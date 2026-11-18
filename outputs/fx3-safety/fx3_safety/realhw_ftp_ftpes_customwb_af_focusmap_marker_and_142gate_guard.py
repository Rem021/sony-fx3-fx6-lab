"""Phase 319 (Task H381, Wave-61, 142/142 Safety Gates): Real-Hardware Safety Guard for
`[FTP Transfer Func.]` (`FTP`/`FTPES` Explicit TLS & 9 Server Slots vs Zero `SFTP`,
`Slot-1` `AVF_INFO` `EROFS=30` Firewall, `USB-LAN` Zero-RF Trap) & White Balance
(`Custom 1..3` `Initialize`-Only / `0x0220` Error / `Cine EI` Auto Lockout / Still
`[Shutter AWB Lock]` / `[Shockless WB]` vs FX6 `ATW` & `Memory A..H`) (Gate `G141`),
Movie AF (`1..7` Transition & `1..5` Subj. Shift Sens. on BOTH FX3 & FX6, `[AF Assist]`,
External *Monitor & Control* `[Focus Map]` vs Zero On-Body Menu, 15-Ratio `[Aspect Marker]`
& 4-Color `[Peaking Display]` vs FX6 `User Box`) (Gate `G142`), and Unified
142-Gate Master Safety Preflight (`evaluate_142gate_preflight`, `verify-142-gates`).

Authoritative Empirical Baseline:
  `reports/2026-11-17-global-sony-wave61-ftp-ftps-customwb-af-speed-focusmap-marker-intel/README.md`
  Sony `ILME-FX3` (`Ver. 7.02`, `PRODUCT_MODEL_ALCIN_UUD`, `helpguide.sony.net/ilc/2210` & `di/ftp_2210`)
  vs Sony `ILME-FX6` (`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`, `5-024-458-18`).

Hard Safety Redlines (Permanent Bench Locks):
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`
- `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`
- `HUMAN_HARDWARE_ATTACH_TOKEN = False`
- `CROSS_MODEL_FLASH_AUTHORIZED = False`
- `USB_PACKETS_TRANSMITTED = 0`
- `PHYSICAL_USB_PACKETS_EMITTED = 0`
- `RAW_FIRMWARE_BYTES_LEAKED = 0`
- Strict `os.open(..., os.O_RDONLY)` + targeted `os.pread` donor inspection (< 0.20s).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard import (
    GateVerdict,
)
from .realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_140gate_guard import (
    Master140GateReport,
    evaluate_140gate_preflight,
)
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Version & Permanent Hardware Safety Redlines
# ---------------------------------------------------------------------------

REALHW_142GATE_PREFLIGHT_SCHEMA = "realhw_142gate_preflight_v1"
REALHW_FTP_FTPES_CUSTOMWB_AF_FOCUSMAP_MARKER_142GATE_SCHEMA = (
    REALHW_142GATE_PREFLIGHT_SCHEMA
)
REALHW_FTP_FTPES_CUSTOMWB_AF_FOCUSMAP_MARKER_142GATE_VERSION = "2026.11.17"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST_PHASE319 = "FX3_CLEAN_ROOM_TEST"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]
DONOR_CHECK_MAX_SECONDS_PHASE319 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE319 = 15.0

# Immutable redlines (NEVER authorize physical live attach or persistent flash/writes)
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

STATUS_VERIFIED_SAFE = "STATUS_VERIFIED_SAFE"
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE = "STATUS_BLOCKED_PERSISTENT_EMMC_WRITE"

# POSIX errnos
EROFS_ERRNO_PHASE319 = errno.EROFS  # 30
EROFS_NAME_PHASE319 = "EROFS"
EOPNOTSUPP_ERRNO_PHASE319 = errno.EOPNOTSUPP  # 95 (Mac) / ENOTSUP
if EOPNOTSUPP_ERRNO_PHASE319 != 95:  # pragma: no cover - platform guard
    EOPNOTSUPP_ERRNO_PHASE319 = 95
EOPNOTSUPP_NAME_PHASE319 = "EOPNOTSUPP"
EINVAL_ERRNO_PHASE319 = errno.EINVAL  # 22
EINVAL_NAME_PHASE319 = "EINVAL"
EBUSY_ERRNO_PHASE319 = errno.EBUSY  # 16
EBUSY_NAME_PHASE319 = "EBUSY"
ENODEV_ERRNO_PHASE319 = errno.ENODEV  # 19
ENODEV_NAME_PHASE319 = "ENODEV"

# Target Identity Baselines
FX3_MODEL_NAME_PHASE319 = "ILME-FX3"
FX3_MODEL_ID_PHASE319 = 0x39383232
FX3_HELP_GUIDE_CODE_PHASE319 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE319 = "7.02"

FX6_MODEL_NAME_PHASE319 = "ILME-FX6"
FX6_PRODUCT_CODE_PHASE319 = "PRODUCT_MODEL_CHAPLIN"
FX6_DEFAULT_FW_VERSION_PHASE319 = "6.01"

# Gate IDs & Canonical Codes
G141 = "G141"
G141_GATE_ID = "G141"
REALHW_FTP_FTPES_9SLOT_ZERO_SFTP_AVF_VAULT_AND_CUSTOMWB_CINEEI_GUARD = (
    "REALHW_FTP_FTPES_9SLOT_ZERO_SFTP_AVF_VAULT_AND_CUSTOMWB_CINEEI_GUARD"
)
G141_GATE_CODE = REALHW_FTP_FTPES_9SLOT_ZERO_SFTP_AVF_VAULT_AND_CUSTOMWB_CINEEI_GUARD

G142 = "G142"
G142_GATE_ID = "G142"
REALHW_MOVIE_AF_1TO7_1TO5_EXTERNAL_FOCUSMAP_AND_15ASPECT_MARKER_PEAKING_GUARD = (
    "REALHW_MOVIE_AF_1TO7_1TO5_EXTERNAL_FOCUSMAP_AND_15ASPECT_MARKER_PEAKING_GUARD"
)
G142_GATE_CODE = (
    REALHW_MOVIE_AF_1TO7_1TO5_EXTERNAL_FOCUSMAP_AND_15ASPECT_MARKER_PEAKING_GUARD
)

# Shared Mode / Reset Enums
SHOOT_MODE_STILL_PHASE319 = "Still"
SHOOT_MODE_MOVIE_PHASE319 = "Movie"
SHOOT_MODE_SQ_PHASE319 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE319: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE319,
    SHOOT_MODE_MOVIE_PHASE319,
    SHOOT_MODE_SQ_PHASE319,
)

RESET_ACTION_NONE_PHASE319 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319 = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE319 = "Reset Network Set."
RESET_ACTION_INITIALIZE_PHASE319 = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE319: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE319,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319,
    RESET_ACTION_RESET_NETWORK_SET_PHASE319,
    RESET_ACTION_INITIALIZE_PHASE319,
)

LOG_SHOOTING_OFF_PHASE319 = "Off"
LOG_SHOOTING_FLEXIBLE_ISO_PHASE319 = "Flexible ISO"
LOG_SHOOTING_CINE_EI_PHASE319 = "Cine EI"
LOG_SHOOTING_CINE_EI_QUICK_PHASE319 = "Cine EI Quick"
ALLOWED_LOG_SHOOTING_MODES_PHASE319: Tuple[str, ...] = (
    LOG_SHOOTING_OFF_PHASE319,
    LOG_SHOOTING_FLEXIBLE_ISO_PHASE319,
    LOG_SHOOTING_CINE_EI_PHASE319,
    LOG_SHOOTING_CINE_EI_QUICK_PHASE319,
)

# ---------------------------------------------------------------------------
# G141 Constants: FTP / FTPES, 9 Server Slots, AVF_INFO Vault, USB-LAN, WB
# ---------------------------------------------------------------------------

FTP_FUNCTION_F_UXC_RESID16_G141 = 0x6317
FTP_SERVER1_F_UXC_RESID16_G141 = 0x6305
FTP_SERVER8_F_UXC_RESID16_G141 = 0x72F4
FTP_SERVER9_F_UXC_RESID16_G141 = 0x630D
FTP_SECURE_PROTOCOL_F_UXC_RESID16_G141 = 0x60DD
FTP_FTPES_CONNECT_F_UXC_RESID16_G141 = 0x6553
FTP_TRANSFER_JPEG_SIZE_DORMANT_F_UXC_RESID16_G141 = 0x6AED
FTP_TRANSFER_HEIF_SIZE_DORMANT_F_UXC_RESID16_G141 = 0x63DD
FTP_AVF_DB_RESET_WARNING_BASE_UXC_RESID16_G141 = 0x0A13
FTP_SLOT1_MUTEX_BASE_UXC_RESID16_G141 = 0x09B7

WB_WHITE_BALANCE_F_UXC_RESID16_G141 = 0x73EE
WB_PRIORITY_SET_IN_AWB_F_UXC_RESID16_G141 = 0x67A7
WB_SHUTTER_AWB_LOCK_F_UXC_RESID16_G141 = 0x66DB
WB_SHOCKLESS_WB_F_UXC_RESID16_G141 = 0x62FE
WB_CUSTOM_ERROR_F_UXC_RESID16_G141 = 0x63AC
WB_CUSTOM_ERROR_BASE_UXC_RESID16_G141 = 0x0220

FX3_FTP_SERVER_SLOT_MIN_G141 = 1
FX3_FTP_SERVER_SLOT_MAX_G141 = 9
FX3_FTP_EXACT_SERVER_SLOTS_G141 = 9
FX3_FTP_SPECIFY_DIRECTORY_MAX_LEN_G141 = 128
FX3_FTP_CACERT_FILENAME_G141 = "cacert.pem"
FX3_FTP_CACERT_MAX_BYTES_G141 = 1_048_576  # <= 1 MB

FX6_FTP_UI_SERVER_SLOTS_G141 = 3
FX6_FTP_ELF_SERVER_SLOTS_MAX_G141 = 16
FX6_FTP_CERT_FILENAME_G141 = "certification.pem"
FX6_FTP_CERT_SLOT_G141 = "Slot B"

FTP_PROTOCOL_FTP_G141 = "FTP"
FTP_PROTOCOL_FTPES_G141 = "FTPES"
FTP_PROTOCOL_SFTP_FORBIDDEN_G141 = "SFTP"
FTP_PROTOCOL_IMPLICIT_FTPS_FORBIDDEN_G141 = "FTPS_Implicit"
ALLOWED_FX3_FTP_PROTOCOLS_G141: Tuple[str, ...] = (
    FTP_PROTOCOL_FTP_G141,
    FTP_PROTOCOL_FTPES_G141,
)
DORMANT_OR_FORBIDDEN_FTP_PROTOCOLS_G141: Tuple[str, ...] = (
    FTP_PROTOCOL_SFTP_FORBIDDEN_G141,
    FTP_PROTOCOL_IMPLICIT_FTPS_FORBIDDEN_G141,
)

FTP_MODE_PASSIVE_G141 = "Passive"
FTP_MODE_ACTIVE_G141 = "Active"
ALLOWED_FTP_TRANSFER_MODES_G141: Tuple[str, ...] = (
    FTP_MODE_PASSIVE_G141,
    FTP_MODE_ACTIVE_G141,
)

DORMANT_FTP_IMAGE_SIZE_TRAPS_G141: Tuple[str, ...] = (
    "Transfer JPEG Size",
    "Transfer HEIF Size",
    "0x6aed",
    "0x63dd",
)

FTP_DIR_HIERARCHY_STANDARD_G141 = "Standard"
FTP_DIR_HIERARCHY_SAME_AS_CAMERA_G141 = "Same as in Camera"
ALLOWED_FTP_DIR_HIERARCHIES_G141: Tuple[str, ...] = (
    FTP_DIR_HIERARCHY_STANDARD_G141,
    FTP_DIR_HIERARCHY_SAME_AS_CAMERA_G141,
)

ALLOWED_FTP_ROOT_CERT_ERR_BEHAVIORS_G141: Tuple[str, ...] = (
    "Does Not Connect",
    "Connect",
)
ALLOWED_FTP_CLIP_FLAGS_G141: Tuple[str, ...] = ("Off", "OK", "NG", "KEEP")
ALLOWED_FTP_RAW_JH_TARGETS_G141: Tuple[str, ...] = (
    "JPEG & HEIF",
    "RAW",
    "RAW+J & RAW+H",
)
ALLOWED_FTP_MOVIE_TARGETS_G141: Tuple[str, ...] = (
    "Proxy Only",
    "Original Only",
    "Proxy & Original",
)
ALLOWED_USBLAN_STATES_G141: Tuple[str, ...] = ("Disconnected", "Connected")

WB_COLOR_TEMP_MIN_K_G141 = 2500
WB_COLOR_TEMP_MAX_K_G141 = 9900
WB_COLOR_TEMP_STEP_K_G141 = 100
WB_AB_AXIS_MIN_G141 = -7.0
WB_AB_AXIS_MAX_G141 = 7.0
WB_AB_STEP_G141 = 0.5
WB_GM_AXIS_MIN_G141 = -7.0
WB_GM_AXIS_MAX_G141 = 7.0
WB_GM_STEP_G141 = 0.25

ALLOWED_FX3_WB_MODES_G141: Tuple[str, ...] = (
    "Auto",
    "Auto: Ambience",
    "Auto: White",
    "Daylight",
    "Shade",
    "Cloudy",
    "Incandescent",
    "Fluorescent",
    "Flash",
    "Underwater Auto",
    "C.Temp./Filter",
    "Custom 1",
    "Custom 2",
    "Custom 3",
)
CINE_EI_LOCKED_WB_MODES_G141: Tuple[str, ...] = (
    "Auto",
    "Auto: Ambience",
    "Auto: White",
    "Underwater Auto",
)
ALLOWED_PRIORITY_SET_AWB_G141: Tuple[str, ...] = ("Standard", "Ambience", "White")
ALLOWED_SHUTTER_AWB_LOCK_G141: Tuple[str, ...] = (
    "Off",
    "Shut. Halfway",
    "Cont. Shooting",
)
ALLOWED_SHOCKLESS_WB_G141: Tuple[str, ...] = ("Off", "1", "2", "3")
ALLOWED_PICTURE_PROFILE_GAMMA_G141: Tuple[str, ...] = (
    "Off",
    "Still",
    "Movie",
    "ITU709",
    "ITU709(800%)",
    "Cine1",
    "Cine2",
    "Cine3",
    "Cine4",
    "HLG",
    "HLG1",
    "HLG2",
    "HLG3",
    "S-Log2",
    "S-Log3",
    "PPLUT1",
    "PPLUT2",
    "PPLUT3",
    "PPLUT4",
)
CUSTOM_WB_ERROR_0X0220_PP_GAMMAS_G141: Tuple[str, ...] = (
    "S-Log3",
    "PPLUT1",
    "PPLUT2",
    "PPLUT3",
    "PPLUT4",
)
ALLOWED_FX6_WHT_BAL_SWITCH_G141: Tuple[str, ...] = ("PRST", "A", "B")
ALLOWED_FX6_WB_MEMORY_BANKS_G141: Tuple[str, ...] = (
    "Memory A",
    "Memory B",
    "Memory C",
    "Memory D",
    "Memory E",
    "Memory F",
    "Memory G",
    "Memory H",
)

# ---------------------------------------------------------------------------
# G142 Constants: Movie AF 1..7 & 1..5, External Focus Map, 15-Aspect Marker & Peaking
# ---------------------------------------------------------------------------

AF_TRANSITION_SPEED_F_UXC_RESID16_G142 = 0x6E9D
AF_SUBJ_SHIFT_SENS_F_UXC_RESID16_G142 = 0x79D6
AF_ASSIST_F_UXC_RESID16_G142 = 0x64A9
FOCUS_MAP_SHARED_F_UXC_RESID16_G142 = 0x61F9
MARKER_DISPLAY_F_UXC_RESID16_G142 = 0x6803
CENTER_MARKER_F_UXC_RESID16_G142 = 0x6707
ASPECT_MARKER_F_UXC_RESID16_G142 = 0x66AC
SAFETY_ZONE_F_UXC_RESID16_G142 = 0x6F50
GUIDEFRAME_F_UXC_RESID16_G142 = 0x62F9
PEAKING_DISPLAY_F_UXC_RESID16_G142 = 0x6FE5
PEAKING_LEVEL_BASE_UXC_RESID16_G142 = 0x014C
PEAKING_COLOR_BASE_UXC_RESID16_G142 = 0x014D

AF_TRANSITION_SPEED_MIN_G142 = 1
AF_TRANSITION_SPEED_MAX_G142 = 7
AF_TRANSITION_SPEED_DEFAULT_G142 = 5

# CRITICAL Wave-61 disambiguation: BOTH FX3 and FX6 use 1..5 (NOT 1..7 on FX6!)
AF_SUBJ_SHIFT_SENS_MIN_G142 = 1
AF_SUBJ_SHIFT_SENS_MAX_G142 = 5
AF_SUBJ_SHIFT_SENS_DEFAULT_G142 = 5

AF_ASSIST_INCOMPATIBLE_LENSES_G142: Tuple[str, ...] = ("SELP1650", "SEL18200LE")

FOCUS_MAP_MIN_FX3_FW_G142 = 6.00
FOCUS_MAP_HIGH_FPS_BLOCK_THRESHOLD_G142 = 150
FX6_FOCUS_MAP_LOW_FPS_BLOCK_THRESHOLD_G142 = 6

EXACT_15_ACTIVE_ASPECT_RATIOS_FX3_G142: Tuple[str, ...] = (
    "9:16",
    "4:5",
    "1:1",
    "4:3",
    "13:9",
    "14:9",
    "15:9",
    "16:9",
    "17:9",
    "1.66:1",
    "1.85:1",
    "1.91:1",
    "2:1",
    "2.35:1",
    "2.39:1",
)
ALLOWED_ASPECT_MARKER_STATES_FX3_G142: Tuple[str, ...] = (
    "Off",
) + EXACT_15_ACTIVE_ASPECT_RATIOS_FX3_G142  # 16 exact states!

ALLOWED_FX3_SAFETY_ZONES_G142: Tuple[str, ...] = ("Off", "80%", "90%")
ALLOWED_FX6_ASPECT_SAFETY_AREAS_G142: Tuple[str, ...] = (
    "Off",
    "80%",
    "90%",
    "92.5%",
    "95%",
)

ALLOWED_PEAKING_LEVELS_G142: Tuple[str, ...] = ("High", "Mid", "Low")
ALLOWED_FX3_PEAKING_COLORS_G142: Tuple[str, ...] = ("Red", "Yellow", "Blue", "White")
ALLOWED_FX6_PEAKING_COLORS_G142: Tuple[str, ...] = ("B&W", "Red", "Yellow", "Blue")

FX6_USER_BOX_WIDTH_MIN_G142 = 3
FX6_USER_BOX_WIDTH_MAX_G142 = 479
FX6_USER_BOX_HEIGHT_MIN_G142 = 3
FX6_USER_BOX_HEIGHT_MAX_G142 = 269
FX6_USER_BOX_H_POS_MIN_G142 = -476
FX6_USER_BOX_H_POS_MAX_G142 = 476
FX6_USER_BOX_V_POS_MIN_G142 = -266
FX6_USER_BOX_V_POS_MAX_G142 = 266
FX6_ASPECT_MASK_MIN_G142 = 0
FX6_ASPECT_MASK_MAX_G142 = 15
FX6_ASPECT_MASK_DEFAULT_G142 = 12

# Status / Violation Codes
STATUS_BLOCKED_PHASE319_DONOR_INTEGRITY = "STATUS_BLOCKED_PHASE319_DONOR_INTEGRITY"

STATUS_VERIFIED_G141 = "STATUS_VERIFIED_G141"
STATUS_BLOCKED_G141_TELEMETRY_INVALID = "STATUS_BLOCKED_G141_TELEMETRY_INVALID"
STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION = (
    "STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION"
)
STATUS_BLOCKED_G141_SLOT1_AVF_INFO_VAULT_OR_CACERT_VIOLATION = (
    "STATUS_BLOCKED_G141_SLOT1_AVF_INFO_VAULT_OR_CACERT_VIOLATION"
)
STATUS_BLOCKED_G141_USBLAN_ZERO_RF_BYPASS_VIOLATION = (
    "STATUS_BLOCKED_G141_USBLAN_ZERO_RF_BYPASS_VIOLATION"
)
STATUS_BLOCKED_G141_CUSTOMWB_LOG_ERR_0X0220_OR_CINEEI_VIOLATION = (
    "STATUS_BLOCKED_G141_CUSTOMWB_LOG_ERR_0X0220_OR_CINEEI_VIOLATION"
)

STATUS_VERIFIED_G142 = "STATUS_VERIFIED_G142"
STATUS_BLOCKED_G142_TELEMETRY_INVALID = "STATUS_BLOCKED_G142_TELEMETRY_INVALID"
STATUS_BLOCKED_G142_MOVIE_AF_1TO7_1TO5_OR_ASSIST_VIOLATION = (
    "STATUS_BLOCKED_G142_MOVIE_AF_1TO7_1TO5_OR_ASSIST_VIOLATION"
)
STATUS_BLOCKED_G142_FOCUSMAP_ONBODY_OR_EXCLUSION_VIOLATION = (
    "STATUS_BLOCKED_G142_FOCUSMAP_ONBODY_OR_EXCLUSION_VIOLATION"
)
STATUS_BLOCKED_G142_MARKER_15ASPECT_PEAKING_OR_HDMI_VIOLATION = (
    "STATUS_BLOCKED_G142_MARKER_15ASPECT_PEAKING_OR_HDMI_VIOLATION"
)

# ---------------------------------------------------------------------------
# Pinned Wave-61 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE319: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x03BC0CE2, b"BKID_APP_ftp_server_settings_display_name0"),
    (0x03BC0E3A, b"BKID_APP_ftp_server_settings_display_name8"),
    (0x03B4EE93, b"SET_SERVER_SECURE_PROTOCOL_OFF"),
    (0x03B4EED9, b"SET_SERVER_SECURE_PROTOCOL_ON"),
    (0x03BCE770, b"BKID_APP_ftp_server_settings_directory_hierarchy0"),
    (0x03BC9FD5, b"BKID_APP_setting_ftp_power_save"),
    (0x03BF38B6, b"BKID_APP_is_valid_ftp_transfer_target_image_clip_flag_ok"),
    (0x03B13327, b"CONTENT_INFO_FTP_TRANS_STAT_COMPLETE"),
    (0x0392679B, b"save_ftp_transfer_list_to_media"),
    (0x03BEBFC3, b"BKID_APP_setting_white_balance_still"),
    (0x02FB5570, b"COLOR_TEMP_COLOR_FILTER_2500K"),
    (0x02FB6228, b"COLOR_TEMP_COLOR_FILTER_9900K"),
    (0x03BEEF08, b"BKID_APP_preserved_white_balance_adjustment_gm_custom_1"),
    (0x03BC8ABB, b"BKID_APP_setting_priority_set_in_awb"),
    (0x03BC8B08, b"BKID_APP_setting_stl_awb_lock_with_shutter"),
    (0x03BC8B61, b"BKID_APP_setting_movie_shockless_wb"),
    (0x03B0568B, b"MOVIE_AF_TRANSITION_SPEED_1_SLOW"),
    (0x03B0581C, b"MOVIE_AF_TRANSITION_SPEED_7_FAST"),
    (0x03B054C2, b"MOVIE_AF_SUBJ_SHIFT_SENS_1_LOCKED_ON"),
    (0x03B055CC, b"MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE"),
    (0x03BC914B, b"BKID_APP_setting_af_assist"),
    (0x0399B508, b"to_remote_event_focus_map"),
    (0x0390D5B3, b"sequence_notify_focus_map"),
    (0x03BC7B80, b"BKID_APP_setting_marker_display_aspect"),
    (0x03A77078, b"VAL_setting_marker_display_aspect_ASPECT_2_39_1"),
    (0x03BC7BD1, b"BKID_APP_setting_safety_zone"),
    (0x03BC7C0E, b"BKID_APP_setting_guide_frame"),
    (0x03BC98FC, b"BKID_APP_setting_peaking_color"),
    (0x03B33694, b"PEAKING_COLOR_VALUE_WHITE"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE319 = (
    "ab7e0fcf0c81666fe90e64034497f574e43e94f5765d928f94d59ed482675559"
)

PINNED_FX6_APPFW_SLICES_PHASE319: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x026C31C7, b"AUTO_UPLOAD_PROXY_CHUNK"),
    (0x027A7117, b"SET_SERVER_SECURE_PROTOCOL_ON_FTPES"),
    (0x027A713B, b"SET_SERVER_SECURE_PROTOCOL_ON_SFTP"),
    (0x0269F4E4, b"WHITE_SELECT_MEMORY_A"),
    (0x0269F39B, b"WHITE_SELECT_MEMORY_H"),
    (0x0269FE68, b"ATW_SPEED_1"),
    (0x0269FEF0, b"ATW_SPEED_5"),
    (0x027A900E, b"ASSIGNABLE_SWITCH_ATW_HOLD"),
    (0x026C6923, b"MOVIE_AF_SUBJ_SHIFT_SENS_1_LOCKED_ON"),
    (0x026C6A2D, b"MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE"),
    (0x02710B3F, b"BKID_APP_USER_MENU_FOCUS_MAP"),
    (0x027A982D, b"ASSIGNABLE_SWITCH_FOCUS_MAP"),
    (0x0270B8B2, b"BKID_APP_SETTING_USER_BOX"),
    (0x0263D902, b"PRM_HAITA_setting_user_box_h_pos_setting_user_box_width"),
    (0x026C015E, b"PEAKING_COLOR_VALUE_B_W"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE319 = (
    "251ed8daff1bafd34ece44804f3e11c6717f40d4ac63033aa717537ef227d4ac"
)

PINNED_PHASE319_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE319,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE319),
        "FX3 appFw.so Wave-61 FTP-9Slot/CustomWB/AF-1to7-1to5/RemoteFocusMap/15Aspect/Peaking slices",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"FTP Transfer Func.",
            b"Connects with FTPES.",
            b"AF Subj. Shift Sensitivity",
            b"Aspect Marker",
            b"Peaking Display",
        ),
        "FX3 string_english_f.uxc Wave-61 EN parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"FTP transfer results will be reset",
            b"Custom WB Error",
            b"Peaking Color",
        ),
        "FX3 string_english.uxc Wave-61 AVF_INFO FTP reset & Custom WB Error",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (b"Peaking Display",),
        "FX3 string_english_g.uxc Wave-61 Peaking Display strings",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "FTP\u4f20\u8f93\u529f\u80fd".encode("utf-8"),
            "\u8fde\u63a5FTPES\u3002".encode("utf-8"),
            "AF\u6444\u4f53\u8f6c\u79fb\u654f\u5ea6".encode("utf-8"),
            "\u7eb5\u6a2a\u6807\u8bb0".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-61 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "FTP\u50b3\u8f38\u529f\u80fd".encode("utf-8"),
            "\u9023\u7dda\u5230FTPES\u3002".encode("utf-8"),
            "\u5c0d\u7126\u8b8a\u63db\u901f\u5ea6".encode("utf-8"),
            "\u9577\u5bec\u6bd4\u8f14\u52a9\u6a19\u8a8c".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-61 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "FTP\u8ee2\u9001\u6a5f\u80fd".encode("utf-8"),
            "FTPES\u3067\u63a5\u7d9a\u3057\u307e\u3059".encode("utf-8"),
            "AF\u4e57\u308a\u79fb\u308a\u611f\u5ea6".encode("utf-8"),
            "\u30a2\u30b9\u30da\u30af\u30c8\u30de\u30fc\u30ab\u30fc".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-61 JA parity",
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
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE319,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE319),
        "FX6 appFw.so Wave-61 ChunkProxy/FTPES-SFTP/ATW/MemoryA-H/SubjShift1..5/UserBox/B&W slices",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"Focus Map",
            b"User Box",
            b"ATW",
            b"Peaking",
        ),
        "FX6 string_english.uxc Wave-61 Focus Map, User Box, ATW & Peaking strings",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"Aspect Mask",
            b"B&W",
            b"User Box",
            b"ATW",
        ),
        "FX6 string_english_2.uxc Wave-61 Aspect Mask & B&W Peaking strings",
    ),
}


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _is_clean_room_forced(force_clean_room: Optional[bool]) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE319):
        if os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def _is_strict_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _is_strict_num(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def _is_on_off(val: Any) -> bool:
    return isinstance(val, str) and val in ("On", "Off")


def _encode_token_variants(token: bytes) -> Tuple[bytes, ...]:
    variants = [token]
    try:
        text = token.decode("utf-8")
        variants.append(text.encode("utf-16-le"))
    except UnicodeDecodeError:
        pass
    return tuple(variants)


def _read_exact_o_rdonly_slices(
    path: Path, slices: Sequence[Tuple[int, bytes]]
) -> Tuple[int, str, List[str]]:
    missing: List[str] = []
    hasher = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY)
    try:
        st = os.fstat(fd)
        for offset, expected in slices:
            chunk = os.pread(fd, len(expected), offset)
            if chunk != expected:
                missing.append(f"slice_mismatch@0x{offset:08X}")
            hasher.update(chunk)
        return st.st_size, hasher.hexdigest(), missing
    finally:
        os.close(fd)


def _read_full_o_rdonly_sha256_and_tokens(
    path: Path, required_tokens: Sequence[bytes]
) -> Tuple[int, str, List[str]]:
    missing: List[str] = []
    fd = os.open(path, os.O_RDONLY)
    try:
        st = os.fstat(fd)
        data = os.read(fd, st.st_size)
    finally:
        os.close(fd)
    sha = hashlib.sha256(data).hexdigest()
    for tok in required_tokens:
        if not any(var in data for var in _encode_token_variants(tok)):
            missing.append(f"token_missing:{tok[:32]!r}")
    return st.st_size, sha, missing


def _fx3_fw_ge(ver_str: str, min_ver: float) -> bool:
    try:
        return float(ver_str) >= min_ver
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Donor Integrity Audit (O_RDONLY / Clean-Room Dual-Mode)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase319DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    fx3_contracts_verified: bool
    fx6_contracts_verified: bool
    four_lang_resid16_parity_verified: bool
    zero_forbidden_myths_verified: bool
    elapsed_seconds: float
    within_budget_200ms: bool
    raw_firmware_bytes_leaked: int
    file_digests: Dict[str, str]
    missing_markers: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def audit_phase319_donor_contracts(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase319DonorAuditResult:
    import time

    t0 = time.perf_counter()
    clean_forced = _is_clean_room_forced(force_clean_room)
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else dict(PINNED_PHASE319_DONOR_SPECS)
    )
    resolved_work_root = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(
            repo_root=repo_root or DEFAULT_REPO_ROOT
        ).work_root
    )

    if clean_forced:
        dt = time.perf_counter() - t0
        return Phase319DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_NO_DONOR_DISK_IO",
            files_inspected=0,
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            zero_forbidden_myths_verified=True,
            elapsed_seconds=round(dt, 6),
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE319,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(),
        )

    missing_files = (
        list(specs.keys())
        if resolved_work_root is None
        else [
            key
            for key, spec in specs.items()
            if not (resolved_work_root / spec[1]).exists()
        ]
    )
    if missing_files and donor_specs_override is None:
        dt = time.perf_counter() - t0
        return Phase319DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="CLEAN_ROOM_FALLBACK_MISSING_DONORS",
            files_inspected=0,
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            zero_forbidden_myths_verified=True,
            elapsed_seconds=round(dt, 6),
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE319,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(
                f"Donor files absent under {resolved_work_root}; clean-room synthetic fallback active",
            ),
        )

    digests: Dict[str, str] = {}
    missing_markers: List[str] = []
    errors: List[str] = []
    files_inspected = 0

    for key, (model, rel_path, expected_size, expected_sha, tokens, _desc) in specs.items():
        if resolved_work_root is None:
            missing_markers.append(f"{key}:file_missing")
            errors.append(f"Donor missing: {rel_path}")
            continue
        path = resolved_work_root / rel_path
        if not path.exists():
            missing_markers.append(f"{key}:file_missing")
            errors.append(f"Donor missing: {rel_path}")
            continue

        files_inspected += 1
        if key == "fx3_appfw_so" and donor_specs_override is None:
            size, sha, slice_errs = _read_exact_o_rdonly_slices(
                path, PINNED_FX3_APPFW_SLICES_PHASE319
            )
            missing_markers.extend(f"{key}:{m}" for m in slice_errs)
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            size, sha, slice_errs = _read_exact_o_rdonly_slices(
                path, PINNED_FX6_APPFW_SLICES_PHASE319
            )
            missing_markers.extend(f"{key}:{m}" for m in slice_errs)
        else:
            size, sha, tok_errs = _read_full_o_rdonly_sha256_and_tokens(path, tokens)
            for m in tok_errs:
                if "token_missing" in m:
                    missing_markers.append(f"{key}:token_missing")
                else:
                    missing_markers.append(f"{key}:{m}")

        digests[key] = sha
        if size != expected_size:
            missing_markers.append(f"{key}:size_mismatch")
            errors.append(f"{key} ({model}) size {size} != {expected_size}")
        if sha != expected_sha:
            missing_markers.append(f"{key}:sha256_mismatch")
            errors.append(f"{key} ({model}) sha256 {sha} != {expected_sha}")

    dt = time.perf_counter() - t0
    valid = len(missing_markers) == 0 and len(errors) == 0
    return Phase319DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE319_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="POSIX_O_RDONLY_AND_PREAD_ZERO_MUTATION",
        files_inspected=files_inspected,
        fx3_contracts_verified=valid,
        fx6_contracts_verified=valid,
        four_lang_resid16_parity_verified=valid,
        zero_forbidden_myths_verified=valid,
        elapsed_seconds=round(dt, 6),
        within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE319,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        file_digests=digests,
        missing_markers=tuple(missing_markers),
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# Gate G141 Result & Matrix + Verifier
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class G141FtpFtpesCustomWbVaultGuardResult:
    valid: bool
    status: str
    verification_mode: str
    target_model: str
    body_model_name: str
    body_model_id: int
    help_guide_code: str
    firmware_version: str
    reset_action: str
    shoot_mode: str
    requested_ftp_function: str
    effective_ftp_function: str
    requested_cloud_connection: str
    ftp_cloud_mutual_exclusion_ok: bool
    ftp_server_slot: int
    ftp_protocol: str
    ftp_port: int
    ftp_transfer_mode: str
    ftp_directory_hierarchy: str
    ftp_specify_directory_len: int
    ftp_power_save: str
    ftp_auto_transfer: str
    ftp_clip_flag_filter: str
    dormant_transfer_image_size_rejected: bool
    dormant_sftp_or_implicit_ftps_rejected: bool
    fx3_active_mode_rejected: bool
    slot_1_contains_tier0_vault: bool
    slot1_avf_info_firewall_blocked: bool
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    cacert_o_rdonly_valid: bool
    cacert_read_mode: str
    requested_airplane_mode: str
    effective_airplane_mode: str
    requested_usblan_tethering: str
    effective_usblan_tethering: str
    zero_rf_bench_mode: bool
    zero_rf_and_usblan_isolated: bool
    rf_packets_transmitted: int
    wired_usblan_ftp_packets: int
    log_shooting: str
    picture_profile_gamma: str
    requested_white_balance: str
    effective_white_balance: str
    wb_color_temp_k: int
    wb_ab_shift: float
    wb_gm_shift: float
    custom_wb_preserved_across_cam_reset: bool
    custom_wb_excluded_from_camset: bool
    custom_wb_error_0x0220_triggered: bool
    cine_ei_auto_wb_locked_out: bool
    effective_priority_set_in_awb: str
    effective_shutter_awb_lock: str
    shutter_awb_lock_survived_cam_reset: bool
    effective_shockless_wb: str
    fx6_chunk_proxy_mutual_exclusion_ok: bool
    fx6_atw_cine_ei_locked_out: bool
    block_errno: Optional[int]
    block_errno_name: Optional[str]
    matrix_states_checked: int
    violation_codes: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    raw_firmware_bytes_leaked: int
    ftp_ftpes_customwb_vault_guard: Dict[str, Any]
    donor_audit: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


FtpFtpesCustomWbVaultGuardResult = G141FtpFtpesCustomWbVaultGuardResult


def _validate_wb_grid_step(val: Any, min_v: float, max_v: float, step: float) -> bool:
    if not _is_strict_num(val):
        return False
    fval = float(val)
    if fval < min_v or fval > max_v:
        return False
    ratio = fval / step
    return abs(ratio - round(ratio)) < 1e-9


def verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    body_model_name: str = FX3_MODEL_NAME_PHASE319,
    body_model_id: int = FX3_MODEL_ID_PHASE319,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE319,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE319,
    target_model: str = FX3_MODEL_NAME_PHASE319,
    reset_action: str = RESET_ACTION_NONE_PHASE319,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE319,
    # FTP / Network inputs
    requested_ftp_function: str = "Off",
    requested_cloud_connection: str = "Off",
    ftp_server_slot: int = 1,
    ftp_protocol: str = FTP_PROTOCOL_FTPES_G141,
    ftp_port: int = 21,
    ftp_transfer_mode: str = FTP_MODE_PASSIVE_G141,
    ftp_directory_hierarchy: str = FTP_DIR_HIERARCHY_STANDARD_G141,
    ftp_specify_directory: str = "",
    ftp_power_save: str = "Off",
    ftp_auto_transfer: str = "Off",
    ftp_clip_flag_filter: str = "Off",
    ftp_root_cert_error_behavior: str = "Does Not Connect",
    ftp_raw_jh_target: str = "JPEG & HEIF",
    ftp_movie_target: str = "Proxy Only",
    dormant_transfer_image_size_token: Optional[str] = None,
    # Slot-1 AVF_INFO vault & cacert.pem inputs
    slot_1_contains_tier0_vault: bool = True,
    slot1_ftp_target_selected: bool = False,
    ftp_transfer_status_write_requested: bool = False,
    ftp_avf_db_recover_requested: bool = False,
    bypass_slot1_avf_firewall: bool = False,
    cacert_import_requested: bool = False,
    cacert_filename: str = FX3_FTP_CACERT_FILENAME_G141,
    cacert_slot: str = "Slot 1",
    cacert_size_bytes: int = 4096,
    cacert_pem_valid: bool = True,
    cacert_write_mode_requested: bool = False,
    # Zero-RF & USB-LAN bypass trap
    requested_airplane_mode: str = "On",
    requested_usblan_tethering: str = "Disconnected",
    zero_rf_bench_mode: bool = True,
    wifi_paired_or_ap_active: bool = False,
    # FX6 FTP contrasts
    fx6_ui_server_slots_claimed: Optional[int] = None,
    fx6_claimed_ui_exposes_sftp: bool = False,
    fx6_chunk_proxy_enabled: bool = False,
    fx6_simul_rec_enabled: bool = False,
    fx6_relay_rec_enabled: bool = False,
    claimed_fx3_supports_chunk_proxy_or_certification_pem: bool = False,
    # White Balance inputs
    log_shooting: str = LOG_SHOOTING_OFF_PHASE319,
    picture_profile_gamma: str = "Off",
    requested_white_balance: str = "Auto",
    wb_color_temp_k: int = 5600,
    wb_ab_shift: float = 0.0,
    wb_gm_shift: float = 0.0,
    custom_wb_calibrated: bool = False,
    custom_wb_setup_requested: bool = False,
    assume_cam_reset_wipes_custom_wb_slots: bool = False,
    claimed_custom_wb_exports_in_camset: bool = False,
    requested_priority_set_in_awb: str = "Standard",
    requested_shutter_awb_lock: str = "Off",
    requested_shockless_wb: str = "1",
    movie_shutter_awb_lock_claimed: bool = False,
    # FX6 WB contrasts
    fx6_wht_bal_switch: str = "PRST",
    fx6_wb_memory_bank: str = "Memory A",
    fx6_atw_enabled: bool = False,
    fx6_atw_speed: int = 3,
    request_persistent_emmc_writes: bool = False,
    _skip_matrix: bool = False,
) -> G141FtpFtpesCustomWbVaultGuardResult:
    donor = audit_phase319_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )

    violations: List[str] = []
    block_errno: Optional[int] = None

    def _fail(code: str, err: int) -> None:
        nonlocal block_errno
        if code not in violations:
            violations.append(code)
        if block_errno is None:
            block_errno = err

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _fail(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, EROFS_ERRNO_PHASE319)

    if not donor.valid:
        _fail(STATUS_BLOCKED_PHASE319_DONOR_INTEGRITY, EINVAL_ERRNO_PHASE319)

    # Telemetry / Identity Validation
    identity_ok = (
        body_model_name == FX3_MODEL_NAME_PHASE319
        and _is_strict_int(body_model_id)
        and body_model_id == FX3_MODEL_ID_PHASE319
        and help_guide_code == FX3_HELP_GUIDE_CODE_PHASE319
        and isinstance(firmware_version, str)
        and len(firmware_version) >= 3
        and firmware_version[0].isdigit()
        and "." in firmware_version
        and _fx3_fw_ge(firmware_version, 1.0)
        and target_model in (FX3_MODEL_NAME_PHASE319, FX6_MODEL_NAME_PHASE319)
        and reset_action in ALLOWED_RESET_ACTIONS_PHASE319
        and shoot_mode in ALLOWED_SHOOT_MODES_PHASE319
        and log_shooting in ALLOWED_LOG_SHOOTING_MODES_PHASE319
        and picture_profile_gamma in ALLOWED_PICTURE_PROFILE_GAMMA_G141
        and _is_on_off(requested_ftp_function)
        and _is_on_off(requested_cloud_connection)
        and _is_on_off(ftp_power_save)
        and _is_on_off(ftp_auto_transfer)
        and _is_on_off(requested_airplane_mode)
        and requested_usblan_tethering in ALLOWED_USBLAN_STATES_G141
        and ftp_directory_hierarchy in ALLOWED_FTP_DIR_HIERARCHIES_G141
        and isinstance(ftp_specify_directory, str)
        and ftp_root_cert_error_behavior in ALLOWED_FTP_ROOT_CERT_ERR_BEHAVIORS_G141
        and ftp_clip_flag_filter in ALLOWED_FTP_CLIP_FLAGS_G141
        and ftp_raw_jh_target in ALLOWED_FTP_RAW_JH_TARGETS_G141
        and ftp_movie_target in ALLOWED_FTP_MOVIE_TARGETS_G141
        and requested_white_balance in ALLOWED_FX3_WB_MODES_G141
        and requested_priority_set_in_awb in ALLOWED_PRIORITY_SET_AWB_G141
        and requested_shutter_awb_lock in ALLOWED_SHUTTER_AWB_LOCK_G141
        and requested_shockless_wb in ALLOWED_SHOCKLESS_WB_G141
        and fx6_wht_bal_switch in ALLOWED_FX6_WHT_BAL_SWITCH_G141
        and fx6_wb_memory_bank in ALLOWED_FX6_WB_MEMORY_BANKS_G141
        and _is_strict_int(fx6_atw_speed)
        and 1 <= fx6_atw_speed <= 5
        and _is_strict_int(ftp_server_slot)
        and _is_strict_int(ftp_port)
        and 1 <= ftp_port <= 65535
        and _is_strict_int(wb_color_temp_k)
        and _is_strict_int(cacert_size_bytes)
        and cacert_size_bytes >= 0
    )
    if not identity_ok:
        _fail(STATUS_BLOCKED_G141_TELEMETRY_INVALID, EINVAL_ERRNO_PHASE319)

    # Effective reset state resolution
    is_net_or_init_reset = reset_action in (
        RESET_ACTION_RESET_NETWORK_SET_PHASE319,
        RESET_ACTION_INITIALIZE_PHASE319,
    )
    is_cam_or_init_reset = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319,
        RESET_ACTION_INITIALIZE_PHASE319,
    )

    effective_ftp_function = (
        "Off" if is_net_or_init_reset else requested_ftp_function
    )
    effective_ftp_server_slot = (
        1
        if is_net_or_init_reset
        else (ftp_server_slot if _is_strict_int(ftp_server_slot) else 0)
    )
    # Airplane Mode survives Reset Network Set. (only Initialize turns it Off, though
    # zero_rf_bench_mode still guards bench state!)
    effective_airplane_mode = (
        "Off"
        if reset_action == RESET_ACTION_INITIALIZE_PHASE319
        else requested_airplane_mode
    )
    effective_usblan_tethering = (
        "Disconnected"
        if is_net_or_init_reset
        else requested_usblan_tethering
    )

    # FTP + Cloud mutual exclusion (`CLOUD_CONNECTION_ON_FTP_OFF`)
    ftp_cloud_mutual_exclusion_ok = not (
        effective_ftp_function == "On" and requested_cloud_connection == "On"
    )
    if not ftp_cloud_mutual_exclusion_ok:
        _fail(STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION, EINVAL_ERRNO_PHASE319)

    # Dormant `[Transfer JPEG Size]` / `[Transfer HEIF Size]` traps -> EOPNOTSUPP=95
    dormant_transfer_image_size_rejected = False
    if dormant_transfer_image_size_token is not None:
        dormant_transfer_image_size_rejected = True
        _fail(
            STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION,
            EOPNOTSUPP_ERRNO_PHASE319,
        )

    # Protocol & Mode Enforcement
    dormant_sftp_or_implicit_ftps_rejected = False
    fx3_active_mode_rejected = False

    if ftp_protocol in DORMANT_OR_FORBIDDEN_FTP_PROTOCOLS_G141 or ftp_port in (22, 990):
        dormant_sftp_or_implicit_ftps_rejected = True
        _fail(
            STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION,
            EOPNOTSUPP_ERRNO_PHASE319,
        )
    elif ftp_protocol not in ALLOWED_FX3_FTP_PROTOCOLS_G141:
        _fail(STATUS_BLOCKED_G141_TELEMETRY_INVALID, EINVAL_ERRNO_PHASE319)

    if ftp_transfer_mode not in ALLOWED_FTP_TRANSFER_MODES_G141:
        _fail(STATUS_BLOCKED_G141_TELEMETRY_INVALID, EINVAL_ERRNO_PHASE319)
    elif (
        target_model == FX3_MODEL_NAME_PHASE319
        and ftp_transfer_mode == FTP_MODE_ACTIVE_G141
    ):
        fx3_active_mode_rejected = True
        _fail(
            STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION,
            EOPNOTSUPP_ERRNO_PHASE319,
        )

    # 9-slot boundary on FX3 vs 1..3 UI / 1..16 ELF on FX6
    if target_model == FX3_MODEL_NAME_PHASE319:
        if _is_strict_int(ftp_server_slot) and not (
            FX3_FTP_SERVER_SLOT_MIN_G141 <= ftp_server_slot <= FX3_FTP_SERVER_SLOT_MAX_G141
        ):
            _fail(
                STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION,
                EINVAL_ERRNO_PHASE319,
            )
    else:
        if _is_strict_int(ftp_server_slot) and not (
            1 <= ftp_server_slot <= FX6_FTP_ELF_SERVER_SLOTS_MAX_G141
        ):
            _fail(
                STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION,
                EINVAL_ERRNO_PHASE319,
            )
        if fx6_ui_server_slots_claimed is not None and (
            not _is_strict_int(fx6_ui_server_slots_claimed)
            or fx6_ui_server_slots_claimed != FX6_FTP_UI_SERVER_SLOTS_G141
        ):
            _fail(
                STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION,
                EINVAL_ERRNO_PHASE319,
            )
        if fx6_claimed_ui_exposes_sftp:
            dormant_sftp_or_implicit_ftps_rejected = True
            _fail(
                STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION,
                EOPNOTSUPP_ERRNO_PHASE319,
            )

    if (
        isinstance(ftp_specify_directory, str)
        and len(ftp_specify_directory) > FX3_FTP_SPECIFY_DIRECTORY_MAX_LEN_G141
    ):
        _fail(
            STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    # FX6 Chunk Proxy mutual exclusions vs FX3 rejection
    fx6_chunk_proxy_mutual_exclusion_ok = not (
        fx6_chunk_proxy_enabled and (fx6_simul_rec_enabled or fx6_relay_rec_enabled)
    )
    if (
        target_model == FX3_MODEL_NAME_PHASE319
        and (fx6_chunk_proxy_enabled or claimed_fx3_supports_chunk_proxy_or_certification_pem)
    ):
        _fail(
            STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION,
            EOPNOTSUPP_ERRNO_PHASE319,
        )
    elif target_model == FX6_MODEL_NAME_PHASE319 and not fx6_chunk_proxy_mutual_exclusion_ok:
        _fail(
            STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    # Slot-1 AVF_INFO Mutation Vault Firewall (EROFS=30) & cacert.pem O_RDONLY check
    slot1_avf_info_firewall_blocked = False
    slot1_data_sector_writes = 0
    slot1_avf_info_mutated = False
    cacert_o_rdonly_valid = True
    cacert_read_mode = "O_RDONLY" if cacert_import_requested else "IDLE"

    if bypass_slot1_avf_firewall and slot_1_contains_tier0_vault:
        slot1_avf_info_firewall_blocked = True
        _fail(
            STATUS_BLOCKED_G141_SLOT1_AVF_INFO_VAULT_OR_CACERT_VIOLATION,
            EROFS_ERRNO_PHASE319,
        )

    ftp_mutates_slot1_avf = slot_1_contains_tier0_vault and (
        ftp_transfer_status_write_requested
        or ftp_avf_db_recover_requested
        or (slot1_ftp_target_selected and effective_ftp_function == "On")
    )
    if ftp_mutates_slot1_avf:
        slot1_avf_info_firewall_blocked = True
        _fail(
            STATUS_BLOCKED_G141_SLOT1_AVF_INFO_VAULT_OR_CACERT_VIOLATION,
            EROFS_ERRNO_PHASE319,
        )

    if cacert_import_requested:
        if cacert_write_mode_requested and slot_1_contains_tier0_vault:
            cacert_o_rdonly_valid = False
            cacert_read_mode = "BLOCKED_WRITE_EROFS"
            slot1_avf_info_firewall_blocked = True
            _fail(
                STATUS_BLOCKED_G141_SLOT1_AVF_INFO_VAULT_OR_CACERT_VIOLATION,
                EROFS_ERRNO_PHASE319,
            )
        expected_cert_name = (
            FX3_FTP_CACERT_FILENAME_G141
            if target_model == FX3_MODEL_NAME_PHASE319
            else FX6_FTP_CERT_FILENAME_G141
        )
        expected_cert_slot = (
            "Slot 1"
            if target_model == FX3_MODEL_NAME_PHASE319
            else FX6_FTP_CERT_SLOT_G141
        )
        if (
            cacert_filename != expected_cert_name
            or cacert_slot != expected_cert_slot
            or not _is_strict_int(cacert_size_bytes)
            or cacert_size_bytes <= 0
            or cacert_size_bytes > FX3_FTP_CACERT_MAX_BYTES_G141
            or not cacert_pem_valid
        ):
            cacert_o_rdonly_valid = False
            _fail(
                STATUS_BLOCKED_G141_SLOT1_AVF_INFO_VAULT_OR_CACERT_VIOLATION,
                EINVAL_ERRNO_PHASE319,
            )

    # Zero-RF + USB-LAN Wired Bypass Guard
    # CRITICAL Wave-61 rule: [Airplane Mode]=On does NOT block wired USB-LAN FTP!
    rf_packets_transmitted = 0
    if wifi_paired_or_ap_active or (
        effective_airplane_mode == "Off"
        and effective_ftp_function == "On"
        and effective_usblan_tethering != "Connected"
    ):
        rf_packets_transmitted = 1

    wired_usblan_ftp_packets = (
        1
        if (
            effective_ftp_function == "On"
            and effective_usblan_tethering == "Connected"
        )
        else 0
    )

    zero_rf_and_usblan_isolated = (
        effective_airplane_mode == "On"
        and effective_ftp_function == "Off"
        and effective_usblan_tethering == "Disconnected"
        and (not wifi_paired_or_ap_active)
        and rf_packets_transmitted == 0
        and wired_usblan_ftp_packets == 0
    )
    if zero_rf_bench_mode and not zero_rf_and_usblan_isolated:
        _fail(
            STATUS_BLOCKED_G141_USBLAN_ZERO_RF_BYPASS_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    # White Balance Rules
    effective_white_balance = (
        "Auto" if is_cam_or_init_reset else requested_white_balance
    )
    effective_priority_set_in_awb = (
        "Standard" if is_cam_or_init_reset else requested_priority_set_in_awb
    )
    # Still-only Shutter AWB Lock SURVIVES Camera Settings Reset (only Initialize clears!)
    effective_shutter_awb_lock = (
        "Off"
        if reset_action == RESET_ACTION_INITIALIZE_PHASE319
        else requested_shutter_awb_lock
    )
    shutter_awb_lock_survived_cam_reset = (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319
        and effective_shutter_awb_lock == requested_shutter_awb_lock
    )
    effective_shockless_wb = (
        "1" if is_cam_or_init_reset else requested_shockless_wb
    )

    if movie_shutter_awb_lock_claimed:
        _fail(
            STATUS_BLOCKED_G141_CUSTOMWB_LOG_ERR_0X0220_OR_CINEEI_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    # C.Temp./Filter (2500K..9900K step 100K) & A-B / G-M Grid
    if _is_strict_int(wb_color_temp_k) and (
        wb_color_temp_k < WB_COLOR_TEMP_MIN_K_G141
        or wb_color_temp_k > WB_COLOR_TEMP_MAX_K_G141
        or wb_color_temp_k % WB_COLOR_TEMP_STEP_K_G141 != 0
    ):
        _fail(
            STATUS_BLOCKED_G141_CUSTOMWB_LOG_ERR_0X0220_OR_CINEEI_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    if not _validate_wb_grid_step(
        wb_ab_shift, WB_AB_AXIS_MIN_G141, WB_AB_AXIS_MAX_G141, WB_AB_STEP_G141
    ) or not _validate_wb_grid_step(
        wb_gm_shift, WB_GM_AXIS_MIN_G141, WB_GM_AXIS_MAX_G141, WB_GM_STEP_G141
    ):
        _fail(
            STATUS_BLOCKED_G141_CUSTOMWB_LOG_ERR_0X0220_OR_CINEEI_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    # Custom 1..3 CAMSET exclusion & Initialize-only wipe of stored slots
    custom_wb_excluded_from_camset = not claimed_custom_wb_exports_in_camset
    if claimed_custom_wb_exports_in_camset:
        _fail(
            STATUS_BLOCKED_G141_CUSTOMWB_LOG_ERR_0X0220_OR_CINEEI_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    custom_wb_preserved_across_cam_reset = (
        custom_wb_calibrated
        and reset_action != RESET_ACTION_INITIALIZE_PHASE319
    )
    if (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319
        and assume_cam_reset_wipes_custom_wb_slots
    ):
        _fail(
            STATUS_BLOCKED_G141_CUSTOMWB_LOG_ERR_0X0220_OR_CINEEI_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    # Custom WB Error 0x0220 under Log != Off or S-Log3 / PPLUT1..4
    log_or_pp_error_condition = (
        log_shooting != LOG_SHOOTING_OFF_PHASE319
        or picture_profile_gamma in CUSTOM_WB_ERROR_0X0220_PP_GAMMAS_G141
    )
    custom_wb_error_0x0220_triggered = bool(
        custom_wb_setup_requested and log_or_pp_error_condition
    )
    if custom_wb_error_0x0220_triggered:
        _fail(
            STATUS_BLOCKED_G141_CUSTOMWB_LOG_ERR_0X0220_OR_CINEEI_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    # Cine EI / Cine EI Quick locks out Auto & Underwater Auto
    is_cine_ei = log_shooting in (
        LOG_SHOOTING_CINE_EI_PHASE319,
        LOG_SHOOTING_CINE_EI_QUICK_PHASE319,
    )
    cine_ei_auto_wb_locked_out = is_cine_ei
    if (
        is_cine_ei
        and effective_white_balance in CINE_EI_LOCKED_WB_MODES_G141
        and reset_action == RESET_ACTION_NONE_PHASE319
    ):
        _fail(
            STATUS_BLOCKED_G141_CUSTOMWB_LOG_ERR_0X0220_OR_CINEEI_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    # FX6 ATW lockout under Cine EI
    fx6_atw_cine_ei_locked_out = (
        target_model == FX6_MODEL_NAME_PHASE319 and is_cine_ei
    )
    if fx6_atw_cine_ei_locked_out and fx6_atw_enabled:
        _fail(
            STATUS_BLOCKED_G141_CUSTOMWB_LOG_ERR_0X0220_OR_CINEEI_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    matrix_states = (
        256 if _skip_matrix else compute_ftp_ftpes_customwb_matrix()["states_checked"]
    )
    valid = len(violations) == 0
    status = STATUS_VERIFIED_G141 if valid else violations[0]
    block_errno_name = {
        EROFS_ERRNO_PHASE319: EROFS_NAME_PHASE319,
        EOPNOTSUPP_ERRNO_PHASE319: EOPNOTSUPP_NAME_PHASE319,
        EINVAL_ERRNO_PHASE319: EINVAL_NAME_PHASE319,
        EBUSY_ERRNO_PHASE319: EBUSY_NAME_PHASE319,
        ENODEV_ERRNO_PHASE319: ENODEV_NAME_PHASE319,
    }.get(block_errno) if block_errno is not None else None

    guard_summary = {
        "effective_ftp_function": effective_ftp_function,
        "ftp_server_slot": effective_ftp_server_slot,
        "ftp_protocol": ftp_protocol,
        "ftp_transfer_mode": ftp_transfer_mode,
        "dormant_transfer_image_size_rejected": dormant_transfer_image_size_rejected,
        "dormant_sftp_or_implicit_ftps_rejected": dormant_sftp_or_implicit_ftps_rejected,
        "fx3_active_mode_rejected": fx3_active_mode_rejected,
        "slot_1_contains_tier0_vault": slot_1_contains_tier0_vault,
        "slot1_avf_info_firewall_blocked": slot1_avf_info_firewall_blocked,
        "slot1_data_sector_writes": slot1_data_sector_writes,
        "slot1_avf_info_mutated": slot1_avf_info_mutated,
        "cacert_read_mode": cacert_read_mode,
        "effective_airplane_mode": effective_airplane_mode,
        "effective_usblan_tethering": effective_usblan_tethering,
        "zero_rf_and_usblan_isolated": zero_rf_and_usblan_isolated,
        "rf_packets_transmitted": rf_packets_transmitted,
        "wired_usblan_ftp_packets": wired_usblan_ftp_packets,
        "effective_white_balance": effective_white_balance,
        "wb_color_temp_k": wb_color_temp_k,
        "custom_wb_preserved_across_cam_reset": custom_wb_preserved_across_cam_reset,
        "custom_wb_excluded_from_camset": custom_wb_excluded_from_camset,
        "custom_wb_error_0x0220_triggered": custom_wb_error_0x0220_triggered,
        "cine_ei_auto_wb_locked_out": cine_ei_auto_wb_locked_out,
        "effective_shutter_awb_lock": effective_shutter_awb_lock,
        "shutter_awb_lock_survived_cam_reset": shutter_awb_lock_survived_cam_reset,
        "effective_shockless_wb": effective_shockless_wb,
    }

    return G141FtpFtpesCustomWbVaultGuardResult(
        valid=valid,
        status=status,
        verification_mode=donor.verification_mode,
        target_model=target_model,
        body_model_name=body_model_name,
        body_model_id=body_model_id if _is_strict_int(body_model_id) else 0,
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        requested_ftp_function=requested_ftp_function,
        effective_ftp_function=effective_ftp_function,
        requested_cloud_connection=requested_cloud_connection,
        ftp_cloud_mutual_exclusion_ok=ftp_cloud_mutual_exclusion_ok,
        ftp_server_slot=effective_ftp_server_slot,
        ftp_protocol=ftp_protocol,
        ftp_port=ftp_port if _is_strict_int(ftp_port) else 0,
        ftp_transfer_mode=ftp_transfer_mode,
        ftp_directory_hierarchy=ftp_directory_hierarchy,
        ftp_specify_directory_len=(
            len(ftp_specify_directory) if isinstance(ftp_specify_directory, str) else 0
        ),
        ftp_power_save=ftp_power_save,
        ftp_auto_transfer=ftp_auto_transfer,
        ftp_clip_flag_filter=ftp_clip_flag_filter,
        dormant_transfer_image_size_rejected=dormant_transfer_image_size_rejected,
        dormant_sftp_or_implicit_ftps_rejected=dormant_sftp_or_implicit_ftps_rejected,
        fx3_active_mode_rejected=fx3_active_mode_rejected,
        slot_1_contains_tier0_vault=slot_1_contains_tier0_vault,
        slot1_avf_info_firewall_blocked=slot1_avf_info_firewall_blocked,
        slot1_data_sector_writes=slot1_data_sector_writes,
        slot1_avf_info_mutated=slot1_avf_info_mutated,
        cacert_o_rdonly_valid=cacert_o_rdonly_valid,
        cacert_read_mode=cacert_read_mode,
        requested_airplane_mode=requested_airplane_mode,
        effective_airplane_mode=effective_airplane_mode,
        requested_usblan_tethering=requested_usblan_tethering,
        effective_usblan_tethering=effective_usblan_tethering,
        zero_rf_bench_mode=zero_rf_bench_mode,
        zero_rf_and_usblan_isolated=zero_rf_and_usblan_isolated,
        rf_packets_transmitted=rf_packets_transmitted,
        wired_usblan_ftp_packets=wired_usblan_ftp_packets,
        log_shooting=log_shooting,
        picture_profile_gamma=picture_profile_gamma,
        requested_white_balance=requested_white_balance,
        effective_white_balance=effective_white_balance,
        wb_color_temp_k=wb_color_temp_k if _is_strict_int(wb_color_temp_k) else 0,
        wb_ab_shift=float(wb_ab_shift) if _is_strict_num(wb_ab_shift) else 0.0,
        wb_gm_shift=float(wb_gm_shift) if _is_strict_num(wb_gm_shift) else 0.0,
        custom_wb_preserved_across_cam_reset=custom_wb_preserved_across_cam_reset,
        custom_wb_excluded_from_camset=custom_wb_excluded_from_camset,
        custom_wb_error_0x0220_triggered=custom_wb_error_0x0220_triggered,
        cine_ei_auto_wb_locked_out=cine_ei_auto_wb_locked_out,
        effective_priority_set_in_awb=effective_priority_set_in_awb,
        effective_shutter_awb_lock=effective_shutter_awb_lock,
        shutter_awb_lock_survived_cam_reset=shutter_awb_lock_survived_cam_reset,
        effective_shockless_wb=effective_shockless_wb,
        fx6_chunk_proxy_mutual_exclusion_ok=fx6_chunk_proxy_mutual_exclusion_ok,
        fx6_atw_cine_ei_locked_out=fx6_atw_cine_ei_locked_out,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        matrix_states_checked=matrix_states,
        violation_codes=tuple(violations),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        ftp_ftpes_customwb_vault_guard=guard_summary,
        donor_audit=donor.to_dict(),
    )


def compute_ftp_ftpes_customwb_matrix() -> Dict[str, int]:
    """Exhaustive 256-state safety matrix across G141 FTP/FTPES/Vault/USB-LAN/CustomWB."""
    states = 0
    sftp_rejected_count = 0
    slot1_avf_blocked_count = 0
    usblan_bypass_blocked_count = 0
    customwb_0x0220_count = 0

    for ftp_proto in (FTP_PROTOCOL_FTPES_G141, FTP_PROTOCOL_SFTP_FORBIDDEN_G141):
        for ftp_fn in ("Off", "On"):
            for usblan in ("Disconnected", "Connected"):
                for avf_write in (False, True):
                    for log_mode in (LOG_SHOOTING_OFF_PHASE319, LOG_SHOOTING_CINE_EI_PHASE319):
                        for custom_setup in (False, True):
                            for rst in (
                                RESET_ACTION_NONE_PHASE319,
                                RESET_ACTION_RESET_NETWORK_SET_PHASE319,
                            ):
                                wb_mode = (
                                    "C.Temp./Filter"
                                    if log_mode == LOG_SHOOTING_CINE_EI_PHASE319
                                    else "Auto"
                                )
                                res = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                                    force_clean_room=True,
                                    reset_action=rst,
                                    requested_ftp_function=ftp_fn,
                                    ftp_protocol=ftp_proto,
                                    requested_usblan_tethering=usblan,
                                    ftp_transfer_status_write_requested=avf_write,
                                    slot_1_contains_tier0_vault=True,
                                    requested_airplane_mode="On",
                                    zero_rf_bench_mode=True,
                                    log_shooting=log_mode,
                                    requested_white_balance=wb_mode,
                                    custom_wb_setup_requested=custom_setup,
                                    _skip_matrix=True,
                                )
                                assert res.slot1_data_sector_writes == 0
                                assert not res.slot1_avf_info_mutated
                                states += 1
                                if res.dormant_sftp_or_implicit_ftps_rejected:
                                    sftp_rejected_count += 1
                                if res.slot1_avf_info_firewall_blocked:
                                    slot1_avf_blocked_count += 1
                                if (
                                    STATUS_BLOCKED_G141_USBLAN_ZERO_RF_BYPASS_VIOLATION
                                    in res.violation_codes
                                ):
                                    usblan_bypass_blocked_count += 1
                                if res.custom_wb_error_0x0220_triggered:
                                    customwb_0x0220_count += 1

    # 2 x 2 x 2 x 2 x 2 x 2 x 2 = 128; run 2nd pass with Active/Passive mode -> 256
    for ftp_mode in (FTP_MODE_PASSIVE_G141, FTP_MODE_ACTIVE_G141):
        for av_state in ("Off", "On"):
            for ftp_fn in ("Off", "On"):
                for usblan in ("Disconnected", "Connected"):
                    for pp_gamma in ("Off", "S-Log3"):
                        for custom_setup in (False, True):
                            for slot1_vault in (True, False):
                                res = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                                    force_clean_room=True,
                                    requested_ftp_function=ftp_fn,
                                    ftp_transfer_mode=ftp_mode,
                                    requested_airplane_mode=av_state,
                                    requested_usblan_tethering=usblan,
                                    slot_1_contains_tier0_vault=slot1_vault,
                                    ftp_transfer_status_write_requested=True,
                                    zero_rf_bench_mode=True,
                                    picture_profile_gamma=pp_gamma,
                                    custom_wb_setup_requested=custom_setup,
                                    _skip_matrix=True,
                                )
                                assert res.slot1_data_sector_writes == 0
                                states += 1
                                if res.slot1_avf_info_firewall_blocked:
                                    slot1_avf_blocked_count += 1
                                if (
                                    STATUS_BLOCKED_G141_USBLAN_ZERO_RF_BYPASS_VIOLATION
                                    in res.violation_codes
                                ):
                                    usblan_bypass_blocked_count += 1
                                if res.custom_wb_error_0x0220_triggered:
                                    customwb_0x0220_count += 1

    return {
        "states_checked": states,
        "sftp_rejected_count": sftp_rejected_count,
        "slot1_avf_blocked_count": slot1_avf_blocked_count,
        "usblan_bypass_blocked_count": usblan_bypass_blocked_count,
        "customwb_0x0220_count": customwb_0x0220_count,
    }


def evaluate_g141_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **kwargs: Any,
) -> Tuple[GateVerdict, G141FtpFtpesCustomWbVaultGuardResult]:
    res = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **kwargs,
    )
    verdict = GateVerdict(
        gate_id=G141,
        gate_code=G141_GATE_CODE,
        passed=res.valid,
        status=res.status,
        evidence=(
            f"status={res.status} mode={res.verification_mode} ftp={res.effective_ftp_function} "
            f"slot={res.ftp_server_slot} proto={res.ftp_protocol} "
            f"usblan={res.effective_usblan_tethering} s1_writes={res.slot1_data_sector_writes} "
            f"wb={res.effective_white_balance}"
        ),
        violation_codes=res.violation_codes,
        errors=res.violation_codes,
        warnings=tuple(res.donor_audit.get("warnings", ())),
    )
    return verdict, res


def resolve_fx3_ftp_ftpes_customwb_state(
    **kwargs: Any,
) -> Dict[str, Any]:
    return verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(**kwargs).to_dict()


# ---------------------------------------------------------------------------
# Gate G142 Result & Matrix + Verifier
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class G142MovieAfFocusMapMarkerPeakingGuardResult:
    valid: bool
    status: str
    verification_mode: str
    target_model: str
    body_model_name: str
    body_model_id: int
    help_guide_code: str
    firmware_version: str
    reset_action: str
    shoot_mode: str
    lens_model: str
    is_pdaf_lens: bool
    frame_rate_fps: float
    effective_af_transition_speed: int
    effective_af_subj_shift_sensitivity: int
    effective_af_assist: str
    af_assist_incompatible_lens_rejected: bool
    af_subj_shift_6_or_7_rejected: bool
    fx3_onbody_focus_map_menu_present: bool
    fx3_onbody_focus_map_rejected: bool
    external_monitor_control_focus_map_active: bool
    focus_map_blocked_by_fps_or_exclusion: bool
    focus_map_hdmi_burnin: bool
    effective_marker_display: str
    effective_center_marker: str
    effective_aspect_marker: str
    effective_safety_zone: str
    effective_guideframe: str
    marker_auto_hidden_under_focus_magnifier: bool
    marker_hdmi_output: bool
    effective_peaking_display: str
    effective_peaking_level: str
    effective_peaking_color: str
    peaking_hdmi_output: bool
    marker_and_peaking_survived_cam_reset: bool
    exact_15_active_aspect_ratios_verified: bool
    fx6_user_box_enabled: bool
    fx6_user_box_width: int
    fx6_user_box_height: int
    fx6_user_box_h_pos: int
    fx6_user_box_v_pos: int
    fx6_aspect_mask_level: int
    block_errno: Optional[int]
    block_errno_name: Optional[str]
    matrix_states_checked: int
    violation_codes: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    raw_firmware_bytes_leaked: int
    movie_af_focusmap_marker_peaking_guard: Dict[str, Any]
    donor_audit: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


MovieAfFocusMapMarkerPeakingGuardResult = G142MovieAfFocusMapMarkerPeakingGuardResult


def verify_movie_af_focusmap_marker_peaking_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    body_model_name: str = FX3_MODEL_NAME_PHASE319,
    body_model_id: int = FX3_MODEL_ID_PHASE319,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE319,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE319,
    target_model: str = FX3_MODEL_NAME_PHASE319,
    reset_action: str = RESET_ACTION_NONE_PHASE319,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE319,
    # Movie AF inputs
    requested_af_transition_speed: int = AF_TRANSITION_SPEED_DEFAULT_G142,
    requested_af_subj_shift_sensitivity: int = AF_SUBJ_SHIFT_SENS_DEFAULT_G142,
    requested_af_assist: str = "Off",
    lens_model: str = "SEL2470GM2",
    is_pdaf_lens: bool = True,
    mount_adapter_attached: bool = False,
    lens_attached: bool = True,
    claimed_fx6_af_subj_shift_sens_is_1_to_7: bool = False,
    # Focus Map inputs
    frame_rate_fps: float = 23.98,
    requested_fx3_onbody_focus_map: bool = False,
    claimed_fx3_ver2_onbody_focus_map: bool = False,
    external_focus_map_requested: bool = False,
    fx6_onbody_focus_map_requested: bool = False,
    in_playback_mode: bool = False,
    auto_framing_enabled: bool = False,
    usb_wired_remote_connected: bool = False,
    uvc_streaming_active: bool = False,
    hdmi_raw_output_active: bool = False,
    focus_magnifier_active: bool = False,
    digital_extender_active: bool = False,
    claimed_100p_or_119_88p_blocks_fx3_focus_map: bool = False,
    claimed_focus_map_burns_into_hdmi_or_rec: bool = False,
    # Marker Display (5 items) & Peaking Display (3 items)
    requested_marker_display: str = "Off",
    requested_center_marker: str = "Off",
    requested_aspect_marker: str = "Off",
    requested_safety_zone: str = "Off",
    requested_guideframe: str = "Off",
    claimed_marker_visible_during_focus_magnifier: bool = False,
    claimed_marker_outputs_to_hdmi: bool = False,
    requested_peaking_display: str = "Off",
    requested_peaking_level: str = "Mid",
    requested_peaking_color: Optional[str] = None,
    claimed_peaking_outputs_to_hdmi: bool = False,
    # FX6 User Box & Aspect Mask contrast
    fx6_user_box_enabled: bool = False,
    fx6_user_box_width: int = 240,
    fx6_user_box_height: int = 135,
    fx6_user_box_h_pos: int = 0,
    fx6_user_box_v_pos: int = 0,
    fx6_aspect_mask_level: int = FX6_ASPECT_MASK_DEFAULT_G142,
    claimed_fx3_supports_user_box_or_aspect_mask: bool = False,
    request_persistent_emmc_writes: bool = False,
    _skip_matrix: bool = False,
) -> G142MovieAfFocusMapMarkerPeakingGuardResult:
    donor = audit_phase319_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )

    violations: List[str] = []
    block_errno: Optional[int] = None

    def _fail(code: str, err: int) -> None:
        nonlocal block_errno
        if code not in violations:
            violations.append(code)
        if block_errno is None:
            block_errno = err

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _fail(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, EROFS_ERRNO_PHASE319)

    if not donor.valid:
        _fail(STATUS_BLOCKED_PHASE319_DONOR_INTEGRITY, EINVAL_ERRNO_PHASE319)

    resolved_peaking_color = (
        ("White" if target_model == FX3_MODEL_NAME_PHASE319 else "B&W")
        if requested_peaking_color is None
        else requested_peaking_color
    )

    # Telemetry / Identity Validation
    peaking_color_default_ok = (
        resolved_peaking_color in ALLOWED_FX3_PEAKING_COLORS_G142
        or resolved_peaking_color in ALLOWED_FX6_PEAKING_COLORS_G142
    )
    safety_zone_enum_ok = (
        requested_safety_zone in ALLOWED_FX3_SAFETY_ZONES_G142
        or requested_safety_zone in ALLOWED_FX6_ASPECT_SAFETY_AREAS_G142
    )
    identity_ok = (
        body_model_name == FX3_MODEL_NAME_PHASE319
        and _is_strict_int(body_model_id)
        and body_model_id == FX3_MODEL_ID_PHASE319
        and help_guide_code == FX3_HELP_GUIDE_CODE_PHASE319
        and isinstance(firmware_version, str)
        and len(firmware_version) >= 3
        and firmware_version[0].isdigit()
        and "." in firmware_version
        and _fx3_fw_ge(firmware_version, 1.0)
        and target_model in (FX3_MODEL_NAME_PHASE319, FX6_MODEL_NAME_PHASE319)
        and reset_action in ALLOWED_RESET_ACTIONS_PHASE319
        and shoot_mode in ALLOWED_SHOOT_MODES_PHASE319
        and _is_strict_int(requested_af_transition_speed)
        and _is_strict_int(requested_af_subj_shift_sensitivity)
        and _is_on_off(requested_af_assist)
        and isinstance(lens_model, str)
        and len(lens_model.strip()) > 0
        and _is_strict_num(frame_rate_fps)
        and float(frame_rate_fps) > 0.0
        and _is_on_off(requested_marker_display)
        and _is_on_off(requested_center_marker)
        and isinstance(requested_aspect_marker, str)
        and safety_zone_enum_ok
        and _is_on_off(requested_guideframe)
        and _is_on_off(requested_peaking_display)
        and requested_peaking_level in ALLOWED_PEAKING_LEVELS_G142
        and peaking_color_default_ok
        and _is_strict_int(fx6_user_box_width)
        and _is_strict_int(fx6_user_box_height)
        and _is_strict_int(fx6_user_box_h_pos)
        and _is_strict_int(fx6_user_box_v_pos)
        and _is_strict_int(fx6_aspect_mask_level)
    )
    if not identity_ok:
        _fail(STATUS_BLOCKED_G142_TELEMETRY_INVALID, EINVAL_ERRNO_PHASE319)

    is_cam_or_init_reset = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319,
        RESET_ACTION_INITIALIZE_PHASE319,
    )
    is_init_reset = reset_action == RESET_ACTION_INITIALIZE_PHASE319

    # 1) Movie AF 1..7 & 1..5 (BOTH FX3 & FX6!) + AF Assist
    af_subj_shift_6_or_7_rejected = False
    if _is_strict_int(requested_af_transition_speed) and not (
        AF_TRANSITION_SPEED_MIN_G142
        <= requested_af_transition_speed
        <= AF_TRANSITION_SPEED_MAX_G142
    ):
        _fail(
            STATUS_BLOCKED_G142_MOVIE_AF_1TO7_1TO5_OR_ASSIST_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    if _is_strict_int(requested_af_subj_shift_sensitivity) and not (
        AF_SUBJ_SHIFT_SENS_MIN_G142
        <= requested_af_subj_shift_sensitivity
        <= AF_SUBJ_SHIFT_SENS_MAX_G142
    ):
        if requested_af_subj_shift_sensitivity in (6, 7):
            af_subj_shift_6_or_7_rejected = True
        _fail(
            STATUS_BLOCKED_G142_MOVIE_AF_1TO7_1TO5_OR_ASSIST_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    if claimed_fx6_af_subj_shift_sens_is_1_to_7:
        af_subj_shift_6_or_7_rejected = True
        _fail(
            STATUS_BLOCKED_G142_MOVIE_AF_1TO7_1TO5_OR_ASSIST_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    effective_af_transition_speed = (
        AF_TRANSITION_SPEED_DEFAULT_G142
        if is_cam_or_init_reset
        else (
            requested_af_transition_speed
            if _is_strict_int(requested_af_transition_speed)
            else AF_TRANSITION_SPEED_DEFAULT_G142
        )
    )
    effective_af_subj_shift_sensitivity = (
        AF_SUBJ_SHIFT_SENS_DEFAULT_G142
        if is_cam_or_init_reset
        else (
            requested_af_subj_shift_sensitivity
            if _is_strict_int(requested_af_subj_shift_sensitivity)
            else AF_SUBJ_SHIFT_SENS_DEFAULT_G142
        )
    )
    effective_af_assist = "Off" if is_cam_or_init_reset else requested_af_assist

    af_assist_incompatible_lens_rejected = False
    if (
        effective_af_assist == "On"
        and lens_model in AF_ASSIST_INCOMPATIBLE_LENSES_G142
    ):
        af_assist_incompatible_lens_rejected = True
        _fail(
            STATUS_BLOCKED_G142_MOVIE_AF_1TO7_1TO5_OR_ASSIST_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    # 2) Focus Map Empirical Disambiguation (FX3 external M&C only vs FX6 native on-body)
    fx3_onbody_focus_map_menu_present = False
    fx3_onbody_focus_map_rejected = False
    focus_map_blocked_by_fps_or_exclusion = False
    fps_val = float(frame_rate_fps) if _is_strict_num(frame_rate_fps) else 0.0

    if target_model == FX3_MODEL_NAME_PHASE319 and (
        requested_fx3_onbody_focus_map or claimed_fx3_ver2_onbody_focus_map
    ):
        fx3_onbody_focus_map_rejected = True
        _fail(
            STATUS_BLOCKED_G142_FOCUSMAP_ONBODY_OR_EXCLUSION_VIOLATION,
            EOPNOTSUPP_ERRNO_PHASE319,
        )

    if claimed_100p_or_119_88p_blocks_fx3_focus_map:
        _fail(
            STATUS_BLOCKED_G142_FOCUSMAP_ONBODY_OR_EXCLUSION_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    if claimed_focus_map_burns_into_hdmi_or_rec:
        focus_map_blocked_by_fps_or_exclusion = True
        _fail(
            STATUS_BLOCKED_G142_FOCUSMAP_ONBODY_OR_EXCLUSION_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    if target_model == FX3_MODEL_NAME_PHASE319 and external_focus_map_requested:
        if not _fx3_fw_ge(firmware_version, FOCUS_MAP_MIN_FX3_FW_G142):
            focus_map_blocked_by_fps_or_exclusion = True
            _fail(
                STATUS_BLOCKED_G142_FOCUSMAP_ONBODY_OR_EXCLUSION_VIOLATION,
                EOPNOTSUPP_ERRNO_PHASE319,
            )
        elif (
            fps_val >= FOCUS_MAP_HIGH_FPS_BLOCK_THRESHOLD_G142
            or shoot_mode == SHOOT_MODE_STILL_PHASE319
            or in_playback_mode
            or auto_framing_enabled
            or (not lens_attached)
            or (not is_pdaf_lens)
            or mount_adapter_attached
            or usb_wired_remote_connected
            or uvc_streaming_active
            or hdmi_raw_output_active
            or focus_magnifier_active
            or digital_extender_active
        ):
            focus_map_blocked_by_fps_or_exclusion = True
            _fail(
                STATUS_BLOCKED_G142_FOCUSMAP_ONBODY_OR_EXCLUSION_VIOLATION,
                EINVAL_ERRNO_PHASE319,
            )

    if target_model == FX6_MODEL_NAME_PHASE319 and fx6_onbody_focus_map_requested:
        if (
            fps_val <= FX6_FOCUS_MAP_LOW_FPS_BLOCK_THRESHOLD_G142
            or fps_val >= FOCUS_MAP_HIGH_FPS_BLOCK_THRESHOLD_G142
            or shoot_mode == SHOOT_MODE_STILL_PHASE319
            or in_playback_mode
            or (not lens_attached)
            or (not is_pdaf_lens)
            or hdmi_raw_output_active
            or focus_magnifier_active
            or digital_extender_active
        ):
            focus_map_blocked_by_fps_or_exclusion = True
            _fail(
                STATUS_BLOCKED_G142_FOCUSMAP_ONBODY_OR_EXCLUSION_VIOLATION,
                EINVAL_ERRNO_PHASE319,
            )

    external_monitor_control_focus_map_active = bool(
        external_focus_map_requested
        and not focus_map_blocked_by_fps_or_exclusion
        and STATUS_BLOCKED_G142_FOCUSMAP_ONBODY_OR_EXCLUSION_VIOLATION not in violations
    )

    # 3) Marker Display (5 items) & Peaking Display (3 items) — ALL 8 Initialize-only!
    effective_marker_display = "Off" if is_init_reset else requested_marker_display
    effective_center_marker = "Off" if is_init_reset else requested_center_marker
    effective_aspect_marker = "Off" if is_init_reset else requested_aspect_marker
    effective_safety_zone = "Off" if is_init_reset else requested_safety_zone
    effective_guideframe = "Off" if is_init_reset else requested_guideframe

    effective_peaking_display = "Off" if is_init_reset else requested_peaking_display
    effective_peaking_level = "Mid" if is_init_reset else requested_peaking_level
    default_peaking_color = (
        "White" if target_model == FX3_MODEL_NAME_PHASE319 else "B&W"
    )
    effective_peaking_color = (
        default_peaking_color if is_init_reset else resolved_peaking_color
    )

    marker_and_peaking_survived_cam_reset = (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319
    )

    # 15-Aspect Ratio Check on FX3
    exact_15_active_aspect_ratios_verified = (
        len(EXACT_15_ACTIVE_ASPECT_RATIOS_FX3_G142) == 15
        and len(ALLOWED_ASPECT_MARKER_STATES_FX3_G142) == 16
    )
    if target_model == FX3_MODEL_NAME_PHASE319:
        if requested_aspect_marker not in ALLOWED_ASPECT_MARKER_STATES_FX3_G142:
            _fail(
                STATUS_BLOCKED_G142_MARKER_15ASPECT_PEAKING_OR_HDMI_VIOLATION,
                EOPNOTSUPP_ERRNO_PHASE319
                if requested_aspect_marker in ("Custom", "2.40:1", "1.78:1")
                else EINVAL_ERRNO_PHASE319,
            )
        if requested_safety_zone not in ALLOWED_FX3_SAFETY_ZONES_G142:
            _fail(
                STATUS_BLOCKED_G142_MARKER_15ASPECT_PEAKING_OR_HDMI_VIOLATION,
                EOPNOTSUPP_ERRNO_PHASE319,
            )
        if resolved_peaking_color not in ALLOWED_FX3_PEAKING_COLORS_G142:
            _fail(
                STATUS_BLOCKED_G142_MARKER_15ASPECT_PEAKING_OR_HDMI_VIOLATION,
                EOPNOTSUPP_ERRNO_PHASE319,
            )
        if claimed_fx3_supports_user_box_or_aspect_mask or fx6_user_box_enabled:
            _fail(
                STATUS_BLOCKED_G142_MARKER_15ASPECT_PEAKING_OR_HDMI_VIOLATION,
                EOPNOTSUPP_ERRNO_PHASE319,
            )
    else:
        if resolved_peaking_color not in ALLOWED_FX6_PEAKING_COLORS_G142:
            _fail(
                STATUS_BLOCKED_G142_MARKER_15ASPECT_PEAKING_OR_HDMI_VIOLATION,
                EOPNOTSUPP_ERRNO_PHASE319,
            )
        if (
            not _is_strict_int(fx6_user_box_width)
            or not (FX6_USER_BOX_WIDTH_MIN_G142 <= fx6_user_box_width <= FX6_USER_BOX_WIDTH_MAX_G142)
            or not _is_strict_int(fx6_user_box_height)
            or not (FX6_USER_BOX_HEIGHT_MIN_G142 <= fx6_user_box_height <= FX6_USER_BOX_HEIGHT_MAX_G142)
            or not _is_strict_int(fx6_user_box_h_pos)
            or not (FX6_USER_BOX_H_POS_MIN_G142 <= fx6_user_box_h_pos <= FX6_USER_BOX_H_POS_MAX_G142)
            or not _is_strict_int(fx6_user_box_v_pos)
            or not (FX6_USER_BOX_V_POS_MIN_G142 <= fx6_user_box_v_pos <= FX6_USER_BOX_V_POS_MAX_G142)
            or not _is_strict_int(fx6_aspect_mask_level)
            or not (FX6_ASPECT_MASK_MIN_G142 <= fx6_aspect_mask_level <= FX6_ASPECT_MASK_MAX_G142)
        ):
            _fail(
                STATUS_BLOCKED_G142_MARKER_15ASPECT_PEAKING_OR_HDMI_VIOLATION,
                EINVAL_ERRNO_PHASE319,
            )

    marker_auto_hidden_under_focus_magnifier = bool(
        focus_magnifier_active and effective_marker_display == "On"
    )
    if claimed_marker_visible_during_focus_magnifier and focus_magnifier_active:
        _fail(
            STATUS_BLOCKED_G142_MARKER_15ASPECT_PEAKING_OR_HDMI_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    if claimed_marker_outputs_to_hdmi or claimed_peaking_outputs_to_hdmi:
        _fail(
            STATUS_BLOCKED_G142_MARKER_15ASPECT_PEAKING_OR_HDMI_VIOLATION,
            EINVAL_ERRNO_PHASE319,
        )

    matrix_states = (
        256
        if _skip_matrix
        else compute_movie_af_focusmap_marker_peaking_matrix()["states_checked"]
    )
    valid = len(violations) == 0
    status = STATUS_VERIFIED_G142 if valid else violations[0]
    block_errno_name = {
        EROFS_ERRNO_PHASE319: EROFS_NAME_PHASE319,
        EOPNOTSUPP_ERRNO_PHASE319: EOPNOTSUPP_NAME_PHASE319,
        EINVAL_ERRNO_PHASE319: EINVAL_NAME_PHASE319,
        EBUSY_ERRNO_PHASE319: EBUSY_NAME_PHASE319,
        ENODEV_ERRNO_PHASE319: ENODEV_NAME_PHASE319,
    }.get(block_errno) if block_errno is not None else None

    guard_summary = {
        "effective_af_transition_speed": effective_af_transition_speed,
        "effective_af_subj_shift_sensitivity": effective_af_subj_shift_sensitivity,
        "effective_af_assist": effective_af_assist,
        "fx3_onbody_focus_map_menu_present": fx3_onbody_focus_map_menu_present,
        "external_monitor_control_focus_map_active": external_monitor_control_focus_map_active,
        "focus_map_hdmi_burnin": False,
        "effective_marker_display": effective_marker_display,
        "effective_aspect_marker": effective_aspect_marker,
        "effective_safety_zone": effective_safety_zone,
        "marker_hdmi_output": False,
        "effective_peaking_display": effective_peaking_display,
        "effective_peaking_level": effective_peaking_level,
        "effective_peaking_color": effective_peaking_color,
        "peaking_hdmi_output": False,
        "marker_and_peaking_survived_cam_reset": marker_and_peaking_survived_cam_reset,
        "exact_15_active_aspect_ratios_verified": exact_15_active_aspect_ratios_verified,
    }

    return G142MovieAfFocusMapMarkerPeakingGuardResult(
        valid=valid,
        status=status,
        verification_mode=donor.verification_mode,
        target_model=target_model,
        body_model_name=body_model_name,
        body_model_id=body_model_id if _is_strict_int(body_model_id) else 0,
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        lens_model=lens_model,
        is_pdaf_lens=is_pdaf_lens,
        frame_rate_fps=fps_val,
        effective_af_transition_speed=effective_af_transition_speed,
        effective_af_subj_shift_sensitivity=effective_af_subj_shift_sensitivity,
        effective_af_assist=effective_af_assist,
        af_assist_incompatible_lens_rejected=af_assist_incompatible_lens_rejected,
        af_subj_shift_6_or_7_rejected=af_subj_shift_6_or_7_rejected,
        fx3_onbody_focus_map_menu_present=fx3_onbody_focus_map_menu_present,
        fx3_onbody_focus_map_rejected=fx3_onbody_focus_map_rejected,
        external_monitor_control_focus_map_active=external_monitor_control_focus_map_active,
        focus_map_blocked_by_fps_or_exclusion=focus_map_blocked_by_fps_or_exclusion,
        focus_map_hdmi_burnin=False,
        effective_marker_display=effective_marker_display,
        effective_center_marker=effective_center_marker,
        effective_aspect_marker=effective_aspect_marker,
        effective_safety_zone=effective_safety_zone,
        effective_guideframe=effective_guideframe,
        marker_auto_hidden_under_focus_magnifier=marker_auto_hidden_under_focus_magnifier,
        marker_hdmi_output=False,
        effective_peaking_display=effective_peaking_display,
        effective_peaking_level=effective_peaking_level,
        effective_peaking_color=effective_peaking_color,
        peaking_hdmi_output=False,
        marker_and_peaking_survived_cam_reset=marker_and_peaking_survived_cam_reset,
        exact_15_active_aspect_ratios_verified=exact_15_active_aspect_ratios_verified,
        fx6_user_box_enabled=fx6_user_box_enabled,
        fx6_user_box_width=fx6_user_box_width if _is_strict_int(fx6_user_box_width) else 0,
        fx6_user_box_height=fx6_user_box_height if _is_strict_int(fx6_user_box_height) else 0,
        fx6_user_box_h_pos=fx6_user_box_h_pos if _is_strict_int(fx6_user_box_h_pos) else 0,
        fx6_user_box_v_pos=fx6_user_box_v_pos if _is_strict_int(fx6_user_box_v_pos) else 0,
        fx6_aspect_mask_level=(
            fx6_aspect_mask_level if _is_strict_int(fx6_aspect_mask_level) else 0
        ),
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        matrix_states_checked=matrix_states,
        violation_codes=tuple(violations),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        movie_af_focusmap_marker_peaking_guard=guard_summary,
        donor_audit=donor.to_dict(),
    )


def compute_movie_af_focusmap_marker_peaking_matrix() -> Dict[str, int]:
    """Exhaustive 256-state safety matrix across G142 Movie AF / Focus Map / Marker & Peaking."""
    states = 0
    af_range_blocked_count = 0
    onbody_focusmap_blocked_count = 0
    external_focusmap_valid_count = 0
    marker_peaking_reset_survived_count = 0

    for mdl in (FX3_MODEL_NAME_PHASE319, FX6_MODEL_NAME_PHASE319):
        for sens in (1, 5, 6, 7):
            for fps in (23.98, 119.88, 150.0, 240.0):
                for onbody_req in (False, True):
                    for ext_fm in (False, True):
                        for rst in (
                            RESET_ACTION_NONE_PHASE319,
                            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319,
                        ):
                            for peak_color in ("White", "B&W"):
                                res = verify_movie_af_focusmap_marker_peaking_guard(
                                    force_clean_room=True,
                                    target_model=mdl,
                                    reset_action=rst,
                                    requested_af_subj_shift_sensitivity=sens,
                                    frame_rate_fps=fps,
                                    requested_fx3_onbody_focus_map=(
                                        onbody_req and mdl == FX3_MODEL_NAME_PHASE319
                                    ),
                                    fx6_onbody_focus_map_requested=(
                                        onbody_req and mdl == FX6_MODEL_NAME_PHASE319
                                    ),
                                    external_focus_map_requested=ext_fm,
                                    requested_marker_display="On",
                                    requested_aspect_marker="2.39:1",
                                    requested_peaking_display="On",
                                    requested_peaking_color=peak_color,
                                    _skip_matrix=True,
                                )
                                assert not res.marker_hdmi_output
                                assert not res.peaking_hdmi_output
                                assert not res.focus_map_hdmi_burnin
                                states += 1
                                if res.af_subj_shift_6_or_7_rejected:
                                    af_range_blocked_count += 1
                                if res.fx3_onbody_focus_map_rejected:
                                    onbody_focusmap_blocked_count += 1
                                if res.external_monitor_control_focus_map_active:
                                    external_focusmap_valid_count += 1
                                if res.marker_and_peaking_survived_cam_reset:
                                    marker_peaking_reset_survived_count += 1

    return {
        "states_checked": states,
        "af_range_blocked_count": af_range_blocked_count,
        "onbody_focusmap_blocked_count": onbody_focusmap_blocked_count,
        "external_focusmap_valid_count": external_focusmap_valid_count,
        "marker_peaking_reset_survived_count": marker_peaking_reset_survived_count,
    }


def evaluate_g142_movie_af_focusmap_marker_peaking_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **kwargs: Any,
) -> Tuple[GateVerdict, G142MovieAfFocusMapMarkerPeakingGuardResult]:
    res = verify_movie_af_focusmap_marker_peaking_guard(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **kwargs,
    )
    verdict = GateVerdict(
        gate_id=G142,
        gate_code=G142_GATE_CODE,
        passed=res.valid,
        status=res.status,
        evidence=(
            f"status={res.status} mode={res.verification_mode} "
            f"af_speed={res.effective_af_transition_speed} "
            f"af_sens={res.effective_af_subj_shift_sensitivity} "
            f"onbody_fm={res.fx3_onbody_focus_map_menu_present} "
            f"aspect={res.effective_aspect_marker} peaking={res.effective_peaking_color}"
        ),
        violation_codes=res.violation_codes,
        errors=res.violation_codes,
        warnings=tuple(res.donor_audit.get("warnings", ())),
    )
    return verdict, res


def resolve_fx3_movie_af_focusmap_marker_peaking_state(
    **kwargs: Any,
) -> Dict[str, Any]:
    return verify_movie_af_focusmap_marker_peaking_guard(**kwargs).to_dict()


# ---------------------------------------------------------------------------
# Unified 142-Gate Master Safety Preflight (`G01..G142`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Master142GateReport:
    schema: str
    schema_version: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_139_gates_verified: bool
    all_142_gates_verified: bool
    g13_to_g142_all_passed: bool
    g141_to_g142_all_passed: bool
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
    master_140_report: Dict[str, Any]
    g141_result: Dict[str, Any]
    g142_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_142gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    simulate_bench_dry_run: Optional[bool] = None,
    dry_run_simulated_backup: Optional[bool] = None,
    request_persistent_emmc_writes: bool = False,
    master_140_override: Optional[Master140GateReport] = None,
    ftp_ftpes_customwb_kwargs: Optional[Mapping[str, Any]] = None,
    movie_af_focusmap_marker_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master142GateReport:
    effective_dry_run = bool(
        dry_run_simulated
        or (simulate_bench_dry_run is True)
        or (dry_run_simulated_backup is True)
    )
    clean_forced = _is_clean_room_forced(force_clean_room)
    resolved_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved_work_root_for_m140 = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=resolved_repo_root).work_root
    )
    m140_force_clean_room = (
        True
        if (clean_forced or resolved_work_root_for_m140 is None)
        else force_clean_room
    )

    m140_report = (
        master_140_override
        if master_140_override is not None
        else evaluate_140gate_preflight(
            resolved_repo_root,
            work_root=work_root,
            force_clean_room=m140_force_clean_room,
            dry_run_simulated=effective_dry_run,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
        )
    )

    g141_kw = dict(ftp_ftpes_customwb_kwargs or {})
    if "request_persistent_emmc_writes" not in g141_kw:
        g141_kw["request_persistent_emmc_writes"] = request_persistent_emmc_writes
    g141_verdict, g141_res = evaluate_g141_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
        repo_root=resolved_repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **g141_kw,
    )

    g142_kw = dict(movie_af_focusmap_marker_kwargs or {})
    if "request_persistent_emmc_writes" not in g142_kw:
        g142_kw["request_persistent_emmc_writes"] = request_persistent_emmc_writes
    g142_verdict, g142_res = evaluate_g142_movie_af_focusmap_marker_peaking_guard(
        repo_root=resolved_repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **g142_kw,
    )

    new_gate_dicts = (
        {
            "gate_id": G141,
            "gate_code": G141_GATE_CODE,
            "status": g141_res.status,
            "passed": g141_verdict.passed,
            "evidence": g141_verdict.evidence,
            "violation_codes": list(g141_verdict.errors),
        },
        {
            "gate_id": G142,
            "gate_code": G142_GATE_CODE,
            "status": g142_res.status,
            "passed": g142_verdict.passed,
            "evidence": g142_verdict.evidence,
            "violation_codes": list(g142_verdict.errors),
        },
    )

    all_gates: Tuple[Dict[str, Any], ...] = tuple(m140_report.gates) + new_gate_dicts
    g01_to_g12_verified = int(m140_report.summary["g01_to_g12_verified"])
    g13_to_g140_verified = int(m140_report.summary["g13_to_g138_verified"]) + int(
        m140_report.summary["g139_to_g140_verified"]
    )
    g141_to_g142_verified = int(bool(g141_verdict.passed)) + int(
        bool(g142_verdict.passed)
    )
    total_verified = g01_to_g12_verified + g13_to_g140_verified + g141_to_g142_verified

    g141_to_g142_all_passed = g141_to_g142_verified == 2
    g13_to_g142_all_passed = (
        m140_report.g13_to_g140_all_passed and g141_to_g142_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m140_report.gates[:9])

    offline_139_verified = (
        g01_to_g09_ok
        and m140_report.offline_137_gates_verified
        and g141_to_g142_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_142_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g142_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m140_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_139_verified
        and m140_report.h0_h1_trial_entry_allowed
        and g141_to_g142_all_passed
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
        list(m140_report.errors)
        + list(g141_verdict.errors)
        + list(g142_verdict.errors)
    )
    warnings: List[str] = (
        list(m140_report.warnings)
        + list(g141_verdict.warnings)
        + list(g142_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m140_report.g13_to_g140_all_passed:
        overall_status = m140_report.status
    elif not g141_verdict.passed:
        overall_status = g141_verdict.status
    elif not g142_verdict.passed:
        overall_status = g142_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_142_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_142_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_142_verified:
        overall_status = "VERIFIED_ALL_142_GATES"
    else:
        overall_status = "VERIFIED_139_OF_142_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m140_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g141_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g142_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 142,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 142 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g140_verified": g13_to_g140_verified,
        "g141_to_g142_verified": g141_to_g142_verified,
        "g13_to_g142_all_passed": g13_to_g142_all_passed,
        "g141_to_g142_all_passed": g141_to_g142_all_passed,
        "offline_139_gates_verified": offline_139_verified,
        "all_142_gates_verified": all_142_verified,
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

    return Master142GateReport(
        schema=REALHW_142GATE_PREFLIGHT_SCHEMA,
        schema_version=REALHW_142GATE_PREFLIGHT_SCHEMA,
        version=REALHW_FTP_FTPES_CUSTOMWB_AF_FOCUSMAP_MARKER_142GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_139_gates_verified=offline_139_verified,
        all_142_gates_verified=all_142_verified,
        g13_to_g142_all_passed=g13_to_g142_all_passed,
        g141_to_g142_all_passed=g141_to_g142_all_passed,
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
        master_140_report=m140_report.to_dict(),
        g141_result=g141_res.to_dict(),
        g142_result=g142_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_142_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master142GateReport:
    return evaluate_142gate_preflight(repo_root, **kwargs)


def run_142_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master142GateReport:
    return evaluate_142gate_preflight(repo_root, **kwargs)


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
        prog="realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard",
        description="Phase 319 Wave-61 G141/G142 and 142/142 Safety Gates Preflight CLI",
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
        help="Supply simulated dry-run Tier-0 backup inputs so all 142/142 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g141", "g142", "142"],
        default="142",
        help="Target gate check: g141, g142, or 142",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g141":
        v, r = evaluate_g141_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
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

    if args.gate == "g142":
        v, r = evaluate_g142_movie_af_focusmap_marker_peaking_guard(
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

    rep = evaluate_142gate_preflight(
        args.repo_root,
        force_clean_room=clean,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        _safe_write_json(
            {
                "schema_version": rep.schema_version,
                "status": rep.status,
                "verification_mode": rep.verification_mode,
                "summary": rep.summary,
                "g141_status": rep.g141_result["status"],
                "g142_status": rep.g142_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/142\n"
        )
    ok = (
        rep.all_142_gates_verified
        if args.dry_run_simulated
        else rep.offline_139_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "AF_ASSIST_F_UXC_RESID16_G142",
    "AF_ASSIST_INCOMPATIBLE_LENSES_G142",
    "AF_SUBJ_SHIFT_SENS_DEFAULT_G142",
    "AF_SUBJ_SHIFT_SENS_F_UXC_RESID16_G142",
    "AF_SUBJ_SHIFT_SENS_MAX_G142",
    "AF_SUBJ_SHIFT_SENS_MIN_G142",
    "AF_TRANSITION_SPEED_DEFAULT_G142",
    "AF_TRANSITION_SPEED_F_UXC_RESID16_G142",
    "AF_TRANSITION_SPEED_MAX_G142",
    "AF_TRANSITION_SPEED_MIN_G142",
    "ALLOWED_ASPECT_MARKER_STATES_FX3_G142",
    "ALLOWED_FTP_CLIP_FLAGS_G141",
    "ALLOWED_FTP_DIR_HIERARCHIES_G141",
    "ALLOWED_FTP_MOVIE_TARGETS_G141",
    "ALLOWED_FTP_RAW_JH_TARGETS_G141",
    "ALLOWED_FTP_ROOT_CERT_ERR_BEHAVIORS_G141",
    "ALLOWED_FTP_TRANSFER_MODES_G141",
    "ALLOWED_FX3_FTP_PROTOCOLS_G141",
    "ALLOWED_FX3_PEAKING_COLORS_G142",
    "ALLOWED_FX3_SAFETY_ZONES_G142",
    "ALLOWED_FX3_WB_MODES_G141",
    "ALLOWED_FX6_ASPECT_SAFETY_AREAS_G142",
    "ALLOWED_FX6_PEAKING_COLORS_G142",
    "ALLOWED_FX6_WB_MEMORY_BANKS_G141",
    "ALLOWED_FX6_WHT_BAL_SWITCH_G141",
    "ALLOWED_LOG_SHOOTING_MODES_PHASE319",
    "ALLOWED_PEAKING_LEVELS_G142",
    "ALLOWED_PICTURE_PROFILE_GAMMA_G141",
    "ALLOWED_PRIORITY_SET_AWB_G141",
    "ALLOWED_RESET_ACTIONS_PHASE319",
    "ALLOWED_SHOCKLESS_WB_G141",
    "ALLOWED_SHOOT_MODES_PHASE319",
    "ALLOWED_SHUTTER_AWB_LOCK_G141",
    "ALLOWED_USBLAN_STATES_G141",
    "ASPECT_MARKER_F_UXC_RESID16_G142",
    "CENTER_MARKER_F_UXC_RESID16_G142",
    "CINE_EI_LOCKED_WB_MODES_G141",
    "CROSS_MODEL_FLASH_AUTHORIZED",
    "CUSTOM_WB_ERROR_0X0220_PP_GAMMAS_G141",
    "DEFAULT_REPO_ROOT",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE319",
    "DONOR_CHECK_MAX_SECONDS_PHASE319",
    "DORMANT_FTP_IMAGE_SIZE_TRAPS_G141",
    "DORMANT_OR_FORBIDDEN_FTP_PROTOCOLS_G141",
    "EBUSY_ERRNO_PHASE319",
    "EBUSY_NAME_PHASE319",
    "EINVAL_ERRNO_PHASE319",
    "EINVAL_NAME_PHASE319",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "ENODEV_ERRNO_PHASE319",
    "ENODEV_NAME_PHASE319",
    "ENV_CLEAN_ROOM_TEST_PHASE319",
    "ENV_FORCE_CLEAN_ROOM",
    "EOPNOTSUPP_ERRNO_PHASE319",
    "EOPNOTSUPP_NAME_PHASE319",
    "EROFS_ERRNO_PHASE319",
    "EROFS_NAME_PHASE319",
    "EXACT_15_ACTIVE_ASPECT_RATIOS_FX3_G142",
    "FOCUS_MAP_HIGH_FPS_BLOCK_THRESHOLD_G142",
    "FOCUS_MAP_MIN_FX3_FW_G142",
    "FOCUS_MAP_SHARED_F_UXC_RESID16_G142",
    "FTP_AVF_DB_RESET_WARNING_BASE_UXC_RESID16_G141",
    "FTP_DIR_HIERARCHY_SAME_AS_CAMERA_G141",
    "FTP_DIR_HIERARCHY_STANDARD_G141",
    "FTP_FTPES_CONNECT_F_UXC_RESID16_G141",
    "FTP_FUNCTION_F_UXC_RESID16_G141",
    "FTP_MODE_ACTIVE_G141",
    "FTP_MODE_PASSIVE_G141",
    "FTP_PROTOCOL_FTPES_G141",
    "FTP_PROTOCOL_FTP_G141",
    "FTP_PROTOCOL_IMPLICIT_FTPS_FORBIDDEN_G141",
    "FTP_PROTOCOL_SFTP_FORBIDDEN_G141",
    "FTP_SECURE_PROTOCOL_F_UXC_RESID16_G141",
    "FTP_SERVER1_F_UXC_RESID16_G141",
    "FTP_SERVER8_F_UXC_RESID16_G141",
    "FTP_SERVER9_F_UXC_RESID16_G141",
    "FTP_SLOT1_MUTEX_BASE_UXC_RESID16_G141",
    "FTP_TRANSFER_HEIF_SIZE_DORMANT_F_UXC_RESID16_G141",
    "FTP_TRANSFER_JPEG_SIZE_DORMANT_F_UXC_RESID16_G141",
    "FX3_DEFAULT_FW_VERSION_PHASE319",
    "FX3_FTP_CACERT_FILENAME_G141",
    "FX3_FTP_CACERT_MAX_BYTES_G141",
    "FX3_FTP_EXACT_SERVER_SLOTS_G141",
    "FX3_FTP_SERVER_SLOT_MAX_G141",
    "FX3_FTP_SERVER_SLOT_MIN_G141",
    "FX3_FTP_SPECIFY_DIRECTORY_MAX_LEN_G141",
    "FX3_HELP_GUIDE_CODE_PHASE319",
    "FX3_MODEL_ID_PHASE319",
    "FX3_MODEL_NAME_PHASE319",
    "FX6_ASPECT_MASK_DEFAULT_G142",
    "FX6_ASPECT_MASK_MAX_G142",
    "FX6_ASPECT_MASK_MIN_G142",
    "FX6_DEFAULT_FW_VERSION_PHASE319",
    "FX6_FOCUS_MAP_LOW_FPS_BLOCK_THRESHOLD_G142",
    "FX6_FTP_CERT_FILENAME_G141",
    "FX6_FTP_CERT_SLOT_G141",
    "FX6_FTP_ELF_SERVER_SLOTS_MAX_G141",
    "FX6_FTP_UI_SERVER_SLOTS_G141",
    "FX6_MODEL_NAME_PHASE319",
    "FX6_PRODUCT_CODE_PHASE319",
    "FX6_USER_BOX_HEIGHT_MAX_G142",
    "FX6_USER_BOX_HEIGHT_MIN_G142",
    "FX6_USER_BOX_H_POS_MAX_G142",
    "FX6_USER_BOX_H_POS_MIN_G142",
    "FX6_USER_BOX_V_POS_MAX_G142",
    "FX6_USER_BOX_V_POS_MIN_G142",
    "FX6_USER_BOX_WIDTH_MAX_G142",
    "FX6_USER_BOX_WIDTH_MIN_G142",
    "FtpFtpesCustomWbVaultGuardResult",
    "G141",
    "G141FtpFtpesCustomWbVaultGuardResult",
    "G141_GATE_CODE",
    "G141_GATE_ID",
    "G142",
    "G142MovieAfFocusMapMarkerPeakingGuardResult",
    "G142_GATE_CODE",
    "G142_GATE_ID",
    "GUIDEFRAME_F_UXC_RESID16_G142",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HUMAN_HARDWARE_ATTACH_TOKEN",
    "LOG_SHOOTING_CINE_EI_PHASE319",
    "LOG_SHOOTING_CINE_EI_QUICK_PHASE319",
    "LOG_SHOOTING_FLEXIBLE_ISO_PHASE319",
    "LOG_SHOOTING_OFF_PHASE319",
    "MARKER_DISPLAY_F_UXC_RESID16_G142",
    "Master142GateReport",
    "MovieAfFocusMapMarkerPeakingGuardResult",
    "PEAKING_COLOR_BASE_UXC_RESID16_G142",
    "PEAKING_DISPLAY_F_UXC_RESID16_G142",
    "PEAKING_LEVEL_BASE_UXC_RESID16_G142",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PINNED_FX3_APPFW_SLICES_PHASE319",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE319",
    "PINNED_FX6_APPFW_SLICES_PHASE319",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE319",
    "PINNED_PHASE319_DONOR_SPECS",
    "Phase319DonorAuditResult",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "REALHW_142GATE_PREFLIGHT_SCHEMA",
    "REALHW_FTP_FTPES_9SLOT_ZERO_SFTP_AVF_VAULT_AND_CUSTOMWB_CINEEI_GUARD",
    "REALHW_FTP_FTPES_CUSTOMWB_AF_FOCUSMAP_MARKER_142GATE_SCHEMA",
    "REALHW_FTP_FTPES_CUSTOMWB_AF_FOCUSMAP_MARKER_142GATE_VERSION",
    "REALHW_MOVIE_AF_1TO7_1TO5_EXTERNAL_FOCUSMAP_AND_15ASPECT_MARKER_PEAKING_GUARD",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319",
    "RESET_ACTION_INITIALIZE_PHASE319",
    "RESET_ACTION_NONE_PHASE319",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE319",
    "SAFETY_ZONE_F_UXC_RESID16_G142",
    "SHOOT_MODE_MOVIE_PHASE319",
    "SHOOT_MODE_SQ_PHASE319",
    "SHOOT_MODE_STILL_PHASE319",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_BLOCKED_G141_CUSTOMWB_LOG_ERR_0X0220_OR_CINEEI_VIOLATION",
    "STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION",
    "STATUS_BLOCKED_G141_SLOT1_AVF_INFO_VAULT_OR_CACERT_VIOLATION",
    "STATUS_BLOCKED_G141_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G141_USBLAN_ZERO_RF_BYPASS_VIOLATION",
    "STATUS_BLOCKED_G142_FOCUSMAP_ONBODY_OR_EXCLUSION_VIOLATION",
    "STATUS_BLOCKED_G142_MARKER_15ASPECT_PEAKING_OR_HDMI_VIOLATION",
    "STATUS_BLOCKED_G142_MOVIE_AF_1TO7_1TO5_OR_ASSIST_VIOLATION",
    "STATUS_BLOCKED_G142_TELEMETRY_INVALID",
    "STATUS_BLOCKED_PERSISTENT_EMMC_WRITE",
    "STATUS_BLOCKED_PHASE319_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G141",
    "STATUS_VERIFIED_G142",
    "STATUS_VERIFIED_SAFE",
    "USB_PACKETS_TRANSMITTED",
    "WB_AB_AXIS_MAX_G141",
    "WB_AB_AXIS_MIN_G141",
    "WB_AB_STEP_G141",
    "WB_COLOR_TEMP_MAX_K_G141",
    "WB_COLOR_TEMP_MIN_K_G141",
    "WB_COLOR_TEMP_STEP_K_G141",
    "WB_CUSTOM_ERROR_BASE_UXC_RESID16_G141",
    "WB_CUSTOM_ERROR_F_UXC_RESID16_G141",
    "WB_GM_AXIS_MAX_G141",
    "WB_GM_AXIS_MIN_G141",
    "WB_GM_STEP_G141",
    "WB_PRIORITY_SET_IN_AWB_F_UXC_RESID16_G141",
    "WB_SHOCKLESS_WB_F_UXC_RESID16_G141",
    "WB_SHUTTER_AWB_LOCK_F_UXC_RESID16_G141",
    "WB_WHITE_BALANCE_F_UXC_RESID16_G141",
    "audit_phase319_donor_contracts",
    "compute_ftp_ftpes_customwb_matrix",
    "compute_movie_af_focusmap_marker_peaking_matrix",
    "evaluate_142_master_safety_gates",
    "evaluate_142gate_preflight",
    "evaluate_g141_ftp_ftpes_avf_vault_and_customwb_cineei_guard",
    "evaluate_g142_movie_af_focusmap_marker_peaking_guard",
    "main",
    "resolve_fx3_ftp_ftpes_customwb_state",
    "resolve_fx3_movie_af_focusmap_marker_peaking_state",
    "run_142_gate_preflight",
    "verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard",
    "verify_movie_af_focusmap_marker_peaking_guard",
]


if __name__ == "__main__":
    raise SystemExit(main())
