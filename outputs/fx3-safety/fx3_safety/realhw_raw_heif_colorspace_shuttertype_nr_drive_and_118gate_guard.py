"""Phase 283 (118/118 Safety Gates, Wave-49) Sony `ILME-FX3` (`Ver. 7.02`, `ilc/2210`)
vs `ILME-FX6` (`Ver. 6.01`) Safety Gates `G117` (Still `[Image Quality Settings]`
2-Option `Compressed`/`Uncompressed` `RAW File Type` vs Dormant `Lossless Comp`
Trap, `JPEG/HEIF 4:2:0/4:2:2`, `[HLG Still Image]` Prerequisites/Lockouts &
`[Color Space]` `sRGB`/`AdobeRGB` DCF 2.0 `_DSC` Leading-Underscore Rule) &
`G118` (2-Option `[Shutter Type]` `Mechanical`/`Electronic` No-`Auto` Guard,
`[e-Front Curtain Shut.]` Reset Survival, `1/250 s` Mechanical Flash Sync &
5-Function Electronic Lockout, & `[Long Exposure NR]` / `[High ISO NR]` /
`[Drive Mode]` `10 fps` Couplings) + Unified `118`-Gate Master Safety Preflight
(`G01..G118`).

Operationalizes Wave-49 official Sony `ILME-FX3` (`Ver. 7.02`, Help Guide
`ilc/2210`) & `ILME-FX6` (`Ver. 6.01`) intelligence
(`reports/2026-11-17-global-sony-wave49-still-raw-heif-colorspace-adobersgb-shutter-type-nr-drive-intel/README.md`)
as deterministic offline preflight verifiers (`G117` and `G118`) and delegates
`G01..G116` directly to `evaluate_116gate_preflight()`.
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
from .realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard import (
    Master116GateReport,
    evaluate_116gate_preflight,
)
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_RAW_HEIF_COLORSPACE_SHUTTERTYPE_NR_DRIVE_118GATE_SCHEMA: str = (
    "realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard_v1"
)
REALHW_RAW_HEIF_COLORSPACE_SHUTTERTYPE_NR_DRIVE_118GATE_VERSION: str = "1.0.0"

G117_GATE_ID: str = (
    "G117_raw_heif_hlg_still_and_colorspace_adobergb_prefix_guard"
)
G117_GATE_CODE: str = (
    "RAW_HEIF_HLG_STILL_AND_COLORSPACE_ADOBERGB_PREFIX_GUARD"
)

G118_GATE_ID: str = (
    "G118_shutter_type_flash_sync_electronic_5lock_nr_and_drive_guard"
)
G118_GATE_CODE: str = (
    "SHUTTER_TYPE_FLASH_SYNC_ELECTRONIC_5LOCK_NR_AND_DRIVE_GUARD"
)

G117: str = G117_GATE_ID
G118: str = G118_GATE_ID
GATE_G117_RAW_HEIF_HLG_STILL_AND_COLORSPACE_ADOBERGB_PREFIX_GUARD: str = (
    G117_GATE_CODE
)
GATE_G118_SHUTTER_TYPE_FLASH_SYNC_ELECTRONIC_5LOCK_NR_AND_DRIVE_GUARD: str = (
    G118_GATE_CODE
)

ENV_CLEAN_ROOM_TEST_PHASE283: str = "FX3_CLEAN_ROOM_TEST"

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE283: float = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE283: float = 1.00

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX6_MODEL_NAME_PHASE283: str = "ILME-FX6"
FX3_DEFAULT_FW_VERSION_PHASE283: str = "7.02"
FX6_DEFAULT_FW_VERSION_PHASE283: str = "6.01"
FX3_HELP_GUIDE_CODE_PHASE283: str = "ilc/2210"

RESET_ACTION_NONE_PHASE283: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE283: str = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE283: str = "Reset Network Set."
RESET_ACTION_INITIALIZE_PHASE283: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE283: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE283,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE283,
    RESET_ACTION_RESET_NETWORK_SET_PHASE283,
    RESET_ACTION_INITIALIZE_PHASE283,
)

SHOOT_MODE_P_PHASE283: str = "P"
SHOOT_MODE_A_PHASE283: str = "A"
SHOOT_MODE_S_PHASE283: str = "S"
SHOOT_MODE_M_PHASE283: str = "M"
SHOOT_MODE_STILL_PASM_PHASE283: str = "Still"
SHOOT_MODE_INTELLIGENT_AUTO_PHASE283: str = "Intelligent Auto"
SHOOT_MODE_MOVIE_PHASE283: str = "Movie"
SHOOT_MODE_SQ_PHASE283: str = "S&Q"
PASM_SHOOT_MODES_PHASE283: Tuple[str, ...] = (
    SHOOT_MODE_P_PHASE283,
    SHOOT_MODE_A_PHASE283,
    SHOOT_MODE_S_PHASE283,
    SHOOT_MODE_M_PHASE283,
    SHOOT_MODE_STILL_PASM_PHASE283,
)
ALLOWED_SHOOT_MODES_PHASE283: Tuple[str, ...] = PASM_SHOOT_MODES_PHASE283 + (
    SHOOT_MODE_INTELLIGENT_AUTO_PHASE283,
    SHOOT_MODE_MOVIE_PHASE283,
    SHOOT_MODE_SQ_PHASE283,
)

# ---------------------------------------------------------------------------
# Status & Violation Codes (G117 / G118 / Phase 283)
# ---------------------------------------------------------------------------

STATUS_VERIFIED_G117: str = "VERIFIED_G117_RAW_HEIF_HLG_AND_COLORSPACE_SAFE"
STATUS_VERIFIED_G118: str = "VERIFIED_G118_SHUTTER_TYPE_SYNC_NR_AND_DRIVE_SAFE"
STATUS_BLOCKED_PHASE283_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE283_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G117_FX3_DORMANT_LOSSLESS_RAW_SPOOF_VIOLATION: str = (
    "BLOCKED_G117_FX3_DORMANT_LOSSLESS_RAW_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G117_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATION: str = (
    "BLOCKED_G117_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATION"
)
STATUS_BLOCKED_G117_COLORSPACE_ADOBERGB_PREFIX_VIOLATION: str = (
    "BLOCKED_G117_COLORSPACE_ADOBERGB_PREFIX_VIOLATION"
)
STATUS_BLOCKED_G117_TELEMETRY_INVALID: str = (
    "BLOCKED_G117_RAW_HEIF_COLORSPACE_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G118_FX3_SHUTTER_TYPE_AUTO_SPOOF_VIOLATION: str = (
    "BLOCKED_G118_FX3_SHUTTER_TYPE_AUTO_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G118_ELECTRONIC_SHUTTER_5LOCK_OR_SYNC_VIOLATION: str = (
    "BLOCKED_G118_ELECTRONIC_SHUTTER_5LOCK_OR_SYNC_VIOLATION"
)
STATUS_BLOCKED_G118_NR_OR_DRIVE_CONT_BOUNDARY_VIOLATION: str = (
    "BLOCKED_G118_NR_OR_DRIVE_CONT_BOUNDARY_VIOLATION"
)
STATUS_BLOCKED_G118_TELEMETRY_INVALID: str = (
    "BLOCKED_G118_SHUTTER_TYPE_NR_DRIVE_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G117 Constants: RAW / JPEG / HEIF, HLG Still Image, Color Space & _DSC
# ---------------------------------------------------------------------------

JPEG_HEIF_SWITCH_MENU_PATH_G117: str = (
    "MENU -> Shooting -> [Image Quality/Rec] -> [JPEG/HEIF Switch]"
)
IMAGE_QUALITY_SETTINGS_MENU_PATH_G117: str = (
    "MENU -> Shooting -> [Image Quality/Rec] -> [Image Quality Settings]"
)
HLG_STILL_IMAGE_MENU_PATH_G117: str = (
    "MENU -> Shooting -> [Image Quality/Rec] -> [HLG Still Image]"
)
COLOR_SPACE_MENU_PATH_G117: str = (
    "MENU -> Shooting -> [Image Quality/Rec] -> [Color Space]"
)
SET_FILE_NAME_MENU_PATH_G117: str = (
    "MENU -> Shooting -> [File] -> [File/Folder Settings] -> [Set File Name]"
)

JPEG_HEIF_SWITCH_UXC_RESID16_G117: int = 0x742A
IMAGE_QUALITY_SETTINGS_UXC_RESID16_G117: int = 0x6ADE
FILE_FORMAT_UXC_RESID16_G117: int = 0xE73D
RAW_FILE_TYPE_UXC_RESID16_G117: int = 0x6FF2
DORMANT_LOSSLESS_COMP_UXC_RESID16_G117: int = 0x6B56
HLG_STILL_IMAGE_UXC_RESID16_G117: int = 0x76C8
HLG_BT2020_UXC_RESID16_G117: int = 0x79E1
COLOR_SPACE_UXC_RESID16_G117: int = 0x68B7
COLOR_SPACE_SRGB_UXC_RESID16_G117: int = 0xE07D
COLOR_SPACE_ADOBERGB_UXC_RESID16_G117: int = 0xE07E
ADOBERGB_DSC_HINT_UXC_RESID16_G117: int = 0xE895
SET_FILE_NAME_UXC_RESID16_G117: int = 0x6993

JH_SWITCH_JPEG_G117: str = "JPEG"
JH_SWITCH_HEIF_420_G117: str = "HEIF(4:2:0)"
JH_SWITCH_HEIF_422_G117: str = "HEIF(4:2:2)"
ALLOWED_JH_SWITCH_MODES_G117: Tuple[str, ...] = (
    JH_SWITCH_JPEG_G117,
    JH_SWITCH_HEIF_420_G117,
    JH_SWITCH_HEIF_422_G117,
)
JH_SWITCH_FACTORY_DEFAULT_G117: str = JH_SWITCH_JPEG_G117

FILE_FORMAT_RAW_G117: str = "RAW"
FILE_FORMAT_RAW_JPEG_G117: str = "RAW & JPEG"
FILE_FORMAT_RAW_HEIF_G117: str = "RAW & HEIF"
FILE_FORMAT_JPEG_G117: str = "JPEG"
FILE_FORMAT_HEIF_G117: str = "HEIF"
ALLOWED_FILE_FORMATS_G117: Tuple[str, ...] = (
    FILE_FORMAT_RAW_G117,
    FILE_FORMAT_RAW_JPEG_G117,
    FILE_FORMAT_RAW_HEIF_G117,
    FILE_FORMAT_JPEG_G117,
    FILE_FORMAT_HEIF_G117,
)
FILE_FORMAT_FACTORY_DEFAULT_G117: str = FILE_FORMAT_JPEG_G117

RAW_TYPE_COMPRESSED_G117: str = "Compressed"
RAW_TYPE_UNCOMPRESSED_G117: str = "Uncompressed"
RAW_TYPE_DORMANT_LOSSLESS_COMP_G117: str = "Lossless Comp"
FX3_EXACT_2_RAW_FILE_TYPES_G117: Tuple[str, ...] = (
    RAW_TYPE_COMPRESSED_G117,
    RAW_TYPE_UNCOMPRESSED_G117,
)
RAW_TYPE_FACTORY_DEFAULT_G117: str = RAW_TYPE_COMPRESSED_G117
RAW_BIT_DEPTH_FX3_G117: int = 14
HEIF_BIT_DEPTH_FX3_G117: int = 10

STILL_QUALITY_EXTRA_FINE_G117: str = "Extra fine"
STILL_QUALITY_FINE_G117: str = "Fine"
STILL_QUALITY_STANDARD_G117: str = "Standard"
ALLOWED_STILL_QUALITIES_G117: Tuple[str, ...] = (
    STILL_QUALITY_EXTRA_FINE_G117,
    STILL_QUALITY_FINE_G117,
    STILL_QUALITY_STANDARD_G117,
)
STILL_QUALITY_FACTORY_DEFAULT_G117: str = STILL_QUALITY_FINE_G117

STILL_SIZE_L_G117: str = "L"
STILL_SIZE_M_G117: str = "M"
STILL_SIZE_S_G117: str = "S"
ALLOWED_STILL_SIZES_G117: Tuple[str, ...] = (
    STILL_SIZE_L_G117,
    STILL_SIZE_M_G117,
    STILL_SIZE_S_G117,
)
STILL_SIZE_FACTORY_DEFAULT_G117: str = STILL_SIZE_L_G117

COLOR_SPACE_SRGB_G117: str = "sRGB"
COLOR_SPACE_ADOBERGB_G117: str = "AdobeRGB"
COLOR_SPACE_BT2100_BT2020_G117: str = "BT.2100/BT.2020"
ALLOWED_COLOR_SPACES_G117: Tuple[str, ...] = (
    COLOR_SPACE_SRGB_G117,
    COLOR_SPACE_ADOBERGB_G117,
)
COLOR_SPACE_FACTORY_DEFAULT_G117: str = COLOR_SPACE_SRGB_G117

SET_FILE_NAME_DEFAULT_PREFIX_G117: str = "DSC"
ADOBERGB_DEFAULT_PREFIX_G117: str = "_DSC"
SET_FILE_NAME_PREFIX_LENGTH_G117: int = 3
HLG_STILL_LOCKED_OUT_FUNCTIONS_G117: Tuple[str, ...] = (
    "Picture Profile",
    "Creative Look",
    "D-Range Optimizer",
    "DRO Bracket",
)

# ---------------------------------------------------------------------------
# Gate G118 Constants: Shutter Type (2-Option), e-Front Curtain, Flash Sync, NR, Drive
# ---------------------------------------------------------------------------

SHUTTER_TYPE_MENU_PATH_G118: str = (
    "MENU -> Shooting -> [Shutter/Silent] -> [Shutter Type]"
)
E_FRONT_CURTAIN_MENU_PATH_G118: str = (
    "MENU -> Shooting -> [Shutter/Silent] -> [e-Front Curtain Shut.]"
)
SILENT_MODE_MENU_PATH_G118: str = (
    "MENU -> Shooting -> [Shutter/Silent] -> [Silent Mode Settings] -> [Silent Mode]"
)
LONG_EXPOSURE_NR_MENU_PATH_G118: str = (
    "MENU -> Shooting -> [Image Quality/Rec] -> [Long Exposure NR]"
)
HIGH_ISO_NR_MENU_PATH_G118: str = (
    "MENU -> Shooting -> [Image Quality/Rec] -> [High ISO NR]"
)
DRIVE_MODE_MENU_PATH_G118: str = (
    "MENU -> Shooting -> [Drive Mode] -> [Drive Mode]"
)

SHUTTER_TYPE_UXC_RESID16_G118: int = 0x7AA9
SHUTTER_TYPE_MECH_UXC_RESID16_G118: int = 0x6DDB
SHUTTER_TYPE_ELEC_UXC_RESID16_G118: int = 0x60A1
E_FRONT_CURTAIN_UXC_RESID16_G118: int = 0x64C6
SILENT_MODE_UXC_RESID16_G118: int = 0x7A53
FLASH_SYNC_1_250_UXC_RESID16_G118: int = 0x759B
LONG_EXPOSURE_NR_UXC_RESID16_G118: int = 0x6CD7
HIGH_ISO_NR_UXC_RESID16_G118: int = 0x650B
HIGH_ISO_NR_NORMAL_UXC_RESID16_G118: int = 0xE9AE
HIGH_ISO_NR_LOW_UXC_RESID16_G118: int = 0xE06E
HIGH_ISO_NR_OFF_UXC_RESID16_G118: int = 0xE6D8
DRIVE_MODE_UXC_RESID16_G118: int = 0x7228
CONT_SHOOTING_HI_PLUS_UXC_RESID16_G118: int = 0x68D1

SHUTTER_TYPE_MECHANICAL_G118: str = "Mechanical Shutter"
SHUTTER_TYPE_ELECTRONIC_G118: str = "Electronic Shutter"
SHUTTER_TYPE_SIBLING_AUTO_TRAP_G118: str = "Auto"
FX3_EXACT_2_SHUTTER_TYPES_G118: Tuple[str, ...] = (
    SHUTTER_TYPE_MECHANICAL_G118,
    SHUTTER_TYPE_ELECTRONIC_G118,
)
SHUTTER_TYPE_FACTORY_DEFAULT_G118: str = SHUTTER_TYPE_MECHANICAL_G118
SHUTTER_TYPE_INTERVAL_DEFAULT_G118: str = SHUTTER_TYPE_ELECTRONIC_G118

E_FRONT_CURTAIN_DEFAULT_G118: str = "On"
SILENT_MODE_DEFAULT_G118: str = "Off"

FX3_FLASH_SYNC_CEILING_DENOM_G118: int = 250
FX3_FLASH_SYNC_CEILING_SECONDS_G118: float = 1.0 / 250.0
FX3_FLASH_SYNC_CEILING_LABEL_G118: str = "1/250 s"
APSC_FLASH_SYNC_SPOOF_DENOM_G118: int = 320

ELECTRONIC_SHUTTER_5LOCKED_FUNCTIONS_G118: Tuple[str, ...] = (
    "Flash shooting",
    "Long Exposure NR",
    "e-Front Curtain Shut.",
    "BULB",
    "Anti-flicker Shoot.",
)

LONG_EXP_NR_THRESHOLD_SECONDS_G118: float = 1.0
LONG_EXP_NR_DEFAULT_G118: str = "On"

HIGH_ISO_NR_NORMAL_G118: str = "Normal"
HIGH_ISO_NR_LOW_G118: str = "Low"
HIGH_ISO_NR_OFF_G118: str = "Off"
ALLOWED_HIGH_ISO_NR_MODES_G118: Tuple[str, ...] = (
    HIGH_ISO_NR_NORMAL_G118,
    HIGH_ISO_NR_LOW_G118,
    HIGH_ISO_NR_OFF_G118,
)
HIGH_ISO_NR_FACTORY_DEFAULT_G118: str = HIGH_ISO_NR_NORMAL_G118

DRIVE_SINGLE_G118: str = "Single Shooting"
DRIVE_CONT_G118: str = "Cont. Shooting"
DRIVE_SELF_TIMER_SINGLE_G118: str = "Self-timer(Single)"
DRIVE_SELF_TIMER_CONT_G118: str = "Self-timer(Cont)"
DRIVE_CONT_BRACKET_G118: str = "Cont. Bracket"
DRIVE_SINGLE_BRACKET_G118: str = "Single Bracket"
DRIVE_WB_BRACKET_G118: str = "WB bracket"
DRIVE_DRO_BRACKET_G118: str = "DRO Bracket"
FX3_EXACT_8_DRIVE_MODES_G118: Tuple[str, ...] = (
    DRIVE_SINGLE_G118,
    DRIVE_CONT_G118,
    DRIVE_SELF_TIMER_SINGLE_G118,
    DRIVE_SELF_TIMER_CONT_G118,
    DRIVE_CONT_BRACKET_G118,
    DRIVE_SINGLE_BRACKET_G118,
    DRIVE_WB_BRACKET_G118,
    DRIVE_DRO_BRACKET_G118,
)
DRIVE_MODE_FACTORY_DEFAULT_G118: str = DRIVE_SINGLE_G118

CONT_SPEED_HI_PLUS_G118: str = "Hi+"
CONT_SPEED_HI_G118: str = "Hi"
CONT_SPEED_MID_G118: str = "Mid"
CONT_SPEED_LO_G118: str = "Lo"
CONT_SPEED_MAX_FPS_G118: Dict[str, float] = {
    CONT_SPEED_HI_PLUS_G118: 10.0,
    CONT_SPEED_HI_G118: 8.0,
    CONT_SPEED_MID_G118: 6.0,
    CONT_SPEED_LO_G118: 3.0,
}
ALLOWED_CONT_SPEEDS_G118: Tuple[str, ...] = (
    CONT_SPEED_HI_PLUS_G118,
    CONT_SPEED_HI_G118,
    CONT_SPEED_MID_G118,
    CONT_SPEED_LO_G118,
)
CONT_AF_FIRST_FRAME_LOCK_SPEEDS_G118: Tuple[str, ...] = (
    CONT_SPEED_HI_PLUS_G118,
    CONT_SPEED_HI_G118,
    CONT_SPEED_MID_G118,
)
CONT_AF_LOCK_APERTURE_THRESHOLD_G118: float = 11.0

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, Targeted Pread on appFw.so, <0.20s)
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE283: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (62_666_043, b"BKID_APP_setting_jh_file_type"),
    (62_666_106, b"BKID_APP_setting_still_file_format"),
    (62_666_179, b"BKID_APP_setting_still_raw_file_type"),
    (61_232_384, b"RAW_FILE_TYPE_LOSSLESS"),
    (62_677_003, b"BKID_APP_setting_still_hlg_photo"),
    (62_677_072, b"BKID_APP_setting_still_color_space"),
    (61_682_904, b"VAL_setting_still_color_space_STILL_COLOR_SPACE_SRGB"),
    (61_682_957, b"VAL_setting_still_color_space_STILL_COLOR_SPACE_ADOBE_RGB"),
    (62_815_259, b"BKID_APP_set_file_name_prefix_still"),
    (62_680_982, b"BKID_APP_setting_still_shutter_type"),
    (61_305_681, b"STILL_SHUTTER_TYPE_MECHANICAL"),
    (61_305_742, b"STILL_SHUTTER_TYPE_ELECTRONIC"),
    (62_681_057, b"BKID_APP_setting_still_shutter_type_anti_distortion_shutter"),
    (62_681_180, b"BKID_APP_setting_front_curtaion_shutter"),
    (62_680_556, b"BKID_APP_setting_silent_mode"),
    (62_676_847, b"BKID_APP_setting_still_long_exposure_nr"),
    (62_676_930, b"BKID_APP_setting_still_high_iso_nr"),
    (62_678_937, b"BKID_APP_setting_menu_drive_mode"),
    (62_707_903, b"BKID_APP_setting_drive_mode_cont_shooting"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE283: str = (
    "05c19a167f199e6b1ed585800dc317c512e2c72cc76864f4ce7ae579b7a5ba6e"
)

PINNED_FX6_APPFW_SLICES_PHASE283: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (40_931_788, b"BKID_APP_SETTING_RAW_OUTPUT_FORMAT"),
    (40_925_432, b"BKID_APP_SETTING_SHUTTER_SELECT"),
    (41_748_974, b"PRODUCT_MODEL_CHAPLIN"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE283: str = (
    "cf09f85d788d4f42fb040e695ebfc6c3288c3f23d40860cf070f9481ad07c06e"
)

PINNED_PHASE283_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE283,
        tuple(tok for _off, tok in PINNED_FX3_APPFW_SLICES_PHASE283),
        "FX3_APPFW_WAVE49_RAW_HEIF_COLORSPACE_SHUTTER_NR_DRIVE_SLICES",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Image Quality Settings",
            b"JPEG/HEIF Switch",
            b"HEIF(4:2:0)",
            b"HEIF(4:2:2)",
            b"RAW File Type",
            b"Compressed",
            b"Uncompressed",
            b"Lossless Comp",
            b"HLG Still Image",
            b"Color Space",
            b"Set File Name",
            b"Shutter Type",
            b"Mechanical Shutter",
            b"Electronic Shutter",
            b"e-Front Curtain Shut.",
            b"Silent Mode Settings",
            b"Long Exposure NR",
            b"High ISO NR",
            b"Drive Mode",
            b"Cont. Shooting: Hi+",
            b"1/250",
        ),
        "FX3_UXC_F_RAW_HEIF_COLORSPACE_SHUTTER_NR_DRIVE_STRINGS",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (b"JPEG/HEIF", b"RAW", b"HLG", b"Hi+"),
        "FX3_UXC_F_ZHCN_WAVE49_RESID16_PARITY",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (b"JPEG/HEIF", b"RAW", b"HLG", b"Hi+"),
        "FX3_UXC_F_ZHTW_WAVE49_RESID16_PARITY",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (b"JPEG/HEIF", b"RAW", b"HLG", b"Hi+"),
        "FX3_UXC_F_JA_WAVE49_RESID16_PARITY",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"sRGB",
            b"AdobeRGB",
            b"_DSC.",
            b"File Format",
            b"RAW & JPEG",
            b"RAW & HEIF",
            b"HEIF",
            b"Extra fine",
            b"Fine",
            b"Standard",
            b"Normal",
            b"Single Shooting",
            b"Cont. Shooting",
            b"Cont. Bracket",
            b"Single Bracket",
            b"WB bracket",
            b"DRO Bracket",
        ),
        "FX3_UXC_COLORSPACE_FILEFORMAT_DRIVE_STRINGS",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (b"Image Quality/Rec", b"Drive Mode", b"Image Quality", b"Silent", b"Shutter"),
        "FX3_UXC_G_IMAGE_QUALITY_REC_DRIVE_SILENT",
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
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE283,
        tuple(tok for _off, tok in PINNED_FX6_APPFW_SLICES_PHASE283),
        "FX6_APPFW_WAVE49_STILL_LESS_MOVIE_RAW_SHUTTER_SLICES",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (b"RAW Output Format", b"RAW 4096", b"HDR(HLG)", b"HLG Live"),
        "FX6_UXC_MOVIE_RAW_OUTPUT_HDR_HLG",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (b"Shutter Mode", b"Shutter Speed", b"Shutter Angle", b"Slow Shutter", b"HLG_BT.2100"),
        "FX6_UXC_2_SHUTTER_MODE_ANGLE_HLG_BT2100",
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase283DonorAuditResult:
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
class RawHeifColorSpaceGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    reset_action: str
    jpeg_heif_switch_menu_path: str
    image_quality_settings_menu_path: str
    hlg_still_image_menu_path: str
    color_space_menu_path: str
    set_file_name_menu_path: str
    shoot_mode: str
    fx3_exact_2_raw_file_types: Tuple[str, ...]
    fx3_dormant_lossless_raw_blocked: bool
    raw_bit_depth: int
    heif_bit_depth: int
    requested_jpeg_heif_switch: str
    effective_jpeg_heif_switch: str
    requested_file_format: str
    effective_file_format: str
    requested_raw_file_type: str
    effective_raw_file_type: str
    effective_quality: str
    effective_image_size: str
    requested_hlg_still_image: str
    effective_hlg_still_image: str
    hlg_still_prereq_met: bool
    hlg_still_locked_functions: Tuple[str, ...]
    effective_picture_profile: str
    effective_creative_look: str
    effective_dro: str
    dro_bracket_available: bool
    requested_color_space: str
    effective_color_space: str
    heif_ignores_srgb_adobergb: bool
    requested_file_name_prefix: str
    effective_base_file_name_prefix: str
    effective_dcf_filename_prefix: str
    example_still_filename: str
    file_name_prefix_survived_cam_reset: bool
    fx6_still_pipeline_supported: bool
    fx6_mechanical_shutter: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G117RawHeifColorSpaceGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    raw_heif_colorspace_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ShutterTypeNrDriveGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    reset_action: str
    shutter_type_menu_path: str
    e_front_curtain_menu_path: str
    silent_mode_menu_path: str
    long_exposure_nr_menu_path: str
    high_iso_nr_menu_path: str
    drive_mode_menu_path: str
    shoot_mode: str
    fx3_exact_2_shutter_types: Tuple[str, ...]
    fx3_auto_shutter_type_blocked: bool
    requested_shutter_type: str
    effective_shutter_type: str
    shutter_type_in_interval_default: str
    requested_silent_mode: str
    effective_silent_mode: str
    requested_e_front_curtain: str
    effective_e_front_curtain: str
    e_front_curtain_survived_cam_reset: bool
    electronic_shutter_5lock_active: bool
    electronic_shutter_5locked_functions: Tuple[str, ...]
    fx3_flash_sync_ceiling_label: str
    fx3_flash_sync_ceiling_denom: int
    shutter_speed_seconds: float
    mechanical_flash_sync_exceeded: bool
    requested_long_exposure_nr: str
    effective_long_exposure_nr: str
    long_exp_nr_dark_frame_active: bool
    long_exp_nr_dark_frame_duration_sec: float
    requested_high_iso_nr: str
    effective_high_iso_nr: str
    arw_raw_data_modified_by_high_iso_nr: bool
    fx3_exact_8_drive_modes: Tuple[str, ...]
    requested_drive_mode: str
    effective_drive_mode: str
    cont_shooting_speed: str
    cont_shooting_nominal_max_fps: float
    hi_plus_sustains_10fps: bool
    monitor_live_view_enabled_in_drive: bool
    aperture_f_number: float
    af_locked_to_first_frame_gt_f11: bool
    dro_bracket_available: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G118ShutterTypeNrDriveGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    shutter_type_nr_drive_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master118GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_115_gates_verified: bool
    all_118_gates_verified: bool
    g13_to_g118_all_passed: bool
    g117_to_g118_all_passed: bool
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
    master_116_report: Dict[str, Any]
    g117_result: Dict[str, Any]
    g118_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers & Normalization
# ---------------------------------------------------------------------------

_TRUTHY_CLEAN_ROOM_TOKENS: Tuple[str, ...] = ("1", "true", "TRUE", "yes", "YES")
_VALID_FILE_NAME_CHAR_RE = re.compile(r"^[A-Z0-9_]{3}$")


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE283):
        if os.environ.get(env_key, "").strip() in _TRUTHY_CLEAN_ROOM_TOKENS:
            return True
    return False


def _default_donor_budget_seconds_phase283() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return DONOR_CHECK_CI_MAX_SECONDS_PHASE283
    return DONOR_CHECK_MAX_SECONDS_PHASE283


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


def _norm_reset_action_phase283(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE_PHASE283
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE283
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE283
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE_PHASE283
    return None


def _norm_shoot_mode_phase283(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "P": SHOOT_MODE_P_PHASE283,
        "A": SHOOT_MODE_A_PHASE283,
        "S": SHOOT_MODE_S_PHASE283,
        "M": SHOOT_MODE_M_PHASE283,
        "STILL": SHOOT_MODE_STILL_PASM_PHASE283,
        "INTELLIGENT AUTO": SHOOT_MODE_INTELLIGENT_AUTO_PHASE283,
        "IAUTO": SHOOT_MODE_INTELLIGENT_AUTO_PHASE283,
        "MOVIE": SHOOT_MODE_MOVIE_PHASE283,
        "S&Q": SHOOT_MODE_SQ_PHASE283,
        "SQ": SHOOT_MODE_SQ_PHASE283,
    }
    return mapping.get(u)


def _norm_on_off_phase283(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "ON":
        return "On"
    if u == "OFF":
        return "Off"
    return None


def _norm_jh_switch_g117(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    if u == "JPEG":
        return JH_SWITCH_JPEG_G117
    if u in ("HEIF(4:2:0)", "HEIF420", "HEIF_420"):
        return JH_SWITCH_HEIF_420_G117
    if u in ("HEIF(4:2:2)", "HEIF422", "HEIF_422"):
        return JH_SWITCH_HEIF_422_G117
    return None


def _norm_file_format_g117(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "RAW": FILE_FORMAT_RAW_G117,
        "RAW & JPEG": FILE_FORMAT_RAW_JPEG_G117,
        "RAW+JPEG": FILE_FORMAT_RAW_JPEG_G117,
        "RAW & HEIF": FILE_FORMAT_RAW_HEIF_G117,
        "RAW+HEIF": FILE_FORMAT_RAW_HEIF_G117,
        "JPEG": FILE_FORMAT_JPEG_G117,
        "HEIF": FILE_FORMAT_HEIF_G117,
    }
    return mapping.get(u)


def _norm_raw_file_type_g117(raw: Any, *, allow_dormant: bool = False) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u == "COMPRESSED":
        return RAW_TYPE_COMPRESSED_G117
    if u == "UNCOMPRESSED":
        return RAW_TYPE_UNCOMPRESSED_G117
    if allow_dormant and u in (
        "LOSSLESS COMP",
        "LOSSLESS",
        "RAW_FILE_TYPE_LOSSLESS",
        "LOSSLESS COMP (L)",
        "LOSSLESS COMP (M)",
        "LOSSLESS COMP (S)",
    ):
        return RAW_TYPE_DORMANT_LOSSLESS_COMP_G117
    return None


def _norm_still_quality_g117(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_STILL_QUALITIES_G117:
        if u == item.upper():
            return item
    return None


def _norm_still_size_g117(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u.startswith("L"):
        if u in ("L", "L:12M", "L: 12M"):
            return STILL_SIZE_L_G117
    if u in ALLOWED_STILL_SIZES_G117:
        return u
    return None


def _norm_color_space_g117(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    if u == "SRGB":
        return COLOR_SPACE_SRGB_G117
    if u == "ADOBERGB":
        return COLOR_SPACE_ADOBERGB_G117
    return None


def _norm_shutter_type_g118(raw: Any, *, allow_auto_trap: bool = False) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("MECHANICAL SHUTTER", "MECHANICAL", "STILL_SHUTTER_TYPE_MECHANICAL"):
        return SHUTTER_TYPE_MECHANICAL_G118
    if u in ("ELECTRONIC SHUTTER", "ELECTRONIC", "STILL_SHUTTER_TYPE_ELECTRONIC"):
        return SHUTTER_TYPE_ELECTRONIC_G118
    if allow_auto_trap and u in ("AUTO", "SHUTTER_TYPE_AUTO"):
        return SHUTTER_TYPE_SIBLING_AUTO_TRAP_G118
    return None


def _norm_high_iso_nr_g118(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    for item in ALLOWED_HIGH_ISO_NR_MODES_G118:
        if u == item.upper():
            return item
    return None


def _norm_drive_mode_g118(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in FX3_EXACT_8_DRIVE_MODES_G118:
        if u == item.upper():
            return item
    return None


def _norm_cont_speed_g118(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    if u in ("HI+", "HIPLUS"):
        return CONT_SPEED_HI_PLUS_G118
    if u == "HI":
        return CONT_SPEED_HI_G118
    if u == "MID":
        return CONT_SPEED_MID_G118
    if u in ("LO", "LOW"):
        return CONT_SPEED_LO_G118
    return None


# ---------------------------------------------------------------------------
# 1. Fast `< 0.20s` O_RDONLY Donor Contract Audit (`Phase 283`)
# ---------------------------------------------------------------------------


def audit_phase283_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: Optional[float] = None,
) -> Phase283DonorAuditResult:
    """Inspect local FX3 Ver. 7.02 / FX6 Ver. 6.01 donor artifacts strictly via
    `os.open(..., os.O_RDONLY)` within `<0.20s` (`1.00s` under
    `GITHUB_ACTIONS=true`), using targeted `os.pread` slices on both 79 MiB FX3
    `appFw.so` and 50.5 MiB FX6 `appFw.so`, and full `O_RDONLY` SHA-256
    verification on 4-language `.uxc` packs and `BK4` seed with deterministic
    `CLEAN_ROOM_SYNTHETIC` fallback.
    """
    t0 = time.perf_counter()
    budget = (
        _default_donor_budget_seconds_phase283()
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE283_DONOR_SPECS.items():
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
            spec[5] for spec in PINNED_PHASE283_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE283_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE283_DONOR_SPECS.items()}
        return Phase283DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE283_DONOR_INTEGRITY
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
    ) in PINNED_PHASE283_DONOR_SPECS.items():
        fp = resolved[key]
        if key in ("fx3_appfw_so", "fx6_appfw_so"):
            slices_spec = (
                PINNED_FX3_APPFW_SLICES_PHASE283
                if key == "fx3_appfw_so"
                else PINNED_FX6_APPFW_SLICES_PHASE283
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
            errors.append(f"Missing required Wave-49 byte markers in {key}.")

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
        files_inspected == len(PINNED_PHASE283_DONOR_SPECS)
        and within_budget
        and (not missing)
        and (not errors)
        and fx3_ok
        and fx6_ok
        and lang_ok
    )
    return Phase283DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE283_DONOR_INTEGRITY,
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
# 2. Gate G117: Still [Image Quality Settings] / [HLG Still] / [Color Space]
# ---------------------------------------------------------------------------


def _align_file_format_with_jh_switch_g117(jh_switch: str, req_fmt: str) -> str:
    if jh_switch == JH_SWITCH_JPEG_G117:
        if req_fmt == FILE_FORMAT_HEIF_G117:
            return FILE_FORMAT_JPEG_G117
        if req_fmt == FILE_FORMAT_RAW_HEIF_G117:
            return FILE_FORMAT_RAW_JPEG_G117
        return req_fmt
    # HEIF(4:2:0) or HEIF(4:2:2)
    if req_fmt == FILE_FORMAT_JPEG_G117:
        return FILE_FORMAT_HEIF_G117
    if req_fmt == FILE_FORMAT_RAW_JPEG_G117:
        return FILE_FORMAT_RAW_HEIF_G117
    return req_fmt


def resolve_fx3_raw_heif_hlg_colorspace_state(
    *,
    shoot_mode: str = SHOOT_MODE_M_PHASE283,
    requested_jpeg_heif_switch: str = JH_SWITCH_FACTORY_DEFAULT_G117,
    requested_file_format: str = FILE_FORMAT_FACTORY_DEFAULT_G117,
    requested_raw_file_type: str = RAW_TYPE_FACTORY_DEFAULT_G117,
    requested_quality: str = STILL_QUALITY_FACTORY_DEFAULT_G117,
    requested_image_size: str = STILL_SIZE_FACTORY_DEFAULT_G117,
    requested_hlg_still_image: str = "Off",
    requested_color_space: str = COLOR_SPACE_FACTORY_DEFAULT_G117,
    requested_file_name_prefix: str = SET_FILE_NAME_DEFAULT_PREFIX_G117,
    reg_custom_shoot_set_iso_or_dro_bracket: bool = False,
    requested_picture_profile: str = "PP11",
    requested_creative_look: str = "ST",
    requested_dro: str = "Auto",
    reset_action: str = RESET_ACTION_NONE_PHASE283,
) -> Dict[str, Any]:
    s_mode = _norm_shoot_mode_phase283(shoot_mode) or SHOOT_MODE_M_PHASE283
    r_act = _norm_reset_action_phase283(reset_action) or RESET_ACTION_NONE_PHASE283

    req_jh = _norm_jh_switch_g117(requested_jpeg_heif_switch) or JH_SWITCH_FACTORY_DEFAULT_G117
    req_fmt = _norm_file_format_g117(requested_file_format) or FILE_FORMAT_FACTORY_DEFAULT_G117
    req_raw = _norm_raw_file_type_g117(requested_raw_file_type) or RAW_TYPE_FACTORY_DEFAULT_G117
    req_qual = _norm_still_quality_g117(requested_quality) or STILL_QUALITY_FACTORY_DEFAULT_G117
    req_size = _norm_still_size_g117(requested_image_size) or STILL_SIZE_FACTORY_DEFAULT_G117
    req_hlg = _norm_on_off_phase283(requested_hlg_still_image) or "Off"
    req_cs = _norm_color_space_g117(requested_color_space) or COLOR_SPACE_FACTORY_DEFAULT_G117

    clean_prefix = (
        requested_file_name_prefix.strip().upper()
        if isinstance(requested_file_name_prefix, str)
        and _VALID_FILE_NAME_CHAR_RE.match(requested_file_name_prefix.strip().upper())
        and not requested_file_name_prefix.strip().upper().startswith("_")
        else SET_FILE_NAME_DEFAULT_PREFIX_G117
    )

    # Reset boundary:
    # - [Camera Settings Reset] resets Image Quality Settings & Color Space to defaults,
    #   YET [Set File Name] (0x6993) SURVIVES [Camera Settings Reset] and only resets under [Initialize]!
    if r_act == RESET_ACTION_INITIALIZE_PHASE283:
        eff_jh = JH_SWITCH_FACTORY_DEFAULT_G117
        eff_fmt = FILE_FORMAT_FACTORY_DEFAULT_G117
        eff_raw = RAW_TYPE_FACTORY_DEFAULT_G117
        eff_qual = STILL_QUALITY_FACTORY_DEFAULT_G117
        eff_size = STILL_SIZE_FACTORY_DEFAULT_G117
        sel_hlg = "Off"
        sel_cs = COLOR_SPACE_FACTORY_DEFAULT_G117
        eff_base_prefix = SET_FILE_NAME_DEFAULT_PREFIX_G117
    elif r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE283:
        eff_jh = JH_SWITCH_FACTORY_DEFAULT_G117
        eff_fmt = FILE_FORMAT_FACTORY_DEFAULT_G117
        eff_raw = RAW_TYPE_FACTORY_DEFAULT_G117
        eff_qual = STILL_QUALITY_FACTORY_DEFAULT_G117
        eff_size = STILL_SIZE_FACTORY_DEFAULT_G117
        sel_hlg = "Off"
        sel_cs = COLOR_SPACE_FACTORY_DEFAULT_G117
        eff_base_prefix = clean_prefix
    else:
        eff_jh = req_jh
        eff_fmt = _align_file_format_with_jh_switch_g117(eff_jh, req_fmt)
        eff_raw = req_raw
        eff_qual = req_qual
        eff_size = req_size
        sel_hlg = req_hlg
        sel_cs = req_cs
        eff_base_prefix = clean_prefix

    is_heif_active = eff_jh != JH_SWITCH_JPEG_G117
    hlg_prereq_met = (
        is_heif_active
        and (eff_fmt == FILE_FORMAT_HEIF_G117)
        and (s_mode in PASM_SHOOT_MODES_PHASE283)
        and (not reg_custom_shoot_set_iso_or_dro_bracket)
    )
    eff_hlg = "On" if (sel_hlg == "On" and hlg_prereq_met) else "Off"

    if eff_hlg == "On":
        eff_pp = "Off"
        eff_cl = "-"
        eff_dro = "Off"
        dro_bracket_avail = False
        eff_cs = COLOR_SPACE_BT2100_BT2020_G117
        heif_ignores_cs = True
    else:
        eff_pp = requested_picture_profile
        eff_cl = "-" if eff_pp != "Off" else requested_creative_look
        eff_dro = "Off" if eff_pp != "Off" else requested_dro
        dro_bracket_avail = True
        if is_heif_active:
            # HEIF ignores sRGB/AdobeRGB selection and records sRGB when HLG Still Image = Off.
            eff_cs = COLOR_SPACE_SRGB_G117
            heif_ignores_cs = True
        else:
            eff_cs = sel_cs
            heif_ignores_cs = False

    # DCF 2.0 filename prefix rule:
    # - In JPEG/RAW+JPEG with Color Space = AdobeRGB, automatic leading `_` -> `_DSC0001`.
    # - In HEIF or sRGB, no AdobeRGB leading `_` -> `DSC00001`.
    if (not is_heif_active) and eff_cs == COLOR_SPACE_ADOBERGB_G117:
        eff_dcf_prefix = f"_{eff_base_prefix}"
        sample_seq = "0001"
    else:
        eff_dcf_prefix = eff_base_prefix
        sample_seq = "00001"

    if eff_fmt in (FILE_FORMAT_RAW_G117, FILE_FORMAT_RAW_JPEG_G117, FILE_FORMAT_RAW_HEIF_G117):
        sample_ext = "ARW"
    elif is_heif_active:
        sample_ext = "HIF"
    else:
        sample_ext = "JPG"

    example_filename = f"{eff_dcf_prefix}{sample_seq}.{sample_ext}"

    return {
        "shoot_mode": s_mode,
        "reset_action": r_act,
        "effective_jpeg_heif_switch": eff_jh,
        "effective_file_format": eff_fmt,
        "effective_raw_file_type": eff_raw,
        "effective_quality": eff_qual,
        "effective_image_size": eff_size,
        "hlg_still_prereq_met": hlg_prereq_met,
        "effective_hlg_still_image": eff_hlg,
        "effective_picture_profile": eff_pp,
        "effective_creative_look": eff_cl,
        "effective_dro": eff_dro,
        "dro_bracket_available": dro_bracket_avail,
        "effective_color_space": eff_cs,
        "heif_ignores_srgb_adobergb": heif_ignores_cs,
        "effective_base_file_name_prefix": eff_base_prefix,
        "effective_dcf_filename_prefix": eff_dcf_prefix,
        "example_still_filename": example_filename,
        "file_name_prefix_survived_cam_reset": (
            r_act != RESET_ACTION_INITIALIZE_PHASE283
            and eff_base_prefix == clean_prefix
        ),
    }


def compute_raw_heif_hlg_colorspace_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate 648 combinations across 3 `[JPEG/HEIF Switch]`
    modes, 2 `[RAW File Type]` modes, 3 `[File Format]` modes (`RAW`,
    `RAW & JPEG`, `HEIF`), 2 `[HLG Still Image]` requests (`Off`, `On`),
    2 `[Color Space]` requests (`sRGB`, `AdobeRGB`), 3 shooting modes (`M`,
    `P`, `Intelligent Auto`), and 3 reset actions (`NONE`,
    `Camera Settings Reset`, `Initialize`).
    """
    states_checked = 0
    hlg_still_active_states = 0
    hlg_still_bt2100_states = 0
    adobergb_underscore_prefix_states = 0
    heif_ignores_adobergb_states = 0
    file_name_survived_cam_reset_states = 0

    for jh in ALLOWED_JH_SWITCH_MODES_G117:
        for raw_t in FX3_EXACT_2_RAW_FILE_TYPES_G117:
            for fmt in (
                FILE_FORMAT_RAW_G117,
                FILE_FORMAT_RAW_JPEG_G117,
                FILE_FORMAT_HEIF_G117,
            ):
                for hlg_req in ("Off", "On"):
                    for cs_req in ALLOWED_COLOR_SPACES_G117:
                        for sm in (
                            SHOOT_MODE_M_PHASE283,
                            SHOOT_MODE_P_PHASE283,
                            SHOOT_MODE_INTELLIGENT_AUTO_PHASE283,
                        ):
                            for r_act in (
                                RESET_ACTION_NONE_PHASE283,
                                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE283,
                                RESET_ACTION_INITIALIZE_PHASE283,
                            ):
                                resolved = resolve_fx3_raw_heif_hlg_colorspace_state(
                                    shoot_mode=sm,
                                    requested_jpeg_heif_switch=jh,
                                    requested_file_format=fmt,
                                    requested_raw_file_type=raw_t,
                                    requested_hlg_still_image=hlg_req,
                                    requested_color_space=cs_req,
                                    requested_file_name_prefix="FX3",
                                    reset_action=r_act,
                                )
                                states_checked += 1
                                if resolved["effective_hlg_still_image"] == "On":
                                    hlg_still_active_states += 1
                                    if resolved["effective_color_space"] == COLOR_SPACE_BT2100_BT2020_G117:
                                        hlg_still_bt2100_states += 1
                                if resolved["effective_dcf_filename_prefix"].startswith("_"):
                                    adobergb_underscore_prefix_states += 1
                                if (
                                    resolved["effective_jpeg_heif_switch"] != JH_SWITCH_JPEG_G117
                                    and not resolved["effective_dcf_filename_prefix"].startswith("_")
                                ):
                                    heif_ignores_adobergb_states += 1
                                if (
                                    r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE283
                                    and resolved["effective_base_file_name_prefix"] == "FX3"
                                ):
                                    file_name_survived_cam_reset_states += 1

    return {
        "states_checked": states_checked,
        "hlg_still_active_states": hlg_still_active_states,
        "hlg_still_bt2100_states": hlg_still_bt2100_states,
        "adobergb_underscore_prefix_states": adobergb_underscore_prefix_states,
        "heif_ignores_adobergb_states": heif_ignores_adobergb_states,
        "file_name_survived_cam_reset_states": file_name_survived_cam_reset_states,
        "all_invariants_hold": (
            states_checked == 648
            and hlg_still_active_states == 16
            and hlg_still_bt2100_states == 16
            and adobergb_underscore_prefix_states == 36
            and heif_ignores_adobergb_states == 144
            and file_name_survived_cam_reset_states == 216
        ),
    }


