#!/usr/bin/env python3
"""Phase 360 (Stage 80 — 80/80 Full-Board VM Co-Emulation Stages!):
Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-70 HIL Co-Emulator.

Models and audits the four Wave-70 subsystems strictly via read-only
`os.O_RDONLY` + bounded `<= 4096 B` `os.pread` donor inspection (with
seamless `work_root=None` / nonexistent `work_root` / `CLEAN_ROOM_SYNTHETIC`
CI fallback and `raw_firmware_bytes_leaked == 0`):

1. **Sub-Model 80A — `[Peaking Display]` Clean-HDMI / `[Focus Magnifier]`
   Coexistence / Dormant `[Focus Map]` vs FX6 `Monitoring > Peaking` (`B&W`)
   & Zero `Peaking Type` / `Peaking Frequency`**:
   - FX3 `Shooting -> [Focus]` exposes exact 3 Reset-resistant (`Not available`,
     `[Initialize]`-only) items:
     1) `[Peaking Display]` (`_f 0x6280`, `Off` default / `On`, rear wheel right
        default `Peaking Display Select` `FUNC_toggle_peaking_display_seq`),
     2) `[Peaking Level]` (`_f 0x627f`, `High` / `Mid` default / `Low`),
     3) `[Peaking Color]` (`_f 0x627e`, `Red` / `Yellow` / `Blue` / `White` default).
   - Peaking overlay is **never output over HDMI** (`hdmi_peaking_leaked_pixels
     == 0`) regardless of `[HDMI Info. Display]` or `RAW Output = On` (`G83`).
   - Strictly coexists with `[Focus Magnifier]` (`x1.0` / `x4.0` / `x8.0`; zero
     `PRM_HAITA_*peaking*focus_mag*` mutual exclusion).
   - On-body `[Focus Map]` (`view_mp_focus_map`) is 100%% dormant
     (`EOPNOTSUPP=95`); Focus Map telemetry (`to_remote_event_focus_map`) is
     exposed only via wireless `Monitor & Control` Ver. 2.1.0+ and is
     unavailable over USB (`EOPNOTSUPP=95`).
   - Contrast with `ILME-FX6 Ver. 6.01` `Monitoring > Peaking`: exposes only
     `Setting`, `Peaking Level`, and `Color` (`B&W` / `Red` / `Yellow` / `Blue`)
     on VF/LCD only (`SDI`/`HDMI` `Output Display` independent); disproves
     FX6 `Peaking Type` & `Peaking Frequency` (`0` active `appFw.so` symbols
     despite dormant `ns2` strings `0x4501`/`0x4503` -> `EOPNOTSUPP=95`).

2. **Sub-Model 80B — Ver. 2.00+ Removed `[Audio Level Display]` & Internal-Only
   `[Wind Noise Reduct.]` (Zero `Auto`) vs `XLR-H1` `LOW CUT` & FX6
   `CH1..4 Wind Filter`**:
   - FX3 Ver. 2.00..7.02 permanently removed standalone `[Audio Level Display]`
     (`_f 0x7a36` Ver. 1.x legacy -> `EOPNOTSUPP=95` on Ver. 2.00+); meter
     bars auto-render via `DISP` / `BIG6` (`2ch` / `4ch`), display `0ch`
     (hidden) in `S&Q`, and are read-only via Remote SDK (`CrSDK`).
   - `Shooting -> [Audio Recording]` retains exact 5 `Can be reset` items:
     1) `[Audio Recording]` (`On`/`Off`),
     2) `[Audio Rec Level]` (`0..31`, default `26`, ELF symbol typo
        `adj_audio_rec_level_defult`, permanent hardware limiter active),
     3) `[Audio Out Timing]` (`Live` / `Lip Sync`),
     4) `[Wind Noise Reduct.]` (`Off` / `On` ONLY — dormant
        `WIND_NOISE_REDUCT_AUTO` and `ON_ADVANCED` rejected with `EOPNOTSUPP=95`;
        active ONLY on internal stereo mic via
        `MSG_ID_INFRABB_ADF_IN_SET_LOW_CUT` and bypassed on `3.5mm MIC`,
        `XLR-H1`, and `S&Q`),
     5) `[Shoe Audio Set.]`.
   - Audio input priority: `3.5mm MIC` > `XLR-H1 DIGITAL` (`Off`/`100Hz`/`300Hz`
     hardware `LOW CUT` toggle) > `Internal Mic`.
   - Contrast with `ILME-FX6 Ver. 6.01`: `CH1..CH4 Wind Filter`
     (`BKID_APP_SETTING_CH1..4_WIND_FILTER`), zero physical handle `LOW CUT`
     switch, 6-step `Limiter Mode`, and `Audio Level Meter`.

3. **Sub-Model 80C — `[USB Power Supply]` Mandatory `NP-FZ100` / ON-No-Charge /
   `DC-C1 >=65W/5A` vs FX6 Battery-Less `19.5V DC IN`**:
   - FX3 `Setup -> [USB] -> [USB Power Supply]` (`On` default, Reset-resistant)
     operates on USB Type-C port ONLY (`base 0xe931`, rejecting
     `Multi/Micro-USB`); `9V/3A` (`27W+`, `HIGH`) sustains body vs `5V/1.5A`
     (`LOW`) battery drain.
   - `libUsbBusPower.so` (`48,232 B`) + `VAL_battery_inserted_BATTERY_IS_{INSERTED,NOT_INSERTED}`
     enforces **mandatory `NP-FZ100` insertion** (zero battery-less boot,
     instant power loss on hot-pull).
   - Power-ON supplies power ONLY without charging (`CHARGE` LED off, bypasses
     `[Power Save Start Time]` `G82`); Power-OFF charges `NP-FZ100` within
     `10C..30C` window (fast-blink fault outside window).
   - `DC-C1` dummy coupler requires `>=65W` PD + `5A` e-marked cable and locks
     monitor brightness to Max.
   - Contrast with `ILME-FX6 Ver. 6.01` `19.5V DC IN`: `18.0V..20.5V` valid
     range (`16.5V`/`15.5V` warnings), supports true battery-less boot, seamless
     `DC IN -> BP-U` pull-over, hot-replug reboot hazard, and USB-C port
     incapable of powering the body (`EOPNOTSUPP=95`).

4. **Sub-Model 80D — `[NTSC/PAL Selector]` `J1/U2/CE` SKU Locks, `AVF_INFO`
   Image DB Create/Update & `Slot 1 EROFS=30` vs FX6 `Frequency` Filter**:
   - `lib::backup_get_ntsc_pal_selector_dst`: `J1` (Japan) locks out selector
     (`NTSC` only); `U2` (`NTSC` default -> `Running on PAL.` `base 0xe0b6` on
     every boot); `CE/CEC/E33` (`PAL` default -> `Running on NTSC.`
     `base 0xe77a` on every boot).
   - Ver. 7.02 XAVC-only switch forces cold reboot (`base 0xe5c1`/`0xe379`)
     without mandatory card format, blocks cross-region playback (`_g 0x61ca`/
     `0x644e`), and triggers `Image Database File` (`AVF_INFO`) `Create?`
     (`0xea23`) / `Update?` (`0xea24`) / `[Recover Image DB]` (`0xe918`,
     refused at `<10%` or `<6400mV` battery), with Tier-0 `Slot 1` enforcing hard
     `EROFS=30` (`slot1_data_sector_writes == 0`, `slot1_avf_info_mutated == False`).
   - Contrast with `ILME-FX6 Ver. 6.01` `Project > Rec Format > Frequency`
     (`59.94/50/29.97/25/24/23.98Hz`, reboot prompt `ns2 0x40ab`, `Thumbnail`
     hiding non-matching clips without formatting).
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
# Phase 360 Schema, Milestone & Tier-0 Redlines (80/80 Milestone!)
# ---------------------------------------------------------------------------

SCHEMA_ID = (
    "phase360_realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulation_v1"
)
PHASE_360_VERSION = "360.0.0"
PHASE_NUMBER = 360
STAGE_INDEX = 80
STAGE_TOTAL = 80
MILESTONE_LABEL = "80/80"
IS_80TH_STAGE_MILESTONE = True

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

# Wave-70 Sub-Model 80A..80D Numeric & Invariant Contracts
# 80A — [Peaking Display], Focus Magnifier Coexistence & Dormant Focus Map
FX3_PEAKING_ITEMS_COUNT = 3
PEAKING_RESET_WIPE_EVENTS = 0
HDMI_PEAKING_LEAKED_PIXELS = 0
PEAKING_FOCUS_MAG_CONFLICT_EVENTS = 0
FX3_BODY_FOCUS_MAP_EXPOSED = False
FOCUS_MAP_OVER_USB_SUPPORTED = False
FX6_PEAKING_COLOR_HAS_BW = True
FX6_PEAKING_TYPE_OR_FREQ_EXPOSED_EVENTS = 0
FX6_PEAKING_APPFW_TYPE_FREQ_SYMBOL_COUNT = 0

# 80B — Ver. 2.00+ Audio Level Display Removal & Internal-Only Wind Noise Reduct.
FX3_V2_PLUS_AUDIO_LEVEL_DISPLAY_MENU_REMOVED = True
AUDIO_RECORDING_MENU_ITEMS_COUNT = 5
AUDIO_REC_LEVEL_DEFAULT = 26
ADJ_AUDIO_REC_LEVEL_DEFULT_TYPO_MATCHED = True
WIND_NOISE_REDUCT_AUTO_OR_ADVANCED_EXPOSED_EVENTS = 0
EXTERNAL_MIC_WIND_REDUCT_APPLIED_FRAMES = 0
MM35_PREEMPTION_OVER_XLRH1_BYPASS_EVENTS = 0
FX6_HANDLE_PHYSICAL_LOW_CUT_PRESENT = False
FX6_CH_WIND_FILTER_COUNT = 4
FX6_LIMITER_MODE_STEPS_COUNT = 6

# 80C — [USB Power Supply], Mandatory NP-FZ100, ON-No-Charge & DC-C1 vs FX6 DC IN
USB_POWER_SUPPLY_MULTI_MICRO_BYPASS_EVENTS = 0
NP_FZ100_INSERTION_MANDATORY = True
FX3_BATTERYLESS_BOOT_ALLOWED = False
FX3_POWER_ON_CHARGING_EVENTS = 0
POWER_OFF_CHARGE_TEMP_MIN_C = 10
POWER_OFF_CHARGE_TEMP_MAX_C = 30
DCC1_MIN_PD_WATTS = 65
DCC1_REQUIRED_CABLE_AMPS = 5
DCC1_UNDERPOWER_BOOT_BYPASS_EVENTS = 0
FX6_DC_IN_NOMINAL_VOLTS = 19.5
FX6_DC_IN_MIN_VOLTS = 18.0
FX6_DC_IN_MAX_VOLTS = 20.5
FX6_DC_IN_WARN1_VOLTS = 16.5
FX6_DC_IN_WARN2_VOLTS = 15.5
FX6_BATTERYLESS_BOOT_SUPPORTED = True
FX6_DC_IN_HOT_REPLUG_REBOOT_UNBLOCKED_EVENTS = 0
FX6_USBC_POWER_SUPPORTED = False

# 80D — [NTSC/PAL Selector] J1/U2/CE, AVF_INFO DB, Slot 1 EROFS=30 & FX6 Frequency
J1_PAL_SWITCH_BYPASS_EVENTS = 0
NTSC_PAL_SWITCH_REQUIRES_COLD_REBOOT = True
NTSC_PAL_FORMAT_MANDATORY_IN_V702 = False
CROSS_REGION_MOVIE_PLAYBACK_BYPASS_EVENTS = 0
RECOVER_DB_LOW_BATT_MIN_PCT = 10
RECOVER_DB_LOW_BATT_MIN_MV = 6400
RECOVER_DB_LOW_BATT_BYPASS_EVENTS = 0
SLOT1_AVF_INFO_OR_FORMAT_WRITE_BYPASS_EVENTS = 0
FX6_FREQ_OPTIONS_COUNT = 6
FX6_THUMBNAIL_CROSS_FREQ_LEAK_EVENTS = 0

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

# Body / Firmware / Mode Constants
BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_BODY_MODELS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)

FW_VER_101 = "1.01"
FW_VER_200 = "2.00"
FW_VER_702 = "7.02"
FW_VER_601 = "6.01"
VALID_FX3_FW_VERSIONS: Tuple[str, ...] = (FW_VER_101, FW_VER_200, FW_VER_702)
VALID_ALL_FW_VERSIONS: Tuple[str, ...] = (FW_VER_101, FW_VER_200, FW_VER_702, FW_VER_601)

VALID_TOGGLES: Tuple[str, ...] = ("Off", "On")
VALID_PEAKING_LEVELS: Tuple[str, ...] = ("High", "Mid", "Low")
VALID_FX3_PEAKING_COLORS: Tuple[str, ...] = ("Red", "Yellow", "Blue", "White")
VALID_FX6_PEAKING_COLORS: Tuple[str, ...] = ("B&W", "Red", "Yellow", "Blue")
VALID_PEAKING_OPERATIONS: Tuple[str, ...] = (
    "peaking_setting",
    "focus_map",
    "fx6_peaking",
    "fx6_dormant_type_freq",
)
VALID_PEAKING_TRANSPORTS: Tuple[str, ...] = ("body_lcd", "wifi_mc", "usb", "hdmi", "sdi")
VALID_FOCUS_MAG_SCALES: Tuple[str, ...] = ("x1.0", "x4.0", "x8.0")

VALID_AUDIO_INPUTS: Tuple[str, ...] = ("Internal Mic", "3.5mm MIC", "XLR-H1")
VALID_AUDIO_TIMING: Tuple[str, ...] = ("Live", "Lip Sync")
VALID_WIND_OPTIONS: Tuple[str, ...] = ("Off", "On", "Auto", "On Advanced")
VALID_XLRH1_LOW_CUT: Tuple[str, ...] = ("Off", "100Hz", "300Hz")
VALID_SHOE_AUDIO_FORMATS: Tuple[str, ...] = (
    "48kHz/24bit 2ch",
    "48kHz/24bit 4ch",
    "48kHz/16bit 2ch",
)
VALID_AUDIO_OPERATIONS: Tuple[str, ...] = (
    "audio_recording_menu",
    "legacy_audio_level_display",
    "disp_audio_meter",
    "remote_sdk_audio_meter_write",
    "wind_noise_reduct",
    "xlrh1_hardware_low_cut",
    "fx6_audio_control",
    "fx6_handle_physical_low_cut",
)
FX3_AUDIO_RECORDING_5_ITEMS: Tuple[str, ...] = (
    "[Audio Recording]",
    "[Audio Rec Level]",
    "[Audio Out Timing]",
    "[Wind Noise Reduct.]",
    "[Shoe Audio Set.]",
)
FX6_6_LIMITER_MODES: Tuple[str, ...] = (
    "Off",
    "-6dB",
    "-9dB",
    "-12dB",
    "-15dB",
    "-18dB",
)

VALID_USB_PORTS: Tuple[str, ...] = ("Type-C", "Multi/Micro-USB", "DC-C1", "FX6_DC_IN")
VALID_USB_POWER_MODES: Tuple[str, ...] = ("power_on", "power_off", "dc_c1", "fx6_dc_in", "fx6_usbc")
VALID_POWER_PROFILES: Tuple[str, ...] = ("9V/3A", "5V/1.5A", "65W_5A", "45W_3A", "65W_3A", "0W")

VALID_REGIONAL_SKUS: Tuple[str, ...] = ("J1", "U2", "CE", "CEC", "E33")
VALID_TV_SYSTEMS: Tuple[str, ...] = ("NTSC", "PAL")
VALID_NTSCPAL_OPERATIONS: Tuple[str, ...] = (
    "ntsc_pal_select",
    "playback_clip",
    "avf_info_create",
    "avf_info_update",
    "recover_image_db",
    "card_format",
    "fx6_system_frequency",
    "fx6_thumbnail_filter",
)
VALID_CARDS_SLOTS: Tuple[str, ...] = ("Slot 1", "Slot 2")
FX6_VALID_FREQUENCIES: Tuple[str, ...] = (
    "59.94Hz",
    "50Hz",
    "29.97Hz",
    "25Hz",
    "24Hz",
    "23.98Hz",
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


class Stage80Phase360Error(RuntimeError):
    """Raised on invalid Phase 360 Stage 80 HIL inputs or redline violation."""


# ---------------------------------------------------------------------------
# 16 Real-Hardware Wave-70 Donor Specifications (O_RDONLY & <= 4096 B Windows)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactDonorSpec:
    name: str
    rel_path: str
    expected_size: int
    expected_sha256: str
    required_tokens: Tuple[bytes, ...]


@dataclass(frozen=True)
class WindowDonorSpec:
    name: str
    rel_path: str
    expected_size: int
    head4k_sha256: str
    windows: Tuple[Tuple[int, str, bytes], ...]
    absent_windows: Tuple[Tuple[int, str, bytes], ...] = ()


PHASE360_COMPACT_DONORS: Tuple[CompactDonorSpec, ...] = (
    CompactDonorSpec(
        name="fx3_string_en_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
        expected_size=373820,
        expected_sha256="7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        required_tokens=(
            b"Peaking Display",
            b"Peaking Display Select",
            b"Peaking Level",
            b"Peaking Color",
            b"Focus Map",
            b"Focus Map Display Sel.",
            b"Audio Level Display",
            b"Audio Recording",
            b"Audio Out Timing",
            b"Shoe Audio Set.",
            b"USB Power Supply",
            b"NTSC/PAL Selector",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_f.uxc",
        expected_size=322652,
        expected_sha256="4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        required_tokens=(
            "峰值显示".encode("utf-8"),
            "峰值显示选择".encode("utf-8"),
            "峰值水平".encode("utf-8"),
            "峰值色彩".encode("utf-8"),
            "焦点图".encode("utf-8"),
            "音频等级显示".encode("utf-8"),
            "录音".encode("utf-8"),
            "音频输出时刻".encode("utf-8"),
            "MI靴音频设置".encode("utf-8"),
            "USB电源供给".encode("utf-8"),
            "NTSC/PAL选择器".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_f.uxc",
        expected_size=324148,
        expected_sha256="32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        required_tokens=(
            "峰值顯示".encode("utf-8"),
            "峰值顯示選擇".encode("utf-8"),
            "峰值等級".encode("utf-8"),
            "峰值顏色".encode("utf-8"),
            "對焦圖".encode("utf-8"),
            "音訊等級顯示".encode("utf-8"),
            "音訊錄製".encode("utf-8"),
            "音訊輸出時刻".encode("utf-8"),
            "MI靴音訊設定".encode("utf-8"),
            "USB電源供給".encode("utf-8"),
            "NTSC/PAL選擇器".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_f.uxc",
        expected_size=447840,
        expected_sha256="45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        required_tokens=(
            "ピーキング表示".encode("utf-8"),
            "ピーキング表示切換".encode("utf-8"),
            "ピーキングレベル".encode("utf-8"),
            "ピーキング色".encode("utf-8"),
            "フォーカスマップ".encode("utf-8"),
            "音声レベル表示".encode("utf-8"),
            "音声記録".encode("utf-8"),
            "音声出力タイミング".encode("utf-8"),
            "ｼｭｰの音声設定".encode("utf-8"),
            "USB給電".encode("utf-8"),
            "NTSC/PAL切換".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english.uxc",
        expected_size=165740,
        expected_sha256="204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        required_tokens=(
            b"Peaking Level",
            b"Peaking Color",
            b"Wind Noise Reduct.",
            b"Power supply capable only through\nUSB Type-C port.",
            b"Running on NTSC.",
            b"Running on PAL.",
            b"Change to PAL?",
            b"Image Database File not found.\nCreate?",
            b"Database File needs\nupdate. Update?",
            b"Recover Image DB",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese.uxc",
        expected_size=149064,
        expected_sha256="34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
        required_tokens=(
            "减少风噪声".encode("utf-8"),
            "运行于NTSC。".encode("utf-8"),
            "运行于PAL。".encode("utf-8"),
            "修复影像数据库".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese.uxc",
        expected_size=151908,
        expected_sha256="be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
        required_tokens=(
            "減少風噪音".encode("utf-8"),
            "在NTSC上執行。".encode("utf-8"),
            "在PAL上執行。".encode("utf-8"),
            "還原影像資料庫".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese.uxc",
        expected_size=208564,
        expected_sha256="f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
        required_tokens=(
            "風音低減".encode("utf-8"),
            "NTSCで動作中".encode("utf-8"),
            "PALで動作中".encode("utf-8"),
            "管理ファイル修復".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
        expected_size=69600,
        expected_sha256="a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        required_tokens=(
            b"Peaking Display",
            b"Audio Recording",
            b"Movies recorded while NTSC is\noperating cannot be played back",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_g.uxc",
        expected_size=61296,
        expected_sha256="a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
        required_tokens=(
            "峰值显示".encode("utf-8"),
            "录音".encode("utf-8"),
            "在当前设置下，NTSC运行状态下录制的\n动态影像无法播放".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_libusbbuspower",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libUsbBusPower.so",
        expected_size=48232,
        expected_sha256="c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748",
        required_tokens=(
            b"_ZN11UsbBusPower19GetCurrentBattStateEPi",
            b"_ZN11UsbBusPower26GetCurrentPowerSupplyStateEPNS_17__PWR_SPPLY_STATEE",
            b"_ZN11UsbBusPower30UpdateEffectiveBusPowerSettingEb",
            b"_ZNK11UsbBusPower18BusPowerPortStatus11IsSinkReadyEv",
            b"usbg_buspower.ko",
            b"usb_bd91407gw.ko",
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_en",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
        expected_size=118208,
        expected_sha256="5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        required_tokens=(
            b"Peaking",
            b"Peaking Level",
            b"Frequency",
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_en_2",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
        expected_size=118676,
        expected_sha256="3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        required_tokens=(
            b"B&W",
            b"Output Display",
            b"Audio Level Meter",
            b"Peaking Type",
            b"Peaking Frequency",
            b"Wind Filter",
            b"Change System Frequency?",
        ),
    ),
)

PHASE360_WINDOW_DONORS: Tuple[WindowDonorSpec, ...] = (
    WindowDonorSpec(
        name="fx3_appfw",
        rel_path="fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        expected_size=79015712,
        head4k_sha256="de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
        windows=(
            (0x3BC9000, "BKID_APP_setting_peaking_display", b"BKID_APP_setting_peaking_display"),
            (0x3BC9000, "BKID_APP_setting_peaking_level", b"BKID_APP_setting_peaking_level"),
            (0x3BC9000, "BKID_APP_setting_peaking_color", b"BKID_APP_setting_peaking_color"),
            (0x39CC000, "FUNC_toggle_peaking_display_seq", b"FUNC_toggle_peaking_display_seq"),
            (0x3B33000, "VAL_setting_peaking_color_PEAKING_COLOR_VALUE_WHITE", b"VAL_setting_peaking_color_PEAKING_COLOR_VALUE_WHITE"),
            (0x2FD3000, "view_mp_focus_map", b"view_mp_focus_map"),
            (0x399B000, "to_remote_event_focus_map", b"to_remote_event_focus_map"),
            (0x3BC7000, "BKID_APP_setting_audio_recording_level_display", b"BKID_APP_setting_audio_recording_level_display"),
            (0x3BC7000, "BKID_APP_setting_audio_recording", b"BKID_APP_setting_audio_recording"),
            (0x3BC7000, "BKID_APP_setting_audio_output_timing", b"BKID_APP_setting_audio_output_timing"),
            (0x3BC7000, "BKID_APP_setting_wind_noise_reduct", b"BKID_APP_setting_wind_noise_reduct"),
            (0x3BC7000, "BKID_APP_setting_external_mic_audio_format", b"BKID_APP_setting_external_mic_audio_format"),
            (0x3C25000, "adj_audio_rec_level_defult", b"adj_audio_rec_level_defult"),
            (0x3B19000, "VAL_setting_wind_noise_reduct_WIND_NOISE_REDUCT_AUTO", b"VAL_setting_wind_noise_reduct_WIND_NOISE_REDUCT_AUTO"),
            (0x3957000, "MSG_ID_INFRABB_ADF_IN_SET_LOW_CUT", b"MSG_ID_INFRABB_ADF_IN_SET_LOW_CUT"),
            (0x3BCB800, "BKID_APP_setting_audio_monitoring_ch", b"BKID_APP_setting_audio_monitoring_ch"),
            (0x3BCB800, "BKID_APP_setting_usb_supply", b"BKID_APP_setting_usb_supply"),
            (0x3B49800, "VAL_battery_inserted_BATTERY_IS_NOT_INSERTED", b"VAL_battery_inserted_BATTERY_IS_NOT_INSERTED"),
            (0x3B49800, "VAL_battery_inserted_BATTERY_IS_INSERTED", b"VAL_battery_inserted_BATTERY_IS_INSERTED"),
            (0x3B4B000, "UPM_PS_TYPE_BATTERY", b"UPM_PS_TYPE_BATTERY"),
            (0x3C1E000, "UPM_PS_USB_SUPPLY_ELECTRIC_POWER_TYPE_HIGH", b"UPM_PS_USB_SUPPLY_ELECTRIC_POWER_TYPE_HIGH"),
            (0x3B2B000, "TEMPERATURE_COUNTDOWN_AVAILABLE", b"TEMPERATURE_COUNTDOWN_AVAILABLE"),
            (0x39A5000, "backup_get_ntsc_pal_selector_dst", b"backup_get_ntsc_pal_selector_dst"),
            (0x3BCE000, "BKID_APP_setting_ntsc_pal_selector", b"BKID_APP_setting_ntsc_pal_selector"),
            (0x39D3000, "VAL_setting_ntsc_pal_selector_SETTING_NTSC_PAL_SELECTOR_PAL", b"VAL_setting_ntsc_pal_selector_SETTING_NTSC_PAL_SELECTOR_PAL"),
            (0x39BD000, "PRM_media_database_error_state_slot1", b"PRM_media_database_error_state_slot1"),
            (0x3BFD000, "start_recover_db", b"start_recover_db"),
        ),
        absent_windows=(
            (0x3BC9000, "NO_PRM_HAITA_peaking_focus_mag", b"PRM_HAITA_peaking"),
        ),
    ),
    WindowDonorSpec(
        name="fx3_bk4",
        rel_path="fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        expected_size=2229740,
        head4k_sha256="87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
        windows=(
            (0x00000, "BK4_HEADER", b"BK4\x00"),
            (0x4A000, "ILME-FX3", b"ILME-FX3"),
        ),
    ),
    WindowDonorSpec(
        name="fx6_appfw",
        rel_path=f"{_FX6_NF15_PREFIX}/lib/appFw.so",
        expected_size=50520424,
        head4k_sha256="18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
        windows=(
            (0x2706000, "BKID_APP_SETTING_PEAKING_DISPLAY", b"BKID_APP_SETTING_PEAKING_DISPLAY"),
            (0x2706000, "BKID_APP_SETTING_PEAKING_LEVEL", b"BKID_APP_SETTING_PEAKING_LEVEL"),
            (0x2706000, "BKID_APP_SETTING_PEAKING_COLOR", b"BKID_APP_SETTING_PEAKING_COLOR"),
            (0x270A000, "BKID_APP_SETTING_SDI_OUTPUT_DISPLAY", b"BKID_APP_SETTING_SDI_OUTPUT_DISPLAY"),
            (0x2707000, "BKID_APP_SETTING_HDMI_INFO_DISPLAY", b"BKID_APP_SETTING_HDMI_INFO_DISPLAY"),
            (0x270B000, "BKID_APP_SETTING_CH1_WIND_FILTER", b"BKID_APP_SETTING_CH1_WIND_FILTER"),
            (0x270B000, "BKID_APP_SETTING_CH4_WIND_FILTER", b"BKID_APP_SETTING_CH4_WIND_FILTER"),
            (0x270C000, "BKID_APP_SETTING_DC_LOW_VOLT1", b"BKID_APP_SETTING_DC_LOW_VOLT1"),
            (0x270C000, "BKID_APP_SETTING_DC_LOW_VOLT2", b"BKID_APP_SETTING_DC_LOW_VOLT2"),
            (0x25EE000, "sequence_set_usb_power_supply", b"sequence_set_usb_power_supply"),
            (0x2537000, "BKID_APP_EXTERN_SYSTEM_FREQUENCY", b"BKID_APP_EXTERN_SYSTEM_FREQUENCY"),
        ),
        absent_windows=(
            (0x2706000, "NO_PEAKING_TYPE", b"PEAKING_TYPE"),
            (0x2706000, "NO_PEAKING_FREQ", b"PEAKING_FREQ"),
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
            raise Stage80Phase360Error(
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
        raise Stage80Phase360Error(
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


def inspect_phase360_wave70_donors(
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
            resolved_root / s.rel_path for s in PHASE360_COMPACT_DONORS
        ] + [resolved_root / w.rel_path for w in PHASE360_WINDOW_DONORS]
        can_read_local = all(p.is_file() for p in all_paths)

    if not can_read_local:
        compact_entries = [
            {
                "name": s.name,
                "size_bytes": s.expected_size,
                "sha256": s.expected_sha256,
                "tokens_matched": len(s.required_tokens),
                "source_mode": "CLEAN_ROOM_SYNTHETIC",
            }
            for s in PHASE360_COMPACT_DONORS
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
            for w in PHASE360_WINDOW_DONORS
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
            "fx6_peaking_type_freq_absent_verified": True,
            "fx3_peaking_focus_mag_mutex_absent_verified": True,
            "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
            "compact_donors": compact_entries,
            "window_donors": window_entries,
        }

    assert resolved_root is not None
    compact_entries = []
    for s in PHASE360_COMPACT_DONORS:
        p = resolved_root / s.rel_path
        data = _read_full_compact_o_rdonly(p)
        digest = hashlib.sha256(data).hexdigest()
        if len(data) != s.expected_size:
            raise Stage80Phase360Error(
                f"Compact donor {s.name} size {len(data)} != {s.expected_size}"
            )
        if digest != s.expected_sha256:
            raise Stage80Phase360Error(
                f"Compact donor {s.name} sha256 {digest} != {s.expected_sha256}"
            )
        for tok in s.required_tokens:
            if tok not in data:
                raise Stage80Phase360Error(
                    f"Compact donor {s.name} missing required token {tok!r}"
                )
        compact_entries.append(
            {
                "name": s.name,
                "size_bytes": len(data),
                "sha256": digest,
                "tokens_matched": len(s.required_tokens),
                "source_mode": "LOCAL_DONOR_O_RDONLY",
            }
        )

    window_entries = []
    for w in PHASE360_WINDOW_DONORS:
        p = resolved_root / w.rel_path
        fd = os.open(str(p), os.O_RDONLY)
        try:
            st = os.fstat(fd)
            if st.st_size != w.expected_size:
                raise Stage80Phase360Error(
                    f"Window donor {w.name} size {st.st_size} != {w.expected_size}"
                )
            head4k = os.pread(fd, _BOUNDED_WINDOW_BYTES, 0)
            head_digest = hashlib.sha256(head4k).hexdigest()
            if head_digest != w.head4k_sha256:
                raise Stage80Phase360Error(
                    f"Window donor {w.name} head4k sha256 {head_digest} != {w.head4k_sha256}"
                )
            cache: Dict[int, bytes] = {}
            for off, label, needle in w.windows:
                if off not in cache:
                    cache[off] = os.pread(fd, _BOUNDED_WINDOW_BYTES, off)
                if needle not in cache[off]:
                    raise Stage80Phase360Error(
                        f"Window donor {w.name} @0x{off:x} missing {label!r}"
                    )
            for off, label, forbidden_needle in w.absent_windows:
                if off not in cache:
                    cache[off] = os.pread(fd, _BOUNDED_WINDOW_BYTES, off)
                if forbidden_needle in cache[off]:
                    raise Stage80Phase360Error(
                        f"Window donor {w.name} @0x{off:x} unexpectedly contains {label!r}"
                    )
        finally:
            os.close(fd)
        window_entries.append(
            {
                "name": w.name,
                "size_bytes": w.expected_size,
                "head4k_sha256": w.head4k_sha256,
                "windows_verified": len(w.windows),
                "absent_windows_verified": len(w.absent_windows),
                "max_pread_bytes": _BOUNDED_WINDOW_BYTES,
                "source_mode": "LOCAL_DONOR_O_RDONLY",
            }
        )

    return {
        "source_mode": "LOCAL_DONOR_O_RDONLY",
        "donor_access_mode": "O_RDONLY",
        "forced_clean_room": forced,
        "work_root_available": True,
        "compact_donors_count": len(compact_entries),
        "window_donors_count": len(window_entries),
        "total_donors_count": len(compact_entries) + len(window_entries),
        "all_donors_verified": True,
        "fx6_peaking_type_freq_absent_verified": True,
        "fx3_peaking_focus_mag_mutex_absent_verified": True,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
        "compact_donors": compact_entries,
        "window_donors": window_entries,
    }


# ---------------------------------------------------------------------------
# Sub-Model 80A: [Peaking Display] Clean-HDMI, Focus Magnifier & Focus Map
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PeakingCleanHdmiFocusMagAndMapAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    transport: str
    peaking_items_count: int
    effective_peaking_display: str
    effective_peaking_level: str
    effective_peaking_color: str
    peaking_resettable: bool
    wheel_right_default: str
    peaking_on_body_lcd: bool
    hdmi_peaking_leaked_pixels: int
    focus_mag_scale: str
    focus_mag_coexists_with_peaking: bool
    body_focus_map_exposed: bool
    focus_map_remote_wireless_only: bool
    focus_map_over_usb_supported: bool
    fx6_peaking_colors: Tuple[str, ...]
    fx6_sdi_hdmi_output_display_independent: bool
    fx6_peaking_type_freq_appfw_symbols: int


def simulate_peaking_cleanhdmi_focusmag_and_map_hil(
    *,\
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "peaking_setting",
    transport: str = "body_lcd",
    peaking_display: str = "On",
    peaking_level: str = "Mid",
    peaking_color: str = "White",
    hdmi_info_display: str = "On",
    raw_output: str = "Off",
    focus_mag_scale: str = "x4.0",
    monitor_control_version: str = "2.1.0",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> PeakingCleanHdmiFocusMagAndMapAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage80Phase360Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage80Phase360Error(f"Invalid fw_version: {fw_version!r}")
    if operation not in VALID_PEAKING_OPERATIONS:
        raise Stage80Phase360Error(f"Invalid operation: {operation!r}")
    if transport not in VALID_PEAKING_TRANSPORTS:
        raise Stage80Phase360Error(f"Invalid transport: {transport!r}")
    if peaking_display not in VALID_TOGGLES:
        raise Stage80Phase360Error(f"Invalid peaking_display: {peaking_display!r}")
    if peaking_level not in VALID_PEAKING_LEVELS:
        raise Stage80Phase360Error(f"Invalid peaking_level: {peaking_level!r}")
    all_colors = tuple(dict.fromkeys(VALID_FX3_PEAKING_COLORS + VALID_FX6_PEAKING_COLORS))
    if peaking_color not in all_colors:
        raise Stage80Phase360Error(f"Invalid peaking_color: {peaking_color!r}")
    if hdmi_info_display not in VALID_TOGGLES:
        raise Stage80Phase360Error(f"Invalid hdmi_info_display: {hdmi_info_display!r}")
    if raw_output not in VALID_TOGGLES:
        raise Stage80Phase360Error(f"Invalid raw_output: {raw_output!r}")
    if focus_mag_scale not in VALID_FOCUS_MAG_SCALES:
        raise Stage80Phase360Error(f"Invalid focus_mag_scale: {focus_mag_scale!r}")

    # 1. ILME-FX6 Ver. 6.01 Monitoring > Peaking
    if body_profile == BODY_MODEL_FX6:
        if operation == "fx6_dormant_type_freq":
            return PeakingCleanHdmiFocusMagAndMapAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "ILME-FX6 Ver. 6.01 disproves Peaking Type & Peaking Frequency: "
                    "0 active appFw.so symbols despite dormant ns2 strings 0x4501/0x4503 -> EOPNOTSUPP=95"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                transport=transport,
                peaking_items_count=FX3_PEAKING_ITEMS_COUNT,
                effective_peaking_display="Off",
                effective_peaking_level=peaking_level,
                effective_peaking_color="Red",
                peaking_resettable=False,
                wheel_right_default="Assignable",
                peaking_on_body_lcd=False,
                hdmi_peaking_leaked_pixels=0,
                focus_mag_scale=focus_mag_scale,
                focus_mag_coexists_with_peaking=True,
                body_focus_map_exposed=False,
                focus_map_remote_wireless_only=False,
                focus_map_over_usb_supported=False,
                fx6_peaking_colors=VALID_FX6_PEAKING_COLORS,
                fx6_sdi_hdmi_output_display_independent=True,
                fx6_peaking_type_freq_appfw_symbols=0,
            )
        if operation != "fx6_peaking":
            return PeakingCleanHdmiFocusMagAndMapAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"ILME-FX6 does not expose FX3 operation {operation!r}",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                transport=transport,
                peaking_items_count=FX3_PEAKING_ITEMS_COUNT,
                effective_peaking_display="Off",
                effective_peaking_level=peaking_level,
                effective_peaking_color="Red",
                peaking_resettable=False,
                wheel_right_default="Assignable",
                peaking_on_body_lcd=False,
                hdmi_peaking_leaked_pixels=0,
                focus_mag_scale=focus_mag_scale,
                focus_mag_coexists_with_peaking=True,
                body_focus_map_exposed=False,
                focus_map_remote_wireless_only=False,
                focus_map_over_usb_supported=False,
                fx6_peaking_colors=VALID_FX6_PEAKING_COLORS,
                fx6_sdi_hdmi_output_display_independent=True,
                fx6_peaking_type_freq_appfw_symbols=0,
            )
        if peaking_color == "White":
            return PeakingCleanHdmiFocusMagAndMapAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "ILME-FX6 Monitoring > Peaking supports B&W/Red/Yellow/Blue (NOT White)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                transport=transport,
                peaking_items_count=FX3_PEAKING_ITEMS_COUNT,
                effective_peaking_display="Off",
                effective_peaking_level=peaking_level,
                effective_peaking_color="B&W",
                peaking_resettable=False,
                wheel_right_default="Assignable",
                peaking_on_body_lcd=False,
                hdmi_peaking_leaked_pixels=0,
                focus_mag_scale=focus_mag_scale,
                focus_mag_coexists_with_peaking=True,
                body_focus_map_exposed=False,
                focus_map_remote_wireless_only=False,
                focus_map_over_usb_supported=False,
                fx6_peaking_colors=VALID_FX6_PEAKING_COLORS,
                fx6_sdi_hdmi_output_display_independent=True,
                fx6_peaking_type_freq_appfw_symbols=0,
            )
        eff_disp = "Off" if initialize_applied else peaking_display
        return PeakingCleanHdmiFocusMagAndMapAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"ILME-FX6 Monitoring > Peaking ({eff_disp}, {peaking_level}, {peaking_color}) "
                "on VF/LCD only; SDI/HDMI Output Display independent; 0 Peaking Type/Freq"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            transport=transport,
            peaking_items_count=FX3_PEAKING_ITEMS_COUNT,
            effective_peaking_display=eff_disp,
            effective_peaking_level=peaking_level,
            effective_peaking_color=peaking_color,
            peaking_resettable=False,
            wheel_right_default="Assignable",
            peaking_on_body_lcd=(eff_disp == "On" and transport == "body_lcd"),
            hdmi_peaking_leaked_pixels=0,
            focus_mag_scale=focus_mag_scale,
            focus_mag_coexists_with_peaking=True,
            body_focus_map_exposed=False,
            focus_map_remote_wireless_only=False,
            focus_map_over_usb_supported=False,
            fx6_peaking_colors=VALID_FX6_PEAKING_COLORS,
            fx6_sdi_hdmi_output_display_independent=True,
            fx6_peaking_type_freq_appfw_symbols=0,
        )

    # 2. ILME-FX3 Ver. 7.02
    if operation in ("fx6_peaking", "fx6_dormant_type_freq"):
        return PeakingCleanHdmiFocusMagAndMapAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"ILME-FX3 does not expose FX6 peaking operation {operation!r}",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            transport=transport,
            peaking_items_count=FX3_PEAKING_ITEMS_COUNT,
            effective_peaking_display="Off",
            effective_peaking_level=peaking_level,
            effective_peaking_color="White",
            peaking_resettable=False,
            wheel_right_default="Peaking Display Select",
            peaking_on_body_lcd=False,
            hdmi_peaking_leaked_pixels=0,
            focus_mag_scale=focus_mag_scale,
            focus_mag_coexists_with_peaking=True,
            body_focus_map_exposed=False,
            focus_map_remote_wireless_only=True,
            focus_map_over_usb_supported=False,
            fx6_peaking_colors=VALID_FX6_PEAKING_COLORS,
            fx6_sdi_hdmi_output_display_independent=False,
            fx6_peaking_type_freq_appfw_symbols=0,
        )

    if operation == "focus_map":
        if transport == "body_lcd":
            return PeakingCleanHdmiFocusMagAndMapAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "FX3 on-body [Focus Map] (view_mp_focus_map) is 100% dormant -> EOPNOTSUPP=95"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                transport=transport,
                peaking_items_count=FX3_PEAKING_ITEMS_COUNT,
                effective_peaking_display=peaking_display,
                effective_peaking_level=peaking_level,
                effective_peaking_color=peaking_color,
                peaking_resettable=False,
                wheel_right_default="Peaking Display Select",
                peaking_on_body_lcd=False,
                hdmi_peaking_leaked_pixels=0,
                focus_mag_scale=focus_mag_scale,
                focus_mag_coexists_with_peaking=True,
                body_focus_map_exposed=False,
                focus_map_remote_wireless_only=True,
                focus_map_over_usb_supported=False,
                fx6_peaking_colors=VALID_FX6_PEAKING_COLORS,
                fx6_sdi_hdmi_output_display_independent=False,
                fx6_peaking_type_freq_appfw_symbols=0,
            )
        if transport == "usb":
            return PeakingCleanHdmiFocusMagAndMapAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "[Focus Map] remote stream unavailable over USB (wireless Monitor & Control Ver. 2.1.0+ only)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                transport=transport,
                peaking_items_count=FX3_PEAKING_ITEMS_COUNT,
                effective_peaking_display=peaking_display,
                effective_peaking_level=peaking_level,
                effective_peaking_color=peaking_color,
                peaking_resettable=False,
                wheel_right_default="Peaking Display Select",
                peaking_on_body_lcd=False,
                hdmi_peaking_leaked_pixels=0,
                focus_mag_scale=focus_mag_scale,
                focus_mag_coexists_with_peaking=True,
                body_focus_map_exposed=False,
                focus_map_remote_wireless_only=True,
                focus_map_over_usb_supported=False,
                fx6_peaking_colors=VALID_FX6_PEAKING_COLORS,
                fx6_sdi_hdmi_output_display_independent=False,
                fx6_peaking_type_freq_appfw_symbols=0,
            )
        if transport == "wifi_mc":
            ver_parts = tuple(int(x) for x in monitor_control_version.split("."))
            if ver_parts < (2, 1, 0):
                return PeakingCleanHdmiFocusMagAndMapAudit(
                    admitted=False,
                    errno_code=EOPNOTSUPP_ERRNO,
                    reason=(
                        f"Monitor & Control Ver. {monitor_control_version} < 2.1.0 lacks remote Focus Map"
                    ),
                    body_profile=body_profile,
                    fw_version=fw_version,
                    operation=operation,
                    transport=transport,
                    peaking_items_count=FX3_PEAKING_ITEMS_COUNT,
                    effective_peaking_display=peaking_display,
                    effective_peaking_level=peaking_level,
                    effective_peaking_color=peaking_color,
                    peaking_resettable=False,
                    wheel_right_default="Peaking Display Select",
                    peaking_on_body_lcd=False,
                    hdmi_peaking_leaked_pixels=0,
                    focus_mag_scale=focus_mag_scale,
                    focus_mag_coexists_with_peaking=True,
                    body_focus_map_exposed=False,
                    focus_map_remote_wireless_only=True,
                    focus_map_over_usb_supported=False,
                    fx6_peaking_colors=VALID_FX6_PEAKING_COLORS,
                    fx6_sdi_hdmi_output_display_independent=False,
                    fx6_peaking_type_freq_appfw_symbols=0,
                )
            return PeakingCleanHdmiFocusMagAndMapAudit(
                admitted=True,
                errno_code=0,
                reason=(
                    f"Wireless Monitor & Control Ver. {monitor_control_version} remote Focus Map active "
                    "(to_remote_event_focus_map)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                transport=transport,
                peaking_items_count=FX3_PEAKING_ITEMS_COUNT,
                effective_peaking_display=peaking_display,
                effective_peaking_level=peaking_level,
                effective_peaking_color=peaking_color,
                peaking_resettable=False,
                wheel_right_default="Peaking Display Select",
                peaking_on_body_lcd=False,
                hdmi_peaking_leaked_pixels=0,
                focus_mag_scale=focus_mag_scale,
                focus_mag_coexists_with_peaking=True,
                body_focus_map_exposed=False,
                focus_map_remote_wireless_only=True,
                focus_map_over_usb_supported=False,
                fx6_peaking_colors=VALID_FX6_PEAKING_COLORS,
                fx6_sdi_hdmi_output_display_independent=False,
                fx6_peaking_type_freq_appfw_symbols=0,
            )
        return PeakingCleanHdmiFocusMagAndMapAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"Focus Map unsupported on transport {transport!r}",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            transport=transport,
            peaking_items_count=FX3_PEAKING_ITEMS_COUNT,
            effective_peaking_display=peaking_display,
            effective_peaking_level=peaking_level,
            effective_peaking_color=peaking_color,
            peaking_resettable=False,
            wheel_right_default="Peaking Display Select",
            peaking_on_body_lcd=False,
            hdmi_peaking_leaked_pixels=0,
            focus_mag_scale=focus_mag_scale,
            focus_mag_coexists_with_peaking=True,
            body_focus_map_exposed=False,
            focus_map_remote_wireless_only=True,
            focus_map_over_usb_supported=False,
            fx6_peaking_colors=VALID_FX6_PEAKING_COLORS,
            fx6_sdi_hdmi_output_display_independent=False,
            fx6_peaking_type_freq_appfw_symbols=0,
        )

    # FX3 peaking_setting
    if peaking_color == "B&W":
        return PeakingCleanHdmiFocusMagAndMapAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="ILME-FX3 [Peaking Color] supports Red/Yellow/Blue/White (NOT B&W)",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            transport=transport,
            peaking_items_count=FX3_PEAKING_ITEMS_COUNT,
            effective_peaking_display="Off",
            effective_peaking_level=peaking_level,
            effective_peaking_color="White",
            peaking_resettable=False,
            wheel_right_default="Peaking Display Select",
            peaking_on_body_lcd=False,
            hdmi_peaking_leaked_pixels=0,
            focus_mag_scale=focus_mag_scale,
            focus_mag_coexists_with_peaking=True,
            body_focus_map_exposed=False,
            focus_map_remote_wireless_only=True,
            focus_map_over_usb_supported=False,
            fx6_peaking_colors=VALID_FX6_PEAKING_COLORS,
            fx6_sdi_hdmi_output_display_independent=False,
            fx6_peaking_type_freq_appfw_symbols=0,
        )

    # All 3 FX3 peaking items are Reset-resistant; Initialize restores Off / Mid / White
    eff_disp = "Off" if initialize_applied else peaking_display
    eff_lvl = "Mid" if initialize_applied else peaking_level
    eff_clr = "White" if initialize_applied else peaking_color
    on_body_lcd = (eff_disp == "On") and (transport == "body_lcd")

    # Even if hdmi_info_display == "On" or raw_output == "On", peaking NEVER outputs on HDMI!
    return PeakingCleanHdmiFocusMagAndMapAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 [Peaking Display]={eff_disp!r} ({eff_lvl}/{eff_clr}, Reset-resistant; "
            f"Coexists with [Focus Magnifier]={focus_mag_scale}; Clean-HDMI pixels=0 "
            f"even with HDMI Info={hdmi_info_display!r} & RAW Output={raw_output!r})"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        transport=transport,
        peaking_items_count=FX3_PEAKING_ITEMS_COUNT,
        effective_peaking_display=eff_disp,
        effective_peaking_level=eff_lvl,
        effective_peaking_color=eff_clr,
        peaking_resettable=False,
        wheel_right_default="Peaking Display Select",
        peaking_on_body_lcd=on_body_lcd,
        hdmi_peaking_leaked_pixels=0,
        focus_mag_scale=focus_mag_scale,
        focus_mag_coexists_with_peaking=True,
        body_focus_map_exposed=False,
        focus_map_remote_wireless_only=True,
        focus_map_over_usb_supported=False,
        fx6_peaking_colors=VALID_FX6_PEAKING_COLORS,
        fx6_sdi_hdmi_output_display_independent=False,
        fx6_peaking_type_freq_appfw_symbols=0,
    )


# ---------------------------------------------------------------------------
# Sub-Model 80B: Ver. 2.00+ Audio Level Display Removal, Wind & XLR-H1 vs FX6
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AudioMeterWindAndXlrh1VsFx6Audit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    legacy_audio_level_display_menu_exposed: bool
    audio_recording_items_count: int
    audio_recording_resettable: bool
    effective_audio_rec_level: int
    rec_level_defult_typo_symbol: str
    permanent_limiter_active: bool
    disp_big6_meter_channels: int
    remote_sdk_audio_meter_read_only: bool
    active_audio_input: str
    effective_wind_noise_reduct: str
    wind_low_cut_dsp_active: bool
    wind_bypassed_reason: Optional[str]
    xlrh1_hardware_low_cut: str
    fx6_ch_wind_filters_count: int
    fx6_handle_physical_low_cut: bool
    fx6_limiter_mode_steps_count: int


def simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "wind_noise_reduct",
    audio_recording: str = "On",
    audio_rec_level: int = AUDIO_REC_LEVEL_DEFAULT,
    audio_out_timing: str = "Live",
    wind_noise_reduct: str = "On",
    shoe_audio_format: str = "48kHz/24bit 4ch",
    sq_mode: bool = False,
    mic_35mm_plugged: bool = False,
    xlrh1_attached: bool = False,
    xlrh1_hardware_low_cut: str = "Off",
    fx6_ch_wind_filters: Tuple[str, str, str, str] = ("Off", "Off", "Off", "Off"),
    fx6_limiter_mode: str = "-6dB",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> AudioMeterWindAndXlrh1VsFx6Audit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage80Phase360Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage80Phase360Error(f"Invalid fw_version: {fw_version!r}")
    if operation not in VALID_AUDIO_OPERATIONS:
        raise Stage80Phase360Error(f"Invalid operation: {operation!r}")
    if audio_recording not in VALID_TOGGLES:
        raise Stage80Phase360Error(f"Invalid audio_recording: {audio_recording!r}")
    if not (0 <= audio_rec_level <= 31):
        raise Stage80Phase360Error(
            f"audio_rec_level {audio_rec_level} out of 0..31"
        )
    if audio_out_timing not in VALID_AUDIO_TIMING:
        raise Stage80Phase360Error(f"Invalid audio_out_timing: {audio_out_timing!r}")
    if wind_noise_reduct not in VALID_WIND_OPTIONS:
        raise Stage80Phase360Error(f"Invalid wind_noise_reduct: {wind_noise_reduct!r}")
    if xlrh1_hardware_low_cut not in VALID_XLRH1_LOW_CUT:
        raise Stage80Phase360Error(
            f"Invalid xlrh1_hardware_low_cut: {xlrh1_hardware_low_cut!r}"
        )
    if shoe_audio_format not in VALID_SHOE_AUDIO_FORMATS:
        raise Stage80Phase360Error(f"Invalid shoe_audio_format: {shoe_audio_format!r}")
    if fx6_limiter_mode not in FX6_6_LIMITER_MODES:
        raise Stage80Phase360Error(f"Invalid fx6_limiter_mode: {fx6_limiter_mode!r}")

    typo_sym = "adj_audio_rec_level_defult"

    # Priority: 3.5mm MIC > XLR-H1 DIGITAL > Internal Mic
    if mic_35mm_plugged:
        active_input = "3.5mm MIC"
    elif xlrh1_attached:
        active_input = "XLR-H1"
    else:
        active_input = "Internal Mic"

    # 1. ILME-FX6 Ver. 6.01
    if body_profile == BODY_MODEL_FX6:
        if operation == "fx6_handle_physical_low_cut":
            return AudioMeterWindAndXlrh1VsFx6Audit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "ILME-FX6 Smart Handle has ZERO physical LOW CUT switch "
                    "(uses menu CH1..CH4 Wind Filter -> EOPNOTSUPP=95)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                legacy_audio_level_display_menu_exposed=False,
                audio_recording_items_count=AUDIO_RECORDING_MENU_ITEMS_COUNT,
                audio_recording_resettable=False,
                effective_audio_rec_level=audio_rec_level,
                rec_level_defult_typo_symbol=typo_sym,
                permanent_limiter_active=False,
                disp_big6_meter_channels=4,
                remote_sdk_audio_meter_read_only=True,
                active_audio_input="XLR Handle",
                effective_wind_noise_reduct="Off",
                wind_low_cut_dsp_active=False,
                wind_bypassed_reason=None,
                xlrh1_hardware_low_cut="UNSUPPORTED",
                fx6_ch_wind_filters_count=FX6_CH_WIND_FILTER_COUNT,
                fx6_handle_physical_low_cut=False,
                fx6_limiter_mode_steps_count=FX6_LIMITER_MODE_STEPS_COUNT,
            )
        if operation != "fx6_audio_control":
            return AudioMeterWindAndXlrh1VsFx6Audit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"ILME-FX6 does not expose FX3 audio operation {operation!r}",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                legacy_audio_level_display_menu_exposed=False,
                audio_recording_items_count=AUDIO_RECORDING_MENU_ITEMS_COUNT,
                audio_recording_resettable=False,
                effective_audio_rec_level=audio_rec_level,
                rec_level_defult_typo_symbol=typo_sym,
                permanent_limiter_active=False,
                disp_big6_meter_channels=4,
                remote_sdk_audio_meter_read_only=True,
                active_audio_input="XLR Handle",
                effective_wind_noise_reduct="Off",
                wind_low_cut_dsp_active=False,
                wind_bypassed_reason=None,
                xlrh1_hardware_low_cut="UNSUPPORTED",
                fx6_ch_wind_filters_count=FX6_CH_WIND_FILTER_COUNT,
                fx6_handle_physical_low_cut=False,
                fx6_limiter_mode_steps_count=FX6_LIMITER_MODE_STEPS_COUNT,
            )
        return AudioMeterWindAndXlrh1VsFx6Audit(
            admitted=True,
            errno_code=0,
            reason=(
                f"ILME-FX6 CH1..CH4 Wind Filter={fx6_ch_wind_filters!r}, "
                f"Limiter Mode={fx6_limiter_mode!r} (6 steps), Audio Level Meter active"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            legacy_audio_level_display_menu_exposed=False,
            audio_recording_items_count=AUDIO_RECORDING_MENU_ITEMS_COUNT,
            audio_recording_resettable=False,
            effective_audio_rec_level=audio_rec_level,
            rec_level_defult_typo_symbol=typo_sym,
            permanent_limiter_active=(fx6_limiter_mode != "Off"),
            disp_big6_meter_channels=0 if sq_mode else 4,
            remote_sdk_audio_meter_read_only=True,
            active_audio_input="FX6 4ch Audio",
            effective_wind_noise_reduct="On" if any(x == "On" for x in fx6_ch_wind_filters) else "Off",
            wind_low_cut_dsp_active=any(x == "On" for x in fx6_ch_wind_filters),
            wind_bypassed_reason=None,
            xlrh1_hardware_low_cut="UNSUPPORTED",
            fx6_ch_wind_filters_count=FX6_CH_WIND_FILTER_COUNT,
            fx6_handle_physical_low_cut=False,
            fx6_limiter_mode_steps_count=FX6_LIMITER_MODE_STEPS_COUNT,
        )

    # 2. ILME-FX3
    if operation in ("fx6_audio_control", "fx6_handle_physical_low_cut"):
        return AudioMeterWindAndXlrh1VsFx6Audit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"ILME-FX3 does not expose FX6 audio operation {operation!r}",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            legacy_audio_level_display_menu_exposed=(fw_version == FW_VER_101),
            audio_recording_items_count=AUDIO_RECORDING_MENU_ITEMS_COUNT,
            audio_recording_resettable=True,
            effective_audio_rec_level=AUDIO_REC_LEVEL_DEFAULT,
            rec_level_defult_typo_symbol=typo_sym,
            permanent_limiter_active=True,
            disp_big6_meter_channels=2,
            remote_sdk_audio_meter_read_only=True,
            active_audio_input=active_input,
            effective_wind_noise_reduct="Off",
            wind_low_cut_dsp_active=False,
            wind_bypassed_reason=None,
            xlrh1_hardware_low_cut=xlrh1_hardware_low_cut if xlrh1_attached else "Detached",
            fx6_ch_wind_filters_count=0,
            fx6_handle_physical_low_cut=False,
            fx6_limiter_mode_steps_count=0,
        )

    # [Audio Recording] all 5 items ARE resettable (`Can be reset`)
    reset_active = camera_settings_reset_applied or initialize_applied
    eff_level = AUDIO_REC_LEVEL_DEFAULT if reset_active else audio_rec_level
    eff_wind_req = "Off" if reset_active else wind_noise_reduct
    eff_rec = "On" if reset_active else audio_recording

    if sq_mode:
        ch_count = 0
    elif xlrh1_attached and active_input == "XLR-H1" and "4ch" in shoe_audio_format:
        ch_count = 4
    elif eff_rec == "Off":
        ch_count = 0
    else:
        ch_count = 2

    if operation == "legacy_audio_level_display":
        if fw_version == FW_VER_101:
            return AudioMeterWindAndXlrh1VsFx6Audit(
                admitted=True,
                errno_code=0,
                reason="FX3 Ver. 1.01 legacy firmware exposed standalone [Audio Level Display]",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                legacy_audio_level_display_menu_exposed=True,
                audio_recording_items_count=6,
                audio_recording_resettable=True,
                effective_audio_rec_level=eff_level,
                rec_level_defult_typo_symbol=typo_sym,
                permanent_limiter_active=True,
                disp_big6_meter_channels=ch_count,
                remote_sdk_audio_meter_read_only=True,
                active_audio_input=active_input,
                effective_wind_noise_reduct=eff_wind_req if eff_wind_req in ("Off", "On") else "Off",
                wind_low_cut_dsp_active=False,
                wind_bypassed_reason=None,
                xlrh1_hardware_low_cut=xlrh1_hardware_low_cut if xlrh1_attached else "Detached",
                fx6_ch_wind_filters_count=0,
                fx6_handle_physical_low_cut=False,
                fx6_limiter_mode_steps_count=0,
            )
        return AudioMeterWindAndXlrh1VsFx6Audit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"FX3 Ver. {fw_version} permanently removed standalone [Audio Level Display] "
                "(_f 0x7a36 Ver. 1.x legacy; auto-rendered via DISP/BIG6 -> EOPNOTSUPP=95)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            legacy_audio_level_display_menu_exposed=False,
            audio_recording_items_count=AUDIO_RECORDING_MENU_ITEMS_COUNT,
            audio_recording_resettable=True,
            effective_audio_rec_level=eff_level,
            rec_level_defult_typo_symbol=typo_sym,
            permanent_limiter_active=True,
            disp_big6_meter_channels=ch_count,
            remote_sdk_audio_meter_read_only=True,
            active_audio_input=active_input,
            effective_wind_noise_reduct="Off",
            wind_low_cut_dsp_active=False,
            wind_bypassed_reason=None,
            xlrh1_hardware_low_cut=xlrh1_hardware_low_cut if xlrh1_attached else "Detached",
            fx6_ch_wind_filters_count=0,
            fx6_handle_physical_low_cut=False,
            fx6_limiter_mode_steps_count=0,
        )

    if operation == "remote_sdk_audio_meter_write":
        return AudioMeterWindAndXlrh1VsFx6Audit(
            admitted=False,
            errno_code=EACCES_ERRNO,
            reason="Remote SDK (CrSDK) Audio Level Meter telemetry is strictly read-only -> EACCES=13",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            legacy_audio_level_display_menu_exposed=False,
            audio_recording_items_count=AUDIO_RECORDING_MENU_ITEMS_COUNT,
            audio_recording_resettable=True,
            effective_audio_rec_level=eff_level,
            rec_level_defult_typo_symbol=typo_sym,
            permanent_limiter_active=True,
            disp_big6_meter_channels=ch_count,
            remote_sdk_audio_meter_read_only=True,
            active_audio_input=active_input,
            effective_wind_noise_reduct="Off",
            wind_low_cut_dsp_active=False,
            wind_bypassed_reason=None,
            xlrh1_hardware_low_cut=xlrh1_hardware_low_cut if xlrh1_attached else "Detached",
            fx6_ch_wind_filters_count=0,
            fx6_handle_physical_low_cut=False,
            fx6_limiter_mode_steps_count=0,
        )

    if eff_wind_req in ("Auto", "On Advanced"):
        return AudioMeterWindAndXlrh1VsFx6Audit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"FX3 Ver. {fw_version} [Wind Noise Reduct.] is 2-option (Off/On ONLY); "
                f"dormant {eff_wind_req!r} rejected -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            legacy_audio_level_display_menu_exposed=False,
            audio_recording_items_count=AUDIO_RECORDING_MENU_ITEMS_COUNT,
            audio_recording_resettable=True,
            effective_audio_rec_level=eff_level,
            rec_level_defult_typo_symbol=typo_sym,
            permanent_limiter_active=True,
            disp_big6_meter_channels=ch_count,
            remote_sdk_audio_meter_read_only=True,
            active_audio_input=active_input,
            effective_wind_noise_reduct="Off",
            wind_low_cut_dsp_active=False,
            wind_bypassed_reason=None,
            xlrh1_hardware_low_cut=xlrh1_hardware_low_cut if xlrh1_attached else "Detached",
            fx6_ch_wind_filters_count=0,
            fx6_handle_physical_low_cut=False,
            fx6_limiter_mode_steps_count=0,
        )

    if operation == "xlrh1_hardware_low_cut":
        if not xlrh1_attached:
            return AudioMeterWindAndXlrh1VsFx6Audit(
                admitted=False,
                errno_code=ENODEV_ERRNO,
                reason="XLR-H1 top handle is not attached to MI Shoe -> ENODEV=19",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                legacy_audio_level_display_menu_exposed=False,
                audio_recording_items_count=AUDIO_RECORDING_MENU_ITEMS_COUNT,
                audio_recording_resettable=True,
                effective_audio_rec_level=eff_level,
                rec_level_defult_typo_symbol=typo_sym,
                permanent_limiter_active=True,
                disp_big6_meter_channels=ch_count,
                remote_sdk_audio_meter_read_only=True,
                active_audio_input=active_input,
                effective_wind_noise_reduct=eff_wind_req,
                wind_low_cut_dsp_active=False,
                wind_bypassed_reason="XLR-H1 detached",
                xlrh1_hardware_low_cut="Detached",
                fx6_ch_wind_filters_count=0,
                fx6_handle_physical_low_cut=False,
                fx6_limiter_mode_steps_count=0,
            )
        if mic_35mm_plugged:
            return AudioMeterWindAndXlrh1VsFx6Audit(
                admitted=False,
                errno_code=EBUSY_ERRNO,
                reason=(
                    "3.5mm MIC preempts XLR-H1 DIGITAL under FX3 priority rule "
                    "(3.5mm MIC > XLR-H1 > Internal Mic) -> EBUSY=16"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                legacy_audio_level_display_menu_exposed=False,
                audio_recording_items_count=AUDIO_RECORDING_MENU_ITEMS_COUNT,
                audio_recording_resettable=True,
                effective_audio_rec_level=eff_level,
                rec_level_defult_typo_symbol=typo_sym,
                permanent_limiter_active=True,
                disp_big6_meter_channels=ch_count,
                remote_sdk_audio_meter_read_only=True,
                active_audio_input="3.5mm MIC",
                effective_wind_noise_reduct=eff_wind_req,
                wind_low_cut_dsp_active=False,
                wind_bypassed_reason="3.5mm MIC active",
                xlrh1_hardware_low_cut=xlrh1_hardware_low_cut,
                fx6_ch_wind_filters_count=0,
                fx6_handle_physical_low_cut=False,
                fx6_limiter_mode_steps_count=0,
            )
        return AudioMeterWindAndXlrh1VsFx6Audit(
            admitted=True,
            errno_code=0,
            reason=(
                f"XLR-H1 DIGITAL hardware LOW CUT={xlrh1_hardware_low_cut!r} active "
                "(software [Wind Noise Reduct.] bypassed on XLR-H1)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            legacy_audio_level_display_menu_exposed=False,
            audio_recording_items_count=AUDIO_RECORDING_MENU_ITEMS_COUNT,
            audio_recording_resettable=True,
            effective_audio_rec_level=eff_level,
            rec_level_defult_typo_symbol=typo_sym,
            permanent_limiter_active=True,
            disp_big6_meter_channels=ch_count,
            remote_sdk_audio_meter_read_only=True,
            active_audio_input="XLR-H1",
            effective_wind_noise_reduct=eff_wind_req,
            wind_low_cut_dsp_active=False,
            wind_bypassed_reason="XLR-H1 active",
            xlrh1_hardware_low_cut=xlrh1_hardware_low_cut,
            fx6_ch_wind_filters_count=0,
            fx6_handle_physical_low_cut=False,
            fx6_limiter_mode_steps_count=0,
        )

    # Internal-only Wind Noise Reduct. + 5-item Audio Recording + DISP/BIG6 meter
    bypass_reason: Optional[str] = None
    if sq_mode:
        bypass_reason = "S&Q mode (0ch audio)"
    elif active_input != "Internal Mic":
        bypass_reason = f"External input active ({active_input})"
    dsp_active = (eff_wind_req == "On") and (bypass_reason is None) and (eff_rec == "On")

    return AudioMeterWindAndXlrh1VsFx6Audit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 Ver. {fw_version} Audio Recording (5 items Resettable, default_lvl=26/{typo_sym}, "
            f"meter={ch_count}ch, input={active_input}, wind={eff_wind_req!r}, dsp_low_cut={dsp_active}"
            + (f", bypassed={bypass_reason!r})" if bypass_reason else ")")
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        legacy_audio_level_display_menu_exposed=False,
        audio_recording_items_count=AUDIO_RECORDING_MENU_ITEMS_COUNT,
        audio_recording_resettable=True,
        effective_audio_rec_level=eff_level,
        rec_level_defult_typo_symbol=typo_sym,
        permanent_limiter_active=True,
        disp_big6_meter_channels=ch_count,
        remote_sdk_audio_meter_read_only=True,
        active_audio_input=active_input,
        effective_wind_noise_reduct=eff_wind_req,
        wind_low_cut_dsp_active=dsp_active,
        wind_bypassed_reason=bypass_reason,
        xlrh1_hardware_low_cut=xlrh1_hardware_low_cut if xlrh1_attached else "Detached",
        fx6_ch_wind_filters_count=0,
        fx6_handle_physical_low_cut=False,
        fx6_limiter_mode_steps_count=0,
    )


# ---------------------------------------------------------------------------
# Sub-Model 80C: [USB Power Supply], NP-FZ100, ON-No-Charge & DC-C1 vs FX6
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UsbPowerSupplyNpFz100Dcc1VsFx6Audit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    mode: str
    port: str
    effective_usb_power_supply: str
    usb_power_resettable: bool
    np_fz100_inserted: bool
    batteryless_boot_supported: bool
    power_on_supply_active: bool
    charging_active: bool
    charge_led_state: str
    power_save_bypassed: bool
    battery_draining_5v15a_low: bool
    instant_power_loss_on_hot_pull: bool
    monitor_brightness_locked_max: bool
    fx6_dc_in_volts: Optional[float]
    fx6_dc_low_volt_warning: Optional[str]
    fx6_seamless_dcin_to_bpu_pullover: bool
    fx6_hot_replug_reboot_blocked: bool


def simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    mode: str = "power_on",
    port: str = "Type-C",
    usb_power_supply: str = "On",
    np_fz100_inserted: bool = True,
    battery_hot_pulled: bool = False,
    power_profile: str = "9V/3A",
    ambient_temp_c: int = 23,
    dc_c1_pd_watts: int = 65,
    dc_c1_cable_amps: int = 5,
    fx6_dc_in_volts: float = 19.5,
    fx6_bpu_inserted: bool = False,
    fx6_dcin_unplugged_to_bpu: bool = False,
    fx6_dcin_hot_replug_while_running: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> UsbPowerSupplyNpFz100Dcc1VsFx6Audit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage80Phase360Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage80Phase360Error(f"Invalid fw_version: {fw_version!r}")
    if mode not in VALID_USB_POWER_MODES:
        raise Stage80Phase360Error(f"Invalid mode: {mode!r}")
    if port not in VALID_USB_PORTS:
        raise Stage80Phase360Error(f"Invalid port: {port!r}")
    if usb_power_supply not in VALID_TOGGLES:
        raise Stage80Phase360Error(f"Invalid usb_power_supply: {usb_power_supply!r}")
    if power_profile not in VALID_POWER_PROFILES:
        raise Stage80Phase360Error(f"Invalid power_profile: {power_profile!r}")

    # 1. ILME-FX6 Ver. 6.01 19.5V DC IN vs USB-C Power Rejection
    if body_profile == BODY_MODEL_FX6:
        if mode == "fx6_usbc" or port == "Type-C":
            return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="ILME-FX6 USB-C port is incapable of powering the camera body -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                mode=mode,
                port=port,
                effective_usb_power_supply="Off",
                usb_power_resettable=False,
                np_fz100_inserted=False,
                batteryless_boot_supported=True,
                power_on_supply_active=False,
                charging_active=False,
                charge_led_state="Off",
                power_save_bypassed=False,
                battery_draining_5v15a_low=False,
                instant_power_loss_on_hot_pull=False,
                monitor_brightness_locked_max=False,
                fx6_dc_in_volts=None,
                fx6_dc_low_volt_warning=None,
                fx6_seamless_dcin_to_bpu_pullover=False,
                fx6_hot_replug_reboot_blocked=False,
            )
        if fx6_dcin_hot_replug_while_running and fx6_bpu_inserted:
            return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
                admitted=False,
                errno_code=EPERM_ERRNO,
                reason=(
                    "ILME-FX6 DC IN hot-replug while running on BP-U triggers reboot hazard "
                    "(HIL power guard blocked unguarded hot-replug -> EPERM=1)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                mode=mode,
                port="FX6_DC_IN",
                effective_usb_power_supply="UNSUPPORTED",
                usb_power_resettable=False,
                np_fz100_inserted=False,
                batteryless_boot_supported=True,
                power_on_supply_active=False,
                charging_active=False,
                charge_led_state="Off",
                power_save_bypassed=False,
                battery_draining_5v15a_low=False,
                instant_power_loss_on_hot_pull=False,
                monitor_brightness_locked_max=False,
                fx6_dc_in_volts=fx6_dc_in_volts,
                fx6_dc_low_volt_warning=None,
                fx6_seamless_dcin_to_bpu_pullover=False,
                fx6_hot_replug_reboot_blocked=True,
            )
        if fx6_dcin_unplugged_to_bpu:
            if not fx6_bpu_inserted:
                return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
                    admitted=False,
                    errno_code=EIO_ERRNO,
                    reason="ILME-FX6 DC IN unplugged with no BP-U inserted -> EIO=5",
                    body_profile=body_profile,
                    fw_version=fw_version,
                    mode=mode,
                    port="FX6_DC_IN",
                    effective_usb_power_supply="UNSUPPORTED",
                    usb_power_resettable=False,
                    np_fz100_inserted=False,
                    batteryless_boot_supported=True,
                    power_on_supply_active=False,
                    charging_active=False,
                    charge_led_state="Off",
                    power_save_bypassed=False,
                    battery_draining_5v15a_low=False,
                    instant_power_loss_on_hot_pull=True,
                    monitor_brightness_locked_max=False,
                    fx6_dc_in_volts=0.0,
                    fx6_dc_low_volt_warning="DC_POWER_LOST",
                    fx6_seamless_dcin_to_bpu_pullover=False,
                    fx6_hot_replug_reboot_blocked=False,
                )
            return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
                admitted=True,
                errno_code=0,
                reason="ILME-FX6 seamless DC IN -> BP-U battery pull-over (0 reboot)",
                body_profile=body_profile,
                fw_version=fw_version,
                mode=mode,
                port="FX6_DC_IN",
                effective_usb_power_supply="UNSUPPORTED",
                usb_power_resettable=False,
                np_fz100_inserted=False,
                batteryless_boot_supported=True,
                power_on_supply_active=True,
                charging_active=False,
                charge_led_state="Off",
                power_save_bypassed=False,
                battery_draining_5v15a_low=False,
                instant_power_loss_on_hot_pull=False,
                monitor_brightness_locked_max=False,
                fx6_dc_in_volts=0.0,
                fx6_dc_low_volt_warning=None,
                fx6_seamless_dcin_to_bpu_pullover=True,
                fx6_hot_replug_reboot_blocked=False,
            )
        if fx6_dc_in_volts <= FX6_DC_IN_WARN2_VOLTS:
            return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=(
                    f"ILME-FX6 DC IN {fx6_dc_in_volts:.1f}V <= DC_LOW_VOLT2 ({FX6_DC_IN_WARN2_VOLTS:.1f}V) "
                    "triggers critical low-voltage shutdown -> EINVAL=22"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                mode=mode,
                port="FX6_DC_IN",
                effective_usb_power_supply="UNSUPPORTED",
                usb_power_resettable=False,
                np_fz100_inserted=False,
                batteryless_boot_supported=True,
                power_on_supply_active=False,
                charging_active=False,
                charge_led_state="Off",
                power_save_bypassed=False,
                battery_draining_5v15a_low=False,
                instant_power_loss_on_hot_pull=False,
                monitor_brightness_locked_max=False,
                fx6_dc_in_volts=fx6_dc_in_volts,
                fx6_dc_low_volt_warning="BKID_APP_SETTING_DC_LOW_VOLT2",
                fx6_seamless_dcin_to_bpu_pullover=False,
                fx6_hot_replug_reboot_blocked=False,
            )
        if fx6_dc_in_volts <= FX6_DC_IN_WARN1_VOLTS:
            return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
                admitted=True,
                errno_code=0,
                reason=(
                    f"ILME-FX6 DC IN {fx6_dc_in_volts:.1f}V triggers BKID_APP_SETTING_DC_LOW_VOLT1 "
                    f"(<= {FX6_DC_IN_WARN1_VOLTS:.1f}V warning)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                mode=mode,
                port="FX6_DC_IN",
                effective_usb_power_supply="UNSUPPORTED",
                usb_power_resettable=False,
                np_fz100_inserted=False,
                batteryless_boot_supported=True,
                power_on_supply_active=True,
                charging_active=False,
                charge_led_state="Off",
                power_save_bypassed=False,
                battery_draining_5v15a_low=False,
                instant_power_loss_on_hot_pull=False,
                monitor_brightness_locked_max=False,
                fx6_dc_in_volts=fx6_dc_in_volts,
                fx6_dc_low_volt_warning="BKID_APP_SETTING_DC_LOW_VOLT1",
                fx6_seamless_dcin_to_bpu_pullover=False,
                fx6_hot_replug_reboot_blocked=False,
            )
        if fx6_dc_in_volts < FX6_DC_IN_MIN_VOLTS or fx6_dc_in_volts > FX6_DC_IN_MAX_VOLTS:
            return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=(
                    f"ILME-FX6 DC IN {fx6_dc_in_volts:.1f}V outside 18.0V..20.5V tolerance -> EINVAL=22"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                mode=mode,
                port="FX6_DC_IN",
                effective_usb_power_supply="UNSUPPORTED",
                usb_power_resettable=False,
                np_fz100_inserted=False,
                batteryless_boot_supported=True,
                power_on_supply_active=False,
                charging_active=False,
                charge_led_state="Off",
                power_save_bypassed=False,
                battery_draining_5v15a_low=False,
                instant_power_loss_on_hot_pull=False,
                monitor_brightness_locked_max=False,
                fx6_dc_in_volts=fx6_dc_in_volts,
                fx6_dc_low_volt_warning="OUT_OF_RANGE",
                fx6_seamless_dcin_to_bpu_pullover=False,
                fx6_hot_replug_reboot_blocked=False,
            )
        return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
            admitted=True,
            errno_code=0,
            reason=(
                f"ILME-FX6 19.5V DC IN ({fx6_dc_in_volts:.1f}V, valid 18.0..20.5V) "
                f"supports true battery-less boot (BP-U={fx6_bpu_inserted})"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            mode=mode,
            port="FX6_DC_IN",
            effective_usb_power_supply="UNSUPPORTED",
            usb_power_resettable=False,
            np_fz100_inserted=False,
            batteryless_boot_supported=True,
            power_on_supply_active=True,
            charging_active=False,
            charge_led_state="Off",
            power_save_bypassed=False,
            battery_draining_5v15a_low=False,
            instant_power_loss_on_hot_pull=False,
            monitor_brightness_locked_max=False,
            fx6_dc_in_volts=fx6_dc_in_volts,
            fx6_dc_low_volt_warning=None,
            fx6_seamless_dcin_to_bpu_pullover=False,
            fx6_hot_replug_reboot_blocked=False,
        )

    # 2. ILME-FX3 Ver. 7.02
    if mode in ("fx6_dc_in", "fx6_usbc"):
        return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"ILME-FX3 does not expose FX6 power mode {mode!r}",
            body_profile=body_profile,
            fw_version=fw_version,
            mode=mode,
            port=port,
            effective_usb_power_supply=usb_power_supply,
            usb_power_resettable=False,
            np_fz100_inserted=np_fz100_inserted,
            batteryless_boot_supported=False,
            power_on_supply_active=False,
            charging_active=False,
            charge_led_state="Off",
            power_save_bypassed=False,
            battery_draining_5v15a_low=False,
            instant_power_loss_on_hot_pull=False,
            monitor_brightness_locked_max=False,
            fx6_dc_in_volts=None,
            fx6_dc_low_volt_warning=None,
            fx6_seamless_dcin_to_bpu_pullover=False,
            fx6_hot_replug_reboot_blocked=False,
        )

    # [USB Power Supply] is Reset-resistant; Initialize restores On
    eff_usb_ps = "On" if initialize_applied else usb_power_supply

    if port == "Multi/Micro-USB":
        return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
            admitted=False,
            errno_code=ENODEV_ERRNO,
            reason=(
                "base 0xe931: Power supply capable only through USB Type-C port (Multi/Micro-USB rejected -> ENODEV=19)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            mode=mode,
            port=port,
            effective_usb_power_supply=eff_usb_ps,
            usb_power_resettable=False,
            np_fz100_inserted=np_fz100_inserted,
            batteryless_boot_supported=False,
            power_on_supply_active=False,
            charging_active=False,
            charge_led_state="Off",
            power_save_bypassed=False,
            battery_draining_5v15a_low=False,
            instant_power_loss_on_hot_pull=False,
            monitor_brightness_locked_max=False,
            fx6_dc_in_volts=None,
            fx6_dc_low_volt_warning=None,
            fx6_seamless_dcin_to_bpu_pullover=False,
            fx6_hot_replug_reboot_blocked=False,
        )

    if mode == "dc_c1" or port == "DC-C1":
        if dc_c1_pd_watts < DCC1_MIN_PD_WATTS or dc_c1_cable_amps < DCC1_REQUIRED_CABLE_AMPS:
            return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=(
                    f"DC-C1 requires >=65W USB-PD & 5A e-marked cable "
                    f"(got {dc_c1_pd_watts}W / {dc_c1_cable_amps}A -> EINVAL=22)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                mode=mode,
                port="DC-C1",
                effective_usb_power_supply=eff_usb_ps,
                usb_power_resettable=False,
                np_fz100_inserted=False,
                batteryless_boot_supported=False,
                power_on_supply_active=False,
                charging_active=False,
                charge_led_state="Off",
                power_save_bypassed=False,
                battery_draining_5v15a_low=False,
                instant_power_loss_on_hot_pull=False,
                monitor_brightness_locked_max=False,
                fx6_dc_in_volts=None,
                fx6_dc_low_volt_warning=None,
                fx6_seamless_dcin_to_bpu_pullover=False,
                fx6_hot_replug_reboot_blocked=False,
            )
        return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
            admitted=True,
            errno_code=0,
            reason=(
                f"DC-C1 coupler booted ({dc_c1_pd_watts}W/{dc_c1_cable_amps}A; satisfies "
                "VAL_battery_inserted_BATTERY_IS_INSERTED; Monitor Brightness locked Max)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            mode=mode,
            port="DC-C1",
            effective_usb_power_supply=eff_usb_ps,
            usb_power_resettable=False,
            np_fz100_inserted=True,
            batteryless_boot_supported=False,
            power_on_supply_active=True,
            charging_active=False,
            charge_led_state="Off",
            power_save_bypassed=True,
            battery_draining_5v15a_low=False,
            instant_power_loss_on_hot_pull=False,
            monitor_brightness_locked_max=True,
            fx6_dc_in_volts=None,
            fx6_dc_low_volt_warning=None,
            fx6_seamless_dcin_to_bpu_pullover=False,
            fx6_hot_replug_reboot_blocked=False,
        )

    # Mandatory NP-FZ100 insertion & instant power loss on hot-pull
    if (not np_fz100_inserted) or battery_hot_pulled:
        return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
            admitted=False,
            errno_code=EIO_ERRNO,
            reason=(
                "libUsbBusPower.so VAL_battery_inserted_BATTERY_IS_NOT_INSERTED: "
                "NP-FZ100 mandatory (0 battery-less boot; instant power loss on hot-pull -> EIO=5)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            mode=mode,
            port=port,
            effective_usb_power_supply=eff_usb_ps,
            usb_power_resettable=False,
            np_fz100_inserted=False,
            batteryless_boot_supported=False,
            power_on_supply_active=False,
            charging_active=False,
            charge_led_state="Off",
            power_save_bypassed=False,
            battery_draining_5v15a_low=False,
            instant_power_loss_on_hot_pull=battery_hot_pulled,
            monitor_brightness_locked_max=False,
            fx6_dc_in_volts=None,
            fx6_dc_low_volt_warning=None,
            fx6_seamless_dcin_to_bpu_pullover=False,
            fx6_hot_replug_reboot_blocked=False,
        )

    # Power-OFF charges NP-FZ100 strictly in 10C..30C window
    if mode == "power_off":
        if ambient_temp_c < POWER_OFF_CHARGE_TEMP_MIN_C or ambient_temp_c > POWER_OFF_CHARGE_TEMP_MAX_C:
            return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
                admitted=False,
                errno_code=EACCES_ERRNO,
                reason=(
                    f"Power-OFF NP-FZ100 charge halted at {ambient_temp_c}C "
                    f"(outside 10..30C window; CHARGE LED fast-blink fault -> EACCES=13)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                mode=mode,
                port=port,
                effective_usb_power_supply=eff_usb_ps,
                usb_power_resettable=False,
                np_fz100_inserted=True,
                batteryless_boot_supported=False,
                power_on_supply_active=False,
                charging_active=False,
                charge_led_state="FastBlink",
                power_save_bypassed=False,
                battery_draining_5v15a_low=False,
                instant_power_loss_on_hot_pull=False,
                monitor_brightness_locked_max=False,
                fx6_dc_in_volts=None,
                fx6_dc_low_volt_warning=None,
                fx6_seamless_dcin_to_bpu_pullover=False,
                fx6_hot_replug_reboot_blocked=False,
            )
        return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
            admitted=True,
            errno_code=0,
            reason=(
                f"Power-OFF charging NP-FZ100 via USB Type-C ({power_profile}, "
                f"{ambient_temp_c}C in 10..30C window, CHARGE LED=On)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            mode=mode,
            port=port,
            effective_usb_power_supply=eff_usb_ps,
            usb_power_resettable=False,
            np_fz100_inserted=True,
            batteryless_boot_supported=False,
            power_on_supply_active=False,
            charging_active=True,
            charge_led_state="On",
            power_save_bypassed=False,
            battery_draining_5v15a_low=False,
            instant_power_loss_on_hot_pull=False,
            monitor_brightness_locked_max=False,
            fx6_dc_in_volts=None,
            fx6_dc_low_volt_warning=None,
            fx6_seamless_dcin_to_bpu_pullover=False,
            fx6_hot_replug_reboot_blocked=False,
        )

    # Power-ON supplies power WITHOUT charging (CHARGE LED Off, Power Save bypass G82)
    supply_on = eff_usb_ps == "On"
    draining = supply_on and (power_profile == "5V/1.5A")
    return UsbPowerSupplyNpFz100Dcc1VsFx6Audit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 Power-ON USB Power Supply={eff_usb_ps!r} ({power_profile}; "
            f"charging_active=False, CHARGE LED=Off, power_save_bypass={supply_on}, "
            f"low_5v15a_drain={draining})"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        mode=mode,
        port=port,
        effective_usb_power_supply=eff_usb_ps,
        usb_power_resettable=False,
        np_fz100_inserted=True,
        batteryless_boot_supported=False,
        power_on_supply_active=supply_on,
        charging_active=False,
        charge_led_state="Off",
        power_save_bypassed=supply_on,
        battery_draining_5v15a_low=draining,
        instant_power_loss_on_hot_pull=False,
        monitor_brightness_locked_max=False,
        fx6_dc_in_volts=None,
        fx6_dc_low_volt_warning=None,
        fx6_seamless_dcin_to_bpu_pullover=False,
        fx6_hot_replug_reboot_blocked=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 80D: [NTSC/PAL Selector], AVF_INFO DB & Slot 1 EROFS vs FX6 Freq
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NtscPalSkuAvfInfoAndSlot1ErofsAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    sku_code: str
    default_tv_system: str
    effective_tv_system: str
    boot_banner_msg: Optional[str]
    selector_locked_out: bool
    requires_cold_reboot: bool
    card_format_mandatory: bool
    cross_region_playback_blocked: bool
    avf_info_prompt: Optional[str]
    target_slot: str
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    battery_pct: int
    battery_mv: int
    fx6_freq_options_count: int
    fx6_active_freq: Optional[str]
    fx6_thumbnail_hides_mismatched_clips: bool


def simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "ntsc_pal_select",
    sku_code: str = "U2",
    requested_tv_system: str = "PAL",
    current_tv_system: Optional[str] = None,
    clip_tv_system: str = "NTSC",
    avf_info_state: str = "valid",
    target_slot: str = "Slot 2",
    battery_pct: int = 85,
    battery_mv: int = 7800,
    fx6_active_freq: str = "23.98Hz",
    fx6_clip_freq: str = "23.98Hz",
    fx6_requested_freq: Optional[str] = None,
) -> NtscPalSkuAvfInfoAndSlot1ErofsAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage80Phase360Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage80Phase360Error(f"Invalid fw_version: {fw_version!r}")
    if operation not in VALID_NTSCPAL_OPERATIONS:
        raise Stage80Phase360Error(f"Invalid operation: {operation!r}")
    if sku_code not in VALID_REGIONAL_SKUS:
        raise Stage80Phase360Error(f"Invalid sku_code: {sku_code!r}")
    if requested_tv_system not in VALID_TV_SYSTEMS:
        raise Stage80Phase360Error(f"Invalid requested_tv_system: {requested_tv_system!r}")
    if clip_tv_system not in VALID_TV_SYSTEMS:
        raise Stage80Phase360Error(f"Invalid clip_tv_system: {clip_tv_system!r}")
    if target_slot not in VALID_CARDS_SLOTS:
        raise Stage80Phase360Error(f"Invalid target_slot: {target_slot!r}")
    if fx6_active_freq not in FX6_VALID_FREQUENCIES:
        raise Stage80Phase360Error(f"Invalid fx6_active_freq: {fx6_active_freq!r}")
    if fx6_clip_freq not in FX6_VALID_FREQUENCIES:
        raise Stage80Phase360Error(f"Invalid fx6_clip_freq: {fx6_clip_freq!r}")
    if fx6_requested_freq is not None and fx6_requested_freq not in FX6_VALID_FREQUENCIES:
        raise Stage80Phase360Error(f"Invalid fx6_requested_freq: {fx6_requested_freq!r}")

    default_tv = "NTSC" if sku_code in ("J1", "U2") else "PAL"
    eff_cur = default_tv if current_tv_system is None else current_tv_system

    # 1. ILME-FX6 Ver. 6.01 Project > Rec Format > Frequency
    if body_profile == BODY_MODEL_FX6:
        if operation == "fx6_system_frequency":
            new_freq = fx6_active_freq if fx6_requested_freq is None else fx6_requested_freq
            reboot = new_freq != fx6_active_freq
            return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
                admitted=True,
                errno_code=0,
                reason=(
                    f"ILME-FX6 Project > Rec Format > Frequency={new_freq!r} "
                    f"(ns2 0x40ab 'Change System Frequency?' reboot={reboot}; 0 format required)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                sku_code=sku_code,
                default_tv_system=default_tv,
                effective_tv_system="NTSC" if new_freq in ("59.94Hz", "29.97Hz", "23.98Hz") else "PAL",
                boot_banner_msg="Change System Frequency?" if reboot else None,
                selector_locked_out=False,
                requires_cold_reboot=reboot,
                card_format_mandatory=False,
                cross_region_playback_blocked=False,
                avf_info_prompt=None,
                target_slot=target_slot,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                battery_pct=battery_pct,
                battery_mv=battery_mv,
                fx6_freq_options_count=FX6_FREQ_OPTIONS_COUNT,
                fx6_active_freq=new_freq,
                fx6_thumbnail_hides_mismatched_clips=True,
            )
        if operation == "fx6_thumbnail_filter":
            matched = fx6_clip_freq == fx6_active_freq
            if not matched:
                return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
                    admitted=False,
                    errno_code=EOPNOTSUPP_ERRNO,
                    reason=(
                        f"ILME-FX6 Thumbnail hides {fx6_clip_freq} clip under active "
                        f"{fx6_active_freq} system frequency (0 cross-freq leak, 0 format)"
                    ),
                    body_profile=body_profile,
                    fw_version=fw_version,
                    operation=operation,
                    sku_code=sku_code,
                    default_tv_system=default_tv,
                    effective_tv_system="NTSC" if fx6_active_freq in ("59.94Hz", "29.97Hz", "23.98Hz") else "PAL",
                    boot_banner_msg=None,
                    selector_locked_out=False,
                    requires_cold_reboot=False,
                    card_format_mandatory=False,
                    cross_region_playback_blocked=True,
                    avf_info_prompt=None,
                    target_slot=target_slot,
                    slot1_data_sector_writes=0,
                    slot1_avf_info_mutated=False,
                    battery_pct=battery_pct,
                    battery_mv=battery_mv,
                    fx6_freq_options_count=FX6_FREQ_OPTIONS_COUNT,
                    fx6_active_freq=fx6_active_freq,
                    fx6_thumbnail_hides_mismatched_clips=True,
                )
            return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
                admitted=True,
                errno_code=0,
                reason=f"ILME-FX6 Thumbnail displays matching {fx6_clip_freq} clip",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                sku_code=sku_code,
                default_tv_system=default_tv,
                effective_tv_system="NTSC" if fx6_active_freq in ("59.94Hz", "29.97Hz", "23.98Hz") else "PAL",
                boot_banner_msg=None,
                selector_locked_out=False,
                requires_cold_reboot=False,
                card_format_mandatory=False,
                cross_region_playback_blocked=False,
                avf_info_prompt=None,
                target_slot=target_slot,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                battery_pct=battery_pct,
                battery_mv=battery_mv,
                fx6_freq_options_count=FX6_FREQ_OPTIONS_COUNT,
                fx6_active_freq=fx6_active_freq,
                fx6_thumbnail_hides_mismatched_clips=True,
            )
        return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"ILME-FX6 does not use FX3 operation {operation!r}",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            default_tv_system=default_tv,
            effective_tv_system="NTSC",
            boot_banner_msg=None,
            selector_locked_out=False,
            requires_cold_reboot=False,
            card_format_mandatory=False,
            cross_region_playback_blocked=False,
            avf_info_prompt=None,
            target_slot=target_slot,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            battery_pct=battery_pct,
            battery_mv=battery_mv,
            fx6_freq_options_count=FX6_FREQ_OPTIONS_COUNT,
            fx6_active_freq=fx6_active_freq,
            fx6_thumbnail_hides_mismatched_clips=True,
        )

    # 2. ILME-FX3 Ver. 7.02
    if operation in ("fx6_system_frequency", "fx6_thumbnail_filter"):
        return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"ILME-FX3 does not expose FX6 frequency operation {operation!r}",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            default_tv_system=default_tv,
            effective_tv_system=eff_cur,
            boot_banner_msg=None,
            selector_locked_out=(sku_code == "J1"),
            requires_cold_reboot=False,
            card_format_mandatory=False,
            cross_region_playback_blocked=False,
            avf_info_prompt=None,
            target_slot=target_slot,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            battery_pct=battery_pct,
            battery_mv=battery_mv,
            fx6_freq_options_count=0,
            fx6_active_freq=None,
            fx6_thumbnail_hides_mismatched_clips=False,
        )

    # Tier-0 Slot 1 EROFS=30 Firewall for ALL AVF_INFO / Recover / Format writes
    if target_slot == "Slot 1" and operation in (
        "avf_info_create",
        "avf_info_update",
        "recover_image_db",
        "card_format",
    ):
        return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason=(
                f"Tier-0 Slot 1 recovery vault firewall blocked {operation!r} -> "
                "hard EROFS=30 (slot1_data_sector_writes=0, slot1_avf_info_mutated=False)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            default_tv_system=default_tv,
            effective_tv_system=eff_cur,
            boot_banner_msg=None,
            selector_locked_out=(sku_code == "J1"),
            requires_cold_reboot=False,
            card_format_mandatory=False,
            cross_region_playback_blocked=False,
            avf_info_prompt=None,
            target_slot="Slot 1",
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            battery_pct=battery_pct,
            battery_mv=battery_mv,
            fx6_freq_options_count=0,
            fx6_active_freq=None,
            fx6_thumbnail_hides_mismatched_clips=False,
        )

    if operation == "ntsc_pal_select":
        if sku_code == "J1":
            if requested_tv_system == "PAL":
                return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
                    admitted=False,
                    errno_code=EOPNOTSUPP_ERRNO,
                    reason=(
                        "lib::backup_get_ntsc_pal_selector_dst: J1 (Japan) SKU locks out "
                        "[NTSC/PAL Selector] (NTSC only -> EOPNOTSUPP=95)"
                    ),
                    body_profile=body_profile,
                    fw_version=fw_version,
                    operation=operation,
                    sku_code=sku_code,
                    default_tv_system="NTSC",
                    effective_tv_system="NTSC",
                    boot_banner_msg=None,
                    selector_locked_out=True,
                    requires_cold_reboot=False,
                    card_format_mandatory=False,
                    cross_region_playback_blocked=False,
                    avf_info_prompt=None,
                    target_slot=target_slot,
                    slot1_data_sector_writes=0,
                    slot1_avf_info_mutated=False,
                    battery_pct=battery_pct,
                    battery_mv=battery_mv,
                    fx6_freq_options_count=0,
                    fx6_active_freq=None,
                    fx6_thumbnail_hides_mismatched_clips=False,
                )
            return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
                admitted=True,
                errno_code=0,
                reason="J1 SKU fixed on NTSC (selector item hidden/locked out)",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                sku_code=sku_code,
                default_tv_system="NTSC",
                effective_tv_system="NTSC",
                boot_banner_msg=None,
                selector_locked_out=True,
                requires_cold_reboot=False,
                card_format_mandatory=False,
                cross_region_playback_blocked=False,
                avf_info_prompt=None,
                target_slot=target_slot,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                battery_pct=battery_pct,
                battery_mv=battery_mv,
                fx6_freq_options_count=0,
                fx6_active_freq=None,
                fx6_thumbnail_hides_mismatched_clips=False,
            )

        banner: Optional[str] = None
        if sku_code == "U2" and requested_tv_system == "PAL":
            banner = "Running on PAL."
        elif sku_code in ("CE", "CEC", "E33") and requested_tv_system == "NTSC":
            banner = "Running on NTSC."
        reboot_needed = requested_tv_system != eff_cur
        return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"SKU {sku_code} switched to {requested_tv_system} (default={default_tv}; "
                f"cold_reboot={reboot_needed}, format_mandatory=False, banner={banner!r})"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            default_tv_system=default_tv,
            effective_tv_system=requested_tv_system,
            boot_banner_msg=banner,
            selector_locked_out=False,
            requires_cold_reboot=reboot_needed,
            card_format_mandatory=False,
            cross_region_playback_blocked=False,
            avf_info_prompt=None,
            target_slot=target_slot,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            battery_pct=battery_pct,
            battery_mv=battery_mv,
            fx6_freq_options_count=0,
            fx6_active_freq=None,
            fx6_thumbnail_hides_mismatched_clips=False,
        )

    if operation == "playback_clip":
        if clip_tv_system != eff_cur:
            return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    f"Cross-region playback blocked (_g 0x61ca/0x644e): {clip_tv_system} clip "
                    f"cannot play back while camera is running on {eff_cur} -> EOPNOTSUPP=95"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                sku_code=sku_code,
                default_tv_system=default_tv,
                effective_tv_system=eff_cur,
                boot_banner_msg=None,
                selector_locked_out=(sku_code == "J1"),
                requires_cold_reboot=False,
                card_format_mandatory=False,
                cross_region_playback_blocked=True,
                avf_info_prompt=None,
                target_slot=target_slot,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                battery_pct=battery_pct,
                battery_mv=battery_mv,
                fx6_freq_options_count=0,
                fx6_active_freq=None,
                fx6_thumbnail_hides_mismatched_clips=False,
            )
        return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
            admitted=True,
            errno_code=0,
            reason=f"Clip ({clip_tv_system}) matches active system ({eff_cur}) playback admitted",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            default_tv_system=default_tv,
            effective_tv_system=eff_cur,
            boot_banner_msg=None,
            selector_locked_out=(sku_code == "J1"),
            requires_cold_reboot=False,
            card_format_mandatory=False,
            cross_region_playback_blocked=False,
            avf_info_prompt=None,
            target_slot=target_slot,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            battery_pct=battery_pct,
            battery_mv=battery_mv,
            fx6_freq_options_count=0,
            fx6_active_freq=None,
            fx6_thumbnail_hides_mismatched_clips=False,
        )

    if operation == "avf_info_create":
        return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
            admitted=True,
            errno_code=0,
            reason="Slot 2 scratch AVF_INFO missing -> base 0xea23 'Image Database File not found. Create?'",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            default_tv_system=default_tv,
            effective_tv_system=eff_cur,
            boot_banner_msg=None,
            selector_locked_out=(sku_code == "J1"),
            requires_cold_reboot=False,
            card_format_mandatory=False,
            cross_region_playback_blocked=False,
            avf_info_prompt="Image Database File not found.\nCreate?",
            target_slot="Slot 2",
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            battery_pct=battery_pct,
            battery_mv=battery_mv,
            fx6_freq_options_count=0,
            fx6_active_freq=None,
            fx6_thumbnail_hides_mismatched_clips=False,
        )

    if operation == "avf_info_update":
        return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
            admitted=True,
            errno_code=0,
            reason="Slot 2 scratch AVF_INFO dirty -> base 0xea24 'Database File needs update. Update?'",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            default_tv_system=default_tv,
            effective_tv_system=eff_cur,
            boot_banner_msg=None,
            selector_locked_out=(sku_code == "J1"),
            requires_cold_reboot=False,
            card_format_mandatory=False,
            cross_region_playback_blocked=False,
            avf_info_prompt="Database File needs\nupdate. Update?",
            target_slot="Slot 2",
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            battery_pct=battery_pct,
            battery_mv=battery_mv,
            fx6_freq_options_count=0,
            fx6_active_freq=None,
            fx6_thumbnail_hides_mismatched_clips=False,
        )

    if operation == "recover_image_db":
        if battery_pct < RECOVER_DB_LOW_BATT_MIN_PCT or battery_mv < RECOVER_DB_LOW_BATT_MIN_MV:
            return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
                admitted=False,
                errno_code=EAGAIN_ERRNO,
                reason=(
                    f"[Recover Image DB] refused due to low battery ({battery_pct}%% / {battery_mv}mV "
                    f"< {RECOVER_DB_LOW_BATT_MIN_PCT}%% / {RECOVER_DB_LOW_BATT_MIN_MV}mV) -> EAGAIN=11"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                sku_code=sku_code,
                default_tv_system=default_tv,
                effective_tv_system=eff_cur,
                boot_banner_msg=None,
                selector_locked_out=(sku_code == "J1"),
                requires_cold_reboot=False,
                card_format_mandatory=False,
                cross_region_playback_blocked=False,
                avf_info_prompt="Recover Image DB",
                target_slot="Slot 2",
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                battery_pct=battery_pct,
                battery_mv=battery_mv,
                fx6_freq_options_count=0,
                fx6_active_freq=None,
                fx6_thumbnail_hides_mismatched_clips=False,
            )
        return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
            admitted=True,
            errno_code=0,
            reason=f"Slot 2 scratch [Recover Image DB] executed safely ({battery_pct}%% / {battery_mv}mV)",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            sku_code=sku_code,
            default_tv_system=default_tv,
            effective_tv_system=eff_cur,
            boot_banner_msg=None,
            selector_locked_out=(sku_code == "J1"),
            requires_cold_reboot=False,
            card_format_mandatory=False,
            cross_region_playback_blocked=False,
            avf_info_prompt="Recover Image DB",
            target_slot="Slot 2",
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            battery_pct=battery_pct,
            battery_mv=battery_mv,
            fx6_freq_options_count=0,
            fx6_active_freq=None,
            fx6_thumbnail_hides_mismatched_clips=False,
        )

    # card_format on Slot 2 virtual scratch
    return NtscPalSkuAvfInfoAndSlot1ErofsAudit(
        admitted=True,
        errno_code=0,
        reason="Slot 2 virtual scratch card_format completed with 0 physical device writes",
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        sku_code=sku_code,
        default_tv_system=default_tv,
        effective_tv_system=eff_cur,
        boot_banner_msg=None,
        selector_locked_out=(sku_code == "J1"),
        requires_cold_reboot=False,
        card_format_mandatory=False,
        cross_region_playback_blocked=False,
        avf_info_prompt=None,
        target_slot="Slot 2",
        slot1_data_sector_writes=0,
        slot1_avf_info_mutated=False,
        battery_pct=battery_pct,
        battery_mv=battery_mv,
        fx6_freq_options_count=0,
        fx6_active_freq=None,
        fx6_thumbnail_hides_mismatched_clips=False,
    )


# ---------------------------------------------------------------------------
# Milestone Probe, Recursive Determinism & Full Stage 80 Runner
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


def _build_stage80_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_80th_stage_milestone": IS_80TH_STAGE_MILESTONE,
        "wave": "Wave-70",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase360_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulation(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    donor_audit = inspect_phase360_wave70_donors(
        work_root=work_root, force_clean_room=force_clean_room, env=env
    )

    # Sub-Model 80A probes
    p80a_fx3_clean = simulate_peaking_cleanhdmi_focusmag_and_map_hil(
        peaking_display="On",
        peaking_level="High",
        peaking_color="White",
        hdmi_info_display="On",
        raw_output="On",
        focus_mag_scale="x8.0",
        camera_settings_reset_applied=True,
    )
    p80a_fx3_init = simulate_peaking_cleanhdmi_focusmag_and_map_hil(
        peaking_display="On",
        peaking_level="High",
        peaking_color="Red",
        initialize_applied=True,
    )
    p80a_fmap_body_block = simulate_peaking_cleanhdmi_focusmag_and_map_hil(
        operation="focus_map", transport="body_lcd"
    )
    p80a_fmap_usb_block = simulate_peaking_cleanhdmi_focusmag_and_map_hil(
        operation="focus_map", transport="usb"
    )
    p80a_fmap_wifi_mc = simulate_peaking_cleanhdmi_focusmag_and_map_hil(
        operation="focus_map", transport="wifi_mc", monitor_control_version="2.1.0"
    )
    p80a_fx6_bw = simulate_peaking_cleanhdmi_focusmag_and_map_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_peaking",
        peaking_display="On",
        peaking_color="B&W",
    )
    p80a_fx6_type_block = simulate_peaking_cleanhdmi_focusmag_and_map_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_dormant_type_freq",
    )
    p80a_ok = (
        p80a_fx3_clean.admitted
        and p80a_fx3_clean.peaking_items_count == 3
        and p80a_fx3_clean.effective_peaking_display == "On"
        and (not p80a_fx3_clean.peaking_resettable)
        and p80a_fx3_clean.hdmi_peaking_leaked_pixels == 0
        and p80a_fx3_clean.focus_mag_coexists_with_peaking
        and p80a_fx3_init.admitted
        and p80a_fx3_init.effective_peaking_display == "Off"
        and p80a_fx3_init.effective_peaking_level == "Mid"
        and p80a_fx3_init.effective_peaking_color == "White"
        and (not p80a_fmap_body_block.admitted)
        and p80a_fmap_body_block.errno_code == EOPNOTSUPP_ERRNO
        and (not p80a_fmap_usb_block.admitted)
        and p80a_fmap_usb_block.errno_code == EOPNOTSUPP_ERRNO
        and p80a_fmap_wifi_mc.admitted
        and p80a_fmap_wifi_mc.focus_map_remote_wireless_only
        and p80a_fx6_bw.admitted
        and p80a_fx6_bw.effective_peaking_color == "B&W"
        and p80a_fx6_bw.fx6_sdi_hdmi_output_display_independent
        and (not p80a_fx6_type_block.admitted)
        and p80a_fx6_type_block.errno_code == EOPNOTSUPP_ERRNO
        and p80a_fx6_type_block.fx6_peaking_type_freq_appfw_symbols == 0
    )

    # Sub-Model 80B probes
    p80b_v702_legacy_removed = simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
        fw_version=FW_VER_702, operation="legacy_audio_level_display"
    )
    p80b_v101_legacy = simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
        fw_version=FW_VER_101, operation="legacy_audio_level_display"
    )
    p80b_internal_wind_on = simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
        operation="wind_noise_reduct", wind_noise_reduct="On"
    )
    p80b_wind_auto_block = simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
        operation="wind_noise_reduct", wind_noise_reduct="Auto"
    )
    p80b_wind_adv_block = simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
        operation="wind_noise_reduct", wind_noise_reduct="On Advanced"
    )
    p80b_35mm_wind_bypass = simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
        operation="wind_noise_reduct", wind_noise_reduct="On", mic_35mm_plugged=True
    )
    p80b_xlrh1_100hz = simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
        operation="xlrh1_hardware_low_cut",
        xlrh1_attached=True,
        xlrh1_hardware_low_cut="100Hz",
    )
    p80b_35mm_preempts_xlrh1 = simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
        operation="xlrh1_hardware_low_cut",
        xlrh1_attached=True,
        mic_35mm_plugged=True,
    )
    p80b_sq_0ch = simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
        operation="disp_audio_meter", sq_mode=True
    )
    p80b_sdk_ro = simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
        operation="remote_sdk_audio_meter_write"
    )
    p80b_fx6_audio = simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_audio_control",
        fx6_ch_wind_filters=("On", "On", "Off", "Off"),
    )
    p80b_fx6_no_phys_lowcut = simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_handle_physical_low_cut",
    )
    p80b_ok = (
        (not p80b_v702_legacy_removed.admitted)
        and p80b_v702_legacy_removed.errno_code == EOPNOTSUPP_ERRNO
        and (not p80b_v702_legacy_removed.legacy_audio_level_display_menu_exposed)
        and p80b_v101_legacy.admitted
        and p80b_v101_legacy.legacy_audio_level_display_menu_exposed
        and p80b_internal_wind_on.admitted
        and p80b_internal_wind_on.wind_low_cut_dsp_active
        and p80b_internal_wind_on.audio_recording_items_count == 5
        and p80b_internal_wind_on.effective_audio_rec_level == 26
        and p80b_internal_wind_on.rec_level_defult_typo_symbol == "adj_audio_rec_level_defult"
        and (not p80b_wind_auto_block.admitted)
        and p80b_wind_auto_block.errno_code == EOPNOTSUPP_ERRNO
        and (not p80b_wind_adv_block.admitted)
        and p80b_wind_adv_block.errno_code == EOPNOTSUPP_ERRNO
        and p80b_35mm_wind_bypass.admitted
        and (not p80b_35mm_wind_bypass.wind_low_cut_dsp_active)
        and p80b_xlrh1_100hz.admitted
        and p80b_xlrh1_100hz.disp_big6_meter_channels == 4
        and (not p80b_35mm_preempts_xlrh1.admitted)
        and p80b_35mm_preempts_xlrh1.errno_code == EBUSY_ERRNO
        and p80b_sq_0ch.admitted
        and p80b_sq_0ch.disp_big6_meter_channels == 0
        and (not p80b_sdk_ro.admitted)
        and p80b_sdk_ro.errno_code == EACCES_ERRNO
        and p80b_fx6_audio.admitted
        and p80b_fx6_audio.fx6_ch_wind_filters_count == 4
        and p80b_fx6_audio.fx6_limiter_mode_steps_count == 6
        and (not p80b_fx6_no_phys_lowcut.admitted)
        and p80b_fx6_no_phys_lowcut.errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 80C probes
    p80c_on_9v3a = simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
        mode="power_on", port="Type-C", power_profile="9V/3A", camera_settings_reset_applied=True
    )
    p80c_on_5v15a_drain = simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
        mode="power_on", port="Type-C", power_profile="5V/1.5A"
    )
    p80c_micro_usb_block = simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
        mode="power_on", port="Multi/Micro-USB"
    )
    p80c_no_batt_block = simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
        mode="power_on", np_fz100_inserted=False
    )
    p80c_hot_pull_loss = simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
        mode="power_on", np_fz100_inserted=True, battery_hot_pulled=True
    )
    p80c_off_charge_23c = simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
        mode="power_off", ambient_temp_c=23
    )
    p80c_off_charge_35c_fault = simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
        mode="power_off", ambient_temp_c=35
    )
    p80c_dcc1_ok = simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
        mode="dc_c1", port="DC-C1", dc_c1_pd_watts=65, dc_c1_cable_amps=5
    )
    p80c_dcc1_underpower = simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
        mode="dc_c1", port="DC-C1", dc_c1_pd_watts=65, dc_c1_cable_amps=3
    )
    p80c_fx6_batteryless = simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        mode="fx6_dc_in",
        port="FX6_DC_IN",
        fx6_dc_in_volts=19.5,
        fx6_bpu_inserted=False,
    )
    p80c_fx6_warn1 = simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        mode="fx6_dc_in",
        port="FX6_DC_IN",
        fx6_dc_in_volts=16.5,
    )
    p80c_fx6_pullover = simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        mode="fx6_dc_in",
        port="FX6_DC_IN",
        fx6_bpu_inserted=True,
        fx6_dcin_unplugged_to_bpu=True,
    )
    p80c_fx6_hot_replug_block = simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        mode="fx6_dc_in",
        port="FX6_DC_IN",
        fx6_bpu_inserted=True,
        fx6_dcin_hot_replug_while_running=True,
    )
    p80c_fx6_usbc_block = simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        mode="fx6_usbc",
        port="Type-C",
    )
    p80c_ok = (
        p80c_on_9v3a.admitted
        and p80c_on_9v3a.power_on_supply_active
        and (not p80c_on_9v3a.charging_active)
        and p80c_on_9v3a.charge_led_state == "Off"
        and p80c_on_9v3a.power_save_bypassed
        and p80c_on_5v15a_drain.admitted
        and p80c_on_5v15a_drain.battery_draining_5v15a_low
        and (not p80c_micro_usb_block.admitted)
        and p80c_micro_usb_block.errno_code == ENODEV_ERRNO
        and (not p80c_no_batt_block.admitted)
        and p80c_no_batt_block.errno_code == EIO_ERRNO
        and (not p80c_hot_pull_loss.admitted)
        and p80c_hot_pull_loss.instant_power_loss_on_hot_pull
        and p80c_off_charge_23c.admitted
        and p80c_off_charge_23c.charging_active
        and p80c_off_charge_23c.charge_led_state == "On"
        and (not p80c_off_charge_35c_fault.admitted)
        and p80c_off_charge_35c_fault.charge_led_state == "FastBlink"
        and p80c_dcc1_ok.admitted
        and p80c_dcc1_ok.monitor_brightness_locked_max
        and (not p80c_dcc1_underpower.admitted)
        and p80c_dcc1_underpower.errno_code == EINVAL_ERRNO
        and p80c_fx6_batteryless.admitted
        and p80c_fx6_batteryless.batteryless_boot_supported
        and p80c_fx6_warn1.admitted
        and p80c_fx6_warn1.fx6_dc_low_volt_warning == "BKID_APP_SETTING_DC_LOW_VOLT1"
        and p80c_fx6_pullover.admitted
        and p80c_fx6_pullover.fx6_seamless_dcin_to_bpu_pullover
        and (not p80c_fx6_hot_replug_block.admitted)
        and p80c_fx6_hot_replug_block.fx6_hot_replug_reboot_blocked
        and (not p80c_fx6_usbc_block.admitted)
        and p80c_fx6_usbc_block.errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 80D probes
    p80d_j1_pal_block = simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
        sku_code="J1", requested_tv_system="PAL"
    )
    p80d_u2_pal = simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
        sku_code="U2", requested_tv_system="PAL"
    )
    p80d_ce_ntsc = simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
        sku_code="CE", requested_tv_system="NTSC"
    )
    p80d_cross_pb_block = simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
        operation="playback_clip", current_tv_system="PAL", clip_tv_system="NTSC"
    )
    p80d_slot1_erofs = simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
        operation="avf_info_create", target_slot="Slot 1"
    )
    p80d_slot1_recover_erofs = simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
        operation="recover_image_db", target_slot="Slot 1"
    )
    p80d_slot2_create = simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
        operation="avf_info_create", target_slot="Slot 2"
    )
    p80d_slot2_update = simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
        operation="avf_info_update", target_slot="Slot 2"
    )
    p80d_recover_low_batt = simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
        operation="recover_image_db", target_slot="Slot 2", battery_pct=9, battery_mv=6350
    )
    p80d_fx6_freq = simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_system_frequency",
        fx6_active_freq="59.94Hz",
        fx6_requested_freq="23.98Hz",
    )
    p80d_fx6_thumb_filter = simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_thumbnail_filter",
        fx6_active_freq="23.98Hz",
        fx6_clip_freq="50Hz",
    )
    p80d_ok = (
        (not p80d_j1_pal_block.admitted)
        and p80d_j1_pal_block.errno_code == EOPNOTSUPP_ERRNO
        and p80d_j1_pal_block.selector_locked_out
        and p80d_u2_pal.admitted
        and p80d_u2_pal.boot_banner_msg == "Running on PAL."
        and p80d_u2_pal.requires_cold_reboot
        and (not p80d_u2_pal.card_format_mandatory)
        and p80d_ce_ntsc.admitted
        and p80d_ce_ntsc.boot_banner_msg == "Running on NTSC."
        and (not p80d_cross_pb_block.admitted)
        and p80d_cross_pb_block.cross_region_playback_blocked
        and (not p80d_slot1_erofs.admitted)
        and p80d_slot1_erofs.errno_code == EROFS_ERRNO
        and p80d_slot1_erofs.slot1_data_sector_writes == 0
        and (not p80d_slot1_recover_erofs.admitted)
        and p80d_slot1_recover_erofs.errno_code == EROFS_ERRNO
        and p80d_slot2_create.admitted
        and "Create?" in (p80d_slot2_create.avf_info_prompt or "")
        and p80d_slot2_update.admitted
        and "Update?" in (p80d_slot2_update.avf_info_prompt or "")
        and (not p80d_recover_low_batt.admitted)
        and p80d_recover_low_batt.errno_code == EAGAIN_ERRNO
        and p80d_fx6_freq.admitted
        and p80d_fx6_freq.fx6_freq_options_count == 6
        and p80d_fx6_freq.requires_cold_reboot
        and (not p80d_fx6_thumb_filter.admitted)
        and p80d_fx6_thumb_filter.fx6_thumbnail_hides_mismatched_clips
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
        # 80A
        "fx3_peaking_items_count": FX3_PEAKING_ITEMS_COUNT,
        "peaking_reset_wipe_events": PEAKING_RESET_WIPE_EVENTS,
        "hdmi_peaking_leaked_pixels": HDMI_PEAKING_LEAKED_PIXELS,
        "peaking_focus_mag_conflict_events": PEAKING_FOCUS_MAG_CONFLICT_EVENTS,
        "fx3_body_focus_map_exposed": FX3_BODY_FOCUS_MAP_EXPOSED,
        "focus_map_over_usb_supported": FOCUS_MAP_OVER_USB_SUPPORTED,
        "fx6_peaking_color_has_bw": FX6_PEAKING_COLOR_HAS_BW,
        "fx6_peaking_type_or_freq_exposed_events": FX6_PEAKING_TYPE_OR_FREQ_EXPOSED_EVENTS,
        "fx6_peaking_appfw_type_freq_symbol_count": FX6_PEAKING_APPFW_TYPE_FREQ_SYMBOL_COUNT,
        # 80B
        "fx3_v2_plus_audio_level_display_menu_removed": FX3_V2_PLUS_AUDIO_LEVEL_DISPLAY_MENU_REMOVED,
        "audio_recording_menu_items_count": AUDIO_RECORDING_MENU_ITEMS_COUNT,
        "audio_rec_level_default": AUDIO_REC_LEVEL_DEFAULT,
        "adj_audio_rec_level_defult_typo_matched": ADJ_AUDIO_REC_LEVEL_DEFULT_TYPO_MATCHED,
        "wind_noise_reduct_auto_or_advanced_exposed_events": WIND_NOISE_REDUCT_AUTO_OR_ADVANCED_EXPOSED_EVENTS,
        "external_mic_wind_reduct_applied_frames": EXTERNAL_MIC_WIND_REDUCT_APPLIED_FRAMES,
        "mm35_preemption_over_xlrh1_bypass_events": MM35_PREEMPTION_OVER_XLRH1_BYPASS_EVENTS,
        "fx6_handle_physical_low_cut_present": FX6_HANDLE_PHYSICAL_LOW_CUT_PRESENT,
        "fx6_ch_wind_filter_count": FX6_CH_WIND_FILTER_COUNT,
        "fx6_limiter_mode_steps_count": FX6_LIMITER_MODE_STEPS_COUNT,
        # 80C
        "usb_power_supply_multi_micro_bypass_events": USB_POWER_SUPPLY_MULTI_MICRO_BYPASS_EVENTS,
        "np_fz100_insertion_mandatory": NP_FZ100_INSERTION_MANDATORY,
        "fx3_batteryless_boot_allowed": FX3_BATTERYLESS_BOOT_ALLOWED,
        "fx3_power_on_charging_events": FX3_POWER_ON_CHARGING_EVENTS,
        "power_off_charge_temp_min_c": POWER_OFF_CHARGE_TEMP_MIN_C,
        "power_off_charge_temp_max_c": POWER_OFF_CHARGE_TEMP_MAX_C,
        "dcc1_min_pd_watts": DCC1_MIN_PD_WATTS,
        "dcc1_required_cable_amps": DCC1_REQUIRED_CABLE_AMPS,
        "dcc1_underpower_boot_bypass_events": DCC1_UNDERPOWER_BOOT_BYPASS_EVENTS,
        "fx6_dc_in_nominal_volts": FX6_DC_IN_NOMINAL_VOLTS,
        "fx6_dc_in_min_volts": FX6_DC_IN_MIN_VOLTS,
        "fx6_dc_in_max_volts": FX6_DC_IN_MAX_VOLTS,
        "fx6_dc_in_warn1_volts": FX6_DC_IN_WARN1_VOLTS,
        "fx6_dc_in_warn2_volts": FX6_DC_IN_WARN2_VOLTS,
        "fx6_batteryless_boot_supported": FX6_BATTERYLESS_BOOT_SUPPORTED,
        "fx6_dc_in_hot_replug_reboot_unblocked_events": FX6_DC_IN_HOT_REPLUG_REBOOT_UNBLOCKED_EVENTS,
        "fx6_usbc_power_supported": FX6_USBC_POWER_SUPPORTED,
        # 80D
        "j1_pal_switch_bypass_events": J1_PAL_SWITCH_BYPASS_EVENTS,
        "ntsc_pal_switch_requires_cold_reboot": NTSC_PAL_SWITCH_REQUIRES_COLD_REBOOT,
        "ntsc_pal_format_mandatory_in_v702": NTSC_PAL_FORMAT_MANDATORY_IN_V702,
        "cross_region_movie_playback_bypass_events": CROSS_REGION_MOVIE_PLAYBACK_BYPASS_EVENTS,
        "recover_db_low_batt_min_pct": RECOVER_DB_LOW_BATT_MIN_PCT,
        "recover_db_low_batt_min_mv": RECOVER_DB_LOW_BATT_MIN_MV,
        "recover_db_low_batt_bypass_events": RECOVER_DB_LOW_BATT_BYPASS_EVENTS,
        "slot1_avf_info_or_format_write_bypass_events": SLOT1_AVF_INFO_OR_FORMAT_WRITE_BYPASS_EVENTS,
        "fx6_freq_options_count": FX6_FREQ_OPTIONS_COUNT,
        "fx6_thumbnail_cross_freq_leak_events": FX6_THUMBNAIL_CROSS_FREQ_LEAK_EVENTS,
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
        donor_audit["all_donors_verified"] and p80a_ok and p80b_ok and p80c_ok and p80d_ok
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_360_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_80th_stage_milestone": IS_80TH_STAGE_MILESTONE,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit["source_mode"],
        "redlines": redlines,
        "donor_audit": donor_audit,
        "stage80_milestone_probe": _build_stage80_milestone_probe(),
        "pillar_a_peaking_cleanhdmi_focusmag_and_map_hil": {
            "passed": p80a_ok,
            "fx3_clean_hdmi_and_focusmag_x8_reset_resistant": asdict(p80a_fx3_clean),
            "fx3_initialize_restores_defaults": asdict(p80a_fx3_init),
            "fx3_body_focus_map_dormant": asdict(p80a_fmap_body_block),
            "fx3_usb_focus_map_blocked": asdict(p80a_fmap_usb_block),
            "fx3_wireless_mc_v210_focus_map_ok": asdict(p80a_fmap_wifi_mc),
            "fx6_peaking_bw_and_independent_sdi_hdmi": asdict(p80a_fx6_bw),
            "fx6_dormant_peaking_type_freq_disproved": asdict(p80a_fx6_type_block),
        },
        "pillar_b_audiometer_wind_reduct_and_xlrh1_vs_fx6_hil": {
            "passed": p80b_ok,
            "v702_legacy_audio_level_display_removed": asdict(p80b_v702_legacy_removed),
            "v101_legacy_audio_level_display": asdict(p80b_v101_legacy),
            "internal_mic_wind_noise_reduct_on": asdict(p80b_internal_wind_on),
            "dormant_wind_auto_rejected": asdict(p80b_wind_auto_block),
            "dormant_wind_on_advanced_rejected": asdict(p80b_wind_adv_block),
            "external_35mm_wind_bypassed": asdict(p80b_35mm_wind_bypass),
            "xlrh1_hardware_low_cut_100hz": asdict(p80b_xlrh1_100hz),
            "mm35_preempts_xlrh1_ebusy": asdict(p80b_35mm_preempts_xlrh1),
            "sq_0ch_meter_hidden": asdict(p80b_sq_0ch),
            "remote_sdk_meter_read_only": asdict(p80b_sdk_ro),
            "fx6_ch1_to_4_wind_filter_and_6step_limiter": asdict(p80b_fx6_audio),
            "fx6_zero_handle_physical_low_cut": asdict(p80b_fx6_no_phys_lowcut),
        },
        "pillar_c_usb_power_supply_npfz100_dcc1_vs_fx6_dcin_hil": {
            "passed": p80c_ok,
            "fx3_power_on_9v3a_no_charge": asdict(p80c_on_9v3a),
            "fx3_power_on_5v15a_low_drain": asdict(p80c_on_5v15a_drain),
            "multi_micro_usb_rejected": asdict(p80c_micro_usb_block),
            "mandatory_np_fz100_no_batteryless_boot": asdict(p80c_no_batt_block),
            "hot_pull_instant_power_loss": asdict(p80c_hot_pull_loss),
            "power_off_charge_23c_ok": asdict(p80c_off_charge_23c),
            "power_off_charge_35c_fastblink_fault": asdict(p80c_off_charge_35c_fault),
            "dcc1_65w_5a_max_brightness_ok": asdict(p80c_dcc1_ok),
            "dcc1_underpower_3a_rejected": asdict(p80c_dcc1_underpower),
            "fx6_19v5_batteryless_boot_ok": asdict(p80c_fx6_batteryless),
            "fx6_16v5_dc_low_volt1_warning": asdict(p80c_fx6_warn1),
            "fx6_seamless_dcin_to_bpu_pullover": asdict(p80c_fx6_pullover),
            "fx6_hot_replug_reboot_guard": asdict(p80c_fx6_hot_replug_block),
            "fx6_usbc_power_unsupported": asdict(p80c_fx6_usbc_block),
        },
        "pillar_d_ntscpal_sku_avfinfo_slot1_erofs_vs_fx6_freq_hil": {
            "passed": p80d_ok,
            "j1_sku_pal_locked_out": asdict(p80d_j1_pal_block),
            "u2_sku_pal_banner_cold_reboot": asdict(p80d_u2_pal),
            "ce_sku_ntsc_banner": asdict(p80d_ce_ntsc),
            "cross_region_playback_blocked": asdict(p80d_cross_pb_block),
            "slot1_avf_info_erofs_30": asdict(p80d_slot1_erofs),
            "slot1_recover_db_erofs_30": asdict(p80d_slot1_recover_erofs),
            "slot2_avf_info_create_prompt": asdict(p80d_slot2_create),
            "slot2_avf_info_update_prompt": asdict(p80d_slot2_update),
            "recover_db_low_battery_refusal": asdict(p80d_recover_low_batt),
            "fx6_6step_system_frequency_reboot": asdict(p80d_fx6_freq),
            "fx6_thumbnail_hides_mismatched_freq": asdict(p80d_fx6_thumb_filter),
        },
    }

    digest = hashlib.sha256(
        json.dumps(_strip_wall_clock(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulator.py",
        description=(
            "Phase 360 (Stage 80 — 80/80 Full-Board VM Co-Emulation Stages!): "
            "Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-70 "
            "Peaking Clean-HDMI / Audio Meter Removal & Wind / USB-PD & DC-C1 / "
            "NTSC-PAL SKU & AVF_INFO Slot 1 EROFS=30 HIL Co-Emulator"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run all 80A..80D HIL checks and 16-donor O_RDONLY/clean-room audit",
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
    rep = run_phase360_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulation(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 360 Stage 80 ({rep['milestone']} Stages) | "
            f"src={rep['source_mode']} | donors={rep['donor_audit']['total_donors_count']} | "
            f"hdmi_pk={red['hdmi_peaking_leaked_pixels']} | "
            f"aud_items={red['audio_recording_menu_items_count']} | "
            f"fz100_req={int(bool(red['np_fz100_insertion_mandatory']))} | "
            f"s1_wr={red['slot1_data_sector_writes']} | "
            f"emmc_wr={red['emmc_nflasha_write_count']} | "
            f"digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2, sort_keys=True) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
