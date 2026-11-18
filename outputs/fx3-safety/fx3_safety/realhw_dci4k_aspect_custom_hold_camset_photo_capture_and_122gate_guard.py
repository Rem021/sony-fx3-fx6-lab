"""Phase 288 (Wave-51) Sony `ILME-FX3` (`Ver. 7.02`, `ilc/2210`) vs `ILME-FX6`
(`Ver. 6.01`) Safety Gates `G121` (`XAVC S-I DCI 4K 4096x2160` `17:9` +
Reboot-Gated `24.00p` vs Long-GOP `UHD 3840x2160` Boundary, `4264x2408` Type-A
HDMI RAW, & Still `[Aspect Ratio]` `3:2/4:3/16:9/1:1`) & `G122` (`[Reg. Custom
Shoot Set]` `11` Hold Checkboxes Still `P/A/S/M` Only vs `[Camera Set. Memory]`
`1..3` + `M1..M4` `/SONY/SETTING/%s/CAMPR%02d%c.DAT` vs `FX6` `s/SONY/PRO/CAMERA/`,
& Playback `[Photo Capture]` `DCI 4K` Lockout `_g 0x60ce` + `Slot-1` Vault Write
Firewall / `[Enlarge Image]` / `[Enlarge Initial Mag./Position]`) + Unified
`122`-Gate Master Safety Preflight (`G01..G122`).

Operationalizes Wave-51 official Sony `ILME-FX3` (`Ver. 7.02`, Help Guide
`ilc/2210`) & `ILME-FX6` (`Ver. 6.01`, `5-024-458-18`) intelligence
(`reports/2026-11-17-global-sony-wave51-uhd-vs-dci4k-aspect-ratio-recall-custom-hold-camset-memory-photo-capture-intel/README.md`)
as deterministic offline preflight verifiers (`G121` and `G122`) and delegates
`G01..G120` directly to `evaluate_120gate_preflight()`.
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
from .realhw_dualmedia_bench_interlock_and_58gate_guard import (
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
)
from .realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard import (
    _DONOR_BLOB_CACHE,
)
from .realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard import (
    Master120GateReport,
    evaluate_120gate_preflight,
)
from .realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import SPI_NOR_WRITE_AUTHORIZED
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_DCI4K_ASPECT_CUSTOM_HOLD_CAMSET_PHOTO_CAPTURE_122GATE_SCHEMA: str = (
    "realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard_v1"
)
REALHW_DCI4K_ASPECT_CUSTOM_HOLD_CAMSET_PHOTO_CAPTURE_122GATE_VERSION: str = "1.0.0"

G121_GATE_ID: str = (
    "G121_dci4k_uhd_longgop_hdmi_raw_and_still_aspect_ratio_guard"
)
G121_GATE_CODE: str = "DCI4K_UHD_LONGGOP_HDMI_RAW_AND_STILL_ASPECT_RATIO_GUARD"

G122_GATE_ID: str = (
    "G122_recall_custom_hold_camset_card_path_photo_capture_and_enlarge_guard"
)
G122_GATE_CODE: str = (
    "RECALL_CUSTOM_HOLD_CAMSET_CARD_PATH_PHOTO_CAPTURE_AND_ENLARGE_GUARD"
)

G121: str = G121_GATE_ID
G122: str = G122_GATE_ID
GATE_G121_DCI4K_UHD_LONGGOP_HDMI_RAW_AND_STILL_ASPECT_RATIO_GUARD: str = G121_GATE_CODE
GATE_G122_RECALL_CUSTOM_HOLD_CAMSET_CARD_PATH_PHOTO_CAPTURE_AND_ENLARGE_GUARD: str = (
    G122_GATE_CODE
)

ENV_CLEAN_ROOM_TEST_PHASE288: str = "FX3_CLEAN_ROOM_TEST"

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE288: float = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE288: float = 1.00

FX3_MODEL_NAME_PHASE288: str = "ILME-FX3"
FX3_MODEL_ID_PHASE288: int = 0x91030080
FX6_MODEL_NAME_PHASE288: str = "ILME-FX6"
FX3_DEFAULT_FW_VERSION_PHASE288: str = "7.02"
FX6_DEFAULT_FW_VERSION_PHASE288: str = "6.01"
FX3_HELP_GUIDE_CODE_PHASE288: str = "ilc/2210"

RESET_ACTION_NONE_PHASE288: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE288: str = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE288: str = "Reset Network Set."
RESET_ACTION_INITIALIZE_PHASE288: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE288: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE288,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE288,
    RESET_ACTION_RESET_NETWORK_SET_PHASE288,
    RESET_ACTION_INITIALIZE_PHASE288,
)

SHOOT_MODE_P_PHASE288: str = "P"
SHOOT_MODE_A_PHASE288: str = "A"
SHOOT_MODE_S_PHASE288: str = "S"
SHOOT_MODE_M_PHASE288: str = "M"
SHOOT_MODE_STILL_PASM_PHASE288: str = "Still"
SHOOT_MODE_INTELLIGENT_AUTO_PHASE288: str = "Intelligent Auto"
SHOOT_MODE_MOVIE_PHASE288: str = "Movie"
SHOOT_MODE_SQ_PHASE288: str = "S&Q"
SHOOT_MODE_MR_PHASE288: str = "MR"
PASM_SHOOT_MODES_PHASE288: Tuple[str, ...] = (
    SHOOT_MODE_P_PHASE288,
    SHOOT_MODE_A_PHASE288,
    SHOOT_MODE_S_PHASE288,
    SHOOT_MODE_M_PHASE288,
    SHOOT_MODE_STILL_PASM_PHASE288,
)
STILL_SHOOT_MODES_PHASE288: Tuple[str, ...] = PASM_SHOOT_MODES_PHASE288 + (
    SHOOT_MODE_INTELLIGENT_AUTO_PHASE288,
)
MOVIE_SHOOT_MODES_PHASE288: Tuple[str, ...] = (
    SHOOT_MODE_MOVIE_PHASE288,
    SHOOT_MODE_SQ_PHASE288,
)
ALLOWED_SHOOT_MODES_PHASE288: Tuple[str, ...] = (
    STILL_SHOOT_MODES_PHASE288 + MOVIE_SHOOT_MODES_PHASE288 + (SHOOT_MODE_MR_PHASE288,)
)

# ---------------------------------------------------------------------------
# Status & Violation Codes (G121 / G122 / Phase 288)
# ---------------------------------------------------------------------------

STATUS_VERIFIED_G121: str = (
    "VERIFIED_G121_DCI4K_UHD_HDMI_RAW_AND_STILL_ASPECT_RATIO_SAFE"
)
STATUS_VERIFIED_G122: str = (
    "VERIFIED_G122_RECALL_CUSTOM_HOLD_CAMSET_PHOTO_CAPTURE_AND_ENLARGE_SAFE"
)
STATUS_BLOCKED_PHASE288_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE288_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION: str = (
    "BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION"
)
STATUS_BLOCKED_G121_LONGGOP_DCI4K_OR_24P_SPOOF_VIOLATION: str = (
    "BLOCKED_G121_LONGGOP_DCI4K_OR_24P_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G121_HDMI_RAW_LOG_OR_STILL_ASPECT_SPOOF_VIOLATION: str = (
    "BLOCKED_G121_HDMI_RAW_LOG_OR_STILL_ASPECT_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G121_TELEMETRY_INVALID: str = (
    "BLOCKED_G121_DCI4K_ASPECT_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G122_RECALL_CUSTOM_HOLD_MODE_OR_HLG_VIOLATION: str = (
    "BLOCKED_G122_RECALL_CUSTOM_HOLD_MODE_OR_HLG_VIOLATION"
)
STATUS_BLOCKED_G122_FX3_CAMSET_CARD_PATH_SPOOF_VIOLATION: str = (
    "BLOCKED_G122_FX3_CAMSET_CARD_PATH_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G122_PHOTO_CAPTURE_DCI4K_OR_SLOT1_WRITE_VIOLATION: str = (
    "BLOCKED_G122_PHOTO_CAPTURE_DCI4K_OR_SLOT1_WRITE_VIOLATION"
)
STATUS_BLOCKED_G122_ENLARGE_IMAGE_OR_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G122_ENLARGE_IMAGE_OR_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G122_TELEMETRY_INVALID: str = (
    "BLOCKED_G122_CUSTOM_HOLD_CAMSET_PHOTO_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G121 Constants: XAVC S-I DCI 4K, Long-GOP UHD, HDMI RAW, Still Aspect
# ---------------------------------------------------------------------------

FILE_FORMAT_MENU_PATH_G121: str = "MENU -> (Shooting) -> [Image Quality/Rec] -> [File Format]"
MOVIE_SETTINGS_MENU_PATH_G121: str = "MENU -> (Shooting) -> [Image Quality/Rec] -> [Movie Settings]"
RAW_OUTPUT_MENU_PATH_G121: str = "MENU -> (Setup) -> [External Output] -> [HDMI Output Settings]"
ASPECT_RATIO_MENU_PATH_G121: str = "MENU -> (Shooting) -> [Image Quality/Rec] -> [Aspect Ratio]"

XAVC_SI_DCI_4K_UXC_RESID16_G121: int = 0x7336
XAVC_SI_DCI_4K_ALT_UXC_RESID16_G121: int = 0x61CE
XAVC_HS_4K_UXC_RESID16_G121: int = 0x76DF
XAVC_S_4K_UXC_RESID16_G121: int = 0x690C
XAVC_SI_4K_UXC_RESID16_G121: int = 0x70BA
FRAME_RATE_24_00P_UXC_RESID16_G121: int = 0x75CE
SHUTTER_MODE_UXC_RESID16_G121: int = 0x7C7C
HDMI_RAW_OUTPUT_UXC_RESID16_G121: int = 0x6E97
REBOOT_24P_G_UXC_RESID16_G121: int = 0x639B
PLAYBACK_24P_QUARANTINE_G_UXC_RESID16_G121: int = 0x63B6
ASPECT_RATIO_F_UXC_RESID16_G121: int = 0x757C
ASPECT_RATIO_UXC_RESID16_G121: int = 0xE680
ASPECT_3_2_UXC_RESID16_G121: int = 0xE4F8

FILE_FORMAT_XAVC_SI_DCI_4K_G121: str = "XAVC S-I DCI 4K"
FILE_FORMAT_XAVC_SI_4K_G121: str = "XAVC S-I 4K"
FILE_FORMAT_XAVC_HS_4K_G121: str = "XAVC HS 4K"
FILE_FORMAT_XAVC_S_4K_G121: str = "XAVC S 4K"
LONGGOP_4K_FILE_FORMATS_G121: Tuple[str, ...] = (
    FILE_FORMAT_XAVC_HS_4K_G121,
    FILE_FORMAT_XAVC_S_4K_G121,
)
UHD_ONLY_4K_FILE_FORMATS_G121: Tuple[str, ...] = (
    FILE_FORMAT_XAVC_HS_4K_G121,
    FILE_FORMAT_XAVC_S_4K_G121,
    FILE_FORMAT_XAVC_SI_4K_G121,
)
ALLOWED_4K_FILE_FORMATS_G121: Tuple[str, ...] = (
    FILE_FORMAT_XAVC_SI_DCI_4K_G121,
    FILE_FORMAT_XAVC_SI_4K_G121,
    FILE_FORMAT_XAVC_HS_4K_G121,
    FILE_FORMAT_XAVC_S_4K_G121,
)
FILE_FORMAT_FACTORY_DEFAULT_G121: str = FILE_FORMAT_XAVC_S_4K_G121

DCI_4K_DIMENSIONS_G121: Tuple[int, int] = (4096, 2160)
DCI_4K_ASPECT_LABEL_G121: str = "17:9"
UHD_4K_DIMENSIONS_G121: Tuple[int, int] = (3840, 2160)
UHD_4K_ASPECT_LABEL_G121: str = "16:9"
HDMI_RAW_DIMENSIONS_G121: Tuple[int, int] = (4264, 2408)
HDMI_RAW_ASPECT_LABEL_G121: str = "16:9"

DCI_4K_ALLOWED_REC_RATES_G121: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "25p",
    "29.97p",
    "50p",
    "59.94p",
)
DCI_4K_BITRATES_MBPS_G121: Dict[str, int] = {
    "23.98p": 240,
    "24.00p": 240,
    "25p": 250,
    "29.97p": 300,
    "50p": 500,
    "59.94p": 600,
}
UHD_4K_ALLOWED_REC_RATES_G121: Tuple[str, ...] = (
    "23.98p",
    "25p",
    "29.97p",
    "50p",
    "59.94p",
    "100p",
    "119.88p",
)
HDMI_RAW_ALLOWED_RATES_G121: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "25p",
    "29.97p",
    "50p",
    "59.94p",
)
DCI_4K_ALLOWED_SQ_FPS_G121: Tuple[int, ...] = (1, 2, 3, 6, 12, 24, 48)
UHD_4K_MAX_SQ_FPS_G121: int = 120
DCI_4K_FORBIDDEN_HFR_FPS_G121: Tuple[int, ...] = (100, 120)

CARD_TIER_CFEXPRESS_VPG200_G121: str = "CFexpress Type A (VPG200+)"
CARD_TIER_SDXC_V90_G121: str = "SDXC UHS-II (V90+)"
CARD_TIER_SDXC_V60_G121: str = "SDXC UHS-II (V60)"
CARD_TIER_SDXC_V30_G121: str = "SDXC UHS-I (V30)"
ALLOWED_CARD_TIERS_G121: Tuple[str, ...] = (
    CARD_TIER_CFEXPRESS_VPG200_G121,
    CARD_TIER_SDXC_V90_G121,
    CARD_TIER_SDXC_V60_G121,
    CARD_TIER_SDXC_V30_G121,
)
DCI4K_600M_ALLOWED_CARD_TIERS_G121: Tuple[str, ...] = (
    CARD_TIER_CFEXPRESS_VPG200_G121,
    CARD_TIER_SDXC_V90_G121,
)

LOG_SHOOTING_OFF_G121: str = "Off"
LOG_SHOOTING_FLEXIBLE_ISO_G121: str = "Flexible ISO"
LOG_SHOOTING_CINE_EI_G121: str = "Cine EI"
LOG_SHOOTING_CINE_EI_QUICK_G121: str = "Cine EI Quick"
ALLOWED_LOG_SHOOTING_MODES_G121: Tuple[str, ...] = (
    LOG_SHOOTING_OFF_G121,
    LOG_SHOOTING_FLEXIBLE_ISO_G121,
    LOG_SHOOTING_CINE_EI_G121,
    LOG_SHOOTING_CINE_EI_QUICK_G121,
)

ASPECT_RATIO_3_2_G121: str = "3:2"
ASPECT_RATIO_4_3_G121: str = "4:3"
ASPECT_RATIO_16_9_G121: str = "16:9"
ASPECT_RATIO_1_1_G121: str = "1:1"
ALLOWED_STILL_ASPECT_RATIOS_G121: Tuple[str, ...] = (
    ASPECT_RATIO_3_2_G121,
    ASPECT_RATIO_4_3_G121,
    ASPECT_RATIO_16_9_G121,
    ASPECT_RATIO_1_1_G121,
)
STILL_ASPECT_RATIO_DEFAULT_G121: str = ASPECT_RATIO_3_2_G121

STILL_IMAGE_SIZE_L_G121: str = "L"
STILL_IMAGE_SIZE_M_G121: str = "M"
STILL_IMAGE_SIZE_S_G121: str = "S"
ALLOWED_STILL_IMAGE_SIZES_G121: Tuple[str, ...] = (
    STILL_IMAGE_SIZE_L_G121,
    STILL_IMAGE_SIZE_M_G121,
    STILL_IMAGE_SIZE_S_G121,
)

STILL_ASPECT_RESOLUTION_TABLE_G121: Dict[str, Dict[str, Tuple[str, Tuple[int, int]]]] = {
    ASPECT_RATIO_3_2_G121: {
        STILL_IMAGE_SIZE_L_G121: ("12M", (4240, 2832)),
        STILL_IMAGE_SIZE_M_G121: ("5.1M", (2768, 1848)),
        STILL_IMAGE_SIZE_S_G121: ("3.0M", (2128, 1416)),
    },
    ASPECT_RATIO_4_3_G121: {
        STILL_IMAGE_SIZE_L_G121: ("11M", (3776, 2832)),
        STILL_IMAGE_SIZE_M_G121: ("4.6M", (2464, 1848)),
        STILL_IMAGE_SIZE_S_G121: ("2.7M", (1888, 1416)),
    },
    ASPECT_RATIO_16_9_G121: {
        STILL_IMAGE_SIZE_L_G121: ("10M", (4240, 2384)),
        STILL_IMAGE_SIZE_M_G121: ("4.3M", (2768, 1560)),
        STILL_IMAGE_SIZE_S_G121: ("2.6M", (2128, 1200)),
    },
    ASPECT_RATIO_1_1_G121: {
        STILL_IMAGE_SIZE_L_G121: ("8.0M", (2832, 2832)),
        STILL_IMAGE_SIZE_M_G121: ("3.4M", (1840, 1840)),
        STILL_IMAGE_SIZE_S_G121: ("2.0M", (1408, 1408)),
    },
}
FX3_RAW_FULL_SENSOR_DIMENSIONS_G121: Tuple[int, int] = (4240, 2832)

# ---------------------------------------------------------------------------
# Gate G122 Constants: [Reg. Custom Shoot Set], [Camera Set. Memory],
# Card Paths, Playback [Photo Capture] & [Enlarge Initial Mag./Position]
# ---------------------------------------------------------------------------

REG_CUSTOM_SHOOT_SET_MENU_PATH_G122: str = (
    "MENU -> (Shooting) -> [Shooting Mode] -> [Reg. Custom Shoot Set]"
)
CAMERA_SET_MEMORY_MENU_PATH_G122: str = (
    "MENU -> (Shooting) -> [Shooting Mode] -> [Camera Set. Memory]"
)
SAVE_LOAD_SETTINGS_MENU_PATH_G122: str = (
    "MENU -> (Setup) -> [Reset/Save Settings] -> [Save/Load Settings]"
)
PHOTO_CAPTURE_MENU_PATH_G122: str = "MENU -> (Playback) -> [Edit] -> [Photo Capture]"
ENLARGE_IMAGE_MENU_PATH_G122: str = (
    "MENU -> (Playback) -> [Magnification] -> [Enlarge Image]"
)

REG_CUSTOM_SHOOT_SET_UXC_RESID16_G122: int = 0x7631
RECALL_CUSTOM_HOLD_1_UXC_RESID16_G122: int = 0x60B4
RECALL_CUSTOM_HOLD_2_UXC_RESID16_G122: int = 0x7581
RECALL_CUSTOM_HOLD_3_UXC_RESID16_G122: int = 0x725B
CAMERA_SET_MEMORY_UXC_RESID16_G122: int = 0x75A6
MEMORY_RECALL_MEDIA_UXC_RESID16_G122: int = 0x763C
PHOTO_CAPTURE_UXC_RESID16_G122: int = 0x6856
PHOTO_CAPTURE_DCI4K_LOCKOUT_G_UXC_RESID16_G122: int = 0x60CE
JPEG_HEIF_SWITCH_UXC_RESID16_G122: int = 0x6938
ENLARGE_IMAGE_UXC_RESID16_G122: int = 0xE8CB
ENLARGE_INITIAL_MAG_UXC_RESID16_G122: int = 0x6B6E
ENLARGE_INITIAL_POSITION_UXC_RESID16_G122: int = 0x781F

RECALL_CUSTOM_HOLD_SLOTS_G122: Tuple[str, ...] = (
    "Recall Custom hold 1",
    "Recall Custom hold 2",
    "Recall Custom hold 3",
)
FX3_EXACT_11_CUSTOM_HOLD_CHECKBOX_KEYS_G122: Tuple[str, ...] = (
    "shooting_mode",
    "aperture",
    "shutter_speed",
    "exposure_comp",
    "iso_sensitivity",
    "metering_mode",
    "drive_mode",
    "focus_mode",
    "focus_area",
    "af_on",
    "still_af_track_sens",
)
FX3_EXACT_11_CUSTOM_HOLD_BOOL_SYMBOLS_G122: Tuple[str, ...] = tuple(
    f"is_checked_recall_custom_hold{i}" for i in range(11)
)
HLG_LOCKOUT_RECALL_PARAMS_G122: Tuple[str, ...] = (
    "iso_sensitivity",
    "drive_mode",
)

CAMERA_MEMORY_BODY_BANKS_G122: Tuple[str, ...] = ("1", "2", "3")
CAMERA_MEMORY_CARD_BANKS_G122: Tuple[str, ...] = ("M1", "M2", "M3", "M4")
ALLOWED_MEMORY_RECALL_MEDIA_SLOTS_G122: Tuple[str, ...] = ("Slot 1", "Slot 2")

FX3_CAMPR_PATH_TEMPLATE_G122: str = "%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT"
FX3_CAMSET_PATH_TEMPLATE_G122: str = "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"
FX3_ALLOWED_CARD_PATH_PREFIXES_G122: Tuple[str, ...] = (
    "/PRIVATE/SONY/SETTING/",
    "/SONY/SETTING/",
)
FX6_FORBIDDEN_CARD_PATH_MARKERS_G122: Tuple[str, ...] = (
    "PRIVATE/SONY/PRO/CAMERA",
    "SONY/PRO/CAMERA",
    "SONY/PRO/SCENE",
    "s/SONY/PRO/CAMERA/",
    "s/SONY/PRO/SCENE/",
)

PHOTO_CAPTURE_TYPE_JPEG_G122: str = "JPEG"
PHOTO_CAPTURE_TYPE_HEIF_420_G122: str = "HEIF(4:2:0)"
PHOTO_CAPTURE_TYPE_HEIF_422_G122: str = "HEIF(4:2:2)"
ALLOWED_PHOTO_CAPTURE_FILE_TYPES_G122: Tuple[str, ...] = (
    PHOTO_CAPTURE_TYPE_JPEG_G122,
    PHOTO_CAPTURE_TYPE_HEIF_420_G122,
    PHOTO_CAPTURE_TYPE_HEIF_422_G122,
)
PHOTO_CAPTURE_FILE_TYPE_DEFAULT_G122: str = PHOTO_CAPTURE_TYPE_JPEG_G122

PHOTO_CAPTURE_4K_MP_LABEL_G122: str = "8.3M"
PHOTO_CAPTURE_4K_DIMENSIONS_G122: Tuple[int, int] = (3840, 2160)
PHOTO_CAPTURE_HD_MP_LABEL_G122: str = "2.1M"
PHOTO_CAPTURE_HD_DIMENSIONS_G122: Tuple[int, int] = (1920, 1080)

ENLARGE_INITIAL_MAG_STANDARD_G122: str = "Standard. Mag."
ENLARGE_INITIAL_MAG_PREVIOUS_G122: str = "Previous Mag."
ALLOWED_ENLARGE_INITIAL_MAG_G122: Tuple[str, ...] = (
    ENLARGE_INITIAL_MAG_STANDARD_G122,
    ENLARGE_INITIAL_MAG_PREVIOUS_G122,
)
ENLARGE_INITIAL_MAG_DEFAULT_G122: str = ENLARGE_INITIAL_MAG_STANDARD_G122

ENLARGE_INITIAL_POS_FOCUSED_G122: str = "Focused Position"
ENLARGE_INITIAL_POS_CENTER_G122: str = "Center"
ALLOWED_ENLARGE_INITIAL_POS_G122: Tuple[str, ...] = (
    ENLARGE_INITIAL_POS_FOCUSED_G122,
    ENLARGE_INITIAL_POS_CENTER_G122,
)
ENLARGE_INITIAL_POS_DEFAULT_G122: str = ENLARGE_INITIAL_POS_FOCUSED_G122

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, Targeted Pread on appFw.so, <0.20s)
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE288: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (62_668_366, b"BKID_APP_setting_movie_rec_frame_rate_xavc_s_i_dci_4k"),
    (62_671_072, b"BKID_APP_setting_movie_record_setting_xavc_s_i_dci_4k_60p"),
    (62_671_429, b"BKID_APP_setting_movie_record_setting_xavc_s_i_dci_4k_25p"),
    (60_718_110, b"XAVC_S_I_DCI_4K"),
    (61_899_012, b"XAVC_S_I_DCI_4K_IMAGER_FRAME_RATE_OVER_60_50"),
    (62_667_636, b"BKID_APP_setting_aspect_ratio"),
    (62_847_712, b"BKID_APP_extern_menu_still_aspect"),
    (62_661_339, b"BKID_APP_shoot_set_registration_shooting_mode_available0"),
    (62_661_567, b"BKID_APP_shoot_set_registration_aperture_available0"),
    (63_079_298, b"is_checked_recall_custom_hold0"),
    (63_079_608, b"is_checked_recall_custom_hold10"),
    (59_801_607, b"%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT"),
    (59_801_508, b"%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"),
    (62_046_185, b"PHOTO_CAPTURE"),
    (62_691_860, b"BKID_APP_setting_photo_capture_file_type"),
    (62_691_677, b"BKID_APP_setting_magnif_set_in_large"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE288: str = (
    "a4a80b0fa107fc04868b4b4cd95f1674209f9e6129bd795484edb3df38a6f73d"
)

PINNED_FX6_APPFW_SLICES_PHASE288: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (39_026_448, b"BKID_APP_EXTERN_DCI_4K_REC_FRAME_RATE"),
    (41_016_140, b"BKID_APP_SETTING_MOVIE_REC_FRAME_RATE_XAVC_S_I_DCI_4K_CURRENT_VALUE"),
    (40_920_169, b"BKID_APP_MARKER_ASPECT_CUSTOM_RATIO_WIDTH"),
    (40_920_211, b"BKID_APP_MARKER_ASPECT_CUSTOM_RATIO_HEIGHT"),
    (40_941_579, b"BKID_APP_SETTING_ASPECT_MARKER"),
    (39_352_923, b"s/SONY/PRO/CAMERA/"),
    (39_354_135, b"CAMPR%02d"),
    (41_748_974, b"PRODUCT_MODEL_CHAPLIN"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE288: str = (
    "3a9396b48d87fa4c755d8f2d59d4f7376295e0007c5c2281c399da320a0b25e1"
)

PINNED_PHASE288_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE288,
        tuple(tok for _off, tok in PINNED_FX3_APPFW_SLICES_PHASE288),
        "FX3_APPFW_WAVE51_DCI4K_ASPECT_HOLD_CAMSET_PHOTO_SLICES",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"XAVC S-I DCI 4K",
            b"XAVC S-I 4K",
            b"XAVC HS 4K",
            b"XAVC S 4K",
            b"24.00p",
            b"Shutter Mode",
            b"RAW Output",
            b"Aspect Ratio",
            b"Reg. Custom Shoot Set",
            b"Recall Custom hold 1",
            b"Recall Custom hold 2",
            b"Recall Custom hold 3",
            b"Import Current Setting",
            b"Camera Set. Memory",
            b"Recall Camera Setting",
            b"Memory/Recall Media",
            b"Photo Capture",
            b"JPEG/HEIF Switch",
            b"Standard. Mag.",
            b"Previous Mag.",
            b"Enlarge Initial Mag.",
            b"Enlarge Initial Position",
            b"Focused Position",
        ),
        "FX3_UXC_F_WAVE51_DCI4K_ASPECT_HOLD_CAMSET_PHOTO_STRINGS",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            b"XAVC S-I DCI 4K",
            b"24.00p",
            "纵横比".encode("utf-8"),
            "注册自定义拍摄设置".encode("utf-8"),
            "拍摄设置存储".encode("utf-8"),
            "初始放大倍率".encode("utf-8"),
        ),
        "FX3_UXC_F_ZHCN_WAVE51_RESID16_PARITY",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            b"XAVC S-I DCI 4K",
            b"24.00p",
            "長寬比".encode("utf-8"),
            "登錄自訂拍攝設定".encode("utf-8"),
            "拍攝設定記憶".encode("utf-8"),
            "初始放大率".encode("utf-8"),
        ),
        "FX3_UXC_F_ZHTW_WAVE51_RESID16_PARITY",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            b"XAVC S-I DCI 4K",
            b"24.00p",
            "横縦比".encode("utf-8"),
            "ｶｽﾀﾑ撮影設定登録".encode("utf-8"),
            "撮影設定登録".encode("utf-8"),
            "拡大の初期倍率".encode("utf-8"),
        ),
        "FX3_UXC_F_JA_WAVE51_RESID16_PARITY",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Aspect Ratio",
            b"3:2",
            b"4:3",
            b"16:9",
            b"1:1",
            b"Enlarge Image",
            b"Center",
        ),
        "FX3_UXC_ASPECT_AND_ENLARGE_IMAGE_STRINGS",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"XAVC S-I DCI 4K",
            b"24.00p",
            b"rate 24.00p cannot be played back in",
            b'set to "XAVC S-I DCI 4K".',
        ),
        "FX3_UXC_G_DCI4K_LOCKOUT_AND_24P_REBOOT_QUARANTINE",
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
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE288,
        tuple(tok for _off, tok in PINNED_FX6_APPFW_SLICES_PHASE288),
        "FX6_APPFW_WAVE51_DCI4K_MARKER_CUSTOM_ASPECT_PRO_PATH_SLICES",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"Custom Aspect Ratio",
            b"Enlarge Screen",
            b"Marker User Box",
        ),
        "FX6_UXC_CUSTOM_ASPECT_MARKER_STRINGS",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"Aspect Marker",
            b"Aspect Mask",
            b"Aspect Select",
            b"Cam ID + Reel#",
        ),
        "FX6_UXC_2_ASPECT_MARKER_AND_CAM_ID_REEL",
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase288DonorAuditResult:
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
class Dci4kUhdLongGopHdmiRawAspectGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    reset_action: str
    file_format_menu_path: str
    movie_settings_menu_path: str
    raw_output_menu_path: str
    aspect_ratio_menu_path: str
    shoot_mode: str
    requested_file_format: str
    effective_file_format: str
    movie_dimensions: Tuple[int, int]
    movie_aspect_label: str
    is_dci_4k_all_intra: bool
    is_longgop_uhd_only: bool
    rec_frame_rate: str
    bitrate_mbps: int
    card_tier: str
    sq_fps: int
    switched_24_00p_boundary: bool
    reboot_completed_for_24_00p: bool
    playback_24_00p_quarantine_enforced: bool
    hdmi_raw_output_enabled: bool
    hdmi_raw_dimensions: Tuple[int, int]
    hdmi_raw_frame_rate: str
    log_shooting: str
    requested_still_aspect_ratio: str
    effective_still_aspect_ratio: str
    requested_still_image_size: str
    effective_still_image_size: str
    still_aspect_megapixel_label: str
    still_jpeg_heif_dimensions: Tuple[int, int]
    apsc_s35_shooting: str
    arw_retains_full_3_2_pixels: bool
    still_aspect_reset_on_cam_reset: bool
    fx6_still_aspect_supported: bool
    fx6_longgop_has_dci4k: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G121Dci4kAspectRatioGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    dci4k_aspect_ratio_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CustomHoldCamsetPhotoEnlargeGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    reset_action: str
    reg_custom_shoot_set_menu_path: str
    camera_set_memory_menu_path: str
    save_load_settings_menu_path: str
    photo_capture_menu_path: str
    enlarge_image_menu_path: str
    shoot_mode: str
    recall_custom_hold_requested: bool
    recall_custom_hold_slot: str
    recalled_hold_params: Tuple[str, ...]
    exact_11_custom_hold_keys: Tuple[str, ...]
    hlg_still_image_forced_off: bool
    recall_custom_hold_survived_cam_reset: bool
    camset_memory_slot: str
    camset_media_slot: str
    effective_campr_path_template: str
    effective_camset_path_template: str
    submitted_card_path: str
    fx6_pro_camera_path_rejected: bool
    format_slot_1_protected: bool
    body_memory_banks_survived_cam_reset: bool
    photo_capture_requested: bool
    playback_slot: str
    playback_source_file_format: str
    playback_source_resolution_tier: str
    requested_photo_capture_file_type: str
    effective_photo_capture_file_type: str
    photo_capture_output_mp_label: str
    photo_capture_output_dimensions: Tuple[int, int]
    photo_capture_dci4k_locked: bool
    photo_capture_slot1_write_blocked: bool
    enlarge_image_requested: bool
    playback_media_kind: str
    requested_enlarge_initial_mag: str
    effective_enlarge_initial_mag: str
    requested_enlarge_initial_position: str
    effective_enlarge_initial_position: str
    enlarge_settings_survived_cam_reset: bool
    fx6_photo_capture_supported: bool
    fx6_playback_enlarge_supported: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G122CustomHoldCamsetPhotoEnlargeGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    custom_hold_camset_photo_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master122GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_119_gates_verified: bool
    all_122_gates_verified: bool
    g13_to_g122_all_passed: bool
    g121_to_g122_all_passed: bool
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
    master_120_report: Dict[str, Any]
    g121_result: Dict[str, Any]
    g122_result: Dict[str, Any]
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
    for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE288):
        if os.environ.get(env_key, "").strip() in _TRUTHY_CLEAN_ROOM_TOKENS:
            return True
    return False


def _default_donor_budget_seconds_phase288() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return DONOR_CHECK_CI_MAX_SECONDS_PHASE288
    return DONOR_CHECK_MAX_SECONDS_PHASE288


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


def _norm_reset_action_phase288(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE_PHASE288
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE288
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE288
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE_PHASE288
    return None


def _norm_shoot_mode_phase288(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "P": SHOOT_MODE_P_PHASE288,
        "A": SHOOT_MODE_A_PHASE288,
        "S": SHOOT_MODE_S_PHASE288,
        "M": SHOOT_MODE_M_PHASE288,
        "STILL": SHOOT_MODE_STILL_PASM_PHASE288,
        "INTELLIGENT AUTO": SHOOT_MODE_INTELLIGENT_AUTO_PHASE288,
        "IAUTO": SHOOT_MODE_INTELLIGENT_AUTO_PHASE288,
        "MOVIE": SHOOT_MODE_MOVIE_PHASE288,
        "S&Q": SHOOT_MODE_SQ_PHASE288,
        "SQ": SHOOT_MODE_SQ_PHASE288,
        "MR": SHOOT_MODE_MR_PHASE288,
    }
    return mapping.get(u)


def _norm_on_off_phase288(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "ON":
        return "On"
    if u == "OFF":
        return "Off"
    return None


def _norm_file_format_g121(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_4K_FILE_FORMATS_G121:
        if u == item.upper():
            return item
    return None


def _norm_rec_frame_rate_g121(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").lower()
    mapping = {
        "23.98p": "23.98p",
        "24.00p": "24.00p",
        "24p": "24.00p",
        "25p": "25p",
        "29.97p": "29.97p",
        "30p": "29.97p",
        "50p": "50p",
        "59.94p": "59.94p",
        "60p": "59.94p",
        "100p": "100p",
        "119.88p": "119.88p",
        "120p": "119.88p",
    }
    return mapping.get(u)


def _norm_card_tier_g121(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_CARD_TIERS_G121:
        if u == item.upper():
            return item
    if "CFEXPRESS" in u or "VPG200" in u or "VPG400" in u:
        return CARD_TIER_CFEXPRESS_VPG200_G121
    if "V90" in u:
        return CARD_TIER_SDXC_V90_G121
    if "V60" in u:
        return CARD_TIER_SDXC_V60_G121
    if "V30" in u:
        return CARD_TIER_SDXC_V30_G121
    return None


def _norm_log_shooting_g121(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_LOG_SHOOTING_MODES_G121:
        if u == item.upper():
            return item
    return None


def _norm_still_aspect_ratio_g121(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]")
    if u in ALLOWED_STILL_ASPECT_RATIOS_G121:
        return u
    return None


def _norm_still_image_size_g121(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u in ALLOWED_STILL_IMAGE_SIZES_G121:
        return u
    return None


def _norm_recall_custom_hold_slot_g122(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in RECALL_CUSTOM_HOLD_SLOTS_G122:
        if u == item.upper():
            return item
    return None


def _norm_media_slot_g122(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("SLOT 1", "SLOT1"):
        return "Slot 1"
    if u in ("SLOT 2", "SLOT2"):
        return "Slot 2"
    return None


def _norm_camset_memory_slot_g122(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    for item in CAMERA_MEMORY_BODY_BANKS_G122 + CAMERA_MEMORY_CARD_BANKS_G122:
        if u == item:
            return item
    return None


def _norm_photo_capture_file_type_g122(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    if u == "JPEG":
        return PHOTO_CAPTURE_TYPE_JPEG_G122
    if u in ("HEIF(4:2:0)", "HEIF4:2:0", "HEIF420"):
        return PHOTO_CAPTURE_TYPE_HEIF_420_G122
    if u in ("HEIF(4:2:2)", "HEIF4:2:2", "HEIF422"):
        return PHOTO_CAPTURE_TYPE_HEIF_422_G122
    return None


def _norm_enlarge_initial_mag_g122(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_ENLARGE_INITIAL_MAG_G122:
        if u == item.upper():
            return item
    return None


def _norm_enlarge_initial_pos_g122(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    for item in ALLOWED_ENLARGE_INITIAL_POS_G122:
        if u == item.upper():
            return item
    return None


# ---------------------------------------------------------------------------
# 1. Local O_RDONLY Donor Audit & Clean-Room Synthetic Fallback (< 0.20s)
# ---------------------------------------------------------------------------


def audit_phase288_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase288DonorAuditResult:
    """Strictly `os.open(..., os.O_RDONLY)` audit of Phase 288 Wave-51 local donor
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
        else PINNED_PHASE288_DONOR_SPECS
    )

    if clean_forced:
        elapsed = time.monotonic() - t0
        return Phase288DonorAuditResult(
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
            return Phase288DonorAuditResult(
                valid=False,
                status=STATUS_BLOCKED_PHASE288_DONOR_INTEGRITY,
                verification_mode="LOCAL_DONOR_O_RDONLY",
                access_mode="O_RDONLY",
                files_inspected=0,
                elapsed_seconds=elapsed,
                within_budget_200ms=(elapsed <= _default_donor_budget_seconds_phase288()),
                raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
                checked_markers=(),
                missing_markers=tuple(missing_paths),
                fx3_contracts_verified=False,
                fx6_contracts_verified=False,
                four_lang_resid16_parity_verified=False,
                sha256_by_artifact={},
                bytes_by_artifact={},
                errors=(
                    f"Explicit work_root missing Wave-51 donor files: {missing_paths}",
                ),
                warnings=(),
            )
        elapsed = time.monotonic() - t0
        return Phase288DonorAuditResult(
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
                "Local Wave-51 Sony donor binaries absent; using CLEAN_ROOM_SYNTHETIC pinned SHA-256 contracts.",
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
                p, PINNED_FX3_APPFW_SLICES_PHASE288
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tokens_ok = _read_targeted_slices_o_rdonly(
                p, PINNED_FX6_APPFW_SLICES_PHASE288
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
    budget = _default_donor_budget_seconds_phase288()
    within_budget = elapsed <= budget
    if not within_budget:
        warnings.append(
            f"Phase 288 donor audit took {elapsed:.4f}s (budget {budget:.2f}s)."
        )

    valid = (not errors) and fx3_ok and fx6_ok and lang_ok
    return Phase288DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE288_DONOR_INTEGRITY,
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
# 2. Gate G121: XAVC S-I DCI 4K (4096x2160) & Rebooted 24.00p vs Long-GOP UHD,
#    4264x2408 Type-A HDMI RAW, & Still [Aspect Ratio] (3:2/4:3/16:9/1:1)
# ---------------------------------------------------------------------------


def resolve_fx3_dci4k_hdmi_raw_and_aspect_ratio_state(
    *,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE288,
    requested_file_format: str = FILE_FORMAT_XAVC_SI_DCI_4K_G121,
    rec_frame_rate: str = "23.98p",
    card_tier: str = CARD_TIER_CFEXPRESS_VPG200_G121,
    sq_fps: int = 24,
    switched_24_00p_boundary: bool = False,
    reboot_completed_for_24_00p: bool = False,
    playback_24_00p_quarantine_enforced: bool = True,
    hdmi_raw_output_enabled: bool = False,
    hdmi_raw_frame_rate: str = "23.98p",
    log_shooting: str = LOG_SHOOTING_FLEXIBLE_ISO_G121,
    requested_still_aspect_ratio: str = STILL_ASPECT_RATIO_DEFAULT_G121,
    requested_still_image_size: str = STILL_IMAGE_SIZE_L_G121,
    apsc_s35_shooting: str = "Off",
    reset_action: str = RESET_ACTION_NONE_PHASE288,
) -> Dict[str, Any]:
    """Resolve effective Wave-51 Gate `G121` FX3 Ver. 7.02 codec/aspect state."""
    eff_reset = _norm_reset_action_phase288(reset_action) or RESET_ACTION_NONE_PHASE288
    eff_fmt = (
        _norm_file_format_g121(requested_file_format)
        or FILE_FORMAT_XAVC_SI_DCI_4K_G121
    )
    eff_aspect = (
        _norm_still_aspect_ratio_g121(requested_still_aspect_ratio)
        or STILL_ASPECT_RATIO_DEFAULT_G121
    )
    eff_size = (
        _norm_still_image_size_g121(requested_still_image_size)
        or STILL_IMAGE_SIZE_L_G121
    )
    eff_apsc = _norm_on_off_phase288(apsc_s35_shooting) or "Off"

    still_aspect_reset_on_cam_reset = eff_reset in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE288,
        RESET_ACTION_INITIALIZE_PHASE288,
    )
    if still_aspect_reset_on_cam_reset:
        eff_aspect = STILL_ASPECT_RATIO_DEFAULT_G121
        eff_size = STILL_IMAGE_SIZE_L_G121

    if eff_apsc == "On" and eff_size == STILL_IMAGE_SIZE_L_G121:
        eff_size = STILL_IMAGE_SIZE_M_G121

    is_dci = eff_fmt == FILE_FORMAT_XAVC_SI_DCI_4K_G121
    is_longgop = eff_fmt in LONGGOP_4K_FILE_FORMATS_G121
    dims = DCI_4K_DIMENSIONS_G121 if is_dci else UHD_4K_DIMENSIONS_G121
    aspect_lbl = DCI_4K_ASPECT_LABEL_G121 if is_dci else UHD_4K_ASPECT_LABEL_G121
    mp_lbl, still_dims = STILL_ASPECT_RESOLUTION_TABLE_G121[eff_aspect][eff_size]

    norm_rate = _norm_rec_frame_rate_g121(rec_frame_rate) or "23.98p"
    bitrate = DCI_4K_BITRATES_MBPS_G121.get(norm_rate, 240 if is_dci else 200)

    return {
        "effective_file_format": eff_fmt,
        "movie_dimensions": dims,
        "movie_aspect_label": aspect_lbl,
        "is_dci_4k_all_intra": is_dci,
        "is_longgop_uhd_only": is_longgop,
        "rec_frame_rate": norm_rate,
        "bitrate_mbps": bitrate,
        "card_tier": _norm_card_tier_g121(card_tier) or CARD_TIER_CFEXPRESS_VPG200_G121,
        "sq_fps": int(sq_fps),
        "hdmi_raw_output_enabled": bool(hdmi_raw_output_enabled),
        "hdmi_raw_dimensions": HDMI_RAW_DIMENSIONS_G121,
        "hdmi_raw_frame_rate": _norm_rec_frame_rate_g121(hdmi_raw_frame_rate) or "23.98p",
        "log_shooting": _norm_log_shooting_g121(log_shooting) or LOG_SHOOTING_OFF_G121,
        "effective_still_aspect_ratio": eff_aspect,
        "effective_still_image_size": eff_size,
        "still_aspect_megapixel_label": mp_lbl,
        "still_jpeg_heif_dimensions": still_dims,
        "apsc_s35_shooting": eff_apsc,
        "arw_retains_full_3_2_pixels": True,
        "still_aspect_reset_on_cam_reset": still_aspect_reset_on_cam_reset,
        "shoot_mode": _norm_shoot_mode_phase288(shoot_mode) or SHOOT_MODE_MOVIE_PHASE288,
        "switched_24_00p_boundary": bool(switched_24_00p_boundary),
        "reboot_completed_for_24_00p": bool(reboot_completed_for_24_00p),
        "playback_24_00p_quarantine_enforced": bool(playback_24_00p_quarantine_enforced),
    }


def compute_dci4k_hdmi_raw_and_aspect_ratio_matrix() -> Dict[str, Any]:
    """Deterministic `384`-state cross-product across `(4 file_formats x 4 rate/sq x
    4 still aspects x 3 apsc/reset configs x 2 hdmi_raw)` verifying `G121` invariants.
    """
    states = 0
    dci4k_all_intra_states = 0
    longgop_uhd_states = 0
    aspect_reset_to_3_2_states = 0
    apsc_l_to_m_stepdown_states = 0

    rate_sq_cases = (
        ("23.98p", 24),
        ("24.00p", 24),
        ("59.94p", 48),
        ("59.94p", 120),
    )
    apsc_reset_cases = (
        ("Off", RESET_ACTION_NONE_PHASE288),
        ("On", RESET_ACTION_NONE_PHASE288),
        ("Off", RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE288),
    )

    for fmt in ALLOWED_4K_FILE_FORMATS_G121:
        for rate, sq_fps in rate_sq_cases:
            for aspect in ALLOWED_STILL_ASPECT_RATIOS_G121:
                for apsc, r_act in apsc_reset_cases:
                    for hdmi_raw in (False, True):
                        states += 1
                        r = resolve_fx3_dci4k_hdmi_raw_and_aspect_ratio_state(
                            requested_file_format=fmt,
                            rec_frame_rate=rate,
                            sq_fps=sq_fps,
                            requested_still_aspect_ratio=aspect,
                            requested_still_image_size=STILL_IMAGE_SIZE_L_G121,
                            apsc_s35_shooting=apsc,
                            reset_action=r_act,
                            hdmi_raw_output_enabled=hdmi_raw,
                        )
                        if r["is_dci_4k_all_intra"]:
                            assert r["movie_dimensions"] == DCI_4K_DIMENSIONS_G121
                            assert r["movie_aspect_label"] == "17:9"
                            dci4k_all_intra_states += 1
                        else:
                            assert r["movie_dimensions"] == UHD_4K_DIMENSIONS_G121
                            assert r["movie_aspect_label"] == "16:9"
                        if r["is_longgop_uhd_only"]:
                            longgop_uhd_states += 1
                        if r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE288:
                            assert (
                                r["effective_still_aspect_ratio"]
                                == STILL_ASPECT_RATIO_DEFAULT_G121
                            )
                            aspect_reset_to_3_2_states += 1
                        if apsc == "On":
                            assert r["effective_still_image_size"] == STILL_IMAGE_SIZE_M_G121
                            apsc_l_to_m_stepdown_states += 1
                        assert r["arw_retains_full_3_2_pixels"] is True

    return {
        "states_checked": states,
        "dci4k_all_intra_states": dci4k_all_intra_states,
        "longgop_uhd_states": longgop_uhd_states,
        "aspect_reset_to_3_2_states": aspect_reset_to_3_2_states,
        "apsc_l_to_m_stepdown_states": apsc_l_to_m_stepdown_states,
        "all_invariants_hold": states == 384,
    }


def verify_dci4k_and_aspect_ratio_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE288,
    body_model_id: int = FX3_MODEL_ID_PHASE288,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE288,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE288,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE288,
    requested_file_format: str = FILE_FORMAT_XAVC_SI_DCI_4K_G121,
    rec_frame_rate: str = "23.98p",
    requested_movie_dimensions: Optional[Tuple[int, int]] = None,
    card_tier: str = CARD_TIER_CFEXPRESS_VPG200_G121,
    sq_fps: int = 24,
    switched_24_00p_boundary: bool = False,
    reboot_completed_for_24_00p: bool = False,
    playback_24_00p_quarantine_enforced: bool = True,
    hdmi_raw_output_enabled: bool = False,
    hdmi_raw_dimensions: Optional[Tuple[int, int]] = None,
    hdmi_raw_frame_rate: str = "23.98p",
    log_shooting: str = LOG_SHOOTING_FLEXIBLE_ISO_G121,
    requested_still_aspect_ratio: str = STILL_ASPECT_RATIO_DEFAULT_G121,
    requested_still_image_size: str = STILL_IMAGE_SIZE_L_G121,
    apsc_s35_shooting: str = "Off",
    reset_action: str = RESET_ACTION_NONE_PHASE288,
    claimed_dci4k_supports_120fps: bool = False,
    claimed_24_00p_no_reboot_or_shared_playback: bool = False,
    claimed_longgop_supports_dci4k: bool = False,
    claimed_longgop_supports_24_00p: bool = False,
    claimed_xavc_si_uhd_supports_dci4k: bool = False,
    claimed_xavc_hs_8k_active_on_fx3: bool = False,
    claimed_hdmi_raw_allowed_with_log_off: bool = False,
    claimed_arw_crops_raw_sensor_pixels: bool = False,
    claimed_apsc_s35_keeps_l_size: bool = False,
    claimed_fx6_has_still_aspect_ratio: bool = False,
    claimed_camera_reset_preserves_still_aspect: bool = False,
) -> Dci4kUhdLongGopHdmiRawAspectGuardResult:
    """Verify Gate `G121` across internal `XAVC S-I DCI 4K` (`4096x2160` + `24.00p`
    reboot/HFR ceiling), Long-GOP `UHD 3840x2160` boundary, `4264x2408` Type-A
    HDMI RAW (`[Log Shooting] != Off`), and Still `[Aspect Ratio]` (`3:2/4:3/16:9/1:1`).
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME_PHASE288
        or not _is_real_int(body_model_id)
        or body_model_id != FX3_MODEL_ID_PHASE288
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE288
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G121_TELEMETRY_INVALID)
        errors.append("Invalid FX3 hardware model/firmware/help-guide identity.")

    norm_shoot = _norm_shoot_mode_phase288(shoot_mode)
    norm_fmt = _norm_file_format_g121(requested_file_format)
    norm_rate = _norm_rec_frame_rate_g121(rec_frame_rate)
    norm_card = _norm_card_tier_g121(card_tier)
    norm_log = _norm_log_shooting_g121(log_shooting)
    norm_hdmi_rate = _norm_rec_frame_rate_g121(hdmi_raw_frame_rate)
    norm_aspect = _norm_still_aspect_ratio_g121(requested_still_aspect_ratio)
    norm_size = _norm_still_image_size_g121(requested_still_image_size)
    norm_apsc = _norm_on_off_phase288(apsc_s35_shooting)
    norm_reset = _norm_reset_action_phase288(reset_action)

    if (
        norm_shoot is None
        or norm_fmt is None
        or norm_rate is None
        or norm_card is None
        or norm_log is None
        or norm_hdmi_rate is None
        or norm_aspect is None
        or norm_size is None
        or norm_apsc is None
        or norm_reset is None
        or not _is_real_int(sq_fps)
        or sq_fps < 1
        or sq_fps > 240
    ):
        _add_code(codes, STATUS_BLOCKED_G121_TELEMETRY_INVALID)
        errors.append("Invalid G121 telemetry enumeration or S&Q fps value.")

    eff = resolve_fx3_dci4k_hdmi_raw_and_aspect_ratio_state(
        shoot_mode=norm_shoot or SHOOT_MODE_MOVIE_PHASE288,
        requested_file_format=norm_fmt or FILE_FORMAT_XAVC_SI_DCI_4K_G121,
        rec_frame_rate=norm_rate or "23.98p",
        card_tier=norm_card or CARD_TIER_CFEXPRESS_VPG200_G121,
        sq_fps=sq_fps if _is_real_int(sq_fps) else 24,
        switched_24_00p_boundary=switched_24_00p_boundary,
        reboot_completed_for_24_00p=reboot_completed_for_24_00p,
        playback_24_00p_quarantine_enforced=playback_24_00p_quarantine_enforced,
        hdmi_raw_output_enabled=hdmi_raw_output_enabled,
        hdmi_raw_frame_rate=norm_hdmi_rate or "23.98p",
        log_shooting=norm_log or LOG_SHOOTING_FLEXIBLE_ISO_G121,
        requested_still_aspect_ratio=norm_aspect or STILL_ASPECT_RATIO_DEFAULT_G121,
        requested_still_image_size=norm_size or STILL_IMAGE_SIZE_L_G121,
        apsc_s35_shooting=norm_apsc or "Off",
        reset_action=norm_reset or RESET_ACTION_NONE_PHASE288,
    )

    if norm_fmt == FILE_FORMAT_XAVC_SI_DCI_4K_G121 and norm_rate is not None:
        if norm_rate not in DCI_4K_ALLOWED_REC_RATES_G121:
            _add_code(codes, STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION)
            errors.append(
                f"XAVC S-I DCI 4K forbids recording rate {norm_rate!r} (no 100p/120p)."
            )
        if _is_real_int(sq_fps) and (
            sq_fps not in DCI_4K_ALLOWED_SQ_FPS_G121 or sq_fps in DCI_4K_FORBIDDEN_HFR_FPS_G121
        ):
            _add_code(codes, STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION)
            errors.append(
                f"XAVC S-I DCI 4K S&Q supports only 1..48 fps ({DCI_4K_ALLOWED_SQ_FPS_G121}); got {sq_fps} fps."
            )
        if (
            DCI_4K_BITRATES_MBPS_G121.get(norm_rate, 0) >= 600
            and norm_card not in DCI4K_600M_ALLOWED_CARD_TIERS_G121
        ):
            _add_code(codes, STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION)
            errors.append(
                f"XAVC S-I DCI 4K 59.94p (600M) requires CFexpress VPG200+ or SDXC V90+; got {norm_card}."
            )
        if requested_movie_dimensions is not None and requested_movie_dimensions != DCI_4K_DIMENSIONS_G121:
            _add_code(codes, STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION)
            errors.append(
                f"XAVC S-I DCI 4K requires exact dimensions 4096x2160; got {requested_movie_dimensions}."
            )

    if switched_24_00p_boundary and not reboot_completed_for_24_00p:
        _add_code(codes, STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION)
        errors.append(
            "Switching into/out of 24.00p (0x75ce) requires a mandatory camera reboot (_g.uxc 0x639b)."
        )
    if not playback_24_00p_quarantine_enforced:
        _add_code(codes, STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION)
        errors.append(
            "24.00p playback quarantine (_g.uxc 0x63b6) must remain enforced."
        )
    if claimed_dci4k_supports_120fps or claimed_24_00p_no_reboot_or_shared_playback:
        _add_code(codes, STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION)
        errors.append(
            "Spoofed DCI 4K 100/120fps HFR or reboot-free/shared-playback 24.00p rejected."
        )

    if norm_fmt in UHD_ONLY_4K_FILE_FORMATS_G121:
        if requested_movie_dimensions == DCI_4K_DIMENSIONS_G121 or (
            requested_movie_dimensions is not None
            and requested_movie_dimensions != UHD_4K_DIMENSIONS_G121
        ):
            _add_code(codes, STATUS_BLOCKED_G121_LONGGOP_DCI4K_OR_24P_SPOOF_VIOLATION)
            errors.append(
                f"{norm_fmt} is strictly 3840x2160 UHD; got {requested_movie_dimensions}."
            )
        if norm_rate == "24.00p":
            _add_code(codes, STATUS_BLOCKED_G121_LONGGOP_DCI4K_OR_24P_SPOOF_VIOLATION)
            errors.append(f"{norm_fmt} does not support 24.00p.")
    if (
        claimed_longgop_supports_dci4k
        or claimed_longgop_supports_24_00p
        or claimed_xavc_si_uhd_supports_dci4k
        or claimed_xavc_hs_8k_active_on_fx3
    ):
        _add_code(codes, STATUS_BLOCKED_G121_LONGGOP_DCI4K_OR_24P_SPOOF_VIOLATION)
        errors.append(
            "Long-GOP / XAVC S-I 4K DCI-4K spoof, 24.00p spoof, or dormant 8K claim rejected."
        )

    if hdmi_raw_output_enabled:
        if norm_log == LOG_SHOOTING_OFF_G121:
            _add_code(codes, STATUS_BLOCKED_G121_HDMI_RAW_LOG_OR_STILL_ASPECT_SPOOF_VIOLATION)
            errors.append(
                "Type-A HDMI RAW output (4264x2408) requires [Log Shooting] != Off."
            )
        if norm_hdmi_rate not in HDMI_RAW_ALLOWED_RATES_G121:
            _add_code(codes, STATUS_BLOCKED_G121_HDMI_RAW_LOG_OR_STILL_ASPECT_SPOOF_VIOLATION)
            errors.append(
                f"HDMI RAW output forbids frame rate {norm_hdmi_rate!r} (only 23.98p..59.94p)."
            )
        if hdmi_raw_dimensions is not None and hdmi_raw_dimensions != HDMI_RAW_DIMENSIONS_G121:
            _add_code(codes, STATUS_BLOCKED_G121_HDMI_RAW_LOG_OR_STILL_ASPECT_SPOOF_VIOLATION)
            errors.append(
                f"FX3 Type-A HDMI RAW outputs exact 4264x2408; got {hdmi_raw_dimensions}."
            )
    if (
        claimed_hdmi_raw_allowed_with_log_off
        or claimed_arw_crops_raw_sensor_pixels
        or claimed_apsc_s35_keeps_l_size
        or claimed_fx6_has_still_aspect_ratio
        or claimed_camera_reset_preserves_still_aspect
    ):
        _add_code(codes, STATUS_BLOCKED_G121_HDMI_RAW_LOG_OR_STILL_ASPECT_SPOOF_VIOLATION)
        errors.append(
            "HDMI RAW Log=Off spoof, .ARW sensor-pixel crop spoof, APS-C L-size spoof, FX6 Still Aspect spoof, or Camera Reset Aspect persistence spoof rejected."
        )

    matrix = compute_dci4k_hdmi_raw_and_aspect_ratio_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G121 if valid else codes[0]

    return Dci4kUhdLongGopHdmiRawAspectGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE288,
        reset_action=norm_reset or "INVALID",
        file_format_menu_path=FILE_FORMAT_MENU_PATH_G121,
        movie_settings_menu_path=MOVIE_SETTINGS_MENU_PATH_G121,
        raw_output_menu_path=RAW_OUTPUT_MENU_PATH_G121,
        aspect_ratio_menu_path=ASPECT_RATIO_MENU_PATH_G121,
        shoot_mode=eff["shoot_mode"],
        requested_file_format=norm_fmt or str(requested_file_format),
        effective_file_format=eff["effective_file_format"],
        movie_dimensions=eff["movie_dimensions"],
        movie_aspect_label=eff["movie_aspect_label"],
        is_dci_4k_all_intra=eff["is_dci_4k_all_intra"],
        is_longgop_uhd_only=eff["is_longgop_uhd_only"],
        rec_frame_rate=eff["rec_frame_rate"],
        bitrate_mbps=eff["bitrate_mbps"],
        card_tier=eff["card_tier"],
        sq_fps=eff["sq_fps"],
        switched_24_00p_boundary=eff["switched_24_00p_boundary"],
        reboot_completed_for_24_00p=eff["reboot_completed_for_24_00p"],
        playback_24_00p_quarantine_enforced=eff["playback_24_00p_quarantine_enforced"],
        hdmi_raw_output_enabled=eff["hdmi_raw_output_enabled"],
        hdmi_raw_dimensions=eff["hdmi_raw_dimensions"],
        hdmi_raw_frame_rate=eff["hdmi_raw_frame_rate"],
        log_shooting=eff["log_shooting"],
        requested_still_aspect_ratio=norm_aspect or str(requested_still_aspect_ratio),
        effective_still_aspect_ratio=eff["effective_still_aspect_ratio"],
        requested_still_image_size=norm_size or str(requested_still_image_size),
        effective_still_image_size=eff["effective_still_image_size"],
        still_aspect_megapixel_label=eff["still_aspect_megapixel_label"],
        still_jpeg_heif_dimensions=eff["still_jpeg_heif_dimensions"],
        apsc_s35_shooting=eff["apsc_s35_shooting"],
        arw_retains_full_3_2_pixels=eff["arw_retains_full_3_2_pixels"],
        still_aspect_reset_on_cam_reset=eff["still_aspect_reset_on_cam_reset"],
        fx6_still_aspect_supported=False,
        fx6_longgop_has_dci4k=False,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g121_dci4k_and_aspect_ratio_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dci4k_aspect_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase288DonorAuditResult] = None,
) -> Tuple[GateVerdict, G121Dci4kAspectRatioGuardResult]:
    """Evaluate Gate `G121` including `< 0.20s` `O_RDONLY` Wave-51 donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase288_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_dci4k_and_aspect_ratio_guard(**(dict(dci4k_aspect_kwargs or {})))
    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G121.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G121 if valid else codes[0]

    res = G121Dci4kAspectRatioGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        dci4k_aspect_ratio_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, fmt={guard.effective_file_format}"
        f"({guard.movie_dimensions[0]}x{guard.movie_dimensions[1]}@{guard.rec_frame_rate},"
        f"sq={guard.sq_fps}fps,24p_quar={guard.playback_24_00p_quarantine_enforced}), "
        f"hdmi_raw=4264x2408(en={guard.hdmi_raw_output_enabled},log={guard.log_shooting}), "
        f"still_aspect={guard.effective_still_aspect_ratio}({guard.effective_still_image_size}="
        f"{guard.still_aspect_megapixel_label},arw_full_3_2={guard.arw_retains_full_3_2_pixels}), "
        f"fx6_still_aspect={guard.fx6_still_aspect_supported}"
    )
    verdict = GateVerdict(
        gate_id=G121_GATE_ID,
        gate_code=G121_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G122: [Reg. Custom Shoot Set] (11 Checkboxes, Still P/A/S/M) vs
#    [Camera Set. Memory] (1..3 + M1..M4 + Card Path Firewall), & Playback
#    [Photo Capture] (DCI 4K Lockout + Slot-1 Firewall) / [Enlarge Image]
# ---------------------------------------------------------------------------


def resolve_fx3_custom_hold_camset_photo_and_enlarge_state(
    *,
    shoot_mode: str = SHOOT_MODE_M_PHASE288,
    recall_custom_hold_requested: bool = False,
    recall_custom_hold_slot: str = "Recall Custom hold 1",
    recalled_hold_params: Sequence[str] = ("aperture", "shutter_speed"),
    camset_memory_slot: str = "1",
    camset_media_slot: str = "Slot 1",
    use_cfexpress_media: bool = False,
    photo_capture_requested: bool = False,
    playback_slot: str = "Slot 2",
    playback_source_file_format: str = FILE_FORMAT_XAVC_S_4K_G121,
    playback_source_resolution_tier: str = "4K",
    requested_photo_capture_file_type: str = PHOTO_CAPTURE_FILE_TYPE_DEFAULT_G122,
    enlarge_image_requested: bool = False,
    playback_media_kind: str = "Still",
    requested_enlarge_initial_mag: str = ENLARGE_INITIAL_MAG_DEFAULT_G122,
    requested_enlarge_initial_position: str = ENLARGE_INITIAL_POS_DEFAULT_G122,
    reset_action: str = RESET_ACTION_NONE_PHASE288,
) -> Dict[str, Any]:
    """Resolve effective Wave-51 Gate `G122` FX3 Ver. 7.02 hold/camset/photo/enlarge state."""
    eff_reset = _norm_reset_action_phase288(reset_action) or RESET_ACTION_NONE_PHASE288
    eff_shoot = _norm_shoot_mode_phase288(shoot_mode) or SHOOT_MODE_M_PHASE288
    eff_hold_slot = (
        _norm_recall_custom_hold_slot_g122(recall_custom_hold_slot)
        or "Recall Custom hold 1"
    )
    eff_hold_params = tuple(recalled_hold_params)
    hlg_forced_off = bool(
        recall_custom_hold_requested
        and any(p in HLG_LOCKOUT_RECALL_PARAMS_G122 for p in eff_hold_params)
    )

    eff_media_slot = _norm_media_slot_g122(camset_media_slot) or "Slot 1"
    if eff_reset in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE288,
        RESET_ACTION_INITIALIZE_PHASE288,
    ):
        eff_media_slot = "Slot 1"

    eff_photo_type = (
        _norm_photo_capture_file_type_g122(requested_photo_capture_file_type)
        or PHOTO_CAPTURE_FILE_TYPE_DEFAULT_G122
    )
    eff_mag = (
        _norm_enlarge_initial_mag_g122(requested_enlarge_initial_mag)
        or ENLARGE_INITIAL_MAG_DEFAULT_G122
    )
    eff_pos = (
        _norm_enlarge_initial_pos_g122(requested_enlarge_initial_position)
        or ENLARGE_INITIAL_POS_DEFAULT_G122
    )

    if eff_reset == RESET_ACTION_INITIALIZE_PHASE288:
        eff_photo_type = PHOTO_CAPTURE_FILE_TYPE_DEFAULT_G122
        eff_mag = ENLARGE_INITIAL_MAG_DEFAULT_G122
        eff_pos = ENLARGE_INITIAL_POS_DEFAULT_G122

    # Playback settings, [Reg. Custom Shoot Set], and [Camera Set. Memory] 1..3
    # all survive [Camera Settings Reset]!
    survived_cam_reset = eff_reset != RESET_ACTION_INITIALIZE_PHASE288

    res_tier = "HD" if str(playback_source_resolution_tier).strip().upper() == "HD" else "4K"
    out_mp = PHOTO_CAPTURE_4K_MP_LABEL_G122 if res_tier == "4K" else PHOTO_CAPTURE_HD_MP_LABEL_G122
    out_dims = (
        PHOTO_CAPTURE_4K_DIMENSIONS_G122
        if res_tier == "4K"
        else PHOTO_CAPTURE_HD_DIMENSIONS_G122
    )

    sample_prefix = "" if use_cfexpress_media else "/PRIVATE"
    return {
        "shoot_mode": eff_shoot,
        "recall_custom_hold_requested": bool(recall_custom_hold_requested),
        "recall_custom_hold_slot": eff_hold_slot,
        "recalled_hold_params": eff_hold_params,
        "hlg_still_image_forced_off": hlg_forced_off,
        "recall_custom_hold_survived_cam_reset": survived_cam_reset,
        "camset_memory_slot": _norm_camset_memory_slot_g122(camset_memory_slot) or "1",
        "camset_media_slot": eff_media_slot,
        "concrete_sample_campr_path": f"1:{sample_prefix}/SONY/SETTING/FX3/CAMPR01A.DAT",
        "concrete_sample_camset_path": f"1:{sample_prefix}/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT",
        "body_memory_banks_survived_cam_reset": survived_cam_reset,
        "photo_capture_requested": bool(photo_capture_requested),
        "playback_slot": _norm_media_slot_g122(playback_slot) or "Slot 2",
        "playback_source_file_format": playback_source_file_format,
        "playback_source_resolution_tier": res_tier,
        "effective_photo_capture_file_type": eff_photo_type,
        "photo_capture_output_mp_label": out_mp,
        "photo_capture_output_dimensions": out_dims,
        "enlarge_image_requested": bool(enlarge_image_requested),
        "playback_media_kind": playback_media_kind,
        "effective_enlarge_initial_mag": eff_mag,
        "effective_enlarge_initial_position": eff_pos,
        "enlarge_settings_survived_cam_reset": survived_cam_reset,
    }


