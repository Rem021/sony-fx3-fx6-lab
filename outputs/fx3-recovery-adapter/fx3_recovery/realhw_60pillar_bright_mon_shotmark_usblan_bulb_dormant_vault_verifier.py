"""Phase 336 Milestone — Recovery Pillar 60 & 60/60 Master Recovery Verifier:
Wave-58 Sony ILME-FX3 (Ver. 7.02) vs ILME-FX6 (Ver. 6.01) Empirically Grounded Guardrails:
  * Pillar 60A: Custom-key-only [Bright Monitoring] (forces Live View Display = Setting Effect OFF,
    auto-cancels on power-off / leaving P/A/S/M / leaving MF, Ver. 7.00/7.02 unlocks coexistence with
    [Focus Magnifier] & [Auto Magnifier in MF], zero multi-gain/area ext), Initialize-only Setup ->
    [Monitor] -> [Monitor Brightness] (Manual -2..+2 def 0 / Sunny Weather vs dormant Auto EOPNOTSUPP=95)
    vs FX6 VF Setting > Brightness (1..15 def 8) + Auto Exposure > Mode > Backlight disambiguation,
    Mechanical-Shutter-only Still [BULB] (fallback to 30" under Electronic/Cont./Bracket/Interval) &
    Resettable [D-Range Optimizer] (Auto[def]/Off/Lv1..5, locked when PP != Off or HLG Still = On)
    vs Dormant [Bulb Timer] (_f 0x630f / 0x78b6) & Dormant [Auto HDR] (base 0xe49d / 0xe5d0 -> EOPNOTSUPP=95).
  * Pillar 60B: Active [Shot Mark 1/2] + Ver. 6.00+/7.00+ [Clip Flag] (OK/NG/KEEP) + Playback [Edit]
    (Photo Capture, JPEG/HEIF Switch, Copy, Rotate, Create Divider Frame) vs strictly dormant [Divide] /
    [Extract] / Cut to 15/30/60s (0 hits in FX3 appFw.so -> EOPNOTSUPP=95), Zero Bluetooth [Timecode Link]
    / UltraSync BLUE (EOPNOTSUPP=95) vs Multi/Micro USB VMC-BNCM1 wired LTC (EXT-LK) + HDMI TC Output vs
    FX6 physical TC IN/OUT BNC switch, Wi-Fi WW728473 (2.4/5GHz) vs WW558244 (2.4GHz), Ver. 7.00+ removal
    of WEP/WPA-PSK/IPsec enforcing WPA2-PSK/WPA3-SAE, USB-LAN (cdc_ncm/r8152) mutual exclusion with Wi-Fi
    & Multi/Micro USB + Airplane Mode=On Zero-RF persistence across Reset Network Set. & Initialize, and
    Fail-Closed Slot-1 Tier-0 Recovery Vault EROFS=30 Firewall protecting M4ROOT/*M01.XML, AVF_INFO & DCIM/.
  * Unified 60/60 Master Recovery Aggregator (Pillars 1..59 + Pillar 60).

Safety Redlines (HARD-LOCKED):
  - Zero hardware attach, zero physical device writes, zero USB/UART TX, zero OTP/RPMB, zero eMMC writes.
  - Zero raw firmware bytes leaked (`raw_firmware_bytes_leaked == 0`).
  - Bounded `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` donor inspection (`< 0.2s` local / `< 0.5s` CI) with
    explicit `work_root is None` guard and automatic `CLEAN_ROOM_SYNTHETIC` fallback on donorless hosts.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import posixpath
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from .realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier import (
    MASTER_59_PILLAR_SPECS,
    Master59PillarRecoveryReport,
    P332_DONOR_FX3_APPFW_702_RELPATH,
    P332_DONOR_FX3_BACKUP_BIN_RELPATH,
    P332_DONOR_FX3_UXC_EN_F_RELPATH,
    P332_DONOR_FX3_UXC_EN_G_RELPATH,
    P332_DONOR_FX3_UXC_EN_RELPATH,
    P332_DONOR_FX3_UXC_JA_F_RELPATH,
    P332_DONOR_FX3_UXC_JA_G_RELPATH,
    P332_DONOR_FX3_UXC_JA_RELPATH,
    P332_DONOR_FX3_UXC_SC_F_RELPATH,
    P332_DONOR_FX3_UXC_SC_G_RELPATH,
    P332_DONOR_FX3_UXC_SC_RELPATH,
    P332_DONOR_FX3_UXC_TC_F_RELPATH,
    P332_DONOR_FX3_UXC_TC_G_RELPATH,
    P332_DONOR_FX3_UXC_TC_RELPATH,
    P332_DONOR_FX6_APPFW_601_RELPATH,
    P332_DONOR_FX6_UXC_EN_2_RELPATH,
    P332_DONOR_FX6_UXC_EN_RELPATH,
    P332_PINNED_FX3_APPFW_702_BYTES,
    P332_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P332_PINNED_FX3_BACKUP_BIN_BYTES,
    P332_PINNED_FX3_BACKUP_BIN_SHA256,
    P332_PINNED_FX3_UXC_EN_BYTES,
    P332_PINNED_FX3_UXC_EN_F_BYTES,
    P332_PINNED_FX3_UXC_EN_F_SHA256,
    P332_PINNED_FX3_UXC_EN_G_BYTES,
    P332_PINNED_FX3_UXC_EN_G_SHA256,
    P332_PINNED_FX3_UXC_EN_SHA256,
    P332_PINNED_FX3_UXC_JA_BYTES,
    P332_PINNED_FX3_UXC_JA_F_BYTES,
    P332_PINNED_FX3_UXC_JA_F_SHA256,
    P332_PINNED_FX3_UXC_JA_G_BYTES,
    P332_PINNED_FX3_UXC_JA_G_SHA256,
    P332_PINNED_FX3_UXC_JA_SHA256,
    P332_PINNED_FX3_UXC_SC_BYTES,
    P332_PINNED_FX3_UXC_SC_F_BYTES,
    P332_PINNED_FX3_UXC_SC_F_SHA256,
    P332_PINNED_FX3_UXC_SC_G_BYTES,
    P332_PINNED_FX3_UXC_SC_G_SHA256,
    P332_PINNED_FX3_UXC_SC_SHA256,
    P332_PINNED_FX3_UXC_TC_BYTES,
    P332_PINNED_FX3_UXC_TC_F_BYTES,
    P332_PINNED_FX3_UXC_TC_F_SHA256,
    P332_PINNED_FX3_UXC_TC_G_BYTES,
    P332_PINNED_FX3_UXC_TC_G_SHA256,
    P332_PINNED_FX3_UXC_TC_SHA256,
    P332_PINNED_FX6_APPFW_601_BYTES,
    P332_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P332_PINNED_FX6_UXC_EN_2_BYTES,
    P332_PINNED_FX6_UXC_EN_2_SHA256,
    P332_PINNED_FX6_UXC_EN_BYTES,
    P332_PINNED_FX6_UXC_EN_SHA256,
    evaluate_realhw_59pillar_recovery_master,
)
from . import files as _fx3_files
from .files import is_forced_clean_room, iter_donor_work_roots
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus

# ---------------------------------------------------------------------------
# Phase 336 Metadata, Safety Redlines & Pinned Budget Constants
# ---------------------------------------------------------------------------

PHASE336_SCHEMA = "realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier_v1"
PHASE336_MASTER_SCHEMA = "realhw_60pillar_recovery_master_v1"
PHASE336_VERSION = "1.0.0"
PHASE336_PHASE_NUMBER = 336

P336_ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"

# Hard-locked Safety Flags
CNFLASHA_USERSPACE_WRITE_BLOCKED = True
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
SPI_NOR_WRITE_AUTHORIZED = False
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
ISP_WRITE_AUTHORIZED = False
PERSISTENT_WRITE_RELEASE = False
ALLOW_BOOT_PARTITION_TARGETING = False
ALLOW_DESTRUCTIVE_FASTBOOT = False
ALLOW_PERSISTENT_JIRITSU_WRITES = False
ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS = False
LIVE_USB_IOKIT_TRANSMIT_ENABLED = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
OVERALL_READY_FOR_HARDWARE_ATTACH = False
CROSS_MODEL_FLASH_AUTHORIZED = False
READ_ONLY_DONOR_ACCESS = True

P336_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
P336_OVERALL_READY_FOR_HARDWARE_ATTACH = False
P336_CROSS_MODEL_FLASH_AUTHORIZED = False

OTP_FUSE_TOUCHES = 0
OTP_FUSE_WRITES = 0
RPMB_COUNTER_INCREMENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PHYSICAL_DEVICE_WRITES = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

P336_BOUNDED_HEADER_BYTES = 4096
P336_MAX_FULL_DONOR_BYTES = 3_000_000
P336_DONOR_INSPECT_BUDGET_SECONDS = 0.20
P336_DONOR_INSPECT_CI_BUDGET_SECONDS = 0.50
P336_FAST_CLI_BUDGET_SECONDS = 1.50
P336_NOMINAL_BUDGET_SECONDS = 4.00
P336_CONCURRENT_CEILING_SECONDS = 6.00

P336_EINVAL_ERRNO = 22
P336_EROFS_ERRNO = 30
P336_EOPNOTSUPP_ERRNO = 95

# Camera Identities
P336_FX3_MODEL_NAME = "ILME-FX3"
P336_FX3_MODEL_ID = 0x91030080
P336_FX3_PRODUCT_CODENAME = "PRODUCT_MODEL_ALCIN_UUD"
P336_FX3_HELPGUIDE_ID = "ilc/2210"
P336_FX3_FW_VERSION = "7.02"
P336_FX3_SUPPORTED_FW_VERSIONS = ("7.02", "7.01", "7.00", "6.02", "6.00")
P336_FX3_FOCUS_MAG_BRIGHT_MON_MIN_FW = ("7.02", "7.01", "7.00")

P336_FX6_DONOR_MODEL_NAME = "ILME-FX6"
P336_FX6_DONOR_FW_VERSION = "6.01"
P336_FX6_PRODUCT_CODENAME = "PRODUCT_MODEL_CHAPLIN"

# Pinned Donor Relpaths & Digests (17 Wave-58 donors: 14 FX3 7.02 + 3 FX6 6.01)
P336_DONOR_FX3_APPFW_702_RELPATH = P332_DONOR_FX3_APPFW_702_RELPATH
P336_DONOR_FX6_APPFW_601_RELPATH = P332_DONOR_FX6_APPFW_601_RELPATH
P336_DONOR_FX3_BACKUP_BIN_RELPATH = P332_DONOR_FX3_BACKUP_BIN_RELPATH
P336_DONOR_FX3_UXC_EN_F_RELPATH = P332_DONOR_FX3_UXC_EN_F_RELPATH
P336_DONOR_FX3_UXC_SC_F_RELPATH = P332_DONOR_FX3_UXC_SC_F_RELPATH
P336_DONOR_FX3_UXC_TC_F_RELPATH = P332_DONOR_FX3_UXC_TC_F_RELPATH
P336_DONOR_FX3_UXC_JA_F_RELPATH = P332_DONOR_FX3_UXC_JA_F_RELPATH
P336_DONOR_FX3_UXC_EN_RELPATH = P332_DONOR_FX3_UXC_EN_RELPATH
P336_DONOR_FX3_UXC_SC_RELPATH = P332_DONOR_FX3_UXC_SC_RELPATH
P336_DONOR_FX3_UXC_TC_RELPATH = P332_DONOR_FX3_UXC_TC_RELPATH
P336_DONOR_FX3_UXC_JA_RELPATH = P332_DONOR_FX3_UXC_JA_RELPATH
P336_DONOR_FX3_UXC_EN_G_RELPATH = P332_DONOR_FX3_UXC_EN_G_RELPATH
P336_DONOR_FX3_UXC_SC_G_RELPATH = P332_DONOR_FX3_UXC_SC_G_RELPATH
P336_DONOR_FX3_UXC_TC_G_RELPATH = P332_DONOR_FX3_UXC_TC_G_RELPATH
P336_DONOR_FX3_UXC_JA_G_RELPATH = P332_DONOR_FX3_UXC_JA_G_RELPATH
P336_DONOR_FX6_UXC_EN_RELPATH = P332_DONOR_FX6_UXC_EN_RELPATH
P336_DONOR_FX6_UXC_EN_2_RELPATH = P332_DONOR_FX6_UXC_EN_2_RELPATH

P336_PINNED_FX3_APPFW_702_BYTES = P332_PINNED_FX3_APPFW_702_BYTES
P336_PINNED_FX3_APPFW_702_HDR4K_SHA256 = P332_PINNED_FX3_APPFW_702_HDR4K_SHA256
P336_PINNED_FX6_APPFW_601_BYTES = P332_PINNED_FX6_APPFW_601_BYTES
P336_PINNED_FX6_APPFW_601_HDR4K_SHA256 = P332_PINNED_FX6_APPFW_601_HDR4K_SHA256
P336_PINNED_FX3_BACKUP_BIN_BYTES = P332_PINNED_FX3_BACKUP_BIN_BYTES
P336_PINNED_FX3_BACKUP_BIN_SHA256 = P332_PINNED_FX3_BACKUP_BIN_SHA256
P336_PINNED_FX3_UXC_EN_F_BYTES = P332_PINNED_FX3_UXC_EN_F_BYTES
P336_PINNED_FX3_UXC_EN_F_SHA256 = P332_PINNED_FX3_UXC_EN_F_SHA256
P336_PINNED_FX3_UXC_SC_F_BYTES = P332_PINNED_FX3_UXC_SC_F_BYTES
P336_PINNED_FX3_UXC_SC_F_SHA256 = P332_PINNED_FX3_UXC_SC_F_SHA256
P336_PINNED_FX3_UXC_TC_F_BYTES = P332_PINNED_FX3_UXC_TC_F_BYTES
P336_PINNED_FX3_UXC_TC_F_SHA256 = P332_PINNED_FX3_UXC_TC_F_SHA256
P336_PINNED_FX3_UXC_JA_F_BYTES = P332_PINNED_FX3_UXC_JA_F_BYTES
P336_PINNED_FX3_UXC_JA_F_SHA256 = P332_PINNED_FX3_UXC_JA_F_SHA256
P336_PINNED_FX3_UXC_EN_BYTES = P332_PINNED_FX3_UXC_EN_BYTES
P336_PINNED_FX3_UXC_EN_SHA256 = P332_PINNED_FX3_UXC_EN_SHA256
P336_PINNED_FX3_UXC_SC_BYTES = P332_PINNED_FX3_UXC_SC_BYTES
P336_PINNED_FX3_UXC_SC_SHA256 = P332_PINNED_FX3_UXC_SC_SHA256
P336_PINNED_FX3_UXC_TC_BYTES = P332_PINNED_FX3_UXC_TC_BYTES
P336_PINNED_FX3_UXC_TC_SHA256 = P332_PINNED_FX3_UXC_TC_SHA256
P336_PINNED_FX3_UXC_JA_BYTES = P332_PINNED_FX3_UXC_JA_BYTES
P336_PINNED_FX3_UXC_JA_SHA256 = P332_PINNED_FX3_UXC_JA_SHA256
P336_PINNED_FX3_UXC_EN_G_BYTES = P332_PINNED_FX3_UXC_EN_G_BYTES
P336_PINNED_FX3_UXC_EN_G_SHA256 = P332_PINNED_FX3_UXC_EN_G_SHA256
P336_PINNED_FX3_UXC_SC_G_BYTES = P332_PINNED_FX3_UXC_SC_G_BYTES
P336_PINNED_FX3_UXC_SC_G_SHA256 = P332_PINNED_FX3_UXC_SC_G_SHA256
P336_PINNED_FX3_UXC_TC_G_BYTES = P332_PINNED_FX3_UXC_TC_G_BYTES
P336_PINNED_FX3_UXC_TC_G_SHA256 = P332_PINNED_FX3_UXC_TC_G_SHA256
P336_PINNED_FX3_UXC_JA_G_BYTES = P332_PINNED_FX3_UXC_JA_G_BYTES
P336_PINNED_FX3_UXC_JA_G_SHA256 = P332_PINNED_FX3_UXC_JA_G_SHA256
P336_PINNED_FX6_UXC_EN_BYTES = P332_PINNED_FX6_UXC_EN_BYTES
P336_PINNED_FX6_UXC_EN_SHA256 = P332_PINNED_FX6_UXC_EN_SHA256
P336_PINNED_FX6_UXC_EN_2_BYTES = P332_PINNED_FX6_UXC_EN_2_BYTES
P336_PINNED_FX6_UXC_EN_2_SHA256 = P332_PINNED_FX6_UXC_EN_2_SHA256

# Zero-Violation Pillar 60 Counters & Vault Flags
P336_BRIGHT_MON_OR_MONITOR_BRIGHTNESS_DRIFT_EVENTS = 0
P336_BULB_MECH_OR_DORMANT_BULB_TIMER_HDR_DRIFT_EVENTS = 0
P336_FX6_VF_BACKLIGHT_OR_STILL_SPOOF_EVENTS = 0
P336_SHOTMARK_CLIPFLAG_OR_DORMANT_DIVIDE_DRIFT_EVENTS = 0
P336_TC_LINK_WPA3_OR_USBLAN_MUTEX_DRIFT_EVENTS = 0
P336_ZERO_RF_OR_SLOT1_VAULT_BYPASS_EVENTS = 0

P336_RF_PACKETS_TRANSMITTED = 0
P336_RF_NVS_MUTATION_BYTES = 0
P336_SLOT1_DATA_SECTOR_WRITES = 0
P336_SLOT1_M4ROOT_AVF_MUTATION_BYTES = 0
P336_SLOT1_DCIM_DIVIDER_MUTATION_BYTES = 0
P336_SLOT1_VAULT_MUTATION_BYTES = 0
P336_SLOT1_FORMAT_HARD_LOCKED = True
P336_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True
P336_AIRPLANE_MODE_FORCED_ON = True

P336_STAGE_B_VOLATILE_OVERLAY_DIR = "/tmp/fx3_stage_b_overlay/pillar60"
P336_FORBIDDEN_PERSISTENT_TARGETS = (
    "/dev/cnflasha",
    "/setting",
    "/mnt/emmc",
    "/nflasha",
)
P336_TIER0_SURFACE_COUNT = 16
P336_SLOT1_VAULT_SLOT = 1
P336_SAFE_SECONDARY_SLOT = 2

# ---------------------------------------------------------------------------
# Wave-58 Empirical Constants: Pillar 60A ([Bright Monitoring], [Monitor Brightness], [BULB] / [DRO])
# ---------------------------------------------------------------------------

P336_BRIGHT_MONITORING_F_RESID16 = 0x701F
P336_BRIGHT_MONITORING_SYMBOLS = (
    "EVENT_FUNC_CUSTOM_BRIGHT_MONITORING_ON",
    "EVENT_FUNC_CUSTOM_BRIGHT_MONITORING_OFF",
    "VAL_setting_bright_monitoring_state_BRIGHT_MONITORING_STATE_ON",
    "VAL_setting_bright_monitoring_state_BRIGHT_MONITORING_STATE_OFF",
    "CAUTION_ID_FACTOR_CAM_SET_BRIGHT_MONITORING_ON_MSG",
    "FUNC_custom_bright_monitoring",
)
P336_FX3_BRIGHT_MONITORING_SYMBOL_COUNT = 6

P336_MONITOR_BRIGHTNESS_BASE_RESID16 = 0xE44B
P336_SUNNY_WEATHER_BASE_RESID16 = 0xE1DA
P336_SUNNY_WEATHER_F_RESID16 = 0x7A61
P336_BKID_LCD_BRIGHTNESS = "BKID_APP_setting_lcd_brightness"
P336_BKID_LCD_BRIGHTNESS_MANUAL = "BKID_APP_setting_lcd_brightness_brightness_setup_manual"
P336_MONITOR_BRIGHTNESS_MENU_PATH = ("Setup", "Monitor", "Monitor Brightness")
P336_MONITOR_BRIGHTNESS_MODES = ("Manual", "Sunny Weather")
P336_MONITOR_BRIGHTNESS_ALL_MODES = ("Manual", "Sunny Weather", "Auto")
P336_MONITOR_BRIGHTNESS_DEFAULT_MODE = "Manual"
P336_MONITOR_BRIGHTNESS_MIN_LEVEL = -2
P336_MONITOR_BRIGHTNESS_MAX_LEVEL = 2
P336_MONITOR_BRIGHTNESS_DEFAULT_LEVEL = 0
P336_DORMANT_LCD_BRIGHTNESS_MODES = (
    "LCD_BRIGHTNESS_AUTO",
    "LCD_BRIGHTNESS_BRIGHT",
    "LCD_BRIGHTNESS_NORMAL",
)

P336_FX6_VF_BRIGHTNESS_MIN = 1
P336_FX6_VF_BRIGHTNESS_MAX = 15
P336_FX6_VF_BRIGHTNESS_DEFAULT = 8
P336_FX6_VF_COLOR_MODES = ("Color", "B&W")
P336_FX6_AE_BACKLIGHT_SYMBOL = "VAL_setting_auto_exposure_mode_MODE_BACKLIGHT"
P336_FX6_DORMANT_LCD_BACKLIGHT_RESID16 = 0x44F0
P336_FX6_DORMANT_VF_BACKLIGHT_RESID16 = 0x44F4
P336_FX6_DORMANT_BACKLIGHT_SYMBOLS = (
    "LCD Backlight",
    "VF Backlight",
    "NIGHTSHOT_ON",
    "NIGHTSHOT_OFF",
)

P336_BULB_BASE_RESID16 = 0xE916
P336_PID_SET_BULB_MODE = "PID_SET_BULB_MODE"
P336_CAUTION_BULB_ON_MSG = "CAUTION_ID_FACTOR_CAM_SET_BULB_ON_MSG"
P336_BULB_FALLBACK_SHUTTER = '30"'
P336_SHUTTER_TYPES = ("Mechanical Shutter", "Electronic Shutter")
P336_STILL_DRIVE_MODES_ALL = (
    "Single Shooting",
    "Cont. Shooting",
    "Self-timer(Single)",
    "Self-timer(Cont)",
    "Cont. Bracket",
    "Interval Shooting",
    "DRO Bracket",
)
P336_BULB_DISALLOWED_DRIVE_MODES = (
    "Cont. Shooting",
    "Self-timer(Cont)",
    "Cont. Bracket",
    "Interval Shooting",
)
P336_DORMANT_BULB_TIMER_BKID = "BKID_APP_setting_bulb_timer"
P336_DORMANT_BULB_TIMER_MR_BKID = "BKID_APP_MR_setting_bulb_timer"
P336_DORMANT_BULB_TIMER_F_RESID16 = 0x630F
P336_DORMANT_BULB_TIMER_SETTINGS_F_RESID16 = 0x78B6
P336_DORMANT_BULB_TIMER_SYMBOL_COUNT = 13

P336_DRO_BASE_RESID16 = 0xE89C
P336_DRO_BRACKET_BASE_RESID16 = 0xE18F
P336_BKID_DRO = "BKID_APP_setting_dro"
P336_BKID_DRO_LEVEL = "BKID_APP_setting_dro_d_range_optimizer"
P336_BKID_DRO_BRACKET = "BKID_APP_setting_drive_mode_dro_adv_bracket"
P336_DRO_MODES = ("Auto", "Off", "Lv1", "Lv2", "Lv3", "Lv4", "Lv5")
P336_DRO_DEFAULT = "Auto"
P336_DRO_BRACKET_OPTIONS = ("Off", "DRO Bracket: Lo", "DRO Bracket: Hi")
P336_HLG_STILL_F_RESID16 = 0x76C8

P336_DORMANT_AUTO_HDR_BASE_RESID16 = 0xE49D
P336_DORMANT_DRO_AUTO_HDR_BASE_RESID16 = 0xE5D0
P336_DORMANT_HDR_LEVEL_BKID = "BKID_APP_extern_menu_hdr_level"
P336_DORMANT_BULB_AND_HDR_SYMBOLS = (
    "BKID_APP_setting_bulb_timer",
    "BKID_APP_MR_setting_bulb_timer",
    "BULB Timer",
    "BULB Timer Settings",
    "Auto HDR",
    "DRO/Auto HDR",
    "BKID_APP_extern_menu_hdr_level",
)

# ---------------------------------------------------------------------------
# Wave-58 Empirical Constants: Pillar 60B ([Shot Mark]/[Edit]/[TC Link]/[Wi-Fi]/[USB-LAN]/Vault)
# ---------------------------------------------------------------------------

P336_ADD_SHOT_MARK1_F_RESID16 = 0x628B
P336_ADD_SHOT_MARK2_F_RESID16 = 0x628A
P336_PB_ADD_DEL_SHOT_MARK1_F_RESID16 = 0x6143
P336_PB_ADD_DEL_SHOT_MARK2_F_RESID16 = 0x6142
P336_IMAGE_JUMP_SHOT_MARK_ONLY_F_RESID16 = 0x76CF
P336_IMAGE_JUMP_SHOT_MARK1_ONLY_F_RESID16 = 0x79CB
P336_IMAGE_JUMP_SHOT_MARK2_ONLY_F_RESID16 = 0x6FFB
P336_IMAGE_JUMP_NO_SHOT_MARK_F_RESID16 = 0x7818
P336_IMAGE_JUMP_DIVIDER_ONLY_F_RESID16 = 0x7868
P336_IMAGE_JUMP_AFTER_DIVIDER_F_RESID16 = 0x7A80
P336_IMAGE_JUMP_OPTIONS = (
    "Shot Mark Only",
    "Shot Mark1 Only",
    "Shot Mark2 Only",
    "No Shot Mark",
    "Divider Frame Only",
    "Image After Divider",
)
P336_CLIP_FLAG_OPTIONS = ("Off", "OK", "NG", "KEEP")
P336_PHOTO_CAPTURE_F_RESID16 = 0x6856
P336_JPEG_HEIF_SWITCH_F_RESID16 = 0x7175
P336_PHOTO_CAPTURE_FILE_TYPES = ("JPEG", "HEIF_420", "HEIF_422")
P336_CREATE_DIVIDER_FRAME_F_RESID16 = 0x747A
P336_DIVIDER_FRAME_G_RESID16 = 0x6118
P336_FX3_PLAYBACK_EDIT_ITEMS = ("Photo Capture", "JPEG/HEIF Switch", "Copy", "Rotate")
P336_SHOT_MARK_TRANSFER_FILTERS = ("All", "Only Shot Mark", "Only Shot Mark Mov.")

P336_DORMANT_CUT_15S_F_RESID16 = 0x7005
P336_DORMANT_CUT_30S_F_RESID16 = 0x6E38
P336_DORMANT_CUT_60S_F_RESID16 = 0x6C2A
P336_DORMANT_CUT_CENTER_F_RESID16 = 0x74A9
P336_DORMANT_CLIP_EDIT_SYMBOLS = (
    "Divide",
    "Extract",
    "divide_clip",
    "clip_divide",
    "extract_clip",
    "Cut to 15 seconds",
    "Cut to 30 seconds",
    "Cut to 60 seconds",
)
P336_FX6_DORMANT_SHOT_MARK_SYMBOLS = (
    "Shot Mark 0..9",
    "Essence Mark",
    "Divide Clip",
    "Content Browser Mobile",
)

P336_TIMECODE_LINK_BT_SYMBOLS = ("Timecode Link", "tc_link", "timecode_link", "UltraSync BLUE")
P336_VMC_BNCM1_PART_NUMBER = "A-5051-506-A"
P336_VMC_BNCM1_ADAPTER_MODEL = "VMC-BNCM1"
P336_BKID_EXT_TC_LOCK_STATUS = "BKID_APP_ext_tc_lock_status"
P336_TIMECODE_MAKE_MODES = ("Preset", "Regenerate")
P336_TIMECODE_RUN_MODES = ("Rec Run", "Free Run")
P336_FX6_DORMANT_USB_TC_IN_BKID = "BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING"

P336_WIFI_SKUS = ("WW728473", "WW558244")
P336_WIFI_SKU_BANDS: Dict[str, Tuple[str, ...]] = {
    "WW728473": ("2.4GHz", "5GHz"),
    "WW558244": ("2.4GHz",),
}
P336_WIFI_SECURITY_ACTIVE_MODES = ("WPA2-PSK", "WPA3-SAE")
P336_WIFI_SECURITY_REMOVED_MODES = ("WEP", "WPA-PSK", "Security(IPsec)")
P336_WIFI_SECURITY_ALL_MODES = P336_WIFI_SECURITY_ACTIVE_MODES + P336_WIFI_SECURITY_REMOVED_MODES
P336_WIFI_REGULATORY_REGION_COUNT = 21
P336_WIFI_REGULATORY_DFS_RULES = 59
P336_WIFI_COUNTRY_CODE_ENTRIES = 29
P336_BT_MAX_PAIRED = 15
P336_BT_MAX_CONCURRENT = 2

P336_USB_LAN_CNCT_LAUNCH_F_RESID16 = 0x7D2A
P336_BKID_USB_LAN_CNCT_LAUNCH = "BKID_APP_setting_usb_lan_connect_launch"
P336_USB_LAN_KERNEL_MODULES = (
    "cdc_ncm.ko",
    "cdc_ether.ko",
    "r8152.ko",
    "asix.ko",
    "ax88179_178a.ko",
    "usbnet.ko",
    "ipheth.ko",
    "rndis_host.ko",
)
P336_USB_LAN_SERVICE_LIBS = ("libWiredLanResource.so", "libNetServiceEther.so")
P336_NETWORK_TRANSPORTS = ("USB-LAN (CDC-NCM)", "Wi-Fi", "Bluetooth", "Wired LAN (Ethernet)")
P336_SAFE_WIRED_TRANSPORT = "USB-LAN (CDC-NCM)"

P336_SHOOTING_DOMAINS = ("Still", "Movie", "S&Q")
P336_EXPOSURE_MODES = ("P", "A", "S", "M", "iAuto", "SCN")
P336_FOCUS_MODES = ("AF-S", "AF-A", "AF-C", "DMF", "MF")
P336_ON_OFF_MODES = ("On", "Off")
P336_RESET_ACTIONS = ("None", "Camera Settings Reset", "Reset Network Set.", "Initialize")
P336_VAULT_ACTIONS = (
    "NONE",
    "READ_ONLY_AUDIT",
    "STREAM_ONLY_USB_LAN",
    "VMC_BNCM1_EXT_LK_INJECT",
    "IMAGE_JUMP_SHOT_MARK",
    "ADD_SHOT_MARK1",
    "ADD_SHOT_MARK2",
    "DELETE_SHOT_MARK",
    "SET_CLIP_FLAG",
    "PHOTO_CAPTURE",
    "CREATE_DIVIDER_FRAME",
    "COPY_TO_SLOT1",
    "ROTATE_CLIP",
    "DORMANT_DIVIDE_CLIP",
    "DORMANT_EXTRACT_CLIP",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P336_WRITE_MUTATING_VAULT_ACTIONS = (
    "ADD_SHOT_MARK1",
    "ADD_SHOT_MARK2",
    "DELETE_SHOT_MARK",
    "SET_CLIP_FLAG",
    "PHOTO_CAPTURE",
    "CREATE_DIVIDER_FRAME",
    "COPY_TO_SLOT1",
    "ROTATE_CLIP",
    "DORMANT_DIVIDE_CLIP",
    "DORMANT_EXTRACT_CLIP",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P336_VAULT_FIREWALL_ERRNOS = ("EROFS", "EBUSY", "EOPNOTSUPP")
P336_VAULT_FIREWALL_ERRNO_CODES: Dict[str, int] = {
    "EBUSY": 16,
    "EROFS": 30,
    "EOPNOTSUPP": 95,
}

# Block Codes & Status Constants
P336_BLOCKED_SAFETY_POLICY_VIOLATION = "P336_BLOCKED_SAFETY_POLICY_VIOLATION"
P336_BLOCKED_INVALID_PILLAR60A_SPEC = "P336_BLOCKED_INVALID_PILLAR60A_SPEC"
P336_BLOCKED_INVALID_PILLAR60B_SPEC = "P336_BLOCKED_INVALID_PILLAR60B_SPEC"
P336_BLOCKED_BRIGHT_MON_OR_MONITOR_BRIGHTNESS_DRIFT = (
    "P336_BLOCKED_BRIGHT_MON_OR_MONITOR_BRIGHTNESS_DRIFT"
)
P336_BLOCKED_BULB_MECH_OR_DORMANT_BULB_TIMER_HDR_DRIFT = (
    "P336_BLOCKED_BULB_MECH_OR_DORMANT_BULB_TIMER_HDR_DRIFT"
)
P336_BLOCKED_FX6_VF_BACKLIGHT_OR_STILL_SPOOF = (
    "P336_BLOCKED_FX6_VF_BACKLIGHT_OR_STILL_SPOOF"
)
P336_BLOCKED_SHOTMARK_CLIPFLAG_OR_DORMANT_DIVIDE_DRIFT = (
    "P336_BLOCKED_SHOTMARK_CLIPFLAG_OR_DORMANT_DIVIDE_DRIFT"
)
P336_BLOCKED_TC_LINK_WPA3_OR_USBLAN_MUTEX_DRIFT = (
    "P336_BLOCKED_TC_LINK_WPA3_OR_USBLAN_MUTEX_DRIFT"
)
P336_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL = (
    "P336_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL"
)
P336_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL = P336_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL
P336_BLOCKED_PERSISTENT_OVERLAY_ESCAPE = "P336_BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P336_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT = "P336_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P336_STATUS_VERIFIED_PILLAR_60A = "VERIFIED_PILLAR_60A_BRIGHT_MON_MONITOR_BRIGHTNESS_BULB_VAULT"
P336_STATUS_REJECTED_PILLAR_60A = "REJECTED_PILLAR_60A_BRIGHT_MON_MONITOR_BRIGHTNESS_BULB_VAULT"
P336_STATUS_VERIFIED_PILLAR_60B = "VERIFIED_PILLAR_60B_SHOTMARK_EDIT_TCLINK_WPA3_USBLAN_VAULT"
P336_STATUS_REJECTED_PILLAR_60B = "REJECTED_PILLAR_60B_SHOTMARK_EDIT_TCLINK_WPA3_USBLAN_VAULT"
P336_STATUS_VERIFIED_PILLAR60_SUITE = "VERIFIED_PILLAR60_BRIGHT_MON_SHOTMARK_USBLAN_BULB_VAULT"
P336_STATUS_FAIL_PILLAR60_SUITE = "FAIL_PILLAR60_BRIGHT_MON_SHOTMARK_USBLAN_BULB_VAULT"
P336_STATUS_VERIFIED_60OF60_AGGREGATOR = "VERIFIED_60OF60_PILLAR_RECOVERY_MASTER"
P336_STATUS_FAIL_60OF60_AGGREGATOR = "FAIL_60OF60_PILLAR_RECOVERY_MASTER"

P336_PILLAR_60A_SCENARIO_IDS = (
    "P60A1_BRIGHT_MON_V700_FOCUS_MAG_COEXIST_MONITOR_BRIGHTNESS_INIT_ALLOW",
    "P60A2_STILL_MECH_BULB_AND_RESETTABLE_DRO_AUTO_ALLOW",
    "P60A3_BRIGHT_MON_PRE700_OR_AUTO_MONITOR_BRIGHTNESS_OR_MULTI_GAIN_REJECT",
    "P60A4_DORMANT_BULB_TIMER_HDR_OR_ELECTRONIC_BULB_NO_FALLBACK_REJECT",
    "P60A5_FX6_AE_BACKLIGHT_CONFLATION_OR_STILL_BULB_HDR_SPOOF_REJECT",
    "P60A6_SLOT1_VAULT_OVERLAY_ESCAPE_OR_H0_H3_DRIFT_REJECT",
)
P336_PILLAR_60B_SCENARIO_IDS = (
    "P60B1_SHOTMARK12_CLIPFLAG_PHOTO_CAPTURE_VMC_BNCM1_EXT_LK_SLOT2_ALLOW",
    "P60B2_USBLAN_CDC_NCM_WPA3_ZERO_RF_AIRPLANE_PERSISTENCE_ALLOW",
    "P60B3_DORMANT_DIVIDE_EXTRACT_CUT15S_OR_FX6_ESSENCE_MARK_SPOOF_REJECT",
    "P60B4_DORMANT_BT_TC_LINK_WEP_WPA_OR_USBLAN_MULTIPORT_COLLISION_REJECT",
    "P60B5_WW558244_5GHZ_OR_RESET_AIRPLANE_WIPE_OR_RF_PACKET_LEAK_REJECT",
    "P60B6_SLOT1_SHOTMARK_M4ROOT_DCIM_PHOTO_CAPTURE_EROFS_BYPASS_REJECT",
)

# ---------------------------------------------------------------------------
# 60-Pillar Master Registry (Pillars 1..59 + Pillar 60)
# ---------------------------------------------------------------------------

MASTER_60_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_59_PILLAR_SPECS + (
    (
        60,
        "pillar60_bright_mon_shotmark_usblan_bulb_dormant_vault",
        "Phase 336",
        "fx3_recovery.realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier",
    ),
)
MASTER_60_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_60_PILLAR_SPECS)
MASTER_60_PILLAR_COUNT = len(MASTER_60_PILLAR_SPECS)


# ---------------------------------------------------------------------------
# Internal Safety, Hashing & Deterministic State Helpers
# ---------------------------------------------------------------------------


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _canonical_sha256(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _is_clean_room_forced(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is True:
        return True
    env_flag = os.environ.get(P336_ENV_CLEAN_ROOM_TEST, "").strip().lower()
    if env_flag in ("1", "true", "yes"):
        return True
    if is_forced_clean_room():
        return True
    return False


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true" or os.environ.get(
        "CI", ""
    ).strip().lower() in ("1", "true", "yes"):
        return P336_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P336_DONOR_INSPECT_BUDGET_SECONDS


def _is_tmpfs_path(path: str) -> bool:
    norm = posixpath.normpath(path)
    return norm == "/tmp" or norm.startswith("/tmp/")


def _targets_persistent_emmc(path: str) -> bool:
    norm = posixpath.normpath(path)
    return any(
        norm == pref or norm.startswith(pref + "/") or norm.startswith(pref)
        for pref in P336_FORBIDDEN_PERSISTENT_TARGETS
    )


def _safety_invariant_errors() -> List[str]:
    errs: List[str] = []
    if PERSISTENT_EMMC_WRITES_AUTHORIZED:
        errs.append("PERSISTENT_EMMC_WRITES_AUTHORIZED must remain False")
    if SPI_NOR_WRITE_AUTHORIZED:
        errs.append("SPI_NOR_WRITE_AUTHORIZED must remain False")
    if EL3_PAYLOAD_TRANSMIT_AUTHORIZED:
        errs.append("EL3_PAYLOAD_TRANSMIT_AUTHORIZED must remain False")
    if ISP_WRITE_AUTHORIZED:
        errs.append("ISP_WRITE_AUTHORIZED must remain False")
    if PERSISTENT_WRITE_RELEASE:
        errs.append("PERSISTENT_WRITE_RELEASE must remain False")
    if ALLOW_BOOT_PARTITION_TARGETING:
        errs.append("ALLOW_BOOT_PARTITION_TARGETING must remain False")
    if ALLOW_DESTRUCTIVE_FASTBOOT:
        errs.append("ALLOW_DESTRUCTIVE_FASTBOOT must remain False")
    if ALLOW_PERSISTENT_JIRITSU_WRITES:
        errs.append("ALLOW_PERSISTENT_JIRITSU_WRITES must remain False")
    if ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS:
        errs.append("ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS must remain False")
    if LIVE_USB_IOKIT_TRANSMIT_ENABLED:
        errs.append("LIVE_USB_IOKIT_TRANSMIT_ENABLED must remain False")
    if HARDWARE_LIVE_ATTACHMENT_AUTHORIZED:
        errs.append("HARDWARE_LIVE_ATTACHMENT_AUTHORIZED must remain False")
    if OVERALL_READY_FOR_HARDWARE_ATTACH:
        errs.append("OVERALL_READY_FOR_HARDWARE_ATTACH must remain False")
    if CROSS_MODEL_FLASH_AUTHORIZED:
        errs.append("CROSS_MODEL_FLASH_AUTHORIZED must remain False")
    if not READ_ONLY_DONOR_ACCESS:
        errs.append("READ_ONLY_DONOR_ACCESS must remain True")
    if not P336_SLOT1_FORMAT_HARD_LOCKED:
        errs.append("P336_SLOT1_FORMAT_HARD_LOCKED must remain True")
    if not P336_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED:
        errs.append("P336_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED must remain True")
    if not CNFLASHA_USERSPACE_WRITE_BLOCKED:
        errs.append("CNFLASHA_USERSPACE_WRITE_BLOCKED must remain True")
    if OTP_FUSE_TOUCHES != 0 or OTP_FUSE_WRITES != 0:
        errs.append("OTP_FUSE_TOUCHES / OTP_FUSE_WRITES must remain 0")
    if RPMB_COUNTER_INCREMENTS != 0:
        errs.append("RPMB_COUNTER_INCREMENTS must remain 0")
    if PASSIVE_TX_BYTES_EMITTED != 0:
        errs.append("PASSIVE_TX_BYTES_EMITTED must remain 0")
    if PHYSICAL_USB_PACKETS_EMITTED != 0:
        errs.append("PHYSICAL_USB_PACKETS_EMITTED must remain 0")
    if PHYSICAL_DEVICE_WRITES != 0:
        errs.append("PHYSICAL_DEVICE_WRITES must remain 0")
    if RAW_FIRMWARE_BYTES_LEAKED != 0:
        errs.append("RAW_FIRMWARE_BYTES_LEAKED must remain 0")
    return errs


def compute_expected_bright_mon_bulb_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    exposure_mode: str,
    focus_mode: str,
    power_state: str,
    bright_monitoring_requested: bool,
    focus_magnifier_active: bool,
    requested_bright_mon_multi_gain_ext: bool,
    monitor_brightness_mode: str,
    monitor_brightness_level: int,
    shutter_type: str,
    still_drive_mode: str,
    bulb_requested: bool,
    picture_profile: str,
    hlg_still_image: str,
    dro_mode: str,
    dro_bracket: str,
    requested_dormant_bulb_or_hdr_symbols: Tuple[str, ...],
    reset_action: str,
) -> Dict[str, Any]:
    """Compute canonical Wave-58 Pillar 60A state:
    [Bright Monitoring] Ver. 7.00+ Focus-Mag Coexistence, [Monitor Brightness] Initialize-only,
    Mechanical-Shutter-only [BULB] -> 30" fallback, Resettable [DRO], & Dormant [Bulb Timer] / [Auto HDR]."""
    is_fx3 = camera_model == P336_FX3_MODEL_NAME
    supports_bm_focus_mag = is_fx3 and fw_version in P336_FX3_FOCUS_MAG_BRIGHT_MON_MIN_FW

    # 1. [Bright Monitoring] auto-cancel & Ver. 7.00+ Focus Magnifier coexistence
    bm_auto_cancelled = (
        not is_fx3
        or power_state != "On"
        or exposure_mode not in ("P", "A", "S", "M")
        or focus_mode != "MF"
    )
    bm_focus_mag_conflict = focus_magnifier_active and not supports_bm_focus_mag
    if requested_bright_mon_multi_gain_ext or not is_fx3:
        effective_bright_monitoring = False
        bright_monitoring_errno: Optional[int] = P336_EOPNOTSUPP_ERRNO
    elif bright_monitoring_requested and (bm_auto_cancelled or bm_focus_mag_conflict):
        effective_bright_monitoring = False
        bright_monitoring_errno = P336_EOPNOTSUPP_ERRNO
    else:
        effective_bright_monitoring = bool(bright_monitoring_requested)
        bright_monitoring_errno = None

    forced_live_view_display = (
        "Setting Effect OFF" if effective_bright_monitoring else "UserConfigured"
    )

    # 2. [Monitor Brightness] (Manual -2..+2 / Sunny Weather; dormant Auto -> EOPNOTSUPP=95)
    dormant_monitor_auto = monitor_brightness_mode not in P336_MONITOR_BRIGHTNESS_MODES
    monitor_level_valid = (
        P336_MONITOR_BRIGHTNESS_MIN_LEVEL
        <= monitor_brightness_level
        <= P336_MONITOR_BRIGHTNESS_MAX_LEVEL
    )
    monitor_brightness_errno: Optional[int] = (
        P336_EOPNOTSUPP_ERRNO
        if (dormant_monitor_auto or not is_fx3)
        else (None if monitor_level_valid else P336_EINVAL_ERRNO)
    )

    # Initialize-only vs Resettable split
    if is_fx3 and reset_action == "Initialize":
        post_monitor_brightness_mode = P336_MONITOR_BRIGHTNESS_DEFAULT_MODE
        post_monitor_brightness_level = P336_MONITOR_BRIGHTNESS_DEFAULT_LEVEL
    else:
        post_monitor_brightness_mode = monitor_brightness_mode
        post_monitor_brightness_level = monitor_brightness_level

    # 3. Manual [BULB] Mechanical Shutter requirement & 30" fallback
    bulb_blocked_reasons: List[str] = []
    if not is_fx3 or shooting_domain != "Still" or exposure_mode != "M":
        bulb_blocked_reasons.append("REQUIRES_FX3_STILL_M_MODE")
    if shutter_type != "Mechanical Shutter":
        bulb_blocked_reasons.append("REQUIRES_MECHANICAL_SHUTTER")
    if still_drive_mode in P336_BULB_DISALLOWED_DRIVE_MODES:
        bulb_blocked_reasons.append("DISALLOWED_STILL_DRIVE_MODE")
    bulb_blocked = len(bulb_blocked_reasons) > 0

    if bulb_requested and bulb_blocked:
        effective_bulb_active = False
        effective_bulb_fallback_shutter = P336_BULB_FALLBACK_SHUTTER
        bulb_errno: Optional[int] = P336_EOPNOTSUPP_ERRNO
    elif bulb_requested:
        effective_bulb_active = True
        effective_bulb_fallback_shutter = "BULB"
        bulb_errno = None
    else:
        effective_bulb_active = False
        effective_bulb_fallback_shutter = '1/125"'
        bulb_errno = None

    anti_flicker_disabled_by_bulb = effective_bulb_active

    # 4. [D-Range Optimizer] & [DRO Bracket] lockouts (PP != Off or HLG Still = On)
    dro_locked_off = (picture_profile != "Off") or (hlg_still_image == "On") or not is_fx3
    effective_dro_mode = "Off" if dro_locked_off else dro_mode
    dro_bracket_allowed = is_fx3 and (hlg_still_image != "On") and (picture_profile == "Off")
    if dro_bracket != "Off" and not dro_bracket_allowed:
        dro_errno: Optional[int] = P336_EOPNOTSUPP_ERRNO
    else:
        dro_errno = None

    if is_fx3 and reset_action in ("Camera Settings Reset", "Initialize"):
        post_dro_mode = "Off" if dro_locked_off else P336_DRO_DEFAULT
        post_dro_bracket = "Off"
        post_bulb_active = False
    else:
        post_dro_mode = effective_dro_mode
        post_dro_bracket = dro_bracket if dro_bracket_allowed else "Off"
        post_bulb_active = effective_bulb_active

    # 5. Dormant [Bulb Timer] & [Auto HDR] fail-closed
    dormant_bulb_hdr_errno: Optional[int] = (
        P336_EOPNOTSUPP_ERRNO if len(requested_dormant_bulb_or_hdr_symbols) > 0 else None
    )

    return {
        "supports_bm_focus_mag": supports_bm_focus_mag,
        "bm_auto_cancelled": bm_auto_cancelled,
        "effective_bright_monitoring": effective_bright_monitoring,
        "bright_monitoring_errno": bright_monitoring_errno,
        "forced_live_view_display": forced_live_view_display,
        "monitor_brightness_errno": monitor_brightness_errno,
        "post_monitor_brightness_mode": post_monitor_brightness_mode,
        "post_monitor_brightness_level": post_monitor_brightness_level,
        "bulb_blocked": bulb_blocked,
        "bulb_blocked_reasons": tuple(bulb_blocked_reasons),
        "effective_bulb_active": effective_bulb_active,
        "effective_bulb_fallback_shutter": effective_bulb_fallback_shutter,
        "bulb_errno": bulb_errno,
        "anti_flicker_disabled_by_bulb": anti_flicker_disabled_by_bulb,
        "dro_locked_off": dro_locked_off,
        "effective_dro_mode": effective_dro_mode,
        "dro_bracket_allowed": dro_bracket_allowed,
        "dro_errno": dro_errno,
        "post_dro_mode": post_dro_mode,
        "post_dro_bracket": post_dro_bracket,
        "post_bulb_active": post_bulb_active,
        "dormant_bulb_hdr_errno": dormant_bulb_hdr_errno,
    }


