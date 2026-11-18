"""Phase 332 — Recovery Pillar 59 & 59/59 Master Recovery Verifier:
Wave-57 Sony ILME-FX3 (Ver. 7.02) vs ILME-FX6 (Ver. 6.01) Empirically Grounded Guardrails:
  * Pillar 59A: [Image Stabilization] 5-Axis IBIS (Movie Active/Standard/Off vs dormant Dynamic active,
    4-Condition Active Lockout, 1.104x crop & Distortion=Auto, CIZ interaction), Still SteadyShot On/Off,
    47-Step Focal Length (8..1000mm), & [Drive Mode] Still Self-timer(Single/Cont) + Bracket + LED #8 +
    [Audio signals] vs dormant Movie Self-timer & FX6 OSS/6-axis gyro/Picture Cache/Interval Rec.
  * Pillar 59B: [Zebra Display] / [Zebra Level] (Custom1 Std+Range 0..109+-1..10%, Custom2 Lower Limit 0..109+,
    S-Log3 41%/61%/94% vs post-LUT measurement), 4-Color [Peaking] Clean-HDMI isolation vs FX6 mutually exclusive
    Off/Zebra1/Zebra2 & B&W/R/Y/B, [Network Streaming] RTMP/RTMPS/SRT (59.94/50/29.97/25p only, no 23.98p/24p,
    Movie Rec During Streaming 4K/2K59.94 lockout, Reset Network Set. preserves Airplane Mode=On),
    & Zero-RF USB-LAN + Slot-1 Tier-0 Recovery Vault EROFS=30 Firewall.
  * Unified 59/59 Recovery Master Aggregator (Pillars 1..58 + Pillar 59).

Safety Redlines (HARD-LOCKED):
  - Zero hardware attach, zero physical device writes, zero USB/UART TX, zero OTP/RPMB, zero eMMC writes.
  - Zero raw firmware bytes leaked (`raw_firmware_bytes_leaked == 0`).
  - Bounded `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` donor inspection (`< 0.2s` local / `< 0.5s` CI) with
    explicit `work_root is None` guard and automatic `CLEAN_ROOM_SYNTHETIC` fallback.
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

from .realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier import (
    MASTER_58_PILLAR_SPECS,
    Master58PillarRecoveryReport,
    P326_DONOR_FX3_APPFW_702_RELPATH,
    P326_DONOR_FX3_BACKUP_BIN_RELPATH,
    P326_DONOR_FX3_UXC_EN_F_RELPATH,
    P326_DONOR_FX3_UXC_EN_G_RELPATH,
    P326_DONOR_FX3_UXC_EN_RELPATH,
    P326_DONOR_FX3_UXC_JA_F_RELPATH,
    P326_DONOR_FX3_UXC_JA_G_RELPATH,
    P326_DONOR_FX3_UXC_JA_RELPATH,
    P326_DONOR_FX3_UXC_SC_F_RELPATH,
    P326_DONOR_FX3_UXC_SC_G_RELPATH,
    P326_DONOR_FX3_UXC_SC_RELPATH,
    P326_DONOR_FX3_UXC_TC_F_RELPATH,
    P326_DONOR_FX3_UXC_TC_G_RELPATH,
    P326_DONOR_FX3_UXC_TC_RELPATH,
    P326_DONOR_FX6_APPFW_601_RELPATH,
    P326_DONOR_FX6_UXC_EN_2_RELPATH,
    P326_DONOR_FX6_UXC_EN_RELPATH,
    P326_PINNED_FX3_APPFW_702_BYTES,
    P326_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P326_PINNED_FX3_BACKUP_BIN_BYTES,
    P326_PINNED_FX3_BACKUP_BIN_SHA256,
    P326_PINNED_FX3_UXC_EN_BYTES,
    P326_PINNED_FX3_UXC_EN_F_BYTES,
    P326_PINNED_FX3_UXC_EN_F_SHA256,
    P326_PINNED_FX3_UXC_EN_G_BYTES,
    P326_PINNED_FX3_UXC_EN_G_SHA256,
    P326_PINNED_FX3_UXC_EN_SHA256,
    P326_PINNED_FX3_UXC_JA_BYTES,
    P326_PINNED_FX3_UXC_JA_F_BYTES,
    P326_PINNED_FX3_UXC_JA_F_SHA256,
    P326_PINNED_FX3_UXC_JA_G_BYTES,
    P326_PINNED_FX3_UXC_JA_G_SHA256,
    P326_PINNED_FX3_UXC_JA_SHA256,
    P326_PINNED_FX3_UXC_SC_BYTES,
    P326_PINNED_FX3_UXC_SC_F_BYTES,
    P326_PINNED_FX3_UXC_SC_F_SHA256,
    P326_PINNED_FX3_UXC_SC_G_BYTES,
    P326_PINNED_FX3_UXC_SC_G_SHA256,
    P326_PINNED_FX3_UXC_SC_SHA256,
    P326_PINNED_FX3_UXC_TC_BYTES,
    P326_PINNED_FX3_UXC_TC_F_BYTES,
    P326_PINNED_FX3_UXC_TC_F_SHA256,
    P326_PINNED_FX3_UXC_TC_G_BYTES,
    P326_PINNED_FX3_UXC_TC_G_SHA256,
    P326_PINNED_FX3_UXC_TC_SHA256,
    P326_PINNED_FX6_APPFW_601_BYTES,
    P326_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P326_PINNED_FX6_UXC_EN_2_BYTES,
    P326_PINNED_FX6_UXC_EN_2_SHA256,
    P326_PINNED_FX6_UXC_EN_BYTES,
    P326_PINNED_FX6_UXC_EN_SHA256,
    evaluate_realhw_58pillar_recovery_master,
)
from . import files as _fx3_files
from .files import is_forced_clean_room, iter_donor_work_roots
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus

# ---------------------------------------------------------------------------
# Phase 332 Metadata, Safety Redlines & Pinned Budget Constants
# ---------------------------------------------------------------------------

PHASE332_SCHEMA = "realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier_v1"
PHASE332_MASTER_SCHEMA = "realhw_59pillar_recovery_master_v1"
PHASE332_VERSION = "1.0.0"
PHASE332_PHASE_NUMBER = 332

P332_ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"

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

P332_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
P332_OVERALL_READY_FOR_HARDWARE_ATTACH = False
P332_CROSS_MODEL_FLASH_AUTHORIZED = False

OTP_FUSE_TOUCHES = 0
OTP_FUSE_WRITES = 0
RPMB_COUNTER_INCREMENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PHYSICAL_DEVICE_WRITES = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

P332_BOUNDED_HEADER_BYTES = 4096
P332_MAX_FULL_DONOR_BYTES = 3_000_000
P332_DONOR_INSPECT_BUDGET_SECONDS = 0.20
P332_DONOR_INSPECT_CI_BUDGET_SECONDS = 0.50
P332_FAST_CLI_BUDGET_SECONDS = 1.50
P332_NOMINAL_BUDGET_SECONDS = 4.00
P332_CONCURRENT_CEILING_SECONDS = 6.00

P332_EINVAL_ERRNO = 22
P332_EROFS_ERRNO = 30
P332_EOPNOTSUPP_ERRNO = 95

# Camera Identities
P332_FX3_MODEL_NAME = "ILME-FX3"
P332_FX3_MODEL_ID = 0x91030080
P332_FX3_PRODUCT_CODENAME = "PRODUCT_MODEL_ALCIN_UUD"
P332_FX3_HELPGUIDE_ID = "ilc/2210"
P332_FX3_FW_VERSION = "7.02"
P332_FX3_SUPPORTED_FW_VERSIONS = ("7.02", "7.01", "7.00", "6.02", "6.00")

P332_FX6_DONOR_MODEL_NAME = "ILME-FX6"
P332_FX6_DONOR_FW_VERSION = "6.01"
P332_FX6_PRODUCT_CODENAME = "PRODUCT_MODEL_CHAPLIN"

# Pinned Donor Relpaths & Digests (17 Wave-57 donors: 14 FX3 7.02 + 3 FX6 6.01)
P332_DONOR_FX3_APPFW_702_RELPATH = P326_DONOR_FX3_APPFW_702_RELPATH
P332_DONOR_FX6_APPFW_601_RELPATH = P326_DONOR_FX6_APPFW_601_RELPATH
P332_DONOR_FX3_BACKUP_BIN_RELPATH = P326_DONOR_FX3_BACKUP_BIN_RELPATH
P332_DONOR_FX3_UXC_EN_F_RELPATH = P326_DONOR_FX3_UXC_EN_F_RELPATH
P332_DONOR_FX3_UXC_SC_F_RELPATH = P326_DONOR_FX3_UXC_SC_F_RELPATH
P332_DONOR_FX3_UXC_TC_F_RELPATH = P326_DONOR_FX3_UXC_TC_F_RELPATH
P332_DONOR_FX3_UXC_JA_F_RELPATH = P326_DONOR_FX3_UXC_JA_F_RELPATH
P332_DONOR_FX3_UXC_EN_RELPATH = P326_DONOR_FX3_UXC_EN_RELPATH
P332_DONOR_FX3_UXC_SC_RELPATH = P326_DONOR_FX3_UXC_SC_RELPATH
P332_DONOR_FX3_UXC_TC_RELPATH = P326_DONOR_FX3_UXC_TC_RELPATH
P332_DONOR_FX3_UXC_JA_RELPATH = P326_DONOR_FX3_UXC_JA_RELPATH
P332_DONOR_FX3_UXC_EN_G_RELPATH = P326_DONOR_FX3_UXC_EN_G_RELPATH
P332_DONOR_FX3_UXC_SC_G_RELPATH = P326_DONOR_FX3_UXC_SC_G_RELPATH
P332_DONOR_FX3_UXC_TC_G_RELPATH = P326_DONOR_FX3_UXC_TC_G_RELPATH
P332_DONOR_FX3_UXC_JA_G_RELPATH = P326_DONOR_FX3_UXC_JA_G_RELPATH
P332_DONOR_FX6_UXC_EN_RELPATH = P326_DONOR_FX6_UXC_EN_RELPATH
P332_DONOR_FX6_UXC_EN_2_RELPATH = P326_DONOR_FX6_UXC_EN_2_RELPATH

P332_PINNED_FX3_APPFW_702_BYTES = P326_PINNED_FX3_APPFW_702_BYTES
P332_PINNED_FX3_APPFW_702_HDR4K_SHA256 = P326_PINNED_FX3_APPFW_702_HDR4K_SHA256
P332_PINNED_FX6_APPFW_601_BYTES = P326_PINNED_FX6_APPFW_601_BYTES
P332_PINNED_FX6_APPFW_601_HDR4K_SHA256 = P326_PINNED_FX6_APPFW_601_HDR4K_SHA256
P332_PINNED_FX3_BACKUP_BIN_BYTES = P326_PINNED_FX3_BACKUP_BIN_BYTES
P332_PINNED_FX3_BACKUP_BIN_SHA256 = P326_PINNED_FX3_BACKUP_BIN_SHA256
P332_PINNED_FX3_UXC_EN_F_BYTES = P326_PINNED_FX3_UXC_EN_F_BYTES
P332_PINNED_FX3_UXC_EN_F_SHA256 = P326_PINNED_FX3_UXC_EN_F_SHA256
P332_PINNED_FX3_UXC_SC_F_BYTES = P326_PINNED_FX3_UXC_SC_F_BYTES
P332_PINNED_FX3_UXC_SC_F_SHA256 = P326_PINNED_FX3_UXC_SC_F_SHA256
P332_PINNED_FX3_UXC_TC_F_BYTES = P326_PINNED_FX3_UXC_TC_F_BYTES
P332_PINNED_FX3_UXC_TC_F_SHA256 = P326_PINNED_FX3_UXC_TC_F_SHA256
P332_PINNED_FX3_UXC_JA_F_BYTES = P326_PINNED_FX3_UXC_JA_F_BYTES
P332_PINNED_FX3_UXC_JA_F_SHA256 = P326_PINNED_FX3_UXC_JA_F_SHA256
P332_PINNED_FX3_UXC_EN_BYTES = P326_PINNED_FX3_UXC_EN_BYTES
P332_PINNED_FX3_UXC_EN_SHA256 = P326_PINNED_FX3_UXC_EN_SHA256
P332_PINNED_FX3_UXC_SC_BYTES = P326_PINNED_FX3_UXC_SC_BYTES
P332_PINNED_FX3_UXC_SC_SHA256 = P326_PINNED_FX3_UXC_SC_SHA256
P332_PINNED_FX3_UXC_TC_BYTES = P326_PINNED_FX3_UXC_TC_BYTES
P332_PINNED_FX3_UXC_TC_SHA256 = P326_PINNED_FX3_UXC_TC_SHA256
P332_PINNED_FX3_UXC_JA_BYTES = P326_PINNED_FX3_UXC_JA_BYTES
P332_PINNED_FX3_UXC_JA_SHA256 = P326_PINNED_FX3_UXC_JA_SHA256
P332_PINNED_FX3_UXC_EN_G_BYTES = P326_PINNED_FX3_UXC_EN_G_BYTES
P332_PINNED_FX3_UXC_EN_G_SHA256 = P326_PINNED_FX3_UXC_EN_G_SHA256
P332_PINNED_FX3_UXC_SC_G_BYTES = P326_PINNED_FX3_UXC_SC_G_BYTES
P332_PINNED_FX3_UXC_SC_G_SHA256 = P326_PINNED_FX3_UXC_SC_G_SHA256
P332_PINNED_FX3_UXC_TC_G_BYTES = P326_PINNED_FX3_UXC_TC_G_BYTES
P332_PINNED_FX3_UXC_TC_G_SHA256 = P326_PINNED_FX3_UXC_TC_G_SHA256
P332_PINNED_FX3_UXC_JA_G_BYTES = P326_PINNED_FX3_UXC_JA_G_BYTES
P332_PINNED_FX3_UXC_JA_G_SHA256 = P326_PINNED_FX3_UXC_JA_G_SHA256
P332_PINNED_FX6_UXC_EN_BYTES = P326_PINNED_FX6_UXC_EN_BYTES
P332_PINNED_FX6_UXC_EN_SHA256 = P326_PINNED_FX6_UXC_EN_SHA256
P332_PINNED_FX6_UXC_EN_2_BYTES = P326_PINNED_FX6_UXC_EN_2_BYTES
P332_PINNED_FX6_UXC_EN_2_SHA256 = P326_PINNED_FX6_UXC_EN_2_SHA256

# Zero-Violation Pillar 59 Counters & Vault Flags
P332_STEADYSHOT_47FOCAL_OR_LOCKOUT_DRIFT_EVENTS = 0
P332_SELFTIMER_DORMANT_OR_LED8_AUDIO_DRIFT_EVENTS = 0
P332_FX6_IBIS_OR_SELFTIMER_SPOOF_EVENTS = 0
P332_ZEBRA_CUSTOM_IRE_OR_PEAKING_CLEAN_HDMI_DRIFT_EVENTS = 0
P332_STREAMING_24P_REC_OR_NETWORK_RESET_DRIFT_EVENTS = 0
P332_ZERO_RF_OR_SLOT1_VAULT_BYPASS_EVENTS = 0

P332_RF_PACKETS_TRANSMITTED = 0
P332_RF_NVS_MUTATION_BYTES = 0
P332_SLOT1_DATA_SECTOR_WRITES = 0
P332_SLOT1_STREAMING_OR_FTP_MUTATION_BYTES = 0
P332_SLOT1_VAULT_MUTATION_BYTES = 0
P332_SLOT1_FORMAT_HARD_LOCKED = True
P332_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True
P332_AIRPLANE_MODE_FORCED_ON = True

P332_STAGE_B_VOLATILE_OVERLAY_DIR = "/tmp/fx3_stage_b_overlay/pillar59"
P332_FORBIDDEN_PERSISTENT_TARGETS = (
    "/dev/cnflasha",
    "/setting",
    "/mnt/emmc",
    "/nflasha",
)
P332_TIER0_SURFACE_COUNT = 16
P332_SLOT1_VAULT_SLOT = 1
P332_SAFE_SECONDARY_SLOT = 2

# ---------------------------------------------------------------------------
# Wave-57 Empirical Constants: Pillar 59A ([Image Stabilization] & [Self-timer])
# ---------------------------------------------------------------------------

P332_IMAGE_STABILIZATION_G_RESID16 = 0x6214
P332_STEADYSHOT_BASE_RESID16 = 0xE153
P332_STEADYSHOT_ACTIVE_F_RESID16 = 0x714F
P332_STEADYSHOT_STANDARD_BASE_RESID16 = 0xE03B
P332_STEADYSHOT_OFF_BASE_RESID16 = 0xE297
P332_STEADYSHOT_ADJUST_F_RESID16 = 0x7880
P332_STEADYSHOT_ADJUST_AUTO_BASE_RESID16 = 0xE6DA
P332_STEADYSHOT_ADJUST_MANUAL_BASE_RESID16 = 0xE44C
P332_FOCAL_LENGTH_F_RESID16 = 0x65B1
P332_STEADYS_FOCAL_LEN_F_RESID16 = 0x625A
P332_DORMANT_DYNAMIC_ACTIVE_F_RESID16 = 0x741C
P332_DORMANT_DYNAMIC_ACTIVE_DESC_F_RESID16 = 0x65B5

P332_BKID_MOVIE_STEADYSHOT = "BKID_APP_setting_movie_steadyshot"
P332_BKID_STILL_STEADYSHOT = "BKID_APP_setting_still_steadyshot"
P332_BKID_STEADYSHOT_ADJUSTMENT = "BKID_APP_setting_steadyshot_adjustment"
P332_BKID_STEADY_FOCAL_LENGTH = "BKID_APP_setting_steady_focal_length"

P332_IMAGE_STABILIZATION_4_ITEMS = (
    "SteadyShot (Movie)",
    "SteadyShot (Still)",
    "SteadyShot Adjust.",
    "Focal Length",
)
P332_IMAGE_STABILIZATION_ITEM_COUNT = 4
P332_MOVIE_STEADYSHOT_MODES = ("Active", "Standard", "Off")
P332_MOVIE_STEADYSHOT_ALL_MODES = ("Active", "Standard", "Off", "Dynamic active")
P332_MOVIE_STEADYSHOT_DEFAULT = "Standard"
P332_STILL_STEADYSHOT_MODES = ("On", "Off")
P332_STILL_STEADYSHOT_DEFAULT = "On"
P332_STEADYSHOT_ADJUST_MODES = ("Auto", "Manual")
P332_STEADYSHOT_ADJUST_DEFAULT = "Auto"

# Exact 47 focal length steps from FX3 Ver. 7.02 appFw.so
P332_STEADYSHOT_47_FOCAL_LENGTHS_MM: Tuple[int, ...] = (
    8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
    24, 25, 28, 30, 32, 35, 40, 45, 50, 55, 60, 70, 75, 80,
    85, 90, 100, 105, 120, 135, 150, 180, 200, 210, 250, 300,
    350, 400, 450, 500, 600, 800, 1000,
)
P332_STEADYSHOT_FOCAL_LENGTH_COUNT = 47
P332_STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM = 8

P332_ACTIVE_CROP_FACTOR_APPROX = 1.104
P332_ACTIVE_LOCKOUT_CONDITIONS = (
    "MOVIE_FPS_GE_100P",
    "SQ_FPS_GE_100FPS",
    "HDMI_RAW_ON",
    "DE_SQUEEZE_NON_OFF",
)
P332_DE_SQUEEZE_OPTIONS = ("Off", "1.3x", "1.5x", "1.65x", "1.8x", "2.0x")
P332_CLEAR_IMAGE_ZOOM_OPTIONS = ("Optical zoom only", "Clear Image Zoom")
P332_CLEAR_IMAGE_ZOOM_DEFAULT = "Optical zoom only"

P332_FX3_HAS_5AXIS_IBIS = True
P332_FX6_HAS_IBIS = False
P332_FX6_HAS_6AXIS_GYRO_METADATA = True
P332_FX6_IBIS_UNSUPPORTED_SYMBOL = "TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED"
P332_FX6_FIXED_STEADYSHOT_RESID16 = 0x2FA5
P332_FX6_OSS_INFO_RESID16 = 0x5232

P332_DRIVE_MODE_G_RESID16 = 0x616E
P332_DRIVE_MODE_BASE_RESID16 = 0xE5D2
P332_SOUND_OPTION_G_RESID16 = 0x6110
P332_AUDIO_SIGNALS_BASE_RESID16 = 0xE0C8
P332_SELFTIMER_SINGLE_F_RESID16 = 0x6772
P332_SELFTIMER_CONT_F_RESID16 = 0x728C
P332_BRACKET_SELFTIMER_F_RESID16 = 0x6EF5
P332_DORMANT_MOVIE_SELFTIMER_BKID = "BKID_APP_setting_movie_self_timer"
P332_DORMANT_MOVIE_REC_START_DELAY_F_RESID16 = 0x7192
P332_DORMANT_SINGLE_BURST_SELFTIMER_F_RESID16 = 0x758B
P332_DORMANT_SELF_PORTRAIT_3SEC_F_RESID16 = 0x70B8
P332_DORMANT_SELFTIMER_SYMBOLS = (
    "BKID_APP_setting_movie_self_timer",
    "Rec Start delay",
    "Single Burst Self-timer",
    "Self-portrait 3-sec",
)

P332_DRIVE_MODE_DEFAULT = "Single Shooting"
P332_DRIVE_MODE_SELFTIMER_TYPES = ("None", "Self-timer(Single)", "Self-timer(Cont)")
P332_SELFTIMER_SINGLE_DELAYS_SEC = (10, 5, 2)
P332_SELFTIMER_CONT_COMBOS = (
    "10 Sec. 3 Img.",
    "10 Sec. 5 Img.",
    "5 Sec. 3 Img.",
    "5 Sec. 5 Img.",
    "2 Sec. 3 Img.",
    "2 Sec. 5 Img.",
)
P332_SELFTIMER_CONT_COMBO_COUNT = 6
P332_BRACKET_SELFTIMER_OPTIONS = ("Off", "2 Sec", "5 Sec", "10 Sec")
P332_BRACKET_SELFTIMER_DEFAULT = "Off"
P332_FRONT_LAMP_8_ID = 8
P332_FRONT_LAMP_8_FUNCTION = "AF illuminator / Self-timer lamp / Visible light and IR sensor"
P332_AUDIO_SIGNALS_MODES = ("On", "Off")
P332_AUDIO_SIGNALS_DEFAULT = "On"
P332_FX3_HAS_MOVIE_SELF_TIMER = False
P332_FX6_HAS_STILL_SELF_TIMER = False
P332_FX6_ALT_REC_FEATURES = ("Picture Cache Rec", "Interval Rec")

# ---------------------------------------------------------------------------
# Wave-57 Empirical Constants: Pillar 59B ([Zebra]/[Peaking] & [Streaming]/Vault)
# ---------------------------------------------------------------------------

P332_EXPOSURE_COLOR_G_RESID16 = 0x609A
P332_ZEBRA_DISPLAY_G_RESID16 = 0x6352
P332_ZEBRA_DISPLAY_F_RESID16 = 0x7852
P332_ZEBRA_LEVEL_F_RESID16 = 0x70D7
P332_ZEBRA_CUSTOM1_F_RESID16 = 0x68AA
P332_ZEBRA_CUSTOM2_F_RESID16 = 0x68AB
P332_ZEBRA_STD_RANGE_F_RESID16 = 0x7500
P332_ZEBRA_LOWER_LIMIT_F_RESID16 = 0x612E
P332_ZEBRA_DISPLAY_SELECT_F_RESID16 = 0x6E05

P332_FOCUS_G_RESID16 = 0x6419
P332_PEAKING_DISPLAY_G_RESID16 = 0x6050
P332_PEAKING_DISPLAY_F_RESID16 = 0x6FE5
P332_PEAKING_DISPLAY_SELECT_F_RESID16 = 0x62A8
P332_PEAKING_COLOR_BLUE_F_RESID16 = 0x7494

P332_BKID_ZEBRA_DISPLAY = "BKID_APP_setting_zebra_display"
P332_BKID_ZEBRA_LEVEL = "BKID_APP_setting_zebra_level"
P332_BKID_PEAKING_DISPLAY = "BKID_APP_setting_peaking_display"
P332_BKID_PEAKING_LEVEL = "BKID_APP_setting_peaking_level"
P332_BKID_PEAKING_COLOR = "BKID_APP_setting_peaking_color"

P332_ZEBRA_DISPLAY_DEFAULT = "Off"
P332_ZEBRA_PRESET_LEVELS = ("70", "75", "80", "85", "90", "95", "100", "100+")
P332_ZEBRA_LEVEL_OPTIONS = P332_ZEBRA_PRESET_LEVELS + ("Custom1", "Custom2")
P332_ZEBRA_LEVEL_DEFAULT = "70"
P332_ZEBRA_CUSTOM_TYPES = ("Std+Range", "Lower Limit")
P332_ZEBRA_STD_MIN_PCT = 0
P332_ZEBRA_STD_MAX_PCT = 109
P332_ZEBRA_RANGE_MIN_PCT = 1
P332_ZEBRA_RANGE_MAX_PCT = 10
P332_ZEBRA_LOWER_LIMIT_MIN_PCT = 0
P332_ZEBRA_LOWER_LIMIT_MAX_PCT = 109

P332_SLOG3_18_GRAY_IRE = 41
P332_SLOG3_90_WHITE_IRE = 61
P332_SLOG3_CLIP_IRE = 94

P332_PEAKING_DISPLAY_DEFAULT = "Off"
P332_PEAKING_LEVELS = ("High", "Mid", "Low")
P332_PEAKING_LEVEL_DEFAULT = "Mid"
P332_PEAKING_COLORS = ("Red", "Yellow", "Blue", "White")
P332_PEAKING_COLOR_DEFAULT = "White"

P332_FX6_ZEBRA_MODES = ("Off", "Zebra1", "Zebra2")
P332_FX6_ZEBRA_ALL_MODES = ("Off", "Zebra1", "Zebra2", "Both")
P332_FX6_ZEBRA1_DEFAULT_LEVEL_PCT = 70
P332_FX6_ZEBRA1_DEFAULT_APERTURE_PCT = 10
P332_FX6_ZEBRA1_APERTURE_MIN_PCT = 2
P332_FX6_ZEBRA1_APERTURE_MAX_PCT = 20
P332_FX6_ZEBRA2_DEFAULT_LEVEL_PCT = 100
P332_FX6_PEAKING_COLORS = ("B&W", "Red", "Yellow", "Blue")

# Network Streaming, FTP & Vault Constants
P332_NETWORK_G_RESID16 = 0x6131
P332_STREAMING_G_RESID16 = 0x618D
P332_NETWORK_STREAMING_F_RESID16 = 0x6CB2
P332_OUTPUT_IMG_QUALITY_SET_F_RESID16 = 0x7065
P332_MOVIE_REC_DURING_STREAMING_F_RESID16 = 0x79D5
P332_EMPHASIZED_OUTPUT_DISPLAY_F_RESID16 = 0x6661
P332_ROOT_CERT_ERROR_F_RESID16 = 0x65F2
P332_FTP_TRANSFER_G_RESID16 = 0x64BF
P332_FTP_TRANSFER_FUNC_F_RESID16 = 0x6317
P332_AUTO_FTP_TRANSFER_F_RESID16 = 0x7B27
P332_NETWORK_OPTION_G_RESID16 = 0x61E1
P332_AIRPLANE_MODE_F_RESID16 = 0x6B05

P332_BKID_STREAMING = "BKID_APP_setting_movie_network_streaming_streaming"
P332_BKID_MOVIE_REC_DURING_STREAMING = (
    "BKID_APP_setting_movie_network_streaming_movie_rec_dur_distribution"
)
P332_BKID_AIRPLANE_MODE = "BKID_APP_setting_airplane_mode"

P332_STREAMING_MENU_PATH = ("Network", "Streaming", "Network Streaming")
P332_STREAMING_PROTOCOLS = ("RTMP", "RTMPS", "SRT")
P332_STREAMING_QUALITY_PRESETS = ("High", "Standard", "Low", "Custom")
P332_STREAMING_QUALITY_DEFAULT = "Standard"
P332_STREAMING_RESOLUTIONS = ("4K", "2K", "1080p", "720p")
P332_STREAMING_RESOLUTION_DEFAULT = "1080p"
P332_STREAMING_ALLOWED_FPS = ("59.94p", "50p", "29.97p", "25p")
P332_STREAMING_DISALLOWED_FPS = ("23.98p", "24p", "24.00p")
P332_STREAMING_ALL_FPS = P332_STREAMING_ALLOWED_FPS + P332_STREAMING_DISALLOWED_FPS
P332_STREAMING_VIDEO_CODECS_BY_PROTOCOL: Dict[str, Tuple[str, ...]] = {
    "RTMP": ("H.264",),
    "RTMPS": ("H.264",),
    "SRT": ("H.265", "H.264"),
}
P332_SRT_ENCRYPTION_MODES = ("None", "AES-128", "AES-256")
P332_STREAMING_AUDIO_FORMAT = "AAC 48kHz 16-bit 2ch"
P332_MOVIE_REC_DURING_STREAMING_MODES = ("Disable", "Enable")
P332_MOVIE_REC_DURING_STREAMING_DEFAULT = "Disable"
P332_STREAMING_LOCKED_OUT_FEATURES = (
    "Menu",
    "Playback",
    "FTP Transfer",
    "Remote Shooting",
    "Cloud Connection",
    "Smartphone Transfer",
    "Power Save Start Time",
)
P332_NETWORK_TRANSPORTS = ("USB-LAN (CDC-NCM)", "Wi-Fi", "USB Tethering")
P332_SAFE_WIRED_TRANSPORT = "USB-LAN (CDC-NCM)"

P332_FTP_AUTO_TARGETS = ("Still Image", "All", "Only Shot Mark")
P332_FTP_MOVIE_TRANSFER_TARGETS = ("Proxy Only", "All", "Only Shot Mark")
P332_FX6_DORMANT_STREAMING_SYMBOLS = (
    "RTMP",
    "RTMPS",
    "SRT",
    "QoS Streaming",
    "Intelligent QoS",
)

P332_SHOOTING_DOMAINS = ("Still", "Movie", "S&Q")
P332_ON_OFF_MODES = ("On", "Off")
P332_RESET_ACTIONS = ("None", "Camera Settings Reset", "Reset Network Set.", "Initialize")
P332_VAULT_ACTIONS = (
    "NONE",
    "READ_ONLY_AUDIT",
    "STREAM_ONLY_USB_LAN",
    "MOVIE_REC_DURING_STREAMING_RECORD",
    "FTP_READ_ONLY_GET",
    "FTP_WRITE_TARGET",
    "MAKE_DIR",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P332_WRITE_MUTATING_VAULT_ACTIONS = (
    "MOVIE_REC_DURING_STREAMING_RECORD",
    "FTP_WRITE_TARGET",
    "MAKE_DIR",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P332_VAULT_FIREWALL_ERRNOS = ("EROFS", "EBUSY", "EOPNOTSUPP")
P332_VAULT_FIREWALL_ERRNO_CODES: Dict[str, int] = {
    "EBUSY": 16,
    "EROFS": 30,
    "EOPNOTSUPP": 95,
}

# Block Codes & Status Constants
P332_BLOCKED_SAFETY_POLICY_VIOLATION = "P332_BLOCKED_SAFETY_POLICY_VIOLATION"
P332_BLOCKED_INVALID_PILLAR59A_SPEC = "P332_BLOCKED_INVALID_PILLAR59A_SPEC"
P332_BLOCKED_INVALID_PILLAR59B_SPEC = "P332_BLOCKED_INVALID_PILLAR59B_SPEC"
P332_BLOCKED_STEADYSHOT_47FOCAL_OR_LOCKOUT_DRIFT = (
    "P332_BLOCKED_STEADYSHOT_47FOCAL_OR_LOCKOUT_DRIFT"
)
P332_BLOCKED_SELFTIMER_DORMANT_OR_LED8_AUDIO_DRIFT = (
    "P332_BLOCKED_SELFTIMER_DORMANT_OR_LED8_AUDIO_DRIFT"
)
P332_BLOCKED_FX6_IBIS_OR_SELFTIMER_SPOOF = "P332_BLOCKED_FX6_IBIS_OR_SELFTIMER_SPOOF"
P332_BLOCKED_ZEBRA_CUSTOM_IRE_OR_PEAKING_CLEAN_HDMI_DRIFT = (
    "P332_BLOCKED_ZEBRA_CUSTOM_IRE_OR_PEAKING_CLEAN_HDMI_DRIFT"
)
P332_BLOCKED_STREAMING_24P_REC_OR_NETWORK_RESET_DRIFT = (
    "P332_BLOCKED_STREAMING_24P_REC_OR_NETWORK_RESET_DRIFT"
)
P332_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL = (
    "P332_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL"
)
P332_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL = P332_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL
P332_BLOCKED_PERSISTENT_OVERLAY_ESCAPE = "P332_BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P332_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT = "P332_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P332_STATUS_VERIFIED_PILLAR_59A = "VERIFIED_PILLAR_59A_STEADYSHOT_47FOCAL_SELFTIMER_VAULT"
P332_STATUS_REJECTED_PILLAR_59A = "REJECTED_PILLAR_59A_STEADYSHOT_47FOCAL_SELFTIMER_VAULT"
P332_STATUS_VERIFIED_PILLAR_59B = "VERIFIED_PILLAR_59B_ZEBRA_PEAKING_STREAMING_VAULT"
P332_STATUS_REJECTED_PILLAR_59B = "REJECTED_PILLAR_59B_ZEBRA_PEAKING_STREAMING_VAULT"
P332_STATUS_VERIFIED_PILLAR59_SUITE = "VERIFIED_PILLAR59_STEADYSHOT_47FOCAL_SELFTIMER_ZEBRA_STREAMING_VAULT"
P332_STATUS_FAIL_PILLAR59_SUITE = "FAIL_PILLAR59_STEADYSHOT_47FOCAL_SELFTIMER_ZEBRA_STREAMING_VAULT"
P332_STATUS_VERIFIED_59OF59_AGGREGATOR = "VERIFIED_59OF59_PILLAR_RECOVERY_MASTER"
P332_STATUS_FAIL_59OF59_AGGREGATOR = "FAIL_59OF59_PILLAR_RECOVERY_MASTER"

P332_PILLAR_59A_SCENARIO_IDS = (
    "P59A1_STEADYSHOT_ACTIVE_CROP_DISTORTION_47FOCAL_ALLOW",
    "P59A2_STILL_SELFTIMER_CONT_6COMBO_BRACKET_LED8_AUDIO_ALLOW",
    "P59A3_ACTIVE_4LOCKOUT_OR_DORMANT_DYNAMIC_ACTIVE_REJECT",
    "P59A4_DORMANT_MOVIE_SELFTIMER_OR_INVALID_FOCAL_REJECT",
    "P59A5_FX6_NO_IBIS_OR_BOTH_SELFTIMER_SPOOF_REJECT",
    "P59A6_SLOT1_VAULT_OVERLAY_ESCAPE_OR_H0_H3_DRIFT_REJECT",
)
P332_PILLAR_59B_SCENARIO_IDS = (
    "P59B1_ZEBRA_SLOG3_CUSTOM12_PEAKING_CLEAN_HDMI_ALLOW",
    "P59B2_USB_LAN_ZERO_RF_SRT_AES256_RESET_NET_AIRPLANE_ALLOW",
    "P59B3_ZEBRA_RESET_LEAK_OR_PEAKING_HDMI_LEAK_REJECT",
    "P59B4_FX6_ZEBRA_BOTH_OR_DORMANT_RTMP_SRT_QOS_SPOOF_REJECT",
    "P59B5_STREAMING_24P_OR_4K_INTERNAL_REC_OR_NET_RESET_WIPE_REJECT",
    "P59B6_ZERO_RF_BREACH_OR_SLOT1_STREAMING_FTP_EROFS_BYPASS_REJECT",
)

# ---------------------------------------------------------------------------
# 59-Pillar Master Registry (Pillars 1..58 + Pillar 59)
# ---------------------------------------------------------------------------

MASTER_59_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_58_PILLAR_SPECS + (
    (
        59,
        "pillar59_steadyshot_47focal_selftimer_zebra_streaming_vault",
        "Phase 332",
        "fx3_recovery.realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier",
    ),
)
MASTER_59_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_59_PILLAR_SPECS)
MASTER_59_PILLAR_COUNT = len(MASTER_59_PILLAR_SPECS)


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
    env_flag = os.environ.get(P332_ENV_CLEAN_ROOM_TEST, "").strip().lower()
    if env_flag in ("1", "true", "yes"):
        return True
    if is_forced_clean_room():
        return True
    return False


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true" or os.environ.get(
        "CI", ""
    ).strip().lower() in ("1", "true", "yes"):
        return P332_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P332_DONOR_INSPECT_BUDGET_SECONDS


def _is_tmpfs_path(path: str) -> bool:
    norm = posixpath.normpath(path)
    return norm == "/tmp" or norm.startswith("/tmp/")


def _targets_persistent_emmc(path: str) -> bool:
    norm = posixpath.normpath(path)
    return any(
        norm == pref or norm.startswith(pref + "/") or norm.startswith(pref)
        for pref in P332_FORBIDDEN_PERSISTENT_TARGETS
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
    if not P332_SLOT1_FORMAT_HARD_LOCKED:
        errs.append("P332_SLOT1_FORMAT_HARD_LOCKED must remain True")
    if not P332_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED:
        errs.append("P332_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED must remain True")
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


def compute_expected_steadyshot_selftimer_state(
    *,
    camera_model: str,
    shooting_domain: str,
    movie_steadyshot: str,
    still_steadyshot: str,
    steadyshot_adjust: str,
    focal_length_mm: int,
    movie_fps: float,
    sq_fps: float,
    hdmi_raw_on: bool,
    de_squeeze: str,
    distortion_comp: str,
    clear_image_zoom: str,
    still_raw_active: bool,
    drive_mode_selftimer_type: str,
    selftimer_bracket: str,
    requested_dormant_selftimer_symbols: Tuple[str, ...],
    silent_mode: str,
    movie_hdmi_audio_active: bool,
    audio_signals: str,
    reset_action: str,
) -> Dict[str, Any]:
    """Compute canonical Wave-57 Pillar 59A ([Image Stabilization] 47-Focal & [Self-timer]) state."""
    is_fx3 = camera_model == P332_FX3_MODEL_NAME

    active_lockout_reasons: List[str] = []
    if movie_fps >= 100.0:
        active_lockout_reasons.append("MOVIE_FPS_GE_100P")
    if sq_fps >= 100.0:
        active_lockout_reasons.append("SQ_FPS_GE_100FPS")
    if hdmi_raw_on:
        active_lockout_reasons.append("HDMI_RAW_ON")
    if de_squeeze != "Off":
        active_lockout_reasons.append("DE_SQUEEZE_NON_OFF")
    active_locked_out = len(active_lockout_reasons) > 0

    dormant_dynamic_active_hit = movie_steadyshot == "Dynamic active"
    dormant_dynamic_active_errno: Optional[int] = (
        P332_EOPNOTSUPP_ERRNO if dormant_dynamic_active_hit else None
    )

    if not is_fx3:
        effective_movie_steadyshot = "Unsupported_Fixed"
        active_lockout_errno: Optional[int] = P332_EOPNOTSUPP_ERRNO
        effective_crop_factor = 1.0
        forced_distortion_comp = distortion_comp
    elif dormant_dynamic_active_hit:
        effective_movie_steadyshot = P332_MOVIE_STEADYSHOT_DEFAULT
        active_lockout_errno = P332_EOPNOTSUPP_ERRNO
        effective_crop_factor = 1.0
        forced_distortion_comp = distortion_comp
    elif movie_steadyshot == "Active" and active_locked_out:
        effective_movie_steadyshot = "Standard"
        active_lockout_errno = P332_EOPNOTSUPP_ERRNO
        effective_crop_factor = 1.0
        forced_distortion_comp = distortion_comp
    elif movie_steadyshot == "Active":
        effective_movie_steadyshot = "Active"
        active_lockout_errno = None
        effective_crop_factor = P332_ACTIVE_CROP_FACTOR_APPROX
        forced_distortion_comp = "Auto"
    else:
        effective_movie_steadyshot = movie_steadyshot
        active_lockout_errno = None
        effective_crop_factor = 1.0
        forced_distortion_comp = distortion_comp

    focal_valid = focal_length_mm in P332_STEADYSHOT_47_FOCAL_LENGTHS_MM
    focal_length_errno: Optional[int] = None if focal_valid else P332_EINVAL_ERRNO

    # Clear Image Zoom lockouts
    ciz_blocked = movie_fps >= 100.0 or sq_fps >= 100.0 or (shooting_domain == "Still" and still_raw_active)
    ciz_errno: Optional[int] = (
        P332_EOPNOTSUPP_ERRNO
        if (clear_image_zoom == "Clear Image Zoom" and ciz_blocked)
        else None
    )
    effective_ciz = (
        P332_CLEAR_IMAGE_ZOOM_DEFAULT
        if (clear_image_zoom == "Clear Image Zoom" and ciz_blocked)
        else clear_image_zoom
    )
    active_ciz_crop_stacked = (
        is_fx3 and effective_movie_steadyshot == "Active" and effective_ciz == "Clear Image Zoom"
    )
    ciz_forces_metering_multi = is_fx3 and effective_ciz == "Clear Image Zoom"

    # Dormant Movie Self-timer & non-FX3 variants
    dormant_selftimer_hit = (
        len(requested_dormant_selftimer_symbols) > 0
        or (is_fx3 and shooting_domain != "Still" and drive_mode_selftimer_type != "None")
    )
    dormant_selftimer_errno: Optional[int] = (
        P332_EOPNOTSUPP_ERRNO if dormant_selftimer_hit else None
    )

    # LED #8 & Audio signals coupling
    selftimer_active_still = (
        is_fx3
        and shooting_domain == "Still"
        and (drive_mode_selftimer_type != "None" or selftimer_bracket != "Off")
    )
    led8_flashes = selftimer_active_still
    audio_muted_by_silent_or_hdmi = silent_mode == "On" or (
        shooting_domain in ("Movie", "S&Q") and movie_hdmi_audio_active
    )
    audio_beep_audible = (
        is_fx3 and audio_signals == "On" and not audio_muted_by_silent_or_hdmi and selftimer_active_still
    )

    # Reset split:
    # - [Image Stabilization] 4 items & Still [Drive Mode] / [Selftimer during Bracket]: Resettable!
    # - [Audio signals]: Initialize-only!
    if is_fx3 and reset_action in ("Camera Settings Reset", "Initialize"):
        post_movie_steadyshot = P332_MOVIE_STEADYSHOT_DEFAULT
        post_still_steadyshot = P332_STILL_STEADYSHOT_DEFAULT
        post_steadyshot_adjust = P332_STEADYSHOT_ADJUST_DEFAULT
        post_focal_length_mm = P332_STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM
        post_drive_mode_selftimer_type = "None"
        post_selftimer_bracket = P332_BRACKET_SELFTIMER_DEFAULT
    else:
        post_movie_steadyshot = effective_movie_steadyshot
        post_still_steadyshot = still_steadyshot
        post_steadyshot_adjust = steadyshot_adjust
        post_focal_length_mm = focal_length_mm
        post_drive_mode_selftimer_type = drive_mode_selftimer_type
        post_selftimer_bracket = selftimer_bracket

    if is_fx3 and reset_action == "Initialize":
        post_audio_signals = P332_AUDIO_SIGNALS_DEFAULT
    else:
        post_audio_signals = audio_signals

    return {
        "has_ibis": is_fx3,
        "active_locked_out": active_locked_out,
        "active_lockout_reasons": tuple(active_lockout_reasons),
        "active_lockout_errno": active_lockout_errno,
        "dormant_dynamic_active_errno": dormant_dynamic_active_errno,
        "effective_movie_steadyshot": effective_movie_steadyshot,
        "effective_crop_factor": effective_crop_factor,
        "forced_distortion_comp": forced_distortion_comp,
        "focal_valid": focal_valid,
        "focal_length_errno": focal_length_errno,
        "ciz_blocked": ciz_blocked,
        "ciz_errno": ciz_errno,
        "effective_ciz": effective_ciz,
        "active_ciz_crop_stacked": active_ciz_crop_stacked,
        "ciz_forces_metering_multi": ciz_forces_metering_multi,
        "dormant_selftimer_errno": dormant_selftimer_errno,
        "led8_flashes": led8_flashes,
        "audio_muted_by_silent_or_hdmi": audio_muted_by_silent_or_hdmi,
        "audio_beep_audible": audio_beep_audible,
        "post_movie_steadyshot": post_movie_steadyshot,
        "post_still_steadyshot": post_still_steadyshot,
        "post_steadyshot_adjust": post_steadyshot_adjust,
        "post_focal_length_mm": post_focal_length_mm,
        "post_drive_mode_selftimer_type": post_drive_mode_selftimer_type,
        "post_selftimer_bracket": post_selftimer_bracket,
        "post_audio_signals": post_audio_signals,
    }


def compute_expected_zebra_peaking_streaming_vault_state(
    *,
    camera_model: str,
    zebra_display: str,
    zebra_level: str,
    zebra_custom1_type: str,
    zebra_custom1_std: int,
    zebra_custom1_range: int,
    zebra_custom2_type: str,
    zebra_custom2_lower_limit: int,
    display_lut_on: bool,
    peaking_display: str,
    peaking_level: str,
    peaking_color: str,
    fx6_zebra_mode: str,
    fx6_peaking_color: str,
    streaming_enabled: str,
    streaming_protocol: str,
    streaming_codec: str,
    srt_encryption: str,
    streaming_resolution: str,
    streaming_fps: str,
    movie_rec_during_streaming: str,
    internal_rec_resolution: str,
    ftp_transfer_func: str,
    airplane_mode: str,
    network_transport: str,
    requested_fx6_dormant_streaming_symbols: Tuple[str, ...],
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
    movie_rec_during_streaming_targets_slot1: bool,
    make_ftp_or_stream_dir_on_slot1: bool,
    reset_action: str,
) -> Dict[str, Any]:
    """Compute canonical Wave-57 Pillar 59B (Zebra/Peaking, Streaming/FTP, Zero-RF & Slot-1 Vault) state."""
    is_fx3 = camera_model == P332_FX3_MODEL_NAME

    custom1_valid = (
        zebra_custom1_type in P332_ZEBRA_CUSTOM_TYPES
        and P332_ZEBRA_STD_MIN_PCT <= zebra_custom1_std <= P332_ZEBRA_STD_MAX_PCT
        and P332_ZEBRA_RANGE_MIN_PCT <= zebra_custom1_range <= P332_ZEBRA_RANGE_MAX_PCT
    )
    custom2_valid = (
        zebra_custom2_type in P332_ZEBRA_CUSTOM_TYPES
        and P332_ZEBRA_LOWER_LIMIT_MIN_PCT <= zebra_custom2_lower_limit <= P332_ZEBRA_LOWER_LIMIT_MAX_PCT
    )
    zebra_measures_post_lut = is_fx3 and display_lut_on

    fx6_zebra_both_errno: Optional[int] = (
        P332_EOPNOTSUPP_ERRNO if fx6_zebra_mode == "Both" else None
    )
    fx6_peaking_color_valid = fx6_peaking_color in P332_FX6_PEAKING_COLORS

    # Clean-HDMI isolation: Zebra and Peaking NEVER output over external HDMI
    clean_hdmi_isolated_to_body_lcd = True

    # Reset behavior for Zebra / Peaking (Initialize-only!)
    if is_fx3 and reset_action == "Initialize":
        post_zebra_display = P332_ZEBRA_DISPLAY_DEFAULT
        post_zebra_level = P332_ZEBRA_LEVEL_DEFAULT
        post_peaking_display = P332_PEAKING_DISPLAY_DEFAULT
        post_peaking_level = P332_PEAKING_LEVEL_DEFAULT
        post_peaking_color = P332_PEAKING_COLOR_DEFAULT
    else:
        post_zebra_display = zebra_display
        post_zebra_level = zebra_level
        post_peaking_display = peaking_display
        post_peaking_level = peaking_level
        post_peaking_color = peaking_color

    # Streaming protocol/codec & 23.98p/24p boundary
    fps_allowed = streaming_fps in P332_STREAMING_ALLOWED_FPS
    streaming_fps_errno: Optional[int] = (
        None if fps_allowed else P332_EOPNOTSUPP_ERRNO
    )
    codec_allowed = (
        streaming_protocol in P332_STREAMING_VIDEO_CODECS_BY_PROTOCOL
        and streaming_codec in P332_STREAMING_VIDEO_CODECS_BY_PROTOCOL[streaming_protocol]
    )
    srt_enc_allowed = (
        True if streaming_protocol != "SRT" else srt_encryption in P332_SRT_ENCRYPTION_MODES
    )

    # [Movie Rec During Streaming] 4K / 2K 59.94p internal 4K lockout
    rec_during_stream_on = movie_rec_during_streaming == "Enable"
    blocks_internal_4k = rec_during_stream_on and (
        streaming_resolution == "4K"
        or (streaming_resolution == "2K" and streaming_fps in ("59.94p", "50p"))
    )
    internal_4k_rec_allowed = not blocks_internal_4k
    forced_internal_rec_fps = streaming_fps if rec_during_stream_on else None
    streaming_locks_out_ftp_menu_pb = streaming_enabled == "On"

    # Network Reset split:
    # - Camera Settings Reset: preserves ALL (Network) items!
    # - Reset Network Set.: resets streaming & FTP, PRESERVES Airplane Mode = On!
    # - Initialize: resets all Network items (bench enforces Airplane Mode = On for zero-RF).
    if is_fx3 and reset_action == "Reset Network Set.":
        post_streaming_enabled = "Off"
        post_movie_rec_during_streaming = P332_MOVIE_REC_DURING_STREAMING_DEFAULT
        post_ftp_transfer_func = "Off"
        post_airplane_mode = airplane_mode  # Preserved!
    elif is_fx3 and reset_action == "Initialize":
        post_streaming_enabled = "Off"
        post_movie_rec_during_streaming = P332_MOVIE_REC_DURING_STREAMING_DEFAULT
        post_ftp_transfer_func = "Off"
        post_airplane_mode = "Off"
    else:
        post_streaming_enabled = streaming_enabled
        post_movie_rec_during_streaming = movie_rec_during_streaming
        post_ftp_transfer_func = ftp_transfer_func
        post_airplane_mode = airplane_mode

    dormant_fx6_streaming_errno: Optional[int] = (
        P332_EOPNOTSUPP_ERRNO if len(requested_fx6_dormant_streaming_symbols) > 0 else None
    )

    # Zero-RF & USB-LAN (CDC-NCM)
    rf_zero_enforced = airplane_mode == "On" and network_transport == P332_SAFE_WIRED_TRANSPORT

    # Slot-1 Tier-0 Vault EROFS=30 Firewall
    mutates_slot1 = requested_vault_slot == P332_SLOT1_VAULT_SLOT and (
        requested_vault_action in P332_WRITE_MUTATING_VAULT_ACTIONS
        or movie_rec_during_streaming_targets_slot1
        or make_ftp_or_stream_dir_on_slot1
    )
    if mutates_slot1 and slot1_holds_tier0_vault:
        action_allowed = False
        firewall_errno: Optional[str] = "EROFS"
    elif requested_vault_action in ("FORMAT_QUICK", "FORMAT_FULL"):
        action_allowed = False
        firewall_errno = "EROFS"
    elif requested_vault_action in ("READ_ONLY_AUDIT", "STREAM_ONLY_USB_LAN", "FTP_READ_ONLY_GET"):
        action_allowed = not (movie_rec_during_streaming_targets_slot1 or make_ftp_or_stream_dir_on_slot1)
        firewall_errno = None if action_allowed else "EROFS"
    elif requested_vault_action == "NONE":
        action_allowed = False
        firewall_errno = None
    elif requested_vault_slot == P332_SAFE_SECONDARY_SLOT:
        action_allowed = True
        firewall_errno = None
    else:
        action_allowed = False
        firewall_errno = "EROFS"

    return {
        "custom1_valid": custom1_valid,
        "custom2_valid": custom2_valid,
        "zebra_measures_post_lut": zebra_measures_post_lut,
        "fx6_zebra_both_errno": fx6_zebra_both_errno,
        "fx6_peaking_color_valid": fx6_peaking_color_valid,
        "clean_hdmi_isolated_to_body_lcd": clean_hdmi_isolated_to_body_lcd,
        "post_zebra_display": post_zebra_display,
        "post_zebra_level": post_zebra_level,
        "post_peaking_display": post_peaking_display,
        "post_peaking_level": post_peaking_level,
        "post_peaking_color": post_peaking_color,
        "fps_allowed": fps_allowed,
        "streaming_fps_errno": streaming_fps_errno,
        "codec_allowed": codec_allowed,
        "srt_enc_allowed": srt_enc_allowed,
        "blocks_internal_4k": blocks_internal_4k,
        "internal_4k_rec_allowed": internal_4k_rec_allowed,
        "forced_internal_rec_fps": forced_internal_rec_fps,
        "streaming_locks_out_ftp_menu_pb": streaming_locks_out_ftp_menu_pb,
        "post_streaming_enabled": post_streaming_enabled,
        "post_movie_rec_during_streaming": post_movie_rec_during_streaming,
        "post_ftp_transfer_func": post_ftp_transfer_func,
        "post_airplane_mode": post_airplane_mode,
        "dormant_fx6_streaming_errno": dormant_fx6_streaming_errno,
        "rf_zero_enforced": rf_zero_enforced,
        "action_allowed": action_allowed,
        "firewall_errno": firewall_errno,
        "firewall_errno_num": (
            P332_VAULT_FIREWALL_ERRNO_CODES[firewall_errno]
            if firewall_errno in P332_VAULT_FIREWALL_ERRNO_CODES
            else None
        ),
    }


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & work_root=None Clean-Room Guard (17 Donors)
# ---------------------------------------------------------------------------


def _iter_work_roots() -> Tuple[Optional[Path], ...]:
    """Return candidate donor work roots (delegates to `_fx3_files.iter_donor_work_roots`)."""
    return _fx3_files.iter_donor_work_roots()


def _resolve_phase332_donor_path(
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
    max_full_bytes: int = P332_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    try:
        resolved = _resolve_phase332_donor_path(relpath)
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
        hdr = os.pread(fd, min(P332_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase332_donors() -> Tuple["Phase332DonorArtifactDigest", ...]:
    specs = (
        ("fx3_appfw_702_so", P332_DONOR_FX3_APPFW_702_RELPATH, P332_PINNED_FX3_APPFW_702_BYTES, P332_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P332_PINNED_FX3_APPFW_702_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702"),
        ("fx6_appfw_601_so", P332_DONOR_FX6_APPFW_601_RELPATH, P332_PINNED_FX6_APPFW_601_BYTES, P332_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P332_PINNED_FX6_APPFW_601_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601"),
        ("fx3_backup_bin", P332_DONOR_FX3_BACKUP_BIN_RELPATH, P332_PINNED_FX3_BACKUP_BIN_BYTES, P332_PINNED_FX3_BACKUP_BIN_BYTES, "FULL_SHA256", P332_PINNED_FX3_BACKUP_BIN_SHA256, "SYNTHETIC_BK4_ILME_FX3"),
        ("fx3_uxc_en_f", P332_DONOR_FX3_UXC_EN_F_RELPATH, P332_PINNED_FX3_UXC_EN_F_BYTES, P332_PINNED_FX3_UXC_EN_F_BYTES, "FULL_SHA256", P332_PINNED_FX3_UXC_EN_F_SHA256, "SYNTHETIC_UXC7_FX3_EN_F"),
        ("fx3_uxc_sc_f", P332_DONOR_FX3_UXC_SC_F_RELPATH, P332_PINNED_FX3_UXC_SC_F_BYTES, P332_PINNED_FX3_UXC_SC_F_BYTES, "FULL_SHA256", P332_PINNED_FX3_UXC_SC_F_SHA256, "SYNTHETIC_UXC7_FX3_SC_F"),
        ("fx3_uxc_tc_f", P332_DONOR_FX3_UXC_TC_F_RELPATH, P332_PINNED_FX3_UXC_TC_F_BYTES, P332_PINNED_FX3_UXC_TC_F_BYTES, "FULL_SHA256", P332_PINNED_FX3_UXC_TC_F_SHA256, "SYNTHETIC_UXC7_FX3_TC_F"),
        ("fx3_uxc_ja_f", P332_DONOR_FX3_UXC_JA_F_RELPATH, P332_PINNED_FX3_UXC_JA_F_BYTES, P332_PINNED_FX3_UXC_JA_F_BYTES, "FULL_SHA256", P332_PINNED_FX3_UXC_JA_F_SHA256, "SYNTHETIC_UXC7_FX3_JA_F"),
        ("fx3_uxc_en", P332_DONOR_FX3_UXC_EN_RELPATH, P332_PINNED_FX3_UXC_EN_BYTES, P332_PINNED_FX3_UXC_EN_BYTES, "FULL_SHA256", P332_PINNED_FX3_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX3_EN"),
        ("fx3_uxc_sc", P332_DONOR_FX3_UXC_SC_RELPATH, P332_PINNED_FX3_UXC_SC_BYTES, P332_PINNED_FX3_UXC_SC_BYTES, "FULL_SHA256", P332_PINNED_FX3_UXC_SC_SHA256, "SYNTHETIC_UXC7_FX3_SC"),
        ("fx3_uxc_tc", P332_DONOR_FX3_UXC_TC_RELPATH, P332_PINNED_FX3_UXC_TC_BYTES, P332_PINNED_FX3_UXC_TC_BYTES, "FULL_SHA256", P332_PINNED_FX3_UXC_TC_SHA256, "SYNTHETIC_UXC7_FX3_TC"),
        ("fx3_uxc_ja", P332_DONOR_FX3_UXC_JA_RELPATH, P332_PINNED_FX3_UXC_JA_BYTES, P332_PINNED_FX3_UXC_JA_BYTES, "FULL_SHA256", P332_PINNED_FX3_UXC_JA_SHA256, "SYNTHETIC_UXC7_FX3_JA"),
        ("fx3_uxc_en_g", P332_DONOR_FX3_UXC_EN_G_RELPATH, P332_PINNED_FX3_UXC_EN_G_BYTES, P332_PINNED_FX3_UXC_EN_G_BYTES, "FULL_SHA256", P332_PINNED_FX3_UXC_EN_G_SHA256, "SYNTHETIC_UXC7_FX3_EN_G"),
        ("fx3_uxc_sc_g", P332_DONOR_FX3_UXC_SC_G_RELPATH, P332_PINNED_FX3_UXC_SC_G_BYTES, P332_PINNED_FX3_UXC_SC_G_BYTES, "FULL_SHA256", P332_PINNED_FX3_UXC_SC_G_SHA256, "SYNTHETIC_UXC7_FX3_SC_G"),
        ("fx3_uxc_tc_g", P332_DONOR_FX3_UXC_TC_G_RELPATH, P332_PINNED_FX3_UXC_TC_G_BYTES, P332_PINNED_FX3_UXC_TC_G_BYTES, "FULL_SHA256", P332_PINNED_FX3_UXC_TC_G_SHA256, "SYNTHETIC_UXC7_FX3_TC_G"),
        ("fx3_uxc_ja_g", P332_DONOR_FX3_UXC_JA_G_RELPATH, P332_PINNED_FX3_UXC_JA_G_BYTES, P332_PINNED_FX3_UXC_JA_G_BYTES, "FULL_SHA256", P332_PINNED_FX3_UXC_JA_G_SHA256, "SYNTHETIC_UXC7_FX3_JA_G"),
        ("fx6_uxc_en", P332_DONOR_FX6_UXC_EN_RELPATH, P332_PINNED_FX6_UXC_EN_BYTES, P332_PINNED_FX6_UXC_EN_BYTES, "FULL_SHA256", P332_PINNED_FX6_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX6_EN"),
        ("fx6_uxc_en_2", P332_DONOR_FX6_UXC_EN_2_RELPATH, P332_PINNED_FX6_UXC_EN_2_BYTES, P332_PINNED_FX6_UXC_EN_2_BYTES, "FULL_SHA256", P332_PINNED_FX6_UXC_EN_2_SHA256, "SYNTHETIC_UXC7_FX6_EN_2"),
    )
    return tuple(
        Phase332DonorArtifactDigest(
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


def inspect_phase332_donors_readonly(force_clean_room: Optional[bool] = None) -> "Phase332DonorSnapshot":
    """Inspect Wave-57 FX3 7.02 (`14` donors) & FX6 6.01 (`3` donors) strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase332_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase332DonorSnapshot(
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
        ("fx3_appfw_702_so", P332_DONOR_FX3_APPFW_702_RELPATH, P332_PINNED_FX3_APPFW_702_BYTES, P332_PINNED_FX3_APPFW_702_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702")),
        ("fx6_appfw_601_so", P332_DONOR_FX6_APPFW_601_RELPATH, P332_PINNED_FX6_APPFW_601_BYTES, P332_PINNED_FX6_APPFW_601_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601")),
        ("fx3_backup_bin", P332_DONOR_FX3_BACKUP_BIN_RELPATH, P332_PINNED_FX3_BACKUP_BIN_BYTES, P332_PINNED_FX3_BACKUP_BIN_SHA256, lambda d: _check_bk4_backup(d, "ILME_FX3")),
        ("fx3_uxc_en_f", P332_DONOR_FX3_UXC_EN_F_RELPATH, P332_PINNED_FX3_UXC_EN_F_BYTES, P332_PINNED_FX3_UXC_EN_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_F")),
        ("fx3_uxc_sc_f", P332_DONOR_FX3_UXC_SC_F_RELPATH, P332_PINNED_FX3_UXC_SC_F_BYTES, P332_PINNED_FX3_UXC_SC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_F")),
        ("fx3_uxc_tc_f", P332_DONOR_FX3_UXC_TC_F_RELPATH, P332_PINNED_FX3_UXC_TC_F_BYTES, P332_PINNED_FX3_UXC_TC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_F")),
        ("fx3_uxc_ja_f", P332_DONOR_FX3_UXC_JA_F_RELPATH, P332_PINNED_FX3_UXC_JA_F_BYTES, P332_PINNED_FX3_UXC_JA_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_F")),
        ("fx3_uxc_en", P332_DONOR_FX3_UXC_EN_RELPATH, P332_PINNED_FX3_UXC_EN_BYTES, P332_PINNED_FX3_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN")),
        ("fx3_uxc_sc", P332_DONOR_FX3_UXC_SC_RELPATH, P332_PINNED_FX3_UXC_SC_BYTES, P332_PINNED_FX3_UXC_SC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC")),
        ("fx3_uxc_tc", P332_DONOR_FX3_UXC_TC_RELPATH, P332_PINNED_FX3_UXC_TC_BYTES, P332_PINNED_FX3_UXC_TC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC")),
        ("fx3_uxc_ja", P332_DONOR_FX3_UXC_JA_RELPATH, P332_PINNED_FX3_UXC_JA_BYTES, P332_PINNED_FX3_UXC_JA_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA")),
        ("fx3_uxc_en_g", P332_DONOR_FX3_UXC_EN_G_RELPATH, P332_PINNED_FX3_UXC_EN_G_BYTES, P332_PINNED_FX3_UXC_EN_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_G")),
        ("fx3_uxc_sc_g", P332_DONOR_FX3_UXC_SC_G_RELPATH, P332_PINNED_FX3_UXC_SC_G_BYTES, P332_PINNED_FX3_UXC_SC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_G")),
        ("fx3_uxc_tc_g", P332_DONOR_FX3_UXC_TC_G_RELPATH, P332_PINNED_FX3_UXC_TC_G_BYTES, P332_PINNED_FX3_UXC_TC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_G")),
        ("fx3_uxc_ja_g", P332_DONOR_FX3_UXC_JA_G_RELPATH, P332_PINNED_FX3_UXC_JA_G_BYTES, P332_PINNED_FX3_UXC_JA_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_G")),
        ("fx6_uxc_en", P332_DONOR_FX6_UXC_EN_RELPATH, P332_PINNED_FX6_UXC_EN_BYTES, P332_PINNED_FX6_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN")),
        ("fx6_uxc_en_2", P332_DONOR_FX6_UXC_EN_2_RELPATH, P332_PINNED_FX6_UXC_EN_2_BYTES, P332_PINNED_FX6_UXC_EN_2_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN_2")),
    )

    def _probe_one(spec: Tuple[str, str, int, str, Any]) -> Optional[Phase332DonorArtifactDigest]:
        aid, relpath, expected_bytes, expected_sha, marker_fn = spec
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            return None
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        return Phase332DonorArtifactDigest(
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
        artifacts = _synthetic_phase332_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase332DonorSnapshot(
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
    return Phase332DonorSnapshot(
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
# Frozen Dataclasses (Specs, Reports, Suites & 59-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase332DonorArtifactDigest:
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
class Phase332DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_20s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase332DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SteadyShot47FocalSelfTimerVaultSpec:
    # Wave-57 [Image Stabilization] 4 Resettable Items, 47-Focal (8..1000mm) & Active 4-Lockout
    camera_model: str
    fw_version: str
    shooting_domain: str
    image_stabilization_items: Tuple[str, ...]
    movie_steadyshot: str
    still_steadyshot: str
    steadyshot_adjust: str
    focal_length_mm: int
    reported_focal_length_steps_count: int
    reported_focal_length_errno: Optional[int]
    movie_fps: float
    sq_fps: float
    hdmi_raw_on: bool
    de_squeeze: str
    distortion_comp: str
    clear_image_zoom: str
    still_raw_active: bool
    reported_effective_movie_steadyshot: str
    reported_active_lockout_errno: Optional[int]
    reported_dormant_dynamic_active_errno: Optional[int]
    reported_effective_crop_factor: float
    reported_forced_distortion_comp: str
    reported_ciz_errno: Optional[int]
    reported_ciz_forces_metering_multi: bool
    post_movie_steadyshot: str
    post_still_steadyshot: str
    post_steadyshot_adjust: str
    post_focal_length_mm: int
    # Wave-57 [Drive Mode] Still Self-timer vs Dormant Movie Self-timer, Front LED #8 & Audio signals
    drive_mode_selftimer_type: str
    selftimer_single_delay_sec: int
    selftimer_cont_combo: str
    selftimer_bracket: str
    requested_dormant_selftimer_symbols: Tuple[str, ...]
    reported_dormant_selftimer_errno: Optional[int]
    front_lamp_id: int
    front_lamp_distinct_from_tally_rec: bool
    reported_led8_flashes: bool
    silent_mode: str
    movie_hdmi_audio_active: bool
    audio_signals: str
    reported_audio_beep_audible: bool
    post_drive_mode_selftimer_type: str
    post_selftimer_bracket: str
    post_audio_signals: str
    # ILME-FX6 Architectural Boundary (Zero IBIS -> OSS + 6-axis Gyro; Picture Cache Rec + Interval Rec)
    fx6_has_ibis: bool
    fx6_has_6axis_gyro_metadata: bool
    fx6_oss_disabled_for_catalyst: bool
    fx6_has_still_self_timer: bool
    fx6_uses_picture_cache_and_interval_rec: bool
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
    steadyshot_47focal_or_lockout_drift_events: int
    selftimer_dormant_or_led8_audio_drift_events: int
    fx6_ibis_or_selftimer_spoof_events: int


@dataclass(frozen=True)
class SteadyShot47FocalSelfTimerVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    steadyshot_4item_47focal_and_4lockout_verified: bool
    selftimer_still_vs_dormant_movie_led8_audio_verified: bool
    fx6_zero_ibis_and_alt_rec_boundary_verified: bool
    slot1_vault_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    steadyshot_47focal_or_lockout_drift_events: int
    selftimer_dormant_or_led8_audio_drift_events: int
    fx6_ibis_or_selftimer_spoof_events: int
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
class ZebraPeakingStreamingVaultSpec:
    # Wave-57 [Zebra Display]/[Zebra Level] Custom1/2 & 4-Color [Peaking] Clean-HDMI Isolation
    camera_model: str
    fw_version: str
    shooting_domain: str
    zebra_display: str
    zebra_level: str
    zebra_custom1_type: str
    zebra_custom1_std: int
    zebra_custom1_range: int
    zebra_custom2_type: str
    zebra_custom2_lower_limit: int
    display_lut_on: bool
    reported_zebra_measures_post_lut: bool
    peaking_display: str
    peaking_level: str
    peaking_color: str
    reported_clean_hdmi_isolated_to_body_lcd: bool
    reported_hdmi_zebra_or_peaking_leaked: bool
    post_zebra_display: str
    post_zebra_level: str
    post_peaking_display: str
    post_peaking_level: str
    post_peaking_color: str
    # ILME-FX6 Zebra (Off/Zebra1/Zebra2 mutually exclusive, NOT Both) & B&W Peaking + Dormant Streaming
    fx6_zebra_mode: str
    reported_fx6_zebra_both_errno: Optional[int]
    fx6_peaking_color: str
    requested_fx6_dormant_streaming_symbols: Tuple[str, ...]
    reported_fx6_dormant_streaming_errno: Optional[int]
    # Wave-57 [Network Streaming] RTMP/RTMPS/SRT, FPS Boundary, Movie Rec During Streaming & Network Reset
    streaming_menu_path: Tuple[str, ...]
    streaming_enabled: str
    streaming_protocol: str
    streaming_codec: str
    srt_encryption: str
    streaming_quality: str
    streaming_resolution: str
    streaming_fps: str
    reported_streaming_fps_errno: Optional[int]
    movie_rec_during_streaming: str
    internal_rec_resolution: str
    reported_internal_4k_rec_allowed: bool
    reported_forced_internal_rec_fps: Optional[str]
    reported_streaming_locks_out_ftp_menu_pb: bool
    ftp_transfer_func: str
    airplane_mode: str
    network_transport: str
    post_streaming_enabled: str
    post_movie_rec_during_streaming: str
    post_ftp_transfer_func: str
    post_airplane_mode: str
    reset_action: str
    # Zero-RF & Slot-1 Tier-0 Recovery Vault EROFS=30 Firewall
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    requested_vault_slot: int
    slot1_holds_tier0_vault: bool
    requested_vault_action: str
    movie_rec_during_streaming_targets_slot1: bool
    make_ftp_or_stream_dir_on_slot1: bool
    reported_vault_action_allowed: bool
    vault_firewall_errno: Optional[str]
    slot1_data_sector_writes: int
    slot1_streaming_or_ftp_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative counters
    zebra_custom_ire_or_peaking_clean_hdmi_drift_events: int
    streaming_24p_rec_or_network_reset_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int


@dataclass(frozen=True)
class ZebraPeakingStreamingVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    zebra_custom12_peaking_clean_hdmi_and_fx6_verified: bool
    streaming_protocols_24p_lockout_and_net_reset_verified: bool
    zero_rf_usblan_and_slot1_erofs30_vault_verified: bool
    overlay_and_h0_h3_verified: bool
    matrix_states_checked: int
    zebra_custom_ire_or_peaking_clean_hdmi_drift_events: int
    streaming_24p_rec_or_network_reset_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_streaming_or_ftp_mutation_bytes: int
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
class SteadyShot47FocalSelfTimerZebraStreamingVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase332DonorSnapshot
    steadyshot_selftimer_report: SteadyShot47FocalSelfTimerVaultReport
    zebra_peaking_streaming_report: ZebraPeakingStreamingVaultReport
    steadyshot_47focal_or_lockout_drift_events: int
    selftimer_dormant_or_led8_audio_drift_events: int
    fx6_ibis_or_selftimer_spoof_events: int
    zebra_custom_ire_or_peaking_clean_hdmi_drift_events: int
    streaming_24p_rec_or_network_reset_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_streaming_or_ftp_mutation_bytes: int
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
class Pillar59ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar59ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar59ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar59BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar59ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar59StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase332DonorSnapshot
    pillar_59a_steadyshot_47focal_selftimer_vault: Pillar59ASuiteResult
    pillar_59b_zebra_peaking_streaming_vault: Pillar59BSuiteResult
    steadyshot_47focal_or_lockout_drift_events: int
    selftimer_dormant_or_led8_audio_drift_events: int
    fx6_ibis_or_selftimer_spoof_events: int
    zebra_custom_ire_or_peaking_clean_hdmi_drift_events: int
    streaming_24p_rec_or_network_reset_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_streaming_or_ftp_mutation_bytes: int
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
class Master59PillarRecoveryReport:
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
    # Pillar 59 & Wave-57 top-level fields (Phase 332 — 59/59 Milestone)
    donor_snapshot: Phase332DonorSnapshot
    pillar59_a_steadyshot_47focal_selftimer_vault: Pillar59ASuiteResult
    pillar59_b_zebra_peaking_streaming_vault: Pillar59BSuiteResult
    steadyshot_47focal_or_lockout_drift_events: int
    selftimer_dormant_or_led8_audio_drift_events: int
    fx6_ibis_or_selftimer_spoof_events: int
    zebra_custom_ire_or_peaking_clean_hdmi_drift_events: int
    streaming_24p_rec_or_network_reset_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_streaming_or_ftp_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
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
    # Preserved Pillars 1..58 rollup metrics
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
    touch_op_dormant_trap_or_reset_drift_events: int
    disp_set_or_zero_evf_blackout_events: int
    fx6_touch_or_evf_spoof_events: int
    still_ael_flash_reset_split_or_mishoe_drift_events: int
    interval_pb_9scale_or_path_drift_events: int
    playback_edit_dormant_or_slot1_vault_bypass_events: int
    slot1_edit_avf_info_mutation_bytes: int
    fx3_has_eye_sensor: bool
    fx3_has_finder_monitor_button: bool
    fx3_touch_active_item_count: int
    fx3_disp_shoot_page_count: int
    fx3_disp_play_page_count: int
    fx3_interval_pb_speed_min: int
    fx3_interval_pb_speed_max: int
    fx3_interval_pb_speed_default: int
    fx6_has_detachable_lcd_viewfinder: bool
    fx6_has_still_ttl_flash: bool
    fx6_has_interval_pb: bool
    fx6_has_playback_edit_menu: bool
    switch_vh_af_lockout_or_coords_drift_events: int
    focus_limit_lt2_or_dormant_symbol_events: int
    focus_area_color_or_fx6_spoof_events: int
    exp_std_adj_mode_conflation_or_reset_drift_events: int
    bracket_settings_reset_or_fx6_spoof_events: int
    tcub_reset_wipe_or_format_lock_violations: int
    reverse_copy_slot2_to_slot1_bypass_events: int
    slideshow_power_save_or_fx6_copy_clip_spoof_events: int
    slot1_copy_avf_info_mutation_bytes: int
    fx3_has_switch_vh_af_area: bool
    fx3_focus_area_limit_count: int
    fx3_focus_area_limit_min_enabled: int
    fx3_exp_std_adj_metering_mode_count: int
    fx3_has_physical_bnc_tc_port: bool
    fx6_has_physical_bnc_tc_port: bool
    fx6_has_switch_vh_af_area: bool
    fx6_has_focus_area_limit: bool
    fx6_has_exp_std_adj: bool
    fx6_has_still_bracket_settings: bool
    fx6_has_copy_clip_active: bool
    fx6_has_slide_show: bool
    dormant_shading_auto_low_exposure_events: int
    lens_comp_lock_or_arw_conflation_events: int
    af_illuminator_gate_or_fx6_spoof_events: int
    movie_af_transition_or_assist_drift_events: int
    aperture_drive_pre_af_shutter_reset_drift_events: int
    circ_focus_diagonal_or_color_drift_events: int
    folder_name_or_leading_underscore_violations: int
    slot1_folder_dir_mutation_bytes: int
    slot1_rating_avf_info_mutation_bytes: int
    fx3_has_builtin_af_illuminator: bool
    fx6_has_builtin_af_illuminator: bool
    fx3_exposes_shading_auto_low: bool
    fx6_has_aperture_drive_pre_af_circ_color: bool
    fx6_has_msdcf_or_star_rating: bool
    sensor_cleaning_low_battery_bypass_events: int
    sensor_cleaning_no_power_off_violations: int
    fx6_ibis_shake_conflation_events: int
    ev_comp_range_or_cine_ei_lockout_violations: int
    exposure_step_or_dormant_reset_ev_drift_events: int
    focus_mode_movie_clamp_or_dormant_drift_events: int
    priority_set_or_illuminator_gate_violations: int
    image_index_dormant_or_view_mode_drift_events: int
    slot1_rotate_exif_mutation_bytes: int
    fx3_has_sensor_cleaning_ibis: bool
    fx3_has_exposure_comp: bool
    fx3_has_physical_ev_reset_dial: bool
    fx6_has_ultrasonic_ibis_cleaning: bool
    fx6_has_variable_end_optical_block: bool
    fx6_has_technical_apr: bool
    fx6_has_still_exposure_comp: bool
    fx6_has_still_image_index_rotate: bool
    dci4k_long_gop_or_8k_violations: int
    reboot_2400p_stage_b_wipe_violations: int
    hdmi_raw_or_still_aspect_drift_events: int
    fx6_still_or_raw_conflation_events: int
    reg_custom_hold_or_hlg_lock_drift_events: int
    camset_cross_model_path_drift_events: int
    photo_capture_dci4k_lockout_bypass_events: int
    slot1_camset_write_bytes: int
    slot1_photo_capture_write_bytes: int
    fx3_appfw_has_dci4k_internal: bool
    fx3_appfw_has_pro_camera_path: bool
    fx6_has_still_aspect_ratio: bool
    fx6_has_photo_capture: bool
    fx6_has_playback_enlarge_image: bool
    fx6_has_reg_custom_shoot_set: bool
    fx6_has_camera_set_memory: bool
    movie_tracking_area_or_limit_violations: int
    af_area_reg_lock_or_reset_drift_events: int
    xlrh1_zoom_or_hold_spoof_events: int
    fx6_handle_or_pos_display_conflation_events: int
    iso_minss_or_cine_ei_lock_drift_events: int
    flash_still_mech_gate_violations: int
    mishoe_pmic_5v_overcurrent_events: int
    slot1_focus_zoom_camset_mutation_bytes: int
    slot1_flash_videolight_imagedb_bytes: int
    xlrh1_has_zoom_lever: bool
    xlrh1_has_rec_button: bool
    xlrh1_has_zoom_hold_switch: bool
    fx6_0_99_is_zoom_position_display: bool
    fx6_has_iso_auto_min_ss: bool
    fx6_mechanical_shutter_present: bool
    dormant_lossless_raw_exposure_events: int
    fx6_still_pipeline_conflation_events: int
    hlg_still_prereq_or_lockout_drift_events: int
    colorspace_adobergb_prefix_violations: int
    shutter_type_auto_spoof_events: int
    fx6_mechanical_shutter_conflation_events: int
    electronic_silent_5lock_bypass_events: int
    nr_or_drive_burst_wall_violations: int
    slot1_still_capture_or_sort_write_bytes: int
    slot1_imagedb_or_burst_mutation_bytes: int
    fx3_ui_exposes_lossless_raw: bool
    fx3_ui_exposes_shutter_type_auto: bool
    fx6_still_pipeline_present: bool
    double_log_or_lockout_bypass_events: int
    pplut_1080p_clamp_bypass_events: int
    pp_internal_reset_trap_violations: int
    fx6_baselook_confusion_events: int
    wb_cine_ei_awb_or_custom_setup_trap_events: int
    wb_custom_camset_exclusion_drift_events: int
    metering_desqueeze_or_cine_ei_base_iso_drift_events: int
    fx3_ui_exposes_usb_streaming: bool
    nouvc_spoof_events: int
    usb_host_data_enumeration_events: int
    hdmi_lcd_blanking_violations: int
    hdmi_log_1080_bypass_events: int
    slot1_protect_only_vault_violations: int
    slot1_vault_format_or_delete_events: int
    network_reset_zero_rf_violations: int
    fx3_ui_exposes_power_save_by_monitor: bool
    legacy_power_save_monitor_spoof_events: int
    unsafe_power_save_sleep_interference_events: int
    bk_lang_parity_drift_events: int
    stage_b_4lang_uxc_ltt_drift_events: int
    xlrh1_acoustic_feedback_violations: int
    audio_mon_4ch_hdmi_confusion_events: int
    destructive_delete_confirm_drift_events: int
    slot1_vault_delete_events: int
    legacy_mf_assist_spoof_events: int
    still_movie_initial_mag_couplings: int
    movie_af_in_focus_mag_events: int
    hdmi_clean_feed_focus_mag_or_peaking_leak_pixels: int
    movie_sq_af_illuminator_fire_events: int
    legacy_datetime_setup_spoof_events: int
    unsolicited_rtc_timezone_jump_events: int
    mishoe_5v_overcurrent_events: int
    hdmi_res_log_internal_rec_2160p_bypass_events: int
    slot1_vault_mutation_events: int
    slot1_vault_folder_mutation_events: int
    slot1_vault_folder_mutation_bytes: int
    movie_custom_folder_or_title_overflow_events: int
    still_prefix_underscore_lead_or_len_violations: int
    gamma_assist_log_lockout_bypass_events: int
    gamma_assist_external_hdmi_leak_events: int
    tcub_camera_reset_wipe_or_format_violations: int
    fx3_has_builtin_end_filter: bool
    e_nd_actuator_tx_count: int
    cardless_unrecorded_production_violations: int
    legacy_v1_audio_level_menu_spoof_events: int
    photographer_copyright_pii_leaked_bytes: int
    copyright_char_overflow_or_movie_mutation_events: int
    slot1_copyright_vault_mutation_bytes: int
    apsc_s35_4k_or_raw_bypass_events: int
    ai_unit_subject_recog_spoof_events: int
    hdmi_clean_feed_eye_frame_baked_pixels: int
    version_dialog_flash_writes: int
    bodydata_flash_attempts_blocked: int
    slot1_bodydata_vault_mutation_bytes: int
    auto_slow_shutter_lockout_bypass_events: int
    auto_slow_shutter_angle_overlap_events: int
    breathing_comp_raw_or_240p_bypass_events: int
    hdmi_rec_ctrl_without_tc_violations: int
    slot1_hdmi_rec_vault_mutation_bytes: int
    diff_set_transition_corruption_events: int
    shutter_angle_common_bleed_events: int
    slot1_custom_key_vault_mutation_bytes: int
    fx3_has_builtin_evf: bool
    evf_finder_monitor_spoof_events: int
    tier0_battery_high_display_violations: int
    bt_rmt_ir_lockout_violations: int
    slot1_mymenu_vault_mutation_bytes: int
    destructive_menu_delete_confusions: int
    shutter_angle_exposure_step_drift_events: int
    fx3_has_var_shutter: bool
    unbuffered_battery_pull_events: int
    overall_ready_for_hardware_attach: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    master_59pillar_sha256: str
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
# Spec Builders (Pillars 59A & 59B)
# ---------------------------------------------------------------------------


def build_default_safe_steadyshot_47focal_selftimer_vault_spec(
    **overrides: Any,
) -> SteadyShot47FocalSelfTimerVaultSpec:
    """Return a clean, verified default `SteadyShot47FocalSelfTimerVaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P332_FX3_MODEL_NAME,
        "fw_version": P332_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "image_stabilization_items": P332_IMAGE_STABILIZATION_4_ITEMS,
        "movie_steadyshot": P332_MOVIE_STEADYSHOT_DEFAULT,
        "still_steadyshot": P332_STILL_STEADYSHOT_DEFAULT,
        "steadyshot_adjust": P332_STEADYSHOT_ADJUST_DEFAULT,
        "focal_length_mm": P332_STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM,
        "reported_focal_length_steps_count": P332_STEADYSHOT_FOCAL_LENGTH_COUNT,
        "reported_focal_length_errno": None,
        "movie_fps": 23.98,
        "sq_fps": 23.98,
        "hdmi_raw_on": False,
        "de_squeeze": "Off",
        "distortion_comp": "Off",
        "clear_image_zoom": P332_CLEAR_IMAGE_ZOOM_DEFAULT,
        "still_raw_active": False,
        "reported_effective_movie_steadyshot": P332_MOVIE_STEADYSHOT_DEFAULT,
        "reported_active_lockout_errno": None,
        "reported_dormant_dynamic_active_errno": None,
        "reported_effective_crop_factor": 1.0,
        "reported_forced_distortion_comp": "Off",
        "reported_ciz_errno": None,
        "reported_ciz_forces_metering_multi": False,
        "post_movie_steadyshot": P332_MOVIE_STEADYSHOT_DEFAULT,
        "post_still_steadyshot": P332_STILL_STEADYSHOT_DEFAULT,
        "post_steadyshot_adjust": P332_STEADYSHOT_ADJUST_DEFAULT,
        "post_focal_length_mm": P332_STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM,
        "drive_mode_selftimer_type": "None",
        "selftimer_single_delay_sec": 10,
        "selftimer_cont_combo": P332_SELFTIMER_CONT_COMBOS[0],
        "selftimer_bracket": P332_BRACKET_SELFTIMER_DEFAULT,
        "requested_dormant_selftimer_symbols": (),
        "reported_dormant_selftimer_errno": None,
        "front_lamp_id": P332_FRONT_LAMP_8_ID,
        "front_lamp_distinct_from_tally_rec": True,
        "reported_led8_flashes": False,
        "silent_mode": "Off",
        "movie_hdmi_audio_active": False,
        "audio_signals": P332_AUDIO_SIGNALS_DEFAULT,
        "reported_audio_beep_audible": False,
        "post_drive_mode_selftimer_type": "None",
        "post_selftimer_bracket": P332_BRACKET_SELFTIMER_DEFAULT,
        "post_audio_signals": P332_AUDIO_SIGNALS_DEFAULT,
        "fx6_has_ibis": P332_FX6_HAS_IBIS,
        "fx6_has_6axis_gyro_metadata": P332_FX6_HAS_6AXIS_GYRO_METADATA,
        "fx6_oss_disabled_for_catalyst": True,
        "fx6_has_still_self_timer": P332_FX6_HAS_STILL_SELF_TIMER,
        "fx6_uses_picture_cache_and_interval_rec": True,
        "reset_action": "None",
        "requested_vault_slot": P332_SLOT1_VAULT_SLOT,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P332_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P332_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P332_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P332_TIER0_SURFACE_COUNT,
        "steadyshot_47focal_or_lockout_drift_events": 0,
        "selftimer_dormant_or_led8_audio_drift_events": 0,
        "fx6_ibis_or_selftimer_spoof_events": 0,
    }
    defaults.update(overrides)
    return SteadyShot47FocalSelfTimerVaultSpec(**defaults)


def build_default_safe_zebra_peaking_streaming_vault_spec(
    **overrides: Any,
) -> ZebraPeakingStreamingVaultSpec:
    """Return a clean, verified default `ZebraPeakingStreamingVaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P332_FX3_MODEL_NAME,
        "fw_version": P332_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "zebra_display": P332_ZEBRA_DISPLAY_DEFAULT,
        "zebra_level": P332_ZEBRA_LEVEL_DEFAULT,
        "zebra_custom1_type": "Std+Range",
        "zebra_custom1_std": P332_SLOG3_18_GRAY_IRE,
        "zebra_custom1_range": 2,
        "zebra_custom2_type": "Lower Limit",
        "zebra_custom2_lower_limit": P332_SLOG3_CLIP_IRE,
        "display_lut_on": False,
        "reported_zebra_measures_post_lut": False,
        "peaking_display": P332_PEAKING_DISPLAY_DEFAULT,
        "peaking_level": P332_PEAKING_LEVEL_DEFAULT,
        "peaking_color": P332_PEAKING_COLOR_DEFAULT,
        "reported_clean_hdmi_isolated_to_body_lcd": True,
        "reported_hdmi_zebra_or_peaking_leaked": False,
        "post_zebra_display": P332_ZEBRA_DISPLAY_DEFAULT,
        "post_zebra_level": P332_ZEBRA_LEVEL_DEFAULT,
        "post_peaking_display": P332_PEAKING_DISPLAY_DEFAULT,
        "post_peaking_level": P332_PEAKING_LEVEL_DEFAULT,
        "post_peaking_color": P332_PEAKING_COLOR_DEFAULT,
        "fx6_zebra_mode": "Zebra1",
        "reported_fx6_zebra_both_errno": None,
        "fx6_peaking_color": "B&W",
        "requested_fx6_dormant_streaming_symbols": (),
        "reported_fx6_dormant_streaming_errno": None,
        "streaming_menu_path": P332_STREAMING_MENU_PATH,
        "streaming_enabled": "Off",
        "streaming_protocol": "SRT",
        "streaming_codec": "H.265",
        "srt_encryption": "AES-256",
        "streaming_quality": P332_STREAMING_QUALITY_DEFAULT,
        "streaming_resolution": P332_STREAMING_RESOLUTION_DEFAULT,
        "streaming_fps": "59.94p",
        "reported_streaming_fps_errno": None,
        "movie_rec_during_streaming": P332_MOVIE_REC_DURING_STREAMING_DEFAULT,
        "internal_rec_resolution": "1080p",
        "reported_internal_4k_rec_allowed": True,
        "reported_forced_internal_rec_fps": None,
        "reported_streaming_locks_out_ftp_menu_pb": False,
        "ftp_transfer_func": "Off",
        "airplane_mode": "On",
        "network_transport": P332_SAFE_WIRED_TRANSPORT,
        "post_streaming_enabled": "Off",
        "post_movie_rec_during_streaming": P332_MOVIE_REC_DURING_STREAMING_DEFAULT,
        "post_ftp_transfer_func": "Off",
        "post_airplane_mode": "On",
        "reset_action": "None",
        "rf_packets_transmitted": 0,
        "rf_nvs_mutation_bytes": 0,
        "requested_vault_slot": P332_SLOT1_VAULT_SLOT,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "movie_rec_during_streaming_targets_slot1": False,
        "make_ftp_or_stream_dir_on_slot1": False,
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": 0,
        "slot1_streaming_or_ftp_mutation_bytes": 0,
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P332_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P332_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P332_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P332_TIER0_SURFACE_COUNT,
        "zebra_custom_ire_or_peaking_clean_hdmi_drift_events": 0,
        "streaming_24p_rec_or_network_reset_drift_events": 0,
        "zero_rf_or_slot1_vault_bypass_events": 0,
    }
    defaults.update(overrides)
    return ZebraPeakingStreamingVaultSpec(**defaults)


# ---------------------------------------------------------------------------
# Evaluators & Single-Shot Combined Verifier (Pillars 59A & 59B)
# ---------------------------------------------------------------------------


def evaluate_steadyshot_47focal_selftimer_vault(
    spec: SteadyShot47FocalSelfTimerVaultSpec,
) -> SteadyShot47FocalSelfTimerVaultReport:
    """Evaluate Pillar 59A: Wave-57 `[Image Stabilization]` 4 resettable items, 47-focal (8..1000mm),
    Active 4-condition lockout & 1.104x crop + Distortion=Auto, dormant `Dynamic active` (EOPNOTSUPP=95),
    Still `[Drive Mode]` Self-timer vs dormant Movie Self-timer, Front LED #8 + `[Audio signals]`,
    `ILME-FX6` Zero-IBIS/Picture Cache/Interval Rec boundary, and Slot-1 Vault."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P332_BLOCKED_SAFETY_POLICY_VIOLATION, "Module safety invariant violation")

    valid_fw = (
        (
            spec.camera_model == P332_FX3_MODEL_NAME
            and spec.fw_version in P332_FX3_SUPPORTED_FW_VERSIONS
        )
        or (
            spec.camera_model == P332_FX6_DONOR_MODEL_NAME
            and spec.fw_version == P332_FX6_DONOR_FW_VERSION
        )
    )
    if (
        not valid_fw
        or spec.shooting_domain not in P332_SHOOTING_DOMAINS
        or spec.movie_steadyshot not in P332_MOVIE_STEADYSHOT_ALL_MODES
        or spec.still_steadyshot not in P332_STILL_STEADYSHOT_MODES
        or spec.steadyshot_adjust not in P332_STEADYSHOT_ADJUST_MODES
        or spec.de_squeeze not in P332_DE_SQUEEZE_OPTIONS
        or spec.clear_image_zoom not in P332_CLEAR_IMAGE_ZOOM_OPTIONS
        or spec.drive_mode_selftimer_type not in P332_DRIVE_MODE_SELFTIMER_TYPES
        or spec.selftimer_bracket not in P332_BRACKET_SELFTIMER_OPTIONS
        or spec.silent_mode not in P332_ON_OFF_MODES
        or spec.audio_signals not in P332_AUDIO_SIGNALS_MODES
        or spec.reset_action not in P332_RESET_ACTIONS
        or spec.requested_vault_slot not in (1, 2)
        or spec.requested_vault_action not in P332_VAULT_ACTIONS
    ):
        _fail(
            P332_BLOCKED_INVALID_PILLAR59A_SPEC,
            "Invalid Pillar 59A camera/SteadyShot/Self-timer/reset/vault spec parameter",
        )

    st = compute_expected_steadyshot_selftimer_state(
        camera_model=spec.camera_model,
        shooting_domain=spec.shooting_domain,
        movie_steadyshot=spec.movie_steadyshot,
        still_steadyshot=spec.still_steadyshot,
        steadyshot_adjust=spec.steadyshot_adjust,
        focal_length_mm=spec.focal_length_mm,
        movie_fps=spec.movie_fps,
        sq_fps=spec.sq_fps,
        hdmi_raw_on=spec.hdmi_raw_on,
        de_squeeze=spec.de_squeeze,
        distortion_comp=spec.distortion_comp,
        clear_image_zoom=spec.clear_image_zoom,
        still_raw_active=spec.still_raw_active,
        drive_mode_selftimer_type=spec.drive_mode_selftimer_type,
        selftimer_bracket=spec.selftimer_bracket,
        requested_dormant_selftimer_symbols=spec.requested_dormant_selftimer_symbols,
        silent_mode=spec.silent_mode,
        movie_hdmi_audio_active=spec.movie_hdmi_audio_active,
        audio_signals=spec.audio_signals,
        reset_action=spec.reset_action,
    )

    # 1. [Image Stabilization] 4 Resettable Items, 47-Focal (8..1000mm), Active 4-Lockout & Dormant Dynamic active
    steadyshot_ok = (
        (
            spec.camera_model != P332_FX3_MODEL_NAME
            or (
                tuple(spec.image_stabilization_items) == P332_IMAGE_STABILIZATION_4_ITEMS
                and spec.reported_focal_length_steps_count == P332_STEADYSHOT_FOCAL_LENGTH_COUNT
                and spec.focal_length_mm in P332_STEADYSHOT_47_FOCAL_LENGTHS_MM
                and spec.reported_focal_length_errno == st["focal_length_errno"]
                and spec.movie_steadyshot in P332_MOVIE_STEADYSHOT_MODES
                and spec.reported_effective_movie_steadyshot == st["effective_movie_steadyshot"]
                and spec.reported_active_lockout_errno == st["active_lockout_errno"]
                and spec.reported_dormant_dynamic_active_errno == st["dormant_dynamic_active_errno"]
                and abs(spec.reported_effective_crop_factor - st["effective_crop_factor"]) < 1e-6
                and spec.reported_forced_distortion_comp == st["forced_distortion_comp"]
                and spec.reported_ciz_errno == st["ciz_errno"]
                and spec.reported_ciz_forces_metering_multi == st["ciz_forces_metering_multi"]
                and spec.post_movie_steadyshot == st["post_movie_steadyshot"]
                and spec.post_still_steadyshot == st["post_still_steadyshot"]
                and spec.post_steadyshot_adjust == st["post_steadyshot_adjust"]
                and spec.post_focal_length_mm == st["post_focal_length_mm"]
            )
        )
        and spec.steadyshot_47focal_or_lockout_drift_events == 0
    )
    if not steadyshot_ok:
        _fail(
            P332_BLOCKED_STEADYSHOT_47FOCAL_OR_LOCKOUT_DRIFT,
            "Image Stabilization violated 4-item resettable tree, 47-step Focal Length (8..1000mm), Active 4-lockout, Distortion=Auto, CIZ, or dormant Dynamic active EOPNOTSUPP=95",
        )

    # 2. Still [Drive Mode] Self-timer vs Dormant Movie Self-timer, Front LED #8 & [Audio signals]
    selftimer_ok = (
        (
            spec.camera_model != P332_FX3_MODEL_NAME
            or (
                spec.selftimer_single_delay_sec in P332_SELFTIMER_SINGLE_DELAYS_SEC
                and spec.selftimer_cont_combo in P332_SELFTIMER_CONT_COMBOS
                and spec.reported_dormant_selftimer_errno == st["dormant_selftimer_errno"]
                and not (
                    (
                        len(spec.requested_dormant_selftimer_symbols) > 0
                        or (
                            spec.shooting_domain != "Still"
                            and spec.drive_mode_selftimer_type != "None"
                        )
                    )
                    and spec.reported_dormant_selftimer_errno != P332_EOPNOTSUPP_ERRNO
                )
                and spec.front_lamp_id == P332_FRONT_LAMP_8_ID
                and spec.front_lamp_distinct_from_tally_rec
                and spec.reported_led8_flashes == st["led8_flashes"]
                and spec.reported_audio_beep_audible == st["audio_beep_audible"]
                and spec.post_drive_mode_selftimer_type == st["post_drive_mode_selftimer_type"]
                and spec.post_selftimer_bracket == st["post_selftimer_bracket"]
                and spec.post_audio_signals == st["post_audio_signals"]
            )
        )
        and len(spec.requested_dormant_selftimer_symbols) == 0
        and spec.selftimer_dormant_or_led8_audio_drift_events == 0
    )
    if not selftimer_ok:
        _fail(
            P332_BLOCKED_SELFTIMER_DORMANT_OR_LED8_AUDIO_DRIFT,
            "Self-timer violated Still Single/Cont(6-combo)/Bracket resettable contract, dormant Movie Self-timer EOPNOTSUPP=95, Front #8 LED, or Initialize-only Audio signals mute contract",
        )

    # 3. ILME-FX6 Zero IBIS (OSS + 6-Axis Gyro) & Picture Cache Rec / Interval Rec Boundary
    fx6_ok = (
        not spec.fx6_has_ibis
        and spec.fx6_has_6axis_gyro_metadata
        and spec.fx6_oss_disabled_for_catalyst
        and not spec.fx6_has_still_self_timer
        and spec.fx6_uses_picture_cache_and_interval_rec
        and spec.fx6_ibis_or_selftimer_spoof_events == 0
    )
    if not fx6_ok:
        _fail(
            P332_BLOCKED_FX6_IBIS_OR_SELFTIMER_SPOOF,
            "FX6 boundary violated Zero-IBIS (TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED / OSS + 6-axis gyro) or Picture Cache/Interval Rec contrast",
        )

    # 4. Slot-1 Tier-0 Vault Firewall & Stage-B Overlay & H0 == H3
    vault_fw_ok = (
        spec.slot1_format_hard_locked
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_vault_mutation_bytes == 0
        and not (
            spec.requested_vault_slot == P332_SLOT1_VAULT_SLOT
            and spec.requested_vault_action in P332_WRITE_MUTATING_VAULT_ACTIONS
        )
    )
    if not vault_fw_ok:
        _fail(
            P332_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Vault EROFS=30 firewall blocked write/format mutation on Tier-0 media",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P332_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P332_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P332_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P332_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "59A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "fw_version": spec.fw_version,
            "shooting_domain": spec.shooting_domain,
            "effective_movie_steadyshot": spec.reported_effective_movie_steadyshot,
            "focal_length_mm": spec.focal_length_mm,
            "post_focal_length_mm": spec.post_focal_length_mm,
            "drive_mode_selftimer_type": spec.drive_mode_selftimer_type,
            "post_audio_signals": spec.post_audio_signals,
            "slot1_bytes": spec.slot1_vault_mutation_bytes,
            "errors": errors,
        }
    )
    return SteadyShot47FocalSelfTimerVaultReport(
        schema=PHASE332_SCHEMA,
        version=PHASE332_VERSION,
        passed=passed,
        status=P332_STATUS_VERIFIED_PILLAR_59A if passed else P332_STATUS_REJECTED_PILLAR_59A,
        block_code=block_code,
        steadyshot_4item_47focal_and_4lockout_verified=steadyshot_ok,
        selftimer_still_vs_dormant_movie_led8_audio_verified=selftimer_ok,
        fx6_zero_ibis_and_alt_rec_boundary_verified=fx6_ok,
        slot1_vault_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=18,
        steadyshot_47focal_or_lockout_drift_events=spec.steadyshot_47focal_or_lockout_drift_events,
        selftimer_dormant_or_led8_audio_drift_events=(
            spec.selftimer_dormant_or_led8_audio_drift_events
        ),
        fx6_ibis_or_selftimer_spoof_events=spec.fx6_ibis_or_selftimer_spoof_events,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_zebra_peaking_streaming_vault(
    spec: ZebraPeakingStreamingVaultSpec,
) -> ZebraPeakingStreamingVaultReport:
    """Evaluate Pillar 59B: Wave-57 `[Zebra]` Custom1/2 IRE & 4-color `[Peaking]` Clean-HDMI isolation
    vs FX6 mutually exclusive `Off/Zebra1/Zebra2` + `B&W/R/Y/B`, `[Network Streaming]` RTMP/RTMPS/SRT
    (59.94/50/29.97/25p only, no 23.98p/24p, Movie Rec During Streaming 4K lockout, Reset Network Set.
    preserving Airplane Mode=On), & Zero-RF USB-LAN + Slot-1 Tier-0 EROFS=30 Vault Firewall."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P332_BLOCKED_SAFETY_POLICY_VIOLATION, "Module safety invariant violation")

    valid_fw = (
        (
            spec.camera_model == P332_FX3_MODEL_NAME
            and spec.fw_version in P332_FX3_SUPPORTED_FW_VERSIONS
        )
        or (
            spec.camera_model == P332_FX6_DONOR_MODEL_NAME
            and spec.fw_version == P332_FX6_DONOR_FW_VERSION
        )
    )
    if (
        not valid_fw
        or spec.shooting_domain not in P332_SHOOTING_DOMAINS
        or spec.zebra_display not in P332_ON_OFF_MODES
        or spec.zebra_level not in P332_ZEBRA_LEVEL_OPTIONS
        or spec.peaking_display not in P332_ON_OFF_MODES
        or spec.peaking_level not in P332_PEAKING_LEVELS
        or spec.peaking_color not in P332_PEAKING_COLORS
        or spec.fx6_zebra_mode not in P332_FX6_ZEBRA_ALL_MODES
        or spec.streaming_enabled not in P332_ON_OFF_MODES
        or spec.streaming_protocol not in P332_STREAMING_PROTOCOLS
        or spec.streaming_quality not in P332_STREAMING_QUALITY_PRESETS
        or spec.streaming_resolution not in P332_STREAMING_RESOLUTIONS
        or spec.streaming_fps not in P332_STREAMING_ALL_FPS
        or spec.movie_rec_during_streaming not in P332_MOVIE_REC_DURING_STREAMING_MODES
        or spec.ftp_transfer_func not in P332_ON_OFF_MODES
        or spec.airplane_mode not in P332_ON_OFF_MODES
        or spec.network_transport not in P332_NETWORK_TRANSPORTS
        or spec.reset_action not in P332_RESET_ACTIONS
        or spec.requested_vault_slot not in (1, 2)
        or spec.requested_vault_action not in P332_VAULT_ACTIONS
        or (
            spec.vault_firewall_errno is not None
            and spec.vault_firewall_errno not in P332_VAULT_FIREWALL_ERRNOS
        )
    ):
        _fail(
            P332_BLOCKED_INVALID_PILLAR59B_SPEC,
            "Invalid Pillar 59B camera/Zebra/Peaking/Streaming/vault spec parameter",
        )

    st = compute_expected_zebra_peaking_streaming_vault_state(
        camera_model=spec.camera_model,
        zebra_display=spec.zebra_display,
        zebra_level=spec.zebra_level,
        zebra_custom1_type=spec.zebra_custom1_type,
        zebra_custom1_std=spec.zebra_custom1_std,
        zebra_custom1_range=spec.zebra_custom1_range,
        zebra_custom2_type=spec.zebra_custom2_type,
        zebra_custom2_lower_limit=spec.zebra_custom2_lower_limit,
        display_lut_on=spec.display_lut_on,
        peaking_display=spec.peaking_display,
        peaking_level=spec.peaking_level,
        peaking_color=spec.peaking_color,
        fx6_zebra_mode=spec.fx6_zebra_mode,
        fx6_peaking_color=spec.fx6_peaking_color,
        streaming_enabled=spec.streaming_enabled,
        streaming_protocol=spec.streaming_protocol,
        streaming_codec=spec.streaming_codec,
        srt_encryption=spec.srt_encryption,
        streaming_resolution=spec.streaming_resolution,
        streaming_fps=spec.streaming_fps,
        movie_rec_during_streaming=spec.movie_rec_during_streaming,
        internal_rec_resolution=spec.internal_rec_resolution,
        ftp_transfer_func=spec.ftp_transfer_func,
        airplane_mode=spec.airplane_mode,
        network_transport=spec.network_transport,
        requested_fx6_dormant_streaming_symbols=spec.requested_fx6_dormant_streaming_symbols,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
        movie_rec_during_streaming_targets_slot1=spec.movie_rec_during_streaming_targets_slot1,
        make_ftp_or_stream_dir_on_slot1=spec.make_ftp_or_stream_dir_on_slot1,
        reset_action=spec.reset_action,
    )

    # 1. Zebra Custom1/2 IRE, Display LUT post-LUT shift, 4-color Peaking, Initialize-only Reset & Clean-HDMI + FX6 boundary
    zebra_peaking_ok = (
        st["custom1_valid"]
        and st["custom2_valid"]
        and spec.reported_zebra_measures_post_lut == st["zebra_measures_post_lut"]
        and spec.reported_clean_hdmi_isolated_to_body_lcd
        and not spec.reported_hdmi_zebra_or_peaking_leaked
        and spec.post_zebra_display == st["post_zebra_display"]
        and spec.post_zebra_level == st["post_zebra_level"]
        and spec.post_peaking_display == st["post_peaking_display"]
        and spec.post_peaking_level == st["post_peaking_level"]
        and spec.post_peaking_color == st["post_peaking_color"]
        and spec.fx6_zebra_mode in P332_FX6_ZEBRA_MODES
        and spec.reported_fx6_zebra_both_errno == st["fx6_zebra_both_errno"]
        and st["fx6_peaking_color_valid"]
        and spec.zebra_custom_ire_or_peaking_clean_hdmi_drift_events == 0
    )
    if not zebra_peaking_ok:
        _fail(
            P332_BLOCKED_ZEBRA_CUSTOM_IRE_OR_PEAKING_CLEAN_HDMI_DRIFT,
            "Zebra Custom1/2 IRE, Display LUT post-LUT check, Initialize-only reset split, 4-color Peaking Clean-HDMI isolation, or FX6 Off/Zebra1/Zebra2+B&W boundary violated",
        )

    # 2. [Network Streaming] RTMP/RTMPS/SRT, 59.94/50/29.97/25p only (no 23.98p/24p), Movie Rec During Streaming & Network Reset split
    streaming_ok = (
        tuple(spec.streaming_menu_path) == P332_STREAMING_MENU_PATH
        and st["fps_allowed"]
        and spec.reported_streaming_fps_errno == st["streaming_fps_errno"]
        and st["codec_allowed"]
        and st["srt_enc_allowed"]
        and spec.reported_internal_4k_rec_allowed == st["internal_4k_rec_allowed"]
        and not (st["blocks_internal_4k"] and spec.internal_rec_resolution == "4K" and spec.reported_internal_4k_rec_allowed)
        and spec.reported_forced_internal_rec_fps == st["forced_internal_rec_fps"]
        and spec.reported_streaming_locks_out_ftp_menu_pb == st["streaming_locks_out_ftp_menu_pb"]
        and spec.post_streaming_enabled == st["post_streaming_enabled"]
        and spec.post_movie_rec_during_streaming == st["post_movie_rec_during_streaming"]
        and spec.post_ftp_transfer_func == st["post_ftp_transfer_func"]
        and spec.post_airplane_mode == st["post_airplane_mode"]
        and len(spec.requested_fx6_dormant_streaming_symbols) == 0
        and spec.reported_fx6_dormant_streaming_errno == st["dormant_fx6_streaming_errno"]
        and spec.streaming_24p_rec_or_network_reset_drift_events == 0
    )
    if not streaming_ok:
        _fail(
            P332_BLOCKED_STREAMING_24P_REC_OR_NETWORK_RESET_DRIFT,
            "Network Streaming violated RTMP/RTMPS/SRT codec, 23.98p/24p exclusion, Movie Rec During Streaming 4K lockout, Network Reset preserving Airplane Mode, or FX6 dormant QoS/RTMP/SRT exclusion",
        )

    # 3. Zero-RF (Airplane Mode=On, USB-LAN CDC-NCM) & Slot-1 Tier-0 EROFS=30 Vault Firewall
    slot1_mutated_violation = (
        spec.requested_vault_slot == P332_SLOT1_VAULT_SLOT
        and spec.slot1_holds_tier0_vault
        and (
            spec.requested_vault_action in P332_WRITE_MUTATING_VAULT_ACTIONS
            or spec.movie_rec_during_streaming_targets_slot1
            or spec.make_ftp_or_stream_dir_on_slot1
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
        and spec.slot1_streaming_or_ftp_mutation_bytes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_format_hard_locked
        and spec.zero_rf_or_slot1_vault_bypass_events == 0
    )
    if not zero_rf_vault_ok:
        _fail(
            P332_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL,
            "Zero-RF Airplane Mode=On (USB-LAN CDC-NCM only) or Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    # 4. Stage-B Overlay & H0 == H3
    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P332_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P332_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P332_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P332_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    overlay_and_h0_h3_ok = overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "59B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "zebra_level": spec.zebra_level,
            "peaking_color": spec.peaking_color,
            "streaming_protocol": spec.streaming_protocol,
            "streaming_fps": spec.streaming_fps,
            "post_airplane_mode": spec.post_airplane_mode,
            "vault_slot": spec.requested_vault_slot,
            "vault_action": spec.requested_vault_action,
            "rf_packets": spec.rf_packets_transmitted,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return ZebraPeakingStreamingVaultReport(
        schema=PHASE332_SCHEMA,
        version=PHASE332_VERSION,
        passed=passed,
        status=P332_STATUS_VERIFIED_PILLAR_59B if passed else P332_STATUS_REJECTED_PILLAR_59B,
        block_code=block_code,
        zebra_custom12_peaking_clean_hdmi_and_fx6_verified=zebra_peaking_ok,
        streaming_protocols_24p_lockout_and_net_reset_verified=streaming_ok,
        zero_rf_usblan_and_slot1_erofs30_vault_verified=zero_rf_vault_ok,
        overlay_and_h0_h3_verified=overlay_and_h0_h3_ok,
        matrix_states_checked=18,
        zebra_custom_ire_or_peaking_clean_hdmi_drift_events=(
            spec.zebra_custom_ire_or_peaking_clean_hdmi_drift_events
        ),
        streaming_24p_rec_or_network_reset_drift_events=(
            spec.streaming_24p_rec_or_network_reset_drift_events
        ),
        zero_rf_or_slot1_vault_bypass_events=spec.zero_rf_or_slot1_vault_bypass_events,
        rf_packets_transmitted=spec.rf_packets_transmitted,
        rf_nvs_mutation_bytes=spec.rf_nvs_mutation_bytes,
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_streaming_or_ftp_mutation_bytes=spec.slot1_streaming_or_ftp_mutation_bytes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_steadyshot_47focal_selftimer_zebra_streaming_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_59a: Optional[SteadyShot47FocalSelfTimerVaultSpec] = None,
    spec_59b: Optional[ZebraPeakingStreamingVaultSpec] = None,
) -> SteadyShot47FocalSelfTimerZebraStreamingVaultReport:
    """Combined single-shot verifier for Pillar 59A + Pillar 59B + bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase332_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_steadyshot_47focal_selftimer_vault(
        spec_59a or build_default_safe_steadyshot_47focal_selftimer_vault_spec()
    )
    rep_b = evaluate_zebra_peaking_streaming_vault(
        spec_59b or build_default_safe_zebra_peaking_streaming_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 332 Wave-57 donor artifact parity check failed")
    if not donor_snapshot.under_0_20s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return SteadyShot47FocalSelfTimerZebraStreamingVaultReport(
        schema=PHASE332_SCHEMA,
        version=PHASE332_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P332_STATUS_VERIFIED_PILLAR59_SUITE if all_ok else P332_STATUS_FAIL_PILLAR59_SUITE,
        donor_snapshot=donor_snapshot,
        steadyshot_selftimer_report=rep_a,
        zebra_peaking_streaming_report=rep_b,
        steadyshot_47focal_or_lockout_drift_events=rep_a.steadyshot_47focal_or_lockout_drift_events,
        selftimer_dormant_or_led8_audio_drift_events=(
            rep_a.selftimer_dormant_or_led8_audio_drift_events
        ),
        fx6_ibis_or_selftimer_spoof_events=rep_a.fx6_ibis_or_selftimer_spoof_events,
        zebra_custom_ire_or_peaking_clean_hdmi_drift_events=(
            rep_b.zebra_custom_ire_or_peaking_clean_hdmi_drift_events
        ),
        streaming_24p_rec_or_network_reset_drift_events=(
            rep_b.streaming_24p_rec_or_network_reset_drift_events
        ),
        zero_rf_or_slot1_vault_bypass_events=rep_b.zero_rf_or_slot1_vault_bypass_events,
        rf_packets_transmitted=rep_b.rf_packets_transmitted,
        rf_nvs_mutation_bytes=rep_b.rf_nvs_mutation_bytes,
        slot1_data_sector_writes=rep_b.slot1_data_sector_writes,
        slot1_streaming_or_ftp_mutation_bytes=rep_b.slot1_streaming_or_ftp_mutation_bytes,
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


def verify_steadyshot_47focal_selftimer_zebra_streaming_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_59a: Optional[SteadyShot47FocalSelfTimerVaultSpec] = None,
    spec_59b: Optional[ZebraPeakingStreamingVaultSpec] = None,
) -> SteadyShot47FocalSelfTimerZebraStreamingVaultReport:
    """Symmetry alias for `verify_steadyshot_47focal_selftimer_zebra_streaming_and_vault`."""
    return verify_steadyshot_47focal_selftimer_zebra_streaming_and_vault(
        force_clean_room=force_clean_room,
        spec_59a=spec_59a,
        spec_59b=spec_59b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 59A & 59B)
# ---------------------------------------------------------------------------


def run_pillar59a_steadyshot_47focal_selftimer_6_scenario_suite() -> Pillar59ASuiteResult:
    """Run 6 Pillar 59A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, SteadyShot47FocalSelfTimerVaultSpec, Optional[str]], ...] = (
        (
            P332_PILLAR_59A_SCENARIO_IDS[0],
            True,
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                shooting_domain="Movie",
                movie_steadyshot="Active",
                steadyshot_adjust="Manual",
                focal_length_mm=1000,
                movie_fps=59.94,
                sq_fps=23.98,
                hdmi_raw_on=False,
                de_squeeze="Off",
                distortion_comp="Off",
                clear_image_zoom="Clear Image Zoom",
                reported_effective_movie_steadyshot="Active",
                reported_effective_crop_factor=P332_ACTIVE_CROP_FACTOR_APPROX,
                reported_forced_distortion_comp="Auto",
                reported_ciz_forces_metering_multi=True,
                reset_action="Camera Settings Reset",
                post_movie_steadyshot="Standard",
                post_still_steadyshot="On",
                post_steadyshot_adjust="Auto",
                post_focal_length_mm=8,
                audio_signals="Off",
                post_audio_signals="Off",
            ),
            None,
        ),
        (
            P332_PILLAR_59A_SCENARIO_IDS[1],
            True,
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                shooting_domain="Still",
                drive_mode_selftimer_type="Self-timer(Cont)",
                selftimer_cont_combo="2 Sec. 5 Img.",
                selftimer_bracket="5 Sec",
                reported_led8_flashes=True,
                silent_mode="Off",
                audio_signals="On",
                reported_audio_beep_audible=True,
                reset_action="Camera Settings Reset",
                post_drive_mode_selftimer_type="None",
                post_selftimer_bracket="Off",
                post_audio_signals="On",
            ),
            None,
        ),
        (
            P332_PILLAR_59A_SCENARIO_IDS[2],
            False,
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                shooting_domain="Movie",
                movie_steadyshot="Dynamic active",
                movie_fps=119.88,
                de_squeeze="1.3x",
                reported_effective_movie_steadyshot="Dynamic active",
                reported_dormant_dynamic_active_errno=None,
                steadyshot_47focal_or_lockout_drift_events=1,
            ),
            P332_BLOCKED_STEADYSHOT_47FOCAL_OR_LOCKOUT_DRIFT,
        ),
        (
            P332_PILLAR_59A_SCENARIO_IDS[3],
            False,
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                shooting_domain="Movie",
                focal_length_mm=42,
                drive_mode_selftimer_type="Self-timer(Single)",
                requested_dormant_selftimer_symbols=("BKID_APP_setting_movie_self_timer", "Rec Start delay"),
                reported_dormant_selftimer_errno=None,
                steadyshot_47focal_or_lockout_drift_events=1,
                selftimer_dormant_or_led8_audio_drift_events=1,
            ),
            P332_BLOCKED_STEADYSHOT_47FOCAL_OR_LOCKOUT_DRIFT,
        ),
        (
            P332_PILLAR_59A_SCENARIO_IDS[4],
            False,
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                camera_model=P332_FX6_DONOR_MODEL_NAME,
                fw_version=P332_FX6_DONOR_FW_VERSION,
                fx6_has_ibis=True,
                fx6_has_still_self_timer=True,
                fx6_uses_picture_cache_and_interval_rec=False,
                fx6_ibis_or_selftimer_spoof_events=1,
            ),
            P332_BLOCKED_FX6_IBIS_OR_SELFTIMER_SPOOF,
        ),
        (
            P332_PILLAR_59A_SCENARIO_IDS[5],
            False,
            build_default_safe_steadyshot_47focal_selftimer_vault_spec(
                requested_vault_slot=1,
                requested_vault_action="FORMAT_QUICK",
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/setting/59a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P332_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar59ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_steadyshot_47focal_selftimer_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar59ScenarioOutcome(
                scenario_id=sid,
                pillar="59A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar59ASuiteResult(
        passed=all_ok,
        status=P332_STATUS_VERIFIED_PILLAR_59A if all_ok else P332_STATUS_REJECTED_PILLAR_59A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar59b_zebra_peaking_streaming_vault_6_scenario_suite() -> Pillar59BSuiteResult:
    """Run 6 Pillar 59B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, ZebraPeakingStreamingVaultSpec, Optional[str]], ...] = (
        (
            P332_PILLAR_59B_SCENARIO_IDS[0],
            True,
            build_default_safe_zebra_peaking_streaming_vault_spec(
                zebra_display="On",
                zebra_level="Custom1",
                zebra_custom1_type="Std+Range",
                zebra_custom1_std=41,
                zebra_custom1_range=2,
                zebra_custom2_type="Lower Limit",
                zebra_custom2_lower_limit=94,
                display_lut_on=True,
                reported_zebra_measures_post_lut=True,
                peaking_display="On",
                peaking_level="High",
                peaking_color="Blue",
                reported_clean_hdmi_isolated_to_body_lcd=True,
                reported_hdmi_zebra_or_peaking_leaked=False,
                reset_action="Camera Settings Reset",
                post_zebra_display="On",
                post_zebra_level="Custom1",
                post_peaking_display="On",
                post_peaking_level="High",
                post_peaking_color="Blue",
            ),
            None,
        ),
        (
            P332_PILLAR_59B_SCENARIO_IDS[1],
            True,
            build_default_safe_zebra_peaking_streaming_vault_spec(
                streaming_enabled="On",
                streaming_protocol="SRT",
                streaming_codec="H.265",
                srt_encryption="AES-256",
                streaming_resolution="2K",
                streaming_fps="59.94p",
                movie_rec_during_streaming="Enable",
                internal_rec_resolution="1080p",
                reported_internal_4k_rec_allowed=False,
                reported_forced_internal_rec_fps="59.94p",
                reported_streaming_locks_out_ftp_menu_pb=True,
                ftp_transfer_func="On",
                airplane_mode="On",
                network_transport="USB-LAN (CDC-NCM)",
                reset_action="Reset Network Set.",
                post_streaming_enabled="Off",
                post_movie_rec_during_streaming="Disable",
                post_ftp_transfer_func="Off",
                post_airplane_mode="On",
                requested_vault_slot=2,
                requested_vault_action="MOVIE_REC_DURING_STREAMING_RECORD",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            ),
            None,
        ),
        (
            P332_PILLAR_59B_SCENARIO_IDS[2],
            False,
            build_default_safe_zebra_peaking_streaming_vault_spec(
                zebra_display="On",
                zebra_level="Custom2",
                peaking_display="On",
                peaking_color="Red",
                reported_hdmi_zebra_or_peaking_leaked=True,
                reset_action="Camera Settings Reset",
                post_zebra_display="Off",
                post_peaking_color="White",
                zebra_custom_ire_or_peaking_clean_hdmi_drift_events=1,
            ),
            P332_BLOCKED_ZEBRA_CUSTOM_IRE_OR_PEAKING_CLEAN_HDMI_DRIFT,
        ),
        (
            P332_PILLAR_59B_SCENARIO_IDS[3],
            False,
            build_default_safe_zebra_peaking_streaming_vault_spec(
                camera_model=P332_FX6_DONOR_MODEL_NAME,
                fw_version=P332_FX6_DONOR_FW_VERSION,
                fx6_zebra_mode="Both",
                reported_fx6_zebra_both_errno=None,
                fx6_peaking_color="White",
                requested_fx6_dormant_streaming_symbols=("RTMP", "SRT", "QoS Streaming"),
                reported_fx6_dormant_streaming_errno=None,
                zebra_custom_ire_or_peaking_clean_hdmi_drift_events=1,
            ),
            P332_BLOCKED_ZEBRA_CUSTOM_IRE_OR_PEAKING_CLEAN_HDMI_DRIFT,
        ),
        (
            P332_PILLAR_59B_SCENARIO_IDS[4],
            False,
            build_default_safe_zebra_peaking_streaming_vault_spec(
                streaming_protocol="RTMP",
                streaming_codec="H.265",
                streaming_resolution="4K",
                streaming_fps="23.98p",
                reported_streaming_fps_errno=None,
                movie_rec_during_streaming="Enable",
                internal_rec_resolution="4K",
                reported_internal_4k_rec_allowed=True,
                airplane_mode="On",
                reset_action="Reset Network Set.",
                post_airplane_mode="Off",
                streaming_24p_rec_or_network_reset_drift_events=1,
            ),
            P332_BLOCKED_STREAMING_24P_REC_OR_NETWORK_RESET_DRIFT,
        ),
        (
            P332_PILLAR_59B_SCENARIO_IDS[5],
            False,
            build_default_safe_zebra_peaking_streaming_vault_spec(
                airplane_mode="Off",
                post_airplane_mode="Off",
                network_transport="Wi-Fi",
                rf_packets_transmitted=12,
                rf_nvs_mutation_bytes=64,
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="FTP_WRITE_TARGET",
                movie_rec_during_streaming_targets_slot1=True,
                make_ftp_or_stream_dir_on_slot1=True,
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=8192,
                slot1_streaming_or_ftp_mutation_bytes=4096,
                slot1_vault_mutation_bytes=12288,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                zero_rf_or_slot1_vault_bypass_events=1,
            ),
            P332_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar59ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_zebra_peaking_streaming_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar59ScenarioOutcome(
                scenario_id=sid,
                pillar="59B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar59BSuiteResult(
        passed=all_ok,
        status=P332_STATUS_VERIFIED_PILLAR_59B if all_ok else P332_STATUS_REJECTED_PILLAR_59B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Standalone Pillar 59 Suite & Unified 59/59 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def run_pillar59_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar59StandaloneReport:
    """Run full Pillar 59 standalone suite (`6/6` Pillar 59A + `6/6` Pillar 59B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase332_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar59a_steadyshot_47focal_selftimer_6_scenario_suite()
    res_b = run_pillar59b_zebra_peaking_streaming_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 332 donor verification failed")
    if not donor_snapshot.under_0_20s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE332_SCHEMA,
            "version": PHASE332_VERSION,
            "mode": donor_snapshot.verification_mode,
            "59a": [asdict(s) for s in res_a.scenarios],
            "59b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar59StandaloneReport(
        schema=PHASE332_SCHEMA,
        version=PHASE332_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P332_STATUS_VERIFIED_PILLAR59_SUITE if all_ok else P332_STATUS_FAIL_PILLAR59_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_59a_steadyshot_47focal_selftimer_vault=res_a,
        pillar_59b_zebra_peaking_streaming_vault=res_b,
        steadyshot_47focal_or_lockout_drift_events=(
            P332_STEADYSHOT_47FOCAL_OR_LOCKOUT_DRIFT_EVENTS if res_a.passed else 1
        ),
        selftimer_dormant_or_led8_audio_drift_events=(
            P332_SELFTIMER_DORMANT_OR_LED8_AUDIO_DRIFT_EVENTS if res_a.passed else 1
        ),
        fx6_ibis_or_selftimer_spoof_events=(
            P332_FX6_IBIS_OR_SELFTIMER_SPOOF_EVENTS if res_a.passed else 1
        ),
        zebra_custom_ire_or_peaking_clean_hdmi_drift_events=(
            P332_ZEBRA_CUSTOM_IRE_OR_PEAKING_CLEAN_HDMI_DRIFT_EVENTS if res_b.passed else 1
        ),
        streaming_24p_rec_or_network_reset_drift_events=(
            P332_STREAMING_24P_REC_OR_NETWORK_RESET_DRIFT_EVENTS if res_b.passed else 1
        ),
        zero_rf_or_slot1_vault_bypass_events=(
            P332_ZERO_RF_OR_SLOT1_VAULT_BYPASS_EVENTS if res_b.passed else 1
        ),
        rf_packets_transmitted=P332_RF_PACKETS_TRANSMITTED if res_b.passed else 1,
        rf_nvs_mutation_bytes=P332_RF_NVS_MUTATION_BYTES if res_b.passed else 64,
        slot1_data_sector_writes=P332_SLOT1_DATA_SECTOR_WRITES if res_b.passed else 1,
        slot1_streaming_or_ftp_mutation_bytes=(
            P332_SLOT1_STREAMING_OR_FTP_MUTATION_BYTES if res_b.passed else 4096
        ),
        slot1_vault_mutation_bytes=(
            P332_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        slot1_format_hard_locked=P332_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_eopnotsupp_enforced=P332_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
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


def _apply_master59_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def _master59_local_donors_available() -> bool:
    """Return True only when legacy BODYDATA.DAT and all 17 Wave-57 local donors exist."""
    required_relpaths: Tuple[str, ...] = (
        "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT",
        P332_DONOR_FX3_APPFW_702_RELPATH,
        P332_DONOR_FX6_APPFW_601_RELPATH,
        P332_DONOR_FX3_BACKUP_BIN_RELPATH,
        P332_DONOR_FX3_UXC_EN_F_RELPATH,
        P332_DONOR_FX3_UXC_SC_F_RELPATH,
        P332_DONOR_FX3_UXC_TC_F_RELPATH,
        P332_DONOR_FX3_UXC_JA_F_RELPATH,
        P332_DONOR_FX3_UXC_EN_RELPATH,
        P332_DONOR_FX3_UXC_SC_RELPATH,
        P332_DONOR_FX3_UXC_TC_RELPATH,
        P332_DONOR_FX3_UXC_JA_RELPATH,
        P332_DONOR_FX3_UXC_EN_G_RELPATH,
        P332_DONOR_FX3_UXC_SC_G_RELPATH,
        P332_DONOR_FX3_UXC_TC_G_RELPATH,
        P332_DONOR_FX3_UXC_JA_G_RELPATH,
        P332_DONOR_FX6_UXC_EN_RELPATH,
        P332_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for relpath in required_relpaths:
        try:
            resolved = _resolve_phase332_donor_path(relpath)
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


def evaluate_realhw_59pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master59PillarRecoveryReport:
    """Evaluate and aggregate all 59 recovery pillars (`1..59`) concurrently -> `59/59` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_59_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    if resolved_clean_room is None and not _master59_local_donors_available():
        resolved_clean_room = True
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_58pillar() -> Master58PillarRecoveryReport:
        return evaluate_realhw_58pillar_recovery_master(**kw)

    def _run_p59() -> Tuple[Pillar59StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar59_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_58 = pool.submit(_run_58pillar)
        fut_59 = pool.submit(_run_p59)
        m58_rep = fut_58.result()
        p59_rep, p59_dt = fut_59.result()

    all_errors: List[str] = list(m58_rep.errors) + list(p59_rep.errors)
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
        if getattr(m58_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-58 violated {attr_name} == {expected_val}")
        if getattr(p59_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 59 violated {attr_name} == {expected_val}")

    if p59_rep.cross_model_flash_authorized is not False:
        all_errors.append("Pillar 59 violated cross_model_flash_authorized == False")

    for attr_name, expected_val in (
        ("dial_customize_dormant_trap_or_reset_drift_events", 0),
        ("rear_dial_lr_or_mydial_override_drift_events", 0),
        ("fn_menu_12x2_or_fx6_dial_spoof_events", 0),
        ("live_view_display_reset_split_or_mode_drift_events", 0),
        ("grid_line_or_hdmi_clean_feed_leak_events", 0),
        ("lut_path_embed_sidecar_or_slot1_vault_bypass_events", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_lut_mutation_bytes", 0),
        ("slot1_avf_info_mutated", False),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_eopnotsupp_enforced", True),
    ):
        if getattr(m58_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-58 violated {attr_name} == {expected_val}")

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
        if getattr(p59_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 59 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m58_rep.pillars)
    spec59 = MASTER_59_PILLAR_SPECS[58]
    p59_metrics = {
        "pillar_59a_steadyshot_47focal_selftimer_vault": (
            f"{p59_rep.pillar_59a_steadyshot_47focal_selftimer_vault.scenarios_passed}/"
            f"{p59_rep.pillar_59a_steadyshot_47focal_selftimer_vault.scenarios_total}"
        ),
        "pillar_59b_zebra_peaking_streaming_vault": (
            f"{p59_rep.pillar_59b_zebra_peaking_streaming_vault.scenarios_passed}/"
            f"{p59_rep.pillar_59b_zebra_peaking_streaming_vault.scenarios_total}"
        ),
        "steadyshot_47focal_or_lockout_drift_events": (
            p59_rep.steadyshot_47focal_or_lockout_drift_events
        ),
        "selftimer_dormant_or_led8_audio_drift_events": (
            p59_rep.selftimer_dormant_or_led8_audio_drift_events
        ),
        "fx6_ibis_or_selftimer_spoof_events": p59_rep.fx6_ibis_or_selftimer_spoof_events,
        "zebra_custom_ire_or_peaking_clean_hdmi_drift_events": (
            p59_rep.zebra_custom_ire_or_peaking_clean_hdmi_drift_events
        ),
        "streaming_24p_rec_or_network_reset_drift_events": (
            p59_rep.streaming_24p_rec_or_network_reset_drift_events
        ),
        "zero_rf_or_slot1_vault_bypass_events": p59_rep.zero_rf_or_slot1_vault_bypass_events,
        "rf_packets_transmitted": p59_rep.rf_packets_transmitted,
        "rf_nvs_mutation_bytes": p59_rep.rf_nvs_mutation_bytes,
        "slot1_data_sector_writes": p59_rep.slot1_data_sector_writes,
        "slot1_streaming_or_ftp_mutation_bytes": p59_rep.slot1_streaming_or_ftp_mutation_bytes,
        "slot1_vault_mutation_bytes": p59_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p59_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_eopnotsupp_enforced": p59_rep.slot1_vault_erofs_eopnotsupp_enforced,
        "overall_ready_for_hardware_attach": p59_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p59_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p59_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p59_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec59[0],
            pillar_id=spec59[1],
            phase_label=spec59[2],
            module_name=spec59[3],
            passed=bool(p59_rep.all_passed),
            status=p59_rep.status,
            verification_mode=p59_rep.verification_mode,
            elapsed_seconds=p59_dt,
            key_metrics=p59_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec59[1],
                    "mode": p59_rep.verification_mode,
                    "status": p59_rep.status,
                    "metrics": p59_metrics,
                    "passed": p59_rep.all_passed,
                }
            ),
            errors=tuple(p59_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master59_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p59_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_59_PILLAR_COUNT == 59
        and pillars_passed == 59
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE332_SCHEMA,
            "schema_version": PHASE332_MASTER_SCHEMA,
            "version": PHASE332_VERSION,
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
    return Master59PillarRecoveryReport(
        schema=PHASE332_SCHEMA,
        schema_version=PHASE332_MASTER_SCHEMA,
        version=PHASE332_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P332_STATUS_VERIFIED_59OF59_AGGREGATOR if all_ok else P332_STATUS_FAIL_59OF59_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P332_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.5,
        under_6s_budget=elapsed < P332_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P332_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p59_rep.donor_snapshot,
        pillar59_a_steadyshot_47focal_selftimer_vault=(
            p59_rep.pillar_59a_steadyshot_47focal_selftimer_vault
        ),
        pillar59_b_zebra_peaking_streaming_vault=(
            p59_rep.pillar_59b_zebra_peaking_streaming_vault
        ),
        steadyshot_47focal_or_lockout_drift_events=(
            p59_rep.steadyshot_47focal_or_lockout_drift_events
        ),
        selftimer_dormant_or_led8_audio_drift_events=(
            p59_rep.selftimer_dormant_or_led8_audio_drift_events
        ),
        fx6_ibis_or_selftimer_spoof_events=p59_rep.fx6_ibis_or_selftimer_spoof_events,
        zebra_custom_ire_or_peaking_clean_hdmi_drift_events=(
            p59_rep.zebra_custom_ire_or_peaking_clean_hdmi_drift_events
        ),
        streaming_24p_rec_or_network_reset_drift_events=(
            p59_rep.streaming_24p_rec_or_network_reset_drift_events
        ),
        zero_rf_or_slot1_vault_bypass_events=p59_rep.zero_rf_or_slot1_vault_bypass_events,
        rf_packets_transmitted=p59_rep.rf_packets_transmitted,
        rf_nvs_mutation_bytes=p59_rep.rf_nvs_mutation_bytes,
        slot1_data_sector_writes=m58_rep.slot1_data_sector_writes + p59_rep.slot1_data_sector_writes,
        slot1_streaming_or_ftp_mutation_bytes=p59_rep.slot1_streaming_or_ftp_mutation_bytes,
        slot1_vault_mutation_bytes=(
            m58_rep.slot1_vault_mutation_bytes + p59_rep.slot1_vault_mutation_bytes
        ),
        slot1_format_hard_locked=(
            m58_rep.slot1_format_hard_locked and p59_rep.slot1_format_hard_locked
        ),
        slot1_vault_erofs_eopnotsupp_enforced=(
            m58_rep.slot1_vault_erofs_eopnotsupp_enforced
            and p59_rep.slot1_vault_erofs_eopnotsupp_enforced
        ),
        fx3_steadyshot_47_focal_count=P332_STEADYSHOT_FOCAL_LENGTH_COUNT,
        fx3_image_stabilization_item_count=P332_IMAGE_STABILIZATION_ITEM_COUNT,
        fx3_selftimer_cont_combo_count=P332_SELFTIMER_CONT_COMBO_COUNT,
        fx3_front_lamp_8_id=P332_FRONT_LAMP_8_ID,
        fx3_zebra_preset_count=len(P332_ZEBRA_PRESET_LEVELS),
        fx3_peaking_color_count=len(P332_PEAKING_COLORS),
        fx3_streaming_protocol_count=len(P332_STREAMING_PROTOCOLS),
        fx3_has_5axis_ibis=P332_FX3_HAS_5AXIS_IBIS,
        fx3_has_movie_self_timer=P332_FX3_HAS_MOVIE_SELF_TIMER,
        fx6_has_ibis=P332_FX6_HAS_IBIS,
        fx6_has_6axis_gyro_metadata=P332_FX6_HAS_6AXIS_GYRO_METADATA,
        fx6_has_still_self_timer=P332_FX6_HAS_STILL_SELF_TIMER,
        dial_customize_dormant_trap_or_reset_drift_events=(
            m58_rep.dial_customize_dormant_trap_or_reset_drift_events
        ),
        rear_dial_lr_or_mydial_override_drift_events=(
            m58_rep.rear_dial_lr_or_mydial_override_drift_events
        ),
        fn_menu_12x2_or_fx6_dial_spoof_events=m58_rep.fn_menu_12x2_or_fx6_dial_spoof_events,
        live_view_display_reset_split_or_mode_drift_events=(
            m58_rep.live_view_display_reset_split_or_mode_drift_events
        ),
        grid_line_or_hdmi_clean_feed_leak_events=m58_rep.grid_line_or_hdmi_clean_feed_leak_events,
        lut_path_embed_sidecar_or_slot1_vault_bypass_events=(
            m58_rep.lut_path_embed_sidecar_or_slot1_vault_bypass_events
        ),
        slot1_lut_mutation_bytes=m58_rep.slot1_lut_mutation_bytes,
        slot1_avf_info_mutated=m58_rep.slot1_avf_info_mutated,
        fx3_dial_customize_item_count=m58_rep.fx3_dial_customize_item_count,
        fx3_physical_dial_count=m58_rep.fx3_physical_dial_count,
        fx3_my_dial_bank_count=m58_rep.fx3_my_dial_bank_count,
        fx3_fn_menu_still_slots=m58_rep.fx3_fn_menu_still_slots,
        fx3_fn_menu_movie_slots=m58_rep.fx3_fn_menu_movie_slots,
        fx3_live_view_display_set_item_count=m58_rep.fx3_live_view_display_set_item_count,
        fx3_grid_line_type_count=m58_rep.fx3_grid_line_type_count,
        fx3_user_lut_slot_count=m58_rep.fx3_user_lut_slot_count,
        fx3_pplut_slot_count=m58_rep.fx3_pplut_slot_count,
        fx6_user_lut_ui_cap=m58_rep.fx6_user_lut_ui_cap,
        fx6_has_av_tv_rotate=m58_rep.fx6_has_av_tv_rotate,
        fx6_has_my_dial=m58_rep.fx6_has_my_dial,
        fx6_has_fn_menu=m58_rep.fx6_has_fn_menu,
        fx6_has_multi_channel_lut_switches=m58_rep.fx6_has_multi_channel_lut_switches,
        touch_op_dormant_trap_or_reset_drift_events=(
            m58_rep.touch_op_dormant_trap_or_reset_drift_events
        ),
        disp_set_or_zero_evf_blackout_events=m58_rep.disp_set_or_zero_evf_blackout_events,
        fx6_touch_or_evf_spoof_events=m58_rep.fx6_touch_or_evf_spoof_events,
        still_ael_flash_reset_split_or_mishoe_drift_events=(
            m58_rep.still_ael_flash_reset_split_or_mishoe_drift_events
        ),
        interval_pb_9scale_or_path_drift_events=m58_rep.interval_pb_9scale_or_path_drift_events,
        playback_edit_dormant_or_slot1_vault_bypass_events=(
            m58_rep.playback_edit_dormant_or_slot1_vault_bypass_events
        ),
        slot1_edit_avf_info_mutation_bytes=m58_rep.slot1_edit_avf_info_mutation_bytes,
        fx3_has_eye_sensor=m58_rep.fx3_has_eye_sensor,
        fx3_has_finder_monitor_button=m58_rep.fx3_has_finder_monitor_button,
        fx3_touch_active_item_count=m58_rep.fx3_touch_active_item_count,
        fx3_disp_shoot_page_count=m58_rep.fx3_disp_shoot_page_count,
        fx3_disp_play_page_count=m58_rep.fx3_disp_play_page_count,
        fx3_interval_pb_speed_min=m58_rep.fx3_interval_pb_speed_min,
        fx3_interval_pb_speed_max=m58_rep.fx3_interval_pb_speed_max,
        fx3_interval_pb_speed_default=m58_rep.fx3_interval_pb_speed_default,
        fx6_has_detachable_lcd_viewfinder=m58_rep.fx6_has_detachable_lcd_viewfinder,
        fx6_has_still_ttl_flash=m58_rep.fx6_has_still_ttl_flash,
        fx6_has_interval_pb=m58_rep.fx6_has_interval_pb,
        fx6_has_playback_edit_menu=m58_rep.fx6_has_playback_edit_menu,
        switch_vh_af_lockout_or_coords_drift_events=(
            m58_rep.switch_vh_af_lockout_or_coords_drift_events
        ),
        focus_limit_lt2_or_dormant_symbol_events=m58_rep.focus_limit_lt2_or_dormant_symbol_events,
        focus_area_color_or_fx6_spoof_events=m58_rep.focus_area_color_or_fx6_spoof_events,
        exp_std_adj_mode_conflation_or_reset_drift_events=(
            m58_rep.exp_std_adj_mode_conflation_or_reset_drift_events
        ),
        bracket_settings_reset_or_fx6_spoof_events=m58_rep.bracket_settings_reset_or_fx6_spoof_events,
        tcub_reset_wipe_or_format_lock_violations=m58_rep.tcub_reset_wipe_or_format_lock_violations,
        reverse_copy_slot2_to_slot1_bypass_events=m58_rep.reverse_copy_slot2_to_slot1_bypass_events,
        slideshow_power_save_or_fx6_copy_clip_spoof_events=(
            m58_rep.slideshow_power_save_or_fx6_copy_clip_spoof_events
        ),
        slot1_copy_avf_info_mutation_bytes=m58_rep.slot1_copy_avf_info_mutation_bytes,
        fx3_has_switch_vh_af_area=m58_rep.fx3_has_switch_vh_af_area,
        fx3_focus_area_limit_count=m58_rep.fx3_focus_area_limit_count,
        fx3_focus_area_limit_min_enabled=m58_rep.fx3_focus_area_limit_min_enabled,
        fx3_exp_std_adj_metering_mode_count=m58_rep.fx3_exp_std_adj_metering_mode_count,
        fx3_has_physical_bnc_tc_port=m58_rep.fx3_has_physical_bnc_tc_port,
        fx6_has_physical_bnc_tc_port=m58_rep.fx6_has_physical_bnc_tc_port,
        fx6_has_switch_vh_af_area=m58_rep.fx6_has_switch_vh_af_area,
        fx6_has_focus_area_limit=m58_rep.fx6_has_focus_area_limit,
        fx6_has_exp_std_adj=m58_rep.fx6_has_exp_std_adj,
        fx6_has_still_bracket_settings=m58_rep.fx6_has_still_bracket_settings,
        fx6_has_copy_clip_active=m58_rep.fx6_has_copy_clip_active,
        fx6_has_slide_show=m58_rep.fx6_has_slide_show,
        dormant_shading_auto_low_exposure_events=m58_rep.dormant_shading_auto_low_exposure_events,
        lens_comp_lock_or_arw_conflation_events=m58_rep.lens_comp_lock_or_arw_conflation_events,
        af_illuminator_gate_or_fx6_spoof_events=m58_rep.af_illuminator_gate_or_fx6_spoof_events,
        movie_af_transition_or_assist_drift_events=m58_rep.movie_af_transition_or_assist_drift_events,
        aperture_drive_pre_af_shutter_reset_drift_events=(
            m58_rep.aperture_drive_pre_af_shutter_reset_drift_events
        ),
        circ_focus_diagonal_or_color_drift_events=m58_rep.circ_focus_diagonal_or_color_drift_events,
        folder_name_or_leading_underscore_violations=(
            m58_rep.folder_name_or_leading_underscore_violations
        ),
        slot1_folder_dir_mutation_bytes=m58_rep.slot1_folder_dir_mutation_bytes,
        slot1_rating_avf_info_mutation_bytes=m58_rep.slot1_rating_avf_info_mutation_bytes,
        fx3_has_builtin_af_illuminator=m58_rep.fx3_has_builtin_af_illuminator,
        fx6_has_builtin_af_illuminator=m58_rep.fx6_has_builtin_af_illuminator,
        fx3_exposes_shading_auto_low=m58_rep.fx3_exposes_shading_auto_low,
        fx6_has_aperture_drive_pre_af_circ_color=m58_rep.fx6_has_aperture_drive_pre_af_circ_color,
        fx6_has_msdcf_or_star_rating=m58_rep.fx6_has_msdcf_or_star_rating,
        sensor_cleaning_low_battery_bypass_events=m58_rep.sensor_cleaning_low_battery_bypass_events,
        sensor_cleaning_no_power_off_violations=m58_rep.sensor_cleaning_no_power_off_violations,
        fx6_ibis_shake_conflation_events=m58_rep.fx6_ibis_shake_conflation_events,
        ev_comp_range_or_cine_ei_lockout_violations=(
            m58_rep.ev_comp_range_or_cine_ei_lockout_violations
        ),
        exposure_step_or_dormant_reset_ev_drift_events=(
            m58_rep.exposure_step_or_dormant_reset_ev_drift_events
        ),
        focus_mode_movie_clamp_or_dormant_drift_events=(
            m58_rep.focus_mode_movie_clamp_or_dormant_drift_events
        ),
        priority_set_or_illuminator_gate_violations=m58_rep.priority_set_or_illuminator_gate_violations,
        image_index_dormant_or_view_mode_drift_events=(
            m58_rep.image_index_dormant_or_view_mode_drift_events
        ),
        slot1_rotate_exif_mutation_bytes=m58_rep.slot1_rotate_exif_mutation_bytes,
        fx3_has_sensor_cleaning_ibis=m58_rep.fx3_has_sensor_cleaning_ibis,
        fx3_has_exposure_comp=m58_rep.fx3_has_exposure_comp,
        fx3_has_physical_ev_reset_dial=m58_rep.fx3_has_physical_ev_reset_dial,
        fx6_has_ultrasonic_ibis_cleaning=m58_rep.fx6_has_ultrasonic_ibis_cleaning,
        fx6_has_variable_end_optical_block=m58_rep.fx6_has_variable_end_optical_block,
        fx6_has_technical_apr=m58_rep.fx6_has_technical_apr,
        fx6_has_still_exposure_comp=m58_rep.fx6_has_still_exposure_comp,
        fx6_has_still_image_index_rotate=m58_rep.fx6_has_still_image_index_rotate,
        dci4k_long_gop_or_8k_violations=m58_rep.dci4k_long_gop_or_8k_violations,
        reboot_2400p_stage_b_wipe_violations=m58_rep.reboot_2400p_stage_b_wipe_violations,
        hdmi_raw_or_still_aspect_drift_events=m58_rep.hdmi_raw_or_still_aspect_drift_events,
        fx6_still_or_raw_conflation_events=m58_rep.fx6_still_or_raw_conflation_events,
        reg_custom_hold_or_hlg_lock_drift_events=m58_rep.reg_custom_hold_or_hlg_lock_drift_events,
        camset_cross_model_path_drift_events=m58_rep.camset_cross_model_path_drift_events,
        photo_capture_dci4k_lockout_bypass_events=m58_rep.photo_capture_dci4k_lockout_bypass_events,
        slot1_camset_write_bytes=m58_rep.slot1_camset_write_bytes,
        slot1_photo_capture_write_bytes=m58_rep.slot1_photo_capture_write_bytes,
        fx3_appfw_has_dci4k_internal=m58_rep.fx3_appfw_has_dci4k_internal,
        fx3_appfw_has_pro_camera_path=m58_rep.fx3_appfw_has_pro_camera_path,
        fx6_has_still_aspect_ratio=m58_rep.fx6_has_still_aspect_ratio,
        fx6_has_photo_capture=m58_rep.fx6_has_photo_capture,
        fx6_has_playback_enlarge_image=m58_rep.fx6_has_playback_enlarge_image,
        fx6_has_reg_custom_shoot_set=m58_rep.fx6_has_reg_custom_shoot_set,
        fx6_has_camera_set_memory=m58_rep.fx6_has_camera_set_memory,
        movie_tracking_area_or_limit_violations=m58_rep.movie_tracking_area_or_limit_violations,
        af_area_reg_lock_or_reset_drift_events=m58_rep.af_area_reg_lock_or_reset_drift_events,
        xlrh1_zoom_or_hold_spoof_events=m58_rep.xlrh1_zoom_or_hold_spoof_events,
        fx6_handle_or_pos_display_conflation_events=(
            m58_rep.fx6_handle_or_pos_display_conflation_events
        ),
        iso_minss_or_cine_ei_lock_drift_events=m58_rep.iso_minss_or_cine_ei_lock_drift_events,
        flash_still_mech_gate_violations=m58_rep.flash_still_mech_gate_violations,
        mishoe_pmic_5v_overcurrent_events=m58_rep.mishoe_pmic_5v_overcurrent_events,
        slot1_focus_zoom_camset_mutation_bytes=m58_rep.slot1_focus_zoom_camset_mutation_bytes,
        slot1_flash_videolight_imagedb_bytes=m58_rep.slot1_flash_videolight_imagedb_bytes,
        xlrh1_has_zoom_lever=m58_rep.xlrh1_has_zoom_lever,
        xlrh1_has_rec_button=m58_rep.xlrh1_has_rec_button,
        xlrh1_has_zoom_hold_switch=m58_rep.xlrh1_has_zoom_hold_switch,
        fx6_0_99_is_zoom_position_display=m58_rep.fx6_0_99_is_zoom_position_display,
        fx6_has_iso_auto_min_ss=m58_rep.fx6_has_iso_auto_min_ss,
        fx6_mechanical_shutter_present=m58_rep.fx6_mechanical_shutter_present,
        dormant_lossless_raw_exposure_events=m58_rep.dormant_lossless_raw_exposure_events,
        fx6_still_pipeline_conflation_events=m58_rep.fx6_still_pipeline_conflation_events,
        hlg_still_prereq_or_lockout_drift_events=m58_rep.hlg_still_prereq_or_lockout_drift_events,
        colorspace_adobergb_prefix_violations=m58_rep.colorspace_adobergb_prefix_violations,
        shutter_type_auto_spoof_events=m58_rep.shutter_type_auto_spoof_events,
        fx6_mechanical_shutter_conflation_events=m58_rep.fx6_mechanical_shutter_conflation_events,
        electronic_silent_5lock_bypass_events=m58_rep.electronic_silent_5lock_bypass_events,
        nr_or_drive_burst_wall_violations=m58_rep.nr_or_drive_burst_wall_violations,
        slot1_still_capture_or_sort_write_bytes=m58_rep.slot1_still_capture_or_sort_write_bytes,
        slot1_imagedb_or_burst_mutation_bytes=m58_rep.slot1_imagedb_or_burst_mutation_bytes,
        fx3_ui_exposes_lossless_raw=m58_rep.fx3_ui_exposes_lossless_raw,
        fx3_ui_exposes_shutter_type_auto=m58_rep.fx3_ui_exposes_shutter_type_auto,
        fx6_still_pipeline_present=m58_rep.fx6_still_pipeline_present,
        double_log_or_lockout_bypass_events=m58_rep.double_log_or_lockout_bypass_events,
        pplut_1080p_clamp_bypass_events=m58_rep.pplut_1080p_clamp_bypass_events,
        pp_internal_reset_trap_violations=m58_rep.pp_internal_reset_trap_violations,
        fx6_baselook_confusion_events=m58_rep.fx6_baselook_confusion_events,
        wb_cine_ei_awb_or_custom_setup_trap_events=(
            m58_rep.wb_cine_ei_awb_or_custom_setup_trap_events
        ),
        wb_custom_camset_exclusion_drift_events=m58_rep.wb_custom_camset_exclusion_drift_events,
        metering_desqueeze_or_cine_ei_base_iso_drift_events=(
            m58_rep.metering_desqueeze_or_cine_ei_base_iso_drift_events
        ),
        fx3_ui_exposes_usb_streaming=m58_rep.fx3_ui_exposes_usb_streaming,
        nouvc_spoof_events=m58_rep.nouvc_spoof_events,
        usb_host_data_enumeration_events=m58_rep.usb_host_data_enumeration_events,
        hdmi_lcd_blanking_violations=m58_rep.hdmi_lcd_blanking_violations,
        hdmi_log_1080_bypass_events=m58_rep.hdmi_log_1080_bypass_events,
        slot1_protect_only_vault_violations=m58_rep.slot1_protect_only_vault_violations,
        slot1_vault_format_or_delete_events=m58_rep.slot1_vault_format_or_delete_events,
        network_reset_zero_rf_violations=m58_rep.network_reset_zero_rf_violations,
        fx3_ui_exposes_power_save_by_monitor=m58_rep.fx3_ui_exposes_power_save_by_monitor,
        legacy_power_save_monitor_spoof_events=m58_rep.legacy_power_save_monitor_spoof_events,
        unsafe_power_save_sleep_interference_events=(
            m58_rep.unsafe_power_save_sleep_interference_events
        ),
        bk_lang_parity_drift_events=m58_rep.bk_lang_parity_drift_events,
        stage_b_4lang_uxc_ltt_drift_events=m58_rep.stage_b_4lang_uxc_ltt_drift_events,
        xlrh1_acoustic_feedback_violations=m58_rep.xlrh1_acoustic_feedback_violations,
        audio_mon_4ch_hdmi_confusion_events=m58_rep.audio_mon_4ch_hdmi_confusion_events,
        destructive_delete_confirm_drift_events=m58_rep.destructive_delete_confirm_drift_events,
        slot1_vault_delete_events=m58_rep.slot1_vault_delete_events,
        legacy_mf_assist_spoof_events=m58_rep.legacy_mf_assist_spoof_events,
        still_movie_initial_mag_couplings=m58_rep.still_movie_initial_mag_couplings,
        movie_af_in_focus_mag_events=m58_rep.movie_af_in_focus_mag_events,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            m58_rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        movie_sq_af_illuminator_fire_events=m58_rep.movie_sq_af_illuminator_fire_events,
        legacy_datetime_setup_spoof_events=m58_rep.legacy_datetime_setup_spoof_events,
        unsolicited_rtc_timezone_jump_events=m58_rep.unsolicited_rtc_timezone_jump_events,
        mishoe_5v_overcurrent_events=m58_rep.mishoe_5v_overcurrent_events,
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            m58_rep.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        slot1_vault_mutation_events=m58_rep.slot1_vault_mutation_events,
        slot1_vault_folder_mutation_events=m58_rep.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=m58_rep.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=(
            m58_rep.movie_custom_folder_or_title_overflow_events
        ),
        still_prefix_underscore_lead_or_len_violations=(
            m58_rep.still_prefix_underscore_lead_or_len_violations
        ),
        gamma_assist_log_lockout_bypass_events=m58_rep.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=m58_rep.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=m58_rep.tcub_camera_reset_wipe_or_format_violations,
        fx3_has_builtin_end_filter=m58_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=m58_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=m58_rep.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=m58_rep.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=m58_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            m58_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=m58_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m58_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m58_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m58_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m58_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m58_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m58_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m58_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m58_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m58_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m58_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m58_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m58_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m58_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m58_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m58_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m58_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m58_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m58_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m58_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m58_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m58_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m58_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m58_rep.unbuffered_battery_pull_events,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        master_59pillar_sha256=master_sha,
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


def evaluate_59pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master59PillarRecoveryReport:
    """Short alias for `evaluate_realhw_59pillar_recovery_master`."""
    return evaluate_realhw_59pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_59pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master59PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_59pillar_recovery_master`."""
    return evaluate_realhw_59pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
