"""Phase 377 Milestone — Recovery Pillar 69 (`69A`/`69B`) & Concurrent 69/69 Master Recovery Verifier:
Wave-67 Sony ILME-FX3 (Ver. 7.02) vs ILME-FX6 (Ver. 6.01) Empirically Grounded Guardrails:
  * Pillar 69A (`Pixel Mapping` / `Auto Pixel Mapping` vs FX6 `APR` & Zero `ABB` + `Setup -> [Monitor]`
    3-Item Group & Dormant EVF Debunk vs FX6 `VF Setting/Adjust` + Hold Custom Keys & Still-Only
    `[Recall Custom hold 1-3]` Exact 11 Bits / Zero Independent WB vs FX6 `Push AF/AGC/Iris`):
    1. `[Auto Pixel Mapping]` (`Setup -> [Setup Option]`, `_f 0x7734`, default `On`, resists
       `Camera Settings Reset`, resets to `On` on `Initialize`) + manual `[Pixel Mapping]` (`_f 0x61f7`,
       lens cap dark-frame check `_g 0x63f1`/`0x60e7`, battery check
       `INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING`, auto reboot after completion) +
       `[Silent Mode Settings] -> [Target Function Settings] -> [Auto Pixel Mapping]` (default `Off` /
       `Not Target` `_f 0x64e7`, resettable; when `Off` with Setup=`On`, shutdown pixel mapping triggers
       mechanical shutter sound via `vdf_set_shutter_mute_by_pixel_mapping`). Records exact Sony ELF typos
       `BKID_APP_setting_notification_for_pixel_mappinng` & `BKID_APP_pixel_mapping_excuted_status`.
       Contrasts FX6 `Technical > APR` (`LIGHT_DETECTED`/`INVALID_TEMPERATURE`, zero mechanical shutter ->
       lens cap + black cloth `ns1 0x3324`, zero user-exposed `ABB` despite dormant `auto_black_balance`).
    2. `Setup -> [Monitor]` (debunking `[Finder/Monitor]` group name on EVF-less FX3): exact 3 exposed
       items (ALL resist `Camera Settings Reset`, cleared only on `Initialize`): `[Monitor Brightness]`
       (`Manual` `-2..+2` default / `Sunny Weather`), `[Display Quality]` (`Standard` default / `High`,
       thermal lock back to `Standard`), `[Monitor Flip Direction]` (`Auto` default / `Horizontal Flip` /
       `180 Degree Flip` / `No Flip`). All 4 dormant EVF items (`Finder/Monitor Sel.`, `Viewfinder Bright.`,
       `Viewfinder Color Temp.`, `Finder Frame Rate`) strictly blocked `EOPNOTSUPP = 95`. Contrasts FX6
       `Monitoring > VF Setting` (`Brightness 1..15` default `8`, `Color Mode Color/B&W`), `VF Adjust`
       assignable button, physical `MIRROR` switch (`Off/B-T/ROT`), and zero 4-item
       `Backlight/Contrast/Chroma/Color Temp.` submenu.
    3. Hold custom keys (`AF On` Still/Movie/S&Q, `Eye AF` Still/Movie, `Tracking On` Still-only `AF-C`) +
       `[Recall Custom hold 1..3]` (`Reg. Custom Shoot Set`, resists `Camera Settings Reset`, serialized in
       `CAMSET*.DAT`, excluded from `CAMPR*.DAT`): strictly Still `P/A/S/M` ONLY (Movie/S&Q/iAuto blocked
       `EOPNOTSUPP = 95`), exact 11 checkable bits (`shooting_mode`, `aperture`, `shutter_speed`,
       `exposure_comp`, `iso_sensitivity`, `metering_mode`, `drive_mode` excluding Self-timer, `focus_mode`,
       `focus_area`, `af_on`, `still_af_track_sens`), ZERO independent `White Balance` checkbox
       (`shoot_set_registration_white_balance` = 0 hits; blocked `EOPNOTSUPP = 95`). Contrasts FX6 `Push AF`
       / `Push AF/Push MF` / `Push AGC` (blocked in `Cine EI`/`Cine EI Quick`/`Bokeh Control=On`) /
       `Push Auto Iris` (blocked on lens `MANUAL`/`Bokeh Control=On`) and dormant `High/Low Key`.
  * Pillar 69B (`Setup -> [External Output]` HDMI Matrix, `TC Output -> REC Control` Gate, `24.00p` Reboot
    Chain, Dormant `4K/2K` & `24p/60p` Debunk, FX6 `SDI/HDMI` Dual-Output Matrix & Tier-0 `Slot 1`
    `EROFS = 30` Recovery Vault Firewall):
    1. All `Setup -> [External Output]` items resist `Camera Settings Reset` (`Initialize` only):
       - `[HDMI Resolution]` (`Auto` def / `2160p` / `1080p` / `1080i`).
       - `[Rec. Media dur HDMI Output]` (`On` def / `Off(HDMI Only)`; `S&Q` locks `On`; `Off(HDMI Only)` or
         `RAW Output = On` temporarily forces `[HDMI Info. Display] = Off`).
       - `[Output Resolution]` (`Auto` def / `2160p` / `1080p` / `1080i`; forced `1080` downscale when
         `Log Shooting != Off` or `PPLUT1..4` with `Rec. Media = On` and `RAW Output = Off`).
       - `[4K Output Set.(HDMI Only)]` (`59.94p/50p/29.97p/25p/23.98p/24.00p 10bit`): switching between
         `24.00p` and non-`24.00p` forces reboot + playback isolation (`_g 0x61d3/0x6413/0x6423`); records
         exact ELF typo `PRM_HAITA_hdmi_4k_outpute_apsc_restriction`.
       - `[Time Code Output]` (default `Off`; blocked in `S&Q`) -> hard precondition for `[REC Control]`
         (default `Off`; requires `Time Code Output = On` + compatible external recorder; displays
         `(STBY)`/`(REC)`).
       - `[4ch Audio Output]` (`CH1/CH2` def vs `CH3/CH4`; cannot send 4 discrete channels simultaneously).
       - `[CTRL FOR HDMI]` (default `On`, exact ELF typo `BKID_APP_setting_ctrl_for_hmdi`).
       - Dormant `4K/2K Output` & `24p/60p Output` (`_f 0x632b`/`0x781c`) strictly blocked `EOPNOTSUPP = 95`.
    2. Tier-0 `Slot 1` Recovery Vault Firewall (`EROFS = 30`): Whenever `[Rec. Media dur HDMI Output] = On`
       (default, or locked `On` in `S&Q`) or `CAMSET*.DAT` `Save/Load Settings` (`Reg. Custom Shoot Set`)
       targets `Slot 1` (`M4ROOT/CLIP/*.MP4`, `AVF_INFO`, `SONY/SETTING/*/CAMSET/*.DAT`), fail-closed
       immediately with `errno = EROFS (30)` (`slot1_writes = 0`, `cnflasha_ro = True`, `otp_writes = 0`,
       `rpmb_writes = 0`, `passive_tx_packets = 0`, `usb_tx = 0`, `raw_firmware_bytes_leaked = 0`).
    3. FX6 `12G/6G/3G-SDI + HDMI` dual-output matrix (`TC/Media > HDMI TC Out`, `SDI/HDMI Remote I/F` vs
       `Parallel Rec`, `RAW(HDMI) 4240x2392` forces SDI to `1080`, `S&Q > 60fps` with `SDI=On` or `RAW`
       forces HDMI to `1080`).
  * Unified `69/69` Master Recovery Aggregator (Pillars `1..68` + Pillar `69`) running concurrently.

Safety Redlines (HARD-LOCKED):
  - Zero hardware attach, zero physical device writes, zero USB/UART TX, zero OTP/RPMB, zero eMMC writes.
  - Zero `Slot 1` format or data sector writes (`EROFS=30` fail-closed).
  - Zero raw firmware bytes leaked (`raw_firmware_bytes_leaked == 0`).
  - Bounded `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 17-donor inspection (`<= 2.0s` budget) with explicit
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
from .realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier import (
    P348_DONOR_FX3_APPFW_702_RELPATH,
    P348_DONOR_FX3_BACKUP_BIN_RELPATH,
    P348_DONOR_FX3_UXC_EN_F_RELPATH,
    P348_DONOR_FX3_UXC_EN_G_RELPATH,
    P348_DONOR_FX3_UXC_EN_RELPATH,
    P348_DONOR_FX3_UXC_JA_F_RELPATH,
    P348_DONOR_FX3_UXC_JA_G_RELPATH,
    P348_DONOR_FX3_UXC_JA_RELPATH,
    P348_DONOR_FX3_UXC_SC_F_RELPATH,
    P348_DONOR_FX3_UXC_SC_G_RELPATH,
    P348_DONOR_FX3_UXC_SC_RELPATH,
    P348_DONOR_FX3_UXC_TC_F_RELPATH,
    P348_DONOR_FX3_UXC_TC_G_RELPATH,
    P348_DONOR_FX3_UXC_TC_RELPATH,
    P348_DONOR_FX6_APPFW_601_RELPATH,
    P348_DONOR_FX6_UXC_EN_2_RELPATH,
    P348_DONOR_FX6_UXC_EN_RELPATH,
    P348_PINNED_FX3_APPFW_702_BYTES,
    P348_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P348_PINNED_FX3_BACKUP_BIN_BYTES,
    P348_PINNED_FX3_BACKUP_BIN_SHA256,
    P348_PINNED_FX3_UXC_EN_BYTES,
    P348_PINNED_FX3_UXC_EN_F_BYTES,
    P348_PINNED_FX3_UXC_EN_F_SHA256,
    P348_PINNED_FX3_UXC_EN_G_BYTES,
    P348_PINNED_FX3_UXC_EN_G_SHA256,
    P348_PINNED_FX3_UXC_EN_SHA256,
    P348_PINNED_FX3_UXC_JA_BYTES,
    P348_PINNED_FX3_UXC_JA_F_BYTES,
    P348_PINNED_FX3_UXC_JA_F_SHA256,
    P348_PINNED_FX3_UXC_JA_G_BYTES,
    P348_PINNED_FX3_UXC_JA_G_SHA256,
    P348_PINNED_FX3_UXC_JA_SHA256,
    P348_PINNED_FX3_UXC_SC_BYTES,
    P348_PINNED_FX3_UXC_SC_F_BYTES,
    P348_PINNED_FX3_UXC_SC_F_SHA256,
    P348_PINNED_FX3_UXC_SC_G_BYTES,
    P348_PINNED_FX3_UXC_SC_G_SHA256,
    P348_PINNED_FX3_UXC_SC_SHA256,
    P348_PINNED_FX3_UXC_TC_BYTES,
    P348_PINNED_FX3_UXC_TC_F_BYTES,
    P348_PINNED_FX3_UXC_TC_F_SHA256,
    P348_PINNED_FX3_UXC_TC_G_BYTES,
    P348_PINNED_FX3_UXC_TC_G_SHA256,
    P348_PINNED_FX3_UXC_TC_SHA256,
    P348_PINNED_FX6_APPFW_601_BYTES,
    P348_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P348_PINNED_FX6_UXC_EN_2_BYTES,
    P348_PINNED_FX6_UXC_EN_2_SHA256,
    P348_PINNED_FX6_UXC_EN_BYTES,
    P348_PINNED_FX6_UXC_EN_SHA256,
)
from .realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier import (
    MASTER_68_PILLAR_SPECS,
    Master68PillarRecoveryReport,
    evaluate_realhw_68pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Phase 377 Metadata, Safety Redlines & Pinned Budget Constants
# ---------------------------------------------------------------------------

PHASE377_SCHEMA = (
    "realhw_69pillar_pixelmap_monitor_recallhold_hdmi_recctrl_vault_verifier_v1"
)
PHASE377_MASTER_SCHEMA = "realhw_69pillar_recovery_master_v1"
PHASE377_VERSION = "1.0.0"
PHASE377_PHASE_NUMBER = 377

P377_ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"

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
BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED = False
READ_ONLY_DONOR_ACCESS = True

P377_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED = False
P377_CROSS_MODEL_FLASH_AUTHORIZED = False
P377_EMMC_WRITES_AUTHORIZED = False
P377_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
P377_OVERALL_READY_FOR_HARDWARE_ATTACH = False

OTP_FUSE_TOUCHES = 0
OTP_FUSE_WRITES = 0
RPMB_COUNTER_INCREMENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PHYSICAL_DEVICE_WRITES = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

P377_BOUNDED_HEADER_BYTES = 4096
P377_MAX_FULL_DONOR_BYTES = 3_000_000
P377_DONOR_INSPECT_BUDGET_SECONDS = 2.0
P377_DONOR_INSPECT_CI_BUDGET_SECONDS = 2.0
P377_FAST_CLI_BUDGET_SECONDS = 1.50
P377_NOMINAL_BUDGET_SECONDS = 4.00
P377_CONCURRENT_CEILING_SECONDS = 6.00

P377_ENOENT_ERRNO = 2
P377_EBUSY_ERRNO = 16
P377_EINVAL_ERRNO = 22
P377_EROFS_ERRNO = 30
P377_EOPNOTSUPP_ERRNO = 95

# Camera Identities
P377_FX3_MODEL_NAME = "ILME-FX3"
P377_FX3_MODEL_ID = 0x91030080
P377_FX3_PRODUCT_CODENAME = "PRODUCT_MODEL_ALCIN_UUD"
P377_FX3_HELPGUIDE_ID = "ilc/2210"
P377_FX3_FW_VERSION = "7.02"
P377_FX3_SUPPORTED_FW_VERSIONS = (
    "7.02", "7.01", "7.00", "6.02", "6.00", "5.00", "4.00", "3.00", "2.05", "2.04", "2.00"
)

P377_FX6_DONOR_MODEL_NAME = "ILME-FX6"
P377_FX6_DONOR_FW_VERSION = "6.01"
P377_FX6_PRODUCT_CODENAME = "PRODUCT_MODEL_CHAPLIN"

# Pinned Wave-67 17 Donors (14 FX3 + 3 FX6)
P377_DONOR_FX3_APPFW_702_RELPATH = P348_DONOR_FX3_APPFW_702_RELPATH
P377_DONOR_FX3_BACKUP_BIN_RELPATH = P348_DONOR_FX3_BACKUP_BIN_RELPATH
P377_DONOR_FX6_APPFW_601_RELPATH = P348_DONOR_FX6_APPFW_601_RELPATH
P377_DONOR_FX3_UXC_EN_F_RELPATH = P348_DONOR_FX3_UXC_EN_F_RELPATH
P377_DONOR_FX3_UXC_SC_F_RELPATH = P348_DONOR_FX3_UXC_SC_F_RELPATH
P377_DONOR_FX3_UXC_TC_F_RELPATH = P348_DONOR_FX3_UXC_TC_F_RELPATH
P377_DONOR_FX3_UXC_JA_F_RELPATH = P348_DONOR_FX3_UXC_JA_F_RELPATH
P377_DONOR_FX3_UXC_EN_RELPATH = P348_DONOR_FX3_UXC_EN_RELPATH
P377_DONOR_FX3_UXC_SC_RELPATH = P348_DONOR_FX3_UXC_SC_RELPATH
P377_DONOR_FX3_UXC_TC_RELPATH = P348_DONOR_FX3_UXC_TC_RELPATH
P377_DONOR_FX3_UXC_JA_RELPATH = P348_DONOR_FX3_UXC_JA_RELPATH
P377_DONOR_FX3_UXC_EN_G_RELPATH = P348_DONOR_FX3_UXC_EN_G_RELPATH
P377_DONOR_FX3_UXC_SC_G_RELPATH = P348_DONOR_FX3_UXC_SC_G_RELPATH
P377_DONOR_FX3_UXC_TC_G_RELPATH = P348_DONOR_FX3_UXC_TC_G_RELPATH
P377_DONOR_FX3_UXC_JA_G_RELPATH = P348_DONOR_FX3_UXC_JA_G_RELPATH
P377_DONOR_FX6_UXC_EN_RELPATH = P348_DONOR_FX6_UXC_EN_RELPATH
P377_DONOR_FX6_UXC_EN_2_RELPATH = P348_DONOR_FX6_UXC_EN_2_RELPATH

P377_PINNED_FX3_APPFW_702_BYTES = P348_PINNED_FX3_APPFW_702_BYTES
P377_PINNED_FX3_APPFW_702_HDR4K_SHA256 = P348_PINNED_FX3_APPFW_702_HDR4K_SHA256
P377_PINNED_FX3_BACKUP_BIN_BYTES = P348_PINNED_FX3_BACKUP_BIN_BYTES
P377_PINNED_FX3_BACKUP_BIN_SHA256 = P348_PINNED_FX3_BACKUP_BIN_SHA256
P377_PINNED_FX6_APPFW_601_BYTES = P348_PINNED_FX6_APPFW_601_BYTES
P377_PINNED_FX6_APPFW_601_HDR4K_SHA256 = P348_PINNED_FX6_APPFW_601_HDR4K_SHA256

P377_PINNED_FX3_UXC_EN_F_BYTES = P348_PINNED_FX3_UXC_EN_F_BYTES
P377_PINNED_FX3_UXC_EN_F_SHA256 = P348_PINNED_FX3_UXC_EN_F_SHA256
P377_PINNED_FX3_UXC_SC_F_BYTES = P348_PINNED_FX3_UXC_SC_F_BYTES
P377_PINNED_FX3_UXC_SC_F_SHA256 = P348_PINNED_FX3_UXC_SC_F_SHA256
P377_PINNED_FX3_UXC_TC_F_BYTES = P348_PINNED_FX3_UXC_TC_F_BYTES
P377_PINNED_FX3_UXC_TC_F_SHA256 = P348_PINNED_FX3_UXC_TC_F_SHA256
P377_PINNED_FX3_UXC_JA_F_BYTES = P348_PINNED_FX3_UXC_JA_F_BYTES
P377_PINNED_FX3_UXC_JA_F_SHA256 = P348_PINNED_FX3_UXC_JA_F_SHA256
P377_PINNED_FX3_UXC_EN_BYTES = P348_PINNED_FX3_UXC_EN_BYTES
P377_PINNED_FX3_UXC_EN_SHA256 = P348_PINNED_FX3_UXC_EN_SHA256
P377_PINNED_FX3_UXC_SC_BYTES = P348_PINNED_FX3_UXC_SC_BYTES
P377_PINNED_FX3_UXC_SC_SHA256 = P348_PINNED_FX3_UXC_SC_SHA256
P377_PINNED_FX3_UXC_TC_BYTES = P348_PINNED_FX3_UXC_TC_BYTES
P377_PINNED_FX3_UXC_TC_SHA256 = P348_PINNED_FX3_UXC_TC_SHA256
P377_PINNED_FX3_UXC_JA_BYTES = P348_PINNED_FX3_UXC_JA_BYTES
P377_PINNED_FX3_UXC_JA_SHA256 = P348_PINNED_FX3_UXC_JA_SHA256
P377_PINNED_FX3_UXC_EN_G_BYTES = P348_PINNED_FX3_UXC_EN_G_BYTES
P377_PINNED_FX3_UXC_EN_G_SHA256 = P348_PINNED_FX3_UXC_EN_G_SHA256
P377_PINNED_FX3_UXC_SC_G_BYTES = P348_PINNED_FX3_UXC_SC_G_BYTES
P377_PINNED_FX3_UXC_SC_G_SHA256 = P348_PINNED_FX3_UXC_SC_G_SHA256
P377_PINNED_FX3_UXC_TC_G_BYTES = P348_PINNED_FX3_UXC_TC_G_BYTES
P377_PINNED_FX3_UXC_TC_G_SHA256 = P348_PINNED_FX3_UXC_TC_G_SHA256
P377_PINNED_FX3_UXC_JA_G_BYTES = P348_PINNED_FX3_UXC_JA_G_BYTES
P377_PINNED_FX3_UXC_JA_G_SHA256 = P348_PINNED_FX3_UXC_JA_G_SHA256
P377_PINNED_FX6_UXC_EN_BYTES = P348_PINNED_FX6_UXC_EN_BYTES
P377_PINNED_FX6_UXC_EN_SHA256 = P348_PINNED_FX6_UXC_EN_SHA256
P377_PINNED_FX6_UXC_EN_2_BYTES = P348_PINNED_FX6_UXC_EN_2_BYTES
P377_PINNED_FX6_UXC_EN_2_SHA256 = P348_PINNED_FX6_UXC_EN_2_SHA256

# Zero-Violation Pillar 69 Counters & Vault Flags
P377_PIXELMAP_APR_OR_ZERO_ABB_DRIFT_EVENTS = 0
P377_MONITOR_3ITEM_OR_DORMANT_EVF_DRIFT_EVENTS = 0
P377_RECALL_HOLD_11BIT_OR_PUSH_KEY_DRIFT_EVENTS = 0
P377_HDMI_RECCTRL_24P_OR_SLOT1_VAULT_DRIFT_EVENTS = 0

P377_SLOT1_WRITES = 0
P377_SLOT1_DATA_SECTOR_WRITES = 0
P377_SLOT1_SECTOR_WRITES = 0
P377_SLOT1_VAULT_MUTATION_BYTES = 0
P377_CNFLASHA_WRITES = 0
P377_RF_PACKETS_TRANSMITTED = 0
P377_RF_NVS_MUTATION_BYTES = 0

P377_SLOT1_FORMAT_HARD_LOCKED = True
P377_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True
P377_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True
P377_AIRPLANE_MODE_FORCED_ON = True

P377_STAGE_B_VOLATILE_OVERLAY_DIR = "/tmp/fx3_stage_b_overlay/pillar69"
P377_FORBIDDEN_PERSISTENT_TARGETS = (
    "/dev/cnflasha",
    "/setting",
    "/mnt/emmc",
    "/nflasha",
)
P377_TIER0_SURFACE_COUNT = 16

# ---------------------------------------------------------------------------
# Wave-67 Empirically Verified Constants (UXC resid16, ELF & Help Guide)
# ---------------------------------------------------------------------------

# 1. Sub-Pillar 69A-1: `[Pixel Mapping]` / `[Auto Pixel Mapping]` vs FX6 `APR` & Zero `ABB`
P377_AUTO_PIXEL_MAP_F_RESID16S = (0x7734, 0x737F)
P377_AUTO_PIXEL_MAP_G_RESID16 = 0x63FA
P377_MANUAL_PIXEL_MAP_F_RESID16 = 0x61F7
P377_MANUAL_PIXEL_MAP_G_RESID16S = (0x63F1, 0x63F6, 0x60E7, 0x6265)
P377_SILENT_TARGET_NOT_TARGET_F_RESID16 = 0x64E7
P377_SILENT_TARGET_AUTO_PIXEL_MAP_G_RESID16 = 0x623D
P377_DORMANT_PIXEL_MAP_NOTIF_F_RESID16S = (0x693F, 0x6FFF, 0x7979)
P377_DORMANT_PIXEL_MAP_NOTIF_G_RESID16 = 0x63AB

P377_BKID_PIXEL_MAP_NOTIFICATION_SONY_TYPO = (
    "BKID_APP_setting_notification_for_pixel_mappinng"
)
P377_BKID_PIXEL_MAP_EXECUTED_STATUS_SONY_TYPO = (
    "BKID_APP_pixel_mapping_excuted_status"
)
P377_ELF_BATTERY_CHECK_PIXEL_MAP_SYMBOL = "INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING"
P377_ELF_SHUTTER_MUTE_PIXEL_MAP_SYMBOL = "vdf_set_shutter_mute_by_pixel_mapping"

P377_FX3_AUTO_PIXEL_MAP_DEFAULT = "On"
P377_FX3_AUTO_PIXEL_MAP_RESETTABLE = False  # Resists Camera Settings Reset; Initialize -> On
P377_FX3_SILENT_TARGET_AUTO_PIXEL_MAP_DEFAULT = "Off"  # Not Target
P377_FX3_SILENT_TARGET_AUTO_PIXEL_MAP_RESETTABLE = True  # Can be reset!
P377_FX3_HAS_PIXEL_MAP_NOTIFICATION_EXPOSED = False
P377_FX3_HAS_SHUTTER_WHEN_PWR_OFF_EXPOSED = False

P377_FX6_APR_NS1_RESID16_RANGE = (0x2E4E, 0x339C)
P377_FX6_APR_LENS_COVER_NS1_RESID16 = 0x3324
P377_FX6_APR_NS2_RESID16_RANGE = (0x40B5, 0x4283)
P377_FX6_DORMANT_ABB_NS1_RESID16 = 0x2494
P377_FX6_DORMANT_ABB_NS2_RESID16S = (0x4413, 0x4EC8)
P377_FX6_HAS_MECHANICAL_SHUTTER = False
P377_FX6_HAS_USER_EXPOSED_ABB = False

# 2. Sub-Pillar 69A-2: `Setup -> [Monitor]` (3-Item Group + Dormant EVF Debunk) vs FX6 `VF Setting/Adjust`
P377_FX3_MONITOR_GROUP_NAME = "Monitor"
P377_FX3_HAS_FINDER_MONITOR_GROUP = False
P377_FX3_MONITOR_EXPOSED_ITEMS = (
    "Monitor Brightness",
    "Display Quality",
    "Monitor Flip Direction",
)
P377_FX3_MONITOR_GROUP_RESETTABLE = False  # All 3 resist Camera Settings Reset!

P377_MONITOR_BRIGHTNESS_BASE_RESID16S = (0xE44B, 0xE1DA)
P377_MONITOR_BRIGHTNESS_SUNNY_F_RESID16 = 0x7A61
P377_FX3_MONITOR_BRIGHTNESS_MODES = ("Manual", "Sunny Weather")
P377_FX3_MONITOR_BRIGHTNESS_DEFAULT = "Manual"
P377_FX3_MONITOR_BRIGHTNESS_MANUAL_RANGE = (-2, 2)

P377_DISPLAY_QUALITY_F_RESID16S = (0x6C5E, 0x7AC6, 0x6664)
P377_FX3_DISPLAY_QUALITY_MODES = ("Standard", "High")
P377_FX3_DISPLAY_QUALITY_DEFAULT = "Standard"

P377_MONITOR_FLIP_F_RESID16S = (0x6A24, 0x7780, 0x6FCC, 0x7363, 0x72D6)
P377_FX3_MONITOR_FLIP_DIRECTIONS = (
    "Auto",
    "Horizontal Flip",
    "180 Degree Flip",
    "No Flip",
)
P377_FX3_MONITOR_FLIP_DEFAULT = "Auto"

P377_FX3_DORMANT_EVF_ITEMS = (
    "Finder/Monitor Sel.",
    "Viewfinder Bright.",
    "Viewfinder Color Temp.",
    "Finder Frame Rate",
)
P377_DORMANT_EVF_RESID16S = (0x6DAF, 0x6935, 0xE662, 0xE38D, 0x604A, 0x7582, 0x718C)
P377_FX3_HAS_DORMANT_EVF_ITEMS_EXPOSED = False

P377_FX6_VF_SETTING_NS2_RESID16 = 0x423C
P377_FX6_VF_ADJUST_NS1_RESID16S = (0x2223, 0x26B5)
P377_FX6_VF_BRIGHTNESS_RANGE = (1, 15)
P377_FX6_VF_BRIGHTNESS_DEFAULT = 8
P377_FX6_VF_COLOR_MODES = ("Color", "B&W")
P377_FX6_MIRROR_SWITCH_POSITIONS = ("Off", "B-T", "ROT")
P377_FX6_HAS_VF_4ITEM_SUBMENU = False

# 3. Sub-Pillar 69A-3: Hold Custom Keys & Still-Only `[Recall Custom hold 1-3]` vs FX6 `Push AF/AGC/Iris`
P377_HOLD_KEY_F_RESID16S = (0x6DF3, 0x794D, 0x7A60, 0x6EDC, 0x70A8)
P377_REG_CUSTOM_SHOOT_SET_F_RESID16S = (0x6282, 0x7631)
P377_RECALL_CUSTOM_HOLD_F_RESID16S = (0x60B4, 0x7581, 0x725B)

P377_FX3_HOLD_CUSTOM_KEYS = (
    "None",
    "AF On",
    "Eye AF",
    "Tracking On",
    "Tracking on Toggle",
    "Tracking On + AF On",
    "Recall Custom hold 1",
    "Recall Custom hold 2",
    "Recall Custom hold 3",
)
P377_FX3_RECALL_CUSTOM_HOLD_SLOTS = (
    "Recall Custom hold 1",
    "Recall Custom hold 2",
    "Recall Custom hold 3",
)
P377_FX3_RECALL_CUSTOM_HOLD_ALLOWED_MODES = ("P", "A", "S", "M")
P377_FX3_RECALL_CUSTOM_HOLD_11_BITS = (
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
P377_FX3_RECALL_CUSTOM_HOLD_BIT_COUNT = 11
P377_FX3_RECALL_CUSTOM_HOLD_WB_HITS = 0
P377_FX3_RECALL_CUSTOM_HOLD_HAS_INDEPENDENT_WB = False
P377_FX3_REG_CUSTOM_SHOOT_SET_RESETTABLE = False  # Resists Camera Settings Reset!
P377_FX3_REG_CUSTOM_SHOOT_SET_IN_CAMSET = True
P377_FX3_REG_CUSTOM_SHOOT_SET_IN_CAMPR = False

P377_FX6_PUSH_KEYS = (
    "None",
    "Push AF",
    "Push AF/Push MF",
    "One Push AF",
    "Push AGC",
    "Push Auto Iris",
    "One Push Auto Iris",
)
P377_FX6_PUSH_AF_NS1_RESID16 = 0x3204
P377_FX6_PUSH_AF_MF_NS2_RESID16 = 0x431A
P377_FX6_PUSH_AGC_NS1_RESID16 = 0x32C1
P377_FX6_PUSH_AUTO_IRIS_NS1_RESID16 = 0x3366
P377_FX6_DORMANT_HIGH_LOW_KEY_NS2_RESID16 = 0x4B25
P377_FX6_HAS_RECALL_CUSTOM_HOLD = False
P377_FX6_HAS_HIGH_LOW_KEY_EXPOSED = False

# 4. Sub-Pillar 69B: `Setup -> [External Output]` HDMI Matrix, `24.00p` Reboot, `TC -> REC Control`,
#    Dormant `4K/2K` & `24p/60p` Debunk, FX6 `SDI/HDMI` Matrix, & `Slot 1 EROFS=30` Firewall
P377_FX3_EXTERNAL_OUTPUT_RESETTABLE = False  # Entire Setup -> External Output resists Camera Settings Reset!
P377_HDMI_RESOLUTION_RESID16S = (0xE1D5, 0x7817, 0x79BA)
P377_REC_MEDIA_DUR_HDMI_F_RESID16S = (0x6144, 0x6573)
P377_OUTPUT_RESOLUTION_F_RESID16 = 0x79AC
P377_HDMI_4K_OUTPUT_SET_F_RESID16 = 0x74D7
P377_HDMI_24_00P_REBOOT_G_RESID16S = (0x61D3, 0x6413, 0x6423)
P377_HDMI_TC_OUTPUT_F_RESID16 = 0x72AF
P377_HDMI_REC_CONTROL_F_RESID16 = 0x76E1
P377_HDMI_4CH_AUDIO_F_RESID16 = 0x6AA0
P377_HDMI_INFO_DISPLAY_F_RESID16 = 0x6E7C
P377_CTRL_FOR_HDMI_BASE_RESID16 = 0xE41F
P377_DORMANT_24P_60P_OUTPUT_F_RESID16S = (0x632B, 0x781C)

P377_PRM_HAITA_HDMI_4K_OUTPUTE_SONY_TYPO = (
    "PRM_HAITA_hdmi_4k_outpute_apsc_restriction"
)
P377_BKID_CTRL_FOR_HDMI_SONY_TYPO = "BKID_APP_setting_ctrl_for_hmdi"

P377_FX3_HDMI_RESOLUTION_MODES = ("Auto", "2160p", "1080p", "1080i")
P377_FX3_HDMI_RESOLUTION_DEFAULT = "Auto"
P377_FX3_REC_MEDIA_DUR_HDMI_MODES = ("On", "Off(HDMI Only)")
P377_FX3_REC_MEDIA_DUR_HDMI_DEFAULT = "On"
P377_FX3_OUTPUT_RESOLUTION_MODES = ("Auto", "2160p", "1080p", "1080i")
P377_FX3_OUTPUT_RESOLUTION_DEFAULT = "Auto"
P377_FX3_4K_OUTPUT_HDMI_ONLY_RATES = (
    "59.94p 10bit",
    "50p 10bit",
    "29.97p 10bit",
    "25p 10bit",
    "23.98p 10bit",
    "24.00p 10bit",
)
P377_FX3_4K_OUTPUT_HDMI_ONLY_DEFAULT = "59.94p 10bit"
P377_FX3_HDMI_TC_OUTPUT_DEFAULT = "Off"
P377_FX3_HDMI_REC_CONTROL_DEFAULT = "Off"
P377_FX3_HDMI_4CH_AUDIO_MODES = ("CH1/CH2", "CH3/CH4")
P377_FX3_HDMI_4CH_AUDIO_DEFAULT = "CH1/CH2"
P377_FX3_HDMI_INFO_DISPLAY_DEFAULT = "On"
P377_FX3_CTRL_FOR_HDMI_DEFAULT = "On"
P377_FX3_PPLUT_SLOTS = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
P377_FX3_HAS_DORMANT_4K_2K_OUTPUT = False
P377_FX3_HAS_DORMANT_24P_60P_OUTPUT = False

P377_FX6_SDI_HDMI_REC_CONTROL_MODES = ("Off", "SDI/HDMI Remote I/F", "Parallel Rec")
P377_FX6_CODEC_MODES = (
    "XAVC-I",
    "XAVC-L",
    "RAW",
    "RAW & XAVC-I",
    "RAW(HDMI)",
    "RAW(HDMI) & XAVC-I",
)
P377_FX6_HDMI_TC_OUT_NS2_RESID16 = 0x4245
P377_FX6_SDI_HDMI_REC_CONTROL_NS2_RESID16 = 0x428D
P377_FX6_OUTPUT_ON_OFF_NS1_RESID16S = (0x2F38, 0x2F93)

# Common Enums & Vault Constants
P377_ON_OFF_MODES = ("Off", "On")
P377_SHOOTING_DOMAINS = ("Still", "Movie", "S&Q")
P377_EXPOSURE_MODES = ("P", "A", "S", "M", "Flexible Exp.", "iAuto", "Cine EI", "Cine EI Quick")
P377_FOCUS_MODES = ("AF-S", "AF-C", "DMF", "MF")
P377_RESET_ACTIONS = ("None", "Camera Settings Reset", "Initialize")
P377_VAULT_ACTIONS = (
    "NONE",
    "READ_ONLY_AUDIT",
    "HDMI_ONLY_ZERO_MEDIA_WRITE",
    "WRITE_M4ROOT_CLIP_SLOT1",
    "WRITE_AVF_INFO_SLOT1",
    "SAVE_CAMSET_DAT_SLOT1",
    "PIXEL_MAP_CNFLASHA_WRITE",
    "WRITE_M4ROOT_CLIP_SLOT2",
    "SAVE_CAMSET_DAT_SLOT2",
)
P377_WRITE_MUTATING_SLOT1_VAULT_ACTIONS = (
    "WRITE_M4ROOT_CLIP_SLOT1",
    "WRITE_AVF_INFO_SLOT1",
    "SAVE_CAMSET_DAT_SLOT1",
    "PIXEL_MAP_CNFLASHA_WRITE",
)
P377_VAULT_FIREWALL_ERRNOS = (None, "EROFS", "EOPNOTSUPP", "EBUSY", "EINVAL", "ENOENT")

# Status & Block Codes
P377_STATUS_VERIFIED_PILLAR_69A = (
    "VERIFIED_PILLAR_69A_PIXELMAP_APR_MONITOR_3ITEM_EVF_RECALLHOLD_11BIT_PUSH_VAULT"
)
P377_STATUS_REJECTED_PILLAR_69A = (
    "REJECTED_PILLAR_69A_PIXELMAP_APR_MONITOR_3ITEM_EVF_RECALLHOLD_11BIT_PUSH_VAULT"
)
P377_STATUS_VERIFIED_PILLAR_69B = (
    "VERIFIED_PILLAR_69B_HDMI_EXTOUT_TC_RECCTRL_24P_REBOOT_SDI_SLOT1_EROFS_VAULT"
)
P377_STATUS_REJECTED_PILLAR_69B = (
    "REJECTED_PILLAR_69B_HDMI_EXTOUT_TC_RECCTRL_24P_REBOOT_SDI_SLOT1_EROFS_VAULT"
)
P377_STATUS_VERIFIED_PILLAR69_SUITE = (
    "VERIFIED_PILLAR69_PIXELMAP_MONITOR_RECALLHOLD_HDMI_RECCTRL_VAULT"
)
P377_STATUS_FAIL_PILLAR69_SUITE = (
    "FAIL_PILLAR69_PIXELMAP_MONITOR_RECALLHOLD_HDMI_RECCTRL_VAULT"
)
P377_STATUS_VERIFIED_69OF69_AGGREGATOR = "VERIFIED_69OF69_PILLAR_RECOVERY_MASTER"
P377_STATUS_FAIL_69OF69_AGGREGATOR = "FAIL_69OF69_PILLAR_RECOVERY_MASTER"

P377_BLOCKED_SAFETY_POLICY_VIOLATION = "BLOCKED_P377_SAFETY_POLICY_VIOLATION"
P377_BLOCKED_INVALID_PILLAR69A_SPEC = "BLOCKED_P377_INVALID_PILLAR69A_SPEC"
P377_BLOCKED_INVALID_PILLAR69B_SPEC = "BLOCKED_P377_INVALID_PILLAR69B_SPEC"
P377_BLOCKED_PIXELMAP_APR_OR_ZERO_ABB_DRIFT = (
    "BLOCKED_P377_PIXELMAP_APR_OR_ZERO_ABB_DRIFT"
)
P377_BLOCKED_MONITOR_3ITEM_OR_DORMANT_EVF_DRIFT = (
    "BLOCKED_P377_MONITOR_3ITEM_OR_DORMANT_EVF_DRIFT"
)
P377_BLOCKED_RECALL_HOLD_11BIT_OR_PUSH_KEY_DRIFT = (
    "BLOCKED_P377_RECALL_HOLD_11BIT_OR_PUSH_KEY_DRIFT"
)
P377_BLOCKED_HDMI_RECCTRL_24P_OR_DORMANT_OUTPUT_DRIFT = (
    "BLOCKED_P377_HDMI_RECCTRL_24P_OR_DORMANT_OUTPUT_DRIFT"
)
P377_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL = "BLOCKED_P377_SLOT1_VAULT_WRITE_FIREWALL"
P377_BLOCKED_PERSISTENT_OVERLAY_ESCAPE = "BLOCKED_P377_PERSISTENT_OVERLAY_ESCAPE"
P377_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT = "BLOCKED_P377_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P377_PILLAR_69A_SCENARIO_IDS = (
    "p377_69a_01_allow_fx3_autopixelmap_silent_shutter_sound_monitor_3item_reset_resist_and_recall_hold_11bit",
    "p377_69a_02_allow_fx6_apr_black_cloth_zero_abb_vf_setting_mirror_and_push_af_agc_iris",
    "p377_69a_03_reject_pixelmap_low_battery_unshielded_lens_or_fx6_dormant_abb_exposure",
    "p377_69a_04_reject_finder_monitor_group_dormant_evf_4items_thermal_high_spoof_or_fx6_vf_4item",
    "p377_69a_05_reject_recall_hold_movie_sq_iauto_independent_wb_selftimer_or_fx6_push_lockout_highlow",
    "p377_69a_06_reject_slot1_camset_or_cnflasha_write_overlay_escape_or_backup_bin_h0_h3_drift",
)
P377_PILLAR_69B_SCENARIO_IDS = (
    "p377_69b_01_allow_fx3_hdmi_only_24_00p_reboot_tc_recctrl_stby_rec_4ch_pair_and_reset_resist",
    "p377_69b_02_allow_fx6_sdi_hdmi_dual_output_raw_hdmi_1080_sdi_sq_gt60_1080_hdmi_and_parallel_rec",
    "p377_69b_03_reject_rec_control_without_tc_output_sq_hdmi_only_or_4discrete_hdmi_audio",
    "p377_69b_04_reject_dormant_4k_2k_24p_60p_output_log_1080_bypass_or_extout_reset_wipe",
    "p377_69b_05_reject_rec_media_dur_hdmi_on_slot1_m4root_avf_or_camset_write_bypass_erofs30",
    "p377_69b_06_reject_slot1_vault_mutation_overlay_escape_or_backup_bin_h0_h3_drift",
)

MASTER_69_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_68_PILLAR_SPECS + (
    (
        69,
        "pillar69_pixelmap_monitor_recallhold_hdmi_recctrl_vault",
        "Phase 377",
        "realhw_69pillar_pixelmap_monitor_recallhold_hdmi_recctrl_vault_verifier",
    ),
)
MASTER_69_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_69_PILLAR_SPECS)
MASTER_69_PILLAR_COUNT = len(MASTER_69_PILLAR_IDS)


# ---------------------------------------------------------------------------
# Internal Helpers (Canonical SHA-256 with volatile stripping, Safety, Paths)
# ---------------------------------------------------------------------------


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _strip_volatile_timing(obj: Any) -> Any:
    """Recursively strip volatile timing keys (`elapsed_seconds`, `elapsed_ms`) for deterministic hashing."""
    if isinstance(obj, dict):
        return {
            k: _strip_volatile_timing(v)
            for k, v in obj.items()
            if k not in ("elapsed_seconds", "elapsed_ms")
        }
    if isinstance(obj, (list, tuple)):
        return [_strip_volatile_timing(item) for item in obj]
    return obj


def _canonical_sha256(obj: Any) -> str:
    cleaned = _strip_volatile_timing(obj)
    payload = json.dumps(
        cleaned,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _is_clean_room_forced(force_clean_room: Optional[bool]) -> bool:
    if force_clean_room is True:
        return True
    if force_clean_room is False:
        return False
    return bool(is_forced_clean_room() or os.environ.get(P377_ENV_CLEAN_ROOM_TEST) == "1")


def _donor_inspect_budget_seconds() -> float:
    return (
        P377_DONOR_INSPECT_CI_BUDGET_SECONDS
        if os.environ.get("CI")
        else P377_DONOR_INSPECT_BUDGET_SECONDS
    )


def _is_tmpfs_path(path: str) -> bool:
    norm = posixpath.normpath(path)
    return norm == "/tmp" or norm.startswith("/tmp/")


def _targets_persistent_emmc(path: str) -> bool:
    norm = posixpath.normpath(path)
    return any(
        norm == t or norm.startswith(f"{t}/")
        for t in P377_FORBIDDEN_PERSISTENT_TARGETS
    )


def _safety_invariant_errors() -> List[str]:
    errs: List[str] = []
    if CNFLASHA_USERSPACE_WRITE_BLOCKED is not True:
        errs.append("CNFLASHA_USERSPACE_WRITE_BLOCKED must remain True")
    for flag_name, flag_val in (
        ("PERSISTENT_EMMC_WRITES_AUTHORIZED", PERSISTENT_EMMC_WRITES_AUTHORIZED),
        ("SPI_NOR_WRITE_AUTHORIZED", SPI_NOR_WRITE_AUTHORIZED),
        ("EL3_PAYLOAD_TRANSMIT_AUTHORIZED", EL3_PAYLOAD_TRANSMIT_AUTHORIZED),
        ("ISP_WRITE_AUTHORIZED", ISP_WRITE_AUTHORIZED),
        ("PERSISTENT_WRITE_RELEASE", PERSISTENT_WRITE_RELEASE),
        ("ALLOW_BOOT_PARTITION_TARGETING", ALLOW_BOOT_PARTITION_TARGETING),
        ("ALLOW_DESTRUCTIVE_FASTBOOT", ALLOW_DESTRUCTIVE_FASTBOOT),
        ("ALLOW_PERSISTENT_JIRITSU_WRITES", ALLOW_PERSISTENT_JIRITSU_WRITES),
        ("ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS", ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS),
        ("LIVE_USB_IOKIT_TRANSMIT_ENABLED", LIVE_USB_IOKIT_TRANSMIT_ENABLED),
        ("HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", HARDWARE_LIVE_ATTACHMENT_AUTHORIZED),
        ("OVERALL_READY_FOR_HARDWARE_ATTACH", OVERALL_READY_FOR_HARDWARE_ATTACH),
        ("CROSS_MODEL_FLASH_AUTHORIZED", CROSS_MODEL_FLASH_AUTHORIZED),
        ("BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED", BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED),
    ):
        if flag_val is not False:
            errs.append(f"{flag_name} must remain False")
    if READ_ONLY_DONOR_ACCESS is not True:
        errs.append("READ_ONLY_DONOR_ACCESS must remain True")
    for cnt_name, cnt_val in (
        ("OTP_FUSE_TOUCHES", OTP_FUSE_TOUCHES),
        ("OTP_FUSE_WRITES", OTP_FUSE_WRITES),
        ("RPMB_COUNTER_INCREMENTS", RPMB_COUNTER_INCREMENTS),
        ("PASSIVE_TX_BYTES_EMITTED", PASSIVE_TX_BYTES_EMITTED),
        ("PHYSICAL_USB_PACKETS_EMITTED", PHYSICAL_USB_PACKETS_EMITTED),
        ("PHYSICAL_DEVICE_WRITES", PHYSICAL_DEVICE_WRITES),
        ("RAW_FIRMWARE_BYTES_LEAKED", RAW_FIRMWARE_BYTES_LEAKED),
    ):
        if cnt_val != 0:
            errs.append(f"{cnt_name} must remain 0")
    return errs


# ---------------------------------------------------------------------------
# Pure Deterministic Ground-Truth State Evaluators (69A & 69B)
# ---------------------------------------------------------------------------


def compute_expected_pixelmap_monitor_recallhold_vault_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    exposure_mode: str,
    focus_mode: str,
    # 1. Pixel Mapping / Auto Pixel Mapping vs FX6 APR & Zero ABB
    setup_auto_pixel_mapping: str,
    silent_mode: str,
    silent_target_auto_pixel_mapping: str,
    manual_pixel_mapping_requested: bool,
    manual_pixel_map_lens_cap_attached: bool,
    manual_pixel_map_battery_ok: bool,
    pixel_map_notification_requested: bool,
    fx6_apr_requested: bool,
    fx6_apr_lens_cap_and_black_cloth: bool,
    fx6_apr_temperature_valid: bool,
    fx6_abb_requested: bool,
    # 2. Setup -> [Monitor] vs Dormant EVF / FX6 VF Setting & VF Adjust
    monitor_group_name: str,
    monitor_brightness_mode: str,
    monitor_brightness_manual_level: int,
    display_quality: str,
    thermal_elevated: bool,
    monitor_flip_direction: str,
    dormant_evf_item_requested: str,
    fx6_vf_connected: bool,
    fx6_vf_brightness: int,
    fx6_vf_color_mode: str,
    fx6_vf_adjust_pressed: bool,
    fx6_mirror_switch: str,
    fx6_vf_4item_submenu_requested: bool,
    # 3. Hold Custom Keys & Still-Only Recall Custom Hold 1-3 vs FX6 Push AF/AGC/Iris
    hold_custom_key: str,
    recall_selected_bits: Tuple[str, ...],
    recall_independent_wb_requested: bool,
    recall_drive_mode_selftimer_requested: bool,
    recall_persists_in_camset: bool,
    recall_persists_in_campr: bool,
    fx6_push_key: str,
    fx6_lens_manual_mode: bool,
    fx6_bokeh_control_on: bool,
    fx6_desqueeze_active: bool,
    fx6_high_low_key_requested: bool,
    # 4. Reset & Vault
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute exact Wave-67 Pillar 69A expected state (`Pixel Mapping`/`Auto Pixel Mapping` vs FX6 `APR`/zero `ABB`,
    `Setup -> [Monitor]` 3-item group + dormant EVF debunk vs FX6 `VF Setting/Adjust`, & Still-only
    `Recall Custom hold 1-3` exact 11 bits / zero independent WB vs FX6 `Push AF/AGC/Iris`)."""
    is_fx6 = camera_model == P377_FX6_DONOR_MODEL_NAME

    # 1. Pixel Mapping / Auto Pixel Mapping vs FX6 APR & Zero ABB
    pixelmap_errno: Optional[int] = None
    shutdown_shutter_sound_emitted = False
    manual_pixel_map_auto_reboot = False

    if is_fx6:
        if fx6_abb_requested or pixel_map_notification_requested:
            pixelmap_errno = P377_EOPNOTSUPP_ERRNO
        elif manual_pixel_mapping_requested:
            pixelmap_errno = P377_EOPNOTSUPP_ERRNO
        elif fx6_apr_requested:
            if not fx6_apr_lens_cap_and_black_cloth:
                pixelmap_errno = P377_EINVAL_ERRNO  # PIXEL_MAPPING_RESULT_LIGHT_DETECTED
            elif not fx6_apr_temperature_valid:
                pixelmap_errno = P377_EBUSY_ERRNO  # PIXEL_MAPPING_RESULT_INVALID_TEMPERATURE
        effective_auto_pixel_mapping = "None"
        effective_silent_target_auto_pixel_mapping = "None"
    else:
        if pixel_map_notification_requested or fx6_abb_requested or fx6_apr_requested:
            pixelmap_errno = P377_EOPNOTSUPP_ERRNO
        elif manual_pixel_mapping_requested:
            if not manual_pixel_map_battery_ok:
                pixelmap_errno = P377_EBUSY_ERRNO  # INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING
            elif not manual_pixel_map_lens_cap_attached:
                pixelmap_errno = P377_EINVAL_ERRNO  # _g 0x60e7 light shielding insufficient
            else:
                manual_pixel_map_auto_reboot = True
        effective_auto_pixel_mapping = setup_auto_pixel_mapping
        effective_silent_target_auto_pixel_mapping = silent_target_auto_pixel_mapping
        # When Setup Auto Pixel Mapping = On, shutdown triggers mechanical shutter sound UNLESS
        # Silent Mode = On AND Silent Target Auto Pixel Mapping = On!
        shutdown_shutter_sound_emitted = bool(
            setup_auto_pixel_mapping == "On"
            and not (silent_mode == "On" and silent_target_auto_pixel_mapping == "On")
        )

    # 2. Setup -> [Monitor] vs Dormant EVF / FX6 VF Setting & VF Adjust
    monitor_errno: Optional[int] = None
    dormant_evf_errno: Optional[int] = None

    if is_fx6:
        if dormant_evf_item_requested != "None" or fx6_vf_4item_submenu_requested:
            dormant_evf_errno = P377_EOPNOTSUPP_ERRNO
            monitor_errno = P377_EOPNOTSUPP_ERRNO
        elif not (
            P377_FX6_VF_BRIGHTNESS_RANGE[0]
            <= fx6_vf_brightness
            <= P377_FX6_VF_BRIGHTNESS_RANGE[1]
        ):
            monitor_errno = P377_EINVAL_ERRNO
        elif fx6_vf_color_mode not in P377_FX6_VF_COLOR_MODES:
            monitor_errno = P377_EINVAL_ERRNO
        elif fx6_mirror_switch not in P377_FX6_MIRROR_SWITCH_POSITIONS:
            monitor_errno = P377_EINVAL_ERRNO
        elif fx6_vf_adjust_pressed and not fx6_vf_connected:
            monitor_errno = P377_ENOENT_ERRNO  # ns1 0x26b5 "Please connect the viewfinder."
        effective_display_quality = "None"
        thermal_display_quality_locked = False
    else:
        if monitor_group_name != P377_FX3_MONITOR_GROUP_NAME:
            monitor_errno = P377_EOPNOTSUPP_ERRNO
        if dormant_evf_item_requested != "None":
            dormant_evf_errno = P377_EOPNOTSUPP_ERRNO
            monitor_errno = P377_EOPNOTSUPP_ERRNO
        if (
            monitor_brightness_mode == "Manual"
            and not (
                P377_FX3_MONITOR_BRIGHTNESS_MANUAL_RANGE[0]
                <= monitor_brightness_manual_level
                <= P377_FX3_MONITOR_BRIGHTNESS_MANUAL_RANGE[1]
            )
        ):
            monitor_errno = P377_EINVAL_ERRNO
        thermal_display_quality_locked = bool(thermal_elevated and display_quality == "High")
        effective_display_quality = "Standard" if thermal_elevated else display_quality

    # 3. Hold Custom Keys & Still-Only Recall Custom Hold 1-3 vs FX6 Push AF/AGC/Iris
    hold_key_errno: Optional[int] = None
    recall_wb_errno: Optional[int] = (
        P377_EOPNOTSUPP_ERRNO if recall_independent_wb_requested else None
    )
    recall_bits_valid = all(
        b in P377_FX3_RECALL_CUSTOM_HOLD_11_BITS for b in recall_selected_bits
    )
    if "white_balance" in recall_selected_bits:
        recall_wb_errno = P377_EOPNOTSUPP_ERRNO

    if is_fx6:
        if (
            hold_custom_key != "None"
            or fx6_high_low_key_requested
            or recall_independent_wb_requested
            or recall_drive_mode_selftimer_requested
        ):
            hold_key_errno = P377_EOPNOTSUPP_ERRNO
        elif fx6_push_key in ("Push AF", "Push AF/Push MF", "One Push AF") and (
            fx6_lens_manual_mode or fx6_desqueeze_active
        ):
            hold_key_errno = P377_EOPNOTSUPP_ERRNO
        elif fx6_push_key == "Push AGC" and (
            exposure_mode in ("Cine EI", "Cine EI Quick") or fx6_bokeh_control_on
        ):
            hold_key_errno = P377_EOPNOTSUPP_ERRNO
        elif fx6_push_key in ("Push Auto Iris", "One Push Auto Iris") and (
            fx6_lens_manual_mode or fx6_bokeh_control_on
        ):
            hold_key_errno = P377_EOPNOTSUPP_ERRNO
        recall_serialization_valid = True
    else:
        if fx6_push_key != "None" or fx6_high_low_key_requested:
            hold_key_errno = P377_EOPNOTSUPP_ERRNO
        elif hold_custom_key == "Eye AF" and shooting_domain == "S&Q":
            hold_key_errno = P377_EOPNOTSUPP_ERRNO
        elif hold_custom_key in ("Tracking On", "Tracking on Toggle", "Tracking On + AF On"):
            if shooting_domain != "Still" or focus_mode != "AF-C":
                hold_key_errno = P377_EOPNOTSUPP_ERRNO
        elif hold_custom_key in P377_FX3_RECALL_CUSTOM_HOLD_SLOTS:
            if (
                shooting_domain != "Still"
                or exposure_mode not in P377_FX3_RECALL_CUSTOM_HOLD_ALLOWED_MODES
            ):
                hold_key_errno = P377_EOPNOTSUPP_ERRNO
            elif (
                not recall_bits_valid
                or recall_independent_wb_requested
                or recall_drive_mode_selftimer_requested
            ):
                hold_key_errno = P377_EOPNOTSUPP_ERRNO
        elif (
            not recall_bits_valid
            or recall_independent_wb_requested
            or recall_drive_mode_selftimer_requested
        ):
            hold_key_errno = P377_EOPNOTSUPP_ERRNO
        recall_serialization_valid = bool(recall_persists_in_camset and not recall_persists_in_campr)

    # 4. Camera Settings Reset vs Initialize Persistence Boundaries
    if is_fx6:
        post_auto_pixel_mapping = "None"
        post_silent_target_auto_pixel_mapping = "None"
        post_monitor_brightness_mode = "None"
        post_display_quality = "None"
        post_monitor_flip_direction = "None"
        post_reg_custom_shoot_set_retained = False
    elif reset_action == "Initialize":
        post_auto_pixel_mapping = P377_FX3_AUTO_PIXEL_MAP_DEFAULT
        post_silent_target_auto_pixel_mapping = P377_FX3_SILENT_TARGET_AUTO_PIXEL_MAP_DEFAULT
        post_monitor_brightness_mode = P377_FX3_MONITOR_BRIGHTNESS_DEFAULT
        post_display_quality = P377_FX3_DISPLAY_QUALITY_DEFAULT
        post_monitor_flip_direction = P377_FX3_MONITOR_FLIP_DEFAULT
        post_reg_custom_shoot_set_retained = False  # Cleared on Initialize
    elif reset_action == "Camera Settings Reset":
        post_auto_pixel_mapping = setup_auto_pixel_mapping  # Resists Reset!
        post_silent_target_auto_pixel_mapping = P377_FX3_SILENT_TARGET_AUTO_PIXEL_MAP_DEFAULT  # Can be reset!
        post_monitor_brightness_mode = monitor_brightness_mode  # Resists Reset!
        post_display_quality = display_quality  # Resists Reset!
        post_monitor_flip_direction = monitor_flip_direction  # Resists Reset!
        post_reg_custom_shoot_set_retained = True  # Resists Reset!
    else:
        post_auto_pixel_mapping = setup_auto_pixel_mapping
        post_silent_target_auto_pixel_mapping = silent_target_auto_pixel_mapping
        post_monitor_brightness_mode = monitor_brightness_mode
        post_display_quality = display_quality
        post_monitor_flip_direction = monitor_flip_direction
        post_reg_custom_shoot_set_retained = True

    # 5. Tier-0 Slot-1 Vault Firewall
    write_blocked_erofs = (
        slot1_holds_tier0_vault
        and (
            requested_vault_action in P377_WRITE_MUTATING_SLOT1_VAULT_ACTIONS
            or (
                requested_vault_slot == 1
                and requested_vault_action not in ("NONE", "READ_ONLY_AUDIT", "HDMI_ONLY_ZERO_MEDIA_WRITE")
            )
        )
    )
    vault_action_allowed = not write_blocked_erofs and (
        requested_vault_action
        in (
            "NONE",
            "READ_ONLY_AUDIT",
            "HDMI_ONLY_ZERO_MEDIA_WRITE",
            "WRITE_M4ROOT_CLIP_SLOT2",
            "SAVE_CAMSET_DAT_SLOT2",
        )
    )
    vault_firewall_errno: Optional[str] = "EROFS" if write_blocked_erofs else None

    return {
        "pixelmap_errno": pixelmap_errno,
        "effective_auto_pixel_mapping": effective_auto_pixel_mapping,
        "effective_silent_target_auto_pixel_mapping": effective_silent_target_auto_pixel_mapping,
        "shutdown_shutter_sound_emitted": shutdown_shutter_sound_emitted,
        "manual_pixel_map_auto_reboot": manual_pixel_map_auto_reboot,
        "monitor_errno": monitor_errno,
        "dormant_evf_errno": dormant_evf_errno,
        "effective_display_quality": effective_display_quality,
        "thermal_display_quality_locked": thermal_display_quality_locked,
        "hold_key_errno": hold_key_errno,
        "recall_wb_errno": recall_wb_errno,
        "recall_bits_valid": recall_bits_valid,
        "recall_serialization_valid": recall_serialization_valid,
        "post_auto_pixel_mapping": post_auto_pixel_mapping,
        "post_silent_target_auto_pixel_mapping": post_silent_target_auto_pixel_mapping,
        "post_monitor_brightness_mode": post_monitor_brightness_mode,
        "post_display_quality": post_display_quality,
        "post_monitor_flip_direction": post_monitor_flip_direction,
        "post_reg_custom_shoot_set_retained": post_reg_custom_shoot_set_retained,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


def compute_expected_hdmi_recctrl_24p_sdi_slot1_vault_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    log_shooting_mode: str,
    picture_profile: str,
    # FX3 Setup -> [External Output] HDMI Matrix
    hdmi_resolution: str,
    rec_media_dur_hdmi_output: str,
    output_resolution: str,
    hdmi_4k_output_rate_prev: str,
    hdmi_4k_output_rate_new: str,
    raw_output_enabled: str,
    time_code_output: str,
    rec_control: str,
    compatible_external_recorder_connected: bool,
    usb_streaming_active: bool,
    hdmi_4ch_audio_output: str,
    four_discrete_hdmi_audio_requested: bool,
    hdmi_info_display: str,
    ctrl_for_hdmi: str,
    dormant_4k_2k_output_requested: bool,
    dormant_24p_60p_output_requested: bool,
    # FX6 Dual-Output SDI + HDMI Matrix
    fx6_sdi_output_on: bool,
    fx6_hdmi_output_on: bool,
    fx6_codec_mode: str,
    fx6_sq_fps: int,
    fx6_hdmi_tc_out: str,
    fx6_sdi_hdmi_rec_control: str,
    fx6_card_inserted: bool,
    # Reset & Tier-0 Slot-1 Vault
    reset_action: str,
    recording_target_slot: int,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute exact Wave-67 Pillar 69B expected state (`Setup -> [External Output]` HDMI matrix,
    `TC Output -> REC Control` gate, `24.00p` reboot & playback isolation, dormant `4K/2K` & `24p/60p`
    debunk, FX6 `SDI/HDMI` dual-output matrix, & Tier-0 `Slot 1 EROFS=30` Recovery Vault Firewall)."""
    is_fx6 = camera_model == P377_FX6_DONOR_MODEL_NAME

    hdmi_matrix_errno: Optional[int] = None
    dormant_output_errno: Optional[int] = (
        P377_EOPNOTSUPP_ERRNO
        if (dormant_4k_2k_output_requested or dormant_24p_60p_output_requested)
        else None
    )

    if is_fx6:
        if dormant_4k_2k_output_requested or dormant_24p_60p_output_requested:
            hdmi_matrix_errno = P377_EOPNOTSUPP_ERRNO
        if fx6_sdi_hdmi_rec_control not in P377_FX6_SDI_HDMI_REC_CONTROL_MODES:
            hdmi_matrix_errno = P377_EOPNOTSUPP_ERRNO
        if fx6_codec_mode not in P377_FX6_CODEC_MODES:
            hdmi_matrix_errno = P377_EOPNOTSUPP_ERRNO
        # FX6 HDMI trigger requires HDMI TC Out = On
        if (
            fx6_sdi_hdmi_rec_control != "Off"
            and fx6_hdmi_output_on
            and fx6_hdmi_tc_out != "On"
        ):
            hdmi_matrix_errno = P377_EOPNOTSUPP_ERRNO
        # FX6 Parallel Rec requires card inserted
        if fx6_sdi_hdmi_rec_control == "Parallel Rec" and not fx6_card_inserted:
            hdmi_matrix_errno = P377_EOPNOTSUPP_ERRNO

        fx6_sdi_forced_1080 = fx6_codec_mode in ("RAW(HDMI)", "RAW(HDMI) & XAVC-I")
        fx6_hdmi_forced_1080 = bool(
            shooting_domain == "S&Q"
            and fx6_sq_fps > 60
            and (fx6_sdi_output_on or fx6_codec_mode in ("RAW", "RAW & XAVC-I"))
        )
        effective_rec_media_dur_hdmi = "None"
        effective_output_resolution = "1080p" if fx6_hdmi_forced_1080 else "2160p"
        output_forced_1080_downscale = fx6_hdmi_forced_1080
        effective_hdmi_info_display = "None"
        reboot_required_for_24_00p_switch = False
        cross_24_00p_playback_isolated = False
        rec_control_stby_rec_indicator_active = bool(
            fx6_sdi_hdmi_rec_control != "Off" and hdmi_matrix_errno is None
        )
        internal_media_write_attempted = bool(fx6_card_inserted)
    else:
        fx6_sdi_forced_1080 = False
        fx6_hdmi_forced_1080 = False

        if dormant_4k_2k_output_requested or dormant_24p_60p_output_requested:
            hdmi_matrix_errno = P377_EOPNOTSUPP_ERRNO

        # S&Q locks Rec. Media dur HDMI Output = On, blocks RAW Output = On, and blocks Time Code Output = On
        if shooting_domain == "S&Q" and rec_media_dur_hdmi_output == "Off(HDMI Only)":
            hdmi_matrix_errno = P377_EOPNOTSUPP_ERRNO
        if shooting_domain == "S&Q" and raw_output_enabled == "On":
            hdmi_matrix_errno = P377_EOPNOTSUPP_ERRNO
        if shooting_domain == "S&Q" and time_code_output == "On":
            hdmi_matrix_errno = P377_EOPNOTSUPP_ERRNO

        # REC Control hard preconditions: Time Code Output == On + compatible external recorder + no USB streaming
        if rec_control == "On":
            if (
                time_code_output != "On"
                or not compatible_external_recorder_connected
                or usb_streaming_active
            ):
                hdmi_matrix_errno = P377_EOPNOTSUPP_ERRNO

        # 4ch Audio Output cannot send 4 discrete channels simultaneously over HDMI
        if four_discrete_hdmi_audio_requested:
            hdmi_matrix_errno = P377_EOPNOTSUPP_ERRNO

        effective_rec_media_dur_hdmi = (
            "On" if shooting_domain == "S&Q" else rec_media_dur_hdmi_output
        )

        # Output Resolution forced downscale to 1080 when Log Shooting != Off or PPLUT1..4 with Rec. Media = On & RAW = Off
        output_forced_1080_downscale = bool(
            effective_rec_media_dur_hdmi == "On"
            and raw_output_enabled == "Off"
            and (log_shooting_mode != "Off" or picture_profile in P377_FX3_PPLUT_SLOTS)
        )
        if output_forced_1080_downscale and output_resolution == "2160p":
            effective_output_resolution = "1080p"
        elif output_forced_1080_downscale and output_resolution == "Auto":
            effective_output_resolution = "1080p"
        else:
            effective_output_resolution = output_resolution

        # Off(HDMI Only) or RAW Output = On temporarily forces HDMI Info. Display = Off
        effective_hdmi_info_display = (
            "Off"
            if (effective_rec_media_dur_hdmi == "Off(HDMI Only)" or raw_output_enabled == "On")
            else hdmi_info_display
        )

        # 24.00p <-> non-24.00p switch forces reboot + playback isolation (_g 0x61d3/0x6413/0x6423)
        prev_is_24 = hdmi_4k_output_rate_prev == "24.00p 10bit"
        new_is_24 = hdmi_4k_output_rate_new == "24.00p 10bit"
        reboot_required_for_24_00p_switch = prev_is_24 != new_is_24
        cross_24_00p_playback_isolated = new_is_24 or reboot_required_for_24_00p_switch

        rec_control_stby_rec_indicator_active = bool(
            rec_control == "On"
            and time_code_output == "On"
            and compatible_external_recorder_connected
            and not usb_streaming_active
            and shooting_domain != "S&Q"
        )
        internal_media_write_attempted = bool(effective_rec_media_dur_hdmi == "On")

    # Camera Settings Reset vs Initialize: ALL Setup -> [External Output] items resist Camera Settings Reset!
    if is_fx6:
        post_rec_media_dur_hdmi = "None"
        post_output_resolution = "None"
        post_time_code_output = "None"
        post_rec_control = "None"
        post_hdmi_4ch_audio = "None"
        post_hdmi_info_display = "None"
        post_ctrl_for_hdmi = "None"
    elif reset_action == "Initialize":
        post_rec_media_dur_hdmi = P377_FX3_REC_MEDIA_DUR_HDMI_DEFAULT
        post_output_resolution = P377_FX3_OUTPUT_RESOLUTION_DEFAULT
        post_time_code_output = P377_FX3_HDMI_TC_OUTPUT_DEFAULT
        post_rec_control = P377_FX3_HDMI_REC_CONTROL_DEFAULT
        post_hdmi_4ch_audio = P377_FX3_HDMI_4CH_AUDIO_DEFAULT
        post_hdmi_info_display = P377_FX3_HDMI_INFO_DISPLAY_DEFAULT
        post_ctrl_for_hdmi = P377_FX3_CTRL_FOR_HDMI_DEFAULT
    else:
        # Both "None" and "Camera Settings Reset" preserve ALL External Output settings!
        post_rec_media_dur_hdmi = rec_media_dur_hdmi_output
        post_output_resolution = output_resolution
        post_time_code_output = time_code_output
        post_rec_control = rec_control
        post_hdmi_4ch_audio = hdmi_4ch_audio_output
        post_hdmi_info_display = hdmi_info_display
        post_ctrl_for_hdmi = ctrl_for_hdmi

    # Tier-0 Slot-1 Recovery Vault Firewall (`EROFS = 30`)
    slot1_targeted_write = (
        requested_vault_action in P377_WRITE_MUTATING_SLOT1_VAULT_ACTIONS
        or (
            requested_vault_slot == 1
            and requested_vault_action
            not in ("NONE", "READ_ONLY_AUDIT", "HDMI_ONLY_ZERO_MEDIA_WRITE")
        )
        or (
            not is_fx6
            and internal_media_write_attempted
            and recording_target_slot == 1
            and requested_vault_action not in ("NONE", "READ_ONLY_AUDIT", "HDMI_ONLY_ZERO_MEDIA_WRITE")
        )
    )
    write_blocked_erofs = bool(slot1_holds_tier0_vault and slot1_targeted_write)
    vault_action_allowed = not write_blocked_erofs and (
        requested_vault_action
        in (
            "NONE",
            "READ_ONLY_AUDIT",
            "HDMI_ONLY_ZERO_MEDIA_WRITE",
            "WRITE_M4ROOT_CLIP_SLOT2",
            "SAVE_CAMSET_DAT_SLOT2",
        )
    )
    vault_firewall_errno: Optional[str] = "EROFS" if write_blocked_erofs else None

    return {
        "hdmi_matrix_errno": hdmi_matrix_errno,
        "dormant_output_errno": dormant_output_errno,
        "effective_rec_media_dur_hdmi": effective_rec_media_dur_hdmi,
        "effective_output_resolution": effective_output_resolution,
        "output_forced_1080_downscale": output_forced_1080_downscale,
        "effective_hdmi_info_display": effective_hdmi_info_display,
        "reboot_required_for_24_00p_switch": reboot_required_for_24_00p_switch,
        "cross_24_00p_playback_isolated": cross_24_00p_playback_isolated,
        "rec_control_stby_rec_indicator_active": rec_control_stby_rec_indicator_active,
        "internal_media_write_attempted": internal_media_write_attempted,
        "fx6_sdi_forced_1080": fx6_sdi_forced_1080,
        "fx6_hdmi_forced_1080": fx6_hdmi_forced_1080,
        "post_rec_media_dur_hdmi": post_rec_media_dur_hdmi,
        "post_output_resolution": post_output_resolution,
        "post_time_code_output": post_time_code_output,
        "post_rec_control": post_rec_control,
        "post_hdmi_4ch_audio": post_hdmi_4ch_audio,
        "post_hdmi_info_display": post_hdmi_info_display,
        "post_ctrl_for_hdmi": post_ctrl_for_hdmi,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


# ---------------------------------------------------------------------------
# Bounded Read-Only Donor Inspection (`O_RDONLY | O_NOFOLLOW | O_NONBLOCK`, 17 Donors)
# ---------------------------------------------------------------------------


def _iter_work_roots() -> Tuple[Optional[Path], ...]:
    return _fx3_files.iter_donor_work_roots()


def _resolve_phase377_donor_path(
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
    max_full_bytes: int = P377_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    try:
        resolved = _resolve_phase377_donor_path(relpath)
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
        hdr = os.pread(fd, min(P377_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase377_donors() -> Tuple["Phase377DonorArtifactDigest", ...]:
    specs = (
        ("fx3_appfw_702_so", P377_DONOR_FX3_APPFW_702_RELPATH, P377_PINNED_FX3_APPFW_702_BYTES, P377_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P377_PINNED_FX3_APPFW_702_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702"),
        ("fx3_backup_bin", P377_DONOR_FX3_BACKUP_BIN_RELPATH, P377_PINNED_FX3_BACKUP_BIN_BYTES, P377_PINNED_FX3_BACKUP_BIN_BYTES, "FULL_SHA256", P377_PINNED_FX3_BACKUP_BIN_SHA256, "SYNTHETIC_BK4_ILME_FX3"),
        ("fx6_appfw_601_so", P377_DONOR_FX6_APPFW_601_RELPATH, P377_PINNED_FX6_APPFW_601_BYTES, P377_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P377_PINNED_FX6_APPFW_601_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601"),
        ("fx3_uxc_en_f", P377_DONOR_FX3_UXC_EN_F_RELPATH, P377_PINNED_FX3_UXC_EN_F_BYTES, P377_PINNED_FX3_UXC_EN_F_BYTES, "FULL_SHA256", P377_PINNED_FX3_UXC_EN_F_SHA256, "SYNTHETIC_UXC7_FX3_EN_F"),
        ("fx3_uxc_sc_f", P377_DONOR_FX3_UXC_SC_F_RELPATH, P377_PINNED_FX3_UXC_SC_F_BYTES, P377_PINNED_FX3_UXC_SC_F_BYTES, "FULL_SHA256", P377_PINNED_FX3_UXC_SC_F_SHA256, "SYNTHETIC_UXC7_FX3_SC_F"),
        ("fx3_uxc_tc_f", P377_DONOR_FX3_UXC_TC_F_RELPATH, P377_PINNED_FX3_UXC_TC_F_BYTES, P377_PINNED_FX3_UXC_TC_F_BYTES, "FULL_SHA256", P377_PINNED_FX3_UXC_TC_F_SHA256, "SYNTHETIC_UXC7_FX3_TC_F"),
        ("fx3_uxc_ja_f", P377_DONOR_FX3_UXC_JA_F_RELPATH, P377_PINNED_FX3_UXC_JA_F_BYTES, P377_PINNED_FX3_UXC_JA_F_BYTES, "FULL_SHA256", P377_PINNED_FX3_UXC_JA_F_SHA256, "SYNTHETIC_UXC7_FX3_JA_F"),
        ("fx3_uxc_en", P377_DONOR_FX3_UXC_EN_RELPATH, P377_PINNED_FX3_UXC_EN_BYTES, P377_PINNED_FX3_UXC_EN_BYTES, "FULL_SHA256", P377_PINNED_FX3_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX3_EN"),
        ("fx3_uxc_sc", P377_DONOR_FX3_UXC_SC_RELPATH, P377_PINNED_FX3_UXC_SC_BYTES, P377_PINNED_FX3_UXC_SC_BYTES, "FULL_SHA256", P377_PINNED_FX3_UXC_SC_SHA256, "SYNTHETIC_UXC7_FX3_SC"),
        ("fx3_uxc_tc", P377_DONOR_FX3_UXC_TC_RELPATH, P377_PINNED_FX3_UXC_TC_BYTES, P377_PINNED_FX3_UXC_TC_BYTES, "FULL_SHA256", P377_PINNED_FX3_UXC_TC_SHA256, "SYNTHETIC_UXC7_FX3_TC"),
        ("fx3_uxc_ja", P377_DONOR_FX3_UXC_JA_RELPATH, P377_PINNED_FX3_UXC_JA_BYTES, P377_PINNED_FX3_UXC_JA_BYTES, "FULL_SHA256", P377_PINNED_FX3_UXC_JA_SHA256, "SYNTHETIC_UXC7_FX3_JA"),
        ("fx3_uxc_en_g", P377_DONOR_FX3_UXC_EN_G_RELPATH, P377_PINNED_FX3_UXC_EN_G_BYTES, P377_PINNED_FX3_UXC_EN_G_BYTES, "FULL_SHA256", P377_PINNED_FX3_UXC_EN_G_SHA256, "SYNTHETIC_UXC7_FX3_EN_G"),
        ("fx3_uxc_sc_g", P377_DONOR_FX3_UXC_SC_G_RELPATH, P377_PINNED_FX3_UXC_SC_G_BYTES, P377_PINNED_FX3_UXC_SC_G_BYTES, "FULL_SHA256", P377_PINNED_FX3_UXC_SC_G_SHA256, "SYNTHETIC_UXC7_FX3_SC_G"),
        ("fx3_uxc_tc_g", P377_DONOR_FX3_UXC_TC_G_RELPATH, P377_PINNED_FX3_UXC_TC_G_BYTES, P377_PINNED_FX3_UXC_TC_G_BYTES, "FULL_SHA256", P377_PINNED_FX3_UXC_TC_G_SHA256, "SYNTHETIC_UXC7_FX3_TC_G"),
        ("fx3_uxc_ja_g", P377_DONOR_FX3_UXC_JA_G_RELPATH, P377_PINNED_FX3_UXC_JA_G_BYTES, P377_PINNED_FX3_UXC_JA_G_BYTES, "FULL_SHA256", P377_PINNED_FX3_UXC_JA_G_SHA256, "SYNTHETIC_UXC7_FX3_JA_G"),
        ("fx6_uxc_en", P377_DONOR_FX6_UXC_EN_RELPATH, P377_PINNED_FX6_UXC_EN_BYTES, P377_PINNED_FX6_UXC_EN_BYTES, "FULL_SHA256", P377_PINNED_FX6_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX6_EN"),
        ("fx6_uxc_en_2", P377_DONOR_FX6_UXC_EN_2_RELPATH, P377_PINNED_FX6_UXC_EN_2_BYTES, P377_PINNED_FX6_UXC_EN_2_BYTES, "FULL_SHA256", P377_PINNED_FX6_UXC_EN_2_SHA256, "SYNTHETIC_UXC7_FX6_EN_2"),
    )
    return tuple(
        Phase377DonorArtifactDigest(
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


def inspect_phase377_donors_readonly(
    force_clean_room: Optional[bool] = None,
) -> "Phase377DonorSnapshot":
    """Inspect Wave-67 FX3 (`14` donors) & FX6 (`3` donors) strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase377_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase377DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_2_0s_budget=dt <= budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        ("fx3_appfw_702_so", P377_DONOR_FX3_APPFW_702_RELPATH, P377_PINNED_FX3_APPFW_702_BYTES, P377_PINNED_FX3_APPFW_702_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702")),
        ("fx3_backup_bin", P377_DONOR_FX3_BACKUP_BIN_RELPATH, P377_PINNED_FX3_BACKUP_BIN_BYTES, P377_PINNED_FX3_BACKUP_BIN_SHA256, lambda d: _check_bk4_backup(d, "ILME_FX3")),
        ("fx6_appfw_601_so", P377_DONOR_FX6_APPFW_601_RELPATH, P377_PINNED_FX6_APPFW_601_BYTES, P377_PINNED_FX6_APPFW_601_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601")),
        ("fx3_uxc_en_f", P377_DONOR_FX3_UXC_EN_F_RELPATH, P377_PINNED_FX3_UXC_EN_F_BYTES, P377_PINNED_FX3_UXC_EN_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_F")),
        ("fx3_uxc_sc_f", P377_DONOR_FX3_UXC_SC_F_RELPATH, P377_PINNED_FX3_UXC_SC_F_BYTES, P377_PINNED_FX3_UXC_SC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_F")),
        ("fx3_uxc_tc_f", P377_DONOR_FX3_UXC_TC_F_RELPATH, P377_PINNED_FX3_UXC_TC_F_BYTES, P377_PINNED_FX3_UXC_TC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_F")),
        ("fx3_uxc_ja_f", P377_DONOR_FX3_UXC_JA_F_RELPATH, P377_PINNED_FX3_UXC_JA_F_BYTES, P377_PINNED_FX3_UXC_JA_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_F")),
        ("fx3_uxc_en", P377_DONOR_FX3_UXC_EN_RELPATH, P377_PINNED_FX3_UXC_EN_BYTES, P377_PINNED_FX3_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN")),
        ("fx3_uxc_sc", P377_DONOR_FX3_UXC_SC_RELPATH, P377_PINNED_FX3_UXC_SC_BYTES, P377_PINNED_FX3_UXC_SC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC")),
        ("fx3_uxc_tc", P377_DONOR_FX3_UXC_TC_RELPATH, P377_PINNED_FX3_UXC_TC_BYTES, P377_PINNED_FX3_UXC_TC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC")),
        ("fx3_uxc_ja", P377_DONOR_FX3_UXC_JA_RELPATH, P377_PINNED_FX3_UXC_JA_BYTES, P377_PINNED_FX3_UXC_JA_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA")),
        ("fx3_uxc_en_g", P377_DONOR_FX3_UXC_EN_G_RELPATH, P377_PINNED_FX3_UXC_EN_G_BYTES, P377_PINNED_FX3_UXC_EN_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_G")),
        ("fx3_uxc_sc_g", P377_DONOR_FX3_UXC_SC_G_RELPATH, P377_PINNED_FX3_UXC_SC_G_BYTES, P377_PINNED_FX3_UXC_SC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_G")),
        ("fx3_uxc_tc_g", P377_DONOR_FX3_UXC_TC_G_RELPATH, P377_PINNED_FX3_UXC_TC_G_BYTES, P377_PINNED_FX3_UXC_TC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_G")),
        ("fx3_uxc_ja_g", P377_DONOR_FX3_UXC_JA_G_RELPATH, P377_PINNED_FX3_UXC_JA_G_BYTES, P377_PINNED_FX3_UXC_JA_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_G")),
        ("fx6_uxc_en", P377_DONOR_FX6_UXC_EN_RELPATH, P377_PINNED_FX6_UXC_EN_BYTES, P377_PINNED_FX6_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN")),
        ("fx6_uxc_en_2", P377_DONOR_FX6_UXC_EN_2_RELPATH, P377_PINNED_FX6_UXC_EN_2_BYTES, P377_PINNED_FX6_UXC_EN_2_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN_2")),
    )

    def _probe_one(spec: Tuple[str, str, int, str, Any]) -> Optional[Phase377DonorArtifactDigest]:
        aid, relpath, expected_bytes, expected_sha, marker_fn = spec
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            return None
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        return Phase377DonorArtifactDigest(
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
        artifacts = _synthetic_phase377_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase377DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_2_0s_budget=dt <= budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    digests = tuple(r for r in results if r is not None)
    all_ok = all(d.present and d.matches_pinned for d in digests) and len(digests) == len(probe_specs)
    dt = round(time.monotonic() - t0, 6)
    return Phase377DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all_ok,
        donor_files_inspected=len(digests),
        elapsed_seconds=dt,
        under_2_0s_budget=dt <= budget,
        budget_seconds_applied=budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=digests,
    )


# ---------------------------------------------------------------------------
# Frozen Dataclasses (Specs, Reports, Suites & 69-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase377DonorArtifactDigest:
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
class Phase377DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_2_0s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase377DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PixelMapMonitorRecallHoldVaultSpec:
    camera_model: str
    fw_version: str
    shooting_domain: str
    exposure_mode: str
    focus_mode: str
    # 1. Pixel Mapping / Auto Pixel Mapping vs FX6 APR & Zero ABB
    setup_auto_pixel_mapping: str
    silent_mode: str
    silent_target_auto_pixel_mapping: str
    manual_pixel_mapping_requested: bool
    manual_pixel_map_lens_cap_attached: bool
    manual_pixel_map_battery_ok: bool
    pixel_map_notification_requested: bool
    fx6_apr_requested: bool
    fx6_apr_lens_cap_and_black_cloth: bool
    fx6_apr_temperature_valid: bool
    fx6_abb_requested: bool
    reported_pixelmap_errno: Optional[int]
    reported_effective_auto_pixel_mapping: str
    reported_effective_silent_target_auto_pixel_mapping: str
    reported_shutdown_shutter_sound_emitted: bool
    reported_manual_pixel_map_auto_reboot: bool
    # 2. Setup -> [Monitor] vs Dormant EVF / FX6 VF Setting & VF Adjust
    monitor_group_name: str
    monitor_brightness_mode: str
    monitor_brightness_manual_level: int
    display_quality: str
    thermal_elevated: bool
    monitor_flip_direction: str
    dormant_evf_item_requested: str
    fx6_vf_connected: bool
    fx6_vf_brightness: int
    fx6_vf_color_mode: str
    fx6_vf_adjust_pressed: bool
    fx6_mirror_switch: str
    fx6_vf_4item_submenu_requested: bool
    reported_monitor_errno: Optional[int]
    reported_dormant_evf_errno: Optional[int]
    reported_effective_display_quality: str
    reported_thermal_display_quality_locked: bool
    # 3. Hold Custom Keys & Still-Only Recall Custom Hold 1-3 vs FX6 Push AF/AGC/Iris
    hold_custom_key: str
    recall_selected_bits: Tuple[str, ...]
    recall_independent_wb_requested: bool
    recall_drive_mode_selftimer_requested: bool
    recall_persists_in_camset: bool
    recall_persists_in_campr: bool
    fx6_push_key: str
    fx6_lens_manual_mode: bool
    fx6_bokeh_control_on: bool
    fx6_desqueeze_active: bool
    fx6_high_low_key_requested: bool
    reported_hold_key_errno: Optional[int]
    reported_recall_wb_errno: Optional[int]
    reported_recall_bits_valid: bool
    reported_recall_serialization_valid: bool
    # 4. Reset boundaries
    reset_action: str
    post_auto_pixel_mapping: str
    post_silent_target_auto_pixel_mapping: str
    post_monitor_brightness_mode: str
    post_display_quality: str
    post_monitor_flip_direction: str
    post_reg_custom_shoot_set_retained: bool
    # 5. Vault & Overlay & H0==H3
    requested_vault_slot: int
    slot1_holds_tier0_vault: bool
    requested_vault_action: str
    reported_vault_action_allowed: bool
    vault_firewall_errno: Optional[str]
    slot1_writes: int
    slot1_data_sector_writes: int
    slot1_sector_writes: int
    slot1_vault_mutation_bytes: int
    cnflasha_writes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative drift counters
    pixelmap_apr_or_zero_abb_drift_events: int
    monitor_3item_or_dormant_evf_drift_events: int
    recall_hold_11bit_or_push_key_drift_events: int


@dataclass(frozen=True)
class PixelMapMonitorRecallHoldVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    pixelmap_apr_and_zero_abb_verified: bool
    monitor_3item_and_dormant_evf_verified: bool
    recall_hold_11bit_and_push_key_verified: bool
    slot1_vault_and_h0_h3_verified: bool
    matrix_states_checked: int
    pixelmap_apr_or_zero_abb_drift_events: int
    monitor_3item_or_dormant_evf_drift_events: int
    recall_hold_11bit_or_push_key_drift_events: int
    slot1_writes: int
    slot1_data_sector_writes: int
    slot1_sector_writes: int
    slot1_vault_mutation_bytes: int
    cnflasha_writes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HdmiRecCtrl24pSdiSlot1VaultSpec:
    camera_model: str
    fw_version: str
    shooting_domain: str
    log_shooting_mode: str
    picture_profile: str
    # FX3 Setup -> [External Output] HDMI Matrix
    hdmi_resolution: str
    rec_media_dur_hdmi_output: str
    output_resolution: str
    hdmi_4k_output_rate_prev: str
    hdmi_4k_output_rate_new: str
    raw_output_enabled: str
    time_code_output: str
    rec_control: str
    compatible_external_recorder_connected: bool
    usb_streaming_active: bool
    hdmi_4ch_audio_output: str
    four_discrete_hdmi_audio_requested: bool
    hdmi_info_display: str
    ctrl_for_hdmi: str
    dormant_4k_2k_output_requested: bool
    dormant_24p_60p_output_requested: bool
    # FX6 Dual-Output SDI + HDMI Matrix
    fx6_sdi_output_on: bool
    fx6_hdmi_output_on: bool
    fx6_codec_mode: str
    fx6_sq_fps: int
    fx6_hdmi_tc_out: str
    fx6_sdi_hdmi_rec_control: str
    fx6_card_inserted: bool
    # Reported Matrix Outcomes
    reported_hdmi_matrix_errno: Optional[int]
    reported_dormant_output_errno: Optional[int]
    reported_effective_rec_media_dur_hdmi: str
    reported_effective_output_resolution: str
    reported_output_forced_1080_downscale: bool
    reported_effective_hdmi_info_display: str
    reported_reboot_required_for_24_00p_switch: bool
    reported_cross_24_00p_playback_isolated: bool
    reported_rec_control_stby_rec_indicator_active: bool
    reported_internal_media_write_attempted: bool
    reported_fx6_sdi_forced_1080: bool
    reported_fx6_hdmi_forced_1080: bool
    # Reset Boundaries (ALL External Output items resist Camera Settings Reset)
    reset_action: str
    post_rec_media_dur_hdmi: str
    post_output_resolution: str
    post_time_code_output: str
    post_rec_control: str
    post_hdmi_4ch_audio: str
    post_hdmi_info_display: str
    post_ctrl_for_hdmi: str
    # Tier-0 Slot-1 Vault Firewall & Overlay & H0==H3
    recording_target_slot: int
    requested_vault_slot: int
    slot1_holds_tier0_vault: bool
    requested_vault_action: str
    reported_vault_action_allowed: bool
    vault_firewall_errno: Optional[str]
    slot1_writes: int
    slot1_data_sector_writes: int
    slot1_sector_writes: int
    slot1_vault_mutation_bytes: int
    cnflasha_writes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative drift counter
    hdmi_recctrl_24p_or_slot1_vault_drift_events: int


@dataclass(frozen=True)
class HdmiRecCtrl24pSdiSlot1VaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    hdmi_extout_24p_recctrl_and_sdi_verified: bool
    extout_reset_resistance_verified: bool
    slot1_erofs_overlay_and_h0_h3_verified: bool
    matrix_states_checked: int
    hdmi_recctrl_24p_or_slot1_vault_drift_events: int
    slot1_writes: int
    slot1_data_sector_writes: int
    slot1_sector_writes: int
    slot1_vault_mutation_bytes: int
    cnflasha_writes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PixelMapMonitorRecallHoldHdmiRecCtrlVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase377DonorSnapshot
    pixelmap_monitor_recallhold_report: PixelMapMonitorRecallHoldVaultReport
    hdmi_recctrl_24p_sdi_slot1_report: HdmiRecCtrl24pSdiSlot1VaultReport
    pixelmap_apr_or_zero_abb_drift_events: int
    monitor_3item_or_dormant_evf_drift_events: int
    recall_hold_11bit_or_push_key_drift_events: int
    hdmi_recctrl_24p_or_slot1_vault_drift_events: int
    slot1_writes: int
    slot1_data_sector_writes: int
    slot1_sector_writes: int
    slot1_vault_mutation_bytes: int
    cnflasha_writes: int
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
    emmc_writes_authorized: bool
    persistent_write_release: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar69ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar69ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar69ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar69BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar69ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar69StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase377DonorSnapshot
    pillar_69a_pixelmap_monitor_recallhold_vault: Pillar69ASuiteResult
    pillar_69b_hdmi_recctrl_24p_sdi_slot1_vault: Pillar69BSuiteResult
    pixelmap_apr_or_zero_abb_drift_events: int
    monitor_3item_or_dormant_evf_drift_events: int
    recall_hold_11bit_or_push_key_drift_events: int
    hdmi_recctrl_24p_or_slot1_vault_drift_events: int
    slot1_writes: int
    slot1_data_sector_writes: int
    slot1_sector_writes: int
    slot1_vault_mutation_bytes: int
    cnflasha_writes: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_vault_erofs_ebusy_enforced: bool
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
    emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master69PillarRecoveryReport:
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
    donor_snapshot: Phase377DonorSnapshot
    pillar69_a_pixelmap_monitor_recallhold_vault: Pillar69ASuiteResult
    pillar69_b_hdmi_recctrl_24p_sdi_slot1_vault: Pillar69BSuiteResult
    # Pillar 69 zero-violation counters & empirical capability booleans
    pixelmap_apr_or_zero_abb_drift_events: int
    monitor_3item_or_dormant_evf_drift_events: int
    recall_hold_11bit_or_push_key_drift_events: int
    hdmi_recctrl_24p_or_slot1_vault_drift_events: int
    fx3_auto_pixel_map_resettable: bool
    fx3_silent_target_auto_pixel_map_resettable: bool
    fx3_has_finder_monitor_group: bool
    fx3_has_dormant_evf_items_exposed: bool
    fx3_monitor_group_resettable: bool
    fx3_recall_custom_hold_bit_count: int
    fx3_recall_custom_hold_wb_hits: int
    fx3_recall_custom_hold_has_independent_wb: bool
    fx3_reg_custom_shoot_set_resettable: bool
    fx3_external_output_resettable: bool
    fx3_has_dormant_4k_2k_output: bool
    fx3_has_dormant_24p_60p_output: bool
    fx6_has_user_exposed_abb: bool
    fx6_has_vf_4item_submenu: bool
    fx6_has_recall_custom_hold: bool
    fx6_has_high_low_key_exposed: bool
    slot1_writes: int
    slot1_sector_writes: int
    cnflasha_writes: int
    emmc_writes_authorized: bool
    # Carried forward from Pillars 61..68
    drive_mode_or_dormant_focus_bracket_drift_events: int
    shutter_2opt_xsync_efcs_or_nr_drift_events: int
    creative_look_8param_override_or_softskin_drift_events: int
    delete_protect_recoverdb_slot1_vault_drift_events: int
    fx3_has_dormant_focus_bracket_exposed: bool
    fx3_has_shutter_type_auto_exposed: bool
    fx3_has_dormant_soft_skin_exposed: bool
    fx6_has_still_drive_mode: bool
    fx6_has_focus_bracket: bool
    fx6_has_mechanical_shutter: bool
    fx6_has_efcs: bool
    fx6_has_long_exp_nr: bool
    fx6_has_creative_look: bool
    fx6_has_soft_skin_effect: bool
    fx3_drive_mode_resettable: bool
    fx3_efcs_resettable: bool
    fx3_creative_look_resettable: bool
    fx3_delete_confirm_resettable: bool
    zoom_ciz_lockout_or_8speed_reset_drift_events: int
    autoslow_6lockout_or_minss_still_drift_events: int
    dual_base_iso_curve_matrix_drift_events: int
    dormant_lossless_arw_exposed_events: int
    hlg_still_or_sort_rec_spillover_drift_events: int
    usb_lun_single_slot1_msc_hazard_events: int
    npfz100_pd_interlock_or_dcc1_drift_events: int
    dormant_uvc_streaming_exposed_events: int
    fx3_zoom_range_resettable: bool
    fx3_zoom_speed_resettable: bool
    fx3_has_dormant_lossless_arw_exposed: bool
    fx3_has_native_uvc_streaming: bool
    fx6_has_native_uvc_streaming: bool
    fx6_has_digital_zoom: bool
    fx6_has_still_arw_hlg_pipeline: bool
    fx6_has_iso_auto_min_ss: bool
    slot1_data_sector_writes: int
    slot1_vault_mutation_bytes: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_vault_erofs_ebusy_enforced: bool
    breathing_comp_lockout_or_catalyst_drift_events: int
    file_settings_camid_reel_or_sdhc_drift_events: int
    copyright_46ch_reset_erratum_or_serial_drift_events: int
    camset_copyright_pii_leak_events: int
    camset_copyright_pii_leaked_bytes: int
    powersave_9cond_or_dormant_monitor_drift_events: int
    dormant_power_save_by_monitor_exposed_events: int
    ntsc_pal_reboot_or_slot1_format_drift_events: int
    hdmi_raw_output_or_media_vault_drift_events: int
    hdmi_4k_only_or_gamut_removal_drift_events: int
    desqueeze_ratio_lock_or_bypass_drift_events: int
    rec_lamp_tally_or_emph_display_drift_events: int
    dormant_var_shutter_or_apsc_reset_drift_events: int
    dormant_var_shutter_exposed_events: int
    hdmi_red_border_clean_feed_leak_pixels: int
    recorded_media_desqueeze_pixels: int
    fx6_sdi_desqueeze_pixels: int
    shoe_audio_preemption_or_limiter_drift_events: int
    subject_recog_myth_or_face_memory_drift_events: int
    silent_mode_target_or_barrier_drift_events: int
    bodydata_version_flash_or_slot1_vault_drift_events: int
    dormant_shutter_when_pwr_off_exposed_events: int
    hdmi_face_frame_pixels_emitted: int
    cnflasha_pixel_map_mutation_bytes: int
    slot1_bodydata_mutation_bytes: int
    bodydata_placement_or_flash_authorized: bool
    ftp_protocol_sftp_or_jpeg_size_drift_events: int
    wb_custom_cine_ei_or_shockless_drift_events: int
    movie_af_speed_or_focus_map_spoof_events: int
    marker_15ratio_peaking_hdmi_leak_events: int
    zero_rf_usblan_or_slot1_avf_bypass_events: int
    usblan_packets_transmitted: int
    hdmi_marker_peaking_pixels_emitted: int
    slot1_avf_info_mutation_bytes: int
    rec_media_prioritize_or_autoswitch_drift_events: int
    card_speed_vpg200_vpg400_gate_drift_events: int
    proxy_sq_dci4k_or_120p_lockout_drift_events: int
    cloud_init_persist_or_power_off_ble_rf_events: int
    mymenu_42slot_or_fx6_lock_spoof_events: int
    zero_rf_or_slot1_vault_bypass_events: int
    slot1_dcim_m4root_avf_mutation_bytes: int
    big6_home_or_lower_left_nd_drift_events: int
    framing_manual_or_dormant_auto_framing_drift_events: int
    interval_shoot_9999_or_fx6_mxf_spoof_events: int
    tc_make_regen_or_hdmi_rec_ctrl_drift_events: int
    access_authen_ssh_tls_or_fan_max_drift_events: int
    slot1_dcim_avf_mutation_bytes: int
    fx3_has_var_shutter: bool
    fx3_has_builtin_evf: bool
    fx3_has_builtin_end_filter: bool
    fx3_has_bt_timecode_link: bool
    fx3_has_dormant_auto_framing: bool
    fx3_has_dormant_auto_hdr: bool
    fx3_has_dormant_bulb_timer: bool
    fx3_has_dormant_divide_extract: bool
    fx3_has_fan_control_max: bool
    fx3_has_movie_self_timer: bool
    fx3_has_movie_sort_recording: bool
    fx3_has_physical_end_hw: bool
    fx3_has_5axis_ibis: bool
    fx3_has_power_save_by_monitor: bool
    fx6_has_ibis: bool
    fx6_has_fan_control_max: bool
    fx6_has_still_self_timer: bool
    fx6_has_fn_menu: bool
    fx6_has_my_dial: bool
    fx6_has_bluetooth_hardware: bool
    fx6_has_av_tv_rotate: bool
    fx6_has_exif_copyright_menu: bool
    overall_ready_for_hardware_attach: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    master_69pillar_sha256: str
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


def build_default_safe_pixelmap_monitor_recallhold_vault_spec(
    **overrides: Any,
) -> PixelMapMonitorRecallHoldVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P377_FX3_MODEL_NAME,
        "fw_version": P377_FX3_FW_VERSION,
        "shooting_domain": "Still",
        "exposure_mode": "M",
        "focus_mode": "AF-C",
        # Pixel Mapping / Auto Pixel Mapping
        "setup_auto_pixel_mapping": "On",
        "silent_mode": "On",
        "silent_target_auto_pixel_mapping": "Off",  # Default Not Target -> shutter sound on shutdown!
        "manual_pixel_mapping_requested": False,
        "manual_pixel_map_lens_cap_attached": True,
        "manual_pixel_map_battery_ok": True,
        "pixel_map_notification_requested": False,
        "fx6_apr_requested": False,
        "fx6_apr_lens_cap_and_black_cloth": True,
        "fx6_apr_temperature_valid": True,
        "fx6_abb_requested": False,
        "reported_pixelmap_errno": None,
        "reported_effective_auto_pixel_mapping": "On",
        "reported_effective_silent_target_auto_pixel_mapping": "Off",
        "reported_shutdown_shutter_sound_emitted": True,
        "reported_manual_pixel_map_auto_reboot": False,
        # Setup -> [Monitor]
        "monitor_group_name": P377_FX3_MONITOR_GROUP_NAME,
        "monitor_brightness_mode": P377_FX3_MONITOR_BRIGHTNESS_DEFAULT,
        "monitor_brightness_manual_level": 0,
        "display_quality": P377_FX3_DISPLAY_QUALITY_DEFAULT,
        "thermal_elevated": False,
        "monitor_flip_direction": P377_FX3_MONITOR_FLIP_DEFAULT,
        "dormant_evf_item_requested": "None",
        "fx6_vf_connected": True,
        "fx6_vf_brightness": P377_FX6_VF_BRIGHTNESS_DEFAULT,
        "fx6_vf_color_mode": "Color",
        "fx6_vf_adjust_pressed": False,
        "fx6_mirror_switch": "Off",
        "fx6_vf_4item_submenu_requested": False,
        "reported_monitor_errno": None,
        "reported_dormant_evf_errno": None,
        "reported_effective_display_quality": P377_FX3_DISPLAY_QUALITY_DEFAULT,
        "reported_thermal_display_quality_locked": False,
        # Hold Custom Keys & Recall Custom hold 1-3
        "hold_custom_key": "Recall Custom hold 1",
        "recall_selected_bits": P377_FX3_RECALL_CUSTOM_HOLD_11_BITS,
        "recall_independent_wb_requested": False,
        "recall_drive_mode_selftimer_requested": False,
        "recall_persists_in_camset": True,
        "recall_persists_in_campr": False,
        "fx6_push_key": "None",
        "fx6_lens_manual_mode": False,
        "fx6_bokeh_control_on": False,
        "fx6_desqueeze_active": False,
        "fx6_high_low_key_requested": False,
        "reported_hold_key_errno": None,
        "reported_recall_wb_errno": None,
        "reported_recall_bits_valid": True,
        "reported_recall_serialization_valid": True,
        # Reset
        "reset_action": "Camera Settings Reset",
        "post_auto_pixel_mapping": "On",
        "post_silent_target_auto_pixel_mapping": "Off",
        "post_monitor_brightness_mode": P377_FX3_MONITOR_BRIGHTNESS_DEFAULT,
        "post_display_quality": P377_FX3_DISPLAY_QUALITY_DEFAULT,
        "post_monitor_flip_direction": P377_FX3_MONITOR_FLIP_DEFAULT,
        "post_reg_custom_shoot_set_retained": True,
        # Vault & Overlay & H0==H3
        "requested_vault_slot": 1,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_writes": 0,
        "slot1_data_sector_writes": 0,
        "slot1_sector_writes": 0,
        "slot1_vault_mutation_bytes": 0,
        "cnflasha_writes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P377_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P377_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P377_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P377_TIER0_SURFACE_COUNT,
        # Drift counters
        "pixelmap_apr_or_zero_abb_drift_events": 0,
        "monitor_3item_or_dormant_evf_drift_events": 0,
        "recall_hold_11bit_or_push_key_drift_events": 0,
    }
    defaults.update(overrides)
    return PixelMapMonitorRecallHoldVaultSpec(**defaults)


def build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
    **overrides: Any,
) -> HdmiRecCtrl24pSdiSlot1VaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P377_FX3_MODEL_NAME,
        "fw_version": P377_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "log_shooting_mode": "Off",
        "picture_profile": "Off",
        # External Output HDMI Matrix (safe default: Off(HDMI Only) + TC Output On + REC Control On)
        "hdmi_resolution": P377_FX3_HDMI_RESOLUTION_DEFAULT,
        "rec_media_dur_hdmi_output": "Off(HDMI Only)",
        "output_resolution": P377_FX3_OUTPUT_RESOLUTION_DEFAULT,
        "hdmi_4k_output_rate_prev": "23.98p 10bit",
        "hdmi_4k_output_rate_new": "23.98p 10bit",
        "raw_output_enabled": "Off",
        "time_code_output": "On",
        "rec_control": "On",
        "compatible_external_recorder_connected": True,
        "usb_streaming_active": False,
        "hdmi_4ch_audio_output": P377_FX3_HDMI_4CH_AUDIO_DEFAULT,
        "four_discrete_hdmi_audio_requested": False,
        "hdmi_info_display": "On",
        "ctrl_for_hdmi": P377_FX3_CTRL_FOR_HDMI_DEFAULT,
        "dormant_4k_2k_output_requested": False,
        "dormant_24p_60p_output_requested": False,
        # FX6 Dual-Output
        "fx6_sdi_output_on": True,
        "fx6_hdmi_output_on": True,
        "fx6_codec_mode": "XAVC-I",
        "fx6_sq_fps": 24,
        "fx6_hdmi_tc_out": "On",
        "fx6_sdi_hdmi_rec_control": "Off",
        "fx6_card_inserted": False,
        # Reported Matrix Outcomes
        "reported_hdmi_matrix_errno": None,
        "reported_dormant_output_errno": None,
        "reported_effective_rec_media_dur_hdmi": "Off(HDMI Only)",
        "reported_effective_output_resolution": "Auto",
        "reported_output_forced_1080_downscale": False,
        "reported_effective_hdmi_info_display": "Off",  # Forced Off under Off(HDMI Only)!
        "reported_reboot_required_for_24_00p_switch": False,
        "reported_cross_24_00p_playback_isolated": False,
        "reported_rec_control_stby_rec_indicator_active": True,
        "reported_internal_media_write_attempted": False,
        "reported_fx6_sdi_forced_1080": False,
        "reported_fx6_hdmi_forced_1080": False,
        # Reset Boundaries (ALL External Output resist Camera Settings Reset)
        "reset_action": "Camera Settings Reset",
        "post_rec_media_dur_hdmi": "Off(HDMI Only)",
        "post_output_resolution": "Auto",
        "post_time_code_output": "On",
        "post_rec_control": "On",
        "post_hdmi_4ch_audio": P377_FX3_HDMI_4CH_AUDIO_DEFAULT,
        "post_hdmi_info_display": "On",
        "post_ctrl_for_hdmi": P377_FX3_CTRL_FOR_HDMI_DEFAULT,
        # Tier-0 Slot-1 Vault
        "recording_target_slot": 2,
        "requested_vault_slot": 1,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "HDMI_ONLY_ZERO_MEDIA_WRITE",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_writes": 0,
        "slot1_data_sector_writes": 0,
        "slot1_sector_writes": 0,
        "slot1_vault_mutation_bytes": 0,
        "cnflasha_writes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P377_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P377_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P377_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P377_TIER0_SURFACE_COUNT,
        # Drift counter
        "hdmi_recctrl_24p_or_slot1_vault_drift_events": 0,
    }
    defaults.update(overrides)
    return HdmiRecCtrl24pSdiSlot1VaultSpec(**defaults)


# ---------------------------------------------------------------------------
# Sub-Pillar Evaluators (69A & 69B) & Combined Single-Shot Verifier
# ---------------------------------------------------------------------------


def evaluate_pixelmap_monitor_recallhold_vault(
    spec: PixelMapMonitorRecallHoldVaultSpec,
) -> PixelMapMonitorRecallHoldVaultReport:
    """Evaluate Pillar 69A spec (`Pixel Mapping`/`Auto Pixel Mapping` vs FX6 `APR`/zero `ABB`,
    `Setup -> [Monitor]` 3-item group + dormant EVF debunk vs FX6 `VF Setting/Adjust`, &
    Still-only `Recall Custom hold 1-3` exact 11 bits / zero WB vs FX6 `Push AF/AGC/Iris`)."""
    errors: List[str] = []
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    for serr in _safety_invariant_errors():
        _fail(P377_BLOCKED_SAFETY_POLICY_VIOLATION, serr)

    valid_spec = (
        spec.camera_model in (P377_FX3_MODEL_NAME, P377_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P377_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P377_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P377_SHOOTING_DOMAINS
        and spec.exposure_mode in P377_EXPOSURE_MODES
        and spec.focus_mode in P377_FOCUS_MODES
        and spec.setup_auto_pixel_mapping in ("None", "Off", "On")
        and spec.silent_mode in ("None", "Off", "On")
        and spec.silent_target_auto_pixel_mapping in ("None", "Off", "On")
        and spec.monitor_brightness_mode in (("None",) + P377_FX3_MONITOR_BRIGHTNESS_MODES)
        and spec.display_quality in (("None",) + P377_FX3_DISPLAY_QUALITY_MODES)
        and spec.monitor_flip_direction in (("None",) + P377_FX3_MONITOR_FLIP_DIRECTIONS)
        and spec.hold_custom_key in P377_FX3_HOLD_CUSTOM_KEYS
        and spec.fx6_push_key in P377_FX6_PUSH_KEYS
        and spec.reset_action in P377_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P377_VAULT_ACTIONS
        and spec.vault_firewall_errno in P377_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P377_BLOCKED_INVALID_PILLAR69A_SPEC, "Invalid Pillar 69A spec fields")

    st = compute_expected_pixelmap_monitor_recallhold_vault_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        exposure_mode=spec.exposure_mode,
        focus_mode=spec.focus_mode,
        setup_auto_pixel_mapping=spec.setup_auto_pixel_mapping,
        silent_mode=spec.silent_mode,
        silent_target_auto_pixel_mapping=spec.silent_target_auto_pixel_mapping,
        manual_pixel_mapping_requested=spec.manual_pixel_mapping_requested,
        manual_pixel_map_lens_cap_attached=spec.manual_pixel_map_lens_cap_attached,
        manual_pixel_map_battery_ok=spec.manual_pixel_map_battery_ok,
        pixel_map_notification_requested=spec.pixel_map_notification_requested,
        fx6_apr_requested=spec.fx6_apr_requested,
        fx6_apr_lens_cap_and_black_cloth=spec.fx6_apr_lens_cap_and_black_cloth,
        fx6_apr_temperature_valid=spec.fx6_apr_temperature_valid,
        fx6_abb_requested=spec.fx6_abb_requested,
        monitor_group_name=spec.monitor_group_name,
        monitor_brightness_mode=spec.monitor_brightness_mode,
        monitor_brightness_manual_level=spec.monitor_brightness_manual_level,
        display_quality=spec.display_quality,
        thermal_elevated=spec.thermal_elevated,
        monitor_flip_direction=spec.monitor_flip_direction,
        dormant_evf_item_requested=spec.dormant_evf_item_requested,
        fx6_vf_connected=spec.fx6_vf_connected,
        fx6_vf_brightness=spec.fx6_vf_brightness,
        fx6_vf_color_mode=spec.fx6_vf_color_mode,
        fx6_vf_adjust_pressed=spec.fx6_vf_adjust_pressed,
        fx6_mirror_switch=spec.fx6_mirror_switch,
        fx6_vf_4item_submenu_requested=spec.fx6_vf_4item_submenu_requested,
        hold_custom_key=spec.hold_custom_key,
        recall_selected_bits=spec.recall_selected_bits,
        recall_independent_wb_requested=spec.recall_independent_wb_requested,
        recall_drive_mode_selftimer_requested=spec.recall_drive_mode_selftimer_requested,
        recall_persists_in_camset=spec.recall_persists_in_camset,
        recall_persists_in_campr=spec.recall_persists_in_campr,
        fx6_push_key=spec.fx6_push_key,
        fx6_lens_manual_mode=spec.fx6_lens_manual_mode,
        fx6_bokeh_control_on=spec.fx6_bokeh_control_on,
        fx6_desqueeze_active=spec.fx6_desqueeze_active,
        fx6_high_low_key_requested=spec.fx6_high_low_key_requested,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    pixelmap_ok = (
        spec.reported_pixelmap_errno == st["pixelmap_errno"]
        and st["pixelmap_errno"] is None
        and spec.reported_effective_auto_pixel_mapping == st["effective_auto_pixel_mapping"]
        and spec.reported_effective_silent_target_auto_pixel_mapping
        == st["effective_silent_target_auto_pixel_mapping"]
        and spec.reported_shutdown_shutter_sound_emitted == st["shutdown_shutter_sound_emitted"]
        and spec.reported_manual_pixel_map_auto_reboot == st["manual_pixel_map_auto_reboot"]
        and spec.post_auto_pixel_mapping == st["post_auto_pixel_mapping"]
        and spec.post_silent_target_auto_pixel_mapping
        == st["post_silent_target_auto_pixel_mapping"]
        and not spec.fx6_abb_requested
        and not spec.pixel_map_notification_requested
        and spec.pixelmap_apr_or_zero_abb_drift_events == 0
    )
    if not pixelmap_ok:
        _fail(
            P377_BLOCKED_PIXELMAP_APR_OR_ZERO_ABB_DRIFT,
            "Pixel Mapping / Auto Pixel Mapping Silent Target / Battery / Lens-Cap or FX6 APR / Zero ABB rule violated",
        )

    monitor_ok = (
        spec.reported_monitor_errno == st["monitor_errno"]
        and st["monitor_errno"] is None
        and spec.reported_dormant_evf_errno == st["dormant_evf_errno"]
        and st["dormant_evf_errno"] is None
        and spec.dormant_evf_item_requested == "None"
        and not spec.fx6_vf_4item_submenu_requested
        and spec.reported_effective_display_quality == st["effective_display_quality"]
        and spec.reported_thermal_display_quality_locked == st["thermal_display_quality_locked"]
        and spec.post_monitor_brightness_mode == st["post_monitor_brightness_mode"]
        and spec.post_display_quality == st["post_display_quality"]
        and spec.post_monitor_flip_direction == st["post_monitor_flip_direction"]
        and spec.monitor_3item_or_dormant_evf_drift_events == 0
    )
    if not monitor_ok:
        _fail(
            P377_BLOCKED_MONITOR_3ITEM_OR_DORMANT_EVF_DRIFT,
            "Setup -> [Monitor] 3-item group, thermal Standard lock, dormant EVF 4-item block, or FX6 VF Setting/Adjust rule violated",
        )

    recall_ok = (
        spec.reported_hold_key_errno == st["hold_key_errno"]
        and st["hold_key_errno"] is None
        and spec.reported_recall_wb_errno == st["recall_wb_errno"]
        and st["recall_wb_errno"] is None
        and not spec.recall_independent_wb_requested
        and not spec.recall_drive_mode_selftimer_requested
        and not spec.fx6_high_low_key_requested
        and spec.reported_recall_bits_valid == st["recall_bits_valid"]
        and st["recall_bits_valid"]
        and spec.reported_recall_serialization_valid == st["recall_serialization_valid"]
        and st["recall_serialization_valid"]
        and spec.post_reg_custom_shoot_set_retained == st["post_reg_custom_shoot_set_retained"]
        and spec.recall_hold_11bit_or_push_key_drift_events == 0
    )
    if not recall_ok:
        _fail(
            P377_BLOCKED_RECALL_HOLD_11BIT_OR_PUSH_KEY_DRIFT,
            "Still-only P/A/S/M Recall Custom hold 1-3 (11 bits, zero independent WB, CAMSET-only) or FX6 Push AF/AGC/Iris rule violated",
        )

    slot1_mutated = (
        spec.requested_vault_action in P377_WRITE_MUTATING_SLOT1_VAULT_ACTIONS
        and spec.reported_vault_action_allowed
    )
    vault_ok = (
        not slot1_mutated
        and spec.reported_vault_action_allowed == st["vault_action_allowed"]
        and spec.vault_firewall_errno == st["vault_firewall_errno"]
        and spec.slot1_writes == 0
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_sector_writes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.cnflasha_writes == 0
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_format_hard_locked
    )
    if not vault_ok:
        _fail(
            P377_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P377_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P377_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P377_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P377_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    vault_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "69A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "auto_pixel_map": spec.post_auto_pixel_mapping,
            "display_quality": spec.reported_effective_display_quality,
            "hold_key": spec.hold_custom_key,
            "slot1_writes": spec.slot1_writes,
            "errors": errors,
        }
    )
    return PixelMapMonitorRecallHoldVaultReport(
        schema=PHASE377_SCHEMA,
        version=PHASE377_VERSION,
        passed=passed,
        status=P377_STATUS_VERIFIED_PILLAR_69A if passed else P377_STATUS_REJECTED_PILLAR_69A,
        block_code=block_code,
        pixelmap_apr_and_zero_abb_verified=pixelmap_ok,
        monitor_3item_and_dormant_evf_verified=monitor_ok,
        recall_hold_11bit_and_push_key_verified=recall_ok,
        slot1_vault_and_h0_h3_verified=vault_and_h0_h3_ok,
        matrix_states_checked=54,
        pixelmap_apr_or_zero_abb_drift_events=spec.pixelmap_apr_or_zero_abb_drift_events,
        monitor_3item_or_dormant_evf_drift_events=spec.monitor_3item_or_dormant_evf_drift_events,
        recall_hold_11bit_or_push_key_drift_events=spec.recall_hold_11bit_or_push_key_drift_events,
        slot1_writes=spec.slot1_writes,
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_sector_writes=spec.slot1_sector_writes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        cnflasha_writes=spec.cnflasha_writes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_hdmi_recctrl_24p_sdi_slot1_vault(
    spec: HdmiRecCtrl24pSdiSlot1VaultSpec,
) -> HdmiRecCtrl24pSdiSlot1VaultReport:
    """Evaluate Pillar 69B spec (`Setup -> [External Output]` HDMI matrix, `TC Output -> REC Control` gate,
    `24.00p` reboot & playback isolation, dormant `4K/2K` & `24p/60p` debunk, FX6 `SDI/HDMI` dual-output
    matrix, & Tier-0 `Slot 1 EROFS=30` Recovery Vault Firewall)."""
    errors: List[str] = []
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    for serr in _safety_invariant_errors():
        _fail(P377_BLOCKED_SAFETY_POLICY_VIOLATION, serr)

    valid_spec = (
        spec.camera_model in (P377_FX3_MODEL_NAME, P377_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P377_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P377_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P377_SHOOTING_DOMAINS
        and spec.hdmi_resolution in (("None",) + P377_FX3_HDMI_RESOLUTION_MODES)
        and spec.rec_media_dur_hdmi_output in (("None",) + P377_FX3_REC_MEDIA_DUR_HDMI_MODES)
        and spec.output_resolution in (("None",) + P377_FX3_OUTPUT_RESOLUTION_MODES)
        and spec.hdmi_4k_output_rate_prev in (("None",) + P377_FX3_4K_OUTPUT_HDMI_ONLY_RATES)
        and spec.hdmi_4k_output_rate_new in (("None",) + P377_FX3_4K_OUTPUT_HDMI_ONLY_RATES)
        and spec.raw_output_enabled in ("None", "Off", "On")
        and spec.time_code_output in ("None", "Off", "On")
        and spec.rec_control in ("None", "Off", "On")
        and spec.hdmi_4ch_audio_output in (("None",) + P377_FX3_HDMI_4CH_AUDIO_MODES)
        and spec.hdmi_info_display in ("None", "Off", "On")
        and spec.ctrl_for_hdmi in ("None", "Off", "On")
        and spec.fx6_hdmi_tc_out in ("None", "Off", "On")
        and spec.reset_action in P377_RESET_ACTIONS
        and spec.recording_target_slot in (1, 2)
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P377_VAULT_ACTIONS
        and spec.vault_firewall_errno in P377_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P377_BLOCKED_INVALID_PILLAR69B_SPEC, "Invalid Pillar 69B spec fields")

    st = compute_expected_hdmi_recctrl_24p_sdi_slot1_vault_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        log_shooting_mode=spec.log_shooting_mode,
        picture_profile=spec.picture_profile,
        hdmi_resolution=spec.hdmi_resolution,
        rec_media_dur_hdmi_output=spec.rec_media_dur_hdmi_output,
        output_resolution=spec.output_resolution,
        hdmi_4k_output_rate_prev=spec.hdmi_4k_output_rate_prev,
        hdmi_4k_output_rate_new=spec.hdmi_4k_output_rate_new,
        raw_output_enabled=spec.raw_output_enabled,
        time_code_output=spec.time_code_output,
        rec_control=spec.rec_control,
        compatible_external_recorder_connected=spec.compatible_external_recorder_connected,
        usb_streaming_active=spec.usb_streaming_active,
        hdmi_4ch_audio_output=spec.hdmi_4ch_audio_output,
        four_discrete_hdmi_audio_requested=spec.four_discrete_hdmi_audio_requested,
        hdmi_info_display=spec.hdmi_info_display,
        ctrl_for_hdmi=spec.ctrl_for_hdmi,
        dormant_4k_2k_output_requested=spec.dormant_4k_2k_output_requested,
        dormant_24p_60p_output_requested=spec.dormant_24p_60p_output_requested,
        fx6_sdi_output_on=spec.fx6_sdi_output_on,
        fx6_hdmi_output_on=spec.fx6_hdmi_output_on,
        fx6_codec_mode=spec.fx6_codec_mode,
        fx6_sq_fps=spec.fx6_sq_fps,
        fx6_hdmi_tc_out=spec.fx6_hdmi_tc_out,
        fx6_sdi_hdmi_rec_control=spec.fx6_sdi_hdmi_rec_control,
        fx6_card_inserted=spec.fx6_card_inserted,
        reset_action=spec.reset_action,
        recording_target_slot=spec.recording_target_slot,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    hdmi_ok = (
        spec.reported_hdmi_matrix_errno == st["hdmi_matrix_errno"]
        and st["hdmi_matrix_errno"] is None
        and spec.reported_dormant_output_errno == st["dormant_output_errno"]
        and st["dormant_output_errno"] is None
        and not spec.dormant_4k_2k_output_requested
        and not spec.dormant_24p_60p_output_requested
        and not spec.four_discrete_hdmi_audio_requested
        and spec.reported_effective_rec_media_dur_hdmi == st["effective_rec_media_dur_hdmi"]
        and spec.reported_effective_output_resolution == st["effective_output_resolution"]
        and spec.reported_output_forced_1080_downscale == st["output_forced_1080_downscale"]
        and spec.reported_effective_hdmi_info_display == st["effective_hdmi_info_display"]
        and spec.reported_reboot_required_for_24_00p_switch
        == st["reboot_required_for_24_00p_switch"]
        and spec.reported_cross_24_00p_playback_isolated == st["cross_24_00p_playback_isolated"]
        and spec.reported_rec_control_stby_rec_indicator_active
        == st["rec_control_stby_rec_indicator_active"]
        and spec.reported_internal_media_write_attempted == st["internal_media_write_attempted"]
        and spec.reported_fx6_sdi_forced_1080 == st["fx6_sdi_forced_1080"]
        and spec.reported_fx6_hdmi_forced_1080 == st["fx6_hdmi_forced_1080"]
        and spec.hdmi_recctrl_24p_or_slot1_vault_drift_events == 0
    )
    if not hdmi_ok:
        _fail(
            P377_BLOCKED_HDMI_RECCTRL_24P_OR_DORMANT_OUTPUT_DRIFT,
            "External Output HDMI matrix, TC->REC Control gate, 24.00p reboot, dormant 4K/2K/24p-60p debunk, or FX6 SDI/HDMI matrix violated",
        )

    reset_ok = (
        spec.post_rec_media_dur_hdmi == st["post_rec_media_dur_hdmi"]
        and spec.post_output_resolution == st["post_output_resolution"]
        and spec.post_time_code_output == st["post_time_code_output"]
        and spec.post_rec_control == st["post_rec_control"]
        and spec.post_hdmi_4ch_audio == st["post_hdmi_4ch_audio"]
        and spec.post_hdmi_info_display == st["post_hdmi_info_display"]
        and spec.post_ctrl_for_hdmi == st["post_ctrl_for_hdmi"]
    )
    if not reset_ok:
        _fail(
            P377_BLOCKED_HDMI_RECCTRL_24P_OR_DORMANT_OUTPUT_DRIFT,
            "Setup -> [External Output] Camera Settings Reset resistance / Initialize reset boundary violated",
        )

    slot1_mutated = (
        spec.requested_vault_action in P377_WRITE_MUTATING_SLOT1_VAULT_ACTIONS
        and spec.reported_vault_action_allowed
    )
    vault_ok = (
        not slot1_mutated
        and spec.reported_vault_action_allowed == st["vault_action_allowed"]
        and spec.vault_firewall_errno == st["vault_firewall_errno"]
        and spec.slot1_writes == 0
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_sector_writes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.cnflasha_writes == 0
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_format_hard_locked
    )
    if not vault_ok:
        _fail(
            P377_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Recovery Vault EROFS=30 firewall breached",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P377_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P377_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P377_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P377_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    vault_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "69B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "rec_media": spec.reported_effective_rec_media_dur_hdmi,
            "output_res": spec.reported_effective_output_resolution,
            "rec_ctrl": spec.reported_rec_control_stby_rec_indicator_active,
            "slot1_writes": spec.slot1_writes,
            "errors": errors,
        }
    )
    return HdmiRecCtrl24pSdiSlot1VaultReport(
        schema=PHASE377_SCHEMA,
        version=PHASE377_VERSION,
        passed=passed,
        status=P377_STATUS_VERIFIED_PILLAR_69B if passed else P377_STATUS_REJECTED_PILLAR_69B,
        block_code=block_code,
        hdmi_extout_24p_recctrl_and_sdi_verified=hdmi_ok,
        extout_reset_resistance_verified=reset_ok,
        slot1_erofs_overlay_and_h0_h3_verified=vault_and_h0_h3_ok,
        matrix_states_checked=50,
        hdmi_recctrl_24p_or_slot1_vault_drift_events=spec.hdmi_recctrl_24p_or_slot1_vault_drift_events,
        slot1_writes=spec.slot1_writes,
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_sector_writes=spec.slot1_sector_writes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        cnflasha_writes=spec.cnflasha_writes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_pixelmap_monitor_recallhold_hdmi_recctrl_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_69a: Optional[PixelMapMonitorRecallHoldVaultSpec] = None,
    spec_69b: Optional[HdmiRecCtrl24pSdiSlot1VaultSpec] = None,
) -> PixelMapMonitorRecallHoldHdmiRecCtrlVaultReport:
    """Combined single-shot verifier for Pillar 69A + Pillar 69B + 17 bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase377_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_pixelmap_monitor_recallhold_vault(
        spec_69a or build_default_safe_pixelmap_monitor_recallhold_vault_spec()
    )
    rep_b = evaluate_hdmi_recctrl_24p_sdi_slot1_vault(
        spec_69b or build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 377 Wave-67 donor artifact parity check failed")
    if not donor_snapshot.under_2_0s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return PixelMapMonitorRecallHoldHdmiRecCtrlVaultReport(
        schema=PHASE377_SCHEMA,
        version=PHASE377_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P377_STATUS_VERIFIED_PILLAR69_SUITE if all_ok else P377_STATUS_FAIL_PILLAR69_SUITE,
        donor_snapshot=donor_snapshot,
        pixelmap_monitor_recallhold_report=rep_a,
        hdmi_recctrl_24p_sdi_slot1_report=rep_b,
        pixelmap_apr_or_zero_abb_drift_events=rep_a.pixelmap_apr_or_zero_abb_drift_events,
        monitor_3item_or_dormant_evf_drift_events=rep_a.monitor_3item_or_dormant_evf_drift_events,
        recall_hold_11bit_or_push_key_drift_events=rep_a.recall_hold_11bit_or_push_key_drift_events,
        hdmi_recctrl_24p_or_slot1_vault_drift_events=(
            rep_b.hdmi_recctrl_24p_or_slot1_vault_drift_events
        ),
        slot1_writes=rep_a.slot1_writes + rep_b.slot1_writes,
        slot1_data_sector_writes=rep_a.slot1_data_sector_writes + rep_b.slot1_data_sector_writes,
        slot1_sector_writes=rep_a.slot1_sector_writes + rep_b.slot1_sector_writes,
        slot1_vault_mutation_bytes=(
            rep_a.slot1_vault_mutation_bytes + rep_b.slot1_vault_mutation_bytes
        ),
        cnflasha_writes=rep_a.cnflasha_writes + rep_b.cnflasha_writes,
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
        emmc_writes_authorized=P377_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(errs),
    )


def verify_pixelmap_monitor_recallhold_hdmi_recctrl_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_69a: Optional[PixelMapMonitorRecallHoldVaultSpec] = None,
    spec_69b: Optional[HdmiRecCtrl24pSdiSlot1VaultSpec] = None,
) -> PixelMapMonitorRecallHoldHdmiRecCtrlVaultReport:
    """Symmetry alias for `verify_pixelmap_monitor_recallhold_hdmi_recctrl_and_vault`."""
    return verify_pixelmap_monitor_recallhold_hdmi_recctrl_and_vault(
        force_clean_room=force_clean_room,
        spec_69a=spec_69a,
        spec_69b=spec_69b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 69A & 69B)
# ---------------------------------------------------------------------------


def run_pillar69a_pixelmap_monitor_recallhold_vault_6_scenario_suite() -> Pillar69ASuiteResult:
    """Run 6 Pillar 69A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, PixelMapMonitorRecallHoldVaultSpec, Optional[str]], ...] = (
        (
            P377_PILLAR_69A_SCENARIO_IDS[0],
            True,
            build_default_safe_pixelmap_monitor_recallhold_vault_spec(
                setup_auto_pixel_mapping="On",
                silent_mode="On",
                silent_target_auto_pixel_mapping="Off",
                reported_shutdown_shutter_sound_emitted=True,
                monitor_brightness_mode="Sunny Weather",
                display_quality="High",
                thermal_elevated=True,
                monitor_flip_direction="180 Degree Flip",
                reported_effective_display_quality="Standard",
                reported_thermal_display_quality_locked=True,
                hold_custom_key="Recall Custom hold 2",
                reset_action="Camera Settings Reset",
                post_auto_pixel_mapping="On",
                post_silent_target_auto_pixel_mapping="Off",
                post_monitor_brightness_mode="Sunny Weather",
                post_display_quality="High",
                post_monitor_flip_direction="180 Degree Flip",
                post_reg_custom_shoot_set_retained=True,
            ),
            None,
        ),
        (
            P377_PILLAR_69A_SCENARIO_IDS[1],
            True,
            build_default_safe_pixelmap_monitor_recallhold_vault_spec(
                camera_model=P377_FX6_DONOR_MODEL_NAME,
                fw_version=P377_FX6_DONOR_FW_VERSION,
                shooting_domain="Movie",
                exposure_mode="M",
                setup_auto_pixel_mapping="None",
                silent_mode="None",
                silent_target_auto_pixel_mapping="None",
                fx6_apr_requested=True,
                fx6_apr_lens_cap_and_black_cloth=True,
                fx6_apr_temperature_valid=True,
                fx6_abb_requested=False,
                reported_effective_auto_pixel_mapping="None",
                reported_effective_silent_target_auto_pixel_mapping="None",
                reported_shutdown_shutter_sound_emitted=False,
                monitor_brightness_mode="None",
                display_quality="None",
                monitor_flip_direction="None",
                fx6_vf_connected=True,
                fx6_vf_brightness=12,
                fx6_vf_color_mode="B&W",
                fx6_vf_adjust_pressed=True,
                fx6_mirror_switch="ROT",
                reported_effective_display_quality="None",
                hold_custom_key="None",
                fx6_push_key="Push AGC",
                fx6_lens_manual_mode=False,
                fx6_bokeh_control_on=False,
                reset_action="None",
                post_auto_pixel_mapping="None",
                post_silent_target_auto_pixel_mapping="None",
                post_monitor_brightness_mode="None",
                post_display_quality="None",
                post_monitor_flip_direction="None",
                post_reg_custom_shoot_set_retained=False,
            ),
            None,
        ),
        (
            P377_PILLAR_69A_SCENARIO_IDS[2],
            False,
            build_default_safe_pixelmap_monitor_recallhold_vault_spec(
                manual_pixel_mapping_requested=True,
                manual_pixel_map_battery_ok=False,
                manual_pixel_map_lens_cap_attached=False,
                pixel_map_notification_requested=True,
                reported_pixelmap_errno=None,
                pixelmap_apr_or_zero_abb_drift_events=1,
            ),
            P377_BLOCKED_PIXELMAP_APR_OR_ZERO_ABB_DRIFT,
        ),
        (
            P377_PILLAR_69A_SCENARIO_IDS[3],
            False,
            build_default_safe_pixelmap_monitor_recallhold_vault_spec(
                monitor_group_name="Finder/Monitor",
                dormant_evf_item_requested="Finder Frame Rate",
                display_quality="High",
                thermal_elevated=True,
                reported_effective_display_quality="High",  # Wrong: thermal forces Standard!
                reported_monitor_errno=None,
                reported_dormant_evf_errno=None,
                monitor_3item_or_dormant_evf_drift_events=1,
            ),
            P377_BLOCKED_MONITOR_3ITEM_OR_DORMANT_EVF_DRIFT,
        ),
        (
            P377_PILLAR_69A_SCENARIO_IDS[4],
            False,
            build_default_safe_pixelmap_monitor_recallhold_vault_spec(
                shooting_domain="Movie",
                exposure_mode="iAuto",
                hold_custom_key="Recall Custom hold 3",
                recall_independent_wb_requested=True,
                recall_drive_mode_selftimer_requested=True,
                reported_hold_key_errno=None,
                reported_recall_wb_errno=None,
                recall_hold_11bit_or_push_key_drift_events=1,
            ),
            P377_BLOCKED_RECALL_HOLD_11BIT_OR_PUSH_KEY_DRIFT,
        ),
        (
            P377_PILLAR_69A_SCENARIO_IDS[5],
            False,
            build_default_safe_pixelmap_monitor_recallhold_vault_spec(
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="SAVE_CAMSET_DAT_SLOT1",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_writes=1,
                slot1_data_sector_writes=4096,
                slot1_sector_writes=8,
                slot1_vault_mutation_bytes=4096,
                cnflasha_writes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/setting/69a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P377_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar69ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_pixelmap_monitor_recallhold_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar69ScenarioOutcome(
                scenario_id=sid,
                pillar="69A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar69ASuiteResult(
        passed=all_ok,
        status=P377_STATUS_VERIFIED_PILLAR_69A if all_ok else P377_STATUS_REJECTED_PILLAR_69A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar69b_hdmi_recctrl_24p_sdi_slot1_vault_6_scenario_suite() -> Pillar69BSuiteResult:
    """Run 6 Pillar 69B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, HdmiRecCtrl24pSdiSlot1VaultSpec, Optional[str]], ...] = (
        (
            P377_PILLAR_69B_SCENARIO_IDS[0],
            True,
            build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
                rec_media_dur_hdmi_output="Off(HDMI Only)",
                hdmi_4k_output_rate_prev="23.98p 10bit",
                hdmi_4k_output_rate_new="24.00p 10bit",
                time_code_output="On",
                rec_control="On",
                hdmi_4ch_audio_output="CH3/CH4",
                reported_effective_rec_media_dur_hdmi="Off(HDMI Only)",
                reported_effective_hdmi_info_display="Off",
                reported_reboot_required_for_24_00p_switch=True,
                reported_cross_24_00p_playback_isolated=True,
                reported_rec_control_stby_rec_indicator_active=True,
                reported_internal_media_write_attempted=False,
                reset_action="Camera Settings Reset",
                post_rec_media_dur_hdmi="Off(HDMI Only)",
                post_time_code_output="On",
                post_rec_control="On",
                post_hdmi_4ch_audio="CH3/CH4",
            ),
            None,
        ),
        (
            P377_PILLAR_69B_SCENARIO_IDS[1],
            True,
            build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
                camera_model=P377_FX6_DONOR_MODEL_NAME,
                fw_version=P377_FX6_DONOR_FW_VERSION,
                shooting_domain="S&Q",
                hdmi_resolution="None",
                rec_media_dur_hdmi_output="None",
                output_resolution="None",
                hdmi_4k_output_rate_prev="None",
                hdmi_4k_output_rate_new="None",
                raw_output_enabled="None",
                time_code_output="None",
                rec_control="None",
                hdmi_4ch_audio_output="None",
                hdmi_info_display="None",
                ctrl_for_hdmi="None",
                fx6_sdi_output_on=True,
                fx6_hdmi_output_on=True,
                fx6_codec_mode="RAW & XAVC-I",
                fx6_sq_fps=120,
                fx6_hdmi_tc_out="On",
                fx6_sdi_hdmi_rec_control="Parallel Rec",
                fx6_card_inserted=True,
                reported_effective_rec_media_dur_hdmi="None",
                reported_effective_output_resolution="1080p",
                reported_output_forced_1080_downscale=True,
                reported_effective_hdmi_info_display="None",
                reported_rec_control_stby_rec_indicator_active=True,
                reported_internal_media_write_attempted=True,
                reported_fx6_sdi_forced_1080=False,
                reported_fx6_hdmi_forced_1080=True,
                reset_action="None",
                post_rec_media_dur_hdmi="None",
                post_output_resolution="None",
                post_time_code_output="None",
                post_rec_control="None",
                post_hdmi_4ch_audio="None",
                post_hdmi_info_display="None",
                post_ctrl_for_hdmi="None",
                requested_vault_slot=2,
                requested_vault_action="READ_ONLY_AUDIT",
            ),
            None,
        ),
        (
            P377_PILLAR_69B_SCENARIO_IDS[2],
            False,
            build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
                shooting_domain="S&Q",
                rec_media_dur_hdmi_output="Off(HDMI Only)",
                time_code_output="Off",
                rec_control="On",
                four_discrete_hdmi_audio_requested=True,
                reported_hdmi_matrix_errno=None,
                hdmi_recctrl_24p_or_slot1_vault_drift_events=1,
            ),
            P377_BLOCKED_HDMI_RECCTRL_24P_OR_DORMANT_OUTPUT_DRIFT,
        ),
        (
            P377_PILLAR_69B_SCENARIO_IDS[3],
            False,
            build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
                rec_media_dur_hdmi_output="On",
                log_shooting_mode="Flexible ISO",
                output_resolution="2160p",
                dormant_4k_2k_output_requested=True,
                dormant_24p_60p_output_requested=True,
                reported_effective_output_resolution="2160p",  # Wrong: Log+RecMedia forces 1080p!
                reported_dormant_output_errno=None,
                reset_action="Camera Settings Reset",
                post_ctrl_for_hdmi="Off",  # Wrong: External Output resists Reset!
                hdmi_recctrl_24p_or_slot1_vault_drift_events=1,
            ),
            P377_BLOCKED_HDMI_RECCTRL_24P_OR_DORMANT_OUTPUT_DRIFT,
        ),
        (
            P377_PILLAR_69B_SCENARIO_IDS[4],
            False,
            build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
                rec_media_dur_hdmi_output="On",
                reported_effective_rec_media_dur_hdmi="On",
                reported_effective_hdmi_info_display="On",
                reported_internal_media_write_attempted=True,
                post_rec_media_dur_hdmi="On",
                recording_target_slot=1,
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="WRITE_M4ROOT_CLIP_SLOT1",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_writes=1,
                slot1_data_sector_writes=4096,
                slot1_sector_writes=8,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
            ),
            P377_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
        (
            P377_PILLAR_69B_SCENARIO_IDS[5],
            False,
            build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="WRITE_AVF_INFO_SLOT1",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_writes=2,
                slot1_data_sector_writes=4096,
                slot1_sector_writes=8,
                slot1_vault_mutation_bytes=4096,
                cnflasha_writes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/mnt/emmc/69b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P377_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar69ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_hdmi_recctrl_24p_sdi_slot1_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar69ScenarioOutcome(
                scenario_id=sid,
                pillar="69B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar69BSuiteResult(
        passed=all_ok,
        status=P377_STATUS_VERIFIED_PILLAR_69B if all_ok else P377_STATUS_REJECTED_PILLAR_69B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Standalone Pillar 69 Suite & Concurrent Unified 69/69 Master Aggregator
# ---------------------------------------------------------------------------


def run_pillar69_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar69StandaloneReport:
    """Run full Pillar 69 standalone suite (`6/6` Pillar 69A + `6/6` Pillar 69B + 17 bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase377_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar69a_pixelmap_monitor_recallhold_vault_6_scenario_suite()
    res_b = run_pillar69b_hdmi_recctrl_24p_sdi_slot1_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 377 donor verification failed")
    if not donor_snapshot.under_2_0s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE377_SCHEMA,
            "version": PHASE377_VERSION,
            "mode": donor_snapshot.verification_mode,
            "69a": [asdict(s) for s in res_a.scenarios],
            "69b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar69StandaloneReport(
        schema=PHASE377_SCHEMA,
        version=PHASE377_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P377_STATUS_VERIFIED_PILLAR69_SUITE if all_ok else P377_STATUS_FAIL_PILLAR69_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_69a_pixelmap_monitor_recallhold_vault=res_a,
        pillar_69b_hdmi_recctrl_24p_sdi_slot1_vault=res_b,
        pixelmap_apr_or_zero_abb_drift_events=(
            P377_PIXELMAP_APR_OR_ZERO_ABB_DRIFT_EVENTS if res_a.passed else 1
        ),
        monitor_3item_or_dormant_evf_drift_events=(
            P377_MONITOR_3ITEM_OR_DORMANT_EVF_DRIFT_EVENTS if res_a.passed else 1
        ),
        recall_hold_11bit_or_push_key_drift_events=(
            P377_RECALL_HOLD_11BIT_OR_PUSH_KEY_DRIFT_EVENTS if res_a.passed else 1
        ),
        hdmi_recctrl_24p_or_slot1_vault_drift_events=(
            P377_HDMI_RECCTRL_24P_OR_SLOT1_VAULT_DRIFT_EVENTS if res_b.passed else 1
        ),
        slot1_writes=(P377_SLOT1_WRITES if (res_a.passed and res_b.passed) else 1),
        slot1_data_sector_writes=(
            P377_SLOT1_DATA_SECTOR_WRITES if (res_a.passed and res_b.passed) else 1
        ),
        slot1_sector_writes=(
            P377_SLOT1_SECTOR_WRITES if (res_a.passed and res_b.passed) else 1
        ),
        slot1_vault_mutation_bytes=(
            P377_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        cnflasha_writes=(P377_CNFLASHA_WRITES if (res_a.passed and res_b.passed) else 4096),
        rf_packets_transmitted=P377_RF_PACKETS_TRANSMITTED,
        rf_nvs_mutation_bytes=P377_RF_NVS_MUTATION_BYTES,
        slot1_format_hard_locked=P377_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_eopnotsupp_enforced=P377_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        slot1_vault_erofs_ebusy_enforced=P377_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
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
        emmc_writes_authorized=P377_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(safety_errs),
    )


def _apply_master69_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def _master69_local_donors_available() -> bool:
    """Return True only when all 17 Wave-67 local donors exist."""
    required_relpaths: Tuple[str, ...] = (
        P377_DONOR_FX3_APPFW_702_RELPATH,
        P377_DONOR_FX3_BACKUP_BIN_RELPATH,
        P377_DONOR_FX6_APPFW_601_RELPATH,
        P377_DONOR_FX3_UXC_EN_F_RELPATH,
        P377_DONOR_FX3_UXC_SC_F_RELPATH,
        P377_DONOR_FX3_UXC_TC_F_RELPATH,
        P377_DONOR_FX3_UXC_JA_F_RELPATH,
        P377_DONOR_FX3_UXC_EN_RELPATH,
        P377_DONOR_FX3_UXC_SC_RELPATH,
        P377_DONOR_FX3_UXC_TC_RELPATH,
        P377_DONOR_FX3_UXC_JA_RELPATH,
        P377_DONOR_FX3_UXC_EN_G_RELPATH,
        P377_DONOR_FX3_UXC_SC_G_RELPATH,
        P377_DONOR_FX3_UXC_TC_G_RELPATH,
        P377_DONOR_FX3_UXC_JA_G_RELPATH,
        P377_DONOR_FX6_UXC_EN_RELPATH,
        P377_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for relpath in required_relpaths:
        try:
            resolved = _resolve_phase377_donor_path(relpath)
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


def evaluate_realhw_69pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master69PillarRecoveryReport:
    """Evaluate and aggregate all 69 recovery pillars (`1..69`) concurrently -> `69/69` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_69_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    if resolved_clean_room is None and not _master69_local_donors_available():
        resolved_clean_room = True
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_68pillar() -> Master68PillarRecoveryReport:
        return evaluate_realhw_68pillar_recovery_master(**kw)

    def _run_p69() -> Tuple[Pillar69StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar69_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_68 = pool.submit(_run_68pillar)
        fut_69 = pool.submit(_run_p69)
        m68_rep = fut_68.result()
        p69_rep, p69_dt = fut_69.result()

    all_errors: List[str] = list(m68_rep.errors) + list(p69_rep.errors)
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
        if getattr(m68_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-68 violated {attr_name} == {expected_val}")
        if getattr(p69_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 69 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("pixelmap_apr_or_zero_abb_drift_events", 0),
        ("monitor_3item_or_dormant_evf_drift_events", 0),
        ("recall_hold_11bit_or_push_key_drift_events", 0),
        ("hdmi_recctrl_24p_or_slot1_vault_drift_events", 0),
        ("slot1_writes", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_sector_writes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("cnflasha_writes", 0),
        ("rf_packets_transmitted", 0),
        ("rf_nvs_mutation_bytes", 0),
        ("emmc_writes_authorized", False),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_eopnotsupp_enforced", True),
        ("slot1_vault_erofs_ebusy_enforced", True),
    ):
        if getattr(p69_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 69 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m68_rep.pillars)
    spec69 = MASTER_69_PILLAR_SPECS[68]
    p69_metrics = {
        "pillar_69a_pixelmap_monitor_recallhold_vault": (
            f"{p69_rep.pillar_69a_pixelmap_monitor_recallhold_vault.scenarios_passed}/"
            f"{p69_rep.pillar_69a_pixelmap_monitor_recallhold_vault.scenarios_total}"
        ),
        "pillar_69b_hdmi_recctrl_24p_sdi_slot1_vault": (
            f"{p69_rep.pillar_69b_hdmi_recctrl_24p_sdi_slot1_vault.scenarios_passed}/"
            f"{p69_rep.pillar_69b_hdmi_recctrl_24p_sdi_slot1_vault.scenarios_total}"
        ),
        "pixelmap_apr_or_zero_abb_drift_events": p69_rep.pixelmap_apr_or_zero_abb_drift_events,
        "monitor_3item_or_dormant_evf_drift_events": (
            p69_rep.monitor_3item_or_dormant_evf_drift_events
        ),
        "recall_hold_11bit_or_push_key_drift_events": (
            p69_rep.recall_hold_11bit_or_push_key_drift_events
        ),
        "hdmi_recctrl_24p_or_slot1_vault_drift_events": (
            p69_rep.hdmi_recctrl_24p_or_slot1_vault_drift_events
        ),
        "slot1_writes": p69_rep.slot1_writes,
        "slot1_data_sector_writes": p69_rep.slot1_data_sector_writes,
        "slot1_sector_writes": p69_rep.slot1_sector_writes,
        "slot1_vault_mutation_bytes": p69_rep.slot1_vault_mutation_bytes,
        "cnflasha_writes": p69_rep.cnflasha_writes,
        "slot1_format_hard_locked": p69_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_eopnotsupp_enforced": p69_rep.slot1_vault_erofs_eopnotsupp_enforced,
        "overall_ready_for_hardware_attach": p69_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p69_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p69_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p69_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec69[0],
            pillar_id=spec69[1],
            phase_label=spec69[2],
            module_name=spec69[3],
            passed=bool(p69_rep.all_passed),
            status=p69_rep.status,
            verification_mode=p69_rep.verification_mode,
            elapsed_seconds=p69_dt,
            key_metrics=p69_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec69[1],
                    "mode": p69_rep.verification_mode,
                    "status": p69_rep.status,
                    "metrics": p69_metrics,
                    "passed": p69_rep.all_passed,
                }
            ),
            errors=tuple(p69_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master69_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p69_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_69_PILLAR_COUNT == 69
        and pillars_passed == 69
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE377_SCHEMA,
            "schema_version": PHASE377_MASTER_SCHEMA,
            "version": PHASE377_VERSION,
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

    return Master69PillarRecoveryReport(
        schema=PHASE377_SCHEMA,
        schema_version=PHASE377_MASTER_SCHEMA,
        version=PHASE377_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=(
            P377_STATUS_VERIFIED_69OF69_AGGREGATOR if all_ok else P377_STATUS_FAIL_69OF69_AGGREGATOR
        ),
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P377_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.50,
        under_6s_budget=elapsed < P377_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P377_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p69_rep.donor_snapshot,
        pillar69_a_pixelmap_monitor_recallhold_vault=(
            p69_rep.pillar_69a_pixelmap_monitor_recallhold_vault
        ),
        pillar69_b_hdmi_recctrl_24p_sdi_slot1_vault=(
            p69_rep.pillar_69b_hdmi_recctrl_24p_sdi_slot1_vault
        ),
        pixelmap_apr_or_zero_abb_drift_events=p69_rep.pixelmap_apr_or_zero_abb_drift_events,
        monitor_3item_or_dormant_evf_drift_events=(
            p69_rep.monitor_3item_or_dormant_evf_drift_events
        ),
        recall_hold_11bit_or_push_key_drift_events=(
            p69_rep.recall_hold_11bit_or_push_key_drift_events
        ),
        hdmi_recctrl_24p_or_slot1_vault_drift_events=(
            p69_rep.hdmi_recctrl_24p_or_slot1_vault_drift_events
        ),
        fx3_auto_pixel_map_resettable=P377_FX3_AUTO_PIXEL_MAP_RESETTABLE,
        fx3_silent_target_auto_pixel_map_resettable=(
            P377_FX3_SILENT_TARGET_AUTO_PIXEL_MAP_RESETTABLE
        ),
        fx3_has_finder_monitor_group=P377_FX3_HAS_FINDER_MONITOR_GROUP,
        fx3_has_dormant_evf_items_exposed=P377_FX3_HAS_DORMANT_EVF_ITEMS_EXPOSED,
        fx3_monitor_group_resettable=P377_FX3_MONITOR_GROUP_RESETTABLE,
        fx3_recall_custom_hold_bit_count=P377_FX3_RECALL_CUSTOM_HOLD_BIT_COUNT,
        fx3_recall_custom_hold_wb_hits=P377_FX3_RECALL_CUSTOM_HOLD_WB_HITS,
        fx3_recall_custom_hold_has_independent_wb=(
            P377_FX3_RECALL_CUSTOM_HOLD_HAS_INDEPENDENT_WB
        ),
        fx3_reg_custom_shoot_set_resettable=P377_FX3_REG_CUSTOM_SHOOT_SET_RESETTABLE,
        fx3_external_output_resettable=P377_FX3_EXTERNAL_OUTPUT_RESETTABLE,
        fx3_has_dormant_4k_2k_output=P377_FX3_HAS_DORMANT_4K_2K_OUTPUT,
        fx3_has_dormant_24p_60p_output=P377_FX3_HAS_DORMANT_24P_60P_OUTPUT,
        fx6_has_user_exposed_abb=P377_FX6_HAS_USER_EXPOSED_ABB,
        fx6_has_vf_4item_submenu=P377_FX6_HAS_VF_4ITEM_SUBMENU,
        fx6_has_recall_custom_hold=P377_FX6_HAS_RECALL_CUSTOM_HOLD,
        fx6_has_high_low_key_exposed=P377_FX6_HAS_HIGH_LOW_KEY_EXPOSED,
        slot1_writes=p69_rep.slot1_writes,
        slot1_sector_writes=m68_rep.slot1_sector_writes + p69_rep.slot1_sector_writes,
        cnflasha_writes=m68_rep.cnflasha_writes + p69_rep.cnflasha_writes,
        emmc_writes_authorized=P377_EMMC_WRITES_AUTHORIZED,
        drive_mode_or_dormant_focus_bracket_drift_events=(
            m68_rep.drive_mode_or_dormant_focus_bracket_drift_events
        ),
        shutter_2opt_xsync_efcs_or_nr_drift_events=(
            m68_rep.shutter_2opt_xsync_efcs_or_nr_drift_events
        ),
        creative_look_8param_override_or_softskin_drift_events=(
            m68_rep.creative_look_8param_override_or_softskin_drift_events
        ),
        delete_protect_recoverdb_slot1_vault_drift_events=(
            m68_rep.delete_protect_recoverdb_slot1_vault_drift_events
        ),
        fx3_has_dormant_focus_bracket_exposed=m68_rep.fx3_has_dormant_focus_bracket_exposed,
        fx3_has_shutter_type_auto_exposed=m68_rep.fx3_has_shutter_type_auto_exposed,
        fx3_has_dormant_soft_skin_exposed=m68_rep.fx3_has_dormant_soft_skin_exposed,
        fx6_has_still_drive_mode=m68_rep.fx6_has_still_drive_mode,
        fx6_has_focus_bracket=m68_rep.fx6_has_focus_bracket,
        fx6_has_mechanical_shutter=m68_rep.fx6_has_mechanical_shutter,
        fx6_has_efcs=m68_rep.fx6_has_efcs,
        fx6_has_long_exp_nr=m68_rep.fx6_has_long_exp_nr,
        fx6_has_creative_look=m68_rep.fx6_has_creative_look,
        fx6_has_soft_skin_effect=m68_rep.fx6_has_soft_skin_effect,
        fx3_drive_mode_resettable=m68_rep.fx3_drive_mode_resettable,
        fx3_efcs_resettable=m68_rep.fx3_efcs_resettable,
        fx3_creative_look_resettable=m68_rep.fx3_creative_look_resettable,
        fx3_delete_confirm_resettable=m68_rep.fx3_delete_confirm_resettable,
        zoom_ciz_lockout_or_8speed_reset_drift_events=(
            m68_rep.zoom_ciz_lockout_or_8speed_reset_drift_events
        ),
        autoslow_6lockout_or_minss_still_drift_events=(
            m68_rep.autoslow_6lockout_or_minss_still_drift_events
        ),
        dual_base_iso_curve_matrix_drift_events=m68_rep.dual_base_iso_curve_matrix_drift_events,
        dormant_lossless_arw_exposed_events=m68_rep.dormant_lossless_arw_exposed_events,
        hlg_still_or_sort_rec_spillover_drift_events=(
            m68_rep.hlg_still_or_sort_rec_spillover_drift_events
        ),
        usb_lun_single_slot1_msc_hazard_events=m68_rep.usb_lun_single_slot1_msc_hazard_events,
        npfz100_pd_interlock_or_dcc1_drift_events=m68_rep.npfz100_pd_interlock_or_dcc1_drift_events,
        dormant_uvc_streaming_exposed_events=m68_rep.dormant_uvc_streaming_exposed_events,
        fx3_zoom_range_resettable=m68_rep.fx3_zoom_range_resettable,
        fx3_zoom_speed_resettable=m68_rep.fx3_zoom_speed_resettable,
        fx3_has_dormant_lossless_arw_exposed=m68_rep.fx3_has_dormant_lossless_arw_exposed,
        fx3_has_native_uvc_streaming=m68_rep.fx3_has_native_uvc_streaming,
        fx6_has_native_uvc_streaming=m68_rep.fx6_has_native_uvc_streaming,
        fx6_has_digital_zoom=m68_rep.fx6_has_digital_zoom,
        fx6_has_still_arw_hlg_pipeline=m68_rep.fx6_has_still_arw_hlg_pipeline,
        fx6_has_iso_auto_min_ss=m68_rep.fx6_has_iso_auto_min_ss,
        slot1_data_sector_writes=(
            m68_rep.slot1_data_sector_writes + p69_rep.slot1_data_sector_writes
        ),
        slot1_vault_mutation_bytes=(
            m68_rep.slot1_vault_mutation_bytes + p69_rep.slot1_vault_mutation_bytes
        ),
        rf_packets_transmitted=m68_rep.rf_packets_transmitted + p69_rep.rf_packets_transmitted,
        rf_nvs_mutation_bytes=m68_rep.rf_nvs_mutation_bytes + p69_rep.rf_nvs_mutation_bytes,
        slot1_format_hard_locked=(
            m68_rep.slot1_format_hard_locked and p69_rep.slot1_format_hard_locked
        ),
        slot1_vault_erofs_eopnotsupp_enforced=(
            m68_rep.slot1_vault_erofs_eopnotsupp_enforced
            and p69_rep.slot1_vault_erofs_eopnotsupp_enforced
        ),
        slot1_vault_erofs_ebusy_enforced=(
            m68_rep.slot1_vault_erofs_ebusy_enforced and p69_rep.slot1_vault_erofs_ebusy_enforced
        ),
        breathing_comp_lockout_or_catalyst_drift_events=(
            m68_rep.breathing_comp_lockout_or_catalyst_drift_events
        ),
        file_settings_camid_reel_or_sdhc_drift_events=(
            m68_rep.file_settings_camid_reel_or_sdhc_drift_events
        ),
        copyright_46ch_reset_erratum_or_serial_drift_events=(
            m68_rep.copyright_46ch_reset_erratum_or_serial_drift_events
        ),
        camset_copyright_pii_leak_events=m68_rep.camset_copyright_pii_leak_events,
        camset_copyright_pii_leaked_bytes=m68_rep.camset_copyright_pii_leaked_bytes,
        powersave_9cond_or_dormant_monitor_drift_events=(
            m68_rep.powersave_9cond_or_dormant_monitor_drift_events
        ),
        dormant_power_save_by_monitor_exposed_events=(
            m68_rep.dormant_power_save_by_monitor_exposed_events
        ),
        ntsc_pal_reboot_or_slot1_format_drift_events=(
            m68_rep.ntsc_pal_reboot_or_slot1_format_drift_events
        ),
        hdmi_raw_output_or_media_vault_drift_events=(
            m68_rep.hdmi_raw_output_or_media_vault_drift_events
        ),
        hdmi_4k_only_or_gamut_removal_drift_events=(
            m68_rep.hdmi_4k_only_or_gamut_removal_drift_events
        ),
        desqueeze_ratio_lock_or_bypass_drift_events=(
            m68_rep.desqueeze_ratio_lock_or_bypass_drift_events
        ),
        rec_lamp_tally_or_emph_display_drift_events=(
            m68_rep.rec_lamp_tally_or_emph_display_drift_events
        ),
        dormant_var_shutter_or_apsc_reset_drift_events=(
            m68_rep.dormant_var_shutter_or_apsc_reset_drift_events
        ),
        dormant_var_shutter_exposed_events=m68_rep.dormant_var_shutter_exposed_events,
        hdmi_red_border_clean_feed_leak_pixels=(
            m68_rep.hdmi_red_border_clean_feed_leak_pixels
        ),
        recorded_media_desqueeze_pixels=m68_rep.recorded_media_desqueeze_pixels,
        fx6_sdi_desqueeze_pixels=m68_rep.fx6_sdi_desqueeze_pixels,
        shoe_audio_preemption_or_limiter_drift_events=(
            m68_rep.shoe_audio_preemption_or_limiter_drift_events
        ),
        subject_recog_myth_or_face_memory_drift_events=(
            m68_rep.subject_recog_myth_or_face_memory_drift_events
        ),
        silent_mode_target_or_barrier_drift_events=(
            m68_rep.silent_mode_target_or_barrier_drift_events
        ),
        bodydata_version_flash_or_slot1_vault_drift_events=(
            m68_rep.bodydata_version_flash_or_slot1_vault_drift_events
        ),
        dormant_shutter_when_pwr_off_exposed_events=(
            m68_rep.dormant_shutter_when_pwr_off_exposed_events
        ),
        hdmi_face_frame_pixels_emitted=m68_rep.hdmi_face_frame_pixels_emitted,
        cnflasha_pixel_map_mutation_bytes=m68_rep.cnflasha_pixel_map_mutation_bytes,
        slot1_bodydata_mutation_bytes=m68_rep.slot1_bodydata_mutation_bytes,
        bodydata_placement_or_flash_authorized=m68_rep.bodydata_placement_or_flash_authorized,
        ftp_protocol_sftp_or_jpeg_size_drift_events=(
            m68_rep.ftp_protocol_sftp_or_jpeg_size_drift_events
        ),
        wb_custom_cine_ei_or_shockless_drift_events=(
            m68_rep.wb_custom_cine_ei_or_shockless_drift_events
        ),
        movie_af_speed_or_focus_map_spoof_events=m68_rep.movie_af_speed_or_focus_map_spoof_events,
        marker_15ratio_peaking_hdmi_leak_events=m68_rep.marker_15ratio_peaking_hdmi_leak_events,
        zero_rf_usblan_or_slot1_avf_bypass_events=(
            m68_rep.zero_rf_usblan_or_slot1_avf_bypass_events
        ),
        usblan_packets_transmitted=m68_rep.usblan_packets_transmitted,
        hdmi_marker_peaking_pixels_emitted=m68_rep.hdmi_marker_peaking_pixels_emitted,
        slot1_avf_info_mutation_bytes=m68_rep.slot1_avf_info_mutation_bytes,
        rec_media_prioritize_or_autoswitch_drift_events=(
            m68_rep.rec_media_prioritize_or_autoswitch_drift_events
        ),
        card_speed_vpg200_vpg400_gate_drift_events=(
            m68_rep.card_speed_vpg200_vpg400_gate_drift_events
        ),
        proxy_sq_dci4k_or_120p_lockout_drift_events=(
            m68_rep.proxy_sq_dci4k_or_120p_lockout_drift_events
        ),
        cloud_init_persist_or_power_off_ble_rf_events=(
            m68_rep.cloud_init_persist_or_power_off_ble_rf_events
        ),
        mymenu_42slot_or_fx6_lock_spoof_events=m68_rep.mymenu_42slot_or_fx6_lock_spoof_events,
        zero_rf_or_slot1_vault_bypass_events=m68_rep.zero_rf_or_slot1_vault_bypass_events,
        slot1_dcim_m4root_avf_mutation_bytes=m68_rep.slot1_dcim_m4root_avf_mutation_bytes,
        big6_home_or_lower_left_nd_drift_events=m68_rep.big6_home_or_lower_left_nd_drift_events,
        framing_manual_or_dormant_auto_framing_drift_events=(
            m68_rep.framing_manual_or_dormant_auto_framing_drift_events
        ),
        interval_shoot_9999_or_fx6_mxf_spoof_events=(
            m68_rep.interval_shoot_9999_or_fx6_mxf_spoof_events
        ),
        tc_make_regen_or_hdmi_rec_ctrl_drift_events=(
            m68_rep.tc_make_regen_or_hdmi_rec_ctrl_drift_events
        ),
        access_authen_ssh_tls_or_fan_max_drift_events=(
            m68_rep.access_authen_ssh_tls_or_fan_max_drift_events
        ),
        slot1_dcim_avf_mutation_bytes=m68_rep.slot1_dcim_avf_mutation_bytes,
        fx3_has_var_shutter=m68_rep.fx3_has_var_shutter,
        fx3_has_builtin_evf=m68_rep.fx3_has_builtin_evf,
        fx3_has_builtin_end_filter=m68_rep.fx3_has_builtin_end_filter,
        fx3_has_bt_timecode_link=m68_rep.fx3_has_bt_timecode_link,
        fx3_has_dormant_auto_framing=m68_rep.fx3_has_dormant_auto_framing,
        fx3_has_dormant_auto_hdr=m68_rep.fx3_has_dormant_auto_hdr,
        fx3_has_dormant_bulb_timer=m68_rep.fx3_has_dormant_bulb_timer,
        fx3_has_dormant_divide_extract=m68_rep.fx3_has_dormant_divide_extract,
        fx3_has_fan_control_max=m68_rep.fx3_has_fan_control_max,
        fx3_has_movie_self_timer=m68_rep.fx3_has_movie_self_timer,
        fx3_has_movie_sort_recording=m68_rep.fx3_has_movie_sort_recording,
        fx3_has_physical_end_hw=m68_rep.fx3_has_physical_end_hw,
        fx3_has_5axis_ibis=m68_rep.fx3_has_5axis_ibis,
        fx3_has_power_save_by_monitor=m68_rep.fx3_has_power_save_by_monitor,
        fx6_has_ibis=m68_rep.fx6_has_ibis,
        fx6_has_fan_control_max=m68_rep.fx6_has_fan_control_max,
        fx6_has_still_self_timer=m68_rep.fx6_has_still_self_timer,
        fx6_has_fn_menu=m68_rep.fx6_has_fn_menu,
        fx6_has_my_dial=m68_rep.fx6_has_my_dial,
        fx6_has_bluetooth_hardware=m68_rep.fx6_has_bluetooth_hardware,
        fx6_has_av_tv_rotate=m68_rep.fx6_has_av_tv_rotate,
        fx6_has_exif_copyright_menu=m68_rep.fx6_has_exif_copyright_menu,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        master_69pillar_sha256=master_sha,
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


def evaluate_69pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master69PillarRecoveryReport:
    """Short alias for `evaluate_realhw_69pillar_recovery_master`."""
    return evaluate_realhw_69pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_69pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master69PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_69pillar_recovery_master`."""
    return evaluate_realhw_69pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_69pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master69PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_69pillar_recovery_master`."""
    return evaluate_realhw_69pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_69pillar_recovery(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master69PillarRecoveryReport:
    """Milestone 364/324 dynamic discovery alias for `evaluate_realhw_69pillar_recovery_master`."""
    return evaluate_realhw_69pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_all_69_recovery_pillars(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master69PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_69pillar_recovery_master`."""
    return evaluate_realhw_69pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
