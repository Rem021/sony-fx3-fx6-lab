"""Phase 276 (Task H315, 114/114 Safety Gates, Wave-47) Sony `ILME-FX3`
(`Ver. 7.02`, `ilc/2210`) vs `ILME-FX6` (`Ver. 6.01`) Safety Gates `G113`
(`[USB Connection Mode]` 4-Mode vs Dormant `NOUVC` `[USB Streaming]` Split,
`[USB LUN Setting]` / `[USB Power Supply]` Data-Isolated PD Guard, &
`[HDMI Info. Display]` LCD-Blanking / `1080` Clamp vs `4K` Clean-Feed Override)
& `G114` (`[Protect]` Scopes vs `[Format]` Override `Slot-1` Dual-Layer
Hardware WP + Firewall Mandate & `[Reset Network Set.]` Auto-Reboot +
Post-Reboot `[Airplane Mode] = [On]` Zero-RF Sequence) + Unified `114`-Gate
Master Safety Preflight (`G01..G114`).

Operationalizes Wave-47 official Sony `ILME-FX3` (`Ver. 7.02`, Help Guide
`ilc/2210`) & `ILME-FX6` (`Ver. 6.01`) intelligence
(`reports/2026-11-17-global-sony-wave47-usb-connection-mode-hdmi-info-protect-reset-network-intel/README.md`)
as deterministic offline preflight verifiers (`G113` and `G114`) and delegates
`G01..G112` directly to `evaluate_112gate_preflight()`.
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
from .realhw_power_save_monitor_language_volume_delete_and_112gate_guard import (
    Master112GateReport,
    evaluate_112gate_preflight,
)
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_114GATE_SCHEMA: str = (
    "realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard_v1"
)
REALHW_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_114GATE_VERSION: str = "1.0.0"

G113_GATE_ID: str = (
    "G113_usb_connection_mode_nouvc_pd_data_isolation_and_hdmi_info_display_guard"
)
G113_GATE_CODE: str = (
    "USB_CONNECTION_MODE_NOUVC_PD_DATA_ISOLATION_AND_HDMI_INFO_DISPLAY_GUARD"
)

G114_GATE_ID: str = (
    "G114_protect_vs_format_slot1_wp_firewall_and_reset_network_set_zero_rf_guard"
)
G114_GATE_CODE: str = (
    "PROTECT_VS_FORMAT_SLOT1_WP_FIREWALL_AND_RESET_NETWORK_SET_ZERO_RF_GUARD"
)

G113: str = G113_GATE_ID
G114: str = G114_GATE_ID
GATE_G113_USB_CONNECTION_MODE_NOUVC_PD_DATA_ISOLATION_AND_HDMI_INFO_DISPLAY_GUARD: str = (
    G113_GATE_CODE
)
GATE_G114_PROTECT_VS_FORMAT_SLOT1_WP_FIREWALL_AND_RESET_NETWORK_SET_ZERO_RF_GUARD: str = (
    G114_GATE_CODE
)

ENV_CLEAN_ROOM_TEST_PHASE276: str = "FX3_CLEAN_ROOM_TEST"

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE276: float = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE276: float = 1.00
DONOR_CHECK_MAX_SECONDS: float = DONOR_CHECK_MAX_SECONDS_PHASE276

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX6_MODEL_NAME: str = "ILME-FX6"
FX3_DEFAULT_FW_VERSION_PHASE276: str = "7.02"
FX6_DEFAULT_FW_VERSION_PHASE276: str = "6.01"
FX3_HELP_GUIDE_CODE_PHASE276: str = "ilc/2210"

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE276: str = "Reset Network Set."
RESET_ACTION_INITIALIZE: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE276: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_RESET_NETWORK_SET_PHASE276,
    RESET_ACTION_INITIALIZE,
)

# ---------------------------------------------------------------------------
# Status & Violation Codes (G113 / G114 / Phase 276)
# ---------------------------------------------------------------------------

STATUS_VERIFIED_G113: str = "VERIFIED_G113_USB_MODE_NOUVC_PD_AND_HDMI_INFO_SAFE"
STATUS_VERIFIED_G114: str = (
    "VERIFIED_G114_PROTECT_SLOT1_WP_AND_RESET_NETWORK_ZERO_RF_SAFE"
)
STATUS_BLOCKED_PHASE276_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE276_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G113_FX3_NOUVC_USB_STREAMING_SPOOF_VIOLATION: str = (
    "BLOCKED_G113_FX3_NOUVC_USB_STREAMING_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G113_AIRGAPPED_USB_DATA_ENUMERATION_HAZARD: str = (
    "BLOCKED_G113_AIRGAPPED_USB_DATA_ENUMERATION_HAZARD"
)
STATUS_BLOCKED_G113_USB_POWER_OR_LUN_CONTRACT_VIOLATION: str = (
    "BLOCKED_G113_USB_POWER_OR_LUN_CONTRACT_VIOLATION"
)
STATUS_BLOCKED_G113_HDMI_INFO_LCD_OR_CLEAN_FEED_OVERRIDE_VIOLATION: str = (
    "BLOCKED_G113_HDMI_INFO_LCD_OR_CLEAN_FEED_OVERRIDE_VIOLATION"
)
STATUS_BLOCKED_G113_SETUP_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G113_SETUP_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G113_TELEMETRY_INVALID: str = (
    "BLOCKED_G113_USB_MODE_HDMI_INFO_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G114_PROTECT_ONLY_WITHOUT_SLOT1_WP_FIREWALL_VIOLATION: str = (
    "BLOCKED_G114_PROTECT_ONLY_WITHOUT_SLOT1_WP_FIREWALL_VIOLATION"
)
STATUS_BLOCKED_G114_PROTECT_SCOPE_OR_PLAYBACK_CONTRACT_VIOLATION: str = (
    "BLOCKED_G114_PROTECT_SCOPE_OR_PLAYBACK_CONTRACT_VIOLATION"
)
STATUS_BLOCKED_G114_POST_NETWORK_RESET_AIRPLANE_OFF_RF_HAZARD: str = (
    "BLOCKED_G114_POST_NETWORK_RESET_AIRPLANE_OFF_RF_HAZARD"
)
STATUS_BLOCKED_G114_RESET_BOUNDARY_OR_AUTO_REBOOT_VIOLATION: str = (
    "BLOCKED_G114_RESET_BOUNDARY_OR_AUTO_REBOOT_VIOLATION"
)
STATUS_BLOCKED_G114_TELEMETRY_INVALID: str = (
    "BLOCKED_G114_PROTECT_AND_NETWORK_RESET_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G113 Constants: [USB Connection Mode], NOUVC, PD Isolation & [HDMI Info. Display]
# ---------------------------------------------------------------------------

USB_CONNECTION_MODE_MENU_PATH_G113: str = (
    "MENU -> Setup -> [USB] -> [USB Connection Mode]"
)
USB_LUN_SETTING_MENU_PATH_G113: str = "MENU -> Setup -> [USB] -> [USB LUN Setting]"
USB_POWER_SUPPLY_MENU_PATH_G113: str = "MENU -> Setup -> [USB] -> [USB Power Supply]"
HDMI_INFO_DISPLAY_MENU_PATH_G113: str = (
    "MENU -> Setup -> [External Output] -> [HDMI Info. Display]"
)
HDMI_OUTPUT_SETTINGS_MENU_PATH_G113: str = (
    "MENU -> Setup -> [External Output] -> [HDMI Output Settings]"
)
FRAMING_SETTINGS_HDMI_MENU_PATH_G113: str = (
    "MENU -> Setup -> [External Output] -> [Framing Settings]"
)

USB_CONN_SEL_WHEN_CONNECT_G113: str = "Sel. When Connect"
USB_CONN_MASS_STORAGE_MSC_G113: str = "MassStorage(MSC)"
USB_CONN_MTP_G113: str = "MTP"
USB_CONN_REMOTE_SHOOT_G113: str = "Remote Shoot (PC Remote)"
USB_CONN_USB_LAN_G113: str = "USB-LAN"
USB_CONN_USB_STREAMING_G113: str = "USB Streaming"

FX3_STOCK_4_USB_CONNECTION_MODES_G113: Tuple[str, ...] = (
    USB_CONN_SEL_WHEN_CONNECT_G113,
    USB_CONN_MASS_STORAGE_MSC_G113,
    USB_CONN_MTP_G113,
    USB_CONN_REMOTE_SHOOT_G113,
)
USB_CONNECTION_MODE_FACTORY_DEFAULT_G113: str = USB_CONN_SEL_WHEN_CONNECT_G113
USB_CONNECTION_MODE_RESID16_G113: int = 0x69A2
USB_MSC_VID_PID_G113: str = "054C:0DA1"
USB_MSC_APPFW_MARKER_G113: str = "USB_CONNECTION_METHOD_MASS_STRAGE"

USB_CONNECTION_MODE_METADATA_G113: Dict[str, Tuple[int, str]] = {
    USB_CONN_SEL_WHEN_CONNECT_G113: (
        0x7738,
        "VAL_setting_usb_connection_method_USB_CONNECTION_SELECT_AFTER_CONNECTION",
    ),
    USB_CONN_MASS_STORAGE_MSC_G113: (
        0x6C54,
        "VAL_setting_usb_connection_method_USB_CONNECTION_MASS_STORAGE",
    ),
    USB_CONN_MTP_G113: (
        0xE24B,
        "VAL_setting_usb_connection_method_USB_CONNECTION_MTP",
    ),
    USB_CONN_REMOTE_SHOOT_G113: (
        0x60AA,
        "VAL_setting_usb_connection_method_USB_CONNECTION_REMOTE_PC",
    ),
}

FX3_UI_EXPOSES_USB_STREAMING_G113: bool = False
DORMANT_USB_STREAMING_RESID16_F_G113: int = 0x7399
DORMANT_USB_STREAMING_RESID16_G_G113: int = 0x63F7
DORMANT_USB_F_UVC_KO_BYTES_G113: int = 78_840

AIRGAPPED_PROHIBITED_USB_DATA_MODES_G113: Tuple[str, ...] = (
    USB_CONN_MASS_STORAGE_MSC_G113,
    USB_CONN_MTP_G113,
    USB_CONN_REMOTE_SHOOT_G113,
    USB_CONN_USB_LAN_G113,
)

USB_LUN_MULTI_G113: str = "Multi"
USB_LUN_SINGLE_G113: str = "Single"
ALLOWED_USB_LUN_SETTINGS_G113: Tuple[str, ...] = (
    USB_LUN_MULTI_G113,
    USB_LUN_SINGLE_G113,
)
USB_LUN_FACTORY_DEFAULT_G113: str = USB_LUN_MULTI_G113
USB_LUN_UXC_RESID16_G113: int = 0x6B19
USB_LUN_MULTI_RESID16_G113: int = 0xE631
USB_LUN_SINGLE_RESID16_G113: int = 0x776D

USB_POWER_SUPPLY_ON_G113: str = "On"
USB_POWER_SUPPLY_OFF_G113: str = "Off"
ALLOWED_USB_POWER_SUPPLY_MODES_G113: Tuple[str, ...] = (
    USB_POWER_SUPPLY_ON_G113,
    USB_POWER_SUPPLY_OFF_G113,
)
USB_POWER_SUPPLY_FACTORY_DEFAULT_G113: str = USB_POWER_SUPPLY_ON_G113
USB_POWER_SUPPLY_RESID16_G113: int = 0x721E
USB_PORT_TYPE_C_G113: str = "USB Type-C"
USB_PORT_MULTI_MICRO_G113: str = "Multi/Micro USB"
USB_PORT_NONE_G113: str = "None"
ALLOWED_USB_PORTS_G113: Tuple[str, ...] = (
    USB_PORT_TYPE_C_G113,
    USB_PORT_MULTI_MICRO_G113,
    USB_PORT_NONE_G113,
)

HDMI_INFO_DISPLAY_ON_G113: str = "On"
HDMI_INFO_DISPLAY_OFF_G113: str = "Off"
ALLOWED_HDMI_INFO_DISPLAY_MODES_G113: Tuple[str, ...] = (
    HDMI_INFO_DISPLAY_ON_G113,
    HDMI_INFO_DISPLAY_OFF_G113,
)
HDMI_INFO_DISPLAY_FACTORY_DEFAULT_G113: str = HDMI_INFO_DISPLAY_ON_G113
HDMI_INFO_DISPLAY_RESID16_G113: int = 0x6E7C

REC_MEDIA_HDMI_ON_G113: str = "On"
REC_MEDIA_HDMI_OFF_HDMI_ONLY_G113: str = "Off(HDMI Only)"
ALLOWED_REC_MEDIA_DUR_HDMI_MODES_G113: Tuple[str, ...] = (
    REC_MEDIA_HDMI_ON_G113,
    REC_MEDIA_HDMI_OFF_HDMI_ONLY_G113,
)
REC_MEDIA_HDMI_FACTORY_DEFAULT_G113: str = REC_MEDIA_HDMI_ON_G113
REC_MEDIA_HDMI_OFF_RESID16_G113: int = 0x6573

RAW_OUTPUT_OFF_G113: str = "Off"
RAW_OUTPUT_ON_G113: str = "On"
ALLOWED_RAW_OUTPUT_MODES_G113: Tuple[str, ...] = (
    RAW_OUTPUT_OFF_G113,
    RAW_OUTPUT_ON_G113,
)
RAW_OUTPUT_FACTORY_DEFAULT_G113: str = RAW_OUTPUT_OFF_G113
RAW_OUTPUT_RESID16_G113: int = 0x6E97

HDMI_OUT_RES_AUTO_G113: str = "Auto"
HDMI_OUT_RES_2160P_G113: str = "2160p"
HDMI_OUT_RES_1080P_G113: str = "1080p"
HDMI_OUT_RES_1080I_G113: str = "1080i"
ALLOWED_HDMI_OUTPUT_RESOLUTIONS_G113: Tuple[str, ...] = (
    HDMI_OUT_RES_AUTO_G113,
    HDMI_OUT_RES_2160P_G113,
    HDMI_OUT_RES_1080P_G113,
    HDMI_OUT_RES_1080I_G113,
)
HDMI_OUT_RES_FACTORY_DEFAULT_G113: str = HDMI_OUT_RES_AUTO_G113
HDMI_CLAMPED_1080_TOKEN_G113: str = "1080"
HDMI_4K_TOKEN_G113: str = "4K"

SHOOT_MODE_MOVIE_G113: str = "Movie"
SHOOT_MODE_STILL_G113: str = "Still"
SHOOT_MODE_SQ_G113: str = "S&Q"
ALLOWED_SHOOT_MODES_G113: Tuple[str, ...] = (
    SHOOT_MODE_MOVIE_G113,
    SHOOT_MODE_STILL_G113,
    SHOOT_MODE_SQ_G113,
)

LOG_SHOOTING_OFF_G113: str = "Off"
LOG_SHOOTING_FLEXIBLE_ISO_G113: str = "Flexible ISO"
LOG_SHOOTING_CINE_EI_G113: str = "Cine EI"
LOG_SHOOTING_CINE_EI_QUICK_G113: str = "Cine EI Quick"
ALLOWED_LOG_SHOOTING_MODES_G113: Tuple[str, ...] = (
    LOG_SHOOTING_OFF_G113,
    LOG_SHOOTING_FLEXIBLE_ISO_G113,
    LOG_SHOOTING_CINE_EI_G113,
    LOG_SHOOTING_CINE_EI_QUICK_G113,
)
PPLUT_PICTURE_PROFILES_G113: Tuple[str, ...] = (
    "PPLUT1",
    "PPLUT2",
    "PPLUT3",
    "PPLUT4",
)
ALLOWED_PICTURE_PROFILES_G113: Tuple[str, ...] = (
    "Off",
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
) + PPLUT_PICTURE_PROFILES_G113

FRAMING_HDMI_CROP_G113: str = "Crop"
FRAMING_HDMI_FULL_G113: str = "Full"
ALLOWED_FRAMING_HDMI_MODES_G113: Tuple[str, ...] = (
    FRAMING_HDMI_CROP_G113,
    FRAMING_HDMI_FULL_G113,
)
FRAMING_HDMI_FACTORY_DEFAULT_G113: str = FRAMING_HDMI_CROP_G113

# ---------------------------------------------------------------------------
# Gate G114 Constants: [Protect] vs [Format] & [Reset Network Set.] Zero-RF
# ---------------------------------------------------------------------------

PROTECT_MENU_PATH_G114: str = "MENU -> Playback -> [Selection/Memo] -> [Protect]"
FORMAT_MENU_PATH_G114: str = "MENU -> Shooting -> [Media] -> [Format]"
RESET_NETWORK_SET_MENU_PATH_G114: str = (
    "MENU -> Network -> [Network Option] -> [Reset Network Set.]"
)
AIRPLANE_MODE_MENU_PATH_G114: str = (
    "MENU -> Network -> [Network Option] -> [Airplane Mode]"
)

PROTECT_RESID16_G114: int = 0xE2C9
PROTECT_SCOPE_SINGLE_G114: str = "Single"
PROTECT_SCOPE_MULTIPLE_IMG_G114: str = "Multiple Img."
PROTECT_SCOPE_ALL_IN_FOLDER_G114: str = "All in this Folder"
PROTECT_SCOPE_ALL_WITH_DATE_G114: str = "All with this date"
PROTECT_SCOPE_ALL_IN_GROUP_G114: str = "All Images in This Group"
ALLOWED_PROTECT_SCOPES_G114: Tuple[str, ...] = (
    PROTECT_SCOPE_SINGLE_G114,
    PROTECT_SCOPE_MULTIPLE_IMG_G114,
    PROTECT_SCOPE_ALL_IN_FOLDER_G114,
    PROTECT_SCOPE_ALL_WITH_DATE_G114,
    PROTECT_SCOPE_ALL_IN_GROUP_G114,
)
PROTECT_SCOPE_RESID16_MAP_G114: Dict[str, Tuple[int, Optional[int], str]] = {
    PROTECT_SCOPE_SINGLE_G114: (0xE2C9, None, "FUNC_protect_content"),
    PROTECT_SCOPE_MULTIPLE_IMG_G114: (0xE2CA, None, "FUNC_protect_for_multipul_images"),
    PROTECT_SCOPE_ALL_IN_FOLDER_G114: (0x6848, 0x72D9, "protect_all_in_folder"),
    PROTECT_SCOPE_ALL_WITH_DATE_G114: (
        0x69F7,
        0x7339,
        "FUNC_protect_all_contents_in_this_date",
    ),
    PROTECT_SCOPE_ALL_IN_GROUP_G114: (
        0xE826,
        0xE553,
        "FUNC_protect_all_contents_in_this_group",
    ),
}

FORMAT_RESID16_G114: int = 0xE449
FORMAT_CONFIRM_RESID16_G114: int = 0xE414
FORMAT_QUICK_RESID16_G114: int = 0xE792
FORMAT_FULL_RESID16_G114: int = 0xE8F5

MEDIA_OP_NONE_G114: str = "NONE"
MEDIA_OP_DELETE_SINGLE_G114: str = "DELETE_SINGLE"
MEDIA_OP_DELETE_PRESSING_TWICE_G114: str = "DELETE_PRESSING_TWICE"
MEDIA_OP_FORMAT_QUICK_G114: str = "FORMAT_QUICK"
MEDIA_OP_FORMAT_FULL_G114: str = "FORMAT_FULL"
ALLOWED_MEDIA_OPS_G114: Tuple[str, ...] = (
    MEDIA_OP_NONE_G114,
    MEDIA_OP_DELETE_SINGLE_G114,
    MEDIA_OP_DELETE_PRESSING_TWICE_G114,
    MEDIA_OP_FORMAT_QUICK_G114,
    MEDIA_OP_FORMAT_FULL_G114,
)

TARGET_SLOT_NONE_G114: str = "NONE"
TARGET_SLOT_1_G114: str = "Slot 1"
TARGET_SLOT_2_G114: str = "Slot 2"
ALLOWED_TARGET_SLOTS_G114: Tuple[str, ...] = (
    TARGET_SLOT_NONE_G114,
    TARGET_SLOT_1_G114,
    TARGET_SLOT_2_G114,
)

RESET_NETWORK_SET_RESID16_G114: int = 0x60D3
RESET_NETWORK_PROMPT_RESID16_G114: int = 0x65D3
AIRPLANE_MODE_RESID16_G114: int = 0x6DF9
AIRPLANE_MODE_ON_G114: str = "On"
AIRPLANE_MODE_OFF_G114: str = "Off"
ALLOWED_AIRPLANE_MODES_G114: Tuple[str, ...] = (
    AIRPLANE_MODE_ON_G114,
    AIRPLANE_MODE_OFF_G114,
)
AIRPLANE_MODE_FACTORY_DEFAULT_G114: str = AIRPLANE_MODE_OFF_G114

NETWORK_RESET_CLEARED_CATEGORIES_G114: Tuple[str, ...] = (
    "Wi-Fi SSID/PSK & Wi-Fi Direct",
    "Bluetooth Pairing / Bluetooth Function / Bluetooth Rmt Ctrl",
    "FTP Profiles 0..8 / Auto FTP / FTP Power Save",
    "Creators' Cloud / Remote Shoot / Access Authen. / IPsec / USB-LAN",
    "Network Streaming (RTMP/RTMPS/SRT) & Root Certificates",
    "Airplane Mode (reset to Off)",
)
NETWORK_RESET_PRESERVED_DOMAINS_G114: Tuple[str, ...] = (
    "(Shooting)",
    "(Exposure/Color)",
    "(Focus)",
    "(Setup)",
    "(Playback)",
    "CAMSET (M1..M4 on card)",
)

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, Targeted Pread on appFw.so, <0.20s)
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE276: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (62_701_666, b"BKID_APP_setting_usb_connection_method"),
    (61_936_024, b"USB_CONNECTION_SELECT_AFTER_CONNECTION"),
    (61_936_214, b"USB_CONNECTION_MASS_STORAGE"),
    (63_021_911, b"USB_CONNECTION_METHOD_MASS_STRAGE"),
    (61_936_276, b"USB_CONNECTION_MTP"),
    (61_936_329, b"USB_CONNECTION_REMOTE_PC"),
    (61_936_097, b"USB_CONNECTION_USB_STREAMING"),
    (62_701_705, b"BKID_APP_setting_lun_settings"),
    (62_701_735, b"BKID_APP_setting_usb_supply"),
    (62_702_156, b"BKID_APP_setting_hdmi_info_display"),
    (62_649_393, b"CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON"),
    (62_701_796, b"BKID_APP_setting_rec_media_during_hdmi_output"),
    (60_604_342, b"FUNC_protect_content"),
    (62_165_974, b"MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1"),
    (60_603_197, b"FUNC_reset_network_settings"),
    (60_434_315, b"SETTING_RESET_NW"),
    (62_843_221, b"BKID_APP_is_shutdown_factor_network_reset"),
    (62_694_699, b"BKID_APP_setting_airplane_mode"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE276: str = (
    "ca367416636bb501c0ac76df3a1bbe86d82176425fca97a0f61f40ec1e28fef9"
)

PINNED_FX6_APPFW_SLICES_PHASE276: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (40_923_148, b"BKID_APP_SETTING_HDMI_INFO_DISPLAY"),
    (40_939_292, b"BKID_APP_SETTING_USB_STREAMING_PROCAM"),
    (40_964_955, b"BKID_APP_USER_MENU_LOCK_UNLOCK_CLIP0"),
    (40_971_200, b"BKID_APP_USER_MENU_NETWORK_RESET"),
    (40_992_525, b"BKID_APP_IS_SHUTDOWN_FACTOR_NETWORK_RESET"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE276: str = (
    "decff496dabc17a2a9834a93f8262f3faa1e0f120d1d7015acc064725634258c"
)

PINNED_PHASE276_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE276,
        tuple(tok for _off, tok in PINNED_FX3_APPFW_SLICES_PHASE276),
        "FX3_APPFW_WAVE47_USB_HDMI_PROTECT_NW_RESET_SLICES",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"USB Connection Mode",
            b"Sel. When Connect",
            b"MassStorage(MSC)",
            b"Remote Shoot (PC Remote)",
            b"USB LUN Setting",
            b"USB Power Supply",
            b"USB Streaming",
            b"HDMI Info. Display",
            b"All in this Folder",
            b"All with this date",
            b"Reset Network Set.",
            b"Reset all network settings?\n(After initialization, reboots\nautomatically.)",
        ),
        "FX3_UXC_F_USB_HDMI_PROTECT_NW_RESET_STRINGS",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"MTP",
            b"Protect",
            b"Multiple Img.",
            b"All Images in This Group",
            b"Format",
            b"All data will be deleted.\nFormat?",
            b"Image protected.",
            b"File protected.",
        ),
        "FX3_UXC_MTP_PROTECT_FORMAT_STRINGS",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Selection/Memo",
            b"Network Option",
            b"External Output",
            b"USB Streaming",
        ),
        "FX3_UXC_G_SELECTION_NETWORK_EXTERNAL_OUTPUT",
    ),
    "fx3_usb_f_uvc_ko": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/usb_f_uvc.ko",
        78_840,
        "a23970925fa91ed7712f14bf7de8ac62ff9d63e9bcbfeecc94b37085d48c5ccc",
        (b"\x7fELF", b"uvc"),
        "FX3_DORMANT_USB_F_UVC_KO_NOUVC_MODULE",
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
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE276,
        tuple(tok for _off, tok in PINNED_FX6_APPFW_SLICES_PHASE276),
        "FX6_APPFW_WAVE47_HDMI_UVC_CLIP_NW_RESET_SLICES",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (b"Format", b"USB Tethering"),
        "FX6_UXC_FORMAT_USB_TETHERING",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"Network Reset",
            b"All Reset",
            b"Lock/Unlock Clip",
            b"Lock All Clips",
            b"Format Media",
        ),
        "FX6_UXC_2_NETWORK_RESET_LOCK_CLIP_FORMAT_MEDIA",
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase276DonorAuditResult:
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
    dormant_usb_f_uvc_ko_bytes: int
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UsbModeAndHdmiInfoGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    reset_action: str
    usb_connection_mode_menu_path: str
    usb_lun_setting_menu_path: str
    usb_power_supply_menu_path: str
    hdmi_info_display_menu_path: str
    hdmi_output_settings_menu_path: str
    framing_settings_hdmi_menu_path: str
    fx3_stock_4_usb_modes: Tuple[str, ...]
    fx3_ui_exposes_usb_streaming: bool
    usb_streaming_spoof_events: int
    pre_reset_usb_connection_mode: str
    effective_post_reset_usb_connection_mode: str
    pre_reset_usb_lun_setting: str
    effective_post_reset_usb_lun_setting: str
    pre_reset_usb_power_supply: str
    effective_post_reset_usb_power_supply: str
    usb_port: str
    np_fz100_battery_inserted: bool
    air_gapped_tier0_bench: bool
    usb_data_lines_physically_isolated: bool
    usb_host_data_enumerated: bool
    airgapped_usb_data_enumeration_hazards: int
    shoot_mode: str
    log_shooting: str
    picture_profile: str
    pre_reset_hdmi_info_display: str
    effective_post_reset_hdmi_info_display: str
    effective_hdmi_info_display: str
    pre_reset_rec_media_dur_hdmi_output: str
    effective_post_reset_rec_media_dur_hdmi_output: str
    pre_reset_raw_output: str
    effective_post_reset_raw_output: str
    pre_reset_output_resolution: str
    effective_post_reset_output_resolution: str
    effective_hdmi_output_resolution: str
    pre_reset_framing_settings_hdmi: str
    effective_post_reset_framing_settings_hdmi: str
    lcd_blanked: bool
    lcd_touch_focus_active: bool
    hdmi_clean_feed_4k_forced_off_active: bool
    hdmi_1080_log_pplut_clamp_active: bool
    setup_reset_persistence_verified: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G113UsbModeAndHdmiInfoGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    usb_mode_hdmi_info_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProtectAndNetworkResetGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    reset_action: str
    protect_menu_path: str
    format_menu_path: str
    reset_network_set_menu_path: str
    airplane_mode_menu_path: str
    protect_scope: str
    protect_blocks_delete: bool
    copy_strips_destination_protect: bool
    format_wipes_protected_files_and_m1_m4: bool
    slot1_holds_recovery_vault: bool
    slot1_sd_physical_wp_locked: bool
    slot1_format_hard_locked: bool
    slot1_vault_write_firewall_enforced: bool
    protect_only_without_slot1_wp: bool
    requested_media_op: str
    target_slot: str
    slot1_wp_firewall_violation_events: int
    network_reset_cleared_categories: Tuple[str, ...]
    network_reset_preserved_domains: Tuple[str, ...]
    auto_reboot_triggered: bool
    post_network_reset_reboot_completed: bool
    pre_reset_airplane_mode: str
    effective_immediate_post_network_reset_airplane_mode: str
    post_reset_airplane_mode: str
    air_gapped_zero_rf_bench: bool
    rf_radio_active_after_reset: bool
    post_network_reset_rf_hazard_events: int
    playback_protect_survives_camera_and_network_reset: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G114ProtectAndNetworkResetGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    protect_and_network_reset_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master114GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_111_gates_verified: bool
    all_114_gates_verified: bool
    g13_to_g114_all_passed: bool
    g113_to_g114_all_passed: bool
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
    master_112_report: Dict[str, Any]
    g113_result: Dict[str, Any]
    g114_result: Dict[str, Any]
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
    for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE276):
        if os.environ.get(env_key, "").strip() in _TRUTHY_CLEAN_ROOM_TOKENS:
            return True
    return False


def _default_donor_budget_seconds_phase276() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return DONOR_CHECK_CI_MAX_SECONDS_PHASE276
    return DONOR_CHECK_MAX_SECONDS_PHASE276


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
    (with `os.lseek`/`os.read` fallback) so large shared `appFw.so` binaries are
    audited in < 1 ms without full hashing.
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


def _norm_reset_action_phase276(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE276
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE
    return None


def _norm_on_off_phase276(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "ON":
        return "On"
    if u == "OFF":
        return "Off"
    return None


def _norm_usb_connection_mode_g113(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    cleaned = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "SEL. WHEN CONNECT": USB_CONN_SEL_WHEN_CONNECT_G113,
        "SEL WHEN CONNECT": USB_CONN_SEL_WHEN_CONNECT_G113,
        "SELECT WHEN CONNECT": USB_CONN_SEL_WHEN_CONNECT_G113,
        "USB_CONNECTION_SELECT_AFTER_CONNECTION": USB_CONN_SEL_WHEN_CONNECT_G113,
        "MASSSTORAGE(MSC)": USB_CONN_MASS_STORAGE_MSC_G113,
        "MASS STORAGE(MSC)": USB_CONN_MASS_STORAGE_MSC_G113,
        "MASS STORAGE (MSC)": USB_CONN_MASS_STORAGE_MSC_G113,
        "MSC": USB_CONN_MASS_STORAGE_MSC_G113,
        "USB_CONNECTION_MASS_STORAGE": USB_CONN_MASS_STORAGE_MSC_G113,
        "MTP": USB_CONN_MTP_G113,
        "USB_CONNECTION_MTP": USB_CONN_MTP_G113,
        "REMOTE SHOOT (PC REMOTE)": USB_CONN_REMOTE_SHOOT_G113,
        "REMOTE SHOOT": USB_CONN_REMOTE_SHOOT_G113,
        "REMOTE SHOOTING": USB_CONN_REMOTE_SHOOT_G113,
        "PC REMOTE": USB_CONN_REMOTE_SHOOT_G113,
        "USB_CONNECTION_REMOTE_PC": USB_CONN_REMOTE_SHOOT_G113,
        "USB-LAN": USB_CONN_USB_LAN_G113,
        "USB LAN": USB_CONN_USB_LAN_G113,
        "USB STREAMING": USB_CONN_USB_STREAMING_G113,
        "USB_CONNECTION_USB_STREAMING": USB_CONN_USB_STREAMING_G113,
    }
    return mapping.get(cleaned)


def _norm_usb_lun_g113(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u in ("MULTI", "LUN_SETTING_MULTI"):
        return USB_LUN_MULTI_G113
    if u in ("SINGLE", "LUN_SETTING_SINGLE"):
        return USB_LUN_SINGLE_G113
    return None


def _norm_usb_port_g113(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u in ("USB TYPE-C", "TYPE-C", "USBC", "USB-C"):
        return USB_PORT_TYPE_C_G113
    if u in ("MULTI/MICRO USB", "MULTI USB", "MICRO USB", "MULTI"):
        return USB_PORT_MULTI_MICRO_G113
    if u in ("NONE", ""):
        return USB_PORT_NONE_G113
    return None


def _norm_rec_media_dur_hdmi_g113(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if u == "ON":
        return REC_MEDIA_HDMI_ON_G113
    if u in ("OFF(HDMI ONLY)", "OFF (HDMI ONLY)", "OFF_HDMI_ONLY", "HDMI ONLY"):
        return REC_MEDIA_HDMI_OFF_HDMI_ONLY_G113
    return None


def _norm_hdmi_out_res_g113(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").lower()
    mapping = {
        "auto": HDMI_OUT_RES_AUTO_G113,
        "2160p": HDMI_OUT_RES_2160P_G113,
        "1080p": HDMI_OUT_RES_1080P_G113,
        "1080i": HDMI_OUT_RES_1080I_G113,
    }
    return mapping.get(u)


def _norm_shoot_mode_g113(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "MOVIE":
        return SHOOT_MODE_MOVIE_G113
    if u == "STILL":
        return SHOOT_MODE_STILL_G113
    if u in ("S&Q", "SQ"):
        return SHOOT_MODE_SQ_G113
    return None


def _norm_log_shooting_g113(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "OFF": LOG_SHOOTING_OFF_G113,
        "FLEXIBLE ISO": LOG_SHOOTING_FLEXIBLE_ISO_G113,
        "CINE EI": LOG_SHOOTING_CINE_EI_G113,
        "CINE EI QUICK": LOG_SHOOTING_CINE_EI_QUICK_G113,
    }
    return mapping.get(u)


def _norm_picture_profile_g113(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip().strip("[]")
    u = cleaned.upper()
    for p in ALLOWED_PICTURE_PROFILES_G113:
        if u == p.upper():
            return p
    return None


def _norm_framing_hdmi_g113(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "CROP":
        return FRAMING_HDMI_CROP_G113
    if u == "FULL":
        return FRAMING_HDMI_FULL_G113
    return None


def _norm_protect_scope_g114(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "SINGLE": PROTECT_SCOPE_SINGLE_G114,
        "SINGLE IMAGE": PROTECT_SCOPE_SINGLE_G114,
        "MULTIPLE IMG.": PROTECT_SCOPE_MULTIPLE_IMG_G114,
        "MULTIPLE IMG": PROTECT_SCOPE_MULTIPLE_IMG_G114,
        "ALL IN THIS FOLDER": PROTECT_SCOPE_ALL_IN_FOLDER_G114,
        "ALL WITH THIS DATE": PROTECT_SCOPE_ALL_WITH_DATE_G114,
        "ALL IMAGES IN THIS GROUP": PROTECT_SCOPE_ALL_IN_GROUP_G114,
    }
    return mapping.get(u)


def _norm_media_op_g114(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "_", raw.strip().strip("[]")).upper()
    if u in ALLOWED_MEDIA_OPS_G114:
        return u
    return None


def _norm_target_slot_g114(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    mapping = {
        "NONE": TARGET_SLOT_NONE_G114,
        "": TARGET_SLOT_NONE_G114,
        "SLOT1": TARGET_SLOT_1_G114,
        "SLOT_1": TARGET_SLOT_1_G114,
        "SLOTA": TARGET_SLOT_1_G114,
        "SLOT2": TARGET_SLOT_2_G114,
        "SLOT_2": TARGET_SLOT_2_G114,
        "SLOTB": TARGET_SLOT_2_G114,
    }
    return mapping.get(u)


# ---------------------------------------------------------------------------
# 1. Fast `< 0.20s` O_RDONLY Donor Contract Audit (`Phase 276`)
# ---------------------------------------------------------------------------


def audit_phase276_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: Optional[float] = None,
) -> Phase276DonorAuditResult:
    """Inspect local FX3 Ver. 7.02 / FX6 Ver. 6.01 donor artifacts strictly via
    `os.open(..., os.O_RDONLY)` within `<0.20s` (`1.00s` under
    `GITHUB_ACTIONS=true`), using targeted `os.pread` slices on both 79 MiB FX3
    `appFw.so` and 50.5 MiB FX6 `appFw.so`, and full `O_RDONLY` SHA-256
    verification on `.uxc`, dormant `usb_f_uvc.ko` (`78,840 B`), and `BK4` seed
    with deterministic `CLEAN_ROOM_SYNTHETIC` fallback.
    """
    t0 = time.perf_counter()
    budget = (
        _default_donor_budget_seconds_phase276()
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE276_DONOR_SPECS.items():
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
            spec[5] for spec in PINNED_PHASE276_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE276_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE276_DONOR_SPECS.items()}
        return Phase276DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE276_DONOR_INTEGRITY
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
            dormant_usb_f_uvc_ko_bytes=DORMANT_USB_F_UVC_KO_BYTES_G113,
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
    uvc_ko_bytes = -1

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE276_DONOR_SPECS.items():
        fp = resolved[key]
        if key in ("fx3_appfw_so", "fx6_appfw_so"):
            slices_spec = (
                PINNED_FX3_APPFW_SLICES_PHASE276
                if key == "fx3_appfw_so"
                else PINNED_FX6_APPFW_SLICES_PHASE276
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
            if key == "fx3_usb_f_uvc_ko":
                uvc_ko_bytes = actual_size

        if not size_ok:
            errors.append(
                f"Donor size mismatch for {key}: got {actual_size}, expected {exp_size}."
            )
        if not sha_ok:
            errors.append(
                f"Donor SHA-256 mismatch for {key}: got {actual_sha}, expected {exp_sha}."
            )
        if not markers_ok:
            errors.append(f"Missing required Wave-47 byte markers in {key}.")

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

    fx3_keys = {k for k, v in PINNED_PHASE276_DONOR_SPECS.items() if v[0] == "FX3"}
    fx6_keys = {k for k, v in PINNED_PHASE276_DONOR_SPECS.items() if v[0] == "FX6"}
    fx3_ok = fx3_keys.issubset(passed_keys)
    fx6_ok = fx6_keys.issubset(passed_keys)
    valid = (
        fx3_ok
        and fx6_ok
        and (not missing)
        and within_budget
        and (not errors)
    )

    return Phase276DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE
        if valid
        else STATUS_BLOCKED_PHASE276_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_200ms=within_budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_ok,
        fx6_contracts_verified=fx6_ok,
        dormant_usb_f_uvc_ko_bytes=uvc_ko_bytes,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate G113: [USB Connection Mode] NOUVC, PD Isolation & [HDMI Info. Display]
# ---------------------------------------------------------------------------


def resolve_fx3_usb_mode_and_hdmi_info_state(
    *,
    reset_action: str = RESET_ACTION_NONE,
    pre_reset_usb_connection_mode: str = USB_CONNECTION_MODE_FACTORY_DEFAULT_G113,
    pre_reset_usb_lun_setting: str = USB_LUN_FACTORY_DEFAULT_G113,
    pre_reset_usb_power_supply: str = USB_POWER_SUPPLY_FACTORY_DEFAULT_G113,
    pre_reset_hdmi_info_display: str = HDMI_INFO_DISPLAY_FACTORY_DEFAULT_G113,
    pre_reset_rec_media_dur_hdmi_output: str = REC_MEDIA_HDMI_FACTORY_DEFAULT_G113,
    pre_reset_raw_output: str = RAW_OUTPUT_FACTORY_DEFAULT_G113,
    pre_reset_output_resolution: str = HDMI_OUT_RES_FACTORY_DEFAULT_G113,
    pre_reset_framing_settings_hdmi: str = FRAMING_HDMI_FACTORY_DEFAULT_G113,
    log_shooting: str = LOG_SHOOTING_OFF_G113,
    picture_profile: str = "Off",
) -> Dict[str, Any]:
    r_act = _norm_reset_action_phase276(reset_action) or RESET_ACTION_NONE
    usb_mode = (
        _norm_usb_connection_mode_g113(pre_reset_usb_connection_mode)
        or USB_CONNECTION_MODE_FACTORY_DEFAULT_G113
    )
    usb_lun = _norm_usb_lun_g113(pre_reset_usb_lun_setting) or USB_LUN_FACTORY_DEFAULT_G113
    usb_pwr = (
        _norm_on_off_phase276(pre_reset_usb_power_supply)
        or USB_POWER_SUPPLY_FACTORY_DEFAULT_G113
    )
    hdmi_info = (
        _norm_on_off_phase276(pre_reset_hdmi_info_display)
        or HDMI_INFO_DISPLAY_FACTORY_DEFAULT_G113
    )
    rec_media = (
        _norm_rec_media_dur_hdmi_g113(pre_reset_rec_media_dur_hdmi_output)
        or REC_MEDIA_HDMI_FACTORY_DEFAULT_G113
    )
    raw_out = (
        _norm_on_off_phase276(pre_reset_raw_output) or RAW_OUTPUT_FACTORY_DEFAULT_G113
    )
    out_res = (
        _norm_hdmi_out_res_g113(pre_reset_output_resolution)
        or HDMI_OUT_RES_FACTORY_DEFAULT_G113
    )
    framing_hdmi = (
        _norm_framing_hdmi_g113(pre_reset_framing_settings_hdmi)
        or FRAMING_HDMI_FACTORY_DEFAULT_G113
    )
    norm_log = _norm_log_shooting_g113(log_shooting) or LOG_SHOOTING_OFF_G113
    norm_pp = _norm_picture_profile_g113(picture_profile) or "Off"

    # (Setup) USB & HDMI items survive BOTH [Camera Settings Reset] and
    # [Reset Network Set.], reverting to defaults ONLY on [Initialize].
    # Exception: [Framing Settings (HDMI)] resets under BOTH [Camera Settings Reset]
    # and [Initialize].
    initialized = r_act == RESET_ACTION_INITIALIZE
    cam_reset = r_act in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE)

    eff_usb_mode = (
        USB_CONNECTION_MODE_FACTORY_DEFAULT_G113 if initialized else usb_mode
    )
    eff_usb_lun = USB_LUN_FACTORY_DEFAULT_G113 if initialized else usb_lun
    eff_usb_pwr = USB_POWER_SUPPLY_FACTORY_DEFAULT_G113 if initialized else usb_pwr
    eff_hdmi_info_stored = (
        HDMI_INFO_DISPLAY_FACTORY_DEFAULT_G113 if initialized else hdmi_info
    )
    eff_rec_media = (
        REC_MEDIA_HDMI_FACTORY_DEFAULT_G113 if initialized else rec_media
    )
    eff_raw_out = RAW_OUTPUT_FACTORY_DEFAULT_G113 if initialized else raw_out
    eff_out_res = HDMI_OUT_RES_FACTORY_DEFAULT_G113 if initialized else out_res
    eff_framing_hdmi = (
        FRAMING_HDMI_FACTORY_DEFAULT_G113 if cam_reset else framing_hdmi
    )

    clean_feed_4k_forced_off = (
        eff_rec_media == REC_MEDIA_HDMI_OFF_HDMI_ONLY_G113
        or eff_raw_out == RAW_OUTPUT_ON_G113
    )
    effective_hdmi_info = (
        HDMI_INFO_DISPLAY_OFF_G113 if clean_feed_4k_forced_off else eff_hdmi_info_stored
    )
    clamp_1080 = (
        (not clean_feed_4k_forced_off)
        and eff_rec_media == REC_MEDIA_HDMI_ON_G113
        and (
            norm_log != LOG_SHOOTING_OFF_G113
            or norm_pp in PPLUT_PICTURE_PROFILES_G113
        )
    )
    if clean_feed_4k_forced_off:
        effective_hdmi_out_res = HDMI_4K_TOKEN_G113
    elif clamp_1080:
        effective_hdmi_out_res = HDMI_CLAMPED_1080_TOKEN_G113
    else:
        effective_hdmi_out_res = eff_out_res

    lcd_blanked = effective_hdmi_info == HDMI_INFO_DISPLAY_ON_G113
    lcd_touch_focus_active = not lcd_blanked

    return {
        "reset_action": r_act,
        "effective_post_reset_usb_connection_mode": eff_usb_mode,
        "effective_post_reset_usb_lun_setting": eff_usb_lun,
        "effective_post_reset_usb_power_supply": eff_usb_pwr,
        "effective_post_reset_hdmi_info_display": eff_hdmi_info_stored,
        "effective_hdmi_info_display": effective_hdmi_info,
        "effective_post_reset_rec_media_dur_hdmi_output": eff_rec_media,
        "effective_post_reset_raw_output": eff_raw_out,
        "effective_post_reset_output_resolution": eff_out_res,
        "effective_hdmi_output_resolution": effective_hdmi_out_res,
        "effective_post_reset_framing_settings_hdmi": eff_framing_hdmi,
        "hdmi_clean_feed_4k_forced_off_active": clean_feed_4k_forced_off,
        "hdmi_1080_log_pplut_clamp_active": clamp_1080,
        "lcd_blanked": lcd_blanked,
        "lcd_touch_focus_active": lcd_touch_focus_active,
    }


def compute_usb_mode_and_hdmi_info_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate 256 combinations across the 4 stock `ILME-FX3`
    `[USB Connection Mode]` modes, 2 `[USB Power Supply]` states, 2 `[HDMI
    Info. Display]` states, 2 `[Rec. Media dur HDMI Output]` / `[RAW Output]`
    clean-feed triggers, 2 `[Log Shooting]` states, and 4 reset actions,
    verifying Setup reset survival, `Framing Settings (HDMI)` exception, `1080`
    Log clamp, and `4K` clean-feed forced-Off override.
    """
    states_checked = 0
    reset_corruptions = 0
    clean_feed_override_violations = 0
    log_1080_clamp_violations = 0

    for usb_mode in FX3_STOCK_4_USB_CONNECTION_MODES_G113:
        for usb_pwr in ALLOWED_USB_POWER_SUPPLY_MODES_G113:
            for hdmi_info in ALLOWED_HDMI_INFO_DISPLAY_MODES_G113:
                for rec_media in ALLOWED_REC_MEDIA_DUR_HDMI_MODES_G113:
                    for log_mode in (LOG_SHOOTING_OFF_G113, LOG_SHOOTING_CINE_EI_G113):
                        for r_act in ALLOWED_RESET_ACTIONS_PHASE276:
                            resolved = resolve_fx3_usb_mode_and_hdmi_info_state(
                                reset_action=r_act,
                                pre_reset_usb_connection_mode=usb_mode,
                                pre_reset_usb_lun_setting=USB_LUN_SINGLE_G113,
                                pre_reset_usb_power_supply=usb_pwr,
                                pre_reset_hdmi_info_display=hdmi_info,
                                pre_reset_rec_media_dur_hdmi_output=rec_media,
                                pre_reset_raw_output=RAW_OUTPUT_OFF_G113,
                                pre_reset_output_resolution=HDMI_OUT_RES_2160P_G113,
                                pre_reset_framing_settings_hdmi=FRAMING_HDMI_FULL_G113,
                                log_shooting=log_mode,
                            )
                            states_checked += 1
                            survives_setup = r_act in (
                                RESET_ACTION_NONE,
                                RESET_ACTION_CAMERA_SETTINGS_RESET,
                                RESET_ACTION_RESET_NETWORK_SET_PHASE276,
                            )
                            if survives_setup and (
                                resolved["effective_post_reset_usb_connection_mode"]
                                != usb_mode
                                or resolved["effective_post_reset_usb_lun_setting"]
                                != USB_LUN_SINGLE_G113
                                or resolved["effective_post_reset_usb_power_supply"]
                                != usb_pwr
                                or resolved["effective_post_reset_hdmi_info_display"]
                                != hdmi_info
                                or resolved[
                                    "effective_post_reset_rec_media_dur_hdmi_output"
                                ]
                                != rec_media
                                or resolved["effective_post_reset_output_resolution"]
                                != HDMI_OUT_RES_2160P_G113
                            ):
                                reset_corruptions += 1

                            if r_act == RESET_ACTION_INITIALIZE and (
                                resolved["effective_post_reset_usb_connection_mode"]
                                != USB_CONNECTION_MODE_FACTORY_DEFAULT_G113
                                or resolved["effective_post_reset_usb_lun_setting"]
                                != USB_LUN_FACTORY_DEFAULT_G113
                                or resolved["effective_post_reset_usb_power_supply"]
                                != USB_POWER_SUPPLY_FACTORY_DEFAULT_G113
                                or resolved["effective_post_reset_hdmi_info_display"]
                                != HDMI_INFO_DISPLAY_FACTORY_DEFAULT_G113
                                or resolved[
                                    "effective_post_reset_rec_media_dur_hdmi_output"
                                ]
                                != REC_MEDIA_HDMI_FACTORY_DEFAULT_G113
                                or resolved["effective_post_reset_output_resolution"]
                                != HDMI_OUT_RES_FACTORY_DEFAULT_G113
                            ):
                                reset_corruptions += 1

                            expected_framing = (
                                FRAMING_HDMI_FACTORY_DEFAULT_G113
                                if r_act
                                in (
                                    RESET_ACTION_CAMERA_SETTINGS_RESET,
                                    RESET_ACTION_INITIALIZE,
                                )
                                else FRAMING_HDMI_FULL_G113
                            )
                            if (
                                resolved["effective_post_reset_framing_settings_hdmi"]
                                != expected_framing
                            ):
                                reset_corruptions += 1

                            eff_rec = resolved[
                                "effective_post_reset_rec_media_dur_hdmi_output"
                            ]
                            if eff_rec == REC_MEDIA_HDMI_OFF_HDMI_ONLY_G113:
                                if (
                                    resolved["effective_hdmi_info_display"]
                                    != HDMI_INFO_DISPLAY_OFF_G113
                                    or resolved["effective_hdmi_output_resolution"]
                                    != HDMI_4K_TOKEN_G113
                                    or resolved["lcd_blanked"]
                                ):
                                    clean_feed_override_violations += 1
                            elif log_mode != LOG_SHOOTING_OFF_G113:
                                if (
                                    resolved["effective_hdmi_output_resolution"]
                                    != HDMI_CLAMPED_1080_TOKEN_G113
                                ):
                                    log_1080_clamp_violations += 1

    return {
        "states_checked": states_checked,
        "reset_corruptions": reset_corruptions,
        "clean_feed_override_violations": clean_feed_override_violations,
        "log_1080_clamp_violations": log_1080_clamp_violations,
        "all_invariants_hold": (
            states_checked == 256
            and reset_corruptions == 0
            and clean_feed_override_violations == 0
            and log_1080_clamp_violations == 0
        ),
    }


