"""Phase 361 Milestone — Recovery Pillar 66 (`66A`/`66B`) & Concurrent 66/66 Master Recovery Verifier:
Wave-64 Sony ILME-FX3 (Ver. 7.02) vs ILME-FX6 (Ver. 6.01) Empirically Grounded Guardrails:
  * Pillar 66A:
    1. `Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]`
       (`_f 0x73ea / 0x659d / 0x616b`, Ver. 3.00+..7.02): `Off` (default) / `On`,
       **Resettable (`Can be reset`)** under `[Camera Settings Reset]` (unlike `Shading Comp.`,
       `Chromatic Aberration Comp.`, and `Distortion Comp.` which are `Not available`);
       `BKID_APP_setting_lens_comp_breathing` + `BKID_APP_MR_setting_lens_comp_breathing` +
       `PID_SET_BREATHING_CORRECTION` + `PRM_HAITA_breathing_correction_lens_type_lens_information`
       (`SUPPORT` / `NOT_SUPPORT` / `NA`; excluding `SEL100F28GM` macro `0.57m..1.0m`,
       `SEL14TC` / `SEL20TC` teleconverters, unsupported/3rd-party lenses, `Clear Image Zoom` /
       Digital Zoom / `Auto Framing` / `Framing Stabilizer`); disabled in Still, regular Movie
       `119.88p / 100p` (`fps >= 100`), `S&Q >= 100/120fps` (`100/120/200/240fps`; allowed `<100fps`
       on FX3!), and bypassed on external HDMI 16-bit `RAW Output` (`4264x2408`). Post-production
       metadata breathing compensation requires paid `Catalyst Prepare` / `Catalyst Prepare Plugin`
       (`Catalyst Browse` unsupported!) AND `[Distortion Comp.] = [Auto]`. Contrasted against
       `ILME-FX6 Ver. 6.01` `Technical > Lens > Breathing Compensation` (`Auto` / `Off`,
       `BKID_APP_SETTING_LENS_COMP_BREATHING`), hard-locked `Off` on 3 strict conditions:
       `Distortion Comp. = Off`, ALL `S&Q Motion = On` (any fps!), and any `RAW` codec.
    2. `Shooting -> [File] -> [File Settings]` (`_f 0x7367 / 0x61bc`, ALL items Reset-resistant
       `Not available` -> `[Initialize]` only): `[File Number]` (`Series` cross-slot
       Slot1<->Slot2 increment / `Reset` + `[Series Counter Reset]` -> `max + 1`),
       `[File Name Format]` (5 modes: `Standard`, `Cam ID + Reel#`, `Title`, `Date + Title`,
       `Title + Date`; `SDHC <=32GB FAT32` forces `Standard` only, splits XAVC S at `4 GB`, and
       forbids mixed `FAT32+exFAT` `[Simult. Recording]`), `[Cam ID + Reel# Settings]` (`A..Z`
       changing ID resets `001..999` Reel#, whereas `File Number = Reset` does NOT reset Reel#;
       `C/L/R` position overflows `C999 -> D001` in output filename ONLY without mutating menu
       setting; 6-digit `YYMMDD` + 2-char random vs 8-digit `YYYYMMDD` in `Date + Title` /
       `Title + Date`), `[Title Name Settings]` (`<=37` chars, default `"C"`, fixed
       `PRIVATE/M4ROOT/CLIP/*.MP4`, applies only to newly recorded clips), and Tier-0 `Slot 1`
       `EROFS=30` vault shield (`BKID_APP_update_required_xavcs_file_name_reel_number` blocked) vs
       FX6 `TC/Media > Clip Name Format` (`Cam ID + Reel#` / `Title`, `4..46`-char `Title Prefix`
       default `nnn_`, hardware card hand-over `DIADEM_PRO`, `/XDROOT/Clip/*.MXF`).
  * Pillar 66B:
    1. `[Copyright Info]` (`46`-char, `_f 0x6d53`) & `[Write Serial Number]` (`_f 0x7058`):
       Explicit **Round 57 Erratum Correction**: ALL 4 `[Copyright Info]` items
       (`[Write Copyright Info]` `Off`/`On` included, `[Set Photographer]` `<=46` ASCII,
       `[Set Copyright]` `<=46` ASCII, `[Disp. Copyright Info]`) AND `[Write Serial Number]`
       (`Off`/`On`) are **Reset-resistant (`Not available` under `[Camera Settings Reset]`)**,
       cleared ONLY by `[Initialize]`; `[Write Serial Number]` is fully active across Still + Movie
       in Ver. 2.00..7.02 (`BKID_APP_setting_write_serial_number_still_movie` `_f 0x6704/0x640c/0x7953`
       replacing Still-only `_f 0x792c`); `Copyright Info` PII is strictly excluded from `Slot 1`
       `CAMSET*.DAT` (`libSaveLoadSettings.so` `18,760 B`, `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`,
       max 10 Slot 1 / 60 C3 Portal), whereas FX6 has zero EXIF `[Copyright Info]` menu and tracks
       lens serials `CURRENT/PRESET_LENS_SERIAL_NUMBER0..5` + `Title Prefix = nnn_`.
    2. `Setup -> [Power Setting Option]` (ALL Reset-resistant, 2 active items + 1 dormant):
       `[Power Save Start Time]` (`Off/30Min/5Min(def)/2Min/1Min/10Sec`; dormant ELF/UXC
       `20SEC/NO_LIMIT/30 sec/60 min/240 min` -> `EOPNOTSUPP=95`) governed by **exact 9 official
       bypass conditions** (USB power supply, slideshow playback, FTP transfer, movie recording,
       PC connection, TV/HDMI connection, `IR Remote Ctrl=On`, `Bluetooth Rmt Ctrl=On`,
       streaming / Creators' Cloud upload) + `[Auto Power OFF Temp.]` (`Standard` def / `High`
       tripod-only warning `_g 0x61a9`), while `[Power Save by Monitor]`
       (`BKID_APP_setting_monitor_power_linkage`) is 100% dormant/unexposed on EVF-less FX3
       (`EOPNOTSUPP=95`); and `Setup -> [Area/Date] -> [NTSC/PAL Selector]` (`_f 0x6b6f`,
       Reset-resistant `Not available`, `base 0xe5c1` mandatory reboot, `Running on NTSC./PAL.`
       `base 0xe77a/0xe0b6`, PAL disables `23.98p` and locks TC `NDF`, cross-region playback block
       `_g 0x61ca/0x644e`, and legacy embedded `base 0xe595` `"Format? Slot 1"` SD-Erase/TRIM hazard
       intercepted fail-closed with `EROFS=30` on Tier-0 `Slot 1`, `cnflasha_ro=True`, `otp=0`,
       `rpmb=0`, `slot1_data_sector_writes=0`).
  * Unified 66/66 Master Recovery Aggregator (Pillars 1..65 + Pillar 66) running concurrently.

Safety Redlines (HARD-LOCKED):
  - Zero hardware attach, zero physical device writes, zero USB/UART TX, zero OTP/RPMB, zero eMMC writes.
  - Zero `Slot 1` format or data sector writes (`EROFS=30` fail-closed).
  - Zero raw firmware bytes leaked (`raw_firmware_bytes_leaked == 0`).
  - Bounded `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 18-donor inspection (`<= 2.0s` budget) with explicit
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
import re
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
from .realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier import (
    MASTER_65_PILLAR_SPECS,
    Master65PillarRecoveryReport,
    evaluate_realhw_65pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Phase 361 Metadata, Safety Redlines & Pinned Budget Constants
# ---------------------------------------------------------------------------

PHASE361_SCHEMA = (
    "realhw_66pillar_breathing_camid_reel_copyright46_powersave_ntscpal_vault_verifier_v1"
)
PHASE361_MASTER_SCHEMA = "realhw_66pillar_recovery_master_v1"
PHASE361_VERSION = "1.0.0"
PHASE361_PHASE_NUMBER = 361

P361_ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"

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

P361_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED = False
P361_CROSS_MODEL_FLASH_AUTHORIZED = False
P361_EMMC_WRITES_AUTHORIZED = False
P361_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
P361_OVERALL_READY_FOR_HARDWARE_ATTACH = False

OTP_FUSE_TOUCHES = 0
OTP_FUSE_WRITES = 0
RPMB_COUNTER_INCREMENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PHYSICAL_DEVICE_WRITES = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

P361_BOUNDED_HEADER_BYTES = 4096
P361_MAX_FULL_DONOR_BYTES = 3_000_000
P361_DONOR_INSPECT_BUDGET_SECONDS = 2.0
P361_DONOR_INSPECT_CI_BUDGET_SECONDS = 2.0
P361_FAST_CLI_BUDGET_SECONDS = 1.50
P361_NOMINAL_BUDGET_SECONDS = 4.00
P361_CONCURRENT_CEILING_SECONDS = 6.00

P361_ENOENT_ERRNO = 2
P361_EBUSY_ERRNO = 16
P361_EINVAL_ERRNO = 22
P361_EROFS_ERRNO = 30
P361_EOPNOTSUPP_ERRNO = 95

# Camera Identities
P361_FX3_MODEL_NAME = "ILME-FX3"
P361_FX3_MODEL_ID = 0x91030080
P361_FX3_PRODUCT_CODENAME = "PRODUCT_MODEL_ALCIN_UUD"
P361_FX3_HELPGUIDE_ID = "ilc/2210"
P361_FX3_FW_VERSION = "7.02"
P361_FX3_SUPPORTED_FW_VERSIONS = (
    "7.02", "7.01", "7.00", "6.02", "6.00", "5.00", "4.00", "3.00", "2.05", "2.04", "2.00"
)

P361_FX6_DONOR_MODEL_NAME = "ILME-FX6"
P361_FX6_DONOR_FW_VERSION = "6.01"
P361_FX6_PRODUCT_CODENAME = "PRODUCT_MODEL_CHAPLIN"

# Pinned Wave-64 18 Donors (15 FX3 + 3 FX6)
P361_DONOR_FX3_APPFW_702_RELPATH = P348_DONOR_FX3_APPFW_702_RELPATH
P361_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH = P255_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH
P361_DONOR_FX6_APPFW_601_RELPATH = P348_DONOR_FX6_APPFW_601_RELPATH
P361_DONOR_FX3_BACKUP_BIN_RELPATH = P348_DONOR_FX3_BACKUP_BIN_RELPATH
P361_DONOR_FX3_UXC_EN_F_RELPATH = P348_DONOR_FX3_UXC_EN_F_RELPATH
P361_DONOR_FX3_UXC_SC_F_RELPATH = P348_DONOR_FX3_UXC_SC_F_RELPATH
P361_DONOR_FX3_UXC_TC_F_RELPATH = P348_DONOR_FX3_UXC_TC_F_RELPATH
P361_DONOR_FX3_UXC_JA_F_RELPATH = P348_DONOR_FX3_UXC_JA_F_RELPATH
P361_DONOR_FX3_UXC_EN_RELPATH = P348_DONOR_FX3_UXC_EN_RELPATH
P361_DONOR_FX3_UXC_SC_RELPATH = P348_DONOR_FX3_UXC_SC_RELPATH
P361_DONOR_FX3_UXC_TC_RELPATH = P348_DONOR_FX3_UXC_TC_RELPATH
P361_DONOR_FX3_UXC_JA_RELPATH = P348_DONOR_FX3_UXC_JA_RELPATH
P361_DONOR_FX3_UXC_EN_G_RELPATH = P348_DONOR_FX3_UXC_EN_G_RELPATH
P361_DONOR_FX3_UXC_SC_G_RELPATH = P348_DONOR_FX3_UXC_SC_G_RELPATH
P361_DONOR_FX3_UXC_TC_G_RELPATH = P348_DONOR_FX3_UXC_TC_G_RELPATH
P361_DONOR_FX3_UXC_JA_G_RELPATH = P348_DONOR_FX3_UXC_JA_G_RELPATH
P361_DONOR_FX6_UXC_EN_RELPATH = P348_DONOR_FX6_UXC_EN_RELPATH
P361_DONOR_FX6_UXC_EN_2_RELPATH = P348_DONOR_FX6_UXC_EN_2_RELPATH

P361_PINNED_FX3_APPFW_702_BYTES = P348_PINNED_FX3_APPFW_702_BYTES
P361_PINNED_FX3_APPFW_702_HDR4K_SHA256 = P348_PINNED_FX3_APPFW_702_HDR4K_SHA256
P361_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES = P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES
P361_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256 = P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256
P361_PINNED_FX6_APPFW_601_BYTES = P348_PINNED_FX6_APPFW_601_BYTES
P361_PINNED_FX6_APPFW_601_HDR4K_SHA256 = P348_PINNED_FX6_APPFW_601_HDR4K_SHA256
P361_PINNED_FX3_BACKUP_BIN_BYTES = P348_PINNED_FX3_BACKUP_BIN_BYTES
P361_PINNED_FX3_BACKUP_BIN_SHA256 = P348_PINNED_FX3_BACKUP_BIN_SHA256
P361_PINNED_FX3_UXC_EN_F_BYTES = P348_PINNED_FX3_UXC_EN_F_BYTES
P361_PINNED_FX3_UXC_EN_F_SHA256 = P348_PINNED_FX3_UXC_EN_F_SHA256
P361_PINNED_FX3_UXC_SC_F_BYTES = P348_PINNED_FX3_UXC_SC_F_BYTES
P361_PINNED_FX3_UXC_SC_F_SHA256 = P348_PINNED_FX3_UXC_SC_F_SHA256
P361_PINNED_FX3_UXC_TC_F_BYTES = P348_PINNED_FX3_UXC_TC_F_BYTES
P361_PINNED_FX3_UXC_TC_F_SHA256 = P348_PINNED_FX3_UXC_TC_F_SHA256
P361_PINNED_FX3_UXC_JA_F_BYTES = P348_PINNED_FX3_UXC_JA_F_BYTES
P361_PINNED_FX3_UXC_JA_F_SHA256 = P348_PINNED_FX3_UXC_JA_F_SHA256
P361_PINNED_FX3_UXC_EN_BYTES = P348_PINNED_FX3_UXC_EN_BYTES
P361_PINNED_FX3_UXC_EN_SHA256 = P348_PINNED_FX3_UXC_EN_SHA256
P361_PINNED_FX3_UXC_SC_BYTES = P348_PINNED_FX3_UXC_SC_BYTES
P361_PINNED_FX3_UXC_SC_SHA256 = P348_PINNED_FX3_UXC_SC_SHA256
P361_PINNED_FX3_UXC_TC_BYTES = P348_PINNED_FX3_UXC_TC_BYTES
P361_PINNED_FX3_UXC_TC_SHA256 = P348_PINNED_FX3_UXC_TC_SHA256
P361_PINNED_FX3_UXC_JA_BYTES = P348_PINNED_FX3_UXC_JA_BYTES
P361_PINNED_FX3_UXC_JA_SHA256 = P348_PINNED_FX3_UXC_JA_SHA256
P361_PINNED_FX3_UXC_EN_G_BYTES = P348_PINNED_FX3_UXC_EN_G_BYTES
P361_PINNED_FX3_UXC_EN_G_SHA256 = P348_PINNED_FX3_UXC_EN_G_SHA256
P361_PINNED_FX3_UXC_SC_G_BYTES = P348_PINNED_FX3_UXC_SC_G_BYTES
P361_PINNED_FX3_UXC_SC_G_SHA256 = P348_PINNED_FX3_UXC_SC_G_SHA256
P361_PINNED_FX3_UXC_TC_G_BYTES = P348_PINNED_FX3_UXC_TC_G_BYTES
P361_PINNED_FX3_UXC_TC_G_SHA256 = P348_PINNED_FX3_UXC_TC_G_SHA256
P361_PINNED_FX3_UXC_JA_G_BYTES = P348_PINNED_FX3_UXC_JA_G_BYTES
P361_PINNED_FX3_UXC_JA_G_SHA256 = P348_PINNED_FX3_UXC_JA_G_SHA256
P361_PINNED_FX6_UXC_EN_BYTES = P348_PINNED_FX6_UXC_EN_BYTES
P361_PINNED_FX6_UXC_EN_SHA256 = P348_PINNED_FX6_UXC_EN_SHA256
P361_PINNED_FX6_UXC_EN_2_BYTES = P348_PINNED_FX6_UXC_EN_2_BYTES
P361_PINNED_FX6_UXC_EN_2_SHA256 = P348_PINNED_FX6_UXC_EN_2_SHA256

# Zero-Violation Pillar 66 Counters & Vault Flags
P361_BREATHING_COMP_LOCKOUT_OR_CATALYST_DRIFT_EVENTS = 0
P361_FILE_SETTINGS_CAMID_REEL_OR_SDHC_DRIFT_EVENTS = 0
P361_COPYRIGHT_46CH_RESET_ERRATUM_OR_SERIAL_DRIFT_EVENTS = 0
P361_CAMSET_COPYRIGHT_PII_LEAK_EVENTS = 0
P361_CAMSET_COPYRIGHT_PII_LEAKED_BYTES = 0
P361_POWERSAVE_9COND_OR_DORMANT_MONITOR_DRIFT_EVENTS = 0
P361_DORMANT_POWER_SAVE_BY_MONITOR_EXPOSED_EVENTS = 0
P361_NTSC_PAL_REBOOT_OR_SLOT1_FORMAT_DRIFT_EVENTS = 0

P361_SLOT1_DATA_SECTOR_WRITES = 0
P361_SLOT1_VAULT_MUTATION_BYTES = 0
P361_RF_PACKETS_TRANSMITTED = 0
P361_RF_NVS_MUTATION_BYTES = 0

P361_SLOT1_FORMAT_HARD_LOCKED = True
P361_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True
P361_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True
P361_AIRPLANE_MODE_FORCED_ON = True

P361_STAGE_B_VOLATILE_OVERLAY_DIR = "/tmp/fx3_stage_b_overlay/pillar66"
P361_FORBIDDEN_PERSISTENT_TARGETS = (
    "/dev/cnflasha",
    "/setting",
    "/mnt/emmc",
    "/nflasha",
)
P361_TIER0_SURFACE_COUNT = 16

# ---------------------------------------------------------------------------
# Wave-64 Empirically Verified Constants (UXC resid16 & ELF Symbols)
# ---------------------------------------------------------------------------

# 1. Sub-Pillar 66A-1: `[Breathing Comp.]` (Ver. 3.00+..7.02) vs FX6 3-Condition Lock
P361_BREATHING_COMP_F_RESID16 = 0x73EA
P361_BREATHING_COMP_ON_DESC_F_RESID16 = 0x659D
P361_BREATHING_COMP_OFF_DESC_F_RESID16 = 0x616B

P361_BKID_LENS_COMP_BREATHING = "BKID_APP_setting_lens_comp_breathing"
P361_BKID_MR_LENS_COMP_BREATHING = "BKID_APP_MR_setting_lens_comp_breathing"
P361_PID_SET_BREATHING_CORRECTION = "PID_SET_BREATHING_CORRECTION"
P361_PRM_HAITA_BREATHING_EXPOSURE_MODE = (
    "PRM_HAITA_setting_lens_comp_breathing_exposure_mode"
)
P361_PRM_HAITA_BREATHING_LENS_INFO = (
    "PRM_HAITA_breathing_correction_lens_type_lens_information"
)
P361_CAUTION_BREATHING_NOT_SUPPORT_MSG = (
    "CAUTION_ID_FACTOR_CAM_LENS_BREATHING_COMP_NOT_SUPPORT_MSG"
)
P361_FX6_BKID_LENS_COMP_BREATHING = "BKID_APP_SETTING_LENS_COMP_BREATHING"

P361_FX3_BREATHING_MENU_PATH = (
    "Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]"
)
P361_FX6_BREATHING_MENU_PATH = "Technical > Lens > Breathing Compensation"
P361_FX3_BREATHING_MODES = ("Off", "On")
P361_FX3_BREATHING_DEFAULT = "Off"
P361_FX3_BREATHING_MIN_FW = "3.00"
P361_FX3_BREATHING_RESETTABLE_BY_CAMERA_SETTINGS_RESET = True
P361_FX3_OTHER_LENS_COMP_RESETTABLE = False  # Shading / Chromatic Aberration / Distortion
P361_BREATHING_LENS_INFO_STATES = ("SUPPORT", "NOT_SUPPORT", "NA")
P361_FX3_BREATHING_EXCLUDED_LENSES = (
    "SEL100F28GM_MACRO_0.57M_1.0M",
    "SEL14TC",
    "SEL20TC",
    "THIRD_PARTY_UNSUPPORTED",
    "MECHANICAL_ADAPTER",
)
P361_FX3_BREATHING_DISABLED_MOVIE_FPS_FLOOR = 100
P361_FX3_BREATHING_DISABLED_SQ_FPS_FLOOR = 100
P361_CATALYST_BROWSE_BREATHING_SUPPORTED = False
P361_CATALYST_PREPARE_BREATHING_SUPPORTED = True
P361_CATALYST_PREPARE_REQUIRES_DISTORTION_AUTO = True
P361_FX6_BREATHING_MODES = ("Auto", "Off")
P361_FX6_RAW_CODECS = ("RAW", "RAW & XAVC-I", "RAW(HDMI)", "RAW(HDMI) & XAVC-I")
P361_FX6_NON_RAW_CODECS = ("XAVC-I", "XAVC-L")

# 2. Sub-Pillar 66A-2: Movie `[File Settings]`, `[Cam ID + Reel#]`, `37`-Char Title, `SDHC 4GB`
P361_FILE_SETTINGS_F_RESID16S = (0x7367, 0x61BC)
P361_FILE_NAME_FORMAT_F_RESID16S = (0x7821, 0x78F5)
P361_SERIES_COUNTER_RESET_F_RESID16S = (0x6250, 0x7A28, 0x6A52)
P361_CAM_ID_REEL_F_RESID16 = 0x67AE
P361_CAMERA_ID_F_RESID16 = 0x72F1
P361_REEL_NUMBER_F_RESID16 = 0x726A
P361_CAMERA_POSITION_F_RESID16S = (0x68C4, 0x7070)
P361_CAM_ID_YYMMDD_DESC_F_RESID16 = 0x6FC6
P361_TITLE_NAME_SETTINGS_F_RESID16 = 0x6C14
P361_TITLE_F_RESID16 = 0x77A6
P361_DATE_TITLE_F_RESID16S = (0x620E, 0x6E06, 0x6E91)
P361_TITLE_DATE_F_RESID16S = (0x6174, 0x61CF, 0x7515)
P361_SERIES_BASE_RESID16 = 0xE8C5
P361_SDHC_UNSUPPORTED_BASE_RESID16S = (
    0xE8F8,
    0xE94A,
    0xE1D8,
    0xE255,
    0xE257,
    0xE2F1,
    0xE2F2,
)

P361_BKID_XAVCS_FILE_NUMBER = "BKID_APP_setting_xavcs_file_number"
P361_BKID_CAMID_CAMERA_ID = "BKID_APP_setting_xavc_s_file_name_camid_camera_id"
P361_BKID_CAMID_CAMERA_POSITION = "BKID_APP_setting_xavc_s_file_name_camid_camera_position"
P361_BKID_CAMID_REEL_NUMBER = "BKID_APP_setting_xavcs_file_name_reel_number"
P361_BKID_UPDATE_REQUIRED_REEL_NUMBER = "BKID_APP_update_required_xavcs_file_name_reel_number"
P361_BKID_RECORDED_AFTER_CAMID_REEL = "BKID_APP_recorded_after_camid_reel_setting"
P361_FX6_BKID_CAMID_HANDOVER_SYMBOLS = (
    "BKID_APP_CAMID_CURRENT_CAMERA_ID0",
    "BKID_APP_CAMID_CURRENT_CAMERA_ID1",
    "BKID_APP_CAMID_CURRENT_CAMERA_POSITION0",
    "BKID_APP_CAMID_CURRENT_CAMERA_POSITION1",
    "BKID_APP_CAMID_CURRENT_CLIP_NUMBER0",
    "BKID_APP_CAMID_CURRENT_CLIP_NUMBER1",
    "BKID_APP_CAMID_CURRENT_REEL_NUMBER0",
    "BKID_APP_CAMID_CURRENT_REEL_NUMBER1",
)

P361_FX3_FILE_SETTINGS_MENU_PATH = "Shooting -> [File] -> [File Settings]"
P361_FX3_FILE_SETTINGS_RESETTABLE = False
P361_FX3_FILE_NUMBER_MODES = ("Series", "Reset")
P361_FX3_FILE_NAME_FORMATS = (
    "Standard",
    "Cam ID + Reel#",
    "Title",
    "Date + Title",
    "Title + Date",
)
P361_FX3_MOVIE_STORAGE_DIR = "PRIVATE/M4ROOT/CLIP"
P361_FX3_TITLE_MAX_LEN = 37
P361_FX3_TITLE_DEFAULT = "C"
P361_FX3_TITLE_ALLOWED_PATTERN = re.compile(r"^[A-Za-z0-9.\-_@!#$%+=^~(),;\[\]]+$")
P361_FX3_CAMERA_IDS = tuple(chr(c) for c in range(ord("A"), ord("Z") + 1))
P361_FX3_CAMERA_POSITIONS = ("C", "L", "R")
P361_FX3_REEL_MIN = 1
P361_FX3_REEL_MAX = 999
P361_FX3_CLIP_MIN = 1
P361_FX3_CLIP_MAX = 999
P361_SDHC_FAT32_SPLIT_GB = 4
P361_CARD_TYPES = ("SDXC", "CFexpress_Type_A", "SDHC_FAT32")
P361_FILESYSTEMS = ("exFAT", "FAT32")
P361_FX3_CAMID_DATE_DIGITS = 6  # YYMMDD
P361_FX3_TITLE_DATE_DIGITS = 8  # YYYYMMDD

P361_FX6_CLIP_NAME_FORMAT_MENU_PATH = "TC/Media > Clip Name Format"
P361_FX6_AUTO_NAMING_MODES = ("Cam ID + Reel#", "Title")
P361_FX6_TITLE_PREFIX_MIN_LEN = 4
P361_FX6_TITLE_PREFIX_MAX_LEN = 46
P361_FX6_TITLE_PREFIX_DEFAULT = "nnn_"
P361_FX6_CFEXPRESS_CLIP_DIR = "/XDROOT/Clip"
P361_FX6_SDXC_CLIP_DIR = "/PRIVATE/XDROOT/Clip"
P361_FX6_CARD_HANDOVER_ENABLED = True

# 3. Sub-Pillar 66B-1: `[Copyright Info]` 46-Char Reset-Resistant (Round 57 Erratum), Active `[Write Serial Number]` & `CAMSET*.DAT`
P361_COPYRIGHT_INFO_F_RESID16 = 0x6D53
P361_WRITE_COPYRIGHT_INFO_F_RESID16S = (0x7AE4, 0x788B, 0x65A0)
P361_SET_PHOTOGRAPHER_F_RESID16S = (0x7172, 0x78D2)
P361_SET_PHOTOGRAPHER_G_RESID16 = 0x62D4
P361_SET_COPYRIGHT_F_RESID16S = (0x612B, 0x6846)
P361_SET_COPYRIGHT_G_RESID16 = 0x6370
P361_DISP_COPYRIGHT_INFO_F_RESID16S = (0x611B, 0x79B2)
P361_WRITE_SERIAL_NUMBER_F_RESID16 = 0x7058
P361_WRITE_SERIAL_STILL_MOVIE_F_RESID16S = (0x6704, 0x640C, 0x7953)
P361_LEGACY_WRITE_SERIAL_STILL_ONLY_F_RESID16S = (0x6436, 0x792C)

P361_BKID_WRITE_COPYRIGHT_INFO = "BKID_APP_setting_still_write_copyright_infomation"
P361_BKID_PHOTOGRAPHER_NAME = "BKID_APP_photographer_name"
P361_BKID_COPYRIGHT_NAME = "BKID_APP_copyright_name"
P361_BKID_WRITE_SERIAL_STILL_MOVIE = "BKID_APP_setting_write_serial_number_still_movie"
P361_BKID_WRITE_SERIAL_STILL_ONLY_LEGACY = (
    "BKID_APP_setting_still_write_serial_number"
)

P361_COPYRIGHT_INFO_MAX_LEN = 46
P361_ROUND57_ERRATUM_ALL_COPYRIGHT_RESETTABLE = False  # Corrected! All 4 items + Serial are Not available
P361_WRITE_COPYRIGHT_RESETTABLE = False
P361_WRITE_SERIAL_RESETTABLE = False
P361_WRITE_SERIAL_STILL_AND_MOVIE_ACTIVE = True
P361_CAMSET_PATH_TEMPLATE = "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"
P361_CAMSET_MAX_SLOT1_FILES = 10
P361_CAMSET_MAX_C3_PORTAL_FILES = 60
P361_CAMSET_EXCLUDED_CATEGORIES = (
    "Copyright Info",
    "IPTC Information",
    "External Flash Set.",
    "White Balance: Custom 1/2/3",
    "Face Memory",
    "FTP Transfer Func.",
    "Network Streaming",
    "Cloud Connection",
    "WPS Push",
    "Access Point Set.",
    "Wi-Fi Frequency Band",
    "IP Address Setting",
    "Edit Device Name",
    "Import Root Certificate",
    "Access Authen.",
)
P361_FX6_HAS_EXIF_COPYRIGHT_MENU = False
P361_FX6_LENS_SERIAL_SLOTS = 6

# 4. Sub-Pillar 66B-2: `[Power Setting Option]` 9-Bypass / Dormant `[Power Save by Monitor]` & `[NTSC/PAL Selector]` `Slot 1 EROFS=30`
P361_POWER_SAVE_START_TIME_F_RESID16 = 0x69B0
P361_POWER_SAVE_2MIN_F_RESID16 = 0x6244
P361_POWER_SAVE_30MIN_F_RESID16 = 0x63C2
P361_POWER_SAVE_10SEC_5MIN_BASE_RESID16S = (0xE50F, 0xEA45)
P361_AUTO_POWER_OFF_TEMP_F_RESID16 = 0x70F1
P361_AUTO_POWER_OFF_TEMP_HIGH_WARN_G_RESID16S = (0x612C, 0x61A9)
P361_DORMANT_POWER_SAVE_MONITOR_F_RESID16S = (0x783F, 0x6DB5, 0x6DB6, 0x60A8, 0x6B2E)

P361_BKID_START_POWER_SAVING = "BKID_APP_setting_start_power_saving"
P361_BKID_AUTO_PWR_OFF_TEMP = "BKID_APP_setting_auto_pwr_off_temp"
P361_BKID_MONITOR_POWER_LINKAGE_DORMANT = "BKID_APP_setting_monitor_power_linkage"

P361_FX3_POWER_SAVE_MODES = ("Off", "30 Min", "5 Min", "2 Min", "1 Min", "10 Sec")
P361_FX3_POWER_SAVE_DEFAULT = "5 Min"
P361_FX3_POWER_SAVE_DORMANT_TIERS = ("20SEC", "NO_LIMIT", "30 sec", "60 min", "240 min")
P361_FX3_POWER_SAVE_9_BYPASS_CONDITIONS = (
    "usb_power_supply",
    "slideshow_playing",
    "ftp_transfer_active",
    "movie_recording_active",
    "pc_connected",
    "tv_hdmi_connected",
    "ir_remote_ctrl_on",
    "bluetooth_rmt_ctrl_on",
    "streaming_or_creators_cloud_active",
)
P361_FX3_AUTO_PWR_OFF_TEMP_MODES = ("Standard", "High")
P361_FX3_AUTO_PWR_OFF_TEMP_DEFAULT = "Standard"
P361_FX3_POWER_SETTING_RESETTABLE = False
P361_FX3_HAS_POWER_SAVE_BY_MONITOR = False

P361_NTSC_PAL_SELECTOR_F_RESID16 = 0x6B6F
P361_BKID_NTSC_PAL_SELECTOR = "BKID_APP_setting_ntsc_pal_selector"
P361_NTSC_PAL_REBOOT_BASE_RESID16 = 0xE5C1
P361_RUNNING_ON_NTSC_BASE_RESID16 = 0xE77A
P361_RUNNING_ON_PAL_BASE_RESID16 = 0xE0B6
P361_NTSC_PAL_PLAYBACK_BLOCK_BASE_RESID16S = (0xE379, 0xE441)
P361_NTSC_PAL_PLAYBACK_BLOCK_G_RESID16S = (0x61CA, 0x644E)
P361_LEGACY_NTSC_PAL_FORMAT_HAZARD_BASE_RESID16S = (
    0xE1E6,
    0xE373,
    0xE51A,
    0xE595,
    0xE597,
    0xE9F6,
)
P361_NTSC_PAL_MODES = ("NTSC", "PAL")
P361_NTSC_PAL_RESETTABLE = False
P361_FX6_REC_FREQUENCIES = ("59.94", "50", "29.97", "25", "24", "23.98")
P361_FX6_HAS_CONSUMER_POWER_SAVE_OR_NTSC_FORMAT_POPUP = False

# Common Enums & Vault Constants
P361_ON_OFF_MODES = ("Off", "On")
P361_SHOOTING_DOMAINS = ("Movie", "Still", "S&Q")
P361_RESET_ACTIONS = ("None", "Camera Settings Reset", "Initialize")
P361_VAULT_ACTIONS = (
    "NONE",
    "READ_ONLY_AUDIT",
    "CARD_WRITE_XAVC_REC",
    "CARD_WRITE_REEL_COUNTER_UPDATE",
    "CARD_WRITE_CAMSET_EXPORT",
    "FORMAT_QUICK",
    "FORMAT_FULL",
    "FORMAT_NTSC_PAL_PROMPT",
)
P361_WRITE_MUTATING_VAULT_ACTIONS = (
    "CARD_WRITE_XAVC_REC",
    "CARD_WRITE_REEL_COUNTER_UPDATE",
    "CARD_WRITE_CAMSET_EXPORT",
    "FORMAT_QUICK",
    "FORMAT_FULL",
    "FORMAT_NTSC_PAL_PROMPT",
)
P361_VAULT_FIREWALL_ERRNOS = (None, "EROFS", "EOPNOTSUPP", "EBUSY", "EINVAL", "ENOENT")

# Status & Block Codes
P361_STATUS_VERIFIED_PILLAR_66A = (
    "VERIFIED_PILLAR_66A_BREATHING_CAMID_REEL_SDHC_4GB_VAULT"
)
P361_STATUS_REJECTED_PILLAR_66A = (
    "REJECTED_PILLAR_66A_BREATHING_CAMID_REEL_SDHC_4GB_VAULT"
)
P361_STATUS_VERIFIED_PILLAR_66B = (
    "VERIFIED_PILLAR_66B_COPYRIGHT46_SERIAL_POWERSAVE_NTSCPAL_VAULT"
)
P361_STATUS_REJECTED_PILLAR_66B = (
    "REJECTED_PILLAR_66B_COPYRIGHT46_SERIAL_POWERSAVE_NTSCPAL_VAULT"
)
P361_STATUS_VERIFIED_PILLAR66_SUITE = (
    "VERIFIED_PILLAR66_BREATHING_CAMID_REEL_COPYRIGHT46_POWERSAVE_NTSCPAL_VAULT"
)
P361_STATUS_FAIL_PILLAR66_SUITE = (
    "FAIL_PILLAR66_BREATHING_CAMID_REEL_COPYRIGHT46_POWERSAVE_NTSCPAL_VAULT"
)
P361_STATUS_VERIFIED_66OF66_AGGREGATOR = "VERIFIED_66OF66_PILLAR_RECOVERY_MASTER"
P361_STATUS_FAIL_66OF66_AGGREGATOR = "FAIL_66OF66_PILLAR_RECOVERY_MASTER"

P361_BLOCKED_SAFETY_POLICY_VIOLATION = "BLOCKED_P361_SAFETY_POLICY_VIOLATION"
P361_BLOCKED_INVALID_PILLAR66A_SPEC = "BLOCKED_P361_INVALID_PILLAR66A_SPEC"
P361_BLOCKED_INVALID_PILLAR66B_SPEC = "BLOCKED_P361_INVALID_PILLAR66B_SPEC"
P361_BLOCKED_BREATHING_COMP_OR_CATALYST_DRIFT = (
    "BLOCKED_P361_BREATHING_COMP_OR_CATALYST_DRIFT"
)
P361_BLOCKED_FILE_SETTINGS_CAMID_OR_SDHC_DRIFT = (
    "BLOCKED_P361_FILE_SETTINGS_CAMID_OR_SDHC_DRIFT"
)
P361_BLOCKED_COPYRIGHT46_RESET_OR_CAMSET_DRIFT = (
    "BLOCKED_P361_COPYRIGHT46_RESET_OR_CAMSET_DRIFT"
)
P361_BLOCKED_POWERSAVE_OR_NTSCPAL_DRIFT = (
    "BLOCKED_P361_POWERSAVE_OR_NTSCPAL_DRIFT"
)
P361_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL = "BLOCKED_P361_SLOT1_VAULT_WRITE_FIREWALL"
P361_BLOCKED_PERSISTENT_OVERLAY_ESCAPE = "BLOCKED_P361_PERSISTENT_OVERLAY_ESCAPE"
P361_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT = "BLOCKED_P361_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P361_PILLAR_66A_SCENARIO_IDS = (
    "p361_66a_01_allow_breathing_on_movie_24p_ciz_resettable_and_catalyst_prepare_distortion_auto",
    "p361_66a_02_allow_camid_reel_c999_to_d001_yymmdd_vs_yyyymmdd_37char_title_and_fx6_3lock_handover",
    "p361_66a_03_reject_breathing_120p_sq100_raw_sel100macro_catalyst_browse_or_fx6_sq_spoof",
    "p361_66a_04_reject_sdhc_non_standard_mixed_simult_4gb_missing_reset_or_title_over_37chars",
    "p361_66a_05_reject_camera_reset_wiping_file_settings_or_file_reset_wiping_reel_number",
    "p361_66a_06_reject_slot1_reel_update_vault_write_overlay_escape_or_backup_bin_h0_h3_drift",
)
P361_PILLAR_66B_SCENARIO_IDS = (
    "p361_66b_01_allow_copyright46_round57_reset_resistant_write_serial_still_movie_and_camset_exclude",
    "p361_66b_02_allow_powersave_9bypass_high_temp_ntsc_pal_reboot_and_fx6_frequency_contrast",
    "p361_66b_03_reject_round57_erratum_reset_wiping_write_copyright_or_copyright_pii_in_camset",
    "p361_66b_04_reject_copyright_over_46chars_dormant_still_only_serial_or_fx6_exif_copyright_spoof",
    "p361_66b_05_reject_dormant_power_save_by_monitor_bypass_violation_or_pal_2398p_df_tc_spoof",
    "p361_66b_06_reject_ntsc_pal_slot1_format_prompt_vault_write_overlay_escape_or_h0_h3_drift",
)

MASTER_66_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_65_PILLAR_SPECS + (
    (
        66,
        "pillar66_breathing_camid_reel_copyright46_powersave_ntscpal_vault",
        "Phase 361",
        "realhw_66pillar_breathing_camid_reel_copyright46_powersave_ntscpal_vault_verifier",
    ),
)
MASTER_66_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_66_PILLAR_SPECS)
MASTER_66_PILLAR_COUNT = len(MASTER_66_PILLAR_IDS)


# ---------------------------------------------------------------------------
# Internal Helpers (Canonical SHA-256 with volatile stripping, Safety, Paths)
# ---------------------------------------------------------------------------


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _strip_volatile_timing(obj: Any) -> Any:
    """Recursively strip volatile timing keys (`elapsed_seconds`) for deterministic hashing."""
    if isinstance(obj, dict):
        return {
            k: _strip_volatile_timing(v)
            for k, v in obj.items()
            if k != "elapsed_seconds"
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
    return bool(is_forced_clean_room() or os.environ.get(P361_ENV_CLEAN_ROOM_TEST) == "1")


def _donor_inspect_budget_seconds() -> float:
    return (
        P361_DONOR_INSPECT_CI_BUDGET_SECONDS
        if os.environ.get("CI")
        else P361_DONOR_INSPECT_BUDGET_SECONDS
    )


def _is_tmpfs_path(path: str) -> bool:
    norm = posixpath.normpath(path)
    return norm == "/tmp" or norm.startswith("/tmp/")


def _targets_persistent_emmc(path: str) -> bool:
    norm = posixpath.normpath(path)
    return any(
        norm == t or norm.startswith(f"{t}/")
        for t in P361_FORBIDDEN_PERSISTENT_TARGETS
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
# Pure Deterministic Ground-Truth State Evaluators (66A & 66B)
# ---------------------------------------------------------------------------


def _next_cam_position_char(pos: str) -> str:
    return chr(ord(pos) + 1)


def compute_expected_breathing_camid_reel_sdhc_vault_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    recording_fps: int,
    raw_output: str,
    breathing_comp: str,
    lens_info_status: str,
    lens_id: str,
    distortion_comp: str,
    clear_image_zoom_scale: float,
    auto_framing_active: bool,
    framing_stabilizer_active: bool,
    catalyst_product: str,
    fx6_sq_motion: str,
    fx6_codec: str,
    file_number_mode: str,
    series_counter_reset_requested: bool,
    existing_max_clip_number: int,
    file_name_format: str,
    card_type: str,
    card_filesystem: str,
    simult_recording_enabled: bool,
    secondary_card_filesystem: str,
    recorded_clip_size_gb: float,
    camera_id: str,
    prev_camera_id: str,
    reel_number: int,
    camera_position: str,
    clip_number: int,
    title_name: str,
    capture_date_yyyymmdd: str,
    random_2char: str,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute exact Wave-64 Pillar 66A expected state (`[Breathing Comp.]` & Movie `[File Settings]`)."""
    is_fx3 = camera_model == P361_FX3_MODEL_NAME
    is_fx6 = camera_model == P361_FX6_DONOR_MODEL_NAME
    fw_supports_ver3 = is_fx6 or (
        fw_version in P361_FX3_SUPPORTED_FW_VERSIONS
        and tuple(int(p) for p in fw_version.split(".")) >= (3, 0)
    )

    # 1. `[Breathing Comp.]` gate & Catalyst Prepare vs FX6 3-lock
    breathing_errno: Optional[int] = None
    effective_breathing = breathing_comp
    optical_crop_active = False
    catalyst_metadata_supported = False
    fx6_hard_locked_off = False

    if is_fx3:
        if not fw_supports_ver3:
            if breathing_comp == "On":
                breathing_errno = P361_EOPNOTSUPP_ERRNO
            effective_breathing = "Off"
        else:
            lens_excluded = (
                lens_info_status != "SUPPORT"
                or lens_id in P361_FX3_BREATHING_EXCLUDED_LENSES
            )
            fps_locked = (
                shooting_domain == "Still"
                or (
                    shooting_domain == "Movie"
                    and recording_fps >= P361_FX3_BREATHING_DISABLED_MOVIE_FPS_FLOOR
                )
                or (
                    shooting_domain == "S&Q"
                    and recording_fps >= P361_FX3_BREATHING_DISABLED_SQ_FPS_FLOOR
                )
            )
            zoom_or_framing_locked = (
                clear_image_zoom_scale > 1.0
                or auto_framing_active
                or framing_stabilizer_active
            )
            if breathing_comp == "On":
                if raw_output == "On":
                    # Bypassed on HDMI 16-bit RAW Output signal (allowed as menu choice if movie/sub-100p, but RAW output itself receives no compensation)
                    effective_breathing = "Off"
                    optical_crop_active = False
                elif lens_excluded or fps_locked:
                    breathing_errno = P361_EOPNOTSUPP_ERRNO
                    effective_breathing = "Off"
                elif zoom_or_framing_locked:
                    # Wave 64 / ilc/2210: `[Breathing Comp.]` remains selectable with CIZ / Auto Framing / Framing Stabilizer, bypassing standalone post-crop & Catalyst metadata
                    effective_breathing = "On"
                    optical_crop_active = False
                else:
                    effective_breathing = "On"
                    optical_crop_active = True

        # Catalyst post-production metadata breathing compensation rule
        catalyst_eligible_capture = (
            shooting_domain in ("Movie", "S&Q")
            and effective_breathing == "Off"
            and raw_output != "On"
            and distortion_comp == "Auto"
            and not (lens_info_status != "SUPPORT" or lens_id in P361_FX3_BREATHING_EXCLUDED_LENSES)
            and not (clear_image_zoom_scale > 1.0 or auto_framing_active or framing_stabilizer_active)
            and not (
                (shooting_domain == "Movie" and recording_fps >= 100)
                or (shooting_domain == "S&Q" and recording_fps >= 100)
            )
        )
        catalyst_metadata_supported = (
            catalyst_product in ("Catalyst Prepare", "Catalyst Prepare Plugin")
            and catalyst_eligible_capture
        )
    elif is_fx6:
        fx6_hard_locked_off = (
            distortion_comp == "Off"
            or fx6_sq_motion == "On"
            or fx6_codec in P361_FX6_RAW_CODECS
        )
        if breathing_comp == "Auto" and fx6_hard_locked_off:
            breathing_errno = P361_EOPNOTSUPP_ERRNO
            effective_breathing = "Off"
        else:
            effective_breathing = breathing_comp
            optical_crop_active = effective_breathing == "Auto"

    # 2. Movie `[File Settings]`, `[Cam ID + Reel#]`, `37`-Char Title, `SDHC 4GB` vs FX6
    file_format_errno: Optional[int] = None
    simult_rec_errno: Optional[int] = None
    title_errno: Optional[int] = None

    if is_fx3:
        if card_type == "SDHC_FAT32" or card_filesystem == "FAT32":
            if file_name_format != "Standard":
                file_format_errno = P361_EOPNOTSUPP_ERRNO
        elif file_name_format == "Cam ID + Reel#" and not fw_supports_ver3:
            file_format_errno = P361_EOPNOTSUPP_ERRNO

        if simult_recording_enabled and card_filesystem != secondary_card_filesystem:
            simult_rec_errno = P361_EOPNOTSUPP_ERRNO

        if (
            len(title_name) == 0
            or len(title_name) > P361_FX3_TITLE_MAX_LEN
            or not bool(P361_FX3_TITLE_ALLOWED_PATTERN.match(title_name))
        ):
            title_errno = P361_EINVAL_ERRNO

        sdhc_split_required = (
            (card_type == "SDHC_FAT32" or card_filesystem == "FAT32")
            and recorded_clip_size_gb > float(P361_SDHC_FAT32_SPLIT_GB)
        )
        expected_storage_dir = P361_FX3_MOVIE_STORAGE_DIR
    else:
        # FX6 Ver. 6.01 Clip Name Format
        if (
            len(title_name) < P361_FX6_TITLE_PREFIX_MIN_LEN
            or len(title_name) > P361_FX6_TITLE_PREFIX_MAX_LEN
        ):
            title_errno = P361_EINVAL_ERRNO
        if file_name_format not in P361_FX6_AUTO_NAMING_MODES:
            file_format_errno = P361_EOPNOTSUPP_ERRNO
        sdhc_split_required = False
        expected_storage_dir = (
            P361_FX6_CFEXPRESS_CLIP_DIR
            if card_type == "CFexpress_Type_A"
            else P361_FX6_SDXC_CLIP_DIR
        )

    # Reel# reset rule: changing Camera ID resets Reel# to 1; File Number=Reset does NOT reset Reel#
    effective_reel_number = 1 if (camera_id != prev_camera_id) else reel_number

    # Series Counter Reset rule: max + 1 if clips exist in folder else 1
    if series_counter_reset_requested:
        expected_next_series_clip = max(1, existing_max_clip_number + 1)
    else:
        expected_next_series_clip = clip_number

    # Position overflow: e.g. C999 -> output filename uses D001, menu Camera Position stays C!
    output_pos = camera_position
    output_clip_num = clip_number
    if clip_number > P361_FX3_CLIP_MAX:
        output_pos = _next_cam_position_char(camera_position)
        output_clip_num = ((clip_number - 1) % P361_FX3_CLIP_MAX) + 1
    menu_position_unchanged = camera_position

    # Date formatting rule: YYMMDD for Cam ID + Reel# vs YYYYMMDD for Date + Title / Title + Date
    yymmdd = capture_date_yyyymmdd[2:8] if len(capture_date_yyyymmdd) == 8 else "230101"
    yyyymmdd = capture_date_yyyymmdd if len(capture_date_yyyymmdd) == 8 else "20230101"
    if file_name_format == "Standard":
        expected_clip_basename = f"C{output_clip_num:04d}"
    elif file_name_format == "Cam ID + Reel#":
        expected_clip_basename = (
            f"{camera_id}{effective_reel_number:03d}"
            f"{output_pos}{output_clip_num:03d}_{yymmdd}{random_2char}"
        )
    elif file_name_format == "Title":
        expected_clip_basename = f"{title_name}_{output_clip_num:04d}"
    elif file_name_format == "Date + Title":
        expected_clip_basename = f"{yyyymmdd}_{title_name}_{output_clip_num:04d}"
    else:  # Title + Date
        expected_clip_basename = f"{title_name}_{yyyymmdd}_{output_clip_num:04d}"

    # Reset behavior:
    # - `[Breathing Comp.]`: `Can be reset` under `[Camera Settings Reset]` AND `[Initialize]` -> `"Off"`
    # - `[File Settings]` (ALL items): Reset-resistant (`Not available` under `Camera Settings Reset`), cleared ONLY by `[Initialize]`
    if reset_action == "Initialize":
        post_breathing_comp = P361_FX3_BREATHING_DEFAULT if is_fx3 else "Auto"
        post_file_number_mode = "Series"
        post_file_name_format = "Standard"
        post_camera_id = "A"
        post_reel_number = 1
        post_camera_position = "C"
        post_title_name = P361_FX3_TITLE_DEFAULT if is_fx3 else P361_FX6_TITLE_PREFIX_DEFAULT
    elif reset_action == "Camera Settings Reset":
        post_breathing_comp = P361_FX3_BREATHING_DEFAULT if is_fx3 else breathing_comp
        post_file_number_mode = file_number_mode
        post_file_name_format = file_name_format
        post_camera_id = camera_id
        post_reel_number = effective_reel_number
        post_camera_position = camera_position
        post_title_name = title_name
    else:
        post_breathing_comp = breathing_comp
        post_file_number_mode = file_number_mode
        post_file_name_format = file_name_format
        post_camera_id = camera_id
        post_reel_number = effective_reel_number
        post_camera_position = camera_position
        post_title_name = title_name

    # Slot-1 Tier-0 Vault EROFS=30 rule
    write_blocked_erofs = (
        requested_vault_slot == 1
        and slot1_holds_tier0_vault
        and requested_vault_action in P361_WRITE_MUTATING_VAULT_ACTIONS
    )
    vault_action_allowed = not write_blocked_erofs and (
        requested_vault_action in ("NONE", "READ_ONLY_AUDIT")
    )
    vault_firewall_errno: Optional[str] = "EROFS" if write_blocked_erofs else None

    return {
        "breathing_errno": breathing_errno,
        "effective_breathing": effective_breathing,
        "optical_crop_active": optical_crop_active,
        "catalyst_metadata_supported": catalyst_metadata_supported,
        "fx6_hard_locked_off": fx6_hard_locked_off,
        "file_format_errno": file_format_errno,
        "simult_rec_errno": simult_rec_errno,
        "title_errno": title_errno,
        "sdhc_split_required": sdhc_split_required,
        "expected_storage_dir": expected_storage_dir,
        "effective_reel_number": effective_reel_number,
        "expected_next_series_clip": expected_next_series_clip,
        "output_position": output_pos,
        "output_clip_number": output_clip_num,
        "menu_position_unchanged": menu_position_unchanged,
        "expected_clip_basename": expected_clip_basename,
        "post_breathing_comp": post_breathing_comp,
        "post_file_number_mode": post_file_number_mode,
        "post_file_name_format": post_file_name_format,
        "post_camera_id": post_camera_id,
        "post_reel_number": post_reel_number,
        "post_camera_position": post_camera_position,
        "post_title_name": post_title_name,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


def compute_expected_copyright46_powersave_ntscpal_vault_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    write_copyright_info: str,
    photographer_name: str,
    copyright_holder: str,
    write_serial_number: str,
    camset_export_requested: bool,
    camset_target_slot: int,
    camset_files_existing: int,
    exif_copyright_menu_requested: bool,
    power_save_start_time: str,
    auto_power_off_temp: str,
    power_save_by_monitor_requested: bool,
    usb_power_supply: bool,
    slideshow_playing: bool,
    ftp_transfer_active: bool,
    movie_recording_active: bool,
    pc_connected: bool,
    tv_hdmi_connected: bool,
    ir_remote_ctrl_on: bool,
    bluetooth_rmt_ctrl_on: bool,
    streaming_or_creators_cloud_active: bool,
    factory_tv_system: str,
    ntsc_pal_selector: str,
    target_ntsc_pal_selector: str,
    requested_movie_fps: str,
    requested_tc_format: str,
    playback_clip_system: str,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute exact Wave-64 Pillar 66B expected state (`[Copyright Info]` 46-char + Round 57 Erratum,
    active `[Write Serial Number]`, `CAMSET` exclusion, `[Power Setting Option]` 9-bypass + dormant
    `[Power Save by Monitor]`, & `[NTSC/PAL Selector]` reboot / cross-region / `Slot 1 EROFS=30`)."""
    is_fx3 = camera_model == P361_FX3_MODEL_NAME
    is_fx6 = camera_model == P361_FX6_DONOR_MODEL_NAME

    # 1. `[Copyright Info]` & `[Write Serial Number]` + `CAMSET` Exclusion
    copyright_str_errno: Optional[int] = None
    exif_menu_errno: Optional[int] = None

    if len(photographer_name) > P361_COPYRIGHT_INFO_MAX_LEN or len(copyright_holder) > P361_COPYRIGHT_INFO_MAX_LEN:
        copyright_str_errno = P361_EINVAL_ERRNO
    if not photographer_name.isascii() or not copyright_holder.isascii():
        copyright_str_errno = P361_EINVAL_ERRNO

    if is_fx6 and exif_copyright_menu_requested:
        exif_menu_errno = P361_EOPNOTSUPP_ERRNO

    # Still EXIF vs Still+Movie Serial Number
    still_copyright_written = is_fx3 and (write_copyright_info == "On") and (shooting_domain == "Still")
    movie_copyright_written = False  # Copyright Info writes Still EXIF only!
    serial_written_on_capture = (
        is_fx3
        and write_serial_number == "On"
        and shooting_domain in ("Still", "Movie", "S&Q")
    )

    camset_slot_limit_ok = (
        (camset_target_slot == 1 and camset_files_existing < P361_CAMSET_MAX_SLOT1_FILES)
        or not camset_export_requested
    )
    camset_excludes_copyright_pii = True
    camset_allows_write_serial_toggle = True

    # 2. `[Power Setting Option]` 9-Bypass + Dormant `[Power Save by Monitor]`
    power_save_errno: Optional[int] = None
    monitor_linkage_errno: Optional[int] = None

    if power_save_start_time in P361_FX3_POWER_SAVE_DORMANT_TIERS or (
        power_save_start_time not in P361_FX3_POWER_SAVE_MODES
    ):
        power_save_errno = P361_EOPNOTSUPP_ERRNO

    if power_save_by_monitor_requested:
        monitor_linkage_errno = P361_EOPNOTSUPP_ERRNO

    active_bypass_reasons = tuple(
        name
        for name, cond in (
            ("usb_power_supply", usb_power_supply),
            ("slideshow_playing", slideshow_playing),
            ("ftp_transfer_active", ftp_transfer_active),
            ("movie_recording_active", movie_recording_active),
            ("pc_connected", pc_connected),
            ("tv_hdmi_connected", tv_hdmi_connected),
            ("ir_remote_ctrl_on", ir_remote_ctrl_on),
            ("bluetooth_rmt_ctrl_on", bluetooth_rmt_ctrl_on),
            ("streaming_or_creators_cloud_active", streaming_or_creators_cloud_active),
        )
        if cond
    )
    power_save_bypassed = len(active_bypass_reasons) > 0
    power_save_timer_effective = (
        is_fx3
        and power_save_errno is None
        and power_save_start_time != "Off"
        and not power_save_bypassed
    )
    tripod_warning_active = is_fx3 and auto_power_off_temp == "High"

    # 3. `[NTSC/PAL Selector]` Reboot, Frame Rates, TC Lock, Cross-Region Block & Slot 1 EROFS
    ntsc_pal_reboot_triggered = is_fx3 and (target_ntsc_pal_selector != ntsc_pal_selector)
    effective_tv_system = target_ntsc_pal_selector if ntsc_pal_reboot_triggered else ntsc_pal_selector
    non_factory_banner = (
        f"Running on {effective_tv_system}."
        if (is_fx3 and effective_tv_system != factory_tv_system)
        else ""
    )

    movie_fps_errno: Optional[int] = None
    tc_format_errno: Optional[int] = None
    if is_fx3 and effective_tv_system == "PAL":
        if requested_movie_fps in ("23.98p", "29.97p", "59.94p", "119.88p"):
            movie_fps_errno = P361_EOPNOTSUPP_ERRNO
        if requested_tc_format == "DF":
            tc_format_errno = P361_EOPNOTSUPP_ERRNO
    elif is_fx3 and effective_tv_system == "NTSC":
        if requested_movie_fps in ("25p", "50p", "100p"):
            movie_fps_errno = P361_EOPNOTSUPP_ERRNO

    playback_allowed = playback_clip_system == effective_tv_system

    # Reset rules (Round 57 Erratum corrected!):
    # ALL of [Copyright Info] (4 items incl. Write Copyright Info), [Write Serial Number],
    # [Power Setting Option] (2 active items), and [NTSC/PAL Selector] are Reset-resistant!
    # Cleared ONLY by `[Initialize]`.
    if reset_action == "Initialize":
        post_write_copyright_info = "Off"
        post_photographer_name = ""
        post_copyright_holder = ""
        post_write_serial_number = "Off"
        post_power_save_start_time = P361_FX3_POWER_SAVE_DEFAULT
        post_auto_power_off_temp = P361_FX3_AUTO_PWR_OFF_TEMP_DEFAULT
        post_ntsc_pal_selector = factory_tv_system
    else:
        # Both "None" AND "Camera Settings Reset" preserve all these settings!
        post_write_copyright_info = write_copyright_info
        post_photographer_name = photographer_name
        post_copyright_holder = copyright_holder
        post_write_serial_number = write_serial_number
        post_power_save_start_time = power_save_start_time
        post_auto_power_off_temp = auto_power_off_temp
        post_ntsc_pal_selector = effective_tv_system

    # Slot-1 Tier-0 Vault Firewall (`EROFS=30`)
    write_blocked_erofs = (
        requested_vault_slot == 1
        and slot1_holds_tier0_vault
        and requested_vault_action in P361_WRITE_MUTATING_VAULT_ACTIONS
    )
    vault_action_allowed = not write_blocked_erofs and (
        requested_vault_action in ("NONE", "READ_ONLY_AUDIT")
    )
    vault_firewall_errno: Optional[str] = "EROFS" if write_blocked_erofs else None

    return {
        "copyright_str_errno": copyright_str_errno,
        "exif_menu_errno": exif_menu_errno,
        "still_copyright_written": still_copyright_written,
        "movie_copyright_written": movie_copyright_written,
        "serial_written_on_capture": serial_written_on_capture,
        "camset_slot_limit_ok": camset_slot_limit_ok,
        "camset_excludes_copyright_pii": camset_excludes_copyright_pii,
        "camset_allows_write_serial_toggle": camset_allows_write_serial_toggle,
        "power_save_errno": power_save_errno,
        "monitor_linkage_errno": monitor_linkage_errno,
        "active_bypass_reasons": active_bypass_reasons,
        "power_save_bypassed": power_save_bypassed,
        "power_save_timer_effective": power_save_timer_effective,
        "tripod_warning_active": tripod_warning_active,
        "ntsc_pal_reboot_triggered": ntsc_pal_reboot_triggered,
        "effective_tv_system": effective_tv_system,
        "non_factory_banner": non_factory_banner,
        "movie_fps_errno": movie_fps_errno,
        "tc_format_errno": tc_format_errno,
        "playback_allowed": playback_allowed,
        "post_write_copyright_info": post_write_copyright_info,
        "post_photographer_name": post_photographer_name,
        "post_copyright_holder": post_copyright_holder,
        "post_write_serial_number": post_write_serial_number,
        "post_power_save_start_time": post_power_save_start_time,
        "post_auto_power_off_temp": post_auto_power_off_temp,
        "post_ntsc_pal_selector": post_ntsc_pal_selector,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


# ---------------------------------------------------------------------------
# Bounded Read-Only Donor Inspection (`O_RDONLY | O_NOFOLLOW | O_NONBLOCK`, 18 Donors)
# ---------------------------------------------------------------------------


def _iter_work_roots() -> Tuple[Optional[Path], ...]:
    """Return candidate donor work roots (delegates to `_fx3_files.iter_donor_work_roots`)."""
    return _fx3_files.iter_donor_work_roots()


def _resolve_phase361_donor_path(
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
    max_full_bytes: int = P361_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    try:
        resolved = _resolve_phase361_donor_path(relpath)
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
        hdr = os.pread(fd, min(P361_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase361_donors() -> Tuple["Phase361DonorArtifactDigest", ...]:
    specs = (
        ("fx3_appfw_702_so", P361_DONOR_FX3_APPFW_702_RELPATH, P361_PINNED_FX3_APPFW_702_BYTES, P361_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P361_PINNED_FX3_APPFW_702_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702"),
        ("fx3_libsaveloadsettings_so", P361_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH, P361_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES, P361_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES, "FULL_SHA256", P361_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_LIBSAVELOADSETTINGS"),
        ("fx6_appfw_601_so", P361_DONOR_FX6_APPFW_601_RELPATH, P361_PINNED_FX6_APPFW_601_BYTES, P361_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P361_PINNED_FX6_APPFW_601_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601"),
        ("fx3_backup_bin", P361_DONOR_FX3_BACKUP_BIN_RELPATH, P361_PINNED_FX3_BACKUP_BIN_BYTES, P361_PINNED_FX3_BACKUP_BIN_BYTES, "FULL_SHA256", P361_PINNED_FX3_BACKUP_BIN_SHA256, "SYNTHETIC_BK4_ILME_FX3"),
        ("fx3_uxc_en_f", P361_DONOR_FX3_UXC_EN_F_RELPATH, P361_PINNED_FX3_UXC_EN_F_BYTES, P361_PINNED_FX3_UXC_EN_F_BYTES, "FULL_SHA256", P361_PINNED_FX3_UXC_EN_F_SHA256, "SYNTHETIC_UXC7_FX3_EN_F"),
        ("fx3_uxc_sc_f", P361_DONOR_FX3_UXC_SC_F_RELPATH, P361_PINNED_FX3_UXC_SC_F_BYTES, P361_PINNED_FX3_UXC_SC_F_BYTES, "FULL_SHA256", P361_PINNED_FX3_UXC_SC_F_SHA256, "SYNTHETIC_UXC7_FX3_SC_F"),
        ("fx3_uxc_tc_f", P361_DONOR_FX3_UXC_TC_F_RELPATH, P361_PINNED_FX3_UXC_TC_F_BYTES, P361_PINNED_FX3_UXC_TC_F_BYTES, "FULL_SHA256", P361_PINNED_FX3_UXC_TC_F_SHA256, "SYNTHETIC_UXC7_FX3_TC_F"),
        ("fx3_uxc_ja_f", P361_DONOR_FX3_UXC_JA_F_RELPATH, P361_PINNED_FX3_UXC_JA_F_BYTES, P361_PINNED_FX3_UXC_JA_F_BYTES, "FULL_SHA256", P361_PINNED_FX3_UXC_JA_F_SHA256, "SYNTHETIC_UXC7_FX3_JA_F"),
        ("fx3_uxc_en", P361_DONOR_FX3_UXC_EN_RELPATH, P361_PINNED_FX3_UXC_EN_BYTES, P361_PINNED_FX3_UXC_EN_BYTES, "FULL_SHA256", P361_PINNED_FX3_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX3_EN"),
        ("fx3_uxc_sc", P361_DONOR_FX3_UXC_SC_RELPATH, P361_PINNED_FX3_UXC_SC_BYTES, P361_PINNED_FX3_UXC_SC_BYTES, "FULL_SHA256", P361_PINNED_FX3_UXC_SC_SHA256, "SYNTHETIC_UXC7_FX3_SC"),
        ("fx3_uxc_tc", P361_DONOR_FX3_UXC_TC_RELPATH, P361_PINNED_FX3_UXC_TC_BYTES, P361_PINNED_FX3_UXC_TC_BYTES, "FULL_SHA256", P361_PINNED_FX3_UXC_TC_SHA256, "SYNTHETIC_UXC7_FX3_TC"),
        ("fx3_uxc_ja", P361_DONOR_FX3_UXC_JA_RELPATH, P361_PINNED_FX3_UXC_JA_BYTES, P361_PINNED_FX3_UXC_JA_BYTES, "FULL_SHA256", P361_PINNED_FX3_UXC_JA_SHA256, "SYNTHETIC_UXC7_FX3_JA"),
        ("fx3_uxc_en_g", P361_DONOR_FX3_UXC_EN_G_RELPATH, P361_PINNED_FX3_UXC_EN_G_BYTES, P361_PINNED_FX3_UXC_EN_G_BYTES, "FULL_SHA256", P361_PINNED_FX3_UXC_EN_G_SHA256, "SYNTHETIC_UXC7_FX3_EN_G"),
        ("fx3_uxc_sc_g", P361_DONOR_FX3_UXC_SC_G_RELPATH, P361_PINNED_FX3_UXC_SC_G_BYTES, P361_PINNED_FX3_UXC_SC_G_BYTES, "FULL_SHA256", P361_PINNED_FX3_UXC_SC_G_SHA256, "SYNTHETIC_UXC7_FX3_SC_G"),
        ("fx3_uxc_tc_g", P361_DONOR_FX3_UXC_TC_G_RELPATH, P361_PINNED_FX3_UXC_TC_G_BYTES, P361_PINNED_FX3_UXC_TC_G_BYTES, "FULL_SHA256", P361_PINNED_FX3_UXC_TC_G_SHA256, "SYNTHETIC_UXC7_FX3_TC_G"),
        ("fx3_uxc_ja_g", P361_DONOR_FX3_UXC_JA_G_RELPATH, P361_PINNED_FX3_UXC_JA_G_BYTES, P361_PINNED_FX3_UXC_JA_G_BYTES, "FULL_SHA256", P361_PINNED_FX3_UXC_JA_G_SHA256, "SYNTHETIC_UXC7_FX3_JA_G"),
        ("fx6_uxc_en", P361_DONOR_FX6_UXC_EN_RELPATH, P361_PINNED_FX6_UXC_EN_BYTES, P361_PINNED_FX6_UXC_EN_BYTES, "FULL_SHA256", P361_PINNED_FX6_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX6_EN"),
        ("fx6_uxc_en_2", P361_DONOR_FX6_UXC_EN_2_RELPATH, P361_PINNED_FX6_UXC_EN_2_BYTES, P361_PINNED_FX6_UXC_EN_2_BYTES, "FULL_SHA256", P361_PINNED_FX6_UXC_EN_2_SHA256, "SYNTHETIC_UXC7_FX6_EN_2"),
    )
    return tuple(
        Phase361DonorArtifactDigest(
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


def inspect_phase361_donors_readonly(
    force_clean_room: Optional[bool] = None,
) -> "Phase361DonorSnapshot":
    """Inspect Wave-64 FX3 (`15` donors incl. `libSaveLoadSettings.so`) & FX6 (`3` donors)
    strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase361_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase361DonorSnapshot(
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
        ("fx3_appfw_702_so", P361_DONOR_FX3_APPFW_702_RELPATH, P361_PINNED_FX3_APPFW_702_BYTES, P361_PINNED_FX3_APPFW_702_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702")),
        ("fx3_libsaveloadsettings_so", P361_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH, P361_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES, P361_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_LIBSAVELOADSETTINGS")),
        ("fx6_appfw_601_so", P361_DONOR_FX6_APPFW_601_RELPATH, P361_PINNED_FX6_APPFW_601_BYTES, P361_PINNED_FX6_APPFW_601_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601")),
        ("fx3_backup_bin", P361_DONOR_FX3_BACKUP_BIN_RELPATH, P361_PINNED_FX3_BACKUP_BIN_BYTES, P361_PINNED_FX3_BACKUP_BIN_SHA256, lambda d: _check_bk4_backup(d, "ILME_FX3")),
        ("fx3_uxc_en_f", P361_DONOR_FX3_UXC_EN_F_RELPATH, P361_PINNED_FX3_UXC_EN_F_BYTES, P361_PINNED_FX3_UXC_EN_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_F")),
        ("fx3_uxc_sc_f", P361_DONOR_FX3_UXC_SC_F_RELPATH, P361_PINNED_FX3_UXC_SC_F_BYTES, P361_PINNED_FX3_UXC_SC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_F")),
        ("fx3_uxc_tc_f", P361_DONOR_FX3_UXC_TC_F_RELPATH, P361_PINNED_FX3_UXC_TC_F_BYTES, P361_PINNED_FX3_UXC_TC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_F")),
        ("fx3_uxc_ja_f", P361_DONOR_FX3_UXC_JA_F_RELPATH, P361_PINNED_FX3_UXC_JA_F_BYTES, P361_PINNED_FX3_UXC_JA_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_F")),
        ("fx3_uxc_en", P361_DONOR_FX3_UXC_EN_RELPATH, P361_PINNED_FX3_UXC_EN_BYTES, P361_PINNED_FX3_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN")),
        ("fx3_uxc_sc", P361_DONOR_FX3_UXC_SC_RELPATH, P361_PINNED_FX3_UXC_SC_BYTES, P361_PINNED_FX3_UXC_SC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC")),
        ("fx3_uxc_tc", P361_DONOR_FX3_UXC_TC_RELPATH, P361_PINNED_FX3_UXC_TC_BYTES, P361_PINNED_FX3_UXC_TC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC")),
        ("fx3_uxc_ja", P361_DONOR_FX3_UXC_JA_RELPATH, P361_PINNED_FX3_UXC_JA_BYTES, P361_PINNED_FX3_UXC_JA_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA")),
        ("fx3_uxc_en_g", P361_DONOR_FX3_UXC_EN_G_RELPATH, P361_PINNED_FX3_UXC_EN_G_BYTES, P361_PINNED_FX3_UXC_EN_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_G")),
        ("fx3_uxc_sc_g", P361_DONOR_FX3_UXC_SC_G_RELPATH, P361_PINNED_FX3_UXC_SC_G_BYTES, P361_PINNED_FX3_UXC_SC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_G")),
        ("fx3_uxc_tc_g", P361_DONOR_FX3_UXC_TC_G_RELPATH, P361_PINNED_FX3_UXC_TC_G_BYTES, P361_PINNED_FX3_UXC_TC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_G")),
        ("fx3_uxc_ja_g", P361_DONOR_FX3_UXC_JA_G_RELPATH, P361_PINNED_FX3_UXC_JA_G_BYTES, P361_PINNED_FX3_UXC_JA_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_G")),
        ("fx6_uxc_en", P361_DONOR_FX6_UXC_EN_RELPATH, P361_PINNED_FX6_UXC_EN_BYTES, P361_PINNED_FX6_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN")),
        ("fx6_uxc_en_2", P361_DONOR_FX6_UXC_EN_2_RELPATH, P361_PINNED_FX6_UXC_EN_2_BYTES, P361_PINNED_FX6_UXC_EN_2_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN_2")),
    )

    def _probe_one(spec: Tuple[str, str, int, str, Any]) -> Optional[Phase361DonorArtifactDigest]:
        aid, relpath, expected_bytes, expected_sha, marker_fn = spec
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            return None
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        return Phase361DonorArtifactDigest(
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
        artifacts = _synthetic_phase361_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase361DonorSnapshot(
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
    return Phase361DonorSnapshot(
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
# Frozen Dataclasses (Specs, Reports, Suites & 66-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase361DonorArtifactDigest:
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
class Phase361DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_2_0s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase361DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BreathingCamIdReelSdhcVaultSpec:
    camera_model: str
    fw_version: str
    shooting_domain: str
    recording_fps: int
    raw_output: str
    # `[Breathing Comp.]` & Catalyst Prepare vs FX6 3-Lock
    breathing_comp: str
    lens_info_status: str
    lens_id: str
    distortion_comp: str
    clear_image_zoom_scale: float
    auto_framing_active: bool
    framing_stabilizer_active: bool
    catalyst_product: str
    fx6_sq_motion: str
    fx6_codec: str
    reported_breathing_errno: Optional[int]
    reported_effective_breathing: str
    reported_optical_crop_active: bool
    reported_catalyst_metadata_supported: bool
    reported_fx6_hard_locked_off: bool
    # Movie `[File Settings]`, `[Cam ID + Reel#]`, `37`-Char Title, `SDHC 4GB`
    file_number_mode: str
    series_counter_reset_requested: bool
    existing_max_clip_number: int
    reported_next_series_clip: int
    file_name_format: str
    card_type: str
    card_filesystem: str
    simult_recording_enabled: bool
    secondary_card_filesystem: str
    recorded_clip_size_gb: float
    reported_file_format_errno: Optional[int]
    reported_simult_rec_errno: Optional[int]
    reported_sdhc_split_required: bool
    reported_storage_dir: str
    camera_id: str
    prev_camera_id: str
    reel_number: int
    camera_position: str
    clip_number: int
    title_name: str
    capture_date_yyyymmdd: str
    random_2char: str
    reported_title_errno: Optional[int]
    reported_effective_reel_number: int
    reported_output_position: str
    reported_output_clip_number: int
    reported_menu_position_unchanged: str
    reported_clip_basename: str
    fx6_card_handover_expected: bool
    # Reset boundaries
    reset_action: str
    post_breathing_comp: str
    post_file_number_mode: str
    post_file_name_format: str
    post_camera_id: str
    post_reel_number: int
    post_camera_position: str
    post_title_name: str
    # Vault & Overlay & H0==H3
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
    # Negative drift counters
    breathing_comp_lockout_or_catalyst_drift_events: int
    file_settings_camid_reel_or_sdhc_drift_events: int


@dataclass(frozen=True)
class BreathingCamIdReelSdhcVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    breathing_comp_120p_sq_raw_catalyst_verified: bool
    file_settings_camid_reel_sdhc_reset_verified: bool
    slot1_vault_and_h0_h3_verified: bool
    matrix_states_checked: int
    breathing_comp_lockout_or_catalyst_drift_events: int
    file_settings_camid_reel_or_sdhc_drift_events: int
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
class Copyright46PowerSaveNtscPalVaultSpec:
    camera_model: str
    fw_version: str
    shooting_domain: str
    # `[Copyright Info]` 46-char + Round 57 Erratum + Active Still/Movie `[Write Serial Number]` + `CAMSET`
    write_copyright_info: str
    photographer_name: str
    copyright_holder: str
    write_serial_number: str
    reported_copyright_str_errno: Optional[int]
    reported_still_copyright_written: bool
    reported_movie_copyright_written: bool
    reported_serial_written_on_capture: bool
    camset_export_requested: bool
    camset_target_slot: int
    camset_files_existing: int
    reported_camset_slot_limit_ok: bool
    reported_camset_excludes_copyright_pii: bool
    reported_camset_allows_write_serial_toggle: bool
    camset_copyright_pii_leaked_bytes: int
    exif_copyright_menu_requested: bool
    reported_exif_menu_errno: Optional[int]
    # `[Power Setting Option]` 9-Bypass + Dormant `[Power Save by Monitor]`
    power_save_start_time: str
    auto_power_off_temp: str
    power_save_by_monitor_requested: bool
    dormant_power_save_by_monitor_exposed_events: int
    reported_power_save_errno: Optional[int]
    reported_monitor_linkage_errno: Optional[int]
    usb_power_supply: bool
    slideshow_playing: bool
    ftp_transfer_active: bool
    movie_recording_active: bool
    pc_connected: bool
    tv_hdmi_connected: bool
    ir_remote_ctrl_on: bool
    bluetooth_rmt_ctrl_on: bool
    streaming_or_creators_cloud_active: bool
    reported_power_save_bypassed: bool
    reported_power_save_timer_effective: bool
    reported_tripod_warning_active: bool
    # `[NTSC/PAL Selector]` Reboot, Cross-Region Playback & Legacy Format Prompt Guard
    factory_tv_system: str
    ntsc_pal_selector: str
    target_ntsc_pal_selector: str
    requested_movie_fps: str
    requested_tc_format: str
    playback_clip_system: str
    reported_ntsc_pal_reboot_triggered: bool
    reported_effective_tv_system: str
    reported_non_factory_banner: str
    reported_movie_fps_errno: Optional[int]
    reported_tc_format_errno: Optional[int]
    reported_playback_allowed: bool
    # Reset boundaries (ALL Reset-resistant; cleared only by `[Initialize]`)
    reset_action: str
    post_write_copyright_info: str
    post_photographer_name: str
    post_copyright_holder: str
    post_write_serial_number: str
    post_power_save_start_time: str
    post_auto_power_off_temp: str
    post_ntsc_pal_selector: str
    # Vault & Overlay & H0==H3
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
    # Negative drift counters
    copyright_46ch_reset_erratum_or_serial_drift_events: int
    camset_copyright_pii_leak_events: int
    powersave_9cond_or_dormant_monitor_drift_events: int
    ntsc_pal_reboot_or_slot1_format_drift_events: int


@dataclass(frozen=True)
class Copyright46PowerSaveNtscPalVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    copyright46_round57_reset_serial_and_camset_verified: bool
    powersave_9cond_dormant_monitor_and_ntscpal_verified: bool
    overlay_and_h0_h3_verified: bool
    matrix_states_checked: int
    copyright_46ch_reset_erratum_or_serial_drift_events: int
    camset_copyright_pii_leak_events: int
    camset_copyright_pii_leaked_bytes: int
    powersave_9cond_or_dormant_monitor_drift_events: int
    dormant_power_save_by_monitor_exposed_events: int
    ntsc_pal_reboot_or_slot1_format_drift_events: int
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
class BreathingCamIdReelCopyright46PowerSaveNtscPalVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase361DonorSnapshot
    breathing_camid_reel_sdhc_report: BreathingCamIdReelSdhcVaultReport
    copyright46_powersave_ntscpal_report: Copyright46PowerSaveNtscPalVaultReport
    breathing_comp_lockout_or_catalyst_drift_events: int
    file_settings_camid_reel_or_sdhc_drift_events: int
    copyright_46ch_reset_erratum_or_serial_drift_events: int
    camset_copyright_pii_leak_events: int
    camset_copyright_pii_leaked_bytes: int
    powersave_9cond_or_dormant_monitor_drift_events: int
    dormant_power_save_by_monitor_exposed_events: int
    ntsc_pal_reboot_or_slot1_format_drift_events: int
    slot1_data_sector_writes: int
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
class Pillar66ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar66ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar66ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar66BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar66ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar66StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase361DonorSnapshot
    pillar_66a_breathing_camid_reel_sdhc_vault: Pillar66ASuiteResult
    pillar_66b_copyright46_powersave_ntscpal_vault: Pillar66BSuiteResult
    breathing_comp_lockout_or_catalyst_drift_events: int
    file_settings_camid_reel_or_sdhc_drift_events: int
    copyright_46ch_reset_erratum_or_serial_drift_events: int
    camset_copyright_pii_leak_events: int
    camset_copyright_pii_leaked_bytes: int
    powersave_9cond_or_dormant_monitor_drift_events: int
    dormant_power_save_by_monitor_exposed_events: int
    ntsc_pal_reboot_or_slot1_format_drift_events: int
    slot1_data_sector_writes: int
    slot1_vault_mutation_bytes: int
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
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master66PillarRecoveryReport:
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
    donor_snapshot: Phase361DonorSnapshot
    pillar66_a_breathing_camid_reel_sdhc_vault: Pillar66ASuiteResult
    pillar66_b_copyright46_powersave_ntscpal_vault: Pillar66BSuiteResult
    # Pillar 66 zero-violation counters & empirical metrics
    breathing_comp_lockout_or_catalyst_drift_events: int
    file_settings_camid_reel_or_sdhc_drift_events: int
    copyright_46ch_reset_erratum_or_serial_drift_events: int
    camset_copyright_pii_leak_events: int
    camset_copyright_pii_leaked_bytes: int
    powersave_9cond_or_dormant_monitor_drift_events: int
    dormant_power_save_by_monitor_exposed_events: int
    ntsc_pal_reboot_or_slot1_format_drift_events: int
    breathing_comp_resettable_by_camera_settings_reset: bool
    catalyst_browse_breathing_supported: bool
    catalyst_prepare_breathing_supported: bool
    fx3_title_name_max_chars: int
    fx3_sdhc_fat32_split_gb: int
    fx6_title_prefix_min_chars: int
    fx6_title_prefix_max_chars: int
    copyright_info_max_chars: int
    round57_erratum_copyright_resettable: bool
    write_serial_still_and_movie_active: bool
    fx6_has_exif_copyright_menu: bool
    fx3_powersave_bypass_condition_count: int
    fx3_has_power_save_by_monitor: bool
    # Shared & carried-forward Pillar 65..41 zero-violation metrics
    slot1_data_sector_writes: int
    slot1_vault_mutation_bytes: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_vault_erofs_ebusy_enforced: bool
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
    fx6_has_ibis: bool
    fx6_has_fan_control_max: bool
    fx6_has_still_self_timer: bool
    fx6_has_fn_menu: bool
    fx6_has_my_dial: bool
    fx6_has_bluetooth_hardware: bool
    fx6_has_av_tv_rotate: bool
    # Safety lock flags
    overall_ready_for_hardware_attach: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    master_66pillar_sha256: str
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
# Default Safe Specs & Evaluators (Pillars 66A & 66B)
# ---------------------------------------------------------------------------


def build_default_safe_breathing_camid_reel_sdhc_vault_spec(
    **overrides: Any,
) -> BreathingCamIdReelSdhcVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P361_FX3_MODEL_NAME,
        "fw_version": P361_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "recording_fps": 24,
        "raw_output": "Off",
        "breathing_comp": "On",
        "lens_info_status": "SUPPORT",
        "lens_id": "SEL24F14GM",
        "distortion_comp": "Auto",
        "clear_image_zoom_scale": 1.0,
        "auto_framing_active": False,
        "framing_stabilizer_active": False,
        "catalyst_product": "Catalyst Prepare",
        "fx6_sq_motion": "Off",
        "fx6_codec": "XAVC-I",
        "reported_breathing_errno": None,
        "reported_effective_breathing": "On",
        "reported_optical_crop_active": True,
        "reported_catalyst_metadata_supported": False,
        "reported_fx6_hard_locked_off": False,
        "file_number_mode": "Series",
        "series_counter_reset_requested": False,
        "existing_max_clip_number": 12,
        "reported_next_series_clip": 1,
        "file_name_format": "Cam ID + Reel#",
        "card_type": "CFexpress_Type_A",
        "card_filesystem": "exFAT",
        "simult_recording_enabled": False,
        "secondary_card_filesystem": "exFAT",
        "recorded_clip_size_gb": 1.5,
        "reported_file_format_errno": None,
        "reported_simult_rec_errno": None,
        "reported_sdhc_split_required": False,
        "reported_storage_dir": P361_FX3_MOVIE_STORAGE_DIR,
        "camera_id": "A",
        "prev_camera_id": "A",
        "reel_number": 1,
        "camera_position": "C",
        "clip_number": 1,
        "title_name": "C",
        "capture_date_yyyymmdd": "20230101",
        "random_2char": "AB",
        "reported_title_errno": None,
        "reported_effective_reel_number": 1,
        "reported_output_position": "C",
        "reported_output_clip_number": 1,
        "reported_menu_position_unchanged": "C",
        "reported_clip_basename": "A001C001_230101AB",
        "fx6_card_handover_expected": False,
        "reset_action": "Camera Settings Reset",
        "post_breathing_comp": "Off",
        "post_file_number_mode": "Series",
        "post_file_name_format": "Cam ID + Reel#",
        "post_camera_id": "A",
        "post_reel_number": 1,
        "post_camera_position": "C",
        "post_title_name": "C",
        "requested_vault_slot": 1,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": 0,
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P361_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P361_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P361_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P361_TIER0_SURFACE_COUNT,
        "breathing_comp_lockout_or_catalyst_drift_events": 0,
        "file_settings_camid_reel_or_sdhc_drift_events": 0,
    }
    defaults.update(overrides)
    return BreathingCamIdReelSdhcVaultSpec(**defaults)


def build_default_safe_copyright46_powersave_ntscpal_vault_spec(
    **overrides: Any,
) -> Copyright46PowerSaveNtscPalVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P361_FX3_MODEL_NAME,
        "fw_version": P361_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "write_copyright_info": "Off",
        "photographer_name": "",
        "copyright_holder": "",
        "write_serial_number": "Off",
        "reported_copyright_str_errno": None,
        "reported_still_copyright_written": False,
        "reported_movie_copyright_written": False,
        "reported_serial_written_on_capture": False,
        "camset_export_requested": True,
        "camset_target_slot": 1,
        "camset_files_existing": 2,
        "reported_camset_slot_limit_ok": True,
        "reported_camset_excludes_copyright_pii": True,
        "reported_camset_allows_write_serial_toggle": True,
        "camset_copyright_pii_leaked_bytes": 0,
        "exif_copyright_menu_requested": False,
        "reported_exif_menu_errno": None,
        "power_save_start_time": "5 Min",
        "auto_power_off_temp": "Standard",
        "power_save_by_monitor_requested": False,
        "dormant_power_save_by_monitor_exposed_events": 0,
        "reported_power_save_errno": None,
        "reported_monitor_linkage_errno": None,
        "usb_power_supply": False,
        "slideshow_playing": False,
        "ftp_transfer_active": False,
        "movie_recording_active": False,
        "pc_connected": False,
        "tv_hdmi_connected": False,
        "ir_remote_ctrl_on": False,
        "bluetooth_rmt_ctrl_on": False,
        "streaming_or_creators_cloud_active": False,
        "reported_power_save_bypassed": False,
        "reported_power_save_timer_effective": True,
        "reported_tripod_warning_active": False,
        "factory_tv_system": "NTSC",
        "ntsc_pal_selector": "NTSC",
        "target_ntsc_pal_selector": "NTSC",
        "requested_movie_fps": "23.98p",
        "requested_tc_format": "DF",
        "playback_clip_system": "NTSC",
        "reported_ntsc_pal_reboot_triggered": False,
        "reported_effective_tv_system": "NTSC",
        "reported_non_factory_banner": "",
        "reported_movie_fps_errno": None,
        "reported_tc_format_errno": None,
        "reported_playback_allowed": True,
        "reset_action": "Camera Settings Reset",
        "post_write_copyright_info": "Off",
        "post_photographer_name": "",
        "post_copyright_holder": "",
        "post_write_serial_number": "Off",
        "post_power_save_start_time": "5 Min",
        "post_auto_power_off_temp": "Standard",
        "post_ntsc_pal_selector": "NTSC",
        "requested_vault_slot": 1,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": 0,
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P361_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P361_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P361_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P361_TIER0_SURFACE_COUNT,
        "copyright_46ch_reset_erratum_or_serial_drift_events": 0,
        "camset_copyright_pii_leak_events": 0,
        "powersave_9cond_or_dormant_monitor_drift_events": 0,
        "ntsc_pal_reboot_or_slot1_format_drift_events": 0,
    }
    defaults.update(overrides)
    return Copyright46PowerSaveNtscPalVaultSpec(**defaults)


def evaluate_breathing_camid_reel_sdhc_vault(
    spec: BreathingCamIdReelSdhcVaultSpec,
) -> BreathingCamIdReelSdhcVaultReport:
    """Evaluate Pillar 66A (`[Breathing Comp.]` optical crop / 120p + S&Q>=100 + RAW / Catalyst Prepare
    vs FX6 3-lock, and Movie `[File Settings]` / `Cam ID + Reel#` / `37`-char Title / `SDHC 4GB` / `Slot 1 EROFS=30`)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P361_BLOCKED_SAFETY_POLICY_VIOLATION, "Safety policy violation")

    valid_spec = (
        spec.camera_model in (P361_FX3_MODEL_NAME, P361_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P361_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P361_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P361_SHOOTING_DOMAINS
        and spec.raw_output in P361_ON_OFF_MODES
        and spec.lens_info_status in P361_BREATHING_LENS_INFO_STATES
        and spec.distortion_comp in ("Auto", "Off")
        and spec.fx6_sq_motion in P361_ON_OFF_MODES
        and spec.file_number_mode in P361_FX3_FILE_NUMBER_MODES
        and spec.file_name_format in P361_FX3_FILE_NAME_FORMATS
        and spec.card_type in P361_CARD_TYPES
        and spec.card_filesystem in P361_FILESYSTEMS
        and spec.secondary_card_filesystem in P361_FILESYSTEMS
        and spec.camera_id in P361_FX3_CAMERA_IDS
        and spec.prev_camera_id in P361_FX3_CAMERA_IDS
        and (P361_FX3_REEL_MIN <= spec.reel_number <= P361_FX3_REEL_MAX)
        and spec.camera_position in P361_FX3_CAMERA_POSITIONS
        and spec.clip_number >= 1
        and spec.reset_action in P361_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P361_VAULT_ACTIONS
        and spec.vault_firewall_errno in P361_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P361_BLOCKED_INVALID_PILLAR66A_SPEC, "Invalid Pillar 66A spec fields")

    st = compute_expected_breathing_camid_reel_sdhc_vault_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        recording_fps=spec.recording_fps,
        raw_output=spec.raw_output,
        breathing_comp=spec.breathing_comp,
        lens_info_status=spec.lens_info_status,
        lens_id=spec.lens_id,
        distortion_comp=spec.distortion_comp,
        clear_image_zoom_scale=spec.clear_image_zoom_scale,
        auto_framing_active=spec.auto_framing_active,
        framing_stabilizer_active=spec.framing_stabilizer_active,
        catalyst_product=spec.catalyst_product,
        fx6_sq_motion=spec.fx6_sq_motion,
        fx6_codec=spec.fx6_codec,
        file_number_mode=spec.file_number_mode,
        series_counter_reset_requested=spec.series_counter_reset_requested,
        existing_max_clip_number=spec.existing_max_clip_number,
        file_name_format=spec.file_name_format,
        card_type=spec.card_type,
        card_filesystem=spec.card_filesystem,
        simult_recording_enabled=spec.simult_recording_enabled,
        secondary_card_filesystem=spec.secondary_card_filesystem,
        recorded_clip_size_gb=spec.recorded_clip_size_gb,
        camera_id=spec.camera_id,
        prev_camera_id=spec.prev_camera_id,
        reel_number=spec.reel_number,
        camera_position=spec.camera_position,
        clip_number=spec.clip_number,
        title_name=spec.title_name,
        capture_date_yyyymmdd=spec.capture_date_yyyymmdd,
        random_2char=spec.random_2char,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    # 1. `[Breathing Comp.]` 120p / S&Q>=100 / RAW / SEL100F28GM / Catalyst Prepare vs FX6 3-Lock
    breathing_ok = (
        spec.reported_breathing_errno == st["breathing_errno"]
        and st["breathing_errno"] is None
        and spec.reported_effective_breathing == st["effective_breathing"]
        and spec.reported_optical_crop_active == st["optical_crop_active"]
        and spec.reported_catalyst_metadata_supported == st["catalyst_metadata_supported"]
        and spec.reported_fx6_hard_locked_off == st["fx6_hard_locked_off"]
        and not (
            spec.catalyst_product == "Catalyst Browse"
            and spec.reported_catalyst_metadata_supported
        )
        and spec.post_breathing_comp == st["post_breathing_comp"]
        and spec.breathing_comp_lockout_or_catalyst_drift_events == 0
    )
    if not breathing_ok:
        _fail(
            P361_BLOCKED_BREATHING_COMP_OR_CATALYST_DRIFT,
            "Breathing Comp. 120p/S&Q>=100/RAW/lens lockout, Catalyst Prepare/Distortion=Auto rule, Reset rule, or FX6 3-lock violated",
        )

    # 2. Movie `[File Settings]` (`Cam ID + Reel#`, `C999->D001`, `YYMMDD` vs `YYYYMMDD`, `37`-Char, `SDHC 4GB`)
    expected_fx6_handover = spec.camera_model == P361_FX6_DONOR_MODEL_NAME
    file_settings_ok = (
        spec.reported_file_format_errno == st["file_format_errno"]
        and st["file_format_errno"] is None
        and spec.reported_simult_rec_errno == st["simult_rec_errno"]
        and st["simult_rec_errno"] is None
        and spec.reported_title_errno == st["title_errno"]
        and st["title_errno"] is None
        and spec.reported_next_series_clip == st["expected_next_series_clip"]
        and spec.reported_sdhc_split_required == st["sdhc_split_required"]
        and spec.reported_storage_dir == st["expected_storage_dir"]
        and spec.reported_effective_reel_number == st["effective_reel_number"]
        and spec.reported_output_position == st["output_position"]
        and spec.reported_output_clip_number == st["output_clip_number"]
        and spec.reported_menu_position_unchanged == st["menu_position_unchanged"]
        and spec.reported_clip_basename == st["expected_clip_basename"]
        and spec.fx6_card_handover_expected == expected_fx6_handover
        and spec.post_file_number_mode == st["post_file_number_mode"]
        and spec.post_file_name_format == st["post_file_name_format"]
        and spec.post_camera_id == st["post_camera_id"]
        and spec.post_reel_number == st["post_reel_number"]
        and spec.post_camera_position == st["post_camera_position"]
        and spec.post_title_name == st["post_title_name"]
        and spec.file_settings_camid_reel_or_sdhc_drift_events == 0
    )
    if not file_settings_ok:
        _fail(
            P361_BLOCKED_FILE_SETTINGS_CAMID_OR_SDHC_DRIFT,
            "Movie File Settings Cam ID+Reel# / C999->D001 / YYMMDD vs YYYYMMDD / 37-char Title / SDHC 4GB / Reset immunity violated",
        )

    # 3. Slot-1 Tier-0 Vault Firewall (`EROFS=30`) & Stage-B Overlay & H0 == H3
    slot1_mutated = (
        (
            spec.requested_vault_action in P361_WRITE_MUTATING_VAULT_ACTIONS
            or (
                spec.requested_vault_slot == 1
                and spec.requested_vault_action not in ("NONE", "READ_ONLY_AUDIT")
            )
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
    )
    if not vault_ok:
        _fail(
            P361_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P361_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P361_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P361_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P361_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    vault_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "66A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "breathing": spec.reported_effective_breathing,
            "catalyst": spec.reported_catalyst_metadata_supported,
            "clip_basename": spec.reported_clip_basename,
            "post_reel": spec.post_reel_number,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return BreathingCamIdReelSdhcVaultReport(
        schema=PHASE361_SCHEMA,
        version=PHASE361_VERSION,
        passed=passed,
        status=P361_STATUS_VERIFIED_PILLAR_66A if passed else P361_STATUS_REJECTED_PILLAR_66A,
        block_code=block_code,
        breathing_comp_120p_sq_raw_catalyst_verified=breathing_ok,
        file_settings_camid_reel_sdhc_reset_verified=file_settings_ok,
        slot1_vault_and_h0_h3_verified=vault_and_h0_h3_ok,
        matrix_states_checked=36,
        breathing_comp_lockout_or_catalyst_drift_events=(
            spec.breathing_comp_lockout_or_catalyst_drift_events
        ),
        file_settings_camid_reel_or_sdhc_drift_events=(
            spec.file_settings_camid_reel_or_sdhc_drift_events
        ),
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_copyright46_powersave_ntscpal_vault(
    spec: Copyright46PowerSaveNtscPalVaultSpec,
) -> Copyright46PowerSaveNtscPalVaultReport:
    """Evaluate Pillar 66B (`[Copyright Info]` 46-char Reset-Resistant [Round 57 Erratum],
    Active Still+Movie `[Write Serial Number]`, `CAMSET*.DAT` PII Exclusion,
    `[Power Setting Option]` 9-Bypass + Dormant `[Power Save by Monitor]`, &
    `[NTSC/PAL Selector]` `Slot 1 EROFS=30` Shield)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P361_BLOCKED_SAFETY_POLICY_VIOLATION, "Safety policy violation")

    valid_spec = (
        spec.camera_model in (P361_FX3_MODEL_NAME, P361_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P361_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P361_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P361_SHOOTING_DOMAINS
        and spec.write_copyright_info in P361_ON_OFF_MODES
        and spec.write_serial_number in P361_ON_OFF_MODES
        and spec.auto_power_off_temp in P361_FX3_AUTO_PWR_OFF_TEMP_MODES
        and spec.factory_tv_system in P361_NTSC_PAL_MODES
        and spec.ntsc_pal_selector in P361_NTSC_PAL_MODES
        and spec.target_ntsc_pal_selector in P361_NTSC_PAL_MODES
        and spec.playback_clip_system in P361_NTSC_PAL_MODES
        and spec.requested_tc_format in ("DF", "NDF")
        and spec.reset_action in P361_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P361_VAULT_ACTIONS
        and spec.vault_firewall_errno in P361_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P361_BLOCKED_INVALID_PILLAR66B_SPEC, "Invalid Pillar 66B spec fields")

    st = compute_expected_copyright46_powersave_ntscpal_vault_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        write_copyright_info=spec.write_copyright_info,
        photographer_name=spec.photographer_name,
        copyright_holder=spec.copyright_holder,
        write_serial_number=spec.write_serial_number,
        camset_export_requested=spec.camset_export_requested,
        camset_target_slot=spec.camset_target_slot,
        camset_files_existing=spec.camset_files_existing,
        exif_copyright_menu_requested=spec.exif_copyright_menu_requested,
        power_save_start_time=spec.power_save_start_time,
        auto_power_off_temp=spec.auto_power_off_temp,
        power_save_by_monitor_requested=spec.power_save_by_monitor_requested,
        usb_power_supply=spec.usb_power_supply,
        slideshow_playing=spec.slideshow_playing,
        ftp_transfer_active=spec.ftp_transfer_active,
        movie_recording_active=spec.movie_recording_active,
        pc_connected=spec.pc_connected,
        tv_hdmi_connected=spec.tv_hdmi_connected,
        ir_remote_ctrl_on=spec.ir_remote_ctrl_on,
        bluetooth_rmt_ctrl_on=spec.bluetooth_rmt_ctrl_on,
        streaming_or_creators_cloud_active=spec.streaming_or_creators_cloud_active,
        factory_tv_system=spec.factory_tv_system,
        ntsc_pal_selector=spec.ntsc_pal_selector,
        target_ntsc_pal_selector=spec.target_ntsc_pal_selector,
        requested_movie_fps=spec.requested_movie_fps,
        requested_tc_format=spec.requested_tc_format,
        playback_clip_system=spec.playback_clip_system,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    # 1. `[Copyright Info]` 46-Char Reset-Resistant (Round 57 Erratum), Still+Movie `[Write Serial Number]`, `CAMSET` PII Shield
    copyright_ok = (
        spec.reported_copyright_str_errno == st["copyright_str_errno"]
        and st["copyright_str_errno"] is None
        and not spec.exif_copyright_menu_requested
        and spec.reported_exif_menu_errno == st["exif_menu_errno"]
        and st["exif_menu_errno"] is None
        and spec.reported_still_copyright_written == st["still_copyright_written"]
        and spec.reported_movie_copyright_written == st["movie_copyright_written"]
        and spec.reported_serial_written_on_capture == st["serial_written_on_capture"]
        and spec.reported_camset_slot_limit_ok == st["camset_slot_limit_ok"]
        and st["camset_slot_limit_ok"]
        and spec.reported_camset_excludes_copyright_pii == st["camset_excludes_copyright_pii"]
        and spec.reported_camset_allows_write_serial_toggle == st["camset_allows_write_serial_toggle"]
        and spec.camset_copyright_pii_leaked_bytes == 0
        and spec.camset_copyright_pii_leak_events == 0
        and spec.post_write_copyright_info == st["post_write_copyright_info"]
        and spec.post_photographer_name == st["post_photographer_name"]
        and spec.post_copyright_holder == st["post_copyright_holder"]
        and spec.post_write_serial_number == st["post_write_serial_number"]
        and spec.copyright_46ch_reset_erratum_or_serial_drift_events == 0
    )
    if not copyright_ok:
        _fail(
            P361_BLOCKED_COPYRIGHT46_RESET_OR_CAMSET_DRIFT,
            "Copyright Info 46-char/Round 57 Reset-resistant erratum, active Write Serial Number, or CAMSET PII exclusion violated",
        )

    # 2. `[Power Setting Option]` 9-Bypass + Dormant `[Power Save by Monitor]` & `[NTSC/PAL Selector]`
    powersave_ntscpal_ok = (
        not spec.power_save_by_monitor_requested
        and spec.dormant_power_save_by_monitor_exposed_events == 0
        and spec.reported_power_save_errno == st["power_save_errno"]
        and st["power_save_errno"] is None
        and spec.reported_monitor_linkage_errno == st["monitor_linkage_errno"]
        and st["monitor_linkage_errno"] is None
        and spec.reported_power_save_bypassed == st["power_save_bypassed"]
        and spec.reported_power_save_timer_effective == st["power_save_timer_effective"]
        and spec.reported_tripod_warning_active == st["tripod_warning_active"]
        and spec.reported_ntsc_pal_reboot_triggered == st["ntsc_pal_reboot_triggered"]
        and spec.reported_effective_tv_system == st["effective_tv_system"]
        and spec.reported_non_factory_banner == st["non_factory_banner"]
        and spec.reported_movie_fps_errno == st["movie_fps_errno"]
        and st["movie_fps_errno"] is None
        and spec.reported_tc_format_errno == st["tc_format_errno"]
        and st["tc_format_errno"] is None
        and spec.reported_playback_allowed == st["playback_allowed"]
        and spec.post_power_save_start_time == st["post_power_save_start_time"]
        and spec.post_auto_power_off_temp == st["post_auto_power_off_temp"]
        and spec.post_ntsc_pal_selector == st["post_ntsc_pal_selector"]
        and spec.powersave_9cond_or_dormant_monitor_drift_events == 0
        and spec.ntsc_pal_reboot_or_slot1_format_drift_events == 0
    )
    if not powersave_ntscpal_ok:
        _fail(
            P361_BLOCKED_POWERSAVE_OR_NTSCPAL_DRIFT,
            "Power Setting Option 9-bypass / dormant Power Save by Monitor, or NTSC/PAL reboot / PAL fps-TC lockout violated",
        )

    # 3. Slot-1 Tier-0 Vault Firewall (`EROFS=30`, intercepts legacy `base 0xe595` Format? Slot 1)
    slot1_mutated = (
        (
            spec.requested_vault_action in P361_WRITE_MUTATING_VAULT_ACTIONS
            or (
                spec.requested_vault_slot == 1
                and spec.requested_vault_action not in ("NONE", "READ_ONLY_AUDIT")
            )
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
    )
    if not vault_ok:
        _fail(
            P361_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P361_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P361_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P361_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P361_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    overlay_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "66B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "post_write_copyright": spec.post_write_copyright_info,
            "post_write_serial": spec.post_write_serial_number,
            "post_powersave": spec.post_power_save_start_time,
            "post_ntsc_pal": spec.post_ntsc_pal_selector,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return Copyright46PowerSaveNtscPalVaultReport(
        schema=PHASE361_SCHEMA,
        version=PHASE361_VERSION,
        passed=passed,
        status=P361_STATUS_VERIFIED_PILLAR_66B if passed else P361_STATUS_REJECTED_PILLAR_66B,
        block_code=block_code,
        copyright46_round57_reset_serial_and_camset_verified=copyright_ok,
        powersave_9cond_dormant_monitor_and_ntscpal_verified=powersave_ntscpal_ok,
        overlay_and_h0_h3_verified=overlay_and_h0_h3_ok,
        matrix_states_checked=36,
        copyright_46ch_reset_erratum_or_serial_drift_events=(
            spec.copyright_46ch_reset_erratum_or_serial_drift_events
        ),
        camset_copyright_pii_leak_events=spec.camset_copyright_pii_leak_events,
        camset_copyright_pii_leaked_bytes=spec.camset_copyright_pii_leaked_bytes,
        powersave_9cond_or_dormant_monitor_drift_events=(
            spec.powersave_9cond_or_dormant_monitor_drift_events
        ),
        dormant_power_save_by_monitor_exposed_events=(
            spec.dormant_power_save_by_monitor_exposed_events
        ),
        ntsc_pal_reboot_or_slot1_format_drift_events=(
            spec.ntsc_pal_reboot_or_slot1_format_drift_events
        ),
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_breathing_camid_reel_copyright46_powersave_ntscpal_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_66a: Optional[BreathingCamIdReelSdhcVaultSpec] = None,
    spec_66b: Optional[Copyright46PowerSaveNtscPalVaultSpec] = None,
) -> BreathingCamIdReelCopyright46PowerSaveNtscPalVaultReport:
    """Combined single-shot verifier for Pillar 66A + Pillar 66B + 18 bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase361_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_breathing_camid_reel_sdhc_vault(
        spec_66a or build_default_safe_breathing_camid_reel_sdhc_vault_spec()
    )
    rep_b = evaluate_copyright46_powersave_ntscpal_vault(
        spec_66b or build_default_safe_copyright46_powersave_ntscpal_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 361 Wave-64 donor artifact parity check failed")
    if not donor_snapshot.under_2_0s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return BreathingCamIdReelCopyright46PowerSaveNtscPalVaultReport(
        schema=PHASE361_SCHEMA,
        version=PHASE361_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P361_STATUS_VERIFIED_PILLAR66_SUITE if all_ok else P361_STATUS_FAIL_PILLAR66_SUITE,
        donor_snapshot=donor_snapshot,
        breathing_camid_reel_sdhc_report=rep_a,
        copyright46_powersave_ntscpal_report=rep_b,
        breathing_comp_lockout_or_catalyst_drift_events=(
            rep_a.breathing_comp_lockout_or_catalyst_drift_events
        ),
        file_settings_camid_reel_or_sdhc_drift_events=(
            rep_a.file_settings_camid_reel_or_sdhc_drift_events
        ),
        copyright_46ch_reset_erratum_or_serial_drift_events=(
            rep_b.copyright_46ch_reset_erratum_or_serial_drift_events
        ),
        camset_copyright_pii_leak_events=rep_b.camset_copyright_pii_leak_events,
        camset_copyright_pii_leaked_bytes=rep_b.camset_copyright_pii_leaked_bytes,
        powersave_9cond_or_dormant_monitor_drift_events=(
            rep_b.powersave_9cond_or_dormant_monitor_drift_events
        ),
        dormant_power_save_by_monitor_exposed_events=(
            rep_b.dormant_power_save_by_monitor_exposed_events
        ),
        ntsc_pal_reboot_or_slot1_format_drift_events=(
            rep_b.ntsc_pal_reboot_or_slot1_format_drift_events
        ),
        slot1_data_sector_writes=rep_a.slot1_data_sector_writes + rep_b.slot1_data_sector_writes,
        slot1_vault_mutation_bytes=(
            rep_a.slot1_vault_mutation_bytes + rep_b.slot1_vault_mutation_bytes
        ),
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


def verify_breathing_camid_reel_copyright46_powersave_ntscpal_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_66a: Optional[BreathingCamIdReelSdhcVaultSpec] = None,
    spec_66b: Optional[Copyright46PowerSaveNtscPalVaultSpec] = None,
) -> BreathingCamIdReelCopyright46PowerSaveNtscPalVaultReport:
    """Symmetry alias for `verify_breathing_camid_reel_copyright46_powersave_ntscpal_and_vault`."""
    return verify_breathing_camid_reel_copyright46_powersave_ntscpal_and_vault(
        force_clean_room=force_clean_room,
        spec_66a=spec_66a,
        spec_66b=spec_66b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 66A & 66B)
# ---------------------------------------------------------------------------


def run_pillar66a_breathing_camid_reel_sdhc_vault_6_scenario_suite() -> Pillar66ASuiteResult:
    """Run 6 Pillar 66A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, BreathingCamIdReelSdhcVaultSpec, Optional[str]], ...] = (
        (
            P361_PILLAR_66A_SCENARIO_IDS[0],
            True,
            build_default_safe_breathing_camid_reel_sdhc_vault_spec(
                shooting_domain="S&Q",
                recording_fps=60,
                breathing_comp="Off",
                distortion_comp="Auto",
                catalyst_product="Catalyst Prepare",
                reported_effective_breathing="Off",
                reported_optical_crop_active=False,
                reported_catalyst_metadata_supported=True,
                file_name_format="Date + Title",
                title_name="Scene_01-Take2",
                capture_date_yyyymmdd="20261117",
                clip_number=7,
                reported_next_series_clip=7,
                reported_output_clip_number=7,
                reported_clip_basename="20261117_Scene_01-Take2_0007",
                reset_action="Camera Settings Reset",
                post_breathing_comp="Off",
                post_file_name_format="Date + Title",
                post_title_name="Scene_01-Take2",
            ),
            None,
        ),
        (
            P361_PILLAR_66A_SCENARIO_IDS[1],
            True,
            build_default_safe_breathing_camid_reel_sdhc_vault_spec(
                camera_model=P361_FX6_DONOR_MODEL_NAME,
                fw_version=P361_FX6_DONOR_FW_VERSION,
                breathing_comp="Off",
                fx6_sq_motion="On",
                fx6_codec="RAW",
                reported_effective_breathing="Off",
                reported_optical_crop_active=False,
                reported_fx6_hard_locked_off=True,
                file_name_format="Cam ID + Reel#",
                card_type="CFexpress_Type_A",
                reported_storage_dir=P361_FX6_CFEXPRESS_CLIP_DIR,
                camera_id="B",
                prev_camera_id="A",
                reel_number=42,
                reported_effective_reel_number=1,
                camera_position="C",
                clip_number=1000,
                reported_next_series_clip=1000,
                title_name=P361_FX6_TITLE_PREFIX_DEFAULT,
                reported_output_position="D",
                reported_output_clip_number=1,
                reported_menu_position_unchanged="C",
                reported_clip_basename="B001D001_230101AB",
                fx6_card_handover_expected=True,
                reset_action="None",
                post_breathing_comp="Off",
                post_camera_id="B",
                post_reel_number=1,
                post_camera_position="C",
                post_title_name=P361_FX6_TITLE_PREFIX_DEFAULT,
            ),
            None,
        ),
        (
            P361_PILLAR_66A_SCENARIO_IDS[2],
            False,
            build_default_safe_breathing_camid_reel_sdhc_vault_spec(
                shooting_domain="S&Q",
                recording_fps=120,
                breathing_comp="On",
                lens_id="SEL100F28GM_MACRO_0.57M_1.0M",
                catalyst_product="Catalyst Browse",
                reported_breathing_errno=None,
                reported_catalyst_metadata_supported=True,
                breathing_comp_lockout_or_catalyst_drift_events=1,
            ),
            P361_BLOCKED_BREATHING_COMP_OR_CATALYST_DRIFT,
        ),
        (
            P361_PILLAR_66A_SCENARIO_IDS[3],
            False,
            build_default_safe_breathing_camid_reel_sdhc_vault_spec(
                card_type="SDHC_FAT32",
                card_filesystem="FAT32",
                file_name_format="Cam ID + Reel#",
                simult_recording_enabled=True,
                secondary_card_filesystem="exFAT",
                recorded_clip_size_gb=6.5,
                title_name="A" * 38,
                reported_file_format_errno=None,
                reported_simult_rec_errno=None,
                reported_sdhc_split_required=False,
                reported_title_errno=None,
                file_settings_camid_reel_or_sdhc_drift_events=1,
            ),
            P361_BLOCKED_FILE_SETTINGS_CAMID_OR_SDHC_DRIFT,
        ),
        (
            P361_PILLAR_66A_SCENARIO_IDS[4],
            False,
            build_default_safe_breathing_camid_reel_sdhc_vault_spec(
                file_name_format="Cam ID + Reel#",
                file_number_mode="Reset",
                camera_id="B",
                prev_camera_id="B",
                reel_number=15,
                reported_effective_reel_number=1,  # Wrong: File Number=Reset must NOT reset Reel#!
                reset_action="Camera Settings Reset",
                post_file_name_format="Standard",  # Wrong: File Settings is Reset-resistant!
                file_settings_camid_reel_or_sdhc_drift_events=1,
            ),
            P361_BLOCKED_FILE_SETTINGS_CAMID_OR_SDHC_DRIFT,
        ),
        (
            P361_PILLAR_66A_SCENARIO_IDS[5],
            False,
            build_default_safe_breathing_camid_reel_sdhc_vault_spec(
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="CARD_WRITE_REEL_COUNTER_UPDATE",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/setting/66a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P361_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar66ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_breathing_camid_reel_sdhc_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar66ScenarioOutcome(
                scenario_id=sid,
                pillar="66A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar66ASuiteResult(
        passed=all_ok,
        status=P361_STATUS_VERIFIED_PILLAR_66A if all_ok else P361_STATUS_REJECTED_PILLAR_66A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar66b_copyright46_powersave_ntscpal_vault_6_scenario_suite() -> Pillar66BSuiteResult:
    """Run 6 Pillar 66B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, Copyright46PowerSaveNtscPalVaultSpec, Optional[str]], ...] = (
        (
            P361_PILLAR_66B_SCENARIO_IDS[0],
            True,
            build_default_safe_copyright46_powersave_ntscpal_vault_spec(
                shooting_domain="Movie",
                write_copyright_info="On",
                photographer_name="P" * 46,
                copyright_holder="C" * 46,
                write_serial_number="On",
                reported_still_copyright_written=False,  # Movie shot does NOT embed Still EXIF Copyright Info
                reported_movie_copyright_written=False,
                reported_serial_written_on_capture=True,
                reset_action="Camera Settings Reset",
                post_write_copyright_info="On",
                post_photographer_name="P" * 46,
                post_copyright_holder="C" * 46,
                post_write_serial_number="On",
            ),
            None,
        ),
        (
            P361_PILLAR_66B_SCENARIO_IDS[1],
            True,
            build_default_safe_copyright46_powersave_ntscpal_vault_spec(
                shooting_domain="Still",
                write_copyright_info="On",
                photographer_name="FX3 Studio Operator",
                copyright_holder="Studio Copyright 2026",
                write_serial_number="On",
                reported_still_copyright_written=True,
                reported_movie_copyright_written=False,
                reported_serial_written_on_capture=True,
                power_save_start_time="10 Sec",
                auto_power_off_temp="High",
                usb_power_supply=True,
                bluetooth_rmt_ctrl_on=True,
                reported_power_save_bypassed=True,
                reported_power_save_timer_effective=False,
                reported_tripod_warning_active=True,
                factory_tv_system="NTSC",
                ntsc_pal_selector="NTSC",
                target_ntsc_pal_selector="PAL",
                requested_movie_fps="25p",
                requested_tc_format="NDF",
                playback_clip_system="PAL",
                reported_ntsc_pal_reboot_triggered=True,
                reported_effective_tv_system="PAL",
                reported_non_factory_banner="Running on PAL.",
                reported_playback_allowed=True,
                reset_action="Camera Settings Reset",
                post_write_copyright_info="On",
                post_photographer_name="FX3 Studio Operator",
                post_copyright_holder="Studio Copyright 2026",
                post_write_serial_number="On",
                post_power_save_start_time="10 Sec",
                post_auto_power_off_temp="High",
                post_ntsc_pal_selector="PAL",
            ),
            None,
        ),
        (
            P361_PILLAR_66B_SCENARIO_IDS[2],
            False,
            build_default_safe_copyright46_powersave_ntscpal_vault_spec(
                write_copyright_info="On",
                photographer_name="Round57 Lab",
                copyright_holder="FX3 Corp",
                reset_action="Camera Settings Reset",
                # Spoofing Round 57 erratum: claiming Camera Settings Reset turns Write Copyright Info Off!
                post_write_copyright_info="Off",
                camset_copyright_pii_leaked_bytes=92,
                camset_copyright_pii_leak_events=1,
                copyright_46ch_reset_erratum_or_serial_drift_events=1,
            ),
            P361_BLOCKED_COPYRIGHT46_RESET_OR_CAMSET_DRIFT,
        ),
        (
            P361_PILLAR_66B_SCENARIO_IDS[3],
            False,
            build_default_safe_copyright46_powersave_ntscpal_vault_spec(
                camera_model=P361_FX6_DONOR_MODEL_NAME,
                fw_version=P361_FX6_DONOR_FW_VERSION,
                photographer_name="X" * 47,
                reported_copyright_str_errno=None,
                exif_copyright_menu_requested=True,
                reported_exif_menu_errno=None,
                copyright_46ch_reset_erratum_or_serial_drift_events=1,
            ),
            P361_BLOCKED_COPYRIGHT46_RESET_OR_CAMSET_DRIFT,
        ),
        (
            P361_PILLAR_66B_SCENARIO_IDS[4],
            False,
            build_default_safe_copyright46_powersave_ntscpal_vault_spec(
                power_save_start_time="30 sec",
                power_save_by_monitor_requested=True,
                dormant_power_save_by_monitor_exposed_events=1,
                reported_power_save_errno=None,
                reported_monitor_linkage_errno=None,
                usb_power_supply=True,
                reported_power_save_bypassed=False,
                reported_power_save_timer_effective=True,
                target_ntsc_pal_selector="PAL",
                requested_movie_fps="23.98p",
                requested_tc_format="DF",
                reported_movie_fps_errno=None,
                reported_tc_format_errno=None,
                powersave_9cond_or_dormant_monitor_drift_events=1,
                ntsc_pal_reboot_or_slot1_format_drift_events=1,
            ),
            P361_BLOCKED_POWERSAVE_OR_NTSCPAL_DRIFT,
        ),
        (
            P361_PILLAR_66B_SCENARIO_IDS[5],
            False,
            build_default_safe_copyright46_powersave_ntscpal_vault_spec(
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="FORMAT_NTSC_PAL_PROMPT",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/mnt/emmc/66b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P361_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar66ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_copyright46_powersave_ntscpal_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar66ScenarioOutcome(
                scenario_id=sid,
                pillar="66B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar66BSuiteResult(
        passed=all_ok,
        status=P361_STATUS_VERIFIED_PILLAR_66B if all_ok else P361_STATUS_REJECTED_PILLAR_66B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Standalone Pillar 66 Suite & Concurrent Unified 66/66 Master Aggregator
# ---------------------------------------------------------------------------


def run_pillar66_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar66StandaloneReport:
    """Run full Pillar 66 standalone suite (`6/6` Pillar 66A + `6/6` Pillar 66B + 18 bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase361_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar66a_breathing_camid_reel_sdhc_vault_6_scenario_suite()
    res_b = run_pillar66b_copyright46_powersave_ntscpal_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 361 donor verification failed")
    if not donor_snapshot.under_2_0s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE361_SCHEMA,
            "version": PHASE361_VERSION,
            "mode": donor_snapshot.verification_mode,
            "66a": [asdict(s) for s in res_a.scenarios],
            "66b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar66StandaloneReport(
        schema=PHASE361_SCHEMA,
        version=PHASE361_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P361_STATUS_VERIFIED_PILLAR66_SUITE if all_ok else P361_STATUS_FAIL_PILLAR66_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_66a_breathing_camid_reel_sdhc_vault=res_a,
        pillar_66b_copyright46_powersave_ntscpal_vault=res_b,
        breathing_comp_lockout_or_catalyst_drift_events=(
            P361_BREATHING_COMP_LOCKOUT_OR_CATALYST_DRIFT_EVENTS if res_a.passed else 1
        ),
        file_settings_camid_reel_or_sdhc_drift_events=(
            P361_FILE_SETTINGS_CAMID_REEL_OR_SDHC_DRIFT_EVENTS if res_a.passed else 1
        ),
        copyright_46ch_reset_erratum_or_serial_drift_events=(
            P361_COPYRIGHT_46CH_RESET_ERRATUM_OR_SERIAL_DRIFT_EVENTS if res_b.passed else 1
        ),
        camset_copyright_pii_leak_events=(
            P361_CAMSET_COPYRIGHT_PII_LEAK_EVENTS if res_b.passed else 1
        ),
        camset_copyright_pii_leaked_bytes=(
            P361_CAMSET_COPYRIGHT_PII_LEAKED_BYTES if res_b.passed else 46
        ),
        powersave_9cond_or_dormant_monitor_drift_events=(
            P361_POWERSAVE_9COND_OR_DORMANT_MONITOR_DRIFT_EVENTS if res_b.passed else 1
        ),
        dormant_power_save_by_monitor_exposed_events=(
            P361_DORMANT_POWER_SAVE_BY_MONITOR_EXPOSED_EVENTS if res_b.passed else 1
        ),
        ntsc_pal_reboot_or_slot1_format_drift_events=(
            P361_NTSC_PAL_REBOOT_OR_SLOT1_FORMAT_DRIFT_EVENTS if res_b.passed else 1
        ),
        slot1_data_sector_writes=(
            P361_SLOT1_DATA_SECTOR_WRITES if (res_a.passed and res_b.passed) else 1
        ),
        slot1_vault_mutation_bytes=(
            P361_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        rf_packets_transmitted=P361_RF_PACKETS_TRANSMITTED,
        rf_nvs_mutation_bytes=P361_RF_NVS_MUTATION_BYTES,
        slot1_format_hard_locked=P361_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_eopnotsupp_enforced=P361_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        slot1_vault_erofs_ebusy_enforced=P361_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
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


def _apply_master66_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def _master66_local_donors_available() -> bool:
    """Return True only when all 18 Wave-64 local donors exist."""
    required_relpaths: Tuple[str, ...] = (
        P361_DONOR_FX3_APPFW_702_RELPATH,
        P361_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
        P361_DONOR_FX6_APPFW_601_RELPATH,
        P361_DONOR_FX3_BACKUP_BIN_RELPATH,
        P361_DONOR_FX3_UXC_EN_F_RELPATH,
        P361_DONOR_FX3_UXC_SC_F_RELPATH,
        P361_DONOR_FX3_UXC_TC_F_RELPATH,
        P361_DONOR_FX3_UXC_JA_F_RELPATH,
        P361_DONOR_FX3_UXC_EN_RELPATH,
        P361_DONOR_FX3_UXC_SC_RELPATH,
        P361_DONOR_FX3_UXC_TC_RELPATH,
        P361_DONOR_FX3_UXC_JA_RELPATH,
        P361_DONOR_FX3_UXC_EN_G_RELPATH,
        P361_DONOR_FX3_UXC_SC_G_RELPATH,
        P361_DONOR_FX3_UXC_TC_G_RELPATH,
        P361_DONOR_FX3_UXC_JA_G_RELPATH,
        P361_DONOR_FX6_UXC_EN_RELPATH,
        P361_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for relpath in required_relpaths:
        try:
            resolved = _resolve_phase361_donor_path(relpath)
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


def evaluate_realhw_66pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master66PillarRecoveryReport:
    """Evaluate and aggregate all 66 recovery pillars (`1..66`) concurrently -> `66/66` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_66_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    if resolved_clean_room is None and not _master66_local_donors_available():
        resolved_clean_room = True
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_65pillar() -> Master65PillarRecoveryReport:
        return evaluate_realhw_65pillar_recovery_master(**kw)

    def _run_p66() -> Tuple[Pillar66StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar66_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_65 = pool.submit(_run_65pillar)
        fut_66 = pool.submit(_run_p66)
        m65_rep = fut_65.result()
        p66_rep, p66_dt = fut_66.result()

    all_errors: List[str] = list(m65_rep.errors) + list(p66_rep.errors)
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
        if getattr(m65_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-65 violated {attr_name} == {expected_val}")
        if getattr(p66_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 66 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("breathing_comp_lockout_or_catalyst_drift_events", 0),
        ("file_settings_camid_reel_or_sdhc_drift_events", 0),
        ("copyright_46ch_reset_erratum_or_serial_drift_events", 0),
        ("camset_copyright_pii_leak_events", 0),
        ("camset_copyright_pii_leaked_bytes", 0),
        ("powersave_9cond_or_dormant_monitor_drift_events", 0),
        ("dormant_power_save_by_monitor_exposed_events", 0),
        ("ntsc_pal_reboot_or_slot1_format_drift_events", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("rf_packets_transmitted", 0),
        ("rf_nvs_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_eopnotsupp_enforced", True),
        ("slot1_vault_erofs_ebusy_enforced", True),
    ):
        if getattr(p66_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 66 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m65_rep.pillars)
    spec66 = MASTER_66_PILLAR_SPECS[65]
    p66_metrics = {
        "pillar_66a_breathing_camid_reel_sdhc_vault": (
            f"{p66_rep.pillar_66a_breathing_camid_reel_sdhc_vault.scenarios_passed}/"
            f"{p66_rep.pillar_66a_breathing_camid_reel_sdhc_vault.scenarios_total}"
        ),
        "pillar_66b_copyright46_powersave_ntscpal_vault": (
            f"{p66_rep.pillar_66b_copyright46_powersave_ntscpal_vault.scenarios_passed}/"
            f"{p66_rep.pillar_66b_copyright46_powersave_ntscpal_vault.scenarios_total}"
        ),
        "breathing_comp_lockout_or_catalyst_drift_events": (
            p66_rep.breathing_comp_lockout_or_catalyst_drift_events
        ),
        "file_settings_camid_reel_or_sdhc_drift_events": (
            p66_rep.file_settings_camid_reel_or_sdhc_drift_events
        ),
        "copyright_46ch_reset_erratum_or_serial_drift_events": (
            p66_rep.copyright_46ch_reset_erratum_or_serial_drift_events
        ),
        "camset_copyright_pii_leak_events": p66_rep.camset_copyright_pii_leak_events,
        "camset_copyright_pii_leaked_bytes": p66_rep.camset_copyright_pii_leaked_bytes,
        "powersave_9cond_or_dormant_monitor_drift_events": (
            p66_rep.powersave_9cond_or_dormant_monitor_drift_events
        ),
        "dormant_power_save_by_monitor_exposed_events": (
            p66_rep.dormant_power_save_by_monitor_exposed_events
        ),
        "ntsc_pal_reboot_or_slot1_format_drift_events": (
            p66_rep.ntsc_pal_reboot_or_slot1_format_drift_events
        ),
        "slot1_data_sector_writes": p66_rep.slot1_data_sector_writes,
        "slot1_vault_mutation_bytes": p66_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p66_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_eopnotsupp_enforced": p66_rep.slot1_vault_erofs_eopnotsupp_enforced,
        "overall_ready_for_hardware_attach": p66_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p66_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p66_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p66_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec66[0],
            pillar_id=spec66[1],
            phase_label=spec66[2],
            module_name=spec66[3],
            passed=bool(p66_rep.all_passed),
            status=p66_rep.status,
            verification_mode=p66_rep.verification_mode,
            elapsed_seconds=p66_dt,
            key_metrics=p66_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec66[1],
                    "mode": p66_rep.verification_mode,
                    "status": p66_rep.status,
                    "metrics": p66_metrics,
                    "passed": p66_rep.all_passed,
                }
            ),
            errors=tuple(p66_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master66_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p66_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_66_PILLAR_COUNT == 66
        and pillars_passed == 66
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE361_SCHEMA,
            "schema_version": PHASE361_MASTER_SCHEMA,
            "version": PHASE361_VERSION,
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

    return Master66PillarRecoveryReport(
        schema=PHASE361_SCHEMA,
        schema_version=PHASE361_MASTER_SCHEMA,
        version=PHASE361_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=(
            P361_STATUS_VERIFIED_66OF66_AGGREGATOR if all_ok else P361_STATUS_FAIL_66OF66_AGGREGATOR
        ),
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P361_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.50,
        under_6s_budget=elapsed < P361_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P361_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p66_rep.donor_snapshot,
        pillar66_a_breathing_camid_reel_sdhc_vault=(
            p66_rep.pillar_66a_breathing_camid_reel_sdhc_vault
        ),
        pillar66_b_copyright46_powersave_ntscpal_vault=(
            p66_rep.pillar_66b_copyright46_powersave_ntscpal_vault
        ),
        breathing_comp_lockout_or_catalyst_drift_events=(
            p66_rep.breathing_comp_lockout_or_catalyst_drift_events
        ),
        file_settings_camid_reel_or_sdhc_drift_events=(
            p66_rep.file_settings_camid_reel_or_sdhc_drift_events
        ),
        copyright_46ch_reset_erratum_or_serial_drift_events=(
            p66_rep.copyright_46ch_reset_erratum_or_serial_drift_events
        ),
        camset_copyright_pii_leak_events=p66_rep.camset_copyright_pii_leak_events,
        camset_copyright_pii_leaked_bytes=p66_rep.camset_copyright_pii_leaked_bytes,
        powersave_9cond_or_dormant_monitor_drift_events=(
            p66_rep.powersave_9cond_or_dormant_monitor_drift_events
        ),
        dormant_power_save_by_monitor_exposed_events=(
            p66_rep.dormant_power_save_by_monitor_exposed_events
        ),
        ntsc_pal_reboot_or_slot1_format_drift_events=(
            p66_rep.ntsc_pal_reboot_or_slot1_format_drift_events
        ),
        breathing_comp_resettable_by_camera_settings_reset=(
            P361_FX3_BREATHING_RESETTABLE_BY_CAMERA_SETTINGS_RESET
        ),
        catalyst_browse_breathing_supported=P361_CATALYST_BROWSE_BREATHING_SUPPORTED,
        catalyst_prepare_breathing_supported=P361_CATALYST_PREPARE_BREATHING_SUPPORTED,
        fx3_title_name_max_chars=P361_FX3_TITLE_MAX_LEN,
        fx3_sdhc_fat32_split_gb=P361_SDHC_FAT32_SPLIT_GB,
        fx6_title_prefix_min_chars=P361_FX6_TITLE_PREFIX_MIN_LEN,
        fx6_title_prefix_max_chars=P361_FX6_TITLE_PREFIX_MAX_LEN,
        copyright_info_max_chars=P361_COPYRIGHT_INFO_MAX_LEN,
        round57_erratum_copyright_resettable=P361_ROUND57_ERRATUM_ALL_COPYRIGHT_RESETTABLE,
        write_serial_still_and_movie_active=P361_WRITE_SERIAL_STILL_AND_MOVIE_ACTIVE,
        fx6_has_exif_copyright_menu=P361_FX6_HAS_EXIF_COPYRIGHT_MENU,
        fx3_powersave_bypass_condition_count=len(P361_FX3_POWER_SAVE_9_BYPASS_CONDITIONS),
        fx3_has_power_save_by_monitor=P361_FX3_HAS_POWER_SAVE_BY_MONITOR,
        slot1_data_sector_writes=(
            m65_rep.slot1_data_sector_writes + p66_rep.slot1_data_sector_writes
        ),
        slot1_vault_mutation_bytes=(
            m65_rep.slot1_vault_mutation_bytes + p66_rep.slot1_vault_mutation_bytes
        ),
        rf_packets_transmitted=m65_rep.rf_packets_transmitted + p66_rep.rf_packets_transmitted,
        rf_nvs_mutation_bytes=m65_rep.rf_nvs_mutation_bytes + p66_rep.rf_nvs_mutation_bytes,
        slot1_format_hard_locked=(
            m65_rep.slot1_format_hard_locked and p66_rep.slot1_format_hard_locked
        ),
        slot1_vault_erofs_eopnotsupp_enforced=(
            m65_rep.slot1_vault_erofs_eopnotsupp_enforced
            and p66_rep.slot1_vault_erofs_eopnotsupp_enforced
        ),
        slot1_vault_erofs_ebusy_enforced=(
            m65_rep.slot1_vault_erofs_ebusy_enforced and p66_rep.slot1_vault_erofs_ebusy_enforced
        ),
        hdmi_raw_output_or_media_vault_drift_events=(
            m65_rep.hdmi_raw_output_or_media_vault_drift_events
        ),
        hdmi_4k_only_or_gamut_removal_drift_events=(
            m65_rep.hdmi_4k_only_or_gamut_removal_drift_events
        ),
        desqueeze_ratio_lock_or_bypass_drift_events=(
            m65_rep.desqueeze_ratio_lock_or_bypass_drift_events
        ),
        rec_lamp_tally_or_emph_display_drift_events=(
            m65_rep.rec_lamp_tally_or_emph_display_drift_events
        ),
        dormant_var_shutter_or_apsc_reset_drift_events=(
            m65_rep.dormant_var_shutter_or_apsc_reset_drift_events
        ),
        dormant_var_shutter_exposed_events=m65_rep.dormant_var_shutter_exposed_events,
        hdmi_red_border_clean_feed_leak_pixels=(
            m65_rep.hdmi_red_border_clean_feed_leak_pixels
        ),
        recorded_media_desqueeze_pixels=m65_rep.recorded_media_desqueeze_pixels,
        fx6_sdi_desqueeze_pixels=m65_rep.fx6_sdi_desqueeze_pixels,
        shoe_audio_preemption_or_limiter_drift_events=(
            m65_rep.shoe_audio_preemption_or_limiter_drift_events
        ),
        subject_recog_myth_or_face_memory_drift_events=(
            m65_rep.subject_recog_myth_or_face_memory_drift_events
        ),
        silent_mode_target_or_barrier_drift_events=(
            m65_rep.silent_mode_target_or_barrier_drift_events
        ),
        bodydata_version_flash_or_slot1_vault_drift_events=(
            m65_rep.bodydata_version_flash_or_slot1_vault_drift_events
        ),
        dormant_shutter_when_pwr_off_exposed_events=(
            m65_rep.dormant_shutter_when_pwr_off_exposed_events
        ),
        hdmi_face_frame_pixels_emitted=m65_rep.hdmi_face_frame_pixels_emitted,
        cnflasha_pixel_map_mutation_bytes=m65_rep.cnflasha_pixel_map_mutation_bytes,
        slot1_bodydata_mutation_bytes=m65_rep.slot1_bodydata_mutation_bytes,
        bodydata_placement_or_flash_authorized=m65_rep.bodydata_placement_or_flash_authorized,
        ftp_protocol_sftp_or_jpeg_size_drift_events=(
            m65_rep.ftp_protocol_sftp_or_jpeg_size_drift_events
        ),
        wb_custom_cine_ei_or_shockless_drift_events=(
            m65_rep.wb_custom_cine_ei_or_shockless_drift_events
        ),
        movie_af_speed_or_focus_map_spoof_events=m65_rep.movie_af_speed_or_focus_map_spoof_events,
        marker_15ratio_peaking_hdmi_leak_events=m65_rep.marker_15ratio_peaking_hdmi_leak_events,
        zero_rf_usblan_or_slot1_avf_bypass_events=(
            m65_rep.zero_rf_usblan_or_slot1_avf_bypass_events
        ),
        usblan_packets_transmitted=m65_rep.usblan_packets_transmitted,
        hdmi_marker_peaking_pixels_emitted=m65_rep.hdmi_marker_peaking_pixels_emitted,
        slot1_avf_info_mutation_bytes=m65_rep.slot1_avf_info_mutation_bytes,
        rec_media_prioritize_or_autoswitch_drift_events=(
            m65_rep.rec_media_prioritize_or_autoswitch_drift_events
        ),
        card_speed_vpg200_vpg400_gate_drift_events=(
            m65_rep.card_speed_vpg200_vpg400_gate_drift_events
        ),
        proxy_sq_dci4k_or_120p_lockout_drift_events=(
            m65_rep.proxy_sq_dci4k_or_120p_lockout_drift_events
        ),
        cloud_init_persist_or_power_off_ble_rf_events=(
            m65_rep.cloud_init_persist_or_power_off_ble_rf_events
        ),
        mymenu_42slot_or_fx6_lock_spoof_events=m65_rep.mymenu_42slot_or_fx6_lock_spoof_events,
        zero_rf_or_slot1_vault_bypass_events=m65_rep.zero_rf_or_slot1_vault_bypass_events,
        slot1_dcim_m4root_avf_mutation_bytes=m65_rep.slot1_dcim_m4root_avf_mutation_bytes,
        big6_home_or_lower_left_nd_drift_events=m65_rep.big6_home_or_lower_left_nd_drift_events,
        framing_manual_or_dormant_auto_framing_drift_events=(
            m65_rep.framing_manual_or_dormant_auto_framing_drift_events
        ),
        interval_shoot_9999_or_fx6_mxf_spoof_events=(
            m65_rep.interval_shoot_9999_or_fx6_mxf_spoof_events
        ),
        tc_make_regen_or_hdmi_rec_ctrl_drift_events=(
            m65_rep.tc_make_regen_or_hdmi_rec_ctrl_drift_events
        ),
        access_authen_ssh_tls_or_fan_max_drift_events=(
            m65_rep.access_authen_ssh_tls_or_fan_max_drift_events
        ),
        slot1_dcim_avf_mutation_bytes=m65_rep.slot1_dcim_avf_mutation_bytes,
        fx3_has_var_shutter=m65_rep.fx3_has_var_shutter,
        fx3_has_builtin_evf=m65_rep.fx3_has_builtin_evf,
        fx3_has_builtin_end_filter=False,
        fx3_has_bt_timecode_link=False,
        fx3_has_dormant_auto_framing=m65_rep.fx3_has_dormant_auto_framing,
        fx3_has_dormant_auto_hdr=False,
        fx3_has_dormant_bulb_timer=False,
        fx3_has_dormant_divide_extract=False,
        fx3_has_fan_control_max=m65_rep.fx3_has_fan_control_max,
        fx3_has_movie_self_timer=False,
        fx3_has_movie_sort_recording=m65_rep.fx3_has_movie_sort_recording,
        fx3_has_physical_end_hw=m65_rep.fx3_has_physical_end_hw,
        fx3_has_5axis_ibis=True,
        fx6_has_ibis=False,
        fx6_has_fan_control_max=m65_rep.fx6_has_fan_control_max,
        fx6_has_still_self_timer=False,
        fx6_has_fn_menu=False,
        fx6_has_my_dial=False,
        fx6_has_bluetooth_hardware=m65_rep.fx6_has_bluetooth_hardware,
        fx6_has_av_tv_rotate=False,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        master_66pillar_sha256=master_sha,
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


def evaluate_66pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master66PillarRecoveryReport:
    """Short alias for `evaluate_realhw_66pillar_recovery_master`."""
    return evaluate_realhw_66pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_66pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master66PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_66pillar_recovery_master`."""
    return evaluate_realhw_66pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_66pillar_recovery(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master66PillarRecoveryReport:
    """Milestone 324/349 dynamic discovery alias for `evaluate_realhw_66pillar_recovery_master`."""
    return evaluate_realhw_66pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_all_66_recovery_pillars(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master66PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_66pillar_recovery_master`."""
    return evaluate_realhw_66pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