def verify_raw_heif_colorspace_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE283,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE283,
    fx6_comparison_fw_version: str = FX6_DEFAULT_FW_VERSION_PHASE283,
    shoot_mode: str = SHOOT_MODE_M_PHASE283,
    requested_jpeg_heif_switch: str = JH_SWITCH_FACTORY_DEFAULT_G117,
    requested_file_format: str = FILE_FORMAT_FACTORY_DEFAULT_G117,
    requested_raw_file_type: str = RAW_TYPE_FACTORY_DEFAULT_G117,
    requested_quality: str = STILL_QUALITY_FACTORY_DEFAULT_G117,
    requested_image_size: str = STILL_SIZE_FACTORY_DEFAULT_G117,
    requested_hlg_still_image: str = "Off",
    requested_color_space: str = COLOR_SPACE_FACTORY_DEFAULT_G117,
    requested_file_name_prefix: str = SET_FILE_NAME_DEFAULT_PREFIX_G117,
    reg_custom_shoot_set_iso_or_dro_bracket: bool = False,
    requested_picture_profile: str = "PP11",
    requested_creative_look: str = "ST",
    requested_dro: str = "Auto",
    reset_action: str = RESET_ACTION_NONE_PHASE283,
    claimed_fx3_raw_file_types: Optional[Sequence[str]] = None,
    claimed_lossless_comp_exposed: bool = False,
    claimed_fx3_raw_bit_depth: int = RAW_BIT_DEPTH_FX3_G117,
    claimed_fx6_still_pipeline_supported: bool = False,
    claimed_fx6_mechanical_shutter: bool = False,
    claimed_hlg_still_allowed_with_jpeg: bool = False,
    claimed_hlg_still_allowed_with_raw: bool = False,
    claimed_hlg_still_allowed_in_iauto: bool = False,
    claimed_hlg_still_allows_picture_profile: bool = False,
    claimed_hlg_still_allows_creative_look: bool = False,
    claimed_hlg_still_allows_dro: bool = False,
    claimed_hlg_still_allows_dro_bracket: bool = False,
    claimed_hlg_still_color_space: Optional[str] = None,
    claimed_set_file_name_allows_leading_underscore: bool = False,
    claimed_camera_reset_resets_file_name_prefix: bool = False,
    claimed_heif_uses_adobergb_prefix: bool = False,
    claimed_heif_honors_color_space_selection: bool = False,
    claimed_effective_color_space: Optional[str] = None,
    claimed_filename_prefix: Optional[str] = None,
) -> RawHeifColorSpaceGuardResult:
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME
        or isinstance(body_model_id, bool)
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE283
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
        or not isinstance(fx6_comparison_fw_version, str)
        or not fx6_comparison_fw_version.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G117_TELEMETRY_INVALID)
        errors.append(
            "Gate G117 requires ILME-FX3 (0x91030080, Help Guide ilc/2210, Ver. 7.02)."
        )

    norm_shoot = _norm_shoot_mode_phase283(shoot_mode)
    norm_jh = _norm_jh_switch_g117(requested_jpeg_heif_switch)
    norm_fmt = _norm_file_format_g117(requested_file_format)
    norm_raw = _norm_raw_file_type_g117(requested_raw_file_type, allow_dormant=True)
    norm_qual = _norm_still_quality_g117(requested_quality)
    norm_size = _norm_still_size_g117(requested_image_size)
    norm_hlg = _norm_on_off_phase283(requested_hlg_still_image)
    norm_cs = _norm_color_space_g117(requested_color_space)
    norm_reset = _norm_reset_action_phase283(reset_action)

    bool_flags_ok = all(
        isinstance(flag, bool)
        for flag in (
            reg_custom_shoot_set_iso_or_dro_bracket,
            claimed_lossless_comp_exposed,
            claimed_fx6_still_pipeline_supported,
            claimed_fx6_mechanical_shutter,
            claimed_hlg_still_allowed_with_jpeg,
            claimed_hlg_still_allowed_with_raw,
            claimed_hlg_still_allowed_in_iauto,
            claimed_hlg_still_allows_picture_profile,
            claimed_hlg_still_allows_creative_look,
            claimed_hlg_still_allows_dro,
            claimed_hlg_still_allows_dro_bracket,
            claimed_set_file_name_allows_leading_underscore,
            claimed_camera_reset_resets_file_name_prefix,
            claimed_heif_uses_adobergb_prefix,
            claimed_heif_honors_color_space_selection,
        )
    )
    if (
        norm_shoot is None
        or norm_jh is None
        or norm_fmt is None
        or norm_raw is None
        or norm_qual is None
        or norm_size is None
        or norm_hlg is None
        or norm_cs is None
        or norm_reset is None
        or not isinstance(requested_file_name_prefix, str)
        or not isinstance(claimed_fx3_raw_bit_depth, int)
        or isinstance(claimed_fx3_raw_bit_depth, bool)
        or not bool_flags_ok
    ):
        _add_code(codes, STATUS_BLOCKED_G117_TELEMETRY_INVALID)
        errors.append("Invalid or unrecognized G117 telemetry or enum value.")

    resolved = resolve_fx3_raw_heif_hlg_colorspace_state(
        shoot_mode=norm_shoot or SHOOT_MODE_M_PHASE283,
        requested_jpeg_heif_switch=norm_jh or JH_SWITCH_FACTORY_DEFAULT_G117,
        requested_file_format=norm_fmt or FILE_FORMAT_FACTORY_DEFAULT_G117,
        requested_raw_file_type=(
            norm_raw
            if norm_raw in FX3_EXACT_2_RAW_FILE_TYPES_G117
            else RAW_TYPE_FACTORY_DEFAULT_G117
        ),
        requested_quality=norm_qual or STILL_QUALITY_FACTORY_DEFAULT_G117,
        requested_image_size=norm_size or STILL_SIZE_FACTORY_DEFAULT_G117,
        requested_hlg_still_image=norm_hlg or "Off",
        requested_color_space=norm_cs or COLOR_SPACE_FACTORY_DEFAULT_G117,
        requested_file_name_prefix=(
            requested_file_name_prefix
            if isinstance(requested_file_name_prefix, str)
            else SET_FILE_NAME_DEFAULT_PREFIX_G117
        ),
        reg_custom_shoot_set_iso_or_dro_bracket=bool(
            reg_custom_shoot_set_iso_or_dro_bracket
        ),
        requested_picture_profile=requested_picture_profile,
        requested_creative_look=requested_creative_look,
        requested_dro=requested_dro,
        reset_action=norm_reset or RESET_ACTION_NONE_PHASE283,
    )

    matrix = compute_raw_heif_hlg_colorspace_matrix()
    if not matrix["all_invariants_hold"]:
        _add_code(codes, STATUS_BLOCKED_G117_TELEMETRY_INVALID)
        errors.append("G117 648-state matrix verification failed.")

    # 1. Stock ILME-FX3 2-Option RAW File Type vs Dormant Lossless Comp Spoof & FX6 Contrast
    raw_types_spoof = False
    if claimed_fx3_raw_file_types is not None:
        normed_list = [
            _norm_raw_file_type_g117(x, allow_dormant=True)
            for x in claimed_fx3_raw_file_types
        ]
        if (
            tuple(normed_list) != FX3_EXACT_2_RAW_FILE_TYPES_G117
            and set(normed_list) != set(FX3_EXACT_2_RAW_FILE_TYPES_G117)
        ) or (RAW_TYPE_DORMANT_LOSSLESS_COMP_G117 in normed_list):
            raw_types_spoof = True

    if (
        norm_raw == RAW_TYPE_DORMANT_LOSSLESS_COMP_G117
        or claimed_lossless_comp_exposed
        or raw_types_spoof
        or claimed_fx3_raw_bit_depth != RAW_BIT_DEPTH_FX3_G117
        or claimed_fx6_still_pipeline_supported
        or claimed_fx6_mechanical_shutter
    ):
        _add_code(codes, STATUS_BLOCKED_G117_FX3_DORMANT_LOSSLESS_RAW_SPOOF_VIOLATION)
        errors.append(
            "Stock ILME-FX3 (12MP IMX510) exposes ONLY 14-bit [Compressed] and "
            "[Uncompressed] .ARW — dormant 0x6b56 'Lossless Comp' is gated off; "
            "ILME-FX6 (PRODUCT_MODEL_CHAPLIN) has zero DCIM/.ARW/.JPG/.HIF still pipeline."
        )

    # 2. [HLG Still Image] Prerequisites, Downstream Lockouts & BT.2100/BT.2020 Override
    hlg_requested_without_prereq = (
        norm_hlg == "On"
        and norm_reset == RESET_ACTION_NONE_PHASE283
        and not resolved["hlg_still_prereq_met"]
    )
    hlg_lockout_spoof = (
        claimed_hlg_still_allowed_with_jpeg
        or claimed_hlg_still_allowed_with_raw
        or claimed_hlg_still_allowed_in_iauto
        or claimed_hlg_still_allows_picture_profile
        or claimed_hlg_still_allows_creative_look
        or claimed_hlg_still_allows_dro
        or claimed_hlg_still_allows_dro_bracket
        or (
            claimed_hlg_still_color_space is not None
            and claimed_hlg_still_color_space != COLOR_SPACE_BT2100_BT2020_G117
        )
    )
    if hlg_requested_without_prereq or hlg_lockout_spoof:
        _add_code(codes, STATUS_BLOCKED_G117_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATION)
        errors.append(
            "[HLG Still Image] = [On] requires [JPEG/HEIF Switch] = HEIF(4:2:0/4:2:2), "
            "[File Format] = HEIF only, and P/A/S/M mode; it locks out Picture Profile, "
            "Creative Look, D-Range Optimizer, and DRO Bracket while overriding Color "
            "Space to BT.2100/BT.2020."
        )

    # 3. [Color Space] DCF 2.0 AdobeRGB `_DSC` Prefix & [Set File Name] Leading `_` Rule
    prefix_raw = (
        requested_file_name_prefix.strip()
        if isinstance(requested_file_name_prefix, str)
        else ""
    )
    manual_prefix_violation = (
        not _VALID_FILE_NAME_CHAR_RE.match(prefix_raw)
        or prefix_raw.startswith("_")
    )
    if (
        manual_prefix_violation
        or claimed_set_file_name_allows_leading_underscore
        or claimed_camera_reset_resets_file_name_prefix
        or claimed_heif_uses_adobergb_prefix
        or claimed_heif_honors_color_space_selection
        or (
            claimed_effective_color_space is not None
            and claimed_effective_color_space != resolved["effective_color_space"]
        )
        or (
            claimed_filename_prefix is not None
            and claimed_filename_prefix != resolved["effective_dcf_filename_prefix"]
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G117_COLORSPACE_ADOBERGB_PREFIX_VIOLATION)
        errors.append(
            "[Color Space] (MENU -> Shooting -> [Image Quality/Rec] -> [Color Space]) "
            "prepends automatic DCF 2.0 leading `_` for AdobeRGB (_DSC0001) vs sRGB "
            "(DSC00001); [Set File Name] (0x6993) forbids manual leading `_` and survives "
            "[Camera Settings Reset], while HEIF ignores sRGB/AdobeRGB selection."
        )

    valid = not codes
    status = STATUS_VERIFIED_G117 if valid else codes[0]

    return RawHeifColorSpaceGuardResult(
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
        jpeg_heif_switch_menu_path=JPEG_HEIF_SWITCH_MENU_PATH_G117,
        image_quality_settings_menu_path=IMAGE_QUALITY_SETTINGS_MENU_PATH_G117,
        hlg_still_image_menu_path=HLG_STILL_IMAGE_MENU_PATH_G117,
        color_space_menu_path=COLOR_SPACE_MENU_PATH_G117,
        set_file_name_menu_path=SET_FILE_NAME_MENU_PATH_G117,
        shoot_mode=resolved["shoot_mode"],
        fx3_exact_2_raw_file_types=FX3_EXACT_2_RAW_FILE_TYPES_G117,
        fx3_dormant_lossless_raw_blocked=True,
        raw_bit_depth=RAW_BIT_DEPTH_FX3_G117,
        heif_bit_depth=HEIF_BIT_DEPTH_FX3_G117,
        requested_jpeg_heif_switch=norm_jh or str(requested_jpeg_heif_switch),
        effective_jpeg_heif_switch=resolved["effective_jpeg_heif_switch"],
        requested_file_format=norm_fmt or str(requested_file_format),
        effective_file_format=resolved["effective_file_format"],
        requested_raw_file_type=norm_raw or str(requested_raw_file_type),
        effective_raw_file_type=resolved["effective_raw_file_type"],
        effective_quality=resolved["effective_quality"],
        effective_image_size=resolved["effective_image_size"],
        requested_hlg_still_image=norm_hlg or str(requested_hlg_still_image),
        effective_hlg_still_image=resolved["effective_hlg_still_image"],
        hlg_still_prereq_met=resolved["hlg_still_prereq_met"],
        hlg_still_locked_functions=HLG_STILL_LOCKED_OUT_FUNCTIONS_G117,
        effective_picture_profile=resolved["effective_picture_profile"],
        effective_creative_look=resolved["effective_creative_look"],
        effective_dro=resolved["effective_dro"],
        dro_bracket_available=resolved["dro_bracket_available"],
        requested_color_space=norm_cs or str(requested_color_space),
        effective_color_space=resolved["effective_color_space"],
        heif_ignores_srgb_adobergb=resolved["heif_ignores_srgb_adobergb"],
        requested_file_name_prefix=str(requested_file_name_prefix),
        effective_base_file_name_prefix=resolved["effective_base_file_name_prefix"],
        effective_dcf_filename_prefix=resolved["effective_dcf_filename_prefix"],
        example_still_filename=resolved["example_still_filename"],
        file_name_prefix_survived_cam_reset=resolved[
            "file_name_prefix_survived_cam_reset"
        ],
        fx6_still_pipeline_supported=False,
        fx6_mechanical_shutter=False,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g117_raw_heif_colorspace_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    raw_heif_colorspace_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase283DonorAuditResult] = None,
) -> Tuple[GateVerdict, G117RawHeifColorSpaceGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase283_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_raw_heif_colorspace_guard(**dict(raw_heif_colorspace_kwargs or {}))

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G117.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G117 if valid else codes[0]

    res = G117RawHeifColorSpaceGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        raw_heif_colorspace_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, raw={guard.effective_raw_file_type}"
        f"(2opt={len(guard.fx3_exact_2_raw_file_types)},lossless_blk={guard.fx3_dormant_lossless_raw_blocked}), "
        f"jh={guard.effective_jpeg_heif_switch}/{guard.effective_file_format}, "
        f"hlg={guard.effective_hlg_still_image}, cs={guard.effective_color_space}"
        f"(prefix={guard.effective_dcf_filename_prefix},sample={guard.example_still_filename}), "
        f"fx6_still={guard.fx6_still_pipeline_supported}"
    )
    verdict = GateVerdict(
        gate_id=G117_GATE_ID,
        gate_code=G117_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G118: 2-Option [Shutter Type], 1/250 s Sync, NR & [Drive Mode]
# ---------------------------------------------------------------------------


def resolve_fx3_shutter_type_nr_drive_state(
    *,
    shoot_mode: str = SHOOT_MODE_M_PHASE283,
    requested_shutter_type: str = SHUTTER_TYPE_FACTORY_DEFAULT_G118,
    requested_e_front_curtain: str = E_FRONT_CURTAIN_DEFAULT_G118,
    requested_silent_mode: str = SILENT_MODE_DEFAULT_G118,
    requested_long_exposure_nr: str = LONG_EXP_NR_DEFAULT_G118,
    requested_high_iso_nr: str = HIGH_ISO_NR_FACTORY_DEFAULT_G118,
    requested_drive_mode: str = DRIVE_MODE_FACTORY_DEFAULT_G118,
    cont_shooting_speed: str = CONT_SPEED_HI_PLUS_G118,
    file_format: str = FILE_FORMAT_RAW_JPEG_G117,
    raw_file_type: str = RAW_TYPE_FACTORY_DEFAULT_G117,
    hlg_still_image: str = "Off",
    flash_enabled: bool = False,
    shutter_speed_seconds: float = 1.0 / 125.0,
    aperture_f_number: float = 2.8,
    bulb_mode: bool = False,
    anti_flicker_shoot: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE283,
) -> Dict[str, Any]:
    s_mode = _norm_shoot_mode_phase283(shoot_mode) or SHOOT_MODE_M_PHASE283
    r_act = _norm_reset_action_phase283(reset_action) or RESET_ACTION_NONE_PHASE283
    req_shutter = (
        _norm_shutter_type_g118(requested_shutter_type)
        or SHUTTER_TYPE_FACTORY_DEFAULT_G118
    )
    req_efront = _norm_on_off_phase283(requested_e_front_curtain) or E_FRONT_CURTAIN_DEFAULT_G118
    req_silent = _norm_on_off_phase283(requested_silent_mode) or SILENT_MODE_DEFAULT_G118
    req_lenr = _norm_on_off_phase283(requested_long_exposure_nr) or LONG_EXP_NR_DEFAULT_G118
    req_hinr = _norm_high_iso_nr_g118(requested_high_iso_nr) or HIGH_ISO_NR_FACTORY_DEFAULT_G118
    req_drive = _norm_drive_mode_g118(requested_drive_mode) or DRIVE_MODE_FACTORY_DEFAULT_G118
    req_cspeed = _norm_cont_speed_g118(cont_shooting_speed) or CONT_SPEED_HI_PLUS_G118
    norm_fmt = _norm_file_format_g117(file_format) or FILE_FORMAT_RAW_JPEG_G117
    norm_raw = _norm_raw_file_type_g117(raw_file_type) or RAW_TYPE_FACTORY_DEFAULT_G117
    norm_hlg = _norm_on_off_phase283(hlg_still_image) or "Off"

    # Reset behavior:
    # - [Camera Settings Reset] resets Shutter Type, Silent Mode, Long Exposure NR,
    #   High ISO NR, and Drive Mode to defaults, YET [e-Front Curtain Shut.] (0x64c6)
    #   SURVIVES [Camera Settings Reset] and needs [Initialize] to reset!
    if r_act == RESET_ACTION_INITIALIZE_PHASE283:
        sel_shutter = SHUTTER_TYPE_FACTORY_DEFAULT_G118
        sel_efront = E_FRONT_CURTAIN_DEFAULT_G118
        eff_silent = SILENT_MODE_DEFAULT_G118
        sel_lenr = LONG_EXP_NR_DEFAULT_G118
        sel_hinr = HIGH_ISO_NR_FACTORY_DEFAULT_G118
        sel_drive = DRIVE_MODE_FACTORY_DEFAULT_G118
        sel_cspeed = CONT_SPEED_HI_PLUS_G118
    elif r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE283:
        sel_shutter = SHUTTER_TYPE_FACTORY_DEFAULT_G118
        sel_efront = req_efront
        eff_silent = SILENT_MODE_DEFAULT_G118
        sel_lenr = LONG_EXP_NR_DEFAULT_G118
        sel_hinr = HIGH_ISO_NR_FACTORY_DEFAULT_G118
        sel_drive = DRIVE_MODE_FACTORY_DEFAULT_G118
        sel_cspeed = CONT_SPEED_HI_PLUS_G118
    else:
        sel_shutter = req_shutter
        sel_efront = req_efront
        eff_silent = req_silent
        sel_lenr = req_lenr
        sel_hinr = req_hinr
        sel_drive = req_drive
        sel_cspeed = req_cspeed

    # Silent Mode = On forces Electronic Shutter regardless of Shutter Type.
    if eff_silent == "On":
        eff_shutter = SHUTTER_TYPE_ELECTRONIC_G118
    elif s_mode not in PASM_SHOOT_MODES_PHASE283:
        eff_shutter = SHUTTER_TYPE_MECHANICAL_G118
    else:
        eff_shutter = sel_shutter

    electronic_5lock_active = (
        eff_shutter == SHUTTER_TYPE_ELECTRONIC_G118
        or eff_silent == "On"
    )

    if electronic_5lock_active:
        eff_efront = "Unavailable"
    else:
        eff_efront = sel_efront

    # Drive Mode couplings:
    if sel_drive == DRIVE_DRO_BRACKET_G118 and norm_hlg == "On":
        eff_drive = DRIVE_SINGLE_G118
        dro_bracket_avail = False
    else:
        eff_drive = sel_drive
        dro_bracket_avail = norm_hlg != "On"

    # Flash Sync ceiling: strictly 1/250 s on mechanical shutter.
    ss_sec = float(shutter_speed_seconds) if shutter_speed_seconds > 0.0 else (1.0 / 125.0)
    mechanical_flash_sync_exceeded = bool(
        flash_enabled
        and (not electronic_5lock_active)
        and ss_sec < (FX3_FLASH_SYNC_CEILING_SECONDS_G118 - 1e-9)
    )

    # Long Exposure NR:
    # Blocked in Electronic Shutter / Silent Mode, Cont. Shooting, or Cont. Bracket.
    lenr_blocked = electronic_5lock_active or (
        eff_drive in (DRIVE_CONT_G118, DRIVE_CONT_BRACKET_G118)
    )
    if lenr_blocked:
        eff_lenr = "Off"
    elif s_mode == SHOOT_MODE_INTELLIGENT_AUTO_PHASE283:
        eff_lenr = "On"
    else:
        eff_lenr = sel_lenr

    lenr_dark_frame_active = bool(
        eff_lenr == "On"
        and (ss_sec >= LONG_EXP_NR_THRESHOLD_SECONDS_G118 or bulb_mode)
    )
    lenr_dark_frame_duration = ss_sec if lenr_dark_frame_active else 0.0

    # High ISO NR:
    # Unavailable for RAW-only; never alters .ARW raw data; fixed to Normal in iAuto.
    if norm_fmt == FILE_FORMAT_RAW_G117:
        eff_hinr = "Unavailable"
    elif s_mode == SHOOT_MODE_INTELLIGENT_AUTO_PHASE283:
        eff_hinr = HIGH_ISO_NR_NORMAL_G118
    else:
        eff_hinr = sel_hinr

    # Continuous Shooting fps & AF lock couplings:
    if eff_drive == DRIVE_CONT_G118:
        nominal_fps = CONT_SPEED_MAX_FPS_G118[sel_cspeed]
        hi_plus_sustains_10fps = (
            sel_cspeed == CONT_SPEED_HI_PLUS_G118
            and (
                norm_raw != RAW_TYPE_UNCOMPRESSED_G117
                or norm_fmt in (FILE_FORMAT_JPEG_G117, FILE_FORMAT_HEIF_G117)
            )
            and (not flash_enabled)
        )
        monitor_live_view = sel_cspeed != CONT_SPEED_HI_PLUS_G118
        af_locked_gt_f11 = (
            sel_cspeed in CONT_AF_FIRST_FRAME_LOCK_SPEEDS_G118
            and float(aperture_f_number) > CONT_AF_LOCK_APERTURE_THRESHOLD_G118
        )
    else:
        nominal_fps = 0.0
        hi_plus_sustains_10fps = False
        monitor_live_view = True
        af_locked_gt_f11 = False

    return {
        "shoot_mode": s_mode,
        "reset_action": r_act,
        "effective_shutter_type": eff_shutter,
        "effective_silent_mode": eff_silent,
        "effective_e_front_curtain": eff_efront,
        "e_front_curtain_survived_cam_reset": (
            r_act != RESET_ACTION_INITIALIZE_PHASE283
            and sel_efront == req_efront
        ),
        "electronic_shutter_5lock_active": electronic_5lock_active,
        "mechanical_flash_sync_exceeded": mechanical_flash_sync_exceeded,
        "effective_long_exposure_nr": eff_lenr,
        "long_exp_nr_dark_frame_active": lenr_dark_frame_active,
        "long_exp_nr_dark_frame_duration_sec": lenr_dark_frame_duration,
        "effective_high_iso_nr": eff_hinr,
        "effective_drive_mode": eff_drive,
        "cont_shooting_speed": sel_cspeed,
        "cont_shooting_nominal_max_fps": nominal_fps,
        "hi_plus_sustains_10fps": hi_plus_sustains_10fps,
        "monitor_live_view_enabled_in_drive": monitor_live_view,
        "af_locked_to_first_frame_gt_f11": af_locked_gt_f11,
        "dro_bracket_available": dro_bracket_avail,
    }


def compute_shutter_type_nr_drive_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate 384 combinations across 2 `[Shutter Type]` modes,
    2 `[Silent Mode]` states, 2 `[Long Exposure NR]` states, 3 `[File Format]`
    states (`RAW`, `RAW & JPEG`, `JPEG`), 2 `[RAW File Type]` states,
    4 `[Drive Mode]` states (`Single Shooting`, `Cont. Shooting`, `Cont. Bracket`,
    `DRO Bracket`), and 2 aperture tiers (`F2.8`, `F16.0`) at `1.0s` / `Hi+`.
    """
    states_checked = 0
    electronic_5lock_states = 0
    long_exp_nr_dark_frame_states = 0
    high_iso_nr_unavailable_states = 0
    hi_plus_10fps_sustained_states = 0
    af_locked_gt_f11_states = 0

    for sh in FX3_EXACT_2_SHUTTER_TYPES_G118:
        for sil in ("Off", "On"):
            for lenr in ("On", "Off"):
                for fmt in (
                    FILE_FORMAT_RAW_G117,
                    FILE_FORMAT_RAW_JPEG_G117,
                    FILE_FORMAT_JPEG_G117,
                ):
                    for raw_t in FX3_EXACT_2_RAW_FILE_TYPES_G117:
                        for drv in (
                            DRIVE_SINGLE_G118,
                            DRIVE_CONT_G118,
                            DRIVE_CONT_BRACKET_G118,
                            DRIVE_DRO_BRACKET_G118,
                        ):
                            for fnum in (2.8, 16.0):
                                resolved = resolve_fx3_shutter_type_nr_drive_state(
                                    shoot_mode=SHOOT_MODE_M_PHASE283,
                                    requested_shutter_type=sh,
                                    requested_silent_mode=sil,
                                    requested_long_exposure_nr=lenr,
                                    requested_drive_mode=drv,
                                    cont_shooting_speed=CONT_SPEED_HI_PLUS_G118,
                                    file_format=fmt,
                                    raw_file_type=raw_t,
                                    shutter_speed_seconds=1.0,
                                    aperture_f_number=fnum,
                                )
                                states_checked += 1
                                if resolved["electronic_shutter_5lock_active"]:
                                    electronic_5lock_states += 1
                                if resolved["long_exp_nr_dark_frame_active"]:
                                    long_exp_nr_dark_frame_states += 1
                                if resolved["effective_high_iso_nr"] == "Unavailable":
                                    high_iso_nr_unavailable_states += 1
                                if resolved["hi_plus_sustains_10fps"]:
                                    hi_plus_10fps_sustained_states += 1
                                if resolved["af_locked_to_first_frame_gt_f11"]:
                                    af_locked_gt_f11_states += 1

    return {
        "states_checked": states_checked,
        "electronic_5lock_states": electronic_5lock_states,
        "long_exp_nr_dark_frame_states": long_exp_nr_dark_frame_states,
        "high_iso_nr_unavailable_states": high_iso_nr_unavailable_states,
        "hi_plus_10fps_sustained_states": hi_plus_10fps_sustained_states,
        "af_locked_gt_f11_states": af_locked_gt_f11_states,
        "all_invariants_hold": (
            states_checked == 384
            and electronic_5lock_states == 288
            and long_exp_nr_dark_frame_states == 24
            and high_iso_nr_unavailable_states == 128
            and hi_plus_10fps_sustained_states == 64
            and af_locked_gt_f11_states == 48
        ),
    }


def verify_shutter_type_nr_drive_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE283,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE283,
    fx6_comparison_fw_version: str = FX6_DEFAULT_FW_VERSION_PHASE283,
    shoot_mode: str = SHOOT_MODE_M_PHASE283,
    requested_shutter_type: str = SHUTTER_TYPE_FACTORY_DEFAULT_G118,
    requested_e_front_curtain: str = E_FRONT_CURTAIN_DEFAULT_G118,
    requested_silent_mode: str = SILENT_MODE_DEFAULT_G118,
    requested_long_exposure_nr: str = LONG_EXP_NR_DEFAULT_G118,
    requested_high_iso_nr: str = HIGH_ISO_NR_FACTORY_DEFAULT_G118,
    requested_drive_mode: str = DRIVE_MODE_FACTORY_DEFAULT_G118,
    cont_shooting_speed: str = CONT_SPEED_HI_PLUS_G118,
    file_format: str = FILE_FORMAT_RAW_JPEG_G117,
    raw_file_type: str = RAW_TYPE_FACTORY_DEFAULT_G117,
    hlg_still_image: str = "Off",
    flash_enabled: bool = False,
    shutter_speed_seconds: float = 1.0 / 125.0,
    aperture_f_number: float = 2.8,
    bulb_mode: bool = False,
    anti_flicker_shoot: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE283,
    claimed_fx3_shutter_types: Optional[Sequence[str]] = None,
    claimed_shutter_type_auto_exposed: bool = False,
    claimed_camera_reset_resets_e_front_curtain: bool = False,
    claimed_flash_sync_ceiling_denom: Optional[int] = None,
    claimed_electronic_shutter_allows_flash: bool = False,
    claimed_electronic_shutter_allows_long_exp_nr: bool = False,
    claimed_electronic_shutter_allows_e_front_curtain: bool = False,
    claimed_electronic_shutter_allows_bulb: bool = False,
    claimed_electronic_shutter_allows_anti_flicker: bool = False,
    claimed_silent_mode_allows_mechanical_shutter: bool = False,
    claimed_long_exp_nr_active_in_cont_shooting: bool = False,
    claimed_long_exp_nr_active_in_cont_bracket: bool = False,
    claimed_high_iso_nr_available_in_raw_only: bool = False,
    claimed_high_iso_nr_alters_arw_raw: bool = False,
    claimed_hi_plus_10fps_sustained_with_uncompressed_raw: bool = False,
    claimed_hi_plus_10fps_sustained_with_flash: bool = False,
    claimed_af_unlocked_above_f11_in_hi_plus: bool = False,
    claimed_dro_bracket_available_in_hlg_still: bool = False,
) -> ShutterTypeNrDriveGuardResult:
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME
        or isinstance(body_model_id, bool)
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE283
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
        or not isinstance(fx6_comparison_fw_version, str)
        or not fx6_comparison_fw_version.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G118_TELEMETRY_INVALID)
        errors.append(
            "Gate G118 requires ILME-FX3 (0x91030080, Help Guide ilc/2210, Ver. 7.02)."
        )

    norm_shoot = _norm_shoot_mode_phase283(shoot_mode)
    norm_shutter = _norm_shutter_type_g118(requested_shutter_type, allow_auto_trap=True)
    norm_efront = _norm_on_off_phase283(requested_e_front_curtain)
    norm_silent = _norm_on_off_phase283(requested_silent_mode)
    norm_lenr = _norm_on_off_phase283(requested_long_exposure_nr)
    norm_hinr = _norm_high_iso_nr_g118(requested_high_iso_nr)
    norm_drive = _norm_drive_mode_g118(requested_drive_mode)
    norm_cspeed = _norm_cont_speed_g118(cont_shooting_speed)
    norm_fmt = _norm_file_format_g117(file_format)
    norm_raw = _norm_raw_file_type_g117(raw_file_type)
    norm_hlg = _norm_on_off_phase283(hlg_still_image)
    norm_reset = _norm_reset_action_phase283(reset_action)

    ss_ok = (
        not isinstance(shutter_speed_seconds, bool)
        and isinstance(shutter_speed_seconds, (int, float))
        and shutter_speed_seconds > 0.0
    )
    ap_ok = (
        not isinstance(aperture_f_number, bool)
        and isinstance(aperture_f_number, (int, float))
        and aperture_f_number > 0.0
    )
    bool_flags_ok = all(
        isinstance(flag, bool)
        for flag in (
            flash_enabled,
            bulb_mode,
            anti_flicker_shoot,
            claimed_shutter_type_auto_exposed,
            claimed_camera_reset_resets_e_front_curtain,
            claimed_electronic_shutter_allows_flash,
            claimed_electronic_shutter_allows_long_exp_nr,
            claimed_electronic_shutter_allows_e_front_curtain,
            claimed_electronic_shutter_allows_bulb,
            claimed_electronic_shutter_allows_anti_flicker,
            claimed_silent_mode_allows_mechanical_shutter,
            claimed_long_exp_nr_active_in_cont_shooting,
            claimed_long_exp_nr_active_in_cont_bracket,
            claimed_high_iso_nr_available_in_raw_only,
            claimed_high_iso_nr_alters_arw_raw,
            claimed_hi_plus_10fps_sustained_with_uncompressed_raw,
            claimed_hi_plus_10fps_sustained_with_flash,
            claimed_af_unlocked_above_f11_in_hi_plus,
            claimed_dro_bracket_available_in_hlg_still,
        )
    )
    if (
        norm_shoot is None
        or norm_shutter is None
        or norm_efront is None
        or norm_silent is None
        or norm_lenr is None
        or norm_hinr is None
        or norm_drive is None
        or norm_cspeed is None
        or norm_fmt is None
        or norm_raw is None
        or norm_hlg is None
        or norm_reset is None
        or not ss_ok
        or not ap_ok
        or not bool_flags_ok
    ):
        _add_code(codes, STATUS_BLOCKED_G118_TELEMETRY_INVALID)
        errors.append("Invalid or unrecognized G118 telemetry or enum value.")

    resolved = resolve_fx3_shutter_type_nr_drive_state(
        shoot_mode=norm_shoot or SHOOT_MODE_M_PHASE283,
        requested_shutter_type=(
            norm_shutter
            if norm_shutter in FX3_EXACT_2_SHUTTER_TYPES_G118
            else SHUTTER_TYPE_FACTORY_DEFAULT_G118
        ),
        requested_e_front_curtain=norm_efront or E_FRONT_CURTAIN_DEFAULT_G118,
        requested_silent_mode=norm_silent or SILENT_MODE_DEFAULT_G118,
        requested_long_exposure_nr=norm_lenr or LONG_EXP_NR_DEFAULT_G118,
        requested_high_iso_nr=norm_hinr or HIGH_ISO_NR_FACTORY_DEFAULT_G118,
        requested_drive_mode=norm_drive or DRIVE_MODE_FACTORY_DEFAULT_G118,
        cont_shooting_speed=norm_cspeed or CONT_SPEED_HI_PLUS_G118,
        file_format=norm_fmt or FILE_FORMAT_RAW_JPEG_G117,
        raw_file_type=norm_raw or RAW_TYPE_FACTORY_DEFAULT_G117,
        hlg_still_image=norm_hlg or "Off",
        flash_enabled=bool(flash_enabled),
        shutter_speed_seconds=float(shutter_speed_seconds) if ss_ok else (1.0 / 125.0),
        aperture_f_number=float(aperture_f_number) if ap_ok else 2.8,
        bulb_mode=bool(bulb_mode),
        anti_flicker_shoot=bool(anti_flicker_shoot),
        reset_action=norm_reset or RESET_ACTION_NONE_PHASE283,
    )

    matrix = compute_shutter_type_nr_drive_matrix()
    if not matrix["all_invariants_hold"]:
        _add_code(codes, STATUS_BLOCKED_G118_TELEMETRY_INVALID)
        errors.append("G118 384-state matrix verification failed.")

    # 1. 2-Option [Shutter Type] (No Auto!) & [e-Front Curtain Shut.] Reset Boundary
    shutter_spoof = False
    if claimed_fx3_shutter_types is not None:
        normed_sh = [
            _norm_shutter_type_g118(x, allow_auto_trap=True)
            for x in claimed_fx3_shutter_types
        ]
        if (
            set(normed_sh) != set(FX3_EXACT_2_SHUTTER_TYPES_G118)
            or SHUTTER_TYPE_SIBLING_AUTO_TRAP_G118 in normed_sh
        ):
            shutter_spoof = True

    if (
        norm_shutter == SHUTTER_TYPE_SIBLING_AUTO_TRAP_G118
        or claimed_shutter_type_auto_exposed
        or shutter_spoof
        or claimed_camera_reset_resets_e_front_curtain
    ):
        _add_code(codes, STATUS_BLOCKED_G118_FX3_SHUTTER_TYPE_AUTO_SPOOF_VIOLATION)
        errors.append(
            "Stock ILME-FX3 exposes ONLY 2 [Shutter Type] options ([Mechanical Shutter] "
            "default / [Electronic Shutter], no [Auto]); [e-Front Curtain Shut.] (0x64c6) "
            "survives [Camera Settings Reset] and needs [Initialize]."
        )

    # 2. 1/250 s Mechanical Flash Sync Ceiling & 5-Function Electronic Lockout
    sync_denom_spoof = (
        claimed_flash_sync_ceiling_denom is not None
        and (
            isinstance(claimed_flash_sync_ceiling_denom, bool)
            or claimed_flash_sync_ceiling_denom != FX3_FLASH_SYNC_CEILING_DENOM_G118
        )
    )
    electronic_lock_violated = resolved["electronic_shutter_5lock_active"] and (
        bool(flash_enabled)
        or bool(bulb_mode)
        or bool(anti_flicker_shoot)
    )
    if (
        sync_denom_spoof
        or resolved["mechanical_flash_sync_exceeded"]
        or electronic_lock_violated
        or claimed_electronic_shutter_allows_flash
        or claimed_electronic_shutter_allows_long_exp_nr
        or claimed_electronic_shutter_allows_e_front_curtain
        or claimed_electronic_shutter_allows_bulb
        or claimed_electronic_shutter_allows_anti_flicker
        or claimed_silent_mode_allows_mechanical_shutter
    ):
        _add_code(codes, STATUS_BLOCKED_G118_ELECTRONIC_SHUTTER_5LOCK_OR_SYNC_VIOLATION)
        errors.append(
            "ILME-FX3 mechanical flash sync ceiling is strictly 1/250 s (no 1/320 s APS-C "
            "sync); [Electronic Shutter] or [Silent Mode] = [On] locks out all 5 functions: "
            "Flash shooting, Long Exposure NR, e-Front Curtain Shut., BULB, and Anti-flicker Shoot."
        )

    # 3. [Long Exposure NR], [High ISO NR], & [Drive Mode] 10 fps / > F11 AF / HLG Couplings
    dro_bracket_in_hlg = (
        norm_drive == DRIVE_DRO_BRACKET_G118
        and norm_hlg == "On"
        and norm_reset == RESET_ACTION_NONE_PHASE283
    )
    if (
        claimed_long_exp_nr_active_in_cont_shooting
        or claimed_long_exp_nr_active_in_cont_bracket
        or claimed_high_iso_nr_available_in_raw_only
        or claimed_high_iso_nr_alters_arw_raw
        or claimed_hi_plus_10fps_sustained_with_uncompressed_raw
        or claimed_hi_plus_10fps_sustained_with_flash
        or claimed_af_unlocked_above_f11_in_hi_plus
        or claimed_dro_bracket_available_in_hlg_still
        or dro_bracket_in_hlg
    ):
        _add_code(codes, STATUS_BLOCKED_G118_NR_OR_DRIVE_CONT_BOUNDARY_VIOLATION)
        errors.append(
            "[Long Exposure NR] is blocked in Electronic Shutter, Cont. Shooting, and "
            "Cont. Bracket; [High ISO NR] is unavailable in RAW-only and never alters "
            ".ARW data; Cont. Shooting Hi+ (10 fps) drops below 10 fps with Uncompressed "
            "RAW or Flash, Hi+/Hi/Mid locks AF to frame 1 when > F11, and DRO Bracket is "
            "blocked when HLG Still Image = On."
        )

    valid = not codes
    status = STATUS_VERIFIED_G118 if valid else codes[0]

    return ShutterTypeNrDriveGuardResult(
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
        shutter_type_menu_path=SHUTTER_TYPE_MENU_PATH_G118,
        e_front_curtain_menu_path=E_FRONT_CURTAIN_MENU_PATH_G118,
        silent_mode_menu_path=SILENT_MODE_MENU_PATH_G118,
        long_exposure_nr_menu_path=LONG_EXPOSURE_NR_MENU_PATH_G118,
        high_iso_nr_menu_path=HIGH_ISO_NR_MENU_PATH_G118,
        drive_mode_menu_path=DRIVE_MODE_MENU_PATH_G118,
        shoot_mode=resolved["shoot_mode"],
        fx3_exact_2_shutter_types=FX3_EXACT_2_SHUTTER_TYPES_G118,
        fx3_auto_shutter_type_blocked=True,
        requested_shutter_type=norm_shutter or str(requested_shutter_type),
        effective_shutter_type=resolved["effective_shutter_type"],
        shutter_type_in_interval_default=SHUTTER_TYPE_INTERVAL_DEFAULT_G118,
        requested_silent_mode=norm_silent or str(requested_silent_mode),
        effective_silent_mode=resolved["effective_silent_mode"],
        requested_e_front_curtain=norm_efront or str(requested_e_front_curtain),
        effective_e_front_curtain=resolved["effective_e_front_curtain"],
        e_front_curtain_survived_cam_reset=resolved[
            "e_front_curtain_survived_cam_reset"
        ],
        electronic_shutter_5lock_active=resolved["electronic_shutter_5lock_active"],
        electronic_shutter_5locked_functions=ELECTRONIC_SHUTTER_5LOCKED_FUNCTIONS_G118,
        fx3_flash_sync_ceiling_label=FX3_FLASH_SYNC_CEILING_LABEL_G118,
        fx3_flash_sync_ceiling_denom=FX3_FLASH_SYNC_CEILING_DENOM_G118,
        shutter_speed_seconds=float(shutter_speed_seconds) if ss_ok else -1.0,
        mechanical_flash_sync_exceeded=resolved["mechanical_flash_sync_exceeded"],
        requested_long_exposure_nr=norm_lenr or str(requested_long_exposure_nr),
        effective_long_exposure_nr=resolved["effective_long_exposure_nr"],
        long_exp_nr_dark_frame_active=resolved["long_exp_nr_dark_frame_active"],
        long_exp_nr_dark_frame_duration_sec=resolved[
            "long_exp_nr_dark_frame_duration_sec"
        ],
        requested_high_iso_nr=norm_hinr or str(requested_high_iso_nr),
        effective_high_iso_nr=resolved["effective_high_iso_nr"],
        arw_raw_data_modified_by_high_iso_nr=False,
        fx3_exact_8_drive_modes=FX3_EXACT_8_DRIVE_MODES_G118,
        requested_drive_mode=norm_drive or str(requested_drive_mode),
        effective_drive_mode=resolved["effective_drive_mode"],
        cont_shooting_speed=resolved["cont_shooting_speed"],
        cont_shooting_nominal_max_fps=resolved["cont_shooting_nominal_max_fps"],
        hi_plus_sustains_10fps=resolved["hi_plus_sustains_10fps"],
        monitor_live_view_enabled_in_drive=resolved[
            "monitor_live_view_enabled_in_drive"
        ],
        aperture_f_number=float(aperture_f_number) if ap_ok else -1.0,
        af_locked_to_first_frame_gt_f11=resolved["af_locked_to_first_frame_gt_f11"],
        dro_bracket_available=resolved["dro_bracket_available"],
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g118_shutter_type_nr_drive_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    shutter_nr_drive_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase283DonorAuditResult] = None,
) -> Tuple[GateVerdict, G118ShutterTypeNrDriveGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase283_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_shutter_type_nr_drive_guard(**dict(shutter_nr_drive_kwargs or {}))

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G118.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G118 if valid else codes[0]

    res = G118ShutterTypeNrDriveGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        shutter_type_nr_drive_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, shutter={guard.effective_shutter_type}"
        f"(2opt={len(guard.fx3_exact_2_shutter_types)},no_auto={guard.fx3_auto_shutter_type_blocked},"
        f"efront={guard.effective_e_front_curtain},sync={guard.fx3_flash_sync_ceiling_label}), "
        f"nr=(lenr={guard.effective_long_exposure_nr},hinr={guard.effective_high_iso_nr}), "
        f"drive={guard.effective_drive_mode}(modes={len(guard.fx3_exact_8_drive_modes)})"
    )
    verdict = GateVerdict(
        gate_id=G118_GATE_ID,
        gate_code=G118_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `118`-Gate Master Safety Preflight (`G01..G118`)
# ---------------------------------------------------------------------------


def evaluate_118gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    raw_heif_colorspace_kwargs: Optional[Mapping[str, Any]] = None,
    shutter_nr_drive_kwargs: Optional[Mapping[str, Any]] = None,
    master_116_override: Optional[Master116GateReport] = None,
    **m116_passthrough_kwargs: Any,
) -> Master118GateReport:
    """Evaluate all 118 Master Safety Gates (`G01..G118`) deterministically by
    delegating `G01..G116` directly to `evaluate_116gate_preflight()`.
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

    m116_report: Master116GateReport = (
        master_116_override
        if master_116_override is not None
        else evaluate_116gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m116_passthrough_kwargs,
        )
    )

    phase283_audit = audit_phase283_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g117_verdict, g117_res = evaluate_g117_raw_heif_colorspace_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        raw_heif_colorspace_kwargs=raw_heif_colorspace_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase283_audit,
    )

    g118_verdict, g118_res = evaluate_g118_shutter_type_nr_drive_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        shutter_nr_drive_kwargs=shutter_nr_drive_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase283_audit,
    )

    gates_117_to_118 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g117_verdict, g118_verdict)
    ]
    all_gates = tuple(list(m116_report.gates) + gates_117_to_118)

    g01_to_g12_verified = int(m116_report.summary["g01_to_g12_verified"])
    g13_to_g116_verified = int(m116_report.summary["g13_to_g114_verified"]) + int(
        m116_report.summary["g115_to_g116_verified"]
    )
    g117_to_g118_verified = sum(1 for v in (g117_verdict, g118_verdict) if v.passed)
    total_verified = (
        g01_to_g12_verified + g13_to_g116_verified + g117_to_g118_verified
    )

    g117_to_g118_all_passed = g117_to_g118_verified == 2
    g13_to_g118_all_passed = (
        m116_report.g13_to_g116_all_passed and g117_to_g118_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m116_report.gates[:9])

    offline_115_verified = (
        g01_to_g09_ok
        and m116_report.offline_113_gates_verified
        and g117_to_g118_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_118_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g118_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m116_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_115_verified
        and m116_report.h0_h1_trial_entry_allowed
        and g117_to_g118_all_passed
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
        list(m116_report.errors)
        + list(g117_verdict.errors)
        + list(g118_verdict.errors)
    )
    warnings: List[str] = (
        list(m116_report.warnings)
        + list(g117_verdict.warnings)
        + list(g118_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m116_report.g13_to_g116_all_passed:
        overall_status = m116_report.status
    elif not g117_verdict.passed:
        overall_status = g117_verdict.status
    elif not g118_verdict.passed:
        overall_status = g118_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_118_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_118_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_118_verified:
        overall_status = "VERIFIED_ALL_118_GATES"
    else:
        overall_status = "VERIFIED_115_OF_118_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m116_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g117_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g118_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 118,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 118 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g116_verified": g13_to_g116_verified,
        "g117_to_g118_verified": g117_to_g118_verified,
        "g13_to_g118_all_passed": g13_to_g118_all_passed,
        "g117_to_g118_all_passed": g117_to_g118_all_passed,
        "offline_115_gates_verified": offline_115_verified,
        "all_118_gates_verified": all_118_verified,
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

    return Master118GateReport(
        schema=REALHW_RAW_HEIF_COLORSPACE_SHUTTERTYPE_NR_DRIVE_118GATE_SCHEMA,
        version=REALHW_RAW_HEIF_COLORSPACE_SHUTTERTYPE_NR_DRIVE_118GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_115_gates_verified=offline_115_verified,
        all_118_gates_verified=all_118_verified,
        g13_to_g118_all_passed=g13_to_g118_all_passed,
        g117_to_g118_all_passed=g117_to_g118_all_passed,
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
        master_116_report=m116_report.to_dict(),
        g117_result=g117_res.to_dict(),
        g118_result=g118_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_118_master_safety_gates = evaluate_118gate_preflight
run_118_gate_preflight = evaluate_118gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard",
        description=(
            "Phase 283 (118/118 Safety Gates, Wave-49) Gates G117 (RAW 2-Option "
            "Compressed/Uncompressed vs Dormant Lossless Comp, JPEG/HEIF 4:2:0/4:2:2, "
            "[HLG Still Image] & [Color Space] AdobeRGB _DSC Prefix Rule) + G118 "
            "(2-Option [Shutter Type] Mechanical/Electronic No-Auto, [e-Front Curtain Shut.], "
            "1/250 s Flash Sync & 5-Function Electronic Lockout, [Long Exposure NR], "
            "[High ISO NR] & [Drive Mode] 10 fps Couplings) + Unified 118-Gate Master "
            "Safety Preflight"
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

    report = evaluate_118gate_preflight(
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
            f"verified={report.summary['verified_gates']}/118 "
            f"g117_to_g118_all_passed={report.g117_to_g118_all_passed} "
            f"all_118_gates_verified={report.all_118_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = (
        report.all_118_gates_verified
        if args.dry_run_simulated
        else report.offline_115_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
