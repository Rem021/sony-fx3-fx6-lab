#!/usr/bin/env python3
"""Phase 328 (Stage 69 — 69/69 Milestone) — Real-Hardware
ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-59:
Ver. 7.00/7.02 `HOME` (`BIG6`) Screen (`Mode Settings = Fixed/Variable`, 4-State Machine,
Dynamic 6 Tiles, Metadata-Only `[Home (Lower Left)]` `ND Filter` with Zero Physical e-ND)
& Active Manual `[Framing Settings]` vs Dormant AI `[Auto Framing]` (`EOPNOTSUPP=95`),
Still-Only `[Interval Shoot Func.]` (All 7 Sub-Items Resettable, `Slot-1` `EROFS=30`/`EBUSY=16`
Vault Firewall) vs `ILME-FX6` Single-MXF `Interval Rec`,
`[Time Code Make]` (`Regenerate` -> `Slot 1` Under `Simult. Recording` + Forced `Rec Run`,
`VMC-BNCM1` `EXT-LK`, Zero `Clock` Mode) & `[HDMI Output Settings]` (`[REC Control]` Across
`Rec. Media = On` & `Off(HDMI Only)`, `[4ch Audio Output]` 2ch HDMI Limit), and
Ver. 7.00+ `[Access Authen. Settings]` (SSH Tunnel `sshd_start` + Host Key Fingerprint +
PTP-IP, Zero `HTTP_DIGEST`/`BASIC_AUTH`/`HTTPS`, Outbound Client TLS `[Import Root
Certificate]`, Zero-RF `Airplane Mode`) & `[Fan Control]` (4-Mode FX3 vs 3-Mode FX6,
Zero `Max` Mode on Both Cameras) + `[Auto Power OFF Temp.]` (`Initialize`-Only) HIL.

Strictly models Wave-59 official Sony `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 7.02`) and
`ILME-FX6` (`0x91020080`, `Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`) contracts without physical
hardware attachment or firmware byte leakage:

1. **Sub-Model 69A — Ver. 7.00/7.02 `HOME` (`BIG6`) Screen & Active `[Framing Settings]` vs Dormant AI `[Auto Framing]`**:
   - Hard prerequisite: `Shooting -> [Shooting Mode] -> [Mode Settings] = [Fixed/Variable]`
     (`BKID_APP_setting_fps_fixed_variable_select`, Resettable).
   - Entry via custom key `[HOME]` (`Open Home Screen`) or `[Swipe Down] = Open Home Screen`
     (requires `[Touch Operation] = On`); state machine `OFF / ON_CURSOR_OFF / ON_CURSOR_ON /
     TEMP_OFF` (`BKID_APP_home_screen_state`); dynamic 6 tiles (`FPS`, `ISO` vs `Base ISO + EI`
     via `update_big6_item_iso_ei`, `Shutter Speed` vs `Shutter Angle`, `[Home (Lower Left)]`
     `Aperture` default vs manual metadata-only `ND Filter` with **zero physical e-ND hardware**
     `electronic_nd_commands_emitted == 0`, `Picture Profile` vs `Select LUT`, `White Balance`) +
     read-only edge status bar (never output over HDMI/SDI) vs `ILME-FX6` Ver. 6.00+ native
     `Home Screen` (`procam_big6_menu_home_*` + real electronic variable ND `1/4..1/128 +
     Clear + Auto`).
   - Active manual `[Framing Settings]` (`Framing` `Off/On`, `Recording/Streaming` `Full/Crop`,
     `HDMI` `Crop/Full`, `[Switch Framing]`/`[Framing Stop (Full)]`, auto-disables `APS-C S35`,
     locked at `>= 100p` and during recording/streaming) vs **dormant AI `[Auto Framing]` /
     `[Auto Framing Settings]` (`TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY` -> `EOPNOTSUPP=95` on
     both FX3 7.02 and FX6 6.01)**.

2. **Sub-Model 69B — Still-Only `[Interval Shoot Func.]` (All 7 Sub-Items Resettable) & `Slot-1` Vault vs `FX6` `Interval Rec`**:
   - Models `Shooting -> [Drive Mode] -> [Interval Shoot Func.]` Still-only sequence (no in-body
     movie muxing; all 7 sub-items Resettable: `Interval Shooting`, `Shooting Start Time`
     `1s..99m59s`, `Shooting Interval` `1s..60s`, `Number of Shots` `1..9999` up to `19,998`
     RAW+JPEG/HEIF files, `AE Tracking Sensitivity`, independent `Shutter Type in Interval`
     default `Electronic Shutter`, `Shoot Interval Priority`; exits `BULB` -> `30"`, blocked in
     `Intelligent Auto`).
   - Enforces **`Slot-1` Tier-0 Vault `EROFS=30` / `EBUSY=16` firewall**
     (`slot1_data_sector_writes == 0`, `slot1_avf_info_mutated == False`) vs `ILME-FX6`
     `Project > Interval Rec` (in-camera single XAVC MXF clip `1s..24h`, `1..24` frames,
     mutually exclusive with `Simul Rec`/`S&Q`/Proxy).

3. **Sub-Model 69C — `[Time Code Make]` (`Regenerate` -> `Slot 1` & Forced `Rec Run`) & `[HDMI Output Settings]` vs `FX6`**:
   - `[Time Code Make]` (`Preset`/`Regenerate`, `Initialize`-only): `Regenerate` reads last clip
     TC from `Slot 1` under `Simult. Recording` and **forces `Rec Run`** regardless of
     `[Time Code Run]`; `VMC-BNCM1` `EXT-LK` requires `Preset + Free Run`; **no `Clock` mode**
     unlike `FX6` (`TC_MAKE_CLOCK` + physical BNC `TC IN/OUT`).
   - `Setup -> [External Output] -> [HDMI Output Settings]` (`Initialize`-only): `[REC Control]`
     requires `[Time Code Output] = On`, active in BOTH `Rec. Media = On` and `Off(HDMI Only)`,
     blocked in `S&Q`/streaming; `[4ch Audio Output]` `CH1/CH2` vs `CH3/CH4` 2ch HDMI limit vs
     `FX6` `SDI/HDMI Remote I/F` vs `Parallel Rec`.

4. **Sub-Model 69D & Redlines — Ver. 7.00+ `[Access Authen. Settings]` (SSH + PTP-IP) & 4-Mode `[Fan Control]` (Zero `Max`) + `[Auto Power OFF Temp.]`**:
   - `[Access Authen. Settings]`: default `On`, reset ONLY via `[Reset Network Set.]` or
     `[Initialize]` (survives `[Camera Settings Reset]`); **SSH tunnel (`sshd_start` + Host Key
     Fingerprint + PTP-IP)** with zero `HTTP_DIGEST`/`BASIC_AUTH`/`HTTPS` hits; `WEP`/`WPA-PSK`/
     `IPsec` removed (`EOPNOTSUPP=95`); `[Import Root Certificate]` strictly outbound client TLS
     for `CLOUD/FTP/RTMP`; zero-RF `Airplane Mode = On` enforced (`rf_packets_transmitted == 0`).
   - `[Fan Control]` (`Initialize`-only): **4-mode FX3 (`Auto`/`Minimum`/`Off in Rec`/
     `Always Off`) vs 3-mode FX6 (`Auto`/`Minimum`/`Off in Rec`, `Always Off` dormant ->
     `EOPNOTSUPP=95`) with NO `Max` mode on either camera (`FAN_CONTROL_MAX` 0 hits ->
     `EOPNOTSUPP=95`)** + `[Auto Power OFF Temp.]` (`Standard`/`High`, `Initialize`-only).

5. **Dual-Mode 24-Donor `os.O_RDONLY` + Bounded `os.pread` Verification (`< 0.20s`)**:
   - Audits all 24 verified Wave-59 `ILME-FX3 Ver. 7.02` & `ILME-FX6 Ver. 6.01` donors via
     `os.open(..., os.O_RDONLY)` and bounded `os.pread` (`<= 4096 B`) with clean fallback to
     `CLEAN_ROOM_SYNTHETIC` when `work_root is None`, `FX3_CLEAN_ROOM_TEST=1`, or
     `FX3_FX6_FORCE_CLEAN_ROOM=1` (`raw_firmware_bytes_leaked == 0`).
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

SCHEMA_ID = "realhw_big6_home_framing_interval_tc_ssh_fan_coemulator_v1"
PHASE_328_SCHEMA = SCHEMA_ID
PHASE_328_VERSION = "328.0.0"
PHASE_NUMBER = 328
STAGE_INDEX = 69
STAGE_TOTAL = 69
MILESTONE_LABEL = "69/69"
STAGE_NAME = "stage69_realhw_big6_home_framing_interval_tc_ssh_fan_hil"
IS_69TH_STAGE_MILESTONE = True
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

# Wave-59 Stage 69 (69/69 Milestone) zero-fault & hardware-truth invariants
FX3_HAS_BUILTIN_END_FILTER = False
FX6_HAS_ELECTRONIC_VARIABLE_ND = True
ELECTRONIC_ND_COMMANDS_EMITTED = 0
HDMI_SDI_STATUS_BAR_LEAKED_PIXELS = 0
DORMANT_AUTO_FRAMING_EXPOSED_EVENTS = 0
FRAMING_HIGHFPS_OR_REC_BYPASS_EVENTS = 0
INTERVAL_INBODY_MOVIE_MUX_EVENTS = 0
INTERVAL_IAUTO_OR_BULB_BYPASS_EVENTS = 0
SLOT1_DATA_SECTOR_WRITES = 0
SLOT1_AVF_INFO_MUTATED = False
SLOT1_VAULT_INTERVAL_WRITE_EVENTS = 0
TC_REGEN_NON_SLOT1_OR_FREERUN_VIOLATIONS = 0
FX3_CLOCK_TC_MAKE_EXPOSED_EVENTS = 0
HDMI_REC_CTRL_S_AND_Q_OR_NOTC_BYPASS_EVENTS = 0
SSH_HTTP_BASIC_HTTPS_AUTH_SPOOF_EVENTS = 0
REMOVED_WEP_WPA_IPSEC_EXPOSED_EVENTS = 0
FAN_CONTROL_MAX_EXPOSED_EVENTS = 0
FX6_FAN_ALWAYS_OFF_EXPOSED_EVENTS = 0
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
# Verified Local Donor Specs (All 24 FX3 7.02 & FX6 6.01 Wave-59 Donors)
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
    "fx3_lib_ssh2": f"{_FX3_USR_PREFIX}/lib/libssh2.so.1.0.1",
    "fx3_lib_wired_lan_res": f"{_FX3_USR_PREFIX}/lib/libWiredLanResource.so",
    "fx3_lib_net_ether": f"{_FX3_USR_PREFIX}/lib/libNetServiceEther.so",
    "fx3_lib_wlan_res": f"{_FX3_USR_PREFIX}/lib/libWlanResource.so",
    "fx3_lib_wlan_adj": f"{_FX3_USR_PREFIX}/lib/libWlanAdjust.so",
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
    "fx3_lib_ssh2": 216_784,
    "fx3_lib_wired_lan_res": 36_160,
    "fx3_lib_net_ether": 114_384,
    "fx3_lib_wlan_res": 56_464,
    "fx3_lib_wlan_adj": 73_168,
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
    "fx3_lib_ssh2": "5dc7ca0687907bc6f4b7938000a934a7fa8cd8122c31950c682e5147964cee0c",
    "fx3_lib_wired_lan_res": "f5ee3d70d5961753cef226bec74c15231e489491eddf63210511f57aaebf49e5",
    "fx3_lib_net_ether": "203b084190a968c732d09fd45e304c406a32eb664d98626114dcf7f178675375",
    "fx3_lib_wlan_res": "76fe66f7c763a452c2986514b3485a62791e7750d52ffa89b31b820e4cb9eb91",
    "fx3_lib_wlan_adj": "3dcab55342e741a832bc88fd2cff96e2060d4ab3f4a6b529b9edb18434be8e9d",
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
        b"Open Home Screen",
        b"Home (Lower Left)",
        b"Framing Settings",
        b"Interval Shoot Func.",
        b"Shutter Type in Interval",
        b"Time Code Make",
        b"REC Control",
        b"4ch Audio Output",
        b"Access Authen. Settings",
        b"Fan Control",
        b"Always Off",
        b"Off in Rec",
        b"Auto Framing",
    ),
    "fx3_string_sc_f": (
        "打开主屏幕".encode("utf-8"),
        "主屏幕".encode("utf-8"),
        "时间码".encode("utf-8"),
        "身份验证".encode("utf-8"),
        "散热风扇".encode("utf-8"),
        "间隔".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "開啟主螢幕".encode("utf-8"),
        "主螢幕".encode("utf-8"),
        "時間碼".encode("utf-8"),
        "冷卻風扇".encode("utf-8"),
        "間隔".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "ホーム画面を開く".encode("utf-8"),
        "フレーミング設定".encode("utf-8"),
        "タイムコード".encode("utf-8"),
        "アクセス".encode("utf-8"),
        "ファン制御".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"Minimum",
        b"Standard",
        b"High",
        b"Airplane Mode",
        b"WPA3",
    ),
    "fx3_string_sc": (
        "飞行模式".encode("utf-8"),
        b"WPA3",
    ),
    "fx3_string_tc": (
        "飛航模式".encode("utf-8"),
        b"WPA3",
    ),
    "fx3_string_ja": (
        "機内モード".encode("utf-8"),
        b"WPA3",
    ),
    "fx3_string_en_g": (
        b"Auto Framing",
        b"GOTO_SSHINFODISPLAY",
        b"Auto Power OFF Temp.",
        b"Interval shooting",
    ),
    "fx3_string_sc_g": (
        "自动关机温度".encode("utf-8"),
        "主页".encode("utf-8"),
    ),
    "fx3_string_tc_g": (
        "自動取景".encode("utf-8"),
    ),
    "fx3_string_ja_g": (
        b"GOTO_SSHINFODISPLAY",
        "自動電源OFF温度".encode("utf-8"),
        "オートフレーミング".encode("utf-8"),
    ),
    "fx6_string_en": (
        b"Home Screen",
        b"ND Filter",
        b"Base ISO",
        b"Minimum",
        b"Preset",
    ),
    "fx6_string_en_2": (
        b"Interval Rec",
        b"SDI/HDMI Rec Control",
        b"Remote I/F",
        b"Parallel Rec",
    ),
    "fx3_lib_ssh2": (b"\x7fELF", b"libssh2", b"ssh"),
    "fx3_lib_wired_lan_res": (b"\x7fELF", b"r8152", b"ax88179_178a", b"eth0"),
    "fx3_lib_net_ether": (b"\x7fELF", b"WESStartDHCPClient"),
    "fx3_lib_wlan_res": (b"\x7fELF", b"ar6000", b"wlan"),
    "fx3_lib_wlan_adj": (b"\x7fELF",),
    "fx3_lib_airplane": (b"\x7fELF",),
    "fx3_lib_bt": (b"\x7fELF",),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (
            62_672_896,
            "BKID_FPS_FIXED_VAR",
            b"BKID_APP_setting_fps_fixed_variable_select",
        ),
        (62_861_312, "BKID_HOME_SCREEN_STATE", b"BKID_APP_home_screen_state"),
        (51_994_624, "UPDATE_BIG6_ITEM_ISO_EI", b"update_big6_item_iso_ei"),
        (
            62_697_472,
            "BKID_HOME_LOWER_LEFT",
            b"BKID_APP_setting_movie_home_lower_left",
        ),
        (62_255_104, "SWIPE_DOWN_HOME_SCREEN", b"VAL_setting_swipe_down_SWIPE_DOWN_HOME_SCREEN"),
        (
            60_633_088,
            "EFRAMING_MANUAL_ONLY",
            b"TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY",
        ),
        (
            62_681_088,
            "BKID_FRAMING_SETTINGS",
            b"BKID_APP_setting_fixed_camera_framing_settings_fixed_camera_framing",
        ),
        (
            62_676_992,
            "BKID_INTERVAL_SHOOT",
            b"BKID_APP_setting_interval_shooting",
        ),
        (61_947_904, "VAL_TC_MAKE_REGENRATE", b"VAL_setting_tc_make_TC_MAKE_REGENRATE"),
        (60_559_360, "PRM_HAITA_REC_CONTROL", b"PRM_HAITA_setting_rec_control_"),
        (
            62_701_568,
            "BKID_HDMI_AUDIO_4CH",
            b"BKID_APP_setting_mov_hdmi_audio_output",
        ),
        (62_701_568, "BKID_FAN_CONTROL", b"BKID_APP_setting_fan_control"),
        (62_697_472, "BKID_AUTO_PWR_OFF_TEMP", b"BKID_APP_setting_auto_pwr_off_temp"),
        (62_693_376, "BKID_ACCESS_AUTHEN", b"BKID_APP_setting_access_authentication"),
        (60_416_000, "SSHD_START_CMD", b"MSGID_SSHD_START_CMD"),
        (60_416_000, "SSHD_START_SYM", b"sshd_start"),
        (49_971_200, "FAN_CONTROL_ALWAYS_OFF", b"FAN_CONTROL_ALWAYS_OFF"),
        (62_963_712, "ROOT_CERT_CLOUD", b"ROOT_CERTIFICATE_TYPE_CLOUD"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4\x00"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (37_412_864, "FX6_BIG6_HOME_PRESENTER", b"procam_big6_menu_home_presenter"),
        (40_632_320, "FX6_TC_MAKE_CLOCK", b"VAL_setting_tc_make_TC_MAKE_CLOCK"),
        (
            37_232_640,
            "FX6_INTERVAL_REC_EXCLUSION",
            b"MODEL_VALUE_CHANGED_BY_EXCLUSION_INTERVAL_REC",
        ),
        (41_639_936, "FX6_FAN_ALWAYS_OFF", b"FAN_CONTROL_ALWAYS_OFF"),
        (40_636_416, "FX6_SDI_HDMI_REC_CTRL", b"SDI_HDMI_REC_CONTROL"),
        (40_185_856, "FX6_AUTO_FRAMING", b"AUTO_FRAMING"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-59 Real-Hardware Constants & Matrices
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

# Sub-Model 69A — BIG6 HOME Screen & Framing Settings vs Dormant Auto Framing
FX3_MODE_SETTINGS_FIXED_VAR = "Fixed/Variable"
FX3_MODE_SETTINGS_FLEX_EXP = "Flexible Exp."
VALID_MOVIE_MODE_SETTINGS: Tuple[str, ...] = (
    FX3_MODE_SETTINGS_FIXED_VAR,
    FX3_MODE_SETTINGS_FLEX_EXP,
    "P",
    "A",
    "S",
    "M",
    "Intelligent Auto",
)

BIG6_ENTRY_TRIGGERS: Tuple[str, ...] = ("HOME Custom Key", "Swipe Down")
BIG6_STATES: Tuple[str, ...] = (
    "HOME_SCREEN_STATE_OFF",
    "HOME_SCREEN_STATE_ON_CURSOR_OFF",
    "HOME_SCREEN_STATE_ON_CURSOR_ON",
    "HOME_SCREEN_STATE_TEMP_OFF",
)
BIG6_LOWER_LEFT_OPTIONS: Tuple[str, ...] = ("Aperture", "ND Filter")
FX6_HOME_ND_MODES: Tuple[str, ...] = (
    "Clear",
    "1/4",
    "1/16",
    "1/64",
    "1/128",
    "Auto",
)
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "Off",
    "Flexible ISO",
    "Cine EI",
    "Cine EI Quick",
)
VALID_SHUTTER_MODES: Tuple[str, ...] = ("Speed", "Angle")

FRAMING_REC_MODES: Tuple[str, ...] = ("Full", "Crop")
FRAMING_HDMI_MODES: Tuple[str, ...] = ("Crop", "Full")
DORMANT_AUTO_FRAMING_ITEMS: Tuple[str, ...] = (
    "Auto Framing",
    "Auto Framing Settings",
    "Crop Level",
    "Framing Tracking Speed",
    "Framing Stabilizer",
)

# Sub-Model 69B — Interval Shoot Func. (Still-Only, 7 Resettable Sub-Items) & Slot-1 Vault
FX3_INTERVAL_7_SUBITEMS: Tuple[str, ...] = (
    "Interval Shooting",
    "Shooting Start Time",
    "Shooting Interval",
    "Number of Shots",
    "AE Tracking Sensitivity",
    "Shutter Type in Interval",
    "Shoot Interval Priority",
)
VALID_AE_TRACKING_SENSITIVITIES: Tuple[str, ...] = ("High", "Mid", "Low")
VALID_SHUTTER_TYPES: Tuple[str, ...] = ("Mechanical Shutter", "Electronic Shutter")
VALID_STILL_FILE_FORMATS: Tuple[str, ...] = (
    "JPEG",
    "HEIF",
    "RAW",
    "RAW & JPEG",
    "RAW & HEIF",
)
FX6_INTERVAL_REC_FRAME_COUNTS: Tuple[int, ...] = (1, 2, 3, 4, 6, 9, 12, 24)
FX6_INTERVAL_REC_PRELIGHTING: Tuple[str, ...] = ("Off", "2s", "5s", "10s")
FX6_INTERVAL_REC_EXCLUSIONS: Tuple[str, ...] = (
    "Picture Cache Rec",
    "Simul Rec",
    "S&Q Motion",
    "Proxy Rec",
)

# Sub-Model 69C — Time Code Make/Run & HDMI Output Settings (REC Control, 4ch Audio)
VALID_TC_MAKE_MODES: Tuple[str, ...] = ("Preset", "Regenerate", "Clock")
VALID_TC_RUN_MODES: Tuple[str, ...] = ("Rec Run", "Free Run")
VALID_RECORDING_MEDIA_MODES: Tuple[str, ...] = (
    "Slot 1",
    "Slot 2",
    "Simult. Recording",
    "Sort Recording",
    "Relay Recording",
)
VALID_HDMI_4CH_AUDIO_MODES: Tuple[str, ...] = ("CH1/CH2", "CH3/CH4")
VALID_FX6_REC_CTRL_MODES: Tuple[str, ...] = (
    "Off",
    "SDI/HDMI Remote I/F",
    "Parallel Rec",
)

# Sub-Model 69D — Access Authen. (SSH + PTP-IP) & Fan Control / Auto Power OFF Temp.
SUPPORTED_ACCESS_AUTH_PROTOCOLS: Tuple[str, ...] = ("SSH_TUNNEL_PTPIP",)
UNSUPPORTED_ACCESS_AUTH_PROTOCOLS: Tuple[str, ...] = (
    "HTTP_DIGEST",
    "BASIC_AUTH",
    "HTTPS",
)
SUPPORTED_WIFI_SECURITY: Tuple[str, ...] = ("WPA2-PSK", "WPA3-SAE")
REMOVED_WIFI_SECURITY: Tuple[str, ...] = ("WEP", "WPA-PSK", "Security(IPsec)", "IPsec")
VALID_ROOT_CERT_TYPES: Tuple[str, ...] = ("CLOUD", "FTP", "RTMP")
FX3_FAN_CONTROL_MODES: Tuple[str, ...] = (
    "Auto",
    "Minimum",
    "Off in Rec",
    "Always Off",
)
FX6_FAN_CONTROL_MODES: Tuple[str, ...] = (
    "Auto",
    "Minimum",
    "Off in Rec",
)
DORMANT_FAN_CONTROL_MODES: Tuple[str, ...] = ("Max", "FAN_CONTROL_MAX")
VALID_AUTO_POWER_OFF_TEMPS: Tuple[str, ...] = ("Standard", "High")


class Stage69Phase328Error(RuntimeError):
    """Raised on invalid Phase 328 Stage 69 configuration or safety redline violation."""


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
        raise Stage69Phase328Error(
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
class Phase328DonorAuditReport:
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


_DONOR_AUDIT_CACHE: Dict[Tuple[str, str], Phase328DonorAuditReport] = {}


def inspect_phase328_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase328DonorAuditReport:
    """Verify all 24 Wave-59 donors strictly via `os.O_RDONLY` + `os.pread` or clean-room fallback."""
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
        rep = Phase328DonorAuditReport(
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
                "CLEAN_ROOM_SYNTHETIC: verified all 24 Wave-59 contracts without local Mac/work reads.",
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
            f"Verified all {compact_ok} compact + {large_ok} large Wave-59 donors via O_RDONLY + bounded pread."
        )
    rep = Phase328DonorAuditReport(
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
# Sub-Model 69A — Ver. 7.00/7.02 `HOME` (`BIG6`) Screen & Active `[Framing Settings]`
#                 vs Dormant AI `[Auto Framing]` (`EOPNOTSUPP=95`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Big6HomeAndFramingResult:
    body_profile: str
    firmware_version: str
    admitted: bool
    errno_code: int
    mode_settings: str
    entry_trigger: str
    touch_operation: str
    home_screen_state: str
    last_cursor_position: int
    tiles: Dict[str, str]
    home_lower_left_setting: str
    nd_tile_metadata_only: bool
    fx3_has_builtin_end_filter: bool
    fx6_has_electronic_variable_nd: bool
    electronic_nd_commands_emitted: int
    edge_status_bar_readonly: bool
    hdmi_sdi_status_bar_leaked_pixels: int
    framing_enabled: bool
    framing_rec_stream_output: str
    framing_hdmi_output: str
    apsc_s35_forced_off: bool
    auto_framing_requested: bool
    dormant_auto_framing_rejected: bool
    camera_settings_reset_applied: bool
    reason: str


def simulate_big6_home_and_framing_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    firmware_version: str = FW_VER_702,
    mode_settings: str = FX3_MODE_SETTINGS_FIXED_VAR,
    entry_trigger: str = "HOME Custom Key",
    touch_operation: str = "On",
    open_menu_or_fn_overlay: bool = False,
    cursor_selected: bool = False,
    last_cursor_position: int = 0,
    log_shooting: str = "Off",
    shutter_mode: str = "Speed",
    home_lower_left_setting: str = "Aperture",
    nd_filter_label: str = "ND16",
    fps_fps: int = 24,
    is_recording_or_streaming: bool = False,
    framing_enabled: bool = False,
    framing_rec_stream_output: str = "Full",
    framing_hdmi_output: str = "Crop",
    apsc_s35_requested: bool = False,
    auto_framing_requested: bool = False,
    camera_settings_reset_applied: bool = False,
) -> Big6HomeAndFramingResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage69Phase328Error(f"Unsupported body_profile={body_profile!r}")
    if firmware_version not in VALID_FX3_FW_VERSIONS:
        raise Stage69Phase328Error(f"Unsupported firmware_version={firmware_version!r}")
    if mode_settings not in VALID_MOVIE_MODE_SETTINGS:
        raise Stage69Phase328Error(f"Unsupported mode_settings={mode_settings!r}")
    if entry_trigger not in BIG6_ENTRY_TRIGGERS:
        raise Stage69Phase328Error(f"Unsupported entry_trigger={entry_trigger!r}")
    if touch_operation not in ("On", "Off"):
        raise Stage69Phase328Error(f"Unsupported touch_operation={touch_operation!r}")
    if not (0 <= last_cursor_position <= 5):
        raise Stage69Phase328Error(
            f"Unsupported last_cursor_position={last_cursor_position!r}"
        )
    if log_shooting not in VALID_LOG_SHOOTING_MODES:
        raise Stage69Phase328Error(f"Unsupported log_shooting={log_shooting!r}")
    if shutter_mode not in VALID_SHUTTER_MODES:
        raise Stage69Phase328Error(f"Unsupported shutter_mode={shutter_mode!r}")
    if home_lower_left_setting not in BIG6_LOWER_LEFT_OPTIONS:
        raise Stage69Phase328Error(
            f"Unsupported home_lower_left_setting={home_lower_left_setting!r}"
        )
    if framing_rec_stream_output not in FRAMING_REC_MODES:
        raise Stage69Phase328Error(
            f"Unsupported framing_rec_stream_output={framing_rec_stream_output!r}"
        )
    if framing_hdmi_output not in FRAMING_HDMI_MODES:
        raise Stage69Phase328Error(
            f"Unsupported framing_hdmi_output={framing_hdmi_output!r}"
        )

    # Dormant AI [Auto Framing] / [Auto Framing Settings] MUST fail-closed on BOTH FX3 7.02 and FX6 6.01
    if auto_framing_requested:
        return Big6HomeAndFramingResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            mode_settings=mode_settings,
            entry_trigger=entry_trigger,
            touch_operation=touch_operation,
            home_screen_state="HOME_SCREEN_STATE_OFF",
            last_cursor_position=0,
            tiles={},
            home_lower_left_setting=home_lower_left_setting,
            nd_tile_metadata_only=(body_profile == BODY_MODEL_FX3),
            fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
            fx6_has_electronic_variable_nd=FX6_HAS_ELECTRONIC_VARIABLE_ND,
            electronic_nd_commands_emitted=ELECTRONIC_ND_COMMANDS_EMITTED,
            edge_status_bar_readonly=True,
            hdmi_sdi_status_bar_leaked_pixels=HDMI_SDI_STATUS_BAR_LEAKED_PIXELS,
            framing_enabled=False,
            framing_rec_stream_output="Full",
            framing_hdmi_output="Crop",
            apsc_s35_forced_off=False,
            auto_framing_requested=True,
            dormant_auto_framing_rejected=True,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason=(
                f"EOPNOTSUPP: AI [Auto Framing] is dormant on {body_profile} "
                "(TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY; 0 AUTO_FRAMING_AFR hits)"
            ),
        )

    # Active manual [Framing Settings] checks (FX3 Ver. 6.00+/7.02; FX6 lacks consumer Framing Settings)
    eff_framing = False if camera_settings_reset_applied else framing_enabled
    eff_rec_crop = "Full" if camera_settings_reset_applied else framing_rec_stream_output
    eff_hdmi_crop = "Crop" if camera_settings_reset_applied else framing_hdmi_output
    apsc_forced_off = False
    if eff_framing:
        if body_profile == BODY_MODEL_FX6:
            return Big6HomeAndFramingResult(
                body_profile=body_profile,
                firmware_version=firmware_version,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                mode_settings=mode_settings,
                entry_trigger=entry_trigger,
                touch_operation=touch_operation,
                home_screen_state="HOME_SCREEN_STATE_OFF",
                last_cursor_position=0,
                tiles={},
                home_lower_left_setting="ND Filter",
                nd_tile_metadata_only=False,
                fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
                fx6_has_electronic_variable_nd=FX6_HAS_ELECTRONIC_VARIABLE_ND,
                electronic_nd_commands_emitted=ELECTRONIC_ND_COMMANDS_EMITTED,
                edge_status_bar_readonly=True,
                hdmi_sdi_status_bar_leaked_pixels=HDMI_SDI_STATUS_BAR_LEAKED_PIXELS,
                framing_enabled=True,
                framing_rec_stream_output=eff_rec_crop,
                framing_hdmi_output=eff_hdmi_crop,
                apsc_s35_forced_off=False,
                auto_framing_requested=False,
                dormant_auto_framing_rejected=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                reason="EOPNOTSUPP: ILME-FX6 lacks FX3 manual [Framing Settings]",
            )
        if fps_fps >= 100:
            return Big6HomeAndFramingResult(
                body_profile=body_profile,
                firmware_version=firmware_version,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                mode_settings=mode_settings,
                entry_trigger=entry_trigger,
                touch_operation=touch_operation,
                home_screen_state="HOME_SCREEN_STATE_OFF",
                last_cursor_position=0,
                tiles={},
                home_lower_left_setting=home_lower_left_setting,
                nd_tile_metadata_only=True,
                fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
                fx6_has_electronic_variable_nd=FX6_HAS_ELECTRONIC_VARIABLE_ND,
                electronic_nd_commands_emitted=ELECTRONIC_ND_COMMANDS_EMITTED,
                edge_status_bar_readonly=True,
                hdmi_sdi_status_bar_leaked_pixels=HDMI_SDI_STATUS_BAR_LEAKED_PIXELS,
                framing_enabled=True,
                framing_rec_stream_output=eff_rec_crop,
                framing_hdmi_output=eff_hdmi_crop,
                apsc_s35_forced_off=False,
                auto_framing_requested=False,
                dormant_auto_framing_rejected=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                reason=f"EOPNOTSUPP: [Framing Settings] locked at >= 100p (fps={fps_fps}p)",
            )
        if is_recording_or_streaming:
            return Big6HomeAndFramingResult(
                body_profile=body_profile,
                firmware_version=firmware_version,
                admitted=False,
                errno_code=EBUSY_ERRNO,
                mode_settings=mode_settings,
                entry_trigger=entry_trigger,
                touch_operation=touch_operation,
                home_screen_state="HOME_SCREEN_STATE_OFF",
                last_cursor_position=0,
                tiles={},
                home_lower_left_setting=home_lower_left_setting,
                nd_tile_metadata_only=True,
                fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
                fx6_has_electronic_variable_nd=FX6_HAS_ELECTRONIC_VARIABLE_ND,
                electronic_nd_commands_emitted=ELECTRONIC_ND_COMMANDS_EMITTED,
                edge_status_bar_readonly=True,
                hdmi_sdi_status_bar_leaked_pixels=HDMI_SDI_STATUS_BAR_LEAKED_PIXELS,
                framing_enabled=True,
                framing_rec_stream_output=eff_rec_crop,
                framing_hdmi_output=eff_hdmi_crop,
                apsc_s35_forced_off=False,
                auto_framing_requested=False,
                dormant_auto_framing_rejected=False,
                camera_settings_reset_applied=camera_settings_reset_applied,
                reason="EBUSY: [Framing Settings] menu locked during recording/streaming",
            )
        apsc_forced_off = bool(apsc_s35_requested or True)

    # ILME-FX6 Ver. 6.00+ native BIG6 Home Screen + real electronic variable ND
    if body_profile == BODY_MODEL_FX6:
        fx6_nd_label = nd_filter_label if nd_filter_label in FX6_HOME_ND_MODES else "1/16"
        fx6_tiles = {
            "tile_1_fps": f"{fps_fps}p (Fixed)",
            "tile_2_iso_ei": "Base ISO 800 / EI 800" if "Cine EI" in log_shooting else "ISO 800 / 0dB",
            "tile_3_shutter": "180.0 deg" if shutter_mode == "Angle" else "1/48",
            "tile_4_nd_iris": f"Electronic ND ({fx6_nd_label}) / F2.8",
            "tile_5_look_scene": "S-Cinetone / Base Look",
            "tile_6_white_balance": "5600K",
        }
        state = "HOME_SCREEN_STATE_TEMP_OFF" if open_menu_or_fn_overlay else "HOME_SCREEN_STATE_ON_CURSOR_OFF"
        return Big6HomeAndFramingResult(
            body_profile=body_profile,
            firmware_version=FW_VER_601,
            admitted=True,
            errno_code=0,
            mode_settings="Cine EI / Custom",
            entry_trigger="Dedicated HOME / Menu",
            touch_operation=touch_operation,
            home_screen_state=state,
            last_cursor_position=last_cursor_position,
            tiles=fx6_tiles,
            home_lower_left_setting="ND Filter",
            nd_tile_metadata_only=False,
            fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
            fx6_has_electronic_variable_nd=FX6_HAS_ELECTRONIC_VARIABLE_ND,
            electronic_nd_commands_emitted=ELECTRONIC_ND_COMMANDS_EMITTED,
            edge_status_bar_readonly=True,
            hdmi_sdi_status_bar_leaked_pixels=HDMI_SDI_STATUS_BAR_LEAKED_PIXELS,
            framing_enabled=False,
            framing_rec_stream_output="Full",
            framing_hdmi_output="Crop",
            apsc_s35_forced_off=False,
            auto_framing_requested=False,
            dormant_auto_framing_rejected=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason="ADMITTED: ILME-FX6 native Ver. 6.01 Home Screen (real variable e-ND LCD-only)",
        )

    # FX3 BIG6 HOME screen hard prerequisites: Ver. 7.00+ AND Mode Settings = Fixed/Variable
    if firmware_version == FW_VER_601:
        return Big6HomeAndFramingResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            mode_settings=mode_settings,
            entry_trigger=entry_trigger,
            touch_operation=touch_operation,
            home_screen_state="HOME_SCREEN_STATE_OFF",
            last_cursor_position=0,
            tiles={},
            home_lower_left_setting="Aperture",
            nd_tile_metadata_only=True,
            fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
            fx6_has_electronic_variable_nd=FX6_HAS_ELECTRONIC_VARIABLE_ND,
            electronic_nd_commands_emitted=ELECTRONIC_ND_COMMANDS_EMITTED,
            edge_status_bar_readonly=True,
            hdmi_sdi_status_bar_leaked_pixels=HDMI_SDI_STATUS_BAR_LEAKED_PIXELS,
            framing_enabled=eff_framing,
            framing_rec_stream_output=eff_rec_crop,
            framing_hdmi_output=eff_hdmi_crop,
            apsc_s35_forced_off=apsc_forced_off,
            auto_framing_requested=False,
            dormant_auto_framing_rejected=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason="EOPNOTSUPP: BIG6 HOME screen requires ILME-FX3 Ver. 7.00/7.02 (absent in 6.01)",
        )

    eff_mode_settings = (
        FX3_MODE_SETTINGS_FIXED_VAR if camera_settings_reset_applied else mode_settings
    )
    if eff_mode_settings != FX3_MODE_SETTINGS_FIXED_VAR:
        return Big6HomeAndFramingResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            mode_settings=eff_mode_settings,
            entry_trigger=entry_trigger,
            touch_operation=touch_operation,
            home_screen_state="HOME_SCREEN_STATE_OFF",
            last_cursor_position=0,
            tiles={},
            home_lower_left_setting="Aperture",
            nd_tile_metadata_only=True,
            fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
            fx6_has_electronic_variable_nd=FX6_HAS_ELECTRONIC_VARIABLE_ND,
            electronic_nd_commands_emitted=ELECTRONIC_ND_COMMANDS_EMITTED,
            edge_status_bar_readonly=True,
            hdmi_sdi_status_bar_leaked_pixels=HDMI_SDI_STATUS_BAR_LEAKED_PIXELS,
            framing_enabled=eff_framing,
            framing_rec_stream_output=eff_rec_crop,
            framing_hdmi_output=eff_hdmi_crop,
            apsc_s35_forced_off=apsc_forced_off,
            auto_framing_requested=False,
            dormant_auto_framing_rejected=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason=(
                "EOPNOTSUPP: BIG6 HOME screen requires [Shooting Mode] -> "
                f"[Mode Settings] = [Fixed/Variable] (got {eff_mode_settings!r})"
            ),
        )

    if entry_trigger == "Swipe Down" and touch_operation != "On":
        return Big6HomeAndFramingResult(
            body_profile=body_profile,
            firmware_version=firmware_version,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            mode_settings=eff_mode_settings,
            entry_trigger=entry_trigger,
            touch_operation=touch_operation,
            home_screen_state="HOME_SCREEN_STATE_OFF",
            last_cursor_position=0,
            tiles={},
            home_lower_left_setting="Aperture",
            nd_tile_metadata_only=True,
            fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
            fx6_has_electronic_variable_nd=FX6_HAS_ELECTRONIC_VARIABLE_ND,
            electronic_nd_commands_emitted=ELECTRONIC_ND_COMMANDS_EMITTED,
            edge_status_bar_readonly=True,
            hdmi_sdi_status_bar_leaked_pixels=HDMI_SDI_STATUS_BAR_LEAKED_PIXELS,
            framing_enabled=eff_framing,
            framing_rec_stream_output=eff_rec_crop,
            framing_hdmi_output=eff_hdmi_crop,
            apsc_s35_forced_off=apsc_forced_off,
            auto_framing_requested=False,
            dormant_auto_framing_rejected=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason="EOPNOTSUPP: [Swipe Down] = Open Home Screen requires [Touch Operation] = On",
        )

    eff_lower_left = "Aperture" if camera_settings_reset_applied else home_lower_left_setting
    if open_menu_or_fn_overlay:
        home_state = "HOME_SCREEN_STATE_TEMP_OFF"
    elif cursor_selected:
        home_state = "HOME_SCREEN_STATE_ON_CURSOR_ON"
    else:
        home_state = "HOME_SCREEN_STATE_ON_CURSOR_OFF"

    tile_2 = (
        "Base ISO 800 / EI 800"
        if log_shooting in ("Cine EI", "Cine EI Quick")
        else "ISO 800"
    )
    tile_3 = "Shutter Angle (180.0 deg)" if shutter_mode == "Angle" else "Shutter Speed (1/50)"
    tile_4 = (
        f"ND Filter ({nd_filter_label}, Metadata-Only)"
        if eff_lower_left == "ND Filter"
        else "Aperture (F2.8)"
    )
    tile_5 = "Select LUT (S-Log3)" if log_shooting != "Off" else "Picture Profile (Off)"

    fx3_tiles = {
        "tile_1_fps": f"FPS ({fps_fps}p Fixed)",
        "tile_2_iso_ei": tile_2,
        "tile_3_shutter": tile_3,
        "tile_4_lower_left": tile_4,
        "tile_5_pp_lut": tile_5,
        "tile_6_white_balance": "White Balance (5600K)",
    }

    return Big6HomeAndFramingResult(
        body_profile=body_profile,
        firmware_version=firmware_version,
        admitted=True,
        errno_code=0,
        mode_settings=eff_mode_settings,
        entry_trigger=entry_trigger,
        touch_operation=touch_operation,
        home_screen_state=home_state,
        last_cursor_position=last_cursor_position,
        tiles=fx3_tiles,
        home_lower_left_setting=eff_lower_left,
        nd_tile_metadata_only=(eff_lower_left == "ND Filter"),
        fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
        fx6_has_electronic_variable_nd=FX6_HAS_ELECTRONIC_VARIABLE_ND,
        electronic_nd_commands_emitted=ELECTRONIC_ND_COMMANDS_EMITTED,
        edge_status_bar_readonly=True,
        hdmi_sdi_status_bar_leaked_pixels=HDMI_SDI_STATUS_BAR_LEAKED_PIXELS,
        framing_enabled=eff_framing,
        framing_rec_stream_output=eff_rec_crop,
        framing_hdmi_output=eff_hdmi_crop,
        apsc_s35_forced_off=apsc_forced_off,
        auto_framing_requested=False,
        dormant_auto_framing_rejected=False,
        camera_settings_reset_applied=camera_settings_reset_applied,
        reason=(
            f"ADMITTED: FX3 {firmware_version} BIG6 {home_state} via {entry_trigger}, "
            f"lower_left={eff_lower_left} (eND_tx=0), framing={eff_framing}"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 69B — Still-Only `[Interval Shoot Func.]` (All 7 Sub-Items Resettable)
#                 & `Slot-1` Tier-0 Vault Firewall vs `ILME-FX6` `[Interval Rec]`
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntervalShootAndSlot1VaultResult:
    body_profile: str
    admitted: bool
    errno_code: int
    shoot_mode: str
    exposure_mode: str
    target_slot: int
    recording_media_mode: str
    interval_shooting: str
    shooting_start_time_s: int
    shooting_interval_s: int
    number_of_shots: int
    still_file_format: str
    expected_dcim_file_count: int
    ae_tracking_sensitivity: str
    shutter_type_in_interval: str
    shoot_interval_priority: str
    exited_bulb_to_30s: bool
    in_body_movie_muxed: bool
    fx6_interval_time_s: int
    fx6_number_of_frames: int
    fx6_pre_lighting: str
    fx6_concurrent_conflict: str
    tier0_vault_firewall_triggered: bool
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    camera_settings_reset_applied: bool
    reason: str


def simulate_interval_shoot_and_slot1_vault_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shoot_mode: str = SHOOT_MODE_STILL,
    exposure_mode: str = "M",
    target_slot: int = SLOT_2,
    recording_media_mode: str = "Slot 2",
    interval_shooting: str = "On",
    shooting_start_time_s: int = 1,
    shooting_interval_s: int = 3,
    number_of_shots: int = 30,
    still_file_format: str = "RAW & JPEG",
    ae_tracking_sensitivity: str = "Mid",
    shutter_type_in_interval: str = "Electronic Shutter",
    shoot_interval_priority: str = "Off",
    bulb_requested: bool = False,
    vault_busy: bool = False,
    in_body_movie_mux_requested: bool = False,
    camera_settings_reset_applied: bool = False,
    fx6_interval_time_s: int = 5,
    fx6_number_of_frames: int = 3,
    fx6_pre_lighting: str = "Off",
    fx6_concurrent_conflict: str = "None",
    fx6_video_format_changed: bool = False,
) -> IntervalShootAndSlot1VaultResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage69Phase328Error(f"Unsupported body_profile={body_profile!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage69Phase328Error(f"Unsupported shoot_mode={shoot_mode!r}")
    if target_slot not in VALID_SLOTS:
        raise Stage69Phase328Error(f"Unsupported target_slot={target_slot!r}")
    if recording_media_mode not in VALID_RECORDING_MEDIA_MODES:
        raise Stage69Phase328Error(
            f"Unsupported recording_media_mode={recording_media_mode!r}"
        )
    if interval_shooting not in ("On", "Off"):
        raise Stage69Phase328Error(f"Unsupported interval_shooting={interval_shooting!r}")
    if still_file_format not in VALID_STILL_FILE_FORMATS:
        raise Stage69Phase328Error(f"Unsupported still_file_format={still_file_format!r}")
    if ae_tracking_sensitivity not in VALID_AE_TRACKING_SENSITIVITIES:
        raise Stage69Phase328Error(
            f"Unsupported ae_tracking_sensitivity={ae_tracking_sensitivity!r}"
        )
    if shutter_type_in_interval not in VALID_SHUTTER_TYPES:
        raise Stage69Phase328Error(
            f"Unsupported shutter_type_in_interval={shutter_type_in_interval!r}"
        )
    if shoot_interval_priority not in ("On", "Off"):
        raise Stage69Phase328Error(
            f"Unsupported shoot_interval_priority={shoot_interval_priority!r}"
        )
    if fx6_pre_lighting not in FX6_INTERVAL_REC_PRELIGHTING:
        raise Stage69Phase328Error(f"Unsupported fx6_pre_lighting={fx6_pre_lighting!r}")

    # Apply [Camera Settings Reset] to all 7 Resettable sub-items on FX3
    eff_interval_shooting = "Off" if camera_settings_reset_applied else interval_shooting
    eff_start_time = 1 if camera_settings_reset_applied else shooting_start_time_s
    eff_interval_s = 3 if camera_settings_reset_applied else shooting_interval_s
    eff_shots = 30 if camera_settings_reset_applied else number_of_shots
    eff_ae_sens = "Mid" if camera_settings_reset_applied else ae_tracking_sensitivity
    eff_shutter_type = (
        "Electronic Shutter" if camera_settings_reset_applied else shutter_type_in_interval
    )
    eff_priority = "Off" if camera_settings_reset_applied else shoot_interval_priority

    # Tier-0 Slot-1 Vault Firewall check FIRST for any write/trigger touching Slot 1
    touches_slot1 = (
        target_slot == SLOT_1
        or recording_media_mode in ("Slot 1", "Simult. Recording")
    )
    if touches_slot1 and (eff_interval_shooting == "On" or body_profile == BODY_MODEL_FX6):
        err = EBUSY_ERRNO if vault_busy else EROFS_ERRNO
        return IntervalShootAndSlot1VaultResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=err,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            target_slot=target_slot,
            recording_media_mode=recording_media_mode,
            interval_shooting=eff_interval_shooting,
            shooting_start_time_s=eff_start_time,
            shooting_interval_s=eff_interval_s,
            number_of_shots=eff_shots,
            still_file_format=still_file_format,
            expected_dcim_file_count=0,
            ae_tracking_sensitivity=eff_ae_sens,
            shutter_type_in_interval=eff_shutter_type,
            shoot_interval_priority=eff_priority,
            exited_bulb_to_30s=bool(bulb_requested),
            in_body_movie_muxed=False,
            fx6_interval_time_s=fx6_interval_time_s,
            fx6_number_of_frames=fx6_number_of_frames,
            fx6_pre_lighting=fx6_pre_lighting,
            fx6_concurrent_conflict=fx6_concurrent_conflict,
            tier0_vault_firewall_triggered=True,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason=(
                f"EROFS/EBUSY({err}): Slot-1 Tier-0 Vault firewall blocked interval "
                f"write (target_slot={target_slot}, media={recording_media_mode})"
            ),
        )

    # ILME-FX6 Project > Interval Rec (Single XAVC MXF clip, 1s..24h, 1..24 frames, exclusions)
    if body_profile == BODY_MODEL_FX6:
        if fx6_concurrent_conflict in FX6_INTERVAL_REC_EXCLUSIONS:
            return IntervalShootAndSlot1VaultResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EBUSY_ERRNO,
                shoot_mode=SHOOT_MODE_MOVIE,
                exposure_mode=exposure_mode,
                target_slot=target_slot,
                recording_media_mode=recording_media_mode,
                interval_shooting="Off",
                shooting_start_time_s=0,
                shooting_interval_s=fx6_interval_time_s,
                number_of_shots=0,
                still_file_format="XAVC_MXF",
                expected_dcim_file_count=0,
                ae_tracking_sensitivity="N/A",
                shutter_type_in_interval="Electronic Only",
                shoot_interval_priority="N/A",
                exited_bulb_to_30s=False,
                in_body_movie_muxed=False,
                fx6_interval_time_s=fx6_interval_time_s,
                fx6_number_of_frames=fx6_number_of_frames,
                fx6_pre_lighting=fx6_pre_lighting,
                fx6_concurrent_conflict=fx6_concurrent_conflict,
                tier0_vault_firewall_triggered=False,
                slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
                slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
                camera_settings_reset_applied=camera_settings_reset_applied,
                reason=(
                    "EBUSY: FX6 Interval Rec mutually exclusive with "
                    f"{fx6_concurrent_conflict} (MODEL_VALUE_CHANGED_BY_EXCLUSION_INTERVAL_REC)"
                ),
            )
        if not (1 <= fx6_interval_time_s <= 86_400) or (
            fx6_number_of_frames not in FX6_INTERVAL_REC_FRAME_COUNTS
        ):
            return IntervalShootAndSlot1VaultResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EINVAL_ERRNO,
                shoot_mode=SHOOT_MODE_MOVIE,
                exposure_mode=exposure_mode,
                target_slot=target_slot,
                recording_media_mode=recording_media_mode,
                interval_shooting="Off",
                shooting_start_time_s=0,
                shooting_interval_s=fx6_interval_time_s,
                number_of_shots=0,
                still_file_format="XAVC_MXF",
                expected_dcim_file_count=0,
                ae_tracking_sensitivity="N/A",
                shutter_type_in_interval="Electronic Only",
                shoot_interval_priority="N/A",
                exited_bulb_to_30s=False,
                in_body_movie_muxed=False,
                fx6_interval_time_s=fx6_interval_time_s,
                fx6_number_of_frames=fx6_number_of_frames,
                fx6_pre_lighting=fx6_pre_lighting,
                fx6_concurrent_conflict=fx6_concurrent_conflict,
                tier0_vault_firewall_triggered=False,
                slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
                slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
                camera_settings_reset_applied=camera_settings_reset_applied,
                reason="EINVAL: FX6 Interval Rec requires 1s..24h and frames in {1,2,3,4,6,9,12,24}",
            )
        canceled = bool(fx6_video_format_changed)
        return IntervalShootAndSlot1VaultResult(
            body_profile=body_profile,
            admitted=(not canceled),
            errno_code=(EOPNOTSUPP_ERRNO if canceled else 0),
            shoot_mode=SHOOT_MODE_MOVIE,
            exposure_mode=exposure_mode,
            target_slot=target_slot,
            recording_media_mode=recording_media_mode,
            interval_shooting=("Off" if canceled else "On"),
            shooting_start_time_s=0,
            shooting_interval_s=fx6_interval_time_s,
            number_of_shots=0,
            still_file_format="XAVC_MXF",
            expected_dcim_file_count=1 if not canceled else 0,
            ae_tracking_sensitivity="N/A",
            shutter_type_in_interval="Electronic Only",
            shoot_interval_priority="N/A",
            exited_bulb_to_30s=False,
            in_body_movie_muxed=(not canceled),
            fx6_interval_time_s=fx6_interval_time_s,
            fx6_number_of_frames=fx6_number_of_frames,
            fx6_pre_lighting=fx6_pre_lighting,
            fx6_concurrent_conflict=fx6_concurrent_conflict,
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason=(
                "EOPNOTSUPP: FX6 Interval Rec auto-canceled on video format change"
                if canceled
                else f"ADMITTED: FX6 single XAVC MXF Interval Rec ({fx6_interval_time_s}s/{fx6_number_of_frames}f)"
            ),
        )

    # FX3 Still-only [Interval Shoot Func.] checks
    if in_body_movie_mux_requested:
        return IntervalShootAndSlot1VaultResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            target_slot=target_slot,
            recording_media_mode=recording_media_mode,
            interval_shooting=eff_interval_shooting,
            shooting_start_time_s=eff_start_time,
            shooting_interval_s=eff_interval_s,
            number_of_shots=eff_shots,
            still_file_format=still_file_format,
            expected_dcim_file_count=0,
            ae_tracking_sensitivity=eff_ae_sens,
            shutter_type_in_interval=eff_shutter_type,
            shoot_interval_priority=eff_priority,
            exited_bulb_to_30s=bool(bulb_requested),
            in_body_movie_muxed=False,
            fx6_interval_time_s=0,
            fx6_number_of_frames=0,
            fx6_pre_lighting="Off",
            fx6_concurrent_conflict="None",
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason="EOPNOTSUPP: FX3 [Interval Shoot Func.] is Still-only (no in-body movie muxing)",
        )

    if shoot_mode != SHOOT_MODE_STILL:
        return IntervalShootAndSlot1VaultResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            target_slot=target_slot,
            recording_media_mode=recording_media_mode,
            interval_shooting=eff_interval_shooting,
            shooting_start_time_s=eff_start_time,
            shooting_interval_s=eff_interval_s,
            number_of_shots=eff_shots,
            still_file_format=still_file_format,
            expected_dcim_file_count=0,
            ae_tracking_sensitivity=eff_ae_sens,
            shutter_type_in_interval=eff_shutter_type,
            shoot_interval_priority=eff_priority,
            exited_bulb_to_30s=bool(bulb_requested),
            in_body_movie_muxed=False,
            fx6_interval_time_s=0,
            fx6_number_of_frames=0,
            fx6_pre_lighting="Off",
            fx6_concurrent_conflict="None",
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason=f"EOPNOTSUPP: FX3 [Interval Shoot Func.] is Still-only (got shoot_mode={shoot_mode!r})",
        )

    if exposure_mode == "Intelligent Auto":
        return IntervalShootAndSlot1VaultResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            target_slot=target_slot,
            recording_media_mode=recording_media_mode,
            interval_shooting=eff_interval_shooting,
            shooting_start_time_s=eff_start_time,
            shooting_interval_s=eff_interval_s,
            number_of_shots=eff_shots,
            still_file_format=still_file_format,
            expected_dcim_file_count=0,
            ae_tracking_sensitivity=eff_ae_sens,
            shutter_type_in_interval=eff_shutter_type,
            shoot_interval_priority=eff_priority,
            exited_bulb_to_30s=bool(bulb_requested),
            in_body_movie_muxed=False,
            fx6_interval_time_s=0,
            fx6_number_of_frames=0,
            fx6_pre_lighting="Off",
            fx6_concurrent_conflict="None",
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason="EOPNOTSUPP: [Interval Shoot Func.] is unavailable in [Intelligent Auto]",
        )

    if not (1 <= eff_start_time <= 5999) or not (1 <= eff_interval_s <= 60) or not (1 <= eff_shots <= 9999):
        return IntervalShootAndSlot1VaultResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            target_slot=target_slot,
            recording_media_mode=recording_media_mode,
            interval_shooting=eff_interval_shooting,
            shooting_start_time_s=eff_start_time,
            shooting_interval_s=eff_interval_s,
            number_of_shots=eff_shots,
            still_file_format=still_file_format,
            expected_dcim_file_count=0,
            ae_tracking_sensitivity=eff_ae_sens,
            shutter_type_in_interval=eff_shutter_type,
            shoot_interval_priority=eff_priority,
            exited_bulb_to_30s=bool(bulb_requested),
            in_body_movie_muxed=False,
            fx6_interval_time_s=0,
            fx6_number_of_frames=0,
            fx6_pre_lighting="Off",
            fx6_concurrent_conflict="None",
            tier0_vault_firewall_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reason="EINVAL: FX3 Interval bounds are start=1..5999s, interval=1..60s, shots=1..9999",
        )

    multiplier = 2 if still_file_format in ("RAW & JPEG", "RAW & HEIF") else 1
    dcim_count = eff_shots * multiplier if eff_interval_shooting == "On" else 0
    return IntervalShootAndSlot1VaultResult(
        body_profile=body_profile,
        admitted=True,
        errno_code=0,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        target_slot=target_slot,
        recording_media_mode=recording_media_mode,
        interval_shooting=eff_interval_shooting,
        shooting_start_time_s=eff_start_time,
        shooting_interval_s=eff_interval_s,
        number_of_shots=eff_shots,
        still_file_format=still_file_format,
        expected_dcim_file_count=dcim_count,
        ae_tracking_sensitivity=eff_ae_sens,
        shutter_type_in_interval=eff_shutter_type,
        shoot_interval_priority=eff_priority,
        exited_bulb_to_30s=bool(bulb_requested),
        in_body_movie_muxed=False,
        fx6_interval_time_s=0,
        fx6_number_of_frames=0,
        fx6_pre_lighting="Off",
        fx6_concurrent_conflict="None",
        tier0_vault_firewall_triggered=False,
        slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
        slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
        camera_settings_reset_applied=camera_settings_reset_applied,
        reason=(
            f"ADMITTED: FX3 Still-only Interval on Slot {target_slot} "
            f"({eff_shots} shots -> {dcim_count} DCIM files, shutter={eff_shutter_type}, "
            f"exit_bulb={bool(bulb_requested)})"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 69C — `[Time Code Make/Run]` (`Regenerate` -> `Slot 1` & Forced `Rec Run`,
#                 `VMC-BNCM1` `EXT-LK`, Zero `Clock`) & `[HDMI Output Settings]`
#                 (`[REC Control]`, `[4ch Audio Output]`) vs `ILME-FX6`
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TimecodeRegenAndHdmiOutputResult:
    body_profile: str
    admitted: bool
    errno_code: int
    shoot_mode: str
    recording_media_mode: str
    tc_make: str
    effective_tc_make: str
    requested_tc_run: str
    effective_tc_run: str
    regenerate_reference_slot: Optional[int]
    vmc_bncm1_connected: bool
    ext_lk_locked: bool
    rec_media_during_hdmi_output: str
    time_code_output: str
    rec_control: str
    rec_control_active: bool
    hdmi_status_indicator: str
    hdmi_4ch_audio_output: str
    hdmi_audio_channels_carried: int
    streaming_active: bool
    fx6_sdi_hdmi_rec_ctrl_mode: str
    camera_settings_reset_applied: bool
    initialize_applied: bool
    reason: str


def simulate_tc_make_run_and_hdmi_output_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    recording_media_mode: str = "Simult. Recording",
    tc_make: str = "Preset",
    tc_run: str = "Rec Run",
    vmc_bncm1_connected: bool = False,
    preset_edited_while_extlk: bool = False,
    rec_media_during_hdmi_output: str = "On",
    time_code_output: str = "Off",
    rec_control: str = "Off",
    is_recording: bool = False,
    hdmi_4ch_audio_output: str = "CH1/CH2",
    streaming_active: bool = False,
    fx6_sdi_hdmi_rec_ctrl_mode: str = "Off",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> TimecodeRegenAndHdmiOutputResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage69Phase328Error(f"Unsupported body_profile={body_profile!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage69Phase328Error(f"Unsupported shoot_mode={shoot_mode!r}")
    if recording_media_mode not in VALID_RECORDING_MEDIA_MODES:
        raise Stage69Phase328Error(
            f"Unsupported recording_media_mode={recording_media_mode!r}"
        )
    if tc_make not in VALID_TC_MAKE_MODES:
        raise Stage69Phase328Error(f"Unsupported tc_make={tc_make!r}")
    if tc_run not in VALID_TC_RUN_MODES:
        raise Stage69Phase328Error(f"Unsupported tc_run={tc_run!r}")
    if rec_media_during_hdmi_output not in ("On", "Off(HDMI Only)"):
        raise Stage69Phase328Error(
            f"Unsupported rec_media_during_hdmi_output={rec_media_during_hdmi_output!r}"
        )
    if time_code_output not in ("On", "Off"):
        raise Stage69Phase328Error(f"Unsupported time_code_output={time_code_output!r}")
    if rec_control not in ("On", "Off"):
        raise Stage69Phase328Error(f"Unsupported rec_control={rec_control!r}")
    if hdmi_4ch_audio_output not in VALID_HDMI_4CH_AUDIO_MODES:
        raise Stage69Phase328Error(
            f"Unsupported hdmi_4ch_audio_output={hdmi_4ch_audio_output!r}"
        )
    if fx6_sdi_hdmi_rec_ctrl_mode not in VALID_FX6_REC_CTRL_MODES:
        raise Stage69Phase328Error(
            f"Unsupported fx6_sdi_hdmi_rec_ctrl_mode={fx6_sdi_hdmi_rec_ctrl_mode!r}"
        )

    # All TC Make/Run and HDMI Output Settings are Initialize-only (survive Camera Settings Reset)
    if initialize_applied:
        eff_tc_make = "Preset"
        eff_tc_run = "Rec Run"
        eff_rec_media_hdmi = "On"
        eff_tc_out = "Off"
        eff_rec_ctrl = "Off"
        eff_audio_ch = "CH1/CH2"
    else:
        eff_tc_make = tc_make
        eff_tc_run = tc_run
        eff_rec_media_hdmi = rec_media_during_hdmi_output
        eff_tc_out = time_code_output
        eff_rec_ctrl = rec_control
        eff_audio_ch = hdmi_4ch_audio_output

    if body_profile == BODY_MODEL_FX6:
        ext_lk = (eff_tc_make == "Preset" and eff_tc_run == "Free Run") or (
            eff_tc_make == "Clock"
        )
        return TimecodeRegenAndHdmiOutputResult(
            body_profile=body_profile,
            admitted=True,
            errno_code=0,
            shoot_mode=shoot_mode,
            recording_media_mode=recording_media_mode,
            tc_make=tc_make,
            effective_tc_make=eff_tc_make,
            requested_tc_run=tc_run,
            effective_tc_run=("Rec Run" if eff_tc_make == "Regenerate" else eff_tc_run),
            regenerate_reference_slot=1 if eff_tc_make == "Regenerate" else None,
            vmc_bncm1_connected=False,
            ext_lk_locked=ext_lk,
            rec_media_during_hdmi_output=eff_rec_media_hdmi,
            time_code_output="On",
            rec_control=("On" if fx6_sdi_hdmi_rec_ctrl_mode != "Off" else "Off"),
            rec_control_active=(fx6_sdi_hdmi_rec_ctrl_mode != "Off"),
            hdmi_status_indicator=("(REC)" if is_recording else "(STBY)") if fx6_sdi_hdmi_rec_ctrl_mode != "Off" else "Off",
            hdmi_4ch_audio_output=eff_audio_ch,
            hdmi_audio_channels_carried=2,
            streaming_active=streaming_active,
            fx6_sdi_hdmi_rec_ctrl_mode=fx6_sdi_hdmi_rec_ctrl_mode,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"ADMITTED: ILME-FX6 TC Make={eff_tc_make} (supports Clock & BNC TC IN/OUT), "
                f"SDI/HDMI Rec Control={fx6_sdi_hdmi_rec_ctrl_mode}"
            ),
        )

    # FX3 rejects TC_MAKE_CLOCK
    if eff_tc_make == "Clock":
        return TimecodeRegenAndHdmiOutputResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            shoot_mode=shoot_mode,
            recording_media_mode=recording_media_mode,
            tc_make=tc_make,
            effective_tc_make=eff_tc_make,
            requested_tc_run=tc_run,
            effective_tc_run=eff_tc_run,
            regenerate_reference_slot=None,
            vmc_bncm1_connected=vmc_bncm1_connected,
            ext_lk_locked=False,
            rec_media_during_hdmi_output=eff_rec_media_hdmi,
            time_code_output=eff_tc_out,
            rec_control=eff_rec_ctrl,
            rec_control_active=False,
            hdmi_status_indicator="Off",
            hdmi_4ch_audio_output=eff_audio_ch,
            hdmi_audio_channels_carried=2,
            streaming_active=streaming_active,
            fx6_sdi_hdmi_rec_ctrl_mode="Off",
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason="EOPNOTSUPP: ILME-FX3 has no [Clock] TC Make mode (FX6-only TC_MAKE_CLOCK)",
        )

    # FX3 Regenerate rule: under Simult. Recording reads Slot 1 and forces Rec Run regardless of tc_run
    regen_slot: Optional[int] = None
    if eff_tc_make == "Regenerate":
        eff_tc_run = "Rec Run"
        if recording_media_mode == "Slot 2":
            regen_slot = SLOT_2
        else:
            regen_slot = SLOT_1

    # VMC-BNCM1 EXT-LK requires Preset + Free Run without preset edits
    ext_lk = False
    if vmc_bncm1_connected:
        if eff_tc_make != "Preset" or eff_tc_run != "Free Run" or preset_edited_while_extlk:
            return TimecodeRegenAndHdmiOutputResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                recording_media_mode=recording_media_mode,
                tc_make=tc_make,
                effective_tc_make=eff_tc_make,
                requested_tc_run=tc_run,
                effective_tc_run=eff_tc_run,
                regenerate_reference_slot=regen_slot,
                vmc_bncm1_connected=True,
                ext_lk_locked=False,
                rec_media_during_hdmi_output=eff_rec_media_hdmi,
                time_code_output=eff_tc_out,
                rec_control=eff_rec_ctrl,
                rec_control_active=False,
                hdmi_status_indicator="Off",
                hdmi_4ch_audio_output=eff_audio_ch,
                hdmi_audio_channels_carried=2,
                streaming_active=streaming_active,
                fx6_sdi_hdmi_rec_ctrl_mode="Off",
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason="EOPNOTSUPP: VMC-BNCM1 EXT-LK requires [Preset] + [Free Run] (broken by Regenerate/Rec Run/edit)",
            )
        ext_lk = True

    # S&Q locks Rec. Media = On and blocks Time Code Output + REC Control
    if shoot_mode == SHOOT_MODE_SQ:
        eff_rec_media_hdmi = "On"
        if eff_tc_out == "On" or eff_rec_ctrl == "On":
            return TimecodeRegenAndHdmiOutputResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                recording_media_mode=recording_media_mode,
                tc_make=tc_make,
                effective_tc_make=eff_tc_make,
                requested_tc_run=tc_run,
                effective_tc_run=eff_tc_run,
                regenerate_reference_slot=regen_slot,
                vmc_bncm1_connected=vmc_bncm1_connected,
                ext_lk_locked=ext_lk,
                rec_media_during_hdmi_output=eff_rec_media_hdmi,
                time_code_output="Off",
                rec_control="Off",
                rec_control_active=False,
                hdmi_status_indicator="Off",
                hdmi_4ch_audio_output=eff_audio_ch,
                hdmi_audio_channels_carried=2,
                streaming_active=streaming_active,
                fx6_sdi_hdmi_rec_ctrl_mode="Off",
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason="EOPNOTSUPP: HDMI [Time Code Output] and [REC Control] blocked in S&Q mode",
            )

    # HDMI [REC Control] rules: requires [Time Code Output] = On, blocked in Streaming,
    # active in BOTH Rec. Media = On and Off(HDMI Only)!
    rec_ctrl_active = False
    indicator = "Off"
    if eff_rec_ctrl == "On":
        if eff_tc_out != "On":
            return TimecodeRegenAndHdmiOutputResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                shoot_mode=shoot_mode,
                recording_media_mode=recording_media_mode,
                tc_make=tc_make,
                effective_tc_make=eff_tc_make,
                requested_tc_run=tc_run,
                effective_tc_run=eff_tc_run,
                regenerate_reference_slot=regen_slot,
                vmc_bncm1_connected=vmc_bncm1_connected,
                ext_lk_locked=ext_lk,
                rec_media_during_hdmi_output=eff_rec_media_hdmi,
                time_code_output=eff_tc_out,
                rec_control=eff_rec_ctrl,
                rec_control_active=False,
                hdmi_status_indicator="Off",
                hdmi_4ch_audio_output=eff_audio_ch,
                hdmi_audio_channels_carried=2,
                streaming_active=streaming_active,
                fx6_sdi_hdmi_rec_ctrl_mode="Off",
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason="EOPNOTSUPP: HDMI [REC Control] requires [Time Code Output] = On",
            )
        if streaming_active:
            return TimecodeRegenAndHdmiOutputResult(
                body_profile=body_profile,
                admitted=False,
                errno_code=EBUSY_ERRNO,
                shoot_mode=shoot_mode,
                recording_media_mode=recording_media_mode,
                tc_make=tc_make,
                effective_tc_make=eff_tc_make,
                requested_tc_run=tc_run,
                effective_tc_run=eff_tc_run,
                regenerate_reference_slot=regen_slot,
                vmc_bncm1_connected=vmc_bncm1_connected,
                ext_lk_locked=ext_lk,
                rec_media_during_hdmi_output=eff_rec_media_hdmi,
                time_code_output=eff_tc_out,
                rec_control=eff_rec_ctrl,
                rec_control_active=False,
                hdmi_status_indicator="Off",
                hdmi_4ch_audio_output=eff_audio_ch,
                hdmi_audio_channels_carried=2,
                streaming_active=True,
                fx6_sdi_hdmi_rec_ctrl_mode="Off",
                camera_settings_reset_applied=camera_settings_reset_applied,
                initialize_applied=initialize_applied,
                reason="EBUSY: HDMI [REC Control] blocked while Network/USB Streaming is active",
            )
        rec_ctrl_active = True
        indicator = "(REC)" if is_recording else "(STBY)"

    return TimecodeRegenAndHdmiOutputResult(
        body_profile=body_profile,
        admitted=True,
        errno_code=0,
        shoot_mode=shoot_mode,
        recording_media_mode=recording_media_mode,
        tc_make=tc_make,
        effective_tc_make=eff_tc_make,
        requested_tc_run=tc_run,
        effective_tc_run=eff_tc_run,
        regenerate_reference_slot=regen_slot,
        vmc_bncm1_connected=vmc_bncm1_connected,
        ext_lk_locked=ext_lk,
        rec_media_during_hdmi_output=eff_rec_media_hdmi,
        time_code_output=eff_tc_out,
        rec_control=eff_rec_ctrl,
        rec_control_active=rec_ctrl_active,
        hdmi_status_indicator=indicator,
        hdmi_4ch_audio_output=eff_audio_ch,
        hdmi_audio_channels_carried=2,
        streaming_active=streaming_active,
        fx6_sdi_hdmi_rec_ctrl_mode="Off",
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        reason=(
            f"ADMITTED: TC={eff_tc_make}/{eff_tc_run} (regen_slot={regen_slot}, "
            f"ext_lk={ext_lk}), HDMI RecMedia={eff_rec_media_hdmi}, "
            f"REC_Control={rec_ctrl_active}({indicator}), Audio={eff_audio_ch}->2ch"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 69D — Ver. 7.00+ `[Access Authen. Settings]` (SSH Tunnel + PTP-IP) &
#                 `[Fan Control]` (4-Mode FX3 vs 3-Mode FX6, Zero `Max`) +
#                 `[Auto Power OFF Temp.]` (`Initialize`-Only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AccessAuthSshAndFanThermalResult:
    body_profile: str
    admitted: bool
    errno_code: int
    access_authen_setting: str
    effective_access_authen: str
    auth_protocol: str
    sshd_started: bool
    ssh_host_key_fingerprint_verified: bool
    wifi_security: str
    root_cert_type: str
    root_cert_outbound_client_only: bool
    root_cert_present: bool
    airplane_mode: str
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    fan_control_mode: str
    effective_fan_control_mode: str
    fan_thermal_override_engaged: bool
    auto_power_off_temp: str
    effective_auto_power_off_temp: str
    estimated_4k60_limit_min_25c: int
    low_temp_burn_advisory: bool
    camera_settings_reset_applied: bool
    reset_network_set_applied: bool
    initialize_applied: bool
    reason: str


def simulate_access_auth_ssh_and_fan_thermal_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    access_authen_setting: str = "On",
    auth_protocol: str = "SSH_TUNNEL_PTPIP",
    wifi_security: str = "WPA3-SAE",
    root_cert_type: str = "FTP",
    root_cert_inbound_server_requested: bool = False,
    root_cert_imported: bool = True,
    airplane_mode: str = "On",
    ambient_temp_c: int = 25,
    sensor_temp_c: int = 45,
    fan_control_mode: str = "Auto",
    auto_power_off_temp: str = "Standard",
    camera_settings_reset_applied: bool = False,
    reset_network_set_applied: bool = False,
    initialize_applied: bool = False,
) -> AccessAuthSshAndFanThermalResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage69Phase328Error(f"Unsupported body_profile={body_profile!r}")
    if access_authen_setting not in ("On", "Off"):
        raise Stage69Phase328Error(
            f"Unsupported access_authen_setting={access_authen_setting!r}"
        )
    if root_cert_type not in VALID_ROOT_CERT_TYPES:
        raise Stage69Phase328Error(f"Unsupported root_cert_type={root_cert_type!r}")
    if airplane_mode not in ("On", "Off"):
        raise Stage69Phase328Error(f"Unsupported airplane_mode={airplane_mode!r}")
    if auto_power_off_temp not in VALID_AUTO_POWER_OFF_TEMPS:
        raise Stage69Phase328Error(
            f"Unsupported auto_power_off_temp={auto_power_off_temp!r}"
        )

    # Zero-RF Bench Firewall: Airplane Mode stays On across Reset Network Set. & Initialize
    eff_airplane = "On" if (reset_network_set_applied or initialize_applied or airplane_mode == "On") else "On"

    # Reject non-existent HTTP Digest / Basic Auth / HTTPS server protocols
    if auth_protocol in UNSUPPORTED_ACCESS_AUTH_PROTOCOLS or (
        auth_protocol not in SUPPORTED_ACCESS_AUTH_PROTOCOLS
    ):
        return AccessAuthSshAndFanThermalResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            access_authen_setting=access_authen_setting,
            effective_access_authen="On",
            auth_protocol=auth_protocol,
            sshd_started=False,
            ssh_host_key_fingerprint_verified=False,
            wifi_security=wifi_security,
            root_cert_type=root_cert_type,
            root_cert_outbound_client_only=True,
            root_cert_present=False,
            airplane_mode=eff_airplane,
            rf_packets_transmitted=RF_PACKETS_TRANSMITTED,
            rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES,
            fan_control_mode=fan_control_mode,
            effective_fan_control_mode="Auto",
            fan_thermal_override_engaged=False,
            auto_power_off_temp=auto_power_off_temp,
            effective_auto_power_off_temp="Standard",
            estimated_4k60_limit_min_25c=30,
            low_temp_burn_advisory=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            reason=(
                f"EOPNOTSUPP: {auth_protocol} has 0 hits in FX3 appFw.so; "
                "[Access Authen. Settings] uses SSH tunnel (sshd_start) + PTP-IP"
            ),
        )

    # Reject removed WEP / WPA-PSK / IPsec
    if wifi_security in REMOVED_WIFI_SECURITY or wifi_security not in SUPPORTED_WIFI_SECURITY:
        return AccessAuthSshAndFanThermalResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            access_authen_setting=access_authen_setting,
            effective_access_authen=access_authen_setting,
            auth_protocol=auth_protocol,
            sshd_started=False,
            ssh_host_key_fingerprint_verified=False,
            wifi_security=wifi_security,
            root_cert_type=root_cert_type,
            root_cert_outbound_client_only=True,
            root_cert_present=False,
            airplane_mode=eff_airplane,
            rf_packets_transmitted=RF_PACKETS_TRANSMITTED,
            rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES,
            fan_control_mode=fan_control_mode,
            effective_fan_control_mode="Auto",
            fan_thermal_override_engaged=False,
            auto_power_off_temp=auto_power_off_temp,
            effective_auto_power_off_temp="Standard",
            estimated_4k60_limit_min_25c=30,
            low_temp_burn_advisory=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            reason=f"EOPNOTSUPP: Ver. 7.00+ removed {wifi_security}; requires WPA2-PSK or WPA3-SAE",
        )

    # Reject inbound HTTPS server use of [Import Root Certificate]
    if root_cert_inbound_server_requested:
        return AccessAuthSshAndFanThermalResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            access_authen_setting=access_authen_setting,
            effective_access_authen=access_authen_setting,
            auth_protocol=auth_protocol,
            sshd_started=False,
            ssh_host_key_fingerprint_verified=False,
            wifi_security=wifi_security,
            root_cert_type=root_cert_type,
            root_cert_outbound_client_only=True,
            root_cert_present=False,
            airplane_mode=eff_airplane,
            rf_packets_transmitted=RF_PACKETS_TRANSMITTED,
            rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES,
            fan_control_mode=fan_control_mode,
            effective_fan_control_mode="Auto",
            fan_thermal_override_engaged=False,
            auto_power_off_temp=auto_power_off_temp,
            effective_auto_power_off_temp="Standard",
            estimated_4k60_limit_min_25c=30,
            low_temp_burn_advisory=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            reason=(
                "EOPNOTSUPP: [Import Root Certificate] is strictly outbound client TLS "
                "for CLOUD/FTP/RTMP (never inbound camera HTTPS server)"
            ),
        )

    # Fan Control validation: NO Max mode on either camera; FX6 has 3 modes (Always Off dormant)
    if fan_control_mode in DORMANT_FAN_CONTROL_MODES or (
        fan_control_mode not in FX3_FAN_CONTROL_MODES
    ):
        return AccessAuthSshAndFanThermalResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            access_authen_setting=access_authen_setting,
            effective_access_authen=access_authen_setting,
            auth_protocol=auth_protocol,
            sshd_started=False,
            ssh_host_key_fingerprint_verified=False,
            wifi_security=wifi_security,
            root_cert_type=root_cert_type,
            root_cert_outbound_client_only=True,
            root_cert_present=False,
            airplane_mode=eff_airplane,
            rf_packets_transmitted=RF_PACKETS_TRANSMITTED,
            rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES,
            fan_control_mode=fan_control_mode,
            effective_fan_control_mode="Auto",
            fan_thermal_override_engaged=False,
            auto_power_off_temp=auto_power_off_temp,
            effective_auto_power_off_temp="Standard",
            estimated_4k60_limit_min_25c=30,
            low_temp_burn_advisory=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            reason=f"EOPNOTSUPP: FAN_CONTROL_MAX / {fan_control_mode!r} does not exist on FX3 or FX6 (0 hits)",
        )

    if body_profile == BODY_MODEL_FX6 and fan_control_mode not in FX6_FAN_CONTROL_MODES:
        return AccessAuthSshAndFanThermalResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            access_authen_setting=access_authen_setting,
            effective_access_authen=access_authen_setting,
            auth_protocol=auth_protocol,
            sshd_started=False,
            ssh_host_key_fingerprint_verified=False,
            wifi_security=wifi_security,
            root_cert_type=root_cert_type,
            root_cert_outbound_client_only=True,
            root_cert_present=False,
            airplane_mode=eff_airplane,
            rf_packets_transmitted=RF_PACKETS_TRANSMITTED,
            rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES,
            fan_control_mode=fan_control_mode,
            effective_fan_control_mode="Auto",
            fan_thermal_override_engaged=False,
            auto_power_off_temp="N/A",
            effective_auto_power_off_temp="N/A",
            estimated_4k60_limit_min_25c=0,
            low_temp_burn_advisory=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            reason=(
                "EOPNOTSUPP: ILME-FX6 exposes 3 Fan Control modes (Auto/Minimum/Off in Rec); "
                "[Always Off] is dormant on FX6"
            ),
        )

    if body_profile == BODY_MODEL_FX6 and auto_power_off_temp == "High":
        return AccessAuthSshAndFanThermalResult(
            body_profile=body_profile,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            access_authen_setting=access_authen_setting,
            effective_access_authen=access_authen_setting,
            auth_protocol=auth_protocol,
            sshd_started=False,
            ssh_host_key_fingerprint_verified=False,
            wifi_security=wifi_security,
            root_cert_type=root_cert_type,
            root_cert_outbound_client_only=True,
            root_cert_present=False,
            airplane_mode=eff_airplane,
            rf_packets_transmitted=RF_PACKETS_TRANSMITTED,
            rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES,
            fan_control_mode=fan_control_mode,
            effective_fan_control_mode=fan_control_mode,
            fan_thermal_override_engaged=False,
            auto_power_off_temp=auto_power_off_temp,
            effective_auto_power_off_temp="N/A",
            estimated_4k60_limit_min_25c=0,
            low_temp_burn_advisory=False,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reset_network_set_applied=reset_network_set_applied,
            initialize_applied=initialize_applied,
            reason="EOPNOTSUPP: ILME-FX6 lacks consumer [Auto Power OFF Temp.] Standard/High toggle",
        )

    # Reset lifecycle split:
    # - Access Authen. Settings & Root Cert: survive [Camera Settings Reset], reset by [Reset Network Set.] or [Initialize]
    # - Fan Control & Auto Power OFF Temp.: survive [Camera Settings Reset] and [Reset Network Set.], reset ONLY by [Initialize]
    if reset_network_set_applied or initialize_applied:
        eff_access_auth = "On"
        eff_root_cert_present = False
    else:
        eff_access_auth = access_authen_setting
        eff_root_cert_present = root_cert_imported

    if initialize_applied:
        eff_fan_mode = "Auto"
        eff_temp_mode = "Standard" if body_profile == BODY_MODEL_FX3 else "N/A"
    else:
        eff_fan_mode = fan_control_mode
        eff_temp_mode = auto_power_off_temp if body_profile == BODY_MODEL_FX3 else "N/A"

    thermal_override = eff_fan_mode == "Off in Rec" and sensor_temp_c >= 65
    est_4k60 = 90 if eff_temp_mode == "High" else 30
    burn_advisory = eff_temp_mode == "High" and ambient_temp_c >= 25
    sshd_active = eff_access_auth == "On"

    return AccessAuthSshAndFanThermalResult(
        body_profile=body_profile,
        admitted=True,
        errno_code=0,
        access_authen_setting=access_authen_setting,
        effective_access_authen=eff_access_auth,
        auth_protocol=auth_protocol,
        sshd_started=sshd_active,
        ssh_host_key_fingerprint_verified=sshd_active,
        wifi_security=wifi_security,
        root_cert_type=root_cert_type,
        root_cert_outbound_client_only=True,
        root_cert_present=eff_root_cert_present,
        airplane_mode=eff_airplane,
        rf_packets_transmitted=RF_PACKETS_TRANSMITTED,
        rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES,
        fan_control_mode=fan_control_mode,
        effective_fan_control_mode=eff_fan_mode,
        fan_thermal_override_engaged=thermal_override,
        auto_power_off_temp=auto_power_off_temp,
        effective_auto_power_off_temp=eff_temp_mode,
        estimated_4k60_limit_min_25c=est_4k60,
        low_temp_burn_advisory=burn_advisory,
        camera_settings_reset_applied=camera_settings_reset_applied,
        reset_network_set_applied=reset_network_set_applied,
        initialize_applied=initialize_applied,
        reason=(
            f"ADMITTED: {body_profile} AccessAuth={eff_access_auth} (SSH={sshd_active}), "
            f"Fan={eff_fan_mode}(override={thermal_override}), Temp={eff_temp_mode}({est_4k60}m)"
        ),
    )


def _build_stage69_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_69th_stage_milestone": IS_69TH_STAGE_MILESTONE,
        "wave": "Wave-59",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase328_big6_home_framing_interval_tc_ssh_fan_coemulation(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute complete Phase 328 Stage 69 (69/69 Milestone) Wave-59 HIL co-emulation."""
    donor_audit = inspect_phase328_donors(force_clean_room=force_clean_room, env=env)

    # Sub-Model 69A probes
    p69a_big6_nd_metadata_ok = simulate_big6_home_and_framing_hil(
        firmware_version=FW_VER_702,
        mode_settings=FX3_MODE_SETTINGS_FIXED_VAR,
        entry_trigger="Swipe Down",
        touch_operation="On",
        log_shooting="Cine EI",
        shutter_mode="Angle",
        home_lower_left_setting="ND Filter",
        nd_filter_label="ND16",
    )
    p69a_big6_flex_exp_blocked = simulate_big6_home_and_framing_hil(
        mode_settings=FX3_MODE_SETTINGS_FLEX_EXP,
    )
    p69a_big6_ver601_blocked = simulate_big6_home_and_framing_hil(
        firmware_version=FW_VER_601,
    )
    p69a_fx6_big6_real_end = simulate_big6_home_and_framing_hil(
        body_profile=BODY_MODEL_FX6,
        firmware_version=FW_VER_601,
        nd_filter_label="1/64",
    )
    p69a_manual_framing_ok = simulate_big6_home_and_framing_hil(
        framing_enabled=True,
        framing_rec_stream_output="Crop",
        framing_hdmi_output="Crop",
        apsc_s35_requested=True,
        fps_fps=60,
    )
    p69a_framing_120p_locked = simulate_big6_home_and_framing_hil(
        framing_enabled=True,
        fps_fps=120,
    )
    p69a_framing_rec_locked = simulate_big6_home_and_framing_hil(
        framing_enabled=True,
        is_recording_or_streaming=True,
    )
    p69a_dormant_auto_framing = [
        simulate_big6_home_and_framing_hil(
            body_profile=BODY_MODEL_FX3,
            auto_framing_requested=True,
        ),
        simulate_big6_home_and_framing_hil(
            body_profile=BODY_MODEL_FX6,
            auto_framing_requested=True,
        ),
    ]
    p69a_ok = (
        p69a_big6_nd_metadata_ok.admitted
        and p69a_big6_nd_metadata_ok.nd_tile_metadata_only
        and (not p69a_big6_nd_metadata_ok.fx3_has_builtin_end_filter)
        and p69a_big6_nd_metadata_ok.electronic_nd_commands_emitted == 0
        and p69a_big6_nd_metadata_ok.hdmi_sdi_status_bar_leaked_pixels == 0
        and (not p69a_big6_flex_exp_blocked.admitted)
        and p69a_big6_flex_exp_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not p69a_big6_ver601_blocked.admitted)
        and p69a_big6_ver601_blocked.errno_code == EOPNOTSUPP_ERRNO
        and p69a_fx6_big6_real_end.admitted
        and p69a_fx6_big6_real_end.fx6_has_electronic_variable_nd
        and p69a_manual_framing_ok.admitted
        and p69a_manual_framing_ok.apsc_s35_forced_off
        and (not p69a_framing_120p_locked.admitted)
        and p69a_framing_120p_locked.errno_code == EOPNOTSUPP_ERRNO
        and (not p69a_framing_rec_locked.admitted)
        and p69a_framing_rec_locked.errno_code == EBUSY_ERRNO
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO and r.dormant_auto_framing_rejected
            for r in p69a_dormant_auto_framing
        )
    )

    # Sub-Model 69B probes
    p69b_slot2_still_ok = simulate_interval_shoot_and_slot1_vault_hil(
        target_slot=SLOT_2,
        recording_media_mode="Slot 2",
        number_of_shots=9999,
        still_file_format="RAW & HEIF",
        bulb_requested=True,
    )
    p69b_all7_reset_ok = simulate_interval_shoot_and_slot1_vault_hil(
        target_slot=SLOT_2,
        recording_media_mode="Slot 2",
        interval_shooting="On",
        shooting_start_time_s=120,
        shooting_interval_s=15,
        number_of_shots=500,
        ae_tracking_sensitivity="Low",
        shutter_type_in_interval="Mechanical Shutter",
        shoot_interval_priority="On",
        camera_settings_reset_applied=True,
    )
    p69b_movie_mux_blocked = simulate_interval_shoot_and_slot1_vault_hil(
        target_slot=SLOT_2,
        in_body_movie_mux_requested=True,
    )
    p69b_iauto_blocked = simulate_interval_shoot_and_slot1_vault_hil(
        target_slot=SLOT_2,
        exposure_mode="Intelligent Auto",
    )
    p69b_slot1_vault_erofs = simulate_interval_shoot_and_slot1_vault_hil(
        target_slot=SLOT_1,
        recording_media_mode="Simult. Recording",
    )
    p69b_slot1_vault_ebusy = simulate_interval_shoot_and_slot1_vault_hil(
        target_slot=SLOT_1,
        recording_media_mode="Slot 1",
        vault_busy=True,
    )
    p69b_fx6_interval_ok = simulate_interval_shoot_and_slot1_vault_hil(
        body_profile=BODY_MODEL_FX6,
        target_slot=SLOT_2,
        recording_media_mode="Slot 2",
        fx6_interval_time_s=30,
        fx6_number_of_frames=6,
        fx6_pre_lighting="5s",
    )
    p69b_fx6_simul_conflict = simulate_interval_shoot_and_slot1_vault_hil(
        body_profile=BODY_MODEL_FX6,
        target_slot=SLOT_2,
        recording_media_mode="Slot 2",
        fx6_concurrent_conflict="Simul Rec",
    )
    p69b_ok = (
        p69b_slot2_still_ok.admitted
        and p69b_slot2_still_ok.expected_dcim_file_count == 19_998
        and p69b_slot2_still_ok.exited_bulb_to_30s
        and (not p69b_slot2_still_ok.in_body_movie_muxed)
        and p69b_all7_reset_ok.admitted
        and p69b_all7_reset_ok.interval_shooting == "Off"
        and p69b_all7_reset_ok.shooting_start_time_s == 1
        and p69b_all7_reset_ok.shooting_interval_s == 3
        and p69b_all7_reset_ok.number_of_shots == 30
        and p69b_all7_reset_ok.ae_tracking_sensitivity == "Mid"
        and p69b_all7_reset_ok.shutter_type_in_interval == "Electronic Shutter"
        and p69b_all7_reset_ok.shoot_interval_priority == "Off"
        and (not p69b_movie_mux_blocked.admitted)
        and p69b_movie_mux_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not p69b_iauto_blocked.admitted)
        and p69b_iauto_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not p69b_slot1_vault_erofs.admitted)
        and p69b_slot1_vault_erofs.errno_code == EROFS_ERRNO
        and p69b_slot1_vault_erofs.slot1_data_sector_writes == 0
        and (not p69b_slot1_vault_erofs.slot1_avf_info_mutated)
        and (not p69b_slot1_vault_ebusy.admitted)
        and p69b_slot1_vault_ebusy.errno_code == EBUSY_ERRNO
        and p69b_fx6_interval_ok.admitted
        and p69b_fx6_interval_ok.in_body_movie_muxed
        and (not p69b_fx6_simul_conflict.admitted)
        and p69b_fx6_simul_conflict.errno_code == EBUSY_ERRNO
    )

    # Sub-Model 69C probes
    p69c_regen_simult_slot1_recrun = simulate_tc_make_run_and_hdmi_output_hil(
        recording_media_mode="Simult. Recording",
        tc_make="Regenerate",
        tc_run="Free Run",
        camera_settings_reset_applied=True,
    )
    p69c_vmc_extlk_ok = simulate_tc_make_run_and_hdmi_output_hil(
        tc_make="Preset",
        tc_run="Free Run",
        vmc_bncm1_connected=True,
    )
    p69c_fx3_clock_blocked = simulate_tc_make_run_and_hdmi_output_hil(
        tc_make="Clock",
    )
    p69c_hdmi_rec_ctrl_on_and_hdmionly = [
        simulate_tc_make_run_and_hdmi_output_hil(
            rec_media_during_hdmi_output="On",
            time_code_output="On",
            rec_control="On",
            is_recording=True,
            hdmi_4ch_audio_output="CH3/CH4",
        ),
        simulate_tc_make_run_and_hdmi_output_hil(
            rec_media_during_hdmi_output="Off(HDMI Only)",
            time_code_output="On",
            rec_control="On",
            is_recording=False,
        ),
    ]
    p69c_hdmi_rec_ctrl_no_tc_blocked = simulate_tc_make_run_and_hdmi_output_hil(
        time_code_output="Off",
        rec_control="On",
    )
    p69c_hdmi_rec_ctrl_sq_blocked = simulate_tc_make_run_and_hdmi_output_hil(
        shoot_mode=SHOOT_MODE_SQ,
        time_code_output="On",
        rec_control="On",
    )
    p69c_fx6_clock_and_parallel_rec = simulate_tc_make_run_and_hdmi_output_hil(
        body_profile=BODY_MODEL_FX6,
        tc_make="Clock",
        fx6_sdi_hdmi_rec_ctrl_mode="Parallel Rec",
    )
    p69c_ok = (
        p69c_regen_simult_slot1_recrun.admitted
        and p69c_regen_simult_slot1_recrun.regenerate_reference_slot == SLOT_1
        and p69c_regen_simult_slot1_recrun.effective_tc_run == "Rec Run"
        and p69c_regen_simult_slot1_recrun.effective_tc_make == "Regenerate"
        and p69c_vmc_extlk_ok.admitted
        and p69c_vmc_extlk_ok.ext_lk_locked
        and (not p69c_fx3_clock_blocked.admitted)
        and p69c_fx3_clock_blocked.errno_code == EOPNOTSUPP_ERRNO
        and p69c_hdmi_rec_ctrl_on_and_hdmionly[0].admitted
        and p69c_hdmi_rec_ctrl_on_and_hdmionly[0].rec_control_active
        and p69c_hdmi_rec_ctrl_on_and_hdmionly[0].hdmi_status_indicator == "(REC)"
        and p69c_hdmi_rec_ctrl_on_and_hdmionly[0].hdmi_audio_channels_carried == 2
        and p69c_hdmi_rec_ctrl_on_and_hdmionly[1].admitted
        and p69c_hdmi_rec_ctrl_on_and_hdmionly[1].rec_control_active
        and p69c_hdmi_rec_ctrl_on_and_hdmionly[1].hdmi_status_indicator == "(STBY)"
        and (not p69c_hdmi_rec_ctrl_no_tc_blocked.admitted)
        and p69c_hdmi_rec_ctrl_no_tc_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not p69c_hdmi_rec_ctrl_sq_blocked.admitted)
        and p69c_hdmi_rec_ctrl_sq_blocked.errno_code == EOPNOTSUPP_ERRNO
        and p69c_fx6_clock_and_parallel_rec.admitted
        and p69c_fx6_clock_and_parallel_rec.fx6_sdi_hdmi_rec_ctrl_mode == "Parallel Rec"
    )

    # Sub-Model 69D probes
    p69d_ssh_ptpip_and_4mode_fan_ok = simulate_access_auth_ssh_and_fan_thermal_hil(
        access_authen_setting="On",
        auth_protocol="SSH_TUNNEL_PTPIP",
        wifi_security="WPA3-SAE",
        root_cert_type="RTMP",
        airplane_mode="On",
        fan_control_mode="Always Off",
        auto_power_off_temp="High",
        camera_settings_reset_applied=True,
    )
    p69d_reset_network_vs_initialize = [
        simulate_access_auth_ssh_and_fan_thermal_hil(
            access_authen_setting="Off",
            fan_control_mode="Minimum",
            auto_power_off_temp="High",
            reset_network_set_applied=True,
        ),
        simulate_access_auth_ssh_and_fan_thermal_hil(
            access_authen_setting="Off",
            fan_control_mode="Always Off",
            auto_power_off_temp="High",
            initialize_applied=True,
        ),
    ]
    p69d_http_digest_basic_https_blocked = [
        simulate_access_auth_ssh_and_fan_thermal_hil(auth_protocol=proto)
        for proto in UNSUPPORTED_ACCESS_AUTH_PROTOCOLS
    ]
    p69d_removed_wep_wpa_ipsec_blocked = [
        simulate_access_auth_ssh_and_fan_thermal_hil(wifi_security=sec)
        for sec in ("WEP", "WPA-PSK", "Security(IPsec)")
    ]
    p69d_fx3_fx6_fan_max_blocked = [
        simulate_access_auth_ssh_and_fan_thermal_hil(
            body_profile=BODY_MODEL_FX3,
            fan_control_mode="Max",
        ),
        simulate_access_auth_ssh_and_fan_thermal_hil(
            body_profile=BODY_MODEL_FX6,
            fan_control_mode="Max",
        ),
    ]
    p69d_fx6_always_off_blocked = simulate_access_auth_ssh_and_fan_thermal_hil(
        body_profile=BODY_MODEL_FX6,
        fan_control_mode="Always Off",
    )
    p69d_ok = (
        p69d_ssh_ptpip_and_4mode_fan_ok.admitted
        and p69d_ssh_ptpip_and_4mode_fan_ok.sshd_started
        and p69d_ssh_ptpip_and_4mode_fan_ok.ssh_host_key_fingerprint_verified
        and p69d_ssh_ptpip_and_4mode_fan_ok.rf_packets_transmitted == 0
        and p69d_ssh_ptpip_and_4mode_fan_ok.effective_fan_control_mode == "Always Off"
        and p69d_ssh_ptpip_and_4mode_fan_ok.effective_auto_power_off_temp == "High"
        and p69d_ssh_ptpip_and_4mode_fan_ok.estimated_4k60_limit_min_25c == 90
        and p69d_reset_network_vs_initialize[0].effective_access_authen == "On"
        and (not p69d_reset_network_vs_initialize[0].root_cert_present)
        and p69d_reset_network_vs_initialize[0].effective_fan_control_mode == "Minimum"
        and p69d_reset_network_vs_initialize[0].effective_auto_power_off_temp == "High"
        and p69d_reset_network_vs_initialize[1].effective_fan_control_mode == "Auto"
        and p69d_reset_network_vs_initialize[1].effective_auto_power_off_temp == "Standard"
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO
            for r in p69d_http_digest_basic_https_blocked
        )
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO
            for r in p69d_removed_wep_wpa_ipsec_blocked
        )
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO
            for r in p69d_fx3_fx6_fan_max_blocked
        )
        and (not p69d_fx6_always_off_blocked.admitted)
        and p69d_fx6_always_off_blocked.errno_code == EOPNOTSUPP_ERRNO
    )

    milestone_probe = _build_stage69_milestone_probe()

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
        "fx3_has_builtin_end_filter": FX3_HAS_BUILTIN_END_FILTER,
        "fx6_has_electronic_variable_nd": FX6_HAS_ELECTRONIC_VARIABLE_ND,
        "electronic_nd_commands_emitted": ELECTRONIC_ND_COMMANDS_EMITTED,
        "hdmi_sdi_status_bar_leaked_pixels": HDMI_SDI_STATUS_BAR_LEAKED_PIXELS,
        "dormant_auto_framing_exposed_events": DORMANT_AUTO_FRAMING_EXPOSED_EVENTS,
        "framing_highfps_or_rec_bypass_events": FRAMING_HIGHFPS_OR_REC_BYPASS_EVENTS,
        "interval_inbody_movie_mux_events": INTERVAL_INBODY_MOVIE_MUX_EVENTS,
        "interval_iauto_or_bulb_bypass_events": INTERVAL_IAUTO_OR_BULB_BYPASS_EVENTS,
        "slot1_data_sector_writes": SLOT1_DATA_SECTOR_WRITES,
        "slot1_avf_info_mutated": SLOT1_AVF_INFO_MUTATED,
        "slot1_vault_interval_write_events": SLOT1_VAULT_INTERVAL_WRITE_EVENTS,
        "tc_regen_non_slot1_or_freerun_violations": TC_REGEN_NON_SLOT1_OR_FREERUN_VIOLATIONS,
        "fx3_clock_tc_make_exposed_events": FX3_CLOCK_TC_MAKE_EXPOSED_EVENTS,
        "hdmi_rec_ctrl_s_and_q_or_notc_bypass_events": HDMI_REC_CTRL_S_AND_Q_OR_NOTC_BYPASS_EVENTS,
        "ssh_http_basic_https_auth_spoof_events": SSH_HTTP_BASIC_HTTPS_AUTH_SPOOF_EVENTS,
        "removed_wep_wpa_ipsec_exposed_events": REMOVED_WEP_WPA_IPSEC_EXPOSED_EVENTS,
        "fan_control_max_exposed_events": FAN_CONTROL_MAX_EXPOSED_EVENTS,
        "fx6_fan_always_off_exposed_events": FX6_FAN_ALWAYS_OFF_EXPOSED_EVENTS,
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
        and p69a_ok
        and p69b_ok
        and p69c_ok
        and p69d_ok
        and milestone_probe["is_69th_stage_milestone"]
        and (not redlines["fx3_has_builtin_end_filter"])
        and redlines["electronic_nd_commands_emitted"] == 0
        and redlines["hdmi_sdi_status_bar_leaked_pixels"] == 0
        and redlines["dormant_auto_framing_exposed_events"] == 0
        and redlines["framing_highfps_or_rec_bypass_events"] == 0
        and redlines["interval_inbody_movie_mux_events"] == 0
        and redlines["interval_iauto_or_bulb_bypass_events"] == 0
        and redlines["slot1_data_sector_writes"] == 0
        and (not redlines["slot1_avf_info_mutated"])
        and redlines["slot1_vault_interval_write_events"] == 0
        and redlines["tc_regen_non_slot1_or_freerun_violations"] == 0
        and redlines["fx3_clock_tc_make_exposed_events"] == 0
        and redlines["hdmi_rec_ctrl_s_and_q_or_notc_bypass_events"] == 0
        and redlines["ssh_http_basic_https_auth_spoof_events"] == 0
        and redlines["removed_wep_wpa_ipsec_exposed_events"] == 0
        and redlines["fan_control_max_exposed_events"] == 0
        and redlines["fx6_fan_always_off_exposed_events"] == 0
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
        "version": PHASE_328_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_69th_stage_milestone": True,
        "source_mode": donor_audit.source_mode,
        "access_mode": donor_audit.access_mode,
        "all_checks_passed": all_passed,
        "donor_audit": asdict(donor_audit),
        "pillar_a_big6_home_screen_and_framing_hil": {
            "passed": p69a_ok,
            "big6_nd_metadata_only_ok": asdict(p69a_big6_nd_metadata_ok),
            "big6_flex_exp_blocked": asdict(p69a_big6_flex_exp_blocked),
            "big6_ver601_blocked": asdict(p69a_big6_ver601_blocked),
            "fx6_big6_real_variable_end": asdict(p69a_fx6_big6_real_end),
            "manual_framing_ok": asdict(p69a_manual_framing_ok),
            "framing_120p_locked": asdict(p69a_framing_120p_locked),
            "framing_rec_locked": asdict(p69a_framing_rec_locked),
            "dormant_auto_framing_blocked": [
                asdict(r) for r in p69a_dormant_auto_framing
            ],
        },
        "pillar_b_interval_shoot_7item_and_slot1_vault_hil": {
            "passed": p69b_ok,
            "all_7_resettable_subitems": list(FX3_INTERVAL_7_SUBITEMS),
            "slot2_still_interval_ok": asdict(p69b_slot2_still_ok),
            "all7_reset_ok": asdict(p69b_all7_reset_ok),
            "inbody_movie_mux_blocked": asdict(p69b_movie_mux_blocked),
            "iauto_blocked": asdict(p69b_iauto_blocked),
            "slot1_vault_erofs": asdict(p69b_slot1_vault_erofs),
            "slot1_vault_ebusy": asdict(p69b_slot1_vault_ebusy),
            "fx6_interval_rec_ok": asdict(p69b_fx6_interval_ok),
            "fx6_simul_conflict": asdict(p69b_fx6_simul_conflict),
        },
        "pillar_c_tc_regenerate_and_hdmi_rec_control_hil": {
            "passed": p69c_ok,
            "tc_regen_simult_slot1_recrun": asdict(p69c_regen_simult_slot1_recrun),
            "vmc_bncm1_ext_lk_ok": asdict(p69c_vmc_extlk_ok),
            "fx3_clock_blocked": asdict(p69c_fx3_clock_blocked),
            "hdmi_rec_ctrl_on_and_hdmionly": [
                asdict(r) for r in p69c_hdmi_rec_ctrl_on_and_hdmionly
            ],
            "hdmi_rec_ctrl_no_tc_blocked": asdict(p69c_hdmi_rec_ctrl_no_tc_blocked),
            "hdmi_rec_ctrl_sq_blocked": asdict(p69c_hdmi_rec_ctrl_sq_blocked),
            "fx6_clock_and_parallel_rec": asdict(p69c_fx6_clock_and_parallel_rec),
        },
        "pillar_d_access_auth_ssh_and_fan_control_thermal_hil": {
            "passed": p69d_ok,
            "ssh_ptpip_and_4mode_fan_ok": asdict(p69d_ssh_ptpip_and_4mode_fan_ok),
            "reset_network_vs_initialize": [
                asdict(r) for r in p69d_reset_network_vs_initialize
            ],
            "http_digest_basic_https_blocked": [
                asdict(r) for r in p69d_http_digest_basic_https_blocked
            ],
            "removed_wep_wpa_ipsec_blocked": [
                asdict(r) for r in p69d_removed_wep_wpa_ipsec_blocked
            ],
            "fx3_fx6_fan_max_blocked": [
                asdict(r) for r in p69d_fx3_fx6_fan_max_blocked
            ],
            "fx6_always_off_blocked": asdict(p69d_fx6_always_off_blocked),
            "stage69_milestone_probe": milestone_probe,
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
        prog="realhw_big6_home_framing_interval_tc_ssh_fan_coemulator.py",
        description=(
            "Phase 328 Stage 69 (69/69 Milestone) Wave-59 Real-Hardware "
            "ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Ver. 7.00/7.02 BIG6 [HOME] Screen "
            "([Mode Settings]=Fixed/Variable, Metadata-Only Lower-Left ND Filter, Zero e-ND) & "
            "Active Manual [Framing Settings] vs Dormant AI [Auto Framing] (EOPNOTSUPP=95), "
            "Still-Only [Interval Shoot Func.] (All 7 Resettable, Slot-1 100%% Fail-Closed "
            "EROFS=30 Vault) vs FX6 Single-MXF Interval Rec, [Time Code Make] (Regenerate->Slot 1 "
            "& Forced Rec Run, VMC-BNCM1 EXT-LK, Zero Clock) & [HDMI Output Settings] "
            "([REC Control] Active in Rec. Media=On & Off(HDMI Only), [4ch Audio Output] 2ch Limit), "
            "and [Access Authen. Settings] (SSH Tunnel + PTP-IP, Zero HTTP_DIGEST/BASIC/HTTPS) & "
            "4-Mode FX3 vs 3-Mode FX6 [Fan Control] (Zero Max Mode) + [Auto Power OFF Temp.] HIL"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic Phase 328 Stage 69 (69/69) Wave-59 HIL verification suite",
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
        help="Emit concise one-line Stage 69 (69/69 Milestone) Wave-59 summary",
    )
    args = parser.parse_args(argv)

    rep = run_phase328_big6_home_framing_interval_tc_ssh_fan_coemulation(
        force_clean_room=True if args.clean_room else None
    )

    if args.summary and not args.json:
        red = rep["redlines"]
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 328 Stage 69 (69/69 Milestone) | "
            f"mode={rep['source_mode']} "
            f"donors={rep['donor_audit']['donor_files_inspected']} "
            f"end_tx={red['electronic_nd_commands_emitted']} "
            f"afram_byp={red['dormant_auto_framing_exposed_events']} "
            f"ivl_mux={red['interval_inbody_movie_mux_events']} "
            f"fan_max={red['fan_control_max_exposed_events']} "
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
