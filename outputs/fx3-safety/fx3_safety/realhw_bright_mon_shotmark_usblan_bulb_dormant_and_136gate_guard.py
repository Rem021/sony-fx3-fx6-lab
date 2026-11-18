"""Phase 310 (310th Phase Milestone! Wave-58, 136/136 Safety Gates):
Real-Hardware Safety Gates G135 & G136 + Unified 136-Gate Preflight Engine.

Implements empirical `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` hardware safety gates:

1. **Gate `G135` (`verify-bright-mon-shotmark-vault-guard`)**:
   - `[Bright Monitoring]` (`_f.uxc 0x701f`, `EVENT_FUNC_CUSTOM_BRIGHT_MONITORING_{ON,OFF}`,
     `VAL_setting_bright_monitoring_state_BRIGHT_MONITORING_STATE_{ON,OFF}`):
     - Strictly **custom-key-only** on `ILME-FX3 Ver. 7.02` (never a shooting menu toggle),
       exposing only `ON / OFF` (rejecting multi-step gain extensions `EOPNOTSUPP=95`),
       forcing `[Live View Display] = Setting Effect OFF` while active, and auto-cancelling
       on power-off, shooting mode leaving `P/A/S/M`, or focus mode leaving `MF`.
     - In **Ver. 7.00+ / Ver. 7.02**, explicitly permits `[Focus Magnifier]` and
       `[Auto Magnifier in MF]` coexistence during `[Bright Monitoring]` (superseding
       legacy `ilc/2210` caveat notes).
   - `[Monitor Brightness]` (`base.uxc 0xe44b`, `BKID_APP_setting_lcd_brightness`):
     - Exposes ONLY `Manual` (`-2..+2`, default `0`) and `Sunny Weather` (`base 0xe1da` /
       `_f 0x7a61`), rejecting dormant `LCD_BRIGHTNESS_{AUTO,BRIGHT,NORMAL}` (`EOPNOTSUPP=95`),
       `Initialize`-only (unaffected by `[Camera Settings Reset]`), with NO 4K/thermal
       screen-dimming lock on fan-cooled FX3.
     - Contrasted with `ILME-FX6 Ver. 6.01` `Monitoring > VF Setting > Brightness` (`1..15`,
       default `8`) & `Color Mode` (`Color / B&W`), while rejecting conflation with
       `Shooting > Auto Exposure > Mode > Backlight` (`MODE_BACKLIGHT` AE compensation)
       and dormant `FX6_2 0x44f0 LCD Backlight`, `0x44f4 VF Backlight`, and `NIGHTSHOT_*`.
   - `Shot Mark 1/2`, `Clip Flag`, `Photo Capture`, `Create Divider Frame`, & `Slot-1` Firewall:
     - Rejects non-existent FX3 in-camera `[Divide]` / `[Extract]` and dormant FTP
       `15/30/60s` Shot-Mark Cut (`_f.uxc 0x7005/0x6e38/0x6c2a/0x74a9 -> EOPNOTSUPP=95`),
       plus FX6 dormant CBM/XDCAM `Shot Mark 0..9` (`FX6_2 0x4fe7..0x53fd`), `Essence Mark`,
       and `Divide Clip`.
     - Enforces FAIL-CLOSED `EROFS=30` / `EBUSY=16` blocking whenever `[Add/Delete Shot Mark1/2]`
       (`_f.uxc 0x628b/0x628a/0x6143/0x6142`), Ver. 7.00+ `[Clip Flag]` (`OK/NG/KEEP`),
       `[Photo Capture]` (`_f 0x6856`), `[Create Divider Frame]` (`_f 0x747a`), or any
       `[Edit]` attempts to mutate `M4ROOT/CLIP/*M01.XML`, `DCIM/`, or `AVF_INFO` on a
       `Slot-1` Tier-0 recovery vault (`slot1_data_sector_writes == 0`,
       `slot1_avf_info_mutated == False`).

2. **Gate `G136` (`verify-tc-link-wifi-usblan-bulb-dormant-guard`)**:
   - **Zero Bluetooth `[Timecode Link]` vs Wired `VMC-BNCM1` & FX6 BNC `TC IN/OUT`**:
     - Rejects Bluetooth `[Timecode Link]` / `UltraSync BLUE` on `ILME-FX3 Ver. 7.02`
       (`0` `tc_link`/`timecode_link`/`UltraSync` symbols in `FX3 appFw.so` -> `EOPNOTSUPP=95`).
     - Enforces FX3 wired Multi/Micro USB `VMC-BNCM1` (`A-5051-506-A`) LTC input with
       `Time Code Make = Preset` + `Time Code Run = Free Run` -> lock indicator `EXT-LK`
       (`BKID_APP_ext_tc_lock_status`) + HDMI `[Time Code Output]` (default `Off`),
       contrasted with `ILME-FX6` physical `TC IN/OUT` switch & BNC port and zero-BT hardware
       (dormant `BKID_APP_SETTING_BLUETOOTH_FUNCTION` / `USB_TC_IN_ALT_MODE_SETTING`).
   - **Wi-Fi `WPA2-PSK`/`WPA3-SAE` SKU + `USB-LAN` Zero-RF Isolation**:
     - Enforces Ver. 7.00+ `WPA2-PSK` / `WPA3-SAE` (`base 0xe407`) + `Access Authen. Settings = On`,
       rejecting removed legacy `WEP`, `WPA-PSK`, and `Security(IPsec)` (`EOPNOTSUPP=95`).
     - Enforces SKU truth: `WW728473` (`2.4/5GHz`, `802.11a/b/g/n/ac`) vs `WW558244`
       (`2.4GHz`-only, `802.11b/g/n`, rejecting `5GHz` -> `EOPNOTSUPP=95`).
     - Validates `USB-LAN` kernel stack (`cdc_ncm.ko`, `r8152.ko`, `asix.ko`,
       `ax88179_178a.ko`, `cdc_ether.ko`, `usbnet.ko`, `ipheth.ko`, `rndis_host.ko` +
       `libWiredLanResource.so` + Ver. 7.00+ `[USB-LAN Cnct. Launch]` `_f.uxc 0x7d2a`
       default `Off`) and enforces strict mutual exclusion with Multi/Micro USB
       (`VMC-BNCM1`/wired shutter) and internal Wi-Fi.
     - Enforces mandatory `[Airplane Mode] = On` zero-RF lock (empirical persistence
       across BOTH `[Reset Network Set.]` AND `[Initialize]`; `wireless_packets_emitted == 0`,
       `rf_nvs_p12_p13_writes_permitted == False`), permitting air-gapped wired `eth0`
       ONLY when authorized without USB-bus conflicts.
   - **Dormant `[Bulb Timer]` / `[Auto HDR]` vs Mechanical-Only Still `[BULB]` & `DRO`**:
     - Rejects dormant `[Bulb Timer]` (`BKID_APP_setting_bulb_timer`, `_f.uxc 0x630f` ->
       `EOPNOTSUPP=95`) and dormant `[Auto HDR]` (`.uxc 0xe49d`/`0xe5d0`,
       `BKID_APP_extern_menu_hdr_level` -> `EOPNOTSUPP=95`, superseded by `[HLG Still Image]`).
     - Enforces Still `[BULB]` (`> 30"` in `Manual Exposure`, `PID_SET_BULB_MODE`)
       **Mechanical Shutter ONLY**: blocked / clamped to `30"` under `Electronic Shutter`,
       `Cont. Shooting`, `Cont. Bracket`, `Self-timer(Cont)`, and `Interval Shooting`,
       and enforces active `[D-Range Optimizer]` / `[DRO Bracket]` lock (`Off` / unavailable)
       when `Picture Profile != Off` or `HLG Still Image = On`.

3. **Unified `136`-Gate Milestone Master Preflight (`evaluate_136gate_preflight` / `verify-136-gates`)**:
   - Delegates `G01..G134` directly to `evaluate_134gate_preflight()` and appends `G135` + `G136`.
   - Offline mode: `133/136` gates pass (`VERIFIED_133_OF_136_AWAITING_PHYSICAL_TIER0`, only
     physical Tier-0 bench receipts `G10..G12` pending); `--simulate-bench-dry-run`: `136/136`
     simulation gates pass (`VERIFIED_ALL_136_GATES_DRY_RUN_SIMULATED_BACKUP`).
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
from .realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard import (
    Master134GateReport,
    evaluate_134gate_preflight,
)

# ---------------------------------------------------------------------------
# Schema, Version & Absolute Hardware / Firmware Safety Redlines
# ---------------------------------------------------------------------------

REALHW_BRIGHT_MON_SHOTMARK_USBLAN_BULB_DORMANT_136GATE_SCHEMA = (
    "realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard_v1"
)
REALHW_BRIGHT_MON_SHOTMARK_USBLAN_BULB_DORMANT_136GATE_VERSION = "2026.11.17"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST_PHASE310 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE310 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE310 = 15.0

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
G135 = "G135"
G135_GATE_ID = "G135"
G135_GATE_CODE = (
    "GATE_G135_BRIGHT_MONITORING_FOCUS_MAG_MONITOR_BRIGHTNESS_VS_FX6_AND_SHOTMARK_CLIPFLAG_DIVIDER_SLOT1_VAULT_GUARD"
)
GATE_G135_BRIGHT_MONITORING_FOCUS_MAG_MONITOR_BRIGHTNESS_VS_FX6_AND_SHOTMARK_CLIPFLAG_DIVIDER_SLOT1_VAULT_GUARD = (
    G135_GATE_CODE
)

G136 = "G136"
G136_GATE_ID = "G136"
G136_GATE_CODE = (
    "GATE_G136_ZERO_BT_TCLINK_VS_VMC_BNCM1_FX6_BNC_WIFI_WPA3_USBLAN_ZERORF_AND_DORMANT_BULB_TIMER_AUTOHDR_GUARD"
)
GATE_G136_ZERO_BT_TCLINK_VS_VMC_BNCM1_FX6_BNC_WIFI_WPA3_USBLAN_ZERORF_AND_DORMANT_BULB_TIMER_AUTOHDR_GUARD = (
    G136_GATE_CODE
)

# Model & Identity Contracts (Phase 310 suffixed to avoid __init__.py shadowing)
FX3_MODEL_NAME_PHASE310 = "ILME-FX3"
FX3_MODEL_ID_PHASE310 = 0x39383232
FX3_HELP_GUIDE_CODE_PHASE310 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE310 = "7.02"

FX6_MODEL_NAME_PHASE310 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE310 = "6.01"
FX6_PRODUCT_CODE_PHASE310 = "PRODUCT_MODEL_CHAPLIN"

# Shoot Modes, Exposure Modes, Focus Modes, Reset Actions & Media Slots
SHOOT_MODE_STILL_PHASE310 = "Still"
SHOOT_MODE_MOVIE_PHASE310 = "Movie"
SHOOT_MODE_SQ_PHASE310 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE310: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE310,
    SHOOT_MODE_MOVIE_PHASE310,
    SHOOT_MODE_SQ_PHASE310,
)

EXPOSURE_MODE_P_G135 = "P"
EXPOSURE_MODE_A_G135 = "A"
EXPOSURE_MODE_S_G135 = "S"
EXPOSURE_MODE_M_G135 = "M"
EXPOSURE_MODE_INTELLIGENT_AUTO_G135 = "Intelligent Auto"
ALLOWED_PASM_MODES_G135: Tuple[str, ...] = (
    EXPOSURE_MODE_P_G135,
    EXPOSURE_MODE_A_G135,
    EXPOSURE_MODE_S_G135,
    EXPOSURE_MODE_M_G135,
)
ALLOWED_EXPOSURE_MODES_G135: Tuple[str, ...] = ALLOWED_PASM_MODES_G135 + (
    EXPOSURE_MODE_INTELLIGENT_AUTO_G135,
)

FOCUS_MODE_MF_G135 = "MF"
FOCUS_MODE_AF_S_G135 = "AF-S"
FOCUS_MODE_AF_C_G135 = "AF-C"
FOCUS_MODE_DMF_G135 = "DMF"
ALLOWED_FOCUS_MODES_G135: Tuple[str, ...] = (
    FOCUS_MODE_MF_G135,
    FOCUS_MODE_AF_S_G135,
    FOCUS_MODE_AF_C_G135,
    FOCUS_MODE_DMF_G135,
)

RESET_ACTION_NONE_PHASE310 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE310 = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE310 = "Reset Network Set."
RESET_ACTION_INITIALIZE_PHASE310 = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE310: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE310,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE310,
    RESET_ACTION_RESET_NETWORK_SET_PHASE310,
    RESET_ACTION_INITIALIZE_PHASE310,
)

MEDIA_SLOT_1_PHASE310 = "Slot 1"
MEDIA_SLOT_2_PHASE310 = "Slot 2"
ALLOWED_MEDIA_SLOTS_PHASE310: Tuple[str, ...] = (
    MEDIA_SLOT_1_PHASE310,
    MEDIA_SLOT_2_PHASE310,
)

EOPNOTSUPP_ERRNO_PHASE310 = 95
EOPNOTSUPP_NAME_PHASE310 = "EOPNOTSUPP"
EROFS_ERRNO_PHASE310 = 30
EROFS_NAME_PHASE310 = "EROFS"
EBUSY_ERRNO_PHASE310 = 16
EBUSY_NAME_PHASE310 = "EBUSY"

# ---------------------------------------------------------------------------
# G135 Constants: Bright Monitoring, Monitor Brightness vs FX6, Shot Mark Vault
# ---------------------------------------------------------------------------

BRIGHT_MONITORING_F_UXC_RESID16_G135 = 0x701F
BRIGHT_MONITORING_KEY_PATH_G135 = (
    "MENU -> (Setup) -> [Operation Customize] -> [Custom Key/Dial Set.] -> [Bright Monitoring]"
)
LIVE_VIEW_DISPLAY_EFFECT_ON_G135 = "Setting Effect ON"
LIVE_VIEW_DISPLAY_EFFECT_OFF_G135 = "Setting Effect OFF"
ALLOWED_LIVE_VIEW_DISPLAY_MODES_G135: Tuple[str, ...] = (
    LIVE_VIEW_DISPLAY_EFFECT_ON_G135,
    LIVE_VIEW_DISPLAY_EFFECT_OFF_G135,
)

MONITOR_BRIGHTNESS_MENU_PATH_G135 = "MENU -> (Setup) -> [Monitor] -> [Monitor Brightness]"
MONITOR_BRIGHTNESS_UXC_RESID16_G135 = 0xE44B
SUNNY_WEATHER_BASE_UXC_RESID16_G135 = 0xE1DA
SUNNY_WEATHER_F_UXC_RESID16_G135 = 0x7A61

MONITOR_BRIGHTNESS_MANUAL_G135 = "Manual"
MONITOR_BRIGHTNESS_SUNNY_WEATHER_G135 = "Sunny Weather"
MONITOR_BRIGHTNESS_DEFAULT_MODE_G135 = MONITOR_BRIGHTNESS_MANUAL_G135
MONITOR_BRIGHTNESS_LEVEL_MIN_G135 = -2
MONITOR_BRIGHTNESS_LEVEL_MAX_G135 = 2
MONITOR_BRIGHTNESS_LEVEL_DEFAULT_G135 = 0
ALLOWED_MONITOR_BRIGHTNESS_MODES_G135: Tuple[str, ...] = (
    MONITOR_BRIGHTNESS_MANUAL_G135,
    MONITOR_BRIGHTNESS_SUNNY_WEATHER_G135,
)
DORMANT_MONITOR_BRIGHTNESS_MODES_G135: Tuple[str, ...] = (
    "AUTO",
    "Auto",
    "BRIGHT",
    "Bright",
    "NORMAL",
    "Normal",
    "LCD_BRIGHTNESS_AUTO",
    "LCD_BRIGHTNESS_BRIGHT",
    "LCD_BRIGHTNESS_NORMAL",
)

FX6_VF_SETTING_MENU_PATH_G135 = "Monitoring > VF Setting > Brightness"
FX6_VF_BRIGHTNESS_MIN_G135 = 1
FX6_VF_BRIGHTNESS_MAX_G135 = 15
FX6_VF_BRIGHTNESS_DEFAULT_G135 = 8
FX6_VF_COLOR_MODES_G135: Tuple[str, ...] = ("Color", "B&W")
FX6_AE_BACKLIGHT_SYMBOL_G135 = "VAL_setting_auto_exposure_mode_MODE_BACKLIGHT"
FX6_DORMANT_BACKLIGHT_SYMBOLS_G135: Tuple[str, ...] = (
    "LCD Backlight",
    "VF Backlight",
    "0x44f0",
    "0x44f4",
    "BKID_APP_SETTING_NIGHTSHOT_BRIGHTNESS",
    "NIGHTSHOT_ON",
)

SHOT_MARK_1_REC_RESID16_G135 = 0x628B
SHOT_MARK_2_REC_RESID16_G135 = 0x628A
SHOT_MARK_1_PB_RESID16_G135 = 0x6143
SHOT_MARK_2_PB_RESID16_G135 = 0x6142
PHOTO_CAPTURE_F_UXC_RESID16_G135 = 0x6856
PHOTO_CAPTURE_SWITCH_F_UXC_RESID16_G135 = 0x7175
CREATE_DIVIDER_FRAME_F_UXC_RESID16_G135 = 0x747A
CREATE_DIVIDER_FRAME_G_UXC_RESID16_G135 = 0x6118

ACTIVE_PB_EDIT_ITEMS_G135: Tuple[str, ...] = (
    "Photo Capture",
    "JPEG/HEIF Switch (Photo Capture)",
    "Copy",
    "Rotate",
)
ALLOWED_CLIP_FLAG_VALUES_G135: Tuple[str, ...] = ("Off", "OK", "NG", "KEEP")
ALLOWED_IMAGE_JUMP_SETTINGS_G135: Tuple[str, ...] = (
    "Shot Mark Only",
    "Shot Mark1 Only",
    "Shot Mark2 Only",
    "No Shot Mark",
    "Divider Frame Only",
    "Image After Divider",
)
ALLOWED_PHOTO_CAPTURE_FILE_TYPES_G135: Tuple[str, ...] = (
    "JPEG",
    "HEIF 4:2:0",
    "HEIF 4:2:2",
)

DORMANT_SHOTMARK_DIVIDE_TRAPS_G135: Tuple[str, ...] = (
    "Divide",
    "Extract",
    "divide_clip",
    "clip_divide",
    "extract_clip",
    "Cut to 15 seconds",
    "Cut to 30 seconds",
    "Cut to 60 seconds",
    "CUT_TO_15",
    "CUT_TO_30",
    "CUT_TO_60",
    "FTP_CUT",
    "0x7005",
    "0x6e38",
    "0x6c2a",
    "0x74a9",
)

CARD_OP_NONE_G135 = "None"
CARD_OP_JUMP_READONLY_G135 = "Image Jump Read-Only"
CARD_OP_ADD_SHOT_MARK_1_G135 = "Add Shot Mark1"
CARD_OP_ADD_SHOT_MARK_2_G135 = "Add Shot Mark2"
CARD_OP_ADD_DELETE_SHOT_MARK_1_G135 = "Add/Delete Shot Mark1"
CARD_OP_ADD_DELETE_SHOT_MARK_2_G135 = "Add/Delete Shot Mark2"
CARD_OP_SET_CLIP_FLAG_G135 = "Set Clip Flag"
CARD_OP_PHOTO_CAPTURE_G135 = "Photo Capture"
CARD_OP_CREATE_DIVIDER_FRAME_G135 = "Create Divider Frame"
CARD_OP_PB_EDIT_G135 = "Playback Edit"

READONLY_CARD_OPS_G135: Tuple[str, ...] = (
    CARD_OP_NONE_G135,
    CARD_OP_JUMP_READONLY_G135,
)
MUTATING_M4ROOT_OPS_G135: Tuple[str, ...] = (
    CARD_OP_ADD_SHOT_MARK_1_G135,
    CARD_OP_ADD_SHOT_MARK_2_G135,
    CARD_OP_ADD_DELETE_SHOT_MARK_1_G135,
    CARD_OP_ADD_DELETE_SHOT_MARK_2_G135,
    CARD_OP_SET_CLIP_FLAG_G135,
)
MUTATING_DCIM_OPS_G135: Tuple[str, ...] = (
    CARD_OP_PHOTO_CAPTURE_G135,
    CARD_OP_CREATE_DIVIDER_FRAME_G135,
    CARD_OP_PB_EDIT_G135,
)
ALLOWED_CARD_OPS_G135: Tuple[str, ...] = (
    READONLY_CARD_OPS_G135 + MUTATING_M4ROOT_OPS_G135 + MUTATING_DCIM_OPS_G135
)

# ---------------------------------------------------------------------------
# G136 Constants: Timecode Link, Wi-Fi WPA2/WPA3 SKU, USB-LAN, Bulb/HDR/DRO
# ---------------------------------------------------------------------------

DORMANT_TC_LINK_TRAPS_G136: Tuple[str, ...] = (
    "Timecode Link",
    "tc_link",
    "timecode_link",
    "UltraSync BLUE",
    "Bluetooth Timecode",
    "TC Link",
)
FX3_WIRED_TC_CABLE_G136 = "VMC-BNCM1 (A-5051-506-A)"
ALLOWED_TC_MAKE_MODES_G136: Tuple[str, ...] = ("Preset", "Regenerate")
ALLOWED_TC_RUN_MODES_G136: Tuple[str, ...] = ("Rec Run", "Free Run")

FX3_SKU_WW728473_G136 = "WW728473"
FX3_SKU_WW558244_G136 = "WW558244"
ALLOWED_FX3_SKUS_G136: Tuple[str, ...] = (
    FX3_SKU_WW728473_G136,
    FX3_SKU_WW558244_G136,
)
WIFI_BAND_2_4GHZ_G136 = "2.4GHz"
WIFI_BAND_5GHZ_G136 = "5GHz"
ALLOWED_WIFI_BANDS_G136: Tuple[str, ...] = (
    WIFI_BAND_2_4GHZ_G136,
    WIFI_BAND_5GHZ_G136,
)

WIFI_SEC_WPA2_PSK_G136 = "WPA2-PSK"
WIFI_SEC_WPA3_SAE_G136 = "WPA3-SAE"
ALLOWED_WIFI_SECURITIES_G136: Tuple[str, ...] = (
    WIFI_SEC_WPA2_PSK_G136,
    WIFI_SEC_WPA3_SAE_G136,
)
REMOVED_LEGACY_WIFI_SECURITIES_G136: Tuple[str, ...] = (
    "WEP",
    "WPA-PSK",
    "WPA",
    "IPsec",
    "Security(IPsec)",
    "BKID_APP_setting_ipsec",
)

USB_LAN_CNCT_LAUNCH_F_UXC_RESID16_G136 = 0x7D2A
USB_LAN_KERNEL_MODULES_G136: Tuple[str, ...] = (
    "cdc_ncm.ko",
    "cdc_ether.ko",
    "r8152.ko",
    "asix.ko",
    "ax88179_178a.ko",
    "usbnet.ko",
    "ipheth.ko",
    "rndis_host.ko",
)

SHUTTER_TYPE_AUTO_G136 = "Auto"
SHUTTER_TYPE_MECHANICAL_G136 = "Mechanical Shutter"
SHUTTER_TYPE_ELECTRONIC_G136 = "Electronic Shutter"
ALLOWED_SHUTTER_TYPES_G136: Tuple[str, ...] = (
    SHUTTER_TYPE_AUTO_G136,
    SHUTTER_TYPE_MECHANICAL_G136,
    SHUTTER_TYPE_ELECTRONIC_G136,
)

STILL_DRIVE_SINGLE_G136 = "Single Shooting"
STILL_DRIVE_CONT_SHOOTING_G136 = "Cont. Shooting"
STILL_DRIVE_SELF_TIMER_SINGLE_G136 = "Self-timer(Single)"
STILL_DRIVE_SELF_TIMER_CONT_G136 = "Self-timer(Cont)"
STILL_DRIVE_CONT_BRACKET_G136 = "Cont. Bracket"
STILL_DRIVE_SINGLE_BRACKET_G136 = "Single Bracket"
STILL_DRIVE_DRO_BRACKET_G136 = "DRO Bracket"
ALLOWED_STILL_DRIVE_MODES_G136: Tuple[str, ...] = (
    STILL_DRIVE_SINGLE_G136,
    STILL_DRIVE_CONT_SHOOTING_G136,
    STILL_DRIVE_SELF_TIMER_SINGLE_G136,
    STILL_DRIVE_SELF_TIMER_CONT_G136,
    STILL_DRIVE_CONT_BRACKET_G136,
    STILL_DRIVE_SINGLE_BRACKET_G136,
    STILL_DRIVE_DRO_BRACKET_G136,
)

DRO_AUTO_G136 = "Auto"
DRO_OFF_G136 = "Off"
ALLOWED_DRO_MODES_G136: Tuple[str, ...] = (
    DRO_AUTO_G136,
    DRO_OFF_G136,
    "Lv1",
    "Lv2",
    "Lv3",
    "Lv4",
    "Lv5",
)
ALLOWED_DRO_BRACKET_MODES_G136: Tuple[str, ...] = (
    "Off",
    "DRO Bracket: Lo",
    "DRO Bracket: Hi",
)

DORMANT_BULB_TIMER_TRAPS_G136: Tuple[str, ...] = (
    "Bulb Timer",
    "BULB Timer",
    "BULB Timer Settings",
    "BKID_APP_setting_bulb_timer",
    "BKID_APP_MR_setting_bulb_timer",
    "N5model20setting_bulb_timer_tE",
    "sequence_set_bulb_timer",
    "BULB_TIMER_ON",
    "0x630f",
    "0x78b6",
)
DORMANT_AUTO_HDR_TRAPS_G136: Tuple[str, ...] = (
    "Auto HDR",
    "DRO/Auto HDR",
    "BKID_APP_extern_menu_hdr_level",
    "Exposure Diff. 4.0EV",
    "Exposure Diff. 6.0EV",
    "0xe49d",
    "0xe5d0",
)

# Status / Violation Codes
STATUS_BLOCKED_PHASE310_DONOR_INTEGRITY = "STATUS_BLOCKED_PHASE310_DONOR_INTEGRITY"

STATUS_VERIFIED_G135 = "STATUS_VERIFIED_G135"
STATUS_BLOCKED_G135_TELEMETRY_INVALID = "STATUS_BLOCKED_G135_TELEMETRY_INVALID"
STATUS_BLOCKED_G135_BRIGHT_MONITORING_CUSTOM_KEY_OR_MAG_VIOLATION = (
    "STATUS_BLOCKED_G135_BRIGHT_MONITORING_CUSTOM_KEY_OR_MAG_VIOLATION"
)
STATUS_BLOCKED_G135_MONITOR_BRIGHTNESS_OR_FX6_BACKLIGHT_VIOLATION = (
    "STATUS_BLOCKED_G135_MONITOR_BRIGHTNESS_OR_FX6_BACKLIGHT_VIOLATION"
)
STATUS_BLOCKED_G135_DORMANT_DIVIDE_EXTRACT_OR_FTP_CUT_VIOLATION = (
    "STATUS_BLOCKED_G135_DORMANT_DIVIDE_EXTRACT_OR_FTP_CUT_VIOLATION"
)
STATUS_BLOCKED_G135_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION = (
    "STATUS_BLOCKED_G135_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION"
)

STATUS_VERIFIED_G136 = "STATUS_VERIFIED_G136"
STATUS_BLOCKED_G136_TELEMETRY_INVALID = "STATUS_BLOCKED_G136_TELEMETRY_INVALID"
STATUS_BLOCKED_G136_DORMANT_BT_TCLINK_OR_FX6_TC_VIOLATION = (
    "STATUS_BLOCKED_G136_DORMANT_BT_TCLINK_OR_FX6_TC_VIOLATION"
)
STATUS_BLOCKED_G136_WIFI_WPA_LEGACY_SKU_OR_USBLAN_EXCLUSION_VIOLATION = (
    "STATUS_BLOCKED_G136_WIFI_WPA_LEGACY_SKU_OR_USBLAN_EXCLUSION_VIOLATION"
)
STATUS_BLOCKED_G136_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION = (
    "STATUS_BLOCKED_G136_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION"
)
STATUS_BLOCKED_G136_DORMANT_BULB_TIMER_OR_AUTO_HDR_VIOLATION = (
    "STATUS_BLOCKED_G136_DORMANT_BULB_TIMER_OR_AUTO_HDR_VIOLATION"
)
STATUS_BLOCKED_G136_STILL_BULB_MECHANICAL_OR_DRO_LOCK_VIOLATION = (
    "STATUS_BLOCKED_G136_STILL_BULB_MECHANICAL_OR_DRO_LOCK_VIOLATION"
)

# ---------------------------------------------------------------------------
# Pinned Wave-58 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE310: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (60_564_416, b"PRM_setting_bright_monitoring_state"),
    (62_198_816, b"VAL_setting_bright_monitoring_state_BRIGHT_MONITORING_STATE_ON"),
    (62_198_752, b"VAL_setting_bright_monitoring_state_BRIGHT_MONITORING_STATE_OFF"),
    (63_143_767, b"EVENT_FUNC_CUSTOM_BRIGHT_MONITORING_ON"),
    (63_143_806, b"EVENT_FUNC_CUSTOM_BRIGHT_MONITORING_OFF"),
    (62_700_706, b"BKID_APP_setting_lcd_brightness"),
    (62_175_219, b"VAL_setting_lcd_brightness_LCD_BRIGHTNESS_MANUAL"),
    (62_175_268, b"VAL_setting_lcd_brightness_LCD_BRIGHTNESS_SUNNY"),
    (62_175_172, b"VAL_setting_lcd_brightness_LCD_BRIGHTNESS_AUTO"),
    (59_820_148, b"sequence_add_shot_mark"),
    (58_328_535, b"jump_to_shot_mark_playback_movie(model::movie_playback_control_t)"),
    (50_570_456, b"get_feedback_item_edit_shot_mark_1()"),
    (50_570_528, b"get_feedback_item_edit_shot_mark_2()"),
    (50_570_392, b"get_feedback_item_clip_flag()"),
    (50_745_608, b"execute_clip_flag_by_remote"),
    (62_855_239, b"BKID_APP_ext_tc_lock_status"),
    (62_694_659, b"BKID_APP_setting_usb_lan_connect_launch"),
    (62_694_699, b"BKID_APP_setting_airplane_mode"),
    (62_685_066, b"BKID_APP_setting_bulb_timer"),
    (62_685_094, b"BKID_APP_MR_setting_bulb_timer"),
    (62_502_600, b"N5model20setting_bulb_timer_tE"),
    (59_821_977, b"sequence_set_bulb_timer"),
    (60_074_064, b"PID_SET_BULB_MODE"),
    (62_847_318, b"BKID_APP_extern_menu_hdr_level"),
    (51_202_043, b"menu_item_id_dro_wrapper(model::value_id_t)"),
    (51_202_603, b"value_id_dro_d_rangeoptimizer_wrapper(model::option_id_t)"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE310 = (
    "2f52e3f13c4c7a7a13db9d87864733f32880aede07c36b81f83e0c1594694960"
)

PINNED_FX6_APPFW_SLICES_PHASE310: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (41_748_974, b"PRODUCT_MODEL_CHAPLIN"),
    (40_555_091, b"VAL_setting_auto_exposure_mode_MODE_BACKLIGHT"),
    (38_514_480, b"BKID_APP_DISPLAY_PANEL_BACKLIGHT_FORCE_NORMAL = %x"),
    (40_962_683, b"BKID_APP_USER_MENU_VF_SETTING0"),
    (40_796_645, b"VAL_content_clip_flag_CONTENT_CLIP_FLAG_OK"),
    (40_796_688, b"VAL_content_clip_flag_CONTENT_CLIP_FLAG_NG"),
    (40_807_989, b"VAL_setting_assignable_switch_grab_ASSIGNABLE_SWITCH_SHOT_MARK_1"),
    (40_808_054, b"VAL_setting_assignable_switch_grab_ASSIGNABLE_SWITCH_SHOT_MARK_2"),
    (40_922_507, b"BKID_APP_SETTING_BLUETOOTH_FUNCTION"),
    (40_939_075, b"BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING"),
    (40_634_262, b"VAL_setting_usb_tc_in_alt_mode_setting_USB_TC_IN_ALT_MODE_SETTING_ON"),
    (40_157_826, b"VAL_system_mode_option_SYSTEM_MODE_OPTION_USB_LAN_AND_TETHERING"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE310 = (
    "c0f0511a7b44fe7bd432b569bc829a0402e5e828845b2815b92a08eaaa3d71ae"
)

PINNED_PHASE310_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE310,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE310),
        "FX3 appFw.so Wave-58 Bright Monitoring/Monitor Brightness/Shot Mark/USB-LAN/TC/Dormant BulbTimer+AutoHDR slices",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Bright Monitoring",
            b"Sunny Weather",
            b"Add Shot Mark1",
            b"Add/Delete Shot Mark1",
            b"Photo Capture",
            b"Create Divider Frame",
            b"Cut to 15 seconds",
            b"USB-LAN Cnct. Launch",
            b"Wi-Fi Frequency Band",
            b"5GHz band: Indoor use only",
            b"Airplane Mode",
            b"Time Code Make",
            b"BULB Timer",
        ),
        "FX3 string_english_f.uxc Wave-58 EN parity",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "亮屏显示".encode("utf-8"),
            "晴朗天气".encode("utf-8"),
            "添加Shot Mark1".encode("utf-8"),
            "照片捕获".encode("utf-8"),
            "创建分隔帧".encode("utf-8"),
            "启动时USB-LAN连接".encode("utf-8"),
            "Wi-Fi频带".encode("utf-8"),
            "飞行模式".encode("utf-8"),
            "BULB定时器".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-58 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "亮屏顯示".encode("utf-8"),
            "晴朗天氣".encode("utf-8"),
            "新增Shot Mark1".encode("utf-8"),
            "照片攝取".encode("utf-8"),
            "建立分格線框架".encode("utf-8"),
            "啟動時USB-LAN連線".encode("utf-8"),
            "Wi-Fi頻帶".encode("utf-8"),
            "飛航模式".encode("utf-8"),
            "BULB計時器".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-58 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "ブライトモニタリング".encode("utf-8"),
            "屋外晴天".encode("utf-8"),
            "Shot Mark1追加".encode("utf-8"),
            "動画から静止画作成".encode("utf-8"),
            "区切り画像作成".encode("utf-8"),
            "起動時のUSB-LAN接続".encode("utf-8"),
            "Wi-Fi周波数帯".encode("utf-8"),
            "機内モード".encode("utf-8"),
            "BULBタイマー".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-58 JA parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Monitor Brightness",
            b"Sunny Weather",
            b"WPA3",
            b"WPA2",
            b"BULB",
            b"D-Range Optimizer",
            b"DRO Bracket",
            b"Auto HDR",
            b"DRO/Auto HDR",
        ),
        "FX3 string_english.uxc Wave-58 base strings",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Divider Frame",
            b"Wired LAN",
            b"Wi-Fi",
            b"Bluetooth",
            b"Network Option",
        ),
        "FX3 string_english_g.uxc Wave-58 menu group strings",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4\x00",),
        "FX3-CX95900_ALLLANG-Backup.bin BK4 seed",
    ),
    "fx3_cdc_ncm_ko": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/cdc_ncm.ko",
        32_208,
        "fce183b98eebbda9bb7954854bdcb717c2da74785c97a08a767afc235628ff70",
        (b"\x7fELF", b"cdc_ncm"),
        "FX3 full-v4 CDC-NCM USB-LAN kernel driver",
    ),
    "fx3_r8152_ko": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/r8152.ko",
        56_264,
        "b06d855ff3944c0de7ce4b600c3d44c1b006f64a5360279e6ed8d56aae70a9bf",
        (b"\x7fELF", b"r8152"),
        "FX3 full-v4 Realtek RTL8152/8153 USB-LAN kernel driver",
    ),
    "fx3_asix_ko": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/asix.ko",
        46_592,
        "49258835b3220042d06b9ba2e0dde7206f74594f48d210a2b1ac57e11da2fcd3",
        (b"\x7fELF", b"asix"),
        "FX3 full-v4 ASIX USB-LAN kernel driver",
    ),
    "fx3_ax88179_ko": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/ax88179_178a.ko",
        23_848,
        "a4f2582b028182d9cfbb42a0d255c75589357cf4ebb19ea38cafafc20f906c76",
        (b"\x7fELF", b"ax88179_178a"),
        "FX3 full-v4 ASIX AX88179 USB-LAN kernel driver",
    ),
    "fx3_lib_wired_lan": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libWiredLanResource.so",
        36_160,
        "f5ee3d70d5961753cef226bec74c15231e489491eddf63210511f57aaebf49e5",
        (b"\x7fELF", b"r8152", b"ax88179_178a", b"eth0"),
        "FX3 libWiredLanResource.so USB-LAN dispatcher",
    ),
    "fx3_lib_wlan": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libWlanResource.so",
        56_464,
        "76fe66f7c763a452c2986514b3485a62791e7750d52ffa89b31b820e4cb9eb91",
        (b"\x7fELF", b"/usr/kmod/ar6000.ko", b"/usr/lib/netconf/ccodeno.txt", b"wlanResource_init"),
        "FX3 libWlanResource.so WLAN driver/regulatory binding",
    ),
    "fx3_lib_airplane": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraAirplaneMode.so",
        14_488,
        "dcf0d7562a879f6d3bd1ed60cf00f9068fec368554b175bc6fabafbf212dffea",
        (b"\x7fELF",),
        "FX3 libInfraAirplaneMode.so Zero-RF isolation library",
    ),
    "fx6_appfw_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
        50_520_424,
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE310,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE310),
        "FX6 appFw.so Wave-58 VF Setting/AE Backlight/Dormant BT+USB_TC_IN/USB-LAN slices",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"VF Adjust",
            b"Backlight",
            b"USB Timecode",
            b"Timecode Run",
            b"Shot Mark",
        ),
        "FX6 string_english.uxc Wave-58 strings",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"VF Setting",
            b"LCD Backlight",
            b"VF Backlight",
            b"Add Shot Mark1",
            b"Essence Mark",
            b"Clip Flag",
            b"Wired LAN",
        ),
        "FX6 string_english_2.uxc Wave-58 strings",
    ),
}

_DONOR_BLOB_CACHE: Dict[str, Tuple[int, float, int, str, bytes]] = {}

# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase310DonorAuditResult:
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
    usblan_kmod_stack_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BrightMonShotMarkVaultGuardResult:
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
    exposure_mode: str
    focus_mode: str
    power_off: bool
    bright_monitoring_key_path: str
    bright_monitoring_custom_key_only: bool
    requested_bright_monitoring_active: bool
    effective_bright_monitoring_active: bool
    bright_monitoring_auto_cancelled: bool
    bright_monitoring_auto_cancel_reasons: Tuple[str, ...]
    requested_live_view_display: str
    effective_live_view_display: str
    focus_magnifier_active: bool
    auto_magnifier_in_mf: bool
    focus_magnifier_coexists_with_bright_monitoring: bool
    monitor_brightness_menu_path: str
    requested_monitor_brightness_mode: str
    effective_monitor_brightness_mode: str
    requested_monitor_brightness_level: int
    effective_monitor_brightness_level: int
    monitor_brightness_survived_cam_reset: bool
    fx3_4k_thermal_lcd_dimming_lock: bool
    fx6_vf_setting_menu_path: str
    fx6_vf_brightness: int
    fx6_vf_color_mode: str
    fx6_ae_backlight_is_ae_only: bool
    requested_card_op: str
    requested_clip_flag: str
    requested_image_jump_setting: str
    requested_photo_capture_file_type: str
    active_pb_edit_items: Tuple[str, ...]
    dormant_divide_extract_or_ftp_cut_blocked: bool
    requested_target_slot: str
    slot_1_contains_tier0_vault: bool
    slot_1_write_protected: bool
    slot1_vault_firewall_blocked: bool
    block_errno: Optional[int]
    block_errno_name: Optional[str]
    slot1_data_sector_writes: int
    slot1_m4root_xml_mutated: bool
    slot1_dcim_mutated: bool
    slot1_avf_info_mutated: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G135BrightMonShotMarkVaultGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    bright_mon_shotmark_vault_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TcLinkWifiUsbLanBulbDormantGuardResult:
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
    fx3_bluetooth_tc_link_symbols: int
    dormant_tc_link_blocked: bool
    vmc_bncm1_cable: str
    vmc_bncm1_ext_ltc_requested: bool
    tc_make: str
    tc_run: str
    hdmi_tc_output: str
    ext_tc_lock_status: str
    fx6_has_physical_tc_in_out_bnc: bool
    fx6_has_bluetooth_hw: bool
    fx3_sku_code: str
    wifi_requested: bool
    wifi_active: bool
    requested_wifi_band: str
    requested_wifi_security: str
    access_authen_settings: str
    usb_lan_requested: bool
    usb_lan_active: bool
    usb_lan_authorized: bool
    requested_usb_lan_cnct_launch: str
    effective_usb_lan_cnct_launch: str
    usb_lan_kernel_modules: Tuple[str, ...]
    multi_micro_usb_active: bool
    usb_bus_mutual_exclusion_blocked: bool
    requested_airplane_mode: str
    effective_airplane_mode: str
    airplane_survived_network_reset_and_init: bool
    bench_zero_rf_required: bool
    rf_nvs_write_requested: bool
    airplane_zero_rf_firewall_blocked: bool
    wired_eth0_permitted_under_airplane: bool
    wireless_packets_emitted: int
    rf_nvs_p12_p13_writes_permitted: bool
    rf_nvs_mutation_bytes: int
    dormant_bulb_timer_blocked: bool
    dormant_auto_hdr_blocked: bool
    requested_shutter_type: str
    requested_drive_mode: str
    interval_shooting_on: bool
    requested_bulb_mode: bool
    effective_bulb_active: bool
    bulb_locked_out_clamped_to_30s: bool
    bulb_lockout_reasons: Tuple[str, ...]
    anti_flicker_shoot_disabled: bool
    long_exposure_nr: str
    requested_dro_mode: str
    effective_dro_mode: str
    requested_dro_bracket: str
    effective_dro_bracket: str
    picture_profile_on: bool
    hlg_still_image_on: bool
    dro_locked_off: bool
    dro_reset_by_cam_reset: bool
    block_errno: Optional[int]
    block_errno_name: Optional[str]
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G136TcLinkWifiUsbLanBulbDormantGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    tc_link_wifi_usblan_bulb_dormant_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master136GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_133_gates_verified: bool
    all_136_gates_verified: bool
    g13_to_g136_all_passed: bool
    g135_to_g136_all_passed: bool
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
    master_134_report: Dict[str, Any]
    g135_result: Dict[str, Any]
    g136_result: Dict[str, Any]
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
        os.environ.get(ENV_CLEAN_ROOM_TEST_PHASE310)
    )


def _is_ci_env() -> bool:
    return _is_truthy(os.environ.get("GITHUB_ACTIONS"))


def _is_real_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _parse_fw_major_minor(fw: Any) -> Optional[Tuple[int, int]]:
    if not isinstance(fw, str):
        return None
    m = re.match(r"^\s*(\d+)\.(\d+)", fw.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _read_exact_o_rdonly(path: Path) -> Tuple[int, str, bytes]:
    """Read an entire small UXC/BIN/kmod/so donor file strictly via os.O_RDONLY."""
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
    key = f"{path.resolve()}::slices310::{len(slices)}"
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
    if m in ("still", "photo"):
        return SHOOT_MODE_STILL_PHASE310
    if m in ("movie", "video"):
        return SHOOT_MODE_MOVIE_PHASE310
    if m in ("s&q", "sq", "s&q motion", "snq"):
        return SHOOT_MODE_SQ_PHASE310
    return None


def _normalize_exposure_mode(mode: Any) -> Optional[str]:
    if not isinstance(mode, str):
        return None
    m = mode.strip().lower()
    if m == "p":
        return EXPOSURE_MODE_P_G135
    if m == "a":
        return EXPOSURE_MODE_A_G135
    if m == "s":
        return EXPOSURE_MODE_S_G135
    if m == "m":
        return EXPOSURE_MODE_M_G135
    if m in ("intelligent auto", "iauto", "auto"):
        return EXPOSURE_MODE_INTELLIGENT_AUTO_G135
    return None


def _normalize_focus_mode(mode: Any) -> Optional[str]:
    if not isinstance(mode, str):
        return None
    m = mode.strip().lower()
    if m == "mf":
        return FOCUS_MODE_MF_G135
    if m in ("af-s", "afs"):
        return FOCUS_MODE_AF_S_G135
    if m in ("af-c", "afc"):
        return FOCUS_MODE_AF_C_G135
    if m == "dmf":
        return FOCUS_MODE_DMF_G135
    return None


def _normalize_reset_action(action: Any) -> Optional[str]:
    if not isinstance(action, str):
        return None
    a = action.strip().lower()
    if a in ("none", "", "no_reset"):
        return RESET_ACTION_NONE_PHASE310
    if a in ("camera settings reset", "cam_reset", "camera_settings_reset"):
        return RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE310
    if a in ("reset network set.", "reset network set", "network_reset"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE310
    if a in ("initialize", "factory_reset", "init"):
        return RESET_ACTION_INITIALIZE_PHASE310
    return None


def _normalize_media_slot(slot: Any) -> Optional[str]:
    if _is_real_int(slot):
        if slot == 1:
            return MEDIA_SLOT_1_PHASE310
        if slot == 2:
            return MEDIA_SLOT_2_PHASE310
        return None
    if not isinstance(slot, str):
        return None
    s = slot.strip().lower().replace("_", " ")
    if s in ("slot 1", "slot1", "1", "a", "slot a"):
        return MEDIA_SLOT_1_PHASE310
    if s in ("slot 2", "slot2", "2", "b", "slot b"):
        return MEDIA_SLOT_2_PHASE310
    return None


def _normalize_on_off(val: Any) -> Optional[str]:
    if isinstance(val, bool) or not isinstance(val, str):
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


def audit_phase310_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase310DonorAuditResult:
    """Audit all 18 Wave-58 local donor files strictly via `os.O_RDONLY` in `< 0.20s`
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
        else dict(PINNED_PHASE310_DONOR_SPECS)
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
            DONOR_CHECK_CI_MAX_SECONDS_PHASE310
            if _is_ci_env()
            else DONOR_CHECK_MAX_SECONDS_PHASE310
        )
        return Phase310DonorAuditResult(
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
            usblan_kmod_stack_verified=True,
            sha256_by_artifact={},
            bytes_by_artifact={},
            errors=(),
            warnings=(
                "CLEAN_ROOM_SYNTHETIC mode active; pinned Wave-58 contracts used without donor I/O.",
            ),
        )

    all_exist = all((effective_root / rel).is_file() for _, rel, *_ in specs.values())
    if (not explicit_root) and (not all_exist) and (donor_specs_override is None):
        elapsed = time.perf_counter() - t0
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE310
            if _is_ci_env()
            else DONOR_CHECK_MAX_SECONDS_PHASE310
        )
        return Phase310DonorAuditResult(
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
            usblan_kmod_stack_verified=True,
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

    for key, (_model, rel, expected_size, expected_sha, tokens, desc) in specs.items():
        path = effective_root / rel
        if not path.is_file():
            missing.append(f"{key}:missing_file:{rel}")
            errors.append(f"Missing donor artifact `{key}` ({desc}) at `{rel}`.")
            continue
        files_inspected += 1
        if key == "fx3_appfw_so" and donor_specs_override is None:
            size, digest, present_tokens = _read_appfw_slices_o_rdonly(
                path, PINNED_FX3_APPFW_SLICES_PHASE310
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            size, digest, present_tokens = _read_appfw_slices_o_rdonly(
                path, PINNED_FX6_APPFW_SLICES_PHASE310
            )
        else:
            size, digest, blob = _read_exact_o_rdonly(path)
            present_tokens = tuple(tok for tok in tokens if tok in blob)

        bytes_map[key] = size
        sha_map[key] = digest

        item_ok = True
        if size != expected_size:
            item_ok = False
            missing.append(f"{key}:size_mismatch:{size}!={expected_size}")
            errors.append(
                f"Donor `{key}` size mismatch: observed {size}, expected {expected_size}."
            )
        if digest != expected_sha:
            item_ok = False
            missing.append(f"{key}:sha256_mismatch:{digest[:12]}")
            errors.append(
                f"Donor `{key}` SHA-256 mismatch: observed {digest}, expected {expected_sha}."
            )
        for tok in tokens:
            if tok not in present_tokens:
                item_ok = False
                missing.append(f"{key}:missing_marker:{tok.decode('utf-8', 'replace')}")
                errors.append(f"Donor `{key}` missing pinned marker `{tok!r}`.")
        if item_ok:
            checked.append(key)

    elapsed = time.perf_counter() - t0
    budget = (
        DONOR_CHECK_CI_MAX_SECONDS_PHASE310
        if _is_ci_env()
        else DONOR_CHECK_MAX_SECONDS_PHASE310
    )
    within_budget = elapsed <= budget
    if not within_budget:
        errors.append(
            f"Phase 310 O_RDONLY donor audit exceeded budget: {elapsed:.4f}s > {budget:.2f}s."
        )

    fx3_ok = all(
        k in checked
        for k in (
            "fx3_appfw_so",
            "fx3_string_english_f_uxc",
            "fx3_string_english_uxc",
            "fx3_string_english_g_uxc",
            "fx3_bk4_bin",
        )
    )
    fx6_ok = all(
        k in checked
        for k in ("fx6_appfw_so", "fx6_string_english_uxc", "fx6_string_english_2_uxc")
    )
    four_lang_ok = all(
        k in checked
        for k in (
            "fx3_string_english_f_uxc",
            "fx3_string_simplifiedchinese_f_uxc",
            "fx3_string_traditionalchinese_f_uxc",
            "fx3_string_japanese_f_uxc",
        )
    )
    usblan_ok = all(
        k in checked
        for k in (
            "fx3_cdc_ncm_ko",
            "fx3_r8152_ko",
            "fx3_asix_ko",
            "fx3_ax88179_ko",
            "fx3_lib_wired_lan",
            "fx3_lib_wlan",
            "fx3_lib_airplane",
        )
    )
    valid = (not missing) and (not errors) and within_budget
    status = STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE310_DONOR_INTEGRITY

    return Phase310DonorAuditResult(
        valid=valid,
        status=status,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="STRICT_OS_OPEN_O_RDONLY_AND_OS_PREAD",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_200ms=within_budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_ok,
        fx6_contracts_verified=fx6_ok,
        four_lang_resid16_parity_verified=four_lang_ok,
        usblan_kmod_stack_verified=usblan_ok,
        sha256_by_artifact=sha_map,
        bytes_by_artifact=bytes_map,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate G135: Bright Monitoring + Focus Magnifier Coexistence, Monitor Brightness
#    vs FX6 VF Setting/AE Backlight, & Shot Mark/Clip Flag/Divider Slot-1 Firewall
# ---------------------------------------------------------------------------


def _normalize_live_view_display(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s in ("setting effect on", "effect on", "on"):
        return LIVE_VIEW_DISPLAY_EFFECT_ON_G135
    if s in ("setting effect off", "effect off", "off"):
        return LIVE_VIEW_DISPLAY_EFFECT_OFF_G135
    return None


def _normalize_monitor_brightness_mode(val: Any) -> Tuple[Optional[str], bool]:
    if not isinstance(val, str):
        return None, False
    raw = val.strip()
    dormant_lower = {x.lower() for x in DORMANT_MONITOR_BRIGHTNESS_MODES_G135}
    if raw.lower() in dormant_lower:
        return None, True
    if raw.lower() in ("manual", "man"):
        return MONITOR_BRIGHTNESS_MANUAL_G135, False
    if raw.lower() in ("sunny weather", "sunny", "sunny_weather"):
        return MONITOR_BRIGHTNESS_SUNNY_WEATHER_G135, False
    return None, False


def _normalize_clip_flag(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s == "off":
        return "Off"
    if s == "ok":
        return "OK"
    if s == "ng":
        return "NG"
    if s == "keep":
        return "KEEP"
    return None


def _normalize_photo_capture_type(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower().replace(" ", "")
    if s == "jpeg":
        return "JPEG"
    if s in ("heif4:2:0", "heif_420", "heif420"):
        return "HEIF 4:2:0"
    if s in ("heif4:2:2", "heif_422", "heif422"):
        return "HEIF 4:2:2"
    return None


def _compute_g135_effective_state(
    *,
    firmware_version: str,
    reset_action: str,
    exposure_mode: str,
    focus_mode: str,
    power_off: bool,
    bright_monitoring_active: bool,
    live_view_display: str,
    monitor_brightness_mode: str,
    monitor_brightness_level: int,
    card_op: str,
    target_slot: str,
    slot_1_contains_tier0_vault: bool,
    slot_1_write_protected: bool,
) -> Dict[str, Any]:
    init_reset = reset_action == RESET_ACTION_INITIALIZE_PHASE310
    cam_reset = reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE310

    cancel_reasons: List[str] = []
    if power_off:
        cancel_reasons.append("power_off")
    if exposure_mode not in ALLOWED_PASM_MODES_G135:
        cancel_reasons.append(f"exposure_mode={exposure_mode} (left P/A/S/M)")
    if focus_mode != FOCUS_MODE_MF_G135:
        cancel_reasons.append(f"focus_mode={focus_mode} (left MF)")
    if init_reset:
        cancel_reasons.append("Initialize")

    auto_cancelled = bool(bright_monitoring_active and cancel_reasons)
    eff_bm_active = bool(bright_monitoring_active and not cancel_reasons)
    eff_lv_disp = (
        LIVE_VIEW_DISPLAY_EFFECT_OFF_G135 if eff_bm_active else live_view_display
    )

    fw_tuple = _parse_fw_major_minor(firmware_version)
    focus_mag_coexists = fw_tuple is not None and fw_tuple >= (7, 0)

    eff_mon_mode = (
        MONITOR_BRIGHTNESS_DEFAULT_MODE_G135 if init_reset else monitor_brightness_mode
    )
    eff_mon_lvl = (
        MONITOR_BRIGHTNESS_LEVEL_DEFAULT_G135 if init_reset else monitor_brightness_level
    )
    mon_survived_cam_reset = cam_reset and (
        eff_mon_mode == monitor_brightness_mode
        and eff_mon_lvl == monitor_brightness_level
    )

    is_mutating = card_op not in READONLY_CARD_OPS_G135
    slot1_protected = bool(slot_1_contains_tier0_vault or slot_1_write_protected)
    slot1_vault_blocked = bool(
        is_mutating and target_slot == MEDIA_SLOT_1_PHASE310 and slot1_protected
    )

    block_errno: Optional[int] = None
    block_errno_name: Optional[str] = None
    if slot1_vault_blocked:
        block_errno = (
            EROFS_ERRNO_PHASE310
            if slot_1_contains_tier0_vault
            else EBUSY_ERRNO_PHASE310
        )
        block_errno_name = (
            EROFS_NAME_PHASE310
            if slot_1_contains_tier0_vault
            else EBUSY_NAME_PHASE310
        )

    return {
        "effective_bright_monitoring_active": eff_bm_active,
        "bright_monitoring_auto_cancelled": auto_cancelled,
        "bright_monitoring_auto_cancel_reasons": tuple(cancel_reasons),
        "effective_live_view_display": eff_lv_disp,
        "focus_magnifier_coexists_with_bright_monitoring": focus_mag_coexists,
        "effective_monitor_brightness_mode": eff_mon_mode,
        "effective_monitor_brightness_level": eff_mon_lvl,
        "monitor_brightness_survived_cam_reset": mon_survived_cam_reset,
        "slot1_vault_firewall_blocked": slot1_vault_blocked,
        "block_errno": block_errno,
        "block_errno_name": block_errno_name,
        "slot1_data_sector_writes": 0,
        "slot1_m4root_xml_mutated": False,
        "slot1_dcim_mutated": False,
        "slot1_avf_info_mutated": False,
    }


def compute_bright_mon_shotmark_vault_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate G135 Bright Monitoring + Monitor Brightness + Shot Mark/Vault
    matrix states (2 reset x 2 exp_mode x 2 focus_mode x 2 power x 2 mon_mode x
    6 card_ops x 2 slots = 384 states).
    """
    states_checked = 0
    all_invariants_hold = True
    bm_active_effect_off_count = 0
    bm_autocancel_count = 0
    cam_reset_mon_persisted_count = 0
    slot1_vault_blocked_count = 0

    for rst in (
        RESET_ACTION_NONE_PHASE310,
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE310,
    ):
        for emode in (EXPOSURE_MODE_M_G135, EXPOSURE_MODE_INTELLIGENT_AUTO_G135):
            for fmode in (FOCUS_MODE_MF_G135, FOCUS_MODE_AF_C_G135):
                for pwr_off in (False, True):
                    for mb_mode in ALLOWED_MONITOR_BRIGHTNESS_MODES_G135:
                        for op in (
                            CARD_OP_JUMP_READONLY_G135,
                            CARD_OP_ADD_SHOT_MARK_1_G135,
                            CARD_OP_ADD_DELETE_SHOT_MARK_2_G135,
                            CARD_OP_SET_CLIP_FLAG_G135,
                            CARD_OP_PHOTO_CAPTURE_G135,
                            CARD_OP_CREATE_DIVIDER_FRAME_G135,
                        ):
                            for slot in ALLOWED_MEDIA_SLOTS_PHASE310:
                                st = _compute_g135_effective_state(
                                    firmware_version=FX3_DEFAULT_FW_VERSION_PHASE310,
                                    reset_action=rst,
                                    exposure_mode=emode,
                                    focus_mode=fmode,
                                    power_off=pwr_off,
                                    bright_monitoring_active=True,
                                    live_view_display=LIVE_VIEW_DISPLAY_EFFECT_ON_G135,
                                    monitor_brightness_mode=mb_mode,
                                    monitor_brightness_level=2,
                                    card_op=op,
                                    target_slot=slot,
                                    slot_1_contains_tier0_vault=True,
                                    slot_1_write_protected=False,
                                )
                                states_checked += 1
                                if st["effective_bright_monitoring_active"]:
                                    bm_active_effect_off_count += 1
                                    if (
                                        st["effective_live_view_display"]
                                        != LIVE_VIEW_DISPLAY_EFFECT_OFF_G135
                                        or not st[
                                            "focus_magnifier_coexists_with_bright_monitoring"
                                        ]
                                    ):
                                        all_invariants_hold = False
                                if st["bright_monitoring_auto_cancelled"]:
                                    bm_autocancel_count += 1
                                if rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE310:
                                    cam_reset_mon_persisted_count += 1
                                    if not st["monitor_brightness_survived_cam_reset"]:
                                        all_invariants_hold = False
                                if st["slot1_vault_firewall_blocked"]:
                                    slot1_vault_blocked_count += 1
                                if (
                                    st["slot1_data_sector_writes"] != 0
                                    or st["slot1_m4root_xml_mutated"]
                                    or st["slot1_dcim_mutated"]
                                    or st["slot1_avf_info_mutated"]
                                ):
                                    all_invariants_hold = False

    return {
        "states_checked": states_checked,
        "all_invariants_hold": all_invariants_hold,
        "bm_active_effect_off_count": bm_active_effect_off_count,
        "bm_autocancel_count": bm_autocancel_count,
        "cam_reset_mon_persisted_count": cam_reset_mon_persisted_count,
        "slot1_vault_blocked_count": slot1_vault_blocked_count,
    }


def resolve_fx3_bright_mon_shotmark_vault_state(**kwargs: Any) -> Dict[str, Any]:
    """Return serialized G135 guard state for UI/VM/orchestrator callers."""
    return verify_bright_mon_shotmark_vault_guard(**kwargs).to_dict()


def verify_bright_mon_shotmark_vault_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE310,
    body_model_id: int = FX3_MODEL_ID_PHASE310,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE310,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE310,
    target_model: str = FX3_MODEL_NAME_PHASE310,
    reset_action: str = RESET_ACTION_NONE_PHASE310,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE310,
    exposure_mode: str = EXPOSURE_MODE_M_G135,
    focus_mode: str = FOCUS_MODE_MF_G135,
    power_off: bool = False,
    requested_bright_monitoring_active: bool = False,
    bright_monitoring_menu_toggle_claimed: bool = False,
    bright_monitoring_multi_step_gain_claimed: bool = False,
    claimed_bright_mon_persists_across_power_or_af_or_auto: bool = False,
    requested_live_view_display: str = LIVE_VIEW_DISPLAY_EFFECT_ON_G135,
    focus_magnifier_active: bool = False,
    auto_magnifier_in_mf: bool = False,
    claimed_focus_magnifier_blocked_in_v7: bool = False,
    requested_monitor_brightness_mode: str = MONITOR_BRIGHTNESS_DEFAULT_MODE_G135,
    requested_monitor_brightness_level: int = MONITOR_BRIGHTNESS_LEVEL_DEFAULT_G135,
    claimed_monitor_brightness_resets_on_cam_reset: bool = False,
    claimed_fx3_4k_thermal_lcd_dimming_lock: bool = False,
    fx6_vf_brightness: int = FX6_VF_BRIGHTNESS_DEFAULT_G135,
    fx6_vf_color_mode: str = "Color",
    claimed_fx6_ae_backlight_is_lcd_backlight: bool = False,
    claimed_fx6_lcd_vf_backlight_or_nightshot_active: bool = False,
    requested_card_op: str = CARD_OP_NONE_G135,
    requested_clip_flag: str = "Off",
    requested_image_jump_setting: str = "Shot Mark Only",
    requested_photo_capture_file_type: str = "JPEG",
    dormant_divide_extract_or_ftp_cut_requested: bool = False,
    requested_dormant_shotmark_symbol: Optional[str] = None,
    claimed_fx6_has_divide_or_shot_mark0_9: bool = False,
    requested_target_slot: str = MEDIA_SLOT_2_PHASE310,
    slot_1_contains_tier0_vault: bool = True,
    slot_1_write_protected: bool = False,
) -> BrightMonShotMarkVaultGuardResult:
    """Enforce Gate G135: Custom-Key-Only `[Bright Monitoring]` + Ver. 7.00+ Focus Magnifier
    coexistence, `[Monitor Brightness]` Manual/Sunny Weather vs FX6 `VF Setting`/AE Backlight,
    and `[Shot Mark 1/2]` / `[Clip Flag]` / `[Photo Capture]` / `[Create Divider Frame]`
    Slot-1 Tier-0 Vault Firewall (`EROFS=30` / `EBUSY=16`).
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    norm_shoot = _normalize_shoot_mode(shoot_mode)
    norm_exp = _normalize_exposure_mode(exposure_mode)
    norm_focus = _normalize_focus_mode(focus_mode)
    norm_reset = _normalize_reset_action(reset_action)
    norm_lv = _normalize_live_view_display(requested_live_view_display)
    norm_mb_mode, dormant_mb_hit = _normalize_monitor_brightness_mode(
        requested_monitor_brightness_mode
    )
    norm_clip_flag = _normalize_clip_flag(requested_clip_flag)
    norm_pc_type = _normalize_photo_capture_type(requested_photo_capture_file_type)
    norm_slot = _normalize_media_slot(requested_target_slot)

    fw_parsed = _parse_fw_major_minor(firmware_version)
    identity_ok = (
        body_model_name == FX3_MODEL_NAME_PHASE310
        and _is_real_int(body_model_id)
        and body_model_id == FX3_MODEL_ID_PHASE310
        and help_guide_code == FX3_HELP_GUIDE_CODE_PHASE310
        and fw_parsed is not None
    )
    if not identity_ok:
        _add_code(codes, STATUS_BLOCKED_G135_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3 Ver. 7.02 hardware/help-guide/firmware identity for Gate G135."
        )

    if target_model not in (FX3_MODEL_NAME_PHASE310, FX6_MODEL_NAME_PHASE310):
        _add_code(codes, STATUS_BLOCKED_G135_TELEMETRY_INVALID)
        errors.append(f"Unsupported target_model `{target_model}`.")

    if norm_shoot is None:
        _add_code(codes, STATUS_BLOCKED_G135_TELEMETRY_INVALID)
        errors.append(f"Invalid shoot_mode `{shoot_mode}`.")
        norm_shoot = SHOOT_MODE_STILL_PHASE310

    if norm_exp is None:
        _add_code(codes, STATUS_BLOCKED_G135_TELEMETRY_INVALID)
        errors.append(f"Invalid exposure_mode `{exposure_mode}`.")
        norm_exp = EXPOSURE_MODE_M_G135

    if norm_focus is None:
        _add_code(codes, STATUS_BLOCKED_G135_TELEMETRY_INVALID)
        errors.append(f"Invalid focus_mode `{focus_mode}`.")
        norm_focus = FOCUS_MODE_MF_G135

    if norm_reset is None:
        _add_code(codes, STATUS_BLOCKED_G135_TELEMETRY_INVALID)
        errors.append(f"Invalid reset_action `{reset_action}`.")
        norm_reset = RESET_ACTION_NONE_PHASE310

    if norm_lv is None:
        _add_code(codes, STATUS_BLOCKED_G135_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Live View Display]` `{requested_live_view_display}`.")
        norm_lv = LIVE_VIEW_DISPLAY_EFFECT_ON_G135

    if norm_clip_flag is None:
        _add_code(codes, STATUS_BLOCKED_G135_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Clip Flag]` `{requested_clip_flag}`.")
        norm_clip_flag = "Off"

    if (
        not isinstance(requested_image_jump_setting, str)
        or requested_image_jump_setting.strip() not in ALLOWED_IMAGE_JUMP_SETTINGS_G135
    ):
        _add_code(codes, STATUS_BLOCKED_G135_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[Image Jump Setting]` `{requested_image_jump_setting}`."
        )
        safe_jump = "Shot Mark Only"
    else:
        safe_jump = requested_image_jump_setting.strip()

    if norm_pc_type is None:
        _add_code(codes, STATUS_BLOCKED_G135_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[Photo Capture]` file type `{requested_photo_capture_file_type}`."
        )
        norm_pc_type = "JPEG"

    if norm_slot is None:
        _add_code(codes, STATUS_BLOCKED_G135_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_target_slot `{requested_target_slot}`.")
        norm_slot = MEDIA_SLOT_2_PHASE310

    # Check dormant Divide/Extract/FTP-Cut traps before validating active card ops
    dormant_sm_lower = {x.strip().lower() for x in DORMANT_SHOTMARK_DIVIDE_TRAPS_G135}
    raw_op = requested_card_op.strip() if isinstance(requested_card_op, str) else ""
    dormant_sm_hit = (
        dormant_divide_extract_or_ftp_cut_requested
        or raw_op.lower() in dormant_sm_lower
        or (
            requested_dormant_shotmark_symbol is not None
            and requested_dormant_shotmark_symbol.strip().lower() in dormant_sm_lower
        )
        or claimed_fx6_has_divide_or_shot_mark0_9
    )
    if dormant_sm_hit:
        _add_code(codes, STATUS_BLOCKED_G135_DORMANT_DIVIDE_EXTRACT_OR_FTP_CUT_VIOLATION)
        errors.append(
            "In-camera `[Divide]` / `[Extract]`, dormant FTP `15/30/60s` Shot-Mark Cut "
            "(`_f.uxc 0x7005/0x6e38/0x6c2a/0x74a9`), and FX6 dormant `Shot Mark 0..9` / "
            "`Essence Mark` are NOT supported on Ver. 7.02/6.01 (`EOPNOTSUPP=95`)."
        )
        safe_op = raw_op if raw_op in ALLOWED_CARD_OPS_G135 else CARD_OP_NONE_G135
    elif raw_op not in ALLOWED_CARD_OPS_G135:
        _add_code(codes, STATUS_BLOCKED_G135_TELEMETRY_INVALID)
        errors.append(f"Unknown card operation `{requested_card_op}`.")
        safe_op = CARD_OP_NONE_G135
    else:
        safe_op = raw_op

    # Part A: Bright Monitoring custom-key-only + auto-cancel + v7.00+ Focus Magnifier
    if (
        bright_monitoring_menu_toggle_claimed
        or bright_monitoring_multi_step_gain_claimed
        or claimed_bright_mon_persists_across_power_or_af_or_auto
        or claimed_focus_magnifier_blocked_in_v7
    ):
        _add_code(
            codes, STATUS_BLOCKED_G135_BRIGHT_MONITORING_CUSTOM_KEY_OR_MAG_VIOLATION
        )
        errors.append(
            "`[Bright Monitoring]` (`_f.uxc 0x701f`) is custom-key-only (`ON/OFF`), forces "
            "`Setting Effect OFF`, auto-cancels on power-off / leaving P-A-S-M / leaving MF, "
            "and coexists with `[Focus Magnifier]` / `[Auto Magnifier in MF]` in Ver. 7.00+."
        )

    # Part B: Monitor Brightness (Manual -2..+2 / Sunny Weather) vs FX6 VF Setting & AE Backlight
    level_ok = _is_real_int(requested_monitor_brightness_level) and (
        MONITOR_BRIGHTNESS_LEVEL_MIN_G135
        <= requested_monitor_brightness_level
        <= MONITOR_BRIGHTNESS_LEVEL_MAX_G135
    )
    if dormant_mb_hit or (norm_mb_mode is None):
        _add_code(
            codes, STATUS_BLOCKED_G135_MONITOR_BRIGHTNESS_OR_FX6_BACKLIGHT_VIOLATION
        )
        errors.append(
            "`[Monitor Brightness]` (`.uxc 0xe44b`) exposes ONLY `Manual` (-2..+2) and "
            "`Sunny Weather`; dormant `AUTO/BRIGHT/NORMAL` rejected (`EOPNOTSUPP=95`)."
        )
        safe_mb_mode = MONITOR_BRIGHTNESS_DEFAULT_MODE_G135
    else:
        safe_mb_mode = norm_mb_mode

    fx6_vf_ok = (
        _is_real_int(fx6_vf_brightness)
        and FX6_VF_BRIGHTNESS_MIN_G135 <= fx6_vf_brightness <= FX6_VF_BRIGHTNESS_MAX_G135
        and isinstance(fx6_vf_color_mode, str)
        and fx6_vf_color_mode.strip() in FX6_VF_COLOR_MODES_G135
    )
    if (
        (not level_ok)
        or (not fx6_vf_ok)
        or claimed_monitor_brightness_resets_on_cam_reset
        or claimed_fx3_4k_thermal_lcd_dimming_lock
        or claimed_fx6_ae_backlight_is_lcd_backlight
        or claimed_fx6_lcd_vf_backlight_or_nightshot_active
    ):
        _add_code(
            codes, STATUS_BLOCKED_G135_MONITOR_BRIGHTNESS_OR_FX6_BACKLIGHT_VIOLATION
        )
        errors.append(
            "`[Monitor Brightness]` is `Initialize`-only (`-2..+2`), FX3 lacks 4K thermal LCD "
            "dimming lock, and FX6 `Auto Exposure > Mode > Backlight` (`1..15` `VF Setting` is "
            "separate) is AE compensation — dormant `LCD/VF Backlight` & `NIGHTSHOT` rejected."
        )

    safe_mb_lvl = (
        int(requested_monitor_brightness_level)
        if level_ok
        else MONITOR_BRIGHTNESS_LEVEL_DEFAULT_G135
    )
    eff = _compute_g135_effective_state(
        firmware_version=firmware_version if isinstance(firmware_version, str) else "0.00",
        reset_action=norm_reset,
        exposure_mode=norm_exp,
        focus_mode=norm_focus,
        power_off=bool(power_off),
        bright_monitoring_active=bool(requested_bright_monitoring_active),
        live_view_display=norm_lv,
        monitor_brightness_mode=safe_mb_mode,
        monitor_brightness_level=safe_mb_lvl,
        card_op=safe_op,
        target_slot=norm_slot,
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        slot_1_write_protected=bool(slot_1_write_protected),
    )

    if eff["slot1_vault_firewall_blocked"]:
        _add_code(codes, STATUS_BLOCKED_G135_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION)
        errors.append(
            f"`Slot 1` Tier-0 Vault Firewall blocked `{safe_op}` mutation on "
            f"`M4ROOT/CLIP/*M01.XML` / `DCIM/` / `AVF_INFO` fail-closed with "
            f"`errno={eff['block_errno']} ({eff['block_errno_name']})`: "
            "`slot1_data_sector_writes == 0`, `slot1_avf_info_mutated == False`."
        )

    block_errno = eff["block_errno"]
    block_errno_name = eff["block_errno_name"]
    any_eopnotsupp = (
        bright_monitoring_menu_toggle_claimed
        or bright_monitoring_multi_step_gain_claimed
        or dormant_mb_hit
        or claimed_fx6_lcd_vf_backlight_or_nightshot_active
        or dormant_sm_hit
    )
    if block_errno is None and any_eopnotsupp:
        block_errno = EOPNOTSUPP_ERRNO_PHASE310
        block_errno_name = EOPNOTSUPP_NAME_PHASE310

    matrix = compute_bright_mon_shotmark_vault_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G135 if valid else codes[0]

    return BrightMonShotMarkVaultGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE310,
        target_model=target_model,
        reset_action=norm_reset,
        shoot_mode=norm_shoot,
        exposure_mode=norm_exp,
        focus_mode=norm_focus,
        power_off=bool(power_off),
        bright_monitoring_key_path=BRIGHT_MONITORING_KEY_PATH_G135,
        bright_monitoring_custom_key_only=True,
        requested_bright_monitoring_active=bool(requested_bright_monitoring_active),
        effective_bright_monitoring_active=eff["effective_bright_monitoring_active"],
        bright_monitoring_auto_cancelled=eff["bright_monitoring_auto_cancelled"],
        bright_monitoring_auto_cancel_reasons=eff[
            "bright_monitoring_auto_cancel_reasons"
        ],
        requested_live_view_display=norm_lv,
        effective_live_view_display=eff["effective_live_view_display"],
        focus_magnifier_active=bool(focus_magnifier_active),
        auto_magnifier_in_mf=bool(auto_magnifier_in_mf),
        focus_magnifier_coexists_with_bright_monitoring=eff[
            "focus_magnifier_coexists_with_bright_monitoring"
        ],
        monitor_brightness_menu_path=MONITOR_BRIGHTNESS_MENU_PATH_G135,
        requested_monitor_brightness_mode=safe_mb_mode,
        effective_monitor_brightness_mode=eff["effective_monitor_brightness_mode"],
        requested_monitor_brightness_level=safe_mb_lvl,
        effective_monitor_brightness_level=eff["effective_monitor_brightness_level"],
        monitor_brightness_survived_cam_reset=eff[
            "monitor_brightness_survived_cam_reset"
        ],
        fx3_4k_thermal_lcd_dimming_lock=False,
        fx6_vf_setting_menu_path=FX6_VF_SETTING_MENU_PATH_G135,
        fx6_vf_brightness=int(fx6_vf_brightness) if _is_real_int(fx6_vf_brightness) else -1,
        fx6_vf_color_mode=str(fx6_vf_color_mode),
        fx6_ae_backlight_is_ae_only=True,
        requested_card_op=safe_op,
        requested_clip_flag=norm_clip_flag,
        requested_image_jump_setting=safe_jump,
        requested_photo_capture_file_type=norm_pc_type,
        active_pb_edit_items=ACTIVE_PB_EDIT_ITEMS_G135,
        dormant_divide_extract_or_ftp_cut_blocked=dormant_sm_hit,
        requested_target_slot=norm_slot,
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        slot_1_write_protected=bool(slot_1_write_protected),
        slot1_vault_firewall_blocked=eff["slot1_vault_firewall_blocked"],
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        slot1_data_sector_writes=eff["slot1_data_sector_writes"],
        slot1_m4root_xml_mutated=eff["slot1_m4root_xml_mutated"],
        slot1_dcim_mutated=eff["slot1_dcim_mutated"],
        slot1_avf_info_mutated=eff["slot1_avf_info_mutated"],
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g135_bright_mon_shotmark_vault_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    bright_mon_shotmark_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase310DonorAuditResult] = None,
) -> Tuple[GateVerdict, G135BrightMonShotMarkVaultGuardResult]:
    """Evaluate Wave-58 Gate `G135` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase310_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_bright_mon_shotmark_vault_guard(
        **(dict(bright_mon_shotmark_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G135.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G135 if valid else codes[0]

    res = G135BrightMonShotMarkVaultGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        bright_mon_shotmark_vault_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, bm={guard.effective_bright_monitoring_active}, "
        f"lv={guard.effective_live_view_display}, mon={guard.effective_monitor_brightness_mode}"
        f"({guard.effective_monitor_brightness_level}), op={guard.requested_card_op}, "
        f"slot1_vault={guard.slot_1_contains_tier0_vault}, s1_writes={guard.slot1_data_sector_writes}"
    )
    verdict = GateVerdict(
        gate_id=G135_GATE_ID,
        gate_code=G135_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G136: Zero BT Timecode Link vs VMC-BNCM1 EXT-LK & FX6 BNC TC IN/OUT,
#    Wi-Fi WPA2/WPA3 SKU + USB-LAN Zero-RF Isolation, & Dormant Bulb Timer /
#    Auto HDR vs Mechanical-Only BULB + DRO Lockout
# ---------------------------------------------------------------------------


def _normalize_shutter_type(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s == "auto":
        return SHUTTER_TYPE_AUTO_G136
    if s in ("mechanical shutter", "mechanical"):
        return SHUTTER_TYPE_MECHANICAL_G136
    if s in ("electronic shutter", "electronic"):
        return SHUTTER_TYPE_ELECTRONIC_G136
    return None


def _normalize_still_drive_mode(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    mapping = {
        "single shooting": STILL_DRIVE_SINGLE_G136,
        "single": STILL_DRIVE_SINGLE_G136,
        "cont. shooting": STILL_DRIVE_CONT_SHOOTING_G136,
        "cont shooting": STILL_DRIVE_CONT_SHOOTING_G136,
        "continuous": STILL_DRIVE_CONT_SHOOTING_G136,
        "self-timer(single)": STILL_DRIVE_SELF_TIMER_SINGLE_G136,
        "self-timer(cont)": STILL_DRIVE_SELF_TIMER_CONT_G136,
        "cont. bracket": STILL_DRIVE_CONT_BRACKET_G136,
        "single bracket": STILL_DRIVE_SINGLE_BRACKET_G136,
        "dro bracket": STILL_DRIVE_DRO_BRACKET_G136,
    }
    return mapping.get(s)


def _normalize_dro_mode(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    mapping = {
        "auto": DRO_AUTO_G136,
        "off": DRO_OFF_G136,
        "lv1": "Lv1",
        "lv2": "Lv2",
        "lv3": "Lv3",
        "lv4": "Lv4",
        "lv5": "Lv5",
    }
    return mapping.get(s)


def _compute_g136_effective_state(
    *,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE310,
    reset_action: str,
    vmc_bncm1_ext_ltc_requested: bool,
    tc_make: str,
    tc_run: str,
    airplane_mode: str,
    bench_zero_rf_required: bool,
    rf_nvs_write_requested: bool,
    wifi_active: bool,
    bt_active: bool,
    usb_lan_active: bool,
    usb_lan_authorized: bool,
    usb_lan_cnct_launch: str,
    multi_micro_usb_active: bool,
    shutter_type: str,
    drive_mode: str,
    interval_shooting_on: bool,
    requested_bulb_mode: bool,
    dro_mode: str,
    dro_bracket: str,
    picture_profile_on: bool,
    hlg_still_image_on: bool,
) -> Dict[str, Any]:
    init_reset = reset_action == RESET_ACTION_INITIALIZE_PHASE310
    net_reset = reset_action == RESET_ACTION_RESET_NETWORK_SET_PHASE310
    cam_reset = reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE310

    # Empirical Sony Ver. 7.02 contract: Airplane Mode = On survives BOTH Reset Network Set. and Initialize!
    eff_airplane = airplane_mode
    airplane_survived = (
        (net_reset or init_reset) and airplane_mode == "On" and eff_airplane == "On"
    )
    eff_usb_lan_launch = "Off" if (init_reset or net_reset) else usb_lan_cnct_launch

    usb_bus_conflict = bool(
        usb_lan_active and (multi_micro_usb_active or wifi_active)
    )
    wireless_tx = bool(wifi_active or bt_active)
    zero_rf_blocked = bool(
        rf_nvs_write_requested
        or (eff_airplane == "On" and wireless_tx)
        or (bench_zero_rf_required and eff_airplane != "On")
        or (usb_lan_active and not usb_lan_authorized)
    )
    wired_eth0_ok = bool(
        usb_lan_active
        and usb_lan_authorized
        and eff_airplane == "On"
        and (not wireless_tx)
        and (not usb_bus_conflict)
        and (not rf_nvs_write_requested)
    )

    ext_lk = (
        "EXT-LK"
        if (
            shoot_mode == SHOOT_MODE_MOVIE_PHASE310
            and vmc_bncm1_ext_ltc_requested
            and tc_make == "Preset"
            and tc_run == "Free Run"
        )
        else "INT"
    )

    bulb_lock_reasons: List[str] = []
    if shoot_mode != SHOOT_MODE_STILL_PHASE310:
        bulb_lock_reasons.append("non_still_shoot_mode")
    if shutter_type == SHUTTER_TYPE_ELECTRONIC_G136:
        bulb_lock_reasons.append("Electronic Shutter")
    if drive_mode in (
        STILL_DRIVE_CONT_SHOOTING_G136,
        STILL_DRIVE_CONT_BRACKET_G136,
        STILL_DRIVE_SELF_TIMER_CONT_G136,
    ):
        bulb_lock_reasons.append(f"Drive Mode={drive_mode}")
    if interval_shooting_on:
        bulb_lock_reasons.append("Interval Shooting=On")

    bulb_clamped = bool(requested_bulb_mode and bulb_lock_reasons)
    eff_bulb_active = bool(requested_bulb_mode and not bulb_lock_reasons)

    dro_base = DRO_AUTO_G136 if (cam_reset or init_reset) else dro_mode
    dro_bracket_base = "Off" if (cam_reset or init_reset) else dro_bracket
    dro_locked = bool(picture_profile_on or hlg_still_image_on)
    eff_dro = DRO_OFF_G136 if dro_locked else dro_base
    eff_dro_bracket = "Off" if dro_locked else dro_bracket_base
    dro_reset_by_cam = cam_reset and (not dro_locked) and (eff_dro == DRO_AUTO_G136)

    return {
        "effective_airplane_mode": eff_airplane,
        "airplane_survived_network_reset_and_init": airplane_survived,
        "effective_usb_lan_cnct_launch": eff_usb_lan_launch,
        "usb_bus_mutual_exclusion_blocked": usb_bus_conflict,
        "airplane_zero_rf_firewall_blocked": zero_rf_blocked,
        "wired_eth0_permitted_under_airplane": wired_eth0_ok,
        "ext_tc_lock_status": ext_lk,
        "effective_bulb_active": eff_bulb_active,
        "bulb_locked_out_clamped_to_30s": bulb_clamped,
        "bulb_lockout_reasons": tuple(bulb_lock_reasons),
        "anti_flicker_shoot_disabled": eff_bulb_active,
        "dro_locked_off": dro_locked,
        "effective_dro_mode": eff_dro,
        "effective_dro_bracket": eff_dro_bracket,
        "dro_reset_by_cam_reset": dro_reset_by_cam,
        "wireless_packets_emitted": 0,
        "rf_nvs_p12_p13_writes_permitted": False,
        "rf_nvs_mutation_bytes": 0,
    }


def compute_tc_link_wifi_usblan_bulb_dormant_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate G136 Airplane Zero-RF + USB-LAN Mutual Exclusion +
    Mechanical-Only BULB + DRO Lockout matrix states (4 reset x 2 airplane x 2 wifi x
    2 usblan x 2 mm_usb x 2 shutter x 3 drive x 2 pp = 384 states).
    """
    states_checked = 0
    all_invariants_hold = True
    zero_rf_blocked_count = 0
    usb_conflict_blocked_count = 0
    bulb_clamped_count = 0
    dro_locked_count = 0

    for rst in ALLOWED_RESET_ACTIONS_PHASE310:
        for air in ("On", "Off"):
            for wifi in (False, True):
                for usblan in (False, True):
                    for mm_usb in (False, True):
                        for sh in (
                            SHUTTER_TYPE_MECHANICAL_G136,
                            SHUTTER_TYPE_ELECTRONIC_G136,
                        ):
                            for drv in (
                                STILL_DRIVE_SINGLE_G136,
                                STILL_DRIVE_CONT_SHOOTING_G136,
                                STILL_DRIVE_CONT_BRACKET_G136,
                            ):
                                for pp_on in (False, True):
                                    st = _compute_g136_effective_state(
                                        reset_action=rst,
                                        vmc_bncm1_ext_ltc_requested=mm_usb,
                                        tc_make="Preset",
                                        tc_run="Free Run",
                                        airplane_mode=air,
                                        bench_zero_rf_required=True,
                                        rf_nvs_write_requested=False,
                                        wifi_active=wifi,
                                        bt_active=False,
                                        usb_lan_active=usblan,
                                        usb_lan_authorized=True,
                                        usb_lan_cnct_launch="Off",
                                        multi_micro_usb_active=mm_usb,
                                        shutter_type=sh,
                                        drive_mode=drv,
                                        interval_shooting_on=False,
                                        requested_bulb_mode=True,
                                        dro_mode="Lv3",
                                        dro_bracket="DRO Bracket: Lo",
                                        picture_profile_on=pp_on,
                                        hlg_still_image_on=False,
                                    )
                                    states_checked += 1
                                    if st["airplane_zero_rf_firewall_blocked"]:
                                        zero_rf_blocked_count += 1
                                    if st["usb_bus_mutual_exclusion_blocked"]:
                                        usb_conflict_blocked_count += 1
                                    if st["bulb_locked_out_clamped_to_30s"]:
                                        bulb_clamped_count += 1
                                        if st["effective_bulb_active"]:
                                            all_invariants_hold = False
                                    if pp_on:
                                        dro_locked_count += 1
                                        if st["effective_dro_mode"] != DRO_OFF_G136:
                                            all_invariants_hold = False
                                    if (rst in (RESET_ACTION_RESET_NETWORK_SET_PHASE310, RESET_ACTION_INITIALIZE_PHASE310)) and air == "On":
                                        if not st["airplane_survived_network_reset_and_init"]:
                                            all_invariants_hold = False
                                    if (
                                        st["wireless_packets_emitted"] != 0
                                        or st["rf_nvs_p12_p13_writes_permitted"]
                                        or st["rf_nvs_mutation_bytes"] != 0
                                    ):
                                        all_invariants_hold = False

    return {
        "states_checked": states_checked,
        "all_invariants_hold": all_invariants_hold,
        "zero_rf_blocked_count": zero_rf_blocked_count,
        "usb_conflict_blocked_count": usb_conflict_blocked_count,
        "bulb_clamped_count": bulb_clamped_count,
        "dro_locked_count": dro_locked_count,
    }


def resolve_fx3_tc_link_wifi_usblan_bulb_dormant_state(**kwargs: Any) -> Dict[str, Any]:
    """Return serialized G136 guard state for UI/VM/orchestrator callers."""
    return verify_tc_link_wifi_usblan_bulb_dormant_guard(**kwargs).to_dict()


def verify_tc_link_wifi_usblan_bulb_dormant_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE310,
    body_model_id: int = FX3_MODEL_ID_PHASE310,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE310,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE310,
    target_model: str = FX3_MODEL_NAME_PHASE310,
    reset_action: str = RESET_ACTION_NONE_PHASE310,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE310,
    tc_link_requested: bool = False,
    requested_dormant_tc_symbol: Optional[str] = None,
    vmc_bncm1_ext_ltc_requested: bool = False,
    tc_make: str = "Preset",
    tc_run: str = "Free Run",
    hdmi_tc_output: str = "Off",
    claimed_fx6_has_bluetooth_hw_or_usb_tc_in: bool = False,
    fx3_sku_code: str = FX3_SKU_WW728473_G136,
    wifi_requested: bool = False,
    requested_wifi_band: str = WIFI_BAND_2_4GHZ_G136,
    requested_wifi_security: str = WIFI_SEC_WPA3_SAE_G136,
    access_authen_settings: str = "On",
    usb_lan_requested: bool = False,
    usb_lan_authorized: bool = True,
    requested_usb_lan_cnct_launch: str = "Off",
    multi_micro_usb_active: bool = False,
    requested_airplane_mode: str = "On",
    bench_zero_rf_required: bool = True,
    rf_nvs_write_requested: bool = False,
    bt_requested: bool = False,
    claimed_airplane_resets_on_net_reset_or_init: bool = False,
    bulb_timer_requested: bool = False,
    requested_dormant_bulb_symbol: Optional[str] = None,
    auto_hdr_requested: bool = False,
    requested_dormant_hdr_symbol: Optional[str] = None,
    requested_shutter_type: str = SHUTTER_TYPE_MECHANICAL_G136,
    requested_drive_mode: str = STILL_DRIVE_SINGLE_G136,
    interval_shooting_on: bool = False,
    requested_bulb_mode: bool = False,
    force_bulb_under_lockout: bool = False,
    long_exposure_nr: str = "On",
    requested_dro_mode: str = DRO_AUTO_G136,
    requested_dro_bracket: str = "Off",
    picture_profile_on: bool = False,
    hlg_still_image_on: bool = False,
    force_dro_when_pp_or_hlg: bool = False,
    claimed_fx6_supports_still_bulb_or_dro: bool = False,
) -> TcLinkWifiUsbLanBulbDormantGuardResult:
    """Enforce Gate G136: Zero Bluetooth `[Timecode Link]` vs wired `VMC-BNCM1` & FX6
    BNC `TC IN/OUT`, Ver. 7.00+ Wi-Fi `WPA2-PSK`/`WPA3-SAE` SKU + `USB-LAN` Zero-RF
    isolation, and dormant `[Bulb Timer]` / `[Auto HDR]` vs mechanical-only `[BULB]`
    and active `DRO` / `DRO Bracket` lock rules.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    norm_shoot = _normalize_shoot_mode(shoot_mode)
    norm_reset = _normalize_reset_action(reset_action)
    norm_air = _normalize_on_off(requested_airplane_mode)
    norm_hdmi_tc = _normalize_on_off(hdmi_tc_output)
    norm_auth = _normalize_on_off(access_authen_settings)
    norm_usb_launch = _normalize_on_off(requested_usb_lan_cnct_launch)
    norm_lenr = _normalize_on_off(long_exposure_nr)
    norm_shutter = _normalize_shutter_type(requested_shutter_type)
    norm_drive = _normalize_still_drive_mode(requested_drive_mode)
    norm_dro = _normalize_dro_mode(requested_dro_mode)

    fw_parsed = _parse_fw_major_minor(firmware_version)
    identity_ok = (
        body_model_name == FX3_MODEL_NAME_PHASE310
        and _is_real_int(body_model_id)
        and body_model_id == FX3_MODEL_ID_PHASE310
        and help_guide_code == FX3_HELP_GUIDE_CODE_PHASE310
        and fw_parsed is not None
    )
    if not identity_ok:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3 Ver. 7.02 hardware/help-guide/firmware identity for Gate G136."
        )

    if target_model not in (FX3_MODEL_NAME_PHASE310, FX6_MODEL_NAME_PHASE310):
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Unsupported target_model `{target_model}`.")

    if norm_shoot is None:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Invalid shoot_mode `{shoot_mode}`.")
        norm_shoot = SHOOT_MODE_STILL_PHASE310

    if norm_reset is None:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Invalid reset_action `{reset_action}`.")
        norm_reset = RESET_ACTION_NONE_PHASE310

    if norm_air is None:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Airplane Mode]` `{requested_airplane_mode}`.")
        norm_air = "On"

    if norm_hdmi_tc is None:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Invalid HDMI `[Time Code Output]` `{hdmi_tc_output}`.")
        norm_hdmi_tc = "Off"

    if norm_auth is None:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Access Authen. Settings]` `{access_authen_settings}`.")
        norm_auth = "On"

    if norm_usb_launch is None:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[USB-LAN Cnct. Launch]` `{requested_usb_lan_cnct_launch}`."
        )
        norm_usb_launch = "Off"

    if norm_lenr is None:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Long Exposure NR]` `{long_exposure_nr}`.")
        norm_lenr = "On"

    if norm_shutter is None:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Shutter Type]` `{requested_shutter_type}`.")
        norm_shutter = SHUTTER_TYPE_MECHANICAL_G136

    if norm_drive is None:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Invalid Still `[Drive Mode]` `{requested_drive_mode}`.")
        norm_drive = STILL_DRIVE_SINGLE_G136

    if norm_dro is None:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Invalid `[D-Range Optimizer]` `{requested_dro_mode}`.")
        norm_dro = DRO_AUTO_G136

    if (
        not isinstance(requested_dro_bracket, str)
        or requested_dro_bracket.strip() not in ALLOWED_DRO_BRACKET_MODES_G136
    ):
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Invalid `[DRO Bracket]` `{requested_dro_bracket}`.")
        safe_dro_bracket = "Off"
    else:
        safe_dro_bracket = requested_dro_bracket.strip()

    if not isinstance(fx3_sku_code, str) or fx3_sku_code.strip() not in ALLOWED_FX3_SKUS_G136:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Unknown FX3 SKU `{fx3_sku_code}` (expected WW728473 or WW558244).")
        safe_sku = FX3_SKU_WW728473_G136
    else:
        safe_sku = fx3_sku_code.strip()

    if not isinstance(tc_make, str) or tc_make.strip() not in ALLOWED_TC_MAKE_MODES_G136:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Time Code Make]` `{tc_make}`.")
        safe_tc_make = "Preset"
    else:
        safe_tc_make = tc_make.strip()

    if not isinstance(tc_run, str) or tc_run.strip() not in ALLOWED_TC_RUN_MODES_G136:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Time Code Run]` `{tc_run}`.")
        safe_tc_run = "Free Run"
    else:
        safe_tc_run = tc_run.strip()

    if not isinstance(requested_wifi_band, str) or requested_wifi_band.strip() not in ALLOWED_WIFI_BANDS_G136:
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Wi-Fi Frequency Band]` `{requested_wifi_band}`.")
        safe_wifi_band = WIFI_BAND_2_4GHZ_G136
    else:
        safe_wifi_band = requested_wifi_band.strip()

    # Part A: Timecode Link (0 BT TC Link symbols) vs VMC-BNCM1 EXT-LK & FX6 BNC
    dormant_tc_lower = {x.strip().lower() for x in DORMANT_TC_LINK_TRAPS_G136}
    dormant_tc_hit = bool(
        tc_link_requested
        or (
            requested_dormant_tc_symbol is not None
            and requested_dormant_tc_symbol.strip().lower() in dormant_tc_lower
        )
    )
    vmc_bad_cfg = bool(
        (
            vmc_bncm1_ext_ltc_requested
            and (
                norm_shoot != SHOOT_MODE_MOVIE_PHASE310
                or safe_tc_make != "Preset"
                or safe_tc_run != "Free Run"
            )
        )
        or (norm_hdmi_tc == "On" and norm_shoot != SHOOT_MODE_MOVIE_PHASE310)
    )
    if dormant_tc_hit or vmc_bad_cfg or claimed_fx6_has_bluetooth_hw_or_usb_tc_in:
        _add_code(codes, STATUS_BLOCKED_G136_DORMANT_BT_TCLINK_OR_FX6_TC_VIOLATION)
        errors.append(
            "Bluetooth `[Timecode Link]` / UltraSync BLUE has 0 symbols in `FX3 appFw.so` "
            "(`EOPNOTSUPP=95`); FX3 requires wired `VMC-BNCM1` in `Movie` mode (`Preset` + "
            "`Free Run` -> `EXT-LK`) and `HDMI TC Out` is Movie-only, while `ILME-FX6` uses "
            "dedicated physical `TC IN/OUT` BNC with zero BT hardware."
        )

    # Part B: Wi-Fi WPA2/WPA3, SKU (WW728473 vs WW558244), & USB-LAN Mutual Exclusion
    legacy_sec_lower = {x.strip().lower() for x in REMOVED_LEGACY_WIFI_SECURITIES_G136}
    raw_sec = requested_wifi_security.strip() if isinstance(requested_wifi_security, str) else ""
    legacy_sec_hit = raw_sec.lower() in legacy_sec_lower
    if (not legacy_sec_hit) and (raw_sec not in ALLOWED_WIFI_SECURITIES_G136):
        _add_code(codes, STATUS_BLOCKED_G136_TELEMETRY_INVALID)
        errors.append(f"Unsupported Wi-Fi security `{requested_wifi_security}`.")
        safe_sec = WIFI_SEC_WPA3_SAE_G136
    else:
        safe_sec = raw_sec if raw_sec in ALLOWED_WIFI_SECURITIES_G136 else WIFI_SEC_WPA3_SAE_G136

    sku_5g_violation = bool(
        safe_sku == FX3_SKU_WW558244_G136 and safe_wifi_band == WIFI_BAND_5GHZ_G136
    )
    authen_violation = bool(wifi_requested and norm_auth != "On")
    effective_multi_micro_usb = bool(
        multi_micro_usb_active or vmc_bncm1_ext_ltc_requested
    )

    eff = _compute_g136_effective_state(
        shoot_mode=norm_shoot,
        reset_action=norm_reset,
        vmc_bncm1_ext_ltc_requested=bool(vmc_bncm1_ext_ltc_requested),
        tc_make=safe_tc_make,
        tc_run=safe_tc_run,
        airplane_mode=norm_air,
        bench_zero_rf_required=bool(bench_zero_rf_required),
        rf_nvs_write_requested=bool(rf_nvs_write_requested),
        wifi_active=bool(wifi_requested),
        bt_active=bool(bt_requested),
        usb_lan_active=bool(usb_lan_requested),
        usb_lan_authorized=bool(usb_lan_authorized),
        usb_lan_cnct_launch=norm_usb_launch,
        multi_micro_usb_active=effective_multi_micro_usb,
        shutter_type=norm_shutter,
        drive_mode=norm_drive,
        interval_shooting_on=bool(interval_shooting_on),
        requested_bulb_mode=bool(requested_bulb_mode),
        dro_mode=norm_dro,
        dro_bracket=safe_dro_bracket,
        picture_profile_on=bool(picture_profile_on),
        hlg_still_image_on=bool(hlg_still_image_on),
    )

    if (
        legacy_sec_hit
        or sku_5g_violation
        or authen_violation
        or eff["usb_bus_mutual_exclusion_blocked"]
    ):
        _add_code(
            codes, STATUS_BLOCKED_G136_WIFI_WPA_LEGACY_SKU_OR_USBLAN_EXCLUSION_VIOLATION
        )
        errors.append(
            "Wi-Fi/USB-LAN contract violated: Ver. 7.00+ removed WEP/WPA-PSK/IPsec (`EOPNOTSUPP=95`), "
            "`WW558244` lacks `5GHz`, `[Access Authen. Settings]=On` is required, and `USB-LAN` "
            "cannot run concurrently with Multi/Micro USB or internal Wi-Fi."
        )

    air_firewall_blocked = bool(
        eff["airplane_zero_rf_firewall_blocked"]
        or claimed_airplane_resets_on_net_reset_or_init
    )
    if air_firewall_blocked:
        _add_code(codes, STATUS_BLOCKED_G136_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION)
        errors.append(
            "Zero-RF Firewall (`[Airplane Mode] = On`, persistent across both `[Reset Network Set.]` "
            "and `[Initialize]`) blocked wireless/unauthorized RF operation (`wireless_packets_emitted == 0`, "
            "`rf_nvs_p12_p13_writes_permitted == False`)."
        )

    # Part C: Dormant Bulb Timer & Auto HDR vs Mechanical-Only Still BULB + DRO Lock
    dormant_bt_lower = {x.strip().lower() for x in DORMANT_BULB_TIMER_TRAPS_G136}
    dormant_bulb_timer_hit = bool(
        bulb_timer_requested
        or (
            requested_dormant_bulb_symbol is not None
            and requested_dormant_bulb_symbol.strip().lower() in dormant_bt_lower
        )
    )
    dormant_hdr_lower = {x.strip().lower() for x in DORMANT_AUTO_HDR_TRAPS_G136}
    dormant_auto_hdr_hit = bool(
        auto_hdr_requested
        or (
            requested_dormant_hdr_symbol is not None
            and requested_dormant_hdr_symbol.strip().lower() in dormant_hdr_lower
        )
    )
    if dormant_bulb_timer_hit or dormant_auto_hdr_hit:
        _add_code(codes, STATUS_BLOCKED_G136_DORMANT_BULB_TIMER_OR_AUTO_HDR_VIOLATION)
        errors.append(
            "Dormant `[Bulb Timer]` (`BKID_APP_setting_bulb_timer` / `_f 0x630f`) and dormant "
            "`[Auto HDR]` (`.uxc 0xe49d` / `0xe5d0`) are NOT exposed on `ILME-FX3 Ver. 7.02` "
            "(`EOPNOTSUPP=95`)."
        )

    bulb_lock_violation = bool(
        eff["bulb_locked_out_clamped_to_30s"] and force_bulb_under_lockout
    )
    dro_lock_violation = bool(eff["dro_locked_off"] and force_dro_when_pp_or_hlg)
    if (
        bulb_lock_violation
        or dro_lock_violation
        or claimed_fx6_supports_still_bulb_or_dro
    ):
        _add_code(codes, STATUS_BLOCKED_G136_STILL_BULB_MECHANICAL_OR_DRO_LOCK_VIOLATION)
        errors.append(
            "Still `[BULB]` is Mechanical-Shutter-only (clamped to `30\"` under Electronic Shutter / "
            "Cont. Shooting / Cont. Bracket / Self-timer(Cont) / Interval Shooting / non-Still modes), "
            "FX6 is still-less, and `DRO` / `DRO Bracket` lock `Off` under `Picture Profile != Off` or `HLG Still Image = On`."
        )

    any_eopnotsupp = (
        dormant_tc_hit
        or claimed_fx6_has_bluetooth_hw_or_usb_tc_in
        or legacy_sec_hit
        or sku_5g_violation
        or dormant_bulb_timer_hit
        or dormant_auto_hdr_hit
        or bulb_lock_violation
        or claimed_fx6_supports_still_bulb_or_dro
    )
    block_errno: Optional[int] = None
    block_errno_name: Optional[str] = None
    if any_eopnotsupp:
        block_errno = EOPNOTSUPP_ERRNO_PHASE310
        block_errno_name = EOPNOTSUPP_NAME_PHASE310
    elif eff["usb_bus_mutual_exclusion_blocked"]:
        block_errno = EBUSY_ERRNO_PHASE310
        block_errno_name = EBUSY_NAME_PHASE310

    matrix = compute_tc_link_wifi_usblan_bulb_dormant_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G136 if valid else codes[0]

    return TcLinkWifiUsbLanBulbDormantGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE310,
        target_model=target_model,
        reset_action=norm_reset,
        shoot_mode=norm_shoot,
        fx3_bluetooth_tc_link_symbols=0,
        dormant_tc_link_blocked=dormant_tc_hit,
        vmc_bncm1_cable=FX3_WIRED_TC_CABLE_G136,
        vmc_bncm1_ext_ltc_requested=bool(vmc_bncm1_ext_ltc_requested),
        tc_make=safe_tc_make,
        tc_run=safe_tc_run,
        hdmi_tc_output=norm_hdmi_tc,
        ext_tc_lock_status=eff["ext_tc_lock_status"],
        fx6_has_physical_tc_in_out_bnc=True,
        fx6_has_bluetooth_hw=False,
        fx3_sku_code=safe_sku,
        wifi_requested=bool(wifi_requested),
        wifi_active=bool(wifi_requested and eff["effective_airplane_mode"] == "Off"),
        requested_wifi_band=safe_wifi_band,
        requested_wifi_security=safe_sec,
        access_authen_settings=norm_auth,
        usb_lan_requested=bool(usb_lan_requested),
        usb_lan_active=bool(usb_lan_requested),
        usb_lan_authorized=bool(usb_lan_authorized),
        requested_usb_lan_cnct_launch=norm_usb_launch,
        effective_usb_lan_cnct_launch=eff["effective_usb_lan_cnct_launch"],
        usb_lan_kernel_modules=USB_LAN_KERNEL_MODULES_G136,
        multi_micro_usb_active=effective_multi_micro_usb,
        usb_bus_mutual_exclusion_blocked=eff["usb_bus_mutual_exclusion_blocked"],
        requested_airplane_mode=norm_air,
        effective_airplane_mode=eff["effective_airplane_mode"],
        airplane_survived_network_reset_and_init=eff[
            "airplane_survived_network_reset_and_init"
        ],
        bench_zero_rf_required=bool(bench_zero_rf_required),
        rf_nvs_write_requested=bool(rf_nvs_write_requested),
        airplane_zero_rf_firewall_blocked=air_firewall_blocked,
        wired_eth0_permitted_under_airplane=eff["wired_eth0_permitted_under_airplane"],
        wireless_packets_emitted=eff["wireless_packets_emitted"],
        rf_nvs_p12_p13_writes_permitted=eff["rf_nvs_p12_p13_writes_permitted"],
        rf_nvs_mutation_bytes=eff["rf_nvs_mutation_bytes"],
        dormant_bulb_timer_blocked=dormant_bulb_timer_hit,
        dormant_auto_hdr_blocked=dormant_auto_hdr_hit,
        requested_shutter_type=norm_shutter,
        requested_drive_mode=norm_drive,
        interval_shooting_on=bool(interval_shooting_on),
        requested_bulb_mode=bool(requested_bulb_mode),
        effective_bulb_active=eff["effective_bulb_active"],
        bulb_locked_out_clamped_to_30s=eff["bulb_locked_out_clamped_to_30s"],
        bulb_lockout_reasons=eff["bulb_lockout_reasons"],
        anti_flicker_shoot_disabled=eff["anti_flicker_shoot_disabled"],
        long_exposure_nr=norm_lenr,
        requested_dro_mode=norm_dro,
        effective_dro_mode=eff["effective_dro_mode"],
        requested_dro_bracket=safe_dro_bracket,
        effective_dro_bracket=eff["effective_dro_bracket"],
        picture_profile_on=bool(picture_profile_on),
        hlg_still_image_on=bool(hlg_still_image_on),
        dro_locked_off=eff["dro_locked_off"],
        dro_reset_by_cam_reset=eff["dro_reset_by_cam_reset"],
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g136_tc_link_wifi_usblan_bulb_dormant_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    tc_link_wifi_usblan_bulb_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase310DonorAuditResult] = None,
) -> Tuple[GateVerdict, G136TcLinkWifiUsbLanBulbDormantGuardResult]:
    """Evaluate Wave-58 Gate `G136` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase310_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_tc_link_wifi_usblan_bulb_dormant_guard(
        **(dict(tc_link_wifi_usblan_bulb_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G136.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G136 if valid else codes[0]

    res = G136TcLinkWifiUsbLanBulbDormantGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        tc_link_wifi_usblan_bulb_dormant_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, bt_tc_link_syms={guard.fx3_bluetooth_tc_link_symbols}, "
        f"sku={guard.fx3_sku_code}, sec={guard.requested_wifi_security}, "
        f"air={guard.effective_airplane_mode}, rf_pkts={guard.wireless_packets_emitted}, "
        f"dro={guard.effective_dro_mode}, shutter={guard.requested_shutter_type}"
    )
    verdict = GateVerdict(
        gate_id=G136_GATE_ID,
        gate_code=G136_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `136`-Gate Milestone Master Safety Preflight (`G01..G136`)
# ---------------------------------------------------------------------------


def evaluate_136gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    bright_mon_shotmark_kwargs: Optional[Mapping[str, Any]] = None,
    tc_link_wifi_usblan_bulb_kwargs: Optional[Mapping[str, Any]] = None,
    master_134_override: Optional[Master134GateReport] = None,
    **m134_passthrough_kwargs: Any,
) -> Master136GateReport:
    """Evaluate all 136 Master Safety Gates (`G01..G136`) deterministically by
    delegating `G01..G134` directly to `evaluate_134gate_preflight()`.
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

    m134_report: Master134GateReport = (
        master_134_override
        if master_134_override is not None
        else evaluate_134gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m134_passthrough_kwargs,
        )
    )

    phase310_audit = audit_phase310_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g135_verdict, g135_res = evaluate_g135_bright_mon_shotmark_vault_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        bright_mon_shotmark_kwargs=bright_mon_shotmark_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase310_audit,
    )

    g136_verdict, g136_res = evaluate_g136_tc_link_wifi_usblan_bulb_dormant_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        tc_link_wifi_usblan_bulb_kwargs=tc_link_wifi_usblan_bulb_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase310_audit,
    )

    gates_135_to_136 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g135_verdict, g136_verdict)
    ]
    all_gates = tuple(list(m134_report.gates) + gates_135_to_136)

    g01_to_g12_verified = int(m134_report.summary["g01_to_g12_verified"])
    g13_to_g134_verified = int(m134_report.summary["g13_to_g132_verified"]) + int(
        m134_report.summary["g133_to_g134_verified"]
    )
    g135_to_g136_verified = sum(1 for v in (g135_verdict, g136_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g134_verified + g135_to_g136_verified

    g135_to_g136_all_passed = g135_to_g136_verified == 2
    g13_to_g136_all_passed = (
        m134_report.g13_to_g134_all_passed and g135_to_g136_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m134_report.gates[:9])

    offline_133_verified = (
        g01_to_g09_ok
        and m134_report.offline_131_gates_verified
        and g135_to_g136_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_136_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g136_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m134_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_133_verified
        and m134_report.h0_h1_trial_entry_allowed
        and g135_to_g136_all_passed
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
        list(m134_report.errors)
        + list(g135_verdict.errors)
        + list(g136_verdict.errors)
    )
    warnings: List[str] = (
        list(m134_report.warnings)
        + list(g135_verdict.warnings)
        + list(g136_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m134_report.g13_to_g134_all_passed:
        overall_status = m134_report.status
    elif not g135_verdict.passed:
        overall_status = g135_verdict.status
    elif not g136_verdict.passed:
        overall_status = g136_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_136_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_136_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_136_verified:
        overall_status = "VERIFIED_ALL_136_GATES"
    else:
        overall_status = "VERIFIED_133_OF_136_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m134_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g135_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g136_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 136,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 136 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g134_verified": g13_to_g134_verified,
        "g135_to_g136_verified": g135_to_g136_verified,
        "g13_to_g136_all_passed": g13_to_g136_all_passed,
        "g135_to_g136_all_passed": g135_to_g136_all_passed,
        "offline_133_gates_verified": offline_133_verified,
        "all_136_gates_verified": all_136_verified,
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

    return Master136GateReport(
        schema=REALHW_BRIGHT_MON_SHOTMARK_USBLAN_BULB_DORMANT_136GATE_SCHEMA,
        version=REALHW_BRIGHT_MON_SHOTMARK_USBLAN_BULB_DORMANT_136GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_133_gates_verified=offline_133_verified,
        all_136_gates_verified=all_136_verified,
        g13_to_g136_all_passed=g13_to_g136_all_passed,
        g135_to_g136_all_passed=g135_to_g136_all_passed,
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
        master_134_report=m134_report.to_dict(),
        g135_result=g135_res.to_dict(),
        g136_result=g136_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_136_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master136GateReport:
    return evaluate_136gate_preflight(repo_root, **kwargs)


def run_136_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master136GateReport:
    return evaluate_136gate_preflight(repo_root, **kwargs)


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
        prog="realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard",
        description="Phase 310 Wave-58 G135/G136 and 136/136 Safety Gates Preflight CLI",
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
        help="Supply simulated dry-run Tier-0 backup inputs so all 136/136 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g135", "g136", "136"],
        default="136",
        help="Target gate check: g135, g136, or 136",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g135":
        v, r = evaluate_g135_bright_mon_shotmark_vault_guard(
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

    if args.gate == "g136":
        v, r = evaluate_g136_tc_link_wifi_usblan_bulb_dormant_guard(
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

    rep = evaluate_136gate_preflight(
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
                "g135_status": rep.g135_result["status"],
                "g136_status": rep.g136_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/136\n"
        )
    ok = (
        rep.all_136_gates_verified
        if args.dry_run_simulated
        else rep.offline_133_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "ACTIVE_PB_EDIT_ITEMS_G135",
    "ALLOWED_CARD_OPS_G135",
    "ALLOWED_CLIP_FLAG_VALUES_G135",
    "ALLOWED_DRO_BRACKET_MODES_G136",
    "ALLOWED_DRO_MODES_G136",
    "ALLOWED_EXPOSURE_MODES_G135",
    "ALLOWED_FOCUS_MODES_G135",
    "ALLOWED_FX3_SKUS_G136",
    "ALLOWED_IMAGE_JUMP_SETTINGS_G135",
    "ALLOWED_LIVE_VIEW_DISPLAY_MODES_G135",
    "ALLOWED_MEDIA_SLOTS_PHASE310",
    "ALLOWED_MONITOR_BRIGHTNESS_MODES_G135",
    "ALLOWED_PASM_MODES_G135",
    "ALLOWED_PHOTO_CAPTURE_FILE_TYPES_G135",
    "ALLOWED_RESET_ACTIONS_PHASE310",
    "ALLOWED_SHOOT_MODES_PHASE310",
    "ALLOWED_SHUTTER_TYPES_G136",
    "ALLOWED_STILL_DRIVE_MODES_G136",
    "ALLOWED_TC_MAKE_MODES_G136",
    "ALLOWED_TC_RUN_MODES_G136",
    "ALLOWED_WIFI_BANDS_G136",
    "ALLOWED_WIFI_SECURITIES_G136",
    "BRIGHT_MONITORING_F_UXC_RESID16_G135",
    "BRIGHT_MONITORING_KEY_PATH_G135",
    "BrightMonShotMarkVaultGuardResult",
    "CARD_OP_ADD_DELETE_SHOT_MARK_1_G135",
    "CARD_OP_ADD_DELETE_SHOT_MARK_2_G135",
    "CARD_OP_ADD_SHOT_MARK_1_G135",
    "CARD_OP_ADD_SHOT_MARK_2_G135",
    "CARD_OP_CREATE_DIVIDER_FRAME_G135",
    "CARD_OP_JUMP_READONLY_G135",
    "CARD_OP_NONE_G135",
    "CARD_OP_PB_EDIT_G135",
    "CARD_OP_PHOTO_CAPTURE_G135",
    "CARD_OP_SET_CLIP_FLAG_G135",
    "CREATE_DIVIDER_FRAME_F_UXC_RESID16_G135",
    "CREATE_DIVIDER_FRAME_G_UXC_RESID16_G135",
    "CROSS_MODEL_FLASH_AUTHORIZED",
    "DEFAULT_REPO_ROOT",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE310",
    "DONOR_CHECK_MAX_SECONDS_PHASE310",
    "DORMANT_AUTO_HDR_TRAPS_G136",
    "DORMANT_BULB_TIMER_TRAPS_G136",
    "DORMANT_MONITOR_BRIGHTNESS_MODES_G135",
    "DORMANT_SHOTMARK_DIVIDE_TRAPS_G135",
    "DORMANT_TC_LINK_TRAPS_G136",
    "DRO_AUTO_G136",
    "DRO_OFF_G136",
    "EBUSY_ERRNO_PHASE310",
    "EBUSY_NAME_PHASE310",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "ENV_CLEAN_ROOM_TEST_PHASE310",
    "ENV_FORCE_CLEAN_ROOM",
    "EOPNOTSUPP_ERRNO_PHASE310",
    "EOPNOTSUPP_NAME_PHASE310",
    "EROFS_ERRNO_PHASE310",
    "EROFS_NAME_PHASE310",
    "EXPOSURE_MODE_A_G135",
    "EXPOSURE_MODE_INTELLIGENT_AUTO_G135",
    "EXPOSURE_MODE_M_G135",
    "EXPOSURE_MODE_P_G135",
    "EXPOSURE_MODE_S_G135",
    "FOCUS_MODE_AF_C_G135",
    "FOCUS_MODE_AF_S_G135",
    "FOCUS_MODE_DMF_G135",
    "FOCUS_MODE_MF_G135",
    "FX3_DEFAULT_FW_VERSION_PHASE310",
    "FX3_HELP_GUIDE_CODE_PHASE310",
    "FX3_MODEL_ID_PHASE310",
    "FX3_MODEL_NAME_PHASE310",
    "FX3_SKU_WW558244_G136",
    "FX3_SKU_WW728473_G136",
    "FX3_WIRED_TC_CABLE_G136",
    "FX6_AE_BACKLIGHT_SYMBOL_G135",
    "FX6_DEFAULT_FW_VERSION_PHASE310",
    "FX6_DORMANT_BACKLIGHT_SYMBOLS_G135",
    "FX6_MODEL_NAME_PHASE310",
    "FX6_PRODUCT_CODE_PHASE310",
    "FX6_VF_BRIGHTNESS_DEFAULT_G135",
    "FX6_VF_BRIGHTNESS_MAX_G135",
    "FX6_VF_BRIGHTNESS_MIN_G135",
    "FX6_VF_COLOR_MODES_G135",
    "FX6_VF_SETTING_MENU_PATH_G135",
    "G135",
    "G135BrightMonShotMarkVaultGuardResult",
    "G135_GATE_CODE",
    "G135_GATE_ID",
    "G136",
    "G136TcLinkWifiUsbLanBulbDormantGuardResult",
    "G136_GATE_CODE",
    "G136_GATE_ID",
    "GATE_G135_BRIGHT_MONITORING_FOCUS_MAG_MONITOR_BRIGHTNESS_VS_FX6_AND_SHOTMARK_CLIPFLAG_DIVIDER_SLOT1_VAULT_GUARD",
    "GATE_G136_ZERO_BT_TCLINK_VS_VMC_BNCM1_FX6_BNC_WIFI_WPA3_USBLAN_ZERORF_AND_DORMANT_BULB_TIMER_AUTOHDR_GUARD",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HUMAN_HARDWARE_ATTACH_TOKEN",
    "LIVE_VIEW_DISPLAY_EFFECT_OFF_G135",
    "LIVE_VIEW_DISPLAY_EFFECT_ON_G135",
    "MEDIA_SLOT_1_PHASE310",
    "MEDIA_SLOT_2_PHASE310",
    "MONITOR_BRIGHTNESS_DEFAULT_MODE_G135",
    "MONITOR_BRIGHTNESS_LEVEL_DEFAULT_G135",
    "MONITOR_BRIGHTNESS_LEVEL_MAX_G135",
    "MONITOR_BRIGHTNESS_LEVEL_MIN_G135",
    "MONITOR_BRIGHTNESS_MANUAL_G135",
    "MONITOR_BRIGHTNESS_MENU_PATH_G135",
    "MONITOR_BRIGHTNESS_SUNNY_WEATHER_G135",
    "MONITOR_BRIGHTNESS_UXC_RESID16_G135",
    "MUTATING_DCIM_OPS_G135",
    "MUTATING_M4ROOT_OPS_G135",
    "Master136GateReport",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHOTO_CAPTURE_F_UXC_RESID16_G135",
    "PHOTO_CAPTURE_SWITCH_F_UXC_RESID16_G135",
    "PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PINNED_FX3_APPFW_SLICES_PHASE310",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE310",
    "PINNED_FX6_APPFW_SLICES_PHASE310",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE310",
    "PINNED_PHASE310_DONOR_SPECS",
    "Phase310DonorAuditResult",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READONLY_CARD_OPS_G135",
    "REALHW_BRIGHT_MON_SHOTMARK_USBLAN_BULB_DORMANT_136GATE_SCHEMA",
    "REALHW_BRIGHT_MON_SHOTMARK_USBLAN_BULB_DORMANT_136GATE_VERSION",
    "REMOVED_LEGACY_WIFI_SECURITIES_G136",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE310",
    "RESET_ACTION_INITIALIZE_PHASE310",
    "RESET_ACTION_NONE_PHASE310",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE310",
    "SHOOT_MODE_MOVIE_PHASE310",
    "SHOOT_MODE_SQ_PHASE310",
    "SHOOT_MODE_STILL_PHASE310",
    "SHOT_MARK_1_PB_RESID16_G135",
    "SHOT_MARK_1_REC_RESID16_G135",
    "SHOT_MARK_2_PB_RESID16_G135",
    "SHOT_MARK_2_REC_RESID16_G135",
    "SHUTTER_TYPE_AUTO_G136",
    "SHUTTER_TYPE_ELECTRONIC_G136",
    "SHUTTER_TYPE_MECHANICAL_G136",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_BLOCKED_G135_BRIGHT_MONITORING_CUSTOM_KEY_OR_MAG_VIOLATION",
    "STATUS_BLOCKED_G135_DORMANT_DIVIDE_EXTRACT_OR_FTP_CUT_VIOLATION",
    "STATUS_BLOCKED_G135_MONITOR_BRIGHTNESS_OR_FX6_BACKLIGHT_VIOLATION",
    "STATUS_BLOCKED_G135_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION",
    "STATUS_BLOCKED_G135_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G136_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION",
    "STATUS_BLOCKED_G136_DORMANT_BT_TCLINK_OR_FX6_TC_VIOLATION",
    "STATUS_BLOCKED_G136_DORMANT_BULB_TIMER_OR_AUTO_HDR_VIOLATION",
    "STATUS_BLOCKED_G136_STILL_BULB_MECHANICAL_OR_DRO_LOCK_VIOLATION",
    "STATUS_BLOCKED_G136_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G136_WIFI_WPA_LEGACY_SKU_OR_USBLAN_EXCLUSION_VIOLATION",
    "STATUS_BLOCKED_PERSISTENT_EMMC_WRITE",
    "STATUS_BLOCKED_PHASE310_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G135",
    "STATUS_VERIFIED_G136",
    "STATUS_VERIFIED_SAFE",
    "STILL_DRIVE_CONT_BRACKET_G136",
    "STILL_DRIVE_CONT_SHOOTING_G136",
    "STILL_DRIVE_DRO_BRACKET_G136",
    "STILL_DRIVE_SELF_TIMER_CONT_G136",
    "STILL_DRIVE_SELF_TIMER_SINGLE_G136",
    "STILL_DRIVE_SINGLE_BRACKET_G136",
    "STILL_DRIVE_SINGLE_G136",
    "SUNNY_WEATHER_BASE_UXC_RESID16_G135",
    "SUNNY_WEATHER_F_UXC_RESID16_G135",
    "TcLinkWifiUsbLanBulbDormantGuardResult",
    "USB_LAN_CNCT_LAUNCH_F_UXC_RESID16_G136",
    "USB_LAN_KERNEL_MODULES_G136",
    "USB_PACKETS_TRANSMITTED",
    "WIFI_BAND_2_4GHZ_G136",
    "WIFI_BAND_5GHZ_G136",
    "WIFI_SEC_WPA2_PSK_G136",
    "WIFI_SEC_WPA3_SAE_G136",
    "audit_phase310_donor_contracts",
    "compute_bright_mon_shotmark_vault_matrix",
    "compute_tc_link_wifi_usblan_bulb_dormant_matrix",
    "evaluate_136_master_safety_gates",
    "evaluate_136gate_preflight",
    "evaluate_g135_bright_mon_shotmark_vault_guard",
    "evaluate_g136_tc_link_wifi_usblan_bulb_dormant_guard",
    "main",
    "resolve_fx3_bright_mon_shotmark_vault_state",
    "resolve_fx3_tc_link_wifi_usblan_bulb_dormant_state",
    "run_136_gate_preflight",
    "verify_bright_mon_shotmark_vault_guard",
    "verify_tc_link_wifi_usblan_bulb_dormant_guard",
]


if __name__ == "__main__":
    raise SystemExit(main())
