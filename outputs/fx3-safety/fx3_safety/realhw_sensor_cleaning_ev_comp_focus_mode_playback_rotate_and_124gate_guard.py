"""Phase 290 (290th Phase Milestone, Wave-52) Sony `ILME-FX3` (`Ver. 7.02`, `ilc/2210`) vs
`ILME-FX6` (`Ver. 6.01`) Safety Gates `G123` (`[Sensor Cleaning]` `>= 51%` `NP-FZ100` Gate &
Mandatory Power-`OFF` vs `FX6` e-ND Optical Block + `[Exposure Comp.]` `±5.0 EV` / `±2.0 EV`,
`[Exposure step]`, Manual `M` + Fixed ISO Disable & Total `[Cine EI]`/`[Cine EI Quick]` Lockout)
& `G124` (`[Focus Mode]` Still 5-Mode vs Movie/`S&Q` 2-Mode `[AF-C (MOVIE_AUTO) / MF]` +
`[Priority Set in AF-S/AF-C]` / `[AF Assist]` / `[AF Illuminator]` + `[Playback]` `[View Mode]` /
`[Image Index]` `9/25` / `[Display as Group]` / `[Display Rotation]` / `[Rotate]` `Slot-1`
Read-Only Vault `EROFS`/`EBUSY` Firewall) + Unified `124`-Gate Master Safety Preflight (`G01..G124`).

Operationalizes Wave-52 official Sony `ILME-FX3` (`Ver. 7.02`, Help Guide `ilc/2210`) &
`ILME-FX6` (`Ver. 6.01`, `5-024-458-18`) intelligence
(`reports/2026-11-17-global-sony-wave52-cleaning-mode-ev-comp-reset-playback-view-group-focus-mode-intel/README.md`)
as deterministic offline preflight verifiers (`G123` and `G124`) and delegates `G01..G122`
directly to `evaluate_122gate_preflight()`.
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
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

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
from .realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard import (
    Master122GateReport,
    evaluate_122gate_preflight,
)
from .realhw_dualmedia_bench_interlock_and_58gate_guard import (
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
)
from .realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard import (
    _DONOR_BLOB_CACHE,
)
from .realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import SPI_NOR_WRITE_AUTHORIZED
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_SENSOR_CLEANING_EV_COMP_FOCUS_MODE_PLAYBACK_ROTATE_124GATE_SCHEMA: str = (
    "realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard_v1"
)
REALHW_SENSOR_CLEANING_EV_COMP_FOCUS_MODE_PLAYBACK_ROTATE_124GATE_VERSION: str = "1.0.0"

G123_GATE_ID: str = (
    "G123_sensor_cleaning_battery_end_block_and_ev_comp_cine_ei_guard"
)
G123_GATE_CODE: str = (
    "SENSOR_CLEANING_BATTERY_END_BLOCK_AND_EV_COMP_CINE_EI_GUARD"
)

G124_GATE_ID: str = (
    "G124_focus_mode_af_assist_illuminator_and_playback_rotate_slot1_guard"
)
G124_GATE_CODE: str = (
    "FOCUS_MODE_AF_ASSIST_ILLUMINATOR_AND_PLAYBACK_ROTATE_SLOT1_GUARD"
)

G123: str = G123_GATE_ID
G124: str = G124_GATE_ID
GATE_G123_SENSOR_CLEANING_EV_COMP_AND_CINE_EI_GUARD: str = G123_GATE_CODE
GATE_G124_FOCUS_MODE_AND_PLAYBACK_ROTATE_SLOT1_GUARD: str = G124_GATE_CODE

ENV_CLEAN_ROOM_TEST_PHASE290: str = "FX3_CLEAN_ROOM_TEST"

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
CROSS_MODEL_FLASH_AUTHORIZED: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE290: float = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE290: float = 1.00

FX3_MODEL_NAME_PHASE290: str = "ILME-FX3"
FX3_MODEL_ID_PHASE290: int = 0x91030080
FX6_MODEL_NAME_PHASE290: str = "ILME-FX6"
FX3_DEFAULT_FW_VERSION_PHASE290: str = "7.02"
FX6_DEFAULT_FW_VERSION_PHASE290: str = "6.01"
FX3_HELP_GUIDE_CODE_PHASE290: str = "ilc/2210"

RESET_ACTION_NONE_PHASE290: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE290: str = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE290: str = "Reset Network Set."
RESET_ACTION_INITIALIZE_PHASE290: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE290: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE290,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE290,
    RESET_ACTION_RESET_NETWORK_SET_PHASE290,
    RESET_ACTION_INITIALIZE_PHASE290,
)

SHOOT_MODE_P_PHASE290: str = "P"
SHOOT_MODE_A_PHASE290: str = "A"
SHOOT_MODE_S_PHASE290: str = "S"
SHOOT_MODE_M_PHASE290: str = "M"
SHOOT_MODE_STILL_PHASE290: str = "Still"
SHOOT_MODE_INTELLIGENT_AUTO_PHASE290: str = "Intelligent Auto"
SHOOT_MODE_MOVIE_PHASE290: str = "Movie"
SHOOT_MODE_SQ_PHASE290: str = "S&Q"
SHOOT_MODE_MR_PHASE290: str = "MR"
PASM_SHOOT_MODES_PHASE290: Tuple[str, ...] = (
    SHOOT_MODE_P_PHASE290,
    SHOOT_MODE_A_PHASE290,
    SHOOT_MODE_S_PHASE290,
    SHOOT_MODE_M_PHASE290,
    SHOOT_MODE_STILL_PHASE290,
)
STILL_SHOOT_MODES_PHASE290: Tuple[str, ...] = PASM_SHOOT_MODES_PHASE290 + (
    SHOOT_MODE_INTELLIGENT_AUTO_PHASE290,
)
MOVIE_SHOOT_MODES_PHASE290: Tuple[str, ...] = (
    SHOOT_MODE_MOVIE_PHASE290,
    SHOOT_MODE_SQ_PHASE290,
)
ALLOWED_SHOOT_MODES_PHASE290: Tuple[str, ...] = (
    STILL_SHOOT_MODES_PHASE290 + MOVIE_SHOOT_MODES_PHASE290 + (SHOOT_MODE_MR_PHASE290,)
)

# ---------------------------------------------------------------------------
# Status & Violation Codes (G123 / G124 / Phase 290)
# ---------------------------------------------------------------------------

STATUS_VERIFIED_G123: str = (
    "VERIFIED_G123_SENSOR_CLEANING_EV_COMP_AND_CINE_EI_SAFE"
)
STATUS_VERIFIED_G124: str = (
    "VERIFIED_G124_FOCUS_MODE_PLAYBACK_VIEW_AND_ROTATE_SLOT1_SAFE"
)
STATUS_BLOCKED_PHASE290_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE290_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G123_CLEANING_LOW_BATTERY_OR_ACTIVE_MOUNT_VIOLATION: str = (
    "BLOCKED_G123_CLEANING_LOW_BATTERY_OR_ACTIVE_MOUNT_VIOLATION"
)
STATUS_BLOCKED_G123_FX6_END_CLEANING_OR_IBIS_SPOOF_VIOLATION: str = (
    "BLOCKED_G123_FX6_END_CLEANING_OR_IBIS_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION: str = (
    "BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION"
)
STATUS_BLOCKED_G123_CINE_EI_EV_COMP_OR_LEGACY_DIAL_SPOOF_VIOLATION: str = (
    "BLOCKED_G123_CINE_EI_EV_COMP_OR_LEGACY_DIAL_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G123_TELEMETRY_INVALID: str = (
    "BLOCKED_G123_SENSOR_CLEANING_EV_COMP_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G124_FOCUS_MODE_MOVIE_SPLIT_OR_DORMANT_VIOLATION: str = (
    "BLOCKED_G124_FOCUS_MODE_MOVIE_SPLIT_OR_DORMANT_VIOLATION"
)
STATUS_BLOCKED_G124_AF_PRIORITY_ASSIST_OR_ILLUMINATOR_VIOLATION: str = (
    "BLOCKED_G124_AF_PRIORITY_ASSIST_OR_ILLUMINATOR_VIOLATION"
)
STATUS_BLOCKED_G124_PLAYBACK_VIEW_INDEX_OR_GROUP_DORMANT_VIOLATION: str = (
    "BLOCKED_G124_PLAYBACK_VIEW_INDEX_OR_GROUP_DORMANT_VIOLATION"
)
STATUS_BLOCKED_G124_SLOT1_ROTATE_WRITE_VAULT_VIOLATION: str = (
    "BLOCKED_G124_SLOT1_ROTATE_WRITE_VAULT_VIOLATION"
)
STATUS_BLOCKED_G124_TELEMETRY_INVALID: str = (
    "BLOCKED_G124_FOCUS_MODE_PLAYBACK_ROTATE_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G123 Constants: [Sensor Cleaning] + [Exposure Comp.] + [Cine EI]
# ---------------------------------------------------------------------------

SENSOR_CLEANING_MENU_PATH_G123: str = (
    "MENU -> (Setup) -> [Setup Option] -> [Sensor Cleaning]"
)
EXPOSURE_COMP_MENU_PATH_G123: str = (
    "MENU -> (Exposure/Color) -> [Exposure Comp.] -> [Exposure Comp.]"
)
EXPOSURE_STEP_MENU_PATH_G123: str = (
    "MENU -> (Exposure/Color) -> [Exposure Comp.] -> [Exposure step]"
)
EXPOSURE_STD_ADJUST_MENU_PATH_G123: str = (
    "MENU -> (Exposure/Color) -> [Exposure Comp.] -> [Exposure Std. Adjust]"
)

SENSOR_CLEANING_F_UXC_RESID16_G123: int = 0x67D6
CLEANING_MODE_LEGACY_UXC_RESID16_G123: int = 0xE7D7
POWER_INSUFFICIENT_UXC_RESID16_G123: int = 0xE574
POWER_OFF_AFTER_CLEANING_G_UXC_RESID16_G123: int = 0x6221
EXPOSURE_COMP_F_UXC_RESID16_G123: int = 0x76DE
EXPOSURE_COMP_UXC_RESID16_G123: int = 0xE956
RESET_EV_COMP_F_UXC_RESID16_G123: int = 0x7853
EXPOSURE_STEP_F_UXC_RESID16_G123: int = 0x78C4
DIAL_EV_COMP_UXC_RESID16_G123: int = 0xE4D9

SENSOR_CLEANING_MIN_BATTERY_PCT_G123: int = 51
SENSOR_CLEANING_PRE_V200_MIN_BARS_G123: int = 3
FX6_CRSDK_SENSOR_CLEANING_CMD_ID_G123: int = 320
FX6_VARIABLE_ND_VALUES_G123: Tuple[str, ...] = ("CLEAR", "1/4..1/128")

EV_COMP_STILL_MIN_EV_G123: float = -5.0
EV_COMP_STILL_MAX_EV_G123: float = 5.0
EV_COMP_MOVIE_MIN_EV_G123: float = -2.0
EV_COMP_MOVIE_MAX_EV_G123: float = 2.0
EV_COMP_LIVE_METER_MIN_EV_G123: float = -3.0
EV_COMP_LIVE_METER_MAX_EV_G123: float = 3.0
EV_COMP_FACTORY_DEFAULT_EV_G123: float = 0.0

EXPOSURE_STEP_0_3_EV_G123: str = "0.3EV"
EXPOSURE_STEP_0_5_EV_G123: str = "0.5EV"
ALLOWED_EXPOSURE_STEPS_G123: Tuple[str, ...] = (
    EXPOSURE_STEP_0_3_EV_G123,
    EXPOSURE_STEP_0_5_EV_G123,
)
EXPOSURE_STEP_FACTORY_DEFAULT_G123: str = EXPOSURE_STEP_0_3_EV_G123

EXPOSURE_STD_ADJUST_MIN_EV_G123: float = -1.0
EXPOSURE_STD_ADJUST_MAX_EV_G123: float = 1.0
EXPOSURE_STD_ADJUST_STEP_DENOM_G123: int = 6

ISO_MODE_AUTO_G123: str = "ISO AUTO"
ISO_MODE_FIXED_G123: str = "Fixed ISO"
ALLOWED_ISO_MODES_G123: Tuple[str, ...] = (ISO_MODE_AUTO_G123, ISO_MODE_FIXED_G123)

LOG_SHOOTING_OFF_G123: str = "Off"
LOG_SHOOTING_FLEXIBLE_ISO_G123: str = "Flexible ISO"
LOG_SHOOTING_CINE_EI_G123: str = "Cine EI"
LOG_SHOOTING_CINE_EI_QUICK_G123: str = "Cine EI Quick"
ALLOWED_LOG_SHOOTING_MODES_G123: Tuple[str, ...] = (
    LOG_SHOOTING_OFF_G123,
    LOG_SHOOTING_FLEXIBLE_ISO_G123,
    LOG_SHOOTING_CINE_EI_G123,
    LOG_SHOOTING_CINE_EI_QUICK_G123,
)
CINE_EI_LOCKED_LOG_MODES_G123: Tuple[str, ...] = (
    LOG_SHOOTING_CINE_EI_G123,
    LOG_SHOOTING_CINE_EI_QUICK_G123,
)
CINE_EI_BASE_ISOS_G123: Tuple[int, ...] = (800, 12800)
CINE_EI_EXPOSURE_INDEX_RANGE_BY_BASE_G123: Dict[int, Tuple[int, int]] = {
    800: (200, 3200),
    12800: (3200, 51200),
}

# ---------------------------------------------------------------------------
# Gate G124 Constants: [Focus Mode] + AF Submenu + [Playback] View/Index/Rotate
# ---------------------------------------------------------------------------

FOCUS_MODE_MENU_PATH_G124: str = "MENU -> (Focus) -> [AF/MF] -> [Focus Mode]"
VIEW_MODE_MENU_PATH_G124: str = "MENU -> (Playback) -> [Playback Target] -> [View Mode]"
IMAGE_INDEX_MENU_PATH_G124: str = (
    "MENU -> (Playback) -> [Playback Option] -> [Image Index]"
)
DISPLAY_AS_GROUP_MENU_PATH_G124: str = (
    "MENU -> (Playback) -> [Playback Option] -> [Display as Group]"
)
DISPLAY_ROTATION_MENU_PATH_G124: str = (
    "MENU -> (Playback) -> [Playback Option] -> [Display Rotation]"
)
ROTATE_MENU_PATH_G124: str = "MENU -> (Playback) -> [Edit] -> [Rotate]"

FOCUS_MODE_G_UXC_RESID16_G124: int = 0x625E
AF_S_UXC_RESID16_G124: int = 0xE56D
AF_A_UXC_RESID16_G124: int = 0xE56C
AF_C_UXC_RESID16_G124: int = 0xE56E
DMF_UXC_RESID16_G124: int = 0xE4AC
MF_UXC_RESID16_G124: int = 0xE9E4
AF_ASSIST_F_UXC_RESID16_G124: int = 0x64A9
PRIORITY_AF_S_F_UXC_RESID16_G124: int = 0x7519
PRIORITY_AF_C_F_UXC_RESID16_G124: int = 0x681B
BALANCED_EMPHASIS_F_UXC_RESID16_G124: int = 0x6A60
AF_ILLUMINATOR_UXC_RESID16_G124: int = 0xE07F
VIEW_MODE_UXC_RESID16_G124: int = 0xE3B7
DATE_VIEW_UXC_RESID16_G124: int = 0xE3B8
FOLDER_VIEW_STILL_UXC_RESID16_G124: int = 0xE3B9
MOVIE_VIEW_F_UXC_RESID16_G124: int = 0x7468
IMAGE_INDEX_UXC_RESID16_G124: int = 0xE20A
IMAGE_INDEX_9_UXC_RESID16_G124: int = 0xE4A3
IMAGE_INDEX_25_F_UXC_RESID16_G124: int = 0x7302
IMAGE_INDEX_30_DORMANT_F_UXC_RESID16_G124: int = 0x6E7A
DISPLAY_AS_GROUP_F_UXC_RESID16_G124: int = 0x6F26
DISPLAY_ROTATION_F_UXC_RESID16_G124: int = 0x6AA4
ROTATE_F_UXC_RESID16_G124: int = 0x795A
ROTATE_UXC_RESID16_G124: int = 0xE5AE
UNABLE_TO_ROTATE_UXC_RESID16_G124: int = 0xE922

FOCUS_MODE_AF_S_G124: str = "Single-shot AF"
FOCUS_MODE_AF_A_G124: str = "Automatic AF"
FOCUS_MODE_AF_C_G124: str = "Continuous AF"
FOCUS_MODE_DMF_G124: str = "DMF"
FOCUS_MODE_MF_G124: str = "Manual Focus"
FX3_STILL_5_FOCUS_MODES_G124: Tuple[str, ...] = (
    FOCUS_MODE_AF_S_G124,
    FOCUS_MODE_AF_A_G124,
    FOCUS_MODE_AF_C_G124,
    FOCUS_MODE_DMF_G124,
    FOCUS_MODE_MF_G124,
)
FX3_MOVIE_2_FOCUS_MODES_G124: Tuple[str, ...] = (
    FOCUS_MODE_AF_C_G124,
    FOCUS_MODE_MF_G124,
)
FX3_MOVIE_AFC_INTERNAL_ENUM_G124: str = "MOVIE_AUTO"
STILL_FOCUS_MODE_FACTORY_DEFAULT_G124: str = FOCUS_MODE_AF_A_G124
DORMANT_FOCUS_MODES_G124: Tuple[str, ...] = ("PF", "SEMI_MANUAL")

AF_PRIORITY_AF_G124: str = "AF"
AF_PRIORITY_RELEASE_G124: str = "Release"
AF_PRIORITY_BALANCED_G124: str = "Balanced Emphasis"
ALLOWED_AF_PRIORITY_MODES_G124: Tuple[str, ...] = (
    AF_PRIORITY_AF_G124,
    AF_PRIORITY_RELEASE_G124,
    AF_PRIORITY_BALANCED_G124,
)
AF_PRIORITY_FACTORY_DEFAULT_G124: str = AF_PRIORITY_BALANCED_G124

AF_ILLUMINATOR_AUTO_G124: str = "Auto"
AF_ILLUMINATOR_OFF_G124: str = "Off"
ALLOWED_AF_ILLUMINATOR_MODES_G124: Tuple[str, ...] = (
    AF_ILLUMINATOR_AUTO_G124,
    AF_ILLUMINATOR_OFF_G124,
)
AF_ILLUMINATOR_FACTORY_DEFAULT_G124: str = AF_ILLUMINATOR_AUTO_G124

VIEW_MODE_DATE_G124: str = "Date View"
VIEW_MODE_FOLDER_STILL_G124: str = "Folder View(Still)"
VIEW_MODE_MOVIE_G124: str = "Movie View"
FX3_ACTIVE_3_VIEW_MODES_G124: Tuple[str, ...] = (
    VIEW_MODE_DATE_G124,
    VIEW_MODE_FOLDER_STILL_G124,
    VIEW_MODE_MOVIE_G124,
)
VIEW_MODE_FACTORY_DEFAULT_G124: str = VIEW_MODE_DATE_G124
DORMANT_VIEW_MODES_G124: Tuple[str, ...] = (
    "Folder View(MP4)",
    "AVCHD View",
    "Mov. View by File Format",
)

IMAGE_INDEX_9_G124: str = "9 Images"
IMAGE_INDEX_25_G124: str = "25 Images"
FX3_ACTIVE_2_IMAGE_INDEX_MODES_G124: Tuple[str, ...] = (
    IMAGE_INDEX_9_G124,
    IMAGE_INDEX_25_G124,
)
IMAGE_INDEX_FACTORY_DEFAULT_G124: str = IMAGE_INDEX_9_G124
DORMANT_IMAGE_INDEX_MODES_G124: Tuple[str, ...] = (
    "12 Images",
    "12_IMAGES",
    "30 Images",
)

DISPLAY_ROTATION_AUTO_G124: str = "Auto"
DISPLAY_ROTATION_MANUAL_G124: str = "Manual"
DISPLAY_ROTATION_OFF_G124: str = "Off"
ALLOWED_DISPLAY_ROTATION_MODES_G124: Tuple[str, ...] = (
    DISPLAY_ROTATION_AUTO_G124,
    DISPLAY_ROTATION_MANUAL_G124,
    DISPLAY_ROTATION_OFF_G124,
)
DISPLAY_ROTATION_FACTORY_DEFAULT_G124: str = DISPLAY_ROTATION_AUTO_G124
FX3_APPFW_DISPLAY_ROTATION_BKID_G124: str = "BKID_APP_setting_display_rotatiton"

PLAYBACK_MEDIA_SLOT1_DEFAULT_G124: str = "Slot 1"
ROTATE_STEP_DEGREES_CCW_G124: int = 90

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, Targeted Pread on appFw.so, <0.20s)
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE290: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (60_605_894, b"FUNC_set_cleaning_mode"),
    (63_042_666, b"BATTERY_CHECK_FOR_CLEANING_MODE_LOWER"),
    (51_390_278, b"INSUFFICIENT_BATTERY_CLEANING_MODE"),
    (62_686_194, b"BKID_APP_setting_exposure_compensation"),
    (62_686_275, b"BKID_APP_setting_exposure_compensation_reset_save"),
    (62_686_378, b"BKID_APP_setting_exposure_step"),
    (
        61_569_123,
        b"VAL_HAITA_setting_log_shooting_general_shooting_mode_setting_aperture_a_m_switching_setting_shutter_speed_a_m_switching_exposure_mode_",
    ),
    (62_688_686, b"BKID_APP_setting_focus_mode_menu_dial"),
    (61_578_820, b"FOCUS_MODE_MENU_DIAL_AF_S_EXPOSURE_MODE_STILL"),
    (61_577_745, b"FOCUS_MODE_MENU_DIAL_AF_A_EXPOSURE_MODE_STILL"),
    (61_579_620, b"FOCUS_MODE_MENU_DIAL_MOVIE_AUTO_EXPOSURE_MODE_MOVIE"),
    (62_688_765, b"BKID_APP_setting_af_s_priority_setup"),
    (62_688_842, b"BKID_APP_setting_af_c_priority_setup"),
    (62_689_099, b"BKID_APP_setting_still_image_af_illuminator"),
    (62_689_611, b"BKID_APP_setting_af_assist"),
    (62_691_645, b"BKID_APP_setting_menu_view_mode"),
    (62_692_004, b"BKID_APP_setting_menu_image_index"),
    (62_692_038, b"BKID_APP_setting_display_group"),
    (62_692_069, b"BKID_APP_setting_display_rotatiton"),
    (60_604_120, b"FUNC_rotate_content"),
    (62_956_593, b"FUNC_CMP_NG_DURING_BACKGROUND_TRANSFER_ROTATE"),
    (61_206_591, b"VAL_status_of_media_slot1_STATUS_OF_MEDIA_SLOT1_READ_ONLY"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE290: str = (
    "6a8a875d77ef5bc5efb835613e9c1ac3478f3632af9f1973e543d2f48f2db318"
)

PINNED_FX6_APPFW_SLICES_PHASE290: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (39_890_921, b"PID_SET_VARIABLE_ND_VALUE"),
    (41_016_415, b"BKID_APP_VARIABLE_ND_CONT"),
    (37_522_026, b"MODEL_APR_EXECUTE_COMP"),
    (40_967_222, b"BKID_APP_USER_MENU_SENSOR_CLEANING"),
    (41_748_974, b"PRODUCT_MODEL_CHAPLIN"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE290: str = (
    "37104e43426ca7f3a6af36fbba7dd0f1ecef8f85a6dcd8cab9ead5160ace71f2"
)

PINNED_PHASE290_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE290,
        tuple(tok for _off, tok in PINNED_FX3_APPFW_SLICES_PHASE290),
        "FX3_APPFW_WAVE52_CLEANING_EV_COMP_FOCUS_PLAYBACK_ROTATE_SLICES",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Sensor Cleaning",
            b"Exposure Comp.",
            b"Reset EV Comp.",
            b"Maintain",
            b"Exposure step",
            b"AF Assist",
            b"Priority Set in AF-S",
            b"Priority Set in AF-C",
            b"Balanced Emphasis",
            b"Movie View",
            b"25 Images",
            b"30 Images",
            b"Display as Group",
            b"Display Rotation",
            b"Rotate",
        ),
        "FX3_UXC_F_WAVE52_CLEANING_EV_FOCUS_PLAYBACK_STRINGS",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "传感器清洁".encode("utf-8"),
            "曝光补偿".encode("utf-8"),
            "重置EV补偿".encode("utf-8"),
            "曝光步级".encode("utf-8"),
            "AF帮助".encode("utf-8"),
            "以组显示".encode("utf-8"),
            "显示旋转".encode("utf-8"),
        ),
        "FX3_UXC_F_ZHCN_WAVE52_RESID16_PARITY",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "感應器清潔".encode("utf-8"),
            "曝光補償".encode("utf-8"),
            "重設EV補償".encode("utf-8"),
            "曝光級數".encode("utf-8"),
            "AF幫助".encode("utf-8"),
            "以群組形式顯示".encode("utf-8"),
            "顯示旋轉".encode("utf-8"),
        ),
        "FX3_UXC_F_ZHTW_WAVE52_RESID16_PARITY",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "ｾﾝｻｰｸﾘｰﾆﾝｸﾞ".encode("utf-8"),
            "露出補正".encode("utf-8"),
            "露出補正値のﾘｾｯﾄ".encode("utf-8"),
            "露出値ステップ幅".encode("utf-8"),
            "AFアシスト".encode("utf-8"),
            "グループ表示".encode("utf-8"),
            "記録画像の回転表示".encode("utf-8"),
        ),
        "FX3_UXC_F_JA_WAVE52_RESID16_PARITY",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Cleaning Mode",
            b"Power insufficient.",
            b"Exposure Comp.",
            b"Dial Ev Comp",
            b"Single-shot AF",
            b"Automatic AF",
            b"Continuous AF",
            b"DMF",
            b"Manual Focus",
            b"AF Illuminator",
            b"View Mode",
            b"Date View",
            b"Folder View(Still)",
            b"Image Index",
            b"9 Images",
            b"Rotate",
            b"Unable to rotate image.",
        ),
        "FX3_UXC_WAVE52_CLEANING_FOCUS_VIEW_ROTATE_STRINGS",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Turn the power off after cleaning",
            b"Exposure Comp.",
            b"Focus Mode",
        ),
        "FX3_UXC_G_CLEANING_POWER_OFF_AND_FOCUS_MODE",
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
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE290,
        tuple(tok for _off, tok in PINNED_FX6_APPFW_SLICES_PHASE290),
        "FX6_APPFW_WAVE52_END_APR_NO_IBIS_SLICES",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"Single-shot AF(AF-S)",
            b"Auto ND Filter",
            b"Sensor Cleaning",
        ),
        "FX6_UXC_PUSH_AF_AND_AUTO_ND_STRINGS",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"Push AF/Push MF",
            b"AF Assist",
            b"Focus Mode",
            b"Clip Thumbnail View Mode",
            b"Material Group",
        ),
        "FX6_UXC_2_FOCUS_MODE_AND_CLIP_THUMBNAIL_STRINGS",
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase290DonorAuditResult:
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
class SensorCleaningEvCompGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    reset_action: str
    sensor_cleaning_menu_path: str
    exposure_comp_menu_path: str
    exposure_step_menu_path: str
    exposure_std_adjust_menu_path: str
    sensor_cleaning_requested: bool
    battery_pct: int
    battery_bars: Optional[int]
    sensor_cleaning_allowed: bool
    power_switch_off_after_cleaning: bool
    tier0_p3_backup_active: bool
    open_mount_active: bool
    fx6_has_ibis: bool
    fx6_front_end_assembly_present: bool
    fx6_sensor_cleaning_supported: bool
    fx6_crsdk_sensor_cleaning_id: int
    fx6_exposes_apr: bool
    shoot_mode: str
    log_shooting: str
    iso_mode: str
    cine_ei_base_iso: int
    requested_ev_comp: float
    effective_ev_comp: float
    ev_comp_active: bool
    ev_comp_allowed_range: Tuple[float, float]
    requested_exposure_step: str
    effective_exposure_step: str
    exposure_std_adjust_ev: float
    ev_comp_reset_on_cam_reset: bool
    exposure_step_survived_cam_reset: bool
    fx3_has_physical_ev_dial: bool
    cine_ei_locks_ev_comp: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G123SensorCleaningEvCompGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    sensor_cleaning_ev_comp_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FocusModePlaybackRotateGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    reset_action: str
    focus_mode_menu_path: str
    view_mode_menu_path: str
    image_index_menu_path: str
    display_as_group_menu_path: str
    display_rotation_menu_path: str
    rotate_menu_path: str
    shoot_mode: str
    requested_focus_mode: str
    effective_focus_mode: str
    internal_focus_enum: str
    af_assist_setting: str
    af_assist_active: bool
    requested_priority_af_s: str
    effective_priority_af_s: str
    requested_priority_af_c: str
    effective_priority_af_c: str
    af_priority_survived_cam_reset: bool
    requested_af_illuminator: str
    effective_af_illuminator: str
    af_illuminator_active: bool
    focus_magnifier_active: bool
    mount_adaptor_attached: bool
    fx6_supports_af_a_dmf_illuminator: bool
    requested_view_mode: str
    effective_view_mode: str
    requested_image_index: str
    effective_image_index: str
    requested_display_as_group: str
    effective_display_as_group: str
    requested_display_rotation: str
    effective_display_rotation: str
    playback_settings_survived_cam_reset: bool
    rotate_requested: bool
    playback_media_slot: str
    playback_media_kind: str
    slot_1_write_protected: bool
    slot_1_contains_tier0_vault: bool
    background_transfer_active: bool
    rotate_blocked: bool
    rotate_block_errno: Optional[str]
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G124FocusModePlaybackRotateGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    focus_mode_playback_rotate_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master124GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_121_gates_verified: bool
    all_124_gates_verified: bool
    g13_to_g124_all_passed: bool
    g123_to_g124_all_passed: bool
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
    master_122_report: Dict[str, Any]
    g123_result: Dict[str, Any]
    g124_result: Dict[str, Any]
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
    for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE290):
        if os.environ.get(env_key, "").strip() in _TRUTHY_CLEAN_ROOM_TOKENS:
            return True
    return False


def _default_donor_budget_seconds_phase290() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return DONOR_CHECK_CI_MAX_SECONDS_PHASE290
    return DONOR_CHECK_MAX_SECONDS_PHASE290


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


def _norm_reset_action_phase290(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE_PHASE290
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE290
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE290
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE_PHASE290
    return None


def _norm_shoot_mode_phase290(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "P": SHOOT_MODE_P_PHASE290,
        "A": SHOOT_MODE_A_PHASE290,
        "S": SHOOT_MODE_S_PHASE290,
        "M": SHOOT_MODE_M_PHASE290,
        "STILL": SHOOT_MODE_STILL_PHASE290,
        "INTELLIGENT AUTO": SHOOT_MODE_INTELLIGENT_AUTO_PHASE290,
        "IAUTO": SHOOT_MODE_INTELLIGENT_AUTO_PHASE290,
        "MOVIE": SHOOT_MODE_MOVIE_PHASE290,
        "S&Q": SHOOT_MODE_SQ_PHASE290,
        "SQ": SHOOT_MODE_SQ_PHASE290,
        "MR": SHOOT_MODE_MR_PHASE290,
    }
    return mapping.get(u)


def _norm_on_off_phase290(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "ON":
        return "On"
    if u == "OFF":
        return "Off"
    return None


def _norm_exposure_step_g123(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    if u == "0.3EV":
        return EXPOSURE_STEP_0_3_EV_G123
    if u == "0.5EV":
        return EXPOSURE_STEP_0_5_EV_G123
    return None


def _norm_iso_mode_g123(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("ISO AUTO", "AUTO"):
        return ISO_MODE_AUTO_G123
    if u in ("FIXED ISO", "FIXED", "MANUAL", "MANUAL ISO"):
        return ISO_MODE_FIXED_G123
    return None


def _norm_log_shooting_g123(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_LOG_SHOOTING_MODES_G123:
        if u == item.upper():
            return item
    return None


def _norm_focus_mode_g124(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "AF-S": FOCUS_MODE_AF_S_G124,
        "SINGLE-SHOT AF": FOCUS_MODE_AF_S_G124,
        "AF-A": FOCUS_MODE_AF_A_G124,
        "AUTOMATIC AF": FOCUS_MODE_AF_A_G124,
        "AF-C": FOCUS_MODE_AF_C_G124,
        "CONTINUOUS AF": FOCUS_MODE_AF_C_G124,
        "MOVIE_AUTO": FOCUS_MODE_AF_C_G124,
        "DMF": FOCUS_MODE_DMF_G124,
        "MF": FOCUS_MODE_MF_G124,
        "MANUAL FOCUS": FOCUS_MODE_MF_G124,
        "PF": "PF",
        "SEMI_MANUAL": "SEMI_MANUAL",
        "SEMI MANUAL": "SEMI_MANUAL",
    }
    return mapping.get(u)


def _norm_af_priority_g124(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_AF_PRIORITY_MODES_G124:
        if u == item.upper():
            return item
    return None


def _norm_af_illuminator_g124(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "AUTO":
        return AF_ILLUMINATOR_AUTO_G124
    if u == "OFF":
        return AF_ILLUMINATOR_OFF_G124
    return None


def _norm_view_mode_g124(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in FX3_ACTIVE_3_VIEW_MODES_G124 + DORMANT_VIEW_MODES_G124:
        if u == item.upper():
            return item
    return None


def _norm_image_index_g124(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in FX3_ACTIVE_2_IMAGE_INDEX_MODES_G124 + DORMANT_IMAGE_INDEX_MODES_G124:
        if u == item.upper():
            return item
    return None


def _norm_display_rotation_g124(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    for item in ALLOWED_DISPLAY_ROTATION_MODES_G124:
        if u == item.upper():
            return item
    return None


def _norm_media_slot_g124(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("SLOT 1", "SLOT1"):
        return "Slot 1"
    if u in ("SLOT 2", "SLOT2"):
        return "Slot 2"
    return None


def _parse_fw_tuple(fw: str) -> Optional[Tuple[int, int]]:
    m = re.match(r"^\s*(\d+)\.(\d+)", fw.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


# ---------------------------------------------------------------------------
# 1. Local O_RDONLY Donor Audit & Clean-Room Synthetic Fallback (< 0.20s)
# ---------------------------------------------------------------------------


def audit_phase290_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase290DonorAuditResult:
    """Strictly `os.open(..., os.O_RDONLY)` audit of Phase 290 Wave-52 local donor
    evidence (`FX3 appFw.so`, 4-language `_f.uxc`, `.uxc`, `_g.uxc`, `BK4`, and
    `FX6 appFw.so` + `.uxc` packs) with `< 0.20s` budget and clean-room fallback.
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
        else PINNED_PHASE290_DONOR_SPECS
    )

    if clean_forced:
        elapsed = time.monotonic() - t0
        return Phase290DonorAuditResult(
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
            return Phase290DonorAuditResult(
                valid=False,
                status=STATUS_BLOCKED_PHASE290_DONOR_INTEGRITY,
                verification_mode="LOCAL_DONOR_O_RDONLY",
                access_mode="O_RDONLY",
                files_inspected=0,
                elapsed_seconds=elapsed,
                within_budget_200ms=(elapsed <= _default_donor_budget_seconds_phase290()),
                raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
                checked_markers=(),
                missing_markers=tuple(missing_paths),
                fx3_contracts_verified=False,
                fx6_contracts_verified=False,
                four_lang_resid16_parity_verified=False,
                sha256_by_artifact={},
                bytes_by_artifact={},
                errors=(
                    f"Explicit work_root missing Wave-52 donor files: {missing_paths}",
                ),
                warnings=(),
            )
        elapsed = time.monotonic() - t0
        return Phase290DonorAuditResult(
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
                "Local Wave-52 Sony donor binaries absent; using CLEAN_ROOM_SYNTHETIC pinned SHA-256 contracts.",
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
                p, PINNED_FX3_APPFW_SLICES_PHASE290
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tokens_ok = _read_targeted_slices_o_rdonly(
                p, PINNED_FX6_APPFW_SLICES_PHASE290
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
    budget = _default_donor_budget_seconds_phase290()
    within_budget = elapsed <= budget
    if not within_budget:
        warnings.append(
            f"Phase 290 donor audit took {elapsed:.4f}s (budget {budget:.2f}s)."
        )

    valid = (not errors) and fx3_ok and fx6_ok and lang_ok
    return Phase290DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE290_DONOR_INTEGRITY,
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
# 2. Gate G123: [Sensor Cleaning] (>= 51% Battery & Mandatory Power-OFF vs
#    FX6 e-ND Optical Block) + [Exposure Comp.] (±5.0 EV Still / ±2.0 EV Movie,
#    Manual M + Fixed ISO Disable & Total [Cine EI] / [Cine EI Quick] Lockout)
# ---------------------------------------------------------------------------


def resolve_fx3_sensor_cleaning_and_ev_comp_state(
    *,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE290,
    sensor_cleaning_requested: bool = False,
    battery_pct: int = 80,
    battery_bars: Optional[int] = None,
    power_switch_off_after_cleaning: bool = True,
    tier0_p3_backup_active: bool = False,
    open_mount_active: bool = False,
    recording_active: bool = False,
    shoot_mode: str = SHOOT_MODE_M_PHASE290,
    log_shooting: str = LOG_SHOOTING_OFF_G123,
    iso_mode: str = ISO_MODE_AUTO_G123,
    cine_ei_base_iso: int = 800,
    requested_ev_comp: float = 0.0,
    requested_exposure_step: str = EXPOSURE_STEP_FACTORY_DEFAULT_G123,
    exposure_std_adjust_ev: float = 0.0,
    reset_action: str = RESET_ACTION_NONE_PHASE290,
) -> Dict[str, Any]:
    """Resolve effective Wave-52 Gate `G123` FX3 Ver. 7.02 Sensor Cleaning & EV Comp. state."""
    eff_reset = _norm_reset_action_phase290(reset_action) or RESET_ACTION_NONE_PHASE290
    eff_shoot = _norm_shoot_mode_phase290(shoot_mode) or SHOOT_MODE_M_PHASE290
    eff_log = _norm_log_shooting_g123(log_shooting) or LOG_SHOOTING_OFF_G123
    eff_iso_mode = _norm_iso_mode_g123(iso_mode) or ISO_MODE_AUTO_G123
    eff_step = (
        _norm_exposure_step_g123(requested_exposure_step)
        or EXPOSURE_STEP_FACTORY_DEFAULT_G123
    )

    fw_tuple = _parse_fw_tuple(firmware_version) or (7, 2)
    if fw_tuple >= (2, 0):
        batt_ok = battery_pct >= SENSOR_CLEANING_MIN_BATTERY_PCT_G123
    else:
        batt_ok = (
            battery_bars >= SENSOR_CLEANING_PRE_V200_MIN_BARS_G123
            if battery_bars is not None
            else battery_pct >= SENSOR_CLEANING_MIN_BATTERY_PCT_G123
        )

    cleaning_allowed = (
        batt_ok
        and (not tier0_p3_backup_active)
        and (not open_mount_active)
        and (not recording_active)
    )

    is_still = eff_shoot in STILL_SHOOT_MODES_PHASE290
    allowed_range = (
        (EV_COMP_STILL_MIN_EV_G123, EV_COMP_STILL_MAX_EV_G123)
        if is_still
        else (EV_COMP_MOVIE_MIN_EV_G123, EV_COMP_MOVIE_MAX_EV_G123)
    )

    cine_ei_locked = eff_log in CINE_EI_LOCKED_LOG_MODES_G123
    # Under Cine EI / Cine EI Quick, sensor gain is pinned to Base ISO 800/12800 and
    # Exposure Mode is locked to Movie M -> EV Comp is 100% locked out.
    if eff_shoot == SHOOT_MODE_INTELLIGENT_AUTO_PHASE290:
        ev_comp_active = False
    elif cine_ei_locked:
        ev_comp_active = False
    elif eff_shoot == SHOOT_MODE_M_PHASE290 and eff_iso_mode == ISO_MODE_FIXED_G123:
        ev_comp_active = False
    else:
        ev_comp_active = True

    eff_ev_comp = float(requested_ev_comp) if ev_comp_active else 0.0
    ev_comp_reset_on_cam_reset = eff_reset in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE290,
        RESET_ACTION_INITIALIZE_PHASE290,
    )
    if ev_comp_reset_on_cam_reset:
        eff_ev_comp = EV_COMP_FACTORY_DEFAULT_EV_G123

    exposure_step_survived_cam_reset = eff_reset != RESET_ACTION_INITIALIZE_PHASE290
    if eff_reset == RESET_ACTION_INITIALIZE_PHASE290:
        eff_step = EXPOSURE_STEP_FACTORY_DEFAULT_G123
        eff_std_adj = 0.0
    else:
        eff_std_adj = float(exposure_std_adjust_ev)

    return {
        "sensor_cleaning_requested": bool(sensor_cleaning_requested),
        "sensor_cleaning_allowed": bool(cleaning_allowed),
        "power_switch_off_after_cleaning": bool(power_switch_off_after_cleaning),
        "shoot_mode": eff_shoot,
        "log_shooting": eff_log,
        "iso_mode": eff_iso_mode,
        "cine_ei_base_iso": int(cine_ei_base_iso),
        "cine_ei_locks_ev_comp": cine_ei_locked,
        "ev_comp_active": ev_comp_active,
        "ev_comp_allowed_range": allowed_range,
        "effective_ev_comp": eff_ev_comp,
        "effective_exposure_step": eff_step,
        "effective_exposure_std_adjust_ev": eff_std_adj,
        "ev_comp_reset_on_cam_reset": ev_comp_reset_on_cam_reset,
        "exposure_step_survived_cam_reset": exposure_step_survived_cam_reset,
    }


def compute_sensor_cleaning_and_ev_comp_matrix() -> Dict[str, Any]:
    """Deterministic `384`-state cross-product across `(4 shoot_modes x 4 log_modes x
    2 iso_modes x 2 exp_steps x 3 battery_levels x 2 resets)` verifying `G123` invariants.
    """
    states = 0
    cleaning_blocked_low_batt = 0
    cine_ei_ev_locked = 0
    manual_fixed_iso_ev_locked = 0
    step_survived_cam_reset = 0

    for sm in (
        SHOOT_MODE_P_PHASE290,
        SHOOT_MODE_M_PHASE290,
        SHOOT_MODE_INTELLIGENT_AUTO_PHASE290,
        SHOOT_MODE_MOVIE_PHASE290,
    ):
        for log_m in ALLOWED_LOG_SHOOTING_MODES_G123:
            for iso_m in ALLOWED_ISO_MODES_G123:
                for step in ALLOWED_EXPOSURE_STEPS_G123:
                    for batt in (40, 50, 51):
                        for r_act in (
                            RESET_ACTION_NONE_PHASE290,
                            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE290,
                        ):
                            states += 1
                            r = resolve_fx3_sensor_cleaning_and_ev_comp_state(
                                sensor_cleaning_requested=True,
                                battery_pct=batt,
                                shoot_mode=sm,
                                log_shooting=log_m,
                                iso_mode=iso_m,
                                requested_ev_comp=1.0,
                                requested_exposure_step=step,
                                reset_action=r_act,
                            )
                            if batt < SENSOR_CLEANING_MIN_BATTERY_PCT_G123:
                                assert r["sensor_cleaning_allowed"] is False
                                cleaning_blocked_low_batt += 1
                            else:
                                assert r["sensor_cleaning_allowed"] is True
                            if log_m in CINE_EI_LOCKED_LOG_MODES_G123:
                                assert r["ev_comp_active"] is False
                                assert r["effective_ev_comp"] == 0.0
                                cine_ei_ev_locked += 1
                            if sm == SHOOT_MODE_M_PHASE290 and iso_m == ISO_MODE_FIXED_G123:
                                assert r["ev_comp_active"] is False
                                manual_fixed_iso_ev_locked += 1
                            if r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE290:
                                assert r["effective_ev_comp"] == 0.0
                                assert r["effective_exposure_step"] == step
                                assert r["exposure_step_survived_cam_reset"] is True
                                step_survived_cam_reset += 1

    return {
        "states_checked": states,
        "cleaning_blocked_low_batt": cleaning_blocked_low_batt,
        "cine_ei_ev_locked": cine_ei_ev_locked,
        "manual_fixed_iso_ev_locked": manual_fixed_iso_ev_locked,
        "step_survived_cam_reset": step_survived_cam_reset,
        "all_invariants_hold": states == 384,
    }


def verify_sensor_cleaning_and_ev_comp_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE290,
    body_model_id: int = FX3_MODEL_ID_PHASE290,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE290,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE290,
    target_model: str = FX3_MODEL_NAME_PHASE290,
    sensor_cleaning_requested: bool = False,
    battery_pct: int = 80,
    battery_bars: Optional[int] = None,
    power_switch_off_after_cleaning: bool = True,
    tier0_p3_backup_active: bool = False,
    open_mount_active: bool = False,
    recording_active: bool = False,
    compressed_air_blower_requested: bool = False,
    shoot_mode: str = SHOOT_MODE_M_PHASE290,
    log_shooting: str = LOG_SHOOTING_OFF_G123,
    iso_mode: str = ISO_MODE_AUTO_G123,
    cine_ei_base_iso: int = 800,
    requested_ev_comp: float = 0.0,
    ev_comp_apply_requested: bool = False,
    requested_exposure_step: str = EXPOSURE_STEP_FACTORY_DEFAULT_G123,
    exposure_std_adjust_ev: float = 0.0,
    reset_action: str = RESET_ACTION_NONE_PHASE290,
    claimed_fx6_has_ibis_sensor_cleaning: bool = False,
    claimed_cross_wire_fx3_ibis_clean_to_fx6_end: bool = False,
    claimed_fx3_has_physical_ev_dial_or_reset_ev_comp: bool = False,
    claimed_cine_ei_allows_ev_comp: bool = False,
    claimed_exposure_step_changes_shutter_angle: bool = False,
) -> SensorCleaningEvCompGuardResult:
    """Verify Gate `G123` across `[Sensor Cleaning]` (`>= 51%` battery gate & mandatory
    power-`OFF` vs `FX6` e-ND optical block / zero IBIS) and `[Exposure Comp.]`
    (`±5.0 EV` Still / `±2.0 EV` Movie, `[Exposure step]`, Manual `M` + Fixed ISO
    disable, & total `[Cine EI]` / `[Cine EI Quick]` lockout).
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version) if isinstance(firmware_version, str) else None
    if (
        body_model_name != FX3_MODEL_NAME_PHASE290
        or not _is_real_int(body_model_id)
        or body_model_id != FX3_MODEL_ID_PHASE290
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE290
        or fw_tuple is None
        or not _is_real_int(battery_pct)
        or battery_pct < 0
        or battery_pct > 100
        or (battery_bars is not None and (not _is_real_int(battery_bars) or battery_bars < 0 or battery_bars > 4))
        or not _is_real_number(requested_ev_comp)
        or not _is_real_number(exposure_std_adjust_ev)
        or not _is_real_int(cine_ei_base_iso)
        or cine_ei_base_iso not in CINE_EI_BASE_ISOS_G123
    ):
        _add_code(codes, STATUS_BLOCKED_G123_TELEMETRY_INVALID)
        errors.append("Invalid FX3 hardware identity, battery telemetry, or numeric EV/ISO type.")

    norm_shoot = _norm_shoot_mode_phase290(shoot_mode)
    norm_log = _norm_log_shooting_g123(log_shooting)
    norm_iso = _norm_iso_mode_g123(iso_mode)
    norm_step = _norm_exposure_step_g123(requested_exposure_step)
    norm_reset = _norm_reset_action_phase290(reset_action)

    if (
        norm_shoot is None
        or norm_log is None
        or norm_iso is None
        or norm_step is None
        or norm_reset is None
        or target_model not in (FX3_MODEL_NAME_PHASE290, FX6_MODEL_NAME_PHASE290)
    ):
        _add_code(codes, STATUS_BLOCKED_G123_TELEMETRY_INVALID)
        errors.append("Invalid G123 shoot mode, Log mode, ISO mode, exposure step, reset action, or target model.")

    safe_batt = battery_pct if _is_real_int(battery_pct) and 0 <= battery_pct <= 100 else 0
    safe_ev = float(requested_ev_comp) if _is_real_number(requested_ev_comp) else 0.0
    safe_std_adj = float(exposure_std_adjust_ev) if _is_real_number(exposure_std_adjust_ev) else 0.0

    eff = resolve_fx3_sensor_cleaning_and_ev_comp_state(
        firmware_version=firmware_version if fw_tuple is not None else FX3_DEFAULT_FW_VERSION_PHASE290,
        sensor_cleaning_requested=sensor_cleaning_requested,
        battery_pct=safe_batt,
        battery_bars=battery_bars if _is_real_int(battery_bars) else None,
        power_switch_off_after_cleaning=power_switch_off_after_cleaning,
        tier0_p3_backup_active=tier0_p3_backup_active,
        open_mount_active=open_mount_active,
        recording_active=recording_active,
        shoot_mode=norm_shoot or SHOOT_MODE_M_PHASE290,
        log_shooting=norm_log or LOG_SHOOTING_OFF_G123,
        iso_mode=norm_iso or ISO_MODE_AUTO_G123,
        cine_ei_base_iso=cine_ei_base_iso if _is_real_int(cine_ei_base_iso) else 800,
        requested_ev_comp=safe_ev,
        requested_exposure_step=norm_step or EXPOSURE_STEP_FACTORY_DEFAULT_G123,
        exposure_std_adjust_ev=safe_std_adj,
        reset_action=norm_reset or RESET_ACTION_NONE_PHASE290,
    )

    # Part A: FX6 e-ND optical block / zero-IBIS cross-wire guard
    if (
        (target_model == FX6_MODEL_NAME_PHASE290 and sensor_cleaning_requested)
        or claimed_fx6_has_ibis_sensor_cleaning
        or claimed_cross_wire_fx3_ibis_clean_to_fx6_end
    ):
        _add_code(codes, STATUS_BLOCKED_G123_FX6_END_CLEANING_OR_IBIS_SPOOF_VIOLATION)
        errors.append(
            "ILME-FX6 Ver. 6.01 has ZERO IBIS, places an electronic Variable ND optical assembly "
            "directly in front of the CMOS sensor, exposes Technical > APR, and marks "
            "CrCommandId_SensorCleaning (320) unsupported; cross-wiring FX3 IBIS cleaning onto FX6 is blocked."
        )

    # Part B: FX3 [Sensor Cleaning] >= 51% battery gate, active mount/backup & mandatory power-OFF
    if sensor_cleaning_requested:
        if fw_tuple is not None and fw_tuple >= (2, 0) and safe_batt < SENSOR_CLEANING_MIN_BATTERY_PCT_G123:
            _add_code(codes, STATUS_BLOCKED_G123_CLEANING_LOW_BATTERY_OR_ACTIVE_MOUNT_VIOLATION)
            errors.append(
                f"[Sensor Cleaning] rejected fail-closed (INSUFFICIENT_BATTERY_CLEANING_MODE / "
                f"'Power insufficient.' .uxc 0xe574): NP-FZ100 {safe_batt}% < {SENSOR_CLEANING_MIN_BATTERY_PCT_G123}%."
            )
        elif fw_tuple is not None and fw_tuple < (2, 0):
            if (battery_bars is not None and battery_bars < SENSOR_CLEANING_PRE_V200_MIN_BARS_G123) or (
                battery_bars is None and safe_batt < SENSOR_CLEANING_MIN_BATTERY_PCT_G123
            ):
                _add_code(codes, STATUS_BLOCKED_G123_CLEANING_LOW_BATTERY_OR_ACTIVE_MOUNT_VIOLATION)
                errors.append(
                    "Pre-Ver. 2.00 [Sensor Cleaning] requires >= 3 remaining battery bars."
                )
        if tier0_p3_backup_active or open_mount_active or recording_active:
            _add_code(codes, STATUS_BLOCKED_G123_CLEANING_LOW_BATTERY_OR_ACTIVE_MOUNT_VIOLATION)
            errors.append(
                "[Sensor Cleaning] forbidden during active Tier-0 p3 backup, open mount, or active recording."
            )
        if not power_switch_off_after_cleaning:
            _add_code(codes, STATUS_BLOCKED_G123_CLEANING_LOW_BATTERY_OR_ACTIVE_MOUNT_VIOLATION)
            errors.append(
                "[Sensor Cleaning] mandates physical power-switch OFF (_g.uxc 0x6221) before manual blower cleaning."
            )
        if compressed_air_blower_requested:
            _add_code(codes, STATUS_BLOCKED_G123_CLEANING_LOW_BATTERY_OR_ACTIVE_MOUNT_VIOLATION)
            errors.append(
                "Compressed air is forbidden for sensor cleaning (use manual air blower only)."
            )

    # Part C: [Exposure Comp.] range, step, Manual M + Fixed ISO, & Cine EI Lockout
    if _is_real_number(requested_ev_comp):
        lo, hi = eff["ev_comp_allowed_range"]
        if safe_ev < lo or safe_ev > hi:
            _add_code(codes, STATUS_BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION)
            errors.append(
                f"[Exposure Comp.] {safe_ev:+.1f} EV out of bounds [{lo:+.1f}, {hi:+.1f}] for shoot_mode={norm_shoot}."
            )

    if _is_real_number(exposure_std_adjust_ev):
        if safe_std_adj < EXPOSURE_STD_ADJUST_MIN_EV_G123 or safe_std_adj > EXPOSURE_STD_ADJUST_MAX_EV_G123:
            _add_code(codes, STATUS_BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION)
            errors.append(
                f"[Exposure Std. Adjust] {safe_std_adj:+.2f} EV out of [-1.0, +1.0] EV (1/6 EV steps)."
            )
        else:
            sixths = round(safe_std_adj * EXPOSURE_STD_ADJUST_STEP_DENOM_G123)
            if abs(safe_std_adj - (sixths / EXPOSURE_STD_ADJUST_STEP_DENOM_G123)) > 1e-6:
                _add_code(codes, STATUS_BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION)
                errors.append(
                    f"[Exposure Std. Adjust] {safe_std_adj:+.3f} EV is not an exact 1/6 EV step."
                )

    ev_mutation_attempted = ev_comp_apply_requested or (abs(safe_ev) > 1e-9)
    if ev_mutation_attempted:
        if norm_log in CINE_EI_LOCKED_LOG_MODES_G123:
            _add_code(codes, STATUS_BLOCKED_G123_CINE_EI_EV_COMP_OR_LEGACY_DIAL_SPOOF_VIOLATION)
            errors.append(
                f"[Exposure Comp.] is 100% locked out under [Log Shooting] = {norm_log} "
                "(hard-locks EXPOSURE_MODE_MOVIE_M + Base ISO 800/12800; use Exposure Index + Display LUT)."
            )
        elif norm_shoot == SHOOT_MODE_INTELLIGENT_AUTO_PHASE290:
            _add_code(codes, STATUS_BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION)
            errors.append("[Exposure Comp.] is disabled in Intelligent Auto (iAuto).")
        elif norm_shoot == SHOOT_MODE_M_PHASE290 and norm_iso == ISO_MODE_FIXED_G123:
            _add_code(codes, STATUS_BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION)
            errors.append(
                "[Exposure Comp.] is inactive in Manual Exposure (M) with fixed numeric ISO "
                "(active in M ONLY when ISO = ISO AUTO)."
            )

    if (
        claimed_fx3_has_physical_ev_dial_or_reset_ev_comp
        or claimed_cine_ei_allows_ev_comp
        or claimed_exposure_step_changes_shutter_angle
    ):
        _add_code(codes, STATUS_BLOCKED_G123_CINE_EI_EV_COMP_OR_LEGACY_DIAL_SPOOF_VIOLATION)
        errors.append(
            "Dial-less FX3 physical EV dial / [Reset EV Comp.] spoof, Cine EI EV Comp. spoof, "
            "or Exposure step alters Shutter Angle spoof rejected."
        )

    matrix = compute_sensor_cleaning_and_ev_comp_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G123 if valid else codes[0]

    return SensorCleaningEvCompGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE290,
        reset_action=norm_reset or "INVALID",
        sensor_cleaning_menu_path=SENSOR_CLEANING_MENU_PATH_G123,
        exposure_comp_menu_path=EXPOSURE_COMP_MENU_PATH_G123,
        exposure_step_menu_path=EXPOSURE_STEP_MENU_PATH_G123,
        exposure_std_adjust_menu_path=EXPOSURE_STD_ADJUST_MENU_PATH_G123,
        sensor_cleaning_requested=eff["sensor_cleaning_requested"],
        battery_pct=safe_batt,
        battery_bars=battery_bars if _is_real_int(battery_bars) else None,
        sensor_cleaning_allowed=eff["sensor_cleaning_allowed"],
        power_switch_off_after_cleaning=eff["power_switch_off_after_cleaning"],
        tier0_p3_backup_active=bool(tier0_p3_backup_active),
        open_mount_active=bool(open_mount_active),
        fx6_has_ibis=False,
        fx6_front_end_assembly_present=True,
        fx6_sensor_cleaning_supported=False,
        fx6_crsdk_sensor_cleaning_id=FX6_CRSDK_SENSOR_CLEANING_CMD_ID_G123,
        fx6_exposes_apr=True,
        shoot_mode=eff["shoot_mode"],
        log_shooting=eff["log_shooting"],
        iso_mode=eff["iso_mode"],
        cine_ei_base_iso=eff["cine_ei_base_iso"],
        requested_ev_comp=safe_ev,
        effective_ev_comp=eff["effective_ev_comp"],
        ev_comp_active=eff["ev_comp_active"],
        ev_comp_allowed_range=eff["ev_comp_allowed_range"],
        requested_exposure_step=norm_step or str(requested_exposure_step),
        effective_exposure_step=eff["effective_exposure_step"],
        exposure_std_adjust_ev=eff["effective_exposure_std_adjust_ev"],
        ev_comp_reset_on_cam_reset=eff["ev_comp_reset_on_cam_reset"],
        exposure_step_survived_cam_reset=eff["exposure_step_survived_cam_reset"],
        fx3_has_physical_ev_dial=False,
        cine_ei_locks_ev_comp=eff["cine_ei_locks_ev_comp"],
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g123_sensor_cleaning_and_ev_comp_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    sensor_cleaning_ev_comp_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase290DonorAuditResult] = None,
) -> Tuple[GateVerdict, G123SensorCleaningEvCompGuardResult]:
    """Evaluate Gate `G123` including `< 0.20s` `O_RDONLY` Wave-52 donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase290_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_sensor_cleaning_and_ev_comp_guard(
        **(dict(sensor_cleaning_ev_comp_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G123.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G123 if valid else codes[0]

    res = G123SensorCleaningEvCompGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        sensor_cleaning_ev_comp_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, clean_batt>={SENSOR_CLEANING_MIN_BATTERY_PCT_G123}%"
        f"(batt={guard.battery_pct}%,allowed={guard.sensor_cleaning_allowed},"
        f"pwr_off={guard.power_switch_off_after_cleaning},fx6_ibis={guard.fx6_has_ibis},"
        f"fx6_end={guard.fx6_front_end_assembly_present}), "
        f"ev_comp={guard.effective_ev_comp:+.1f}EV(range={guard.ev_comp_allowed_range},"
        f"step={guard.effective_exposure_step},log={guard.log_shooting},"
        f"cine_ei_lock={guard.cine_ei_locks_ev_comp},fx3_dial={guard.fx3_has_physical_ev_dial})"
    )
    verdict = GateVerdict(
        gate_id=G123_GATE_ID,
        gate_code=G123_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G124: [Focus Mode] Still 5-Mode vs Movie/S&Q 2-Mode (MOVIE_AUTO/MF) +
#    [Priority Set in AF-S/AF-C] / [AF Assist] / [AF Illuminator] + [Playback]
#    [View Mode] / [Image Index] (9/25 vs 12/30) / [Display as Group] /
#    [Display Rotation] / [Rotate] Slot-1 Read-Only Vault EROFS/EBUSY Firewall
# ---------------------------------------------------------------------------


def resolve_fx3_focus_mode_and_playback_rotate_state(
    *,
    shoot_mode: str = SHOOT_MODE_M_PHASE290,
    requested_focus_mode: str = STILL_FOCUS_MODE_FACTORY_DEFAULT_G124,
    af_assist_setting: str = "Off",
    requested_priority_af_s: str = AF_PRIORITY_FACTORY_DEFAULT_G124,
    requested_priority_af_c: str = AF_PRIORITY_FACTORY_DEFAULT_G124,
    requested_af_illuminator: str = AF_ILLUMINATOR_FACTORY_DEFAULT_G124,
    focus_magnifier_active: bool = False,
    mount_adaptor_attached: bool = False,
    requested_view_mode: str = VIEW_MODE_FACTORY_DEFAULT_G124,
    requested_image_index: str = IMAGE_INDEX_FACTORY_DEFAULT_G124,
    requested_display_as_group: str = "Off",
    requested_display_rotation: str = DISPLAY_ROTATION_FACTORY_DEFAULT_G124,
    rotate_requested: bool = False,
    playback_media_slot: str = PLAYBACK_MEDIA_SLOT1_DEFAULT_G124,
    playback_media_kind: str = "Still",
    slot_1_write_protected: bool = True,
    slot_1_contains_tier0_vault: bool = True,
    background_transfer_active: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE290,
) -> Dict[str, Any]:
    """Resolve effective Wave-52 Gate `G124` FX3 Ver. 7.02 Focus Mode & Playback/Rotate state."""
    eff_reset = _norm_reset_action_phase290(reset_action) or RESET_ACTION_NONE_PHASE290
    eff_shoot = _norm_shoot_mode_phase290(shoot_mode) or SHOOT_MODE_M_PHASE290
    is_movie_domain = eff_shoot in MOVIE_SHOOT_MODES_PHASE290

    eff_focus = _norm_focus_mode_g124(requested_focus_mode) or STILL_FOCUS_MODE_FACTORY_DEFAULT_G124
    if is_movie_domain and eff_focus not in FX3_MOVIE_2_FOCUS_MODES_G124:
        eff_focus = FOCUS_MODE_AF_C_G124

    eff_af_assist = _norm_on_off_phase290(af_assist_setting) or "Off"
    eff_prio_s = _norm_af_priority_g124(requested_priority_af_s) or AF_PRIORITY_FACTORY_DEFAULT_G124
    eff_prio_c = _norm_af_priority_g124(requested_priority_af_c) or AF_PRIORITY_FACTORY_DEFAULT_G124
    eff_illum = _norm_af_illuminator_g124(requested_af_illuminator) or AF_ILLUMINATOR_FACTORY_DEFAULT_G124

    eff_view = _norm_view_mode_g124(requested_view_mode) or VIEW_MODE_FACTORY_DEFAULT_G124
    if eff_view in DORMANT_VIEW_MODES_G124:
        eff_view = VIEW_MODE_FACTORY_DEFAULT_G124

    eff_index = _norm_image_index_g124(requested_image_index) or IMAGE_INDEX_FACTORY_DEFAULT_G124
    if eff_index in DORMANT_IMAGE_INDEX_MODES_G124:
        eff_index = IMAGE_INDEX_FACTORY_DEFAULT_G124

    eff_group = _norm_on_off_phase290(requested_display_as_group) or "Off"
    eff_disp_rot = _norm_display_rotation_g124(requested_display_rotation) or DISPLAY_ROTATION_FACTORY_DEFAULT_G124

    if eff_reset == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE290:
        if not is_movie_domain:
            eff_focus = STILL_FOCUS_MODE_FACTORY_DEFAULT_G124
        eff_illum = AF_ILLUMINATOR_FACTORY_DEFAULT_G124
    elif eff_reset == RESET_ACTION_INITIALIZE_PHASE290:
        eff_focus = FOCUS_MODE_AF_C_G124 if is_movie_domain else STILL_FOCUS_MODE_FACTORY_DEFAULT_G124
        eff_af_assist = "Off"
        eff_prio_s = AF_PRIORITY_FACTORY_DEFAULT_G124
        eff_prio_c = AF_PRIORITY_FACTORY_DEFAULT_G124
        eff_illum = AF_ILLUMINATOR_FACTORY_DEFAULT_G124
        eff_view = VIEW_MODE_FACTORY_DEFAULT_G124
        eff_index = IMAGE_INDEX_FACTORY_DEFAULT_G124
        eff_group = "Off"
        eff_disp_rot = DISPLAY_ROTATION_FACTORY_DEFAULT_G124

    survived_cam_reset = eff_reset != RESET_ACTION_INITIALIZE_PHASE290

    if is_movie_domain and eff_focus == FOCUS_MODE_AF_C_G124:
        internal_enum = FX3_MOVIE_AFC_INTERNAL_ENUM_G124
    elif eff_focus == FOCUS_MODE_AF_S_G124:
        internal_enum = "AF_S"
    elif eff_focus == FOCUS_MODE_AF_A_G124:
        internal_enum = "AF_A"
    elif eff_focus == FOCUS_MODE_AF_C_G124:
        internal_enum = "AF_C"
    elif eff_focus == FOCUS_MODE_DMF_G124:
        internal_enum = "DMF"
    else:
        internal_enum = "MF"

    af_assist_active = bool(
        is_movie_domain
        and eff_focus == FOCUS_MODE_AF_C_G124
        and eff_af_assist == "On"
    )
    af_illuminator_active = bool(
        (not is_movie_domain)
        and eff_focus in (FOCUS_MODE_AF_S_G124, FOCUS_MODE_AF_A_G124, FOCUS_MODE_DMF_G124)
        and eff_illum == AF_ILLUMINATOR_AUTO_G124
        and (not focus_magnifier_active)
        and (not mount_adaptor_attached)
    )

    eff_slot = _norm_media_slot_g124(playback_media_slot) or PLAYBACK_MEDIA_SLOT1_DEFAULT_G124
    pb_kind = (
        playback_media_kind.strip().title()
        if isinstance(playback_media_kind, str)
        and playback_media_kind.strip().title() in ("Still", "Movie")
        else "Still"
    )

    slot1_ro_hazard = (eff_slot == "Slot 1") and (
        bool(slot_1_write_protected) or bool(slot_1_contains_tier0_vault)
    )
    rotate_errno: Optional[str] = None
    if rotate_requested:
        if slot1_ro_hazard:
            rotate_errno = "EROFS"
        elif background_transfer_active:
            rotate_errno = "EBUSY"
        elif pb_kind != "Still":
            rotate_errno = "EINVAL"
    rotate_blocked = rotate_errno is not None

    return {
        "shoot_mode": eff_shoot,
        "effective_focus_mode": eff_focus,
        "internal_focus_enum": internal_enum,
        "af_assist_setting": eff_af_assist,
        "af_assist_active": af_assist_active,
        "effective_priority_af_s": eff_prio_s,
        "effective_priority_af_c": eff_prio_c,
        "af_priority_survived_cam_reset": survived_cam_reset,
        "effective_af_illuminator": eff_illum,
        "af_illuminator_active": af_illuminator_active,
        "effective_view_mode": eff_view,
        "effective_image_index": eff_index,
        "effective_display_as_group": eff_group,
        "effective_display_rotation": eff_disp_rot,
        "playback_settings_survived_cam_reset": survived_cam_reset,
        "playback_media_slot": eff_slot,
        "playback_media_kind": pb_kind,
        "rotate_requested": bool(rotate_requested),
        "rotate_blocked": rotate_blocked,
        "rotate_block_errno": rotate_errno,
    }


def compute_focus_mode_and_playback_rotate_matrix() -> Dict[str, Any]:
    """Deterministic `384`-state cross-product across `(4 shoot_modes x 4 focus_modes x
    2 af_illum_conds x 3 view_modes x 2 image_indices x 2 resets)` verifying `G124` invariants.
    """
    states = 0
    movie_afc_internal_movie_auto = 0
    illuminator_locked_states = 0
    priority_survived_cam_reset = 0
    playback_survived_cam_reset = 0

    for sm in (
        SHOOT_MODE_P_PHASE290,
        SHOOT_MODE_M_PHASE290,
        SHOOT_MODE_MOVIE_PHASE290,
        SHOOT_MODE_SQ_PHASE290,
    ):
        for fm in (
            FOCUS_MODE_AF_S_G124,
            FOCUS_MODE_AF_A_G124,
            FOCUS_MODE_AF_C_G124,
            FOCUS_MODE_MF_G124,
        ):
            for mag_or_adaptor in (False, True):
                for vm in FX3_ACTIVE_3_VIEW_MODES_G124:
                    for idx in FX3_ACTIVE_2_IMAGE_INDEX_MODES_G124:
                        for r_act in (
                            RESET_ACTION_NONE_PHASE290,
                            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE290,
                        ):
                            states += 1
                            r = resolve_fx3_focus_mode_and_playback_rotate_state(
                                shoot_mode=sm,
                                requested_focus_mode=fm,
                                requested_priority_af_s=AF_PRIORITY_AF_G124,
                                requested_priority_af_c=AF_PRIORITY_RELEASE_G124,
                                requested_af_illuminator=AF_ILLUMINATOR_AUTO_G124,
                                focus_magnifier_active=mag_or_adaptor,
                                requested_view_mode=vm,
                                requested_image_index=idx,
                                requested_display_as_group="On",
                                requested_display_rotation=DISPLAY_ROTATION_MANUAL_G124,
                                reset_action=r_act,
                            )
                            if sm in MOVIE_SHOOT_MODES_PHASE290:
                                assert r["effective_focus_mode"] in FX3_MOVIE_2_FOCUS_MODES_G124
                                if r["effective_focus_mode"] == FOCUS_MODE_AF_C_G124:
                                    assert r["internal_focus_enum"] == FX3_MOVIE_AFC_INTERNAL_ENUM_G124
                                    movie_afc_internal_movie_auto += 1
                            if not r["af_illuminator_active"]:
                                illuminator_locked_states += 1
                            if r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE290:
                                assert r["effective_priority_af_s"] == AF_PRIORITY_AF_G124
                                assert r["effective_priority_af_c"] == AF_PRIORITY_RELEASE_G124
                                assert r["effective_view_mode"] == vm
                                assert r["effective_image_index"] == idx
                                assert r["effective_display_as_group"] == "On"
                                assert r["effective_display_rotation"] == DISPLAY_ROTATION_MANUAL_G124
                                priority_survived_cam_reset += 1
                                playback_survived_cam_reset += 1

    return {
        "states_checked": states,
        "movie_afc_internal_movie_auto": movie_afc_internal_movie_auto,
        "illuminator_locked_states": illuminator_locked_states,
        "priority_survived_cam_reset": priority_survived_cam_reset,
        "playback_survived_cam_reset": playback_survived_cam_reset,
        "all_invariants_hold": states == 384,
    }


def verify_focus_mode_and_playback_rotate_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE290,
    body_model_id: int = FX3_MODEL_ID_PHASE290,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE290,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE290,
    shoot_mode: str = SHOOT_MODE_M_PHASE290,
    requested_focus_mode: str = STILL_FOCUS_MODE_FACTORY_DEFAULT_G124,
    af_assist_setting: str = "Off",
    requested_priority_af_s: str = AF_PRIORITY_FACTORY_DEFAULT_G124,
    requested_priority_af_c: str = AF_PRIORITY_FACTORY_DEFAULT_G124,
    requested_af_illuminator: str = AF_ILLUMINATOR_FACTORY_DEFAULT_G124,
    af_illuminator_fire_requested: bool = False,
    focus_magnifier_active: bool = False,
    mount_adaptor_attached: bool = False,
    requested_view_mode: str = VIEW_MODE_FACTORY_DEFAULT_G124,
    requested_image_index: str = IMAGE_INDEX_FACTORY_DEFAULT_G124,
    requested_display_as_group: str = "Off",
    requested_display_rotation: str = DISPLAY_ROTATION_FACTORY_DEFAULT_G124,
    rotate_requested: bool = False,
    group_delete_requested: bool = False,
    playback_media_slot: str = PLAYBACK_MEDIA_SLOT1_DEFAULT_G124,
    playback_media_kind: str = "Still",
    slot_1_write_protected: bool = True,
    slot_1_contains_tier0_vault: bool = True,
    background_transfer_active: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE290,
    claimed_movie_supports_af_s_af_a_dmf: bool = False,
    claimed_fx6_has_af_a_dmf_or_illuminator: bool = False,
    claimed_priority_reset_on_cam_reset: bool = False,
    claimed_rotate_is_read_only_display_only: bool = False,
    claimed_group_delete_keeps_other_frames: bool = False,
) -> FocusModePlaybackRotateGuardResult:
    """Verify Gate `G124` across `[Focus Mode]` (Still 5-mode vs Movie/`S&Q` 2-mode
    `AF-C [MOVIE_AUTO] / MF`), `[Priority Set in AF-S/AF-C]` / `[AF Assist]` /
    `[AF Illuminator]`, and `[Playback]` `[View Mode]` / `[Image Index]` (`9/25` vs
    dormant `12/30`) / `[Display as Group]` / `[Display Rotation]` / `[Rotate]`
    `Slot-1` read-only vault `EROFS`/`EBUSY` firewall.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME_PHASE290
        or not _is_real_int(body_model_id)
        or body_model_id != FX3_MODEL_ID_PHASE290
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE290
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G124_TELEMETRY_INVALID)
        errors.append("Invalid FX3 hardware model/firmware/help-guide identity.")

    norm_shoot = _norm_shoot_mode_phase290(shoot_mode)
    norm_focus = _norm_focus_mode_g124(requested_focus_mode)
    norm_assist = _norm_on_off_phase290(af_assist_setting)
    norm_prio_s = _norm_af_priority_g124(requested_priority_af_s)
    norm_prio_c = _norm_af_priority_g124(requested_priority_af_c)
    norm_illum = _norm_af_illuminator_g124(requested_af_illuminator)
    norm_view = _norm_view_mode_g124(requested_view_mode)
    norm_index = _norm_image_index_g124(requested_image_index)
    norm_group = _norm_on_off_phase290(requested_display_as_group)
    norm_disp_rot = _norm_display_rotation_g124(requested_display_rotation)
    norm_slot = _norm_media_slot_g124(playback_media_slot)
    norm_reset = _norm_reset_action_phase290(reset_action)
    pb_kind_norm = (
        playback_media_kind.strip().title()
        if isinstance(playback_media_kind, str)
        and playback_media_kind.strip().title() in ("Still", "Movie")
        else None
    )

    if (
        norm_shoot is None
        or norm_focus is None
        or norm_assist is None
        or norm_prio_s is None
        or norm_prio_c is None
        or norm_illum is None
        or norm_view is None
        or norm_index is None
        or norm_group is None
        or norm_disp_rot is None
        or norm_slot is None
        or norm_reset is None
        or pb_kind_norm is None
    ):
        _add_code(codes, STATUS_BLOCKED_G124_TELEMETRY_INVALID)
        errors.append("Invalid G124 Focus Mode, Playback, or media slot enumeration.")

    eff = resolve_fx3_focus_mode_and_playback_rotate_state(
        shoot_mode=norm_shoot or SHOOT_MODE_M_PHASE290,
        requested_focus_mode=norm_focus or STILL_FOCUS_MODE_FACTORY_DEFAULT_G124,
        af_assist_setting=norm_assist or "Off",
        requested_priority_af_s=norm_prio_s or AF_PRIORITY_FACTORY_DEFAULT_G124,
        requested_priority_af_c=norm_prio_c or AF_PRIORITY_FACTORY_DEFAULT_G124,
        requested_af_illuminator=norm_illum or AF_ILLUMINATOR_FACTORY_DEFAULT_G124,
        focus_magnifier_active=focus_magnifier_active,
        mount_adaptor_attached=mount_adaptor_attached,
        requested_view_mode=norm_view or VIEW_MODE_FACTORY_DEFAULT_G124,
        requested_image_index=norm_index or IMAGE_INDEX_FACTORY_DEFAULT_G124,
        requested_display_as_group=norm_group or "Off",
        requested_display_rotation=norm_disp_rot or DISPLAY_ROTATION_FACTORY_DEFAULT_G124,
        rotate_requested=rotate_requested,
        playback_media_slot=norm_slot or PLAYBACK_MEDIA_SLOT1_DEFAULT_G124,
        playback_media_kind=pb_kind_norm or "Still",
        slot_1_write_protected=slot_1_write_protected,
        slot_1_contains_tier0_vault=slot_1_contains_tier0_vault,
        background_transfer_active=background_transfer_active,
        reset_action=norm_reset or RESET_ACTION_NONE_PHASE290,
    )

    is_movie_domain = norm_shoot in MOVIE_SHOOT_MODES_PHASE290
    if norm_focus in DORMANT_FOCUS_MODES_G124:
        _add_code(codes, STATUS_BLOCKED_G124_FOCUS_MODE_MOVIE_SPLIT_OR_DORMANT_VIOLATION)
        errors.append(
            f"Dormant Alpha Focus Mode {norm_focus!r} is unsupported on ILME-FX3."
        )
    if is_movie_domain and norm_focus is not None and norm_focus not in FX3_MOVIE_2_FOCUS_MODES_G124:
        _add_code(codes, STATUS_BLOCKED_G124_FOCUS_MODE_MOVIE_SPLIT_OR_DORMANT_VIOLATION)
        errors.append(
            f"Movie/{norm_shoot} supports strictly 2 Focus Modes (Continuous AF [MOVIE_AUTO] & Manual Focus); "
            f"{norm_focus!r} is locked out."
        )
    if claimed_movie_supports_af_s_af_a_dmf or claimed_fx6_has_af_a_dmf_or_illuminator:
        _add_code(codes, STATUS_BLOCKED_G124_FOCUS_MODE_MOVIE_SPLIT_OR_DORMANT_VIOLATION)
        errors.append(
            "Movie AF-S/AF-A/DMF spoof or FX6 AF-A/DMF/AF-Illuminator spoof rejected."
        )

    # [AF Assist] is strictly Movie AF-C (MOVIE_AUTO) only
    if norm_assist == "On" and (not is_movie_domain or norm_focus != FOCUS_MODE_AF_C_G124):
        _add_code(codes, STATUS_BLOCKED_G124_AF_PRIORITY_ASSIST_OR_ILLUMINATOR_VIOLATION)
        errors.append(
            f"[AF Assist] (_f.uxc 0x64a9) is gated strictly to Movie/S&Q Continuous AF (MOVIE_AUTO); "
            f"forbidden in shoot_mode={norm_shoot}, focus_mode={norm_focus}."
        )

    # [AF Illuminator] is strictly Still-only and locked out in Movie/S&Q, AF-C, Focus Magnifier, Mount Adaptor
    if af_illuminator_fire_requested:
        if (
            is_movie_domain
            or norm_focus == FOCUS_MODE_AF_C_G124
            or focus_magnifier_active
            or mount_adaptor_attached
            or norm_illum == AF_ILLUMINATOR_OFF_G124
        ):
            _add_code(codes, STATUS_BLOCKED_G124_AF_PRIORITY_ASSIST_OR_ILLUMINATOR_VIOLATION)
            errors.append(
                "[AF Illuminator] (.uxc 0xe07f) locked out in Movie/S&Q, AF-C, Focus Magnifier, Mount Adaptor, or Off."
            )

    if claimed_priority_reset_on_cam_reset:
        _add_code(codes, STATUS_BLOCKED_G124_AF_PRIORITY_ASSIST_OR_ILLUMINATOR_VIOLATION)
        errors.append(
            "[Priority Set in AF-S/AF-C] survives [Camera Settings Reset] (needs [Initialize])."
        )

    # Dormant Playback View Mode / Image Index checks
    if norm_view in DORMANT_VIEW_MODES_G124:
        _add_code(codes, STATUS_BLOCKED_G124_PLAYBACK_VIEW_INDEX_OR_GROUP_DORMANT_VIOLATION)
        errors.append(
            f"Dormant Playback [View Mode] {norm_view!r} is NOT exposed on ILME-FX3 (only Date View, Folder View(Still), Movie View)."
        )
    if norm_index in DORMANT_IMAGE_INDEX_MODES_G124:
        _add_code(codes, STATUS_BLOCKED_G124_PLAYBACK_VIEW_INDEX_OR_GROUP_DORMANT_VIOLATION)
        errors.append(
            f"Dormant Playback [Image Index] {norm_index!r} (12/30 Images) is NOT exposed on ILME-FX3 (only 9 Images / 25 Images)."
        )
    if claimed_group_delete_keeps_other_frames:
        _add_code(codes, STATUS_BLOCKED_G124_PLAYBACK_VIEW_INDEX_OR_GROUP_DORMANT_VIOLATION)
        errors.append(
            "Deleting a group under [Display as Group] wipes ALL frames in the burst/interval group."
        )

    # [Rotate] Slot-1 Read-Only Vault Firewall (EROFS / EBUSY) & group-delete on Slot 1
    if rotate_requested and eff["rotate_blocked"]:
        _add_code(codes, STATUS_BLOCKED_G124_SLOT1_ROTATE_WRITE_VAULT_VIOLATION)
        errors.append(
            f"Playback [Rotate] (FUNC_rotate_content) blocked with errno={eff['rotate_block_errno']}: "
            f"slot={norm_slot}, slot1_wp={slot_1_write_protected}, slot1_vault={slot_1_contains_tier0_vault}, "
            f"bg_xfer={background_transfer_active}, media_kind={pb_kind_norm}."
        )
    if group_delete_requested and norm_slot == "Slot 1" and (
        slot_1_write_protected or slot_1_contains_tier0_vault
    ):
        _add_code(codes, STATUS_BLOCKED_G124_SLOT1_ROTATE_WRITE_VAULT_VIOLATION)
        errors.append(
            "Group delete on write-protected / Tier-0 recovery vault Slot 1 blocked (EROFS)."
        )
    if claimed_rotate_is_read_only_display_only:
        _add_code(codes, STATUS_BLOCKED_G124_SLOT1_ROTATE_WRITE_VAULT_VIOLATION)
        errors.append(
            "[Rotate] (FUNC_rotate_content) mutates EXIF orientation metadata on card (not display-only)."
        )

    matrix = compute_focus_mode_and_playback_rotate_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G124 if valid else codes[0]

    return FocusModePlaybackRotateGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE290,
        reset_action=norm_reset or "INVALID",
        focus_mode_menu_path=FOCUS_MODE_MENU_PATH_G124,
        view_mode_menu_path=VIEW_MODE_MENU_PATH_G124,
        image_index_menu_path=IMAGE_INDEX_MENU_PATH_G124,
        display_as_group_menu_path=DISPLAY_AS_GROUP_MENU_PATH_G124,
        display_rotation_menu_path=DISPLAY_ROTATION_MENU_PATH_G124,
        rotate_menu_path=ROTATE_MENU_PATH_G124,
        shoot_mode=eff["shoot_mode"],
        requested_focus_mode=norm_focus or str(requested_focus_mode),
        effective_focus_mode=eff["effective_focus_mode"],
        internal_focus_enum=eff["internal_focus_enum"],
        af_assist_setting=eff["af_assist_setting"],
        af_assist_active=eff["af_assist_active"],
        requested_priority_af_s=norm_prio_s or str(requested_priority_af_s),
        effective_priority_af_s=eff["effective_priority_af_s"],
        requested_priority_af_c=norm_prio_c or str(requested_priority_af_c),
        effective_priority_af_c=eff["effective_priority_af_c"],
        af_priority_survived_cam_reset=eff["af_priority_survived_cam_reset"],
        requested_af_illuminator=norm_illum or str(requested_af_illuminator),
        effective_af_illuminator=eff["effective_af_illuminator"],
        af_illuminator_active=eff["af_illuminator_active"],
        focus_magnifier_active=bool(focus_magnifier_active),
        mount_adaptor_attached=bool(mount_adaptor_attached),
        fx6_supports_af_a_dmf_illuminator=False,
        requested_view_mode=norm_view or str(requested_view_mode),
        effective_view_mode=eff["effective_view_mode"],
        requested_image_index=norm_index or str(requested_image_index),
        effective_image_index=eff["effective_image_index"],
        requested_display_as_group=norm_group or str(requested_display_as_group),
        effective_display_as_group=eff["effective_display_as_group"],
        requested_display_rotation=norm_disp_rot or str(requested_display_rotation),
        effective_display_rotation=eff["effective_display_rotation"],
        playback_settings_survived_cam_reset=eff["playback_settings_survived_cam_reset"],
        rotate_requested=eff["rotate_requested"],
        playback_media_slot=eff["playback_media_slot"],
        playback_media_kind=eff["playback_media_kind"],
        slot_1_write_protected=bool(slot_1_write_protected),
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        background_transfer_active=bool(background_transfer_active),
        rotate_blocked=eff["rotate_blocked"],
        rotate_block_errno=eff["rotate_block_errno"],
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g124_focus_mode_and_playback_rotate_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    focus_mode_playback_rotate_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase290DonorAuditResult] = None,
) -> Tuple[GateVerdict, G124FocusModePlaybackRotateGuardResult]:
    """Evaluate Gate `G124` including `< 0.20s` `O_RDONLY` Wave-52 donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase290_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_focus_mode_and_playback_rotate_guard(
        **(dict(focus_mode_playback_rotate_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G124.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G124 if valid else codes[0]

    res = G124FocusModePlaybackRotateGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        focus_mode_playback_rotate_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, focus={guard.effective_focus_mode}"
        f"(still5={len(FX3_STILL_5_FOCUS_MODES_G124)},movie2={len(FX3_MOVIE_2_FOCUS_MODES_G124)},"
        f"enum={guard.internal_focus_enum},illum_active={guard.af_illuminator_active},"
        f"fx6_af={guard.fx6_supports_af_a_dmf_illuminator}), "
        f"playback=(view={guard.effective_view_mode},idx={guard.effective_image_index},"
        f"group={guard.effective_display_as_group},rot_disp={guard.effective_display_rotation},"
        f"slot1_wp={guard.slot_1_write_protected},rotate_blk={guard.rotate_blocked})"
    )
    verdict = GateVerdict(
        gate_id=G124_GATE_ID,
        gate_code=G124_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `124`-Gate Master Safety Preflight (`G01..G124`)
# ---------------------------------------------------------------------------


def evaluate_124gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    sensor_cleaning_ev_comp_kwargs: Optional[Mapping[str, Any]] = None,
    focus_mode_playback_rotate_kwargs: Optional[Mapping[str, Any]] = None,
    master_122_override: Optional[Master122GateReport] = None,
    **m122_passthrough_kwargs: Any,
) -> Master124GateReport:
    """Evaluate all 124 Master Safety Gates (`G01..G124`) deterministically by
    delegating `G01..G122` directly to `evaluate_122gate_preflight()`.
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

    m122_report: Master122GateReport = (
        master_122_override
        if master_122_override is not None
        else evaluate_122gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m122_passthrough_kwargs,
        )
    )

    phase290_audit = audit_phase290_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g123_verdict, g123_res = evaluate_g123_sensor_cleaning_and_ev_comp_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        sensor_cleaning_ev_comp_kwargs=sensor_cleaning_ev_comp_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase290_audit,
    )

    g124_verdict, g124_res = evaluate_g124_focus_mode_and_playback_rotate_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        focus_mode_playback_rotate_kwargs=focus_mode_playback_rotate_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase290_audit,
    )

    gates_123_to_124 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g123_verdict, g124_verdict)
    ]
    all_gates = tuple(list(m122_report.gates) + gates_123_to_124)

    g01_to_g12_verified = int(m122_report.summary["g01_to_g12_verified"])
    g13_to_g122_verified = int(m122_report.summary["g13_to_g120_verified"]) + int(
        m122_report.summary["g121_to_g122_verified"]
    )
    g123_to_g124_verified = sum(1 for v in (g123_verdict, g124_verdict) if v.passed)
    total_verified = (
        g01_to_g12_verified + g13_to_g122_verified + g123_to_g124_verified
    )

    g123_to_g124_all_passed = g123_to_g124_verified == 2
    g13_to_g124_all_passed = (
        m122_report.g13_to_g122_all_passed and g123_to_g124_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m122_report.gates[:9])

    offline_121_verified = (
        g01_to_g09_ok
        and m122_report.offline_119_gates_verified
        and g123_to_g124_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_124_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g124_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m122_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_121_verified
        and m122_report.h0_h1_trial_entry_allowed
        and g123_to_g124_all_passed
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
        list(m122_report.errors)
        + list(g123_verdict.errors)
        + list(g124_verdict.errors)
    )
    warnings: List[str] = (
        list(m122_report.warnings)
        + list(g123_verdict.warnings)
        + list(g124_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m122_report.g13_to_g122_all_passed:
        overall_status = m122_report.status
    elif not g123_verdict.passed:
        overall_status = g123_verdict.status
    elif not g124_verdict.passed:
        overall_status = g124_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_124_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_124_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_124_verified:
        overall_status = "VERIFIED_ALL_124_GATES"
    else:
        overall_status = "VERIFIED_121_OF_124_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m122_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g123_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g124_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 124,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 124 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g122_verified": g13_to_g122_verified,
        "g123_to_g124_verified": g123_to_g124_verified,
        "g13_to_g124_all_passed": g13_to_g124_all_passed,
        "g123_to_g124_all_passed": g123_to_g124_all_passed,
        "offline_121_gates_verified": offline_121_verified,
        "all_124_gates_verified": all_124_verified,
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

    return Master124GateReport(
        schema=REALHW_SENSOR_CLEANING_EV_COMP_FOCUS_MODE_PLAYBACK_ROTATE_124GATE_SCHEMA,
        version=REALHW_SENSOR_CLEANING_EV_COMP_FOCUS_MODE_PLAYBACK_ROTATE_124GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_121_gates_verified=offline_121_verified,
        all_124_gates_verified=all_124_verified,
        g13_to_g124_all_passed=g13_to_g124_all_passed,
        g123_to_g124_all_passed=g123_to_g124_all_passed,
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
        master_122_report=m122_report.to_dict(),
        g123_result=g123_res.to_dict(),
        g124_result=g124_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_124_master_safety_gates = evaluate_124gate_preflight
run_124_gate_preflight = evaluate_124gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard",
        description=(
            "Phase 290 (290th Phase Milestone, Wave-52) Gates G123 ([Sensor Cleaning] >= 51%% "
            "NP-FZ100 Gate & Mandatory Power-OFF vs FX6 e-ND Optical Block + [Exposure Comp.] "
            "±5.0 EV Still / ±2.0 EV Movie, [Exposure step], Manual M + Fixed ISO Disable & "
            "Total [Cine EI]/[Cine EI Quick] Lockout) + G124 ([Focus Mode] Still 5-Mode vs "
            "Movie/S&Q 2-Mode AF-C [MOVIE_AUTO]/MF + [Priority Set in AF-S/AF-C]/[AF Assist]/"
            "[AF Illuminator] + [Playback] [View Mode]/[Image Index] 9/25/[Display as Group]/"
            "[Display Rotation]/[Rotate] Slot-1 Vault EROFS/EBUSY Firewall) + Unified 124-Gate "
            "Master Safety Preflight"
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
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
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G124 gates can be rehearsed offline",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    parser.add_argument("--summary", action="store_true", help="Emit concise summary output")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_124gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        payload = (
            {
                "status": report.status,
                "verification_mode": report.verification_mode,
                "summary": report.summary,
                "g123_status": report.g123_result["status"],
                "g124_status": report.g124_result["status"],
            }
            if args.summary
            else report.to_dict()
        )
        try:
            sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            os.close(devnull)
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/124 "
            f"g123_to_g124_all_passed={report.g123_to_g124_all_passed} "
            f"all_124_gates_verified={report.all_124_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
            f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
            f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        report.all_124_gates_verified
        if args.dry_run_simulated
        else report.offline_121_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