def compute_custom_hold_camset_photo_and_enlarge_matrix() -> Dict[str, Any]:
    """Deterministic `384`-state cross-product across `(4 shoot_modes x 4 hold_params x
    3 camset_slots x 2 playback_slots x 2 enlarges x 2 resets)` verifying `G122` invariants.
    """
    states = 0
    hlg_forced_off_states = 0
    cam_reset_survived_states = 0
    init_reset_states = 0
    slot1_protected_states = 0

    hold_cases = (
        ("aperture",),
        ("iso_sensitivity",),
        ("drive_mode",),
        ("focus_area", "af_on"),
    )
    resets = (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE288,
        RESET_ACTION_INITIALIZE_PHASE288,
    )

    for sm in (
        SHOOT_MODE_M_PHASE288,
        SHOOT_MODE_P_PHASE288,
        SHOOT_MODE_MOVIE_PHASE288,
        SHOOT_MODE_MR_PHASE288,
    ):
        for params in hold_cases:
            for cslot in ("1", "M1", "M4"):
                for pslot in ("Slot 1", "Slot 2"):
                    for mag in ALLOWED_ENLARGE_INITIAL_MAG_G122:
                        for r_act in resets:
                            states += 1
                            r = resolve_fx3_custom_hold_camset_photo_and_enlarge_state(
                                shoot_mode=sm,
                                recall_custom_hold_requested=True,
                                recalled_hold_params=params,
                                camset_memory_slot=cslot,
                                camset_media_slot="Slot 2",
                                playback_slot=pslot,
                                requested_enlarge_initial_mag=mag,
                                requested_enlarge_initial_position=ENLARGE_INITIAL_POS_CENTER_G122,
                                reset_action=r_act,
                            )
                            if r["hlg_still_image_forced_off"]:
                                hlg_forced_off_states += 1
                            if r_act == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE288:
                                assert r["camset_media_slot"] == "Slot 1"
                                assert r["effective_enlarge_initial_mag"] == mag
                                assert (
                                    r["effective_enlarge_initial_position"]
                                    == ENLARGE_INITIAL_POS_CENTER_G122
                                )
                                cam_reset_survived_states += 1
                            else:
                                assert (
                                    r["effective_enlarge_initial_mag"]
                                    == ENLARGE_INITIAL_MAG_DEFAULT_G122
                                )
                                assert (
                                    r["effective_enlarge_initial_position"]
                                    == ENLARGE_INITIAL_POS_DEFAULT_G122
                                )
                                init_reset_states += 1
                            if pslot == "Slot 1":
                                slot1_protected_states += 1

    return {
        "states_checked": states,
        "hlg_forced_off_states": hlg_forced_off_states,
        "cam_reset_survived_states": cam_reset_survived_states,
        "init_reset_states": init_reset_states,
        "slot1_protected_states": slot1_protected_states,
        "all_invariants_hold": states == 384,
    }


