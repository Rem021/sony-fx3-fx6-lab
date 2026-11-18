"""Phase 280 (Task H321 Milestone, 116/116 Safety Gates, Wave-48) Sony `ILME-FX3`
(`Ver. 7.02`, `ilc/2210`) vs `ILME-FX6` (`Ver. 6.01`) Safety Gates `G115`
(`[Picture Profile]` Out-of-Box `PP11` `S-Cinetone` Default vs `[Creative Look]`
10 Looks & `[D-Range Optimizer]` Mutual Exclusivity under `[Log Shooting]`,
`PPLUT1..4` Movie-Only / `1080p` HDMI Clamp & `[PPx] -> [Reset]` Internal-Param
Survival Trap) & `G116` (`[White Balance]` `2500K..9900K`, `Custom 1..3`,
`Cine EI` AWB Lockout, `Custom Setup` Error Guard & `[Metering Mode]` 6 Modes,
`De-Squeeze` Face-Priority Lockout & `Cine EI` Base ISO `M.M.` Invariance) +
Unified `116`-Gate Master Safety Preflight (`G01..G116`).

Operationalizes Wave-48 official Sony `ILME-FX3` (`Ver. 7.02`, Help Guide
`ilc/2210`) & `ILME-FX6` (`Ver. 6.01`) intelligence
(`reports/2026-11-17-global-sony-wave48-picture-profile-scinetone-creative-look-dro-wb-metering-intel/README.md`)
as deterministic offline preflight verifiers (`G115` and `G116`) and delegates
`G01..G114` directly to `evaluate_114gate_preflight()`.
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
from .realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard import (
    Master114GateReport,
    evaluate_114gate_preflight,
)
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_PP_SCINETONE_CREATIVELOOK_DRO_WB_METERING_116GATE_SCHEMA: str = (
    "realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard_v1"
)
REALHW_PP_SCINETONE_CREATIVELOOK_DRO_WB_METERING_116GATE_VERSION: str = "1.0.0"

G115_GATE_ID: str = (
    "G115_picture_profile_scinetone_creative_look_dro_and_log_shooting_guard"
)
G115_GATE_CODE: str = (
    "PICTURE_PROFILE_SCINETONE_CREATIVE_LOOK_DRO_AND_LOG_SHOOTING_GUARD"
)

G116_GATE_ID: str = (
    "G116_white_balance_cine_ei_custom_setup_and_metering_mode_guard"
)
G116_GATE_CODE: str = (
    "WHITE_BALANCE_CINE_EI_CUSTOM_SETUP_AND_METERING_MODE_GUARD"
)

G115: str = G115_GATE_ID
G116: str = G116_GATE_ID
GATE_G115_PICTURE_PROFILE_SCINETONE_CREATIVE_LOOK_DRO_AND_LOG_SHOOTING_GUARD: str = (
    G115_GATE_CODE
)
GATE_G116_WHITE_BALANCE_CINE_EI_CUSTOM_SETUP_AND_METERING_MODE_GUARD: str = (
    G116_GATE_CODE
)

ENV_CLEAN_ROOM_TEST_PHASE280: str = "FX3_CLEAN_ROOM_TEST"

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE280: float = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE280: float = 1.00
DONOR_CHECK_MAX_SECONDS: float = DONOR_CHECK_MAX_SECONDS_PHASE280

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX6_MODEL_NAME_PHASE280: str = "ILME-FX6"
FX3_DEFAULT_FW_VERSION_PHASE280: str = "7.02"
FX6_DEFAULT_FW_VERSION_PHASE280: str = "6.01"
FX3_HELP_GUIDE_CODE_PHASE280: str = "ilc/2210"

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE280: str = "Reset Network Set."
RESET_ACTION_INITIALIZE: str = "Initialize"
RESET_ACTION_PP_SLOT_RESET_PHASE280: str = "PPx Reset"
ALLOWED_RESET_ACTIONS_PHASE280: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_RESET_NETWORK_SET_PHASE280,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_PP_SLOT_RESET_PHASE280,
)

SHOOT_MODE_MOVIE_PHASE280: str = "Movie"
SHOOT_MODE_STILL_PHASE280: str = "Still"
SHOOT_MODE_SQ_PHASE280: str = "S&Q"
SHOOT_MODE_INTELLIGENT_AUTO_PHASE280: str = "Intelligent Auto"
ALLOWED_SHOOT_MODES_PHASE280: Tuple[str, ...] = (
    SHOOT_MODE_MOVIE_PHASE280,
    SHOOT_MODE_STILL_PHASE280,
    SHOOT_MODE_SQ_PHASE280,
    SHOOT_MODE_INTELLIGENT_AUTO_PHASE280,
)

# ---------------------------------------------------------------------------
# Status & Violation Codes (G115 / G116 / Phase 280)
# ---------------------------------------------------------------------------

STATUS_VERIFIED_G115: str = "VERIFIED_G115_PP_SCINETONE_CREATIVELOOK_DRO_AND_LOG_SAFE"
STATUS_VERIFIED_G116: str = "VERIFIED_G116_WB_CINEEI_CUSTOM_SETUP_AND_METERING_SAFE"
STATUS_BLOCKED_PHASE280_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE280_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G115_PP_CREATIVELOOK_DRO_MUTUAL_EXCLUSION_VIOLATION: str = (
    "BLOCKED_G115_PP_CREATIVELOOK_DRO_MUTUAL_EXCLUSION_VIOLATION"
)
STATUS_BLOCKED_G115_LOG_SHOOTING_DOUBLE_PP_CORRUPTION_VIOLATION: str = (
    "BLOCKED_G115_LOG_SHOOTING_DOUBLE_PP_CORRUPTION_VIOLATION"
)
STATUS_BLOCKED_G115_PP_INTERNAL_PARAM_UNRESET_TRAP: str = (
    "BLOCKED_G115_PP_INTERNAL_PARAM_UNRESET_TRAP"
)
STATUS_BLOCKED_G115_PPLUT_STILL_OR_HDMI_CLAMP_VIOLATION: str = (
    "BLOCKED_G115_PPLUT_STILL_OR_HDMI_CLAMP_VIOLATION"
)
STATUS_BLOCKED_G115_TELEMETRY_INVALID: str = (
    "BLOCKED_G115_PP_CREATIVELOOK_DRO_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G116_CINE_EI_AWB_VIOLATION: str = (
    "BLOCKED_G116_CINE_EI_AWB_VIOLATION"
)
STATUS_BLOCKED_G116_LOG_CUSTOM_WB_CAPTURE_TRAP: str = (
    "BLOCKED_G116_LOG_CUSTOM_WB_CAPTURE_TRAP"
)
STATUS_BLOCKED_G116_METERING_OR_CINE_EI_BASE_ISO_VIOLATION: str = (
    "BLOCKED_G116_METERING_OR_CINE_EI_BASE_ISO_VIOLATION"
)
STATUS_BLOCKED_G116_WB_OR_METERING_RESET_CAMSET_BOUNDARY_VIOLATION: str = (
    "BLOCKED_G116_WB_OR_METERING_RESET_CAMSET_BOUNDARY_VIOLATION"
)
STATUS_BLOCKED_G116_TELEMETRY_INVALID: str = (
    "BLOCKED_G116_WB_AND_METERING_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G115 Constants: [Picture Profile] PP11, [Creative Look], [DRO], [Log Shooting]
# ---------------------------------------------------------------------------

PICTURE_PROFILE_MENU_PATH_G115: str = (
    "MENU -> Exposure/Color -> [Color/Tone] -> [Picture Profile]"
)
DIFFERENT_SET_STILL_MV_MENU_PATH_G115: str = (
    "MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]"
)
CREATIVE_LOOK_MENU_PATH_G115: str = (
    "MENU -> Exposure/Color -> [Color/Tone] -> [Creative Look]"
)
DRO_MENU_PATH_G115: str = (
    "MENU -> Exposure/Color -> [Exposure Comp.] -> [D-Range Optimizer]"
)
LOG_SHOOTING_MENU_PATH_G115: str = (
    "MENU -> Shooting -> [Image Quality/Rec] -> [Log Shooting Setting]"
)

PICTURE_PROFILE_UXC_RESID16_G115: int = 0x6830
PICTURE_PROFILE_PP11_RESID16_G115: int = 0x67AB
SCINETONE_RESID16_G115: int = 0x6E61
DIFFERENT_SET_RESID16_G115: int = 0x62EE
CREATIVE_LOOK_UXC_RESID16_G115: int = 0x6823
CREATIVE_LOOK_ST_RESID16_G115: int = 0x770C
CREATIVE_LOOK_VV2_RESID16_G115: int = 0x7864
CREATIVE_LOOK_SE_RESID16_G115: int = 0x7702
DRO_UXC_RESID16_G115: int = 0xE89C
DRO_AUTO_RESID16_G115: int = 0xEA04
LOG_SHOOTING_UXC_RESID16_G115: int = 0x6020
SELECT_LUT_RESID16_G115: int = 0x643E
SELECT_LUT_S709_RESID16_G115: int = 0x6A3E
DISPLAY_LUT_RESID16_G115: int = 0x729A

PP_OFF_G115: str = "Off"
PP_FACTORY_DEFAULT_G115: str = "PP11"
PP_1_TO_11_G115: Tuple[str, ...] = (
    "PP1",
    "PP2",
    "PP3",
    "PP4",
    "PP5",
    "PP6",
    "PP7",
    "PP8",
    "PP9",
    "PP10",
    "PP11",
)
PPLUT_PICTURE_PROFILES_G115: Tuple[str, ...] = (
    "PPLUT1",
    "PPLUT2",
    "PPLUT3",
    "PPLUT4",
)
SLOG3_PICTURE_PROFILES_G115: Tuple[str, ...] = ("PP8", "PP9")
ALLOWED_PICTURE_PROFILES_G115: Tuple[str, ...] = (
    (PP_OFF_G115,) + PP_1_TO_11_G115 + PPLUT_PICTURE_PROFILES_G115
)

PICTURE_PROFILE_DEFAULT_CURVES_G115: Dict[str, Tuple[str, str]] = {
    "Off": ("None", "None"),
    "PP1": ("Movie", "Movie"),
    "PP2": ("Still", "Still"),
    "PP3": ("ITU709", "ITU709"),
    "PP4": ("ITU709", "ITU709"),
    "PP5": ("Cine1", "Cinema"),
    "PP6": ("Cine2", "Cinema"),
    "PP7": ("S-Log2", "S-Gamut"),
    "PP8": ("S-Log3", "S-Gamut3.Cine"),
    "PP9": ("S-Log3", "S-Gamut3"),
    "PP10": ("HLG2", "BT.2020"),
    "PP11": ("S-Cinetone", "S-Cinetone"),
    "PPLUT1": ("User .cube LUT", "User .cube LUT"),
    "PPLUT2": ("User .cube LUT", "User .cube LUT"),
    "PPLUT3": ("User .cube LUT", "User .cube LUT"),
    "PPLUT4": ("User .cube LUT", "User .cube LUT"),
}
DIFFERENT_SET_PP_DEFAULT_CHECKED_G115: bool = False

CREATIVE_LOOK_10_PRESETS_G115: Tuple[str, ...] = (
    "ST",
    "PT",
    "NT",
    "VV",
    "VV2",
    "FL",
    "IN",
    "SH",
    "BW",
    "SE",
)
CREATIVE_LOOK_CUSTOM_SLOTS_G115: Tuple[str, ...] = (
    "CREATIVE_BOX_1",
    "CREATIVE_BOX_2",
    "CREATIVE_BOX_3",
    "CREATIVE_BOX_4",
    "CREATIVE_BOX_5",
    "CREATIVE_BOX_6",
)
CREATIVE_LOOK_FACTORY_DEFAULT_G115: str = "ST"
CREATIVE_LOOK_LOCKED_VALUE_G115: str = "-"
ALLOWED_CREATIVE_LOOKS_G115: Tuple[str, ...] = (
    CREATIVE_LOOK_10_PRESETS_G115
    + CREATIVE_LOOK_CUSTOM_SLOTS_G115
    + (CREATIVE_LOOK_LOCKED_VALUE_G115,)
)
CREATIVE_LOOK_8_PARAMS_G115: Tuple[str, ...] = (
    "Contrast",
    "Highlights",
    "Shadows",
    "Fade",
    "Saturation",
    "Sharpness",
    "Sharpness Range",
    "Clarity",
)

DRO_OFF_G115: str = "Off"
DRO_AUTO_G115: str = "Auto"
DRO_LV1_TO_LV5_G115: Tuple[str, ...] = ("Lv1", "Lv2", "Lv3", "Lv4", "Lv5")
ALLOWED_DRO_MODES_G115: Tuple[str, ...] = (
    DRO_OFF_G115,
    DRO_AUTO_G115,
) + DRO_LV1_TO_LV5_G115
DRO_FACTORY_DEFAULT_G115: str = DRO_AUTO_G115

LOG_SHOOTING_OFF_G115: str = "Off"
LOG_SHOOTING_FLEXIBLE_ISO_G115: str = "Flexible ISO"
LOG_SHOOTING_CINE_EI_QUICK_G115: str = "Cine EI Quick"
LOG_SHOOTING_CINE_EI_G115: str = "Cine EI"
ALLOWED_LOG_SHOOTING_MODES_G115: Tuple[str, ...] = (
    LOG_SHOOTING_OFF_G115,
    LOG_SHOOTING_FLEXIBLE_ISO_G115,
    LOG_SHOOTING_CINE_EI_QUICK_G115,
    LOG_SHOOTING_CINE_EI_G115,
)
SELECT_LUT_FACTORY_DEFAULT_G115: str = "s709"
FX6_BASE_LOOK_CUSTOM_DEFAULT_G115: str = "S-Cinetone"

HDMI_RES_AUTO_G115: str = "Auto"
HDMI_RES_2160P_G115: str = "2160p"
HDMI_RES_1080P_G115: str = "1080p"
HDMI_RES_1080I_G115: str = "1080i"
ALLOWED_HDMI_OUT_RESOLUTIONS_G115: Tuple[str, ...] = (
    HDMI_RES_AUTO_G115,
    HDMI_RES_2160P_G115,
    HDMI_RES_1080P_G115,
    HDMI_RES_1080I_G115,
)

# ---------------------------------------------------------------------------
# Gate G116 Constants: [White Balance] & [Metering Mode]
# ---------------------------------------------------------------------------

WHITE_BALANCE_MENU_PATH_G116: str = (
    "MENU -> Exposure/Color -> [White Balance] -> [White Balance]"
)
PRIORITY_SET_IN_AWB_MENU_PATH_G116: str = (
    "MENU -> Exposure/Color -> [White Balance] -> [Priority Set in AWB]"
)
SHUTTER_AWB_LOCK_MENU_PATH_G116: str = (
    "MENU -> Exposure/Color -> [White Balance] -> [Shutter AWB Lock]"
)
SHOCKLESS_WB_MENU_PATH_G116: str = (
    "MENU -> Exposure/Color -> [White Balance] -> [Shockless WB]"
)
METERING_MODE_MENU_PATH_G116: str = (
    "MENU -> Exposure/Color -> [Metering] -> [Metering Mode]"
)
FACE_PRIORITY_MULTI_METERING_MENU_PATH_G116: str = (
    "MENU -> Exposure/Color -> [Metering] -> [Face Priority in Multi Metering]"
)
SPOT_METERING_POINT_MENU_PATH_G116: str = (
    "MENU -> Exposure/Color -> [Metering] -> [Spot Metering Point]"
)
AEL_W_SHUTTER_MENU_PATH_G116: str = (
    "MENU -> Exposure/Color -> [Metering] -> [AEL w/ Shutter]"
)

WHITE_BALANCE_UXC_RESID16_G116: int = 0xE5D4
WHITE_BALANCE_AUTO_RESID16_G116: int = 0xE6DA
CTEMP_FILTER_UXC_RESID16_G116: int = 0xE2AC
CUSTOM_WB_1_RESID16_G116: int = 0xE79D
CUSTOM_WB_2_RESID16_G116: int = 0xE79B
CUSTOM_WB_3_RESID16_G116: int = 0xE79C
PRIORITY_AWB_RESID16_G116: int = 0x67A7
SHUTTER_AWB_LOCK_RESID16_G116: int = 0x66DB
SHOCKLESS_WB_RESID16_G116: int = 0x62FE

METERING_MODE_UXC_RESID16_G116: int = 0xE5CF
FACE_PRIORITY_MULTI_RESID16_G116: int = 0x69C7
SPOT_METERING_POINT_RESID16_G116: int = 0x71B5
SPOT_METERING_CENTER_RESID16_G116: int = 0x7080
SPOT_METERING_LINK_RESID16_G116: int = 0x625C
AEL_W_SHUTTER_RESID16_G116: int = 0x669D

WB_AUTO_G116: str = "Auto"
WB_UNDERWATER_AUTO_G116: str = "Underwater Auto"
WB_FLASH_G116: str = "Flash"
WB_CTEMP_FILTER_G116: str = "C.Temp./Filter"
WB_CUSTOM_1_G116: str = "Custom 1"
WB_CUSTOM_2_G116: str = "Custom 2"
WB_CUSTOM_3_G116: str = "Custom 3"
WB_CUSTOM_SLOTS_G116: Tuple[str, ...] = (
    WB_CUSTOM_1_G116,
    WB_CUSTOM_2_G116,
    WB_CUSTOM_3_G116,
)
WB_FIXED_PRESETS_G116: Tuple[str, ...] = (
    "Daylight",
    "Shade",
    "Cloudy",
    "Incandescent",
    "Fluor.: Warm White",
    "Fluor.: Cool White",
    "Fluor.: Day White",
    "Fluor.: Daylight",
    WB_FLASH_G116,
    WB_UNDERWATER_AUTO_G116,
)
ALLOWED_WHITE_BALANCE_MODES_G116: Tuple[str, ...] = (
    (WB_AUTO_G116,)
    + WB_FIXED_PRESETS_G116
    + (WB_CTEMP_FILTER_G116,)
    + WB_CUSTOM_SLOTS_G116
)
WB_FACTORY_DEFAULT_G116: str = WB_AUTO_G116
WB_AWB_BLOCKED_IN_CINE_EI_G116: Tuple[str, ...] = (
    WB_AUTO_G116,
    WB_UNDERWATER_AUTO_G116,
)

WB_CTEMP_MIN_K_G116: int = 2500
WB_CTEMP_MAX_K_G116: int = 9900
WB_CTEMP_STEP_K_G116: int = 100
WB_CTEMP_TOTAL_STEPS_G116: int = 75
WB_FINE_TRIM_MIN_G116: int = -7
WB_FINE_TRIM_MAX_G116: int = 7

PRIORITY_AWB_STANDARD_G116: str = "Standard"
PRIORITY_AWB_AMBIENCE_G116: str = "Ambience"
PRIORITY_AWB_WHITE_G116: str = "White"
ALLOWED_PRIORITY_AWB_MODES_G116: Tuple[str, ...] = (
    PRIORITY_AWB_STANDARD_G116,
    PRIORITY_AWB_AMBIENCE_G116,
    PRIORITY_AWB_WHITE_G116,
)
PRIORITY_AWB_FACTORY_DEFAULT_G116: str = PRIORITY_AWB_STANDARD_G116

SHUTTER_AWB_LOCK_HALF_PRESS_G116: str = "Shutter Half Press"
SHUTTER_AWB_LOCK_CONT_SHOOTING_G116: str = "Cont. Shooting"
SHUTTER_AWB_LOCK_OFF_G116: str = "Off"
ALLOWED_SHUTTER_AWB_LOCK_MODES_G116: Tuple[str, ...] = (
    SHUTTER_AWB_LOCK_HALF_PRESS_G116,
    SHUTTER_AWB_LOCK_CONT_SHOOTING_G116,
    SHUTTER_AWB_LOCK_OFF_G116,
)
SHUTTER_AWB_LOCK_FACTORY_DEFAULT_G116: str = SHUTTER_AWB_LOCK_OFF_G116

SHOCKLESS_WB_OFF_G116: str = "Off"
SHOCKLESS_WB_1_FAST_G116: str = "1 (Fast)"
SHOCKLESS_WB_2_G116: str = "2"
SHOCKLESS_WB_3_SLOW_G116: str = "3 (Slow)"
ALLOWED_SHOCKLESS_WB_MODES_G116: Tuple[str, ...] = (
    SHOCKLESS_WB_OFF_G116,
    SHOCKLESS_WB_1_FAST_G116,
    SHOCKLESS_WB_2_G116,
    SHOCKLESS_WB_3_SLOW_G116,
)
SHOCKLESS_WB_FACTORY_DEFAULT_G116: str = SHOCKLESS_WB_1_FAST_G116

FX6_PRESET_CUSTOM_KELVINS_G116: Tuple[int, ...] = (3200, 4300, 5600, 6300)
FX6_PRESET_CINE_EI_KELVINS_G116: Tuple[int, ...] = (3200, 4300, 5500)

METERING_MODE_MULTI_G116: str = "Multi"
METERING_MODE_CENTER_G116: str = "Center"
METERING_MODE_SPOT_STANDARD_G116: str = "Spot: Standard"
METERING_MODE_SPOT_LARGE_G116: str = "Spot: Large"
METERING_MODE_ENTIRE_SCREEN_AVG_G116: str = "Entire Screen Avg."
METERING_MODE_HIGHLIGHT_G116: str = "Highlight"
FX3_EXACT_6_METERING_MODES_G116: Tuple[str, ...] = (
    METERING_MODE_MULTI_G116,
    METERING_MODE_CENTER_G116,
    METERING_MODE_SPOT_STANDARD_G116,
    METERING_MODE_SPOT_LARGE_G116,
    METERING_MODE_ENTIRE_SCREEN_AVG_G116,
    METERING_MODE_HIGHLIGHT_G116,
)
METERING_MODE_FACTORY_DEFAULT_G116: str = METERING_MODE_MULTI_G116

FACE_PRIORITY_MULTI_ON_G116: str = "On"
FACE_PRIORITY_MULTI_OFF_G116: str = "Off"
FACE_PRIORITY_MULTI_DEFAULT_G116: str = FACE_PRIORITY_MULTI_ON_G116
ALLOWED_DESQUEEZE_MODES_G116: Tuple[str, ...] = (
    "Off",
    "1.3x",
    "1.33x",
    "1.5x",
    "1.6x",
    "1.8x",
    "2.0x",
)

SPOT_METERING_POINT_CENTER_G116: str = "Center"
SPOT_METERING_POINT_FOCUS_LINK_G116: str = "Focus Point Link"
ALLOWED_SPOT_METERING_POINTS_G116: Tuple[str, ...] = (
    SPOT_METERING_POINT_CENTER_G116,
    SPOT_METERING_POINT_FOCUS_LINK_G116,
)
SPOT_METERING_POINT_DEFAULT_G116: str = SPOT_METERING_POINT_CENTER_G116

SPOT_METERING_CENTER_LOCKED_FOCUS_AREAS_G116: Tuple[str, ...] = (
    "Wide",
    "Zone",
    "Center Fix",
)
SPOT_METERING_LINKABLE_FOCUS_AREAS_G116: Tuple[str, ...] = (
    "Spot: S",
    "Spot: M",
    "Spot: L",
    "Expand Spot",
    "Tracking: Spot S",
    "Tracking: Spot M",
    "Tracking: Spot L",
    "Tracking: Expand Spot",
)
ALLOWED_FOCUS_AREAS_G116: Tuple[str, ...] = (
    SPOT_METERING_CENTER_LOCKED_FOCUS_AREAS_G116 + SPOT_METERING_LINKABLE_FOCUS_AREAS_G116
)

AEL_W_SHUTTER_AUTO_G116: str = "Auto"
AEL_W_SHUTTER_ON_G116: str = "On"
AEL_W_SHUTTER_OFF_G116: str = "Off"
ALLOWED_AEL_W_SHUTTER_MODES_G116: Tuple[str, ...] = (
    AEL_W_SHUTTER_AUTO_G116,
    AEL_W_SHUTTER_ON_G116,
    AEL_W_SHUTTER_OFF_G116,
)
AEL_W_SHUTTER_DEFAULT_G116: str = AEL_W_SHUTTER_AUTO_G116

CINE_EI_BASE_ISOS_G116: Tuple[int, ...] = (800, 12800)
EXP_STD_ADJUST_MIN_EV_G116: float = -1.0
EXP_STD_ADJUST_MAX_EV_G116: float = 1.0

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, Targeted Pread on appFw.so, <0.20s)
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE280: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (62_688_361, b"BKID_APP_setting_picture_profile"),
    (62_724_006, b"BKID_APP_setting_picture_profile_movie"),
    (62_723_925, b"BKID_APP_setting_picture_profile_still"),
    (62_620_794, b"CAUTION_ID_FACTOR_GAMMA_SCINETONE_MSG"),
    (62_675_859, b"BKID_APP_setting_different_set"),
    (62_688_217, b"BKID_APP_setting_creative_style_plus"),
    (61_613_625, b"CREATIVE_BOX_1"),
    (62_688_172, b"BKID_APP_setting_dro"),
    (62_709_958, b"BKID_APP_setting_dro_d_range_optimizer"),
    (62_675_946, b"BKID_APP_setting_log_shooting"),
    (62_688_430, b"BKID_APP_setting_select_lut"),
    (62_687_866, b"BKID_APP_setting_white_balance"),
    (50_025_826, b"WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_2500K"),
    (50_029_082, b"WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_9900K"),
    (62_687_931, b"BKID_APP_setting_priority_set_in_awb"),
    (62_688_008, b"BKID_APP_setting_stl_awb_lock_with_shutter"),
    (62_688_097, b"BKID_APP_setting_movie_shockless_wb"),
    (62_687_020, b"BKID_APP_setting_metering_mode"),
    (62_687_085, b"BKID_APP_setting_face_detection_in_multi"),
    (62_687_170, b"BKID_APP_setting_spot_metering_link_to_focus_point"),
    (62_687_275, b"BKID_APP_setting_still_image_ael_w_shutter"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE280: str = (
    "75212aef523a945536f70f0902403a4f95e9b2dfd6e2528ad3b86e5a67642e35"
)

PINNED_FX6_APPFW_SLICES_PHASE280: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (40_955_328, b"BKID_APP_USER_MENU_BASE_LOOK0"),
    (40_940_425, b"BKID_APP_SETTING_BASE_LOOK_LUT_DISPLAY"),
    (40_997_628, b"BKID_APP_EXTERN_WHITEMEMORYA_ND1"),
    (40_928_795, b"BKID_APP_SETTING_ATW_MODE"),
    (40_922_041, b"BKID_APP_SETTING_MOVIE_SHOCKLESS_WB"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE280: str = (
    "9b172e4557d92e55848d0d7ed7f25ee3ce3d61c48fb22deb6a4c8a2cfa5eb5ad"
)

PINNED_PHASE280_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE280,
        tuple(tok for _off, tok in PINNED_FX3_APPFW_SLICES_PHASE280),
        "FX3_APPFW_WAVE48_PP_CREATIVELOOK_DRO_WB_METERING_SLICES",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Picture Profile",
            b"PP11",
            b"S-Cinetone",
            b"Different Set for Still/Mv",
            b"Creative Look",
            b"Log Shooting",
            b"Cine EI",
            b"Cine EI Quick",
            b"Flexible ISO",
            b"Select LUT",
            b"Priority Set in AWB",
            b"Shutter AWB Lock",
            b"Shockless WB",
            b"Spot: Standard",
            b"Spot: Large",
            b"Entire Screen Avg.",
            b"Highlight",
            b"Face Priority in Multi Metering",
            b"Spot Metering Point",
            b"Focus Point Link",
            b"AEL w/ Shutter",
        ),
        "FX3_UXC_F_PP_SCINETONE_CREATIVELOOK_WB_METERING_STRINGS",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (b"PP11", b"S-Cinetone", b"Log", b"AWB", b"WB"),
        "FX3_UXC_F_ZHCN_RESID16_PARITY",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (b"PP11", b"S-Cinetone", b"Log", b"AWB", b"WB"),
        "FX3_UXC_F_ZHTW_RESID16_PARITY",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (b"PP11", b"S-Cinetone", b"Log", b"AWB", b"WB"),
        "FX3_UXC_F_JA_RESID16_PARITY",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"D-Range Optimizer",
            b"White Balance",
            b"Custom 1",
            b"Custom 2",
            b"Custom 3",
            b"C.Temp./Filter",
            b"Metering Mode",
            b"Multi",
            b"Center",
            b"Cloudy",
            b"Shade",
        ),
        "FX3_UXC_DRO_WB_METERING_STRINGS",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (b"Gamma Display Assist", b"Color/Tone", b"Exposure/Color"),
        "FX3_UXC_G_GAMMA_ASSIST_COLOR_TONE",
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
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE280,
        tuple(tok for _off, tok in PINNED_FX6_APPFW_SLICES_PHASE280),
        "FX6_APPFW_WAVE48_BASE_LOOK_WB_ATW_SLICES",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (b"S-Cinetone", b"Base Look", b"709tone", b"HLG Live", b"ATW"),
        "FX6_UXC_BASE_LOOK_SCINETONE_ATW",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (b"Memory A", b"Memory B", b"3200K", b"5500K", b"Shockless White"),
        "FX6_UXC_2_MEMORY_AB_PRESET_SHOCKLESS",
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase280DonorAuditResult:
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
class PpScinetoneCreativeLookDroGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    reset_action: str
    picture_profile_menu_path: str
    different_set_menu_path: str
    creative_look_menu_path: str
    dro_menu_path: str
    log_shooting_menu_path: str
    shoot_mode: str
    log_shooting: str
    fx3_oob_picture_profile_default: str
    fx3_creative_look_10_presets: Tuple[str, ...]
    fx3_creative_look_8_params: Tuple[str, ...]
    different_set_pp_checked: bool
    requested_picture_profile: str
    effective_picture_profile: str
    effective_picture_profile_still: str
    effective_creative_look: str
    effective_dro: str
    effective_gamma_display_assist: str
    effective_select_lut: str
    effective_hdmi_output_resolution: str
    internal_recording_active: bool
    hlg_still_image: bool
    pp_internal_params_customized: bool
    pp_explicit_slot_reset_invoked: bool
    pp_internal_params_cleared: bool
    creative_look_and_dro_locked: bool
    double_log_or_baked_look_blocked: bool
    pplut_hdmi_1080p_clamped: bool
    fx6_base_look_custom_default: str
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G115PpScinetoneCreativeLookDroGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    pp_scinetone_creativelook_dro_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WbCineEiAndMeteringGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    reset_action: str
    white_balance_menu_path: str
    priority_awb_menu_path: str
    shutter_awb_lock_menu_path: str
    shockless_wb_menu_path: str
    metering_mode_menu_path: str
    face_priority_multi_menu_path: str
    spot_metering_point_menu_path: str
    ael_w_shutter_menu_path: str
    shoot_mode: str
    log_shooting: str
    picture_profile: str
    requested_white_balance: str
    effective_white_balance: str
    color_temp_k: int
    wb_ab_trim: int
    wb_gm_trim: int
    effective_priority_set_in_awb: str
    effective_shutter_awb_lock: str
    effective_shockless_wb: str
    custom_wb_slots_memorized_after_reset: bool
    custom_wb_excluded_from_camset: bool
    custom_wb_setup_executed: bool
    custom_wb_capture_blocked: bool
    cine_ei_awb_blocked: bool
    fx3_exact_6_metering_modes: Tuple[str, ...]
    requested_metering_mode: str
    effective_metering_mode: str
    desqueeze_display: str
    effective_face_priority_in_multi: str
    focus_area: str
    effective_spot_metering_point: str
    effective_ael_w_shutter: str
    exposure_std_adjust_ev: float
    cine_ei_base_iso: int
    cine_ei_recording_iso_locked: bool
    metering_drives_mm_monitoring_only: bool
    fx6_preset_custom_kelvins: Tuple[int, ...]
    fx6_preset_cine_ei_kelvins: Tuple[int, ...]
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G116WbCineEiAndMeteringGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    wb_cineei_and_metering_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master116GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_113_gates_verified: bool
    all_116_gates_verified: bool
    g13_to_g116_all_passed: bool
    g115_to_g116_all_passed: bool
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
    master_114_report: Dict[str, Any]
    g115_result: Dict[str, Any]
    g116_result: Dict[str, Any]
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
    for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE280):
        if os.environ.get(env_key, "").strip() in _TRUTHY_CLEAN_ROOM_TOKENS:
            return True
    return False


def _default_donor_budget_seconds_phase280() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return DONOR_CHECK_CI_MAX_SECONDS_PHASE280
    return DONOR_CHECK_MAX_SECONDS_PHASE280


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


def _norm_reset_action_phase280(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE280
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE
    if u in ("PPX RESET", "PP RESET", "PICTURE PROFILE RESET"):
        return RESET_ACTION_PP_SLOT_RESET_PHASE280
    return None


def _norm_shoot_mode_phase280(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "MOVIE": SHOOT_MODE_MOVIE_PHASE280,
        "STILL": SHOOT_MODE_STILL_PHASE280,
        "S&Q": SHOOT_MODE_SQ_PHASE280,
        "SQ": SHOOT_MODE_SQ_PHASE280,
        "INTELLIGENT AUTO": SHOOT_MODE_INTELLIGENT_AUTO_PHASE280,
        "IAUTO": SHOOT_MODE_INTELLIGENT_AUTO_PHASE280,
    }
    return mapping.get(u)


def _norm_log_shooting_phase280(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "OFF": LOG_SHOOTING_OFF_G115,
        "FLEXIBLE ISO": LOG_SHOOTING_FLEXIBLE_ISO_G115,
        "CINE EI QUICK": LOG_SHOOTING_CINE_EI_QUICK_G115,
        "CINE EI": LOG_SHOOTING_CINE_EI_G115,
    }
    return mapping.get(u)


def _norm_picture_profile_g115(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    for p in ALLOWED_PICTURE_PROFILES_G115:
        if u == p.upper():
            return p
    return None


def _norm_creative_look_g115(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip().strip("[]")
    u = cleaned.upper()
    for item in ALLOWED_CREATIVE_LOOKS_G115:
        if u == item.upper():
            return item
    return None


def _norm_dro_g115(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_DRO_MODES_G115:
        if u == item.upper():
            return item
    return None


def _norm_hdmi_res_g115(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").lower()
    for item in ALLOWED_HDMI_OUT_RESOLUTIONS_G115:
        if u == item.lower():
            return item
    return None


def _norm_on_off_phase280(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "ON":
        return "On"
    if u == "OFF":
        return "Off"
    return None


def _norm_white_balance_g116(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_WHITE_BALANCE_MODES_G116:
        if u == item.upper():
            return item
    return None


def _norm_priority_awb_g116(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    for item in ALLOWED_PRIORITY_AWB_MODES_G116:
        if u == item.upper():
            return item
    return None


def _norm_shutter_awb_lock_g116(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("SHUTTER HALF PRESS", "SHUT. HALFWAY DOWN"):
        return SHUTTER_AWB_LOCK_HALF_PRESS_G116
    if u == "CONT. SHOOTING":
        return SHUTTER_AWB_LOCK_CONT_SHOOTING_G116
    if u == "OFF":
        return SHUTTER_AWB_LOCK_OFF_G116
    return None


def _norm_shockless_wb_g116(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "OFF": SHOCKLESS_WB_OFF_G116,
        "1 (FAST)": SHOCKLESS_WB_1_FAST_G116,
        "1(FAST)": SHOCKLESS_WB_1_FAST_G116,
        "1": SHOCKLESS_WB_1_FAST_G116,
        "2": SHOCKLESS_WB_2_G116,
        "3 (SLOW)": SHOCKLESS_WB_3_SLOW_G116,
        "3(SLOW)": SHOCKLESS_WB_3_SLOW_G116,
        "3": SHOCKLESS_WB_3_SLOW_G116,
    }
    return mapping.get(u)


def _norm_metering_mode_g116(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in FX3_EXACT_6_METERING_MODES_G116:
        if u == item.upper():
            return item
    return None


def _norm_desqueeze_g116(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").lower()
    for item in ALLOWED_DESQUEEZE_MODES_G116:
        if u == item.lower():
            return item
    return None


def _norm_spot_metering_point_g116(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_SPOT_METERING_POINTS_G116:
        if u == item.upper():
            return item
    return None


def _norm_focus_area_g116(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_FOCUS_AREAS_G116:
        if u == item.upper():
            return item
    return None


def _norm_ael_w_shutter_g116(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    for item in ALLOWED_AEL_W_SHUTTER_MODES_G116:
        if u == item.upper():
            return item
    return None


# ---------------------------------------------------------------------------
# 1. Fast `< 0.20s` O_RDONLY Donor Contract Audit (`Phase 280`)
# ---------------------------------------------------------------------------


def audit_phase280_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: Optional[float] = None,
) -> Phase280DonorAuditResult:
    """Inspect local FX3 Ver. 7.02 / FX6 Ver. 6.01 donor artifacts strictly via
    `os.open(..., os.O_RDONLY)` within `<0.20s` (`1.00s` under
    `GITHUB_ACTIONS=true`), using targeted `os.pread` slices on both 79 MiB FX3
    `appFw.so` and 50.5 MiB FX6 `appFw.so`, and full `O_RDONLY` SHA-256
    verification on 4-language `.uxc` packs and `BK4` seed with deterministic
    `CLEAN_ROOM_SYNTHETIC` fallback.
    """
    t0 = time.perf_counter()
    budget = (
        _default_donor_budget_seconds_phase280()
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE280_DONOR_SPECS.items():
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
            spec[5] for spec in PINNED_PHASE280_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE280_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE280_DONOR_SPECS.items()}
        return Phase280DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE280_DONOR_INTEGRITY
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
    ) in PINNED_PHASE280_DONOR_SPECS.items():
        fp = resolved[key]
        if key in ("fx3_appfw_so", "fx6_appfw_so"):
            slices_spec = (
                PINNED_FX3_APPFW_SLICES_PHASE280
                if key == "fx3_appfw_so"
                else PINNED_FX6_APPFW_SLICES_PHASE280
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
            errors.append(f"Missing required Wave-48 byte markers in {key}.")

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
        files_inspected == len(PINNED_PHASE280_DONOR_SPECS)
        and within_budget
        and (not missing)
        and (not errors)
        and fx3_ok
        and fx6_ok
        and lang_ok
    )
    return Phase280DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE280_DONOR_INTEGRITY,
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
# 2. Gate G115: [Picture Profile] PP11 vs [Creative Look] / [DRO] & [Log Shooting]
# ---------------------------------------------------------------------------


def resolve_fx3_pp_scinetone_creativelook_dro_state(
    *,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE280,
    log_shooting: str = LOG_SHOOTING_OFF_G115,
    requested_picture_profile: str = PP_FACTORY_DEFAULT_G115,
    requested_picture_profile_still: Optional[str] = None,
    different_set_picture_profile_checked: bool = DIFFERENT_SET_PP_DEFAULT_CHECKED_G115,
    requested_creative_look: str = CREATIVE_LOOK_FACTORY_DEFAULT_G115,
    requested_dro: str = DRO_FACTORY_DEFAULT_G115,
    hlg_still_image: bool = False,
    internal_recording_active: bool = True,
    requested_hdmi_output_resolution: str = HDMI_RES_AUTO_G115,
    reset_action: str = RESET_ACTION_NONE,
    pp_internal_params_customized: bool = False,
    pp_explicit_slot_reset_invoked: bool = False,
) -> Dict[str, Any]:
    s_mode = _norm_shoot_mode_phase280(shoot_mode) or SHOOT_MODE_MOVIE_PHASE280
    l_shoot = _norm_log_shooting_phase280(log_shooting) or LOG_SHOOTING_OFF_G115
    r_act = _norm_reset_action_phase280(reset_action) or RESET_ACTION_NONE
    req_pp = _norm_picture_profile_g115(requested_picture_profile) or PP_FACTORY_DEFAULT_G115
    req_pp_still = (
        _norm_picture_profile_g115(requested_picture_profile_still)
        if requested_picture_profile_still is not None
        else req_pp
    ) or PP_FACTORY_DEFAULT_G115
    req_cl = _norm_creative_look_g115(requested_creative_look) or CREATIVE_LOOK_FACTORY_DEFAULT_G115
    req_dro = _norm_dro_g115(requested_dro) or DRO_FACTORY_DEFAULT_G115
    req_hdmi = _norm_hdmi_res_g115(requested_hdmi_output_resolution) or HDMI_RES_AUTO_G115

    # [Different Set for Still/Mv] check mark survives BOTH Camera Settings Reset & Initialize.
    effective_diff_set = bool(different_set_picture_profile_checked)

    # Reset behavior:
    # - Camera Settings Reset / Initialize restores active PP selector to PP11,
    #   Creative Look -> ST, DRO -> Auto (when unlocked),
    #   YET customized internal params inside PP1..PP11 survive BOTH!
    # - Only explicit [PPx] -> [Reset] clears internal parameters of a PP slot.
    if r_act in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        sel_pp_movie = PP_FACTORY_DEFAULT_G115
        sel_pp_still = PP_FACTORY_DEFAULT_G115
        sel_cl = CREATIVE_LOOK_FACTORY_DEFAULT_G115
        sel_dro = DRO_FACTORY_DEFAULT_G115
    else:
        sel_pp_movie = req_pp
        sel_pp_still = req_pp_still if effective_diff_set else req_pp
        sel_cl = req_cl
        sel_dro = req_dro

    pp_internal_cleared = (
        bool(pp_explicit_slot_reset_invoked)
        or (r_act == RESET_ACTION_PP_SLOT_RESET_PHASE280)
        or (not pp_internal_params_customized)
    )

    if l_shoot != LOG_SHOOTING_OFF_G115:
        eff_pp = PP_OFF_G115
        eff_pp_still = PP_OFF_G115
        eff_cl = CREATIVE_LOOK_LOCKED_VALUE_G115
        eff_dro = DRO_OFF_G115
        eff_gamma_assist = "Off"
        double_log_blocked = True
        cl_dro_locked = True
        eff_hdmi = HDMI_RES_1080P_G115 if internal_recording_active else req_hdmi
        pplut_clamped = False
    elif s_mode == SHOOT_MODE_INTELLIGENT_AUTO_PHASE280:
        eff_pp = PP_OFF_G115
        eff_pp_still = PP_OFF_G115
        eff_cl = CREATIVE_LOOK_LOCKED_VALUE_G115
        eff_dro = DRO_AUTO_G115
        eff_gamma_assist = "Off"
        double_log_blocked = False
        cl_dro_locked = True
        eff_hdmi = req_hdmi
        pplut_clamped = False
    else:
        eff_pp = sel_pp_still if s_mode == SHOOT_MODE_STILL_PHASE280 else sel_pp_movie
        eff_pp_still = sel_pp_still
        double_log_blocked = False
        if eff_pp != PP_OFF_G115:
            eff_cl = CREATIVE_LOOK_LOCKED_VALUE_G115
            eff_dro = DRO_OFF_G115
            cl_dro_locked = True
        else:
            eff_cl = sel_cl
            eff_dro = DRO_OFF_G115 if (s_mode == SHOOT_MODE_STILL_PHASE280 and hlg_still_image) else sel_dro
            cl_dro_locked = False
        eff_gamma_assist = "Off"
        pplut_clamped = (
            eff_pp in PPLUT_PICTURE_PROFILES_G115 and bool(internal_recording_active)
        )
        eff_hdmi = HDMI_RES_1080P_G115 if pplut_clamped else req_hdmi

    return {
        "shoot_mode": s_mode,
        "log_shooting": l_shoot,
        "reset_action": r_act,
        "effective_diff_set": effective_diff_set,
        "effective_picture_profile": eff_pp,
        "effective_picture_profile_still": eff_pp_still,
        "effective_creative_look": eff_cl,
        "effective_dro": eff_dro,
        "effective_gamma_display_assist": eff_gamma_assist,
        "effective_select_lut": SELECT_LUT_FACTORY_DEFAULT_G115,
        "effective_hdmi_output_resolution": eff_hdmi,
        "creative_look_and_dro_locked": cl_dro_locked,
        "double_log_or_baked_look_blocked": double_log_blocked,
        "pplut_hdmi_1080p_clamped": pplut_clamped,
        "pp_internal_params_cleared": pp_internal_cleared,
    }


def compute_pp_scinetone_creativelook_dro_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate 512 combinations across 4 `[Log Shooting]` modes,
    4 representative `[Picture Profile]` modes (`Off`, `PP11`, `PP8`, `PPLUT1`),
    2 `[Creative Look]` states, 2 `[D-Range Optimizer]` states,
    2 `[Different Set for Still/Mv]` check states, and 4 reset actions.
    """
    states_checked = 0
    double_pp_lockouts = 0
    pp_mutual_exclusions = 0
    internal_param_unreset_traps = 0
    pplut_hdmi_clamps = 0

    for l_shoot in ALLOWED_LOG_SHOOTING_MODES_G115:
        for req_pp in (PP_OFF_G115, "PP11", "PP8", "PPLUT1"):
            for req_cl in ("ST", "BW"):
                for req_dro in ("Auto", "Off"):
                    for diff_set in (False, True):
                        for r_act in (
                            RESET_ACTION_NONE,
                            RESET_ACTION_CAMERA_SETTINGS_RESET,
                            RESET_ACTION_INITIALIZE,
                            RESET_ACTION_PP_SLOT_RESET_PHASE280,
                        ):
                            resolved = resolve_fx3_pp_scinetone_creativelook_dro_state(
                                shoot_mode=SHOOT_MODE_MOVIE_PHASE280,
                                log_shooting=l_shoot,
                                requested_picture_profile=req_pp,
                                different_set_picture_profile_checked=diff_set,
                                requested_creative_look=req_cl,
                                requested_dro=req_dro,
                                internal_recording_active=True,
                                reset_action=r_act,
                                pp_internal_params_customized=True,
                                pp_explicit_slot_reset_invoked=(
                                    r_act == RESET_ACTION_PP_SLOT_RESET_PHASE280
                                ),
                            )
                            states_checked += 1
                            if resolved["double_log_or_baked_look_blocked"]:
                                double_pp_lockouts += 1
                            elif resolved["creative_look_and_dro_locked"]:
                                pp_mutual_exclusions += 1
                            if not resolved["pp_internal_params_cleared"]:
                                internal_param_unreset_traps += 1
                            if resolved["pplut_hdmi_1080p_clamped"]:
                                pplut_hdmi_clamps += 1

    return {
        "states_checked": states_checked,
        "double_pp_lockouts": double_pp_lockouts,
        "pp_mutual_exclusions": pp_mutual_exclusions,
        "internal_param_unreset_traps": internal_param_unreset_traps,
        "pplut_hdmi_clamps": pplut_hdmi_clamps,
        "all_invariants_hold": (
            states_checked == 512
            and double_pp_lockouts == 384
            and pp_mutual_exclusions == 112
            and internal_param_unreset_traps == 384
            and pplut_hdmi_clamps == 16
        ),
    }


