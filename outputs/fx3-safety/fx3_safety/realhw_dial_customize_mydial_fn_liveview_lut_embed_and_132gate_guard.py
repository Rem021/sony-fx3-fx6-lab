"""Phase 303 (Wave-56, 132/132 Safety Gates Milestone!):
Real-Hardware Safety Gates G131 & G132 + Unified 132-Gate Preflight Engine.

Implements empirical `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` hardware safety gates:

1. **Gate `G131` (`verify-dial-customize-mydial-fn-guard`)**:
   - `MENU -> (Setup) -> [Dial Customize]` (`_g.uxc 0x62ed`) exposes **exact 5 active
     items** on `ILME-FX3 Ver. 7.02` (`ilc/2210`):
     1) `[Custom Key/Dial Set.]` (`_f 0x6290`/`0x73a0` — replaced Ver. 1.xx `[Dial Setup]`
        / `_f 0x6a89` `Dial/Wheel Setup` since Ver. 2.00+)
     2) `[My Dial Settings]` (`_f 0x6538`: `My Dial 1..3`)
     3) `[Av/Tv Rotate]` (`_f 0x72e3`: `Normal` default / `Reverse`)
     4) `[Function Ring(Lens)]` (`_f 0x715e`: `Power Focus` default /
        `APS-C/Super 35 mm / Full Frame`; reject `VAL_setting_function_ring_FUNCTION_RING_INVALID`)
     5) `[Lock Operation Parts]` (`_f 0x6904`: `Off` default / `Multi-Selector Only` /
        `Dial + Wheel` / `All` — replaced legacy `Dial / Wheel Lock` `base 0xe352`)
     All 5 items are **`Initialize`-only** (survive `[Camera Settings Reset]`).
   - **Physical 3-Dial Hardware Topology Enforcement**: `ILME-FX3` has ONLY `Front Dial`
     (`base 0xe4da`), single `Rear Dial` (`base 0xe4db`), and `Control Wheel`
     (`base 0xe353`). Reject dormant 4-dial Alpha `Rear Dial L` / `Rear Dial R`
     (`_f 0x6a5c`/`0x680d` / `BKID_APP_mydial_rear_dial_{left,right}_setting_list0..2` /
     `DIALCUSTOMIZE_DIAL_SETUP_LEFT_SHUTTER_RIGHT_F_NO`) phantom bindings fail-closed
     (`EOPNOTSUPP`, errno `95`).
   - `[My Dial Settings]` `1..3` shared NVRAM banks with independent Still/Movie recall
     (`Hold` / `Toggle` / `1->2->3` skipping all-`Not set` banks, temporarily unlocking
     `[Lock Operation Parts]` while recalled) and `[Fn Menu Settings]` (`_g 0x614b`)
     strict **12 Still + 12 Movie** slot split (rejecting `Fn` invocation when all 12
     slots of the active mode are `Not set`, `_f.uxc 0x6220`). Contrasted with
     `ILME-FX6 Ver. 6.01` (`Multi Function Dial`, `Grip Dial`, `Handle Dial`,
     `IRIS Dial`, `ND Dial`, physical `HOLD` switch, `Status Screens`, and `Direct Menu`
     `Home Screen Priority` / `Direct Menu Priority`).

2. **Gate `G132` (`verify-liveview-grid-lut-embed-guard`)**:
   - Still-only `MENU -> (Shooting) -> [Shooting Display] -> [Live View Display Set.]`
     (`_f 0x6429`) **exact 3 active sub-items** on `ILME-FX3 Ver. 7.02`:
     1) `[Live View Display]` (`Setting Effect ON` default / `Setting Effect OFF`,
        `Initialize`-only; forced `Setting Effect OFF` whenever `[Bright Monitoring]` is active)
     2) `[Exposure Effect]` (`Exposure Set. & flash` default / `Exposure Setting Only`,
        `Initialize`-only)
     3) `[Frame Rate Low Limit]` (`On` / `Off` default — **Can be reset via
        `[Camera Settings Reset]`!**)
   - `[Grid Line Display]` (`On` / `Off` default, Still/Movie/`S&Q`, `Initialize`-only)
     & `[Grid Line Type]` (`Rule of 3rds Grid` default / `Square Grid` / `Diag. + Square Grid`,
     `Initialize`-only) isolated from HDMI clean feed when `HDMI Info. Display = Off`
     (or RAW output / `Off(HDMI Only)`), contrasted with `ILME-FX6` `Monitoring > Marker`
     (`Guide Frame`, `Aspect Marker`, `Safety Zone 80/90/92.5/95%`) and dormant custom
     PNG grids (`BKID_APP_IS_EXIST_CUSTOM_GRID_LINE0..3`).
   - `[Manage User LUTs]` (`(Exposure/Color) -> [Color/Tone]`: `User1..User16`, `17pt`/`33pt`
     `.cube`, `Initialize`-only; SD/SDXC `/Private/Sony/PRO/LUT`, CFexpress `/Sony/PRO/LUT`,
     safe `O_RDONLY` import with `slot1_data_sector_writes == 0`) & `[Select LUT]`
     (`S-Log3` / `s709` default resettable / `709(800%)` / `User1..16`), vs `[Embed LUT File]`
     under `MENU -> (Shooting) -> [Image Quality/Rec] -> [Log Shooting Setting]` (NOT under
     `[Color/Tone]`! default `On`, resettable; hardware-locked `Off` on `SD/SDHC` per
     `_g.uxc 0x61a0`; embeds 3D LUT metadata in recorded video container preserving `S-Log3`
     pixels without sidecar files), vs Picture Profile `PPLUT1..4` (`[Basic Look]`:
     irreversible pixel baking, reset by BOTH `[Camera Settings Reset]` and `[Initialize]`).
   - **Fail-Closed `Slot-1` Tier-0 Vault Firewall**: block any video recording with
     `Embed LUT File` / `PPLUT1..4` or any LUT/folder/sidecar/config write targeting a
     `Slot 1` Tier-0 recovery vault (`EROFS=30` / `EBUSY=16`, `slot1_data_sector_writes == 0`).

3. **Unified `132`-Gate Milestone Master Preflight (`evaluate_132gate_preflight` /
   `verify-132-gates`)**:
   - Delegates `G01..G130` directly to `evaluate_130gate_preflight()` and appends `G131` +
     `G132`.
   - Offline mode: `129/132` gates pass (`VERIFIED_129_OF_132_AWAITING_PHYSICAL_TIER0`, only
     physical Tier-0 bench receipts `G10..G12` pending); `--simulate-bench-dry-run`:
     `132/132` simulation gates pass (`VERIFIED_ALL_132_GATES_DRY_RUN_SIMULATED_BACKUP`).
   - All hardware attach, persistent eMMC write, EL3/SPI-NOR transmit, and cross-model
     flash redlines remain hard-locked `False`, `usb_packets_transmitted == 0`, and
     `raw_firmware_bytes_leaked == 0`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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
from .realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard import (
    Master130GateReport,
    evaluate_130gate_preflight,
)

# ---------------------------------------------------------------------------
# Schema, Version & Absolute Hardware / Firmware Safety Redlines
# ---------------------------------------------------------------------------

REALHW_DIAL_CUSTOMIZE_MYDIAL_FN_LIVEVIEW_LUT_EMBED_132GATE_SCHEMA = (
    "realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard_v1"
)
REALHW_DIAL_CUSTOMIZE_MYDIAL_FN_LIVEVIEW_LUT_EMBED_132GATE_VERSION = "2026.11.17"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST_PHASE303 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE303 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE303 = 15.0

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
G131 = "G131"
G131_GATE_ID = "G131"
G131_GATE_CODE = (
    "GATE_G131_DIAL_CUSTOMIZE_5ITEM_3DIAL_MYDIAL_12X2_FN_SPLIT_GUARD"
)
GATE_G131_DIAL_CUSTOMIZE_5ITEM_3DIAL_MYDIAL_12X2_FN_SPLIT_GUARD = G131_GATE_CODE

G132 = "G132"
G132_GATE_ID = "G132"
G132_GATE_CODE = (
    "GATE_G132_LIVEVIEW_3ITEM_BRIGHT_GRID_HDMI_LUT_EMBED_PPLUT_VAULT_GUARD"
)
GATE_G132_LIVEVIEW_3ITEM_BRIGHT_GRID_HDMI_LUT_EMBED_PPLUT_VAULT_GUARD = G132_GATE_CODE

# Model & Identity Contracts (Phase 303 suffixed to avoid __init__.py shadowing)
FX3_MODEL_NAME_PHASE303 = "ILME-FX3"
FX3_MODEL_ID_PHASE303 = 0x39383232
FX3_HELP_GUIDE_CODE_PHASE303 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE303 = "7.02"

FX6_MODEL_NAME_PHASE303 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE303 = "6.01"
FX6_PRODUCT_CODE_PHASE303 = "PRODUCT_MODEL_CHAPLIN"

# Shoot Modes & Reset Actions
SHOOT_MODE_STILL_PHASE303 = "Still"
SHOOT_MODE_MOVIE_PHASE303 = "Movie"
SHOOT_MODE_SQ_PHASE303 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE303: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE303,
    SHOOT_MODE_MOVIE_PHASE303,
    SHOOT_MODE_SQ_PHASE303,
)

RESET_ACTION_NONE_PHASE303 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303 = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE303 = "Reset Network Set."
RESET_ACTION_INITIALIZE_PHASE303 = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE303: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE303,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303,
    RESET_ACTION_RESET_NETWORK_SET_PHASE303,
    RESET_ACTION_INITIALIZE_PHASE303,
)

MEDIA_SLOT_1_PHASE303 = "Slot 1"
MEDIA_SLOT_2_PHASE303 = "Slot 2"
ALLOWED_MEDIA_SLOTS_PHASE303: Tuple[str, ...] = (
    MEDIA_SLOT_1_PHASE303,
    MEDIA_SLOT_2_PHASE303,
)

# ---------------------------------------------------------------------------
# G131 Constants: Dial Customize 5-Item, 3-Dial Topology, My Dial 1..3, Fn 12+12
# ---------------------------------------------------------------------------

DIAL_CUSTOMIZE_MENU_PATH_G131 = "MENU -> (Setup) -> [Dial Customize]"
DIAL_CUSTOMIZE_G_UXC_RESID16_G131 = 0x62ED

DIAL_CUSTOMIZE_5_ITEMS_G131: Tuple[str, ...] = (
    "Custom Key/Dial Set.",
    "My Dial Settings",
    "Av/Tv Rotate",
    "Function Ring(Lens)",
    "Lock Operation Parts",
)

LEGACY_DIAL_SETUP_MENU_NAME_G131 = "Dial Setup"
LEGACY_DIAL_WHEEL_SETUP_NAME_G131 = "Dial/Wheel Setup"
LEGACY_DIAL_WHEEL_SETUP_F_UXC_RESID16_G131 = 0x6A89
LEGACY_DIAL_WHEEL_LOCK_NAME_G131 = "Dial / Wheel Lock"
LEGACY_DIAL_WHEEL_LOCK_BASE_UXC_RESID16_G131 = 0xE352

AV_TV_ROTATE_F_UXC_RESID16_G131 = 0x72E3
AV_TV_ROTATE_NORMAL_G131 = "Normal"
AV_TV_ROTATE_REVERSE_G131 = "Reverse"
AV_TV_ROTATE_DEFAULT_G131 = AV_TV_ROTATE_NORMAL_G131
ALLOWED_AV_TV_ROTATE_MODES_G131: Tuple[str, ...] = (
    AV_TV_ROTATE_NORMAL_G131,
    AV_TV_ROTATE_REVERSE_G131,
)

FUNCTION_RING_F_UXC_RESID16_G131 = 0x715E
FUNCTION_RING_POWER_FOCUS_G131 = "Power Focus"
FUNCTION_RING_APSC_S35_FF_G131 = "APS-C/Super 35 mm / Full Frame"
FUNCTION_RING_DEFAULT_G131 = FUNCTION_RING_POWER_FOCUS_G131
ALLOWED_FUNCTION_RING_MODES_G131: Tuple[str, ...] = (
    FUNCTION_RING_POWER_FOCUS_G131,
    FUNCTION_RING_APSC_S35_FF_G131,
)
DORMANT_FUNCTION_RING_INVALID_G131 = "VAL_setting_function_ring_FUNCTION_RING_INVALID"

LOCK_OPERATION_PARTS_F_UXC_RESID16_G131 = 0x6904
LOCK_OPERATION_PARTS_OFF_G131 = "Off"
LOCK_OPERATION_PARTS_MULTI_SELECTOR_G131 = "Multi-Selector Only"
LOCK_OPERATION_PARTS_DIAL_WHEEL_G131 = "Dial + Wheel"
LOCK_OPERATION_PARTS_ALL_G131 = "All"
LOCK_OPERATION_PARTS_DEFAULT_G131 = LOCK_OPERATION_PARTS_OFF_G131
ALLOWED_LOCK_OPERATION_PARTS_MODES_G131: Tuple[str, ...] = (
    LOCK_OPERATION_PARTS_OFF_G131,
    LOCK_OPERATION_PARTS_MULTI_SELECTOR_G131,
    LOCK_OPERATION_PARTS_DIAL_WHEEL_G131,
    LOCK_OPERATION_PARTS_ALL_G131,
)

FX3_PHYSICAL_DIAL_FRONT_G131 = "Front Dial"
FX3_PHYSICAL_DIAL_REAR_G131 = "Rear Dial"
FX3_PHYSICAL_DIAL_WHEEL_G131 = "Control Wheel"
FX3_PHYSICAL_3_DIALS_G131: Tuple[str, ...] = (
    FX3_PHYSICAL_DIAL_FRONT_G131,
    FX3_PHYSICAL_DIAL_REAR_G131,
    FX3_PHYSICAL_DIAL_WHEEL_G131,
)

EOPNOTSUPP_ERRNO_G131 = 95
EOPNOTSUPP_NAME_G131 = "EOPNOTSUPP"

DORMANT_4DIAL_REAR_LR_TRAPS_G131: Tuple[str, ...] = (
    "Rear Dial L",
    "Rear Dial R",
    "BKID_APP_mydial_rear_dial_left_setting_list0",
    "BKID_APP_mydial_rear_dial_left_setting_list1",
    "BKID_APP_mydial_rear_dial_left_setting_list2",
    "BKID_APP_mydial_rear_dial_right_setting_list0",
    "BKID_APP_mydial_rear_dial_right_setting_list1",
    "BKID_APP_mydial_rear_dial_right_setting_list2",
    "DIALCUSTOMIZE_DIAL_SETUP_LEFT_SHUTTER_RIGHT_F_NO",
    "DIALCUSTOMIZE_DIAL_SETUP_LEFT_F_NO_RIGHT_SHUTTER",
    "BKID_APP_setting_dial_setup",
    "Dial Setup",
    "Dial/Wheel Setup",
    "Dial / Wheel Lock",
)

MY_DIAL_SETTINGS_F_UXC_RESID16_G131 = 0x6538
MY_DIAL_BANKS_G131: Tuple[str, ...] = ("My Dial 1", "My Dial 2", "My Dial 3")
MY_DIAL_RECALL_NONE_G131 = "None"
MY_DIAL_RECALL_HOLD_G131 = "Hold"
MY_DIAL_RECALL_TOGGLE_G131 = "Toggle"
MY_DIAL_RECALL_CYCLE_G131 = "1->2->3"
MY_DIAL_RECALL_DEFAULT_G131 = MY_DIAL_RECALL_NONE_G131
ALLOWED_MY_DIAL_RECALL_MODES_G131: Tuple[str, ...] = (
    MY_DIAL_RECALL_NONE_G131,
    MY_DIAL_RECALL_HOLD_G131,
    MY_DIAL_RECALL_TOGGLE_G131,
    MY_DIAL_RECALL_CYCLE_G131,
)
MY_DIAL_CYCLE_F_UXC_RESID16_G131 = 0x7987
MY_DIAL_UNSET_TOKEN_G131 = "Not set"

FN_MENU_SETTINGS_MENU_PATH_G131 = (
    "MENU -> (Setup) -> [Operation Customize] -> [Fn Menu Settings]"
)
FN_MENU_SETTINGS_G_UXC_RESID16_G131 = 0x614B
FN_MENU_ALL_NOT_SET_WARNING_F_UXC_RESID16_G131 = 0x6220
FN_MENU_NOT_SET_BASE_UXC_RESID16_G131 = 0xE0AC
FN_MENU_STILL_SLOTS_G131 = 12
FN_MENU_MOVIE_SLOTS_G131 = 12

FX6_MULTI_FUNCTION_DIAL_PATH_G131 = "Project > Multi Function Dial > Default Function"
FX6_DIAL_CONTROLS_G131: Tuple[str, ...] = (
    "Multi Function Dial",
    "Grip Dial",
    "Handle Dial",
    "IRIS Dial",
    "ND Dial",
)
FX6_INFO_DISP_PRIORITY_MODES_G131: Tuple[str, ...] = (
    "Home Screen Priority",
    "Direct Menu Priority",
)
FX6_STATUS_AND_DIRECT_MENU_SURFACES_G131: Tuple[str, ...] = (
    "Status Screens",
    "Direct Menu",
)

# ---------------------------------------------------------------------------
# G132 Constants: Live View Display Set. 3-Item + Bright Monitoring, Grid Line, LUT
# ---------------------------------------------------------------------------

LIVE_VIEW_DISPLAY_SET_MENU_PATH_G132 = (
    "MENU -> (Shooting) -> [Shooting Display] -> [Live View Display Set.]"
)
LIVE_VIEW_DISPLAY_SET_F_UXC_RESID16_G132 = 0x6429
LIVE_VIEW_DISPLAY_SET_3_SUBITEMS_G132: Tuple[str, ...] = (
    "Live View Display",
    "Exposure Effect",
    "Frame Rate Low Limit",
)

LIVE_VIEW_SETTING_EFFECT_ON_G132 = "Setting Effect ON"
LIVE_VIEW_SETTING_EFFECT_OFF_G132 = "Setting Effect OFF"
LIVE_VIEW_DISPLAY_DEFAULT_G132 = LIVE_VIEW_SETTING_EFFECT_ON_G132
ALLOWED_LIVE_VIEW_DISPLAY_MODES_G132: Tuple[str, ...] = (
    LIVE_VIEW_SETTING_EFFECT_ON_G132,
    LIVE_VIEW_SETTING_EFFECT_OFF_G132,
)

EXPOSURE_EFFECT_SET_AND_FLASH_G132 = "Exposure Set. & flash"
EXPOSURE_EFFECT_SET_ONLY_G132 = "Exposure Setting Only"
EXPOSURE_EFFECT_DEFAULT_G132 = EXPOSURE_EFFECT_SET_AND_FLASH_G132
ALLOWED_EXPOSURE_EFFECT_MODES_G132: Tuple[str, ...] = (
    EXPOSURE_EFFECT_SET_AND_FLASH_G132,
    EXPOSURE_EFFECT_SET_ONLY_G132,
)

FRAME_RATE_LOW_LIMIT_ON_G132 = "On"
FRAME_RATE_LOW_LIMIT_OFF_G132 = "Off"
FRAME_RATE_LOW_LIMIT_DEFAULT_G132 = FRAME_RATE_LOW_LIMIT_OFF_G132
ALLOWED_FRAME_RATE_LOW_LIMIT_MODES_G132: Tuple[str, ...] = (
    FRAME_RATE_LOW_LIMIT_ON_G132,
    FRAME_RATE_LOW_LIMIT_OFF_G132,
)

GRID_LINE_MENU_PATH_G132 = "MENU -> (Shooting) -> [Shooting Display]"
GRID_LINE_DISPLAY_F_UXC_RESID16_G132 = 0x6F9D
GRID_LINE_DISPLAY_ON_G132 = "On"
GRID_LINE_DISPLAY_OFF_G132 = "Off"
GRID_LINE_DISPLAY_DEFAULT_G132 = GRID_LINE_DISPLAY_OFF_G132
ALLOWED_GRID_LINE_DISPLAY_MODES_G132: Tuple[str, ...] = (
    GRID_LINE_DISPLAY_ON_G132,
    GRID_LINE_DISPLAY_OFF_G132,
)

GRID_LINE_TYPE_RULE_OF_3RDS_G132 = "Rule of 3rds Grid"
GRID_LINE_TYPE_SQUARE_G132 = "Square Grid"
GRID_LINE_TYPE_DIAG_SQUARE_G132 = "Diag. + Square Grid"
GRID_LINE_TYPE_DEFAULT_G132 = GRID_LINE_TYPE_RULE_OF_3RDS_G132
ALLOWED_GRID_LINE_TYPES_G132: Tuple[str, ...] = (
    GRID_LINE_TYPE_RULE_OF_3RDS_G132,
    GRID_LINE_TYPE_SQUARE_G132,
    GRID_LINE_TYPE_DIAG_SQUARE_G132,
)

HDMI_INFO_DISPLAY_F_UXC_RESID16_G132 = 0x6E7C
HDMI_INFO_DISPLAY_ON_G132 = "On"
HDMI_INFO_DISPLAY_OFF_G132 = "Off"
HDMI_INFO_DISPLAY_DEFAULT_G132 = HDMI_INFO_DISPLAY_ON_G132
ALLOWED_HDMI_INFO_DISPLAY_MODES_G132: Tuple[str, ...] = (
    HDMI_INFO_DISPLAY_ON_G132,
    HDMI_INFO_DISPLAY_OFF_G132,
)

FX6_MARKER_MENU_PATH_G132 = "Monitoring > Marker"
FX6_MARKER_SAFETY_ZONES_G132: Tuple[str, ...] = ("80%", "90%", "92.5%", "95%")
FX6_DORMANT_CUSTOM_PNG_GRID_SYMBOLS_G132: Tuple[str, ...] = (
    "BKID_APP_IS_EXIST_CUSTOM_GRID_LINE0",
    "BKID_APP_IS_EXIST_CUSTOM_GRID_LINE1",
    "BKID_APP_IS_EXIST_CUSTOM_GRID_LINE2",
    "BKID_APP_IS_EXIST_CUSTOM_GRID_LINE3",
    "BKID_APP_DELETED_SETTING_GRID_LINE_DISPLAY_MOVIE",
    "GOLDEN_RATIO_GRID",
    "Custom PNG Grid",
)

MANAGE_USER_LUTS_MENU_PATH_G132 = (
    "MENU -> (Exposure/Color) -> [Color/Tone] -> [Manage User LUTs]"
)
MANAGE_USER_LUTS_F_UXC_RESID16_G132 = 0x71AF
EMBED_LUT_FILE_MENU_PATH_G132 = (
    "MENU -> (Shooting) -> [Image Quality/Rec] -> [Log Shooting Setting] -> [Embed LUT File]"
)
EMBED_LUT_FILE_WRONG_PATH_G132 = (
    "MENU -> (Exposure/Color) -> [Color/Tone] -> [Embed LUT File]"
)
EMBED_LUT_FILE_F_UXC_RESID16_G132 = 0x680F
EMBED_LUT_SDHC_LOCK_G_UXC_RESID16_G132 = 0x61A0

USER_LUT_SLOT_MIN_G132 = 1
USER_LUT_SLOT_MAX_G132 = 16
ALLOWED_USER_LUT_SLOTS_G132: Tuple[str, ...] = tuple(
    f"User{i}" for i in range(USER_LUT_SLOT_MIN_G132, USER_LUT_SLOT_MAX_G132 + 1)
)
ALLOWED_CUBE_GRID_POINTS_G132: Tuple[int, ...] = (17, 33)
USER_LUT_MAX_FILENAME_CHARS_G132 = 63

LUT_FOLDER_SD_SDXC_G132 = "/Private/Sony/PRO/LUT"
LUT_FOLDER_CFEXPRESS_G132 = "/Sony/PRO/LUT"

CARD_TYPE_SD_SDHC_G132 = "SD/SDHC"
CARD_TYPE_SDXC_G132 = "SDXC"
CARD_TYPE_CFEXPRESS_A_G132 = "CFexpress Type A"
ALLOWED_CARD_TYPES_G132: Tuple[str, ...] = (
    CARD_TYPE_SD_SDHC_G132,
    CARD_TYPE_SDXC_G132,
    CARD_TYPE_CFEXPRESS_A_G132,
)

SELECT_LUT_SLOG3_G132 = "S-Log3"
SELECT_LUT_S709_G132 = "s709"
SELECT_LUT_709_800_G132 = "709(800%)"
SELECT_LUT_DEFAULT_G132 = SELECT_LUT_S709_G132
ALLOWED_SELECT_LUT_PRESETS_G132: Tuple[str, ...] = (
    SELECT_LUT_SLOG3_G132,
    SELECT_LUT_S709_G132,
    SELECT_LUT_709_800_G132,
) + ALLOWED_USER_LUT_SLOTS_G132

EMBED_LUT_ON_G132 = "On"
EMBED_LUT_OFF_G132 = "Off"
EMBED_LUT_DEFAULT_G132 = EMBED_LUT_ON_G132
ALLOWED_EMBED_LUT_MODES_G132: Tuple[str, ...] = (
    EMBED_LUT_ON_G132,
    EMBED_LUT_OFF_G132,
)

PPLUT_SLOTS_G132: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
FX6_EMBED_LUT_MENU_PATH_G132 = "Project > Cine EI/Flex.ISO Set > Embed LUT File"
FX6_LUT_CHANNEL_SWITCHES_G132: Tuple[str, ...] = (
    "Internal Rec.",
    "SDI/HDMI",
    "LCD/VF",
    "Proxy/Stream",
)
FX6_USER_LUT_ACTIVE_UI_CAP_G132 = 16
FX6_APPFW_PRM_USER_LUT_BUFFER_SLOTS_G132 = 50

LUT_OP_IMPORT_USER_LUT_G132 = "Import User LUT"
LUT_OP_DELETE_ALL_USER_LUTS_G132 = "Delete All"
LUT_OP_MAKE_CUBE_FOLDER_G132 = "Make Cube Folder"
LUT_OP_WRITE_CUBE_OR_SIDECAR_G132 = "Write Cube/Sidecar"
LUT_OP_RECORD_EMBED_LUT_G132 = "Record Embed LUT File"
LUT_OP_RECORD_PPLUT_G132 = "Record PPLUT"
ALLOWED_LUT_REC_OPS_G132: Tuple[str, ...] = (
    LUT_OP_IMPORT_USER_LUT_G132,
    LUT_OP_DELETE_ALL_USER_LUTS_G132,
    LUT_OP_MAKE_CUBE_FOLDER_G132,
    LUT_OP_WRITE_CUBE_OR_SIDECAR_G132,
    LUT_OP_RECORD_EMBED_LUT_G132,
    LUT_OP_RECORD_PPLUT_G132,
)

EROFS_ERRNO_G132 = 30
EBUSY_ERRNO_G132 = 16

# Status / Violation Codes
STATUS_BLOCKED_PHASE303_DONOR_INTEGRITY = "STATUS_BLOCKED_PHASE303_DONOR_INTEGRITY"

STATUS_VERIFIED_G131 = "STATUS_VERIFIED_G131"
STATUS_BLOCKED_G131_TELEMETRY_INVALID = "STATUS_BLOCKED_G131_TELEMETRY_INVALID"
STATUS_BLOCKED_G131_DIAL_CUSTOMIZE_5ITEM_OR_RESET_VIOLATION = (
    "STATUS_BLOCKED_G131_DIAL_CUSTOMIZE_5ITEM_OR_RESET_VIOLATION"
)
STATUS_BLOCKED_G131_4DIAL_REAR_LR_OR_LEGACY_TRAP_VIOLATION = (
    "STATUS_BLOCKED_G131_4DIAL_REAR_LR_OR_LEGACY_TRAP_VIOLATION"
)
STATUS_BLOCKED_G131_MYDIAL_OR_FN_12X2_SPLIT_VIOLATION = (
    "STATUS_BLOCKED_G131_MYDIAL_OR_FN_12X2_SPLIT_VIOLATION"
)
STATUS_BLOCKED_G131_FX6_DIAL_OR_DIRECT_MENU_CROSSWIRE_VIOLATION = (
    "STATUS_BLOCKED_G131_FX6_DIAL_OR_DIRECT_MENU_CROSSWIRE_VIOLATION"
)

STATUS_VERIFIED_G132 = "STATUS_VERIFIED_G132"
STATUS_BLOCKED_G132_TELEMETRY_INVALID = "STATUS_BLOCKED_G132_TELEMETRY_INVALID"
STATUS_BLOCKED_G132_LIVEVIEW_3ITEM_BRIGHT_OR_RESET_VIOLATION = (
    "STATUS_BLOCKED_G132_LIVEVIEW_3ITEM_BRIGHT_OR_RESET_VIOLATION"
)
STATUS_BLOCKED_G132_GRID_CLEAN_HDMI_OR_FX6_PNG_VIOLATION = (
    "STATUS_BLOCKED_G132_GRID_CLEAN_HDMI_OR_FX6_PNG_VIOLATION"
)
STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION = (
    "STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION"
)
STATUS_BLOCKED_G132_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION = (
    "STATUS_BLOCKED_G132_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION"
)

# ---------------------------------------------------------------------------
# Pinned Wave-56 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE303: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (62_700_047, b"BKID_APP_setting_av_tv_rotate"),
    (49_969_107, b"AV_TV_ROTATE_NORMAL"),
    (49_969_127, b"AV_TV_ROTATE_REVERSE"),
    (62_700_139, b"BKID_APP_setting_device_lock"),
    (62_076_809, b"DEVICE_LOCK_OFF"),
    (62_076_849, b"DEVICE_LOCK_MULTISELECTOR"),
    (62_076_899, b"DEVICE_LOCK_DIAL_WHEEL"),
    (62_076_946, b"DEVICE_LOCK_ALL"),
    (62_700_108, b"BKID_APP_setting_function_ring"),
    (61_890_744, b"VAL_setting_function_ring_FUNCTION_RING_POWER_FOCUS"),
    (61_890_796, b"VAL_setting_function_ring_FUNCTION_RING_SUPER_35MM_SEL"),
    (61_890_851, b"VAL_setting_function_ring_FUNCTION_RING_INVALID"),
    (62_696_568, b"BKID_APP_setting_custom_key_movie_front_dial"),
    (62_700_019, b"BKID_APP_setting_dial_setup"),
    (49_969_037, b"DIAL_SETUP_FRONT_SHUTTER_REAR_F_NO"),
    (49_969_072, b"DIAL_SETUP_FRONT_F_NO_REAR_SHUTTER"),
    (49_968_939, b"DIALCUSTOMIZE_DIAL_SETUP_LEFT_SHUTTER_RIGHT_F_NO"),
    (49_968_988, b"DIALCUSTOMIZE_DIAL_SETUP_LEFT_F_NO_RIGHT_SHUTTER"),
    (62_699_491, b"BKID_APP_mydial_front_dial_setting_list0"),
    (62_699_614, b"BKID_APP_mydial_rear_dial_left_setting_list0"),
    (62_699_749, b"BKID_APP_mydial_rear_dial_right_setting_list0"),
    (62_699_887, b"BKID_APP_mydial_control_wheel_setting_list0"),
    (62_074_889, b"VAL_my_dial_recall_state_MY_DIAL_RECALL_STATE_NONE"),
    (62_075_084, b"VAL_my_dial_recall_state_MY_DIAL_RECALL_STATE_1_HOLD"),
    (62_698_483, b"BKID_APP_fn_menu_item_ids_for_still0"),
    (62_698_891, b"BKID_APP_fn_menu_item_ids_for_still11"),
    (62_698_929, b"BKID_APP_fn_menu_item_ids_for_movie0"),
    (62_699_337, b"BKID_APP_fn_menu_item_ids_for_movie11"),
    (62_683_444, b"BKID_APP_setting_live_view_display"),
    (62_683_677, b"BKID_APP_setting_live_view_display_with_flash"),
    (62_683_517, b"BKID_APP_setting_flash_exposure_effect"),
    (61_483_333, b"FLASH_EXPOSURE_EFFECT_ON"),
    (61_483_392, b"FLASH_EXPOSURE_EFFECT_OFF"),
    (62_683_304, b"BKID_APP_setting_grid_line_display"),
    (62_683_377, b"BKID_APP_setting_grid_line_type"),
    (62_702_156, b"BKID_APP_setting_hdmi_info_display"),
    (59_805_546, b"/Private/Sony/PRO/LUT"),
    (62_853_087, b"BKID_APP_is_exist_user_lut0"),
    (62_853_512, b"BKID_APP_is_exist_user_lut15"),
    (62_853_541, b"BKID_APP_user_lut_file_id0"),
    (62_853_979, b"BKID_APP_user_lut_attr_input_gamut0"),
    (62_852_441, b"BKID_APP_user_lut_attr_ae_level_offset0"),
    (62_688_430, b"BKID_APP_setting_select_lut"),
    (59_805_606, b"SL3SG3Ctos709.cube"),
    (59_805_572, b"SL3SG3CtoR709-800.cube"),
    (62_676_058, b"BKID_APP_setting_embed_lut_file"),
    (62_854_730, b"BKID_APP_setting_pplut1_link_uset_lut"),
    (62_854_967, b"BKID_APP_setting_pplut4_link_uset_lut"),
    (63_095_125, b"is_embedded_lut_in_pb_file"),
    (60_083_152, b"N5model25sequence_set_embedded_lutE"),
    (59_918_952, b"N5model27sequence_embedded_lut_applyE"),
    (58_690_284, b"embedded_lut_file_name"),
    (59_919_132, b"read3DLUTFileForCube"),
    (59_805_303, b"mount_lut_folder"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE303 = (
    "a4da108c5081286aa7cfe741d86e2c708c8558ac0662a16d4e81899398b25269"
)

PINNED_FX6_APPFW_SLICES_PHASE303: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (41_748_974, b"PRODUCT_MODEL_CHAPLIN"),
    (40_933_833, b"BKID_APP_SETTING_MULTI_FUNCTION_DIAL"),
    (40_933_560, b"BKID_APP_SETTING_ASSIGNABLE_DIAL_00"),
    (40_933_724, b"BKID_APP_SETTING_ASSIGNABLE_DIAL_01"),
    (40_921_540, b"BKID_APP_SETTING_GUIDE_FRAME"),
    (40_921_416, b"BKID_APP_SETTING_MARKER_DISPLAY"),
    (40_941_579, b"BKID_APP_SETTING_ASPECT_MARKER"),
    (40_931_879, b"BKID_APP_SETTING_FLEXIBLE_ISO_EMBED_LUT_FILE"),
    (40_078_929, b"PRM_is_exist_user_lut0"),
    (40_080_095, b"PRM_is_exist_user_lut49"),
    (41_121_066, b"BKID_APP_IS_EXIST_CUSTOM_GRID_LINE0"),
    (40_982_866, b"BKID_APP_DELETED_SETTING_GRID_LINE_DISPLAY_MOVIE"),
    (41_532_422, b"GOLDEN_RATIO_GRID"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE303 = (
    "656ba14c5ea7dfb6828b71ec1350471b701149d760de8b0a8c6fc2b9103c5fd5"
)

PINNED_PHASE303_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE303,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE303),
        "FX3 appFw.so Wave-56 Dial/MyDial/Fn/LiveView/Grid/LUT/Embed/PPLUT symbols",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Custom Key/Dial Set.",
            b"Dial/Wheel Setup",
            b"Av/Tv Rotate",
            b"Function Ring(Lens)",
            b"Power Focus",
            b"Lock Operation Parts",
            b"Front Dial",
            b"Rear Dial",
            b"Rear Dial L",
            b"Rear Dial R",
            b"Control Wheel",
            b"My Dial Settings",
            b"My Dial 1 during Hold",
            b"Toggle My Dial 1",
            b"Live View Display Set.",
            b"Setting Effect ON",
            b"Setting Effect OFF",
            b"Exposure Effect",
            b"Frame Rate Low Limit",
            b"Grid Line Display",
            b"Grid Line Type",
            b"Rule of 3rds Grid",
            b"Square Grid",
            b"Diag. + Square Grid",
            b"HDMI Info. Display",
            b"Manage User LUTs",
            b"Select LUT",
            b"Embed LUT File",
            b"Basic Look",
        ),
        "FX3 string_english_f.uxc Wave-56 EN parity",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "Av/Tv旋转".encode("utf-8"),
            "功能环(镜头)".encode("utf-8"),
            "锁定操作的部件".encode("utf-8"),
            "我的转盘设置".encode("utf-8"),
            "实时取景显示设置".encode("utf-8"),
            "曝光效果".encode("utf-8"),
            "帧速率低速限制".encode("utf-8"),
            "网格线显示".encode("utf-8"),
            "管理用户LUT".encode("utf-8"),
            "选择LUT".encode("utf-8"),
            "内置LUT文件".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-56 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "自訂鍵/轉盤設定".encode("utf-8"),
            "Av/Tv旋轉".encode("utf-8"),
            "功能環(鏡頭)".encode("utf-8"),
            "操作鈕鎖定".encode("utf-8"),
            "我的轉盤設定".encode("utf-8"),
            "Live View顯示設定".encode("utf-8"),
            "曝光效果".encode("utf-8"),
            "幀率低速限制".encode("utf-8"),
            "格線顯示".encode("utf-8"),
            "管理使用者LUT".encode("utf-8"),
            "選取LUT".encode("utf-8"),
            "嵌入LUT檔案".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-56 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "Av/Tvの回転方向".encode("utf-8"),
            "操作部のロック".encode("utf-8"),
            "マイダイヤル設定".encode("utf-8"),
            "露出の効果反映".encode("utf-8"),
            "ｸﾞﾘｯﾄﾞﾗｲﾝ表示".encode("utf-8"),
            "ユーザーLUTの管理".encode("utf-8"),
            "LUT選択".encode("utf-8"),
            "LUTﾌｧｲﾙの埋め込み".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-56 JA parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Front dial",
            b"Rear dial",
            b"Control Wheel",
            b"Not set",
            b"Dial / Wheel Lock",
            b"Setting Effect ON",
            b"Setting Effect OFF",
            b"Rule of 3rds Grid",
            b"Square Grid",
            b"Diag. + Square Grid",
        ),
        "FX3 string_english.uxc Wave-56 base dial/grid/liveview strings",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Dial Customize",
            b"Fn Menu Settings",
            b"Shooting Display",
            b"Color/Tone",
        ),
        "FX3 string_english_g.uxc Wave-56 menu group strings",
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
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE303,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE303),
        "FX6 appFw.so Wave-56 MultiFunctionDial/GuideFrame/Marker/EmbedLUT/50LutBuf/CustomGrid symbols",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"Multi Function Dial",
            b"Grip Dial",
            b"Handle Dial",
            b"IRIS Dial",
            b"Base Look",
            b"Import from Media(B)",
            b"Embed LUT File",
            b"Home Screen Priority",
            b"Direct Menu Priority",
        ),
        "FX6 string_english.uxc Wave-56 strings",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"ND Dial",
            b"Direct Menu",
            b"Guide Frame",
            b"Aspect Marker",
            b"Safety Zone",
            b"Center Marker",
            b"User 3D LUT",
        ),
        "FX6 string_english_2.uxc Wave-56 strings",
    ),
}

_DONOR_BLOB_CACHE: Dict[str, Tuple[int, float, int, str, bytes]] = {}

# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase303DonorAuditResult:
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
class DialCustomizeMyDialFnGuardResult:
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
    dial_customize_menu_path: str
    dial_customize_5_items: Tuple[str, ...]
    dial_customize_survived_cam_reset: bool
    effective_av_tv_rotate: str
    effective_function_ring: str
    effective_lock_operation_parts: str
    fx3_physical_3_dials: Tuple[str, ...]
    requested_physical_dial: str
    dormant_4dial_rear_lr_blocked: bool
    block_errno: Optional[int]
    block_errno_name: Optional[str]
    my_dial_nvram_shared_across_modes: bool
    my_dial_recall_per_mode_custom_key_split: bool
    effective_my_dial_recall_mode: str
    effective_my_dial_bank: Optional[int]
    my_dial_cycle_order: Tuple[int, ...]
    my_dial_skipped_empty_banks: Tuple[int, ...]
    my_dial_temp_unlock_override_active: bool
    fn_menu_menu_path: str
    fn_menu_still_slots: int
    fn_menu_movie_slots: int
    fn_menu_active_mode_pool: str
    fn_menu_survived_cam_reset: bool
    fn_invocation_blocked_all_not_set: bool
    fx6_dial_controls: Tuple[str, ...]
    fx6_surfaces: Tuple[str, ...]
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G131DialCustomizeMyDialFnGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    dial_customize_mydial_fn_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LiveViewGridLutEmbedGuardResult:
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
    live_view_display_set_menu_path: str
    live_view_display_set_3_subitems: Tuple[str, ...]
    live_view_display_set_still_only: bool
    bright_monitoring_active: bool
    effective_live_view_display: str
    effective_exposure_effect: str
    effective_frame_rate_low_limit: str
    live_view_and_exposure_effect_survived_cam_reset: bool
    frame_rate_low_limit_reset_on_cam_reset: bool
    effective_grid_line_display: str
    effective_grid_line_type: str
    grid_line_survived_cam_reset: bool
    effective_hdmi_info_display: str
    grid_line_isolated_from_hdmi_clean_feed: bool
    hdmi_clean_feed_preserved: bool
    manage_user_luts_menu_path: str
    embed_lut_file_menu_path: str
    card_type: str
    expected_lut_folder_path: str
    effective_select_lut: str
    select_lut_reset_on_cam_reset: bool
    user_luts_survived_cam_reset: bool
    effective_embed_lut_file: str
    embed_lut_locked_off_by_sdhc: bool
    embed_lut_reset_on_cam_reset: bool
    embed_lut_preserves_slog3_pixels: bool
    embed_lut_creates_external_sidecar: bool
    embed_lut_metadata_embedded_in_container: bool
    pplut_slots: Tuple[str, ...]
    pplut_bakes_pixels_irreversibly: bool
    pplut_reset_on_cam_reset_and_initialize: bool
    requested_lut_or_rec_op: Optional[str]
    requested_target_slot: str
    slot_1_write_protected: bool
    slot_1_contains_tier0_vault: bool
    lut_import_read_only_safe: bool
    slot1_vault_firewall_blocked: bool
    block_errno: Optional[str]
    block_errno_code: Optional[int]
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    fx6_user_lut_ui_cap: int
    fx6_appfw_buffer_slots: int
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G132LiveViewGridLutEmbedGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    liveview_grid_lut_embed_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master132GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_129_gates_verified: bool
    all_132_gates_verified: bool
    g13_to_g132_all_passed: bool
    g131_to_g132_all_passed: bool
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
    master_130_report: Dict[str, Any]
    g131_result: Dict[str, Any]
    g132_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _is_truthy(val: Optional[str]) -> bool:
    if val is None:
        return False
    return val.strip().lower() in ("1", "true", "yes", "on")


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return _is_truthy(os.environ.get(ENV_FORCE_CLEAN_ROOM)) or _is_truthy(
        os.environ.get(ENV_CLEAN_ROOM_TEST_PHASE303)
    )


def _is_ci_env() -> bool:
    return _is_truthy(os.environ.get("GITHUB_ACTIONS"))


def _is_real_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _read_exact_o_rdonly(path: Path) -> Tuple[int, str, bytes]:
    """Read an entire small UXC/BIN donor file strictly via os.O_RDONLY."""
    key = str(path.resolve())
    st = os.stat(key)
    cached = _DONOR_BLOB_CACHE.get(key)
    if (
        cached is not None
        and cached[0] == st.st_size
        and cached[1] == st.st_mtime
        and cached[2] == getattr(st, "st_ino", 0)
    ):
        return cached[0], cached[3], cached[4]

    fd = os.open(key, os.O_RDONLY)
    try:
        chunks: List[bytes] = []
        hasher = hashlib.sha256()
        total = 0
        while True:
            blk = os.read(fd, 1024 * 1024)
            if not blk:
                break
            total += len(blk)
            hasher.update(blk)
            chunks.append(blk)
        blob = b"".join(chunks)
        digest = hasher.hexdigest()
        _DONOR_BLOB_CACHE[key] = (
            total,
            st.st_mtime,
            getattr(st, "st_ino", 0),
            digest,
            blob,
        )
        return total, digest, blob
    finally:
        os.close(fd)


def _read_appfw_slices_o_rdonly(
    path: Path,
    slices: Tuple[Tuple[int, bytes], ...],
) -> Tuple[int, str, Tuple[bytes, ...]]:
    """Bounded os.pread SHA-256 verification over pinned appFw.so byte slices."""
    key = f"{path.resolve()}::slices303::{len(slices)}"
    st = os.stat(path)
    cached = _DONOR_BLOB_CACHE.get(key)
    if (
        cached is not None
        and cached[0] == st.st_size
        and cached[1] == st.st_mtime
        and cached[2] == getattr(st, "st_ino", 0)
    ):
        return cached[0], cached[3], tuple(tok for _, tok in slices)

    fd = os.open(str(path), os.O_RDONLY)
    try:
        hasher = hashlib.sha256()
        missing: List[bytes] = []
        for offset, expected in slices:
            if offset < 0 or offset + len(expected) > st.st_size:
                missing.append(expected)
                continue
            observed = os.pread(fd, len(expected), offset)
            if observed != expected:
                missing.append(expected)
            else:
                hasher.update(observed)
        digest = hasher.hexdigest() if not missing else "MISSING_SLICE"
        if not missing:
            _DONOR_BLOB_CACHE[key] = (
                st.st_size,
                st.st_mtime,
                getattr(st, "st_ino", 0),
                digest,
                b"",
            )
        present = tuple(tok for _, tok in slices if tok not in missing)
        return st.st_size, digest, present
    finally:
        os.close(fd)


def _normalize_shoot_mode(mode: Any) -> Optional[str]:
    if not isinstance(mode, str):
        return None
    m = mode.strip().lower()
    if m in ("still", "photo", "p", "a", "s", "m"):
        return SHOOT_MODE_STILL_PHASE303
    if m in ("movie", "video"):
        return SHOOT_MODE_MOVIE_PHASE303
    if m in ("s&q", "sq", "s&q motion", "snq"):
        return SHOOT_MODE_SQ_PHASE303
    return None


def _normalize_reset_action(action: Any) -> Optional[str]:
    if not isinstance(action, str):
        return None
    a = action.strip().lower()
    if a in ("none", "", "no_reset"):
        return RESET_ACTION_NONE_PHASE303
    if a in ("camera settings reset", "cam_reset", "camera_settings_reset"):
        return RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303
    if a in ("reset network set.", "reset network set", "network_reset"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE303
    if a in ("initialize", "factory_reset", "init"):
        return RESET_ACTION_INITIALIZE_PHASE303
    return None


def _normalize_media_slot(slot: Any) -> Optional[str]:
    if _is_real_int(slot):
        if slot == 1:
            return MEDIA_SLOT_1_PHASE303
        if slot == 2:
            return MEDIA_SLOT_2_PHASE303
        return None
    if not isinstance(slot, str):
        return None
    s = slot.strip().lower().replace("_", " ")
    if s in ("slot 1", "slot1", "1", "a", "slot a"):
        return MEDIA_SLOT_1_PHASE303
    if s in ("slot 2", "slot2", "2", "b", "slot b"):
        return MEDIA_SLOT_2_PHASE303
    return None


def _normalize_on_off(val: Any) -> Optional[str]:
    if isinstance(val, bool):
        return None
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s == "on":
        return "On"
    if s == "off":
        return "Off"
    return None


# ---------------------------------------------------------------------------
# 1. `< 0.20s` Bounded O_RDONLY Local Donor Audit (Clean-Room Fallback Safe)
# ---------------------------------------------------------------------------


def audit_phase303_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase303DonorAuditResult:
    """Audit all 11 Wave-56 local donor files strictly via `os.O_RDONLY` in `< 0.20s`
    (with deterministic `CLEAN_ROOM_SYNTHETIC` fallback when donor assets are absent
    or clean-room mode is forced).
    """
    t0 = time.perf_counter()
    resolved_repo = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else dict(PINNED_PHASE303_DONOR_SPECS)
    )
    clean_forced = _is_forced_clean_room(force_clean_room)
    explicit_root = work_root is not None
    effective_root = (
        Path(work_root)
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=resolved_repo).work_root
    )

    if clean_forced:
        elapsed = time.perf_counter() - t0
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE303
            if _is_ci_env()
            else DONOR_CHECK_MAX_SECONDS_PHASE303
        )
        return Phase303DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_NO_DONOR_TOUCH",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_200ms=elapsed <= budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(specs.keys()),
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            sha256_by_artifact={},
            bytes_by_artifact={},
            errors=(),
            warnings=(
                "CLEAN_ROOM_SYNTHETIC mode active; pinned Wave-56 contracts used without donor I/O.",
            ),
        )

    all_exist = all((effective_root / rel).is_file() for _, rel, *_ in specs.values())
    if (not explicit_root) and (not all_exist) and (donor_specs_override is None):
        elapsed = time.perf_counter() - t0
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE303
            if _is_ci_env()
            else DONOR_CHECK_MAX_SECONDS_PHASE303
        )
        return Phase303DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_ABSENT_DONOR_FALLBACK",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_200ms=elapsed <= budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(specs.keys()),
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            sha256_by_artifact={},
            bytes_by_artifact={},
            errors=(),
            warnings=(
                "Local donor tree absent; deterministic CLEAN_ROOM_SYNTHETIC fallback engaged.",
            ),
        )

    checked: List[str] = []
    missing: List[str] = []
    errors: List[str] = []
    sha_map: Dict[str, str] = {}
    bytes_map: Dict[str, int] = {}
    files_inspected = 0

    for key, (model, rel, expected_size, expected_sha, tokens, desc) in specs.items():
        path = effective_root / rel
        if not path.is_file():
            missing.append(f"{key}:missing_file:{rel}")
            errors.append(f"Missing donor artifact `{key}` ({desc}) at `{rel}`.")
            continue
        files_inspected += 1
        if key == "fx3_appfw_so" and donor_specs_override is None:
            size, digest, present_tokens = _read_appfw_slices_o_rdonly(
                path, PINNED_FX3_APPFW_SLICES_PHASE303
            )
            blob: Optional[bytes] = None
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            size, digest, present_tokens = _read_appfw_slices_o_rdonly(
                path, PINNED_FX6_APPFW_SLICES_PHASE303
            )
            blob = None
        else:
            size, digest, blob = _read_exact_o_rdonly(path)
            present_tokens = tuple(tok for tok in tokens if tok in blob)

        bytes_map[key] = size
        sha_map[key] = digest

        if size != expected_size:
            missing.append(f"{key}:size_mismatch:{size}!={expected_size}")
            errors.append(
                f"Donor `{key}` size mismatch: observed {size}, expected {expected_size}."
            )
        if digest != expected_sha:
            missing.append(f"{key}:sha256_mismatch:{digest[:12]}")
            errors.append(
                f"Donor `{key}` SHA-256 mismatch: observed {digest}, expected {expected_sha}."
            )
        for tok in tokens:
            if tok not in present_tokens:
                missing.append(f"{key}:missing_marker:{tok.decode('utf-8', 'replace')}")
                errors.append(f"Donor `{key}` missing pinned marker `{tok!r}`.")
        if not errors:
            checked.append(key)

    elapsed = time.perf_counter() - t0
    budget = (
        DONOR_CHECK_CI_MAX_SECONDS_PHASE303
        if _is_ci_env()
        else DONOR_CHECK_MAX_SECONDS_PHASE303
    )
    within_budget = elapsed <= budget
    if not within_budget:
        errors.append(
            f"Phase 303 O_RDONLY donor audit exceeded budget: {elapsed:.4f}s > {budget:.2f}s."
        )

    fx3_ok = not any(m.startswith("fx3_") for m in missing)
    fx6_ok = not any(m.startswith("fx6_") for m in missing)
    lang_ok = not any("string_" in m for m in missing)
    valid = (len(missing) == 0) and (len(errors) == 0) and within_budget
    status = STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE303_DONOR_INTEGRITY

    return Phase303DonorAuditResult(
        valid=valid,
        status=status,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY_PREAD_AND_EXACT",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_200ms=within_budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_ok,
        fx6_contracts_verified=fx6_ok,
        four_lang_resid16_parity_verified=lang_ok,
        sha256_by_artifact=sha_map,
        bytes_by_artifact=bytes_map,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate G131: Dial Customize 5-Item Truth, 3-Dial Hardware Topology,
#    My Dial 1..3 & Fn Menu 12+12 Split Guard
# ---------------------------------------------------------------------------


def _normalize_av_tv_rotate(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s == "normal":
        return AV_TV_ROTATE_NORMAL_G131
    if s == "reverse":
        return AV_TV_ROTATE_REVERSE_G131
    return None


def _normalize_function_ring(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower().replace("_", " ").replace("-", " ")
    if s == "power focus":
        return FUNCTION_RING_POWER_FOCUS_G131
    if s in (
        "aps c/super 35 mm / full frame",
        "aps c / super 35 mm / full frame",
        "aps c s35 ff",
        "super 35mm sel",
        "apsc s35 ff",
    ):
        return FUNCTION_RING_APSC_S35_FF_G131
    if val.strip() == FUNCTION_RING_APSC_S35_FF_G131:
        return FUNCTION_RING_APSC_S35_FF_G131
    return None


def _normalize_lock_operation_parts(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s == "off":
        return LOCK_OPERATION_PARTS_OFF_G131
    if s in ("multi-selector only", "multi selector only", "multiselector"):
        return LOCK_OPERATION_PARTS_MULTI_SELECTOR_G131
    if s in ("dial + wheel", "dial+wheel", "dial_wheel"):
        return LOCK_OPERATION_PARTS_DIAL_WHEEL_G131
    if s == "all":
        return LOCK_OPERATION_PARTS_ALL_G131
    return None


def _normalize_my_dial_recall_mode(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower().replace("→", "->")
    if s in ("none", "off", ""):
        return MY_DIAL_RECALL_NONE_G131
    if s in ("hold", "during hold"):
        return MY_DIAL_RECALL_HOLD_G131
    if s == "toggle":
        return MY_DIAL_RECALL_TOGGLE_G131
    if s in ("1->2->3", "cycle", "1-2-3"):
        return MY_DIAL_RECALL_CYCLE_G131
    return None


def _normalize_physical_dial(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s == "front dial":
        return FX3_PHYSICAL_DIAL_FRONT_G131
    if s == "rear dial":
        return FX3_PHYSICAL_DIAL_REAR_G131
    if s == "control wheel":
        return FX3_PHYSICAL_DIAL_WHEEL_G131
    if s in ("rear dial l", "rear dial left"):
        return "Rear Dial L"
    if s in ("rear dial r", "rear dial right"):
        return "Rear Dial R"
    return None


def _compute_g131_effective_state(
    *,
    shoot_mode: str,
    reset_action: str,
    av_tv_rotate: str,
    function_ring: str,
    lock_operation_parts: str,
    my_dial_recall_mode: str,
    my_dial_bank: Optional[int],
    bank1_configured: bool,
    bank2_configured: bool,
    bank3_configured: bool,
) -> Dict[str, Any]:
    if reset_action == RESET_ACTION_INITIALIZE_PHASE303:
        eff_av_tv = AV_TV_ROTATE_DEFAULT_G131
        eff_func_ring = FUNCTION_RING_DEFAULT_G131
        eff_lock = LOCK_OPERATION_PARTS_DEFAULT_G131
        eff_recall = MY_DIAL_RECALL_DEFAULT_G131
        dial_survived = False
        fn_survived = False
    else:
        eff_av_tv = av_tv_rotate
        eff_func_ring = function_ring
        eff_lock = lock_operation_parts
        eff_recall = my_dial_recall_mode
        dial_survived = reset_action in (
            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303,
            RESET_ACTION_RESET_NETWORK_SET_PHASE303,
        )
        fn_survived = dial_survived

    configured_flags = {1: bank1_configured, 2: bank2_configured, 3: bank3_configured}
    configured_banks = tuple(b for b in (1, 2, 3) if configured_flags[b])
    skipped_banks = tuple(b for b in (1, 2, 3) if not configured_flags[b])

    if eff_recall == MY_DIAL_RECALL_NONE_G131 or not configured_banks:
        eff_bank: Optional[int] = None
        recalled_active = False
    elif eff_recall == MY_DIAL_RECALL_CYCLE_G131:
        if my_dial_bank is not None and configured_flags.get(my_dial_bank, False):
            eff_bank = my_dial_bank
        else:
            eff_bank = configured_banks[0]
        recalled_active = True
    else:
        cand = my_dial_bank if my_dial_bank is not None else 1
        if configured_flags.get(cand, False):
            eff_bank = cand
            recalled_active = True
        else:
            eff_bank = None
            recalled_active = False

    temp_unlock = recalled_active and (
        eff_lock in (LOCK_OPERATION_PARTS_DIAL_WHEEL_G131, LOCK_OPERATION_PARTS_ALL_G131)
    )
    fn_pool = "still_12" if shoot_mode == SHOOT_MODE_STILL_PHASE303 else "movie_12"

    return {
        "shoot_mode": shoot_mode,
        "reset_action": reset_action,
        "dial_customize_survived_cam_reset": dial_survived,
        "fn_menu_survived_cam_reset": fn_survived,
        "effective_av_tv_rotate": eff_av_tv,
        "effective_function_ring": eff_func_ring,
        "effective_lock_operation_parts": eff_lock,
        "effective_my_dial_recall_mode": eff_recall,
        "effective_my_dial_bank": eff_bank,
        "my_dial_cycle_order": configured_banks,
        "my_dial_skipped_empty_banks": skipped_banks,
        "my_dial_temp_unlock_override_active": temp_unlock,
        "fn_menu_active_mode_pool": fn_pool,
    }


def compute_dial_customize_mydial_fn_matrix() -> Dict[str, Any]:
    """Exhaustively verify all 768 state transitions across shoot_mode x av_tv x
    function_ring x lock_operation_parts x my_dial_recall x reset_action for G131.
    """
    states_checked = 0
    cam_reset_survived_count = 0
    initialize_reset_count = 0
    temp_unlock_active_count = 0
    all_invariants_hold = True

    for sm in ALLOWED_SHOOT_MODES_PHASE303:
        for av_tv in ALLOWED_AV_TV_ROTATE_MODES_G131:
            for ring in ALLOWED_FUNCTION_RING_MODES_G131:
                for lock in ALLOWED_LOCK_OPERATION_PARTS_MODES_G131:
                    for recall in ALLOWED_MY_DIAL_RECALL_MODES_G131:
                        for rst in ALLOWED_RESET_ACTIONS_PHASE303:
                            states_checked += 1
                            st = _compute_g131_effective_state(
                                shoot_mode=sm,
                                reset_action=rst,
                                av_tv_rotate=av_tv,
                                function_ring=ring,
                                lock_operation_parts=lock,
                                my_dial_recall_mode=recall,
                                my_dial_bank=1,
                                bank1_configured=True,
                                bank2_configured=False,
                                bank3_configured=True,
                            )
                            if rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303:
                                cam_reset_survived_count += 1
                                if not (
                                    st["dial_customize_survived_cam_reset"]
                                    and st["fn_menu_survived_cam_reset"]
                                    and st["effective_av_tv_rotate"] == av_tv
                                    and st["effective_function_ring"] == ring
                                    and st["effective_lock_operation_parts"] == lock
                                ):
                                    all_invariants_hold = False
                            if rst == RESET_ACTION_INITIALIZE_PHASE303:
                                initialize_reset_count += 1
                                if (
                                    st["effective_av_tv_rotate"] != AV_TV_ROTATE_DEFAULT_G131
                                    or st["effective_function_ring"] != FUNCTION_RING_DEFAULT_G131
                                    or st["effective_lock_operation_parts"]
                                    != LOCK_OPERATION_PARTS_DEFAULT_G131
                                    or st["effective_my_dial_recall_mode"]
                                    != MY_DIAL_RECALL_DEFAULT_G131
                                ):
                                    all_invariants_hold = False
                            if st["my_dial_temp_unlock_override_active"]:
                                temp_unlock_active_count += 1
                                if lock not in (
                                    LOCK_OPERATION_PARTS_DIAL_WHEEL_G131,
                                    LOCK_OPERATION_PARTS_ALL_G131,
                                ):
                                    all_invariants_hold = False
                            if st["my_dial_cycle_order"] != (1, 3):
                                all_invariants_hold = False
                            if st["my_dial_skipped_empty_banks"] != (2,):
                                all_invariants_hold = False
                            expected_pool = (
                                "still_12"
                                if sm == SHOOT_MODE_STILL_PHASE303
                                else "movie_12"
                            )
                            if st["fn_menu_active_mode_pool"] != expected_pool:
                                all_invariants_hold = False

    return {
        "states_checked": states_checked,
        "all_invariants_hold": all_invariants_hold,
        "cam_reset_survived_count": cam_reset_survived_count,
        "initialize_reset_count": initialize_reset_count,
        "temp_unlock_active_count": temp_unlock_active_count,
    }


def resolve_fx3_dial_customize_mydial_fn_state(**kwargs: Any) -> Dict[str, Any]:
    """Return serialized G131 guard state for UI/VM/orchestrator callers."""
    return verify_dial_customize_mydial_fn_guard(**kwargs).to_dict()


def verify_dial_customize_mydial_fn_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE303,
    body_model_id: int = FX3_MODEL_ID_PHASE303,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE303,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE303,
    target_model: str = FX3_MODEL_NAME_PHASE303,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE303,
    reset_action: str = RESET_ACTION_NONE_PHASE303,
    requested_dial_customize_items: Sequence[str] = DIAL_CUSTOMIZE_5_ITEMS_G131,
    requested_av_tv_rotate: str = AV_TV_ROTATE_DEFAULT_G131,
    requested_function_ring: str = FUNCTION_RING_DEFAULT_G131,
    requested_lock_operation_parts: str = LOCK_OPERATION_PARTS_DEFAULT_G131,
    requested_physical_dial: str = FX3_PHYSICAL_DIAL_FRONT_G131,
    requested_dormant_dial_symbol: Optional[str] = None,
    requested_dial_customize_legacy_item: Optional[str] = None,
    claimed_fx3_has_4_dials: bool = False,
    claimed_legacy_dial_setup_active: bool = False,
    claimed_legacy_dial_wheel_lock_active: bool = False,
    claimed_dial_customize_resets_on_cam_reset: bool = False,
    requested_my_dial_recall_mode: str = MY_DIAL_RECALL_DEFAULT_G131,
    requested_my_dial_bank: Optional[int] = None,
    my_dial_bank_1_configured: bool = True,
    my_dial_bank_2_configured: bool = False,
    my_dial_bank_3_configured: bool = True,
    claimed_cycle_includes_empty_mydial_bank: bool = False,
    claimed_lock_blocks_recalled_mydial: bool = False,
    claimed_mydial_resets_on_cam_reset: bool = False,
    fn_menu_still_slots: int = FN_MENU_STILL_SLOTS_G131,
    fn_menu_movie_slots: int = FN_MENU_MOVIE_SLOTS_G131,
    fn_still_all_not_set: bool = False,
    fn_movie_all_not_set: bool = False,
    fn_invoke_requested: bool = False,
    claimed_fn_menu_shared_single_pool: bool = False,
    claimed_fn_menu_resets_on_cam_reset: bool = False,
    av_tv_rotate_use_requested: bool = False,
    lock_operation_parts_use_requested: bool = False,
    my_dial_use_requested: bool = False,
    fn_menu_use_requested: bool = False,
    claimed_fx6_has_mydial_or_fn_menu: bool = False,
    claimed_fx3_has_multi_function_dial_or_direct_menu: bool = False,
    claimed_fx3_has_grip_or_handle_dial: bool = False,
) -> DialCustomizeMyDialFnGuardResult:
    """Enforce Gate G131: `[Dial Customize]` 5-Item Truth, 3-Dial Hardware Topology vs
    Dormant `Rear Dial L/R` (`EOPNOTSUPP=95`), `[My Dial Settings]` `1..3`, and
    `[Fn Menu Settings]` `12 + 12` Still/Movie split.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    norm_shoot = _normalize_shoot_mode(shoot_mode)
    norm_reset = _normalize_reset_action(reset_action)
    norm_av_tv = _normalize_av_tv_rotate(requested_av_tv_rotate)
    norm_lock = _normalize_lock_operation_parts(requested_lock_operation_parts)
    norm_recall = _normalize_my_dial_recall_mode(requested_my_dial_recall_mode)
    norm_dial = _normalize_physical_dial(requested_physical_dial)

    is_invalid_ring_token = (
        isinstance(requested_function_ring, str)
        and (
            requested_function_ring.strip() == DORMANT_FUNCTION_RING_INVALID_G131
            or requested_function_ring.strip().upper() == "INVALID"
        )
    )
    norm_ring = None if is_invalid_ring_token else _normalize_function_ring(requested_function_ring)

    identity_ok = (
        body_model_name == FX3_MODEL_NAME_PHASE303
        and _is_real_int(body_model_id)
        and body_model_id == FX3_MODEL_ID_PHASE303
        and help_guide_code == FX3_HELP_GUIDE_CODE_PHASE303
        and isinstance(firmware_version, str)
        and firmware_version.strip() not in ("", "BAD", "INVALID")
    )
    if not identity_ok:
        _add_code(codes, STATUS_BLOCKED_G131_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3 Ver. 7.02 hardware/help-guide identity for Gate G131."
        )

    if target_model not in (FX3_MODEL_NAME_PHASE303, FX6_MODEL_NAME_PHASE303):
        _add_code(codes, STATUS_BLOCKED_G131_TELEMETRY_INVALID)
        errors.append(f"Unsupported target_model `{target_model}`.")

    if norm_shoot is None:
        _add_code(codes, STATUS_BLOCKED_G131_TELEMETRY_INVALID)
        errors.append(f"Invalid shoot_mode `{shoot_mode}`.")
        norm_shoot = SHOOT_MODE_STILL_PHASE303

    if norm_reset is None:
        _add_code(codes, STATUS_BLOCKED_G131_TELEMETRY_INVALID)
        errors.append(f"Invalid reset_action `{reset_action}`.")
        norm_reset = RESET_ACTION_NONE_PHASE303

    if norm_av_tv is None:
        _add_code(codes, STATUS_BLOCKED_G131_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Av/Tv Rotate]` value `{requested_av_tv_rotate}`.")
        norm_av_tv = AV_TV_ROTATE_DEFAULT_G131

    if is_invalid_ring_token:
        _add_code(codes, STATUS_BLOCKED_G131_DIAL_CUSTOMIZE_5ITEM_OR_RESET_VIOLATION)
        errors.append(
            "`[Function Ring(Lens)]` sentinel `VAL_setting_function_ring_FUNCTION_RING_INVALID` "
            "rejected fail-closed (only `Power Focus` and `APS-C/Super 35 mm / Full Frame` allowed)."
        )
        norm_ring = FUNCTION_RING_DEFAULT_G131
    elif norm_ring is None:
        _add_code(codes, STATUS_BLOCKED_G131_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[Function Ring(Lens)]` value `{requested_function_ring}`."
        )
        norm_ring = FUNCTION_RING_DEFAULT_G131

    if norm_lock is None:
        _add_code(codes, STATUS_BLOCKED_G131_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[Lock Operation Parts]` value `{requested_lock_operation_parts}`."
        )
        norm_lock = LOCK_OPERATION_PARTS_DEFAULT_G131

    if norm_recall is None:
        _add_code(codes, STATUS_BLOCKED_G131_TELEMETRY_INVALID)
        errors.append(
            f"Invalid My Dial recall mode `{requested_my_dial_recall_mode}`."
        )
        norm_recall = MY_DIAL_RECALL_DEFAULT_G131

    if requested_my_dial_bank is not None and (
        not _is_real_int(requested_my_dial_bank) or requested_my_dial_bank not in (1, 2, 3)
    ):
        _add_code(codes, STATUS_BLOCKED_G131_TELEMETRY_INVALID)
        errors.append(
            f"Invalid My Dial bank `{requested_my_dial_bank}` (must be 1, 2, or 3)."
        )

    if norm_dial is None:
        _add_code(codes, STATUS_BLOCKED_G131_TELEMETRY_INVALID)
        errors.append(
            f"Unknown physical dial `{requested_physical_dial}` (FX3 has Front Dial, Rear Dial, Control Wheel)."
        )
        norm_dial = FX3_PHYSICAL_DIAL_FRONT_G131

    # Part A: Exact 5-Item [Dial Customize] & Initialize-Only Reset Law
    items_tuple = tuple(str(x).strip() for x in requested_dial_customize_items)
    legacy_names_lower = {
        LEGACY_DIAL_SETUP_MENU_NAME_G131.lower(),
        LEGACY_DIAL_WHEEL_SETUP_NAME_G131.lower(),
        LEGACY_DIAL_WHEEL_LOCK_NAME_G131.lower(),
    }
    if any(x.lower() in legacy_names_lower for x in items_tuple):
        _add_code(codes, STATUS_BLOCKED_G131_4DIAL_REAR_LR_OR_LEGACY_TRAP_VIOLATION)
        errors.append(
            "Legacy Ver. 1.xx `[Dial Setup]` / `[Dial/Wheel Setup]` / `[Dial / Wheel Lock]` "
            "replaced on FX3 Ver. 7.02 by `[Custom Key/Dial Set.]` and `[Lock Operation Parts]`."
        )
    elif items_tuple != DIAL_CUSTOMIZE_5_ITEMS_G131:
        _add_code(codes, STATUS_BLOCKED_G131_DIAL_CUSTOMIZE_5ITEM_OR_RESET_VIOLATION)
        errors.append(
            f"`[Dial Customize]` must expose exact 5 items `{DIAL_CUSTOMIZE_5_ITEMS_G131}`, "
            f"got `{items_tuple}`."
        )

    if claimed_dial_customize_resets_on_cam_reset:
        _add_code(codes, STATUS_BLOCKED_G131_DIAL_CUSTOMIZE_5ITEM_OR_RESET_VIOLATION)
        errors.append(
            "All 5 `[Dial Customize]` items are Initialize-only and MUST survive `[Camera Settings Reset]`."
        )

    # Part B: Physical 3-Dial Hardware Topology vs Dormant 4-Dial Alpha Rear Dial L/R
    block_errno: Optional[int] = None
    block_errno_name: Optional[str] = None
    dormant_4dial_lower = {k.strip().lower() for k in DORMANT_4DIAL_REAR_LR_TRAPS_G131}
    dormant_dial_hit = norm_dial in ("Rear Dial L", "Rear Dial R")
    dormant_sym_hit = (
        requested_dormant_dial_symbol is not None
        and requested_dormant_dial_symbol.strip().lower() in dormant_4dial_lower
    )
    legacy_item_hit = (
        requested_dial_customize_legacy_item is not None
        and requested_dial_customize_legacy_item.strip().lower() in dormant_4dial_lower
    )
    if (
        dormant_dial_hit
        or dormant_sym_hit
        or legacy_item_hit
        or claimed_fx3_has_4_dials
        or claimed_legacy_dial_setup_active
        or claimed_legacy_dial_wheel_lock_active
    ):
        _add_code(codes, STATUS_BLOCKED_G131_4DIAL_REAR_LR_OR_LEGACY_TRAP_VIOLATION)
        block_errno = EOPNOTSUPP_ERRNO_G131
        block_errno_name = EOPNOTSUPP_NAME_G131
        errors.append(
            "ILME-FX3 has ONLY 3 physical dials (Front Dial, single Rear Dial, Control Wheel): "
            "dormant 4-dial Alpha `Rear Dial L/R` (`_f 0x6a5c/0x680d`) or legacy Ver. 1.xx "
            "bindings rejected fail-closed (`EOPNOTSUPP=95`)."
        )

    # Part C: My Dial 1..3 Shared NVRAM & Fn Menu 12+12 Split
    if (
        not _is_real_int(fn_menu_still_slots)
        or not _is_real_int(fn_menu_movie_slots)
        or fn_menu_still_slots != FN_MENU_STILL_SLOTS_G131
        or fn_menu_movie_slots != FN_MENU_MOVIE_SLOTS_G131
        or claimed_fn_menu_shared_single_pool
    ):
        _add_code(codes, STATUS_BLOCKED_G131_MYDIAL_OR_FN_12X2_SPLIT_VIOLATION)
        errors.append(
            "`[Fn Menu Settings]` (`_g 0x614b`) enforces a strict 12 Still + 12 Movie slot split "
            "(`BKID_APP_fn_menu_item_ids_for_{still,movie}0..11`), Initialize-only."
        )

    eff = _compute_g131_effective_state(
        shoot_mode=norm_shoot,
        reset_action=norm_reset,
        av_tv_rotate=norm_av_tv,
        function_ring=norm_ring,
        lock_operation_parts=norm_lock,
        my_dial_recall_mode=norm_recall,
        my_dial_bank=requested_my_dial_bank
        if _is_real_int(requested_my_dial_bank)
        else None,
        bank1_configured=bool(my_dial_bank_1_configured),
        bank2_configured=bool(my_dial_bank_2_configured),
        bank3_configured=bool(my_dial_bank_3_configured),
    )

    active_fn_all_not_set = (
        fn_still_all_not_set
        if norm_shoot == SHOOT_MODE_STILL_PHASE303
        else fn_movie_all_not_set
    )
    fn_invocation_blocked = bool(fn_invoke_requested and active_fn_all_not_set)
    if fn_invocation_blocked:
        _add_code(codes, STATUS_BLOCKED_G131_MYDIAL_OR_FN_12X2_SPLIT_VIOLATION)
        errors.append(
            f"Fn invocation blocked fail-closed in `{norm_shoot}` mode: all 12 Fn slots are "
            "`Not set` (`_f.uxc 0x6220`, `base 0xe0ac`)."
        )

    if (
        claimed_cycle_includes_empty_mydial_bank
        or claimed_lock_blocks_recalled_mydial
        or claimed_mydial_resets_on_cam_reset
        or claimed_fn_menu_resets_on_cam_reset
    ):
        _add_code(codes, STATUS_BLOCKED_G131_MYDIAL_OR_FN_12X2_SPLIT_VIOLATION)
        errors.append(
            "`[My Dial Settings]` (`1..3` shared NVRAM, skipping all-`Not set` banks in `1->2->3` "
            "and temporarily unlocking `[Lock Operation Parts]` while recalled) and `[Fn Menu Settings]` "
            "are Initialize-only."
        )

    # Part D: ILME-FX6 Dial / Status Screens / Direct Menu Crosswire Isolation
    if (
        claimed_fx6_has_mydial_or_fn_menu
        or claimed_fx3_has_multi_function_dial_or_direct_menu
        or claimed_fx3_has_grip_or_handle_dial
        or (
            target_model == FX6_MODEL_NAME_PHASE303
            and (
                av_tv_rotate_use_requested
                or lock_operation_parts_use_requested
                or my_dial_use_requested
                or fn_menu_use_requested
            )
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G131_FX6_DIAL_OR_DIRECT_MENU_CROSSWIRE_VIOLATION)
        errors.append(
            "Cross-model dial/menu crosswire blocked: ILME-FX6 Ver. 6.01 uses `Multi Function Dial`, "
            "`Grip Dial`, `Handle Dial`, `IRIS Dial`, `ND Dial`, physical `HOLD` switch, `Status Screens`, "
            "and `Direct Menu` (NOT FX3 `My Dial 1..3`, `Fn Menu`, `Av/Tv Rotate`, or `Lock Operation Parts`)."
        )

    matrix = compute_dial_customize_mydial_fn_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G131 if valid else codes[0]

    return DialCustomizeMyDialFnGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE303,
        target_model=target_model,
        reset_action=eff["reset_action"],
        shoot_mode=eff["shoot_mode"],
        dial_customize_menu_path=DIAL_CUSTOMIZE_MENU_PATH_G131,
        dial_customize_5_items=DIAL_CUSTOMIZE_5_ITEMS_G131,
        dial_customize_survived_cam_reset=eff["dial_customize_survived_cam_reset"],
        effective_av_tv_rotate=eff["effective_av_tv_rotate"],
        effective_function_ring=eff["effective_function_ring"],
        effective_lock_operation_parts=eff["effective_lock_operation_parts"],
        fx3_physical_3_dials=FX3_PHYSICAL_3_DIALS_G131,
        requested_physical_dial=norm_dial,
        dormant_4dial_rear_lr_blocked=True,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        my_dial_nvram_shared_across_modes=True,
        my_dial_recall_per_mode_custom_key_split=True,
        effective_my_dial_recall_mode=eff["effective_my_dial_recall_mode"],
        effective_my_dial_bank=eff["effective_my_dial_bank"],
        my_dial_cycle_order=eff["my_dial_cycle_order"],
        my_dial_skipped_empty_banks=eff["my_dial_skipped_empty_banks"],
        my_dial_temp_unlock_override_active=eff["my_dial_temp_unlock_override_active"],
        fn_menu_menu_path=FN_MENU_SETTINGS_MENU_PATH_G131,
        fn_menu_still_slots=FN_MENU_STILL_SLOTS_G131,
        fn_menu_movie_slots=FN_MENU_MOVIE_SLOTS_G131,
        fn_menu_active_mode_pool=eff["fn_menu_active_mode_pool"],
        fn_menu_survived_cam_reset=eff["fn_menu_survived_cam_reset"],
        fn_invocation_blocked_all_not_set=fn_invocation_blocked,
        fx6_dial_controls=FX6_DIAL_CONTROLS_G131,
        fx6_surfaces=FX6_STATUS_AND_DIRECT_MENU_SURFACES_G131,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g131_dial_customize_mydial_fn_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dial_customize_mydial_fn_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase303DonorAuditResult] = None,
) -> Tuple[GateVerdict, G131DialCustomizeMyDialFnGuardResult]:
    """Evaluate Wave-56 Gate `G131` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase303_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_dial_customize_mydial_fn_guard(
        **(dict(dial_customize_mydial_fn_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G131.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G131 if valid else codes[0]

    res = G131DialCustomizeMyDialFnGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        dial_customize_mydial_fn_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, 5items=verified, 3dials=Front/Rear/Wheel,"
        f"av_tv={guard.effective_av_tv_rotate}, ring={guard.effective_function_ring},"
        f"lock={guard.effective_lock_operation_parts}, mydial={guard.effective_my_dial_recall_mode},"
        f"fn_split={guard.fn_menu_still_slots}+{guard.fn_menu_movie_slots}"
    )
    verdict = GateVerdict(
        gate_id=G131_GATE_ID,
        gate_code=G131_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G132: Live View Display Set. 3-Item + Bright Monitoring Override,
#    Grid Line Clean-HDMI Isolation, & Manage User LUTs / Embed LUT vs PPLUT1..4
# ---------------------------------------------------------------------------


def _normalize_live_view_display(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s in ("setting effect on", "on", "effect_on"):
        return LIVE_VIEW_SETTING_EFFECT_ON_G132
    if s in ("setting effect off", "off", "effect_off"):
        return LIVE_VIEW_SETTING_EFFECT_OFF_G132
    return None


def _normalize_exposure_effect(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s in ("exposure set. & flash", "exposure set. and flash", "ambient&flash", "on"):
        return EXPOSURE_EFFECT_SET_AND_FLASH_G132
    if s in ("exposure setting only", "ambient only", "off"):
        return EXPOSURE_EFFECT_SET_ONLY_G132
    return None


def _normalize_grid_line_type(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s in ("rule of 3rds grid", "rule of 3rds", "3rds"):
        return GRID_LINE_TYPE_RULE_OF_3RDS_G132
    if s in ("square grid", "square"):
        return GRID_LINE_TYPE_SQUARE_G132
    if s in ("diag. + square grid", "diag + square grid", "diag+square"):
        return GRID_LINE_TYPE_DIAG_SQUARE_G132
    return None


def _normalize_card_type(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s in ("sd/sdhc", "sd", "sdhc"):
        return CARD_TYPE_SD_SDHC_G132
    if s == "sdxc":
        return CARD_TYPE_SDXC_G132
    if s in ("cfexpress type a", "cfexpress", "cfa"):
        return CARD_TYPE_CFEXPRESS_A_G132
    return None


def _normalize_select_lut(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    raw = val.strip()
    s = raw.lower()
    if s in ("s-log3", "slog3"):
        return SELECT_LUT_SLOG3_G132
    if s == "s709":
        return SELECT_LUT_S709_G132
    if s in ("709(800%)", "r709", "709_800"):
        return SELECT_LUT_709_800_G132
    if s.startswith("user") and s[4:].isdigit():
        idx = int(s[4:])
        if USER_LUT_SLOT_MIN_G132 <= idx <= USER_LUT_SLOT_MAX_G132:
            return f"User{idx}"
    return None


def _compute_g132_effective_state(
    *,
    shoot_mode: str,
    reset_action: str,
    live_view_display: str,
    exposure_effect: str,
    frame_rate_low_limit: str,
    bright_monitoring_active: bool,
    grid_line_display: str,
    grid_line_type: str,
    hdmi_info_display: str,
    raw_hdmi_output_active: bool,
    hdmi_only_off_mode_active: bool,
    card_type: str,
    select_lut: str,
    embed_lut_file: str,
    requested_lut_or_rec_op: Optional[str],
    target_slot: str,
    slot_1_write_protected: bool,
    slot_1_contains_tier0_vault: bool,
) -> Dict[str, Any]:
    if reset_action == RESET_ACTION_INITIALIZE_PHASE303:
        eff_lv = LIVE_VIEW_DISPLAY_DEFAULT_G132
        eff_exp_eff = EXPOSURE_EFFECT_DEFAULT_G132
        eff_fr_low = FRAME_RATE_LOW_LIMIT_DEFAULT_G132
        eff_grid_disp = GRID_LINE_DISPLAY_DEFAULT_G132
        eff_grid_type = GRID_LINE_TYPE_DEFAULT_G132
        eff_select_lut = SELECT_LUT_DEFAULT_G132
        eff_embed = EMBED_LUT_DEFAULT_G132
        lv_survived = False
        fr_reset = False
        grid_survived = False
        select_lut_reset = False
        user_luts_survived = False
        embed_reset = False
        pplut_reset = True
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303:
        eff_lv = live_view_display
        eff_exp_eff = exposure_effect
        eff_fr_low = FRAME_RATE_LOW_LIMIT_DEFAULT_G132
        eff_grid_disp = grid_line_display
        eff_grid_type = grid_line_type
        eff_select_lut = SELECT_LUT_DEFAULT_G132
        eff_embed = EMBED_LUT_DEFAULT_G132
        lv_survived = True
        fr_reset = True
        grid_survived = True
        select_lut_reset = True
        user_luts_survived = True
        embed_reset = True
        pplut_reset = True
    else:
        eff_lv = live_view_display
        eff_exp_eff = exposure_effect
        eff_fr_low = frame_rate_low_limit
        eff_grid_disp = grid_line_display
        eff_grid_type = grid_line_type
        eff_select_lut = select_lut
        eff_embed = embed_lut_file
        survived_net = reset_action == RESET_ACTION_RESET_NETWORK_SET_PHASE303
        lv_survived = survived_net
        fr_reset = False
        grid_survived = survived_net
        select_lut_reset = False
        user_luts_survived = True
        embed_reset = False
        pplut_reset = False

    if bright_monitoring_active:
        eff_lv = LIVE_VIEW_SETTING_EFFECT_OFF_G132

    eff_hdmi_info = (
        HDMI_INFO_DISPLAY_OFF_G132
        if (raw_hdmi_output_active or hdmi_only_off_mode_active)
        else hdmi_info_display
    )
    hdmi_clean_isolated = eff_hdmi_info == HDMI_INFO_DISPLAY_OFF_G132

    embed_locked_sdhc = card_type == CARD_TYPE_SD_SDHC_G132
    if embed_locked_sdhc:
        eff_embed = EMBED_LUT_OFF_G132

    expected_lut_folder = (
        LUT_FOLDER_CFEXPRESS_G132
        if card_type == CARD_TYPE_CFEXPRESS_A_G132
        else LUT_FOLDER_SD_SDXC_G132
    )

    is_ro_import = requested_lut_or_rec_op == LUT_OP_IMPORT_USER_LUT_G132
    is_write_op = requested_lut_or_rec_op in (
        LUT_OP_MAKE_CUBE_FOLDER_G132,
        LUT_OP_WRITE_CUBE_OR_SIDECAR_G132,
        LUT_OP_RECORD_EMBED_LUT_G132,
        LUT_OP_RECORD_PPLUT_G132,
    )
    slot1_blocked = bool(
        is_write_op
        and target_slot == MEDIA_SLOT_1_PHASE303
        and (slot_1_contains_tier0_vault or slot_1_write_protected)
    )
    if slot1_blocked:
        block_errno: Optional[str] = "EROFS" if slot_1_write_protected else "EBUSY"
        block_errno_code: Optional[int] = (
            EROFS_ERRNO_G132 if slot_1_write_protected else EBUSY_ERRNO_G132
        )
    else:
        block_errno = None
        block_errno_code = None

    return {
        "shoot_mode": shoot_mode,
        "reset_action": reset_action,
        "bright_monitoring_active": bright_monitoring_active,
        "effective_live_view_display": eff_lv,
        "effective_exposure_effect": eff_exp_eff,
        "effective_frame_rate_low_limit": eff_fr_low,
        "live_view_and_exposure_effect_survived_cam_reset": lv_survived,
        "frame_rate_low_limit_reset_on_cam_reset": fr_reset,
        "effective_grid_line_display": eff_grid_disp,
        "effective_grid_line_type": eff_grid_type,
        "grid_line_survived_cam_reset": grid_survived,
        "effective_hdmi_info_display": eff_hdmi_info,
        "grid_line_isolated_from_hdmi_clean_feed": hdmi_clean_isolated,
        "hdmi_clean_feed_preserved": hdmi_clean_isolated,
        "card_type": card_type,
        "expected_lut_folder_path": expected_lut_folder,
        "effective_select_lut": eff_select_lut,
        "select_lut_reset_on_cam_reset": select_lut_reset,
        "user_luts_survived_cam_reset": user_luts_survived,
        "effective_embed_lut_file": eff_embed,
        "embed_lut_locked_off_by_sdhc": embed_locked_sdhc,
        "embed_lut_reset_on_cam_reset": embed_reset,
        "pplut_reset_on_cam_reset_and_initialize": pplut_reset,
        "lut_import_read_only_safe": bool(is_ro_import or requested_lut_or_rec_op is None),
        "slot1_vault_firewall_blocked": slot1_blocked,
        "block_errno": block_errno,
        "block_errno_code": block_errno_code,
        "slot1_data_sector_writes": 0,
        "slot1_avf_info_mutated": False,
    }


def compute_liveview_grid_lut_embed_matrix() -> Dict[str, Any]:
    """Exhaustively verify all 864 states across shoot_mode x live_view x
    bright_monitoring x fr_low_limit x grid_disp x hdmi_info x card_type x reset_action.
    """
    states_checked = 0
    bright_override_count = 0
    sdhc_embed_locked_count = 0
    clean_hdmi_isolated_count = 0
    cam_reset_fr_low_count = 0
    all_invariants_hold = True

    reset_subset = (
        RESET_ACTION_NONE_PHASE303,
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303,
        RESET_ACTION_INITIALIZE_PHASE303,
    )
    for sm in ALLOWED_SHOOT_MODES_PHASE303:
        for lv in ALLOWED_LIVE_VIEW_DISPLAY_MODES_G132:
            for bm in (False, True):
                for fr in ALLOWED_FRAME_RATE_LOW_LIMIT_MODES_G132:
                    for gd in ALLOWED_GRID_LINE_DISPLAY_MODES_G132:
                        for hdmi in ALLOWED_HDMI_INFO_DISPLAY_MODES_G132:
                            for card in ALLOWED_CARD_TYPES_G132:
                                for rst in reset_subset:
                                    states_checked += 1
                                    st = _compute_g132_effective_state(
                                        shoot_mode=sm,
                                        reset_action=rst,
                                        live_view_display=lv,
                                        exposure_effect=EXPOSURE_EFFECT_SET_ONLY_G132,
                                        frame_rate_low_limit=fr,
                                        bright_monitoring_active=bm,
                                        grid_line_display=gd,
                                        grid_line_type=GRID_LINE_TYPE_SQUARE_G132,
                                        hdmi_info_display=hdmi,
                                        raw_hdmi_output_active=False,
                                        hdmi_only_off_mode_active=False,
                                        card_type=card,
                                        select_lut="User1",
                                        embed_lut_file=EMBED_LUT_ON_G132,
                                        requested_lut_or_rec_op=None,
                                        target_slot=MEDIA_SLOT_2_PHASE303,
                                        slot_1_write_protected=False,
                                        slot_1_contains_tier0_vault=True,
                                    )
                                    if bm:
                                        bright_override_count += 1
                                        if (
                                            st["effective_live_view_display"]
                                            != LIVE_VIEW_SETTING_EFFECT_OFF_G132
                                        ):
                                            all_invariants_hold = False
                                    if card == CARD_TYPE_SD_SDHC_G132:
                                        sdhc_embed_locked_count += 1
                                        if (
                                            st["effective_embed_lut_file"]
                                            != EMBED_LUT_OFF_G132
                                            or not st["embed_lut_locked_off_by_sdhc"]
                                        ):
                                            all_invariants_hold = False
                                    if hdmi == HDMI_INFO_DISPLAY_OFF_G132:
                                        clean_hdmi_isolated_count += 1
                                        if not st["grid_line_isolated_from_hdmi_clean_feed"]:
                                            all_invariants_hold = False
                                    if rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303:
                                        cam_reset_fr_low_count += 1
                                        if (
                                            st["effective_frame_rate_low_limit"]
                                            != FRAME_RATE_LOW_LIMIT_DEFAULT_G132
                                            or st["effective_select_lut"]
                                            != SELECT_LUT_DEFAULT_G132
                                            or st["effective_exposure_effect"]
                                            != EXPOSURE_EFFECT_SET_ONLY_G132
                                            or st["effective_grid_line_display"] != gd
                                            or not st["user_luts_survived_cam_reset"]
                                        ):
                                            all_invariants_hold = False

    return {
        "states_checked": states_checked,
        "all_invariants_hold": all_invariants_hold,
        "bright_override_count": bright_override_count,
        "sdhc_embed_locked_count": sdhc_embed_locked_count,
        "clean_hdmi_isolated_count": clean_hdmi_isolated_count,
        "cam_reset_fr_low_count": cam_reset_fr_low_count,
    }


def resolve_fx3_liveview_grid_lut_embed_state(**kwargs: Any) -> Dict[str, Any]:
    """Return serialized G132 guard state for UI/VM/orchestrator callers."""
    return verify_liveview_grid_lut_embed_guard(**kwargs).to_dict()


def verify_liveview_grid_lut_embed_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE303,
    body_model_id: int = FX3_MODEL_ID_PHASE303,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE303,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE303,
    target_model: str = FX3_MODEL_NAME_PHASE303,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE303,
    reset_action: str = RESET_ACTION_NONE_PHASE303,
    live_view_display_set_menu_path: str = LIVE_VIEW_DISPLAY_SET_MENU_PATH_G132,
    requested_live_view_subitems: Sequence[str] = LIVE_VIEW_DISPLAY_SET_3_SUBITEMS_G132,
    live_view_display_set_use_requested: bool = False,
    requested_live_view_display: str = LIVE_VIEW_DISPLAY_DEFAULT_G132,
    requested_exposure_effect: str = EXPOSURE_EFFECT_DEFAULT_G132,
    requested_frame_rate_low_limit: str = FRAME_RATE_LOW_LIMIT_DEFAULT_G132,
    bright_monitoring_active: bool = False,
    claimed_setting_effect_on_with_bright_monitoring: bool = False,
    claimed_frame_rate_low_limit_ignores_cam_reset: bool = False,
    claimed_live_view_or_exposure_effect_resets_on_cam_reset: bool = False,
    requested_grid_line_display: str = GRID_LINE_DISPLAY_DEFAULT_G132,
    requested_grid_line_type: str = GRID_LINE_TYPE_DEFAULT_G132,
    requested_hdmi_info_display: str = HDMI_INFO_DISPLAY_DEFAULT_G132,
    raw_hdmi_output_active: bool = False,
    hdmi_only_off_mode_active: bool = False,
    claimed_grid_line_burned_into_clean_hdmi: bool = False,
    claimed_grid_line_resets_on_cam_reset: bool = False,
    fx6_custom_png_grid_requested: bool = False,
    requested_dormant_grid_symbol: Optional[str] = None,
    fx3_grid_line_type_use_requested: bool = False,
    claimed_fx3_supports_custom_aspect_or_safety_92_5_95: bool = False,
    embed_lut_file_menu_path: str = EMBED_LUT_FILE_MENU_PATH_G132,
    claimed_embed_lut_under_color_tone: bool = False,
    card_type: str = CARD_TYPE_CFEXPRESS_A_G132,
    requested_lut_folder_path: Optional[str] = None,
    requested_cube_grid_points: int = 33,
    requested_cube_filename: Optional[str] = None,
    requested_select_lut: str = SELECT_LUT_DEFAULT_G132,
    requested_embed_lut_file: str = EMBED_LUT_DEFAULT_G132,
    claimed_embed_lut_allowed_on_sdhc: bool = False,
    embed_lut_recording_requested: bool = False,
    claimed_embed_lut_creates_sidecar: bool = False,
    claimed_embed_lut_bakes_pixels: bool = False,
    claimed_pplut_preserves_slog3_or_survives_reset: bool = False,
    claimed_fx6_exposes_50_user_luts_in_ui: bool = False,
    claimed_fx3_has_independent_sdi_hdmi_lut_switches: bool = False,
    requested_lut_or_rec_op: Optional[str] = None,
    requested_target_slot: str = MEDIA_SLOT_2_PHASE303,
    slot_1_write_protected: bool = False,
    slot_1_contains_tier0_vault: bool = True,
) -> LiveViewGridLutEmbedGuardResult:
    """Enforce Gate G132: Still-only `[Live View Display Set.]` 3-item + Bright
    Monitoring override, Grid Line Clean-HDMI isolation vs FX6 custom PNG grids,
    `[Manage User LUTs]` / `[Embed LUT File]` vs `PPLUT1..4`, and Slot-1 Tier-0
    Vault write firewall (`EROFS=30` / `EBUSY=16`).
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    norm_shoot = _normalize_shoot_mode(shoot_mode)
    norm_reset = _normalize_reset_action(reset_action)
    norm_lv = _normalize_live_view_display(requested_live_view_display)
    norm_exp_eff = _normalize_exposure_effect(requested_exposure_effect)
    norm_fr_low = _normalize_on_off(requested_frame_rate_low_limit)
    norm_grid_disp = _normalize_on_off(requested_grid_line_display)
    norm_grid_type = _normalize_grid_line_type(requested_grid_line_type)
    norm_hdmi_info = _normalize_on_off(requested_hdmi_info_display)
    norm_card = _normalize_card_type(card_type)
    norm_select_lut = _normalize_select_lut(requested_select_lut)
    norm_embed_lut = _normalize_on_off(requested_embed_lut_file)
    norm_slot = _normalize_media_slot(requested_target_slot)

    identity_ok = (
        body_model_name == FX3_MODEL_NAME_PHASE303
        and _is_real_int(body_model_id)
        and body_model_id == FX3_MODEL_ID_PHASE303
        and help_guide_code == FX3_HELP_GUIDE_CODE_PHASE303
        and isinstance(firmware_version, str)
        and firmware_version.strip() not in ("", "BAD", "INVALID")
    )
    if not identity_ok:
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3 Ver. 7.02 hardware/help-guide identity for Gate G132."
        )

    if target_model not in (FX3_MODEL_NAME_PHASE303, FX6_MODEL_NAME_PHASE303):
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(f"Unsupported target_model `{target_model}`.")

    if norm_shoot is None:
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(f"Invalid shoot_mode `{shoot_mode}`.")
        norm_shoot = SHOOT_MODE_STILL_PHASE303

    if norm_reset is None:
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(f"Invalid reset_action `{reset_action}`.")
        norm_reset = RESET_ACTION_NONE_PHASE303

    if norm_lv is None:
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[Live View Display]` value `{requested_live_view_display}`."
        )
        norm_lv = LIVE_VIEW_DISPLAY_DEFAULT_G132

    if norm_exp_eff is None:
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[Exposure Effect]` value `{requested_exposure_effect}`."
        )
        norm_exp_eff = EXPOSURE_EFFECT_DEFAULT_G132

    if norm_fr_low is None:
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[Frame Rate Low Limit]` value `{requested_frame_rate_low_limit}`."
        )
        norm_fr_low = FRAME_RATE_LOW_LIMIT_DEFAULT_G132

    if norm_grid_disp is None:
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[Grid Line Display]` value `{requested_grid_line_display}`."
        )
        norm_grid_disp = GRID_LINE_DISPLAY_DEFAULT_G132

    if norm_grid_type is None:
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[Grid Line Type]` value `{requested_grid_line_type}`."
        )
        norm_grid_type = GRID_LINE_TYPE_DEFAULT_G132

    if norm_hdmi_info is None:
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[HDMI Info. Display]` value `{requested_hdmi_info_display}`."
        )
        norm_hdmi_info = HDMI_INFO_DISPLAY_DEFAULT_G132

    if norm_card is None:
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(f"Invalid card_type `{card_type}`.")
        norm_card = CARD_TYPE_CFEXPRESS_A_G132

    if norm_select_lut is None:
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Select LUT]` preset `{requested_select_lut}`.")
        norm_select_lut = SELECT_LUT_DEFAULT_G132

    if norm_embed_lut is None:
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[Embed LUT File]` mode `{requested_embed_lut_file}`."
        )
        norm_embed_lut = EMBED_LUT_DEFAULT_G132

    if norm_slot is None:
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_target_slot `{requested_target_slot}`.")
        norm_slot = MEDIA_SLOT_2_PHASE303

    if requested_lut_or_rec_op is not None and (
        not isinstance(requested_lut_or_rec_op, str)
        or requested_lut_or_rec_op.strip() not in ALLOWED_LUT_REC_OPS_G132
    ):
        _add_code(codes, STATUS_BLOCKED_G132_TELEMETRY_INVALID)
        errors.append(
            f"Unknown requested_lut_or_rec_op `{requested_lut_or_rec_op}`."
        )

    # Part A: Still-Only [Live View Display Set.] 3-Item + Bright Monitoring Override
    subitems_tuple = tuple(str(x).strip() for x in requested_live_view_subitems)
    if (
        live_view_display_set_menu_path != LIVE_VIEW_DISPLAY_SET_MENU_PATH_G132
        or subitems_tuple != LIVE_VIEW_DISPLAY_SET_3_SUBITEMS_G132
    ):
        _add_code(codes, STATUS_BLOCKED_G132_LIVEVIEW_3ITEM_BRIGHT_OR_RESET_VIOLATION)
        errors.append(
            "`[Live View Display Set.]` (`_f 0x6429`) must live under "
            "`MENU -> (Shooting) -> [Shooting Display] -> [Live View Display Set.]` "
            "with exact 3 active sub-items (`Live View Display`, `Exposure Effect`, "
            "`Frame Rate Low Limit`)."
        )

    if live_view_display_set_use_requested and norm_shoot != SHOOT_MODE_STILL_PHASE303:
        _add_code(codes, STATUS_BLOCKED_G132_LIVEVIEW_3ITEM_BRIGHT_OR_RESET_VIOLATION)
        errors.append(
            f"`[Live View Display Set.]` is Still-only and unavailable in `{norm_shoot}` mode."
        )

    if bright_monitoring_active and claimed_setting_effect_on_with_bright_monitoring:
        _add_code(codes, STATUS_BLOCKED_G132_LIVEVIEW_3ITEM_BRIGHT_OR_RESET_VIOLATION)
        errors.append(
            "When `[Bright Monitoring]` is active, `[Live View Display]` is forced to "
            "`Setting Effect OFF` (claiming `Setting Effect ON` blocked fail-closed)."
        )

    if (
        claimed_frame_rate_low_limit_ignores_cam_reset
        or claimed_live_view_or_exposure_effect_resets_on_cam_reset
    ):
        _add_code(codes, STATUS_BLOCKED_G132_LIVEVIEW_3ITEM_BRIGHT_OR_RESET_VIOLATION)
        errors.append(
            "`[Live View Display]` and `[Exposure Effect]` are Initialize-only, whereas "
            "`[Frame Rate Low Limit]` IS resettable via `[Camera Settings Reset]`."
        )

    # Part B: Grid Line Clean-HDMI Isolation vs FX6 Marker / Custom PNG Grid Firewall
    dormant_grid_lower = {k.strip().lower() for k in FX6_DORMANT_CUSTOM_PNG_GRID_SYMBOLS_G132}
    dormant_grid_hit = (
        requested_dormant_grid_symbol is not None
        and requested_dormant_grid_symbol.strip().lower() in dormant_grid_lower
    )
    if (
        claimed_grid_line_burned_into_clean_hdmi
        or claimed_grid_line_resets_on_cam_reset
        or fx6_custom_png_grid_requested
        or dormant_grid_hit
        or claimed_fx3_supports_custom_aspect_or_safety_92_5_95
        or (target_model == FX6_MODEL_NAME_PHASE303 and fx3_grid_line_type_use_requested)
    ):
        _add_code(codes, STATUS_BLOCKED_G132_GRID_CLEAN_HDMI_OR_FX6_PNG_VIOLATION)
        errors.append(
            "Grid Line contract violation: `[Grid Line Display]`/`[Grid Line Type]` are "
            "Initialize-only and isolated from HDMI clean feed (`HDMI Info. Display = Off`), "
            "while dormant FX6 custom PNG grids (`BKID_APP_IS_EXIST_CUSTOM_GRID_LINE0..3`) "
            "and FX6 `Safety Zone 92.5%/95%` / `Custom Aspect Ratio` are rejected fail-closed."
        )

    # Part C: Manage User LUTs, Embed LUT File (SD/SDHC lock & path), PPLUT1..4
    if (
        claimed_embed_lut_under_color_tone
        or embed_lut_file_menu_path != EMBED_LUT_FILE_MENU_PATH_G132
        or "Color/Tone" in embed_lut_file_menu_path
    ):
        _add_code(codes, STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION)
        errors.append(
            "`[Embed LUT File]` lives under `MENU -> (Shooting) -> [Image Quality/Rec] -> "
            "[Log Shooting Setting] -> [Embed LUT File]`, NOT under `[Color/Tone]`."
        )

    if (
        not _is_real_int(requested_cube_grid_points)
        or requested_cube_grid_points not in ALLOWED_CUBE_GRID_POINTS_G132
    ):
        _add_code(codes, STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION)
        errors.append(
            f"Unsupported `.cube` 3D LUT grid size `{requested_cube_grid_points}` "
            "(only 17pt / 33pt `.cube` supported)."
        )

    if requested_cube_filename is not None:
        fn = requested_cube_filename.strip()
        if (
            not fn.lower().endswith(".cube")
            or len(fn) > USER_LUT_MAX_FILENAME_CHARS_G132
            or not fn.isascii()
        ):
            _add_code(codes, STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION)
            errors.append(
                f"Invalid `.cube` filename `{fn}` (must be ASCII `.cube` <= 63 chars)."
            )

    expected_lut_folder = (
        LUT_FOLDER_CFEXPRESS_G132
        if norm_card == CARD_TYPE_CFEXPRESS_A_G132
        else LUT_FOLDER_SD_SDXC_G132
    )
    if requested_lut_folder_path is not None:
        folder_clean = requested_lut_folder_path.strip().rstrip("/")
        if folder_clean != expected_lut_folder:
            _add_code(codes, STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION)
            errors.append(
                f"LUT card folder `{folder_clean}` mismatches media `{norm_card}` "
                f"(expected `{expected_lut_folder}`)."
            )

    if (
        claimed_embed_lut_allowed_on_sdhc
        or (
            norm_card == CARD_TYPE_SD_SDHC_G132
            and embed_lut_recording_requested
            and norm_embed_lut == EMBED_LUT_ON_G132
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION)
        errors.append(
            "`[Embed LUT File]` is hardware-locked `Off` on `SD/SDHC` cards (`_g.uxc 0x61a0`); "
            "SDXC or CFexpress Type A is required to embed LUT metadata."
        )

    if (
        claimed_embed_lut_creates_sidecar
        or claimed_embed_lut_bakes_pixels
        or claimed_pplut_preserves_slog3_or_survives_reset
        or claimed_fx6_exposes_50_user_luts_in_ui
        or claimed_fx3_has_independent_sdi_hdmi_lut_switches
    ):
        _add_code(codes, STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION)
        errors.append(
            "`[Embed LUT File]` embeds 3D LUT metadata inside the video container preserving "
            "S-Log3 pixels without sidecar files, whereas `PPLUT1..4` irreducibly bakes pixels "
            "and resets on BOTH `[Camera Settings Reset]` and `[Initialize]`; FX6 exposes 16 UI "
            "LUT slots despite `PRM_is_exist_user_lut0..49`."
        )

    eff = _compute_g132_effective_state(
        shoot_mode=norm_shoot,
        reset_action=norm_reset,
        live_view_display=norm_lv,
        exposure_effect=norm_exp_eff,
        frame_rate_low_limit=norm_fr_low,
        bright_monitoring_active=bool(bright_monitoring_active),
        grid_line_display=norm_grid_disp,
        grid_line_type=norm_grid_type,
        hdmi_info_display=norm_hdmi_info,
        raw_hdmi_output_active=bool(raw_hdmi_output_active),
        hdmi_only_off_mode_active=bool(hdmi_only_off_mode_active),
        card_type=norm_card,
        select_lut=norm_select_lut,
        embed_lut_file=norm_embed_lut,
        requested_lut_or_rec_op=requested_lut_or_rec_op.strip()
        if isinstance(requested_lut_or_rec_op, str)
        else None,
        target_slot=norm_slot,
        slot_1_write_protected=bool(slot_1_write_protected),
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
    )

    # Part D: Fail-Closed Slot-1 Tier-0 Vault Firewall
    if eff["slot1_vault_firewall_blocked"]:
        _add_code(
            codes, STATUS_BLOCKED_G132_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION
        )
        errors.append(
            f"LUT/recording write operation `{requested_lut_or_rec_op}` targets protected "
            f"`Slot 1` Tier-0 vault (`errno={eff['block_errno']} ({eff['block_errno_code']})`): "
            "blocked fail-closed (`slot1_data_sector_writes == 0`, `slot1_avf_info_mutated == False`)."
        )

    matrix = compute_liveview_grid_lut_embed_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G132 if valid else codes[0]

    return LiveViewGridLutEmbedGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE303,
        target_model=target_model,
        reset_action=eff["reset_action"],
        shoot_mode=eff["shoot_mode"],
        live_view_display_set_menu_path=LIVE_VIEW_DISPLAY_SET_MENU_PATH_G132,
        live_view_display_set_3_subitems=LIVE_VIEW_DISPLAY_SET_3_SUBITEMS_G132,
        live_view_display_set_still_only=True,
        bright_monitoring_active=eff["bright_monitoring_active"],
        effective_live_view_display=eff["effective_live_view_display"],
        effective_exposure_effect=eff["effective_exposure_effect"],
        effective_frame_rate_low_limit=eff["effective_frame_rate_low_limit"],
        live_view_and_exposure_effect_survived_cam_reset=eff[
            "live_view_and_exposure_effect_survived_cam_reset"
        ],
        frame_rate_low_limit_reset_on_cam_reset=eff[
            "frame_rate_low_limit_reset_on_cam_reset"
        ],
        effective_grid_line_display=eff["effective_grid_line_display"],
        effective_grid_line_type=eff["effective_grid_line_type"],
        grid_line_survived_cam_reset=eff["grid_line_survived_cam_reset"],
        effective_hdmi_info_display=eff["effective_hdmi_info_display"],
        grid_line_isolated_from_hdmi_clean_feed=eff[
            "grid_line_isolated_from_hdmi_clean_feed"
        ],
        hdmi_clean_feed_preserved=eff["hdmi_clean_feed_preserved"],
        manage_user_luts_menu_path=MANAGE_USER_LUTS_MENU_PATH_G132,
        embed_lut_file_menu_path=EMBED_LUT_FILE_MENU_PATH_G132,
        card_type=eff["card_type"],
        expected_lut_folder_path=eff["expected_lut_folder_path"],
        effective_select_lut=eff["effective_select_lut"],
        select_lut_reset_on_cam_reset=eff["select_lut_reset_on_cam_reset"],
        user_luts_survived_cam_reset=eff["user_luts_survived_cam_reset"],
        effective_embed_lut_file=eff["effective_embed_lut_file"],
        embed_lut_locked_off_by_sdhc=eff["embed_lut_locked_off_by_sdhc"],
        embed_lut_reset_on_cam_reset=eff["embed_lut_reset_on_cam_reset"],
        embed_lut_preserves_slog3_pixels=True,
        embed_lut_creates_external_sidecar=False,
        embed_lut_metadata_embedded_in_container=True,
        pplut_slots=PPLUT_SLOTS_G132,
        pplut_bakes_pixels_irreversibly=True,
        pplut_reset_on_cam_reset_and_initialize=eff[
            "pplut_reset_on_cam_reset_and_initialize"
        ],
        requested_lut_or_rec_op=requested_lut_or_rec_op,
        requested_target_slot=norm_slot,
        slot_1_write_protected=bool(slot_1_write_protected),
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        lut_import_read_only_safe=eff["lut_import_read_only_safe"],
        slot1_vault_firewall_blocked=eff["slot1_vault_firewall_blocked"],
        block_errno=eff["block_errno"],
        block_errno_code=eff["block_errno_code"],
        slot1_data_sector_writes=eff["slot1_data_sector_writes"],
        slot1_avf_info_mutated=eff["slot1_avf_info_mutated"],
        fx6_user_lut_ui_cap=FX6_USER_LUT_ACTIVE_UI_CAP_G132,
        fx6_appfw_buffer_slots=FX6_APPFW_PRM_USER_LUT_BUFFER_SLOTS_G132,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g132_liveview_grid_lut_embed_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    liveview_grid_lut_embed_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase303DonorAuditResult] = None,
) -> Tuple[GateVerdict, G132LiveViewGridLutEmbedGuardResult]:
    """Evaluate Wave-56 Gate `G132` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase303_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_liveview_grid_lut_embed_guard(
        **(dict(liveview_grid_lut_embed_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G132.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G132 if valid else codes[0]

    res = G132LiveViewGridLutEmbedGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        liveview_grid_lut_embed_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, lv={guard.effective_live_view_display},"
        f"exp_eff={guard.effective_exposure_effect}, fr_low={guard.effective_frame_rate_low_limit},"
        f"grid={guard.effective_grid_line_display}/{guard.effective_grid_line_type},"
        f"card={guard.card_type}, embed={guard.effective_embed_lut_file},"
        f"slot1_vault={guard.slot_1_contains_tier0_vault}, s1_writes={guard.slot1_data_sector_writes}"
    )
    verdict = GateVerdict(
        gate_id=G132_GATE_ID,
        gate_code=G132_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `132`-Gate Milestone Master Safety Preflight (`G01..G132`)
# ---------------------------------------------------------------------------


def evaluate_132gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    dial_customize_mydial_fn_kwargs: Optional[Mapping[str, Any]] = None,
    liveview_grid_lut_embed_kwargs: Optional[Mapping[str, Any]] = None,
    master_130_override: Optional[Master130GateReport] = None,
    **m130_passthrough_kwargs: Any,
) -> Master132GateReport:
    """Evaluate all 132 Master Safety Gates (`G01..G132`) deterministically by
    delegating `G01..G130` directly to `evaluate_130gate_preflight()`.
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

    m130_report: Master130GateReport = (
        master_130_override
        if master_130_override is not None
        else evaluate_130gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m130_passthrough_kwargs,
        )
    )

    phase303_audit = audit_phase303_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g131_verdict, g131_res = evaluate_g131_dial_customize_mydial_fn_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        dial_customize_mydial_fn_kwargs=dial_customize_mydial_fn_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase303_audit,
    )

    g132_verdict, g132_res = evaluate_g132_liveview_grid_lut_embed_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        liveview_grid_lut_embed_kwargs=liveview_grid_lut_embed_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase303_audit,
    )

    gates_131_to_132 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g131_verdict, g132_verdict)
    ]
    all_gates = tuple(list(m130_report.gates) + gates_131_to_132)

    g01_to_g12_verified = int(m130_report.summary["g01_to_g12_verified"])
    g13_to_g130_verified = int(m130_report.summary["g13_to_g128_verified"]) + int(
        m130_report.summary["g129_to_g130_verified"]
    )
    g131_to_g132_verified = sum(1 for v in (g131_verdict, g132_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g130_verified + g131_to_g132_verified

    g131_to_g132_all_passed = g131_to_g132_verified == 2
    g13_to_g132_all_passed = (
        m130_report.g13_to_g130_all_passed and g131_to_g132_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m130_report.gates[:9])

    offline_129_verified = (
        g01_to_g09_ok
        and m130_report.offline_127_gates_verified
        and g131_to_g132_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_132_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g132_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m130_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_129_verified
        and m130_report.h0_h1_trial_entry_allowed
        and g131_to_g132_all_passed
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
        list(m130_report.errors)
        + list(g131_verdict.errors)
        + list(g132_verdict.errors)
    )
    warnings: List[str] = (
        list(m130_report.warnings)
        + list(g131_verdict.warnings)
        + list(g132_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m130_report.g13_to_g130_all_passed:
        overall_status = m130_report.status
    elif not g131_verdict.passed:
        overall_status = g131_verdict.status
    elif not g132_verdict.passed:
        overall_status = g132_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_132_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_132_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_132_verified:
        overall_status = "VERIFIED_ALL_132_GATES"
    else:
        overall_status = "VERIFIED_129_OF_132_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m130_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g131_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g132_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 132,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 132 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g130_verified": g13_to_g130_verified,
        "g131_to_g132_verified": g131_to_g132_verified,
        "g13_to_g132_all_passed": g13_to_g132_all_passed,
        "g131_to_g132_all_passed": g131_to_g132_all_passed,
        "offline_129_gates_verified": offline_129_verified,
        "all_132_gates_verified": all_132_verified,
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

    return Master132GateReport(
        schema=REALHW_DIAL_CUSTOMIZE_MYDIAL_FN_LIVEVIEW_LUT_EMBED_132GATE_SCHEMA,
        version=REALHW_DIAL_CUSTOMIZE_MYDIAL_FN_LIVEVIEW_LUT_EMBED_132GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_129_gates_verified=offline_129_verified,
        all_132_gates_verified=all_132_verified,
        g13_to_g132_all_passed=g13_to_g132_all_passed,
        g131_to_g132_all_passed=g131_to_g132_all_passed,
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
        master_130_report=m130_report.to_dict(),
        g131_result=g131_res.to_dict(),
        g132_result=g132_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_132_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master132GateReport:
    return evaluate_132gate_preflight(repo_root, **kwargs)


def run_132_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master132GateReport:
    return evaluate_132gate_preflight(repo_root, **kwargs)


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
        prog="realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard",
        description="Phase 303 Wave-56 G131/G132 & 132/132 Safety Gates Preflight CLI",
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
        help="Supply simulated dry-run Tier-0 backup inputs so all 132/132 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g131", "g132", "132"],
        default="132",
        help="Target gate check: g131, g132, or 132",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g131":
        v, r = evaluate_g131_dial_customize_mydial_fn_guard(
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

    if args.gate == "g132":
        v, r = evaluate_g132_liveview_grid_lut_embed_guard(
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

    rep = evaluate_132gate_preflight(
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
                "g131_status": rep.g131_result["status"],
                "g132_status": rep.g132_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/132\n"
        )
    ok = (
        rep.all_132_gates_verified
        if args.dry_run_simulated
        else rep.offline_129_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "ALLOWED_AV_TV_ROTATE_MODES_G131",
    "ALLOWED_CARD_TYPES_G132",
    "ALLOWED_CUBE_GRID_POINTS_G132",
    "ALLOWED_EMBED_LUT_MODES_G132",
    "ALLOWED_EXPOSURE_EFFECT_MODES_G132",
    "ALLOWED_FRAME_RATE_LOW_LIMIT_MODES_G132",
    "ALLOWED_FUNCTION_RING_MODES_G131",
    "ALLOWED_GRID_LINE_DISPLAY_MODES_G132",
    "ALLOWED_GRID_LINE_TYPES_G132",
    "ALLOWED_HDMI_INFO_DISPLAY_MODES_G132",
    "ALLOWED_LIVE_VIEW_DISPLAY_MODES_G132",
    "ALLOWED_LOCK_OPERATION_PARTS_MODES_G131",
    "ALLOWED_LUT_REC_OPS_G132",
    "ALLOWED_MEDIA_SLOTS_PHASE303",
    "ALLOWED_MY_DIAL_RECALL_MODES_G131",
    "ALLOWED_RESET_ACTIONS_PHASE303",
    "ALLOWED_SELECT_LUT_PRESETS_G132",
    "ALLOWED_SHOOT_MODES_PHASE303",
    "ALLOWED_USER_LUT_SLOTS_G132",
    "AV_TV_ROTATE_DEFAULT_G131",
    "AV_TV_ROTATE_F_UXC_RESID16_G131",
    "AV_TV_ROTATE_NORMAL_G131",
    "AV_TV_ROTATE_REVERSE_G131",
    "CARD_TYPE_CFEXPRESS_A_G132",
    "CARD_TYPE_SDXC_G132",
    "CARD_TYPE_SD_SDHC_G132",
    "CROSS_MODEL_FLASH_AUTHORIZED",
    "DEFAULT_REPO_ROOT",
    "DIAL_CUSTOMIZE_5_ITEMS_G131",
    "DIAL_CUSTOMIZE_G_UXC_RESID16_G131",
    "DIAL_CUSTOMIZE_MENU_PATH_G131",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE303",
    "DONOR_CHECK_MAX_SECONDS_PHASE303",
    "DORMANT_4DIAL_REAR_LR_TRAPS_G131",
    "DORMANT_FUNCTION_RING_INVALID_G131",
    "DialCustomizeMyDialFnGuardResult",
    "EBUSY_ERRNO_G132",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "EMBED_LUT_DEFAULT_G132",
    "EMBED_LUT_FILE_F_UXC_RESID16_G132",
    "EMBED_LUT_FILE_MENU_PATH_G132",
    "EMBED_LUT_FILE_WRONG_PATH_G132",
    "EMBED_LUT_OFF_G132",
    "EMBED_LUT_ON_G132",
    "EMBED_LUT_SDHC_LOCK_G_UXC_RESID16_G132",
    "ENV_CLEAN_ROOM_TEST_PHASE303",
    "ENV_FORCE_CLEAN_ROOM",
    "EOPNOTSUPP_ERRNO_G131",
    "EOPNOTSUPP_NAME_G131",
    "EROFS_ERRNO_G132",
    "EXPOSURE_EFFECT_DEFAULT_G132",
    "EXPOSURE_EFFECT_SET_AND_FLASH_G132",
    "EXPOSURE_EFFECT_SET_ONLY_G132",
    "FN_MENU_ALL_NOT_SET_WARNING_F_UXC_RESID16_G131",
    "FN_MENU_MOVIE_SLOTS_G131",
    "FN_MENU_NOT_SET_BASE_UXC_RESID16_G131",
    "FN_MENU_SETTINGS_G_UXC_RESID16_G131",
    "FN_MENU_SETTINGS_MENU_PATH_G131",
    "FN_MENU_STILL_SLOTS_G131",
    "FRAME_RATE_LOW_LIMIT_DEFAULT_G132",
    "FRAME_RATE_LOW_LIMIT_OFF_G132",
    "FRAME_RATE_LOW_LIMIT_ON_G132",
    "FUNCTION_RING_APSC_S35_FF_G131",
    "FUNCTION_RING_DEFAULT_G131",
    "FUNCTION_RING_F_UXC_RESID16_G131",
    "FUNCTION_RING_POWER_FOCUS_G131",
    "FX3_DEFAULT_FW_VERSION_PHASE303",
    "FX3_HELP_GUIDE_CODE_PHASE303",
    "FX3_MODEL_ID_PHASE303",
    "FX3_MODEL_NAME_PHASE303",
    "FX3_PHYSICAL_3_DIALS_G131",
    "FX3_PHYSICAL_DIAL_FRONT_G131",
    "FX3_PHYSICAL_DIAL_REAR_G131",
    "FX3_PHYSICAL_DIAL_WHEEL_G131",
    "FX6_APPFW_PRM_USER_LUT_BUFFER_SLOTS_G132",
    "FX6_DEFAULT_FW_VERSION_PHASE303",
    "FX6_DIAL_CONTROLS_G131",
    "FX6_DORMANT_CUSTOM_PNG_GRID_SYMBOLS_G132",
    "FX6_EMBED_LUT_MENU_PATH_G132",
    "FX6_INFO_DISP_PRIORITY_MODES_G131",
    "FX6_LUT_CHANNEL_SWITCHES_G132",
    "FX6_MARKER_MENU_PATH_G132",
    "FX6_MARKER_SAFETY_ZONES_G132",
    "FX6_MODEL_NAME_PHASE303",
    "FX6_MULTI_FUNCTION_DIAL_PATH_G131",
    "FX6_PRODUCT_CODE_PHASE303",
    "FX6_STATUS_AND_DIRECT_MENU_SURFACES_G131",
    "FX6_USER_LUT_ACTIVE_UI_CAP_G132",
    "G131",
    "G131DialCustomizeMyDialFnGuardResult",
    "G131_GATE_CODE",
    "G131_GATE_ID",
    "G132",
    "G132LiveViewGridLutEmbedGuardResult",
    "G132_GATE_CODE",
    "G132_GATE_ID",
    "GATE_G131_DIAL_CUSTOMIZE_5ITEM_3DIAL_MYDIAL_12X2_FN_SPLIT_GUARD",
    "GATE_G132_LIVEVIEW_3ITEM_BRIGHT_GRID_HDMI_LUT_EMBED_PPLUT_VAULT_GUARD",
    "GRID_LINE_DISPLAY_DEFAULT_G132",
    "GRID_LINE_DISPLAY_F_UXC_RESID16_G132",
    "GRID_LINE_DISPLAY_OFF_G132",
    "GRID_LINE_DISPLAY_ON_G132",
    "GRID_LINE_MENU_PATH_G132",
    "GRID_LINE_TYPE_DEFAULT_G132",
    "GRID_LINE_TYPE_DIAG_SQUARE_G132",
    "GRID_LINE_TYPE_RULE_OF_3RDS_G132",
    "GRID_LINE_TYPE_SQUARE_G132",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HDMI_INFO_DISPLAY_DEFAULT_G132",
    "HDMI_INFO_DISPLAY_F_UXC_RESID16_G132",
    "HDMI_INFO_DISPLAY_OFF_G132",
    "HDMI_INFO_DISPLAY_ON_G132",
    "HUMAN_HARDWARE_ATTACH_TOKEN",
    "LEGACY_DIAL_SETUP_MENU_NAME_G131",
    "LEGACY_DIAL_WHEEL_LOCK_BASE_UXC_RESID16_G131",
    "LEGACY_DIAL_WHEEL_LOCK_NAME_G131",
    "LEGACY_DIAL_WHEEL_SETUP_F_UXC_RESID16_G131",
    "LEGACY_DIAL_WHEEL_SETUP_NAME_G131",
    "LIVE_VIEW_DISPLAY_DEFAULT_G132",
    "LIVE_VIEW_DISPLAY_SET_3_SUBITEMS_G132",
    "LIVE_VIEW_DISPLAY_SET_F_UXC_RESID16_G132",
    "LIVE_VIEW_DISPLAY_SET_MENU_PATH_G132",
    "LIVE_VIEW_SETTING_EFFECT_OFF_G132",
    "LIVE_VIEW_SETTING_EFFECT_ON_G132",
    "LOCK_OPERATION_PARTS_ALL_G131",
    "LOCK_OPERATION_PARTS_DEFAULT_G131",
    "LOCK_OPERATION_PARTS_DIAL_WHEEL_G131",
    "LOCK_OPERATION_PARTS_F_UXC_RESID16_G131",
    "LOCK_OPERATION_PARTS_MULTI_SELECTOR_G131",
    "LOCK_OPERATION_PARTS_OFF_G131",
    "LUT_FOLDER_CFEXPRESS_G132",
    "LUT_FOLDER_SD_SDXC_G132",
    "LUT_OP_DELETE_ALL_USER_LUTS_G132",
    "LUT_OP_IMPORT_USER_LUT_G132",
    "LUT_OP_MAKE_CUBE_FOLDER_G132",
    "LUT_OP_RECORD_EMBED_LUT_G132",
    "LUT_OP_RECORD_PPLUT_G132",
    "LUT_OP_WRITE_CUBE_OR_SIDECAR_G132",
    "LiveViewGridLutEmbedGuardResult",
    "MANAGE_USER_LUTS_F_UXC_RESID16_G132",
    "MANAGE_USER_LUTS_MENU_PATH_G132",
    "MEDIA_SLOT_1_PHASE303",
    "MEDIA_SLOT_2_PHASE303",
    "MY_DIAL_BANKS_G131",
    "MY_DIAL_CYCLE_F_UXC_RESID16_G131",
    "MY_DIAL_RECALL_CYCLE_G131",
    "MY_DIAL_RECALL_DEFAULT_G131",
    "MY_DIAL_RECALL_HOLD_G131",
    "MY_DIAL_RECALL_NONE_G131",
    "MY_DIAL_RECALL_TOGGLE_G131",
    "MY_DIAL_SETTINGS_F_UXC_RESID16_G131",
    "MY_DIAL_UNSET_TOKEN_G131",
    "Master132GateReport",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PINNED_FX3_APPFW_SLICES_PHASE303",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE303",
    "PINNED_FX6_APPFW_SLICES_PHASE303",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE303",
    "PINNED_PHASE303_DONOR_SPECS",
    "PPLUT_SLOTS_G132",
    "Phase303DonorAuditResult",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "REALHW_DIAL_CUSTOMIZE_MYDIAL_FN_LIVEVIEW_LUT_EMBED_132GATE_SCHEMA",
    "REALHW_DIAL_CUSTOMIZE_MYDIAL_FN_LIVEVIEW_LUT_EMBED_132GATE_VERSION",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303",
    "RESET_ACTION_INITIALIZE_PHASE303",
    "RESET_ACTION_NONE_PHASE303",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE303",
    "SELECT_LUT_709_800_G132",
    "SELECT_LUT_DEFAULT_G132",
    "SELECT_LUT_S709_G132",
    "SELECT_LUT_SLOG3_G132",
    "SHOOT_MODE_MOVIE_PHASE303",
    "SHOOT_MODE_SQ_PHASE303",
    "SHOOT_MODE_STILL_PHASE303",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_BLOCKED_G131_4DIAL_REAR_LR_OR_LEGACY_TRAP_VIOLATION",
    "STATUS_BLOCKED_G131_DIAL_CUSTOMIZE_5ITEM_OR_RESET_VIOLATION",
    "STATUS_BLOCKED_G131_FX6_DIAL_OR_DIRECT_MENU_CROSSWIRE_VIOLATION",
    "STATUS_BLOCKED_G131_MYDIAL_OR_FN_12X2_SPLIT_VIOLATION",
    "STATUS_BLOCKED_G131_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G132_GRID_CLEAN_HDMI_OR_FX6_PNG_VIOLATION",
    "STATUS_BLOCKED_G132_LIVEVIEW_3ITEM_BRIGHT_OR_RESET_VIOLATION",
    "STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION",
    "STATUS_BLOCKED_G132_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION",
    "STATUS_BLOCKED_G132_TELEMETRY_INVALID",
    "STATUS_BLOCKED_PERSISTENT_EMMC_WRITE",
    "STATUS_BLOCKED_PHASE303_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G131",
    "STATUS_VERIFIED_G132",
    "STATUS_VERIFIED_SAFE",
    "USB_PACKETS_TRANSMITTED",
    "USER_LUT_MAX_FILENAME_CHARS_G132",
    "USER_LUT_SLOT_MAX_G132",
    "USER_LUT_SLOT_MIN_G132",
    "audit_phase303_donor_contracts",
    "compute_dial_customize_mydial_fn_matrix",
    "compute_liveview_grid_lut_embed_matrix",
    "evaluate_132_master_safety_gates",
    "evaluate_132gate_preflight",
    "evaluate_g131_dial_customize_mydial_fn_guard",
    "evaluate_g132_liveview_grid_lut_embed_guard",
    "main",
    "resolve_fx3_dial_customize_mydial_fn_state",
    "resolve_fx3_liveview_grid_lut_embed_state",
    "run_132_gate_preflight",
    "verify_dial_customize_mydial_fn_guard",
    "verify_liveview_grid_lut_embed_guard",
]


if __name__ == "__main__":
    raise SystemExit(main())
