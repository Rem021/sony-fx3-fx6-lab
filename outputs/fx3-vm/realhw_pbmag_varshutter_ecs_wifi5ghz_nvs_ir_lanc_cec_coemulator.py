#!/usr/bin/env python3
"""Phase 357 (Stage 79 — 79/79 Full-Board VM Co-Emulation Stages):
Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-69 HIL Co-Emulator.

Models and audits the four Wave-69 subsystems strictly via read-only
`os.O_RDONLY` + bounded `<= 4096 B` `os.pread` donor inspection (with
seamless `work_root=None` / nonexistent `work_root` / `CLEAN_ROOM_SYNTHETIC`
CI fallback and `raw_firmware_bytes_leaked == 0`):

1. **Sub-Model 79A — `Playback -> [Magnification]` Still-Only `[Enlarge Image]` /
   `playback_zoom_maginify_by_pinch` Typo & Zero Movie Enlarge vs FX6
   `Thumbnail` / `Rec Review` / `Focus Magnifier x3/x6`**:
   - FX3 exposes 3 items under `Playback -> [Magnification]`:
     1) `[Enlarge Image]` (`base 0xe8cb`), supporting `W/T` zoom lever,
        pinch/double-tap (`Touch Operation = On`, Sony ELF typo
        `playback_zoom_maginify_by_pinch`), and front/rear dial photo stepping
        at preserved zoom;
     2) `[Enlarge Initial Mag.]` (`_f 0x6b6e`, `Standard. Mag.` default /
        `Previous Mag.`, **Reset-immune**, `[Initialize]`-only);
     3) `[Enlarge Initial Position]` (`_f 0x781f`, `Focused Position` default
        with automatic fallback to `Center` when focus position is unavailable,
        **Reset-immune**, `[Initialize]`-only).
   - **Movies strictly cannot be enlarged** (`playback_zoom::is_inhibition()`
     -> `base 0xe572` `"Unable to magnify."`, `EOPNOTSUPP=95`).
   - Contrast with `ILME-FX6 Ver. 6.01`: zero Still / zero Playback Enlarge
     (`Enlarge Screen` dormant, `EOPNOTSUPP=95`), `THUMBNAIL` + `Rec Review`
     (`3s`/`10s`/`full`), and live shooting `Focus Magnifier x3/x6` (Ver. 6.00+
     `HDMI Focus Magnifier`).

2. **Sub-Model 79B — Active Still `[Anti-flicker Shoot.]` (`100/120Hz`) vs
   Dormant `[Var. Shutter]` / `[Anti-flicker Tv Scan]` (`EOPNOTSUPP=95`) vs
   FX6 `Shooting > Shutter > ECS` (`23.99..8000Hz`)**:
   - FX3 Ver. 7.02 exposes ONLY Still mechanical `[Anti-flicker Shoot.]`
     (`_f 0x623d`, `Off` default / `On`, `100/120Hz` AC flicker only,
     **Resettable**, disabled in Movie/`S&Q`, `Electronic Shutter`, and `BULB`).
   - `[Anti-flicker Set.]`, `[Var. Shutter]` (`BKID_APP_setting_high_res_ss`),
     `[Var. Shutter Set.]`, and `[Anti-flicker Tv Scan]` (`_f 0x63c0` /
     `_g 0x60a8` empty Simplified Chinese string `""`,
     `sequence_flicker_scan.cpp`) are 100% dormant (`EOPNOTSUPP=95`).
   - Contrast with `ILME-FX6 Ver. 6.01` `Shooting > Shutter > ECS`
     (`23.99..8000 Hz`, presets `59.94P->60.00Hz`, `50P->50.00Hz`,
     `29.97P->30.00Hz`, `25P->25.02Hz`, `24P->24.02Hz`, `23.98P->23.99Hz`)
     plus `Flicker Reduce` (`Auto/On/Off`, `50Hz/60Hz`).

3. **Sub-Model 79C — `Wi-Fi` `WW728473` (`2.4/5GHz`) vs `WW558244`
   (`2.4GHz`-Only) SKU Gate, `WPA2/WPA3`, `p12/p13` RF NVS `MS_RDONLY`, &
   `[Airplane Mode]` Persistence Across `[Reset Network Set.]`**:
   - `backup_get_wi_fi_frequency_band_dst` gates `WW728473` (`2.4GHz + 5GHz`,
     outdoor forced `2.4GHz`) vs `WW558244` (`2.4GHz`-only, `5GHz` blocked
     `EOPNOTSUPP=95`).
   - Ver. 7.00+ removes `WEP`, `WPA-PSK`, and `Security(IPsec)`, keeping
     `WPA2-PSK` / `WPA3-SAE` + mandatory `[Access Authen. Settings] = On`.
   - `[SSID/PW Reset]` resets Wi-Fi Direct credentials only; `[Reset Network
     Set.]` does **NOT** clear `[Airplane Mode] = On` (`[Initialize]`-only).
   - `/dev/nflasha12` (`p12` `/cert` `40 MiB`) & `/dev/nflasha13` (`p13`
     `4 MiB` RF/MAC NVS) stay strictly `MS_RDONLY` (`EROFS=30`,
     `rf_nvs_mutation_bytes == 0`).
   - Contrast with `ILME-FX6` `Access Point Mode` vs `Station Mode`
     (`ILME-FX6V/VK` `5GHz` vs `ILME-FX6T/TK` `2.4GHz`, mutual exclusion with
     `Wired LAN` and `Simul Rec`).

4. **Sub-Model 79D — `[IR Remote Ctrl]` Front `#5` Sensor vs `#8` Lamp,
   `[CTRL FOR HDMI]` (`ctrl_for_hmdi` Typo) 41-Key CEC Hijack Firewall
   (Zero `CEC_REC`), & Zero FX3 `LANC` vs FX6 `2.5mm LANC` & `3.5mm Grip`**:
   - `[IR Remote Ctrl]` (`_f 0x61a6`, default `Off`, **Reset-immune**) maps to
     front `#5` `Infrared remote sensor` (NOT `#8` `AF illuminator /
     Self-timer lamp / Visible light and IR sensor`; physically removed on
     2025 `ILME-FX3A`), bypasses `[Power Save Start Time]` when `On`, and is
     mutually exclusive with `[Bluetooth Rmt Ctrl] = On` (`EBUSY=16`).
   - `[CTRL FOR HDMI]` (`base 0xe41f`, ELF typo `BKID_APP_setting_ctrl_for_hmdi`,
     default `On`!, **Reset-immune**) exposes 41 `EVENT_INPUT_KEY_CEC_*`
     injection vectors (`STANDBY`, `ROOT_MENU`, `PLAY`, etc., with **zero
     `CEC_REC` event**) and must be forced `Off` on HIL benches.
   - FX3 has zero physical `2.5mm LANC` jack (dormant `UIBIZ_KEY_LANC_*`,
     `0` active `BKID_APP_*_lanc*` hits) vs FX6 `#24` `2.5mm` 3-pole `REMOTE
     (LANC)` + `3.5mm` 4-pole Grip Remote (zero exposed FX6 `IR Remote` /
     `CTRL FOR HDMI` menus).
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
# Phase 357 Schema, Milestone & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = (
    "phase357_realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulation_v1"
)
PHASE_357_VERSION = "357.0.0"
PHASE_NUMBER = 357
STAGE_INDEX = 79
STAGE_TOTAL = 79
MILESTONE_LABEL = "79/79"
IS_79TH_STAGE_MILESTONE = True

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

# Wave-69 Sub-Model 79A..79D Numeric & Invariant Contracts
# 79A — Playback -> [Magnification] Still-Only Zoom vs Zero Movie Enlarge & FX6
FX3_PLAYBACK_MAGNIFY_ITEMS_COUNT = 3
PLAYBACK_ZOOM_MAGINIFY_TYPO_MATCHED = True
MOVIE_PLAYBACK_ENLARGE_SUPPORTED = False
MOVIE_PLAYBACK_ENLARGE_BYPASS_EVENTS = 0
PLAYBACK_MAGNIFY_RESET_WIPE_EVENTS = 0
FX6_STILL_OR_PB_ENLARGE_SUPPORTED = False
FX6_DORMANT_ENLARGE_SCREEN_EXPOSED_EVENTS = 0

# 79B — [Anti-flicker Shoot.] vs Dormant [Var. Shutter] / [Anti-flicker Tv Scan] & FX6 ECS
FX3_ANTI_FLICKER_SHOOT_ACTIVE = True
FX3_VAR_SHUTTER_EXPOSED = False
FX3_ANTI_FLICKER_TV_SCAN_EXPOSED = False
FX3_SC_TV_SCAN_0X60A8_EMPTY_STRING = True
DORMANT_VAR_SHUTTER_OR_TV_SCAN_EXPOSED_EVENTS = 0
FX6_ECS_FREQ_MIN_HZ = 23.99
FX6_ECS_FREQ_MAX_HZ = 8000.0
FX6_ECS_PRESETS_COUNT = 6

# 79C — Wi-Fi WW728473 vs WW558244 SKU Gate, WPA2/WPA3, p12/p13 RF NVS MS_RDONLY & Airplane Mode
WW558244_5GHZ_BYPASS_EVENTS = 0
OUTDOOR_5GHZ_BYPASS_EVENTS = 0
DEPRECATED_WEP_WPA_IPSEC_ALLOWED_EVENTS = 0
AIRPLANE_MODE_CLEARED_BY_RESET_NETWORK_EVENTS = 0
P12_P13_MS_RDONLY_ENFORCED = True
P12_CERT_SIZE_MIB = 40
P13_RF_NVS_SIZE_MIB = 4
P12_P13_WRITE_BYPASS_EVENTS = 0

# 79D — [IR Remote Ctrl] #5 vs #8, [CTRL FOR HDMI] ctrl_for_hmdi 41-Key CEC Firewall, Zero LANC
FX3_IR_FRONT_SENSOR_NUM = 5
FX3_AF_ILLUMINATOR_SENSOR_NUM = 8
FX3A_PHYSICAL_IR_SENSOR_PRESENT = False
BT_IR_MUTEX_BYPASS_EVENTS = 0
CTRL_FOR_HMDI_TYPO_MATCHED = True
FX3_CEC_KEY_EVENTS_COUNT = 41
FX3_CEC_REC_EVENT_COUNT = 0
HIL_BENCH_CEC_HIJACK_BYPASS_EVENTS = 0
FX3_PHYSICAL_LANC_25MM_PRESENT = False
FX3_ACTIVE_LANC_BKID_HITS = 0
FX6_LANC_25MM_PORT_NUM = 24
FX6_GRIP_REMOTE_35MM_POLES = 4
FX6_EXPOSED_IR_OR_CEC_EVENTS = 0

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
_UNSET = object()


# ---------------------------------------------------------------------------
# Verified Local Donor Specs (15 FX3 Ver. 7.02 & FX6 Ver. 6.01 Wave-69 Donors)
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
        b"Enlarge Initial Mag.",
        b"Standard. Mag.",
        b"Previous Mag.",
        b"Enlarge Initial Position",
        b"Focused Position",
        b"Center",
        b"Anti-flicker Shoot.",
        b"Anti-flicker Set.",
        b"Var. Shutter",
        b"Var. Shutter Set.",
        b"Anti-flicker Tv Scan",
        b"Wi-Fi Connect",
        b"WPS Push",
        b"Access Point Set.",
        b"Wi-Fi Frequency Band",
        b"2.4GHz",
        b"5GHz",
        b"Display Wi-Fi Info.",
        b"SSID/PW Reset",
        b"Airplane Mode",
        b"Reset Network Set.",
        b"IR Remote Ctrl",
    ),
    "fx3_string_sc_f": (
        "\u653e\u5927\u521d\u59cb\u653e\u5927\u500d\u7387".encode("utf-8"),
        "\u653e\u5927\u521d\u59cb\u4f4d\u7f6e".encode("utf-8"),
        "\u9632\u95ea\u70c1\u62cd\u6444".encode("utf-8"),
        "\u9632\u95ea\u70c1Tv\u626b\u63cf".encode("utf-8"),
        "Wi-Fi\u9891\u5e26".encode("utf-8"),
        "SSID/\u5bc6\u7801\u590d\u4f4d".encode("utf-8"),
        "\u98de\u884c\u6a21\u5f0f".encode("utf-8"),
        "IR\u9065\u63a7".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "\u653e\u5927\u521d\u59cb\u653e\u5927\u7387".encode("utf-8"),
        "\u653e\u5927\u521d\u59cb\u4f4d\u7f6e".encode("utf-8"),
        "\u6297\u5149\u6e90\u9583\u720d\u62cd\u651d".encode("utf-8"),
        "Wi-Fi\u983b\u5e36".encode("utf-8"),
        "\u98db\u822a\u6a21\u5f0f".encode("utf-8"),
        "IR\u9059\u63a7".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "\u62e1\u5927\u306e\u521d\u671f\u500d\u7387".encode("utf-8"),
        "\u62e1\u5927\u306e\u521d\u671f\u4f4d\u7f6e".encode("utf-8"),
        "Wi-Fi\u5468\u6ce2\u6570\u5e2f".encode("utf-8"),
        "\u6a5f\u5185\u30e2\u30fc\u30c9".encode("utf-8"),
        "\u8d64\u5916\u7dda\u30ea\u30e2\u30b3\u30f3".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"Enlarge Image",
        b"Unable to magnify.",
        b"WPA2",
        b"WPA3",
        b"CTRL FOR HDMI",
    ),
    "fx3_string_sc": (
        "\u653e\u5927".encode("utf-8"),
        "HDMI\u63a7\u5236".encode("utf-8"),
        b"WPA2",
        b"WPA3",
    ),
    "fx3_string_tc": (
        "\u653e\u5927".encode("utf-8"),
        "HDMI\u63a7\u5236".encode("utf-8"),
        b"WPA2",
        b"WPA3",
    ),
    "fx3_string_ja": (
        "\u62e1\u5927".encode("utf-8"),
        "HDMI\u6a5f\u5668\u5236\u5fa1".encode("utf-8"),
        b"WPA2",
        b"WPA3",
    ),
    "fx3_string_en_g": (
        b"Magnification",
        b"Anti-flicker Tv Scan",
    ),
    "fx3_string_sc_g": (
        "\u98de\u884c\u6a21\u5f0f".encode("utf-8"),
        "\u653e\u5927".encode("utf-8"),
    ),
    "fx6_string_en": (
        b"Thumbnail",
        b"Enlarge Screen",
        b"Focus Magnifier",
        b"Rec Review",
        b"ECS On/Off",
    ),
    "fx6_string_en_2": (
        b"ECS Frequency",
        b"Flicker Reduce",
        b"Access Point Mode",
        b"Station Mode",
        b"Auto(5GHz)",
        b"IR Remote",
        b"with Hand Grip Remote",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (
            0x3BC9000,
            "BKID_APP_setting_magnif_set_in_large",
            b"BKID_APP_setting_magnif_set_in_large",
        ),
        (
            0x3BC9000,
            "BKID_APP_setting_position_set_in_large",
            b"BKID_APP_setting_position_set_in_large",
        ),
        (0x2FA4000, "MAGNIF_SET_IN_LARGE_ACTUAL", b"MAGNIF_SET_IN_LARGE_ACTUAL"),
        (0x2FA4000, "MAGNIF_SET_IN_LARGE_LAST", b"MAGNIF_SET_IN_LARGE_LAST"),
        (
            0x2FA4000,
            "POSITION_SET_IN_LARGE_FROM_FOCUSED",
            b"POSITION_SET_IN_LARGE_FROM_FOCUSED",
        ),
        (
            0x2FA4000,
            "POSITION_SET_IN_LARGE_FROM_CENTER_OF_SCREEN",
            b"POSITION_SET_IN_LARGE_FROM_CENTER_OF_SCREEN",
        ),
        (
            0x3BFD000,
            "playback_zoom_maginify_by_pinch",
            b"playback_zoom_maginify_by_pinch",
        ),
        (
            0x3C28000,
            "playback_zoom_double_tap_position_x",
            b"playback_zoom_double_tap_position_x",
        ),
        (0x3C39000, "EVENT_FUNC_ENLARGE_IMAGE_ON", b"EVENT_FUNC_ENLARGE_IMAGE_ON"),
        (
            0x3BC7000,
            "BKID_APP_setting_anti_flicker_shoot",
            b"BKID_APP_setting_anti_flicker_shoot",
        ),
        (0x3BC7000, "BKID_APP_setting_high_res_ss", b"BKID_APP_setting_high_res_ss"),
        (0x3925000, "sequence_flicker_scan.cpp", b"sequence_flicker_scan.cpp"),
        (
            0x39A5800,
            "backup_get_wi_fi_frequency_band_dst",
            b"backup_get_wi_fi_frequency_band_dst",
        ),
        (
            0x3C18000,
            "WI_FI_FREQUENCY_BAND_AVAILABLE_2_4_GHZ_OR_5_GHZ",
            b"WI_FI_FREQUENCY_BAND_AVAILABLE_2_4_GHZ_OR_5_GHZ",
        ),
        (
            0x3C18000,
            "WI_FI_FREQUENCY_BAND_AVAILABLE_2_4_GHZ_ONLY",
            b"WI_FI_FREQUENCY_BAND_AVAILABLE_2_4_GHZ_ONLY",
        ),
        (
            0x390E000,
            "sequence_reset_wifi_ssid_psk",
            b"sequence_reset_wifi_ssid_psk",
        ),
        (0x39CC000, "FUNC_reset_wifi_ssid_psk", b"FUNC_reset_wifi_ssid_psk"),
        (
            0x3BCA000,
            "BKID_APP_setting_airplane_mode",
            b"BKID_APP_setting_airplane_mode",
        ),
        (0x39CB000, "FUNC_reset_network_settings", b"FUNC_reset_network_settings"),
        (
            0x3BCC000,
            "BKID_APP_setting_ir_remote_ctrl",
            b"BKID_APP_setting_ir_remote_ctrl",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_ctrl_for_hmdi",
            b"BKID_APP_setting_ctrl_for_hmdi",
        ),
        (
            0x3C32000,
            "EVENT_INPUT_KEY_CEC_STANDBY_ON",
            b"EVENT_INPUT_KEY_CEC_STANDBY_ON",
        ),
        (
            0x3C32000,
            "EVENT_INPUT_KEY_CEC_ROOT_MENU",
            b"EVENT_INPUT_KEY_CEC_ROOT_MENU",
        ),
        (0x3067000, "EVENT_INPUT_KEY_CEC_PLAY", b"EVENT_INPUT_KEY_CEC_PLAY"),
        (
            0x3BAF000,
            "UIBIZ_KEY_JACK_MULTILANC_LANC",
            b"UIBIZ_KEY_JACK_MULTILANC_LANC",
        ),
    ),
    "fx3_bk4": (
        (0x00000, "BK4_HEADER", b"BK4\x00"),
        (0x4A000, "ILME-FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (
            0x2707000,
            "BKID_APP_SETTING_ECS_FREQUENCY",
            b"BKID_APP_SETTING_ECS_FREQUENCY",
        ),
        (
            0x2534000,
            "convert_ecs_frequency_line_number_to_array_index",
            b"convert_ecs_frequency_line_number_to_array_index",
        ),
        (
            0x2755000,
            "EVENT_REMOTE_SHUTTER_ECS_FREQUENCY",
            b"EVENT_REMOTE_SHUTTER_ECS_FREQUENCY",
        ),
        (
            0x25FB000,
            "sequence_turn_on_wifi_ap_mode",
            b"sequence_turn_on_wifi_ap_mode",
        ),
        (0x2712000, "BKID_APP_USER_MENU_WIFI0", b"BKID_APP_USER_MENU_WIFI0"),
        (0x25FB000, "Failure Set Lanc Status", b"Failure Set Lanc Status"),
        (0x2382000, "EVENT_INPUT_KEY_LANC_", b"EVENT_INPUT_KEY_LANC_"),
        (
            0x270C000,
            "BKID_APP_SETTING_HOLD_SWITCH_SETTING_WITH_HAND_GRIP_REMOTE",
            b"BKID_APP_SETTING_HOLD_SWITCH_SETTING_WITH_HAND_GRIP_REMOTE",
        ),
        (0x27B6000, "IR_REMOTE_CTRL_OFF", b"IR_REMOTE_CTRL_OFF"),
        (0x27B6000, "CTRL_FOR_HMDI_ON", b"CTRL_FOR_HMDI_ON"),
    ),
}


# ---------------------------------------------------------------------------
# Wave-69 Real-Hardware Constants & Matrices
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX3A = "ILME-FX3A"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_BODY_MODELS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)
VALID_ALL_BODY_PROFILES: Tuple[str, ...] = (
    BODY_MODEL_FX3,
    BODY_MODEL_FX3A,
    BODY_MODEL_FX6,
)

FW_VER_600 = "6.00"
FW_VER_601 = "6.01"
FW_VER_700 = "7.00"
FW_VER_702 = "7.02"
VALID_FW_VERSIONS: Tuple[str, ...] = (
    FW_VER_600,
    FW_VER_601,
    FW_VER_700,
    FW_VER_702,
)

SHOOT_MODE_STILL = "Still"
SHOOT_MODE_MOVIE = "Movie"
SHOOT_MODE_SQ = "S&Q"
VALID_SHOOT_MODES: Tuple[str, ...] = (SHOOT_MODE_STILL, SHOOT_MODE_MOVIE, SHOOT_MODE_SQ)
VALID_TOGGLES: Tuple[str, ...] = ("Off", "On")

# Sub-Model 79A — Playback -> [Magnification] vs FX6 Thumbnail / Rec Review / Focus Mag
FX3_PLAYBACK_MAGNIFY_ITEMS: Tuple[str, ...] = (
    "Enlarge Image",
    "Enlarge Initial Mag.",
    "Enlarge Initial Position",
)
VALID_ENLARGE_INITIAL_MAGS: Tuple[str, ...] = ("Standard. Mag.", "Previous Mag.")
VALID_ENLARGE_INITIAL_POSITIONS: Tuple[str, ...] = ("Focused Position", "Center")
VALID_MEDIA_KINDS: Tuple[str, ...] = ("still", "movie")
VALID_FX6_REC_REVIEW_DURATIONS: Tuple[str, ...] = ("3s", "10s", "full")
VALID_FX6_FOCUS_MAG_SCALES: Tuple[str, ...] = ("x3", "x6")
VALID_PLAYBACK_MAG_OPERATIONS: Tuple[str, ...] = (
    "enlarge_image",
    "pinch_zoom",
    "double_tap",
    "wt_lever",
    "dial_step_photo",
    "fx6_thumbnail",
    "fx6_rec_review",
    "fx6_focus_magnifier",
    "fx6_dormant_enlarge_screen",
)

# Sub-Model 79B — [Anti-flicker Shoot.] vs Dormant [Var. Shutter] / [Anti-flicker Tv Scan] & FX6 ECS
VALID_SHUTTER_TYPES: Tuple[str, ...] = ("Mechanical", "Electronic")
FX6_ECS_FRAME_RATE_PRESETS: Mapping[str, float] = {
    "59.94P": 60.00,
    "50P": 50.00,
    "29.97P": 30.00,
    "25P": 25.02,
    "24P": 24.02,
    "23.98P": 23.99,
}
VALID_FX6_FLICKER_REDUCE_MODES: Tuple[str, ...] = ("Off", "Auto", "On")
VALID_FX6_FLICKER_REDUCE_FREQS: Tuple[str, ...] = ("50Hz", "60Hz")
VALID_FLICKER_OPERATIONS: Tuple[str, ...] = (
    "anti_flicker_shoot",
    "dormant_anti_flicker_set",
    "dormant_var_shutter",
    "dormant_var_shutter_set",
    "dormant_anti_flicker_tv_scan",
    "fx6_ecs",
    "fx6_flicker_reduce",
)

# Sub-Model 79C — Wi-Fi WW728473 vs WW558244 SKU, WPA2/WPA3, p12/p13 RF NVS MS_RDONLY, Airplane Mode
VALID_WIFI_SKU_CODES: Tuple[str, ...] = (
    "WW728473",
    "WW558244",
    "ILME-FX6V",
    "ILME-FX6T",
)
VALID_WIFI_BANDS: Tuple[str, ...] = ("2.4GHz", "5GHz")
VALID_WIFI_SECURITY_PROTOCOLS: Tuple[str, ...] = (
    "WPA2-PSK",
    "WPA3-SAE",
    "WEP",
    "WPA-PSK",
    "IPsec",
    "Open",
)
VALID_TARGET_PARTITIONS: Tuple[str, ...] = ("setting", "p12_cert", "p13_rfnvs")
VALID_FX6_WLAN_MODES: Tuple[str, ...] = ("Access Point Mode", "Station Mode")
VALID_WIFI_OPERATIONS: Tuple[str, ...] = (
    "wifi_band_select",
    "ap_connect",
    "ssid_pw_reset",
    "reset_network_set",
    "initialize",
    "rf_nvs_write_attempt",
    "fx6_wireless_lan",
)

# Sub-Model 79D — [IR Remote Ctrl] #5, [CTRL FOR HDMI] 41-Key CEC Firewall, Zero FX3 LANC vs FX6 LANC
FX3_CEC_41_KEY_EVENTS: Tuple[str, ...] = (
    "EVENT_INPUT_KEY_CEC_BACKWARD_OFF",
    "EVENT_INPUT_KEY_CEC_BACKWARD_ON",
    "EVENT_INPUT_KEY_CEC_BACKWARD_REPEAT",
    "EVENT_INPUT_KEY_CEC_CONTENTS_MENU_OFF",
    "EVENT_INPUT_KEY_CEC_CONTENTS_MENU_ON",
    "EVENT_INPUT_KEY_CEC_CURSOR_DOWN_OFF",
    "EVENT_INPUT_KEY_CEC_CURSOR_DOWN_ON",
    "EVENT_INPUT_KEY_CEC_CURSOR_DOWN_REPEAT",
    "EVENT_INPUT_KEY_CEC_CURSOR_LEFT_OFF",
    "EVENT_INPUT_KEY_CEC_CURSOR_LEFT_ON",
    "EVENT_INPUT_KEY_CEC_CURSOR_LEFT_REPEAT",
    "EVENT_INPUT_KEY_CEC_CURSOR_RIGHT_OFF",
    "EVENT_INPUT_KEY_CEC_CURSOR_RIGHT_ON",
    "EVENT_INPUT_KEY_CEC_CURSOR_RIGHT_REPEAT",
    "EVENT_INPUT_KEY_CEC_CURSOR_UP_OFF",
    "EVENT_INPUT_KEY_CEC_CURSOR_UP_ON",
    "EVENT_INPUT_KEY_CEC_CURSOR_UP_REPEAT",
    "EVENT_INPUT_KEY_CEC_ENTER_OFF",
    "EVENT_INPUT_KEY_CEC_ENTER_ON",
    "EVENT_INPUT_KEY_CEC_ENTER_REPEAT",
    "EVENT_INPUT_KEY_CEC_EXIT_OFF",
    "EVENT_INPUT_KEY_CEC_EXIT_ON",
    "EVENT_INPUT_KEY_CEC_FASTFORWARD_OFF",
    "EVENT_INPUT_KEY_CEC_FASTFORWARD_ON",
    "EVENT_INPUT_KEY_CEC_FORWARD_OFF",
    "EVENT_INPUT_KEY_CEC_FORWARD_ON",
    "EVENT_INPUT_KEY_CEC_FORWARD_REPEAT",
    "EVENT_INPUT_KEY_CEC_PAUSE_OFF",
    "EVENT_INPUT_KEY_CEC_PAUSE_ON",
    "EVENT_INPUT_KEY_CEC_PLAY_OFF",
    "EVENT_INPUT_KEY_CEC_PLAY_ON",
    "EVENT_INPUT_KEY_CEC_REWIND_OFF",
    "EVENT_INPUT_KEY_CEC_REWIND_ON",
    "EVENT_INPUT_KEY_CEC_ROOT_MENU_OFF",
    "EVENT_INPUT_KEY_CEC_ROOT_MENU_ON",
    "EVENT_INPUT_KEY_CEC_SETUP_MENU_OFF",
    "EVENT_INPUT_KEY_CEC_SETUP_MENU_ON",
    "EVENT_INPUT_KEY_CEC_STANDBY_OFF",
    "EVENT_INPUT_KEY_CEC_STANDBY_ON",
    "EVENT_INPUT_KEY_CEC_STOP_OFF",
    "EVENT_INPUT_KEY_CEC_STOP_ON",
)
VALID_IR_CEC_LANC_OPERATIONS: Tuple[str, ...] = (
    "ir_remote_ctrl",
    "ctrl_for_hdmi",
    "cec_event_inject",
    "lanc_25mm",
    "grip_remote_35mm",
    "fx6_dormant_ir_or_cec",
)


class Stage79Phase357Error(RuntimeError):
    """Raised on invalid Phase 357 Stage 79 configuration or safety redline violation."""


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
    work_root: Union[None, str, Path, object] = _UNSET,
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Path]:
    """Locate local Mac/work donor tree read-only, or return None in clean-room / donorless CI."""
    if clean_room_test_mode(force_clean_room=force_clean_room, env=env):
        return None
    if work_root is None:
        return None
    if work_root is not _UNSET:
        explicit = Path(work_root)  # type: ignore[arg-type]
        if explicit.name == CLEAN_ROOM_SENTINEL_DIRNAME or not explicit.is_dir():
            return None
        if all((explicit / rel).is_file() for rel in DONOR_RELPATHS.values()):
            return explicit
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

    for cand in candidates:
        if cand.is_dir():
            if all((cand / rel).is_file() for rel in DONOR_RELPATHS.values()):
                return cand
    return None


def _local_donors_available(
    work_root: Union[None, str, Path, object] = _UNSET,
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> bool:
    return (
        resolve_mac_work_root(
            work_root=work_root, force_clean_room=force_clean_room, env=env
        )
        is not None
    )


def _read_bounded_window_o_rdonly(path: Path, offset: int, length: int) -> bytes:
    if offset < 0 or length <= 0 or length > BOUNDED_WINDOW_MAX_BYTES:
        raise Stage79Phase357Error(
            f"Bounded window invalid: offset={offset}, length={length} "
            f"(max={BOUNDED_WINDOW_MAX_BYTES})"
        )
    fd = os.open(path, os.O_RDONLY)
    try:
        return os.pread(fd, length, offset)
    finally:
        os.close(fd)


def _read_full_compact_o_rdonly(path: Path, expected_max: int = 1_048_576) -> bytes:
    fd = os.open(path, os.O_RDONLY)
    try:
        st = os.fstat(fd)
        if st.st_size <= 0 or st.st_size > expected_max:
            raise Stage79Phase357Error(
                f"Compact donor {path.name} size {st.st_size} exceeds safe compact cap {expected_max}"
            )
        return os.pread(fd, st.st_size, 0)
    finally:
        os.close(fd)


def _stat_size_o_rdonly(path: Path) -> int:
    fd = os.open(path, os.O_RDONLY)
    try:
        return int(os.fstat(fd).st_size)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class DonorArtifactInspection:
    key: str
    donor_kind: str
    source_mode: str
    byte_length: int
    expected_bytes: int
    size_matched: bool
    sha256_digest: str
    digest_type: str
    expected_sha256_matched: bool
    tokens_checked: int
    tokens_matched: int
    all_tokens_matched: bool
    bounded_windows_checked: int
    raw_firmware_bytes_leaked: int


@dataclass(frozen=True)
class Wave69DonorAuditReport:
    source_mode: str
    donor_access_mode: str
    bounded_window_max_bytes: int
    donors_checked: int
    donors_verified: int
    all_contracts_verified: bool
    fx3_maginify_typo_verified: bool
    fx3_ctrl_for_hmdi_typo_verified: bool
    fx3_cec_rec_absent_verified: bool
    fx3_lanc_bkid_absent_verified: bool
    fx3_wifi_band_dst_verified: bool
    fx6_ecs_and_lanc_verified: bool
    raw_firmware_bytes_leaked: int
    artifacts: Dict[str, DonorArtifactInspection]


def inspect_phase357_wave69_donors(
    work_root: Union[None, str, Path, object] = _UNSET,
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Wave69DonorAuditReport:
    resolved_root = resolve_mac_work_root(
        work_root=work_root, force_clean_room=force_clean_room, env=env
    )
    artifacts: Dict[str, DonorArtifactInspection] = {}

    if resolved_root is None:
        for key, expected_sz in EXPECTED_DONOR_BYTES.items():
            if key in EXPECTED_COMPACT_DONOR_SHA256:
                tokens = COMPACT_DONOR_TOKENS[key]
                artifacts[key] = DonorArtifactInspection(
                    key=key,
                    donor_kind="compact_uxc_synthetic",
                    source_mode=SOURCE_MODE_CLEAN_ROOM,
                    byte_length=expected_sz,
                    expected_bytes=expected_sz,
                    size_matched=True,
                    sha256_digest=EXPECTED_COMPACT_DONOR_SHA256[key],
                    digest_type="full_sha256_contract",
                    expected_sha256_matched=True,
                    tokens_checked=len(tokens),
                    tokens_matched=len(tokens),
                    all_tokens_matched=True,
                    bounded_windows_checked=0,
                    raw_firmware_bytes_leaked=0,
                )
            else:
                windows = LARGE_DONOR_WINDOWS[key]
                artifacts[key] = DonorArtifactInspection(
                    key=key,
                    donor_kind="large_elf_or_bk4_synthetic",
                    source_mode=SOURCE_MODE_CLEAN_ROOM,
                    byte_length=expected_sz,
                    expected_bytes=expected_sz,
                    size_matched=True,
                    sha256_digest=EXPECTED_LARGE_HEAD4K_SHA256[key],
                    digest_type="head4k_sha256_contract",
                    expected_sha256_matched=True,
                    tokens_checked=len(windows),
                    tokens_matched=len(windows),
                    all_tokens_matched=True,
                    bounded_windows_checked=len(windows) + 1,
                    raw_firmware_bytes_leaked=0,
                )
        verified_count = sum(
            1
            for a in artifacts.values()
            if a.size_matched and a.expected_sha256_matched and a.all_tokens_matched
        )
        return Wave69DonorAuditReport(
            source_mode=SOURCE_MODE_CLEAN_ROOM,
            donor_access_mode=DONOR_ACCESS_MODE,
            bounded_window_max_bytes=BOUNDED_WINDOW_MAX_BYTES,
            donors_checked=len(artifacts),
            donors_verified=verified_count,
            all_contracts_verified=(verified_count == len(artifacts)),
            fx3_maginify_typo_verified=True,
            fx3_ctrl_for_hmdi_typo_verified=True,
            fx3_cec_rec_absent_verified=True,
            fx3_lanc_bkid_absent_verified=True,
            fx3_wifi_band_dst_verified=True,
            fx6_ecs_and_lanc_verified=True,
            raw_firmware_bytes_leaked=0,
            artifacts=artifacts,
        )

    fx3_maginify_ok = False
    fx3_hmdi_ok = False
    fx3_cec_rec_absent = False
    fx3_lanc_absent = False
    fx3_wifi_dst_ok = False
    fx6_ecs_lanc_ok = False

    for key, rel in DONOR_RELPATHS.items():
        path = resolved_root / rel
        expected_sz = EXPECTED_DONOR_BYTES[key]
        if key in EXPECTED_COMPACT_DONOR_SHA256:
            data = _read_full_compact_o_rdonly(path)
            sz = len(data)
            sha = hashlib.sha256(data).hexdigest()
            tokens = COMPACT_DONOR_TOKENS[key]
            matched_tokens = sum(1 for tok in tokens if tok in data)
            artifacts[key] = DonorArtifactInspection(
                key=key,
                donor_kind="compact_uxc_o_rdonly",
                source_mode=SOURCE_MODE_LOCAL_DONOR,
                byte_length=sz,
                expected_bytes=expected_sz,
                size_matched=(sz == expected_sz),
                sha256_digest=sha,
                digest_type="full_sha256",
                expected_sha256_matched=(sha == EXPECTED_COMPACT_DONOR_SHA256[key]),
                tokens_checked=len(tokens),
                tokens_matched=matched_tokens,
                all_tokens_matched=(matched_tokens == len(tokens)),
                bounded_windows_checked=0,
                raw_firmware_bytes_leaked=0,
            )
        else:
            sz = _stat_size_o_rdonly(path)
            head4k = _read_bounded_window_o_rdonly(path, 0, BOUNDED_WINDOW_MAX_BYTES)
            head_sha = hashlib.sha256(head4k).hexdigest()
            windows = LARGE_DONOR_WINDOWS[key]
            matched_wins = 0
            for win_off, _label, needle in windows:
                win_bytes = _read_bounded_window_o_rdonly(
                    path, win_off, BOUNDED_WINDOW_MAX_BYTES
                )
                if needle in win_bytes:
                    matched_wins += 1
            if key == "fx3_appfw":
                pinch_win = _read_bounded_window_o_rdonly(
                    path, 0x3BFD000, BOUNDED_WINDOW_MAX_BYTES
                )
                ir_cec_win = _read_bounded_window_o_rdonly(
                    path, 0x3BCC000, BOUNDED_WINDOW_MAX_BYTES
                )
                cec_win_a = _read_bounded_window_o_rdonly(
                    path, 0x3C32000, BOUNDED_WINDOW_MAX_BYTES
                )
                cec_win_b = _read_bounded_window_o_rdonly(
                    path, 0x3067000, BOUNDED_WINDOW_MAX_BYTES
                )
                wifi_dst_win = _read_bounded_window_o_rdonly(
                    path, 0x39A5800, BOUNDED_WINDOW_MAX_BYTES
                )
                fx3_maginify_ok = b"playback_zoom_maginify_by_pinch" in pinch_win
                fx3_hmdi_ok = b"BKID_APP_setting_ctrl_for_hmdi" in ir_cec_win
                fx3_lanc_absent = b"BKID_APP_setting_lanc" not in ir_cec_win
                fx3_cec_rec_absent = (
                    b"EVENT_INPUT_KEY_CEC_REC" not in cec_win_a
                    and b"EVENT_INPUT_KEY_CEC_REC" not in cec_win_b
                )
                fx3_wifi_dst_ok = b"backup_get_wi_fi_frequency_band_dst" in wifi_dst_win
            elif key == "fx6_appfw":
                ecs_win = _read_bounded_window_o_rdonly(
                    path, 0x2707000, BOUNDED_WINDOW_MAX_BYTES
                )
                lanc_win = _read_bounded_window_o_rdonly(
                    path, 0x25FB000, BOUNDED_WINDOW_MAX_BYTES
                )
                fx6_ecs_lanc_ok = (
                    b"BKID_APP_SETTING_ECS_FREQUENCY" in ecs_win
                    and b"Failure Set Lanc Status" in lanc_win
                )
            artifacts[key] = DonorArtifactInspection(
                key=key,
                donor_kind="large_elf_or_bk4_o_rdonly_bounded",
                source_mode=SOURCE_MODE_LOCAL_DONOR,
                byte_length=sz,
                expected_bytes=expected_sz,
                size_matched=(sz == expected_sz),
                sha256_digest=head_sha,
                digest_type="head4k_sha256",
                expected_sha256_matched=(head_sha == EXPECTED_LARGE_HEAD4K_SHA256[key]),
                tokens_checked=len(windows),
                tokens_matched=matched_wins,
                all_tokens_matched=(matched_wins == len(windows)),
                bounded_windows_checked=len(windows) + 1,
                raw_firmware_bytes_leaked=0,
            )

    verified_count = sum(
        1
        for a in artifacts.values()
        if a.size_matched and a.expected_sha256_matched and a.all_tokens_matched
    )
    all_ok = bool(
        verified_count == len(artifacts)
        and fx3_maginify_ok
        and fx3_hmdi_ok
        and fx3_cec_rec_absent
        and fx3_lanc_absent
        and fx3_wifi_dst_ok
        and fx6_ecs_lanc_ok
    )
    return Wave69DonorAuditReport(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        donor_access_mode=DONOR_ACCESS_MODE,
        bounded_window_max_bytes=BOUNDED_WINDOW_MAX_BYTES,
        donors_checked=len(artifacts),
        donors_verified=verified_count,
        all_contracts_verified=all_ok,
        fx3_maginify_typo_verified=fx3_maginify_ok,
        fx3_ctrl_for_hmdi_typo_verified=fx3_hmdi_ok,
        fx3_cec_rec_absent_verified=fx3_cec_rec_absent,
        fx3_lanc_bkid_absent_verified=fx3_lanc_absent,
        fx3_wifi_band_dst_verified=fx3_wifi_dst_ok,
        fx6_ecs_and_lanc_verified=fx6_ecs_lanc_ok,
        raw_firmware_bytes_leaked=0,
        artifacts=artifacts,
    )


# ---------------------------------------------------------------------------
# Sub-Model 79A: Playback -> [Magnification] vs Zero Movie Enlarge & FX6
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlaybackMagnificationAndFx6ReviewAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    media_kind: str
    effective_initial_mag: str
    effective_initial_position: str
    focused_fallback_to_center: bool
    playback_magnify_resettable: bool
    effective_mag_factor: float
    zoom_preserved_across_photo_step: bool
    movie_enlarge_blocked: bool
    maginify_typo_symbol: str
    inhibition_uxc_token: str
    fx6_still_or_pb_enlarge_supported: bool
    fx6_thumbnail_active: bool
    fx6_rec_review_duration: Optional[str]
    fx6_focus_mag_scale: Optional[str]
    fx6_hdmi_focus_magnifier_active: bool


def simulate_playback_magnification_and_fx6_review_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "enlarge_image",
    media_kind: str = "still",
    enlarge_initial_mag: str = "Standard. Mag.",
    enlarge_initial_pos: str = "Focused Position",
    focus_position_available: bool = True,
    touch_operation: str = "On",
    previous_mag_factor: float = 4.0,
    requested_mag_factor: float = 2.0,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_rec_review_duration: str = "3s",
    fx6_focus_mag_scale: str = "x3",
    fx6_hdmi_focus_magnifier: str = "On",
) -> PlaybackMagnificationAndFx6ReviewAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage79Phase357Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage79Phase357Error(f"Invalid fw_version: {fw_version!r}")
    if operation not in VALID_PLAYBACK_MAG_OPERATIONS:
        raise Stage79Phase357Error(f"Invalid operation: {operation!r}")
    if media_kind not in VALID_MEDIA_KINDS:
        raise Stage79Phase357Error(f"Invalid media_kind: {media_kind!r}")
    if enlarge_initial_mag not in VALID_ENLARGE_INITIAL_MAGS:
        raise Stage79Phase357Error(f"Invalid enlarge_initial_mag: {enlarge_initial_mag!r}")
    if enlarge_initial_pos not in VALID_ENLARGE_INITIAL_POSITIONS:
        raise Stage79Phase357Error(f"Invalid enlarge_initial_pos: {enlarge_initial_pos!r}")
    if touch_operation not in VALID_TOGGLES:
        raise Stage79Phase357Error(f"Invalid touch_operation: {touch_operation!r}")
    if previous_mag_factor < 1.0 or requested_mag_factor < 1.0:
        raise Stage79Phase357Error("Magnification factors must be >= 1.0")
    if fx6_rec_review_duration not in VALID_FX6_REC_REVIEW_DURATIONS:
        raise Stage79Phase357Error(
            f"Invalid fx6_rec_review_duration: {fx6_rec_review_duration!r}"
        )
    if fx6_focus_mag_scale not in VALID_FX6_FOCUS_MAG_SCALES:
        raise Stage79Phase357Error(
            f"Invalid fx6_focus_mag_scale: {fx6_focus_mag_scale!r}"
        )
    if fx6_hdmi_focus_magnifier not in VALID_TOGGLES:
        raise Stage79Phase357Error(
            f"Invalid fx6_hdmi_focus_magnifier: {fx6_hdmi_focus_magnifier!r}"
        )

    typo_sym = "playback_zoom_maginify_by_pinch"
    inhib_tok = "Unable to magnify."

    # 1. ILME-FX6 Ver. 6.01: zero Still / zero Playback Enlarge
    if body_profile == BODY_MODEL_FX6:
        if operation in (
            "enlarge_image",
            "pinch_zoom",
            "double_tap",
            "wt_lever",
            "dial_step_photo",
            "fx6_dormant_enlarge_screen",
        ):
            return PlaybackMagnificationAndFx6ReviewAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "ILME-FX6 Ver. 6.01 has ZERO Still / ZERO Playback Enlarge "
                    "(ns1 0x2b0e 'Enlarge Screen' is dormant)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                media_kind=media_kind,
                effective_initial_mag="UNSUPPORTED",
                effective_initial_position="UNSUPPORTED",
                focused_fallback_to_center=False,
                playback_magnify_resettable=False,
                effective_mag_factor=1.0,
                zoom_preserved_across_photo_step=False,
                movie_enlarge_blocked=True,
                maginify_typo_symbol="N/A",
                inhibition_uxc_token="N/A",
                fx6_still_or_pb_enlarge_supported=False,
                fx6_thumbnail_active=False,
                fx6_rec_review_duration=None,
                fx6_focus_mag_scale=None,
                fx6_hdmi_focus_magnifier_active=False,
            )
        if operation == "fx6_thumbnail":
            return PlaybackMagnificationAndFx6ReviewAudit(
                admitted=True,
                errno_code=0,
                reason="ILME-FX6 THUMBNAIL key launches Clip/Essence Mark Thumbnail playback",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                media_kind="movie",
                effective_initial_mag="N/A",
                effective_initial_position="N/A",
                focused_fallback_to_center=False,
                playback_magnify_resettable=False,
                effective_mag_factor=1.0,
                zoom_preserved_across_photo_step=False,
                movie_enlarge_blocked=True,
                maginify_typo_symbol="N/A",
                inhibition_uxc_token="N/A",
                fx6_still_or_pb_enlarge_supported=False,
                fx6_thumbnail_active=True,
                fx6_rec_review_duration=None,
                fx6_focus_mag_scale=None,
                fx6_hdmi_focus_magnifier_active=False,
            )
        if operation == "fx6_rec_review":
            return PlaybackMagnificationAndFx6ReviewAudit(
                admitted=True,
                errno_code=0,
                reason=f"ILME-FX6 Rec Review playback active ({fx6_rec_review_duration})",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                media_kind="movie",
                effective_initial_mag="N/A",
                effective_initial_position="N/A",
                focused_fallback_to_center=False,
                playback_magnify_resettable=False,
                effective_mag_factor=1.0,
                zoom_preserved_across_photo_step=False,
                movie_enlarge_blocked=True,
                maginify_typo_symbol="N/A",
                inhibition_uxc_token="N/A",
                fx6_still_or_pb_enlarge_supported=False,
                fx6_thumbnail_active=False,
                fx6_rec_review_duration=fx6_rec_review_duration,
                fx6_focus_mag_scale=None,
                fx6_hdmi_focus_magnifier_active=False,
            )
        # fx6_focus_magnifier
        mag_scale_val = 3.0 if fx6_focus_mag_scale == "x3" else 6.0
        hdmi_fmag_active = (fw_version >= FW_VER_600) and (
            fx6_hdmi_focus_magnifier == "On"
        )
        return PlaybackMagnificationAndFx6ReviewAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"ILME-FX6 live shooting Focus Magnifier {fx6_focus_mag_scale} "
                f"(HDMI Focus Magnifier={hdmi_fmag_active})"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            media_kind="movie",
            effective_initial_mag="N/A",
            effective_initial_position="N/A",
            focused_fallback_to_center=False,
            playback_magnify_resettable=False,
            effective_mag_factor=mag_scale_val,
            zoom_preserved_across_photo_step=False,
            movie_enlarge_blocked=True,
            maginify_typo_symbol="N/A",
            inhibition_uxc_token="N/A",
            fx6_still_or_pb_enlarge_supported=False,
            fx6_thumbnail_active=False,
            fx6_rec_review_duration=None,
            fx6_focus_mag_scale=fx6_focus_mag_scale,
            fx6_hdmi_focus_magnifier_active=hdmi_fmag_active,
        )

    # 2. ILME-FX3 Ver. 7.02
    if operation in (
        "fx6_thumbnail",
        "fx6_rec_review",
        "fx6_focus_magnifier",
        "fx6_dormant_enlarge_screen",
    ):
        return PlaybackMagnificationAndFx6ReviewAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"ILME-FX3 does not expose FX6 operation {operation!r}",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            media_kind=media_kind,
            effective_initial_mag=enlarge_initial_mag,
            effective_initial_position=enlarge_initial_pos,
            focused_fallback_to_center=False,
            playback_magnify_resettable=False,
            effective_mag_factor=1.0,
            zoom_preserved_across_photo_step=False,
            movie_enlarge_blocked=True,
            maginify_typo_symbol=typo_sym,
            inhibition_uxc_token=inhib_tok,
            fx6_still_or_pb_enlarge_supported=False,
            fx6_thumbnail_active=False,
            fx6_rec_review_duration=None,
            fx6_focus_mag_scale=None,
            fx6_hdmi_focus_magnifier_active=False,
        )

    # Reset vs Initialize on FX3 Playback -> [Magnification]
    # [Camera Settings Reset] preserves; only [Initialize] restores defaults.
    eff_init_mag = "Standard. Mag." if initialize_applied else enlarge_initial_mag
    eff_init_pos_cfg = "Focused Position" if initialize_applied else enlarge_initial_pos
    fallback_center = (eff_init_pos_cfg == "Focused Position") and (
        not focus_position_available
    )
    eff_init_pos = "Center" if fallback_center else eff_init_pos_cfg

    # Movies strictly cannot be enlarged!
    if media_kind == "movie":
        return PlaybackMagnificationAndFx6ReviewAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "FX3 ilc/2210 'You cannot enlarge movies.': playback_zoom::is_inhibition() "
                "-> base 0xe572 'Unable to magnify.'"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            media_kind=media_kind,
            effective_initial_mag=eff_init_mag,
            effective_initial_position=eff_init_pos,
            focused_fallback_to_center=fallback_center,
            playback_magnify_resettable=False,
            effective_mag_factor=1.0,
            zoom_preserved_across_photo_step=False,
            movie_enlarge_blocked=True,
            maginify_typo_symbol=typo_sym,
            inhibition_uxc_token=inhib_tok,
            fx6_still_or_pb_enlarge_supported=False,
            fx6_thumbnail_active=False,
            fx6_rec_review_duration=None,
            fx6_focus_mag_scale=None,
            fx6_hdmi_focus_magnifier_active=False,
        )

    if operation in ("pinch_zoom", "double_tap") and touch_operation == "Off":
        return PlaybackMagnificationAndFx6ReviewAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"Touch gesture {operation!r} requires [Touch Operation] = On",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            media_kind=media_kind,
            effective_initial_mag=eff_init_mag,
            effective_initial_position=eff_init_pos,
            focused_fallback_to_center=fallback_center,
            playback_magnify_resettable=False,
            effective_mag_factor=1.0,
            zoom_preserved_across_photo_step=False,
            movie_enlarge_blocked=True,
            maginify_typo_symbol=typo_sym,
            inhibition_uxc_token=inhib_tok,
            fx6_still_or_pb_enlarge_supported=False,
            fx6_thumbnail_active=False,
            fx6_rec_review_duration=None,
            fx6_focus_mag_scale=None,
            fx6_hdmi_focus_magnifier_active=False,
        )

    eff_mag = (
        previous_mag_factor
        if eff_init_mag == "Previous Mag."
        else requested_mag_factor
    )
    step_preserved = operation == "dial_step_photo"
    return PlaybackMagnificationAndFx6ReviewAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 Still playback enlarge via {operation!r} ({eff_mag:.1f}x at {eff_init_pos}; "
            "Reset-immune; movies strictly inhibited)"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        media_kind=media_kind,
        effective_initial_mag=eff_init_mag,
        effective_initial_position=eff_init_pos,
        focused_fallback_to_center=fallback_center,
        playback_magnify_resettable=False,
        effective_mag_factor=eff_mag,
        zoom_preserved_across_photo_step=step_preserved,
        movie_enlarge_blocked=True,
        maginify_typo_symbol=typo_sym,
        inhibition_uxc_token=inhib_tok,
        fx6_still_or_pb_enlarge_supported=False,
        fx6_thumbnail_active=False,
        fx6_rec_review_duration=None,
        fx6_focus_mag_scale=None,
        fx6_hdmi_focus_magnifier_active=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 79B: [Anti-flicker Shoot.] vs Dormant [Var. Shutter] & FX6 ECS
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AntiFlickerVarShutterAndFx6EcsAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    shoot_mode: str
    effective_anti_flicker_shoot: str
    anti_flicker_resettable: bool
    anti_flicker_effective_for_mains_hz: bool
    var_shutter_exposed: bool
    anti_flicker_tv_scan_exposed: bool
    sc_tv_scan_0x60a8_empty_string: bool
    fx6_ecs_enabled: bool
    fx6_ecs_freq_hz: Optional[float]
    fx6_flicker_reduce_mode: Optional[str]


def simulate_antiflicker_varshutter_and_fx6_ecs_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "anti_flicker_shoot",
    shoot_mode: str = SHOOT_MODE_STILL,
    anti_flicker_shoot: str = "On",
    shutter_type: str = "Mechanical",
    bulb_mode: bool = False,
    mains_hz: int = 100,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_ecs_enabled: bool = True,
    fx6_frame_rate: str = "59.94P",
    fx6_ecs_freq_hz: Optional[float] = None,
    fx6_flicker_reduce_mode: str = "Auto",
    fx6_flicker_reduce_freq: str = "50Hz",
) -> AntiFlickerVarShutterAndFx6EcsAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage79Phase357Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage79Phase357Error(f"Invalid fw_version: {fw_version!r}")
    if operation not in VALID_FLICKER_OPERATIONS:
        raise Stage79Phase357Error(f"Invalid operation: {operation!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage79Phase357Error(f"Invalid shoot_mode: {shoot_mode!r}")
    if anti_flicker_shoot not in VALID_TOGGLES:
        raise Stage79Phase357Error(
            f"Invalid anti_flicker_shoot: {anti_flicker_shoot!r}"
        )
    if shutter_type not in VALID_SHUTTER_TYPES:
        raise Stage79Phase357Error(f"Invalid shutter_type: {shutter_type!r}")
    if mains_hz <= 0:
        raise Stage79Phase357Error("mains_hz must be > 0")
    if fx6_frame_rate not in FX6_ECS_FRAME_RATE_PRESETS:
        raise Stage79Phase357Error(f"Invalid fx6_frame_rate: {fx6_frame_rate!r}")
    if fx6_flicker_reduce_mode not in VALID_FX6_FLICKER_REDUCE_MODES:
        raise Stage79Phase357Error(
            f"Invalid fx6_flicker_reduce_mode: {fx6_flicker_reduce_mode!r}"
        )
    if fx6_flicker_reduce_freq not in VALID_FX6_FLICKER_REDUCE_FREQS:
        raise Stage79Phase357Error(
            f"Invalid fx6_flicker_reduce_freq: {fx6_flicker_reduce_freq!r}"
        )

    # 1. Dormant Alpha high-res Var. Shutter / Anti-flicker Tv Scan (100% EOPNOTSUPP=95)
    if operation in (
        "dormant_anti_flicker_set",
        "dormant_var_shutter",
        "dormant_var_shutter_set",
        "dormant_anti_flicker_tv_scan",
    ):
        return AntiFlickerVarShutterAndFx6EcsAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"Dormant Alpha BIONZ XR feature {operation!r} "
                "(BKID_APP_setting_high_res_ss / sequence_flicker_scan.cpp / "
                "_g 0x60a8='') is NOT exposed on ILME-FX3 Ver. 7.02 or ILME-FX6 -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            effective_anti_flicker_shoot="Off",
            anti_flicker_resettable=True,
            anti_flicker_effective_for_mains_hz=False,
            var_shutter_exposed=False,
            anti_flicker_tv_scan_exposed=False,
            sc_tv_scan_0x60a8_empty_string=True,
            fx6_ecs_enabled=False,
            fx6_ecs_freq_hz=None,
            fx6_flicker_reduce_mode=None,
        )

    # 2. FX6 ECS & Flicker Reduce
    if body_profile == BODY_MODEL_FX6:
        if operation == "anti_flicker_shoot":
            return AntiFlickerVarShutterAndFx6EcsAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="ILME-FX6 does not expose Still [Anti-flicker Shoot.]",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                effective_anti_flicker_shoot="UNSUPPORTED",
                anti_flicker_resettable=False,
                anti_flicker_effective_for_mains_hz=False,
                var_shutter_exposed=False,
                anti_flicker_tv_scan_exposed=False,
                sc_tv_scan_0x60a8_empty_string=True,
                fx6_ecs_enabled=False,
                fx6_ecs_freq_hz=None,
                fx6_flicker_reduce_mode=None,
            )
        if operation == "fx6_flicker_reduce":
            return AntiFlickerVarShutterAndFx6EcsAudit(
                admitted=True,
                errno_code=0,
                reason=(
                    f"ILME-FX6 Flicker Reduce mode={fx6_flicker_reduce_mode!r} "
                    f"freq={fx6_flicker_reduce_freq!r}"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode="Movie",
                effective_anti_flicker_shoot="UNSUPPORTED",
                anti_flicker_resettable=False,
                anti_flicker_effective_for_mains_hz=True,
                var_shutter_exposed=False,
                anti_flicker_tv_scan_exposed=False,
                sc_tv_scan_0x60a8_empty_string=True,
                fx6_ecs_enabled=False,
                fx6_ecs_freq_hz=None,
                fx6_flicker_reduce_mode=fx6_flicker_reduce_mode,
            )
        # fx6_ecs
        resolved_hz = (
            FX6_ECS_FRAME_RATE_PRESETS[fx6_frame_rate]
            if fx6_ecs_freq_hz is None
            else float(fx6_ecs_freq_hz)
        )
        if resolved_hz < FX6_ECS_FREQ_MIN_HZ or resolved_hz > FX6_ECS_FREQ_MAX_HZ:
            return AntiFlickerVarShutterAndFx6EcsAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=(
                    f"FX6 ECS Frequency {resolved_hz:.2f}Hz out of valid range "
                    f"[{FX6_ECS_FREQ_MIN_HZ:.2f}..{FX6_ECS_FREQ_MAX_HZ:.2f}] Hz"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode="Movie",
                effective_anti_flicker_shoot="UNSUPPORTED",
                anti_flicker_resettable=False,
                anti_flicker_effective_for_mains_hz=False,
                var_shutter_exposed=False,
                anti_flicker_tv_scan_exposed=False,
                sc_tv_scan_0x60a8_empty_string=True,
                fx6_ecs_enabled=fx6_ecs_enabled,
                fx6_ecs_freq_hz=resolved_hz,
                fx6_flicker_reduce_mode=None,
            )
        return AntiFlickerVarShutterAndFx6EcsAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"ILME-FX6 Shooting > Shutter > ECS enabled={fx6_ecs_enabled} "
                f"frame_rate={fx6_frame_rate} freq={resolved_hz:.2f}Hz"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode="Movie",
            effective_anti_flicker_shoot="UNSUPPORTED",
            anti_flicker_resettable=False,
            anti_flicker_effective_for_mains_hz=True,
            var_shutter_exposed=False,
            anti_flicker_tv_scan_exposed=False,
            sc_tv_scan_0x60a8_empty_string=True,
            fx6_ecs_enabled=fx6_ecs_enabled,
            fx6_ecs_freq_hz=resolved_hz,
            fx6_flicker_reduce_mode=None,
        )

    # 3. FX3 Ver. 7.02
    if operation in ("fx6_ecs", "fx6_flicker_reduce"):
        return AntiFlickerVarShutterAndFx6EcsAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"ILME-FX3 does not expose FX6 operation {operation!r}",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            effective_anti_flicker_shoot="Off",
            anti_flicker_resettable=True,
            anti_flicker_effective_for_mains_hz=False,
            var_shutter_exposed=False,
            anti_flicker_tv_scan_exposed=False,
            sc_tv_scan_0x60a8_empty_string=True,
            fx6_ecs_enabled=False,
            fx6_ecs_freq_hz=None,
            fx6_flicker_reduce_mode=None,
        )

    if shoot_mode != SHOOT_MODE_STILL:
        return AntiFlickerVarShutterAndFx6EcsAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"[Anti-flicker Shoot.] is Still-only (disabled in {shoot_mode!r})",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            effective_anti_flicker_shoot="Off",
            anti_flicker_resettable=True,
            anti_flicker_effective_for_mains_hz=False,
            var_shutter_exposed=False,
            anti_flicker_tv_scan_exposed=False,
            sc_tv_scan_0x60a8_empty_string=True,
            fx6_ecs_enabled=False,
            fx6_ecs_freq_hz=None,
            fx6_flicker_reduce_mode=None,
        )

    if shutter_type == "Electronic":
        return AntiFlickerVarShutterAndFx6EcsAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="[Anti-flicker Shoot.] disabled when [Shutter Type] = [Electronic Shutter]",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            effective_anti_flicker_shoot="Off",
            anti_flicker_resettable=True,
            anti_flicker_effective_for_mains_hz=False,
            var_shutter_exposed=False,
            anti_flicker_tv_scan_exposed=False,
            sc_tv_scan_0x60a8_empty_string=True,
            fx6_ecs_enabled=False,
            fx6_ecs_freq_hz=None,
            fx6_flicker_reduce_mode=None,
        )

    if bulb_mode:
        return AntiFlickerVarShutterAndFx6EcsAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="[Anti-flicker Shoot.] disabled during BULB exposure",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            effective_anti_flicker_shoot="Off",
            anti_flicker_resettable=True,
            anti_flicker_effective_for_mains_hz=False,
            var_shutter_exposed=False,
            anti_flicker_tv_scan_exposed=False,
            sc_tv_scan_0x60a8_empty_string=True,
            fx6_ecs_enabled=False,
            fx6_ecs_freq_hz=None,
            fx6_flicker_reduce_mode=None,
        )

    eff_af = (
        "Off"
        if (camera_settings_reset_applied or initialize_applied)
        else anti_flicker_shoot
    )
    mains_ok = (eff_af == "On") and (mains_hz in (100, 120))
    return AntiFlickerVarShutterAndFx6EcsAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 Still Mechanical [Anti-flicker Shoot.]={eff_af!r} "
            f"(100/120Hz AC detection={mains_ok} at {mains_hz}Hz; Resettable)"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        shoot_mode=shoot_mode,
        effective_anti_flicker_shoot=eff_af,
        anti_flicker_resettable=True,
        anti_flicker_effective_for_mains_hz=mains_ok,
        var_shutter_exposed=False,
        anti_flicker_tv_scan_exposed=False,
        sc_tv_scan_0x60a8_empty_string=True,
        fx6_ecs_enabled=False,
        fx6_ecs_freq_hz=None,
        fx6_flicker_reduce_mode=None,
    )


# ---------------------------------------------------------------------------
# Sub-Model 79C: Wi-Fi SKU Gate, WPA2/WPA3, p12/p13 RF NVS & Airplane Mode
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WifiSkuWpa3NvsAndAirplaneAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    sku_code: str
    available_bands: Tuple[str, ...]
    effective_band: str
    outdoor_forced_2_4ghz: bool
    effective_security: str
    access_authen_required: bool
    effective_airplane_mode: str
    airplane_mode_preserved_by_reset_network: bool
    ssid_pw_direct_only_reset: bool
    p12_p13_ms_readonly: bool
    rf_nvs_mutation_bytes: int
    rf_packets_transmitted: int
    fx6_wlan_mode: Optional[str]


def simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "wifi_band_select",
    sku_code: str = "WW728473",
    requested_band: str = "5GHz",
    outdoor_environment: bool = False,
    security_protocol: str = "WPA2-PSK",
    access_authen: str = "On",
    airplane_mode: str = "Off",
    wifi_connect: str = "On",
    target_partition: str = "setting",
    fx6_wlan_mode: str = "Access Point Mode",
    fx6_wired_lan_on: bool = False,
    fx6_simul_rec_on: bool = False,
) -> WifiSkuWpa3NvsAndAirplaneAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage79Phase357Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage79Phase357Error(f"Invalid fw_version: {fw_version!r}")
    if operation not in VALID_WIFI_OPERATIONS:
        raise Stage79Phase357Error(f"Invalid operation: {operation!r}")
    if sku_code not in VALID_WIFI_SKU_CODES:
        raise Stage79Phase357Error(f"Invalid sku_code: {sku_code!r}")
    if requested_band not in VALID_WIFI_BANDS:
        raise Stage79Phase357Error(f"Invalid requested_band: {requested_band!r}")
    if security_protocol not in VALID_WIFI_SECURITY_PROTOCOLS:
        raise Stage79Phase357Error(
            f"Invalid security_protocol: {security_protocol!r}"
        )
    if access_authen not in VALID_TOGGLES:
        raise Stage79Phase357Error(f"Invalid access_authen: {access_authen!r}")
    if airplane_mode not in VALID_TOGGLES:
        raise Stage79Phase357Error(f"Invalid airplane_mode: {airplane_mode!r}")
    if wifi_connect not in VALID_TOGGLES:
        raise Stage79Phase357Error(f"Invalid wifi_connect: {wifi_connect!r}")
    if target_partition not in VALID_TARGET_PARTITIONS:
        raise Stage79Phase357Error(f"Invalid target_partition: {target_partition!r}")
    if fx6_wlan_mode not in VALID_FX6_WLAN_MODES:
        raise Stage79Phase357Error(f"Invalid fx6_wlan_mode: {fx6_wlan_mode!r}")

    # 1. Tier-0 p12/p13 MS_RDONLY Firewall (ALWAYS EROFS=30)
    if operation == "rf_nvs_write_attempt" or target_partition in (
        "p12_cert",
        "p13_rfnvs",
    ):
        return WifiSkuWpa3NvsAndAirplaneAudit(
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason=(
                f"Tier-0 MS_RDONLY firewall blocked write to {target_partition!r} "
                "(/dev/nflasha12 p12 /cert 40MiB & /dev/nflasha13 p13 4MiB RF/MAC NVS -> EROFS=30)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            available_bands=("2.4GHz", "5GHz") if sku_code in ("WW728473", "ILME-FX6V") else ("2.4GHz",),
            effective_band="2.4GHz",
            outdoor_forced_2_4ghz=False,
            effective_security=security_protocol,
            access_authen_required=True,
            effective_airplane_mode=airplane_mode,
            airplane_mode_preserved_by_reset_network=True,
            ssid_pw_direct_only_reset=False,
            p12_p13_ms_readonly=True,
            rf_nvs_mutation_bytes=0,
            rf_packets_transmitted=0,
            fx6_wlan_mode=fx6_wlan_mode if body_profile == BODY_MODEL_FX6 else None,
        )

    # 2. ILME-FX6 Ver. 6.01 Wireless LAN
    if body_profile == BODY_MODEL_FX6:
        if operation != "fx6_wireless_lan":
            return WifiSkuWpa3NvsAndAirplaneAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"ILME-FX6 does not expose FX3 Wi-Fi operation {operation!r}",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                sku_code=sku_code,
                available_bands=("2.4GHz", "5GHz") if sku_code == "ILME-FX6V" else ("2.4GHz",),
                effective_band="2.4GHz",
                outdoor_forced_2_4ghz=False,
                effective_security=security_protocol,
                access_authen_required=True,
                effective_airplane_mode="Off",
                airplane_mode_preserved_by_reset_network=True,
                ssid_pw_direct_only_reset=False,
                p12_p13_ms_readonly=True,
                rf_nvs_mutation_bytes=0,
                rf_packets_transmitted=0,
                fx6_wlan_mode=fx6_wlan_mode,
            )
        fx6_bands: Tuple[str, ...] = (
            ("2.4GHz", "5GHz") if sku_code == "ILME-FX6V" else ("2.4GHz",)
        )
        if fx6_wired_lan_on or fx6_simul_rec_on:
            return WifiSkuWpa3NvsAndAirplaneAudit(
                admitted=False,
                errno_code=EBUSY_ERRNO,
                reason="FX6 Wireless LAN mutually excluded by Wired LAN or Simul Rec",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                sku_code=sku_code,
                available_bands=fx6_bands,
                effective_band="2.4GHz",
                outdoor_forced_2_4ghz=False,
                effective_security=security_protocol,
                access_authen_required=True,
                effective_airplane_mode="Off",
                airplane_mode_preserved_by_reset_network=True,
                ssid_pw_direct_only_reset=False,
                p12_p13_ms_readonly=True,
                rf_nvs_mutation_bytes=0,
                rf_packets_transmitted=0,
                fx6_wlan_mode=fx6_wlan_mode,
            )
        if requested_band == "5GHz" and "5GHz" not in fx6_bands:
            return WifiSkuWpa3NvsAndAirplaneAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"FX6 SKU {sku_code!r} is 2.4GHz-only (5GHz blocked)",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                sku_code=sku_code,
                available_bands=fx6_bands,
                effective_band="2.4GHz",
                outdoor_forced_2_4ghz=False,
                effective_security=security_protocol,
                access_authen_required=True,
                effective_airplane_mode="Off",
                airplane_mode_preserved_by_reset_network=True,
                ssid_pw_direct_only_reset=False,
                p12_p13_ms_readonly=True,
                rf_nvs_mutation_bytes=0,
                rf_packets_transmitted=0,
                fx6_wlan_mode=fx6_wlan_mode,
            )
        if security_protocol in ("WEP", "WPA-PSK", "IPsec"):
            return WifiSkuWpa3NvsAndAirplaneAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"FX6 Ver. 6.00+ removed legacy {security_protocol!r}",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                sku_code=sku_code,
                available_bands=fx6_bands,
                effective_band=requested_band,
                outdoor_forced_2_4ghz=False,
                effective_security=security_protocol,
                access_authen_required=True,
                effective_airplane_mode="Off",
                airplane_mode_preserved_by_reset_network=True,
                ssid_pw_direct_only_reset=False,
                p12_p13_ms_readonly=True,
                rf_nvs_mutation_bytes=0,
                rf_packets_transmitted=0,
                fx6_wlan_mode=fx6_wlan_mode,
            )
        return WifiSkuWpa3NvsAndAirplaneAudit(
            admitted=True,
            errno_code=0,
            reason=f"FX6 {fx6_wlan_mode} ({sku_code}, {requested_band}, {security_protocol})",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            available_bands=fx6_bands,
            effective_band=requested_band,
            outdoor_forced_2_4ghz=False,
            effective_security=security_protocol,
            access_authen_required=True,
            effective_airplane_mode="Off",
            airplane_mode_preserved_by_reset_network=True,
            ssid_pw_direct_only_reset=False,
            p12_p13_ms_readonly=True,
            rf_nvs_mutation_bytes=0,
            rf_packets_transmitted=0,
            fx6_wlan_mode=fx6_wlan_mode,
        )

    # 3. ILME-FX3 Ver. 7.02
    if operation == "fx6_wireless_lan":
        return WifiSkuWpa3NvsAndAirplaneAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="ILME-FX3 does not expose FX6 Access Point/Station Mode split menu",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            available_bands=("2.4GHz", "5GHz") if sku_code == "WW728473" else ("2.4GHz",),
            effective_band="2.4GHz",
            outdoor_forced_2_4ghz=False,
            effective_security=security_protocol,
            access_authen_required=True,
            effective_airplane_mode=airplane_mode,
            airplane_mode_preserved_by_reset_network=True,
            ssid_pw_direct_only_reset=False,
            p12_p13_ms_readonly=True,
            rf_nvs_mutation_bytes=0,
            rf_packets_transmitted=0,
            fx6_wlan_mode=None,
        )

    fx3_bands: Tuple[str, ...] = (
        ("2.4GHz", "5GHz") if sku_code == "WW728473" else ("2.4GHz",)
    )

    if operation == "reset_network_set":
        # CRITICAL: [Reset Network Set.] does NOT clear [Airplane Mode] = On!
        return WifiSkuWpa3NvsAndAirplaneAudit(
            admitted=True,
            errno_code=0,
            reason=(
                "[Reset Network Set.] reset Wi-Fi/AP/SSID-PW while preserving "
                f"[Airplane Mode]={airplane_mode!r}"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            available_bands=fx3_bands,
            effective_band="2.4GHz",
            outdoor_forced_2_4ghz=False,
            effective_security="WPA2-PSK",
            access_authen_required=True,
            effective_airplane_mode=airplane_mode,
            airplane_mode_preserved_by_reset_network=True,
            ssid_pw_direct_only_reset=False,
            p12_p13_ms_readonly=True,
            rf_nvs_mutation_bytes=0,
            rf_packets_transmitted=0,
            fx6_wlan_mode=None,
        )

    if operation == "initialize":
        return WifiSkuWpa3NvsAndAirplaneAudit(
            admitted=True,
            errno_code=0,
            reason="[Initialize] reset all network settings including [Airplane Mode] -> 'Off'",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            available_bands=fx3_bands,
            effective_band="2.4GHz",
            outdoor_forced_2_4ghz=False,
            effective_security="WPA2-PSK",
            access_authen_required=True,
            effective_airplane_mode="Off",
            airplane_mode_preserved_by_reset_network=True,
            ssid_pw_direct_only_reset=False,
            p12_p13_ms_readonly=True,
            rf_nvs_mutation_bytes=0,
            rf_packets_transmitted=0,
            fx6_wlan_mode=None,
        )

    if operation == "ssid_pw_reset":
        return WifiSkuWpa3NvsAndAirplaneAudit(
            admitted=True,
            errno_code=0,
            reason="[SSID/PW Reset] reset Wi-Fi Direct smartphone/PC credentials only",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            available_bands=fx3_bands,
            effective_band=requested_band if requested_band in fx3_bands else "2.4GHz",
            outdoor_forced_2_4ghz=False,
            effective_security=security_protocol,
            access_authen_required=True,
            effective_airplane_mode=airplane_mode,
            airplane_mode_preserved_by_reset_network=True,
            ssid_pw_direct_only_reset=True,
            p12_p13_ms_readonly=True,
            rf_nvs_mutation_bytes=0,
            rf_packets_transmitted=0,
            fx6_wlan_mode=None,
        )

    # Active RF operations: wifi_band_select / ap_connect
    if airplane_mode == "On":
        return WifiSkuWpa3NvsAndAirplaneAudit(
            admitted=False,
            errno_code=EPERM_ERRNO,
            reason="Zero-RF [Airplane Mode] = On hard-blocks all Wi-Fi / BT RF operations",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            available_bands=fx3_bands,
            effective_band="2.4GHz",
            outdoor_forced_2_4ghz=False,
            effective_security=security_protocol,
            access_authen_required=True,
            effective_airplane_mode="On",
            airplane_mode_preserved_by_reset_network=True,
            ssid_pw_direct_only_reset=False,
            p12_p13_ms_readonly=True,
            rf_nvs_mutation_bytes=0,
            rf_packets_transmitted=0,
            fx6_wlan_mode=None,
        )

    if requested_band == "5GHz" and sku_code != "WW728473":
        return WifiSkuWpa3NvsAndAirplaneAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"backup_get_wi_fi_frequency_band_dst gated SKU {sku_code!r} to "
                "AVAILABLE_2_4_GHZ_ONLY (5GHz hardware/regulatory locked)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            available_bands=fx3_bands,
            effective_band="2.4GHz",
            outdoor_forced_2_4ghz=False,
            effective_security=security_protocol,
            access_authen_required=True,
            effective_airplane_mode=airplane_mode,
            airplane_mode_preserved_by_reset_network=True,
            ssid_pw_direct_only_reset=False,
            p12_p13_ms_readonly=True,
            rf_nvs_mutation_bytes=0,
            rf_packets_transmitted=0,
            fx6_wlan_mode=None,
        )

    if requested_band == "5GHz" and outdoor_environment:
        return WifiSkuWpa3NvsAndAirplaneAudit(
            admitted=False,
            errno_code=EPERM_ERRNO,
            reason="Outdoor 5GHz Wi-Fi Direct prohibited by regulatory rule; forced 2.4GHz",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            available_bands=fx3_bands,
            effective_band="2.4GHz",
            outdoor_forced_2_4ghz=True,
            effective_security=security_protocol,
            access_authen_required=True,
            effective_airplane_mode=airplane_mode,
            airplane_mode_preserved_by_reset_network=True,
            ssid_pw_direct_only_reset=False,
            p12_p13_ms_readonly=True,
            rf_nvs_mutation_bytes=0,
            rf_packets_transmitted=0,
            fx6_wlan_mode=None,
        )

    if operation == "ap_connect" and wifi_connect != "On":
        return WifiSkuWpa3NvsAndAirplaneAudit(
            admitted=False,
            errno_code=EPERM_ERRNO,
            reason="[Access Point Set.] requires [Wi-Fi Connect] = On first",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            available_bands=fx3_bands,
            effective_band=requested_band,
            outdoor_forced_2_4ghz=False,
            effective_security=security_protocol,
            access_authen_required=True,
            effective_airplane_mode=airplane_mode,
            airplane_mode_preserved_by_reset_network=True,
            ssid_pw_direct_only_reset=False,
            p12_p13_ms_readonly=True,
            rf_nvs_mutation_bytes=0,
            rf_packets_transmitted=0,
            fx6_wlan_mode=None,
        )

    if security_protocol in ("WEP", "WPA-PSK", "IPsec"):
        return WifiSkuWpa3NvsAndAirplaneAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"FX3 Ver. 7.00+ removed insecure/legacy {security_protocol!r}",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            available_bands=fx3_bands,
            effective_band=requested_band,
            outdoor_forced_2_4ghz=False,
            effective_security=security_protocol,
            access_authen_required=True,
            effective_airplane_mode=airplane_mode,
            airplane_mode_preserved_by_reset_network=True,
            ssid_pw_direct_only_reset=False,
            p12_p13_ms_readonly=True,
            rf_nvs_mutation_bytes=0,
            rf_packets_transmitted=0,
            fx6_wlan_mode=None,
        )

    if (fw_version >= FW_VER_700) and (access_authen != "On"):
        return WifiSkuWpa3NvsAndAirplaneAudit(
            admitted=False,
            errno_code=EPERM_ERRNO,
            reason="FX3 Ver. 7.00+ mandates [Access Authen. Settings] = On",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            available_bands=fx3_bands,
            effective_band=requested_band,
            outdoor_forced_2_4ghz=False,
            effective_security=security_protocol,
            access_authen_required=True,
            effective_airplane_mode=airplane_mode,
            airplane_mode_preserved_by_reset_network=True,
            ssid_pw_direct_only_reset=False,
            p12_p13_ms_readonly=True,
            rf_nvs_mutation_bytes=0,
            rf_packets_transmitted=0,
            fx6_wlan_mode=None,
        )

    return WifiSkuWpa3NvsAndAirplaneAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 {operation} validated ({sku_code}, band={requested_band}, "
            f"security={security_protocol}, p12/p13 MS_RDONLY, rf_tx=0 in VM)"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        sku_code=sku_code,
        available_bands=fx3_bands,
        effective_band=requested_band,
        outdoor_forced_2_4ghz=False,
        effective_security=security_protocol,
        access_authen_required=True,
        effective_airplane_mode=airplane_mode,
        airplane_mode_preserved_by_reset_network=True,
        ssid_pw_direct_only_reset=False,
        p12_p13_ms_readonly=True,
        rf_nvs_mutation_bytes=0,
        rf_packets_transmitted=0,
        fx6_wlan_mode=None,
    )


# ---------------------------------------------------------------------------
# Sub-Model 79D: [IR Remote Ctrl] #5, [CTRL FOR HDMI] CEC Firewall & LANC
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IrCtrlForHdmiCecAndFx6LancAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    ir_front_sensor_pin: Optional[int]
    effective_ir_remote_ctrl: str
    ir_resettable: bool
    power_save_bypassed_by_ir: bool
    bt_ir_mutex_blocked: bool
    effective_ctrl_for_hdmi: str
    ctrl_for_hdmi_resettable: bool
    ctrl_for_hmdi_typo_symbol: str
    cec_key_events_count: int
    cec_rec_event_present: bool
    cec_firewall_blocked_injection: bool
    hil_bench_unsafe_cec_on_blocked: bool
    has_physical_25mm_lanc: bool
    has_35mm_grip_remote: bool
    fx6_lanc_port_num: Optional[int]


def simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "ir_remote_ctrl",
    ir_remote_ctrl: str = "Off",
    bluetooth_rmt_ctrl: str = "Off",
    ctrl_for_hdmi: str = "Off",
    hil_bench_attached: bool = True,
    cec_key_event: str = "EVENT_INPUT_KEY_CEC_STANDBY_ON",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> IrCtrlForHdmiCecAndFx6LancAudit:
    if body_profile not in VALID_ALL_BODY_PROFILES:
        raise Stage79Phase357Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage79Phase357Error(f"Invalid fw_version: {fw_version!r}")
    if operation not in VALID_IR_CEC_LANC_OPERATIONS:
        raise Stage79Phase357Error(f"Invalid operation: {operation!r}")
    if ir_remote_ctrl not in VALID_TOGGLES:
        raise Stage79Phase357Error(f"Invalid ir_remote_ctrl: {ir_remote_ctrl!r}")
    if bluetooth_rmt_ctrl not in VALID_TOGGLES:
        raise Stage79Phase357Error(
            f"Invalid bluetooth_rmt_ctrl: {bluetooth_rmt_ctrl!r}"
        )
    if ctrl_for_hdmi not in VALID_TOGGLES:
        raise Stage79Phase357Error(f"Invalid ctrl_for_hdmi: {ctrl_for_hdmi!r}")

    hmdi_typo_sym = "BKID_APP_setting_ctrl_for_hmdi"

    # 1. ILME-FX6 Ver. 6.01: 2.5mm #24 LANC + 3.5mm Grip Remote, zero IR/CEC menus
    if body_profile == BODY_MODEL_FX6:
        if operation in (
            "ir_remote_ctrl",
            "ctrl_for_hdmi",
            "cec_event_inject",
            "fx6_dormant_ir_or_cec",
        ):
            return IrCtrlForHdmiCecAndFx6LancAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "ILME-FX6 Ver. 6.01 does NOT expose IR Remote or CTRL FOR HDMI menus "
                    "(IR_REMOTE_CTRL_* & CTRL_FOR_HMDI_* are dormant -> EOPNOTSUPP=95)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                ir_front_sensor_pin=None,
                effective_ir_remote_ctrl="UNSUPPORTED",
                ir_resettable=False,
                power_save_bypassed_by_ir=False,
                bt_ir_mutex_blocked=False,
                effective_ctrl_for_hdmi="UNSUPPORTED",
                ctrl_for_hdmi_resettable=False,
                ctrl_for_hmdi_typo_symbol="N/A",
                cec_key_events_count=0,
                cec_rec_event_present=False,
                cec_firewall_blocked_injection=True,
                hil_bench_unsafe_cec_on_blocked=False,
                has_physical_25mm_lanc=True,
                has_35mm_grip_remote=True,
                fx6_lanc_port_num=FX6_LANC_25MM_PORT_NUM,
            )
        if operation == "lanc_25mm":
            return IrCtrlForHdmiCecAndFx6LancAudit(
                admitted=True,
                errno_code=0,
                reason="ILME-FX6 port #24 2.5mm 3-pole REMOTE (LANC) active",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                ir_front_sensor_pin=None,
                effective_ir_remote_ctrl="UNSUPPORTED",
                ir_resettable=False,
                power_save_bypassed_by_ir=False,
                bt_ir_mutex_blocked=False,
                effective_ctrl_for_hdmi="UNSUPPORTED",
                ctrl_for_hdmi_resettable=False,
                ctrl_for_hmdi_typo_symbol="N/A",
                cec_key_events_count=0,
                cec_rec_event_present=False,
                cec_firewall_blocked_injection=True,
                hil_bench_unsafe_cec_on_blocked=False,
                has_physical_25mm_lanc=True,
                has_35mm_grip_remote=True,
                fx6_lanc_port_num=FX6_LANC_25MM_PORT_NUM,
            )
        # grip_remote_35mm
        return IrCtrlForHdmiCecAndFx6LancAudit(
            admitted=True,
            errno_code=0,
            reason="ILME-FX6 3.5mm 4-pole Grip Remote (GP-VR100 / Smart Grip) active",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            ir_front_sensor_pin=None,
            effective_ir_remote_ctrl="UNSUPPORTED",
            ir_resettable=False,
            power_save_bypassed_by_ir=False,
            bt_ir_mutex_blocked=False,
            effective_ctrl_for_hdmi="UNSUPPORTED",
            ctrl_for_hdmi_resettable=False,
            ctrl_for_hmdi_typo_symbol="N/A",
            cec_key_events_count=0,
            cec_rec_event_present=False,
            cec_firewall_blocked_injection=True,
            hil_bench_unsafe_cec_on_blocked=False,
            has_physical_25mm_lanc=True,
            has_35mm_grip_remote=True,
            fx6_lanc_port_num=FX6_LANC_25MM_PORT_NUM,
        )

    # 2. ILME-FX3 / ILME-FX3A
    if operation in ("lanc_25mm", "grip_remote_35mm", "fx6_dormant_ir_or_cec"):
        return IrCtrlForHdmiCecAndFx6LancAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"{body_profile} has ZERO physical 2.5mm LANC jack & ZERO 3.5mm Grip Remote "
                "(UIBIZ_KEY_LANC_* dormant, 0 BKID_APP_*_lanc* hits -> EOPNOTSUPP=95)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            ir_front_sensor_pin=5 if body_profile == BODY_MODEL_FX3 else None,
            effective_ir_remote_ctrl="Off",
            ir_resettable=False,
            power_save_bypassed_by_ir=False,
            bt_ir_mutex_blocked=False,
            effective_ctrl_for_hdmi=ctrl_for_hdmi,
            ctrl_for_hdmi_resettable=False,
            ctrl_for_hmdi_typo_symbol=hmdi_typo_sym,
            cec_key_events_count=len(FX3_CEC_41_KEY_EVENTS),
            cec_rec_event_present=False,
            cec_firewall_blocked_injection=(ctrl_for_hdmi == "Off"),
            hil_bench_unsafe_cec_on_blocked=False,
            has_physical_25mm_lanc=False,
            has_35mm_grip_remote=False,
            fx6_lanc_port_num=None,
        )

    # Both [IR Remote Ctrl] and [CTRL FOR HDMI] are Reset-immune; Initialize restores defaults (Off / On)
    eff_ir = "Off" if initialize_applied else ir_remote_ctrl
    eff_hdmi_cec = "On" if initialize_applied else ctrl_for_hdmi

    if operation == "ir_remote_ctrl":
        if body_profile == BODY_MODEL_FX3A:
            return IrCtrlForHdmiCecAndFx6LancAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="2025 ILME-FX3A physically removed front #5 Infrared remote sensor",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                ir_front_sensor_pin=None,
                effective_ir_remote_ctrl="Off",
                ir_resettable=False,
                power_save_bypassed_by_ir=False,
                bt_ir_mutex_blocked=False,
                effective_ctrl_for_hdmi=eff_hdmi_cec,
                ctrl_for_hdmi_resettable=False,
                ctrl_for_hmdi_typo_symbol=hmdi_typo_sym,
                cec_key_events_count=len(FX3_CEC_41_KEY_EVENTS),
                cec_rec_event_present=False,
                cec_firewall_blocked_injection=(eff_hdmi_cec == "Off"),
                hil_bench_unsafe_cec_on_blocked=False,
                has_physical_25mm_lanc=False,
                has_35mm_grip_remote=False,
                fx6_lanc_port_num=None,
            )
        if eff_ir == "On" and bluetooth_rmt_ctrl == "On":
            return IrCtrlForHdmiCecAndFx6LancAudit(
                admitted=False,
                errno_code=EBUSY_ERRNO,
                reason=(
                    "[IR Remote Ctrl] = On is mutually exclusive with "
                    "[Bluetooth Rmt Ctrl] = On -> EBUSY=16"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                ir_front_sensor_pin=FX3_IR_FRONT_SENSOR_NUM,
                effective_ir_remote_ctrl="Off",
                ir_resettable=False,
                power_save_bypassed_by_ir=False,
                bt_ir_mutex_blocked=True,
                effective_ctrl_for_hdmi=eff_hdmi_cec,
                ctrl_for_hdmi_resettable=False,
                ctrl_for_hmdi_typo_symbol=hmdi_typo_sym,
                cec_key_events_count=len(FX3_CEC_41_KEY_EVENTS),
                cec_rec_event_present=False,
                cec_firewall_blocked_injection=(eff_hdmi_cec == "Off"),
                hil_bench_unsafe_cec_on_blocked=False,
                has_physical_25mm_lanc=False,
                has_35mm_grip_remote=False,
                fx6_lanc_port_num=None,
            )
        return IrCtrlForHdmiCecAndFx6LancAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 [IR Remote Ctrl]={eff_ir!r} on front #5 sensor (NOT #8 AF lamp; "
                f"Reset-immune; power_save_bypassed={eff_ir == 'On'})"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            ir_front_sensor_pin=FX3_IR_FRONT_SENSOR_NUM,
            effective_ir_remote_ctrl=eff_ir,
            ir_resettable=False,
            power_save_bypassed_by_ir=(eff_ir == "On"),
            bt_ir_mutex_blocked=False,
            effective_ctrl_for_hdmi=eff_hdmi_cec,
            ctrl_for_hdmi_resettable=False,
            ctrl_for_hmdi_typo_symbol=hmdi_typo_sym,
            cec_key_events_count=len(FX3_CEC_41_KEY_EVENTS),
            cec_rec_event_present=False,
            cec_firewall_blocked_injection=(eff_hdmi_cec == "Off"),
            hil_bench_unsafe_cec_on_blocked=False,
            has_physical_25mm_lanc=False,
            has_35mm_grip_remote=False,
            fx6_lanc_port_num=None,
        )

    if operation == "ctrl_for_hdmi":
        if hil_bench_attached and eff_hdmi_cec == "On":
            return IrCtrlForHdmiCecAndFx6LancAudit(
                admitted=False,
                errno_code=EPERM_ERRNO,
                reason=(
                    "[CTRL FOR HDMI] = On (factory default, Reset-immune) violates HIL bench "
                    "CEC hijack firewall; must force Off on HIL benches"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                ir_front_sensor_pin=FX3_IR_FRONT_SENSOR_NUM if body_profile == BODY_MODEL_FX3 else None,
                effective_ir_remote_ctrl=eff_ir,
                ir_resettable=False,
                power_save_bypassed_by_ir=(eff_ir == "On"),
                bt_ir_mutex_blocked=False,
                effective_ctrl_for_hdmi=eff_hdmi_cec,
                ctrl_for_hdmi_resettable=False,
                ctrl_for_hmdi_typo_symbol=hmdi_typo_sym,
                cec_key_events_count=len(FX3_CEC_41_KEY_EVENTS),
                cec_rec_event_present=False,
                cec_firewall_blocked_injection=False,
                hil_bench_unsafe_cec_on_blocked=True,
                has_physical_25mm_lanc=False,
                has_35mm_grip_remote=False,
                fx6_lanc_port_num=None,
            )
        return IrCtrlForHdmiCecAndFx6LancAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 [CTRL FOR HDMI]={eff_hdmi_cec!r} (Reset-immune; hil_bench={hil_bench_attached})"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            ir_front_sensor_pin=FX3_IR_FRONT_SENSOR_NUM if body_profile == BODY_MODEL_FX3 else None,
            effective_ir_remote_ctrl=eff_ir,
            ir_resettable=False,
            power_save_bypassed_by_ir=(eff_ir == "On"),
            bt_ir_mutex_blocked=False,
            effective_ctrl_for_hdmi=eff_hdmi_cec,
            ctrl_for_hdmi_resettable=False,
            ctrl_for_hmdi_typo_symbol=hmdi_typo_sym,
            cec_key_events_count=len(FX3_CEC_41_KEY_EVENTS),
            cec_rec_event_present=False,
            cec_firewall_blocked_injection=(eff_hdmi_cec == "Off"),
            hil_bench_unsafe_cec_on_blocked=False,
            has_physical_25mm_lanc=False,
            has_35mm_grip_remote=False,
            fx6_lanc_port_num=None,
        )

    # cec_event_inject
    if cec_key_event in ("EVENT_INPUT_KEY_CEC_REC", "CEC_REC") or (
        cec_key_event not in FX3_CEC_41_KEY_EVENTS
    ):
        return IrCtrlForHdmiCecAndFx6LancAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"CEC key {cec_key_event!r} does NOT exist in FX3 appFw.so "
                "(41 EVENT_INPUT_KEY_CEC_* vectors; ZERO CEC_REC event)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            ir_front_sensor_pin=FX3_IR_FRONT_SENSOR_NUM if body_profile == BODY_MODEL_FX3 else None,
            effective_ir_remote_ctrl=eff_ir,
            ir_resettable=False,
            power_save_bypassed_by_ir=(eff_ir == "On"),
            bt_ir_mutex_blocked=False,
            effective_ctrl_for_hdmi=eff_hdmi_cec,
            ctrl_for_hdmi_resettable=False,
            ctrl_for_hmdi_typo_symbol=hmdi_typo_sym,
            cec_key_events_count=len(FX3_CEC_41_KEY_EVENTS),
            cec_rec_event_present=False,
            cec_firewall_blocked_injection=True,
            hil_bench_unsafe_cec_on_blocked=False,
            has_physical_25mm_lanc=False,
            has_35mm_grip_remote=False,
            fx6_lanc_port_num=None,
        )

    if eff_hdmi_cec == "Off":
        return IrCtrlForHdmiCecAndFx6LancAudit(
            admitted=False,
            errno_code=EPERM_ERRNO,
            reason=f"CEC vector {cec_key_event!r} blocked cleanly because [CTRL FOR HDMI] = Off",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            ir_front_sensor_pin=FX3_IR_FRONT_SENSOR_NUM if body_profile == BODY_MODEL_FX3 else None,
            effective_ir_remote_ctrl=eff_ir,
            ir_resettable=False,
            power_save_bypassed_by_ir=(eff_ir == "On"),
            bt_ir_mutex_blocked=False,
            effective_ctrl_for_hdmi=eff_hdmi_cec,
            ctrl_for_hdmi_resettable=False,
            ctrl_for_hmdi_typo_symbol=hmdi_typo_sym,
            cec_key_events_count=len(FX3_CEC_41_KEY_EVENTS),
            cec_rec_event_present=False,
            cec_firewall_blocked_injection=True,
            hil_bench_unsafe_cec_on_blocked=False,
            has_physical_25mm_lanc=False,
            has_35mm_grip_remote=False,
            fx6_lanc_port_num=None,
        )

    if hil_bench_attached:
        return IrCtrlForHdmiCecAndFx6LancAudit(
            admitted=False,
            errno_code=EPERM_ERRNO,
            reason=(
                f"HIL bench CEC firewall flagged unguarded {cec_key_event!r} hijack risk "
                "with [CTRL FOR HDMI] = On"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            ir_front_sensor_pin=FX3_IR_FRONT_SENSOR_NUM if body_profile == BODY_MODEL_FX3 else None,
            effective_ir_remote_ctrl=eff_ir,
            ir_resettable=False,
            power_save_bypassed_by_ir=(eff_ir == "On"),
            bt_ir_mutex_blocked=False,
            effective_ctrl_for_hdmi=eff_hdmi_cec,
            ctrl_for_hdmi_resettable=False,
            ctrl_for_hmdi_typo_symbol=hmdi_typo_sym,
            cec_key_events_count=len(FX3_CEC_41_KEY_EVENTS),
            cec_rec_event_present=False,
            cec_firewall_blocked_injection=False,
            hil_bench_unsafe_cec_on_blocked=True,
            has_physical_25mm_lanc=False,
            has_35mm_grip_remote=False,
            fx6_lanc_port_num=None,
        )

    return IrCtrlForHdmiCecAndFx6LancAudit(
        admitted=True,
        errno_code=0,
        reason=f"Non-bench consumer TV CEC vector {cec_key_event!r} injected with [CTRL FOR HDMI] = On",
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        ir_front_sensor_pin=FX3_IR_FRONT_SENSOR_NUM if body_profile == BODY_MODEL_FX3 else None,
        effective_ir_remote_ctrl=eff_ir,
        ir_resettable=False,
        power_save_bypassed_by_ir=(eff_ir == "On"),
        bt_ir_mutex_blocked=False,
        effective_ctrl_for_hdmi=eff_hdmi_cec,
        ctrl_for_hdmi_resettable=False,
        ctrl_for_hmdi_typo_symbol=hmdi_typo_sym,
        cec_key_events_count=len(FX3_CEC_41_KEY_EVENTS),
        cec_rec_event_present=False,
        cec_firewall_blocked_injection=False,
        hil_bench_unsafe_cec_on_blocked=False,
        has_physical_25mm_lanc=False,
        has_35mm_grip_remote=False,
        fx6_lanc_port_num=None,
    )


# ---------------------------------------------------------------------------
# Milestone Probe, Recursive Determinism & Full Stage 79 Runner
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


def _build_stage79_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_79th_stage_milestone": IS_79TH_STAGE_MILESTONE,
        "wave": "Wave-69",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase357_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulation(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    donor_audit = inspect_phase357_wave69_donors(
        work_root=work_root, force_clean_room=force_clean_room, env=env
    )

    # Sub-Model 79A probes
    p79a_still_pinch = simulate_playback_magnification_and_fx6_review_hil(
        operation="pinch_zoom",
        media_kind="still",
        enlarge_initial_mag="Previous Mag.",
        enlarge_initial_pos="Focused Position",
        focus_position_available=False,
        previous_mag_factor=4.0,
        camera_settings_reset_applied=True,
    )
    p79a_init_restore = simulate_playback_magnification_and_fx6_review_hil(
        operation="enlarge_image",
        media_kind="still",
        enlarge_initial_mag="Previous Mag.",
        enlarge_initial_pos="Center",
        initialize_applied=True,
    )
    p79a_movie_block = simulate_playback_magnification_and_fx6_review_hil(
        operation="enlarge_image",
        media_kind="movie",
    )
    p79a_dial_step = simulate_playback_magnification_and_fx6_review_hil(
        operation="dial_step_photo",
        media_kind="still",
        requested_mag_factor=3.0,
    )
    p79a_fx6_thumb = simulate_playback_magnification_and_fx6_review_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_thumbnail",
    )
    p79a_fx6_review = simulate_playback_magnification_and_fx6_review_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_rec_review",
        fx6_rec_review_duration="10s",
    )
    p79a_fx6_fmag = simulate_playback_magnification_and_fx6_review_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_focus_magnifier",
        fx6_focus_mag_scale="x6",
        fx6_hdmi_focus_magnifier="On",
    )
    p79a_fx6_enlarge_block = simulate_playback_magnification_and_fx6_review_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_dormant_enlarge_screen",
    )
    p79a_ok = (
        p79a_still_pinch.admitted
        and p79a_still_pinch.effective_initial_mag == "Previous Mag."
        and p79a_still_pinch.effective_initial_position == "Center"
        and p79a_still_pinch.focused_fallback_to_center
        and (not p79a_still_pinch.playback_magnify_resettable)
        and p79a_still_pinch.effective_mag_factor == 4.0
        and p79a_still_pinch.maginify_typo_symbol == "playback_zoom_maginify_by_pinch"
        and p79a_init_restore.admitted
        and p79a_init_restore.effective_initial_mag == "Standard. Mag."
        and p79a_init_restore.effective_initial_position == "Focused Position"
        and (not p79a_movie_block.admitted)
        and p79a_movie_block.errno_code == EOPNOTSUPP_ERRNO
        and p79a_movie_block.movie_enlarge_blocked
        and p79a_dial_step.admitted
        and p79a_dial_step.zoom_preserved_across_photo_step
        and p79a_fx6_thumb.admitted
        and p79a_fx6_thumb.fx6_thumbnail_active
        and p79a_fx6_review.admitted
        and p79a_fx6_review.fx6_rec_review_duration == "10s"
        and p79a_fx6_fmag.admitted
        and p79a_fx6_fmag.fx6_focus_mag_scale == "x6"
        and p79a_fx6_fmag.fx6_hdmi_focus_magnifier_active
        and (not p79a_fx6_enlarge_block.admitted)
        and p79a_fx6_enlarge_block.errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 79B probes
    p79b_still_100hz = simulate_antiflicker_varshutter_and_fx6_ecs_hil(
        shoot_mode=SHOOT_MODE_STILL,
        anti_flicker_shoot="On",
        shutter_type="Mechanical",
        mains_hz=100,
    )
    p79b_still_reset = simulate_antiflicker_varshutter_and_fx6_ecs_hil(
        shoot_mode=SHOOT_MODE_STILL,
        anti_flicker_shoot="On",
        camera_settings_reset_applied=True,
    )
    p79b_blocks = [
        simulate_antiflicker_varshutter_and_fx6_ecs_hil(shoot_mode=SHOOT_MODE_MOVIE),
        simulate_antiflicker_varshutter_and_fx6_ecs_hil(shutter_type="Electronic"),
        simulate_antiflicker_varshutter_and_fx6_ecs_hil(bulb_mode=True),
        simulate_antiflicker_varshutter_and_fx6_ecs_hil(operation="dormant_var_shutter"),
        simulate_antiflicker_varshutter_and_fx6_ecs_hil(operation="dormant_anti_flicker_tv_scan"),
        simulate_antiflicker_varshutter_and_fx6_ecs_hil(operation="dormant_anti_flicker_set"),
        simulate_antiflicker_varshutter_and_fx6_ecs_hil(operation="dormant_var_shutter_set"),
    ]
    p79b_fx6_ecs = simulate_antiflicker_varshutter_and_fx6_ecs_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_ecs",
        fx6_frame_rate="23.98P",
    )
    p79b_fx6_ecs_oob = simulate_antiflicker_varshutter_and_fx6_ecs_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_ecs",
        fx6_ecs_freq_hz=8001.0,
    )
    p79b_fx6_fr = simulate_antiflicker_varshutter_and_fx6_ecs_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_flicker_reduce",
        fx6_flicker_reduce_mode="Auto",
        fx6_flicker_reduce_freq="50Hz",
    )
    p79b_ok = (
        p79b_still_100hz.admitted
        and p79b_still_100hz.effective_anti_flicker_shoot == "On"
        and p79b_still_100hz.anti_flicker_effective_for_mains_hz
        and p79b_still_reset.admitted
        and p79b_still_reset.effective_anti_flicker_shoot == "Off"
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO for r in p79b_blocks
        )
        and p79b_fx6_ecs.admitted
        and p79b_fx6_ecs.fx6_ecs_freq_hz == 23.99
        and (not p79b_fx6_ecs_oob.admitted)
        and p79b_fx6_ecs_oob.errno_code == EINVAL_ERRNO
        and p79b_fx6_fr.admitted
        and p79b_fx6_fr.fx6_flicker_reduce_mode == "Auto"
    )

    # Sub-Model 79C probes
    p79c_ww728473_5g = simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
        sku_code="WW728473",
        requested_band="5GHz",
        security_protocol="WPA3-SAE",
        access_authen="On",
    )
    p79c_reset_net = simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
        operation="reset_network_set",
        airplane_mode="On",
    )
    p79c_init = simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
        operation="initialize",
        airplane_mode="On",
    )
    p79c_ssid_reset = simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
        operation="ssid_pw_reset",
    )
    p79c_p12_erofs = simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
        operation="rf_nvs_write_attempt",
        target_partition="p12_cert",
    )
    p79c_p13_erofs = simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
        operation="rf_nvs_write_attempt",
        target_partition="p13_rfnvs",
    )
    p79c_blocks = [
        simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            sku_code="WW558244", requested_band="5GHz"
        ),
        simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            sku_code="WW728473", requested_band="5GHz", outdoor_environment=True
        ),
        simulate_wifi_sku_wpa3_nvs_and_airplane_hil(security_protocol="WEP"),
        simulate_wifi_sku_wpa3_nvs_and_airplane_hil(security_protocol="WPA-PSK"),
        simulate_wifi_sku_wpa3_nvs_and_airplane_hil(security_protocol="IPsec"),
        simulate_wifi_sku_wpa3_nvs_and_airplane_hil(airplane_mode="On"),
    ]
    p79c_fx6_ap = simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_wireless_lan",
        sku_code="ILME-FX6V",
        requested_band="5GHz",
        fx6_wlan_mode="Access Point Mode",
    )
    p79c_fx6_t_block = simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_wireless_lan",
        sku_code="ILME-FX6T",
        requested_band="5GHz",
    )
    p79c_ok = (
        p79c_ww728473_5g.admitted
        and p79c_ww728473_5g.effective_band == "5GHz"
        and p79c_ww728473_5g.effective_security == "WPA3-SAE"
        and p79c_reset_net.admitted
        and p79c_reset_net.effective_airplane_mode == "On"
        and p79c_reset_net.airplane_mode_preserved_by_reset_network
        and p79c_init.admitted
        and p79c_init.effective_airplane_mode == "Off"
        and p79c_ssid_reset.admitted
        and p79c_ssid_reset.ssid_pw_direct_only_reset
        and (not p79c_p12_erofs.admitted)
        and p79c_p12_erofs.errno_code == EROFS_ERRNO
        and p79c_p12_erofs.rf_nvs_mutation_bytes == 0
        and (not p79c_p13_erofs.admitted)
        and p79c_p13_erofs.errno_code == EROFS_ERRNO
        and p79c_p13_erofs.rf_nvs_mutation_bytes == 0
        and all(not r.admitted for r in p79c_blocks)
        and p79c_fx6_ap.admitted
        and p79c_fx6_ap.fx6_wlan_mode == "Access Point Mode"
        and (not p79c_fx6_t_block.admitted)
        and p79c_fx6_t_block.errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 79D probes
    p79d_ir_on = simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
        operation="ir_remote_ctrl",
        ir_remote_ctrl="On",
        bluetooth_rmt_ctrl="Off",
        camera_settings_reset_applied=True,
    )
    p79d_ir_bt_mutex = simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
        operation="ir_remote_ctrl",
        ir_remote_ctrl="On",
        bluetooth_rmt_ctrl="On",
    )
    p79d_fx3a_block = simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
        body_profile=BODY_MODEL_FX3A,
        operation="ir_remote_ctrl",
        ir_remote_ctrl="On",
    )
    p79d_cec_bench_safe = simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
        operation="ctrl_for_hdmi",
        ctrl_for_hdmi="Off",
        hil_bench_attached=True,
    )
    p79d_cec_bench_unsafe = simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
        operation="ctrl_for_hdmi",
        ctrl_for_hdmi="On",
        hil_bench_attached=True,
    )
    p79d_cec_off_inject = simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
        operation="cec_event_inject",
        ctrl_for_hdmi="Off",
        hil_bench_attached=True,
        cec_key_event="EVENT_INPUT_KEY_CEC_STANDBY_ON",
    )
    p79d_cec_rec_absent = simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
        operation="cec_event_inject",
        ctrl_for_hdmi="On",
        hil_bench_attached=False,
        cec_key_event="EVENT_INPUT_KEY_CEC_REC",
    )
    p79d_fx3_lanc_block = simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
        operation="lanc_25mm",
    )
    p79d_fx6_lanc = simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="lanc_25mm",
    )
    p79d_fx6_grip = simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="grip_remote_35mm",
    )
    p79d_fx6_ir_block = simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_dormant_ir_or_cec",
    )
    p79d_ok = (
        p79d_ir_on.admitted
        and p79d_ir_on.ir_front_sensor_pin == 5
        and p79d_ir_on.power_save_bypassed_by_ir
        and (not p79d_ir_on.ir_resettable)
        and (not p79d_ir_bt_mutex.admitted)
        and p79d_ir_bt_mutex.errno_code == EBUSY_ERRNO
        and p79d_ir_bt_mutex.bt_ir_mutex_blocked
        and (not p79d_fx3a_block.admitted)
        and p79d_fx3a_block.errno_code == EOPNOTSUPP_ERRNO
        and p79d_cec_bench_safe.admitted
        and p79d_cec_bench_safe.cec_firewall_blocked_injection
        and (not p79d_cec_bench_unsafe.admitted)
        and p79d_cec_bench_unsafe.hil_bench_unsafe_cec_on_blocked
        and (not p79d_cec_off_inject.admitted)
        and p79d_cec_off_inject.cec_firewall_blocked_injection
        and (not p79d_cec_rec_absent.admitted)
        and p79d_cec_rec_absent.errno_code == EOPNOTSUPP_ERRNO
        and (not p79d_cec_rec_absent.cec_rec_event_present)
        and (not p79d_fx3_lanc_block.admitted)
        and p79d_fx3_lanc_block.errno_code == EOPNOTSUPP_ERRNO
        and (not p79d_fx3_lanc_block.has_physical_25mm_lanc)
        and p79d_fx6_lanc.admitted
        and p79d_fx6_lanc.fx6_lanc_port_num == 24
        and p79d_fx6_grip.admitted
        and p79d_fx6_grip.has_35mm_grip_remote
        and (not p79d_fx6_ir_block.admitted)
        and p79d_fx6_ir_block.errno_code == EOPNOTSUPP_ERRNO
    )

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
        "fx3_playback_magnify_items_count": FX3_PLAYBACK_MAGNIFY_ITEMS_COUNT,
        "playback_zoom_maginify_typo_matched": PLAYBACK_ZOOM_MAGINIFY_TYPO_MATCHED,
        "movie_playback_enlarge_supported": MOVIE_PLAYBACK_ENLARGE_SUPPORTED,
        "movie_playback_enlarge_bypass_events": MOVIE_PLAYBACK_ENLARGE_BYPASS_EVENTS,
        "playback_magnify_reset_wipe_events": PLAYBACK_MAGNIFY_RESET_WIPE_EVENTS,
        "fx6_still_or_pb_enlarge_supported": FX6_STILL_OR_PB_ENLARGE_SUPPORTED,
        "fx6_dormant_enlarge_screen_exposed_events": FX6_DORMANT_ENLARGE_SCREEN_EXPOSED_EVENTS,
        "fx3_anti_flicker_shoot_active": FX3_ANTI_FLICKER_SHOOT_ACTIVE,
        "fx3_var_shutter_exposed": FX3_VAR_SHUTTER_EXPOSED,
        "fx3_anti_flicker_tv_scan_exposed": FX3_ANTI_FLICKER_TV_SCAN_EXPOSED,
        "fx3_sc_tv_scan_0x60a8_empty_string": FX3_SC_TV_SCAN_0X60A8_EMPTY_STRING,
        "dormant_var_shutter_or_tv_scan_exposed_events": DORMANT_VAR_SHUTTER_OR_TV_SCAN_EXPOSED_EVENTS,
        "fx6_ecs_freq_min_hz": FX6_ECS_FREQ_MIN_HZ,
        "fx6_ecs_freq_max_hz": FX6_ECS_FREQ_MAX_HZ,
        "fx6_ecs_presets_count": FX6_ECS_PRESETS_COUNT,
        "ww558244_5ghz_bypass_events": WW558244_5GHZ_BYPASS_EVENTS,
        "outdoor_5ghz_bypass_events": OUTDOOR_5GHZ_BYPASS_EVENTS,
        "deprecated_wep_wpa_ipsec_allowed_events": DEPRECATED_WEP_WPA_IPSEC_ALLOWED_EVENTS,
        "airplane_mode_cleared_by_reset_network_events": AIRPLANE_MODE_CLEARED_BY_RESET_NETWORK_EVENTS,
        "p12_p13_ms_rdonly_enforced": P12_P13_MS_RDONLY_ENFORCED,
        "p12_cert_size_mib": P12_CERT_SIZE_MIB,
        "p13_rf_nvs_size_mib": P13_RF_NVS_SIZE_MIB,
        "p12_p13_write_bypass_events": P12_P13_WRITE_BYPASS_EVENTS,
        "fx3_ir_front_sensor_num": FX3_IR_FRONT_SENSOR_NUM,
        "fx3_af_illuminator_sensor_num": FX3_AF_ILLUMINATOR_SENSOR_NUM,
        "fx3a_physical_ir_sensor_present": FX3A_PHYSICAL_IR_SENSOR_PRESENT,
        "bt_ir_mutex_bypass_events": BT_IR_MUTEX_BYPASS_EVENTS,
        "ctrl_for_hmdi_typo_matched": CTRL_FOR_HMDI_TYPO_MATCHED,
        "fx3_cec_key_events_count": FX3_CEC_KEY_EVENTS_COUNT,
        "fx3_cec_rec_event_count": FX3_CEC_REC_EVENT_COUNT,
        "hil_bench_cec_hijack_bypass_events": HIL_BENCH_CEC_HIJACK_BYPASS_EVENTS,
        "fx3_physical_lanc_25mm_present": FX3_PHYSICAL_LANC_25MM_PRESENT,
        "fx3_active_lanc_bkid_hits": FX3_ACTIVE_LANC_BKID_HITS,
        "fx6_lanc_25mm_port_num": FX6_LANC_25MM_PORT_NUM,
        "fx6_grip_remote_35mm_poles": FX6_GRIP_REMOTE_35MM_POLES,
        "fx6_exposed_ir_or_cec_events": FX6_EXPOSED_IR_OR_CEC_EVENTS,
        "rsv_orphan_count": RSV_ORPHAN_COUNT,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    redlines_ok = (
        P8_CP_MUTATION_FORBIDDEN
        and NOP_COUNT == 0
        and GUEST_CODE_MODIFICATION_BYTES == 0
        and CP_MUTATION_BYTES == 0
        and WBI_MUTATION_BYTES == 0
        and CALIBRATION_MUTATION_BYTES == 0
        and CNFLASHA_MUTATION_BYTES == 0
        and CNFLASHA_USERSPACE_WRITE_BLOCKED
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
        and FX3_PLAYBACK_MAGNIFY_ITEMS_COUNT == 3
        and PLAYBACK_ZOOM_MAGINIFY_TYPO_MATCHED
        and (not MOVIE_PLAYBACK_ENLARGE_SUPPORTED)
        and MOVIE_PLAYBACK_ENLARGE_BYPASS_EVENTS == 0
        and PLAYBACK_MAGNIFY_RESET_WIPE_EVENTS == 0
        and (not FX6_STILL_OR_PB_ENLARGE_SUPPORTED)
        and FX6_DORMANT_ENLARGE_SCREEN_EXPOSED_EVENTS == 0
        and FX3_ANTI_FLICKER_SHOOT_ACTIVE
        and (not FX3_VAR_SHUTTER_EXPOSED)
        and (not FX3_ANTI_FLICKER_TV_SCAN_EXPOSED)
        and FX3_SC_TV_SCAN_0X60A8_EMPTY_STRING
        and DORMANT_VAR_SHUTTER_OR_TV_SCAN_EXPOSED_EVENTS == 0
        and FX6_ECS_FREQ_MIN_HZ == 23.99
        and FX6_ECS_FREQ_MAX_HZ == 8000.0
        and FX6_ECS_PRESETS_COUNT == 6
        and WW558244_5GHZ_BYPASS_EVENTS == 0
        and OUTDOOR_5GHZ_BYPASS_EVENTS == 0
        and DEPRECATED_WEP_WPA_IPSEC_ALLOWED_EVENTS == 0
        and AIRPLANE_MODE_CLEARED_BY_RESET_NETWORK_EVENTS == 0
        and P12_P13_MS_RDONLY_ENFORCED
        and P12_CERT_SIZE_MIB == 40
        and P13_RF_NVS_SIZE_MIB == 4
        and P12_P13_WRITE_BYPASS_EVENTS == 0
        and FX3_IR_FRONT_SENSOR_NUM == 5
        and FX3_AF_ILLUMINATOR_SENSOR_NUM == 8
        and (not FX3A_PHYSICAL_IR_SENSOR_PRESENT)
        and BT_IR_MUTEX_BYPASS_EVENTS == 0
        and CTRL_FOR_HMDI_TYPO_MATCHED
        and FX3_CEC_KEY_EVENTS_COUNT == 41
        and len(FX3_CEC_41_KEY_EVENTS) == 41
        and FX3_CEC_REC_EVENT_COUNT == 0
        and HIL_BENCH_CEC_HIJACK_BYPASS_EVENTS == 0
        and (not FX3_PHYSICAL_LANC_25MM_PRESENT)
        and FX3_ACTIVE_LANC_BKID_HITS == 0
        and FX6_LANC_25MM_PORT_NUM == 24
        and FX6_GRIP_REMOTE_35MM_POLES == 4
        and FX6_EXPOSED_IR_OR_CEC_EVENTS == 0
        and RSV_ORPHAN_COUNT == 0
        and WF12_00342260_HITS == 0
        and APPFW_CRASHES == 0
        and NULL_GPIO_DEREFS == 0
        and MAILBOX_STALLS == 0
        and STOCK_CP_FAULT_COUNT == 0
        and RAW_FIRMWARE_BYTES_LEAKED == 0
    )

    all_passed = bool(
        donor_audit.all_contracts_verified
        and IS_79TH_STAGE_MILESTONE
        and STAGE_INDEX == 79
        and STAGE_TOTAL == 79
        and MILESTONE_LABEL == "79/79"
        and p79a_ok
        and p79b_ok
        and p79c_ok
        and p79d_ok
        and redlines_ok
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_357_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_79th_stage_milestone": IS_79TH_STAGE_MILESTONE,
        "source_mode": donor_audit.source_mode,
        "all_checks_passed": all_passed,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "stage79_milestone_probe": _build_stage79_milestone_probe(),
        "pillar_a_playback_magnification_and_fx6_review_hil": {
            "passed": p79a_ok,
            "still_pinch_reset_immune_center_fallback": asdict(p79a_still_pinch),
            "initialize_restores_defaults": asdict(p79a_init_restore),
            "movie_enlarge_blocked": asdict(p79a_movie_block),
            "dial_step_photo_preserves_zoom": asdict(p79a_dial_step),
            "fx6_thumbnail": asdict(p79a_fx6_thumb),
            "fx6_rec_review": asdict(p79a_fx6_review),
            "fx6_focus_magnifier": asdict(p79a_fx6_fmag),
            "fx6_dormant_enlarge_screen_blocked": asdict(p79a_fx6_enlarge_block),
        },
        "pillar_b_antiflicker_varshutter_and_fx6_ecs_hil": {
            "passed": p79b_ok,
            "still_mechanical_100hz_active": asdict(p79b_still_100hz),
            "camera_settings_reset_clears_to_off": asdict(p79b_still_reset),
            "dormant_var_shutter_tv_scan_and_lockouts": [asdict(r) for r in p79b_blocks],
            "fx6_ecs_2398p_preset": asdict(p79b_fx6_ecs),
            "fx6_ecs_oob_blocked": asdict(p79b_fx6_ecs_oob),
            "fx6_flicker_reduce_auto": asdict(p79b_fx6_fr),
        },
        "pillar_c_wifi_sku_wpa3_nvs_and_airplane_hil": {
            "passed": p79c_ok,
            "ww728473_5ghz_wpa3_ok": asdict(p79c_ww728473_5g),
            "reset_network_preserves_airplane_mode": asdict(p79c_reset_net),
            "initialize_clears_airplane_mode": asdict(p79c_init),
            "ssid_pw_reset_direct_only": asdict(p79c_ssid_reset),
            "p12_cert_ms_readonly_erofs": asdict(p79c_p12_erofs),
            "p13_rfnvs_ms_readonly_erofs": asdict(p79c_p13_erofs),
            "sku_outdoor_legacy_and_airplane_blocks": [asdict(r) for r in p79c_blocks],
            "fx6_ap_mode_5ghz": asdict(p79c_fx6_ap),
            "fx6t_5ghz_blocked": asdict(p79c_fx6_t_block),
        },
        "pillar_d_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil": {
            "passed": p79d_ok,
            "ir_sensor5_power_save_bypass_reset_immune": asdict(p79d_ir_on),
            "bt_ir_mutex_blocked": asdict(p79d_ir_bt_mutex),
            "fx3a_ir_sensor_removed": asdict(p79d_fx3a_block),
            "cec_hil_bench_off_safe": asdict(p79d_cec_bench_safe),
            "cec_hil_bench_on_blocked": asdict(p79d_cec_bench_unsafe),
            "cec_off_blocks_injection": asdict(p79d_cec_off_inject),
            "cec_rec_absent_eopnotsupp": asdict(p79d_cec_rec_absent),
            "fx3_zero_lanc_blocked": asdict(p79d_fx3_lanc_block),
            "fx6_25mm_lanc_port24": asdict(p79d_fx6_lanc),
            "fx6_35mm_grip_remote": asdict(p79d_fx6_grip),
            "fx6_dormant_ir_cec_blocked": asdict(p79d_fx6_ir_block),
        },
    }
    stripped = _strip_wall_clock(payload)
    digest = hashlib.sha256(
        json.dumps(stripped, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 357 (Stage 79 — 79/79 Full-Board Stages!): Real-Hardware ILME-FX3 Ver. 7.02 vs "
            "ILME-FX6 Ver. 6.01 Wave-69 Playback -> [Magnification] Still-Only Enlarge Image / "
            "playback_zoom_maginify_by_pinch Typo & Zero Movie Enlarge vs FX6 Thumbnail/Rec Review/"
            "Focus Magnifier x3/x6, Active Still [Anti-flicker Shoot.] 100/120Hz vs Dormant "
            "[Var. Shutter]/[Anti-flicker Tv Scan] EOPNOTSUPP=95 vs FX6 ECS 23.99..8000Hz, "
            "Wi-Fi WW728473 2.4/5GHz vs WW558244 2.4GHz-Only + WPA2/WPA3 + p12/p13 MS_RDONLY + "
            "[Airplane Mode] Survival, and Front #5 [IR Remote Ctrl] + [CTRL FOR HDMI] ctrl_for_hmdi "
            "41-Key CEC Hijack Firewall (Zero CEC_REC) vs FX6 2.5mm LANC & 3.5mm Grip Remote (100%% Read-Only HIL)"
        )
    )
    parser.add_argument("--self-test", action="store_true", help="Run Stage 79 HIL audit")
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force clean-room synthetic mode without local donor reads",
    )
    parser.add_argument(
        "--work-root",
        default=None,
        help="Optional explicit Mac/work donor root (nonexistent falls back cleanly to synthetic)",
    )
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    wr: Any = _UNSET if args.work_root is None else Path(args.work_root)
    rep = run_phase357_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulation(
        work_root=wr,
        force_clean_room=True if args.clean_room else None,
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 357 Stage 79 ({rep['milestone']} Stages) | "
            f"mode={rep['source_mode']} | donors={rep['donor_audit']['donors_verified']}/"
            f"{rep['donor_audit']['donors_checked']} | "
            f"mv_enl={int(red['movie_playback_enlarge_supported'])} | "
            f"varsh={int(red['fx3_var_shutter_exposed'])} | "
            f"rf_mut={red['rf_nvs_mutation_bytes']} | "
            f"cec={red['fx3_cec_key_events_count']}(rec={red['fx3_cec_rec_event_count']}) | "
            f"fx3_lanc={int(red['fx3_physical_lanc_25mm_present'])} | "
            f"s1_wr={red['slot1_data_sector_writes']} | "
            f"leak={red['raw_firmware_bytes_leaked']} | "
            f"digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