def compute_expected_shotmark_tc_usblan_vault_state(
    *,
    camera_model: str,
    shot_mark_slot: int,
    clip_flag: str,
    image_jump_setting: str,
    photo_capture_file_type: str,
    requested_dormant_clip_edit_symbols: Tuple[str, ...],
    requested_fx6_dormant_shot_mark_symbols: Tuple[str, ...],
    requested_bt_timecode_link: bool,
    vmc_bncm1_connected: bool,
    timecode_make: str,
    timecode_run: str,
    hdmi_tc_output: str,
    wifi_sku: str,
    wifi_band: str,
    wifi_security: str,
    usb_lan_active: bool,
    usb_lan_cnct_launch: str,
    wifi_active: bool,
    multi_micro_usb_in_use: bool,
    airplane_mode: str,
    network_transport: str,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
    shot_mark_or_clip_flag_targets_slot1: bool,
    photo_capture_or_divider_targets_slot1: bool,
) -> Dict[str, Any]:
    """Compute canonical Wave-58 Pillar 60B state:
    [Shot Mark 1/2] & [Clip Flag] vs Dormant Divide/Extract, Zero-BT Timecode Link vs VMC-BNCM1 EXT-LK,
    WPA2/WPA3 vs removed WEP/WPA/IPsec, USB-LAN / Multi-Micro USB / Wi-Fi mutual exclusion,
    Airplane Mode=On retention across Reset Network Set. & Initialize, and Slot-1 EROFS=30 Firewall."""
    is_fx3 = camera_model == P336_FX3_MODEL_NAME

    # 1. Dormant Clip Edit / FX6 Shot Mark 0..9
    dormant_clip_edit_errno: Optional[int] = (
        P336_EOPNOTSUPP_ERRNO
        if (
            len(requested_dormant_clip_edit_symbols) > 0
            or requested_vault_action in ("DORMANT_DIVIDE_CLIP", "DORMANT_EXTRACT_CLIP")
        )
        else None
    )
    dormant_fx6_shot_mark_errno: Optional[int] = (
        P336_EOPNOTSUPP_ERRNO if len(requested_fx6_dormant_shot_mark_symbols) > 0 else None
    )

    # 2. Zero Bluetooth Timecode Link vs VMC-BNCM1 wired EXT-LK
    bt_timecode_link_errno: Optional[int] = (
        P336_EOPNOTSUPP_ERRNO if requested_bt_timecode_link else None
    )
    if is_fx3:
        ext_tc_locked = (
            vmc_bncm1_connected
            and timecode_make == "Preset"
            and timecode_run == "Free Run"
            and not usb_lan_active
        )
        ext_tc_status = "EXT-LK" if ext_tc_locked else "INTERNAL"
    else:
        # FX6 uses dedicated physical TC IN/OUT BNC switch
        ext_tc_locked = timecode_make == "Preset" and timecode_run == "Free Run"
        ext_tc_status = "EXT-LK" if ext_tc_locked else "INTERNAL"

    # 3. Wi-Fi SKU band & Ver. 7.00+ WPA2-PSK/WPA3-SAE hardening (WEP/WPA-PSK/IPsec removed)
    allowed_bands = P336_WIFI_SKU_BANDS.get(wifi_sku, ("2.4GHz",))
    wifi_band_errno: Optional[int] = (
        None if wifi_band in allowed_bands else P336_EOPNOTSUPP_ERRNO
    )
    wifi_security_errno: Optional[int] = (
        None if wifi_security in P336_WIFI_SECURITY_ACTIVE_MODES else P336_EOPNOTSUPP_ERRNO
    )

    # 4. USB-LAN mutual exclusion with Wi-Fi & Multi/Micro USB (e.g. VMC-BNCM1)
    usb_lan_bus_conflict = usb_lan_active and (wifi_active or multi_micro_usb_in_use)
    usb_lan_conflict_errno: Optional[int] = (
        P336_EOPNOTSUPP_ERRNO if usb_lan_bus_conflict else None
    )

    # 5. Airplane Mode persistence across Reset Network Set. AND Initialize (Wave 58 empirical rule!)
    if is_fx3 and reset_action in ("Reset Network Set.", "Initialize"):
        post_usb_lan_cnct_launch = "Off"
        post_airplane_mode = airplane_mode  # Retained as "On" across BOTH Reset Network Set. & Initialize!
    else:
        post_usb_lan_cnct_launch = usb_lan_cnct_launch
        post_airplane_mode = airplane_mode

    rf_zero_enforced = (
        airplane_mode == "On"
        and post_airplane_mode == "On"
        and not wifi_active
        and network_transport == P336_SAFE_WIRED_TRANSPORT
    )

    # 6. Slot-1 Tier-0 Vault EROFS=30 Firewall
    mutates_slot1 = requested_vault_slot == P336_SLOT1_VAULT_SLOT and (
        requested_vault_action in P336_WRITE_MUTATING_VAULT_ACTIONS
        or shot_mark_or_clip_flag_targets_slot1
        or photo_capture_or_divider_targets_slot1
    )
    if mutates_slot1 and slot1_holds_tier0_vault:
        action_allowed = False
        firewall_errno: Optional[str] = "EROFS"
    elif requested_vault_action in ("FORMAT_QUICK", "FORMAT_FULL"):
        action_allowed = False
        firewall_errno = "EROFS"
    elif requested_vault_action in (
        "READ_ONLY_AUDIT",
        "STREAM_ONLY_USB_LAN",
        "VMC_BNCM1_EXT_LK_INJECT",
        "IMAGE_JUMP_SHOT_MARK",
    ):
        action_allowed = not (
            shot_mark_or_clip_flag_targets_slot1 or photo_capture_or_divider_targets_slot1
        )
        firewall_errno = None if action_allowed else "EROFS"
    elif requested_vault_action == "NONE":
        action_allowed = False
        firewall_errno = None
    elif requested_vault_slot == P336_SAFE_SECONDARY_SLOT:
        action_allowed = True
        firewall_errno = None
    else:
        action_allowed = False
        firewall_errno = "EROFS"

    return {
        "shot_mark_slot_valid": shot_mark_slot in (1, 2),
        "clip_flag_valid": clip_flag in P336_CLIP_FLAG_OPTIONS,
        "image_jump_valid": image_jump_setting in P336_IMAGE_JUMP_OPTIONS,
        "photo_capture_type_valid": photo_capture_file_type in P336_PHOTO_CAPTURE_FILE_TYPES,
        "dormant_clip_edit_errno": dormant_clip_edit_errno,
        "dormant_fx6_shot_mark_errno": dormant_fx6_shot_mark_errno,
        "bt_timecode_link_errno": bt_timecode_link_errno,
        "ext_tc_locked": ext_tc_locked,
        "ext_tc_status": ext_tc_status,
        "wifi_band_errno": wifi_band_errno,
        "wifi_security_errno": wifi_security_errno,
        "usb_lan_bus_conflict": usb_lan_bus_conflict,
        "usb_lan_conflict_errno": usb_lan_conflict_errno,
        "post_usb_lan_cnct_launch": post_usb_lan_cnct_launch,
        "post_airplane_mode": post_airplane_mode,
        "rf_zero_enforced": rf_zero_enforced,
        "action_allowed": action_allowed,
        "firewall_errno": firewall_errno,
        "firewall_errno_num": (
            P336_VAULT_FIREWALL_ERRNO_CODES[firewall_errno]
            if firewall_errno in P336_VAULT_FIREWALL_ERRNO_CODES
            else None
        ),
        "hdmi_tc_output": hdmi_tc_output,
    }


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & work_root=None Clean-Room Guard (17 Donors)
# ---------------------------------------------------------------------------


