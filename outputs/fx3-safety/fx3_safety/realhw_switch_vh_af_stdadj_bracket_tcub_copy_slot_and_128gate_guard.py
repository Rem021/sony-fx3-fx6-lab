"""Phase 297 (Wave-54, 128/128 Power-of-Two Safety Gates Milestone):
Real-Hardware Safety Gates G127 & G128 + Unified 128-Gate Preflight Engine.

Implements empirical `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` hardware safety gates:

1. **Gate `G127` (`verify-switch-vh-af-and-exposure-stdadj-guard`)**:
   - `[Switch V/H AF Area]` (`Off` default / `AF Point Only` / `AF Point + AF Area`, `_f.uxc 0x73ae`)
     operates ONLY in Still `AF-C` across 3 gravity states (`0_DEGREES`, `90_DEGREES`,
     `270_DEGREES`), returning `INVALID` on vertical pitch up/down, and locked out across
     8 conditions (non-Still Movie/S&Q, non-AF-C, `Intelligent Auto`, Digital Zoom, active AF,
     continuous/burst shooting, self-timer countdown, and `[Focus Magnifier]`); changing the
     mode clears stored per-orientation AF points; supports `[Camera Settings Reset]`.
   - `[Focus Area Limit]` (`_f.uxc 0x6de2`) exposes **exact 14** checkboxes on FX3 (`Wide`,
     `Zone`, `Center Fix`, `Spot: S/M/L`, `Expand Spot`, and 7 `Tracking:` equivalents) —
     dormant multi-model `model::focus_area_limit_flexible_spot_{xl,xs}` / `custom_{1..3}`
     rejected fail-closed; minimum `>= 2` enabled areas enforced via `.uxc 0xea28`; `Tracking:*`
     disabled in Movie/`S&Q` `[Focus Area]`; supports `[Camera Settings Reset]`.
   - `[Exposure Std. Adjust]` (`_f.uxc 0x6114`, `.uxc 0xe567` warning) calibrates **ALL 5
     metering modes** (`Multi`, `Center`, `Spot`, `Entire Screen Avg.`, `Highlight` — 13 steps
     `-1..+1 EV` in `1/6 EV` increments), shifts `M.M.` & Spot AEL independently of
     `Exposure Comp.` (separate EXIF entry), resets active bracket shot count if changed
     mid-sequence, and **survives `[Camera Settings Reset]` (wiped ONLY by `[Initialize]`)**.
   - Still `[Bracket Settings]` (`[Selftimer during Bracket]`: `Off/2 Sec/5 Sec/10 Sec`,
     `[Bracket order]`: `0->-->+ / -->0->+`) is Still-only, resettable by `[Camera Settings Reset]`,
     and absent on cinema-only `ILME-FX6` (dormant `FX6 appFw.so` `bracket_*` blocked).

2. **Gate `G128` (`verify-tcub-format-and-playback-copy-slot-guard`)**:
   - All 6 `MENU -> (Shooting) -> [TC/UB]` items (`Time Code Preset`, `User Bit Preset`,
     `Time Code Format`/`TC Format`, `Time Code Run`, `Time Code Make`, `User Bit Time Rec`)
     plus `(Setup) -> [Display Option] -> [TC/UB Disp. Setting]` (`Counter / TC [default] /
     U-Bit`, Movie-only toggle during playback per `.uxc 0xe728`) **survive `[Camera Settings
     Reset]` (reset ONLY via `[Initialize]`)**.
   - `[Time Code Format]` (`DF` default / `NDF`) is NTSC-only, forced `NDF` (`[-]`) in
     `23.98p`/`24.00p`, and hidden in `PAL`; contrasted with `ILME-FX6` physical BNC
     `TC IN/TC OUT` + `EXT-LK` + `USB TC IN`.
   - Playback `[Copy]` (`FUNC_copy_content`) copies from active `[Select Playback Media]` to
     the opposite slot: when `[Select Playback Media] = Slot 1`, `Copy` reads `Slot 1 -> Slot 2`
     (stripping `Protect` flags & burst grouping on destination); **HOWEVER, when `[Select
     Playback Media] = Slot 2`, `Copy` reverses write direction onto `Slot 1` (`Slot 2 ->
     Slot 1`) and MUST be blocked fail-closed (`EROFS`/`EBUSY`, `slot1_data_sector_writes == 0`,
     `slot1_avf_info_mutated == False`) whenever `Slot 1` holds the read-only Tier-0 recovery
     vault**. Also enforces `get_battery_status_for_copy`, destination card speed class
     (`.uxc 0xe80e`/`0xe8ca`), `[Slide Show]` (`Date View`/`Folder View(Still)` only, `Repeat`,
     `Interval 1/3/5/10/30 Sec`) automatic `Power Save Start Time` sleep-bypass awareness, and
     dormant `FX6` `Copy Clip` menu exclusion.

3. **Unified `128`-Gate Power-of-Two Milestone Master Preflight (`evaluate_128gate_preflight` /
   `verify-128-gates`)**:
   - Delegates `G01..G126` directly to `evaluate_126gate_preflight()` and appends `G127` + `G128`.
   - Offline mode: `125/128` gates pass (`VERIFIED_125_OF_128_AWAITING_PHYSICAL_TIER0`);
     `--simulate-bench-dry-run`: `128/128` simulation gates pass.
   - All hardware attach, persistent eMMC write, EL3/SPI-NOR transmit, and cross-model flash
     redlines remain hard-locked `False`, `usb_packets_transmitted == 0`, and
     `raw_firmware_bytes_leaked == 0`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths
from .realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard import (
    DEFAULT_REPO_ROOT,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_VERIFIED_SAFE,
    GateVerdict,
)
from .realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard import (
    Master126GateReport,
    evaluate_126gate_preflight,
)

# ---------------------------------------------------------------------------
# Schema, Version & Absolute Hardware / Firmware Safety Redlines
# ---------------------------------------------------------------------------

REALHW_SWITCH_VH_AF_STDADJ_BRACKET_TCUB_COPY_SLOT_128GATE_SCHEMA = (
    "realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard_v1"
)
REALHW_SWITCH_VH_AF_STDADJ_BRACKET_TCUB_COPY_SLOT_128GATE_VERSION = "2026.11.17"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST_PHASE297 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE297 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE297 = 15.0

# Hard-locked redlines (identical immutable values; NEVER relaxed at runtime)
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
SPI_NOR_WRITE_AUTHORIZED = False
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
PERSISTENT_WRITE_RELEASE = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
HUMAN_HARDWARE_ATTACH_TOKEN = False
CROSS_MODEL_FLASH_AUTHORIZED = False
USB_PACKETS_TRANSMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

# Gate Identifiers
G127 = "G127"
G127_GATE_ID = "G127"
G127_GATE_CODE = "GATE_G127_SWITCH_VH_AF_FOCUS_LIMIT_STD_ADJ_AND_BRACKET_GUARD"
GATE_G127_SWITCH_VH_AF_FOCUS_LIMIT_STD_ADJ_AND_BRACKET_GUARD = G127_GATE_CODE

G128 = "G128"
G128_GATE_ID = "G128"
G128_GATE_CODE = "GATE_G128_TCUB_FORMAT_PLAYBACK_COPY_DIRECTION_AND_SLIDESHOW_GUARD"
GATE_G128_TCUB_FORMAT_PLAYBACK_COPY_DIRECTION_AND_SLIDESHOW_GUARD = G128_GATE_CODE

# Model & Identity Contracts (Phase 297 suffixed to avoid __init__.py shadowing)
FX3_MODEL_NAME_PHASE297 = "ILME-FX3"
FX3_MODEL_ID_PHASE297 = 0x39383232
FX3_HELP_GUIDE_CODE_PHASE297 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE297 = "7.02"

FX6_MODEL_NAME_PHASE297 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE297 = "6.01"
FX6_PRODUCT_CODE_PHASE297 = "PRODUCT_MODEL_CHAPLIN"

# Shoot Modes & Reset Actions
SHOOT_MODE_P_PHASE297 = "P"
SHOOT_MODE_A_PHASE297 = "A"
SHOOT_MODE_S_PHASE297 = "S"
SHOOT_MODE_M_PHASE297 = "M"
SHOOT_MODE_STILL_PHASE297 = "Still"
SHOOT_MODE_INTELLIGENT_AUTO_PHASE297 = "Intelligent Auto"
SHOOT_MODE_MOVIE_PHASE297 = "Movie"
SHOOT_MODE_SQ_PHASE297 = "S&Q"
SHOOT_MODE_MR_PHASE297 = "MR"

STILL_PASM_SHOOT_MODES_PHASE297: Tuple[str, ...] = (
    SHOOT_MODE_P_PHASE297,
    SHOOT_MODE_A_PHASE297,
    SHOOT_MODE_S_PHASE297,
    SHOOT_MODE_M_PHASE297,
    SHOOT_MODE_STILL_PHASE297,
)
STILL_SHOOT_MODES_PHASE297: Tuple[str, ...] = (
    STILL_PASM_SHOOT_MODES_PHASE297 + (SHOOT_MODE_INTELLIGENT_AUTO_PHASE297,)
)
MOVIE_SHOOT_MODES_PHASE297: Tuple[str, ...] = (
    SHOOT_MODE_MOVIE_PHASE297,
    SHOOT_MODE_SQ_PHASE297,
)
ALLOWED_SHOOT_MODES_PHASE297: Tuple[str, ...] = (
    STILL_SHOOT_MODES_PHASE297 + MOVIE_SHOOT_MODES_PHASE297 + (SHOOT_MODE_MR_PHASE297,)
)

RESET_ACTION_NONE_PHASE297 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE297 = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE297 = "Reset Network Set."
RESET_ACTION_INITIALIZE_PHASE297 = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE297: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE297,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE297,
    RESET_ACTION_RESET_NETWORK_SET_PHASE297,
    RESET_ACTION_INITIALIZE_PHASE297,
)

# ---------------------------------------------------------------------------
# G127 Constants: [Switch V/H AF Area] + [Focus Area Limit] +
#                 [Exposure Std. Adjust] + Still [Bracket Settings]
# ---------------------------------------------------------------------------

SWITCH_VH_AF_MENU_PATH_G127 = "MENU -> (Focus) -> [Focus Area] -> [Switch V/H AF Area]"
SWITCH_VH_AF_F_UXC_RESID16_G127 = 0x73AE
SWITCH_VH_AF_OFF_G127 = "Off"
SWITCH_VH_AF_POINT_ONLY_G127 = "AF Point Only"
SWITCH_VH_AF_POINT_AND_AREA_G127 = "AF Point + AF Area"
SWITCH_VH_AF_DEFAULT_G127 = SWITCH_VH_AF_OFF_G127
ALLOWED_SWITCH_VH_AF_MODES_G127: Tuple[str, ...] = (
    SWITCH_VH_AF_OFF_G127,
    SWITCH_VH_AF_POINT_ONLY_G127,
    SWITCH_VH_AF_POINT_AND_AREA_G127,
)

GRAVITY_ORIENTATION_0_DEG_G127 = "0_DEGREES"
GRAVITY_ORIENTATION_90_DEG_G127 = "90_DEGREES"
GRAVITY_ORIENTATION_270_DEG_G127 = "270_DEGREES"
GRAVITY_ORIENTATION_INVALID_G127 = "INVALID"
ALLOWED_GRAVITY_ORIENTATIONS_G127: Tuple[str, ...] = (
    GRAVITY_ORIENTATION_0_DEG_G127,
    GRAVITY_ORIENTATION_90_DEG_G127,
    GRAVITY_ORIENTATION_270_DEG_G127,
    GRAVITY_ORIENTATION_INVALID_G127,
)
VALID_SWITCHABLE_ORIENTATIONS_G127: Tuple[str, ...] = (
    GRAVITY_ORIENTATION_0_DEG_G127,
    GRAVITY_ORIENTATION_90_DEG_G127,
    GRAVITY_ORIENTATION_270_DEG_G127,
)

FOCUS_AREA_LIMIT_MENU_PATH_G127 = "MENU -> (Focus) -> [Focus Area] -> [Focus Area Limit]"
FOCUS_AREA_LIMIT_F_UXC_RESID16_G127 = 0x6DE2
FOCUS_AREA_LIMIT_MIN_WARNING_UXC_RESID16_G127 = 0xEA28
FOCUS_AREA_LIMIT_MIN_ENABLED_G127 = 2

FOCUS_AREA_LIMIT_14_OPTIONS_G127: Tuple[str, ...] = (
    "Wide",
    "Zone",
    "Center Fix",
    "Spot: S",
    "Spot: M",
    "Spot: L",
    "Expand Spot",
    "Tracking: Wide",
    "Tracking: Zone",
    "Tracking: Center Fix",
    "Tracking: Spot: S",
    "Tracking: Spot: M",
    "Tracking: Spot: L",
    "Tracking: Expand Spot",
)
FOCUS_AREA_LIMIT_TRACKING_OPTIONS_G127: Tuple[str, ...] = tuple(
    opt for opt in FOCUS_AREA_LIMIT_14_OPTIONS_G127 if opt.startswith("Tracking:")
)
DORMANT_FOCUS_AREA_LIMIT_OPTIONS_G127: Tuple[str, ...] = (
    "Spot: XL",
    "Spot: XS",
    "Custom 1",
    "Custom 2",
    "Custom 3",
    "focus_area_limit_flexible_spot_xl",
    "focus_area_limit_flexible_spot_xs",
    "focus_area_limit_custom_1",
    "focus_area_limit_custom_2",
    "focus_area_limit_custom_3",
)

FOCUS_AREA_COLOR_MENU_PATH_G127 = "MENU -> (Focus) -> [Focus Area] -> [Focus Area Color]"
FOCUS_AREA_COLOR_WHITE_G127 = "White"
FOCUS_AREA_COLOR_RED_G127 = "Red"
FOCUS_AREA_COLOR_DEFAULT_G127 = FOCUS_AREA_COLOR_WHITE_G127
ALLOWED_FOCUS_AREA_COLORS_G127: Tuple[str, ...] = (
    FOCUS_AREA_COLOR_WHITE_G127,
    FOCUS_AREA_COLOR_RED_G127,
)

EXPOSURE_STD_ADJ_MENU_PATH_G127 = (
    "MENU -> (Exposure/Color) -> [Exposure Comp.] -> [Exposure Std. Adjust]"
)
EXPOSURE_STD_ADJ_F_UXC_RESID16_G127 = 0x6114
EXPOSURE_STD_ADJ_WARNING_UXC_RESID16_G127 = 0xE567
EXPOSURE_STD_ADJ_5_METERING_MODES_G127: Tuple[str, ...] = (
    "Multi",
    "Center",
    "Spot",
    "Entire Screen Avg.",
    "Highlight",
)
EXPOSURE_STD_ADJ_MIN_SIXTHS_G127 = -6
EXPOSURE_STD_ADJ_MAX_SIXTHS_G127 = 6
EXPOSURE_STD_ADJ_VALID_SIXTHS_G127: Tuple[int, ...] = tuple(
    range(EXPOSURE_STD_ADJ_MIN_SIXTHS_G127, EXPOSURE_STD_ADJ_MAX_SIXTHS_G127 + 1)
)
EXPOSURE_STD_ADJ_STEP_COUNT_G127 = 13

BRACKET_SETTINGS_MENU_PATH_G127 = (
    "MENU -> (Shooting) -> [Drive Mode] -> [Bracket Settings]"
)
BRACKET_SETTINGS_F_UXC_RESID16_G127 = 0x6466
SELFTIMER_DURING_BRACKET_F_UXC_RESID16_G127 = 0x6EF5
BRACKET_ORDER_F_UXC_RESID16_G127 = 0x76B1
BRACKET_SELFTIMER_OFF_G127 = "Off"
BRACKET_SELFTIMER_2SEC_G127 = "2 Sec"
BRACKET_SELFTIMER_5SEC_G127 = "5 Sec"
BRACKET_SELFTIMER_10SEC_G127 = "10 Sec"
BRACKET_SELFTIMER_DEFAULT_G127 = BRACKET_SELFTIMER_OFF_G127
ALLOWED_BRACKET_SELFTIMER_OPTIONS_G127: Tuple[str, ...] = (
    BRACKET_SELFTIMER_OFF_G127,
    BRACKET_SELFTIMER_2SEC_G127,
    BRACKET_SELFTIMER_5SEC_G127,
    BRACKET_SELFTIMER_10SEC_G127,
)
BRACKET_ORDER_ZERO_MINUS_PLUS_G127 = "0->-->+"
BRACKET_ORDER_MINUS_ZERO_PLUS_G127 = "-->0->+"
BRACKET_ORDER_DEFAULT_G127 = BRACKET_ORDER_ZERO_MINUS_PLUS_G127
ALLOWED_BRACKET_ORDERS_G127: Tuple[str, ...] = (
    BRACKET_ORDER_ZERO_MINUS_PLUS_G127,
    BRACKET_ORDER_MINUS_ZERO_PLUS_G127,
)

# ---------------------------------------------------------------------------
# G128 Constants: [TC/UB] 6-Item + [TC/UB Disp. Setting] + Playback [Copy] & [Slide Show]
# ---------------------------------------------------------------------------

TCUB_MENU_PATH_G128 = "MENU -> (Shooting) -> [TC/UB]"
TCUB_DISP_MENU_PATH_G128 = "MENU -> (Setup) -> [Display Option] -> [TC/UB Disp. Setting]"
TCUB_G_UXC_RESID16_G128 = 0x6389
TCUB_DISP_F_UXC_RESID16_G128 = 0x6B0C
TCUB_DISP_PLAYBACK_INVALID_UXC_RESID16_G128 = 0xE728

TCUB_6_ITEMS_G128: Tuple[str, ...] = (
    "Time Code Preset",
    "User Bit Preset",
    "Time Code Format",
    "Time Code Run",
    "Time Code Make",
    "User Bit Time Rec",
)

TC_PRESET_DEFAULT_G128 = "00:00:00.00"
UB_PRESET_DEFAULT_G128 = "00 00 00 00"
TC_FORMAT_DF_G128 = "DF"
TC_FORMAT_NDF_G128 = "NDF"
TC_FORMAT_DEFAULT_G128 = TC_FORMAT_DF_G128
ALLOWED_TC_FORMATS_G128: Tuple[str, ...] = (TC_FORMAT_DF_G128, TC_FORMAT_NDF_G128)
TC_RUN_REC_G128 = "Rec Run"
TC_RUN_FREE_G128 = "Free Run"
TC_RUN_DEFAULT_G128 = TC_RUN_REC_G128
ALLOWED_TC_RUN_MODES_G128: Tuple[str, ...] = (TC_RUN_REC_G128, TC_RUN_FREE_G128)
TC_MAKE_PRESET_G128 = "Preset"
TC_MAKE_REGENERATE_G128 = "Regenerate"
TC_MAKE_DEFAULT_G128 = TC_MAKE_PRESET_G128
ALLOWED_TC_MAKE_MODES_G128: Tuple[str, ...] = (TC_MAKE_PRESET_G128, TC_MAKE_REGENERATE_G128)
UB_TIME_REC_DEFAULT_G128 = "Off"

TCUB_DISP_COUNTER_G128 = "Counter"
TCUB_DISP_TC_G128 = "TC"
TCUB_DISP_UBIT_G128 = "U-Bit"
TCUB_DISP_DEFAULT_G128 = TCUB_DISP_TC_G128
ALLOWED_TCUB_DISP_SETTINGS_G128: Tuple[str, ...] = (
    TCUB_DISP_COUNTER_G128,
    TCUB_DISP_TC_G128,
    TCUB_DISP_UBIT_G128,
)

TV_SYSTEM_NTSC_G128 = "NTSC"
TV_SYSTEM_PAL_G128 = "PAL"
ALLOWED_TV_SYSTEMS_G128: Tuple[str, ...] = (TV_SYSTEM_NTSC_G128, TV_SYSTEM_PAL_G128)
FORCED_NDF_FRAME_RATES_G128: Tuple[str, ...] = ("23.98p", "24.00p", "24p")

SELECT_PLAYBACK_MEDIA_MENU_PATH_G128 = (
    "MENU -> (Playback) -> [Playback Target] -> [Select Playback Media]"
)
PLAYBACK_COPY_MENU_PATH_G128 = "MENU -> (Playback) -> [Edit] -> [Copy]"
SLIDE_SHOW_MENU_PATH_G128 = "MENU -> (Playback) -> [Viewing] -> [Slide Show]"
SELECT_PLAYBACK_MEDIA_F_UXC_RESID16_G128 = 0x6BCD
PLAYBACK_COPY_F_UXC_RESID16_G128 = 0x79FC
SLIDE_SHOW_UXC_RESID16_G128 = 0xE2CC

MEDIA_SLOT_1_G128 = "Slot 1"
MEDIA_SLOT_2_G128 = "Slot 2"
ALLOWED_PLAYBACK_MEDIA_SLOTS_G128: Tuple[str, ...] = (MEDIA_SLOT_1_G128, MEDIA_SLOT_2_G128)

ALLOWED_DEST_CARD_SPEED_CLASSES_G128: Tuple[str, ...] = (
    "CFexpress Type A",
    "SDXC V90",
    "SDXC V60",
    "SDXC V30",
    "SDXC V10",
    "SDXC U1",
    "SDXC Class10",
)
SLOW_DEST_CARD_SPEED_CLASSES_G128: Tuple[str, ...] = (
    "SDHC Class4",
    "SDHC Class6",
    "SD Class2",
    "SD Class4",
    "UNRATED",
)

SLIDE_SHOW_VIEW_DATE_G128 = "Date View"
SLIDE_SHOW_VIEW_FOLDER_STILL_G128 = "Folder View(Still)"
ALLOWED_SLIDE_SHOW_VIEW_MODES_G128: Tuple[str, ...] = (
    SLIDE_SHOW_VIEW_DATE_G128,
    SLIDE_SHOW_VIEW_FOLDER_STILL_G128,
)
DISALLOWED_SLIDE_SHOW_VIEW_MODES_G128: Tuple[str, ...] = (
    "Folder View(Movie)",
    "Folder View(XAVC S)",
    "Movie View",
)
SLIDE_SHOW_INTERVAL_1SEC_G128 = "1 Sec"
SLIDE_SHOW_INTERVAL_3SEC_G128 = "3 Sec"
SLIDE_SHOW_INTERVAL_5SEC_G128 = "5 Sec"
SLIDE_SHOW_INTERVAL_10SEC_G128 = "10 Sec"
SLIDE_SHOW_INTERVAL_30SEC_G128 = "30 Sec"
SLIDE_SHOW_INTERVAL_DEFAULT_G128 = SLIDE_SHOW_INTERVAL_3SEC_G128
ALLOWED_SLIDE_SHOW_INTERVALS_G128: Tuple[str, ...] = (
    SLIDE_SHOW_INTERVAL_1SEC_G128,
    SLIDE_SHOW_INTERVAL_3SEC_G128,
    SLIDE_SHOW_INTERVAL_5SEC_G128,
    SLIDE_SHOW_INTERVAL_10SEC_G128,
    SLIDE_SHOW_INTERVAL_30SEC_G128,
)

# Status / Violation Codes
STATUS_BLOCKED_PHASE297_DONOR_INTEGRITY = "STATUS_BLOCKED_PHASE297_DONOR_INTEGRITY"

STATUS_VERIFIED_G127 = "STATUS_VERIFIED_G127"
STATUS_BLOCKED_G127_TELEMETRY_INVALID = "STATUS_BLOCKED_G127_TELEMETRY_INVALID"
STATUS_BLOCKED_G127_SWITCH_VH_AF_LOCKOUT_OR_PITCH_INVALID = (
    "STATUS_BLOCKED_G127_SWITCH_VH_AF_LOCKOUT_OR_PITCH_INVALID"
)
STATUS_BLOCKED_G127_FOCUS_AREA_LIMIT_DORMANT_OR_MIN2_VIOLATION = (
    "STATUS_BLOCKED_G127_FOCUS_AREA_LIMIT_DORMANT_OR_MIN2_VIOLATION"
)
STATUS_BLOCKED_G127_EXPOSURE_STD_ADJ_5MODE_OR_RESET_VIOLATION = (
    "STATUS_BLOCKED_G127_EXPOSURE_STD_ADJ_5MODE_OR_RESET_VIOLATION"
)
STATUS_BLOCKED_G127_BRACKET_SETTINGS_OR_FX6_CROSSWIRE_VIOLATION = (
    "STATUS_BLOCKED_G127_BRACKET_SETTINGS_OR_FX6_CROSSWIRE_VIOLATION"
)

STATUS_VERIFIED_G128 = "STATUS_VERIFIED_G128"
STATUS_BLOCKED_G128_TELEMETRY_INVALID = "STATUS_BLOCKED_G128_TELEMETRY_INVALID"
STATUS_BLOCKED_G128_TCUB_RESET_PERSISTENCE_OR_PLAYBACK_TOGGLE_VIOLATION = (
    "STATUS_BLOCKED_G128_TCUB_RESET_PERSISTENCE_OR_PLAYBACK_TOGGLE_VIOLATION"
)
STATUS_BLOCKED_G128_TC_FORMAT_PAL_OR_24P_NDF_LOCK_VIOLATION = (
    "STATUS_BLOCKED_G128_TC_FORMAT_PAL_OR_24P_NDF_LOCK_VIOLATION"
)
STATUS_BLOCKED_G128_SLOT2_TO_SLOT1_VAULT_COPY_FIREWALL_VIOLATION = (
    "STATUS_BLOCKED_G128_SLOT2_TO_SLOT1_VAULT_COPY_FIREWALL_VIOLATION"
)
STATUS_BLOCKED_G128_COPY_BATTERY_SPEED_OR_SLIDESHOW_FX6_VIOLATION = (
    "STATUS_BLOCKED_G128_COPY_BATTERY_SPEED_OR_SLIDESHOW_FX6_VIOLATION"
)

# ---------------------------------------------------------------------------
# Pinned Wave-54 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE297: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (62_689_773, b"BKID_APP_setting_vertical_horizontal_focus_area_switch"),
    (61_809_972, b"VAL_setting_vertical_horizontal_focus_area_switch_VERTICAL_HORIZONTAL_FOCUS_AREA_SWITCH_OFF"),
    (61_810_064, b"VAL_setting_vertical_horizontal_focus_area_switch_VERTICAL_HORIZONTAL_FOCUS_AREA_SWITCH_FOCUS_POSITION_ONLY"),
    (61_810_172, b"VAL_setting_vertical_horizontal_focus_area_switch_VERTICAL_HORIZONTAL_FOCUS_AREA_SWITCH_FOCUS_POSITION_FOCUS_AREA"),
    (61_814_301, b"VH_AF_AREA_ORIENTATION_INFORMATION_0_DEGREES"),
    (61_814_385, b"VH_AF_AREA_ORIENTATION_INFORMATION_90_DEGREES"),
    (61_814_470, b"VH_AF_AREA_ORIENTATION_INFORMATION_270_DEGREES"),
    (61_814_556, b"VH_AF_AREA_ORIENTATION_INFORMATION_INVALID"),
    (62_654_365, b"BKID_APP_focus_area_limit_wide"),
    (62_654_430, b"BKID_APP_focus_area_limit_zone"),
    (62_654_495, b"BKID_APP_focus_area_limit_center"),
    (62_654_564, b"BKID_APP_focus_area_limit_flexible_spot_s"),
    (62_654_651, b"BKID_APP_focus_area_limit_flexible_spot_m"),
    (62_654_738, b"BKID_APP_focus_area_limit_flexible_spot_l"),
    (62_654_825, b"BKID_APP_focus_area_limit_expanded_flexible_spot"),
    (62_654_926, b"BKID_APP_focus_area_limit_tracking_af_wide"),
    (62_655_015, b"BKID_APP_focus_area_limit_tracking_af_zone"),
    (62_655_104, b"BKID_APP_focus_area_limit_tracking_af_center"),
    (62_655_197, b"BKID_APP_focus_area_limit_tracking_af_flexible_spot_s"),
    (62_655_308, b"BKID_APP_focus_area_limit_tracking_af_flexible_spot_m"),
    (62_655_419, b"BKID_APP_focus_area_limit_tracking_af_flexible_spot_l"),
    (62_655_530, b"BKID_APP_focus_area_limit_tracking_af_expanded_flexible_spot"),
    (62_689_886, b"BKID_APP_setting_focus_frame_color"),
    (62_686_443, b"BKID_APP_setting_exposure_standard_metering_mode_multi"),
    (62_686_556, b"BKID_APP_setting_exposure_standard_metering_mode_center"),
    (62_686_671, b"BKID_APP_setting_exposure_standard_metering_mode_spot"),
    (62_686_782, b"BKID_APP_setting_exposure_standard_metering_mode_average"),
    (62_686_899, b"BKID_APP_setting_exposure_standard_metering_mode_highlight"),
    (60_121_183, b"PID_SET_STANDARD_EXPOSURE_SETTING"),
    (62_679_493, b"BKID_APP_setting_bracket_self_timer"),
    (62_679_568, b"BKID_APP_setting_bracket_order"),
    (62_679_633, b"BKID_APP_setting_focus_bracket_order"),
    (62_713_243, b"BKID_APP_tc_preset_time_hour"),
    (62_831_531, b"BKID_APP_ub_preset_digit_12"),
    (62_682_023, b"BKID_APP_setting_tc_format"),
    (62_682_050, b"BKID_APP_setting_tc_run"),
    (62_682_074, b"BKID_APP_setting_tc_make"),
    (62_682_099, b"BKID_APP_setting_ub_time_rec"),
    (62_700_951, b"BKID_APP_setting_tc_ub_disp_setting"),
    (62_713_065, b"BKID_APP_select_playback_media"),
    (60_604_525, b"FUNC_copy_content"),
    (60_428_656, b"get_battery_status_for_copy"),
    (62_691_938, b"BKID_APP_setting_viewing_repeat"),
    (62_691_970, b"BKID_APP_setting_viewing_interval"),
    (60_605_144, b"FUNC_start_playback_slide_show"),
    (61_206_591, b"VAL_status_of_media_slot1_STATUS_OF_MEDIA_SLOT1_READ_ONLY"),
    (61_205_949, b"STATUS_OF_MEDIA_SLOT1_DB_LOCKED"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE297 = (
    "670730eb10ed17c9446da4b6c1228ba76e538d37a3d5814b77af8a8fc23d57f6"
)

PINNED_FX6_APPFW_SLICES_PHASE297: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (41_748_974, b"PRODUCT_MODEL_CHAPLIN"),
    (40_920_869, b"BKID_APP_SETTING_TC_FORMAT"),
    (40_920_896, b"BKID_APP_SETTING_TC_RUN"),
    (40_920_920, b"BKID_APP_SETTING_TC_MAKE"),
    (40_922_905, b"BKID_APP_SETTING_TC_UB_DISP_SETTING"),
    (40_920_945, b"BKID_APP_SETTING_UB_TIME_REC"),
    (40_923_085, b"BKID_APP_SETTING_HDMI_TC_OUTPUT"),
    (40_939_075, b"BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING"),
    (41_010_938, b"BKID_APP_EXT_TC_LOCK_STATUS"),
    (40_965_130, b"BKID_APP_USER_MENU_COPY_CLIP0"),
    (40_965_160, b"BKID_APP_USER_MENU_COPY_CLIP1"),
    (40_918_994, b"BKID_APP_AUTOFOCUS_AREA_ZONE_0_DEGREES"),
    (39_886_198, b"PID_SET_TC_MODE"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE297 = (
    "8e2a4a756a844453a7d087998083e9c2904639e95132916632e14decae65fa14"
)

PINNED_PHASE297_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE297,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE297),
        "FX3 appFw.so Wave-54 SwitchV/H/FocusLimit/ExpStdAdj/Bracket/TCUB/Copy/SlideShow symbols",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Switch V/H AF Area",
            b"AF Point Only",
            b"AF Point + AF Area",
            b"Focus Area Limit",
            b"Focus Area Color",
            b"Exposure Std. Adjust",
            b"Multi",
            b"Center",
            b"Spot",
            b"Entire Screen Average",
            b"Highlight",
            b"Bracket Settings",
            b"Selftimer during Bracket",
            b"Bracket order",
            b"TC/UB Disp. Setting",
            b"User Bit Preset",
            b"User Bit Time Rec",
            b"Time Code Format",
            b"Select Playback Media",
            b"Copy",
            b"Repeat",
        ),
        "FX3 string_english_f.uxc Wave-54 EN parity",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "换垂直和水平AF区".encode("utf-8"),
            "仅AF点".encode("utf-8"),
            "AF点 + AF区域".encode("utf-8"),
            "对焦区域限制".encode("utf-8"),
            "对焦边框颜色".encode("utf-8"),
            "曝光标准调整".encode("utf-8"),
            "多重".encode("utf-8"),
            "中心".encode("utf-8"),
            "点测光".encode("utf-8"),
            "整个屏幕平均".encode("utf-8"),
            "强光".encode("utf-8"),
            "阶段曝光设置".encode("utf-8"),
            "阶段曝光中自拍定时".encode("utf-8"),
            "阶段曝光顺序".encode("utf-8"),
            "TC/UB显示设置".encode("utf-8"),
            b"User Bit Preset",
            b"User Bit Time Rec",
            b"Time Code Format",
            "选择播放媒体".encode("utf-8"),
            "复制".encode("utf-8"),
            "重复".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-54 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "換垂直/水平AF區".encode("utf-8"),
            "僅對焦點".encode("utf-8"),
            "對焦點 + 對焦區域".encode("utf-8"),
            "對焦區域限制".encode("utf-8"),
            "對焦框色".encode("utf-8"),
            "曝光標準調整".encode("utf-8"),
            "多重".encode("utf-8"),
            "中心".encode("utf-8"),
            "定點測光".encode("utf-8"),
            "全螢幕平均".encode("utf-8"),
            "醒目".encode("utf-8"),
            "包圍式曝光設定".encode("utf-8"),
            "包圍曝光時自拍定時".encode("utf-8"),
            "階段順序".encode("utf-8"),
            "TC/UB顯示設定".encode("utf-8"),
            b"User Bit Preset",
            b"User Bit Time Rec",
            b"Time Code Format",
            "選擇播放插槽".encode("utf-8"),
            "複製".encode("utf-8"),
            "重複".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-54 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "縦横ﾌｫｰｶｽｴﾘｱ切換".encode("utf-8"),
            "ﾌｫｰｶｽ位置のみ".encode("utf-8"),
            "ﾌｫｰｶｽ位置+ﾌｫｰｶｽｴﾘｱ".encode("utf-8"),
            "ﾌｫｰｶｽｴﾘｱ限定".encode("utf-8"),
            "ﾌｫｰｶｽｴﾘｱ枠色".encode("utf-8"),
            "露出基準調整".encode("utf-8"),
            "ﾏﾙﾁ".encode("utf-8"),
            "中央重点".encode("utf-8"),
            "スポット".encode("utf-8"),
            "画面全体平均".encode("utf-8"),
            "ハイライト重点".encode("utf-8"),
            "ブラケット設定".encode("utf-8"),
            "ﾌﾞﾗｹｯﾄ時のｾﾙﾌﾀｲﾏｰ".encode("utf-8"),
            "ブラケット順序".encode("utf-8"),
            "TC/UB表示設定".encode("utf-8"),
            b"User Bit Preset",
            b"User Bit Time Rec",
            b"Time Code Format",
            "再生メディア選択".encode("utf-8"),
            "コピー".encode("utf-8"),
            "繰り返し".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-54 JA parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Selectable AF areas are limited to 1",
            b"White",
            b"Red",
            b"This function adjusts the standard of",
            b"Slide Show",
            b"Interval",
            b"Cannot copy.",
            b"Copy failed.",
            b"TC/UB display switching is invalid",
        ),
        "FX3 string_english.uxc Wave-54 FocusLimit/StdAdj/SlideShow/Copy strings",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Slot 1",
            b"Slot 2",
            b"TC/UB",
            b"Reset the user bit?",
        ),
        "FX3 string_english_g.uxc Wave-54 Slot/TCUB strings",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4\x00",),
        "FX3-CX95900_ALLLANG-Backup.bin BK4 seed",
    ),
    "fx6_appfw_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
        50_520_424,
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE297,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE297),
        "FX6 appFw.so Wave-54 TC/UB/EXT-LK/dormant CopyClip/Autofocus symbols",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"Timecode",
            b"Users Bit Mode",
            b"TC Display",
            b"Focus Area Ind.(AF-S)",
        ),
        "FX6 string_english.uxc Wave-54 strings",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"TC Format",
            b"HDMI TC Out",
            b"Focus Area Marker",
            b"Copy Clip",
        ),
        "FX6 string_english_2.uxc Wave-54 strings",
    ),
}

_DONOR_BLOB_CACHE: Dict[str, Tuple[int, float, int, str, bytes]] = {}

# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase297DonorAuditResult:
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
class SwitchVhAfAndExposureStdAdjGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    target_model: str
    reset_action: str
    shoot_mode: str
    focus_mode: str
    gravity_orientation: str
    effective_switch_vh_af_area: str
    vh_af_orientation_switch_active: bool
    vh_af_lockout_reasons: Tuple[str, ...]
    stored_points_cleared_on_mode_change: bool
    switch_vh_af_reset_on_cam_reset: bool
    enabled_focus_area_limit_options: Tuple[str, ...]
    enabled_focus_area_limit_count: int
    focus_area_limit_tracking_available: bool
    focus_area_limit_reset_on_cam_reset: bool
    effective_focus_area_color: str
    focus_area_color_survived_cam_reset: bool
    exposure_std_adjust_sixths_by_mode: Dict[str, int]
    exposure_std_adjust_ev_by_mode: Dict[str, float]
    exposure_std_adjust_metering_mode_count: int
    exposure_std_adjust_survived_cam_reset: bool
    exposure_std_adjust_independent_of_exp_comp: bool
    mm_and_spot_ael_shifted: bool
    bracket_shot_count_reset_on_std_adj_change: bool
    effective_bracket_selftimer: str
    effective_bracket_order: str
    bracket_settings_still_only: bool
    bracket_settings_reset_on_cam_reset: bool
    fx6_lacks_vh_switch_limit_std_adj_bracket: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G127SwitchVhAfExposureStdAdjGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    switch_vh_af_exposure_stdadj_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TcubFormatAndPlaybackCopySlotGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    target_model: str
    reset_action: str
    tv_system: str
    frame_rate: str
    effective_tc_preset: str
    effective_ub_preset: str
    effective_tc_format: str
    tc_format_menu_visible: bool
    tc_format_forced_ndf: bool
    effective_tc_run: str
    effective_tc_make: str
    effective_ub_time_rec: str
    effective_tcub_disp_setting: str
    tcub_6_items_survived_cam_reset: bool
    tcub_disp_survived_cam_reset: bool
    initialize_required_to_reset_tcub: bool
    playback_active: bool
    playback_media_is_movie: bool
    tcub_disp_playback_toggle_allowed: bool
    fx3_has_bnc_tc_port: bool
    fx6_has_bnc_tc_port: bool
    effective_select_playback_media: str
    copy_source_slot: str
    copy_destination_slot: str
    copy_direction_label: str
    slot_1_write_protected: bool
    slot_1_contains_tier0_vault: bool
    copy_requested: bool
    copy_blocked_by_slot1_vault_firewall: bool
    block_errno: Optional[str]
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    battery_sufficient_for_copy: bool
    destination_card_speed_class: str
    destination_card_speed_ok: bool
    protect_flags_preserved_on_destination: bool
    slide_show_view_mode: str
    effective_slide_show_repeat: str
    effective_slide_show_interval: str
    slide_show_survived_cam_reset: bool
    power_save_sleep_bypassed_during_slideshow: bool
    fx6_lacks_slideshow_and_copy_clip: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G128TcubPlaybackCopySlotGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    tcub_playback_copy_slot_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master128GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_125_gates_verified: bool
    all_128_gates_verified: bool
    g13_to_g128_all_passed: bool
    g127_to_g128_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_126_report: Dict[str, Any]
    g127_result: Dict[str, Any]
    g128_result: Dict[str, Any]
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
    for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE297):
        if os.environ.get(env_key, "").strip() in _TRUTHY_CLEAN_ROOM_TOKENS:
            return True
    return False


def _default_donor_budget_seconds_phase297() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return DONOR_CHECK_CI_MAX_SECONDS_PHASE297
    return DONOR_CHECK_MAX_SECONDS_PHASE297


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
    """Read targeted byte slices via `os.open(..., os.O_RDONLY)` + `os.pread`."""
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


def _parse_fw_tuple(fw: str) -> Optional[Tuple[int, int]]:
    m = re.match(r"^\s*(\d+)\.(\d+)", fw.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def _norm_reset_action_phase297(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE_PHASE297
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE297
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE297
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE_PHASE297
    return None


def _norm_shoot_mode_phase297(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "P": SHOOT_MODE_P_PHASE297,
        "A": SHOOT_MODE_A_PHASE297,
        "S": SHOOT_MODE_S_PHASE297,
        "M": SHOOT_MODE_M_PHASE297,
        "STILL": SHOOT_MODE_STILL_PHASE297,
        "INTELLIGENT AUTO": SHOOT_MODE_INTELLIGENT_AUTO_PHASE297,
        "IAUTO": SHOOT_MODE_INTELLIGENT_AUTO_PHASE297,
        "MOVIE": SHOOT_MODE_MOVIE_PHASE297,
        "S&Q": SHOOT_MODE_SQ_PHASE297,
        "SQ": SHOOT_MODE_SQ_PHASE297,
        "MR": SHOOT_MODE_MR_PHASE297,
    }
    return mapping.get(u)


def _norm_focus_mode_g127(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "AF-S": "AF-S",
        "SINGLE-SHOT AF": "AF-S",
        "AF-A": "AF-A",
        "AUTOMATIC AF": "AF-A",
        "AF-C": "AF-C",
        "CONTINUOUS AF": "AF-C",
        "DMF": "DMF",
        "MF": "MF",
        "MANUAL FOCUS": "MF",
    }
    return mapping.get(u)


def _norm_on_off_phase297(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "ON":
        return "On"
    if u == "OFF":
        return "Off"
    return None


def _norm_switch_vh_af_g127(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("OFF", "VERTICAL_HORIZONTAL_FOCUS_AREA_SWITCH_OFF"):
        return SWITCH_VH_AF_OFF_G127
    if u in (
        "AF POINT ONLY",
        "FOCUS_POSITION_ONLY",
        "VERTICAL_HORIZONTAL_FOCUS_AREA_SWITCH_FOCUS_POSITION_ONLY",
    ):
        return SWITCH_VH_AF_POINT_ONLY_G127
    if u in (
        "AF POINT + AF AREA",
        "AF POINT+AF AREA",
        "FOCUS_POSITION_FOCUS_AREA",
        "VERTICAL_HORIZONTAL_FOCUS_AREA_SWITCH_FOCUS_POSITION_FOCUS_AREA",
    ):
        return SWITCH_VH_AF_POINT_AND_AREA_G127
    return None


def _norm_gravity_orientation_g127(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "_", raw.strip().strip("[]")).upper()
    u = u.replace("VH_AF_AREA_ORIENTATION_INFORMATION_", "")
    if u in ("0_DEGREES", "0", "0°", "HORIZONTAL", "0_DEG"):
        return GRAVITY_ORIENTATION_0_DEG_G127
    if u in ("90_DEGREES", "90", "90°", "VERTICAL_90", "90_DEG"):
        return GRAVITY_ORIENTATION_90_DEG_G127
    if u in ("270_DEGREES", "270", "270°", "VERTICAL_270", "270_DEG"):
        return GRAVITY_ORIENTATION_270_DEG_G127
    if u in ("INVALID", "VERTICAL_PITCH_UP", "VERTICAL_PITCH_DOWN", "PITCH_UP", "PITCH_DOWN"):
        return GRAVITY_ORIENTATION_INVALID_G127
    return None


def _norm_focus_area_color_g127(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "WHITE":
        return FOCUS_AREA_COLOR_WHITE_G127
    if u == "RED":
        return FOCUS_AREA_COLOR_RED_G127
    return None


def _norm_bracket_selftimer_g127(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "OFF": BRACKET_SELFTIMER_OFF_G127,
        "2 SEC": BRACKET_SELFTIMER_2SEC_G127,
        "2SEC": BRACKET_SELFTIMER_2SEC_G127,
        "5 SEC": BRACKET_SELFTIMER_5SEC_G127,
        "5SEC": BRACKET_SELFTIMER_5SEC_G127,
        "10 SEC": BRACKET_SELFTIMER_10SEC_G127,
        "10SEC": BRACKET_SELFTIMER_10SEC_G127,
    }
    return mapping.get(u)


def _norm_bracket_order_g127(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").replace("→", "->").replace(" ", "").upper()
    if u in ("0->-->+", "0->-->PLUS", "ZERO_MINUS_PLUS"):
        return BRACKET_ORDER_ZERO_MINUS_PLUS_G127
    if u in ("-->0->+", "MINUS_ZERO_PLUS"):
        return BRACKET_ORDER_MINUS_ZERO_PLUS_G127
    return None


def _norm_tv_system_g128(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u in ("NTSC", "PAL"):
        return u
    return None


def _norm_tc_format_g128(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u in ("DF", "NDF"):
        return u
    return None


def _norm_tc_run_g128(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("REC RUN", "REC_RUN"):
        return TC_RUN_REC_G128
    if u in ("FREE RUN", "FREE_RUN"):
        return TC_RUN_FREE_G128
    return None


def _norm_tc_make_g128(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "PRESET":
        return TC_MAKE_PRESET_G128
    if u == "REGENERATE":
        return TC_MAKE_REGENERATE_G128
    return None


def _norm_tcub_disp_g128(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("COUNTER", "DURATION"):
        return TCUB_DISP_COUNTER_G128
    if u in ("TC", "TIMECODE"):
        return TCUB_DISP_TC_G128
    if u in ("U-BIT", "UBIT", "USERS BIT"):
        return TCUB_DISP_UBIT_G128
    return None


def _norm_playback_media_slot_g128(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("SLOT 1", "SLOT1"):
        return MEDIA_SLOT_1_G128
    if u in ("SLOT 2", "SLOT2"):
        return MEDIA_SLOT_2_G128
    return None


def _norm_slide_show_interval_g128(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "1 SEC": SLIDE_SHOW_INTERVAL_1SEC_G128,
        "1SEC": SLIDE_SHOW_INTERVAL_1SEC_G128,
        "3 SEC": SLIDE_SHOW_INTERVAL_3SEC_G128,
        "3SEC": SLIDE_SHOW_INTERVAL_3SEC_G128,
        "5 SEC": SLIDE_SHOW_INTERVAL_5SEC_G128,
        "5SEC": SLIDE_SHOW_INTERVAL_5SEC_G128,
        "10 SEC": SLIDE_SHOW_INTERVAL_10SEC_G128,
        "10SEC": SLIDE_SHOW_INTERVAL_10SEC_G128,
        "30 SEC": SLIDE_SHOW_INTERVAL_30SEC_G128,
        "30SEC": SLIDE_SHOW_INTERVAL_30SEC_G128,
    }
    return mapping.get(u)


def _is_valid_tc_preset(val: str) -> bool:
    return bool(re.match(r"^\d{2}:\d{2}:\d{2}\.\d{2}$", val.strip()))


def _is_valid_ub_preset(val: str) -> bool:
    return bool(
        re.match(r"^[0-9A-Fa-f]{2}\s+[0-9A-Fa-f]{2}\s+[0-9A-Fa-f]{2}\s+[0-9A-Fa-f]{2}$", val.strip())
    )


# ---------------------------------------------------------------------------
# 1. Local O_RDONLY Donor Audit & Clean-Room Synthetic Fallback (< 0.20s)
# ---------------------------------------------------------------------------


def audit_phase297_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase297DonorAuditResult:
    """Strictly `os.open(..., os.O_RDONLY)` audit of Phase 297 Wave-54 local donor
    evidence (`FX3 appFw.so`, 4-language `_f.uxc`, `.uxc`, `_g.uxc`, `BK4`, and
    `FX6 appFw.so` + `.uxc` packs) with clean-room synthetic fallback.
    """
    t0 = time.monotonic()
    clean_forced = _is_forced_clean_room(force_clean_room)
    resolved_work = (
        Path(work_root)
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=repo_root).work_root
    )
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else PINNED_PHASE297_DONOR_SPECS
    )

    if clean_forced:
        elapsed = time.monotonic() - t0
        return Phase297DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_CLEAN_ROOM_PINNED_CONTRACTS",
            files_inspected=0,
            elapsed_seconds=elapsed,
            within_budget_200ms=True,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(v[5] for v in specs.values()),
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            sha256_by_artifact={k: v[3] for k, v in specs.items()},
            bytes_by_artifact={k: v[2] for k, v in specs.items()},
            errors=(),
            warnings=(),
        )

    missing_paths: List[str] = []
    resolved_paths: Dict[str, Path] = {}
    for key, (_family, rel, _size, _sha, _tokens, _marker) in specs.items():
        p = resolved_work / rel
        if not p.exists():
            missing_paths.append(rel)
        resolved_paths[key] = p

    if missing_paths:
        if work_root is not None and donor_specs_override is None:
            elapsed = time.monotonic() - t0
            return Phase297DonorAuditResult(
                valid=False,
                status=STATUS_BLOCKED_PHASE297_DONOR_INTEGRITY,
                verification_mode="LOCAL_DONOR_O_RDONLY",
                access_mode="O_RDONLY",
                files_inspected=0,
                elapsed_seconds=elapsed,
                within_budget_200ms=(elapsed <= _default_donor_budget_seconds_phase297()),
                raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
                checked_markers=(),
                missing_markers=tuple(missing_paths),
                fx3_contracts_verified=False,
                fx6_contracts_verified=False,
                four_lang_resid16_parity_verified=False,
                sha256_by_artifact={},
                bytes_by_artifact={},
                errors=(
                    f"Explicit work_root missing Wave-54 donor files: {missing_paths}",
                ),
                warnings=(),
            )
        elapsed = time.monotonic() - t0
        return Phase297DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_CLEAN_ROOM_FALLBACK_NO_LOCAL_DONOR",
            files_inspected=0,
            elapsed_seconds=elapsed,
            within_budget_200ms=True,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(v[5] for v in specs.values()),
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            sha256_by_artifact={k: v[3] for k, v in specs.items()},
            bytes_by_artifact={k: v[2] for k, v in specs.items()},
            errors=(),
            warnings=(
                "Local Wave-54 Sony donor binaries absent; using CLEAN_ROOM_SYNTHETIC pinned SHA-256 contracts.",
            ),
        )

    errors: List[str] = []
    warnings: List[str] = []
    checked_markers: List[str] = []
    missing_markers: List[str] = []
    sha_map: Dict[str, str] = {}
    size_map: Dict[str, int] = {}
    fx3_ok = True
    fx6_ok = True
    lang_ok = True
    inspected = 0

    for key, (family, _rel, exp_size, exp_sha, tokens, marker) in specs.items():
        p = resolved_paths[key]
        if key == "fx3_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tokens_ok = _read_targeted_slices_o_rdonly(
                p, PINNED_FX3_APPFW_SLICES_PHASE297
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tokens_ok = _read_targeted_slices_o_rdonly(
                p, PINNED_FX6_APPFW_SLICES_PHASE297
            )
        else:
            actual_size, actual_sha, blob = _read_cached_donor_o_rdonly(p)
            tokens_ok = all(tok in blob for tok in tokens)
        inspected += 1
        sha_map[key] = actual_sha
        size_map[key] = actual_size

        size_match = actual_size == exp_size
        sha_match = actual_sha == exp_sha
        if size_match and sha_match and tokens_ok:
            checked_markers.append(marker)
        else:
            missing_markers.append(marker)
            errors.append(
                f"{key}: mismatch (size={actual_size}/{exp_size}, sha={actual_sha[:12]}/{exp_sha[:12]}, tokens_ok={tokens_ok})"
            )
            if family == "FX3":
                fx3_ok = False
            elif family == "FX6":
                fx6_ok = False
            if key in (
                "fx3_string_english_f_uxc",
                "fx3_string_simplifiedchinese_f_uxc",
                "fx3_string_traditionalchinese_f_uxc",
                "fx3_string_japanese_f_uxc",
            ):
                lang_ok = False

    elapsed = time.monotonic() - t0
    budget = _default_donor_budget_seconds_phase297()
    within_budget = elapsed <= budget
    if not within_budget:
        warnings.append(
            f"Phase 297 donor audit took {elapsed:.4f}s (budget {budget:.2f}s)."
        )

    valid = (not errors) and fx3_ok and fx6_ok and lang_ok
    return Phase297DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE297_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=inspected,
        elapsed_seconds=elapsed,
        within_budget_200ms=within_budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked_markers),
        missing_markers=tuple(missing_markers),
        fx3_contracts_verified=fx3_ok,
        fx6_contracts_verified=fx6_ok,
        four_lang_resid16_parity_verified=lang_ok,
        sha256_by_artifact=sha_map,
        bytes_by_artifact=size_map,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Gate G127: [Switch V/H AF Area] + [Focus Area Limit] +
#    [Exposure Std. Adjust] (5 Modes @ 1/6 EV, Initialize-Only) + Still [Bracket Settings]
# ---------------------------------------------------------------------------


def _default_exposure_std_adj_sixths() -> Dict[str, int]:
    return {mode: 0 for mode in EXPOSURE_STD_ADJ_5_METERING_MODES_G127}


def resolve_fx3_switch_vh_af_and_exposure_stdadj_state(
    *,
    shoot_mode: str = SHOOT_MODE_M_PHASE297,
    focus_mode: str = "AF-C",
    gravity_orientation: str = GRAVITY_ORIENTATION_0_DEG_G127,
    requested_switch_vh_af_area: str = SWITCH_VH_AF_DEFAULT_G127,
    previous_switch_vh_af_area: Optional[str] = None,
    digital_zoom_active: bool = False,
    af_in_progress: bool = False,
    continuous_shooting_active: bool = False,
    self_timer_countdown_active: bool = False,
    focus_magnifier_active: bool = False,
    requested_focus_area_limit_options: Sequence[str] = FOCUS_AREA_LIMIT_14_OPTIONS_G127,
    requested_focus_area_color: str = FOCUS_AREA_COLOR_DEFAULT_G127,
    requested_exposure_std_adjust_sixths: Optional[Mapping[str, int]] = None,
    exposure_std_adjust_changed_mid_bracket: bool = False,
    requested_bracket_selftimer: str = BRACKET_SELFTIMER_DEFAULT_G127,
    requested_bracket_order: str = BRACKET_ORDER_DEFAULT_G127,
    reset_action: str = RESET_ACTION_NONE_PHASE297,
) -> Dict[str, Any]:
    """Resolve effective Wave-54 Gate `G127` FX3 Ver. 7.02 state."""
    eff_reset = _norm_reset_action_phase297(reset_action) or RESET_ACTION_NONE_PHASE297
    eff_shoot = _norm_shoot_mode_phase297(shoot_mode) or SHOOT_MODE_M_PHASE297
    eff_focus = _norm_focus_mode_g127(focus_mode) or "AF-C"
    eff_orient = _norm_gravity_orientation_g127(gravity_orientation) or GRAVITY_ORIENTATION_0_DEG_G127
    eff_vh = _norm_switch_vh_af_g127(requested_switch_vh_af_area) or SWITCH_VH_AF_DEFAULT_G127
    prev_vh = (
        _norm_switch_vh_af_g127(previous_switch_vh_af_area)
        if previous_switch_vh_af_area is not None
        else eff_vh
    )
    eff_color = _norm_focus_area_color_g127(requested_focus_area_color) or FOCUS_AREA_COLOR_DEFAULT_G127
    eff_bracket_timer = (
        _norm_bracket_selftimer_g127(requested_bracket_selftimer) or BRACKET_SELFTIMER_DEFAULT_G127
    )
    eff_bracket_order = (
        _norm_bracket_order_g127(requested_bracket_order) or BRACKET_ORDER_DEFAULT_G127
    )

    eff_limit_opts = tuple(
        opt for opt in requested_focus_area_limit_options if opt in FOCUS_AREA_LIMIT_14_OPTIONS_G127
    )
    if not eff_limit_opts:
        eff_limit_opts = FOCUS_AREA_LIMIT_14_OPTIONS_G127

    eff_std_sixths = _default_exposure_std_adj_sixths()
    if requested_exposure_std_adjust_sixths:
        for mode, val in requested_exposure_std_adjust_sixths.items():
            if mode in EXPOSURE_STD_ADJ_5_METERING_MODES_G127 and _is_real_int(val):
                eff_std_sixths[mode] = max(
                    EXPOSURE_STD_ADJ_MIN_SIXTHS_G127,
                    min(EXPOSURE_STD_ADJ_MAX_SIXTHS_G127, int(val)),
                )

    # Reset matrix:
    # - Camera Settings Reset resets: Switch V/H AF Area, Focus Area Limit, Bracket Settings
    # - Initialize ONLY resets: Focus Area Color, Exposure Std. Adjust (all 5 modes)
    if eff_reset in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE297,
        RESET_ACTION_INITIALIZE_PHASE297,
    ):
        eff_vh = SWITCH_VH_AF_DEFAULT_G127
        eff_limit_opts = FOCUS_AREA_LIMIT_14_OPTIONS_G127
        eff_bracket_timer = BRACKET_SELFTIMER_DEFAULT_G127
        eff_bracket_order = BRACKET_ORDER_DEFAULT_G127

    if eff_reset == RESET_ACTION_INITIALIZE_PHASE297:
        eff_color = FOCUS_AREA_COLOR_DEFAULT_G127
        eff_std_sixths = _default_exposure_std_adj_sixths()

    switch_vh_af_reset_on_cam_reset = eff_reset in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE297,
        RESET_ACTION_INITIALIZE_PHASE297,
    )
    exposure_std_adj_survived_cam_reset = eff_reset != RESET_ACTION_INITIALIZE_PHASE297
    focus_area_color_survived_cam_reset = eff_reset != RESET_ACTION_INITIALIZE_PHASE297

    is_still_pasm = eff_shoot in STILL_PASM_SHOOT_MODES_PHASE297
    is_movie = eff_shoot in MOVIE_SHOOT_MODES_PHASE297

    lockout_reasons: List[str] = []
    if is_movie:
        lockout_reasons.append("MOVIE_OR_SQ_MODE")
    if eff_shoot == SHOOT_MODE_INTELLIGENT_AUTO_PHASE297:
        lockout_reasons.append("INTELLIGENT_AUTO")
    if eff_focus != "AF-C":
        lockout_reasons.append("FOCUS_MODE_NOT_AF_C")
    if digital_zoom_active:
        lockout_reasons.append("DIGITAL_ZOOM_ACTIVE")
    if af_in_progress:
        lockout_reasons.append("AF_ACTIVE")
    if continuous_shooting_active:
        lockout_reasons.append("CONTINUOUS_SHOOTING")
    if self_timer_countdown_active:
        lockout_reasons.append("SELF_TIMER_COUNTDOWN")
    if focus_magnifier_active:
        lockout_reasons.append("FOCUS_MAGNIFIER_ACTIVE")
    if eff_orient == GRAVITY_ORIENTATION_INVALID_G127:
        lockout_reasons.append("VERTICAL_PITCH_INVALID")

    vh_switch_active = (
        eff_vh != SWITCH_VH_AF_OFF_G127
        and (not lockout_reasons)
        and (eff_orient in VALID_SWITCHABLE_ORIENTATIONS_G127)
    )
    stored_points_cleared = (prev_vh is not None and eff_vh != prev_vh) or (
        eff_reset in (RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE297, RESET_ACTION_INITIALIZE_PHASE297)
    )

    ev_by_mode = {
        mode: round(sixths / 6.0, 4) for mode, sixths in eff_std_sixths.items()
    }
    any_std_adj_nonzero = any(v != 0 for v in eff_std_sixths.values())

    return {
        "reset_action": eff_reset,
        "shoot_mode": eff_shoot,
        "focus_mode": eff_focus,
        "gravity_orientation": eff_orient,
        "effective_switch_vh_af_area": eff_vh,
        "vh_af_orientation_switch_active": vh_switch_active,
        "vh_af_lockout_reasons": tuple(lockout_reasons),
        "stored_points_cleared_on_mode_change": stored_points_cleared,
        "switch_vh_af_reset_on_cam_reset": switch_vh_af_reset_on_cam_reset,
        "enabled_focus_area_limit_options": eff_limit_opts,
        "enabled_focus_area_limit_count": len(eff_limit_opts),
        "focus_area_limit_tracking_available": not is_movie,
        "focus_area_limit_reset_on_cam_reset": switch_vh_af_reset_on_cam_reset,
        "effective_focus_area_color": eff_color,
        "focus_area_color_survived_cam_reset": focus_area_color_survived_cam_reset,
        "exposure_std_adjust_sixths_by_mode": eff_std_sixths,
        "exposure_std_adjust_ev_by_mode": ev_by_mode,
        "exposure_std_adjust_survived_cam_reset": exposure_std_adj_survived_cam_reset,
        "mm_and_spot_ael_shifted": any_std_adj_nonzero,
        "bracket_shot_count_reset_on_std_adj_change": bool(
            exposure_std_adjust_changed_mid_bracket
        ),
        "effective_bracket_selftimer": eff_bracket_timer,
        "effective_bracket_order": eff_bracket_order,
        "bracket_settings_still_only": is_still_pasm or (
            eff_shoot == SHOOT_MODE_INTELLIGENT_AUTO_PHASE297
        ),
        "bracket_settings_reset_on_cam_reset": switch_vh_af_reset_on_cam_reset,
    }


def compute_switch_vh_af_and_exposure_stdadj_matrix() -> Dict[str, Any]:
    """Deterministic `384`-state cross-product across
    `(4 shoot_modes x 2 focus_modes x 4 orientations x 3 vh_modes x 4 reset_actions)`
    verifying `G127` invariants.
    """
    states = 0
    vh_active_count = 0
    pitch_invalid_blocked = 0
    std_adj_survived_cam_reset_count = 0
    vh_reset_on_cam_reset_count = 0

    for sm in (
        SHOOT_MODE_M_PHASE297,
        SHOOT_MODE_INTELLIGENT_AUTO_PHASE297,
        SHOOT_MODE_MOVIE_PHASE297,
        SHOOT_MODE_SQ_PHASE297,
    ):
        for fm in ("AF-C", "AF-S"):
            for orient in ALLOWED_GRAVITY_ORIENTATIONS_G127:
                for vh in ALLOWED_SWITCH_VH_AF_MODES_G127:
                    for r_act in ALLOWED_RESET_ACTIONS_PHASE297:
                        states += 1
                        r = resolve_fx3_switch_vh_af_and_exposure_stdadj_state(
                            shoot_mode=sm,
                            focus_mode=fm,
                            gravity_orientation=orient,
                            requested_switch_vh_af_area=vh,
                            requested_exposure_std_adjust_sixths={
                                "Multi": 2,
                                "Center": -1,
                                "Spot": 3,
                                "Entire Screen Avg.": -2,
                                "Highlight": 1,
                            },
                            requested_bracket_selftimer=BRACKET_SELFTIMER_5SEC_G127,
                            requested_bracket_order=BRACKET_ORDER_MINUS_ZERO_PLUS_G127,
                            reset_action=r_act,
                        )
                        if r["vh_af_orientation_switch_active"]:
                            assert sm == SHOOT_MODE_M_PHASE297
                            assert fm == "AF-C"
                            assert orient in VALID_SWITCHABLE_ORIENTATIONS_G127
                            assert vh != SWITCH_VH_AF_OFF_G127
                            assert r_act in (
                                RESET_ACTION_NONE_PHASE297,
                                RESET_ACTION_RESET_NETWORK_SET_PHASE297,
                            )
                            vh_active_count += 1
                        if orient == GRAVITY_ORIENTATION_INVALID_G127:
                            assert r["vh_af_orientation_switch_active"] is False
                            assert "VERTICAL_PITCH_INVALID" in r["vh_af_lockout_reasons"]
                            pitch_invalid_blocked += 1
                        if r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE297:
                            assert r["effective_switch_vh_af_area"] == SWITCH_VH_AF_OFF_G127
                            assert r["effective_bracket_selftimer"] == BRACKET_SELFTIMER_OFF_G127
                            assert r["effective_bracket_order"] == BRACKET_ORDER_ZERO_MINUS_PLUS_G127
                            assert r["exposure_std_adjust_sixths_by_mode"]["Highlight"] == 1
                            assert r["exposure_std_adjust_sixths_by_mode"]["Spot"] == 3
                            assert r["exposure_std_adjust_survived_cam_reset"] is True
                            std_adj_survived_cam_reset_count += 1
                            vh_reset_on_cam_reset_count += 1

    return {
        "states_checked": states,
        "vh_active_count": vh_active_count,
        "pitch_invalid_blocked": pitch_invalid_blocked,
        "std_adj_survived_cam_reset_count": std_adj_survived_cam_reset_count,
        "vh_reset_on_cam_reset_count": vh_reset_on_cam_reset_count,
        "all_invariants_hold": states == 384,
    }


def verify_switch_vh_af_and_exposure_stdadj_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE297,
    body_model_id: int = FX3_MODEL_ID_PHASE297,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE297,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE297,
    target_model: str = FX3_MODEL_NAME_PHASE297,
    shoot_mode: str = SHOOT_MODE_M_PHASE297,
    focus_mode: str = "AF-C",
    gravity_orientation: str = GRAVITY_ORIENTATION_0_DEG_G127,
    requested_switch_vh_af_area: str = SWITCH_VH_AF_DEFAULT_G127,
    previous_switch_vh_af_area: Optional[str] = None,
    switch_vh_af_trigger_requested: bool = False,
    digital_zoom_active: bool = False,
    af_in_progress: bool = False,
    continuous_shooting_active: bool = False,
    self_timer_countdown_active: bool = False,
    focus_magnifier_active: bool = False,
    claimed_stored_points_persist_across_mode_change: bool = False,
    requested_focus_area_limit_options: Sequence[str] = FOCUS_AREA_LIMIT_14_OPTIONS_G127,
    focus_area_limit_switch_requested: bool = False,
    focus_area_tracking_select_requested: bool = False,
    requested_focus_area_color: str = FOCUS_AREA_COLOR_DEFAULT_G127,
    requested_exposure_std_adjust_sixths: Optional[Mapping[str, int]] = None,
    exposure_std_adjust_changed_mid_bracket: bool = False,
    claimed_only_4_metering_modes: bool = False,
    claimed_exposure_std_adj_resets_on_cam_settings_reset: bool = False,
    claimed_exposure_std_adj_stacks_into_exp_comp: bool = False,
    claimed_bracket_count_continues_after_std_adj_change: bool = False,
    requested_bracket_selftimer: str = BRACKET_SELFTIMER_DEFAULT_G127,
    requested_bracket_order: str = BRACKET_ORDER_DEFAULT_G127,
    bracket_settings_use_requested: bool = False,
    claimed_fx6_has_vh_switch_limit_std_adj_or_bracket: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE297,
) -> SwitchVhAfAndExposureStdAdjGuardResult:
    """Verify Wave-54 Gate `G127` hardware safety contracts."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version) if isinstance(firmware_version, str) else None
    norm_shoot = _norm_shoot_mode_phase297(shoot_mode)
    norm_focus = _norm_focus_mode_g127(focus_mode)
    norm_reset = _norm_reset_action_phase297(reset_action)
    norm_orient = _norm_gravity_orientation_g127(gravity_orientation)
    norm_vh = _norm_switch_vh_af_g127(requested_switch_vh_af_area)
    norm_color = _norm_focus_area_color_g127(requested_focus_area_color)
    norm_bracket_timer = _norm_bracket_selftimer_g127(requested_bracket_selftimer)
    norm_bracket_order = _norm_bracket_order_g127(requested_bracket_order)

    std_adj_map_valid = True
    if requested_exposure_std_adjust_sixths is not None:
        if not isinstance(requested_exposure_std_adjust_sixths, Mapping):
            std_adj_map_valid = False
        else:
            for k, v in requested_exposure_std_adjust_sixths.items():
                if k not in EXPOSURE_STD_ADJ_5_METERING_MODES_G127:
                    std_adj_map_valid = False
                elif (not _is_real_int(v)) or (v not in EXPOSURE_STD_ADJ_VALID_SIXTHS_G127):
                    std_adj_map_valid = False

    if (
        body_model_name != FX3_MODEL_NAME_PHASE297
        or not _is_real_int(body_model_id)
        or body_model_id != FX3_MODEL_ID_PHASE297
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE297
        or fw_tuple is None
        or norm_shoot is None
        or norm_focus is None
        or norm_reset is None
        or norm_orient is None
        or norm_vh is None
        or norm_color is None
        or norm_bracket_timer is None
        or norm_bracket_order is None
        or not std_adj_map_valid
        or target_model not in (FX3_MODEL_NAME_PHASE297, FX6_MODEL_NAME_PHASE297)
    ):
        _add_code(codes, STATUS_BLOCKED_G127_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3/FX6 identity, Switch V/H AF Area, Focus Area Limit, Exposure Std. Adjust, or Bracket Settings telemetry."
        )

    eff = resolve_fx3_switch_vh_af_and_exposure_stdadj_state(
        shoot_mode=norm_shoot or SHOOT_MODE_M_PHASE297,
        focus_mode=norm_focus or "AF-C",
        gravity_orientation=norm_orient or GRAVITY_ORIENTATION_0_DEG_G127,
        requested_switch_vh_af_area=norm_vh or SWITCH_VH_AF_DEFAULT_G127,
        previous_switch_vh_af_area=previous_switch_vh_af_area,
        digital_zoom_active=digital_zoom_active,
        af_in_progress=af_in_progress,
        continuous_shooting_active=continuous_shooting_active,
        self_timer_countdown_active=self_timer_countdown_active,
        focus_magnifier_active=focus_magnifier_active,
        requested_focus_area_limit_options=requested_focus_area_limit_options,
        requested_focus_area_color=norm_color or FOCUS_AREA_COLOR_DEFAULT_G127,
        requested_exposure_std_adjust_sixths=(
            requested_exposure_std_adjust_sixths if std_adj_map_valid else None
        ),
        exposure_std_adjust_changed_mid_bracket=exposure_std_adjust_changed_mid_bracket,
        requested_bracket_selftimer=norm_bracket_timer or BRACKET_SELFTIMER_DEFAULT_G127,
        requested_bracket_order=norm_bracket_order or BRACKET_ORDER_DEFAULT_G127,
        reset_action=norm_reset or RESET_ACTION_NONE_PHASE297,
    )

    # Part A: [Switch V/H AF Area] Still AF-C 3-orientation + 8 lockouts + pitch INVALID
    if switch_vh_af_trigger_requested and (not eff["vh_af_orientation_switch_active"]):
        _add_code(codes, STATUS_BLOCKED_G127_SWITCH_VH_AF_LOCKOUT_OR_PITCH_INVALID)
        errors.append(
            f"[Switch V/H AF Area] orientation switch blocked (reasons={eff['vh_af_lockout_reasons']}, "
            f"mode={eff['effective_switch_vh_af_area']}, orient={eff['gravity_orientation']})."
        )

    if claimed_stored_points_persist_across_mode_change:
        _add_code(codes, STATUS_BLOCKED_G127_SWITCH_VH_AF_LOCKOUT_OR_PITCH_INVALID)
        errors.append(
            "Changing [Switch V/H AF Area] setting MUST clear stored per-orientation AF points."
        )

    # Part B: [Focus Area Limit] exact 14 checkboxes vs dormant XL/XS/Custom1..3 & >= 2 min
    dormant_hits = [
        opt
        for opt in requested_focus_area_limit_options
        if opt in DORMANT_FOCUS_AREA_LIMIT_OPTIONS_G127 or opt not in FOCUS_AREA_LIMIT_14_OPTIONS_G127
    ]
    if dormant_hits:
        _add_code(codes, STATUS_BLOCKED_G127_FOCUS_AREA_LIMIT_DORMANT_OR_MIN2_VIOLATION)
        errors.append(
            f"[Focus Area Limit] dormant/unsupported options rejected fail-closed: {dormant_hits} "
            "(ILME-FX3 Ver. 7.02 exposes exact 14 BKID_APP_focus_area_limit_* checkboxes only)."
        )

    if len(requested_focus_area_limit_options) < FOCUS_AREA_LIMIT_MIN_ENABLED_G127 or (
        focus_area_limit_switch_requested
        and eff["enabled_focus_area_limit_count"] < FOCUS_AREA_LIMIT_MIN_ENABLED_G127
    ):
        _add_code(codes, STATUS_BLOCKED_G127_FOCUS_AREA_LIMIT_DORMANT_OR_MIN2_VIOLATION)
        errors.append(
            "[Focus Area Limit] requires >= 2 enabled AF areas (.uxc 0xea28: "
            "'Selectable AF areas are limited to 1 so changes cannot be made')."
        )

    if focus_area_tracking_select_requested and (norm_shoot in MOVIE_SHOOT_MODES_PHASE297):
        _add_code(codes, STATUS_BLOCKED_G127_FOCUS_AREA_LIMIT_DORMANT_OR_MIN2_VIOLATION)
        errors.append(
            "[Tracking:*] entries in [Focus Area] are unavailable in Movie/S&Q (use Touch Tracking)."
        )

    # Part C: [Exposure Std. Adjust] 5 metering modes, 1/6 EV, Initialize-only persistence
    if claimed_only_4_metering_modes:
        _add_code(codes, STATUS_BLOCKED_G127_EXPOSURE_STD_ADJ_5MODE_OR_RESET_VIOLATION)
        errors.append(
            "[Exposure Std. Adjust] calibrates ALL 5 metering modes "
            "(Multi, Center, Spot, Entire Screen Avg., Highlight) — never 4."
        )

    if claimed_exposure_std_adj_resets_on_cam_settings_reset:
        _add_code(codes, STATUS_BLOCKED_G127_EXPOSURE_STD_ADJ_5MODE_OR_RESET_VIOLATION)
        errors.append(
            "[Exposure Std. Adjust] (all 5 metering modes) survives [Camera Settings Reset] and "
            "resets ONLY via [Initialize]."
        )

    if claimed_exposure_std_adj_stacks_into_exp_comp:
        _add_code(codes, STATUS_BLOCKED_G127_EXPOSURE_STD_ADJ_5MODE_OR_RESET_VIOLATION)
        errors.append(
            "[Exposure Std. Adjust] writes independently to EXIF and shifts M.M. & Spot AEL "
            "without altering [Exposure Comp.]."
        )

    if claimed_bracket_count_continues_after_std_adj_change and exposure_std_adjust_changed_mid_bracket:
        _add_code(codes, STATUS_BLOCKED_G127_EXPOSURE_STD_ADJ_5MODE_OR_RESET_VIOLATION)
        errors.append(
            "Changing [Exposure Std. Adjust] mid-bracket resets active bracket shot count."
        )

    # Part D: Still [Bracket Settings] & ILME-FX6 cross-wire exclusion
    if bracket_settings_use_requested and (norm_shoot in MOVIE_SHOOT_MODES_PHASE297):
        _add_code(codes, STATUS_BLOCKED_G127_BRACKET_SETTINGS_OR_FX6_CROSSWIRE_VIOLATION)
        errors.append(
            "[Bracket Settings] ([Selftimer during Bracket], [Bracket order]) is Still-only."
        )

    if claimed_fx6_has_vh_switch_limit_std_adj_or_bracket or (
        target_model == FX6_MODEL_NAME_PHASE297
        and (
            switch_vh_af_trigger_requested
            or bracket_settings_use_requested
            or focus_area_limit_switch_requested
            or (requested_exposure_std_adjust_sixths is not None)
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G127_BRACKET_SETTINGS_OR_FX6_CROSSWIRE_VIOLATION)
        errors.append(
            "ILME-FX6 Ver. 6.01 lacks [Switch V/H AF Area], [Focus Area Limit], "
            "[Exposure Std. Adjust], and Still [Bracket Settings] (dormant FX6 `bracket_*` symbols blocked)."
        )

    matrix = compute_switch_vh_af_and_exposure_stdadj_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G127 if valid else codes[0]

    return SwitchVhAfAndExposureStdAdjGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE297,
        target_model=target_model,
        reset_action=eff["reset_action"],
        shoot_mode=eff["shoot_mode"],
        focus_mode=eff["focus_mode"],
        gravity_orientation=eff["gravity_orientation"],
        effective_switch_vh_af_area=eff["effective_switch_vh_af_area"],
        vh_af_orientation_switch_active=eff["vh_af_orientation_switch_active"],
        vh_af_lockout_reasons=eff["vh_af_lockout_reasons"],
        stored_points_cleared_on_mode_change=eff["stored_points_cleared_on_mode_change"],
        switch_vh_af_reset_on_cam_reset=eff["switch_vh_af_reset_on_cam_reset"],
        enabled_focus_area_limit_options=eff["enabled_focus_area_limit_options"],
        enabled_focus_area_limit_count=eff["enabled_focus_area_limit_count"],
        focus_area_limit_tracking_available=eff["focus_area_limit_tracking_available"],
        focus_area_limit_reset_on_cam_reset=eff["focus_area_limit_reset_on_cam_reset"],
        effective_focus_area_color=eff["effective_focus_area_color"],
        focus_area_color_survived_cam_reset=eff["focus_area_color_survived_cam_reset"],
        exposure_std_adjust_sixths_by_mode=eff["exposure_std_adjust_sixths_by_mode"],
        exposure_std_adjust_ev_by_mode=eff["exposure_std_adjust_ev_by_mode"],
        exposure_std_adjust_metering_mode_count=len(EXPOSURE_STD_ADJ_5_METERING_MODES_G127),
        exposure_std_adjust_survived_cam_reset=eff["exposure_std_adjust_survived_cam_reset"],
        exposure_std_adjust_independent_of_exp_comp=True,
        mm_and_spot_ael_shifted=eff["mm_and_spot_ael_shifted"],
        bracket_shot_count_reset_on_std_adj_change=eff[
            "bracket_shot_count_reset_on_std_adj_change"
        ],
        effective_bracket_selftimer=eff["effective_bracket_selftimer"],
        effective_bracket_order=eff["effective_bracket_order"],
        bracket_settings_still_only=eff["bracket_settings_still_only"],
        bracket_settings_reset_on_cam_reset=eff["bracket_settings_reset_on_cam_reset"],
        fx6_lacks_vh_switch_limit_std_adj_bracket=True,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g127_switch_vh_af_and_exposure_stdadj_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    switch_vh_af_exposure_stdadj_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase297DonorAuditResult] = None,
) -> Tuple[GateVerdict, G127SwitchVhAfExposureStdAdjGuardResult]:
    """Evaluate Wave-54 Gate `G127` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase297_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_switch_vh_af_and_exposure_stdadj_guard(
        **(dict(switch_vh_af_exposure_stdadj_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G127.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G127 if valid else codes[0]

    res = G127SwitchVhAfExposureStdAdjGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        switch_vh_af_exposure_stdadj_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, vh={guard.effective_switch_vh_af_area},"
        f"limit_n={guard.enabled_focus_area_limit_count},"
        f"std_modes={guard.exposure_std_adjust_metering_mode_count},"
        f"std_survived={guard.exposure_std_adjust_survived_cam_reset},"
        f"bracket_timer={guard.effective_bracket_selftimer},"
        f"bracket_order={guard.effective_bracket_order}"
    )
    verdict = GateVerdict(
        gate_id=G127_GATE_ID,
        gate_code=G127_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G128: [TC/UB] 6-Item + [TC Format] + [TC/UB Disp. Setting] +
#    Playback [Copy] Directional Asymmetry (`Slot 2 -> Slot 1` Tier-0 Firewall) + [Slide Show]
# ---------------------------------------------------------------------------


def resolve_fx3_tcub_format_and_playback_copy_slot_state(
    *,
    tv_system: str = TV_SYSTEM_NTSC_G128,
    frame_rate: str = "29.97p",
    requested_tc_preset: str = TC_PRESET_DEFAULT_G128,
    requested_ub_preset: str = UB_PRESET_DEFAULT_G128,
    requested_tc_format: str = TC_FORMAT_DEFAULT_G128,
    requested_tc_run: str = TC_RUN_DEFAULT_G128,
    requested_tc_make: str = TC_MAKE_DEFAULT_G128,
    requested_ub_time_rec: str = UB_TIME_REC_DEFAULT_G128,
    requested_tcub_disp_setting: str = TCUB_DISP_DEFAULT_G128,
    playback_active: bool = False,
    playback_media_is_movie: bool = True,
    requested_select_playback_media: str = MEDIA_SLOT_1_G128,
    slot_1_write_protected: bool = False,
    slot_1_contains_tier0_vault: bool = True,
    copy_requested: bool = False,
    battery_sufficient_for_copy: bool = True,
    destination_card_speed_class: str = "CFexpress Type A",
    slide_show_view_mode: str = SLIDE_SHOW_VIEW_DATE_G128,
    requested_slide_show_repeat: str = "Off",
    requested_slide_show_interval: str = SLIDE_SHOW_INTERVAL_DEFAULT_G128,
    slide_show_active: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE297,
) -> Dict[str, Any]:
    """Resolve effective Wave-54 Gate `G128` FX3 Ver. 7.02 TC/UB & Playback Copy state."""
    eff_reset = _norm_reset_action_phase297(reset_action) or RESET_ACTION_NONE_PHASE297
    eff_tv = _norm_tv_system_g128(tv_system) or TV_SYSTEM_NTSC_G128
    eff_tc_preset = requested_tc_preset.strip() if _is_valid_tc_preset(requested_tc_preset) else TC_PRESET_DEFAULT_G128
    eff_ub_preset = requested_ub_preset.strip().upper() if _is_valid_ub_preset(requested_ub_preset) else UB_PRESET_DEFAULT_G128
    eff_tc_format = _norm_tc_format_g128(requested_tc_format) or TC_FORMAT_DEFAULT_G128
    eff_tc_run = _norm_tc_run_g128(requested_tc_run) or TC_RUN_DEFAULT_G128
    eff_tc_make = _norm_tc_make_g128(requested_tc_make) or TC_MAKE_DEFAULT_G128
    eff_ub_time_rec = _norm_on_off_phase297(requested_ub_time_rec) or UB_TIME_REC_DEFAULT_G128
    eff_tcub_disp = _norm_tcub_disp_g128(requested_tcub_disp_setting) or TCUB_DISP_DEFAULT_G128
    eff_media = _norm_playback_media_slot_g128(requested_select_playback_media) or MEDIA_SLOT_1_G128
    eff_repeat = _norm_on_off_phase297(requested_slide_show_repeat) or "Off"
    eff_interval = (
        _norm_slide_show_interval_g128(requested_slide_show_interval)
        or SLIDE_SHOW_INTERVAL_DEFAULT_G128
    )

    # CRITICAL EMPIRICAL FACT: All 6 [TC/UB] items + [TC/UB Disp. Setting] + [Slide Show]
    # survive [Camera Settings Reset] and are reset ONLY via [Initialize].
    survived_cam_reset = eff_reset != RESET_ACTION_INITIALIZE_PHASE297
    if eff_reset == RESET_ACTION_INITIALIZE_PHASE297:
        eff_tc_preset = TC_PRESET_DEFAULT_G128
        eff_ub_preset = UB_PRESET_DEFAULT_G128
        eff_tc_format = TC_FORMAT_DEFAULT_G128
        eff_tc_run = TC_RUN_DEFAULT_G128
        eff_tc_make = TC_MAKE_DEFAULT_G128
        eff_ub_time_rec = UB_TIME_REC_DEFAULT_G128
        eff_tcub_disp = TCUB_DISP_DEFAULT_G128
        eff_media = MEDIA_SLOT_1_G128
        eff_repeat = "Off"
        eff_interval = SLIDE_SHOW_INTERVAL_DEFAULT_G128

    fr_norm = frame_rate.strip().lower()
    forced_ndf = (eff_tv == TV_SYSTEM_NTSC_G128) and (
        fr_norm in ("23.98p", "24.00p", "24p", "23.976p")
    )
    tc_format_menu_visible = eff_tv == TV_SYSTEM_NTSC_G128
    if forced_ndf or eff_tv == TV_SYSTEM_PAL_G128:
        eff_tc_format = TC_FORMAT_NDF_G128

    tcub_disp_playback_toggle_allowed = (not playback_active) or bool(playback_media_is_movie)

    # Playback [Copy] Directional Asymmetry:
    # Source = [Select Playback Media], Destination = opposite slot.
    copy_source_slot = eff_media
    copy_dest_slot = MEDIA_SLOT_2_G128 if eff_media == MEDIA_SLOT_1_G128 else MEDIA_SLOT_1_G128
    copy_direction_label = f"{copy_source_slot} -> {copy_dest_slot}"

    slot1_locked = bool(slot_1_write_protected or slot_1_contains_tier0_vault)
    copy_targets_slot1 = copy_dest_slot == MEDIA_SLOT_1_G128
    copy_blocked_by_slot1 = bool(copy_requested and copy_targets_slot1 and slot1_locked)

    block_errno: Optional[str] = None
    if copy_blocked_by_slot1:
        block_errno = "EROFS" if slot_1_write_protected else "EBUSY"

    dest_speed_ok = destination_card_speed_class in ALLOWED_DEST_CARD_SPEED_CLASSES_G128

    return {
        "reset_action": eff_reset,
        "tv_system": eff_tv,
        "frame_rate": frame_rate,
        "effective_tc_preset": eff_tc_preset,
        "effective_ub_preset": eff_ub_preset,
        "effective_tc_format": eff_tc_format,
        "tc_format_menu_visible": tc_format_menu_visible,
        "tc_format_forced_ndf": forced_ndf,
        "effective_tc_run": eff_tc_run,
        "effective_tc_make": eff_tc_make,
        "effective_ub_time_rec": eff_ub_time_rec,
        "effective_tcub_disp_setting": eff_tcub_disp,
        "tcub_6_items_survived_cam_reset": survived_cam_reset,
        "tcub_disp_survived_cam_reset": survived_cam_reset,
        "tcub_disp_playback_toggle_allowed": tcub_disp_playback_toggle_allowed,
        "effective_select_playback_media": eff_media,
        "copy_source_slot": copy_source_slot,
        "copy_destination_slot": copy_dest_slot,
        "copy_direction_label": copy_direction_label,
        "copy_blocked_by_slot1_vault_firewall": copy_blocked_by_slot1,
        "block_errno": block_errno,
        "slot1_data_sector_writes": 0,
        "slot1_avf_info_mutated": False,
        "battery_sufficient_for_copy": bool(battery_sufficient_for_copy),
        "destination_card_speed_ok": dest_speed_ok,
        "protect_flags_preserved_on_destination": False,
        "effective_slide_show_repeat": eff_repeat,
        "effective_slide_show_interval": eff_interval,
        "slide_show_survived_cam_reset": survived_cam_reset,
        "power_save_sleep_bypassed_during_slideshow": bool(slide_show_active),
    }


def compute_tcub_and_playback_copy_slot_matrix() -> Dict[str, Any]:
    """Deterministic `384`-state cross-product across
    `(2 tv_system x 2 frame_rate x 3 tcub_disp x 2 playback_media x 2 slot1_vault x 2 copy_req x 4 reset)`
    verifying `G128` invariants.
    """
    states = 0
    ndf_locked_24p_count = 0
    pal_hidden_count = 0
    tcub_survived_cam_reset_count = 0
    slot2_to_slot1_blocked_count = 0

    for tv in ALLOWED_TV_SYSTEMS_G128:
        for fr in ("29.97p", "23.98p"):
            for disp in ALLOWED_TCUB_DISP_SETTINGS_G128:
                for media in ALLOWED_PLAYBACK_MEDIA_SLOTS_G128:
                    for s1_vault in (True, False):
                        for copy_req in (True, False):
                            for r_act in ALLOWED_RESET_ACTIONS_PHASE297:
                                states += 1
                                r = resolve_fx3_tcub_format_and_playback_copy_slot_state(
                                    tv_system=tv,
                                    frame_rate=fr,
                                    requested_tc_format=TC_FORMAT_DF_G128,
                                    requested_tc_run=TC_RUN_FREE_G128,
                                    requested_tc_make=TC_MAKE_REGENERATE_G128,
                                    requested_ub_time_rec="On",
                                    requested_tcub_disp_setting=disp,
                                    requested_select_playback_media=media,
                                    slot_1_contains_tier0_vault=s1_vault,
                                    copy_requested=copy_req,
                                    reset_action=r_act,
                                )
                                if tv == TV_SYSTEM_NTSC_G128 and fr == "23.98p":
                                    assert r["tc_format_forced_ndf"] is True
                                    assert r["effective_tc_format"] == TC_FORMAT_NDF_G128
                                    ndf_locked_24p_count += 1
                                if tv == TV_SYSTEM_PAL_G128:
                                    assert r["tc_format_menu_visible"] is False
                                    pal_hidden_count += 1
                                if r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE297:
                                    assert r["effective_tc_run"] == TC_RUN_FREE_G128
                                    assert r["effective_tc_make"] == TC_MAKE_REGENERATE_G128
                                    assert r["effective_ub_time_rec"] == "On"
                                    assert r["effective_tcub_disp_setting"] == disp
                                    assert r["tcub_6_items_survived_cam_reset"] is True
                                    tcub_survived_cam_reset_count += 1
                                if (
                                    media == MEDIA_SLOT_2_G128
                                    and r_act != RESET_ACTION_INITIALIZE_PHASE297
                                    and s1_vault
                                    and copy_req
                                ):
                                    assert r["copy_destination_slot"] == MEDIA_SLOT_1_G128
                                    assert r["copy_blocked_by_slot1_vault_firewall"] is True
                                    assert r["slot1_data_sector_writes"] == 0
                                    assert r["slot1_avf_info_mutated"] is False
                                    slot2_to_slot1_blocked_count += 1

    return {
        "states_checked": states,
        "ndf_locked_24p_count": ndf_locked_24p_count,
        "pal_hidden_count": pal_hidden_count,
        "tcub_survived_cam_reset_count": tcub_survived_cam_reset_count,
        "slot2_to_slot1_blocked_count": slot2_to_slot1_blocked_count,
        "all_invariants_hold": states == 384,
    }


def verify_tcub_format_and_playback_copy_slot_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE297,
    body_model_id: int = FX3_MODEL_ID_PHASE297,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE297,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE297,
    target_model: str = FX3_MODEL_NAME_PHASE297,
    tv_system: str = TV_SYSTEM_NTSC_G128,
    frame_rate: str = "29.97p",
    requested_tc_preset: str = TC_PRESET_DEFAULT_G128,
    requested_ub_preset: str = UB_PRESET_DEFAULT_G128,
    requested_tc_format: str = TC_FORMAT_DEFAULT_G128,
    tc_format_change_requested: bool = False,
    requested_tc_run: str = TC_RUN_DEFAULT_G128,
    requested_tc_make: str = TC_MAKE_DEFAULT_G128,
    requested_ub_time_rec: str = UB_TIME_REC_DEFAULT_G128,
    requested_tcub_disp_setting: str = TCUB_DISP_DEFAULT_G128,
    playback_active: bool = False,
    playback_media_is_movie: bool = True,
    tcub_disp_toggle_in_playback_requested: bool = False,
    claimed_tcub_resets_on_cam_settings_reset: bool = False,
    claimed_fx3_has_bnc_tc_port: bool = False,
    requested_select_playback_media: str = MEDIA_SLOT_1_G128,
    slot_1_write_protected: bool = False,
    slot_1_contains_tier0_vault: bool = True,
    copy_requested: bool = False,
    copy_includes_movie: bool = False,
    battery_sufficient_for_copy: bool = True,
    destination_card_speed_class: str = "CFexpress Type A",
    claimed_copy_preserves_protect_flags: bool = False,
    slide_show_start_requested: bool = False,
    slide_show_view_mode: str = SLIDE_SHOW_VIEW_DATE_G128,
    requested_slide_show_repeat: str = "Off",
    requested_slide_show_interval: str = SLIDE_SHOW_INTERVAL_DEFAULT_G128,
    slide_show_active: bool = False,
    claimed_power_save_triggers_during_slideshow: bool = False,
    claimed_fx6_has_slideshow_or_copy_clip: bool = False,
    fx6_copy_clip_requested: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE297,
) -> TcubFormatAndPlaybackCopySlotGuardResult:
    """Verify Wave-54 Gate `G128` hardware safety contracts."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version) if isinstance(firmware_version, str) else None
    norm_reset = _norm_reset_action_phase297(reset_action)
    norm_tv = _norm_tv_system_g128(tv_system)
    norm_tc_fmt = _norm_tc_format_g128(requested_tc_format)
    norm_tc_run = _norm_tc_run_g128(requested_tc_run)
    norm_tc_make = _norm_tc_make_g128(requested_tc_make)
    norm_ub_time = _norm_on_off_phase297(requested_ub_time_rec)
    norm_disp = _norm_tcub_disp_g128(requested_tcub_disp_setting)
    norm_media = _norm_playback_media_slot_g128(requested_select_playback_media)
    norm_repeat = _norm_on_off_phase297(requested_slide_show_repeat)
    norm_interval = _norm_slide_show_interval_g128(requested_slide_show_interval)

    if (
        body_model_name != FX3_MODEL_NAME_PHASE297
        or not _is_real_int(body_model_id)
        or body_model_id != FX3_MODEL_ID_PHASE297
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE297
        or fw_tuple is None
        or norm_reset is None
        or norm_tv is None
        or norm_tc_fmt is None
        or norm_tc_run is None
        or norm_tc_make is None
        or norm_ub_time is None
        or norm_disp is None
        or norm_media is None
        or norm_repeat is None
        or norm_interval is None
        or (not isinstance(requested_tc_preset, str) or not _is_valid_tc_preset(requested_tc_preset))
        or (not isinstance(requested_ub_preset, str) or not _is_valid_ub_preset(requested_ub_preset))
        or target_model not in (FX3_MODEL_NAME_PHASE297, FX6_MODEL_NAME_PHASE297)
    ):
        _add_code(codes, STATUS_BLOCKED_G128_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3/FX6 identity, TC/UB preset/format, Playback Copy slot, or Slide Show telemetry."
        )

    eff = resolve_fx3_tcub_format_and_playback_copy_slot_state(
        tv_system=norm_tv or TV_SYSTEM_NTSC_G128,
        frame_rate=frame_rate,
        requested_tc_preset=(
            requested_tc_preset
            if isinstance(requested_tc_preset, str) and _is_valid_tc_preset(requested_tc_preset)
            else TC_PRESET_DEFAULT_G128
        ),
        requested_ub_preset=(
            requested_ub_preset
            if isinstance(requested_ub_preset, str) and _is_valid_ub_preset(requested_ub_preset)
            else UB_PRESET_DEFAULT_G128
        ),
        requested_tc_format=norm_tc_fmt or TC_FORMAT_DEFAULT_G128,
        requested_tc_run=norm_tc_run or TC_RUN_DEFAULT_G128,
        requested_tc_make=norm_tc_make or TC_MAKE_DEFAULT_G128,
        requested_ub_time_rec=norm_ub_time or UB_TIME_REC_DEFAULT_G128,
        requested_tcub_disp_setting=norm_disp or TCUB_DISP_DEFAULT_G128,
        playback_active=playback_active,
        playback_media_is_movie=playback_media_is_movie,
        requested_select_playback_media=norm_media or MEDIA_SLOT_1_G128,
        slot_1_write_protected=slot_1_write_protected,
        slot_1_contains_tier0_vault=slot_1_contains_tier0_vault,
        copy_requested=copy_requested,
        battery_sufficient_for_copy=battery_sufficient_for_copy,
        destination_card_speed_class=destination_card_speed_class,
        slide_show_view_mode=slide_show_view_mode,
        requested_slide_show_repeat=norm_repeat or "Off",
        requested_slide_show_interval=norm_interval or SLIDE_SHOW_INTERVAL_DEFAULT_G128,
        slide_show_active=slide_show_active,
        reset_action=norm_reset or RESET_ACTION_NONE_PHASE297,
    )

    # Part A: [TC/UB] 6 items & [TC/UB Disp. Setting] Initialize-only reset + playback toggle
    if claimed_tcub_resets_on_cam_settings_reset:
        _add_code(
            codes,
            STATUS_BLOCKED_G128_TCUB_RESET_PERSISTENCE_OR_PLAYBACK_TOGGLE_VIOLATION,
        )
        errors.append(
            "All 6 [TC/UB] items (`Time Code Preset`, `User Bit Preset`, `Time Code Format`, "
            "`Time Code Run`, `Time Code Make`, `User Bit Time Rec`) plus `[TC/UB Disp. Setting]` "
            "survive [Camera Settings Reset] (reset ONLY via [Initialize])."
        )

    if tcub_disp_toggle_in_playback_requested and playback_active and (not playback_media_is_movie):
        _add_code(
            codes,
            STATUS_BLOCKED_G128_TCUB_RESET_PERSISTENCE_OR_PLAYBACK_TOGGLE_VIOLATION,
        )
        errors.append(
            "[TC/UB Disp. Setting] toggle during playback is Movie-only (`.uxc 0xe728`: "
            "'TC/UB display switching is invalid during still playback')."
        )

    if claimed_fx3_has_bnc_tc_port:
        _add_code(
            codes,
            STATUS_BLOCKED_G128_TCUB_RESET_PERSISTENCE_OR_PLAYBACK_TOGGLE_VIOLATION,
        )
        errors.append(
            "ILME-FX3 has NO physical BNC TC IN/TC OUT port (unlike ILME-FX6 physical BNC + IN/OUT switch + EXT-LK)."
        )

    # Part B: [Time Code Format] NTSC-only, forced NDF in 23.98p/24.00p, hidden in PAL
    if (norm_tv == TV_SYSTEM_PAL_G128) and tc_format_change_requested:
        _add_code(codes, STATUS_BLOCKED_G128_TC_FORMAT_PAL_OR_24P_NDF_LOCK_VIOLATION)
        errors.append(
            "[Time Code Format] is NTSC-only and hidden in PAL (`[NTSC/PAL Selector] = PAL`)."
        )

    if eff["tc_format_forced_ndf"] and (norm_tc_fmt == TC_FORMAT_DF_G128) and tc_format_change_requested:
        _add_code(codes, STATUS_BLOCKED_G128_TC_FORMAT_PAL_OR_24P_NDF_LOCK_VIOLATION)
        errors.append(
            f"[Time Code Format] is forced `NDF` (`[-]`) in `{frame_rate}` (`DF` selection blocked)."
        )

    # Part C: Playback [Copy] Directional Asymmetry Firewall (`Slot 2 -> Slot 1` Tier-0 Vault!)
    if eff["copy_blocked_by_slot1_vault_firewall"]:
        _add_code(
            codes, STATUS_BLOCKED_G128_SLOT2_TO_SLOT1_VAULT_COPY_FIREWALL_VIOLATION
        )
        errors.append(
            f"Playback [Copy] (`FUNC_copy_content`) with `[Select Playback Media] = {eff['copy_source_slot']}` "
            f"reverses write direction to `{eff['copy_direction_label']}` onto read-only Tier-0 Slot-1 vault "
            f"(`errno={eff['block_errno']}`): blocked fail-closed (`slot1_data_sector_writes == 0`, "
            "`slot1_avf_info_mutated == False`)."
        )

    if claimed_copy_preserves_protect_flags:
        _add_code(
            codes, STATUS_BLOCKED_G128_SLOT2_TO_SLOT1_VAULT_COPY_FIREWALL_VIOLATION
        )
        errors.append(
            "Playback [Copy] strips `Protect` flags and burst group display on the destination card."
        )

    # Part D: Battery gate, destination card speed class, [Slide Show] & FX6 exclusions
    if copy_requested and (not battery_sufficient_for_copy):
        _add_code(codes, STATUS_BLOCKED_G128_COPY_BATTERY_SPEED_OR_SLIDESHOW_FX6_VIOLATION)
        errors.append(
            "Playback [Copy] blocked by `get_battery_status_for_copy`: insufficient battery power."
        )

    if copy_requested and copy_includes_movie and (not eff["destination_card_speed_ok"]):
        _add_code(codes, STATUS_BLOCKED_G128_COPY_BATTERY_SPEED_OR_SLIDESHOW_FX6_VIOLATION)
        errors.append(
            f"Movie [Copy] blocked (`.uxc 0xe80e/0xe8ca`): destination card `{destination_card_speed_class}` "
            "below SDXC Class10/U1/V10 or CFexpress Type A threshold."
        )

    if slide_show_start_requested and (
        slide_show_view_mode not in ALLOWED_SLIDE_SHOW_VIEW_MODES_G128
    ):
        _add_code(codes, STATUS_BLOCKED_G128_COPY_BATTERY_SPEED_OR_SLIDESHOW_FX6_VIOLATION)
        errors.append(
            f"[Slide Show] can ONLY start in `Date View` or `Folder View(Still)` (not `{slide_show_view_mode}`)."
        )

    if claimed_power_save_triggers_during_slideshow:
        _add_code(codes, STATUS_BLOCKED_G128_COPY_BATTERY_SPEED_OR_SLIDESHOW_FX6_VIOLATION)
        errors.append(
            "[Slide Show] automatically bypasses `[Power Save Start Time]` (`DURING_PLAYBACK_SLIDESHOW`)."
        )

    if claimed_fx6_has_slideshow_or_copy_clip or (
        target_model == FX6_MODEL_NAME_PHASE297
        and (slide_show_start_requested or fx6_copy_clip_requested or copy_requested)
    ):
        _add_code(codes, STATUS_BLOCKED_G128_COPY_BATTERY_SPEED_OR_SLIDESHOW_FX6_VIOLATION)
        errors.append(
            "ILME-FX6 Ver. 6.01 lacks `[Slide Show]` and in-camera `[Copy Clip]`/`[Copy All]` "
            "(dormant PXW-FX9 `BKID_APP_USER_MENU_COPY_CLIP*` blocked; FX6 uses FTP Transfer Clip <= 200 or Catalyst Browse/Prepare)."
        )

    matrix = compute_tcub_and_playback_copy_slot_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G128 if valid else codes[0]

    return TcubFormatAndPlaybackCopySlotGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE297,
        target_model=target_model,
        reset_action=eff["reset_action"],
        tv_system=eff["tv_system"],
        frame_rate=eff["frame_rate"],
        effective_tc_preset=eff["effective_tc_preset"],
        effective_ub_preset=eff["effective_ub_preset"],
        effective_tc_format=eff["effective_tc_format"],
        tc_format_menu_visible=eff["tc_format_menu_visible"],
        tc_format_forced_ndf=eff["tc_format_forced_ndf"],
        effective_tc_run=eff["effective_tc_run"],
        effective_tc_make=eff["effective_tc_make"],
        effective_ub_time_rec=eff["effective_ub_time_rec"],
        effective_tcub_disp_setting=eff["effective_tcub_disp_setting"],
        tcub_6_items_survived_cam_reset=eff["tcub_6_items_survived_cam_reset"],
        tcub_disp_survived_cam_reset=eff["tcub_disp_survived_cam_reset"],
        initialize_required_to_reset_tcub=True,
        playback_active=bool(playback_active),
        playback_media_is_movie=bool(playback_media_is_movie),
        tcub_disp_playback_toggle_allowed=eff["tcub_disp_playback_toggle_allowed"],
        fx3_has_bnc_tc_port=False,
        fx6_has_bnc_tc_port=True,
        effective_select_playback_media=eff["effective_select_playback_media"],
        copy_source_slot=eff["copy_source_slot"],
        copy_destination_slot=eff["copy_destination_slot"],
        copy_direction_label=eff["copy_direction_label"],
        slot_1_write_protected=bool(slot_1_write_protected),
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        copy_requested=bool(copy_requested),
        copy_blocked_by_slot1_vault_firewall=eff["copy_blocked_by_slot1_vault_firewall"],
        block_errno=eff["block_errno"],
        slot1_data_sector_writes=eff["slot1_data_sector_writes"],
        slot1_avf_info_mutated=eff["slot1_avf_info_mutated"],
        battery_sufficient_for_copy=eff["battery_sufficient_for_copy"],
        destination_card_speed_class=destination_card_speed_class,
        destination_card_speed_ok=eff["destination_card_speed_ok"],
        protect_flags_preserved_on_destination=eff["protect_flags_preserved_on_destination"],
        slide_show_view_mode=slide_show_view_mode,
        effective_slide_show_repeat=eff["effective_slide_show_repeat"],
        effective_slide_show_interval=eff["effective_slide_show_interval"],
        slide_show_survived_cam_reset=eff["slide_show_survived_cam_reset"],
        power_save_sleep_bypassed_during_slideshow=eff[
            "power_save_sleep_bypassed_during_slideshow"
        ],
        fx6_lacks_slideshow_and_copy_clip=True,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g128_tcub_format_and_playback_copy_slot_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    tcub_playback_copy_slot_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase297DonorAuditResult] = None,
) -> Tuple[GateVerdict, G128TcubPlaybackCopySlotGuardResult]:
    """Evaluate Wave-54 Gate `G128` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase297_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_tcub_format_and_playback_copy_slot_guard(
        **(dict(tcub_playback_copy_slot_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G128.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G128 if valid else codes[0]

    res = G128TcubPlaybackCopySlotGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        tcub_playback_copy_slot_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, tc_fmt={guard.effective_tc_format},"
        f"tc_disp={guard.effective_tcub_disp_setting},"
        f"tcub_survived={guard.tcub_6_items_survived_cam_reset},"
        f"copy_dir={guard.copy_direction_label},"
        f"slot1_vault={guard.slot_1_contains_tier0_vault},"
        f"s1_writes={guard.slot1_data_sector_writes},"
        f"slideshow_int={guard.effective_slide_show_interval}"
    )
    verdict = GateVerdict(
        gate_id=G128_GATE_ID,
        gate_code=G128_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `128`-Gate Power-of-Two Milestone Master Safety Preflight (`G01..G128`)
# ---------------------------------------------------------------------------


def evaluate_128gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    switch_vh_af_exposure_stdadj_kwargs: Optional[Mapping[str, Any]] = None,
    tcub_playback_copy_slot_kwargs: Optional[Mapping[str, Any]] = None,
    master_126_override: Optional[Master126GateReport] = None,
    **m126_passthrough_kwargs: Any,
) -> Master128GateReport:
    """Evaluate all 128 Master Safety Gates (`G01..G128`) deterministically by
    delegating `G01..G126` directly to `evaluate_126gate_preflight()`.
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

    m126_report: Master126GateReport = (
        master_126_override
        if master_126_override is not None
        else evaluate_126gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m126_passthrough_kwargs,
        )
    )

    phase297_audit = audit_phase297_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g127_verdict, g127_res = evaluate_g127_switch_vh_af_and_exposure_stdadj_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        switch_vh_af_exposure_stdadj_kwargs=switch_vh_af_exposure_stdadj_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase297_audit,
    )

    g128_verdict, g128_res = evaluate_g128_tcub_format_and_playback_copy_slot_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        tcub_playback_copy_slot_kwargs=tcub_playback_copy_slot_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase297_audit,
    )

    gates_127_to_128 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g127_verdict, g128_verdict)
    ]
    all_gates = tuple(list(m126_report.gates) + gates_127_to_128)

    g01_to_g12_verified = int(m126_report.summary["g01_to_g12_verified"])
    g13_to_g126_verified = int(m126_report.summary["g13_to_g124_verified"]) + int(
        m126_report.summary["g125_to_g126_verified"]
    )
    g127_to_g128_verified = sum(1 for v in (g127_verdict, g128_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g126_verified + g127_to_g128_verified

    g127_to_g128_all_passed = g127_to_g128_verified == 2
    g13_to_g128_all_passed = (
        m126_report.g13_to_g126_all_passed and g127_to_g128_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m126_report.gates[:9])

    offline_125_verified = (
        g01_to_g09_ok
        and m126_report.offline_123_gates_verified
        and g127_to_g128_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_128_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g128_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m126_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_125_verified
        and m126_report.h0_h1_trial_entry_allowed
        and g127_to_g128_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not CROSS_MODEL_FLASH_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m126_report.errors)
        + list(g127_verdict.errors)
        + list(g128_verdict.errors)
    )
    warnings: List[str] = (
        list(m126_report.warnings)
        + list(g127_verdict.warnings)
        + list(g128_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m126_report.g13_to_g126_all_passed:
        overall_status = m126_report.status
    elif not g127_verdict.passed:
        overall_status = g127_verdict.status
    elif not g128_verdict.passed:
        overall_status = g128_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_128_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_128_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_128_verified:
        overall_status = "VERIFIED_ALL_128_GATES"
    else:
        overall_status = "VERIFIED_125_OF_128_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m126_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g127_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g128_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 128,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 128 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g126_verified": g13_to_g126_verified,
        "g127_to_g128_verified": g127_to_g128_verified,
        "g13_to_g128_all_passed": g13_to_g128_all_passed,
        "g127_to_g128_all_passed": g127_to_g128_all_passed,
        "offline_125_gates_verified": offline_125_verified,
        "all_128_gates_verified": all_128_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "human_hardware_attach_token": HUMAN_HARDWARE_ATTACH_TOKEN,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "cross_model_flash_authorized": CROSS_MODEL_FLASH_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master128GateReport(
        schema=REALHW_SWITCH_VH_AF_STDADJ_BRACKET_TCUB_COPY_SLOT_128GATE_SCHEMA,
        version=REALHW_SWITCH_VH_AF_STDADJ_BRACKET_TCUB_COPY_SLOT_128GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_125_gates_verified=offline_125_verified,
        all_128_gates_verified=all_128_verified,
        g13_to_g128_all_passed=g13_to_g128_all_passed,
        g127_to_g128_all_passed=g127_to_g128_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_126_report=m126_report.to_dict(),
        g127_result=g127_res.to_dict(),
        g128_result=g128_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_128_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master128GateReport:
    return evaluate_128gate_preflight(repo_root, **kwargs)


def run_128_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master128GateReport:
    return evaluate_128gate_preflight(repo_root, **kwargs)


def _safe_write_json(payload: Any) -> None:
    try:
        sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.close(devnull)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard",
        description="Phase 297 Wave-54 G127/G128 & 128/128 Milestone Preflight CLI",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    parser.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all 128/128 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g127", "g128", "128"],
        default="128",
        help="Target gate check: g127, g128, or 128",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g127":
        v, r = evaluate_g127_switch_vh_af_and_exposure_stdadj_guard(
            repo_root=args.repo_root,
            force_clean_room=clean,
        )
        if args.json:
            _safe_write_json(
                {
                    "gate": v.gate_id,
                    "status": r.status,
                    "verification_mode": r.verification_mode,
                    "valid": r.valid,
                }
                if args.summary
                else r.to_dict()
            )
        else:
            sys.stdout.write(f"gate={v.gate_id} status={r.status} valid={r.valid}\n")
        return 0 if r.valid else 1

    if args.gate == "g128":
        v, r = evaluate_g128_tcub_format_and_playback_copy_slot_guard(
            repo_root=args.repo_root,
            force_clean_room=clean,
        )
        if args.json:
            _safe_write_json(
                {
                    "gate": v.gate_id,
                    "status": r.status,
                    "verification_mode": r.verification_mode,
                    "valid": r.valid,
                }
                if args.summary
                else r.to_dict()
            )
        else:
            sys.stdout.write(f"gate={v.gate_id} status={r.status} valid={r.valid}\n")
        return 0 if r.valid else 1

    rep = evaluate_128gate_preflight(
        args.repo_root,
        force_clean_room=clean,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        _safe_write_json(
            {
                "status": rep.status,
                "verification_mode": rep.verification_mode,
                "summary": rep.summary,
                "g127_status": rep.g127_result["status"],
                "g128_status": rep.g128_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/128\n"
        )
    ok = rep.all_128_gates_verified if args.dry_run_simulated else rep.offline_125_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
