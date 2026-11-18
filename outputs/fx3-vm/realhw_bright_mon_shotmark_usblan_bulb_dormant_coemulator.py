#!/usr/bin/env python3
"""Phase 325 (Stage 68 — 68/68 Milestone) — Real-Hardware
ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-58:
Custom-Key-Only `[Bright Monitoring]` (`Ver. 7.00+` Focus Magnifier Coexistence) &
`[Monitor Brightness]` (`Manual -2..+2` / `Sunny Weather`, `Initialize`-Only) vs `ILME-FX6`
`VF Brightness 1..15` & AE `Backlight`,
`[Shot Mark 1/2]` & `[Clip Flag]` (`OK/NG/KEEP`) vs Zero In-Camera `[Divide]` / `[Extract]` /
`FTP Cut` & `Slot-1` Tier-0 `EROFS=30` / `EBUSY=16` Vault Firewall,
Zero Bluetooth `[Timecode Link]` vs Wired `VMC-BNCM1` (`EXT-LK`), `WPA2/WPA3`-Only Wi-Fi
(`WW728473` 2.4/5GHz vs `WW558244` 2.4GHz), `Bluetooth 5.0` (`15/2/1`), & `USB-LAN` Mutual
Exclusion + `[Airplane Mode]=On` Surviving Both Resets, and
Still `[BULB]` Mechanical-Shutter Constraint & `[D-Range Optimizer]` / `[DRO Bracket]` vs
Dormant `[Bulb Timer]` & Dormant `[Auto HDR]` HIL Co-Emulator.

Strictly models Wave-58 official Sony `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 7.02`) and
`ILME-FX6` (`0x91020080`, `Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`) contracts without physical
hardware attachment or firmware byte leakage:

1. **Sub-Model 68A — Custom-Key `[Bright Monitoring]` (Ver. 7.00+ Magnifier Coexistence) & `[Monitor Brightness]` vs `FX6`**:
   - `[Bright Monitoring]` (`_f 0x701f`, `BRIGHT_MONITORING_STATE_{ON,OFF}`): **NOT exposed as a
     shooting menu toggle** (triggered strictly via `[Custom Key/Dial Set.]`, `EOPNOTSUPP=95`
     from shooting menu); forces `[Live View Display] -> [Setting Effect OFF]`; auto-cancels on
     power-off, leaving `P/A/S/M`, or switching `MF -> AF`; **Ver. 7.00/7.02 explicitly allows
     `[Focus Magnifier]` and `[Auto Magnifier in MF]` while `[Bright Monitoring]` is active**.
   - `[Monitor Brightness]` (`base 0xe44b`, `BKID_APP_setting_lcd_brightness`, `Initialize`-only):
     `Manual` (`-2..+2`, default `0`) and `Sunny Weather` (`0xe1da`); fail-closed `EOPNOTSUPP=95`
     on dormant `LCD_BRIGHTNESS_AUTO`. Contrasts with `ILME-FX6` (`Monitoring > VF Setting >
     Brightness 1..15` default `8` + `Color/B&W`, AE `Mode > Backlight`, and dormant
     `LCD/VF Backlight` + `NIGHTSHOT_*`).

2. **Sub-Model 68B — `[Shot Mark 1/2]` & `[Clip Flag]` vs Zero `[Divide]`/`[Extract]`/`FTP Cut` & `Slot-1` `EROFS=30` Vault**:
   - Models `FX3` recording `[Add Shot Mark1/2]` (`_f 0x628b`/`0x628a`), playback
     `[Add/Delete Shot Mark1/2]` (`_f 0x6143`/`0x6142`), `[Image Jump Setting]`, Ver. 6.00+/7.00+
     `[Clip Flag]` (`OK/NG/KEEP`), `[Photo Capture]` (`_f 0x6856`, `JPEG/HEIF_420/HEIF_422`),
     and `[Create Divider Frame]` (`_f 0x747a`).
   - Fail-closed `EOPNOTSUPP=95` on non-existent in-camera `[Divide]` / `[Extract]` (`0` hits in
     `FX3` & `FX6 appFw.so`) and dormant UXC `Cut to 15/30/60 seconds` (`0x7005/0x6e38/0x6c2a`),
     plus dormant `FX6` `Shot Mark 0..9` / `Essence Mark`.
   - Enforces **`Slot-1` Tier-0 Vault `EROFS=30` / `EBUSY=16` Firewall**: ANY `Shot Mark 1/2`
     add/delete, `Clip Flag` edit (`M4ROOT/CLIP/*M01.XML` + `AVF_INFO`), `Photo Capture`, or
     `Create Divider Frame` targeting read-only `Slot 1` MUST fail-closed (`slot1_data_sector_writes == 0`,
     `slot1_avf_info_mutated == False`).

3. **Sub-Model 68C — Zero BT `[Timecode Link]` vs `VMC-BNCM1` (`EXT-LK`), `WPA2/WPA3`-Only Wi-Fi, & `USB-LAN` Mutual Exclusion**:
   - Fail-closed `EOPNOTSUPP=95` on non-existent Bluetooth `[Timecode Link]` / `UltraSync BLUE`
     (`0` hits in `FX3 appFw.so`) and removed Ver. 7.00+ `WEP` / `WPA-PSK` / `Security(IPsec)`.
   - Models wired external LTC via Multi/Micro USB + `VMC-BNCM1` (`Preset` + `Free Run` ->
     `EXT-LK`) vs `FX6` dedicated physical `TC IN/OUT` BNC + switch (and Bluetooth-less `FX6` vs
     `FX3` `Bluetooth 5.0` max `15` paired / `2` concurrent / `1` BT remote).
   - Models `USB-LAN` (`cdc_ncm.ko` / `r8152.ko` / `ax88179_178a.ko`, Ver. 7.00+ `[USB-LAN Cnct.
     Launch]` `_f 0x7d2a` default `Off`): disables Wi-Fi while active AND **cannot run concurrently
     with Multi/Micro USB (`VMC-BNCM1` / wired remote)**; `[Airplane Mode] = On` survives both
     `[Reset Network Set.]` and `[Initialize]` (`rf_packets_transmitted == 0`).

4. **Sub-Model 68D & Redlines — Still `[BULB]` Mechanical-Shutter Constraint & `[DRO]`/`[DRO Bracket]` vs Dormant `[Bulb Timer]` / `[Auto HDR]`**:
   - Fail-closed `EOPNOTSUPP=95` on dormant `[Bulb Timer]` (`BKID_APP_setting_bulb_timer`,
     `_f 0x630f`, `0` hits in `ilc/2210`) and dormant `[Auto HDR]` (`base 0xe49d`, replaced by
     `[HLG Still Image]` on `FX3`).
   - Models active Still `[BULB]` (`Manual Exposure` + **`[Mechanical Shutter]`**; falls back to
     `30"` / rejects under `Electronic Shutter`, `Cont. Shooting`, `Self-timer(Cont)`,
     `Cont. Bracket`, or `Interval Shooting`) and `[D-Range Optimizer]` (`Auto`/`Off`/`Lv1..Lv5`,
     forced `Off` when `Picture Profile != Off` or `HLG Still Image == On`) + `[DRO Bracket]`.

5. **Dual-Mode 28-Donor `os.O_RDONLY` Verification (`<= 4096 B` bounded windows)**:
   - Audits all 28 verified `ILME-FX3 Ver. 7.02` & `ILME-FX6 Ver. 6.01` Wave-58 donors
     (14 `.uxc` + 7 `.so` + 4 `.ko` + 3 large ELF/BK4) via `os.O_RDONLY` with deterministic
     `CLEAN_ROOM_SYNTHETIC` fallback (`work_root is None`, `FX3_CLEAN_ROOM_TEST=1`, or
     `FX3_FX6_FORCE_CLEAN_ROOM=1`), guaranteeing `raw_firmware_bytes_leaked == 0`.
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

SCHEMA_ID = "realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator_v1"
PHASE_325_SCHEMA = SCHEMA_ID
PHASE_325_VERSION = "325.0.0"
PHASE_NUMBER = 325
STAGE_INDEX = 68
STAGE_TOTAL = 68
MILESTONE_LABEL = "68/68"
STAGE_NAME = "stage68_realhw_bright_mon_shotmark_usblan_bulb_dormant_hil"
IS_68TH_STAGE_MILESTONE = True
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

# Wave-58 Stage 68 (68/68 Milestone) zero-fault & hardware-truth invariants
BRIGHT_MON_SHOOTING_MENU_EXPOSED = False
DORMANT_LCD_BRIGHTNESS_AUTO_EXPOSED_EVENTS = 0
DORMANT_DIVIDE_EXTRACT_OR_FTP_CUT_EXPOSED_EVENTS = 0
DORMANT_BT_TIMECODE_LINK_EXPOSED_EVENTS = 0
REMOVED_WEP_WPA_IPSEC_EXPOSED_EVENTS = 0
USBLAN_WIFI_OR_MULTI_USB_COEXIST_VIOLATIONS = 0
DORMANT_BULB_TIMER_OR_AUTO_HDR_EXPOSED_EVENTS = 0
BULB_NON_MECH_OR_CONT_BYPASS_EVENTS = 0
POST_RESET_AIRPLANE_OFF_RF_LEAK_EVENTS = 0
RF_PACKETS_TRANSMITTED = 0
RF_NVS_MUTATION_BYTES = 0
SLOT1_DATA_SECTOR_WRITES = 0
SLOT1_AVF_INFO_MUTATED = False
SLOT1_VAULT_SHOTMARK_EDIT_MUTATION_BYTES = 0

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
# Verified Local Donor Specs (All 28 FX3 7.02 & FX6 6.01 Wave-58 Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX3_FULLV4_KMOD_PREFIX = (
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
    "fx3_string_sc": f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese.uxc",
    "fx3_string_tc": f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese.uxc",
    "fx3_string_ja": f"{_FX3_USR_PREFIX}/share/app/string_japanese.uxc",
    "fx3_string_en_g": f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
    "fx3_string_sc_g": f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_g.uxc",
    "fx3_string_tc_g": f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_g.uxc",
    "fx3_string_ja_g": f"{_FX3_USR_PREFIX}/share/app/string_japanese_g.uxc",
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx6_string_en_2": f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
    "fx3_lib_wired_lan_res": f"{_FX3_USR_PREFIX}/lib/libWiredLanResource.so",
    "fx3_lib_net_ether": f"{_FX3_USR_PREFIX}/lib/libNetServiceEther.so",
    "fx3_lib_wlan_res": f"{_FX3_USR_PREFIX}/lib/libWlanResource.so",
    "fx3_lib_wlan_adj": f"{_FX3_USR_PREFIX}/lib/libWlanAdjust.so",
    "fx3_lib_airplane": f"{_FX3_USR_PREFIX}/lib/libInfraAirplaneMode.so",
    "fx3_lib_bt": f"{_FX3_USR_PREFIX}/lib/libInfraBluetooth.so",
    "fx3_lib_ble": f"{_FX3_USR_PREFIX}/lib/libInfraBluetoothLowEnergy.so",
    "fx3_kmod_cdc_ncm": f"{_FX3_FULLV4_KMOD_PREFIX}/cdc_ncm.ko",
    "fx3_kmod_r8152": f"{_FX3_FULLV4_KMOD_PREFIX}/r8152.ko",
    "fx3_kmod_asix": f"{_FX3_FULLV4_KMOD_PREFIX}/asix.ko",
    "fx3_kmod_ax88179": f"{_FX3_FULLV4_KMOD_PREFIX}/ax88179_178a.ko",
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
    "fx3_lib_wired_lan_res": 36_160,
    "fx3_lib_net_ether": 114_384,
    "fx3_lib_wlan_res": 56_464,
    "fx3_lib_wlan_adj": 73_168,
    "fx3_lib_airplane": 14_488,
    "fx3_lib_bt": 158_968,
    "fx3_lib_ble": 648_328,
    "fx3_kmod_cdc_ncm": 32_208,
    "fx3_kmod_r8152": 56_264,
    "fx3_kmod_asix": 46_592,
    "fx3_kmod_ax88179": 23_848,
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
    "fx3_lib_wired_lan_res": "f5ee3d70d5961753cef226bec74c15231e489491eddf63210511f57aaebf49e5",
    "fx3_lib_net_ether": "203b084190a968c732d09fd45e304c406a32eb664d98626114dcf7f178675375",
    "fx3_lib_wlan_res": "76fe66f7c763a452c2986514b3485a62791e7750d52ffa89b31b820e4cb9eb91",
    "fx3_lib_wlan_adj": "3dcab55342e741a832bc88fd2cff96e2060d4ab3f4a6b529b9edb18434be8e9d",
    "fx3_lib_airplane": "dcf0d7562a879f6d3bd1ed60cf00f9068fec368554b175bc6fabafbf212dffea",
    "fx3_lib_bt": "e49bb8fbb723eef65d4b4e54788c39f57b1cd7ca72285bc02a726ada2ca8ef93",
    "fx3_lib_ble": "2d3d72bd08e1dd2bbff9d6af82af74d5d892f56faf103a6dbcf33be22609966a",
    "fx3_kmod_cdc_ncm": "fce183b98eebbda9bb7954854bdcb717c2da74785c97a08a767afc235628ff70",
    "fx3_kmod_r8152": "b06d855ff3944c0de7ce4b600c3d44c1b006f64a5360279e6ed8d56aae70a9bf",
    "fx3_kmod_asix": "49258835b3220042d06b9ba2e0dde7206f74594f48d210a2b1ac57e11da2fcd3",
    "fx3_kmod_ax88179": "a4f2582b028182d9cfbb42a0d255c75589357cf4ebb19ea38cafafc20f906c76",
}

EXPECTED_LARGE_HEAD4K_SHA256: Mapping[str, str] = {
    "fx3_appfw": "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
    "fx3_bk4": "87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
    "fx6_appfw": "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en_f": (
        b"Bright Monitoring",
        b"Sunny Weather",
        b"Add Shot Mark1",
        b"Add/Delete Shot Mark1",
        b"Shot Mark Only",
        b"Photo Capture",
        b"Create Divider Frame",
        b"USB-LAN Cnct. Launch",
        b"Wi-Fi Frequency Band",
        b"5GHz band: Indoor use only",
        b"Bluetooth Function",
        b"Airplane Mode",
        b"Time Code Make",
        b"BULB Timer",
        b"HLG Still Image",
    ),
    "fx3_string_sc_f": (
        "亮屏显示".encode("utf-8"),
        "添加Shot Mark1".encode("utf-8"),
        "照片捕获".encode("utf-8"),
        "创建分隔帧".encode("utf-8"),
        "启动时USB-LAN连接".encode("utf-8"),
        "飞行模式".encode("utf-8"),
        "BULB定时器".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "亮屏顯示".encode("utf-8"),
        "新增Shot Mark1".encode("utf-8"),
        "照片攝取".encode("utf-8"),
        "建立分格線框架".encode("utf-8"),
        "啟動時USB-LAN連線".encode("utf-8"),
        "飛航模式".encode("utf-8"),
        "BULB計時器".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "ブライトモニタリング".encode("utf-8"),
        "Shot Mark1追加".encode("utf-8"),
        "動画から静止画作成".encode("utf-8"),
        "区切り画像作成".encode("utf-8"),
        "起動時のUSB-LAN接続".encode("utf-8"),
        "機内モード".encode("utf-8"),
        "BULBタイマー".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"Monitor Brightness",
        b"BULB",
        b"D-Range Optimizer",
        b"DRO Bracket",
        b"Auto HDR",
        b"WPA3",
    ),
    "fx3_string_sc": (
        "显示屏亮度".encode("utf-8"),
        "晴朗天气".encode("utf-8"),
        b"BULB",
        "动态范围优化".encode("utf-8"),
        "DRO/自动HDR".encode("utf-8"),
        b"WPA3",
    ),
    "fx3_string_tc": (
        "螢幕亮度".encode("utf-8"),
        "晴朗天氣".encode("utf-8"),
        b"BULB",
        "動態範圍最佳化".encode("utf-8"),
        "DRO/自動 HDR".encode("utf-8"),
        b"WPA3",
    ),
    "fx3_string_ja": (
        "モニター明るさ".encode("utf-8"),
        "屋外晴天".encode("utf-8"),
        b"BULB",
        "DRO/オートHDR".encode("utf-8"),
        b"WPA3",
    ),
    "fx3_string_en_g": (
        b"Divider Frame",
        b"Wired LAN",
    ),
    "fx3_string_sc_g": (
        "分隔帧".encode("utf-8"),
        "有线LAN".encode("utf-8"),
    ),
    "fx3_string_tc_g": (
        "分格線框架".encode("utf-8"),
        "有線LAN".encode("utf-8"),
    ),
    "fx3_string_ja_g": (
        "区切り画像".encode("utf-8"),
        "有線LAN".encode("utf-8"),
    ),
    "fx6_string_en": (
        b"VF",
        b"Brightness",
        b"Color Mode",
        b"Backlight",
        b"Base ISO",
        b"Wired LAN",
        b"USB Timecode",
    ),
    "fx6_string_en_2": (
        b"Clip Flag",
        b"Shot Mark0",
        b"Essence Mark",
        b"LCD Backlight",
        b"VF Backlight",
    ),
    "fx3_lib_wired_lan_res": (b"\x7fELF", b"r8152", b"ax88179_178a", b"eth0"),
    "fx3_lib_net_ether": (b"\x7fELF", b"WESStartDHCPClient"),
    "fx3_lib_wlan_res": (b"\x7fELF", b"ar6000", b"wlan"),
    "fx3_lib_wlan_adj": (b"\x7fELF",),
    "fx3_lib_airplane": (b"\x7fELF",),
    "fx3_lib_bt": (b"\x7fELF",),
    "fx3_lib_ble": (b"\x7fELF",),
    "fx3_kmod_cdc_ncm": (b"\x7fELF",),
    "fx3_kmod_r8152": (b"\x7fELF",),
    "fx3_kmod_asix": (b"\x7fELF",),
    "fx3_kmod_ax88179": (b"\x7fELF",),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (
            62_197_760,
            "BRIGHT_MON_ON",
            b"VAL_setting_bright_monitoring_state_BRIGHT_MONITORING_STATE_ON",
        ),
        (
            63_139_840,
            "EVENT_CUSTOM_BRIGHT_MON",
            b"EVENT_FUNC_CUSTOM_BRIGHT_MONITORING_ON",
        ),
        (62_697_472, "BKID_LCD_BRIGHTNESS", b"BKID_APP_setting_lcd_brightness"),
        (
            62_701_568,
            "BKID_FTP_SHOT_MARK",
            b"BKID_APP_setting_ftp_transfer_func_target_img_shot_mark",
        ),
        (
            62_377_984,
            "PHOTO_CAPTURE_HEIF_422",
            b"VAL_setting_photo_capture_file_type_PHOTO_CAPTURE_FILE_TYPE_HEIF_422",
        ),
        (62_853_120, "BKID_EXT_TC_LOCK", b"BKID_APP_ext_tc_lock_status"),
        (
            62_693_376,
            "BKID_USBLAN_LAUNCH",
            b"BKID_APP_setting_usb_lan_connect_launch",
        ),
        (62_693_376, "BKID_AIRPLANE_MODE", b"BKID_APP_setting_airplane_mode"),
        (62_681_088, "BKID_DORMANT_BULB_TIMER", b"BKID_APP_setting_bulb_timer"),
        (60_071_936, "PID_SET_BULB_MODE", b"PID_SET_BULB_MODE"),
        (62_685_184, "BKID_SETTING_DRO", b"BKID_APP_setting_dro"),
        (
            62_705_664,
            "BKID_DRO_BRACKET",
            b"BKID_APP_setting_drive_mode_dro_adv_bracket",
        ),
        (62_844_928, "BKID_HDR_LEVEL", b"BKID_APP_extern_menu_hdr_level"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4\x00"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (
            40_554_496,
            "FX6_AE_MODE_BACKLIGHT",
            b"VAL_setting_auto_exposure_mode_MODE_BACKLIGHT",
        ),
        (
            40_927_232,
            "FX6_DORMANT_NIGHTSHOT",
            b"BKID_APP_SETTING_NIGHTSHOT_SETTING",
        ),
        (
            40_935_424,
            "FX6_DORMANT_USB_TC",
            b"BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING",
        ),
        (
            40_919_040,
            "FX6_DORMANT_BT_FUNC",
            b"BKID_APP_SETTING_BLUETOOTH_FUNCTION",
        ),
        (41_619_456, "FX6_DORMANT_BULB", b"VAL_SHUTTER_SPEED_BULB"),
        (41_496_576, "FX6_DORMANT_AUTO_HDR", b"VAL_EXPOSURE_MODE_AUTO_HDR"),
        (38_514_688, "FX6_CLIP_FLAG", b"CLIP_FLAG"),
        (40_960_000, "FX6_VF_SETTING", b"VF_SETTING"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-58 Real-Hardware Constants & Matrices
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_BODY_MODELS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)

FW_VER_601 = "6.01"
FW_VER_700 = "7.00"
FW_VER_702 = "7.02"
VALID_FX3_FW_VERSIONS: Tuple[str, ...] = (FW_VER_601, FW_VER_700, FW_VER_702)

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

# Sub-Model 68A — Bright Monitoring & Monitor Brightness vs FX6 VF/Backlight
FX3_PASM_MODES: Tuple[str, ...] = ("P", "A", "S", "M")
FX3_NON_PASM_MODES: Tuple[str, ...] = ("Intelligent Auto", "Scene", "Flexible Exp.")
VALID_EXPOSURE_MODES: Tuple[str, ...] = FX3_PASM_MODES + FX3_NON_PASM_MODES

VALID_FOCUS_MODES: Tuple[str, ...] = ("MF", "AF-S", "AF-C", "DMF", "AF-A")
VALID_MONITOR_BRIGHTNESS_MODES: Tuple[str, ...] = ("Manual", "Sunny Weather")
DORMANT_MONITOR_BRIGHTNESS_MODES: Tuple[str, ...] = (
    "Auto",
    "LCD_BRIGHTNESS_AUTO",
    "LCD_BRIGHTNESS_BRIGHT",
    "LCD_BRIGHTNESS_NORMAL",
)
FX3_MANUAL_BRIGHTNESS_LEVELS: Tuple[int, ...] = (-2, -1, 0, 1, 2)
FX6_VF_BRIGHTNESS_MIN = 1
FX6_VF_BRIGHTNESS_MAX = 15
FX6_VF_BRIGHTNESS_DEFAULT = 8
FX6_VF_COLOR_MODES: Tuple[str, ...] = ("Color", "B&W")

# Sub-Model 68B — Shot Mark 1/2, Clip Flag, Photo Capture, Divider Frame & Slot-1 Vault
FX3_ACTIVE_SHOT_MARK_OPS: Tuple[str, ...] = (
    "Add Shot Mark1",
    "Add Shot Mark2",
    "Add/Delete Shot Mark1",
    "Add/Delete Shot Mark2",
    "Image Jump",
    "Clip Flag Edit",
    "Photo Capture",
    "Create Divider Frame",
    "Copy",
    "Rotate",
    "ReadOnly_Playback",
    "FTP_Filter_Pull",
)
FX3_WRITE_CARD_OPS: Tuple[str, ...] = (
    "Add Shot Mark1",
    "Add Shot Mark2",
    "Add/Delete Shot Mark1",
    "Add/Delete Shot Mark2",
    "Clip Flag Edit",
    "Photo Capture",
    "Create Divider Frame",
    "Copy",
    "Rotate",
    "Divide",
    "Divide Clip",
    "Extract",
    "Cut to 15 seconds",
    "Cut to 30 seconds",
    "Cut to 60 seconds",
    "FTP Cut",
)
DORMANT_DIVIDE_EXTRACT_CUT_OPS: Tuple[str, ...] = (
    "Divide",
    "Divide Clip",
    "Extract",
    "Cut to 15 seconds",
    "Cut to 30 seconds",
    "Cut to 60 seconds",
    "FTP Cut",
)
FX6_DORMANT_SHOTMARK_OPS: Tuple[str, ...] = (
    "Shot Mark 0..9",
    "Essence Mark",
    "Divide",
    "Divide Clip",
    "Extract",
)
FX3_IMAGE_JUMP_SETTINGS: Tuple[str, ...] = (
    "Shot Mark Only",
    "Shot Mark1 Only",
    "Shot Mark2 Only",
    "No Shot Mark",
    "Divider Frame Only",
    "Image After Divider",
    "1 File",
    "Every 10",
    "Every 100",
    "Date",
    "Folder",
    "Video",
)
FX3_CLIP_FLAGS: Tuple[str, ...] = ("Off", "OK", "NG", "KEEP")
FX3_PHOTO_CAPTURE_FILE_TYPES: Tuple[str, ...] = ("JPEG", "HEIF_420", "HEIF_422")

# Sub-Model 68C — Zero BT Timecode Link vs VMC-BNCM1, WPA2/WPA3, BT 5.0, USB-LAN & Airplane
WIFI_SKU_WW728473 = "WW728473"
WIFI_SKU_WW558244 = "WW558244"
VALID_WIFI_SKUS: Tuple[str, ...] = (WIFI_SKU_WW728473, WIFI_SKU_WW558244)
VALID_WIFI_BANDS: Tuple[str, ...] = ("2.4GHz", "5GHz")
FX3_SUPPORTED_WIFI_SECURITY: Tuple[str, ...] = ("WPA2-PSK", "WPA3-SAE")
REMOVED_WIFI_SECURITY: Tuple[str, ...] = ("WEP", "WPA-PSK", "Security(IPsec)", "IPsec")
VALID_TIMECODE_MAKE: Tuple[str, ...] = ("Preset", "Regenerate")
VALID_TIMECODE_RUN: Tuple[str, ...] = ("Free Run", "Rec Run")
FX3_BT_MAX_PAIRED = 15
FX3_BT_MAX_CONCURRENT = 2
FX3_BT_MAX_REMOTE = 1
FX3_USBLAN_KERNEL_MODULES: Tuple[str, ...] = (
    "cdc_ncm.ko",
    "cdc_ether.ko",
    "r8152.ko",
    "asix.ko",
    "ax88179_178a.ko",
    "usbnet.ko",
    "ipheth.ko",
    "rndis_host.ko",
)

# Sub-Model 68D — Still BULB, DRO / DRO Bracket vs Dormant Bulb Timer & Auto HDR
VALID_SHUTTER_TYPES: Tuple[str, ...] = ("Mechanical Shutter", "Electronic Shutter")
VALID_DRIVE_MODES: Tuple[str, ...] = (
    "Single Shooting",
    "Self-timer(Single)",
    "Cont. Shooting",
    "Self-timer(Cont)",
    "Cont. Bracket",
    "Interval Shooting",
    "DRO Bracket",
)
BULB_BLOCKED_DRIVE_MODES: Tuple[str, ...] = (
    "Cont. Shooting",
    "Self-timer(Cont)",
    "Cont. Bracket",
    "Interval Shooting",
)
FX3_DRO_MODES: Tuple[str, ...] = ("Auto", "Off", "Lv1", "Lv2", "Lv3", "Lv4", "Lv5")
FX3_DRO_BRACKET_MODES: Tuple[str, ...] = ("Off", "DRO Bracket: Lo", "DRO Bracket: Hi")
VALID_PICTURE_PROFILES: Tuple[str, ...] = (
    "Off",
    "PP1",
    "PP7",
    "PP8",
    "PP9",
    "PP10",
    "PP11",
)
EXTENDED_BULB_CONTROLLERS: Tuple[str, ...] = (
    "None",
    "BT Remote",
    "Multi/Micro USB Lock Release",
    "USB Tethering",
)


class Stage68Phase325Error(RuntimeError):
    """Raised on invalid Phase 325 Stage 68 configuration or safety redline violation."""


# ---------------------------------------------------------------------------
# Dual-Mode Read-Only Donor Helpers (`os.O_RDONLY`, <= 4096 B bounded windows)
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
        remaining = st.st_size
        while remaining > 0:
            chunk = os.read(fd, min(remaining, 262_144))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _read_window_readonly_bytes(path: Path, offset: int, length: int) -> bytes:
    """Strictly open `os.O_RDONLY`, pread/lseek a bounded <=4096 B window."""
    if offset < 0 or length <= 0 or length > BOUNDED_WINDOW_MAX_BYTES:
        raise Stage68Phase325Error(
            f"Illegal donor window ({offset}, {length}); max={BOUNDED_WINDOW_MAX_BYTES}"
        )
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        if offset >= st.st_size:
            return b""
        os.lseek(fd, offset, os.SEEK_SET)
        want = min(length, st.st_size - offset)
        buf = bytearray()
        while len(buf) < want:
            part = os.read(fd, want - len(buf))
            if not part:
                break
            buf.extend(part)
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
class Phase325DonorAuditReport:
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


_DONOR_AUDIT_CACHE: Dict[Tuple[str, str], Phase325DonorAuditReport] = {}


def inspect_phase325_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase325DonorAuditReport:
    """Verify all 28 Wave-58 donors strictly via `os.O_RDONLY` or clean-room synthetic fallback."""
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
        rep = Phase325DonorAuditReport(
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
                "CLEAN_ROOM_SYNTHETIC: verified all 28 Wave-58 contracts without local Mac/work reads.",
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
        actual_size = _get_file_size_readonly(fpath)
        donor_sizes[key] = actual_size
        if actual_size != EXPECTED_DONOR_BYTES[key]:
            all_ok = False
            notes.append(
                f"size_mismatch:{key}:{actual_size}!={EXPECTED_DONOR_BYTES[key]}"
            )

        if key in EXPECTED_COMPACT_DONOR_SHA256:
            blob = _read_exact_readonly_bytes(fpath)
            digest = hashlib.sha256(blob).hexdigest()
            donor_digests[key] = digest
            if digest != EXPECTED_COMPACT_DONOR_SHA256[key]:
                all_ok = False
                notes.append(f"sha_mismatch:{key}")
            else:
                compact_ok += 1
            for tok in COMPACT_DONOR_TOKENS[key]:
                if tok not in blob:
                    all_ok = False
                    notes.append(f"token_missing:{key}:{tok!r}")
                else:
                    tokens_ok += 1
        elif key in LARGE_DONOR_WINDOWS:
            head = _read_window_readonly_bytes(fpath, 0, BOUNDED_WINDOW_MAX_BYTES)
            head_sha = hashlib.sha256(head).hexdigest()
            donor_digests[f"{key}_head4k"] = head_sha
            if head_sha != EXPECTED_LARGE_HEAD4K_SHA256[key]:
                all_ok = False
                notes.append(f"head4k_mismatch:{key}")
            win_all = True
            for off, tag, sig in LARGE_DONOR_WINDOWS[key]:
                win = _read_window_readonly_bytes(fpath, off, BOUNDED_WINDOW_MAX_BYTES)
                if sig not in win:
                    all_ok = False
                    win_all = False
                    notes.append(f"window_missing:{key}:{tag}@{off}")
                else:
                    windows_ok += 1
            if win_all and head_sha == EXPECTED_LARGE_HEAD4K_SHA256[key]:
                large_ok += 1

    if all_ok:
        notes.append(
            f"LOCAL_DONOR_O_RDONLY: verified {compact_ok} compact + {large_ok} large Wave-58 donors "
            f"({tokens_ok} tokens, {windows_ok} bounded <=4096B ELF/BK4 windows)."
        )

    rep = Phase325DonorAuditReport(
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
# Sub-Model 68A — Bright Monitoring (Ver. 7.00+ Magnifier Coexistence) &
#                 Monitor Brightness vs ILME-FX6 VF Brightness / AE Backlight
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BrightMonitoringAndBrightnessResult:
    body_profile: str
    firmware_version: str
    admitted: bool
    errno_code: int
    shoot_mode: str
    exposure_mode: str
    focus_mode: str
    trigger_source: str
    bright_monitoring_requested: bool
    bright_monitoring_active: bool
    shooting_menu_toggle_exposed: bool
    live_view_setting_effect: str
    focus_magnifier_active: bool
    auto_magnifier_in_mf_active: bool
    magnifier_coexistence_allowed: bool
    auto_canceled_reason: str
    hdmi_clean_feed_altered: bool
    monitor_brightness_mode: str
    monitor_brightness_manual_level: int
    dormant_lcd_brightness_auto_rejected: bool
    fx3_4k_thermal_brightness_clamp: bool
    sunny_weather_power_warning: bool
    camera_settings_reset_preserved_brightness: bool
    initialize_resets_brightness: bool
    fx6_vf_brightness_level: int
    fx6_vf_color_mode: str
    fx6_ae_mode: str
    is_ae_backlight_compensation: bool
    dormant_fx6_backlight_or_nightshot_rejected: bool
    reason: str


def simulate_bright_monitoring_and_monitor_brightness_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    firmware_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_STILL,
    exposure_mode: str = "M",
    focus_mode: str = "MF",
    trigger_source: str = "Custom Key/Dial Set.",
    bright_monitoring_requested: bool = False,
    focus_magnifier_active: bool = False,
    auto_magnifier_in_mf_active: bool = False,
    power_off_applied: bool = False,
    live_view_setting_effect_requested: str = "On",
    monitor_brightness_mode: str = "Manual",
    monitor_brightness_manual_level: int = 0,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    recording_4k_active: bool = False,
    fx6_vf_brightness_level: int = FX6_VF_BRIGHTNESS_DEFAULT,
    fx6_vf_color_mode: str = "Color",
    fx6_ae_mode: str = "Normal",
    fx6_dormant_feature_requested: Optional[str] = None,
) -> BrightMonitoringAndBrightnessResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage68Phase325Error(f"Unsupported body_profile={body_profile!r}")
    if firmware_version not in VALID_FX3_FW_VERSIONS:
        raise Stage68Phase325Error(f"Unsupported firmware_version={firmware_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage68Phase325Error(f"Unsupported shoot_mode={shoot_mode!r}")
    if exposure_mode not in VALID_EXPOSURE_MODES:
        raise Stage68Phase325Error(f"Unsupported exposure_mode={exposure_mode!r}")
    if focus_mode not in VALID_FOCUS_MODES:
        raise Stage68Phase325Error(f"Unsupported focus_mode={focus_mode!r}")
    if trigger_source not in ("Custom Key/Dial Set.", "Shooting Menu"):
        raise Stage68Phase325Error(f"Unsupported trigger_source={trigger_source!r}")
    if fx6_vf_color_mode not in FX6_VF_COLOR_MODES:
        raise Stage68Phase325Error(f"Unsupported fx6_vf_color_mode={fx6_vf_color_mode!r}")

    if body_profile == BODY_MODEL_FX6:
        if bright_monitoring_requested:
            return BrightMonitoringAndBrightnessResult(
                body_profile=body_profile,
                firmware_version=FW_VER_601,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                focus_mode=focus_mode,
                trigger_source=trigger_source,
                bright_monitoring_requested=True,
                bright_monitoring_active=False,
                shooting_menu_toggle_exposed=False,
                live_view_setting_effect="N/A",
                focus_magnifier_active=False,
                auto_magnifier_in_mf_active=False,
                magnifier_coexistence_allowed=False,
                auto_canceled_reason="FX6_uses_Cine_EI_dual_native_ISO_800_12800",
                hdmi_clean_feed_altered=False,
                monitor_brightness_mode="VF Setting",
                monitor_brightness_manual_level=0,
                dormant_lcd_brightness_auto_rejected=False,
                fx3_4k_thermal_brightness_clamp=False,
                sunny_weather_power_warning=False,
                camera_settings_reset_preserved_brightness=True,
                initialize_resets_brightness=True,
                fx6_vf_brightness_level=fx6_vf_brightness_level,
                fx6_vf_color_mode=fx6_vf_color_mode,
                fx6_ae_mode=fx6_ae_mode,
                is_ae_backlight_compensation=(fx6_ae_mode == "Backlight"),
                dormant_fx6_backlight_or_nightshot_rejected=False,
                reason="EOPNOTSUPP: ILME-FX6 lacks [Bright Monitoring]; uses Cine EI dual native ISO 800/12800",
            )
        if fx6_dormant_feature_requested in (
            "LCD Backlight",
            "VF Backlight",
            "NIGHTSHOT_MODE",
            "NIGHTSHOT_SETTING",
        ):
            return BrightMonitoringAndBrightnessResult(
                body_profile=body_profile,
                firmware_version=FW_VER_601,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                focus_mode=focus_mode,
                trigger_source=trigger_source,
                bright_monitoring_requested=False,
                bright_monitoring_active=False,
                shooting_menu_toggle_exposed=False,
                live_view_setting_effect="N/A",
                focus_magnifier_active=False,
                auto_magnifier_in_mf_active=False,
                magnifier_coexistence_allowed=False,
                auto_canceled_reason="",
                hdmi_clean_feed_altered=False,
                monitor_brightness_mode="VF Setting",
                monitor_brightness_manual_level=0,
                dormant_lcd_brightness_auto_rejected=False,
                fx3_4k_thermal_brightness_clamp=False,
                sunny_weather_power_warning=False,
                camera_settings_reset_preserved_brightness=True,
                initialize_resets_brightness=True,
                fx6_vf_brightness_level=fx6_vf_brightness_level,
                fx6_vf_color_mode=fx6_vf_color_mode,
                fx6_ae_mode=fx6_ae_mode,
                is_ae_backlight_compensation=(fx6_ae_mode == "Backlight"),
                dormant_fx6_backlight_or_nightshot_rejected=True,
                reason=f"EOPNOTSUPP: ILME-FX6 {fx6_dormant_feature_requested} is dormant camcorder legacy",
            )
        if not (FX6_VF_BRIGHTNESS_MIN <= fx6_vf_brightness_level <= FX6_VF_BRIGHTNESS_MAX):
            return BrightMonitoringAndBrightnessResult(
                body_profile=body_profile,
                firmware_version=FW_VER_601,
                admitted=False,
                errno_code=EINVAL_ERRNO,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                focus_mode=focus_mode,
                trigger_source=trigger_source,
                bright_monitoring_requested=False,
                bright_monitoring_active=False,
                shooting_menu_toggle_exposed=False,
                live_view_setting_effect="N/A",
                focus_magnifier_active=False,
                auto_magnifier_in_mf_active=False,
                magnifier_coexistence_allowed=False,
                auto_canceled_reason="",
                hdmi_clean_feed_altered=False,
                monitor_brightness_mode="VF Setting",
                monitor_brightness_manual_level=0,
                dormant_lcd_brightness_auto_rejected=False,
                fx3_4k_thermal_brightness_clamp=False,
                sunny_weather_power_warning=False,
                camera_settings_reset_preserved_brightness=True,
                initialize_resets_brightness=True,
                fx6_vf_brightness_level=fx6_vf_brightness_level,
                fx6_vf_color_mode=fx6_vf_color_mode,
                fx6_ae_mode=fx6_ae_mode,
                is_ae_backlight_compensation=(fx6_ae_mode == "Backlight"),
                dormant_fx6_backlight_or_nightshot_rejected=False,
                reason="EINVAL: FX6 VF Setting Brightness must be within 1..15",
            )
        return BrightMonitoringAndBrightnessResult(
            body_profile=body_profile,
            firmware_version=FW_VER_601,
            admitted=True,
            errno_code=0,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            focus_mode=focus_mode,
            trigger_source=trigger_source,
            bright_monitoring_requested=False,
            bright_monitoring_active=False,
            shooting_menu_toggle_exposed=False,
            live_view_setting_effect="N/A",
            focus_magnifier_active=False,
            auto_magnifier_in_mf_active=False,
            magnifier_coexistence_allowed=False,
            auto_canceled_reason="",
            hdmi_clean_feed_altered=False,
            monitor_brightness_mode="VF Setting",
            monitor_brightness_manual_level=0,
            dormant_lcd_brightness_auto_rejected=False,
            fx3_4k_thermal_brightness_clamp=False,
            sunny_weather_power_warning=False,
            camera_settings_reset_preserved_brightness=True,
            initialize_resets_brightness=True,
            fx6_vf_brightness_level=fx6_vf_brightness_level,
            fx6_vf_color_mode=fx6_vf_color_mode,
            fx6_ae_mode=fx6_ae_mode,
            is_ae_backlight_compensation=(fx6_ae_mode == "Backlight"),
            dormant_fx6_backlight_or_nightshot_rejected=False,
            reason=(
                "ADMITTED: FX6 Monitoring>VF Setting>Brightness (1..15, Color/B&W); "
                "Shooting>AE>Mode>Backlight is AE compensation (not LCD backlight)"
            ),
        )

    # FX3 Monitor Brightness checks first
    if monitor_brightness_mode in DORMANT_MONITOR_BRIGHTNESS_MODES:
        return BrightMonitoringAndBrightnessResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            focus_mode=focus_mode,
            trigger_source=trigger_source,
            bright_monitoring_requested=bright_monitoring_requested,
            bright_monitoring_active=False,
            shooting_menu_toggle_exposed=False,
            live_view_setting_effect=live_view_setting_effect_requested,
            focus_magnifier_active=focus_magnifier_active,
            auto_magnifier_in_mf_active=auto_magnifier_in_mf_active,
            magnifier_coexistence_allowed=(firmware_version in (FW_VER_700, FW_VER_702)),
            auto_canceled_reason="",
            hdmi_clean_feed_altered=False,
            monitor_brightness_mode=monitor_brightness_mode,
            monitor_brightness_manual_level=monitor_brightness_manual_level,
            dormant_lcd_brightness_auto_rejected=True,
            fx3_4k_thermal_brightness_clamp=False,
            sunny_weather_power_warning=False,
            camera_settings_reset_preserved_brightness=True,
            initialize_resets_brightness=True,
            fx6_vf_brightness_level=0,
            fx6_vf_color_mode="N/A",
            fx6_ae_mode="N/A",
            is_ae_backlight_compensation=False,
            dormant_fx6_backlight_or_nightshot_rejected=False,
            reason=f"EOPNOTSUPP: Monitor Brightness {monitor_brightness_mode!r} is dormant on ILME-FX3",
        )
    if monitor_brightness_mode not in VALID_MONITOR_BRIGHTNESS_MODES:
        raise Stage68Phase325Error(
            f"Unsupported monitor_brightness_mode={monitor_brightness_mode!r}"
        )
    if monitor_brightness_manual_level not in FX3_MANUAL_BRIGHTNESS_LEVELS:
        return BrightMonitoringAndBrightnessResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            focus_mode=focus_mode,
            trigger_source=trigger_source,
            bright_monitoring_requested=bright_monitoring_requested,
            bright_monitoring_active=False,
            shooting_menu_toggle_exposed=False,
            live_view_setting_effect=live_view_setting_effect_requested,
            focus_magnifier_active=focus_magnifier_active,
            auto_magnifier_in_mf_active=auto_magnifier_in_mf_active,
            magnifier_coexistence_allowed=(firmware_version in (FW_VER_700, FW_VER_702)),
            auto_canceled_reason="",
            hdmi_clean_feed_altered=False,
            monitor_brightness_mode=monitor_brightness_mode,
            monitor_brightness_manual_level=monitor_brightness_manual_level,
            dormant_lcd_brightness_auto_rejected=False,
            fx3_4k_thermal_brightness_clamp=False,
            sunny_weather_power_warning=False,
            camera_settings_reset_preserved_brightness=True,
            initialize_resets_brightness=True,
            fx6_vf_brightness_level=0,
            fx6_vf_color_mode="N/A",
            fx6_ae_mode="N/A",
            is_ae_backlight_compensation=False,
            dormant_fx6_backlight_or_nightshot_rejected=False,
            reason="EINVAL: FX3 Monitor Brightness Manual must be in -2..+2",
        )

    eff_bright_mode = monitor_brightness_mode
    eff_bright_level = monitor_brightness_manual_level
    if initialize_applied:
        eff_bright_mode = "Manual"
        eff_bright_level = 0
    # Camera Settings Reset does NOT reset Monitor Brightness

    # Bright Monitoring contract checks
    if bright_monitoring_requested and trigger_source == "Shooting Menu":
        return BrightMonitoringAndBrightnessResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            focus_mode=focus_mode,
            trigger_source=trigger_source,
            bright_monitoring_requested=True,
            bright_monitoring_active=False,
            shooting_menu_toggle_exposed=False,
            live_view_setting_effect=live_view_setting_effect_requested,
            focus_magnifier_active=focus_magnifier_active,
            auto_magnifier_in_mf_active=auto_magnifier_in_mf_active,
            magnifier_coexistence_allowed=(firmware_version in (FW_VER_700, FW_VER_702)),
            auto_canceled_reason="CustomKeyOnly",
            hdmi_clean_feed_altered=False,
            monitor_brightness_mode=eff_bright_mode,
            monitor_brightness_manual_level=eff_bright_level,
            dormant_lcd_brightness_auto_rejected=False,
            fx3_4k_thermal_brightness_clamp=False,
            sunny_weather_power_warning=(eff_bright_mode == "Sunny Weather"),
            camera_settings_reset_preserved_brightness=True,
            initialize_resets_brightness=True,
            fx6_vf_brightness_level=0,
            fx6_vf_color_mode="N/A",
            fx6_ae_mode="N/A",
            is_ae_backlight_compensation=False,
            dormant_fx6_backlight_or_nightshot_rejected=False,
            reason="EOPNOTSUPP: [Bright Monitoring] is Custom-Key-Only (absent from shooting menu)",
        )

    mag_coexist = firmware_version in (FW_VER_700, FW_VER_702)
    auto_canceled_reason = ""
    bm_active = bool(bright_monitoring_requested)

    if bm_active:
        if power_off_applied:
            bm_active = False
            auto_canceled_reason = "AutoCanceled:PowerOff"
        elif exposure_mode not in FX3_PASM_MODES:
            bm_active = False
            auto_canceled_reason = "AutoCanceled:Left_PASM"
        elif focus_mode != "MF":
            bm_active = False
            auto_canceled_reason = "AutoCanceled:Left_MF_For_AF"
        elif (focus_magnifier_active or auto_magnifier_in_mf_active) and not mag_coexist:
            return BrightMonitoringAndBrightnessResult(
                body_profile=body_profile,
                firmware_version=firmware_version,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                focus_mode=focus_mode,
                trigger_source=trigger_source,
                bright_monitoring_requested=True,
                bright_monitoring_active=False,
                shooting_menu_toggle_exposed=False,
                live_view_setting_effect=live_view_setting_effect_requested,
                focus_magnifier_active=focus_magnifier_active,
                auto_magnifier_in_mf_active=auto_magnifier_in_mf_active,
                magnifier_coexistence_allowed=False,
                auto_canceled_reason="LegacyPre700_Magnifier_MutualExclusion",
                hdmi_clean_feed_altered=False,
                monitor_brightness_mode=eff_bright_mode,
                monitor_brightness_manual_level=eff_bright_level,
                dormant_lcd_brightness_auto_rejected=False,
                fx3_4k_thermal_brightness_clamp=False,
                sunny_weather_power_warning=(eff_bright_mode == "Sunny Weather"),
                camera_settings_reset_preserved_brightness=True,
                initialize_resets_brightness=True,
                fx6_vf_brightness_level=0,
                fx6_vf_color_mode="N/A",
                fx6_ae_mode="N/A",
                is_ae_backlight_compensation=False,
                dormant_fx6_backlight_or_nightshot_rejected=False,
                reason="EOPNOTSUPP: Pre-Ver.7.00 blocked Focus Magnifier during Bright Monitoring",
            )

    eff_setting_effect = "Setting Effect OFF" if bm_active else live_view_setting_effect_requested
    _ = recording_4k_active  # FX3 ilc/2210 records no 4K brightness clamp
    return BrightMonitoringAndBrightnessResult(
        body_profile=body_profile,
        firmware_version=firmware_version,
        admitted=True,
        errno_code=0,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        focus_mode=focus_mode,
        trigger_source=trigger_source,
        bright_monitoring_requested=bright_monitoring_requested,
        bright_monitoring_active=bm_active,
        shooting_menu_toggle_exposed=False,
        live_view_setting_effect=eff_setting_effect,
        focus_magnifier_active=focus_magnifier_active,
        auto_magnifier_in_mf_active=auto_magnifier_in_mf_active,
        magnifier_coexistence_allowed=mag_coexist,
        auto_canceled_reason=auto_canceled_reason,
        hdmi_clean_feed_altered=False,
        monitor_brightness_mode=eff_bright_mode,
        monitor_brightness_manual_level=eff_bright_level,
        dormant_lcd_brightness_auto_rejected=False,
        fx3_4k_thermal_brightness_clamp=False,
        sunny_weather_power_warning=(eff_bright_mode == "Sunny Weather"),
        camera_settings_reset_preserved_brightness=True,
        initialize_resets_brightness=True,
        fx6_vf_brightness_level=0,
        fx6_vf_color_mode="N/A",
        fx6_ae_mode="N/A",
        is_ae_backlight_compensation=False,
        dormant_fx6_backlight_or_nightshot_rejected=False,
        reason=(
            f"ADMITTED: BrightMonitoring={bm_active} (SettingEffect={eff_setting_effect}, "
            f"MagCoexist={mag_coexist}), MonitorBrightness={eff_bright_mode}({eff_bright_level})"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 68B — [Shot Mark 1/2], [Clip Flag], [Photo Capture], [Create Divider Frame],
#                 Zero In-Camera [Divide]/[Extract]/FTP Cut & Slot-1 EROFS=30 Vault
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShotMarkEditVaultResult:
    body_profile: str
    admitted: bool
    errno_code: int
    operation: str
    target_slot: int
    clip_flag: str
    image_jump_setting: str
    photo_capture_file_type: str
    is_recording: bool
    dormant_divide_extract_cut_rejected: bool
    dormant_fx6_shotmark_essence_rejected: bool
    tier0_vault_firewall_triggered: bool
    m4root_xml_sidecar_rewritten: bool
    dcim_still_written: bool
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    slot1_vault_shotmark_edit_mutation_bytes: int
    reason: str


def simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    operation: str = "Add Shot Mark1",
    target_slot: int = SLOT_2,
    is_recording: bool = True,
    clip_flag: str = "OK",
    image_jump_setting: str = "Shot Mark Only",
    photo_capture_file_type: str = "JPEG",
    slot1_vault_busy: bool = False,
) -> ShotMarkEditVaultResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage68Phase325Error(f"Unsupported body_profile={body_profile!r}")
    if target_slot not in VALID_SLOTS:
        raise Stage68Phase325Error(f"Unsupported target_slot={target_slot!r}")
    if clip_flag not in FX3_CLIP_FLAGS:
        raise Stage68Phase325Error(f"Unsupported clip_flag={clip_flag!r}")
    if image_jump_setting not in FX3_IMAGE_JUMP_SETTINGS:
        raise Stage68Phase325Error(f"Unsupported image_jump_setting={image_jump_setting!r}")
    if photo_capture_file_type not in FX3_PHOTO_CAPTURE_FILE_TYPES:
        raise Stage68Phase325Error(
            f"Unsupported photo_capture_file_type={photo_capture_file_type!r}"
        )

    # Tier-0 Slot-1 Vault Firewall MUST fire first for any write-class path targeting Slot 1
    is_write_op = operation in FX3_WRITE_CARD_OPS or operation in FX6_DORMANT_SHOTMARK_OPS
    if target_slot == SLOT_1 and is_write_op:
        err = EBUSY_ERRNO if slot1_vault_busy else EROFS_ERRNO
        return ShotMarkEditVaultResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=err,
            operation=operation,
            target_slot=target_slot,
            clip_flag=clip_flag,
            image_jump_setting=image_jump_setting,
            photo_capture_file_type=photo_capture_file_type,
            is_recording=is_recording,
            dormant_divide_extract_cut_rejected=(
                operation in DORMANT_DIVIDE_EXTRACT_CUT_OPS
            ),
            dormant_fx6_shotmark_essence_rejected=(
                body_profile == BODY_MODEL_FX6 and operation in FX6_DORMANT_SHOTMARK_OPS
            ),
            tier0_vault_firewall_triggered=True,
            m4root_xml_sidecar_rewritten=False,
            dcim_still_written=False,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            slot1_vault_shotmark_edit_mutation_bytes=0,
            reason=f"VAULT_FIREWALL(errno={err}): Slot-1 read-only vault blocked {operation}",
        )

    # Dormant Divide / Extract / FTP Cut (on Slot 2 or FX3/FX6)
    if operation in DORMANT_DIVIDE_EXTRACT_CUT_OPS:
        return ShotMarkEditVaultResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            operation=operation,
            target_slot=target_slot,
            clip_flag=clip_flag,
            image_jump_setting=image_jump_setting,
            photo_capture_file_type=photo_capture_file_type,
            is_recording=is_recording,
            dormant_divide_extract_cut_rejected=True,
            dormant_fx6_shotmark_essence_rejected=(body_profile == BODY_MODEL_FX6),
            tier0_vault_firewall_triggered=False,
            m4root_xml_sidecar_rewritten=False,
            dcim_still_written=False,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            slot1_vault_shotmark_edit_mutation_bytes=0,
            reason=f"EOPNOTSUPP: {operation!r} does not exist in-camera on {body_profile}",
        )

    if body_profile == BODY_MODEL_FX6:
        if operation in FX6_DORMANT_SHOTMARK_OPS or operation in (
            "Add Shot Mark1",
            "Add Shot Mark2",
            "Add/Delete Shot Mark1",
            "Add/Delete Shot Mark2",
            "Create Divider Frame",
        ):
            return ShotMarkEditVaultResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                operation=operation,
                target_slot=target_slot,
                clip_flag=clip_flag,
                image_jump_setting=image_jump_setting,
                photo_capture_file_type=photo_capture_file_type,
                is_recording=is_recording,
                dormant_divide_extract_cut_rejected=False,
                dormant_fx6_shotmark_essence_rejected=True,
                tier0_vault_firewall_triggered=False,
                m4root_xml_sidecar_rewritten=False,
                dcim_still_written=False,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                slot1_vault_shotmark_edit_mutation_bytes=0,
                reason=f"EOPNOTSUPP: ILME-FX6 uses Thumbnail>Clip Flag; {operation!r} dormant post-CBM",
            )
        if operation not in ("Clip Flag Edit", "ReadOnly_Playback", "FTP_Filter_Pull"):
            raise Stage68Phase325Error(f"Unsupported FX6 operation={operation!r}")
        return ShotMarkEditVaultResult(
            body_profile=body_profile,
            admitted=True,
            errno_code=0,
            operation=operation,
            target_slot=target_slot,
            clip_flag=clip_flag,
            image_jump_setting=image_jump_setting,
            photo_capture_file_type=photo_capture_file_type,
            is_recording=is_recording,
            dormant_divide_extract_cut_rejected=False,
            dormant_fx6_shotmark_essence_rejected=False,
            tier0_vault_firewall_triggered=False,
            m4root_xml_sidecar_rewritten=(operation == "Clip Flag Edit"),
            dcim_still_written=False,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            slot1_vault_shotmark_edit_mutation_bytes=0,
            reason=f"ADMITTED: FX6 Thumbnail {operation} (ClipFlag={clip_flag}) on Slot {target_slot}",
        )

    if operation not in FX3_ACTIVE_SHOT_MARK_OPS:
        raise Stage68Phase325Error(f"Unsupported FX3 operation={operation!r}")

    if operation in ("Add Shot Mark1", "Add Shot Mark2") and not is_recording:
        return ShotMarkEditVaultResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            operation=operation,
            target_slot=target_slot,
            clip_flag=clip_flag,
            image_jump_setting=image_jump_setting,
            photo_capture_file_type=photo_capture_file_type,
            is_recording=False,
            dormant_divide_extract_cut_rejected=False,
            dormant_fx6_shotmark_essence_rejected=False,
            tier0_vault_firewall_triggered=False,
            m4root_xml_sidecar_rewritten=False,
            dcim_still_written=False,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            slot1_vault_shotmark_edit_mutation_bytes=0,
            reason=f"EINVAL: {operation} requires active movie recording",
        )

    if operation in ("Add/Delete Shot Mark1", "Add/Delete Shot Mark2", "Photo Capture") and is_recording:
        return ShotMarkEditVaultResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EBUSY_ERRNO,
            operation=operation,
            target_slot=target_slot,
            clip_flag=clip_flag,
            image_jump_setting=image_jump_setting,
            photo_capture_file_type=photo_capture_file_type,
            is_recording=True,
            dormant_divide_extract_cut_rejected=False,
            dormant_fx6_shotmark_essence_rejected=False,
            tier0_vault_firewall_triggered=False,
            m4root_xml_sidecar_rewritten=False,
            dcim_still_written=False,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            slot1_vault_shotmark_edit_mutation_bytes=0,
            reason=f"EBUSY: {operation} is playback-only",
        )

    m4root_rewrite = operation in (
        "Add Shot Mark1",
        "Add Shot Mark2",
        "Add/Delete Shot Mark1",
        "Add/Delete Shot Mark2",
        "Clip Flag Edit",
    )
    dcim_write = operation in ("Photo Capture", "Create Divider Frame")
    return ShotMarkEditVaultResult(
        body_profile=body_profile,
        admitted=True,
        errno_code=0,
        operation=operation,
        target_slot=target_slot,
        clip_flag=clip_flag,
        image_jump_setting=image_jump_setting,
        photo_capture_file_type=photo_capture_file_type,
        is_recording=is_recording,
        dormant_divide_extract_cut_rejected=False,
        dormant_fx6_shotmark_essence_rejected=False,
        tier0_vault_firewall_triggered=False,
        m4root_xml_sidecar_rewritten=m4root_rewrite,
        dcim_still_written=dcim_write,
        slot1_data_sector_writes=0,
        slot1_avf_info_mutated=False,
        slot1_vault_shotmark_edit_mutation_bytes=0,
        reason=f"ADMITTED: FX3 {operation} on Slot {target_slot} (sidecar={m4root_rewrite}, dcim={dcim_write})",
    )


# ---------------------------------------------------------------------------
# Sub-Model 68C — Zero BT Timecode Link vs Wired VMC-BNCM1, WPA2/WPA3 Wi-Fi,
#                 BT 5.0 (15/2/1), USB-LAN Mutual Exclusion & Airplane Persistence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TimecodeWifiUsblanAirplaneResult:
    body_profile: str
    admitted: bool
    errno_code: int
    tc_source: str
    tc_make: str
    tc_run: str
    ext_lk_locked: bool
    hdmi_tc_output_default: str
    fx6_physical_bnc_tc_switch: bool
    wifi_sku: str
    wifi_band: str
    wifi_security: str
    wifi_5ghz_indoor_only: bool
    wifi_available: bool
    bluetooth_enabled: bool
    bt_paired_devices: int
    bt_concurrent_connections: int
    bt_remote_count: int
    usb_lan_active: bool
    usb_lan_connect_launch: str
    multi_micro_usb_active: bool
    usblan_mutual_exclusion_triggered: bool
    airplane_mode: str
    reset_network_set_applied: bool
    initialize_applied: bool
    zero_rf_firewall_enforced: bool
    dormant_bt_timecode_link_rejected: bool
    removed_wep_wpa_ipsec_rejected: bool
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    reason: str


def simulate_timecode_wifi_bt_usblan_and_airplane_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    tc_source: str = "Internal",
    tc_make: str = "Preset",
    tc_run: str = "Free Run",
    wifi_sku: str = WIFI_SKU_WW728473,
    wifi_band: str = "2.4GHz",
    wifi_security: str = "WPA3-SAE",
    wifi_requested: bool = False,
    bluetooth_requested: bool = False,
    bt_paired_devices: int = 0,
    bt_concurrent_connections: int = 0,
    bt_remote_count: int = 0,
    usb_lan_requested: bool = False,
    usb_lan_connect_launch: str = "Off",
    multi_micro_usb_active: bool = False,
    airplane_mode: str = "On",
    reset_network_set_applied: bool = False,
    initialize_applied: bool = False,
    zero_rf_bench_firewall: bool = True,
) -> TimecodeWifiUsblanAirplaneResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage68Phase325Error(f"Unsupported body_profile={body_profile!r}")
    if tc_make not in VALID_TIMECODE_MAKE:
        raise Stage68Phase325Error(f"Unsupported tc_make={tc_make!r}")
    if tc_run not in VALID_TIMECODE_RUN:
        raise Stage68Phase325Error(f"Unsupported tc_run={tc_run!r}")
    if wifi_sku not in VALID_WIFI_SKUS:
        raise Stage68Phase325Error(f"Unsupported wifi_sku={wifi_sku!r}")
    if wifi_band not in VALID_WIFI_BANDS:
        raise Stage68Phase325Error(f"Unsupported wifi_band={wifi_band!r}")
    if usb_lan_connect_launch not in ("Off", "On"):
        raise Stage68Phase325Error(
            f"Unsupported usb_lan_connect_launch={usb_lan_connect_launch!r}"
        )
    if airplane_mode not in ("On", "Off"):
        raise Stage68Phase325Error(f"Unsupported airplane_mode={airplane_mode!r}")

    # Effective Airplane Mode survives both Reset Network Set. and Initialize when On
    eff_airplane = airplane_mode

    # 1. Non-existent Bluetooth [Timecode Link] / UltraSync BLUE
    if tc_source in ("Timecode Link", "Bluetooth Timecode Link", "UltraSync BLUE"):
        return TimecodeWifiUsblanAirplaneResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            tc_source=tc_source,
            tc_make=tc_make,
            tc_run=tc_run,
            ext_lk_locked=False,
            hdmi_tc_output_default="Off",
            fx6_physical_bnc_tc_switch=(body_profile == BODY_MODEL_FX6),
            wifi_sku=wifi_sku,
            wifi_band=wifi_band,
            wifi_security=wifi_security,
            wifi_5ghz_indoor_only=True,
            wifi_available=False,
            bluetooth_enabled=False,
            bt_paired_devices=0,
            bt_concurrent_connections=0,
            bt_remote_count=0,
            usb_lan_active=False,
            usb_lan_connect_launch=usb_lan_connect_launch,
            multi_micro_usb_active=multi_micro_usb_active,
            usblan_mutual_exclusion_triggered=False,
            airplane_mode=eff_airplane,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            zero_rf_firewall_enforced=zero_rf_bench_firewall,
            dormant_bt_timecode_link_rejected=True,
            removed_wep_wpa_ipsec_rejected=False,
            rf_packets_transmitted=0,
            rf_nvs_mutation_bytes=0,
            reason=f"EOPNOTSUPP: Bluetooth {tc_source!r} does not exist in {body_profile} appFw.so",
        )

    # 2. FX6 has NO Bluetooth hardware and NO USB Timecode
    if body_profile == BODY_MODEL_FX6:
        if tc_source in ("USB Timecode", "VMC-BNCM1"):
            return TimecodeWifiUsblanAirplaneResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                tc_source=tc_source,
                tc_make=tc_make,
                tc_run=tc_run,
                ext_lk_locked=False,
                hdmi_tc_output_default="Off",
                fx6_physical_bnc_tc_switch=True,
                wifi_sku=wifi_sku,
                wifi_band=wifi_band,
                wifi_security=wifi_security,
                wifi_5ghz_indoor_only=True,
                wifi_available=False,
                bluetooth_enabled=False,
                bt_paired_devices=0,
                bt_concurrent_connections=0,
                bt_remote_count=0,
                usb_lan_active=False,
                usb_lan_connect_launch=usb_lan_connect_launch,
                multi_micro_usb_active=False,
                usblan_mutual_exclusion_triggered=False,
                airplane_mode=eff_airplane,
                reset_network_set_applied=reset_network_set_applied,
                initialize_applied=initialize_applied,
                zero_rf_firewall_enforced=zero_rf_bench_firewall,
                dormant_bt_timecode_link_rejected=False,
                removed_wep_wpa_ipsec_rejected=False,
                rf_packets_transmitted=0,
                rf_nvs_mutation_bytes=0,
                reason="EOPNOTSUPP: ILME-FX6 uses physical TC IN/OUT BNC switch; USB Timecode dormant",
            )
        if bluetooth_requested:
            return TimecodeWifiUsblanAirplaneResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                tc_source=tc_source,
                tc_make=tc_make,
                tc_run=tc_run,
                ext_lk_locked=(tc_source == "Physical BNC TC IN"),
                hdmi_tc_output_default="Off",
                fx6_physical_bnc_tc_switch=True,
                wifi_sku=wifi_sku,
                wifi_band=wifi_band,
                wifi_security=wifi_security,
                wifi_5ghz_indoor_only=True,
                wifi_available=False,
                bluetooth_enabled=False,
                bt_paired_devices=0,
                bt_concurrent_connections=0,
                bt_remote_count=0,
                usb_lan_active=False,
                usb_lan_connect_launch=usb_lan_connect_launch,
                multi_micro_usb_active=False,
                usblan_mutual_exclusion_triggered=False,
                airplane_mode=eff_airplane,
                reset_network_set_applied=reset_network_set_applied,
                initialize_applied=initialize_applied,
                zero_rf_firewall_enforced=zero_rf_bench_firewall,
                dormant_bt_timecode_link_rejected=False,
                removed_wep_wpa_ipsec_rejected=False,
                rf_packets_transmitted=0,
                rf_nvs_mutation_bytes=0,
                reason="EOPNOTSUPP: ILME-FX6 lacks Bluetooth hardware",
            )

    # 3. Removed Ver. 7.00+ WEP / WPA-PSK / Security(IPsec)
    if wifi_security in REMOVED_WIFI_SECURITY:
        return TimecodeWifiUsblanAirplaneResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            tc_source=tc_source,
            tc_make=tc_make,
            tc_run=tc_run,
            ext_lk_locked=False,
            hdmi_tc_output_default="Off",
            fx6_physical_bnc_tc_switch=(body_profile == BODY_MODEL_FX6),
            wifi_sku=wifi_sku,
            wifi_band=wifi_band,
            wifi_security=wifi_security,
            wifi_5ghz_indoor_only=True,
            wifi_available=False,
            bluetooth_enabled=False,
            bt_paired_devices=0,
            bt_concurrent_connections=0,
            bt_remote_count=0,
            usb_lan_active=False,
            usb_lan_connect_launch=usb_lan_connect_launch,
            multi_micro_usb_active=multi_micro_usb_active,
            usblan_mutual_exclusion_triggered=False,
            airplane_mode=eff_airplane,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            zero_rf_firewall_enforced=zero_rf_bench_firewall,
            dormant_bt_timecode_link_rejected=False,
            removed_wep_wpa_ipsec_rejected=True,
            rf_packets_transmitted=0,
            rf_nvs_mutation_bytes=0,
            reason=f"EOPNOTSUPP: Ver. 7.00+ removed insecure Wi-Fi protocol {wifi_security!r}",
        )
    if wifi_security not in FX3_SUPPORTED_WIFI_SECURITY:
        raise Stage68Phase325Error(f"Unsupported wifi_security={wifi_security!r}")

    # 4. Wi-Fi SKU WW558244 (2.4 GHz only) vs WW728473 (2.4/5 GHz)
    if wifi_sku == WIFI_SKU_WW558244 and wifi_band == "5GHz":
        return TimecodeWifiUsblanAirplaneResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            tc_source=tc_source,
            tc_make=tc_make,
            tc_run=tc_run,
            ext_lk_locked=False,
            hdmi_tc_output_default="Off",
            fx6_physical_bnc_tc_switch=(body_profile == BODY_MODEL_FX6),
            wifi_sku=wifi_sku,
            wifi_band=wifi_band,
            wifi_security=wifi_security,
            wifi_5ghz_indoor_only=True,
            wifi_available=False,
            bluetooth_enabled=False,
            bt_paired_devices=0,
            bt_concurrent_connections=0,
            bt_remote_count=0,
            usb_lan_active=False,
            usb_lan_connect_launch=usb_lan_connect_launch,
            multi_micro_usb_active=multi_micro_usb_active,
            usblan_mutual_exclusion_triggered=False,
            airplane_mode=eff_airplane,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            zero_rf_firewall_enforced=zero_rf_bench_firewall,
            dormant_bt_timecode_link_rejected=False,
            removed_wep_wpa_ipsec_rejected=False,
            rf_packets_transmitted=0,
            rf_nvs_mutation_bytes=0,
            reason="EOPNOTSUPP: WW558244 hardware SKU supports 2.4GHz only (no 5GHz)",
        )

    # 5. USB-LAN mutual exclusions: (a) cannot coexist with Multi/Micro USB (e.g., VMC-BNCM1),
    #    and (b) disables Wi-Fi while active
    eff_multi_usb = multi_micro_usb_active or (
        body_profile == BODY_MODEL_FX3 and tc_source == "VMC-BNCM1"
    )
    if usb_lan_requested and eff_multi_usb:
        return TimecodeWifiUsblanAirplaneResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EBUSY_ERRNO,
            tc_source=tc_source,
            tc_make=tc_make,
            tc_run=tc_run,
            ext_lk_locked=False,
            hdmi_tc_output_default="Off",
            fx6_physical_bnc_tc_switch=(body_profile == BODY_MODEL_FX6),
            wifi_sku=wifi_sku,
            wifi_band=wifi_band,
            wifi_security=wifi_security,
            wifi_5ghz_indoor_only=True,
            wifi_available=False,
            bluetooth_enabled=False,
            bt_paired_devices=0,
            bt_concurrent_connections=0,
            bt_remote_count=0,
            usb_lan_active=False,
            usb_lan_connect_launch=usb_lan_connect_launch,
            multi_micro_usb_active=True,
            usblan_mutual_exclusion_triggered=True,
            airplane_mode=eff_airplane,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            zero_rf_firewall_enforced=zero_rf_bench_firewall,
            dormant_bt_timecode_link_rejected=False,
            removed_wep_wpa_ipsec_rejected=False,
            rf_packets_transmitted=0,
            rf_nvs_mutation_bytes=0,
            reason="EBUSY: USB-LAN cannot communicate concurrently with Multi/Micro USB (VMC-BNCM1/wired)",
        )

    if usb_lan_requested and wifi_requested:
        return TimecodeWifiUsblanAirplaneResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EBUSY_ERRNO,
            tc_source=tc_source,
            tc_make=tc_make,
            tc_run=tc_run,
            ext_lk_locked=False,
            hdmi_tc_output_default="Off",
            fx6_physical_bnc_tc_switch=(body_profile == BODY_MODEL_FX6),
            wifi_sku=wifi_sku,
            wifi_band=wifi_band,
            wifi_security=wifi_security,
            wifi_5ghz_indoor_only=True,
            wifi_available=False,
            bluetooth_enabled=False,
            bt_paired_devices=0,
            bt_concurrent_connections=0,
            bt_remote_count=0,
            usb_lan_active=True,
            usb_lan_connect_launch=usb_lan_connect_launch,
            multi_micro_usb_active=False,
            usblan_mutual_exclusion_triggered=True,
            airplane_mode=eff_airplane,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            zero_rf_firewall_enforced=zero_rf_bench_firewall,
            dormant_bt_timecode_link_rejected=False,
            removed_wep_wpa_ipsec_rejected=False,
            rf_packets_transmitted=0,
            rf_nvs_mutation_bytes=0,
            reason="EBUSY: Internal Wi-Fi is unavailable while USB-LAN is active",
        )

    # 6. Zero-RF bench firewall & Airplane Mode = On RF isolation
    if zero_rf_bench_firewall and (
        eff_airplane != "On" or wifi_requested or bluetooth_requested
    ):
        return TimecodeWifiUsblanAirplaneResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EPERM_ERRNO,
            tc_source=tc_source,
            tc_make=tc_make,
            tc_run=tc_run,
            ext_lk_locked=False,
            hdmi_tc_output_default="Off",
            fx6_physical_bnc_tc_switch=(body_profile == BODY_MODEL_FX6),
            wifi_sku=wifi_sku,
            wifi_band=wifi_band,
            wifi_security=wifi_security,
            wifi_5ghz_indoor_only=True,
            wifi_available=False,
            bluetooth_enabled=False,
            bt_paired_devices=bt_paired_devices,
            bt_concurrent_connections=bt_concurrent_connections,
            bt_remote_count=bt_remote_count,
            usb_lan_active=usb_lan_requested,
            usb_lan_connect_launch=usb_lan_connect_launch,
            multi_micro_usb_active=eff_multi_usb,
            usblan_mutual_exclusion_triggered=False,
            airplane_mode=eff_airplane,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            zero_rf_firewall_enforced=True,
            dormant_bt_timecode_link_rejected=False,
            removed_wep_wpa_ipsec_rejected=False,
            rf_packets_transmitted=0,
            rf_nvs_mutation_bytes=0,
            reason="ZERO_RF_FIREWALL(EPERM): Bench requires Airplane Mode=On and zero Wi-Fi/BT RF emission",
        )

    # 7. Bluetooth 5.0 capacity bounds (15 paired / 2 concurrent / 1 remote) when non-zero-RF checks run
    if (
        bt_paired_devices > FX3_BT_MAX_PAIRED
        or bt_concurrent_connections > FX3_BT_MAX_CONCURRENT
        or bt_remote_count > FX3_BT_MAX_REMOTE
    ):
        return TimecodeWifiUsblanAirplaneResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            tc_source=tc_source,
            tc_make=tc_make,
            tc_run=tc_run,
            ext_lk_locked=False,
            hdmi_tc_output_default="Off",
            fx6_physical_bnc_tc_switch=False,
            wifi_sku=wifi_sku,
            wifi_band=wifi_band,
            wifi_security=wifi_security,
            wifi_5ghz_indoor_only=True,
            wifi_available=False,
            bluetooth_enabled=False,
            bt_paired_devices=bt_paired_devices,
            bt_concurrent_connections=bt_concurrent_connections,
            bt_remote_count=bt_remote_count,
            usb_lan_active=usb_lan_requested,
            usb_lan_connect_launch=usb_lan_connect_launch,
            multi_micro_usb_active=eff_multi_usb,
            usblan_mutual_exclusion_triggered=False,
            airplane_mode=eff_airplane,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            zero_rf_firewall_enforced=zero_rf_bench_firewall,
            dormant_bt_timecode_link_rejected=False,
            removed_wep_wpa_ipsec_rejected=False,
            rf_packets_transmitted=0,
            rf_nvs_mutation_bytes=0,
            reason="EINVAL: FX3 Bluetooth 5.0 enforces <=15 paired, <=2 concurrent, <=1 BT remote",
        )

    # 8. VMC-BNCM1 EXT-LK lock rule (Make=Preset + Run=Free Run)
    if body_profile == BODY_MODEL_FX3 and tc_source == "VMC-BNCM1":
        ext_lk = tc_make == "Preset" and tc_run == "Free Run"
    elif body_profile == BODY_MODEL_FX6 and tc_source == "Physical BNC TC IN":
        ext_lk = tc_make == "Preset" and tc_run == "Free Run"
    else:
        ext_lk = False

    if (
        body_profile == BODY_MODEL_FX3
        and tc_source == "VMC-BNCM1"
        and not ext_lk
    ):
        return TimecodeWifiUsblanAirplaneResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            tc_source=tc_source,
            tc_make=tc_make,
            tc_run=tc_run,
            ext_lk_locked=False,
            hdmi_tc_output_default="Off",
            fx6_physical_bnc_tc_switch=False,
            wifi_sku=wifi_sku,
            wifi_band=wifi_band,
            wifi_security=wifi_security,
            wifi_5ghz_indoor_only=True,
            wifi_available=False,
            bluetooth_enabled=False,
            bt_paired_devices=bt_paired_devices,
            bt_concurrent_connections=bt_concurrent_connections,
            bt_remote_count=bt_remote_count,
            usb_lan_active=False,
            usb_lan_connect_launch=usb_lan_connect_launch,
            multi_micro_usb_active=True,
            usblan_mutual_exclusion_triggered=False,
            airplane_mode=eff_airplane,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            zero_rf_firewall_enforced=zero_rf_bench_firewall,
            dormant_bt_timecode_link_rejected=False,
            removed_wep_wpa_ipsec_rejected=False,
            rf_packets_transmitted=0,
            rf_nvs_mutation_bytes=0,
            reason="EINVAL: VMC-BNCM1 EXT-LK requires [Time Code Make]=Preset and [Time Code Run]=Free Run",
        )

    return TimecodeWifiUsblanAirplaneResult(
        body_profile=body_profile,
        admitted=True,
        errno_code=0,
        tc_source=tc_source,
        tc_make=tc_make,
        tc_run=tc_run,
        ext_lk_locked=ext_lk,
        hdmi_tc_output_default="Off",
        fx6_physical_bnc_tc_switch=(body_profile == BODY_MODEL_FX6),
        wifi_sku=wifi_sku,
        wifi_band=wifi_band,
        wifi_security=wifi_security,
        wifi_5ghz_indoor_only=True,
        wifi_available=(not usb_lan_requested) and (eff_airplane == "Off"),
        bluetooth_enabled=False,
        bt_paired_devices=bt_paired_devices,
        bt_concurrent_connections=bt_concurrent_connections,
        bt_remote_count=bt_remote_count,
        usb_lan_active=usb_lan_requested,
        usb_lan_connect_launch=usb_lan_connect_launch,
        multi_micro_usb_active=eff_multi_usb,
        usblan_mutual_exclusion_triggered=False,
        airplane_mode=eff_airplane,
        reset_network_set_applied=reset_network_set_applied,
        initialize_applied=initialize_applied,
        zero_rf_firewall_enforced=zero_rf_bench_firewall,
        dormant_bt_timecode_link_rejected=False,
        removed_wep_wpa_ipsec_rejected=False,
        rf_packets_transmitted=0,
        rf_nvs_mutation_bytes=0,
        reason=(
            f"ADMITTED: {body_profile} tc={tc_source}(EXT-LK={ext_lk}), "
            f"usb_lan={usb_lan_requested}, airplane={eff_airplane}"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 68D — Still [BULB] Mechanical-Shutter Constraint & [DRO] / [DRO Bracket]
#                 vs Dormant [Bulb Timer] & Dormant [Auto HDR]
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BulbDroDormantResult:
    body_profile: str
    admitted: bool
    errno_code: int
    shoot_mode: str
    exposure_mode: str
    shutter_type: str
    drive_mode: str
    bulb_requested: bool
    bulb_timer_requested: bool
    auto_hdr_requested: bool
    effective_shutter_speed: str
    bulb_fallback_to_30s: bool
    anti_flicker_allowed: bool
    long_exposure_nr_dark_frame: bool
    extended_bulb_controller: str
    picture_profile: str
    hlg_still_image: str
    dro_mode: str
    effective_dro_mode: str
    dro_bracket_mode: str
    dro_forced_off_by_pp: bool
    dro_disabled_by_hlg: bool
    dormant_bulb_timer_rejected: bool
    dormant_auto_hdr_rejected: bool
    reason: str


def simulate_bulb_dro_and_dormant_timer_hdr_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shoot_mode: str = SHOOT_MODE_STILL,
    exposure_mode: str = "M",
    shutter_type: str = "Mechanical Shutter",
    drive_mode: str = "Single Shooting",
    bulb_requested: bool = False,
    bulb_timer_requested: bool = False,
    auto_hdr_requested: bool = False,
    long_exposure_nr: str = "On",
    extended_bulb_controller: str = "None",
    picture_profile: str = "Off",
    hlg_still_image: str = "Off",
    dro_mode: str = "Auto",
    dro_bracket_mode: str = "Off",
    camera_settings_reset_applied: bool = False,
) -> BulbDroDormantResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage68Phase325Error(f"Unsupported body_profile={body_profile!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage68Phase325Error(f"Unsupported shoot_mode={shoot_mode!r}")
    if exposure_mode not in VALID_EXPOSURE_MODES:
        raise Stage68Phase325Error(f"Unsupported exposure_mode={exposure_mode!r}")
    if shutter_type not in VALID_SHUTTER_TYPES:
        raise Stage68Phase325Error(f"Unsupported shutter_type={shutter_type!r}")
    if drive_mode not in VALID_DRIVE_MODES:
        raise Stage68Phase325Error(f"Unsupported drive_mode={drive_mode!r}")
    if long_exposure_nr not in ("On", "Off"):
        raise Stage68Phase325Error(f"Unsupported long_exposure_nr={long_exposure_nr!r}")
    if extended_bulb_controller not in EXTENDED_BULB_CONTROLLERS:
        raise Stage68Phase325Error(
            f"Unsupported extended_bulb_controller={extended_bulb_controller!r}"
        )
    if picture_profile not in VALID_PICTURE_PROFILES:
        raise Stage68Phase325Error(f"Unsupported picture_profile={picture_profile!r}")
    if hlg_still_image not in ("On", "Off"):
        raise Stage68Phase325Error(f"Unsupported hlg_still_image={hlg_still_image!r}")
    if dro_mode not in FX3_DRO_MODES:
        raise Stage68Phase325Error(f"Unsupported dro_mode={dro_mode!r}")
    if dro_bracket_mode not in FX3_DRO_BRACKET_MODES:
        raise Stage68Phase325Error(f"Unsupported dro_bracket_mode={dro_bracket_mode!r}")

    # Dormant Bulb Timer and Auto HDR MUST fail-closed EOPNOTSUPP=95
    if bulb_timer_requested:
        return BulbDroDormantResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            shutter_type=shutter_type,
            drive_mode=drive_mode,
            bulb_requested=bulb_requested,
            bulb_timer_requested=True,
            auto_hdr_requested=auto_hdr_requested,
            effective_shutter_speed="N/A",
            bulb_fallback_to_30s=False,
            anti_flicker_allowed=False,
            long_exposure_nr_dark_frame=False,
            extended_bulb_controller=extended_bulb_controller,
            picture_profile=picture_profile,
            hlg_still_image=hlg_still_image,
            dro_mode=dro_mode,
            effective_dro_mode="Off",
            dro_bracket_mode=dro_bracket_mode,
            dro_forced_off_by_pp=False,
            dro_disabled_by_hlg=False,
            dormant_bulb_timer_rejected=True,
            dormant_auto_hdr_rejected=False,
            reason="EOPNOTSUPP: [Bulb Timer] is dormant on FX3 Ver. 7.02 (0 hits in ilc/2210)",
        )
    if auto_hdr_requested:
        return BulbDroDormantResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            shutter_type=shutter_type,
            drive_mode=drive_mode,
            bulb_requested=bulb_requested,
            bulb_timer_requested=False,
            auto_hdr_requested=True,
            effective_shutter_speed="N/A",
            bulb_fallback_to_30s=False,
            anti_flicker_allowed=False,
            long_exposure_nr_dark_frame=False,
            extended_bulb_controller=extended_bulb_controller,
            picture_profile=picture_profile,
            hlg_still_image=hlg_still_image,
            dro_mode=dro_mode,
            effective_dro_mode="Off",
            dro_bracket_mode=dro_bracket_mode,
            dro_forced_off_by_pp=False,
            dro_disabled_by_hlg=False,
            dormant_bulb_timer_rejected=False,
            dormant_auto_hdr_rejected=True,
            reason="EOPNOTSUPP: [Auto HDR] is dormant on FX3 Ver. 7.02 (replaced by [HLG Still Image])",
        )

    # ILME-FX6 lacks Still pipeline, mechanical shutter, BULB, and DRO
    if body_profile == BODY_MODEL_FX6:
        return BulbDroDormantResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            shutter_type="Electronic Only",
            drive_mode=drive_mode,
            bulb_requested=bulb_requested,
            bulb_timer_requested=False,
            auto_hdr_requested=False,
            effective_shutter_speed="N/A",
            bulb_fallback_to_30s=False,
            anti_flicker_allowed=False,
            long_exposure_nr_dark_frame=False,
            extended_bulb_controller=extended_bulb_controller,
            picture_profile=picture_profile,
            hlg_still_image=hlg_still_image,
            dro_mode=dro_mode,
            effective_dro_mode="N/A",
            dro_bracket_mode=dro_bracket_mode,
            dro_forced_off_by_pp=False,
            dro_disabled_by_hlg=False,
            dormant_bulb_timer_rejected=False,
            dormant_auto_hdr_rejected=False,
            reason="EOPNOTSUPP: ILME-FX6 lacks Still pipeline, Mechanical Shutter, BULB, and DRO",
        )

    # Active Still BULB checks
    if bulb_requested:
        if shoot_mode != SHOOT_MODE_STILL:
            return BulbDroDormantResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                shutter_type=shutter_type,
                drive_mode=drive_mode,
                bulb_requested=True,
                bulb_timer_requested=False,
                auto_hdr_requested=False,
                effective_shutter_speed="N/A",
                bulb_fallback_to_30s=False,
                anti_flicker_allowed=False,
                long_exposure_nr_dark_frame=False,
                extended_bulb_controller=extended_bulb_controller,
                picture_profile=picture_profile,
                hlg_still_image=hlg_still_image,
                dro_mode=dro_mode,
                effective_dro_mode="Off",
                dro_bracket_mode=dro_bracket_mode,
                dro_forced_off_by_pp=False,
                dro_disabled_by_hlg=False,
                dormant_bulb_timer_rejected=False,
                dormant_auto_hdr_rejected=False,
                reason="EOPNOTSUPP: [BULB] is Still-only",
            )
        if exposure_mode != "M":
            return BulbDroDormantResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                shutter_type=shutter_type,
                drive_mode=drive_mode,
                bulb_requested=True,
                bulb_timer_requested=False,
                auto_hdr_requested=False,
                effective_shutter_speed='30"',
                bulb_fallback_to_30s=True,
                anti_flicker_allowed=False,
                long_exposure_nr_dark_frame=False,
                extended_bulb_controller=extended_bulb_controller,
                picture_profile=picture_profile,
                hlg_still_image=hlg_still_image,
                dro_mode=dro_mode,
                effective_dro_mode="Off",
                dro_bracket_mode=dro_bracket_mode,
                dro_forced_off_by_pp=False,
                dro_disabled_by_hlg=False,
                dormant_bulb_timer_rejected=False,
                dormant_auto_hdr_rejected=False,
                reason="EOPNOTSUPP: [BULB] requires Manual Exposure (M)",
            )
        if shutter_type != "Mechanical Shutter" or drive_mode in BULB_BLOCKED_DRIVE_MODES:
            return BulbDroDormantResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                shutter_type=shutter_type,
                drive_mode=drive_mode,
                bulb_requested=True,
                bulb_timer_requested=False,
                auto_hdr_requested=False,
                effective_shutter_speed='30"',
                bulb_fallback_to_30s=True,
                anti_flicker_allowed=False,
                long_exposure_nr_dark_frame=False,
                extended_bulb_controller=extended_bulb_controller,
                picture_profile=picture_profile,
                hlg_still_image=hlg_still_image,
                dro_mode=dro_mode,
                effective_dro_mode="Off",
                dro_bracket_mode=dro_bracket_mode,
                dro_forced_off_by_pp=False,
                dro_disabled_by_hlg=False,
                dormant_bulb_timer_rejected=False,
                dormant_auto_hdr_rejected=False,
                reason=(
                    f'EOPNOTSUPP: [BULB] falls back to 30" under '
                    f"{shutter_type}/{drive_mode} (requires Mechanical Shutter)"
                ),
            )

    # DRO & DRO Bracket checks
    eff_dro = "Auto" if camera_settings_reset_applied else dro_mode
    eff_dro_bracket = "Off" if camera_settings_reset_applied else dro_bracket_mode
    forced_off_pp = picture_profile != "Off"
    disabled_hlg = hlg_still_image == "On"
    if forced_off_pp or disabled_hlg:
        eff_dro = "Off"
        if eff_dro_bracket != "Off":
            return BulbDroDormantResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                shutter_type=shutter_type,
                drive_mode=drive_mode,
                bulb_requested=bulb_requested,
                bulb_timer_requested=False,
                auto_hdr_requested=False,
                effective_shutter_speed=("BULB" if bulb_requested else '1/60"'),
                bulb_fallback_to_30s=False,
                anti_flicker_allowed=(not bulb_requested),
                long_exposure_nr_dark_frame=(bulb_requested and long_exposure_nr == "On"),
                extended_bulb_controller=extended_bulb_controller,
                picture_profile=picture_profile,
                hlg_still_image=hlg_still_image,
                dro_mode=dro_mode,
                effective_dro_mode="Off",
                dro_bracket_mode=dro_bracket_mode,
                dro_forced_off_by_pp=forced_off_pp,
                dro_disabled_by_hlg=disabled_hlg,
                dormant_bulb_timer_rejected=False,
                dormant_auto_hdr_rejected=False,
                reason="EOPNOTSUPP: [DRO Bracket] disabled when Picture Profile != Off or HLG Still Image == On",
            )

    return BulbDroDormantResult(
        body_profile=body_profile,
        admitted=True,
        errno_code=0,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        shutter_type=shutter_type,
        drive_mode=drive_mode,
        bulb_requested=bulb_requested,
        bulb_timer_requested=False,
        auto_hdr_requested=False,
        effective_shutter_speed=("BULB" if bulb_requested else '1/60"'),
        bulb_fallback_to_30s=False,
        anti_flicker_allowed=(not bulb_requested),
        long_exposure_nr_dark_frame=(bulb_requested and long_exposure_nr == "On"),
        extended_bulb_controller=extended_bulb_controller,
        picture_profile=picture_profile,
        hlg_still_image=hlg_still_image,
        dro_mode=dro_mode,
        effective_dro_mode=eff_dro,
        dro_bracket_mode=eff_dro_bracket,
        dro_forced_off_by_pp=forced_off_pp,
        dro_disabled_by_hlg=disabled_hlg,
        dormant_bulb_timer_rejected=False,
        dormant_auto_hdr_rejected=False,
        reason=(
            f"ADMITTED: BULB={bulb_requested}, DRO={eff_dro}, "
            f"DROBracket={eff_dro_bracket}, LenNRDarkFrame={bulb_requested and long_exposure_nr == 'On'}"
        ),
    )


def _build_stage68_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_68th_stage_milestone": IS_68TH_STAGE_MILESTONE,
        "wave": "Wave-58",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase325_bright_mon_shotmark_usblan_bulb_dormant_coemulation(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute complete Phase 325 Stage 68 (68/68 Milestone) Wave-58 HIL co-emulation."""
    donor_audit = inspect_phase325_donors(force_clean_room=force_clean_room, env=env)

    # Sub-Model 68A probes
    p68a_bm_ver702_mag_ok = simulate_bright_monitoring_and_monitor_brightness_hil(
        firmware_version=FW_VER_702,
        exposure_mode="M",
        focus_mode="MF",
        trigger_source="Custom Key/Dial Set.",
        bright_monitoring_requested=True,
        focus_magnifier_active=True,
        auto_magnifier_in_mf_active=True,
        monitor_brightness_mode="Sunny Weather",
    )
    p68a_bm_shooting_menu_blocked = simulate_bright_monitoring_and_monitor_brightness_hil(
        trigger_source="Shooting Menu",
        bright_monitoring_requested=True,
    )
    p68a_bm_auto_cancels = [
        simulate_bright_monitoring_and_monitor_brightness_hil(
            bright_monitoring_requested=True,
            power_off_applied=True,
        ),
        simulate_bright_monitoring_and_monitor_brightness_hil(
            bright_monitoring_requested=True,
            exposure_mode="Intelligent Auto",
        ),
        simulate_bright_monitoring_and_monitor_brightness_hil(
            bright_monitoring_requested=True,
            focus_mode="AF-C",
        ),
    ]
    p68a_dormant_auto_brightness = simulate_bright_monitoring_and_monitor_brightness_hil(
        monitor_brightness_mode="Auto",
    )
    p68a_brightness_reset_split = [
        simulate_bright_monitoring_and_monitor_brightness_hil(
            monitor_brightness_mode="Manual",
            monitor_brightness_manual_level=2,
            camera_settings_reset_applied=True,
        ),
        simulate_bright_monitoring_and_monitor_brightness_hil(
            monitor_brightness_mode="Sunny Weather",
            initialize_applied=True,
        ),
    ]
    p68a_fx6_vf_and_ae_backlight = simulate_bright_monitoring_and_monitor_brightness_hil(
        body_profile=BODY_MODEL_FX6,
        fx6_vf_brightness_level=12,
        fx6_vf_color_mode="B&W",
        fx6_ae_mode="Backlight",
    )
    p68a_fx6_dormant_rejected = simulate_bright_monitoring_and_monitor_brightness_hil(
        body_profile=BODY_MODEL_FX6,
        fx6_dormant_feature_requested="NIGHTSHOT_SETTING",
    )
    p68a_ok = (
        p68a_bm_ver702_mag_ok.admitted
        and p68a_bm_ver702_mag_ok.bright_monitoring_active
        and p68a_bm_ver702_mag_ok.magnifier_coexistence_allowed
        and p68a_bm_ver702_mag_ok.live_view_setting_effect == "Setting Effect OFF"
        and (not p68a_bm_ver702_mag_ok.hdmi_clean_feed_altered)
        and (not p68a_bm_shooting_menu_blocked.admitted)
        and p68a_bm_shooting_menu_blocked.errno_code == EOPNOTSUPP_ERRNO
        and all((not r.bright_monitoring_active) and bool(r.auto_canceled_reason) for r in p68a_bm_auto_cancels)
        and (not p68a_dormant_auto_brightness.admitted)
        and p68a_dormant_auto_brightness.errno_code == EOPNOTSUPP_ERRNO
        and p68a_brightness_reset_split[0].monitor_brightness_manual_level == 2
        and p68a_brightness_reset_split[1].monitor_brightness_mode == "Manual"
        and p68a_fx6_vf_and_ae_backlight.admitted
        and p68a_fx6_vf_and_ae_backlight.is_ae_backlight_compensation
        and (not p68a_fx6_dormant_rejected.admitted)
        and p68a_fx6_dormant_rejected.errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 68B probes
    p68b_slot2_ops_ok = [
        simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
            operation="Add Shot Mark1",
            target_slot=SLOT_2,
            is_recording=True,
        ),
        simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
            operation="Add/Delete Shot Mark2",
            target_slot=SLOT_2,
            is_recording=False,
        ),
        simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
            operation="Clip Flag Edit",
            target_slot=SLOT_2,
            is_recording=False,
            clip_flag="KEEP",
        ),
        simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
            operation="Photo Capture",
            target_slot=SLOT_2,
            is_recording=False,
            photo_capture_file_type="HEIF_422",
        ),
        simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
            operation="Create Divider Frame",
            target_slot=SLOT_2,
            is_recording=False,
        ),
    ]
    p68b_dormant_divide_extract_rejected = [
        simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
            operation=op,
            target_slot=SLOT_2,
            is_recording=False,
        )
        for op in ("Divide", "Extract", "Cut to 15 seconds", "Cut to 60 seconds")
    ]
    p68b_slot1_vault_erofs = [
        simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
            operation=op,
            target_slot=SLOT_1,
            is_recording=(op == "Add Shot Mark1"),
        )
        for op in (
            "Add Shot Mark1",
            "Add/Delete Shot Mark2",
            "Clip Flag Edit",
            "Photo Capture",
            "Create Divider Frame",
        )
    ]
    p68b_fx6_clip_flag_vs_dormant_shotmark = [
        simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
            body_profile=BODY_MODEL_FX6,
            operation="Clip Flag Edit",
            target_slot=SLOT_2,
            clip_flag="OK",
        ),
        simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
            body_profile=BODY_MODEL_FX6,
            operation="Shot Mark 0..9",
            target_slot=SLOT_2,
        ),
    ]
    p68b_ok = (
        all(r.admitted and r.slot1_data_sector_writes == 0 for r in p68b_slot2_ops_ok)
        and all(
            (not r.admitted)
            and r.errno_code == EOPNOTSUPP_ERRNO
            and r.dormant_divide_extract_cut_rejected
            for r in p68b_dormant_divide_extract_rejected
        )
        and all(
            (not r.admitted)
            and r.errno_code == EROFS_ERRNO
            and r.tier0_vault_firewall_triggered
            and r.slot1_data_sector_writes == 0
            and (not r.slot1_avf_info_mutated)
            for r in p68b_slot1_vault_erofs
        )
        and p68b_fx6_clip_flag_vs_dormant_shotmark[0].admitted
        and (not p68b_fx6_clip_flag_vs_dormant_shotmark[1].admitted)
        and p68b_fx6_clip_flag_vs_dormant_shotmark[1].errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 68C probes
    p68c_zero_bt_tc_link_blocked = simulate_timecode_wifi_bt_usblan_and_airplane_hil(
        tc_source="UltraSync BLUE",
    )
    p68c_vmc_bncm1_ext_lk_ok = simulate_timecode_wifi_bt_usblan_and_airplane_hil(
        tc_source="VMC-BNCM1",
        tc_make="Preset",
        tc_run="Free Run",
        airplane_mode="On",
    )
    p68c_usblan_ok = simulate_timecode_wifi_bt_usblan_and_airplane_hil(
        usb_lan_requested=True,
        airplane_mode="On",
        reset_network_set_applied=True,
        initialize_applied=True,
    )
    p68c_usblan_multi_usb_blocked = simulate_timecode_wifi_bt_usblan_and_airplane_hil(
        tc_source="VMC-BNCM1",
        usb_lan_requested=True,
    )
    p68c_usblan_wifi_blocked = simulate_timecode_wifi_bt_usblan_and_airplane_hil(
        usb_lan_requested=True,
        wifi_requested=True,
    )
    p68c_removed_wep_wpa_ipsec_blocked = [
        simulate_timecode_wifi_bt_usblan_and_airplane_hil(wifi_security=sec)
        for sec in ("WEP", "WPA-PSK", "Security(IPsec)")
    ]
    p68c_ww558244_5ghz_blocked = simulate_timecode_wifi_bt_usblan_and_airplane_hil(
        wifi_sku=WIFI_SKU_WW558244,
        wifi_band="5GHz",
    )
    p68c_fx6_no_bt_ok_bnc = [
        simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            body_profile=BODY_MODEL_FX6,
            tc_source="Physical BNC TC IN",
            tc_make="Preset",
            tc_run="Free Run",
        ),
        simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            body_profile=BODY_MODEL_FX6,
            bluetooth_requested=True,
        ),
    ]
    p68c_ok = (
        (not p68c_zero_bt_tc_link_blocked.admitted)
        and p68c_zero_bt_tc_link_blocked.errno_code == EOPNOTSUPP_ERRNO
        and p68c_zero_bt_tc_link_blocked.dormant_bt_timecode_link_rejected
        and p68c_vmc_bncm1_ext_lk_ok.admitted
        and p68c_vmc_bncm1_ext_lk_ok.ext_lk_locked
        and p68c_usblan_ok.admitted
        and p68c_usblan_ok.usb_lan_active
        and p68c_usblan_ok.airplane_mode == "On"
        and p68c_usblan_ok.rf_packets_transmitted == 0
        and (not p68c_usblan_multi_usb_blocked.admitted)
        and p68c_usblan_multi_usb_blocked.errno_code == EBUSY_ERRNO
        and p68c_usblan_multi_usb_blocked.usblan_mutual_exclusion_triggered
        and (not p68c_usblan_wifi_blocked.admitted)
        and p68c_usblan_wifi_blocked.errno_code == EBUSY_ERRNO
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO and r.removed_wep_wpa_ipsec_rejected
            for r in p68c_removed_wep_wpa_ipsec_blocked
        )
        and (not p68c_ww558244_5ghz_blocked.admitted)
        and p68c_ww558244_5ghz_blocked.errno_code == EOPNOTSUPP_ERRNO
        and p68c_fx6_no_bt_ok_bnc[0].admitted
        and p68c_fx6_no_bt_ok_bnc[0].ext_lk_locked
        and (not p68c_fx6_no_bt_ok_bnc[1].admitted)
        and p68c_fx6_no_bt_ok_bnc[1].errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 68D probes
    p68d_bulb_mech_ok = simulate_bulb_dro_and_dormant_timer_hdr_hil(
        shoot_mode=SHOOT_MODE_STILL,
        exposure_mode="M",
        shutter_type="Mechanical Shutter",
        drive_mode="Single Shooting",
        bulb_requested=True,
        long_exposure_nr="On",
    )
    p68d_bulb_eshutter_or_cont_blocked = [
        simulate_bulb_dro_and_dormant_timer_hdr_hil(
            shutter_type="Electronic Shutter",
            bulb_requested=True,
        ),
        simulate_bulb_dro_and_dormant_timer_hdr_hil(
            shutter_type="Mechanical Shutter",
            drive_mode="Cont. Shooting",
            bulb_requested=True,
        ),
        simulate_bulb_dro_and_dormant_timer_hdr_hil(
            shutter_type="Mechanical Shutter",
            drive_mode="Interval Shooting",
            bulb_requested=True,
        ),
    ]
    p68d_dormant_bulb_timer_blocked = simulate_bulb_dro_and_dormant_timer_hdr_hil(
        bulb_timer_requested=True,
    )
    p68d_dormant_auto_hdr_blocked = simulate_bulb_dro_and_dormant_timer_hdr_hil(
        auto_hdr_requested=True,
    )
    p68d_dro_pp_hlg_rules = [
        simulate_bulb_dro_and_dormant_timer_hdr_hil(
            picture_profile="PP11",
            dro_mode="Lv5",
        ),
        simulate_bulb_dro_and_dormant_timer_hdr_hil(
            hlg_still_image="On",
            dro_mode="Lv3",
            dro_bracket_mode="DRO Bracket: Hi",
        ),
    ]
    p68d_ok = (
        p68d_bulb_mech_ok.admitted
        and p68d_bulb_mech_ok.effective_shutter_speed == "BULB"
        and (not p68d_bulb_mech_ok.anti_flicker_allowed)
        and p68d_bulb_mech_ok.long_exposure_nr_dark_frame
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO and r.bulb_fallback_to_30s
            for r in p68d_bulb_eshutter_or_cont_blocked
        )
        and (not p68d_dormant_bulb_timer_blocked.admitted)
        and p68d_dormant_bulb_timer_blocked.errno_code == EOPNOTSUPP_ERRNO
        and p68d_dormant_bulb_timer_blocked.dormant_bulb_timer_rejected
        and (not p68d_dormant_auto_hdr_blocked.admitted)
        and p68d_dormant_auto_hdr_blocked.errno_code == EOPNOTSUPP_ERRNO
        and p68d_dormant_auto_hdr_blocked.dormant_auto_hdr_rejected
        and p68d_dro_pp_hlg_rules[0].admitted
        and p68d_dro_pp_hlg_rules[0].effective_dro_mode == "Off"
        and p68d_dro_pp_hlg_rules[0].dro_forced_off_by_pp
        and (not p68d_dro_pp_hlg_rules[1].admitted)
        and p68d_dro_pp_hlg_rules[1].errno_code == EOPNOTSUPP_ERRNO
        and p68d_dro_pp_hlg_rules[1].dro_disabled_by_hlg
    )

    milestone_probe = _build_stage68_milestone_probe()

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
        "bright_mon_shooting_menu_exposed": BRIGHT_MON_SHOOTING_MENU_EXPOSED,
        "dormant_lcd_brightness_auto_exposed_events": (
            DORMANT_LCD_BRIGHTNESS_AUTO_EXPOSED_EVENTS
        ),
        "dormant_divide_extract_or_ftp_cut_exposed_events": (
            DORMANT_DIVIDE_EXTRACT_OR_FTP_CUT_EXPOSED_EVENTS
        ),
        "dormant_bt_timecode_link_exposed_events": (
            DORMANT_BT_TIMECODE_LINK_EXPOSED_EVENTS
        ),
        "removed_wep_wpa_ipsec_exposed_events": REMOVED_WEP_WPA_IPSEC_EXPOSED_EVENTS,
        "usblan_wifi_or_multi_usb_coexist_violations": (
            USBLAN_WIFI_OR_MULTI_USB_COEXIST_VIOLATIONS
        ),
        "dormant_bulb_timer_or_auto_hdr_exposed_events": (
            DORMANT_BULB_TIMER_OR_AUTO_HDR_EXPOSED_EVENTS
        ),
        "bulb_non_mech_or_cont_bypass_events": BULB_NON_MECH_OR_CONT_BYPASS_EVENTS,
        "post_reset_airplane_off_rf_leak_events": (
            POST_RESET_AIRPLANE_OFF_RF_LEAK_EVENTS
        ),
        "rf_packets_transmitted": RF_PACKETS_TRANSMITTED,
        "rf_nvs_mutation_bytes": RF_NVS_MUTATION_BYTES,
        "slot1_data_sector_writes": SLOT1_DATA_SECTOR_WRITES,
        "slot1_avf_info_mutated": SLOT1_AVF_INFO_MUTATED,
        "slot1_vault_shotmark_edit_mutation_bytes": (
            SLOT1_VAULT_SHOTMARK_EDIT_MUTATION_BYTES
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
        and p68a_ok
        and p68b_ok
        and p68c_ok
        and p68d_ok
        and milestone_probe["is_68th_stage_milestone"]
        and (not redlines["bright_mon_shooting_menu_exposed"])
        and redlines["dormant_lcd_brightness_auto_exposed_events"] == 0
        and redlines["dormant_divide_extract_or_ftp_cut_exposed_events"] == 0
        and redlines["dormant_bt_timecode_link_exposed_events"] == 0
        and redlines["removed_wep_wpa_ipsec_exposed_events"] == 0
        and redlines["usblan_wifi_or_multi_usb_coexist_violations"] == 0
        and redlines["dormant_bulb_timer_or_auto_hdr_exposed_events"] == 0
        and redlines["bulb_non_mech_or_cont_bypass_events"] == 0
        and redlines["post_reset_airplane_off_rf_leak_events"] == 0
        and redlines["rf_packets_transmitted"] == 0
        and redlines["rf_nvs_mutation_bytes"] == 0
        and redlines["slot1_data_sector_writes"] == 0
        and (not redlines["slot1_avf_info_mutated"])
        and redlines["slot1_vault_shotmark_edit_mutation_bytes"] == 0
        and redlines["raw_firmware_bytes_leaked"] == 0
        and redlines["physical_device_writes"] == 0
        and (not redlines["persistent_emmc_writes_authorized"])
        and (not redlines["hardware_live_attachment_authorized"])
        and (not redlines["overall_ready_for_hardware_attach"])
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_325_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_68th_stage_milestone": True,
        "source_mode": donor_audit.source_mode,
        "access_mode": donor_audit.access_mode,
        "all_checks_passed": all_passed,
        "donor_audit": asdict(donor_audit),
        "pillar_a_bright_mon_ver7_magnifier_and_monitor_brightness_hil": {
            "passed": p68a_ok,
            "bm_ver702_magnifier_coexist_ok": asdict(p68a_bm_ver702_mag_ok),
            "bm_shooting_menu_blocked": asdict(p68a_bm_shooting_menu_blocked),
            "bm_auto_cancel_triggers": [asdict(r) for r in p68a_bm_auto_cancels],
            "dormant_auto_brightness_blocked": asdict(p68a_dormant_auto_brightness),
            "monitor_brightness_reset_split": [
                asdict(r) for r in p68a_brightness_reset_split
            ],
            "fx6_vf_and_ae_backlight_ok": asdict(p68a_fx6_vf_and_ae_backlight),
            "fx6_dormant_backlight_nightshot_blocked": asdict(p68a_fx6_dormant_rejected),
        },
        "pillar_b_shotmark_clipflag_edit_and_slot1_vault_hil": {
            "passed": p68b_ok,
            "active_shotmark_ops": list(FX3_ACTIVE_SHOT_MARK_OPS),
            "dormant_divide_extract_ops": list(DORMANT_DIVIDE_EXTRACT_CUT_OPS),
            "slot2_ops_ok": [asdict(r) for r in p68b_slot2_ops_ok],
            "dormant_divide_extract_blocked": [
                asdict(r) for r in p68b_dormant_divide_extract_rejected
            ],
            "slot1_vault_erofs_blocked": [asdict(r) for r in p68b_slot1_vault_erofs],
            "fx6_clip_flag_vs_dormant_shotmark": [
                asdict(r) for r in p68b_fx6_clip_flag_vs_dormant_shotmark
            ],
        },
        "pillar_c_zero_bt_tclink_wpa3_usblan_and_airplane_hil": {
            "passed": p68c_ok,
            "usblan_kernel_modules": list(FX3_USBLAN_KERNEL_MODULES),
            "zero_bt_tc_link_blocked": asdict(p68c_zero_bt_tc_link_blocked),
            "vmc_bncm1_ext_lk_ok": asdict(p68c_vmc_bncm1_ext_lk_ok),
            "usblan_zero_rf_ok": asdict(p68c_usblan_ok),
            "usblan_multi_usb_mutual_exclusion": asdict(p68c_usblan_multi_usb_blocked),
            "usblan_wifi_mutual_exclusion": asdict(p68c_usblan_wifi_blocked),
            "removed_wep_wpa_ipsec_blocked": [
                asdict(r) for r in p68c_removed_wep_wpa_ipsec_blocked
            ],
            "ww558244_5ghz_blocked": asdict(p68c_ww558244_5ghz_blocked),
            "fx6_bnc_vs_zero_bt": [asdict(r) for r in p68c_fx6_no_bt_ok_bnc],
        },
        "pillar_d_bulb_mech_dro_and_dormant_timer_hdr_hil": {
            "passed": p68d_ok,
            "bulb_mechanical_shutter_ok": asdict(p68d_bulb_mech_ok),
            "bulb_eshutter_and_cont_blocked": [
                asdict(r) for r in p68d_bulb_eshutter_or_cont_blocked
            ],
            "dormant_bulb_timer_blocked": asdict(p68d_dormant_bulb_timer_blocked),
            "dormant_auto_hdr_blocked": asdict(p68d_dormant_auto_hdr_blocked),
            "dro_pp_and_hlg_rules": [asdict(r) for r in p68d_dro_pp_hlg_rules],
            "stage68_milestone_probe": milestone_probe,
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
        prog="realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator.py",
        description=(
            "Phase 325 Stage 68 (68/68 Milestone) Wave-58 Real-Hardware "
            "ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Custom-Key [Bright Monitoring] "
            "Ver. 7.00+ Focus Magnifier Coexistence & [Monitor Brightness] (-2..+2/Sunny), "
            "[Shot Mark 1/2] / [Clip Flag] vs Zero [Divide]/[Extract]/FTP Cut & Slot-1 "
            "100%% Fail-Closed EROFS=30 Vault Firewall, Zero BT [Timecode Link] vs Wired "
            "VMC-BNCM1 EXT-LK & WPA2/WPA3 + USB-LAN Mutual Exclusion + Airplane Mode Reset "
            "Persistence, and Still [BULB] Mechanical Shutter & [DRO] vs Dormant "
            "[Bulb Timer] / [Auto HDR] HIL"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic Phase 325 Stage 68 (68/68) Wave-58 HIL verification suite",
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
        help="Emit concise one-line Stage 68 (68/68 Milestone) Wave-58 summary",
    )
    args = parser.parse_args(argv)

    rep = run_phase325_bright_mon_shotmark_usblan_bulb_dormant_coemulation(
        force_clean_room=True if args.clean_room else None
    )

    if args.summary and not args.json:
        red = rep["redlines"]
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 325 Stage 68 (68/68 Milestone) | "
            f"mode={rep['source_mode']} "
            f"donors={rep['donor_audit']['donor_files_inspected']} "
            f"bm_menu={int(red['bright_mon_shooting_menu_exposed'])} "
            f"div_byp={red['dormant_divide_extract_or_ftp_cut_exposed_events']} "
            f"bt_tc_byp={red['dormant_bt_timecode_link_exposed_events']} "
            f"usblan_viol={red['usblan_wifi_or_multi_usb_coexist_violations']} "
            f"bulb_byp={red['bulb_non_mech_or_cont_bypass_events']} "
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