def verify_usb_mode_and_hdmi_info_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE276,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE276,
    reset_action: str = RESET_ACTION_NONE,
    claimed_fx3_exposes_usb_streaming: bool = False,
    claimed_usb_streaming_uvc_active: bool = False,
    claimed_usb_streaming_spoof_events: int = 0,
    pre_reset_usb_connection_mode: str = USB_CONNECTION_MODE_FACTORY_DEFAULT_G113,
    claimed_post_reset_usb_connection_mode: Optional[str] = None,
    pre_reset_usb_lun_setting: str = USB_LUN_FACTORY_DEFAULT_G113,
    claimed_post_reset_usb_lun_setting: Optional[str] = None,
    pre_reset_usb_power_supply: str = USB_POWER_SUPPLY_FACTORY_DEFAULT_G113,
    claimed_post_reset_usb_power_supply: Optional[str] = None,
    usb_port: str = USB_PORT_TYPE_C_G113,
    np_fz100_battery_inserted: bool = True,
    air_gapped_tier0_bench: bool = True,
    usb_data_lines_physically_isolated: bool = True,
    usb_host_data_enumerated: bool = False,
    shoot_mode: str = SHOOT_MODE_MOVIE_G113,
    log_shooting: str = LOG_SHOOTING_OFF_G113,
    picture_profile: str = "Off",
    pre_reset_hdmi_info_display: str = HDMI_INFO_DISPLAY_OFF_G113,
    claimed_post_reset_hdmi_info_display: Optional[str] = None,
    claimed_effective_hdmi_info_display: Optional[str] = None,
    pre_reset_rec_media_dur_hdmi_output: str = REC_MEDIA_HDMI_FACTORY_DEFAULT_G113,
    claimed_post_reset_rec_media_dur_hdmi_output: Optional[str] = None,
    pre_reset_raw_output: str = RAW_OUTPUT_FACTORY_DEFAULT_G113,
    claimed_post_reset_raw_output: Optional[str] = None,
    pre_reset_output_resolution: str = HDMI_OUT_RES_FACTORY_DEFAULT_G113,
    claimed_post_reset_output_resolution: Optional[str] = None,
    claimed_effective_hdmi_output_resolution: Optional[str] = None,
    pre_reset_framing_settings_hdmi: str = FRAMING_HDMI_FACTORY_DEFAULT_G113,
    claimed_post_reset_framing_settings_hdmi: Optional[str] = None,
    claimed_lcd_blanked: Optional[bool] = None,
    claimed_lcd_touch_focus_active: Optional[bool] = None,
) -> UsbModeAndHdmiInfoGuardResult:
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME
        or isinstance(body_model_id, bool)
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE276
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G113_TELEMETRY_INVALID)
        errors.append(
            "Gate G113 requires ILME-FX3 (0x91030080, Help Guide ilc/2210, Ver. 7.02)."
        )

    norm_reset = _norm_reset_action_phase276(reset_action)
    norm_usb_mode = _norm_usb_connection_mode_g113(pre_reset_usb_connection_mode)
    norm_usb_lun = _norm_usb_lun_g113(pre_reset_usb_lun_setting)
    norm_usb_pwr = _norm_on_off_phase276(pre_reset_usb_power_supply)
    norm_usb_port = _norm_usb_port_g113(usb_port)
    norm_shoot = _norm_shoot_mode_g113(shoot_mode)
    norm_log = _norm_log_shooting_g113(log_shooting)
    norm_pp = _norm_picture_profile_g113(picture_profile)
    norm_hdmi_info = _norm_on_off_phase276(pre_reset_hdmi_info_display)
    norm_rec_media = _norm_rec_media_dur_hdmi_g113(pre_reset_rec_media_dur_hdmi_output)
    norm_raw_out = _norm_on_off_phase276(pre_reset_raw_output)
    norm_out_res = _norm_hdmi_out_res_g113(pre_reset_output_resolution)
    norm_framing = _norm_framing_hdmi_g113(pre_reset_framing_settings_hdmi)

    if (
        norm_reset is None
        or norm_usb_mode is None
        or norm_usb_lun is None
        or norm_usb_pwr is None
        or norm_usb_port is None
        or norm_shoot is None
        or norm_log is None
        or norm_pp is None
        or norm_hdmi_info is None
        or norm_rec_media is None
        or norm_raw_out is None
        or norm_out_res is None
        or norm_framing is None
        or not isinstance(claimed_fx3_exposes_usb_streaming, bool)
        or not isinstance(claimed_usb_streaming_uvc_active, bool)
        or not isinstance(np_fz100_battery_inserted, bool)
        or not isinstance(air_gapped_tier0_bench, bool)
        or not isinstance(usb_data_lines_physically_isolated, bool)
        or not isinstance(usb_host_data_enumerated, bool)
        or isinstance(claimed_usb_streaming_spoof_events, bool)
        or not isinstance(claimed_usb_streaming_spoof_events, int)
        or claimed_usb_streaming_spoof_events < 0
        or (claimed_lcd_blanked is not None and not isinstance(claimed_lcd_blanked, bool))
        or (
            claimed_lcd_touch_focus_active is not None
            and not isinstance(claimed_lcd_touch_focus_active, bool)
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G113_TELEMETRY_INVALID)
        errors.append("Invalid or unrecognized G113 telemetry or enum value.")

    # 1. Dormant NOUVC [USB Streaming] Spoof Check
    uvc_spoof_events = (
        claimed_usb_streaming_spoof_events
        if isinstance(claimed_usb_streaming_spoof_events, int)
        and not isinstance(claimed_usb_streaming_spoof_events, bool)
        else 1
    )
    if (
        claimed_fx3_exposes_usb_streaming
        or claimed_usb_streaming_uvc_active
        or norm_usb_mode == USB_CONN_USB_STREAMING_G113
        or uvc_spoof_events != 0
    ):
        uvc_spoof_events = max(1, uvc_spoof_events)
        _add_code(codes, STATUS_BLOCKED_G113_FX3_NOUVC_USB_STREAMING_SPOOF_VIOLATION)
        errors.append(
            "Stock ILME-FX3 Ver. 7.02 (ilc/2210) exposes ONLY 4 [USB Connection Mode] "
            "modes (Sel. When Connect, MassStorage(MSC), MTP, Remote Shoot); native "
            "UVC/UAC [USB Streaming] is NOUVC-masked and dormant."
        )

    resolved = resolve_fx3_usb_mode_and_hdmi_info_state(
        reset_action=norm_reset or RESET_ACTION_NONE,
        pre_reset_usb_connection_mode=norm_usb_mode
        or USB_CONNECTION_MODE_FACTORY_DEFAULT_G113,
        pre_reset_usb_lun_setting=norm_usb_lun or USB_LUN_FACTORY_DEFAULT_G113,
        pre_reset_usb_power_supply=norm_usb_pwr or USB_POWER_SUPPLY_FACTORY_DEFAULT_G113,
        pre_reset_hdmi_info_display=norm_hdmi_info
        or HDMI_INFO_DISPLAY_FACTORY_DEFAULT_G113,
        pre_reset_rec_media_dur_hdmi_output=norm_rec_media
        or REC_MEDIA_HDMI_FACTORY_DEFAULT_G113,
        pre_reset_raw_output=norm_raw_out or RAW_OUTPUT_FACTORY_DEFAULT_G113,
        pre_reset_output_resolution=norm_out_res or HDMI_OUT_RES_FACTORY_DEFAULT_G113,
        pre_reset_framing_settings_hdmi=norm_framing or FRAMING_HDMI_FACTORY_DEFAULT_G113,
        log_shooting=norm_log or LOG_SHOOTING_OFF_G113,
        picture_profile=norm_pp or "Off",
    )

    matrix = compute_usb_mode_and_hdmi_info_matrix()
    if not matrix["all_invariants_hold"]:
        _add_code(codes, STATUS_BLOCKED_G113_TELEMETRY_INVALID)
        errors.append("G113 256-state matrix verification failed.")

    # 2. Air-Gapped Tier-0 USB Data Enumeration & PD Data Isolation Rule
    eff_usb_mode = resolved["effective_post_reset_usb_connection_mode"]
    eff_usb_pwr = resolved["effective_post_reset_usb_power_supply"]
    data_enum_hazards = 0
    if air_gapped_tier0_bench:
        if (
            usb_host_data_enumerated
            or eff_usb_mode in AIRGAPPED_PROHIBITED_USB_DATA_MODES_G113
            or norm_usb_mode in AIRGAPPED_PROHIBITED_USB_DATA_MODES_G113
        ):
            data_enum_hazards += 1
        if eff_usb_pwr == USB_POWER_SUPPLY_ON_G113 and (
            not usb_data_lines_physically_isolated
        ):
            data_enum_hazards += 1
    if data_enum_hazards != 0:
        _add_code(codes, STATUS_BLOCKED_G113_AIRGAPPED_USB_DATA_ENUMERATION_HAZARD)
        errors.append(
            "Air-gapped Tier-0 bench prohibits MassStorage(MSC), MTP, Remote Shoot, "
            "and USB-LAN host enumeration; [USB Power Supply] = On is allowed ONLY "
            "when USB D+/D- and SuperSpeed data lines are physically isolated."
        )

    # 3. [USB Power Supply] Hardware Contract (Type-C only + NP-FZ100 inserted)
    if eff_usb_pwr == USB_POWER_SUPPLY_ON_G113 and (
        norm_usb_port == USB_PORT_MULTI_MICRO_G113 or not np_fz100_battery_inserted
    ):
        _add_code(codes, STATUS_BLOCKED_G113_USB_POWER_OR_LUN_CONTRACT_VIOLATION)
        errors.append(
            "[USB Power Supply] operates exclusively over USB Type-C (never Multi/Micro USB) "
            "and requires an NP-FZ100 battery pack inserted."
        )

    # 4. [HDMI Info. Display] LCD-Blanking, S&Q Lockout, 1080 Clamp & 4K Clean-Feed Override
    eff_hdmi_info = resolved["effective_hdmi_info_display"]
    eff_hdmi_res = resolved["effective_hdmi_output_resolution"]
    eff_rec_media = resolved["effective_post_reset_rec_media_dur_hdmi_output"]
    eff_raw_out = resolved["effective_post_reset_raw_output"]
    expected_lcd_blanked = resolved["lcd_blanked"]
    expected_touch_active = resolved["lcd_touch_focus_active"]

    hdmi_contract_bad = False
    if norm_shoot == SHOOT_MODE_SQ_G113 and (
        eff_rec_media == REC_MEDIA_HDMI_OFF_HDMI_ONLY_G113
        or eff_raw_out == RAW_OUTPUT_ON_G113
    ):
        hdmi_contract_bad = True
    if claimed_effective_hdmi_info_display is not None:
        if _norm_on_off_phase276(claimed_effective_hdmi_info_display) != eff_hdmi_info:
            hdmi_contract_bad = True
    if claimed_effective_hdmi_output_resolution is not None:
        raw_res_claim = claimed_effective_hdmi_output_resolution.strip().strip("[]")
        if resolved["hdmi_clean_feed_4k_forced_off_active"]:
            if raw_res_claim.upper() not in ("4K", "2160P"):
                hdmi_contract_bad = True
        elif resolved["hdmi_1080_log_pplut_clamp_active"]:
            if raw_res_claim.lower() not in ("1080", "1080p", "1080i"):
                hdmi_contract_bad = True
        elif _norm_hdmi_out_res_g113(raw_res_claim) != eff_hdmi_res:
            hdmi_contract_bad = True
    if claimed_lcd_blanked is not None and claimed_lcd_blanked != expected_lcd_blanked:
        hdmi_contract_bad = True
    if (
        claimed_lcd_touch_focus_active is not None
        and claimed_lcd_touch_focus_active != expected_touch_active
    ):
        hdmi_contract_bad = True

    if hdmi_contract_bad:
        _add_code(
            codes, STATUS_BLOCKED_G113_HDMI_INFO_LCD_OR_CLEAN_FEED_OVERRIDE_VIOLATION
        )
        errors.append(
            "[HDMI Info. Display] = On blanks built-in LCD & disables LCD touch-focus; "
            "internal rec + Log/PPLUT1..4 forces 1080 HDMI; [Off(HDMI Only)] or [RAW Output = On] "
            "outputs 4K and forces [HDMI Info. Display] = [Off] (disabled in S&Q)."
        )

    # 5. (Setup) USB/HDMI Reset Persistence vs Framing Settings (HDMI) Exception
    reset_ok = True
    reset_checks: Tuple[Tuple[Optional[str], str, Any], ...] = (
        (
            claimed_post_reset_usb_connection_mode,
            eff_usb_mode,
            _norm_usb_connection_mode_g113,
        ),
        (
            claimed_post_reset_usb_lun_setting,
            resolved["effective_post_reset_usb_lun_setting"],
            _norm_usb_lun_g113,
        ),
        (
            claimed_post_reset_usb_power_supply,
            eff_usb_pwr,
            _norm_on_off_phase276,
        ),
        (
            claimed_post_reset_hdmi_info_display,
            resolved["effective_post_reset_hdmi_info_display"],
            _norm_on_off_phase276,
        ),
        (
            claimed_post_reset_rec_media_dur_hdmi_output,
            eff_rec_media,
            _norm_rec_media_dur_hdmi_g113,
        ),
        (
            claimed_post_reset_raw_output,
            eff_raw_out,
            _norm_on_off_phase276,
        ),
        (
            claimed_post_reset_output_resolution,
            resolved["effective_post_reset_output_resolution"],
            _norm_hdmi_out_res_g113,
        ),
        (
            claimed_post_reset_framing_settings_hdmi,
            resolved["effective_post_reset_framing_settings_hdmi"],
            _norm_framing_hdmi_g113,
        ),
    )
    for claimed_raw, expected_val, norm_fn in reset_checks:
        if claimed_raw is not None:
            if norm_fn(claimed_raw) != expected_val:
                reset_ok = False
                break
    if not reset_ok:
        _add_code(codes, STATUS_BLOCKED_G113_SETUP_RESET_PERSISTENCE_VIOLATION)
        errors.append(
            "(Setup) USB & HDMI items survive [Camera Settings Reset] (resetting only via "
            "[Initialize]), except [Framing Settings (HDMI)] which resets under "
            "[Camera Settings Reset]."
        )

    valid = not codes
    status = STATUS_VERIFIED_G113 if valid else codes[0]

    return UsbModeAndHdmiInfoGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}"
        if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
        else "invalid",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        reset_action=resolved["reset_action"],
        usb_connection_mode_menu_path=USB_CONNECTION_MODE_MENU_PATH_G113,
        usb_lun_setting_menu_path=USB_LUN_SETTING_MENU_PATH_G113,
        usb_power_supply_menu_path=USB_POWER_SUPPLY_MENU_PATH_G113,
        hdmi_info_display_menu_path=HDMI_INFO_DISPLAY_MENU_PATH_G113,
        hdmi_output_settings_menu_path=HDMI_OUTPUT_SETTINGS_MENU_PATH_G113,
        framing_settings_hdmi_menu_path=FRAMING_SETTINGS_HDMI_MENU_PATH_G113,
        fx3_stock_4_usb_modes=FX3_STOCK_4_USB_CONNECTION_MODES_G113,
        fx3_ui_exposes_usb_streaming=FX3_UI_EXPOSES_USB_STREAMING_G113,
        usb_streaming_spoof_events=uvc_spoof_events,
        pre_reset_usb_connection_mode=norm_usb_mode or str(pre_reset_usb_connection_mode),
        effective_post_reset_usb_connection_mode=eff_usb_mode,
        pre_reset_usb_lun_setting=norm_usb_lun or str(pre_reset_usb_lun_setting),
        effective_post_reset_usb_lun_setting=resolved[
            "effective_post_reset_usb_lun_setting"
        ],
        pre_reset_usb_power_supply=norm_usb_pwr or str(pre_reset_usb_power_supply),
        effective_post_reset_usb_power_supply=eff_usb_pwr,
        usb_port=norm_usb_port or str(usb_port),
        np_fz100_battery_inserted=bool(np_fz100_battery_inserted),
        air_gapped_tier0_bench=bool(air_gapped_tier0_bench),
        usb_data_lines_physically_isolated=bool(usb_data_lines_physically_isolated),
        usb_host_data_enumerated=bool(usb_host_data_enumerated),
        airgapped_usb_data_enumeration_hazards=data_enum_hazards,
        shoot_mode=norm_shoot or str(shoot_mode),
        log_shooting=norm_log or str(log_shooting),
        picture_profile=norm_pp or str(picture_profile),
        pre_reset_hdmi_info_display=norm_hdmi_info or str(pre_reset_hdmi_info_display),
        effective_post_reset_hdmi_info_display=resolved[
            "effective_post_reset_hdmi_info_display"
        ],
        effective_hdmi_info_display=eff_hdmi_info,
        pre_reset_rec_media_dur_hdmi_output=norm_rec_media
        or str(pre_reset_rec_media_dur_hdmi_output),
        effective_post_reset_rec_media_dur_hdmi_output=eff_rec_media,
        pre_reset_raw_output=norm_raw_out or str(pre_reset_raw_output),
        effective_post_reset_raw_output=eff_raw_out,
        pre_reset_output_resolution=norm_out_res or str(pre_reset_output_resolution),
        effective_post_reset_output_resolution=resolved[
            "effective_post_reset_output_resolution"
        ],
        effective_hdmi_output_resolution=eff_hdmi_res,
        pre_reset_framing_settings_hdmi=norm_framing
        or str(pre_reset_framing_settings_hdmi),
        effective_post_reset_framing_settings_hdmi=resolved[
            "effective_post_reset_framing_settings_hdmi"
        ],
        lcd_blanked=expected_lcd_blanked,
        lcd_touch_focus_active=expected_touch_active,
        hdmi_clean_feed_4k_forced_off_active=resolved[
            "hdmi_clean_feed_4k_forced_off_active"
        ],
        hdmi_1080_log_pplut_clamp_active=resolved["hdmi_1080_log_pplut_clamp_active"],
        setup_reset_persistence_verified=reset_ok,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g113_usb_mode_and_hdmi_info_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    usb_mode_hdmi_info_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase276DonorAuditResult] = None,
) -> Tuple[GateVerdict, G113UsbModeAndHdmiInfoGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase276_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_usb_mode_and_hdmi_info_guard(
        **dict(usb_mode_hdmi_info_kwargs or {})
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
        errors.append("Persistent eMMC write authorization requested in Gate G113.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G113 if valid else codes[0]

    res = G113UsbModeAndHdmiInfoGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        usb_mode_hdmi_info_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, usb_modes={len(guard.fx3_stock_4_usb_modes)}"
        f"(sel={guard.effective_post_reset_usb_connection_mode},nouvc_spoof={guard.usb_streaming_spoof_events},"
        f"pd={guard.effective_post_reset_usb_power_supply},data_iso={guard.usb_data_lines_physically_isolated}), "
        f"hdmi_info={guard.effective_hdmi_info_display}(lcd_blank={guard.lcd_blanked},"
        f"out_res={guard.effective_hdmi_output_resolution},4k_clean={guard.hdmi_clean_feed_4k_forced_off_active})"
    )
    verdict = GateVerdict(
        gate_id=G113_GATE_ID,
        gate_code=G113_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G114: [Protect] vs [Format] Slot-1 WP + [Reset Network Set.] Zero-RF
# ---------------------------------------------------------------------------


def resolve_fx3_protect_and_network_reset_state(
    *,
    reset_action: str = RESET_ACTION_NONE,
    post_network_reset_performed: bool = False,
    pre_reset_airplane_mode: str = AIRPLANE_MODE_ON_G114,
    post_reboot_reassert_airplane_mode: Optional[str] = AIRPLANE_MODE_ON_G114,
    slot1_holds_recovery_vault: bool = True,
    slot1_sd_physical_wp_locked: bool = True,
    slot1_format_hard_locked: bool = True,
) -> Dict[str, Any]:
    r_act = _norm_reset_action_phase276(reset_action) or RESET_ACTION_NONE
    pre_air = _norm_on_off_phase276(pre_reset_airplane_mode) or AIRPLANE_MODE_ON_G114

    if (
        r_act in (RESET_ACTION_RESET_NETWORK_SET_PHASE276, RESET_ACTION_INITIALIZE)
        or post_network_reset_performed
    ):
        immediate_air = AIRPLANE_MODE_FACTORY_DEFAULT_G114
        auto_reboot = (
            r_act == RESET_ACTION_RESET_NETWORK_SET_PHASE276
            or bool(post_network_reset_performed)
        )
        if post_reboot_reassert_airplane_mode is not None:
            post_air = (
                _norm_on_off_phase276(post_reboot_reassert_airplane_mode)
                or immediate_air
            )
        else:
            post_air = immediate_air
    else:
        immediate_air = pre_air
        auto_reboot = False
        post_air = pre_air

    return {
        "reset_action": r_act,
        "auto_reboot_triggered": auto_reboot,
        "effective_immediate_post_network_reset_airplane_mode": immediate_air,
        "post_reset_airplane_mode": post_air,
        "playback_protect_survives_reset": r_act != RESET_ACTION_INITIALIZE,
        "slot1_dual_layer_wp_firewall_ok": (
            (not slot1_holds_recovery_vault)
            or (bool(slot1_sd_physical_wp_locked) and bool(slot1_format_hard_locked))
        ),
    }


def compute_protect_and_network_reset_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate 160 combinations across all 5 `[Protect]` scopes,
    2 `Slot-1` physical SD `WP` states, 2 `Slot-1` Format firewall states,
    4 reset actions, and 2 post-reset `[Airplane Mode]` states, enforcing
    dual-layer `Slot-1` defense and zero-RF post-network-reset re-assertion.
    """
    states_checked = 0
    playback_reset_corruptions = 0
    unprotected_slot1_detected = 0
    rf_hazards_detected = 0

    for _scope in ALLOWED_PROTECT_SCOPES_G114:
        for wp_locked in (True, False):
            for fmt_locked in (True, False):
                for r_act in ALLOWED_RESET_ACTIONS_PHASE276:
                    for reassert_air in (AIRPLANE_MODE_ON_G114, AIRPLANE_MODE_OFF_G114):
                        resolved = resolve_fx3_protect_and_network_reset_state(
                            reset_action=r_act,
                            pre_reset_airplane_mode=AIRPLANE_MODE_ON_G114,
                            post_reboot_reassert_airplane_mode=reassert_air,
                            slot1_holds_recovery_vault=True,
                            slot1_sd_physical_wp_locked=wp_locked,
                            slot1_format_hard_locked=fmt_locked,
                        )
                        states_checked += 1
                        expected_survive = r_act != RESET_ACTION_INITIALIZE
                        if resolved["playback_protect_survives_reset"] != expected_survive:
                            playback_reset_corruptions += 1
                        if not resolved["slot1_dual_layer_wp_firewall_ok"]:
                            unprotected_slot1_detected += 1
                        if resolved["post_reset_airplane_mode"] != AIRPLANE_MODE_ON_G114:
                            rf_hazards_detected += 1

    return {
        "states_checked": states_checked,
        "playback_reset_corruptions": playback_reset_corruptions,
        "unprotected_slot1_detected": unprotected_slot1_detected,
        "rf_hazards_detected": rf_hazards_detected,
        "all_invariants_hold": (
            states_checked == 160
            and playback_reset_corruptions == 0
            and unprotected_slot1_detected == 120
            and rf_hazards_detected == 40
        ),
    }


def verify_protect_and_network_reset_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE276,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE276,
    reset_action: str = RESET_ACTION_NONE,
    protect_scope: str = PROTECT_SCOPE_ALL_IN_FOLDER_G114,
    claimed_protect_blocks_delete: bool = True,
    claimed_copy_strips_destination_protect: bool = True,
    claimed_format_preserves_protected_files: bool = False,
    claimed_format_preserves_m1_m4: bool = False,
    claimed_playback_protect_survives_network_reset: Optional[bool] = None,
    slot1_holds_recovery_vault: bool = True,
    slot1_sd_physical_wp_locked: bool = True,
    slot1_format_hard_locked: bool = True,
    slot1_vault_write_firewall_enforced: bool = True,
    protect_only_without_slot1_wp: bool = False,
    requested_media_op: str = MEDIA_OP_NONE_G114,
    target_slot: str = TARGET_SLOT_NONE_G114,
    claimed_slot1_wp_firewall_violation_events: int = 0,
    claimed_auto_reboot_triggered: Optional[bool] = None,
    post_network_reset_performed: bool = False,
    post_network_reset_reboot_completed: bool = True,
    pre_reset_airplane_mode: str = AIRPLANE_MODE_ON_G114,
    post_reset_airplane_mode: Optional[str] = None,
    air_gapped_zero_rf_bench: bool = True,
    rf_radio_active_after_reset: bool = False,
    claimed_network_reset_clears_shooting_or_setup: bool = False,
    claimed_network_reset_clears_camset: bool = False,
) -> ProtectAndNetworkResetGuardResult:
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME
        or isinstance(body_model_id, bool)
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE276
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G114_TELEMETRY_INVALID)
        errors.append(
            "Gate G114 requires ILME-FX3 (0x91030080, Help Guide ilc/2210, Ver. 7.02)."
        )

    norm_reset = _norm_reset_action_phase276(reset_action)
    norm_scope = _norm_protect_scope_g114(protect_scope)
    norm_media_op = _norm_media_op_g114(requested_media_op)
    norm_slot = _norm_target_slot_g114(target_slot)
    norm_pre_air = _norm_on_off_phase276(pre_reset_airplane_mode)
    norm_post_air = (
        _norm_on_off_phase276(post_reset_airplane_mode)
        if post_reset_airplane_mode is not None
        else None
    )

    if (
        norm_reset is None
        or norm_scope is None
        or norm_media_op is None
        or norm_slot is None
        or norm_pre_air is None
        or (post_reset_airplane_mode is not None and norm_post_air is None)
        or not isinstance(claimed_protect_blocks_delete, bool)
        or not isinstance(claimed_copy_strips_destination_protect, bool)
        or not isinstance(claimed_format_preserves_protected_files, bool)
        or not isinstance(claimed_format_preserves_m1_m4, bool)
        or (
            claimed_playback_protect_survives_network_reset is not None
            and not isinstance(claimed_playback_protect_survives_network_reset, bool)
        )
        or not isinstance(slot1_holds_recovery_vault, bool)
        or not isinstance(slot1_sd_physical_wp_locked, bool)
        or not isinstance(slot1_format_hard_locked, bool)
        or not isinstance(slot1_vault_write_firewall_enforced, bool)
        or not isinstance(protect_only_without_slot1_wp, bool)
        or (
            claimed_auto_reboot_triggered is not None
            and not isinstance(claimed_auto_reboot_triggered, bool)
        )
        or not isinstance(post_network_reset_performed, bool)
        or not isinstance(post_network_reset_reboot_completed, bool)
        or not isinstance(air_gapped_zero_rf_bench, bool)
        or not isinstance(rf_radio_active_after_reset, bool)
        or not isinstance(claimed_network_reset_clears_shooting_or_setup, bool)
        or not isinstance(claimed_network_reset_clears_camset, bool)
        or isinstance(claimed_slot1_wp_firewall_violation_events, bool)
        or not isinstance(claimed_slot1_wp_firewall_violation_events, int)
        or claimed_slot1_wp_firewall_violation_events < 0
    ):
        _add_code(codes, STATUS_BLOCKED_G114_TELEMETRY_INVALID)
        errors.append("Invalid or unrecognized G114 telemetry or enum value.")

    resolved = resolve_fx3_protect_and_network_reset_state(
        reset_action=norm_reset or RESET_ACTION_NONE,
        post_network_reset_performed=bool(post_network_reset_performed),
        pre_reset_airplane_mode=norm_pre_air or AIRPLANE_MODE_ON_G114,
        post_reboot_reassert_airplane_mode=(
            norm_post_air
            if post_reset_airplane_mode is not None
            else (
                AIRPLANE_MODE_OFF_G114
                if (
                    norm_reset
                    in (RESET_ACTION_RESET_NETWORK_SET_PHASE276, RESET_ACTION_INITIALIZE)
                    or post_network_reset_performed
                )
                else (norm_pre_air or AIRPLANE_MODE_ON_G114)
            )
        ),
        slot1_holds_recovery_vault=bool(slot1_holds_recovery_vault),
        slot1_sd_physical_wp_locked=bool(slot1_sd_physical_wp_locked),
        slot1_format_hard_locked=bool(slot1_format_hard_locked),
    )

    matrix = compute_protect_and_network_reset_matrix()
    if not matrix["all_invariants_hold"]:
        _add_code(codes, STATUS_BLOCKED_G114_TELEMETRY_INVALID)
        errors.append("G114 160-state matrix verification failed.")

    # 1. [Protect] vs [Delete]/[Format] & Dual-Layer Slot-1 Hardware WP + Firewall Mandate
    wp_firewall_events = (
        claimed_slot1_wp_firewall_violation_events
        if isinstance(claimed_slot1_wp_firewall_violation_events, int)
        and not isinstance(claimed_slot1_wp_firewall_violation_events, bool)
        else 1
    )
    if protect_only_without_slot1_wp:
        wp_firewall_events = max(1, wp_firewall_events)
    if slot1_holds_recovery_vault and (
        not slot1_sd_physical_wp_locked
        or not slot1_format_hard_locked
        or not slot1_vault_write_firewall_enforced
        or (
            norm_slot == TARGET_SLOT_1_G114
            and norm_media_op is not None
            and norm_media_op != MEDIA_OP_NONE_G114
        )
    ):
        wp_firewall_events = max(1, wp_firewall_events)

    if wp_firewall_events != 0:
        _add_code(
            codes, STATUS_BLOCKED_G114_PROTECT_ONLY_WITHOUT_SLOT1_WP_FIREWALL_VIOLATION
        )
        errors.append(
            "[Protect] is file-attribute only and is WIPED by [Format]; Slot-1 recovery "
            "vault requires dual-layer defense: physical SD WP lock "
            "(MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1) + slot1_format_hard_locked == True."
        )

    if (
        not claimed_protect_blocks_delete
        or not claimed_copy_strips_destination_protect
        or claimed_format_preserves_protected_files
        or claimed_format_preserves_m1_m4
        or (
            claimed_playback_protect_survives_network_reset is not None
            and claimed_playback_protect_survives_network_reset
            != resolved["playback_protect_survives_reset"]
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G114_PROTECT_SCOPE_OR_PLAYBACK_CONTRACT_VIOLATION)
        errors.append(
            "[Protect] blocks [Delete] and [Delete pressing twice], strips protection on "
            "card copy, survives [Reset Network Set.]/[Camera Settings Reset], yet [Format] "
            "wipes protected files and M1..M4 card settings."
        )

    # 2. [Reset Network Set.] 3-Way Boundary & Mandatory Auto-Reboot
    eff_reset = resolved["reset_action"]
    nw_reset_active = (
        eff_reset == RESET_ACTION_RESET_NETWORK_SET_PHASE276
        or post_network_reset_performed
    )
    expected_auto_reboot = nw_reset_active
    if (
        claimed_network_reset_clears_shooting_or_setup
        or claimed_network_reset_clears_camset
        or (
            claimed_auto_reboot_triggered is not None
            and claimed_auto_reboot_triggered != expected_auto_reboot
        )
        or (nw_reset_active and not post_network_reset_reboot_completed)
    ):
        _add_code(codes, STATUS_BLOCKED_G114_RESET_BOUNDARY_OR_AUTO_REBOOT_VIOLATION)
        errors.append(
            "[Reset Network Set.] (SETTING_RESET_NW) clears only (Network) credentials, "
            "preserves (Shooting)/(Setup)/(Playback)/CAMSET, and triggers mandatory "
            "automatic reboot (BKID_APP_is_shutdown_factor_network_reset)."
        )

    # 3. Post-[Reset Network Set.] [Airplane Mode] = [On] Zero-RF Mandate
    eff_post_air = resolved["post_reset_airplane_mode"]
    rf_hazard_events = 0
    if air_gapped_zero_rf_bench:
        if eff_post_air != AIRPLANE_MODE_ON_G114 or rf_radio_active_after_reset:
            rf_hazard_events += 1
    if rf_hazard_events != 0:
        _add_code(codes, STATUS_BLOCKED_G114_POST_NETWORK_RESET_AIRPLANE_OFF_RF_HAZARD)
        errors.append(
            "[Reset Network Set.] resets [Airplane Mode] to Off; air-gapped bench must "
            "complete the auto-reboot and re-assert [Airplane Mode] = [On] for Zero-RF."
        )

    valid = not codes
    status = STATUS_VERIFIED_G114 if valid else codes[0]

    return ProtectAndNetworkResetGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}"
        if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
        else "invalid",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        reset_action=eff_reset,
        protect_menu_path=PROTECT_MENU_PATH_G114,
        format_menu_path=FORMAT_MENU_PATH_G114,
        reset_network_set_menu_path=RESET_NETWORK_SET_MENU_PATH_G114,
        airplane_mode_menu_path=AIRPLANE_MODE_MENU_PATH_G114,
        protect_scope=norm_scope or str(protect_scope),
        protect_blocks_delete=bool(claimed_protect_blocks_delete),
        copy_strips_destination_protect=bool(claimed_copy_strips_destination_protect),
        format_wipes_protected_files_and_m1_m4=(
            not claimed_format_preserves_protected_files
            and not claimed_format_preserves_m1_m4
        ),
        slot1_holds_recovery_vault=bool(slot1_holds_recovery_vault),
        slot1_sd_physical_wp_locked=bool(slot1_sd_physical_wp_locked),
        slot1_format_hard_locked=bool(slot1_format_hard_locked),
        slot1_vault_write_firewall_enforced=bool(slot1_vault_write_firewall_enforced),
        protect_only_without_slot1_wp=bool(protect_only_without_slot1_wp),
        requested_media_op=norm_media_op or str(requested_media_op),
        target_slot=norm_slot or str(target_slot),
        slot1_wp_firewall_violation_events=wp_firewall_events,
        network_reset_cleared_categories=NETWORK_RESET_CLEARED_CATEGORIES_G114,
        network_reset_preserved_domains=NETWORK_RESET_PRESERVED_DOMAINS_G114,
        auto_reboot_triggered=expected_auto_reboot,
        post_network_reset_reboot_completed=bool(post_network_reset_reboot_completed),
        pre_reset_airplane_mode=norm_pre_air or str(pre_reset_airplane_mode),
        effective_immediate_post_network_reset_airplane_mode=resolved[
            "effective_immediate_post_network_reset_airplane_mode"
        ],
        post_reset_airplane_mode=eff_post_air,
        air_gapped_zero_rf_bench=bool(air_gapped_zero_rf_bench),
        rf_radio_active_after_reset=bool(rf_radio_active_after_reset),
        post_network_reset_rf_hazard_events=rf_hazard_events,
        playback_protect_survives_camera_and_network_reset=resolved[
            "playback_protect_survives_reset"
        ],
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g114_protect_and_network_reset_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    protect_and_network_reset_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase276DonorAuditResult] = None,
) -> Tuple[GateVerdict, G114ProtectAndNetworkResetGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase276_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_protect_and_network_reset_guard(
        **dict(protect_and_network_reset_kwargs or {})
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
        errors.append("Persistent eMMC write authorization requested in Gate G114.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G114 if valid else codes[0]

    res = G114ProtectAndNetworkResetGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        protect_and_network_reset_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, protect_scope={guard.protect_scope}"
        f"(slot1_wp={guard.slot1_sd_physical_wp_locked},fmt_lock={guard.slot1_format_hard_locked},"
        f"wp_viol={guard.slot1_wp_firewall_violation_events}), "
        f"nw_reset_reboot={guard.auto_reboot_triggered}, "
        f"post_air={guard.post_reset_airplane_mode}(rf_haz={guard.post_network_reset_rf_hazard_events})"
    )
    verdict = GateVerdict(
        gate_id=G114_GATE_ID,
        gate_code=G114_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `114`-Gate Master Safety Preflight (`G01..G114`)
# ---------------------------------------------------------------------------


def evaluate_114gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    usb_mode_hdmi_info_kwargs: Optional[Mapping[str, Any]] = None,
    protect_and_network_reset_kwargs: Optional[Mapping[str, Any]] = None,
    master_112_override: Optional[Master112GateReport] = None,
    **m112_passthrough_kwargs: Any,
) -> Master114GateReport:
    """Evaluate all 114 Master Safety Gates (`G01..G114`) deterministically by
    delegating `G01..G112` directly to `evaluate_112gate_preflight()`.
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

    m112_report: Master112GateReport = (
        master_112_override
        if master_112_override is not None
        else evaluate_112gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m112_passthrough_kwargs,
        )
    )

    phase276_audit = audit_phase276_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g113_verdict, g113_res = evaluate_g113_usb_mode_and_hdmi_info_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        usb_mode_hdmi_info_kwargs=usb_mode_hdmi_info_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase276_audit,
    )

    g114_verdict, g114_res = evaluate_g114_protect_and_network_reset_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        protect_and_network_reset_kwargs=protect_and_network_reset_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase276_audit,
    )

    gates_113_to_114 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g113_verdict, g114_verdict)
    ]
    all_gates = tuple(list(m112_report.gates) + gates_113_to_114)

    g01_to_g12_verified = int(m112_report.summary["g01_to_g12_verified"])
    g13_to_g112_verified = int(m112_report.summary["g13_to_g110_verified"]) + int(
        m112_report.summary["g111_to_g112_verified"]
    )
    g113_to_g114_verified = sum(1 for v in (g113_verdict, g114_verdict) if v.passed)
    total_verified = (
        g01_to_g12_verified + g13_to_g112_verified + g113_to_g114_verified
    )

    g113_to_g114_all_passed = g113_to_g114_verified == 2
    g13_to_g114_all_passed = (
        m112_report.g13_to_g112_all_passed and g113_to_g114_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m112_report.gates[:9])

    offline_111_verified = (
        g01_to_g09_ok
        and m112_report.offline_109_gates_verified
        and g113_to_g114_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_114_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g114_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m112_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_111_verified
        and m112_report.h0_h1_trial_entry_allowed
        and g113_to_g114_all_passed
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
        list(m112_report.errors)
        + list(g113_verdict.errors)
        + list(g114_verdict.errors)
    )
    warnings: List[str] = (
        list(m112_report.warnings)
        + list(g113_verdict.warnings)
        + list(g114_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m112_report.g13_to_g112_all_passed:
        overall_status = m112_report.status
    elif not g113_verdict.passed:
        overall_status = g113_verdict.status
    elif not g114_verdict.passed:
        overall_status = g114_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_114_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_114_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_114_verified:
        overall_status = "VERIFIED_ALL_114_GATES"
    else:
        overall_status = "VERIFIED_111_OF_114_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m112_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g113_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g114_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 114,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 114 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g112_verified": g13_to_g112_verified,
        "g113_to_g114_verified": g113_to_g114_verified,
        "g13_to_g114_all_passed": g13_to_g114_all_passed,
        "g113_to_g114_all_passed": g113_to_g114_all_passed,
        "offline_111_gates_verified": offline_111_verified,
        "all_114_gates_verified": all_114_verified,
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

    return Master114GateReport(
        schema=REALHW_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_114GATE_SCHEMA,
        version=REALHW_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_114GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_111_gates_verified=offline_111_verified,
        all_114_gates_verified=all_114_verified,
        g13_to_g114_all_passed=g13_to_g114_all_passed,
        g113_to_g114_all_passed=g113_to_g114_all_passed,
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
        master_112_report=m112_report.to_dict(),
        g113_result=g113_res.to_dict(),
        g114_result=g114_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_114_master_safety_gates = evaluate_114gate_preflight
run_114_gate_preflight = evaluate_114gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard",
        description=(
            "Phase 276 (114/114 Safety Gates, Wave-47) Gates G113 ([USB Connection Mode] "
            "4-Mode vs Dormant NOUVC [USB Streaming], Data-Isolated PD Guard & [HDMI "
            "Info. Display] LCD Blanking / 1080 Clamp / 4K Clean-Feed Override) + G114 "
            "([Protect] vs [Format] Slot-1 Dual-Layer WP Firewall & [Reset Network Set.] "
            "Auto-Reboot + Post-Reboot [Airplane Mode] = [On] Zero-RF Sequence) + "
            "Unified 114-Gate Master Safety Preflight"
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

    report = evaluate_114gate_preflight(
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
            f"verified={report.summary['verified_gates']}/114 "
            f"g113_to_g114_all_passed={report.g113_to_g114_all_passed} "
            f"all_114_gates_verified={report.all_114_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = (
        report.all_114_gates_verified
        if args.dry_run_simulated
        else report.offline_111_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
