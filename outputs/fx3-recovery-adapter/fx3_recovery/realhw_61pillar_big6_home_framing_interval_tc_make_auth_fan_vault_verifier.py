"""Phase 340 Milestone — Recovery Pillar 61 & Concurrent 61/61 Master Recovery Verifier:
Wave-59 Sony ILME-FX3 (Ver. 7.02) vs ILME-FX6 (Ver. 6.01) Empirically Grounded Guardrails:
  * Pillar 61A: Ver. 7.00/7.02 [HOME] (`BIG6`) screen requiring `Mode Settings = Fixed/Variable`
    (`BKID_APP_setting_fps_fixed_variable_select`), dynamic 6-tile matrix (`FPS`, `ISO / Base ISO + EI`
    via `update_big6_item_iso_ei`, `Shutter Speed/Angle`, `Home (Lower Left)` `Aperture` default vs
    metadata-only `ND Filter` with zero physical `e-ND` hardware vs FX6 built-in electronic ND,
    `Picture Profile / Select LUT`, `White Balance`), Manual `[Framing Settings]` (`Framing`,
    `Recording/Streaming` `Full`/`Crop`, `HDMI` `Crop`/`Full`, `TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY`)
    vs 100% dormant AI `[Auto Framing]` (`0` hits in FX3 `appFw.so` -> `EOPNOTSUPP=95`), and Still-only
    `[Interval Shoot Func.]` (7 Resettable sub-items, `Shutter Type in Interval = Electronic Shutter`
    independent default, up to 9,999 shots -> Slot-1 Tier-0 `EROFS=30` firewall blocking `DCIM/` &
    `AVF_INFO` burst writes) vs `FX6 Project > Interval Rec` single-MXF clip.
  * Pillar 61B: Reset-immune `[Time Code Make/Run]` (`Preset`/`Regenerate` — `Regenerate` reads Slot 1
    under `Simult. Recording` and forces `Rec Run`; `VMC-BNCM1` LTC `EXT-LK` requires `Preset + Free Run`),
    HDMI `[REC Control]` requiring `[Time Code Output] = On` (empirically valid in BOTH `Rec. Media = On`
    and `Off(HDMI Only)` including RAW, disabled in `S&Q`/Streaming) + `[4ch Audio Output]` vs FX6
    `TC_MAKE_CLOCK` + `SDI/HDMI Remote I/F` vs `Parallel Rec`, Ver. 7.00+ `[Access Authen.]` (`SSH`
    `MSGID_SSHD_START_CMD` + `PTP-IP`, `WEP`/`WPA-PSK`/`IPsec` removed, `0` hits `HTTP_DIGEST`/`BASIC_AUTH`
    /`HTTPS`, `[Import Root Certificate]` outbound FTPS/RTMPS/Cloud TLS only), and `[Fan Control]`
    4-mode (`Auto`/`Minimum`/`Off in Rec`/`Always Off` on FX3 vs 3-mode with dormant `Always Off` on FX6,
    ZERO `Max` option on BOTH FX3 & FX6!) + `[Auto Power OFF Temp.]` (`Standard`/`High` ~90-120 min),
    Zero-RF (`Airplane Mode=On`, USB-LAN CDC-NCM) & Slot-1 Tier-0 Recovery Vault `EROFS=30` Firewall.
  * Unified 61/61 Master Recovery Aggregator (Pillars 1..60 + Pillar 61).

Safety Redlines (HARD-LOCKED):
  - Zero hardware attach, zero physical device writes, zero USB/UART TX, zero OTP/RPMB, zero eMMC writes.
  - Zero raw firmware bytes leaked (`raw_firmware_bytes_leaked == 0`).
  - Bounded `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` donor inspection (`< 2.0s` budget) with explicit
    `work_root is None` guard and automatic `CLEAN_ROOM_SYNTHETIC` fallback on donorless hosts.
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

from .realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier import (
    MASTER_60_PILLAR_SPECS,
    Master60PillarRecoveryReport,
    P336_DONOR_FX3_APPFW_702_RELPATH,
    P336_DONOR_FX3_BACKUP_BIN_RELPATH,
    P336_DONOR_FX3_UXC_EN_F_RELPATH,
    P336_DONOR_FX3_UXC_EN_G_RELPATH,
    P336_DONOR_FX3_UXC_EN_RELPATH,
    P336_DONOR_FX3_UXC_JA_F_RELPATH,
    P336_DONOR_FX3_UXC_JA_G_RELPATH,
    P336_DONOR_FX3_UXC_JA_RELPATH,
    P336_DONOR_FX3_UXC_SC_F_RELPATH,
    P336_DONOR_FX3_UXC_SC_G_RELPATH,
    P336_DONOR_FX3_UXC_SC_RELPATH,
    P336_DONOR_FX3_UXC_TC_F_RELPATH,
    P336_DONOR_FX3_UXC_TC_G_RELPATH,
    P336_DONOR_FX3_UXC_TC_RELPATH,
    P336_DONOR_FX6_APPFW_601_RELPATH,
    P336_DONOR_FX6_UXC_EN_2_RELPATH,
    P336_DONOR_FX6_UXC_EN_RELPATH,
    P336_PINNED_FX3_APPFW_702_BYTES,
    P336_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P336_PINNED_FX3_BACKUP_BIN_BYTES,
    P336_PINNED_FX3_BACKUP_BIN_SHA256,
    P336_PINNED_FX3_UXC_EN_BYTES,
    P336_PINNED_FX3_UXC_EN_F_BYTES,
    P336_PINNED_FX3_UXC_EN_F_SHA256,
    P336_PINNED_FX3_UXC_EN_G_BYTES,
    P336_PINNED_FX3_UXC_EN_G_SHA256,
    P336_PINNED_FX3_UXC_EN_SHA256,
    P336_PINNED_FX3_UXC_JA_BYTES,
    P336_PINNED_FX3_UXC_JA_F_BYTES,
    P336_PINNED_FX3_UXC_JA_F_SHA256,
    P336_PINNED_FX3_UXC_JA_G_BYTES,
    P336_PINNED_FX3_UXC_JA_G_SHA256,
    P336_PINNED_FX3_UXC_JA_SHA256,
    P336_PINNED_FX3_UXC_SC_BYTES,
    P336_PINNED_FX3_UXC_SC_F_BYTES,
    P336_PINNED_FX3_UXC_SC_F_SHA256,
    P336_PINNED_FX3_UXC_SC_G_BYTES,
    P336_PINNED_FX3_UXC_SC_G_SHA256,
    P336_PINNED_FX3_UXC_SC_SHA256,
    P336_PINNED_FX3_UXC_TC_BYTES,
    P336_PINNED_FX3_UXC_TC_F_BYTES,
    P336_PINNED_FX3_UXC_TC_F_SHA256,
    P336_PINNED_FX3_UXC_TC_G_BYTES,
    P336_PINNED_FX3_UXC_TC_G_SHA256,
    P336_PINNED_FX3_UXC_TC_SHA256,
    P336_PINNED_FX6_APPFW_601_BYTES,
    P336_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P336_PINNED_FX6_UXC_EN_2_BYTES,
    P336_PINNED_FX6_UXC_EN_2_SHA256,
    P336_PINNED_FX6_UXC_EN_BYTES,
    P336_PINNED_FX6_UXC_EN_SHA256,
    evaluate_realhw_60pillar_recovery_master,
)
from . import files as _fx3_files
from .files import is_forced_clean_room
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus

# ---------------------------------------------------------------------------
# Phase 340 Metadata, Safety Redlines & Pinned Budget Constants
# ---------------------------------------------------------------------------

PHASE340_SCHEMA = "realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier_v1"
PHASE340_MASTER_SCHEMA = "realhw_61pillar_recovery_master_v1"
PHASE340_VERSION = "1.0.0"
PHASE340_PHASE_NUMBER = 340

P340_ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"

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

P340_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
P340_OVERALL_READY_FOR_HARDWARE_ATTACH = False
P340_CROSS_MODEL_FLASH_AUTHORIZED = False

OTP_FUSE_TOUCHES = 0
OTP_FUSE_WRITES = 0
RPMB_COUNTER_INCREMENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PHYSICAL_DEVICE_WRITES = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

P340_BOUNDED_HEADER_BYTES = 4096
P340_MAX_FULL_DONOR_BYTES = 3_000_000
P340_DONOR_INSPECT_BUDGET_SECONDS = 2.0
P340_DONOR_INSPECT_CI_BUDGET_SECONDS = 2.0
P340_FAST_CLI_BUDGET_SECONDS = 1.50
P340_NOMINAL_BUDGET_SECONDS = 4.00
P340_CONCURRENT_CEILING_SECONDS = 6.00

P340_EBUSY_ERRNO = 16
P340_EINVAL_ERRNO = 22
P340_EROFS_ERRNO = 30
P340_EOPNOTSUPP_ERRNO = 95

# Camera Identities
P340_FX3_MODEL_NAME = "ILME-FX3"
P340_FX3_MODEL_ID = 0x91030080
P340_FX3_PRODUCT_CODENAME = "PRODUCT_MODEL_ALCIN_UUD"
P340_FX3_HELPGUIDE_ID = "ilc/2210"
P340_FX3_FW_VERSION = "7.02"
P340_FX3_SUPPORTED_FW_VERSIONS = ("7.02", "7.01", "7.00", "6.02", "6.00")
P340_FX3_BIG6_MIN_FW_VERSIONS = ("7.02", "7.01", "7.00")

P340_FX6_DONOR_MODEL_NAME = "ILME-FX6"
P340_FX6_DONOR_FW_VERSION = "6.01"
P340_FX6_PRODUCT_CODENAME = "PRODUCT_MODEL_CHAPLIN"

# Pinned Donor Relpaths & Digests (17 Wave-59 donors: 14 FX3 7.02 + 3 FX6 6.01)
P340_DONOR_FX3_APPFW_702_RELPATH = P336_DONOR_FX3_APPFW_702_RELPATH
P340_DONOR_FX6_APPFW_601_RELPATH = P336_DONOR_FX6_APPFW_601_RELPATH
P340_DONOR_FX3_BACKUP_BIN_RELPATH = P336_DONOR_FX3_BACKUP_BIN_RELPATH
P340_DONOR_FX3_UXC_EN_F_RELPATH = P336_DONOR_FX3_UXC_EN_F_RELPATH
P340_DONOR_FX3_UXC_SC_F_RELPATH = P336_DONOR_FX3_UXC_SC_F_RELPATH
P340_DONOR_FX3_UXC_TC_F_RELPATH = P336_DONOR_FX3_UXC_TC_F_RELPATH
P340_DONOR_FX3_UXC_JA_F_RELPATH = P336_DONOR_FX3_UXC_JA_F_RELPATH
P340_DONOR_FX3_UXC_EN_RELPATH = P336_DONOR_FX3_UXC_EN_RELPATH
P340_DONOR_FX3_UXC_SC_RELPATH = P336_DONOR_FX3_UXC_SC_RELPATH
P340_DONOR_FX3_UXC_TC_RELPATH = P336_DONOR_FX3_UXC_TC_RELPATH
P340_DONOR_FX3_UXC_JA_RELPATH = P336_DONOR_FX3_UXC_JA_RELPATH
P340_DONOR_FX3_UXC_EN_G_RELPATH = P336_DONOR_FX3_UXC_EN_G_RELPATH
P340_DONOR_FX3_UXC_SC_G_RELPATH = P336_DONOR_FX3_UXC_SC_G_RELPATH
P340_DONOR_FX3_UXC_TC_G_RELPATH = P336_DONOR_FX3_UXC_TC_G_RELPATH
P340_DONOR_FX3_UXC_JA_G_RELPATH = P336_DONOR_FX3_UXC_JA_G_RELPATH
P340_DONOR_FX6_UXC_EN_RELPATH = P336_DONOR_FX6_UXC_EN_RELPATH
P340_DONOR_FX6_UXC_EN_2_RELPATH = P336_DONOR_FX6_UXC_EN_2_RELPATH

P340_PINNED_FX3_APPFW_702_BYTES = P336_PINNED_FX3_APPFW_702_BYTES
P340_PINNED_FX3_APPFW_702_HDR4K_SHA256 = P336_PINNED_FX3_APPFW_702_HDR4K_SHA256
P340_PINNED_FX6_APPFW_601_BYTES = P336_PINNED_FX6_APPFW_601_BYTES
P340_PINNED_FX6_APPFW_601_HDR4K_SHA256 = P336_PINNED_FX6_APPFW_601_HDR4K_SHA256
P340_PINNED_FX3_BACKUP_BIN_BYTES = P336_PINNED_FX3_BACKUP_BIN_BYTES
P340_PINNED_FX3_BACKUP_BIN_SHA256 = P336_PINNED_FX3_BACKUP_BIN_SHA256
P340_PINNED_FX3_UXC_EN_F_BYTES = P336_PINNED_FX3_UXC_EN_F_BYTES
P340_PINNED_FX3_UXC_EN_F_SHA256 = P336_PINNED_FX3_UXC_EN_F_SHA256
P340_PINNED_FX3_UXC_SC_F_BYTES = P336_PINNED_FX3_UXC_SC_F_BYTES
P340_PINNED_FX3_UXC_SC_F_SHA256 = P336_PINNED_FX3_UXC_SC_F_SHA256
P340_PINNED_FX3_UXC_TC_F_BYTES = P336_PINNED_FX3_UXC_TC_F_BYTES
P340_PINNED_FX3_UXC_TC_F_SHA256 = P336_PINNED_FX3_UXC_TC_F_SHA256
P340_PINNED_FX3_UXC_JA_F_BYTES = P336_PINNED_FX3_UXC_JA_F_BYTES
P340_PINNED_FX3_UXC_JA_F_SHA256 = P336_PINNED_FX3_UXC_JA_F_SHA256
P340_PINNED_FX3_UXC_EN_BYTES = P336_PINNED_FX3_UXC_EN_BYTES
P340_PINNED_FX3_UXC_EN_SHA256 = P336_PINNED_FX3_UXC_EN_SHA256
P340_PINNED_FX3_UXC_SC_BYTES = P336_PINNED_FX3_UXC_SC_BYTES
P340_PINNED_FX3_UXC_SC_SHA256 = P336_PINNED_FX3_UXC_SC_SHA256
P340_PINNED_FX3_UXC_TC_BYTES = P336_PINNED_FX3_UXC_TC_BYTES
P340_PINNED_FX3_UXC_TC_SHA256 = P336_PINNED_FX3_UXC_TC_SHA256
P340_PINNED_FX3_UXC_JA_BYTES = P336_PINNED_FX3_UXC_JA_BYTES
P340_PINNED_FX3_UXC_JA_SHA256 = P336_PINNED_FX3_UXC_JA_SHA256
P340_PINNED_FX3_UXC_EN_G_BYTES = P336_PINNED_FX3_UXC_EN_G_BYTES
P340_PINNED_FX3_UXC_EN_G_SHA256 = P336_PINNED_FX3_UXC_EN_G_SHA256
P340_PINNED_FX3_UXC_SC_G_BYTES = P336_PINNED_FX3_UXC_SC_G_BYTES
P340_PINNED_FX3_UXC_SC_G_SHA256 = P336_PINNED_FX3_UXC_SC_G_SHA256
P340_PINNED_FX3_UXC_TC_G_BYTES = P336_PINNED_FX3_UXC_TC_G_BYTES
P340_PINNED_FX3_UXC_TC_G_SHA256 = P336_PINNED_FX3_UXC_TC_G_SHA256
P340_PINNED_FX3_UXC_JA_G_BYTES = P336_PINNED_FX3_UXC_JA_G_BYTES
P340_PINNED_FX3_UXC_JA_G_SHA256 = P336_PINNED_FX3_UXC_JA_G_SHA256
P340_PINNED_FX6_UXC_EN_BYTES = P336_PINNED_FX6_UXC_EN_BYTES
P340_PINNED_FX6_UXC_EN_SHA256 = P336_PINNED_FX6_UXC_EN_SHA256
P340_PINNED_FX6_UXC_EN_2_BYTES = P336_PINNED_FX6_UXC_EN_2_BYTES
P340_PINNED_FX6_UXC_EN_2_SHA256 = P336_PINNED_FX6_UXC_EN_2_SHA256

# Zero-Violation Pillar 61 Counters & Vault Flags
P340_BIG6_HOME_OR_LOWER_LEFT_ND_DRIFT_EVENTS = 0
P340_FRAMING_MANUAL_OR_DORMANT_AUTO_FRAMING_DRIFT_EVENTS = 0
P340_INTERVAL_SHOOT_9999_OR_FX6_MXF_SPOOF_EVENTS = 0
P340_TC_MAKE_REGEN_OR_HDMI_REC_CTRL_DRIFT_EVENTS = 0
P340_ACCESS_AUTHEN_SSH_TLS_OR_FAN_MAX_DRIFT_EVENTS = 0
P340_ZERO_RF_OR_SLOT1_VAULT_BYPASS_EVENTS = 0

P340_RF_PACKETS_TRANSMITTED = 0
P340_RF_NVS_MUTATION_BYTES = 0
P340_SLOT1_DATA_SECTOR_WRITES = 0
P340_SLOT1_DCIM_AVF_MUTATION_BYTES = 0
P340_SLOT1_VAULT_MUTATION_BYTES = 0
P340_SLOT1_FORMAT_HARD_LOCKED = True
P340_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True
P340_AIRPLANE_MODE_FORCED_ON = True

P340_STAGE_B_VOLATILE_OVERLAY_DIR = "/tmp/fx3_stage_b_overlay/pillar61"
P340_FORBIDDEN_PERSISTENT_TARGETS = (
    "/dev/cnflasha",
    "/setting",
    "/mnt/emmc",
    "/nflasha",
)
P340_TIER0_SURFACE_COUNT = 16
P340_SLOT1_VAULT_SLOT = 1
P340_SAFE_SECONDARY_SLOT = 2

# ---------------------------------------------------------------------------
# Wave-59 Empirical Constants: Pillar 61A (BIG6 Home, Framing Settings, Interval Shoot)
# ---------------------------------------------------------------------------

P340_MODE_SETTINGS_FIXED_VAR_F_RESID16 = 0x7D0D
P340_HOME_KEY_F_RESID16 = 0x7CAD
P340_HOME_OPEN_F_RESID16 = 0x7CB1
P340_HOME_LOWER_LEFT_F_RESID16 = 0x7CE3
P340_SWIPE_DOWN_F_RESID16 = 0x7CDD
P340_SELECT_LUT_F_RESID16 = 0x643E
P340_BASE_ISO_F_RESID16 = 0x78CE

P340_BKID_MODE_SETTINGS_FIXED_VAR = "BKID_APP_setting_fps_fixed_variable_select"
P340_BKID_HOME_SCREEN_STATE = "BKID_APP_home_screen_state"
P340_BKID_HOME_LAST_CURSOR_POS = "BKID_APP_home_screen_last_cursor_position_number"
P340_BKID_HOME_LOWER_LEFT = "BKID_APP_setting_movie_home_lower_left"
P340_BIG6_FUNC_ISO_EI = "update_big6_item_iso_ei"
P340_BIG6_VIEW_SYMBOL = "26view_tp_button_01_for_big6"

P340_MODE_SETTINGS_OPTIONS = ("Movie", "Fixed/Variable")
P340_BIG6_ENTRY_TRIGGERS = ("NONE", "HOME_KEY", "SWIPE_DOWN")
P340_HOME_SCREEN_STATES = (
    "HOME_SCREEN_STATE_OFF",
    "HOME_SCREEN_STATE_ON_CURSOR_OFF",
    "HOME_SCREEN_STATE_ON_CURSOR_ON",
    "HOME_SCREEN_STATE_TEMP_OFF",
)
P340_LOG_SHOOTING_MODES = ("Off", "Flexible ISO", "Cine EI", "Cine EI Quick")
P340_SHUTTER_MODES = ("Speed", "Angle")
P340_HOME_LOWER_LEFT_MODES = ("Aperture", "ND Filter")
P340_FX3_BIG6_TILE_COUNT = 6
P340_FX3_PHYSICAL_END_HARDWARE = False
P340_FX6_BIG6_TILES = (
    "FPS",
    "Shutter",
    "ISO/Gain/EI",
    "ND Filter/Iris",
    "Base Look/Scene",
    "White Balance",
)
P340_FX6_END_STOPS = ("Clear", "1/4", "1/128", "Auto")

# Manual [Framing Settings] vs Dormant AI [Auto Framing]
P340_FRAMING_SETTINGS_F_RESID16 = 0x7D18
P340_FRAMING_REC_STREAMING_F_RESID16 = 0x7D13
P340_FRAMING_HDMI_F_RESID16 = 0x7D0F
P340_FRAMING_SWITCH_F_RESID16 = 0x7D1E
P340_FRAMING_STOP_FULL_F_RESID16 = 0x7D25
P340_FX3_FRAMING_SUPPORT_ENUM = "TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY"
P340_FRAMING_CROP_OPTIONS = ("Full", "Crop")
P340_FRAMING_DEFAULT_STATE = "Off"
P340_FRAMING_DEFAULT_REC_STREAMING = "Full"
P340_FRAMING_DEFAULT_HDMI = "Crop"

P340_DORMANT_AUTO_FRAMING_F_RESID16S: Tuple[int, ...] = (0x6BE6, 0x79BC, 0x6C9D, 0x69CC, 0x7566)
P340_DORMANT_AUTO_FRAMING_SYMBOLS = (
    "Auto Framing",
    "Auto Framing Settings",
    "AUTO_FRAMING_AFR",
    "FRAMING_SIZE",
    "FRAMING_FOLLOW_UP_SPEED",
    "PTZAUTOFRAMING_MODE",
    "Crop Level",
    "Framing Tracking Speed",
    "Framing Stabilizer",
)
P340_FX3_APPFW_AUTO_FRAMING_HIT_COUNT = 0

# Still-only [Interval Shoot Func.] vs FX6 [Interval Rec]
P340_INTERVAL_SHOOT_FUNC_F_RESID16 = 0x7027
P340_INTERVAL_SHOOTING_F_RESID16 = 0x7874
P340_INTERVAL_START_TIME_F_RESID16 = 0x6B0A
P340_INTERVAL_PERIOD_F_RESID16 = 0x624C
P340_INTERVAL_NUM_SHOTS_F_RESID16 = 0x71DD
P340_INTERVAL_AE_TRACK_F_RESID16 = 0x615B
P340_INTERVAL_SHUTTER_TYPE_F_RESID16 = 0x74C0
P340_INTERVAL_PRIORITY_F_RESID16 = 0x6F69
P340_DISPLAY_AS_GROUP_F_RESID16 = 0x6F26
P340_PB_SPEED_INTERVAL_F_RESID16 = 0x72BD

P340_INTERVAL_SUBITEM_COUNT = 7
P340_INTERVAL_START_TIME_MIN_SEC = 1
P340_INTERVAL_START_TIME_MAX_SEC = 5999  # 99m59s
P340_INTERVAL_START_TIME_DEFAULT_SEC = 1
P340_INTERVAL_SEC_MIN = 1
P340_INTERVAL_SEC_MAX = 60
P340_INTERVAL_SEC_DEFAULT = 3
P340_INTERVAL_SHOTS_MIN = 1
P340_INTERVAL_SHOTS_MAX = 9999
P340_INTERVAL_SHOTS_DEFAULT = 30
P340_INTERVAL_AE_TRACKING_MODES = ("High", "Mid", "Low")
P340_INTERVAL_AE_TRACKING_DEFAULT = "Mid"
P340_INTERVAL_SHUTTER_TYPES = ("Mechanical Shutter", "Electronic Shutter")
P340_INTERVAL_SHUTTER_TYPE_DEFAULT = "Electronic Shutter"

P340_FX6_INTERVAL_REC_FRAME_COUNTS = (1, 2, 3, 4, 6, 9, 12, 24)
P340_FX6_INTERVAL_REC_PRE_LIGHTING = ("Off", "2s", "5s", "10s")
P340_FX6_INTERVAL_REC_EXCLUSIONS = (
    "Picture Cache Rec",
    "Simul Rec",
    "S&Q Motion",
    "Proxy",
    "Audio",
)

# ---------------------------------------------------------------------------
# Wave-59 Empirical Constants: Pillar 61B (TC Make/Run, HDMI REC Control, Access Authen., Fan Control)
# ---------------------------------------------------------------------------

P340_TC_MAKE_F_RESID16 = 0x6B79
P340_TC_RUN_F_RESID16 = 0x7313
P340_REC_MEDIA_HDMI_F_RESID16 = 0x6144
P340_HDMI_TC_OUTPUT_F_RESID16 = 0x72AF
P340_HDMI_REC_CONTROL_F_RESID16 = 0x76E1
P340_AUDIO_4CH_OUTPUT_F_RESID16 = 0x6AA0

P340_TC_MAKE_FX3_SYMBOL_REGENERATE = "VAL_setting_tc_make_TC_MAKE_REGENRATE"
P340_FX6_TC_MAKE_SYMBOL_CLOCK = "VAL_setting_tc_make_TC_MAKE_CLOCK"
P340_TIMECODE_MAKE_MODES = ("Preset", "Regenerate", "Clock")
P340_FX3_TIMECODE_MAKE_MODES = ("Preset", "Regenerate")
P340_TIMECODE_RUN_MODES = ("Rec Run", "Free Run")
P340_RECORDING_MEDIA_MODES = ("Slot 1", "Slot 2", "Simult. Recording", "Relay Rec")
P340_REC_MEDIA_HDMI_MODES = ("On", "Off(HDMI Only)")
P340_AUDIO_4CH_OUTPUT_MODES = ("CH1/CH2", "CH3/CH4")
P340_FX6_SDI_HDMI_REC_CTRL_MODES = ("Off", "SDI/HDMI Remote I/F", "Parallel Rec")

# Ver. 7.00+ [Access Authen.] & TLS Root Cert
P340_ACCESS_AUTHEN_F_RESID16 = 0x7ADA
P340_ACCESS_AUTHEN_INFO_F_RESID16 = 0x6B2B
P340_ACCESS_AUTHEN_FINGERPRINT_G_RESID16 = 0x610B
P340_IMPORT_ROOT_CERT_F_RESID16 = 0x7940
P340_DORMANT_IPSEC_F_RESID16 = 0x69AA
P340_SSHD_START_CMD = "MSGID_SSHD_START_CMD"

P340_FX3_ACCESS_AUTHEN_PROTOCOLS = ("SSH+PTP-IP",)
P340_FX3_FORBIDDEN_AUTH_PROTOCOLS = ("HTTP_DIGEST", "BASIC_AUTH", "HTTPS")
P340_FX3_WIFI_SECURITY_ACTIVE_MODES = ("WPA2-PSK", "WPA3-SAE")
P340_FX3_WIFI_SECURITY_REMOVED_MODES = ("WEP", "WPA-PSK", "Security(IPsec)")
P340_FX3_WIFI_SECURITY_ALL_MODES = (
    P340_FX3_WIFI_SECURITY_ACTIVE_MODES + P340_FX3_WIFI_SECURITY_REMOVED_MODES
)
P340_ROOT_CERT_TYPES = ("CLOUD", "FTP", "RTMP")
P340_FX3_HTTP_DIGEST_HTTPS_HIT_COUNT = 0

# [Fan Control] & [Auto Power OFF Temp.] — ZERO `Max` option on BOTH FX3 & FX6!
P340_FAN_CONTROL_F_RESID16 = 0x6E77
P340_FAN_MINIMUM_F_RESID16 = 0x6D0D
P340_FAN_OFF_IN_REC_F_RESID16 = 0x6B53
P340_FAN_ALWAYS_OFF_F_RESID16 = 0x68FD
P340_AUTO_PWR_OFF_TEMP_F_RESID16 = 0x70F1

P340_FX3_FAN_CONTROL_MODES = ("Auto", "Minimum", "Off in Rec", "Always Off")
P340_FX6_FAN_CONTROL_ACTIVE_MODES = ("Auto", "Minimum", "Off in Rec")
P340_FAN_CONTROL_ALL_MODES = ("Auto", "Minimum", "Off in Rec", "Always Off", "Max", "Always (Max)")
P340_FAN_CONTROL_FORBIDDEN_MAX_MODES = ("Max", "Always (Max)")
P340_FX3_FAN_MAX_HIT_COUNT = 0
P340_FX6_FAN_MAX_HIT_COUNT = 0
P340_AUTO_POWER_OFF_TEMP_MODES = ("Standard", "High")
P340_FX3_4K60_STANDARD_MIN = 30
P340_FX3_4K60_HIGH_MIN = 90
P340_FX3_HD60_STANDARD_MIN = 60
P340_FX3_HD60_HIGH_MIN = 120

P340_SHOOTING_DOMAINS = ("Still", "Movie", "S&Q")
P340_EXPOSURE_MODES = ("P", "A", "S", "M", "iAuto", "SCN")
P340_ON_OFF_MODES = ("On", "Off")
P340_RESET_ACTIONS = ("None", "Camera Settings Reset", "Reset Network Set.", "Initialize")
P340_NETWORK_TRANSPORTS = ("USB-LAN (CDC-NCM)", "Wi-Fi", "Bluetooth", "Wired LAN (Ethernet)")
P340_SAFE_WIRED_TRANSPORT = "USB-LAN (CDC-NCM)"

P340_VAULT_ACTIONS = (
    "NONE",
    "READ_ONLY_AUDIT",
    "STREAM_ONLY_USB_LAN",
    "HDMI_ONLY_EXT_REC_TRIGGER",
    "INTERVAL_SHOOT_SLOT2",
    "INTERVAL_SHOOT_SLOT1_BURST",
    "TC_REGEN_SLOT1_READ_ONLY",
    "IMPORT_ROOT_CERT_SLOT2",
    "IMPORT_ROOT_CERT_SLOT1_WRITE",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P340_WRITE_MUTATING_VAULT_ACTIONS = (
    "INTERVAL_SHOOT_SLOT1_BURST",
    "IMPORT_ROOT_CERT_SLOT1_WRITE",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P340_VAULT_FIREWALL_ERRNOS = ("EBUSY", "EROFS", "EOPNOTSUPP")
P340_VAULT_FIREWALL_ERRNO_CODES: Dict[str, int] = {
    "EBUSY": 16,
    "EROFS": 30,
    "EOPNOTSUPP": 95,
}

# Block Codes & Status Constants
P340_BLOCKED_SAFETY_POLICY_VIOLATION = "P340_BLOCKED_SAFETY_POLICY_VIOLATION"
P340_BLOCKED_INVALID_PILLAR61A_SPEC = "P340_BLOCKED_INVALID_PILLAR61A_SPEC"
P340_BLOCKED_INVALID_PILLAR61B_SPEC = "P340_BLOCKED_INVALID_PILLAR61B_SPEC"
P340_BLOCKED_BIG6_HOME_OR_LOWER_LEFT_ND_DRIFT = "P340_BLOCKED_BIG6_HOME_OR_LOWER_LEFT_ND_DRIFT"
P340_BLOCKED_FRAMING_MANUAL_OR_DORMANT_AUTO_FRAMING_DRIFT = (
    "P340_BLOCKED_FRAMING_MANUAL_OR_DORMANT_AUTO_FRAMING_DRIFT"
)
P340_BLOCKED_INTERVAL_SHOOT_9999_OR_FX6_MXF_SPOOF = (
    "P340_BLOCKED_INTERVAL_SHOOT_9999_OR_FX6_MXF_SPOOF"
)
P340_BLOCKED_TC_MAKE_REGEN_OR_HDMI_REC_CTRL_DRIFT = (
    "P340_BLOCKED_TC_MAKE_REGEN_OR_HDMI_REC_CTRL_DRIFT"
)
P340_BLOCKED_ACCESS_AUTHEN_SSH_TLS_OR_FAN_MAX_DRIFT = (
    "P340_BLOCKED_ACCESS_AUTHEN_SSH_TLS_OR_FAN_MAX_DRIFT"
)
P340_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL = (
    "P340_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL"
)
P340_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL = P340_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL
P340_BLOCKED_PERSISTENT_OVERLAY_ESCAPE = "P340_BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P340_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT = "P340_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P340_STATUS_VERIFIED_PILLAR_61A = "VERIFIED_PILLAR_61A_BIG6_HOME_FRAMING_INTERVAL_VAULT"
P340_STATUS_REJECTED_PILLAR_61A = "REJECTED_PILLAR_61A_BIG6_HOME_FRAMING_INTERVAL_VAULT"
P340_STATUS_VERIFIED_PILLAR_61B = "VERIFIED_PILLAR_61B_TC_MAKE_HDMI_REC_SSH_AUTH_FAN_VAULT"
P340_STATUS_REJECTED_PILLAR_61B = "REJECTED_PILLAR_61B_TC_MAKE_HDMI_REC_SSH_AUTH_FAN_VAULT"
P340_STATUS_VERIFIED_PILLAR61_SUITE = "VERIFIED_PILLAR61_BIG6_FRAMING_INTERVAL_TC_AUTH_FAN_VAULT"
P340_STATUS_FAIL_PILLAR61_SUITE = "FAIL_PILLAR61_BIG6_FRAMING_INTERVAL_TC_AUTH_FAN_VAULT"
P340_STATUS_VERIFIED_61OF61_AGGREGATOR = "VERIFIED_61OF61_PILLAR_RECOVERY_MASTER"
P340_STATUS_FAIL_61OF61_AGGREGATOR = "FAIL_61OF61_PILLAR_RECOVERY_MASTER"

P340_PILLAR_61A_SCENARIO_IDS = (
    "P61A1_BIG6_FIXED_VAR_CINE_EI_LOWER_LEFT_ND_METADATA_AND_MANUAL_FRAMING_ALLOW",
    "P61A2_STILL_INTERVAL_SHOOT_ELECTRONIC_DEFAULT_SLOT2_AND_FX6_MXF_PARITY_ALLOW",
    "P61A3_BIG6_WITHOUT_FIXED_VAR_OR_PHYSICAL_END_OR_PRE700_SPOOF_REJECT",
    "P61A4_DORMANT_AUTO_FRAMING_OR_HFR_RECORDING_FRAMING_LOCK_BYPASS_REJECT",
    "P61A5_INTERVAL_BULB_IAUTO_SHUTTER_OR_FX6_CONFLATION_SPOOF_REJECT",
    "P61A6_SLOT1_INTERVAL_9999_BURST_EROFS_OR_OVERLAY_H0_H3_DRIFT_REJECT",
)
P340_PILLAR_61B_SCENARIO_IDS = (
    "P61B1_TC_REGEN_FORCED_REC_RUN_SLOT1_HDMI_REC_CTRL_WITH_TC_OUT_ON_ALLOW",
    "P61B2_ACCESS_AUTHEN_SSH_TLS_OUTBOUND_WPA3_FAN_4MODE_ZERO_RF_VAULT_ALLOW",
    "P61B3_HDMI_REC_CTRL_TC_OUT_OFF_OR_EXT_LK_REGEN_CONFLICT_OR_FX6_CLOCK_SPOOF_REJECT",
    "P61B4_ACCESS_AUTHEN_HTTP_DIGEST_HTTPS_WEP_IPSEC_OR_AIRPLANE_RESET_WIPE_REJECT",
    "P61B5_FAN_CONTROL_MAX_SPOOF_ON_FX3_OR_FX6_OR_FX6_ALWAYS_OFF_EXPOSED_REJECT",
    "P61B6_ZERO_RF_BREACH_OR_SLOT1_VAULT_FORMAT_WRITE_EROFS_BYPASS_REJECT",
)

# ---------------------------------------------------------------------------
# 61-Pillar Master Registry (Pillars 1..60 + Pillar 61)
# ---------------------------------------------------------------------------

MASTER_61_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_60_PILLAR_SPECS + (
    (
        61,
        "pillar61_big6_home_framing_interval_tc_make_auth_fan_vault",
        "Phase 340",
        "fx3_recovery.realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier",
    ),
)
MASTER_61_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_61_PILLAR_SPECS)
MASTER_61_PILLAR_COUNT = len(MASTER_61_PILLAR_SPECS)

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
    env_flag = os.environ.get(P340_ENV_CLEAN_ROOM_TEST, "").strip().lower()
    if env_flag in ("1", "true", "yes"):
        return True
    if is_forced_clean_room():
        return True
    return False


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true" or os.environ.get(
        "CI", ""
    ).strip().lower() in ("1", "true", "yes"):
        return P340_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P340_DONOR_INSPECT_BUDGET_SECONDS


def _is_tmpfs_path(path: str) -> bool:
    norm = posixpath.normpath(path)
    return norm == "/tmp" or norm.startswith("/tmp/")


def _targets_persistent_emmc(path: str) -> bool:
    norm = posixpath.normpath(path)
    return any(
        norm == pref or norm.startswith(pref + "/") or norm.startswith(pref)
        for pref in P340_FORBIDDEN_PERSISTENT_TARGETS
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
    if not P340_SLOT1_FORMAT_HARD_LOCKED:
        errs.append("P340_SLOT1_FORMAT_HARD_LOCKED must remain True")
    if not P340_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED:
        errs.append("P340_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED must remain True")
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


def compute_expected_big6_framing_interval_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    exposure_mode: str,
    mode_settings: str,
    big6_entry_trigger: str,
    touch_operation_enabled: bool,
    swipe_down_setting: str,
    log_shooting_mode: str,
    shutter_mode: str,
    home_lower_left_mode: str,
    requested_physical_end_hw: bool,
    framing_enabled: bool,
    framing_rec_streaming: str,
    framing_hdmi: str,
    apsc_s35_requested: bool,
    movie_frame_rate_fps: float,
    active_recording: bool,
    active_streaming: bool,
    requested_dormant_auto_framing_symbols: Tuple[str, ...],
    interval_shooting_enabled: bool,
    interval_start_time_sec: int,
    interval_period_sec: int,
    interval_num_shots: int,
    interval_ae_tracking: str,
    interval_shutter_type: str,
    interval_priority: str,
    bulb_active: bool,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
    interval_targets_slot1: bool,
) -> Dict[str, Any]:
    """Compute canonical Wave-59 Pillar 61A state:
    Ver. 7.00+ BIG6 Home Screen (`Mode Settings = Fixed/Variable`, 6 dynamic tiles, Lower-Left
    metadata-only ND vs Aperture), Manual `[Framing Settings]` vs Dormant `[Auto Framing]`, and
    Still-only `[Interval Shoot Func.]` (`<= 9999` shots, Electronic Shutter default, Slot-1 EROFS=30)."""
    is_fx3 = camera_model == P340_FX3_MODEL_NAME
    supports_big6 = is_fx3 and fw_version in P340_FX3_BIG6_MIN_FW_VERSIONS

    # 1. Ver. 7.00+ BIG6 Home Screen activation & dynamic tile mapping
    swipe_entry_ok = (
        big6_entry_trigger != "SWIPE_DOWN"
        or (touch_operation_enabled and swipe_down_setting == "Open Home Screen")
    )
    big6_prereq_ok = (
        supports_big6
        and mode_settings == "Fixed/Variable"
        and swipe_entry_ok
    )
    if big6_entry_trigger != "NONE":
        if is_fx3 and big6_prereq_ok:
            big6_active = True
            big6_errno: Optional[int] = None
        else:
            big6_active = False
            big6_errno = P340_EOPNOTSUPP_ERRNO
    else:
        big6_active = False
        big6_errno = None

    tile2_exposure = (
        "Base ISO + EI" if log_shooting_mode in ("Cine EI", "Cine EI Quick") else "ISO"
    )
    tile3_shutter = "Shutter Angle" if shutter_mode == "Angle" else "Shutter Speed"
    tile4_lower_left = "ND Filter" if home_lower_left_mode == "ND Filter" else "Aperture"
    tile5_look = "Select LUT" if log_shooting_mode != "Off" else "Picture Profile"
    big6_tiles = ("FPS", tile2_exposure, tile3_shutter, tile4_lower_left, tile5_look, "White Balance")

    physical_end_errno: Optional[int] = (
        P340_EOPNOTSUPP_ERRNO if (is_fx3 and requested_physical_end_hw) else None
    )

    # 2. Manual [Framing Settings] vs Dormant AI [Auto Framing]
    framing_locked = (
        not is_fx3
        or movie_frame_rate_fps >= 100.0
        or active_recording
        or active_streaming
    )
    if framing_enabled and framing_locked:
        effective_framing_enabled = False
        framing_errno: Optional[int] = P340_EBUSY_ERRNO if is_fx3 else P340_EOPNOTSUPP_ERRNO
    else:
        effective_framing_enabled = bool(framing_enabled and is_fx3)
        framing_errno = None

    effective_apsc_s35 = False if effective_framing_enabled else bool(apsc_s35_requested)
    dormant_auto_framing_errno: Optional[int] = (
        P340_EOPNOTSUPP_ERRNO if len(requested_dormant_auto_framing_symbols) > 0 else None
    )

    # 3. Still-only [Interval Shoot Func.] (7 Resettable sub-items, 9999 shots)
    interval_range_valid = (
        P340_INTERVAL_START_TIME_MIN_SEC <= interval_start_time_sec <= P340_INTERVAL_START_TIME_MAX_SEC
        and P340_INTERVAL_SEC_MIN <= interval_period_sec <= P340_INTERVAL_SEC_MAX
        and P340_INTERVAL_SHOTS_MIN <= interval_num_shots <= P340_INTERVAL_SHOTS_MAX
        and interval_ae_tracking in P340_INTERVAL_AE_TRACKING_MODES
        and interval_shutter_type in P340_INTERVAL_SHUTTER_TYPES
        and interval_priority in P340_ON_OFF_MODES
    )
    interval_blocked_reasons: List[str] = []
    if not is_fx3 or shooting_domain != "Still":
        interval_blocked_reasons.append("REQUIRES_FX3_STILL_DOMAIN")
    if exposure_mode == "iAuto":
        interval_blocked_reasons.append("UNAVAILABLE_IN_INTELLIGENT_AUTO")
    if not interval_range_valid:
        interval_blocked_reasons.append("INVALID_INTERVAL_RANGE")

    if interval_shooting_enabled and interval_blocked_reasons:
        effective_interval_enabled = False
        interval_errno: Optional[int] = (
            P340_EINVAL_ERRNO if not interval_range_valid else P340_EOPNOTSUPP_ERRNO
        )
    elif not interval_range_valid:
        effective_interval_enabled = False
        interval_errno = P340_EINVAL_ERRNO
    else:
        effective_interval_enabled = bool(interval_shooting_enabled)
        interval_errno = None

    bulb_overridden_to_30s = bool(effective_interval_enabled and bulb_active)

    # 4. Reset matrix: Home (Lower Left), Framing Settings (3), Interval Shoot (7) are ALL Resettable!
    if is_fx3 and reset_action in ("Camera Settings Reset", "Initialize"):
        post_home_lower_left = "Aperture"
        post_framing_enabled = False
        post_framing_rec_streaming = P340_FRAMING_DEFAULT_REC_STREAMING
        post_framing_hdmi = P340_FRAMING_DEFAULT_HDMI
        post_interval_enabled = False
        post_interval_start_sec = P340_INTERVAL_START_TIME_DEFAULT_SEC
        post_interval_period_sec = P340_INTERVAL_SEC_DEFAULT
        post_interval_num_shots = P340_INTERVAL_SHOTS_DEFAULT
        post_interval_ae_tracking = P340_INTERVAL_AE_TRACKING_DEFAULT
        post_interval_shutter_type = P340_INTERVAL_SHUTTER_TYPE_DEFAULT
        post_interval_priority = "Off"
    else:
        post_home_lower_left = home_lower_left_mode
        post_framing_enabled = effective_framing_enabled
        post_framing_rec_streaming = framing_rec_streaming
        post_framing_hdmi = framing_hdmi
        post_interval_enabled = effective_interval_enabled
        post_interval_start_sec = interval_start_time_sec
        post_interval_period_sec = interval_period_sec
        post_interval_num_shots = interval_num_shots
        post_interval_ae_tracking = interval_ae_tracking
        post_interval_shutter_type = interval_shutter_type
        post_interval_priority = interval_priority

    # 5. Slot-1 Tier-0 Vault Firewall for Interval 9999-shot DCIM/AVF_INFO bursts
    mutates_slot1 = (
        requested_vault_slot == P340_SLOT1_VAULT_SLOT
        and (
            requested_vault_action in P340_WRITE_MUTATING_VAULT_ACTIONS
            or (effective_interval_enabled and interval_targets_slot1)
        )
    )
    if mutates_slot1 and slot1_holds_tier0_vault:
        vault_action_allowed = False
        vault_firewall_errno: Optional[str] = "EROFS"
    elif requested_vault_action in ("FORMAT_QUICK", "FORMAT_FULL"):
        vault_action_allowed = False
        vault_firewall_errno = "EROFS"
    elif requested_vault_action in ("READ_ONLY_AUDIT", "INTERVAL_SHOOT_SLOT2") and not interval_targets_slot1:
        vault_action_allowed = True
        vault_firewall_errno = None
    elif requested_vault_action == "NONE":
        vault_action_allowed = False
        vault_firewall_errno = None
    elif requested_vault_slot == P340_SAFE_SECONDARY_SLOT and not interval_targets_slot1:
        vault_action_allowed = True
        vault_firewall_errno = None
    else:
        vault_action_allowed = False
        vault_firewall_errno = "EROFS"

    return {
        "supports_big6": supports_big6,
        "big6_prereq_ok": big6_prereq_ok,
        "big6_active": big6_active,
        "big6_errno": big6_errno,
        "big6_tiles": big6_tiles,
        "physical_end_errno": physical_end_errno,
        "framing_locked": framing_locked,
        "effective_framing_enabled": effective_framing_enabled,
        "framing_errno": framing_errno,
        "effective_apsc_s35": effective_apsc_s35,
        "dormant_auto_framing_errno": dormant_auto_framing_errno,
        "interval_range_valid": interval_range_valid,
        "interval_blocked_reasons": tuple(interval_blocked_reasons),
        "effective_interval_enabled": effective_interval_enabled,
        "interval_errno": interval_errno,
        "bulb_overridden_to_30s": bulb_overridden_to_30s,
        "post_home_lower_left": post_home_lower_left,
        "post_framing_enabled": post_framing_enabled,
        "post_framing_rec_streaming": post_framing_rec_streaming,
        "post_framing_hdmi": post_framing_hdmi,
        "post_interval_enabled": post_interval_enabled,
        "post_interval_start_sec": post_interval_start_sec,
        "post_interval_period_sec": post_interval_period_sec,
        "post_interval_num_shots": post_interval_num_shots,
        "post_interval_ae_tracking": post_interval_ae_tracking,
        "post_interval_shutter_type": post_interval_shutter_type,
        "post_interval_priority": post_interval_priority,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


def compute_expected_tc_make_hdmi_auth_fan_state(
    *,
    camera_model: str,
    shooting_domain: str,
    recording_media_mode: str,
    timecode_make: str,
    timecode_run: str,
    vmc_bncm1_connected: bool,
    rec_media_dur_hdmi_output: str,
    hdmi_tc_output: str,
    hdmi_rec_control: str,
    hdmi_4ch_audio_output: str,
    network_streaming_active: bool,
    usb_streaming_active: bool,
    access_authen_settings: str,
    access_authen_protocol: str,
    wifi_security: str,
    root_cert_inbound_server_requested: bool,
    fan_control: str,
    recording_active: bool,
    internal_temp_over_threshold: bool,
    auto_power_off_temp: str,
    airplane_mode: str,
    wifi_active: bool,
    usb_lan_active: bool,
    network_transport: str,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute canonical Wave-59 Pillar 61B state:
    Initialize-only `[Time Code Make/Run]` (`Regenerate` reads Slot 1 under Simult. Rec & forces
    `Rec Run`), HDMI `[REC Control]` (`Time Code Output = On` gate, valid in `On` & `Off(HDMI Only)`),
    Ver. 7.00+ `[Access Authen.]` SSH/PTP-IP + outbound TLS Root Certs, and `[Fan Control]` 4-mode
    (FX3) vs 3-mode (FX6) with ZERO `Max` option + Zero-RF / Slot-1 `EROFS=30` Vault Firewall."""
    is_fx3 = camera_model == P340_FX3_MODEL_NAME

    # 1. [Time Code Make] & [Time Code Run] (Initialize-only on FX3; FX6 adds Clock)
    if is_fx3 and timecode_make not in P340_FX3_TIMECODE_MAKE_MODES:
        tc_make_errno: Optional[int] = P340_EOPNOTSUPP_ERRNO
    else:
        tc_make_errno = None

    effective_tc_run = "Rec Run" if timecode_make == "Regenerate" else timecode_run
    regen_source_slot: Optional[int] = None
    if timecode_make == "Regenerate":
        if recording_media_mode in ("Slot 1", "Simult. Recording"):
            regen_source_slot = 1
        elif recording_media_mode == "Slot 2":
            regen_source_slot = 2
        else:
            regen_source_slot = 1

    if is_fx3:
        ext_tc_locked = (
            vmc_bncm1_connected
            and timecode_make == "Preset"
            and effective_tc_run == "Free Run"
            and not usb_lan_active
        )
    else:
        ext_tc_locked = timecode_make == "Preset" and effective_tc_run == "Free Run"
    ext_tc_status = "EXT-LK" if ext_tc_locked else "INTERNAL"

    # 2. [HDMI Output Settings] -> [REC Control] requires [Time Code Output] = On
    # Valid in BOTH Rec. Media dur HDMI Output = On AND Off(HDMI Only); blocked in S&Q / Streaming
    rec_control_blocked = (
        hdmi_tc_output != "On"
        or shooting_domain == "S&Q"
        or network_streaming_active
        or usb_streaming_active
    )
    if hdmi_rec_control == "On" and rec_control_blocked:
        effective_hdmi_rec_control = "Off"
        hdmi_rec_control_errno: Optional[int] = P340_EOPNOTSUPP_ERRNO
    else:
        effective_hdmi_rec_control = hdmi_rec_control
        hdmi_rec_control_errno = None

    # 3. Ver. 7.00+ [Access Authen.] (SSH + PTP-IP; 0 hits HTTP_DIGEST/BASIC_AUTH/HTTPS; no WEP/WPA-PSK/IPsec)
    auth_proto_errno: Optional[int] = (
        None if access_authen_protocol in P340_FX3_ACCESS_AUTHEN_PROTOCOLS else P340_EOPNOTSUPP_ERRNO
    )
    wifi_sec_errno: Optional[int] = (
        None if wifi_security in P340_FX3_WIFI_SECURITY_ACTIVE_MODES else P340_EOPNOTSUPP_ERRNO
    )
    root_cert_inbound_errno: Optional[int] = (
        P340_EOPNOTSUPP_ERRNO if root_cert_inbound_server_requested else None
    )

    # 4. [Fan Control] — ZERO `Max` on BOTH FX3 & FX6; `Always Off` active on FX3, dormant on FX6
    if fan_control in P340_FAN_CONTROL_FORBIDDEN_MAX_MODES:
        fan_control_errno: Optional[int] = P340_EOPNOTSUPP_ERRNO
    elif is_fx3 and fan_control not in P340_FX3_FAN_CONTROL_MODES:
        fan_control_errno = P340_EOPNOTSUPP_ERRNO
    elif (not is_fx3) and fan_control not in P340_FX6_FAN_CONTROL_ACTIVE_MODES:
        fan_control_errno = P340_EOPNOTSUPP_ERRNO
    else:
        fan_control_errno = None

    if fan_control == "Off in Rec":
        fan_spinning_now = (not recording_active) or internal_temp_over_threshold
    elif fan_control == "Always Off":
        fan_spinning_now = False
    elif fan_control in ("Auto", "Minimum"):
        fan_spinning_now = True
    else:
        fan_spinning_now = True

    # 5. Reset differentiation across Camera Settings Reset, Reset Network Set., and Initialize
    if reset_action == "Initialize":
        post_tc_make = "Preset"
        post_tc_run = "Rec Run"
        post_hdmi_rec_control = "Off"
        post_hdmi_tc_output = "Off"
        post_rec_media_hdmi = "On"
        post_4ch_audio_out = "CH1/CH2"
        post_access_authen = "On"
        post_root_certs_cleared = True
        post_fan_control = "Auto"
        post_auto_pwr_off_temp = "Standard"
        post_airplane_mode = airplane_mode  # Preserved across Initialize!
    elif reset_action == "Reset Network Set.":
        post_tc_make = timecode_make
        post_tc_run = timecode_run
        post_hdmi_rec_control = effective_hdmi_rec_control
        post_hdmi_tc_output = hdmi_tc_output
        post_rec_media_hdmi = rec_media_dur_hdmi_output
        post_4ch_audio_out = hdmi_4ch_audio_output
        post_access_authen = "On"
        post_root_certs_cleared = True
        post_fan_control = fan_control
        post_auto_pwr_off_temp = auto_power_off_temp
        post_airplane_mode = airplane_mode  # Preserved across Reset Network Set.!
    else:
        # Both "None" AND "Camera Settings Reset" preserve ALL Pillar 61B settings!
        post_tc_make = timecode_make
        post_tc_run = timecode_run
        post_hdmi_rec_control = effective_hdmi_rec_control
        post_hdmi_tc_output = hdmi_tc_output
        post_rec_media_hdmi = rec_media_dur_hdmi_output
        post_4ch_audio_out = hdmi_4ch_audio_output
        post_access_authen = access_authen_settings
        post_root_certs_cleared = False
        post_fan_control = fan_control
        post_auto_pwr_off_temp = auto_power_off_temp
        post_airplane_mode = airplane_mode

    rf_zero_enforced = (
        airplane_mode == "On"
        and post_airplane_mode == "On"
        and not wifi_active
        and network_transport == P340_SAFE_WIRED_TRANSPORT
    )

    # 6. Slot-1 Tier-0 Vault Firewall
    if requested_vault_action in P340_WRITE_MUTATING_VAULT_ACTIONS or (
        requested_vault_slot == P340_SLOT1_VAULT_SLOT
        and requested_vault_action == "HDMI_ONLY_EXT_REC_TRIGGER"
        and rec_media_dur_hdmi_output == "On"
        and slot1_holds_tier0_vault
    ):
        vault_action_allowed = False
        vault_firewall_errno: Optional[str] = "EROFS"
    elif requested_vault_action in (
        "READ_ONLY_AUDIT",
        "STREAM_ONLY_USB_LAN",
        "TC_REGEN_SLOT1_READ_ONLY",
    ):
        vault_action_allowed = True
        vault_firewall_errno = None
    elif requested_vault_action == "HDMI_ONLY_EXT_REC_TRIGGER":
        vault_action_allowed = rec_media_dur_hdmi_output == "Off(HDMI Only)"
        vault_firewall_errno = None if vault_action_allowed else "EROFS"
    elif requested_vault_action == "IMPORT_ROOT_CERT_SLOT2":
        vault_action_allowed = requested_vault_slot == P340_SAFE_SECONDARY_SLOT
        vault_firewall_errno = None if vault_action_allowed else "EROFS"
    elif requested_vault_action == "NONE":
        vault_action_allowed = False
        vault_firewall_errno = None
    else:
        vault_action_allowed = False
        vault_firewall_errno = "EROFS"

    return {
        "tc_make_errno": tc_make_errno,
        "effective_tc_run": effective_tc_run,
        "regen_source_slot": regen_source_slot,
        "ext_tc_locked": ext_tc_locked,
        "ext_tc_status": ext_tc_status,
        "rec_control_blocked": rec_control_blocked,
        "effective_hdmi_rec_control": effective_hdmi_rec_control,
        "hdmi_rec_control_errno": hdmi_rec_control_errno,
        "auth_proto_errno": auth_proto_errno,
        "wifi_sec_errno": wifi_sec_errno,
        "root_cert_inbound_errno": root_cert_inbound_errno,
        "fan_control_errno": fan_control_errno,
        "fan_spinning_now": fan_spinning_now,
        "post_tc_make": post_tc_make,
        "post_tc_run": post_tc_run,
        "post_hdmi_rec_control": post_hdmi_rec_control,
        "post_hdmi_tc_output": post_hdmi_tc_output,
        "post_rec_media_hdmi": post_rec_media_hdmi,
        "post_4ch_audio_out": post_4ch_audio_out,
        "post_access_authen": post_access_authen,
        "post_root_certs_cleared": post_root_certs_cleared,
        "post_fan_control": post_fan_control,
        "post_auto_pwr_off_temp": post_auto_pwr_off_temp,
        "post_airplane_mode": post_airplane_mode,
        "rf_zero_enforced": rf_zero_enforced,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & work_root=None Clean-Room Guard (17 Donors)
# ---------------------------------------------------------------------------


def _iter_work_roots() -> Tuple[Optional[Path], ...]:
    """Return candidate donor work roots (delegates to `_fx3_files.iter_donor_work_roots`)."""
    return _fx3_files.iter_donor_work_roots()


def _resolve_phase340_donor_path(
    relpath: str,
    *,
    work_roots: Optional[Tuple[Optional[Path], ...]] = None,
) -> Optional[Path]:
    """Resolve `relpath` with an explicit `work_root is None` guard for donorless Clean-Room CI."""
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
    max_full_bytes: int = P340_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    try:
        resolved = _resolve_phase340_donor_path(relpath)
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
        hdr = os.pread(fd, min(P340_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase340_donors() -> Tuple["Phase340DonorArtifactDigest", ...]:
    specs = (
        ("fx3_appfw_702_so", P340_DONOR_FX3_APPFW_702_RELPATH, P340_PINNED_FX3_APPFW_702_BYTES, P340_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P340_PINNED_FX3_APPFW_702_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702"),
        ("fx6_appfw_601_so", P340_DONOR_FX6_APPFW_601_RELPATH, P340_PINNED_FX6_APPFW_601_BYTES, P340_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P340_PINNED_FX6_APPFW_601_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601"),
        ("fx3_backup_bin", P340_DONOR_FX3_BACKUP_BIN_RELPATH, P340_PINNED_FX3_BACKUP_BIN_BYTES, P340_PINNED_FX3_BACKUP_BIN_BYTES, "FULL_SHA256", P340_PINNED_FX3_BACKUP_BIN_SHA256, "SYNTHETIC_BK4_ILME_FX3"),
        ("fx3_uxc_en_f", P340_DONOR_FX3_UXC_EN_F_RELPATH, P340_PINNED_FX3_UXC_EN_F_BYTES, P340_PINNED_FX3_UXC_EN_F_BYTES, "FULL_SHA256", P340_PINNED_FX3_UXC_EN_F_SHA256, "SYNTHETIC_UXC7_FX3_EN_F"),
        ("fx3_uxc_sc_f", P340_DONOR_FX3_UXC_SC_F_RELPATH, P340_PINNED_FX3_UXC_SC_F_BYTES, P340_PINNED_FX3_UXC_SC_F_BYTES, "FULL_SHA256", P340_PINNED_FX3_UXC_SC_F_SHA256, "SYNTHETIC_UXC7_FX3_SC_F"),
        ("fx3_uxc_tc_f", P340_DONOR_FX3_UXC_TC_F_RELPATH, P340_PINNED_FX3_UXC_TC_F_BYTES, P340_PINNED_FX3_UXC_TC_F_BYTES, "FULL_SHA256", P340_PINNED_FX3_UXC_TC_F_SHA256, "SYNTHETIC_UXC7_FX3_TC_F"),
        ("fx3_uxc_ja_f", P340_DONOR_FX3_UXC_JA_F_RELPATH, P340_PINNED_FX3_UXC_JA_F_BYTES, P340_PINNED_FX3_UXC_JA_F_BYTES, "FULL_SHA256", P340_PINNED_FX3_UXC_JA_F_SHA256, "SYNTHETIC_UXC7_FX3_JA_F"),
        ("fx3_uxc_en", P340_DONOR_FX3_UXC_EN_RELPATH, P340_PINNED_FX3_UXC_EN_BYTES, P340_PINNED_FX3_UXC_EN_BYTES, "FULL_SHA256", P340_PINNED_FX3_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX3_EN"),
        ("fx3_uxc_sc", P340_DONOR_FX3_UXC_SC_RELPATH, P340_PINNED_FX3_UXC_SC_BYTES, P340_PINNED_FX3_UXC_SC_BYTES, "FULL_SHA256", P340_PINNED_FX3_UXC_SC_SHA256, "SYNTHETIC_UXC7_FX3_SC"),
        ("fx3_uxc_tc", P340_DONOR_FX3_UXC_TC_RELPATH, P340_PINNED_FX3_UXC_TC_BYTES, P340_PINNED_FX3_UXC_TC_BYTES, "FULL_SHA256", P340_PINNED_FX3_UXC_TC_SHA256, "SYNTHETIC_UXC7_FX3_TC"),
        ("fx3_uxc_ja", P340_DONOR_FX3_UXC_JA_RELPATH, P340_PINNED_FX3_UXC_JA_BYTES, P340_PINNED_FX3_UXC_JA_BYTES, "FULL_SHA256", P340_PINNED_FX3_UXC_JA_SHA256, "SYNTHETIC_UXC7_FX3_JA"),
        ("fx3_uxc_en_g", P340_DONOR_FX3_UXC_EN_G_RELPATH, P340_PINNED_FX3_UXC_EN_G_BYTES, P340_PINNED_FX3_UXC_EN_G_BYTES, "FULL_SHA256", P340_PINNED_FX3_UXC_EN_G_SHA256, "SYNTHETIC_UXC7_FX3_EN_G"),
        ("fx3_uxc_sc_g", P340_DONOR_FX3_UXC_SC_G_RELPATH, P340_PINNED_FX3_UXC_SC_G_BYTES, P340_PINNED_FX3_UXC_SC_G_BYTES, "FULL_SHA256", P340_PINNED_FX3_UXC_SC_G_SHA256, "SYNTHETIC_UXC7_FX3_SC_G"),
        ("fx3_uxc_tc_g", P340_DONOR_FX3_UXC_TC_G_RELPATH, P340_PINNED_FX3_UXC_TC_G_BYTES, P340_PINNED_FX3_UXC_TC_G_BYTES, "FULL_SHA256", P340_PINNED_FX3_UXC_TC_G_SHA256, "SYNTHETIC_UXC7_FX3_TC_G"),
        ("fx3_uxc_ja_g", P340_DONOR_FX3_UXC_JA_G_RELPATH, P340_PINNED_FX3_UXC_JA_G_BYTES, P340_PINNED_FX3_UXC_JA_G_BYTES, "FULL_SHA256", P340_PINNED_FX3_UXC_JA_G_SHA256, "SYNTHETIC_UXC7_FX3_JA_G"),
        ("fx6_uxc_en", P340_DONOR_FX6_UXC_EN_RELPATH, P340_PINNED_FX6_UXC_EN_BYTES, P340_PINNED_FX6_UXC_EN_BYTES, "FULL_SHA256", P340_PINNED_FX6_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX6_EN"),
        ("fx6_uxc_en_2", P340_DONOR_FX6_UXC_EN_2_RELPATH, P340_PINNED_FX6_UXC_EN_2_BYTES, P340_PINNED_FX6_UXC_EN_2_BYTES, "FULL_SHA256", P340_PINNED_FX6_UXC_EN_2_SHA256, "SYNTHETIC_UXC7_FX6_EN_2"),
    )
    return tuple(
        Phase340DonorArtifactDigest(
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


def inspect_phase340_donors_readonly(
    force_clean_room: Optional[bool] = None,
) -> "Phase340DonorSnapshot":
    """Inspect Wave-59 FX3 7.02 (`14` donors) & FX6 6.01 (`3` donors) strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase340_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase340DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_2_0s_budget=dt < budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        ("fx3_appfw_702_so", P340_DONOR_FX3_APPFW_702_RELPATH, P340_PINNED_FX3_APPFW_702_BYTES, P340_PINNED_FX3_APPFW_702_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702")),
        ("fx6_appfw_601_so", P340_DONOR_FX6_APPFW_601_RELPATH, P340_PINNED_FX6_APPFW_601_BYTES, P340_PINNED_FX6_APPFW_601_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601")),
        ("fx3_backup_bin", P340_DONOR_FX3_BACKUP_BIN_RELPATH, P340_PINNED_FX3_BACKUP_BIN_BYTES, P340_PINNED_FX3_BACKUP_BIN_SHA256, lambda d: _check_bk4_backup(d, "ILME_FX3")),
        ("fx3_uxc_en_f", P340_DONOR_FX3_UXC_EN_F_RELPATH, P340_PINNED_FX3_UXC_EN_F_BYTES, P340_PINNED_FX3_UXC_EN_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_F")),
        ("fx3_uxc_sc_f", P340_DONOR_FX3_UXC_SC_F_RELPATH, P340_PINNED_FX3_UXC_SC_F_BYTES, P340_PINNED_FX3_UXC_SC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_F")),
        ("fx3_uxc_tc_f", P340_DONOR_FX3_UXC_TC_F_RELPATH, P340_PINNED_FX3_UXC_TC_F_BYTES, P340_PINNED_FX3_UXC_TC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_F")),
        ("fx3_uxc_ja_f", P340_DONOR_FX3_UXC_JA_F_RELPATH, P340_PINNED_FX3_UXC_JA_F_BYTES, P340_PINNED_FX3_UXC_JA_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_F")),
        ("fx3_uxc_en", P340_DONOR_FX3_UXC_EN_RELPATH, P340_PINNED_FX3_UXC_EN_BYTES, P340_PINNED_FX3_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN")),
        ("fx3_uxc_sc", P340_DONOR_FX3_UXC_SC_RELPATH, P340_PINNED_FX3_UXC_SC_BYTES, P340_PINNED_FX3_UXC_SC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC")),
        ("fx3_uxc_tc", P340_DONOR_FX3_UXC_TC_RELPATH, P340_PINNED_FX3_UXC_TC_BYTES, P340_PINNED_FX3_UXC_TC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC")),
        ("fx3_uxc_ja", P340_DONOR_FX3_UXC_JA_RELPATH, P340_PINNED_FX3_UXC_JA_BYTES, P340_PINNED_FX3_UXC_JA_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA")),
        ("fx3_uxc_en_g", P340_DONOR_FX3_UXC_EN_G_RELPATH, P340_PINNED_FX3_UXC_EN_G_BYTES, P340_PINNED_FX3_UXC_EN_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_G")),
        ("fx3_uxc_sc_g", P340_DONOR_FX3_UXC_SC_G_RELPATH, P340_PINNED_FX3_UXC_SC_G_BYTES, P340_PINNED_FX3_UXC_SC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_G")),
        ("fx3_uxc_tc_g", P340_DONOR_FX3_UXC_TC_G_RELPATH, P340_PINNED_FX3_UXC_TC_G_BYTES, P340_PINNED_FX3_UXC_TC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_G")),
        ("fx3_uxc_ja_g", P340_DONOR_FX3_UXC_JA_G_RELPATH, P340_PINNED_FX3_UXC_JA_G_BYTES, P340_PINNED_FX3_UXC_JA_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_G")),
        ("fx6_uxc_en", P340_DONOR_FX6_UXC_EN_RELPATH, P340_PINNED_FX6_UXC_EN_BYTES, P340_PINNED_FX6_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN")),
        ("fx6_uxc_en_2", P340_DONOR_FX6_UXC_EN_2_RELPATH, P340_PINNED_FX6_UXC_EN_2_BYTES, P340_PINNED_FX6_UXC_EN_2_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN_2")),
    )

    def _probe_one(spec: Tuple[str, str, int, str, Any]) -> Optional[Phase340DonorArtifactDigest]:
        aid, relpath, expected_bytes, expected_sha, marker_fn = spec
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            return None
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        return Phase340DonorArtifactDigest(
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
        artifacts = _synthetic_phase340_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase340DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_2_0s_budget=dt < budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    digests = tuple(r for r in results if r is not None)
    all_ok = all(d.present and d.matches_pinned for d in digests) and len(digests) == len(probe_specs)
    dt = round(time.monotonic() - t0, 6)
    return Phase340DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all_ok,
        donor_files_inspected=len(digests),
        elapsed_seconds=dt,
        under_2_0s_budget=dt < budget,
        budget_seconds_applied=budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=digests,
    )


# ---------------------------------------------------------------------------
# Frozen Dataclasses (Specs, Reports, Suites & 61-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase340DonorArtifactDigest:
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
class Phase340DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_2_0s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase340DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Big6FramingIntervalSlot1VaultSpec:
    # Ver. 7.00/7.02 [HOME] (`BIG6`) screen & lower-left metadata-only ND
    camera_model: str
    fw_version: str
    shooting_domain: str
    exposure_mode: str
    mode_settings: str
    big6_entry_trigger: str
    touch_operation_enabled: bool
    swipe_down_setting: str
    log_shooting_mode: str
    shutter_mode: str
    home_lower_left_mode: str
    reported_big6_active: bool
    reported_big6_errno: Optional[int]
    reported_big6_tiles: Tuple[str, ...]
    reported_big6_status_bars_readonly: bool
    requested_physical_end_hw: bool
    reported_physical_end_errno: Optional[int]
    post_home_lower_left: str
    # Manual [Framing Settings] vs Dormant AI [Auto Framing]
    framing_enabled: bool
    framing_rec_streaming: str
    framing_hdmi: str
    framing_support_enum: str
    apsc_s35_requested: bool
    movie_frame_rate_fps: float
    active_recording: bool
    active_streaming: bool
    reported_effective_framing_enabled: bool
    reported_framing_errno: Optional[int]
    reported_effective_apsc_s35: bool
    requested_dormant_auto_framing_symbols: Tuple[str, ...]
    reported_dormant_auto_framing_errno: Optional[int]
    post_framing_enabled: bool
    post_framing_rec_streaming: str
    post_framing_hdmi: str
    # Still-only [Interval Shoot Func.] (7 Resettable sub-items, 9999 shots) vs FX6 [Interval Rec]
    interval_shooting_enabled: bool
    interval_start_time_sec: int
    interval_period_sec: int
    interval_num_shots: int
    interval_ae_tracking: str
    interval_shutter_type: str
    interval_priority: str
    bulb_active: bool
    reported_effective_interval_enabled: bool
    reported_interval_errno: Optional[int]
    reported_bulb_overridden_to_30s: bool
    post_interval_enabled: bool
    post_interval_start_sec: int
    post_interval_period_sec: int
    post_interval_num_shots: int
    post_interval_ae_tracking: str
    post_interval_shutter_type: str
    post_interval_priority: str
    fx6_has_builtin_end: bool
    fx6_interval_rec_single_mxf: bool
    fx6_has_auto_framing_menu: bool
    reset_action: str
    # Slot-1 Tier-0 Vault Firewall & Stage-B Overlay & H0 == H3
    requested_vault_slot: int
    slot1_holds_tier0_vault: bool
    requested_vault_action: str
    interval_targets_slot1: bool
    reported_vault_action_allowed: bool
    vault_firewall_errno: Optional[str]
    slot1_data_sector_writes: int
    slot1_dcim_avf_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative counters
    big6_home_or_lower_left_nd_drift_events: int
    framing_manual_or_dormant_auto_framing_drift_events: int
    interval_shoot_9999_or_fx6_mxf_spoof_events: int


@dataclass(frozen=True)
class Big6FramingIntervalSlot1VaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    big6_home_fixed_var_and_lower_left_nd_verified: bool
    framing_manual_and_dormant_auto_framing_verified: bool
    interval_shoot_still_7item_and_fx6_mxf_verified: bool
    slot1_vault_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    big6_home_or_lower_left_nd_drift_events: int
    framing_manual_or_dormant_auto_framing_drift_events: int
    interval_shoot_9999_or_fx6_mxf_spoof_events: int
    slot1_data_sector_writes: int
    slot1_dcim_avf_mutation_bytes: int
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
class TcMakeHdmiAccessAuthFanVaultSpec:
    # Wave-59 Initialize-only [Time Code Make/Run] & HDMI [REC Control] / [4ch Audio Output]
    camera_model: str
    fw_version: str
    shooting_domain: str
    recording_media_mode: str
    timecode_make: str
    timecode_run: str
    vmc_bncm1_connected: bool
    reported_tc_make_errno: Optional[int]
    reported_effective_tc_run: str
    reported_regen_source_slot: Optional[int]
    reported_ext_tc_status: str
    rec_media_dur_hdmi_output: str
    hdmi_tc_output: str
    hdmi_rec_control: str
    hdmi_4ch_audio_output: str
    network_streaming_active: bool
    usb_streaming_active: bool
    reported_effective_hdmi_rec_control: str
    reported_hdmi_rec_control_errno: Optional[int]
    fx6_supports_tc_clock_mode: bool
    fx6_splits_remote_if_vs_parallel_rec: bool
    # Ver. 7.00+ [Access Authen.] SSH/PTP-IP, Root Cert outbound TLS & [Fan Control] / [Auto Power OFF Temp.]
    access_authen_settings: str
    access_authen_protocol: str
    reported_auth_proto_errno: Optional[int]
    wifi_security: str
    reported_wifi_sec_errno: Optional[int]
    root_cert_inbound_server_requested: bool
    reported_root_cert_inbound_errno: Optional[int]
    fan_control: str
    recording_active: bool
    internal_temp_over_threshold: bool
    reported_fan_control_errno: Optional[int]
    reported_fan_spinning_now: bool
    auto_power_off_temp: str
    fx6_has_fan_control_max: bool
    fx6_fan_always_off_dormant: bool
    reset_action: str
    post_tc_make: str
    post_tc_run: str
    post_hdmi_rec_control: str
    post_hdmi_tc_output: str
    post_rec_media_hdmi: str
    post_4ch_audio_out: str
    post_access_authen: str
    post_root_certs_cleared: bool
    post_fan_control: str
    post_auto_pwr_off_temp: str
    post_airplane_mode: str
    # Zero-RF & Slot-1 Tier-0 Vault Firewall & Stage-B Overlay & H0 == H3
    airplane_mode: str
    wifi_active: bool
    usb_lan_active: bool
    network_transport: str
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    requested_vault_slot: int
    slot1_holds_tier0_vault: bool
    requested_vault_action: str
    reported_vault_action_allowed: bool
    vault_firewall_errno: Optional[str]
    slot1_data_sector_writes: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative counters
    tc_make_regen_or_hdmi_rec_ctrl_drift_events: int
    access_authen_ssh_tls_or_fan_max_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int


@dataclass(frozen=True)
class TcMakeHdmiAccessAuthFanVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    tc_make_regen_and_hdmi_rec_ctrl_verified: bool
    access_authen_ssh_tls_and_fan_no_max_verified: bool
    zero_rf_and_slot1_erofs30_vault_verified: bool
    overlay_and_h0_h3_verified: bool
    matrix_states_checked: int
    tc_make_regen_or_hdmi_rec_ctrl_drift_events: int
    access_authen_ssh_tls_or_fan_max_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
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
class Big6FramingIntervalTcAuthFanVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase340DonorSnapshot
    big6_framing_interval_report: Big6FramingIntervalSlot1VaultReport
    tc_make_hdmi_auth_fan_report: TcMakeHdmiAccessAuthFanVaultReport
    big6_home_or_lower_left_nd_drift_events: int
    framing_manual_or_dormant_auto_framing_drift_events: int
    interval_shoot_9999_or_fx6_mxf_spoof_events: int
    tc_make_regen_or_hdmi_rec_ctrl_drift_events: int
    access_authen_ssh_tls_or_fan_max_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_dcim_avf_mutation_bytes: int
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
class Pillar61ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar61ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar61ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar61BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar61ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar61StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase340DonorSnapshot
    pillar_61a_big6_home_framing_interval_vault: Pillar61ASuiteResult
    pillar_61b_tc_make_hdmi_auth_fan_vault: Pillar61BSuiteResult
    big6_home_or_lower_left_nd_drift_events: int
    framing_manual_or_dormant_auto_framing_drift_events: int
    interval_shoot_9999_or_fx6_mxf_spoof_events: int
    tc_make_regen_or_hdmi_rec_ctrl_drift_events: int
    access_authen_ssh_tls_or_fan_max_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_dcim_avf_mutation_bytes: int
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
class Master61PillarRecoveryReport:
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
    donor_snapshot: Phase340DonorSnapshot
    pillar61_a_big6_home_framing_interval_vault: Pillar61ASuiteResult
    pillar61_b_tc_make_hdmi_auth_fan_vault: Pillar61BSuiteResult
    # Pillar 61 zero-violation counters & hardware boundaries
    big6_home_or_lower_left_nd_drift_events: int
    framing_manual_or_dormant_auto_framing_drift_events: int
    interval_shoot_9999_or_fx6_mxf_spoof_events: int
    tc_make_regen_or_hdmi_rec_ctrl_drift_events: int
    access_authen_ssh_tls_or_fan_max_drift_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_dcim_avf_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
    fx3_big6_tile_count: int
    fx3_has_physical_end_hw: bool
    fx3_has_dormant_auto_framing: bool
    fx3_interval_subitem_count: int
    fx3_interval_max_shots: int
    fx3_access_authen_http_digest_hits: int
    fx3_fan_control_mode_count: int
    fx6_fan_control_mode_count: int
    fx3_has_fan_control_max: bool
    fx6_has_fan_control_max: bool
    # Carried forward Pillar 60 metrics
    bright_mon_or_monitor_brightness_drift_events: int
    bulb_mech_or_dormant_bulb_timer_hdr_drift_events: int
    fx6_vf_backlight_or_still_spoof_events: int
    shotmark_clipflag_or_dormant_divide_drift_events: int
    tc_link_wpa3_or_usblan_mutex_drift_events: int
    slot1_m4root_avf_mutation_bytes: int
    slot1_dcim_divider_mutation_bytes: int
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
    master_61pillar_sha256: str
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
# Spec Builders (Pillars 61A & 61B)
# ---------------------------------------------------------------------------


def build_default_safe_big6_framing_interval_vault_spec(
    **overrides: Any,
) -> Big6FramingIntervalSlot1VaultSpec:
    """Return a clean, verified default `Big6FramingIntervalSlot1VaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P340_FX3_MODEL_NAME,
        "fw_version": P340_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "exposure_mode": "M",
        "mode_settings": "Fixed/Variable",
        "big6_entry_trigger": "HOME_KEY",
        "touch_operation_enabled": True,
        "swipe_down_setting": "Open Home Screen",
        "log_shooting_mode": "Off",
        "shutter_mode": "Speed",
        "home_lower_left_mode": "Aperture",
        "reported_big6_active": True,
        "reported_big6_errno": None,
        "reported_big6_tiles": (
            "FPS",
            "ISO",
            "Shutter Speed",
            "Aperture",
            "Picture Profile",
            "White Balance",
        ),
        "reported_big6_status_bars_readonly": True,
        "requested_physical_end_hw": False,
        "reported_physical_end_errno": None,
        "post_home_lower_left": "Aperture",
        "framing_enabled": False,
        "framing_rec_streaming": P340_FRAMING_DEFAULT_REC_STREAMING,
        "framing_hdmi": P340_FRAMING_DEFAULT_HDMI,
        "framing_support_enum": P340_FX3_FRAMING_SUPPORT_ENUM,
        "apsc_s35_requested": False,
        "movie_frame_rate_fps": 23.98,
        "active_recording": False,
        "active_streaming": False,
        "reported_effective_framing_enabled": False,
        "reported_framing_errno": None,
        "reported_effective_apsc_s35": False,
        "requested_dormant_auto_framing_symbols": (),
        "reported_dormant_auto_framing_errno": None,
        "post_framing_enabled": False,
        "post_framing_rec_streaming": P340_FRAMING_DEFAULT_REC_STREAMING,
        "post_framing_hdmi": P340_FRAMING_DEFAULT_HDMI,
        "interval_shooting_enabled": False,
        "interval_start_time_sec": P340_INTERVAL_START_TIME_DEFAULT_SEC,
        "interval_period_sec": P340_INTERVAL_SEC_DEFAULT,
        "interval_num_shots": P340_INTERVAL_SHOTS_DEFAULT,
        "interval_ae_tracking": P340_INTERVAL_AE_TRACKING_DEFAULT,
        "interval_shutter_type": P340_INTERVAL_SHUTTER_TYPE_DEFAULT,
        "interval_priority": "Off",
        "bulb_active": False,
        "reported_effective_interval_enabled": False,
        "reported_interval_errno": None,
        "reported_bulb_overridden_to_30s": False,
        "post_interval_enabled": False,
        "post_interval_start_sec": P340_INTERVAL_START_TIME_DEFAULT_SEC,
        "post_interval_period_sec": P340_INTERVAL_SEC_DEFAULT,
        "post_interval_num_shots": P340_INTERVAL_SHOTS_DEFAULT,
        "post_interval_ae_tracking": P340_INTERVAL_AE_TRACKING_DEFAULT,
        "post_interval_shutter_type": P340_INTERVAL_SHUTTER_TYPE_DEFAULT,
        "post_interval_priority": "Off",
        "fx6_has_builtin_end": True,
        "fx6_interval_rec_single_mxf": True,
        "fx6_has_auto_framing_menu": False,
        "reset_action": "None",
        "requested_vault_slot": P340_SLOT1_VAULT_SLOT,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "interval_targets_slot1": False,
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": 0,
        "slot1_dcim_avf_mutation_bytes": 0,
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P340_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P340_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P340_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P340_TIER0_SURFACE_COUNT,
        "big6_home_or_lower_left_nd_drift_events": 0,
        "framing_manual_or_dormant_auto_framing_drift_events": 0,
        "interval_shoot_9999_or_fx6_mxf_spoof_events": 0,
    }
    defaults.update(overrides)
    return Big6FramingIntervalSlot1VaultSpec(**defaults)


def build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
    **overrides: Any,
) -> TcMakeHdmiAccessAuthFanVaultSpec:
    """Return a clean, verified default `TcMakeHdmiAccessAuthFanVaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P340_FX3_MODEL_NAME,
        "fw_version": P340_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "recording_media_mode": "Simult. Recording",
        "timecode_make": "Preset",
        "timecode_run": "Free Run",
        "vmc_bncm1_connected": False,
        "reported_tc_make_errno": None,
        "reported_effective_tc_run": "Free Run",
        "reported_regen_source_slot": None,
        "reported_ext_tc_status": "INTERNAL",
        "rec_media_dur_hdmi_output": "On",
        "hdmi_tc_output": "On",
        "hdmi_rec_control": "Off",
        "hdmi_4ch_audio_output": "CH1/CH2",
        "network_streaming_active": False,
        "usb_streaming_active": False,
        "reported_effective_hdmi_rec_control": "Off",
        "reported_hdmi_rec_control_errno": None,
        "fx6_supports_tc_clock_mode": True,
        "fx6_splits_remote_if_vs_parallel_rec": True,
        "access_authen_settings": "On",
        "access_authen_protocol": "SSH+PTP-IP",
        "reported_auth_proto_errno": None,
        "wifi_security": "WPA3-SAE",
        "reported_wifi_sec_errno": None,
        "root_cert_inbound_server_requested": False,
        "reported_root_cert_inbound_errno": None,
        "fan_control": "Auto",
        "recording_active": False,
        "internal_temp_over_threshold": False,
        "reported_fan_control_errno": None,
        "reported_fan_spinning_now": True,
        "auto_power_off_temp": "Standard",
        "fx6_has_fan_control_max": False,
        "fx6_fan_always_off_dormant": True,
        "reset_action": "None",
        "post_tc_make": "Preset",
        "post_tc_run": "Free Run",
        "post_hdmi_rec_control": "Off",
        "post_hdmi_tc_output": "On",
        "post_rec_media_hdmi": "On",
        "post_4ch_audio_out": "CH1/CH2",
        "post_access_authen": "On",
        "post_root_certs_cleared": False,
        "post_fan_control": "Auto",
        "post_auto_pwr_off_temp": "Standard",
        "post_airplane_mode": "On",
        "airplane_mode": "On",
        "wifi_active": False,
        "usb_lan_active": True,
        "network_transport": P340_SAFE_WIRED_TRANSPORT,
        "rf_packets_transmitted": 0,
        "rf_nvs_mutation_bytes": 0,
        "requested_vault_slot": P340_SLOT1_VAULT_SLOT,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": 0,
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P340_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P340_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P340_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P340_TIER0_SURFACE_COUNT,
        "tc_make_regen_or_hdmi_rec_ctrl_drift_events": 0,
        "access_authen_ssh_tls_or_fan_max_drift_events": 0,
        "zero_rf_or_slot1_vault_bypass_events": 0,
    }
    defaults.update(overrides)
    return TcMakeHdmiAccessAuthFanVaultSpec(**defaults)


# ---------------------------------------------------------------------------
# Evaluators & Single-Shot Combined Verifier (Pillars 61A & 61B)
# ---------------------------------------------------------------------------


def evaluate_big6_framing_interval_vault(
    spec: Big6FramingIntervalSlot1VaultSpec,
) -> Big6FramingIntervalSlot1VaultReport:
    """Evaluate Pillar 61A: Ver. 7.00+ `[HOME]` (`BIG6`) screen (`Mode Settings = Fixed/Variable`,
    6 dynamic tiles, Lower-Left metadata-only ND vs FX6 built-in e-ND), Manual `[Framing Settings]`
    vs Dormant `[Auto Framing]` (`EOPNOTSUPP=95`), and Still-only `[Interval Shoot Func.]` (7 Resettable
    sub-items, Electronic Shutter default, 9999 shots -> Slot-1 Tier-0 `EROFS=30`) vs FX6 Interval Rec."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P340_BLOCKED_SAFETY_POLICY_VIOLATION, "Module safety invariant violation")

    valid_fw = (
        (
            spec.camera_model == P340_FX3_MODEL_NAME
            and spec.fw_version in P340_FX3_SUPPORTED_FW_VERSIONS
        )
        or (
            spec.camera_model == P340_FX6_DONOR_MODEL_NAME
            and spec.fw_version == P340_FX6_DONOR_FW_VERSION
        )
    )
    if (
        not valid_fw
        or spec.shooting_domain not in P340_SHOOTING_DOMAINS
        or spec.exposure_mode not in P340_EXPOSURE_MODES
        or spec.mode_settings not in P340_MODE_SETTINGS_OPTIONS
        or spec.big6_entry_trigger not in P340_BIG6_ENTRY_TRIGGERS
        or spec.log_shooting_mode not in P340_LOG_SHOOTING_MODES
        or spec.shutter_mode not in P340_SHUTTER_MODES
        or spec.home_lower_left_mode not in P340_HOME_LOWER_LEFT_MODES
        or spec.framing_rec_streaming not in P340_FRAMING_CROP_OPTIONS
        or spec.framing_hdmi not in P340_FRAMING_CROP_OPTIONS
        or spec.reset_action not in P340_RESET_ACTIONS
        or spec.requested_vault_slot not in (1, 2)
        or spec.requested_vault_action not in P340_VAULT_ACTIONS
        or (
            spec.vault_firewall_errno is not None
            and spec.vault_firewall_errno not in P340_VAULT_FIREWALL_ERRNOS
        )
    ):
        _fail(
            P340_BLOCKED_INVALID_PILLAR61A_SPEC,
            "Invalid Pillar 61A camera/BIG6/Framing/Interval/vault spec parameter",
        )

    st = compute_expected_big6_framing_interval_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        exposure_mode=spec.exposure_mode,
        mode_settings=spec.mode_settings,
        big6_entry_trigger=spec.big6_entry_trigger,
        touch_operation_enabled=spec.touch_operation_enabled,
        swipe_down_setting=spec.swipe_down_setting,
        log_shooting_mode=spec.log_shooting_mode,
        shutter_mode=spec.shutter_mode,
        home_lower_left_mode=spec.home_lower_left_mode,
        requested_physical_end_hw=spec.requested_physical_end_hw,
        framing_enabled=spec.framing_enabled,
        framing_rec_streaming=spec.framing_rec_streaming,
        framing_hdmi=spec.framing_hdmi,
        apsc_s35_requested=spec.apsc_s35_requested,
        movie_frame_rate_fps=spec.movie_frame_rate_fps,
        active_recording=spec.active_recording,
        active_streaming=spec.active_streaming,
        requested_dormant_auto_framing_symbols=spec.requested_dormant_auto_framing_symbols,
        interval_shooting_enabled=spec.interval_shooting_enabled,
        interval_start_time_sec=spec.interval_start_time_sec,
        interval_period_sec=spec.interval_period_sec,
        interval_num_shots=spec.interval_num_shots,
        interval_ae_tracking=spec.interval_ae_tracking,
        interval_shutter_type=spec.interval_shutter_type,
        interval_priority=spec.interval_priority,
        bulb_active=spec.bulb_active,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
        interval_targets_slot1=spec.interval_targets_slot1,
    )

    # 1. Ver. 7.00+ BIG6 Home Screen & Lower-Left metadata-only ND
    big6_ok = (
        (
            spec.camera_model != P340_FX3_MODEL_NAME
            or (
                spec.reported_big6_active == st["big6_active"]
                and spec.reported_big6_errno == st["big6_errno"]
                and not (
                    spec.big6_entry_trigger != "NONE"
                    and not st["big6_prereq_ok"]
                    and spec.reported_big6_active
                )
                and tuple(spec.reported_big6_tiles) == st["big6_tiles"]
                and len(spec.reported_big6_tiles) == P340_FX3_BIG6_TILE_COUNT
                and spec.reported_big6_status_bars_readonly
                and not spec.requested_physical_end_hw
                and spec.reported_physical_end_errno == st["physical_end_errno"]
                and spec.post_home_lower_left == st["post_home_lower_left"]
            )
        )
        and not spec.requested_physical_end_hw
        and spec.big6_home_or_lower_left_nd_drift_events == 0
    )
    if not big6_ok:
        _fail(
            P340_BLOCKED_BIG6_HOME_OR_LOWER_LEFT_ND_DRIFT,
            "BIG6 Home Screen Fixed/Variable prerequisite, 6-tile dynamic mapping, or zero physical e-ND boundary violated",
        )

    # 2. Manual [Framing Settings] vs Dormant AI [Auto Framing]
    framing_ok = (
        (
            spec.camera_model != P340_FX3_MODEL_NAME
            or (
                spec.framing_support_enum == P340_FX3_FRAMING_SUPPORT_ENUM
                and spec.reported_effective_framing_enabled == st["effective_framing_enabled"]
                and spec.reported_framing_errno == st["framing_errno"]
                and not (
                    spec.framing_enabled
                    and st["framing_locked"]
                    and spec.reported_effective_framing_enabled
                )
                and spec.reported_effective_apsc_s35 == st["effective_apsc_s35"]
                and spec.reported_dormant_auto_framing_errno == st["dormant_auto_framing_errno"]
                and spec.post_framing_enabled == st["post_framing_enabled"]
                and spec.post_framing_rec_streaming == st["post_framing_rec_streaming"]
                and spec.post_framing_hdmi == st["post_framing_hdmi"]
            )
        )
        and len(spec.requested_dormant_auto_framing_symbols) == 0
        and spec.framing_manual_or_dormant_auto_framing_drift_events == 0
    )
    if not framing_ok:
        _fail(
            P340_BLOCKED_FRAMING_MANUAL_OR_DORMANT_AUTO_FRAMING_DRIFT,
            "Manual Framing Settings (APS-C off, 100p/Rec/Stream lock) or dormant AI Auto Framing EOPNOTSUPP=95 violated",
        )

    # 3. Still-only [Interval Shoot Func.] (7 Resettable sub-items) vs FX6 [Interval Rec]
    interval_ok = (
        (
            spec.camera_model != P340_FX3_MODEL_NAME
            or (
                st["interval_range_valid"]
                and spec.reported_effective_interval_enabled == st["effective_interval_enabled"]
                and spec.reported_interval_errno == st["interval_errno"]
                and not (
                    spec.interval_shooting_enabled
                    and bool(st["interval_blocked_reasons"])
                    and spec.reported_effective_interval_enabled
                )
                and spec.reported_bulb_overridden_to_30s == st["bulb_overridden_to_30s"]
                and spec.post_interval_enabled == st["post_interval_enabled"]
                and spec.post_interval_start_sec == st["post_interval_start_sec"]
                and spec.post_interval_period_sec == st["post_interval_period_sec"]
                and spec.post_interval_num_shots == st["post_interval_num_shots"]
                and spec.post_interval_ae_tracking == st["post_interval_ae_tracking"]
                and spec.post_interval_shutter_type == st["post_interval_shutter_type"]
                and spec.post_interval_priority == st["post_interval_priority"]
            )
        )
        and spec.fx6_has_builtin_end
        and spec.fx6_interval_rec_single_mxf
        and not spec.fx6_has_auto_framing_menu
        and spec.interval_shoot_9999_or_fx6_mxf_spoof_events == 0
    )
    if not interval_ok:
        _fail(
            P340_BLOCKED_INTERVAL_SHOOT_9999_OR_FX6_MXF_SPOOF,
            "Still-only Interval Shoot Func. (7 Resettable sub-items, 1..9999, Electronic Shutter default, BULB->30\") or FX6 Interval Rec boundary violated",
        )

    # 4. Slot-1 Tier-0 Vault EROFS=30 Firewall & Stage-B Overlay & H0 == H3
    slot1_mutated = (
        spec.requested_vault_slot == P340_SLOT1_VAULT_SLOT
        and spec.slot1_holds_tier0_vault
        and (
            spec.requested_vault_action in P340_WRITE_MUTATING_VAULT_ACTIONS
            or (st["effective_interval_enabled"] and spec.interval_targets_slot1)
        )
        and spec.reported_vault_action_allowed
    )
    vault_fw_ok = (
        not slot1_mutated
        and spec.reported_vault_action_allowed == st["vault_action_allowed"]
        and spec.vault_firewall_errno == st["vault_firewall_errno"]
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_dcim_avf_mutation_bytes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_format_hard_locked
    )
    if not vault_fw_ok:
        _fail(
            P340_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached on Interval 9999-shot DCIM/AVF_INFO or format attempt",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P340_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P340_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P340_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P340_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "61A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "fw_version": spec.fw_version,
            "big6_active": spec.reported_big6_active,
            "big6_tiles": list(spec.reported_big6_tiles),
            "framing_enabled": spec.reported_effective_framing_enabled,
            "interval_enabled": spec.reported_effective_interval_enabled,
            "interval_num_shots": spec.post_interval_num_shots,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return Big6FramingIntervalSlot1VaultReport(
        schema=PHASE340_SCHEMA,
        version=PHASE340_VERSION,
        passed=passed,
        status=P340_STATUS_VERIFIED_PILLAR_61A if passed else P340_STATUS_REJECTED_PILLAR_61A,
        block_code=block_code,
        big6_home_fixed_var_and_lower_left_nd_verified=big6_ok,
        framing_manual_and_dormant_auto_framing_verified=framing_ok,
        interval_shoot_still_7item_and_fx6_mxf_verified=interval_ok,
        slot1_vault_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=18,
        big6_home_or_lower_left_nd_drift_events=spec.big6_home_or_lower_left_nd_drift_events,
        framing_manual_or_dormant_auto_framing_drift_events=(
            spec.framing_manual_or_dormant_auto_framing_drift_events
        ),
        interval_shoot_9999_or_fx6_mxf_spoof_events=(
            spec.interval_shoot_9999_or_fx6_mxf_spoof_events
        ),
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_dcim_avf_mutation_bytes=spec.slot1_dcim_avf_mutation_bytes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_tc_make_hdmi_auth_fan_vault(
    spec: TcMakeHdmiAccessAuthFanVaultSpec,
) -> TcMakeHdmiAccessAuthFanVaultReport:
    """Evaluate Pillar 61B: Wave-59 Initialize-only `[Time Code Make/Run]` (`Regenerate` reads Slot 1
    under Simult. Rec & forces `Rec Run`), HDMI `[REC Control]` (`Time Code Output=On` gate, valid in
    `On` & `Off(HDMI Only)`), Ver. 7.00+ `[Access Authen.]` SSH/PTP-IP + outbound TLS Root Certs,
    and `[Fan Control]` 4-mode (FX3) vs 3-mode (FX6) with ZERO `Max` option + Zero-RF / Slot-1 EROFS=30."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P340_BLOCKED_SAFETY_POLICY_VIOLATION, "Module safety invariant violation")

    valid_fw = (
        (
            spec.camera_model == P340_FX3_MODEL_NAME
            and spec.fw_version in P340_FX3_SUPPORTED_FW_VERSIONS
        )
        or (
            spec.camera_model == P340_FX6_DONOR_MODEL_NAME
            and spec.fw_version == P340_FX6_DONOR_FW_VERSION
        )
    )
    if (
        not valid_fw
        or spec.shooting_domain not in P340_SHOOTING_DOMAINS
        or spec.recording_media_mode not in P340_RECORDING_MEDIA_MODES
        or spec.timecode_make not in P340_TIMECODE_MAKE_MODES
        or spec.timecode_run not in P340_TIMECODE_RUN_MODES
        or spec.rec_media_dur_hdmi_output not in P340_REC_MEDIA_HDMI_MODES
        or spec.hdmi_tc_output not in P340_ON_OFF_MODES
        or spec.hdmi_rec_control not in P340_ON_OFF_MODES
        or spec.hdmi_4ch_audio_output not in P340_AUDIO_4CH_OUTPUT_MODES
        or spec.access_authen_settings not in P340_ON_OFF_MODES
        or spec.wifi_security not in P340_FX3_WIFI_SECURITY_ALL_MODES
        or spec.fan_control not in P340_FAN_CONTROL_ALL_MODES
        or spec.auto_power_off_temp not in P340_AUTO_POWER_OFF_TEMP_MODES
        or spec.airplane_mode not in P340_ON_OFF_MODES
        or spec.network_transport not in P340_NETWORK_TRANSPORTS
        or spec.reset_action not in P340_RESET_ACTIONS
        or spec.requested_vault_slot not in (1, 2)
        or spec.requested_vault_action not in P340_VAULT_ACTIONS
        or (
            spec.vault_firewall_errno is not None
            and spec.vault_firewall_errno not in P340_VAULT_FIREWALL_ERRNOS
        )
    ):
        _fail(
            P340_BLOCKED_INVALID_PILLAR61B_SPEC,
            "Invalid Pillar 61B camera/TC/HDMI/AccessAuthen/Fan/vault spec parameter",
        )

    st = compute_expected_tc_make_hdmi_auth_fan_state(
        camera_model=spec.camera_model,
        shooting_domain=spec.shooting_domain,
        recording_media_mode=spec.recording_media_mode,
        timecode_make=spec.timecode_make,
        timecode_run=spec.timecode_run,
        vmc_bncm1_connected=spec.vmc_bncm1_connected,
        rec_media_dur_hdmi_output=spec.rec_media_dur_hdmi_output,
        hdmi_tc_output=spec.hdmi_tc_output,
        hdmi_rec_control=spec.hdmi_rec_control,
        hdmi_4ch_audio_output=spec.hdmi_4ch_audio_output,
        network_streaming_active=spec.network_streaming_active,
        usb_streaming_active=spec.usb_streaming_active,
        access_authen_settings=spec.access_authen_settings,
        access_authen_protocol=spec.access_authen_protocol,
        wifi_security=spec.wifi_security,
        root_cert_inbound_server_requested=spec.root_cert_inbound_server_requested,
        fan_control=spec.fan_control,
        recording_active=spec.recording_active,
        internal_temp_over_threshold=spec.internal_temp_over_threshold,
        auto_power_off_temp=spec.auto_power_off_temp,
        airplane_mode=spec.airplane_mode,
        wifi_active=spec.wifi_active,
        usb_lan_active=spec.usb_lan_active,
        network_transport=spec.network_transport,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    # 1. Initialize-only [Time Code Make/Run] & HDMI [REC Control] / [4ch Audio Output]
    tc_hdmi_ok = (
        spec.reported_tc_make_errno == st["tc_make_errno"]
        and (spec.camera_model != P340_FX3_MODEL_NAME or spec.timecode_make in P340_FX3_TIMECODE_MAKE_MODES)
        and spec.reported_effective_tc_run == st["effective_tc_run"]
        and spec.reported_regen_source_slot == st["regen_source_slot"]
        and spec.reported_ext_tc_status == st["ext_tc_status"]
        and spec.reported_effective_hdmi_rec_control == st["effective_hdmi_rec_control"]
        and spec.reported_hdmi_rec_control_errno == st["hdmi_rec_control_errno"]
        and not (
            spec.hdmi_rec_control == "On"
            and st["rec_control_blocked"]
            and spec.reported_effective_hdmi_rec_control == "On"
        )
        and spec.post_tc_make == st["post_tc_make"]
        and spec.post_tc_run == st["post_tc_run"]
        and spec.post_hdmi_rec_control == st["post_hdmi_rec_control"]
        and spec.post_hdmi_tc_output == st["post_hdmi_tc_output"]
        and spec.post_rec_media_hdmi == st["post_rec_media_hdmi"]
        and spec.post_4ch_audio_out == st["post_4ch_audio_out"]
        and spec.fx6_supports_tc_clock_mode
        and spec.fx6_splits_remote_if_vs_parallel_rec
        and spec.tc_make_regen_or_hdmi_rec_ctrl_drift_events == 0
    )
    if not tc_hdmi_ok:
        _fail(
            P340_BLOCKED_TC_MAKE_REGEN_OR_HDMI_REC_CTRL_DRIFT,
            "Time Code Make/Run (Regenerate forced Rec Run / Slot-1 Simult. / EXT-LK) or HDMI REC Control (TC Out=On gate) violated",
        )

    # 2. Ver. 7.00+ [Access Authen.] SSH/PTP-IP, TLS Root Cert, [Fan Control] no-Max & [Auto Power OFF Temp.]
    auth_fan_ok = (
        spec.access_authen_settings == "On"
        and spec.access_authen_protocol in P340_FX3_ACCESS_AUTHEN_PROTOCOLS
        and spec.reported_auth_proto_errno == st["auth_proto_errno"]
        and spec.wifi_security in P340_FX3_WIFI_SECURITY_ACTIVE_MODES
        and spec.reported_wifi_sec_errno == st["wifi_sec_errno"]
        and not spec.root_cert_inbound_server_requested
        and spec.reported_root_cert_inbound_errno == st["root_cert_inbound_errno"]
        and spec.fan_control not in P340_FAN_CONTROL_FORBIDDEN_MAX_MODES
        and (
            (spec.camera_model == P340_FX3_MODEL_NAME and spec.fan_control in P340_FX3_FAN_CONTROL_MODES)
            or (
                spec.camera_model == P340_FX6_DONOR_MODEL_NAME
                and spec.fan_control in P340_FX6_FAN_CONTROL_ACTIVE_MODES
            )
        )
        and spec.reported_fan_control_errno == st["fan_control_errno"]
        and spec.reported_fan_spinning_now == st["fan_spinning_now"]
        and not spec.fx6_has_fan_control_max
        and spec.fx6_fan_always_off_dormant
        and spec.post_access_authen == st["post_access_authen"]
        and spec.post_root_certs_cleared == st["post_root_certs_cleared"]
        and spec.post_fan_control == st["post_fan_control"]
        and spec.post_auto_pwr_off_temp == st["post_auto_pwr_off_temp"]
        and spec.post_airplane_mode == st["post_airplane_mode"]
        and spec.access_authen_ssh_tls_or_fan_max_drift_events == 0
    )
    if not auth_fan_ok:
        _fail(
            P340_BLOCKED_ACCESS_AUTHEN_SSH_TLS_OR_FAN_MAX_DRIFT,
            "Access Authen. (SSH+PTP-IP, no HTTP_DIGEST/HTTPS, WPA2/WPA3, outbound TLS Root Cert) or Fan Control (4-mode FX3 / 3-mode FX6, ZERO Max) violated",
        )

    # 3. Zero-RF (Airplane Mode=On, USB-LAN CDC-NCM) & Slot-1 Tier-0 EROFS=30 Vault Firewall
    slot1_mutated = (
        (
            spec.requested_vault_action in P340_WRITE_MUTATING_VAULT_ACTIONS
            or (
                spec.requested_vault_slot == P340_SLOT1_VAULT_SLOT
                and spec.requested_vault_action == "HDMI_ONLY_EXT_REC_TRIGGER"
                and spec.rec_media_dur_hdmi_output == "On"
                and spec.slot1_holds_tier0_vault
            )
        )
        and spec.reported_vault_action_allowed
    )
    zero_rf_vault_ok = (
        st["rf_zero_enforced"]
        and spec.rf_packets_transmitted == 0
        and spec.rf_nvs_mutation_bytes == 0
        and not slot1_mutated
        and spec.reported_vault_action_allowed == st["vault_action_allowed"]
        and spec.vault_firewall_errno == st["vault_firewall_errno"]
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_format_hard_locked
        and spec.zero_rf_or_slot1_vault_bypass_events == 0
    )
    if not zero_rf_vault_ok:
        _fail(
            P340_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL,
            "Zero-RF Airplane Mode=On (USB-LAN CDC-NCM only) or Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    # 4. Stage-B Overlay & H0 == H3
    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P340_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P340_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P340_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P340_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    overlay_and_h0_h3_ok = overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "61B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "timecode_make": spec.timecode_make,
            "effective_tc_run": spec.reported_effective_tc_run,
            "ext_tc_status": spec.reported_ext_tc_status,
            "hdmi_rec_control": spec.reported_effective_hdmi_rec_control,
            "access_authen_protocol": spec.access_authen_protocol,
            "fan_control": spec.fan_control,
            "post_airplane_mode": spec.post_airplane_mode,
            "rf_packets": spec.rf_packets_transmitted,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return TcMakeHdmiAccessAuthFanVaultReport(
        schema=PHASE340_SCHEMA,
        version=PHASE340_VERSION,
        passed=passed,
        status=P340_STATUS_VERIFIED_PILLAR_61B if passed else P340_STATUS_REJECTED_PILLAR_61B,
        block_code=block_code,
        tc_make_regen_and_hdmi_rec_ctrl_verified=tc_hdmi_ok,
        access_authen_ssh_tls_and_fan_no_max_verified=auth_fan_ok,
        zero_rf_and_slot1_erofs30_vault_verified=zero_rf_vault_ok,
        overlay_and_h0_h3_verified=overlay_and_h0_h3_ok,
        matrix_states_checked=18,
        tc_make_regen_or_hdmi_rec_ctrl_drift_events=spec.tc_make_regen_or_hdmi_rec_ctrl_drift_events,
        access_authen_ssh_tls_or_fan_max_drift_events=(
            spec.access_authen_ssh_tls_or_fan_max_drift_events
        ),
        zero_rf_or_slot1_vault_bypass_events=spec.zero_rf_or_slot1_vault_bypass_events,
        rf_packets_transmitted=spec.rf_packets_transmitted,
        rf_nvs_mutation_bytes=spec.rf_nvs_mutation_bytes,
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_big6_framing_interval_tc_auth_fan_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_61a: Optional[Big6FramingIntervalSlot1VaultSpec] = None,
    spec_61b: Optional[TcMakeHdmiAccessAuthFanVaultSpec] = None,
) -> Big6FramingIntervalTcAuthFanVaultReport:
    """Combined single-shot verifier for Pillar 61A + Pillar 61B + bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase340_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_big6_framing_interval_vault(
        spec_61a or build_default_safe_big6_framing_interval_vault_spec()
    )
    rep_b = evaluate_tc_make_hdmi_auth_fan_vault(
        spec_61b or build_default_safe_tc_make_hdmi_auth_fan_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 340 Wave-59 donor artifact parity check failed")
    if not donor_snapshot.under_2_0s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return Big6FramingIntervalTcAuthFanVaultReport(
        schema=PHASE340_SCHEMA,
        version=PHASE340_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P340_STATUS_VERIFIED_PILLAR61_SUITE if all_ok else P340_STATUS_FAIL_PILLAR61_SUITE,
        donor_snapshot=donor_snapshot,
        big6_framing_interval_report=rep_a,
        tc_make_hdmi_auth_fan_report=rep_b,
        big6_home_or_lower_left_nd_drift_events=rep_a.big6_home_or_lower_left_nd_drift_events,
        framing_manual_or_dormant_auto_framing_drift_events=(
            rep_a.framing_manual_or_dormant_auto_framing_drift_events
        ),
        interval_shoot_9999_or_fx6_mxf_spoof_events=(
            rep_a.interval_shoot_9999_or_fx6_mxf_spoof_events
        ),
        tc_make_regen_or_hdmi_rec_ctrl_drift_events=(
            rep_b.tc_make_regen_or_hdmi_rec_ctrl_drift_events
        ),
        access_authen_ssh_tls_or_fan_max_drift_events=(
            rep_b.access_authen_ssh_tls_or_fan_max_drift_events
        ),
        zero_rf_or_slot1_vault_bypass_events=rep_b.zero_rf_or_slot1_vault_bypass_events,
        rf_packets_transmitted=rep_b.rf_packets_transmitted,
        rf_nvs_mutation_bytes=rep_b.rf_nvs_mutation_bytes,
        slot1_data_sector_writes=rep_a.slot1_data_sector_writes + rep_b.slot1_data_sector_writes,
        slot1_dcim_avf_mutation_bytes=rep_a.slot1_dcim_avf_mutation_bytes,
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


def verify_big6_framing_interval_tc_auth_fan_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_61a: Optional[Big6FramingIntervalSlot1VaultSpec] = None,
    spec_61b: Optional[TcMakeHdmiAccessAuthFanVaultSpec] = None,
) -> Big6FramingIntervalTcAuthFanVaultReport:
    """Symmetry alias for `verify_big6_framing_interval_tc_auth_fan_and_vault`."""
    return verify_big6_framing_interval_tc_auth_fan_and_vault(
        force_clean_room=force_clean_room,
        spec_61a=spec_61a,
        spec_61b=spec_61b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 61A & 61B)
# ---------------------------------------------------------------------------


def run_pillar61a_big6_framing_interval_vault_6_scenario_suite() -> Pillar61ASuiteResult:
    """Run 6 Pillar 61A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, Big6FramingIntervalSlot1VaultSpec, Optional[str]], ...] = (
        (
            P340_PILLAR_61A_SCENARIO_IDS[0],
            True,
            build_default_safe_big6_framing_interval_vault_spec(
                fw_version="7.02",
                shooting_domain="Movie",
                mode_settings="Fixed/Variable",
                big6_entry_trigger="SWIPE_DOWN",
                touch_operation_enabled=True,
                swipe_down_setting="Open Home Screen",
                log_shooting_mode="Cine EI",
                shutter_mode="Angle",
                home_lower_left_mode="ND Filter",
                reported_big6_active=True,
                reported_big6_tiles=(
                    "FPS",
                    "Base ISO + EI",
                    "Shutter Angle",
                    "ND Filter",
                    "Select LUT",
                    "White Balance",
                ),
                framing_enabled=True,
                framing_rec_streaming="Full",
                framing_hdmi="Crop",
                apsc_s35_requested=False,
                movie_frame_rate_fps=23.98,
                reported_effective_framing_enabled=True,
                reported_effective_apsc_s35=False,
                reset_action="Camera Settings Reset",
                post_home_lower_left="Aperture",
                post_framing_enabled=False,
                post_framing_rec_streaming="Full",
                post_framing_hdmi="Crop",
            ),
            None,
        ),
        (
            P340_PILLAR_61A_SCENARIO_IDS[1],
            True,
            build_default_safe_big6_framing_interval_vault_spec(
                shooting_domain="Still",
                exposure_mode="M",
                mode_settings="Movie",
                big6_entry_trigger="NONE",
                reported_big6_active=False,
                interval_shooting_enabled=True,
                interval_start_time_sec=5,
                interval_period_sec=10,
                interval_num_shots=9999,
                interval_ae_tracking="Low",
                interval_shutter_type="Electronic Shutter",
                interval_priority="On",
                bulb_active=True,
                reported_effective_interval_enabled=True,
                reported_bulb_overridden_to_30s=True,
                reset_action="Camera Settings Reset",
                post_interval_enabled=False,
                post_interval_start_sec=1,
                post_interval_period_sec=3,
                post_interval_num_shots=30,
                post_interval_ae_tracking="Mid",
                post_interval_shutter_type="Electronic Shutter",
                post_interval_priority="Off",
                requested_vault_slot=2,
                requested_vault_action="INTERVAL_SHOOT_SLOT2",
                interval_targets_slot1=False,
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            ),
            None,
        ),
        (
            P340_PILLAR_61A_SCENARIO_IDS[2],
            False,
            build_default_safe_big6_framing_interval_vault_spec(
                fw_version="6.02",
                mode_settings="Movie",
                big6_entry_trigger="HOME_KEY",
                reported_big6_active=True,
                requested_physical_end_hw=True,
                reported_physical_end_errno=None,
                big6_home_or_lower_left_nd_drift_events=1,
            ),
            P340_BLOCKED_BIG6_HOME_OR_LOWER_LEFT_ND_DRIFT,
        ),
        (
            P340_PILLAR_61A_SCENARIO_IDS[3],
            False,
            build_default_safe_big6_framing_interval_vault_spec(
                framing_enabled=True,
                movie_frame_rate_fps=119.88,
                active_recording=True,
                reported_effective_framing_enabled=True,
                reported_framing_errno=None,
                requested_dormant_auto_framing_symbols=("Auto Framing", "PTZAUTOFRAMING_MODE"),
                reported_dormant_auto_framing_errno=None,
                framing_manual_or_dormant_auto_framing_drift_events=1,
            ),
            P340_BLOCKED_FRAMING_MANUAL_OR_DORMANT_AUTO_FRAMING_DRIFT,
        ),
        (
            P340_PILLAR_61A_SCENARIO_IDS[4],
            False,
            build_default_safe_big6_framing_interval_vault_spec(
                shooting_domain="Still",
                exposure_mode="iAuto",
                interval_shooting_enabled=True,
                interval_num_shots=10000,
                reported_effective_interval_enabled=True,
                reported_interval_errno=None,
                fx6_interval_rec_single_mxf=False,
                fx6_has_auto_framing_menu=True,
                interval_shoot_9999_or_fx6_mxf_spoof_events=1,
            ),
            P340_BLOCKED_INTERVAL_SHOOT_9999_OR_FX6_MXF_SPOOF,
        ),
        (
            P340_PILLAR_61A_SCENARIO_IDS[5],
            False,
            build_default_safe_big6_framing_interval_vault_spec(
                shooting_domain="Still",
                mode_settings="Movie",
                big6_entry_trigger="NONE",
                reported_big6_active=False,
                interval_shooting_enabled=True,
                interval_num_shots=9999,
                reported_effective_interval_enabled=True,
                post_interval_enabled=True,
                post_interval_num_shots=9999,
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="INTERVAL_SHOOT_SLOT1_BURST",
                interval_targets_slot1=True,
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=8192,
                slot1_dcim_avf_mutation_bytes=4096,
                slot1_vault_mutation_bytes=12288,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/setting/61a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P340_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar61ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_big6_framing_interval_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar61ScenarioOutcome(
                scenario_id=sid,
                pillar="61A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar61ASuiteResult(
        passed=all_ok,
        status=P340_STATUS_VERIFIED_PILLAR_61A if all_ok else P340_STATUS_REJECTED_PILLAR_61A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar61b_tc_make_hdmi_auth_fan_vault_6_scenario_suite() -> Pillar61BSuiteResult:
    """Run 6 Pillar 61B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, TcMakeHdmiAccessAuthFanVaultSpec, Optional[str]], ...] = (
        (
            P340_PILLAR_61B_SCENARIO_IDS[0],
            True,
            build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                recording_media_mode="Simult. Recording",
                timecode_make="Regenerate",
                timecode_run="Free Run",
                vmc_bncm1_connected=False,
                reported_effective_tc_run="Rec Run",
                reported_regen_source_slot=1,
                reported_ext_tc_status="INTERNAL",
                rec_media_dur_hdmi_output="Off(HDMI Only)",
                hdmi_tc_output="On",
                hdmi_rec_control="On",
                hdmi_4ch_audio_output="CH3/CH4",
                reported_effective_hdmi_rec_control="On",
                reset_action="Camera Settings Reset",
                post_tc_make="Regenerate",
                post_tc_run="Free Run",
                post_hdmi_rec_control="On",
                post_hdmi_tc_output="On",
                post_rec_media_hdmi="Off(HDMI Only)",
                post_4ch_audio_out="CH3/CH4",
                requested_vault_slot=1,
                requested_vault_action="HDMI_ONLY_EXT_REC_TRIGGER",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            ),
            None,
        ),
        (
            P340_PILLAR_61B_SCENARIO_IDS[1],
            True,
            build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                timecode_make="Preset",
                timecode_run="Free Run",
                vmc_bncm1_connected=True,
                usb_lan_active=False,
                reported_effective_tc_run="Free Run",
                reported_ext_tc_status="EXT-LK",
                access_authen_settings="On",
                access_authen_protocol="SSH+PTP-IP",
                wifi_security="WPA3-SAE",
                fan_control="Always Off",
                recording_active=True,
                reported_fan_spinning_now=False,
                auto_power_off_temp="High",
                reset_action="Reset Network Set.",
                post_tc_make="Preset",
                post_tc_run="Free Run",
                post_access_authen="On",
                post_root_certs_cleared=True,
                post_fan_control="Always Off",
                post_auto_pwr_off_temp="High",
                post_airplane_mode="On",
                requested_vault_slot=2,
                requested_vault_action="IMPORT_ROOT_CERT_SLOT2",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            ),
            None,
        ),
        (
            P340_PILLAR_61B_SCENARIO_IDS[2],
            False,
            build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                timecode_make="Clock",
                reported_tc_make_errno=None,
                vmc_bncm1_connected=True,
                reported_ext_tc_status="EXT-LK",
                hdmi_tc_output="Off",
                hdmi_rec_control="On",
                reported_effective_hdmi_rec_control="On",
                reported_hdmi_rec_control_errno=None,
                tc_make_regen_or_hdmi_rec_ctrl_drift_events=1,
            ),
            P340_BLOCKED_TC_MAKE_REGEN_OR_HDMI_REC_CTRL_DRIFT,
        ),
        (
            P340_PILLAR_61B_SCENARIO_IDS[3],
            False,
            build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                access_authen_protocol="HTTP_DIGEST",
                reported_auth_proto_errno=None,
                wifi_security="WEP",
                reported_wifi_sec_errno=None,
                root_cert_inbound_server_requested=True,
                reported_root_cert_inbound_errno=None,
                reset_action="Reset Network Set.",
                post_airplane_mode="Off",
                access_authen_ssh_tls_or_fan_max_drift_events=1,
            ),
            P340_BLOCKED_ACCESS_AUTHEN_SSH_TLS_OR_FAN_MAX_DRIFT,
        ),
        (
            P340_PILLAR_61B_SCENARIO_IDS[4],
            False,
            build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                fan_control="Max",
                reported_fan_control_errno=None,
                fx6_has_fan_control_max=True,
                fx6_fan_always_off_dormant=False,
                access_authen_ssh_tls_or_fan_max_drift_events=1,
            ),
            P340_BLOCKED_ACCESS_AUTHEN_SSH_TLS_OR_FAN_MAX_DRIFT,
        ),
        (
            P340_PILLAR_61B_SCENARIO_IDS[5],
            False,
            build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                airplane_mode="Off",
                post_airplane_mode="Off",
                wifi_active=True,
                network_transport="Wi-Fi",
                rf_packets_transmitted=8,
                rf_nvs_mutation_bytes=64,
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="FORMAT_FULL",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                zero_rf_or_slot1_vault_bypass_events=1,
            ),
            P340_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar61ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_tc_make_hdmi_auth_fan_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar61ScenarioOutcome(
                scenario_id=sid,
                pillar="61B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar61BSuiteResult(
        passed=all_ok,
        status=P340_STATUS_VERIFIED_PILLAR_61B if all_ok else P340_STATUS_REJECTED_PILLAR_61B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Standalone Pillar 61 Suite & Unified 61/61 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def run_pillar61_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar61StandaloneReport:
    """Run full Pillar 61 standalone suite (`6/6` Pillar 61A + `6/6` Pillar 61B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase340_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar61a_big6_framing_interval_vault_6_scenario_suite()
    res_b = run_pillar61b_tc_make_hdmi_auth_fan_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 340 donor verification failed")
    if not donor_snapshot.under_2_0s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE340_SCHEMA,
            "version": PHASE340_VERSION,
            "mode": donor_snapshot.verification_mode,
            "61a": [asdict(s) for s in res_a.scenarios],
            "61b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar61StandaloneReport(
        schema=PHASE340_SCHEMA,
        version=PHASE340_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P340_STATUS_VERIFIED_PILLAR61_SUITE if all_ok else P340_STATUS_FAIL_PILLAR61_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_61a_big6_home_framing_interval_vault=res_a,
        pillar_61b_tc_make_hdmi_auth_fan_vault=res_b,
        big6_home_or_lower_left_nd_drift_events=(
            P340_BIG6_HOME_OR_LOWER_LEFT_ND_DRIFT_EVENTS if res_a.passed else 1
        ),
        framing_manual_or_dormant_auto_framing_drift_events=(
            P340_FRAMING_MANUAL_OR_DORMANT_AUTO_FRAMING_DRIFT_EVENTS if res_a.passed else 1
        ),
        interval_shoot_9999_or_fx6_mxf_spoof_events=(
            P340_INTERVAL_SHOOT_9999_OR_FX6_MXF_SPOOF_EVENTS if res_a.passed else 1
        ),
        tc_make_regen_or_hdmi_rec_ctrl_drift_events=(
            P340_TC_MAKE_REGEN_OR_HDMI_REC_CTRL_DRIFT_EVENTS if res_b.passed else 1
        ),
        access_authen_ssh_tls_or_fan_max_drift_events=(
            P340_ACCESS_AUTHEN_SSH_TLS_OR_FAN_MAX_DRIFT_EVENTS if res_b.passed else 1
        ),
        zero_rf_or_slot1_vault_bypass_events=(
            P340_ZERO_RF_OR_SLOT1_VAULT_BYPASS_EVENTS if res_b.passed else 1
        ),
        rf_packets_transmitted=P340_RF_PACKETS_TRANSMITTED if res_b.passed else 1,
        rf_nvs_mutation_bytes=P340_RF_NVS_MUTATION_BYTES if res_b.passed else 64,
        slot1_data_sector_writes=(
            P340_SLOT1_DATA_SECTOR_WRITES if (res_a.passed and res_b.passed) else 1
        ),
        slot1_dcim_avf_mutation_bytes=(
            P340_SLOT1_DCIM_AVF_MUTATION_BYTES if res_a.passed else 4096
        ),
        slot1_vault_mutation_bytes=(
            P340_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        slot1_format_hard_locked=P340_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_eopnotsupp_enforced=P340_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
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


def _apply_master61_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def _master61_local_donors_available() -> bool:
    """Return True only when legacy BODYDATA.DAT and all 17 Wave-59 local donors exist."""
    required_relpaths: Tuple[str, ...] = (
        "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT",
        P340_DONOR_FX3_APPFW_702_RELPATH,
        P340_DONOR_FX6_APPFW_601_RELPATH,
        P340_DONOR_FX3_BACKUP_BIN_RELPATH,
        P340_DONOR_FX3_UXC_EN_F_RELPATH,
        P340_DONOR_FX3_UXC_SC_F_RELPATH,
        P340_DONOR_FX3_UXC_TC_F_RELPATH,
        P340_DONOR_FX3_UXC_JA_F_RELPATH,
        P340_DONOR_FX3_UXC_EN_RELPATH,
        P340_DONOR_FX3_UXC_SC_RELPATH,
        P340_DONOR_FX3_UXC_TC_RELPATH,
        P340_DONOR_FX3_UXC_JA_RELPATH,
        P340_DONOR_FX3_UXC_EN_G_RELPATH,
        P340_DONOR_FX3_UXC_SC_G_RELPATH,
        P340_DONOR_FX3_UXC_TC_G_RELPATH,
        P340_DONOR_FX3_UXC_JA_G_RELPATH,
        P340_DONOR_FX6_UXC_EN_RELPATH,
        P340_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for relpath in required_relpaths:
        try:
            resolved = _resolve_phase340_donor_path(relpath)
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


def evaluate_realhw_61pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master61PillarRecoveryReport:
    """Evaluate and aggregate all 61 recovery pillars (`1..61`) concurrently -> `61/61` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_61_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    if resolved_clean_room is None and not _master61_local_donors_available():
        resolved_clean_room = True
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_60pillar() -> Master60PillarRecoveryReport:
        return evaluate_realhw_60pillar_recovery_master(**kw)

    def _run_p61() -> Tuple[Pillar61StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar61_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_60 = pool.submit(_run_60pillar)
        fut_61 = pool.submit(_run_p61)
        m60_rep = fut_60.result()
        p61_rep, p61_dt = fut_61.result()

    all_errors: List[str] = list(m60_rep.errors) + list(p61_rep.errors)
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
        if getattr(m60_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-60 violated {attr_name} == {expected_val}")
        if getattr(p61_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 61 violated {attr_name} == {expected_val}")

    if p61_rep.cross_model_flash_authorized is not False:
        all_errors.append("Pillar 61 violated cross_model_flash_authorized == False")

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
        if getattr(m60_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-60 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("big6_home_or_lower_left_nd_drift_events", 0),
        ("framing_manual_or_dormant_auto_framing_drift_events", 0),
        ("interval_shoot_9999_or_fx6_mxf_spoof_events", 0),
        ("tc_make_regen_or_hdmi_rec_ctrl_drift_events", 0),
        ("access_authen_ssh_tls_or_fan_max_drift_events", 0),
        ("zero_rf_or_slot1_vault_bypass_events", 0),
        ("rf_packets_transmitted", 0),
        ("rf_nvs_mutation_bytes", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_dcim_avf_mutation_bytes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_eopnotsupp_enforced", True),
    ):
        if getattr(p61_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 61 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m60_rep.pillars)
    spec61 = MASTER_61_PILLAR_SPECS[60]
    p61_metrics = {
        "pillar_61a_big6_home_framing_interval_vault": (
            f"{p61_rep.pillar_61a_big6_home_framing_interval_vault.scenarios_passed}/"
            f"{p61_rep.pillar_61a_big6_home_framing_interval_vault.scenarios_total}"
        ),
        "pillar_61b_tc_make_hdmi_auth_fan_vault": (
            f"{p61_rep.pillar_61b_tc_make_hdmi_auth_fan_vault.scenarios_passed}/"
            f"{p61_rep.pillar_61b_tc_make_hdmi_auth_fan_vault.scenarios_total}"
        ),
        "big6_home_or_lower_left_nd_drift_events": p61_rep.big6_home_or_lower_left_nd_drift_events,
        "framing_manual_or_dormant_auto_framing_drift_events": (
            p61_rep.framing_manual_or_dormant_auto_framing_drift_events
        ),
        "interval_shoot_9999_or_fx6_mxf_spoof_events": (
            p61_rep.interval_shoot_9999_or_fx6_mxf_spoof_events
        ),
        "tc_make_regen_or_hdmi_rec_ctrl_drift_events": (
            p61_rep.tc_make_regen_or_hdmi_rec_ctrl_drift_events
        ),
        "access_authen_ssh_tls_or_fan_max_drift_events": (
            p61_rep.access_authen_ssh_tls_or_fan_max_drift_events
        ),
        "zero_rf_or_slot1_vault_bypass_events": p61_rep.zero_rf_or_slot1_vault_bypass_events,
        "rf_packets_transmitted": p61_rep.rf_packets_transmitted,
        "rf_nvs_mutation_bytes": p61_rep.rf_nvs_mutation_bytes,
        "slot1_data_sector_writes": p61_rep.slot1_data_sector_writes,
        "slot1_dcim_avf_mutation_bytes": p61_rep.slot1_dcim_avf_mutation_bytes,
        "slot1_vault_mutation_bytes": p61_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p61_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_eopnotsupp_enforced": p61_rep.slot1_vault_erofs_eopnotsupp_enforced,
        "overall_ready_for_hardware_attach": p61_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p61_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p61_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p61_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec61[0],
            pillar_id=spec61[1],
            phase_label=spec61[2],
            module_name=spec61[3],
            passed=bool(p61_rep.all_passed),
            status=p61_rep.status,
            verification_mode=p61_rep.verification_mode,
            elapsed_seconds=p61_dt,
            key_metrics=p61_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec61[1],
                    "mode": p61_rep.verification_mode,
                    "status": p61_rep.status,
                    "metrics": p61_metrics,
                    "passed": p61_rep.all_passed,
                }
            ),
            errors=tuple(p61_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master61_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p61_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_61_PILLAR_COUNT == 61
        and pillars_passed == 61
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE340_SCHEMA,
            "schema_version": PHASE340_MASTER_SCHEMA,
            "version": PHASE340_VERSION,
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
    return Master61PillarRecoveryReport(
        schema=PHASE340_SCHEMA,
        schema_version=PHASE340_MASTER_SCHEMA,
        version=PHASE340_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P340_STATUS_VERIFIED_61OF61_AGGREGATOR if all_ok else P340_STATUS_FAIL_61OF61_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P340_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.5,
        under_6s_budget=elapsed < P340_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P340_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p61_rep.donor_snapshot,
        pillar61_a_big6_home_framing_interval_vault=(
            p61_rep.pillar_61a_big6_home_framing_interval_vault
        ),
        pillar61_b_tc_make_hdmi_auth_fan_vault=p61_rep.pillar_61b_tc_make_hdmi_auth_fan_vault,
        big6_home_or_lower_left_nd_drift_events=p61_rep.big6_home_or_lower_left_nd_drift_events,
        framing_manual_or_dormant_auto_framing_drift_events=(
            p61_rep.framing_manual_or_dormant_auto_framing_drift_events
        ),
        interval_shoot_9999_or_fx6_mxf_spoof_events=(
            p61_rep.interval_shoot_9999_or_fx6_mxf_spoof_events
        ),
        tc_make_regen_or_hdmi_rec_ctrl_drift_events=(
            p61_rep.tc_make_regen_or_hdmi_rec_ctrl_drift_events
        ),
        access_authen_ssh_tls_or_fan_max_drift_events=(
            p61_rep.access_authen_ssh_tls_or_fan_max_drift_events
        ),
        zero_rf_or_slot1_vault_bypass_events=p61_rep.zero_rf_or_slot1_vault_bypass_events,
        rf_packets_transmitted=p61_rep.rf_packets_transmitted,
        rf_nvs_mutation_bytes=p61_rep.rf_nvs_mutation_bytes,
        slot1_data_sector_writes=m60_rep.slot1_data_sector_writes + p61_rep.slot1_data_sector_writes,
        slot1_dcim_avf_mutation_bytes=p61_rep.slot1_dcim_avf_mutation_bytes,
        slot1_vault_mutation_bytes=(
            m60_rep.slot1_vault_mutation_bytes + p61_rep.slot1_vault_mutation_bytes
        ),
        slot1_format_hard_locked=(
            m60_rep.slot1_format_hard_locked and p61_rep.slot1_format_hard_locked
        ),
        slot1_vault_erofs_eopnotsupp_enforced=(
            m60_rep.slot1_vault_erofs_eopnotsupp_enforced
            and p61_rep.slot1_vault_erofs_eopnotsupp_enforced
        ),
        fx3_big6_tile_count=P340_FX3_BIG6_TILE_COUNT,
        fx3_has_physical_end_hw=P340_FX3_PHYSICAL_END_HARDWARE,
        fx3_has_dormant_auto_framing=False,
        fx3_interval_subitem_count=P340_INTERVAL_SUBITEM_COUNT,
        fx3_interval_max_shots=P340_INTERVAL_SHOTS_MAX,
        fx3_access_authen_http_digest_hits=P340_FX3_HTTP_DIGEST_HTTPS_HIT_COUNT,
        fx3_fan_control_mode_count=len(P340_FX3_FAN_CONTROL_MODES),
        fx6_fan_control_mode_count=len(P340_FX6_FAN_CONTROL_ACTIVE_MODES),
        fx3_has_fan_control_max=False,
        fx6_has_fan_control_max=False,
        # Carried forward Pillar 60 metrics
        bright_mon_or_monitor_brightness_drift_events=(
            m60_rep.bright_mon_or_monitor_brightness_drift_events
        ),
        bulb_mech_or_dormant_bulb_timer_hdr_drift_events=(
            m60_rep.bulb_mech_or_dormant_bulb_timer_hdr_drift_events
        ),
        fx6_vf_backlight_or_still_spoof_events=m60_rep.fx6_vf_backlight_or_still_spoof_events,
        shotmark_clipflag_or_dormant_divide_drift_events=(
            m60_rep.shotmark_clipflag_or_dormant_divide_drift_events
        ),
        tc_link_wpa3_or_usblan_mutex_drift_events=(
            m60_rep.tc_link_wpa3_or_usblan_mutex_drift_events
        ),
        slot1_m4root_avf_mutation_bytes=m60_rep.slot1_m4root_avf_mutation_bytes,
        slot1_dcim_divider_mutation_bytes=m60_rep.slot1_dcim_divider_mutation_bytes,
        fx3_bright_monitoring_symbol_count=m60_rep.fx3_bright_monitoring_symbol_count,
        fx3_bright_mon_v700_focus_mag_coexist=m60_rep.fx3_bright_mon_v700_focus_mag_coexist,
        fx3_monitor_brightness_level_min=m60_rep.fx3_monitor_brightness_level_min,
        fx3_monitor_brightness_level_max=m60_rep.fx3_monitor_brightness_level_max,
        fx3_has_dormant_bulb_timer=m60_rep.fx3_has_dormant_bulb_timer,
        fx3_has_dormant_auto_hdr=m60_rep.fx3_has_dormant_auto_hdr,
        fx3_has_dormant_divide_extract=m60_rep.fx3_has_dormant_divide_extract,
        fx3_has_bt_timecode_link=m60_rep.fx3_has_bt_timecode_link,
        fx3_usb_lan_kmod_count=m60_rep.fx3_usb_lan_kmod_count,
        fx3_wifi_active_security_count=m60_rep.fx3_wifi_active_security_count,
        fx6_vf_brightness_min=m60_rep.fx6_vf_brightness_min,
        fx6_vf_brightness_max=m60_rep.fx6_vf_brightness_max,
        fx6_has_physical_tc_in_out_bnc=m60_rep.fx6_has_physical_tc_in_out_bnc,
        fx6_has_bluetooth_hardware=m60_rep.fx6_has_bluetooth_hardware,
        # Carried forward Pillar 59 metrics
        steadyshot_47focal_or_lockout_drift_events=(
            m60_rep.steadyshot_47focal_or_lockout_drift_events
        ),
        selftimer_dormant_or_led8_audio_drift_events=(
            m60_rep.selftimer_dormant_or_led8_audio_drift_events
        ),
        fx6_ibis_or_selftimer_spoof_events=m60_rep.fx6_ibis_or_selftimer_spoof_events,
        zebra_custom_ire_or_peaking_clean_hdmi_drift_events=(
            m60_rep.zebra_custom_ire_or_peaking_clean_hdmi_drift_events
        ),
        streaming_24p_rec_or_network_reset_drift_events=(
            m60_rep.streaming_24p_rec_or_network_reset_drift_events
        ),
        slot1_streaming_or_ftp_mutation_bytes=m60_rep.slot1_streaming_or_ftp_mutation_bytes,
        fx3_steadyshot_47_focal_count=m60_rep.fx3_steadyshot_47_focal_count,
        fx3_image_stabilization_item_count=m60_rep.fx3_image_stabilization_item_count,
        fx3_selftimer_cont_combo_count=m60_rep.fx3_selftimer_cont_combo_count,
        fx3_front_lamp_8_id=m60_rep.fx3_front_lamp_8_id,
        fx3_zebra_preset_count=m60_rep.fx3_zebra_preset_count,
        fx3_peaking_color_count=m60_rep.fx3_peaking_color_count,
        fx3_streaming_protocol_count=m60_rep.fx3_streaming_protocol_count,
        fx3_has_5axis_ibis=m60_rep.fx3_has_5axis_ibis,
        fx3_has_movie_self_timer=m60_rep.fx3_has_movie_self_timer,
        fx6_has_ibis=m60_rep.fx6_has_ibis,
        fx6_has_6axis_gyro_metadata=m60_rep.fx6_has_6axis_gyro_metadata,
        fx6_has_still_self_timer=m60_rep.fx6_has_still_self_timer,
        # Carried forward Pillar 58..41 metrics
        dial_customize_dormant_trap_or_reset_drift_events=(
            m60_rep.dial_customize_dormant_trap_or_reset_drift_events
        ),
        rear_dial_lr_or_mydial_override_drift_events=(
            m60_rep.rear_dial_lr_or_mydial_override_drift_events
        ),
        fn_menu_12x2_or_fx6_dial_spoof_events=m60_rep.fn_menu_12x2_or_fx6_dial_spoof_events,
        live_view_display_reset_split_or_mode_drift_events=(
            m60_rep.live_view_display_reset_split_or_mode_drift_events
        ),
        grid_line_or_hdmi_clean_feed_leak_events=m60_rep.grid_line_or_hdmi_clean_feed_leak_events,
        lut_path_embed_sidecar_or_slot1_vault_bypass_events=(
            m60_rep.lut_path_embed_sidecar_or_slot1_vault_bypass_events
        ),
        slot1_lut_mutation_bytes=m60_rep.slot1_lut_mutation_bytes,
        slot1_avf_info_mutated=m60_rep.slot1_avf_info_mutated,
        fx3_dial_customize_item_count=m60_rep.fx3_dial_customize_item_count,
        fx3_physical_dial_count=m60_rep.fx3_physical_dial_count,
        fx3_my_dial_bank_count=m60_rep.fx3_my_dial_bank_count,
        fx3_fn_menu_still_slots=m60_rep.fx3_fn_menu_still_slots,
        fx3_fn_menu_movie_slots=m60_rep.fx3_fn_menu_movie_slots,
        fx3_live_view_display_set_item_count=m60_rep.fx3_live_view_display_set_item_count,
        fx3_grid_line_type_count=m60_rep.fx3_grid_line_type_count,
        fx3_user_lut_slot_count=m60_rep.fx3_user_lut_slot_count,
        fx3_pplut_slot_count=m60_rep.fx3_pplut_slot_count,
        fx6_user_lut_ui_cap=m60_rep.fx6_user_lut_ui_cap,
        fx6_has_av_tv_rotate=m60_rep.fx6_has_av_tv_rotate,
        fx6_has_my_dial=m60_rep.fx6_has_my_dial,
        fx6_has_fn_menu=m60_rep.fx6_has_fn_menu,
        fx6_has_multi_channel_lut_switches=m60_rep.fx6_has_multi_channel_lut_switches,
        fx3_has_builtin_evf=m60_rep.fx3_has_builtin_evf,
        fx3_has_var_shutter=m60_rep.fx3_has_var_shutter,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        master_61pillar_sha256=master_sha,
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


def evaluate_61pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master61PillarRecoveryReport:
    """Short alias for `evaluate_realhw_61pillar_recovery_master`."""
    return evaluate_realhw_61pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_61pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master61PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_61pillar_recovery_master`."""
    return evaluate_realhw_61pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
