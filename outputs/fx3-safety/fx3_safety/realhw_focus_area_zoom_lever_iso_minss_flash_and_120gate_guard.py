"""Phase 286 (120/120 Safety Gates Milestone!, Wave-50) Sony `ILME-FX3`
(`Ver. 7.02`, `ilc/2210`) vs `ILME-FX6` (`Ver. 6.01`) Safety Gates `G119`
(Complete `14`-Option `[Focus Area]` Hierarchy Still-Only `7` `Tracking:`
Entries vs Movie `Touch Tracking`, `[AF Area Registration]` / `[Focus Area Limit]`,
& `XLR-H1` Handle No-Zoom-Lever Myth-Bust + `[Zoom Lever Speed]` /
`[Remote Zoom Speed]` `1..8` vs `FX6` `0..99` Indicator) & `G120`
(`[ISO Range Limit]` / `[ISO AUTO Min. SS]` vs `Cine EI` Base-ISO Lockout &
Still-Only Mechanical-Shutter `[Flash Mode]` `< 250V` MI-Shoe Sync Guard vs
Movie `[Video Light Mode]`) + Unified `120`-Gate Master Safety Preflight
(`G01..G120`).

Operationalizes Wave-50 official Sony `ILME-FX3` (`Ver. 7.02`, Help Guide
`ilc/2210`) & `ILME-FX6` (`Ver. 6.01`) intelligence
(`reports/2026-11-17-global-sony-wave50-milestone-focus-area-zoom-lever-speed-iso-auto-minss-flash-intel/README.md`)
as deterministic offline preflight verifiers (`G119` and `G120`) and delegates
`G01..G118` directly to `evaluate_118gate_preflight()`.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    ENV_FORCE_CLEAN_ROOM,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_VERIFIED_SAFE,
    GateVerdict,
)
from .realhw_cfexpress_ufu_el3_and_52gate_guard import EL3_PAYLOAD_TRANSMIT_AUTHORIZED
from .realhw_dualmedia_bench_interlock_and_58gate_guard import (
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
)
from .realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard import (
    _DONOR_BLOB_CACHE,
)
from .realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import SPI_NOR_WRITE_AUTHORIZED
from .realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard import (
    Master118GateReport,
    evaluate_118gate_preflight,
)
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_FOCUS_AREA_ZOOM_LEVER_ISO_MINSS_FLASH_120GATE_SCHEMA: str = (
    "realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard_v1"
)
REALHW_FOCUS_AREA_ZOOM_LEVER_ISO_MINSS_FLASH_120GATE_VERSION: str = "1.0.0"

G119_GATE_ID: str = (
    "G119_focus_area_14opt_af_reg_xlrh1_no_zoom_lever_and_zoom_speed_guard"
)
G119_GATE_CODE: str = (
    "FOCUS_AREA_14OPT_AF_REG_XLRH1_NO_ZOOM_LEVER_AND_ZOOM_SPEED_GUARD"
)

G120_GATE_ID: str = (
    "G120_iso_range_minss_cine_ei_and_still_mechanical_flash_sync_guard"
)
G120_GATE_CODE: str = (
    "ISO_RANGE_MINSS_CINE_EI_AND_STILL_MECHANICAL_FLASH_SYNC_GUARD"
)

G119: str = G119_GATE_ID
G120: str = G120_GATE_ID
GATE_G119_FOCUS_AREA_14OPT_AF_REG_XLRH1_NO_ZOOM_LEVER_AND_ZOOM_SPEED_GUARD: str = (
    G119_GATE_CODE
)
GATE_G120_ISO_RANGE_MINSS_CINE_EI_AND_STILL_MECHANICAL_FLASH_SYNC_GUARD: str = (
    G120_GATE_CODE
)

ENV_CLEAN_ROOM_TEST_PHASE286: str = "FX3_CLEAN_ROOM_TEST"

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE286: float = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE286: float = 1.00

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX6_MODEL_NAME_PHASE286: str = "ILME-FX6"
FX3_DEFAULT_FW_VERSION_PHASE286: str = "7.02"
FX6_DEFAULT_FW_VERSION_PHASE286: str = "6.01"
FX3_HELP_GUIDE_CODE_PHASE286: str = "ilc/2210"

RESET_ACTION_NONE_PHASE286: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286: str = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE286: str = "Reset Network Set."
RESET_ACTION_INITIALIZE_PHASE286: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE286: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE286,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286,
    RESET_ACTION_RESET_NETWORK_SET_PHASE286,
    RESET_ACTION_INITIALIZE_PHASE286,
)

SHOOT_MODE_P_PHASE286: str = "P"
SHOOT_MODE_A_PHASE286: str = "A"
SHOOT_MODE_S_PHASE286: str = "S"
SHOOT_MODE_M_PHASE286: str = "M"
SHOOT_MODE_STILL_PASM_PHASE286: str = "Still"
SHOOT_MODE_INTELLIGENT_AUTO_PHASE286: str = "Intelligent Auto"
SHOOT_MODE_MOVIE_PHASE286: str = "Movie"
SHOOT_MODE_SQ_PHASE286: str = "S&Q"
PASM_SHOOT_MODES_PHASE286: Tuple[str, ...] = (
    SHOOT_MODE_P_PHASE286,
    SHOOT_MODE_A_PHASE286,
    SHOOT_MODE_S_PHASE286,
    SHOOT_MODE_M_PHASE286,
    SHOOT_MODE_STILL_PASM_PHASE286,
)
STILL_SHOOT_MODES_PHASE286: Tuple[str, ...] = PASM_SHOOT_MODES_PHASE286 + (
    SHOOT_MODE_INTELLIGENT_AUTO_PHASE286,
)
MOVIE_SHOOT_MODES_PHASE286: Tuple[str, ...] = (
    SHOOT_MODE_MOVIE_PHASE286,
    SHOOT_MODE_SQ_PHASE286,
)
ALLOWED_SHOOT_MODES_PHASE286: Tuple[str, ...] = (
    STILL_SHOOT_MODES_PHASE286 + MOVIE_SHOOT_MODES_PHASE286
)

# ---------------------------------------------------------------------------
# Status & Violation Codes (G119 / G120 / Phase 286)
# ---------------------------------------------------------------------------

STATUS_VERIFIED_G119: str = "VERIFIED_G119_FOCUS_AREA_AND_ZOOM_LEVER_SAFE"
STATUS_VERIFIED_G120: str = "VERIFIED_G120_ISO_MINSS_AND_FLASH_SYNC_SAFE"
STATUS_BLOCKED_PHASE286_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE286_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G119_MOVIE_TRACKING_FOCUS_AREA_VIOLATION: str = (
    "BLOCKED_G119_MOVIE_TRACKING_FOCUS_AREA_VIOLATION"
)
STATUS_BLOCKED_G119_FOCUS_AREA_LIMIT_OR_AF_REG_VIOLATION: str = (
    "BLOCKED_G119_FOCUS_AREA_LIMIT_OR_AF_REG_VIOLATION"
)
STATUS_BLOCKED_G119_XLRH1_FAKE_HANDLE_ZOOM_SPOOF_VIOLATION: str = (
    "BLOCKED_G119_XLRH1_FAKE_HANDLE_ZOOM_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G119_ZOOM_RANGE_OR_SPEED_BOUNDARY_VIOLATION: str = (
    "BLOCKED_G119_ZOOM_RANGE_OR_SPEED_BOUNDARY_VIOLATION"
)
STATUS_BLOCKED_G119_TELEMETRY_INVALID: str = (
    "BLOCKED_G119_FOCUS_AREA_ZOOM_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G120_ISO_MINSS_MOVIE_OR_CINE_EI_VIOLATION: str = (
    "BLOCKED_G120_ISO_MINSS_MOVIE_OR_CINE_EI_VIOLATION"
)
STATUS_BLOCKED_G120_ISO_RANGE_OR_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G120_ISO_RANGE_OR_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G120_FLASH_MOVIE_ESHUTTER_OR_HV_SHOE_VIOLATION: str = (
    "BLOCKED_G120_FLASH_MOVIE_ESHUTTER_OR_HV_SHOE_VIOLATION"
)
STATUS_BLOCKED_G120_VIDEO_LIGHT_OR_FLASH_COMP_VIOLATION: str = (
    "BLOCKED_G120_VIDEO_LIGHT_OR_FLASH_COMP_VIOLATION"
)
STATUS_BLOCKED_G120_TELEMETRY_INVALID: str = (
    "BLOCKED_G120_ISO_MINSS_FLASH_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G119 Constants: 14-Option [Focus Area], AF Area Registration & Zoom
# ---------------------------------------------------------------------------

FOCUS_AREA_MENU_PATH_G119: str = "MENU -> (Focus) -> [Focus Area] -> [Focus Area]"
FOCUS_AREA_LIMIT_MENU_PATH_G119: str = (
    "MENU -> (Focus) -> [Focus Area] -> [Focus Area Limit]"
)
AF_AREA_REG_MENU_PATH_G119: str = (
    "MENU -> (Focus) -> [Focus Area] -> [AF Area Registration]"
)
ZOOM_MENU_PATH_G119: str = "MENU -> Shooting -> [Zoom]"
ZOOM_LEVER_SPEED_MENU_PATH_G119: str = (
    "MENU -> Shooting -> [Zoom] -> [Zoom Lever Speed]"
)
REMOTE_ZOOM_SPEED_MENU_PATH_G119: str = (
    "MENU -> Shooting -> [Zoom] -> [Remote Zoom Speed]"
)

FOCUS_AREA_UXC_RESID16_G119: int = 0xE0AD
FOCUS_AREA_LIMIT_UXC_RESID16_G119: int = 0x6DE2
FOCUS_AREA_LIMIT_MIN2_HINT_RESID16_G119: int = 0xE227
FOCUS_AREA_COLOR_UXC_RESID16_G119: int = 0x6AF1
CIRC_FOCUS_POINT_UXC_RESID16_G119: int = 0x74F6
AF_AREA_REG_UXC_RESID16_G119: int = 0x6B65
DEL_REGIST_AF_AREA_UXC_RESID16_G119: int = 0x696C
ZOOM_LEVER_SPEED_UXC_RESID16_G119: int = 0x6304
CUSTOM_KEY_Z_SPEED_UXC_RESID16_G119: int = 0x78E8
REMOTE_ZOOM_SPEED_UXC_RESID16_G119: int = 0x7128
ZOOM_RANGE_UXC_RESID16_G119: int = 0x7164
FX6_ZOOM_POSITION_DISPLAY_UXC_RESID16_G119: int = 0x22CE

FOCUS_AREA_WIDE_G119: str = "Wide"
FOCUS_AREA_ZONE_G119: str = "Zone"
FOCUS_AREA_CENTER_FIX_G119: str = "Center Fix"
FOCUS_AREA_SPOT_S_G119: str = "Spot: S"
FOCUS_AREA_SPOT_M_G119: str = "Spot: M"
FOCUS_AREA_SPOT_L_G119: str = "Spot: L"
FOCUS_AREA_EXPAND_SPOT_G119: str = "Expand Spot"
FOCUS_AREA_TRACKING_WIDE_G119: str = "Tracking: Wide"
FOCUS_AREA_TRACKING_ZONE_G119: str = "Tracking: Zone"
FOCUS_AREA_TRACKING_CENTER_FIX_G119: str = "Tracking: Center Fix"
FOCUS_AREA_TRACKING_SPOT_S_G119: str = "Tracking: Spot S"
FOCUS_AREA_TRACKING_SPOT_M_G119: str = "Tracking: Spot M"
FOCUS_AREA_TRACKING_SPOT_L_G119: str = "Tracking: Spot L"
FOCUS_AREA_TRACKING_EXPAND_SPOT_G119: str = "Tracking: Expand Spot"

FX3_SHARED_7_FOCUS_AREAS_G119: Tuple[str, ...] = (
    FOCUS_AREA_WIDE_G119,
    FOCUS_AREA_ZONE_G119,
    FOCUS_AREA_CENTER_FIX_G119,
    FOCUS_AREA_SPOT_S_G119,
    FOCUS_AREA_SPOT_M_G119,
    FOCUS_AREA_SPOT_L_G119,
    FOCUS_AREA_EXPAND_SPOT_G119,
)
FX3_STILL_ONLY_7_TRACKING_FOCUS_AREAS_G119: Tuple[str, ...] = (
    FOCUS_AREA_TRACKING_WIDE_G119,
    FOCUS_AREA_TRACKING_ZONE_G119,
    FOCUS_AREA_TRACKING_CENTER_FIX_G119,
    FOCUS_AREA_TRACKING_SPOT_S_G119,
    FOCUS_AREA_TRACKING_SPOT_M_G119,
    FOCUS_AREA_TRACKING_SPOT_L_G119,
    FOCUS_AREA_TRACKING_EXPAND_SPOT_G119,
)
FX3_EXACT_14_FOCUS_AREAS_G119: Tuple[str, ...] = (
    FX3_SHARED_7_FOCUS_AREAS_G119 + FX3_STILL_ONLY_7_TRACKING_FOCUS_AREAS_G119
)
FX6_EXACT_3_FOCUS_AREAS_G119: Tuple[str, ...] = (
    "Wide",
    "Zone",
    "Flexible Spot",
)
FOCUS_AREA_FACTORY_DEFAULT_G119: str = FOCUS_AREA_WIDE_G119
MOVIE_TRACKING_MECHANISM_G119: str = "Touch Tracking"
MIN_FOCUS_AREA_LIMIT_COUNT_G119: int = 2

FOCUS_AREA_COLOR_WHITE_G119: str = "White"
FOCUS_AREA_COLOR_RED_G119: str = "Red"
ALLOWED_FOCUS_AREA_COLORS_G119: Tuple[str, ...] = (
    FOCUS_AREA_COLOR_WHITE_G119,
    FOCUS_AREA_COLOR_RED_G119,
)
FOCUS_AREA_COLOR_FACTORY_DEFAULT_G119: str = FOCUS_AREA_COLOR_WHITE_G119

CIRC_DOES_NOT_CIRCULATE_G119: str = "Does Not Circulate"
CIRC_CIRCULATE_G119: str = "Circulate"
ALLOWED_CIRC_FOCUS_POINT_MODES_G119: Tuple[str, ...] = (
    CIRC_DOES_NOT_CIRCULATE_G119,
    CIRC_CIRCULATE_G119,
)
CIRC_FOCUS_POINT_DEFAULT_G119: str = CIRC_DOES_NOT_CIRCULATE_G119
CIRCULATING_FOCUS_AREAS_G119: Tuple[str, ...] = (
    FOCUS_AREA_ZONE_G119,
    FOCUS_AREA_SPOT_S_G119,
    FOCUS_AREA_SPOT_M_G119,
    FOCUS_AREA_SPOT_L_G119,
    FOCUS_AREA_EXPAND_SPOT_G119,
    FOCUS_AREA_TRACKING_ZONE_G119,
    FOCUS_AREA_TRACKING_SPOT_S_G119,
    FOCUS_AREA_TRACKING_SPOT_M_G119,
    FOCUS_AREA_TRACKING_SPOT_L_G119,
    FOCUS_AREA_TRACKING_EXPAND_SPOT_G119,
)

SWITCH_VH_OFF_G119: str = "Off"
SWITCH_VH_AF_POINT_ONLY_G119: str = "AF Point Only"
SWITCH_VH_AF_POINT_PLUS_AREA_G119: str = "AF Point + AF Area"
ALLOWED_SWITCH_VH_MODES_G119: Tuple[str, ...] = (
    SWITCH_VH_OFF_G119,
    SWITCH_VH_AF_POINT_ONLY_G119,
    SWITCH_VH_AF_POINT_PLUS_AREA_G119,
)

AF_FOCUS_MODE_AF_S_G119: str = "AF-S"
AF_FOCUS_MODE_AF_A_G119: str = "AF-A"
AF_FOCUS_MODE_AF_C_G119: str = "AF-C"
AF_FOCUS_MODE_DMF_G119: str = "DMF"
AF_FOCUS_MODE_MF_G119: str = "MF"
ALLOWED_FOCUS_MODES_G119: Tuple[str, ...] = (
    AF_FOCUS_MODE_AF_S_G119,
    AF_FOCUS_MODE_AF_A_G119,
    AF_FOCUS_MODE_AF_C_G119,
    AF_FOCUS_MODE_DMF_G119,
    AF_FOCUS_MODE_MF_G119,
)

ZOOM_RANGE_OPTICAL_ONLY_G119: str = "Optical zoom only"
ZOOM_RANGE_CLEAR_IMAGE_G119: str = "ClearImage Zoom"
ZOOM_RANGE_DIGITAL_G119: str = "Digital Zoom"
ALLOWED_ZOOM_RANGES_G119: Tuple[str, ...] = (
    ZOOM_RANGE_OPTICAL_ONLY_G119,
    ZOOM_RANGE_CLEAR_IMAGE_G119,
    ZOOM_RANGE_DIGITAL_G119,
)
ZOOM_RANGE_FACTORY_DEFAULT_G119: str = ZOOM_RANGE_OPTICAL_ONLY_G119

ZOOM_SPEED_MIN_G119: int = 1
ZOOM_SPEED_MAX_G119: int = 8
ZOOM_LEVER_1ST_DEFAULT_G119: int = 3
ZOOM_LEVER_2ND_DEFAULT_G119: int = 8
CUSTOM_KEY_Z_SPEED_DEFAULT_G119: int = 3
REMOTE_ZOOM_SPEED_TYPE_VARIABLE_G119: str = "Variable"
REMOTE_ZOOM_SPEED_TYPE_FIXED_G119: str = "Fixed"
ALLOWED_REMOTE_ZOOM_SPEED_TYPES_G119: Tuple[str, ...] = (
    REMOTE_ZOOM_SPEED_TYPE_VARIABLE_G119,
    REMOTE_ZOOM_SPEED_TYPE_FIXED_G119,
)
REMOTE_ZOOM_SPEED_TYPE_DEFAULT_G119: str = REMOTE_ZOOM_SPEED_TYPE_VARIABLE_G119
REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G119: int = 3

FX3_XLR_H1_HAS_ZOOM_LEVER_G119: bool = False
FX3_XLR_H1_HAS_REC_BUTTON_G119: bool = False
FX3_XLR_H1_HAS_ZOOM_HOLD_SWITCH_G119: bool = False
FX6_HANDLE_ZOOM_MODES_G119: Tuple[str, ...] = ("Off", "Low", "High", "Variable")
FX6_HANDLE_HOLD_MODES_G119: Tuple[str, ...] = ("Normal", "Rec Button Only")
FX6_ZOOM_POSITION_DISPLAY_RANGE_G119: Tuple[int, int] = (0, 99)

# ---------------------------------------------------------------------------
# Gate G120 Constants: [ISO Range Limit], [ISO AUTO Min. SS], Flash & Video Light
# ---------------------------------------------------------------------------

ISO_RANGE_LIMIT_MENU_PATH_G120: str = (
    "MENU -> (Exposure/Color) -> [Exposure] -> [ISO Range Limit]"
)
ISO_AUTO_MIN_SS_MENU_PATH_G120: str = (
    "MENU -> (Exposure/Color) -> [Exposure] -> [ISO AUTO Min. SS]"
)
FLASH_MODE_MENU_PATH_G120: str = (
    "MENU -> (Exposure/Color) -> [Flash] -> [Flash Mode]"
)
VIDEO_LIGHT_MODE_MENU_PATH_G120: str = (
    "MENU -> Setup -> [Setup Option] -> [Video Light Mode]"
)

ISO_RANGE_LIMIT_UXC_RESID16_G120: int = 0x72F8
ISO_AUTO_MIN_UXC_RESID16_G120: int = 0xE88C
ISO_AUTO_MAX_UXC_RESID16_G120: int = 0xE69B
ISO_AUTO_MIN_SS_UXC_RESID16_G120: int = 0x778B
FLASH_MODE_UXC_RESID16_G120: int = 0xE5CE
FLASH_COMP_UXC_RESID16_G120: int = 0xE5D3
EXP_COMP_SET_UXC_RESID16_G120: int = 0xE11A
WIRELESS_FLASH_UXC_RESID16_G120: int = 0x6201
RED_EYE_REDUCTION_UXC_RESID16_G120: int = 0x7AC9
EXTERNAL_FLASH_SET_UXC_RESID16_G120: int = 0x6771
VIDEO_LIGHT_MODE_UXC_RESID16_G120: int = 0x6211
FX6_FLASH_BAND_REDUCE_UXC_RESID16_G120: int = 0x4215

ISO_HARDWARE_MIN_G120: int = 50
ISO_HARDWARE_MAX_G120: int = 409600
ISO_DEFAULT_STILL_MIN_G120: int = 80
ISO_DEFAULT_STILL_MAX_G120: int = 102400
CINE_EI_BASE_ISOS_G120: Tuple[int, int] = (800, 12800)

LOG_SHOOTING_OFF_G120: str = "Off"
LOG_SHOOTING_FLEXIBLE_ISO_G120: str = "Flexible ISO"
LOG_SHOOTING_CINE_EI_QUICK_G120: str = "Cine EI Quick"
LOG_SHOOTING_CINE_EI_G120: str = "Cine EI"
ALLOWED_LOG_SHOOTING_MODES_G120: Tuple[str, ...] = (
    LOG_SHOOTING_OFF_G120,
    LOG_SHOOTING_FLEXIBLE_ISO_G120,
    LOG_SHOOTING_CINE_EI_QUICK_G120,
    LOG_SHOOTING_CINE_EI_G120,
)
CINE_EI_LOCKED_LOG_MODES_G120: Tuple[str, ...] = (
    LOG_SHOOTING_CINE_EI_QUICK_G120,
    LOG_SHOOTING_CINE_EI_G120,
)

ISO_AUTO_MIN_SS_SLOWER_G120: str = "Slower"
ISO_AUTO_MIN_SS_SLOW_G120: str = "Slow"
ISO_AUTO_MIN_SS_STANDARD_G120: str = "Standard"
ISO_AUTO_MIN_SS_FAST_G120: str = "Fast"
ISO_AUTO_MIN_SS_FASTER_G120: str = "Faster"
ISO_AUTO_MIN_SS_RELATIVE_PRESETS_G120: Tuple[str, ...] = (
    ISO_AUTO_MIN_SS_SLOWER_G120,
    ISO_AUTO_MIN_SS_SLOW_G120,
    ISO_AUTO_MIN_SS_STANDARD_G120,
    ISO_AUTO_MIN_SS_FAST_G120,
    ISO_AUTO_MIN_SS_FASTER_G120,
)
ISO_AUTO_MIN_SS_MANUAL_SHUTTER_TOKENS_G120: Tuple[str, ...] = (
    "1/8000",
    "1/4000",
    "1/2000",
    "1/1000",
    "1/500",
    "1/250",
    "1/125",
    "1/60",
    "1/30",
    "1/15",
    "1/8",
    "1/4",
    "1/2",
    '1"',
    '2"',
    '4"',
    '8"',
    '15"',
    '30"',
)
ISO_AUTO_MIN_SS_FACTORY_DEFAULT_G120: str = ISO_AUTO_MIN_SS_STANDARD_G120
ISO_AUTO_MIN_SS_ELIGIBLE_MODES_G120: Tuple[str, ...] = (
    SHOOT_MODE_P_PHASE286,
    SHOOT_MODE_A_PHASE286,
)

FLASH_MODE_AUTOFLASH_G120: str = "Autoflash"
FLASH_MODE_FILL_FLASH_G120: str = "Fill-flash"
FLASH_MODE_SLOW_SYNC_G120: str = "Slow Sync."
FLASH_MODE_REAR_SYNC_G120: str = "Rear Sync."
FLASH_MODE_FLASH_OFF_G120: str = "Flash Off"
FX3_EXACT_5_FLASH_MODES_G120: Tuple[str, ...] = (
    FLASH_MODE_AUTOFLASH_G120,
    FLASH_MODE_FILL_FLASH_G120,
    FLASH_MODE_SLOW_SYNC_G120,
    FLASH_MODE_REAR_SYNC_G120,
    FLASH_MODE_FLASH_OFF_G120,
)
FLASH_MODE_FACTORY_DEFAULT_G120: str = FLASH_MODE_AUTOFLASH_G120

FLASH_COMP_MIN_EV_G120: float = -3.0
FLASH_COMP_MAX_EV_G120: float = 3.0
FLASH_COMP_STEP_EV_G120: float = 1.0 / 3.0

EXP_COMP_SET_AMBIENT_AND_FLASH_G120: str = "Ambient&flash"
EXP_COMP_SET_AMBIENT_ONLY_G120: str = "Ambient only"
ALLOWED_EXP_COMP_SET_MODES_G120: Tuple[str, ...] = (
    EXP_COMP_SET_AMBIENT_AND_FLASH_G120,
    EXP_COMP_SET_AMBIENT_ONLY_G120,
)
EXP_COMP_SET_FACTORY_DEFAULT_G120: str = EXP_COMP_SET_AMBIENT_AND_FLASH_G120

SHUTTER_TYPE_MECHANICAL_G120: str = "Mechanical Shutter"
SHUTTER_TYPE_ELECTRONIC_G120: str = "Electronic Shutter"
FX3_FLASH_SYNC_CEILING_DENOM_G120: int = 250
FX3_FLASH_SYNC_CEILING_SECONDS_G120: float = 1.0 / 250.0
FX3_MI_SHOE_MAX_SAFE_SYNC_VOLTAGE_V_G120: float = 250.0

VIDEO_LIGHT_POWER_LINK_G120: str = "Power Link"
VIDEO_LIGHT_REC_LINK_G120: str = "REC Link"
VIDEO_LIGHT_REC_LINK_STBY_G120: str = "REC Link&STBY"
VIDEO_LIGHT_AUTO_G120: str = "Auto"
FX3_EXACT_4_VIDEO_LIGHT_MODES_G120: Tuple[str, ...] = (
    VIDEO_LIGHT_POWER_LINK_G120,
    VIDEO_LIGHT_REC_LINK_G120,
    VIDEO_LIGHT_REC_LINK_STBY_G120,
    VIDEO_LIGHT_AUTO_G120,
)
VIDEO_LIGHT_FACTORY_DEFAULT_G120: str = VIDEO_LIGHT_POWER_LINK_G120

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, Targeted Pread on appFw.so, <0.20s)
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE286: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (62_689_668, b"BKID_APP_setting_autofocus_area_contrast_detect_af"),
    (60_921_500, b"AUTOFOCUS_AREA_CONTRAST_DETECT_AF_WIDE"),
    (60_921_601, b"AUTOFOCUS_AREA_CONTRAST_DETECT_AF_ZONE"),
    (60_921_702, b"AUTOFOCUS_AREA_CONTRAST_DETECT_AF_CENTER"),
    (62_654_365, b"BKID_APP_focus_area_limit_wide"),
    (62_689_773, b"BKID_APP_setting_vertical_horizontal_focus_area_switch"),
    (62_689_886, b"BKID_APP_setting_focus_frame_color"),
    (62_690_314, b"BKID_APP_setting_circulate_of_focus_point"),
    (62_689_959, b"BKID_APP_setting_register_the_af_frame"),
    (62_682_428, b"BKID_APP_setting_zoom_setting"),
    (62_682_550, b"BKID_APP_setting_1st_zoom_spd_stby"),
    (62_682_767, b"BKID_APP_setting_2nd_zoom_spd_rec"),
    (62_682_838, b"BKID_APP_setting_fixed_zoom_speed_stby"),
    (62_682_998, b"BKID_APP_setting_fixed_zoom_speed_type"),
    (62_683_116, b"BKID_APP_setting_remote_fixed_zoom_speed_stby"),
    (62_844_362, b"BKID_APP_setting_iso_range_limit_min"),
    (62_844_107, b"BKID_APP_setting_iso_range_limit_max"),
    (62_685_366, b"BKID_APP_setting_iso_auto_min_s_s"),
    (62_687_318, b"BKID_APP_setting_flash_mode"),
    (61_565_186, b"VAL_HAITA_setting_flash_mode_exposure_mode_"),
    (62_687_377, b"BKID_APP_setting_flash_compensation"),
    (62_687_452, b"BKID_APP_setting_exp_comp_set"),
    (62_687_515, b"BKID_APP_setting_wireless_flash"),
    (62_687_793, b"BKID_APP_setting_red_eye_reduction"),
    (62_702_222, b"BKID_APP_setting_video_light_set"),
    (49_971_995, b"VIDEO_LIGHT_SET_POWER_LINK"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE286: str = (
    "0bb1ce50139e29786603af8aad6810ae9ed12aa3914fd6475c2805655a621659"
)

PINNED_FX6_APPFW_SLICES_PHASE286: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (40_946_149, b"BKID_APP_SETTING_HANDLE_ZOOM"),
    (40_946_178, b"BKID_APP_SETTING_HANDLE_ZOOM_HIGH"),
    (40_946_212, b"BKID_APP_SETTING_HANDLE_ZOOM_LOW"),
    (40_945_993, b"BKID_APP_SETTING_HOLD_SWITCH_SETTING_HANDLE_HOLD_SWITCH"),
    (40_940_241, b"BKID_APP_SETTING_ZOOM_POSITION_DISPLAY"),
    (40_930_060, b"BKID_APP_SETTING_FOCUS_AREA_AF_S"),
    (40_922_015, b"BKID_APP_SETTING_BASE_ISO"),
    (41_748_974, b"PRODUCT_MODEL_CHAPLIN"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE286: str = (
    "b303cf26ccd7e44c6b3b8405badf89f833d36a9eccc9759fd13a233cd791f624"
)

PINNED_PHASE286_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE286,
        tuple(tok for _off, tok in PINNED_FX3_APPFW_SLICES_PHASE286),
        "FX3_APPFW_WAVE50_FOCUS_AREA_ZOOM_ISO_FLASH_SLICES",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Spot: S",
            b"Spot: M",
            b"Spot: L",
            b"Expand Spot",
            b"Center Fix",
            b"Tracking: Wide",
            b"Tracking: Zone",
            b"Tracking: Center Fix",
            b"Tracking: Spot S",
            b"Tracking: Expand Spot",
            b"Focus Area Limit",
            b"Switch V/H AF Area",
            b"Focus Area Color",
            b"Circ. of Focus Point",
            b"AF Area Registration",
            b"Del. Regist. AF Area",
            b"Zoom Range",
            b"Zoom Lever Speed",
            b"Custom Key Z. Speed",
            b"Remote Zoom Speed",
            b"ISO Range Limit",
            b"ISO AUTO Min. SS",
            b"External Flash Set.",
            b"Video Light Mode",
            b"FEL Lock hold",
        ),
        "FX3_UXC_F_FOCUS_AREA_ZOOM_ISO_FLASH_STRINGS",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (b"AF", b"ISO AUTO", "对焦区域限制".encode("utf-8"), "变焦杆速度".encode("utf-8")),
        "FX3_UXC_F_ZHCN_WAVE50_RESID16_PARITY",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (b"AF", b"ISO AUTO", "對焦區域限制".encode("utf-8"), "變焦控制桿速度".encode("utf-8")),
        "FX3_UXC_F_ZHTW_WAVE50_RESID16_PARITY",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (b"AF", b"ISO AUTO", "ﾌｫｰｶｽｴﾘｱ限定".encode("utf-8"), "ｽﾞｰﾑﾚﾊﾞｰｽﾋﾟｰﾄﾞ".encode("utf-8")),
        "FX3_UXC_F_JA_WAVE50_RESID16_PARITY",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Focus Area",
            b"Wide",
            b"Zone",
            b"ISO AUTO Min",
            b"ISO AUTO Max",
            b"Flash Mode",
            b"Autoflash",
            b"Flash Off",
            b"Slow Sync.",
            b"Fill-flash",
            b"Rear Sync.",
            b"Flash Comp.",
            b"Exp.comp.set",
            b"White",
            b"Red",
        ),
        "FX3_UXC_FOCUS_ISO_FLASH_STRINGS",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (b"Focus Area", b"Zoom", b"Flash"),
        "FX3_UXC_G_FOCUS_AREA_ZOOM_FLASH",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4\x00", b"ILME-FX3"),
        "FX3_BK4_ALLLANG_SEED_BASELINE",
    ),
    "fx6_appfw_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
        50_520_424,
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE286,
        tuple(tok for _off, tok in PINNED_FX6_APPFW_SLICES_PHASE286),
        "FX6_APPFW_WAVE50_SMART_HANDLE_ZOOM_POSITION_SLICES",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"Handle Zoom",
            b"Handle HOLD Switch",
            b"Rec Button Only",
            b"Zoom Position Display",
            b"Focus Area (AF-S)",
        ),
        "FX6_UXC_HANDLE_ZOOM_POSITION_FOCUS_AREA",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"Handle Zoom",
            b"HOLD Switch Setting",
            b"Flexible Spot",
            b"Focus Area (Push AF)",
            b"Flash Band Reduce",
        ),
        "FX6_UXC_2_HANDLE_ZOOM_HOLD_FLASH_BAND_REDUCE",
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase286DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    elapsed_seconds: float
    within_budget_200ms: bool
    raw_firmware_bytes_leaked: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    fx6_contracts_verified: bool
    four_lang_resid16_parity_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FocusAreaZoomLeverGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    reset_action: str
    focus_area_menu_path: str
    focus_area_limit_menu_path: str
    af_area_reg_menu_path: str
    zoom_menu_path: str
    zoom_lever_speed_menu_path: str
    remote_zoom_speed_menu_path: str
    shoot_mode: str
    focus_mode: str
    fx3_exact_14_focus_areas: Tuple[str, ...]
    fx3_shared_7_focus_areas: Tuple[str, ...]
    fx3_still_only_7_tracking_focus_areas: Tuple[str, ...]
    movie_tracking_mechanism: str
    requested_focus_area: str
    effective_focus_area: str
    focus_area_limit_enabled_count: int
    focus_area_color: str
    focus_area_color_survived_cam_reset: bool
    circ_of_focus_point: str
    switch_vh_af_area: str
    requested_af_area_registration: str
    effective_af_area_registration: str
    af_area_reg_survived_cam_reset: bool
    lock_operation_parts_forced_off: bool
    xlr_h1_has_zoom_lever: bool
    xlr_h1_has_rec_button: bool
    xlr_h1_has_zoom_hold_switch: bool
    requested_zoom_range: str
    effective_zoom_range: str
    zoom_range_survived_cam_reset: bool
    clear_digital_zoom_available: bool
    zoom_lever_1st_speed_stby: int
    zoom_lever_1st_speed_rec: int
    zoom_lever_2nd_speed_stby: int
    zoom_lever_2nd_speed_rec: int
    custom_key_z_speed_stby: int
    custom_key_z_speed_rec: int
    remote_zoom_speed_type: str
    remote_zoom_fixed_speed_stby: int
    remote_zoom_fixed_speed_rec: int
    fx6_zoom_position_display_range: Tuple[int, int]
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G119FocusAreaZoomLeverGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    focus_area_zoom_lever_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IsoMinSsFlashGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    reset_action: str
    iso_range_limit_menu_path: str
    iso_auto_min_ss_menu_path: str
    flash_mode_menu_path: str
    video_light_mode_menu_path: str
    shoot_mode: str
    log_shooting: str
    effective_iso_range_min: int
    effective_iso_range_max: int
    iso_range_limit_survived_cam_reset: bool
    cine_ei_base_iso_pinned: bool
    effective_base_iso: Optional[int]
    requested_iso_auto_min_ss: str
    effective_iso_auto_min_ss: str
    iso_auto_min_ss_active: bool
    shutter_type: str
    silent_mode: str
    flash_requested: bool
    requested_flash_mode: str
    effective_flash_mode: str
    flash_available: bool
    flash_comp_ev: float
    effective_exp_comp_set: str
    exp_comp_set_survived_cam_reset: bool
    wireless_flash: str
    red_eye_reduction: str
    mi_shoe_trigger_voltage_v: float
    mi_shoe_positive_polarity: bool
    fx3_flash_sync_ceiling_denom: int
    shutter_speed_seconds: float
    requested_video_light_mode: str
    effective_video_light_mode: str
    video_light_active_across_still_movie_sq: bool
    fx6_still_flash_supported: bool
    fx6_flash_band_reduce_supported: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G120IsoMinSsFlashGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    iso_minss_flash_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master120GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_117_gates_verified: bool
    all_120_gates_verified: bool
    g13_to_g120_all_passed: bool
    g119_to_g120_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_118_report: Dict[str, Any]
    g119_result: Dict[str, Any]
    g120_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers & Normalization
# ---------------------------------------------------------------------------

_TRUTHY_CLEAN_ROOM_TOKENS: Tuple[str, ...] = ("1", "true", "TRUE", "yes", "YES")


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE286):
        if os.environ.get(env_key, "").strip() in _TRUTHY_CLEAN_ROOM_TOKENS:
            return True
    return False


def _default_donor_budget_seconds_phase286() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return DONOR_CHECK_CI_MAX_SECONDS_PHASE286
    return DONOR_CHECK_MAX_SECONDS_PHASE286


def _read_file_o_rdonly(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    fd = os.open(str(path), flags)
    chunks: List[bytes] = []
    try:
        while True:
            buf = os.read(fd, 1 << 20)
            if not buf:
                break
            chunks.append(buf)
    finally:
        os.close(fd)
    return b"".join(chunks)


def _read_targeted_slices_o_rdonly(
    path: Path, slices_spec: Sequence[Tuple[int, bytes]]
) -> Tuple[int, str, bool]:
    """Read targeted byte slices via `os.open(..., os.O_RDONLY)` + `os.pread`
    so large shared `appFw.so` binaries are audited in < 1 ms without full hashing.
    """
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    fd = os.open(str(path), flags)
    try:
        st = os.fstat(fd)
        file_size = int(st.st_size)
        chunks: List[bytes] = []
        all_matched = True
        pread_fn = getattr(os, "pread", None)
        for offset, token in slices_spec:
            if offset + len(token) > file_size:
                all_matched = False
                chunks.append(b"")
                continue
            if pread_fn is not None:
                chunk = pread_fn(fd, len(token), offset)
            else:
                os.lseek(fd, offset, os.SEEK_SET)
                chunk = os.read(fd, len(token))
            chunks.append(chunk)
            if chunk != token:
                all_matched = False
        slice_sha = hashlib.sha256(b"".join(chunks)).hexdigest()
        return file_size, slice_sha, all_matched
    finally:
        os.close(fd)


def _read_cached_donor_o_rdonly(path: Path) -> Tuple[int, str, bytes]:
    key = str(path.resolve())
    st = os.stat(key)
    cached = _DONOR_BLOB_CACHE.get(key)
    if cached is not None and cached[0] == st.st_size and cached[1] == st.st_mtime:
        return cached[2], cached[3], cached[4]
    blob = _read_file_o_rdonly(path)
    sha = hashlib.sha256(blob).hexdigest()
    _DONOR_BLOB_CACHE[key] = (st.st_size, st.st_mtime, len(blob), sha, blob)
    return len(blob), sha, blob


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _is_real_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _is_real_number(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def _norm_reset_action_phase286(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE_PHASE286
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE286
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE_PHASE286
    return None


def _norm_shoot_mode_phase286(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "P": SHOOT_MODE_P_PHASE286,
        "A": SHOOT_MODE_A_PHASE286,
        "S": SHOOT_MODE_S_PHASE286,
        "M": SHOOT_MODE_M_PHASE286,
        "STILL": SHOOT_MODE_STILL_PASM_PHASE286,
        "INTELLIGENT AUTO": SHOOT_MODE_INTELLIGENT_AUTO_PHASE286,
        "IAUTO": SHOOT_MODE_INTELLIGENT_AUTO_PHASE286,
        "MOVIE": SHOOT_MODE_MOVIE_PHASE286,
        "S&Q": SHOOT_MODE_SQ_PHASE286,
        "SQ": SHOOT_MODE_SQ_PHASE286,
    }
    return mapping.get(u)


def _norm_on_off_phase286(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "ON":
        return "On"
    if u == "OFF":
        return "Off"
    return None


def _norm_focus_area_g119(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in FX3_EXACT_14_FOCUS_AREAS_G119:
        if u == item.upper():
            return item
    aliases = {
        "TRACKING: SPOT: S": FOCUS_AREA_TRACKING_SPOT_S_G119,
        "TRACKING: SPOT: M": FOCUS_AREA_TRACKING_SPOT_M_G119,
        "TRACKING: SPOT: L": FOCUS_AREA_TRACKING_SPOT_L_G119,
    }
    return aliases.get(u)


def _norm_focus_mode_g119(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    for item in ALLOWED_FOCUS_MODES_G119:
        if u == item.upper():
            return item
    return None


def _norm_focus_area_color_g119(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    for item in ALLOWED_FOCUS_AREA_COLORS_G119:
        if u == item.upper():
            return item
    return None


def _norm_circ_focus_point_g119(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_CIRC_FOCUS_POINT_MODES_G119:
        if u == item.upper():
            return item
    return None


def _norm_switch_vh_g119(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_SWITCH_VH_MODES_G119:
        if u == item.upper():
            return item
    return None


def _norm_zoom_range_g119(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_ZOOM_RANGES_G119:
        if u == item.upper():
            return item
    if u == "CLEAR IMAGE ZOOM":
        return ZOOM_RANGE_CLEAR_IMAGE_G119
    return None


def _norm_remote_zoom_speed_type_g119(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    for item in ALLOWED_REMOTE_ZOOM_SPEED_TYPES_G119:
        if u == item.upper():
            return item
    return None


def _norm_log_shooting_g120(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_LOG_SHOOTING_MODES_G120:
        if u == item.upper():
            return item
    return None


def _norm_iso_auto_min_ss_g120(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]")
    u = s.upper()
    if u == "STD":
        return ISO_AUTO_MIN_SS_STANDARD_G120
    for item in ISO_AUTO_MIN_SS_RELATIVE_PRESETS_G120:
        if u == item.upper():
            return item
    if s in ISO_AUTO_MIN_SS_MANUAL_SHUTTER_TOKENS_G120:
        return s
    return None


def _norm_shutter_type_g120(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("MECHANICAL SHUTTER", "MECHANICAL"):
        return SHUTTER_TYPE_MECHANICAL_G120
    if u in ("ELECTRONIC SHUTTER", "ELECTRONIC"):
        return SHUTTER_TYPE_ELECTRONIC_G120
    return None


def _norm_flash_mode_g120(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in FX3_EXACT_5_FLASH_MODES_G120:
        if u == item.upper():
            return item
    return None


def _norm_exp_comp_set_g120(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_EXP_COMP_SET_MODES_G120:
        if u == item.upper():
            return item
    return None


def _norm_video_light_mode_g120(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in FX3_EXACT_4_VIDEO_LIGHT_MODES_G120:
        if u == item.upper():
            return item
    return None


# ---------------------------------------------------------------------------
# 1. Fast `< 0.20s` O_RDONLY Donor Contract Audit (`Phase 286`)
# ---------------------------------------------------------------------------


def audit_phase286_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: Optional[float] = None,
) -> Phase286DonorAuditResult:
    """Inspect local FX3 Ver. 7.02 / FX6 Ver. 6.01 donor artifacts strictly via
    `os.open(..., os.O_RDONLY)` within `<0.20s` (`1.00s` under
    `GITHUB_ACTIONS=true`), using targeted `os.pread` slices on both 79 MiB FX3
    `appFw.so` and 50.5 MiB FX6 `appFw.so`, and full `O_RDONLY` SHA-256
    verification on 4-language `.uxc` packs and `BK4` seed with deterministic
    `CLEAN_ROOM_SYNTHETIC` fallback.
    """
    t0 = time.perf_counter()
    budget = (
        _default_donor_budget_seconds_phase286()
        if max_budget_seconds is None
        else float(max_budget_seconds)
    )
    clean_forced = _is_forced_clean_room(force_clean_room)
    resolved_repo = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()

    candidate_root: Optional[Path] = None
    if not clean_forced:
        if work_root is not None:
            candidate_root = Path(work_root)
        else:
            paths = resolve_donor_thermal_power_paths(
                work_root=work_root, repo_root=resolved_repo
            )
            candidate_root = paths.work_root

    resolved: Dict[str, Path] = {}
    all_present = False
    if not clean_forced and candidate_root is not None and candidate_root.is_dir():
        all_present = True
        for key, (_body, rel_path, *_rest) in PINNED_PHASE286_DONOR_SPECS.items():
            fp = candidate_root / rel_path
            if fp.is_file():
                resolved[key] = fp
            else:
                all_present = False
                break

    if clean_forced or not all_present:
        elapsed = time.perf_counter() - t0
        within_budget = elapsed < budget
        synthetic_markers = tuple(
            spec[5] for spec in PINNED_PHASE286_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE286_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE286_DONOR_SPECS.items()}
        return Phase286DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE286_DONOR_INTEGRITY
            ),
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_CLEAN_ROOM",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_200ms=within_budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=synthetic_markers,
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            sha256_by_artifact=synthetic_shas,
            bytes_by_artifact=synthetic_sizes,
            errors=()
            if within_budget
            else (
                f"Clean-room donor check exceeded budget ({elapsed:.4f}s >= {budget:.4f}s).",
            ),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []
    passed_keys: Set[str] = set()
    files_inspected = 0

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE286_DONOR_SPECS.items():
        fp = resolved[key]
        if key in ("fx3_appfw_so", "fx6_appfw_so"):
            slices_spec = (
                PINNED_FX3_APPFW_SLICES_PHASE286
                if key == "fx3_appfw_so"
                else PINNED_FX6_APPFW_SLICES_PHASE286
            )
            try:
                actual_size, actual_sha, slices_ok = _read_targeted_slices_o_rdonly(
                    fp, slices_spec
                )
                files_inspected += 1
            except OSError as exc:
                missing.append(marker_label)
                errors.append(f"O_RDONLY targeted pread failed for {key}: {exc}")
                continue
            sizes[key] = actual_size
            shas[key] = actual_sha
            size_ok = actual_size == exp_size
            sha_ok = actual_sha == exp_sha
            markers_ok = bool(slices_ok)
        else:
            try:
                actual_size, actual_sha, blob = _read_cached_donor_o_rdonly(fp)
                files_inspected += 1
            except OSError as exc:
                missing.append(marker_label)
                errors.append(f"O_RDONLY read failed for {key}: {exc}")
                continue
            sizes[key] = actual_size
            shas[key] = actual_sha
            size_ok = actual_size == exp_size
            sha_ok = actual_sha == exp_sha
            markers_ok = all(m in blob for m in marker_tuple)

        if not size_ok:
            errors.append(
                f"Donor size mismatch for {key}: got {actual_size}, expected {exp_size}."
            )
        if not sha_ok:
            errors.append(
                f"Donor SHA-256 mismatch for {key}: got {actual_sha}, expected {exp_sha}."
            )
        if not markers_ok:
            errors.append(f"Missing required Wave-50 byte markers in {key}.")

        if size_ok and sha_ok and markers_ok:
            checked.append(marker_label)
            passed_keys.add(key)
        else:
            missing.append(marker_label)

    elapsed = time.perf_counter() - t0
    within_budget = elapsed < budget
    if not within_budget:
        errors.append(
            f"Local O_RDONLY donor audit exceeded budget ({elapsed:.4f}s >= {budget:.4f}s)."
        )

    fx3_ok = all(
        k in passed_keys
        for k in (
            "fx3_appfw_so",
            "fx3_string_english_f_uxc",
            "fx3_string_english_uxc",
            "fx3_string_english_g_uxc",
            "fx3_bk4_bin",
        )
    )
    lang_ok = all(
        k in passed_keys
        for k in (
            "fx3_string_english_f_uxc",
            "fx3_string_simplifiedchinese_f_uxc",
            "fx3_string_traditionalchinese_f_uxc",
            "fx3_string_japanese_f_uxc",
        )
    )
    fx6_ok = all(
        k in passed_keys
        for k in (
            "fx6_appfw_so",
            "fx6_string_english_uxc",
            "fx6_string_english_2_uxc",
        )
    )
    valid = (
        files_inspected == len(PINNED_PHASE286_DONOR_SPECS)
        and within_budget
        and (not missing)
        and (not errors)
        and fx3_ok
        and fx6_ok
        and lang_ok
    )
    return Phase286DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE286_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="OS_OPEN_O_RDONLY",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_200ms=within_budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_ok,
        fx6_contracts_verified=fx6_ok,
        four_lang_resid16_parity_verified=lang_ok,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate G119: 14-Option [Focus Area], AF Area Reg, XLR-H1 & Zoom Speeds
# ---------------------------------------------------------------------------


def resolve_fx3_focus_area_and_zoom_lever_state(
    *,
    shoot_mode: str = SHOOT_MODE_M_PHASE286,
    focus_mode: str = AF_FOCUS_MODE_AF_C_G119,
    requested_focus_area: str = FOCUS_AREA_FACTORY_DEFAULT_G119,
    focus_area_limit_enabled_count: int = len(FX3_EXACT_14_FOCUS_AREAS_G119),
    requested_focus_area_color: str = FOCUS_AREA_COLOR_FACTORY_DEFAULT_G119,
    requested_circ_of_focus_point: str = CIRC_FOCUS_POINT_DEFAULT_G119,
    requested_switch_vh_af_area: str = SWITCH_VH_OFF_G119,
    requested_af_area_registration: str = "Off",
    requested_zoom_range: str = ZOOM_RANGE_FACTORY_DEFAULT_G119,
    raw_recording: bool = False,
    high_fps_120p_100p: bool = False,
    zoom_lever_1st_speed_stby: int = ZOOM_LEVER_1ST_DEFAULT_G119,
    zoom_lever_1st_speed_rec: int = ZOOM_LEVER_1ST_DEFAULT_G119,
    zoom_lever_2nd_speed_stby: int = ZOOM_LEVER_2ND_DEFAULT_G119,
    zoom_lever_2nd_speed_rec: int = ZOOM_LEVER_2ND_DEFAULT_G119,
    custom_key_z_speed_stby: int = CUSTOM_KEY_Z_SPEED_DEFAULT_G119,
    custom_key_z_speed_rec: int = CUSTOM_KEY_Z_SPEED_DEFAULT_G119,
    remote_zoom_speed_type: str = REMOTE_ZOOM_SPEED_TYPE_DEFAULT_G119,
    remote_zoom_fixed_speed_stby: int = REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G119,
    remote_zoom_fixed_speed_rec: int = REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G119,
    reset_action: str = RESET_ACTION_NONE_PHASE286,
) -> Dict[str, Any]:
    s_mode = _norm_shoot_mode_phase286(shoot_mode) or SHOOT_MODE_M_PHASE286
    f_mode = _norm_focus_mode_g119(focus_mode) or AF_FOCUS_MODE_AF_C_G119
    r_act = _norm_reset_action_phase286(reset_action) or RESET_ACTION_NONE_PHASE286

    req_fa = _norm_focus_area_g119(requested_focus_area) or FOCUS_AREA_FACTORY_DEFAULT_G119
    req_color = _norm_focus_area_color_g119(requested_focus_area_color) or FOCUS_AREA_COLOR_FACTORY_DEFAULT_G119
    req_circ = _norm_circ_focus_point_g119(requested_circ_of_focus_point) or CIRC_FOCUS_POINT_DEFAULT_G119
    req_vh = _norm_switch_vh_g119(requested_switch_vh_af_area) or SWITCH_VH_OFF_G119
    req_af_reg = _norm_on_off_phase286(requested_af_area_registration) or "Off"
    req_zrange = _norm_zoom_range_g119(requested_zoom_range) or ZOOM_RANGE_FACTORY_DEFAULT_G119
    req_rtype = _norm_remote_zoom_speed_type_g119(remote_zoom_speed_type) or REMOTE_ZOOM_SPEED_TYPE_DEFAULT_G119

    # Reset behavior:
    # - [Camera Settings Reset] resets Focus Area, Focus Area Limit, Circ. of Focus Point,
    #   Switch V/H AF Area, Zoom Lever Speed, Custom Key Z. Speed, and Remote Zoom Speed.
    # - [Focus Area Color] (0x6af1), [AF Area Registration] (0x6b65), and [Zoom Range] (0x7164)
    #   SURVIVE [Camera Settings Reset] and only reset on [Initialize]!
    if r_act == RESET_ACTION_INITIALIZE_PHASE286:
        sel_fa = FOCUS_AREA_FACTORY_DEFAULT_G119
        eff_limit_cnt = len(FX3_EXACT_14_FOCUS_AREAS_G119)
        eff_color = FOCUS_AREA_COLOR_FACTORY_DEFAULT_G119
        eff_circ = CIRC_FOCUS_POINT_DEFAULT_G119
        sel_vh = SWITCH_VH_OFF_G119
        sel_af_reg = "Off"
        sel_zrange = ZOOM_RANGE_FACTORY_DEFAULT_G119
        z1_stby = ZOOM_LEVER_1ST_DEFAULT_G119
        z1_rec = ZOOM_LEVER_1ST_DEFAULT_G119
        z2_stby = ZOOM_LEVER_2ND_DEFAULT_G119
        z2_rec = ZOOM_LEVER_2ND_DEFAULT_G119
        ck_stby = CUSTOM_KEY_Z_SPEED_DEFAULT_G119
        ck_rec = CUSTOM_KEY_Z_SPEED_DEFAULT_G119
        eff_rtype = REMOTE_ZOOM_SPEED_TYPE_DEFAULT_G119
        rz_stby = REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G119
        rz_rec = REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G119
    elif r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286:
        sel_fa = FOCUS_AREA_FACTORY_DEFAULT_G119
        eff_limit_cnt = len(FX3_EXACT_14_FOCUS_AREAS_G119)
        eff_color = req_color
        eff_circ = CIRC_FOCUS_POINT_DEFAULT_G119
        sel_vh = SWITCH_VH_OFF_G119
        sel_af_reg = req_af_reg
        sel_zrange = req_zrange
        z1_stby = ZOOM_LEVER_1ST_DEFAULT_G119
        z1_rec = ZOOM_LEVER_1ST_DEFAULT_G119
        z2_stby = ZOOM_LEVER_2ND_DEFAULT_G119
        z2_rec = ZOOM_LEVER_2ND_DEFAULT_G119
        ck_stby = CUSTOM_KEY_Z_SPEED_DEFAULT_G119
        ck_rec = CUSTOM_KEY_Z_SPEED_DEFAULT_G119
        eff_rtype = REMOTE_ZOOM_SPEED_TYPE_DEFAULT_G119
        rz_stby = REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G119
        rz_rec = REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G119
    else:
        sel_fa = req_fa
        eff_limit_cnt = int(focus_area_limit_enabled_count)
        eff_color = req_color
        eff_circ = req_circ
        sel_vh = req_vh
        sel_af_reg = req_af_reg
        sel_zrange = req_zrange
        z1_stby = int(zoom_lever_1st_speed_stby)
        z1_rec = int(zoom_lever_1st_speed_rec)
        z2_stby = int(zoom_lever_2nd_speed_stby)
        z2_rec = int(zoom_lever_2nd_speed_rec)
        ck_stby = int(custom_key_z_speed_stby)
        ck_rec = int(custom_key_z_speed_rec)
        eff_rtype = req_rtype
        rz_stby = int(remote_zoom_fixed_speed_stby)
        rz_rec = int(remote_zoom_fixed_speed_rec)

    is_still_pasm = s_mode in PASM_SHOOT_MODES_PHASE286
    is_movie_or_sq = s_mode in MOVIE_SHOOT_MODES_PHASE286

    # Effective Focus Area rules:
    # - In Intelligent Auto, locked to Wide.
    # - In Movie/S&Q, the 7 Tracking: menu entries are locked out (falls back to Wide;
    #   Movie uses Touch Tracking).
    # - In Still PASM, Tracking:* requires AF-C.
    if s_mode == SHOOT_MODE_INTELLIGENT_AUTO_PHASE286:
        eff_fa = FOCUS_AREA_WIDE_G119
    elif sel_fa in FX3_STILL_ONLY_7_TRACKING_FOCUS_AREAS_G119 and (
        is_movie_or_sq or f_mode != AF_FOCUS_MODE_AF_C_G119
    ):
        eff_fa = FOCUS_AREA_WIDE_G119
    else:
        eff_fa = sel_fa

    # Effective AF Area Registration & Switch V/H AF Area: Still PASM only.
    eff_af_reg = sel_af_reg if is_still_pasm else "Off"
    lock_op_parts_forced_off = eff_af_reg == "On"

    # Zoom Range & ClearImage / Digital Zoom lockouts:
    clear_digital_zoom_avail = (not bool(raw_recording)) and (
        not bool(high_fps_120p_100p)
    )
    if (
        sel_zrange in (ZOOM_RANGE_CLEAR_IMAGE_G119, ZOOM_RANGE_DIGITAL_G119)
        and not clear_digital_zoom_avail
    ):
        eff_zrange = ZOOM_RANGE_OPTICAL_ONLY_G119
    else:
        eff_zrange = sel_zrange

    eff_vh = (
        sel_vh
        if (is_still_pasm and eff_zrange != ZOOM_RANGE_DIGITAL_G119)
        else SWITCH_VH_OFF_G119
    )

    return {
        "shoot_mode": s_mode,
        "focus_mode": f_mode,
        "reset_action": r_act,
        "effective_focus_area": eff_fa,
        "focus_area_limit_enabled_count": eff_limit_cnt,
        "focus_area_color": eff_color,
        "focus_area_color_survived_cam_reset": (
            r_act != RESET_ACTION_INITIALIZE_PHASE286 and eff_color == req_color
        ),
        "circ_of_focus_point": eff_circ,
        "switch_vh_af_area": eff_vh,
        "effective_af_area_registration": eff_af_reg,
        "af_area_reg_survived_cam_reset": (
            r_act != RESET_ACTION_INITIALIZE_PHASE286 and sel_af_reg == req_af_reg
        ),
        "lock_operation_parts_forced_off": lock_op_parts_forced_off,
        "effective_zoom_range": eff_zrange,
        "zoom_range_survived_cam_reset": (
            r_act != RESET_ACTION_INITIALIZE_PHASE286 and sel_zrange == req_zrange
        ),
        "clear_digital_zoom_available": clear_digital_zoom_avail,
        "zoom_lever_1st_speed_stby": z1_stby,
        "zoom_lever_1st_speed_rec": z1_rec,
        "zoom_lever_2nd_speed_stby": z2_stby,
        "zoom_lever_2nd_speed_rec": z2_rec,
        "custom_key_z_speed_stby": ck_stby,
        "custom_key_z_speed_rec": ck_rec,
        "remote_zoom_speed_type": eff_rtype,
        "remote_zoom_fixed_speed_stby": rz_stby,
        "remote_zoom_fixed_speed_rec": rz_rec,
    }


def compute_focus_area_and_zoom_lever_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate 384 combinations across 4 `[Focus Area]` variants
    (`Wide`, `Spot: M`, `Tracking: Wide`, `Tracking: Expand Spot`), 4 shoot modes
    (`M`, `Intelligent Auto`, `Movie`, `S&Q`), 3 reset actions (`NONE`,
    `Camera Settings Reset`, `Initialize`), 2 `[Zoom Range]` requests
    (`Optical zoom only`, `ClearImage Zoom`), 2 RAW/120p lockout states, and
    2 `AF Area Registration` states (`Off`, `On`).
    """
    states_checked = 0
    movie_tracking_locked_states = 0
    af_reg_lock_op_parts_off_states = 0
    ciz_locked_in_raw_120p_states = 0
    non_resettable_survived_cam_reset_states = 0

    for fa in (
        FOCUS_AREA_WIDE_G119,
        FOCUS_AREA_SPOT_M_G119,
        FOCUS_AREA_TRACKING_WIDE_G119,
        FOCUS_AREA_TRACKING_EXPAND_SPOT_G119,
    ):
        for sm in (
            SHOOT_MODE_M_PHASE286,
            SHOOT_MODE_INTELLIGENT_AUTO_PHASE286,
            SHOOT_MODE_MOVIE_PHASE286,
            SHOOT_MODE_SQ_PHASE286,
        ):
            for r_act in (
                RESET_ACTION_NONE_PHASE286,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286,
                RESET_ACTION_INITIALIZE_PHASE286,
            ):
                for zr in (
                    ZOOM_RANGE_OPTICAL_ONLY_G119,
                    ZOOM_RANGE_CLEAR_IMAGE_G119,
                ):
                    for raw_or_120p in (False, True):
                        for af_reg in ("Off", "On"):
                            res = resolve_fx3_focus_area_and_zoom_lever_state(
                                shoot_mode=sm,
                                focus_mode=AF_FOCUS_MODE_AF_C_G119,
                                requested_focus_area=fa,
                                requested_focus_area_color=FOCUS_AREA_COLOR_RED_G119,
                                requested_af_area_registration=af_reg,
                                requested_zoom_range=zr,
                                raw_recording=raw_or_120p,
                                high_fps_120p_100p=raw_or_120p,
                                reset_action=r_act,
                            )
                            states_checked += 1
                            if (
                                sm in MOVIE_SHOOT_MODES_PHASE286
                                and fa in FX3_STILL_ONLY_7_TRACKING_FOCUS_AREAS_G119
                                and res["effective_focus_area"] == FOCUS_AREA_WIDE_G119
                            ):
                                movie_tracking_locked_states += 1
                            if res["lock_operation_parts_forced_off"]:
                                af_reg_lock_op_parts_off_states += 1
                            if (
                                zr == ZOOM_RANGE_CLEAR_IMAGE_G119
                                and raw_or_120p
                                and res["effective_zoom_range"] == ZOOM_RANGE_OPTICAL_ONLY_G119
                            ):
                                ciz_locked_in_raw_120p_states += 1
                            if (
                                r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286
                                and res["focus_area_color"] == FOCUS_AREA_COLOR_RED_G119
                                and res["af_area_reg_survived_cam_reset"]
                                and res["zoom_range_survived_cam_reset"]
                            ):
                                non_resettable_survived_cam_reset_states += 1

    return {
        "states_checked": states_checked,
        "movie_tracking_locked_states": movie_tracking_locked_states,
        "af_reg_lock_op_parts_off_states": af_reg_lock_op_parts_off_states,
        "ciz_locked_in_raw_120p_states": ciz_locked_in_raw_120p_states,
        "non_resettable_survived_cam_reset_states": non_resettable_survived_cam_reset_states,
        "all_invariants_hold": (
            states_checked == 384
            and movie_tracking_locked_states == 96
            and af_reg_lock_op_parts_off_states == 32
            and ciz_locked_in_raw_120p_states == 96
            and non_resettable_survived_cam_reset_states == 128
        ),
    }