def verify_pp_scinetone_creativelook_dro_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE280,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE280,
    fx6_comparison_fw_version: str = FX6_DEFAULT_FW_VERSION_PHASE280,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE280,
    log_shooting: str = LOG_SHOOTING_OFF_G115,
    requested_picture_profile: str = PP_FACTORY_DEFAULT_G115,
    requested_picture_profile_still: Optional[str] = None,
    different_set_picture_profile_checked: bool = DIFFERENT_SET_PP_DEFAULT_CHECKED_G115,
    requested_creative_look: str = CREATIVE_LOOK_FACTORY_DEFAULT_G115,
    requested_dro: str = DRO_FACTORY_DEFAULT_G115,
    hlg_still_image: bool = False,
    internal_recording_active: bool = True,
    requested_hdmi_output_resolution: str = HDMI_RES_AUTO_G115,
    reset_action: str = RESET_ACTION_NONE,
    pp_internal_params_customized: bool = False,
    pp_explicit_slot_reset_invoked: bool = False,
    claimed_fx3_oob_picture_profile_default: Optional[str] = PP_FACTORY_DEFAULT_G115,
    claimed_picture_profile: Optional[str] = None,
    claimed_creative_look: Optional[str] = None,
    claimed_dro: Optional[str] = None,
    claimed_creative_look_active_with_pp_on: bool = False,
    claimed_dro_active_with_pp_on: bool = False,
    claimed_pp_active_with_log_on: bool = False,
    claimed_gamma_display_assist_movie_on: bool = False,
    claimed_pplut_still_supported: bool = False,
    claimed_hdmi_output_resolution: Optional[str] = None,
    claimed_camera_reset_clears_pp_internal_params: bool = False,
    claimed_initialize_clears_pp_internal_params: bool = False,
    claimed_reset_clears_diff_set_check: bool = False,
    claimed_pp_slots_clean_after_reset: bool = False,
) -> PpScinetoneCreativeLookDroGuardResult:
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME
        or isinstance(body_model_id, bool)
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE280
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
        or not isinstance(fx6_comparison_fw_version, str)
        or not fx6_comparison_fw_version.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G115_TELEMETRY_INVALID)
        errors.append(
            "Gate G115 requires ILME-FX3 (0x91030080, Help Guide ilc/2210, Ver. 7.02)."
        )

    norm_shoot = _norm_shoot_mode_phase280(shoot_mode)
    norm_log = _norm_log_shooting_phase280(log_shooting)
    norm_pp = _norm_picture_profile_g115(requested_picture_profile)
    norm_pp_still = (
        _norm_picture_profile_g115(requested_picture_profile_still)
        if requested_picture_profile_still is not None
        else None
    )
    norm_cl = _norm_creative_look_g115(requested_creative_look)
    norm_dro = _norm_dro_g115(requested_dro)
    norm_hdmi = _norm_hdmi_res_g115(requested_hdmi_output_resolution)
    norm_reset = _norm_reset_action_phase280(reset_action)

    if (
        norm_shoot is None
        or norm_log is None
        or norm_pp is None
        or (requested_picture_profile_still is not None and norm_pp_still is None)
        or norm_cl is None
        or norm_dro is None
        or norm_hdmi is None
        or norm_reset is None
        or not isinstance(different_set_picture_profile_checked, bool)
        or not isinstance(hlg_still_image, bool)
        or not isinstance(internal_recording_active, bool)
        or not isinstance(pp_internal_params_customized, bool)
        or not isinstance(pp_explicit_slot_reset_invoked, bool)
        or not isinstance(claimed_creative_look_active_with_pp_on, bool)
        or not isinstance(claimed_dro_active_with_pp_on, bool)
        or not isinstance(claimed_pp_active_with_log_on, bool)
        or not isinstance(claimed_gamma_display_assist_movie_on, bool)
        or not isinstance(claimed_pplut_still_supported, bool)
        or not isinstance(claimed_camera_reset_clears_pp_internal_params, bool)
        or not isinstance(claimed_initialize_clears_pp_internal_params, bool)
        or not isinstance(claimed_reset_clears_diff_set_check, bool)
        or not isinstance(claimed_pp_slots_clean_after_reset, bool)
    ):
        _add_code(codes, STATUS_BLOCKED_G115_TELEMETRY_INVALID)
        errors.append("Invalid or unrecognized G115 telemetry or enum value.")

    resolved = resolve_fx3_pp_scinetone_creativelook_dro_state(
        shoot_mode=norm_shoot or SHOOT_MODE_MOVIE_PHASE280,
        log_shooting=norm_log or LOG_SHOOTING_OFF_G115,
        requested_picture_profile=norm_pp or PP_FACTORY_DEFAULT_G115,
        requested_picture_profile_still=norm_pp_still,
        different_set_picture_profile_checked=bool(different_set_picture_profile_checked),
        requested_creative_look=norm_cl or CREATIVE_LOOK_FACTORY_DEFAULT_G115,
        requested_dro=norm_dro or DRO_FACTORY_DEFAULT_G115,
        hlg_still_image=bool(hlg_still_image),
        internal_recording_active=bool(internal_recording_active),
        requested_hdmi_output_resolution=norm_hdmi or HDMI_RES_AUTO_G115,
        reset_action=norm_reset or RESET_ACTION_NONE,
        pp_internal_params_customized=bool(pp_internal_params_customized),
        pp_explicit_slot_reset_invoked=bool(pp_explicit_slot_reset_invoked),
    )

    matrix = compute_pp_scinetone_creativelook_dro_matrix()
    if not matrix["all_invariants_hold"]:
        _add_code(codes, STATUS_BLOCKED_G115_TELEMETRY_INVALID)
        errors.append("G115 512-state matrix verification failed.")

    # 1. [Log Shooting] Double-Log / Baked-Look ISP Corruption Guard
    eff_log = norm_log or LOG_SHOOTING_OFF_G115
    if eff_log != LOG_SHOOTING_OFF_G115:
        norm_claimed_pp = (
            _norm_picture_profile_g115(claimed_picture_profile)
            if claimed_picture_profile is not None
            else None
        )
        norm_claimed_cl = (
            _norm_creative_look_g115(claimed_creative_look)
            if claimed_creative_look is not None
            else None
        )
        norm_claimed_dro = (
            _norm_dro_g115(claimed_dro) if claimed_dro is not None else None
        )
        if (
            claimed_pp_active_with_log_on
            or claimed_gamma_display_assist_movie_on
            or (norm_claimed_pp is not None and norm_claimed_pp != PP_OFF_G115)
            or (
                norm_claimed_cl is not None
                and norm_claimed_cl != CREATIVE_LOOK_LOCKED_VALUE_G115
            )
            or (norm_claimed_dro is not None and norm_claimed_dro != DRO_OFF_G115)
        ):
            _add_code(codes, STATUS_BLOCKED_G115_LOG_SHOOTING_DOUBLE_PP_CORRUPTION_VIOLATION)
            errors.append(
                "[Log Shooting] (Flexible ISO / Cine EI Quick / Cine EI) hard-locks "
                "[Picture Profile] to Off, [Creative Look] to '-', [D-Range Optimizer] "
                "to Off, and movie [Gamma Display Assist] to Off to prevent double-log "
                "or baked-look ISP corruption."
            )

    # 2. Out-of-Box PP11 Default & PP vs Creative Look / DRO Mutual Exclusivity
    norm_oob_pp = (
        _norm_picture_profile_g115(claimed_fx3_oob_picture_profile_default)
        if claimed_fx3_oob_picture_profile_default is not None
        else None
    )
    norm_claimed_cl2 = (
        _norm_creative_look_g115(claimed_creative_look)
        if claimed_creative_look is not None
        else None
    )
    norm_claimed_dro2 = (
        _norm_dro_g115(claimed_dro) if claimed_dro is not None else None
    )
    if (
        (claimed_fx3_oob_picture_profile_default is not None and norm_oob_pp != PP_FACTORY_DEFAULT_G115)
        or claimed_creative_look_active_with_pp_on
        or claimed_dro_active_with_pp_on
        or (
            resolved["effective_picture_profile"] != PP_OFF_G115
            and (
                (
                    norm_claimed_cl2 is not None
                    and norm_claimed_cl2 != CREATIVE_LOOK_LOCKED_VALUE_G115
                )
                or (norm_claimed_dro2 is not None and norm_claimed_dro2 != DRO_OFF_G115)
            )
        )
        or (
            norm_shoot == SHOOT_MODE_STILL_PHASE280
            and hlg_still_image
            and norm_claimed_dro2 is not None
            and norm_claimed_dro2 != DRO_OFF_G115
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G115_PP_CREATIVELOOK_DRO_MUTUAL_EXCLUSION_VIOLATION)
        errors.append(
            "Out-of-box ILME-FX3 defaults [Picture Profile] to PP11 (S-Cinetone) for "
            "both Movie and Still unless decoupled via [Different Set for Still/Mv]; "
            "whenever [Picture Profile] != Off, [Creative Look] is '-' and "
            "[D-Range Optimizer] is Off."
        )

    # 3. PPLUT1..4 Movie-Only & Internal-Recording 1080p HDMI Clamp Guard
    norm_claimed_hdmi = (
        _norm_hdmi_res_g115(claimed_hdmi_output_resolution)
        if claimed_hdmi_output_resolution is not None
        else None
    )
    if (
        claimed_pplut_still_supported
        or (
            norm_shoot == SHOOT_MODE_STILL_PHASE280
            and norm_pp in PPLUT_PICTURE_PROFILES_G115
        )
        or (
            resolved["pplut_hdmi_1080p_clamped"]
            and norm_claimed_hdmi is not None
            and norm_claimed_hdmi != HDMI_RES_1080P_G115
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G115_PPLUT_STILL_OR_HDMI_CLAMP_VIOLATION)
        errors.append(
            "PPLUT1..4 are Movie-only and clamp internal-recording HDMI output to 1080p."
        )

    # 4. Reset Trap Guard ([Camera Settings Reset] / [Initialize] vs [PPx] -> [Reset])
    unreset_trap = (
        pp_internal_params_customized
        and (norm_reset in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE))
        and (not pp_explicit_slot_reset_invoked)
    )
    if (
        claimed_camera_reset_clears_pp_internal_params
        or claimed_initialize_clears_pp_internal_params
        or claimed_reset_clears_diff_set_check
        or claimed_pp_slots_clean_after_reset
        or unreset_trap
    ):
        _add_code(codes, STATUS_BLOCKED_G115_PP_INTERNAL_PARAM_UNRESET_TRAP)
        errors.append(
            "[Camera Settings Reset] restores active selector to PP11, yet customized "
            "internal parameters inside PP1..PP11 and [Different Set for Still/Mv] check "
            "marks survive BOTH [Camera Settings Reset] and [Initialize] unless each "
            "[PPx] -> [Reset] is explicitly invoked."
        )

    valid = not codes
    status = STATUS_VERIFIED_G115 if valid else codes[0]

    return PpScinetoneCreativeLookDroGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}"
        if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
        else "invalid",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        fx6_comparison_fw_version=fx6_comparison_fw_version,
        reset_action=resolved["reset_action"],
        picture_profile_menu_path=PICTURE_PROFILE_MENU_PATH_G115,
        different_set_menu_path=DIFFERENT_SET_STILL_MV_MENU_PATH_G115,
        creative_look_menu_path=CREATIVE_LOOK_MENU_PATH_G115,
        dro_menu_path=DRO_MENU_PATH_G115,
        log_shooting_menu_path=LOG_SHOOTING_MENU_PATH_G115,
        shoot_mode=resolved["shoot_mode"],
        log_shooting=resolved["log_shooting"],
        fx3_oob_picture_profile_default=PP_FACTORY_DEFAULT_G115,
        fx3_creative_look_10_presets=CREATIVE_LOOK_10_PRESETS_G115,
        fx3_creative_look_8_params=CREATIVE_LOOK_8_PARAMS_G115,
        different_set_pp_checked=resolved["effective_diff_set"],
        requested_picture_profile=norm_pp or str(requested_picture_profile),
        effective_picture_profile=resolved["effective_picture_profile"],
        effective_picture_profile_still=resolved["effective_picture_profile_still"],
        effective_creative_look=resolved["effective_creative_look"],
        effective_dro=resolved["effective_dro"],
        effective_gamma_display_assist=resolved["effective_gamma_display_assist"],
        effective_select_lut=resolved["effective_select_lut"],
        effective_hdmi_output_resolution=resolved["effective_hdmi_output_resolution"],
        internal_recording_active=bool(internal_recording_active),
        hlg_still_image=bool(hlg_still_image),
        pp_internal_params_customized=bool(pp_internal_params_customized),
        pp_explicit_slot_reset_invoked=bool(pp_explicit_slot_reset_invoked),
        pp_internal_params_cleared=resolved["pp_internal_params_cleared"],
        creative_look_and_dro_locked=resolved["creative_look_and_dro_locked"],
        double_log_or_baked_look_blocked=resolved["double_log_or_baked_look_blocked"],
        pplut_hdmi_1080p_clamped=resolved["pplut_hdmi_1080p_clamped"],
        fx6_base_look_custom_default=FX6_BASE_LOOK_CUSTOM_DEFAULT_G115,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g115_pp_scinetone_creativelook_dro_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    pp_creativelook_dro_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase280DonorAuditResult] = None,
) -> Tuple[GateVerdict, G115PpScinetoneCreativeLookDroGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase280_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_pp_scinetone_creativelook_dro_guard(
        **dict(pp_creativelook_dro_kwargs or {})
    )

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G115.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G115 if valid else codes[0]

    res = G115PpScinetoneCreativeLookDroGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        pp_scinetone_creativelook_dro_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, oob_pp={guard.fx3_oob_picture_profile_default}, "
        f"eff_pp={guard.effective_picture_profile}(diff_set={guard.different_set_pp_checked}), "
        f"creative_look={guard.effective_creative_look}(looks={len(guard.fx3_creative_look_10_presets)}), "
        f"dro={guard.effective_dro}, log={guard.log_shooting}"
    )
    verdict = GateVerdict(
        gate_id=G115_GATE_ID,
        gate_code=G115_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G116: [White Balance] (2500K..9900K / Cine EI) & [Metering Mode] (6 Modes)
# ---------------------------------------------------------------------------


def resolve_fx3_wb_cineei_and_metering_state(
    *,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE280,
    log_shooting: str = LOG_SHOOTING_OFF_G115,
    picture_profile: str = PP_FACTORY_DEFAULT_G115,
    requested_white_balance: str = WB_FACTORY_DEFAULT_G116,
    priority_set_in_awb: str = PRIORITY_AWB_FACTORY_DEFAULT_G116,
    shutter_awb_lock: str = SHUTTER_AWB_LOCK_FACTORY_DEFAULT_G116,
    shockless_wb: str = SHOCKLESS_WB_FACTORY_DEFAULT_G116,
    custom_wb_setup_executed: bool = False,
    requested_metering_mode: str = METERING_MODE_FACTORY_DEFAULT_G116,
    desqueeze_display: str = "Off",
    face_priority_in_multi: str = FACE_PRIORITY_MULTI_DEFAULT_G116,
    focus_area: str = "Spot: M",
    spot_metering_point: str = SPOT_METERING_POINT_DEFAULT_G116,
    ael_w_shutter: str = AEL_W_SHUTTER_DEFAULT_G116,
    non_optical_zoom_active: bool = False,
    reset_action: str = RESET_ACTION_NONE,
) -> Dict[str, Any]:
    s_mode = _norm_shoot_mode_phase280(shoot_mode) or SHOOT_MODE_MOVIE_PHASE280
    l_shoot = _norm_log_shooting_phase280(log_shooting) or LOG_SHOOTING_OFF_G115
    pp = _norm_picture_profile_g115(picture_profile) or PP_FACTORY_DEFAULT_G115
    wb = _norm_white_balance_g116(requested_white_balance) or WB_FACTORY_DEFAULT_G116
    prio_awb = _norm_priority_awb_g116(priority_set_in_awb) or PRIORITY_AWB_FACTORY_DEFAULT_G116
    shutter_lock = _norm_shutter_awb_lock_g116(shutter_awb_lock) or SHUTTER_AWB_LOCK_FACTORY_DEFAULT_G116
    shockless = _norm_shockless_wb_g116(shockless_wb) or SHOCKLESS_WB_FACTORY_DEFAULT_G116
    m_mode = _norm_metering_mode_g116(requested_metering_mode) or METERING_MODE_FACTORY_DEFAULT_G116
    desq = _norm_desqueeze_g116(desqueeze_display) or "Off"
    face_prio = _norm_on_off_phase280(face_priority_in_multi) or FACE_PRIORITY_MULTI_DEFAULT_G116
    f_area = _norm_focus_area_g116(focus_area) or "Spot: M"
    spot_pt = _norm_spot_metering_point_g116(spot_metering_point) or SPOT_METERING_POINT_DEFAULT_G116
    ael_sh = _norm_ael_w_shutter_g116(ael_w_shutter) or AEL_W_SHUTTER_DEFAULT_G116
    r_act = _norm_reset_action_phase280(reset_action) or RESET_ACTION_NONE

    # Reset rules:
    # - Camera Settings Reset resets active WB -> Auto (unless Cine EI holds manual WB),
    #   Priority Set in AWB -> Standard, Shockless WB -> 1 (Fast), Metering -> Multi,
    #   Face Priority -> On (unless De-Squeeze), Spot Metering Point -> Center.
    # - Shutter AWB Lock & AEL w/ Shutter & Custom 1..3 memorized data SURVIVE Camera Settings Reset!
    # - Initialize resets Shutter AWB Lock -> Off, AEL w/ Shutter -> Auto.
    if r_act == RESET_ACTION_CAMERA_SETTINGS_RESET:
        eff_wb = wb if l_shoot in (LOG_SHOOTING_CINE_EI_G115, LOG_SHOOTING_CINE_EI_QUICK_G115) else WB_FACTORY_DEFAULT_G116
        eff_prio = PRIORITY_AWB_FACTORY_DEFAULT_G116
        eff_shockless = SHOCKLESS_WB_FACTORY_DEFAULT_G116
        eff_shutter_lock = shutter_lock
        eff_m_base = METERING_MODE_FACTORY_DEFAULT_G116
        eff_face_base = FACE_PRIORITY_MULTI_DEFAULT_G116
        eff_spot_base = SPOT_METERING_POINT_DEFAULT_G116
        eff_ael_sh = ael_sh
        custom_wb_survives = True
    elif r_act == RESET_ACTION_INITIALIZE:
        eff_wb = WB_FACTORY_DEFAULT_G116
        eff_prio = PRIORITY_AWB_FACTORY_DEFAULT_G116
        eff_shockless = SHOCKLESS_WB_FACTORY_DEFAULT_G116
        eff_shutter_lock = SHUTTER_AWB_LOCK_FACTORY_DEFAULT_G116
        eff_m_base = METERING_MODE_FACTORY_DEFAULT_G116
        eff_face_base = FACE_PRIORITY_MULTI_DEFAULT_G116
        eff_spot_base = SPOT_METERING_POINT_DEFAULT_G116
        eff_ael_sh = AEL_W_SHUTTER_DEFAULT_G116
        custom_wb_survives = False
    else:
        eff_wb = wb
        eff_prio = prio_awb
        eff_shockless = shockless
        eff_shutter_lock = shutter_lock
        eff_m_base = m_mode
        eff_face_base = face_prio
        eff_spot_base = spot_pt
        eff_ael_sh = ael_sh
        custom_wb_survives = True

    cine_ei_active = l_shoot in (
        LOG_SHOOTING_CINE_EI_G115,
        LOG_SHOOTING_CINE_EI_QUICK_G115,
    )
    cine_ei_awb_blocked = cine_ei_active and (eff_wb in WB_AWB_BLOCKED_IN_CINE_EI_G116)

    pp_slog3_or_lut = (
        pp in SLOG3_PICTURE_PROFILES_G115 or pp in PPLUT_PICTURE_PROFILES_G115
    )
    custom_wb_capture_blocked = bool(custom_wb_setup_executed) and (
        l_shoot != LOG_SHOOTING_OFF_G115 or pp_slog3_or_lut
    )

    eff_face_prio = (
        FACE_PRIORITY_MULTI_OFF_G116 if desq != "Off" else eff_face_base
    )
    eff_spot_pt = (
        SPOT_METERING_POINT_CENTER_G116
        if f_area in SPOT_METERING_CENTER_LOCKED_FOCUS_AREAS_G116
        else eff_spot_base
    )
    eff_metering = (
        METERING_MODE_MULTI_G116
        if (s_mode == SHOOT_MODE_INTELLIGENT_AUTO_PHASE280 or non_optical_zoom_active)
        else eff_m_base
    )

    return {
        "reset_action": r_act,
        "effective_white_balance": eff_wb,
        "effective_priority_set_in_awb": eff_prio,
        "effective_shutter_awb_lock": eff_shutter_lock,
        "effective_shockless_wb": eff_shockless,
        "custom_wb_slots_memorized_after_reset": custom_wb_survives,
        "cine_ei_awb_blocked": cine_ei_awb_blocked,
        "custom_wb_capture_blocked": custom_wb_capture_blocked,
        "effective_metering_mode": eff_metering,
        "effective_face_priority_in_multi": eff_face_prio,
        "effective_spot_metering_point": eff_spot_pt,
        "effective_ael_w_shutter": eff_ael_sh,
        "cine_ei_recording_iso_locked": cine_ei_active,
        "metering_drives_mm_monitoring_only": cine_ei_active,
    }


def compute_wb_cineei_and_metering_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate 288 combinations across 4 `[Log Shooting]` modes,
    3 `[White Balance]` modes, 2 `[Custom Setup]` states, 2 `[De-Squeeze Display]`
    states, 2 focus area classes, and 3 `[Metering Mode]` states.
    """
    states_checked = 0
    cine_ei_awb_blocks = 0
    custom_setup_traps = 0
    desqueeze_face_locks = 0
    spot_center_locks = 0
    cine_ei_passive_mm_states = 0

    for l_shoot in ALLOWED_LOG_SHOOTING_MODES_G115:
        for wb in (WB_AUTO_G116, WB_CTEMP_FILTER_G116, WB_CUSTOM_1_G116):
            for custom_setup in (False, True):
                for desq in ("Off", "1.3x"):
                    for f_area in ("Wide", "Spot: M"):
                        for m_mode in (
                            METERING_MODE_MULTI_G116,
                            METERING_MODE_SPOT_STANDARD_G116,
                            METERING_MODE_HIGHLIGHT_G116,
                        ):
                            resolved = resolve_fx3_wb_cineei_and_metering_state(
                                shoot_mode=SHOOT_MODE_MOVIE_PHASE280,
                                log_shooting=l_shoot,
                                picture_profile=PP_FACTORY_DEFAULT_G115,
                                requested_white_balance=wb,
                                custom_wb_setup_executed=custom_setup,
                                requested_metering_mode=m_mode,
                                desqueeze_display=desq,
                                face_priority_in_multi=FACE_PRIORITY_MULTI_ON_G116,
                                focus_area=f_area,
                                spot_metering_point=SPOT_METERING_POINT_FOCUS_LINK_G116,
                            )
                            states_checked += 1
                            if resolved["cine_ei_awb_blocked"]:
                                cine_ei_awb_blocks += 1
                            if resolved["custom_wb_capture_blocked"]:
                                custom_setup_traps += 1
                            if resolved["effective_face_priority_in_multi"] == FACE_PRIORITY_MULTI_OFF_G116:
                                desqueeze_face_locks += 1
                            if resolved["effective_spot_metering_point"] == SPOT_METERING_POINT_CENTER_G116:
                                spot_center_locks += 1
                            if resolved["metering_drives_mm_monitoring_only"]:
                                cine_ei_passive_mm_states += 1

    return {
        "states_checked": states_checked,
        "cine_ei_awb_blocks": cine_ei_awb_blocks,
        "custom_setup_traps": custom_setup_traps,
        "desqueeze_face_locks": desqueeze_face_locks,
        "spot_center_locks": spot_center_locks,
        "cine_ei_passive_mm_states": cine_ei_passive_mm_states,
        "all_invariants_hold": (
            states_checked == 288
            and cine_ei_awb_blocks == 48
            and custom_setup_traps == 108
            and desqueeze_face_locks == 144
            and spot_center_locks == 144
            and cine_ei_passive_mm_states == 144
        ),
    }


def verify_wb_cineei_and_metering_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE280,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE280,
    fx6_comparison_fw_version: str = FX6_DEFAULT_FW_VERSION_PHASE280,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE280,
    log_shooting: str = LOG_SHOOTING_OFF_G115,
    picture_profile: str = PP_FACTORY_DEFAULT_G115,
    picture_profile_gamma: Optional[str] = None,
    requested_white_balance: str = WB_FACTORY_DEFAULT_G116,
    color_temp_k: int = 5600,
    wb_ab_trim: int = 0,
    wb_gm_trim: int = 0,
    priority_set_in_awb: str = PRIORITY_AWB_FACTORY_DEFAULT_G116,
    shutter_awb_lock: str = SHUTTER_AWB_LOCK_FACTORY_DEFAULT_G116,
    shockless_wb: str = SHOCKLESS_WB_FACTORY_DEFAULT_G116,
    custom_wb_setup_executed: bool = False,
    claimed_cine_ei_awb_allowed: bool = False,
    claimed_custom_wb_saved_to_camset: bool = False,
    claimed_camera_reset_wipes_custom_wb_slots: bool = False,
    claimed_camera_reset_resets_shutter_awb_lock: bool = False,
    claimed_camera_reset_resets_ael_w_shutter: bool = False,
    requested_metering_mode: str = METERING_MODE_FACTORY_DEFAULT_G116,
    desqueeze_display: str = "Off",
    face_priority_in_multi: str = FACE_PRIORITY_MULTI_DEFAULT_G116,
    claimed_effective_face_priority_in_multi: Optional[str] = None,
    focus_area: str = "Spot: M",
    spot_metering_point: str = SPOT_METERING_POINT_DEFAULT_G116,
    claimed_effective_spot_metering_point: Optional[str] = None,
    claimed_effective_metering_mode: Optional[str] = None,
    ael_w_shutter: str = AEL_W_SHUTTER_DEFAULT_G116,
    exposure_std_adjust_ev: float = 0.0,
    non_optical_zoom_active: bool = False,
    cine_ei_base_iso: int = 800,
    claimed_metering_alters_cine_ei_recording_iso: bool = False,
    reset_action: str = RESET_ACTION_NONE,
) -> WbCineEiAndMeteringGuardResult:
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME
        or isinstance(body_model_id, bool)
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE280
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
        or not isinstance(fx6_comparison_fw_version, str)
        or not fx6_comparison_fw_version.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G116_TELEMETRY_INVALID)
        errors.append(
            "Gate G116 requires ILME-FX3 (0x91030080, Help Guide ilc/2210, Ver. 7.02)."
        )

    norm_shoot = _norm_shoot_mode_phase280(shoot_mode)
    norm_log = _norm_log_shooting_phase280(log_shooting)
    norm_pp = _norm_picture_profile_g115(picture_profile)
    norm_wb = _norm_white_balance_g116(requested_white_balance)
    norm_prio = _norm_priority_awb_g116(priority_set_in_awb)
    norm_shutter_lock = _norm_shutter_awb_lock_g116(shutter_awb_lock)
    norm_shockless = _norm_shockless_wb_g116(shockless_wb)
    norm_metering = _norm_metering_mode_g116(requested_metering_mode)
    norm_desq = _norm_desqueeze_g116(desqueeze_display)
    norm_face = _norm_on_off_phase280(face_priority_in_multi)
    norm_focus = _norm_focus_area_g116(focus_area)
    norm_spot_pt = _norm_spot_metering_point_g116(spot_metering_point)
    norm_ael = _norm_ael_w_shutter_g116(ael_w_shutter)
    norm_reset = _norm_reset_action_phase280(reset_action)

    ctemp_valid = (
        not isinstance(color_temp_k, bool)
        and isinstance(color_temp_k, int)
        and WB_CTEMP_MIN_K_G116 <= color_temp_k <= WB_CTEMP_MAX_K_G116
        and (color_temp_k % WB_CTEMP_STEP_K_G116 == 0)
    )
    trim_valid = (
        not isinstance(wb_ab_trim, bool)
        and isinstance(wb_ab_trim, int)
        and WB_FINE_TRIM_MIN_G116 <= wb_ab_trim <= WB_FINE_TRIM_MAX_G116
        and not isinstance(wb_gm_trim, bool)
        and isinstance(wb_gm_trim, int)
        and WB_FINE_TRIM_MIN_G116 <= wb_gm_trim <= WB_FINE_TRIM_MAX_G116
    )
    exp_std_valid = (
        not isinstance(exposure_std_adjust_ev, bool)
        and isinstance(exposure_std_adjust_ev, (int, float))
        and EXP_STD_ADJUST_MIN_EV_G116 <= float(exposure_std_adjust_ev) <= EXP_STD_ADJUST_MAX_EV_G116
    )
    flash_scope_valid = not (
        norm_wb == WB_FLASH_G116 and norm_shoot != SHOOT_MODE_STILL_PHASE280
    )

    if (
        norm_shoot is None
        or norm_log is None
        or norm_pp is None
        or norm_wb is None
        or norm_prio is None
        or norm_shutter_lock is None
        or norm_shockless is None
        or norm_metering is None
        or norm_desq is None
        or norm_face is None
        or norm_focus is None
        or norm_spot_pt is None
        or norm_ael is None
        or norm_reset is None
        or not ctemp_valid
        or not trim_valid
        or not exp_std_valid
        or not flash_scope_valid
        or not isinstance(custom_wb_setup_executed, bool)
        or not isinstance(claimed_cine_ei_awb_allowed, bool)
        or not isinstance(claimed_custom_wb_saved_to_camset, bool)
        or not isinstance(claimed_camera_reset_wipes_custom_wb_slots, bool)
        or not isinstance(claimed_camera_reset_resets_shutter_awb_lock, bool)
        or not isinstance(claimed_camera_reset_resets_ael_w_shutter, bool)
        or not isinstance(non_optical_zoom_active, bool)
        or not isinstance(claimed_metering_alters_cine_ei_recording_iso, bool)
        or isinstance(cine_ei_base_iso, bool)
        or not isinstance(cine_ei_base_iso, int)
    ):
        _add_code(codes, STATUS_BLOCKED_G116_TELEMETRY_INVALID)
        errors.append("Invalid or unrecognized G116 WB / Metering telemetry or range.")

    resolved = resolve_fx3_wb_cineei_and_metering_state(
        shoot_mode=norm_shoot or SHOOT_MODE_MOVIE_PHASE280,
        log_shooting=norm_log or LOG_SHOOTING_OFF_G115,
        picture_profile=norm_pp or PP_FACTORY_DEFAULT_G115,
        requested_white_balance=norm_wb or WB_FACTORY_DEFAULT_G116,
        priority_set_in_awb=norm_prio or PRIORITY_AWB_FACTORY_DEFAULT_G116,
        shutter_awb_lock=norm_shutter_lock or SHUTTER_AWB_LOCK_FACTORY_DEFAULT_G116,
        shockless_wb=norm_shockless or SHOCKLESS_WB_FACTORY_DEFAULT_G116,
        custom_wb_setup_executed=bool(custom_wb_setup_executed),
        requested_metering_mode=norm_metering or METERING_MODE_FACTORY_DEFAULT_G116,
        desqueeze_display=norm_desq or "Off",
        face_priority_in_multi=norm_face or FACE_PRIORITY_MULTI_DEFAULT_G116,
        focus_area=norm_focus or "Spot: M",
        spot_metering_point=norm_spot_pt or SPOT_METERING_POINT_DEFAULT_G116,
        ael_w_shutter=norm_ael or AEL_W_SHUTTER_DEFAULT_G116,
        non_optical_zoom_active=bool(non_optical_zoom_active),
        reset_action=norm_reset or RESET_ACTION_NONE,
    )

    matrix = compute_wb_cineei_and_metering_matrix()
    if not matrix["all_invariants_hold"]:
        _add_code(codes, STATUS_BLOCKED_G116_TELEMETRY_INVALID)
        errors.append("G116 288-state matrix verification failed.")

    # 1. Cine EI / Cine EI Quick AWB Lockout
    if resolved["cine_ei_awb_blocked"] or claimed_cine_ei_awb_allowed:
        _add_code(codes, STATUS_BLOCKED_G116_CINE_EI_AWB_VIOLATION)
        errors.append(
            "[Auto] and [Underwater Auto] White Balance are blocked under "
            "[Log Shooting] = [Cine EI] / [Cine EI Quick]."
        )

    # 2. Custom Setup Capture Error Trap under Log Shooting / S-Log3 / PPLUT1..4
    slog3_gamma_override = (
        isinstance(picture_profile_gamma, str)
        and picture_profile_gamma.strip().upper() == "S-LOG3"
    )
    capture_trap = resolved["custom_wb_capture_blocked"] or (
        bool(custom_wb_setup_executed) and slog3_gamma_override
    )
    if capture_trap:
        _add_code(codes, STATUS_BLOCKED_G116_LOG_CUSTOM_WB_CAPTURE_TRAP)
        errors.append(
            "Executing [Custom Setup] while [Log Shooting] != Off or S-Log3 / PPLUT1..4 "
            "is active triggers the custom WB setup error trap."
        )

    # 3. Reset & Save/Load Settings (CAMSET) Boundary Guard
    if (
        claimed_custom_wb_saved_to_camset
        or claimed_camera_reset_wipes_custom_wb_slots
        or claimed_camera_reset_resets_shutter_awb_lock
        or claimed_camera_reset_resets_ael_w_shutter
    ):
        _add_code(codes, STATUS_BLOCKED_G116_WB_OR_METERING_RESET_CAMSET_BOUNDARY_VIOLATION)
        errors.append(
            "Custom 1..3 memorized WB data, Still [Shutter AWB Lock], and Still "
            "[AEL w/ Shutter] survive [Camera Settings Reset], and Custom 1..3 "
            "CANNOT be saved to Save/Load Settings (CAMSET)."
        )

    # 4. Metering Mode, De-Squeeze Face-Priority Lockout, Spot Point & Cine EI Base ISO Invariance
    norm_claimed_face = (
        _norm_on_off_phase280(claimed_effective_face_priority_in_multi)
        if claimed_effective_face_priority_in_multi is not None
        else None
    )
    norm_claimed_spot = (
        _norm_spot_metering_point_g116(claimed_effective_spot_metering_point)
        if claimed_effective_spot_metering_point is not None
        else None
    )
    norm_claimed_meter = (
        _norm_metering_mode_g116(claimed_effective_metering_mode)
        if claimed_effective_metering_mode is not None
        else None
    )
    cine_ei_active = norm_log in (LOG_SHOOTING_CINE_EI_G115, LOG_SHOOTING_CINE_EI_QUICK_G115)
    base_iso_invalid = cine_ei_active and (
        isinstance(cine_ei_base_iso, bool)
        or cine_ei_base_iso not in CINE_EI_BASE_ISOS_G116
    )

    if (
        (
            norm_desq is not None
            and norm_desq != "Off"
            and norm_claimed_face is not None
            and norm_claimed_face != FACE_PRIORITY_MULTI_OFF_G116
        )
        or (
            norm_focus in SPOT_METERING_CENTER_LOCKED_FOCUS_AREAS_G116
            and norm_claimed_spot is not None
            and norm_claimed_spot != SPOT_METERING_POINT_CENTER_G116
        )
        or (
            (norm_shoot == SHOOT_MODE_INTELLIGENT_AUTO_PHASE280 or non_optical_zoom_active)
            and norm_claimed_meter is not None
            and norm_claimed_meter != METERING_MODE_MULTI_G116
        )
        or base_iso_invalid
        or (cine_ei_active and claimed_metering_alters_cine_ei_recording_iso)
    ):
        _add_code(codes, STATUS_BLOCKED_G116_METERING_OR_CINE_EI_BASE_ISO_VIOLATION)
        errors.append(
            "[Face Priority in Multi Metering] is hard-locked Off when [De-Squeeze "
            "Display] != Off; [Spot Metering Point] locks to Center on Wide/Zone/Center "
            "Fix; under Cine EI Base ISO (800/12800), metering drives M.M. monitoring "
            "only without altering recording ISO/gain."
        )

    valid = not codes
    status = STATUS_VERIFIED_G116 if valid else codes[0]

    return WbCineEiAndMeteringGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}"
        if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
        else "invalid",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        fx6_comparison_fw_version=fx6_comparison_fw_version,
        reset_action=resolved["reset_action"],
        white_balance_menu_path=WHITE_BALANCE_MENU_PATH_G116,
        priority_awb_menu_path=PRIORITY_SET_IN_AWB_MENU_PATH_G116,
        shutter_awb_lock_menu_path=SHUTTER_AWB_LOCK_MENU_PATH_G116,
        shockless_wb_menu_path=SHOCKLESS_WB_MENU_PATH_G116,
        metering_mode_menu_path=METERING_MODE_MENU_PATH_G116,
        face_priority_multi_menu_path=FACE_PRIORITY_MULTI_METERING_MENU_PATH_G116,
        spot_metering_point_menu_path=SPOT_METERING_POINT_MENU_PATH_G116,
        ael_w_shutter_menu_path=AEL_W_SHUTTER_MENU_PATH_G116,
        shoot_mode=norm_shoot or str(shoot_mode),
        log_shooting=norm_log or str(log_shooting),
        picture_profile=norm_pp or str(picture_profile),
        requested_white_balance=norm_wb or str(requested_white_balance),
        effective_white_balance=resolved["effective_white_balance"],
        color_temp_k=int(color_temp_k) if not isinstance(color_temp_k, bool) else -1,
        wb_ab_trim=int(wb_ab_trim) if not isinstance(wb_ab_trim, bool) else 0,
        wb_gm_trim=int(wb_gm_trim) if not isinstance(wb_gm_trim, bool) else 0,
        effective_priority_set_in_awb=resolved["effective_priority_set_in_awb"],
        effective_shutter_awb_lock=resolved["effective_shutter_awb_lock"],
        effective_shockless_wb=resolved["effective_shockless_wb"],
        custom_wb_slots_memorized_after_reset=resolved["custom_wb_slots_memorized_after_reset"],
        custom_wb_excluded_from_camset=not claimed_custom_wb_saved_to_camset,
        custom_wb_setup_executed=bool(custom_wb_setup_executed),
        custom_wb_capture_blocked=bool(capture_trap),
        cine_ei_awb_blocked=resolved["cine_ei_awb_blocked"],
        fx3_exact_6_metering_modes=FX3_EXACT_6_METERING_MODES_G116,
        requested_metering_mode=norm_metering or str(requested_metering_mode),
        effective_metering_mode=resolved["effective_metering_mode"],
        desqueeze_display=norm_desq or str(desqueeze_display),
        effective_face_priority_in_multi=resolved["effective_face_priority_in_multi"],
        focus_area=norm_focus or str(focus_area),
        effective_spot_metering_point=resolved["effective_spot_metering_point"],
        effective_ael_w_shutter=resolved["effective_ael_w_shutter"],
        exposure_std_adjust_ev=float(exposure_std_adjust_ev)
        if not isinstance(exposure_std_adjust_ev, bool)
        and isinstance(exposure_std_adjust_ev, (int, float))
        else 0.0,
        cine_ei_base_iso=int(cine_ei_base_iso)
        if not isinstance(cine_ei_base_iso, bool)
        else -1,
        cine_ei_recording_iso_locked=resolved["cine_ei_recording_iso_locked"],
        metering_drives_mm_monitoring_only=resolved["metering_drives_mm_monitoring_only"],
        fx6_preset_custom_kelvins=FX6_PRESET_CUSTOM_KELVINS_G116,
        fx6_preset_cine_ei_kelvins=FX6_PRESET_CINE_EI_KELVINS_G116,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g116_wb_cineei_and_metering_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    wb_metering_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase280DonorAuditResult] = None,
) -> Tuple[GateVerdict, G116WbCineEiAndMeteringGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase280_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_wb_cineei_and_metering_guard(**dict(wb_metering_kwargs or {}))

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G116.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G116 if valid else codes[0]

    res = G116WbCineEiAndMeteringGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        wb_cineei_and_metering_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, wb={guard.effective_white_balance}"
        f"({guard.color_temp_k}K,awb_prio={guard.effective_priority_set_in_awb},"
        f"shockless={guard.effective_shockless_wb},cine_ei_blk={guard.cine_ei_awb_blocked}), "
        f"metering={guard.effective_metering_mode}(modes={len(guard.fx3_exact_6_metering_modes)},"
        f"face_prio={guard.effective_face_priority_in_multi},spot_pt={guard.effective_spot_metering_point})"
    )
    verdict = GateVerdict(
        gate_id=G116_GATE_ID,
        gate_code=G116_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `116`-Gate Master Safety Preflight (`G01..G116`)
# ---------------------------------------------------------------------------


def evaluate_116gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    pp_creativelook_dro_kwargs: Optional[Mapping[str, Any]] = None,
    wb_metering_kwargs: Optional[Mapping[str, Any]] = None,
    master_114_override: Optional[Master114GateReport] = None,
    **m114_passthrough_kwargs: Any,
) -> Master116GateReport:
    """Evaluate all 116 Master Safety Gates (`G01..G116`) deterministically by
    delegating `G01..G114` directly to `evaluate_114gate_preflight()`.
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

    m114_report: Master114GateReport = (
        master_114_override
        if master_114_override is not None
        else evaluate_114gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m114_passthrough_kwargs,
        )
    )

    phase280_audit = audit_phase280_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g115_verdict, g115_res = evaluate_g115_pp_scinetone_creativelook_dro_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        pp_creativelook_dro_kwargs=pp_creativelook_dro_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase280_audit,
    )

    g116_verdict, g116_res = evaluate_g116_wb_cineei_and_metering_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        wb_metering_kwargs=wb_metering_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase280_audit,
    )

    gates_115_to_116 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g115_verdict, g116_verdict)
    ]
    all_gates = tuple(list(m114_report.gates) + gates_115_to_116)

    g01_to_g12_verified = int(m114_report.summary["g01_to_g12_verified"])
    g13_to_g114_verified = int(m114_report.summary["g13_to_g112_verified"]) + int(
        m114_report.summary["g113_to_g114_verified"]
    )
    g115_to_g116_verified = sum(1 for v in (g115_verdict, g116_verdict) if v.passed)
    total_verified = (
        g01_to_g12_verified + g13_to_g114_verified + g115_to_g116_verified
    )

    g115_to_g116_all_passed = g115_to_g116_verified == 2
    g13_to_g116_all_passed = (
        m114_report.g13_to_g114_all_passed and g115_to_g116_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m114_report.gates[:9])

    offline_113_verified = (
        g01_to_g09_ok
        and m114_report.offline_111_gates_verified
        and g115_to_g116_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_116_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g116_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m114_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_113_verified
        and m114_report.h0_h1_trial_entry_allowed
        and g115_to_g116_all_passed
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
        list(m114_report.errors)
        + list(g115_verdict.errors)
        + list(g116_verdict.errors)
    )
    warnings: List[str] = (
        list(m114_report.warnings)
        + list(g115_verdict.warnings)
        + list(g116_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m114_report.g13_to_g114_all_passed:
        overall_status = m114_report.status
    elif not g115_verdict.passed:
        overall_status = g115_verdict.status
    elif not g116_verdict.passed:
        overall_status = g116_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_116_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_116_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_116_verified:
        overall_status = "VERIFIED_ALL_116_GATES"
    else:
        overall_status = "VERIFIED_113_OF_116_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m114_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g115_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g116_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 116,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 116 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g114_verified": g13_to_g114_verified,
        "g115_to_g116_verified": g115_to_g116_verified,
        "g13_to_g116_all_passed": g13_to_g116_all_passed,
        "g115_to_g116_all_passed": g115_to_g116_all_passed,
        "offline_113_gates_verified": offline_113_verified,
        "all_116_gates_verified": all_116_verified,
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

    return Master116GateReport(
        schema=REALHW_PP_SCINETONE_CREATIVELOOK_DRO_WB_METERING_116GATE_SCHEMA,
        version=REALHW_PP_SCINETONE_CREATIVELOOK_DRO_WB_METERING_116GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_113_gates_verified=offline_113_verified,
        all_116_gates_verified=all_116_verified,
        g13_to_g116_all_passed=g13_to_g116_all_passed,
        g115_to_g116_all_passed=g115_to_g116_all_passed,
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
        master_114_report=m114_report.to_dict(),
        g115_result=g115_res.to_dict(),
        g116_result=g116_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_116_master_safety_gates = evaluate_116gate_preflight
run_116_gate_preflight = evaluate_116gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard",
        description=(
            "Phase 280 (280th Milestone, 116/116 Safety Gates, Wave-48) Gates G115 "
            "([Picture Profile] PP11 S-Cinetone Default vs [Creative Look] 10 Looks & "
            "[D-Range Optimizer] under [Log Shooting] + PPLUT1..4 / Reset Trap) + G116 "
            "([White Balance] 2500K..9900K, Custom 1..3, Cine EI Lockout & [Metering Mode] "
            "6 Modes, De-Squeeze Face-Priority Lockout & Cine EI Base ISO M.M. Rule) + "
            "Unified 116-Gate Master Safety Preflight"
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

    report = evaluate_116gate_preflight(
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
            f"verified={report.summary['verified_gates']}/116 "
            f"g115_to_g116_all_passed={report.g115_to_g116_all_passed} "
            f"all_116_gates_verified={report.all_116_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = (
        report.all_116_gates_verified
        if args.dry_run_simulated
        else report.offline_113_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
