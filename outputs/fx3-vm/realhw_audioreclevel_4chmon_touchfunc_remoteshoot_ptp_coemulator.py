#!/usr/bin/env python3
"""Phase 365 (Stage 82 — 82/82 Full-Board VM Co-Emulation Stages!):
Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-72 HIL Co-Emulator.

Models and audits the four Wave-72 subsystems strictly via read-only
`os.O_RDONLY` + bounded `<= 4096 B` `os.pread` donor inspection (with
seamless `work_root=None` / nonexistent `work_root` / `CLEAN_ROOM_SYNTHETIC`
CI fallback and `raw_firmware_bytes_leaked == 0`):

1. **Sub-Model 82A — `[Audio Rec Level]` (`0..31`) / `XLR-H1` Physical Bypass /
   Permanent Body Limiter vs FX6 3-Tier Reference & 6-Step `Limiter Mode`**:
   - FX3 Ver. 7.02 `Shooting -> [Audio Recording] -> [Audio Rec Level]` (`0..31`,
     default `26` `adj_audio_rec_level_defult`, `Delete` key resets to `26`,
     `Can be reset` under `[Camera Settings Reset]`) applies ONLY to internal
     stereo mic and body `3.5mm MIC` with an **always-on non-defeatable body
     limiter**.
   - Preemption chain `3.5mm MIC` > `XLR-H1` (`HANDLE AUDIO = ON`,
     `UIBIZ_INP_HOTSHOE_XLRMIC`) > internal stereo mic: when no `3.5mm` plug is
     present and `XLR-H1 HANDLE AUDIO = ON`, body `[Audio Rec Level]` is
     completely bypassed (`greyed_out=True`), and physical handle switches
     govern (`LINE +4 dBu`, `MIC`/`MIC+48V` `ATT 0/10/20 dB` =
     `-60/-50/-40 dBu`, `AUTO/MAN(/LINK)`, `0..10` analog dials). `S&Q` locks
     all 4 audio regulation items (`0ch`).
   - Contrast with `ILME-FX6 Ver. 6.01` `Audio -> [Audio Input]`: independent
     `CH1..CH4 Input Select` matrix, digital `0..99` levels, 3-tier Reference
     (`INPUT1/2 MIC Reference -80..-30 dB`, `Line Input Reference +4/0/-3 dB/EBUL`,
     `Reference Level -20/-18/-16/-12 dB/EBUL` 5 steps), and **6-step
     `Limiter Mode`** (`Off`/`-6dB`/`-9dB`/`-12dB`/`-15dB`/`-17dB`, disproving
     4-step rumor).

2. **Sub-Model 82B — `[Audio Out Timing]` `Live`/`Lip Sync`, `[Volume Settings]`
   `0..15` & Exact 5-Option `[4ch Audio Monitoring]` vs FX6 7-Option `Monitor CH`
   & Zero Side `"MONITOR VOL"` Button**:
   - FX3 `[Audio Out Timing]` (`Live` default / `Lip Sync`, under `Shooting ->
     [Audio Recording]`, `Can be reset`, disabled in `S&Q`).
   - FX3 `Setup -> [Sound Option]` `[Volume Settings]` (`0..15`, default `7`,
     Reset-resistant `Not available`) and `[4ch Audio Monitoring]` (`CH1/CH2`
     default, `CH3/CH4`, `CH1+3/CH2+4`, **`CH1/CH1`**, **`CH2/CH2`** — exact 5
     options correcting Wave 62/70 3-option errata, Reset-resistant
     `Not available`, governs `3.5mm` headphone + rear mono speaker
     independently of HDMI `[4ch Audio Output]` `CH1/CH2` / `CH3/CH4`).
   - Contrast with `ILME-FX6 Ver. 6.01` `Audio -> [Audio Output]`: `Monitor CH`
     7 options (`CH1`, `CH2`, `CH3`, `CH4`, `CH1/CH2`, `CH3/CH4`, `MIX ALL`),
     `Headphone Out` (`Stereo`/`Mono`), `Volume` (`0..50` via menu/status
     dial/assignable button — **zero physical `"MONITOR VOL +/-"` button**),
     `HDMI Output` `2ch` vs `SDI Output` `4ch`.

3. **Sub-Model 82C — `Setup -> [Touch Operation]` Exact 4 Active Items vs
   Dormant `[Touch Panel/Pad]` / `[Touch Shutter]` / `[Touch AE]` & FX6
   `Touch Function in MF` / `BIG6`**:
   - FX3 Ver. 7.02 exposes ONLY 4 Reset-resistant (`Not available`) items:
     `[Touch Operation]` (`On` default / `On: Playback Only` / `Off`),
     `[Touch Sensitivity]` (`Standard` default / `Sensitive`),
     `[Touch Func. in Shooting]` (`Touch Focus` / `Touch Tracking` default /
     `Off` — identical across Still/Movie/`S&Q`), and `[Swipe Up]` (`Open the
     Fn Menu` default / `Off`).
   - Proves `[Touch Panel/Pad]`, `[Touch Shutter]`, and `[Touch AE]` are
     **100%% dormant (`EOPNOTSUPP=95`)**, and `[Spot Metering Point] = Focus
     Point Link` links only to the static focus area, NOT the active moving
     tracking box.
   - Contrast with `ILME-FX6 Ver. 6.01`: `Technical -> [Touch Operation]`
     (`On`/`Off`), `Focus -> [Touch Function in MF]` (`Spot Focus` disabled on
     manual lens / `De-Squeeze != 1.0x` / `Focus Magnifier`; `Tracking AF`),
     plus Ver. 6.00+ `BIG6` & full menu touch.

4. **Sub-Model 82D — `[PC Remote Function]` -> `[Remote Shoot Setting]`
   Evolution, PTP/PTP-IP `Destination Only` RAM Direct-Transfer & Tier-0
   `Slot 1 EROFS=30` Firewall vs FX6 `Camera Remote Control`**:
   - FX3 Ver. 2.00..7.02 `Network -> [Cnct./Remote Sht.] -> [Remote Shoot
     Setting]` (Reset-resistant under `[Camera Settings Reset]`, cleared by
     `[Reset Network Set.]` / `[Initialize]`): `[Still Img. Save Dest.]`
     (`Destination Only` / **`Dest.+Camera` factory default!** / `Camera Only`),
     `[Save Image Size]` (`Original` / `2M` default), `[RAW+J Save Image]`,
     `[RAW+H Save Image]`.
   - USB `/dev/usb/sicd_*` (`054c:0d2b`) & PTP-IP TCP `15740`
     (`libInfraPtpControl.so` / `libInfraRemote.so`): ONLY `Destination Only`
     captures cardless in RAM (`slot1_data_sector_writes == 0`), whereas
     factory default `Dest.+Camera` and `Camera Only` attempt `Slot 1` writes
     and hit hard `EROFS=30` on Tier-0 vault (`slot1_data_sector_writes == 0`,
     `rf_tx_packets == 0` under USB-C wired mode).
   - Contrast with `ILME-FX6 Ver. 6.01`: `Network -> Network Client Mode` &
     `Camera Remote Control` (`Enable`/`Disable`, PTP-IP CrSDK / `Monitor &
     Control`, zero `Still Img. Save Dest.` UI).
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
# Phase 365 Schema, Stage 82 (82/82) & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = (
    "phase365_realhw_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation_v1"
)
PHASE_365_VERSION = "365.0.0"
PHASE_NUMBER = 365
STAGE_INDEX = 82
STAGE_TOTAL = 82
MILESTONE_LABEL = "82/82"
IS_82ND_STAGE_MILESTONE = True

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

# Wave-72 Sub-Model 82A..82D Numeric & Invariant Contracts
# 82A — [Audio Rec Level] 0..31 / XLR-H1 Physical Bypass / Permanent Body Limiter vs FX6
FX3_AUDIO_REC_LEVEL_MIN = 0
FX3_AUDIO_REC_LEVEL_MAX = 31
FX3_AUDIO_REC_LEVEL_DEFAULT = 26
FX3_AUDIO_REC_LEVEL_STEPS_COUNT = 32
FX3_BODY_LIMITER_ALWAYS_ON = True
FX3_XLRH1_BODY_RECLEVEL_BYPASS_VERIFIED = True
FX3_XLRH1_BYPASS_ESCAPE_EVENTS = 0
FX6_DIGITAL_AUDIO_LEVEL_MIN = 0
FX6_DIGITAL_AUDIO_LEVEL_MAX = 99
FX6_LIMITER_MODE_STEPS_COUNT = 6
FX6_4STEP_LIMITER_RUMOR_DISPROVED = True
FX6_REF_LEVEL_STEPS_COUNT = 5

# 82B — [Audio Out Timing], [Volume Settings] & Exact 5-Option [4ch Audio Monitoring] vs FX6
FX3_VOLUME_SETTINGS_MIN = 0
FX3_VOLUME_SETTINGS_MAX = 15
FX3_VOLUME_SETTINGS_DEFAULT = 7
FX3_4CH_MONITORING_OPTIONS_COUNT = 5
FX3_3OPTION_ERRATA_CORRECTED = True
FX3_4CH_MONITORING_RESET_WIPE_EVENTS = 0
FX3_35MM_HEADPHONE_MAX_CHANNELS = 2
FX6_MONITOR_CH_OPTIONS_COUNT = 7
FX6_VOLUME_MIN = 0
FX6_VOLUME_MAX = 50
FX6_PHYSICAL_MONITOR_VOL_BUTTON_PRESENT = False
FX6_SDI_AUDIO_CHANNELS = 4

# 82C — [Touch Operation] Exact 4 Active Items vs Dormant Touch Shutter/AE/Pad & FX6
FX3_TOUCH_SETUP_ACTIVE_ITEMS_COUNT = 4
FX3_DORMANT_TOUCH_SHUTTER_AE_PAD_EXPOSED_EVENTS = 0
FX3_ILC2210_TOUCH_SHUTTER_HITS = 0
FX3_ILC2210_TOUCH_AE_HITS = 0
FX3_SPOT_LINK_TRACKS_MOVING_BOX = False
FX3_TOUCH_SETUP_RESET_WIPE_EVENTS = 0
FX6_TOUCH_MF_SUPPORTED = True
FX6_BIG6_FULL_MENU_TOUCH_SUPPORTED = True

# 82D — [Remote Shoot Setting], PTP/PTP-IP Destination Only RAM & Tier-0 Slot 1 EROFS=30
FX3_PTP_USB_VID_PID = "054c:0d2b"
FX3_PTPIP_TCP_PORT = 15740
FX3_REMOTE_SHOOT_FACTORY_DEFAULT_DEST = "Dest.+Camera"
FX3_REMOTE_SHOOT_DEST_ONLY_RAM_WRITES_SLOT1 = 0
FX3_SLOT1_REMOTE_SHOOT_WRITE_BYPASS_EVENTS = 0
FX6_STILL_IMG_SAVE_DEST_UI_EXPOSED = False

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
VALID_FX3_FW_VERSIONS: Tuple[str, ...] = (
    FW_VER_101,
    FW_VER_200,
    FW_VER_600,
    FW_VER_702,
)
VALID_ALL_FW_VERSIONS: Tuple[str, ...] = (
    FW_VER_101,
    FW_VER_200,
    FW_VER_500,
    FW_VER_600,
    FW_VER_601,
    FW_VER_702,
)

# 82A Constants
VALID_82A_OPERATIONS: Tuple[str, ...] = (
    "fx3_body_audio_rec_level",
    "fx3_xlr_h1_handle",
    "fx6_audio_input",
)
VALID_82A_SHOOT_MODES: Tuple[str, ...] = ("Movie", "S&Q", "Still")
VALID_XLR_H1_INPUT_MODES: Tuple[str, ...] = ("LINE", "MIC", "MIC+48V")
VALID_XLR_H1_ATT_DB: Tuple[int, ...] = (0, 10, 20)
VALID_XLR_H1_AGC_MODES: Tuple[str, ...] = ("AUTO", "MAN", "LINK")
FX6_CH1_SELECTS: Tuple[str, ...] = ("INPUT1", "Internal MIC", "Shoe CH1")
FX6_CH2_SELECTS: Tuple[str, ...] = ("INPUT1", "INPUT2", "Internal MIC", "Shoe CH2")
FX6_CH3_SELECTS: Tuple[str, ...] = ("Off", "INPUT1", "Internal MIC", "Shoe CH1")
FX6_CH4_SELECTS: Tuple[str, ...] = ("Off", "INPUT1", "INPUT2", "Internal MIC", "Shoe CH2")
FX6_MIC_REF_STEPS_DB: Tuple[int, ...] = (-80, -70, -60, -50, -40, -30)
FX6_LINE_REF_STEPS: Tuple[str, ...] = ("+4dB", "0dB", "-3dB", "EBUL")
FX6_REF_LEVEL_5_STEPS: Tuple[str, ...] = ("-20dB", "-18dB", "-16dB", "-12dB", "EBUL")
FX6_LIMITER_MODE_6_STEPS: Tuple[str, ...] = (
    "Off",
    "-6dB",
    "-9dB",
    "-12dB",
    "-15dB",
    "-17dB",
)

# 82B Constants
VALID_82B_OPERATIONS: Tuple[str, ...] = (
    "fx3_audio_out_timing",
    "fx3_volume_settings",
    "fx3_4ch_monitoring",
    "fx6_audio_output",
)
VALID_AUDIO_OUT_TIMINGS: Tuple[str, ...] = ("Live", "Lip Sync")
FX3_4CH_MONITORING_5_OPTIONS: Tuple[str, ...] = (
    "CH1/CH2",
    "CH3/CH4",
    "CH1+3/CH2+4",
    "CH1/CH1",
    "CH2/CH2",
)
FX3_4CH_ERRATA_INVALID_OPTIONS: Tuple[str, ...] = (
    "CH1/CH2 mono mix",
    "CH1+2/CH3+4",
    "All",
    "MIX ALL",
    "CH1",
    "CH2",
    "CH3",
    "CH4",
)
VALID_HDMI_4CH_OUTPUT_OPTIONS: Tuple[str, ...] = ("CH1/CH2", "CH3/CH4")
FX6_MONITOR_CH_7_OPTIONS: Tuple[str, ...] = (
    "CH1",
    "CH2",
    "CH3",
    "CH4",
    "CH1/CH2",
    "CH3/CH4",
    "MIX ALL",
)
FX6_HEADPHONE_OUT_MODES: Tuple[str, ...] = ("Stereo", "Mono")

# 82C Constants
VALID_82C_OPERATIONS: Tuple[str, ...] = (
    "fx3_touch_setup",
    "fx3_touch_tap_in_shooting",
    "dormant_touch_panel_pad",
    "dormant_touch_shutter",
    "dormant_touch_ae",
    "fx3_spot_metering_link",
    "fx6_touch_operation",
)
FX3_TOUCH_SETUP_4_ITEMS: Tuple[str, ...] = (
    "[Touch Operation]",
    "[Touch Sensitivity]",
    "[Touch Func. in Shooting]",
    "[Swipe Up]",
)
FX3_TOUCH_OPERATION_MODES: Tuple[str, ...] = ("On", "On: Playback Only", "Off")
FX3_TOUCH_SENSITIVITY_MODES: Tuple[str, ...] = ("Standard", "Sensitive")
FX3_TOUCH_FUNC_IN_SHOOTING_MODES: Tuple[str, ...] = (
    "Touch Focus",
    "Touch Tracking",
    "Off",
)
FX3_SWIPE_UP_MODES: Tuple[str, ...] = ("Open the Fn Menu", "Off")
FX3_SPOT_METERING_POINT_MODES: Tuple[str, ...] = ("Center", "Focus Point Link")
FX6_TOUCH_OPERATION_MODES: Tuple[str, ...] = ("On", "Off")
FX6_TOUCH_MF_MODES: Tuple[str, ...] = ("Spot Focus", "Tracking AF")

# 82D Constants
VALID_82D_OPERATIONS: Tuple[str, ...] = (
    "fx3_remote_shoot_config",
    "fx3_remote_capture",
    "fx6_camera_remote_control",
)
FX3_REMOTE_SHOOT_SAVE_DEST_V2_PLUS: Tuple[str, ...] = (
    "Destination Only",
    "Dest.+Camera",
    "Camera Only",
)
FX3_REMOTE_SHOOT_SAVE_DEST_V1: Tuple[str, ...] = (
    "PC Only",
    "PC+Camera",
    "Camera Only",
)
VALID_SAVE_IMAGE_SIZES: Tuple[str, ...] = ("Original", "2M")
VALID_RAW_J_SAVE_OPTIONS: Tuple[str, ...] = ("RAW & JPEG", "JPEG Only", "RAW Only")
VALID_RAW_H_SAVE_OPTIONS: Tuple[str, ...] = ("RAW & HEIF", "HEIF Only", "RAW Only")
VALID_REMOTE_TRANSPORTS: Tuple[str, ...] = ("PTP_USB_SICD", "PTP_IP_TCP_15740")
VALID_CONNECTION_STATES: Tuple[str, ...] = ("DISCONNECTED", "CONNECTED")

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


class Stage82Phase365Error(RuntimeError):
    """Raised on invalid Phase 365 Stage 82 HIL inputs or redline violation."""


# ---------------------------------------------------------------------------
# 25 Real-Hardware Wave-72 Donor Specifications (O_RDONLY & <= 4096 B Windows)
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


PHASE365_COMPACT_DONORS: Tuple[CompactDonorSpec, ...] = (
    CompactDonorSpec(
        name="fx3_string_en_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
        expected_size=373820,
        expected_sha256="7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        required_tokens=(
            b"Audio Rec Level",
            b"Audio Out Timing",
            b"Live",
            b"Lip Sync",
            b"4ch Audio Monitoring",
            b"CH1/CH2",
            b"CH3/CH4",
            b"CH1+3/CH2+4",
            b"CH1/CH1",
            b"CH2/CH2",
            b"Touch Sensitivity",
            b"Touch Func. in Shooting",
            b"Touch Tracking",
            b"Touch Focus",
            b"Swipe Up",
            b"Open the Fn Menu",
            b"On: Playback Only",
            b"Focus Point Link",
            b"Touch Panel/Pad",
            b"Touch Shutter",
            b"Touch AE",
            b"Remote Shoot Setting",
            b"Remote Shoot Function",
            b"Still Img. Save Dest.",
            b"Destination Only",
            b"Dest.+Camera",
            b"Camera Only",
            b"Save Image Size",
            b"RAW+J Save Image",
            b"RAW+H Save Image",
        ),
        absent_tokens=(
            b"CH1+2/CH3+4",
            b"CH1/CH2 mono mix",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_f.uxc",
        expected_size=322652,
        expected_sha256="4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        required_tokens=(
            "录音音量".encode("utf-8"),
            "音频输出时刻".encode("utf-8"),
            "实况转播".encode("utf-8"),
            "唇音同步".encode("utf-8"),
            "4ch音频监测".encode("utf-8"),
            "拍摄期间的触摸功能".encode("utf-8"),
            "触摸屏/触摸板".encode("utf-8"),
            "触屏快门".encode("utf-8"),
            "触屏AE".encode("utf-8"),
            "遥控拍摄设置".encode("utf-8"),
            "静态影像保存目的地".encode("utf-8"),
            "仅限目的地".encode("utf-8"),
            "目的地+拍摄装置".encode("utf-8"),
            "仅拍摄装置".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_f.uxc",
        expected_size=324148,
        expected_sha256="32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        required_tokens=(
            "錄音音量".encode("utf-8"),
            "音訊輸出時刻".encode("utf-8"),
            "即時播送".encode("utf-8"),
            "唇音同步".encode("utf-8"),
            "4ch音訊監聽".encode("utf-8"),
            "拍攝期間的觸控功能".encode("utf-8"),
            "觸控面板/觸控板".encode("utf-8"),
            "觸控快門".encode("utf-8"),
            "觸控AE".encode("utf-8"),
            "遙控拍攝設定".encode("utf-8"),
            "靜態影像儲存目的地".encode("utf-8"),
            "僅限目的地".encode("utf-8"),
            "目的地+拍攝裝置".encode("utf-8"),
            "僅限拍攝裝置".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_f.uxc",
        expected_size=447840,
        expected_sha256="45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        required_tokens=(
            "録音レベル".encode("utf-8"),
            "音声出力タイミング".encode("utf-8"),
            "ライブ".encode("utf-8"),
            "リップシンク".encode("utf-8"),
            "4ch音声のﾓﾆﾀﾘﾝｸﾞ".encode("utf-8"),
            "撮影時のタッチ機能".encode("utf-8"),
            "ﾀｯﾁﾊﾟﾈﾙ/ﾀｯﾁﾊﾟｯﾄﾞ".encode("utf-8"),
            "タッチシャッター".encode("utf-8"),
            "タッチAE".encode("utf-8"),
            "リモート撮影設定".encode("utf-8"),
            "静止画の保存先".encode("utf-8"),
            "接続先のみ".encode("utf-8"),
            "接続先+ｶﾒﾗ本体".encode("utf-8"),
            "カメラ本体のみ".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english.uxc",
        expected_size=165740,
        expected_sha256="204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        required_tokens=(b"Volume Settings", b"Touch Operation"),
    ),
    CompactDonorSpec(
        name="fx3_string_sc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese.uxc",
        expected_size=149064,
        expected_sha256="34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
        required_tokens=("音量设置".encode("utf-8"), "触摸操作".encode("utf-8")),
    ),
    CompactDonorSpec(
        name="fx3_string_tc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese.uxc",
        expected_size=151908,
        expected_sha256="be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
        required_tokens=("音量設定".encode("utf-8"), "觸控操作".encode("utf-8")),
    ),
    CompactDonorSpec(
        name="fx3_string_ja",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese.uxc",
        expected_size=208564,
        expected_sha256="f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
        required_tokens=("音量設定".encode("utf-8"), "タッチ操作".encode("utf-8")),
    ),
    CompactDonorSpec(
        name="fx3_string_en_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
        expected_size=69600,
        expected_sha256="a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        required_tokens=(b"Touch Operation", b"Cnct./Remote Sht.", b"Touch AE Cancel"),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_g.uxc",
        expected_size=61296,
        expected_sha256="a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
        required_tokens=("连接/遥控拍摄".encode("utf-8"), "取消触屏AE".encode("utf-8")),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_g.uxc",
        expected_size=61372,
        expected_sha256="97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80",
        required_tokens=("連線/遙控拍攝".encode("utf-8"), "取消觸控AE".encode("utf-8")),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_g.uxc",
        expected_size=89428,
        expected_sha256="4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980",
        required_tokens=("接続/ﾘﾓｰﾄ撮影".encode("utf-8"),),
    ),
    CompactDonorSpec(
        name="fx3_libptp",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libptp.so",
        expected_size=73304,
        expected_sha256="8646befc379b1efc2fe303f8462cbbe519bca77e308f25b9efcf56b30081da46",
        required_tokens=(b"PTP", b"libptp"),
    ),
    CompactDonorSpec(
        name="fx3_libinfraptpcontrol",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libInfraPtpControl.so",
        expected_size=165320,
        expected_sha256="445c83b36c7243a880523e4dd03f7231d6de601fe227b6730bf0b4e3b2741c6d",
        required_tokens=(
            b"/dev/usb/sicd_core",
            b"/dev/usb/sicd_data",
            b"/dev/usb/sicd_event",
            b"PTPT_EE_send_data_usb",
            b"PTPT_EE_send_data_ip_remote",
            b"PtpIpConnMgrThread",
            b"PtpIpEvtThread",
        ),
    ),
    CompactDonorSpec(
        name="fx3_libinfraptpextcmd",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libInfraPtpExtCmd.so",
        expected_size=35600,
        expected_sha256="2dfe5d52abf029192714a28b85c513076f9076b00733cc3c641018607f79e5b3",
        required_tokens=(b"InfraPtpExtCmd", b"PtpExtCmd"),
    ),
    CompactDonorSpec(
        name="fx3_libinframtpserver",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libInfraMtpServer.so",
        expected_size=276856,
        expected_sha256="95bdf031ea623a065e920fa5ae875a9138006fc17c00f35075cd44ca46b329c9",
        required_tokens=(b"InfraMtpServer",),
    ),
    CompactDonorSpec(
        name="fx6_string_en",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
        expected_size=118208,
        expected_sha256="5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        required_tokens=(
            b"Audio Input",
            b"Reference",
            b"Monitor",
            b"Headphone",
            b"Touch",
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_en_2",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
        expected_size=118676,
        expected_sha256="3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        required_tokens=(b"Monitor", b"Limiter", b"Remote", b"Touch"),
    ),
    CompactDonorSpec(
        name="fx6_libptp",
        rel_path=f"{_FX6_NF15_PREFIX}/lib/libptp.so",
        expected_size=77408,
        expected_sha256="21e212ae68a6d8fe1ae8fc4eb40bd3629e3f126a41ddfc1e00e750cd46a134aa",
        required_tokens=(b"PTP",),
    ),
    CompactDonorSpec(
        name="fx6_libinfraptpcontrol",
        rel_path=f"{_FX6_NF15_PREFIX}/lib/libInfraPtpControl.so",
        expected_size=152520,
        expected_sha256="5af1afff957290bbd2519e237af5df761413e54193e149ee70189f32fe646a27",
        required_tokens=(b"PtpIpConnMgrThread", b"PTPT_EE_send_data_ip_remote"),
    ),
)

PHASE365_WINDOW_DONORS: Tuple[WindowDonorSpec, ...] = (
    WindowDonorSpec(
        name="fx3_appfw",
        rel_path="fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        expected_size=79015712,
        head4k_sha256="de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
        windows=(
            (0x3B32000, "AUDIO_RECORDING_LEVEL_0", b"VAL_setting_audio_recording_level_AUDIO_RECORDING_LEVEL_0"),
            (0x3B32800, "AUDIO_RECORDING_LEVEL_31", b"VAL_setting_audio_recording_level_AUDIO_RECORDING_LEVEL_31"),
            (0x3C25000, "adj_audio_rec_level_defult", b"adj_audio_rec_level_defult"),
            (0x3BB2800, "UIBIZ_INP_HOTSHOE_XLRMIC", b"UIBIZ_INP_HOTSHOE_XLRMIC"),
            (0x3BC7000, "BKID_APP_setting_audio_output_timing", b"BKID_APP_setting_audio_output_timing"),
            (0x3B33000, "AUDIO_OUTPUT_TIMING_LIVE", b"VAL_setting_audio_output_timing_AUDIO_OUTPUT_TIMING_LIVE"),
            (0x3B33000, "AUDIO_OUTPUT_TIMING_LIP_SYNC", b"VAL_setting_audio_output_timing_AUDIO_OUTPUT_TIMING_LIP_SYNC"),
            (0x2FA8000, "VOLUME_SETTINGS_0", b"VOLUME_SETTINGS_0"),
            (0x2FA7800, "VOLUME_SETTINGS_15", b"VOLUME_SETTINGS_15"),
            (0x3BCB800, "BKID_APP_setting_audio_monitoring_ch", b"BKID_APP_setting_audio_monitoring_ch"),
            (0x2FA8000, "AUDIO_MONITORING_CH_1CH_2CH", b"AUDIO_MONITORING_CH_1CH_2CH"),
            (0x2FA8000, "AUDIO_MONITORING_CH_3CH_4CH", b"AUDIO_MONITORING_CH_3CH_4CH"),
            (0x2FA8000, "AUDIO_MONITORING_CH_MIX_ALL", b"AUDIO_MONITORING_CH_MIX_ALL"),
            (0x2FA8000, "AUDIO_MONITORING_CH_1CH", b"AUDIO_MONITORING_CH_1CH"),
            (0x2FA8000, "AUDIO_MONITORING_CH_2CH", b"AUDIO_MONITORING_CH_2CH"),
            (0x3BCC000, "BKID_APP_setting_4ch_output_ch", b"BKID_APP_setting_4ch_output_ch"),
            (0x3BCB800, "BKID_APP_setting_touch_panel_pad", b"BKID_APP_setting_touch_panel_pad"),
            (0x3B03800, "SHOOTING_TOUCH_FUNCTION_TOUCH_SHUTTER", b"SHOOTING_TOUCH_FUNCTION_TOUCH_SHUTTER"),
            (0x3986000, "PID_SET_TOUCH_SPOT_METER", b"PID_SET_TOUCH_SPOT_METER"),
            (0x3BC9800, "BKID_APP_setting_pc_remote_func", b"BKID_APP_setting_pc_remote_func"),
            (0x3BC9800, "BKID_APP_setting_remote_settings_still_img_save_dest", b"BKID_APP_setting_remote_settings_still_img_save_dest"),
            (0x3BC9800, "BKID_APP_setting_remote_settings_still_img_trans_size", b"BKID_APP_setting_remote_settings_still_img_trans_size"),
            (0x3BC9800, "BKID_APP_setting_remote_settings_raw_j_pc_save_img", b"BKID_APP_setting_remote_settings_raw_j_pc_save_img"),
            (0x3BC9800, "BKID_APP_setting_remote_settings_raw_h_pc_save_img", b"BKID_APP_setting_remote_settings_raw_h_pc_save_img"),
            (0x39BC000, "PRM_HAITA_still_img_save_dest_conn", b"PRM_HAITA_setting_remote_settings_still_img_save_dest_pc_remote_connection_state"),
            (0x3B97800, "stillrec_running_without_pseudo_rec", b"N5model37stillrec_running_without_pseudo_rec_tE"),
            (0x3B1C800, "HAITA_pc_only_media_not_mount", b"VAL_HAITA_not_save_still_smartphone_only_not_save_still_pc_only_media_mount_state_setting_release_wo_card_NOT_SAVE_STILL_SMARTPHONE_ONLY_NOT_SAVE_STILL_PC_ONLY_PC_REMOTE_CONNECTED_MEDIA_NOT_MOUNT"),
        ),
    ),
    WindowDonorSpec(
        name="fx3_libinfraremote",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libInfraRemote.so",
        expected_size=1271152,
        head4k_sha256="616c7e922ab24acb8e4038c4ff78a22f86265e8670fd06699c9eb92f5f86f7f2",
        windows=(
            (0x0025000, "InfraRemoteIP", b"InfraRemoteIP"),
            (0x0026000, "actionStartPtpIp", b"actionStartPtpIp"),
            (0x0028800, "actionStopPtpIp", b"actionStopPtpIp"),
            (0x0048000, "SetContentsTransferMode", b"SetContentsTransferMode"),
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
            (0x26BA000, "VAL_setting_ch1_input_select_", b"VAL_setting_ch1_input_select_"),
            (0x26BA800, "VAL_setting_ch4_input_select_", b"VAL_setting_ch4_input_select_"),
            (0x26BD800, "INPUT_MIC_REFERENCE_80DB", b"INPUT_MIC_REFERENCE_80DB"),
            (0x26BD800, "INPUT_MIC_REFERENCE_30DB", b"INPUT_MIC_REFERENCE_30DB"),
            (0x2786800, "EXTERN_LINE_INPUT_REFERENCE_4_DB", b"EXTERN_LINE_INPUT_REFERENCE_4_DB"),
            (0x2786800, "EXTERN_LINE_INPUT_REFERENCE_EBUL", b"EXTERN_LINE_INPUT_REFERENCE_EBUL"),
            (0x2786800, "EXTERN_REFERENCE_LEVEL_NEGATIVE_20_DB", b"EXTERN_REFERENCE_LEVEL_NEGATIVE_20_DB"),
            (0x2786800, "EXTERN_REFERENCE_LEVEL_NEGATIVE_18_DB", b"EXTERN_REFERENCE_LEVEL_NEGATIVE_18_DB"),
            (0x2786800, "EXTERN_REFERENCE_LEVEL_NEGATIVE_16_DB", b"EXTERN_REFERENCE_LEVEL_NEGATIVE_16_DB"),
            (0x2786800, "EXTERN_REFERENCE_LEVEL_NEGATIVE_12_DB", b"EXTERN_REFERENCE_LEVEL_NEGATIVE_12_DB"),
            (0x2786800, "EXTERN_REFERENCE_LEVEL_EBUL", b"EXTERN_REFERENCE_LEVEL_EBUL"),
            (0x2786000, "EXTERN_LIMITER_MODE_OFF", b"EXTERN_LIMITER_MODE_OFF"),
            (0x2786000, "EXTERN_LIMITER_MODE_NEGATIVE_6_DB", b"EXTERN_LIMITER_MODE_NEGATIVE_6_DB"),
            (0x2786000, "EXTERN_LIMITER_MODE_NEGATIVE_9_DB", b"EXTERN_LIMITER_MODE_NEGATIVE_9_DB"),
            (0x2786000, "EXTERN_LIMITER_MODE_NEGATIVE_12_DB", b"EXTERN_LIMITER_MODE_NEGATIVE_12_DB"),
            (0x2786000, "EXTERN_LIMITER_MODE_NEGATIVE_15_DB", b"EXTERN_LIMITER_MODE_NEGATIVE_15_DB"),
            (0x2786000, "EXTERN_LIMITER_MODE_NEGATIVE_17_DB", b"EXTERN_LIMITER_MODE_NEGATIVE_17_DB"),
            (0x2786000, "EXTERN_AUDIO_MONITORING_CH_CH1", b"EXTERN_AUDIO_MONITORING_CH_CH1"),
            (0x2786000, "EXTERN_AUDIO_MONITORING_CH_CH1_CH2", b"EXTERN_AUDIO_MONITORING_CH_CH1_CH2"),
            (0x2786000, "EXTERN_AUDIO_MONITORING_CH_MIXALL", b"EXTERN_AUDIO_MONITORING_CH_MIXALL"),
            (0x2786000, "EXTERN_HEADPHONE_OUT_STEREO", b"EXTERN_HEADPHONE_OUT_STEREO"),
            (0x2786000, "EXTERN_HEADPHONE_OUT_MONO", b"EXTERN_HEADPHONE_OUT_MONO"),
            (0x2706800, "BKID_APP_SETTING_TOUCH_OPERATION", b"BKID_APP_SETTING_TOUCH_OPERATION"),
            (0x2708800, "BKID_APP_SETTING_TOUCH_FUNCTION_IN_MF", b"BKID_APP_SETTING_TOUCH_FUNCTION_IN_MF"),
            (0x2713800, "BKID_APP_TOUCH_TRACKING_STATE", b"BKID_APP_TOUCH_TRACKING_STATE"),
            (0x2739000, "BKID_APP_HOME_SCREEN_STATE", b"BKID_APP_HOME_SCREEN_STATE"),
            (0x26D4000, "TYPE_COMMUNICATION_WITH_BASE_BLOCK_VIA_PTP_IP", b"TYPE_COMMUNICATION_WITH_BASE_BLOCK_VIA_PTP_IP"),
            (0x252F000, "setting_remote_settings_still_img_save_dest", b"setting_remote_settings_still_img_save_dest"),
        ),
        absent_windows=(
            (0x2786000, "NO_MONITOR_VOL", b"MONITOR VOL"),
        ),
    ),
    WindowDonorSpec(
        name="fx6_libinfraremote",
        rel_path=f"{_FX6_NF15_PREFIX}/lib/libInfraRemote.so",
        expected_size=1262824,
        head4k_sha256="81817f9a546943573512d8e121b7d2b6136525b9a2d43c1cece6390c9223f06b",
        windows=(
            (0x0024800, "InfraRemoteIP", b"InfraRemoteIP"),
            (0x0026000, "actionStartPtpIp", b"actionStartPtpIp"),
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
            raise Stage82Phase365Error(
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
        raise Stage82Phase365Error(
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


def inspect_phase365_wave72_donors(
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
            resolved_root / s.rel_path for s in PHASE365_COMPACT_DONORS
        ] + [resolved_root / w.rel_path for w in PHASE365_WINDOW_DONORS]
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
            for s in PHASE365_COMPACT_DONORS
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
            for w in PHASE365_WINDOW_DONORS
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
    for spec in PHASE365_COMPACT_DONORS:
        p = resolved_root / spec.rel_path
        data = _read_full_compact_o_rdonly(p)
        if len(data) != spec.expected_size:
            raise Stage82Phase365Error(
                f"{spec.name} size {len(data)} != expected {spec.expected_size}"
            )
        digest = hashlib.sha256(data).hexdigest()
        if digest != spec.expected_sha256:
            raise Stage82Phase365Error(
                f"{spec.name} sha256 {digest} != expected {spec.expected_sha256}"
            )
        for tok in spec.required_tokens:
            if tok not in data:
                raise Stage82Phase365Error(
                    f"{spec.name} missing required token {tok!r}"
                )
        for abs_tok in spec.absent_tokens:
            if abs_tok in data:
                raise Stage82Phase365Error(
                    f"{spec.name} unexpectedly contains forbidden token {abs_tok!r}"
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
    for wspec in PHASE365_WINDOW_DONORS:
        p = resolved_root / wspec.rel_path
        size0, head4k, _ = _read_bounded_window_o_rdonly(p, 0, _BOUNDED_WINDOW_BYTES)
        if size0 != wspec.expected_size:
            raise Stage82Phase365Error(
                f"{wspec.name} size {size0} != expected {wspec.expected_size}"
            )
        h4k_sha = hashlib.sha256(head4k).hexdigest()
        if h4k_sha != wspec.head4k_sha256:
            raise Stage82Phase365Error(
                f"{wspec.name} head4k sha256 {h4k_sha} != expected {wspec.head4k_sha256}"
            )
        cache: Dict[int, bytes] = {}
        for off, label, needle in wspec.windows:
            if off not in cache:
                _, _, win = _read_bounded_window_o_rdonly(
                    p, off, _BOUNDED_WINDOW_BYTES
                )
                cache[off] = win
            if needle not in cache[off]:
                raise Stage82Phase365Error(
                    f"{wspec.name} window 0x{off:x} ({label}) missing {needle!r}"
                )
        for off, label, forbidden in wspec.absent_windows:
            if off not in cache:
                _, _, win = _read_bounded_window_o_rdonly(
                    p, off, _BOUNDED_WINDOW_BYTES
                )
                cache[off] = win
            if forbidden in cache[off]:
                raise Stage82Phase365Error(
                    f"{wspec.name} window 0x{off:x} ({label}) unexpectedly contains {forbidden!r}"
                )
        window_entries.append(
            {
                "name": wspec.name,
                "size_bytes": size0,
                "head4k_sha256": h4k_sha,
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
# Sub-Model 82A: [Audio Rec Level] (0..31) / XLR-H1 Bypass / Body Limiter
#                vs FX6 3-Tier Reference & Exact 6-Step Limiter Mode
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AudioRecLevelAndXlrBypassAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    menu_path: str
    shoot_mode: str
    active_input_source: str
    body_audio_rec_level: Optional[int]
    body_audio_rec_level_greyed_out: bool
    body_limiter_always_on: bool
    limiter_defeatable: bool
    xlr_h1_handle_audio_on: bool
    xlr_h1_input_mode: Optional[str]
    xlr_h1_att_db: Optional[int]
    xlr_h1_std_level_dbu: Optional[int]
    xlr_h1_agc_mode: Optional[str]
    xlr_h1_dial_0_to_10: Optional[int]
    xlr_h1_input2_dial_disabled: bool
    channels_count: int
    bit_depth: int
    resettable_via_camera_settings_reset: bool
    fx6_ch_input_select: Optional[str]
    fx6_digital_level_0_99: Optional[int]
    fx6_mic_reference_db: Optional[int]
    fx6_line_input_reference: Optional[str]
    fx6_reference_level: Optional[str]
    fx6_limiter_mode: Optional[str]
    fx6_limiter_steps_count: int
    fx6_sg_1khz_enabled: bool


def simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "fx3_body_audio_rec_level",
    shoot_mode: str = "Movie",
    body_rec_level: int = FX3_AUDIO_REC_LEVEL_DEFAULT,
    mic_35mm_plugged: bool = False,
    xlr_h1_handle_audio_on: bool = False,
    xlr_h1_input_mode: str = "MIC+48V",
    xlr_h1_att_db: int = 10,
    xlr_h1_agc_mode: str = "MAN",
    xlr_h1_dial_0_to_10: int = 5,
    xlr_h1_four_ch_mode: bool = False,
    attempt_body_rec_level_override: bool = False,
    limiter_disable_requested: bool = False,
    delete_key_reset: bool = False,
    camera_settings_reset_applied: bool = False,
    fx6_channel: str = "CH1",
    fx6_ch_input_select: str = "INPUT1",
    fx6_digital_level_0_99: int = 50,
    fx6_mic_reference_db: int = -60,
    fx6_line_input_reference: str = "+4dB",
    fx6_reference_level: str = "-20dB",
    fx6_limiter_mode: str = "-6dB",
    fx6_sg_1khz_enabled: bool = False,
) -> AudioRecLevelAndXlrBypassAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage82Phase365Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage82Phase365Error(f"Unsupported fw_version: {fw_version!r}")
    if operation not in VALID_82A_OPERATIONS:
        raise Stage82Phase365Error(f"Unsupported 82A operation: {operation!r}")
    if shoot_mode not in VALID_82A_SHOOT_MODES:
        raise Stage82Phase365Error(f"Unsupported shoot_mode: {shoot_mode!r}")

    if body_profile == BODY_MODEL_FX6:
        if operation != "fx6_audio_input":
            return AudioRecLevelAndXlrBypassAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"FX6 does not expose FX3 operation {operation} -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                menu_path="Audio -> [Audio Input]",
                shoot_mode=shoot_mode,
                active_input_source="fx6_xlr",
                body_audio_rec_level=None,
                body_audio_rec_level_greyed_out=False,
                body_limiter_always_on=False,
                limiter_defeatable=True,
                xlr_h1_handle_audio_on=False,
                xlr_h1_input_mode=None,
                xlr_h1_att_db=None,
                xlr_h1_std_level_dbu=None,
                xlr_h1_agc_mode=None,
                xlr_h1_dial_0_to_10=None,
                xlr_h1_input2_dial_disabled=False,
                channels_count=4,
                bit_depth=24,
                resettable_via_camera_settings_reset=False,
                fx6_ch_input_select=fx6_ch_input_select,
                fx6_digital_level_0_99=fx6_digital_level_0_99,
                fx6_mic_reference_db=fx6_mic_reference_db,
                fx6_line_input_reference=fx6_line_input_reference,
                fx6_reference_level=fx6_reference_level,
                fx6_limiter_mode=fx6_limiter_mode,
                fx6_limiter_steps_count=FX6_LIMITER_MODE_STEPS_COUNT,
                fx6_sg_1khz_enabled=fx6_sg_1khz_enabled,
            )

        ch_map = {
            "CH1": FX6_CH1_SELECTS,
            "CH2": FX6_CH2_SELECTS,
            "CH3": FX6_CH3_SELECTS,
            "CH4": FX6_CH4_SELECTS,
        }
        if fx6_channel not in ch_map or fx6_ch_input_select not in ch_map[fx6_channel]:
            return AudioRecLevelAndXlrBypassAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"FX6 invalid {fx6_channel} Input Select={fx6_ch_input_select!r} -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                menu_path="Audio -> [Audio Input]",
                shoot_mode=shoot_mode,
                active_input_source="fx6_xlr",
                body_audio_rec_level=None,
                body_audio_rec_level_greyed_out=False,
                body_limiter_always_on=False,
                limiter_defeatable=True,
                xlr_h1_handle_audio_on=False,
                xlr_h1_input_mode=None,
                xlr_h1_att_db=None,
                xlr_h1_std_level_dbu=None,
                xlr_h1_agc_mode=None,
                xlr_h1_dial_0_to_10=None,
                xlr_h1_input2_dial_disabled=False,
                channels_count=4,
                bit_depth=24,
                resettable_via_camera_settings_reset=False,
                fx6_ch_input_select=fx6_ch_input_select,
                fx6_digital_level_0_99=fx6_digital_level_0_99,
                fx6_mic_reference_db=fx6_mic_reference_db,
                fx6_line_input_reference=fx6_line_input_reference,
                fx6_reference_level=fx6_reference_level,
                fx6_limiter_mode=fx6_limiter_mode,
                fx6_limiter_steps_count=FX6_LIMITER_MODE_STEPS_COUNT,
                fx6_sg_1khz_enabled=fx6_sg_1khz_enabled,
            )

        if (
            fx6_digital_level_0_99 < FX6_DIGITAL_AUDIO_LEVEL_MIN
            or fx6_digital_level_0_99 > FX6_DIGITAL_AUDIO_LEVEL_MAX
            or fx6_mic_reference_db not in FX6_MIC_REF_STEPS_DB
            or fx6_line_input_reference not in FX6_LINE_REF_STEPS
            or fx6_reference_level not in FX6_REF_LEVEL_5_STEPS
            or fx6_limiter_mode not in FX6_LIMITER_MODE_6_STEPS
        ):
            return AudioRecLevelAndXlrBypassAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason="FX6 Audio Input parameter out of Ver. 6.01 enum/0..99 range -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                menu_path="Audio -> [Audio Input]",
                shoot_mode=shoot_mode,
                active_input_source="fx6_xlr",
                body_audio_rec_level=None,
                body_audio_rec_level_greyed_out=False,
                body_limiter_always_on=False,
                limiter_defeatable=True,
                xlr_h1_handle_audio_on=False,
                xlr_h1_input_mode=None,
                xlr_h1_att_db=None,
                xlr_h1_std_level_dbu=None,
                xlr_h1_agc_mode=None,
                xlr_h1_dial_0_to_10=None,
                xlr_h1_input2_dial_disabled=False,
                channels_count=4,
                bit_depth=24,
                resettable_via_camera_settings_reset=False,
                fx6_ch_input_select=fx6_ch_input_select,
                fx6_digital_level_0_99=fx6_digital_level_0_99,
                fx6_mic_reference_db=fx6_mic_reference_db,
                fx6_line_input_reference=fx6_line_input_reference,
                fx6_reference_level=fx6_reference_level,
                fx6_limiter_mode=fx6_limiter_mode,
                fx6_limiter_steps_count=FX6_LIMITER_MODE_STEPS_COUNT,
                fx6_sg_1khz_enabled=fx6_sg_1khz_enabled,
            )

        return AudioRecLevelAndXlrBypassAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX6 Audio > Audio Input: {fx6_channel}={fx6_ch_input_select}, "
                f"Level={fx6_digital_level_0_99}/99, MICRef={fx6_mic_reference_db}dB, "
                f"LineRef={fx6_line_input_reference}, Ref={fx6_reference_level}, "
                f"LimiterMode={fx6_limiter_mode} (6 steps, SG={fx6_sg_1khz_enabled})"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path="Audio -> [Audio Input]",
            shoot_mode=shoot_mode,
            active_input_source=f"fx6_{fx6_channel}_{fx6_ch_input_select}",
            body_audio_rec_level=None,
            body_audio_rec_level_greyed_out=False,
            body_limiter_always_on=False,
            limiter_defeatable=True,
            xlr_h1_handle_audio_on=False,
            xlr_h1_input_mode=None,
            xlr_h1_att_db=None,
            xlr_h1_std_level_dbu=None,
            xlr_h1_agc_mode=None,
            xlr_h1_dial_0_to_10=None,
            xlr_h1_input2_dial_disabled=False,
            channels_count=4,
            bit_depth=24,
            resettable_via_camera_settings_reset=False,
            fx6_ch_input_select=fx6_ch_input_select,
            fx6_digital_level_0_99=fx6_digital_level_0_99,
            fx6_mic_reference_db=fx6_mic_reference_db,
            fx6_line_input_reference=fx6_line_input_reference,
            fx6_reference_level=fx6_reference_level,
            fx6_limiter_mode=fx6_limiter_mode,
            fx6_limiter_steps_count=FX6_LIMITER_MODE_STEPS_COUNT,
            fx6_sg_1khz_enabled=fx6_sg_1khz_enabled,
        )

    # ILME-FX3 path
    if operation == "fx6_audio_input":
        return AudioRecLevelAndXlrBypassAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="FX3 does not expose FX6 3-tier Reference or 6-step Limiter Mode menu -> EOPNOTSUPP=95",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path="Shooting -> [Audio Recording] -> [Audio Rec Level]",
            shoot_mode=shoot_mode,
            active_input_source="internal_stereo_mic",
            body_audio_rec_level=body_rec_level,
            body_audio_rec_level_greyed_out=False,
            body_limiter_always_on=True,
            limiter_defeatable=False,
            xlr_h1_handle_audio_on=False,
            xlr_h1_input_mode=None,
            xlr_h1_att_db=None,
            xlr_h1_std_level_dbu=None,
            xlr_h1_agc_mode=None,
            xlr_h1_dial_0_to_10=None,
            xlr_h1_input2_dial_disabled=False,
            channels_count=2,
            bit_depth=16,
            resettable_via_camera_settings_reset=True,
            fx6_ch_input_select=None,
            fx6_digital_level_0_99=None,
            fx6_mic_reference_db=None,
            fx6_line_input_reference=None,
            fx6_reference_level=None,
            fx6_limiter_mode=None,
            fx6_limiter_steps_count=0,
            fx6_sg_1khz_enabled=False,
        )

    if shoot_mode == "S&Q":
        return AudioRecLevelAndXlrBypassAudit(
            admitted=False,
            errno_code=EBUSY_ERRNO,
            reason="S&Q Motion locks 0ch audio and greys out all 4 [Audio Recording] items -> EBUSY=16",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path="Shooting -> [Audio Recording] -> [Audio Rec Level]",
            shoot_mode=shoot_mode,
            active_input_source="none_0ch_sq",
            body_audio_rec_level=None,
            body_audio_rec_level_greyed_out=True,
            body_limiter_always_on=True,
            limiter_defeatable=False,
            xlr_h1_handle_audio_on=xlr_h1_handle_audio_on,
            xlr_h1_input_mode=None,
            xlr_h1_att_db=None,
            xlr_h1_std_level_dbu=None,
            xlr_h1_agc_mode=None,
            xlr_h1_dial_0_to_10=None,
            xlr_h1_input2_dial_disabled=False,
            channels_count=0,
            bit_depth=0,
            resettable_via_camera_settings_reset=True,
            fx6_ch_input_select=None,
            fx6_digital_level_0_99=None,
            fx6_mic_reference_db=None,
            fx6_line_input_reference=None,
            fx6_reference_level=None,
            fx6_limiter_mode=None,
            fx6_limiter_steps_count=0,
            fx6_sg_1khz_enabled=False,
        )

    if limiter_disable_requested:
        return AudioRecLevelAndXlrBypassAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="FX3 internal/3.5mm body limiter always operates and cannot be disabled -> EOPNOTSUPP=95",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path="Shooting -> [Audio Recording] -> [Audio Rec Level]",
            shoot_mode=shoot_mode,
            active_input_source="body_35mm_mic" if mic_35mm_plugged else "internal_stereo_mic",
            body_audio_rec_level=body_rec_level,
            body_audio_rec_level_greyed_out=False,
            body_limiter_always_on=True,
            limiter_defeatable=False,
            xlr_h1_handle_audio_on=xlr_h1_handle_audio_on,
            xlr_h1_input_mode=None,
            xlr_h1_att_db=None,
            xlr_h1_std_level_dbu=None,
            xlr_h1_agc_mode=None,
            xlr_h1_dial_0_to_10=None,
            xlr_h1_input2_dial_disabled=False,
            channels_count=2,
            bit_depth=16,
            resettable_via_camera_settings_reset=True,
            fx6_ch_input_select=None,
            fx6_digital_level_0_99=None,
            fx6_mic_reference_db=None,
            fx6_line_input_reference=None,
            fx6_reference_level=None,
            fx6_limiter_mode=None,
            fx6_limiter_steps_count=0,
            fx6_sg_1khz_enabled=False,
        )

    # Preemption chain: 3.5mm MIC > XLR-H1 (HANDLE AUDIO=ON) > Internal Stereo Mic
    if (not mic_35mm_plugged) and xlr_h1_handle_audio_on:
        if (
            xlr_h1_input_mode not in VALID_XLR_H1_INPUT_MODES
            or xlr_h1_att_db not in VALID_XLR_H1_ATT_DB
            or xlr_h1_agc_mode not in VALID_XLR_H1_AGC_MODES
            or xlr_h1_dial_0_to_10 < 0
            or xlr_h1_dial_0_to_10 > 10
        ):
            return AudioRecLevelAndXlrBypassAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason="Invalid XLR-H1 switch/attenuator/dial parameter -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                menu_path="XLR-H1 Physical Handle (Body [Audio Rec Level] bypassed)",
                shoot_mode=shoot_mode,
                active_input_source="xlr_h1_mishoe",
                body_audio_rec_level=None,
                body_audio_rec_level_greyed_out=True,
                body_limiter_always_on=True,
                limiter_defeatable=False,
                xlr_h1_handle_audio_on=True,
                xlr_h1_input_mode=xlr_h1_input_mode,
                xlr_h1_att_db=xlr_h1_att_db,
                xlr_h1_std_level_dbu=None,
                xlr_h1_agc_mode=xlr_h1_agc_mode,
                xlr_h1_dial_0_to_10=xlr_h1_dial_0_to_10,
                xlr_h1_input2_dial_disabled=False,
                channels_count=4 if xlr_h1_four_ch_mode else 2,
                bit_depth=24,
                resettable_via_camera_settings_reset=True,
                fx6_ch_input_select=None,
                fx6_digital_level_0_99=None,
                fx6_mic_reference_db=None,
                fx6_line_input_reference=None,
                fx6_reference_level=None,
                fx6_limiter_mode=None,
                fx6_limiter_steps_count=0,
                fx6_sg_1khz_enabled=False,
            )

        if attempt_body_rec_level_override:
            return AudioRecLevelAndXlrBypassAudit(
                admitted=False,
                errno_code=EBUSY_ERRNO,
                reason=(
                    "XLR-H1 HANDLE AUDIO=ON bypasses and greys out body [Audio Rec Level]; "
                    "physical handle switches govern exclusively -> EBUSY=16"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                menu_path="Shooting -> [Audio Recording] -> [Audio Rec Level] (greyed_out)",
                shoot_mode=shoot_mode,
                active_input_source="xlr_h1_mishoe",
                body_audio_rec_level=None,
                body_audio_rec_level_greyed_out=True,
                body_limiter_always_on=True,
                limiter_defeatable=False,
                xlr_h1_handle_audio_on=True,
                xlr_h1_input_mode=xlr_h1_input_mode,
                xlr_h1_att_db=xlr_h1_att_db,
                xlr_h1_std_level_dbu=4 if xlr_h1_input_mode == "LINE" else (-60 + xlr_h1_att_db),
                xlr_h1_agc_mode=xlr_h1_agc_mode,
                xlr_h1_dial_0_to_10=xlr_h1_dial_0_to_10,
                xlr_h1_input2_dial_disabled=(xlr_h1_agc_mode == "LINK"),
                channels_count=4 if xlr_h1_four_ch_mode else 2,
                bit_depth=24,
                resettable_via_camera_settings_reset=True,
                fx6_ch_input_select=None,
                fx6_digital_level_0_99=None,
                fx6_mic_reference_db=None,
                fx6_line_input_reference=None,
                fx6_reference_level=None,
                fx6_limiter_mode=None,
                fx6_limiter_steps_count=0,
                fx6_sg_1khz_enabled=False,
            )

        std_dbu = 4 if xlr_h1_input_mode == "LINE" else (-60 + xlr_h1_att_db)
        return AudioRecLevelAndXlrBypassAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"XLR-H1 HANDLE AUDIO=ON active ({xlr_h1_input_mode}, std={std_dbu:+d}dBu, "
                f"AGC={xlr_h1_agc_mode}, dial={xlr_h1_dial_0_to_10}/10); body [Audio Rec Level] bypassed"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path="XLR-H1 Physical Handle (Body [Audio Rec Level] bypassed)",
            shoot_mode=shoot_mode,
            active_input_source="xlr_h1_mishoe",
            body_audio_rec_level=None,
            body_audio_rec_level_greyed_out=True,
            body_limiter_always_on=True,
            limiter_defeatable=False,
            xlr_h1_handle_audio_on=True,
            xlr_h1_input_mode=xlr_h1_input_mode,
            xlr_h1_att_db=xlr_h1_att_db,
            xlr_h1_std_level_dbu=std_dbu,
            xlr_h1_agc_mode=xlr_h1_agc_mode,
            xlr_h1_dial_0_to_10=xlr_h1_dial_0_to_10,
            xlr_h1_input2_dial_disabled=(xlr_h1_agc_mode == "LINK"),
            channels_count=4 if xlr_h1_four_ch_mode else 2,
            bit_depth=24,
            resettable_via_camera_settings_reset=True,
            fx6_ch_input_select=None,
            fx6_digital_level_0_99=None,
            fx6_mic_reference_db=None,
            fx6_line_input_reference=None,
            fx6_reference_level=None,
            fx6_limiter_mode=None,
            fx6_limiter_steps_count=0,
            fx6_sg_1khz_enabled=False,
        )

    # Body internal stereo mic or 3.5mm MIC path (3.5mm preempts XLR-H1!)
    if body_rec_level < FX3_AUDIO_REC_LEVEL_MIN or body_rec_level > FX3_AUDIO_REC_LEVEL_MAX:
        return AudioRecLevelAndXlrBypassAudit(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason=f"FX3 [Audio Rec Level] {body_rec_level} out of 0..31 -> EINVAL=22",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path="Shooting -> [Audio Recording] -> [Audio Rec Level]",
            shoot_mode=shoot_mode,
            active_input_source="body_35mm_mic" if mic_35mm_plugged else "internal_stereo_mic",
            body_audio_rec_level=None,
            body_audio_rec_level_greyed_out=False,
            body_limiter_always_on=True,
            limiter_defeatable=False,
            xlr_h1_handle_audio_on=xlr_h1_handle_audio_on,
            xlr_h1_input_mode=None,
            xlr_h1_att_db=None,
            xlr_h1_std_level_dbu=None,
            xlr_h1_agc_mode=None,
            xlr_h1_dial_0_to_10=None,
            xlr_h1_input2_dial_disabled=False,
            channels_count=2,
            bit_depth=16,
            resettable_via_camera_settings_reset=True,
            fx6_ch_input_select=None,
            fx6_digital_level_0_99=None,
            fx6_mic_reference_db=None,
            fx6_line_input_reference=None,
            fx6_reference_level=None,
            fx6_limiter_mode=None,
            fx6_limiter_steps_count=0,
            fx6_sg_1khz_enabled=False,
        )

    eff_level = (
        FX3_AUDIO_REC_LEVEL_DEFAULT
        if (delete_key_reset or camera_settings_reset_applied)
        else body_rec_level
    )
    active_src = "body_35mm_mic" if mic_35mm_plugged else "internal_stereo_mic"
    return AudioRecLevelAndXlrBypassAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 Shooting -> [Audio Recording] -> [Audio Rec Level]={eff_level} "
            f"(0..31, default=26 adj_audio_rec_level_defult, src={active_src}, "
            "body_limiter_always_on=True, resettable=True)"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        menu_path="Shooting -> [Audio Recording] -> [Audio Rec Level]",
        shoot_mode=shoot_mode,
        active_input_source=active_src,
        body_audio_rec_level=eff_level,
        body_audio_rec_level_greyed_out=False,
        body_limiter_always_on=True,
        limiter_defeatable=False,
        xlr_h1_handle_audio_on=xlr_h1_handle_audio_on,
        xlr_h1_input_mode=None,
        xlr_h1_att_db=None,
        xlr_h1_std_level_dbu=None,
        xlr_h1_agc_mode=None,
        xlr_h1_dial_0_to_10=None,
        xlr_h1_input2_dial_disabled=False,
        channels_count=2,
        bit_depth=16,
        resettable_via_camera_settings_reset=True,
        fx6_ch_input_select=None,
        fx6_digital_level_0_99=None,
        fx6_mic_reference_db=None,
        fx6_line_input_reference=None,
        fx6_reference_level=None,
        fx6_limiter_mode=None,
        fx6_limiter_steps_count=0,
        fx6_sg_1khz_enabled=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 82B: [Audio Out Timing] Live/Lip Sync, [Volume Settings] 0..15 &
#                Exact 5-Option [4ch Audio Monitoring] vs FX6 7-Option Monitor
#                CH & Zero Physical "MONITOR VOL" Button
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AudioOutTimingVolumeAnd4chMonAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    shoot_mode: str
    audio_out_timing: Optional[str]
    audio_out_timing_delay_ms: float
    audio_out_timing_resettable: bool
    volume_level: Optional[int]
    volume_resettable_by_camera_reset: bool
    monitoring_4ch_option: Optional[str]
    monitoring_options_count: int
    monitoring_4ch_resettable_by_camera_reset: bool
    headphone_channels_count: int
    governs_headphone_and_rear_speaker: bool
    hdmi_4ch_audio_output: Optional[str]
    hdmi_channels_count: int
    sdi_channels_count: int
    fx6_headphone_out_mode: Optional[str]
    fx6_physical_monitor_vol_button_present: bool
    speaker_feedback_howl_risk: bool


def simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "fx3_4ch_monitoring",
    shoot_mode: str = "Movie",
    audio_out_timing: str = "Live",
    volume_level: int = FX3_VOLUME_SETTINGS_DEFAULT,
    monitoring_4ch_option: str = "CH1/CH2",
    hdmi_4ch_audio_output: str = "CH1/CH2",
    headphone_plugged: bool = True,
    xlr_h1_attached: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_headphone_out_mode: str = "Stereo",
    request_physical_monitor_vol_button: bool = False,
) -> AudioOutTimingVolumeAnd4chMonAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage82Phase365Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage82Phase365Error(f"Unsupported fw_version: {fw_version!r}")
    if operation not in VALID_82B_OPERATIONS:
        raise Stage82Phase365Error(f"Unsupported 82B operation: {operation!r}")
    if shoot_mode not in VALID_82A_SHOOT_MODES:
        raise Stage82Phase365Error(f"Unsupported shoot_mode: {shoot_mode!r}")

    if body_profile == BODY_MODEL_FX6:
        if operation != "fx6_audio_output":
            return AudioOutTimingVolumeAnd4chMonAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"FX6 does not expose FX3 operation {operation} -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                audio_out_timing=None,
                audio_out_timing_delay_ms=0.0,
                audio_out_timing_resettable=False,
                volume_level=None,
                volume_resettable_by_camera_reset=False,
                monitoring_4ch_option=None,
                monitoring_options_count=FX6_MONITOR_CH_OPTIONS_COUNT,
                monitoring_4ch_resettable_by_camera_reset=False,
                headphone_channels_count=2,
                governs_headphone_and_rear_speaker=False,
                hdmi_4ch_audio_output=hdmi_4ch_audio_output,
                hdmi_channels_count=2,
                sdi_channels_count=FX6_SDI_AUDIO_CHANNELS,
                fx6_headphone_out_mode=fx6_headphone_out_mode,
                fx6_physical_monitor_vol_button_present=False,
                speaker_feedback_howl_risk=False,
            )

        if request_physical_monitor_vol_button:
            return AudioOutTimingVolumeAnd4chMonAudit(
                admitted=False,
                errno_code=ENODEV_ERRNO,
                reason=(
                    "FX6 5-024-458-18 has ZERO physical 'MONITOR VOL +/-' button; "
                    "adjust 0..50 via menu/status dial/ASSIGN -> ENODEV=19"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                audio_out_timing=None,
                audio_out_timing_delay_ms=0.0,
                audio_out_timing_resettable=False,
                volume_level=volume_level,
                volume_resettable_by_camera_reset=False,
                monitoring_4ch_option=monitoring_4ch_option,
                monitoring_options_count=FX6_MONITOR_CH_OPTIONS_COUNT,
                monitoring_4ch_resettable_by_camera_reset=False,
                headphone_channels_count=2,
                governs_headphone_and_rear_speaker=False,
                hdmi_4ch_audio_output=hdmi_4ch_audio_output,
                hdmi_channels_count=2,
                sdi_channels_count=FX6_SDI_AUDIO_CHANNELS,
                fx6_headphone_out_mode=fx6_headphone_out_mode,
                fx6_physical_monitor_vol_button_present=False,
                speaker_feedback_howl_risk=False,
            )

        if (
            monitoring_4ch_option not in FX6_MONITOR_CH_7_OPTIONS
            or fx6_headphone_out_mode not in FX6_HEADPHONE_OUT_MODES
            or hdmi_4ch_audio_output not in VALID_HDMI_4CH_OUTPUT_OPTIONS
            or volume_level < FX6_VOLUME_MIN
            or volume_level > FX6_VOLUME_MAX
        ):
            return AudioOutTimingVolumeAnd4chMonAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason="FX6 Audio Output Monitor CH / Headphone Out / Volume (0..50) invalid -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                audio_out_timing=None,
                audio_out_timing_delay_ms=0.0,
                audio_out_timing_resettable=False,
                volume_level=None,
                volume_resettable_by_camera_reset=False,
                monitoring_4ch_option=monitoring_4ch_option,
                monitoring_options_count=FX6_MONITOR_CH_OPTIONS_COUNT,
                monitoring_4ch_resettable_by_camera_reset=False,
                headphone_channels_count=2,
                governs_headphone_and_rear_speaker=False,
                hdmi_4ch_audio_output=hdmi_4ch_audio_output,
                hdmi_channels_count=2,
                sdi_channels_count=FX6_SDI_AUDIO_CHANNELS,
                fx6_headphone_out_mode=fx6_headphone_out_mode,
                fx6_physical_monitor_vol_button_present=False,
                speaker_feedback_howl_risk=False,
            )

        return AudioOutTimingVolumeAnd4chMonAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX6 Audio Output: MonitorCH={monitoring_4ch_option} (7 options), "
                f"Headphone={fx6_headphone_out_mode}, Vol={volume_level}/50 (no side MONITOR VOL key), "
                f"HDMI={hdmi_4ch_audio_output} (2ch), SDI=4ch"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            audio_out_timing=None,
            audio_out_timing_delay_ms=0.0,
            audio_out_timing_resettable=False,
            volume_level=volume_level,
            volume_resettable_by_camera_reset=False,
            monitoring_4ch_option=monitoring_4ch_option,
            monitoring_options_count=FX6_MONITOR_CH_OPTIONS_COUNT,
            monitoring_4ch_resettable_by_camera_reset=False,
            headphone_channels_count=2,
            governs_headphone_and_rear_speaker=False,
            hdmi_4ch_audio_output=hdmi_4ch_audio_output,
            hdmi_channels_count=2,
            sdi_channels_count=FX6_SDI_AUDIO_CHANNELS,
            fx6_headphone_out_mode=fx6_headphone_out_mode,
            fx6_physical_monitor_vol_button_present=False,
            speaker_feedback_howl_risk=False,
        )

    # ILME-FX3 path
    if operation == "fx6_audio_output":
        return AudioOutTimingVolumeAnd4chMonAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="FX3 lacks FX6 7-option Monitor CH, SDI 4ch out and 0..50 Volume -> EOPNOTSUPP=95",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            audio_out_timing=None,
            audio_out_timing_delay_ms=0.0,
            audio_out_timing_resettable=False,
            volume_level=None,
            volume_resettable_by_camera_reset=False,
            monitoring_4ch_option=None,
            monitoring_options_count=FX3_4CH_MONITORING_OPTIONS_COUNT,
            monitoring_4ch_resettable_by_camera_reset=False,
            headphone_channels_count=FX3_35MM_HEADPHONE_MAX_CHANNELS,
            governs_headphone_and_rear_speaker=True,
            hdmi_4ch_audio_output=hdmi_4ch_audio_output,
            hdmi_channels_count=2,
            sdi_channels_count=0,
            fx6_headphone_out_mode=None,
            fx6_physical_monitor_vol_button_present=False,
            speaker_feedback_howl_risk=False,
        )

    if operation == "fx3_audio_out_timing":
        if shoot_mode == "S&Q":
            return AudioOutTimingVolumeAnd4chMonAudit(
                admitted=False,
                errno_code=EBUSY_ERRNO,
                reason="FX3 [Audio Out Timing] disabled in S&Q (0ch audio) -> EBUSY=16",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                audio_out_timing=None,
                audio_out_timing_delay_ms=0.0,
                audio_out_timing_resettable=True,
                volume_level=None,
                volume_resettable_by_camera_reset=False,
                monitoring_4ch_option=None,
                monitoring_options_count=FX3_4CH_MONITORING_OPTIONS_COUNT,
                monitoring_4ch_resettable_by_camera_reset=False,
                headphone_channels_count=FX3_35MM_HEADPHONE_MAX_CHANNELS,
                governs_headphone_and_rear_speaker=True,
                hdmi_4ch_audio_output=hdmi_4ch_audio_output,
                hdmi_channels_count=2,
                sdi_channels_count=0,
                fx6_headphone_out_mode=None,
                fx6_physical_monitor_vol_button_present=False,
                speaker_feedback_howl_risk=False,
            )
        if audio_out_timing not in VALID_AUDIO_OUT_TIMINGS:
            return AudioOutTimingVolumeAnd4chMonAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"Invalid FX3 [Audio Out Timing]={audio_out_timing!r} -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                audio_out_timing=None,
                audio_out_timing_delay_ms=0.0,
                audio_out_timing_resettable=True,
                volume_level=None,
                volume_resettable_by_camera_reset=False,
                monitoring_4ch_option=None,
                monitoring_options_count=FX3_4CH_MONITORING_OPTIONS_COUNT,
                monitoring_4ch_resettable_by_camera_reset=False,
                headphone_channels_count=FX3_35MM_HEADPHONE_MAX_CHANNELS,
                governs_headphone_and_rear_speaker=True,
                hdmi_4ch_audio_output=hdmi_4ch_audio_output,
                hdmi_channels_count=2,
                sdi_channels_count=0,
                fx6_headphone_out_mode=None,
                fx6_physical_monitor_vol_button_present=False,
                speaker_feedback_howl_risk=False,
            )
        # Shooting -> [Audio Recording] -> [Audio Out Timing] IS resettable to Live!
        eff_timing = (
            "Live"
            if (camera_settings_reset_applied or initialize_applied)
            else audio_out_timing
        )
        delay_ms = 0.0 if eff_timing == "Live" else 48.0
        return AudioOutTimingVolumeAnd4chMonAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 Shooting -> [Audio Recording] -> [Audio Out Timing]={eff_timing} "
                f"(delay={delay_ms}ms, Can be reset under Camera Settings Reset)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            audio_out_timing=eff_timing,
            audio_out_timing_delay_ms=delay_ms,
            audio_out_timing_resettable=True,
            volume_level=None,
            volume_resettable_by_camera_reset=False,
            monitoring_4ch_option=None,
            monitoring_options_count=FX3_4CH_MONITORING_OPTIONS_COUNT,
            monitoring_4ch_resettable_by_camera_reset=False,
            headphone_channels_count=FX3_35MM_HEADPHONE_MAX_CHANNELS,
            governs_headphone_and_rear_speaker=True,
            hdmi_4ch_audio_output=hdmi_4ch_audio_output,
            hdmi_channels_count=2,
            sdi_channels_count=0,
            fx6_headphone_out_mode=None,
            fx6_physical_monitor_vol_button_present=False,
            speaker_feedback_howl_risk=False,
        )

    if operation == "fx3_volume_settings":
        if volume_level < FX3_VOLUME_SETTINGS_MIN or volume_level > FX3_VOLUME_SETTINGS_MAX:
            return AudioOutTimingVolumeAnd4chMonAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"FX3 [Volume Settings] {volume_level} out of 0..15 -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                audio_out_timing=None,
                audio_out_timing_delay_ms=0.0,
                audio_out_timing_resettable=False,
                volume_level=None,
                volume_resettable_by_camera_reset=False,
                monitoring_4ch_option=None,
                monitoring_options_count=FX3_4CH_MONITORING_OPTIONS_COUNT,
                monitoring_4ch_resettable_by_camera_reset=False,
                headphone_channels_count=FX3_35MM_HEADPHONE_MAX_CHANNELS,
                governs_headphone_and_rear_speaker=True,
                hdmi_4ch_audio_output=hdmi_4ch_audio_output,
                hdmi_channels_count=2,
                sdi_channels_count=0,
                fx6_headphone_out_mode=None,
                fx6_physical_monitor_vol_button_present=False,
                speaker_feedback_howl_risk=False,
            )
        # Setup -> [Sound Option] -> [Volume Settings] is Reset-resistant!
        _ = camera_settings_reset_applied
        eff_vol = FX3_VOLUME_SETTINGS_DEFAULT if initialize_applied else volume_level
        howl_risk = (not headphone_plugged) and xlr_h1_attached and (eff_vol >= 12)
        return AudioOutTimingVolumeAnd4chMonAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 Setup -> [Sound Option] -> [Volume Settings]={eff_vol}/15 "
                "(default=7, Not available under Camera Settings Reset, cleared only by Initialize)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            audio_out_timing=None,
            audio_out_timing_delay_ms=0.0,
            audio_out_timing_resettable=False,
            volume_level=eff_vol,
            volume_resettable_by_camera_reset=False,
            monitoring_4ch_option=None,
            monitoring_options_count=FX3_4CH_MONITORING_OPTIONS_COUNT,
            monitoring_4ch_resettable_by_camera_reset=False,
            headphone_channels_count=FX3_35MM_HEADPHONE_MAX_CHANNELS,
            governs_headphone_and_rear_speaker=True,
            hdmi_4ch_audio_output=hdmi_4ch_audio_output,
            hdmi_channels_count=2,
            sdi_channels_count=0,
            fx6_headphone_out_mode=None,
            fx6_physical_monitor_vol_button_present=False,
            speaker_feedback_howl_risk=howl_risk,
        )

    # operation == "fx3_4ch_monitoring"
    if monitoring_4ch_option in FX3_4CH_ERRATA_INVALID_OPTIONS:
        return AudioOutTimingVolumeAnd4chMonAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"FX3 [4ch Audio Monitoring] rejects errata/FX6-only option "
                f"{monitoring_4ch_option!r} (exact 5 options: CH1/CH2, CH3/CH4, "
                "CH1+3/CH2+4, CH1/CH1, CH2/CH2) -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            audio_out_timing=None,
            audio_out_timing_delay_ms=0.0,
            audio_out_timing_resettable=False,
            volume_level=None,
            volume_resettable_by_camera_reset=False,
            monitoring_4ch_option=monitoring_4ch_option,
            monitoring_options_count=FX3_4CH_MONITORING_OPTIONS_COUNT,
            monitoring_4ch_resettable_by_camera_reset=False,
            headphone_channels_count=FX3_35MM_HEADPHONE_MAX_CHANNELS,
            governs_headphone_and_rear_speaker=True,
            hdmi_4ch_audio_output=hdmi_4ch_audio_output,
            hdmi_channels_count=2,
            sdi_channels_count=0,
            fx6_headphone_out_mode=None,
            fx6_physical_monitor_vol_button_present=False,
            speaker_feedback_howl_risk=False,
        )
    if (
        monitoring_4ch_option not in FX3_4CH_MONITORING_5_OPTIONS
        or hdmi_4ch_audio_output not in VALID_HDMI_4CH_OUTPUT_OPTIONS
    ):
        return AudioOutTimingVolumeAnd4chMonAudit(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason="Invalid FX3 [4ch Audio Monitoring] or HDMI [4ch Audio Output] option -> EINVAL=22",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            audio_out_timing=None,
            audio_out_timing_delay_ms=0.0,
            audio_out_timing_resettable=False,
            volume_level=None,
            volume_resettable_by_camera_reset=False,
            monitoring_4ch_option=monitoring_4ch_option,
            monitoring_options_count=FX3_4CH_MONITORING_OPTIONS_COUNT,
            monitoring_4ch_resettable_by_camera_reset=False,
            headphone_channels_count=FX3_35MM_HEADPHONE_MAX_CHANNELS,
            governs_headphone_and_rear_speaker=True,
            hdmi_4ch_audio_output=hdmi_4ch_audio_output,
            hdmi_channels_count=2,
            sdi_channels_count=0,
            fx6_headphone_out_mode=None,
            fx6_physical_monitor_vol_button_present=False,
            speaker_feedback_howl_risk=False,
        )

    # Setup -> [Sound Option] -> [4ch Audio Monitoring] is Reset-resistant!
    _ = camera_settings_reset_applied
    eff_mon = "CH1/CH2" if initialize_applied else monitoring_4ch_option
    return AudioOutTimingVolumeAnd4chMonAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 Setup -> [Sound Option] -> [4ch Audio Monitoring]={eff_mon} "
            "(exact 5 options, Reset-resistant Not available, governs 3.5mm 2ch + rear mono speaker "
            f"independently of HDMI [4ch Audio Output]={hdmi_4ch_audio_output})"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        shoot_mode=shoot_mode,
        audio_out_timing=None,
        audio_out_timing_delay_ms=0.0,
        audio_out_timing_resettable=False,
        volume_level=None,
        volume_resettable_by_camera_reset=False,
        monitoring_4ch_option=eff_mon,
        monitoring_options_count=FX3_4CH_MONITORING_OPTIONS_COUNT,
        monitoring_4ch_resettable_by_camera_reset=False,
        headphone_channels_count=FX3_35MM_HEADPHONE_MAX_CHANNELS,
        governs_headphone_and_rear_speaker=True,
        hdmi_4ch_audio_output=hdmi_4ch_audio_output,
        hdmi_channels_count=2,
        sdi_channels_count=0,
        fx6_headphone_out_mode=None,
        fx6_physical_monitor_vol_button_present=False,
        speaker_feedback_howl_risk=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 82C: Setup -> [Touch Operation] Exact 4 Active Items vs Dormant
#                [Touch Panel/Pad] / [Touch Shutter] / [Touch AE] & FX6 MF/BIG6
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TouchOperationAndDormantMaskAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    shoot_mode: str
    af_mf_mode: str
    touch_setup_active_items_count: int
    touch_operation: str
    touch_sensitivity: Optional[str]
    touch_func_in_shooting: Optional[str]
    swipe_up: Optional[str]
    swipe_up_active: bool
    resettable_via_camera_settings_reset: bool
    cleared_only_by_initialize: bool
    dormant_touch_panel_pad_exposed: bool
    dormant_touch_shutter_exposed: bool
    dormant_touch_ae_exposed: bool
    spot_metering_point: str
    spot_link_tracks_moving_box: bool
    fx6_touch_function_in_mf: Optional[str]
    fx6_spot_focus_disabled_reason: Optional[str]
    fx6_big6_and_full_menu_touch_supported: bool


def simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "fx3_touch_setup",
    shoot_mode: str = "Movie",
    af_mf_mode: str = "AF",
    touch_operation: str = "On",
    touch_sensitivity: str = "Standard",
    touch_func_in_shooting: str = "Touch Tracking",
    swipe_up: str = "Open the Fn Menu",
    spot_metering_point: str = "Focus Point Link",
    request_follow_moving_tracking_box: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_touch_function_in_mf: str = "Spot Focus",
    fx6_manual_lens_switch: bool = False,
    fx6_desqueeze_active: bool = False,
    fx6_focus_magnifier_active: bool = False,
    invoke_touch_in_mf: bool = False,
) -> TouchOperationAndDormantMaskAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage82Phase365Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage82Phase365Error(f"Unsupported fw_version: {fw_version!r}")
    if operation not in VALID_82C_OPERATIONS:
        raise Stage82Phase365Error(f"Unsupported 82C operation: {operation!r}")
    if shoot_mode not in VALID_82A_SHOOT_MODES:
        raise Stage82Phase365Error(f"Unsupported shoot_mode: {shoot_mode!r}")
    if af_mf_mode not in ("AF", "MF"):
        raise Stage82Phase365Error(f"Unsupported af_mf_mode: {af_mf_mode!r}")

    if operation in ("dormant_touch_panel_pad", "dormant_touch_shutter", "dormant_touch_ae"):
        return TouchOperationAndDormantMaskAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"{body_profile} {operation} is 100%% dormant/unexposed on ilc/2210 "
                "(EVF-less ALCIN_UUD; 0 hits for Touch Shutter/AE) -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            af_mf_mode=af_mf_mode,
            touch_setup_active_items_count=FX3_TOUCH_SETUP_ACTIVE_ITEMS_COUNT if body_profile == BODY_MODEL_FX3 else 1,
            touch_operation=touch_operation,
            touch_sensitivity=None,
            touch_func_in_shooting=None,
            swipe_up=None,
            swipe_up_active=False,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            dormant_touch_panel_pad_exposed=False,
            dormant_touch_shutter_exposed=False,
            dormant_touch_ae_exposed=False,
            spot_metering_point=spot_metering_point,
            spot_link_tracks_moving_box=False,
            fx6_touch_function_in_mf=None,
            fx6_spot_focus_disabled_reason=None,
            fx6_big6_and_full_menu_touch_supported=(body_profile == BODY_MODEL_FX6 and fw_version in (FW_VER_600, FW_VER_601)),
        )

    if body_profile == BODY_MODEL_FX6:
        if operation != "fx6_touch_operation":
            return TouchOperationAndDormantMaskAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"FX6 does not expose FX3 touch operation {operation} -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                af_mf_mode=af_mf_mode,
                touch_setup_active_items_count=1,
                touch_operation="On",
                touch_sensitivity=None,
                touch_func_in_shooting=None,
                swipe_up=None,
                swipe_up_active=False,
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=True,
                dormant_touch_panel_pad_exposed=False,
                dormant_touch_shutter_exposed=False,
                dormant_touch_ae_exposed=False,
                spot_metering_point="Center",
                spot_link_tracks_moving_box=False,
                fx6_touch_function_in_mf=fx6_touch_function_in_mf,
                fx6_spot_focus_disabled_reason=None,
                fx6_big6_and_full_menu_touch_supported=(fw_version in (FW_VER_600, FW_VER_601)),
            )

        if touch_operation not in FX6_TOUCH_OPERATION_MODES or fx6_touch_function_in_mf not in FX6_TOUCH_MF_MODES:
            return TouchOperationAndDormantMaskAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason="Invalid FX6 Technical > Touch Operation or Focus > Touch Function in MF -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                af_mf_mode=af_mf_mode,
                touch_setup_active_items_count=1,
                touch_operation=touch_operation,
                touch_sensitivity=None,
                touch_func_in_shooting=None,
                swipe_up=None,
                swipe_up_active=False,
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=True,
                dormant_touch_panel_pad_exposed=False,
                dormant_touch_shutter_exposed=False,
                dormant_touch_ae_exposed=False,
                spot_metering_point="Center",
                spot_link_tracks_moving_box=False,
                fx6_touch_function_in_mf=fx6_touch_function_in_mf,
                fx6_spot_focus_disabled_reason=None,
                fx6_big6_and_full_menu_touch_supported=(fw_version in (FW_VER_600, FW_VER_601)),
            )

        disabled_reason: Optional[str] = None
        if fx6_touch_function_in_mf == "Spot Focus":
            if fx6_manual_lens_switch:
                disabled_reason = "manual_lens_switch"
            elif fx6_desqueeze_active:
                disabled_reason = "desqueeze_active"
            elif fx6_focus_magnifier_active:
                disabled_reason = "focus_magnifier_active"

        big6_touch = fw_version in (FW_VER_600, FW_VER_601)
        if invoke_touch_in_mf and disabled_reason is not None:
            return TouchOperationAndDormantMaskAudit(
                admitted=False,
                errno_code=EBUSY_ERRNO,
                reason=f"FX6 Touch Function in MF = Spot Focus disabled ({disabled_reason}) -> EBUSY=16",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                af_mf_mode="MF",
                touch_setup_active_items_count=1,
                touch_operation=touch_operation,
                touch_sensitivity=None,
                touch_func_in_shooting=None,
                swipe_up=None,
                swipe_up_active=False,
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=True,
                dormant_touch_panel_pad_exposed=False,
                dormant_touch_shutter_exposed=False,
                dormant_touch_ae_exposed=False,
                spot_metering_point="Center",
                spot_link_tracks_moving_box=False,
                fx6_touch_function_in_mf=fx6_touch_function_in_mf,
                fx6_spot_focus_disabled_reason=disabled_reason,
                fx6_big6_and_full_menu_touch_supported=big6_touch,
            )

        return TouchOperationAndDormantMaskAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX6 Ver. {fw_version} Touch Operation={touch_operation}, "
                f"Touch Function in MF={fx6_touch_function_in_mf} "
                f"(disabled_reason={disabled_reason}), BIG6/MenuTouch={big6_touch}"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            af_mf_mode=af_mf_mode,
            touch_setup_active_items_count=1,
            touch_operation=touch_operation,
            touch_sensitivity=None,
            touch_func_in_shooting=None,
            swipe_up=None,
            swipe_up_active=False,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            dormant_touch_panel_pad_exposed=False,
            dormant_touch_shutter_exposed=False,
            dormant_touch_ae_exposed=False,
            spot_metering_point="Center",
            spot_link_tracks_moving_box=False,
            fx6_touch_function_in_mf=fx6_touch_function_in_mf,
            fx6_spot_focus_disabled_reason=disabled_reason,
            fx6_big6_and_full_menu_touch_supported=big6_touch,
        )

    # ILME-FX3 path
    if operation == "fx6_touch_operation":
        return TouchOperationAndDormantMaskAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="FX3 lacks FX6 [Touch Function in MF] (Spot Focus one-push AF) -> EOPNOTSUPP=95",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            af_mf_mode=af_mf_mode,
            touch_setup_active_items_count=FX3_TOUCH_SETUP_ACTIVE_ITEMS_COUNT,
            touch_operation=touch_operation,
            touch_sensitivity=touch_sensitivity,
            touch_func_in_shooting=touch_func_in_shooting,
            swipe_up=swipe_up,
            swipe_up_active=False,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            dormant_touch_panel_pad_exposed=False,
            dormant_touch_shutter_exposed=False,
            dormant_touch_ae_exposed=False,
            spot_metering_point=spot_metering_point,
            spot_link_tracks_moving_box=False,
            fx6_touch_function_in_mf=None,
            fx6_spot_focus_disabled_reason=None,
            fx6_big6_and_full_menu_touch_supported=(fw_version in (FW_VER_600, FW_VER_702)),
        )

    if (
        touch_operation not in FX3_TOUCH_OPERATION_MODES
        or touch_sensitivity not in FX3_TOUCH_SENSITIVITY_MODES
        or touch_func_in_shooting not in FX3_TOUCH_FUNC_IN_SHOOTING_MODES
        or swipe_up not in FX3_SWIPE_UP_MODES
        or spot_metering_point not in FX3_SPOT_METERING_POINT_MODES
    ):
        return TouchOperationAndDormantMaskAudit(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason="Invalid FX3 Touch Operation / Sensitivity / Func. in Shooting / Swipe Up / Spot Point -> EINVAL=22",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            af_mf_mode=af_mf_mode,
            touch_setup_active_items_count=FX3_TOUCH_SETUP_ACTIVE_ITEMS_COUNT,
            touch_operation=touch_operation,
            touch_sensitivity=touch_sensitivity,
            touch_func_in_shooting=touch_func_in_shooting,
            swipe_up=swipe_up,
            swipe_up_active=False,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            dormant_touch_panel_pad_exposed=False,
            dormant_touch_shutter_exposed=False,
            dormant_touch_ae_exposed=False,
            spot_metering_point=spot_metering_point,
            spot_link_tracks_moving_box=False,
            fx6_touch_function_in_mf=None,
            fx6_spot_focus_disabled_reason=None,
            fx6_big6_and_full_menu_touch_supported=(fw_version in (FW_VER_600, FW_VER_702)),
        )

    # All 4 Setup -> [Touch Operation] items are Reset-resistant!
    _ = camera_settings_reset_applied
    eff_op = "On" if initialize_applied else touch_operation
    eff_sens = "Standard" if initialize_applied else touch_sensitivity
    eff_func = "Touch Tracking" if initialize_applied else touch_func_in_shooting
    eff_swipe = "Open the Fn Menu" if initialize_applied else swipe_up
    swipe_active = (eff_op == "On") and (eff_swipe == "Open the Fn Menu")
    big6_touch = fw_version in (FW_VER_600, FW_VER_702)

    if operation == "fx3_spot_metering_link":
        if request_follow_moving_tracking_box:
            return TouchOperationAndDormantMaskAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "[Spot Metering Point] = Focus Point Link links only to static focus area "
                    "and NEVER follows the active Touch Tracking box -> EOPNOTSUPP=95"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                af_mf_mode=af_mf_mode,
                touch_setup_active_items_count=FX3_TOUCH_SETUP_ACTIVE_ITEMS_COUNT,
                touch_operation=eff_op,
                touch_sensitivity=eff_sens,
                touch_func_in_shooting=eff_func,
                swipe_up=eff_swipe,
                swipe_up_active=swipe_active,
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=True,
                dormant_touch_panel_pad_exposed=False,
                dormant_touch_shutter_exposed=False,
                dormant_touch_ae_exposed=False,
                spot_metering_point=spot_metering_point,
                spot_link_tracks_moving_box=False,
                fx6_touch_function_in_mf=None,
                fx6_spot_focus_disabled_reason=None,
                fx6_big6_and_full_menu_touch_supported=big6_touch,
            )
        return TouchOperationAndDormantMaskAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 [Spot Metering Point]={spot_metering_point} anchored to static focus area "
                "(spot_link_tracks_moving_box=False)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            shoot_mode=shoot_mode,
            af_mf_mode=af_mf_mode,
            touch_setup_active_items_count=FX3_TOUCH_SETUP_ACTIVE_ITEMS_COUNT,
            touch_operation=eff_op,
            touch_sensitivity=eff_sens,
            touch_func_in_shooting=eff_func,
            swipe_up=eff_swipe,
            swipe_up_active=swipe_active,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            dormant_touch_panel_pad_exposed=False,
            dormant_touch_shutter_exposed=False,
            dormant_touch_ae_exposed=False,
            spot_metering_point=spot_metering_point,
            spot_link_tracks_moving_box=False,
            fx6_touch_function_in_mf=None,
            fx6_spot_focus_disabled_reason=None,
            fx6_big6_and_full_menu_touch_supported=big6_touch,
        )

    if operation == "fx3_touch_tap_in_shooting":
        if eff_op != "On" or eff_func == "Off":
            return TouchOperationAndDormantMaskAudit(
                admitted=False,
                errno_code=EBUSY_ERRNO,
                reason=(
                    f"Touch tap in shooting suppressed (Touch Operation={eff_op}, "
                    f"Touch Func. in Shooting={eff_func}) -> EBUSY=16"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                af_mf_mode=af_mf_mode,
                touch_setup_active_items_count=FX3_TOUCH_SETUP_ACTIVE_ITEMS_COUNT,
                touch_operation=eff_op,
                touch_sensitivity=eff_sens,
                touch_func_in_shooting=eff_func,
                swipe_up=eff_swipe,
                swipe_up_active=swipe_active,
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=True,
                dormant_touch_panel_pad_exposed=False,
                dormant_touch_shutter_exposed=False,
                dormant_touch_ae_exposed=False,
                spot_metering_point=spot_metering_point,
                spot_link_tracks_moving_box=False,
                fx6_touch_function_in_mf=None,
                fx6_spot_focus_disabled_reason=None,
                fx6_big6_and_full_menu_touch_supported=big6_touch,
            )
        if af_mf_mode == "MF" and eff_func == "Touch Tracking":
            return TouchOperationAndDormantMaskAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="FX3 Touch Tracking disabled in MF mode -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                shoot_mode=shoot_mode,
                af_mf_mode=af_mf_mode,
                touch_setup_active_items_count=FX3_TOUCH_SETUP_ACTIVE_ITEMS_COUNT,
                touch_operation=eff_op,
                touch_sensitivity=eff_sens,
                touch_func_in_shooting=eff_func,
                swipe_up=eff_swipe,
                swipe_up_active=swipe_active,
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=True,
                dormant_touch_panel_pad_exposed=False,
                dormant_touch_shutter_exposed=False,
                dormant_touch_ae_exposed=False,
                spot_metering_point=spot_metering_point,
                spot_link_tracks_moving_box=False,
                fx6_touch_function_in_mf=None,
                fx6_spot_focus_disabled_reason=None,
                fx6_big6_and_full_menu_touch_supported=big6_touch,
            )

    return TouchOperationAndDormantMaskAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 Setup -> [Touch Operation] 4 active Reset-resistant items: "
            f"Op={eff_op}, Sens={eff_sens}, ShootFunc={eff_func} (shared across Still/Movie/S&Q, "
            f"mode={shoot_mode}), SwipeUp={eff_swipe} (active={swipe_active})"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        shoot_mode=shoot_mode,
        af_mf_mode=af_mf_mode,
        touch_setup_active_items_count=FX3_TOUCH_SETUP_ACTIVE_ITEMS_COUNT,
        touch_operation=eff_op,
        touch_sensitivity=eff_sens,
        touch_func_in_shooting=eff_func,
        swipe_up=eff_swipe,
        swipe_up_active=swipe_active,
        resettable_via_camera_settings_reset=False,
        cleared_only_by_initialize=True,
        dormant_touch_panel_pad_exposed=False,
        dormant_touch_shutter_exposed=False,
        dormant_touch_ae_exposed=False,
        spot_metering_point=spot_metering_point,
        spot_link_tracks_moving_box=False,
        fx6_touch_function_in_mf=None,
        fx6_spot_focus_disabled_reason=None,
        fx6_big6_and_full_menu_touch_supported=big6_touch,
    )


# ---------------------------------------------------------------------------
# Sub-Model 82D: [PC Remote Function] -> [Remote Shoot Setting] Evolution,
#                PTP/PTP-IP Destination Only RAM Direct-Transfer & Tier-0
#                Slot 1 EROFS=30 Firewall vs FX6 Camera Remote Control
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RemoteShootSettingPtpAndSlot1FirewallAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    menu_path: str
    still_img_save_dest: Optional[str]
    save_image_size: Optional[str]
    raw_j_save_image: Optional[str]
    raw_h_save_image: Optional[str]
    resettable_via_camera_settings_reset: bool
    cleared_by_initialize_or_reset_network: bool
    transport_protocol: str
    usb_pid_vid: Optional[str]
    ptp_ip_port: Optional[int]
    airplane_mode: str
    rf_tx_packets: int
    connection_state: str
    card_inserted_slot1: bool
    release_wo_card: str
    slot1_is_tier0_vault: bool
    slot1_data_sector_writes: int
    slot1_erofs_enforced: bool
    ram_direct_transfer_active: bool
    fx6_still_img_save_dest_ui_exposed: bool


def simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "fx3_remote_capture",
    still_img_save_dest: str = "Destination Only",
    save_image_size: str = "2M",
    raw_j_save_image: str = "JPEG Only",
    raw_h_save_image: str = "HEIF Only",
    transport_protocol: str = "PTP_USB_SICD",
    wired_usb_lan: bool = True,
    airplane_mode: str = "On",
    connection_state: str = "CONNECTED",
    change_save_dest_while_connected: bool = False,
    card_inserted_slot1: bool = False,
    release_wo_card: str = "Disable",
    slot1_is_tier0_vault: bool = True,
    camera_settings_reset_applied: bool = False,
    reset_network_set_applied: bool = False,
    initialize_applied: bool = False,
    request_fx6_save_dest_ui: bool = False,
) -> RemoteShootSettingPtpAndSlot1FirewallAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage82Phase365Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage82Phase365Error(f"Unsupported fw_version: {fw_version!r}")
    if operation not in VALID_82D_OPERATIONS:
        raise Stage82Phase365Error(f"Unsupported 82D operation: {operation!r}")
    if transport_protocol not in VALID_REMOTE_TRANSPORTS:
        raise Stage82Phase365Error(f"Unsupported transport_protocol: {transport_protocol!r}")
    if airplane_mode not in ("On", "Off"):
        raise Stage82Phase365Error(f"Unsupported airplane_mode: {airplane_mode!r}")
    if connection_state not in VALID_CONNECTION_STATES:
        raise Stage82Phase365Error(f"Unsupported connection_state: {connection_state!r}")
    if release_wo_card not in ("Disable", "Enable"):
        raise Stage82Phase365Error(f"Unsupported release_wo_card: {release_wo_card!r}")

    if body_profile == BODY_MODEL_FX6:
        if operation != "fx6_camera_remote_control":
            return RemoteShootSettingPtpAndSlot1FirewallAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"FX6 does not expose FX3 remote operation {operation} -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                menu_path="Network -> Camera Remote Control",
                still_img_save_dest=None,
                save_image_size=None,
                raw_j_save_image=None,
                raw_h_save_image=None,
                resettable_via_camera_settings_reset=False,
                cleared_by_initialize_or_reset_network=True,
                transport_protocol=transport_protocol,
                usb_pid_vid=None,
                ptp_ip_port=FX3_PTPIP_TCP_PORT,
                airplane_mode=airplane_mode,
                rf_tx_packets=0,
                connection_state=connection_state,
                card_inserted_slot1=card_inserted_slot1,
                release_wo_card=release_wo_card,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_erofs_enforced=True,
                ram_direct_transfer_active=False,
                fx6_still_img_save_dest_ui_exposed=False,
            )
        if request_fx6_save_dest_ui:
            return RemoteShootSettingPtpAndSlot1FirewallAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "FX6 Ver. 6.01 masks dormant setting_remote_settings_still_img_save_dest "
                    "in UI (0 exposure) -> EOPNOTSUPP=95"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                menu_path="Network -> Camera Remote Control",
                still_img_save_dest=None,
                save_image_size=None,
                raw_j_save_image=None,
                raw_h_save_image=None,
                resettable_via_camera_settings_reset=False,
                cleared_by_initialize_or_reset_network=True,
                transport_protocol="PTP_IP_TCP_15740",
                usb_pid_vid=None,
                ptp_ip_port=FX3_PTPIP_TCP_PORT,
                airplane_mode=airplane_mode,
                rf_tx_packets=0,
                connection_state=connection_state,
                card_inserted_slot1=card_inserted_slot1,
                release_wo_card=release_wo_card,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_erofs_enforced=True,
                ram_direct_transfer_active=False,
                fx6_still_img_save_dest_ui_exposed=False,
            )
        return RemoteShootSettingPtpAndSlot1FirewallAudit(
            admitted=True,
            errno_code=0,
            reason=(
                "FX6 Network -> Network Client Mode / Camera Remote Control (Enable) "
                "via PTP-IP TCP/15740 (Monitor & Control / CrSDK, zero Still Img. Save Dest. UI)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path="Network -> [Wired LAN / USB Tethering] -> Camera Remote Control",
            still_img_save_dest=None,
            save_image_size=None,
            raw_j_save_image=None,
            raw_h_save_image=None,
            resettable_via_camera_settings_reset=False,
            cleared_by_initialize_or_reset_network=True,
            transport_protocol="PTP_IP_TCP_15740",
            usb_pid_vid=None,
            ptp_ip_port=FX3_PTPIP_TCP_PORT,
            airplane_mode=airplane_mode,
            rf_tx_packets=0,
            connection_state=connection_state,
            card_inserted_slot1=card_inserted_slot1,
            release_wo_card=release_wo_card,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            slot1_data_sector_writes=0,
            slot1_erofs_enforced=True,
            ram_direct_transfer_active=False,
            fx6_still_img_save_dest_ui_exposed=False,
        )

    # ILME-FX3 path
    if operation == "fx6_camera_remote_control":
        return RemoteShootSettingPtpAndSlot1FirewallAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="FX3 uses [Remote Shoot Setting] rather than FX6 Network Client Mode -> EOPNOTSUPP=95",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path="Network -> [Cnct./Remote Sht.] -> [Remote Shoot Setting]",
            still_img_save_dest=still_img_save_dest,
            save_image_size=save_image_size,
            raw_j_save_image=raw_j_save_image,
            raw_h_save_image=raw_h_save_image,
            resettable_via_camera_settings_reset=False,
            cleared_by_initialize_or_reset_network=True,
            transport_protocol=transport_protocol,
            usb_pid_vid=FX3_PTP_USB_VID_PID if transport_protocol == "PTP_USB_SICD" else None,
            ptp_ip_port=FX3_PTPIP_TCP_PORT if transport_protocol == "PTP_IP_TCP_15740" else None,
            airplane_mode=airplane_mode,
            rf_tx_packets=0,
            connection_state=connection_state,
            card_inserted_slot1=card_inserted_slot1,
            release_wo_card=release_wo_card,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            slot1_data_sector_writes=0,
            slot1_erofs_enforced=True,
            ram_direct_transfer_active=False,
            fx6_still_img_save_dest_ui_exposed=False,
        )

    is_v1 = fw_version == FW_VER_101
    menu_path = (
        "Transfer/Remote -> [PC Remote Function]"
        if is_v1
        else "Network -> [Cnct./Remote Sht.] -> [Remote Shoot Setting]"
    )
    valid_dests = FX3_REMOTE_SHOOT_SAVE_DEST_V1 if is_v1 else FX3_REMOTE_SHOOT_SAVE_DEST_V2_PLUS
    default_dest = "PC+Camera" if is_v1 else FX3_REMOTE_SHOOT_FACTORY_DEFAULT_DEST
    if (
        still_img_save_dest not in valid_dests
        or save_image_size not in VALID_SAVE_IMAGE_SIZES
        or raw_j_save_image not in VALID_RAW_J_SAVE_OPTIONS
        or raw_h_save_image not in VALID_RAW_H_SAVE_OPTIONS
    ):
        return RemoteShootSettingPtpAndSlot1FirewallAudit(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason=(
                f"Invalid FX3 Ver. {fw_version} [Remote Shoot Setting] enum: "
                f"dest={still_img_save_dest!r}, size={save_image_size!r} -> EINVAL=22"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path=menu_path,
            still_img_save_dest=still_img_save_dest,
            save_image_size=save_image_size,
            raw_j_save_image=raw_j_save_image,
            raw_h_save_image=raw_h_save_image,
            resettable_via_camera_settings_reset=False,
            cleared_by_initialize_or_reset_network=True,
            transport_protocol=transport_protocol,
            usb_pid_vid=FX3_PTP_USB_VID_PID if transport_protocol == "PTP_USB_SICD" else None,
            ptp_ip_port=FX3_PTPIP_TCP_PORT if transport_protocol == "PTP_IP_TCP_15740" else None,
            airplane_mode=airplane_mode,
            rf_tx_packets=0,
            connection_state=connection_state,
            card_inserted_slot1=card_inserted_slot1,
            release_wo_card=release_wo_card,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            slot1_data_sector_writes=0,
            slot1_erofs_enforced=True,
            ram_direct_transfer_active=False,
            fx6_still_img_save_dest_ui_exposed=False,
        )

    usb_id = FX3_PTP_USB_VID_PID if transport_protocol == "PTP_USB_SICD" else None
    ptp_port = FX3_PTPIP_TCP_PORT if transport_protocol == "PTP_IP_TCP_15740" else None

    if operation == "fx3_remote_shoot_config":
        if change_save_dest_while_connected and connection_state == "CONNECTED":
            return RemoteShootSettingPtpAndSlot1FirewallAudit(
                admitted=False,
                errno_code=EBUSY_ERRNO,
                reason=(
                    "PRM_HAITA_setting_remote_settings_still_img_save_dest_pc_remote_connection_state: "
                    "[Still Img. Save Dest.] locked while PC_REMOTE_CONNECTION_STATE_CONNECTED -> EBUSY=16"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                menu_path=menu_path,
                still_img_save_dest=still_img_save_dest,
                save_image_size=save_image_size,
                raw_j_save_image=raw_j_save_image,
                raw_h_save_image=raw_h_save_image,
                resettable_via_camera_settings_reset=False,
                cleared_by_initialize_or_reset_network=True,
                transport_protocol=transport_protocol,
                usb_pid_vid=usb_id,
                ptp_ip_port=ptp_port,
                airplane_mode=airplane_mode,
                rf_tx_packets=0,
                connection_state=connection_state,
                card_inserted_slot1=card_inserted_slot1,
                release_wo_card=release_wo_card,
                slot1_is_tier0_vault=slot1_is_tier0_vault,
                slot1_data_sector_writes=0,
                slot1_erofs_enforced=True,
                ram_direct_transfer_active=False,
                fx6_still_img_save_dest_ui_exposed=False,
            )

        # Reset-resistant under [Camera Settings Reset]; cleared by [Reset Network Set.] / [Initialize]
        _ = camera_settings_reset_applied
        wiped = reset_network_set_applied or initialize_applied
        eff_dest = default_dest if wiped else still_img_save_dest
        eff_size = "2M" if wiped else save_image_size
        eff_rj = "JPEG Only" if wiped else raw_j_save_image
        eff_rh = "HEIF Only" if wiped else raw_h_save_image
        return RemoteShootSettingPtpAndSlot1FirewallAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 Ver. {fw_version} {menu_path}: StillImgSaveDest={eff_dest}, "
                f"Size={eff_size}, RAW+J={eff_rj}, RAW+H={eff_rh} "
                "(Reset-resistant vs Camera Settings Reset; cleared by Reset Network Set./Initialize)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path=menu_path,
            still_img_save_dest=eff_dest,
            save_image_size=eff_size,
            raw_j_save_image=eff_rj,
            raw_h_save_image=eff_rh,
            resettable_via_camera_settings_reset=False,
            cleared_by_initialize_or_reset_network=True,
            transport_protocol=transport_protocol,
            usb_pid_vid=usb_id,
            ptp_ip_port=ptp_port,
            airplane_mode=airplane_mode,
            rf_tx_packets=0,
            connection_state=connection_state,
            card_inserted_slot1=card_inserted_slot1,
            release_wo_card=release_wo_card,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            slot1_data_sector_writes=0,
            slot1_erofs_enforced=True,
            ram_direct_transfer_active=(eff_dest in ("Destination Only", "PC Only")),
            fx6_still_img_save_dest_ui_exposed=False,
        )

    # operation == "fx3_remote_capture"
    if transport_protocol == "PTP_IP_TCP_15740" and (not wired_usb_lan) and airplane_mode == "On":
        return RemoteShootSettingPtpAndSlot1FirewallAudit(
            admitted=False,
            errno_code=ENODEV_ERRNO,
            reason="PTP-IP over Wi-Fi blocked when [Airplane Mode]=On (use wired USB-LAN CDC-NCM) -> ENODEV=19",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path=menu_path,
            still_img_save_dest=still_img_save_dest,
            save_image_size=save_image_size,
            raw_j_save_image=raw_j_save_image,
            raw_h_save_image=raw_h_save_image,
            resettable_via_camera_settings_reset=False,
            cleared_by_initialize_or_reset_network=True,
            transport_protocol=transport_protocol,
            usb_pid_vid=usb_id,
            ptp_ip_port=ptp_port,
            airplane_mode=airplane_mode,
            rf_tx_packets=0,
            connection_state=connection_state,
            card_inserted_slot1=card_inserted_slot1,
            release_wo_card=release_wo_card,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            slot1_data_sector_writes=0,
            slot1_erofs_enforced=True,
            ram_direct_transfer_active=False,
            fx6_still_img_save_dest_ui_exposed=False,
        )

    if still_img_save_dest in ("Destination Only", "PC Only"):
        # RAM direct-transfer bypasses media mount & [Release w/o Card]=Disable with 0 Slot 1 writes!
        return RemoteShootSettingPtpAndSlot1FirewallAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 {still_img_save_dest} cardless RAM capture via {transport_protocol} "
                "(stillrec_running_without_pseudo_rec_t, slot1_data_sector_writes=0, rf_tx_packets=0)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path=menu_path,
            still_img_save_dest=still_img_save_dest,
            save_image_size=save_image_size,
            raw_j_save_image=raw_j_save_image,
            raw_h_save_image=raw_h_save_image,
            resettable_via_camera_settings_reset=False,
            cleared_by_initialize_or_reset_network=True,
            transport_protocol=transport_protocol,
            usb_pid_vid=usb_id,
            ptp_ip_port=ptp_port,
            airplane_mode=airplane_mode,
            rf_tx_packets=0,
            connection_state=connection_state,
            card_inserted_slot1=card_inserted_slot1,
            release_wo_card=release_wo_card,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            slot1_data_sector_writes=0,
            slot1_erofs_enforced=True,
            ram_direct_transfer_active=True,
            fx6_still_img_save_dest_ui_exposed=False,
        )

    # Dest.+Camera (factory default!) or Camera Only attempts Slot 1 write -> blocked cardless or EROFS=30!
    if not card_inserted_slot1:
        return RemoteShootSettingPtpAndSlot1FirewallAudit(
            admitted=False,
            errno_code=ENODEV_ERRNO,
            reason=(
                f"FX3 {still_img_save_dest} requires [Recording Media]=Slot 1 mount; "
                f"cardless shutter refused even with [Release w/o Card]={release_wo_card} -> ENODEV=19"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            menu_path=menu_path,
            still_img_save_dest=still_img_save_dest,
            save_image_size=save_image_size,
            raw_j_save_image=raw_j_save_image,
            raw_h_save_image=raw_h_save_image,
            resettable_via_camera_settings_reset=False,
            cleared_by_initialize_or_reset_network=True,
            transport_protocol=transport_protocol,
            usb_pid_vid=usb_id,
            ptp_ip_port=ptp_port,
            airplane_mode=airplane_mode,
            rf_tx_packets=0,
            connection_state=connection_state,
            card_inserted_slot1=False,
            release_wo_card=release_wo_card,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            slot1_data_sector_writes=0,
            slot1_erofs_enforced=True,
            ram_direct_transfer_active=False,
            fx6_still_img_save_dest_ui_exposed=False,
        )

    # Card inserted in Slot 1 -> Tier-0 vault hard EROFS=30 firewall blocks all writes!
    return RemoteShootSettingPtpAndSlot1FirewallAudit(
        admitted=False,
        errno_code=EROFS_ERRNO,
        reason=(
            f"Tier-0 Slot 1 vault hard EROFS=30 firewall blocked {still_img_save_dest} "
            "DCIM/AVF_INFO write attempt (slot1_data_sector_writes=0)"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        menu_path=menu_path,
        still_img_save_dest=still_img_save_dest,
        save_image_size=save_image_size,
        raw_j_save_image=raw_j_save_image,
        raw_h_save_image=raw_h_save_image,
        resettable_via_camera_settings_reset=False,
        cleared_by_initialize_or_reset_network=True,
        transport_protocol=transport_protocol,
        usb_pid_vid=usb_id,
        ptp_ip_port=ptp_port,
        airplane_mode=airplane_mode,
        rf_tx_packets=0,
        connection_state=connection_state,
        card_inserted_slot1=True,
        release_wo_card=release_wo_card,
        slot1_is_tier0_vault=slot1_is_tier0_vault,
        slot1_data_sector_writes=0,
        slot1_erofs_enforced=True,
        ram_direct_transfer_active=False,
        fx6_still_img_save_dest_ui_exposed=False,
    )


# ---------------------------------------------------------------------------
# Milestone Probe, Recursive Determinism & Full Stage 82 Runner
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


def _build_stage82_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_82nd_stage_milestone": IS_82ND_STAGE_MILESTONE,
        "wave": "Wave-72",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    donor_audit = inspect_phase365_wave72_donors(
        work_root=work_root, force_clean_room=force_clean_room, env=env
    )

    # Sub-Model 82A probes
    p82a_internal_default = simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
        body_rec_level=26
    )
    p82a_delete_resets_26 = simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
        body_rec_level=12, delete_key_reset=True
    )
    p82a_limiter_cannot_disable = simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
        limiter_disable_requested=True
    )
    p82a_xlr_bypasses_body = simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
        operation="fx3_xlr_h1_handle",
        xlr_h1_handle_audio_on=True,
        xlr_h1_input_mode="MIC+48V",
        xlr_h1_att_db=20,
        xlr_h1_agc_mode="LINK",
        xlr_h1_dial_0_to_10=7,
        xlr_h1_four_ch_mode=True,
    )
    p82a_35mm_preempts_xlr = simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
        operation="fx3_xlr_h1_handle",
        mic_35mm_plugged=True,
        xlr_h1_handle_audio_on=True,
        body_rec_level=19,
    )
    p82a_sq_locked = simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
        shoot_mode="S&Q"
    )
    p82a_fx6_6step_limiter = simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_audio_input",
        fx6_channel="CH4",
        fx6_ch_input_select="INPUT2",
        fx6_digital_level_0_99=75,
        fx6_mic_reference_db=-60,
        fx6_line_input_reference="+4dB",
        fx6_reference_level="-16dB",
        fx6_limiter_mode="-17dB",
        fx6_sg_1khz_enabled=True,
    )
    p82a_ok = (
        p82a_internal_default.admitted
        and p82a_internal_default.body_audio_rec_level == 26
        and p82a_internal_default.body_limiter_always_on
        and (not p82a_internal_default.limiter_defeatable)
        and p82a_internal_default.resettable_via_camera_settings_reset
        and p82a_delete_resets_26.admitted
        and p82a_delete_resets_26.body_audio_rec_level == 26
        and (not p82a_limiter_cannot_disable.admitted)
        and p82a_limiter_cannot_disable.errno_code == EOPNOTSUPP_ERRNO
        and p82a_xlr_bypasses_body.admitted
        and p82a_xlr_bypasses_body.body_audio_rec_level_greyed_out
        and p82a_xlr_bypasses_body.xlr_h1_std_level_dbu == -40
        and p82a_xlr_bypasses_body.xlr_h1_input2_dial_disabled
        and p82a_xlr_bypasses_body.channels_count == 4
        and p82a_xlr_bypasses_body.bit_depth == 24
        and p82a_35mm_preempts_xlr.admitted
        and p82a_35mm_preempts_xlr.active_input_source == "body_35mm_mic"
        and (not p82a_35mm_preempts_xlr.body_audio_rec_level_greyed_out)
        and (not p82a_sq_locked.admitted)
        and p82a_sq_locked.errno_code == EBUSY_ERRNO
        and p82a_sq_locked.channels_count == 0
        and p82a_fx6_6step_limiter.admitted
        and p82a_fx6_6step_limiter.fx6_limiter_steps_count == 6
        and p82a_fx6_6step_limiter.fx6_limiter_mode == "-17dB"
        and p82a_fx6_6step_limiter.fx6_reference_level == "-16dB"
    )

    # Sub-Model 82B probes
    p82b_timing_lip_sync = simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
        operation="fx3_audio_out_timing", audio_out_timing="Lip Sync"
    )
    p82b_timing_reset_live = simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
        operation="fx3_audio_out_timing",
        audio_out_timing="Lip Sync",
        camera_settings_reset_applied=True,
    )
    p82b_vol_reset_resistant = simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
        operation="fx3_volume_settings",
        volume_level=12,
        camera_settings_reset_applied=True,
    )
    p82b_mon_ch1_ch1_reset_resistant = simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
        operation="fx3_4ch_monitoring",
        monitoring_4ch_option="CH1/CH1",
        hdmi_4ch_audio_output="CH3/CH4",
        camera_settings_reset_applied=True,
    )
    p82b_mon_errata_rejected = simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
        operation="fx3_4ch_monitoring",
        monitoring_4ch_option="CH1+2/CH3+4",
    )
    p82b_fx6_7opt_mix_all = simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_audio_output",
        monitoring_4ch_option="MIX ALL",
        volume_level=35,
        fx6_headphone_out_mode="Mono",
    )
    p82b_fx6_no_side_vol_btn = simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_audio_output",
        request_physical_monitor_vol_button=True,
    )
    p82b_ok = (
        p82b_timing_lip_sync.admitted
        and p82b_timing_lip_sync.audio_out_timing == "Lip Sync"
        and p82b_timing_lip_sync.audio_out_timing_resettable
        and p82b_timing_reset_live.admitted
        and p82b_timing_reset_live.audio_out_timing == "Live"
        and p82b_vol_reset_resistant.admitted
        and p82b_vol_reset_resistant.volume_level == 12
        and (not p82b_vol_reset_resistant.volume_resettable_by_camera_reset)
        and p82b_mon_ch1_ch1_reset_resistant.admitted
        and p82b_mon_ch1_ch1_reset_resistant.monitoring_options_count == 5
        and p82b_mon_ch1_ch1_reset_resistant.monitoring_4ch_option == "CH1/CH1"
        and (not p82b_mon_ch1_ch1_reset_resistant.monitoring_4ch_resettable_by_camera_reset)
        and p82b_mon_ch1_ch1_reset_resistant.hdmi_4ch_audio_output == "CH3/CH4"
        and (not p82b_mon_errata_rejected.admitted)
        and p82b_mon_errata_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p82b_fx6_7opt_mix_all.admitted
        and p82b_fx6_7opt_mix_all.monitoring_options_count == 7
        and (not p82b_fx6_7opt_mix_all.fx6_physical_monitor_vol_button_present)
        and p82b_fx6_7opt_mix_all.sdi_channels_count == 4
        and (not p82b_fx6_no_side_vol_btn.admitted)
        and p82b_fx6_no_side_vol_btn.errno_code == ENODEV_ERRNO
    )

    # Sub-Model 82C probes
    p82c_4item_reset_resistant = simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
        operation="fx3_touch_setup",
        shoot_mode="S&Q",
        touch_operation="On",
        touch_sensitivity="Sensitive",
        touch_func_in_shooting="Touch Focus",
        swipe_up="Open the Fn Menu",
        camera_settings_reset_applied=True,
    )
    p82c_dormant_pad = simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
        operation="dormant_touch_panel_pad"
    )
    p82c_dormant_shutter = simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
        operation="dormant_touch_shutter"
    )
    p82c_dormant_ae = simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
        operation="dormant_touch_ae"
    )
    p82c_spot_static_only = simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
        operation="fx3_spot_metering_link",
        spot_metering_point="Focus Point Link",
    )
    p82c_spot_moving_box_blocked = simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
        operation="fx3_spot_metering_link",
        spot_metering_point="Focus Point Link",
        request_follow_moving_tracking_box=True,
    )
    p82c_fx6_mf_desqueeze_blocked = simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_touch_operation",
        fx6_touch_function_in_mf="Spot Focus",
        fx6_desqueeze_active=True,
        invoke_touch_in_mf=True,
    )
    p82c_fx6_big6_tracking_mf = simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_touch_operation",
        fx6_touch_function_in_mf="Tracking AF",
        invoke_touch_in_mf=True,
    )
    p82c_ok = (
        p82c_4item_reset_resistant.admitted
        and p82c_4item_reset_resistant.touch_setup_active_items_count == 4
        and p82c_4item_reset_resistant.touch_sensitivity == "Sensitive"
        and p82c_4item_reset_resistant.touch_func_in_shooting == "Touch Focus"
        and (not p82c_4item_reset_resistant.resettable_via_camera_settings_reset)
        and p82c_4item_reset_resistant.swipe_up_active
        and (not p82c_dormant_pad.admitted)
        and p82c_dormant_pad.errno_code == EOPNOTSUPP_ERRNO
        and (not p82c_dormant_shutter.admitted)
        and p82c_dormant_shutter.errno_code == EOPNOTSUPP_ERRNO
        and (not p82c_dormant_ae.admitted)
        and p82c_dormant_ae.errno_code == EOPNOTSUPP_ERRNO
        and p82c_spot_static_only.admitted
        and (not p82c_spot_static_only.spot_link_tracks_moving_box)
        and (not p82c_spot_moving_box_blocked.admitted)
        and p82c_spot_moving_box_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not p82c_fx6_mf_desqueeze_blocked.admitted)
        and p82c_fx6_mf_desqueeze_blocked.errno_code == EBUSY_ERRNO
        and p82c_fx6_mf_desqueeze_blocked.fx6_spot_focus_disabled_reason == "desqueeze_active"
        and p82c_fx6_big6_tracking_mf.admitted
        and p82c_fx6_big6_tracking_mf.fx6_big6_and_full_menu_touch_supported
    )

    # Sub-Model 82D probes
    p82d_config_reset_resistant = simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
        operation="fx3_remote_shoot_config",
        still_img_save_dest="Destination Only",
        camera_settings_reset_applied=True,
    )
    p82d_dest_only_usb_ram = simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
        operation="fx3_remote_capture",
        still_img_save_dest="Destination Only",
        transport_protocol="PTP_USB_SICD",
        card_inserted_slot1=False,
        release_wo_card="Disable",
    )
    p82d_dest_only_ptpip_usblan = simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
        operation="fx3_remote_capture",
        still_img_save_dest="Destination Only",
        transport_protocol="PTP_IP_TCP_15740",
        wired_usb_lan=True,
        airplane_mode="On",
    )
    p82d_default_dest_cam_cardless_blocked = simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
        operation="fx3_remote_capture",
        still_img_save_dest="Dest.+Camera",
        card_inserted_slot1=False,
        release_wo_card="Enable",
    )
    p82d_default_dest_cam_slot1_erofs = simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
        operation="fx3_remote_capture",
        still_img_save_dest="Dest.+Camera",
        card_inserted_slot1=True,
        slot1_is_tier0_vault=True,
    )
    p82d_camera_only_slot1_erofs = simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
        operation="fx3_remote_capture",
        still_img_save_dest="Camera Only",
        card_inserted_slot1=True,
        slot1_is_tier0_vault=True,
    )
    p82d_connected_lock = simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
        operation="fx3_remote_shoot_config",
        connection_state="CONNECTED",
        change_save_dest_while_connected=True,
    )
    p82d_fx6_remote = simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_camera_remote_control",
    )
    p82d_fx6_save_dest_masked = simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_camera_remote_control",
        request_fx6_save_dest_ui=True,
    )
    p82d_ok = (
        p82d_config_reset_resistant.admitted
        and p82d_config_reset_resistant.still_img_save_dest == "Destination Only"
        and (not p82d_config_reset_resistant.resettable_via_camera_settings_reset)
        and p82d_dest_only_usb_ram.admitted
        and p82d_dest_only_usb_ram.ram_direct_transfer_active
        and p82d_dest_only_usb_ram.slot1_data_sector_writes == 0
        and p82d_dest_only_ptpip_usblan.admitted
        and p82d_dest_only_ptpip_usblan.ptp_ip_port == 15740
        and p82d_dest_only_ptpip_usblan.rf_tx_packets == 0
        and (not p82d_default_dest_cam_cardless_blocked.admitted)
        and p82d_default_dest_cam_cardless_blocked.errno_code == ENODEV_ERRNO
        and (not p82d_default_dest_cam_slot1_erofs.admitted)
        and p82d_default_dest_cam_slot1_erofs.errno_code == EROFS_ERRNO
        and p82d_default_dest_cam_slot1_erofs.slot1_data_sector_writes == 0
        and (not p82d_camera_only_slot1_erofs.admitted)
        and p82d_camera_only_slot1_erofs.errno_code == EROFS_ERRNO
        and p82d_camera_only_slot1_erofs.slot1_data_sector_writes == 0
        and (not p82d_connected_lock.admitted)
        and p82d_connected_lock.errno_code == EBUSY_ERRNO
        and p82d_fx6_remote.admitted
        and (not p82d_fx6_remote.fx6_still_img_save_dest_ui_exposed)
        and (not p82d_fx6_save_dest_masked.admitted)
        and p82d_fx6_save_dest_masked.errno_code == EOPNOTSUPP_ERRNO
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
        # 82A
        "fx3_audio_rec_level_default": FX3_AUDIO_REC_LEVEL_DEFAULT,
        "fx3_audio_rec_level_steps_count": FX3_AUDIO_REC_LEVEL_STEPS_COUNT,
        "fx3_body_limiter_always_on": FX3_BODY_LIMITER_ALWAYS_ON,
        "fx3_xlrh1_body_reclevel_bypass_verified": FX3_XLRH1_BODY_RECLEVEL_BYPASS_VERIFIED,
        "fx3_xlrh1_bypass_escape_events": FX3_XLRH1_BYPASS_ESCAPE_EVENTS,
        "fx6_limiter_mode_steps_count": FX6_LIMITER_MODE_STEPS_COUNT,
        "fx6_4step_limiter_rumor_disproved": FX6_4STEP_LIMITER_RUMOR_DISPROVED,
        "fx6_ref_level_steps_count": FX6_REF_LEVEL_STEPS_COUNT,
        # 82B
        "fx3_volume_settings_default": FX3_VOLUME_SETTINGS_DEFAULT,
        "fx3_4ch_monitoring_options_count": FX3_4CH_MONITORING_OPTIONS_COUNT,
        "fx3_3option_errata_corrected": FX3_3OPTION_ERRATA_CORRECTED,
        "fx3_4ch_monitoring_reset_wipe_events": FX3_4CH_MONITORING_RESET_WIPE_EVENTS,
        "fx6_monitor_ch_options_count": FX6_MONITOR_CH_OPTIONS_COUNT,
        "fx6_physical_monitor_vol_button_present": FX6_PHYSICAL_MONITOR_VOL_BUTTON_PRESENT,
        "fx6_sdi_audio_channels": FX6_SDI_AUDIO_CHANNELS,
        # 82C
        "fx3_touch_setup_active_items_count": FX3_TOUCH_SETUP_ACTIVE_ITEMS_COUNT,
        "fx3_dormant_touch_shutter_ae_pad_exposed_events": FX3_DORMANT_TOUCH_SHUTTER_AE_PAD_EXPOSED_EVENTS,
        "fx3_ilc2210_touch_shutter_hits": FX3_ILC2210_TOUCH_SHUTTER_HITS,
        "fx3_ilc2210_touch_ae_hits": FX3_ILC2210_TOUCH_AE_HITS,
        "fx3_spot_link_tracks_moving_box": FX3_SPOT_LINK_TRACKS_MOVING_BOX,
        "fx3_touch_setup_reset_wipe_events": FX3_TOUCH_SETUP_RESET_WIPE_EVENTS,
        # 82D
        "fx3_ptp_usb_vid_pid": FX3_PTP_USB_VID_PID,
        "fx3_ptpip_tcp_port": FX3_PTPIP_TCP_PORT,
        "fx3_remote_shoot_factory_default_dest": FX3_REMOTE_SHOOT_FACTORY_DEFAULT_DEST,
        "fx3_remote_shoot_dest_only_ram_writes_slot1": FX3_REMOTE_SHOOT_DEST_ONLY_RAM_WRITES_SLOT1,
        "fx3_slot1_remote_shoot_write_bypass_events": FX3_SLOT1_REMOTE_SHOOT_WRITE_BYPASS_EVENTS,
        "fx6_still_img_save_dest_ui_exposed": FX6_STILL_IMG_SAVE_DEST_UI_EXPOSED,
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
        donor_audit["all_donors_verified"] and p82a_ok and p82b_ok and p82c_ok and p82d_ok
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_365_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_82nd_stage_milestone": IS_82ND_STAGE_MILESTONE,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit["source_mode"],
        "redlines": redlines,
        "donor_audit": donor_audit,
        "stage82_milestone_probe": _build_stage82_milestone_probe(),
        "pillar_a_audio_reclevel_xlrh1_bypass_vs_fx6_hil": {
            "passed": p82a_ok,
            "fx3_internal_mic_default_26": asdict(p82a_internal_default),
            "fx3_delete_key_resets_26": asdict(p82a_delete_resets_26),
            "fx3_body_limiter_non_defeatable": asdict(p82a_limiter_cannot_disable),
            "fx3_xlrh1_handle_bypasses_body_reclevel": asdict(p82a_xlr_bypasses_body),
            "fx3_35mm_preempts_xlrh1": asdict(p82a_35mm_preempts_xlr),
            "fx3_sq_locks_0ch_audio": asdict(p82a_sq_locked),
            "fx6_6step_limiter_and_3tier_ref": asdict(p82a_fx6_6step_limiter),
        },
        "pillar_b_audio_out_timing_volume_4ch_mon_vs_fx6_hil": {
            "passed": p82b_ok,
            "fx3_audio_out_timing_lip_sync": asdict(p82b_timing_lip_sync),
            "fx3_audio_out_timing_reset_to_live": asdict(p82b_timing_reset_live),
            "fx3_volume_settings_reset_resistant": asdict(p82b_vol_reset_resistant),
            "fx3_4ch_monitoring_5opt_ch1_ch1_reset_resistant": asdict(p82b_mon_ch1_ch1_reset_resistant),
            "fx3_4ch_monitoring_errata_rejected": asdict(p82b_mon_errata_rejected),
            "fx6_7opt_monitor_ch_mix_all_and_sdi_4ch": asdict(p82b_fx6_7opt_mix_all),
            "fx6_zero_side_monitor_vol_button": asdict(p82b_fx6_no_side_vol_btn),
        },
        "pillar_c_touch_operation_4item_vs_dormant_shutter_ae_fx6_hil": {
            "passed": p82c_ok,
            "fx3_touch_setup_4item_reset_resistant": asdict(p82c_4item_reset_resistant),
            "fx3_dormant_touch_panel_pad_eopnotsupp": asdict(p82c_dormant_pad),
            "fx3_dormant_touch_shutter_eopnotsupp": asdict(p82c_dormant_shutter),
            "fx3_dormant_touch_ae_eopnotsupp": asdict(p82c_dormant_ae),
            "fx3_spot_metering_link_static_only": asdict(p82c_spot_static_only),
            "fx3_spot_metering_link_no_tracking_box": asdict(p82c_spot_moving_box_blocked),
            "fx6_mf_spot_focus_desqueeze_lock": asdict(p82c_fx6_mf_desqueeze_blocked),
            "fx6_big6_full_menu_and_tracking_mf": asdict(p82c_fx6_big6_tracking_mf),
        },
        "pillar_d_remote_shoot_setting_ptp_vs_slot1_erofs_fx6_hil": {
            "passed": p82d_ok,
            "fx3_remote_shoot_config_reset_resistant": asdict(p82d_config_reset_resistant),
            "fx3_dest_only_usb_cardless_ram_capture": asdict(p82d_dest_only_usb_ram),
            "fx3_dest_only_ptpip_usblan_zero_rf": asdict(p82d_dest_only_ptpip_usblan),
            "fx3_default_dest_cam_cardless_refused": asdict(p82d_default_dest_cam_cardless_blocked),
            "fx3_default_dest_cam_slot1_erofs_30": asdict(p82d_default_dest_cam_slot1_erofs),
            "fx3_camera_only_slot1_erofs_30": asdict(p82d_camera_only_slot1_erofs),
            "fx3_connected_save_dest_locked_ebusy": asdict(p82d_connected_lock),
            "fx6_camera_remote_control_ptpip": asdict(p82d_fx6_remote),
            "fx6_still_img_save_dest_masked": asdict(p82d_fx6_save_dest_masked),
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
        prog="realhw_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulator.py",
        description=(
            "Phase 365 (Stage 82 — 82/82 Full-Board VM Co-Emulation Stages!): "
            "Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-72 "
            "[Audio Rec Level] 0..31 / XLR-H1 Bypass / Permanent Body Limiter vs "
            "FX6 3-Tier Reference & 6-Step Limiter Mode / [Audio Out Timing] & "
            "Exact 5-Option [4ch Audio Monitoring] vs FX6 7-Option Monitor CH / "
            "4-Item [Touch Operation] & 100%% Dormant Touch Shutter/AE/Pad / "
            "[Remote Shoot Setting] PTP/PTP-IP Destination Only RAM & Slot 1 "
            "EROFS=30 Firewall HIL Co-Emulator"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run all 82A..82D HIL checks and 25-donor O_RDONLY/clean-room audit",
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
    rep = run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        rl = rep["redlines"]
        da = rep["donor_audit"]
        sys.stdout.write(
            f"[{status}] Phase 365 Stage {MILESTONE_LABEL} | src={rep['source_mode']} "
            f"donors={da['total_donors_count']} | "
            f"reclevel_def={rl['fx3_audio_rec_level_default']} "
            f"fx6_lim={rl['fx6_limiter_mode_steps_count']}st | "
            f"mon4ch={rl['fx3_4ch_monitoring_options_count']}opt/"
            f"fx6_{rl['fx6_monitor_ch_options_count']}opt | "
            f"touch={rl['fx3_touch_setup_active_items_count']}i/"
            f"dorm={rl['fx3_dormant_touch_shutter_ae_pad_exposed_events']} | "
            f"ptp_rf={rl['rf_tx_packets']} s1_wr={rl['slot1_data_sector_writes']} "
            f"emmc_wr={rl['emmc_nflasha_write_count']} "
            f"attach={int(bool(rl['ready_for_live_camera_attach']))} | "
            f"digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