def verify_focus_area_and_zoom_lever_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE286,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE286,
    fx6_comparison_fw_version: str = FX6_DEFAULT_FW_VERSION_PHASE286,
    shoot_mode: str = SHOOT_MODE_M_PHASE286,
    focus_mode: str = AF_FOCUS_MODE_AF_C_G119,
    requested_focus_area: str = FOCUS_AREA_FACTORY_DEFAULT_G119,
    focus_area_limit_enabled_count: int = len(FX3_EXACT_14_FOCUS_AREAS_G119),
    requested_focus_area_color: str = FOCUS_AREA_COLOR_FACTORY_DEFAULT_G119,
    requested_circ_of_focus_point: str = CIRC_FOCUS_POINT_DEFAULT_G119,
    requested_switch_vh_af_area: str = SWITCH_VH_OFF_G119,
    requested_af_area_registration: str = "Off",
    requested_zoom_range: str = ZOOM_RANGE_FACTORY_DEFAULT_G119,
    raw_recording: bool = False,
    high_fps_120p_100p: bool = False,
    zoom_lever_1st_speed_stby: int = ZOOM_LEVER_1ST_DEFAULT_G119,
    zoom_lever_1st_speed_rec: int = ZOOM_LEVER_1ST_DEFAULT_G119,
    zoom_lever_2nd_speed_stby: int = ZOOM_LEVER_2ND_DEFAULT_G119,
    zoom_lever_2nd_speed_rec: int = ZOOM_LEVER_2ND_DEFAULT_G119,
    custom_key_z_speed_stby: int = CUSTOM_KEY_Z_SPEED_DEFAULT_G119,
    custom_key_z_speed_rec: int = CUSTOM_KEY_Z_SPEED_DEFAULT_G119,
    remote_zoom_speed_type: str = REMOTE_ZOOM_SPEED_TYPE_DEFAULT_G119,
    remote_zoom_fixed_speed_stby: int = REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G119,
    remote_zoom_fixed_speed_rec: int = REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G119,
    reset_action: str = RESET_ACTION_NONE_PHASE286,
    claimed_fx3_focus_areas: Optional[Sequence[str]] = None,
    claimed_movie_tracking_menu_available: bool = False,
    claimed_fx6_has_tracking_focus_areas: bool = False,
    claimed_camera_reset_resets_focus_area_color: bool = False,
    claimed_camera_reset_resets_af_area_reg: bool = False,
    claimed_af_area_reg_allows_lock_op_parts_on: bool = False,
    claimed_xlr_h1_has_zoom_lever: bool = False,
    claimed_xlr_h1_has_rec_button: bool = False,
    claimed_xlr_h1_has_zoom_hold_switch: bool = False,
    claimed_fx6_0_99_is_zoom_speed: bool = False,
    claimed_camera_reset_resets_zoom_range: bool = False,
    claimed_ciz_digital_allowed_in_raw_or_120p: bool = False,
) -> FocusAreaZoomLeverGuardResult:
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME
        or not _is_real_int(body_model_id)
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE286
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
        or not isinstance(fx6_comparison_fw_version, str)
        or not fx6_comparison_fw_version.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G119_TELEMETRY_INVALID)
        errors.append(
            "Gate G119 requires ILME-FX3 (0x91030080, Help Guide ilc/2210, Ver. 7.02)."
        )

    norm_shoot = _norm_shoot_mode_phase286(shoot_mode)
    norm_focus_mode = _norm_focus_mode_g119(focus_mode)
    norm_fa = _norm_focus_area_g119(requested_focus_area)
    norm_color = _norm_focus_area_color_g119(requested_focus_area_color)
    norm_circ = _norm_circ_focus_point_g119(requested_circ_of_focus_point)
    norm_vh = _norm_switch_vh_g119(requested_switch_vh_af_area)
    norm_af_reg = _norm_on_off_phase286(requested_af_area_registration)
    norm_zrange = _norm_zoom_range_g119(requested_zoom_range)
    norm_rtype = _norm_remote_zoom_speed_type_g119(remote_zoom_speed_type)
    norm_reset = _norm_reset_action_phase286(reset_action)

    ints_ok = all(
        _is_real_int(v)
        for v in (
            focus_area_limit_enabled_count,
            zoom_lever_1st_speed_stby,
            zoom_lever_1st_speed_rec,
            zoom_lever_2nd_speed_stby,
            zoom_lever_2nd_speed_rec,
            custom_key_z_speed_stby,
            custom_key_z_speed_rec,
            remote_zoom_fixed_speed_stby,
            remote_zoom_fixed_speed_rec,
        )
    )
    bools_ok = all(
        isinstance(b, bool)
        for b in (
            raw_recording,
            high_fps_120p_100p,
            claimed_movie_tracking_menu_available,
            claimed_fx6_has_tracking_focus_areas,
            claimed_camera_reset_resets_focus_area_color,
            claimed_camera_reset_resets_af_area_reg,
            claimed_af_area_reg_allows_lock_op_parts_on,
            claimed_xlr_h1_has_zoom_lever,
            claimed_xlr_h1_has_rec_button,
            claimed_xlr_h1_has_zoom_hold_switch,
            claimed_fx6_0_99_is_zoom_speed,
            claimed_camera_reset_resets_zoom_range,
            claimed_ciz_digital_allowed_in_raw_or_120p,
        )
    )
    if (
        norm_shoot is None
        or norm_focus_mode is None
        or norm_fa is None
        or norm_color is None
        or norm_circ is None
        or norm_vh is None
        or norm_af_reg is None
        or norm_zrange is None
        or norm_rtype is None
        or norm_reset is None
        or not ints_ok
        or not bools_ok
    ):
        _add_code(codes, STATUS_BLOCKED_G119_TELEMETRY_INVALID)
        errors.append("Invalid or unrecognized G119 telemetry or enum value.")

    resolved = resolve_fx3_focus_area_and_zoom_lever_state(
        shoot_mode=norm_shoot or SHOOT_MODE_M_PHASE286,
        focus_mode=norm_focus_mode or AF_FOCUS_MODE_AF_C_G119,
        requested_focus_area=norm_fa or FOCUS_AREA_FACTORY_DEFAULT_G119,
        focus_area_limit_enabled_count=(
            int(focus_area_limit_enabled_count)
            if _is_real_int(focus_area_limit_enabled_count)
            else len(FX3_EXACT_14_FOCUS_AREAS_G119)
        ),
        requested_focus_area_color=norm_color or FOCUS_AREA_COLOR_FACTORY_DEFAULT_G119,
        requested_circ_of_focus_point=norm_circ or CIRC_FOCUS_POINT_DEFAULT_G119,
        requested_switch_vh_af_area=norm_vh or SWITCH_VH_OFF_G119,
        requested_af_area_registration=norm_af_reg or "Off",
        requested_zoom_range=norm_zrange or ZOOM_RANGE_FACTORY_DEFAULT_G119,
        raw_recording=bool(raw_recording),
        high_fps_120p_100p=bool(high_fps_120p_100p),
        zoom_lever_1st_speed_stby=(
            int(zoom_lever_1st_speed_stby)
            if _is_real_int(zoom_lever_1st_speed_stby)
            else ZOOM_LEVER_1ST_DEFAULT_G119
        ),
        zoom_lever_1st_speed_rec=(
            int(zoom_lever_1st_speed_rec)
            if _is_real_int(zoom_lever_1st_speed_rec)
            else ZOOM_LEVER_1ST_DEFAULT_G119
        ),
        zoom_lever_2nd_speed_stby=(
            int(zoom_lever_2nd_speed_stby)
            if _is_real_int(zoom_lever_2nd_speed_stby)
            else ZOOM_LEVER_2ND_DEFAULT_G119
        ),
        zoom_lever_2nd_speed_rec=(
            int(zoom_lever_2nd_speed_rec)
            if _is_real_int(zoom_lever_2nd_speed_rec)
            else ZOOM_LEVER_2ND_DEFAULT_G119
        ),
        custom_key_z_speed_stby=(
            int(custom_key_z_speed_stby)
            if _is_real_int(custom_key_z_speed_stby)
            else CUSTOM_KEY_Z_SPEED_DEFAULT_G119
        ),
        custom_key_z_speed_rec=(
            int(custom_key_z_speed_rec)
            if _is_real_int(custom_key_z_speed_rec)
            else CUSTOM_KEY_Z_SPEED_DEFAULT_G119
        ),
        remote_zoom_speed_type=norm_rtype or REMOTE_ZOOM_SPEED_TYPE_DEFAULT_G119,
        remote_zoom_fixed_speed_stby=(
            int(remote_zoom_fixed_speed_stby)
            if _is_real_int(remote_zoom_fixed_speed_stby)
            else REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G119
        ),
        remote_zoom_fixed_speed_rec=(
            int(remote_zoom_fixed_speed_rec)
            if _is_real_int(remote_zoom_fixed_speed_rec)
            else REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G119
        ),
        reset_action=norm_reset or RESET_ACTION_NONE_PHASE286,
    )

    matrix = compute_focus_area_and_zoom_lever_matrix()
    if not matrix["all_invariants_hold"]:
        _add_code(codes, STATUS_BLOCKED_G119_TELEMETRY_INVALID)
        errors.append("G119 384-state matrix verification failed.")

    # 1. Movie/S&Q Tracking: Focus Area Lockout & Still AF-C Boundary + 14-Option Catalog
    fa_catalog_spoof = False
    if claimed_fx3_focus_areas is not None:
        normed_fa = [_norm_focus_area_g119(x) for x in claimed_fx3_focus_areas]
        if (
            len(claimed_fx3_focus_areas) != len(FX3_EXACT_14_FOCUS_AREAS_G119)
            or None in normed_fa
            or set(normed_fa) != set(FX3_EXACT_14_FOCUS_AREAS_G119)
        ):
            fa_catalog_spoof = True

    movie_tracking_requested = (
        norm_reset == RESET_ACTION_NONE_PHASE286
        and norm_shoot in MOVIE_SHOOT_MODES_PHASE286
        and norm_fa in FX3_STILL_ONLY_7_TRACKING_FOCUS_AREAS_G119
    )
    still_tracking_non_afc = (
        norm_reset == RESET_ACTION_NONE_PHASE286
        and norm_shoot in PASM_SHOOT_MODES_PHASE286
        and norm_fa in FX3_STILL_ONLY_7_TRACKING_FOCUS_AREAS_G119
        and norm_focus_mode != AF_FOCUS_MODE_AF_C_G119
    )
    if (
        movie_tracking_requested
        or still_tracking_non_afc
        or claimed_movie_tracking_menu_available
        or claimed_fx6_has_tracking_focus_areas
        or fa_catalog_spoof
    ):
        _add_code(codes, STATUS_BLOCKED_G119_MOVIE_TRACKING_FOCUS_AREA_VIOLATION)
        errors.append(
            "ILME-FX3 [Focus Area] (0xe0ad) exposes 7 shared Still+Movie areas + "
            "7 Still-only (AF-C) [Tracking:] areas; Movie/S&Q locks out all 7 menu "
            "Tracking: areas (use [Touch Tracking] instead), and FX6 exposes only "
            "Wide/Zone/Flexible Spot."
        )

    # 2. [Focus Area Limit] >= 2, [Focus Area Color] Reset Survival & [AF Area Registration]
    limit_bad = (
        _is_real_int(focus_area_limit_enabled_count)
        and (
            focus_area_limit_enabled_count < MIN_FOCUS_AREA_LIMIT_COUNT_G119
            or focus_area_limit_enabled_count > len(FX3_EXACT_14_FOCUS_AREAS_G119)
        )
    )
    af_reg_in_movie_or_iauto = (
        norm_reset == RESET_ACTION_NONE_PHASE286
        and norm_af_reg == "On"
        and norm_shoot not in PASM_SHOOT_MODES_PHASE286
    )
    if (
        limit_bad
        or af_reg_in_movie_or_iauto
        or claimed_camera_reset_resets_focus_area_color
        or claimed_camera_reset_resets_af_area_reg
        or claimed_af_area_reg_allows_lock_op_parts_on
    ):
        _add_code(codes, STATUS_BLOCKED_G119_FOCUS_AREA_LIMIT_OR_AF_REG_VIOLATION)
        errors.append(
            "[Focus Area Limit] (0x6de2/0xe227) requires >= 2 active areas; "
            "[Focus Area Color] (0x6af1) and [AF Area Registration] (0x6b65, Still-only) "
            "survive [Camera Settings Reset], and active [AF Area Registration] locks "
            "[Lock Operation Parts] to Off."
        )

    # 3. XLR-H1 No-Zoom-Lever Myth-Bust & FX6 0..99 Position Display Contrast
    if (
        claimed_xlr_h1_has_zoom_lever
        or claimed_xlr_h1_has_rec_button
        or claimed_xlr_h1_has_zoom_hold_switch
        or claimed_fx6_0_99_is_zoom_speed
    ):
        _add_code(codes, STATUS_BLOCKED_G119_XLRH1_FAKE_HANDLE_ZOOM_SPOOF_VIOLATION)
        errors.append(
            "ILME-FX3 XLR-H1 handle is audio-only: NO zoom lever, NO record button, "
            "and NO ZOOM HOLD switch (only body W/T Zoom Lever Speed 1..8 exists); "
            "FX6 0..99 is Zoom Position Display (0x22ce), not zoom speed."
        )

    # 4. Zoom Speed (1..8) & [Zoom Range] RAW/120p Lockout + Reset Persistence
    speeds_ok = all(
        _is_real_int(s) and ZOOM_SPEED_MIN_G119 <= s <= ZOOM_SPEED_MAX_G119
        for s in (
            zoom_lever_1st_speed_stby,
            zoom_lever_1st_speed_rec,
            zoom_lever_2nd_speed_stby,
            zoom_lever_2nd_speed_rec,
            custom_key_z_speed_stby,
            custom_key_z_speed_rec,
            remote_zoom_fixed_speed_stby,
            remote_zoom_fixed_speed_rec,
        )
    )
    ciz_digital_in_raw_or_120p = (
        norm_reset == RESET_ACTION_NONE_PHASE286
        and norm_zrange in (ZOOM_RANGE_CLEAR_IMAGE_G119, ZOOM_RANGE_DIGITAL_G119)
        and (bool(raw_recording) or bool(high_fps_120p_100p))
    )
    if (
        (not speeds_ok)
        or ciz_digital_in_raw_or_120p
        or claimed_camera_reset_resets_zoom_range
        or claimed_ciz_digital_allowed_in_raw_or_120p
    ):
        _add_code(codes, STATUS_BLOCKED_G119_ZOOM_RANGE_OR_SPEED_BOUNDARY_VIOLATION)
        errors.append(
            "[Zoom Lever Speed], [Custom Key Z. Speed], and [Remote Zoom Speed] speeds "
            "must be within 1..8; [Zoom Range] (0x7164) survives [Camera Settings Reset], "
            "and ClearImage/Digital Zoom are locked out in RAW or 119.88p/100p."
        )

    valid = not codes
    status = STATUS_VERIFIED_G119 if valid else codes[0]

    return FocusAreaZoomLeverGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}"
        if _is_real_int(body_model_id)
        else "invalid",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        fx6_comparison_fw_version=fx6_comparison_fw_version,
        reset_action=resolved["reset_action"],
        focus_area_menu_path=FOCUS_AREA_MENU_PATH_G119,
        focus_area_limit_menu_path=FOCUS_AREA_LIMIT_MENU_PATH_G119,
        af_area_reg_menu_path=AF_AREA_REG_MENU_PATH_G119,
        zoom_menu_path=ZOOM_MENU_PATH_G119,
        zoom_lever_speed_menu_path=ZOOM_LEVER_SPEED_MENU_PATH_G119,
        remote_zoom_speed_menu_path=REMOTE_ZOOM_SPEED_MENU_PATH_G119,
        shoot_mode=resolved["shoot_mode"],
        focus_mode=resolved["focus_mode"],
        fx3_exact_14_focus_areas=FX3_EXACT_14_FOCUS_AREAS_G119,
        fx3_shared_7_focus_areas=FX3_SHARED_7_FOCUS_AREAS_G119,
        fx3_still_only_7_tracking_focus_areas=FX3_STILL_ONLY_7_TRACKING_FOCUS_AREAS_G119,
        movie_tracking_mechanism=MOVIE_TRACKING_MECHANISM_G119,
        requested_focus_area=norm_fa or str(requested_focus_area),
        effective_focus_area=resolved["effective_focus_area"],
        focus_area_limit_enabled_count=resolved["focus_area_limit_enabled_count"],
        focus_area_color=resolved["focus_area_color"],
        focus_area_color_survived_cam_reset=resolved[
            "focus_area_color_survived_cam_reset"
        ],
        circ_of_focus_point=resolved["circ_of_focus_point"],
        switch_vh_af_area=resolved["switch_vh_af_area"],
        requested_af_area_registration=norm_af_reg or str(requested_af_area_registration),
        effective_af_area_registration=resolved["effective_af_area_registration"],
        af_area_reg_survived_cam_reset=resolved["af_area_reg_survived_cam_reset"],
        lock_operation_parts_forced_off=resolved["lock_operation_parts_forced_off"],
        xlr_h1_has_zoom_lever=FX3_XLR_H1_HAS_ZOOM_LEVER_G119,
        xlr_h1_has_rec_button=FX3_XLR_H1_HAS_REC_BUTTON_G119,
        xlr_h1_has_zoom_hold_switch=FX3_XLR_H1_HAS_ZOOM_HOLD_SWITCH_G119,
        requested_zoom_range=norm_zrange or str(requested_zoom_range),
        effective_zoom_range=resolved["effective_zoom_range"],
        zoom_range_survived_cam_reset=resolved["zoom_range_survived_cam_reset"],
        clear_digital_zoom_available=resolved["clear_digital_zoom_available"],
        zoom_lever_1st_speed_stby=resolved["zoom_lever_1st_speed_stby"],
        zoom_lever_1st_speed_rec=resolved["zoom_lever_1st_speed_rec"],
        zoom_lever_2nd_speed_stby=resolved["zoom_lever_2nd_speed_stby"],
        zoom_lever_2nd_speed_rec=resolved["zoom_lever_2nd_speed_rec"],
        custom_key_z_speed_stby=resolved["custom_key_z_speed_stby"],
        custom_key_z_speed_rec=resolved["custom_key_z_speed_rec"],
        remote_zoom_speed_type=resolved["remote_zoom_speed_type"],
        remote_zoom_fixed_speed_stby=resolved["remote_zoom_fixed_speed_stby"],
        remote_zoom_fixed_speed_rec=resolved["remote_zoom_fixed_speed_rec"],
        fx6_zoom_position_display_range=FX6_ZOOM_POSITION_DISPLAY_RANGE_G119,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g119_focus_area_and_zoom_lever_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    focus_area_zoom_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase286DonorAuditResult] = None,
) -> Tuple[GateVerdict, G119FocusAreaZoomLeverGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase286_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_focus_area_and_zoom_lever_guard(**dict(focus_area_zoom_kwargs or {}))

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G119.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G119 if valid else codes[0]

    res = G119FocusAreaZoomLeverGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        focus_area_zoom_lever_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, fa={guard.effective_focus_area}"
        f"(14opt={len(guard.fx3_exact_14_focus_areas)},trk_still_only=7,"
        f"limit={guard.focus_area_limit_enabled_count},af_reg={guard.effective_af_area_registration}), "
        f"xlr_h1_zoom_lever={guard.xlr_h1_has_zoom_lever}, "
        f"z_lever=({guard.zoom_lever_1st_speed_stby}/{guard.zoom_lever_2nd_speed_stby}), "
        f"remote_z={guard.remote_zoom_speed_type}({guard.remote_zoom_fixed_speed_stby}), "
        f"z_range={guard.effective_zoom_range}"
    )
    verdict = GateVerdict(
        gate_id=G119_GATE_ID,
        gate_code=G119_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G120: [ISO Range Limit], [ISO AUTO Min. SS], Cine EI & Flash Sync
# ---------------------------------------------------------------------------


def resolve_fx3_iso_minss_and_flash_state(
    *,
    shoot_mode: str = SHOOT_MODE_M_PHASE286,
    log_shooting: str = LOG_SHOOTING_OFF_G120,
    iso_mode: str = "Manual",
    requested_iso_value: int = 800,
    requested_iso_range_min: int = ISO_DEFAULT_STILL_MIN_G120,
    requested_iso_range_max: int = ISO_DEFAULT_STILL_MAX_G120,
    requested_iso_auto_min_ss: str = ISO_AUTO_MIN_SS_FACTORY_DEFAULT_G120,
    shutter_type: str = SHUTTER_TYPE_MECHANICAL_G120,
    silent_mode: str = "Off",
    flash_requested: bool = False,
    requested_flash_mode: str = FLASH_MODE_FACTORY_DEFAULT_G120,
    flash_comp_ev: float = 0.0,
    requested_exp_comp_set: str = EXP_COMP_SET_FACTORY_DEFAULT_G120,
    wireless_flash: str = "Off",
    red_eye_reduction: str = "Off",
    shutter_speed_seconds: float = 1.0 / 125.0,
    requested_video_light_mode: str = VIDEO_LIGHT_FACTORY_DEFAULT_G120,
    reset_action: str = RESET_ACTION_NONE_PHASE286,
) -> Dict[str, Any]:
    s_mode = _norm_shoot_mode_phase286(shoot_mode) or SHOOT_MODE_M_PHASE286
    l_mode = _norm_log_shooting_g120(log_shooting) or LOG_SHOOTING_OFF_G120
    r_act = _norm_reset_action_phase286(reset_action) or RESET_ACTION_NONE_PHASE286
    sh_type = _norm_shutter_type_g120(shutter_type) or SHUTTER_TYPE_MECHANICAL_G120
    sil_mode = _norm_on_off_phase286(silent_mode) or "Off"
    req_min_ss = _norm_iso_auto_min_ss_g120(requested_iso_auto_min_ss) or ISO_AUTO_MIN_SS_FACTORY_DEFAULT_G120
    req_flash = _norm_flash_mode_g120(requested_flash_mode) or FLASH_MODE_FACTORY_DEFAULT_G120
    req_exp_comp = _norm_exp_comp_set_g120(requested_exp_comp_set) or EXP_COMP_SET_FACTORY_DEFAULT_G120
    req_wless = _norm_on_off_phase286(wireless_flash) or "Off"
    req_redeye = _norm_on_off_phase286(red_eye_reduction) or "Off"
    req_vlight = _norm_video_light_mode_g120(requested_video_light_mode) or VIDEO_LIGHT_FACTORY_DEFAULT_G120

    # Reset behavior:
    # - [Camera Settings Reset] resets [ISO AUTO Min. SS], [Flash Mode], [Flash Comp.],
    #   [Wireless Flash], [Red Eye Reduction], and [Video Light Mode].
    # - [ISO Range Limit] (0x72f8), [Exp.comp.set] (0xe11a), and [External Flash Set.]
    #   SURVIVE [Camera Settings Reset] and only reset on [Initialize]!
    if r_act == RESET_ACTION_INITIALIZE_PHASE286:
        eff_iso_min = ISO_DEFAULT_STILL_MIN_G120
        eff_iso_max = ISO_DEFAULT_STILL_MAX_G120
        eff_min_ss = ISO_AUTO_MIN_SS_FACTORY_DEFAULT_G120
        sel_flash = FLASH_MODE_FACTORY_DEFAULT_G120
        eff_fcomp = 0.0
        eff_exp_comp = EXP_COMP_SET_FACTORY_DEFAULT_G120
        eff_wless = "Off"
        eff_redeye = "Off"
        eff_vlight = VIDEO_LIGHT_FACTORY_DEFAULT_G120
    elif r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286:
        eff_iso_min = int(requested_iso_range_min)
        eff_iso_max = int(requested_iso_range_max)
        eff_min_ss = ISO_AUTO_MIN_SS_FACTORY_DEFAULT_G120
        sel_flash = FLASH_MODE_FACTORY_DEFAULT_G120
        eff_fcomp = 0.0
        eff_exp_comp = req_exp_comp
        eff_wless = "Off"
        eff_redeye = "Off"
        eff_vlight = VIDEO_LIGHT_FACTORY_DEFAULT_G120
    else:
        eff_iso_min = int(requested_iso_range_min)
        eff_iso_max = int(requested_iso_range_max)
        eff_min_ss = req_min_ss
        sel_flash = req_flash
        eff_fcomp = float(flash_comp_ev)
        eff_exp_comp = req_exp_comp
        eff_wless = req_wless
        eff_redeye = req_redeye
        eff_vlight = req_vlight

    cine_ei_pinned = l_mode in CINE_EI_LOCKED_LOG_MODES_G120
    eff_base_iso: Optional[int] = None
    if cine_ei_pinned:
        eff_base_iso = (
            CINE_EI_BASE_ISOS_G120[1]
            if int(requested_iso_value) == CINE_EI_BASE_ISOS_G120[1]
            else CINE_EI_BASE_ISOS_G120[0]
        )

    is_iso_auto = isinstance(iso_mode, str) and iso_mode.strip().upper() in (
        "AUTO",
        "ISO AUTO",
    )
    iso_auto_min_ss_active = bool(
        (s_mode in ISO_AUTO_MIN_SS_ELIGIBLE_MODES_G120)
        and is_iso_auto
        and (not cine_ei_pinned)
    )

    # Flash availability: strictly Still + Mechanical Shutter + Silent Mode Off
    flash_available = bool(
        (s_mode in STILL_SHOOT_MODES_PHASE286)
        and (sh_type == SHUTTER_TYPE_MECHANICAL_G120)
        and (sil_mode == "Off")
    )
    eff_flash = sel_flash if flash_available else FLASH_MODE_FLASH_OFF_G120

    return {
        "shoot_mode": s_mode,
        "log_shooting": l_mode,
        "reset_action": r_act,
        "effective_iso_range_min": eff_iso_min,
        "effective_iso_range_max": eff_iso_max,
        "iso_range_limit_survived_cam_reset": (
            r_act != RESET_ACTION_INITIALIZE_PHASE286
            and eff_iso_min == int(requested_iso_range_min)
            and eff_iso_max == int(requested_iso_range_max)
        ),
        "cine_ei_base_iso_pinned": cine_ei_pinned,
        "effective_base_iso": eff_base_iso,
        "effective_iso_auto_min_ss": eff_min_ss,
        "iso_auto_min_ss_active": iso_auto_min_ss_active,
        "effective_flash_mode": eff_flash,
        "flash_available": flash_available,
        "flash_comp_ev": eff_fcomp,
        "effective_exp_comp_set": eff_exp_comp,
        "exp_comp_set_survived_cam_reset": (
            r_act != RESET_ACTION_INITIALIZE_PHASE286
            and eff_exp_comp == req_exp_comp
        ),
        "wireless_flash": eff_wless,
        "red_eye_reduction": eff_redeye,
        "effective_video_light_mode": eff_vlight,
        "video_light_active_across_still_movie_sq": True,
    }


def compute_iso_minss_and_flash_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate 384 combinations across 4 shoot modes (`P`, `A`,
    `M`, `Movie`), 4 `[Log Shooting]` modes (`Off`, `Flexible ISO`,
    `Cine EI Quick`, `Cine EI`), 2 `[Shutter Type]` modes, 2 `[Silent Mode]`
    states, 3 reset actions (`NONE`, `Camera Settings Reset`, `Initialize`), and
    2 `[ISO]` modes (`ISO AUTO`, `Manual`) at `ISO Range Limit = 200..6400`,
    `Exp.comp.set = Ambient only`.
    """
    states_checked = 0
    iso_auto_min_ss_active_states = 0
    cine_ei_base_iso_pinned_states = 0
    flash_available_states = 0
    non_resettable_survived_cam_reset_states = 0

    for sm in (
        SHOOT_MODE_P_PHASE286,
        SHOOT_MODE_A_PHASE286,
        SHOOT_MODE_M_PHASE286,
        SHOOT_MODE_MOVIE_PHASE286,
    ):
        for lg in ALLOWED_LOG_SHOOTING_MODES_G120:
            for sh in (SHUTTER_TYPE_MECHANICAL_G120, SHUTTER_TYPE_ELECTRONIC_G120):
                for sil in ("Off", "On"):
                    for r_act in (
                        RESET_ACTION_NONE_PHASE286,
                        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286,
                        RESET_ACTION_INITIALIZE_PHASE286,
                    ):
                        for imode in ("ISO AUTO", "Manual"):
                            res = resolve_fx3_iso_minss_and_flash_state(
                                shoot_mode=sm,
                                log_shooting=lg,
                                iso_mode=imode,
                                requested_iso_value=800,
                                requested_iso_range_min=200,
                                requested_iso_range_max=6400,
                                requested_iso_auto_min_ss=ISO_AUTO_MIN_SS_FAST_G120,
                                shutter_type=sh,
                                silent_mode=sil,
                                requested_flash_mode=FLASH_MODE_FILL_FLASH_G120,
                                requested_exp_comp_set=EXP_COMP_SET_AMBIENT_ONLY_G120,
                                reset_action=r_act,
                            )
                            states_checked += 1
                            if res["iso_auto_min_ss_active"]:
                                iso_auto_min_ss_active_states += 1
                            if res["cine_ei_base_iso_pinned"]:
                                cine_ei_base_iso_pinned_states += 1
                            if res["flash_available"]:
                                flash_available_states += 1
                            if (
                                r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286
                                and res["iso_range_limit_survived_cam_reset"]
                                and res["exp_comp_set_survived_cam_reset"]
                            ):
                                non_resettable_survived_cam_reset_states += 1

    return {
        "states_checked": states_checked,
        "iso_auto_min_ss_active_states": iso_auto_min_ss_active_states,
        "cine_ei_base_iso_pinned_states": cine_ei_base_iso_pinned_states,
        "flash_available_states": flash_available_states,
        "non_resettable_survived_cam_reset_states": non_resettable_survived_cam_reset_states,
        "all_invariants_hold": (
            states_checked == 384
            and iso_auto_min_ss_active_states == 48
            and cine_ei_base_iso_pinned_states == 192
            and flash_available_states == 72
            and non_resettable_survived_cam_reset_states == 128
        ),
    }


def verify_iso_minss_and_flash_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE286,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE286,
    fx6_comparison_fw_version: str = FX6_DEFAULT_FW_VERSION_PHASE286,
    shoot_mode: str = SHOOT_MODE_M_PHASE286,
    log_shooting: str = LOG_SHOOTING_OFF_G120,
    iso_mode: str = "Manual",
    requested_iso_value: int = 800,
    requested_iso_range_min: int = ISO_DEFAULT_STILL_MIN_G120,
    requested_iso_range_max: int = ISO_DEFAULT_STILL_MAX_G120,
    requested_iso_auto_min_ss: str = ISO_AUTO_MIN_SS_FACTORY_DEFAULT_G120,
    shutter_type: str = SHUTTER_TYPE_MECHANICAL_G120,
    silent_mode: str = "Off",
    flash_requested: bool = False,
    requested_flash_mode: str = FLASH_MODE_FACTORY_DEFAULT_G120,
    flash_comp_ev: float = 0.0,
    requested_exp_comp_set: str = EXP_COMP_SET_FACTORY_DEFAULT_G120,
    wireless_flash: str = "Off",
    red_eye_reduction: str = "Off",
    mi_shoe_trigger_voltage_v: float = 5.0,
    mi_shoe_positive_polarity: bool = True,
    shutter_speed_seconds: float = 1.0 / 125.0,
    hss_external_flash: bool = False,
    requested_video_light_mode: str = VIDEO_LIGHT_FACTORY_DEFAULT_G120,
    reset_action: str = RESET_ACTION_NONE_PHASE286,
    claimed_iso_minss_active_in_movie_or_sq: bool = False,
    claimed_cine_ei_allows_variable_iso: bool = False,
    claimed_camera_reset_resets_iso_range_limit: bool = False,
    claimed_camera_reset_resets_exp_comp_set: bool = False,
    claimed_flash_allowed_in_movie_or_sq: bool = False,
    claimed_flash_allowed_with_electronic_shutter: bool = False,
    claimed_flash_allowed_with_silent_mode_on: bool = False,
    claimed_fx6_has_still_flash_stack: bool = False,
    claimed_video_light_blocked_in_movie: bool = False,
) -> IsoMinSsFlashGuardResult:
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME
        or not _is_real_int(body_model_id)
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE286
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
        or not isinstance(fx6_comparison_fw_version, str)
        or not fx6_comparison_fw_version.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G120_TELEMETRY_INVALID)
        errors.append(
            "Gate G120 requires ILME-FX3 (0x91030080, Help Guide ilc/2210, Ver. 7.02)."
        )

    norm_shoot = _norm_shoot_mode_phase286(shoot_mode)
    norm_log = _norm_log_shooting_g120(log_shooting)
    norm_min_ss = _norm_iso_auto_min_ss_g120(requested_iso_auto_min_ss)
    norm_shutter = _norm_shutter_type_g120(shutter_type)
    norm_silent = _norm_on_off_phase286(silent_mode)
    norm_flash = _norm_flash_mode_g120(requested_flash_mode)
    norm_exp_comp = _norm_exp_comp_set_g120(requested_exp_comp_set)
    norm_wless = _norm_on_off_phase286(wireless_flash)
    norm_redeye = _norm_on_off_phase286(red_eye_reduction)
    norm_vlight = _norm_video_light_mode_g120(requested_video_light_mode)
    norm_reset = _norm_reset_action_phase286(reset_action)

    iso_mode_ok = isinstance(iso_mode, str) and iso_mode.strip().upper() in (
        "MANUAL",
        "AUTO",
        "ISO AUTO",
    )
    nums_ok = (
        _is_real_int(requested_iso_value)
        and requested_iso_value > 0
        and _is_real_int(requested_iso_range_min)
        and _is_real_int(requested_iso_range_max)
        and _is_real_number(flash_comp_ev)
        and _is_real_number(mi_shoe_trigger_voltage_v)
        and mi_shoe_trigger_voltage_v >= 0.0
        and _is_real_number(shutter_speed_seconds)
        and shutter_speed_seconds > 0.0
    )
    bools_ok = all(
        isinstance(b, bool)
        for b in (
            flash_requested,
            mi_shoe_positive_polarity,
            hss_external_flash,
            claimed_iso_minss_active_in_movie_or_sq,
            claimed_cine_ei_allows_variable_iso,
            claimed_camera_reset_resets_iso_range_limit,
            claimed_camera_reset_resets_exp_comp_set,
            claimed_flash_allowed_in_movie_or_sq,
            claimed_flash_allowed_with_electronic_shutter,
            claimed_flash_allowed_with_silent_mode_on,
            claimed_fx6_has_still_flash_stack,
            claimed_video_light_blocked_in_movie,
        )
    )
    if (
        norm_shoot is None
        or norm_log is None
        or norm_min_ss is None
        or norm_shutter is None
        or norm_silent is None
        or norm_flash is None
        or norm_exp_comp is None
        or norm_wless is None
        or norm_redeye is None
        or norm_vlight is None
        or norm_reset is None
        or (not iso_mode_ok)
        or (not nums_ok)
        or (not bools_ok)
    ):
        _add_code(codes, STATUS_BLOCKED_G120_TELEMETRY_INVALID)
        errors.append("Invalid or unrecognized G120 telemetry or enum value.")

    resolved = resolve_fx3_iso_minss_and_flash_state(
        shoot_mode=norm_shoot or SHOOT_MODE_M_PHASE286,
        log_shooting=norm_log or LOG_SHOOTING_OFF_G120,
        iso_mode=iso_mode if iso_mode_ok else "Manual",
        requested_iso_value=(
            int(requested_iso_value) if _is_real_int(requested_iso_value) else 800
        ),
        requested_iso_range_min=(
            int(requested_iso_range_min)
            if _is_real_int(requested_iso_range_min)
            else ISO_DEFAULT_STILL_MIN_G120
        ),
        requested_iso_range_max=(
            int(requested_iso_range_max)
            if _is_real_int(requested_iso_range_max)
            else ISO_DEFAULT_STILL_MAX_G120
        ),
        requested_iso_auto_min_ss=norm_min_ss or ISO_AUTO_MIN_SS_FACTORY_DEFAULT_G120,
        shutter_type=norm_shutter or SHUTTER_TYPE_MECHANICAL_G120,
        silent_mode=norm_silent or "Off",
        flash_requested=bool(flash_requested),
        requested_flash_mode=norm_flash or FLASH_MODE_FACTORY_DEFAULT_G120,
        flash_comp_ev=float(flash_comp_ev) if _is_real_number(flash_comp_ev) else 0.0,
        requested_exp_comp_set=norm_exp_comp or EXP_COMP_SET_FACTORY_DEFAULT_G120,
        wireless_flash=norm_wless or "Off",
        red_eye_reduction=norm_redeye or "Off",
        shutter_speed_seconds=(
            float(shutter_speed_seconds)
            if _is_real_number(shutter_speed_seconds) and shutter_speed_seconds > 0.0
            else 1.0 / 125.0
        ),
        requested_video_light_mode=norm_vlight or VIDEO_LIGHT_FACTORY_DEFAULT_G120,
        reset_action=norm_reset or RESET_ACTION_NONE_PHASE286,
    )

    matrix = compute_iso_minss_and_flash_matrix()
    if not matrix["all_invariants_hold"]:
        _add_code(codes, STATUS_BLOCKED_G120_TELEMETRY_INVALID)
        errors.append("G120 384-state matrix verification failed.")

    # 1. [ISO AUTO Min. SS] Still P/A-Only & Cine EI Base ISO (800/12800) Lockout
    cine_ei_non_base_iso = (
        norm_log in CINE_EI_LOCKED_LOG_MODES_G120
        and _is_real_int(requested_iso_value)
        and requested_iso_value not in CINE_EI_BASE_ISOS_G120
    )
    non_default_min_ss_requested_in_movie_or_cine_ei = (
        norm_reset == RESET_ACTION_NONE_PHASE286
        and norm_min_ss != ISO_AUTO_MIN_SS_FACTORY_DEFAULT_G120
        and (
            norm_shoot in MOVIE_SHOOT_MODES_PHASE286
            or norm_log in CINE_EI_LOCKED_LOG_MODES_G120
        )
    )
    if (
        cine_ei_non_base_iso
        or non_default_min_ss_requested_in_movie_or_cine_ei
        or claimed_iso_minss_active_in_movie_or_sq
        or claimed_cine_ei_allows_variable_iso
    ):
        _add_code(codes, STATUS_BLOCKED_G120_ISO_MINSS_MOVIE_OR_CINE_EI_VIOLATION)
        errors.append(
            "[ISO AUTO Min. SS] (0x778b) operates strictly in Still P/A with [ISO AUTO] "
            "(inactive in Movie/S&Q); [Cine EI] / [Cine EI Quick] pins sensor recording "
            "sensitivity strictly to Base ISO 800 or Base ISO 12800."
        )

    # 2. [ISO Range Limit] Bounds & Reset Survival
    iso_bounds_bad = (
        _is_real_int(requested_iso_range_min)
        and _is_real_int(requested_iso_range_max)
        and (
            requested_iso_range_min < ISO_HARDWARE_MIN_G120
            or requested_iso_range_max > ISO_HARDWARE_MAX_G120
            or requested_iso_range_min > requested_iso_range_max
        )
    )
    manual_iso_out_of_range = (
        iso_mode_ok
        and iso_mode.strip().upper() == "MANUAL"
        and norm_log not in CINE_EI_LOCKED_LOG_MODES_G120
        and _is_real_int(requested_iso_value)
        and (
            requested_iso_value < resolved["effective_iso_range_min"]
            or requested_iso_value > resolved["effective_iso_range_max"]
        )
    )
    if (
        iso_bounds_bad
        or manual_iso_out_of_range
        or claimed_camera_reset_resets_iso_range_limit
        or claimed_camera_reset_resets_exp_comp_set
    ):
        _add_code(codes, STATUS_BLOCKED_G120_ISO_RANGE_OR_RESET_PERSISTENCE_VIOLATION)
        errors.append(
            "[ISO Range Limit] (0x72f8, 50..409600) constrains manual ISO and, like "
            "[Exp.comp.set] (0xe11a), survives [Camera Settings Reset] (needs [Initialize])."
        )

    # 3. Still-Only Mechanical-Shutter [Flash Mode] & <250V MI-Shoe Sync Guard
    flash_active_request = bool(flash_requested)
    flash_in_movie_or_eshutter = flash_active_request and (
        norm_shoot in MOVIE_SHOOT_MODES_PHASE286
        or norm_shutter == SHUTTER_TYPE_ELECTRONIC_G120
        or norm_silent == "On"
    )
    flash_sync_exceeded = (
        bool(flash_requested)
        and (not bool(hss_external_flash))
        and _is_real_number(shutter_speed_seconds)
        and float(shutter_speed_seconds) < (FX3_FLASH_SYNC_CEILING_SECONDS_G120 - 1e-9)
    )
    hv_or_polarity_unsafe = (
        _is_real_number(mi_shoe_trigger_voltage_v)
        and float(mi_shoe_trigger_voltage_v) >= FX3_MI_SHOE_MAX_SAFE_SYNC_VOLTAGE_V_G120
    ) or (not bool(mi_shoe_positive_polarity))
    if (
        flash_in_movie_or_eshutter
        or flash_sync_exceeded
        or hv_or_polarity_unsafe
        or claimed_flash_allowed_in_movie_or_sq
        or claimed_flash_allowed_with_electronic_shutter
        or claimed_flash_allowed_with_silent_mode_on
        or claimed_fx6_has_still_flash_stack
    ):
        _add_code(codes, STATUS_BLOCKED_G120_FLASH_MOVIE_ESHUTTER_OR_HV_SHOE_VIOLATION)
        errors.append(
            "[Flash Mode] (0xe5ce, VAL_HAITA_*_EXPOSURE_MODE_STILL) is strictly Still-only "
            "and Mechanical-Shutter-only (<= 1/250 s sync; locked out in Movie/S&Q, "
            "Electronic Shutter, and Silent Mode = On); MI-Shoe requires < 250 V "
            "positive-polarity sync, and FX6 has zero still flash stack."
        )

    # 4. [Flash Comp.] Bounds (-3.0..+3.0 EV) & [Video Light Mode] Active Scope
    fcomp_bad = _is_real_number(flash_comp_ev) and (
        float(flash_comp_ev) < FLASH_COMP_MIN_EV_G120 - 1e-9
        or float(flash_comp_ev) > FLASH_COMP_MAX_EV_G120 + 1e-9
    )
    if fcomp_bad or claimed_video_light_blocked_in_movie:
        _add_code(codes, STATUS_BLOCKED_G120_VIDEO_LIGHT_OR_FLASH_COMP_VIOLATION)
        errors.append(
            "[Flash Comp.] (0xe5d3) must stay within -3.0..+3.0 EV; [Video Light Mode] "
            "(0x6211) remains active across Still, Movie, and S&Q."
        )

    valid = not codes
    status = STATUS_VERIFIED_G120 if valid else codes[0]

    return IsoMinSsFlashGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}"
        if _is_real_int(body_model_id)
        else "invalid",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        fx6_comparison_fw_version=fx6_comparison_fw_version,
        reset_action=resolved["reset_action"],
        iso_range_limit_menu_path=ISO_RANGE_LIMIT_MENU_PATH_G120,
        iso_auto_min_ss_menu_path=ISO_AUTO_MIN_SS_MENU_PATH_G120,
        flash_mode_menu_path=FLASH_MODE_MENU_PATH_G120,
        video_light_mode_menu_path=VIDEO_LIGHT_MODE_MENU_PATH_G120,
        shoot_mode=resolved["shoot_mode"],
        log_shooting=resolved["log_shooting"],
        effective_iso_range_min=resolved["effective_iso_range_min"],
        effective_iso_range_max=resolved["effective_iso_range_max"],
        iso_range_limit_survived_cam_reset=resolved[
            "iso_range_limit_survived_cam_reset"
        ],
        cine_ei_base_iso_pinned=resolved["cine_ei_base_iso_pinned"],
        effective_base_iso=resolved["effective_base_iso"],
        requested_iso_auto_min_ss=norm_min_ss or str(requested_iso_auto_min_ss),
        effective_iso_auto_min_ss=resolved["effective_iso_auto_min_ss"],
        iso_auto_min_ss_active=resolved["iso_auto_min_ss_active"],
        shutter_type=norm_shutter or str(shutter_type),
        silent_mode=norm_silent or str(silent_mode),
        flash_requested=bool(flash_requested),
        requested_flash_mode=norm_flash or str(requested_flash_mode),
        effective_flash_mode=resolved["effective_flash_mode"],
        flash_available=resolved["flash_available"],
        flash_comp_ev=resolved["flash_comp_ev"],
        effective_exp_comp_set=resolved["effective_exp_comp_set"],
        exp_comp_set_survived_cam_reset=resolved["exp_comp_set_survived_cam_reset"],
        wireless_flash=resolved["wireless_flash"],
        red_eye_reduction=resolved["red_eye_reduction"],
        mi_shoe_trigger_voltage_v=(
            float(mi_shoe_trigger_voltage_v)
            if _is_real_number(mi_shoe_trigger_voltage_v)
            else -1.0
        ),
        mi_shoe_positive_polarity=bool(mi_shoe_positive_polarity),
        fx3_flash_sync_ceiling_denom=FX3_FLASH_SYNC_CEILING_DENOM_G120,
        shutter_speed_seconds=(
            float(shutter_speed_seconds)
            if _is_real_number(shutter_speed_seconds)
            else -1.0
        ),
        requested_video_light_mode=norm_vlight or str(requested_video_light_mode),
        effective_video_light_mode=resolved["effective_video_light_mode"],
        video_light_active_across_still_movie_sq=resolved[
            "video_light_active_across_still_movie_sq"
        ],
        fx6_still_flash_supported=False,
        fx6_flash_band_reduce_supported=True,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g120_iso_minss_and_flash_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    iso_minss_flash_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase286DonorAuditResult] = None,
) -> Tuple[GateVerdict, G120IsoMinSsFlashGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase286_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_iso_minss_and_flash_guard(**dict(iso_minss_flash_kwargs or {}))

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G120.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G120 if valid else codes[0]

    res = G120IsoMinSsFlashGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        iso_minss_flash_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, iso_range=({guard.effective_iso_range_min}.."
        f"{guard.effective_iso_range_max}), min_ss={guard.effective_iso_auto_min_ss}"
        f"(active={guard.iso_auto_min_ss_active},cine_ei_pin={guard.cine_ei_base_iso_pinned}), "
        f"flash={guard.effective_flash_mode}(avail={guard.flash_available},"
        f"sync<=1/{guard.fx3_flash_sync_ceiling_denom},v={guard.mi_shoe_trigger_voltage_v}V), "
        f"vlight={guard.effective_video_light_mode}, fx6_flash={guard.fx6_still_flash_supported}"
    )
    verdict = GateVerdict(
        gate_id=G120_GATE_ID,
        gate_code=G120_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `120`-Gate Milestone Master Safety Preflight (`G01..G120`)
# ---------------------------------------------------------------------------


def evaluate_120gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    focus_area_zoom_kwargs: Optional[Mapping[str, Any]] = None,
    iso_minss_flash_kwargs: Optional[Mapping[str, Any]] = None,
    master_118_override: Optional[Master118GateReport] = None,
    **m118_passthrough_kwargs: Any,
) -> Master120GateReport:
    """Evaluate all 120 Master Safety Gates (`G01..G120`) deterministically by
    delegating `G01..G118` directly to `evaluate_118gate_preflight()`.
    """
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        or simulate_bench_dry_run
        or bool(dry_run_simulated_backup)
    )

    m118_report: Master118GateReport = (
        master_118_override
        if master_118_override is not None
        else evaluate_118gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m118_passthrough_kwargs,
        )
    )

    phase286_audit = audit_phase286_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g119_verdict, g119_res = evaluate_g119_focus_area_and_zoom_lever_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        focus_area_zoom_kwargs=focus_area_zoom_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase286_audit,
    )

    g120_verdict, g120_res = evaluate_g120_iso_minss_and_flash_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        iso_minss_flash_kwargs=iso_minss_flash_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase286_audit,
    )

    gates_119_to_120 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g119_verdict, g120_verdict)
    ]
    all_gates = tuple(list(m118_report.gates) + gates_119_to_120)

    g01_to_g12_verified = int(m118_report.summary["g01_to_g12_verified"])
    g13_to_g118_verified = int(m118_report.summary["g13_to_g116_verified"]) + int(
        m118_report.summary["g117_to_g118_verified"]
    )
    g119_to_g120_verified = sum(1 for v in (g119_verdict, g120_verdict) if v.passed)
    total_verified = (
        g01_to_g12_verified + g13_to_g118_verified + g119_to_g120_verified
    )

    g119_to_g120_all_passed = g119_to_g120_verified == 2
    g13_to_g120_all_passed = (
        m118_report.g13_to_g118_all_passed and g119_to_g120_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m118_report.gates[:9])

    offline_117_verified = (
        g01_to_g09_ok
        and m118_report.offline_115_gates_verified
        and g119_to_g120_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_120_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g120_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m118_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_117_verified
        and m118_report.h0_h1_trial_entry_allowed
        and g119_to_g120_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m118_report.errors)
        + list(g119_verdict.errors)
        + list(g120_verdict.errors)
    )
    warnings: List[str] = (
        list(m118_report.warnings)
        + list(g119_verdict.warnings)
        + list(g120_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m118_report.g13_to_g118_all_passed:
        overall_status = m118_report.status
    elif not g119_verdict.passed:
        overall_status = g119_verdict.status
    elif not g120_verdict.passed:
        overall_status = g120_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_120_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_120_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_120_verified:
        overall_status = "VERIFIED_ALL_120_GATES"
    else:
        overall_status = "VERIFIED_117_OF_120_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m118_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g119_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g120_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 120,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 120 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g118_verified": g13_to_g118_verified,
        "g119_to_g120_verified": g119_to_g120_verified,
        "g13_to_g120_all_passed": g13_to_g120_all_passed,
        "g119_to_g120_all_passed": g119_to_g120_all_passed,
        "offline_117_gates_verified": offline_117_verified,
        "all_120_gates_verified": all_120_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "human_hardware_attach_token": HUMAN_HARDWARE_ATTACH_TOKEN,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master120GateReport(
        schema=REALHW_FOCUS_AREA_ZOOM_LEVER_ISO_MINSS_FLASH_120GATE_SCHEMA,
        version=REALHW_FOCUS_AREA_ZOOM_LEVER_ISO_MINSS_FLASH_120GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_117_gates_verified=offline_117_verified,
        all_120_gates_verified=all_120_verified,
        g13_to_g120_all_passed=g13_to_g120_all_passed,
        g119_to_g120_all_passed=g119_to_g120_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_118_report=m118_report.to_dict(),
        g119_result=g119_res.to_dict(),
        g120_result=g120_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_120_master_safety_gates = evaluate_120gate_preflight
run_120_gate_preflight = evaluate_120gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard",
        description=(
            "Phase 286 (120/120 Safety Gates Milestone!, Wave-50) Gates G119 "
            "(14-Option [Focus Area], [AF Area Registration] / [Focus Area Limit], "
            "XLR-H1 No-Zoom-Lever Myth-Bust & [Zoom Lever Speed]/[Remote Zoom Speed] "
            "1..8 vs FX6 0..99 Indicator) + G120 ([ISO Range Limit] / [ISO AUTO Min. SS] "
            "vs Cine EI Base-ISO Lockout & Still-Only Mechanical-Shutter [Flash Mode] "
            "< 250V MI-Shoe Sync Guard vs Movie [Video Light Mode]) + Unified "
            "120-Gate Master Safety Preflight"
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
    )
    parser.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_120gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        try:
            sys.stdout.write(
                json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
            )
            sys.stdout.flush()
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            os.close(devnull)
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/120 "
            f"g119_to_g120_all_passed={report.g119_to_g120_all_passed} "
            f"all_120_gates_verified={report.all_120_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = (
        report.all_120_gates_verified
        if args.dry_run_simulated
        else report.offline_117_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