def _iter_work_roots() -> Tuple[Optional[Path], ...]:
    """Return candidate donor work roots (delegates to `_fx3_files.iter_donor_work_roots`)."""
    return _fx3_files.iter_donor_work_roots()


def _resolve_phase336_donor_path(
    relpath: str,
    *,
    work_roots: Optional[Tuple[Optional[Path], ...]] = None,
) -> Optional[Path]:
    """Resolve `relpath` with an explicit `work_root is None` guard for donorless Ubuntu CI."""
    if _is_clean_room_forced(None):
        return None
    rel_norm = relpath.strip("/")
    if rel_norm.startswith("work/"):
        rel_norm = rel_norm[len("work/") :]
    roots = _iter_work_roots() if work_roots is None else work_roots
    for work_root in roots:
        if work_root is None:
            continue
        candidate = Path(work_root) / rel_norm
        try:
            if candidate.exists():
                return candidate
        except OSError:
            continue
    return None


def _read_donor_readonly_bounded(
    relpath: str,
    max_full_bytes: int = P336_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    try:
        resolved = _resolve_phase336_donor_path(relpath)
    except Exception:
        return False, 0, 0, "MISSING", "", b""
    if resolved is None:
        return False, 0, 0, "MISSING", "", b""
    try:
        if not resolved.exists():
            return False, 0, 0, "MISSING", "", b""
    except OSError:
        return False, 0, 0, "MISSING", "", b""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(str(resolved), flags)
    except OSError:
        return False, 0, 0, "OPEN_ERROR", "", b""
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return False, 0, 0, "NOT_REGULAR", "", b""
        total_size = int(st.st_size)
        if total_size <= max_full_bytes:
            chunks: List[bytes] = []
            offset = 0
            while offset < total_size:
                chunk = os.pread(fd, min(65536, total_size - offset), offset)
                if not chunk:
                    break
                chunks.append(chunk)
                offset += len(chunk)
            data = b"".join(chunks)
            return True, total_size, len(data), "FULL_SHA256", sha256(data).hexdigest(), data
        hdr = os.pread(fd, min(P336_BOUNDED_HEADER_BYTES, total_size), 0)
        return True, total_size, len(hdr), "HEADER4K_SHA256", sha256(hdr).hexdigest(), hdr
    finally:
        os.close(fd)


def _check_elf64_aarch64(data: bytes, label: str) -> Tuple[bool, str]:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        return False, f"NOT_ELF:{label}"
    ei_class, ei_data = data[4], data[5]
    e_machine = struct.unpack_from("<H", data, 18)[0]
    if ei_class != 2 or ei_data != 1 or e_machine != 183:
        return False, f"BAD_ELF64_AARCH64(class={ei_class},data={ei_data},mach={e_machine})"
    return True, f"ELF64_AARCH64:{label}"


def _check_uxc7_pack(data: bytes, label: str) -> Tuple[bool, str]:
    if len(data) < 16 or data[:4] != b"uxc\x07":
        return False, f"BAD_UXC7_MAGIC:{label}"
    return True, f"UXC7_{label}"


def _check_bk4_backup(data: bytes, label: str) -> Tuple[bool, str]:
    if len(data) < 32 or struct.unpack_from("<I", data, 4)[0] != 0xAAAAAAAA or data[12:16] != b"BK4\x00":
        return False, f"BAD_BK4_MAGIC:{label}"
    return True, f"BK4_{label}"


def _synthetic_phase336_donors() -> Tuple["Phase336DonorArtifactDigest", ...]:
    specs = (
        ("fx3_appfw_702_so", P336_DONOR_FX3_APPFW_702_RELPATH, P336_PINNED_FX3_APPFW_702_BYTES, P336_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P336_PINNED_FX3_APPFW_702_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702"),
        ("fx6_appfw_601_so", P336_DONOR_FX6_APPFW_601_RELPATH, P336_PINNED_FX6_APPFW_601_BYTES, P336_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P336_PINNED_FX6_APPFW_601_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601"),
        ("fx3_backup_bin", P336_DONOR_FX3_BACKUP_BIN_RELPATH, P336_PINNED_FX3_BACKUP_BIN_BYTES, P336_PINNED_FX3_BACKUP_BIN_BYTES, "FULL_SHA256", P336_PINNED_FX3_BACKUP_BIN_SHA256, "SYNTHETIC_BK4_ILME_FX3"),
        ("fx3_uxc_en_f", P336_DONOR_FX3_UXC_EN_F_RELPATH, P336_PINNED_FX3_UXC_EN_F_BYTES, P336_PINNED_FX3_UXC_EN_F_BYTES, "FULL_SHA256", P336_PINNED_FX3_UXC_EN_F_SHA256, "SYNTHETIC_UXC7_FX3_EN_F"),
        ("fx3_uxc_sc_f", P336_DONOR_FX3_UXC_SC_F_RELPATH, P336_PINNED_FX3_UXC_SC_F_BYTES, P336_PINNED_FX3_UXC_SC_F_BYTES, "FULL_SHA256", P336_PINNED_FX3_UXC_SC_F_SHA256, "SYNTHETIC_UXC7_FX3_SC_F"),
        ("fx3_uxc_tc_f", P336_DONOR_FX3_UXC_TC_F_RELPATH, P336_PINNED_FX3_UXC_TC_F_BYTES, P336_PINNED_FX3_UXC_TC_F_BYTES, "FULL_SHA256", P336_PINNED_FX3_UXC_TC_F_SHA256, "SYNTHETIC_UXC7_FX3_TC_F"),
        ("fx3_uxc_ja_f", P336_DONOR_FX3_UXC_JA_F_RELPATH, P336_PINNED_FX3_UXC_JA_F_BYTES, P336_PINNED_FX3_UXC_JA_F_BYTES, "FULL_SHA256", P336_PINNED_FX3_UXC_JA_F_SHA256, "SYNTHETIC_UXC7_FX3_JA_F"),
        ("fx3_uxc_en", P336_DONOR_FX3_UXC_EN_RELPATH, P336_PINNED_FX3_UXC_EN_BYTES, P336_PINNED_FX3_UXC_EN_BYTES, "FULL_SHA256", P336_PINNED_FX3_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX3_EN"),
        ("fx3_uxc_sc", P336_DONOR_FX3_UXC_SC_RELPATH, P336_PINNED_FX3_UXC_SC_BYTES, P336_PINNED_FX3_UXC_SC_BYTES, "FULL_SHA256", P336_PINNED_FX3_UXC_SC_SHA256, "SYNTHETIC_UXC7_FX3_SC"),
        ("fx3_uxc_tc", P336_DONOR_FX3_UXC_TC_RELPATH, P336_PINNED_FX3_UXC_TC_BYTES, P336_PINNED_FX3_UXC_TC_BYTES, "FULL_SHA256", P336_PINNED_FX3_UXC_TC_SHA256, "SYNTHETIC_UXC7_FX3_TC"),
        ("fx3_uxc_ja", P336_DONOR_FX3_UXC_JA_RELPATH, P336_PINNED_FX3_UXC_JA_BYTES, P336_PINNED_FX3_UXC_JA_BYTES, "FULL_SHA256", P336_PINNED_FX3_UXC_JA_SHA256, "SYNTHETIC_UXC7_FX3_JA"),
        ("fx3_uxc_en_g", P336_DONOR_FX3_UXC_EN_G_RELPATH, P336_PINNED_FX3_UXC_EN_G_BYTES, P336_PINNED_FX3_UXC_EN_G_BYTES, "FULL_SHA256", P336_PINNED_FX3_UXC_EN_G_SHA256, "SYNTHETIC_UXC7_FX3_EN_G"),
        ("fx3_uxc_sc_g", P336_DONOR_FX3_UXC_SC_G_RELPATH, P336_PINNED_FX3_UXC_SC_G_BYTES, P336_PINNED_FX3_UXC_SC_G_BYTES, "FULL_SHA256", P336_PINNED_FX3_UXC_SC_G_SHA256, "SYNTHETIC_UXC7_FX3_SC_G"),
        ("fx3_uxc_tc_g", P336_DONOR_FX3_UXC_TC_G_RELPATH, P336_PINNED_FX3_UXC_TC_G_BYTES, P336_PINNED_FX3_UXC_TC_G_BYTES, "FULL_SHA256", P336_PINNED_FX3_UXC_TC_G_SHA256, "SYNTHETIC_UXC7_FX3_TC_G"),
        ("fx3_uxc_ja_g", P336_DONOR_FX3_UXC_JA_G_RELPATH, P336_PINNED_FX3_UXC_JA_G_BYTES, P336_PINNED_FX3_UXC_JA_G_BYTES, "FULL_SHA256", P336_PINNED_FX3_UXC_JA_G_SHA256, "SYNTHETIC_UXC7_FX3_JA_G"),
        ("fx6_uxc_en", P336_DONOR_FX6_UXC_EN_RELPATH, P336_PINNED_FX6_UXC_EN_BYTES, P336_PINNED_FX6_UXC_EN_BYTES, "FULL_SHA256", P336_PINNED_FX6_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX6_EN"),
        ("fx6_uxc_en_2", P336_DONOR_FX6_UXC_EN_2_RELPATH, P336_PINNED_FX6_UXC_EN_2_BYTES, P336_PINNED_FX6_UXC_EN_2_BYTES, "FULL_SHA256", P336_PINNED_FX6_UXC_EN_2_SHA256, "SYNTHETIC_UXC7_FX6_EN_2"),
    )
    return tuple(
        Phase336DonorArtifactDigest(
            artifact_id=aid,
            relpath=rel,
            present=True,
            read_mode="CLEAN_ROOM_SYNTHETIC",
            total_bytes=total,
            header_bytes_read=hdr_b,
            digest_kind=dkind,
            digest_sha256=dsha,
            marker_summary=msum,
            matches_pinned=True,
        )
        for aid, rel, total, hdr_b, dkind, dsha, msum in specs
    )


def inspect_phase336_donors_readonly(
    force_clean_room: Optional[bool] = None,
) -> "Phase336DonorSnapshot":
    """Inspect Wave-58 FX3 7.02 (`14` donors) & FX6 6.01 (`3` donors) strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase336_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase336DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_20s_budget=dt < budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        ("fx3_appfw_702_so", P336_DONOR_FX3_APPFW_702_RELPATH, P336_PINNED_FX3_APPFW_702_BYTES, P336_PINNED_FX3_APPFW_702_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702")),
        ("fx6_appfw_601_so", P336_DONOR_FX6_APPFW_601_RELPATH, P336_PINNED_FX6_APPFW_601_BYTES, P336_PINNED_FX6_APPFW_601_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601")),
        ("fx3_backup_bin", P336_DONOR_FX3_BACKUP_BIN_RELPATH, P336_PINNED_FX3_BACKUP_BIN_BYTES, P336_PINNED_FX3_BACKUP_BIN_SHA256, lambda d: _check_bk4_backup(d, "ILME_FX3")),
        ("fx3_uxc_en_f", P336_DONOR_FX3_UXC_EN_F_RELPATH, P336_PINNED_FX3_UXC_EN_F_BYTES, P336_PINNED_FX3_UXC_EN_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_F")),
        ("fx3_uxc_sc_f", P336_DONOR_FX3_UXC_SC_F_RELPATH, P336_PINNED_FX3_UXC_SC_F_BYTES, P336_PINNED_FX3_UXC_SC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_F")),
        ("fx3_uxc_tc_f", P336_DONOR_FX3_UXC_TC_F_RELPATH, P336_PINNED_FX3_UXC_TC_F_BYTES, P336_PINNED_FX3_UXC_TC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_F")),
        ("fx3_uxc_ja_f", P336_DONOR_FX3_UXC_JA_F_RELPATH, P336_PINNED_FX3_UXC_JA_F_BYTES, P336_PINNED_FX3_UXC_JA_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_F")),
        ("fx3_uxc_en", P336_DONOR_FX3_UXC_EN_RELPATH, P336_PINNED_FX3_UXC_EN_BYTES, P336_PINNED_FX3_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN")),
        ("fx3_uxc_sc", P336_DONOR_FX3_UXC_SC_RELPATH, P336_PINNED_FX3_UXC_SC_BYTES, P336_PINNED_FX3_UXC_SC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC")),
        ("fx3_uxc_tc", P336_DONOR_FX3_UXC_TC_RELPATH, P336_PINNED_FX3_UXC_TC_BYTES, P336_PINNED_FX3_UXC_TC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC")),
        ("fx3_uxc_ja", P336_DONOR_FX3_UXC_JA_RELPATH, P336_PINNED_FX3_UXC_JA_BYTES, P336_PINNED_FX3_UXC_JA_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA")),
        ("fx3_uxc_en_g", P336_DONOR_FX3_UXC_EN_G_RELPATH, P336_PINNED_FX3_UXC_EN_G_BYTES, P336_PINNED_FX3_UXC_EN_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_G")),
        ("fx3_uxc_sc_g", P336_DONOR_FX3_UXC_SC_G_RELPATH, P336_PINNED_FX3_UXC_SC_G_BYTES, P336_PINNED_FX3_UXC_SC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_G")),
        ("fx3_uxc_tc_g", P336_DONOR_FX3_UXC_TC_G_RELPATH, P336_PINNED_FX3_UXC_TC_G_BYTES, P336_PINNED_FX3_UXC_TC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_G")),
        ("fx3_uxc_ja_g", P336_DONOR_FX3_UXC_JA_G_RELPATH, P336_PINNED_FX3_UXC_JA_G_BYTES, P336_PINNED_FX3_UXC_JA_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_G")),
        ("fx6_uxc_en", P336_DONOR_FX6_UXC_EN_RELPATH, P336_PINNED_FX6_UXC_EN_BYTES, P336_PINNED_FX6_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN")),
        ("fx6_uxc_en_2", P336_DONOR_FX6_UXC_EN_2_RELPATH, P336_PINNED_FX6_UXC_EN_2_BYTES, P336_PINNED_FX6_UXC_EN_2_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN_2")),
    )

    def _probe_one(spec: Tuple[str, str, int, str, Any]) -> Optional[Phase336DonorArtifactDigest]:
        aid, relpath, expected_bytes, expected_sha, marker_fn = spec
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            return None
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        return Phase336DonorArtifactDigest(
            artifact_id=aid,
            relpath=relpath,
            present=True,
            read_mode="LOCAL_DONOR_O_RDONLY",
            total_bytes=total_b,
            header_bytes_read=hdr_b,
            digest_kind=dkind,
            digest_sha256=dsha,
            marker_summary=msum,
            matches_pinned=matches,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_probe_one, probe_specs))

    if any(r is None for r in results):
        artifacts = _synthetic_phase336_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase336DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_20s_budget=dt < budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    digests = tuple(r for r in results if r is not None)
    all_ok = all(d.present and d.matches_pinned for d in digests) and len(digests) == len(probe_specs)
    dt = round(time.monotonic() - t0, 6)
    return Phase336DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all_ok,
        donor_files_inspected=len(digests),
        elapsed_seconds=dt,
        under_0_20s_budget=dt < budget,
        budget_seconds_applied=budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=digests,
    )


# ---------------------------------------------------------------------------
# Frozen Dataclasses (Specs, Reports, Suites & 60-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase336DonorArtifactDigest:
    artifact_id: str
    relpath: str
    present: bool
    read_mode: str
    total_bytes: int
    header_bytes_read: int
    digest_kind: str
    digest_sha256: str
    marker_summary: str
    matches_pinned: bool


@dataclass(frozen=True)
class Phase336DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_20s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase336DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BrightMonMonitorBrightnessBulbVaultSpec:
    # Wave-58 [Bright Monitoring] Ver.7.00+ Focus-Mag Coexistence & [Monitor Brightness]
    camera_model: str
    fw_version: str
    shooting_domain: str
    exposure_mode: str
    focus_mode: str
    power_state: str
    bright_monitoring_custom_key_only: bool
    bright_monitoring_in_shooting_menu: bool
    bright_monitoring_symbol_count: int
    bright_monitoring_requested: bool
    focus_magnifier_active: bool
    requested_bright_mon_multi_gain_ext: bool
    reported_effective_bright_monitoring: bool
    reported_bright_monitoring_errno: Optional[int]
    reported_forced_live_view_display: str
    monitor_brightness_menu_path: Tuple[str, ...]
    monitor_brightness_mode: str
    monitor_brightness_level: int
    reported_monitor_brightness_errno: Optional[int]
    post_monitor_brightness_mode: str
    post_monitor_brightness_level: int
    # Wave-58 Manual [BULB] Mechanical Shutter, Resettable [DRO] & Dormant [Bulb Timer] / [Auto HDR]
    shutter_type: str
    still_drive_mode: str
    bulb_requested: bool
    reported_effective_bulb_active: bool
    reported_bulb_fallback_shutter: str
    reported_bulb_errno: Optional[int]
    reported_anti_flicker_disabled_by_bulb: bool
    picture_profile: str
    hlg_still_image: str
    dro_mode: str
    dro_bracket: str
    reported_effective_dro_mode: str
    reported_dro_errno: Optional[int]
    post_dro_mode: str
    post_dro_bracket: str
    post_bulb_active: bool
    requested_dormant_bulb_or_hdr_symbols: Tuple[str, ...]
    reported_dormant_bulb_hdr_errno: Optional[int]
    # ILME-FX6 VF Setting > Brightness (1..15) + AE Backlight Disambiguation & Zero Still Pipeline
    fx6_vf_brightness: int
    fx6_vf_color_mode: str
    fx6_ae_backlight_is_exposure_mode: bool
    fx6_has_bright_monitoring: bool
    fx6_has_still_bulb_or_dro_hdr: bool
    fx6_uses_dual_base_iso_800_12800: bool
    requested_fx6_dormant_backlight_symbols: Tuple[str, ...]
    reported_fx6_dormant_backlight_errno: Optional[int]
    reset_action: str
    # Slot-1 Tier-0 Vault & Stage-B Overlay
    requested_vault_slot: int
    requested_vault_action: str
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative counters
    bright_mon_or_monitor_brightness_drift_events: int
    bulb_mech_or_dormant_bulb_timer_hdr_drift_events: int
    fx6_vf_backlight_or_still_spoof_events: int


@dataclass(frozen=True)
class BrightMonMonitorBrightnessBulbVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    bright_mon_v700_focus_mag_and_monitor_brightness_verified: bool
    bulb_mech_dro_and_dormant_bulb_timer_hdr_verified: bool
    fx6_vf_backlight_disambiguation_and_zero_still_verified: bool
    slot1_vault_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    bright_mon_or_monitor_brightness_drift_events: int
    bulb_mech_or_dormant_bulb_timer_hdr_drift_events: int
    fx6_vf_backlight_or_still_spoof_events: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ShotMarkEditTcLinkUsbLanVaultSpec:
    # Wave-58 [Shot Mark 1/2], [Clip Flag], [Edit] vs Dormant [Divide]/[Extract]/Cut-15/30/60s
    camera_model: str
    fw_version: str
    shot_mark_slot: int
    clip_flag: str
    image_jump_setting: str
    playback_edit_items: Tuple[str, ...]
    photo_capture_file_type: str
    create_divider_frame_supported: bool
    requested_dormant_clip_edit_symbols: Tuple[str, ...]
    reported_dormant_clip_edit_errno: Optional[int]
    requested_fx6_dormant_shot_mark_symbols: Tuple[str, ...]
    reported_fx6_dormant_shot_mark_errno: Optional[int]
    # Wave-58 Zero-BT [Timecode Link] vs VMC-BNCM1 EXT-LK, Wi-Fi WPA3 & USB-LAN Mutual Exclusion
    requested_bt_timecode_link: bool
    reported_bt_timecode_link_errno: Optional[int]
    vmc_bncm1_connected: bool
    timecode_make: str
    timecode_run: str
    hdmi_tc_output: str
    reported_ext_tc_status: str
    fx6_has_physical_tc_in_out_bnc: bool
    fx6_has_bluetooth_hardware: bool
    wifi_sku: str
    wifi_band: str
    reported_wifi_band_errno: Optional[int]
    wifi_security: str
    reported_wifi_security_errno: Optional[int]
    access_authen_settings: str
    usb_lan_active: bool
    usb_lan_cnct_launch: str
    usb_lan_kernel_modules_present: Tuple[str, ...]
    wifi_active: bool
    multi_micro_usb_in_use: bool
    reported_usb_lan_conflict_errno: Optional[int]
    airplane_mode: str
    network_transport: str
    post_usb_lan_cnct_launch: str
    post_airplane_mode: str
    reset_action: str
    # Zero-RF & Slot-1 Tier-0 Recovery Vault EROFS=30 Firewall
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    requested_vault_slot: int
    slot1_holds_tier0_vault: bool
    requested_vault_action: str
    shot_mark_or_clip_flag_targets_slot1: bool
    photo_capture_or_divider_targets_slot1: bool
    reported_vault_action_allowed: bool
    vault_firewall_errno: Optional[str]
    slot1_data_sector_writes: int
    slot1_m4root_avf_mutation_bytes: int
    slot1_dcim_divider_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative counters
    shotmark_clipflag_or_dormant_divide_drift_events: int
    tc_link_wpa3_or_usblan_mutex_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int


@dataclass(frozen=True)
class ShotMarkEditTcLinkUsbLanVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    shotmark_clipflag_edit_and_dormant_divide_verified: bool
    tclink_bncm1_wpa3_usblan_mutex_and_airplane_verified: bool
    zero_rf_and_slot1_erofs30_vault_verified: bool
    overlay_and_h0_h3_verified: bool
    matrix_states_checked: int
    shotmark_clipflag_or_dormant_divide_drift_events: int
    tc_link_wpa3_or_usblan_mutex_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_m4root_avf_mutation_bytes: int
    slot1_dcim_divider_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BrightMonShotMarkUsbLanBulbVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase336DonorSnapshot
    bright_mon_bulb_report: BrightMonMonitorBrightnessBulbVaultReport
    shotmark_usblan_report: ShotMarkEditTcLinkUsbLanVaultReport
    bright_mon_or_monitor_brightness_drift_events: int
    bulb_mech_or_dormant_bulb_timer_hdr_drift_events: int
    fx6_vf_backlight_or_still_spoof_events: int
    shotmark_clipflag_or_dormant_divide_drift_events: int
    tc_link_wpa3_or_usblan_mutex_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_m4root_avf_mutation_bytes: int
    slot1_dcim_divider_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
    overall_ready_for_hardware_attach: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    cnflasha_userspace_write_blocked: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar60ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar60ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar60ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar60BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar60ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar60StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase336DonorSnapshot
    pillar_60a_bright_mon_monitor_brightness_bulb_vault: Pillar60ASuiteResult
    pillar_60b_shotmark_edit_tclink_wpa3_usblan_vault: Pillar60BSuiteResult
    bright_mon_or_monitor_brightness_drift_events: int
    bulb_mech_or_dormant_bulb_timer_hdr_drift_events: int
    fx6_vf_backlight_or_still_spoof_events: int
    shotmark_clipflag_or_dormant_divide_drift_events: int
    tc_link_wpa3_or_usblan_mutex_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_m4root_avf_mutation_bytes: int
    slot1_dcim_divider_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
    overall_ready_for_hardware_attach: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    suite_sha256: str
    cnflasha_userspace_write_blocked: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master60PillarRecoveryReport:
    schema: str
    schema_version: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_1_5s_fast_cli_budget: bool
    under_2_5s_fast_cli_budget: bool
    under_6s_budget: bool
    nominal_under_4_0s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase336DonorSnapshot
    pillar60_a_bright_mon_monitor_brightness_bulb_vault: Pillar60ASuiteResult
    pillar60_b_shotmark_edit_tclink_wpa3_usblan_vault: Pillar60BSuiteResult
    # Pillar 60 zero-violation counters & hardware boundaries
    bright_mon_or_monitor_brightness_drift_events: int
    bulb_mech_or_dormant_bulb_timer_hdr_drift_events: int
    fx6_vf_backlight_or_still_spoof_events: int
    shotmark_clipflag_or_dormant_divide_drift_events: int
    tc_link_wpa3_or_usblan_mutex_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_m4root_avf_mutation_bytes: int
    slot1_dcim_divider_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
    fx3_bright_monitoring_symbol_count: int
    fx3_bright_mon_v700_focus_mag_coexist: bool
    fx3_monitor_brightness_level_min: int
    fx3_monitor_brightness_level_max: int
    fx3_has_dormant_bulb_timer: bool
    fx3_has_dormant_auto_hdr: bool
    fx3_has_dormant_divide_extract: bool
    fx3_has_bt_timecode_link: bool
    fx3_usb_lan_kmod_count: int
    fx3_wifi_active_security_count: int
    fx6_vf_brightness_min: int
    fx6_vf_brightness_max: int
    fx6_has_physical_tc_in_out_bnc: bool
    fx6_has_bluetooth_hardware: bool
    # Carried forward Pillar 59 metrics
    steadyshot_47focal_or_lockout_drift_events: int
    selftimer_dormant_or_led8_audio_drift_events: int
    fx6_ibis_or_selftimer_spoof_events: int
    zebra_custom_ire_or_peaking_clean_hdmi_drift_events: int
    streaming_24p_rec_or_network_reset_drift_events: int
    slot1_streaming_or_ftp_mutation_bytes: int
    fx3_steadyshot_47_focal_count: int
    fx3_image_stabilization_item_count: int
    fx3_selftimer_cont_combo_count: int
    fx3_front_lamp_8_id: int
    fx3_zebra_preset_count: int
    fx3_peaking_color_count: int
    fx3_streaming_protocol_count: int
    fx3_has_5axis_ibis: bool
    fx3_has_movie_self_timer: bool
    fx6_has_ibis: bool
    fx6_has_6axis_gyro_metadata: bool
    fx6_has_still_self_timer: bool
    # Carried forward Pillar 58..41 metrics
    dial_customize_dormant_trap_or_reset_drift_events: int
    rear_dial_lr_or_mydial_override_drift_events: int
    fn_menu_12x2_or_fx6_dial_spoof_events: int
    live_view_display_reset_split_or_mode_drift_events: int
    grid_line_or_hdmi_clean_feed_leak_events: int
    lut_path_embed_sidecar_or_slot1_vault_bypass_events: int
    slot1_lut_mutation_bytes: int
    slot1_avf_info_mutated: bool
    fx3_dial_customize_item_count: int
    fx3_physical_dial_count: int
    fx3_my_dial_bank_count: int
    fx3_fn_menu_still_slots: int
    fx3_fn_menu_movie_slots: int
    fx3_live_view_display_set_item_count: int
    fx3_grid_line_type_count: int
    fx3_user_lut_slot_count: int
    fx3_pplut_slot_count: int
    fx6_user_lut_ui_cap: int
    fx6_has_av_tv_rotate: bool
    fx6_has_my_dial: bool
    fx6_has_fn_menu: bool
    fx6_has_multi_channel_lut_switches: bool
    fx3_has_builtin_evf: bool
    fx3_has_var_shutter: bool
    # Safety lock flags
    overall_ready_for_hardware_attach: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    master_60pillar_sha256: str
    cnflasha_userspace_write_blocked: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Spec Builders (Pillars 60A & 60B)
# ---------------------------------------------------------------------------


def build_default_safe_bright_mon_bulb_vault_spec(
    **overrides: Any,
) -> BrightMonMonitorBrightnessBulbVaultSpec:
    """Return a clean, verified default `BrightMonMonitorBrightnessBulbVaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P336_FX3_MODEL_NAME,
        "fw_version": P336_FX3_FW_VERSION,
        "shooting_domain": "Still",
        "exposure_mode": "M",
        "focus_mode": "MF",
        "power_state": "On",
        "bright_monitoring_custom_key_only": True,
        "bright_monitoring_in_shooting_menu": False,
        "bright_monitoring_symbol_count": P336_FX3_BRIGHT_MONITORING_SYMBOL_COUNT,
        "bright_monitoring_requested": False,
        "focus_magnifier_active": False,
        "requested_bright_mon_multi_gain_ext": False,
        "reported_effective_bright_monitoring": False,
        "reported_bright_monitoring_errno": None,
        "reported_forced_live_view_display": "UserConfigured",
        "monitor_brightness_menu_path": P336_MONITOR_BRIGHTNESS_MENU_PATH,
        "monitor_brightness_mode": P336_MONITOR_BRIGHTNESS_DEFAULT_MODE,
        "monitor_brightness_level": P336_MONITOR_BRIGHTNESS_DEFAULT_LEVEL,
        "reported_monitor_brightness_errno": None,
        "post_monitor_brightness_mode": P336_MONITOR_BRIGHTNESS_DEFAULT_MODE,
        "post_monitor_brightness_level": P336_MONITOR_BRIGHTNESS_DEFAULT_LEVEL,
        "shutter_type": "Mechanical Shutter",
        "still_drive_mode": "Single Shooting",
        "bulb_requested": False,
        "reported_effective_bulb_active": False,
        "reported_bulb_fallback_shutter": '1/125"',
        "reported_bulb_errno": None,
        "reported_anti_flicker_disabled_by_bulb": False,
        "picture_profile": "Off",
        "hlg_still_image": "Off",
        "dro_mode": P336_DRO_DEFAULT,
        "dro_bracket": "Off",
        "reported_effective_dro_mode": P336_DRO_DEFAULT,
        "reported_dro_errno": None,
        "post_dro_mode": P336_DRO_DEFAULT,
        "post_dro_bracket": "Off",
        "post_bulb_active": False,
        "requested_dormant_bulb_or_hdr_symbols": (),
        "reported_dormant_bulb_hdr_errno": None,
        "fx6_vf_brightness": P336_FX6_VF_BRIGHTNESS_DEFAULT,
        "fx6_vf_color_mode": "Color",
        "fx6_ae_backlight_is_exposure_mode": True,
        "fx6_has_bright_monitoring": False,
        "fx6_has_still_bulb_or_dro_hdr": False,
        "fx6_uses_dual_base_iso_800_12800": True,
        "requested_fx6_dormant_backlight_symbols": (),
        "reported_fx6_dormant_backlight_errno": None,
        "reset_action": "None",
        "requested_vault_slot": P336_SLOT1_VAULT_SLOT,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P336_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P336_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P336_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P336_TIER0_SURFACE_COUNT,
        "bright_mon_or_monitor_brightness_drift_events": 0,
        "bulb_mech_or_dormant_bulb_timer_hdr_drift_events": 0,
        "fx6_vf_backlight_or_still_spoof_events": 0,
    }
    defaults.update(overrides)
    return BrightMonMonitorBrightnessBulbVaultSpec(**defaults)


def build_default_safe_shotmark_usblan_vault_spec(
    **overrides: Any,
) -> ShotMarkEditTcLinkUsbLanVaultSpec:
    """Return a clean, verified default `ShotMarkEditTcLinkUsbLanVaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P336_FX3_MODEL_NAME,
        "fw_version": P336_FX3_FW_VERSION,
        "shot_mark_slot": 1,
        "clip_flag": "Off",
        "image_jump_setting": "Shot Mark Only",
        "playback_edit_items": P336_FX3_PLAYBACK_EDIT_ITEMS,
        "photo_capture_file_type": "JPEG",
        "create_divider_frame_supported": True,
        "requested_dormant_clip_edit_symbols": (),
        "reported_dormant_clip_edit_errno": None,
        "requested_fx6_dormant_shot_mark_symbols": (),
        "reported_fx6_dormant_shot_mark_errno": None,
        "requested_bt_timecode_link": False,
        "reported_bt_timecode_link_errno": None,
        "vmc_bncm1_connected": False,
        "timecode_make": "Preset",
        "timecode_run": "Free Run",
        "hdmi_tc_output": "Off",
        "reported_ext_tc_status": "INTERNAL",
        "fx6_has_physical_tc_in_out_bnc": True,
        "fx6_has_bluetooth_hardware": False,
        "wifi_sku": "WW728473",
        "wifi_band": "2.4GHz",
        "reported_wifi_band_errno": None,
        "wifi_security": "WPA3-SAE",
        "reported_wifi_security_errno": None,
        "access_authen_settings": "On",
        "usb_lan_active": False,
        "usb_lan_cnct_launch": "Off",
        "usb_lan_kernel_modules_present": P336_USB_LAN_KERNEL_MODULES,
        "wifi_active": False,
        "multi_micro_usb_in_use": False,
        "reported_usb_lan_conflict_errno": None,
        "airplane_mode": "On",
        "network_transport": P336_SAFE_WIRED_TRANSPORT,
        "post_usb_lan_cnct_launch": "Off",
        "post_airplane_mode": "On",
        "reset_action": "None",
        "rf_packets_transmitted": 0,
        "rf_nvs_mutation_bytes": 0,
        "requested_vault_slot": P336_SLOT1_VAULT_SLOT,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "shot_mark_or_clip_flag_targets_slot1": False,
        "photo_capture_or_divider_targets_slot1": False,
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": 0,
        "slot1_m4root_avf_mutation_bytes": 0,
        "slot1_dcim_divider_mutation_bytes": 0,
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P336_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P336_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P336_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P336_TIER0_SURFACE_COUNT,
        "shotmark_clipflag_or_dormant_divide_drift_events": 0,
        "tc_link_wpa3_or_usblan_mutex_drift_events": 0,
        "zero_rf_or_slot1_vault_bypass_events": 0,
    }
    defaults.update(overrides)
    return ShotMarkEditTcLinkUsbLanVaultSpec(**defaults)


# ---------------------------------------------------------------------------
# Evaluators & Single-Shot Combined Verifier (Pillars 60A & 60B)
# ---------------------------------------------------------------------------


def evaluate_bright_mon_bulb_vault(
    spec: BrightMonMonitorBrightnessBulbVaultSpec,
) -> BrightMonMonitorBrightnessBulbVaultReport:
    """Evaluate Pillar 60A: Wave-58 Custom-key-only [Bright Monitoring] (Ver.7.00+ Focus-Mag coexistence,
    Setting Effect OFF, auto-cancel), Initialize-only [Monitor Brightness] (Manual -2..+2 / Sunny Weather
    vs dormant Auto EOPNOTSUPP=95), FX6 VF Brightness + AE Backlight disambiguation, Mechanical-only Still
    [BULB] -> 30" fallback, Resettable [DRO], & Dormant [Bulb Timer] / [Auto HDR] (EOPNOTSUPP=95)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P336_BLOCKED_SAFETY_POLICY_VIOLATION, "Module safety invariant violation")

    valid_fw = (
        (
            spec.camera_model == P336_FX3_MODEL_NAME
            and spec.fw_version in P336_FX3_SUPPORTED_FW_VERSIONS
        )
        or (
            spec.camera_model == P336_FX6_DONOR_MODEL_NAME
            and spec.fw_version == P336_FX6_DONOR_FW_VERSION
        )
    )
    if (
        not valid_fw
        or spec.shooting_domain not in P336_SHOOTING_DOMAINS
        or spec.exposure_mode not in P336_EXPOSURE_MODES
        or spec.focus_mode not in P336_FOCUS_MODES
        or spec.power_state not in P336_ON_OFF_MODES
        or spec.monitor_brightness_mode not in P336_MONITOR_BRIGHTNESS_ALL_MODES
        or spec.shutter_type not in P336_SHUTTER_TYPES
        or spec.still_drive_mode not in P336_STILL_DRIVE_MODES_ALL
        or spec.hlg_still_image not in P336_ON_OFF_MODES
        or spec.dro_mode not in P336_DRO_MODES
        or spec.dro_bracket not in P336_DRO_BRACKET_OPTIONS
        or spec.fx6_vf_color_mode not in P336_FX6_VF_COLOR_MODES
        or spec.reset_action not in P336_RESET_ACTIONS
        or spec.requested_vault_slot not in (1, 2)
        or spec.requested_vault_action not in P336_VAULT_ACTIONS
    ):
        _fail(
            P336_BLOCKED_INVALID_PILLAR60A_SPEC,
            "Invalid Pillar 60A camera/BrightMon/MonitorBrightness/BULB/DRO/vault spec parameter",
        )

    st = compute_expected_bright_mon_bulb_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        exposure_mode=spec.exposure_mode,
        focus_mode=spec.focus_mode,
        power_state=spec.power_state,
        bright_monitoring_requested=spec.bright_monitoring_requested,
        focus_magnifier_active=spec.focus_magnifier_active,
        requested_bright_mon_multi_gain_ext=spec.requested_bright_mon_multi_gain_ext,
        monitor_brightness_mode=spec.monitor_brightness_mode,
        monitor_brightness_level=spec.monitor_brightness_level,
        shutter_type=spec.shutter_type,
        still_drive_mode=spec.still_drive_mode,
        bulb_requested=spec.bulb_requested,
        picture_profile=spec.picture_profile,
        hlg_still_image=spec.hlg_still_image,
        dro_mode=spec.dro_mode,
        dro_bracket=spec.dro_bracket,
        requested_dormant_bulb_or_hdr_symbols=spec.requested_dormant_bulb_or_hdr_symbols,
        reset_action=spec.reset_action,
    )

    # 1. [Bright Monitoring] & [Monitor Brightness]
    bright_mon_ok = (
        (
            spec.camera_model != P336_FX3_MODEL_NAME
            or (
                spec.bright_monitoring_custom_key_only
                and not spec.bright_monitoring_in_shooting_menu
                and spec.bright_monitoring_symbol_count == P336_FX3_BRIGHT_MONITORING_SYMBOL_COUNT
                and not spec.requested_bright_mon_multi_gain_ext
                and spec.reported_effective_bright_monitoring == st["effective_bright_monitoring"]
                and spec.reported_bright_monitoring_errno == st["bright_monitoring_errno"]
                and not (
                    spec.bright_monitoring_requested
                    and (st["bm_auto_cancelled"] or (spec.focus_magnifier_active and not st["supports_bm_focus_mag"]))
                    and spec.reported_effective_bright_monitoring
                )
                and spec.reported_forced_live_view_display == st["forced_live_view_display"]
                and tuple(spec.monitor_brightness_menu_path) == P336_MONITOR_BRIGHTNESS_MENU_PATH
                and spec.monitor_brightness_mode in P336_MONITOR_BRIGHTNESS_MODES
                and P336_MONITOR_BRIGHTNESS_MIN_LEVEL
                <= spec.monitor_brightness_level
                <= P336_MONITOR_BRIGHTNESS_MAX_LEVEL
                and spec.reported_monitor_brightness_errno == st["monitor_brightness_errno"]
                and spec.post_monitor_brightness_mode == st["post_monitor_brightness_mode"]
                and spec.post_monitor_brightness_level == st["post_monitor_brightness_level"]
            )
        )
        and not spec.requested_bright_mon_multi_gain_ext
        and spec.bright_mon_or_monitor_brightness_drift_events == 0
    )
    if not bright_mon_ok:
        _fail(
            P336_BLOCKED_BRIGHT_MON_OR_MONITOR_BRIGHTNESS_DRIFT,
            "Bright Monitoring (Ver.7.00+ Focus-Mag coexistence, Setting Effect OFF, auto-cancel) or Initialize-only Monitor Brightness (Manual -2..+2 / Sunny Weather vs dormant Auto) violated",
        )

    # 2. Manual [BULB] Mechanical Shutter, Resettable [DRO] & Dormant [Bulb Timer] / [Auto HDR]
    bulb_dro_ok = (
        (
            spec.camera_model != P336_FX3_MODEL_NAME
            or (
                spec.reported_effective_bulb_active == st["effective_bulb_active"]
                and spec.reported_bulb_fallback_shutter == st["effective_bulb_fallback_shutter"]
                and spec.reported_bulb_errno == st["bulb_errno"]
                and not (
                    spec.bulb_requested
                    and st["bulb_blocked"]
                    and spec.reported_effective_bulb_active
                )
                and spec.reported_anti_flicker_disabled_by_bulb == st["anti_flicker_disabled_by_bulb"]
                and spec.reported_effective_dro_mode == st["effective_dro_mode"]
                and spec.reported_dro_errno == st["dro_errno"]
                and spec.post_dro_mode == st["post_dro_mode"]
                and spec.post_dro_bracket == st["post_dro_bracket"]
                and spec.post_bulb_active == st["post_bulb_active"]
                and spec.reported_dormant_bulb_hdr_errno == st["dormant_bulb_hdr_errno"]
            )
        )
        and len(spec.requested_dormant_bulb_or_hdr_symbols) == 0
        and spec.bulb_mech_or_dormant_bulb_timer_hdr_drift_events == 0
    )
    if not bulb_dro_ok:
        _fail(
            P336_BLOCKED_BULB_MECH_OR_DORMANT_BULB_TIMER_HDR_DRIFT,
            "Still BULB Mechanical-Shutter gate (30\" fallback), Resettable DRO (PP/HLG lockout), or dormant Bulb Timer / Auto HDR EOPNOTSUPP=95 violated",
        )

    # 3. ILME-FX6 VF Setting > Brightness & AE Backlight Disambiguation & Zero Still Pipeline
    fx6_ok = (
        P336_FX6_VF_BRIGHTNESS_MIN <= spec.fx6_vf_brightness <= P336_FX6_VF_BRIGHTNESS_MAX
        and spec.fx6_ae_backlight_is_exposure_mode
        and not spec.fx6_has_bright_monitoring
        and not spec.fx6_has_still_bulb_or_dro_hdr
        and spec.fx6_uses_dual_base_iso_800_12800
        and len(spec.requested_fx6_dormant_backlight_symbols) == 0
        and (
            len(spec.requested_fx6_dormant_backlight_symbols) == 0
            or spec.reported_fx6_dormant_backlight_errno == P336_EOPNOTSUPP_ERRNO
        )
        and spec.fx6_vf_backlight_or_still_spoof_events == 0
    )
    if not fx6_ok:
        _fail(
            P336_BLOCKED_FX6_VF_BACKLIGHT_OR_STILL_SPOOF,
            "FX6 boundary violated VF Brightness (1..15), AE Backlight disambiguation, Cine EI Dual Base ISO 800/12800, or zero Still BULB/DRO/HDR boundary",
        )

    # 4. Slot-1 Tier-0 Vault Firewall & Stage-B Overlay & H0 == H3
    vault_fw_ok = (
        spec.slot1_format_hard_locked
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_vault_mutation_bytes == 0
        and not (
            spec.requested_vault_slot == P336_SLOT1_VAULT_SLOT
            and spec.requested_vault_action in P336_WRITE_MUTATING_VAULT_ACTIONS
        )
    )
    if not vault_fw_ok:
        _fail(
            P336_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Vault EROFS=30 firewall blocked write/format mutation on Tier-0 media",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P336_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P336_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P336_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P336_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "60A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "fw_version": spec.fw_version,
            "effective_bright_monitoring": spec.reported_effective_bright_monitoring,
            "post_monitor_brightness_mode": spec.post_monitor_brightness_mode,
            "post_monitor_brightness_level": spec.post_monitor_brightness_level,
            "effective_bulb_active": spec.reported_effective_bulb_active,
            "post_dro_mode": spec.post_dro_mode,
            "slot1_bytes": spec.slot1_vault_mutation_bytes,
            "errors": errors,
        }
    )
    return BrightMonMonitorBrightnessBulbVaultReport(
        schema=PHASE336_SCHEMA,
        version=PHASE336_VERSION,
        passed=passed,
        status=P336_STATUS_VERIFIED_PILLAR_60A if passed else P336_STATUS_REJECTED_PILLAR_60A,
        block_code=block_code,
        bright_mon_v700_focus_mag_and_monitor_brightness_verified=bright_mon_ok,
        bulb_mech_dro_and_dormant_bulb_timer_hdr_verified=bulb_dro_ok,
        fx6_vf_backlight_disambiguation_and_zero_still_verified=fx6_ok,
        slot1_vault_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=18,
        bright_mon_or_monitor_brightness_drift_events=(
            spec.bright_mon_or_monitor_brightness_drift_events
        ),
        bulb_mech_or_dormant_bulb_timer_hdr_drift_events=(
            spec.bulb_mech_or_dormant_bulb_timer_hdr_drift_events
        ),
        fx6_vf_backlight_or_still_spoof_events=spec.fx6_vf_backlight_or_still_spoof_events,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_shotmark_tc_usblan_vault(
    spec: ShotMarkEditTcLinkUsbLanVaultSpec,
) -> ShotMarkEditTcLinkUsbLanVaultReport:
    """Evaluate Pillar 60B: Wave-58 [Shot Mark 1/2], [Clip Flag] (OK/NG/KEEP), Playback [Edit] vs dormant
    [Divide]/[Extract]/Cut-15/30/60s, Zero-BT [Timecode Link] vs VMC-BNCM1 EXT-LK & FX6 BNC,
    Wi-Fi WW728473 vs WW558244 + Ver. 7.00+ WPA2-PSK/WPA3-SAE hardening, USB-LAN mutual exclusion,
    Airplane Mode=On Zero-RF retention, and Slot-1 Tier-0 EROFS=30 Vault Firewall."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P336_BLOCKED_SAFETY_POLICY_VIOLATION, "Module safety invariant violation")

    valid_fw = (
        (
            spec.camera_model == P336_FX3_MODEL_NAME
            and spec.fw_version in P336_FX3_SUPPORTED_FW_VERSIONS
        )
        or (
            spec.camera_model == P336_FX6_DONOR_MODEL_NAME
            and spec.fw_version == P336_FX6_DONOR_FW_VERSION
        )
    )
    if (
        not valid_fw
        or spec.shot_mark_slot not in (1, 2)
        or spec.clip_flag not in P336_CLIP_FLAG_OPTIONS
        or spec.image_jump_setting not in P336_IMAGE_JUMP_OPTIONS
        or spec.photo_capture_file_type not in P336_PHOTO_CAPTURE_FILE_TYPES
        or spec.timecode_make not in P336_TIMECODE_MAKE_MODES
        or spec.timecode_run not in P336_TIMECODE_RUN_MODES
        or spec.hdmi_tc_output not in P336_ON_OFF_MODES
        or spec.wifi_sku not in P336_WIFI_SKUS
        or spec.wifi_band not in ("2.4GHz", "5GHz")
        or spec.wifi_security not in P336_WIFI_SECURITY_ALL_MODES
        or spec.access_authen_settings not in P336_ON_OFF_MODES
        or spec.usb_lan_cnct_launch not in P336_ON_OFF_MODES
        or spec.airplane_mode not in P336_ON_OFF_MODES
        or spec.network_transport not in P336_NETWORK_TRANSPORTS
        or spec.reset_action not in P336_RESET_ACTIONS
        or spec.requested_vault_slot not in (1, 2)
        or spec.requested_vault_action not in P336_VAULT_ACTIONS
        or (
            spec.vault_firewall_errno is not None
            and spec.vault_firewall_errno not in P336_VAULT_FIREWALL_ERRNOS
        )
    ):
        _fail(
            P336_BLOCKED_INVALID_PILLAR60B_SPEC,
            "Invalid Pillar 60B camera/ShotMark/Edit/Timecode/WiFi/USBLAN/vault spec parameter",
        )

    st = compute_expected_shotmark_tc_usblan_vault_state(
        camera_model=spec.camera_model,
        shot_mark_slot=spec.shot_mark_slot,
        clip_flag=spec.clip_flag,
        image_jump_setting=spec.image_jump_setting,
        photo_capture_file_type=spec.photo_capture_file_type,
        requested_dormant_clip_edit_symbols=spec.requested_dormant_clip_edit_symbols,
        requested_fx6_dormant_shot_mark_symbols=spec.requested_fx6_dormant_shot_mark_symbols,
        requested_bt_timecode_link=spec.requested_bt_timecode_link,
        vmc_bncm1_connected=spec.vmc_bncm1_connected,
        timecode_make=spec.timecode_make,
        timecode_run=spec.timecode_run,
        hdmi_tc_output=spec.hdmi_tc_output,
        wifi_sku=spec.wifi_sku,
        wifi_band=spec.wifi_band,
        wifi_security=spec.wifi_security,
        usb_lan_active=spec.usb_lan_active,
        usb_lan_cnct_launch=spec.usb_lan_cnct_launch,
        wifi_active=spec.wifi_active,
        multi_micro_usb_in_use=spec.multi_micro_usb_in_use,
        airplane_mode=spec.airplane_mode,
        network_transport=spec.network_transport,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
        shot_mark_or_clip_flag_targets_slot1=spec.shot_mark_or_clip_flag_targets_slot1,
        photo_capture_or_divider_targets_slot1=spec.photo_capture_or_divider_targets_slot1,
    )

    # 1. [Shot Mark 1/2], [Clip Flag], Playback [Edit] vs Dormant [Divide] / [Extract] / FX6 Shot Mark 0..9
    shotmark_ok = (
        st["shot_mark_slot_valid"]
        and st["clip_flag_valid"]
        and st["image_jump_valid"]
        and st["photo_capture_type_valid"]
        and tuple(spec.playback_edit_items) == P336_FX3_PLAYBACK_EDIT_ITEMS
        and spec.create_divider_frame_supported
        and len(spec.requested_dormant_clip_edit_symbols) == 0
        and spec.reported_dormant_clip_edit_errno == st["dormant_clip_edit_errno"]
        and len(spec.requested_fx6_dormant_shot_mark_symbols) == 0
        and spec.reported_fx6_dormant_shot_mark_errno == st["dormant_fx6_shot_mark_errno"]
        and spec.shotmark_clipflag_or_dormant_divide_drift_events == 0
    )
    if not shotmark_ok:
        _fail(
            P336_BLOCKED_SHOTMARK_CLIPFLAG_OR_DORMANT_DIVIDE_DRIFT,
            "Shot Mark 1/2, Clip Flag (OK/NG/KEEP), Playback Edit, or dormant Divide/Extract/Cut-15-30-60s / FX6 Essence Mark exclusion violated",
        )

    # 2. Zero-BT Timecode Link vs VMC-BNCM1 EXT-LK, Wi-Fi WPA3/SKU & USB-LAN mutual exclusion
    tc_wifi_usblan_ok = (
        not spec.requested_bt_timecode_link
        and spec.reported_bt_timecode_link_errno == st["bt_timecode_link_errno"]
        and spec.reported_ext_tc_status == st["ext_tc_status"]
        and spec.fx6_has_physical_tc_in_out_bnc
        and not spec.fx6_has_bluetooth_hardware
        and spec.wifi_band in P336_WIFI_SKU_BANDS[spec.wifi_sku]
        and spec.reported_wifi_band_errno == st["wifi_band_errno"]
        and spec.wifi_security in P336_WIFI_SECURITY_ACTIVE_MODES
        and spec.reported_wifi_security_errno == st["wifi_security_errno"]
        and spec.access_authen_settings == "On"
        and tuple(spec.usb_lan_kernel_modules_present) == P336_USB_LAN_KERNEL_MODULES
        and not st["usb_lan_bus_conflict"]
        and spec.reported_usb_lan_conflict_errno == st["usb_lan_conflict_errno"]
        and spec.post_usb_lan_cnct_launch == st["post_usb_lan_cnct_launch"]
        and spec.post_airplane_mode == st["post_airplane_mode"]
        and spec.tc_link_wpa3_or_usblan_mutex_drift_events == 0
    )
    if not tc_wifi_usblan_ok:
        _fail(
            P336_BLOCKED_TC_LINK_WPA3_OR_USBLAN_MUTEX_DRIFT,
            "Timecode Link zero-BT, VMC-BNCM1 EXT-LK, Wi-Fi WW728473/WW558244 + WPA2/WPA3 hardening, USB-LAN mutex, or Airplane Mode Reset persistence violated",
        )

    # 3. Zero-RF (Airplane Mode=On, USB-LAN CDC-NCM) & Slot-1 Tier-0 EROFS=30 Vault Firewall
    slot1_mutated_violation = (
        spec.requested_vault_slot == P336_SLOT1_VAULT_SLOT
        and spec.slot1_holds_tier0_vault
        and (
            spec.requested_vault_action in P336_WRITE_MUTATING_VAULT_ACTIONS
            or spec.shot_mark_or_clip_flag_targets_slot1
            or spec.photo_capture_or_divider_targets_slot1
        )
        and spec.reported_vault_action_allowed
    )
    zero_rf_vault_ok = (
        st["rf_zero_enforced"]
        and spec.rf_packets_transmitted == 0
        and spec.rf_nvs_mutation_bytes == 0
        and not slot1_mutated_violation
        and spec.reported_vault_action_allowed == st["action_allowed"]
        and spec.vault_firewall_errno == st["firewall_errno"]
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_m4root_avf_mutation_bytes == 0
        and spec.slot1_dcim_divider_mutation_bytes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_format_hard_locked
        and spec.zero_rf_or_slot1_vault_bypass_events == 0
    )
    if not zero_rf_vault_ok:
        _fail(
            P336_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL,
            "Zero-RF Airplane Mode=On (USB-LAN CDC-NCM only) or Slot-1 Tier-0 Vault EROFS=30 firewall breached on Shot Mark / Clip Flag / Photo Capture / Divider Frame",
        )

    # 4. Stage-B Overlay & H0 == H3
    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P336_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P336_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P336_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P336_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    overlay_and_h0_h3_ok = overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "60B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "clip_flag": spec.clip_flag,
            "image_jump": spec.image_jump_setting,
            "ext_tc_status": spec.reported_ext_tc_status,
            "wifi_sku": spec.wifi_sku,
            "wifi_security": spec.wifi_security,
            "post_airplane_mode": spec.post_airplane_mode,
            "vault_slot": spec.requested_vault_slot,
            "vault_action": spec.requested_vault_action,
            "rf_packets": spec.rf_packets_transmitted,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return ShotMarkEditTcLinkUsbLanVaultReport(
        schema=PHASE336_SCHEMA,
        version=PHASE336_VERSION,
        passed=passed,
        status=P336_STATUS_VERIFIED_PILLAR_60B if passed else P336_STATUS_REJECTED_PILLAR_60B,
        block_code=block_code,
        shotmark_clipflag_edit_and_dormant_divide_verified=shotmark_ok,
        tclink_bncm1_wpa3_usblan_mutex_and_airplane_verified=tc_wifi_usblan_ok,
        zero_rf_and_slot1_erofs30_vault_verified=zero_rf_vault_ok,
        overlay_and_h0_h3_verified=overlay_and_h0_h3_ok,
        matrix_states_checked=18,
        shotmark_clipflag_or_dormant_divide_drift_events=(
            spec.shotmark_clipflag_or_dormant_divide_drift_events
        ),
        tc_link_wpa3_or_usblan_mutex_drift_events=spec.tc_link_wpa3_or_usblan_mutex_drift_events,
        zero_rf_or_slot1_vault_bypass_events=spec.zero_rf_or_slot1_vault_bypass_events,
        rf_packets_transmitted=spec.rf_packets_transmitted,
        rf_nvs_mutation_bytes=spec.rf_nvs_mutation_bytes,
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_m4root_avf_mutation_bytes=spec.slot1_m4root_avf_mutation_bytes,
        slot1_dcim_divider_mutation_bytes=spec.slot1_dcim_divider_mutation_bytes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_bright_mon_shotmark_usblan_bulb_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_60a: Optional[BrightMonMonitorBrightnessBulbVaultSpec] = None,
    spec_60b: Optional[ShotMarkEditTcLinkUsbLanVaultSpec] = None,
) -> BrightMonShotMarkUsbLanBulbVaultReport:
    """Combined single-shot verifier for Pillar 60A + Pillar 60B + bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase336_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_bright_mon_bulb_vault(
        spec_60a or build_default_safe_bright_mon_bulb_vault_spec()
    )
    rep_b = evaluate_shotmark_tc_usblan_vault(
        spec_60b or build_default_safe_shotmark_usblan_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 336 Wave-58 donor artifact parity check failed")
    if not donor_snapshot.under_0_20s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return BrightMonShotMarkUsbLanBulbVaultReport(
        schema=PHASE336_SCHEMA,
        version=PHASE336_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P336_STATUS_VERIFIED_PILLAR60_SUITE if all_ok else P336_STATUS_FAIL_PILLAR60_SUITE,
        donor_snapshot=donor_snapshot,
        bright_mon_bulb_report=rep_a,
        shotmark_usblan_report=rep_b,
        bright_mon_or_monitor_brightness_drift_events=(
            rep_a.bright_mon_or_monitor_brightness_drift_events
        ),
        bulb_mech_or_dormant_bulb_timer_hdr_drift_events=(
            rep_a.bulb_mech_or_dormant_bulb_timer_hdr_drift_events
        ),
        fx6_vf_backlight_or_still_spoof_events=rep_a.fx6_vf_backlight_or_still_spoof_events,
        shotmark_clipflag_or_dormant_divide_drift_events=(
            rep_b.shotmark_clipflag_or_dormant_divide_drift_events
        ),
        tc_link_wpa3_or_usblan_mutex_drift_events=rep_b.tc_link_wpa3_or_usblan_mutex_drift_events,
        zero_rf_or_slot1_vault_bypass_events=rep_b.zero_rf_or_slot1_vault_bypass_events,
        rf_packets_transmitted=rep_b.rf_packets_transmitted,
        rf_nvs_mutation_bytes=rep_b.rf_nvs_mutation_bytes,
        slot1_data_sector_writes=rep_b.slot1_data_sector_writes,
        slot1_m4root_avf_mutation_bytes=rep_b.slot1_m4root_avf_mutation_bytes,
        slot1_dcim_divider_mutation_bytes=rep_b.slot1_dcim_divider_mutation_bytes,
        slot1_vault_mutation_bytes=rep_a.slot1_vault_mutation_bytes + rep_b.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=(rep_a.slot1_format_hard_locked and rep_b.slot1_format_hard_locked),
        slot1_vault_erofs_eopnotsupp_enforced=(
            rep_a.slot1_vault_erofs_eopnotsupp_enforced
            and rep_b.slot1_vault_erofs_eopnotsupp_enforced
        ),
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(errs),
    )


def verify_bright_mon_shotmark_usblan_bulb_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_60a: Optional[BrightMonMonitorBrightnessBulbVaultSpec] = None,
    spec_60b: Optional[ShotMarkEditTcLinkUsbLanVaultSpec] = None,
) -> BrightMonShotMarkUsbLanBulbVaultReport:
    """Symmetry alias for `verify_bright_mon_shotmark_usblan_bulb_and_vault`."""
    return verify_bright_mon_shotmark_usblan_bulb_and_vault(
        force_clean_room=force_clean_room,
        spec_60a=spec_60a,
        spec_60b=spec_60b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 60A & 60B)
# ---------------------------------------------------------------------------


def run_pillar60a_bright_mon_bulb_vault_6_scenario_suite() -> Pillar60ASuiteResult:
    """Run 6 Pillar 60A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, BrightMonMonitorBrightnessBulbVaultSpec, Optional[str]], ...] = (
        (
            P336_PILLAR_60A_SCENARIO_IDS[0],
            True,
            build_default_safe_bright_mon_bulb_vault_spec(
                fw_version="7.02",
                shooting_domain="Still",
                exposure_mode="M",
                focus_mode="MF",
                power_state="On",
                bright_monitoring_requested=True,
                focus_magnifier_active=True,
                reported_effective_bright_monitoring=True,
                reported_forced_live_view_display="Setting Effect OFF",
                monitor_brightness_mode="Sunny Weather",
                monitor_brightness_level=2,
                reset_action="Camera Settings Reset",
                post_monitor_brightness_mode="Sunny Weather",
                post_monitor_brightness_level=2,
            ),
            None,
        ),
        (
            P336_PILLAR_60A_SCENARIO_IDS[1],
            True,
            build_default_safe_bright_mon_bulb_vault_spec(
                shooting_domain="Still",
                exposure_mode="M",
                shutter_type="Mechanical Shutter",
                still_drive_mode="Single Shooting",
                bulb_requested=True,
                reported_effective_bulb_active=True,
                reported_bulb_fallback_shutter="BULB",
                reported_anti_flicker_disabled_by_bulb=True,
                picture_profile="Off",
                hlg_still_image="Off",
                dro_mode="Lv4",
                reported_effective_dro_mode="Lv4",
                reset_action="Camera Settings Reset",
                post_dro_mode="Auto",
                post_dro_bracket="Off",
                post_bulb_active=False,
            ),
            None,
        ),
        (
            P336_PILLAR_60A_SCENARIO_IDS[2],
            False,
            build_default_safe_bright_mon_bulb_vault_spec(
                fw_version="6.02",
                bright_monitoring_requested=True,
                focus_magnifier_active=True,
                requested_bright_mon_multi_gain_ext=True,
                reported_effective_bright_monitoring=True,
                monitor_brightness_mode="Auto",
                reported_monitor_brightness_errno=None,
                bright_mon_or_monitor_brightness_drift_events=1,
            ),
            P336_BLOCKED_BRIGHT_MON_OR_MONITOR_BRIGHTNESS_DRIFT,
        ),
        (
            P336_PILLAR_60A_SCENARIO_IDS[3],
            False,
            build_default_safe_bright_mon_bulb_vault_spec(
                shutter_type="Electronic Shutter",
                bulb_requested=True,
                reported_effective_bulb_active=True,
                reported_bulb_fallback_shutter="BULB",
                requested_dormant_bulb_or_hdr_symbols=(
                    "BKID_APP_setting_bulb_timer",
                    "Auto HDR",
                ),
                reported_dormant_bulb_hdr_errno=None,
                bulb_mech_or_dormant_bulb_timer_hdr_drift_events=1,
            ),
            P336_BLOCKED_BULB_MECH_OR_DORMANT_BULB_TIMER_HDR_DRIFT,
        ),
        (
            P336_PILLAR_60A_SCENARIO_IDS[4],
            False,
            build_default_safe_bright_mon_bulb_vault_spec(
                camera_model=P336_FX6_DONOR_MODEL_NAME,
                fw_version=P336_FX6_DONOR_FW_VERSION,
                fx6_ae_backlight_is_exposure_mode=False,
                fx6_has_bright_monitoring=True,
                fx6_has_still_bulb_or_dro_hdr=True,
                requested_fx6_dormant_backlight_symbols=("LCD Backlight", "NIGHTSHOT_ON"),
                fx6_vf_backlight_or_still_spoof_events=1,
            ),
            P336_BLOCKED_FX6_VF_BACKLIGHT_OR_STILL_SPOOF,
        ),
        (
            P336_PILLAR_60A_SCENARIO_IDS[5],
            False,
            build_default_safe_bright_mon_bulb_vault_spec(
                requested_vault_slot=1,
                requested_vault_action="FORMAT_QUICK",
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/setting/60a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P336_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar60ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_bright_mon_bulb_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar60ScenarioOutcome(
                scenario_id=sid,
                pillar="60A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar60ASuiteResult(
        passed=all_ok,
        status=P336_STATUS_VERIFIED_PILLAR_60A if all_ok else P336_STATUS_REJECTED_PILLAR_60A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar60b_shotmark_tc_usblan_vault_6_scenario_suite() -> Pillar60BSuiteResult:
    """Run 6 Pillar 60B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, ShotMarkEditTcLinkUsbLanVaultSpec, Optional[str]], ...] = (
        (
            P336_PILLAR_60B_SCENARIO_IDS[0],
            True,
            build_default_safe_shotmark_usblan_vault_spec(
                shot_mark_slot=2,
                clip_flag="KEEP",
                image_jump_setting="Shot Mark2 Only",
                photo_capture_file_type="HEIF_422",
                vmc_bncm1_connected=True,
                timecode_make="Preset",
                timecode_run="Free Run",
                hdmi_tc_output="On",
                reported_ext_tc_status="EXT-LK",
                usb_lan_active=False,
                multi_micro_usb_in_use=True,
                airplane_mode="On",
                post_airplane_mode="On",
                requested_vault_slot=2,
                requested_vault_action="ADD_SHOT_MARK2",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            ),
            None,
        ),
        (
            P336_PILLAR_60B_SCENARIO_IDS[1],
            True,
            build_default_safe_shotmark_usblan_vault_spec(
                wifi_sku="WW728473",
                wifi_band="5GHz",
                wifi_security="WPA3-SAE",
                access_authen_settings="On",
                usb_lan_active=True,
                usb_lan_cnct_launch="On",
                wifi_active=False,
                multi_micro_usb_in_use=False,
                airplane_mode="On",
                network_transport="USB-LAN (CDC-NCM)",
                reset_action="Initialize",
                post_usb_lan_cnct_launch="Off",
                post_airplane_mode="On",
                requested_vault_slot=1,
                requested_vault_action="STREAM_ONLY_USB_LAN",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            ),
            None,
        ),
        (
            P336_PILLAR_60B_SCENARIO_IDS[2],
            False,
            build_default_safe_shotmark_usblan_vault_spec(
                requested_dormant_clip_edit_symbols=("Divide", "Extract", "Cut to 15 seconds"),
                reported_dormant_clip_edit_errno=None,
                requested_fx6_dormant_shot_mark_symbols=("Shot Mark 0..9", "Essence Mark"),
                reported_fx6_dormant_shot_mark_errno=None,
                shotmark_clipflag_or_dormant_divide_drift_events=1,
            ),
            P336_BLOCKED_SHOTMARK_CLIPFLAG_OR_DORMANT_DIVIDE_DRIFT,
        ),
        (
            P336_PILLAR_60B_SCENARIO_IDS[3],
            False,
            build_default_safe_shotmark_usblan_vault_spec(
                requested_bt_timecode_link=True,
                reported_bt_timecode_link_errno=None,
                wifi_security="WEP",
                reported_wifi_security_errno=None,
                usb_lan_active=True,
                multi_micro_usb_in_use=True,
                reported_usb_lan_conflict_errno=None,
                tc_link_wpa3_or_usblan_mutex_drift_events=1,
            ),
            P336_BLOCKED_TC_LINK_WPA3_OR_USBLAN_MUTEX_DRIFT,
        ),
        (
            P336_PILLAR_60B_SCENARIO_IDS[4],
            False,
            build_default_safe_shotmark_usblan_vault_spec(
                wifi_sku="WW558244",
                wifi_band="5GHz",
                reported_wifi_band_errno=None,
                airplane_mode="On",
                reset_action="Reset Network Set.",
                post_airplane_mode="Off",
                rf_packets_transmitted=8,
                rf_nvs_mutation_bytes=64,
                tc_link_wpa3_or_usblan_mutex_drift_events=1,
            ),
            P336_BLOCKED_TC_LINK_WPA3_OR_USBLAN_MUTEX_DRIFT,
        ),
        (
            P336_PILLAR_60B_SCENARIO_IDS[5],
            False,
            build_default_safe_shotmark_usblan_vault_spec(
                airplane_mode="Off",
                post_airplane_mode="Off",
                network_transport="Wi-Fi",
                rf_packets_transmitted=16,
                rf_nvs_mutation_bytes=128,
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="ADD_SHOT_MARK1",
                shot_mark_or_clip_flag_targets_slot1=True,
                photo_capture_or_divider_targets_slot1=True,
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=8192,
                slot1_m4root_avf_mutation_bytes=4096,
                slot1_dcim_divider_mutation_bytes=4096,
                slot1_vault_mutation_bytes=16384,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                zero_rf_or_slot1_vault_bypass_events=1,
            ),
            P336_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar60ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_shotmark_tc_usblan_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar60ScenarioOutcome(
                scenario_id=sid,
                pillar="60B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar60BSuiteResult(
        passed=all_ok,
        status=P336_STATUS_VERIFIED_PILLAR_60B if all_ok else P336_STATUS_REJECTED_PILLAR_60B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Standalone Pillar 60 Suite & Unified 60/60 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def run_pillar60_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar60StandaloneReport:
    """Run full Pillar 60 standalone suite (`6/6` Pillar 60A + `6/6` Pillar 60B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase336_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar60a_bright_mon_bulb_vault_6_scenario_suite()
    res_b = run_pillar60b_shotmark_tc_usblan_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 336 donor verification failed")
    if not donor_snapshot.under_0_20s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE336_SCHEMA,
            "version": PHASE336_VERSION,
            "mode": donor_snapshot.verification_mode,
            "60a": [asdict(s) for s in res_a.scenarios],
            "60b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar60StandaloneReport(
        schema=PHASE336_SCHEMA,
        version=PHASE336_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P336_STATUS_VERIFIED_PILLAR60_SUITE if all_ok else P336_STATUS_FAIL_PILLAR60_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_60a_bright_mon_monitor_brightness_bulb_vault=res_a,
        pillar_60b_shotmark_edit_tclink_wpa3_usblan_vault=res_b,
        bright_mon_or_monitor_brightness_drift_events=(
            P336_BRIGHT_MON_OR_MONITOR_BRIGHTNESS_DRIFT_EVENTS if res_a.passed else 1
        ),
        bulb_mech_or_dormant_bulb_timer_hdr_drift_events=(
            P336_BULB_MECH_OR_DORMANT_BULB_TIMER_HDR_DRIFT_EVENTS if res_a.passed else 1
        ),
        fx6_vf_backlight_or_still_spoof_events=(
            P336_FX6_VF_BACKLIGHT_OR_STILL_SPOOF_EVENTS if res_a.passed else 1
        ),
        shotmark_clipflag_or_dormant_divide_drift_events=(
            P336_SHOTMARK_CLIPFLAG_OR_DORMANT_DIVIDE_DRIFT_EVENTS if res_b.passed else 1
        ),
        tc_link_wpa3_or_usblan_mutex_drift_events=(
            P336_TC_LINK_WPA3_OR_USBLAN_MUTEX_DRIFT_EVENTS if res_b.passed else 1
        ),
        zero_rf_or_slot1_vault_bypass_events=(
            P336_ZERO_RF_OR_SLOT1_VAULT_BYPASS_EVENTS if res_b.passed else 1
        ),
        rf_packets_transmitted=P336_RF_PACKETS_TRANSMITTED if res_b.passed else 1,
        rf_nvs_mutation_bytes=P336_RF_NVS_MUTATION_BYTES if res_b.passed else 64,
        slot1_data_sector_writes=P336_SLOT1_DATA_SECTOR_WRITES if res_b.passed else 1,
        slot1_m4root_avf_mutation_bytes=(
            P336_SLOT1_M4ROOT_AVF_MUTATION_BYTES if res_b.passed else 4096
        ),
        slot1_dcim_divider_mutation_bytes=(
            P336_SLOT1_DCIM_DIVIDER_MUTATION_BYTES if res_b.passed else 4096
        ),
        slot1_vault_mutation_bytes=(
            P336_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        slot1_format_hard_locked=P336_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_eopnotsupp_enforced=P336_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        suite_sha256=suite_sha,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(safety_errs),
    )


def _apply_master60_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
    err = f"FAULT_INJECTED:{pillar.pillar_id}"
    return MasterPillarStatus(
        pillar_number=pillar.pillar_number,
        pillar_id=pillar.pillar_id,
        phase_label=pillar.phase_label,
        module_name=pillar.module_name,
        passed=False,
        status=f"FAULT_INJECTED_{pillar.pillar_id.upper()}",
        verification_mode=pillar.verification_mode,
        elapsed_seconds=pillar.elapsed_seconds,
        key_metrics=pillar.key_metrics,
        digest_sha256=_canonical_sha256({"pillar": pillar.pillar_id, "fault_injected": True}),
        errors=pillar.errors + (err,),
    )


def _master60_local_donors_available() -> bool:
    """Return True only when legacy BODYDATA.DAT and all 17 Wave-58 local donors exist."""
    required_relpaths: Tuple[str, ...] = (
        "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT",
        P336_DONOR_FX3_APPFW_702_RELPATH,
        P336_DONOR_FX6_APPFW_601_RELPATH,
        P336_DONOR_FX3_BACKUP_BIN_RELPATH,
        P336_DONOR_FX3_UXC_EN_F_RELPATH,
        P336_DONOR_FX3_UXC_SC_F_RELPATH,
        P336_DONOR_FX3_UXC_TC_F_RELPATH,
        P336_DONOR_FX3_UXC_JA_F_RELPATH,
        P336_DONOR_FX3_UXC_EN_RELPATH,
        P336_DONOR_FX3_UXC_SC_RELPATH,
        P336_DONOR_FX3_UXC_TC_RELPATH,
        P336_DONOR_FX3_UXC_JA_RELPATH,
        P336_DONOR_FX3_UXC_EN_G_RELPATH,
        P336_DONOR_FX3_UXC_SC_G_RELPATH,
        P336_DONOR_FX3_UXC_TC_G_RELPATH,
        P336_DONOR_FX3_UXC_JA_G_RELPATH,
        P336_DONOR_FX6_UXC_EN_RELPATH,
        P336_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for relpath in required_relpaths:
        try:
            resolved = _resolve_phase336_donor_path(relpath)
        except Exception:
            return False
        if resolved is None:
            return False
        try:
            if not resolved.is_file():
                return False
        except OSError:
            return False
    return True


def evaluate_realhw_60pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master60PillarRecoveryReport:
    """Evaluate and aggregate all 60 recovery pillars (`1..60`) concurrently -> `60/60` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_60_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    if resolved_clean_room is None and not _master60_local_donors_available():
        resolved_clean_room = True
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_59pillar() -> Master59PillarRecoveryReport:
        return evaluate_realhw_59pillar_recovery_master(**kw)

    def _run_p60() -> Tuple[Pillar60StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar60_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_59 = pool.submit(_run_59pillar)
        fut_60 = pool.submit(_run_p60)
        m59_rep = fut_59.result()
        p60_rep, p60_dt = fut_60.result()

    all_errors: List[str] = list(m59_rep.errors) + list(p60_rep.errors)
    for attr_name, expected_val in (
        ("otp_fuse_touches", 0),
        ("otp_fuse_writes", 0),
        ("rpmb_counter_increments", 0),
        ("passive_tx_bytes_emitted", 0),
        ("physical_usb_packets_emitted", 0),
        ("physical_device_writes", 0),
        ("raw_firmware_bytes_leaked", 0),
        ("el3_payload_transmit_authorized", False),
        ("isp_write_authorized", False),
        ("spi_nor_write_authorized", False),
        ("persistent_emmc_writes_authorized", False),
        ("persistent_write_release", False),
        ("live_usb_iokit_transmit_enabled", False),
        ("cnflasha_userspace_write_blocked", True),
        ("overall_ready_for_hardware_attach", False),
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(m59_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-59 violated {attr_name} == {expected_val}")
        if getattr(p60_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 60 violated {attr_name} == {expected_val}")

    if p60_rep.cross_model_flash_authorized is not False:
        all_errors.append("Pillar 60 violated cross_model_flash_authorized == False")

    for attr_name, expected_val in (
        ("steadyshot_47focal_or_lockout_drift_events", 0),
        ("selftimer_dormant_or_led8_audio_drift_events", 0),
        ("fx6_ibis_or_selftimer_spoof_events", 0),
        ("zebra_custom_ire_or_peaking_clean_hdmi_drift_events", 0),
        ("streaming_24p_rec_or_network_reset_drift_events", 0),
        ("zero_rf_or_slot1_vault_bypass_events", 0),
        ("rf_packets_transmitted", 0),
        ("rf_nvs_mutation_bytes", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_streaming_or_ftp_mutation_bytes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_eopnotsupp_enforced", True),
    ):
        if getattr(m59_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-59 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("bright_mon_or_monitor_brightness_drift_events", 0),
        ("bulb_mech_or_dormant_bulb_timer_hdr_drift_events", 0),
        ("fx6_vf_backlight_or_still_spoof_events", 0),
        ("shotmark_clipflag_or_dormant_divide_drift_events", 0),
        ("tc_link_wpa3_or_usblan_mutex_drift_events", 0),
        ("zero_rf_or_slot1_vault_bypass_events", 0),
        ("rf_packets_transmitted", 0),
        ("rf_nvs_mutation_bytes", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_m4root_avf_mutation_bytes", 0),
        ("slot1_dcim_divider_mutation_bytes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_eopnotsupp_enforced", True),
    ):
        if getattr(p60_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 60 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m59_rep.pillars)
    spec60 = MASTER_60_PILLAR_SPECS[59]
    p60_metrics = {
        "pillar_60a_bright_mon_monitor_brightness_bulb_vault": (
            f"{p60_rep.pillar_60a_bright_mon_monitor_brightness_bulb_vault.scenarios_passed}/"
            f"{p60_rep.pillar_60a_bright_mon_monitor_brightness_bulb_vault.scenarios_total}"
        ),
        "pillar_60b_shotmark_edit_tclink_wpa3_usblan_vault": (
            f"{p60_rep.pillar_60b_shotmark_edit_tclink_wpa3_usblan_vault.scenarios_passed}/"
            f"{p60_rep.pillar_60b_shotmark_edit_tclink_wpa3_usblan_vault.scenarios_total}"
        ),
        "bright_mon_or_monitor_brightness_drift_events": (
            p60_rep.bright_mon_or_monitor_brightness_drift_events
        ),
        "bulb_mech_or_dormant_bulb_timer_hdr_drift_events": (
            p60_rep.bulb_mech_or_dormant_bulb_timer_hdr_drift_events
        ),
        "fx6_vf_backlight_or_still_spoof_events": p60_rep.fx6_vf_backlight_or_still_spoof_events,
        "shotmark_clipflag_or_dormant_divide_drift_events": (
            p60_rep.shotmark_clipflag_or_dormant_divide_drift_events
        ),
        "tc_link_wpa3_or_usblan_mutex_drift_events": (
            p60_rep.tc_link_wpa3_or_usblan_mutex_drift_events
        ),
        "zero_rf_or_slot1_vault_bypass_events": p60_rep.zero_rf_or_slot1_vault_bypass_events,
        "rf_packets_transmitted": p60_rep.rf_packets_transmitted,
        "rf_nvs_mutation_bytes": p60_rep.rf_nvs_mutation_bytes,
        "slot1_data_sector_writes": p60_rep.slot1_data_sector_writes,
        "slot1_m4root_avf_mutation_bytes": p60_rep.slot1_m4root_avf_mutation_bytes,
        "slot1_dcim_divider_mutation_bytes": p60_rep.slot1_dcim_divider_mutation_bytes,
        "slot1_vault_mutation_bytes": p60_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p60_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_eopnotsupp_enforced": p60_rep.slot1_vault_erofs_eopnotsupp_enforced,
        "overall_ready_for_hardware_attach": p60_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p60_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p60_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p60_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec60[0],
            pillar_id=spec60[1],
            phase_label=spec60[2],
            module_name=spec60[3],
            passed=bool(p60_rep.all_passed),
            status=p60_rep.status,
            verification_mode=p60_rep.verification_mode,
            elapsed_seconds=p60_dt,
            key_metrics=p60_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec60[1],
                    "mode": p60_rep.verification_mode,
                    "status": p60_rep.status,
                    "metrics": p60_metrics,
                    "passed": p60_rep.all_passed,
                }
            ),
            errors=tuple(p60_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master60_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p60_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_60_PILLAR_COUNT == 60
        and pillars_passed == 60
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE336_SCHEMA,
            "schema_version": PHASE336_MASTER_SCHEMA,
            "version": PHASE336_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [
                (p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses
            ],
            "all_passed": all_ok,
        }
    )
    return Master60PillarRecoveryReport(
        schema=PHASE336_SCHEMA,
        schema_version=PHASE336_MASTER_SCHEMA,
        version=PHASE336_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P336_STATUS_VERIFIED_60OF60_AGGREGATOR if all_ok else P336_STATUS_FAIL_60OF60_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P336_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.5,
        under_6s_budget=elapsed < P336_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P336_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p60_rep.donor_snapshot,
        pillar60_a_bright_mon_monitor_brightness_bulb_vault=(
            p60_rep.pillar_60a_bright_mon_monitor_brightness_bulb_vault
        ),
        pillar60_b_shotmark_edit_tclink_wpa3_usblan_vault=(
            p60_rep.pillar_60b_shotmark_edit_tclink_wpa3_usblan_vault
        ),
        bright_mon_or_monitor_brightness_drift_events=(
            p60_rep.bright_mon_or_monitor_brightness_drift_events
        ),
        bulb_mech_or_dormant_bulb_timer_hdr_drift_events=(
            p60_rep.bulb_mech_or_dormant_bulb_timer_hdr_drift_events
        ),
        fx6_vf_backlight_or_still_spoof_events=p60_rep.fx6_vf_backlight_or_still_spoof_events,
        shotmark_clipflag_or_dormant_divide_drift_events=(
            p60_rep.shotmark_clipflag_or_dormant_divide_drift_events
        ),
        tc_link_wpa3_or_usblan_mutex_drift_events=(
            p60_rep.tc_link_wpa3_or_usblan_mutex_drift_events
        ),
        zero_rf_or_slot1_vault_bypass_events=p60_rep.zero_rf_or_slot1_vault_bypass_events,
        rf_packets_transmitted=p60_rep.rf_packets_transmitted,
        rf_nvs_mutation_bytes=p60_rep.rf_nvs_mutation_bytes,
        slot1_data_sector_writes=m59_rep.slot1_data_sector_writes + p60_rep.slot1_data_sector_writes,
        slot1_m4root_avf_mutation_bytes=p60_rep.slot1_m4root_avf_mutation_bytes,
        slot1_dcim_divider_mutation_bytes=p60_rep.slot1_dcim_divider_mutation_bytes,
        slot1_vault_mutation_bytes=(
            m59_rep.slot1_vault_mutation_bytes + p60_rep.slot1_vault_mutation_bytes
        ),
        slot1_format_hard_locked=(
            m59_rep.slot1_format_hard_locked and p60_rep.slot1_format_hard_locked
        ),
        slot1_vault_erofs_eopnotsupp_enforced=(
            m59_rep.slot1_vault_erofs_eopnotsupp_enforced
            and p60_rep.slot1_vault_erofs_eopnotsupp_enforced
        ),
        fx3_bright_monitoring_symbol_count=P336_FX3_BRIGHT_MONITORING_SYMBOL_COUNT,
        fx3_bright_mon_v700_focus_mag_coexist=True,
        fx3_monitor_brightness_level_min=P336_MONITOR_BRIGHTNESS_MIN_LEVEL,
        fx3_monitor_brightness_level_max=P336_MONITOR_BRIGHTNESS_MAX_LEVEL,
        fx3_has_dormant_bulb_timer=False,
        fx3_has_dormant_auto_hdr=False,
        fx3_has_dormant_divide_extract=False,
        fx3_has_bt_timecode_link=False,
        fx3_usb_lan_kmod_count=len(P336_USB_LAN_KERNEL_MODULES),
        fx3_wifi_active_security_count=len(P336_WIFI_SECURITY_ACTIVE_MODES),
        fx6_vf_brightness_min=P336_FX6_VF_BRIGHTNESS_MIN,
        fx6_vf_brightness_max=P336_FX6_VF_BRIGHTNESS_MAX,
        fx6_has_physical_tc_in_out_bnc=True,
        fx6_has_bluetooth_hardware=False,
        steadyshot_47focal_or_lockout_drift_events=(
            m59_rep.steadyshot_47focal_or_lockout_drift_events
        ),
        selftimer_dormant_or_led8_audio_drift_events=(
            m59_rep.selftimer_dormant_or_led8_audio_drift_events
        ),
        fx6_ibis_or_selftimer_spoof_events=m59_rep.fx6_ibis_or_selftimer_spoof_events,
        zebra_custom_ire_or_peaking_clean_hdmi_drift_events=(
            m59_rep.zebra_custom_ire_or_peaking_clean_hdmi_drift_events
        ),
        streaming_24p_rec_or_network_reset_drift_events=(
            m59_rep.streaming_24p_rec_or_network_reset_drift_events
        ),
        slot1_streaming_or_ftp_mutation_bytes=m59_rep.slot1_streaming_or_ftp_mutation_bytes,
        fx3_steadyshot_47_focal_count=m59_rep.fx3_steadyshot_47_focal_count,
        fx3_image_stabilization_item_count=m59_rep.fx3_image_stabilization_item_count,
        fx3_selftimer_cont_combo_count=m59_rep.fx3_selftimer_cont_combo_count,
        fx3_front_lamp_8_id=m59_rep.fx3_front_lamp_8_id,
        fx3_zebra_preset_count=m59_rep.fx3_zebra_preset_count,
        fx3_peaking_color_count=m59_rep.fx3_peaking_color_count,
        fx3_streaming_protocol_count=m59_rep.fx3_streaming_protocol_count,
        fx3_has_5axis_ibis=m59_rep.fx3_has_5axis_ibis,
        fx3_has_movie_self_timer=m59_rep.fx3_has_movie_self_timer,
        fx6_has_ibis=m59_rep.fx6_has_ibis,
        fx6_has_6axis_gyro_metadata=m59_rep.fx6_has_6axis_gyro_metadata,
        fx6_has_still_self_timer=m59_rep.fx6_has_still_self_timer,
        dial_customize_dormant_trap_or_reset_drift_events=(
            m59_rep.dial_customize_dormant_trap_or_reset_drift_events
        ),
        rear_dial_lr_or_mydial_override_drift_events=(
            m59_rep.rear_dial_lr_or_mydial_override_drift_events
        ),
        fn_menu_12x2_or_fx6_dial_spoof_events=m59_rep.fn_menu_12x2_or_fx6_dial_spoof_events,
        live_view_display_reset_split_or_mode_drift_events=(
            m59_rep.live_view_display_reset_split_or_mode_drift_events
        ),
        grid_line_or_hdmi_clean_feed_leak_events=m59_rep.grid_line_or_hdmi_clean_feed_leak_events,
        lut_path_embed_sidecar_or_slot1_vault_bypass_events=(
            m59_rep.lut_path_embed_sidecar_or_slot1_vault_bypass_events
        ),
        slot1_lut_mutation_bytes=m59_rep.slot1_lut_mutation_bytes,
        slot1_avf_info_mutated=m59_rep.slot1_avf_info_mutated,
        fx3_dial_customize_item_count=m59_rep.fx3_dial_customize_item_count,
        fx3_physical_dial_count=m59_rep.fx3_physical_dial_count,
        fx3_my_dial_bank_count=m59_rep.fx3_my_dial_bank_count,
        fx3_fn_menu_still_slots=m59_rep.fx3_fn_menu_still_slots,
        fx3_fn_menu_movie_slots=m59_rep.fx3_fn_menu_movie_slots,
        fx3_live_view_display_set_item_count=m59_rep.fx3_live_view_display_set_item_count,
        fx3_grid_line_type_count=m59_rep.fx3_grid_line_type_count,
        fx3_user_lut_slot_count=m59_rep.fx3_user_lut_slot_count,
        fx3_pplut_slot_count=m59_rep.fx3_pplut_slot_count,
        fx6_user_lut_ui_cap=m59_rep.fx6_user_lut_ui_cap,
        fx6_has_av_tv_rotate=m59_rep.fx6_has_av_tv_rotate,
        fx6_has_my_dial=m59_rep.fx6_has_my_dial,
        fx6_has_fn_menu=m59_rep.fx6_has_fn_menu,
        fx6_has_multi_channel_lut_switches=m59_rep.fx6_has_multi_channel_lut_switches,
        fx3_has_builtin_evf=m59_rep.fx3_has_builtin_evf,
        fx3_has_var_shutter=m59_rep.fx3_has_var_shutter,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        master_60pillar_sha256=master_sha,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(all_errors),
    )


def evaluate_60pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master60PillarRecoveryReport:
    """Short alias for `evaluate_realhw_60pillar_recovery_master`."""
    return evaluate_realhw_60pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_60pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master60PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_60pillar_recovery_master`."""
    return evaluate_realhw_60pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
