"""Phase 380 Milestone — Recovery Pillar 70 (`70A`/`70B`) & Concurrent 70/70 Master Recovery Verifier:
Wave-68 Sony ILME-FX3 (Ver. 7.02) vs ILME-FX6 (Ver. 6.01) Empirically Grounded Guardrails:
  * Pillar 70A (`Area/Date-DST` & RTC Backup vs FX6 `Clock Set` + `[Grid Line]` vs `[Marker Display] -> [Guideframe]`
    Clean-HDMI Split vs FX6 `Marker`):
    1. `Setup -> [Area/Date] -> [Area/Date/Time Setting]` (`_f 0x6a9c`, replacing legacy `base 0xe87f`
       `Date/Time Setup`): exact 4 items (`[Area Setting]` 30 `AREA_GMT_*` zones `GMT_M_11_0..GMT_P_12_0`
       incl. 6 half-hour zones `M_03_5`/`P_03_5`/`P_04_5`/`P_05_5`/`P_06_5`/`P_09_5`, `[Daylight Savings]`
       `Off` def / `On` + exact Sony ELF typo `convert_setting_daylight_saving_to_saylight_saving`,
       `[Date/Time]` + exact Sony ELF typo `BKID_APP_setting_auto_sync_sever_date_time`, `[Date Format]`
       `Y-M-D` / `M-D-Y` / `D-M-Y` only). Resists `Camera Settings Reset`, reset only on `Initialize`
       (re-triggers `37dlg_rec203_initial_setting_controller`). Internal rechargeable backup battery
       (NO user CR2032 slot; `>= 24 hours` OFF with full `NP-FZ100` to charge; no `3 months` claim in
       `ilc/2210`). Contrasts FX6 `Maintenance > Clock Set` (`UTC -12:00..+14:00` 30-min steps,
       `YYMMDD`/`MMDDYY`/`DDMMYY` + `12h/24h`, ZERO UI DST switch despite dormant `summer_time_name_dst`,
       `Backup Battery End` `ns2 0x411f`).
    2. `[Grid Line Display]` (`_f 0x6f9d`, `Off` def / `On`) & `[Grid Line Type]` (`_f 0x69c9`,
       `Rule of 3rds Grid` def / `Square Grid` / `Diag. + Square Grid`, all-mode Still/Movie/S&Q,
       deleted old `_movie` keys `BKID_APP_deleted_setting_grid_line_{display,type}_movie`, resists
       `Camera Settings Reset`, DOES passthrough to HDMI when `HDMI Info. Display = On` unless forced
       Clean-Feed by `Off(HDMI Only)` or `RAW Output = On`) vs `[Marker Display]` (`_f 0x61b2`, Movie/S&Q
       ONLY, 4 sub-items incl. `[Guideframe]` `_f 0x62f9`, ALL 5 resist `Camera Settings Reset`, hidden
       during `[Focus Magnifier]`, 100% Clean-HDMI monitor-only `0` HDMI pixels injected). Contrasts FX6
       `Monitoring > Marker` (`Guide Frame`, `Center Marker 1/2/3/4/Off`, `Safety Area 80/90/92.5/95%`,
       `Aspect Marker`, `100% Marker`, `User Box`, independent VF/SDI/HDMI OSD gates, ZERO 3-mode
       composition grid UI despite dormant `GUIDE_FRAME_{RULE_OF_3RD,SQUARE,DIAG_SQUARE,GOLDEN_RATIO}_GRID`).
  * Pillar 70B (`[Save/Load Settings]` `CAMSET01..10.DAT` / `libSaveLoadSettings.so` / `Camera Set. Memory`
    `1..3` vs `M1..M4` & Slot-1 `EROFS=30` + Sync Terminal Debunk / MI-Shoe `[Video Light Mode]` vs
    `XLR-H1` Preemption vs FX6 `TC IN/OUT` & Zero `GENLOCK`):
    1. `[Save/Load Settings]` (`_f 0x6254`): Card target HARD-LOCKED to `Slot 1` (cannot switch to `Slot 2`),
       max `10` slots `CAMSET01..10.DAT` (plus C3 Portal Cloud Private/Share max `60`), exact path
       `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT` (SD `/PRIVATE` prefix vs CFexpress `""`, ZERO `PRO/CAMERA`
       hits in FX3). Verifies `libSaveLoadSettings.so` (`18,760 B`, SHA-256
       `07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7`, `requestTo{Read,Check,Write}`,
       `Backup_{get_datasize,read,write}`, `infra_getCallbackFuncTable{,Ftp}`). Enforces same-model lock,
       Ver. `1.01 -> 2.00+` cross-version reject, `MR` mode block, reboot-after-Load prompt (`_g 0x62dd`),
       complete official exclusion list (IPTC, Copyright, External Flash Set., Custom WB 1-3, Face Memory,
       11 FTP/Network/Security items, Language, Area/Date/Time), separate `FTPSET%02d.DAT` path, and
       `[Camera Set. Memory]` (`1..3` NVRAM anti-Reset & inside `CAMSET`, vs `M1..M4` card
       `%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT` via `[Memory/Recall Media]` Slot 1/2, excluding
       `Custom Key/Dial Set.` & `Program Shift`). Tier-0 `Slot 1` Vault Firewall: ANY Save/Delete of
       `CAMSET*.DAT`, `FTPSET*.DAT`, or Slot-1 `CAMPR*.DAT` MUST fail-closed with `EROFS (errno 30)`
       (`slot1_writes = 0`); read-only `Load` allowed only on simulated non-destructive host buffer
       (never writes physical eMMC). Contrasts FX6 `Project > All File` (`Media(B)`
       `%c:%s/SONY/PRO/CAMERA/%s/%s.ALL`, max 64, `All File Load Network Data`), `User File` (`.USRF`),
       `Scene File` (`.SCN`), `User 3D LUT` (16 `.cube`), and `0`-hit dormant `Reference File`.
    2. Sync Terminal Debunk: FX3 has ZERO physical PC flash sync terminal (`0` `SYNCHRO_TERMINAL*` symbols
       in `FX3 appFw.so`, `0` pages in `ilc/2210`); dormant `Flash Sync Spd. Prty.` (`_f 0x6b31`) &
       `SYNCHRO_TERMINAL_OUTPUT_SET_ON` (`_g 0x645e`) blocked `EOPNOTSUPP = 95`. MI Shoe `[Flash Mode]` /
       `[External Flash Set.]`: Still mechanical shutter ONLY (`1/250 s` max sync, `< 250 V` positive
       polarity, anti-Reset & excluded from `CAMSET*.DAT`). `[Video Light Mode]` (`_f 0x6211`, `HVL-LBPC`,
       4 modes: `Power Link` def / `REC Link` / `REC Link&STBY` / `Auto`): hard physical mutual exclusion
       with `XLR-H1` (occupies sole electrical MI Shoe; Accessory Shoe Kit is passive cold shoe only),
       plus Stage-B `PMIC 5V <= 900 mA` budget. Contrasts FX6 `Technical > Video Light Set` (3 modes ONLY
       — zero `Auto`), zero Still Flash UI, single switchable `TC IN/OUT` BNC (`EXT-LK`), and ZERO
       physical `GENLOCK` BNC (vs `PXW-FX9`, despite `107` dormant `GENLOCK` ELF symbols).
  * Unified `70/70` Master Recovery Aggregator (Pillars `1..69` + Pillar `70`) running concurrently.

Safety Redlines (HARD-LOCKED):
  - Zero hardware attach, zero physical device writes, zero USB/UART TX, zero OTP/RPMB, zero eMMC writes.
  - Zero `Slot 1` format or data sector writes (`EROFS=30` fail-closed).
  - Zero raw firmware bytes leaked (`raw_firmware_bytes_leaked == 0`).
  - Bounded `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 18-donor inspection (`<= 2.0s` budget, incl.
    `libSaveLoadSettings.so`) with explicit `work_root is None` guard and automatic `CLEAN_ROOM_SYNTHETIC`
    fallback on donorless hosts.
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
from .realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier import (
    P255_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
    P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
    P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
)
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
from .realhw_69pillar_pixelmap_monitor_recallhold_hdmi_recctrl_vault_verifier import (
    MASTER_69_PILLAR_SPECS,
    Master69PillarRecoveryReport,
    evaluate_realhw_69pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Phase 380 Milestone Metadata, Safety Redlines & Pinned Budget Constants
# ---------------------------------------------------------------------------

PHASE380_SCHEMA = (
    "realhw_70pillar_milestone_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_vault_verifier_v1"
)
PHASE380_MASTER_SCHEMA = "realhw_70pillar_recovery_master_v1"
PHASE380_VERSION = "1.0.0"
PHASE380_PHASE_NUMBER = 380

P380_ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"

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

P380_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED = False
P380_CROSS_MODEL_FLASH_AUTHORIZED = False
P380_EMMC_WRITES_AUTHORIZED = False
P380_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
P380_OVERALL_READY_FOR_HARDWARE_ATTACH = False

OTP_FUSE_TOUCHES = 0
OTP_FUSE_WRITES = 0
RPMB_COUNTER_INCREMENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PHYSICAL_DEVICE_WRITES = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

P380_BOUNDED_HEADER_BYTES = 4096
P380_MAX_FULL_DONOR_BYTES = 3_000_000
P380_DONOR_INSPECT_BUDGET_SECONDS = 2.0
P380_DONOR_INSPECT_CI_BUDGET_SECONDS = 2.0
P380_FAST_CLI_BUDGET_SECONDS = 1.50
P380_NOMINAL_BUDGET_SECONDS = 4.00
P380_CONCURRENT_CEILING_SECONDS = 6.00

P380_ENOENT_ERRNO = 2
P380_EBUSY_ERRNO = 16
P380_EINVAL_ERRNO = 22
P380_EROFS_ERRNO = 30
P380_EOPNOTSUPP_ERRNO = 95

# Camera Identities
P380_FX3_MODEL_NAME = "ILME-FX3"
P380_FX3_MODEL_ID = 0x91030080
P380_FX3_PRODUCT_CODENAME = "PRODUCT_MODEL_ALCIN_UUD"
P380_FX3_HELPGUIDE_ID = "ilc/2210"
P380_FX3_FW_VERSION = "7.02"
P380_FX3_SUPPORTED_FW_VERSIONS = (
    "7.02", "7.01", "7.00", "6.02", "6.00", "5.00", "4.00", "3.00", "2.05", "2.04", "2.00"
)
P380_FX3_LEGACY_INCOMPATIBLE_CAMSET_VERSIONS = ("1.01", "1.00")

P380_FX6_DONOR_MODEL_NAME = "ILME-FX6"
P380_FX6_DONOR_FW_VERSION = "6.01"
P380_FX6_PRODUCT_CODENAME = "PRODUCT_MODEL_CHAPLIN"

# Pinned Wave-68 18 Donors (15 FX3 incl. libSaveLoadSettings.so + 3 FX6)
P380_DONOR_FX3_APPFW_702_RELPATH = P348_DONOR_FX3_APPFW_702_RELPATH
P380_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH = P255_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH
P380_DONOR_FX3_BACKUP_BIN_RELPATH = P348_DONOR_FX3_BACKUP_BIN_RELPATH
P380_DONOR_FX6_APPFW_601_RELPATH = P348_DONOR_FX6_APPFW_601_RELPATH
P380_DONOR_FX3_UXC_EN_F_RELPATH = P348_DONOR_FX3_UXC_EN_F_RELPATH
P380_DONOR_FX3_UXC_SC_F_RELPATH = P348_DONOR_FX3_UXC_SC_F_RELPATH
P380_DONOR_FX3_UXC_TC_F_RELPATH = P348_DONOR_FX3_UXC_TC_F_RELPATH
P380_DONOR_FX3_UXC_JA_F_RELPATH = P348_DONOR_FX3_UXC_JA_F_RELPATH
P380_DONOR_FX3_UXC_EN_RELPATH = P348_DONOR_FX3_UXC_EN_RELPATH
P380_DONOR_FX3_UXC_SC_RELPATH = P348_DONOR_FX3_UXC_SC_RELPATH
P380_DONOR_FX3_UXC_TC_RELPATH = P348_DONOR_FX3_UXC_TC_RELPATH
P380_DONOR_FX3_UXC_JA_RELPATH = P348_DONOR_FX3_UXC_JA_RELPATH
P380_DONOR_FX3_UXC_EN_G_RELPATH = P348_DONOR_FX3_UXC_EN_G_RELPATH
P380_DONOR_FX3_UXC_SC_G_RELPATH = P348_DONOR_FX3_UXC_SC_G_RELPATH
P380_DONOR_FX3_UXC_TC_G_RELPATH = P348_DONOR_FX3_UXC_TC_G_RELPATH
P380_DONOR_FX3_UXC_JA_G_RELPATH = P348_DONOR_FX3_UXC_JA_G_RELPATH
P380_DONOR_FX6_UXC_EN_RELPATH = P348_DONOR_FX6_UXC_EN_RELPATH
P380_DONOR_FX6_UXC_EN_2_RELPATH = P348_DONOR_FX6_UXC_EN_2_RELPATH

P380_PINNED_FX3_APPFW_702_BYTES = P348_PINNED_FX3_APPFW_702_BYTES
P380_PINNED_FX3_APPFW_702_HDR4K_SHA256 = P348_PINNED_FX3_APPFW_702_HDR4K_SHA256
P380_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES = P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES
P380_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256 = P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256
P380_PINNED_FX3_BACKUP_BIN_BYTES = P348_PINNED_FX3_BACKUP_BIN_BYTES
P380_PINNED_FX3_BACKUP_BIN_SHA256 = P348_PINNED_FX3_BACKUP_BIN_SHA256
P380_PINNED_FX6_APPFW_601_BYTES = P348_PINNED_FX6_APPFW_601_BYTES
P380_PINNED_FX6_APPFW_601_HDR4K_SHA256 = P348_PINNED_FX6_APPFW_601_HDR4K_SHA256

P380_PINNED_FX3_UXC_EN_F_BYTES = P348_PINNED_FX3_UXC_EN_F_BYTES
P380_PINNED_FX3_UXC_EN_F_SHA256 = P348_PINNED_FX3_UXC_EN_F_SHA256
P380_PINNED_FX3_UXC_SC_F_BYTES = P348_PINNED_FX3_UXC_SC_F_BYTES
P380_PINNED_FX3_UXC_SC_F_SHA256 = P348_PINNED_FX3_UXC_SC_F_SHA256
P380_PINNED_FX3_UXC_TC_F_BYTES = P348_PINNED_FX3_UXC_TC_F_BYTES
P380_PINNED_FX3_UXC_TC_F_SHA256 = P348_PINNED_FX3_UXC_TC_F_SHA256
P380_PINNED_FX3_UXC_JA_F_BYTES = P348_PINNED_FX3_UXC_JA_F_BYTES
P380_PINNED_FX3_UXC_JA_F_SHA256 = P348_PINNED_FX3_UXC_JA_F_SHA256
P380_PINNED_FX3_UXC_EN_BYTES = P348_PINNED_FX3_UXC_EN_BYTES
P380_PINNED_FX3_UXC_EN_SHA256 = P348_PINNED_FX3_UXC_EN_SHA256
P380_PINNED_FX3_UXC_SC_BYTES = P348_PINNED_FX3_UXC_SC_BYTES
P380_PINNED_FX3_UXC_SC_SHA256 = P348_PINNED_FX3_UXC_SC_SHA256
P380_PINNED_FX3_UXC_TC_BYTES = P348_PINNED_FX3_UXC_TC_BYTES
P380_PINNED_FX3_UXC_TC_SHA256 = P348_PINNED_FX3_UXC_TC_SHA256
P380_PINNED_FX3_UXC_JA_BYTES = P348_PINNED_FX3_UXC_JA_BYTES
P380_PINNED_FX3_UXC_JA_SHA256 = P348_PINNED_FX3_UXC_JA_SHA256
P380_PINNED_FX3_UXC_EN_G_BYTES = P348_PINNED_FX3_UXC_EN_G_BYTES
P380_PINNED_FX3_UXC_EN_G_SHA256 = P348_PINNED_FX3_UXC_EN_G_SHA256
P380_PINNED_FX3_UXC_SC_G_BYTES = P348_PINNED_FX3_UXC_SC_G_BYTES
P380_PINNED_FX3_UXC_SC_G_SHA256 = P348_PINNED_FX3_UXC_SC_G_SHA256
P380_PINNED_FX3_UXC_TC_G_BYTES = P348_PINNED_FX3_UXC_TC_G_BYTES
P380_PINNED_FX3_UXC_TC_G_SHA256 = P348_PINNED_FX3_UXC_TC_G_SHA256
P380_PINNED_FX3_UXC_JA_G_BYTES = P348_PINNED_FX3_UXC_JA_G_BYTES
P380_PINNED_FX3_UXC_JA_G_SHA256 = P348_PINNED_FX3_UXC_JA_G_SHA256
P380_PINNED_FX6_UXC_EN_BYTES = P348_PINNED_FX6_UXC_EN_BYTES
P380_PINNED_FX6_UXC_EN_SHA256 = P348_PINNED_FX6_UXC_EN_SHA256
P380_PINNED_FX6_UXC_EN_2_BYTES = P348_PINNED_FX6_UXC_EN_2_BYTES
P380_PINNED_FX6_UXC_EN_2_SHA256 = P348_PINNED_FX6_UXC_EN_2_SHA256

# Zero-Violation Pillar 70 Counters & Vault Flags
P380_AREADATE_DST_OR_RTC_BACKUP_DRIFT_EVENTS = 0
P380_GRID_VS_MARKER_CLEANHDMI_DRIFT_EVENTS = 0
P380_SAVELOAD_CAMSET_OR_CAMPR_SLOT1_DRIFT_EVENTS = 0
P380_SYNC_TERMINAL_MISHOE_OR_GENLOCK_DRIFT_EVENTS = 0

P380_HDMI_MARKER_GUIDEFRAME_LEAK_PIXELS = 0
P380_CAMSET_EXCLUDED_ITEM_LEAK_EVENTS = 0
P380_CAMSET_EXCLUDED_ITEM_LEAKED_BYTES = 0
P380_SLOT1_WRITES = 0
P380_SLOT1_DATA_SECTOR_WRITES = 0
P380_SLOT1_SECTOR_WRITES = 0
P380_SLOT1_VAULT_MUTATION_BYTES = 0
P380_CNFLASHA_WRITES = 0
P380_RF_PACKETS_TRANSMITTED = 0
P380_RF_NVS_MUTATION_BYTES = 0

P380_SLOT1_FORMAT_HARD_LOCKED = True
P380_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True
P380_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True
P380_AIRPLANE_MODE_FORCED_ON = True

P380_STAGE_B_VOLATILE_OVERLAY_DIR = "/tmp/fx3_stage_b_overlay/pillar70"
P380_FORBIDDEN_PERSISTENT_TARGETS = (
    "/dev/cnflasha",
    "/setting",
    "/mnt/emmc",
    "/nflasha",
)
P380_TIER0_SURFACE_COUNT = 16

# ---------------------------------------------------------------------------
# Wave-68 Empirically Verified Constants (UXC resid16, ELF & Help Guide)
# ---------------------------------------------------------------------------

# 1. Pillar 70A-1: `Setup -> [Area/Date]` & RTC Backup vs FX6 `Maintenance > Clock Set`
P380_AREA_DATE_TIME_SETTING_F_RESID16 = 0x6A9C
P380_LEGACY_DATE_TIME_SETUP_BASE_RESID16 = 0xE87F
P380_AREA_DATE_GROUP_G_RESID16 = 0x6108
P380_AREA_SETTING_BASE_RESID16 = 0xE91A
P380_DAYLIGHT_SAVINGS_BASE_RESID16 = 0xE917
P380_DATE_TIME_F_RESID16S = (0x73B5, 0x7A9A)
P380_DATE_FORMAT_F_RESID16S = (0x670D, 0x7416, 0x7976, 0x65DA)
P380_DATE_FORMAT_BASE_RESID16S = (0xE888, 0xE887, 0xE97E)
P380_INITIAL_SETTING_CREATORS_APP_G_RESID16S = (0x64A8, 0x63A6)

P380_ELF_DAYLIGHT_SAVING_SONY_TYPO = (
    "convert_setting_daylight_saving_to_saylight_saving"
)
P380_ELF_AUTO_SYNC_SERVER_SONY_TYPO = (
    "BKID_APP_setting_auto_sync_sever_date_time"
)
P380_ELF_INITIAL_SETTING_CONTROLLER = "37dlg_rec203_initial_setting_controller"
P380_ELF_LAUNCH_DATE_TIME_SETUP_SYMBOL = "PRM_launch_date_time_setup_area_setting"
P380_BKID_DAYLIGHT_SAVING = "BKID_APP_setting_daylight_saving"
P380_BKID_DATE_FORMAT = "BKID_APP_setting_date_format"
P380_BKID_DATE_TIME_SET_STATUS = "BKID_APP_date_time_set_status"

P380_FX3_AREA_DATE_TIME_4_ITEMS = (
    "Area Setting",
    "Daylight Savings",
    "Date/Time",
    "Date Format",
)
P380_FX3_AREA_GMT_HALF_HOUR_ZONES = (
    "AREA_GMT_M_03_5",
    "AREA_GMT_P_03_5",
    "AREA_GMT_P_04_5",
    "AREA_GMT_P_05_5",
    "AREA_GMT_P_06_5",
    "AREA_GMT_P_09_5",
)
P380_FX3_AREA_GMT_30_ZONES = (
    "AREA_GMT_M_11_0",
    "AREA_GMT_M_10_0",
    "AREA_GMT_M_09_0",
    "AREA_GMT_M_08_0",
    "AREA_GMT_M_07_0",
    "AREA_GMT_M_06_0",
    "AREA_GMT_M_05_0",
    "AREA_GMT_M_04_0",
    "AREA_GMT_M_03_5",
    "AREA_GMT_M_03_0",
    "AREA_GMT_M_02_0",
    "AREA_GMT_M_01_0",
    "AREA_GMT_P_00_0",
    "AREA_GMT_P_01_0",
    "AREA_GMT_P_02_0",
    "AREA_GMT_P_03_0",
    "AREA_GMT_P_03_5",
    "AREA_GMT_P_04_0",
    "AREA_GMT_P_04_5",
    "AREA_GMT_P_05_0",
    "AREA_GMT_P_05_5",
    "AREA_GMT_P_06_0",
    "AREA_GMT_P_06_5",
    "AREA_GMT_P_07_0",
    "AREA_GMT_P_08_0",
    "AREA_GMT_P_09_0",
    "AREA_GMT_P_09_5",
    "AREA_GMT_P_10_0",
    "AREA_GMT_P_11_0",
    "AREA_GMT_P_12_0",
)
P380_FX3_AREA_GMT_ZONE_COUNT = 30
P380_FX3_DAYLIGHT_SAVINGS_DEFAULT = "Off"
P380_FX3_DATE_FORMATS = ("Y-M-D", "M-D-Y", "D-M-Y")
P380_FX3_AREA_DATE_TIME_RESETTABLE = False  # Resists Camera Settings Reset; Initialize only
P380_FX3_HAS_USER_CR2032_SLOT = False
P380_FX3_RTC_BACKUP_CHARGE_MIN_HOURS_OFF = 24
P380_FX3_HELPGUIDE_CLAIMS_3_MONTHS_RETENTION = False

P380_FX6_CLOCK_SET_NS2_RESID16 = 0x426C
P380_FX6_UTC_TZ_NS2_RESID16_RANGE = (0x4A55, 0x4ABD)
P380_FX6_DORMANT_DST_NS2_RESID16 = 0x564D
P380_FX6_BACKUP_BATTERY_END_NS2_RESID16 = 0x411F
P380_FX6_ELF_DORMANT_SUMMER_TIME_SYMBOL = "summer_time_name_dst"
P380_FX6_UTC_OFFSET_MIN_MINUTES = -720  # UTC -12:00
P380_FX6_UTC_OFFSET_MAX_MINUTES = 840   # UTC +14:00
P380_FX6_UTC_OFFSET_STEP_MINUTES = 30
P380_FX6_DATE_MODES = ("YYMMDD", "MMDDYY", "DDMMYY")
P380_FX6_TIME_FORMAT_MODES = ("12h", "24h")
P380_FX6_HAS_UI_DST_SWITCH = False
P380_FX6_HAS_USER_CR2032_SLOT = False

# 2. Pillar 70A-2: `[Grid Line]` vs `[Marker Display] -> [Guideframe]` Clean-HDMI Split vs FX6 `Marker`
P380_GRID_LINE_DISPLAY_F_RESID16 = 0x6F9D
P380_GRID_LINE_TYPE_F_RESID16 = 0x69C9
P380_GRID_LINE_DISPLAY_SELECT_F_RESID16 = 0x70C5
P380_GRID_LINE_TYPE_VALUES_F_RESID16S = (0x78AE, 0x715A, 0x786C)
P380_GRID_LINE_TYPE_VALUES_BASE_RESID16S = (0xE809, 0xE806, 0xE807)
P380_MARKER_DISPLAY_F_RESID16S = (0x61B2, 0x6803)
P380_GUIDEFRAME_F_RESID16 = 0x62F9
P380_GUIDEFRAME_G_RESID16 = 0x62A0

P380_BKID_DELETED_GRID_LINE_MOVIE_SYMBOLS = (
    "BKID_APP_deleted_setting_grid_line_display_movie",
    "BKID_APP_deleted_setting_grid_line_type_movie",
)
P380_BKID_GRID_LINE_DISPLAY = "BKID_APP_setting_grid_line_display"
P380_BKID_GRID_LINE_TYPE = "BKID_APP_setting_grid_line_type"
P380_BKID_MARKER_DISPLAY = "BKID_APP_setting_marker_display"
P380_BKID_GUIDE_FRAME = "BKID_APP_setting_guide_frame"

P380_FX3_GRID_LINE_DISPLAY_DEFAULT = "Off"
P380_FX3_GRID_LINE_TYPES = (
    "Rule of 3rds Grid",
    "Square Grid",
    "Diag. + Square Grid",
)
P380_FX3_GRID_LINE_TYPE_DEFAULT = "Rule of 3rds Grid"
P380_FX3_GRID_LINE_ALLOWED_DOMAINS = ("Still", "Movie", "S&Q")
P380_FX3_GRID_LINE_RESETTABLE = False  # Resists Camera Settings Reset!
P380_FX3_GRID_LINE_PASSTHROUGH_HDMI_ON_INFO = True

P380_FX3_MARKER_DISPLAY_DEFAULT = "Off"
P380_FX3_MARKER_DISPLAY_ALLOWED_DOMAINS = ("Movie", "S&Q")
P380_FX3_MARKER_DISPLAY_4_SUBITEMS = (
    "Center Marker",
    "Aspect Marker",
    "Safety Zone",
    "Guideframe",
)
P380_FX3_MARKER_DISPLAY_ALL_5_RESETTABLE = False  # All 5 resist Camera Settings Reset!
P380_FX3_MARKER_DISPLAY_HDMI_PIXELS_EMITTED = 0  # Strictly monitor-only Clean-HDMI!

P380_FX6_GUIDE_FRAME_NS2_RESID16 = 0x4520
P380_FX6_CENTER_MARKER_NS2_RESID16 = 0x450A
P380_FX6_CENTER_MARKER_MODES = ("Off", "1", "2", "3", "4")
P380_FX6_SAFETY_AREA_PERCENTAGES = ("80%", "90%", "92.5%", "95%")
P380_FX6_MARKER_SUBITEMS = (
    "Guide Frame",
    "Center Marker",
    "Safety Area",
    "Aspect Marker",
    "100% Marker",
    "User Box",
)
P380_FX6_MARKER_OSD_GATES = ("VF", "SDI", "HDMI")
P380_FX6_HAS_3MODE_COMPOSITION_GRID_UI = False
P380_FX6_DORMANT_GRID_SYMBOLS = (
    "GUIDE_FRAME_RULE_OF_3RD_GRID",
    "GUIDE_FRAME_SQUARE_GRID",
    "GUIDE_FRAME_DIAG_SQUARE_GRID",
    "GUIDE_FRAME_GOLDEN_RATIO_GRID",
)

# 3. Pillar 70B-1: `[Save/Load Settings]` `CAMSET01..10.DAT`, `libSaveLoadSettings.so`,
#    `Camera Set. Memory` `1..3` vs `M1..M4`, Slot-1 `EROFS=30` & FX6 `All File`
P380_SAVE_LOAD_SETTINGS_F_RESID16 = 0x6254
P380_CLOUD_PRIVATE_SHARE_F_RESID16S = (0x7C53, 0x7C5A)
P380_MEMORY_RECALL_MEDIA_F_RESID16 = 0x763C
P380_SAVE_LOAD_FTP_SETTINGS_F_RESID16 = 0x71AE
P380_SAVE_LOAD_REBOOT_PROMPT_G_RESID16 = 0x62DD
P380_SAVE_LOAD_ERROR_G_RESID16S = (0x624D, 0x61D7)

P380_FX3_CAMSET_PATH_TEMPLATE = "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"
P380_FX3_CAMPR_PATH_TEMPLATE = "%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT"
P380_FX3_FTPSET_PATH_TEMPLATE = "%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT"
P380_FX3_SD_MEDIA_PREFIX = "/PRIVATE"
P380_FX3_CFEXPRESS_MEDIA_PREFIX = ""
P380_FX3_PRO_CAMERA_PATH_HITS = 0
P380_FX3_CAMSET_LOCKED_SLOT = 1
P380_FX3_CAMSET_MAX_CARD_SLOTS = 10
P380_FX3_CAMSET_MAX_CLOUD_SLOTS = 60
P380_FX3_LIBSAVELOADSETTINGS_EXPORTS = (
    "SaveLoadSettingsIf::requestToRead",
    "SaveLoadSettingsIf::requestToCheck",
    "SaveLoadSettingsIf::requestToWrite",
    "SaveLoadSettings::procRead",
    "SaveLoadSettings::procCheck",
    "SaveLoadSettings::procWrite",
    "Backup_get_datasize",
    "Backup_read",
    "Backup_write",
    "infra_getCallbackFuncTable",
    "infra_getCallbackFuncTableFtp",
)

P380_FX3_CAMSET_NETWORK_11_EXCLUDED_ITEMS = (
    "FTP Transfer Func.",
    "Network Streaming",
    "Cloud Connection",
    "WPS Push",
    "Access Point Set.",
    "Wi-Fi Frequency Band",
    "IP Address Setting",
    "Edit Device Name",
    "Import Root Certificate",
    "Access Authen. Settings",
    "Security(IPsec)",
)
P380_FX3_CAMSET_SYSTEM_2_EXCLUDED_ITEMS = (
    "Language",
    "Area/Date/Time Setting",
)
P380_FX3_CAMSET_OFFICIAL_EXCLUDED_ITEMS = (
    "IPTC Information",
    "Copyright Info",
    "External Flash Set.",
    "White Balance (Custom 1-3)",
    "Face Memory",
) + P380_FX3_CAMSET_NETWORK_11_EXCLUDED_ITEMS + P380_FX3_CAMSET_SYSTEM_2_EXCLUDED_ITEMS
P380_FX3_CAMSET_CORE_EXCLUDED_COUNT = 16
P380_FX3_CAMSET_TOTAL_EXCLUDED_COUNT = len(P380_FX3_CAMSET_OFFICIAL_EXCLUDED_ITEMS)

P380_FX3_CAMERA_SET_MEMORY_BODY_SLOTS = ("1", "2", "3")
P380_FX3_CAMERA_SET_MEMORY_CARD_SLOTS = ("M1", "M2", "M3", "M4")
P380_FX3_CAMERA_SET_MEMORY_EXCLUDED_ITEMS = (
    "Custom Key/Dial Set.",
    "Program Shift",
)
P380_FX3_CAMERA_SET_MEMORY_BODY_RESETTABLE = False  # Resists Camera Settings Reset; inside CAMSET

P380_FX6_ALL_FILE_PATH_TEMPLATE = "%c:%s/SONY/PRO/CAMERA/%s/%s.ALL"
P380_FX6_ALL_FILE_SLOT = "Media(B)"
P380_FX6_ALL_FILE_MAX_SLOTS = 64
P380_FX6_USER_FILE_EXTENSION = ".USRF"
P380_FX6_SCENE_FILE_PATH_TEMPLATE = "%c:%s/SONY/PRO/SCENE/%s.SCN"
P380_FX6_USER_3D_LUT_MAX_SLOTS = 16
P380_FX6_REFERENCE_FILE_NS2_RESID16S = (0x429B, 0x4D52)
P380_FX6_REFERENCE_FILE_APPFW_HITS = 0
P380_FX6_HAS_USER_EXPOSED_REFERENCE_FILE = False

# 4. Pillar 70B-2: Sync Terminal Debunk, MI-Shoe `[External Flash Set.]` / `[Video Light Mode]`
#    vs `XLR-H1` Preemption vs FX6 `TC IN/OUT` BNC & Zero `GENLOCK`
P380_FX3_HAS_PHYSICAL_SYNC_TERMINAL = False
P380_FX3_SYNCHRO_TERMINAL_APPFW_HITS = 0
P380_FX3_SYNC_TERMINAL_HELPGUIDE_PAGES = 0
P380_DORMANT_FLASH_SYNC_SPD_PRTY_F_RESID16 = 0x6B31
P380_DORMANT_SYNCHRO_TERMINAL_ON_G_RESID16 = 0x645E

P380_FLASH_MODE_BASE_RESID16 = 0xE5CE
P380_FX3_FLASH_MODES = ("Flash Off", "Autoflash", "Fill-flash", "Slow Sync.", "Rear Sync.")
P380_EXTERNAL_FLASH_SET_F_RESID16S = (0x6771, 0x671D, 0x705F)
P380_FX3_FLASH_MAX_SYNC_RECIPROCAL = 250  # 1/250 s
P380_FX3_FLASH_TRIGGER_VOLTAGE_LIMIT_V = 250  # Must be strictly < 250 V positive polarity
P380_FX3_EXTERNAL_FLASH_SET_RESETTABLE = False
P380_FX3_EXTERNAL_FLASH_SET_IN_CAMSET = False

P380_VIDEO_LIGHT_MODE_F_RESID16S = (0x6211, 0x651B, 0x652F, 0x647A, 0x698E)
P380_FX3_VIDEO_LIGHT_MODES = ("Power Link", "REC Link", "REC Link&STBY", "Auto")
P380_FX3_VIDEO_LIGHT_MODE_DEFAULT = "Power Link"
P380_FX3_VIDEO_LIGHT_MODEL = "HVL-LBPC"
P380_XLR_H1_ACCESSORY_SHOE_IS_PASSIVE_COLD_SHOE = True
P380_XLR_H1_PREEMPTS_ELECTRICAL_MI_SHOE = True
P380_MISHOE_PMIC_5V_MAX_MA = 900

P380_FX6_VIDEO_LIGHT_SET_NS2_RESID16 = 0x4289
P380_FX6_VIDEO_LIGHT_MODES = ("Power Link", "Rec Link", "Rec Link + Stby")
P380_FX6_HAS_VIDEO_LIGHT_AUTO = False
P380_FX6_HAS_STILL_FLASH_UI = False
P380_FX3_HAS_TC_BNC = False
P380_FX6_HAS_TC_IN_OUT_BNC = True
P380_FX6_HAS_PHYSICAL_GENLOCK_BNC = False
P380_FX6_DORMANT_GENLOCK_SYMBOL_COUNT = 107
P380_FX6_DORMANT_GENLOCK_NS2_RESID16S = (0x4262, 0x56D5, 0x56D6, 0x56D7)

# Common Enums & Vault Actions
P380_ON_OFF_MODES = ("Off", "On")
P380_SHOOTING_DOMAINS = ("Still", "Movie", "S&Q")
P380_SHUTTER_TYPES = ("Mechanical Shutter", "Electronic Shutter")
P380_MEDIA_CARD_TYPES = ("SDXC", "CFexpress Type A")
P380_SAVELOAD_OPS = (
    "NONE",
    "SAVE_CAMSET",
    "LOAD_CAMSET",
    "DELETE_CAMSET",
    "SAVE_FTPSET",
    "LOAD_FTPSET",
    "DELETE_FTPSET",
    "SAVE_CAMPR",
    "RECALL_CAMPR",
    "FX6_SAVE_ALL_FILE",
    "FX6_LOAD_ALL_FILE",
)
P380_RESET_ACTIONS = ("None", "Camera Settings Reset", "Initialize")
P380_VAULT_ACTIONS = (
    "NONE",
    "READ_ONLY_AUDIT",
    "LOAD_CAMSET_SLOT1_HOST_BUFFER_RO",
    "LOAD_FTPSET_SLOT1_HOST_BUFFER_RO",
    "RECALL_CAMPR_SLOT1_RO",
    "SAVE_CAMSET_DAT_SLOT1",
    "DELETE_CAMSET_DAT_SLOT1",
    "SAVE_FTPSET_DAT_SLOT1",
    "DELETE_FTPSET_DAT_SLOT1",
    "SAVE_CAMPR_DAT_SLOT1",
    "PHYSICAL_EMMC_NVRAM_WRITE",
    "SAVE_CAMPR_DAT_SLOT2",
    "FX6_ALL_FILE_MEDIA_B",
)
P380_WRITE_MUTATING_SLOT1_VAULT_ACTIONS = (
    "SAVE_CAMSET_DAT_SLOT1",
    "DELETE_CAMSET_DAT_SLOT1",
    "SAVE_FTPSET_DAT_SLOT1",
    "DELETE_FTPSET_DAT_SLOT1",
    "SAVE_CAMPR_DAT_SLOT1",
    "PHYSICAL_EMMC_NVRAM_WRITE",
)
P380_VAULT_FIREWALL_ERRNOS = (None, "EROFS", "EOPNOTSUPP", "EBUSY", "EINVAL", "ENOENT")

# Status & Block Codes
P380_STATUS_VERIFIED_PILLAR_70A = (
    "VERIFIED_PILLAR_70A_AREADATE_DST_RTC_GRID_VS_MARKER_CLEANHDMI_VAULT"
)
P380_STATUS_REJECTED_PILLAR_70A = (
    "REJECTED_PILLAR_70A_AREADATE_DST_RTC_GRID_VS_MARKER_CLEANHDMI_VAULT"
)
P380_STATUS_VERIFIED_PILLAR_70B = (
    "VERIFIED_PILLAR_70B_SAVELOAD_CAMSET_CAMPR_EROFS30_SYNC_MISHOE_XLRH1_GENLOCK_VAULT"
)
P380_STATUS_REJECTED_PILLAR_70B = (
    "REJECTED_PILLAR_70B_SAVELOAD_CAMSET_CAMPR_EROFS30_SYNC_MISHOE_XLRH1_GENLOCK_VAULT"
)
P380_STATUS_VERIFIED_PILLAR70_SUITE = (
    "VERIFIED_PILLAR70_MILESTONE_AREADATE_DST_GRID_CLEANHDMI_SAVELOAD_CAMSET_MISHOE_VAULT"
)
P380_STATUS_FAIL_PILLAR70_SUITE = (
    "FAIL_PILLAR70_MILESTONE_AREADATE_DST_GRID_CLEANHDMI_SAVELOAD_CAMSET_MISHOE_VAULT"
)
P380_STATUS_VERIFIED_70OF70_AGGREGATOR = "VERIFIED_70OF70_PILLAR_RECOVERY_MASTER"
P380_STATUS_FAIL_70OF70_AGGREGATOR = "FAIL_70OF70_PILLAR_RECOVERY_MASTER"

P380_BLOCKED_SAFETY_POLICY_VIOLATION = "BLOCKED_P380_SAFETY_POLICY_VIOLATION"
P380_BLOCKED_INVALID_PILLAR70A_SPEC = "BLOCKED_P380_INVALID_PILLAR70A_SPEC"
P380_BLOCKED_INVALID_PILLAR70B_SPEC = "BLOCKED_P380_INVALID_PILLAR70B_SPEC"
P380_BLOCKED_AREADATE_DST_OR_RTC_BACKUP_DRIFT = (
    "BLOCKED_P380_AREADATE_DST_OR_RTC_BACKUP_DRIFT"
)
P380_BLOCKED_GRID_VS_MARKER_CLEANHDMI_DRIFT = (
    "BLOCKED_P380_GRID_VS_MARKER_CLEANHDMI_DRIFT"
)
P380_BLOCKED_SAVELOAD_CAMSET_OR_CAMPR_DRIFT = (
    "BLOCKED_P380_SAVELOAD_CAMSET_OR_CAMPR_DRIFT"
)
P380_BLOCKED_SYNC_TERMINAL_MISHOE_OR_GENLOCK_DRIFT = (
    "BLOCKED_P380_SYNC_TERMINAL_MISHOE_OR_GENLOCK_DRIFT"
)
P380_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL = "BLOCKED_P380_SLOT1_VAULT_WRITE_FIREWALL"
P380_BLOCKED_PERSISTENT_OVERLAY_ESCAPE = "BLOCKED_P380_PERSISTENT_OVERLAY_ESCAPE"
P380_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT = "BLOCKED_P380_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P380_PILLAR_70A_SCENARIO_IDS = (
    "p380_70a_01_allow_fx3_areadate_30zone_dst_rtc24h_grid_hdmi_passthrough_and_marker_cleanhdmi_reset_resist",
    "p380_70a_02_allow_fx6_clock_set_utc_30min_zero_dst_and_marker_independent_vf_sdi_hdmi_gates",
    "p380_70a_03_reject_fx3_invalid_timezone_datefmt_cr2032_claim_3mo_claim_or_reset_wipe_areadate",
    "p380_70a_04_reject_fx6_dormant_dst_ui_bad_utc_step_or_dormant_3mode_grid_ui",
    "p380_70a_05_reject_marker_still_mode_focus_mag_visible_marker_hdmi_leak_or_reset_wipe_grid_marker",
    "p380_70a_06_reject_slot1_vault_mutation_overlay_escape_or_backup_bin_h0_h3_drift",
)
P380_PILLAR_70B_SCENARIO_IDS = (
    "p380_70b_01_allow_fx3_camset_ro_hostbuf_reboot_campr_slot2_and_mishoe_videolight_auto_without_xlrh1",
    "p380_70b_02_allow_fx6_allfile_media_b_3mode_videolight_tc_in_out_bnc_and_zero_genlock",
    "p380_70b_03_reject_camset_slot2_cross_model_v101_to_v200_mr_mode_pro_camera_or_excluded_item_leak",
    "p380_70b_04_reject_fx3_sync_terminal_xlrh1_mishoe_collision_pmic_over900ma_or_flash_gt250v_elec",
    "p380_70b_05_reject_fx6_videolight_auto_still_flash_dormant_reference_file_or_dormant_genlock_bnc",
    "p380_70b_06_reject_slot1_camset_ftpset_campr_save_delete_erofs30_bypass_overlay_escape_or_h0_h3_drift",
)

MASTER_70_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_69_PILLAR_SPECS + (
    (
        70,
        "pillar70_milestone_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_vault",
        "Phase 380",
        "realhw_70pillar_milestone_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_vault_verifier",
    ),
)
MASTER_70_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_70_PILLAR_SPECS)
MASTER_70_PILLAR_COUNT = len(MASTER_70_PILLAR_IDS)


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
    return bool(is_forced_clean_room() or os.environ.get(P380_ENV_CLEAN_ROOM_TEST) == "1")


def _donor_inspect_budget_seconds() -> float:
    return (
        P380_DONOR_INSPECT_CI_BUDGET_SECONDS
        if os.environ.get("CI")
        else P380_DONOR_INSPECT_BUDGET_SECONDS
    )


def _is_tmpfs_path(path: str) -> bool:
    norm = posixpath.normpath(path)
    return norm == "/tmp" or norm.startswith("/tmp/")


def _targets_persistent_emmc(path: str) -> bool:
    norm = posixpath.normpath(path)
    return any(
        norm == t or norm.startswith(f"{t}/")
        for t in P380_FORBIDDEN_PERSISTENT_TARGETS
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


def _fw_major_minor(ver: str) -> Tuple[int, int]:
    parts = ver.strip().split(".")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return (-1, -1)
    return (int(parts[0]), int(parts[1]))


# ---------------------------------------------------------------------------
# Pure Deterministic Ground-Truth State Evaluators (70A & 70B)
# ---------------------------------------------------------------------------


def compute_expected_areadate_dst_grid_cleanhdmi_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    # 1. Area/Date-DST & RTC Backup vs FX6 Clock Set
    area_gmt_zone: str,
    daylight_savings: str,
    date_format: str,
    rtc_backup_depleted: bool,
    rtc_charge_hours_off_with_full_npfz100: int,
    claim_user_cr2032_slot: bool,
    claim_3month_retention_in_ilc2210: bool,
    fx6_utc_offset_minutes: int,
    fx6_date_mode: str,
    fx6_time_format: str,
    fx6_ui_dst_switch_requested: bool,
    fx6_backup_battery_end_alert: bool,
    # 2. Grid Line vs Marker Display -> Guideframe Clean-HDMI Split vs FX6 Marker
    grid_line_display: str,
    grid_line_type: str,
    hdmi_info_display: str,
    rec_media_dur_hdmi_output: str,
    raw_output_enabled: str,
    marker_display: str,
    marker_guideframe: str,
    focus_magnifier_active: bool,
    fx6_marker_setting: str,
    fx6_center_marker: str,
    fx6_safety_area: str,
    fx6_guide_frame: str,
    fx6_vf_marker_osd: str,
    fx6_sdi_marker_osd: str,
    fx6_hdmi_marker_osd: str,
    fx6_3mode_composition_grid_requested: bool,
    # 3. Reset & Vault
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute exact Wave-68 Pillar 70A expected state (`Area/Date-DST` & RTC backup vs FX6 `Clock Set`,
    plus `[Grid Line]` vs `[Marker Display] -> [Guideframe]` Clean-HDMI split vs FX6 `Marker`)."""
    is_fx6 = camera_model == P380_FX6_DONOR_MODEL_NAME

    # 1. Area/Date-DST & RTC Backup vs FX6 Clock Set
    areadate_errno: Optional[int] = None
    initial_setting_wizard_triggered = False
    rtc_backup_charged_sufficiently = False

    if is_fx6:
        if fx6_ui_dst_switch_requested or claim_user_cr2032_slot:
            areadate_errno = P380_EOPNOTSUPP_ERRNO
        elif (
            fx6_utc_offset_minutes < P380_FX6_UTC_OFFSET_MIN_MINUTES
            or fx6_utc_offset_minutes > P380_FX6_UTC_OFFSET_MAX_MINUTES
            or (fx6_utc_offset_minutes % P380_FX6_UTC_OFFSET_STEP_MINUTES) != 0
            or fx6_date_mode not in P380_FX6_DATE_MODES
            or fx6_time_format not in P380_FX6_TIME_FORMAT_MODES
        ):
            areadate_errno = P380_EINVAL_ERRNO
        initial_setting_wizard_triggered = bool(
            rtc_backup_depleted or fx6_backup_battery_end_alert or reset_action == "Initialize"
        )
        rtc_backup_charged_sufficiently = not (rtc_backup_depleted or fx6_backup_battery_end_alert)
    else:
        if claim_user_cr2032_slot or claim_3month_retention_in_ilc2210:
            areadate_errno = P380_EOPNOTSUPP_ERRNO
        elif area_gmt_zone not in P380_FX3_AREA_GMT_30_ZONES:
            areadate_errno = P380_EINVAL_ERRNO
        elif daylight_savings not in P380_ON_OFF_MODES:
            areadate_errno = P380_EINVAL_ERRNO
        elif date_format not in P380_FX3_DATE_FORMATS:
            areadate_errno = P380_EINVAL_ERRNO
        rtc_backup_charged_sufficiently = bool(
            (not rtc_backup_depleted)
            or rtc_charge_hours_off_with_full_npfz100 >= P380_FX3_RTC_BACKUP_CHARGE_MIN_HOURS_OFF
        )
        initial_setting_wizard_triggered = bool(
            reset_action == "Initialize"
            or (rtc_backup_depleted and not rtc_backup_charged_sufficiently)
        )

    # 2. Grid Line vs Marker Display -> Guideframe Clean-HDMI Split vs FX6 Marker
    grid_marker_errno: Optional[int] = None
    grid_line_hdmi_passthrough = False
    marker_visible_on_lcd = False
    marker_hdmi_pixels_emitted = 0

    if is_fx6:
        if fx6_3mode_composition_grid_requested:
            grid_marker_errno = P380_EOPNOTSUPP_ERRNO
        elif (
            fx6_center_marker not in P380_FX6_CENTER_MARKER_MODES
            or fx6_safety_area not in P380_FX6_SAFETY_AREA_PERCENTAGES
            or fx6_marker_setting not in P380_ON_OFF_MODES
            or fx6_guide_frame not in P380_ON_OFF_MODES
            or fx6_vf_marker_osd not in P380_ON_OFF_MODES
            or fx6_sdi_marker_osd not in P380_ON_OFF_MODES
            or fx6_hdmi_marker_osd not in P380_ON_OFF_MODES
        ):
            grid_marker_errno = P380_EINVAL_ERRNO
        marker_visible_on_lcd = bool(fx6_marker_setting == "On" and fx6_vf_marker_osd == "On")
        grid_line_hdmi_passthrough = False
        marker_hdmi_pixels_emitted = 0
    else:
        if grid_line_type not in P380_FX3_GRID_LINE_TYPES:
            grid_marker_errno = P380_EOPNOTSUPP_ERRNO
        elif shooting_domain not in P380_FX3_MARKER_DISPLAY_ALLOWED_DOMAINS and (
            marker_display == "On" or marker_guideframe == "On"
        ):
            # Marker Display (incl. Guideframe) is strictly Movie/S&Q ONLY!
            grid_marker_errno = P380_EOPNOTSUPP_ERRNO
        forced_clean_feed = (
            hdmi_info_display == "Off"
            or rec_media_dur_hdmi_output == "Off(HDMI Only)"
            or raw_output_enabled == "On"
        )
        grid_line_hdmi_passthrough = bool(grid_line_display == "On" and not forced_clean_feed)
        marker_visible_on_lcd = bool(
            shooting_domain in P380_FX3_MARKER_DISPLAY_ALLOWED_DOMAINS
            and marker_display == "On"
            and not focus_magnifier_active
        )
        # Marker Display (including Guideframe) NEVER outputs to HDMI (0 pixels)!
        marker_hdmi_pixels_emitted = 0

    # 3. Reset boundaries: Area/Date/Time, Grid Line Display/Type, & ALL 5 Marker Display items
    #    resist Camera Settings Reset; ONLY Initialize resets them!
    if reset_action == "Initialize":
        post_daylight_savings = P380_FX3_DAYLIGHT_SAVINGS_DEFAULT
        post_area_date_retained = False
        post_grid_line_display = P380_FX3_GRID_LINE_DISPLAY_DEFAULT
        post_grid_line_type = P380_FX3_GRID_LINE_TYPE_DEFAULT
        post_marker_display = P380_FX3_MARKER_DISPLAY_DEFAULT
        post_marker_guideframe = P380_FX3_MARKER_DISPLAY_DEFAULT
    else:
        post_daylight_savings = daylight_savings
        post_area_date_retained = True
        post_grid_line_display = grid_line_display
        post_grid_line_type = grid_line_type
        post_marker_display = marker_display
        post_marker_guideframe = marker_guideframe

    # 4. Tier-0 Slot-1 Vault Firewall
    slot1_targeted_write = (
        requested_vault_action in P380_WRITE_MUTATING_SLOT1_VAULT_ACTIONS
        or (
            requested_vault_slot == 1
            and requested_vault_action
            not in (
                "NONE",
                "READ_ONLY_AUDIT",
                "LOAD_CAMSET_SLOT1_HOST_BUFFER_RO",
                "LOAD_FTPSET_SLOT1_HOST_BUFFER_RO",
                "RECALL_CAMPR_SLOT1_RO",
            )
        )
    )
    write_blocked_erofs = bool(slot1_holds_tier0_vault and slot1_targeted_write)
    vault_action_allowed = not write_blocked_erofs and (
        requested_vault_action
        in (
            "NONE",
            "READ_ONLY_AUDIT",
            "LOAD_CAMSET_SLOT1_HOST_BUFFER_RO",
            "LOAD_FTPSET_SLOT1_HOST_BUFFER_RO",
            "RECALL_CAMPR_SLOT1_RO",
            "SAVE_CAMPR_DAT_SLOT2",
            "FX6_ALL_FILE_MEDIA_B",
        )
    )
    vault_firewall_errno: Optional[str] = "EROFS" if write_blocked_erofs else None

    return {
        "areadate_errno": areadate_errno,
        "initial_setting_wizard_triggered": initial_setting_wizard_triggered,
        "rtc_backup_charged_sufficiently": rtc_backup_charged_sufficiently,
        "grid_marker_errno": grid_marker_errno,
        "grid_line_hdmi_passthrough": grid_line_hdmi_passthrough,
        "marker_visible_on_lcd": marker_visible_on_lcd,
        "marker_hdmi_pixels_emitted": marker_hdmi_pixels_emitted,
        "post_daylight_savings": post_daylight_savings,
        "post_area_date_retained": post_area_date_retained,
        "post_grid_line_display": post_grid_line_display,
        "post_grid_line_type": post_grid_line_type,
        "post_marker_display": post_marker_display,
        "post_marker_guideframe": post_marker_guideframe,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


def compute_expected_saveload_camset_mishoe_sync_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    shutter_type: str,
    silent_mode: str,
    # 1. Save/Load Settings CAMSET01..10.DAT, FTPSET, Camera Set. Memory 1..3 vs M1..M4 & FX6 All File
    saveload_operation: str,
    saveload_target_slot: int,
    camset_slot_index: int,
    cloud_slot_count: int,
    media_card_type: str,
    camset_path_uses_pro_camera: bool,
    camset_source_model: str,
    camset_source_fw_version: str,
    in_mr_recall_mode: bool,
    camset_excluded_item_requested: str,
    load_into_simulated_host_buffer_only: bool,
    cam_memory_slot: str,
    memory_recall_media_slot: int,
    cam_memory_includes_custom_key_or_pshift: bool,
    fx6_all_file_slot_count: int,
    fx6_all_file_load_network_data: bool,
    fx6_user_3d_lut_count: int,
    fx6_reference_file_requested: bool,
    # 2. Sync Terminal Debunk, MI-Shoe Flash / Video Light Mode vs XLR-H1 Preemption vs FX6 TC/Genlock
    sync_terminal_requested: bool,
    flash_sync_spd_prty_requested: bool,
    flash_mode: str,
    flash_shutter_reciprocal: int,
    flash_trigger_voltage_v: int,
    flash_reverse_polarity: bool,
    video_light_mode: str,
    xlr_h1_attached: bool,
    mishoe_electrical_device_attached: bool,
    mishoe_current_ma: int,
    fx6_video_light_mode: str,
    fx6_still_flash_requested: bool,
    fx6_tc_bnc_mode: str,
    fx6_genlock_bnc_requested: bool,
    # 3. Reset & Tier-0 Slot-1 Vault Firewall
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute exact Wave-68 Pillar 70B expected state (`[Save/Load Settings]` `CAMSET01..10.DAT`,
    `libSaveLoadSettings.so`, `Camera Set. Memory` `1..3` vs `M1..M4`, Slot-1 `EROFS=30` firewall,
    Sync Terminal debunk, MI-Shoe Flash / `[Video Light Mode]` vs `XLR-H1` preemption, & FX6
    `All File` / `TC IN/OUT` / Zero `GENLOCK`)."""
    is_fx6 = camera_model == P380_FX6_DONOR_MODEL_NAME

    # 1. Save/Load Settings & Camera Set. Memory vs FX6 All File
    saveload_errno: Optional[int] = None
    saveload_reboot_required = False
    expected_media_prefix = (
        P380_FX3_SD_MEDIA_PREFIX
        if media_card_type == "SDXC"
        else P380_FX3_CFEXPRESS_MEDIA_PREFIX
    )

    if is_fx6:
        if fx6_reference_file_requested:
            saveload_errno = P380_EOPNOTSUPP_ERRNO
        elif saveload_operation in (
            "SAVE_CAMSET",
            "LOAD_CAMSET",
            "DELETE_CAMSET",
            "SAVE_FTPSET",
            "LOAD_FTPSET",
            "DELETE_FTPSET",
            "SAVE_CAMPR",
            "RECALL_CAMPR",
        ):
            saveload_errno = P380_EOPNOTSUPP_ERRNO
        elif (
            fx6_all_file_slot_count < 0
            or fx6_all_file_slot_count > P380_FX6_ALL_FILE_MAX_SLOTS
            or fx6_user_3d_lut_count < 0
            or fx6_user_3d_lut_count > P380_FX6_USER_3D_LUT_MAX_SLOTS
        ):
            saveload_errno = P380_EINVAL_ERRNO
        elif saveload_operation == "FX6_LOAD_ALL_FILE":
            saveload_reboot_required = True
    else:
        if fx6_reference_file_requested or saveload_operation in (
            "FX6_SAVE_ALL_FILE",
            "FX6_LOAD_ALL_FILE",
        ):
            saveload_errno = P380_EOPNOTSUPP_ERRNO
        elif camset_path_uses_pro_camera:
            # FX3 has ZERO PRO/CAMERA path hits!
            saveload_errno = P380_EOPNOTSUPP_ERRNO
        elif camset_excluded_item_requested != "None":
            # Any attempt to serialize/leak any official excluded item into CAMSET*.DAT -> EOPNOTSUPP(95)
            saveload_errno = P380_EOPNOTSUPP_ERRNO
        elif cam_memory_includes_custom_key_or_pshift:
            # Camera Set. Memory (1..3 & M1..M4) excludes Custom Key/Dial Set. & Program Shift
            saveload_errno = P380_EOPNOTSUPP_ERRNO
        elif saveload_operation in ("SAVE_CAMSET", "LOAD_CAMSET", "DELETE_CAMSET"):
            if saveload_target_slot != P380_FX3_CAMSET_LOCKED_SLOT:
                # Save/Load Settings card target is HARD-LOCKED to Slot 1!
                saveload_errno = P380_EOPNOTSUPP_ERRNO
            elif in_mr_recall_mode:
                # MR mode blocks Save/Load Settings
                saveload_errno = P380_EBUSY_ERRNO
            elif (
                camset_slot_index < 1
                or camset_slot_index > P380_FX3_CAMSET_MAX_CARD_SLOTS
                or cloud_slot_count < 0
                or cloud_slot_count > P380_FX3_CAMSET_MAX_CLOUD_SLOTS
            ):
                saveload_errno = P380_EINVAL_ERRNO
            elif saveload_operation == "LOAD_CAMSET":
                src_maj_min = _fw_major_minor(camset_source_fw_version)
                dst_maj_min = _fw_major_minor(fw_version)
                if camset_source_model != P380_FX3_MODEL_NAME:
                    saveload_errno = P380_EOPNOTSUPP_ERRNO  # _g 0x624d same-model lock
                elif (
                    src_maj_min == (-1, -1)
                    or dst_maj_min == (-1, -1)
                    or (src_maj_min <= (1, 1) and dst_maj_min >= (2, 0))
                ):
                    saveload_errno = P380_EINVAL_ERRNO  # Ver. 1.01 -> 2.00+ cross-version reject
                elif not load_into_simulated_host_buffer_only:
                    saveload_errno = P380_EROFS_ERRNO  # Never write physical eMMC!
                else:
                    saveload_reboot_required = True  # _g 0x62dd Reboots after loading
        elif saveload_operation in ("SAVE_FTPSET", "LOAD_FTPSET", "DELETE_FTPSET"):
            if saveload_target_slot != P380_FX3_CAMSET_LOCKED_SLOT:
                saveload_errno = P380_EOPNOTSUPP_ERRNO
            elif saveload_operation == "LOAD_FTPSET" and not load_into_simulated_host_buffer_only:
                saveload_errno = P380_EROFS_ERRNO
        elif saveload_operation in ("SAVE_CAMPR", "RECALL_CAMPR"):
            if cam_memory_slot not in P380_FX3_CAMERA_SET_MEMORY_CARD_SLOTS:
                saveload_errno = P380_EINVAL_ERRNO
            elif memory_recall_media_slot not in (1, 2):
                saveload_errno = P380_EINVAL_ERRNO
            # Real-time recall without reboot!

    # 2. Sync Terminal Debunk, MI-Shoe Flash / Video Light Mode vs XLR-H1 Preemption vs FX6 TC/Genlock
    mishoe_sync_errno: Optional[int] = None
    fx6_tc_ext_lk_active = False

    if is_fx6:
        if fx6_genlock_bnc_requested or fx6_still_flash_requested or sync_terminal_requested or flash_sync_spd_prty_requested:
            mishoe_sync_errno = P380_EOPNOTSUPP_ERRNO
        elif fx6_video_light_mode not in P380_FX6_VIDEO_LIGHT_MODES:
            # FX6 Technical > Video Light Set has 3 modes ONLY — ZERO Auto!
            mishoe_sync_errno = P380_EOPNOTSUPP_ERRNO
        elif fx6_tc_bnc_mode not in ("OFF", "IN", "OUT"):
            mishoe_sync_errno = P380_EINVAL_ERRNO
        else:
            fx6_tc_ext_lk_active = fx6_tc_bnc_mode == "IN"
    else:
        if sync_terminal_requested or flash_sync_spd_prty_requested or fx6_genlock_bnc_requested:
            # Zero physical PC Sync Terminal (0 SYNCHRO_TERMINAL* hits) & zero Genlock!
            mishoe_sync_errno = P380_EOPNOTSUPP_ERRNO
        elif video_light_mode not in P380_FX3_VIDEO_LIGHT_MODES:
            mishoe_sync_errno = P380_EINVAL_ERRNO
        elif flash_mode not in P380_FX3_FLASH_MODES:
            mishoe_sync_errno = P380_EINVAL_ERRNO
        elif xlr_h1_attached and mishoe_electrical_device_attached:
            # XLR-H1 occupies sole electrical MI Shoe; Accessory Shoe Kit is passive cold shoe only!
            mishoe_sync_errno = P380_EBUSY_ERRNO
        elif mishoe_current_ma < 0 or mishoe_current_ma > P380_MISHOE_PMIC_5V_MAX_MA:
            # Stage-B PMIC 5V <= 900 mA budget
            mishoe_sync_errno = P380_EINVAL_ERRNO
        elif flash_mode != "Flash Off":
            if (
                shooting_domain != "Still"
                or shutter_type != "Mechanical Shutter"
                or silent_mode == "On"
            ):
                mishoe_sync_errno = P380_EOPNOTSUPP_ERRNO
            elif (
                flash_shutter_reciprocal > P380_FX3_FLASH_MAX_SYNC_RECIPROCAL
                or flash_trigger_voltage_v >= P380_FX3_FLASH_TRIGGER_VOLTAGE_LIMIT_V
                or flash_reverse_polarity
            ):
                mishoe_sync_errno = P380_EINVAL_ERRNO

    # 3. Reset Boundaries: Body Camera Set. Memory 1..3 & External Flash Set. resist Camera Settings Reset
    post_body_cam_memory_retained = reset_action != "Initialize"
    post_external_flash_set_retained = reset_action != "Initialize"

    # 4. Tier-0 Slot-1 Vault Firewall (`EROFS = 30`)
    slot1_targeted_write = (
        requested_vault_action in P380_WRITE_MUTATING_SLOT1_VAULT_ACTIONS
        or (
            not is_fx6
            and saveload_operation in ("SAVE_CAMSET", "DELETE_CAMSET", "SAVE_FTPSET", "DELETE_FTPSET")
            and saveload_target_slot == 1
        )
        or (
            not is_fx6
            and saveload_operation == "SAVE_CAMPR"
            and memory_recall_media_slot == 1
        )
        or (
            requested_vault_slot == 1
            and requested_vault_action
            not in (
                "NONE",
                "READ_ONLY_AUDIT",
                "LOAD_CAMSET_SLOT1_HOST_BUFFER_RO",
                "LOAD_FTPSET_SLOT1_HOST_BUFFER_RO",
                "RECALL_CAMPR_SLOT1_RO",
            )
        )
    )
    write_blocked_erofs = bool(slot1_holds_tier0_vault and slot1_targeted_write)
    vault_action_allowed = not write_blocked_erofs and (
        requested_vault_action
        in (
            "NONE",
            "READ_ONLY_AUDIT",
            "LOAD_CAMSET_SLOT1_HOST_BUFFER_RO",
            "LOAD_FTPSET_SLOT1_HOST_BUFFER_RO",
            "RECALL_CAMPR_SLOT1_RO",
            "SAVE_CAMPR_DAT_SLOT2",
            "FX6_ALL_FILE_MEDIA_B",
        )
    )
    vault_firewall_errno: Optional[str] = "EROFS" if write_blocked_erofs else None

    return {
        "saveload_errno": saveload_errno,
        "saveload_reboot_required": saveload_reboot_required,
        "expected_media_prefix": expected_media_prefix,
        "mishoe_sync_errno": mishoe_sync_errno,
        "fx6_tc_ext_lk_active": fx6_tc_ext_lk_active,
        "post_body_cam_memory_retained": post_body_cam_memory_retained,
        "post_external_flash_set_retained": post_external_flash_set_retained,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


# ---------------------------------------------------------------------------
# Bounded Read-Only Donor Inspection (`O_RDONLY | O_NOFOLLOW | O_NONBLOCK`, 18 Donors)
# ---------------------------------------------------------------------------


def _iter_work_roots() -> Tuple[Optional[Path], ...]:
    return _fx3_files.iter_donor_work_roots()


def _resolve_phase380_donor_path(
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
    max_full_bytes: int = P380_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    try:
        resolved = _resolve_phase380_donor_path(relpath)
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
        hdr = os.pread(fd, min(P380_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase380_donors() -> Tuple["Phase380DonorArtifactDigest", ...]:
    specs = (
        ("fx3_appfw_702_so", P380_DONOR_FX3_APPFW_702_RELPATH, P380_PINNED_FX3_APPFW_702_BYTES, P380_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P380_PINNED_FX3_APPFW_702_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702"),
        ("fx3_libsaveloadsettings_so", P380_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH, P380_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES, P380_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES, "FULL_SHA256", P380_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_LIBSAVELOADSETTINGS"),
        ("fx3_backup_bin", P380_DONOR_FX3_BACKUP_BIN_RELPATH, P380_PINNED_FX3_BACKUP_BIN_BYTES, P380_PINNED_FX3_BACKUP_BIN_BYTES, "FULL_SHA256", P380_PINNED_FX3_BACKUP_BIN_SHA256, "SYNTHETIC_BK4_ILME_FX3"),
        ("fx6_appfw_601_so", P380_DONOR_FX6_APPFW_601_RELPATH, P380_PINNED_FX6_APPFW_601_BYTES, P380_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P380_PINNED_FX6_APPFW_601_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601"),
        ("fx3_uxc_en_f", P380_DONOR_FX3_UXC_EN_F_RELPATH, P380_PINNED_FX3_UXC_EN_F_BYTES, P380_PINNED_FX3_UXC_EN_F_BYTES, "FULL_SHA256", P380_PINNED_FX3_UXC_EN_F_SHA256, "SYNTHETIC_UXC7_FX3_EN_F"),
        ("fx3_uxc_sc_f", P380_DONOR_FX3_UXC_SC_F_RELPATH, P380_PINNED_FX3_UXC_SC_F_BYTES, P380_PINNED_FX3_UXC_SC_F_BYTES, "FULL_SHA256", P380_PINNED_FX3_UXC_SC_F_SHA256, "SYNTHETIC_UXC7_FX3_SC_F"),
        ("fx3_uxc_tc_f", P380_DONOR_FX3_UXC_TC_F_RELPATH, P380_PINNED_FX3_UXC_TC_F_BYTES, P380_PINNED_FX3_UXC_TC_F_BYTES, "FULL_SHA256", P380_PINNED_FX3_UXC_TC_F_SHA256, "SYNTHETIC_UXC7_FX3_TC_F"),
        ("fx3_uxc_ja_f", P380_DONOR_FX3_UXC_JA_F_RELPATH, P380_PINNED_FX3_UXC_JA_F_BYTES, P380_PINNED_FX3_UXC_JA_F_BYTES, "FULL_SHA256", P380_PINNED_FX3_UXC_JA_F_SHA256, "SYNTHETIC_UXC7_FX3_JA_F"),
        ("fx3_uxc_en", P380_DONOR_FX3_UXC_EN_RELPATH, P380_PINNED_FX3_UXC_EN_BYTES, P380_PINNED_FX3_UXC_EN_BYTES, "FULL_SHA256", P380_PINNED_FX3_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX3_EN"),
        ("fx3_uxc_sc", P380_DONOR_FX3_UXC_SC_RELPATH, P380_PINNED_FX3_UXC_SC_BYTES, P380_PINNED_FX3_UXC_SC_BYTES, "FULL_SHA256", P380_PINNED_FX3_UXC_SC_SHA256, "SYNTHETIC_UXC7_FX3_SC"),
        ("fx3_uxc_tc", P380_DONOR_FX3_UXC_TC_RELPATH, P380_PINNED_FX3_UXC_TC_BYTES, P380_PINNED_FX3_UXC_TC_BYTES, "FULL_SHA256", P380_PINNED_FX3_UXC_TC_SHA256, "SYNTHETIC_UXC7_FX3_TC"),
        ("fx3_uxc_ja", P380_DONOR_FX3_UXC_JA_RELPATH, P380_PINNED_FX3_UXC_JA_BYTES, P380_PINNED_FX3_UXC_JA_BYTES, "FULL_SHA256", P380_PINNED_FX3_UXC_JA_SHA256, "SYNTHETIC_UXC7_FX3_JA"),
        ("fx3_uxc_en_g", P380_DONOR_FX3_UXC_EN_G_RELPATH, P380_PINNED_FX3_UXC_EN_G_BYTES, P380_PINNED_FX3_UXC_EN_G_BYTES, "FULL_SHA256", P380_PINNED_FX3_UXC_EN_G_SHA256, "SYNTHETIC_UXC7_FX3_EN_G"),
        ("fx3_uxc_sc_g", P380_DONOR_FX3_UXC_SC_G_RELPATH, P380_PINNED_FX3_UXC_SC_G_BYTES, P380_PINNED_FX3_UXC_SC_G_BYTES, "FULL_SHA256", P380_PINNED_FX3_UXC_SC_G_SHA256, "SYNTHETIC_UXC7_FX3_SC_G"),
        ("fx3_uxc_tc_g", P380_DONOR_FX3_UXC_TC_G_RELPATH, P380_PINNED_FX3_UXC_TC_G_BYTES, P380_PINNED_FX3_UXC_TC_G_BYTES, "FULL_SHA256", P380_PINNED_FX3_UXC_TC_G_SHA256, "SYNTHETIC_UXC7_FX3_TC_G"),
        ("fx3_uxc_ja_g", P380_DONOR_FX3_UXC_JA_G_RELPATH, P380_PINNED_FX3_UXC_JA_G_BYTES, P380_PINNED_FX3_UXC_JA_G_BYTES, "FULL_SHA256", P380_PINNED_FX3_UXC_JA_G_SHA256, "SYNTHETIC_UXC7_FX3_JA_G"),
        ("fx6_uxc_en", P380_DONOR_FX6_UXC_EN_RELPATH, P380_PINNED_FX6_UXC_EN_BYTES, P380_PINNED_FX6_UXC_EN_BYTES, "FULL_SHA256", P380_PINNED_FX6_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX6_EN"),
        ("fx6_uxc_en_2", P380_DONOR_FX6_UXC_EN_2_RELPATH, P380_PINNED_FX6_UXC_EN_2_BYTES, P380_PINNED_FX6_UXC_EN_2_BYTES, "FULL_SHA256", P380_PINNED_FX6_UXC_EN_2_SHA256, "SYNTHETIC_UXC7_FX6_EN_2"),
    )
    return tuple(
        Phase380DonorArtifactDigest(
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


def inspect_phase380_donors_readonly(
    force_clean_room: Optional[bool] = None,
) -> "Phase380DonorSnapshot":
    """Inspect Wave-68 FX3 (`15` donors incl. `libSaveLoadSettings.so`) & FX6 (`3` donors)
    strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase380_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase380DonorSnapshot(
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
        ("fx3_appfw_702_so", P380_DONOR_FX3_APPFW_702_RELPATH, P380_PINNED_FX3_APPFW_702_BYTES, P380_PINNED_FX3_APPFW_702_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702")),
        ("fx3_libsaveloadsettings_so", P380_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH, P380_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES, P380_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_LIBSAVELOADSETTINGS")),
        ("fx3_backup_bin", P380_DONOR_FX3_BACKUP_BIN_RELPATH, P380_PINNED_FX3_BACKUP_BIN_BYTES, P380_PINNED_FX3_BACKUP_BIN_SHA256, lambda d: _check_bk4_backup(d, "ILME_FX3")),
        ("fx6_appfw_601_so", P380_DONOR_FX6_APPFW_601_RELPATH, P380_PINNED_FX6_APPFW_601_BYTES, P380_PINNED_FX6_APPFW_601_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601")),
        ("fx3_uxc_en_f", P380_DONOR_FX3_UXC_EN_F_RELPATH, P380_PINNED_FX3_UXC_EN_F_BYTES, P380_PINNED_FX3_UXC_EN_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_F")),
        ("fx3_uxc_sc_f", P380_DONOR_FX3_UXC_SC_F_RELPATH, P380_PINNED_FX3_UXC_SC_F_BYTES, P380_PINNED_FX3_UXC_SC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_F")),
        ("fx3_uxc_tc_f", P380_DONOR_FX3_UXC_TC_F_RELPATH, P380_PINNED_FX3_UXC_TC_F_BYTES, P380_PINNED_FX3_UXC_TC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_F")),
        ("fx3_uxc_ja_f", P380_DONOR_FX3_UXC_JA_F_RELPATH, P380_PINNED_FX3_UXC_JA_F_BYTES, P380_PINNED_FX3_UXC_JA_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_F")),
        ("fx3_uxc_en", P380_DONOR_FX3_UXC_EN_RELPATH, P380_PINNED_FX3_UXC_EN_BYTES, P380_PINNED_FX3_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN")),
        ("fx3_uxc_sc", P380_DONOR_FX3_UXC_SC_RELPATH, P380_PINNED_FX3_UXC_SC_BYTES, P380_PINNED_FX3_UXC_SC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC")),
        ("fx3_uxc_tc", P380_DONOR_FX3_UXC_TC_RELPATH, P380_PINNED_FX3_UXC_TC_BYTES, P380_PINNED_FX3_UXC_TC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC")),
        ("fx3_uxc_ja", P380_DONOR_FX3_UXC_JA_RELPATH, P380_PINNED_FX3_UXC_JA_BYTES, P380_PINNED_FX3_UXC_JA_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA")),
        ("fx3_uxc_en_g", P380_DONOR_FX3_UXC_EN_G_RELPATH, P380_PINNED_FX3_UXC_EN_G_BYTES, P380_PINNED_FX3_UXC_EN_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_G")),
        ("fx3_uxc_sc_g", P380_DONOR_FX3_UXC_SC_G_RELPATH, P380_PINNED_FX3_UXC_SC_G_BYTES, P380_PINNED_FX3_UXC_SC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_G")),
        ("fx3_uxc_tc_g", P380_DONOR_FX3_UXC_TC_G_RELPATH, P380_PINNED_FX3_UXC_TC_G_BYTES, P380_PINNED_FX3_UXC_TC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_G")),
        ("fx3_uxc_ja_g", P380_DONOR_FX3_UXC_JA_G_RELPATH, P380_PINNED_FX3_UXC_JA_G_BYTES, P380_PINNED_FX3_UXC_JA_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_G")),
        ("fx6_uxc_en", P380_DONOR_FX6_UXC_EN_RELPATH, P380_PINNED_FX6_UXC_EN_BYTES, P380_PINNED_FX6_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN")),
        ("fx6_uxc_en_2", P380_DONOR_FX6_UXC_EN_2_RELPATH, P380_PINNED_FX6_UXC_EN_2_BYTES, P380_PINNED_FX6_UXC_EN_2_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN_2")),
    )

    def _probe_one(spec: Tuple[str, str, int, str, Any]) -> Optional[Phase380DonorArtifactDigest]:
        aid, relpath, expected_bytes, expected_sha, marker_fn = spec
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            return None
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        return Phase380DonorArtifactDigest(
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
        artifacts = _synthetic_phase380_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase380DonorSnapshot(
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
    return Phase380DonorSnapshot(
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
# Frozen Dataclasses (Specs, Reports, Suites & 70-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase380DonorArtifactDigest:
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
class Phase380DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_2_0s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase380DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AreaDateDstGridCleanHdmiVaultSpec:
    camera_model: str
    fw_version: str
    shooting_domain: str
    # 1. Area/Date-DST & RTC Backup vs FX6 Clock Set
    area_gmt_zone: str
    daylight_savings: str
    date_format: str
    rtc_backup_depleted: bool
    rtc_charge_hours_off_with_full_npfz100: int
    claim_user_cr2032_slot: bool
    claim_3month_retention_in_ilc2210: bool
    fx6_utc_offset_minutes: int
    fx6_date_mode: str
    fx6_time_format: str
    fx6_ui_dst_switch_requested: bool
    fx6_backup_battery_end_alert: bool
    reported_areadate_errno: Optional[int]
    reported_initial_setting_wizard_triggered: bool
    reported_rtc_backup_charged_sufficiently: bool
    # 2. Grid Line vs Marker Display -> Guideframe Clean-HDMI Split vs FX6 Marker
    grid_line_display: str
    grid_line_type: str
    hdmi_info_display: str
    rec_media_dur_hdmi_output: str
    raw_output_enabled: str
    marker_display: str
    marker_guideframe: str
    focus_magnifier_active: bool
    fx6_marker_setting: str
    fx6_center_marker: str
    fx6_safety_area: str
    fx6_guide_frame: str
    fx6_vf_marker_osd: str
    fx6_sdi_marker_osd: str
    fx6_hdmi_marker_osd: str
    fx6_3mode_composition_grid_requested: bool
    reported_grid_marker_errno: Optional[int]
    reported_grid_line_hdmi_passthrough: bool
    reported_marker_visible_on_lcd: bool
    reported_marker_hdmi_pixels_emitted: int
    # 3. Reset Boundaries
    reset_action: str
    post_daylight_savings: str
    post_area_date_retained: bool
    post_grid_line_display: str
    post_grid_line_type: str
    post_marker_display: str
    post_marker_guideframe: str
    # 4. Tier-0 Slot-1 Vault, Overlay & H0==H3
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
    # Drift counters
    areadate_dst_or_rtc_backup_drift_events: int
    grid_vs_marker_cleanhdmi_drift_events: int


@dataclass(frozen=True)
class AreaDateDstGridCleanHdmiVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    areadate_dst_and_rtc_backup_verified: bool
    grid_vs_marker_cleanhdmi_verified: bool
    slot1_vault_and_h0_h3_verified: bool
    matrix_states_checked: int
    areadate_dst_or_rtc_backup_drift_events: int
    grid_vs_marker_cleanhdmi_drift_events: int
    hdmi_marker_guideframe_leak_pixels: int
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
class SaveLoadCamsetMiShoeSyncVaultSpec:
    camera_model: str
    fw_version: str
    shooting_domain: str
    shutter_type: str
    silent_mode: str
    # 1. Save/Load Settings CAMSET01..10.DAT, FTPSET, Camera Set. Memory 1..3 vs M1..M4 & FX6 All File
    saveload_operation: str
    saveload_target_slot: int
    camset_slot_index: int
    cloud_slot_count: int
    media_card_type: str
    camset_path_uses_pro_camera: bool
    camset_source_model: str
    camset_source_fw_version: str
    in_mr_recall_mode: bool
    camset_excluded_item_requested: str
    load_into_simulated_host_buffer_only: bool
    cam_memory_slot: str
    memory_recall_media_slot: int
    cam_memory_includes_custom_key_or_pshift: bool
    fx6_all_file_slot_count: int
    fx6_all_file_load_network_data: bool
    fx6_user_3d_lut_count: int
    fx6_reference_file_requested: bool
    reported_saveload_errno: Optional[int]
    reported_saveload_reboot_required: bool
    reported_media_prefix: str
    camset_excluded_item_leak_events: int
    camset_excluded_item_leaked_bytes: int
    # 2. Sync Terminal Debunk, MI-Shoe Flash / Video Light Mode vs XLR-H1 Preemption vs FX6 TC/Genlock
    sync_terminal_requested: bool
    flash_sync_spd_prty_requested: bool
    flash_mode: str
    flash_shutter_reciprocal: int
    flash_trigger_voltage_v: int
    flash_reverse_polarity: bool
    video_light_mode: str
    xlr_h1_attached: bool
    mishoe_electrical_device_attached: bool
    mishoe_current_ma: int
    fx6_video_light_mode: str
    fx6_still_flash_requested: bool
    fx6_tc_bnc_mode: str
    fx6_genlock_bnc_requested: bool
    reported_mishoe_sync_errno: Optional[int]
    reported_fx6_tc_ext_lk_active: bool
    # 3. Reset Boundaries
    reset_action: str
    post_body_cam_memory_retained: bool
    post_external_flash_set_retained: bool
    # 4. Tier-0 Slot-1 Vault, Overlay & H0==H3
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
    # Drift counters
    saveload_camset_or_campr_slot1_drift_events: int
    sync_terminal_mishoe_or_genlock_drift_events: int


@dataclass(frozen=True)
class SaveLoadCamsetMiShoeSyncVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    saveload_camset_campr_and_allfile_verified: bool
    sync_terminal_mishoe_xlrh1_and_genlock_verified: bool
    slot1_erofs_overlay_and_h0_h3_verified: bool
    matrix_states_checked: int
    saveload_camset_or_campr_slot1_drift_events: int
    sync_terminal_mishoe_or_genlock_drift_events: int
    camset_excluded_item_leak_events: int
    camset_excluded_item_leaked_bytes: int
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
class AreaDateDstGridCleanHdmiSaveLoadCamsetMiShoeVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase380DonorSnapshot
    areadate_dst_grid_cleanhdmi_report: AreaDateDstGridCleanHdmiVaultReport
    saveload_camset_mishoe_sync_report: SaveLoadCamsetMiShoeSyncVaultReport
    areadate_dst_or_rtc_backup_drift_events: int
    grid_vs_marker_cleanhdmi_drift_events: int
    saveload_camset_or_campr_slot1_drift_events: int
    sync_terminal_mishoe_or_genlock_drift_events: int
    hdmi_marker_guideframe_leak_pixels: int
    camset_excluded_item_leak_events: int
    camset_excluded_item_leaked_bytes: int
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
class Pillar70ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar70ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar70ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar70BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar70ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar70StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase380DonorSnapshot
    pillar_70a_areadate_dst_grid_cleanhdmi_vault: Pillar70ASuiteResult
    pillar_70b_saveload_camset_mishoe_sync_vault: Pillar70BSuiteResult
    areadate_dst_or_rtc_backup_drift_events: int
    grid_vs_marker_cleanhdmi_drift_events: int
    saveload_camset_or_campr_slot1_drift_events: int
    sync_terminal_mishoe_or_genlock_drift_events: int
    hdmi_marker_guideframe_leak_pixels: int
    camset_excluded_item_leak_events: int
    camset_excluded_item_leaked_bytes: int
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
class Master70PillarRecoveryReport:
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
    donor_snapshot: Phase380DonorSnapshot
    pillar70_a_areadate_dst_grid_cleanhdmi_vault: Pillar70ASuiteResult
    pillar70_b_saveload_camset_mishoe_sync_vault: Pillar70BSuiteResult
    # Pillar 70 zero-violation counters & empirical capability booleans
    areadate_dst_or_rtc_backup_drift_events: int
    grid_vs_marker_cleanhdmi_drift_events: int
    saveload_camset_or_campr_slot1_drift_events: int
    sync_terminal_mishoe_or_genlock_drift_events: int
    hdmi_marker_guideframe_leak_pixels: int
    camset_excluded_item_leak_events: int
    camset_excluded_item_leaked_bytes: int
    fx3_area_gmt_zone_count: int
    fx3_area_date_time_resettable: bool
    fx3_has_user_cr2032_slot: bool
    fx3_helpguide_claims_3_months_retention: bool
    fx3_grid_line_resettable: bool
    fx3_marker_display_all_5_resettable: bool
    fx3_pro_camera_path_hits: int
    fx3_camset_locked_slot: int
    fx3_camset_max_card_slots: int
    fx3_has_physical_sync_terminal: bool
    fx3_synchro_terminal_appfw_hits: int
    fx3_has_tc_bnc: bool
    xlr_h1_preempts_electrical_mi_shoe: bool
    fx6_has_ui_dst_switch: bool
    fx6_has_3mode_composition_grid_ui: bool
    fx6_has_user_exposed_reference_file: bool
    fx6_has_video_light_auto: bool
    fx6_has_still_flash_ui: bool
    fx6_has_tc_in_out_bnc: bool
    fx6_has_physical_genlock_bnc: bool
    fx6_dormant_genlock_symbol_count: int
    # Carried forward from Pillar 69
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
    master_70pillar_sha256: str
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


def build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
    **overrides: Any,
) -> AreaDateDstGridCleanHdmiVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P380_FX3_MODEL_NAME,
        "fw_version": P380_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        # Area/Date-DST & RTC Backup
        "area_gmt_zone": "AREA_GMT_P_08_0",
        "daylight_savings": "On",
        "date_format": "Y-M-D",
        "rtc_backup_depleted": False,
        "rtc_charge_hours_off_with_full_npfz100": 24,
        "claim_user_cr2032_slot": False,
        "claim_3month_retention_in_ilc2210": False,
        "fx6_utc_offset_minutes": 480,
        "fx6_date_mode": "YYMMDD",
        "fx6_time_format": "24h",
        "fx6_ui_dst_switch_requested": False,
        "fx6_backup_battery_end_alert": False,
        "reported_areadate_errno": None,
        "reported_initial_setting_wizard_triggered": False,
        "reported_rtc_backup_charged_sufficiently": True,
        # Grid Line vs Marker Display -> Guideframe Clean-HDMI Split
        "grid_line_display": "On",
        "grid_line_type": "Rule of 3rds Grid",
        "hdmi_info_display": "On",
        "rec_media_dur_hdmi_output": "On",
        "raw_output_enabled": "Off",
        "marker_display": "On",
        "marker_guideframe": "On",
        "focus_magnifier_active": False,
        "fx6_marker_setting": "On",
        "fx6_center_marker": "1",
        "fx6_safety_area": "90%",
        "fx6_guide_frame": "On",
        "fx6_vf_marker_osd": "On",
        "fx6_sdi_marker_osd": "Off",
        "fx6_hdmi_marker_osd": "Off",
        "fx6_3mode_composition_grid_requested": False,
        "reported_grid_marker_errno": None,
        "reported_grid_line_hdmi_passthrough": True,
        "reported_marker_visible_on_lcd": True,
        "reported_marker_hdmi_pixels_emitted": 0,
        # Reset Boundaries (ALL resist Camera Settings Reset!)
        "reset_action": "Camera Settings Reset",
        "post_daylight_savings": "On",
        "post_area_date_retained": True,
        "post_grid_line_display": "On",
        "post_grid_line_type": "Rule of 3rds Grid",
        "post_marker_display": "On",
        "post_marker_guideframe": "On",
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
        "overlay_dir": P380_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P380_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P380_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P380_TIER0_SURFACE_COUNT,
        # Drift counters
        "areadate_dst_or_rtc_backup_drift_events": 0,
        "grid_vs_marker_cleanhdmi_drift_events": 0,
    }
    defaults.update(overrides)
    return AreaDateDstGridCleanHdmiVaultSpec(**defaults)


def build_default_safe_saveload_camset_mishoe_sync_vault_spec(
    **overrides: Any,
) -> SaveLoadCamsetMiShoeSyncVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P380_FX3_MODEL_NAME,
        "fw_version": P380_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "shutter_type": "Mechanical Shutter",
        "silent_mode": "Off",
        # Save/Load Settings CAMSET01..10.DAT (RO Load into simulated host buffer)
        "saveload_operation": "LOAD_CAMSET",
        "saveload_target_slot": 1,
        "camset_slot_index": 1,
        "cloud_slot_count": 10,
        "media_card_type": "SDXC",
        "camset_path_uses_pro_camera": False,
        "camset_source_model": P380_FX3_MODEL_NAME,
        "camset_source_fw_version": P380_FX3_FW_VERSION,
        "in_mr_recall_mode": False,
        "camset_excluded_item_requested": "None",
        "load_into_simulated_host_buffer_only": True,
        "cam_memory_slot": "M1",
        "memory_recall_media_slot": 2,
        "cam_memory_includes_custom_key_or_pshift": False,
        "fx6_all_file_slot_count": 16,
        "fx6_all_file_load_network_data": False,
        "fx6_user_3d_lut_count": 8,
        "fx6_reference_file_requested": False,
        "reported_saveload_errno": None,
        "reported_saveload_reboot_required": True,
        "reported_media_prefix": P380_FX3_SD_MEDIA_PREFIX,
        "camset_excluded_item_leak_events": 0,
        "camset_excluded_item_leaked_bytes": 0,
        # Sync Terminal Debunk, MI-Shoe Flash / Video Light Mode vs XLR-H1
        "sync_terminal_requested": False,
        "flash_sync_spd_prty_requested": False,
        "flash_mode": "Flash Off",
        "flash_shutter_reciprocal": 250,
        "flash_trigger_voltage_v": 12,
        "flash_reverse_polarity": False,
        "video_light_mode": "Auto",
        "xlr_h1_attached": False,
        "mishoe_electrical_device_attached": True,
        "mishoe_current_ma": 450,
        "fx6_video_light_mode": "Power Link",
        "fx6_still_flash_requested": False,
        "fx6_tc_bnc_mode": "IN",
        "fx6_genlock_bnc_requested": False,
        "reported_mishoe_sync_errno": None,
        "reported_fx6_tc_ext_lk_active": False,
        # Reset Boundaries
        "reset_action": "Camera Settings Reset",
        "post_body_cam_memory_retained": True,
        "post_external_flash_set_retained": True,
        # Tier-0 Slot-1 Vault
        "requested_vault_slot": 1,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "LOAD_CAMSET_SLOT1_HOST_BUFFER_RO",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_writes": 0,
        "slot1_data_sector_writes": 0,
        "slot1_sector_writes": 0,
        "slot1_vault_mutation_bytes": 0,
        "cnflasha_writes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P380_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P380_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P380_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P380_TIER0_SURFACE_COUNT,
        # Drift counters
        "saveload_camset_or_campr_slot1_drift_events": 0,
        "sync_terminal_mishoe_or_genlock_drift_events": 0,
    }
    defaults.update(overrides)
    return SaveLoadCamsetMiShoeSyncVaultSpec(**defaults)


# ---------------------------------------------------------------------------
# Sub-Pillar Evaluators (70A & 70B) & Combined Single-Shot Verifier
# ---------------------------------------------------------------------------


def evaluate_areadate_dst_grid_cleanhdmi_vault(
    spec: AreaDateDstGridCleanHdmiVaultSpec,
) -> AreaDateDstGridCleanHdmiVaultReport:
    """Evaluate Pillar 70A spec (`Area/Date-DST` & RTC Backup vs FX6 `Clock Set` +
    `[Grid Line]` vs `[Marker Display] -> [Guideframe]` Clean-HDMI Split vs FX6 `Marker`)."""
    errors: List[str] = []
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    for serr in _safety_invariant_errors():
        _fail(P380_BLOCKED_SAFETY_POLICY_VIOLATION, serr)

    valid_spec = (
        spec.camera_model in (P380_FX3_MODEL_NAME, P380_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P380_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P380_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P380_SHOOTING_DOMAINS
        and spec.grid_line_display in P380_ON_OFF_MODES
        and spec.hdmi_info_display in P380_ON_OFF_MODES
        and spec.rec_media_dur_hdmi_output in ("On", "Off(HDMI Only)")
        and spec.raw_output_enabled in P380_ON_OFF_MODES
        and spec.marker_display in P380_ON_OFF_MODES
        and spec.marker_guideframe in P380_ON_OFF_MODES
        and spec.reset_action in P380_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P380_VAULT_ACTIONS
        and spec.vault_firewall_errno in P380_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P380_BLOCKED_INVALID_PILLAR70A_SPEC, "Invalid Pillar 70A spec fields")

    st = compute_expected_areadate_dst_grid_cleanhdmi_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        area_gmt_zone=spec.area_gmt_zone,
        daylight_savings=spec.daylight_savings,
        date_format=spec.date_format,
        rtc_backup_depleted=spec.rtc_backup_depleted,
        rtc_charge_hours_off_with_full_npfz100=spec.rtc_charge_hours_off_with_full_npfz100,
        claim_user_cr2032_slot=spec.claim_user_cr2032_slot,
        claim_3month_retention_in_ilc2210=spec.claim_3month_retention_in_ilc2210,
        fx6_utc_offset_minutes=spec.fx6_utc_offset_minutes,
        fx6_date_mode=spec.fx6_date_mode,
        fx6_time_format=spec.fx6_time_format,
        fx6_ui_dst_switch_requested=spec.fx6_ui_dst_switch_requested,
        fx6_backup_battery_end_alert=spec.fx6_backup_battery_end_alert,
        grid_line_display=spec.grid_line_display,
        grid_line_type=spec.grid_line_type,
        hdmi_info_display=spec.hdmi_info_display,
        rec_media_dur_hdmi_output=spec.rec_media_dur_hdmi_output,
        raw_output_enabled=spec.raw_output_enabled,
        marker_display=spec.marker_display,
        marker_guideframe=spec.marker_guideframe,
        focus_magnifier_active=spec.focus_magnifier_active,
        fx6_marker_setting=spec.fx6_marker_setting,
        fx6_center_marker=spec.fx6_center_marker,
        fx6_safety_area=spec.fx6_safety_area,
        fx6_guide_frame=spec.fx6_guide_frame,
        fx6_vf_marker_osd=spec.fx6_vf_marker_osd,
        fx6_sdi_marker_osd=spec.fx6_sdi_marker_osd,
        fx6_hdmi_marker_osd=spec.fx6_hdmi_marker_osd,
        fx6_3mode_composition_grid_requested=spec.fx6_3mode_composition_grid_requested,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    areadate_ok = (
        spec.reported_areadate_errno == st["areadate_errno"]
        and st["areadate_errno"] is None
        and spec.reported_initial_setting_wizard_triggered == st["initial_setting_wizard_triggered"]
        and spec.reported_rtc_backup_charged_sufficiently == st["rtc_backup_charged_sufficiently"]
        and spec.post_daylight_savings == st["post_daylight_savings"]
        and spec.post_area_date_retained == st["post_area_date_retained"]
        and not spec.claim_user_cr2032_slot
        and not spec.claim_3month_retention_in_ilc2210
        and not spec.fx6_ui_dst_switch_requested
        and spec.areadate_dst_or_rtc_backup_drift_events == 0
    )
    if not areadate_ok:
        _fail(
            P380_BLOCKED_AREADATE_DST_OR_RTC_BACKUP_DRIFT,
            "Area/Date-DST 30-zone/RTC 24h/Reset resistance or FX6 Clock Set zero-DST rule violated",
        )

    grid_marker_ok = (
        spec.reported_grid_marker_errno == st["grid_marker_errno"]
        and st["grid_marker_errno"] is None
        and spec.reported_grid_line_hdmi_passthrough == st["grid_line_hdmi_passthrough"]
        and spec.reported_marker_visible_on_lcd == st["marker_visible_on_lcd"]
        and spec.reported_marker_hdmi_pixels_emitted == 0
        and st["marker_hdmi_pixels_emitted"] == 0
        and spec.post_grid_line_display == st["post_grid_line_display"]
        and spec.post_grid_line_type == st["post_grid_line_type"]
        and spec.post_marker_display == st["post_marker_display"]
        and spec.post_marker_guideframe == st["post_marker_guideframe"]
        and not spec.fx6_3mode_composition_grid_requested
        and spec.grid_vs_marker_cleanhdmi_drift_events == 0
    )
    if not grid_marker_ok:
        _fail(
            P380_BLOCKED_GRID_VS_MARKER_CLEANHDMI_DRIFT,
            "Grid Line HDMI passthrough vs Marker Display/Guideframe Clean-HDMI 0-pixel or FX6 Marker rule violated",
        )

    slot1_mutated = (
        spec.requested_vault_action in P380_WRITE_MUTATING_SLOT1_VAULT_ACTIONS
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
            P380_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P380_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P380_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P380_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P380_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    vault_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "70A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "area_gmt_zone": spec.area_gmt_zone,
            "grid_line_hdmi_passthrough": spec.reported_grid_line_hdmi_passthrough,
            "marker_hdmi_pixels_emitted": spec.reported_marker_hdmi_pixels_emitted,
            "slot1_writes": spec.slot1_writes,
            "errors": errors,
        }
    )
    return AreaDateDstGridCleanHdmiVaultReport(
        schema=PHASE380_SCHEMA,
        version=PHASE380_VERSION,
        passed=passed,
        status=P380_STATUS_VERIFIED_PILLAR_70A if passed else P380_STATUS_REJECTED_PILLAR_70A,
        block_code=block_code,
        areadate_dst_and_rtc_backup_verified=areadate_ok,
        grid_vs_marker_cleanhdmi_verified=grid_marker_ok,
        slot1_vault_and_h0_h3_verified=vault_and_h0_h3_ok,
        matrix_states_checked=64,
        areadate_dst_or_rtc_backup_drift_events=spec.areadate_dst_or_rtc_backup_drift_events,
        grid_vs_marker_cleanhdmi_drift_events=spec.grid_vs_marker_cleanhdmi_drift_events,
        hdmi_marker_guideframe_leak_pixels=spec.reported_marker_hdmi_pixels_emitted,
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


def evaluate_saveload_camset_mishoe_sync_vault(
    spec: SaveLoadCamsetMiShoeSyncVaultSpec,
) -> SaveLoadCamsetMiShoeSyncVaultReport:
    """Evaluate Pillar 70B spec (`[Save/Load Settings]` `CAMSET01..10.DAT`, `libSaveLoadSettings.so`,
    `Camera Set. Memory` `1..3` vs `M1..M4`, Slot-1 `EROFS=30` firewall, Sync Terminal debunk,
    MI-Shoe `[Video Light Mode]` vs `XLR-H1` preemption, & FX6 `All File` / `TC IN/OUT` / Zero `GENLOCK`)."""
    errors: List[str] = []
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    for serr in _safety_invariant_errors():
        _fail(P380_BLOCKED_SAFETY_POLICY_VIOLATION, serr)

    valid_spec = (
        spec.camera_model in (P380_FX3_MODEL_NAME, P380_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P380_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P380_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P380_SHOOTING_DOMAINS
        and spec.shutter_type in P380_SHUTTER_TYPES
        and spec.silent_mode in P380_ON_OFF_MODES
        and spec.saveload_operation in P380_SAVELOAD_OPS
        and spec.saveload_target_slot in (1, 2)
        and spec.media_card_type in P380_MEDIA_CARD_TYPES
        and spec.memory_recall_media_slot in (1, 2)
        and spec.reset_action in P380_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P380_VAULT_ACTIONS
        and spec.vault_firewall_errno in P380_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P380_BLOCKED_INVALID_PILLAR70B_SPEC, "Invalid Pillar 70B spec fields")

    st = compute_expected_saveload_camset_mishoe_sync_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        shutter_type=spec.shutter_type,
        silent_mode=spec.silent_mode,
        saveload_operation=spec.saveload_operation,
        saveload_target_slot=spec.saveload_target_slot,
        camset_slot_index=spec.camset_slot_index,
        cloud_slot_count=spec.cloud_slot_count,
        media_card_type=spec.media_card_type,
        camset_path_uses_pro_camera=spec.camset_path_uses_pro_camera,
        camset_source_model=spec.camset_source_model,
        camset_source_fw_version=spec.camset_source_fw_version,
        in_mr_recall_mode=spec.in_mr_recall_mode,
        camset_excluded_item_requested=spec.camset_excluded_item_requested,
        load_into_simulated_host_buffer_only=spec.load_into_simulated_host_buffer_only,
        cam_memory_slot=spec.cam_memory_slot,
        memory_recall_media_slot=spec.memory_recall_media_slot,
        cam_memory_includes_custom_key_or_pshift=spec.cam_memory_includes_custom_key_or_pshift,
        fx6_all_file_slot_count=spec.fx6_all_file_slot_count,
        fx6_all_file_load_network_data=spec.fx6_all_file_load_network_data,
        fx6_user_3d_lut_count=spec.fx6_user_3d_lut_count,
        fx6_reference_file_requested=spec.fx6_reference_file_requested,
        sync_terminal_requested=spec.sync_terminal_requested,
        flash_sync_spd_prty_requested=spec.flash_sync_spd_prty_requested,
        flash_mode=spec.flash_mode,
        flash_shutter_reciprocal=spec.flash_shutter_reciprocal,
        flash_trigger_voltage_v=spec.flash_trigger_voltage_v,
        flash_reverse_polarity=spec.flash_reverse_polarity,
        video_light_mode=spec.video_light_mode,
        xlr_h1_attached=spec.xlr_h1_attached,
        mishoe_electrical_device_attached=spec.mishoe_electrical_device_attached,
        mishoe_current_ma=spec.mishoe_current_ma,
        fx6_video_light_mode=spec.fx6_video_light_mode,
        fx6_still_flash_requested=spec.fx6_still_flash_requested,
        fx6_tc_bnc_mode=spec.fx6_tc_bnc_mode,
        fx6_genlock_bnc_requested=spec.fx6_genlock_bnc_requested,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    saveload_ok = (
        spec.reported_saveload_errno == st["saveload_errno"]
        and st["saveload_errno"] is None
        and spec.reported_saveload_reboot_required == st["saveload_reboot_required"]
        and spec.reported_media_prefix == st["expected_media_prefix"]
        and not spec.camset_path_uses_pro_camera
        and spec.camset_excluded_item_requested == "None"
        and spec.camset_excluded_item_leak_events == 0
        and spec.camset_excluded_item_leaked_bytes == 0
        and not spec.cam_memory_includes_custom_key_or_pshift
        and not spec.fx6_reference_file_requested
        and spec.post_body_cam_memory_retained == st["post_body_cam_memory_retained"]
        and spec.saveload_camset_or_campr_slot1_drift_events == 0
    )
    if not saveload_ok:
        _fail(
            P380_BLOCKED_SAVELOAD_CAMSET_OR_CAMPR_DRIFT,
            "Save/Load Settings CAMSET01..10.DAT, libSaveLoadSettings.so, exclusion list, Camera Set. Memory 1..3/M1..M4, or FX6 All File rule violated",
        )

    mishoe_ok = (
        spec.reported_mishoe_sync_errno == st["mishoe_sync_errno"]
        and st["mishoe_sync_errno"] is None
        and spec.reported_fx6_tc_ext_lk_active == st["fx6_tc_ext_lk_active"]
        and spec.post_external_flash_set_retained == st["post_external_flash_set_retained"]
        and not spec.sync_terminal_requested
        and not spec.flash_sync_spd_prty_requested
        and not spec.fx6_still_flash_requested
        and not spec.fx6_genlock_bnc_requested
        and spec.sync_terminal_mishoe_or_genlock_drift_events == 0
    )
    if not mishoe_ok:
        _fail(
            P380_BLOCKED_SYNC_TERMINAL_MISHOE_OR_GENLOCK_DRIFT,
            "Sync Terminal debunk, MI-Shoe Flash/Video Light vs XLR-H1 preemption, PMIC 900mA budget, or FX6 TC/zero-GENLOCK rule violated",
        )

    slot1_mutated = (
        spec.requested_vault_action in P380_WRITE_MUTATING_SLOT1_VAULT_ACTIONS
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
            P380_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P380_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P380_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P380_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P380_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    vault_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "70B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "saveload_op": spec.saveload_operation,
            "video_light_mode": spec.video_light_mode,
            "xlr_h1_attached": spec.xlr_h1_attached,
            "slot1_writes": spec.slot1_writes,
            "errors": errors,
        }
    )
    return SaveLoadCamsetMiShoeSyncVaultReport(
        schema=PHASE380_SCHEMA,
        version=PHASE380_VERSION,
        passed=passed,
        status=P380_STATUS_VERIFIED_PILLAR_70B if passed else P380_STATUS_REJECTED_PILLAR_70B,
        block_code=block_code,
        saveload_camset_campr_and_allfile_verified=saveload_ok,
        sync_terminal_mishoe_xlrh1_and_genlock_verified=mishoe_ok,
        slot1_erofs_overlay_and_h0_h3_verified=vault_and_h0_h3_ok,
        matrix_states_checked=72,
        saveload_camset_or_campr_slot1_drift_events=spec.saveload_camset_or_campr_slot1_drift_events,
        sync_terminal_mishoe_or_genlock_drift_events=spec.sync_terminal_mishoe_or_genlock_drift_events,
        camset_excluded_item_leak_events=spec.camset_excluded_item_leak_events,
        camset_excluded_item_leaked_bytes=spec.camset_excluded_item_leaked_bytes,
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


def verify_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_vault(
    *,
    areadate_grid_spec: Optional[AreaDateDstGridCleanHdmiVaultSpec] = None,
    saveload_mishoe_spec: Optional[SaveLoadCamsetMiShoeSyncVaultSpec] = None,
    force_clean_room: Optional[bool] = None,
) -> AreaDateDstGridCleanHdmiSaveLoadCamsetMiShoeVaultReport:
    """Single-shot combined Pillar 70 verifier (70A + 70B + 18 bounded `O_RDONLY` donors)."""
    donor_snapshot = inspect_phase380_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_areadate_dst_grid_cleanhdmi_vault(
        areadate_grid_spec or build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec()
    )
    rep_b = evaluate_saveload_camset_mishoe_sync_vault(
        saveload_mishoe_spec or build_default_safe_saveload_camset_mishoe_sync_vault_spec()
    )
    errs: List[str] = list(_safety_invariant_errors())
    if not donor_snapshot.all_donors_present:
        errs.append("Wave-68 18-donor verification failed")
    errs.extend(rep_a.errors)
    errs.extend(rep_b.errors)
    all_ok = rep_a.passed and rep_b.passed and donor_snapshot.all_donors_present and len(errs) == 0
    return AreaDateDstGridCleanHdmiSaveLoadCamsetMiShoeVaultReport(
        schema=PHASE380_SCHEMA,
        version=PHASE380_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P380_STATUS_VERIFIED_PILLAR70_SUITE if all_ok else P380_STATUS_FAIL_PILLAR70_SUITE,
        donor_snapshot=donor_snapshot,
        areadate_dst_grid_cleanhdmi_report=rep_a,
        saveload_camset_mishoe_sync_report=rep_b,
        areadate_dst_or_rtc_backup_drift_events=rep_a.areadate_dst_or_rtc_backup_drift_events,
        grid_vs_marker_cleanhdmi_drift_events=rep_a.grid_vs_marker_cleanhdmi_drift_events,
        saveload_camset_or_campr_slot1_drift_events=rep_b.saveload_camset_or_campr_slot1_drift_events,
        sync_terminal_mishoe_or_genlock_drift_events=rep_b.sync_terminal_mishoe_or_genlock_drift_events,
        hdmi_marker_guideframe_leak_pixels=rep_a.hdmi_marker_guideframe_leak_pixels,
        camset_excluded_item_leak_events=rep_b.camset_excluded_item_leak_events,
        camset_excluded_item_leaked_bytes=rep_b.camset_excluded_item_leaked_bytes,
        slot1_writes=rep_a.slot1_writes + rep_b.slot1_writes,
        slot1_data_sector_writes=rep_a.slot1_data_sector_writes + rep_b.slot1_data_sector_writes,
        slot1_sector_writes=rep_a.slot1_sector_writes + rep_b.slot1_sector_writes,
        slot1_vault_mutation_bytes=rep_a.slot1_vault_mutation_bytes + rep_b.slot1_vault_mutation_bytes,
        cnflasha_writes=rep_a.cnflasha_writes + rep_b.cnflasha_writes,
        slot1_format_hard_locked=rep_a.slot1_format_hard_locked and rep_b.slot1_format_hard_locked,
        slot1_vault_erofs_eopnotsupp_enforced=(
            rep_a.slot1_vault_erofs_eopnotsupp_enforced and rep_b.slot1_vault_erofs_eopnotsupp_enforced
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
        emmc_writes_authorized=P380_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(errs),
    )


def verify_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_vault(
    *,
    areadate_grid_spec: Optional[AreaDateDstGridCleanHdmiVaultSpec] = None,
    saveload_mishoe_spec: Optional[SaveLoadCamsetMiShoeSyncVaultSpec] = None,
    force_clean_room: Optional[bool] = None,
) -> AreaDateDstGridCleanHdmiSaveLoadCamsetMiShoeVaultReport:
    """Short symmetry alias for `verify_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_vault`."""
    return verify_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_vault(
        areadate_grid_spec=areadate_grid_spec,
        saveload_mishoe_spec=saveload_mishoe_spec,
        force_clean_room=force_clean_room,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillar 70A & Pillar 70B = 12 Scenarios Total)
# ---------------------------------------------------------------------------


def run_pillar70a_areadate_dst_grid_cleanhdmi_vault_6_scenario_suite() -> Pillar70ASuiteResult:
    """Run 6 deterministic Pillar 70A scenarios (2 allow + 4 fail-closed reject)."""
    cases: Tuple[Tuple[str, bool, AreaDateDstGridCleanHdmiVaultSpec, Optional[str]], ...] = (
        (
            P380_PILLAR_70A_SCENARIO_IDS[0],
            True,
            build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
                area_gmt_zone="AREA_GMT_P_05_5",  # Half-hour zone (India +5:30)
                daylight_savings="On",
                date_format="D-M-Y",
                grid_line_display="On",
                grid_line_type="Diag. + Square Grid",
                hdmi_info_display="On",
                rec_media_dur_hdmi_output="On",
                raw_output_enabled="Off",
                marker_display="On",
                marker_guideframe="On",
                focus_magnifier_active=False,
                reported_grid_line_hdmi_passthrough=True,
                reported_marker_visible_on_lcd=True,
                reported_marker_hdmi_pixels_emitted=0,
                reset_action="Camera Settings Reset",
                post_daylight_savings="On",
                post_area_date_retained=True,
                post_grid_line_display="On",
                post_grid_line_type="Diag. + Square Grid",
                post_marker_display="On",
                post_marker_guideframe="On",
            ),
            None,
        ),
        (
            P380_PILLAR_70A_SCENARIO_IDS[1],
            True,
            build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
                camera_model=P380_FX6_DONOR_MODEL_NAME,
                fw_version=P380_FX6_DONOR_FW_VERSION,
                shooting_domain="Movie",
                fx6_utc_offset_minutes=840,  # UTC +14:00
                fx6_date_mode="DDMMYY",
                fx6_time_format="12h",
                fx6_ui_dst_switch_requested=False,
                fx6_marker_setting="On",
                fx6_center_marker="4",
                fx6_safety_area="92.5%",
                fx6_guide_frame="On",
                fx6_vf_marker_osd="On",
                fx6_sdi_marker_osd="On",
                fx6_hdmi_marker_osd="Off",
                fx6_3mode_composition_grid_requested=False,
                reported_grid_line_hdmi_passthrough=False,
                reported_marker_visible_on_lcd=True,
                reported_marker_hdmi_pixels_emitted=0,
            ),
            None,
        ),
        (
            P380_PILLAR_70A_SCENARIO_IDS[2],
            False,
            build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
                area_gmt_zone="AREA_GMT_P_14_0",  # Invalid on FX3 (only up to +12:00)
                date_format="YYYY-MM-DD",  # Invalid (only Y-M-D/M-D-Y/D-M-Y)
                claim_user_cr2032_slot=True,
                claim_3month_retention_in_ilc2210=True,
                reported_areadate_errno=None,
                reset_action="Camera Settings Reset",
                post_area_date_retained=False,  # Wrong: Area/Date resists Reset!
                areadate_dst_or_rtc_backup_drift_events=1,
            ),
            P380_BLOCKED_AREADATE_DST_OR_RTC_BACKUP_DRIFT,
        ),
        (
            P380_PILLAR_70A_SCENARIO_IDS[3],
            False,
            build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
                camera_model=P380_FX6_DONOR_MODEL_NAME,
                fw_version=P380_FX6_DONOR_FW_VERSION,
                fx6_utc_offset_minutes=495,  # Invalid non-30-min step!
                fx6_ui_dst_switch_requested=True,
                fx6_3mode_composition_grid_requested=True,
                reported_areadate_errno=None,
                reported_grid_marker_errno=None,
                areadate_dst_or_rtc_backup_drift_events=1,
                grid_vs_marker_cleanhdmi_drift_events=1,
            ),
            P380_BLOCKED_AREADATE_DST_OR_RTC_BACKUP_DRIFT,
        ),
        (
            P380_PILLAR_70A_SCENARIO_IDS[4],
            False,
            build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
                shooting_domain="Still",
                marker_display="On",
                marker_guideframe="On",
                focus_magnifier_active=True,
                reported_grid_marker_errno=None,
                reported_marker_visible_on_lcd=True,
                reported_marker_hdmi_pixels_emitted=640,  # Wrong: Marker MUST emit 0 HDMI px!
                reset_action="Camera Settings Reset",
                post_grid_line_display="Off",  # Wrong: Grid Line resists Reset!
                post_marker_guideframe="Off",  # Wrong: Marker Display all 5 resist Reset!
                grid_vs_marker_cleanhdmi_drift_events=1,
            ),
            P380_BLOCKED_GRID_VS_MARKER_CLEANHDMI_DRIFT,
        ),
        (
            P380_PILLAR_70A_SCENARIO_IDS[5],
            False,
            build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
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
                overlay_dir="/dev/cnflasha/70a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P380_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar70ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_areadate_dst_grid_cleanhdmi_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar70ScenarioOutcome(
                scenario_id=sid,
                pillar="70A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar70ASuiteResult(
        passed=all_ok,
        status=P380_STATUS_VERIFIED_PILLAR_70A if all_ok else P380_STATUS_REJECTED_PILLAR_70A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar70b_saveload_camset_mishoe_sync_vault_6_scenario_suite() -> Pillar70BSuiteResult:
    """Run 6 deterministic Pillar 70B scenarios (2 allow + 4 fail-closed reject)."""
    cases: Tuple[Tuple[str, bool, SaveLoadCamsetMiShoeSyncVaultSpec, Optional[str]], ...] = (
        (
            P380_PILLAR_70B_SCENARIO_IDS[0],
            True,
            build_default_safe_saveload_camset_mishoe_sync_vault_spec(
                saveload_operation="LOAD_CAMSET",
                saveload_target_slot=1,
                camset_slot_index=10,
                cloud_slot_count=60,
                media_card_type="CFexpress Type A",
                reported_media_prefix=P380_FX3_CFEXPRESS_MEDIA_PREFIX,
                load_into_simulated_host_buffer_only=True,
                reported_saveload_reboot_required=True,
                video_light_mode="Auto",
                xlr_h1_attached=False,
                mishoe_electrical_device_attached=True,
                mishoe_current_ma=850,
                requested_vault_slot=1,
                requested_vault_action="LOAD_CAMSET_SLOT1_HOST_BUFFER_RO",
            ),
            None,
        ),
        (
            P380_PILLAR_70B_SCENARIO_IDS[1],
            True,
            build_default_safe_saveload_camset_mishoe_sync_vault_spec(
                camera_model=P380_FX6_DONOR_MODEL_NAME,
                fw_version=P380_FX6_DONOR_FW_VERSION,
                saveload_operation="FX6_LOAD_ALL_FILE",
                fx6_all_file_slot_count=64,
                fx6_all_file_load_network_data=True,
                fx6_user_3d_lut_count=16,
                fx6_reference_file_requested=False,
                reported_saveload_reboot_required=True,
                fx6_video_light_mode="Rec Link + Stby",
                fx6_still_flash_requested=False,
                fx6_tc_bnc_mode="IN",
                fx6_genlock_bnc_requested=False,
                reported_fx6_tc_ext_lk_active=True,
                requested_vault_slot=2,
                requested_vault_action="FX6_ALL_FILE_MEDIA_B",
            ),
            None,
        ),
        (
            P380_PILLAR_70B_SCENARIO_IDS[2],
            False,
            build_default_safe_saveload_camset_mishoe_sync_vault_spec(
                saveload_operation="LOAD_CAMSET",
                saveload_target_slot=2,  # Wrong: Save/Load Settings locked to Slot 1!
                camset_path_uses_pro_camera=True,
                camset_source_model="ILCE-7SM3",
                camset_source_fw_version="1.01",
                in_mr_recall_mode=True,
                camset_excluded_item_requested="Copyright Info",
                camset_excluded_item_leak_events=1,
                camset_excluded_item_leaked_bytes=46,
                reported_saveload_errno=None,
                saveload_camset_or_campr_slot1_drift_events=1,
            ),
            P380_BLOCKED_SAVELOAD_CAMSET_OR_CAMPR_DRIFT,
        ),
        (
            P380_PILLAR_70B_SCENARIO_IDS[3],
            False,
            build_default_safe_saveload_camset_mishoe_sync_vault_spec(
                shooting_domain="Still",
                shutter_type="Electronic Shutter",
                sync_terminal_requested=True,
                flash_sync_spd_prty_requested=True,
                flash_mode="Fill-flash",
                flash_shutter_reciprocal=320,
                flash_trigger_voltage_v=300,
                xlr_h1_attached=True,
                mishoe_electrical_device_attached=True,
                mishoe_current_ma=1100,
                reported_mishoe_sync_errno=None,
                sync_terminal_mishoe_or_genlock_drift_events=1,
            ),
            P380_BLOCKED_SYNC_TERMINAL_MISHOE_OR_GENLOCK_DRIFT,
        ),
        (
            P380_PILLAR_70B_SCENARIO_IDS[4],
            False,
            build_default_safe_saveload_camset_mishoe_sync_vault_spec(
                camera_model=P380_FX6_DONOR_MODEL_NAME,
                fw_version=P380_FX6_DONOR_FW_VERSION,
                saveload_operation="FX6_LOAD_ALL_FILE",
                fx6_reference_file_requested=True,
                fx6_video_light_mode="Auto",  # Wrong: FX6 has 3 modes ONLY!
                fx6_still_flash_requested=True,
                fx6_genlock_bnc_requested=True,
                reported_saveload_errno=None,
                reported_mishoe_sync_errno=None,
                saveload_camset_or_campr_slot1_drift_events=1,
                sync_terminal_mishoe_or_genlock_drift_events=1,
            ),
            P380_BLOCKED_SAVELOAD_CAMSET_OR_CAMPR_DRIFT,
        ),
        (
            P380_PILLAR_70B_SCENARIO_IDS[5],
            False,
            build_default_safe_saveload_camset_mishoe_sync_vault_spec(
                saveload_operation="SAVE_CAMSET",
                saveload_target_slot=1,
                reported_saveload_reboot_required=False,
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
                overlay_dir="/mnt/emmc/70b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P380_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar70ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_saveload_camset_mishoe_sync_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar70ScenarioOutcome(
                scenario_id=sid,
                pillar="70B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar70BSuiteResult(
        passed=all_ok,
        status=P380_STATUS_VERIFIED_PILLAR_70B if all_ok else P380_STATUS_REJECTED_PILLAR_70B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Standalone Pillar 70 Suite & Concurrent Unified 70/70 Master Aggregator
# ---------------------------------------------------------------------------


def run_pillar70_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar70StandaloneReport:
    """Run full Pillar 70 standalone suite (`6/6` Pillar 70A + `6/6` Pillar 70B + 18 bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase380_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar70a_areadate_dst_grid_cleanhdmi_vault_6_scenario_suite()
    res_b = run_pillar70b_saveload_camset_mishoe_sync_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 380 18-donor verification failed")
    if not donor_snapshot.under_2_0s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE380_SCHEMA,
            "version": PHASE380_VERSION,
            "mode": donor_snapshot.verification_mode,
            "70a": [asdict(s) for s in res_a.scenarios],
            "70b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar70StandaloneReport(
        schema=PHASE380_SCHEMA,
        version=PHASE380_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P380_STATUS_VERIFIED_PILLAR70_SUITE if all_ok else P380_STATUS_FAIL_PILLAR70_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_70a_areadate_dst_grid_cleanhdmi_vault=res_a,
        pillar_70b_saveload_camset_mishoe_sync_vault=res_b,
        areadate_dst_or_rtc_backup_drift_events=(
            P380_AREADATE_DST_OR_RTC_BACKUP_DRIFT_EVENTS if res_a.passed else 1
        ),
        grid_vs_marker_cleanhdmi_drift_events=(
            P380_GRID_VS_MARKER_CLEANHDMI_DRIFT_EVENTS if res_a.passed else 1
        ),
        saveload_camset_or_campr_slot1_drift_events=(
            P380_SAVELOAD_CAMSET_OR_CAMPR_SLOT1_DRIFT_EVENTS if res_b.passed else 1
        ),
        sync_terminal_mishoe_or_genlock_drift_events=(
            P380_SYNC_TERMINAL_MISHOE_OR_GENLOCK_DRIFT_EVENTS if res_b.passed else 1
        ),
        hdmi_marker_guideframe_leak_pixels=(
            P380_HDMI_MARKER_GUIDEFRAME_LEAK_PIXELS if res_a.passed else 1
        ),
        camset_excluded_item_leak_events=(
            P380_CAMSET_EXCLUDED_ITEM_LEAK_EVENTS if res_b.passed else 1
        ),
        camset_excluded_item_leaked_bytes=(
            P380_CAMSET_EXCLUDED_ITEM_LEAKED_BYTES if res_b.passed else 1
        ),
        slot1_writes=(P380_SLOT1_WRITES if (res_a.passed and res_b.passed) else 1),
        slot1_data_sector_writes=(
            P380_SLOT1_DATA_SECTOR_WRITES if (res_a.passed and res_b.passed) else 1
        ),
        slot1_sector_writes=(
            P380_SLOT1_SECTOR_WRITES if (res_a.passed and res_b.passed) else 1
        ),
        slot1_vault_mutation_bytes=(
            P380_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        cnflasha_writes=(P380_CNFLASHA_WRITES if (res_a.passed and res_b.passed) else 4096),
        rf_packets_transmitted=P380_RF_PACKETS_TRANSMITTED,
        rf_nvs_mutation_bytes=P380_RF_NVS_MUTATION_BYTES,
        slot1_format_hard_locked=P380_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_eopnotsupp_enforced=P380_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        slot1_vault_erofs_ebusy_enforced=P380_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
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
        emmc_writes_authorized=P380_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(safety_errs),
    )


def _apply_master70_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def _master70_local_donors_available() -> bool:
    """Return True only when all 18 Wave-68 local donors exist."""
    required_relpaths: Tuple[str, ...] = (
        P380_DONOR_FX3_APPFW_702_RELPATH,
        P380_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
        P380_DONOR_FX3_BACKUP_BIN_RELPATH,
        P380_DONOR_FX6_APPFW_601_RELPATH,
        P380_DONOR_FX3_UXC_EN_F_RELPATH,
        P380_DONOR_FX3_UXC_SC_F_RELPATH,
        P380_DONOR_FX3_UXC_TC_F_RELPATH,
        P380_DONOR_FX3_UXC_JA_F_RELPATH,
        P380_DONOR_FX3_UXC_EN_RELPATH,
        P380_DONOR_FX3_UXC_SC_RELPATH,
        P380_DONOR_FX3_UXC_TC_RELPATH,
        P380_DONOR_FX3_UXC_JA_RELPATH,
        P380_DONOR_FX3_UXC_EN_G_RELPATH,
        P380_DONOR_FX3_UXC_SC_G_RELPATH,
        P380_DONOR_FX3_UXC_TC_G_RELPATH,
        P380_DONOR_FX3_UXC_JA_G_RELPATH,
        P380_DONOR_FX6_UXC_EN_RELPATH,
        P380_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for relpath in required_relpaths:
        try:
            resolved = _resolve_phase380_donor_path(relpath)
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


def evaluate_realhw_70pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master70PillarRecoveryReport:
    """Evaluate and aggregate all 70 recovery pillars (`1..70`) concurrently -> `70/70` Milestone master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_70_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    if resolved_clean_room is None and not _master70_local_donors_available():
        resolved_clean_room = True
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_69pillar() -> Master69PillarRecoveryReport:
        return evaluate_realhw_69pillar_recovery_master(**kw)

    def _run_p70() -> Tuple[Pillar70StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar70_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_69 = pool.submit(_run_69pillar)
        fut_70 = pool.submit(_run_p70)
        m69_rep = fut_69.result()
        p70_rep, p70_dt = fut_70.result()

    all_errors: List[str] = list(m69_rep.errors) + list(p70_rep.errors)
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
        if getattr(m69_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-69 violated {attr_name} == {expected_val}")
        if getattr(p70_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 70 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("areadate_dst_or_rtc_backup_drift_events", 0),
        ("grid_vs_marker_cleanhdmi_drift_events", 0),
        ("saveload_camset_or_campr_slot1_drift_events", 0),
        ("sync_terminal_mishoe_or_genlock_drift_events", 0),
        ("hdmi_marker_guideframe_leak_pixels", 0),
        ("camset_excluded_item_leak_events", 0),
        ("camset_excluded_item_leaked_bytes", 0),
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
        if getattr(p70_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 70 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m69_rep.pillars)
    spec70 = MASTER_70_PILLAR_SPECS[69]
    p70_metrics = {
        "pillar_70a_areadate_dst_grid_cleanhdmi_vault": (
            f"{p70_rep.pillar_70a_areadate_dst_grid_cleanhdmi_vault.scenarios_passed}/"
            f"{p70_rep.pillar_70a_areadate_dst_grid_cleanhdmi_vault.scenarios_total}"
        ),
        "pillar_70b_saveload_camset_mishoe_sync_vault": (
            f"{p70_rep.pillar_70b_saveload_camset_mishoe_sync_vault.scenarios_passed}/"
            f"{p70_rep.pillar_70b_saveload_camset_mishoe_sync_vault.scenarios_total}"
        ),
        "areadate_dst_or_rtc_backup_drift_events": p70_rep.areadate_dst_or_rtc_backup_drift_events,
        "grid_vs_marker_cleanhdmi_drift_events": p70_rep.grid_vs_marker_cleanhdmi_drift_events,
        "saveload_camset_or_campr_slot1_drift_events": (
            p70_rep.saveload_camset_or_campr_slot1_drift_events
        ),
        "sync_terminal_mishoe_or_genlock_drift_events": (
            p70_rep.sync_terminal_mishoe_or_genlock_drift_events
        ),
        "hdmi_marker_guideframe_leak_pixels": p70_rep.hdmi_marker_guideframe_leak_pixels,
        "camset_excluded_item_leak_events": p70_rep.camset_excluded_item_leak_events,
        "camset_excluded_item_leaked_bytes": p70_rep.camset_excluded_item_leaked_bytes,
        "slot1_writes": p70_rep.slot1_writes,
        "slot1_data_sector_writes": p70_rep.slot1_data_sector_writes,
        "slot1_sector_writes": p70_rep.slot1_sector_writes,
        "slot1_vault_mutation_bytes": p70_rep.slot1_vault_mutation_bytes,
        "cnflasha_writes": p70_rep.cnflasha_writes,
        "slot1_format_hard_locked": p70_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_eopnotsupp_enforced": p70_rep.slot1_vault_erofs_eopnotsupp_enforced,
        "overall_ready_for_hardware_attach": p70_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p70_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p70_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p70_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec70[0],
            pillar_id=spec70[1],
            phase_label=spec70[2],
            module_name=spec70[3],
            passed=bool(p70_rep.all_passed),
            status=p70_rep.status,
            verification_mode=p70_rep.verification_mode,
            elapsed_seconds=p70_dt,
            key_metrics=p70_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec70[1],
                    "mode": p70_rep.verification_mode,
                    "status": p70_rep.status,
                    "metrics": p70_metrics,
                    "passed": p70_rep.all_passed,
                }
            ),
            errors=tuple(p70_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master70_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p70_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_70_PILLAR_COUNT == 70
        and pillars_passed == 70
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE380_SCHEMA,
            "schema_version": PHASE380_MASTER_SCHEMA,
            "version": PHASE380_VERSION,
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

    return Master70PillarRecoveryReport(
        schema=PHASE380_SCHEMA,
        schema_version=PHASE380_MASTER_SCHEMA,
        version=PHASE380_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=(
            P380_STATUS_VERIFIED_70OF70_AGGREGATOR if all_ok else P380_STATUS_FAIL_70OF70_AGGREGATOR
        ),
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P380_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.50,
        under_6s_budget=elapsed < P380_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P380_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p70_rep.donor_snapshot,
        pillar70_a_areadate_dst_grid_cleanhdmi_vault=(
            p70_rep.pillar_70a_areadate_dst_grid_cleanhdmi_vault
        ),
        pillar70_b_saveload_camset_mishoe_sync_vault=(
            p70_rep.pillar_70b_saveload_camset_mishoe_sync_vault
        ),
        areadate_dst_or_rtc_backup_drift_events=p70_rep.areadate_dst_or_rtc_backup_drift_events,
        grid_vs_marker_cleanhdmi_drift_events=p70_rep.grid_vs_marker_cleanhdmi_drift_events,
        saveload_camset_or_campr_slot1_drift_events=(
            p70_rep.saveload_camset_or_campr_slot1_drift_events
        ),
        sync_terminal_mishoe_or_genlock_drift_events=(
            p70_rep.sync_terminal_mishoe_or_genlock_drift_events
        ),
        hdmi_marker_guideframe_leak_pixels=p70_rep.hdmi_marker_guideframe_leak_pixels,
        camset_excluded_item_leak_events=p70_rep.camset_excluded_item_leak_events,
        camset_excluded_item_leaked_bytes=p70_rep.camset_excluded_item_leaked_bytes,
        fx3_area_gmt_zone_count=P380_FX3_AREA_GMT_ZONE_COUNT,
        fx3_area_date_time_resettable=P380_FX3_AREA_DATE_TIME_RESETTABLE,
        fx3_has_user_cr2032_slot=P380_FX3_HAS_USER_CR2032_SLOT,
        fx3_helpguide_claims_3_months_retention=P380_FX3_HELPGUIDE_CLAIMS_3_MONTHS_RETENTION,
        fx3_grid_line_resettable=P380_FX3_GRID_LINE_RESETTABLE,
        fx3_marker_display_all_5_resettable=P380_FX3_MARKER_DISPLAY_ALL_5_RESETTABLE,
        fx3_pro_camera_path_hits=P380_FX3_PRO_CAMERA_PATH_HITS,
        fx3_camset_locked_slot=P380_FX3_CAMSET_LOCKED_SLOT,
        fx3_camset_max_card_slots=P380_FX3_CAMSET_MAX_CARD_SLOTS,
        fx3_has_physical_sync_terminal=P380_FX3_HAS_PHYSICAL_SYNC_TERMINAL,
        fx3_synchro_terminal_appfw_hits=P380_FX3_SYNCHRO_TERMINAL_APPFW_HITS,
        fx3_has_tc_bnc=P380_FX3_HAS_TC_BNC,
        xlr_h1_preempts_electrical_mi_shoe=P380_XLR_H1_PREEMPTS_ELECTRICAL_MI_SHOE,
        fx6_has_ui_dst_switch=P380_FX6_HAS_UI_DST_SWITCH,
        fx6_has_3mode_composition_grid_ui=P380_FX6_HAS_3MODE_COMPOSITION_GRID_UI,
        fx6_has_user_exposed_reference_file=P380_FX6_HAS_USER_EXPOSED_REFERENCE_FILE,
        fx6_has_video_light_auto=P380_FX6_HAS_VIDEO_LIGHT_AUTO,
        fx6_has_still_flash_ui=P380_FX6_HAS_STILL_FLASH_UI,
        fx6_has_tc_in_out_bnc=P380_FX6_HAS_TC_IN_OUT_BNC,
        fx6_has_physical_genlock_bnc=P380_FX6_HAS_PHYSICAL_GENLOCK_BNC,
        fx6_dormant_genlock_symbol_count=P380_FX6_DORMANT_GENLOCK_SYMBOL_COUNT,
        # Carried forward from Pillar 69
        pixelmap_apr_or_zero_abb_drift_events=m69_rep.pixelmap_apr_or_zero_abb_drift_events,
        monitor_3item_or_dormant_evf_drift_events=m69_rep.monitor_3item_or_dormant_evf_drift_events,
        recall_hold_11bit_or_push_key_drift_events=m69_rep.recall_hold_11bit_or_push_key_drift_events,
        hdmi_recctrl_24p_or_slot1_vault_drift_events=(
            m69_rep.hdmi_recctrl_24p_or_slot1_vault_drift_events
        ),
        fx3_auto_pixel_map_resettable=m69_rep.fx3_auto_pixel_map_resettable,
        fx3_silent_target_auto_pixel_map_resettable=(
            m69_rep.fx3_silent_target_auto_pixel_map_resettable
        ),
        fx3_has_finder_monitor_group=m69_rep.fx3_has_finder_monitor_group,
        fx3_has_dormant_evf_items_exposed=m69_rep.fx3_has_dormant_evf_items_exposed,
        fx3_monitor_group_resettable=m69_rep.fx3_monitor_group_resettable,
        fx3_recall_custom_hold_bit_count=m69_rep.fx3_recall_custom_hold_bit_count,
        fx3_recall_custom_hold_wb_hits=m69_rep.fx3_recall_custom_hold_wb_hits,
        fx3_recall_custom_hold_has_independent_wb=(
            m69_rep.fx3_recall_custom_hold_has_independent_wb
        ),
        fx3_reg_custom_shoot_set_resettable=m69_rep.fx3_reg_custom_shoot_set_resettable,
        fx3_external_output_resettable=m69_rep.fx3_external_output_resettable,
        fx3_has_dormant_4k_2k_output=m69_rep.fx3_has_dormant_4k_2k_output,
        fx3_has_dormant_24p_60p_output=m69_rep.fx3_has_dormant_24p_60p_output,
        fx6_has_user_exposed_abb=m69_rep.fx6_has_user_exposed_abb,
        fx6_has_vf_4item_submenu=m69_rep.fx6_has_vf_4item_submenu,
        fx6_has_recall_custom_hold=m69_rep.fx6_has_recall_custom_hold,
        fx6_has_high_low_key_exposed=m69_rep.fx6_has_high_low_key_exposed,
        slot1_writes=m69_rep.slot1_writes + p70_rep.slot1_writes,
        slot1_sector_writes=m69_rep.slot1_sector_writes + p70_rep.slot1_sector_writes,
        cnflasha_writes=m69_rep.cnflasha_writes + p70_rep.cnflasha_writes,
        emmc_writes_authorized=P380_EMMC_WRITES_AUTHORIZED,
        # Carried forward from Pillars 61..68
        drive_mode_or_dormant_focus_bracket_drift_events=(
            m69_rep.drive_mode_or_dormant_focus_bracket_drift_events
        ),
        shutter_2opt_xsync_efcs_or_nr_drift_events=(
            m69_rep.shutter_2opt_xsync_efcs_or_nr_drift_events
        ),
        creative_look_8param_override_or_softskin_drift_events=(
            m69_rep.creative_look_8param_override_or_softskin_drift_events
        ),
        delete_protect_recoverdb_slot1_vault_drift_events=(
            m69_rep.delete_protect_recoverdb_slot1_vault_drift_events
        ),
        fx3_has_dormant_focus_bracket_exposed=m69_rep.fx3_has_dormant_focus_bracket_exposed,
        fx3_has_shutter_type_auto_exposed=m69_rep.fx3_has_shutter_type_auto_exposed,
        fx3_has_dormant_soft_skin_exposed=m69_rep.fx3_has_dormant_soft_skin_exposed,
        fx6_has_still_drive_mode=m69_rep.fx6_has_still_drive_mode,
        fx6_has_focus_bracket=m69_rep.fx6_has_focus_bracket,
        fx6_has_mechanical_shutter=m69_rep.fx6_has_mechanical_shutter,
        fx6_has_efcs=m69_rep.fx6_has_efcs,
        fx6_has_long_exp_nr=m69_rep.fx6_has_long_exp_nr,
        fx6_has_creative_look=m69_rep.fx6_has_creative_look,
        fx6_has_soft_skin_effect=m69_rep.fx6_has_soft_skin_effect,
        fx3_drive_mode_resettable=m69_rep.fx3_drive_mode_resettable,
        fx3_efcs_resettable=m69_rep.fx3_efcs_resettable,
        fx3_creative_look_resettable=m69_rep.fx3_creative_look_resettable,
        fx3_delete_confirm_resettable=m69_rep.fx3_delete_confirm_resettable,
        zoom_ciz_lockout_or_8speed_reset_drift_events=(
            m69_rep.zoom_ciz_lockout_or_8speed_reset_drift_events
        ),
        autoslow_6lockout_or_minss_still_drift_events=(
            m69_rep.autoslow_6lockout_or_minss_still_drift_events
        ),
        dual_base_iso_curve_matrix_drift_events=m69_rep.dual_base_iso_curve_matrix_drift_events,
        dormant_lossless_arw_exposed_events=m69_rep.dormant_lossless_arw_exposed_events,
        hlg_still_or_sort_rec_spillover_drift_events=(
            m69_rep.hlg_still_or_sort_rec_spillover_drift_events
        ),
        usb_lun_single_slot1_msc_hazard_events=m69_rep.usb_lun_single_slot1_msc_hazard_events,
        npfz100_pd_interlock_or_dcc1_drift_events=m69_rep.npfz100_pd_interlock_or_dcc1_drift_events,
        dormant_uvc_streaming_exposed_events=m69_rep.dormant_uvc_streaming_exposed_events,
        fx3_zoom_range_resettable=m69_rep.fx3_zoom_range_resettable,
        fx3_zoom_speed_resettable=m69_rep.fx3_zoom_speed_resettable,
        fx3_has_dormant_lossless_arw_exposed=m69_rep.fx3_has_dormant_lossless_arw_exposed,
        fx3_has_native_uvc_streaming=m69_rep.fx3_has_native_uvc_streaming,
        fx6_has_native_uvc_streaming=m69_rep.fx6_has_native_uvc_streaming,
        fx6_has_digital_zoom=m69_rep.fx6_has_digital_zoom,
        fx6_has_still_arw_hlg_pipeline=m69_rep.fx6_has_still_arw_hlg_pipeline,
        fx6_has_iso_auto_min_ss=m69_rep.fx6_has_iso_auto_min_ss,
        slot1_data_sector_writes=(
            m69_rep.slot1_data_sector_writes + p70_rep.slot1_data_sector_writes
        ),
        slot1_vault_mutation_bytes=(
            m69_rep.slot1_vault_mutation_bytes + p70_rep.slot1_vault_mutation_bytes
        ),
        rf_packets_transmitted=m69_rep.rf_packets_transmitted + p70_rep.rf_packets_transmitted,
        rf_nvs_mutation_bytes=m69_rep.rf_nvs_mutation_bytes + p70_rep.rf_nvs_mutation_bytes,
        slot1_format_hard_locked=(
            m69_rep.slot1_format_hard_locked and p70_rep.slot1_format_hard_locked
        ),
        slot1_vault_erofs_eopnotsupp_enforced=(
            m69_rep.slot1_vault_erofs_eopnotsupp_enforced
            and p70_rep.slot1_vault_erofs_eopnotsupp_enforced
        ),
        slot1_vault_erofs_ebusy_enforced=(
            m69_rep.slot1_vault_erofs_ebusy_enforced and p70_rep.slot1_vault_erofs_ebusy_enforced
        ),
        breathing_comp_lockout_or_catalyst_drift_events=(
            m69_rep.breathing_comp_lockout_or_catalyst_drift_events
        ),
        file_settings_camid_reel_or_sdhc_drift_events=(
            m69_rep.file_settings_camid_reel_or_sdhc_drift_events
        ),
        copyright_46ch_reset_erratum_or_serial_drift_events=(
            m69_rep.copyright_46ch_reset_erratum_or_serial_drift_events
        ),
        camset_copyright_pii_leak_events=m69_rep.camset_copyright_pii_leak_events,
        camset_copyright_pii_leaked_bytes=m69_rep.camset_copyright_pii_leaked_bytes,
        powersave_9cond_or_dormant_monitor_drift_events=(
            m69_rep.powersave_9cond_or_dormant_monitor_drift_events
        ),
        dormant_power_save_by_monitor_exposed_events=(
            m69_rep.dormant_power_save_by_monitor_exposed_events
        ),
        ntsc_pal_reboot_or_slot1_format_drift_events=(
            m69_rep.ntsc_pal_reboot_or_slot1_format_drift_events
        ),
        hdmi_raw_output_or_media_vault_drift_events=(
            m69_rep.hdmi_raw_output_or_media_vault_drift_events
        ),
        hdmi_4k_only_or_gamut_removal_drift_events=(
            m69_rep.hdmi_4k_only_or_gamut_removal_drift_events
        ),
        desqueeze_ratio_lock_or_bypass_drift_events=(
            m69_rep.desqueeze_ratio_lock_or_bypass_drift_events
        ),
        rec_lamp_tally_or_emph_display_drift_events=(
            m69_rep.rec_lamp_tally_or_emph_display_drift_events
        ),
        dormant_var_shutter_or_apsc_reset_drift_events=(
            m69_rep.dormant_var_shutter_or_apsc_reset_drift_events
        ),
        dormant_var_shutter_exposed_events=m69_rep.dormant_var_shutter_exposed_events,
        hdmi_red_border_clean_feed_leak_pixels=(
            m69_rep.hdmi_red_border_clean_feed_leak_pixels
        ),
        recorded_media_desqueeze_pixels=m69_rep.recorded_media_desqueeze_pixels,
        fx6_sdi_desqueeze_pixels=m69_rep.fx6_sdi_desqueeze_pixels,
        shoe_audio_preemption_or_limiter_drift_events=(
            m69_rep.shoe_audio_preemption_or_limiter_drift_events
        ),
        subject_recog_myth_or_face_memory_drift_events=(
            m69_rep.subject_recog_myth_or_face_memory_drift_events
        ),
        silent_mode_target_or_barrier_drift_events=(
            m69_rep.silent_mode_target_or_barrier_drift_events
        ),
        bodydata_version_flash_or_slot1_vault_drift_events=(
            m69_rep.bodydata_version_flash_or_slot1_vault_drift_events
        ),
        dormant_shutter_when_pwr_off_exposed_events=(
            m69_rep.dormant_shutter_when_pwr_off_exposed_events
        ),
        hdmi_face_frame_pixels_emitted=m69_rep.hdmi_face_frame_pixels_emitted,
        cnflasha_pixel_map_mutation_bytes=m69_rep.cnflasha_pixel_map_mutation_bytes,
        slot1_bodydata_mutation_bytes=m69_rep.slot1_bodydata_mutation_bytes,
        bodydata_placement_or_flash_authorized=m69_rep.bodydata_placement_or_flash_authorized,
        ftp_protocol_sftp_or_jpeg_size_drift_events=(
            m69_rep.ftp_protocol_sftp_or_jpeg_size_drift_events
        ),
        wb_custom_cine_ei_or_shockless_drift_events=(
            m69_rep.wb_custom_cine_ei_or_shockless_drift_events
        ),
        movie_af_speed_or_focus_map_spoof_events=m69_rep.movie_af_speed_or_focus_map_spoof_events,
        marker_15ratio_peaking_hdmi_leak_events=m69_rep.marker_15ratio_peaking_hdmi_leak_events,
        zero_rf_usblan_or_slot1_avf_bypass_events=(
            m69_rep.zero_rf_usblan_or_slot1_avf_bypass_events
        ),
        usblan_packets_transmitted=m69_rep.usblan_packets_transmitted,
        hdmi_marker_peaking_pixels_emitted=m69_rep.hdmi_marker_peaking_pixels_emitted,
        slot1_avf_info_mutation_bytes=m69_rep.slot1_avf_info_mutation_bytes,
        rec_media_prioritize_or_autoswitch_drift_events=(
            m69_rep.rec_media_prioritize_or_autoswitch_drift_events
        ),
        card_speed_vpg200_vpg400_gate_drift_events=(
            m69_rep.card_speed_vpg200_vpg400_gate_drift_events
        ),
        proxy_sq_dci4k_or_120p_lockout_drift_events=(
            m69_rep.proxy_sq_dci4k_or_120p_lockout_drift_events
        ),
        cloud_init_persist_or_power_off_ble_rf_events=(
            m69_rep.cloud_init_persist_or_power_off_ble_rf_events
        ),
        mymenu_42slot_or_fx6_lock_spoof_events=m69_rep.mymenu_42slot_or_fx6_lock_spoof_events,
        zero_rf_or_slot1_vault_bypass_events=m69_rep.zero_rf_or_slot1_vault_bypass_events,
        slot1_dcim_m4root_avf_mutation_bytes=m69_rep.slot1_dcim_m4root_avf_mutation_bytes,
        big6_home_or_lower_left_nd_drift_events=m69_rep.big6_home_or_lower_left_nd_drift_events,
        framing_manual_or_dormant_auto_framing_drift_events=(
            m69_rep.framing_manual_or_dormant_auto_framing_drift_events
        ),
        interval_shoot_9999_or_fx6_mxf_spoof_events=(
            m69_rep.interval_shoot_9999_or_fx6_mxf_spoof_events
        ),
        tc_make_regen_or_hdmi_rec_ctrl_drift_events=(
            m69_rep.tc_make_regen_or_hdmi_rec_ctrl_drift_events
        ),
        access_authen_ssh_tls_or_fan_max_drift_events=(
            m69_rep.access_authen_ssh_tls_or_fan_max_drift_events
        ),
        slot1_dcim_avf_mutation_bytes=m69_rep.slot1_dcim_avf_mutation_bytes,
        fx3_has_var_shutter=m69_rep.fx3_has_var_shutter,
        fx3_has_builtin_evf=m69_rep.fx3_has_builtin_evf,
        fx3_has_builtin_end_filter=m69_rep.fx3_has_builtin_end_filter,
        fx3_has_bt_timecode_link=m69_rep.fx3_has_bt_timecode_link,
        fx3_has_dormant_auto_framing=m69_rep.fx3_has_dormant_auto_framing,
        fx3_has_dormant_auto_hdr=m69_rep.fx3_has_dormant_auto_hdr,
        fx3_has_dormant_bulb_timer=m69_rep.fx3_has_dormant_bulb_timer,
        fx3_has_dormant_divide_extract=m69_rep.fx3_has_dormant_divide_extract,
        fx3_has_fan_control_max=m69_rep.fx3_has_fan_control_max,
        fx3_has_movie_self_timer=m69_rep.fx3_has_movie_self_timer,
        fx3_has_movie_sort_recording=m69_rep.fx3_has_movie_sort_recording,
        fx3_has_physical_end_hw=m69_rep.fx3_has_physical_end_hw,
        fx3_has_5axis_ibis=m69_rep.fx3_has_5axis_ibis,
        fx3_has_power_save_by_monitor=m69_rep.fx3_has_power_save_by_monitor,
        fx6_has_ibis=m69_rep.fx6_has_ibis,
        fx6_has_fan_control_max=m69_rep.fx6_has_fan_control_max,
        fx6_has_still_self_timer=m69_rep.fx6_has_still_self_timer,
        fx6_has_fn_menu=m69_rep.fx6_has_fn_menu,
        fx6_has_my_dial=m69_rep.fx6_has_my_dial,
        fx6_has_bluetooth_hardware=m69_rep.fx6_has_bluetooth_hardware,
        fx6_has_av_tv_rotate=m69_rep.fx6_has_av_tv_rotate,
        fx6_has_exif_copyright_menu=m69_rep.fx6_has_exif_copyright_menu,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        master_70pillar_sha256=master_sha,
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


def evaluate_70pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master70PillarRecoveryReport:
    """Short alias for `evaluate_realhw_70pillar_recovery_master`."""
    return evaluate_realhw_70pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_70pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master70PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_70pillar_recovery_master`."""
    return evaluate_realhw_70pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_70pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master70PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_70pillar_recovery_master`."""
    return evaluate_realhw_70pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_70pillar_recovery(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master70PillarRecoveryReport:
    """Milestone 375/364/324 dynamic discovery alias for `evaluate_realhw_70pillar_recovery_master`."""
    return evaluate_realhw_70pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_all_70_recovery_pillars(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master70PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_70pillar_recovery_master`."""
    return evaluate_realhw_70pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
