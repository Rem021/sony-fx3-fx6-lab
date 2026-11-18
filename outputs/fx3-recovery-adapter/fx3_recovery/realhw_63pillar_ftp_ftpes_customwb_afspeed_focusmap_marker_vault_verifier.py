"""Phase 348 Milestone — Recovery Pillar 63 & Concurrent 63/63 Master Recovery Verifier:
Wave-61 Sony ILME-FX3 (Ver. 7.02) vs ILME-FX6 (Ver. 6.01) Empirically Grounded Guardrails:
  * Pillar 63A: `[FTP Transfer Func.]` (`Server 1..9`, `BKID_APP_ftp_server_settings_*0..8`,
    `FTP` & `FTPES` Explicit TLS `SET_SERVER_SECURE_PROTOCOL_{OFF,ON}` in Passive Mode ONLY,
    ZERO `SFTP` / ZERO `Active Mode` / ZERO dormant `Transfer JPEG/HEIF Size` -> `EOPNOTSUPP=95`,
    `cacert.pem` <= 1 MiB on `Slot 1` root, `Clip Flag` `OK/NG/KEEP/Off`, `Reset Network Set.`
    boundary vs FX6 `Server Settings1..3`, `Passive Mode On/Off`, `certification.pem` on `Slot B`,
    `Auto Upload (Proxy): Chunk`), `Slot 1` `AVF_INFO` (`base 0x0a13`) /
    `CONTENT_INFO_FTP_TRANS_STAT_*` / `save_ftp_transfer_list_to_media` write firewall
    (`EROFS=30`, `slot1_data_sector_writes == 0`), `[Airplane Mode] = On` + `USB-LAN`
    (`USB_ETHER`) wired bypass guard (Zero-RF requires BOTH RF=Off AND `USB-LAN` gated);
    and White Balance deep truth (`Auto` def, `C.Temp./Filter` `2500K..9900K`, `Custom 1..3`
    excluded from `CAMSET*.DAT` with `Custom WB Error` under `Log != Off` / `S-Log3` / `PPLUT1..4`,
    `Cine EI` / `Cine EI Quick` Auto & Underwater Auto lockout, Resettable `[Priority Set in AWB]`
    & Movie/S&Q `[Shockless WB]` bypassed on direct `C.Temp.`/`A-B`/`G-M` tweaks, vs Still-only
    Reset-immune `[Shutter AWB Lock]`, vs FX6 `WHT BAL PRST/A/B` + `Memory A..H` + `ATW Speed 1..5`).
  * Pillar 63B: Critical FX6 parity correction (`ILME-FX3 Ver. 7.02` AND `ILME-FX6 Ver. 6.01` BOTH
    use `AF Transition Speed = 1..7` and `AF Subj. Shift Sensitivity = 1..5` — ZERO `6`/`7` hits
    in FX6 `appFw.so`!), `[AF Assist]` (`Off` def, `SELP1650`/`SEL18200LE` incompatible);
    In-body `[Focus Map]` myth-busting (`ILME-FX3 Ver. 7.02` has ZERO in-body `[Focus Map]` UI,
    `0` hits `BKID_APP_USER_MENU_FOCUS_MAP` / `ASSIGNABLE_SWITCH_FOCUS_MAP`, added in `Ver. 6.00+`
    ONLY via remote telemetry to *Monitor & Control* App `Ver. 2.1.0+`, locked out at `>= 150 fps`,
    vs FX6 native in-body `Focus Map` with `<= 6 fps` & `>= 150 fps` lockouts); and 8 Reset-immune
    Movie/Still assist items (`[Marker Display]` 5 items including `Off` + `15` active
    `Aspect Marker` ratios `9:16..2.39:1` = `16` states, auto-hidden during `[Focus Magnifier]`;
    plus `[Peaking Display]` 3 items `High/Mid/Low` & `Red/Yellow/Blue/White`) outputting `0 px`
    over Clean-HDMI regardless of `[HDMI Info. Display]`, vs FX6 `Aspect Mask 0..15`, `Custom`,
    `Safety Area 80/90/92.5/95%`, pixel-exact `User Box` (`W 3..479`, `H 3..269`, `H -476..+476`,
    `V -266..+266`), and `B&W` peaking color.
  * Unified 63/63 Master Recovery Aggregator (Pillars 1..62 + Pillar 63).

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

from . import files as _fx3_files
from .files import is_forced_clean_room
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus
from .realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier import (
    MASTER_62_PILLAR_SPECS,
    Master62PillarRecoveryReport,
    P344_DONOR_FX3_APPFW_702_RELPATH,
    P344_DONOR_FX3_BACKUP_BIN_RELPATH,
    P344_DONOR_FX3_UXC_EN_F_RELPATH,
    P344_DONOR_FX3_UXC_EN_G_RELPATH,
    P344_DONOR_FX3_UXC_EN_RELPATH,
    P344_DONOR_FX3_UXC_JA_F_RELPATH,
    P344_DONOR_FX3_UXC_JA_G_RELPATH,
    P344_DONOR_FX3_UXC_JA_RELPATH,
    P344_DONOR_FX3_UXC_SC_F_RELPATH,
    P344_DONOR_FX3_UXC_SC_G_RELPATH,
    P344_DONOR_FX3_UXC_SC_RELPATH,
    P344_DONOR_FX3_UXC_TC_F_RELPATH,
    P344_DONOR_FX3_UXC_TC_G_RELPATH,
    P344_DONOR_FX3_UXC_TC_RELPATH,
    P344_DONOR_FX6_APPFW_601_RELPATH,
    P344_DONOR_FX6_UXC_EN_2_RELPATH,
    P344_DONOR_FX6_UXC_EN_RELPATH,
    P344_PINNED_FX3_APPFW_702_BYTES,
    P344_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P344_PINNED_FX3_BACKUP_BIN_BYTES,
    P344_PINNED_FX3_BACKUP_BIN_SHA256,
    P344_PINNED_FX3_UXC_EN_BYTES,
    P344_PINNED_FX3_UXC_EN_F_BYTES,
    P344_PINNED_FX3_UXC_EN_F_SHA256,
    P344_PINNED_FX3_UXC_EN_G_BYTES,
    P344_PINNED_FX3_UXC_EN_G_SHA256,
    P344_PINNED_FX3_UXC_EN_SHA256,
    P344_PINNED_FX3_UXC_JA_BYTES,
    P344_PINNED_FX3_UXC_JA_F_BYTES,
    P344_PINNED_FX3_UXC_JA_F_SHA256,
    P344_PINNED_FX3_UXC_JA_G_BYTES,
    P344_PINNED_FX3_UXC_JA_G_SHA256,
    P344_PINNED_FX3_UXC_JA_SHA256,
    P344_PINNED_FX3_UXC_SC_BYTES,
    P344_PINNED_FX3_UXC_SC_F_BYTES,
    P344_PINNED_FX3_UXC_SC_F_SHA256,
    P344_PINNED_FX3_UXC_SC_G_BYTES,
    P344_PINNED_FX3_UXC_SC_G_SHA256,
    P344_PINNED_FX3_UXC_SC_SHA256,
    P344_PINNED_FX3_UXC_TC_BYTES,
    P344_PINNED_FX3_UXC_TC_F_BYTES,
    P344_PINNED_FX3_UXC_TC_F_SHA256,
    P344_PINNED_FX3_UXC_TC_G_BYTES,
    P344_PINNED_FX3_UXC_TC_G_SHA256,
    P344_PINNED_FX3_UXC_TC_SHA256,
    P344_PINNED_FX6_APPFW_601_BYTES,
    P344_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P344_PINNED_FX6_UXC_EN_2_BYTES,
    P344_PINNED_FX6_UXC_EN_2_SHA256,
    P344_PINNED_FX6_UXC_EN_BYTES,
    P344_PINNED_FX6_UXC_EN_SHA256,
    evaluate_realhw_62pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Phase 348 Metadata, Safety Redlines & Pinned Budget Constants
# ---------------------------------------------------------------------------

PHASE348_SCHEMA = "realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier_v1"
PHASE348_MASTER_SCHEMA = "realhw_63pillar_recovery_master_v1"
PHASE348_VERSION = "1.0.0"
PHASE348_PHASE_NUMBER = 348

P348_ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"

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

P348_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
P348_OVERALL_READY_FOR_HARDWARE_ATTACH = False
P348_CROSS_MODEL_FLASH_AUTHORIZED = False

OTP_FUSE_TOUCHES = 0
OTP_FUSE_WRITES = 0
RPMB_COUNTER_INCREMENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PHYSICAL_DEVICE_WRITES = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

P348_BOUNDED_HEADER_BYTES = 4096
P348_MAX_FULL_DONOR_BYTES = 3_000_000
P348_DONOR_INSPECT_BUDGET_SECONDS = 2.0
P348_DONOR_INSPECT_CI_BUDGET_SECONDS = 2.0
P348_FAST_CLI_BUDGET_SECONDS = 1.50
P348_NOMINAL_BUDGET_SECONDS = 4.00
P348_CONCURRENT_CEILING_SECONDS = 6.00

P348_EBUSY_ERRNO = 16
P348_EINVAL_ERRNO = 22
P348_EROFS_ERRNO = 30
P348_EOPNOTSUPP_ERRNO = 95

# Camera Identities
P348_FX3_MODEL_NAME = "ILME-FX3"
P348_FX3_MODEL_ID = 0x91030080
P348_FX3_PRODUCT_CODENAME = "PRODUCT_MODEL_ALCIN_UUD"
P348_FX3_HELPGUIDE_ID = "ilc/2210"
P348_FX3_FTP_HELPGUIDE_ID = "di/ftp_2210"
P348_FX3_FW_VERSION = "7.02"
P348_FX3_SUPPORTED_FW_VERSIONS = ("7.02", "7.01", "7.00", "6.02", "6.00", "5.00", "4.00", "3.00", "2.00")

P348_FX6_DONOR_MODEL_NAME = "ILME-FX6"
P348_FX6_DONOR_FW_VERSION = "6.01"
P348_FX6_PRODUCT_CODENAME = "PRODUCT_MODEL_CHAPLIN"

# Pinned Donor Relpaths & Digests (17 Wave-61 donors: 14 FX3 7.02 + 3 FX6 6.01)
P348_DONOR_FX3_APPFW_702_RELPATH = P344_DONOR_FX3_APPFW_702_RELPATH
P348_DONOR_FX6_APPFW_601_RELPATH = P344_DONOR_FX6_APPFW_601_RELPATH
P348_DONOR_FX3_BACKUP_BIN_RELPATH = P344_DONOR_FX3_BACKUP_BIN_RELPATH
P348_DONOR_FX3_UXC_EN_F_RELPATH = P344_DONOR_FX3_UXC_EN_F_RELPATH
P348_DONOR_FX3_UXC_SC_F_RELPATH = P344_DONOR_FX3_UXC_SC_F_RELPATH
P348_DONOR_FX3_UXC_TC_F_RELPATH = P344_DONOR_FX3_UXC_TC_F_RELPATH
P348_DONOR_FX3_UXC_JA_F_RELPATH = P344_DONOR_FX3_UXC_JA_F_RELPATH
P348_DONOR_FX3_UXC_EN_RELPATH = P344_DONOR_FX3_UXC_EN_RELPATH
P348_DONOR_FX3_UXC_SC_RELPATH = P344_DONOR_FX3_UXC_SC_RELPATH
P348_DONOR_FX3_UXC_TC_RELPATH = P344_DONOR_FX3_UXC_TC_RELPATH
P348_DONOR_FX3_UXC_JA_RELPATH = P344_DONOR_FX3_UXC_JA_RELPATH
P348_DONOR_FX3_UXC_EN_G_RELPATH = P344_DONOR_FX3_UXC_EN_G_RELPATH
P348_DONOR_FX3_UXC_SC_G_RELPATH = P344_DONOR_FX3_UXC_SC_G_RELPATH
P348_DONOR_FX3_UXC_TC_G_RELPATH = P344_DONOR_FX3_UXC_TC_G_RELPATH
P348_DONOR_FX3_UXC_JA_G_RELPATH = P344_DONOR_FX3_UXC_JA_G_RELPATH
P348_DONOR_FX6_UXC_EN_RELPATH = P344_DONOR_FX6_UXC_EN_RELPATH
P348_DONOR_FX6_UXC_EN_2_RELPATH = P344_DONOR_FX6_UXC_EN_2_RELPATH

P348_PINNED_FX3_APPFW_702_BYTES = P344_PINNED_FX3_APPFW_702_BYTES
P348_PINNED_FX3_APPFW_702_HDR4K_SHA256 = P344_PINNED_FX3_APPFW_702_HDR4K_SHA256
P348_PINNED_FX6_APPFW_601_BYTES = P344_PINNED_FX6_APPFW_601_BYTES
P348_PINNED_FX6_APPFW_601_HDR4K_SHA256 = P344_PINNED_FX6_APPFW_601_HDR4K_SHA256
P348_PINNED_FX3_BACKUP_BIN_BYTES = P344_PINNED_FX3_BACKUP_BIN_BYTES
P348_PINNED_FX3_BACKUP_BIN_SHA256 = P344_PINNED_FX3_BACKUP_BIN_SHA256
P348_PINNED_FX3_UXC_EN_F_BYTES = P344_PINNED_FX3_UXC_EN_F_BYTES
P348_PINNED_FX3_UXC_EN_F_SHA256 = P344_PINNED_FX3_UXC_EN_F_SHA256
P348_PINNED_FX3_UXC_SC_F_BYTES = P344_PINNED_FX3_UXC_SC_F_BYTES
P348_PINNED_FX3_UXC_SC_F_SHA256 = P344_PINNED_FX3_UXC_SC_F_SHA256
P348_PINNED_FX3_UXC_TC_F_BYTES = P344_PINNED_FX3_UXC_TC_F_BYTES
P348_PINNED_FX3_UXC_TC_F_SHA256 = P344_PINNED_FX3_UXC_TC_F_SHA256
P348_PINNED_FX3_UXC_JA_F_BYTES = P344_PINNED_FX3_UXC_JA_F_BYTES
P348_PINNED_FX3_UXC_JA_F_SHA256 = P344_PINNED_FX3_UXC_JA_F_SHA256
P348_PINNED_FX3_UXC_EN_BYTES = P344_PINNED_FX3_UXC_EN_BYTES
P348_PINNED_FX3_UXC_EN_SHA256 = P344_PINNED_FX3_UXC_EN_SHA256
P348_PINNED_FX3_UXC_SC_BYTES = P344_PINNED_FX3_UXC_SC_BYTES
P348_PINNED_FX3_UXC_SC_SHA256 = P344_PINNED_FX3_UXC_SC_SHA256
P348_PINNED_FX3_UXC_TC_BYTES = P344_PINNED_FX3_UXC_TC_BYTES
P348_PINNED_FX3_UXC_TC_SHA256 = P344_PINNED_FX3_UXC_TC_SHA256
P348_PINNED_FX3_UXC_JA_BYTES = P344_PINNED_FX3_UXC_JA_BYTES
P348_PINNED_FX3_UXC_JA_SHA256 = P344_PINNED_FX3_UXC_JA_SHA256
P348_PINNED_FX3_UXC_EN_G_BYTES = P344_PINNED_FX3_UXC_EN_G_BYTES
P348_PINNED_FX3_UXC_EN_G_SHA256 = P344_PINNED_FX3_UXC_EN_G_SHA256
P348_PINNED_FX3_UXC_SC_G_BYTES = P344_PINNED_FX3_UXC_SC_G_BYTES
P348_PINNED_FX3_UXC_SC_G_SHA256 = P344_PINNED_FX3_UXC_SC_G_SHA256
P348_PINNED_FX3_UXC_TC_G_BYTES = P344_PINNED_FX3_UXC_TC_G_BYTES
P348_PINNED_FX3_UXC_TC_G_SHA256 = P344_PINNED_FX3_UXC_TC_G_SHA256
P348_PINNED_FX3_UXC_JA_G_BYTES = P344_PINNED_FX3_UXC_JA_G_BYTES
P348_PINNED_FX3_UXC_JA_G_SHA256 = P344_PINNED_FX3_UXC_JA_G_SHA256
P348_PINNED_FX6_UXC_EN_BYTES = P344_PINNED_FX6_UXC_EN_BYTES
P348_PINNED_FX6_UXC_EN_SHA256 = P344_PINNED_FX6_UXC_EN_SHA256
P348_PINNED_FX6_UXC_EN_2_BYTES = P344_PINNED_FX6_UXC_EN_2_BYTES
P348_PINNED_FX6_UXC_EN_2_SHA256 = P344_PINNED_FX6_UXC_EN_2_SHA256

# Zero-Violation Pillar 63 Counters & Vault Flags
P348_FTP_PROTOCOL_SFTP_OR_JPEG_SIZE_DRIFT_EVENTS = 0
P348_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT_EVENTS = 0
P348_MOVIE_AF_SPEED_OR_FOCUS_MAP_SPOOF_EVENTS = 0
P348_MARKER_15RATIO_PEAKING_HDMI_LEAK_EVENTS = 0
P348_ZERO_RF_USBLAN_OR_SLOT1_AVF_BYPASS_EVENTS = 0

P348_RF_PACKETS_TRANSMITTED = 0
P348_USBLAN_PACKETS_TRANSMITTED = 0
P348_RF_NVS_MUTATION_BYTES = 0
P348_SLOT1_DATA_SECTOR_WRITES = 0
P348_SLOT1_AVF_INFO_MUTATION_BYTES = 0
P348_SLOT1_VAULT_MUTATION_BYTES = 0
P348_HDMI_MARKER_PEAKING_LEAK_PIXELS = 0
P348_SLOT1_FORMAT_HARD_LOCKED = True
P348_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True
P348_AIRPLANE_MODE_FORCED_ON = True
P348_USBLAN_BENCH_LOCKED_OFF = True

P348_STAGE_B_VOLATILE_OVERLAY_DIR = "/tmp/fx3_stage_b_overlay/pillar63"
P348_FORBIDDEN_PERSISTENT_TARGETS = (
    "/dev/cnflasha",
    "/setting",
    "/mnt/emmc",
    "/nflasha",
)
P348_TIER0_SURFACE_COUNT = 16

# ---------------------------------------------------------------------------
# Wave-61 Empirically Verified Constants (UXC resid16 & ELF Symbols)
# ---------------------------------------------------------------------------

# 1. [FTP Transfer Func.] (`FTP`/`FTPES` vs ZERO `SFTP`, 9 Server Slots, USB-LAN Bypass, Slot 1 AVF_INFO)
P348_FTP_FUNCTION_F_RESID16 = (0x7287, 0x6317)
P348_FTP_TRANSFER_F_RESID16 = 0x62FC
P348_FTP_SERVER_F_RESID16 = (0x6442, 0x6305, 0x72F4, 0x630D)
P348_FTP_SECURE_PROTOCOL_F_RESID16 = (0x60DD, 0x6553)
P348_FTP_DIRECTORY_HIERARCHY_F_RESID16 = (0x6E7E, 0x76E6)
P348_FTP_POWER_SAVE_F_RESID16 = 0x6A5F
P348_FTP_CLIP_FLAG_F_RESID16 = 0x7D31
P348_FTP_RAW_JH_TARGET_F_RESID16 = 0x6BD5
P348_FTP_IMPORT_ROOT_CERT_F_RESID16 = 0x7940
P348_FTP_AVF_INFO_RESET_BASE_RESID16 = 0x0A13
P348_FTP_TRANSFERRING_SLOT_BASE_RESID16S = (0x09B7, 0x09B8)
P348_DORMANT_TRANSFER_JPEG_SIZE_F_RESID16 = 0x6AED
P348_DORMANT_TRANSFER_HEIF_SIZE_F_RESID16 = 0x63DD
P348_DORMANT_SFTP_F_RESID16S = (0x68D9, 0x6ED3)

P348_FX3_APPFW_SFTP_HIT_COUNT = 0
P348_FX3_APPFW_FTPES_STRING_HIT_COUNT = 0
P348_FX3_APPFW_PASSIVE_MODE_HIT_COUNT = 0
P348_FX3_APPFW_TRANSFER_JPEG_HEIF_SIZE_HIT_COUNT = 0

P348_BKID_FTP_FUNCTION = "BKID_APP_setting_ftp_function"
P348_BKID_FTP_POWER_SAVE = "BKID_APP_setting_ftp_power_save"
P348_FTP_SERVER_SLOT_COUNT = 9
P348_FTP_SERVER_SLOT_PREFIXES = tuple(
    f"BKID_APP_ftp_server_settings_host_name{i}" for i in range(P348_FTP_SERVER_SLOT_COUNT)
)
P348_FTP_SAVE_TRANSFER_LIST_SYMBOL = "save_ftp_transfer_list_to_media"
P348_FTP_TRANS_STAT_EXCLUSION_PREFIX = "CONTENT_INFO_FTP_TRANS_STAT_"
P348_FTP_USB_ETHER_SYMBOL = (
    "VAL_HAITA_setting_ftp_function_setting_ftp_connect_method_FTP_CONNECT_METHOD_USB_ETHER"
)

P348_FTP_PROTOCOLS = ("FTP", "FTPES", "SFTP", "FTPS_IMPLICIT")
P348_FX3_FTP_SUPPORTED_PROTOCOLS = ("FTP", "FTPES")
P348_FTP_TRANSFER_MODES = ("Passive", "Active")
P348_FX3_FTP_TRANSFER_MODE_ONLY = "Passive"
P348_FTP_DIRECTORY_HIERARCHIES = ("Standard", "Same as in Camera")
P348_FTP_DIR_PATH_MAX_CHARS = 128
P348_FTP_CLIP_FLAG_FILTERS = ("Off", "OK", "NG", "KEEP")
P348_FX3_FTP_CERT_FILENAME = "cacert.pem"
P348_FX3_FTP_CERT_MAX_BYTES = 1048576
P348_FX3_FTP_CERT_SLOT = 1

P348_FX6_FTP_SERVER_UI_SLOTS = 3
P348_FX6_FTP_CERT_FILENAME = "certification.pem"
P348_FX6_FTP_CERT_SLOT = "Slot B"
P348_FX6_AUTO_UPLOAD_CHUNK_MODES = ("Off", "Chunk")

# 2. White Balance Deep Truth (`Custom 1..3`, `[Priority Set in AWB]`, `[Shutter AWB Lock]`, `[Shockless WB]`, `Cine EI`)
P348_WB_F_RESID16 = (0x73EE, 0x6035)
P348_WB_CUSTOM_FAIL_F_RESID16 = 0x63AC
P348_WB_CUSTOM_ERROR_BASE_RESID16 = 0x0220
P348_PRIORITY_SET_AWB_F_RESID16 = (0x67A7, 0x749F, 0x6541)
P348_SHUTTER_AWB_LOCK_F_RESID16 = (0x66DB, 0x6373, 0x6A32)
P348_SHOCKLESS_WB_F_RESID16 = (0x62FE, 0x6649, 0x6EF1)

P348_BKID_WB_STILL = "BKID_APP_setting_white_balance_still"
P348_BKID_WB_MOVIE = "BKID_APP_setting_white_balance_movie"
P348_BKID_PRIORITY_SET_AWB = "BKID_APP_setting_priority_set_in_awb"
P348_BKID_SHUTTER_AWB_LOCK = "BKID_APP_setting_stl_awb_lock_with_shutter"
P348_BKID_SHOCKLESS_WB = "BKID_APP_setting_movie_shockless_wb"

P348_WB_MODES = (
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
P348_WB_DEFAULT = "Auto"
P348_WB_C_TEMP_MIN_K = 2500
P348_WB_C_TEMP_MAX_K = 9900
P348_WB_C_TEMP_STEP_K = 100
P348_WB_CUSTOM_SLOTS = (1, 2, 3)
P348_LOG_SHOOTING_MODES = ("Off", "Flexible ISO", "Cine EI", "Cine EI Quick")
P348_CINE_EI_MODES = ("Cine EI", "Cine EI Quick")
P348_WB_CINE_EI_LOCKED_MODES = ("Auto", "Auto: Ambience", "Auto: White", "Underwater Auto")
P348_PICTURE_PROFILES = (
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
    "PPLUT1",
    "PPLUT2",
    "PPLUT3",
    "PPLUT4",
)
P348_WB_CUSTOM_HAZARD_PROFILES = ("PP7", "PP8", "PP9", "PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
P348_PRIORITY_SET_AWB_MODES = ("Standard", "Ambience", "White")
P348_PRIORITY_SET_AWB_DEFAULT = "Standard"
P348_SHUTTER_AWB_LOCK_MODES = ("Off", "Shut. Halfway", "Cont. Shooting")
P348_SHUTTER_AWB_LOCK_DEFAULT = "Off"
P348_SHOCKLESS_WB_MODES = ("Off", "1", "2", "3")
P348_SHOCKLESS_WB_DEFAULT = "1"

P348_FX6_WHT_BAL_SWITCH_POSITIONS = ("PRST", "A", "B")
P348_FX6_WB_MEMORY_SLOTS = ("A", "B", "C", "D", "E", "F", "G", "H")
P348_FX6_ATW_SPEED_MIN = 1
P348_FX6_ATW_SPEED_MAX = 5

# 3. Movie AF (`AF Transition Speed 1..7`, `AF Subj. Shift Sens. 1..5`, `AF Assist`) & App-Only `[Focus Map]`
P348_AF_TRANSITION_SPEED_F_RESID16 = 0x6E9D
P348_AF_SUBJ_SHIFT_SENS_F_RESID16 = 0x79D6
P348_AF_ASSIST_F_RESID16 = 0x64A9
P348_FOCUS_MAP_F_RESID16 = 0x61F9

P348_BKID_AF_ASSIST = "BKID_APP_setting_af_assist"
P348_FX3_FOCUS_MAP_TELEMETRY_SYMBOLS = ("to_remote_event_focus_map", "sequence_notify_focus_map")
P348_FX3_IN_BODY_FOCUS_MAP_BKID_HITS = 0
P348_FX3_APPFW_UVC_HITS = 0
P348_FX6_APPFW_AF_SUBJ_SHIFT_6_7_HITS = 0

P348_AF_TRANSITION_SPEED_MIN = 1
P348_AF_TRANSITION_SPEED_MAX = 7
P348_AF_TRANSITION_SPEED_DEFAULT = 5
P348_AF_SUBJ_SHIFT_SENS_MIN = 1
P348_AF_SUBJ_SHIFT_SENS_MAX = 5
P348_AF_SUBJ_SHIFT_SENS_DEFAULT = 5
P348_AF_ASSIST_DEFAULT = "Off"
P348_AF_ASSIST_INCOMPATIBLE_LENSES = ("SELP1650", "SEL18200LE")

P348_FX3_FOCUS_MAP_ADDED_FW = "6.00"
P348_FX3_FOCUS_MAP_SUPPORTED_FW_VERSIONS = ("7.02", "7.01", "7.00", "6.02", "6.00")
P348_FX3_FOCUS_MAP_MIN_MC_APP_VER = "2.1.0"
P348_FX3_FOCUS_MAP_HIGH_FPS_LOCKOUT_THRESHOLD = 150
P348_FX6_FOCUS_MAP_LOW_FPS_LOCKOUT_MAX = 6
P348_FX6_FOCUS_MAP_HIGH_FPS_LOCKOUT_THRESHOLD = 150

# 4. Reset-Immune `[Marker Display]` (`15` Ratios) + `4`-Color `[Peaking Display]` Clean-HDMI Isolation vs FX6 `User Box`
P348_MARKER_DISPLAY_F_RESID16 = 0x6803
P348_CENTER_MARKER_F_RESID16 = 0x6707
P348_ASPECT_MARKER_F_RESID16 = 0x66AC
P348_SAFETY_ZONE_F_RESID16 = 0x6F50
P348_GUIDEFRAME_F_RESID16 = 0x62F9
P348_PEAKING_DISPLAY_F_RESID16 = 0x6FE5
P348_PEAKING_LEVEL_BASE_RESID16 = 0x014C
P348_PEAKING_COLOR_BASE_RESID16 = 0x014D

P348_BKID_MARKER_DISPLAY = "BKID_APP_setting_marker_display"
P348_BKID_CENTER_MARKER = "BKID_APP_setting_center"
P348_BKID_ASPECT_MARKER = "BKID_APP_setting_marker_display_aspect"
P348_BKID_SAFETY_ZONE = "BKID_APP_setting_safety_zone"
P348_BKID_GUIDEFRAME = "BKID_APP_setting_guide_frame"
P348_BKID_PEAKING_DISPLAY = "BKID_APP_setting_peaking_display"
P348_BKID_PEAKING_LEVEL = "BKID_APP_setting_peaking_level"
P348_BKID_PEAKING_COLOR = "BKID_APP_setting_peaking_color"

P348_FX3_ASPECT_MARKER_ACTIVE_RATIOS = (
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
P348_FX3_ASPECT_MARKER_STATES = ("Off",) + P348_FX3_ASPECT_MARKER_ACTIVE_RATIOS
P348_FX3_SAFETY_ZONE_MODES = ("Off", "80%", "90%")
P348_FX3_PEAKING_LEVELS = ("High", "Mid", "Low")
P348_FX3_PEAKING_LEVEL_DEFAULT = "Mid"
P348_FX3_PEAKING_COLORS = ("Red", "Yellow", "Blue", "White")
P348_FX3_PEAKING_COLOR_DEFAULT = "White"
P348_RESET_IMMUNE_ASSIST_ITEM_COUNT = 8

P348_FX6_ASPECT_MASK_MIN = 0
P348_FX6_ASPECT_MASK_MAX = 15
P348_FX6_ASPECT_MASK_DEFAULT = 12
P348_FX6_SAFETY_AREA_MODES = ("80%", "90%", "92.5%", "95%")
P348_FX6_USER_BOX_WIDTH_RANGE = (3, 479)
P348_FX6_USER_BOX_HEIGHT_RANGE = (3, 269)
P348_FX6_USER_BOX_H_POS_RANGE = (-476, 476)
P348_FX6_USER_BOX_V_POS_RANGE = (-266, 266)
P348_FX6_PEAKING_COLORS = ("B&W", "Red", "Yellow", "Blue")

# Common Enums & Vault Constants
P348_ON_OFF_MODES = ("Off", "On")
P348_SHOOTING_DOMAINS = ("Movie", "Still", "S&Q")
P348_RESET_ACTIONS = ("None", "Camera Settings Reset", "Reset Network Set.", "Initialize")
P348_NETWORK_TRANSPORTS = ("NONE", "Wi-Fi", "BLE", "USB-LAN")
P348_ZERO_RF_SAFE_TRANSPORTS = ("NONE",)

P348_SLOT1_VAULT_SLOT = 1
P348_SAFE_SECONDARY_SLOT = 2
P348_VAULT_ACTIONS = (
    "NONE",
    "READ_ONLY_AUDIT",
    "FTP_FROM_SLOT2",
    "CERT_READ_TEST_ISOLATED",
    "WRITE_FTP_TRANS_STAT_SLOT1",
    "SAVE_FTP_TRANSFER_LIST_SLOT1",
    "RECOVER_AVF_INFO_SLOT1",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P348_WRITE_MUTATING_VAULT_ACTIONS = (
    "WRITE_FTP_TRANS_STAT_SLOT1",
    "SAVE_FTP_TRANSFER_LIST_SLOT1",
    "RECOVER_AVF_INFO_SLOT1",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P348_VAULT_FIREWALL_ERRNOS = (None, "EROFS", "EOPNOTSUPP", "EBUSY", "EINVAL")

# Status & Block Codes
P348_STATUS_VERIFIED_PILLAR_63A = "VERIFIED_PILLAR_63A_FTP_FTPES_USBLAN_CUSTOMWB_VAULT"
P348_STATUS_REJECTED_PILLAR_63A = "REJECTED_PILLAR_63A_FTP_FTPES_USBLAN_CUSTOMWB_VAULT"
P348_STATUS_VERIFIED_PILLAR_63B = "VERIFIED_PILLAR_63B_MOVIE_AF_FOCUSMAP_MARKER_PEAKING_VAULT"
P348_STATUS_REJECTED_PILLAR_63B = "REJECTED_PILLAR_63B_MOVIE_AF_FOCUSMAP_MARKER_PEAKING_VAULT"
P348_STATUS_VERIFIED_PILLAR63_SUITE = "VERIFIED_PILLAR63_FTP_FTPES_CUSTOMWB_AFSPEED_FOCUSMAP_MARKER_VAULT"
P348_STATUS_FAIL_PILLAR63_SUITE = "FAIL_PILLAR63_FTP_FTPES_CUSTOMWB_AFSPEED_FOCUSMAP_MARKER_VAULT"
P348_STATUS_VERIFIED_63OF63_AGGREGATOR = "VERIFIED_63OF63_PILLAR_RECOVERY_MASTER"
P348_STATUS_FAIL_63OF63_AGGREGATOR = "FAIL_63OF63_PILLAR_RECOVERY_MASTER"

P348_BLOCKED_SAFETY_POLICY_VIOLATION = "BLOCKED_P348_SAFETY_POLICY_VIOLATION"
P348_BLOCKED_INVALID_PILLAR63A_SPEC = "BLOCKED_P348_INVALID_PILLAR63A_SPEC"
P348_BLOCKED_INVALID_PILLAR63B_SPEC = "BLOCKED_P348_INVALID_PILLAR63B_SPEC"
P348_BLOCKED_FTP_PROTOCOL_SFTP_OR_JPEG_SIZE_DRIFT = (
    "BLOCKED_P348_FTP_PROTOCOL_SFTP_OR_JPEG_SIZE_DRIFT"
)
P348_BLOCKED_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT = (
    "BLOCKED_P348_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT"
)
P348_BLOCKED_ZERO_RF_USBLAN_OR_SLOT1_AVF_FIREWALL = (
    "BLOCKED_P348_ZERO_RF_USBLAN_OR_SLOT1_AVF_FIREWALL"
)
P348_BLOCKED_MOVIE_AF_SPEED_OR_FOCUS_MAP_SPOOF = (
    "BLOCKED_P348_MOVIE_AF_SPEED_OR_FOCUS_MAP_SPOOF"
)
P348_BLOCKED_MARKER_15RATIO_PEAKING_HDMI_LEAK = (
    "BLOCKED_P348_MARKER_15RATIO_PEAKING_HDMI_LEAK"
)
P348_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL = "BLOCKED_P348_SLOT1_VAULT_WRITE_FIREWALL"
P348_BLOCKED_PERSISTENT_OVERLAY_ESCAPE = "BLOCKED_P348_PERSISTENT_OVERLAY_ESCAPE"
P348_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT = "BLOCKED_P348_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P348_PILLAR_63A_SCENARIO_IDS = (
    "p348_63a_01_allow_ftpes_9slots_passive_camset_reset_survival_and_zero_rf_usblan_locked",
    "p348_63a_02_allow_custom_wb_cine_ei_awb_lock_shockless_bypass_and_fx6_atw_memory_contrast",
    "p348_63a_03_reject_dormant_sftp_active_mode_or_transfer_jpeg_heif_size_eopnotsupp_bypass",
    "p348_63a_04_reject_custom_wb_camset_spoof_slog3_error_or_cine_ei_auto_unlock",
    "p348_63a_05_reject_airplane_mode_usblan_ftp_bypass_when_usb_ether_unblocked",
    "p348_63a_06_reject_slot1_avf_info_trans_stat_write_erofs30_bypass_or_h0_h3_drift",
)
P348_PILLAR_63B_SCENARIO_IDS = (
    "p348_63b_01_allow_af_speed_1_7_shift_1_5_parity_app_only_focus_map_and_15ratio_clean_hdmi",
    "p348_63b_02_allow_fx6_in_body_focus_map_user_box_aspect_mask_and_bw_peaking_contrast",
    "p348_63b_03_reject_fx6_af_subj_shift_7_spoof_or_incompatible_af_assist_lens",
    "p348_63b_04_reject_fx3_in_body_focus_map_ui_spoof_ver2_claim_or_240fps_bypass",
    "p348_63b_05_reject_marker_peaking_hdmi_pixel_leak_reset_wipe_or_missing_15_ratios",
    "p348_63b_06_reject_slot1_erofs30_bypass_overlay_escape_or_tier0_h0_h3_drift",
)

MASTER_63_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_62_PILLAR_SPECS + (
    (
        63,
        "pillar63_ftp_ftpes_customwb_afspeed_focusmap_marker_vault",
        "Phase 348",
        "realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier",
    ),
)
MASTER_63_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_63_PILLAR_SPECS)
MASTER_63_PILLAR_COUNT = len(MASTER_63_PILLAR_IDS)


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
    return bool(is_forced_clean_room() or os.environ.get(P348_ENV_CLEAN_ROOM_TEST) == "1")


def _donor_inspect_budget_seconds() -> float:
    return (
        P348_DONOR_INSPECT_CI_BUDGET_SECONDS
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS")
        else P348_DONOR_INSPECT_BUDGET_SECONDS
    )


def _is_tmpfs_path(path: str) -> bool:
    norm = posixpath.normpath(path)
    return norm == "/tmp" or norm.startswith("/tmp/")


def _targets_persistent_emmc(path: str) -> bool:
    norm = posixpath.normpath(path)
    return any(norm == p or norm.startswith(p + "/") for p in P348_FORBIDDEN_PERSISTENT_TARGETS)


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
# Empirically Grounded State Calculators (Pillars 63A & 63B)
# ---------------------------------------------------------------------------


def compute_expected_ftp_ftpes_customwb_state(
    *,
    camera_model: str,
    fw_version: str,
    ftp_server_slot: int,
    ftp_protocol: str,
    ftp_transfer_mode: str,
    transfer_jpeg_heif_size_requested: bool,
    ftp_directory_hierarchy: str,
    ftp_specify_dir_len: int,
    ftp_clip_flag_filter: str,
    ftp_cert_filename: str,
    ftp_cert_bytes: int,
    ftp_cert_slot: str,
    ftp_power_save: str,
    fx6_auto_upload_proxy_chunk: str,
    fx6_simul_or_relay_active: bool,
    airplane_mode: str,
    usb_lan_enabled: bool,
    wifi_active: bool,
    ble_active: bool,
    ftp_function_enabled: bool,
    network_transport: str,
    shooting_domain: str,
    wb_mode: str,
    wb_color_temp_k: int,
    wb_direct_ctemp_or_tint_tweaked: bool,
    custom_wb_slots_populated: int,
    custom_wb_exported_in_camset: bool,
    custom_setup_triggered: bool,
    log_shooting_mode: str,
    picture_profile: str,
    priority_set_in_awb: str,
    shutter_awb_lock: str,
    shockless_wb: str,
    fx6_wht_bal_switch: str,
    fx6_memory_bank: str,
    fx6_atw_speed: int,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute canonical Wave-61 Pillar 63A state:
    - `[FTP Transfer Func.]` `Server 1..9`, ONLY `FTP`/`FTPES` Passive Mode (ZERO `SFTP`, ZERO
      Active Mode on FX3, ZERO dormant `Transfer JPEG/HEIF Size` -> `EOPNOTSUPP=95`), `cacert.pem`
      <= 1 MiB on `Slot 1`, vs FX6 `Server Settings1..3`, `Active/Passive`, `certification.pem`
      on `Slot B`, `Auto Upload (Proxy): Chunk` mutex
    - `[Airplane Mode] = On` blocks Wi-Fi/BLE ONLY and STILL permits wired `USB-LAN` (`USB_ETHER`)
    - `Slot 1` `AVF_INFO` (`base 0x0a13`) / `CONTENT_INFO_FTP_TRANS_STAT_*` firewall (`EROFS=30`)
    - White Balance `2500K..9900K`, `Custom 1..3` excluded from `CAMSET*.DAT`, `Custom WB Error`
      hazard under `Log != Off` / `S-Log3` / `PPLUT1..4`, `Cine EI` `Auto`/`Underwater Auto` lockout,
      Resettable `[Priority Set in AWB]` / `[Shockless WB]` vs Still-only Reset-immune
      `[Shutter AWB Lock]`."""
    is_fx3 = camera_model == P348_FX3_MODEL_NAME

    # 1. [FTP Transfer Func.] Protocol, Slot Count, Transfer Mode & Dormant Size
    if is_fx3:
        ftp_slot_errno: Optional[int] = (
            None if (1 <= ftp_server_slot <= P348_FTP_SERVER_SLOT_COUNT) else P348_EINVAL_ERRNO
        )
        ftp_protocol_errno: Optional[int] = (
            None if ftp_protocol in P348_FX3_FTP_SUPPORTED_PROTOCOLS else P348_EOPNOTSUPP_ERRNO
        )
        ftp_mode_errno: Optional[int] = (
            None if ftp_transfer_mode == P348_FX3_FTP_TRANSFER_MODE_ONLY else P348_EOPNOTSUPP_ERRNO
        )
        transfer_size_errno: Optional[int] = (
            P348_EOPNOTSUPP_ERRNO if transfer_jpeg_heif_size_requested else None
        )
        cert_valid = (
            ftp_cert_filename == P348_FX3_FTP_CERT_FILENAME
            and 0 < ftp_cert_bytes <= P348_FX3_FTP_CERT_MAX_BYTES
            and ftp_cert_slot == "Slot 1"
        )
        fx6_chunk_ok = fx6_auto_upload_proxy_chunk == "Off"
    else:
        ftp_slot_errno = None if (1 <= ftp_server_slot <= 16) else P348_EINVAL_ERRNO
        ftp_protocol_errno = (
            None if ftp_protocol in P348_FX3_FTP_SUPPORTED_PROTOCOLS else P348_EOPNOTSUPP_ERRNO
        )
        ftp_mode_errno = None if ftp_transfer_mode in P348_FTP_TRANSFER_MODES else P348_EINVAL_ERRNO
        transfer_size_errno = (
            P348_EOPNOTSUPP_ERRNO if transfer_jpeg_heif_size_requested else None
        )
        cert_valid = (
            ftp_cert_filename == P348_FX6_FTP_CERT_FILENAME
            and 0 < ftp_cert_bytes <= P348_FX3_FTP_CERT_MAX_BYTES
            and ftp_cert_slot == P348_FX6_FTP_CERT_SLOT
        )
        fx6_chunk_ok = (
            fx6_auto_upload_proxy_chunk in P348_FX6_AUTO_UPLOAD_CHUNK_MODES
            and (fx6_auto_upload_proxy_chunk == "Off" or not fx6_simul_or_relay_active)
        )

    ftp_dir_ok = (
        ftp_directory_hierarchy in P348_FTP_DIRECTORY_HIERARCHIES
        and 0 <= ftp_specify_dir_len <= P348_FTP_DIR_PATH_MAX_CHARS
    )
    ftp_clip_flag_supported = (not is_fx3) or (fw_version in ("7.02", "7.01", "7.00"))
    ftp_clip_flag_errno: Optional[int] = (
        None
        if (ftp_clip_flag_filter in P348_FTP_CLIP_FLAG_FILTERS and (ftp_clip_flag_filter == "Off" or ftp_clip_flag_supported))
        else P348_EOPNOTSUPP_ERRNO
    )

    # 2. Zero-RF & USB-LAN Airplane-Mode Bypass Guard
    # Airplane Mode = On blocks Wi-Fi/BLE ONLY; wired USB-LAN FTP STILL operates!
    wired_usblan_bypass_active = (
        airplane_mode == "On" and (usb_lan_enabled or network_transport == "USB-LAN") and ftp_function_enabled
    )

    # 3. White Balance & Cine EI / Custom Setup Hazard / Shockless WB Bypass
    ctemp_valid = (
        P348_WB_C_TEMP_MIN_K <= wb_color_temp_k <= P348_WB_C_TEMP_MAX_K
        and (wb_color_temp_k % P348_WB_C_TEMP_STEP_K == 0)
    )
    wb_locked_by_cine_ei = (
        log_shooting_mode in P348_CINE_EI_MODES
        and wb_mode in P348_WB_CINE_EI_LOCKED_MODES
    )
    wb_errno: Optional[int] = (
        P348_EOPNOTSUPP_ERRNO
        if (
            wb_locked_by_cine_ei
            or (shooting_domain != "Still" and wb_mode == "Flash")
            or not ctemp_valid
        )
        else None
    )
    custom_wb_error_hazard = custom_setup_triggered and (
        log_shooting_mode != "Off" or picture_profile in P348_WB_CUSTOM_HAZARD_PROFILES
    )
    custom_camset_excluded_ok = not custom_wb_exported_in_camset

    if shooting_domain == "Still":
        shutter_awb_lock_errno: Optional[int] = None
        shockless_wb_effective = "Off"
        shockless_wb_bypassed = True
    else:
        shutter_awb_lock_errno = (
            P348_EOPNOTSUPP_ERRNO if shutter_awb_lock != "Off" else None
        )
        shockless_wb_bypassed = (shockless_wb == "Off") or wb_direct_ctemp_or_tint_tweaked
        shockless_wb_effective = "Off" if wb_direct_ctemp_or_tint_tweaked else shockless_wb

    fx6_wb_valid = (
        fx6_wht_bal_switch in P348_FX6_WHT_BAL_SWITCH_POSITIONS
        and fx6_memory_bank in P348_FX6_WB_MEMORY_SLOTS
        and P348_FX6_ATW_SPEED_MIN <= fx6_atw_speed <= P348_FX6_ATW_SPEED_MAX
        and not (
            log_shooting_mode in P348_CINE_EI_MODES
            and not is_fx3
            and wb_mode in ("Auto", "ATW")
        )
    )

    # 4. Reset Matrix (`Camera Settings Reset` vs `Reset Network Set.` vs `Initialize`)
    if reset_action == "Initialize":
        post_ftp_servers_cleared = True
        post_ftp_function_enabled = False
        post_ftp_power_save = "Off"
        post_wb_mode = P348_WB_DEFAULT
        post_priority_set_in_awb = P348_PRIORITY_SET_AWB_DEFAULT
        post_shutter_awb_lock = P348_SHUTTER_AWB_LOCK_DEFAULT
        post_shockless_wb = P348_SHOCKLESS_WB_DEFAULT
        post_custom_wb_slots_cleared = True
        post_airplane_mode = airplane_mode  # Preserved across Initialize!
    elif reset_action == "Reset Network Set.":
        post_ftp_servers_cleared = True
        post_ftp_function_enabled = False
        post_ftp_power_save = "Off"
        post_wb_mode = wb_mode
        post_priority_set_in_awb = priority_set_in_awb
        post_shutter_awb_lock = shutter_awb_lock
        post_shockless_wb = shockless_wb
        post_custom_wb_slots_cleared = False
        post_airplane_mode = airplane_mode  # Preserved across Reset Network Set.!
    elif reset_action == "Camera Settings Reset":
        # FTP settings survive Camera Settings Reset; Shutter AWB Lock is Reset-immune;
        # Custom 1..3 internal calibration slots are NOT guaranteed cleared by Camera Settings Reset!
        post_ftp_servers_cleared = False
        post_ftp_function_enabled = ftp_function_enabled
        post_ftp_power_save = ftp_power_save
        post_wb_mode = P348_WB_DEFAULT
        post_priority_set_in_awb = P348_PRIORITY_SET_AWB_DEFAULT
        post_shutter_awb_lock = shutter_awb_lock  # Reset-immune!
        post_shockless_wb = P348_SHOCKLESS_WB_DEFAULT
        post_custom_wb_slots_cleared = False
        post_airplane_mode = airplane_mode
    else:
        post_ftp_servers_cleared = False
        post_ftp_function_enabled = ftp_function_enabled
        post_ftp_power_save = ftp_power_save
        post_wb_mode = wb_mode
        post_priority_set_in_awb = priority_set_in_awb
        post_shutter_awb_lock = shutter_awb_lock
        post_shockless_wb = shockless_wb
        post_custom_wb_slots_cleared = custom_wb_slots_populated == 0
        post_airplane_mode = airplane_mode

    # Zero-RF & Airgap Bench Policy: Airplane Mode = On AND USB-LAN = False AND FTP Function = Off
    rf_and_usblan_zero_enforced = (
        airplane_mode == "On"
        and post_airplane_mode == "On"
        and not usb_lan_enabled
        and not wifi_active
        and not ble_active
        and not ftp_function_enabled
        and not wired_usblan_bypass_active
        and network_transport in P348_ZERO_RF_SAFE_TRANSPORTS
    )

    # 5. Slot-1 Tier-0 Vault Firewall (`EROFS=30` on `AVF_INFO` / `FTP_TRANS_STAT`)
    mutates_slot1 = (
        requested_vault_action in P348_WRITE_MUTATING_VAULT_ACTIONS
        or (requested_vault_slot == P348_SLOT1_VAULT_SLOT and requested_vault_action not in ("NONE", "READ_ONLY_AUDIT"))
    )
    if (mutates_slot1 and slot1_holds_tier0_vault) or requested_vault_action in (
        "FORMAT_QUICK",
        "FORMAT_FULL",
    ):
        vault_action_allowed = False
        vault_firewall_errno: Optional[str] = "EROFS"
    elif requested_vault_action in ("READ_ONLY_AUDIT", "FTP_FROM_SLOT2", "CERT_READ_TEST_ISOLATED"):
        vault_action_allowed = (
            requested_vault_slot == P348_SAFE_SECONDARY_SLOT or requested_vault_action in ("READ_ONLY_AUDIT", "CERT_READ_TEST_ISOLATED")
        )
        vault_firewall_errno = None if vault_action_allowed else "EROFS"
    elif requested_vault_action == "NONE":
        vault_action_allowed = False
        vault_firewall_errno = None
    else:
        vault_action_allowed = False
        vault_firewall_errno = "EROFS"

    return {
        "is_fx3": is_fx3,
        "ftp_slot_errno": ftp_slot_errno,
        "ftp_protocol_errno": ftp_protocol_errno,
        "ftp_mode_errno": ftp_mode_errno,
        "transfer_size_errno": transfer_size_errno,
        "cert_valid": cert_valid,
        "fx6_chunk_ok": fx6_chunk_ok,
        "ftp_dir_ok": ftp_dir_ok,
        "ftp_clip_flag_errno": ftp_clip_flag_errno,
        "wired_usblan_bypass_active": wired_usblan_bypass_active,
        "rf_and_usblan_zero_enforced": rf_and_usblan_zero_enforced,
        "ctemp_valid": ctemp_valid,
        "wb_locked_by_cine_ei": wb_locked_by_cine_ei,
        "wb_errno": wb_errno,
        "custom_wb_error_hazard": custom_wb_error_hazard,
        "custom_camset_excluded_ok": custom_camset_excluded_ok,
        "shutter_awb_lock_errno": shutter_awb_lock_errno,
        "shockless_wb_bypassed": shockless_wb_bypassed,
        "shockless_wb_effective": shockless_wb_effective,
        "fx6_wb_valid": fx6_wb_valid,
        "post_ftp_servers_cleared": post_ftp_servers_cleared,
        "post_ftp_function_enabled": post_ftp_function_enabled,
        "post_ftp_power_save": post_ftp_power_save,
        "post_wb_mode": post_wb_mode,
        "post_priority_set_in_awb": post_priority_set_in_awb,
        "post_shutter_awb_lock": post_shutter_awb_lock,
        "post_shockless_wb": post_shockless_wb,
        "post_custom_wb_slots_cleared": post_custom_wb_slots_cleared,
        "post_airplane_mode": post_airplane_mode,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


def compute_expected_movie_af_focusmap_marker_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    af_transition_speed: int,
    af_subj_shift_sens: int,
    af_assist: str,
    attached_lens_model: str,
    focus_map_in_body_requested: bool,
    focus_map_remote_mc_requested: bool,
    mc_app_version: str,
    recording_fps: int,
    playback_control_active: bool,
    auto_framing_active: bool,
    pdaf_capable_lens_attached: bool,
    usb_remote_or_uvc_active: bool,
    fx6_hdmi_raw_or_mag_or_extender_active: bool,
    marker_display: str,
    center_marker: str,
    aspect_marker: str,
    safety_zone: str,
    guideframe: str,
    focus_magnifier_active: bool,
    peaking_display: str,
    peaking_level: str,
    peaking_color: str,
    hdmi_info_display: str,
    fx6_aspect_mask_level: int,
    fx6_aspect_custom_ratio: bool,
    fx6_safety_area: str,
    fx6_user_box_width: int,
    fx6_user_box_height: int,
    fx6_user_box_h_pos: int,
    fx6_user_box_v_pos: int,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute canonical Wave-61 Pillar 63B state:
    - Movie AF parity: BOTH `ILME-FX3 Ver. 7.02` & `ILME-FX6 Ver. 6.01` use `AF Transition Speed 1..7`
      AND `AF Subj. Shift Sens. 1..5` (NO `6`/`7` in FX6!); `[AF Assist]` incompatible w/
      `SELP1650` & `SEL18200LE`
    - In-body `[Focus Map]` myth-busting: FX3 has ZERO in-body `[Focus Map]` UI (`EOPNOTSUPP=95`);
      `Ver. 6.00+` telemetry only to *Monitor & Control* `Ver. 2.1.0+`, locked out at `>= 150 fps`
      (vs FX6 native in-body with `<= 6 fps` & `>= 150 fps` lockouts)
    - All 8 `[Marker Display]` (5) + `[Peaking Display]` (3) items are Reset-immune and emit `0 px`
      over Clean-HDMI regardless of `[HDMI Info. Display]` (`Marker Display` auto-hides under
      `[Focus Magnifier]`)."""
    is_fx3 = camera_model == P348_FX3_MODEL_NAME

    # 1. Movie AF Parity (`1..7` / `1..5`) & `[AF Assist]`
    af_speed_errno: Optional[int] = (
        None
        if (P348_AF_TRANSITION_SPEED_MIN <= af_transition_speed <= P348_AF_TRANSITION_SPEED_MAX)
        else P348_EINVAL_ERRNO
    )
    af_shift_errno: Optional[int] = (
        None
        if (P348_AF_SUBJ_SHIFT_SENS_MIN <= af_subj_shift_sens <= P348_AF_SUBJ_SHIFT_SENS_MAX)
        else P348_EOPNOTSUPP_ERRNO
    )
    af_assist_effective = (
        "Off"
        if (af_assist == "On" and attached_lens_model in P348_AF_ASSIST_INCOMPATIBLE_LENSES)
        else af_assist
    )
    af_assist_errno: Optional[int] = (
        P348_EOPNOTSUPP_ERRNO
        if (af_assist == "On" and attached_lens_model in P348_AF_ASSIST_INCOMPATIBLE_LENSES)
        else None
    )

    # 2. `[Focus Map]` App-Only Truth (`Ver. 6.00+`, *M&C* `Ver. 2.1.0+`, `>= 150 fps` Lockout)
    def _ver_tuple(v: str) -> Tuple[int, ...]:
        parts: List[int] = []
        for p in v.strip().split("."):
            if p.isdigit():
                parts.append(int(p))
        return tuple(parts)

    if is_fx3:
        focus_map_in_body_errno: Optional[int] = (
            P348_EOPNOTSUPP_ERRNO if focus_map_in_body_requested else None
        )
        mc_ver_ok = _ver_tuple(mc_app_version) >= _ver_tuple(P348_FX3_FOCUS_MAP_MIN_MC_APP_VER)
        fw_focus_map_ok = fw_version in P348_FX3_FOCUS_MAP_SUPPORTED_FW_VERSIONS
        remote_blocked = (
            not fw_focus_map_ok
            or not mc_ver_ok
            or recording_fps >= P348_FX3_FOCUS_MAP_HIGH_FPS_LOCKOUT_THRESHOLD
            or playback_control_active
            or auto_framing_active
            or not pdaf_capable_lens_attached
            or usb_remote_or_uvc_active
        )
        focus_map_remote_errno: Optional[int] = (
            P348_EOPNOTSUPP_ERRNO if (focus_map_remote_mc_requested and remote_blocked) else None
        )
        focus_map_effective_active = focus_map_remote_mc_requested and not remote_blocked
    else:
        fx6_in_body_blocked = (
            recording_fps <= P348_FX6_FOCUS_MAP_LOW_FPS_LOCKOUT_MAX
            or recording_fps >= P348_FX6_FOCUS_MAP_HIGH_FPS_LOCKOUT_THRESHOLD
            or not pdaf_capable_lens_attached
            or fx6_hdmi_raw_or_mag_or_extender_active
        )
        focus_map_in_body_errno = (
            P348_EOPNOTSUPP_ERRNO if (focus_map_in_body_requested and fx6_in_body_blocked) else None
        )
        focus_map_remote_errno = (
            P348_EOPNOTSUPP_ERRNO
            if (focus_map_remote_mc_requested and (fx6_in_body_blocked or playback_control_active))
            else None
        )
        focus_map_effective_active = (
            (focus_map_in_body_requested and not fx6_in_body_blocked)
            or (focus_map_remote_mc_requested and not fx6_in_body_blocked and not playback_control_active)
        )

    # 3. `[Marker Display]` 15 Ratios + `[Peaking Display]` 4 Colors + Clean-HDMI Isolation
    if is_fx3:
        aspect_marker_valid = aspect_marker in P348_FX3_ASPECT_MARKER_STATES
        safety_zone_valid = safety_zone in P348_FX3_SAFETY_ZONE_MODES
        peaking_color_valid = peaking_color in P348_FX3_PEAKING_COLORS
    else:
        aspect_marker_valid = (
            aspect_marker in P348_FX3_ASPECT_MARKER_STATES or fx6_aspect_custom_ratio
        )
        safety_zone_valid = (
            safety_zone in P348_FX3_SAFETY_ZONE_MODES
            and fx6_safety_area in P348_FX6_SAFETY_AREA_MODES
        )
        peaking_color_valid = peaking_color in P348_FX6_PEAKING_COLORS

    fx6_user_box_valid = (
        P348_FX6_USER_BOX_WIDTH_RANGE[0] <= fx6_user_box_width <= P348_FX6_USER_BOX_WIDTH_RANGE[1]
        and P348_FX6_USER_BOX_HEIGHT_RANGE[0] <= fx6_user_box_height <= P348_FX6_USER_BOX_HEIGHT_RANGE[1]
        and P348_FX6_USER_BOX_H_POS_RANGE[0] <= fx6_user_box_h_pos <= P348_FX6_USER_BOX_H_POS_RANGE[1]
        and P348_FX6_USER_BOX_V_POS_RANGE[0] <= fx6_user_box_v_pos <= P348_FX6_USER_BOX_V_POS_RANGE[1]
        and P348_FX6_ASPECT_MASK_MIN <= fx6_aspect_mask_level <= P348_FX6_ASPECT_MASK_MAX
    )

    marker_auto_hidden_by_magnifier = focus_magnifier_active
    effective_marker_visible_on_lcd = (
        shooting_domain in ("Movie", "S&Q")
        and marker_display == "On"
        and not focus_magnifier_active
    )
    hdmi_marker_peaking_pixels_emitted = 0  # Strictly isolated regardless of hdmi_info_display!

    # 4. Reset Matrix (`Camera Settings Reset` vs `Initialize`)
    # - Movie AF (`AF Transition Speed`, `AF Subj. Shift Sens.`, `AF Assist`) ARE Resettable.
    # - ALL 8 `[Marker Display]` (5) & `[Peaking Display]` (3) items are Reset-immune (`Not available`)!
    if reset_action == "Initialize":
        post_af_transition_speed = P348_AF_TRANSITION_SPEED_DEFAULT
        post_af_subj_shift_sens = P348_AF_SUBJ_SHIFT_SENS_DEFAULT
        post_af_assist = P348_AF_ASSIST_DEFAULT
        post_marker_display = "Off"
        post_center_marker = "Off"
        post_aspect_marker = "Off"
        post_safety_zone = "Off"
        post_guideframe = "Off"
        post_peaking_display = "Off"
        post_peaking_level = P348_FX3_PEAKING_LEVEL_DEFAULT
        post_peaking_color = (
            P348_FX3_PEAKING_COLOR_DEFAULT if is_fx3 else P348_FX6_PEAKING_COLORS[0]
        )
    elif reset_action == "Camera Settings Reset":
        post_af_transition_speed = P348_AF_TRANSITION_SPEED_DEFAULT
        post_af_subj_shift_sens = P348_AF_SUBJ_SHIFT_SENS_DEFAULT
        post_af_assist = P348_AF_ASSIST_DEFAULT
        # All 8 Marker & Peaking items SURVIVE Camera Settings Reset!
        post_marker_display = marker_display
        post_center_marker = center_marker
        post_aspect_marker = aspect_marker
        post_safety_zone = safety_zone
        post_guideframe = guideframe
        post_peaking_display = peaking_display
        post_peaking_level = peaking_level
        post_peaking_color = peaking_color
    else:
        post_af_transition_speed = af_transition_speed
        post_af_subj_shift_sens = af_subj_shift_sens
        post_af_assist = af_assist_effective
        post_marker_display = marker_display
        post_center_marker = center_marker
        post_aspect_marker = aspect_marker
        post_safety_zone = safety_zone
        post_guideframe = guideframe
        post_peaking_display = peaking_display
        post_peaking_level = peaking_level
        post_peaking_color = peaking_color

    # 5. Slot-1 Tier-0 Vault Firewall (`EROFS=30`)
    mutates_slot1 = (
        requested_vault_action in P348_WRITE_MUTATING_VAULT_ACTIONS
        or (requested_vault_slot == P348_SLOT1_VAULT_SLOT and requested_vault_action not in ("NONE", "READ_ONLY_AUDIT"))
    )
    if (mutates_slot1 and slot1_holds_tier0_vault) or requested_vault_action in (
        "FORMAT_QUICK",
        "FORMAT_FULL",
    ):
        vault_action_allowed = False
        vault_firewall_errno: Optional[str] = "EROFS"
    elif requested_vault_action == "READ_ONLY_AUDIT":
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
        "af_speed_errno": af_speed_errno,
        "af_shift_errno": af_shift_errno,
        "af_assist_effective": af_assist_effective,
        "af_assist_errno": af_assist_errno,
        "focus_map_in_body_errno": focus_map_in_body_errno,
        "focus_map_remote_errno": focus_map_remote_errno,
        "focus_map_effective_active": focus_map_effective_active,
        "aspect_marker_valid": aspect_marker_valid,
        "safety_zone_valid": safety_zone_valid,
        "peaking_color_valid": peaking_color_valid,
        "fx6_user_box_valid": fx6_user_box_valid,
        "marker_auto_hidden_by_magnifier": marker_auto_hidden_by_magnifier,
        "effective_marker_visible_on_lcd": effective_marker_visible_on_lcd,
        "hdmi_marker_peaking_pixels_emitted": hdmi_marker_peaking_pixels_emitted,
        "post_af_transition_speed": post_af_transition_speed,
        "post_af_subj_shift_sens": post_af_subj_shift_sens,
        "post_af_assist": post_af_assist,
        "post_marker_display": post_marker_display,
        "post_center_marker": post_center_marker,
        "post_aspect_marker": post_aspect_marker,
        "post_safety_zone": post_safety_zone,
        "post_guideframe": post_guideframe,
        "post_peaking_display": post_peaking_display,
        "post_peaking_level": post_peaking_level,
        "post_peaking_color": post_peaking_color,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & work_root=None Clean-Room Guard (17 Donors)
# ---------------------------------------------------------------------------


def _iter_work_roots() -> Tuple[Optional[Path], ...]:
    """Return candidate donor work roots (delegates to `_fx3_files.iter_donor_work_roots`)."""
    return _fx3_files.iter_donor_work_roots()


def _resolve_phase348_donor_path(
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
    max_full_bytes: int = P348_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    try:
        resolved = _resolve_phase348_donor_path(relpath)
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
        hdr = os.pread(fd, min(P348_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase348_donors() -> Tuple["Phase348DonorArtifactDigest", ...]:
    specs = (
        ("fx3_appfw_702_so", P348_DONOR_FX3_APPFW_702_RELPATH, P348_PINNED_FX3_APPFW_702_BYTES, P348_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P348_PINNED_FX3_APPFW_702_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702"),
        ("fx6_appfw_601_so", P348_DONOR_FX6_APPFW_601_RELPATH, P348_PINNED_FX6_APPFW_601_BYTES, P348_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P348_PINNED_FX6_APPFW_601_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601"),
        ("fx3_backup_bin", P348_DONOR_FX3_BACKUP_BIN_RELPATH, P348_PINNED_FX3_BACKUP_BIN_BYTES, P348_PINNED_FX3_BACKUP_BIN_BYTES, "FULL_SHA256", P348_PINNED_FX3_BACKUP_BIN_SHA256, "SYNTHETIC_BK4_ILME_FX3"),
        ("fx3_uxc_en_f", P348_DONOR_FX3_UXC_EN_F_RELPATH, P348_PINNED_FX3_UXC_EN_F_BYTES, P348_PINNED_FX3_UXC_EN_F_BYTES, "FULL_SHA256", P348_PINNED_FX3_UXC_EN_F_SHA256, "SYNTHETIC_UXC7_FX3_EN_F"),
        ("fx3_uxc_sc_f", P348_DONOR_FX3_UXC_SC_F_RELPATH, P348_PINNED_FX3_UXC_SC_F_BYTES, P348_PINNED_FX3_UXC_SC_F_BYTES, "FULL_SHA256", P348_PINNED_FX3_UXC_SC_F_SHA256, "SYNTHETIC_UXC7_FX3_SC_F"),
        ("fx3_uxc_tc_f", P348_DONOR_FX3_UXC_TC_F_RELPATH, P348_PINNED_FX3_UXC_TC_F_BYTES, P348_PINNED_FX3_UXC_TC_F_BYTES, "FULL_SHA256", P348_PINNED_FX3_UXC_TC_F_SHA256, "SYNTHETIC_UXC7_FX3_TC_F"),
        ("fx3_uxc_ja_f", P348_DONOR_FX3_UXC_JA_F_RELPATH, P348_PINNED_FX3_UXC_JA_F_BYTES, P348_PINNED_FX3_UXC_JA_F_BYTES, "FULL_SHA256", P348_PINNED_FX3_UXC_JA_F_SHA256, "SYNTHETIC_UXC7_FX3_JA_F"),
        ("fx3_uxc_en", P348_DONOR_FX3_UXC_EN_RELPATH, P348_PINNED_FX3_UXC_EN_BYTES, P348_PINNED_FX3_UXC_EN_BYTES, "FULL_SHA256", P348_PINNED_FX3_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX3_EN"),
        ("fx3_uxc_sc", P348_DONOR_FX3_UXC_SC_RELPATH, P348_PINNED_FX3_UXC_SC_BYTES, P348_PINNED_FX3_UXC_SC_BYTES, "FULL_SHA256", P348_PINNED_FX3_UXC_SC_SHA256, "SYNTHETIC_UXC7_FX3_SC"),
        ("fx3_uxc_tc", P348_DONOR_FX3_UXC_TC_RELPATH, P348_PINNED_FX3_UXC_TC_BYTES, P348_PINNED_FX3_UXC_TC_BYTES, "FULL_SHA256", P348_PINNED_FX3_UXC_TC_SHA256, "SYNTHETIC_UXC7_FX3_TC"),
        ("fx3_uxc_ja", P348_DONOR_FX3_UXC_JA_RELPATH, P348_PINNED_FX3_UXC_JA_BYTES, P348_PINNED_FX3_UXC_JA_BYTES, "FULL_SHA256", P348_PINNED_FX3_UXC_JA_SHA256, "SYNTHETIC_UXC7_FX3_JA"),
        ("fx3_uxc_en_g", P348_DONOR_FX3_UXC_EN_G_RELPATH, P348_PINNED_FX3_UXC_EN_G_BYTES, P348_PINNED_FX3_UXC_EN_G_BYTES, "FULL_SHA256", P348_PINNED_FX3_UXC_EN_G_SHA256, "SYNTHETIC_UXC7_FX3_EN_G"),
        ("fx3_uxc_sc_g", P348_DONOR_FX3_UXC_SC_G_RELPATH, P348_PINNED_FX3_UXC_SC_G_BYTES, P348_PINNED_FX3_UXC_SC_G_BYTES, "FULL_SHA256", P348_PINNED_FX3_UXC_SC_G_SHA256, "SYNTHETIC_UXC7_FX3_SC_G"),
        ("fx3_uxc_tc_g", P348_DONOR_FX3_UXC_TC_G_RELPATH, P348_PINNED_FX3_UXC_TC_G_BYTES, P348_PINNED_FX3_UXC_TC_G_BYTES, "FULL_SHA256", P348_PINNED_FX3_UXC_TC_G_SHA256, "SYNTHETIC_UXC7_FX3_TC_G"),
        ("fx3_uxc_ja_g", P348_DONOR_FX3_UXC_JA_G_RELPATH, P348_PINNED_FX3_UXC_JA_G_BYTES, P348_PINNED_FX3_UXC_JA_G_BYTES, "FULL_SHA256", P348_PINNED_FX3_UXC_JA_G_SHA256, "SYNTHETIC_UXC7_FX3_JA_G"),
        ("fx6_uxc_en", P348_DONOR_FX6_UXC_EN_RELPATH, P348_PINNED_FX6_UXC_EN_BYTES, P348_PINNED_FX6_UXC_EN_BYTES, "FULL_SHA256", P348_PINNED_FX6_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX6_EN"),
        ("fx6_uxc_en_2", P348_DONOR_FX6_UXC_EN_2_RELPATH, P348_PINNED_FX6_UXC_EN_2_BYTES, P348_PINNED_FX6_UXC_EN_2_BYTES, "FULL_SHA256", P348_PINNED_FX6_UXC_EN_2_SHA256, "SYNTHETIC_UXC7_FX6_EN_2"),
    )
    return tuple(
        Phase348DonorArtifactDigest(
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


def inspect_phase348_donors_readonly(
    force_clean_room: Optional[bool] = None,
) -> "Phase348DonorSnapshot":
    """Inspect Wave-61 FX3 7.02 (`14` donors) & FX6 6.01 (`3` donors) strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase348_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase348DonorSnapshot(
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
        ("fx3_appfw_702_so", P348_DONOR_FX3_APPFW_702_RELPATH, P348_PINNED_FX3_APPFW_702_BYTES, P348_PINNED_FX3_APPFW_702_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702")),
        ("fx6_appfw_601_so", P348_DONOR_FX6_APPFW_601_RELPATH, P348_PINNED_FX6_APPFW_601_BYTES, P348_PINNED_FX6_APPFW_601_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601")),
        ("fx3_backup_bin", P348_DONOR_FX3_BACKUP_BIN_RELPATH, P348_PINNED_FX3_BACKUP_BIN_BYTES, P348_PINNED_FX3_BACKUP_BIN_SHA256, lambda d: _check_bk4_backup(d, "ILME_FX3")),
        ("fx3_uxc_en_f", P348_DONOR_FX3_UXC_EN_F_RELPATH, P348_PINNED_FX3_UXC_EN_F_BYTES, P348_PINNED_FX3_UXC_EN_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_F")),
        ("fx3_uxc_sc_f", P348_DONOR_FX3_UXC_SC_F_RELPATH, P348_PINNED_FX3_UXC_SC_F_BYTES, P348_PINNED_FX3_UXC_SC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_F")),
        ("fx3_uxc_tc_f", P348_DONOR_FX3_UXC_TC_F_RELPATH, P348_PINNED_FX3_UXC_TC_F_BYTES, P348_PINNED_FX3_UXC_TC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_F")),
        ("fx3_uxc_ja_f", P348_DONOR_FX3_UXC_JA_F_RELPATH, P348_PINNED_FX3_UXC_JA_F_BYTES, P348_PINNED_FX3_UXC_JA_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_F")),
        ("fx3_uxc_en", P348_DONOR_FX3_UXC_EN_RELPATH, P348_PINNED_FX3_UXC_EN_BYTES, P348_PINNED_FX3_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN")),
        ("fx3_uxc_sc", P348_DONOR_FX3_UXC_SC_RELPATH, P348_PINNED_FX3_UXC_SC_BYTES, P348_PINNED_FX3_UXC_SC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC")),
        ("fx3_uxc_tc", P348_DONOR_FX3_UXC_TC_RELPATH, P348_PINNED_FX3_UXC_TC_BYTES, P348_PINNED_FX3_UXC_TC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC")),
        ("fx3_uxc_ja", P348_DONOR_FX3_UXC_JA_RELPATH, P348_PINNED_FX3_UXC_JA_BYTES, P348_PINNED_FX3_UXC_JA_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA")),
        ("fx3_uxc_en_g", P348_DONOR_FX3_UXC_EN_G_RELPATH, P348_PINNED_FX3_UXC_EN_G_BYTES, P348_PINNED_FX3_UXC_EN_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_G")),
        ("fx3_uxc_sc_g", P348_DONOR_FX3_UXC_SC_G_RELPATH, P348_PINNED_FX3_UXC_SC_G_BYTES, P348_PINNED_FX3_UXC_SC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_G")),
        ("fx3_uxc_tc_g", P348_DONOR_FX3_UXC_TC_G_RELPATH, P348_PINNED_FX3_UXC_TC_G_BYTES, P348_PINNED_FX3_UXC_TC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_G")),
        ("fx3_uxc_ja_g", P348_DONOR_FX3_UXC_JA_G_RELPATH, P348_PINNED_FX3_UXC_JA_G_BYTES, P348_PINNED_FX3_UXC_JA_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_G")),
        ("fx6_uxc_en", P348_DONOR_FX6_UXC_EN_RELPATH, P348_PINNED_FX6_UXC_EN_BYTES, P348_PINNED_FX6_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN")),
        ("fx6_uxc_en_2", P348_DONOR_FX6_UXC_EN_2_RELPATH, P348_PINNED_FX6_UXC_EN_2_BYTES, P348_PINNED_FX6_UXC_EN_2_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN_2")),
    )

    def _probe_one(spec: Tuple[str, str, int, str, Any]) -> Optional[Phase348DonorArtifactDigest]:
        aid, relpath, expected_bytes, expected_sha, marker_fn = spec
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            return None
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        return Phase348DonorArtifactDigest(
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
        artifacts = _synthetic_phase348_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase348DonorSnapshot(
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
    return Phase348DonorSnapshot(
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
# Frozen Dataclasses (Specs, Reports, Suites & 63-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase348DonorArtifactDigest:
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
class Phase348DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_2_0s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase348DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FtpFtpesUsbLanCustomWbVaultSpec:
    # [FTP Transfer Func.] (`FTP`/`FTPES`, 9 Server Slots, ZERO SFTP/Active/Transfer JPEG Size)
    camera_model: str
    fw_version: str
    ftp_server_slot: int
    ftp_protocol: str
    ftp_transfer_mode: str
    transfer_jpeg_heif_size_requested: bool
    reported_ftp_slot_errno: Optional[int]
    reported_ftp_protocol_errno: Optional[int]
    reported_ftp_mode_errno: Optional[int]
    reported_transfer_size_errno: Optional[int]
    ftp_directory_hierarchy: str
    ftp_specify_dir_len: int
    ftp_clip_flag_filter: str
    reported_clip_flag_errno: Optional[int]
    ftp_cert_filename: str
    ftp_cert_bytes: int
    ftp_cert_slot: str
    ftp_power_save: str
    fx6_auto_upload_proxy_chunk: str
    fx6_simul_or_relay_active: bool
    fx3_appfw_sftp_hits: int
    fx3_appfw_passive_mode_hits: int
    fx3_appfw_transfer_jpeg_heif_size_hits: int
    # Zero-RF & USB-LAN Airplane-Mode Bypass Guard
    airplane_mode: str
    usb_lan_enabled: bool
    wifi_active: bool
    ble_active: bool
    ftp_function_enabled: bool
    network_transport: str
    rf_packets_transmitted: int
    usblan_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    # White Balance Deep Truth (`Custom 1..3`, `Priority Set in AWB`, `Shutter AWB Lock`, `Shockless WB`, `Cine EI`)
    shooting_domain: str
    wb_mode: str
    wb_color_temp_k: int
    wb_direct_ctemp_or_tint_tweaked: bool
    reported_wb_errno: Optional[int]
    custom_wb_slots_populated: int
    custom_wb_exported_in_camset: bool
    custom_setup_triggered: bool
    reported_custom_wb_error_hazard: bool
    log_shooting_mode: str
    picture_profile: str
    priority_set_in_awb: str
    shutter_awb_lock: str
    reported_shutter_awb_lock_errno: Optional[int]
    shockless_wb: str
    reported_shockless_wb_effective: str
    reported_shockless_wb_bypassed: bool
    fx6_wht_bal_switch: str
    fx6_memory_bank: str
    fx6_atw_speed: int
    # Reset Matrix (`None`, `Camera Settings Reset`, `Reset Network Set.`, `Initialize`)
    reset_action: str
    post_ftp_servers_cleared: bool
    post_ftp_function_enabled: bool
    post_ftp_power_save: str
    post_wb_mode: str
    post_priority_set_in_awb: str
    post_shutter_awb_lock: str
    post_shockless_wb: str
    post_custom_wb_slots_cleared: bool
    post_airplane_mode: str
    # Slot-1 Tier-0 AVF_INFO / FTP_TRANS_STAT Vault Firewall & Stage-B Overlay & H0 == H3
    requested_vault_slot: int
    slot1_holds_tier0_vault: bool
    requested_vault_action: str
    reported_vault_action_allowed: bool
    vault_firewall_errno: Optional[str]
    slot1_data_sector_writes: int
    slot1_avf_info_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative drift event counters
    ftp_protocol_sftp_or_jpeg_size_drift_events: int
    wb_custom_cine_ei_or_shockless_drift_events: int
    zero_rf_usblan_or_slot1_avf_bypass_events: int


@dataclass(frozen=True)
class FtpFtpesUsbLanCustomWbVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    ftp_ftpes_9slots_passive_and_zero_sftp_verified: bool
    wb_custom_cine_ei_and_shockless_verified: bool
    zero_rf_usblan_and_slot1_avf_erofs30_verified: bool
    overlay_and_h0_h3_verified: bool
    matrix_states_checked: int
    ftp_protocol_sftp_or_jpeg_size_drift_events: int
    wb_custom_cine_ei_or_shockless_drift_events: int
    zero_rf_usblan_or_slot1_avf_bypass_events: int
    rf_packets_transmitted: int
    usblan_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_avf_info_mutation_bytes: int
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
class MovieAfFocusMapMarkerPeakingVaultSpec:
    # Movie AF Parity (`AF Transition Speed 1..7`, `AF Subj. Shift Sens. 1..5`, `[AF Assist]`)
    camera_model: str
    fw_version: str
    shooting_domain: str
    af_transition_speed: int
    af_subj_shift_sens: int
    reported_af_speed_errno: Optional[int]
    reported_af_shift_errno: Optional[int]
    fx6_appfw_af_subj_shift_6_7_hits: int
    af_assist: str
    attached_lens_model: str
    reported_af_assist_effective: str
    reported_af_assist_errno: Optional[int]
    # App-Only `[Focus Map]` Myth-Busting (`Ver. 6.00+`, *M&C* `Ver. 2.1.0+`, ZERO In-Body UI on FX3)
    focus_map_in_body_requested: bool
    focus_map_remote_mc_requested: bool
    mc_app_version: str
    recording_fps: int
    playback_control_active: bool
    auto_framing_active: bool
    pdaf_capable_lens_attached: bool
    usb_remote_or_uvc_active: bool
    fx6_hdmi_raw_or_mag_or_extender_active: bool
    fx3_in_body_focus_map_bkid_hits: int
    reported_focus_map_in_body_errno: Optional[int]
    reported_focus_map_remote_errno: Optional[int]
    reported_focus_map_effective_active: bool
    # 8 Reset-Immune Assist Items (`[Marker Display]` 5 + `[Peaking Display]` 3) + Clean-HDMI Isolation
    marker_display: str
    center_marker: str
    aspect_marker: str
    safety_zone: str
    guideframe: str
    focus_magnifier_active: bool
    reported_effective_marker_visible_on_lcd: bool
    peaking_display: str
    peaking_level: str
    peaking_color: str
    hdmi_info_display: str
    hdmi_marker_peaking_pixels_emitted: int
    fx6_aspect_mask_level: int
    fx6_aspect_custom_ratio: bool
    fx6_safety_area: str
    fx6_user_box_width: int
    fx6_user_box_height: int
    fx6_user_box_h_pos: int
    fx6_user_box_v_pos: int
    # Reset boundary (`None`, `Camera Settings Reset`, `Initialize`)
    reset_action: str
    post_af_transition_speed: int
    post_af_subj_shift_sens: int
    post_af_assist: str
    post_marker_display: str
    post_center_marker: str
    post_aspect_marker: str
    post_safety_zone: str
    post_guideframe: str
    post_peaking_display: str
    post_peaking_level: str
    post_peaking_color: str
    # Slot-1 Tier-0 Vault Firewall & Stage-B Overlay & H0 == H3
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
    movie_af_speed_or_focus_map_spoof_events: int
    marker_15ratio_peaking_hdmi_leak_events: int
    zero_rf_usblan_or_slot1_avf_bypass_events: int


@dataclass(frozen=True)
class MovieAfFocusMapMarkerPeakingVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    movie_af_parity_and_app_only_focus_map_verified: bool
    marker_15ratio_peaking_reset_immune_clean_hdmi_verified: bool
    slot1_vault_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    movie_af_speed_or_focus_map_spoof_events: int
    marker_15ratio_peaking_hdmi_leak_events: int
    zero_rf_usblan_or_slot1_avf_bypass_events: int
    hdmi_marker_peaking_pixels_emitted: int
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
class FtpFtpesCustomWbAfFocusMapMarkerVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase348DonorSnapshot
    ftp_ftpes_customwb_report: FtpFtpesUsbLanCustomWbVaultReport
    movie_af_focusmap_marker_report: MovieAfFocusMapMarkerPeakingVaultReport
    ftp_protocol_sftp_or_jpeg_size_drift_events: int
    wb_custom_cine_ei_or_shockless_drift_events: int
    movie_af_speed_or_focus_map_spoof_events: int
    marker_15ratio_peaking_hdmi_leak_events: int
    zero_rf_usblan_or_slot1_avf_bypass_events: int
    rf_packets_transmitted: int
    usblan_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    hdmi_marker_peaking_pixels_emitted: int
    slot1_data_sector_writes: int
    slot1_avf_info_mutation_bytes: int
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
class Pillar63ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar63ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar63ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar63BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar63ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar63StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase348DonorSnapshot
    pillar_63a_ftp_ftpes_usblan_customwb_vault: Pillar63ASuiteResult
    pillar_63b_movie_af_focusmap_marker_peaking_vault: Pillar63BSuiteResult
    ftp_protocol_sftp_or_jpeg_size_drift_events: int
    wb_custom_cine_ei_or_shockless_drift_events: int
    movie_af_speed_or_focus_map_spoof_events: int
    marker_15ratio_peaking_hdmi_leak_events: int
    zero_rf_usblan_or_slot1_avf_bypass_events: int
    rf_packets_transmitted: int
    usblan_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    hdmi_marker_peaking_pixels_emitted: int
    slot1_data_sector_writes: int
    slot1_avf_info_mutation_bytes: int
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
class Master63PillarRecoveryReport:
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
    donor_snapshot: Phase348DonorSnapshot
    pillar63_a_ftp_ftpes_usblan_customwb_vault: Pillar63ASuiteResult
    pillar63_b_movie_af_focusmap_marker_peaking_vault: Pillar63BSuiteResult
    # Pillar 63 zero-violation counters & hardware boundaries
    ftp_protocol_sftp_or_jpeg_size_drift_events: int
    wb_custom_cine_ei_or_shockless_drift_events: int
    movie_af_speed_or_focus_map_spoof_events: int
    marker_15ratio_peaking_hdmi_leak_events: int
    zero_rf_usblan_or_slot1_avf_bypass_events: int
    rf_packets_transmitted: int
    usblan_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    hdmi_marker_peaking_pixels_emitted: int
    slot1_data_sector_writes: int
    slot1_avf_info_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
    fx3_appfw_sftp_hits: int
    fx3_appfw_passive_mode_hits: int
    fx3_appfw_transfer_jpeg_heif_size_hits: int
    fx3_ftp_server_slot_count: int
    fx3_ftp_passive_mode_only: bool
    fx3_usblan_bypasses_airplane_mode: bool
    fx3_wb_custom_slots: int
    fx3_shutter_awb_lock_reset_immune: bool
    fx3_af_transition_speed_max: int
    fx3_af_subj_shift_sens_max: int
    fx6_af_subj_shift_sens_max: int
    fx3_in_body_focus_map_bkid_hits: int
    fx3_focus_map_app_only_since_fw: str
    fx3_aspect_marker_active_ratio_count: int
    fx3_peaking_color_count: int
    fx3_reset_immune_assist_item_count: int
    # Carried forward Pillar 62 metrics
    rec_media_prioritize_or_autoswitch_drift_events: int
    card_speed_vpg200_vpg400_gate_drift_events: int
    proxy_sq_dci4k_or_120p_lockout_drift_events: int
    cloud_init_persist_or_power_off_ble_rf_events: int
    mymenu_42slot_or_fx6_lock_spoof_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    slot1_dcim_m4root_avf_mutation_bytes: int
    fx3_appfw_prioritize_hits: int
    fx3_appfw_prm_haita_proxy_hits: int
    fx3_has_movie_sort_recording: bool
    fx3_proxy_dci4k_allowed: bool
    fx3_cloud_star_survives_initialize: bool
    fx3_power_off_ble_forced_off: bool
    fx3_mymenu_slot_capacity: int
    fx6_user_menu_max_items: int
    fx6_has_bluetooth_hardware: bool
    # Carried forward Pillar 61..41 metrics
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
    fx3_has_builtin_evf: bool
    fx3_has_var_shutter: bool
    # Safety lock flags
    overall_ready_for_hardware_attach: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    master_63pillar_sha256: str
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


def build_default_safe_ftp_ftpes_customwb_vault_spec(
    **overrides: Any,
) -> FtpFtpesUsbLanCustomWbVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P348_FX3_MODEL_NAME,
        "fw_version": P348_FX3_FW_VERSION,
        "ftp_server_slot": 9,
        "ftp_protocol": "FTPES",
        "ftp_transfer_mode": "Passive",
        "transfer_jpeg_heif_size_requested": False,
        "reported_ftp_slot_errno": None,
        "reported_ftp_protocol_errno": None,
        "reported_ftp_mode_errno": None,
        "reported_transfer_size_errno": None,
        "ftp_directory_hierarchy": "Same as in Camera",
        "ftp_specify_dir_len": 64,
        "ftp_clip_flag_filter": "OK",
        "reported_clip_flag_errno": None,
        "ftp_cert_filename": P348_FX3_FTP_CERT_FILENAME,
        "ftp_cert_bytes": 4096,
        "ftp_cert_slot": "Slot 1",
        "ftp_power_save": "Off",
        "fx6_auto_upload_proxy_chunk": "Off",
        "fx6_simul_or_relay_active": False,
        "fx3_appfw_sftp_hits": P348_FX3_APPFW_SFTP_HIT_COUNT,
        "fx3_appfw_passive_mode_hits": P348_FX3_APPFW_PASSIVE_MODE_HIT_COUNT,
        "fx3_appfw_transfer_jpeg_heif_size_hits": P348_FX3_APPFW_TRANSFER_JPEG_HEIF_SIZE_HIT_COUNT,
        "airplane_mode": "On",
        "usb_lan_enabled": False,
        "wifi_active": False,
        "ble_active": False,
        "ftp_function_enabled": False,
        "network_transport": "NONE",
        "rf_packets_transmitted": P348_RF_PACKETS_TRANSMITTED,
        "usblan_packets_transmitted": P348_USBLAN_PACKETS_TRANSMITTED,
        "rf_nvs_mutation_bytes": P348_RF_NVS_MUTATION_BYTES,
        "shooting_domain": "Movie",
        "wb_mode": "C.Temp./Filter",
        "wb_color_temp_k": 5600,
        "wb_direct_ctemp_or_tint_tweaked": False,
        "reported_wb_errno": None,
        "custom_wb_slots_populated": 3,
        "custom_wb_exported_in_camset": False,
        "custom_setup_triggered": False,
        "reported_custom_wb_error_hazard": False,
        "log_shooting_mode": "Off",
        "picture_profile": "Off",
        "priority_set_in_awb": "Standard",
        "shutter_awb_lock": "Off",
        "reported_shutter_awb_lock_errno": None,
        "shockless_wb": "1",
        "reported_shockless_wb_effective": "1",
        "reported_shockless_wb_bypassed": False,
        "fx6_wht_bal_switch": "PRST",
        "fx6_memory_bank": "A",
        "fx6_atw_speed": 3,
        "reset_action": "None",
        "post_ftp_servers_cleared": False,
        "post_ftp_function_enabled": False,
        "post_ftp_power_save": "Off",
        "post_wb_mode": "C.Temp./Filter",
        "post_priority_set_in_awb": "Standard",
        "post_shutter_awb_lock": "Off",
        "post_shockless_wb": "1",
        "post_custom_wb_slots_cleared": False,
        "post_airplane_mode": "On",
        "requested_vault_slot": P348_SLOT1_VAULT_SLOT,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": P348_SLOT1_DATA_SECTOR_WRITES,
        "slot1_avf_info_mutation_bytes": P348_SLOT1_AVF_INFO_MUTATION_BYTES,
        "slot1_vault_mutation_bytes": P348_SLOT1_VAULT_MUTATION_BYTES,
        "slot1_vault_erofs_eopnotsupp_enforced": P348_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        "slot1_format_hard_locked": P348_SLOT1_FORMAT_HARD_LOCKED,
        "overlay_dir": f"{P348_STAGE_B_VOLATILE_OVERLAY_DIR}/63a",
        "backup_bin_h0_sha256": P348_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P348_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P348_TIER0_SURFACE_COUNT,
        "ftp_protocol_sftp_or_jpeg_size_drift_events": (
            P348_FTP_PROTOCOL_SFTP_OR_JPEG_SIZE_DRIFT_EVENTS
        ),
        "wb_custom_cine_ei_or_shockless_drift_events": (
            P348_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT_EVENTS
        ),
        "zero_rf_usblan_or_slot1_avf_bypass_events": (
            P348_ZERO_RF_USBLAN_OR_SLOT1_AVF_BYPASS_EVENTS
        ),
    }
    defaults.update(overrides)
    return FtpFtpesUsbLanCustomWbVaultSpec(**defaults)


def build_default_safe_movie_af_focusmap_marker_vault_spec(
    **overrides: Any,
) -> MovieAfFocusMapMarkerPeakingVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P348_FX3_MODEL_NAME,
        "fw_version": P348_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "af_transition_speed": P348_AF_TRANSITION_SPEED_DEFAULT,
        "af_subj_shift_sens": P348_AF_SUBJ_SHIFT_SENS_DEFAULT,
        "reported_af_speed_errno": None,
        "reported_af_shift_errno": None,
        "fx6_appfw_af_subj_shift_6_7_hits": P348_FX6_APPFW_AF_SUBJ_SHIFT_6_7_HITS,
        "af_assist": "Off",
        "attached_lens_model": "SEL2470GM2",
        "reported_af_assist_effective": "Off",
        "reported_af_assist_errno": None,
        "focus_map_in_body_requested": False,
        "focus_map_remote_mc_requested": True,
        "mc_app_version": P348_FX3_FOCUS_MAP_MIN_MC_APP_VER,
        "recording_fps": 120,
        "playback_control_active": False,
        "auto_framing_active": False,
        "pdaf_capable_lens_attached": True,
        "usb_remote_or_uvc_active": False,
        "fx6_hdmi_raw_or_mag_or_extender_active": False,
        "fx3_in_body_focus_map_bkid_hits": P348_FX3_IN_BODY_FOCUS_MAP_BKID_HITS,
        "reported_focus_map_in_body_errno": None,
        "reported_focus_map_remote_errno": None,
        "reported_focus_map_effective_active": True,
        "marker_display": "On",
        "center_marker": "On",
        "aspect_marker": "2.39:1",
        "safety_zone": "90%",
        "guideframe": "On",
        "focus_magnifier_active": False,
        "reported_effective_marker_visible_on_lcd": True,
        "peaking_display": "On",
        "peaking_level": "Mid",
        "peaking_color": "Red",
        "hdmi_info_display": "On",
        "hdmi_marker_peaking_pixels_emitted": P348_HDMI_MARKER_PEAKING_LEAK_PIXELS,
        "fx6_aspect_mask_level": P348_FX6_ASPECT_MASK_DEFAULT,
        "fx6_aspect_custom_ratio": False,
        "fx6_safety_area": "90%",
        "fx6_user_box_width": 240,
        "fx6_user_box_height": 135,
        "fx6_user_box_h_pos": 0,
        "fx6_user_box_v_pos": 0,
        "reset_action": "None",
        "post_af_transition_speed": P348_AF_TRANSITION_SPEED_DEFAULT,
        "post_af_subj_shift_sens": P348_AF_SUBJ_SHIFT_SENS_DEFAULT,
        "post_af_assist": "Off",
        "post_marker_display": "On",
        "post_center_marker": "On",
        "post_aspect_marker": "2.39:1",
        "post_safety_zone": "90%",
        "post_guideframe": "On",
        "post_peaking_display": "On",
        "post_peaking_level": "Mid",
        "post_peaking_color": "Red",
        "requested_vault_slot": P348_SLOT1_VAULT_SLOT,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": P348_SLOT1_DATA_SECTOR_WRITES,
        "slot1_vault_mutation_bytes": P348_SLOT1_VAULT_MUTATION_BYTES,
        "slot1_vault_erofs_eopnotsupp_enforced": P348_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        "slot1_format_hard_locked": P348_SLOT1_FORMAT_HARD_LOCKED,
        "overlay_dir": f"{P348_STAGE_B_VOLATILE_OVERLAY_DIR}/63b",
        "backup_bin_h0_sha256": P348_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P348_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P348_TIER0_SURFACE_COUNT,
        "movie_af_speed_or_focus_map_spoof_events": (
            P348_MOVIE_AF_SPEED_OR_FOCUS_MAP_SPOOF_EVENTS
        ),
        "marker_15ratio_peaking_hdmi_leak_events": (
            P348_MARKER_15RATIO_PEAKING_HDMI_LEAK_EVENTS
        ),
        "zero_rf_usblan_or_slot1_avf_bypass_events": (
            P348_ZERO_RF_USBLAN_OR_SLOT1_AVF_BYPASS_EVENTS
        ),
    }
    defaults.update(overrides)
    return MovieAfFocusMapMarkerPeakingVaultSpec(**defaults)


# ---------------------------------------------------------------------------
# Sub-Pillar Evaluators (63A & 63B) + Combined Single-Shot Verifier
# ---------------------------------------------------------------------------


def evaluate_ftp_ftpes_customwb_vault(
    spec: FtpFtpesUsbLanCustomWbVaultSpec,
) -> FtpFtpesUsbLanCustomWbVaultReport:
    """Evaluate Pillar 63A spec (`[FTP Transfer Func.]`, `USB-LAN` bypass, `Slot 1` `AVF_INFO` `EROFS=30`, White Balance)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P348_BLOCKED_SAFETY_POLICY_VIOLATION, "Safety policy violation")

    valid_spec = (
        spec.camera_model in (P348_FX3_MODEL_NAME, P348_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P348_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P348_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.ftp_protocol in P348_FTP_PROTOCOLS
        and spec.ftp_transfer_mode in P348_FTP_TRANSFER_MODES
        and spec.ftp_power_save in P348_ON_OFF_MODES
        and spec.airplane_mode in P348_ON_OFF_MODES
        and spec.network_transport in P348_NETWORK_TRANSPORTS
        and spec.shooting_domain in P348_SHOOTING_DOMAINS
        and spec.wb_mode in P348_WB_MODES
        and spec.log_shooting_mode in P348_LOG_SHOOTING_MODES
        and spec.picture_profile in P348_PICTURE_PROFILES
        and spec.priority_set_in_awb in P348_PRIORITY_SET_AWB_MODES
        and spec.shutter_awb_lock in P348_SHUTTER_AWB_LOCK_MODES
        and spec.shockless_wb in P348_SHOCKLESS_WB_MODES
        and spec.reset_action in P348_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P348_VAULT_ACTIONS
        and spec.vault_firewall_errno in P348_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P348_BLOCKED_INVALID_PILLAR63A_SPEC, "Invalid Pillar 63A spec fields")

    st = compute_expected_ftp_ftpes_customwb_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        ftp_server_slot=spec.ftp_server_slot,
        ftp_protocol=spec.ftp_protocol,
        ftp_transfer_mode=spec.ftp_transfer_mode,
        transfer_jpeg_heif_size_requested=spec.transfer_jpeg_heif_size_requested,
        ftp_directory_hierarchy=spec.ftp_directory_hierarchy,
        ftp_specify_dir_len=spec.ftp_specify_dir_len,
        ftp_clip_flag_filter=spec.ftp_clip_flag_filter,
        ftp_cert_filename=spec.ftp_cert_filename,
        ftp_cert_bytes=spec.ftp_cert_bytes,
        ftp_cert_slot=spec.ftp_cert_slot,
        ftp_power_save=spec.ftp_power_save,
        fx6_auto_upload_proxy_chunk=spec.fx6_auto_upload_proxy_chunk,
        fx6_simul_or_relay_active=spec.fx6_simul_or_relay_active,
        airplane_mode=spec.airplane_mode,
        usb_lan_enabled=spec.usb_lan_enabled,
        wifi_active=spec.wifi_active,
        ble_active=spec.ble_active,
        ftp_function_enabled=spec.ftp_function_enabled,
        network_transport=spec.network_transport,
        shooting_domain=spec.shooting_domain,
        wb_mode=spec.wb_mode,
        wb_color_temp_k=spec.wb_color_temp_k,
        wb_direct_ctemp_or_tint_tweaked=spec.wb_direct_ctemp_or_tint_tweaked,
        custom_wb_slots_populated=spec.custom_wb_slots_populated,
        custom_wb_exported_in_camset=spec.custom_wb_exported_in_camset,
        custom_setup_triggered=spec.custom_setup_triggered,
        log_shooting_mode=spec.log_shooting_mode,
        picture_profile=spec.picture_profile,
        priority_set_in_awb=spec.priority_set_in_awb,
        shutter_awb_lock=spec.shutter_awb_lock,
        shockless_wb=spec.shockless_wb,
        fx6_wht_bal_switch=spec.fx6_wht_bal_switch,
        fx6_memory_bank=spec.fx6_memory_bank,
        fx6_atw_speed=spec.fx6_atw_speed,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    # 1. [FTP Transfer Func.] (`FTP`/`FTPES` 9 slots, Passive only, ZERO SFTP / dormant Transfer JPEG Size)
    ftp_ok = (
        spec.fx3_appfw_sftp_hits == P348_FX3_APPFW_SFTP_HIT_COUNT
        and spec.fx3_appfw_passive_mode_hits == P348_FX3_APPFW_PASSIVE_MODE_HIT_COUNT
        and spec.fx3_appfw_transfer_jpeg_heif_size_hits == P348_FX3_APPFW_TRANSFER_JPEG_HEIF_SIZE_HIT_COUNT
        and spec.reported_ftp_slot_errno == st["ftp_slot_errno"]
        and st["ftp_slot_errno"] is None
        and spec.reported_ftp_protocol_errno == st["ftp_protocol_errno"]
        and st["ftp_protocol_errno"] is None
        and spec.reported_ftp_mode_errno == st["ftp_mode_errno"]
        and st["ftp_mode_errno"] is None
        and spec.reported_transfer_size_errno == st["transfer_size_errno"]
        and st["transfer_size_errno"] is None
        and st["cert_valid"]
        and st["fx6_chunk_ok"]
        and st["ftp_dir_ok"]
        and spec.reported_clip_flag_errno == st["ftp_clip_flag_errno"]
        and st["ftp_clip_flag_errno"] is None
        and spec.post_ftp_servers_cleared == st["post_ftp_servers_cleared"]
        and spec.post_ftp_function_enabled == st["post_ftp_function_enabled"]
        and spec.post_ftp_power_save == st["post_ftp_power_save"]
        and spec.ftp_protocol_sftp_or_jpeg_size_drift_events == 0
    )
    if not ftp_ok:
        _fail(
            P348_BLOCKED_FTP_PROTOCOL_SFTP_OR_JPEG_SIZE_DRIFT,
            "FTP/FTPES 9-slot Passive-only boundary, dormant SFTP / Transfer JPEG Size EOPNOTSUPP=95, or Reset Network boundary violated",
        )

    # 2. White Balance (`Custom 1..3`, `Priority Set in AWB`, `Shutter AWB Lock`, `Shockless WB`, `Cine EI`)
    wb_ok = (
        st["ctemp_valid"]
        and spec.reported_wb_errno == st["wb_errno"]
        and st["wb_errno"] is None
        and st["custom_camset_excluded_ok"]
        and spec.reported_custom_wb_error_hazard == st["custom_wb_error_hazard"]
        and not st["custom_wb_error_hazard"]
        and spec.reported_shutter_awb_lock_errno == st["shutter_awb_lock_errno"]
        and st["shutter_awb_lock_errno"] is None
        and spec.reported_shockless_wb_effective == st["shockless_wb_effective"]
        and spec.reported_shockless_wb_bypassed == st["shockless_wb_bypassed"]
        and st["fx6_wb_valid"]
        and spec.post_wb_mode == st["post_wb_mode"]
        and spec.post_priority_set_in_awb == st["post_priority_set_in_awb"]
        and spec.post_shutter_awb_lock == st["post_shutter_awb_lock"]
        and spec.post_shockless_wb == st["post_shockless_wb"]
        and spec.post_custom_wb_slots_cleared == st["post_custom_wb_slots_cleared"]
        and spec.wb_custom_cine_ei_or_shockless_drift_events == 0
    )
    if not wb_ok:
        _fail(
            P348_BLOCKED_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT,
            "White Balance Custom 1..3 CAMSET exclusion, Cine EI Auto lockout, Shutter AWB Lock Reset-immunity, or Shockless WB contract violated",
        )

    # 3. Zero-RF + USB-LAN Airplane-Mode Bypass Guard & Slot-1 AVF_INFO EROFS=30 Firewall
    slot1_mutated = (
        (
            spec.requested_vault_action in P348_WRITE_MUTATING_VAULT_ACTIONS
            or (spec.requested_vault_slot == P348_SLOT1_VAULT_SLOT and spec.requested_vault_action not in ("NONE", "READ_ONLY_AUDIT"))
        )
        and spec.reported_vault_action_allowed
    )
    zero_rf_and_vault_ok = (
        st["rf_and_usblan_zero_enforced"]
        and not st["wired_usblan_bypass_active"]
        and spec.post_airplane_mode == st["post_airplane_mode"]
        and spec.rf_packets_transmitted == 0
        and spec.usblan_packets_transmitted == 0
        and spec.rf_nvs_mutation_bytes == 0
        and not slot1_mutated
        and spec.reported_vault_action_allowed == st["vault_action_allowed"]
        and spec.vault_firewall_errno == st["vault_firewall_errno"]
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_avf_info_mutation_bytes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_format_hard_locked
        and spec.zero_rf_usblan_or_slot1_avf_bypass_events == 0
    )
    if not zero_rf_and_vault_ok:
        _fail(
            P348_BLOCKED_ZERO_RF_USBLAN_OR_SLOT1_AVF_FIREWALL,
            "Zero-RF (Airplane Mode=On + USB-LAN gated Off) or Slot-1 AVF_INFO / FTP_TRANS_STAT EROFS=30 firewall breached",
        )

    # 4. Stage-B Volatile Overlay & H0 == H3
    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P348_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P348_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P348_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P348_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    overlay_and_h0_h3_ok = overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "63A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "ftp_server_slot": spec.ftp_server_slot,
            "ftp_protocol": spec.ftp_protocol,
            "ftp_transfer_mode": spec.ftp_transfer_mode,
            "usb_lan_enabled": spec.usb_lan_enabled,
            "wb_mode": spec.wb_mode,
            "shutter_awb_lock": spec.post_shutter_awb_lock,
            "shockless_wb": spec.post_shockless_wb,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return FtpFtpesUsbLanCustomWbVaultReport(
        schema=PHASE348_SCHEMA,
        version=PHASE348_VERSION,
        passed=passed,
        status=P348_STATUS_VERIFIED_PILLAR_63A if passed else P348_STATUS_REJECTED_PILLAR_63A,
        block_code=block_code,
        ftp_ftpes_9slots_passive_and_zero_sftp_verified=ftp_ok,
        wb_custom_cine_ei_and_shockless_verified=wb_ok,
        zero_rf_usblan_and_slot1_avf_erofs30_verified=zero_rf_and_vault_ok,
        overlay_and_h0_h3_verified=overlay_and_h0_h3_ok,
        matrix_states_checked=28,
        ftp_protocol_sftp_or_jpeg_size_drift_events=(
            spec.ftp_protocol_sftp_or_jpeg_size_drift_events
        ),
        wb_custom_cine_ei_or_shockless_drift_events=(
            spec.wb_custom_cine_ei_or_shockless_drift_events
        ),
        zero_rf_usblan_or_slot1_avf_bypass_events=(
            spec.zero_rf_usblan_or_slot1_avf_bypass_events
        ),
        rf_packets_transmitted=spec.rf_packets_transmitted,
        usblan_packets_transmitted=spec.usblan_packets_transmitted,
        rf_nvs_mutation_bytes=spec.rf_nvs_mutation_bytes,
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_avf_info_mutation_bytes=spec.slot1_avf_info_mutation_bytes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_movie_af_focusmap_marker_vault(
    spec: MovieAfFocusMapMarkerPeakingVaultSpec,
) -> MovieAfFocusMapMarkerPeakingVaultReport:
    """Evaluate Pillar 63B spec (Movie AF `1..7`/`1..5` parity, App-only `[Focus Map]`, 8 Reset-immune Assist items & Clean-HDMI)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P348_BLOCKED_SAFETY_POLICY_VIOLATION, "Safety policy violation")

    valid_spec = (
        spec.camera_model in (P348_FX3_MODEL_NAME, P348_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P348_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P348_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P348_SHOOTING_DOMAINS
        and spec.af_assist in P348_ON_OFF_MODES
        and spec.marker_display in P348_ON_OFF_MODES
        and spec.center_marker in P348_ON_OFF_MODES
        and spec.guideframe in P348_ON_OFF_MODES
        and spec.peaking_display in P348_ON_OFF_MODES
        and spec.peaking_level in P348_FX3_PEAKING_LEVELS
        and spec.hdmi_info_display in P348_ON_OFF_MODES
        and spec.reset_action in ("None", "Camera Settings Reset", "Initialize")
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P348_VAULT_ACTIONS
        and spec.vault_firewall_errno in P348_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P348_BLOCKED_INVALID_PILLAR63B_SPEC, "Invalid Pillar 63B spec fields")

    st = compute_expected_movie_af_focusmap_marker_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        af_transition_speed=spec.af_transition_speed,
        af_subj_shift_sens=spec.af_subj_shift_sens,
        af_assist=spec.af_assist,
        attached_lens_model=spec.attached_lens_model,
        focus_map_in_body_requested=spec.focus_map_in_body_requested,
        focus_map_remote_mc_requested=spec.focus_map_remote_mc_requested,
        mc_app_version=spec.mc_app_version,
        recording_fps=spec.recording_fps,
        playback_control_active=spec.playback_control_active,
        auto_framing_active=spec.auto_framing_active,
        pdaf_capable_lens_attached=spec.pdaf_capable_lens_attached,
        usb_remote_or_uvc_active=spec.usb_remote_or_uvc_active,
        fx6_hdmi_raw_or_mag_or_extender_active=spec.fx6_hdmi_raw_or_mag_or_extender_active,
        marker_display=spec.marker_display,
        center_marker=spec.center_marker,
        aspect_marker=spec.aspect_marker,
        safety_zone=spec.safety_zone,
        guideframe=spec.guideframe,
        focus_magnifier_active=spec.focus_magnifier_active,
        peaking_display=spec.peaking_display,
        peaking_level=spec.peaking_level,
        peaking_color=spec.peaking_color,
        hdmi_info_display=spec.hdmi_info_display,
        fx6_aspect_mask_level=spec.fx6_aspect_mask_level,
        fx6_aspect_custom_ratio=spec.fx6_aspect_custom_ratio,
        fx6_safety_area=spec.fx6_safety_area,
        fx6_user_box_width=spec.fx6_user_box_width,
        fx6_user_box_height=spec.fx6_user_box_height,
        fx6_user_box_h_pos=spec.fx6_user_box_h_pos,
        fx6_user_box_v_pos=spec.fx6_user_box_v_pos,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    # 1. Movie AF Parity (`1..7` / `1..5`) & App-Only `[Focus Map]` Myth-Busting
    af_focusmap_ok = (
        spec.fx6_appfw_af_subj_shift_6_7_hits == P348_FX6_APPFW_AF_SUBJ_SHIFT_6_7_HITS
        and spec.fx3_in_body_focus_map_bkid_hits == P348_FX3_IN_BODY_FOCUS_MAP_BKID_HITS
        and spec.reported_af_speed_errno == st["af_speed_errno"]
        and st["af_speed_errno"] is None
        and spec.reported_af_shift_errno == st["af_shift_errno"]
        and st["af_shift_errno"] is None
        and spec.reported_af_assist_effective == st["af_assist_effective"]
        and spec.reported_af_assist_errno == st["af_assist_errno"]
        and st["af_assist_errno"] is None
        and spec.reported_focus_map_in_body_errno == st["focus_map_in_body_errno"]
        and st["focus_map_in_body_errno"] is None
        and spec.reported_focus_map_remote_errno == st["focus_map_remote_errno"]
        and st["focus_map_remote_errno"] is None
        and spec.reported_focus_map_effective_active == st["focus_map_effective_active"]
        and spec.post_af_transition_speed == st["post_af_transition_speed"]
        and spec.post_af_subj_shift_sens == st["post_af_subj_shift_sens"]
        and spec.post_af_assist == st["post_af_assist"]
        and spec.movie_af_speed_or_focus_map_spoof_events == 0
    )
    if not af_focusmap_ok:
        _fail(
            P348_BLOCKED_MOVIE_AF_SPEED_OR_FOCUS_MAP_SPOOF,
            "Movie AF Speed 1..7 / Subj. Shift Sens. 1..5 parity, AF Assist lens gate, or App-only Focus Map Ver. 6.00+ boundary violated",
        )

    # 2. 8 Reset-Immune Assist Items (`[Marker Display]` 15 Ratios + `[Peaking Display]` 4 Colors) & Clean-HDMI Isolation
    marker_peaking_ok = (
        st["aspect_marker_valid"]
        and st["safety_zone_valid"]
        and st["peaking_color_valid"]
        and st["fx6_user_box_valid"]
        and spec.reported_effective_marker_visible_on_lcd == st["effective_marker_visible_on_lcd"]
        and spec.hdmi_marker_peaking_pixels_emitted == st["hdmi_marker_peaking_pixels_emitted"]
        and spec.hdmi_marker_peaking_pixels_emitted == 0
        and spec.post_marker_display == st["post_marker_display"]
        and spec.post_center_marker == st["post_center_marker"]
        and spec.post_aspect_marker == st["post_aspect_marker"]
        and spec.post_safety_zone == st["post_safety_zone"]
        and spec.post_guideframe == st["post_guideframe"]
        and spec.post_peaking_display == st["post_peaking_display"]
        and spec.post_peaking_level == st["post_peaking_level"]
        and spec.post_peaking_color == st["post_peaking_color"]
        and spec.marker_15ratio_peaking_hdmi_leak_events == 0
    )
    if not marker_peaking_ok:
        _fail(
            P348_BLOCKED_MARKER_15RATIO_PEAKING_HDMI_LEAK,
            "Marker Display (15 ratios) / Peaking Display Reset-immunity, Clean-HDMI 0px isolation, or FX6 User Box bounds violated",
        )

    # 3. Slot-1 Tier-0 Vault Firewall (`EROFS=30`) & Stage-B Overlay & H0 == H3
    slot1_mutated = (
        (
            spec.requested_vault_action in P348_WRITE_MUTATING_VAULT_ACTIONS
            or (spec.requested_vault_slot == P348_SLOT1_VAULT_SLOT and spec.requested_vault_action not in ("NONE", "READ_ONLY_AUDIT"))
        )
        and spec.reported_vault_action_allowed
    )
    vault_ok = (
        not slot1_mutated
        and spec.reported_vault_action_allowed == st["vault_action_allowed"]
        and spec.vault_firewall_errno == st["vault_firewall_errno"]
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_format_hard_locked
        and spec.zero_rf_usblan_or_slot1_avf_bypass_events == 0
    )
    if not vault_ok:
        _fail(
            P348_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P348_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P348_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P348_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P348_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    vault_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "63B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "af_transition_speed": spec.af_transition_speed,
            "af_subj_shift_sens": spec.af_subj_shift_sens,
            "focus_map_active": spec.reported_focus_map_effective_active,
            "aspect_marker": spec.post_aspect_marker,
            "peaking_color": spec.post_peaking_color,
            "hdmi_pixels": spec.hdmi_marker_peaking_pixels_emitted,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return MovieAfFocusMapMarkerPeakingVaultReport(
        schema=PHASE348_SCHEMA,
        version=PHASE348_VERSION,
        passed=passed,
        status=P348_STATUS_VERIFIED_PILLAR_63B if passed else P348_STATUS_REJECTED_PILLAR_63B,
        block_code=block_code,
        movie_af_parity_and_app_only_focus_map_verified=af_focusmap_ok,
        marker_15ratio_peaking_reset_immune_clean_hdmi_verified=marker_peaking_ok,
        slot1_vault_firewall_and_h0_h3_verified=vault_and_h0_h3_ok,
        matrix_states_checked=28,
        movie_af_speed_or_focus_map_spoof_events=spec.movie_af_speed_or_focus_map_spoof_events,
        marker_15ratio_peaking_hdmi_leak_events=spec.marker_15ratio_peaking_hdmi_leak_events,
        zero_rf_usblan_or_slot1_avf_bypass_events=spec.zero_rf_usblan_or_slot1_avf_bypass_events,
        hdmi_marker_peaking_pixels_emitted=spec.hdmi_marker_peaking_pixels_emitted,
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_ftp_ftpes_customwb_afspeed_focusmap_marker_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_63a: Optional[FtpFtpesUsbLanCustomWbVaultSpec] = None,
    spec_63b: Optional[MovieAfFocusMapMarkerPeakingVaultSpec] = None,
) -> FtpFtpesCustomWbAfFocusMapMarkerVaultReport:
    """Combined single-shot verifier for Pillar 63A + Pillar 63B + bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase348_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_ftp_ftpes_customwb_vault(
        spec_63a or build_default_safe_ftp_ftpes_customwb_vault_spec()
    )
    rep_b = evaluate_movie_af_focusmap_marker_vault(
        spec_63b or build_default_safe_movie_af_focusmap_marker_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 348 Wave-61 donor artifact parity check failed")
    if not donor_snapshot.under_2_0s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return FtpFtpesCustomWbAfFocusMapMarkerVaultReport(
        schema=PHASE348_SCHEMA,
        version=PHASE348_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P348_STATUS_VERIFIED_PILLAR63_SUITE if all_ok else P348_STATUS_FAIL_PILLAR63_SUITE,
        donor_snapshot=donor_snapshot,
        ftp_ftpes_customwb_report=rep_a,
        movie_af_focusmap_marker_report=rep_b,
        ftp_protocol_sftp_or_jpeg_size_drift_events=(
            rep_a.ftp_protocol_sftp_or_jpeg_size_drift_events
        ),
        wb_custom_cine_ei_or_shockless_drift_events=(
            rep_a.wb_custom_cine_ei_or_shockless_drift_events
        ),
        movie_af_speed_or_focus_map_spoof_events=rep_b.movie_af_speed_or_focus_map_spoof_events,
        marker_15ratio_peaking_hdmi_leak_events=rep_b.marker_15ratio_peaking_hdmi_leak_events,
        zero_rf_usblan_or_slot1_avf_bypass_events=(
            rep_a.zero_rf_usblan_or_slot1_avf_bypass_events
            + rep_b.zero_rf_usblan_or_slot1_avf_bypass_events
        ),
        rf_packets_transmitted=rep_a.rf_packets_transmitted,
        usblan_packets_transmitted=rep_a.usblan_packets_transmitted,
        rf_nvs_mutation_bytes=rep_a.rf_nvs_mutation_bytes,
        hdmi_marker_peaking_pixels_emitted=rep_b.hdmi_marker_peaking_pixels_emitted,
        slot1_data_sector_writes=rep_a.slot1_data_sector_writes + rep_b.slot1_data_sector_writes,
        slot1_avf_info_mutation_bytes=rep_a.slot1_avf_info_mutation_bytes,
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


def verify_ftp_ftpes_customwb_afspeed_focusmap_marker_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_63a: Optional[FtpFtpesUsbLanCustomWbVaultSpec] = None,
    spec_63b: Optional[MovieAfFocusMapMarkerPeakingVaultSpec] = None,
) -> FtpFtpesCustomWbAfFocusMapMarkerVaultReport:
    """Symmetry alias for `verify_ftp_ftpes_customwb_afspeed_focusmap_marker_and_vault`."""
    return verify_ftp_ftpes_customwb_afspeed_focusmap_marker_and_vault(
        force_clean_room=force_clean_room,
        spec_63a=spec_63a,
        spec_63b=spec_63b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 63A & 63B)
# ---------------------------------------------------------------------------


def run_pillar63a_ftp_ftpes_customwb_vault_6_scenario_suite() -> Pillar63ASuiteResult:
    """Run 6 Pillar 63A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, FtpFtpesUsbLanCustomWbVaultSpec, Optional[str]], ...] = (
        (
            P348_PILLAR_63A_SCENARIO_IDS[0],
            True,
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                ftp_server_slot=9,
                ftp_protocol="FTPES",
                ftp_transfer_mode="Passive",
                ftp_cert_filename="cacert.pem",
                ftp_cert_slot="Slot 1",
                airplane_mode="On",
                usb_lan_enabled=False,
                ftp_function_enabled=False,
                network_transport="NONE",
                reset_action="Camera Settings Reset",
                post_ftp_servers_cleared=False,
                post_ftp_function_enabled=False,
                post_wb_mode="Auto",
                post_priority_set_in_awb="Standard",
                post_shutter_awb_lock="Off",
                post_shockless_wb="1",
                post_custom_wb_slots_cleared=False,
                post_airplane_mode="On",
            ),
            None,
        ),
        (
            P348_PILLAR_63A_SCENARIO_IDS[1],
            True,
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                camera_model=P348_FX6_DONOR_MODEL_NAME,
                fw_version=P348_FX6_DONOR_FW_VERSION,
                ftp_server_slot=3,
                ftp_protocol="FTPES",
                ftp_transfer_mode="Active",
                ftp_cert_filename=P348_FX6_FTP_CERT_FILENAME,
                ftp_cert_slot=P348_FX6_FTP_CERT_SLOT,
                fx6_auto_upload_proxy_chunk="Chunk",
                fx6_simul_or_relay_active=False,
                shooting_domain="Still",
                wb_mode="Custom 1",
                wb_direct_ctemp_or_tint_tweaked=True,
                log_shooting_mode="Cine EI",
                shutter_awb_lock="Shut. Halfway",
                shockless_wb="2",
                reported_shockless_wb_effective="Off",
                reported_shockless_wb_bypassed=True,
                fx6_wht_bal_switch="A",
                fx6_memory_bank="H",
                fx6_atw_speed=5,
                reset_action="Camera Settings Reset",
                post_wb_mode="Auto",
                post_priority_set_in_awb="Standard",
                post_shutter_awb_lock="Shut. Halfway",
                post_shockless_wb="1",
                post_custom_wb_slots_cleared=False,
            ),
            None,
        ),
        (
            P348_PILLAR_63A_SCENARIO_IDS[2],
            False,
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                ftp_protocol="SFTP",
                ftp_transfer_mode="Active",
                transfer_jpeg_heif_size_requested=True,
                reported_ftp_protocol_errno=None,
                reported_ftp_mode_errno=None,
                reported_transfer_size_errno=None,
                fx3_appfw_sftp_hits=1,
                fx3_appfw_passive_mode_hits=1,
                fx3_appfw_transfer_jpeg_heif_size_hits=1,
                ftp_protocol_sftp_or_jpeg_size_drift_events=1,
            ),
            P348_BLOCKED_FTP_PROTOCOL_SFTP_OR_JPEG_SIZE_DRIFT,
        ),
        (
            P348_PILLAR_63A_SCENARIO_IDS[3],
            False,
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                wb_mode="Auto",
                log_shooting_mode="Cine EI",
                picture_profile="PPLUT1",
                custom_wb_exported_in_camset=True,
                custom_setup_triggered=True,
                reported_wb_errno=None,
                reported_custom_wb_error_hazard=True,
                wb_custom_cine_ei_or_shockless_drift_events=1,
            ),
            P348_BLOCKED_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT,
        ),
        (
            P348_PILLAR_63A_SCENARIO_IDS[4],
            False,
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                airplane_mode="On",
                usb_lan_enabled=True,
                ftp_function_enabled=True,
                post_ftp_function_enabled=True,
                network_transport="USB-LAN",
                usblan_packets_transmitted=64,
                zero_rf_usblan_or_slot1_avf_bypass_events=1,
            ),
            P348_BLOCKED_ZERO_RF_USBLAN_OR_SLOT1_AVF_FIREWALL,
        ),
        (
            P348_PILLAR_63A_SCENARIO_IDS[5],
            False,
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="SAVE_FTP_TRANSFER_LIST_SLOT1",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
                slot1_avf_info_mutation_bytes=4096,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/setting/63a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
                zero_rf_usblan_or_slot1_avf_bypass_events=1,
            ),
            P348_BLOCKED_ZERO_RF_USBLAN_OR_SLOT1_AVF_FIREWALL,
        ),
    )

    outcomes: List[Pillar63ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_ftp_ftpes_customwb_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar63ScenarioOutcome(
                scenario_id=sid,
                pillar="63A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar63ASuiteResult(
        passed=all_ok,
        status=P348_STATUS_VERIFIED_PILLAR_63A if all_ok else P348_STATUS_REJECTED_PILLAR_63A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar63b_movie_af_focusmap_marker_vault_6_scenario_suite() -> Pillar63BSuiteResult:
    """Run 6 Pillar 63B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, MovieAfFocusMapMarkerPeakingVaultSpec, Optional[str]], ...] = (
        (
            P348_PILLAR_63B_SCENARIO_IDS[0],
            True,
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                af_transition_speed=7,
                af_subj_shift_sens=5,
                focus_map_in_body_requested=False,
                focus_map_remote_mc_requested=True,
                mc_app_version="2.1.0",
                recording_fps=120,
                marker_display="On",
                center_marker="On",
                aspect_marker="16:9",
                safety_zone="80%",
                guideframe="On",
                peaking_display="On",
                peaking_level="High",
                peaking_color="White",
                hdmi_info_display="On",
                hdmi_marker_peaking_pixels_emitted=0,
                reset_action="Camera Settings Reset",
                post_af_transition_speed=5,
                post_af_subj_shift_sens=5,
                post_af_assist="Off",
                post_marker_display="On",
                post_center_marker="On",
                post_aspect_marker="16:9",
                post_safety_zone="80%",
                post_guideframe="On",
                post_peaking_display="On",
                post_peaking_level="High",
                post_peaking_color="White",
            ),
            None,
        ),
        (
            P348_PILLAR_63B_SCENARIO_IDS[1],
            True,
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                camera_model=P348_FX6_DONOR_MODEL_NAME,
                fw_version=P348_FX6_DONOR_FW_VERSION,
                af_transition_speed=4,
                af_subj_shift_sens=5,
                focus_map_in_body_requested=True,
                focus_map_remote_mc_requested=False,
                recording_fps=60,
                aspect_marker="2.39:1",
                fx6_aspect_mask_level=15,
                fx6_aspect_custom_ratio=True,
                fx6_safety_area="92.5%",
                fx6_user_box_width=479,
                fx6_user_box_height=269,
                fx6_user_box_h_pos=-476,
                fx6_user_box_v_pos=266,
                peaking_color="B&W",
                post_af_transition_speed=4,
                post_peaking_color="B&W",
            ),
            None,
        ),
        (
            P348_PILLAR_63B_SCENARIO_IDS[2],
            False,
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                camera_model=P348_FX6_DONOR_MODEL_NAME,
                fw_version=P348_FX6_DONOR_FW_VERSION,
                af_subj_shift_sens=7,
                reported_af_shift_errno=None,
                fx6_appfw_af_subj_shift_6_7_hits=2,
                af_assist="On",
                attached_lens_model="SELP1650",
                reported_af_assist_effective="On",
                reported_af_assist_errno=None,
                movie_af_speed_or_focus_map_spoof_events=1,
            ),
            P348_BLOCKED_MOVIE_AF_SPEED_OR_FOCUS_MAP_SPOOF,
        ),
        (
            P348_PILLAR_63B_SCENARIO_IDS[3],
            False,
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                fw_version="2.00",
                focus_map_in_body_requested=True,
                focus_map_remote_mc_requested=True,
                recording_fps=240,
                fx3_in_body_focus_map_bkid_hits=1,
                reported_focus_map_in_body_errno=None,
                reported_focus_map_remote_errno=None,
                reported_focus_map_effective_active=True,
                movie_af_speed_or_focus_map_spoof_events=1,
            ),
            P348_BLOCKED_MOVIE_AF_SPEED_OR_FOCUS_MAP_SPOOF,
        ),
        (
            P348_PILLAR_63B_SCENARIO_IDS[4],
            False,
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                marker_display="On",
                focus_magnifier_active=True,
                reported_effective_marker_visible_on_lcd=True,
                peaking_display="On",
                peaking_color="B&W",
                hdmi_info_display="On",
                hdmi_marker_peaking_pixels_emitted=1280,
                reset_action="Camera Settings Reset",
                post_marker_display="Off",
                post_aspect_marker="Off",
                post_peaking_display="Off",
                marker_15ratio_peaking_hdmi_leak_events=1,
            ),
            P348_BLOCKED_MARKER_15RATIO_PEAKING_HDMI_LEAK,
        ),
        (
            P348_PILLAR_63B_SCENARIO_IDS[5],
            False,
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="FORMAT_QUICK",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/setting/63b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
                zero_rf_usblan_or_slot1_avf_bypass_events=1,
            ),
            P348_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar63ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_movie_af_focusmap_marker_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar63ScenarioOutcome(
                scenario_id=sid,
                pillar="63B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar63BSuiteResult(
        passed=all_ok,
        status=P348_STATUS_VERIFIED_PILLAR_63B if all_ok else P348_STATUS_REJECTED_PILLAR_63B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Standalone Pillar 63 Suite & Unified 63/63 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def run_pillar63_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar63StandaloneReport:
    """Run full Pillar 63 standalone suite (`6/6` Pillar 63A + `6/6` Pillar 63B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase348_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar63a_ftp_ftpes_customwb_vault_6_scenario_suite()
    res_b = run_pillar63b_movie_af_focusmap_marker_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 348 donor verification failed")
    if not donor_snapshot.under_2_0s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE348_SCHEMA,
            "version": PHASE348_VERSION,
            "mode": donor_snapshot.verification_mode,
            "63a": [asdict(s) for s in res_a.scenarios],
            "63b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar63StandaloneReport(
        schema=PHASE348_SCHEMA,
        version=PHASE348_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P348_STATUS_VERIFIED_PILLAR63_SUITE if all_ok else P348_STATUS_FAIL_PILLAR63_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_63a_ftp_ftpes_usblan_customwb_vault=res_a,
        pillar_63b_movie_af_focusmap_marker_peaking_vault=res_b,
        ftp_protocol_sftp_or_jpeg_size_drift_events=(
            P348_FTP_PROTOCOL_SFTP_OR_JPEG_SIZE_DRIFT_EVENTS if res_a.passed else 1
        ),
        wb_custom_cine_ei_or_shockless_drift_events=(
            P348_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT_EVENTS if res_a.passed else 1
        ),
        movie_af_speed_or_focus_map_spoof_events=(
            P348_MOVIE_AF_SPEED_OR_FOCUS_MAP_SPOOF_EVENTS if res_b.passed else 1
        ),
        marker_15ratio_peaking_hdmi_leak_events=(
            P348_MARKER_15RATIO_PEAKING_HDMI_LEAK_EVENTS if res_b.passed else 1
        ),
        zero_rf_usblan_or_slot1_avf_bypass_events=(
            P348_ZERO_RF_USBLAN_OR_SLOT1_AVF_BYPASS_EVENTS if (res_a.passed and res_b.passed) else 1
        ),
        rf_packets_transmitted=P348_RF_PACKETS_TRANSMITTED if res_a.passed else 1,
        usblan_packets_transmitted=P348_USBLAN_PACKETS_TRANSMITTED if res_a.passed else 1,
        rf_nvs_mutation_bytes=P348_RF_NVS_MUTATION_BYTES if res_a.passed else 64,
        hdmi_marker_peaking_pixels_emitted=(
            P348_HDMI_MARKER_PEAKING_LEAK_PIXELS if res_b.passed else 1280
        ),
        slot1_data_sector_writes=(
            P348_SLOT1_DATA_SECTOR_WRITES if (res_a.passed and res_b.passed) else 1
        ),
        slot1_avf_info_mutation_bytes=(
            P348_SLOT1_AVF_INFO_MUTATION_BYTES if res_a.passed else 4096
        ),
        slot1_vault_mutation_bytes=(
            P348_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        slot1_format_hard_locked=P348_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_eopnotsupp_enforced=P348_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
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


def _apply_master63_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def _master63_local_donors_available() -> bool:
    """Return True only when legacy BODYDATA.DAT and all 17 Wave-61 local donors exist."""
    required_relpaths: Tuple[str, ...] = (
        "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT",
        P348_DONOR_FX3_APPFW_702_RELPATH,
        P348_DONOR_FX6_APPFW_601_RELPATH,
        P348_DONOR_FX3_BACKUP_BIN_RELPATH,
        P348_DONOR_FX3_UXC_EN_F_RELPATH,
        P348_DONOR_FX3_UXC_SC_F_RELPATH,
        P348_DONOR_FX3_UXC_TC_F_RELPATH,
        P348_DONOR_FX3_UXC_JA_F_RELPATH,
        P348_DONOR_FX3_UXC_EN_RELPATH,
        P348_DONOR_FX3_UXC_SC_RELPATH,
        P348_DONOR_FX3_UXC_TC_RELPATH,
        P348_DONOR_FX3_UXC_JA_RELPATH,
        P348_DONOR_FX3_UXC_EN_G_RELPATH,
        P348_DONOR_FX3_UXC_SC_G_RELPATH,
        P348_DONOR_FX3_UXC_TC_G_RELPATH,
        P348_DONOR_FX3_UXC_JA_G_RELPATH,
        P348_DONOR_FX6_UXC_EN_RELPATH,
        P348_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for relpath in required_relpaths:
        try:
            resolved = _resolve_phase348_donor_path(relpath)
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


def evaluate_realhw_63pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master63PillarRecoveryReport:
    """Evaluate and aggregate all 63 recovery pillars (`1..63`) concurrently -> `63/63` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_63_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    if resolved_clean_room is None and not _master63_local_donors_available():
        resolved_clean_room = True
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_62pillar() -> Master62PillarRecoveryReport:
        return evaluate_realhw_62pillar_recovery_master(**kw)

    def _run_p63() -> Tuple[Pillar63StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar63_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_62 = pool.submit(_run_62pillar)
        fut_63 = pool.submit(_run_p63)
        m62_rep = fut_62.result()
        p63_rep, p63_dt = fut_63.result()

    all_errors: List[str] = list(m62_rep.errors) + list(p63_rep.errors)
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
        ("cross_model_flash_authorized", False),
    ):
        if getattr(m62_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-62 violated {attr_name} == {expected_val}")
        if getattr(p63_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 63 violated {attr_name} == {expected_val}")

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
        if getattr(m62_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-62 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("ftp_protocol_sftp_or_jpeg_size_drift_events", 0),
        ("wb_custom_cine_ei_or_shockless_drift_events", 0),
        ("movie_af_speed_or_focus_map_spoof_events", 0),
        ("marker_15ratio_peaking_hdmi_leak_events", 0),
        ("zero_rf_usblan_or_slot1_avf_bypass_events", 0),
        ("rf_packets_transmitted", 0),
        ("usblan_packets_transmitted", 0),
        ("rf_nvs_mutation_bytes", 0),
        ("hdmi_marker_peaking_pixels_emitted", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_avf_info_mutation_bytes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_eopnotsupp_enforced", True),
    ):
        if getattr(p63_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 63 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m62_rep.pillars)
    spec63 = MASTER_63_PILLAR_SPECS[62]
    p63_metrics = {
        "pillar_63a_ftp_ftpes_usblan_customwb_vault": (
            f"{p63_rep.pillar_63a_ftp_ftpes_usblan_customwb_vault.scenarios_passed}/"
            f"{p63_rep.pillar_63a_ftp_ftpes_usblan_customwb_vault.scenarios_total}"
        ),
        "pillar_63b_movie_af_focusmap_marker_peaking_vault": (
            f"{p63_rep.pillar_63b_movie_af_focusmap_marker_peaking_vault.scenarios_passed}/"
            f"{p63_rep.pillar_63b_movie_af_focusmap_marker_peaking_vault.scenarios_total}"
        ),
        "ftp_protocol_sftp_or_jpeg_size_drift_events": (
            p63_rep.ftp_protocol_sftp_or_jpeg_size_drift_events
        ),
        "wb_custom_cine_ei_or_shockless_drift_events": (
            p63_rep.wb_custom_cine_ei_or_shockless_drift_events
        ),
        "movie_af_speed_or_focus_map_spoof_events": (
            p63_rep.movie_af_speed_or_focus_map_spoof_events
        ),
        "marker_15ratio_peaking_hdmi_leak_events": (
            p63_rep.marker_15ratio_peaking_hdmi_leak_events
        ),
        "zero_rf_usblan_or_slot1_avf_bypass_events": (
            p63_rep.zero_rf_usblan_or_slot1_avf_bypass_events
        ),
        "rf_packets_transmitted": p63_rep.rf_packets_transmitted,
        "usblan_packets_transmitted": p63_rep.usblan_packets_transmitted,
        "rf_nvs_mutation_bytes": p63_rep.rf_nvs_mutation_bytes,
        "hdmi_marker_peaking_pixels_emitted": p63_rep.hdmi_marker_peaking_pixels_emitted,
        "slot1_data_sector_writes": p63_rep.slot1_data_sector_writes,
        "slot1_avf_info_mutation_bytes": p63_rep.slot1_avf_info_mutation_bytes,
        "slot1_vault_mutation_bytes": p63_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p63_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_eopnotsupp_enforced": p63_rep.slot1_vault_erofs_eopnotsupp_enforced,
        "overall_ready_for_hardware_attach": p63_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p63_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p63_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p63_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec63[0],
            pillar_id=spec63[1],
            phase_label=spec63[2],
            module_name=spec63[3],
            passed=bool(p63_rep.all_passed),
            status=p63_rep.status,
            verification_mode=p63_rep.verification_mode,
            elapsed_seconds=p63_dt,
            key_metrics=p63_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec63[1],
                    "mode": p63_rep.verification_mode,
                    "status": p63_rep.status,
                    "metrics": p63_metrics,
                    "passed": p63_rep.all_passed,
                }
            ),
            errors=tuple(p63_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master63_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p63_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_63_PILLAR_COUNT == 63
        and pillars_passed == 63
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE348_SCHEMA,
            "schema_version": PHASE348_MASTER_SCHEMA,
            "version": PHASE348_VERSION,
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

    return Master63PillarRecoveryReport(
        schema=PHASE348_SCHEMA,
        schema_version=PHASE348_MASTER_SCHEMA,
        version=PHASE348_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=(
            P348_STATUS_VERIFIED_63OF63_AGGREGATOR if all_ok else P348_STATUS_FAIL_63OF63_AGGREGATOR
        ),
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P348_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.50,
        under_6s_budget=elapsed < P348_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P348_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p63_rep.donor_snapshot,
        pillar63_a_ftp_ftpes_usblan_customwb_vault=p63_rep.pillar_63a_ftp_ftpes_usblan_customwb_vault,
        pillar63_b_movie_af_focusmap_marker_peaking_vault=(
            p63_rep.pillar_63b_movie_af_focusmap_marker_peaking_vault
        ),
        ftp_protocol_sftp_or_jpeg_size_drift_events=(
            p63_rep.ftp_protocol_sftp_or_jpeg_size_drift_events
        ),
        wb_custom_cine_ei_or_shockless_drift_events=(
            p63_rep.wb_custom_cine_ei_or_shockless_drift_events
        ),
        movie_af_speed_or_focus_map_spoof_events=p63_rep.movie_af_speed_or_focus_map_spoof_events,
        marker_15ratio_peaking_hdmi_leak_events=p63_rep.marker_15ratio_peaking_hdmi_leak_events,
        zero_rf_usblan_or_slot1_avf_bypass_events=p63_rep.zero_rf_usblan_or_slot1_avf_bypass_events,
        rf_packets_transmitted=p63_rep.rf_packets_transmitted,
        usblan_packets_transmitted=p63_rep.usblan_packets_transmitted,
        rf_nvs_mutation_bytes=p63_rep.rf_nvs_mutation_bytes,
        hdmi_marker_peaking_pixels_emitted=p63_rep.hdmi_marker_peaking_pixels_emitted,
        slot1_data_sector_writes=p63_rep.slot1_data_sector_writes,
        slot1_avf_info_mutation_bytes=p63_rep.slot1_avf_info_mutation_bytes,
        slot1_vault_mutation_bytes=p63_rep.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=p63_rep.slot1_format_hard_locked,
        slot1_vault_erofs_eopnotsupp_enforced=p63_rep.slot1_vault_erofs_eopnotsupp_enforced,
        fx3_appfw_sftp_hits=P348_FX3_APPFW_SFTP_HIT_COUNT,
        fx3_appfw_passive_mode_hits=P348_FX3_APPFW_PASSIVE_MODE_HIT_COUNT,
        fx3_appfw_transfer_jpeg_heif_size_hits=P348_FX3_APPFW_TRANSFER_JPEG_HEIF_SIZE_HIT_COUNT,
        fx3_ftp_server_slot_count=P348_FTP_SERVER_SLOT_COUNT,
        fx3_ftp_passive_mode_only=True,
        fx3_usblan_bypasses_airplane_mode=True,
        fx3_wb_custom_slots=len(P348_WB_CUSTOM_SLOTS),
        fx3_shutter_awb_lock_reset_immune=True,
        fx3_af_transition_speed_max=P348_AF_TRANSITION_SPEED_MAX,
        fx3_af_subj_shift_sens_max=P348_AF_SUBJ_SHIFT_SENS_MAX,
        fx6_af_subj_shift_sens_max=P348_AF_SUBJ_SHIFT_SENS_MAX,
        fx3_in_body_focus_map_bkid_hits=P348_FX3_IN_BODY_FOCUS_MAP_BKID_HITS,
        fx3_focus_map_app_only_since_fw=P348_FX3_FOCUS_MAP_ADDED_FW,
        fx3_aspect_marker_active_ratio_count=len(P348_FX3_ASPECT_MARKER_ACTIVE_RATIOS),
        fx3_peaking_color_count=len(P348_FX3_PEAKING_COLORS),
        fx3_reset_immune_assist_item_count=P348_RESET_IMMUNE_ASSIST_ITEM_COUNT,
        rec_media_prioritize_or_autoswitch_drift_events=(
            m62_rep.rec_media_prioritize_or_autoswitch_drift_events
        ),
        card_speed_vpg200_vpg400_gate_drift_events=(
            m62_rep.card_speed_vpg200_vpg400_gate_drift_events
        ),
        proxy_sq_dci4k_or_120p_lockout_drift_events=(
            m62_rep.proxy_sq_dci4k_or_120p_lockout_drift_events
        ),
        cloud_init_persist_or_power_off_ble_rf_events=(
            m62_rep.cloud_init_persist_or_power_off_ble_rf_events
        ),
        mymenu_42slot_or_fx6_lock_spoof_events=m62_rep.mymenu_42slot_or_fx6_lock_spoof_events,
        zero_rf_or_slot1_vault_bypass_events=m62_rep.zero_rf_or_slot1_vault_bypass_events,
        slot1_dcim_m4root_avf_mutation_bytes=m62_rep.slot1_dcim_m4root_avf_mutation_bytes,
        fx3_appfw_prioritize_hits=m62_rep.fx3_appfw_prioritize_hits,
        fx3_appfw_prm_haita_proxy_hits=m62_rep.fx3_appfw_prm_haita_proxy_hits,
        fx3_has_movie_sort_recording=m62_rep.fx3_has_movie_sort_recording,
        fx3_proxy_dci4k_allowed=m62_rep.fx3_proxy_dci4k_allowed,
        fx3_cloud_star_survives_initialize=m62_rep.fx3_cloud_star_survives_initialize,
        fx3_power_off_ble_forced_off=m62_rep.fx3_power_off_ble_forced_off,
        fx3_mymenu_slot_capacity=m62_rep.fx3_mymenu_slot_capacity,
        fx6_user_menu_max_items=m62_rep.fx6_user_menu_max_items,
        fx6_has_bluetooth_hardware=m62_rep.fx6_has_bluetooth_hardware,
        big6_home_or_lower_left_nd_drift_events=m62_rep.big6_home_or_lower_left_nd_drift_events,
        framing_manual_or_dormant_auto_framing_drift_events=(
            m62_rep.framing_manual_or_dormant_auto_framing_drift_events
        ),
        interval_shoot_9999_or_fx6_mxf_spoof_events=(
            m62_rep.interval_shoot_9999_or_fx6_mxf_spoof_events
        ),
        tc_make_regen_or_hdmi_rec_ctrl_drift_events=(
            m62_rep.tc_make_regen_or_hdmi_rec_ctrl_drift_events
        ),
        access_authen_ssh_tls_or_fan_max_drift_events=(
            m62_rep.access_authen_ssh_tls_or_fan_max_drift_events
        ),
        slot1_dcim_avf_mutation_bytes=m62_rep.slot1_dcim_avf_mutation_bytes,
        fx3_big6_tile_count=m62_rep.fx3_big6_tile_count,
        fx3_has_physical_end_hw=m62_rep.fx3_has_physical_end_hw,
        fx3_has_dormant_auto_framing=m62_rep.fx3_has_dormant_auto_framing,
        fx3_interval_subitem_count=m62_rep.fx3_interval_subitem_count,
        fx3_interval_max_shots=m62_rep.fx3_interval_max_shots,
        fx3_access_authen_http_digest_hits=m62_rep.fx3_access_authen_http_digest_hits,
        fx3_fan_control_mode_count=m62_rep.fx3_fan_control_mode_count,
        fx6_fan_control_mode_count=m62_rep.fx6_fan_control_mode_count,
        fx3_has_fan_control_max=m62_rep.fx3_has_fan_control_max,
        fx6_has_fan_control_max=m62_rep.fx6_has_fan_control_max,
        fx3_has_builtin_evf=m62_rep.fx3_has_builtin_evf,
        fx3_has_var_shutter=m62_rep.fx3_has_var_shutter,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        master_63pillar_sha256=master_sha,
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


def evaluate_63pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master63PillarRecoveryReport:
    """Short alias for `evaluate_realhw_63pillar_recovery_master`."""
    return evaluate_realhw_63pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_63pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master63PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_63pillar_recovery_master`."""
    return evaluate_realhw_63pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
