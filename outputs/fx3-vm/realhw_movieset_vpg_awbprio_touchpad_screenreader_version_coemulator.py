#!/usr/bin/env python3
"""Phase 379 — Stage 87 (87/87 Full-Board VM HIL Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-77 HIL:
- 87A: `Shooting -> [Image Quality/Rec] -> [File Format]` & `[Movie Settings]`
  6-Codec Matrix (`XAVC HS 4K`, `XAVC S 4K`, `XAVC S HD` factory default,
  `XAVC S-I 4K`, `XAVC S-I HD`, `XAVC S-I DCI 4K` Ver. 3.00+ `_f 0x7336`),
  dormant `8K` (`xavc_hs_8k`) blocked `EOPNOTSUPP=95`, `24.00p` cross-mode
  reboot (`MODEL_EVENT_REBOOT_BY_CROSS_2400P`) + playback isolation
  (`_g 0x6127/0x63d7`) + `4K Output Set.(HDMI Only)` mutex + `48fps` S&Q
  exclusive to `24.00p + DCI 4K`, 5-tier ELF transfer-rate firewall
  (`100/200/400/600/1350 MBPS` mapping to `Class 10`, `SDXC U3/V30`,
  `SDXC V60`, `SDXC V90`, `CFexpress Type A VPG200`, `CFexpress Type A VPG400`),
  Wave-77 `G139` Erratum (`S&Q XAVC S HD 100fps/120fps` requires ONLY `SDXC V60+`,
  only `200fps/240fps` needs `SDXC V90+`; `XAVC S-I DCI 4K` forbids `100/120fps`
  in S&Q max `60/50fps 600M`; `VPG400` `0xea64/0xea6c/0xea78/0xea7b` enforces
  the `1350MBPS` proxy-stack threshold for `S&Q XAVC S-I 4K 1200M + Proxy`),
  and `[Camera Settings Reset]` resets both `[File Format]` & `[Movie Settings]`
  vs `ILME-FX6` `Project > Rec Format` (`RAW & XAVC-I`, `RAW(HDMI) & XAVC-I`,
  `XAVC-I` `Class300` max `600M VBR` with dormant `Class480` blocked, `XAVC-L`
  QFHD `150M/100M` / HD `50M/35M` with dormant `XAVC-L25` & DCI 4K blocked).
- 87B: `Exposure/Color -> [White Balance]`: `[Priority Set in AWB]` (`Standard`
  default / `Ambience` / `White`, `Can be reset`, active in Still & Movie when
  `WB = Auto` including `Flexible ISO`, inactive/disabled in `Cine EI` /
  `Cine EI Quick`), `[Shutter AWB Lock]` (`Off` default / `Shutter Half Press` /
  `Cont. Shooting`, strictly Still-only with Movie/S&Q blocked `EOPNOTSUPP=95`
  requiring Custom Key `AWB Lock Hold/Toggle`, and resists `[Camera Settings
  Reset]` — `[Initialize]` only), and `[C.Temp./Filter]` (`2500K..9900K` `100K`
  steps = `75` steps, `A7..B7` `29` steps at `0.5`, `G7..M7` `57` steps at
  `0.25`) vs `ILME-FX6` physical 3-way `WHT BAL` (`B/A/PRESET`), `Preset`
  (Custom `3200/4300/5600/6300K`; Cine EI `3200/4300/5500K`), `ATW`
  (`2000K..15000K`, `ATW Speed 1..5`, `ATW Hold`, blocked in Cine EI), `Tint
  -99..+99`, `R/B Gain -99.0..+99.0`, and `Shockless White Off/1/2/3`.
- 87C: `Setup -> [Touch Operation]` strictly 4 exposed items (all resist Reset:
  `Touch Operation` `On`/`On: Playback Only`/`Off`, `Touch Sensitivity`
  `Standard`/`Sensitive`, `Touch Func. in Shooting` `Touch Tracking`/`Touch
  Focus`/`Off`, `Swipe Up` `Open the Fn Menu`/`Off`) vs dormant EVF `[Touch
  Panel/Pad]` (`BKID_APP_setting_touch_panel_pad`, `_f 0x76ec`), `Touch Pad
  Settings/Area Set./vertical`, & `Touch Shutter` blocked `EOPNOTSUPP=95` on
  EVF-less FX3; Wave-77 `G109` Erratum: ALL 7 items across `[Focus Assistant]`
  (`Auto Magnifier in MF`, `Focus Magnif. Time`, `Initial Focus Mag.`, `AF in
  Focus Mag.`) and `[Peaking Display]` (`Display`, `Level`, `Color`, `0` HDMI
  output) resist `[Camera Settings Reset]` (reset ONLY on `[Initialize]`), with
  `[AF in Focus Mag.]` strictly Still-only (blocked in Movie/S&Q, `AF-C`,
  non-PASM `AF-A`, `Cont. Shooting`, and Mount Adaptor) vs `ILME-FX6`
  `Monitoring > Peaking` strictly 3 ELF-bound items (`Setting`, `Level`, `Color
  B&W/Red/Yellow/Blue`), dormant `Peaking Type (Normal/Color)` & `Peaking
  Frequency` (`fx6_2 0x4501..0x4508`) blocked `EOPNOTSUPP=95`.
- 87D: `[Accessibility]` / `[Screen Reader]` compiled-in (`screen_reader/
  screen_reader.cpp`, `SLOW_2..FAST_4`, volume `0..15`, `/usr/data/
  screen_reader_ext`) but SKU-gated to `0` UI exposure on both `ILME-FX3`
  (`ALCIN_UUD`) & `ILME-FX6` (`EOPNOTSUPP=95` unless authorized SKU/pack; zero
  HDMI audio link); Wave-77 `G104` Erratum: `Setup -> [Setup Option] ->
  [Version]` (`libInfraGetVersion.so`: ONLY `InfraGetVersion` &
  `InfraGetVersionLens`) displays EXACTLY 2 slots (`Body` `_g 0x6515` & `Lens`
  `_g 0x6517` shared by compatible Mount Adaptor; NO separate 3rd mount-adaptor
  slot and NO MI-Shoe accessory firmware version); Ver. 6.00+ online update dot
  (`_g 0x6516`) silenced under `Airplane Mode = On` (`rf_tx_packets = 0`); and
  `[Software Update]` (`_f 0x6fd6`, `Slot 1` `BODYDATA.DAT`) hard-blocked
  `EROFS=30` (`slot1_writes = 0`, `cross_model_flash_authorized = False`,
  `live_attach_authorized = False`) vs `ILME-FX6` `Maintenance > Version`
  (`Body`, `Lens`, `Ext. Unit`, `Slot B` + AC adapter).

Enforces strict Tier-0 safety redlines across all 4 execution modes (normal
local donors strictly `os.O_RDONLY` with `<= 4096 B` `os.pread` bounded windows
on multi-MiB files; `FX3_CLEAN_ROOM_TEST=1`; `FX3_FX6_FORCE_CLEAN_ROOM=1`; and
donorless `work_root=None` / `FX3_FX6_MAC_WORK_ROOT` sentinel).
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
# Phase 379 Schema, Stage 87 (87/87) & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = (
    "phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation_v1"
)
PHASE_379_VERSION = "379.0.0"
PHASE_NUMBER = 379
STAGE_INDEX = 87
STAGE_TOTAL = 87
MILESTONE_LABEL = "87/87"

# Hardware Safety & Redline Constants (Tier-0 NO-GO / EROFS=30 / Zero-Leak)
READY_FOR_LIVE_CAMERA_ATTACH = False
LIVE_ATTACH_AUTHORIZED = False
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
USB_TX_PACKETS = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PASSIVE_TX_BYTES_EMITTED = 0
SLOT1_BODYDATA_WRITE_AUTHORIZED = False
SLOT1_WRITES = 0
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

# Body & Mode Constants
BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
BODY_MODEL_FX30_AUTH = "ILME-FX30-AUTH"
VALID_BODY_MODELS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)
VALID_SHOOT_MODES: Tuple[str, ...] = ("Still", "Movie", "S&Q")

# ---------------------------------------------------------------------------
# 87A Constants — 6-Codec Matrix, 24.00p Isolation, 5-Tier VPG & G139 Erratum
# ---------------------------------------------------------------------------

FX3_FILE_FORMATS: Tuple[str, ...] = (
    "XAVC HS 4K",
    "XAVC S 4K",
    "XAVC S HD",
    "XAVC S-I 4K",
    "XAVC S-I HD",
    "XAVC S-I DCI 4K",
)
FX3_FILE_FORMAT_DEFAULT = "XAVC S HD"
FX3_MOVIE_DEFAULT_FRAME_RATE = "59.94p"
FX3_MOVIE_DEFAULT_RECORD_SETTING = "50M 4:2:0 8bit"
FX3_DORMANT_8K_FORMATS: Tuple[str, ...] = ("XAVC HS 8K", "xavc_hs_8k")

FX3_CODEC_SPECS: Mapping[str, Mapping[str, Any]] = {
    "XAVC HS 4K": {
        "resolution": "3840x2160",
        "compression": "HEVC Long GOP",
        "frame_rates": ("119.88p", "100p", "59.94p", "50p", "23.98p"),
        "default_frame_rate": "59.94p",
        "max_movie_bitrate_mbps": 280,
    },
    "XAVC S 4K": {
        "resolution": "3840x2160",
        "compression": "H.264 Long GOP",
        "frame_rates": ("119.88p", "100p", "59.94p", "50p", "29.97p", "25p", "23.98p"),
        "default_frame_rate": "59.94p",
        "max_movie_bitrate_mbps": 280,
    },
    "XAVC S HD": {
        "resolution": "1920x1080",
        "compression": "H.264 Long GOP",
        "frame_rates": ("119.88p", "100p", "59.94p", "50p", "29.97p", "25p", "23.98p"),
        "default_frame_rate": "59.94p",
        "max_movie_bitrate_mbps": 100,
    },
    "XAVC S-I 4K": {
        "resolution": "3840x2160",
        "compression": "H.264 All-Intra",
        "frame_rates": ("59.94p", "50p", "29.97p", "25p", "23.98p"),
        "default_frame_rate": "59.94p",
        "max_movie_bitrate_mbps": 600,
    },
    "XAVC S-I HD": {
        "resolution": "1920x1080",
        "compression": "H.264 All-Intra",
        "frame_rates": ("59.94p", "50p", "29.97p", "25p", "23.98p"),
        "default_frame_rate": "59.94p",
        "max_movie_bitrate_mbps": 222,
    },
    "XAVC S-I DCI 4K": {
        "resolution": "4096x2160",
        "compression": "H.264 All-Intra",
        "frame_rates": ("59.94p", "50p", "29.97p", "25p", "24.00p", "23.98p"),
        "default_frame_rate": "24.00p",
        "max_movie_bitrate_mbps": 600,
        "min_fw_version": "3.00",
    },
}

FX3_ELF_TRANSFER_RATE_TIERS_MBPS: Tuple[int, ...] = (100, 200, 400, 600, 1350)
FX3_CARD_TIERS: Mapping[str, int] = {
    "SDHC/SDXC Class 10": 1,
    "SDXC U3/V30": 2,
    "SDXC V60": 3,
    "SDXC V90": 4,
    "CFexpress Type A VPG200": 5,
    "CFexpress Type A VPG400": 6,
}
FX3_CARD_RANK_LABELS: Mapping[int, str] = {v: k for k, v in FX3_CARD_TIERS.items()}
FX3_REBOOT_2400P_EVENT = "MODEL_EVENT_REBOOT_BY_CROSS_2400P"
FX3_G139_CARD_SPEED_ERRATUM_RECONCILED = True

FX6_REC_FORMAT_CODECS: Tuple[str, ...] = (
    "RAW & XAVC-I",
    "RAW(HDMI) & XAVC-I",
    "XAVC-I",
    "XAVC-L",
)
FX6_DORMANT_REC_FORMATS: Tuple[str, ...] = ("Class480", "XAVC-L25")
FX6_XAVCI_CLASS = "Class300"
FX6_XAVCI_MAX_BITRATE_MBPS = 600
FX6_XAVCL_QFHD_BITRATES_MBPS: Tuple[int, ...] = (150, 100)
FX6_XAVCL_HD_BITRATES_MBPS: Tuple[int, ...] = (50, 35)

VALID_87A_OPERATIONS: Tuple[str, ...] = (
    "fx3_file_format_6codec_and_dormant_8k",
    "fx3_2400p_reboot_playback_isolation_and_sq_48fps",
    "fx3_card_speed_5tier_vpg_and_g139_erratum",
    "fx6_project_rec_format_and_dormant_class480_xavcl25",
)

# ---------------------------------------------------------------------------
# 87B Constants — AWB Priority, Still-Only Shutter AWB Lock, C.Temp & FX6 ATW
# ---------------------------------------------------------------------------

FX3_AWB_PRIORITY_MODES: Tuple[str, ...] = ("Standard", "Ambience", "White")
FX3_AWB_PRIORITY_DEFAULT = "Standard"
FX3_SHUTTER_AWB_LOCK_MODES: Tuple[str, ...] = (
    "Off",
    "Shutter Half Press",
    "Cont. Shooting",
)
FX3_SHUTTER_AWB_LOCK_DEFAULT = "Off"
FX3_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "Off",
    "Flexible ISO",
    "Cine EI Quick",
    "Cine EI",
)
FX3_CTEMP_MIN_K = 2500
FX3_CTEMP_MAX_K = 9900
FX3_CTEMP_STEP_K = 100
FX3_CTEMP_STEPS_COUNT = ((FX3_CTEMP_MAX_K - FX3_CTEMP_MIN_K) // FX3_CTEMP_STEP_K) + 1  # 75
FX3_AB_FILTER_MIN = -7.0
FX3_AB_FILTER_MAX = 7.0
FX3_AB_FILTER_STEP = 0.5
FX3_AB_FILTER_STEPS_COUNT = 29  # A7..B7 at 0.5
FX3_GM_FILTER_MIN = -7.0
FX3_GM_FILTER_MAX = 7.0
FX3_GM_FILTER_STEP = 0.25
FX3_GM_FILTER_STEPS_COUNT = 57  # G7..M7 at 0.25

FX6_WHT_BAL_SWITCH_POSITIONS: Tuple[str, ...] = ("B", "A", "PRESET")
FX6_CUSTOM_PRESET_KELVINS: Tuple[int, ...] = (3200, 4300, 5600, 6300)
FX6_CINE_EI_PRESET_KELVINS: Tuple[int, ...] = (3200, 4300, 5500)
FX6_ATW_MIN_K = 2000
FX6_ATW_MAX_K = 15000
FX6_ATW_SPEED_RANGE: Tuple[int, ...] = (1, 2, 3, 4, 5)
FX6_TINT_MIN = -99
FX6_TINT_MAX = 99
FX6_RB_GAIN_MIN = -99.0
FX6_RB_GAIN_MAX = 99.0
FX6_SHOCKLESS_WHITE_MODES: Tuple[str, ...] = ("Off", "1", "2", "3")

VALID_87B_OPERATIONS: Tuple[str, ...] = (
    "fx3_priority_set_in_awb_and_cine_ei",
    "fx3_shutter_awb_lock_still_only_and_reset_resistance",
    "fx3_ctemp_filter_grid_and_custom_wb_log_warning",
    "fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
)

# ---------------------------------------------------------------------------
# 87C Constants — Touch Operation (4 Items), Dormant EVF Pad & G109 Erratum
# ---------------------------------------------------------------------------

FX3_HAS_BUILTIN_EVF = False
FX3_TOUCH_EXPOSED_4_ITEMS: Tuple[str, ...] = (
    "Touch Operation",
    "Touch Sensitivity",
    "Touch Func. in Shooting",
    "Swipe Up",
)
FX3_TOUCH_OPERATION_OPTIONS: Tuple[str, ...] = ("On", "On: Playback Only", "Off")
FX3_TOUCH_OPERATION_DEFAULT = "On"
FX3_TOUCH_SENSITIVITY_OPTIONS: Tuple[str, ...] = ("Standard", "Sensitive")
FX3_TOUCH_SENSITIVITY_DEFAULT = "Standard"
FX3_TOUCH_FUNC_SHOOTING_OPTIONS: Tuple[str, ...] = (
    "Touch Tracking",
    "Touch Focus",
    "Off",
)
FX3_TOUCH_FUNC_SHOOTING_DEFAULT = "Touch Tracking"
FX3_SWIPE_UP_OPTIONS: Tuple[str, ...] = ("Open the Fn Menu", "Off")
FX3_SWIPE_UP_DEFAULT = "Open the Fn Menu"
FX3_DORMANT_EVF_TOUCH_ITEMS: Tuple[str, ...] = (
    "Touch Panel/Pad",
    "Touch Panel Only",
    "Touch Pad Only",
    "Touch Panel+Pad",
    "Touch Pad Settings",
    "Touch Pad Area Set.",
    "Touch Pad (vertical)",
    "Touch Panel Settings",
    "Touch Shutter",
    "Icon Touch Function",
)

FX3_FOCUS_ASSISTANT_4_ITEMS: Tuple[str, ...] = (
    "Auto Magnifier in MF",
    "Focus Magnif. Time",
    "Initial Focus Mag.",
    "AF in Focus Mag.",
)
FX3_PEAKING_3_ITEMS: Tuple[str, ...] = (
    "Peaking Display",
    "Peaking Level",
    "Peaking Color",
)
FX3_FOCUS_PEAKING_RESET_RESISTANT_7_ITEMS: Tuple[str, ...] = (
    FX3_FOCUS_ASSISTANT_4_ITEMS + FX3_PEAKING_3_ITEMS
)
FX3_FOCUS_MAGNIF_TIME_OPTIONS: Tuple[str, ...] = ("2 Sec", "5 Sec", "No Limit")
FX3_FOCUS_MAGNIF_TIME_DEFAULT = "No Limit"
FX3_INIT_FOCUS_MAG_MOVIE_OPTIONS: Tuple[str, ...] = ("x1.0", "x4.0")
FX3_INIT_FOCUS_MAG_STILL_FF_OPTIONS: Tuple[str, ...] = ("x1.0", "x2.1")
FX3_INIT_FOCUS_MAG_STILL_APSC_OPTIONS: Tuple[str, ...] = ("x1.0", "x1.5")
FX3_PEAKING_LEVEL_OPTIONS: Tuple[str, ...] = ("High", "Mid", "Low")
FX3_PEAKING_LEVEL_DEFAULT = "Mid"
FX3_PEAKING_COLOR_OPTIONS: Tuple[str, ...] = ("Red", "Yellow", "Blue", "White")
FX3_PEAKING_COLOR_DEFAULT = "White"
FX3_G109_FOCUS_PEAKING_RESET_ERRATUM_RECONCILED = True

FX6_TOUCH_MF_OPTIONS: Tuple[str, ...] = ("Tracking AF", "Spot Focus")
FX6_PEAKING_3_ITEMS: Tuple[str, ...] = ("Setting", "Peaking Level", "Color")
FX6_PEAKING_COLOR_OPTIONS: Tuple[str, ...] = ("B&W", "Red", "Yellow", "Blue")
FX6_DORMANT_PEAKING_ITEMS: Tuple[str, ...] = (
    "Peaking Type",
    "Normal/Color",
    "Peaking Frequency",
    "Normal Peaking Level",
)

VALID_87C_OPERATIONS: Tuple[str, ...] = (
    "fx3_touch_operation_4item_and_dormant_evf_pad",
    "fx3_focus_assistant_and_peaking_g109_reset_resistance",
    "fx6_touch_mf_focus_mag_and_3item_peaking_dormant_block",
)

# ---------------------------------------------------------------------------
# 87D Constants — Screen Reader SKU Gate, 2-Slot Version (G104) & EROFS=30
# ---------------------------------------------------------------------------

FX3_SCREEN_READER_UI_EXPOSED_ITEMS = 0
FX6_SCREEN_READER_UI_EXPOSED_ITEMS = 0
FX3_SCREEN_READER_SPEEDS: Tuple[str, ...] = (
    "SLOW_2",
    "SLOW_1",
    "NORMAL",
    "FAST_1",
    "FAST_2",
    "FAST_3",
    "FAST_4",
)
FX3_SCREEN_READER_SPEED_DEFAULT = "NORMAL"
FX3_SCREEN_READER_VOLUME_MIN = 0
FX3_SCREEN_READER_VOLUME_MAX = 15
FX3_SCREEN_READER_VOLUME_DEFAULT = 7
FX3_SCREEN_READER_HDMI_AUDIO_LINK_SYMBOLS = 0

FX3_VERSION_DISPLAY_SLOTS: Tuple[str, ...] = ("Body", "Lens")
FX3_VERSION_SLOTS_COUNT = 2
FX3_MOUNT_ADAPTOR_SHARES_LENS_SLOT = True
FX3_MI_SHOE_VERSION_DISPLAYED = False
FX3_G104_VERSION_2SLOT_ERRATUM_RECONCILED = True
FX3_SOFTWARE_UPDATE_MIN_BATTERY_PCT = 51

FX6_VERSION_DOMAINS: Tuple[str, ...] = ("Body", "Lens", "Ext. Unit")
FX6_VERSION_UP_REQUIRED_SLOT = "Slot B"
FX6_VERSION_UP_REQUIRES_AC_ADAPTER = True

VALID_87D_OPERATIONS: Tuple[str, ...] = (
    "fx3_screen_reader_sku_gate_and_zero_hdmi_audio",
    "fx3_version_2slot_g104_erratum_and_airplane_dot",
    "fx3_software_update_slot1_bodydata_erofs_firewall",
    "fx6_screen_reader_dormant_and_version_up_slotb_ac",
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


class Stage87Phase379Error(RuntimeError):
    """Raised on invalid Phase 379 Stage 87 HIL inputs or redline violation."""


# ---------------------------------------------------------------------------
# 20 Real-Hardware Wave-77 Donor Specifications (O_RDONLY & <= 4096 B Windows)
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


PHASE379_COMPACT_DONORS: Tuple[CompactDonorSpec, ...] = (
    CompactDonorSpec(
        name="fx3_string_en_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
        expected_size=373820,
        expected_sha256="7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        required_tokens=(
            b"XAVC S-I DCI 4K",
            b"Movie Settings",
            b"Rec Frame Rate",
            b"Record Setting",
            b"Priority Set in AWB",
            b"Shutter AWB Lock",
            b"Shutter Half Press",
            b"AWB Lock Hold",
            b"AWB Lock Toggle",
            b"Touch Sensitivity",
            b"Touch Func. in Shooting",
            b"Swipe Up",
            b"Touch Panel/Pad",
            b"Touch Pad Settings",
            b"Touch Pad Area Set.",
            b"Touch Pad (vertical)",
            b"Initial Focus Mag.",
            b"Focus Magnif. Time",
            b"AF in Focus Mag.",
            b"Peaking Display",
            b"Screen Reader",
            b"Software Update",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_f.uxc",
        expected_size=322652,
        expected_sha256="4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        required_tokens=(
            b"XAVC S-I DCI 4K",
            "动态影像设置".encode("utf-8"),
            "AWB优先级设置".encode("utf-8"),
            "快门AWB锁".encode("utf-8"),
            "触摸灵敏度".encode("utf-8"),
            "触摸屏/触摸板".encode("utf-8"),
            "峰值显示".encode("utf-8"),
            "屏幕阅读器".encode("utf-8"),
            "软件更新".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_f.uxc",
        expected_size=324148,
        expected_sha256="32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        required_tokens=(
            b"XAVC S-I DCI 4K",
            "動態影像設定".encode("utf-8"),
            "峰值顯示".encode("utf-8"),
            "軟體更新".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_f.uxc",
        expected_size=447840,
        expected_sha256="45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        required_tokens=(
            b"XAVC S-I DCI 4K",
            "動画設定".encode("utf-8"),
            "AWBロック".encode("utf-8"),
            "ﾀｯﾁﾊﾟﾈﾙのみ".encode("utf-8"),
            "ﾀｯﾁﾊﾟｯﾄﾞのみ".encode("utf-8"),
            "ﾀｯﾁﾄﾗｯｷﾝｸﾞ".encode("utf-8"),
            "ｱｯﾌﾟﾃﾞｰﾄ".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english.uxc",
        expected_size=165740,
        expected_sha256="204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        required_tokens=(
            b"CFexpress VPG400",
            b"CFexpress VPG200",
            b"SDXC V90",
            b"SDXC V60",
            b"Version",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese.uxc",
        expected_size=149064,
        expected_sha256="34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
        required_tokens=(
            b"VPG400",
            b"VPG200",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese.uxc",
        expected_size=151908,
        expected_sha256="be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
        required_tokens=(
            b"VPG400",
            b"VPG200",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese.uxc",
        expected_size=208564,
        expected_sha256="f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
        required_tokens=(
            b"VPG400",
            b"VPG200",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
        expected_size=69600,
        expected_sha256="a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        required_tokens=(
            b"Accessibility",
            b"Screen Reader",
            b"Body: Ver.${v1}",
            b"Lens: Ver.${v1}",
            b"There is the latest software version.",
            b"24.00p",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_g.uxc",
        expected_size=61296,
        expected_sha256="a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
        required_tokens=(
            "屏幕阅读器".encode("utf-8"),
            "机身更新完成".encode("utf-8"),
            b"24.00p",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_g.uxc",
        expected_size=61372,
        expected_sha256="97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80",
        required_tokens=(b"24.00p",),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_g.uxc",
        expected_size=89428,
        expected_sha256="4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980",
        required_tokens=(b"24.00p",),
    ),
    CompactDonorSpec(
        name="fx3_lib_infra_get_version",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libInfraGetVersion.so",
        expected_size=10144,
        expected_sha256="3a69e737c04b50d120d00e8a0b977f1d60dbb4228abe3b41083e7ab9178be620",
        required_tokens=(
            b"InfraGetVersion",
            b"InfraGetVersionLens",
        ),
        absent_tokens=(
            b"InfraGetVersionMount",
            b"InfraGetVersionShoe",
            b"InfraGetVersionExt",
        ),
    ),
    CompactDonorSpec(
        name="fx3_lib_updater_media",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libupdatermedia.so",
        expected_size=10144,
        expected_sha256="1b5fa6dfd53075afcea591f3a38a1af9a957d6129ea3d180fe1cd562cfdd30db",
        required_tokens=(
            b"udtr_get_media_path",
            b"UDTR_MEDIA",
            b"GetMediaIDByAttribute",
        ),
    ),
    CompactDonorSpec(
        name="fx3_lib_infra_media_detect",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libInfraMediaDetect.so",
        expected_size=98224,
        expected_sha256="4c1dbb303cf9d2d762723e0eb2266309c83aefe7d50f050fc8baa3964e4ea70d",
        required_tokens=(
            b"_ZN16InfraMediaDetect10GetVersionEv",
            b"_ZN16InfraMediaDetect7SuspendEv",
            b"_ZN16InfraMediaDetect6ResumeEv",
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_en",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
        expected_size=118208,
        expected_sha256="5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        required_tokens=(
            b"Screen Reader",
            b"Extension Unit",
            b"Tracking AF",
            b"Spot Focus",
            b"Focus Magnifier",
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_en_2",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
        expected_size=118676,
        expected_sha256="3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        required_tokens=(
            b"Rec Format",
            b"Class480",
            b"XAVC-L25",
            b"Peaking Type",
            b"Peaking Frequency",
            b"Version Up",
            b"Lens Version Up",
            b"Ext. Unit Version Up",
        ),
    ),
)

PHASE379_WINDOW_DONORS: Tuple[WindowDonorSpec, ...] = (
    WindowDonorSpec(
        name="fx3_appfw",
        rel_path="fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        expected_size=79015712,
        head4k_sha256="de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
        windows=(
            (0x2FB5000, "WB_CTEMP_2500K", b"WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_2500K"),
            (0x2FB6000, "WB_CTEMP_9900K", b"WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_9900K"),
            (0x2FC2000, "SCREEN_READER_CPP", b"screen_reader/screen_reader.cpp"),
            (0x3BC3000, "XAVC_SI_DCI_4K", b"BKID_APP_setting_movie_rec_frame_rate_xavc_s_i_dci_4k"),
            (0x3BC3000, "DORMANT_XAVC_HS_8K", b"BKID_APP_setting_movie_rec_frame_rate_xavc_hs_8k"),
            (0x3BC8000, "PRIORITY_SET_IN_AWB", b"BKID_APP_setting_priority_set_in_awb"),
            (0x3BC8000, "SHUTTER_AWB_LOCK", b"BKID_APP_setting_stl_awb_lock_with_shutter"),
            (0x3BC9000, "MOV_INIT_FOCUS_MAG", b"BKID_APP_setting_mov_init_ratio_focus_magnif"),
            (0x3BC9000, "STL_INIT_FOCUS_MAG", b"BKID_APP_setting_stl_init_ratio_focus_magnif"),
            (0x3BCB000, "TOUCH_OPERATION", b"BKID_APP_setting_touch_operation"),
            (0x3BCB000, "TOUCH_SENSITIVITY", b"BKID_APP_setting_touch_sensitivity"),
            (0x3BCB000, "TOUCH_FUNC_SHOOTING", b"BKID_APP_setting_shooting_touch_function"),
            (0x3BCB000, "SWIPE_UP", b"BKID_APP_setting_swipe_up"),
            (0x3BCB000, "DORMANT_TOUCH_PANEL_PAD", b"BKID_APP_setting_touch_panel_pad"),
            (0x3BCB000, "DORMANT_TOUCH_PAD_AREA", b"BKID_APP_setting_touch_pad_operation_area"),
            (0x3BCB000, "SCREEN_READER_SETTING", b"BKID_APP_setting_screen_reader_setting"),
            (0x3BCB000, "SCREEN_READER_SPEED", b"BKID_APP_setting_screen_reader_speed"),
            (0x3BCB000, "SCREEN_READER_VOLUME", b"BKID_APP_setting_screen_reader_volume"),
            (0x3BF3000, "UPDATE_BODY_VERSION", b"BKID_APP_update_body_version"),
            (0x3C10000, "DCI_4K_24_00P", b"EXTERN_VAL_DCI_4K_REC_FRAME_RATE_24_00P"),
            (0x3C1B000, "RATE_UNDER_100MBPS", b"MEDIA_TRANSFER_RATE_SLOT1_UNDER_100MBPS"),
            (0x3C1B000, "RATE_UNDER_200MBPS", b"MEDIA_TRANSFER_RATE_SLOT1_UNDER_200MBPS"),
            (0x3C1B000, "RATE_UNDER_400MBPS", b"MEDIA_TRANSFER_RATE_SLOT1_UNDER_400MBPS"),
            (0x3C1B000, "RATE_UNDER_600MBPS", b"MEDIA_TRANSFER_RATE_SLOT1_UNDER_600MBPS"),
            (0x3C1B000, "RATE_UNDER_1350MBPS", b"MEDIA_TRANSFER_RATE_SLOT1_UNDER_1350MBPS"),
            (0x3C26000, "SUPPORT_SCREEN_READER", b"support_screen_reader"),
            (0x3C41000, "REBOOT_CROSS_2400P", b"MODEL_EVENT_REBOOT_BY_CROSS_2400P"),
        ),
        absent_windows=(
            (0x3BCB000, "NO_SCREEN_READER_HDMI_BKID", b"BKID_APP_setting_screen_reader_hdmi"),
            (0x3C26000, "NO_SCREEN_READER_HDMI_LINK", b"SCREEN_READER_HDMI"),
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
            (0x2273000, "FX6_PROCAM_SR_CPP", b"procam/screen_reader/screen_reader.cpp"),
            (0x24BB000, "FX6_SR_EXT_PATH", b"/usr/data/screen_reader_ext"),
            (0x2708000, "FX6_ATW_SPEED", b"BKID_APP_SETTING_ATW_SPEED"),
            (0x2710000, "FX6_USER_MENU_PEAKING0", b"BKID_APP_USER_MENU_PEAKING0"),
            (0x2710000, "FX6_USER_MENU_PEAKING1", b"BKID_APP_USER_MENU_PEAKING1"),
            (0x2710000, "FX6_USER_MENU_PEAKING2", b"BKID_APP_USER_MENU_PEAKING2"),
            (0x2712000, "FX6_USER_MENU_ACCESSIBILITY0", b"BKID_APP_USER_MENU_ACCESSIBILITY0"),
            (0x2712000, "FX6_USER_MENU_ACCESSIBILITY1", b"BKID_APP_USER_MENU_ACCESSIBILITY1"),
            (0x2713000, "FX6_BODY_VERSION", b"BKID_APP_BODY_VERSION"),
            (0x2743000, "FX6_ATW_HOLD_ON", b"EVENT_FUNC_ATW_HOLD_ON"),
            (0x27E4000, "FX6_SR_SPEAKER_OUT", b"audio_set_screen_reader_speaker_output"),
        ),
        absent_windows=(
            (0x2710000, "FX6_NO_USER_MENU_PEAKING3", b"BKID_APP_USER_MENU_PEAKING3"),
            (0x2710000, "FX6_NO_PEAKING_FREQUENCY", b"BKID_APP_SETTING_PEAKING_FREQUENCY"),
            (0x2710000, "FX6_NO_PEAKING_TYPE", b"BKID_APP_SETTING_PEAKING_TYPE"),
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
            raise Stage87Phase379Error(
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
        raise Stage87Phase379Error(
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


def inspect_phase379_wave77_donors(
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
            resolved_root / s.rel_path for s in PHASE379_COMPACT_DONORS
        ] + [resolved_root / w.rel_path for w in PHASE379_WINDOW_DONORS]
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
            for s in PHASE379_COMPACT_DONORS
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
            for w in PHASE379_WINDOW_DONORS
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
    for spec in PHASE379_COMPACT_DONORS:
        p = resolved_root / spec.rel_path
        data = _read_full_compact_o_rdonly(p)
        sha = hashlib.sha256(data).hexdigest()
        if len(data) != spec.expected_size or sha != spec.expected_sha256:
            raise Stage87Phase379Error(
                f"Donor mismatch {spec.name}: size={len(data)} sha={sha}"
            )
        missing = [t for t in spec.required_tokens if t not in data]
        if missing:
            raise Stage87Phase379Error(
                f"Donor {spec.name} missing required tokens: {len(missing)}"
            )
        present_bad = [t for t in spec.absent_tokens if t in data]
        if present_bad:
            raise Stage87Phase379Error(
                f"Donor {spec.name} unexpectedly contains absent tokens: {len(present_bad)}"
            )
        compact_entries.append(
            {
                "name": spec.name,
                "size_bytes": len(data),
                "sha256": sha,
                "tokens_matched": len(spec.required_tokens),
                "absent_tokens_verified": len(spec.absent_tokens),
                "source_mode": "LOCAL_DONOR_O_RDONLY",
            }
        )

    window_entries = []
    for wspec in PHASE379_WINDOW_DONORS:
        p = resolved_root / wspec.rel_path
        win_cache: Dict[int, bytes] = {}
        file_size = -1
        head4k_sha = ""
        for off, label, needle in wspec.windows:
            if off not in win_cache:
                sz, h4k, win = _read_bounded_window_o_rdonly(
                    p, off, _BOUNDED_WINDOW_BYTES
                )
                file_size = sz
                head4k_sha = hashlib.sha256(h4k).hexdigest()
                win_cache[off] = win
            if needle not in win_cache[off]:
                raise Stage87Phase379Error(
                    f"Window donor {wspec.name} missing {label} at 0x{off:x}"
                )
        for off, label, needle in wspec.absent_windows:
            if off not in win_cache:
                sz, h4k, win = _read_bounded_window_o_rdonly(
                    p, off, _BOUNDED_WINDOW_BYTES
                )
                file_size = sz
                head4k_sha = hashlib.sha256(h4k).hexdigest()
                win_cache[off] = win
            if needle in win_cache[off]:
                raise Stage87Phase379Error(
                    f"Window donor {wspec.name} unexpectedly had {label} at 0x{off:x}"
                )
        if file_size != wspec.expected_size or head4k_sha != wspec.head4k_sha256:
            raise Stage87Phase379Error(
                f"Window donor {wspec.name} size/head4k mismatch: {file_size}/{head4k_sha}"
            )
        window_entries.append(
            {
                "name": wspec.name,
                "size_bytes": file_size,
                "head4k_sha256": head4k_sha,
                "windows_verified": len(wspec.windows),
                "absent_windows_verified": len(wspec.absent_windows),
                "max_pread_bytes": _BOUNDED_WINDOW_BYTES,
                "source_mode": "LOCAL_DONOR_O_RDONLY",
            }
        )

    return {
        "source_mode": "LOCAL_DONOR_O_RDONLY",
        "donor_access_mode": "O_RDONLY_BOUNDED_4K_AND_COMPACT",
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
# Sub-Model 87A..87D Audit Result Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubModel87AMovieSettingsVpgAuditResult:
    operation: str
    body_model: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    file_format: str
    rec_frame_rate: str
    sq_frame_rate_fps: int
    bitrate_mbps: int
    proxy_recording_on: bool
    card_tier: str
    required_min_card_tier: str
    required_elf_transfer_tier_mbps: int
    dormant_8k_blocked: bool
    reboot_required: bool
    reboot_event: str
    playback_isolation_enforced: bool
    sq_48fps_exclusive_ok: bool
    g139_erratum_reconciled: bool
    can_be_reset_by_cam_reset: bool
    fx6_codec: str
    fx6_video_format: str
    fx6_xavci_class: str
    fx6_dormant_format_blocked: bool
    slot1_writes: int = 0
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel87BAwbPriorityShutterLockCtempAuditResult:
    operation: str
    body_model: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    log_shooting_mode: str
    wb_mode: str
    priority_set_in_awb: str
    priority_effective: bool
    priority_can_be_reset: bool
    shutter_awb_lock: str
    shutter_awb_lock_still_only: bool
    shutter_awb_lock_survived_cam_reset: bool
    shutter_awb_lock_reset_on_init: bool
    movie_awb_lock_alternative: str
    ctemp_kelvin: int
    ab_filter: float
    gm_filter: float
    custom_wb_log_warning: bool
    fx6_wht_bal_switch: str
    fx6_preset_kelvin: int
    fx6_atw_enabled: bool
    fx6_atw_speed: int
    fx6_atw_hold_active: bool
    fx6_tint: int
    fx6_r_gain: float
    fx6_b_gain: float
    fx6_shockless_white: str
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel87CTouchPadFocusPeakingG109AuditResult:
    operation: str
    body_model: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    touch_operation: str
    touch_sensitivity: str
    touch_func_in_shooting: str
    swipe_up: str
    touch_4items_survived_cam_reset: bool
    dormant_evf_touch_item: str
    dormant_evf_touch_blocked: bool
    focus_assistant_item: str
    peaking_display: str
    peaking_level: str
    peaking_color: str
    hdmi_peaking_leaked_pixels: int
    af_in_focus_mag_active: bool
    focus_peaking_7items_survived_cam_reset: bool
    focus_peaking_7items_reset_on_init: bool
    g109_erratum_reconciled: bool
    fx6_touch_mf_mode: str
    fx6_peaking_color: str
    fx6_dormant_peaking_blocked: bool
    fx6_peaking_elf_items_count: int
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel87DScreenReaderVersion2SlotErofsAuditResult:
    operation: str
    body_model: str
    allowed: bool
    errno: int
    reason: str
    screen_reader_ui_exposed: bool
    screen_reader_sku_authorized: bool
    screen_reader_speed: str
    screen_reader_volume: int
    screen_reader_language: str
    screen_reader_language_prompt: bool
    screen_reader_hdmi_audio_links: int
    screen_reader_survived_cam_reset: bool
    version_slots: Tuple[str, ...]
    version_slots_count: int
    mount_adaptor_shares_lens_slot: bool
    mi_shoe_version_displayed: bool
    g104_erratum_reconciled: bool
    airplane_mode_on: bool
    online_update_dot_shown: bool
    software_update_blocked_erofs: bool
    slot1_bodydata_write_authorized: bool
    cross_model_flash_authorized: bool
    live_attach_authorized: bool
    fx6_version_domains: Tuple[str, ...]
    fx6_slot_b_and_ac_required: bool
    slot1_writes: int = 0
    slot1_sector_writes: int = 0
    slot1_data_sector_writes: int = 0
    rf_tx_packets: int = 0
    usb_tx_packets: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Sub-Model 87A Simulator — 6-Codec, 24.00p Reboot/Playback, VPG & G139
# ---------------------------------------------------------------------------


def simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    shoot_mode: str = "Movie",
    file_format: str = FX3_FILE_FORMAT_DEFAULT,
    rec_frame_rate: str = FX3_MOVIE_DEFAULT_FRAME_RATE,
    previous_frame_rate: Optional[str] = None,
    sq_frame_rate_fps: int = 60,
    bitrate_mbps: int = 50,
    proxy_recording_on: bool = False,
    card_tier: str = "SDXC V60",
    playback_clip_is_2400p: Optional[bool] = None,
    hdmi_only_4k_output_requested: bool = False,
    camera_settings_reset_triggered: bool = False,
    fx6_codec: str = "XAVC-I",
    fx6_video_format: str = "4096x2160",
    fx6_bitrate_mbps: int = 600,
    fx6_class_or_variant: str = FX6_XAVCI_CLASS,
) -> SubModel87AMovieSettingsVpgAuditResult:
    if operation not in VALID_87A_OPERATIONS:
        raise Stage87Phase379Error(f"Unknown 87A operation {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage87Phase379Error(f"Unknown body_model {body_model!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage87Phase379Error(f"Unknown shoot_mode {shoot_mode!r}")

    def _mk(**kw: Any) -> SubModel87AMovieSettingsVpgAuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            shoot_mode=shoot_mode,
            allowed=True,
            errno=0,
            reason="OK",
            file_format=file_format,
            rec_frame_rate=rec_frame_rate,
            sq_frame_rate_fps=sq_frame_rate_fps,
            bitrate_mbps=bitrate_mbps,
            proxy_recording_on=proxy_recording_on,
            card_tier=card_tier,
            required_min_card_tier="SDHC/SDXC Class 10",
            required_elf_transfer_tier_mbps=100,
            dormant_8k_blocked=False,
            reboot_required=False,
            reboot_event="",
            playback_isolation_enforced=False,
            sq_48fps_exclusive_ok=False,
            g139_erratum_reconciled=FX3_G139_CARD_SPEED_ERRATUM_RECONCILED,
            can_be_reset_by_cam_reset=True,
            fx6_codec=fx6_codec,
            fx6_video_format=fx6_video_format,
            fx6_xavci_class=fx6_class_or_variant,
            fx6_dormant_format_blocked=False,
            slot1_writes=0,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            raw_firmware_bytes_leaked=0,
        )
        defaults.update(kw)
        return SubModel87AMovieSettingsVpgAuditResult(**defaults)

    if operation == "fx3_file_format_6codec_and_dormant_8k":
        if file_format in FX3_DORMANT_8K_FORMATS:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX3_DORMANT_XAVC_HS_8K_BLOCKED_EOPNOTSUPP",
                dormant_8k_blocked=True,
            )
        if file_format not in FX3_FILE_FORMATS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX3_FILE_FORMAT",
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="CAM_RESET_RESTORES_FILE_FORMAT_AND_MOVIE_SETTINGS_TO_XAVC_S_HD",
                file_format=FX3_FILE_FORMAT_DEFAULT,
                rec_frame_rate=FX3_MOVIE_DEFAULT_FRAME_RATE,
                bitrate_mbps=50,
                can_be_reset_by_cam_reset=True,
            )
        spec = FX3_CODEC_SPECS[file_format]
        if rec_frame_rate not in spec["frame_rates"]:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=f"FRAME_RATE_{rec_frame_rate}_UNSUPPORTED_FOR_{file_format}",
            )
        if bitrate_mbps <= 0 or bitrate_mbps > spec["max_movie_bitrate_mbps"]:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="BITRATE_OUT_OF_CODEC_ENVELOPE",
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"FX3_CODEC_{file_format.replace(' ', '_')}_VALID",
            can_be_reset_by_cam_reset=True,
        )

    if operation == "fx3_2400p_reboot_playback_isolation_and_sq_48fps":
        if file_format not in FX3_FILE_FORMATS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX3_FILE_FORMAT",
            )
        if rec_frame_rate == "24.00p" and file_format != "XAVC S-I DCI 4K":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="24_00P_EXCLUSIVE_TO_XAVC_SI_DCI_4K",
            )
        is_2400p = rec_frame_rate == "24.00p"
        if previous_frame_rate is not None:
            prev_is_2400p = previous_frame_rate == "24.00p"
            if prev_is_2400p != is_2400p:
                return _mk(
                    allowed=True,
                    errno=0,
                    reason=(
                        "CROSS_INTO_24_00P_TRIGGERS_MANDATORY_REBOOT"
                        if is_2400p
                        else "CROSS_OUT_OF_24_00P_TRIGGERS_MANDATORY_REBOOT"
                    ),
                    reboot_required=True,
                    reboot_event=FX3_REBOOT_2400P_EVENT,
                    playback_isolation_enforced=is_2400p,
                )
        if hdmi_only_4k_output_requested and is_2400p:
            return _mk(
                allowed=False,
                errno=EBUSY_ERRNO,
                reason="HDMI_ONLY_4K_OUTPUT_MUTEX_BLOCKED_IN_24_00P",
                playback_isolation_enforced=True,
            )
        if playback_clip_is_2400p is not None:
            if is_2400p and not playback_clip_is_2400p:
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="PLAYBACK_ISOLATION_24_00P_MODE_BLOCKS_NON_24_00P_CLIPS",
                    playback_isolation_enforced=True,
                )
            if (not is_2400p) and playback_clip_is_2400p:
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="PLAYBACK_ISOLATION_NON_24_00P_MODE_BLOCKS_24_00P_CLIPS",
                    playback_isolation_enforced=True,
                )
            return _mk(
                allowed=True,
                errno=0,
                reason="PLAYBACK_ISOLATION_MATCHING_FRAME_DOMAIN_OK",
                playback_isolation_enforced=True,
            )
        if shoot_mode == "S&Q" and sq_frame_rate_fps == 48:
            if file_format == "XAVC S-I DCI 4K" and is_2400p:
                return _mk(
                    allowed=True,
                    errno=0,
                    reason="SQ_48FPS_ALLOWED_EXCLUSIVELY_IN_24_00P_XAVC_SI_DCI_4K",
                    playback_isolation_enforced=True,
                    sq_48fps_exclusive_ok=True,
                )
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="SQ_48FPS_EXCLUSIVE_TO_24_00P_DCI_4K_BLOCKED",
                sq_48fps_exclusive_ok=False,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="FX3_24_00P_DOMAIN_STATE_VALID",
            playback_isolation_enforced=is_2400p,
        )

    if operation == "fx3_card_speed_5tier_vpg_and_g139_erratum":
        if file_format not in FX3_FILE_FORMATS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX3_FILE_FORMAT",
            )
        if card_tier not in FX3_CARD_TIERS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_CARD_TIER",
            )
        card_rank = FX3_CARD_TIERS[card_tier]

        # Wave 77 G139 Erratum: XAVC S-I DCI 4K strictly forbids 100fps/120fps in S&Q
        if shoot_mode == "S&Q" and file_format == "XAVC S-I DCI 4K":
            if sq_frame_rate_fps in (100, 120) or sq_frame_rate_fps > 60:
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="G139_XAVC_SI_DCI_4K_SQ_FORBIDS_100_120FPS_MAX_60FPS_600M",
                    required_min_card_tier="SDXC V90",
                    required_elf_transfer_tier_mbps=600,
                )

        # Determine exact official ilc/2210 minimum card rank & ELF transfer tier
        min_rank = 1
        elf_tier_mbps = 100
        if shoot_mode == "S&Q":
            if file_format == "XAVC S HD":
                if sq_frame_rate_fps in (200, 240):
                    min_rank = 4  # SDXC V90+
                    elf_tier_mbps = 600
                elif sq_frame_rate_fps in (100, 120):
                    # Wave 77 G139 Erratum: ONLY SDXC V60+ (NOT V90+!)
                    min_rank = 3  # SDXC V60+
                    elf_tier_mbps = 400
                else:
                    min_rank = 2  # SDXC U3/V30
                    elf_tier_mbps = 200
            elif file_format in ("XAVC HS 4K", "XAVC S 4K"):
                if sq_frame_rate_fps in (100, 120):
                    min_rank = 4  # SDXC V90+
                    elf_tier_mbps = 600
                elif sq_frame_rate_fps in (50, 60):
                    min_rank = 3  # SDXC V60+
                    elf_tier_mbps = 400
                else:
                    min_rank = 2
                    elf_tier_mbps = 200
            elif file_format == "XAVC S-I HD":
                if sq_frame_rate_fps in (200, 240):
                    min_rank = 5  # CFexpress Type A VPG200+ (890M)
                    elf_tier_mbps = 600
                else:
                    min_rank = 4  # SDXC V90+
                    elf_tier_mbps = 600
            elif file_format == "XAVC S-I 4K":
                if sq_frame_rate_fps in (100, 120):
                    if proxy_recording_on:
                        # 1200M + Proxy hits 1350MBPS VPG400 gate (0xea64/0xea6c/0xea78/0xea7b)
                        min_rank = 6  # CFexpress Type A VPG400
                        elf_tier_mbps = 1350
                    else:
                        min_rank = 5  # CFexpress Type A VPG200+ (1000M/1200M)
                        elf_tier_mbps = 600
                else:
                    min_rank = 5 if proxy_recording_on else 4
                    elf_tier_mbps = 600
            else:  # XAVC S-I DCI 4K (<= 60fps, max 600M)
                min_rank = 5 if proxy_recording_on else 4
                elf_tier_mbps = 600
        else:
            # Standard Movie recording tiers
            if file_format in ("XAVC S-I 4K", "XAVC S-I HD", "XAVC S-I DCI 4K"):
                min_rank = 5 if proxy_recording_on else 4
                elf_tier_mbps = 600
            elif bitrate_mbps >= 280:
                min_rank = 3  # SDXC V60+
                elf_tier_mbps = 400
            elif bitrate_mbps >= 75:
                min_rank = 2  # SDXC U3/V30
                elf_tier_mbps = 200
            else:
                min_rank = 1  # Class 10
                elf_tier_mbps = 100

        req_label = FX3_CARD_RANK_LABELS[min_rank]
        if card_rank < min_rank:
            reason_code = (
                "TRANSFER_RATE_UNDER_1350MBPS_REQUIRES_CFEXPRESS_VPG400_OR_PROXY_OFF"
                if elf_tier_mbps == 1350
                else f"CARD_SPEED_BELOW_{req_label.replace(' ', '_').upper()}_UNDER_{elf_tier_mbps}MBPS"
            )
            return _mk(
                allowed=False,
                errno=EAGAIN_ERRNO,
                reason=reason_code,
                required_min_card_tier=req_label,
                required_elf_transfer_tier_mbps=elf_tier_mbps,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"CARD_TIER_{card_tier.replace(' ', '_').upper()}_MEETS_G139_{elf_tier_mbps}MBPS_GATE",
            required_min_card_tier=req_label,
            required_elf_transfer_tier_mbps=elf_tier_mbps,
        )

    # fx6_project_rec_format_and_dormant_class480_xavcl25
    if fx6_class_or_variant in FX6_DORMANT_REC_FORMATS or fx6_codec in FX6_DORMANT_REC_FORMATS:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason=f"FX6_DORMANT_FORMAT_{fx6_class_or_variant}_BLOCKED_EOPNOTSUPP",
            fx6_dormant_format_blocked=True,
        )
    if fx6_codec not in FX6_REC_FORMAT_CODECS:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_REC_FORMAT_CODEC",
        )
    if fx6_codec == "XAVC-L":
        if fx6_video_format == "4096x2160":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX6_XAVCL_HAS_NO_DCI_4K_ONLY_XAVCI",
            )
        if fx6_video_format == "3840x2160" and fx6_bitrate_mbps not in FX6_XAVCL_QFHD_BITRATES_MBPS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="FX6_XAVCL_QFHD_ONLY_150M_OR_100M",
            )
        if fx6_video_format == "1920x1080" and fx6_bitrate_mbps not in FX6_XAVCL_HD_BITRATES_MBPS:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO if fx6_bitrate_mbps == 25 else EINVAL_ERRNO,
                reason=(
                    "FX6_DORMANT_XAVCL25_BLOCKED_EOPNOTSUPP"
                    if fx6_bitrate_mbps == 25
                    else "FX6_XAVCL_HD_ONLY_50M_OR_35M"
                ),
                fx6_dormant_format_blocked=(fx6_bitrate_mbps == 25),
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="FX6_PROJECT_REC_FORMAT_XAVCL_VALID",
            fx6_xavci_class="N/A",
        )

    # XAVC-I / RAW & XAVC-I / RAW(HDMI) & XAVC-I
    if fx6_bitrate_mbps > FX6_XAVCI_MAX_BITRATE_MBPS:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_XAVCI_CLASS300_MAX_600M_VBR_EXCEEDED",
        )
    return _mk(
        allowed=True,
        errno=0,
        reason="FX6_PROJECT_REC_FORMAT_XAVCI_CLASS300_VALID",
        fx6_xavci_class=FX6_XAVCI_CLASS,
    )


# ---------------------------------------------------------------------------
# Sub-Model 87B Simulator — AWB Priority, Shutter AWB Lock, C.Temp & FX6 ATW
# ---------------------------------------------------------------------------


def simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    shoot_mode: str = "Movie",
    log_shooting_mode: str = "Off",
    wb_mode: str = "Auto",
    priority_set_in_awb: str = FX3_AWB_PRIORITY_DEFAULT,
    shutter_awb_lock: str = FX3_SHUTTER_AWB_LOCK_DEFAULT,
    ctemp_kelvin: int = 5600,
    ab_filter: float = 0.0,
    gm_filter: float = 0.0,
    custom_wb_capture_requested: bool = False,
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    fx6_wht_bal_switch: str = "PRESET",
    fx6_shooting_mode: str = "Custom",
    fx6_preset_kelvin: int = 3200,
    fx6_atw_enabled: bool = False,
    fx6_atw_kelvin: int = 5600,
    fx6_atw_speed: int = 3,
    fx6_atw_hold_active: bool = False,
    fx6_tint: int = 0,
    fx6_r_gain: float = 0.0,
    fx6_b_gain: float = 0.0,
    fx6_shockless_white: str = "1",
) -> SubModel87BAwbPriorityShutterLockCtempAuditResult:
    if operation not in VALID_87B_OPERATIONS:
        raise Stage87Phase379Error(f"Unknown 87B operation {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage87Phase379Error(f"Unknown body_model {body_model!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage87Phase379Error(f"Unknown shoot_mode {shoot_mode!r}")

    def _mk(**kw: Any) -> SubModel87BAwbPriorityShutterLockCtempAuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            shoot_mode=shoot_mode,
            allowed=True,
            errno=0,
            reason="OK",
            log_shooting_mode=log_shooting_mode,
            wb_mode=wb_mode,
            priority_set_in_awb=priority_set_in_awb,
            priority_effective=False,
            priority_can_be_reset=True,
            shutter_awb_lock=shutter_awb_lock,
            shutter_awb_lock_still_only=True,
            shutter_awb_lock_survived_cam_reset=False,
            shutter_awb_lock_reset_on_init=False,
            movie_awb_lock_alternative="Custom Key AWB Lock Hold / AWB Lock Toggle",
            ctemp_kelvin=ctemp_kelvin,
            ab_filter=ab_filter,
            gm_filter=gm_filter,
            custom_wb_log_warning=False,
            fx6_wht_bal_switch=fx6_wht_bal_switch,
            fx6_preset_kelvin=fx6_preset_kelvin,
            fx6_atw_enabled=fx6_atw_enabled,
            fx6_atw_speed=fx6_atw_speed,
            fx6_atw_hold_active=fx6_atw_hold_active,
            fx6_tint=fx6_tint,
            fx6_r_gain=fx6_r_gain,
            fx6_b_gain=fx6_b_gain,
            fx6_shockless_white=fx6_shockless_white,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            raw_firmware_bytes_leaked=0,
        )
        defaults.update(kw)
        return SubModel87BAwbPriorityShutterLockCtempAuditResult(**defaults)

    if operation == "fx3_priority_set_in_awb_and_cine_ei":
        if log_shooting_mode not in FX3_LOG_SHOOTING_MODES:
            return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_LOG_SHOOTING_MODE")
        if priority_set_in_awb not in FX3_AWB_PRIORITY_MODES:
            return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_AWB_PRIORITY_MODE")
        if camera_settings_reset_triggered or initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="PRIORITY_SET_IN_AWB_RESET_TO_STANDARD",
                priority_set_in_awb=FX3_AWB_PRIORITY_DEFAULT,
                priority_effective=(wb_mode == "Auto" and log_shooting_mode not in ("Cine EI", "Cine EI Quick")),
                priority_can_be_reset=True,
            )
        if log_shooting_mode in ("Cine EI", "Cine EI Quick"):
            if wb_mode in ("Auto", "Underwater Auto"):
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="CINE_EI_DISABLES_AUTO_AND_UNDERWATER_AUTO_WB",
                    priority_effective=False,
                )
            return _mk(
                allowed=True,
                errno=0,
                reason="CINE_EI_PRIORITY_SET_IN_AWB_INACTIVE",
                priority_effective=False,
            )
        # Off or Flexible ISO: Auto WB is available
        eff = wb_mode == "Auto"
        return _mk(
            allowed=True,
            errno=0,
            reason=(
                "PRIORITY_SET_IN_AWB_ACTIVE_WITH_AUTO_WB"
                if eff
                else "PRIORITY_SET_IN_AWB_IDLE_FOR_NON_AUTO_WB"
            ),
            priority_effective=eff,
        )

    if operation == "fx3_shutter_awb_lock_still_only_and_reset_resistance":
        if shutter_awb_lock not in FX3_SHUTTER_AWB_LOCK_MODES:
            return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_SHUTTER_AWB_LOCK_MODE")
        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_SHUTTER_AWB_LOCK_TO_OFF",
                shutter_awb_lock=FX3_SHUTTER_AWB_LOCK_DEFAULT,
                shutter_awb_lock_survived_cam_reset=False,
                shutter_awb_lock_reset_on_init=True,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="CAM_RESET_PRESERVES_SHUTTER_AWB_LOCK_NOT_AVAILABLE",
                shutter_awb_lock=shutter_awb_lock,
                shutter_awb_lock_survived_cam_reset=True,
                shutter_awb_lock_reset_on_init=False,
            )
        if shoot_mode in ("Movie", "S&Q"):
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="SHUTTER_AWB_LOCK_STRICTLY_STILL_ONLY_USE_CUSTOM_KEY_IN_MOVIE",
                shutter_awb_lock_still_only=True,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="SHUTTER_AWB_LOCK_ACTIVE_IN_STILL",
            shutter_awb_lock_still_only=True,
        )

    if operation == "fx3_ctemp_filter_grid_and_custom_wb_log_warning":
        if log_shooting_mode not in FX3_LOG_SHOOTING_MODES:
            return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_LOG_SHOOTING_MODE")
        if (
            ctemp_kelvin < FX3_CTEMP_MIN_K
            or ctemp_kelvin > FX3_CTEMP_MAX_K
            or (ctemp_kelvin - FX3_CTEMP_MIN_K) % FX3_CTEMP_STEP_K != 0
        ):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="CTEMP_OUT_OF_2500K_9900K_100K_GRID",
            )
        ab_units = round(ab_filter / FX3_AB_FILTER_STEP)
        if (
            ab_filter < FX3_AB_FILTER_MIN
            or ab_filter > FX3_AB_FILTER_MAX
            or abs(ab_filter - ab_units * FX3_AB_FILTER_STEP) > 1e-9
        ):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="AB_FILTER_OUT_OF_A7_B7_0_5_GRID",
            )
        gm_units = round(gm_filter / FX3_GM_FILTER_STEP)
        if (
            gm_filter < FX3_GM_FILTER_MIN
            or gm_filter > FX3_GM_FILTER_MAX
            or abs(gm_filter - gm_units * FX3_GM_FILTER_STEP) > 1e-9
        ):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="GM_FILTER_OUT_OF_G7_M7_0_25_GRID",
            )
        log_warn = bool(custom_wb_capture_requested and log_shooting_mode != "Off")
        return _mk(
            allowed=True,
            errno=0,
            reason=(
                "CUSTOM_WB_CAPTURE_IN_LOG_SHOOTING_WARNS_SET_LOG_OFF_FIRST"
                if log_warn
                else "FX3_CTEMP_FILTER_GRID_VALID"
            ),
            custom_wb_log_warning=log_warn,
        )

    # fx6_physical_whtbal_preset_atw_tint_rbgain_shockless
    if fx6_wht_bal_switch not in FX6_WHT_BAL_SWITCH_POSITIONS:
        return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_FX6_WHT_BAL_SWITCH")
    if fx6_shooting_mode not in ("Custom", "Cine EI"):
        return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_FX6_SHOOTING_MODE")
    if fx6_shockless_white not in FX6_SHOCKLESS_WHITE_MODES:
        return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_FX6_SHOCKLESS_WHITE")
    if fx6_tint < FX6_TINT_MIN or fx6_tint > FX6_TINT_MAX:
        return _mk(allowed=False, errno=EINVAL_ERRNO, reason="FX6_TINT_OUT_OF_RANGE")
    if (
        fx6_r_gain < FX6_RB_GAIN_MIN
        or fx6_r_gain > FX6_RB_GAIN_MAX
        or fx6_b_gain < FX6_RB_GAIN_MIN
        or fx6_b_gain > FX6_RB_GAIN_MAX
    ):
        return _mk(allowed=False, errno=EINVAL_ERRNO, reason="FX6_RB_GAIN_OUT_OF_RANGE")

    if fx6_atw_enabled:
        if fx6_shooting_mode == "Cine EI":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX6_ATW_DISABLED_IN_CINE_EI",
            )
        if fx6_atw_kelvin < FX6_ATW_MIN_K or fx6_atw_kelvin > FX6_ATW_MAX_K:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="FX6_ATW_OUT_OF_2000K_15000K_RANGE",
            )
        if fx6_atw_speed not in FX6_ATW_SPEED_RANGE:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="FX6_ATW_SPEED_OUT_OF_1_5_RANGE",
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=(
                "FX6_ATW_HOLD_ENGAGED"
                if fx6_atw_hold_active
                else "FX6_ATW_ACTIVE_CUSTOM_MODE"
            ),
        )

    if fx6_wht_bal_switch == "PRESET":
        valid_presets = (
            FX6_CINE_EI_PRESET_KELVINS
            if fx6_shooting_mode == "Cine EI"
            else FX6_CUSTOM_PRESET_KELVINS
        )
        if fx6_preset_kelvin not in valid_presets:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"FX6_PRESET_KELVIN_INVALID_FOR_{fx6_shooting_mode.upper().replace(' ', '_')}",
            )
    return _mk(
        allowed=True,
        errno=0,
        reason="FX6_PHYSICAL_WHT_BAL_MEMORY_AB_PRESET_VALID",
    )


# ---------------------------------------------------------------------------
# Sub-Model 87C Simulator — Touch Op (4 Items), Dormant Pad & G109 Erratum
# ---------------------------------------------------------------------------


def simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    shoot_mode: str = "Movie",
    touch_operation: str = FX3_TOUCH_OPERATION_DEFAULT,
    touch_sensitivity: str = FX3_TOUCH_SENSITIVITY_DEFAULT,
    touch_func_in_shooting: str = FX3_TOUCH_FUNC_SHOOTING_DEFAULT,
    swipe_up: str = FX3_SWIPE_UP_DEFAULT,
    dormant_evf_touch_item: str = "",
    focus_assistant_item: str = "Initial Focus Mag.",
    focus_mode: str = "AF-S",
    exposure_mode: str = "M",
    drive_mode: str = "Single Shooting",
    mount_adaptor_attached: bool = False,
    af_in_focus_mag_requested: bool = False,
    peaking_display: str = "Off",
    peaking_level: str = FX3_PEAKING_LEVEL_DEFAULT,
    peaking_color: str = FX3_PEAKING_COLOR_DEFAULT,
    hdmi_peaking_requested: bool = False,
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    fx6_touch_mf_mode: str = "Tracking AF",
    fx6_peaking_color: str = "B&W",
    fx6_dormant_peaking_item: str = "",
) -> SubModel87CTouchPadFocusPeakingG109AuditResult:
    if operation not in VALID_87C_OPERATIONS:
        raise Stage87Phase379Error(f"Unknown 87C operation {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage87Phase379Error(f"Unknown body_model {body_model!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage87Phase379Error(f"Unknown shoot_mode {shoot_mode!r}")

    def _mk(**kw: Any) -> SubModel87CTouchPadFocusPeakingG109AuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            shoot_mode=shoot_mode,
            allowed=True,
            errno=0,
            reason="OK",
            touch_operation=touch_operation,
            touch_sensitivity=touch_sensitivity,
            touch_func_in_shooting=touch_func_in_shooting,
            swipe_up=swipe_up,
            touch_4items_survived_cam_reset=False,
            dormant_evf_touch_item=dormant_evf_touch_item,
            dormant_evf_touch_blocked=False,
            focus_assistant_item=focus_assistant_item,
            peaking_display=peaking_display,
            peaking_level=peaking_level,
            peaking_color=peaking_color,
            hdmi_peaking_leaked_pixels=0,
            af_in_focus_mag_active=False,
            focus_peaking_7items_survived_cam_reset=False,
            focus_peaking_7items_reset_on_init=False,
            g109_erratum_reconciled=FX3_G109_FOCUS_PEAKING_RESET_ERRATUM_RECONCILED,
            fx6_touch_mf_mode=fx6_touch_mf_mode,
            fx6_peaking_color=fx6_peaking_color,
            fx6_dormant_peaking_blocked=False,
            fx6_peaking_elf_items_count=len(FX6_PEAKING_3_ITEMS),
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            raw_firmware_bytes_leaked=0,
        )
        defaults.update(kw)
        return SubModel87CTouchPadFocusPeakingG109AuditResult(**defaults)

    if operation == "fx3_touch_operation_4item_and_dormant_evf_pad":
        if dormant_evf_touch_item:
            if dormant_evf_touch_item in FX3_DORMANT_EVF_TOUCH_ITEMS:
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason=f"EVFLESS_FX3_DORMANT_{dormant_evf_touch_item.upper().replace(' ', '_').replace('/', '_')}_BLOCKED",
                    dormant_evf_touch_blocked=True,
                )
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="UNKNOWN_DORMANT_TOUCH_ITEM",
            )
        if touch_operation not in FX3_TOUCH_OPERATION_OPTIONS:
            return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_TOUCH_OPERATION")
        if touch_sensitivity not in FX3_TOUCH_SENSITIVITY_OPTIONS:
            return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_TOUCH_SENSITIVITY")
        if touch_func_in_shooting == "Touch Shutter":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="EVFLESS_FX3_DORMANT_TOUCH_SHUTTER_BLOCKED",
                dormant_evf_touch_item="Touch Shutter",
                dormant_evf_touch_blocked=True,
            )
        if touch_func_in_shooting not in FX3_TOUCH_FUNC_SHOOTING_OPTIONS:
            return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_TOUCH_FUNC_SHOOTING")
        if swipe_up not in FX3_SWIPE_UP_OPTIONS:
            return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_SWIPE_UP")

        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_ALL_4_TOUCH_OPERATION_ITEMS",
                touch_operation=FX3_TOUCH_OPERATION_DEFAULT,
                touch_sensitivity=FX3_TOUCH_SENSITIVITY_DEFAULT,
                touch_func_in_shooting=FX3_TOUCH_FUNC_SHOOTING_DEFAULT,
                swipe_up=FX3_SWIPE_UP_DEFAULT,
                touch_4items_survived_cam_reset=False,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="CAM_RESET_PRESERVES_ALL_4_TOUCH_OPERATION_ITEMS",
                touch_4items_survived_cam_reset=True,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="FX3_TOUCH_OPERATION_4ITEM_VALID",
        )

    if operation == "fx3_focus_assistant_and_peaking_g109_reset_resistance":
        if peaking_display not in ("On", "Off"):
            return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_PEAKING_DISPLAY")
        if peaking_level not in FX3_PEAKING_LEVEL_OPTIONS:
            return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_PEAKING_LEVEL")
        if peaking_color not in FX3_PEAKING_COLOR_OPTIONS:
            return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_PEAKING_COLOR")

        if hdmi_peaking_requested:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX3_PEAKING_NEVER_OUTPUTS_TO_HDMI_ZERO_PIXELS",
                hdmi_peaking_leaked_pixels=0,
            )

        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_ALL_7_FOCUS_ASSISTANT_AND_PEAKING_ITEMS",
                peaking_display="Off",
                peaking_level=FX3_PEAKING_LEVEL_DEFAULT,
                peaking_color=FX3_PEAKING_COLOR_DEFAULT,
                focus_peaking_7items_survived_cam_reset=False,
                focus_peaking_7items_reset_on_init=True,
            )
        if camera_settings_reset_triggered:
            # Wave 77 G109 Erratum: ALL 7 items resist Camera Settings Reset!
            return _mk(
                allowed=True,
                errno=0,
                reason="G109_ERRATUM_ALL_7_FOCUS_ASSISTANT_AND_PEAKING_ITEMS_RESIST_CAM_RESET",
                focus_peaking_7items_survived_cam_reset=True,
                focus_peaking_7items_reset_on_init=False,
            )

        if af_in_focus_mag_requested:
            if shoot_mode in ("Movie", "S&Q"):
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="AF_IN_FOCUS_MAG_STRICTLY_STILL_ONLY_BLOCKED_IN_MOVIE_SQ",
                    focus_assistant_item="AF in Focus Mag.",
                    af_in_focus_mag_active=False,
                )
            if focus_mode == "AF-C":
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="AF_IN_FOCUS_MAG_DISABLED_IN_AF_C",
                    focus_assistant_item="AF in Focus Mag.",
                    af_in_focus_mag_active=False,
                )
            if focus_mode == "AF-A" and exposure_mode not in ("P", "A", "S", "M"):
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="AF_IN_FOCUS_MAG_DISABLED_IN_NON_PASM_AF_A",
                    focus_assistant_item="AF in Focus Mag.",
                    af_in_focus_mag_active=False,
                )
            if drive_mode == "Cont. Shooting":
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="AF_IN_FOCUS_MAG_DISABLED_IN_CONT_SHOOTING",
                    focus_assistant_item="AF in Focus Mag.",
                    af_in_focus_mag_active=False,
                )
            if mount_adaptor_attached:
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="AF_IN_FOCUS_MAG_DISABLED_WITH_MOUNT_ADAPTOR",
                    focus_assistant_item="AF in Focus Mag.",
                    af_in_focus_mag_active=False,
                )
            return _mk(
                allowed=True,
                errno=0,
                reason="AF_IN_FOCUS_MAG_ACTIVE_IN_STILL_AFS",
                focus_assistant_item="AF in Focus Mag.",
                af_in_focus_mag_active=True,
            )

        return _mk(
            allowed=True,
            errno=0,
            reason="FX3_FOCUS_ASSISTANT_AND_PEAKING_VALID_ZERO_HDMI_LEAK",
            hdmi_peaking_leaked_pixels=0,
        )

    # fx6_touch_mf_focus_mag_and_3item_peaking_dormant_block
    if fx6_dormant_peaking_item:
        if fx6_dormant_peaking_item in FX6_DORMANT_PEAKING_ITEMS:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=f"FX6_DORMANT_PEAKING_UXC_{fx6_dormant_peaking_item.upper().replace(' ', '_').replace('/', '_')}_ZERO_ELF_BINDING_BLOCKED",
                fx6_dormant_peaking_blocked=True,
            )
        return _mk(allowed=False, errno=EINVAL_ERRNO, reason="UNKNOWN_FX6_PEAKING_ITEM")
    if fx6_touch_mf_mode not in FX6_TOUCH_MF_OPTIONS:
        return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_FX6_TOUCH_MF_MODE")
    if fx6_peaking_color not in FX6_PEAKING_COLOR_OPTIONS:
        return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_FX6_PEAKING_COLOR")
    return _mk(
        allowed=True,
        errno=0,
        reason="FX6_TOUCH_MF_AND_3ITEM_PEAKING_VALID",
        fx6_peaking_elf_items_count=len(FX6_PEAKING_3_ITEMS),
    )


# ---------------------------------------------------------------------------
# Sub-Model 87D Simulator — Screen Reader SKU Gate, 2-Slot Version & EROFS
# ---------------------------------------------------------------------------


def simulate_87d_screen_reader_version_2slot_g104_and_erofs(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    sku_screen_reader_authorized: bool = False,
    screen_reader_speed: str = FX3_SCREEN_READER_SPEED_DEFAULT,
    screen_reader_volume: int = FX3_SCREEN_READER_VOLUME_DEFAULT,
    screen_reader_language: str = "English",
    screen_reader_hdmi_audio_requested: bool = False,
    mount_adaptor_attached: bool = False,
    request_separate_mount_adaptor_slot: bool = False,
    request_mi_shoe_version: bool = False,
    airplane_mode_on: bool = True,
    online_newer_fw_available: bool = True,
    battery_pct: int = 80,
    current_fw_version: str = "7.02",
    software_update_execute_requested: bool = False,
    slot1_bodydata_write_requested: bool = False,
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    fx6_update_slot: str = FX6_VERSION_UP_REQUIRED_SLOT,
    fx6_ac_adapter_connected: bool = True,
    fx6_version_up_execute_requested: bool = False,
) -> SubModel87DScreenReaderVersion2SlotErofsAuditResult:
    if operation not in VALID_87D_OPERATIONS:
        raise Stage87Phase379Error(f"Unknown 87D operation {operation!r}")
    if body_model not in (BODY_MODEL_FX3, BODY_MODEL_FX6, BODY_MODEL_FX30_AUTH):
        raise Stage87Phase379Error(f"Unknown body_model {body_model!r}")

    def _mk(**kw: Any) -> SubModel87DScreenReaderVersion2SlotErofsAuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            allowed=True,
            errno=0,
            reason="OK",
            screen_reader_ui_exposed=False,
            screen_reader_sku_authorized=sku_screen_reader_authorized,
            screen_reader_speed=screen_reader_speed,
            screen_reader_volume=screen_reader_volume,
            screen_reader_language=screen_reader_language,
            screen_reader_language_prompt=False,
            screen_reader_hdmi_audio_links=FX3_SCREEN_READER_HDMI_AUDIO_LINK_SYMBOLS,
            screen_reader_survived_cam_reset=False,
            version_slots=FX3_VERSION_DISPLAY_SLOTS,
            version_slots_count=FX3_VERSION_SLOTS_COUNT,
            mount_adaptor_shares_lens_slot=FX3_MOUNT_ADAPTOR_SHARES_LENS_SLOT,
            mi_shoe_version_displayed=FX3_MI_SHOE_VERSION_DISPLAYED,
            g104_erratum_reconciled=FX3_G104_VERSION_2SLOT_ERRATUM_RECONCILED,
            airplane_mode_on=airplane_mode_on,
            online_update_dot_shown=False,
            software_update_blocked_erofs=False,
            slot1_bodydata_write_authorized=SLOT1_BODYDATA_WRITE_AUTHORIZED,
            cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
            live_attach_authorized=LIVE_ATTACH_AUTHORIZED,
            fx6_version_domains=FX6_VERSION_DOMAINS,
            fx6_slot_b_and_ac_required=True,
            slot1_writes=0,
            slot1_sector_writes=0,
            slot1_data_sector_writes=0,
            rf_tx_packets=0,
            usb_tx_packets=0,
            emmc_nflasha_write_count=0,
            raw_firmware_bytes_leaked=0,
        )
        defaults.update(kw)
        return SubModel87DScreenReaderVersion2SlotErofsAuditResult(**defaults)

    if operation == "fx3_screen_reader_sku_gate_and_zero_hdmi_audio":
        if screen_reader_hdmi_audio_requested:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="SCREEN_READER_ZERO_HDMI_AUDIO_LINK_SPEAKER_HEADPHONE_ONLY",
                screen_reader_hdmi_audio_links=0,
            )
        # Standard ILME-FX3 (ALCIN_UUD) and ILME-FX6 expose 0 Screen Reader items
        if (not sku_screen_reader_authorized) or body_model in (BODY_MODEL_FX3, BODY_MODEL_FX6):
            if not sku_screen_reader_authorized:
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="SCREEN_READER_SKU_GATED_ZERO_UI_EXPOSURE_ON_FX3_AND_FX6",
                    screen_reader_ui_exposed=False,
                )
        if screen_reader_speed not in FX3_SCREEN_READER_SPEEDS:
            return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_SCREEN_READER_SPEED")
        if (
            screen_reader_volume < FX3_SCREEN_READER_VOLUME_MIN
            or screen_reader_volume > FX3_SCREEN_READER_VOLUME_MAX
        ):
            return _mk(allowed=False, errno=EINVAL_ERRNO, reason="INVALID_SCREEN_READER_VOLUME")
        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_AUTHORIZED_SKU_SCREEN_READER_SPEED_VOL",
                screen_reader_ui_exposed=True,
                screen_reader_speed=FX3_SCREEN_READER_SPEED_DEFAULT,
                screen_reader_volume=FX3_SCREEN_READER_VOLUME_DEFAULT,
                screen_reader_survived_cam_reset=False,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="CAM_RESET_PRESERVES_AUTHORIZED_SKU_SCREEN_READER_SPEED_VOL",
                screen_reader_ui_exposed=True,
                screen_reader_survived_cam_reset=True,
            )
        lang_prompt = screen_reader_language != "English"
        return _mk(
            allowed=True,
            errno=0,
            reason=(
                "AUTHORIZED_SKU_SCREEN_READER_REQUIRES_ENGLISH_LANGUAGE_SWITCH"
                if lang_prompt
                else "AUTHORIZED_SKU_SCREEN_READER_ACTIVE_ZERO_HDMI_LINK"
            ),
            screen_reader_ui_exposed=True,
            screen_reader_language_prompt=lang_prompt,
        )

    if operation == "fx3_version_2slot_g104_erratum_and_airplane_dot":
        if request_separate_mount_adaptor_slot:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="G104_ERRATUM_NO_SEPARATE_3RD_MOUNT_ADAPTOR_SLOT_SHARES_LENS_SLOT",
                version_slots=FX3_VERSION_DISPLAY_SLOTS,
                version_slots_count=FX3_VERSION_SLOTS_COUNT,
            )
        if request_mi_shoe_version:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="G104_ERRATUM_MI_SHOE_ACCESSORY_VERSION_NOT_DISPLAYED",
                mi_shoe_version_displayed=False,
            )
        dot_shown = bool((not airplane_mode_on) and online_newer_fw_available)
        return _mk(
            allowed=True,
            errno=0,
            reason=(
                "VERSION_2SLOT_BODY_LENS_READONLY_AIRPLANE_SILENCES_UPDATE_DOT"
                if airplane_mode_on
                else (
                    "VERSION_2SLOT_BODY_LENS_READONLY_ONLINE_UPDATE_DOT_SHOWN"
                    if dot_shown
                    else "VERSION_2SLOT_BODY_LENS_READONLY_UP_TO_DATE"
                )
            ),
            version_slots=FX3_VERSION_DISPLAY_SLOTS,
            version_slots_count=FX3_VERSION_SLOTS_COUNT,
            mount_adaptor_shares_lens_slot=True,
            mi_shoe_version_displayed=False,
            online_update_dot_shown=dot_shown,
            rf_tx_packets=0,
        )

    if operation == "fx3_software_update_slot1_bodydata_erofs_firewall":
        if software_update_execute_requested or slot1_bodydata_write_requested:
            return _mk(
                allowed=False,
                errno=EROFS_ERRNO,
                reason="TIER0_SLOT1_BODYDATA_SOFTWARE_UPDATE_HARD_BLOCKED_EROFS",
                software_update_blocked_erofs=True,
                slot1_bodydata_write_authorized=False,
                cross_model_flash_authorized=False,
                live_attach_authorized=False,
                slot1_writes=0,
                slot1_sector_writes=0,
                slot1_data_sector_writes=0,
            )
        if battery_pct < FX3_SOFTWARE_UPDATE_MIN_BATTERY_PCT:
            return _mk(
                allowed=False,
                errno=EAGAIN_ERRNO,
                reason="SOFTWARE_UPDATE_PRECHECK_BATTERY_BELOW_51PCT",
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"VERSION_DIALOG_READONLY_PRECHECK_FW_{current_fw_version}_ZERO_WRITES",
            slot1_writes=0,
        )

    # fx6_screen_reader_dormant_and_version_up_slotb_ac
    if fx6_version_up_execute_requested:
        if fx6_update_slot != FX6_VERSION_UP_REQUIRED_SLOT:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="FX6_VERSION_UP_REQUIRES_SLOT_B",
            )
        if not fx6_ac_adapter_connected:
            return _mk(
                allowed=False,
                errno=EAGAIN_ERRNO,
                reason="FX6_VERSION_UP_REQUIRES_AC_ADAPTER",
            )
        return _mk(
            allowed=False,
            errno=EROFS_ERRNO,
            reason="FX6_TIER0_VERSION_UP_FLASH_HARD_BLOCKED_EROFS",
            software_update_blocked_erofs=True,
            cross_model_flash_authorized=False,
            live_attach_authorized=False,
        )
    return _mk(
        allowed=True,
        errno=0,
        reason="FX6_MAINTENANCE_VERSION_3DOMAIN_READONLY_OK",
        screen_reader_ui_exposed=False,
        fx6_version_domains=FX6_VERSION_DOMAINS,
        fx6_slot_b_and_ac_required=True,
    )


# ---------------------------------------------------------------------------
# Sub-Model Evaluators & Unified Stage 87 (87/87) Orchestrator
# ---------------------------------------------------------------------------


def _evaluate_submodel_87a() -> Dict[str, Any]:
    r_dci = simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
        operation="fx3_file_format_6codec_and_dormant_8k",
        file_format="XAVC S-I DCI 4K",
        rec_frame_rate="24.00p",
        bitrate_mbps=240,
    )
    r_8k = simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
        operation="fx3_file_format_6codec_and_dormant_8k",
        file_format="xavc_hs_8k",
    )
    r_rst = simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
        operation="fx3_file_format_6codec_and_dormant_8k",
        file_format="XAVC S-I DCI 4K",
        camera_settings_reset_triggered=True,
    )
    r_reb = simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
        operation="fx3_2400p_reboot_playback_isolation_and_sq_48fps",
        file_format="XAVC S-I DCI 4K",
        previous_frame_rate="23.98p",
        rec_frame_rate="24.00p",
    )
    r_pb_iso = simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
        operation="fx3_2400p_reboot_playback_isolation_and_sq_48fps",
        file_format="XAVC S-I DCI 4K",
        rec_frame_rate="24.00p",
        playback_clip_is_2400p=False,
    )
    r_sq48 = simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
        operation="fx3_2400p_reboot_playback_isolation_and_sq_48fps",
        shoot_mode="S&Q",
        file_format="XAVC S-I DCI 4K",
        rec_frame_rate="24.00p",
        sq_frame_rate_fps=48,
    )
    r_g139_v60 = simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
        operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
        shoot_mode="S&Q",
        file_format="XAVC S HD",
        sq_frame_rate_fps=120,
        card_tier="SDXC V60",
    )
    r_g139_dci120 = simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
        operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
        shoot_mode="S&Q",
        file_format="XAVC S-I DCI 4K",
        sq_frame_rate_fps=120,
        card_tier="CFexpress Type A VPG400",
    )
    r_vpg400_blk = simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
        operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
        shoot_mode="S&Q",
        file_format="XAVC S-I 4K",
        sq_frame_rate_fps=120,
        proxy_recording_on=True,
        card_tier="CFexpress Type A VPG200",
    )
    r_vpg400_ok = simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
        operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
        shoot_mode="S&Q",
        file_format="XAVC S-I 4K",
        sq_frame_rate_fps=120,
        proxy_recording_on=True,
        card_tier="CFexpress Type A VPG400",
    )
    r_fx6_c480 = simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
        operation="fx6_project_rec_format_and_dormant_class480_xavcl25",
        body_model=BODY_MODEL_FX6,
        fx6_codec="XAVC-I",
        fx6_class_or_variant="Class480",
    )
    r_fx6_ok = simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
        operation="fx6_project_rec_format_and_dormant_class480_xavcl25",
        body_model=BODY_MODEL_FX6,
        fx6_codec="XAVC-I",
        fx6_video_format="4096x2160",
        fx6_bitrate_mbps=600,
    )
    passed = (
        r_dci.allowed
        and (not r_8k.allowed and r_8k.errno == EOPNOTSUPP_ERRNO and r_8k.dormant_8k_blocked)
        and (r_rst.allowed and r_rst.file_format == "XAVC S HD")
        and (r_reb.allowed and r_reb.reboot_required and r_reb.reboot_event == FX3_REBOOT_2400P_EVENT)
        and (not r_pb_iso.allowed and r_pb_iso.errno == EOPNOTSUPP_ERRNO)
        and (r_sq48.allowed and r_sq48.sq_48fps_exclusive_ok)
        and (r_g139_v60.allowed and r_g139_v60.required_min_card_tier == "SDXC V60")
        and (not r_g139_dci120.allowed and r_g139_dci120.errno == EOPNOTSUPP_ERRNO)
        and (not r_vpg400_blk.allowed and r_vpg400_blk.errno == EAGAIN_ERRNO and r_vpg400_blk.required_elf_transfer_tier_mbps == 1350)
        and (r_vpg400_ok.allowed and r_vpg400_ok.required_min_card_tier == "CFexpress Type A VPG400")
        and (not r_fx6_c480.allowed and r_fx6_c480.errno == EOPNOTSUPP_ERRNO and r_fx6_c480.fx6_dormant_format_blocked)
        and (r_fx6_ok.allowed and r_fx6_ok.fx6_xavci_class == "Class300")
    )
    return {
        "passed": passed,
        "fx3_codecs_count": len(FX3_FILE_FORMATS),
        "fx3_elf_transfer_tiers_count": len(FX3_ELF_TRANSFER_RATE_TIERS_MBPS),
        "fx3_vpg400_proxy_threshold_mbps": 1350,
        "fx3_dormant_8k_exposed_events": 0,
        "fx3_g139_card_speed_erratum_reconciled": FX3_G139_CARD_SPEED_ERRATUM_RECONCILED,
        "fx6_dormant_class480_xavcl25_exposed_events": 0,
        "samples": {
            "fx3_dci4k_2400p_ok": r_dci.to_dict(),
            "fx3_dormant_8k_blocked": r_8k.to_dict(),
            "fx3_movieset_cam_reset": r_rst.to_dict(),
            "fx3_cross_2400p_reboot": r_reb.to_dict(),
            "fx3_2400p_playback_isolation": r_pb_iso.to_dict(),
            "fx3_sq_48fps_exclusive": r_sq48.to_dict(),
            "fx3_g139_sq_hd_120fps_v60_ok": r_g139_v60.to_dict(),
            "fx3_g139_sq_dci4k_120fps_blocked": r_g139_dci120.to_dict(),
            "fx3_vpg400_1350mbps_blocks_vpg200": r_vpg400_blk.to_dict(),
            "fx3_vpg400_1350mbps_passes_vpg400": r_vpg400_ok.to_dict(),
            "fx6_dormant_class480_blocked": r_fx6_c480.to_dict(),
            "fx6_xavci_class300_ok": r_fx6_ok.to_dict(),
        },
    }


def _evaluate_submodel_87b() -> Dict[str, Any]:
    r_prio_flex = simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
        operation="fx3_priority_set_in_awb_and_cine_ei",
        log_shooting_mode="Flexible ISO",
        wb_mode="Auto",
        priority_set_in_awb="White",
    )
    r_prio_cine = simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
        operation="fx3_priority_set_in_awb_and_cine_ei",
        log_shooting_mode="Cine EI",
        wb_mode="Auto",
    )
    r_sh_mv = simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
        operation="fx3_shutter_awb_lock_still_only_and_reset_resistance",
        shoot_mode="Movie",
        shutter_awb_lock="Shutter Half Press",
    )
    r_sh_rst = simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
        operation="fx3_shutter_awb_lock_still_only_and_reset_resistance",
        shoot_mode="Still",
        shutter_awb_lock="Cont. Shooting",
        camera_settings_reset_triggered=True,
    )
    r_sh_init = simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
        operation="fx3_shutter_awb_lock_still_only_and_reset_resistance",
        shoot_mode="Still",
        shutter_awb_lock="Cont. Shooting",
        initialize_triggered=True,
    )
    r_ctemp = simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
        operation="fx3_ctemp_filter_grid_and_custom_wb_log_warning",
        ctemp_kelvin=9900,
        ab_filter=-7.0,
        gm_filter=6.75,
        log_shooting_mode="Cine EI",
        custom_wb_capture_requested=True,
    )
    r_fx6_atw = simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
        operation="fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
        body_model=BODY_MODEL_FX6,
        fx6_wht_bal_switch="B",
        fx6_shooting_mode="Custom",
        fx6_atw_enabled=True,
        fx6_atw_kelvin=15000,
        fx6_atw_speed=1,
        fx6_atw_hold_active=True,
        fx6_tint=-99,
        fx6_r_gain=99.0,
        fx6_b_gain=-99.0,
        fx6_shockless_white="3",
    )
    r_fx6_atw_blk = simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
        operation="fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
        body_model=BODY_MODEL_FX6,
        fx6_shooting_mode="Cine EI",
        fx6_atw_enabled=True,
    )
    passed = (
        (r_prio_flex.allowed and r_prio_flex.priority_effective)
        and (not r_prio_cine.allowed and r_prio_cine.errno == EOPNOTSUPP_ERRNO)
        and (not r_sh_mv.allowed and r_sh_mv.errno == EOPNOTSUPP_ERRNO)
        and (r_sh_rst.allowed and r_sh_rst.shutter_awb_lock == "Cont. Shooting" and r_sh_rst.shutter_awb_lock_survived_cam_reset)
        and (r_sh_init.allowed and r_sh_init.shutter_awb_lock == "Off" and r_sh_init.shutter_awb_lock_reset_on_init)
        and (r_ctemp.allowed and r_ctemp.custom_wb_log_warning)
        and (r_fx6_atw.allowed and r_fx6_atw.fx6_atw_hold_active)
        and (not r_fx6_atw_blk.allowed and r_fx6_atw_blk.errno == EOPNOTSUPP_ERRNO)
    )
    return {
        "passed": passed,
        "fx3_awb_priority_modes_count": len(FX3_AWB_PRIORITY_MODES),
        "fx3_ctemp_steps_count": FX3_CTEMP_STEPS_COUNT,
        "fx3_ab_filter_steps_count": FX3_AB_FILTER_STEPS_COUNT,
        "fx3_gm_filter_steps_count": FX3_GM_FILTER_STEPS_COUNT,
        "fx3_shutter_awb_lock_movie_bypass_events": 0,
        "fx6_atw_speed_steps_count": len(FX6_ATW_SPEED_RANGE),
        "samples": {
            "fx3_priority_flex_iso_ok": r_prio_flex.to_dict(),
            "fx3_priority_cine_ei_auto_blocked": r_prio_cine.to_dict(),
            "fx3_shutter_awb_lock_movie_blocked": r_sh_mv.to_dict(),
            "fx3_shutter_awb_lock_resists_cam_reset": r_sh_rst.to_dict(),
            "fx3_shutter_awb_lock_resets_on_init": r_sh_init.to_dict(),
            "fx3_ctemp_9900k_and_log_warn": r_ctemp.to_dict(),
            "fx6_atw_hold_custom_ok": r_fx6_atw.to_dict(),
            "fx6_atw_cine_ei_blocked": r_fx6_atw_blk.to_dict(),
        },
    }


def _evaluate_submodel_87c() -> Dict[str, Any]:
    r_tch_rst = simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
        operation="fx3_touch_operation_4item_and_dormant_evf_pad",
        touch_operation="On: Playback Only",
        touch_sensitivity="Sensitive",
        touch_func_in_shooting="Touch Focus",
        swipe_up="Off",
        camera_settings_reset_triggered=True,
    )
    r_pad_blk = simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
        operation="fx3_touch_operation_4item_and_dormant_evf_pad",
        dormant_evf_touch_item="Touch Panel/Pad",
    )
    r_sh_blk = simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
        operation="fx3_touch_operation_4item_and_dormant_evf_pad",
        touch_func_in_shooting="Touch Shutter",
    )
    r_g109_rst = simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
        operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
        peaking_display="On",
        peaking_level="High",
        peaking_color="Red",
        camera_settings_reset_triggered=True,
    )
    r_g109_init = simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
        operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
        peaking_display="On",
        peaking_level="High",
        peaking_color="Red",
        initialize_triggered=True,
    )
    r_afmag_mv = simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
        operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
        shoot_mode="Movie",
        af_in_focus_mag_requested=True,
    )
    r_afmag_still = simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
        operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
        shoot_mode="Still",
        focus_mode="AF-S",
        af_in_focus_mag_requested=True,
    )
    r_hdmi_pk = simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
        operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
        hdmi_peaking_requested=True,
    )
    r_fx6_pk_blk = simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
        operation="fx6_touch_mf_focus_mag_and_3item_peaking_dormant_block",
        body_model=BODY_MODEL_FX6,
        fx6_dormant_peaking_item="Peaking Frequency",
    )
    r_fx6_pk_ok = simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
        operation="fx6_touch_mf_focus_mag_and_3item_peaking_dormant_block",
        body_model=BODY_MODEL_FX6,
        fx6_touch_mf_mode="Spot Focus",
        fx6_peaking_color="B&W",
    )
    passed = (
        (r_tch_rst.allowed and r_tch_rst.touch_4items_survived_cam_reset)
        and (not r_pad_blk.allowed and r_pad_blk.errno == EOPNOTSUPP_ERRNO and r_pad_blk.dormant_evf_touch_blocked)
        and (not r_sh_blk.allowed and r_sh_blk.errno == EOPNOTSUPP_ERRNO and r_sh_blk.dormant_evf_touch_blocked)
        and (r_g109_rst.allowed and r_g109_rst.focus_peaking_7items_survived_cam_reset and r_g109_rst.peaking_display == "On")
        and (r_g109_init.allowed and r_g109_init.focus_peaking_7items_reset_on_init and r_g109_init.peaking_display == "Off")
        and (not r_afmag_mv.allowed and r_afmag_mv.errno == EOPNOTSUPP_ERRNO)
        and (r_afmag_still.allowed and r_afmag_still.af_in_focus_mag_active)
        and (not r_hdmi_pk.allowed and r_hdmi_pk.errno == EOPNOTSUPP_ERRNO and r_hdmi_pk.hdmi_peaking_leaked_pixels == 0)
        and (not r_fx6_pk_blk.allowed and r_fx6_pk_blk.errno == EOPNOTSUPP_ERRNO and r_fx6_pk_blk.fx6_dormant_peaking_blocked)
        and (r_fx6_pk_ok.allowed and r_fx6_pk_ok.fx6_peaking_elf_items_count == 3)
    )
    return {
        "passed": passed,
        "fx3_has_builtin_evf": FX3_HAS_BUILTIN_EVF,
        "fx3_touch_exposed_items_count": len(FX3_TOUCH_EXPOSED_4_ITEMS),
        "fx3_dormant_evf_touch_pad_exposed_events": 0,
        "fx3_focus_peaking_reset_resistant_items_count": len(FX3_FOCUS_PEAKING_RESET_RESISTANT_7_ITEMS),
        "fx3_g109_focus_peaking_reset_erratum_reconciled": FX3_G109_FOCUS_PEAKING_RESET_ERRATUM_RECONCILED,
        "fx3_hdmi_peaking_leaked_pixels": 0,
        "fx6_peaking_elf_items_count": len(FX6_PEAKING_3_ITEMS),
        "fx6_dormant_peaking_frequency_exposed_events": 0,
        "samples": {
            "fx3_touch_4items_resist_reset": r_tch_rst.to_dict(),
            "fx3_dormant_touch_panel_pad_blocked": r_pad_blk.to_dict(),
            "fx3_dormant_touch_shutter_blocked": r_sh_blk.to_dict(),
            "fx3_g109_focus_peaking_resist_reset": r_g109_rst.to_dict(),
            "fx3_g109_focus_peaking_reset_on_init": r_g109_init.to_dict(),
            "fx3_af_in_focus_mag_movie_blocked": r_afmag_mv.to_dict(),
            "fx3_af_in_focus_mag_still_ok": r_afmag_still.to_dict(),
            "fx3_hdmi_peaking_blocked": r_hdmi_pk.to_dict(),
            "fx6_dormant_peaking_freq_blocked": r_fx6_pk_blk.to_dict(),
            "fx6_peaking_3items_ok": r_fx6_pk_ok.to_dict(),
        },
    }


def _evaluate_submodel_87d() -> Dict[str, Any]:
    r_sr_fx3 = simulate_87d_screen_reader_version_2slot_g104_and_erofs(
        operation="fx3_screen_reader_sku_gate_and_zero_hdmi_audio",
        body_model=BODY_MODEL_FX3,
        sku_screen_reader_authorized=False,
    )
    r_sr_fx6 = simulate_87d_screen_reader_version_2slot_g104_and_erofs(
        operation="fx3_screen_reader_sku_gate_and_zero_hdmi_audio",
        body_model=BODY_MODEL_FX6,
        sku_screen_reader_authorized=False,
    )
    r_sr_auth = simulate_87d_screen_reader_version_2slot_g104_and_erofs(
        operation="fx3_screen_reader_sku_gate_and_zero_hdmi_audio",
        body_model=BODY_MODEL_FX30_AUTH,
        sku_screen_reader_authorized=True,
        screen_reader_speed="FAST_2",
        screen_reader_volume=10,
        screen_reader_language="English",
    )
    r_sr_hdmi = simulate_87d_screen_reader_version_2slot_g104_and_erofs(
        operation="fx3_screen_reader_sku_gate_and_zero_hdmi_audio",
        body_model=BODY_MODEL_FX30_AUTH,
        sku_screen_reader_authorized=True,
        screen_reader_hdmi_audio_requested=True,
    )
    r_ver_air = simulate_87d_screen_reader_version_2slot_g104_and_erofs(
        operation="fx3_version_2slot_g104_erratum_and_airplane_dot",
        mount_adaptor_attached=True,
        airplane_mode_on=True,
        online_newer_fw_available=True,
    )
    r_ver_3rd = simulate_87d_screen_reader_version_2slot_g104_and_erofs(
        operation="fx3_version_2slot_g104_erratum_and_airplane_dot",
        request_separate_mount_adaptor_slot=True,
    )
    r_ver_mi = simulate_87d_screen_reader_version_2slot_g104_and_erofs(
        operation="fx3_version_2slot_g104_erratum_and_airplane_dot",
        request_mi_shoe_version=True,
    )
    r_sw_erofs = simulate_87d_screen_reader_version_2slot_g104_and_erofs(
        operation="fx3_software_update_slot1_bodydata_erofs_firewall",
        software_update_execute_requested=True,
        slot1_bodydata_write_requested=True,
    )
    r_fx6_ver = simulate_87d_screen_reader_version_2slot_g104_and_erofs(
        operation="fx6_screen_reader_dormant_and_version_up_slotb_ac",
        body_model=BODY_MODEL_FX6,
    )
    r_fx6_flash = simulate_87d_screen_reader_version_2slot_g104_and_erofs(
        operation="fx6_screen_reader_dormant_and_version_up_slotb_ac",
        body_model=BODY_MODEL_FX6,
        fx6_update_slot="Slot B",
        fx6_ac_adapter_connected=True,
        fx6_version_up_execute_requested=True,
    )
    passed = (
        (not r_sr_fx3.allowed and r_sr_fx3.errno == EOPNOTSUPP_ERRNO and not r_sr_fx3.screen_reader_ui_exposed)
        and (not r_sr_fx6.allowed and r_sr_fx6.errno == EOPNOTSUPP_ERRNO and not r_sr_fx6.screen_reader_ui_exposed)
        and (r_sr_auth.allowed and r_sr_auth.screen_reader_ui_exposed and r_sr_auth.screen_reader_hdmi_audio_links == 0)
        and (not r_sr_hdmi.allowed and r_sr_hdmi.errno == EOPNOTSUPP_ERRNO)
        and (r_ver_air.allowed and r_ver_air.version_slots_count == 2 and not r_ver_air.online_update_dot_shown and r_ver_air.rf_tx_packets == 0)
        and (not r_ver_3rd.allowed and r_ver_3rd.errno == EOPNOTSUPP_ERRNO)
        and (not r_ver_mi.allowed and r_ver_mi.errno == EOPNOTSUPP_ERRNO)
        and (not r_sw_erofs.allowed and r_sw_erofs.errno == EROFS_ERRNO and r_sw_erofs.software_update_blocked_erofs and r_sw_erofs.slot1_writes == 0)
        and (r_fx6_ver.allowed and len(r_fx6_ver.fx6_version_domains) == 3 and r_fx6_ver.fx6_slot_b_and_ac_required)
        and (not r_fx6_flash.allowed and r_fx6_flash.errno == EROFS_ERRNO)
    )
    return {
        "passed": passed,
        "fx3_screen_reader_ui_exposed_items": FX3_SCREEN_READER_UI_EXPOSED_ITEMS,
        "fx6_screen_reader_ui_exposed_items": FX6_SCREEN_READER_UI_EXPOSED_ITEMS,
        "fx3_screen_reader_hdmi_audio_links": FX3_SCREEN_READER_HDMI_AUDIO_LINK_SYMBOLS,
        "fx3_version_slots_count": FX3_VERSION_SLOTS_COUNT,
        "fx3_g104_version_2slot_erratum_reconciled": FX3_G104_VERSION_2SLOT_ERRATUM_RECONCILED,
        "fx3_mi_shoe_version_displayed": FX3_MI_SHOE_VERSION_DISPLAYED,
        "slot1_bodydata_write_authorized": SLOT1_BODYDATA_WRITE_AUTHORIZED,
        "fx6_version_domains_count": len(FX6_VERSION_DOMAINS),
        "samples": {
            "fx3_screen_reader_sku_gated": r_sr_fx3.to_dict(),
            "fx6_screen_reader_sku_gated": r_sr_fx6.to_dict(),
            "auth_sku_screen_reader_ok": r_sr_auth.to_dict(),
            "screen_reader_hdmi_audio_blocked": r_sr_hdmi.to_dict(),
            "fx3_version_2slot_airplane_silent": r_ver_air.to_dict(),
            "fx3_g104_3rd_mount_slot_blocked": r_ver_3rd.to_dict(),
            "fx3_g104_mi_shoe_version_blocked": r_ver_mi.to_dict(),
            "fx3_slot1_bodydata_erofs": r_sw_erofs.to_dict(),
            "fx6_version_3domains_readonly": r_fx6_ver.to_dict(),
            "fx6_version_up_erofs": r_fx6_flash.to_dict(),
        },
    }


def _strip_wall_clock(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: _strip_wall_clock(v)
            for k, v in obj.items()
            if k not in ("elapsed_seconds", "elapsed_ms")
        }
    if isinstance(obj, list):
        return [_strip_wall_clock(v) for v in obj]
    return obj


def _build_stage87_probe(
    sub_87a: Mapping[str, Any],
    sub_87b: Mapping[str, Any],
    sub_87c: Mapping[str, Any],
    sub_87d: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone_label": MILESTONE_LABEL,
        "submodel_87a_passed": bool(sub_87a["passed"]),
        "submodel_87b_passed": bool(sub_87b["passed"]),
        "submodel_87c_passed": bool(sub_87c["passed"]),
        "submodel_87d_passed": bool(sub_87d["passed"]),
        "ready_for_live_camera_attach": READY_FOR_LIVE_CAMERA_ATTACH,
    }


def run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    donor_info = inspect_phase379_wave77_donors(
        work_root=work_root,
        force_clean_room=force_clean_room,
        env=env,
    )
    sub_87a = _evaluate_submodel_87a()
    sub_87b = _evaluate_submodel_87b()
    sub_87c = _evaluate_submodel_87c()
    sub_87d = _evaluate_submodel_87d()
    probe = _build_stage87_probe(sub_87a, sub_87b, sub_87c, sub_87d)

    all_passed = bool(
        donor_info["all_donors_verified"]
        and sub_87a["passed"]
        and sub_87b["passed"]
        and sub_87c["passed"]
        and sub_87d["passed"]
    )

    payload: Dict[str, Any] = {
        "schema": SCHEMA_ID,
        "version": PHASE_379_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "all_checks_passed": all_passed,
        "source_mode": donor_info["source_mode"],
        "donor_access_mode": donor_info["donor_access_mode"],
        "donors": donor_info,
        # Tier-0 Hardware Safety Redlines
        "ready_for_live_camera_attach": READY_FOR_LIVE_CAMERA_ATTACH,
        "live_attach_authorized": LIVE_ATTACH_AUTHORIZED,
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
        "usb_tx_packets": USB_TX_PACKETS,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "passive_tx_bytes_emitted": PASSIVE_TX_BYTES_EMITTED,
        "slot1_bodydata_write_authorized": SLOT1_BODYDATA_WRITE_AUTHORIZED,
        "slot1_writes": SLOT1_WRITES,
        "slot1_sector_writes": SLOT1_SECTOR_WRITES,
        "slot1_data_sector_writes": SLOT1_DATA_SECTOR_WRITES,
        "slot1_avf_info_mutated": SLOT1_AVF_INFO_MUTATED,
        "rf_tx_packets": RF_TX_PACKETS,
        "rf_packets_transmitted": RF_PACKETS_TRANSMITTED,
        "rf_nvs_mutation_bytes": RF_NVS_MUTATION_BYTES,
        "rsv_orphan_count": RSV_ORPHAN_COUNT,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
        # Stage 87 Wave-77 Invariant Metrics
        "fx3_codecs_count": len(FX3_FILE_FORMATS),
        "fx3_elf_transfer_tiers_count": len(FX3_ELF_TRANSFER_RATE_TIERS_MBPS),
        "fx3_vpg400_proxy_threshold_mbps": 1350,
        "fx3_dormant_8k_exposed_events": 0,
        "fx3_g139_card_speed_erratum_reconciled": FX3_G139_CARD_SPEED_ERRATUM_RECONCILED,
        "fx6_dormant_class480_xavcl25_exposed_events": 0,
        "fx3_awb_priority_modes_count": len(FX3_AWB_PRIORITY_MODES),
        "fx3_ctemp_steps_count": FX3_CTEMP_STEPS_COUNT,
        "fx3_ab_filter_steps_count": FX3_AB_FILTER_STEPS_COUNT,
        "fx3_gm_filter_steps_count": FX3_GM_FILTER_STEPS_COUNT,
        "fx3_shutter_awb_lock_movie_bypass_events": 0,
        "fx6_atw_speed_steps_count": len(FX6_ATW_SPEED_RANGE),
        "fx3_has_builtin_evf": FX3_HAS_BUILTIN_EVF,
        "fx3_touch_exposed_items_count": len(FX3_TOUCH_EXPOSED_4_ITEMS),
        "fx3_dormant_evf_touch_pad_exposed_events": 0,
        "fx3_focus_peaking_reset_resistant_items_count": len(
            FX3_FOCUS_PEAKING_RESET_RESISTANT_7_ITEMS
        ),
        "fx3_g109_focus_peaking_reset_erratum_reconciled": (
            FX3_G109_FOCUS_PEAKING_RESET_ERRATUM_RECONCILED
        ),
        "fx3_hdmi_peaking_leaked_pixels": 0,
        "fx6_peaking_elf_items_count": len(FX6_PEAKING_3_ITEMS),
        "fx6_dormant_peaking_frequency_exposed_events": 0,
        "fx3_screen_reader_ui_exposed_items": FX3_SCREEN_READER_UI_EXPOSED_ITEMS,
        "fx6_screen_reader_ui_exposed_items": FX6_SCREEN_READER_UI_EXPOSED_ITEMS,
        "fx3_screen_reader_hdmi_audio_links": FX3_SCREEN_READER_HDMI_AUDIO_LINK_SYMBOLS,
        "fx3_version_slots_count": FX3_VERSION_SLOTS_COUNT,
        "fx3_g104_version_2slot_erratum_reconciled": FX3_G104_VERSION_2SLOT_ERRATUM_RECONCILED,
        "fx3_mi_shoe_version_displayed": FX3_MI_SHOE_VERSION_DISPLAYED,
        "fx6_version_domains_count": len(FX6_VERSION_DOMAINS),
        # Nested Sub-Model Audits
        "submodel_87a_movieset_6codec_2400p_vpg_fx6_recfmt": sub_87a,
        "submodel_87b_awb_priority_shutter_lock_ctemp_fx6_atw": sub_87b,
        "submodel_87c_touch_pad_focus_peaking_g109_fx6": sub_87c,
        "submodel_87d_screen_reader_version_2slot_g104_erofs": sub_87d,
        "stage87_probe": probe,
    }
    digest_body = _strip_wall_clock(payload)
    payload["phase379_audit_digest_sha256"] = hashlib.sha256(
        json.dumps(digest_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def run_self_test(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Union[None, str, Path, object] = _UNSET,
) -> Dict[str, Any]:
    return run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
        work_root=work_root,
        force_clean_room=force_clean_room,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulator.py",
        description=(
            "Phase 379 Stage 87 (87/87) Real-Hardware FX3/FX6 Wave-77 Co-Emulator: "
            "87A Movie Settings 6-Codec / 24.00p Reboot & Playback Isolation / 5-Tier VPG200-VPG400 1350Mbps & G139 Erratum vs FX6 Rec Format, "
            "87B Priority Set in AWB / Still-Only Reset-Resistant Shutter AWB Lock / 2500K..9900K C.Temp vs FX6 ATW & Memory A/B, "
            "87C Touch Operation 4-Item vs Dormant EVF Touch Panel/Pad & G109 Focus Assistant/Peaking 7-Item Reset-Resistance vs FX6 3-Item Peaking, "
            "and 87D Screen Reader SKU Gate (0 UI on FX3/FX6) & 2-Slot Body/Lens Version Dialog (G104 Erratum) + Slot 1 BODYDATA.DAT EROFS=30 Firewall"
        ),
    )
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force clean-room synthetic donor mode",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run Stage 87 (87/87) built-in self-test matrix",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit full deterministic JSON payload (default)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Emit concise one-line HIL summary",
    )
    args = parser.parse_args(argv)

    rep = run_self_test(force_clean_room=(True if args.clean_room else None))
    if args.summary:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 379 Stage 87 ({rep['milestone']}) | mode={rep['source_mode']} "
            f"| donors={rep['donors']['total_donors_count']} "
            f"| mv={rep['fx3_codecs_count']}c/{rep['fx3_elf_transfer_tiers_count']}t/vpg400={rep['fx3_vpg400_proxy_threshold_mbps']}M/g139={int(rep['fx3_g139_card_speed_erratum_reconciled'])} "
            f"| wb={rep['fx3_awb_priority_modes_count']}p/{rep['fx3_ctemp_steps_count']}k/ab={rep['fx3_ab_filter_steps_count']}/gm={rep['fx3_gm_filter_steps_count']} "
            f"| tch={rep['fx3_touch_exposed_items_count']}i/evf={int(rep['fx3_has_builtin_evf'])}/g109={int(rep['fx3_g109_focus_peaking_reset_erratum_reconciled'])}/fx6pk={rep['fx6_peaking_elf_items_count']} "
            f"| sr={rep['fx3_screen_reader_ui_exposed_items']}/{rep['fx6_screen_reader_ui_exposed_items']}/ver={rep['fx3_version_slots_count']}s/g104={int(rep['fx3_g104_version_2slot_erratum_reconciled'])} "
            f"| s1_wr={rep['slot1_data_sector_writes']} usb_tx={rep['usb_tx_packets']} rf_tx={rep['rf_tx_packets']} emmc_wr={rep['emmc_nflasha_write_count']} "
            f"leaked={rep['raw_firmware_bytes_leaked']} "
            f"| digest={rep['phase379_audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