def verify_custom_hold_camset_photo_capture_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE288,
    body_model_id: int = FX3_MODEL_ID_PHASE288,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE288,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE288,
    shoot_mode: str = SHOOT_MODE_M_PHASE288,
    recall_custom_hold_requested: bool = False,
    recall_custom_hold_slot: str = "Recall Custom hold 1",
    recalled_hold_params: Sequence[str] = ("aperture", "shutter_speed"),
    hlg_still_image_on: bool = False,
    camset_memory_slot: str = "1",
    camset_media_slot: str = "Slot 1",
    use_cfexpress_media: bool = False,
    submitted_card_path: str = "%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT",
    save_load_settings_requested: bool = False,
    save_load_target_slot: str = "Slot 1",
    format_slot_1_requested: bool = False,
    slot_1_contains_camset_or_m1_m4_vault: bool = True,
    photo_capture_requested: bool = False,
    playback_slot: str = "Slot 2",
    playback_source_file_format: str = FILE_FORMAT_XAVC_S_4K_G121,
    playback_source_resolution_tier: str = "4K",
    requested_photo_capture_file_type: str = PHOTO_CAPTURE_FILE_TYPE_DEFAULT_G122,
    enlarge_image_requested: bool = False,
    playback_media_kind: str = "Still",
    requested_enlarge_initial_mag: str = ENLARGE_INITIAL_MAG_DEFAULT_G122,
    requested_enlarge_initial_position: str = ENLARGE_INITIAL_POS_DEFAULT_G122,
    reset_action: str = RESET_ACTION_NONE_PHASE288,
    claimed_recall_custom_hold_includes_self_timer: bool = False,
    claimed_camera_reset_wipes_custom_hold_or_camset_1_3: bool = False,
    claimed_format_preserves_camset_or_m1_m4: bool = False,
    claimed_photo_capture_supported_on_dci4k: bool = False,
    claimed_photo_capture_read_only: bool = False,
    claimed_enlarge_image_supported_on_movie: bool = False,
    claimed_enlarge_initial_mag_init_alias: bool = False,
    claimed_camera_reset_wipes_enlarge_or_photo_capture: bool = False,
    claimed_fx6_has_photo_capture_or_playback_enlarge: bool = False,
) -> CustomHoldCamsetPhotoEnlargeGuardResult:
    """Verify Gate `G122` across `[Reg. Custom Shoot Set]` (`11` hold keys, Still
    `P/A/S/M` only, `HLG` off on ISO/DRO-BKT), `[Camera Set. Memory]` (`1..3` +
    `M1..M4` `/SONY/SETTING/%s/` path vs FX6 `s/SONY/PRO/CAMERA/` spoof + `[Format]`
    protection), Playback `[Photo Capture]` (`DCI 4K` lockout `_g 0x60ce` + `Slot-1`
    vault write firewall), and Still-only `[Enlarge Image]` / `[Enlarge Initial Mag./Position]`.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME_PHASE288
        or not _is_real_int(body_model_id)
        or body_model_id != FX3_MODEL_ID_PHASE288
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE288
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
        or not isinstance(submitted_card_path, str)
        or not submitted_card_path.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G122_TELEMETRY_INVALID)
        errors.append("Invalid FX3 hardware identity or empty card path.")

    norm_shoot = _norm_shoot_mode_phase288(shoot_mode)
    norm_hold_slot = _norm_recall_custom_hold_slot_g122(recall_custom_hold_slot)
    norm_camset_slot = _norm_camset_memory_slot_g122(camset_memory_slot)
    norm_camset_media = _norm_media_slot_g122(camset_media_slot)
    norm_save_slot = _norm_media_slot_g122(save_load_target_slot)
    norm_playback_slot = _norm_media_slot_g122(playback_slot)
    norm_photo_type = _norm_photo_capture_file_type_g122(
        requested_photo_capture_file_type
    )
    norm_mag = _norm_enlarge_initial_mag_g122(requested_enlarge_initial_mag)
    norm_pos = _norm_enlarge_initial_pos_g122(requested_enlarge_initial_position)
    norm_reset = _norm_reset_action_phase288(reset_action)

    pb_kind_norm = (
        playback_media_kind.strip().title()
        if isinstance(playback_media_kind, str)
        and playback_media_kind.strip().title() in ("Still", "Movie")
        else None
    )
    res_tier_norm = (
        playback_source_resolution_tier.strip().upper()
        if isinstance(playback_source_resolution_tier, str)
        and playback_source_resolution_tier.strip().upper() in ("4K", "HD")
        else None
    )

    if (
        norm_shoot is None
        or norm_hold_slot is None
        or norm_camset_slot is None
        or norm_camset_media is None
        or norm_save_slot is None
        or norm_playback_slot is None
        or norm_photo_type is None
        or norm_mag is None
        or norm_pos is None
        or norm_reset is None
        or pb_kind_norm is None
        or res_tier_norm is None
    ):
        _add_code(codes, STATUS_BLOCKED_G122_TELEMETRY_INVALID)
        errors.append("Invalid G122 enumeration value.")

    if isinstance(recalled_hold_params, (str, bytes)):
        _add_code(codes, STATUS_BLOCKED_G122_TELEMETRY_INVALID)
        errors.append("recalled_hold_params must be a sequence of parameter keys.")
        hold_params_seq: Tuple[str, ...] = ()
    else:
        hold_params_seq = tuple(str(x) for x in recalled_hold_params)
        unknown_hold = [
            p for p in hold_params_seq if p not in FX3_EXACT_11_CUSTOM_HOLD_CHECKBOX_KEYS_G122
        ]
        if unknown_hold:
            _add_code(codes, STATUS_BLOCKED_G122_RECALL_CUSTOM_HOLD_MODE_OR_HLG_VIOLATION)
            errors.append(
                f"Unsupported [Reg. Custom Shoot Set] parameter keys (only 11 keys valid, no self-timer): {unknown_hold}."
            )

    eff = resolve_fx3_custom_hold_camset_photo_and_enlarge_state(
        shoot_mode=norm_shoot or SHOOT_MODE_M_PHASE288,
        recall_custom_hold_requested=recall_custom_hold_requested,
        recall_custom_hold_slot=norm_hold_slot or "Recall Custom hold 1",
        recalled_hold_params=hold_params_seq or ("aperture",),
        camset_memory_slot=norm_camset_slot or "1",
        camset_media_slot=norm_camset_media or "Slot 1",
        use_cfexpress_media=use_cfexpress_media,
        photo_capture_requested=photo_capture_requested,
        playback_slot=norm_playback_slot or "Slot 2",
        playback_source_file_format=playback_source_file_format,
        playback_source_resolution_tier=res_tier_norm or "4K",
        requested_photo_capture_file_type=(
            norm_photo_type or PHOTO_CAPTURE_FILE_TYPE_DEFAULT_G122
        ),
        enlarge_image_requested=enlarge_image_requested,
        playback_media_kind=pb_kind_norm or "Still",
        requested_enlarge_initial_mag=norm_mag or ENLARGE_INITIAL_MAG_DEFAULT_G122,
        requested_enlarge_initial_position=(
            norm_pos or ENLARGE_INITIAL_POS_DEFAULT_G122
        ),
        reset_action=norm_reset or RESET_ACTION_NONE_PHASE288,
    )

    if recall_custom_hold_requested:
        if norm_shoot not in PASM_SHOOT_MODES_PHASE288:
            _add_code(codes, STATUS_BLOCKED_G122_RECALL_CUSTOM_HOLD_MODE_OR_HLG_VIOLATION)
            errors.append(
                f"[Reg. Custom Shoot Set] (0x7631) is strictly Still P/A/S/M only; forbidden in {norm_shoot}."
            )
        if hlg_still_image_on and any(
            p in HLG_LOCKOUT_RECALL_PARAMS_G122 for p in hold_params_seq
        ):
            _add_code(codes, STATUS_BLOCKED_G122_RECALL_CUSTOM_HOLD_MODE_OR_HLG_VIOLATION)
            errors.append(
                "Recalling ISO or Drive/DRO Bracket via [Reg. Custom Shoot Set] forces [HLG Still Image] = Off."
            )
    if (
        claimed_recall_custom_hold_includes_self_timer
        or claimed_camera_reset_wipes_custom_hold_or_camset_1_3
    ):
        _add_code(codes, STATUS_BLOCKED_G122_RECALL_CUSTOM_HOLD_MODE_OR_HLG_VIOLATION)
        errors.append(
            "Self-timer in [Reg. Custom Shoot Set] or Camera Reset wipe spoof rejected."
        )

    card_path_str = submitted_card_path if isinstance(submitted_card_path, str) else ""
    fx6_spoof_detected = any(
        marker in card_path_str for marker in FX6_FORBIDDEN_CARD_PATH_MARKERS_G122
    )
    fx3_path_valid = (
        card_path_str in (FX3_CAMPR_PATH_TEMPLATE_G122, FX3_CAMSET_PATH_TEMPLATE_G122)
        or (
            "/SONY/SETTING/" in card_path_str
            and ("CAMPR" in card_path_str or "CAMSET" in card_path_str)
        )
    )
    if fx6_spoof_detected or not fx3_path_valid:
        _add_code(codes, STATUS_BLOCKED_G122_FX3_CAMSET_CARD_PATH_SPOOF_VIOLATION)
        errors.append(
            f"Invalid FX3 card setting path {card_path_str!r}; FX3 uses /SONY/SETTING/ (never FX6 PRIVATE/SONY/PRO/CAMERA)."
        )
    if save_load_settings_requested:
        if norm_shoot == SHOOT_MODE_MR_PHASE288:
            _add_code(codes, STATUS_BLOCKED_G122_FX3_CAMSET_CARD_PATH_SPOOF_VIOLATION)
            errors.append("[Save/Load Settings] is disabled while in MR mode.")
        if norm_save_slot != "Slot 1":
            _add_code(codes, STATUS_BLOCKED_G122_FX3_CAMSET_CARD_PATH_SPOOF_VIOLATION)
            errors.append(
                f"[Save/Load Settings] CAMSET/*.DAT is strictly Slot 1 only; got {norm_save_slot}."
            )
    if (format_slot_1_requested and slot_1_contains_camset_or_m1_m4_vault) or claimed_format_preserves_camset_or_m1_m4:
        _add_code(codes, STATUS_BLOCKED_G122_FX3_CAMSET_CARD_PATH_SPOOF_VIOLATION)
        errors.append(
            "[Format] on Slot 1 permanently erases M1..M4 and CAMSET recovery files — blocked by Slot-1 vault firewall."
        )

    pb_fmt_norm = _norm_file_format_g121(playback_source_file_format)
    pb_is_dci4k = pb_fmt_norm == FILE_FORMAT_XAVC_SI_DCI_4K_G121
    photo_slot1_hazard = photo_capture_requested and (norm_playback_slot == "Slot 1")
    photo_dci4k_hazard = photo_capture_requested and pb_is_dci4k
    if (
        photo_slot1_hazard
        or photo_dci4k_hazard
        or claimed_photo_capture_supported_on_dci4k
        or claimed_photo_capture_read_only
    ):
        _add_code(codes, STATUS_BLOCKED_G122_PHOTO_CAPTURE_DCI4K_OR_SLOT1_WRITE_VIOLATION)
        errors.append(
            "Playback [Photo Capture] blocked: hard-blocked on XAVC S-I DCI 4K (_g 0x60ce) and hard-blocked on Slot 1 recovery vault (mutates DCIM + MDB/AVF_INFO)."
        )

    if enlarge_image_requested and pb_kind_norm != "Still":
        _add_code(codes, STATUS_BLOCKED_G122_ENLARGE_IMAGE_OR_RESET_PERSISTENCE_VIOLATION)
        errors.append(
            "Playback [Enlarge Image] (.uxc 0xe8cb) is strictly Still-image only (disabled on movies)."
        )
    if (
        claimed_enlarge_image_supported_on_movie
        or claimed_enlarge_initial_mag_init_alias
        or claimed_camera_reset_wipes_enlarge_or_photo_capture
        or claimed_fx6_has_photo_capture_or_playback_enlarge
    ):
        _add_code(codes, STATUS_BLOCKED_G122_ENLARGE_IMAGE_OR_RESET_PERSISTENCE_VIOLATION)
        errors.append(
            "Movie Enlarge Image spoof, bogus 'Init.' magnification label, Playback Camera Reset wipe spoof, or FX6 Photo Capture/Playback Enlarge spoof rejected."
        )

    matrix = compute_custom_hold_camset_photo_and_enlarge_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G122 if valid else codes[0]

    return CustomHoldCamsetPhotoEnlargeGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE288,
        reset_action=norm_reset or "INVALID",
        reg_custom_shoot_set_menu_path=REG_CUSTOM_SHOOT_SET_MENU_PATH_G122,
        camera_set_memory_menu_path=CAMERA_SET_MEMORY_MENU_PATH_G122,
        save_load_settings_menu_path=SAVE_LOAD_SETTINGS_MENU_PATH_G122,
        photo_capture_menu_path=PHOTO_CAPTURE_MENU_PATH_G122,
        enlarge_image_menu_path=ENLARGE_IMAGE_MENU_PATH_G122,
        shoot_mode=eff["shoot_mode"],
        recall_custom_hold_requested=eff["recall_custom_hold_requested"],
        recall_custom_hold_slot=eff["recall_custom_hold_slot"],
        recalled_hold_params=eff["recalled_hold_params"],
        exact_11_custom_hold_keys=FX3_EXACT_11_CUSTOM_HOLD_CHECKBOX_KEYS_G122,
        hlg_still_image_forced_off=eff["hlg_still_image_forced_off"],
        recall_custom_hold_survived_cam_reset=eff[
            "recall_custom_hold_survived_cam_reset"
        ],
        camset_memory_slot=eff["camset_memory_slot"],
        camset_media_slot=eff["camset_media_slot"],
        effective_campr_path_template=FX3_CAMPR_PATH_TEMPLATE_G122,
        effective_camset_path_template=FX3_CAMSET_PATH_TEMPLATE_G122,
        submitted_card_path=card_path_str,
        fx6_pro_camera_path_rejected=True,
        format_slot_1_protected=True,
        body_memory_banks_survived_cam_reset=eff[
            "body_memory_banks_survived_cam_reset"
        ],
        photo_capture_requested=eff["photo_capture_requested"],
        playback_slot=eff["playback_slot"],
        playback_source_file_format=eff["playback_source_file_format"],
        playback_source_resolution_tier=eff["playback_source_resolution_tier"],
        requested_photo_capture_file_type=norm_photo_type
        or str(requested_photo_capture_file_type),
        effective_photo_capture_file_type=eff["effective_photo_capture_file_type"],
        photo_capture_output_mp_label=eff["photo_capture_output_mp_label"],
        photo_capture_output_dimensions=eff["photo_capture_output_dimensions"],
        photo_capture_dci4k_locked=True,
        photo_capture_slot1_write_blocked=True,
        enlarge_image_requested=eff["enlarge_image_requested"],
        playback_media_kind=eff["playback_media_kind"],
        requested_enlarge_initial_mag=norm_mag or str(requested_enlarge_initial_mag),
        effective_enlarge_initial_mag=eff["effective_enlarge_initial_mag"],
        requested_enlarge_initial_position=norm_pos
        or str(requested_enlarge_initial_position),
        effective_enlarge_initial_position=eff["effective_enlarge_initial_position"],
        enlarge_settings_survived_cam_reset=eff[
            "enlarge_settings_survived_cam_reset"
        ],
        fx6_photo_capture_supported=False,
        fx6_playback_enlarge_supported=False,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g122_custom_hold_camset_photo_capture_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    custom_hold_camset_photo_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase288DonorAuditResult] = None,
) -> Tuple[GateVerdict, G122CustomHoldCamsetPhotoEnlargeGuardResult]:
    """Evaluate Gate `G122` including `< 0.20s` `O_RDONLY` Wave-51 donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase288_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_custom_hold_camset_photo_capture_guard(
        **(dict(custom_hold_camset_photo_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G122.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G122 if valid else codes[0]

    res = G122CustomHoldCamsetPhotoEnlargeGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        custom_hold_camset_photo_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, hold_keys={len(guard.exact_11_custom_hold_keys)}"
        f"(pasm_only=True), camset_path=/SONY/SETTING/(fx6_pro_rej={guard.fx6_pro_camera_path_rejected},"
        f"slot1_fmt_prot={guard.format_slot_1_protected}), "
        f"photo_cap={guard.effective_photo_capture_file_type}"
        f"({guard.photo_capture_output_mp_label},dci4k_blk={guard.photo_capture_dci4k_locked},"
        f"slot1_blk={guard.photo_capture_slot1_write_blocked}), "
        f"enlarge=({guard.effective_enlarge_initial_mag},{guard.effective_enlarge_initial_position}), "
        f"fx6_photo={guard.fx6_photo_capture_supported}"
    )
    verdict = GateVerdict(
        gate_id=G122_GATE_ID,
        gate_code=G122_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `122`-Gate Master Safety Preflight (`G01..G122`)
# ---------------------------------------------------------------------------


def evaluate_122gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    dci4k_aspect_kwargs: Optional[Mapping[str, Any]] = None,
    custom_hold_camset_photo_kwargs: Optional[Mapping[str, Any]] = None,
    master_120_override: Optional[Master120GateReport] = None,
    **m120_passthrough_kwargs: Any,
) -> Master122GateReport:
    """Evaluate all 122 Master Safety Gates (`G01..G122`) deterministically by
    delegating `G01..G120` directly to `evaluate_120gate_preflight()`.
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

    m120_report: Master120GateReport = (
        master_120_override
        if master_120_override is not None
        else evaluate_120gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m120_passthrough_kwargs,
        )
    )

    phase288_audit = audit_phase288_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g121_verdict, g121_res = evaluate_g121_dci4k_and_aspect_ratio_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        dci4k_aspect_kwargs=dci4k_aspect_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase288_audit,
    )

    g122_verdict, g122_res = evaluate_g122_custom_hold_camset_photo_capture_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        custom_hold_camset_photo_kwargs=custom_hold_camset_photo_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase288_audit,
    )

    gates_121_to_122 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g121_verdict, g122_verdict)
    ]
    all_gates = tuple(list(m120_report.gates) + gates_121_to_122)

    g01_to_g12_verified = int(m120_report.summary["g01_to_g12_verified"])
    g13_to_g120_verified = int(m120_report.summary["g13_to_g118_verified"]) + int(
        m120_report.summary["g119_to_g120_verified"]
    )
    g121_to_g122_verified = sum(1 for v in (g121_verdict, g122_verdict) if v.passed)
    total_verified = (
        g01_to_g12_verified + g13_to_g120_verified + g121_to_g122_verified
    )

    g121_to_g122_all_passed = g121_to_g122_verified == 2
    g13_to_g122_all_passed = (
        m120_report.g13_to_g120_all_passed and g121_to_g122_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m120_report.gates[:9])

    offline_119_verified = (
        g01_to_g09_ok
        and m120_report.offline_117_gates_verified
        and g121_to_g122_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_122_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g122_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m120_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_119_verified
        and m120_report.h0_h1_trial_entry_allowed
        and g121_to_g122_all_passed
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
        list(m120_report.errors)
        + list(g121_verdict.errors)
        + list(g122_verdict.errors)
    )
    warnings: List[str] = (
        list(m120_report.warnings)
        + list(g121_verdict.warnings)
        + list(g122_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m120_report.g13_to_g120_all_passed:
        overall_status = m120_report.status
    elif not g121_verdict.passed:
        overall_status = g121_verdict.status
    elif not g122_verdict.passed:
        overall_status = g122_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_122_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_122_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_122_verified:
        overall_status = "VERIFIED_ALL_122_GATES"
    else:
        overall_status = "VERIFIED_119_OF_122_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m120_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g121_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g122_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 122,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 122 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g120_verified": g13_to_g120_verified,
        "g121_to_g122_verified": g121_to_g122_verified,
        "g13_to_g122_all_passed": g13_to_g122_all_passed,
        "g121_to_g122_all_passed": g121_to_g122_all_passed,
        "offline_119_gates_verified": offline_119_verified,
        "all_122_gates_verified": all_122_verified,
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

    return Master122GateReport(
        schema=REALHW_DCI4K_ASPECT_CUSTOM_HOLD_CAMSET_PHOTO_CAPTURE_122GATE_SCHEMA,
        version=REALHW_DCI4K_ASPECT_CUSTOM_HOLD_CAMSET_PHOTO_CAPTURE_122GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_119_gates_verified=offline_119_verified,
        all_122_gates_verified=all_122_verified,
        g13_to_g122_all_passed=g13_to_g122_all_passed,
        g121_to_g122_all_passed=g121_to_g122_all_passed,
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
        master_120_report=m120_report.to_dict(),
        g121_result=g121_res.to_dict(),
        g122_result=g122_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_122_master_safety_gates = evaluate_122gate_preflight
run_122_gate_preflight = evaluate_122gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard",
        description=(
            "Phase 288 (Wave-51) Gates G121 (XAVC S-I DCI 4K 4096x2160 + Reboot-Gated "
            "24.00p vs Long-GOP UHD 3840x2160, 4264x2408 Type-A HDMI RAW, & Still "
            "[Aspect Ratio] 3:2/4:3/16:9/1:1) + G122 ([Reg. Custom Shoot Set] 11 Hold "
            "Checkboxes Still P/A/S/M vs [Camera Set. Memory] 1..3 + M1..M4 "
            "%%c:%%s/SONY/SETTING/%%s/CAMPR%%02d%%c.DAT vs FX6 s/SONY/PRO/CAMERA/, & "
            "Playback [Photo Capture] DCI 4K Lockout + Slot-1 Vault Write Firewall / "
            "[Enlarge Initial Mag./Position]) + Unified 122-Gate Master Safety Preflight"
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

    report = evaluate_122gate_preflight(
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
            f"verified={report.summary['verified_gates']}/122 "
            f"g121_to_g122_all_passed={report.g121_to_g122_all_passed} "
            f"all_122_gates_verified={report.all_122_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = (
        report.all_122_gates_verified
        if args.dry_run_simulated
        else report.offline_119_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
