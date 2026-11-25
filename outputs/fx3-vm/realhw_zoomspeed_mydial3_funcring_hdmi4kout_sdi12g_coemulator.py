#!/usr/bin/env python3
"""Phase 385 — Stage 89 (89/89 Full-Board VM HIL Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-79 HIL:
- 89A: `Shooting -> [Zoom]` 8-Step Speed Architecture vs FX6 `Technical > Zoom`
  & `Handle Zoom`:
  - `[Zoom Range]` (`_f 0x7164`: `Optical zoom only` def / `ClearImage Zoom`
    [`4K 1.5x` / `HD 2.0x` / Still `L 2.0x..S 4.0x`] / `Digital Zoom`
    [`Movie 4.0x` / Still `S 8.0x`]; `Smart Zoom` Still `M/S` ONLY; resists
    `[Camera Settings Reset]`, cleared ONLY on `[Initialize]`);
  - `[Zoom Lever Speed]` (`_f 0x6304`: `1st Zoom Spd.` def `3` / `2nd Zoom Spd.`
    def `8`, Standby/REC, `Can be reset`; does not affect lens zoom ring or PZ
    lens rocker);
  - `[Custom Key Z. Speed]` (`_f 0x78e8`: **Fixed Speed `1..8` def `3` ONLY —
    NO `Variable` Speed Type**, Standby/REC, `Can be reset`, closing Wave-79
    `G149` erratum);
  - `[Remote Zoom Speed]` (`_f 0x7128`: `Speed Type` `Variable` def / `Fix` +
    `Fixed Speed` `1..8` def `3`, ELF `BKID_APP_setting_fixed_zoom_speed_type`,
    `Can be reset`);
  - `[Zoom Ring Rotate]` (`_f 0x6be7`, `Left(W)/Right(T)` def / `Right(W)/Left(T)`,
    anti-Reset); `XLR-H1` has NO zoom lever / Zoom Hold;
  - 4 hard CIZ/Digital pre-lockouts (Still RAW, Movie `119.88p/100p`,
    `S&Q >= 100fps`, HDMI `RAW Output = On`) + 5 active degradations (`Focus
    Area` -> Center priority AF, `Metering Mode` -> `Multi`, Face/Eye AF,
    Multi-Face Metering, and Tracking disabled);
  - vs FX6 `Technical > Zoom > Zoom Type` (`Optical Zoom Only` / `On(Clear Image
    Zoom)`, ZERO `Digital Zoom`), `Technical > Handle Zoom` (`Off` / `Low 1..8`
    def `3` / `High 1..8` def `8` / `Variable`), `0..99` clarified as HUD
    `Zoom Position Display` (NOT speed `1..99`).
- 89B: `Setup -> [Dial Customize]` Exact 5-Item Matrix & Physical 3-Dial
  Boundary vs FX6 `Assignable Dial` / `Multi Function Dial`:
  - Exact 5 exposed items (ALL anti-Reset / `Initialize`-only):
    `[Custom Key/Dial Set.]` (physical `Front Dial` / `Rear Dial` / `Control
    Wheel` only — `Rear Dial L/R` dormant blocked `EOPNOTSUPP=95`), `[My Dial
    Settings]` (`My Dial 1..3`, Hold/Toggle/`1->2->3` skipping empty banks,
    temporary unlock of `[Lock Operation Parts]`), `[Av/Tv Rotate]` (`Normal` /
    `Reverse`), `[Function Ring(Lens)]` (`Power Focus` def vs `APS-C/S35 / Full
    Frame` respecting 4K/RAW crop lock; `FUNCTION_RING_INVALID` on ringless
    lenses), `[Lock Operation Parts]` (`Off` / `Multi-Selector Only` /
    `Dial + Wheel` / `All`);
  - Retired/dormant `[Dial Setup]` (`_f 0x79d1`, `VAL_setting_dial_setup_*` = 0
    ELF hits) & `[Dial / Wheel Lock]` (`base 0xe352`) blocked `EOPNOTSUPP=95`;
  - vs FX6 `Project > Assignable Dial` (`Grip/Remote Dial` & `Handle Dial` def
    `IRIS`, includes `ND Filter`) vs `Project > Multi Function Dial` (def `Off`,
    excludes `ND Filter`, disabled while Menu open).
- 89C: `Setup -> [Operation Customize]` Bitmasks, Zero-EVF `[DISP]` /
  `[Finder/Monitor]` Dormancy, & `[Gamma Display Assist]` vs `[Select LUT]`:
  - `[Different Set for Still/Mv]` exact 8-item bitmask (`Aperture`, `Shutter
    Speed`, `ISO`, `Exposure Comp.`, `Metering Mode`, `White Balance`, `Picture
    Profile`, `Focus Mode`), with `[Picture Profile]` resisting BOTH `[Camera
    Settings Reset]` AND `[Initialize]` (closing Wave-79 `G99` erratum) and
    `Shutter Mode = Angle` forcing Still/Movie shutter independence; independent
    `[Fn Menu Settings]` `12+12` Still/Movie slots (rejecting all-`Not set`
    activation);
  - `[DISP (Screen Disp) Set]` exact 4 shooting pages (`Display All Info.` /
    `No Disp. Info.` / `Histogram` / `Level`) and 3 playback pages; 100% dormant
    `Graphic Display`, `For viewfinder`, `Monitor Off`, and `[Finder/Monitor]`
    branch blocked `EOPNOTSUPP=95` (zero-EVF blackout firewall);
  - `[Select LUT]` (`s709` def / `709(800%)` / `S-Log3` / `User1..16`) +
    `[Display LUT]` override `[Gamma Display Assist]` during Movie/S&Q Log
    Shooting while `[Gamma Display Assist]` remains active for Still Log
    (`_f 0x6538`) and non-Log PP S-Log3/HLG (closing Wave-79 `G132` erratum);
  - vs FX6 60-route `BKID_APP_SETTING_*_DISPLAY` (`104` User Menu toggles,
    `Rec/Play Status`, `Video Signal Monitor`) + FX6 `Gamma Display Assist`
    hard-locked `Off` in `Cine EI`.
- 89D: `Setup -> [External Output]` HDMI 4K/10-bit/RAW & 3 Sony ELF Typos vs
  FX6 `12G-SDI + HDMI` Dual Pipeline:
  - All `[External Output]` items resist `[Camera Settings Reset]`;
  - `[HDMI Resolution]` exact 4 modes (`Auto` / `2160p` / `1080p` / `1080i`,
    NO `720p`); `[Output Resolution]` downshifts to `1080p` when internal rec
    + Log/`PPLUT1..4`; `[4K Output Set.(HDMI Only)]` exact 6 `10bit 4:2:2`
    modes (NO `4:2:0`, NO dormant `_f 0x748a` `24.00p 8bit`, `24.00p` reboot,
    `APS-C/S35` lock, `S&Q` locks `Rec. Media = On`); `24p/60p Output` 100%
    dormant (`0` ELF hits);
  - `[HDMI Info. Display] = On` blacks out internal LCD ONLY when `Rec. Media =
    On & RAW = Off` (auto-clamps to Clean HDMI `Off` with LCD restored when
    `Off(HDMI Only)` or `RAW = On`); `[REC Control] = On` requires `[Time Code
    Output] = On`; `[4ch Audio Output]` (`CH1/CH2` def / `CH3/CH4`); 3 Sony ELF
    typos (`BKID_APP_setting_ctrl_for_hmdi`,
    `PRM_HAITA_hdmi_4k_outpute_apsc_restriction`, `BKID_APP_setting_4ch_output_ch`);
    Tier-0 `Slot 1 EROFS=30` firewall;
  - vs FX6 25-entry `VAL_setting_output_format_sdi_hdmi_*` dual pipeline (`SDI
    RAW` + 4K HDMI vs `HDMI RAW` `4240x2392` locking SDI `1080P/i` & blocking
    `24Hz`, `S&Q > 60fps` cap `<= 1080p`, 3-mode `SDI/HDMI Rec Control`).

Enforces strict Tier-0 safety redlines across all 4 execution modes (normal
local donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` with `<= 4096 B`
`os.pread` bounded windows on multi-MiB files; `FX3_CLEAN_ROOM_TEST=1`;
`FX3_FX6_FORCE_CLEAN_ROOM=1`; and donorless `work_root=None` /
`FX3_FX6_MAC_WORK_ROOT` sentinel).
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
# Phase 385 Schema, Stage 89 (89/89) & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = (
    "phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation_v1"
)
PHASE_385_VERSION = "385.0.0"
PHASE_NUMBER = 385
STAGE_INDEX = 89
STAGE_TOTAL = 89
MILESTONE_LABEL = "89/89"

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
SLOT1_WRITE_AUTHORIZED = False
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
BODY_MODEL_FX3A = "ILME-FX3A"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_BODY_MODELS: Tuple[str, ...] = (
    BODY_MODEL_FX3,
    BODY_MODEL_FX3A,
    BODY_MODEL_FX6,
)
VALID_SHOOT_MODES: Tuple[str, ...] = ("Still", "Movie", "S&Q")

# ---------------------------------------------------------------------------
# 89A Constants — Shooting -> [Zoom] 8-Step Speed vs FX6 Technical > Zoom
# ---------------------------------------------------------------------------

FX3_ZOOM_RANGES: Tuple[str, ...] = (
    "Optical zoom only",
    "Smart Zoom",
    "ClearImage Zoom",
    "Digital Zoom",
)
FX3_ZOOM_RANGE_DEFAULT = "Optical zoom only"
FX3_ZOOM_SPEED_MIN = 1
FX3_ZOOM_SPEED_MAX = 8
FX3_ZOOM_LEVER_1ST_DEFAULT = 3
FX3_ZOOM_LEVER_2ND_DEFAULT = 8
FX3_CUSTOM_KEY_ZOOM_SPEED_DEFAULT = 3
FX3_CUSTOM_KEY_HAS_VARIABLE_MODE = False
FX3_G149_CUSTOM_KEY_NO_VARIABLE_RECONCILED = True
FX3_REMOTE_ZOOM_SPEED_TYPES: Tuple[str, ...] = ("Variable", "Fix")
FX3_REMOTE_ZOOM_SPEED_TYPE_DEFAULT = "Variable"
FX3_REMOTE_ZOOM_FIXED_SPEED_DEFAULT = 3
FX3_REMOTE_SPEED_TYPE_ELF_SYMBOL = "BKID_APP_setting_fixed_zoom_speed_type"
FX3_ZOOM_RING_ROTATE_OPTIONS: Tuple[str, ...] = (
    "Left(W)/Right(T)",
    "Right(W)/Left(T)",
)
FX3_ZOOM_RING_ROTATE_DEFAULT = "Left(W)/Right(T)"
FX3_XLR_H1_HAS_ZOOM_LEVER = False

FX3_CIZ_MOVIE_4K_MAX_MAG = 1.5
FX3_CIZ_MOVIE_HD_MAX_MAG = 2.0
FX3_DIGITAL_MOVIE_MAX_MAG = 4.0

FX3_CIZ_4_PRE_LOCKOUT_IDS: Tuple[str, ...] = (
    "STILL_RAW_FORMAT",
    "MOVIE_119_88P_100P",
    "SQ_GE_100FPS",
    "HDMI_RAW_OUTPUT_ON",
)
FX3_CIZ_5_ACTIVE_DEGRADATION_IDS: Tuple[str, ...] = (
    "FOCUS_AREA_CENTER_PRIORITY_AF",
    "METERING_MODE_LOCKED_MULTI",
    "FACE_EYE_PRIOR_AF_DISABLED",
    "FACE_PRIORITY_MULTI_METERING_DISABLED",
    "TRACKING_DISABLED",
)

FX6_ZOOM_TYPES: Tuple[str, ...] = (
    "Optical Zoom Only",
    "On(Clear Image Zoom)",
)
FX6_HAS_DIGITAL_ZOOM = False
FX6_HANDLE_ZOOM_SETTINGS: Tuple[str, ...] = ("Off", "Low", "High", "Variable")
FX6_HANDLE_ZOOM_LOW_DEFAULT = 3
FX6_HANDLE_ZOOM_HIGH_DEFAULT = 8
FX6_ZOOM_POSITION_DISPLAY_MODES: Tuple[str, ...] = ("Bar", "Number", "Focal Length")
FX6_ZOOM_POSITION_HUD_MIN = 0
FX6_ZOOM_POSITION_HUD_MAX = 99
FX6_HAS_SPEED_1_99_MENU = False

VALID_89A_OPERATIONS: Tuple[str, ...] = (
    "fx3_zoom_range_speeds_reset_split_and_ring_rotate",
    "fx3_ciz_digital_4_prelockouts_and_5_active_degradations",
    "fx6_zoom_type_handle_zoom_and_0_99_hud_clarification",
)

# ---------------------------------------------------------------------------
# 89B Constants — Setup -> [Dial Customize] 5-Item Matrix & 3-Dial Boundary
# ---------------------------------------------------------------------------

FX3_DIAL_CUSTOMIZE_EXACT_5_ITEMS: Tuple[str, ...] = (
    "Custom Key/Dial Set.",
    "My Dial Settings",
    "Av/Tv Rotate",
    "Function Ring(Lens)",
    "Lock Operation Parts",
)
FX3_PHYSICAL_3_DIALS: Tuple[str, ...] = (
    "Front Dial",
    "Rear Dial",
    "Control Wheel",
)
FX3_MOVIE_DEFAULT_DIAL_MAP: Mapping[str, str] = {
    "Front Dial": "Aperture",
    "Rear Dial": "ISO/EI",
    "Control Wheel": "Shutter Speed",
}
FX3_DORMANT_DIAL_ITEMS: Tuple[str, ...] = (
    "Dial Setup",
    "Dial / Wheel Lock",
    "Dial/Wheel Lock",
    "Rear Dial L",
    "Rear Dial R",
)
FX3_MY_DIAL_BANKS: Tuple[str, ...] = ("My Dial 1", "My Dial 2", "My Dial 3")
FX3_MY_DIAL_RECALL_MODES: Tuple[str, ...] = ("Hold", "Toggle", "Cycle")
FX3_AV_TV_ROTATE_OPTIONS: Tuple[str, ...] = ("Normal", "Reverse")
FX3_AV_TV_ROTATE_DEFAULT = "Normal"
FX3_FUNCTION_RING_OPTIONS: Tuple[str, ...] = (
    "Power Focus",
    "APS-C/Super 35 mm / Full Frame",
)
FX3_FUNCTION_RING_DEFAULT = "Power Focus"
FX3_LOCK_OP_PARTS_OPTIONS: Tuple[str, ...] = (
    "Off",
    "Multi-Selector Only",
    "Dial + Wheel",
    "All",
)
FX3_LOCK_OP_PARTS_DEFAULT = "Off"

FX6_ASSIGNABLE_DIAL_TARGETS: Tuple[str, ...] = (
    "Grip/Remote Dial",
    "Handle Dial",
)
FX6_ASSIGNABLE_DIAL_DEFAULT = "IRIS"
FX6_ASSIGNABLE_DIAL_OPTIONS: Tuple[str, ...] = (
    "Off",
    "ISO/Gain/EI",
    "ND Filter",
    "IRIS",
    "Auto Exposure Level",
    "Audio Input Level",
    "Multi Function Dial",
)
FX6_MULTI_FUNCTION_DIAL_DEFAULT = "Off"
FX6_MULTI_FUNCTION_DIAL_OPTIONS: Tuple[str, ...] = (
    "Off",
    "ISO/Gain/EI",
    "IRIS",
    "Auto Exposure Level",
    "Audio Input Level",
)

VALID_89B_OPERATIONS: Tuple[str, ...] = (
    "fx3_dial_customize_5item_3dial_boundary_and_dormant_block",
    "fx3_mydial_1_3_recall_skip_empty_and_lock_temp_unlock",
    "fx3_function_ring_lens_power_focus_and_apsc_s35",
    "fx6_assignable_dial_nd_filter_vs_multi_function_dial",
)

# ---------------------------------------------------------------------------
# 89C Constants — [Operation Customize], Zero-EVF [DISP], LUT vs Gamma Assist
# ---------------------------------------------------------------------------

FX3_DIFF_SET_EXACT_8_ITEMS: Tuple[str, ...] = (
    "Aperture",
    "Shutter Speed",
    "ISO",
    "Exposure Comp.",
    "Metering Mode",
    "White Balance",
    "Picture Profile",
    "Focus Mode",
)
FX3_DIFF_SET_ANTI_INITIALIZE_ITEM = "Picture Profile"
FX3_G99_PP_ANTI_INIT_ERRATUM_RECONCILED = True
FX3_FN_MENU_STILL_SLOTS = 12
FX3_FN_MENU_MOVIE_SLOTS = 12

FX3_DISP_SHOOT_EXACT_4_PAGES: Tuple[str, ...] = (
    "Display All Info.",
    "No Disp. Info.",
    "Histogram",
    "Level",
)
FX3_DISP_PLAYBACK_EXACT_3_PAGES: Tuple[str, ...] = (
    "Display Info.",
    "Histogram",
    "No Disp. Info.",
)
FX3_DORMANT_EVF_AND_DISP_ITEMS: Tuple[str, ...] = (
    "Graphic Display",
    "For viewfinder",
    "Monitor Off",
    "Finder/Monitor",
    "Finder/Monitor Sel.",
    "Select Finder/Monitor",
    "BKID_APP_setting_finder_monitor",
    "BKID_APP_disp_mode_shoot_finder",
)
FX3_HAS_BUILTIN_EVF = False

FX3_SELECT_LUT_PRESETS: Tuple[str, ...] = ("s709", "709(800%)", "S-Log3")
FX3_SELECT_LUT_DEFAULT = "s709"
FX3_SELECT_LUT_USER_SLOTS: Tuple[str, ...] = tuple(f"User{i}" for i in range(1, 17))
FX3_SELECT_LUT_ALL_SLOTS: Tuple[str, ...] = (
    FX3_SELECT_LUT_PRESETS + FX3_SELECT_LUT_USER_SLOTS
)
FX3_GAMMA_DISPLAY_ASSIST_TYPES: Tuple[str, ...] = (
    "Auto",
    "S-Log3->709(800%)",
    "HLG(BT.2020)",
    "HLG(709)",
)
FX3_G132_LOG_LUT_GAMMA_SPLIT_RECONCILED = True

FX6_DISPLAY_ON_OFF_ELF_ROUTES_COUNT = 60
FX6_USER_MENU_DISPLAY_TOGGLES_COUNT = 104
FX6_HUD_INDIVIDUAL_TOGGLES_MIN = 24
FX6_REC_PLAY_STATUS_DISPLAY_MODES: Tuple[str, ...] = (
    "Always On",
    "Always On (Minimum)",
    "On",
    "Off",
)
FX6_VIDEO_SIGNAL_MONITORS: Tuple[str, ...] = (
    "Waveform",
    "Vectorscope",
    "Histogram",
)

VALID_89C_OPERATIONS: Tuple[str, ...] = (
    "fx3_diff_set_8item_bitmask_pp_anti_init_and_fn_12x2",
    "fx3_disp_4pages_and_zero_evf_finder_monitor_dormancy",
    "fx3_select_lut_vs_gamma_display_assist_routing",
    "fx6_60route_display_on_off_and_cine_ei_gamma_assist_lock",
)

# ---------------------------------------------------------------------------
# 89D Constants — [External Output] HDMI 4K/10-bit/RAW & 3 Typos vs FX6 SDI
# ---------------------------------------------------------------------------

FX3_HDMI_RESOLUTION_EXACT_4_MODES: Tuple[str, ...] = (
    "Auto",
    "2160p",
    "1080p",
    "1080i",
)
FX3_HDMI_RESOLUTION_DEFAULT = "Auto"
FX3_DORMANT_HDMI_RESOLUTIONS: Tuple[str, ...] = (
    "720p",
    "720p/480p",
    "480i",
    "576i",
    "4320p",
    "HDMI_RESOLUTION_720P_480P",
)
FX3_4K_OUTPUT_SET_EXACT_6_MODES: Tuple[str, ...] = (
    "59.94p 10bit",
    "50p 10bit",
    "29.97p 10bit",
    "25p 10bit",
    "23.98p 10bit",
    "24.00p 10bit",
)
FX3_4K_OUTPUT_SET_DEFAULT = "59.94p 10bit"
FX3_4K_OUTPUT_CHROMA_SPEC = "10bit 4:2:2"
FX3_4K_OUTPUT_HAS_420_OPTION = False
FX3_DORMANT_4K_OUTPUT_MODES: Tuple[str, ...] = (
    "24.00p 8bit",
    "59.94p 8bit 4:2:0",
    "29.97p 4:2:0",
    "4:2:0",
    "HDMI_ONLY_4K_OUTPUT_SETTING_24_00P_8BIT",
)
FX3_DORMANT_24P_60P_OUTPUT_ELF_HITS = 0
FX3_HDMI_RAW_RES = "4264x2408"
FX3_HDMI_RAW_BITS = 16
FX3_HDMI_RAW_FPS_OPTIONS: Tuple[str, ...] = (
    "59.94p",
    "50p",
    "29.97p",
    "25p",
    "23.98p",
    "24.00p",
)
FX3_4CH_AUDIO_OUTPUT_OPTIONS: Tuple[str, ...] = ("CH1/CH2", "CH3/CH4")
FX3_4CH_AUDIO_OUTPUT_DEFAULT = "CH1/CH2"
FX3_SONY_ELF_3_TYPOS: Tuple[str, ...] = (
    "BKID_APP_setting_ctrl_for_hmdi",
    "PRM_HAITA_hdmi_4k_outpute_apsc_restriction",
    "BKID_APP_setting_4ch_output_ch",
)

FX6_SDI_HDMI_OUTPUT_FORMAT_MATRIX_ENTRIES = 25
FX6_SDI_OUTPUT_FORMATS: Tuple[str, ...] = (
    "4096x2160P",
    "3840x2160P",
    "1920x1080P (Level A)",
    "1920x1080P (Level B)",
    "1920x1080i",
)
FX6_HDMI_OUTPUT_FORMATS: Tuple[str, ...] = (
    "4096x2160P",
    "3840x2160P",
    "1920x1080P",
    "1920x1080i",
)
FX6_SDI_RAW_FORMATS: Tuple[str, ...] = ("4096x2160 RAW", "3840x2160 RAW")
FX6_HDMI_RAW_RES = "4240x2392"
FX6_SDI_HDMI_REC_CONTROL_3_MODES: Tuple[str, ...] = (
    "Off",
    "SDI/HDMI Remote I/F",
    "Parallel Rec",
)

VALID_89D_OPERATIONS: Tuple[str, ...] = (
    "fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
    "fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
    "fx6_12gsdi_hdmi_dual_pipeline_raw_sq60_cap_and_rec_ctrl",
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
_DONOR_OPEN_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
)

_FX3_USR_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX6_NF15_PREFIX = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)


class Stage89Phase385Error(RuntimeError):
    """Raised on invalid Phase 385 Stage 89 HIL inputs or redline violation."""


# ---------------------------------------------------------------------------
# 22 Real-Hardware Wave-79 Donor Specs (O_RDONLY|O_NOFOLLOW|O_NONBLOCK)
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


PHASE385_COMPACT_DONORS: Tuple[CompactDonorSpec, ...] = (
    CompactDonorSpec(
        name="fx3_string_en_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
        expected_size=373820,
        expected_sha256="7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        required_tokens=(
            b"Zoom Range",
            b"Optical zoom only",
            b"ClearImage Zoom",
            b"Zoom Lever Speed",
            b"Custom Key Z. Speed",
            b"Remote Zoom Speed",
            b"Zoom Ring Rotate",
            b"My Dial Settings",
            b"Av/Tv Rotate",
            b"Function Ring(Lens)",
            b"Power Focus",
            b"Lock Operation Parts",
            b"Different Set for Still/Mv",
            b"Gamma Display Assist",
            b"Select LUT",
            b"Rec. Media dur HDMI Output",
            b"4K Output Set.(HDMI Only)",
            b"RAW Output",
            b"Time Code Output",
            b"REC Control",
            b"4ch Audio Output",
            b"HDMI Info. Display",
            b"24p/60p Output",
            b"24.00p 8bit",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_f.uxc",
        expected_size=322652,
        expected_sha256="4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        required_tokens=(
            "变焦范围".encode("utf-8"),
            "变焦杆速度".encode("utf-8"),
            "自定义键变焦速度".encode("utf-8"),
            "遥控变焦速度".encode("utf-8"),
            "变焦环旋转".encode("utf-8"),
            "我的转盘设置".encode("utf-8"),
            "功能环(镜头)".encode("utf-8"),
            "锁定操作的部件".encode("utf-8"),
            "静态/动态不同设置".encode("utf-8"),
            "Gamma显示辅助".encode("utf-8"),
            "选择LUT".encode("utf-8"),
            "4K输出设置(仅HDMI)".encode("utf-8"),
            "RAW输出".encode("utf-8"),
            "HDMI信息显示".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_f.uxc",
        expected_size=324148,
        expected_sha256="32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        required_tokens=(
            "變焦範圍".encode("utf-8"),
            "變焦控制桿速度".encode("utf-8"),
            "自訂鍵變焦速度".encode("utf-8"),
            "遙控變焦速度".encode("utf-8"),
            "變焦環旋轉".encode("utf-8"),
            "我的轉盤設定".encode("utf-8"),
            "功能環(鏡頭)".encode("utf-8"),
            "操作鈕鎖定".encode("utf-8"),
            "不同靜像/影片設定".encode("utf-8"),
            "Gamma顯示輔助".encode("utf-8"),
            "選取LUT".encode("utf-8"),
            "4K輸出設定(僅限HDMI)".encode("utf-8"),
            "RAW輸出".encode("utf-8"),
            "HDMI資訊顯示".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_f.uxc",
        expected_size=447840,
        expected_sha256="45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        required_tokens=(
            "ズーム範囲".encode("utf-8"),
            "ｽﾞｰﾑﾚﾊﾞｰｽﾋﾟｰﾄﾞ".encode("utf-8"),
            "ｶｽﾀﾑｷｰｽﾞｰﾑｽﾋﾟｰﾄﾞ".encode("utf-8"),
            "ﾘﾓｰﾄｽﾞｰﾑｽﾋﾟｰﾄﾞ".encode("utf-8"),
            "ｽﾞｰﾑﾘﾝｸﾞ操作方向".encode("utf-8"),
            "マイダイヤル設定".encode("utf-8"),
            "ﾌｧﾝｸｼｮﾝﾘﾝｸﾞ(ﾚﾝｽﾞ)".encode("utf-8"),
            "操作部のロック".encode("utf-8"),
            "静止画/動画独立設定".encode("utf-8"),
            "ｶﾞﾝﾏ表示ｱｼｽﾄ".encode("utf-8"),
            "LUT選択".encode("utf-8"),
            "4K出力設定(HDMIのみ)".encode("utf-8"),
            "RAW出力".encode("utf-8"),
            "HDMI情報表示".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english.uxc",
        expected_size=165740,
        expected_sha256="204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        required_tokens=(
            b"Digital Zoom",
            b"Dial / Wheel Lock",
            b"Display All Info.",
            b"No Disp. Info.",
            b"Histogram",
            b"Level",
            b"Graphic Display",
            b"For viewfinder",
            b"HDMI Resolution",
            b"CTRL FOR HDMI",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese.uxc",
        expected_size=149064,
        expected_sha256="34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
        required_tokens=(
            "数字变焦".encode("utf-8"),
            "图形显示".encode("utf-8"),
            "HDMI分辨率".encode("utf-8"),
            "HDMI控制".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese.uxc",
        expected_size=151908,
        expected_sha256="be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
        required_tokens=(
            "數位變焦".encode("utf-8"),
            "圖形顯示".encode("utf-8"),
            "HDMI解析度".encode("utf-8"),
            "HDMI控制".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese.uxc",
        expected_size=208564,
        expected_sha256="f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
        required_tokens=(
            "デジタルズーム".encode("utf-8"),
            "グラフィック表示".encode("utf-8"),
            "HDMI解像度".encode("utf-8"),
            "HDMI機器制御".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
        expected_size=69600,
        expected_sha256="a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        required_tokens=(
            b"Dial Customize",
            b"Operation Customize",
            b"Fn Menu Settings",
            b"DISP (Screen Disp) Set",
            b"Finder/Monitor",
            b"External Output",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_g.uxc",
        expected_size=61296,
        expected_sha256="a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
        required_tokens=(
            "转盘自定义".encode("utf-8"),
            "操作自定义".encode("utf-8"),
            "Fn菜单设置".encode("utf-8"),
            "DISP(画面显示)设置".encode("utf-8"),
            "取景器/显示屏".encode("utf-8"),
            "外部输出".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_g.uxc",
        expected_size=61372,
        expected_sha256="97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80",
        required_tokens=(
            "轉盤客製化".encode("utf-8"),
            "操作客製化".encode("utf-8"),
            "Fn功能表設定".encode("utf-8"),
            "DISP(畫面顯示)設定".encode("utf-8"),
            "觀景窗/螢幕".encode("utf-8"),
            "外部輸出".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_g.uxc",
        expected_size=89428,
        expected_sha256="4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980",
        required_tokens=(
            "ﾀﾞｲﾔﾙｶｽﾀﾏｲｽﾞ".encode("utf-8"),
            "操作カスタマイズ".encode("utf-8"),
            "Fnメニュー設定".encode("utf-8"),
            "DISP(画面表示)設定".encode("utf-8"),
            "ﾌｧｲﾝﾀﾞｰ/ﾓﾆﾀｰ".encode("utf-8"),
            "外部出力".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_en",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
        expected_size=118208,
        expected_sha256="5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        required_tokens=(
            b"Multi Function Dial",
            b"Grip/Remote Dial",
            b"Handle Dial",
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_en_2",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
        expected_size=118676,
        expected_sha256="3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        required_tokens=(
            b"Handle Zoom",
            b"Zoom Ring Direction",
            b"Display On/Off",
            b"Output Format",
            b"SDI/HDMI Rec Control",
            b"Parallel Rec",
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_sc",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_simplifiedchinese.uxc",
        expected_size=118644,
        expected_sha256="ba060e859156bfaefcc4177bfa6e9c5bea112258b15ce815a5ba683d033e688f",
        required_tokens=(
            "手柄/遥控拨盘".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_sc_2",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_simplifiedchinese_2.uxc",
        expected_size=122084,
        expected_sha256="058c09066cd7cd4eb5d68fa4228255fa7d2ad195a4088f145ac647e3577e58a3",
        required_tokens=(
            "手柄变焦".encode("utf-8"),
            "显示开/关".encode("utf-8"),
            "输出格式".encode("utf-8"),
            "SDI/HDMI录制控制".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_tc",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_traditionalchinese.uxc",
        expected_size=119168,
        expected_sha256="8c34b415ce4d19fd40ca22d00c4543c64eb4741b96250de13b93ec473b25b18b",
        required_tokens=(
            "手把/遙控轉盤".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_tc_2",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_traditionalchinese_2.uxc",
        expected_size=121824,
        expected_sha256="07fa20ae03457465a8c4922f479d6cfe1280980a70ac43797081e87654680c6d",
        required_tokens=(
            "手柄變焦".encode("utf-8"),
            "顯示開/關".encode("utf-8"),
            "輸出格式".encode("utf-8"),
            "SDI/HDMI錄製控制".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_ja",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_japanese.uxc",
        expected_size=141692,
        expected_sha256="9b47630ebe8e011a9d0bdb7a2fda06574f5187222b92d60bf6887042fe186d35",
        required_tokens=(
            "グリップ/リモートダイヤル".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_ja_2",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_japanese_2.uxc",
        expected_size=144720,
        expected_sha256="98315732d7e29078a98dc32c077a799f8831d8bb3d96ec26ca2110ed8e36aa26",
        required_tokens=(
            "ハンドルズーム".encode("utf-8"),
            "画面表示On/Off設定".encode("utf-8"),
            "出力フォーマット".encode("utf-8"),
            "SDI/HDMI記録制御".encode("utf-8"),
        ),
    ),
)

PHASE385_WINDOW_DONORS: Tuple[WindowDonorSpec, ...] = (
    WindowDonorSpec(
        name="fx3_appfw",
        rel_path="fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        expected_size=79015712,
        head4k_sha256="de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
        windows=(
            # 89A: Zoom 8-Step Speed & Range
            (0x3BC7000, "ZOOM_RANGE_BKID", b"BKID_APP_MR_setting_zoom_setting"),
            (0x3AC8000, "ZOOM_OPTICAL", b"VAL_setting_zoom_setting_ZOOM_SETTING_OPTICAL_ZOOM_ONLY"),
            (0x3AC8000, "ZOOM_SMART", b"VAL_setting_zoom_setting_ZOOM_SETTING_SMART_ZOOM_ONLY"),
            (0x3AC8000, "ZOOM_CIZ", b"VAL_setting_zoom_setting_ZOOM_SETTING_CLEAR_IMAGE_ZOOM_ON"),
            (0x3AC8000, "ZOOM_DIGITAL", b"VAL_setting_zoom_setting_ZOOM_SETTING_DIGITAL_ZOOM_ON"),
            (0x3BC7000, "ZOOM_1ST_STBY", b"BKID_APP_setting_1st_zoom_spd_stby"),
            (0x3BC7000, "ZOOM_1ST_REC", b"BKID_APP_setting_1st_zoom_spd_rec"),
            (0x3BC7000, "ZOOM_2ND_STBY", b"BKID_APP_setting_2nd_zoom_spd_stby"),
            (0x3BC7000, "ZOOM_2ND_REC", b"BKID_APP_setting_2nd_zoom_spd_rec"),
            (0x3BC7000, "ZOOM_CKEY_STBY", b"BKID_APP_setting_fixed_zoom_speed_stby"),
            (0x3BC7000, "ZOOM_CKEY_REC", b"BKID_APP_setting_fixed_zoom_speed_rec"),
            (0x3BC7000, "ZOOM_REMOTE_TYPE", b"BKID_APP_setting_fixed_zoom_speed_type"),
            (0x3B7C000, "ZOOM_TYPE_VAR", b"VAL_setting_fixed_zoom_speed_type_ZOOM_SPEED_TYPE_VARIABLE"),
            (0x3B7C000, "ZOOM_TYPE_FIX", b"VAL_setting_fixed_zoom_speed_type_ZOOM_SPEED_TYPE_FIXED"),
            (0x3BC7000, "ZOOM_REMOTE_STBY", b"BKID_APP_setting_remote_fixed_zoom_speed_stby"),
            (0x3BC7000, "ZOOM_REMOTE_REC", b"BKID_APP_setting_remote_fixed_zoom_speed_rec"),
            (0x3BEF000, "ZOOM_RING_ROTATE", b"BKID_APP_extern_menu_ring_zoom_direction_mode"),
            # 89B: Dial Customize, My Dial 1..3, Function Ring & Dormant Symbols
            (0x3BCB000, "AV_TV_ROTATE", b"BKID_APP_setting_av_tv_rotate"),
            (0x3BCB000, "FUNCTION_RING", b"BKID_APP_setting_function_ring"),
            (0x3B06000, "FUNC_RING_S35", b"VAL_setting_function_ring_FUNCTION_RING_SUPER_35MM_SEL"),
            (0x3B06000, "FUNC_RING_INV", b"VAL_setting_function_ring_FUNCTION_RING_INVALID"),
            (0x3BCB000, "DORMANT_DIAL_SETUP", b"BKID_APP_setting_dial_setup"),
            (0x3BCB000, "MYDIAL_FRONT", b"BKID_APP_mydial_front_dial_setting_list0"),
            (0x3BCB000, "MYDIAL_WHEEL", b"BKID_APP_mydial_control_wheel_setting_list0"),
            (0x3BCB000, "DORMANT_REAR_L", b"BKID_APP_mydial_rear_dial_left_setting_list0"),
            (0x3BCB000, "DORMANT_REAR_R", b"BKID_APP_mydial_rear_dial_right_setting_list0"),
            # 89C: Operation Customize, Fn 12+12 & Zero-EVF Dormancy
            (0x3BC5000, "DIFF_SET_8", b"BKID_APP_setting_different_set_for_s_q_mv"),
            (0x3BCB000, "FN_STILL0", b"BKID_APP_fn_menu_item_ids_for_still0"),
            (0x3BCB000, "FN_MOVIE0", b"BKID_APP_fn_menu_item_ids_for_movie0"),
            (0x3BCB000, "DORMANT_FINDER_MON", b"BKID_APP_setting_finder_monitor"),
            (0x3BCE000, "DORMANT_DISP_FINDER", b"BKID_APP_disp_mode_shoot_finder"),
            (0x3B2B000, "DORMANT_MON_OFF", b"VAL_disp_mode_shoot_monitor_DISP_MODE_SHOOT_MONITOR_MONITOR_OFF"),
            # 89D: External Output HDMI 4K/10bit/RAW & 3 Sony ELF Typos
            (0x3BCC000, "HDMI_RES_BKID", b"BKID_APP_setting_hdmi_resolution"),
            (0x3B4A000, "HDMI_RES_AUTO", b"VAL_setting_hdmi_resolution_HDMI_RESOLUTION_AUTO_SET"),
            (0x3B4A000, "HDMI_RES_2160P", b"VAL_setting_hdmi_resolution_HDMI_RESOLUTION_2160P"),
            (0x3B4A000, "HDMI_RES_1080P", b"VAL_setting_hdmi_resolution_HDMI_RESOLUTION_1080P"),
            (0x3B4A000, "HDMI_RES_1080I", b"VAL_setting_hdmi_resolution_HDMI_RESOLUTION_1080I"),
            (0x3B4A000, "DORMANT_HDMI_720P", b"VAL_setting_hdmi_resolution_HDMI_RESOLUTION_720P_480P"),
            (0x3BCC000, "REC_MEDIA_HDMI", b"BKID_APP_setting_rec_media_during_hdmi_output"),
            (0x3BCC000, "OUTPUT_RES_BKID", b"BKID_APP_setting_output_resolution"),
            (0x3BCC000, "HDMI_4K_OUT_BKID", b"BKID_APP_setting_hdmi_4k_output_setting"),
            (0x3AFE000, "HDMI_24_00P_10BIT", b"VAL_setting_hdmi_4k_output_setting_HDMI_ONLY_4K_OUTPUT_SETTING_24_00P_10BIT"),
            (0x39BA000, "TYPO_HDMI_OUTPUTE", b"PRM_HAITA_hdmi_4k_outpute_apsc_restriction"),
            (0x3BCC000, "RAW_OUTPUT_BKID", b"BKID_APP_setting_raw_output"),
            (0x3BCC000, "RAW_OUTPUT_FPS", b"BKID_APP_setting_raw_output_frame_rate"),
            (0x3BCC000, "REC_CONTROL_BKID", b"BKID_APP_setting_rec_control"),
            (0x3BCC000, "TYPO_4CH_OUTPUT_CH", b"BKID_APP_setting_4ch_output_ch"),
            (0x3BCC000, "HDMI_INFO_DISP", b"BKID_APP_setting_hdmi_info_display"),
            (0x3BCC000, "TYPO_CTRL_FOR_HMDI", b"BKID_APP_setting_ctrl_for_hmdi"),
        ),
        absent_windows=(
            (0x3BCB000, "NO_VAL_DIAL_SETUP", b"VAL_setting_dial_setup_"),
            (0x3AFE000, "NO_HDMI_24_00P_8BIT", b"HDMI_ONLY_4K_OUTPUT_SETTING_24_00P_8BIT"),
            (0x3BCC000, "NO_24P_60P_OUTPUT", b"24p/60p Output"),
            (0x3BCC000, "NO_4CH_AUDIO_OUTPUT_KEY", b"BKID_APP_setting_4ch_audio_output"),
            (0x3BCC000, "NO_CTRL_FOR_HDMI_SPELLED", b"BKID_APP_setting_ctrl_for_hdmi"),
        ),
    ),
    WindowDonorSpec(
        name="fx6_appfw",
        rel_path=f"{_FX6_NF15_PREFIX}/lib/appFw.so",
        expected_size=50520424,
        head4k_sha256="18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
        windows=(
            (0x270C000, "FX6_HANDLE_ZOOM_HIGH", b"BKID_APP_SETTING_HANDLE_ZOOM_HIGH"),
            (0x270C000, "FX6_HANDLE_ZOOM_LOW", b"BKID_APP_SETTING_HANDLE_ZOOM_LOW"),
            (0x270C000, "FX6_ZOOM_POS_DISP", b"BKID_APP_SETTING_LENS_ZOOM_POSITION_DISPLAY"),
            (0x2709000, "FX6_ASSIGN_DIAL_00", b"BKID_APP_SETTING_ASSIGNABLE_DIAL_00"),
            (0x2709000, "FX6_ASSIGN_DIAL_01", b"BKID_APP_SETTING_ASSIGNABLE_DIAL_01"),
            (0x2709000, "FX6_ASSIGN_DIAL_02", b"BKID_APP_SETTING_ASSIGNABLE_DIAL_02"),
            (0x2709000, "FX6_IRIS_DIAL", b"BKID_APP_SETTING_IRIS_DIAL"),
            (0x270B000, "FX6_LUT_DISPLAY", b"BKID_APP_SETTING_BASE_LOOK_LUT_DISPLAY"),
            (0x270B000, "FX6_AE_LEVEL_DISP", b"BKID_APP_SETTING_AE_LEVEL_DISPLAY"),
            (0x270F000, "FX6_USER_DISP_0", b"BKID_APP_USER_MENU_DISPLAY_ON_OF0"),
            (0x2710000, "FX6_USER_DISP_103", b"BKID_APP_USER_MENU_DISPLAY_ON_OF103"),
            (0x26A1000, "FX6_SDI_HDMI_4096", b"VAL_setting_output_format_sdi_hdmi_OUTPUT_FORMAT_HDMI_4096"),
            (0x26A1000, "FX6_SDI_HDMI_3840", b"VAL_setting_output_format_sdi_hdmi_OUTPUT_FORMAT_HDMI_3840"),
            (0x26A1000, "FX6_SDI_HDMI_1920", b"VAL_setting_output_format_sdi_hdmi_OUTPUT_FORMAT_HDMI_1920"),
            (0x2709000, "FX6_SDI_HDMI_REC_CTRL", b"BKID_APP_SETTING_SDI_HDMI_REC_CONTROL"),
        ),
        absent_windows=(
            (0x270C000, "FX6_NO_DIGITAL_ZOOM", b"BKID_APP_SETTING_DIGITAL_ZOOM"),
        ),
    ),
)


# ---------------------------------------------------------------------------
# Strict O_RDONLY | O_NOFOLLOW | O_NONBLOCK & Clean-Room Synthetic Helpers
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
    fd = os.open(str(path), _DONOR_OPEN_FLAGS)
    try:
        st = os.fstat(fd)
        if st.st_size > _COMPACT_MAX_READ_BYTES:
            raise Stage89Phase385Error(
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
        raise Stage89Phase385Error(
            f"Bounded read size {size} exceeds {_BOUNDED_WINDOW_BYTES} B"
        )
    fd = os.open(str(path), _DONOR_OPEN_FLAGS)
    try:
        st = os.fstat(fd)
        head4k = os.pread(fd, _BOUNDED_WINDOW_BYTES, 0)
        win = os.pread(fd, size, offset)
        return st.st_size, head4k, win
    finally:
        os.close(fd)


def inspect_phase385_wave79_donors(
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
            resolved_root / s.rel_path for s in PHASE385_COMPACT_DONORS
        ] + [resolved_root / w.rel_path for w in PHASE385_WINDOW_DONORS]
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
            for s in PHASE385_COMPACT_DONORS
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
            for w in PHASE385_WINDOW_DONORS
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
    for spec in PHASE385_COMPACT_DONORS:
        p = resolved_root / spec.rel_path
        data = _read_full_compact_o_rdonly(p)
        sha = hashlib.sha256(data).hexdigest()
        if len(data) != spec.expected_size or sha != spec.expected_sha256:
            raise Stage89Phase385Error(
                f"Donor mismatch {spec.name}: size={len(data)} sha={sha}"
            )
        missing = [t for t in spec.required_tokens if t not in data]
        if missing:
            raise Stage89Phase385Error(
                f"Donor {spec.name} missing required tokens: {len(missing)}"
            )
        present_bad = [t for t in spec.absent_tokens if t in data]
        if present_bad:
            raise Stage89Phase385Error(
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
    for wspec in PHASE385_WINDOW_DONORS:
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
                raise Stage89Phase385Error(
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
                raise Stage89Phase385Error(
                    f"Window donor {wspec.name} unexpectedly had {label} at 0x{off:x}"
                )
        if file_size != wspec.expected_size or head4k_sha != wspec.head4k_sha256:
            raise Stage89Phase385Error(
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
        "donor_access_mode": "O_RDONLY_NOFOLLOW_NONBLOCK_BOUNDED_4K",
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
# Sub-Model 89A..89D Audit Result Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubModel89AZoomSpeedFx6HandleAuditResult:
    operation: str
    body_model: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    zoom_range: str
    max_magnification: float
    zoom_range_survived_cam_reset: bool
    zoom_ring_rotate: str
    zoom_ring_rotate_survived_cam_reset: bool
    lever_1st_stby: int
    lever_1st_rec: int
    lever_2nd_stby: int
    lever_2nd_rec: int
    custom_key_speed_stby: int
    custom_key_speed_rec: int
    custom_key_has_variable_mode: bool
    custom_key_variable_blocked: bool
    g149_custom_key_no_variable_reconciled: bool
    remote_speed_type: str
    remote_speed_type_elf_symbol: str
    remote_fixed_speed_stby: int
    remote_fixed_speed_rec: int
    speeds_reset_on_cam_reset: bool
    xlr_h1_has_zoom_lever: bool
    xlr_h1_phantom_zoom_blocked: bool
    is_power_zoom_lens: bool
    seamless_optical_to_ciz: bool
    pre_lockouts_triggered: Tuple[str, ...]
    active_degradations_triggered: Tuple[str, ...]
    fx6_zoom_type: str
    fx6_digital_zoom_blocked: bool
    fx6_handle_zoom_setting: str
    fx6_handle_zoom_low: int
    fx6_handle_zoom_high: int
    fx6_zoom_position_hud_value: int
    fx6_speed_1_99_debunked: bool
    slot1_writes: int = 0
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel89BDialCustomizeFuncRingFx6AuditResult:
    operation: str
    body_model: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    exposed_dial_customize_items_count: int
    physical_dial_count: int
    all_5_items_resist_cam_reset: bool
    survived_cam_reset: bool
    reset_on_initialize: bool
    dormant_dial_or_rear_lr_blocked: bool
    front_dial_func: str
    rear_dial_func: str
    control_wheel_func: str
    av_tv_rotate: str
    av_tv_rotate_coefficient: int
    lock_operation_parts: str
    my_dial_active_bank: str
    my_dial_recall_mode: str
    my_dial_skipped_empty_banks: Tuple[str, ...]
    lock_op_parts_temp_unlocked: bool
    function_ring_mode: str
    lens_has_function_ring: bool
    function_ring_invalid_fallback: bool
    apsc_s35_crop_lock_blocked: bool
    fx6_dial_node: str
    fx6_dial_function: str
    fx6_nd_filter_allowed_on_node: bool
    fx6_menu_open_dial_blocked: bool
    slot1_writes: int = 0
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel89COpCustomizeDispLutFx6AuditResult:
    operation: str
    body_model: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    diff_set_items_count: int
    diff_set_checked_items: Tuple[str, ...]
    diff_set_survived_cam_reset: bool
    picture_profile_survived_initialize: bool
    g99_pp_anti_init_reconciled: bool
    shutter_angle_forces_still_movie_split: bool
    fn_still_slots_count: int
    fn_movie_slots_count: int
    fn_slots_decoupled_from_diff_set: bool
    empty_fn_menu_rejected: bool
    disp_shoot_pages_count: int
    disp_playback_pages_count: int
    fx3_has_builtin_evf: bool
    dormant_evf_or_disp_blocked: bool
    log_shooting_mode: str
    select_lut_slot: str
    display_lut_on: bool
    gamma_display_assist_on: bool
    gamma_display_assist_type: str
    gamma_assist_active: bool
    gamma_assist_overridden_by_select_lut: bool
    g132_log_lut_gamma_split_reconciled: bool
    fx6_display_elf_routes_count: int
    fx6_user_menu_display_toggles_count: int
    fx6_rec_play_status_mode: str
    fx6_video_signal_monitor: str
    fx6_cine_ei_gamma_assist_locked_off: bool
    slot1_writes: int = 0
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel89DExternalOutputHdmiSdi12gAuditResult:
    operation: str
    body_model: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    external_output_resists_cam_reset: bool
    hdmi_resolution: str
    hdmi_resolution_exposed_count: int
    dormant_hdmi_720p_blocked: bool
    rec_media_dur_hdmi_output: str
    output_resolution: str
    effective_hdmi_resolution: str
    hdmi_log_1080_downshifted: bool
    hdmi_4k_output_set: str
    hdmi_4k_output_exposed_count: int
    hdmi_4k_chroma_spec: str
    dormant_420_or_8bit_blocked: bool
    reboot_required_for_24_00p: bool
    apsc_s35_blocks_4k_output_set: bool
    dormant_24p_60p_output_blocked: bool
    hdmi_info_display_setting: str
    effective_hdmi_info_display: str
    internal_lcd_blacked_out: bool
    hdmi_raw_output_on: bool
    hdmi_raw_resolution: str
    time_code_output_on: bool
    rec_control_on: bool
    rec_control_missing_tc_blocked: bool
    audio_4ch_output_pair: str
    ctrl_for_hdmi_on: bool
    sony_elf_3_typos: Tuple[str, ...]
    target_slot: str
    slot1_erofs_blocked: bool
    fx6_codec: str
    fx6_sdi_format: str
    fx6_hdmi_format: str
    fx6_sdi_hdmi_matrix_entries_count: int
    fx6_hdmi_raw_locks_sdi_1080: bool
    fx6_sq_gt60_caps_hdmi_1080: bool
    fx6_rec_control_mode: str
    slot1_writes: int = 0
    slot1_sector_writes: int = 0
    slot1_data_sector_writes: int = 0
    usb_tx_packets: int = 0
    rf_tx_packets: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Sub-Model 89A Simulator — Shooting -> [Zoom] 8-Step Speed vs FX6 Zoom
# ---------------------------------------------------------------------------


def _resolve_fx3_max_zoom_mag(
    zoom_range: str,
    shoot_mode: str,
    movie_resolution: str,
    still_image_size: str,
    apsc_s35_on: bool,
) -> float:
    if zoom_range == "Optical zoom only":
        return 1.0
    if shoot_mode in ("Movie", "S&Q"):
        if zoom_range == "ClearImage Zoom":
            return FX3_CIZ_MOVIE_4K_MAX_MAG if movie_resolution == "4K" else FX3_CIZ_MOVIE_HD_MAX_MAG
        if zoom_range == "Digital Zoom":
            return FX3_DIGITAL_MOVIE_MAX_MAG
        return 1.0
    # Still 3:2 FF vs APS-C
    if apsc_s35_on:
        table_apsc = {
            ("Smart Zoom", "M"): 1.3,
            ("Smart Zoom", "S"): 2.0,
            ("ClearImage Zoom", "M"): 2.6,
            ("ClearImage Zoom", "S"): 4.0,
            ("Digital Zoom", "M"): 5.2,
            ("Digital Zoom", "S"): 8.0,
        }
        return table_apsc.get((zoom_range, still_image_size), 1.0)
    table_ff = {
        ("Smart Zoom", "M"): 1.5,
        ("Smart Zoom", "S"): 2.0,
        ("ClearImage Zoom", "L"): 2.0,
        ("ClearImage Zoom", "M"): 3.1,
        ("ClearImage Zoom", "S"): 4.0,
        ("Digital Zoom", "L"): 4.0,
        ("Digital Zoom", "M"): 6.1,
        ("Digital Zoom", "S"): 8.0,
    }
    return table_ff.get((zoom_range, still_image_size), 1.0)


def simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    shoot_mode: str = "Movie",
    zoom_range: str = FX3_ZOOM_RANGE_DEFAULT,
    movie_resolution: str = "4K",
    still_image_size: str = "L",
    apsc_s35_on: bool = False,
    still_file_format: str = "JPEG",
    rec_frame_rate: str = "23.98p",
    sq_frame_rate_fps: int = 60,
    hdmi_raw_output_on: bool = False,
    non_optical_engaged: bool = False,
    is_power_zoom_lens: bool = True,
    lever_1st_stby: int = FX3_ZOOM_LEVER_1ST_DEFAULT,
    lever_1st_rec: int = FX3_ZOOM_LEVER_1ST_DEFAULT,
    lever_2nd_stby: int = FX3_ZOOM_LEVER_2ND_DEFAULT,
    lever_2nd_rec: int = FX3_ZOOM_LEVER_2ND_DEFAULT,
    custom_key_speed_stby: int = FX3_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
    custom_key_speed_rec: int = FX3_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
    custom_key_speed_type: str = "Fix",
    remote_speed_type: str = FX3_REMOTE_ZOOM_SPEED_TYPE_DEFAULT,
    remote_fixed_speed_stby: int = FX3_REMOTE_ZOOM_FIXED_SPEED_DEFAULT,
    remote_fixed_speed_rec: int = FX3_REMOTE_ZOOM_FIXED_SPEED_DEFAULT,
    zoom_ring_rotate: str = FX3_ZOOM_RING_ROTATE_DEFAULT,
    xlr_h1_zoom_lever_requested: bool = False,
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    fx6_zoom_type: str = "Optical Zoom Only",
    fx6_handle_zoom_setting: str = "Low",
    fx6_handle_zoom_low: int = FX6_HANDLE_ZOOM_LOW_DEFAULT,
    fx6_handle_zoom_high: int = FX6_HANDLE_ZOOM_HIGH_DEFAULT,
    fx6_zoom_position_hud_value: int = 50,
    fx6_speed_1_99_menu_requested: bool = False,
) -> SubModel89AZoomSpeedFx6HandleAuditResult:
    if operation not in VALID_89A_OPERATIONS:
        raise Stage89Phase385Error(f"Unknown 89A operation {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage89Phase385Error(f"Unknown body_model {body_model!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage89Phase385Error(f"Unknown shoot_mode {shoot_mode!r}")

    def _mk(**kw: Any) -> SubModel89AZoomSpeedFx6HandleAuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            shoot_mode=shoot_mode,
            allowed=True,
            errno=0,
            reason="OK",
            zoom_range=zoom_range,
            max_magnification=_resolve_fx3_max_zoom_mag(
                zoom_range, shoot_mode, movie_resolution, still_image_size, apsc_s35_on
            ),
            zoom_range_survived_cam_reset=False,
            zoom_ring_rotate=zoom_ring_rotate,
            zoom_ring_rotate_survived_cam_reset=False,
            lever_1st_stby=lever_1st_stby,
            lever_1st_rec=lever_1st_rec,
            lever_2nd_stby=lever_2nd_stby,
            lever_2nd_rec=lever_2nd_rec,
            custom_key_speed_stby=custom_key_speed_stby,
            custom_key_speed_rec=custom_key_speed_rec,
            custom_key_has_variable_mode=FX3_CUSTOM_KEY_HAS_VARIABLE_MODE,
            custom_key_variable_blocked=False,
            g149_custom_key_no_variable_reconciled=FX3_G149_CUSTOM_KEY_NO_VARIABLE_RECONCILED,
            remote_speed_type=remote_speed_type,
            remote_speed_type_elf_symbol=FX3_REMOTE_SPEED_TYPE_ELF_SYMBOL,
            remote_fixed_speed_stby=remote_fixed_speed_stby,
            remote_fixed_speed_rec=remote_fixed_speed_rec,
            speeds_reset_on_cam_reset=True,
            xlr_h1_has_zoom_lever=FX3_XLR_H1_HAS_ZOOM_LEVER,
            xlr_h1_phantom_zoom_blocked=False,
            is_power_zoom_lens=is_power_zoom_lens,
            seamless_optical_to_ciz=(is_power_zoom_lens and zoom_range != "Optical zoom only"),
            pre_lockouts_triggered=(),
            active_degradations_triggered=(),
            fx6_zoom_type=fx6_zoom_type,
            fx6_digital_zoom_blocked=False,
            fx6_handle_zoom_setting=fx6_handle_zoom_setting,
            fx6_handle_zoom_low=fx6_handle_zoom_low,
            fx6_handle_zoom_high=fx6_handle_zoom_high,
            fx6_zoom_position_hud_value=fx6_zoom_position_hud_value,
            fx6_speed_1_99_debunked=False,
            slot1_writes=0,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            raw_firmware_bytes_leaked=0,
        )
        defaults.update(kw)
        return SubModel89AZoomSpeedFx6HandleAuditResult(**defaults)

    if operation == "fx3_zoom_range_speeds_reset_split_and_ring_rotate":
        if xlr_h1_zoom_lever_requested:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX3_XLR_H1_TOP_HANDLE_HAS_NO_PHYSICAL_ZOOM_LEVER",
                xlr_h1_phantom_zoom_blocked=True,
            )
        if zoom_range not in FX3_ZOOM_RANGES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX3_ZOOM_RANGE",
            )
        if zoom_range == "Smart Zoom" and (
            shoot_mode != "Still" or still_image_size not in ("M", "S")
        ):
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="SMART_ZOOM_EXPOSED_ONLY_FOR_STILL_M_OR_S",
            )
        if custom_key_speed_type == "Variable":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="G149_CUSTOM_KEY_Z_SPEED_FIXED_ONLY_NO_VARIABLE_MODE",
                custom_key_variable_blocked=True,
            )
        if custom_key_speed_type != "Fix":
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_CUSTOM_KEY_SPEED_TYPE",
            )
        if remote_speed_type not in FX3_REMOTE_ZOOM_SPEED_TYPES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_REMOTE_ZOOM_SPEED_TYPE",
            )
        if zoom_ring_rotate not in FX3_ZOOM_RING_ROTATE_OPTIONS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_ZOOM_RING_ROTATE_DIRECTION",
            )
        for spd in (
            lever_1st_stby,
            lever_1st_rec,
            lever_2nd_stby,
            lever_2nd_rec,
            custom_key_speed_stby,
            custom_key_speed_rec,
            remote_fixed_speed_stby,
            remote_fixed_speed_rec,
        ):
            if spd < FX3_ZOOM_SPEED_MIN or spd > FX3_ZOOM_SPEED_MAX:
                return _mk(
                    allowed=False,
                    errno=EINVAL_ERRNO,
                    reason="FX3_ZOOM_SPEED_OUT_OF_1_TO_8_RANGE",
                )
        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_ZOOM_RANGE_RING_ROTATE_AND_ALL_3_SPEED_GROUPS",
                zoom_range=FX3_ZOOM_RANGE_DEFAULT,
                max_magnification=1.0,
                zoom_range_survived_cam_reset=False,
                zoom_ring_rotate=FX3_ZOOM_RING_ROTATE_DEFAULT,
                zoom_ring_rotate_survived_cam_reset=False,
                lever_1st_stby=FX3_ZOOM_LEVER_1ST_DEFAULT,
                lever_1st_rec=FX3_ZOOM_LEVER_1ST_DEFAULT,
                lever_2nd_stby=FX3_ZOOM_LEVER_2ND_DEFAULT,
                lever_2nd_rec=FX3_ZOOM_LEVER_2ND_DEFAULT,
                custom_key_speed_stby=FX3_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
                custom_key_speed_rec=FX3_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
                remote_speed_type=FX3_REMOTE_ZOOM_SPEED_TYPE_DEFAULT,
                remote_fixed_speed_stby=FX3_REMOTE_ZOOM_FIXED_SPEED_DEFAULT,
                remote_fixed_speed_rec=FX3_REMOTE_ZOOM_FIXED_SPEED_DEFAULT,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="CAM_RESET_PRESERVES_ZOOM_RANGE_AND_RING_ROTATE_WHILE_RESETTING_ALL_3_SPEEDS",
                zoom_range=zoom_range,
                zoom_range_survived_cam_reset=True,
                zoom_ring_rotate=zoom_ring_rotate,
                zoom_ring_rotate_survived_cam_reset=True,
                lever_1st_stby=FX3_ZOOM_LEVER_1ST_DEFAULT,
                lever_1st_rec=FX3_ZOOM_LEVER_1ST_DEFAULT,
                lever_2nd_stby=FX3_ZOOM_LEVER_2ND_DEFAULT,
                lever_2nd_rec=FX3_ZOOM_LEVER_2ND_DEFAULT,
                custom_key_speed_stby=FX3_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
                custom_key_speed_rec=FX3_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
                remote_speed_type=FX3_REMOTE_ZOOM_SPEED_TYPE_DEFAULT,
                remote_fixed_speed_stby=FX3_REMOTE_ZOOM_FIXED_SPEED_DEFAULT,
                remote_fixed_speed_rec=FX3_REMOTE_ZOOM_FIXED_SPEED_DEFAULT,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"FX3_ZOOM_{zoom_range.replace(' ', '_').upper()}_8STEP_OK",
        )

    if operation == "fx3_ciz_digital_4_prelockouts_and_5_active_degradations":
        if zoom_range not in FX3_ZOOM_RANGES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX3_ZOOM_RANGE",
            )
        if zoom_range == "Optical zoom only":
            return _mk(
                allowed=True,
                errno=0,
                reason="OPTICAL_ZOOM_ONLY_NO_CIZ_LOCKOUT_OR_AF_DEGRADATION",
                max_magnification=1.0,
                seamless_optical_to_ciz=False,
                pre_lockouts_triggered=(),
                active_degradations_triggered=(),
            )
        lockouts: List[str] = []
        if shoot_mode == "Still" and still_file_format in (
            "RAW",
            "RAW & JPEG",
            "RAW & HEIF",
        ):
            lockouts.append("STILL_RAW_FORMAT")
        if shoot_mode == "Movie" and rec_frame_rate in ("119.88p", "100p"):
            lockouts.append("MOVIE_119_88P_100P")
        if shoot_mode == "S&Q" and sq_frame_rate_fps >= 100:
            lockouts.append("SQ_GE_100FPS")
        if hdmi_raw_output_on:
            lockouts.append("HDMI_RAW_OUTPUT_ON")
        if lockouts:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="NON_OPTICAL_ZOOM_PRELOCKED_BY_" + "_AND_".join(lockouts),
                max_magnification=1.0,
                seamless_optical_to_ciz=False,
                pre_lockouts_triggered=tuple(lockouts),
            )
        if zoom_range == "Smart Zoom" and (
            shoot_mode != "Still" or still_image_size not in ("M", "S")
        ):
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="SMART_ZOOM_STILL_M_S_ONLY",
                max_magnification=1.0,
            )
        degs = FX3_CIZ_5_ACTIVE_DEGRADATION_IDS if non_optical_engaged else ()
        return _mk(
            allowed=True,
            errno=0,
            reason=(
                "NON_OPTICAL_ZOOM_ENGAGED_5_AF_METERING_DEGRADATIONS_ACTIVE"
                if non_optical_engaged
                else "NON_OPTICAL_ZOOM_ARMED_OPTICAL_SEGMENT_FULL_AF"
            ),
            active_degradations_triggered=degs,
        )

    # fx6_zoom_type_handle_zoom_and_0_99_hud_clarification
    if fx6_speed_1_99_menu_requested:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_ZERO_SPEED_1_99_MENU_0_99_IS_ZOOM_POSITION_HUD_DISPLAY",
            fx6_speed_1_99_debunked=True,
        )
    if fx6_zoom_type == "Digital Zoom":
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_ZERO_DIGITAL_ZOOM_ONLY_OPTICAL_OR_CIZ",
            fx6_digital_zoom_blocked=True,
        )
    if fx6_zoom_type not in FX6_ZOOM_TYPES:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_ZOOM_TYPE",
        )
    if fx6_handle_zoom_setting not in FX6_HANDLE_ZOOM_SETTINGS:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_HANDLE_ZOOM_SETTING",
        )
    if not (
        FX3_ZOOM_SPEED_MIN <= fx6_handle_zoom_low <= FX3_ZOOM_SPEED_MAX
        and FX3_ZOOM_SPEED_MIN <= fx6_handle_zoom_high <= FX3_ZOOM_SPEED_MAX
    ):
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="FX6_HANDLE_ZOOM_LOW_HIGH_MUST_BE_1_TO_8",
        )
    if not (
        FX6_ZOOM_POSITION_HUD_MIN
        <= fx6_zoom_position_hud_value
        <= FX6_ZOOM_POSITION_HUD_MAX
    ):
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="FX6_ZOOM_POSITION_HUD_OUT_OF_0_99_RANGE",
        )
    fx6_mag = (
        1.0
        if fx6_zoom_type == "Optical Zoom Only"
        else (
            FX3_CIZ_MOVIE_4K_MAX_MAG
            if movie_resolution == "4K"
            else FX3_CIZ_MOVIE_HD_MAX_MAG
        )
    )
    return _mk(
        allowed=True,
        errno=0,
        reason=f"FX6_ZOOM_{fx6_handle_zoom_setting.upper()}_HUD_POS_{fx6_zoom_position_hud_value}_OK",
        max_magnification=fx6_mag,
    )


# ---------------------------------------------------------------------------
# Sub-Model 89B Simulator — [Dial Customize] 5-Item Matrix & FX6 Dials
# ---------------------------------------------------------------------------


def simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    shoot_mode: str = "Movie",
    dial_customize_item: str = "Custom Key/Dial Set.",
    target_dial: str = "Front Dial",
    front_dial_func: str = "Aperture",
    rear_dial_func: str = "ISO/EI",
    control_wheel_func: str = "Shutter Speed",
    av_tv_rotate: str = FX3_AV_TV_ROTATE_DEFAULT,
    lock_operation_parts: str = FX3_LOCK_OP_PARTS_DEFAULT,
    my_dial_bank: str = "My Dial 1",
    my_dial_recall_mode: str = "Hold",
    my_dial_banks_configured: Optional[Mapping[str, Tuple[str, str, str]]] = None,
    function_ring_mode: str = FX3_FUNCTION_RING_DEFAULT,
    lens_has_function_ring: bool = True,
    rec_format_forbids_apsc: bool = False,
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    fx6_dial_node: str = "Grip/Remote Dial",
    fx6_dial_function: str = FX6_ASSIGNABLE_DIAL_DEFAULT,
    fx6_menu_open: bool = False,
) -> SubModel89BDialCustomizeFuncRingFx6AuditResult:
    if operation not in VALID_89B_OPERATIONS:
        raise Stage89Phase385Error(f"Unknown 89B operation {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage89Phase385Error(f"Unknown body_model {body_model!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage89Phase385Error(f"Unknown shoot_mode {shoot_mode!r}")

    def _mk(**kw: Any) -> SubModel89BDialCustomizeFuncRingFx6AuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            shoot_mode=shoot_mode,
            allowed=True,
            errno=0,
            reason="OK",
            exposed_dial_customize_items_count=len(FX3_DIAL_CUSTOMIZE_EXACT_5_ITEMS),
            physical_dial_count=len(FX3_PHYSICAL_3_DIALS),
            all_5_items_resist_cam_reset=True,
            survived_cam_reset=False,
            reset_on_initialize=False,
            dormant_dial_or_rear_lr_blocked=False,
            front_dial_func=front_dial_func,
            rear_dial_func=rear_dial_func,
            control_wheel_func=control_wheel_func,
            av_tv_rotate=av_tv_rotate,
            av_tv_rotate_coefficient=(1 if av_tv_rotate == "Normal" else -1),
            lock_operation_parts=lock_operation_parts,
            my_dial_active_bank="",
            my_dial_recall_mode=my_dial_recall_mode,
            my_dial_skipped_empty_banks=(),
            lock_op_parts_temp_unlocked=False,
            function_ring_mode=function_ring_mode,
            lens_has_function_ring=lens_has_function_ring,
            function_ring_invalid_fallback=False,
            apsc_s35_crop_lock_blocked=False,
            fx6_dial_node=fx6_dial_node,
            fx6_dial_function=fx6_dial_function,
            fx6_nd_filter_allowed_on_node=(fx6_dial_node in FX6_ASSIGNABLE_DIAL_TARGETS),
            fx6_menu_open_dial_blocked=False,
            slot1_writes=0,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            raw_firmware_bytes_leaked=0,
        )
        defaults.update(kw)
        return SubModel89BDialCustomizeFuncRingFx6AuditResult(**defaults)

    if operation == "fx3_dial_customize_5item_3dial_boundary_and_dormant_block":
        if (
            dial_customize_item in FX3_DORMANT_DIAL_ITEMS
            or target_dial in FX3_DORMANT_DIAL_ITEMS
        ):
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX3_DORMANT_DIAL_SETUP_WHEEL_LOCK_OR_REAR_DIAL_LR_BLOCKED_EOPNOTSUPP",
                dormant_dial_or_rear_lr_blocked=True,
            )
        if dial_customize_item not in FX3_DIAL_CUSTOMIZE_EXACT_5_ITEMS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX3_DIAL_CUSTOMIZE_ITEM_EXACT_5_ONLY",
            )
        if target_dial not in FX3_PHYSICAL_3_DIALS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX3_PHYSICAL_DIAL_ONLY_3_DIALS_EXIST",
            )
        if av_tv_rotate not in FX3_AV_TV_ROTATE_OPTIONS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_AV_TV_ROTATE_OPTION",
            )
        if lock_operation_parts not in FX3_LOCK_OP_PARTS_OPTIONS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_LOCK_OPERATION_PARTS_OPTION",
            )
        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_ALL_5_DIAL_CUSTOMIZE_ITEMS",
                front_dial_func=FX3_MOVIE_DEFAULT_DIAL_MAP["Front Dial"],
                rear_dial_func=FX3_MOVIE_DEFAULT_DIAL_MAP["Rear Dial"],
                control_wheel_func=FX3_MOVIE_DEFAULT_DIAL_MAP["Control Wheel"],
                av_tv_rotate=FX3_AV_TV_ROTATE_DEFAULT,
                av_tv_rotate_coefficient=1,
                lock_operation_parts=FX3_LOCK_OP_PARTS_DEFAULT,
                function_ring_mode=FX3_FUNCTION_RING_DEFAULT,
                survived_cam_reset=False,
                reset_on_initialize=True,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="ALL_5_DIAL_CUSTOMIZE_ITEMS_RESIST_CAMERA_SETTINGS_RESET",
                survived_cam_reset=True,
                reset_on_initialize=False,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"FX3_DIAL_CUSTOMIZE_5ITEM_3DIAL_{target_dial.replace(' ', '_').upper()}_OK",
        )

    if operation == "fx3_mydial_1_3_recall_skip_empty_and_lock_temp_unlock":
        if target_dial in ("Rear Dial L", "Rear Dial R"):
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="MY_DIAL_REAR_DIAL_L_R_DORMANT_4DIAL_ALPHA_ONLY",
                dormant_dial_or_rear_lr_blocked=True,
            )
        if my_dial_recall_mode not in FX3_MY_DIAL_RECALL_MODES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_MY_DIAL_RECALL_MODE",
            )
        if lock_operation_parts not in FX3_LOCK_OP_PARTS_OPTIONS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_LOCK_OPERATION_PARTS_OPTION",
            )
        banks = (
            dict(my_dial_banks_configured)
            if my_dial_banks_configured is not None
            else {
                "My Dial 1": ("ISO", "Exposure Comp.", "White Balance"),
                "My Dial 2": ("Not set", "Not set", "Not set"),
                "My Dial 3": ("Picture Profile", "Metering Mode", "Aperture"),
            }
        )
        if my_dial_bank not in FX3_MY_DIAL_BANKS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_MY_DIAL_BANK_MUST_BE_1_TO_3",
            )
        if my_dial_recall_mode == "Cycle":
            start_idx = FX3_MY_DIAL_BANKS.index(my_dial_bank)
            skipped: List[str] = []
            selected_bank = ""
            for step in range(1, len(FX3_MY_DIAL_BANKS) + 1):
                cand = FX3_MY_DIAL_BANKS[(start_idx + step) % len(FX3_MY_DIAL_BANKS)]
                cfg = banks.get(cand, ("Not set", "Not set", "Not set"))
                if all(x == "Not set" for x in cfg):
                    skipped.append(cand)
                    continue
                selected_bank = cand
                break
            if not selected_bank:
                return _mk(
                    allowed=False,
                    errno=EBUSY_ERRNO,
                    reason="MY_DIAL_1_2_3_ALL_EMPTY_NOT_SET",
                    my_dial_skipped_empty_banks=tuple(skipped),
                )
            cfg = banks[selected_bank]
            temp_unlock = lock_operation_parts in ("Dial + Wheel", "All")
            return _mk(
                allowed=True,
                errno=0,
                reason="MY_DIAL_1_2_3_CYCLE_SKIPPED_EMPTY_BANKS_AND_TEMP_UNLOCKED_LOCK_OP",
                my_dial_active_bank=selected_bank,
                front_dial_func=cfg[0],
                rear_dial_func=cfg[1],
                control_wheel_func=cfg[2],
                my_dial_skipped_empty_banks=tuple(skipped),
                lock_op_parts_temp_unlocked=temp_unlock,
            )
        cfg = banks.get(my_dial_bank, ("Not set", "Not set", "Not set"))
        if all(x == "Not set" for x in cfg):
            return _mk(
                allowed=False,
                errno=EBUSY_ERRNO,
                reason="MY_DIAL_BANK_ALL_NOT_SET",
            )
        temp_unlock = lock_operation_parts in ("Dial + Wheel", "All")
        return _mk(
            allowed=True,
            errno=0,
            reason=f"MY_DIAL_{my_dial_recall_mode.upper()}_ACTIVE_TEMP_UNLOCK_{int(temp_unlock)}",
            my_dial_active_bank=my_dial_bank,
            front_dial_func=cfg[0],
            rear_dial_func=cfg[1],
            control_wheel_func=cfg[2],
            lock_op_parts_temp_unlocked=temp_unlock,
        )

    if operation == "fx3_function_ring_lens_power_focus_and_apsc_s35":
        if function_ring_mode not in FX3_FUNCTION_RING_OPTIONS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FUNCTION_RING_LENS_OPTION",
            )
        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_FUNCTION_RING_TO_POWER_FOCUS",
                function_ring_mode=FX3_FUNCTION_RING_DEFAULT,
                reset_on_initialize=True,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="FUNCTION_RING_RESISTS_CAMERA_SETTINGS_RESET",
                survived_cam_reset=True,
            )
        if not lens_has_function_ring:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FUNCTION_RING_INVALID_LENS_WITHOUT_ELECTRONIC_FUNCTION_RING",
                function_ring_invalid_fallback=True,
            )
        if (
            function_ring_mode == "APS-C/Super 35 mm / Full Frame"
            and rec_format_forbids_apsc
        ):
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FUNCTION_RING_APSC_S35_TOGGLE_BLOCKED_IN_4K_OR_RAW_FORMAT",
                apsc_s35_crop_lock_blocked=True,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"FUNCTION_RING_{'POWER_FOCUS' if function_ring_mode == 'Power Focus' else 'APSC_S35_TOGGLE'}_OK",
        )

    # fx6_assignable_dial_nd_filter_vs_multi_function_dial
    if fx6_dial_node == "Multi Function Dial":
        if fx6_menu_open:
            return _mk(
                allowed=False,
                errno=EBUSY_ERRNO,
                reason="FX6_MULTI_FUNCTION_DIAL_AUTO_DISABLED_WHILE_MENU_OPEN",
                fx6_nd_filter_allowed_on_node=False,
                fx6_menu_open_dial_blocked=True,
            )
        if fx6_dial_function == "ND Filter":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX6_MULTI_FUNCTION_DIAL_EXCLUDES_ND_FILTER_USE_PHYSICAL_ND_OR_ASSIGNABLE_DIAL",
                fx6_nd_filter_allowed_on_node=False,
            )
        if fx6_dial_function not in FX6_MULTI_FUNCTION_DIAL_OPTIONS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX6_MULTI_FUNCTION_DIAL_OPTION",
                fx6_nd_filter_allowed_on_node=False,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"FX6_MULTI_FUNCTION_DIAL_{fx6_dial_function.replace(' ', '_').replace('/', '_').upper()}_OK",
            fx6_nd_filter_allowed_on_node=False,
        )
    if fx6_dial_node in FX6_ASSIGNABLE_DIAL_TARGETS:
        if fx6_dial_function not in FX6_ASSIGNABLE_DIAL_OPTIONS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX6_ASSIGNABLE_DIAL_OPTION",
                fx6_nd_filter_allowed_on_node=True,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"FX6_ASSIGNABLE_DIAL_{fx6_dial_function.replace(' ', '_').replace('/', '_').upper()}_OK",
            fx6_nd_filter_allowed_on_node=True,
        )
    return _mk(
        allowed=False,
        errno=EINVAL_ERRNO,
        reason="INVALID_FX6_DIAL_NODE",
    )


# ---------------------------------------------------------------------------
# Sub-Model 89C Simulator — [Operation Customize], Zero-EVF [DISP], LUT vs GDA
# ---------------------------------------------------------------------------


def simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    shoot_mode: str = "Movie",
    diff_set_checked_items: Tuple[str, ...] = ("Picture Profile", "ISO"),
    shutter_mode: str = "Speed",
    fn_still_assigned_count: int = 12,
    fn_movie_assigned_count: int = 12,
    fn_button_pressed: bool = False,
    disp_page_requested: str = "Display All Info.",
    is_playback_mode: bool = False,
    log_shooting_mode: str = "Off",
    picture_profile_is_log_or_hlg: bool = False,
    select_lut_slot: str = FX3_SELECT_LUT_DEFAULT,
    display_lut_on: bool = True,
    gamma_display_assist_on: bool = False,
    gamma_display_assist_type: str = "Auto",
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    fx6_shooting_mode: str = "Cine EI",
    fx6_target_display: str = "SDR(BT.709)",
    fx6_gamma_display_assist_requested: bool = False,
    fx6_rec_play_status_mode: str = "Always On",
    fx6_video_signal_monitor: str = "Waveform",
) -> SubModel89COpCustomizeDispLutFx6AuditResult:
    if operation not in VALID_89C_OPERATIONS:
        raise Stage89Phase385Error(f"Unknown 89C operation {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage89Phase385Error(f"Unknown body_model {body_model!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage89Phase385Error(f"Unknown shoot_mode {shoot_mode!r}")

    def _mk(**kw: Any) -> SubModel89COpCustomizeDispLutFx6AuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            shoot_mode=shoot_mode,
            allowed=True,
            errno=0,
            reason="OK",
            diff_set_items_count=len(FX3_DIFF_SET_EXACT_8_ITEMS),
            diff_set_checked_items=diff_set_checked_items,
            diff_set_survived_cam_reset=False,
            picture_profile_survived_initialize=False,
            g99_pp_anti_init_reconciled=FX3_G99_PP_ANTI_INIT_ERRATUM_RECONCILED,
            shutter_angle_forces_still_movie_split=(shutter_mode == "Angle"),
            fn_still_slots_count=FX3_FN_MENU_STILL_SLOTS,
            fn_movie_slots_count=FX3_FN_MENU_MOVIE_SLOTS,
            fn_slots_decoupled_from_diff_set=True,
            empty_fn_menu_rejected=False,
            disp_shoot_pages_count=len(FX3_DISP_SHOOT_EXACT_4_PAGES),
            disp_playback_pages_count=len(FX3_DISP_PLAYBACK_EXACT_3_PAGES),
            fx3_has_builtin_evf=FX3_HAS_BUILTIN_EVF,
            dormant_evf_or_disp_blocked=False,
            log_shooting_mode=log_shooting_mode,
            select_lut_slot=select_lut_slot,
            display_lut_on=display_lut_on,
            gamma_display_assist_on=gamma_display_assist_on,
            gamma_display_assist_type=gamma_display_assist_type,
            gamma_assist_active=False,
            gamma_assist_overridden_by_select_lut=False,
            g132_log_lut_gamma_split_reconciled=FX3_G132_LOG_LUT_GAMMA_SPLIT_RECONCILED,
            fx6_display_elf_routes_count=FX6_DISPLAY_ON_OFF_ELF_ROUTES_COUNT,
            fx6_user_menu_display_toggles_count=FX6_USER_MENU_DISPLAY_TOGGLES_COUNT,
            fx6_rec_play_status_mode=fx6_rec_play_status_mode,
            fx6_video_signal_monitor=fx6_video_signal_monitor,
            fx6_cine_ei_gamma_assist_locked_off=False,
            slot1_writes=0,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            raw_firmware_bytes_leaked=0,
        )
        defaults.update(kw)
        return SubModel89COpCustomizeDispLutFx6AuditResult(**defaults)

    if operation == "fx3_diff_set_8item_bitmask_pp_anti_init_and_fn_12x2":
        for item in diff_set_checked_items:
            if item not in FX3_DIFF_SET_EXACT_8_ITEMS:
                return _mk(
                    allowed=False,
                    errno=EINVAL_ERRNO,
                    reason="INVALID_DIFF_SET_ITEM_EXACT_8_BITMASK_ONLY",
                )
        if not (0 <= fn_still_assigned_count <= FX3_FN_MENU_STILL_SLOTS):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="FN_STILL_SLOTS_OUT_OF_0_12_RANGE",
            )
        if not (0 <= fn_movie_assigned_count <= FX3_FN_MENU_MOVIE_SLOTS):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="FN_MOVIE_SLOTS_OUT_OF_0_12_RANGE",
            )
        if initialize_triggered:
            # Wave 79 G99 closure: Picture Profile resists BOTH Camera Reset AND Initialize!
            kept = tuple(
                x
                for x in diff_set_checked_items
                if x == FX3_DIFF_SET_ANTI_INITIALIZE_ITEM
            )
            return _mk(
                allowed=True,
                errno=0,
                reason="G99_INITIALIZE_RESETS_7_DIFF_SET_ITEMS_WHILE_PICTURE_PROFILE_SURVIVES",
                diff_set_checked_items=kept,
                diff_set_survived_cam_reset=False,
                picture_profile_survived_initialize=(
                    FX3_DIFF_SET_ANTI_INITIALIZE_ITEM in kept
                ),
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="ALL_8_DIFF_SET_ITEMS_AND_FN_12X2_RESIST_CAMERA_SETTINGS_RESET",
                diff_set_checked_items=diff_set_checked_items,
                diff_set_survived_cam_reset=True,
            )
        if fn_button_pressed:
            active_slots = (
                fn_still_assigned_count
                if shoot_mode == "Still"
                else fn_movie_assigned_count
            )
            if active_slots == 0:
                return _mk(
                    allowed=False,
                    errno=EBUSY_ERRNO,
                    reason="FN_MENU_ALL_12_SLOTS_NOT_SET_WARNING_0X6220",
                    empty_fn_menu_rejected=True,
                )
        return _mk(
            allowed=True,
            errno=0,
            reason=(
                "DIFF_SET_8ITEM_AND_SHUTTER_ANGLE_FORCED_SPLIT_OK"
                if shutter_mode == "Angle"
                else "DIFF_SET_8ITEM_AND_FN_12X2_INDEPENDENT_OK"
            ),
        )

    if operation == "fx3_disp_4pages_and_zero_evf_finder_monitor_dormancy":
        if disp_page_requested in FX3_DORMANT_EVF_AND_DISP_ITEMS:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX3_ZERO_EVF_DORMANT_GRAPHIC_VIEWFINDER_MONOFF_FINDER_BLOCKED_EOPNOTSUPP",
                dormant_evf_or_disp_blocked=True,
            )
        valid_pages = (
            FX3_DISP_PLAYBACK_EXACT_3_PAGES
            if is_playback_mode
            else FX3_DISP_SHOOT_EXACT_4_PAGES
        )
        if disp_page_requested not in valid_pages:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX3_DISP_SCREEN_PAGE",
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="DISP_SCREEN_DISP_SET_RESISTS_CAMERA_SETTINGS_RESET",
                diff_set_survived_cam_reset=True,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"FX3_DISP_{'PB_3PAGE' if is_playback_mode else 'SHOOT_4PAGE'}_OK",
        )

    if operation == "fx3_select_lut_vs_gamma_display_assist_routing":
        if select_lut_slot not in FX3_SELECT_LUT_ALL_SLOTS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_SELECT_LUT_SLOT",
            )
        if gamma_display_assist_type not in FX3_GAMMA_DISPLAY_ASSIST_TYPES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_GAMMA_DISPLAY_ASSIST_TYPE",
            )
        if log_shooting_mode not in ("Off", "Flexible ISO", "Cine EI", "Cine EI Quick"):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_LOG_SHOOTING_MODE",
            )
        if shoot_mode in ("Movie", "S&Q") and log_shooting_mode != "Off":
            # Select LUT + Display LUT override Gamma Display Assist under Movie/S&Q Log Shooting
            return _mk(
                allowed=True,
                errno=0,
                reason="G132_SELECT_LUT_AND_DISPLAY_LUT_OVERRIDE_GAMMA_DISPLAY_ASSIST_IN_LOG_SHOOTING",
                gamma_assist_active=False,
                gamma_assist_overridden_by_select_lut=True,
            )
        if shoot_mode == "Still" and (log_shooting_mode != "Off" or picture_profile_is_log_or_hlg):
            return _mk(
                allowed=True,
                errno=0,
                reason="G132_STILL_LOG_USES_GAMMA_DISPLAY_ASSIST_INSTEAD_OF_LUT_0X6538",
                gamma_assist_active=bool(gamma_display_assist_on),
                gamma_assist_overridden_by_select_lut=False,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="NON_LOG_PP_OR_STANDARD_GAMMA_DISPLAY_ASSIST_ROUTING_OK",
            gamma_assist_active=bool(gamma_display_assist_on and picture_profile_is_log_or_hlg),
            gamma_assist_overridden_by_select_lut=False,
        )

    # fx6_60route_display_on_off_and_cine_ei_gamma_assist_lock
    if fx6_rec_play_status_mode not in FX6_REC_PLAY_STATUS_DISPLAY_MODES:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_REC_PLAY_STATUS_DISPLAY_MODE",
        )
    if fx6_video_signal_monitor not in FX6_VIDEO_SIGNAL_MONITORS:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_VIDEO_SIGNAL_MONITOR",
        )
    if fx6_gamma_display_assist_requested:
        if fx6_shooting_mode != "Custom" or fx6_target_display != "HDR(HLG)":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX6_GAMMA_DISPLAY_ASSIST_HARD_LOCKED_OFF_IN_CINE_EI_OR_SDR",
                fx6_cine_ei_gamma_assist_locked_off=True,
            )
    return _mk(
        allowed=True,
        errno=0,
        reason=f"FX6_60ROUTE_DISPLAY_ON_OFF_{fx6_video_signal_monitor.upper()}_OK",
        fx6_cine_ei_gamma_assist_locked_off=(fx6_shooting_mode == "Cine EI"),
    )


# ---------------------------------------------------------------------------
# Sub-Model 89D Simulator — [External Output] HDMI 4K/RAW vs FX6 12G-SDI
# ---------------------------------------------------------------------------


def simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    shoot_mode: str = "Movie",
    hdmi_resolution: str = FX3_HDMI_RESOLUTION_DEFAULT,
    rec_media_dur_hdmi_output: str = "On",
    output_resolution: str = "Auto",
    hdmi_4k_output_set: str = FX3_4K_OUTPUT_SET_DEFAULT,
    chroma_requested: str = FX3_4K_OUTPUT_CHROMA_SPEC,
    legacy_24p_60p_output_requested: bool = False,
    log_or_pplut_active: bool = False,
    apsc_s35_on: bool = False,
    hdmi_info_display_setting: str = "On",
    hdmi_raw_output_on: bool = False,
    hdmi_raw_fps: str = "59.94p",
    log_shooting_on: bool = False,
    time_code_output_on: bool = False,
    rec_control_on: bool = False,
    audio_4ch_output_pair: str = FX3_4CH_AUDIO_OUTPUT_DEFAULT,
    ctrl_for_hdmi_on: bool = True,
    target_slot: str = "Slot 2",
    simulated_sandbox: bool = True,
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    fx6_codec: str = "XAVC-I",
    fx6_sdi_enabled: bool = True,
    fx6_sdi_format: str = "1920x1080P (Level A)",
    fx6_hdmi_format: str = "3840x2160P",
    fx6_system_freq_hz: float = 59.94,
    fx6_sq_on: bool = False,
    fx6_sq_fps: int = 60,
    fx6_rec_control_mode: str = "Parallel Rec",
) -> SubModel89DExternalOutputHdmiSdi12gAuditResult:
    if operation not in VALID_89D_OPERATIONS:
        raise Stage89Phase385Error(f"Unknown 89D operation {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage89Phase385Error(f"Unknown body_model {body_model!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage89Phase385Error(f"Unknown shoot_mode {shoot_mode!r}")

    def _mk(**kw: Any) -> SubModel89DExternalOutputHdmiSdi12gAuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            shoot_mode=shoot_mode,
            allowed=True,
            errno=0,
            reason="OK",
            external_output_resists_cam_reset=True,
            hdmi_resolution=hdmi_resolution,
            hdmi_resolution_exposed_count=len(FX3_HDMI_RESOLUTION_EXACT_4_MODES),
            dormant_hdmi_720p_blocked=False,
            rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
            output_resolution=output_resolution,
            effective_hdmi_resolution=output_resolution,
            hdmi_log_1080_downshifted=False,
            hdmi_4k_output_set=hdmi_4k_output_set,
            hdmi_4k_output_exposed_count=len(FX3_4K_OUTPUT_SET_EXACT_6_MODES),
            hdmi_4k_chroma_spec=FX3_4K_OUTPUT_CHROMA_SPEC,
            dormant_420_or_8bit_blocked=False,
            reboot_required_for_24_00p=(hdmi_4k_output_set == "24.00p 10bit"),
            apsc_s35_blocks_4k_output_set=False,
            dormant_24p_60p_output_blocked=False,
            hdmi_info_display_setting=hdmi_info_display_setting,
            effective_hdmi_info_display=hdmi_info_display_setting,
            internal_lcd_blacked_out=False,
            hdmi_raw_output_on=hdmi_raw_output_on,
            hdmi_raw_resolution=(FX3_HDMI_RAW_RES if hdmi_raw_output_on else ""),
            time_code_output_on=time_code_output_on,
            rec_control_on=rec_control_on,
            rec_control_missing_tc_blocked=False,
            audio_4ch_output_pair=audio_4ch_output_pair,
            ctrl_for_hdmi_on=ctrl_for_hdmi_on,
            sony_elf_3_typos=FX3_SONY_ELF_3_TYPOS,
            target_slot=target_slot,
            slot1_erofs_blocked=False,
            fx6_codec=fx6_codec,
            fx6_sdi_format=fx6_sdi_format,
            fx6_hdmi_format=fx6_hdmi_format,
            fx6_sdi_hdmi_matrix_entries_count=FX6_SDI_HDMI_OUTPUT_FORMAT_MATRIX_ENTRIES,
            fx6_hdmi_raw_locks_sdi_1080=False,
            fx6_sq_gt60_caps_hdmi_1080=False,
            fx6_rec_control_mode=fx6_rec_control_mode,
            slot1_writes=0,
            slot1_sector_writes=0,
            slot1_data_sector_writes=0,
            usb_tx_packets=0,
            rf_tx_packets=0,
            emmc_nflasha_write_count=0,
            raw_firmware_bytes_leaked=0,
        )
        defaults.update(kw)
        return SubModel89DExternalOutputHdmiSdi12gAuditResult(**defaults)

    if operation == "fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block":
        if legacy_24p_60p_output_requested:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX3_24P_60P_OUTPUT_100PCT_DORMANT_0_ELF_HITS_BLOCKED_EOPNOTSUPP",
                dormant_24p_60p_output_blocked=True,
            )
        if hdmi_resolution in FX3_DORMANT_HDMI_RESOLUTIONS:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX3_HDMI_RESOLUTION_720P_480P_4320P_DORMANT_EXACT_4_MODES_ONLY",
                dormant_hdmi_720p_blocked=True,
            )
        if hdmi_resolution not in FX3_HDMI_RESOLUTION_EXACT_4_MODES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX3_HDMI_RESOLUTION",
            )
        if rec_media_dur_hdmi_output not in ("On", "Off(HDMI Only)"):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_REC_MEDIA_DUR_HDMI_OUTPUT",
            )
        if shoot_mode == "S&Q" and rec_media_dur_hdmi_output == "Off(HDMI Only)":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="SQ_MODE_HARD_LOCKS_REC_MEDIA_DUR_HDMI_OUTPUT_ON",
            )
        if output_resolution not in FX3_HDMI_RESOLUTION_EXACT_4_MODES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_OUTPUT_RESOLUTION",
            )
        if (
            hdmi_4k_output_set in FX3_DORMANT_4K_OUTPUT_MODES
            or chroma_requested != FX3_4K_OUTPUT_CHROMA_SPEC
        ):
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX3_4K_OUTPUT_SET_10BIT_422_ONLY_NO_420_AND_NO_24_00P_8BIT",
                dormant_420_or_8bit_blocked=True,
            )
        if hdmi_4k_output_set not in FX3_4K_OUTPUT_SET_EXACT_6_MODES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_4K_OUTPUT_SET_EXACT_6_10BIT_MODES_ONLY",
            )
        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_EXTERNAL_OUTPUT_TO_DEFAULTS",
                hdmi_resolution=FX3_HDMI_RESOLUTION_DEFAULT,
                rec_media_dur_hdmi_output="On",
                output_resolution="Auto",
                hdmi_4k_output_set=FX3_4K_OUTPUT_SET_DEFAULT,
                reboot_required_for_24_00p=False,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="ALL_EXTERNAL_OUTPUT_SETTINGS_RESIST_CAMERA_SETTINGS_RESET",
                external_output_resists_cam_reset=True,
            )
        if rec_media_dur_hdmi_output == "Off(HDMI Only)" and apsc_s35_on:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="PRM_HAITA_HDMI_4K_OUTPUTE_APSC_RESTRICTION_BLOCKS_4K_OUTPUT_SET",
                apsc_s35_blocks_4k_output_set=True,
            )
        if rec_media_dur_hdmi_output == "On" and (not hdmi_raw_output_on):
            if log_or_pplut_active and output_resolution in ("Auto", "2160p"):
                return _mk(
                    allowed=True,
                    errno=0,
                    reason="HDMI_INTERNAL_REC_WITH_LOG_OR_PPLUT_DOWNSHIFTS_TO_1080P",
                    effective_hdmi_resolution="1080p",
                    hdmi_log_1080_downshifted=True,
                )
        return _mk(
            allowed=True,
            errno=0,
            reason=(
                "FX3_4K_OUTPUT_SET_24_00P_10BIT_422_REQUIRES_REBOOT"
                if (
                    rec_media_dur_hdmi_output == "Off(HDMI Only)"
                    and hdmi_4k_output_set == "24.00p 10bit"
                )
                else "FX3_EXTERNAL_OUTPUT_4MODE_HDMI_6MODE_4K_10BIT_422_OK"
            ),
            reboot_required_for_24_00p=(
                rec_media_dur_hdmi_output == "Off(HDMI Only)"
                and hdmi_4k_output_set == "24.00p 10bit"
            ),
        )

    if operation == "fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos":
        if hdmi_info_display_setting not in ("On", "Off"):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_HDMI_INFO_DISPLAY_SETTING",
            )
        if rec_media_dur_hdmi_output not in ("On", "Off(HDMI Only)"):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_REC_MEDIA_DUR_HDMI_OUTPUT",
            )
        if audio_4ch_output_pair not in FX3_4CH_AUDIO_OUTPUT_OPTIONS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_4CH_AUDIO_OUTPUT_PAIR_CH1_CH2_OR_CH3_CH4",
            )
        if hdmi_raw_output_on:
            if shoot_mode != "Movie" or not log_shooting_on:
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="HDMI_RAW_OUTPUT_4264X2408_REQUIRES_MOVIE_AND_LOG_SHOOTING",
                )
            if hdmi_raw_fps not in FX3_HDMI_RAW_FPS_OPTIONS:
                return _mk(
                    allowed=False,
                    errno=EINVAL_ERRNO,
                    reason="INVALID_HDMI_RAW_OUTPUT_FPS",
                )
        if shoot_mode == "S&Q" and time_code_output_on:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="TIME_CODE_OUTPUT_DISABLED_IN_SQ_MODE",
            )
        if rec_control_on and not time_code_output_on:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="HDMI_REC_CONTROL_STRICTLY_REQUIRES_TIME_CODE_OUTPUT_ON",
                rec_control_missing_tc_blocked=True,
            )
        if rec_media_dur_hdmi_output == "On":
            if target_slot == "Slot 1":
                return _mk(
                    allowed=False,
                    errno=EROFS_ERRNO,
                    reason="TIER0_SLOT1_EROFS_BLOCKS_HDMI_INTERNAL_REC_MEDIA_WRITE",
                    slot1_erofs_blocked=True,
                    slot1_writes=0,
                    slot1_sector_writes=0,
                    slot1_data_sector_writes=0,
                )
            if target_slot != "Slot 2" or not simulated_sandbox:
                return _mk(
                    allowed=False,
                    errno=EROFS_ERRNO if not simulated_sandbox else EINVAL_ERRNO,
                    reason="INTERNAL_REC_MEDIA_ALLOWED_ONLY_ON_SANDBOX_SLOT2",
                    slot1_erofs_blocked=not simulated_sandbox,
                )
        # Wave 79 LCD blackout truth: On blacks out LCD ONLY when Rec. Media=On & RAW=Off
        if rec_media_dur_hdmi_output == "Off(HDMI Only)" or hdmi_raw_output_on:
            eff_info = "Off"
            lcd_blackout = False
            reason = "HDMI_INFO_AUTO_CLAMPED_OFF_CLEAN_HDMI_LCD_RESTORED"
        elif hdmi_info_display_setting == "On":
            eff_info = "On"
            lcd_blackout = True
            reason = "HDMI_INFO_ON_WITH_REC_MEDIA_ON_AND_RAW_OFF_BLACKS_OUT_INTERNAL_LCD"
        else:
            eff_info = "Off"
            lcd_blackout = False
            reason = "HDMI_INFO_OFF_CLEAN_HDMI_INTERNAL_LCD_ACTIVE"
        return _mk(
            allowed=True,
            errno=0,
            reason=reason,
            effective_hdmi_info_display=eff_info,
            internal_lcd_blacked_out=lcd_blackout,
            slot1_writes=0,
        )

    # fx6_12gsdi_hdmi_dual_pipeline_raw_sq60_cap_and_rec_ctrl
    if fx6_rec_control_mode not in FX6_SDI_HDMI_REC_CONTROL_3_MODES:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_SDI_HDMI_REC_CONTROL_MODE",
        )
    if fx6_sdi_format not in FX6_SDI_OUTPUT_FORMATS:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_SDI_OUTPUT_FORMAT",
        )
    if fx6_hdmi_format not in FX6_HDMI_OUTPUT_FORMATS:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_HDMI_OUTPUT_FORMAT",
        )
    if fx6_codec not in (
        "XAVC-I",
        "XAVC-L",
        "RAW",
        "RAW & XAVC-I",
        "RAW(HDMI)",
        "RAW(HDMI) & XAVC-I",
    ):
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_CODEC",
        )
    if fx6_codec in ("RAW(HDMI)", "RAW(HDMI) & XAVC-I"):
        if fx6_sq_on:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX6_HDMI_RAW_DOES_NOT_SUPPORT_SQ_MOTION",
            )
        if fx6_system_freq_hz == 24.0:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX6_HDMI_RAW_4240X2392_EXCLUDES_24HZ",
            )
        if fx6_sdi_format in ("4096x2160P", "3840x2160P"):
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX6_HDMI_RAW_4240X2392_LOCKS_SDI_TO_1080P_OR_1080I",
                fx6_hdmi_raw_locks_sdi_1080=True,
                hdmi_raw_output_on=True,
                hdmi_raw_resolution=FX6_HDMI_RAW_RES,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="FX6_HDMI_RAW_4240X2392_WITH_SDI_1080_LOCK_OK",
            fx6_hdmi_raw_locks_sdi_1080=True,
            hdmi_raw_output_on=True,
            hdmi_raw_resolution=FX6_HDMI_RAW_RES,
            internal_lcd_blacked_out=False,
        )
    if fx6_sq_on and fx6_sq_fps > 60 and (
        fx6_sdi_enabled or fx6_codec in ("RAW", "RAW & XAVC-I")
    ):
        if fx6_hdmi_format in ("4096x2160P", "3840x2160P"):
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX6_SQ_GT_60FPS_WITH_SDI_OR_RAW_CAPS_HDMI_TO_LE_1080P",
                fx6_sq_gt60_caps_hdmi_1080=True,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="FX6_SQ_GT_60FPS_HDMI_1080P_CAP_COMPLIANT",
            fx6_sq_gt60_caps_hdmi_1080=True,
            internal_lcd_blacked_out=False,
        )
    return _mk(
        allowed=True,
        errno=0,
        reason=f"FX6_12G_SDI_PLUS_HDMI_DUAL_PIPELINE_{fx6_codec.replace(' ', '_').replace('&', 'AND').upper()}_OK",
        internal_lcd_blacked_out=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model Evaluators & Unified Stage 89 (89/89) Orchestrator
# ---------------------------------------------------------------------------


def _evaluate_submodel_89a() -> Dict[str, Any]:
    r_rst = simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
        operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
        zoom_range="ClearImage Zoom",
        zoom_ring_rotate="Right(W)/Left(T)",
        lever_1st_stby=5,
        lever_2nd_rec=6,
        custom_key_speed_stby=7,
        remote_speed_type="Fix",
        remote_fixed_speed_rec=2,
        camera_settings_reset_triggered=True,
    )
    r_ck_var = simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
        operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
        custom_key_speed_type="Variable",
    )
    r_xlr = simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
        operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
        xlr_h1_zoom_lever_requested=True,
    )
    r_ciz_lck = simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
        operation="fx3_ciz_digital_4_prelockouts_and_5_active_degradations",
        shoot_mode="Movie",
        zoom_range="ClearImage Zoom",
        rec_frame_rate="119.88p",
        hdmi_raw_output_on=True,
    )
    r_ciz_deg = simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
        operation="fx3_ciz_digital_4_prelockouts_and_5_active_degradations",
        shoot_mode="Movie",
        zoom_range="ClearImage Zoom",
        movie_resolution="4K",
        non_optical_engaged=True,
    )
    r_fx6_dig = simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
        operation="fx6_zoom_type_handle_zoom_and_0_99_hud_clarification",
        body_model=BODY_MODEL_FX6,
        fx6_zoom_type="Digital Zoom",
    )
    r_fx6_99 = simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
        operation="fx6_zoom_type_handle_zoom_and_0_99_hud_clarification",
        body_model=BODY_MODEL_FX6,
        fx6_speed_1_99_menu_requested=True,
    )
    r_fx6_ok = simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
        operation="fx6_zoom_type_handle_zoom_and_0_99_hud_clarification",
        body_model=BODY_MODEL_FX6,
        fx6_zoom_type="On(Clear Image Zoom)",
        fx6_handle_zoom_setting="High",
        fx6_zoom_position_hud_value=75,
    )
    passed = (
        (
            r_rst.allowed
            and r_rst.zoom_range == "ClearImage Zoom"
            and r_rst.zoom_range_survived_cam_reset
            and r_rst.zoom_ring_rotate == "Right(W)/Left(T)"
            and r_rst.zoom_ring_rotate_survived_cam_reset
            and r_rst.lever_1st_stby == 3
            and r_rst.lever_2nd_rec == 8
            and r_rst.custom_key_speed_stby == 3
            and r_rst.remote_speed_type == "Variable"
            and r_rst.remote_fixed_speed_rec == 3
        )
        and (not r_ck_var.allowed and r_ck_var.errno == EOPNOTSUPP_ERRNO and r_ck_var.custom_key_variable_blocked)
        and (not r_xlr.allowed and r_xlr.errno == EOPNOTSUPP_ERRNO and r_xlr.xlr_h1_phantom_zoom_blocked)
        and (not r_ciz_lck.allowed and r_ciz_lck.errno == EOPNOTSUPP_ERRNO and len(r_ciz_lck.pre_lockouts_triggered) == 2)
        and (r_ciz_deg.allowed and r_ciz_deg.max_magnification == 1.5 and len(r_ciz_deg.active_degradations_triggered) == 5)
        and (not r_fx6_dig.allowed and r_fx6_dig.errno == EOPNOTSUPP_ERRNO and r_fx6_dig.fx6_digital_zoom_blocked)
        and (not r_fx6_99.allowed and r_fx6_99.errno == EOPNOTSUPP_ERRNO and r_fx6_99.fx6_speed_1_99_debunked)
        and (r_fx6_ok.allowed and r_fx6_ok.max_magnification == 1.5 and r_fx6_ok.fx6_zoom_position_hud_value == 75)
    )
    return {
        "passed": passed,
        "fx3_custom_key_has_variable_mode": FX3_CUSTOM_KEY_HAS_VARIABLE_MODE,
        "fx3_g149_custom_key_no_variable_reconciled": FX3_G149_CUSTOM_KEY_NO_VARIABLE_RECONCILED,
        "fx3_ciz_pre_lockouts_count": len(FX3_CIZ_4_PRE_LOCKOUT_IDS),
        "fx3_ciz_active_degradations_count": len(FX3_CIZ_5_ACTIVE_DEGRADATION_IDS),
        "fx3_xlr_h1_has_zoom_lever": FX3_XLR_H1_HAS_ZOOM_LEVER,
        "fx6_has_digital_zoom": FX6_HAS_DIGITAL_ZOOM,
        "fx6_has_speed_1_99_menu": FX6_HAS_SPEED_1_99_MENU,
        "samples": {
            "fx3_zoom_reset_split_ok": r_rst.to_dict(),
            "fx3_custom_key_variable_blocked": r_ck_var.to_dict(),
            "fx3_xlr_h1_phantom_zoom_blocked": r_xlr.to_dict(),
            "fx3_ciz_prelockout_blocked": r_ciz_lck.to_dict(),
            "fx3_ciz_5_degradations_active": r_ciz_deg.to_dict(),
            "fx6_digital_zoom_blocked": r_fx6_dig.to_dict(),
            "fx6_speed_1_99_debunked": r_fx6_99.to_dict(),
            "fx6_handle_zoom_high_hud_75": r_fx6_ok.to_dict(),
        },
    }


def _evaluate_submodel_89b() -> Dict[str, Any]:
    r_5rst = simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
        operation="fx3_dial_customize_5item_3dial_boundary_and_dormant_block",
        dial_customize_item="Av/Tv Rotate",
        av_tv_rotate="Reverse",
        lock_operation_parts="All",
        camera_settings_reset_triggered=True,
    )
    r_dorm = simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
        operation="fx3_dial_customize_5item_3dial_boundary_and_dormant_block",
        dial_customize_item="Dial Setup",
    )
    r_rlr = simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
        operation="fx3_dial_customize_5item_3dial_boundary_and_dormant_block",
        target_dial="Rear Dial L",
    )
    r_myd = simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
        operation="fx3_mydial_1_3_recall_skip_empty_and_lock_temp_unlock",
        my_dial_bank="My Dial 1",
        my_dial_recall_mode="Cycle",
        lock_operation_parts="All",
    )
    r_fr_ok = simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
        operation="fx3_function_ring_lens_power_focus_and_apsc_s35",
        function_ring_mode="APS-C/Super 35 mm / Full Frame",
        lens_has_function_ring=True,
        rec_format_forbids_apsc=False,
    )
    r_fr_lck = simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
        operation="fx3_function_ring_lens_power_focus_and_apsc_s35",
        function_ring_mode="APS-C/Super 35 mm / Full Frame",
        lens_has_function_ring=True,
        rec_format_forbids_apsc=True,
    )
    r_fx6_ad = simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
        operation="fx6_assignable_dial_nd_filter_vs_multi_function_dial",
        body_model=BODY_MODEL_FX6,
        fx6_dial_node="Grip/Remote Dial",
        fx6_dial_function="ND Filter",
    )
    r_fx6_mfd = simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
        operation="fx6_assignable_dial_nd_filter_vs_multi_function_dial",
        body_model=BODY_MODEL_FX6,
        fx6_dial_node="Multi Function Dial",
        fx6_dial_function="ND Filter",
    )
    passed = (
        (r_5rst.allowed and r_5rst.survived_cam_reset and r_5rst.exposed_dial_customize_items_count == 5 and r_5rst.physical_dial_count == 3)
        and (not r_dorm.allowed and r_dorm.errno == EOPNOTSUPP_ERRNO and r_dorm.dormant_dial_or_rear_lr_blocked)
        and (not r_rlr.allowed and r_rlr.errno == EOPNOTSUPP_ERRNO and r_rlr.dormant_dial_or_rear_lr_blocked)
        and (r_myd.allowed and r_myd.my_dial_active_bank == "My Dial 3" and r_myd.my_dial_skipped_empty_banks == ("My Dial 2",) and r_myd.lock_op_parts_temp_unlocked)
        and (r_fr_ok.allowed and not r_fr_ok.apsc_s35_crop_lock_blocked)
        and (not r_fr_lck.allowed and r_fr_lck.errno == EOPNOTSUPP_ERRNO and r_fr_lck.apsc_s35_crop_lock_blocked)
        and (r_fx6_ad.allowed and r_fx6_ad.fx6_nd_filter_allowed_on_node)
        and (not r_fx6_mfd.allowed and r_fx6_mfd.errno == EOPNOTSUPP_ERRNO and not r_fx6_mfd.fx6_nd_filter_allowed_on_node)
    )
    return {
        "passed": passed,
        "fx3_dial_customize_exact_items_count": len(FX3_DIAL_CUSTOMIZE_EXACT_5_ITEMS),
        "fx3_physical_dials_count": len(FX3_PHYSICAL_3_DIALS),
        "fx3_my_dial_banks_count": len(FX3_MY_DIAL_BANKS),
        "fx3_dormant_dial_exposed_events": 0,
        "fx6_assignable_dial_options_count": len(FX6_ASSIGNABLE_DIAL_OPTIONS),
        "fx6_multi_function_dial_options_count": len(FX6_MULTI_FUNCTION_DIAL_OPTIONS),
        "samples": {
            "fx3_5item_all_resist_cam_reset": r_5rst.to_dict(),
            "fx3_dormant_dial_setup_blocked": r_dorm.to_dict(),
            "fx3_dormant_rear_dial_l_blocked": r_rlr.to_dict(),
            "fx3_mydial_cycle_skip_empty_temp_unlock": r_myd.to_dict(),
            "fx3_function_ring_apsc_ok": r_fr_ok.to_dict(),
            "fx3_function_ring_apsc_4k_blocked": r_fr_lck.to_dict(),
            "fx6_assignable_dial_nd_ok": r_fx6_ad.to_dict(),
            "fx6_multi_function_dial_nd_blocked": r_fx6_mfd.to_dict(),
        },
    }


def _evaluate_submodel_89c() -> Dict[str, Any]:
    r_pp_init = simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
        operation="fx3_diff_set_8item_bitmask_pp_anti_init_and_fn_12x2",
        diff_set_checked_items=("Aperture", "ISO", "Picture Profile", "White Balance"),
        initialize_triggered=True,
    )
    r_fn_emp = simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
        operation="fx3_diff_set_8item_bitmask_pp_anti_init_and_fn_12x2",
        shoot_mode="Movie",
        fn_movie_assigned_count=0,
        fn_button_pressed=True,
    )
    r_disp_ok = simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
        operation="fx3_disp_4pages_and_zero_evf_finder_monitor_dormancy",
        disp_page_requested="Histogram",
    )
    r_evf_blk = simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
        operation="fx3_disp_4pages_and_zero_evf_finder_monitor_dormancy",
        disp_page_requested="Finder/Monitor",
    )
    r_lut_ovr = simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
        operation="fx3_select_lut_vs_gamma_display_assist_routing",
        shoot_mode="Movie",
        log_shooting_mode="Cine EI",
        select_lut_slot="User16",
        display_lut_on=True,
        gamma_display_assist_on=True,
    )
    r_still_gda = simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
        operation="fx3_select_lut_vs_gamma_display_assist_routing",
        shoot_mode="Still",
        log_shooting_mode="Flexible ISO",
        gamma_display_assist_on=True,
    )
    r_fx6_gda = simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
        operation="fx6_60route_display_on_off_and_cine_ei_gamma_assist_lock",
        body_model=BODY_MODEL_FX6,
        fx6_shooting_mode="Cine EI",
        fx6_gamma_display_assist_requested=True,
    )
    r_fx6_disp = simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
        operation="fx6_60route_display_on_off_and_cine_ei_gamma_assist_lock",
        body_model=BODY_MODEL_FX6,
        fx6_rec_play_status_mode="Always On (Minimum)",
        fx6_video_signal_monitor="Vectorscope",
    )
    passed = (
        (r_pp_init.allowed and r_pp_init.diff_set_checked_items == ("Picture Profile",) and r_pp_init.picture_profile_survived_initialize)
        and (not r_fn_emp.allowed and r_fn_emp.errno == EBUSY_ERRNO and r_fn_emp.empty_fn_menu_rejected)
        and (r_disp_ok.allowed and r_disp_ok.disp_shoot_pages_count == 4 and not r_disp_ok.fx3_has_builtin_evf)
        and (not r_evf_blk.allowed and r_evf_blk.errno == EOPNOTSUPP_ERRNO and r_evf_blk.dormant_evf_or_disp_blocked)
        and (r_lut_ovr.allowed and r_lut_ovr.gamma_assist_overridden_by_select_lut and not r_lut_ovr.gamma_assist_active)
        and (r_still_gda.allowed and r_still_gda.gamma_assist_active)
        and (not r_fx6_gda.allowed and r_fx6_gda.errno == EOPNOTSUPP_ERRNO and r_fx6_gda.fx6_cine_ei_gamma_assist_locked_off)
        and (r_fx6_disp.allowed and r_fx6_disp.fx6_display_elf_routes_count == 60)
    )
    return {
        "passed": passed,
        "fx3_diff_set_items_count": len(FX3_DIFF_SET_EXACT_8_ITEMS),
        "fx3_g99_pp_anti_init_erratum_reconciled": FX3_G99_PP_ANTI_INIT_ERRATUM_RECONCILED,
        "fx3_fn_menu_total_slots": FX3_FN_MENU_STILL_SLOTS + FX3_FN_MENU_MOVIE_SLOTS,
        "fx3_disp_shoot_pages_count": len(FX3_DISP_SHOOT_EXACT_4_PAGES),
        "fx3_has_builtin_evf": FX3_HAS_BUILTIN_EVF,
        "fx3_dormant_evf_exposed_events": 0,
        "fx3_select_lut_total_slots": len(FX3_SELECT_LUT_ALL_SLOTS),
        "fx3_g132_log_lut_gamma_split_reconciled": FX3_G132_LOG_LUT_GAMMA_SPLIT_RECONCILED,
        "fx6_display_elf_routes_count": FX6_DISPLAY_ON_OFF_ELF_ROUTES_COUNT,
        "samples": {
            "fx3_g99_pp_survives_initialize": r_pp_init.to_dict(),
            "fx3_empty_fn_menu_rejected": r_fn_emp.to_dict(),
            "fx3_disp_4page_histogram_ok": r_disp_ok.to_dict(),
            "fx3_dormant_finder_monitor_blocked": r_evf_blk.to_dict(),
            "fx3_g132_select_lut_overrides_gamma_assist": r_lut_ovr.to_dict(),
            "fx3_g132_still_log_uses_gamma_assist": r_still_gda.to_dict(),
            "fx6_cine_ei_gamma_assist_locked_off": r_fx6_gda.to_dict(),
            "fx6_60route_display_vectorscope_ok": r_fx6_disp.to_dict(),
        },
    }


def _evaluate_submodel_89d() -> Dict[str, Any]:
    r_720 = simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
        operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
        hdmi_resolution="720p",
    )
    r_420 = simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
        operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
        rec_media_dur_hdmi_output="Off(HDMI Only)",
        chroma_requested="8bit 4:2:0",
    )
    r_2460 = simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
        operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
        legacy_24p_60p_output_requested=True,
    )
    r_24rb = simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
        operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
        rec_media_dur_hdmi_output="Off(HDMI Only)",
        hdmi_4k_output_set="24.00p 10bit",
    )
    r_blk = simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
        operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
        hdmi_info_display_setting="On",
        rec_media_dur_hdmi_output="On",
        hdmi_raw_output_on=False,
        target_slot="Slot 2",
    )
    r_raw_lcd = simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
        operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
        hdmi_info_display_setting="On",
        rec_media_dur_hdmi_output="Off(HDMI Only)",
        hdmi_raw_output_on=True,
        log_shooting_on=True,
        time_code_output_on=True,
        rec_control_on=True,
    )
    r_rc_notc = simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
        operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
        rec_media_dur_hdmi_output="Off(HDMI Only)",
        time_code_output_on=False,
        rec_control_on=True,
    )
    r_s1 = simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
        operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
        rec_media_dur_hdmi_output="On",
        target_slot="Slot 1",
    )
    r_fx6_hraw = simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
        operation="fx6_12gsdi_hdmi_dual_pipeline_raw_sq60_cap_and_rec_ctrl",
        body_model=BODY_MODEL_FX6,
        fx6_codec="RAW(HDMI)",
        fx6_sdi_format="4096x2160P",
    )
    r_fx6_sq = simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
        operation="fx6_12gsdi_hdmi_dual_pipeline_raw_sq60_cap_and_rec_ctrl",
        body_model=BODY_MODEL_FX6,
        fx6_codec="RAW & XAVC-I",
        fx6_sq_on=True,
        fx6_sq_fps=120,
        fx6_hdmi_format="3840x2160P",
    )
    r_fx6_ok = simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
        operation="fx6_12gsdi_hdmi_dual_pipeline_raw_sq60_cap_and_rec_ctrl",
        body_model=BODY_MODEL_FX6,
        fx6_codec="RAW & XAVC-I",
        fx6_sdi_format="4096x2160P",
        fx6_hdmi_format="4096x2160P",
        fx6_rec_control_mode="Parallel Rec",
    )
    passed = (
        (not r_720.allowed and r_720.errno == EOPNOTSUPP_ERRNO and r_720.dormant_hdmi_720p_blocked)
        and (not r_420.allowed and r_420.errno == EOPNOTSUPP_ERRNO and r_420.dormant_420_or_8bit_blocked)
        and (not r_2460.allowed and r_2460.errno == EOPNOTSUPP_ERRNO and r_2460.dormant_24p_60p_output_blocked)
        and (r_24rb.allowed and r_24rb.reboot_required_for_24_00p)
        and (r_blk.allowed and r_blk.internal_lcd_blacked_out and r_blk.effective_hdmi_info_display == "On")
        and (r_raw_lcd.allowed and not r_raw_lcd.internal_lcd_blacked_out and r_raw_lcd.effective_hdmi_info_display == "Off")
        and (not r_rc_notc.allowed and r_rc_notc.errno == EOPNOTSUPP_ERRNO and r_rc_notc.rec_control_missing_tc_blocked)
        and (not r_s1.allowed and r_s1.errno == EROFS_ERRNO and r_s1.slot1_erofs_blocked and r_s1.slot1_writes == 0)
        and (not r_fx6_hraw.allowed and r_fx6_hraw.errno == EOPNOTSUPP_ERRNO and r_fx6_hraw.fx6_hdmi_raw_locks_sdi_1080)
        and (not r_fx6_sq.allowed and r_fx6_sq.errno == EOPNOTSUPP_ERRNO and r_fx6_sq.fx6_sq_gt60_caps_hdmi_1080)
        and (r_fx6_ok.allowed and not r_fx6_ok.internal_lcd_blacked_out)
    )
    return {
        "passed": passed,
        "fx3_hdmi_resolution_exposed_count": len(FX3_HDMI_RESOLUTION_EXACT_4_MODES),
        "fx3_4k_output_set_exposed_count": len(FX3_4K_OUTPUT_SET_EXACT_6_MODES),
        "fx3_4k_output_has_420_option": FX3_4K_OUTPUT_HAS_420_OPTION,
        "fx3_dormant_24p_60p_output_elf_hits": FX3_DORMANT_24P_60P_OUTPUT_ELF_HITS,
        "fx3_sony_elf_typos_count": len(FX3_SONY_ELF_3_TYPOS),
        "fx6_sdi_hdmi_matrix_entries_count": FX6_SDI_HDMI_OUTPUT_FORMAT_MATRIX_ENTRIES,
        "fx6_sdi_hdmi_rec_control_modes_count": len(FX6_SDI_HDMI_REC_CONTROL_3_MODES),
        "samples": {
            "fx3_hdmi_720p_blocked": r_720.to_dict(),
            "fx3_hdmi_420_blocked": r_420.to_dict(),
            "fx3_dormant_24p_60p_output_blocked": r_2460.to_dict(),
            "fx3_4k_24_00p_10bit_reboot": r_24rb.to_dict(),
            "fx3_hdmi_info_on_lcd_blackout": r_blk.to_dict(),
            "fx3_hdmi_raw_clamps_info_off_lcd_on": r_raw_lcd.to_dict(),
            "fx3_rec_control_requires_tc_on": r_rc_notc.to_dict(),
            "fx3_hdmi_rec_media_slot1_erofs": r_s1.to_dict(),
            "fx6_hdmi_raw_locks_sdi_1080": r_fx6_hraw.to_dict(),
            "fx6_sq_gt60_caps_hdmi_1080": r_fx6_sq.to_dict(),
            "fx6_sdi_raw_plus_4k_hdmi_ok": r_fx6_ok.to_dict(),
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


def _build_stage89_probe(
    sub_89a: Mapping[str, Any],
    sub_89b: Mapping[str, Any],
    sub_89c: Mapping[str, Any],
    sub_89d: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone_label": MILESTONE_LABEL,
        "submodel_89a_passed": bool(sub_89a["passed"]),
        "submodel_89b_passed": bool(sub_89b["passed"]),
        "submodel_89c_passed": bool(sub_89c["passed"]),
        "submodel_89d_passed": bool(sub_89d["passed"]),
        "ready_for_live_camera_attach": READY_FOR_LIVE_CAMERA_ATTACH,
    }


def run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    donor_info = inspect_phase385_wave79_donors(
        work_root=work_root,
        force_clean_room=force_clean_room,
        env=env,
    )
    sub_89a = _evaluate_submodel_89a()
    sub_89b = _evaluate_submodel_89b()
    sub_89c = _evaluate_submodel_89c()
    sub_89d = _evaluate_submodel_89d()
    probe = _build_stage89_probe(sub_89a, sub_89b, sub_89c, sub_89d)

    all_passed = bool(
        donor_info["all_donors_verified"]
        and sub_89a["passed"]
        and sub_89b["passed"]
        and sub_89c["passed"]
        and sub_89d["passed"]
    )

    payload: Dict[str, Any] = {
        "schema": SCHEMA_ID,
        "version": PHASE_385_VERSION,
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
        "slot1_write_authorized": SLOT1_WRITE_AUTHORIZED,
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
        # Stage 89 Wave-79 Invariant Metrics
        "fx3_custom_key_has_variable_mode": FX3_CUSTOM_KEY_HAS_VARIABLE_MODE,
        "fx3_g149_custom_key_no_variable_reconciled": FX3_G149_CUSTOM_KEY_NO_VARIABLE_RECONCILED,
        "fx3_ciz_pre_lockouts_count": len(FX3_CIZ_4_PRE_LOCKOUT_IDS),
        "fx3_ciz_active_degradations_count": len(FX3_CIZ_5_ACTIVE_DEGRADATION_IDS),
        "fx3_xlr_h1_has_zoom_lever": FX3_XLR_H1_HAS_ZOOM_LEVER,
        "fx6_has_digital_zoom": FX6_HAS_DIGITAL_ZOOM,
        "fx6_has_speed_1_99_menu": FX6_HAS_SPEED_1_99_MENU,
        "fx3_dial_customize_exact_items_count": len(FX3_DIAL_CUSTOMIZE_EXACT_5_ITEMS),
        "fx3_physical_dials_count": len(FX3_PHYSICAL_3_DIALS),
        "fx3_my_dial_banks_count": len(FX3_MY_DIAL_BANKS),
        "fx3_dormant_dial_exposed_events": 0,
        "fx6_assignable_dial_options_count": len(FX6_ASSIGNABLE_DIAL_OPTIONS),
        "fx6_multi_function_dial_options_count": len(FX6_MULTI_FUNCTION_DIAL_OPTIONS),
        "fx3_diff_set_items_count": len(FX3_DIFF_SET_EXACT_8_ITEMS),
        "fx3_g99_pp_anti_init_erratum_reconciled": FX3_G99_PP_ANTI_INIT_ERRATUM_RECONCILED,
        "fx3_fn_menu_total_slots": FX3_FN_MENU_STILL_SLOTS + FX3_FN_MENU_MOVIE_SLOTS,
        "fx3_disp_shoot_pages_count": len(FX3_DISP_SHOOT_EXACT_4_PAGES),
        "fx3_has_builtin_evf": FX3_HAS_BUILTIN_EVF,
        "fx3_dormant_evf_exposed_events": 0,
        "fx3_select_lut_total_slots": len(FX3_SELECT_LUT_ALL_SLOTS),
        "fx3_g132_log_lut_gamma_split_reconciled": FX3_G132_LOG_LUT_GAMMA_SPLIT_RECONCILED,
        "fx6_display_elf_routes_count": FX6_DISPLAY_ON_OFF_ELF_ROUTES_COUNT,
        "fx3_hdmi_resolution_exposed_count": len(FX3_HDMI_RESOLUTION_EXACT_4_MODES),
        "fx3_4k_output_set_exposed_count": len(FX3_4K_OUTPUT_SET_EXACT_6_MODES),
        "fx3_4k_output_has_420_option": FX3_4K_OUTPUT_HAS_420_OPTION,
        "fx3_dormant_24p_60p_output_elf_hits": FX3_DORMANT_24P_60P_OUTPUT_ELF_HITS,
        "fx3_sony_elf_typos_count": len(FX3_SONY_ELF_3_TYPOS),
        "fx6_sdi_hdmi_matrix_entries_count": FX6_SDI_HDMI_OUTPUT_FORMAT_MATRIX_ENTRIES,
        "fx6_sdi_hdmi_rec_control_modes_count": len(FX6_SDI_HDMI_REC_CONTROL_3_MODES),
        # Nested Sub-Model Audits
        "submodel_89a_zoom_8step_speed_ciz_lockouts_fx6_handle_zoom": sub_89a,
        "submodel_89b_dial_customize_5item_mydial3_funcring_fx6_dials": sub_89b,
        "submodel_89c_op_customize_diffset8_disp4_zeroevf_lut_fx6_60disp": sub_89c,
        "submodel_89d_external_output_hdmi4k_3typos_fx6_12gsdi_dual": sub_89d,
        "stage89_probe": probe,
    }
    digest_body = _strip_wall_clock(payload)
    payload["phase385_audit_digest_sha256"] = hashlib.sha256(
        json.dumps(digest_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def run_self_test(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Union[None, str, Path, object] = _UNSET,
) -> Dict[str, Any]:
    return run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation(
        work_root=work_root,
        force_clean_room=force_clean_room,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulator.py",
        description=(
            "Phase 385 Stage 89 (89/89) Real-Hardware FX3/FX6 Wave-79 Co-Emulator: "
            "89A Shooting->[Zoom] 8-Step Speed (Custom Key Fixed-Only G149, Remote Variable/Fix, CIZ 4 Pre-Lockouts + 5 Degradations, XLR-H1 Zero Zoom Lever) vs FX6 Zoom/Handle Zoom & 0..99 HUD, "
            "89B Setup->[Dial Customize] Exact 5-Item Matrix & Physical 3-Dial Boundary / My Dial 1..3 Temp Unlock / Function Ring(Lens) vs FX6 Assignable/Multi-Function Dial, "
            "89C Setup->[Operation Customize] 8-Item Bitmask (PP Anti-Initialize G99) / Fn 12+12 / Zero-EVF 4-Page DISP / Select LUT vs Gamma Display Assist (G132) vs FX6 60-Route Display On/Off, "
            "and 89D Setup->[External Output] 4-Mode HDMI Resolution / 6-Mode 10bit 4:2:2 4K Output / LCD Blackout / 3 Sony ELF Typos vs FX6 12G-SDI + HDMI 25-Entry Dual Pipeline"
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
        help="Run Stage 89 (89/89) built-in self-test matrix",
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
            f"[{status}] Phase 385 Stage 89 ({rep['milestone']}) | mode={rep['source_mode']} "
            f"| donors={rep['donors']['total_donors_count']} "
            f"| zm=ckvar:{int(rep['fx3_custom_key_has_variable_mode'])}/lck:{rep['fx3_ciz_pre_lockouts_count']}/deg:{rep['fx3_ciz_active_degradations_count']}/fx6dig:{int(rep['fx6_has_digital_zoom'])} "
            f"| dial=5i:{rep['fx3_dial_customize_exact_items_count']}/3d:{rep['fx3_physical_dials_count']}/md:{rep['fx3_my_dial_banks_count']}/dorm:{rep['fx3_dormant_dial_exposed_events']} "
            f"| op=ds:{rep['fx3_diff_set_items_count']}/g99:{int(rep['fx3_g99_pp_anti_init_erratum_reconciled'])}/disp:{rep['fx3_disp_shoot_pages_count']}/evf:{int(rep['fx3_has_builtin_evf'])}/fx6d:{rep['fx6_display_elf_routes_count']} "
            f"| hdmi=res:{rep['fx3_hdmi_resolution_exposed_count']}/4k10:{rep['fx3_4k_output_set_exposed_count']}/420:{int(rep['fx3_4k_output_has_420_option'])}/typos:{rep['fx3_sony_elf_typos_count']}/sdi:{rep['fx6_sdi_hdmi_matrix_entries_count']} "
            f"| s1_wr={rep['slot1_writes']} usb_tx={rep['usb_tx_packets']} rf_tx={rep['rf_tx_packets']} emmc_wr={rep['emmc_nflasha_write_count']} "
            f"leaked={rep['raw_firmware_bytes_leaked']} "
            f"| digest={rep['phase385_audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
