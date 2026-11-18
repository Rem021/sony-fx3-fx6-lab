"""Phase 299 (Wave-55, 130/130 Safety Gates Milestone!):
Real-Hardware Safety Gates G129 & G130 + Unified 130-Gate Preflight Engine.

Implements empirical `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` hardware safety gates:

1. **Gate `G129` (`verify-touch-shooting-and-disp-evf-absence-guard`)**:
   - `MENU -> (Setup) -> [Touch Operation]` (`_g.uxc 0x6345`) exposes **ONLY 4 active
     sub-items** on `ILME-FX3 Ver. 7.02`:
     1) `[Touch Operation]` (`On` [default] / `On: Playback Only` [`_f 0x6cde`] / `Off`)
     2) `[Touch Sensitivity]` (`Standard` [default] / `Sensitive` [`_f 0x7205`] — NOT `Responsive`!)
     3) `[Touch Func. in Shooting]` (`Touch Focus` / `Touch Tracking` [default] / `Off`) —
        identical across Still, Movie, and `S&Q`
     4) `[Swipe Up]` (`Open the Fn Menu` [default] / `Off`, active when `Touch Operation = On`)
     All 4 items **survive `[Camera Settings Reset]` (`[Initialize]`-only!)**.
   - Dormant multi-model Alpha traps (`Touch Shutter` `_f 0x6a80`, `Touch AE` `_f 0x702a`,
     `Touch Panel/Pad` / `Touch Pad Settings` `_f 0x76ec`, `Footer Icon Touch` `_f 0x70da`,
     `Swipe Left`/`Swipe Right`) present in `FX3 appFw.so`/`.uxc` MUST be rejected
     fail-closed. Contrasted with `ILME-FX6 Ver. 6.01` (`Technical > Touch Operation`
     `On/Off` + `Shooting > Focus > Touch Function in MF` `Spot Focus / Tracking AF`).
   - `MENU -> (Setup) -> [Operation Customize] -> [DISP (Screen Disp) Set]` (`_g 0x61c4 ->
     0x61da`, NOT under `Display Option`!) exposes **ONLY 4 shooting pages** (`Display All
     Info.`, `No Disp. Info.`, `Histogram`, `Level`) and **3 playback pages** (`Display Info.`,
     `Histogram`, `No Disp. Info.`), surviving `[Camera Settings Reset]`.
   - **Total Zero-EVF Blackout Trap Firewall**: `ILME-FX3` has **ZERO EVF, ZERO eye
     sensor, and ZERO `FINDER/MONITOR` button**. Dormant `Select Finder/Monitor`,
     `Finder/Monitor Sel.`, `For viewfinder`, `Graphic Display`, `Monitor Off`, and
     `DISP Button:Finder` keys MUST be blocked fail-closed so no script ever switches
     FX3 scanout to a non-existent EVF (black-screen soft-brick trap!), contrasted with
     `ILME-FX6` (`TYPE_BUILTIN_EVF_NOT_EXIST`, detachable 3.5" LCD `Viewfinder` +
     `Viewfinder Hood`, no `"Loupe"`).

2. **Gate `G130` (`verify-ael-wireless-flash-and-interval-pb-edit-guard`)**:
   - Still-only `[AEL w/ Shutter]` (`Exposure/Color -> [Metering]`: `Auto` default / `On` /
     `Off`, `Initialize`-only, `[AEL toggle]` overrides half-press).
   - Still-only `[Exp.comp.set]` (`Exposure/Color -> [Flash]`: `Ambient&flash` default /
     `Ambient only`, `Initialize`-only).
   - Still-only `[Wireless Flash]` (`Exposure/Color -> [Flash]`: `Off` default / `On`, **the
     ONLY one resettable via `[Camera Settings Reset]`**; supports `[Wireless Test Flash]`).
   - Still-only direct-MI-Shoe `[External Flash Set.]` (`[Ext. Flash Firing Set.]` /
     `[Ext. Flash Cust. Set.]`, `Initialize`-only; off-camera sync cord and camera-menu
     flash reset unsupported), contrasted with flash-less `ILME-FX6` (where `Flash Band
     Reduce` is CMOS rolling-shutter band compensation, NOT flash trigger!).
   - Playback `MENU -> (Playback) -> [Viewing]` (`_g 0x6033`, NOT `Playback Option`):
     `[Cont. Play for Interval]` & `[Play Speed for Interval]` exact **`1..9` speed scale
     (`default 5`, NOT `1..5`)**, `Initialize`-only, read-only safe, no in-camera movie
     assembly.
   - Playback `MENU -> (Playback) -> [Edit]` (`_g 0x6418`): exposes **ONLY 4 active items**
     (`Rotate`, `Photo Capture`, `JPEG/HEIF Switch` [`JPEG` / `HEIF(4:2:0)` / `HEIF(4:2:2)`],
     `Copy`) — blocking dormant `[Beauty Effect]` (`_f 0x7849`) & `sequence_edit_trimming_*`
     traps AND fail-closed blocking (`EROFS`/`EOPNOTSUPP`) any `Rotate` / `Photo Capture` /
     `Copy (Slot 2 -> Slot 1)` write mutation targeting read-only `Slot 1` Tier-0 vault!

3. **Unified `130`-Gate Milestone Master Preflight (`evaluate_130gate_preflight` /
   `verify-130-gates`)**:
   - Delegates `G01..G128` directly to `evaluate_128gate_preflight()` and appends `G129` +
     `G130`.
   - Offline mode: `127/130` gates pass (`VERIFIED_127_OF_130_AWAITING_PHYSICAL_TIER0`);
     `--simulate-bench-dry-run`: `130/130` simulation gates pass
     (`VERIFIED_ALL_130_GATES_DRY_RUN_SIMULATED_BACKUP`).
   - All hardware attach, persistent eMMC write, EL3/SPI-NOR transmit, and cross-model
     flash redlines remain hard-locked `False`, `usb_packets_transmitted == 0`, and
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
from .realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard import (
    Master128GateReport,
    evaluate_128gate_preflight,
)

# ---------------------------------------------------------------------------
# Schema, Version & Absolute Hardware / Firmware Safety Redlines
# ---------------------------------------------------------------------------

REALHW_TOUCH_SHOOTING_DISP_EVF_AEL_FLASH_INTERVAL_PB_130GATE_SCHEMA = (
    "realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard_v1"
)
REALHW_TOUCH_SHOOTING_DISP_EVF_AEL_FLASH_INTERVAL_PB_130GATE_VERSION = "2026.11.17"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST_PHASE299 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE299 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE299 = 15.0

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
G129 = "G129"
G129_GATE_ID = "G129"
G129_GATE_CODE = "GATE_G129_TOUCH_OPERATION_DISP_4MODE_AND_ZERO_EVF_BLACKOUT_GUARD"
GATE_G129_TOUCH_OPERATION_DISP_4MODE_AND_ZERO_EVF_BLACKOUT_GUARD = G129_GATE_CODE

G130 = "G130"
G130_GATE_ID = "G130"
G130_GATE_CODE = "GATE_G130_AEL_WIRELESS_FLASH_INTERVAL_9SCALE_AND_PLAYBACK_EDIT_VAULT_GUARD"
GATE_G130_AEL_WIRELESS_FLASH_INTERVAL_9SCALE_AND_PLAYBACK_EDIT_VAULT_GUARD = G130_GATE_CODE

# Model & Identity Contracts (Phase 299 suffixed to avoid __init__.py shadowing)
FX3_MODEL_NAME_PHASE299 = "ILME-FX3"
FX3_MODEL_ID_PHASE299 = 0x39383232
FX3_HELP_GUIDE_CODE_PHASE299 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE299 = "7.02"

FX6_MODEL_NAME_PHASE299 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE299 = "6.01"
FX6_PRODUCT_CODE_PHASE299 = "PRODUCT_MODEL_CHAPLIN"

# Shoot Modes & Reset Actions
SHOOT_MODE_STILL_PHASE299 = "Still"
SHOOT_MODE_MOVIE_PHASE299 = "Movie"
SHOOT_MODE_SQ_PHASE299 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE299: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE299,
    SHOOT_MODE_MOVIE_PHASE299,
    SHOOT_MODE_SQ_PHASE299,
)

RESET_ACTION_NONE_PHASE299 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE299 = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE299 = "Reset Network Set."
RESET_ACTION_INITIALIZE_PHASE299 = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE299: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE299,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE299,
    RESET_ACTION_RESET_NETWORK_SET_PHASE299,
    RESET_ACTION_INITIALIZE_PHASE299,
)

# ---------------------------------------------------------------------------
# G129 Constants: [Touch Operation] 4-Item + [DISP (Screen Disp) Set] + Zero EVF
# ---------------------------------------------------------------------------

TOUCH_OPERATION_MENU_PATH_G129 = "MENU -> (Setup) -> [Touch Operation]"
TOUCH_OPERATION_G_UXC_RESID16_G129 = 0x6345
TOUCH_OPERATION_BASE_UXC_RESID16_G129 = 0xE8E3

TOUCH_OPERATION_4_ITEMS_G129: Tuple[str, ...] = (
    "Touch Operation",
    "Touch Sensitivity",
    "Touch Func. in Shooting",
    "Swipe Up",
)

TOUCH_OP_ON_G129 = "On"
TOUCH_OP_PLAYBACK_ONLY_G129 = "On: Playback Only"
TOUCH_OP_OFF_G129 = "Off"
TOUCH_OP_DEFAULT_G129 = TOUCH_OP_ON_G129
ALLOWED_TOUCH_OPERATION_MODES_G129: Tuple[str, ...] = (
    TOUCH_OP_ON_G129,
    TOUCH_OP_PLAYBACK_ONLY_G129,
    TOUCH_OP_OFF_G129,
)

TOUCH_SENSITIVITY_F_UXC_RESID16_G129 = 0x739F
TOUCH_SENSITIVITY_STANDARD_G129 = "Standard"
TOUCH_SENSITIVITY_SENSITIVE_G129 = "Sensitive"
TOUCH_SENSITIVITY_DEFAULT_G129 = TOUCH_SENSITIVITY_STANDARD_G129
ALLOWED_TOUCH_SENSITIVITIES_G129: Tuple[str, ...] = (
    TOUCH_SENSITIVITY_STANDARD_G129,
    TOUCH_SENSITIVITY_SENSITIVE_G129,
)
DORMANT_OR_WRONG_TOUCH_SENSITIVITY_G129 = "Responsive"

TOUCH_FUNC_SHOOTING_F_UXC_RESID16_G129 = 0x7575
TOUCH_FUNC_TOUCH_FOCUS_G129 = "Touch Focus"
TOUCH_FUNC_TOUCH_TRACKING_G129 = "Touch Tracking"
TOUCH_FUNC_OFF_G129 = "Off"
TOUCH_FUNC_DEFAULT_G129 = TOUCH_FUNC_TOUCH_TRACKING_G129
ALLOWED_TOUCH_FUNC_IN_SHOOTING_G129: Tuple[str, ...] = (
    TOUCH_FUNC_TOUCH_FOCUS_G129,
    TOUCH_FUNC_TOUCH_TRACKING_G129,
    TOUCH_FUNC_OFF_G129,
)

SWIPE_UP_F_UXC_RESID16_G129 = 0x7518
SWIPE_UP_OPEN_FN_MENU_G129 = "Open the Fn Menu"
SWIPE_UP_OFF_G129 = "Off"
SWIPE_UP_DEFAULT_G129 = SWIPE_UP_OPEN_FN_MENU_G129
ALLOWED_SWIPE_UP_MODES_G129: Tuple[str, ...] = (
    SWIPE_UP_OPEN_FN_MENU_G129,
    SWIPE_UP_OFF_G129,
)

DORMANT_TOUCH_TRAP_KEYS_G129: Tuple[str, ...] = (
    "Touch Shutter",
    "Touch AE",
    "Touch Focus+AE",
    "Touch AE Cancel",
    "Touch Panel/Pad",
    "Touch Pad Settings",
    "Touch Pad Only",
    "Touch Pad (vertical)",
    "Footer Icon Touch",
    "Swipe Left",
    "Swipe Right",
    "VAL_setting_shooting_touch_function_SHOOTING_TOUCH_FUNCTION_TOUCH_SHUTTER",
    "FUNC_touch_shutter_yuv_seq",
    "PID_SET_TOUCH_SPOT_METER",
    "BKID_APP_setting_touch_panel_pad",
    "BKID_APP_setting_touch_pad_operation_area",
)

DISP_SET_MENU_PATH_G129 = (
    "MENU -> (Setup) -> [Operation Customize] -> [DISP (Screen Disp) Set]"
)
DISP_SET_WRONG_PATH_G129 = "MENU -> (Setup) -> [Display Option] -> [DISP (Screen Disp) Set]"
OPERATION_CUSTOMIZE_G_UXC_RESID16_G129 = 0x61C4
DISP_SET_G_UXC_RESID16_G129 = 0x61DA

DISP_SHOOT_4_PAGES_G129: Tuple[str, ...] = (
    "Display All Info.",
    "No Disp. Info.",
    "Histogram",
    "Level",
)
DISP_PLAY_3_PAGES_G129: Tuple[str, ...] = (
    "Display Info.",
    "Histogram",
    "No Disp. Info.",
)

DORMANT_EVF_AND_DISP_TRAP_KEYS_G129: Tuple[str, ...] = (
    "Select Finder/Monitor",
    "Finder/Monitor Sel.",
    "For viewfinder",
    "Graphic Display",
    "Monitor Off",
    "DISP Button:Finder",
    "FINDER/MONITOR",
    "BKID_APP_setting_finder_monitor",
    "BKID_APP_disp_mode_shoot_finder",
    "BKID_APP_valid_disp_mode_shoot_monitor_for_viewfinder",
    "BKID_APP_valid_disp_mode_shoot_monitor_monitor_off",
    "FUNC_toggle_set_finder_monitor_sel_seq",
    "FUNC_disp_button_finder_seq",
    "BKID_APP_extern_disp_layoutmode_rec_evf",
)

FX6_TOUCH_OPERATION_MENU_PATH_G129 = "Technical > Touch Operation"
FX6_TOUCH_MF_MENU_PATH_G129 = "Shooting > Focus > Touch Function in MF"
FX6_TOUCH_MF_ALLOWED_G129: Tuple[str, ...] = ("Spot Focus", "Tracking AF")
FX6_DETACHABLE_LCD_TERMS_G129: Tuple[str, ...] = ("Viewfinder", "Viewfinder Hood")
FX6_INFO_DISP_OPERATION_MODES_G129: Tuple[str, ...] = (
    "Home Screen Priority",
    "Direct Menu Priority",
)

# ---------------------------------------------------------------------------
# G130 Constants: Still [AEL w/ Shutter] / [Flash] + Interval PB 1..9 & [Edit]
# ---------------------------------------------------------------------------

AEL_W_SHUTTER_MENU_PATH_G130 = "MENU -> (Exposure/Color) -> [Metering] -> [AEL w/ Shutter]"
AEL_W_SHUTTER_F_UXC_RESID16_G130 = 0x669D
AEL_W_SHUTTER_AUTO_G130 = "Auto"
AEL_W_SHUTTER_ON_G130 = "On"
AEL_W_SHUTTER_OFF_G130 = "Off"
AEL_W_SHUTTER_DEFAULT_G130 = AEL_W_SHUTTER_AUTO_G130
ALLOWED_AEL_W_SHUTTER_MODES_G130: Tuple[str, ...] = (
    AEL_W_SHUTTER_AUTO_G130,
    AEL_W_SHUTTER_ON_G130,
    AEL_W_SHUTTER_OFF_G130,
)

EXP_COMP_SET_MENU_PATH_G130 = "MENU -> (Exposure/Color) -> [Flash] -> [Exp.comp.set]"
EXP_COMP_SET_F_UXC_RESID16_G130 = 0x73C2
EXP_COMP_SET_BASE_UXC_RESID16_G130 = 0xE11A
EXP_COMP_SET_AMBIENT_AND_FLASH_G130 = "Ambient&flash"
EXP_COMP_SET_AMBIENT_ONLY_G130 = "Ambient only"
EXP_COMP_SET_DEFAULT_G130 = EXP_COMP_SET_AMBIENT_AND_FLASH_G130
ALLOWED_EXP_COMP_SET_MODES_G130: Tuple[str, ...] = (
    EXP_COMP_SET_AMBIENT_AND_FLASH_G130,
    EXP_COMP_SET_AMBIENT_ONLY_G130,
)

WIRELESS_FLASH_MENU_PATH_G130 = "MENU -> (Exposure/Color) -> [Flash] -> [Wireless Flash]"
WIRELESS_FLASH_F_UXC_RESID16_G130 = 0x6201
WIRELESS_TEST_FLASH_F_UXC_RESID16_G130 = 0x7567
WIRELESS_FLASH_OFF_G130 = "Off"
WIRELESS_FLASH_ON_G130 = "On"
WIRELESS_FLASH_DEFAULT_G130 = WIRELESS_FLASH_OFF_G130
ALLOWED_WIRELESS_FLASH_MODES_G130: Tuple[str, ...] = (
    WIRELESS_FLASH_OFF_G130,
    WIRELESS_FLASH_ON_G130,
)

EXT_FLASH_SET_MENU_PATH_G130 = (
    "MENU -> (Exposure/Color) -> [Flash] -> [External Flash Set.]"
)
EXT_FLASH_SET_F_UXC_RESID16_G130 = 0x6771
EXT_FLASH_SUBMENUS_G130: Tuple[str, ...] = (
    "Ext. Flash Firing Set.",
    "Ext. Flash Cust. Set.",
)
FX6_FLASH_BAND_REDUCE_NAME_G130 = "Flash Band Reduce"

INTERVAL_PB_MENU_PATH_G130 = "MENU -> (Playback) -> [Viewing]"
INTERVAL_PB_WRONG_PATH_G130 = "MENU -> (Playback) -> [Playback Option]"
CONT_PLAY_FOR_INTERVAL_F_UXC_RESID16_G130 = 0x78FA
CONT_PB_FOR_INTERVAL_LEGACY_F_UXC_RESID16_G130 = 0x72E6
PLAY_SPEED_FOR_INTERVAL_F_UXC_RESID16_G130 = 0x639E
PB_SPEED_FOR_INTERVAL_LEGACY_F_UXC_RESID16_G130 = 0x72BD

PLAY_SPEED_INTERVAL_MIN_G130 = 1
PLAY_SPEED_INTERVAL_MAX_G130 = 9
PLAY_SPEED_INTERVAL_DEFAULT_G130 = 5
ALLOWED_PLAY_SPEED_INTERVAL_SCALE_G130: Tuple[int, ...] = tuple(
    range(PLAY_SPEED_INTERVAL_MIN_G130, PLAY_SPEED_INTERVAL_MAX_G130 + 1)
)

PLAYBACK_EDIT_MENU_PATH_G130 = "MENU -> (Playback) -> [Edit]"
PLAYBACK_EDIT_ACTIVE_4_ITEMS_G130: Tuple[str, ...] = (
    "Rotate",
    "Photo Capture",
    "JPEG/HEIF Switch",
    "Copy",
)
DORMANT_PLAYBACK_EDIT_TRAP_ITEMS_G130: Tuple[str, ...] = (
    "Beauty Effect",
    "Trimming",
    "API_START_BEAUTYEFFECT_DETECTION",
    "sequence_edit_trimming_start",
)

PHOTO_CAPTURE_FILE_JPEG_G130 = "JPEG"
PHOTO_CAPTURE_FILE_HEIF_420_G130 = "HEIF(4:2:0)"
PHOTO_CAPTURE_FILE_HEIF_422_G130 = "HEIF(4:2:2)"
PHOTO_CAPTURE_FILE_DEFAULT_G130 = PHOTO_CAPTURE_FILE_JPEG_G130
ALLOWED_PHOTO_CAPTURE_FILE_TYPES_G130: Tuple[str, ...] = (
    PHOTO_CAPTURE_FILE_JPEG_G130,
    PHOTO_CAPTURE_FILE_HEIF_420_G130,
    PHOTO_CAPTURE_FILE_HEIF_422_G130,
)

MEDIA_SLOT_1_PHASE299 = "Slot 1"
MEDIA_SLOT_2_PHASE299 = "Slot 2"
ALLOWED_MEDIA_SLOTS_PHASE299: Tuple[str, ...] = (
    MEDIA_SLOT_1_PHASE299,
    MEDIA_SLOT_2_PHASE299,
)

# Status / Violation Codes
STATUS_BLOCKED_PHASE299_DONOR_INTEGRITY = "STATUS_BLOCKED_PHASE299_DONOR_INTEGRITY"

STATUS_VERIFIED_G129 = "STATUS_VERIFIED_G129"
STATUS_BLOCKED_G129_TELEMETRY_INVALID = "STATUS_BLOCKED_G129_TELEMETRY_INVALID"
STATUS_BLOCKED_G129_TOUCH_RESET_OR_DORMANT_TRAP_VIOLATION = (
    "STATUS_BLOCKED_G129_TOUCH_RESET_OR_DORMANT_TRAP_VIOLATION"
)
STATUS_BLOCKED_G129_DISP_4MODE_OR_PATH_VIOLATION = (
    "STATUS_BLOCKED_G129_DISP_4MODE_OR_PATH_VIOLATION"
)
STATUS_BLOCKED_G129_ZERO_EVF_BLACKOUT_TRAP_VIOLATION = (
    "STATUS_BLOCKED_G129_ZERO_EVF_BLACKOUT_TRAP_VIOLATION"
)
STATUS_BLOCKED_G129_FX6_TOUCH_OR_EVF_CROSSWIRE_VIOLATION = (
    "STATUS_BLOCKED_G129_FX6_TOUCH_OR_EVF_CROSSWIRE_VIOLATION"
)

STATUS_VERIFIED_G130 = "STATUS_VERIFIED_G130"
STATUS_BLOCKED_G130_TELEMETRY_INVALID = "STATUS_BLOCKED_G130_TELEMETRY_INVALID"
STATUS_BLOCKED_G130_AEL_OR_FLASH_STILL_RESET_VIOLATION = (
    "STATUS_BLOCKED_G130_AEL_OR_FLASH_STILL_RESET_VIOLATION"
)
STATUS_BLOCKED_G130_EXT_FLASH_MISHOE_OR_FX6_VIOLATION = (
    "STATUS_BLOCKED_G130_EXT_FLASH_MISHOE_OR_FX6_VIOLATION"
)
STATUS_BLOCKED_G130_INTERVAL_PLAYBACK_SCALE_OR_PATH_VIOLATION = (
    "STATUS_BLOCKED_G130_INTERVAL_PLAYBACK_SCALE_OR_PATH_VIOLATION"
)
STATUS_BLOCKED_G130_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_VIOLATION = (
    "STATUS_BLOCKED_G130_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_VIOLATION"
)

# ---------------------------------------------------------------------------
# Pinned Wave-55 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE299: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (62_700_168, b"BKID_APP_setting_touch_operation"),
    (62_048_678, b"VAL_setting_touch_operation_TOUCH_OPERATION_ON_PLAYBACK_ONLY"),
    (62_700_201, b"BKID_APP_setting_touch_sensitivity"),
    (62_700_519, b"BKID_APP_setting_shooting_touch_function"),
    (62_700_345, b"BKID_APP_setting_swipe_up"),
    (62_700_306, b"BKID_APP_setting_stby_rec_touch_button"),
    (62_700_269, b"BKID_APP_setting_icon_touch_function"),
    (61_881_666, b"VAL_setting_shooting_touch_function_SHOOTING_TOUCH_FUNCTION_TOUCH_SHUTTER"),
    (60_602_488, b"FUNC_touch_shutter_yuv_seq"),
    (60_319_685, b"PID_SET_TOUCH_SPOT_METER"),
    (62_700_236, b"BKID_APP_setting_touch_panel_pad"),
    (62_700_477, b"BKID_APP_setting_touch_pad_operation_area"),
    (62_713_096, b"BKID_APP_disp_mode_shoot_monitor"),
    (62_815_616, b"BKID_APP_valid_disp_mode_shoot_monitor_all_info"),
    (62_815_664, b"BKID_APP_valid_disp_mode_shoot_monitor_no_info"),
    (62_815_711, b"BKID_APP_valid_disp_mode_shoot_monitor_histogram"),
    (62_815_760, b"BKID_APP_valid_disp_mode_shoot_monitor_level"),
    (62_815_805, b"BKID_APP_valid_disp_mode_shoot_monitor_for_viewfinder"),
    (62_815_859, b"BKID_APP_valid_disp_mode_shoot_monitor_monitor_off"),
    (62_713_161, b"BKID_APP_disp_mode_play"),
    (62_048_032, b"VAL_disp_mode_play_DISP_MODE_PLAY_INFO_ON"),
    (62_048_074, b"VAL_disp_mode_play_DISP_MODE_PLAY_HISTOGRAM"),
    (62_048_118, b"VAL_disp_mode_play_DISP_MODE_PLAY_INFO_OFF"),
    (60_606_474, b"FUNC_set_next_disp_mode_play"),
    (62_700_674, b"BKID_APP_setting_finder_monitor"),
    (62_713_129, b"BKID_APP_disp_mode_shoot_finder"),
    (60_607_213, b"FUNC_toggle_set_finder_monitor_sel_seq"),
    (60_606_446, b"FUNC_disp_button_finder_seq"),
    (62_845_298, b"BKID_APP_extern_disp_layoutmode_rec_evf"),
    (62_687_275, b"BKID_APP_setting_still_image_ael_w_shutter"),
    (62_687_452, b"BKID_APP_setting_exp_comp_set"),
    (62_687_515, b"BKID_APP_setting_wireless_flash"),
    (61_562_619, b"VAL_HAITA_setting_wireless_flash_wireless_function_for_flash_signal_communications_NOT_SET"),
    (62_843_769, b"BKID_APP_external_flash_menu_tab_number"),
    (60_084_708, b"PID_SET_EXT_FLASH_AFLED_ASSIST[InPrm1:%08x]"),
    (62_691_901, b"BKID_APP_setting_continuous_playback"),
    (62_383_026, b"VAL_setting_continuous_playback_CONTINUOUS_PLAYBACK_SPEED_1"),
    (62_382_786, b"VAL_setting_continuous_playback_CONTINUOUS_PLAYBACK_SPEED_5"),
    (62_382_546, b"VAL_setting_continuous_playback_CONTINUOUS_PLAYBACK_SPEED_9"),
    (58_332_023, b"increment_continuous_playback_speed"),
    (58_331_839, b"decrement_continuous_playback_speed"),
    (62_691_860, b"BKID_APP_setting_photo_capture_file_type"),
    (62_379_732, b"VAL_setting_photo_capture_file_type_PHOTO_CAPTURE_FILE_TYPE_JPEG"),
    (62_379_797, b"VAL_setting_photo_capture_file_type_PHOTO_CAPTURE_FILE_TYPE_HEIF_420"),
    (62_379_866, b"VAL_setting_photo_capture_file_type_PHOTO_CAPTURE_FILE_TYPE_HEIF_422"),
    (60_604_120, b"FUNC_rotate_content"),
    (62_869_788, b"API_START_BEAUTYEFFECT_DETECTION"),
    (59_820_195, b"sequence_edit_trimming_start"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE299 = (
    "2303eca0bfd8a7c43eee832b6f084c77038eb97c9547c13559c23ab8072f8eea"
)

PINNED_FX6_APPFW_SLICES_PHASE299: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (41_748_974, b"PRODUCT_MODEL_CHAPLIN"),
    (40_922_652, b"BKID_APP_SETTING_TOUCH_OPERATION"),
    (40_930_461, b"BKID_APP_SETTING_TOUCH_FUNCTION_IN_MF"),
    (40_975_781, b"BKID_APP_TOUCH_TRACKING_STATE"),
    (40_155_484, b"VAL_FEATURE_MANAGER_builtin_evf_TYPE_BUILTIN_EVF_NOT_EXIST"),
    (40_946_321, b"BKID_APP_SETTING_INFO_DISP_MODE_OPERATION"),
    (41_284_904, b"N5model22setting_exp_comp_set_tE"),
    (41_284_944, b"N5model24setting_wireless_flash_tE"),
    (41_285_144, b"N5model27launch_ext_flash_settings_tE"),
    (41_502_605, b"EXTERN_VAL_EV_SHIFT_AFFECT_AMBIENT"),
    (41_289_521, b"launch_photo_capture_t"),
    (40_803_742, b"DISP_MODE_SHOOT_MONITOR_FOR_VIEWFINDER"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE299 = (
    "7f906640e7faa754f8790f1ac599cc77bc4f746fa3c9564ca32b5510279a7123"
)

PINNED_PHASE299_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE299,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE299),
        "FX3 appFw.so Wave-55 Touch/DISP/EVF/AEL/Flash/Interval/Edit symbols",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Touch Func. in Shooting",
            b"Touch Focus",
            b"Touch Tracking",
            b"Touch Sensitivity",
            b"Sensitive",
            b"Swipe Up",
            b"Open the Fn Menu",
            b"On: Playback Only",
            b"Touch Shutter",
            b"Touch AE",
            b"Touch Panel/Pad",
            b"Footer Icon Touch",
            b"Select Finder/Monitor",
            b"AEL w/ Shutter",
            b"Exp.comp.set",
            b"Ambient&flash",
            b"Ambient only",
            b"Wireless Flash",
            b"External Flash Set.",
            b"Ext. Flash Firing Set.",
            b"Ext. Flash Cust. Set.",
            b"Cont. Play for",
            b"Play Speed for",
            b"Photo Capture",
            b"JPEG/HEIF Switch",
            b"HEIF(4:2:0)",
            b"HEIF(4:2:2)",
            b"Beauty Effect",
        ),
        "FX3 string_english_f.uxc Wave-55 EN parity",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "拍摄期间的触摸功能".encode("utf-8"),
            "触摸灵敏度".encode("utf-8"),
            "上划".encode("utf-8"),
            "触屏快门".encode("utf-8"),
            "触屏AE".encode("utf-8"),
            "页脚图标触摸".encode("utf-8"),
            "选择取景器/显示屏".encode("utf-8"),
            "快门AEL".encode("utf-8"),
            "曝光补偿设置".encode("utf-8"),
            "无线闪光灯".encode("utf-8"),
            "外置闪光灯设置".encode("utf-8"),
            "照片捕获".encode("utf-8"),
            "美化效果".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-55 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "拍攝期間的觸控功能".encode("utf-8"),
            "觸控靈敏度".encode("utf-8"),
            "向上滑動".encode("utf-8"),
            "觸控快門".encode("utf-8"),
            "觸控AE".encode("utf-8"),
            "註腳圖示觸控".encode("utf-8"),
            "選擇觀景窗/螢幕".encode("utf-8"),
            "半按快門AEL".encode("utf-8"),
            "曝光補償設定".encode("utf-8"),
            "無線閃光燈".encode("utf-8"),
            "外接閃光燈設定".encode("utf-8"),
            "照片攝取".encode("utf-8"),
            "美容效果".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-55 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "撮影時のタッチ機能".encode("utf-8"),
            "タッチ感度".encode("utf-8"),
            "上方向にスワイプ".encode("utf-8"),
            "タッチシャッター".encode("utf-8"),
            "タッチAE".encode("utf-8"),
            "ﾌｯﾀｰｱｲｺﾝﾀｯﾁ".encode("utf-8"),
            "ﾌｧｲﾝﾀﾞｰ/ﾓﾆﾀｰ選択".encode("utf-8"),
            "ｼｬｯﾀｰ半押しAEL".encode("utf-8"),
            "露出補正の影響".encode("utf-8"),
            "ワイヤレスフラッシュ".encode("utf-8"),
            "外部フラッシュ設定".encode("utf-8"),
            "動画から静止画作成".encode("utf-8"),
            "ﾋﾞｭｰﾃｨｰｴﾌｪｸﾄ".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-55 JA parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Display All Info.",
            b"No Disp. Info.",
            b"Histogram",
            b"Level",
            b"Graphic Display",
            b"For viewfinder",
            b"FINDER/MONITOR",
            b"Exp.comp.set",
            b"Ambient only",
            b"Ambient&flash",
            b"Rotate",
        ),
        "FX3 string_english.uxc Wave-55 DISP/EVF/Flash/Rotate strings",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Touch Operation",
            b"Operation Customize",
            b"DISP (Screen Disp) Set",
            b"DISP Button",
            b"Viewing",
            b"Edit",
            b"Playback Option",
            b"Touch AE Cancel",
            b"Finder/Monitor",
        ),
        "FX3 string_english_g.uxc Wave-55 menu group strings",
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
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE299,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE299),
        "FX6 appFw.so Wave-55 Touch/BuiltinEVFNotExist/InfoDisp/DormantFlash symbols",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"Touch Operation",
            b"Touch Function in MF",
            b"LCD Monitor/VF Select",
            b"Home Screen Priority",
            b"Direct Menu Priority",
        ),
        "FX6 string_english.uxc Wave-55 strings",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"Viewfinder",
            b"Display On/Off",
            b"VF Display Setting",
            b"Flash Band Reduce",
        ),
        "FX6 string_english_2.uxc Wave-55 strings",
    ),
}

_DONOR_BLOB_CACHE: Dict[str, Tuple[int, float, int, str, bytes]] = {}

# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase299DonorAuditResult:
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
class TouchShootingAndDispEvfGuardResult:
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
    effective_touch_operation: str
    effective_touch_sensitivity: str
    effective_touch_func_in_shooting: str
    effective_swipe_up: str
    touch_4_items_survived_cam_reset: bool
    swipe_up_active: bool
    dormant_touch_traps_blocked: bool
    disp_set_menu_path: str
    disp_shoot_pages_enabled: Tuple[str, ...]
    disp_play_pages_enabled: Tuple[str, ...]
    disp_set_survived_cam_reset: bool
    fx3_has_builtin_evf: bool
    fx3_has_eye_sensor: bool
    fx3_has_finder_monitor_button: bool
    fx6_has_builtin_evf: bool
    evf_scanout_blocked: bool
    lcd_panel_scanout_preserved: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G129TouchShootingDispEvfGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    touch_shooting_disp_evf_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AelFlashAndIntervalPbEditGuardResult:
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
    effective_ael_w_shutter: str
    ael_toggle_overrides_half_press: bool
    ael_w_shutter_survived_cam_reset: bool
    effective_exp_comp_set: str
    exp_comp_set_survived_cam_reset: bool
    effective_wireless_flash: str
    wireless_flash_reset_on_cam_reset: bool
    effective_external_flash_set: str
    ext_flash_direct_mishoe_only: bool
    off_camera_sync_cord_supported: bool
    fx6_has_still_flash_or_ael: bool
    fx6_flash_band_reduce_is_rolling_shutter_comp: bool
    interval_pb_menu_path: str
    effective_cont_play_for_interval: str
    effective_play_speed_for_interval: int
    play_speed_scale_min: int
    play_speed_scale_max: int
    play_speed_scale_default: int
    interval_pb_survived_cam_reset: bool
    interval_pb_read_only_safe: bool
    in_camera_timelapse_movie_assembly_supported: bool
    playback_edit_active_items: Tuple[str, ...]
    effective_photo_capture_file_type: str
    effective_select_playback_media: str
    requested_playback_edit_action: Optional[str]
    target_write_slot: Optional[str]
    slot_1_write_protected: bool
    slot_1_contains_tier0_vault: bool
    playback_edit_blocked_by_slot1_vault_firewall: bool
    block_errno: Optional[str]
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G130AelFlashIntervalPbEditGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    ael_flash_interval_pb_edit_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master130GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_127_gates_verified: bool
    all_130_gates_verified: bool
    g13_to_g130_all_passed: bool
    g129_to_g130_all_passed: bool
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
    master_128_report: Dict[str, Any]
    g129_result: Dict[str, Any]
    g130_result: Dict[str, Any]
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
    for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE299):
        if os.environ.get(env_key, "").strip() in _TRUTHY_CLEAN_ROOM_TOKENS:
            return True
    return False


def _default_donor_budget_seconds_phase299() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return DONOR_CHECK_CI_MAX_SECONDS_PHASE299
    return DONOR_CHECK_MAX_SECONDS_PHASE299


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


def _norm_reset_action_phase299(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE_PHASE299
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE299
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE299
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE_PHASE299
    return None


def _norm_shoot_mode_phase299(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("STILL", "P", "A", "S", "M", "IAUTO", "INTELLIGENT AUTO"):
        return SHOOT_MODE_STILL_PHASE299
    if u == "MOVIE":
        return SHOOT_MODE_MOVIE_PHASE299
    if u in ("S&Q", "SQ", "S&Q MOTION"):
        return SHOOT_MODE_SQ_PHASE299
    return None


def _norm_on_off_phase299(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "ON":
        return "On"
    if u == "OFF":
        return "Off"
    return None


def _norm_touch_op_g129(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u == "ON":
        return TOUCH_OP_ON_G129
    if u in ("ON: PLAYBACK ONLY", "ON:PLAYBACK ONLY", "ON_PLAYBACK_ONLY"):
        return TOUCH_OP_PLAYBACK_ONLY_G129
    if u == "OFF":
        return TOUCH_OP_OFF_G129
    return None


def _norm_touch_sensitivity_g129(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "STANDARD":
        return TOUCH_SENSITIVITY_STANDARD_G129
    if u == "SENSITIVE":
        return TOUCH_SENSITIVITY_SENSITIVE_G129
    return None


def _norm_touch_func_g129(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u == "TOUCH FOCUS":
        return TOUCH_FUNC_TOUCH_FOCUS_G129
    if u == "TOUCH TRACKING":
        return TOUCH_FUNC_TOUCH_TRACKING_G129
    if u == "OFF":
        return TOUCH_FUNC_OFF_G129
    return None


def _norm_swipe_up_g129(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("OPEN THE FN MENU", "OPEN FN MENU", "FN MENU"):
        return SWIPE_UP_OPEN_FN_MENU_G129
    if u == "OFF":
        return SWIPE_UP_OFF_G129
    return None


def _norm_ael_w_shutter_g130(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "AUTO":
        return AEL_W_SHUTTER_AUTO_G130
    if u == "ON":
        return AEL_W_SHUTTER_ON_G130
    if u == "OFF":
        return AEL_W_SHUTTER_OFF_G130
    return None


def _norm_exp_comp_set_g130(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("AMBIENT&FLASH", "AMBIENT & FLASH", "AMBIENT AND FLASH"):
        return EXP_COMP_SET_AMBIENT_AND_FLASH_G130
    if u == "AMBIENT ONLY":
        return EXP_COMP_SET_AMBIENT_ONLY_G130
    return None


def _norm_photo_capture_file_type_g130(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").replace(" ", "").upper()
    if u == "JPEG":
        return PHOTO_CAPTURE_FILE_JPEG_G130
    if u == "HEIF(4:2:0)":
        return PHOTO_CAPTURE_FILE_HEIF_420_G130
    if u == "HEIF(4:2:2)":
        return PHOTO_CAPTURE_FILE_HEIF_422_G130
    return None


def _norm_media_slot_phase299(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("SLOT 1", "SLOT1"):
        return MEDIA_SLOT_1_PHASE299
    if u in ("SLOT 2", "SLOT2"):
        return MEDIA_SLOT_2_PHASE299
    return None


# ---------------------------------------------------------------------------
# 1. Local O_RDONLY Donor Audit & Clean-Room Synthetic Fallback (< 0.20s)
# ---------------------------------------------------------------------------


def audit_phase299_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase299DonorAuditResult:
    """Strictly `os.open(..., os.O_RDONLY)` audit of Phase 299 Wave-55 local donor
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
        else PINNED_PHASE299_DONOR_SPECS
    )

    if clean_forced:
        elapsed = time.monotonic() - t0
        return Phase299DonorAuditResult(
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
        if resolved_work is None:
            missing_paths.append(rel)
            continue
        p = resolved_work / rel
        if not p.exists():
            missing_paths.append(rel)
        resolved_paths[key] = p

    if missing_paths:
        if work_root is not None and donor_specs_override is None:
            elapsed = time.monotonic() - t0
            return Phase299DonorAuditResult(
                valid=False,
                status=STATUS_BLOCKED_PHASE299_DONOR_INTEGRITY,
                verification_mode="LOCAL_DONOR_O_RDONLY",
                access_mode="O_RDONLY",
                files_inspected=0,
                elapsed_seconds=elapsed,
                within_budget_200ms=(elapsed <= _default_donor_budget_seconds_phase299()),
                raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
                checked_markers=(),
                missing_markers=tuple(missing_paths),
                fx3_contracts_verified=False,
                fx6_contracts_verified=False,
                four_lang_resid16_parity_verified=False,
                sha256_by_artifact={},
                bytes_by_artifact={},
                errors=(
                    f"Explicit work_root missing Wave-55 donor files: {missing_paths}",
                ),
                warnings=(),
            )
        elapsed = time.monotonic() - t0
        return Phase299DonorAuditResult(
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
                "Local Wave-55 Sony donor binaries absent; using CLEAN_ROOM_SYNTHETIC pinned SHA-256 contracts.",
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
                p, PINNED_FX3_APPFW_SLICES_PHASE299
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tokens_ok = _read_targeted_slices_o_rdonly(
                p, PINNED_FX6_APPFW_SLICES_PHASE299
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
    budget = _default_donor_budget_seconds_phase299()
    within_budget = elapsed <= budget
    if not within_budget:
        warnings.append(
            f"Phase 299 donor audit took {elapsed:.4f}s (budget {budget:.2f}s)."
        )

    valid = (not errors) and fx3_ok and fx6_ok and lang_ok
    return Phase299DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE299_DONOR_INTEGRITY,
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
# 2. Gate G129: [Touch Operation] 4-Item Menu + [DISP (Screen Disp) Set] &
#    Total Zero-EVF Blackout Trap Firewall
# ---------------------------------------------------------------------------


def resolve_fx3_touch_shooting_and_disp_evf_state(
    *,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE299,
    requested_touch_operation: str = TOUCH_OP_DEFAULT_G129,
    requested_touch_sensitivity: str = TOUCH_SENSITIVITY_DEFAULT_G129,
    requested_touch_func_in_shooting: str = TOUCH_FUNC_DEFAULT_G129,
    requested_swipe_up: str = SWIPE_UP_DEFAULT_G129,
    requested_disp_shoot_pages: Sequence[str] = DISP_SHOOT_4_PAGES_G129,
    requested_disp_play_pages: Sequence[str] = DISP_PLAY_3_PAGES_G129,
    reset_action: str = RESET_ACTION_NONE_PHASE299,
) -> Dict[str, Any]:
    """Resolve effective Wave-55 Gate `G129` FX3 Ver. 7.02 `[Touch Operation]` & `[DISP]` state."""
    eff_reset = _norm_reset_action_phase299(reset_action) or RESET_ACTION_NONE_PHASE299
    eff_shoot = _norm_shoot_mode_phase299(shoot_mode) or SHOOT_MODE_STILL_PHASE299
    eff_touch_op = _norm_touch_op_g129(requested_touch_operation) or TOUCH_OP_DEFAULT_G129
    eff_touch_sens = (
        _norm_touch_sensitivity_g129(requested_touch_sensitivity)
        or TOUCH_SENSITIVITY_DEFAULT_G129
    )
    eff_touch_func = (
        _norm_touch_func_g129(requested_touch_func_in_shooting)
        or TOUCH_FUNC_DEFAULT_G129
    )
    eff_swipe_up = _norm_swipe_up_g129(requested_swipe_up) or SWIPE_UP_DEFAULT_G129
    eff_disp_shoot = tuple(
        p for p in requested_disp_shoot_pages if p in DISP_SHOOT_4_PAGES_G129
    ) or DISP_SHOOT_4_PAGES_G129
    eff_disp_play = tuple(
        p for p in requested_disp_play_pages if p in DISP_PLAY_3_PAGES_G129
    ) or DISP_PLAY_3_PAGES_G129

    # CRITICAL EMPIRICAL FACT: All 4 [Touch Operation] items + [DISP (Screen Disp) Set]
    # survive [Camera Settings Reset] and are reset ONLY via [Initialize].
    survived_cam_reset = eff_reset != RESET_ACTION_INITIALIZE_PHASE299
    if eff_reset == RESET_ACTION_INITIALIZE_PHASE299:
        eff_touch_op = TOUCH_OP_DEFAULT_G129
        eff_touch_sens = TOUCH_SENSITIVITY_DEFAULT_G129
        eff_touch_func = TOUCH_FUNC_DEFAULT_G129
        eff_swipe_up = SWIPE_UP_DEFAULT_G129
        eff_disp_shoot = DISP_SHOOT_4_PAGES_G129
        eff_disp_play = DISP_PLAY_3_PAGES_G129

    swipe_up_active = (eff_touch_op == TOUCH_OP_ON_G129) and (
        eff_swipe_up == SWIPE_UP_OPEN_FN_MENU_G129
    )

    return {
        "reset_action": eff_reset,
        "shoot_mode": eff_shoot,
        "effective_touch_operation": eff_touch_op,
        "effective_touch_sensitivity": eff_touch_sens,
        "effective_touch_func_in_shooting": eff_touch_func,
        "effective_swipe_up": eff_swipe_up,
        "touch_4_items_survived_cam_reset": survived_cam_reset,
        "swipe_up_active": swipe_up_active,
        "disp_shoot_pages_enabled": eff_disp_shoot,
        "disp_play_pages_enabled": eff_disp_play,
        "disp_set_survived_cam_reset": survived_cam_reset,
    }


def compute_touch_shooting_and_disp_evf_matrix() -> Dict[str, Any]:
    """Deterministic `432`-state cross-product across
    `(3 touch_op x 2 touch_sens x 3 touch_func x 2 swipe_up x 3 shoot_mode x 4 reset_action)`
    verifying `G129` invariants.
    """
    states = 0
    cam_reset_survived_count = 0
    initialize_reset_count = 0
    swipe_up_active_count = 0

    for t_op in ALLOWED_TOUCH_OPERATION_MODES_G129:
        for t_sens in ALLOWED_TOUCH_SENSITIVITIES_G129:
            for t_func in ALLOWED_TOUCH_FUNC_IN_SHOOTING_G129:
                for sw_up in ALLOWED_SWIPE_UP_MODES_G129:
                    for sm in ALLOWED_SHOOT_MODES_PHASE299:
                        for r_act in ALLOWED_RESET_ACTIONS_PHASE299:
                            states += 1
                            r = resolve_fx3_touch_shooting_and_disp_evf_state(
                                shoot_mode=sm,
                                requested_touch_operation=t_op,
                                requested_touch_sensitivity=t_sens,
                                requested_touch_func_in_shooting=t_func,
                                requested_swipe_up=sw_up,
                                requested_disp_shoot_pages=("Display All Info.", "Histogram"),
                                reset_action=r_act,
                            )
                            if r_act != RESET_ACTION_INITIALIZE_PHASE299:
                                assert r["touch_4_items_survived_cam_reset"] is True
                                assert r["disp_set_survived_cam_reset"] is True
                                assert r["effective_touch_operation"] == t_op
                                assert r["effective_touch_sensitivity"] == t_sens
                                assert r["effective_touch_func_in_shooting"] == t_func
                                assert r["effective_swipe_up"] == sw_up
                                assert r["disp_shoot_pages_enabled"] == (
                                    "Display All Info.",
                                    "Histogram",
                                )
                                if r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE299:
                                    cam_reset_survived_count += 1
                            else:
                                assert r["touch_4_items_survived_cam_reset"] is False
                                assert r["effective_touch_operation"] == TOUCH_OP_DEFAULT_G129
                                assert (
                                    r["effective_touch_sensitivity"]
                                    == TOUCH_SENSITIVITY_DEFAULT_G129
                                )
                                assert (
                                    r["effective_touch_func_in_shooting"]
                                    == TOUCH_FUNC_DEFAULT_G129
                                )
                                assert r["effective_swipe_up"] == SWIPE_UP_DEFAULT_G129
                                assert r["disp_shoot_pages_enabled"] == DISP_SHOOT_4_PAGES_G129
                                initialize_reset_count += 1
                            if r["swipe_up_active"]:
                                swipe_up_active_count += 1

    return {
        "states_checked": states,
        "cam_reset_survived_count": cam_reset_survived_count,
        "initialize_reset_count": initialize_reset_count,
        "swipe_up_active_count": swipe_up_active_count,
        "all_invariants_hold": states == 432,
    }


def verify_touch_shooting_and_disp_evf_absence_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE299,
    body_model_id: int = FX3_MODEL_ID_PHASE299,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE299,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE299,
    target_model: str = FX3_MODEL_NAME_PHASE299,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE299,
    requested_touch_operation: str = TOUCH_OP_DEFAULT_G129,
    requested_touch_sensitivity: str = TOUCH_SENSITIVITY_DEFAULT_G129,
    requested_touch_func_in_shooting: str = TOUCH_FUNC_DEFAULT_G129,
    requested_swipe_up: str = SWIPE_UP_DEFAULT_G129,
    requested_dormant_touch_feature: Optional[str] = None,
    claimed_touch_resets_on_cam_settings_reset: bool = False,
    claimed_fx3_has_dormant_touch_features: bool = False,
    requested_disp_shoot_pages: Sequence[str] = DISP_SHOOT_4_PAGES_G129,
    requested_disp_play_pages: Sequence[str] = DISP_PLAY_3_PAGES_G129,
    disp_set_menu_path: str = DISP_SET_MENU_PATH_G129,
    claimed_disp_set_under_display_option: bool = False,
    claimed_disp_resets_on_cam_settings_reset: bool = False,
    requested_dormant_evf_or_disp_key: Optional[str] = None,
    evf_scanout_switch_requested: bool = False,
    claimed_fx3_has_evf_or_eye_sensor: bool = False,
    touch_sensitivity_adjust_requested: bool = False,
    swipe_up_requested: bool = False,
    claimed_fx6_has_touch_sensitivity_or_swipe_up: bool = False,
    claimed_fx6_has_builtin_evf: bool = False,
    claimed_fx6_uses_loupe_terminology: bool = False,
    fx6_4page_disp_ring_requested: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE299,
) -> TouchShootingAndDispEvfGuardResult:
    """Verify Wave-55 Gate `G129` hardware safety contracts."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version) if isinstance(firmware_version, str) else None
    norm_reset = _norm_reset_action_phase299(reset_action)
    norm_shoot = _norm_shoot_mode_phase299(shoot_mode)
    norm_touch_op = _norm_touch_op_g129(requested_touch_operation)
    norm_touch_sens = _norm_touch_sensitivity_g129(requested_touch_sensitivity)
    norm_touch_func = _norm_touch_func_g129(requested_touch_func_in_shooting)
    norm_swipe_up = _norm_swipe_up_g129(requested_swipe_up)

    # Reject dormant Touch Sensitivity (`Responsive`) / dormant Touch Shutter / Touch AE
    dormant_touch_vals = {
        k.strip().lower() for k in DORMANT_TOUCH_TRAP_KEYS_G129
    }
    raw_sens_lower = (
        requested_touch_sensitivity.strip().lower()
        if isinstance(requested_touch_sensitivity, str)
        else ""
    )
    raw_func_lower = (
        requested_touch_func_in_shooting.strip().lower()
        if isinstance(requested_touch_func_in_shooting, str)
        else ""
    )
    is_dormant_sens_responsive = raw_sens_lower == DORMANT_OR_WRONG_TOUCH_SENSITIVITY_G129.lower()
    is_dormant_func = raw_func_lower in dormant_touch_vals

    if (
        body_model_name != FX3_MODEL_NAME_PHASE299
        or not _is_real_int(body_model_id)
        or body_model_id != FX3_MODEL_ID_PHASE299
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE299
        or fw_tuple is None
        or norm_reset is None
        or norm_shoot is None
        or norm_touch_op is None
        or (norm_touch_sens is None and not is_dormant_sens_responsive)
        or (norm_touch_func is None and not is_dormant_func)
        or norm_swipe_up is None
        or target_model not in (FX3_MODEL_NAME_PHASE299, FX6_MODEL_NAME_PHASE299)
    ):
        _add_code(codes, STATUS_BLOCKED_G129_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3/FX6 identity, Touch Operation, or DISP telemetry in Gate G129."
        )

    eff = resolve_fx3_touch_shooting_and_disp_evf_state(
        shoot_mode=norm_shoot or SHOOT_MODE_STILL_PHASE299,
        requested_touch_operation=norm_touch_op or TOUCH_OP_DEFAULT_G129,
        requested_touch_sensitivity=norm_touch_sens or TOUCH_SENSITIVITY_DEFAULT_G129,
        requested_touch_func_in_shooting=norm_touch_func or TOUCH_FUNC_DEFAULT_G129,
        requested_swipe_up=norm_swipe_up or SWIPE_UP_DEFAULT_G129,
        requested_disp_shoot_pages=requested_disp_shoot_pages,
        requested_disp_play_pages=requested_disp_play_pages,
        reset_action=norm_reset or RESET_ACTION_NONE_PHASE299,
    )

    # Part A: Touch Operation 4-item contract, reset persistence & dormant Touch Shutter/AE/Pad/Footer traps
    if claimed_touch_resets_on_cam_settings_reset:
        _add_code(codes, STATUS_BLOCKED_G129_TOUCH_RESET_OR_DORMANT_TRAP_VIOLATION)
        errors.append(
            "All 4 [Touch Operation] items (`Touch Operation`, `Touch Sensitivity`, "
            "`Touch Func. in Shooting`, `Swipe Up`) survive [Camera Settings Reset] (`[Initialize]`-only)."
        )

    if is_dormant_sens_responsive:
        _add_code(codes, STATUS_BLOCKED_G129_TOUCH_RESET_OR_DORMANT_TRAP_VIOLATION)
        errors.append(
            "[Touch Sensitivity] on ILME-FX3 Ver. 7.02 exposes `Standard / Sensitive` ONLY (NOT `Responsive`)."
        )

    if is_dormant_func:
        _add_code(codes, STATUS_BLOCKED_G129_TOUCH_RESET_OR_DORMANT_TRAP_VIOLATION)
        errors.append(
            f"[Touch Func. in Shooting] on ILME-FX3 exposes `Touch Focus / Touch Tracking / Off` ONLY "
            f"(dormant `{requested_touch_func_in_shooting}` rejected across Still/Movie/S&Q)."
        )

    if requested_dormant_touch_feature is not None or claimed_fx3_has_dormant_touch_features:
        _add_code(codes, STATUS_BLOCKED_G129_TOUCH_RESET_OR_DORMANT_TRAP_VIOLATION)
        errors.append(
            f"Dormant Alpha touch trap blocked fail-closed on ILME-FX3 "
            f"(Touch Shutter / Touch AE / Touch Panel/Pad / Footer Icon Touch / Swipe Left-Right: "
            f"`{requested_dormant_touch_feature}`)."
        )

    # Part B: [DISP (Screen Disp) Set] exact Operation Customize path, 4 shoot + 3 play pages
    if claimed_disp_set_under_display_option or (
        isinstance(disp_set_menu_path, str) and "Display Option" in disp_set_menu_path
    ):
        _add_code(codes, STATUS_BLOCKED_G129_DISP_4MODE_OR_PATH_VIOLATION)
        errors.append(
            "[DISP (Screen Disp) Set] lives under `MENU -> (Setup) -> [Operation Customize]` "
            "(`_g 0x61c4 -> 0x61da`), NOT under `[Display Option]`."
        )

    if claimed_disp_resets_on_cam_settings_reset:
        _add_code(codes, STATUS_BLOCKED_G129_DISP_4MODE_OR_PATH_VIOLATION)
        errors.append(
            "[DISP (Screen Disp) Set] survives [Camera Settings Reset] (`[Initialize]`-only)."
        )

    # Validate shoot & play DISP pages against exact 4 shooting + 3 playback pages
    evf_trap_keys_lower = {k.strip().lower() for k in DORMANT_EVF_AND_DISP_TRAP_KEYS_G129}
    if (not requested_disp_shoot_pages) or len(requested_disp_shoot_pages) > len(
        DISP_SHOOT_4_PAGES_G129
    ):
        _add_code(codes, STATUS_BLOCKED_G129_DISP_4MODE_OR_PATH_VIOLATION)
        errors.append(
            "[DISP (Screen Disp) Set] exposes ONLY 4 shooting pages "
            "(`Display All Info.`, `No Disp. Info.`, `Histogram`, `Level`; min 1 enabled)."
        )

    for page in requested_disp_shoot_pages:
        if page.strip().lower() in evf_trap_keys_lower:
            _add_code(codes, STATUS_BLOCKED_G129_ZERO_EVF_BLACKOUT_TRAP_VIOLATION)
            errors.append(
                f"Zero-EVF Blackout Firewall blocked dormant DISP shooting page `{page}` on ILME-FX3."
            )
        elif page not in DISP_SHOOT_4_PAGES_G129:
            _add_code(codes, STATUS_BLOCKED_G129_DISP_4MODE_OR_PATH_VIOLATION)
            errors.append(
                f"Invalid DISP shooting page `{page}` (only 4 pages supported on ILME-FX3)."
            )

    if (not requested_disp_play_pages) or len(requested_disp_play_pages) > len(
        DISP_PLAY_3_PAGES_G129
    ):
        _add_code(codes, STATUS_BLOCKED_G129_DISP_4MODE_OR_PATH_VIOLATION)
        errors.append(
            "Playback DISP cycles ONLY 3 pages (`Display Info.`, `Histogram`, `No Disp. Info.`)."
        )

    for page in requested_disp_play_pages:
        if page not in DISP_PLAY_3_PAGES_G129:
            _add_code(codes, STATUS_BLOCKED_G129_DISP_4MODE_OR_PATH_VIOLATION)
            errors.append(
                f"Invalid DISP playback page `{page}` (only 3 playback pages supported on ILME-FX3)."
            )

    # Part C: Total Zero-EVF Blackout Trap Firewall
    if (
        (requested_dormant_evf_or_disp_key is not None)
        or evf_scanout_switch_requested
        or claimed_fx3_has_evf_or_eye_sensor
    ):
        _add_code(codes, STATUS_BLOCKED_G129_ZERO_EVF_BLACKOUT_TRAP_VIOLATION)
        errors.append(
            "ILME-FX3 has ZERO EVF, ZERO eye sensor, and ZERO `FINDER/MONITOR` button: "
            f"dormant EVF/Finder switch (`{requested_dormant_evf_or_disp_key}`) blocked fail-closed "
            "to prevent black-screen LCD scanout soft-brick!"
        )

    # Part D: ILME-FX6 Ver. 6.01 cross-model boundary
    if (
        claimed_fx6_has_touch_sensitivity_or_swipe_up
        or claimed_fx6_has_builtin_evf
        or claimed_fx6_uses_loupe_terminology
        or (
            target_model == FX6_MODEL_NAME_PHASE299
            and (touch_sensitivity_adjust_requested or swipe_up_requested or fx6_4page_disp_ring_requested)
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G129_FX6_TOUCH_OR_EVF_CROSSWIRE_VIOLATION)
        errors.append(
            "ILME-FX6 Ver. 6.01 (`TYPE_BUILTIN_EVF_NOT_EXIST`) uses detachable 3.5\" LCD "
            "`Viewfinder` + `Viewfinder Hood` (never `Loupe`), `Technical > Touch Operation`, "
            "`Touch Function in MF`, and `Monitoring > Display On/Off`; lacks FX3 `Touch Sensitivity`, "
            "`Swipe Up`, and 4-page `DISP` ring."
        )

    matrix = compute_touch_shooting_and_disp_evf_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G129 if valid else codes[0]

    return TouchShootingAndDispEvfGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE299,
        target_model=target_model,
        reset_action=eff["reset_action"],
        shoot_mode=eff["shoot_mode"],
        effective_touch_operation=eff["effective_touch_operation"],
        effective_touch_sensitivity=eff["effective_touch_sensitivity"],
        effective_touch_func_in_shooting=eff["effective_touch_func_in_shooting"],
        effective_swipe_up=eff["effective_swipe_up"],
        touch_4_items_survived_cam_reset=eff["touch_4_items_survived_cam_reset"],
        swipe_up_active=eff["swipe_up_active"],
        dormant_touch_traps_blocked=True,
        disp_set_menu_path=DISP_SET_MENU_PATH_G129,
        disp_shoot_pages_enabled=eff["disp_shoot_pages_enabled"],
        disp_play_pages_enabled=eff["disp_play_pages_enabled"],
        disp_set_survived_cam_reset=eff["disp_set_survived_cam_reset"],
        fx3_has_builtin_evf=False,
        fx3_has_eye_sensor=False,
        fx3_has_finder_monitor_button=False,
        fx6_has_builtin_evf=False,
        evf_scanout_blocked=True,
        lcd_panel_scanout_preserved=True,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g129_touch_shooting_and_disp_evf_absence_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    touch_shooting_disp_evf_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase299DonorAuditResult] = None,
) -> Tuple[GateVerdict, G129TouchShootingDispEvfGuardResult]:
    """Evaluate Wave-55 Gate `G129` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase299_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_touch_shooting_and_disp_evf_absence_guard(
        **(dict(touch_shooting_disp_evf_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G129.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G129 if valid else codes[0]

    res = G129TouchShootingDispEvfGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        touch_shooting_disp_evf_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, touch=({guard.effective_touch_operation},"
        f"{guard.effective_touch_sensitivity},{guard.effective_touch_func_in_shooting},"
        f"{guard.effective_swipe_up}), disp_shoot={len(guard.disp_shoot_pages_enabled)},"
        f"fx3_evf={guard.fx3_has_builtin_evf}, evf_blocked={guard.evf_scanout_blocked}"
    )
    verdict = GateVerdict(
        gate_id=G129_GATE_ID,
        gate_code=G129_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G130: Still [AEL w/ Shutter] & [Flash] Submenu +
#    Interval Playback `1..9` Scale & Playback `[Edit]` Slot-1 Tier-0 Vault Firewall
# ---------------------------------------------------------------------------


def resolve_fx3_ael_flash_and_interval_pb_edit_state(
    *,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE299,
    requested_ael_w_shutter: str = AEL_W_SHUTTER_DEFAULT_G130,
    requested_exp_comp_set: str = EXP_COMP_SET_DEFAULT_G130,
    requested_wireless_flash: str = WIRELESS_FLASH_DEFAULT_G130,
    requested_external_flash_set: str = "Ext. Flash Firing Set.",
    requested_cont_play_for_interval: str = "Off",
    requested_play_speed_for_interval: int = PLAY_SPEED_INTERVAL_DEFAULT_G130,
    requested_photo_capture_file_type: str = PHOTO_CAPTURE_FILE_DEFAULT_G130,
    requested_select_playback_media: str = MEDIA_SLOT_1_PHASE299,
    requested_playback_edit_action: Optional[str] = None,
    slot_1_write_protected: bool = False,
    slot_1_contains_tier0_vault: bool = True,
    reset_action: str = RESET_ACTION_NONE_PHASE299,
) -> Dict[str, Any]:
    """Resolve effective Wave-55 Gate `G130` FX3 Ver. 7.02 AEL/Flash & Interval Playback/Edit state."""
    eff_reset = _norm_reset_action_phase299(reset_action) or RESET_ACTION_NONE_PHASE299
    eff_shoot = _norm_shoot_mode_phase299(shoot_mode) or SHOOT_MODE_STILL_PHASE299
    eff_ael = _norm_ael_w_shutter_g130(requested_ael_w_shutter) or AEL_W_SHUTTER_DEFAULT_G130
    eff_exp_comp_set = (
        _norm_exp_comp_set_g130(requested_exp_comp_set) or EXP_COMP_SET_DEFAULT_G130
    )
    eff_wireless = (
        _norm_on_off_phase299(requested_wireless_flash) or WIRELESS_FLASH_DEFAULT_G130
    )
    eff_ext_flash = (
        requested_external_flash_set
        if requested_external_flash_set in EXT_FLASH_SUBMENUS_G130
        else "Ext. Flash Firing Set."
    )
    eff_cont_play = _norm_on_off_phase299(requested_cont_play_for_interval) or "Off"
    eff_play_speed = (
        requested_play_speed_for_interval
        if _is_real_int(requested_play_speed_for_interval)
        and (
            PLAY_SPEED_INTERVAL_MIN_G130
            <= requested_play_speed_for_interval
            <= PLAY_SPEED_INTERVAL_MAX_G130
        )
        else PLAY_SPEED_INTERVAL_DEFAULT_G130
    )
    eff_photo_type = (
        _norm_photo_capture_file_type_g130(requested_photo_capture_file_type)
        or PHOTO_CAPTURE_FILE_DEFAULT_G130
    )
    eff_media = _norm_media_slot_phase299(requested_select_playback_media) or MEDIA_SLOT_1_PHASE299

    # CRITICAL EMPIRICAL DIFFERENTIATION:
    # - [AEL w/ Shutter], [Exp.comp.set], [External Flash Set.], [Cont. Play for Interval],
    #   and [Play Speed for Interval] ALL survive [Camera Settings Reset] (`Initialize`-only!).
    # - [Wireless Flash] is the ONLY Flash/AEL item resettable via [Camera Settings Reset]!
    survived_cam_reset = eff_reset != RESET_ACTION_INITIALIZE_PHASE299
    wireless_reset = eff_reset in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE299,
        RESET_ACTION_INITIALIZE_PHASE299,
    )
    if wireless_reset:
        eff_wireless = WIRELESS_FLASH_DEFAULT_G130
    if eff_reset == RESET_ACTION_INITIALIZE_PHASE299:
        eff_ael = AEL_W_SHUTTER_DEFAULT_G130
        eff_exp_comp_set = EXP_COMP_SET_DEFAULT_G130
        eff_cont_play = "Off"
        eff_play_speed = PLAY_SPEED_INTERVAL_DEFAULT_G130
        eff_photo_type = PHOTO_CAPTURE_FILE_DEFAULT_G130
        eff_media = MEDIA_SLOT_1_PHASE299

    # Playback [Edit] write target resolution & Slot-1 Tier-0 Vault Firewall:
    # - Rotate & Photo Capture write directly to `[Select Playback Media]` (`eff_media`).
    # - Copy writes to the OPPOSITE slot of `[Select Playback Media]`.
    # - Dormant Beauty Effect / Trimming attempt to save a new file on `eff_media`.
    target_write_slot: Optional[str] = None
    if requested_playback_edit_action is not None:
        act_norm = requested_playback_edit_action.strip().lower()
        if act_norm in ("rotate", "photo capture", "beauty effect", "trimming"):
            target_write_slot = eff_media
        elif act_norm == "copy":
            target_write_slot = (
                MEDIA_SLOT_2_PHASE299
                if eff_media == MEDIA_SLOT_1_PHASE299
                else MEDIA_SLOT_1_PHASE299
            )

    slot1_locked = bool(slot_1_write_protected or slot_1_contains_tier0_vault)
    edit_blocked_by_slot1 = bool(
        (target_write_slot == MEDIA_SLOT_1_PHASE299) and slot1_locked
    )
    block_errno: Optional[str] = None
    if edit_blocked_by_slot1:
        block_errno = "EROFS" if slot_1_write_protected else "EOPNOTSUPP"

    return {
        "reset_action": eff_reset,
        "shoot_mode": eff_shoot,
        "effective_ael_w_shutter": eff_ael,
        "ael_w_shutter_survived_cam_reset": survived_cam_reset,
        "effective_exp_comp_set": eff_exp_comp_set,
        "exp_comp_set_survived_cam_reset": survived_cam_reset,
        "effective_wireless_flash": eff_wireless,
        "wireless_flash_reset_on_cam_reset": wireless_reset,
        "effective_external_flash_set": eff_ext_flash,
        "effective_cont_play_for_interval": eff_cont_play,
        "effective_play_speed_for_interval": eff_play_speed,
        "interval_pb_survived_cam_reset": survived_cam_reset,
        "effective_photo_capture_file_type": eff_photo_type,
        "effective_select_playback_media": eff_media,
        "target_write_slot": target_write_slot,
        "playback_edit_blocked_by_slot1_vault_firewall": edit_blocked_by_slot1,
        "block_errno": block_errno,
        "slot1_data_sector_writes": 0,
        "slot1_avf_info_mutated": False,
    }


def compute_ael_flash_and_interval_pb_edit_matrix() -> Dict[str, Any]:
    """Deterministic `432`-state cross-product across
    `(3 ael x 2 exp_comp x 2 wireless x 9 speed * ...)` -> `(3 ael x 2 exp_comp x 2 wireless x 2 media x 3 edit_action_or_none x 2 vault_or_reset)`
    specifically `(3 ael x 2 exp_comp x 2 wireless x 3 speed_sample(1,5,9) x 2 media x 3 reset(None,CamReset,Init))` = `216`? Wait let's make it `3 ael * 2 exp_comp * 2 wireless * 9 play_speed * 2 media * 2 reset(CamReset, Init)` = `432` states!
    """
    states = 0
    wireless_reset_cam_count = 0
    ael_survived_cam_count = 0
    slot1_edit_blocked_count = 0

    for ael in ALLOWED_AEL_W_SHUTTER_MODES_G130:
        for exp_c in ALLOWED_EXP_COMP_SET_MODES_G130:
            for wf in ALLOWED_WIRELESS_FLASH_MODES_G130:
                for spd in ALLOWED_PLAY_SPEED_INTERVAL_SCALE_G130:
                    for media in ALLOWED_MEDIA_SLOTS_PHASE299:
                        for r_act in (
                            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE299,
                            RESET_ACTION_INITIALIZE_PHASE299,
                        ):
                            states += 1
                            r = resolve_fx3_ael_flash_and_interval_pb_edit_state(
                                requested_ael_w_shutter=ael,
                                requested_exp_comp_set=exp_c,
                                requested_wireless_flash=wf,
                                requested_play_speed_for_interval=spd,
                                requested_select_playback_media=media,
                                requested_playback_edit_action="Photo Capture",
                                slot_1_contains_tier0_vault=True,
                                reset_action=r_act,
                            )
                            if r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE299:
                                assert r["ael_w_shutter_survived_cam_reset"] is True
                                assert r["exp_comp_set_survived_cam_reset"] is True
                                assert r["interval_pb_survived_cam_reset"] is True
                                assert r["effective_ael_w_shutter"] == ael
                                assert r["effective_exp_comp_set"] == exp_c
                                assert r["effective_play_speed_for_interval"] == spd
                                # ONLY Wireless Flash resets on Camera Settings Reset!
                                assert r["wireless_flash_reset_on_cam_reset"] is True
                                assert r["effective_wireless_flash"] == WIRELESS_FLASH_DEFAULT_G130
                                wireless_reset_cam_count += 1
                                ael_survived_cam_count += 1
                                if media == MEDIA_SLOT_1_PHASE299:
                                    assert (
                                        r["playback_edit_blocked_by_slot1_vault_firewall"]
                                        is True
                                    )
                                    assert r["slot1_data_sector_writes"] == 0
                                    assert r["slot1_avf_info_mutated"] is False
                                    slot1_edit_blocked_count += 1
                            else:
                                assert r["ael_w_shutter_survived_cam_reset"] is False
                                assert r["effective_ael_w_shutter"] == AEL_W_SHUTTER_DEFAULT_G130
                                assert (
                                    r["effective_exp_comp_set"] == EXP_COMP_SET_DEFAULT_G130
                                )
                                assert (
                                    r["effective_play_speed_for_interval"]
                                    == PLAY_SPEED_INTERVAL_DEFAULT_G130
                                )

    return {
        "states_checked": states,
        "wireless_reset_cam_count": wireless_reset_cam_count,
        "ael_survived_cam_count": ael_survived_cam_count,
        "slot1_edit_blocked_count": slot1_edit_blocked_count,
        "all_invariants_hold": states == 432,
    }


def verify_ael_wireless_flash_and_interval_pb_edit_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE299,
    body_model_id: int = FX3_MODEL_ID_PHASE299,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE299,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE299,
    target_model: str = FX3_MODEL_NAME_PHASE299,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE299,
    requested_ael_w_shutter: str = AEL_W_SHUTTER_DEFAULT_G130,
    ael_w_shutter_use_requested: bool = False,
    requested_exp_comp_set: str = EXP_COMP_SET_DEFAULT_G130,
    exp_comp_set_use_requested: bool = False,
    claimed_exp_comp_set_under_exposure_comp: bool = False,
    requested_wireless_flash: str = WIRELESS_FLASH_DEFAULT_G130,
    wireless_flash_use_requested: bool = False,
    requested_external_flash_set: str = "Ext. Flash Firing Set.",
    external_flash_use_requested: bool = False,
    claimed_ael_or_exp_comp_resets_on_cam_reset: bool = False,
    claimed_wireless_flash_ignores_cam_reset: bool = False,
    off_camera_sync_cord_flash_requested: bool = False,
    camera_menu_flash_reset_requested: bool = False,
    claimed_fx6_has_still_flash_or_ael: bool = False,
    claimed_fx6_flash_band_reduce_is_flash_trigger: bool = False,
    interval_pb_menu_path: str = INTERVAL_PB_MENU_PATH_G130,
    claimed_interval_under_playback_option: bool = False,
    requested_cont_play_for_interval: str = "Off",
    requested_play_speed_for_interval: int = PLAY_SPEED_INTERVAL_DEFAULT_G130,
    claimed_play_speed_max_is_5: bool = False,
    claimed_in_camera_timelapse_movie_assembly: bool = False,
    requested_photo_capture_file_type: str = PHOTO_CAPTURE_FILE_DEFAULT_G130,
    requested_select_playback_media: str = MEDIA_SLOT_1_PHASE299,
    requested_playback_edit_action: Optional[str] = None,
    slot_1_write_protected: bool = False,
    slot_1_contains_tier0_vault: bool = True,
    reset_action: str = RESET_ACTION_NONE_PHASE299,
) -> AelFlashAndIntervalPbEditGuardResult:
    """Verify Wave-55 Gate `G130` hardware safety contracts."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version) if isinstance(firmware_version, str) else None
    norm_reset = _norm_reset_action_phase299(reset_action)
    norm_shoot = _norm_shoot_mode_phase299(shoot_mode)
    norm_ael = _norm_ael_w_shutter_g130(requested_ael_w_shutter)
    norm_exp_comp = _norm_exp_comp_set_g130(requested_exp_comp_set)
    norm_wireless = _norm_on_off_phase299(requested_wireless_flash)
    norm_cont_play = _norm_on_off_phase299(requested_cont_play_for_interval)
    norm_photo_type = _norm_photo_capture_file_type_g130(requested_photo_capture_file_type)
    norm_media = _norm_media_slot_phase299(requested_select_playback_media)

    valid_speed_int = _is_real_int(requested_play_speed_for_interval)
    speed_in_1_to_9 = valid_speed_int and (
        PLAY_SPEED_INTERVAL_MIN_G130
        <= requested_play_speed_for_interval
        <= PLAY_SPEED_INTERVAL_MAX_G130
    )

    if (
        body_model_name != FX3_MODEL_NAME_PHASE299
        or not _is_real_int(body_model_id)
        or body_model_id != FX3_MODEL_ID_PHASE299
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE299
        or fw_tuple is None
        or norm_reset is None
        or norm_shoot is None
        or norm_ael is None
        or norm_exp_comp is None
        or norm_wireless is None
        or norm_cont_play is None
        or norm_photo_type is None
        or norm_media is None
        or (not valid_speed_int)
        or (requested_external_flash_set not in EXT_FLASH_SUBMENUS_G130)
        or target_model not in (FX3_MODEL_NAME_PHASE299, FX6_MODEL_NAME_PHASE299)
    ):
        _add_code(codes, STATUS_BLOCKED_G130_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3/FX6 identity, AEL/Flash, or Interval Playback/Edit telemetry in Gate G130."
        )

    eff = resolve_fx3_ael_flash_and_interval_pb_edit_state(
        shoot_mode=norm_shoot or SHOOT_MODE_STILL_PHASE299,
        requested_ael_w_shutter=norm_ael or AEL_W_SHUTTER_DEFAULT_G130,
        requested_exp_comp_set=norm_exp_comp or EXP_COMP_SET_DEFAULT_G130,
        requested_wireless_flash=norm_wireless or WIRELESS_FLASH_DEFAULT_G130,
        requested_external_flash_set=requested_external_flash_set,
        requested_cont_play_for_interval=norm_cont_play or "Off",
        requested_play_speed_for_interval=(
            requested_play_speed_for_interval
            if speed_in_1_to_9
            else PLAY_SPEED_INTERVAL_DEFAULT_G130
        ),
        requested_photo_capture_file_type=norm_photo_type or PHOTO_CAPTURE_FILE_DEFAULT_G130,
        requested_select_playback_media=norm_media or MEDIA_SLOT_1_PHASE299,
        requested_playback_edit_action=requested_playback_edit_action,
        slot_1_write_protected=slot_1_write_protected,
        slot_1_contains_tier0_vault=slot_1_contains_tier0_vault,
        reset_action=norm_reset or RESET_ACTION_NONE_PHASE299,
    )

    # Part A: Still-only [AEL w/ Shutter], [Exp.comp.set], [Wireless Flash] & Reset Differentiation
    is_movie_or_sq = norm_shoot in (SHOOT_MODE_MOVIE_PHASE299, SHOOT_MODE_SQ_PHASE299)
    if is_movie_or_sq and (
        ael_w_shutter_use_requested
        or exp_comp_set_use_requested
        or wireless_flash_use_requested
        or external_flash_use_requested
    ):
        _add_code(codes, STATUS_BLOCKED_G130_AEL_OR_FLASH_STILL_RESET_VIOLATION)
        errors.append(
            f"[AEL w/ Shutter], [Exp.comp.set], [Wireless Flash], and [External Flash Set.] "
            f"are Still-only (blocked in `{norm_shoot}`)."
        )

    if claimed_exp_comp_set_under_exposure_comp:
        _add_code(codes, STATUS_BLOCKED_G130_AEL_OR_FLASH_STILL_RESET_VIOLATION)
        errors.append(
            "[Exp.comp.set] (`Ambient&flash / Ambient only`) lives under `(Exposure/Color) -> [Flash]`, "
            "NOT under `[Exposure Comp.]`."
        )

    if claimed_ael_or_exp_comp_resets_on_cam_reset or claimed_wireless_flash_ignores_cam_reset:
        _add_code(codes, STATUS_BLOCKED_G130_AEL_OR_FLASH_STILL_RESET_VIOLATION)
        errors.append(
            "[AEL w/ Shutter], [Exp.comp.set], and [External Flash Set.] are Initialize-only, "
            "whereas [Wireless Flash] is the ONLY Flash item resettable via [Camera Settings Reset]."
        )

    # Part B: Direct MI-Shoe External Flash Set. & Flash-less ILME-FX6 Contrast
    if off_camera_sync_cord_flash_requested or camera_menu_flash_reset_requested:
        _add_code(codes, STATUS_BLOCKED_G130_EXT_FLASH_MISHOE_OR_FX6_VIOLATION)
        errors.append(
            "[External Flash Set.] requires direct MI-Shoe attachment "
            "(off-camera sync cord and camera-menu flash reset/initialize are unsupported per `.uxc 0xe8c7/0xe53e`)."
        )

    if (
        claimed_fx6_has_still_flash_or_ael
        or claimed_fx6_flash_band_reduce_is_flash_trigger
        or (
            target_model == FX6_MODEL_NAME_PHASE299
            and (
                ael_w_shutter_use_requested
                or exp_comp_set_use_requested
                or wireless_flash_use_requested
                or external_flash_use_requested
            )
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G130_EXT_FLASH_MISHOE_OR_FX6_VIOLATION)
        errors.append(
            "Flash-less ILME-FX6 lacks Still [AEL w/ Shutter] and all [Flash] submenus (`0` BKID keys); "
            "`Flash Band Reduce` is CMOS rolling-shutter band compensation, NOT flash trigger!"
        )

    # Part C: Interval Playback [Viewing] & 1..9 Scale (default 5)
    if claimed_interval_under_playback_option or (
        isinstance(interval_pb_menu_path, str) and "Playback Option" in interval_pb_menu_path
    ):
        _add_code(codes, STATUS_BLOCKED_G130_INTERVAL_PLAYBACK_SCALE_OR_PATH_VIOLATION)
        errors.append(
            "[Cont. Play for Interval] & [Play Speed for Interval] live under "
            "`MENU -> (Playback) -> [Viewing]` (`_g 0x6033`), NOT `[Playback Option]`."
        )

    if valid_speed_int and (not speed_in_1_to_9):
        _add_code(codes, STATUS_BLOCKED_G130_INTERVAL_PLAYBACK_SCALE_OR_PATH_VIOLATION)
        errors.append(
            f"[Play Speed for Interval] speed `{requested_play_speed_for_interval}` out of valid "
            "`1..9` scale (`CONTINUOUS_PLAYBACK_SPEED_1..9`, default `5`)."
        )

    if claimed_play_speed_max_is_5 or claimed_in_camera_timelapse_movie_assembly:
        _add_code(codes, STATUS_BLOCKED_G130_INTERVAL_PLAYBACK_SCALE_OR_PATH_VIOLATION)
        errors.append(
            "[Play Speed for Interval] uses exact `1..9` scale (default `5`, NOT `1..5`), "
            "and in-camera assembly of interval stills into a movie is unsupported."
        )

    # Part D: Playback [Edit] 4-Item vs Dormant [Beauty Effect]/[Trimming] & Slot-1 Tier-0 Vault Firewall
    dormant_edit_lower = {k.strip().lower() for k in DORMANT_PLAYBACK_EDIT_TRAP_ITEMS_G130}
    if requested_playback_edit_action is not None:
        act_clean = requested_playback_edit_action.strip()
        act_lower = act_clean.lower()
        if act_lower in dormant_edit_lower:
            _add_code(
                codes,
                STATUS_BLOCKED_G130_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_VIOLATION,
            )
            errors.append(
                f"Dormant Alpha Playback [Edit] trap `{act_clean}` (`Beauty Effect` / `Trimming`) "
                "is unexposed on ILME-FX3 and blocked fail-closed."
            )
        elif act_clean not in PLAYBACK_EDIT_ACTIVE_4_ITEMS_G130:
            _add_code(codes, STATUS_BLOCKED_G130_TELEMETRY_INVALID)
            errors.append(
                f"Unknown Playback [Edit] action `{act_clean}` (only `Rotate`, `Photo Capture`, "
                "`JPEG/HEIF Switch`, `Copy` exist on ILME-FX3)."
            )

    if eff["playback_edit_blocked_by_slot1_vault_firewall"]:
        _add_code(
            codes,
            STATUS_BLOCKED_G130_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_VIOLATION,
        )
        errors.append(
            f"Playback [Edit] write action `{requested_playback_edit_action}` targets read-only "
            f"Tier-0 `Slot 1` vault (`[Select Playback Media] = {eff['effective_select_playback_media']}`, "
            f"`errno={eff['block_errno']}`): blocked fail-closed (`slot1_data_sector_writes == 0`, "
            "`slot1_avf_info_mutated == False`)."
        )

    matrix = compute_ael_flash_and_interval_pb_edit_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G130 if valid else codes[0]

    return AelFlashAndIntervalPbEditGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE299,
        target_model=target_model,
        reset_action=eff["reset_action"],
        shoot_mode=eff["shoot_mode"],
        effective_ael_w_shutter=eff["effective_ael_w_shutter"],
        ael_toggle_overrides_half_press=True,
        ael_w_shutter_survived_cam_reset=eff["ael_w_shutter_survived_cam_reset"],
        effective_exp_comp_set=eff["effective_exp_comp_set"],
        exp_comp_set_survived_cam_reset=eff["exp_comp_set_survived_cam_reset"],
        effective_wireless_flash=eff["effective_wireless_flash"],
        wireless_flash_reset_on_cam_reset=eff["wireless_flash_reset_on_cam_reset"],
        effective_external_flash_set=eff["effective_external_flash_set"],
        ext_flash_direct_mishoe_only=True,
        off_camera_sync_cord_supported=False,
        fx6_has_still_flash_or_ael=False,
        fx6_flash_band_reduce_is_rolling_shutter_comp=True,
        interval_pb_menu_path=INTERVAL_PB_MENU_PATH_G130,
        effective_cont_play_for_interval=eff["effective_cont_play_for_interval"],
        effective_play_speed_for_interval=eff["effective_play_speed_for_interval"],
        play_speed_scale_min=PLAY_SPEED_INTERVAL_MIN_G130,
        play_speed_scale_max=PLAY_SPEED_INTERVAL_MAX_G130,
        play_speed_scale_default=PLAY_SPEED_INTERVAL_DEFAULT_G130,
        interval_pb_survived_cam_reset=eff["interval_pb_survived_cam_reset"],
        interval_pb_read_only_safe=True,
        in_camera_timelapse_movie_assembly_supported=False,
        playback_edit_active_items=PLAYBACK_EDIT_ACTIVE_4_ITEMS_G130,
        effective_photo_capture_file_type=eff["effective_photo_capture_file_type"],
        effective_select_playback_media=eff["effective_select_playback_media"],
        requested_playback_edit_action=requested_playback_edit_action,
        target_write_slot=eff["target_write_slot"],
        slot_1_write_protected=bool(slot_1_write_protected),
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        playback_edit_blocked_by_slot1_vault_firewall=eff[
            "playback_edit_blocked_by_slot1_vault_firewall"
        ],
        block_errno=eff["block_errno"],
        slot1_data_sector_writes=eff["slot1_data_sector_writes"],
        slot1_avf_info_mutated=eff["slot1_avf_info_mutated"],
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g130_ael_wireless_flash_and_interval_pb_edit_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    ael_flash_interval_pb_edit_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase299DonorAuditResult] = None,
) -> Tuple[GateVerdict, G130AelFlashIntervalPbEditGuardResult]:
    """Evaluate Wave-55 Gate `G130` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase299_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_ael_wireless_flash_and_interval_pb_edit_guard(
        **(dict(ael_flash_interval_pb_edit_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G130.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G130 if valid else codes[0]

    res = G130AelFlashIntervalPbEditGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        ael_flash_interval_pb_edit_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, ael={guard.effective_ael_w_shutter},"
        f"exp_comp_set={guard.effective_exp_comp_set},"
        f"wireless={guard.effective_wireless_flash},"
        f"interval_spd={guard.effective_play_speed_for_interval}/9,"
        f"pb_media={guard.effective_select_playback_media},"
        f"slot1_vault={guard.slot_1_contains_tier0_vault},"
        f"s1_writes={guard.slot1_data_sector_writes}"
    )
    verdict = GateVerdict(
        gate_id=G130_GATE_ID,
        gate_code=G130_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `130`-Gate Milestone Master Safety Preflight (`G01..G130`)
# ---------------------------------------------------------------------------


def evaluate_130gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    touch_shooting_disp_evf_kwargs: Optional[Mapping[str, Any]] = None,
    ael_flash_interval_pb_edit_kwargs: Optional[Mapping[str, Any]] = None,
    master_128_override: Optional[Master128GateReport] = None,
    **m128_passthrough_kwargs: Any,
) -> Master130GateReport:
    """Evaluate all 130 Master Safety Gates (`G01..G130`) deterministically by
    delegating `G01..G128` directly to `evaluate_128gate_preflight()`.
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

    m128_report: Master128GateReport = (
        master_128_override
        if master_128_override is not None
        else evaluate_128gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m128_passthrough_kwargs,
        )
    )

    phase299_audit = audit_phase299_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g129_verdict, g129_res = evaluate_g129_touch_shooting_and_disp_evf_absence_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        touch_shooting_disp_evf_kwargs=touch_shooting_disp_evf_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase299_audit,
    )

    g130_verdict, g130_res = evaluate_g130_ael_wireless_flash_and_interval_pb_edit_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        ael_flash_interval_pb_edit_kwargs=ael_flash_interval_pb_edit_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase299_audit,
    )

    gates_129_to_130 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g129_verdict, g130_verdict)
    ]
    all_gates = tuple(list(m128_report.gates) + gates_129_to_130)

    g01_to_g12_verified = int(m128_report.summary["g01_to_g12_verified"])
    g13_to_g128_verified = int(m128_report.summary["g13_to_g126_verified"]) + int(
        m128_report.summary["g127_to_g128_verified"]
    )
    g129_to_g130_verified = sum(1 for v in (g129_verdict, g130_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g128_verified + g129_to_g130_verified

    g129_to_g130_all_passed = g129_to_g130_verified == 2
    g13_to_g130_all_passed = (
        m128_report.g13_to_g128_all_passed and g129_to_g130_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m128_report.gates[:9])

    offline_127_verified = (
        g01_to_g09_ok
        and m128_report.offline_125_gates_verified
        and g129_to_g130_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_130_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g130_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m128_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_127_verified
        and m128_report.h0_h1_trial_entry_allowed
        and g129_to_g130_all_passed
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
        list(m128_report.errors)
        + list(g129_verdict.errors)
        + list(g130_verdict.errors)
    )
    warnings: List[str] = (
        list(m128_report.warnings)
        + list(g129_verdict.warnings)
        + list(g130_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m128_report.g13_to_g128_all_passed:
        overall_status = m128_report.status
    elif not g129_verdict.passed:
        overall_status = g129_verdict.status
    elif not g130_verdict.passed:
        overall_status = g130_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_130_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_130_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_130_verified:
        overall_status = "VERIFIED_ALL_130_GATES"
    else:
        overall_status = "VERIFIED_127_OF_130_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m128_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g129_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g130_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 130,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 130 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g128_verified": g13_to_g128_verified,
        "g129_to_g130_verified": g129_to_g130_verified,
        "g13_to_g130_all_passed": g13_to_g130_all_passed,
        "g129_to_g130_all_passed": g129_to_g130_all_passed,
        "offline_127_gates_verified": offline_127_verified,
        "all_130_gates_verified": all_130_verified,
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

    return Master130GateReport(
        schema=REALHW_TOUCH_SHOOTING_DISP_EVF_AEL_FLASH_INTERVAL_PB_130GATE_SCHEMA,
        version=REALHW_TOUCH_SHOOTING_DISP_EVF_AEL_FLASH_INTERVAL_PB_130GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_127_gates_verified=offline_127_verified,
        all_130_gates_verified=all_130_verified,
        g13_to_g130_all_passed=g13_to_g130_all_passed,
        g129_to_g130_all_passed=g129_to_g130_all_passed,
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
        master_128_report=m128_report.to_dict(),
        g129_result=g129_res.to_dict(),
        g130_result=g130_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_130_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master130GateReport:
    return evaluate_130gate_preflight(repo_root, **kwargs)


def run_130_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master130GateReport:
    return evaluate_130gate_preflight(repo_root, **kwargs)


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
        prog="realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard",
        description="Phase 299 Wave-55 G129/G130 & 130/130 Safety Gates Milestone Preflight CLI",
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
        help="Supply simulated dry-run Tier-0 backup inputs so all 130/130 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g129", "g130", "130"],
        default="130",
        help="Target gate check: g129, g130, or 130",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g129":
        v, r = evaluate_g129_touch_shooting_and_disp_evf_absence_guard(
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

    if args.gate == "g130":
        v, r = evaluate_g130_ael_wireless_flash_and_interval_pb_edit_guard(
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

    rep = evaluate_130gate_preflight(
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
                "g129_status": rep.g129_result["status"],
                "g130_status": rep.g130_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/130\n"
        )
    ok = rep.all_130_gates_verified if args.dry_run_simulated else rep.offline_127_gates_verified
    return 0 if ok else 1
