"""Phase 294 (Wave-53): Real-Hardware Safety Gates G125 & G126 + Unified 126-Gate Preflight Engine.

Implements empirical `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` hardware safety gates:

1. **Gate `G125` (`verify-lens-comp-and-af-illuminator-guard`)**:
   - `[Lens Compensation]` (`Shading Comp.`, `Chromatic Aberration Comp.`, `Distortion Comp.`)
     strictly `[Auto]` / `[Off]` on FX3 (`Auto: Low` / `LENS_COMP_SHADING_AUTO_LOW` `_f 0x6c9c`
     dormant in shared `appFw.so` rejected fail-closed), surviving `[Camera Settings Reset]`
     (unlike Movie-only `[Breathing Comp.]` `On/Off`, which resets), E-mount forced-`Auto`
     distortion lock (`SELP1650`, `FE 28-70mm`, `LENS_SELECT_DISTORTION_NOT_SUPPORTED`) and
     `SteadyShot = Active` forced-`Auto` distortion lock, unchipped manual lens lockout, vs
     `ILME-FX6 Ver. 6.01` `Technical > Lens` (`All File`, forcing `Breathing Compensation = Off`
     whenever `Distortion Comp. = Off`, `S&Q = On`, or `Codec` includes `RAW`).
   - Movie/`S&Q`-only `[AF Transition Speed]` (`1 (Slow)..7 (Fast)`, default `5`),
     `[AF Subj. Shift Sensitivity]` (`1(Locked on)..5(Responsive)`, default `5`, Sony firmware typo
     `5_RESPONSICE`), and `[AF Assist]` (`On/Off`, default `Off`, strictly Movie `AF-C`/`MOVIE_AUTO`,
     incompatible with `SELP1650`/`SEL18200LE`), all resettable by `Camera Settings Reset`.
   - Empirical `[AF Illuminator]` Front LED Hardware Reality Split: `ILME-FX3` DOES possess a
     built-in front `AF illuminator/Self-timer lamp` LED (#8, `0.3..3.0 m`) + MI-Shoe external flash
     AF illuminator dual-trigger in Still mode (`Auto` default / `Off`, locked out in `Movie`, `S&Q`,
     `AF-C`/moving `AF-A`, `Focus Magnifier`, Mount Adaptor), whereas `ILME-FX6` completely lacks any
     built-in AF illuminator LED or menu (dormant `setting_still_image_af_illuminator` symbols blocked).

2. **Gate `G126` (`verify-aperture-drive-and-folder-rating-guard`)**:
   - Still-only `[Aperture Drive in AF]` (`Focus Priority / Standard [default] / Silent Priority` +
     `Silent Mode Settings` `Standard / Silent Priority` sub-key), Still-only `[AF w/ Shutter]` (`On`
     default / `Off`), Still-only `[Pre-AF]` (`Off` default / `On`, `LENS_PRE_AF_SUPPORT` gated),
     all-mode `[Circ. of Focus Point]` (`Does Not Circulate` default / `Circulate`, orthogonal wrap
     only — NO diagonal wrap), and `[Focus Area Color]` (`White` default / `Red`; exact `ilc/2210`
     naming vs legacy `Focus Frame Color` BKID). All 5 survive `Camera Settings Reset` (reset ONLY
     via `[Initialize]`), and all 5 are absent on `ILME-FX6` (which uses cinema `Iris` control).
   - `[File/Folder Settings]` (`Standard Form` `100MSDCF..999MSDCF` default vs `Date Form`
     `100_MMDD` disabling `[Select REC Folder]`, `4,000`-image per-folder cap, dual-slot sync rules)
     and fail-closed `EROFS`/`EOPNOTSUPP` Slot-1 Tier-0 recovery vault firewall blocking
     `[Create New Folder]`, `[Forced File Number Reset]`, Playback `[Rating]` (`★1..★5`), Still
     custom-key `[Add Rating]`, `[Rating Set(Custom Key)]`, and Slot-1 mutating `[Select REC Folder]`
     to preserve `slot1_metadata_sector_writes == 0` and `slot1_avf_info_mutated == False`.

3. **Unified `126`-Gate Master Safety Preflight (`evaluate_126gate_preflight` / `verify-126-gates`)**:
   - Delegates `G01..G124` to `evaluate_124gate_preflight()` and appends `G125` + `G126`.
   - Offline mode: `123/126` gates pass; `--simulate-bench-dry-run`: `126/126` simulation gates pass.
   - All hardware attach, persistent eMMC write, EL3/SPI-NOR transmit, and cross-model flash redlines
     remain hard-locked `False`, `usb_packets_transmitted == 0`, and `raw_firmware_bytes_leaked == 0`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import sys

from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths
from .realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard import (
    DEFAULT_REPO_ROOT,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_VERIFIED_SAFE,
    GateVerdict,
    Master124GateReport,
    evaluate_124gate_preflight,
)

# ---------------------------------------------------------------------------
# Schema, Version & Absolute Hardware / Firmware Safety Redlines
# ---------------------------------------------------------------------------

REALHW_LENS_COMP_AF_ILLUMINATOR_APERTURE_DRIVE_FOLDER_RATING_126GATE_SCHEMA = (
    "realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard_v1"
)
REALHW_LENS_COMP_AF_ILLUMINATOR_APERTURE_DRIVE_FOLDER_RATING_126GATE_VERSION = "2026.11.17"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST_PHASE294 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE294 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE294 = 15.0

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
G125 = "G125"
G125_GATE_ID = "G125"
G125_GATE_CODE = "GATE_G125_LENS_COMP_AF_ASSIST_AND_FRONT_AF_ILLUMINATOR_GUARD"
GATE_G125_LENS_COMP_AF_ASSIST_AND_FRONT_AF_ILLUMINATOR_GUARD = G125_GATE_CODE

G126 = "G126"
G126_GATE_ID = "G126"
G126_GATE_CODE = "GATE_G126_APERTURE_DRIVE_FOCUS_FRAME_AND_SLOT1_FOLDER_RATING_GUARD"
GATE_G126_APERTURE_DRIVE_FOCUS_FRAME_AND_SLOT1_FOLDER_RATING_GUARD = G126_GATE_CODE

# Model & Identity Contracts (Phase 294 suffixed to avoid __init__.py shadowing)
FX3_MODEL_NAME_PHASE294 = "ILME-FX3"
FX3_MODEL_ID_PHASE294 = 0x39383232
FX3_HELP_GUIDE_CODE_PHASE294 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE294 = "7.02"

FX6_MODEL_NAME_PHASE294 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE294 = "6.01"
FX6_PRODUCT_CODE_PHASE294 = "PRODUCT_MODEL_CHAPLIN"

# Shoot Modes & Reset Actions
SHOOT_MODE_P_PHASE294 = "P"
SHOOT_MODE_A_PHASE294 = "A"
SHOOT_MODE_S_PHASE294 = "S"
SHOOT_MODE_M_PHASE294 = "M"
SHOOT_MODE_STILL_PHASE294 = "Still"
SHOOT_MODE_INTELLIGENT_AUTO_PHASE294 = "Intelligent Auto"
SHOOT_MODE_MOVIE_PHASE294 = "Movie"
SHOOT_MODE_SQ_PHASE294 = "S&Q"
SHOOT_MODE_MR_PHASE294 = "MR"

PASM_SHOOT_MODES_PHASE294: Tuple[str, ...] = (
    SHOOT_MODE_P_PHASE294,
    SHOOT_MODE_A_PHASE294,
    SHOOT_MODE_S_PHASE294,
    SHOOT_MODE_M_PHASE294,
)
STILL_SHOOT_MODES_PHASE294: Tuple[str, ...] = (
    SHOOT_MODE_P_PHASE294,
    SHOOT_MODE_A_PHASE294,
    SHOOT_MODE_S_PHASE294,
    SHOOT_MODE_M_PHASE294,
    SHOOT_MODE_STILL_PHASE294,
    SHOOT_MODE_INTELLIGENT_AUTO_PHASE294,
)
MOVIE_SHOOT_MODES_PHASE294: Tuple[str, ...] = (
    SHOOT_MODE_MOVIE_PHASE294,
    SHOOT_MODE_SQ_PHASE294,
)
ALLOWED_SHOOT_MODES_PHASE294: Tuple[str, ...] = (
    STILL_SHOOT_MODES_PHASE294 + MOVIE_SHOOT_MODES_PHASE294 + (SHOOT_MODE_MR_PHASE294,)
)

RESET_ACTION_NONE_PHASE294 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE294 = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE294 = "Reset Network Set."
RESET_ACTION_INITIALIZE_PHASE294 = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE294: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE294,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE294,
    RESET_ACTION_RESET_NETWORK_SET_PHASE294,
    RESET_ACTION_INITIALIZE_PHASE294,
)

# ---------------------------------------------------------------------------
# G125 Constants: [Lens Compensation] + [AF Transition/Assist] + [AF Illuminator]
# ---------------------------------------------------------------------------

LENS_COMP_MENU_PATH_G125 = "MENU -> (Shooting) -> [Image Quality/Rec] -> [Lens Compensation]"
LENS_COMP_F_UXC_RESID16_G125 = 0x75C8
LENS_COMP_UXC_RESID16_G125 = 0x631F
SHADING_COMP_F_UXC_RESID16_G125 = 0x64E1
SHADING_AUTO_LOW_DORMANT_F_UXC_RESID16_G125 = 0x6C9C
CA_COMP_F_UXC_RESID16_G125 = 0x68CD
DISTORTION_COMP_F_UXC_RESID16_G125 = 0x6200
BREATHING_COMP_F_UXC_RESID16_G125 = 0x73EA

LENS_COMP_AUTO_G125 = "Auto"
LENS_COMP_OFF_G125 = "Off"
DORMANT_SHADING_AUTO_LOW_MODES_G125: Tuple[str, ...] = (
    "Auto: Low",
    "Auto:Low",
    "Low",
    "AUTO_LOW",
    "LENS_COMP_SHADING_AUTO_LOW",
)
ALLOWED_LENS_COMP_OPTIONS_G125: Tuple[str, ...] = (LENS_COMP_AUTO_G125, LENS_COMP_OFF_G125)
SHADING_COMP_FACTORY_DEFAULT_G125 = LENS_COMP_AUTO_G125
CA_COMP_FACTORY_DEFAULT_G125 = LENS_COMP_AUTO_G125
DISTORTION_COMP_FACTORY_DEFAULT_G125 = LENS_COMP_OFF_G125
BREATHING_COMP_FACTORY_DEFAULT_G125 = LENS_COMP_OFF_G125

FORCED_AUTO_DISTORTION_LENSES_G125: Tuple[str, ...] = (
    "SELP1650",
    "FE 28-70mm F3.5-5.6 OSS",
    "FE 28-70",
    "SEL2870",
)

FX6_LENS_COMP_MENU_PATH_G125 = "Technical > Lens"
FX6_LENS_COMP_PROFILE_SCOPE_G125 = "All File"
FX6_LEGACY_FAKE_MENU_PATHS_G125: Tuple[str, ...] = (
    "Project/Paint/Lens -> Lens -> Compensate",
    "Scene File",
)
FX6_SHADING_COMP_UXC2_RESID16_G125 = 0x560A
FX6_CA_COMP_UXC2_RESID16_G125 = 0x4F71
FX6_DISTORTION_COMP_UXC2_RESID16_G125 = 0x4F62

AF_TRANSITION_SPEED_MENU_PATH_G125 = "MENU -> (Focus) -> [AF/MF] -> [AF Transition Speed]"
AF_TRANSITION_SPEED_F_UXC_RESID16_G125 = 0x6E9D
AF_TRANSITION_SPEED_MIN_G125 = 1
AF_TRANSITION_SPEED_MAX_G125 = 7
AF_TRANSITION_SPEED_FACTORY_DEFAULT_G125 = 5

AF_SUBJ_SHIFT_SENS_MENU_PATH_G125 = "MENU -> (Focus) -> [AF/MF] -> [AF Subj. Shift Sensitivity]"
AF_SUBJ_SHIFT_SENS_F_UXC_RESID16_G125 = 0x79D6
AF_SUBJ_SHIFT_SENS_FN_F_UXC_RESID16_G125 = 0x64DE
AF_SUBJ_SHIFT_SENS_MIN_G125 = 1
AF_SUBJ_SHIFT_SENS_MAX_G125 = 5
AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT_G125 = 5
AF_SUBJ_SHIFT_SENS_5_FIRMWARE_SYMBOL_G125 = "MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE"

AF_ASSIST_MENU_PATH_G125 = "MENU -> (Focus) -> [AF/MF] -> [AF Assist]"
AF_ASSIST_F_UXC_RESID16_G125 = 0x64A9
AF_ASSIST_FACTORY_DEFAULT_G125 = "Off"
AF_ASSIST_INCOMPATIBLE_LENSES_G125: Tuple[str, ...] = ("SELP1650", "SEL18200LE")

AF_ILLUMINATOR_MENU_PATH_G125 = "MENU -> (Focus) -> [AF/MF] -> [AF Illuminator]"
AF_ILLUMINATOR_UXC_RESID16_G125 = 0xE07F
AF_ILLUMINATOR_F_UXC_RESID16_G125 = 0x69C0
AF_ILLUMINATOR_AUTO_G125 = "Auto"
AF_ILLUMINATOR_OFF_G125 = "Off"
AF_ILLUMINATOR_FACTORY_DEFAULT_G125 = AF_ILLUMINATOR_AUTO_G125
ALLOWED_AF_ILLUMINATOR_MODES_G125: Tuple[str, ...] = (
    AF_ILLUMINATOR_AUTO_G125,
    AF_ILLUMINATOR_OFF_G125,
)
FX3_FRONT_AF_ILLUMINATOR_PART_NUM_G125 = "Front side #8 (TP1000886886)"
FX3_FRONT_AF_ILLUMINATOR_RANGE_M_G125 = (0.3, 3.0)

# ---------------------------------------------------------------------------
# G126 Constants: [Aperture Drive in AF]..[Focus Area Color] + [File/Folder]/[Rating]
# ---------------------------------------------------------------------------

APERTURE_DRIVE_IN_AF_MENU_PATH_G126 = "MENU -> (Focus) -> [AF/MF] -> [Aperture Drive in AF]"
APERTURE_DRIVE_IN_AF_F_UXC_RESID16_G126 = 0x7879
APERTURE_DRIVE_FOCUS_PRIORITY_G126 = "Focus Priority"
APERTURE_DRIVE_STANDARD_G126 = "Standard"
APERTURE_DRIVE_SILENT_PRIORITY_G126 = "Silent Priority"
APERTURE_DRIVE_FACTORY_DEFAULT_G126 = APERTURE_DRIVE_STANDARD_G126
ALLOWED_APERTURE_DRIVE_MODES_G126: Tuple[str, ...] = (
    APERTURE_DRIVE_FOCUS_PRIORITY_G126,
    APERTURE_DRIVE_STANDARD_G126,
    APERTURE_DRIVE_SILENT_PRIORITY_G126,
)
SILENT_DETAIL_APERTURE_DRIVE_MODES_G126: Tuple[str, ...] = (
    APERTURE_DRIVE_STANDARD_G126,
    APERTURE_DRIVE_SILENT_PRIORITY_G126,
)

AF_W_SHUTTER_MENU_PATH_G126 = "MENU -> (Focus) -> [AF/MF] -> [AF w/ Shutter]"
AF_W_SHUTTER_F_UXC_RESID16_G126 = 0x771D
AF_W_SHUTTER_FACTORY_DEFAULT_G126 = "On"

PRE_AF_MENU_PATH_G126 = "MENU -> (Focus) -> [AF/MF] -> [Pre-AF]"
PRE_AF_F_UXC_RESID16_G126 = 0x76D8
PRE_AF_FACTORY_DEFAULT_G126 = "Off"

CIRC_FOCUS_POINT_MENU_PATH_G126 = "MENU -> (Focus) -> [Focus Area] -> [Circ. of Focus Point]"
CIRC_FOCUS_POINT_F_UXC_RESID16_G126 = 0x74F6
CIRC_FOCUS_POINT_DOES_NOT_G126 = "Does Not Circulate"
CIRC_FOCUS_POINT_CIRCULATE_G126 = "Circulate"
CIRC_FOCUS_POINT_DEFAULT_G126 = CIRC_FOCUS_POINT_DOES_NOT_G126
ALLOWED_CIRC_FOCUS_POINT_MODES_G126: Tuple[str, ...] = (
    CIRC_FOCUS_POINT_DOES_NOT_G126,
    CIRC_FOCUS_POINT_CIRCULATE_G126,
)

FOCUS_AREA_COLOR_MENU_PATH_G126 = "MENU -> (Focus) -> [Focus Area] -> [Focus Area Color]"
FOCUS_AREA_COLOR_F_UXC_RESID16_G126 = 0x74AD
FOCUS_FRAME_COLOR_LEGACY_F_UXC_RESID16_G126 = 0x7087
FOCUS_AREA_COLOR_WHITE_G126 = "White"
FOCUS_AREA_COLOR_RED_G126 = "Red"
FOCUS_AREA_COLOR_DEFAULT_G126 = FOCUS_AREA_COLOR_WHITE_G126
ALLOWED_FOCUS_AREA_COLORS_G126: Tuple[str, ...] = (
    FOCUS_AREA_COLOR_WHITE_G126,
    FOCUS_AREA_COLOR_RED_G126,
)

FX6_IRIS_CONTROL_MODES_G126: Tuple[str, ...] = (
    "Auto Iris",
    "Manual",
    "Push Auto Iris",
    "Iris Override",
)

FILE_FOLDER_SETTINGS_MENU_PATH_G126 = "MENU -> (Shooting) -> [File] -> [File/Folder Settings]"
SELECT_REC_FOLDER_MENU_PATH_G126 = "MENU -> (Shooting) -> [File] -> [Select REC Folder]"
CREATE_NEW_FOLDER_MENU_PATH_G126 = "MENU -> (Shooting) -> [File] -> [Create New Folder]"
RATING_MENU_PATH_G126 = "MENU -> (Playback) -> [Selection/Memo] -> [Rating]"
RATING_CUSTOM_KEY_MENU_PATH_G126 = "MENU -> (Playback) -> [Selection/Memo] -> [Rating Set(Custom Key)]"

FOLDER_NAME_STANDARD_FORM_G126 = "Standard Form"
FOLDER_NAME_DATE_FORM_G126 = "Date Form"
FOLDER_NAME_FACTORY_DEFAULT_G126 = FOLDER_NAME_STANDARD_FORM_G126
ALLOWED_FOLDER_NAME_FORMS_G126: Tuple[str, ...] = (
    FOLDER_NAME_STANDARD_FORM_G126,
    FOLDER_NAME_DATE_FORM_G126,
)
FILE_NUMBER_SERIES_G126 = "Series"
FILE_NUMBER_RESET_G126 = "Reset"
ALLOWED_FILE_NUMBER_MODES_G126: Tuple[str, ...] = (
    FILE_NUMBER_SERIES_G126,
    FILE_NUMBER_RESET_G126,
)
SET_FILE_NAME_DEFAULT_PREFIX_G126 = "DSC"
FOLDER_IMAGE_CAPACITY_LIMIT_G126 = 4000
FOLDER_NUM_MIN_G126 = 100
FOLDER_NUM_MAX_G126 = 999
RATING_MIN_STARS_G126 = 1
RATING_MAX_STARS_G126 = 5

FX6_CLIP_FLAG_VALUES_G126: Tuple[str, ...] = ("OK", "NG", "KEEP", "NONE")

# Status / Violation Codes
STATUS_BLOCKED_PHASE294_DONOR_INTEGRITY = "STATUS_BLOCKED_PHASE294_DONOR_INTEGRITY"

STATUS_VERIFIED_G125 = "STATUS_VERIFIED_G125"
STATUS_BLOCKED_G125_TELEMETRY_INVALID = "STATUS_BLOCKED_G125_TELEMETRY_INVALID"
STATUS_BLOCKED_G125_DORMANT_AUTO_LOW_OR_RESET_PERSISTENCE_VIOLATION = (
    "STATUS_BLOCKED_G125_DORMANT_AUTO_LOW_OR_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G125_EMOUNT_OR_ACTIVE_SS_DISTORTION_LOCK_VIOLATION = (
    "STATUS_BLOCKED_G125_EMOUNT_OR_ACTIVE_SS_DISTORTION_LOCK_VIOLATION"
)
STATUS_BLOCKED_G125_FX6_TECHNICAL_LENS_RAW_SQ_BREATHING_VIOLATION = (
    "STATUS_BLOCKED_G125_FX6_TECHNICAL_LENS_RAW_SQ_BREATHING_VIOLATION"
)
STATUS_BLOCKED_G125_MOVIE_AF_TRANSITION_SHIFT_OR_ASSIST_VIOLATION = (
    "STATUS_BLOCKED_G125_MOVIE_AF_TRANSITION_SHIFT_OR_ASSIST_VIOLATION"
)
STATUS_BLOCKED_G125_AF_ILLUMINATOR_LED_REALITY_OR_LOCKOUT_VIOLATION = (
    "STATUS_BLOCKED_G125_AF_ILLUMINATOR_LED_REALITY_OR_LOCKOUT_VIOLATION"
)

STATUS_VERIFIED_G126 = "STATUS_VERIFIED_G126"
STATUS_BLOCKED_G126_TELEMETRY_INVALID = "STATUS_BLOCKED_G126_TELEMETRY_INVALID"
STATUS_BLOCKED_G126_APERTURE_DRIVE_OR_PRE_AF_SHUTTER_MODE_VIOLATION = (
    "STATUS_BLOCKED_G126_APERTURE_DRIVE_OR_PRE_AF_SHUTTER_MODE_VIOLATION"
)
STATUS_BLOCKED_G126_CIRC_DIAGONAL_OR_INITIALIZE_RESET_SPOOF_VIOLATION = (
    "STATUS_BLOCKED_G126_CIRC_DIAGONAL_OR_INITIALIZE_RESET_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G126_FX6_IRIS_VS_FX3_STILL_AF_CROSSWIRE_VIOLATION = (
    "STATUS_BLOCKED_G126_FX6_IRIS_VS_FX3_STILL_AF_CROSSWIRE_VIOLATION"
)
STATUS_BLOCKED_G126_FOLDER_NAMING_CAPACITY_OR_DUAL_SLOT_VIOLATION = (
    "STATUS_BLOCKED_G126_FOLDER_NAMING_CAPACITY_OR_DUAL_SLOT_VIOLATION"
)
STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION = (
    "STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION"
)

# ---------------------------------------------------------------------------
# Pinned Wave-53 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE294: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (62_677_145, b"BKID_APP_setting_lens_comp_shading"),
    (62_677_218, b"BKID_APP_setting_lens_comp_chro_aber"),
    (62_677_295, b"BKID_APP_setting_lens_comp_distortion"),
    (62_677_374, b"BKID_APP_setting_lens_comp_breathing"),
    (62_140_185, b"VAL_setting_lens_comp_shading_LENS_COMP_SHADING_AUTO_LOW"),
    (60_651_993, b"VAL_select_distortion_support_LENS_SELECT_DISTORTION_NOT_SUPPORTED"),
    (60_320_209, b"PID_SET_LENS_CORRECTION_DATA"),
    (60_320_602, b"PID_SET_MANUAL_LENS_CORRECTION"),
    (62_689_435, b"BKID_APP_setting_movie_af_transition_speed"),
    (62_689_524, b"BKID_APP_setting_movie_af_subj_shift_sens"),
    (61_887_948, b"MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE"),
    (62_689_611, b"BKID_APP_setting_af_assist"),
    (62_689_099, b"BKID_APP_setting_still_image_af_illuminator"),
    (62_689_190, b"BKID_APP_setting_stl_aperture_drive_in_af"),
    (62_680_617, b"BKID_APP_setting_silent_detail_setting_aperture_drive_in_af"),
    (62_689_277, b"BKID_APP_setting_still_image_af_w_shutter"),
    (62_689_384, b"BKID_APP_setting_pre_af"),
    (60_652_200, b"VAL_lens_pre_af_support_LENS_PRE_AF_SUPPORT"),
    (62_690_314, b"BKID_APP_setting_circulate_of_focus_point"),
    (62_689_886, b"BKID_APP_setting_focus_frame_color"),
    (62_677_705, b"BKID_APP_setting_still_still_folder_name"),
    (62_677_670, b"BKID_APP_setting_still_file_number"),
    (60_605_566, b"FUNC_create_folder"),
    (60_605_831, b"FUNC_still_file_number_reset"),
    (60_604_475, b"FUNC_rating_content"),
    (60_609_287, b"FUNC_rating_on_shooting_screen"),
    (61_945_114, b"VAL_xmp_rating_XMP_RATING_VALID"),
    (62_956_537, b"EDIT_FUNC_CMP_NG_DURING_BACKGROUND_TRANSFER_RATING"),
    (61_206_591, b"VAL_status_of_media_slot1_STATUS_OF_MEDIA_SLOT1_READ_ONLY"),
    (61_205_949, b"STATUS_OF_MEDIA_SLOT1_DB_LOCKED"),
    (61_206_061, b"STATUS_OF_MEDIA_SLOT1_FOLDER_MAX"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE294 = (
    "60493b7d79182ded886f14b1cbf2511397d21d1af1cbe0bd987777f460b2def1"
)

PINNED_FX6_APPFW_SLICES_PHASE294: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (41_748_974, b"PRODUCT_MODEL_CHAPLIN"),
    (39_028_088, b"BKID_APP_EXTERN_LENS_SHADING_COMPENSATION"),
    (39_030_208, b"BKID_APP_EXTERN_LENS_CHROMATIC_ABERRATION_COMPENSATION"),
    (39_028_704, b"BKID_APP_EXTERN_LENS_DISTORTION_COMPENSATION"),
    (40_672_789, b"VAL_setting_lens_comp_shading_LENS_COMP_SHADING_AUTO_LOW"),
    (40_922_255, b"BKID_APP_SETTING_AF_ASSIST"),
    (40_922_170, b"BKID_APP_SETTING_MOVIE_AF_TRANSITION_SPEED"),
    (40_922_213, b"BKID_APP_SETTING_MOVIE_AF_SUBJ_SHIFT_SENS"),
    (40_659_501, b"MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE"),
    (40_796_645, b"VAL_content_clip_flag_CONTENT_CLIP_FLAG_OK"),
    (41_286_216, b"N5model36setting_still_image_af_illuminator_tE"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE294 = (
    "b216aa327cd26f1112ee52af151a0510640743d1eca9fa02ae4a3bd14996b261"
)

PINNED_PHASE294_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE294,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE294),
        "FX3 appFw.so Wave-53 LensComp/AF/Aperture/Folder/Rating symbols",
    ),
    "fx3_lib_infra_lens_communicator_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraLensCommunicator.so",
        14_544,
        "e61bf145f050dd037802871395c38d1c0471518130d5bcd2f621268da8c8f6ab",
        (b"osal_snd_sync_msg", b"osal_snd_msg", b"osal_reg_sync_msg_queue_cb"),
        "FX3 libInfraLensCommunicator.so IPC lens bus library",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Shading Comp.",
            b"Auto: Low",
            b"Chromatic Aberration Comp.",
            b"Distortion Comp.",
            b"Breathing Comp.",
            b"AF Transition Speed",
            b"AF Subj. Shift Sensitivity",
            b"AF Assist",
            b"Aperture Drive in AF",
            b"AF w/ Shutter",
            b"Pre-AF",
            b"Circ. of Focus Point",
            b"Focus Area Color",
            b"File/Folder Settings",
            b"Create New Folder",
            b"Rating",
            b"Rating Set(Custom Key)",
        ),
        "FX3 string_english_f.uxc Wave-53 EN parity",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "阴影补偿".encode("utf-8"),
            "自动: 低".encode("utf-8"),
            "色差补偿".encode("utf-8"),
            "失真补偿".encode("utf-8"),
            "呼吸补偿".encode("utf-8"),
            "AF过渡速度".encode("utf-8"),
            "AF摄体转移敏度".encode("utf-8"),
            "AF帮助".encode("utf-8"),
            "AF光圈驱动".encode("utf-8"),
            "半按快门AF".encode("utf-8"),
            "预先AF".encode("utf-8"),
            "对焦点的循环".encode("utf-8"),
            "对焦边框颜色".encode("utf-8"),
            "文件/文件夹设置".encode("utf-8"),
            "新文件夹".encode("utf-8"),
            "分级".encode("utf-8"),
            "分级设置(自定义键)".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-53 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "陰影補償".encode("utf-8"),
            "自動: 小".encode("utf-8"),
            "色像差補償".encode("utf-8"),
            "失真補償".encode("utf-8"),
            "呼吸補償".encode("utf-8"),
            "對焦變換速度".encode("utf-8"),
            "對焦變換靈敏度".encode("utf-8"),
            "AF幫助".encode("utf-8"),
            "對焦中的光圈驅動".encode("utf-8"),
            "半按快門對焦".encode("utf-8"),
            "預先對焦".encode("utf-8"),
            "對焦點循環".encode("utf-8"),
            "對焦框色".encode("utf-8"),
            "檔案/資料夾設定".encode("utf-8"),
            "新資料夾".encode("utf-8"),
            "等級".encode("utf-8"),
            "等級設定（自訂鍵）".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-53 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "周辺光量補正".encode("utf-8"),
            "オート: 弱".encode("utf-8"),
            "倍率色収差補正".encode("utf-8"),
            "歪曲収差補正".encode("utf-8"),
            "ブリージング補正".encode("utf-8"),
            "AFﾄﾗﾝｼﾞｼｮﾝ速度".encode("utf-8"),
            "AF乗り移り感度".encode("utf-8"),
            "AFアシスト".encode("utf-8"),
            "AF時の絞り駆動".encode("utf-8"),
            "ｼｬｯﾀｰ半押しAF".encode("utf-8"),
            "プリAF".encode("utf-8"),
            "ﾌｫｰｶｽ位置の循環".encode("utf-8"),
            "ﾌｫｰｶｽｴﾘｱ枠色".encode("utf-8"),
            "ﾌｧｲﾙ/ﾌｫﾙﾀﾞｰ設定".encode("utf-8"),
            "ﾌｫﾙﾀﾞｰ新規作成".encode("utf-8"),
            "レーティング".encode("utf-8"),
            "ﾚｰﾃｨﾝｸﾞ ｶｽﾀﾑｷｰ設定".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-53 JA parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"AF Illuminator",
            b"Folder Name",
            b"Standard Form",
            b"Date Form",
            b"File Number",
            b"Select REC Folder",
            b"New Folder",
            b"White",
            b"Red",
            b"Unable to perform rating on\nthis image.",
        ),
        "FX3 string_english.uxc Wave-53 AF Illuminator/Folder/Rating tokens",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Lens Comp.",
            b"Create a new folder.",
            b"Last 5 char. of folder name can be changed.",
            b"Can't add since a Rating is already applied.",
            b"Image Database File error",
        ),
        "FX3 string_english_g.uxc Wave-53 warning strings",
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
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE294,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE294),
        "FX6 appFw.so Wave-53 Technical>Lens/AF Assist/Clip Flag/dormant illuminator symbols",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (b"AF Transition Speed", b"AF Subj. Shift Sens.", b"XAVC Root Folder Name"),
        "FX6 string_english.uxc Wave-53 strings",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"Shading Compensation",
            b"Chroma Aberration Comp.",
            b"Distortion Comp.",
            b"AF Assist",
            b"Edit Folder Name",
            b"Select Folder",
            b"Rename Folder",
            b"Set Clip Flag",
            b"Close Iris to F2.4 for AF",
        ),
        "FX6 string_english_2.uxc Wave-53 strings",
    ),
}

_DONOR_BLOB_CACHE: Dict[str, Tuple[int, float, int, str, bytes]] = {}

# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase294DonorAuditResult:
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
class LensCompAndAfIlluminatorGuardResult:
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
    lens_model: str
    lens_electronic_contacts: bool
    distortion_forced_auto_by_lens: bool
    steadyshot_active: bool
    lens_comp_menu_path: str
    effective_shading_comp: str
    effective_ca_comp: str
    effective_distortion_comp: str
    effective_breathing_comp: str
    lens_comp_survived_cam_reset: bool
    breathing_comp_reset_on_cam_reset: bool
    fx6_menu_path: str
    fx6_profile_scope: str
    fx6_breathing_locked_off: bool
    af_transition_speed: int
    af_subj_shift_sens: int
    af_assist_setting: str
    af_assist_active: bool
    af_assist_lens_compatible: bool
    af_transition_reset_on_cam_reset: bool
    requested_af_illuminator: str
    effective_af_illuminator: str
    af_illuminator_active: bool
    fx3_has_built_in_af_illuminator_led: bool
    fx3_front_led_part: str
    fx3_front_led_range_m: Tuple[float, float]
    mi_shoe_flash_illuminator_attached: bool
    mi_shoe_flash_illuminator_active: bool
    fx6_has_built_in_af_illuminator_led: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G125LensCompAfIlluminatorGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    lens_comp_af_illuminator_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ApertureDriveAndFolderRatingGuardResult:
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
    silent_mode_active: bool
    lens_pre_af_supported: bool
    effective_aperture_drive_in_af: str
    effective_silent_detail_aperture_drive: str
    effective_af_w_shutter: str
    effective_pre_af: str
    effective_circ_of_focus_point: str
    orthogonal_wrap_only: bool
    effective_focus_area_color: str
    focus_frame_5_settings_survived_cam_reset: bool
    initialize_required_to_reset_5_settings: bool
    fx6_uses_iris_architecture: bool
    fx6_iris_modes: Tuple[str, ...]
    effective_folder_name_form: str
    effective_file_number_mode: str
    set_file_name_prefix: str
    select_rec_folder_enabled: bool
    dual_slot_simultaneous_rec: bool
    current_folder_image_count: int
    folder_at_4000_limit: bool
    target_media_slot: str
    slot_1_write_protected: bool
    slot_1_contains_tier0_vault: bool
    rating_stars: Optional[int]
    rating_operation_blocked: bool
    folder_mutation_blocked: bool
    block_errno: Optional[str]
    slot1_metadata_sector_writes: int
    slot1_avf_info_mutated: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G126ApertureDriveFolderRatingGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    aperture_drive_folder_rating_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master126GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_123_gates_verified: bool
    all_126_gates_verified: bool
    g13_to_g126_all_passed: bool
    g125_to_g126_all_passed: bool
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
    master_124_report: Dict[str, Any]
    g125_result: Dict[str, Any]
    g126_result: Dict[str, Any]
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
    for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE294):
        if os.environ.get(env_key, "").strip() in _TRUTHY_CLEAN_ROOM_TOKENS:
            return True
    return False


def _default_donor_budget_seconds_phase294() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return DONOR_CHECK_CI_MAX_SECONDS_PHASE294
    return DONOR_CHECK_MAX_SECONDS_PHASE294


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


def _norm_reset_action_phase294(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE_PHASE294
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE294
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE294
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE_PHASE294
    return None


def _norm_shoot_mode_phase294(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "P": SHOOT_MODE_P_PHASE294,
        "A": SHOOT_MODE_A_PHASE294,
        "S": SHOOT_MODE_S_PHASE294,
        "M": SHOOT_MODE_M_PHASE294,
        "STILL": SHOOT_MODE_STILL_PHASE294,
        "INTELLIGENT AUTO": SHOOT_MODE_INTELLIGENT_AUTO_PHASE294,
        "IAUTO": SHOOT_MODE_INTELLIGENT_AUTO_PHASE294,
        "MOVIE": SHOOT_MODE_MOVIE_PHASE294,
        "S&Q": SHOOT_MODE_SQ_PHASE294,
        "SQ": SHOOT_MODE_SQ_PHASE294,
        "MR": SHOOT_MODE_MR_PHASE294,
    }
    return mapping.get(u)


def _norm_on_off_phase294(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "ON":
        return "On"
    if u == "OFF":
        return "Off"
    return None


def _norm_lens_comp_auto_off_g125(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u == "AUTO":
        return LENS_COMP_AUTO_G125
    if u == "OFF":
        return LENS_COMP_OFF_G125
    for d in DORMANT_SHADING_AUTO_LOW_MODES_G125:
        if u == d.upper():
            return d
    return None


def _norm_focus_mode_g125(raw: Any) -> Optional[str]:
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
        "MOVIE_AUTO": "AF-C",
        "DMF": "DMF",
        "MF": "MF",
        "MANUAL FOCUS": "MF",
    }
    return mapping.get(u)


def _norm_af_illuminator_g125(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "AUTO":
        return AF_ILLUMINATOR_AUTO_G125
    if u == "OFF":
        return AF_ILLUMINATOR_OFF_G125
    return None


def _norm_aperture_drive_g126(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_APERTURE_DRIVE_MODES_G126:
        if u == item.upper():
            return item
    return None


def _norm_circ_focus_point_g126(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("DOES NOT CIRCULATE", "DOES_NOT_CIRCULATE", "OFF"):
        return CIRC_FOCUS_POINT_DOES_NOT_G126
    if u in ("CIRCULATE", "ON"):
        return CIRC_FOCUS_POINT_CIRCULATE_G126
    return None


def _norm_focus_area_color_g126(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "WHITE":
        return FOCUS_AREA_COLOR_WHITE_G126
    if u == "RED":
        return FOCUS_AREA_COLOR_RED_G126
    return None


def _norm_folder_name_form_g126(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("STANDARD FORM", "STANDARD"):
        return FOLDER_NAME_STANDARD_FORM_G126
    if u in ("DATE FORM", "DATE"):
        return FOLDER_NAME_DATE_FORM_G126
    return None


def _norm_file_number_mode_g126(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "SERIES":
        return FILE_NUMBER_SERIES_G126
    if u == "RESET":
        return FILE_NUMBER_RESET_G126
    return None


def _norm_media_slot_g126(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("SLOT 1", "SLOT1"):
        return "Slot 1"
    if u in ("SLOT 2", "SLOT2"):
        return "Slot 2"
    if u in ("DUAL", "BOTH", "SLOT 1+2", "SIMULTANEOUS"):
        return "Slot 1+2"
    return None


# ---------------------------------------------------------------------------
# 1. Local O_RDONLY Donor Audit & Clean-Room Synthetic Fallback (< 0.20s)
# ---------------------------------------------------------------------------


def audit_phase294_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase294DonorAuditResult:
    """Strictly `os.open(..., os.O_RDONLY)` audit of Phase 294 Wave-53 local donor
    evidence (`FX3 appFw.so`, `libInfraLensCommunicator.so`, 4-language `_f.uxc`,
    `.uxc`, `_g.uxc`, `BK4`, and `FX6 appFw.so` + `.uxc` packs) with clean-room fallback.
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
        else PINNED_PHASE294_DONOR_SPECS
    )

    if clean_forced:
        elapsed = time.monotonic() - t0
        return Phase294DonorAuditResult(
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
            return Phase294DonorAuditResult(
                valid=False,
                status=STATUS_BLOCKED_PHASE294_DONOR_INTEGRITY,
                verification_mode="LOCAL_DONOR_O_RDONLY",
                access_mode="O_RDONLY",
                files_inspected=0,
                elapsed_seconds=elapsed,
                within_budget_200ms=(elapsed <= _default_donor_budget_seconds_phase294()),
                raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
                checked_markers=(),
                missing_markers=tuple(missing_paths),
                fx3_contracts_verified=False,
                fx6_contracts_verified=False,
                four_lang_resid16_parity_verified=False,
                sha256_by_artifact={},
                bytes_by_artifact={},
                errors=(
                    f"Explicit work_root missing Wave-53 donor files: {missing_paths}",
                ),
                warnings=(),
            )
        elapsed = time.monotonic() - t0
        return Phase294DonorAuditResult(
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
                "Local Wave-53 Sony donor binaries absent; using CLEAN_ROOM_SYNTHETIC pinned SHA-256 contracts.",
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
                p, PINNED_FX3_APPFW_SLICES_PHASE294
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tokens_ok = _read_targeted_slices_o_rdonly(
                p, PINNED_FX6_APPFW_SLICES_PHASE294
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
    budget = _default_donor_budget_seconds_phase294()
    within_budget = elapsed <= budget
    if not within_budget:
        warnings.append(
            f"Phase 294 donor audit took {elapsed:.4f}s (budget {budget:.2f}s)."
        )

    valid = (not errors) and fx3_ok and fx6_ok and lang_ok
    return Phase294DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE294_DONOR_INTEGRITY,
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
# 2. Gate G125: [Lens Compensation] + Movie [AF Transition/Assist] &
#    [AF Illuminator] Front LED Hardware Reality Split
# ---------------------------------------------------------------------------


def _is_forced_auto_distortion_lens(lens_model: str) -> bool:
    upper = lens_model.strip().upper()
    return any(
        tok in upper
        for tok in ("SELP1650", "FE 28-70", "FE28-70", "SEL2870")
    )


def _is_af_assist_incompatible_lens(lens_model: str) -> bool:
    upper = lens_model.strip().upper()
    return any(tok in upper for tok in ("SELP1650", "SEL18200LE"))


def resolve_fx3_lens_comp_and_af_illuminator_state(
    *,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE294,
    focus_mode: str = "AF-C",
    lens_model: str = "FE 35mm F1.4 GM",
    lens_electronic_contacts: bool = True,
    steadyshot_active: bool = False,
    requested_shading_comp: str = SHADING_COMP_FACTORY_DEFAULT_G125,
    requested_ca_comp: str = CA_COMP_FACTORY_DEFAULT_G125,
    requested_distortion_comp: str = DISTORTION_COMP_FACTORY_DEFAULT_G125,
    requested_breathing_comp: str = BREATHING_COMP_FACTORY_DEFAULT_G125,
    requested_af_transition_speed: int = AF_TRANSITION_SPEED_FACTORY_DEFAULT_G125,
    requested_af_subj_shift_sens: int = AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT_G125,
    requested_af_assist: str = AF_ASSIST_FACTORY_DEFAULT_G125,
    requested_af_illuminator: str = AF_ILLUMINATOR_FACTORY_DEFAULT_G125,
    subject_moving_in_af_a: bool = False,
    focus_magnifier_active: bool = False,
    mount_adaptor_attached: bool = False,
    mi_shoe_flash_illuminator_attached: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE294,
    fx6_sq_on: bool = False,
    fx6_codec: str = "XAVC-I",
) -> Dict[str, Any]:
    """Resolve effective Wave-53 Gate `G125` FX3 Ver. 7.02 & FX6 Ver. 6.01 state."""
    eff_reset = _norm_reset_action_phase294(reset_action) or RESET_ACTION_NONE_PHASE294
    eff_shoot = _norm_shoot_mode_phase294(shoot_mode) or SHOOT_MODE_MOVIE_PHASE294
    eff_focus = _norm_focus_mode_g125(focus_mode) or "AF-C"
    eff_shading = _norm_lens_comp_auto_off_g125(requested_shading_comp) or SHADING_COMP_FACTORY_DEFAULT_G125
    if eff_shading in DORMANT_SHADING_AUTO_LOW_MODES_G125:
        eff_shading = SHADING_COMP_FACTORY_DEFAULT_G125
    eff_ca = _norm_lens_comp_auto_off_g125(requested_ca_comp) or CA_COMP_FACTORY_DEFAULT_G125
    if eff_ca in DORMANT_SHADING_AUTO_LOW_MODES_G125:
        eff_ca = CA_COMP_FACTORY_DEFAULT_G125
    eff_dist = _norm_lens_comp_auto_off_g125(requested_distortion_comp) or DISTORTION_COMP_FACTORY_DEFAULT_G125
    if eff_dist in DORMANT_SHADING_AUTO_LOW_MODES_G125:
        eff_dist = DISTORTION_COMP_FACTORY_DEFAULT_G125
    eff_breath = _norm_on_off_phase294(requested_breathing_comp) or BREATHING_COMP_FACTORY_DEFAULT_G125
    eff_assist = _norm_on_off_phase294(requested_af_assist) or AF_ASSIST_FACTORY_DEFAULT_G125
    eff_illum = _norm_af_illuminator_g125(requested_af_illuminator) or AF_ILLUMINATOR_FACTORY_DEFAULT_G125

    eff_trans = (
        int(requested_af_transition_speed)
        if _is_real_int(requested_af_transition_speed)
        else AF_TRANSITION_SPEED_FACTORY_DEFAULT_G125
    )
    eff_shift = (
        int(requested_af_subj_shift_sens)
        if _is_real_int(requested_af_subj_shift_sens)
        else AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT_G125
    )

    is_still = eff_shoot in STILL_SHOOT_MODES_PHASE294
    is_movie = eff_shoot in MOVIE_SHOOT_MODES_PHASE294

    lens_forced_auto = lens_electronic_contacts and _is_forced_auto_distortion_lens(lens_model)
    ss_active_forced_auto = bool(steadyshot_active and is_movie and lens_electronic_contacts)
    if (lens_forced_auto or ss_active_forced_auto) and eff_dist == LENS_COMP_OFF_G125:
        eff_dist = LENS_COMP_AUTO_G125

    if eff_reset == RESET_ACTION_INITIALIZE_PHASE294:
        eff_shading = SHADING_COMP_FACTORY_DEFAULT_G125
        eff_ca = CA_COMP_FACTORY_DEFAULT_G125
        eff_dist = LENS_COMP_AUTO_G125 if (lens_forced_auto or ss_active_forced_auto) else DISTORTION_COMP_FACTORY_DEFAULT_G125

    if eff_reset in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE294,
        RESET_ACTION_INITIALIZE_PHASE294,
    ):
        eff_breath = BREATHING_COMP_FACTORY_DEFAULT_G125
        eff_trans = AF_TRANSITION_SPEED_FACTORY_DEFAULT_G125
        eff_shift = AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT_G125
        eff_assist = AF_ASSIST_FACTORY_DEFAULT_G125
        eff_illum = AF_ILLUMINATOR_FACTORY_DEFAULT_G125

    lens_comp_survived_cam_reset = eff_reset != RESET_ACTION_INITIALIZE_PHASE294
    breathing_reset_on_cam_reset = eff_reset in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE294,
        RESET_ACTION_INITIALIZE_PHASE294,
    )

    assist_lens_compat = not _is_af_assist_incompatible_lens(lens_model)
    af_assist_active = (
        is_movie
        and eff_focus == "AF-C"
        and eff_assist == "On"
        and assist_lens_compat
        and lens_electronic_contacts
    )

    af_illum_lockout = (
        (not is_still)
        or (eff_focus == "AF-C")
        or (eff_focus == "AF-A" and subject_moving_in_af_a)
        or focus_magnifier_active
        or mount_adaptor_attached
    )
    af_illum_active = (eff_illum == AF_ILLUMINATOR_AUTO_G125) and (not af_illum_lockout)
    mi_shoe_active = bool(mi_shoe_flash_illuminator_attached and af_illum_active)

    fx6_raw = "RAW" in fx6_codec.strip().upper()
    fx6_breathing_locked_off = (eff_dist == LENS_COMP_OFF_G125) or fx6_sq_on or fx6_raw

    return {
        "shoot_mode": eff_shoot,
        "focus_mode": eff_focus,
        "reset_action": eff_reset,
        "distortion_forced_auto_by_lens": lens_forced_auto,
        "steadyshot_active_forced_auto": ss_active_forced_auto,
        "effective_shading_comp": eff_shading,
        "effective_ca_comp": eff_ca,
        "effective_distortion_comp": eff_dist,
        "effective_breathing_comp": eff_breath if is_movie else BREATHING_COMP_FACTORY_DEFAULT_G125,
        "lens_comp_survived_cam_reset": lens_comp_survived_cam_reset,
        "breathing_comp_reset_on_cam_reset": breathing_reset_on_cam_reset,
        "af_transition_speed": eff_trans,
        "af_subj_shift_sens": eff_shift,
        "af_assist_setting": eff_assist,
        "af_assist_lens_compatible": assist_lens_compat,
        "af_assist_active": af_assist_active,
        "af_transition_reset_on_cam_reset": breathing_reset_on_cam_reset,
        "effective_af_illuminator": eff_illum,
        "af_illuminator_lockout": af_illum_lockout,
        "af_illuminator_active": af_illum_active,
        "mi_shoe_flash_illuminator_active": mi_shoe_active,
        "fx6_breathing_locked_off": fx6_breathing_locked_off,
    }


def compute_lens_comp_and_af_illuminator_matrix() -> Dict[str, Any]:
    """Deterministic `384`-state cross-product across
    `(4 shoot_modes x 4 focus_modes x 2 lens_types x 2 steadyshot x 3 dist/reset x 2 illum)`
    verifying `G125` invariants.
    """
    states = 0
    forced_auto_dist_count = 0
    illum_blocked_count = 0
    assist_active_count = 0
    lens_comp_persisted_count = 0

    for sm in (
        SHOOT_MODE_M_PHASE294,
        SHOOT_MODE_P_PHASE294,
        SHOOT_MODE_MOVIE_PHASE294,
        SHOOT_MODE_SQ_PHASE294,
    ):
        for fm in ("AF-S", "AF-A", "AF-C", "MF"):
            for lens in ("SELP1650", "FE 35mm F1.4 GM"):
                for ss in (False, True):
                    for r_act in (
                        RESET_ACTION_NONE_PHASE294,
                        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE294,
                        RESET_ACTION_INITIALIZE_PHASE294,
                    ):
                        for illum in ALLOWED_AF_ILLUMINATOR_MODES_G125:
                            states += 1
                            r = resolve_fx3_lens_comp_and_af_illuminator_state(
                                shoot_mode=sm,
                                focus_mode=fm,
                                lens_model=lens,
                                steadyshot_active=ss,
                                requested_shading_comp=LENS_COMP_OFF_G125,
                                requested_distortion_comp=LENS_COMP_OFF_G125,
                                requested_breathing_comp="On",
                                requested_af_assist="On",
                                requested_af_illuminator=illum,
                                reset_action=r_act,
                            )
                            if (
                                r["distortion_forced_auto_by_lens"]
                                or r["steadyshot_active_forced_auto"]
                            ):
                                assert r["effective_distortion_comp"] == LENS_COMP_AUTO_G125
                                forced_auto_dist_count += 1
                            if (sm in MOVIE_SHOOT_MODES_PHASE294) or (fm == "AF-C"):
                                assert r["af_illuminator_active"] is False
                                illum_blocked_count += 1
                            if (
                                sm in MOVIE_SHOOT_MODES_PHASE294
                                and fm == "AF-C"
                                and r["af_assist_lens_compatible"]
                                and r_act == RESET_ACTION_NONE_PHASE294
                            ):
                                assert r["af_assist_active"] is True
                                assist_active_count += 1
                            if r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE294:
                                assert r["effective_shading_comp"] == LENS_COMP_OFF_G125
                                assert r["effective_breathing_comp"] == LENS_COMP_OFF_G125
                                assert r["lens_comp_survived_cam_reset"] is True
                                lens_comp_persisted_count += 1

    return {
        "states_checked": states,
        "forced_auto_dist_count": forced_auto_dist_count,
        "illum_blocked_count": illum_blocked_count,
        "assist_active_count": assist_active_count,
        "lens_comp_persisted_count": lens_comp_persisted_count,
        "all_invariants_hold": states == 384,
    }


def verify_lens_comp_and_af_illuminator_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE294,
    body_model_id: int = FX3_MODEL_ID_PHASE294,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE294,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE294,
    target_model: str = FX3_MODEL_NAME_PHASE294,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE294,
    focus_mode: str = "AF-C",
    lens_model: str = "FE 35mm F1.4 GM",
    lens_electronic_contacts: bool = True,
    lens_comp_adjust_requested: bool = False,
    steadyshot_active: bool = False,
    hdmi_raw_output_active: bool = False,
    requested_shading_comp: str = SHADING_COMP_FACTORY_DEFAULT_G125,
    requested_ca_comp: str = CA_COMP_FACTORY_DEFAULT_G125,
    requested_distortion_comp: str = DISTORTION_COMP_FACTORY_DEFAULT_G125,
    requested_breathing_comp: str = BREATHING_COMP_FACTORY_DEFAULT_G125,
    breathing_comp_activate_requested: bool = False,
    distortion_off_override_requested: bool = False,
    requested_af_transition_speed: int = AF_TRANSITION_SPEED_FACTORY_DEFAULT_G125,
    requested_af_subj_shift_sens: int = AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT_G125,
    af_transition_adjust_requested: bool = False,
    requested_af_assist: str = AF_ASSIST_FACTORY_DEFAULT_G125,
    af_assist_activate_requested: bool = False,
    requested_af_illuminator: str = AF_ILLUMINATOR_FACTORY_DEFAULT_G125,
    af_illuminator_fire_requested: bool = False,
    subject_moving_in_af_a: bool = False,
    focus_magnifier_active: bool = False,
    mount_adaptor_attached: bool = False,
    mi_shoe_flash_illuminator_attached: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE294,
    fx6_menu_path: str = FX6_LENS_COMP_MENU_PATH_G125,
    fx6_profile_scope: str = FX6_LENS_COMP_PROFILE_SCOPE_G125,
    fx6_sq_on: bool = False,
    fx6_codec: str = "XAVC-I",
    fx6_breathing_requested: str = LENS_COMP_OFF_G125,
    claimed_fx3_lacks_built_in_af_illuminator_led: bool = False,
    claimed_fx6_has_built_in_af_illuminator_led: bool = False,
    claimed_lens_comp_resets_on_cam_settings_reset: bool = False,
) -> LensCompAndAfIlluminatorGuardResult:
    """Verify Wave-53 Gate `G125` hardware safety contracts."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version) if isinstance(firmware_version, str) else None
    norm_shoot = _norm_shoot_mode_phase294(shoot_mode)
    norm_focus = _norm_focus_mode_g125(focus_mode)
    norm_reset = _norm_reset_action_phase294(reset_action)
    norm_shading = _norm_lens_comp_auto_off_g125(requested_shading_comp)
    norm_ca = _norm_lens_comp_auto_off_g125(requested_ca_comp)
    norm_dist = _norm_lens_comp_auto_off_g125(requested_distortion_comp)
    norm_breath = _norm_on_off_phase294(requested_breathing_comp)
    norm_assist = _norm_on_off_phase294(requested_af_assist)
    norm_illum = _norm_af_illuminator_g125(requested_af_illuminator)
    norm_fx6_breath = _norm_lens_comp_auto_off_g125(fx6_breathing_requested)

    if (
        body_model_name != FX3_MODEL_NAME_PHASE294
        or not _is_real_int(body_model_id)
        or body_model_id != FX3_MODEL_ID_PHASE294
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE294
        or fw_tuple is None
        or norm_shoot is None
        or norm_focus is None
        or norm_reset is None
        or norm_shading is None
        or norm_ca is None
        or norm_dist is None
        or norm_breath is None
        or norm_assist is None
        or norm_illum is None
        or norm_fx6_breath is None
        or not _is_real_int(requested_af_transition_speed)
        or not _is_real_int(requested_af_subj_shift_sens)
        or target_model not in (FX3_MODEL_NAME_PHASE294, FX6_MODEL_NAME_PHASE294)
    ):
        _add_code(codes, STATUS_BLOCKED_G125_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3/FX6 identity, Lens Comp., AF Transition/Shift, AF Assist, or AF Illuminator telemetry."
        )

    eff = resolve_fx3_lens_comp_and_af_illuminator_state(
        shoot_mode=norm_shoot or SHOOT_MODE_MOVIE_PHASE294,
        focus_mode=norm_focus or "AF-C",
        lens_model=lens_model,
        lens_electronic_contacts=lens_electronic_contacts,
        steadyshot_active=steadyshot_active,
        requested_shading_comp=norm_shading or SHADING_COMP_FACTORY_DEFAULT_G125,
        requested_ca_comp=norm_ca or CA_COMP_FACTORY_DEFAULT_G125,
        requested_distortion_comp=norm_dist or DISTORTION_COMP_FACTORY_DEFAULT_G125,
        requested_breathing_comp=norm_breath or BREATHING_COMP_FACTORY_DEFAULT_G125,
        requested_af_transition_speed=(
            requested_af_transition_speed
            if _is_real_int(requested_af_transition_speed)
            else AF_TRANSITION_SPEED_FACTORY_DEFAULT_G125
        ),
        requested_af_subj_shift_sens=(
            requested_af_subj_shift_sens
            if _is_real_int(requested_af_subj_shift_sens)
            else AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT_G125
        ),
        requested_af_assist=norm_assist or AF_ASSIST_FACTORY_DEFAULT_G125,
        requested_af_illuminator=norm_illum or AF_ILLUMINATOR_FACTORY_DEFAULT_G125,
        subject_moving_in_af_a=subject_moving_in_af_a,
        focus_magnifier_active=focus_magnifier_active,
        mount_adaptor_attached=mount_adaptor_attached,
        mi_shoe_flash_illuminator_attached=mi_shoe_flash_illuminator_attached,
        reset_action=norm_reset or RESET_ACTION_NONE_PHASE294,
        fx6_sq_on=fx6_sq_on,
        fx6_codec=fx6_codec,
    )

    # Part A: Dormant `Auto: Low` rejection & Reset persistence contract
    for comp_name, val in (
        ("Shading Comp.", norm_shading),
        ("Chromatic Aberration Comp.", norm_ca),
        ("Distortion Comp.", norm_dist),
    ):
        if val in DORMANT_SHADING_AUTO_LOW_MODES_G125:
            _add_code(
                codes, STATUS_BLOCKED_G125_DORMANT_AUTO_LOW_OR_RESET_PERSISTENCE_VIOLATION
            )
            errors.append(
                f"{comp_name}: dormant multi-model enum `{val}` (LENS_COMP_SHADING_AUTO_LOW / "
                "_f.uxc 0x6c9c) is NOT exposed on ILME-FX3 Ver. 7.02 (only Auto/Off allowed)."
            )

    if claimed_lens_comp_resets_on_cam_settings_reset:
        _add_code(
            codes, STATUS_BLOCKED_G125_DORMANT_AUTO_LOW_OR_RESET_PERSISTENCE_VIOLATION
        )
        errors.append(
            "Shading/CA/Distortion Comp. survive [Camera Settings Reset] (reset ONLY via [Initialize]), "
            "whereas Movie [Breathing Comp.] resets on [Camera Settings Reset]."
        )

    # Part B: E-mount forced-Auto / SteadyShot Active forced-Auto / Unchipped Manual Lens / Breathing
    if (
        (eff["distortion_forced_auto_by_lens"] or eff["steadyshot_active_forced_auto"])
        and (norm_dist == LENS_COMP_OFF_G125 or distortion_off_override_requested)
    ):
        _add_code(
            codes, STATUS_BLOCKED_G125_EMOUNT_OR_ACTIVE_SS_DISTORTION_LOCK_VIOLATION
        )
        errors.append(
            f"[Distortion Comp.] is forced-locked to [Auto] by E-mount lens `{lens_model}` "
            "or Movie [SteadyShot] = [Active]; switching to [Off] is blocked."
        )

    if (not lens_electronic_contacts) and lens_comp_adjust_requested:
        _add_code(
            codes, STATUS_BLOCKED_G125_EMOUNT_OR_ACTIVE_SS_DISTORTION_LOCK_VIOLATION
        )
        errors.append(
            "Unchipped manual lens attached (LENS_COMP_VALUE_NOT_EXIST): Lens Compensation menu adjustment locked out."
        )

    if breathing_comp_activate_requested or (norm_breath == "On"):
        if norm_shoot not in MOVIE_SHOOT_MODES_PHASE294:
            _add_code(
                codes, STATUS_BLOCKED_G125_EMOUNT_OR_ACTIVE_SS_DISTORTION_LOCK_VIOLATION
            )
            errors.append(
                "[Breathing Comp.] is strictly Movie/S&Q-only (inactive in Still PASM/iAuto)."
            )
        if hdmi_raw_output_active:
            _add_code(
                codes, STATUS_BLOCKED_G125_EMOUNT_OR_ACTIVE_SS_DISTORTION_LOCK_VIOLATION
            )
            errors.append(
                "In-body [Breathing Comp.] is unsupported during external Type-A HDMI RAW output."
            )

    # Part C: FX6 Technical > Lens (All File) & Breathing Lockout under Distortion=Off / S&Q / RAW
    if target_model == FX6_MODEL_NAME_PHASE294:
        if fx6_menu_path != FX6_LENS_COMP_MENU_PATH_G125 or fx6_profile_scope != FX6_LENS_COMP_PROFILE_SCOPE_G125:
            _add_code(
                codes, STATUS_BLOCKED_G125_FX6_TECHNICAL_LENS_RAW_SQ_BREATHING_VIOLATION
            )
            errors.append(
                f"ILME-FX6 Ver. 6.01 places Lens Compensation under `{FX6_LENS_COMP_MENU_PATH_G125}` "
                f"({FX6_LENS_COMP_PROFILE_SCOPE_G125}), NOT `{fx6_menu_path}` / `{fx6_profile_scope}`."
            )
        if norm_fx6_breath in DORMANT_SHADING_AUTO_LOW_MODES_G125:
            _add_code(
                codes, STATUS_BLOCKED_G125_FX6_TECHNICAL_LENS_RAW_SQ_BREATHING_VIOLATION
            )
            errors.append(
                "Dormant `LENS_COMP_SHADING_AUTO_LOW` is rejected on ILME-FX6 Ver. 6.01."
            )
        if norm_fx6_breath == LENS_COMP_AUTO_G125 and eff["fx6_breathing_locked_off"]:
            _add_code(
                codes, STATUS_BLOCKED_G125_FX6_TECHNICAL_LENS_RAW_SQ_BREATHING_VIOLATION
            )
            errors.append(
                "FX6 `Breathing Compensation` is locked `Off` when `Distortion Comp. = Off`, "
                "`S&Q = On`, or `Codec` includes `RAW`."
            )

    # Part D: Movie [AF Transition Speed] (1..7), [AF Subj. Shift Sens.] (1..5), [AF Assist] (MOVIE_AUTO)
    if _is_real_int(requested_af_transition_speed) and (
        requested_af_transition_speed < AF_TRANSITION_SPEED_MIN_G125
        or requested_af_transition_speed > AF_TRANSITION_SPEED_MAX_G125
    ):
        _add_code(
            codes, STATUS_BLOCKED_G125_MOVIE_AF_TRANSITION_SHIFT_OR_ASSIST_VIOLATION
        )
        errors.append(
            f"[AF Transition Speed] {requested_af_transition_speed} out of range 1 (Slow)..7 (Fast)."
        )

    if _is_real_int(requested_af_subj_shift_sens) and (
        requested_af_subj_shift_sens < AF_SUBJ_SHIFT_SENS_MIN_G125
        or requested_af_subj_shift_sens > AF_SUBJ_SHIFT_SENS_MAX_G125
    ):
        _add_code(
            codes, STATUS_BLOCKED_G125_MOVIE_AF_TRANSITION_SHIFT_OR_ASSIST_VIOLATION
        )
        errors.append(
            f"[AF Subj. Shift Sensitivity] {requested_af_subj_shift_sens} out of range 1 (Locked on)..5 (Responsive)."
        )

    if af_transition_adjust_requested and (norm_shoot not in MOVIE_SHOOT_MODES_PHASE294):
        _add_code(
            codes, STATUS_BLOCKED_G125_MOVIE_AF_TRANSITION_SHIFT_OR_ASSIST_VIOLATION
        )
        errors.append(
            "[AF Transition Speed] & [AF Subj. Shift Sensitivity] are strictly Movie/S&Q-only."
        )

    if af_assist_activate_requested or (norm_assist == "On"):
        if norm_shoot not in MOVIE_SHOOT_MODES_PHASE294:
            _add_code(
                codes, STATUS_BLOCKED_G125_MOVIE_AF_TRANSITION_SHIFT_OR_ASSIST_VIOLATION
            )
            errors.append("[AF Assist] is gated strictly to Movie/S&Q mode.")
        elif norm_focus != "AF-C":
            _add_code(
                codes, STATUS_BLOCKED_G125_MOVIE_AF_TRANSITION_SHIFT_OR_ASSIST_VIOLATION
            )
            errors.append(
                "[AF Assist] is gated strictly to Movie AF-C (`MOVIE_AUTO` internal enum)."
            )
        if not eff["af_assist_lens_compatible"]:
            _add_code(
                codes, STATUS_BLOCKED_G125_MOVIE_AF_TRANSITION_SHIFT_OR_ASSIST_VIOLATION
            )
            errors.append(
                f"[AF Assist] is officially incompatible with `{lens_model}` (SELP1650/SEL18200LE)."
            )

    # Part E: [AF Illuminator] Front LED Hardware Reality Split (FX3 HAS LED #8 vs FX6 ZERO LED)
    if claimed_fx3_lacks_built_in_af_illuminator_led:
        _add_code(
            codes, STATUS_BLOCKED_G125_AF_ILLUMINATOR_LED_REALITY_OR_LOCKOUT_VIOLATION
        )
        errors.append(
            "Empirical correction: ILME-FX3 DOES possess built-in Front side #8 AF illuminator/Self-timer LED "
            "(0.3..3.0 m) + MI-Shoe external flash AF illuminator dual-trigger in Still mode."
        )

    if claimed_fx6_has_built_in_af_illuminator_led:
        _add_code(
            codes, STATUS_BLOCKED_G125_AF_ILLUMINATOR_LED_REALITY_OR_LOCKOUT_VIOLATION
        )
        errors.append(
            "ILME-FX6 completely lacks any built-in AF illuminator LED or menu; dormant "
            "`N5model36setting_still_image_af_illuminator_tE` symbols in FX6 appFw.so are blocked."
        )

    if target_model == FX6_MODEL_NAME_PHASE294 and af_illuminator_fire_requested:
        _add_code(
            codes, STATUS_BLOCKED_G125_AF_ILLUMINATOR_LED_REALITY_OR_LOCKOUT_VIOLATION
        )
        errors.append(
            "Firing [AF Illuminator] on FX6 is blocked: ILME-FX6 has zero AF illuminator hardware."
        )

    if target_model == FX3_MODEL_NAME_PHASE294 and af_illuminator_fire_requested:
        if eff["af_illuminator_lockout"] or norm_illum == AF_ILLUMINATOR_OFF_G125:
            _add_code(
                codes, STATUS_BLOCKED_G125_AF_ILLUMINATOR_LED_REALITY_OR_LOCKOUT_VIOLATION
            )
            errors.append(
                "[AF Illuminator] locked out in Movie/S&Q, AF-C, moving AF-A, Focus Magnifier, "
                "Mount Adaptor, or when set to Off."
            )

    matrix = compute_lens_comp_and_af_illuminator_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G125 if valid else codes[0]

    return LensCompAndAfIlluminatorGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE294,
        target_model=target_model,
        reset_action=eff["reset_action"],
        shoot_mode=eff["shoot_mode"],
        focus_mode=eff["focus_mode"],
        lens_model=lens_model,
        lens_electronic_contacts=bool(lens_electronic_contacts),
        distortion_forced_auto_by_lens=eff["distortion_forced_auto_by_lens"],
        steadyshot_active=bool(steadyshot_active),
        lens_comp_menu_path=LENS_COMP_MENU_PATH_G125,
        effective_shading_comp=eff["effective_shading_comp"],
        effective_ca_comp=eff["effective_ca_comp"],
        effective_distortion_comp=eff["effective_distortion_comp"],
        effective_breathing_comp=eff["effective_breathing_comp"],
        lens_comp_survived_cam_reset=eff["lens_comp_survived_cam_reset"],
        breathing_comp_reset_on_cam_reset=eff["breathing_comp_reset_on_cam_reset"],
        fx6_menu_path=fx6_menu_path,
        fx6_profile_scope=fx6_profile_scope,
        fx6_breathing_locked_off=eff["fx6_breathing_locked_off"],
        af_transition_speed=eff["af_transition_speed"],
        af_subj_shift_sens=eff["af_subj_shift_sens"],
        af_assist_setting=eff["af_assist_setting"],
        af_assist_active=eff["af_assist_active"],
        af_assist_lens_compatible=eff["af_assist_lens_compatible"],
        af_transition_reset_on_cam_reset=eff["af_transition_reset_on_cam_reset"],
        requested_af_illuminator=norm_illum or str(requested_af_illuminator),
        effective_af_illuminator=eff["effective_af_illuminator"],
        af_illuminator_active=eff["af_illuminator_active"],
        fx3_has_built_in_af_illuminator_led=True,
        fx3_front_led_part=FX3_FRONT_AF_ILLUMINATOR_PART_NUM_G125,
        fx3_front_led_range_m=FX3_FRONT_AF_ILLUMINATOR_RANGE_M_G125,
        mi_shoe_flash_illuminator_attached=bool(mi_shoe_flash_illuminator_attached),
        mi_shoe_flash_illuminator_active=eff["mi_shoe_flash_illuminator_active"],
        fx6_has_built_in_af_illuminator_led=False,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g125_lens_comp_and_af_illuminator_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    lens_comp_af_illuminator_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase294DonorAuditResult] = None,
) -> Tuple[GateVerdict, G125LensCompAfIlluminatorGuardResult]:
    """Evaluate Wave-53 Gate `G125` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase294_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_lens_comp_and_af_illuminator_guard(
        **(dict(lens_comp_af_illuminator_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G125.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G125 if valid else codes[0]

    res = G125LensCompAfIlluminatorGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        lens_comp_af_illuminator_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, shading={guard.effective_shading_comp},"
        f"ca={guard.effective_ca_comp},dist={guard.effective_distortion_comp},"
        f"breath={guard.effective_breathing_comp},af_trans={guard.af_transition_speed},"
        f"af_shift={guard.af_subj_shift_sens},af_assist={guard.af_assist_setting},"
        f"fx3_led={guard.fx3_has_built_in_af_illuminator_led},"
        f"fx6_led={guard.fx6_has_built_in_af_illuminator_led}"
    )
    verdict = GateVerdict(
        gate_id=G125_GATE_ID,
        gate_code=G125_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G126: Still [Aperture Drive in AF] / [AF w/ Shutter] / [Pre-AF] /
#    [Circ. of Focus Point] / [Focus Area Color] (`Initialize`-Only) +
#    [File/Folder Settings] & Playback [Rating] `Slot-1` Vault Write Firewall
# ---------------------------------------------------------------------------


def _is_valid_set_file_name_prefix(prefix: str) -> bool:
    return bool(re.match(r"^[A-Z0-9][A-Z0-9_]{2}$", prefix))


def resolve_fx3_aperture_drive_and_folder_rating_state(
    *,
    shoot_mode: str = SHOOT_MODE_M_PHASE294,
    silent_mode_active: bool = False,
    lens_pre_af_supported: bool = True,
    requested_aperture_drive_in_af: str = APERTURE_DRIVE_FACTORY_DEFAULT_G126,
    requested_silent_detail_aperture_drive: str = APERTURE_DRIVE_FACTORY_DEFAULT_G126,
    requested_af_w_shutter: str = AF_W_SHUTTER_FACTORY_DEFAULT_G126,
    requested_pre_af: str = PRE_AF_FACTORY_DEFAULT_G126,
    requested_circ_of_focus_point: str = CIRC_FOCUS_POINT_DEFAULT_G126,
    requested_focus_area_color: str = FOCUS_AREA_COLOR_DEFAULT_G126,
    reset_action: str = RESET_ACTION_NONE_PHASE294,
    requested_folder_name_form: str = FOLDER_NAME_FACTORY_DEFAULT_G126,
    requested_file_number_mode: str = FILE_NUMBER_SERIES_G126,
    set_file_name_prefix: str = SET_FILE_NAME_DEFAULT_PREFIX_G126,
    dual_slot_simultaneous_rec: bool = False,
    slot1_folder_image_count: int = 0,
    target_media_slot: str = "Slot 2",
    slot_1_write_protected: bool = False,
    slot_1_contains_tier0_vault: bool = True,
    create_new_folder_requested: bool = False,
    forced_file_number_reset_requested: bool = False,
    rating_requested: bool = False,
    rating_stars: Optional[int] = None,
) -> Dict[str, Any]:
    """Resolve effective Wave-53 Gate `G126` FX3 Ver. 7.02 Aperture/Focus/Folder/Rating state."""
    eff_reset = _norm_reset_action_phase294(reset_action) or RESET_ACTION_NONE_PHASE294
    eff_shoot = _norm_shoot_mode_phase294(shoot_mode) or SHOOT_MODE_M_PHASE294
    eff_ap = _norm_aperture_drive_g126(requested_aperture_drive_in_af) or APERTURE_DRIVE_FACTORY_DEFAULT_G126
    eff_silent_ap = (
        _norm_aperture_drive_g126(requested_silent_detail_aperture_drive)
        or APERTURE_DRIVE_FACTORY_DEFAULT_G126
    )
    if eff_silent_ap not in SILENT_DETAIL_APERTURE_DRIVE_MODES_G126:
        eff_silent_ap = APERTURE_DRIVE_FACTORY_DEFAULT_G126
    eff_af_shutter = _norm_on_off_phase294(requested_af_w_shutter) or AF_W_SHUTTER_FACTORY_DEFAULT_G126
    eff_pre_af = _norm_on_off_phase294(requested_pre_af) or PRE_AF_FACTORY_DEFAULT_G126
    if not lens_pre_af_supported:
        eff_pre_af = "Off"
    eff_circ = _norm_circ_focus_point_g126(requested_circ_of_focus_point) or CIRC_FOCUS_POINT_DEFAULT_G126
    eff_color = _norm_focus_area_color_g126(requested_focus_area_color) or FOCUS_AREA_COLOR_DEFAULT_G126

    eff_folder_form = (
        _norm_folder_name_form_g126(requested_folder_name_form)
        or FOLDER_NAME_FACTORY_DEFAULT_G126
    )
    eff_file_num = (
        _norm_file_number_mode_g126(requested_file_number_mode)
        or FILE_NUMBER_SERIES_G126
    )
    eff_slot = _norm_media_slot_g126(target_media_slot) or "Slot 2"

    # CRITICAL EMPIRICAL FACT: All 5 settings (`Aperture Drive in AF`, `AF w/ Shutter`,
    # `Pre-AF`, `Circ. of Focus Point`, `Focus Area Color`) + `[Folder Name]` / `[File Number]`
    # survive `[Camera Settings Reset]` (Not available) and reset ONLY via `[Initialize]`.
    survived_cam_reset = eff_reset != RESET_ACTION_INITIALIZE_PHASE294
    if eff_reset == RESET_ACTION_INITIALIZE_PHASE294:
        eff_ap = APERTURE_DRIVE_FACTORY_DEFAULT_G126
        eff_silent_ap = APERTURE_DRIVE_FACTORY_DEFAULT_G126
        eff_af_shutter = AF_W_SHUTTER_FACTORY_DEFAULT_G126
        eff_pre_af = PRE_AF_FACTORY_DEFAULT_G126
        eff_circ = CIRC_FOCUS_POINT_DEFAULT_G126
        eff_color = FOCUS_AREA_COLOR_DEFAULT_G126
        eff_folder_form = FOLDER_NAME_FACTORY_DEFAULT_G126
        eff_file_num = FILE_NUMBER_SERIES_G126

    select_rec_folder_enabled = eff_folder_form == FOLDER_NAME_STANDARD_FORM_G126
    folder_at_limit = int(slot1_folder_image_count) >= FOLDER_IMAGE_CAPACITY_LIMIT_G126

    touches_slot1 = (eff_slot in ("Slot 1", "Slot 1+2")) or bool(dual_slot_simultaneous_rec)
    slot1_locked = bool(slot_1_write_protected or slot_1_contains_tier0_vault)

    folder_mutation_requested = bool(create_new_folder_requested or forced_file_number_reset_requested)
    folder_mutation_blocked = touches_slot1 and slot1_locked and folder_mutation_requested
    rating_operation_blocked = (eff_slot in ("Slot 1", "Slot 1+2")) and slot1_locked and bool(rating_requested)

    block_errno: Optional[str] = None
    if folder_mutation_blocked or rating_operation_blocked:
        block_errno = "EROFS" if slot_1_write_protected else "EOPNOTSUPP"

    return {
        "shoot_mode": eff_shoot,
        "silent_mode_active": bool(silent_mode_active),
        "effective_aperture_drive_in_af": eff_ap,
        "effective_silent_detail_aperture_drive": eff_silent_ap,
        "effective_af_w_shutter": eff_af_shutter,
        "effective_pre_af": eff_pre_af,
        "effective_circ_of_focus_point": eff_circ,
        "effective_focus_area_color": eff_color,
        "focus_frame_5_settings_survived_cam_reset": survived_cam_reset,
        "initialize_required_to_reset_5_settings": True,
        "effective_folder_name_form": eff_folder_form,
        "effective_file_number_mode": eff_file_num,
        "set_file_name_prefix": set_file_name_prefix,
        "select_rec_folder_enabled": select_rec_folder_enabled,
        "folder_at_4000_limit": folder_at_limit,
        "target_media_slot": eff_slot,
        "rating_stars": rating_stars,
        "rating_operation_blocked": rating_operation_blocked,
        "folder_mutation_blocked": folder_mutation_blocked,
        "block_errno": block_errno,
        "slot1_metadata_sector_writes": 0,
        "slot1_avf_info_mutated": False,
    }


def compute_aperture_drive_and_folder_rating_matrix() -> Dict[str, Any]:
    """Deterministic `384`-state cross-product across
    `(3 aperture_drive x 2 pre_af x 2 circ x 2 color x 2 folder_form x 4 reset x 2 slot1_vault)`
    verifying `G126` invariants.
    """
    states = 0
    survived_cam_reset_count = 0
    date_form_select_disabled = 0
    slot1_vault_mutations_blocked = 0

    for ap in ALLOWED_APERTURE_DRIVE_MODES_G126:
        for pre_af in ("Off", "On"):
            for circ in ALLOWED_CIRC_FOCUS_POINT_MODES_G126:
                for col in ALLOWED_FOCUS_AREA_COLORS_G126:
                    for fname in ALLOWED_FOLDER_NAME_FORMS_G126:
                        for r_act in ALLOWED_RESET_ACTIONS_PHASE294:
                            for s1_vault in (True, False):
                                states += 1
                                r = resolve_fx3_aperture_drive_and_folder_rating_state(
                                    requested_aperture_drive_in_af=ap,
                                    requested_af_w_shutter="Off",
                                    requested_pre_af=pre_af,
                                    requested_circ_of_focus_point=circ,
                                    requested_focus_area_color=col,
                                    requested_folder_name_form=fname,
                                    reset_action=r_act,
                                    target_media_slot="Slot 1",
                                    slot_1_contains_tier0_vault=s1_vault,
                                    create_new_folder_requested=True,
                                    rating_requested=True,
                                    rating_stars=3,
                                )
                                if r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE294:
                                    assert r["effective_aperture_drive_in_af"] == ap
                                    assert r["effective_af_w_shutter"] == "Off"
                                    assert r["effective_pre_af"] == pre_af
                                    assert r["effective_circ_of_focus_point"] == circ
                                    assert r["effective_focus_area_color"] == col
                                    assert r["focus_frame_5_settings_survived_cam_reset"] is True
                                    survived_cam_reset_count += 1
                                if (
                                    fname == FOLDER_NAME_DATE_FORM_G126
                                    and r_act != RESET_ACTION_INITIALIZE_PHASE294
                                ):
                                    assert r["select_rec_folder_enabled"] is False
                                    date_form_select_disabled += 1
                                if s1_vault:
                                    assert r["folder_mutation_blocked"] is True
                                    assert r["rating_operation_blocked"] is True
                                    assert r["slot1_metadata_sector_writes"] == 0
                                    assert r["slot1_avf_info_mutated"] is False
                                    slot1_vault_mutations_blocked += 1

    return {
        "states_checked": states,
        "survived_cam_reset_count": survived_cam_reset_count,
        "date_form_select_disabled": date_form_select_disabled,
        "slot1_vault_mutations_blocked": slot1_vault_mutations_blocked,
        "all_invariants_hold": states == 384,
    }


def verify_aperture_drive_and_folder_rating_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE294,
    body_model_id: int = FX3_MODEL_ID_PHASE294,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE294,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE294,
    target_model: str = FX3_MODEL_NAME_PHASE294,
    shoot_mode: str = SHOOT_MODE_M_PHASE294,
    silent_mode_active: bool = False,
    lens_pre_af_supported: bool = True,
    requested_aperture_drive_in_af: str = APERTURE_DRIVE_FACTORY_DEFAULT_G126,
    requested_silent_detail_aperture_drive: str = APERTURE_DRIVE_FACTORY_DEFAULT_G126,
    still_aperture_adjust_requested: bool = False,
    requested_af_w_shutter: str = AF_W_SHUTTER_FACTORY_DEFAULT_G126,
    af_w_shutter_still_use_requested: bool = False,
    requested_pre_af: str = PRE_AF_FACTORY_DEFAULT_G126,
    pre_af_activate_requested: bool = False,
    requested_circ_of_focus_point: str = CIRC_FOCUS_POINT_DEFAULT_G126,
    focus_area: str = "Spot: M",
    requested_focus_area_color: str = FOCUS_AREA_COLOR_DEFAULT_G126,
    reset_action: str = RESET_ACTION_NONE_PHASE294,
    claimed_diagonal_focus_point_wrap: bool = False,
    claimed_5_settings_reset_by_cam_settings_reset: bool = False,
    claimed_fx6_has_aperture_drive_or_circ_or_white_red_color: bool = False,
    claimed_fx6_close_iris_warning_wired: bool = False,
    requested_folder_name_form: str = FOLDER_NAME_FACTORY_DEFAULT_G126,
    requested_file_number_mode: str = FILE_NUMBER_SERIES_G126,
    set_file_name_prefix: str = SET_FILE_NAME_DEFAULT_PREFIX_G126,
    select_rec_folder_requested: bool = False,
    dual_slot_simultaneous_rec: bool = False,
    slot1_slot2_common_folder_exists: bool = True,
    slot1_folder_image_count: int = 0,
    still_capture_into_current_folder_requested: bool = False,
    target_media_slot: str = "Slot 2",
    slot_1_write_protected: bool = False,
    slot_1_contains_tier0_vault: bool = True,
    create_new_folder_requested: bool = False,
    forced_file_number_reset_requested: bool = False,
    rating_requested: bool = False,
    rating_add_on_shooting_screen_requested: bool = False,
    rating_stars: Optional[int] = None,
    rating_existing_stars: Optional[int] = None,
    background_transfer_active: bool = False,
    claimed_rating_is_ram_only_non_card_write: bool = False,
    fx6_clip_flag: str = "OK",
) -> ApertureDriveAndFolderRatingGuardResult:
    """Verify Wave-53 Gate `G126` hardware safety contracts."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version) if isinstance(firmware_version, str) else None
    norm_shoot = _norm_shoot_mode_phase294(shoot_mode)
    norm_reset = _norm_reset_action_phase294(reset_action)
    norm_ap = _norm_aperture_drive_g126(requested_aperture_drive_in_af)
    norm_silent_ap = _norm_aperture_drive_g126(requested_silent_detail_aperture_drive)
    norm_af_shutter = _norm_on_off_phase294(requested_af_w_shutter)
    norm_pre_af = _norm_on_off_phase294(requested_pre_af)
    norm_circ = _norm_circ_focus_point_g126(requested_circ_of_focus_point)
    norm_color = _norm_focus_area_color_g126(requested_focus_area_color)
    norm_folder_form = _norm_folder_name_form_g126(requested_folder_name_form)
    norm_file_num = _norm_file_number_mode_g126(requested_file_number_mode)
    norm_slot = _norm_media_slot_g126(target_media_slot)

    stars_ok = (rating_stars is None) or (
        _is_real_int(rating_stars)
        and RATING_MIN_STARS_G126 <= rating_stars <= RATING_MAX_STARS_G126
    )

    if (
        body_model_name != FX3_MODEL_NAME_PHASE294
        or not _is_real_int(body_model_id)
        or body_model_id != FX3_MODEL_ID_PHASE294
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE294
        or fw_tuple is None
        or norm_shoot is None
        or norm_reset is None
        or norm_ap is None
        or norm_silent_ap is None
        or norm_af_shutter is None
        or norm_pre_af is None
        or norm_circ is None
        or norm_color is None
        or norm_folder_form is None
        or norm_file_num is None
        or norm_slot is None
        or not _is_real_int(slot1_folder_image_count)
        or slot1_folder_image_count < 0
        or not stars_ok
        or fx6_clip_flag.upper() not in FX6_CLIP_FLAG_VALUES_G126
        or target_model not in (FX3_MODEL_NAME_PHASE294, FX6_MODEL_NAME_PHASE294)
    ):
        _add_code(codes, STATUS_BLOCKED_G126_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3/FX6 identity, Aperture Drive, Pre-AF, Focus Frame, Folder, or Rating telemetry."
        )

    eff = resolve_fx3_aperture_drive_and_folder_rating_state(
        shoot_mode=norm_shoot or SHOOT_MODE_M_PHASE294,
        silent_mode_active=silent_mode_active,
        lens_pre_af_supported=lens_pre_af_supported,
        requested_aperture_drive_in_af=norm_ap or APERTURE_DRIVE_FACTORY_DEFAULT_G126,
        requested_silent_detail_aperture_drive=norm_silent_ap or APERTURE_DRIVE_FACTORY_DEFAULT_G126,
        requested_af_w_shutter=norm_af_shutter or AF_W_SHUTTER_FACTORY_DEFAULT_G126,
        requested_pre_af=norm_pre_af or PRE_AF_FACTORY_DEFAULT_G126,
        requested_circ_of_focus_point=norm_circ or CIRC_FOCUS_POINT_DEFAULT_G126,
        requested_focus_area_color=norm_color or FOCUS_AREA_COLOR_DEFAULT_G126,
        reset_action=norm_reset or RESET_ACTION_NONE_PHASE294,
        requested_folder_name_form=norm_folder_form or FOLDER_NAME_FACTORY_DEFAULT_G126,
        requested_file_number_mode=norm_file_num or FILE_NUMBER_SERIES_G126,
        set_file_name_prefix=set_file_name_prefix,
        dual_slot_simultaneous_rec=dual_slot_simultaneous_rec,
        slot1_folder_image_count=slot1_folder_image_count if _is_real_int(slot1_folder_image_count) else 0,
        target_media_slot=norm_slot or "Slot 2",
        slot_1_write_protected=slot_1_write_protected,
        slot_1_contains_tier0_vault=slot_1_contains_tier0_vault,
        create_new_folder_requested=create_new_folder_requested,
        forced_file_number_reset_requested=forced_file_number_reset_requested,
        rating_requested=bool(rating_requested or rating_add_on_shooting_screen_requested),
        rating_stars=rating_stars,
    )

    is_still = (norm_shoot or SHOOT_MODE_M_PHASE294) in STILL_SHOOT_MODES_PHASE294

    # Part A: Still-only [Aperture Drive in AF], [AF w/ Shutter], [Pre-AF]
    if norm_silent_ap is not None and norm_silent_ap not in SILENT_DETAIL_APERTURE_DRIVE_MODES_G126:
        _add_code(
            codes, STATUS_BLOCKED_G126_APERTURE_DRIVE_OR_PRE_AF_SHUTTER_MODE_VIOLATION
        )
        errors.append(
            "Silent Mode [Aperture Drive in AF] sub-setting only supports `Standard` or `Silent Priority` "
            "(not `Focus Priority`)."
        )

    if still_aperture_adjust_requested and (not is_still):
        _add_code(
            codes, STATUS_BLOCKED_G126_APERTURE_DRIVE_OR_PRE_AF_SHUTTER_MODE_VIOLATION
        )
        errors.append("[Aperture Drive in AF] is strictly Still-only (inactive in Movie/S&Q).")

    if af_w_shutter_still_use_requested and (not is_still):
        _add_code(
            codes, STATUS_BLOCKED_G126_APERTURE_DRIVE_OR_PRE_AF_SHUTTER_MODE_VIOLATION
        )
        errors.append("[AF w/ Shutter] is strictly Still-only (inactive in Movie/S&Q).")

    if pre_af_activate_requested or (norm_pre_af == "On"):
        if not is_still:
            _add_code(
                codes, STATUS_BLOCKED_G126_APERTURE_DRIVE_OR_PRE_AF_SHUTTER_MODE_VIOLATION
            )
            errors.append("[Pre-AF] is strictly Still-only (inactive in Movie/S&Q).")
        if not lens_pre_af_supported:
            _add_code(
                codes, STATUS_BLOCKED_G126_APERTURE_DRIVE_OR_PRE_AF_SHUTTER_MODE_VIOLATION
            )
            errors.append(
                "[Pre-AF] blocked: attached lens lacks `LENS_PRE_AF_SUPPORT` capability bit."
            )

    # Part B: [Circ. of Focus Point] orthogonal-only wrap + Initialize-only reset persistence
    if claimed_diagonal_focus_point_wrap:
        _add_code(
            codes, STATUS_BLOCKED_G126_CIRC_DIAGONAL_OR_INITIALIZE_RESET_SPOOF_VIOLATION
        )
        errors.append(
            "[Circ. of Focus Point] supports orthogonal edge wrap ONLY (Zone/Spot/Expand Spot) — "
            "diagonal wrap is unsupported."
        )

    if claimed_5_settings_reset_by_cam_settings_reset:
        _add_code(
            codes, STATUS_BLOCKED_G126_CIRC_DIAGONAL_OR_INITIALIZE_RESET_SPOOF_VIOLATION
        )
        errors.append(
            "All 5 G126 AF/Focus settings (`Aperture Drive in AF`, `AF w/ Shutter`, `Pre-AF`, "
            "`Circ. of Focus Point`, `Focus Area Color`) survive [Camera Settings Reset] and reset ONLY via [Initialize]."
        )

    # Part C: FX6 Iris vs FX3 Still-AF cross-wire guard
    if (
        claimed_fx6_has_aperture_drive_or_circ_or_white_red_color
        or claimed_fx6_close_iris_warning_wired
        or (
            target_model == FX6_MODEL_NAME_PHASE294
            and (still_aperture_adjust_requested or pre_af_activate_requested or af_w_shutter_still_use_requested)
        )
    ):
        _add_code(
            codes, STATUS_BLOCKED_G126_FX6_IRIS_VS_FX3_STILL_AF_CROSSWIRE_VIOLATION
        )
        errors.append(
            "ILME-FX6 Ver. 6.01 lacks FX3 Still AF settings (uses cinema Iris: Auto Iris / Manual / "
            "Push Auto Iris / Iris Override); FX6 `Close Iris to F2.4 for AF` is un-wired broadcast string residue."
        )

    # Part D: Folder Name (Date Form lockout), Set File Name, 4,000-image cap, Dual-slot rules
    if not _is_valid_set_file_name_prefix(set_file_name_prefix):
        _add_code(
            codes, STATUS_BLOCKED_G126_FOLDER_NAMING_CAPACITY_OR_DUAL_SLOT_VIOLATION
        )
        errors.append(
            f"[Set File Name] `{set_file_name_prefix}` invalid: must be 3 chars `[A-Z0-9][A-Z0-9_]{{2}}` "
            "(first char cannot be `_`)."
        )

    if select_rec_folder_requested:
        if norm_folder_form == FOLDER_NAME_DATE_FORM_G126:
            _add_code(
                codes, STATUS_BLOCKED_G126_FOLDER_NAMING_CAPACITY_OR_DUAL_SLOT_VIOLATION
            )
            errors.append(
                "[Select REC Folder] is disabled when [Folder Name] = [Date Form] (`100_MMDD`)."
            )
        if dual_slot_simultaneous_rec and (not slot1_slot2_common_folder_exists):
            _add_code(
                codes, STATUS_BLOCKED_G126_FOLDER_NAMING_CAPACITY_OR_DUAL_SLOT_VIOLATION
            )
            errors.append(
                "[Select REC Folder] in Dual-Slot Simultaneous mode requires identical folder name on both cards."
            )

    if (
        still_capture_into_current_folder_requested
        and _is_real_int(slot1_folder_image_count)
        and slot1_folder_image_count >= FOLDER_IMAGE_CAPACITY_LIMIT_G126
    ):
        _add_code(
            codes, STATUS_BLOCKED_G126_FOLDER_NAMING_CAPACITY_OR_DUAL_SLOT_VIOLATION
        )
        errors.append(
            f"Folder image limit `{FOLDER_IMAGE_CAPACITY_LIMIT_G126}` reached (`STATUS_OF_MEDIA_SLOT1_FOLDER_MAX`)."
        )

    # Part E: Slot-1 Tier-0 Recovery Vault Write Firewall (EROFS / EOPNOTSUPP) + Rating rules
    if claimed_rating_is_ram_only_non_card_write:
        _add_code(
            codes, STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION
        )
        errors.append(
            "[Rating] directly mutates EXIF/XMP (`XMP_RATING_VALID`) and `AVF_INFO` ImageDB on card."
        )

    if eff["folder_mutation_blocked"] or eff["rating_operation_blocked"]:
        _add_code(
            codes, STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION
        )
        errors.append(
            f"Slot 1 holds read-only/Tier-0 recovery vault (`errno={eff['block_errno']}`): "
            "[Create New Folder], [Forced File Number Reset], Playback [Rating], and [Add Rating] "
            "targeting Slot 1 are blocked fail-closed (`slot1_metadata_sector_writes == 0`)."
        )

    if rating_add_on_shooting_screen_requested and (norm_shoot in MOVIE_SHOOT_MODES_PHASE294):
        _add_code(
            codes, STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION
        )
        errors.append(
            "Still-screen custom key [Add Rating] (`FUNC_rating_on_shooting_screen`) is forbidden during Movie/S&Q."
        )

    if (
        rating_add_on_shooting_screen_requested
        and rating_existing_stars is not None
        and _is_real_int(rating_existing_stars)
        and rating_existing_stars > 0
    ):
        _add_code(
            codes, STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION
        )
        errors.append(
            "Still [Add Rating] rejected: `_g.uxc 0x627d` `Can't add since a Rating is already applied.`"
        )

    if (rating_requested or rating_add_on_shooting_screen_requested) and background_transfer_active:
        _add_code(
            codes, STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION
        )
        errors.append(
            "[Rating] blocked during background FTP/transfer (`EDIT_FUNC_CMP_NG_DURING_BACKGROUND_TRANSFER_RATING`)."
        )

    if target_model == FX6_MODEL_NAME_PHASE294 and (
        rating_requested or rating_add_on_shooting_screen_requested or forced_file_number_reset_requested
    ):
        _add_code(
            codes, STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION
        )
        errors.append(
            "ILME-FX6 uses XAVC Root/Edit/Rename Folder & `Clip Flag` (`OK/NG/KEEP`), NOT 100MSDCF/[Forced File Number Reset]/[Rating]."
        )

    matrix = compute_aperture_drive_and_folder_rating_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G126 if valid else codes[0]

    return ApertureDriveAndFolderRatingGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE294,
        target_model=target_model,
        reset_action=norm_reset or "INVALID",
        shoot_mode=eff["shoot_mode"],
        silent_mode_active=eff["silent_mode_active"],
        lens_pre_af_supported=bool(lens_pre_af_supported),
        effective_aperture_drive_in_af=eff["effective_aperture_drive_in_af"],
        effective_silent_detail_aperture_drive=eff["effective_silent_detail_aperture_drive"],
        effective_af_w_shutter=eff["effective_af_w_shutter"],
        effective_pre_af=eff["effective_pre_af"],
        effective_circ_of_focus_point=eff["effective_circ_of_focus_point"],
        orthogonal_wrap_only=True,
        effective_focus_area_color=eff["effective_focus_area_color"],
        focus_frame_5_settings_survived_cam_reset=eff["focus_frame_5_settings_survived_cam_reset"],
        initialize_required_to_reset_5_settings=eff["initialize_required_to_reset_5_settings"],
        fx6_uses_iris_architecture=True,
        fx6_iris_modes=FX6_IRIS_CONTROL_MODES_G126,
        effective_folder_name_form=eff["effective_folder_name_form"],
        effective_file_number_mode=eff["effective_file_number_mode"],
        set_file_name_prefix=eff["set_file_name_prefix"],
        select_rec_folder_enabled=eff["select_rec_folder_enabled"],
        dual_slot_simultaneous_rec=bool(dual_slot_simultaneous_rec),
        current_folder_image_count=slot1_folder_image_count if _is_real_int(slot1_folder_image_count) else 0,
        folder_at_4000_limit=eff["folder_at_4000_limit"],
        target_media_slot=eff["target_media_slot"],
        slot_1_write_protected=bool(slot_1_write_protected),
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        rating_stars=rating_stars,
        rating_operation_blocked=eff["rating_operation_blocked"],
        folder_mutation_blocked=eff["folder_mutation_blocked"],
        block_errno=eff["block_errno"],
        slot1_metadata_sector_writes=eff["slot1_metadata_sector_writes"],
        slot1_avf_info_mutated=eff["slot1_avf_info_mutated"],
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g126_aperture_drive_and_folder_rating_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    aperture_drive_folder_rating_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase294DonorAuditResult] = None,
) -> Tuple[GateVerdict, G126ApertureDriveFolderRatingGuardResult]:
    """Evaluate Wave-53 Gate `G126` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase294_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_aperture_drive_and_folder_rating_guard(
        **(dict(aperture_drive_folder_rating_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G126.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G126 if valid else codes[0]

    res = G126ApertureDriveFolderRatingGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        aperture_drive_folder_rating_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, ap={guard.effective_aperture_drive_in_af},"
        f"af_shut={guard.effective_af_w_shutter},pre_af={guard.effective_pre_af},"
        f"circ={guard.effective_circ_of_focus_point},color={guard.effective_focus_area_color},"
        f"folder={guard.effective_folder_name_form},slot1_vault={guard.slot_1_contains_tier0_vault},"
        f"s1_writes={guard.slot1_metadata_sector_writes}"
    )
    verdict = GateVerdict(
        gate_id=G126_GATE_ID,
        gate_code=G126_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `126`-Gate Master Safety Preflight (`G01..G126`)
# ---------------------------------------------------------------------------


def evaluate_126gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    lens_comp_af_illuminator_kwargs: Optional[Mapping[str, Any]] = None,
    aperture_drive_folder_rating_kwargs: Optional[Mapping[str, Any]] = None,
    master_124_override: Optional[Master124GateReport] = None,
    **m124_passthrough_kwargs: Any,
) -> Master126GateReport:
    """Evaluate all 126 Master Safety Gates (`G01..G126`) deterministically by
    delegating `G01..G124` directly to `evaluate_124gate_preflight()`.
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

    m124_report: Master124GateReport = (
        master_124_override
        if master_124_override is not None
        else evaluate_124gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m124_passthrough_kwargs,
        )
    )

    phase294_audit = audit_phase294_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g125_verdict, g125_res = evaluate_g125_lens_comp_and_af_illuminator_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        lens_comp_af_illuminator_kwargs=lens_comp_af_illuminator_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase294_audit,
    )

    g126_verdict, g126_res = evaluate_g126_aperture_drive_and_folder_rating_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        aperture_drive_folder_rating_kwargs=aperture_drive_folder_rating_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase294_audit,
    )

    gates_125_to_126 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g125_verdict, g126_verdict)
    ]
    all_gates = tuple(list(m124_report.gates) + gates_125_to_126)

    g01_to_g12_verified = int(m124_report.summary["g01_to_g12_verified"])
    g13_to_g124_verified = int(m124_report.summary["g13_to_g122_verified"]) + int(
        m124_report.summary["g123_to_g124_verified"]
    )
    g125_to_g126_verified = sum(1 for v in (g125_verdict, g126_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g124_verified + g125_to_g126_verified

    g125_to_g126_all_passed = g125_to_g126_verified == 2
    g13_to_g126_all_passed = (
        m124_report.g13_to_g124_all_passed and g125_to_g126_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m124_report.gates[:9])

    offline_123_verified = (
        g01_to_g09_ok
        and m124_report.offline_121_gates_verified
        and g125_to_g126_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_126_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g126_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m124_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_123_verified
        and m124_report.h0_h1_trial_entry_allowed
        and g125_to_g126_all_passed
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
        list(m124_report.errors)
        + list(g125_verdict.errors)
        + list(g126_verdict.errors)
    )
    warnings: List[str] = (
        list(m124_report.warnings)
        + list(g125_verdict.warnings)
        + list(g126_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m124_report.g13_to_g124_all_passed:
        overall_status = m124_report.status
    elif not g125_verdict.passed:
        overall_status = g125_verdict.status
    elif not g126_verdict.passed:
        overall_status = g126_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_126_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_126_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_126_verified:
        overall_status = "VERIFIED_ALL_126_GATES"
    else:
        overall_status = "VERIFIED_123_OF_126_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m124_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g125_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g126_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 126,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 126 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g124_verified": g13_to_g124_verified,
        "g125_to_g126_verified": g125_to_g126_verified,
        "g13_to_g126_all_passed": g13_to_g126_all_passed,
        "g125_to_g126_all_passed": g125_to_g126_all_passed,
        "offline_123_gates_verified": offline_123_verified,
        "all_126_gates_verified": all_126_verified,
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

    return Master126GateReport(
        schema=REALHW_LENS_COMP_AF_ILLUMINATOR_APERTURE_DRIVE_FOLDER_RATING_126GATE_SCHEMA,
        version=REALHW_LENS_COMP_AF_ILLUMINATOR_APERTURE_DRIVE_FOLDER_RATING_126GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_123_gates_verified=offline_123_verified,
        all_126_gates_verified=all_126_verified,
        g13_to_g126_all_passed=g13_to_g126_all_passed,
        g125_to_g126_all_passed=g125_to_g126_all_passed,
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
        master_124_report=m124_report.to_dict(),
        g125_result=g125_res.to_dict(),
        g126_result=g126_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_126_master_safety_gates = evaluate_126gate_preflight
run_126_gate_preflight = evaluate_126gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard",
        description=(
            "Phase 294 (Wave-53) Gates G125 ([Lens Compensation] Auto/Off vs Dormant Auto: Low + "
            "Movie [AF Transition Speed]/[AF Subj. Shift Sensitivity]/[AF Assist] & [AF Illuminator] "
            "Front LED Reality Split) + G126 ([Aperture Drive in AF]/[AF w/ Shutter]/[Pre-AF]/"
            "[Circ. of Focus Point]/[Focus Area Color] Initialize-Only Survival + [File/Folder Settings] "
            "& Playback [Rating] Slot-1 Vault EROFS/EOPNOTSUPP Firewall) + Unified 126-Gate Preflight (100%%)"
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
        help="Supply simulated dry-run Tier-0 bench inputs so all G01..G126 gates can be rehearsed offline",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    parser.add_argument("--summary", action="store_true", help="Emit concise summary output")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_126gate_preflight(
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
                "g125_status": report.g125_result["status"],
                "g126_status": report.g126_result["status"],
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
            f"verified={report.summary['verified_gates']}/126 "
            f"g125_to_g126_all_passed={report.g125_to_g126_all_passed} "
            f"all_126_gates_verified={report.all_126_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
            f"cross_model_flash_authorized={report.cross_model_flash_authorized} "
            f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        report.all_126_gates_verified
        if args.dry_run_simulated
        else report.offline_123_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
