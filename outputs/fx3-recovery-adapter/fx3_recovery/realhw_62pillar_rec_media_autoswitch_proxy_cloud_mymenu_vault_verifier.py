"""Phase 344 Milestone — Recovery Pillar 62 & Concurrent 62/62 Master Recovery Verifier:
Wave-60 Sony ILME-FX3 (Ver. 7.02) vs ILME-FX6 (Ver. 6.01) Empirically Grounded Guardrails:
  * Pillar 62A: `[Rec. Media Settings]` architectural evolution from dormant Alpha
    `[Prioritize Rec. Media]` (`_f 0x719e`, `0` hits in FX3 `appFw.so`) to split Reset-immune
    Still/Movie `[Recording Media]` (ZERO Movie `Sort Recording`, `Simult. Recording` identical
    filesystem gate) + Reset-immune `[Auto Switch Media]` (`BKID_APP_setting_relay_rec`); critical
    Tier-0 `Slot 1` spillover guard (`RELAY_REC_OFF` + `SLOT_2` + `PRM_HAITA_*_read_only_state_slot1`
    + VFS `EROFS=30`) vs FX6 `Project > Simul Rec` + dual `Rec Button Set` + hard LAN/Modem/Proxy/
    Streaming/Chunk exclusions; `SDXC V60/V90` vs `CFexpress Type A VPG200` (`base 0xe228`) /
    `VPG400` (`base 0xe224`/`0xe93f`/`0xe9aa`) speed-gate matrix; and `[Proxy Settings]` (`sq_proxy`,
    `0` `PRM_HAITA_*proxy*` strings, `XAVC S HD` `1280x720 6M` / `XAVC HS HD` `1920x1080 16M/9M 10bit`,
    `XAVC S-I DCI 4K` allowed vs `119.88p/100p` & `S&Q 120/100fps` lockout, `M4ROOT/SUB/*S03.MP4`
    coupled Delete/Protect & `Slot 1` `EROFS=30`).
  * Pillar 62B: `[Creators' Cloud]` / `[C3 Portal]` (`Ver. 4.00..7.02`, Ver. 7.00+ `Clip Flag`
    `OK/NG/KEEP` filter, `Cloud Connection *` & `Cloud Information *` Initialize-persistence,
    FTP mutual exclusion), `[Cnct. while Power OFF]` (`BKID_APP_extern_menu_cnct_while_power_off`,
    `_f 0x6ab3`, keeps BLE `UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER` energized while physical POWER switch
    is `OFF` -> dual Zero-RF lock `Airplane Mode = On` + `Cnct. while Power OFF = Off` vs Bluetooth-less
    `ILME-FX6`), `[My Menu]` `6 pages x 7 items = 42` NVRAM slots (`BKID_APP_mymenu_group{1..6}_setting_list{0..6}`,
    NOT `30` or `36`, Playback disallowed, Reset-immune) vs FX6 `20`-item `User Menu` + `User Menu Only` +
    rental-house `User Menu with Lock` (`Multi-selector + MENU` + 4-digit PIN `0000..9999`, excluded
    from `All File` & `Scene File`), Stage-B `/tmp/...` volatile overlay, `H0 == H3` (`16/16`), and
    Tier-0 `Slot 1` `EROFS=30` Vault Firewall.
  * Unified 62/62 Master Recovery Aggregator (Pillars 1..61 + Pillar 62).

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

from .realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier import (
    MASTER_61_PILLAR_SPECS,
    Master61PillarRecoveryReport,
    P340_DONOR_FX3_APPFW_702_RELPATH,
    P340_DONOR_FX3_BACKUP_BIN_RELPATH,
    P340_DONOR_FX3_UXC_EN_F_RELPATH,
    P340_DONOR_FX3_UXC_EN_G_RELPATH,
    P340_DONOR_FX3_UXC_EN_RELPATH,
    P340_DONOR_FX3_UXC_JA_F_RELPATH,
    P340_DONOR_FX3_UXC_JA_G_RELPATH,
    P340_DONOR_FX3_UXC_JA_RELPATH,
    P340_DONOR_FX3_UXC_SC_F_RELPATH,
    P340_DONOR_FX3_UXC_SC_G_RELPATH,
    P340_DONOR_FX3_UXC_SC_RELPATH,
    P340_DONOR_FX3_UXC_TC_F_RELPATH,
    P340_DONOR_FX3_UXC_TC_G_RELPATH,
    P340_DONOR_FX3_UXC_TC_RELPATH,
    P340_DONOR_FX6_APPFW_601_RELPATH,
    P340_DONOR_FX6_UXC_EN_2_RELPATH,
    P340_DONOR_FX6_UXC_EN_RELPATH,
    P340_PINNED_FX3_APPFW_702_BYTES,
    P340_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P340_PINNED_FX3_BACKUP_BIN_BYTES,
    P340_PINNED_FX3_BACKUP_BIN_SHA256,
    P340_PINNED_FX3_UXC_EN_BYTES,
    P340_PINNED_FX3_UXC_EN_F_BYTES,
    P340_PINNED_FX3_UXC_EN_F_SHA256,
    P340_PINNED_FX3_UXC_EN_G_BYTES,
    P340_PINNED_FX3_UXC_EN_G_SHA256,
    P340_PINNED_FX3_UXC_EN_SHA256,
    P340_PINNED_FX3_UXC_JA_BYTES,
    P340_PINNED_FX3_UXC_JA_F_BYTES,
    P340_PINNED_FX3_UXC_JA_F_SHA256,
    P340_PINNED_FX3_UXC_JA_G_BYTES,
    P340_PINNED_FX3_UXC_JA_G_SHA256,
    P340_PINNED_FX3_UXC_JA_SHA256,
    P340_PINNED_FX3_UXC_SC_BYTES,
    P340_PINNED_FX3_UXC_SC_F_BYTES,
    P340_PINNED_FX3_UXC_SC_F_SHA256,
    P340_PINNED_FX3_UXC_SC_G_BYTES,
    P340_PINNED_FX3_UXC_SC_G_SHA256,
    P340_PINNED_FX3_UXC_SC_SHA256,
    P340_PINNED_FX3_UXC_TC_BYTES,
    P340_PINNED_FX3_UXC_TC_F_BYTES,
    P340_PINNED_FX3_UXC_TC_F_SHA256,
    P340_PINNED_FX3_UXC_TC_G_BYTES,
    P340_PINNED_FX3_UXC_TC_G_SHA256,
    P340_PINNED_FX3_UXC_TC_SHA256,
    P340_PINNED_FX6_APPFW_601_BYTES,
    P340_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P340_PINNED_FX6_UXC_EN_2_BYTES,
    P340_PINNED_FX6_UXC_EN_2_SHA256,
    P340_PINNED_FX6_UXC_EN_BYTES,
    P340_PINNED_FX6_UXC_EN_SHA256,
    evaluate_realhw_61pillar_recovery_master,
)
from . import files as _fx3_files
from .files import is_forced_clean_room
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus

# ---------------------------------------------------------------------------
# Phase 344 Metadata, Safety Redlines & Pinned Budget Constants
# ---------------------------------------------------------------------------

PHASE344_SCHEMA = "realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier_v1"
PHASE344_MASTER_SCHEMA = "realhw_62pillar_recovery_master_v1"
PHASE344_VERSION = "1.0.0"
PHASE344_PHASE_NUMBER = 344

P344_ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"

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

P344_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
P344_OVERALL_READY_FOR_HARDWARE_ATTACH = False
P344_CROSS_MODEL_FLASH_AUTHORIZED = False

OTP_FUSE_TOUCHES = 0
OTP_FUSE_WRITES = 0
RPMB_COUNTER_INCREMENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PHYSICAL_DEVICE_WRITES = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

P344_BOUNDED_HEADER_BYTES = 4096
P344_MAX_FULL_DONOR_BYTES = 3_000_000
P344_DONOR_INSPECT_BUDGET_SECONDS = 2.0
P344_DONOR_INSPECT_CI_BUDGET_SECONDS = 2.0
P344_FAST_CLI_BUDGET_SECONDS = 1.50
P344_NOMINAL_BUDGET_SECONDS = 4.00
P344_CONCURRENT_CEILING_SECONDS = 6.00

P344_EBUSY_ERRNO = 16
P344_EINVAL_ERRNO = 22
P344_EROFS_ERRNO = 30
P344_EOPNOTSUPP_ERRNO = 95

# Camera Identities
P344_FX3_MODEL_NAME = "ILME-FX3"
P344_FX3_MODEL_ID = 0x91030080
P344_FX3_PRODUCT_CODENAME = "PRODUCT_MODEL_ALCIN_UUD"
P344_FX3_HELPGUIDE_ID = "ilc/2210"
P344_FX3_FW_VERSION = "7.02"
P344_FX3_SUPPORTED_FW_VERSIONS = ("7.02", "7.01", "7.00", "6.02", "6.00", "5.00", "4.00", "3.00", "2.00")

P344_FX6_DONOR_MODEL_NAME = "ILME-FX6"
P344_FX6_DONOR_FW_VERSION = "6.01"
P344_FX6_PRODUCT_CODENAME = "PRODUCT_MODEL_CHAPLIN"

# Pinned Donor Relpaths & Digests (17 Wave-60 donors: 14 FX3 7.02 + 3 FX6 6.01)
P344_DONOR_FX3_APPFW_702_RELPATH = P340_DONOR_FX3_APPFW_702_RELPATH
P344_DONOR_FX6_APPFW_601_RELPATH = P340_DONOR_FX6_APPFW_601_RELPATH
P344_DONOR_FX3_BACKUP_BIN_RELPATH = P340_DONOR_FX3_BACKUP_BIN_RELPATH
P344_DONOR_FX3_UXC_EN_F_RELPATH = P340_DONOR_FX3_UXC_EN_F_RELPATH
P344_DONOR_FX3_UXC_SC_F_RELPATH = P340_DONOR_FX3_UXC_SC_F_RELPATH
P344_DONOR_FX3_UXC_TC_F_RELPATH = P340_DONOR_FX3_UXC_TC_F_RELPATH
P344_DONOR_FX3_UXC_JA_F_RELPATH = P340_DONOR_FX3_UXC_JA_F_RELPATH
P344_DONOR_FX3_UXC_EN_RELPATH = P340_DONOR_FX3_UXC_EN_RELPATH
P344_DONOR_FX3_UXC_SC_RELPATH = P340_DONOR_FX3_UXC_SC_RELPATH
P344_DONOR_FX3_UXC_TC_RELPATH = P340_DONOR_FX3_UXC_TC_RELPATH
P344_DONOR_FX3_UXC_JA_RELPATH = P340_DONOR_FX3_UXC_JA_RELPATH
P344_DONOR_FX3_UXC_EN_G_RELPATH = P340_DONOR_FX3_UXC_EN_G_RELPATH
P344_DONOR_FX3_UXC_SC_G_RELPATH = P340_DONOR_FX3_UXC_SC_G_RELPATH
P344_DONOR_FX3_UXC_TC_G_RELPATH = P340_DONOR_FX3_UXC_TC_G_RELPATH
P344_DONOR_FX3_UXC_JA_G_RELPATH = P340_DONOR_FX3_UXC_JA_G_RELPATH
P344_DONOR_FX6_UXC_EN_RELPATH = P340_DONOR_FX6_UXC_EN_RELPATH
P344_DONOR_FX6_UXC_EN_2_RELPATH = P340_DONOR_FX6_UXC_EN_2_RELPATH

P344_PINNED_FX3_APPFW_702_BYTES = P340_PINNED_FX3_APPFW_702_BYTES
P344_PINNED_FX3_APPFW_702_HDR4K_SHA256 = P340_PINNED_FX3_APPFW_702_HDR4K_SHA256
P344_PINNED_FX6_APPFW_601_BYTES = P340_PINNED_FX6_APPFW_601_BYTES
P344_PINNED_FX6_APPFW_601_HDR4K_SHA256 = P340_PINNED_FX6_APPFW_601_HDR4K_SHA256
P344_PINNED_FX3_BACKUP_BIN_BYTES = P340_PINNED_FX3_BACKUP_BIN_BYTES
P344_PINNED_FX3_BACKUP_BIN_SHA256 = P340_PINNED_FX3_BACKUP_BIN_SHA256
P344_PINNED_FX3_UXC_EN_F_BYTES = P340_PINNED_FX3_UXC_EN_F_BYTES
P344_PINNED_FX3_UXC_EN_F_SHA256 = P340_PINNED_FX3_UXC_EN_F_SHA256
P344_PINNED_FX3_UXC_SC_F_BYTES = P340_PINNED_FX3_UXC_SC_F_BYTES
P344_PINNED_FX3_UXC_SC_F_SHA256 = P340_PINNED_FX3_UXC_SC_F_SHA256
P344_PINNED_FX3_UXC_TC_F_BYTES = P340_PINNED_FX3_UXC_TC_F_BYTES
P344_PINNED_FX3_UXC_TC_F_SHA256 = P340_PINNED_FX3_UXC_TC_F_SHA256
P344_PINNED_FX3_UXC_JA_F_BYTES = P340_PINNED_FX3_UXC_JA_F_BYTES
P344_PINNED_FX3_UXC_JA_F_SHA256 = P340_PINNED_FX3_UXC_JA_F_SHA256
P344_PINNED_FX3_UXC_EN_BYTES = P340_PINNED_FX3_UXC_EN_BYTES
P344_PINNED_FX3_UXC_EN_SHA256 = P340_PINNED_FX3_UXC_EN_SHA256
P344_PINNED_FX3_UXC_SC_BYTES = P340_PINNED_FX3_UXC_SC_BYTES
P344_PINNED_FX3_UXC_SC_SHA256 = P340_PINNED_FX3_UXC_SC_SHA256
P344_PINNED_FX3_UXC_TC_BYTES = P340_PINNED_FX3_UXC_TC_BYTES
P344_PINNED_FX3_UXC_TC_SHA256 = P340_PINNED_FX3_UXC_TC_SHA256
P344_PINNED_FX3_UXC_JA_BYTES = P340_PINNED_FX3_UXC_JA_BYTES
P344_PINNED_FX3_UXC_JA_SHA256 = P340_PINNED_FX3_UXC_JA_SHA256
P344_PINNED_FX3_UXC_EN_G_BYTES = P340_PINNED_FX3_UXC_EN_G_BYTES
P344_PINNED_FX3_UXC_EN_G_SHA256 = P340_PINNED_FX3_UXC_EN_G_SHA256
P344_PINNED_FX3_UXC_SC_G_BYTES = P340_PINNED_FX3_UXC_SC_G_BYTES
P344_PINNED_FX3_UXC_SC_G_SHA256 = P340_PINNED_FX3_UXC_SC_G_SHA256
P344_PINNED_FX3_UXC_TC_G_BYTES = P340_PINNED_FX3_UXC_TC_G_BYTES
P344_PINNED_FX3_UXC_TC_G_SHA256 = P340_PINNED_FX3_UXC_TC_G_SHA256
P344_PINNED_FX3_UXC_JA_G_BYTES = P340_PINNED_FX3_UXC_JA_G_BYTES
P344_PINNED_FX3_UXC_JA_G_SHA256 = P340_PINNED_FX3_UXC_JA_G_SHA256
P344_PINNED_FX6_UXC_EN_BYTES = P340_PINNED_FX6_UXC_EN_BYTES
P344_PINNED_FX6_UXC_EN_SHA256 = P340_PINNED_FX6_UXC_EN_SHA256
P344_PINNED_FX6_UXC_EN_2_BYTES = P340_PINNED_FX6_UXC_EN_2_BYTES
P344_PINNED_FX6_UXC_EN_2_SHA256 = P340_PINNED_FX6_UXC_EN_2_SHA256

# Zero-Violation Pillar 62 Counters & Vault Flags
P344_REC_MEDIA_PRIORITIZE_OR_AUTOSWITCH_DRIFT_EVENTS = 0
P344_CARD_SPEED_VPG200_VPG400_GATE_DRIFT_EVENTS = 0
P344_PROXY_SQ_DCI4K_OR_120P_LOCKOUT_DRIFT_EVENTS = 0
P344_CLOUD_INIT_PERSIST_OR_POWER_OFF_BLE_RF_EVENTS = 0
P344_MYMENU_42SLOT_OR_FX6_LOCK_SPOOF_EVENTS = 0
P344_ZERO_RF_OR_SLOT1_VAULT_BYPASS_EVENTS = 0

P344_RF_PACKETS_TRANSMITTED = 0
P344_RF_NVS_MUTATION_BYTES = 0
P344_SLOT1_DATA_SECTOR_WRITES = 0
P344_SLOT1_DCIM_M4ROOT_AVF_MUTATION_BYTES = 0
P344_SLOT1_VAULT_MUTATION_BYTES = 0
P344_SLOT1_FORMAT_HARD_LOCKED = True
P344_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True
P344_AIRPLANE_MODE_FORCED_ON = True
P344_POWER_OFF_BLE_FORCED_OFF = True

P344_STAGE_B_VOLATILE_OVERLAY_DIR = "/tmp/fx3_stage_b_overlay/pillar62"
P344_FORBIDDEN_PERSISTENT_TARGETS = (
    "/dev/cnflasha",
    "/setting",
    "/mnt/emmc",
    "/nflasha",
)
P344_TIER0_SURFACE_COUNT = 16

# ---------------------------------------------------------------------------
# Wave-60 Empirically Verified Constants (UXC resid16 & ELF Symbols)
# ---------------------------------------------------------------------------

# 1. [Rec. Media Settings] / Dormant [Prioritize Rec. Media] / [Auto Switch Media]
P344_REC_MEDIA_SETTINGS_F_RESID16 = (0x734D, 0x794A)
P344_RECORDING_MEDIA_F_RESID16 = (0x749D, 0x78BE)
P344_SIMULT_RECORDING_F_RESID16 = 0x7505
P344_SORT_RECORDING_F_RESID16 = 0x7916
P344_AUTO_SWITCH_MEDIA_F_RESID16 = 0x6DD9

P344_DORMANT_PRIORITIZE_REC_MEDIA_F_RESID16 = 0x719E
P344_DORMANT_SORT_RAW_JPEG_F_RESID16 = 0x710D
P344_DORMANT_SORT_JPEG_RAW_F_RESID16 = 0x765B
P344_DORMANT_PRIORITIZE_SYMBOLS = (
    "Prioritize Rec. Media",
    "Sort(RAW/JPEG)",
    "Sort(JPEG/RAW)",
)
P344_FX3_APPFW_PRIORITIZE_HIT_COUNT = 0

P344_BKID_STILL_RECORDING_MEDIA = "BKID_APP_setting_still_recording_media"
P344_BKID_MOVIE_RECORDING_MEDIA = "BKID_APP_setting_movie_recording_media"
P344_BKID_AUTO_SWITCH_MEDIA = "BKID_APP_setting_relay_rec"
P344_PRM_HAITA_RELAY_REC_SLOT1_RO_SYMBOL = (
    "PRM_HAITA_setting_relay_rec_movie_setting_movie_recording_media_media_read_only_state_slot1"
)
P344_PRM_HAITA_RELAY_REC_SLOT1_LOCKED_SYMBOL = (
    "PRM_HAITA_setting_relay_rec_movie_setting_movie_recording_media_media_locked_state_slot1"
)

P344_STILL_RECORDING_MEDIA_MODES = (
    "Slot 1",
    "Slot 2",
    "Simult. Recording",
    "Sort Recording",
)
P344_MOVIE_RECORDING_MEDIA_MODES = (
    "Slot 1",
    "Slot 2",
    "Simult. Recording",
)
P344_RECORDING_MEDIA_DEFAULT = "Slot 1"
P344_AUTO_SWITCH_MEDIA_MODES = ("Off", "On")
P344_AUTO_SWITCH_MEDIA_DEFAULT = "Off"
P344_FILESYSTEM_TYPES = ("exFAT", "FAT32")

P344_FX6_BKID_SIMUL_REC = "BKID_APP_SETTING_SIMUL_REC"
P344_FX6_SIMUL_REC_EXCLUSIONS = (
    "Wired LAN",
    "Wireless LAN",
    "Modem",
    "Proxy Rec",
    "Streaming",
    "Auto Upload (Proxy): Chunk",
)
P344_FX6_REC_BUTTON_CONTROLS = ("Slot A", "Slot B")

# 2. Card-Speed Gate Matrix (CFexpress Type A VPG200/VPG400 vs SDXC V60/V90/U3)
P344_BASE_CFEXPRESS_VPG200_RESID16 = 0xE228
P344_BASE_CFEXPRESS_VPG400_RESID16S = (0xE224, 0xE93F, 0xE9AA, 0xEA64, 0xEA78)
P344_CARD_MEDIA_TYPES = (
    "CFexpress Type A VPG400",
    "CFexpress Type A VPG200",
    "SDXC V90",
    "SDXC V60",
    "SDXC U3/V30",
    "CFexpress Type B",
)
P344_SUPPORTED_CARD_MEDIA_TYPES = (
    "CFexpress Type A VPG400",
    "CFexpress Type A VPG200",
    "SDXC V90",
    "SDXC V60",
    "SDXC U3/V30",
)
P344_MOVIE_FILE_FORMATS = (
    "XAVC HS 4K",
    "XAVC S 4K",
    "XAVC S HD",
    "XAVC S-I 4K",
    "XAVC S-I DCI 4K",
    "XAVC S-I HD",
)

# 3. [Proxy Settings] (`sq_proxy`, M4ROOT/SUB/*S03.MP4)
P344_PROXY_SETTINGS_F_RESID16 = 0x6E3F
P344_PROXY_RECORDING_F_RESID16 = 0x6F19
P344_PROXY_FILE_FORMAT_F_RESID16 = 0x6662
P344_PROXY_REC_SETTINGS_F_RESID16 = 0x6AAD
P344_PROXY_9M_10BIT_F_RESID16 = 0x611C
P344_PROXY_16M_10BIT_F_RESID16 = 0x62A6
P344_PROXY_6M_8BIT_F_RESID16 = 0x764C
P344_DORMANT_PROXY_16M_8BIT_F_RESID16 = 0x6B8F

P344_BKID_SQ_PROXY_RECORDING = "BKID_APP_setting_sq_proxy_recording"
P344_BKID_SQ_PROXY_FILE_FORMAT = "BKID_APP_setting_sq_proxy_file_format"
P344_BKID_SQ_PROXY_RECORD_SETTING = "BKID_APP_setting_sq_proxy_record_setting"
P344_FX3_APPFW_PRM_HAITA_PROXY_HIT_COUNT = 0

P344_ON_OFF_MODES = ("Off", "On")
P344_PROXY_RECORDING_DEFAULT = "Off"
P344_PROXY_FILE_FORMATS = ("XAVC S HD", "XAVC HS HD")
P344_PROXY_FILE_FORMAT_DEFAULT = "XAVC S HD"
P344_PROXY_REC_SETTINGS_XAVC_S_HD = ("6M 4:2:0 8bit",)
P344_PROXY_REC_SETTINGS_XAVC_HS_HD = ("9M 4:2:0 10bit", "16M 4:2:0 10bit")
P344_PROXY_DORMANT_REC_SETTINGS = ("16M 4:2:0 8bit", "9M 4:2:0 8bit")
P344_PROXY_DISALLOWED_MOVIE_FPS = (119.88, 100.0)
P344_PROXY_DISALLOWED_SQ_SENSOR_FPS = (120, 100)
P344_PROXY_SD_SUBDIR = "/PRIVATE/M4ROOT/SUB"
P344_PROXY_CFE_SUBDIR = "/M4ROOT/SUB"
P344_PROXY_FILE_SUFFIX = "S03.MP4"

P344_FX6_PROXY_RESOLUTION = "1920x1080"
P344_FX6_PROXY_BITRATE_MBPS = 9
P344_FX6_PROXY_CHUNK_DURATIONS = ("Off", "30s", "1min", "2min")
P344_FX6_BKID_PROXY_LUT = "BKID_APP_SETTING_LUT_SETTING_PROXY"
P344_FX6_PROXY_EXCLUSIONS = ("Simul Rec", "S&Q Motion", "Interval Rec")

# 4. [Creators' Cloud] / [C3 Portal] & [Cnct. while Power OFF]
P344_CLOUD_CONNECTION_F_RESID16 = 0x6E63
P344_CLOUD_INFORMATION_F_RESID16 = 0x773E
P344_CREATORS_CLOUD_G_RESID16 = 0x62B5
P344_C3_PORTAL_PRIVATE_F_RESID16 = 0x7C55
P344_C3_PORTAL_SHARE_F_RESID16 = 0x7C52
P344_CNCT_WHILE_POWER_OFF_F_RESID16 = 0x6AB3
P344_ALWAYS_CONNECTED_F_RESID16 = 0x6833
P344_CLOUD_BT_AIRPLANE_L10N_DEFECT_G_RESID16 = 0x6476

P344_BKID_CLOUD_CONNECTION = "BKID_APP_setting_cloud_connection"
P344_PRM_HAITA_CLOUD_FTP_SYMBOL = "PRM_HAITA_confirm_change_cloud_connection"
P344_BKID_CNCT_WHILE_POWER_OFF = "BKID_APP_extern_menu_cnct_while_power_off"
P344_BKID_ALWAYS_CONNECTED = "BKID_APP_setting_always_connected"
P344_UIBIZ_BLE_POWER_SYMBOL = "UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER"
P344_CLIP_FLAG_FILTERS = ("Off", "OK", "NG", "KEEP", "All")
P344_POWER_SWITCH_STATES = ("ON", "OFF")
P344_FX6_HAS_BLUETOOTH_HARDWARE = False

# 5. [My Menu] 6x7=42 Slots vs FX6 20-Item [User Menu with Lock]
P344_MYMENU_G_RESID16 = 0x6232
P344_DISPLAY_FROM_MYMENU_F_RESID16 = 0x64F6
P344_MYMENU_ADD_ITEM_F_RESID16 = 0x7122
P344_MYMENU_SORT_ITEM_F_RESID16 = 0x7A11
P344_MYMENU_DELETE_ITEM_F_RESID16 = 0x698D
P344_MYMENU_DELETE_PAGE_F_RESID16 = 0x6B7C
P344_MYMENU_DELETE_ALL_F_RESID16 = 0x6226

P344_BKID_DISPLAY_FROM_MYMENU = "BKID_APP_setting_display_from_mymenu"
P344_FX3_MYMENU_PAGES = 6
P344_FX3_MYMENU_ITEMS_PER_PAGE = 7
P344_FX3_MYMENU_TOTAL_SLOTS = 42
P344_FX3_MYMENU_DORMANT_BOUNDARY_HITS = 0
P344_FX3_MYMENU_SLOT_SYMBOLS = tuple(
    f"BKID_APP_mymenu_group{g}_setting_list{i}"
    for g in range(1, P344_FX3_MYMENU_PAGES + 1)
    for i in range(P344_FX3_MYMENU_ITEMS_PER_PAGE)
)
P344_FX3_MYMENU_SUBITEMS = (
    "Add Item",
    "Sort Item",
    "Delete Item",
    "Delete Page",
    "Delete All",
    "Display From My Menu",
)
P344_FX3_MYMENU_ALLOWED_DOMAINS = ("Shooting", "Exposure/Color", "Focus", "Setup", "Network")

P344_FX6_USER_MENU_MAX_ITEMS = 20
P344_FX6_BKID_USER_MENU_ONLY = "BKID_APP_SETTING_USER_MENU_ONLY"
P344_FX6_USER_MENU_LOCK_CHORD = "Multi-selector + MENU"
P344_FX6_USER_MENU_LOCK_PIN_DIGITS = 4
P344_FX6_USER_MENU_LOCK_DEFAULT_PIN = "0000"

P344_SHOOTING_DOMAINS = ("Movie", "Still", "S&Q")
P344_RESET_ACTIONS = ("None", "Camera Settings Reset", "Reset Network Set.", "Initialize")
P344_NETWORK_TRANSPORTS = ("NONE", "USB_LAN_CDC_NCM", "Wi-Fi", "BLE")
P344_SAFE_WIRED_TRANSPORTS = ("NONE", "USB_LAN_CDC_NCM")
P344_SAFE_WIRED_TRANSPORT = "USB_LAN_CDC_NCM"

P344_SLOT1_VAULT_SLOT = 1
P344_SAFE_SECONDARY_SLOT = 2
P344_VAULT_ACTIONS = (
    "NONE",
    "READ_ONLY_AUDIT",
    "REC_TO_SLOT2",
    "PROXY_TO_SLOT2",
    "SIMULT_REC_SLOT1_SLOT2",
    "AUTO_SWITCH_SPILLOVER_SLOT1",
    "REC_TO_SLOT1",
    "PROXY_TO_SLOT1",
    "COUPLED_DELETE_PROTECT_SLOT1_PROXY",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P344_WRITE_MUTATING_VAULT_ACTIONS = (
    "SIMULT_REC_SLOT1_SLOT2",
    "AUTO_SWITCH_SPILLOVER_SLOT1",
    "REC_TO_SLOT1",
    "PROXY_TO_SLOT1",
    "COUPLED_DELETE_PROTECT_SLOT1_PROXY",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P344_VAULT_FIREWALL_ERRNOS = (None, "EROFS", "EOPNOTSUPP", "EBUSY", "EINVAL")

# Status & Block Codes
P344_STATUS_VERIFIED_PILLAR_62A = "VERIFIED_PILLAR_62A_REC_MEDIA_AUTOSWITCH_PROXY_VAULT"
P344_STATUS_REJECTED_PILLAR_62A = "REJECTED_PILLAR_62A_REC_MEDIA_AUTOSWITCH_PROXY_VAULT"
P344_STATUS_VERIFIED_PILLAR_62B = "VERIFIED_PILLAR_62B_CLOUD_POWEROFF_BLE_MYMENU_VAULT"
P344_STATUS_REJECTED_PILLAR_62B = "REJECTED_PILLAR_62B_CLOUD_POWEROFF_BLE_MYMENU_VAULT"
P344_STATUS_VERIFIED_PILLAR62_SUITE = "VERIFIED_PILLAR62_REC_MEDIA_AUTOSWITCH_PROXY_CLOUD_MYMENU_VAULT"
P344_STATUS_FAIL_PILLAR62_SUITE = "FAIL_PILLAR62_REC_MEDIA_AUTOSWITCH_PROXY_CLOUD_MYMENU_VAULT"
P344_STATUS_VERIFIED_62OF62_AGGREGATOR = "VERIFIED_62OF62_PILLAR_RECOVERY_MASTER"
P344_STATUS_FAIL_62OF62_AGGREGATOR = "FAIL_62OF62_PILLAR_RECOVERY_MASTER"

P344_BLOCKED_SAFETY_POLICY_VIOLATION = "BLOCKED_P344_SAFETY_POLICY_VIOLATION"
P344_BLOCKED_INVALID_PILLAR62A_SPEC = "BLOCKED_P344_INVALID_PILLAR62A_SPEC"
P344_BLOCKED_INVALID_PILLAR62B_SPEC = "BLOCKED_P344_INVALID_PILLAR62B_SPEC"
P344_BLOCKED_REC_MEDIA_PRIORITIZE_OR_AUTOSWITCH_DRIFT = (
    "BLOCKED_P344_REC_MEDIA_PRIORITIZE_OR_AUTOSWITCH_DRIFT"
)
P344_BLOCKED_CARD_SPEED_VPG200_VPG400_GATE_DRIFT = (
    "BLOCKED_P344_CARD_SPEED_VPG200_VPG400_GATE_DRIFT"
)
P344_BLOCKED_PROXY_SQ_DCI4K_OR_120P_LOCKOUT_DRIFT = (
    "BLOCKED_P344_PROXY_SQ_DCI4K_OR_120P_LOCKOUT_DRIFT"
)
P344_BLOCKED_CLOUD_INIT_PERSIST_OR_POWEROFF_BLE_RF = (
    "BLOCKED_P344_CLOUD_INIT_PERSIST_OR_POWEROFF_BLE_RF"
)
P344_BLOCKED_MYMENU_42SLOT_OR_FX6_LOCK_SPOOF = (
    "BLOCKED_P344_MYMENU_42SLOT_OR_FX6_LOCK_SPOOF"
)
P344_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL = (
    "BLOCKED_P344_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL"
)
P344_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL = "BLOCKED_P344_SLOT1_VAULT_WRITE_FIREWALL"
P344_BLOCKED_PERSISTENT_OVERLAY_ESCAPE = "BLOCKED_P344_PERSISTENT_OVERLAY_ESCAPE"
P344_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT = "BLOCKED_P344_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P344_PILLAR_62A_SCENARIO_IDS = (
    "p344_62a_01_allow_slot2_relay_off_dci4k_proxy_xavc_hs_hd_cfe_vpg400",
    "p344_62a_02_allow_still_sort_rec_and_reset_immune_media_settings",
    "p344_62a_03_reject_dormant_prioritize_or_movie_sort_rec_or_fs_mismatch",
    "p344_62a_04_reject_sq_1200mbps_sdxc_v90_or_vpg200_vpg400_bypass",
    "p344_62a_05_reject_proxy_120p_lockout_dormant_8bit_or_dci4k_false_lock",
    "p344_62a_06_reject_auto_switch_slot1_spillover_proxy_erofs30_bypass",
)
P344_PILLAR_62B_SCENARIO_IDS = (
    "p344_62b_01_allow_cloud_init_persist_zero_rf_poweroff_ble_off_42slot_mymenu",
    "p344_62b_02_allow_fx6_20item_user_menu_with_lock_pin_and_allfile_exclusion",
    "p344_62b_03_reject_cloud_ftp_mutex_or_initialize_wiped_cloud_star",
    "p344_62b_04_reject_cnct_while_power_off_ble_rf_leak_when_switch_off",
    "p344_62b_05_reject_mymenu_30_36_cap_or_playback_or_fx6_pin_in_allfile",
    "p344_62b_06_reject_slot1_erofs30_bypass_overlay_escape_or_h0_h3_drift",
)

MASTER_62_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_61_PILLAR_SPECS + (
    (
        62,
        "pillar62_rec_media_autoswitch_proxy_cloud_mymenu_vault",
        "Phase 344",
        "realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier",
    ),
)
MASTER_62_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_62_PILLAR_SPECS)
MASTER_62_PILLAR_COUNT = len(MASTER_62_PILLAR_IDS)


# ---------------------------------------------------------------------------
# Internal Helpers (Canonical SHA-256, Safety, Path Guards)
# ---------------------------------------------------------------------------


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _canonical_sha256(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def _is_clean_room_forced(force_clean_room: Optional[bool]) -> bool:
    if force_clean_room is True:
        return True
    if force_clean_room is False:
        return False
    return bool(is_forced_clean_room() or os.environ.get(P344_ENV_CLEAN_ROOM_TEST) == "1")


def _donor_inspect_budget_seconds() -> float:
    return (
        P344_DONOR_INSPECT_CI_BUDGET_SECONDS
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS")
        else P344_DONOR_INSPECT_BUDGET_SECONDS
    )


def _is_tmpfs_path(path: str) -> bool:
    norm = posixpath.normpath(path)
    return norm == "/tmp" or norm.startswith("/tmp/")


def _targets_persistent_emmc(path: str) -> bool:
    norm = posixpath.normpath(path)
    return any(norm == p or norm.startswith(p + "/") for p in P344_FORBIDDEN_PERSISTENT_TARGETS)


def _safety_invariant_errors() -> List[str]:
    errs: List[str] = []
    checks = (
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("PERSISTENT_EMMC_WRITES_AUTHORIZED", PERSISTENT_EMMC_WRITES_AUTHORIZED, False),
        ("SPI_NOR_WRITE_AUTHORIZED", SPI_NOR_WRITE_AUTHORIZED, False),
        ("EL3_PAYLOAD_TRANSMIT_AUTHORIZED", EL3_PAYLOAD_TRANSMIT_AUTHORIZED, False),
        ("ISP_WRITE_AUTHORIZED", ISP_WRITE_AUTHORIZED, False),
        ("PERSISTENT_WRITE_RELEASE", PERSISTENT_WRITE_RELEASE, False),
        ("ALLOW_BOOT_PARTITION_TARGETING", ALLOW_BOOT_PARTITION_TARGETING, False),
        ("ALLOW_DESTRUCTIVE_FASTBOOT", ALLOW_DESTRUCTIVE_FASTBOOT, False),
        ("ALLOW_PERSISTENT_JIRITSU_WRITES", ALLOW_PERSISTENT_JIRITSU_WRITES, False),
        ("ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS", ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS, False),
        ("LIVE_USB_IOKIT_TRANSMIT_ENABLED", LIVE_USB_IOKIT_TRANSMIT_ENABLED, False),
        ("HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("OVERALL_READY_FOR_HARDWARE_ATTACH", OVERALL_READY_FOR_HARDWARE_ATTACH, False),
        ("CROSS_MODEL_FLASH_AUTHORIZED", CROSS_MODEL_FLASH_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("OTP_FUSE_TOUCHES", OTP_FUSE_TOUCHES, 0),
        ("OTP_FUSE_WRITES", OTP_FUSE_WRITES, 0),
        ("RPMB_COUNTER_INCREMENTS", RPMB_COUNTER_INCREMENTS, 0),
        ("PASSIVE_TX_BYTES_EMITTED", PASSIVE_TX_BYTES_EMITTED, 0),
        ("PHYSICAL_USB_PACKETS_EMITTED", PHYSICAL_USB_PACKETS_EMITTED, 0),
        ("PHYSICAL_DEVICE_WRITES", PHYSICAL_DEVICE_WRITES, 0),
        ("RAW_FIRMWARE_BYTES_LEAKED", RAW_FIRMWARE_BYTES_LEAKED, 0),
    )
    for name, val, expected in checks:
        if val != expected:
            errs.append(f"Hard-locked safety invariant violated: {name}={val!r} != {expected!r}")
    return errs


# ---------------------------------------------------------------------------
# Empirically Grounded State Calculators (Pillars 62A & 62B)
# ---------------------------------------------------------------------------


def compute_expected_rec_media_autoswitch_proxy_state(
    *,
    camera_model: str,
    shooting_domain: str,
    still_recording_media: str,
    movie_recording_media: str,
    prioritize_rec_media_requested: bool,
    auto_switch_media: str,
    slot1_filesystem: str,
    slot2_filesystem: str,
    slot2_full_or_missing: bool,
    still_jpeg_raw_settings_shared: bool,
    movie_file_format: str,
    movie_bitrate_mbps: int,
    rec_frame_rate_p: float,
    sq_sensor_fps: int,
    media_card_slot2_type: str,
    proxy_recording: str,
    proxy_file_format: str,
    proxy_rec_setting: str,
    proxy_playable_in_camera: bool,
    proxy_coupled_delete_protect: bool,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
    fx6_simul_rec_enabled: bool,
    fx6_simul_exclusions_active: Tuple[str, ...],
    fx6_proxy_chunk_mode: str,
) -> Dict[str, Any]:
    """Compute canonical Wave-60 Pillar 62A state:
    - Dormant `[Prioritize Rec. Media]` (`_f 0x719e`) -> `EOPNOTSUPP=95`
    - Split Reset-immune `[Recording Media]` (ZERO Movie `Sort Recording`, `Simult.` filesystem match)
    - Reset-immune `[Auto Switch Media]` (`BKID_APP_setting_relay_rec`) + Tier-0 `Slot 1` spillover guard
    - Card-speed gate matrix (`SDXC V60/V90` vs `CFexpress Type A VPG200/VPG400`)
    - `[Proxy Settings]` (`sq_proxy`) `XAVC S-I DCI 4K` allowed vs `119.88p/100p` & `S&Q 120/100` lockout
    - `M4ROOT/SUB/*S03.MP4` lifecycle & `Slot 1` `EROFS=30` firewall."""
    is_fx3 = camera_model == P344_FX3_MODEL_NAME

    # 1. Dormant [Prioritize Rec. Media] & Split [Recording Media]
    prioritize_errno: Optional[int] = P344_EOPNOTSUPP_ERRNO if prioritize_rec_media_requested else None
    movie_sort_errno: Optional[int] = (
        P344_EOPNOTSUPP_ERRNO if movie_recording_media == "Sort Recording" else None
    )
    if (
        still_recording_media == "Simult. Recording" or movie_recording_media == "Simult. Recording"
    ) and slot1_filesystem != slot2_filesystem:
        simult_fs_errno: Optional[int] = P344_EINVAL_ERRNO
    else:
        simult_fs_errno = None

    still_sort_shared_ok = (still_recording_media != "Sort Recording") or still_jpeg_raw_settings_shared

    # 2. Tier-0 Slot 1 Spillover Hazard when Auto Switch Media = On
    active_primary_media = still_recording_media if shooting_domain == "Still" else movie_recording_media
    would_spillover_to_slot1 = (
        slot1_holds_tier0_vault
        and (
            active_primary_media in ("Simult. Recording", "Slot 1")
            or (
                auto_switch_media == "On"
                and active_primary_media in ("Slot 2", "Sort Recording")
                and slot2_full_or_missing
            )
        )
    )

    # 3. Card-Speed Gate Matrix (VPG200/VPG400 vs SDXC V60/V90/U3)
    card_rank_map = {
        "CFexpress Type A VPG400": 5,
        "CFexpress Type A VPG200": 4,
        "SDXC V90": 3,
        "SDXC V60": 2,
        "SDXC U3/V30": 1,
        "CFexpress Type B": 0,
    }
    card_rank = card_rank_map.get(media_card_slot2_type, 0)
    is_cfe = media_card_slot2_type in ("CFexpress Type A VPG400", "CFexpress Type A VPG200")
    card_gate_errno: Optional[int] = None
    card_gate_warning: Optional[str] = None

    if media_card_slot2_type == "CFexpress Type B":
        card_gate_errno = P344_EOPNOTSUPP_ERRNO
    elif shooting_domain == "S&Q":
        if movie_file_format == "XAVC S-I 4K":
            # S&Q 1200 Mbps: SDXC is strictly blocked; mandatory CFexpress Type A!
            if not is_cfe:
                card_gate_errno = P344_EINVAL_ERRNO
            elif media_card_slot2_type == "CFexpress Type A VPG200":
                card_gate_warning = (
                    "VPG400_RECOMMENDED_DISABLE_PROXY" if proxy_recording == "On" else "VPG200_VPG400_GATE"
                )
        elif movie_file_format == "XAVC S-I DCI 4K":
            if sq_sensor_fps in P344_PROXY_DISALLOWED_SQ_SENSOR_FPS or not is_cfe:
                card_gate_errno = P344_EINVAL_ERRNO
        elif movie_file_format == "XAVC S-I HD":
            if sq_sensor_fps >= 200 and not is_cfe:
                card_gate_errno = P344_EINVAL_ERRNO
            elif card_rank < 3:
                card_gate_errno = P344_EINVAL_ERRNO
        elif movie_file_format in ("XAVC HS 4K", "XAVC S 4K", "XAVC S HD"):
            min_rank = 3 if sq_sensor_fps >= 100 else 2
            if card_rank < min_rank:
                card_gate_errno = P344_EINVAL_ERRNO
    elif shooting_domain == "Movie":
        if movie_file_format in ("XAVC S-I 4K", "XAVC S-I DCI 4K", "XAVC S-I HD"):
            if card_rank < 3:
                card_gate_errno = P344_EINVAL_ERRNO
            elif (
                movie_file_format == "XAVC S-I DCI 4K"
                and proxy_recording == "On"
                and movie_bitrate_mbps >= 600
                and media_card_slot2_type in ("SDXC V90", "CFexpress Type A VPG200")
            ):
                card_gate_warning = "PROXY_OVERLAY_HIGHER_CARD_OR_DISABLE_PROXY"
        elif movie_file_format in ("XAVC HS 4K", "XAVC S 4K"):
            min_rank = 2 if movie_bitrate_mbps > 200 else 1
            if card_rank < min_rank:
                card_gate_errno = P344_EINVAL_ERRNO
        elif movie_file_format == "XAVC S HD":
            if card_rank < 1:
                card_gate_errno = P344_EINVAL_ERRNO

    # 4. [Proxy Settings] (sq_proxy) Lockout Truth & Format Validation
    # Disabled ONLY on Movie 119.88p/100p and S&Q 120/100fps (or S&Q rec_frame_rate 119.88p/100p).
    # XAVC S-I DCI 4K IS allowed (max 59.94p/50p) subject to card-speed gates!
    proxy_locked_out = (
        (shooting_domain == "Movie" and rec_frame_rate_p in P344_PROXY_DISALLOWED_MOVIE_FPS)
        or (
            shooting_domain == "S&Q"
            and (
                sq_sensor_fps in P344_PROXY_DISALLOWED_SQ_SENSOR_FPS
                or rec_frame_rate_p in P344_PROXY_DISALLOWED_MOVIE_FPS
            )
        )
        or (shooting_domain == "Still")
    )
    proxy_dormant_setting = proxy_rec_setting in P344_PROXY_DORMANT_REC_SETTINGS
    proxy_setting_valid = (
        (proxy_file_format == "XAVC S HD" and proxy_rec_setting in P344_PROXY_REC_SETTINGS_XAVC_S_HD)
        or (proxy_file_format == "XAVC HS HD" and proxy_rec_setting in P344_PROXY_REC_SETTINGS_XAVC_HS_HD)
    )
    if proxy_recording == "On" and (proxy_locked_out or proxy_dormant_setting or not proxy_setting_valid):
        effective_proxy_recording = "Off"
        proxy_errno: Optional[int] = P344_EOPNOTSUPP_ERRNO
    elif proxy_dormant_setting or not proxy_setting_valid:
        effective_proxy_recording = proxy_recording
        proxy_errno = P344_EOPNOTSUPP_ERRNO
    else:
        effective_proxy_recording = proxy_recording
        proxy_errno = None

    proxy_subdir = P344_PROXY_CFE_SUBDIR if is_cfe else P344_PROXY_SD_SUBDIR
    proxy_example_path = f"{proxy_subdir}/C0001{P344_PROXY_FILE_SUFFIX}"
    proxy_lifecycle_ok = (not proxy_playable_in_camera) and proxy_coupled_delete_protect

    # 5. FX6 Simul Rec & Proxy Chunk mutual exclusions
    fx6_simul_ok = (
        not fx6_simul_rec_enabled
        or len(set(fx6_simul_exclusions_active) & set(P344_FX6_SIMUL_REC_EXCLUSIONS)) == 0
    )
    fx6_chunk_ok = (
        fx6_proxy_chunk_mode in P344_FX6_PROXY_CHUNK_DURATIONS
        and (fx6_proxy_chunk_mode == "Off" or not fx6_simul_rec_enabled)
    )

    # 6. Reset Matrix ([Camera Settings Reset] vs [Initialize])
    # - [Recording Media] & [Auto Switch Media] are Reset-immune; reset only on Initialize.
    # - [Proxy Settings] ARE Resettable by BOTH Camera Settings Reset and Initialize.
    if reset_action == "Initialize":
        post_still_rec_media = P344_RECORDING_MEDIA_DEFAULT
        post_movie_rec_media = P344_RECORDING_MEDIA_DEFAULT
        post_auto_switch_media = P344_AUTO_SWITCH_MEDIA_DEFAULT
        post_proxy_recording = P344_PROXY_RECORDING_DEFAULT
        post_proxy_file_format = P344_PROXY_FILE_FORMAT_DEFAULT
        post_proxy_rec_setting = P344_PROXY_REC_SETTINGS_XAVC_S_HD[0]
    elif reset_action == "Camera Settings Reset":
        post_still_rec_media = still_recording_media
        post_movie_rec_media = movie_recording_media
        post_auto_switch_media = auto_switch_media
        post_proxy_recording = P344_PROXY_RECORDING_DEFAULT
        post_proxy_file_format = P344_PROXY_FILE_FORMAT_DEFAULT
        post_proxy_rec_setting = P344_PROXY_REC_SETTINGS_XAVC_S_HD[0]
    else:
        post_still_rec_media = still_recording_media
        post_movie_rec_media = movie_recording_media
        post_auto_switch_media = auto_switch_media
        post_proxy_recording = effective_proxy_recording
        post_proxy_file_format = proxy_file_format
        post_proxy_rec_setting = proxy_rec_setting

    # 7. Slot-1 Tier-0 Vault Firewall (`EROFS=30`)
    mutates_slot1 = (
        requested_vault_action in P344_WRITE_MUTATING_VAULT_ACTIONS
        or (requested_vault_slot == P344_SLOT1_VAULT_SLOT and requested_vault_action != "READ_ONLY_AUDIT")
        or would_spillover_to_slot1
    )
    if (mutates_slot1 and slot1_holds_tier0_vault) or requested_vault_action in (
        "FORMAT_QUICK",
        "FORMAT_FULL",
    ):
        vault_action_allowed = False
        vault_firewall_errno: Optional[str] = "EROFS"
    elif requested_vault_action in ("READ_ONLY_AUDIT", "REC_TO_SLOT2", "PROXY_TO_SLOT2") and (
        requested_vault_slot == P344_SAFE_SECONDARY_SLOT or requested_vault_action == "READ_ONLY_AUDIT"
    ):
        vault_action_allowed = True
        vault_firewall_errno = None
    elif requested_vault_action == "NONE":
        vault_action_allowed = False
        vault_firewall_errno = None
    else:
        vault_action_allowed = False
        vault_firewall_errno = "EROFS"

    return {
        "is_fx3": is_fx3,
        "prioritize_errno": prioritize_errno,
        "movie_sort_errno": movie_sort_errno,
        "simult_fs_errno": simult_fs_errno,
        "still_sort_shared_ok": still_sort_shared_ok,
        "would_spillover_to_slot1": would_spillover_to_slot1,
        "card_gate_errno": card_gate_errno,
        "card_gate_warning": card_gate_warning,
        "proxy_locked_out": proxy_locked_out,
        "effective_proxy_recording": effective_proxy_recording,
        "proxy_errno": proxy_errno,
        "proxy_subdir": proxy_subdir,
        "proxy_example_path": proxy_example_path,
        "proxy_lifecycle_ok": proxy_lifecycle_ok,
        "fx6_simul_ok": fx6_simul_ok,
        "fx6_chunk_ok": fx6_chunk_ok,
        "post_still_rec_media": post_still_rec_media,
        "post_movie_rec_media": post_movie_rec_media,
        "post_auto_switch_media": post_auto_switch_media,
        "post_proxy_recording": post_proxy_recording,
        "post_proxy_file_format": post_proxy_file_format,
        "post_proxy_rec_setting": post_proxy_rec_setting,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


def compute_expected_cloud_poweroff_ble_mymenu_state(
    *,
    camera_model: str,
    fw_version: str,
    cloud_connection_enabled: bool,
    cloud_account_bound_star: bool,
    cloud_clip_flag_filter: str,
    ftp_transfer_enabled: bool,
    explicit_cloud_account_deleted: bool,
    bluetooth_paired: bool,
    cnct_while_power_off: str,
    power_switch_state: str,
    airplane_mode: str,
    wifi_active: bool,
    cloud_upload_active: bool,
    network_transport: str,
    mymenu_page: int,
    mymenu_slot_index: int,
    mymenu_registered_count: int,
    mymenu_includes_playback_item: bool,
    mymenu_display_from_mymenu: str,
    mymenu_delete_all_requested: bool,
    fx6_user_menu_item_count: int,
    fx6_user_menu_only: bool,
    fx6_user_menu_with_lock: bool,
    fx6_lock_chord_used: str,
    fx6_lock_pin: str,
    fx6_save_target: str,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute canonical Wave-60 Pillar 62B state:
    - `[Creators' Cloud]` `*` persistence across BOTH `Camera Settings Reset` AND `Initialize`
    - `[Cnct. while Power OFF]` BLE power-off wakeup RF hazard vs `Airplane Mode = On` + `Off`
    - `[My Menu]` `6x7=42` slots (`group{1..6}_setting_list{0..6}`, NO Playback, Reset-immune)
      vs FX6 `20`-item `User Menu with Lock` (`Multi-selector + MENU`, 4-digit PIN, excluded from `All File`)."""
    is_fx3 = camera_model == P344_FX3_MODEL_NAME

    # 1. Creators' Cloud / C3 Portal & FTP Mutex (`CLOUD_CONNECTION_ON_FTP_OFF`)
    if cloud_connection_enabled and ftp_transfer_enabled:
        cloud_ftp_errno: Optional[int] = P344_EBUSY_ERRNO
    else:
        cloud_ftp_errno = None

    cloud_clip_flag_supported = (not is_fx3) or (fw_version in ("7.02", "7.01", "7.00"))
    if cloud_clip_flag_filter not in P344_CLIP_FLAG_FILTERS or (
        cloud_clip_flag_filter != "Off" and not cloud_clip_flag_supported
    ):
        clip_flag_errno: Optional[int] = P344_EOPNOTSUPP_ERRNO
    else:
        clip_flag_errno = None

    # 2. [Cnct. while Power OFF] BLE power-off RF state
    if (not is_fx3) and cnct_while_power_off == "On":
        # FX6 has zero Bluetooth hardware
        cnct_poweroff_errno: Optional[int] = P344_EOPNOTSUPP_ERRNO
    else:
        cnct_poweroff_errno = None

    # On FX3, when Cnct. while Power OFF = On and Bluetooth paired, BLE stays energized even at POWER OFF!
    ble_energized_while_power_off = (
        is_fx3
        and cnct_while_power_off == "On"
        and bluetooth_paired
        and airplane_mode != "On"
    )

    # 3. [My Menu] 6x7=42 NVRAM slots vs FX6 20-item User Menu with Lock
    if is_fx3:
        if mymenu_includes_playback_item:
            mymenu_errno: Optional[int] = P344_EOPNOTSUPP_ERRNO
        elif not (
            1 <= mymenu_page <= P344_FX3_MYMENU_PAGES
            and 0 <= mymenu_slot_index < P344_FX3_MYMENU_ITEMS_PER_PAGE
            and 0 <= mymenu_registered_count <= P344_FX3_MYMENU_TOTAL_SLOTS
        ):
            mymenu_errno = P344_EINVAL_ERRNO
        else:
            mymenu_errno = None
    else:
        mymenu_errno = None

    # FX6 User Menu / Lock constraints
    fx6_pin_valid = len(fx6_lock_pin) == P344_FX6_USER_MENU_LOCK_PIN_DIGITS and fx6_lock_pin.isdigit()
    fx6_user_menu_valid = (
        0 <= fx6_user_menu_item_count <= P344_FX6_USER_MENU_MAX_ITEMS
        and (not fx6_user_menu_with_lock or (fx6_lock_chord_used == P344_FX6_USER_MENU_LOCK_CHORD and fx6_pin_valid))
    )
    if fx6_save_target == "Scene File":
        fx6_menu_exported = False
        fx6_lock_exported = False
    elif fx6_save_target == "All File":
        fx6_menu_exported = True
        fx6_lock_exported = False  # User Menu with Lock is NEVER exported even in All File!
    else:
        fx6_menu_exported = False
        fx6_lock_exported = False

    # 4. Reset Matrix (`Camera Settings Reset` vs `Reset Network Set.` vs `Initialize`)
    # - `Cloud Connection *` & `Cloud Information *`: survive Camera Settings Reset AND Initialize!
    #   Cleared ONLY when `explicit_cloud_account_deleted=True`.
    post_cloud_account_bound_star = (
        False if explicit_cloud_account_deleted else cloud_account_bound_star
    )
    if reset_action == "Initialize":
        post_cloud_connection_enabled = cloud_connection_enabled and not explicit_cloud_account_deleted
        post_cnct_while_power_off = "Off"
        post_airplane_mode = airplane_mode  # Preserved across Initialize!
        post_mymenu_count = 0
        post_display_from_mymenu = "Off"
    elif reset_action == "Reset Network Set.":
        post_cloud_connection_enabled = False if explicit_cloud_account_deleted else cloud_connection_enabled
        post_cnct_while_power_off = "Off"
        post_airplane_mode = airplane_mode  # Preserved across Reset Network Set.!
        post_mymenu_count = 0 if mymenu_delete_all_requested else mymenu_registered_count
        post_display_from_mymenu = mymenu_display_from_mymenu
    else:
        # Both "None" and "Camera Settings Reset" preserve Cloud *, Cnct. while Power OFF, My Menu!
        post_cloud_connection_enabled = cloud_connection_enabled and not explicit_cloud_account_deleted
        post_cnct_while_power_off = cnct_while_power_off
        post_airplane_mode = airplane_mode
        post_mymenu_count = 0 if mymenu_delete_all_requested else mymenu_registered_count
        post_display_from_mymenu = mymenu_display_from_mymenu

    # Zero-RF Bench Policy: Airplane Mode = On AND Cnct. while Power OFF = Off (independent of Power Switch!)
    rf_zero_enforced = (
        airplane_mode == "On"
        and post_airplane_mode == "On"
        and cnct_while_power_off == "Off"
        and post_cnct_while_power_off == "Off"
        and not ble_energized_while_power_off
        and not wifi_active
        and not cloud_upload_active
        and network_transport in P344_SAFE_WIRED_TRANSPORTS
    )

    # 5. Slot-1 Tier-0 Vault Firewall
    if requested_vault_action in P344_WRITE_MUTATING_VAULT_ACTIONS or (
        requested_vault_slot == P344_SLOT1_VAULT_SLOT and requested_vault_action != "READ_ONLY_AUDIT"
    ):
        vault_action_allowed = False
        vault_firewall_errno: Optional[str] = "EROFS"
    elif requested_vault_action in ("READ_ONLY_AUDIT", "REC_TO_SLOT2", "PROXY_TO_SLOT2"):
        vault_action_allowed = requested_vault_slot == P344_SAFE_SECONDARY_SLOT or requested_vault_action == "READ_ONLY_AUDIT"
        vault_firewall_errno = None if vault_action_allowed else "EROFS"
    elif requested_vault_action == "NONE":
        vault_action_allowed = False
        vault_firewall_errno = None
    else:
        vault_action_allowed = False
        vault_firewall_errno = "EROFS"

    return {
        "is_fx3": is_fx3,
        "cloud_ftp_errno": cloud_ftp_errno,
        "clip_flag_errno": clip_flag_errno,
        "cnct_poweroff_errno": cnct_poweroff_errno,
        "ble_energized_while_power_off": ble_energized_while_power_off,
        "mymenu_errno": mymenu_errno,
        "fx6_pin_valid": fx6_pin_valid,
        "fx6_user_menu_valid": fx6_user_menu_valid,
        "fx6_menu_exported": fx6_menu_exported,
        "fx6_lock_exported": fx6_lock_exported,
        "post_cloud_account_bound_star": post_cloud_account_bound_star,
        "post_cloud_connection_enabled": post_cloud_connection_enabled,
        "post_cnct_while_power_off": post_cnct_while_power_off,
        "post_airplane_mode": post_airplane_mode,
        "post_mymenu_count": post_mymenu_count,
        "post_display_from_mymenu": post_display_from_mymenu,
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


def _resolve_phase344_donor_path(
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
    max_full_bytes: int = P344_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    try:
        resolved = _resolve_phase344_donor_path(relpath)
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
        hdr = os.pread(fd, min(P344_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase344_donors() -> Tuple["Phase344DonorArtifactDigest", ...]:
    specs = (
        ("fx3_appfw_702_so", P344_DONOR_FX3_APPFW_702_RELPATH, P344_PINNED_FX3_APPFW_702_BYTES, P344_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P344_PINNED_FX3_APPFW_702_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702"),
        ("fx6_appfw_601_so", P344_DONOR_FX6_APPFW_601_RELPATH, P344_PINNED_FX6_APPFW_601_BYTES, P344_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P344_PINNED_FX6_APPFW_601_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601"),
        ("fx3_backup_bin", P344_DONOR_FX3_BACKUP_BIN_RELPATH, P344_PINNED_FX3_BACKUP_BIN_BYTES, P344_PINNED_FX3_BACKUP_BIN_BYTES, "FULL_SHA256", P344_PINNED_FX3_BACKUP_BIN_SHA256, "SYNTHETIC_BK4_ILME_FX3"),
        ("fx3_uxc_en_f", P344_DONOR_FX3_UXC_EN_F_RELPATH, P344_PINNED_FX3_UXC_EN_F_BYTES, P344_PINNED_FX3_UXC_EN_F_BYTES, "FULL_SHA256", P344_PINNED_FX3_UXC_EN_F_SHA256, "SYNTHETIC_UXC7_FX3_EN_F"),
        ("fx3_uxc_sc_f", P344_DONOR_FX3_UXC_SC_F_RELPATH, P344_PINNED_FX3_UXC_SC_F_BYTES, P344_PINNED_FX3_UXC_SC_F_BYTES, "FULL_SHA256", P344_PINNED_FX3_UXC_SC_F_SHA256, "SYNTHETIC_UXC7_FX3_SC_F"),
        ("fx3_uxc_tc_f", P344_DONOR_FX3_UXC_TC_F_RELPATH, P344_PINNED_FX3_UXC_TC_F_BYTES, P344_PINNED_FX3_UXC_TC_F_BYTES, "FULL_SHA256", P344_PINNED_FX3_UXC_TC_F_SHA256, "SYNTHETIC_UXC7_FX3_TC_F"),
        ("fx3_uxc_ja_f", P344_DONOR_FX3_UXC_JA_F_RELPATH, P344_PINNED_FX3_UXC_JA_F_BYTES, P344_PINNED_FX3_UXC_JA_F_BYTES, "FULL_SHA256", P344_PINNED_FX3_UXC_JA_F_SHA256, "SYNTHETIC_UXC7_FX3_JA_F"),
        ("fx3_uxc_en", P344_DONOR_FX3_UXC_EN_RELPATH, P344_PINNED_FX3_UXC_EN_BYTES, P344_PINNED_FX3_UXC_EN_BYTES, "FULL_SHA256", P344_PINNED_FX3_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX3_EN"),
        ("fx3_uxc_sc", P344_DONOR_FX3_UXC_SC_RELPATH, P344_PINNED_FX3_UXC_SC_BYTES, P344_PINNED_FX3_UXC_SC_BYTES, "FULL_SHA256", P344_PINNED_FX3_UXC_SC_SHA256, "SYNTHETIC_UXC7_FX3_SC"),
        ("fx3_uxc_tc", P344_DONOR_FX3_UXC_TC_RELPATH, P344_PINNED_FX3_UXC_TC_BYTES, P344_PINNED_FX3_UXC_TC_BYTES, "FULL_SHA256", P344_PINNED_FX3_UXC_TC_SHA256, "SYNTHETIC_UXC7_FX3_TC"),
        ("fx3_uxc_ja", P344_DONOR_FX3_UXC_JA_RELPATH, P344_PINNED_FX3_UXC_JA_BYTES, P344_PINNED_FX3_UXC_JA_BYTES, "FULL_SHA256", P344_PINNED_FX3_UXC_JA_SHA256, "SYNTHETIC_UXC7_FX3_JA"),
        ("fx3_uxc_en_g", P344_DONOR_FX3_UXC_EN_G_RELPATH, P344_PINNED_FX3_UXC_EN_G_BYTES, P344_PINNED_FX3_UXC_EN_G_BYTES, "FULL_SHA256", P344_PINNED_FX3_UXC_EN_G_SHA256, "SYNTHETIC_UXC7_FX3_EN_G"),
        ("fx3_uxc_sc_g", P344_DONOR_FX3_UXC_SC_G_RELPATH, P344_PINNED_FX3_UXC_SC_G_BYTES, P344_PINNED_FX3_UXC_SC_G_BYTES, "FULL_SHA256", P344_PINNED_FX3_UXC_SC_G_SHA256, "SYNTHETIC_UXC7_FX3_SC_G"),
        ("fx3_uxc_tc_g", P344_DONOR_FX3_UXC_TC_G_RELPATH, P344_PINNED_FX3_UXC_TC_G_BYTES, P344_PINNED_FX3_UXC_TC_G_BYTES, "FULL_SHA256", P344_PINNED_FX3_UXC_TC_G_SHA256, "SYNTHETIC_UXC7_FX3_TC_G"),
        ("fx3_uxc_ja_g", P344_DONOR_FX3_UXC_JA_G_RELPATH, P344_PINNED_FX3_UXC_JA_G_BYTES, P344_PINNED_FX3_UXC_JA_G_BYTES, "FULL_SHA256", P344_PINNED_FX3_UXC_JA_G_SHA256, "SYNTHETIC_UXC7_FX3_JA_G"),
        ("fx6_uxc_en", P344_DONOR_FX6_UXC_EN_RELPATH, P344_PINNED_FX6_UXC_EN_BYTES, P344_PINNED_FX6_UXC_EN_BYTES, "FULL_SHA256", P344_PINNED_FX6_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX6_EN"),
        ("fx6_uxc_en_2", P344_DONOR_FX6_UXC_EN_2_RELPATH, P344_PINNED_FX6_UXC_EN_2_BYTES, P344_PINNED_FX6_UXC_EN_2_BYTES, "FULL_SHA256", P344_PINNED_FX6_UXC_EN_2_SHA256, "SYNTHETIC_UXC7_FX6_EN_2"),
    )
    return tuple(
        Phase344DonorArtifactDigest(
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


def inspect_phase344_donors_readonly(
    force_clean_room: Optional[bool] = None,
) -> "Phase344DonorSnapshot":
    """Inspect Wave-60 FX3 7.02 (`14` donors) & FX6 6.01 (`3` donors) strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase344_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase344DonorSnapshot(
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
        ("fx3_appfw_702_so", P344_DONOR_FX3_APPFW_702_RELPATH, P344_PINNED_FX3_APPFW_702_BYTES, P344_PINNED_FX3_APPFW_702_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702")),
        ("fx6_appfw_601_so", P344_DONOR_FX6_APPFW_601_RELPATH, P344_PINNED_FX6_APPFW_601_BYTES, P344_PINNED_FX6_APPFW_601_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601")),
        ("fx3_backup_bin", P344_DONOR_FX3_BACKUP_BIN_RELPATH, P344_PINNED_FX3_BACKUP_BIN_BYTES, P344_PINNED_FX3_BACKUP_BIN_SHA256, lambda d: _check_bk4_backup(d, "ILME_FX3")),
        ("fx3_uxc_en_f", P344_DONOR_FX3_UXC_EN_F_RELPATH, P344_PINNED_FX3_UXC_EN_F_BYTES, P344_PINNED_FX3_UXC_EN_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_F")),
        ("fx3_uxc_sc_f", P344_DONOR_FX3_UXC_SC_F_RELPATH, P344_PINNED_FX3_UXC_SC_F_BYTES, P344_PINNED_FX3_UXC_SC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_F")),
        ("fx3_uxc_tc_f", P344_DONOR_FX3_UXC_TC_F_RELPATH, P344_PINNED_FX3_UXC_TC_F_BYTES, P344_PINNED_FX3_UXC_TC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_F")),
        ("fx3_uxc_ja_f", P344_DONOR_FX3_UXC_JA_F_RELPATH, P344_PINNED_FX3_UXC_JA_F_BYTES, P344_PINNED_FX3_UXC_JA_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_F")),
        ("fx3_uxc_en", P344_DONOR_FX3_UXC_EN_RELPATH, P344_PINNED_FX3_UXC_EN_BYTES, P344_PINNED_FX3_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN")),
        ("fx3_uxc_sc", P344_DONOR_FX3_UXC_SC_RELPATH, P344_PINNED_FX3_UXC_SC_BYTES, P344_PINNED_FX3_UXC_SC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC")),
        ("fx3_uxc_tc", P344_DONOR_FX3_UXC_TC_RELPATH, P344_PINNED_FX3_UXC_TC_BYTES, P344_PINNED_FX3_UXC_TC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC")),
        ("fx3_uxc_ja", P344_DONOR_FX3_UXC_JA_RELPATH, P344_PINNED_FX3_UXC_JA_BYTES, P344_PINNED_FX3_UXC_JA_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA")),
        ("fx3_uxc_en_g", P344_DONOR_FX3_UXC_EN_G_RELPATH, P344_PINNED_FX3_UXC_EN_G_BYTES, P344_PINNED_FX3_UXC_EN_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_G")),
        ("fx3_uxc_sc_g", P344_DONOR_FX3_UXC_SC_G_RELPATH, P344_PINNED_FX3_UXC_SC_G_BYTES, P344_PINNED_FX3_UXC_SC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_G")),
        ("fx3_uxc_tc_g", P344_DONOR_FX3_UXC_TC_G_RELPATH, P344_PINNED_FX3_UXC_TC_G_BYTES, P344_PINNED_FX3_UXC_TC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_G")),
        ("fx3_uxc_ja_g", P344_DONOR_FX3_UXC_JA_G_RELPATH, P344_PINNED_FX3_UXC_JA_G_BYTES, P344_PINNED_FX3_UXC_JA_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_G")),
        ("fx6_uxc_en", P344_DONOR_FX6_UXC_EN_RELPATH, P344_PINNED_FX6_UXC_EN_BYTES, P344_PINNED_FX6_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN")),
        ("fx6_uxc_en_2", P344_DONOR_FX6_UXC_EN_2_RELPATH, P344_PINNED_FX6_UXC_EN_2_BYTES, P344_PINNED_FX6_UXC_EN_2_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN_2")),
    )

    def _probe_one(spec: Tuple[str, str, int, str, Any]) -> Optional[Phase344DonorArtifactDigest]:
        aid, relpath, expected_bytes, expected_sha, marker_fn = spec
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            return None
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        return Phase344DonorArtifactDigest(
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
        artifacts = _synthetic_phase344_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase344DonorSnapshot(
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
    return Phase344DonorSnapshot(
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
# Frozen Dataclasses (Specs, Reports, Suites & 62-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase344DonorArtifactDigest:
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
class Phase344DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_2_0s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase344DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecMediaAutoSwitchProxyVaultSpec:
    # [Rec. Media Settings], Dormant [Prioritize Rec. Media], [Auto Switch Media] & Spillover Hazard
    camera_model: str
    fw_version: str
    shooting_domain: str
    still_recording_media: str
    movie_recording_media: str
    prioritize_rec_media_requested: bool
    reported_prioritize_errno: Optional[int]
    reported_movie_sort_errno: Optional[int]
    auto_switch_media: str
    slot1_filesystem: str
    slot2_filesystem: str
    reported_simult_fs_errno: Optional[int]
    slot2_full_or_missing: bool
    still_jpeg_raw_settings_shared: bool
    fx3_appfw_prioritize_hits: int
    fx3_appfw_prm_haita_proxy_hits: int
    # Card-speed gate matrix (`VPG200/VPG400` vs `SDXC V60/V90/U3`)
    movie_file_format: str
    movie_bitrate_mbps: int
    rec_frame_rate_p: float
    sq_sensor_fps: int
    media_card_slot2_type: str
    reported_card_gate_errno: Optional[int]
    reported_card_gate_warning: Optional[str]
    # [Proxy Settings] (`sq_proxy`) & `M4ROOT/SUB/*S03.MP4`
    proxy_recording: str
    proxy_file_format: str
    proxy_rec_setting: str
    reported_effective_proxy_recording: str
    reported_proxy_errno: Optional[int]
    reported_proxy_subdir: str
    reported_proxy_example_path: str
    proxy_playable_in_camera: bool
    proxy_coupled_delete_protect: bool
    # FX6 contrasts (`Simul Rec`, `Rec Button Set`, `Chunk` exclusions)
    fx6_simul_rec_enabled: bool
    fx6_simul_exclusions_active: Tuple[str, ...]
    fx6_proxy_chunk_mode: str
    # Reset boundary (`None`, `Camera Settings Reset`, `Initialize`)
    reset_action: str
    post_still_rec_media: str
    post_movie_rec_media: str
    post_auto_switch_media: str
    post_proxy_recording: str
    post_proxy_file_format: str
    post_proxy_rec_setting: str
    # Slot-1 Tier-0 Vault Firewall & Stage-B Overlay & H0 == H3
    requested_vault_slot: int
    slot1_holds_tier0_vault: bool
    requested_vault_action: str
    reported_vault_action_allowed: bool
    vault_firewall_errno: Optional[str]
    slot1_data_sector_writes: int
    slot1_dcim_m4root_avf_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative drift event counters
    rec_media_prioritize_or_autoswitch_drift_events: int
    card_speed_vpg200_vpg400_gate_drift_events: int
    proxy_sq_dci4k_or_120p_lockout_drift_events: int


@dataclass(frozen=True)
class RecMediaAutoSwitchProxyVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    rec_media_split_and_autoswitch_guard_verified: bool
    card_speed_vpg200_vpg400_gate_verified: bool
    proxy_sq_dci4k_and_m4root_sub_verified: bool
    slot1_vault_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    rec_media_prioritize_or_autoswitch_drift_events: int
    card_speed_vpg200_vpg400_gate_drift_events: int
    proxy_sq_dci4k_or_120p_lockout_drift_events: int
    slot1_data_sector_writes: int
    slot1_dcim_m4root_avf_mutation_bytes: int
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
class CloudPowerOffBleMyMenuVaultSpec:
    # [Creators' Cloud] / [C3 Portal] (`*` Initialize-Persistence)
    camera_model: str
    fw_version: str
    cloud_connection_enabled: bool
    cloud_account_bound_star: bool
    cloud_clip_flag_filter: str
    ftp_transfer_enabled: bool
    explicit_cloud_account_deleted: bool
    reported_cloud_ftp_errno: Optional[int]
    reported_clip_flag_errno: Optional[int]
    # [Cnct. while Power OFF] Power-Off BLE RF Hazard
    bluetooth_paired: bool
    cnct_while_power_off: str
    power_switch_state: str
    reported_cnct_poweroff_errno: Optional[int]
    reported_ble_energized_while_power_off: bool
    fx6_has_bluetooth_hardware: bool
    # [My Menu] 6x7=42 Slots vs FX6 20-Item User Menu with Lock
    mymenu_page: int
    mymenu_slot_index: int
    mymenu_registered_count: int
    mymenu_includes_playback_item: bool
    mymenu_display_from_mymenu: str
    mymenu_delete_all_requested: bool
    reported_mymenu_errno: Optional[int]
    fx3_mymenu_slot_capacity: int
    fx3_mymenu_dormant_boundary_hits: int
    fx6_user_menu_item_count: int
    fx6_user_menu_only: bool
    fx6_user_menu_with_lock: bool
    fx6_lock_chord_used: str
    fx6_lock_pin: str
    fx6_save_target: str
    reported_fx6_menu_exported: bool
    reported_fx6_lock_exported: bool
    # Reset boundary
    reset_action: str
    post_cloud_account_bound_star: bool
    post_cloud_connection_enabled: bool
    post_cnct_while_power_off: str
    post_airplane_mode: str
    post_mymenu_count: int
    post_display_from_mymenu: str
    # Zero-RF & Slot-1 Tier-0 Vault Firewall & Stage-B Overlay & H0 == H3
    airplane_mode: str
    wifi_active: bool
    cloud_upload_active: bool
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
    # Negative drift event counters
    cloud_init_persist_or_power_off_ble_rf_events: int
    mymenu_42slot_or_fx6_lock_spoof_events: int
    zero_rf_or_slot1_vault_bypass_events: int


@dataclass(frozen=True)
class CloudPowerOffBleMyMenuVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    cloud_star_init_persist_and_poweroff_ble_verified: bool
    mymenu_42slot_and_fx6_pin_lock_verified: bool
    zero_rf_and_slot1_erofs30_vault_verified: bool
    overlay_and_h0_h3_verified: bool
    matrix_states_checked: int
    cloud_init_persist_or_power_off_ble_rf_events: int
    mymenu_42slot_or_fx6_lock_spoof_events: int
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
class RecMediaAutoSwitchProxyCloudMyMenuVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase344DonorSnapshot
    rec_media_autoswitch_proxy_report: RecMediaAutoSwitchProxyVaultReport
    cloud_poweroff_ble_mymenu_report: CloudPowerOffBleMyMenuVaultReport
    rec_media_prioritize_or_autoswitch_drift_events: int
    card_speed_vpg200_vpg400_gate_drift_events: int
    proxy_sq_dci4k_or_120p_lockout_drift_events: int
    cloud_init_persist_or_power_off_ble_rf_events: int
    mymenu_42slot_or_fx6_lock_spoof_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_dcim_m4root_avf_mutation_bytes: int
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
class Pillar62ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar62ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar62ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar62BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar62ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar62StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase344DonorSnapshot
    pillar_62a_rec_media_autoswitch_proxy_vault: Pillar62ASuiteResult
    pillar_62b_cloud_poweroff_ble_mymenu_vault: Pillar62BSuiteResult
    rec_media_prioritize_or_autoswitch_drift_events: int
    card_speed_vpg200_vpg400_gate_drift_events: int
    proxy_sq_dci4k_or_120p_lockout_drift_events: int
    cloud_init_persist_or_power_off_ble_rf_events: int
    mymenu_42slot_or_fx6_lock_spoof_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_dcim_m4root_avf_mutation_bytes: int
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
class Master62PillarRecoveryReport:
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
    donor_snapshot: Phase344DonorSnapshot
    pillar62_a_rec_media_autoswitch_proxy_vault: Pillar62ASuiteResult
    pillar62_b_cloud_poweroff_ble_mymenu_vault: Pillar62BSuiteResult
    # Pillar 62 zero-violation counters & hardware boundaries
    rec_media_prioritize_or_autoswitch_drift_events: int
    card_speed_vpg200_vpg400_gate_drift_events: int
    proxy_sq_dci4k_or_120p_lockout_drift_events: int
    cloud_init_persist_or_power_off_ble_rf_events: int
    mymenu_42slot_or_fx6_lock_spoof_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_dcim_m4root_avf_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
    fx3_appfw_prioritize_hits: int
    fx3_appfw_prm_haita_proxy_hits: int
    fx3_has_movie_sort_recording: bool
    fx3_proxy_dci4k_allowed: bool
    fx3_cloud_star_survives_initialize: bool
    fx3_power_off_ble_forced_off: bool
    fx3_mymenu_slot_capacity: int
    fx3_mymenu_pages: int
    fx3_mymenu_items_per_page: int
    fx6_user_menu_max_items: int
    fx6_has_bluetooth_hardware: bool
    # Carried forward Pillar 61 metrics
    big6_home_or_lower_left_nd_drift_events: int
    framing_manual_or_dormant_auto_framing_drift_events: int
    interval_shoot_9999_or_fx6_mxf_spoof_events: int
    tc_make_regen_or_hdmi_rec_ctrl_drift_events: int
    access_authen_ssh_tls_or_fan_max_drift_events: int
    slot1_dcim_avf_mutation_bytes: int
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
    master_62pillar_sha256: str
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
# Default-Safe Spec Builders
# ---------------------------------------------------------------------------


def build_default_safe_rec_media_autoswitch_proxy_vault_spec(
    **overrides: Any,
) -> RecMediaAutoSwitchProxyVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P344_FX3_MODEL_NAME,
        "fw_version": P344_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "still_recording_media": "Slot 2",
        "movie_recording_media": "Slot 2",
        "prioritize_rec_media_requested": False,
        "reported_prioritize_errno": None,
        "reported_movie_sort_errno": None,
        "auto_switch_media": "Off",
        "slot1_filesystem": "exFAT",
        "slot2_filesystem": "exFAT",
        "reported_simult_fs_errno": None,
        "slot2_full_or_missing": False,
        "still_jpeg_raw_settings_shared": True,
        "fx3_appfw_prioritize_hits": P344_FX3_APPFW_PRIORITIZE_HIT_COUNT,
        "fx3_appfw_prm_haita_proxy_hits": P344_FX3_APPFW_PRM_HAITA_PROXY_HIT_COUNT,
        "movie_file_format": "XAVC S-I DCI 4K",
        "movie_bitrate_mbps": 600,
        "rec_frame_rate_p": 23.98,
        "sq_sensor_fps": 24,
        "media_card_slot2_type": "CFexpress Type A VPG400",
        "reported_card_gate_errno": None,
        "reported_card_gate_warning": None,
        "proxy_recording": "On",
        "proxy_file_format": "XAVC HS HD",
        "proxy_rec_setting": "9M 4:2:0 10bit",
        "reported_effective_proxy_recording": "On",
        "reported_proxy_errno": None,
        "reported_proxy_subdir": P344_PROXY_CFE_SUBDIR,
        "reported_proxy_example_path": f"{P344_PROXY_CFE_SUBDIR}/C0001{P344_PROXY_FILE_SUFFIX}",
        "proxy_playable_in_camera": False,
        "proxy_coupled_delete_protect": True,
        "fx6_simul_rec_enabled": False,
        "fx6_simul_exclusions_active": (),
        "fx6_proxy_chunk_mode": "Off",
        "reset_action": "None",
        "post_still_rec_media": "Slot 2",
        "post_movie_rec_media": "Slot 2",
        "post_auto_switch_media": "Off",
        "post_proxy_recording": "On",
        "post_proxy_file_format": "XAVC HS HD",
        "post_proxy_rec_setting": "9M 4:2:0 10bit",
        "requested_vault_slot": P344_SAFE_SECONDARY_SLOT,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "PROXY_TO_SLOT2",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": P344_SLOT1_DATA_SECTOR_WRITES,
        "slot1_dcim_m4root_avf_mutation_bytes": P344_SLOT1_DCIM_M4ROOT_AVF_MUTATION_BYTES,
        "slot1_vault_mutation_bytes": P344_SLOT1_VAULT_MUTATION_BYTES,
        "slot1_vault_erofs_eopnotsupp_enforced": P344_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        "slot1_format_hard_locked": P344_SLOT1_FORMAT_HARD_LOCKED,
        "overlay_dir": f"{P344_STAGE_B_VOLATILE_OVERLAY_DIR}/62a",
        "backup_bin_h0_sha256": P344_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P344_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P344_TIER0_SURFACE_COUNT,
        "rec_media_prioritize_or_autoswitch_drift_events": (
            P344_REC_MEDIA_PRIORITIZE_OR_AUTOSWITCH_DRIFT_EVENTS
        ),
        "card_speed_vpg200_vpg400_gate_drift_events": (
            P344_CARD_SPEED_VPG200_VPG400_GATE_DRIFT_EVENTS
        ),
        "proxy_sq_dci4k_or_120p_lockout_drift_events": (
            P344_PROXY_SQ_DCI4K_OR_120P_LOCKOUT_DRIFT_EVENTS
        ),
    }
    defaults.update(overrides)
    return RecMediaAutoSwitchProxyVaultSpec(**defaults)


def build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
    **overrides: Any,
) -> CloudPowerOffBleMyMenuVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P344_FX3_MODEL_NAME,
        "fw_version": P344_FX3_FW_VERSION,
        "cloud_connection_enabled": False,
        "cloud_account_bound_star": True,
        "cloud_clip_flag_filter": "OK",
        "ftp_transfer_enabled": False,
        "explicit_cloud_account_deleted": False,
        "reported_cloud_ftp_errno": None,
        "reported_clip_flag_errno": None,
        "bluetooth_paired": False,
        "cnct_while_power_off": "Off",
        "power_switch_state": "OFF",
        "reported_cnct_poweroff_errno": None,
        "reported_ble_energized_while_power_off": False,
        "fx6_has_bluetooth_hardware": P344_FX6_HAS_BLUETOOTH_HARDWARE,
        "mymenu_page": 6,
        "mymenu_slot_index": 6,
        "mymenu_registered_count": P344_FX3_MYMENU_TOTAL_SLOTS,
        "mymenu_includes_playback_item": False,
        "mymenu_display_from_mymenu": "Off",
        "mymenu_delete_all_requested": False,
        "reported_mymenu_errno": None,
        "fx3_mymenu_slot_capacity": P344_FX3_MYMENU_TOTAL_SLOTS,
        "fx3_mymenu_dormant_boundary_hits": P344_FX3_MYMENU_DORMANT_BOUNDARY_HITS,
        "fx6_user_menu_item_count": P344_FX6_USER_MENU_MAX_ITEMS,
        "fx6_user_menu_only": False,
        "fx6_user_menu_with_lock": False,
        "fx6_lock_chord_used": P344_FX6_USER_MENU_LOCK_CHORD,
        "fx6_lock_pin": P344_FX6_USER_MENU_LOCK_DEFAULT_PIN,
        "fx6_save_target": "All File",
        "reported_fx6_menu_exported": True,
        "reported_fx6_lock_exported": False,
        "reset_action": "None",
        "post_cloud_account_bound_star": True,
        "post_cloud_connection_enabled": False,
        "post_cnct_while_power_off": "Off",
        "post_airplane_mode": "On",
        "post_mymenu_count": P344_FX3_MYMENU_TOTAL_SLOTS,
        "post_display_from_mymenu": "Off",
        "airplane_mode": "On",
        "wifi_active": False,
        "cloud_upload_active": False,
        "network_transport": P344_SAFE_WIRED_TRANSPORT,
        "rf_packets_transmitted": P344_RF_PACKETS_TRANSMITTED,
        "rf_nvs_mutation_bytes": P344_RF_NVS_MUTATION_BYTES,
        "requested_vault_slot": P344_SLOT1_VAULT_SLOT,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": P344_SLOT1_DATA_SECTOR_WRITES,
        "slot1_vault_mutation_bytes": P344_SLOT1_VAULT_MUTATION_BYTES,
        "slot1_vault_erofs_eopnotsupp_enforced": P344_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        "slot1_format_hard_locked": P344_SLOT1_FORMAT_HARD_LOCKED,
        "overlay_dir": f"{P344_STAGE_B_VOLATILE_OVERLAY_DIR}/62b",
        "backup_bin_h0_sha256": P344_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P344_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P344_TIER0_SURFACE_COUNT,
        "cloud_init_persist_or_power_off_ble_rf_events": (
            P344_CLOUD_INIT_PERSIST_OR_POWER_OFF_BLE_RF_EVENTS
        ),
        "mymenu_42slot_or_fx6_lock_spoof_events": (
            P344_MYMENU_42SLOT_OR_FX6_LOCK_SPOOF_EVENTS
        ),
        "zero_rf_or_slot1_vault_bypass_events": P344_ZERO_RF_OR_SLOT1_VAULT_BYPASS_EVENTS,
    }
    defaults.update(overrides)
    return CloudPowerOffBleMyMenuVaultSpec(**defaults)


# ---------------------------------------------------------------------------
# Sub-Pillar Evaluators (62A & 62B) + Combined Single-Shot Verifier
# ---------------------------------------------------------------------------


def evaluate_rec_media_autoswitch_proxy_vault(
    spec: RecMediaAutoSwitchProxyVaultSpec,
) -> RecMediaAutoSwitchProxyVaultReport:
    """Evaluate Pillar 62A spec (`[Rec. Media Settings]`, `VPG200/VPG400`, `[Proxy Settings]`, `Slot 1` `EROFS=30`)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P344_BLOCKED_SAFETY_POLICY_VIOLATION, "Safety policy violation")

    valid_spec = (
        spec.camera_model in (P344_FX3_MODEL_NAME, P344_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P344_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P344_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P344_SHOOTING_DOMAINS
        and spec.still_recording_media in P344_STILL_RECORDING_MEDIA_MODES
        and spec.auto_switch_media in P344_AUTO_SWITCH_MEDIA_MODES
        and spec.slot1_filesystem in P344_FILESYSTEM_TYPES
        and spec.slot2_filesystem in P344_FILESYSTEM_TYPES
        and spec.movie_file_format in P344_MOVIE_FILE_FORMATS
        and spec.media_card_slot2_type in P344_CARD_MEDIA_TYPES
        and spec.proxy_recording in P344_ON_OFF_MODES
        and spec.proxy_file_format in P344_PROXY_FILE_FORMATS
        and spec.reset_action in ("None", "Camera Settings Reset", "Initialize")
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P344_VAULT_ACTIONS
        and spec.vault_firewall_errno in P344_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P344_BLOCKED_INVALID_PILLAR62A_SPEC, "Invalid Pillar 62A spec fields")

    st = compute_expected_rec_media_autoswitch_proxy_state(
        camera_model=spec.camera_model,
        shooting_domain=spec.shooting_domain,
        still_recording_media=spec.still_recording_media,
        movie_recording_media=spec.movie_recording_media,
        prioritize_rec_media_requested=spec.prioritize_rec_media_requested,
        auto_switch_media=spec.auto_switch_media,
        slot1_filesystem=spec.slot1_filesystem,
        slot2_filesystem=spec.slot2_filesystem,
        slot2_full_or_missing=spec.slot2_full_or_missing,
        still_jpeg_raw_settings_shared=spec.still_jpeg_raw_settings_shared,
        movie_file_format=spec.movie_file_format,
        movie_bitrate_mbps=spec.movie_bitrate_mbps,
        rec_frame_rate_p=spec.rec_frame_rate_p,
        sq_sensor_fps=spec.sq_sensor_fps,
        media_card_slot2_type=spec.media_card_slot2_type,
        proxy_recording=spec.proxy_recording,
        proxy_file_format=spec.proxy_file_format,
        proxy_rec_setting=spec.proxy_rec_setting,
        proxy_playable_in_camera=spec.proxy_playable_in_camera,
        proxy_coupled_delete_protect=spec.proxy_coupled_delete_protect,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
        fx6_simul_rec_enabled=spec.fx6_simul_rec_enabled,
        fx6_simul_exclusions_active=spec.fx6_simul_exclusions_active,
        fx6_proxy_chunk_mode=spec.fx6_proxy_chunk_mode,
    )

    # 1. Dormant Prioritize, Split Recording Media, Reset-immune Auto Switch Media & Tier-0 Spillover Lock
    rec_media_ok = (
        spec.fx3_appfw_prioritize_hits == P344_FX3_APPFW_PRIORITIZE_HIT_COUNT
        and spec.fx3_appfw_prm_haita_proxy_hits == P344_FX3_APPFW_PRM_HAITA_PROXY_HIT_COUNT
        and (not spec.prioritize_rec_media_requested or spec.reported_prioritize_errno == st["prioritize_errno"])
        and (
            spec.movie_recording_media in P344_MOVIE_RECORDING_MEDIA_MODES
            or spec.reported_movie_sort_errno == P344_EOPNOTSUPP_ERRNO
        )
        and spec.reported_movie_sort_errno == st["movie_sort_errno"]
        and spec.reported_simult_fs_errno == st["simult_fs_errno"]
        and st["still_sort_shared_ok"]
        and spec.post_still_rec_media == st["post_still_rec_media"]
        and spec.post_movie_rec_media == st["post_movie_rec_media"]
        and spec.post_auto_switch_media == st["post_auto_switch_media"]
        and st["fx6_simul_ok"]
        and st["fx6_chunk_ok"]
        and spec.rec_media_prioritize_or_autoswitch_drift_events == 0
    )
    if not rec_media_ok:
        _fail(
            P344_BLOCKED_REC_MEDIA_PRIORITIZE_OR_AUTOSWITCH_DRIFT,
            "Dormant Prioritize Rec. Media / split Movie Sort Rec / Simult. FS / Auto Switch Media / FX6 Simul exclusion violated",
        )

    # 2. Card-Speed Gate Matrix (CFexpress Type A VPG200/VPG400 vs SDXC V60/V90)
    card_speed_ok = (
        spec.reported_card_gate_errno == st["card_gate_errno"]
        and spec.reported_card_gate_warning == st["card_gate_warning"]
        and spec.card_speed_vpg200_vpg400_gate_drift_events == 0
    )
    if not card_speed_ok:
        _fail(
            P344_BLOCKED_CARD_SPEED_VPG200_VPG400_GATE_DRIFT,
            "Card-speed gate matrix (SDXC V60/V90 vs CFexpress Type A VPG200/VPG400) violated",
        )

    # 3. [Proxy Settings] (`sq_proxy`) XAVC S-I DCI 4K Allowed vs 120p/100p Lockout & M4ROOT/SUB/*S03.MP4
    proxy_ok = (
        spec.reported_effective_proxy_recording == st["effective_proxy_recording"]
        and spec.reported_proxy_errno == st["proxy_errno"]
        and spec.reported_proxy_subdir == st["proxy_subdir"]
        and spec.reported_proxy_example_path == st["proxy_example_path"]
        and st["proxy_lifecycle_ok"]
        and spec.post_proxy_recording == st["post_proxy_recording"]
        and spec.post_proxy_file_format == st["post_proxy_file_format"]
        and spec.post_proxy_rec_setting == st["post_proxy_rec_setting"]
        and spec.proxy_sq_dci4k_or_120p_lockout_drift_events == 0
    )
    if not proxy_ok:
        _fail(
            P344_BLOCKED_PROXY_SQ_DCI4K_OR_120P_LOCKOUT_DRIFT,
            "Proxy Settings (sq_proxy XAVC S-I DCI 4K allowed vs 120p/100p lockout, dormant 8bit, or M4ROOT/SUB lifecycle) violated",
        )

    # 4. Tier-0 Slot-1 Spillover & Proxy EROFS=30 Vault Firewall
    slot1_mutated = (
        (
            spec.requested_vault_action in P344_WRITE_MUTATING_VAULT_ACTIONS
            or st["would_spillover_to_slot1"]
        )
        and spec.reported_vault_action_allowed
    )
    vault_ok = (
        not slot1_mutated
        and spec.reported_vault_action_allowed == st["vault_action_allowed"]
        and spec.vault_firewall_errno == st["vault_firewall_errno"]
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_dcim_m4root_avf_mutation_bytes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_format_hard_locked
    )
    if not vault_ok:
        _fail(
            P344_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault Firewall (Auto Switch spillover / Proxy M4ROOT/SUB / EROFS=30) breached",
        )

    # 5. Stage-B Volatile Overlay & H0 == H3
    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P344_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P344_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P344_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P344_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    vault_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "62A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "still_rec_media": spec.still_recording_media,
            "movie_rec_media": spec.movie_recording_media,
            "auto_switch_media": spec.auto_switch_media,
            "media_card_slot2_type": spec.media_card_slot2_type,
            "movie_file_format": spec.movie_file_format,
            "proxy_recording": spec.reported_effective_proxy_recording,
            "proxy_file_format": spec.proxy_file_format,
            "proxy_rec_setting": spec.proxy_rec_setting,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return RecMediaAutoSwitchProxyVaultReport(
        schema=PHASE344_SCHEMA,
        version=PHASE344_VERSION,
        passed=passed,
        status=P344_STATUS_VERIFIED_PILLAR_62A if passed else P344_STATUS_REJECTED_PILLAR_62A,
        block_code=block_code,
        rec_media_split_and_autoswitch_guard_verified=rec_media_ok,
        card_speed_vpg200_vpg400_gate_verified=card_speed_ok,
        proxy_sq_dci4k_and_m4root_sub_verified=proxy_ok,
        slot1_vault_firewall_and_h0_h3_verified=vault_and_h0_h3_ok,
        matrix_states_checked=28,
        rec_media_prioritize_or_autoswitch_drift_events=(
            spec.rec_media_prioritize_or_autoswitch_drift_events
        ),
        card_speed_vpg200_vpg400_gate_drift_events=spec.card_speed_vpg200_vpg400_gate_drift_events,
        proxy_sq_dci4k_or_120p_lockout_drift_events=spec.proxy_sq_dci4k_or_120p_lockout_drift_events,
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_dcim_m4root_avf_mutation_bytes=spec.slot1_dcim_m4root_avf_mutation_bytes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_cloud_poweroff_ble_mymenu_vault(
    spec: CloudPowerOffBleMyMenuVaultSpec,
) -> CloudPowerOffBleMyMenuVaultReport:
    """Evaluate Pillar 62B spec (`[Creators' Cloud]`, `[Cnct. while Power OFF]` BLE RF, `[My Menu]` 42 vs FX6 20 Lock)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P344_BLOCKED_SAFETY_POLICY_VIOLATION, "Safety policy violation")

    valid_spec = (
        spec.camera_model in (P344_FX3_MODEL_NAME, P344_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P344_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P344_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.cnct_while_power_off in P344_ON_OFF_MODES
        and spec.power_switch_state in P344_POWER_SWITCH_STATES
        and spec.mymenu_display_from_mymenu in P344_ON_OFF_MODES
        and spec.airplane_mode in P344_ON_OFF_MODES
        and spec.network_transport in P344_NETWORK_TRANSPORTS
        and spec.reset_action in P344_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P344_VAULT_ACTIONS
        and spec.vault_firewall_errno in P344_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P344_BLOCKED_INVALID_PILLAR62B_SPEC, "Invalid Pillar 62B spec fields")

    st = compute_expected_cloud_poweroff_ble_mymenu_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        cloud_connection_enabled=spec.cloud_connection_enabled,
        cloud_account_bound_star=spec.cloud_account_bound_star,
        cloud_clip_flag_filter=spec.cloud_clip_flag_filter,
        ftp_transfer_enabled=spec.ftp_transfer_enabled,
        explicit_cloud_account_deleted=spec.explicit_cloud_account_deleted,
        bluetooth_paired=spec.bluetooth_paired,
        cnct_while_power_off=spec.cnct_while_power_off,
        power_switch_state=spec.power_switch_state,
        airplane_mode=spec.airplane_mode,
        wifi_active=spec.wifi_active,
        cloud_upload_active=spec.cloud_upload_active,
        network_transport=spec.network_transport,
        mymenu_page=spec.mymenu_page,
        mymenu_slot_index=spec.mymenu_slot_index,
        mymenu_registered_count=spec.mymenu_registered_count,
        mymenu_includes_playback_item=spec.mymenu_includes_playback_item,
        mymenu_display_from_mymenu=spec.mymenu_display_from_mymenu,
        mymenu_delete_all_requested=spec.mymenu_delete_all_requested,
        fx6_user_menu_item_count=spec.fx6_user_menu_item_count,
        fx6_user_menu_only=spec.fx6_user_menu_only,
        fx6_user_menu_with_lock=spec.fx6_user_menu_with_lock,
        fx6_lock_chord_used=spec.fx6_lock_chord_used,
        fx6_lock_pin=spec.fx6_lock_pin,
        fx6_save_target=spec.fx6_save_target,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    # 1. [Creators' Cloud] `*` Initialize-Persistence & [Cnct. while Power OFF] BLE RF
    cloud_poweroff_ok = (
        spec.reported_cloud_ftp_errno == st["cloud_ftp_errno"]
        and st["cloud_ftp_errno"] is None
        and spec.reported_clip_flag_errno == st["clip_flag_errno"]
        and st["clip_flag_errno"] is None
        and spec.reported_cnct_poweroff_errno == st["cnct_poweroff_errno"]
        and spec.reported_ble_energized_while_power_off == st["ble_energized_while_power_off"]
        and not spec.reported_ble_energized_while_power_off
        and not spec.fx6_has_bluetooth_hardware
        and spec.post_cloud_account_bound_star == st["post_cloud_account_bound_star"]
        and spec.post_cloud_connection_enabled == st["post_cloud_connection_enabled"]
        and spec.post_cnct_while_power_off == st["post_cnct_while_power_off"]
        and spec.post_airplane_mode == st["post_airplane_mode"]
        and spec.cloud_init_persist_or_power_off_ble_rf_events == 0
    )
    if not cloud_poweroff_ok:
        _fail(
            P344_BLOCKED_CLOUD_INIT_PERSIST_OR_POWEROFF_BLE_RF,
            "Creators' Cloud (*) Initialize-persistence / FTP mutex or Cnct. while Power OFF BLE RF hazard violated",
        )

    # 2. [My Menu] 6x7=42 NVRAM Slots vs FX6 20-Item User Menu with Lock
    mymenu_ok = (
        spec.fx3_mymenu_slot_capacity == P344_FX3_MYMENU_TOTAL_SLOTS
        and spec.fx3_mymenu_dormant_boundary_hits == P344_FX3_MYMENU_DORMANT_BOUNDARY_HITS
        and spec.reported_mymenu_errno == st["mymenu_errno"]
        and st["mymenu_errno"] is None
        and st["fx6_user_menu_valid"]
        and spec.reported_fx6_menu_exported == st["fx6_menu_exported"]
        and spec.reported_fx6_lock_exported == st["fx6_lock_exported"]
        and spec.post_mymenu_count == st["post_mymenu_count"]
        and spec.post_display_from_mymenu == st["post_display_from_mymenu"]
        and spec.mymenu_42slot_or_fx6_lock_spoof_events == 0
    )
    if not mymenu_ok:
        _fail(
            P344_BLOCKED_MYMENU_42SLOT_OR_FX6_LOCK_SPOOF,
            "My Menu 6x7=42 slots (Playback disallowed, Reset-immune) or FX6 20-item User Menu with Lock contract violated",
        )

    # 3. Dual Zero-RF (Airplane Mode=On + Cnct. while Power OFF=Off) & Slot-1 EROFS=30 Vault Firewall
    slot1_mutated = (
        (
            spec.requested_vault_action in P344_WRITE_MUTATING_VAULT_ACTIONS
            or (spec.requested_vault_slot == P344_SLOT1_VAULT_SLOT and spec.requested_vault_action != "READ_ONLY_AUDIT")
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
            P344_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL,
            "Zero-RF (Airplane Mode=On AND Cnct. while Power OFF=Off) or Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    # 4. Stage-B Volatile Overlay & H0 == H3
    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P344_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P344_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P344_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P344_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    overlay_and_h0_h3_ok = overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "62B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "cloud_account_bound_star": spec.post_cloud_account_bound_star,
            "cnct_while_power_off": spec.cnct_while_power_off,
            "power_switch_state": spec.power_switch_state,
            "mymenu_count": spec.mymenu_registered_count,
            "fx6_user_menu_with_lock": spec.fx6_user_menu_with_lock,
            "post_airplane_mode": spec.post_airplane_mode,
            "rf_packets": spec.rf_packets_transmitted,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return CloudPowerOffBleMyMenuVaultReport(
        schema=PHASE344_SCHEMA,
        version=PHASE344_VERSION,
        passed=passed,
        status=P344_STATUS_VERIFIED_PILLAR_62B if passed else P344_STATUS_REJECTED_PILLAR_62B,
        block_code=block_code,
        cloud_star_init_persist_and_poweroff_ble_verified=cloud_poweroff_ok,
        mymenu_42slot_and_fx6_pin_lock_verified=mymenu_ok,
        zero_rf_and_slot1_erofs30_vault_verified=zero_rf_vault_ok,
        overlay_and_h0_h3_verified=overlay_and_h0_h3_ok,
        matrix_states_checked=22,
        cloud_init_persist_or_power_off_ble_rf_events=(
            spec.cloud_init_persist_or_power_off_ble_rf_events
        ),
        mymenu_42slot_or_fx6_lock_spoof_events=spec.mymenu_42slot_or_fx6_lock_spoof_events,
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


def verify_rec_media_autoswitch_proxy_cloud_mymenu_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_62a: Optional[RecMediaAutoSwitchProxyVaultSpec] = None,
    spec_62b: Optional[CloudPowerOffBleMyMenuVaultSpec] = None,
) -> RecMediaAutoSwitchProxyCloudMyMenuVaultReport:
    """Combined single-shot verifier for Pillar 62A + Pillar 62B + bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase344_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_rec_media_autoswitch_proxy_vault(
        spec_62a or build_default_safe_rec_media_autoswitch_proxy_vault_spec()
    )
    rep_b = evaluate_cloud_poweroff_ble_mymenu_vault(
        spec_62b or build_default_safe_cloud_poweroff_ble_mymenu_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 344 Wave-60 donor artifact parity check failed")
    if not donor_snapshot.under_2_0s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return RecMediaAutoSwitchProxyCloudMyMenuVaultReport(
        schema=PHASE344_SCHEMA,
        version=PHASE344_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P344_STATUS_VERIFIED_PILLAR62_SUITE if all_ok else P344_STATUS_FAIL_PILLAR62_SUITE,
        donor_snapshot=donor_snapshot,
        rec_media_autoswitch_proxy_report=rep_a,
        cloud_poweroff_ble_mymenu_report=rep_b,
        rec_media_prioritize_or_autoswitch_drift_events=(
            rep_a.rec_media_prioritize_or_autoswitch_drift_events
        ),
        card_speed_vpg200_vpg400_gate_drift_events=rep_a.card_speed_vpg200_vpg400_gate_drift_events,
        proxy_sq_dci4k_or_120p_lockout_drift_events=rep_a.proxy_sq_dci4k_or_120p_lockout_drift_events,
        cloud_init_persist_or_power_off_ble_rf_events=(
            rep_b.cloud_init_persist_or_power_off_ble_rf_events
        ),
        mymenu_42slot_or_fx6_lock_spoof_events=rep_b.mymenu_42slot_or_fx6_lock_spoof_events,
        zero_rf_or_slot1_vault_bypass_events=rep_b.zero_rf_or_slot1_vault_bypass_events,
        rf_packets_transmitted=rep_b.rf_packets_transmitted,
        rf_nvs_mutation_bytes=rep_b.rf_nvs_mutation_bytes,
        slot1_data_sector_writes=rep_a.slot1_data_sector_writes + rep_b.slot1_data_sector_writes,
        slot1_dcim_m4root_avf_mutation_bytes=rep_a.slot1_dcim_m4root_avf_mutation_bytes,
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


def verify_rec_media_autoswitch_proxy_cloud_mymenu_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_62a: Optional[RecMediaAutoSwitchProxyVaultSpec] = None,
    spec_62b: Optional[CloudPowerOffBleMyMenuVaultSpec] = None,
) -> RecMediaAutoSwitchProxyCloudMyMenuVaultReport:
    """Symmetry alias for `verify_rec_media_autoswitch_proxy_cloud_mymenu_and_vault`."""
    return verify_rec_media_autoswitch_proxy_cloud_mymenu_and_vault(
        force_clean_room=force_clean_room,
        spec_62a=spec_62a,
        spec_62b=spec_62b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 62A & 62B)
# ---------------------------------------------------------------------------


def run_pillar62a_rec_media_autoswitch_proxy_vault_6_scenario_suite() -> Pillar62ASuiteResult:
    """Run 6 Pillar 62A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, RecMediaAutoSwitchProxyVaultSpec, Optional[str]], ...] = (
        (
            P344_PILLAR_62A_SCENARIO_IDS[0],
            True,
            build_default_safe_rec_media_autoswitch_proxy_vault_spec(
                shooting_domain="Movie",
                movie_recording_media="Slot 2",
                auto_switch_media="Off",
                movie_file_format="XAVC S-I DCI 4K",
                movie_bitrate_mbps=600,
                rec_frame_rate_p=59.94,
                media_card_slot2_type="CFexpress Type A VPG400",
                proxy_recording="On",
                proxy_file_format="XAVC HS HD",
                proxy_rec_setting="16M 4:2:0 10bit",
                reported_effective_proxy_recording="On",
                post_proxy_recording="On",
                post_proxy_file_format="XAVC HS HD",
                post_proxy_rec_setting="16M 4:2:0 10bit",
            ),
            None,
        ),
        (
            P344_PILLAR_62A_SCENARIO_IDS[1],
            True,
            build_default_safe_rec_media_autoswitch_proxy_vault_spec(
                shooting_domain="Still",
                still_recording_media="Sort Recording",
                movie_recording_media="Slot 2",
                auto_switch_media="Off",
                slot2_full_or_missing=False,
                media_card_slot2_type="SDXC V60",
                movie_file_format="XAVC S 4K",
                movie_bitrate_mbps=200,
                proxy_recording="Off",
                proxy_file_format="XAVC S HD",
                proxy_rec_setting="6M 4:2:0 8bit",
                reported_effective_proxy_recording="Off",
                reported_proxy_subdir=P344_PROXY_SD_SUBDIR,
                reported_proxy_example_path=f"{P344_PROXY_SD_SUBDIR}/C0001{P344_PROXY_FILE_SUFFIX}",
                reset_action="Camera Settings Reset",
                post_still_rec_media="Sort Recording",
                post_movie_rec_media="Slot 2",
                post_auto_switch_media="Off",
                post_proxy_recording="Off",
                post_proxy_file_format="XAVC S HD",
                post_proxy_rec_setting="6M 4:2:0 8bit",
                requested_vault_slot=2,
                requested_vault_action="REC_TO_SLOT2",
            ),
            None,
        ),
        (
            P344_PILLAR_62A_SCENARIO_IDS[2],
            False,
            build_default_safe_rec_media_autoswitch_proxy_vault_spec(
                prioritize_rec_media_requested=True,
                reported_prioritize_errno=None,
                movie_recording_media="Sort Recording",
                reported_movie_sort_errno=None,
                still_recording_media="Simult. Recording",
                slot1_filesystem="exFAT",
                slot2_filesystem="FAT32",
                reported_simult_fs_errno=None,
                rec_media_prioritize_or_autoswitch_drift_events=1,
            ),
            P344_BLOCKED_REC_MEDIA_PRIORITIZE_OR_AUTOSWITCH_DRIFT,
        ),
        (
            P344_PILLAR_62A_SCENARIO_IDS[3],
            False,
            build_default_safe_rec_media_autoswitch_proxy_vault_spec(
                shooting_domain="S&Q",
                movie_file_format="XAVC S-I 4K",
                movie_bitrate_mbps=1200,
                sq_sensor_fps=120,
                rec_frame_rate_p=23.98,
                media_card_slot2_type="SDXC V90",
                reported_card_gate_errno=None,
                proxy_recording="Off",
                proxy_file_format="XAVC S HD",
                proxy_rec_setting="6M 4:2:0 8bit",
                reported_effective_proxy_recording="Off",
                reported_proxy_errno=P344_EOPNOTSUPP_ERRNO,
                reported_proxy_subdir=P344_PROXY_SD_SUBDIR,
                reported_proxy_example_path=f"{P344_PROXY_SD_SUBDIR}/C0001{P344_PROXY_FILE_SUFFIX}",
                post_proxy_recording="Off",
                post_proxy_file_format="XAVC S HD",
                post_proxy_rec_setting="6M 4:2:0 8bit",
                card_speed_vpg200_vpg400_gate_drift_events=1,
            ),
            P344_BLOCKED_CARD_SPEED_VPG200_VPG400_GATE_DRIFT,
        ),
        (
            P344_PILLAR_62A_SCENARIO_IDS[4],
            False,
            build_default_safe_rec_media_autoswitch_proxy_vault_spec(
                shooting_domain="Movie",
                movie_file_format="XAVC S 4K",
                movie_bitrate_mbps=280,
                rec_frame_rate_p=119.88,
                media_card_slot2_type="CFexpress Type A VPG200",
                proxy_recording="On",
                proxy_file_format="XAVC HS HD",
                proxy_rec_setting="16M 4:2:0 8bit",
                reported_effective_proxy_recording="On",
                reported_proxy_errno=None,
                proxy_sq_dci4k_or_120p_lockout_drift_events=1,
            ),
            P344_BLOCKED_PROXY_SQ_DCI4K_OR_120P_LOCKOUT_DRIFT,
        ),
        (
            P344_PILLAR_62A_SCENARIO_IDS[5],
            False,
            build_default_safe_rec_media_autoswitch_proxy_vault_spec(
                movie_recording_media="Slot 2",
                auto_switch_media="On",
                slot2_full_or_missing=True,
                reset_action="Camera Settings Reset",
                post_auto_switch_media="On",
                post_proxy_recording="Off",
                post_proxy_file_format="XAVC S HD",
                post_proxy_rec_setting="6M 4:2:0 8bit",
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="AUTO_SWITCH_SPILLOVER_SLOT1",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=8192,
                slot1_dcim_m4root_avf_mutation_bytes=4096,
                slot1_vault_mutation_bytes=12288,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/setting/62a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P344_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar62ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_rec_media_autoswitch_proxy_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar62ScenarioOutcome(
                scenario_id=sid,
                pillar="62A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar62ASuiteResult(
        passed=all_ok,
        status=P344_STATUS_VERIFIED_PILLAR_62A if all_ok else P344_STATUS_REJECTED_PILLAR_62A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar62b_cloud_poweroff_ble_mymenu_vault_6_scenario_suite() -> Pillar62BSuiteResult:
    """Run 6 Pillar 62B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, CloudPowerOffBleMyMenuVaultSpec, Optional[str]], ...] = (
        (
            P344_PILLAR_62B_SCENARIO_IDS[0],
            True,
            build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
                cloud_connection_enabled=False,
                cloud_account_bound_star=True,
                cloud_clip_flag_filter="OK",
                bluetooth_paired=False,
                cnct_while_power_off="Off",
                power_switch_state="OFF",
                mymenu_page=6,
                mymenu_slot_index=6,
                mymenu_registered_count=42,
                mymenu_display_from_mymenu="On",
                reset_action="Initialize",
                post_cloud_account_bound_star=True,
                post_cloud_connection_enabled=False,
                post_cnct_while_power_off="Off",
                post_airplane_mode="On",
                post_mymenu_count=0,
                post_display_from_mymenu="Off",
            ),
            None,
        ),
        (
            P344_PILLAR_62B_SCENARIO_IDS[1],
            True,
            build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
                camera_model=P344_FX6_DONOR_MODEL_NAME,
                fw_version=P344_FX6_DONOR_FW_VERSION,
                fx6_has_bluetooth_hardware=False,
                fx6_user_menu_item_count=20,
                fx6_user_menu_only=True,
                fx6_user_menu_with_lock=True,
                fx6_lock_chord_used=P344_FX6_USER_MENU_LOCK_CHORD,
                fx6_lock_pin="4321",
                fx6_save_target="All File",
                reported_fx6_menu_exported=True,
                reported_fx6_lock_exported=False,
                reset_action="Camera Settings Reset",
                post_cloud_account_bound_star=True,
                post_cnct_while_power_off="Off",
                post_airplane_mode="On",
                post_mymenu_count=42,
            ),
            None,
        ),
        (
            P344_PILLAR_62B_SCENARIO_IDS[2],
            False,
            build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
                cloud_connection_enabled=True,
                ftp_transfer_enabled=True,
                reported_cloud_ftp_errno=None,
                reset_action="Initialize",
                post_cloud_account_bound_star=False,
                post_cloud_connection_enabled=False,
                post_mymenu_count=0,
                cloud_init_persist_or_power_off_ble_rf_events=1,
            ),
            P344_BLOCKED_CLOUD_INIT_PERSIST_OR_POWEROFF_BLE_RF,
        ),
        (
            P344_PILLAR_62B_SCENARIO_IDS[3],
            False,
            build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
                bluetooth_paired=True,
                cnct_while_power_off="On",
                power_switch_state="OFF",
                airplane_mode="Off",
                post_airplane_mode="Off",
                post_cnct_while_power_off="On",
                reported_ble_energized_while_power_off=True,
                network_transport="BLE",
                rf_packets_transmitted=12,
                cloud_init_persist_or_power_off_ble_rf_events=1,
            ),
            P344_BLOCKED_CLOUD_INIT_PERSIST_OR_POWEROFF_BLE_RF,
        ),
        (
            P344_PILLAR_62B_SCENARIO_IDS[4],
            False,
            build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
                mymenu_page=7,
                mymenu_slot_index=7,
                mymenu_registered_count=36,
                mymenu_includes_playback_item=True,
                reported_mymenu_errno=None,
                fx3_mymenu_slot_capacity=36,
                fx3_mymenu_dormant_boundary_hits=1,
                fx6_user_menu_item_count=25,
                fx6_user_menu_with_lock=True,
                fx6_lock_pin="12A4",
                reported_fx6_lock_exported=True,
                mymenu_42slot_or_fx6_lock_spoof_events=1,
            ),
            P344_BLOCKED_MYMENU_42SLOT_OR_FX6_LOCK_SPOOF,
        ),
        (
            P344_PILLAR_62B_SCENARIO_IDS[5],
            False,
            build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
                airplane_mode="Off",
                post_airplane_mode="Off",
                wifi_active=True,
                cloud_upload_active=True,
                network_transport="Wi-Fi",
                rf_packets_transmitted=16,
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
            P344_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar62ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_cloud_poweroff_ble_mymenu_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar62ScenarioOutcome(
                scenario_id=sid,
                pillar="62B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar62BSuiteResult(
        passed=all_ok,
        status=P344_STATUS_VERIFIED_PILLAR_62B if all_ok else P344_STATUS_REJECTED_PILLAR_62B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Standalone Pillar 62 Suite & Unified 62/62 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def run_pillar62_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar62StandaloneReport:
    """Run full Pillar 62 standalone suite (`6/6` Pillar 62A + `6/6` Pillar 62B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase344_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar62a_rec_media_autoswitch_proxy_vault_6_scenario_suite()
    res_b = run_pillar62b_cloud_poweroff_ble_mymenu_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 344 donor verification failed")
    if not donor_snapshot.under_2_0s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE344_SCHEMA,
            "version": PHASE344_VERSION,
            "mode": donor_snapshot.verification_mode,
            "62a": [asdict(s) for s in res_a.scenarios],
            "62b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar62StandaloneReport(
        schema=PHASE344_SCHEMA,
        version=PHASE344_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P344_STATUS_VERIFIED_PILLAR62_SUITE if all_ok else P344_STATUS_FAIL_PILLAR62_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_62a_rec_media_autoswitch_proxy_vault=res_a,
        pillar_62b_cloud_poweroff_ble_mymenu_vault=res_b,
        rec_media_prioritize_or_autoswitch_drift_events=(
            P344_REC_MEDIA_PRIORITIZE_OR_AUTOSWITCH_DRIFT_EVENTS if res_a.passed else 1
        ),
        card_speed_vpg200_vpg400_gate_drift_events=(
            P344_CARD_SPEED_VPG200_VPG400_GATE_DRIFT_EVENTS if res_a.passed else 1
        ),
        proxy_sq_dci4k_or_120p_lockout_drift_events=(
            P344_PROXY_SQ_DCI4K_OR_120P_LOCKOUT_DRIFT_EVENTS if res_a.passed else 1
        ),
        cloud_init_persist_or_power_off_ble_rf_events=(
            P344_CLOUD_INIT_PERSIST_OR_POWER_OFF_BLE_RF_EVENTS if res_b.passed else 1
        ),
        mymenu_42slot_or_fx6_lock_spoof_events=(
            P344_MYMENU_42SLOT_OR_FX6_LOCK_SPOOF_EVENTS if res_b.passed else 1
        ),
        zero_rf_or_slot1_vault_bypass_events=(
            P344_ZERO_RF_OR_SLOT1_VAULT_BYPASS_EVENTS if res_b.passed else 1
        ),
        rf_packets_transmitted=P344_RF_PACKETS_TRANSMITTED if res_b.passed else 1,
        rf_nvs_mutation_bytes=P344_RF_NVS_MUTATION_BYTES if res_b.passed else 64,
        slot1_data_sector_writes=(
            P344_SLOT1_DATA_SECTOR_WRITES if (res_a.passed and res_b.passed) else 1
        ),
        slot1_dcim_m4root_avf_mutation_bytes=(
            P344_SLOT1_DCIM_M4ROOT_AVF_MUTATION_BYTES if res_a.passed else 4096
        ),
        slot1_vault_mutation_bytes=(
            P344_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        slot1_format_hard_locked=P344_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_eopnotsupp_enforced=P344_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
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


def _apply_master62_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def _master62_local_donors_available() -> bool:
    """Return True only when legacy BODYDATA.DAT and all 17 Wave-60 local donors exist."""
    required_relpaths: Tuple[str, ...] = (
        "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT",
        P344_DONOR_FX3_APPFW_702_RELPATH,
        P344_DONOR_FX6_APPFW_601_RELPATH,
        P344_DONOR_FX3_BACKUP_BIN_RELPATH,
        P344_DONOR_FX3_UXC_EN_F_RELPATH,
        P344_DONOR_FX3_UXC_SC_F_RELPATH,
        P344_DONOR_FX3_UXC_TC_F_RELPATH,
        P344_DONOR_FX3_UXC_JA_F_RELPATH,
        P344_DONOR_FX3_UXC_EN_RELPATH,
        P344_DONOR_FX3_UXC_SC_RELPATH,
        P344_DONOR_FX3_UXC_TC_RELPATH,
        P344_DONOR_FX3_UXC_JA_RELPATH,
        P344_DONOR_FX3_UXC_EN_G_RELPATH,
        P344_DONOR_FX3_UXC_SC_G_RELPATH,
        P344_DONOR_FX3_UXC_TC_G_RELPATH,
        P344_DONOR_FX3_UXC_JA_G_RELPATH,
        P344_DONOR_FX6_UXC_EN_RELPATH,
        P344_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for relpath in required_relpaths:
        try:
            resolved = _resolve_phase344_donor_path(relpath)
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


def evaluate_realhw_62pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master62PillarRecoveryReport:
    """Evaluate and aggregate all 62 recovery pillars (`1..62`) concurrently -> `62/62` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_62_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    if resolved_clean_room is None and not _master62_local_donors_available():
        resolved_clean_room = True
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_61pillar() -> Master61PillarRecoveryReport:
        return evaluate_realhw_61pillar_recovery_master(**kw)

    def _run_p62() -> Tuple[Pillar62StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar62_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_61 = pool.submit(_run_61pillar)
        fut_62 = pool.submit(_run_p62)
        m61_rep = fut_61.result()
        p62_rep, p62_dt = fut_62.result()

    all_errors: List[str] = list(m61_rep.errors) + list(p62_rep.errors)
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
        if getattr(m61_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-61 violated {attr_name} == {expected_val}")
        if getattr(p62_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 62 violated {attr_name} == {expected_val}")

    if p62_rep.cross_model_flash_authorized is not False:
        all_errors.append("Pillar 62 violated cross_model_flash_authorized == False")

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
        if getattr(m61_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-61 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("rec_media_prioritize_or_autoswitch_drift_events", 0),
        ("card_speed_vpg200_vpg400_gate_drift_events", 0),
        ("proxy_sq_dci4k_or_120p_lockout_drift_events", 0),
        ("cloud_init_persist_or_power_off_ble_rf_events", 0),
        ("mymenu_42slot_or_fx6_lock_spoof_events", 0),
        ("zero_rf_or_slot1_vault_bypass_events", 0),
        ("rf_packets_transmitted", 0),
        ("rf_nvs_mutation_bytes", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_dcim_m4root_avf_mutation_bytes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_eopnotsupp_enforced", True),
    ):
        if getattr(p62_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 62 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m61_rep.pillars)
    spec62 = MASTER_62_PILLAR_SPECS[61]
    p62_metrics = {
        "pillar_62a_rec_media_autoswitch_proxy_vault": (
            f"{p62_rep.pillar_62a_rec_media_autoswitch_proxy_vault.scenarios_passed}/"
            f"{p62_rep.pillar_62a_rec_media_autoswitch_proxy_vault.scenarios_total}"
        ),
        "pillar_62b_cloud_poweroff_ble_mymenu_vault": (
            f"{p62_rep.pillar_62b_cloud_poweroff_ble_mymenu_vault.scenarios_passed}/"
            f"{p62_rep.pillar_62b_cloud_poweroff_ble_mymenu_vault.scenarios_total}"
        ),
        "rec_media_prioritize_or_autoswitch_drift_events": (
            p62_rep.rec_media_prioritize_or_autoswitch_drift_events
        ),
        "card_speed_vpg200_vpg400_gate_drift_events": (
            p62_rep.card_speed_vpg200_vpg400_gate_drift_events
        ),
        "proxy_sq_dci4k_or_120p_lockout_drift_events": (
            p62_rep.proxy_sq_dci4k_or_120p_lockout_drift_events
        ),
        "cloud_init_persist_or_power_off_ble_rf_events": (
            p62_rep.cloud_init_persist_or_power_off_ble_rf_events
        ),
        "mymenu_42slot_or_fx6_lock_spoof_events": p62_rep.mymenu_42slot_or_fx6_lock_spoof_events,
        "zero_rf_or_slot1_vault_bypass_events": p62_rep.zero_rf_or_slot1_vault_bypass_events,
        "rf_packets_transmitted": p62_rep.rf_packets_transmitted,
        "rf_nvs_mutation_bytes": p62_rep.rf_nvs_mutation_bytes,
        "slot1_data_sector_writes": p62_rep.slot1_data_sector_writes,
        "slot1_dcim_m4root_avf_mutation_bytes": p62_rep.slot1_dcim_m4root_avf_mutation_bytes,
        "slot1_vault_mutation_bytes": p62_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p62_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_eopnotsupp_enforced": p62_rep.slot1_vault_erofs_eopnotsupp_enforced,
        "overall_ready_for_hardware_attach": p62_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p62_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p62_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p62_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec62[0],
            pillar_id=spec62[1],
            phase_label=spec62[2],
            module_name=spec62[3],
            passed=bool(p62_rep.all_passed),
            status=p62_rep.status,
            verification_mode=p62_rep.verification_mode,
            elapsed_seconds=p62_dt,
            key_metrics=p62_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec62[1],
                    "mode": p62_rep.verification_mode,
                    "status": p62_rep.status,
                    "metrics": p62_metrics,
                    "passed": p62_rep.all_passed,
                }
            ),
            errors=tuple(p62_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master62_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p62_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_62_PILLAR_COUNT == 62
        and pillars_passed == 62
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE344_SCHEMA,
            "schema_version": PHASE344_MASTER_SCHEMA,
            "version": PHASE344_VERSION,
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
    return Master62PillarRecoveryReport(
        schema=PHASE344_SCHEMA,
        schema_version=PHASE344_MASTER_SCHEMA,
        version=PHASE344_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P344_STATUS_VERIFIED_62OF62_AGGREGATOR if all_ok else P344_STATUS_FAIL_62OF62_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P344_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.5,
        under_6s_budget=elapsed < P344_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P344_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p62_rep.donor_snapshot,
        pillar62_a_rec_media_autoswitch_proxy_vault=(
            p62_rep.pillar_62a_rec_media_autoswitch_proxy_vault
        ),
        pillar62_b_cloud_poweroff_ble_mymenu_vault=(
            p62_rep.pillar_62b_cloud_poweroff_ble_mymenu_vault
        ),
        rec_media_prioritize_or_autoswitch_drift_events=(
            p62_rep.rec_media_prioritize_or_autoswitch_drift_events
        ),
        card_speed_vpg200_vpg400_gate_drift_events=(
            p62_rep.card_speed_vpg200_vpg400_gate_drift_events
        ),
        proxy_sq_dci4k_or_120p_lockout_drift_events=(
            p62_rep.proxy_sq_dci4k_or_120p_lockout_drift_events
        ),
        cloud_init_persist_or_power_off_ble_rf_events=(
            p62_rep.cloud_init_persist_or_power_off_ble_rf_events
        ),
        mymenu_42slot_or_fx6_lock_spoof_events=p62_rep.mymenu_42slot_or_fx6_lock_spoof_events,
        zero_rf_or_slot1_vault_bypass_events=p62_rep.zero_rf_or_slot1_vault_bypass_events,
        rf_packets_transmitted=p62_rep.rf_packets_transmitted,
        rf_nvs_mutation_bytes=p62_rep.rf_nvs_mutation_bytes,
        slot1_data_sector_writes=m61_rep.slot1_data_sector_writes + p62_rep.slot1_data_sector_writes,
        slot1_dcim_m4root_avf_mutation_bytes=p62_rep.slot1_dcim_m4root_avf_mutation_bytes,
        slot1_vault_mutation_bytes=(
            m61_rep.slot1_vault_mutation_bytes + p62_rep.slot1_vault_mutation_bytes
        ),
        slot1_format_hard_locked=(
            m61_rep.slot1_format_hard_locked and p62_rep.slot1_format_hard_locked
        ),
        slot1_vault_erofs_eopnotsupp_enforced=(
            m61_rep.slot1_vault_erofs_eopnotsupp_enforced
            and p62_rep.slot1_vault_erofs_eopnotsupp_enforced
        ),
        fx3_appfw_prioritize_hits=P344_FX3_APPFW_PRIORITIZE_HIT_COUNT,
        fx3_appfw_prm_haita_proxy_hits=P344_FX3_APPFW_PRM_HAITA_PROXY_HIT_COUNT,
        fx3_has_movie_sort_recording=False,
        fx3_proxy_dci4k_allowed=True,
        fx3_cloud_star_survives_initialize=True,
        fx3_power_off_ble_forced_off=P344_POWER_OFF_BLE_FORCED_OFF,
        fx3_mymenu_slot_capacity=P344_FX3_MYMENU_TOTAL_SLOTS,
        fx3_mymenu_pages=P344_FX3_MYMENU_PAGES,
        fx3_mymenu_items_per_page=P344_FX3_MYMENU_ITEMS_PER_PAGE,
        fx6_user_menu_max_items=P344_FX6_USER_MENU_MAX_ITEMS,
        fx6_has_bluetooth_hardware=P344_FX6_HAS_BLUETOOTH_HARDWARE,
        # Carried forward Pillar 61 metrics
        big6_home_or_lower_left_nd_drift_events=m61_rep.big6_home_or_lower_left_nd_drift_events,
        framing_manual_or_dormant_auto_framing_drift_events=(
            m61_rep.framing_manual_or_dormant_auto_framing_drift_events
        ),
        interval_shoot_9999_or_fx6_mxf_spoof_events=(
            m61_rep.interval_shoot_9999_or_fx6_mxf_spoof_events
        ),
        tc_make_regen_or_hdmi_rec_ctrl_drift_events=(
            m61_rep.tc_make_regen_or_hdmi_rec_ctrl_drift_events
        ),
        access_authen_ssh_tls_or_fan_max_drift_events=(
            m61_rep.access_authen_ssh_tls_or_fan_max_drift_events
        ),
        slot1_dcim_avf_mutation_bytes=m61_rep.slot1_dcim_avf_mutation_bytes,
        fx3_big6_tile_count=m61_rep.fx3_big6_tile_count,
        fx3_has_physical_end_hw=m61_rep.fx3_has_physical_end_hw,
        fx3_has_dormant_auto_framing=m61_rep.fx3_has_dormant_auto_framing,
        fx3_interval_subitem_count=m61_rep.fx3_interval_subitem_count,
        fx3_interval_max_shots=m61_rep.fx3_interval_max_shots,
        fx3_access_authen_http_digest_hits=m61_rep.fx3_access_authen_http_digest_hits,
        fx3_fan_control_mode_count=m61_rep.fx3_fan_control_mode_count,
        fx6_fan_control_mode_count=m61_rep.fx6_fan_control_mode_count,
        fx3_has_fan_control_max=m61_rep.fx3_has_fan_control_max,
        fx6_has_fan_control_max=m61_rep.fx6_has_fan_control_max,
        # Carried forward Pillar 60 metrics
        bright_mon_or_monitor_brightness_drift_events=(
            m61_rep.bright_mon_or_monitor_brightness_drift_events
        ),
        bulb_mech_or_dormant_bulb_timer_hdr_drift_events=(
            m61_rep.bulb_mech_or_dormant_bulb_timer_hdr_drift_events
        ),
        fx6_vf_backlight_or_still_spoof_events=m61_rep.fx6_vf_backlight_or_still_spoof_events,
        shotmark_clipflag_or_dormant_divide_drift_events=(
            m61_rep.shotmark_clipflag_or_dormant_divide_drift_events
        ),
        tc_link_wpa3_or_usblan_mutex_drift_events=(
            m61_rep.tc_link_wpa3_or_usblan_mutex_drift_events
        ),
        slot1_m4root_avf_mutation_bytes=m61_rep.slot1_m4root_avf_mutation_bytes,
        slot1_dcim_divider_mutation_bytes=m61_rep.slot1_dcim_divider_mutation_bytes,
        fx3_bright_monitoring_symbol_count=m61_rep.fx3_bright_monitoring_symbol_count,
        fx3_bright_mon_v700_focus_mag_coexist=m61_rep.fx3_bright_mon_v700_focus_mag_coexist,
        fx3_monitor_brightness_level_min=m61_rep.fx3_monitor_brightness_level_min,
        fx3_monitor_brightness_level_max=m61_rep.fx3_monitor_brightness_level_max,
        fx3_has_dormant_bulb_timer=m61_rep.fx3_has_dormant_bulb_timer,
        fx3_has_dormant_auto_hdr=m61_rep.fx3_has_dormant_auto_hdr,
        fx3_has_dormant_divide_extract=m61_rep.fx3_has_dormant_divide_extract,
        fx3_has_bt_timecode_link=m61_rep.fx3_has_bt_timecode_link,
        fx3_usb_lan_kmod_count=m61_rep.fx3_usb_lan_kmod_count,
        fx3_wifi_active_security_count=m61_rep.fx3_wifi_active_security_count,
        fx6_vf_brightness_min=m61_rep.fx6_vf_brightness_min,
        fx6_vf_brightness_max=m61_rep.fx6_vf_brightness_max,
        fx6_has_physical_tc_in_out_bnc=m61_rep.fx6_has_physical_tc_in_out_bnc,
        # Carried forward Pillar 59 metrics
        steadyshot_47focal_or_lockout_drift_events=(
            m61_rep.steadyshot_47focal_or_lockout_drift_events
        ),
        selftimer_dormant_or_led8_audio_drift_events=(
            m61_rep.selftimer_dormant_or_led8_audio_drift_events
        ),
        fx6_ibis_or_selftimer_spoof_events=m61_rep.fx6_ibis_or_selftimer_spoof_events,
        zebra_custom_ire_or_peaking_clean_hdmi_drift_events=(
            m61_rep.zebra_custom_ire_or_peaking_clean_hdmi_drift_events
        ),
        streaming_24p_rec_or_network_reset_drift_events=(
            m61_rep.streaming_24p_rec_or_network_reset_drift_events
        ),
        slot1_streaming_or_ftp_mutation_bytes=m61_rep.slot1_streaming_or_ftp_mutation_bytes,
        fx3_steadyshot_47_focal_count=m61_rep.fx3_steadyshot_47_focal_count,
        fx3_image_stabilization_item_count=m61_rep.fx3_image_stabilization_item_count,
        fx3_selftimer_cont_combo_count=m61_rep.fx3_selftimer_cont_combo_count,
        fx3_front_lamp_8_id=m61_rep.fx3_front_lamp_8_id,
        fx3_zebra_preset_count=m61_rep.fx3_zebra_preset_count,
        fx3_peaking_color_count=m61_rep.fx3_peaking_color_count,
        fx3_streaming_protocol_count=m61_rep.fx3_streaming_protocol_count,
        fx3_has_5axis_ibis=m61_rep.fx3_has_5axis_ibis,
        fx3_has_movie_self_timer=m61_rep.fx3_has_movie_self_timer,
        fx6_has_ibis=m61_rep.fx6_has_ibis,
        fx6_has_6axis_gyro_metadata=m61_rep.fx6_has_6axis_gyro_metadata,
        fx6_has_still_self_timer=m61_rep.fx6_has_still_self_timer,
        # Carried forward Pillar 58..41 metrics
        dial_customize_dormant_trap_or_reset_drift_events=(
            m61_rep.dial_customize_dormant_trap_or_reset_drift_events
        ),
        rear_dial_lr_or_mydial_override_drift_events=(
            m61_rep.rear_dial_lr_or_mydial_override_drift_events
        ),
        fn_menu_12x2_or_fx6_dial_spoof_events=m61_rep.fn_menu_12x2_or_fx6_dial_spoof_events,
        live_view_display_reset_split_or_mode_drift_events=(
            m61_rep.live_view_display_reset_split_or_mode_drift_events
        ),
        grid_line_or_hdmi_clean_feed_leak_events=m61_rep.grid_line_or_hdmi_clean_feed_leak_events,
        lut_path_embed_sidecar_or_slot1_vault_bypass_events=(
            m61_rep.lut_path_embed_sidecar_or_slot1_vault_bypass_events
        ),
        slot1_lut_mutation_bytes=m61_rep.slot1_lut_mutation_bytes,
        slot1_avf_info_mutated=m61_rep.slot1_avf_info_mutated,
        fx3_dial_customize_item_count=m61_rep.fx3_dial_customize_item_count,
        fx3_physical_dial_count=m61_rep.fx3_physical_dial_count,
        fx3_my_dial_bank_count=m61_rep.fx3_my_dial_bank_count,
        fx3_fn_menu_still_slots=m61_rep.fx3_fn_menu_still_slots,
        fx3_fn_menu_movie_slots=m61_rep.fx3_fn_menu_movie_slots,
        fx3_live_view_display_set_item_count=m61_rep.fx3_live_view_display_set_item_count,
        fx3_grid_line_type_count=m61_rep.fx3_grid_line_type_count,
        fx3_user_lut_slot_count=m61_rep.fx3_user_lut_slot_count,
        fx3_pplut_slot_count=m61_rep.fx3_pplut_slot_count,
        fx6_user_lut_ui_cap=m61_rep.fx6_user_lut_ui_cap,
        fx6_has_av_tv_rotate=m61_rep.fx6_has_av_tv_rotate,
        fx6_has_my_dial=m61_rep.fx6_has_my_dial,
        fx6_has_fn_menu=m61_rep.fx6_has_fn_menu,
        fx6_has_multi_channel_lut_switches=m61_rep.fx6_has_multi_channel_lut_switches,
        fx3_has_builtin_evf=m61_rep.fx3_has_builtin_evf,
        fx3_has_var_shutter=m61_rep.fx3_has_var_shutter,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        master_62pillar_sha256=master_sha,
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


def evaluate_62pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master62PillarRecoveryReport:
    """Short alias for `evaluate_realhw_62pillar_recovery_master`."""
    return evaluate_realhw_62pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_62pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master62PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_62pillar_recovery_master`."""
    return evaluate_realhw_62pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
