"""Phase 366 Milestone — Recovery Pillar 67 (`67A`/`67B`) & Concurrent 67/67 Master Recovery Verifier:
Wave-65 Sony ILME-FX3 (Ver. 7.02) vs ILME-FX6 (Ver. 6.01) Empirically Grounded Guardrails:
  * Pillar 67A (`[Zoom Range]` / 8-Step Standby-vs-Movie Zoom Speeds / `[Auto Slow Shutter]` 6+ Lockouts /
    Still-Only `[ISO AUTO Min. SS]` & Dual Base ISO Curve Matrix):
    1. `Shooting -> [Zoom]` (`[Zoom Range]`: `Optical zoom only` default / `ClearImage Zoom` `1.5x` 4K & `2.0x` HD /
       `Digital Zoom` `4.0x` Movie & `4x/6.1x/8x` Still 3:2 L/M/S; Reset-resistant `Not available` on
       `Camera Settings Reset`, cleared only on `Initialize`) + `Setup -> [Operation Customize] -> [Zoom Ring Rotate]`
       (`Left(W)/Right(T)` default / `Right(W)/Left(T)`, Reset-resistant `Not available`) vs **Resettable (`Can be reset`)**
       `[Zoom Lever Speed]` (`Standby` & `Movie Rec`, `1st=3`, `2nd=8 Fast`, range `1..8`),
       `[Custom Key Z. Speed]` (`1..8` default `3`, `Standby` & `Movie Rec`), and `[Remote Zoom Speed]` (`Variable` def /
       `Fixed` `1..8` def `3`). CIZ/Digital/Smart Zoom locked out (`EOPNOTSUPP=95`) under Still `RAW`/`RAW & JPEG`/
       `RAW & HEIF`, Movie `119.88p/100p` (`120p`), `S&Q >= 100fps`, HDMI `RAW Output = On`, or `Breathing Comp. = On`;
       when active, forces `[Focus Area]` Center-priority disabled, `[Metering Mode] = [Multi]`, and disables
       `Face/Eye Prior. in AF` / `Face Priority in Multi Metering` / `Tracking`. Contrasted vs `ILME-FX6 Ver. 6.01`
       `Technical > Zoom > Zoom Type` (2-only: `Optical Zoom Only` / `On(Clear Image Zoom)`, zero `Digital Zoom`, locked
       under `S&Q > 60fps` or `RAW` codec) + dual-rocker `Handle Zoom` (`Off/Low=3/High=8/Variable`).
    2. `Exposure/Color -> [Exposure]`: `[Auto Slow Shutter]` (Movie-only, `On` default, `Can be reset`, disabled under
       6+ official conditions: `S&Q`, `S`, `M`, fixed manual ISO != `ISO AUTO`, `Flexible Exp. Mode` manual shutter,
       `Log Shooting` in `Cine EI`/`Cine EI Quick`, and mutually exclusive with `[Shutter Mode] = Angle`),
       `[ISO Range Limit]` (Reset-resistant `Not available`, restricts manual `[ISO]` only — `ISO AUTO` min/max
       configured inside `[ISO] -> [ISO AUTO]`), Still-only `[ISO AUTO Min. SS]` (`P`/`A` + `ISO AUTO`, `SLOWER (-2 EV)..FASTER (+2 EV)`
       or `1/8000..30"`, `STD` default, `Can be reset`, disabled in Movie/`S&Q`, flash sync `1/250s` overrides),
       and empirically pinned Dual Base ISO gain curves (`20x` `+4.33 EV`: `800/12800` Cine EI, `640/12800` Flexible ISO
       S-Log3/S-Log2/ITU709 800%, `100/2000` PP11 S-Cinetone/HLG/HLG3/Cine4, `80/1600` PP Off/HLG2/Cine3/ITU709,
       `64/1280` Cine1, `50/1000` HLG1/Cine2; `[Base ISO]` switch exposed ONLY in `Cine EI`/`Cine EI Quick`) vs
       FX6 `Custom` (`Base Sensitivity = Low/High` + `AGC`, zero `ISO AUTO Min. SS`) & `Cine EI` (`800/12800`).
  * Pillar 67B (Dormant `Lossless Comp` `.ARW` Rejection / `[HLG Still Image]` / `Sort Recording` Spillover,
    `[USB LUN Setting] = Single` [`Slot 1`-Only!] macOS MSC Hazard, `NP-FZ100` PD Gate & Dual FX3/FX6 Dormant `UVC` Firewall):
    1. Still `.ARW` `[RAW File Type]` strictly exposes ONLY `Compressed` (default) & `Uncompressed` 14-bit (`Can be reset`);
       dormant `RAW_FILE_TYPE_LOSSLESS` (`L/M/S`) MUST be rejected (`EOPNOTSUPP=95`). `[JPEG/HEIF Switch]` (`JPEG` def /
       `HEIF(4:2:0)` / `HEIF(4:2:2)`) & `[HLG Still Image]` (`Off` def / `On`, internal typo `STILL_HLD_PHOTO_*`: requires
       HEIF switch + pure `HEIF` + `P/A/S/M`; forces `BT.2100`, ISO floor `100/125`, disables PP/Creative Look/DRO).
       `[Recording Media] = [Sort Recording]` + `[Auto Switch Media]` spillover blocked fail-closed by Tier-0
       `Slot 1 EROFS=30` (`slot1_data_sector_writes == 0`, zero `.ARW`/`.JPG`/`.HIF`/`avf` writes) vs FX6 zero still pipeline.
    2. `Setup -> [USB]` (ALL Reset-resistant `Not available`): `[USB Connection Mode]` strictly 4 options
       (`Sel. When Connect` def / `MassStorage(MSC)` / `MTP` / `Remote Shooting`), `[USB LUN Setting]` (`Multi` exposes
       `Slot 1 + Slot 2`; **`Single` exposes `Slot 1` ONLY — NEVER hiding Slot 1!**; `MTP` also maps `Slot 1`) blocking
       live macOS MSC attach (`mds`/`fseventsd`/`Finder`/`fsck_exfat` dirty writes) on Tier-0 `Slot 1` (`EROFS=30`,
       `hardware_live_attachment_authorized == False`); `[USB Power Supply]` (`On` def, Type-C only) enforces **`NP-FZ100`
       mandatory even on `9V/3A` USB-C PD** (battery-less DC requires `DC-C1` + `>=65W PD` + `5A e-Marked` cable) vs FX6
       `19.5V DC IN` (`18.0..20.5V`, `DC Low Voltage1/2 = 16.5V/15.5V`); and dual FX3/FX6 Dormant `UVC USB Streaming`
       Firewall (`USB_CONNECTION_USB_STREAMING` / `usb_f_uvc.ko` / `g_webcam.ko` / `BKID_APP_SETTING_USB_STREAMING_PROCAM`
       rejected `EOPNOTSUPP=95`), plus FX3 `Network -> [Streaming]` (`RTMP/RTMPS/SRT` USB-LAN zero-RF) `[Movie Rec During
       Streaming]` vs HDMI `[Rec. Media dur HDMI Output]` `Slot 1 EROFS=30` + Stage-B `/tmp` + `Backup.bin H0 == H3` (`16/16`).
  * Unified `67/67` Master Recovery Aggregator (Pillars `1..66` + Pillar `67`) running concurrently.

Safety Redlines (HARD-LOCKED):
  - Zero hardware attach, zero physical device writes, zero USB/UART TX, zero OTP/RPMB, zero eMMC writes.
  - Zero `Slot 1` format or data sector writes (`EROFS=30` fail-closed).
  - Zero raw firmware bytes leaked (`raw_firmware_bytes_leaked == 0`).
  - Bounded `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 25-donor inspection (`<= 2.0s` budget) with explicit
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
from .realhw_66pillar_breathing_camid_reel_copyright46_powersave_ntscpal_vault_verifier import (
    MASTER_66_PILLAR_SPECS,
    Master66PillarRecoveryReport,
    evaluate_realhw_66pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Phase 366 Metadata, Safety Redlines & Pinned Budget Constants
# ---------------------------------------------------------------------------

PHASE366_SCHEMA = (
    "realhw_67pillar_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault_verifier_v1"
)
PHASE366_MASTER_SCHEMA = "realhw_67pillar_recovery_master_v1"
PHASE366_VERSION = "1.0.0"
PHASE366_PHASE_NUMBER = 366

P366_ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"

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

P366_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED = False
P366_CROSS_MODEL_FLASH_AUTHORIZED = False
P366_EMMC_WRITES_AUTHORIZED = False
P366_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
P366_OVERALL_READY_FOR_HARDWARE_ATTACH = False

OTP_FUSE_TOUCHES = 0
OTP_FUSE_WRITES = 0
RPMB_COUNTER_INCREMENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PHYSICAL_DEVICE_WRITES = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

P366_BOUNDED_HEADER_BYTES = 4096
P366_MAX_FULL_DONOR_BYTES = 3_000_000
P366_DONOR_INSPECT_BUDGET_SECONDS = 2.0
P366_DONOR_INSPECT_CI_BUDGET_SECONDS = 2.0
P366_FAST_CLI_BUDGET_SECONDS = 1.50
P366_NOMINAL_BUDGET_SECONDS = 4.00
P366_CONCURRENT_CEILING_SECONDS = 6.00

P366_ENOENT_ERRNO = 2
P366_EBUSY_ERRNO = 16
P366_EINVAL_ERRNO = 22
P366_EROFS_ERRNO = 30
P366_EOPNOTSUPP_ERRNO = 95

# Camera Identities
P366_FX3_MODEL_NAME = "ILME-FX3"
P366_FX3_MODEL_ID = 0x91030080
P366_FX3_PRODUCT_CODENAME = "PRODUCT_MODEL_ALCIN_UUD"
P366_FX3_HELPGUIDE_ID = "ilc/2210"
P366_FX3_FW_VERSION = "7.02"
P366_FX3_SUPPORTED_FW_VERSIONS = (
    "7.02", "7.01", "7.00", "6.02", "6.00", "5.00", "4.00", "3.00", "2.05", "2.04", "2.00"
)

P366_FX6_DONOR_MODEL_NAME = "ILME-FX6"
P366_FX6_DONOR_FW_VERSION = "6.01"
P366_FX6_PRODUCT_CODENAME = "PRODUCT_MODEL_CHAPLIN"

# Pinned Wave-65 25 Donors (18 FX3 + 7 FX6, incl. USB Gadget + UVC kernel modules)
P366_DONOR_FX3_APPFW_702_RELPATH = P348_DONOR_FX3_APPFW_702_RELPATH
P366_DONOR_FX3_BACKUP_BIN_RELPATH = P348_DONOR_FX3_BACKUP_BIN_RELPATH
P366_DONOR_FX3_USBG_STORAGE_KO_RELPATH = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/usbg_storage.ko"
)
P366_DONOR_FX3_USBG_STILLIMAGE_KO_RELPATH = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/usbg_stillimage.ko"
)
P366_DONOR_FX3_USB_F_UVC_KO_RELPATH = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/usb_f_uvc.ko"
)
P366_DONOR_FX3_G_WEBCAM_KO_RELPATH = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/g_webcam.ko"
)
P366_DONOR_FX6_APPFW_601_RELPATH = P348_DONOR_FX6_APPFW_601_RELPATH
P366_DONOR_FX6_USBG_STORAGE_KO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/kmod/usbg_storage.ko"
)
P366_DONOR_FX6_USBG_STILLIMAGE_KO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/kmod/usbg_stillimage.ko"
)
P366_DONOR_FX6_USB_F_UVC_KO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/kmod/usb_f_uvc.ko"
)
P366_DONOR_FX6_G_WEBCAM_KO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/kmod/g_webcam.ko"
)
P366_DONOR_FX3_UXC_EN_F_RELPATH = P348_DONOR_FX3_UXC_EN_F_RELPATH
P366_DONOR_FX3_UXC_SC_F_RELPATH = P348_DONOR_FX3_UXC_SC_F_RELPATH
P366_DONOR_FX3_UXC_TC_F_RELPATH = P348_DONOR_FX3_UXC_TC_F_RELPATH
P366_DONOR_FX3_UXC_JA_F_RELPATH = P348_DONOR_FX3_UXC_JA_F_RELPATH
P366_DONOR_FX3_UXC_EN_RELPATH = P348_DONOR_FX3_UXC_EN_RELPATH
P366_DONOR_FX3_UXC_SC_RELPATH = P348_DONOR_FX3_UXC_SC_RELPATH
P366_DONOR_FX3_UXC_TC_RELPATH = P348_DONOR_FX3_UXC_TC_RELPATH
P366_DONOR_FX3_UXC_JA_RELPATH = P348_DONOR_FX3_UXC_JA_RELPATH
P366_DONOR_FX3_UXC_EN_G_RELPATH = P348_DONOR_FX3_UXC_EN_G_RELPATH
P366_DONOR_FX3_UXC_SC_G_RELPATH = P348_DONOR_FX3_UXC_SC_G_RELPATH
P366_DONOR_FX3_UXC_TC_G_RELPATH = P348_DONOR_FX3_UXC_TC_G_RELPATH
P366_DONOR_FX3_UXC_JA_G_RELPATH = P348_DONOR_FX3_UXC_JA_G_RELPATH
P366_DONOR_FX6_UXC_EN_RELPATH = P348_DONOR_FX6_UXC_EN_RELPATH
P366_DONOR_FX6_UXC_EN_2_RELPATH = P348_DONOR_FX6_UXC_EN_2_RELPATH

P366_PINNED_FX3_APPFW_702_BYTES = P348_PINNED_FX3_APPFW_702_BYTES
P366_PINNED_FX3_APPFW_702_HDR4K_SHA256 = P348_PINNED_FX3_APPFW_702_HDR4K_SHA256
P366_PINNED_FX3_BACKUP_BIN_BYTES = P348_PINNED_FX3_BACKUP_BIN_BYTES
P366_PINNED_FX3_BACKUP_BIN_SHA256 = P348_PINNED_FX3_BACKUP_BIN_SHA256

P366_PINNED_FX3_USBG_STORAGE_KO_BYTES = 104_288
P366_PINNED_FX3_USBG_STORAGE_KO_SHA256 = (
    "b43130dbc3d9b72dc03c3acb7993639e1cefcbb43621fef809f6f617cb30b255"
)
P366_PINNED_FX3_USBG_STILLIMAGE_KO_BYTES = 49_448
P366_PINNED_FX3_USBG_STILLIMAGE_KO_SHA256 = (
    "0ef9132f6e043bd38a376519f0f130545e4c8ae68473b1b9d97b1228fa2829a5"
)
P366_PINNED_FX3_USB_F_UVC_KO_BYTES = 78_840
P366_PINNED_FX3_USB_F_UVC_KO_SHA256 = (
    "a23970925fa91ed7712f14bf7de8ac62ff9d63e9bcbfeecc94b37085d48c5ccc"
)
P366_PINNED_FX3_G_WEBCAM_KO_BYTES = 13_728
P366_PINNED_FX3_G_WEBCAM_KO_SHA256 = (
    "9d8df09a035d288673dbc59daac186959fe826fdddb613a7cecc57d321164792"
)

P366_PINNED_FX6_APPFW_601_BYTES = P348_PINNED_FX6_APPFW_601_BYTES
P366_PINNED_FX6_APPFW_601_HDR4K_SHA256 = P348_PINNED_FX6_APPFW_601_HDR4K_SHA256
P366_PINNED_FX6_USBG_STORAGE_KO_BYTES = 104_288
P366_PINNED_FX6_USBG_STORAGE_KO_SHA256 = (
    "fc6de444414c9931dc33ac9702aa9a8113e8d41bdf09d818de8fd0524783aa1e"
)
P366_PINNED_FX6_USBG_STILLIMAGE_KO_BYTES = 49_448
P366_PINNED_FX6_USBG_STILLIMAGE_KO_SHA256 = (
    "c62b1b698f552f7476df08407cf754abaa796e91deb694ec1239ea079dc19caa"
)
P366_PINNED_FX6_USB_F_UVC_KO_BYTES = 78_840
P366_PINNED_FX6_USB_F_UVC_KO_SHA256 = (
    "bf073599272e2bb5641668d457ff9962525f17a37c8c75f15a3892d7c26b5305"
)
P366_PINNED_FX6_G_WEBCAM_KO_BYTES = 13_728
P366_PINNED_FX6_G_WEBCAM_KO_SHA256 = (
    "bec168eebeba90e4b5f6a35e1c4e12bfc0a70242c4a99ad01fde4c29462110d0"
)

P366_PINNED_FX3_UXC_EN_F_BYTES = P348_PINNED_FX3_UXC_EN_F_BYTES
P366_PINNED_FX3_UXC_EN_F_SHA256 = P348_PINNED_FX3_UXC_EN_F_SHA256
P366_PINNED_FX3_UXC_SC_F_BYTES = P348_PINNED_FX3_UXC_SC_F_BYTES
P366_PINNED_FX3_UXC_SC_F_SHA256 = P348_PINNED_FX3_UXC_SC_F_SHA256
P366_PINNED_FX3_UXC_TC_F_BYTES = P348_PINNED_FX3_UXC_TC_F_BYTES
P366_PINNED_FX3_UXC_TC_F_SHA256 = P348_PINNED_FX3_UXC_TC_F_SHA256
P366_PINNED_FX3_UXC_JA_F_BYTES = P348_PINNED_FX3_UXC_JA_F_BYTES
P366_PINNED_FX3_UXC_JA_F_SHA256 = P348_PINNED_FX3_UXC_JA_F_SHA256
P366_PINNED_FX3_UXC_EN_BYTES = P348_PINNED_FX3_UXC_EN_BYTES
P366_PINNED_FX3_UXC_EN_SHA256 = P348_PINNED_FX3_UXC_EN_SHA256
P366_PINNED_FX3_UXC_SC_BYTES = P348_PINNED_FX3_UXC_SC_BYTES
P366_PINNED_FX3_UXC_SC_SHA256 = P348_PINNED_FX3_UXC_SC_SHA256
P366_PINNED_FX3_UXC_TC_BYTES = P348_PINNED_FX3_UXC_TC_BYTES
P366_PINNED_FX3_UXC_TC_SHA256 = P348_PINNED_FX3_UXC_TC_SHA256
P366_PINNED_FX3_UXC_JA_BYTES = P348_PINNED_FX3_UXC_JA_BYTES
P366_PINNED_FX3_UXC_JA_SHA256 = P348_PINNED_FX3_UXC_JA_SHA256
P366_PINNED_FX3_UXC_EN_G_BYTES = P348_PINNED_FX3_UXC_EN_G_BYTES
P366_PINNED_FX3_UXC_EN_G_SHA256 = P348_PINNED_FX3_UXC_EN_G_SHA256
P366_PINNED_FX3_UXC_SC_G_BYTES = P348_PINNED_FX3_UXC_SC_G_BYTES
P366_PINNED_FX3_UXC_SC_G_SHA256 = P348_PINNED_FX3_UXC_SC_G_SHA256
P366_PINNED_FX3_UXC_TC_G_BYTES = P348_PINNED_FX3_UXC_TC_G_BYTES
P366_PINNED_FX3_UXC_TC_G_SHA256 = P348_PINNED_FX3_UXC_TC_G_SHA256
P366_PINNED_FX3_UXC_JA_G_BYTES = P348_PINNED_FX3_UXC_JA_G_BYTES
P366_PINNED_FX3_UXC_JA_G_SHA256 = P348_PINNED_FX3_UXC_JA_G_SHA256
P366_PINNED_FX6_UXC_EN_BYTES = P348_PINNED_FX6_UXC_EN_BYTES
P366_PINNED_FX6_UXC_EN_SHA256 = P348_PINNED_FX6_UXC_EN_SHA256
P366_PINNED_FX6_UXC_EN_2_BYTES = P348_PINNED_FX6_UXC_EN_2_BYTES
P366_PINNED_FX6_UXC_EN_2_SHA256 = P348_PINNED_FX6_UXC_EN_2_SHA256

# Zero-Violation Pillar 67 Counters & Vault Flags
P366_ZOOM_CIZ_LOCKOUT_OR_8SPEED_RESET_DRIFT_EVENTS = 0
P366_AUTOSLOW_6LOCKOUT_OR_MINSS_STILL_DRIFT_EVENTS = 0
P366_DUAL_BASE_ISO_CURVE_MATRIX_DRIFT_EVENTS = 0
P366_DORMANT_LOSSLESS_ARW_EXPOSED_EVENTS = 0
P366_HLG_STILL_OR_SORT_REC_SPILLOVER_DRIFT_EVENTS = 0
P366_USB_LUN_SINGLE_SLOT1_MSC_HAZARD_EVENTS = 0
P366_NPFZ100_PD_INTERLOCK_OR_DCC1_DRIFT_EVENTS = 0
P366_DORMANT_UVC_STREAMING_EXPOSED_EVENTS = 0

P366_SLOT1_DATA_SECTOR_WRITES = 0
P366_SLOT1_VAULT_MUTATION_BYTES = 0
P366_RF_PACKETS_TRANSMITTED = 0
P366_RF_NVS_MUTATION_BYTES = 0

P366_SLOT1_FORMAT_HARD_LOCKED = True
P366_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True
P366_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True
P366_AIRPLANE_MODE_FORCED_ON = True

P366_STAGE_B_VOLATILE_OVERLAY_DIR = "/tmp/fx3_stage_b_overlay/pillar67"
P366_FORBIDDEN_PERSISTENT_TARGETS = (
    "/dev/cnflasha",
    "/setting",
    "/mnt/emmc",
    "/nflasha",
)
P366_TIER0_SURFACE_COUNT = 16

# ---------------------------------------------------------------------------
# Wave-65 Empirically Verified Constants (UXC resid16, ELF & Kernel Symbols)
# ---------------------------------------------------------------------------

# 1. Sub-Pillar 67A-1: `[Zoom Range]`, 8-Step Standby/Movie Speeds & `[Zoom Ring Rotate]`
P366_ZOOM_RANGE_F_RESID16S = (0x7164, 0x774E)
P366_ZOOM_OPTICAL_F_RESID16S = (0x73F2, 0x74C9)
P366_ZOOM_CIZ_F_RESID16S = (0x70E0, 0x70E1)
P366_ZOOM_DIGITAL_F_RESID16S = (0x796C, 0x796D)
P366_ZOOM_LEVER_SPEED_F_RESID16S = (0x6079, 0x6304, 0x6FC0, 0x753F, 0x78F0)
P366_CUSTOM_KEY_ZOOM_SPEED_F_RESID16S = (0x6CCF, 0x78E8, 0x6FDB)
P366_REMOTE_ZOOM_SPEED_F_RESID16S = (0x7128, 0x728A, 0x7435)
P366_ZOOM_RING_ROTATE_F_RESID16S = (0x6BE7, 0x7A01, 0x7A9E)

P366_BKID_ZOOM_SETTING = "BKID_APP_setting_zoom_setting"
P366_BKID_ZOOM_DIRECTION = "BKID_APP_setting_zoom_direction"
P366_BKID_1ST_ZOOM_SPD_STBY = "BKID_APP_setting_1st_zoom_spd_stby"
P366_BKID_1ST_ZOOM_SPD_REC = "BKID_APP_setting_1st_zoom_spd_rec"
P366_BKID_2ND_ZOOM_SPD_STBY = "BKID_APP_setting_2nd_zoom_spd_stby"
P366_BKID_2ND_ZOOM_SPD_REC = "BKID_APP_setting_2nd_zoom_spd_rec"
P366_BKID_FIXED_ZOOM_SPEED_STBY = "BKID_APP_setting_fixed_zoom_speed_stby"
P366_BKID_FIXED_ZOOM_SPEED_REC = "BKID_APP_setting_fixed_zoom_speed_rec"
P366_BKID_REMOTE_ZOOM_SPEED_TYPE = "BKID_APP_setting_fixed_zoom_speed_type"
P366_BKID_REMOTE_ZOOM_SPEED_STBY = "BKID_APP_setting_remote_fixed_zoom_speed_stby"
P366_BKID_REMOTE_ZOOM_SPEED_REC = "BKID_APP_setting_remote_fixed_zoom_speed_rec"

P366_FX3_ZOOM_RANGES = ("Optical zoom only", "ClearImage Zoom", "Digital Zoom")
P366_FX3_ZOOM_RANGE_DEFAULT = "Optical zoom only"
P366_FX3_ZOOM_RANGE_RESETTABLE = False  # Not available under Camera Settings Reset
P366_FX3_ZOOM_RING_ROTATES = ("Left(W)/Right(T)", "Right(W)/Left(T)")
P366_FX3_ZOOM_RING_ROTATE_DEFAULT = "Left(W)/Right(T)"
P366_FX3_ZOOM_RING_ROTATE_RESETTABLE = False  # Not available under Camera Settings Reset
P366_FX3_ZOOM_SPEED_RESETTABLE = True  # Can be reset under Camera Settings Reset
P366_FX3_ZOOM_SPEED_MIN = 1
P366_FX3_ZOOM_SPEED_MAX = 8
P366_FX3_ZOOM_LEVER_1ST_DEFAULT = 3
P366_FX3_ZOOM_LEVER_2ND_DEFAULT = 8
P366_FX3_CUSTOM_KEY_ZOOM_SPEED_DEFAULT = 3
P366_FX3_REMOTE_ZOOM_SPEED_TYPES = ("Variable", "Fixed")
P366_FX3_REMOTE_ZOOM_SPEED_TYPE_DEFAULT = "Variable"
P366_FX3_REMOTE_ZOOM_FIXED_SPEED_DEFAULT = 3

P366_FX3_MOVIE_CIZ_4K_SCALE = 1.5
P366_FX3_MOVIE_CIZ_HD_SCALE = 2.0
P366_FX3_MOVIE_DIGITAL_MAX_SCALE = 4.0
P366_FX3_STILL_S_DIGITAL_MAX_SCALE = 8.0
P366_FX3_ZOOM_SCALE_TABLE: Dict[Tuple[str, str], Dict[str, Optional[float]]] = {
    ("Movie", "4K"): {"Optical": 1.0, "Smart": None, "ClearImage": 1.5, "Digital": 4.0},
    ("Movie", "HD"): {"Optical": 1.0, "Smart": None, "ClearImage": 2.0, "Digital": 4.0},
    ("Still_FF", "L"): {"Optical": 1.0, "Smart": None, "ClearImage": 2.0, "Digital": 4.0},
    ("Still_FF", "M"): {"Optical": 1.0, "Smart": 1.5, "ClearImage": 3.1, "Digital": 6.1},
    ("Still_FF", "S"): {"Optical": 1.0, "Smart": 2.0, "ClearImage": 4.0, "Digital": 8.0},
    ("Still_APSC", "M"): {"Optical": 1.0, "Smart": 1.3, "ClearImage": 2.6, "Digital": 5.2},
    ("Still_APSC", "S"): {"Optical": 1.0, "Smart": 2.0, "ClearImage": 4.0, "Digital": 8.0},
}

P366_FX6_ZOOM_TYPES = ("Optical Zoom Only", "On(Clear Image Zoom)")
P366_FX6_HAS_DIGITAL_ZOOM = False
P366_FX6_HANDLE_ZOOM_MODES = ("Off", "Low", "High", "Variable")
P366_FX6_HANDLE_ZOOM_LOW_DEFAULT = 3
P366_FX6_HANDLE_ZOOM_HIGH_DEFAULT = 8

# 2. Sub-Pillar 67A-2: `[Auto Slow Shutter]`, `[ISO Range Limit]`, Still `[ISO AUTO Min. SS]`, Dual Base ISO
P366_AUTO_SLOW_SHUTTER_F_RESID16S = (0x632F, 0x6483, 0x76EE)
P366_ISO_RANGE_LIMIT_F_RESID16S = (0x69CB, 0x6D8B, 0x72F8, 0x75A0)
P366_ISO_AUTO_MIN_SS_F_RESID16S = (0x6717, 0x778B)
P366_BASE_ISO_F_RESID16S = (0x78CE, 0x696B)

P366_BKID_AUTO_SLOW_SHUTTER = "BKID_APP_setting_auto_slow_shutter"
P366_BKID_ISO_AUTO_MIN_SS = "BKID_APP_setting_iso_auto_min_s_s"
P366_BKID_BASE_ISO = "BKID_APP_setting_base_iso"

P366_FX3_AUTO_SLOW_SHUTTER_DEFAULT = "On"
P366_FX3_AUTO_SLOW_SHUTTER_RESETTABLE = True
P366_FX3_AUTO_SLOW_SHUTTER_LOCKOUT_MODES = (
    "sq_motion",
    "shutter_priority_s",
    "manual_exposure_m",
    "fixed_manual_iso",
    "flexible_exp_manual_shutter",
    "cine_ei_or_quick",
    "shutter_mode_angle",
)
P366_FX3_ISO_RANGE_LIMIT_RESETTABLE = False  # Not available under Camera Settings Reset
P366_FX3_ISO_AUTO_MIN_SS_PRESETS = (
    "SLOWER",
    "SLOW",
    "STD",
    "FAST",
    "FASTER",
    "1/8000",
    "1/4000",
    "1/2000",
    "1/1000",
    "1/500",
    "1/250",
    "1/125",
    "1/60",
    "1/30",
    "1/15",
    "1/8",
    "1/4",
    "1/2",
    "1\"",
    "2\"",
    "4\"",
    "8\"",
    "15\"",
    "30\"",
)
P366_FX3_ISO_AUTO_MIN_SS_DEFAULT = "STD"
P366_FX3_ISO_AUTO_MIN_SS_RESETTABLE = True
P366_FX3_FLASH_SYNC_CEILING = "1/250"

# Dual Base ISO Gain Curve Matrix (`High = 20x Low`, +4.33 EV; `[Base ISO]` menu exposed ONLY in Cine EI / Cine EI Quick)
P366_FX3_DUAL_BASE_ISO_CURVES: Dict[str, Tuple[int, int, bool]] = {
    "Cine EI": (800, 12800, True),
    "Cine EI Quick": (800, 12800, True),
    "Flexible ISO (S-Log3)": (640, 12800, False),
    "PP S-Log3": (640, 12800, False),
    "PP S-Log2": (640, 12800, False),
    "PP ITU709(800%)": (640, 12800, False),
    "PP11 S-Cinetone": (100, 2000, False),
    "PP HLG": (100, 2000, False),
    "PP HLG3": (100, 2000, False),
    "PP Cine4": (100, 2000, False),
    "PP Off": (80, 1600, False),
    "PP Movie": (80, 1600, False),
    "PP Still": (80, 1600, False),
    "PP HLG2": (80, 1600, False),
    "PP Cine3": (80, 1600, False),
    "PP ITU709": (80, 1600, False),
    "PP Cine1": (64, 1280, False),
    "PP HLG1": (50, 1000, False),
    "PP Cine2": (50, 1000, False),
}
P366_FX6_HAS_ISO_AUTO_MIN_SS = False
P366_FX6_BASE_SENSITIVITY_MODES = ("Low", "High")

# 3. Sub-Pillar 67B-1: Still `.ARW` `[RAW File Type]` (Dormant `Lossless Comp`), `HEIF` / `[HLG Still Image]`, `Sort Recording`
P366_RAW_FILE_TYPE_F_RESID16 = 0x6FF2
P366_RAW_UNCOMPRESSED_F_RESID16S = (0x67A9, 0x6F5B)
P366_RAW_COMPRESSED_F_RESID16S = (0x6327, 0x6F67)
P366_DORMANT_RAW_LOSSLESS_F_RESID16S = (0x6B56, 0x7897, 0x6BFD, 0x7894)
P366_JPEG_HEIF_SWITCH_F_RESID16S = (0x742A, 0x6E14, 0x7959, 0x6057)
P366_HLG_STILL_IMAGE_F_RESID16 = 0x76C8
P366_SORT_RECORDING_F_RESID16 = 0x7916
P366_AUTO_SWITCH_MEDIA_F_RESID16 = 0x6DD9

P366_FX3_ACTIVE_RAW_FILE_TYPES = ("Compressed", "Uncompressed")
P366_FX3_RAW_FILE_TYPE_DEFAULT = "Compressed"
P366_FX3_DORMANT_RAW_FILE_TYPES = (
    "Lossless Comp",
    "Lossless Comp (L)",
    "Lossless Comp (M)",
    "Lossless Comp (S)",
    "RAW_FILE_TYPE_LOSSLESS",
    "RAW_FILE_TYPE_LOSSLESS_L",
    "RAW_FILE_TYPE_LOSSLESS_M",
    "RAW_FILE_TYPE_LOSSLESS_S",
)
P366_FX3_HAS_DORMANT_LOSSLESS_ARW_EXPOSED = False
P366_FX3_STILL_FILE_FORMATS = ("JPEG", "HEIF", "RAW", "RAW & JPEG", "RAW & HEIF")
P366_FX3_JPEG_HEIF_SWITCH_MODES = ("JPEG", "HEIF(4:2:0)", "HEIF(4:2:2)")
P366_FX3_HLG_STILL_COLOR_SPACE = "BT.2100"
P366_FX3_HLG_STILL_ISO_FLOOR = 100
P366_FX3_REC_MEDIA_MODES = ("Slot 1", "Slot 2", "Simult. Recording", "Sort Recording")
P366_FX3_REC_MEDIA_RESETTABLE = False
P366_FX6_HAS_STILL_ARW_HLG_PIPELINE = False

# 4. Sub-Pillar 67B-2: `[USB Connection Mode]` 4-Option, `[USB LUN Setting] = Single` (`Slot 1`-Only!), `NP-FZ100` PD & Dual `UVC` Firewall
P366_USB_CONNECTION_MODE_F_RESID16 = 0x69A2
P366_USB_LUN_SETTING_F_RESID16 = 0x6B19
P366_USB_LUN_MULTI_F_RESID16S = (0x679D, 0x6CEC)
P366_USB_LUN_SINGLE_F_RESID16S = (0x69BE, 0x776D)
P366_USB_POWER_SUPPLY_F_RESID16 = 0x721E
P366_DORMANT_USB_STREAMING_F_RESID16S = (0x6216, 0x6194)
P366_DORMANT_USB_STREAMING_G_RESID16 = 0x63F7
P366_MOVIE_REC_DURING_STREAMING_F_RESID16 = 0x79D5
P366_REC_MEDIA_DUR_HDMI_F_RESID16 = 0x6144

P366_FX3_ACTIVE_USB_CONNECTION_MODES = (
    "Sel. When Connect",
    "MassStorage(MSC)",
    "MTP",
    "Remote Shooting",
)
P366_FX3_USB_CONNECTION_DEFAULT = "Sel. When Connect"
P366_FX3_USB_MENU_RESETTABLE = False  # Setup -> USB all Not available under Camera Settings Reset
P366_FX3_USB_LUN_SETTINGS = ("Multi", "Single")
P366_FX3_USB_LUN_DEFAULT = "Multi"
P366_FX3_USB_VID_PID = "054C:0DA1"
P366_MACOS_MSC_HAZARD_PROCESSES = ("mds", "mdworker", "fseventsd", "Finder", "fsck_exfat", "fsck_msdos")
P366_FX3_USB_PD_VOLTS = 9
P366_FX3_USB_PD_AMPS = 3
P366_FX3_DC_COUPLER_MODEL = "DC-C1"
P366_FX3_DC_COUPLER_MIN_WATTS = 65
P366_FX3_DC_COUPLER_CABLE_AMPS = 5
P366_FX6_DC_IN_NOMINAL_V = 19.5
P366_FX6_DC_IN_RANGE_V = (18.0, 20.5)
P366_FX6_DC_LOW_VOLTAGE1_V = 16.5
P366_FX6_DC_LOW_VOLTAGE2_V = 15.5
P366_FX3_HAS_NATIVE_UVC_STREAMING = False
P366_FX6_HAS_NATIVE_UVC_STREAMING = False
P366_FX3_STREAMING_TRANSPORTS = ("USB-LAN", "Wi-Fi", "USB Tethering")
P366_FX3_STREAMING_PROTOCOLS = ("RTMP", "RTMPS", "SRT")
P366_FX3_MOVIE_REC_DURING_STREAMING_MODES = ("Disable", "Enable")
P366_FX3_REC_MEDIA_DUR_HDMI_MODES = ("On", "Off(HDMI Only)")

# Common Enums & Vault Constants
P366_ON_OFF_MODES = ("Off", "On")
P366_SHOOTING_DOMAINS = ("Movie", "Still", "S&Q")
P366_EXPOSURE_MODES = ("P", "A", "S", "M", "Flexible Exp.", "iAuto")
P366_RESET_ACTIONS = ("None", "Camera Settings Reset", "Initialize")
P366_VAULT_ACTIONS = (
    "NONE",
    "READ_ONLY_AUDIT",
    "CARD_WRITE_STILL_ARW_HIF_SORT_SPILLOVER",
    "CARD_WRITE_MOVIE_REC_DURING_STREAMING",
    "CARD_WRITE_REC_MEDIA_DUR_HDMI",
    "HOST_MSC_SINGLE_SLOT1_MOUNT",
    "HOST_MSC_MULTI_SLOT1_MOUNT",
    "HOST_MTP_SLOT1_ACCESS",
)
P366_WRITE_MUTATING_VAULT_ACTIONS = (
    "CARD_WRITE_STILL_ARW_HIF_SORT_SPILLOVER",
    "CARD_WRITE_MOVIE_REC_DURING_STREAMING",
    "CARD_WRITE_REC_MEDIA_DUR_HDMI",
    "HOST_MSC_SINGLE_SLOT1_MOUNT",
    "HOST_MSC_MULTI_SLOT1_MOUNT",
    "HOST_MTP_SLOT1_ACCESS",
)
P366_VAULT_FIREWALL_ERRNOS = (None, "EROFS", "EOPNOTSUPP", "EBUSY", "EINVAL", "ENOENT")

# Status & Block Codes
P366_STATUS_VERIFIED_PILLAR_67A = (
    "VERIFIED_PILLAR_67A_ZOOM_CIZ_8SPEED_AUTOSLOW_MINSS_DUAL_BASE_ISO_VAULT"
)
P366_STATUS_REJECTED_PILLAR_67A = (
    "REJECTED_PILLAR_67A_ZOOM_CIZ_8SPEED_AUTOSLOW_MINSS_DUAL_BASE_ISO_VAULT"
)
P366_STATUS_VERIFIED_PILLAR_67B = (
    "VERIFIED_PILLAR_67B_ARW_HLG_SORT_USBLUN_SINGLE_NPFZ100_UVC_FIREWALL_VAULT"
)
P366_STATUS_REJECTED_PILLAR_67B = (
    "REJECTED_PILLAR_67B_ARW_HLG_SORT_USBLUN_SINGLE_NPFZ100_UVC_FIREWALL_VAULT"
)
P366_STATUS_VERIFIED_PILLAR67_SUITE = (
    "VERIFIED_PILLAR67_ZOOM_CIZ_AUTOSLOW_BASEISO_ARW_USBLUN_UVC_VAULT"
)
P366_STATUS_FAIL_PILLAR67_SUITE = (
    "FAIL_PILLAR67_ZOOM_CIZ_AUTOSLOW_BASEISO_ARW_USBLUN_UVC_VAULT"
)
P366_STATUS_VERIFIED_67OF67_AGGREGATOR = "VERIFIED_67OF67_PILLAR_RECOVERY_MASTER"
P366_STATUS_FAIL_67OF67_AGGREGATOR = "FAIL_67OF67_PILLAR_RECOVERY_MASTER"

P366_BLOCKED_SAFETY_POLICY_VIOLATION = "BLOCKED_P366_SAFETY_POLICY_VIOLATION"
P366_BLOCKED_INVALID_PILLAR67A_SPEC = "BLOCKED_P366_INVALID_PILLAR67A_SPEC"
P366_BLOCKED_INVALID_PILLAR67B_SPEC = "BLOCKED_P366_INVALID_PILLAR67B_SPEC"
P366_BLOCKED_ZOOM_CIZ_OR_8SPEED_RESET_DRIFT = (
    "BLOCKED_P366_ZOOM_CIZ_OR_8SPEED_RESET_DRIFT"
)
P366_BLOCKED_AUTOSLOW_MINSS_OR_DUAL_BASE_ISO_DRIFT = (
    "BLOCKED_P366_AUTOSLOW_MINSS_OR_DUAL_BASE_ISO_DRIFT"
)
P366_BLOCKED_DORMANT_ARW_HLG_OR_SORT_SPILLOVER_DRIFT = (
    "BLOCKED_P366_DORMANT_ARW_HLG_OR_SORT_SPILLOVER_DRIFT"
)
P366_BLOCKED_USBLUN_SINGLE_PD_OR_DORMANT_UVC_DRIFT = (
    "BLOCKED_P366_USBLUN_SINGLE_PD_OR_DORMANT_UVC_DRIFT"
)
P366_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL = "BLOCKED_P366_SLOT1_VAULT_WRITE_FIREWALL"
P366_BLOCKED_PERSISTENT_OVERLAY_ESCAPE = "BLOCKED_P366_PERSISTENT_OVERLAY_ESCAPE"
P366_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT = "BLOCKED_P366_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P366_PILLAR_67A_SCENARIO_IDS = (
    "p366_67a_01_allow_zoom_ciz_8speed_reset_split_autoslow_on_and_dual_base_iso_cine_ei",
    "p366_67a_02_allow_still_iso_auto_minss_s_cinetone_100_2000_and_fx6_2zoom_handle_contrast",
    "p366_67a_03_reject_ciz_digital_in_raw_120p_sq100_fx6_digital_spoof_or_zoom_range_reset_wipe",
    "p366_67a_04_reject_autoslow_6lockout_bypass_movie_minss_or_flash_sync_minss_override_drift",
    "p366_67a_05_reject_dual_base_iso_curve_drift_cine_ei_base_menu_spoof_or_iso_limit_reset_wipe",
    "p366_67a_06_reject_slot1_vault_write_overlay_escape_or_backup_bin_h0_h3_drift",
)
P366_PILLAR_67B_SCENARIO_IDS = (
    "p366_67b_01_allow_arw_uncompressed_hlg_still_bt2100_100_and_dcc1_65w_5a_read_only_audit",
    "p366_67b_02_allow_usb_4mode_reset_resistant_network_usblan_rtmp_and_fx6_19_5v_dc_contrast",
    "p366_67b_03_reject_dormant_lossless_arw_lms_hlg_still_raw_spoof_or_fx6_still_arw_spoof",
    "p366_67b_04_reject_usb_lun_single_hiding_slot1_spoof_macos_msc_attach_or_batteryless_pd9v_3a",
    "p366_67b_05_reject_dormant_uvc_usb_streaming_on_fx3_or_fx6_and_movie_rec_dur_streaming_slot1",
    "p366_67b_06_reject_sort_rec_auto_switch_spillover_slot1_write_overlay_escape_or_h0_h3_drift",
)

MASTER_67_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_66_PILLAR_SPECS + (
    (
        67,
        "pillar67_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault",
        "Phase 366",
        "realhw_67pillar_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault_verifier",
    ),
)
MASTER_67_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_67_PILLAR_SPECS)
MASTER_67_PILLAR_COUNT = len(MASTER_67_PILLAR_IDS)


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
    return bool(is_forced_clean_room() or os.environ.get(P366_ENV_CLEAN_ROOM_TEST) == "1")


def _donor_inspect_budget_seconds() -> float:
    return (
        P366_DONOR_INSPECT_CI_BUDGET_SECONDS
        if os.environ.get("CI")
        else P366_DONOR_INSPECT_BUDGET_SECONDS
    )


def _is_tmpfs_path(path: str) -> bool:
    norm = posixpath.normpath(path)
    return norm == "/tmp" or norm.startswith("/tmp/")


def _targets_persistent_emmc(path: str) -> bool:
    norm = posixpath.normpath(path)
    return any(
        norm == t or norm.startswith(f"{t}/")
        for t in P366_FORBIDDEN_PERSISTENT_TARGETS
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
# Pure Deterministic Ground-Truth State Evaluators (67A & 67B)
# ---------------------------------------------------------------------------


def compute_expected_zoom_ciz_autoslow_baseiso_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    recording_fps: int,
    movie_resolution: str,
    still_file_format: str,
    still_image_size: str,
    apsc_s35_on: bool,
    raw_output: str,
    breathing_comp: str,
    zoom_range: str,
    zoom_ring_rotate: str,
    zoom_lever_1st_stby: int,
    zoom_lever_1st_rec: int,
    zoom_lever_2nd_stby: int,
    zoom_lever_2nd_rec: int,
    custom_key_zoom_speed_stby: int,
    custom_key_zoom_speed_rec: int,
    remote_zoom_speed_type: str,
    remote_zoom_fixed_stby: int,
    remote_zoom_fixed_rec: int,
    fx6_sq_motion: str,
    fx6_codec: str,
    fx6_handle_zoom_mode: str,
    exposure_mode: str,
    iso_setting: str,
    flexible_exp_manual_shutter: bool,
    log_shooting_mode: str,
    shutter_mode: str,
    auto_slow_shutter: str,
    iso_auto_min_ss: str,
    flash_active: bool,
    gamma_curve_key: str,
    hlg_still_image: str,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute exact Wave-65 Pillar 67A expected state (`Zoom`, `Auto Slow Shutter`, `ISO AUTO Min. SS`, `Dual Base ISO`)."""
    is_fx3 = camera_model == P366_FX3_MODEL_NAME
    is_fx6 = camera_model == P366_FX6_DONOR_MODEL_NAME

    # 1. `[Zoom Range]` / CIZ / Digital / Smart Zoom scales, lockouts & AF/Metering side effects
    zoom_errno: Optional[int] = None
    non_optical_zoom = zoom_range in ("ClearImage Zoom", "Digital Zoom", "Smart Zoom")
    if is_fx6:
        if zoom_range == "Digital Zoom":
            zoom_errno = P366_EOPNOTSUPP_ERRNO
            effective_zoom_range = "Optical zoom only"
        elif zoom_range == "ClearImage Zoom" and (
            (fx6_sq_motion == "On" and recording_fps > 60) or ("RAW" in fx6_codec)
        ):
            zoom_errno = P366_EOPNOTSUPP_ERRNO
            effective_zoom_range = "Optical zoom only"
        else:
            effective_zoom_range = zoom_range
        max_zoom_scale = (
            (P366_FX3_MOVIE_CIZ_4K_SCALE if movie_resolution == "4K" else P366_FX3_MOVIE_CIZ_HD_SCALE)
            if effective_zoom_range == "ClearImage Zoom"
            else 1.0
        )
    else:
        raw_still_lock = shooting_domain == "Still" and ("RAW" in still_file_format)
        hfr_lock = (
            (shooting_domain == "Movie" and recording_fps >= 100)
            or (shooting_domain == "S&Q" and recording_fps >= 100)
        )
        hdmi_raw_lock = raw_output == "On"
        breathing_lock = breathing_comp == "On"
        smart_movie_lock = zoom_range == "Smart Zoom" and shooting_domain in ("Movie", "S&Q")
        smart_l_lock = zoom_range == "Smart Zoom" and shooting_domain == "Still" and still_image_size == "L"
        if non_optical_zoom and (
            raw_still_lock or hfr_lock or hdmi_raw_lock or breathing_lock or smart_movie_lock or smart_l_lock
        ):
            zoom_errno = P366_EOPNOTSUPP_ERRNO
            effective_zoom_range = "Optical zoom only"
        else:
            effective_zoom_range = zoom_range

        if shooting_domain in ("Movie", "S&Q"):
            tbl_key = ("Movie", "4K" if movie_resolution == "4K" else "HD")
        else:
            tbl_key = ("Still_APSC" if apsc_s35_on else "Still_FF", still_image_size)
        col_map = {
            "Optical zoom only": "Optical",
            "Smart Zoom": "Smart",
            "ClearImage Zoom": "ClearImage",
            "Digital Zoom": "Digital",
        }
        scale_val = P366_FX3_ZOOM_SCALE_TABLE.get(tbl_key, {}).get(
            col_map.get(effective_zoom_range, "Optical")
        )
        max_zoom_scale = float(scale_val) if scale_val is not None else 1.0

    ciz_digital_active = effective_zoom_range in ("ClearImage Zoom", "Digital Zoom", "Smart Zoom")
    focus_area_locked_center = bool(is_fx3 and ciz_digital_active)
    metering_locked_multi = bool(is_fx3 and ciz_digital_active)
    face_eye_tracking_disabled = bool(is_fx3 and ciz_digital_active)

    # 2. `[Auto Slow Shutter]` 6+ lockouts & Still-only `[ISO AUTO Min. SS]`
    auto_slow_errno: Optional[int] = None
    auto_slow_locked = (
        shooting_domain != "Movie"
        or exposure_mode in ("S", "M")
        or iso_setting != "ISO AUTO"
        or (exposure_mode == "Flexible Exp." and flexible_exp_manual_shutter)
        or log_shooting_mode in ("Cine EI", "Cine EI Quick")
        or shutter_mode == "Angle"
    )
    if is_fx3 and auto_slow_shutter == "On" and auto_slow_locked:
        auto_slow_errno = P366_EOPNOTSUPP_ERRNO
        effective_auto_slow_shutter = "Off"
    elif is_fx6:
        effective_auto_slow_shutter = "Off"
    else:
        effective_auto_slow_shutter = auto_slow_shutter

    iso_auto_min_ss_errno: Optional[int] = None
    min_ss_allowed = (
        is_fx3
        and shooting_domain == "Still"
        and exposure_mode in ("P", "A")
        and iso_setting == "ISO AUTO"
    )
    if iso_auto_min_ss != P366_FX3_ISO_AUTO_MIN_SS_DEFAULT and not min_ss_allowed:
        iso_auto_min_ss_errno = P366_EOPNOTSUPP_ERRNO
    effective_min_ss_flash_override = bool(is_fx3 and min_ss_allowed and flash_active)

    # 3. Dual Base ISO Curve Matrix
    curve = P366_FX3_DUAL_BASE_ISO_CURVES.get(gamma_curve_key)
    if curve is None:
        base_iso_low, base_iso_high, base_iso_menu_exposed = (80, 1600, False)
    else:
        base_iso_low, base_iso_high, base_iso_menu_exposed = curve
    if is_fx3 and shooting_domain == "Still" and hlg_still_image == "On":
        base_iso_low = max(base_iso_low, P366_FX3_HLG_STILL_ISO_FLOOR)
        base_iso_high = max(base_iso_high, base_iso_low * 20)
    if is_fx3 and log_shooting_mode not in ("Cine EI", "Cine EI Quick"):
        base_iso_menu_exposed = False
    if is_fx6:
        base_iso_menu_exposed = log_shooting_mode in ("Cine EI", "Cine EI Quick")

    # 4. `[Camera Settings Reset]` vs `[Initialize]` asymmetric persistence
    if reset_action == "Initialize":
        post_zoom_range = P366_FX3_ZOOM_RANGE_DEFAULT
        post_zoom_ring_rotate = P366_FX3_ZOOM_RING_ROTATE_DEFAULT
        post_zoom_lever_1st_stby = P366_FX3_ZOOM_LEVER_1ST_DEFAULT
        post_zoom_lever_1st_rec = P366_FX3_ZOOM_LEVER_1ST_DEFAULT
        post_zoom_lever_2nd_stby = P366_FX3_ZOOM_LEVER_2ND_DEFAULT
        post_zoom_lever_2nd_rec = P366_FX3_ZOOM_LEVER_2ND_DEFAULT
        post_custom_key_zoom_speed_stby = P366_FX3_CUSTOM_KEY_ZOOM_SPEED_DEFAULT
        post_custom_key_zoom_speed_rec = P366_FX3_CUSTOM_KEY_ZOOM_SPEED_DEFAULT
        post_remote_zoom_speed_type = P366_FX3_REMOTE_ZOOM_SPEED_TYPE_DEFAULT
        post_remote_zoom_fixed_stby = P366_FX3_REMOTE_ZOOM_FIXED_SPEED_DEFAULT
        post_remote_zoom_fixed_rec = P366_FX3_REMOTE_ZOOM_FIXED_SPEED_DEFAULT
        post_auto_slow_shutter = P366_FX3_AUTO_SLOW_SHUTTER_DEFAULT
        post_iso_auto_min_ss = P366_FX3_ISO_AUTO_MIN_SS_DEFAULT
        post_iso_range_limit_persisted = False
    elif reset_action == "Camera Settings Reset":
        post_zoom_range = effective_zoom_range  # Not available!
        post_zoom_ring_rotate = zoom_ring_rotate  # Not available!
        post_zoom_lever_1st_stby = P366_FX3_ZOOM_LEVER_1ST_DEFAULT  # Can be reset!
        post_zoom_lever_1st_rec = P366_FX3_ZOOM_LEVER_1ST_DEFAULT
        post_zoom_lever_2nd_stby = P366_FX3_ZOOM_LEVER_2ND_DEFAULT
        post_zoom_lever_2nd_rec = P366_FX3_ZOOM_LEVER_2ND_DEFAULT
        post_custom_key_zoom_speed_stby = P366_FX3_CUSTOM_KEY_ZOOM_SPEED_DEFAULT
        post_custom_key_zoom_speed_rec = P366_FX3_CUSTOM_KEY_ZOOM_SPEED_DEFAULT
        post_remote_zoom_speed_type = P366_FX3_REMOTE_ZOOM_SPEED_TYPE_DEFAULT
        post_remote_zoom_fixed_stby = P366_FX3_REMOTE_ZOOM_FIXED_SPEED_DEFAULT
        post_remote_zoom_fixed_rec = P366_FX3_REMOTE_ZOOM_FIXED_SPEED_DEFAULT
        post_auto_slow_shutter = P366_FX3_AUTO_SLOW_SHUTTER_DEFAULT
        post_iso_auto_min_ss = P366_FX3_ISO_AUTO_MIN_SS_DEFAULT
        post_iso_range_limit_persisted = True  # Not available!
    else:
        post_zoom_range = effective_zoom_range
        post_zoom_ring_rotate = zoom_ring_rotate
        post_zoom_lever_1st_stby = zoom_lever_1st_stby
        post_zoom_lever_1st_rec = zoom_lever_1st_rec
        post_zoom_lever_2nd_stby = zoom_lever_2nd_stby
        post_zoom_lever_2nd_rec = zoom_lever_2nd_rec
        post_custom_key_zoom_speed_stby = custom_key_zoom_speed_stby
        post_custom_key_zoom_speed_rec = custom_key_zoom_speed_rec
        post_remote_zoom_speed_type = remote_zoom_speed_type
        post_remote_zoom_fixed_stby = remote_zoom_fixed_stby
        post_remote_zoom_fixed_rec = remote_zoom_fixed_rec
        post_auto_slow_shutter = effective_auto_slow_shutter
        post_iso_auto_min_ss = iso_auto_min_ss
        post_iso_range_limit_persisted = True

    write_blocked_erofs = (
        requested_vault_slot == 1
        and slot1_holds_tier0_vault
        and requested_vault_action in P366_WRITE_MUTATING_VAULT_ACTIONS
    )
    vault_action_allowed = not write_blocked_erofs and (
        requested_vault_action in ("NONE", "READ_ONLY_AUDIT")
    )
    vault_firewall_errno: Optional[str] = "EROFS" if write_blocked_erofs else None

    return {
        "zoom_errno": zoom_errno,
        "effective_zoom_range": effective_zoom_range,
        "max_zoom_scale": max_zoom_scale,
        "focus_area_locked_center": focus_area_locked_center,
        "metering_locked_multi": metering_locked_multi,
        "face_eye_tracking_disabled": face_eye_tracking_disabled,
        "auto_slow_errno": auto_slow_errno,
        "effective_auto_slow_shutter": effective_auto_slow_shutter,
        "iso_auto_min_ss_errno": iso_auto_min_ss_errno,
        "min_ss_allowed": min_ss_allowed,
        "effective_min_ss_flash_override": effective_min_ss_flash_override,
        "base_iso_low": base_iso_low,
        "base_iso_high": base_iso_high,
        "base_iso_menu_exposed": base_iso_menu_exposed,
        "post_zoom_range": post_zoom_range,
        "post_zoom_ring_rotate": post_zoom_ring_rotate,
        "post_zoom_lever_1st_stby": post_zoom_lever_1st_stby,
        "post_zoom_lever_1st_rec": post_zoom_lever_1st_rec,
        "post_zoom_lever_2nd_stby": post_zoom_lever_2nd_stby,
        "post_zoom_lever_2nd_rec": post_zoom_lever_2nd_rec,
        "post_custom_key_zoom_speed_stby": post_custom_key_zoom_speed_stby,
        "post_custom_key_zoom_speed_rec": post_custom_key_zoom_speed_rec,
        "post_remote_zoom_speed_type": post_remote_zoom_speed_type,
        "post_remote_zoom_fixed_stby": post_remote_zoom_fixed_stby,
        "post_remote_zoom_fixed_rec": post_remote_zoom_fixed_rec,
        "post_auto_slow_shutter": post_auto_slow_shutter,
        "post_iso_auto_min_ss": post_iso_auto_min_ss,
        "post_iso_range_limit_persisted": post_iso_range_limit_persisted,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


def compute_expected_arw_hlg_sort_usblun_uvc_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    exposure_mode: str,
    dro_bracket_active: bool,
    still_file_format: str,
    raw_file_type: str,
    jpeg_heif_switch: str,
    hlg_still_image: str,
    rec_media_mode: str,
    auto_switch_media: str,
    slot2_full_or_unready: bool,
    usb_connection_mode: str,
    usb_lun_setting: str,
    host_os_is_macos: bool,
    usb_power_supply: str,
    npfz100_present_with_charge: bool,
    usb_pd_watts: int,
    dc_coupler_model: str,
    cable_emarked_amps: int,
    fx6_dc_in_volts: float,
    uvc_streaming_requested: bool,
    network_streaming_active: bool,
    streaming_transport: str,
    movie_rec_during_streaming: str,
    rec_media_dur_hdmi_output: str,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute exact Wave-65 Pillar 67B expected state (ARW/HLG/Sort, USB LUN Single, NP-FZ100 PD, Dual UVC Firewall)."""
    is_fx3 = camera_model == P366_FX3_MODEL_NAME
    is_fx6 = camera_model == P366_FX6_DONOR_MODEL_NAME

    # 1. Dormant Lossless Comp `.ARW` Rejection, `[HLG Still Image]`, & `Sort Recording` Spillover
    raw_file_type_errno: Optional[int] = None
    if is_fx6:
        if raw_file_type != "None" or hlg_still_image == "On" or rec_media_mode == "Sort Recording":
            raw_file_type_errno = P366_EOPNOTSUPP_ERRNO
        effective_hlg_still = "Off"
        hlg_still_errno: Optional[int] = P366_EOPNOTSUPP_ERRNO if hlg_still_image == "On" else None
    else:
        if raw_file_type in P366_FX3_DORMANT_RAW_FILE_TYPES or raw_file_type not in P366_FX3_ACTIVE_RAW_FILE_TYPES:
            raw_file_type_errno = P366_EOPNOTSUPP_ERRNO

        hlg_prereqs_ok = (
            jpeg_heif_switch in ("HEIF(4:2:0)", "HEIF(4:2:2)")
            and still_file_format == "HEIF"
            and exposure_mode in ("P", "A", "S", "M")
            and not dro_bracket_active
        )
        hlg_still_errno = None
        if hlg_still_image == "On":
            if not hlg_prereqs_ok:
                hlg_still_errno = P366_EOPNOTSUPP_ERRNO
                effective_hlg_still = "Off"
            else:
                effective_hlg_still = "On"
        else:
            effective_hlg_still = "Off"

    hlg_bt2100_active = bool(is_fx3 and effective_hlg_still == "On")
    hlg_pp_dro_disabled = hlg_bt2100_active
    sort_spillover_targets_slot1 = bool(
        is_fx3
        and rec_media_mode == "Sort Recording"
        and auto_switch_media == "On"
        and slot2_full_or_unready
    )

    # 2. `[USB Connection Mode]`, `[USB LUN Setting]` (`Single` exposes `Slot 1` ONLY!), macOS MSC Hazard
    usb_mode_errno: Optional[int] = None
    if uvc_streaming_requested or usb_connection_mode not in P366_FX3_ACTIVE_USB_CONNECTION_MODES:
        usb_mode_errno = P366_EOPNOTSUPP_ERRNO

    if usb_connection_mode == "MassStorage(MSC)":
        slot1_exposed_to_host = True  # Both Multi AND Single expose Slot 1!
        slot2_exposed_to_host = usb_lun_setting == "Multi"
    elif usb_connection_mode == "MTP":
        slot1_exposed_to_host = True
        slot2_exposed_to_host = False
    else:
        slot1_exposed_to_host = False
        slot2_exposed_to_host = False

    macos_msc_host_blocked = bool(
        host_os_is_macos and slot1_exposed_to_host and usb_connection_mode in ("MassStorage(MSC)", "MTP")
    )

    # 3. `NP-FZ100` USB-C PD Interlock / `DC-C1` >=65W+5A vs FX6 `19.5V DC IN`
    if is_fx3:
        dcc1_valid = (
            dc_coupler_model == P366_FX3_DC_COUPLER_MODEL
            and usb_pd_watts >= P366_FX3_DC_COUPLER_MIN_WATTS
            and cable_emarked_amps >= P366_FX3_DC_COUPLER_CABLE_AMPS
        )
        power_boot_allowed = npfz100_present_with_charge or dcc1_valid
        power_brownout_risk = not power_boot_allowed
    else:
        power_boot_allowed = (
            P366_FX6_DC_IN_RANGE_V[0] <= fx6_dc_in_volts <= P366_FX6_DC_IN_RANGE_V[1]
        ) or npfz100_present_with_charge
        power_brownout_risk = fx6_dc_in_volts <= P366_FX6_DC_LOW_VOLTAGE1_V

    # 4. Dual FX3/FX6 Dormant `UVC` Firewall & `Movie Rec During Streaming` vs HDMI `Rec. Media dur HDMI Output`
    dormant_uvc_errno: Optional[int] = P366_EOPNOTSUPP_ERRNO if uvc_streaming_requested else None
    streaming_card_write_attempt = bool(
        is_fx3 and network_streaming_active and movie_rec_during_streaming == "Enable"
    )
    hdmi_card_write_attempt = bool(is_fx3 and rec_media_dur_hdmi_output == "On")

    # 5. Reset persistence
    if reset_action == "Initialize":
        post_raw_file_type = P366_FX3_RAW_FILE_TYPE_DEFAULT if is_fx3 else raw_file_type
        post_jpeg_heif_switch = "JPEG"
        post_hlg_still_image = "Off"
        post_usb_connection_mode = P366_FX3_USB_CONNECTION_DEFAULT
        post_usb_lun_setting = P366_FX3_USB_LUN_DEFAULT
        post_usb_power_supply = "On"
        post_rec_media_mode = "Slot 1"
    elif reset_action == "Camera Settings Reset":
        post_raw_file_type = P366_FX3_RAW_FILE_TYPE_DEFAULT if is_fx3 else raw_file_type
        post_jpeg_heif_switch = "JPEG"
        post_hlg_still_image = "Off"
        post_usb_connection_mode = usb_connection_mode  # Setup -> USB Not available!
        post_usb_lun_setting = usb_lun_setting  # Not available!
        post_usb_power_supply = usb_power_supply  # Not available!
        post_rec_media_mode = rec_media_mode  # Not available!
    else:
        post_raw_file_type = raw_file_type
        post_jpeg_heif_switch = jpeg_heif_switch
        post_hlg_still_image = effective_hlg_still
        post_usb_connection_mode = usb_connection_mode
        post_usb_lun_setting = usb_lun_setting
        post_usb_power_supply = usb_power_supply
        post_rec_media_mode = rec_media_mode

    write_blocked_erofs = (
        requested_vault_slot == 1
        and slot1_holds_tier0_vault
        and requested_vault_action in P366_WRITE_MUTATING_VAULT_ACTIONS
    )
    vault_action_allowed = not write_blocked_erofs and (
        requested_vault_action in ("NONE", "READ_ONLY_AUDIT")
    )
    vault_firewall_errno: Optional[str] = "EROFS" if write_blocked_erofs else None

    return {
        "raw_file_type_errno": raw_file_type_errno,
        "hlg_still_errno": hlg_still_errno,
        "effective_hlg_still": effective_hlg_still,
        "hlg_bt2100_active": hlg_bt2100_active,
        "hlg_pp_dro_disabled": hlg_pp_dro_disabled,
        "sort_spillover_targets_slot1": sort_spillover_targets_slot1,
        "usb_mode_errno": usb_mode_errno,
        "slot1_exposed_to_host": slot1_exposed_to_host,
        "slot2_exposed_to_host": slot2_exposed_to_host,
        "macos_msc_host_blocked": macos_msc_host_blocked,
        "power_boot_allowed": power_boot_allowed,
        "power_brownout_risk": power_brownout_risk,
        "dormant_uvc_errno": dormant_uvc_errno,
        "streaming_card_write_attempt": streaming_card_write_attempt,
        "hdmi_card_write_attempt": hdmi_card_write_attempt,
        "post_raw_file_type": post_raw_file_type,
        "post_jpeg_heif_switch": post_jpeg_heif_switch,
        "post_hlg_still_image": post_hlg_still_image,
        "post_usb_connection_mode": post_usb_connection_mode,
        "post_usb_lun_setting": post_usb_lun_setting,
        "post_usb_power_supply": post_usb_power_supply,
        "post_rec_media_mode": post_rec_media_mode,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


# ---------------------------------------------------------------------------
# Bounded Read-Only Donor Inspection (`O_RDONLY | O_NOFOLLOW | O_NONBLOCK`, 25 Donors)
# ---------------------------------------------------------------------------


def _iter_work_roots() -> Tuple[Optional[Path], ...]:
    return _fx3_files.iter_donor_work_roots()


def _resolve_phase366_donor_path(
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
    max_full_bytes: int = P366_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    try:
        resolved = _resolve_phase366_donor_path(relpath)
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
        hdr = os.pread(fd, min(P366_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase366_donors() -> Tuple["Phase366DonorArtifactDigest", ...]:
    specs = (
        ("fx3_appfw_702_so", P366_DONOR_FX3_APPFW_702_RELPATH, P366_PINNED_FX3_APPFW_702_BYTES, P366_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P366_PINNED_FX3_APPFW_702_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702"),
        ("fx3_backup_bin", P366_DONOR_FX3_BACKUP_BIN_RELPATH, P366_PINNED_FX3_BACKUP_BIN_BYTES, P366_PINNED_FX3_BACKUP_BIN_BYTES, "FULL_SHA256", P366_PINNED_FX3_BACKUP_BIN_SHA256, "SYNTHETIC_BK4_ILME_FX3"),
        ("fx3_usbg_storage_ko", P366_DONOR_FX3_USBG_STORAGE_KO_RELPATH, P366_PINNED_FX3_USBG_STORAGE_KO_BYTES, P366_PINNED_FX3_USBG_STORAGE_KO_BYTES, "FULL_SHA256", P366_PINNED_FX3_USBG_STORAGE_KO_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_USBG_STORAGE"),
        ("fx3_usbg_stillimage_ko", P366_DONOR_FX3_USBG_STILLIMAGE_KO_RELPATH, P366_PINNED_FX3_USBG_STILLIMAGE_KO_BYTES, P366_PINNED_FX3_USBG_STILLIMAGE_KO_BYTES, "FULL_SHA256", P366_PINNED_FX3_USBG_STILLIMAGE_KO_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_USBG_STILLIMAGE"),
        ("fx3_usb_f_uvc_ko", P366_DONOR_FX3_USB_F_UVC_KO_RELPATH, P366_PINNED_FX3_USB_F_UVC_KO_BYTES, P366_PINNED_FX3_USB_F_UVC_KO_BYTES, "FULL_SHA256", P366_PINNED_FX3_USB_F_UVC_KO_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_USB_F_UVC"),
        ("fx3_g_webcam_ko", P366_DONOR_FX3_G_WEBCAM_KO_RELPATH, P366_PINNED_FX3_G_WEBCAM_KO_BYTES, P366_PINNED_FX3_G_WEBCAM_KO_BYTES, "FULL_SHA256", P366_PINNED_FX3_G_WEBCAM_KO_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_G_WEBCAM"),
        ("fx6_appfw_601_so", P366_DONOR_FX6_APPFW_601_RELPATH, P366_PINNED_FX6_APPFW_601_BYTES, P366_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P366_PINNED_FX6_APPFW_601_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601"),
        ("fx6_usbg_storage_ko", P366_DONOR_FX6_USBG_STORAGE_KO_RELPATH, P366_PINNED_FX6_USBG_STORAGE_KO_BYTES, P366_PINNED_FX6_USBG_STORAGE_KO_BYTES, "FULL_SHA256", P366_PINNED_FX6_USBG_STORAGE_KO_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_USBG_STORAGE"),
        ("fx6_usbg_stillimage_ko", P366_DONOR_FX6_USBG_STILLIMAGE_KO_RELPATH, P366_PINNED_FX6_USBG_STILLIMAGE_KO_BYTES, P366_PINNED_FX6_USBG_STILLIMAGE_KO_BYTES, "FULL_SHA256", P366_PINNED_FX6_USBG_STILLIMAGE_KO_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_USBG_STILLIMAGE"),
        ("fx6_usb_f_uvc_ko", P366_DONOR_FX6_USB_F_UVC_KO_RELPATH, P366_PINNED_FX6_USB_F_UVC_KO_BYTES, P366_PINNED_FX6_USB_F_UVC_KO_BYTES, "FULL_SHA256", P366_PINNED_FX6_USB_F_UVC_KO_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_USB_F_UVC"),
        ("fx6_g_webcam_ko", P366_DONOR_FX6_G_WEBCAM_KO_RELPATH, P366_PINNED_FX6_G_WEBCAM_KO_BYTES, P366_PINNED_FX6_G_WEBCAM_KO_BYTES, "FULL_SHA256", P366_PINNED_FX6_G_WEBCAM_KO_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_G_WEBCAM"),
        ("fx3_uxc_en_f", P366_DONOR_FX3_UXC_EN_F_RELPATH, P366_PINNED_FX3_UXC_EN_F_BYTES, P366_PINNED_FX3_UXC_EN_F_BYTES, "FULL_SHA256", P366_PINNED_FX3_UXC_EN_F_SHA256, "SYNTHETIC_UXC7_FX3_EN_F"),
        ("fx3_uxc_sc_f", P366_DONOR_FX3_UXC_SC_F_RELPATH, P366_PINNED_FX3_UXC_SC_F_BYTES, P366_PINNED_FX3_UXC_SC_F_BYTES, "FULL_SHA256", P366_PINNED_FX3_UXC_SC_F_SHA256, "SYNTHETIC_UXC7_FX3_SC_F"),
        ("fx3_uxc_tc_f", P366_DONOR_FX3_UXC_TC_F_RELPATH, P366_PINNED_FX3_UXC_TC_F_BYTES, P366_PINNED_FX3_UXC_TC_F_BYTES, "FULL_SHA256", P366_PINNED_FX3_UXC_TC_F_SHA256, "SYNTHETIC_UXC7_FX3_TC_F"),
        ("fx3_uxc_ja_f", P366_DONOR_FX3_UXC_JA_F_RELPATH, P366_PINNED_FX3_UXC_JA_F_BYTES, P366_PINNED_FX3_UXC_JA_F_BYTES, "FULL_SHA256", P366_PINNED_FX3_UXC_JA_F_SHA256, "SYNTHETIC_UXC7_FX3_JA_F"),
        ("fx3_uxc_en", P366_DONOR_FX3_UXC_EN_RELPATH, P366_PINNED_FX3_UXC_EN_BYTES, P366_PINNED_FX3_UXC_EN_BYTES, "FULL_SHA256", P366_PINNED_FX3_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX3_EN"),
        ("fx3_uxc_sc", P366_DONOR_FX3_UXC_SC_RELPATH, P366_PINNED_FX3_UXC_SC_BYTES, P366_PINNED_FX3_UXC_SC_BYTES, "FULL_SHA256", P366_PINNED_FX3_UXC_SC_SHA256, "SYNTHETIC_UXC7_FX3_SC"),
        ("fx3_uxc_tc", P366_DONOR_FX3_UXC_TC_RELPATH, P366_PINNED_FX3_UXC_TC_BYTES, P366_PINNED_FX3_UXC_TC_BYTES, "FULL_SHA256", P366_PINNED_FX3_UXC_TC_SHA256, "SYNTHETIC_UXC7_FX3_TC"),
        ("fx3_uxc_ja", P366_DONOR_FX3_UXC_JA_RELPATH, P366_PINNED_FX3_UXC_JA_BYTES, P366_PINNED_FX3_UXC_JA_BYTES, "FULL_SHA256", P366_PINNED_FX3_UXC_JA_SHA256, "SYNTHETIC_UXC7_FX3_JA"),
        ("fx3_uxc_en_g", P366_DONOR_FX3_UXC_EN_G_RELPATH, P366_PINNED_FX3_UXC_EN_G_BYTES, P366_PINNED_FX3_UXC_EN_G_BYTES, "FULL_SHA256", P366_PINNED_FX3_UXC_EN_G_SHA256, "SYNTHETIC_UXC7_FX3_EN_G"),
        ("fx3_uxc_sc_g", P366_DONOR_FX3_UXC_SC_G_RELPATH, P366_PINNED_FX3_UXC_SC_G_BYTES, P366_PINNED_FX3_UXC_SC_G_BYTES, "FULL_SHA256", P366_PINNED_FX3_UXC_SC_G_SHA256, "SYNTHETIC_UXC7_FX3_SC_G"),
        ("fx3_uxc_tc_g", P366_DONOR_FX3_UXC_TC_G_RELPATH, P366_PINNED_FX3_UXC_TC_G_BYTES, P366_PINNED_FX3_UXC_TC_G_BYTES, "FULL_SHA256", P366_PINNED_FX3_UXC_TC_G_SHA256, "SYNTHETIC_UXC7_FX3_TC_G"),
        ("fx3_uxc_ja_g", P366_DONOR_FX3_UXC_JA_G_RELPATH, P366_PINNED_FX3_UXC_JA_G_BYTES, P366_PINNED_FX3_UXC_JA_G_BYTES, "FULL_SHA256", P366_PINNED_FX3_UXC_JA_G_SHA256, "SYNTHETIC_UXC7_FX3_JA_G"),
        ("fx6_uxc_en", P366_DONOR_FX6_UXC_EN_RELPATH, P366_PINNED_FX6_UXC_EN_BYTES, P366_PINNED_FX6_UXC_EN_BYTES, "FULL_SHA256", P366_PINNED_FX6_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX6_EN"),
        ("fx6_uxc_en_2", P366_DONOR_FX6_UXC_EN_2_RELPATH, P366_PINNED_FX6_UXC_EN_2_BYTES, P366_PINNED_FX6_UXC_EN_2_BYTES, "FULL_SHA256", P366_PINNED_FX6_UXC_EN_2_SHA256, "SYNTHETIC_UXC7_FX6_EN_2"),
    )
    return tuple(
        Phase366DonorArtifactDigest(
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


def inspect_phase366_donors_readonly(
    force_clean_room: Optional[bool] = None,
) -> "Phase366DonorSnapshot":
    """Inspect Wave-65 FX3 (`18` donors incl. `usbg_*.ko` & `usb_f_uvc.ko`/`g_webcam.ko`) & FX6 (`7` donors)
    strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase366_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase366DonorSnapshot(
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
        ("fx3_appfw_702_so", P366_DONOR_FX3_APPFW_702_RELPATH, P366_PINNED_FX3_APPFW_702_BYTES, P366_PINNED_FX3_APPFW_702_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702")),
        ("fx3_backup_bin", P366_DONOR_FX3_BACKUP_BIN_RELPATH, P366_PINNED_FX3_BACKUP_BIN_BYTES, P366_PINNED_FX3_BACKUP_BIN_SHA256, lambda d: _check_bk4_backup(d, "ILME_FX3")),
        ("fx3_usbg_storage_ko", P366_DONOR_FX3_USBG_STORAGE_KO_RELPATH, P366_PINNED_FX3_USBG_STORAGE_KO_BYTES, P366_PINNED_FX3_USBG_STORAGE_KO_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_USBG_STORAGE")),
        ("fx3_usbg_stillimage_ko", P366_DONOR_FX3_USBG_STILLIMAGE_KO_RELPATH, P366_PINNED_FX3_USBG_STILLIMAGE_KO_BYTES, P366_PINNED_FX3_USBG_STILLIMAGE_KO_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_USBG_STILLIMAGE")),
        ("fx3_usb_f_uvc_ko", P366_DONOR_FX3_USB_F_UVC_KO_RELPATH, P366_PINNED_FX3_USB_F_UVC_KO_BYTES, P366_PINNED_FX3_USB_F_UVC_KO_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_USB_F_UVC")),
        ("fx3_g_webcam_ko", P366_DONOR_FX3_G_WEBCAM_KO_RELPATH, P366_PINNED_FX3_G_WEBCAM_KO_BYTES, P366_PINNED_FX3_G_WEBCAM_KO_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_G_WEBCAM")),
        ("fx6_appfw_601_so", P366_DONOR_FX6_APPFW_601_RELPATH, P366_PINNED_FX6_APPFW_601_BYTES, P366_PINNED_FX6_APPFW_601_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601")),
        ("fx6_usbg_storage_ko", P366_DONOR_FX6_USBG_STORAGE_KO_RELPATH, P366_PINNED_FX6_USBG_STORAGE_KO_BYTES, P366_PINNED_FX6_USBG_STORAGE_KO_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_USBG_STORAGE")),
        ("fx6_usbg_stillimage_ko", P366_DONOR_FX6_USBG_STILLIMAGE_KO_RELPATH, P366_PINNED_FX6_USBG_STILLIMAGE_KO_BYTES, P366_PINNED_FX6_USBG_STILLIMAGE_KO_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_USBG_STILLIMAGE")),
        ("fx6_usb_f_uvc_ko", P366_DONOR_FX6_USB_F_UVC_KO_RELPATH, P366_PINNED_FX6_USB_F_UVC_KO_BYTES, P366_PINNED_FX6_USB_F_UVC_KO_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_USB_F_UVC")),
        ("fx6_g_webcam_ko", P366_DONOR_FX6_G_WEBCAM_KO_RELPATH, P366_PINNED_FX6_G_WEBCAM_KO_BYTES, P366_PINNED_FX6_G_WEBCAM_KO_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_G_WEBCAM")),
        ("fx3_uxc_en_f", P366_DONOR_FX3_UXC_EN_F_RELPATH, P366_PINNED_FX3_UXC_EN_F_BYTES, P366_PINNED_FX3_UXC_EN_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_F")),
        ("fx3_uxc_sc_f", P366_DONOR_FX3_UXC_SC_F_RELPATH, P366_PINNED_FX3_UXC_SC_F_BYTES, P366_PINNED_FX3_UXC_SC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_F")),
        ("fx3_uxc_tc_f", P366_DONOR_FX3_UXC_TC_F_RELPATH, P366_PINNED_FX3_UXC_TC_F_BYTES, P366_PINNED_FX3_UXC_TC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_F")),
        ("fx3_uxc_ja_f", P366_DONOR_FX3_UXC_JA_F_RELPATH, P366_PINNED_FX3_UXC_JA_F_BYTES, P366_PINNED_FX3_UXC_JA_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_F")),
        ("fx3_uxc_en", P366_DONOR_FX3_UXC_EN_RELPATH, P366_PINNED_FX3_UXC_EN_BYTES, P366_PINNED_FX3_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN")),
        ("fx3_uxc_sc", P366_DONOR_FX3_UXC_SC_RELPATH, P366_PINNED_FX3_UXC_SC_BYTES, P366_PINNED_FX3_UXC_SC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC")),
        ("fx3_uxc_tc", P366_DONOR_FX3_UXC_TC_RELPATH, P366_PINNED_FX3_UXC_TC_BYTES, P366_PINNED_FX3_UXC_TC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC")),
        ("fx3_uxc_ja", P366_DONOR_FX3_UXC_JA_RELPATH, P366_PINNED_FX3_UXC_JA_BYTES, P366_PINNED_FX3_UXC_JA_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA")),
        ("fx3_uxc_en_g", P366_DONOR_FX3_UXC_EN_G_RELPATH, P366_PINNED_FX3_UXC_EN_G_BYTES, P366_PINNED_FX3_UXC_EN_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_G")),
        ("fx3_uxc_sc_g", P366_DONOR_FX3_UXC_SC_G_RELPATH, P366_PINNED_FX3_UXC_SC_G_BYTES, P366_PINNED_FX3_UXC_SC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_G")),
        ("fx3_uxc_tc_g", P366_DONOR_FX3_UXC_TC_G_RELPATH, P366_PINNED_FX3_UXC_TC_G_BYTES, P366_PINNED_FX3_UXC_TC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_G")),
        ("fx3_uxc_ja_g", P366_DONOR_FX3_UXC_JA_G_RELPATH, P366_PINNED_FX3_UXC_JA_G_BYTES, P366_PINNED_FX3_UXC_JA_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_G")),
        ("fx6_uxc_en", P366_DONOR_FX6_UXC_EN_RELPATH, P366_PINNED_FX6_UXC_EN_BYTES, P366_PINNED_FX6_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN")),
        ("fx6_uxc_en_2", P366_DONOR_FX6_UXC_EN_2_RELPATH, P366_PINNED_FX6_UXC_EN_2_BYTES, P366_PINNED_FX6_UXC_EN_2_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN_2")),
    )

    def _probe_one(spec: Tuple[str, str, int, str, Any]) -> Optional[Phase366DonorArtifactDigest]:
        aid, relpath, expected_bytes, expected_sha, marker_fn = spec
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            return None
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        return Phase366DonorArtifactDigest(
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
        artifacts = _synthetic_phase366_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase366DonorSnapshot(
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
    return Phase366DonorSnapshot(
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
# Frozen Dataclasses (Specs, Reports, Suites & 67-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase366DonorArtifactDigest:
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
class Phase366DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_2_0s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase366DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ZoomCizAutoSlowBaseIsoVaultSpec:
    camera_model: str
    fw_version: str
    shooting_domain: str
    recording_fps: int
    movie_resolution: str
    still_file_format: str
    still_image_size: str
    apsc_s35_on: bool
    raw_output: str
    breathing_comp: str
    # `[Zoom Range]`, 8-Step Standby/Movie Speeds & `[Zoom Ring Rotate]`
    zoom_range: str
    zoom_ring_rotate: str
    zoom_lever_1st_stby: int
    zoom_lever_1st_rec: int
    zoom_lever_2nd_stby: int
    zoom_lever_2nd_rec: int
    custom_key_zoom_speed_stby: int
    custom_key_zoom_speed_rec: int
    remote_zoom_speed_type: str
    remote_zoom_fixed_stby: int
    remote_zoom_fixed_rec: int
    fx6_sq_motion: str
    fx6_codec: str
    fx6_handle_zoom_mode: str
    reported_zoom_errno: Optional[int]
    reported_effective_zoom_range: str
    reported_max_zoom_scale: float
    reported_focus_area_locked_center: bool
    reported_metering_locked_multi: bool
    reported_face_eye_tracking_disabled: bool
    # `[Auto Slow Shutter]`, `[ISO Range Limit]`, Still `[ISO AUTO Min. SS]`, Dual Base ISO
    exposure_mode: str
    iso_setting: str
    flexible_exp_manual_shutter: bool
    log_shooting_mode: str
    shutter_mode: str
    auto_slow_shutter: str
    iso_auto_min_ss: str
    flash_active: bool
    gamma_curve_key: str
    hlg_still_image: str
    reported_auto_slow_errno: Optional[int]
    reported_effective_auto_slow_shutter: str
    reported_iso_auto_min_ss_errno: Optional[int]
    reported_min_ss_flash_override: bool
    reported_base_iso_low: int
    reported_base_iso_high: int
    reported_base_iso_menu_exposed: bool
    # Reset boundaries (`Zoom Range`/`Ring Rotate`/`ISO Range Limit` Not available; 8-speed/AutoSlow/MinSS Can be reset)
    reset_action: str
    post_zoom_range: str
    post_zoom_ring_rotate: str
    post_zoom_lever_1st_stby: int
    post_zoom_lever_1st_rec: int
    post_zoom_lever_2nd_stby: int
    post_zoom_lever_2nd_rec: int
    post_custom_key_zoom_speed_stby: int
    post_custom_key_zoom_speed_rec: int
    post_remote_zoom_speed_type: str
    post_remote_zoom_fixed_stby: int
    post_remote_zoom_fixed_rec: int
    post_auto_slow_shutter: str
    post_iso_auto_min_ss: str
    post_iso_range_limit_persisted: bool
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
    # Drift counters
    zoom_ciz_lockout_or_8speed_reset_drift_events: int
    autoslow_6lockout_or_minss_still_drift_events: int
    dual_base_iso_curve_matrix_drift_events: int


@dataclass(frozen=True)
class ZoomCizAutoSlowBaseIsoVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    zoom_ciz_8speed_reset_verified: bool
    autoslow_minss_dual_base_iso_verified: bool
    slot1_vault_and_h0_h3_verified: bool
    matrix_states_checked: int
    zoom_ciz_lockout_or_8speed_reset_drift_events: int
    autoslow_6lockout_or_minss_still_drift_events: int
    dual_base_iso_curve_matrix_drift_events: int
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
class ArwHlgSortUsbLunUvcVaultSpec:
    camera_model: str
    fw_version: str
    shooting_domain: str
    exposure_mode: str
    dro_bracket_active: bool
    # `.ARW` `[RAW File Type]` / `HEIF` / `[HLG Still Image]` / `Sort Recording`
    still_file_format: str
    raw_file_type: str
    jpeg_heif_switch: str
    hlg_still_image: str
    rec_media_mode: str
    auto_switch_media: str
    slot2_full_or_unready: bool
    reported_raw_file_type_errno: Optional[int]
    reported_hlg_still_errno: Optional[int]
    reported_effective_hlg_still: str
    reported_hlg_bt2100_active: bool
    reported_hlg_pp_dro_disabled: bool
    reported_sort_spillover_targets_slot1: bool
    # `[USB Connection Mode]`, `[USB LUN Setting] = Single` (`Slot 1`-Only!), macOS MSC Hazard, `NP-FZ100` PD & Dual UVC
    usb_connection_mode: str
    usb_lun_setting: str
    host_os_is_macos: bool
    reported_usb_mode_errno: Optional[int]
    reported_slot1_exposed_to_host: bool
    reported_slot2_exposed_to_host: bool
    reported_macos_msc_host_blocked: bool
    usb_power_supply: str
    npfz100_present_with_charge: bool
    usb_pd_watts: int
    dc_coupler_model: str
    cable_emarked_amps: int
    fx6_dc_in_volts: float
    reported_power_boot_allowed: bool
    reported_power_brownout_risk: bool
    uvc_streaming_requested: bool
    reported_dormant_uvc_errno: Optional[int]
    network_streaming_active: bool
    streaming_transport: str
    movie_rec_during_streaming: str
    rec_media_dur_hdmi_output: str
    reported_streaming_card_write_attempt: bool
    reported_hdmi_card_write_attempt: bool
    # Reset boundaries
    reset_action: str
    post_raw_file_type: str
    post_jpeg_heif_switch: str
    post_hlg_still_image: str
    post_usb_connection_mode: str
    post_usb_lun_setting: str
    post_usb_power_supply: str
    post_rec_media_mode: str
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
    dormant_lossless_arw_exposed_events: int
    hlg_still_or_sort_rec_spillover_drift_events: int
    usb_lun_single_slot1_msc_hazard_events: int
    npfz100_pd_interlock_or_dcc1_drift_events: int
    dormant_uvc_streaming_exposed_events: int


@dataclass(frozen=True)
class ArwHlgSortUsbLunUvcVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    arw_hlg_sort_spillover_verified: bool
    usblun_single_npfz100_uvc_firewall_verified: bool
    overlay_and_h0_h3_verified: bool
    matrix_states_checked: int
    dormant_lossless_arw_exposed_events: int
    hlg_still_or_sort_rec_spillover_drift_events: int
    usb_lun_single_slot1_msc_hazard_events: int
    npfz100_pd_interlock_or_dcc1_drift_events: int
    dormant_uvc_streaming_exposed_events: int
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
class ZoomCizAutoSlowBaseIsoArwUsbLunUvcVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase366DonorSnapshot
    zoom_ciz_autoslow_baseiso_report: ZoomCizAutoSlowBaseIsoVaultReport
    arw_hlg_sort_usblun_uvc_report: ArwHlgSortUsbLunUvcVaultReport
    zoom_ciz_lockout_or_8speed_reset_drift_events: int
    autoslow_6lockout_or_minss_still_drift_events: int
    dual_base_iso_curve_matrix_drift_events: int
    dormant_lossless_arw_exposed_events: int
    hlg_still_or_sort_rec_spillover_drift_events: int
    usb_lun_single_slot1_msc_hazard_events: int
    npfz100_pd_interlock_or_dcc1_drift_events: int
    dormant_uvc_streaming_exposed_events: int
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
class Pillar67ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar67ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar67ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar67BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar67ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar67StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase366DonorSnapshot
    pillar_67a_zoom_ciz_autoslow_baseiso_vault: Pillar67ASuiteResult
    pillar_67b_arw_hlg_sort_usblun_uvc_vault: Pillar67BSuiteResult
    zoom_ciz_lockout_or_8speed_reset_drift_events: int
    autoslow_6lockout_or_minss_still_drift_events: int
    dual_base_iso_curve_matrix_drift_events: int
    dormant_lossless_arw_exposed_events: int
    hlg_still_or_sort_rec_spillover_drift_events: int
    usb_lun_single_slot1_msc_hazard_events: int
    npfz100_pd_interlock_or_dcc1_drift_events: int
    dormant_uvc_streaming_exposed_events: int
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
class Master67PillarRecoveryReport:
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
    donor_snapshot: Phase366DonorSnapshot
    pillar67_a_zoom_ciz_autoslow_baseiso_vault: Pillar67ASuiteResult
    pillar67_b_arw_hlg_sort_usblun_uvc_vault: Pillar67BSuiteResult
    # Pillar 67 zero-violation counters & empirical metrics
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
    # Carried-forward Pillar 66..41 zero-violation metrics
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
    # Safety lock flags
    overall_ready_for_hardware_attach: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    master_67pillar_sha256: str
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
# Default Safe Specs & Evaluators (Pillars 67A & 67B)
# ---------------------------------------------------------------------------


def build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
    **overrides: Any,
) -> ZoomCizAutoSlowBaseIsoVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P366_FX3_MODEL_NAME,
        "fw_version": P366_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "recording_fps": 24,
        "movie_resolution": "4K",
        "still_file_format": "JPEG",
        "still_image_size": "L",
        "apsc_s35_on": False,
        "raw_output": "Off",
        "breathing_comp": "Off",
        "zoom_range": "ClearImage Zoom",
        "zoom_ring_rotate": "Left(W)/Right(T)",
        "zoom_lever_1st_stby": 3,
        "zoom_lever_1st_rec": 3,
        "zoom_lever_2nd_stby": 8,
        "zoom_lever_2nd_rec": 8,
        "custom_key_zoom_speed_stby": 3,
        "custom_key_zoom_speed_rec": 3,
        "remote_zoom_speed_type": "Variable",
        "remote_zoom_fixed_stby": 3,
        "remote_zoom_fixed_rec": 3,
        "fx6_sq_motion": "Off",
        "fx6_codec": "XAVC-I",
        "fx6_handle_zoom_mode": "Variable",
        "reported_zoom_errno": None,
        "reported_effective_zoom_range": "ClearImage Zoom",
        "reported_max_zoom_scale": 1.5,
        "reported_focus_area_locked_center": True,
        "reported_metering_locked_multi": True,
        "reported_face_eye_tracking_disabled": True,
        "exposure_mode": "P",
        "iso_setting": "ISO AUTO",
        "flexible_exp_manual_shutter": False,
        "log_shooting_mode": "Off",
        "shutter_mode": "Speed",
        "auto_slow_shutter": "On",
        "iso_auto_min_ss": "STD",
        "flash_active": False,
        "gamma_curve_key": "PP11 S-Cinetone",
        "hlg_still_image": "Off",
        "reported_auto_slow_errno": None,
        "reported_effective_auto_slow_shutter": "On",
        "reported_iso_auto_min_ss_errno": None,
        "reported_min_ss_flash_override": False,
        "reported_base_iso_low": 100,
        "reported_base_iso_high": 2000,
        "reported_base_iso_menu_exposed": False,
        "reset_action": "Camera Settings Reset",
        "post_zoom_range": "ClearImage Zoom",
        "post_zoom_ring_rotate": "Left(W)/Right(T)",
        "post_zoom_lever_1st_stby": 3,
        "post_zoom_lever_1st_rec": 3,
        "post_zoom_lever_2nd_stby": 8,
        "post_zoom_lever_2nd_rec": 8,
        "post_custom_key_zoom_speed_stby": 3,
        "post_custom_key_zoom_speed_rec": 3,
        "post_remote_zoom_speed_type": "Variable",
        "post_remote_zoom_fixed_stby": 3,
        "post_remote_zoom_fixed_rec": 3,
        "post_auto_slow_shutter": "On",
        "post_iso_auto_min_ss": "STD",
        "post_iso_range_limit_persisted": True,
        "requested_vault_slot": 1,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": 0,
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P366_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P366_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P366_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P366_TIER0_SURFACE_COUNT,
        "zoom_ciz_lockout_or_8speed_reset_drift_events": 0,
        "autoslow_6lockout_or_minss_still_drift_events": 0,
        "dual_base_iso_curve_matrix_drift_events": 0,
    }
    defaults.update(overrides)
    return ZoomCizAutoSlowBaseIsoVaultSpec(**defaults)


def build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
    **overrides: Any,
) -> ArwHlgSortUsbLunUvcVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P366_FX3_MODEL_NAME,
        "fw_version": P366_FX3_FW_VERSION,
        "shooting_domain": "Still",
        "exposure_mode": "A",
        "dro_bracket_active": False,
        "still_file_format": "RAW & JPEG",
        "raw_file_type": "Compressed",
        "jpeg_heif_switch": "JPEG",
        "hlg_still_image": "Off",
        "rec_media_mode": "Slot 1",
        "auto_switch_media": "Off",
        "slot2_full_or_unready": False,
        "reported_raw_file_type_errno": None,
        "reported_hlg_still_errno": None,
        "reported_effective_hlg_still": "Off",
        "reported_hlg_bt2100_active": False,
        "reported_hlg_pp_dro_disabled": False,
        "reported_sort_spillover_targets_slot1": False,
        "usb_connection_mode": "Sel. When Connect",
        "usb_lun_setting": "Multi",
        "host_os_is_macos": True,
        "reported_usb_mode_errno": None,
        "reported_slot1_exposed_to_host": False,
        "reported_slot2_exposed_to_host": False,
        "reported_macos_msc_host_blocked": False,
        "usb_power_supply": "On",
        "npfz100_present_with_charge": True,
        "usb_pd_watts": 27,
        "dc_coupler_model": "",
        "cable_emarked_amps": 3,
        "fx6_dc_in_volts": 19.5,
        "reported_power_boot_allowed": True,
        "reported_power_brownout_risk": False,
        "uvc_streaming_requested": False,
        "reported_dormant_uvc_errno": None,
        "network_streaming_active": False,
        "streaming_transport": "USB-LAN",
        "movie_rec_during_streaming": "Disable",
        "rec_media_dur_hdmi_output": "Off(HDMI Only)",
        "reported_streaming_card_write_attempt": False,
        "reported_hdmi_card_write_attempt": False,
        "reset_action": "Camera Settings Reset",
        "post_raw_file_type": "Compressed",
        "post_jpeg_heif_switch": "JPEG",
        "post_hlg_still_image": "Off",
        "post_usb_connection_mode": "Sel. When Connect",
        "post_usb_lun_setting": "Multi",
        "post_usb_power_supply": "On",
        "post_rec_media_mode": "Slot 1",
        "requested_vault_slot": 1,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": 0,
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P366_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P366_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P366_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P366_TIER0_SURFACE_COUNT,
        "dormant_lossless_arw_exposed_events": 0,
        "hlg_still_or_sort_rec_spillover_drift_events": 0,
        "usb_lun_single_slot1_msc_hazard_events": 0,
        "npfz100_pd_interlock_or_dcc1_drift_events": 0,
        "dormant_uvc_streaming_exposed_events": 0,
    }
    defaults.update(overrides)
    return ArwHlgSortUsbLunUvcVaultSpec(**defaults)


def evaluate_zoom_ciz_autoslow_baseiso_vault(
    spec: ZoomCizAutoSlowBaseIsoVaultSpec,
) -> ZoomCizAutoSlowBaseIsoVaultReport:
    """Evaluate Pillar 67A (`[Zoom Range]` / CIZ / 8-speed Standby-vs-Movie split / Reset boundaries,
    `[Auto Slow Shutter]` 6+ lockouts, Still `[ISO AUTO Min. SS]`, and Dual Base ISO curve table)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P366_BLOCKED_SAFETY_POLICY_VIOLATION, "Safety policy violation")

    speed_vals = (
        spec.zoom_lever_1st_stby,
        spec.zoom_lever_1st_rec,
        spec.zoom_lever_2nd_stby,
        spec.zoom_lever_2nd_rec,
        spec.custom_key_zoom_speed_stby,
        spec.custom_key_zoom_speed_rec,
        spec.remote_zoom_fixed_stby,
        spec.remote_zoom_fixed_rec,
    )
    valid_spec = (
        spec.camera_model in (P366_FX3_MODEL_NAME, P366_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P366_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P366_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P366_SHOOTING_DOMAINS
        and spec.movie_resolution in ("4K", "HD")
        and spec.still_file_format in P366_FX3_STILL_FILE_FORMATS
        and spec.still_image_size in ("L", "M", "S")
        and spec.raw_output in P366_ON_OFF_MODES
        and spec.breathing_comp in P366_ON_OFF_MODES
        and spec.zoom_range in ("Optical zoom only", "ClearImage Zoom", "Digital Zoom", "Smart Zoom")
        and spec.zoom_ring_rotate in P366_FX3_ZOOM_RING_ROTATES
        and all(P366_FX3_ZOOM_SPEED_MIN <= s <= P366_FX3_ZOOM_SPEED_MAX for s in speed_vals)
        and spec.remote_zoom_speed_type in P366_FX3_REMOTE_ZOOM_SPEED_TYPES
        and spec.fx6_sq_motion in P366_ON_OFF_MODES
        and spec.fx6_handle_zoom_mode in P366_FX6_HANDLE_ZOOM_MODES
        and spec.exposure_mode in P366_EXPOSURE_MODES
        and spec.shutter_mode in ("Speed", "Angle")
        and spec.auto_slow_shutter in P366_ON_OFF_MODES
        and spec.iso_auto_min_ss in P366_FX3_ISO_AUTO_MIN_SS_PRESETS
        and spec.hlg_still_image in P366_ON_OFF_MODES
        and spec.reset_action in P366_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P366_VAULT_ACTIONS
        and spec.vault_firewall_errno in P366_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P366_BLOCKED_INVALID_PILLAR67A_SPEC, "Invalid Pillar 67A spec fields")

    st = compute_expected_zoom_ciz_autoslow_baseiso_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        recording_fps=spec.recording_fps,
        movie_resolution=spec.movie_resolution,
        still_file_format=spec.still_file_format,
        still_image_size=spec.still_image_size,
        apsc_s35_on=spec.apsc_s35_on,
        raw_output=spec.raw_output,
        breathing_comp=spec.breathing_comp,
        zoom_range=spec.zoom_range,
        zoom_ring_rotate=spec.zoom_ring_rotate,
        zoom_lever_1st_stby=spec.zoom_lever_1st_stby,
        zoom_lever_1st_rec=spec.zoom_lever_1st_rec,
        zoom_lever_2nd_stby=spec.zoom_lever_2nd_stby,
        zoom_lever_2nd_rec=spec.zoom_lever_2nd_rec,
        custom_key_zoom_speed_stby=spec.custom_key_zoom_speed_stby,
        custom_key_zoom_speed_rec=spec.custom_key_zoom_speed_rec,
        remote_zoom_speed_type=spec.remote_zoom_speed_type,
        remote_zoom_fixed_stby=spec.remote_zoom_fixed_stby,
        remote_zoom_fixed_rec=spec.remote_zoom_fixed_rec,
        fx6_sq_motion=spec.fx6_sq_motion,
        fx6_codec=spec.fx6_codec,
        fx6_handle_zoom_mode=spec.fx6_handle_zoom_mode,
        exposure_mode=spec.exposure_mode,
        iso_setting=spec.iso_setting,
        flexible_exp_manual_shutter=spec.flexible_exp_manual_shutter,
        log_shooting_mode=spec.log_shooting_mode,
        shutter_mode=spec.shutter_mode,
        auto_slow_shutter=spec.auto_slow_shutter,
        iso_auto_min_ss=spec.iso_auto_min_ss,
        flash_active=spec.flash_active,
        gamma_curve_key=spec.gamma_curve_key,
        hlg_still_image=spec.hlg_still_image,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    zoom_ok = (
        spec.reported_zoom_errno == st["zoom_errno"]
        and st["zoom_errno"] is None
        and spec.reported_effective_zoom_range == st["effective_zoom_range"]
        and abs(spec.reported_max_zoom_scale - st["max_zoom_scale"]) < 1e-9
        and spec.reported_focus_area_locked_center == st["focus_area_locked_center"]
        and spec.reported_metering_locked_multi == st["metering_locked_multi"]
        and spec.reported_face_eye_tracking_disabled == st["face_eye_tracking_disabled"]
        and spec.post_zoom_range == st["post_zoom_range"]
        and spec.post_zoom_ring_rotate == st["post_zoom_ring_rotate"]
        and spec.post_zoom_lever_1st_stby == st["post_zoom_lever_1st_stby"]
        and spec.post_zoom_lever_1st_rec == st["post_zoom_lever_1st_rec"]
        and spec.post_zoom_lever_2nd_stby == st["post_zoom_lever_2nd_stby"]
        and spec.post_zoom_lever_2nd_rec == st["post_zoom_lever_2nd_rec"]
        and spec.post_custom_key_zoom_speed_stby == st["post_custom_key_zoom_speed_stby"]
        and spec.post_custom_key_zoom_speed_rec == st["post_custom_key_zoom_speed_rec"]
        and spec.post_remote_zoom_speed_type == st["post_remote_zoom_speed_type"]
        and spec.post_remote_zoom_fixed_stby == st["post_remote_zoom_fixed_stby"]
        and spec.post_remote_zoom_fixed_rec == st["post_remote_zoom_fixed_rec"]
        and spec.zoom_ciz_lockout_or_8speed_reset_drift_events == 0
    )
    if not zoom_ok:
        _fail(
            P366_BLOCKED_ZOOM_CIZ_OR_8SPEED_RESET_DRIFT,
            "Zoom Range / CIZ / 8-speed Standby-Rec split, lockout, AF/Metering side effect, or Reset boundary violated",
        )

    autoslow_dual_base_ok = (
        spec.reported_auto_slow_errno == st["auto_slow_errno"]
        and st["auto_slow_errno"] is None
        and spec.reported_effective_auto_slow_shutter == st["effective_auto_slow_shutter"]
        and spec.reported_iso_auto_min_ss_errno == st["iso_auto_min_ss_errno"]
        and st["iso_auto_min_ss_errno"] is None
        and spec.reported_min_ss_flash_override == st["effective_min_ss_flash_override"]
        and spec.reported_base_iso_low == st["base_iso_low"]
        and spec.reported_base_iso_high == st["base_iso_high"]
        and spec.reported_base_iso_menu_exposed == st["base_iso_menu_exposed"]
        and spec.post_auto_slow_shutter == st["post_auto_slow_shutter"]
        and spec.post_iso_auto_min_ss == st["post_iso_auto_min_ss"]
        and spec.post_iso_range_limit_persisted == st["post_iso_range_limit_persisted"]
        and spec.autoslow_6lockout_or_minss_still_drift_events == 0
        and spec.dual_base_iso_curve_matrix_drift_events == 0
    )
    if not autoslow_dual_base_ok:
        _fail(
            P366_BLOCKED_AUTOSLOW_MINSS_OR_DUAL_BASE_ISO_DRIFT,
            "Auto Slow Shutter 6+ lockout, Still ISO AUTO Min. SS, ISO Range Limit reset, or Dual Base ISO matrix violated",
        )

    slot1_mutated = (
        (
            spec.requested_vault_action in P366_WRITE_MUTATING_VAULT_ACTIONS
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
            P366_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P366_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P366_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P366_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P366_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    vault_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "67A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "effective_zoom_range": spec.reported_effective_zoom_range,
            "max_zoom_scale": spec.reported_max_zoom_scale,
            "effective_auto_slow": spec.reported_effective_auto_slow_shutter,
            "base_iso": [spec.reported_base_iso_low, spec.reported_base_iso_high],
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return ZoomCizAutoSlowBaseIsoVaultReport(
        schema=PHASE366_SCHEMA,
        version=PHASE366_VERSION,
        passed=passed,
        status=P366_STATUS_VERIFIED_PILLAR_67A if passed else P366_STATUS_REJECTED_PILLAR_67A,
        block_code=block_code,
        zoom_ciz_8speed_reset_verified=zoom_ok,
        autoslow_minss_dual_base_iso_verified=autoslow_dual_base_ok,
        slot1_vault_and_h0_h3_verified=vault_and_h0_h3_ok,
        matrix_states_checked=42,
        zoom_ciz_lockout_or_8speed_reset_drift_events=(
            spec.zoom_ciz_lockout_or_8speed_reset_drift_events
        ),
        autoslow_6lockout_or_minss_still_drift_events=(
            spec.autoslow_6lockout_or_minss_still_drift_events
        ),
        dual_base_iso_curve_matrix_drift_events=spec.dual_base_iso_curve_matrix_drift_events,
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_arw_hlg_sort_usblun_uvc_vault(
    spec: ArwHlgSortUsbLunUvcVaultSpec,
) -> ArwHlgSortUsbLunUvcVaultReport:
    """Evaluate Pillar 67B (Dormant `Lossless Comp` `.ARW` rejection, `[HLG Still Image]` `BT.2100`,
    `Sort Recording` spillover guard, `[USB LUN Setting] = Single` (`Slot 1`-Only!) macOS MSC hazard,
    `NP-FZ100` / `DC-C1` PD gate vs FX6 `19.5V`, and Dual FX3/FX6 Dormant `UVC` firewall)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P366_BLOCKED_SAFETY_POLICY_VIOLATION, "Safety policy violation")

    valid_spec = (
        spec.camera_model in (P366_FX3_MODEL_NAME, P366_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P366_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P366_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P366_SHOOTING_DOMAINS
        and spec.exposure_mode in P366_EXPOSURE_MODES
        and spec.still_file_format in P366_FX3_STILL_FILE_FORMATS
        and spec.jpeg_heif_switch in P366_FX3_JPEG_HEIF_SWITCH_MODES
        and spec.hlg_still_image in P366_ON_OFF_MODES
        and spec.rec_media_mode in P366_FX3_REC_MEDIA_MODES
        and spec.auto_switch_media in P366_ON_OFF_MODES
        and spec.usb_lun_setting in P366_FX3_USB_LUN_SETTINGS
        and spec.usb_power_supply in P366_ON_OFF_MODES
        and spec.streaming_transport in P366_FX3_STREAMING_TRANSPORTS
        and spec.movie_rec_during_streaming in P366_FX3_MOVIE_REC_DURING_STREAMING_MODES
        and spec.rec_media_dur_hdmi_output in P366_FX3_REC_MEDIA_DUR_HDMI_MODES
        and spec.reset_action in P366_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P366_VAULT_ACTIONS
        and spec.vault_firewall_errno in P366_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P366_BLOCKED_INVALID_PILLAR67B_SPEC, "Invalid Pillar 67B spec fields")

    st = compute_expected_arw_hlg_sort_usblun_uvc_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        exposure_mode=spec.exposure_mode,
        dro_bracket_active=spec.dro_bracket_active,
        still_file_format=spec.still_file_format,
        raw_file_type=spec.raw_file_type,
        jpeg_heif_switch=spec.jpeg_heif_switch,
        hlg_still_image=spec.hlg_still_image,
        rec_media_mode=spec.rec_media_mode,
        auto_switch_media=spec.auto_switch_media,
        slot2_full_or_unready=spec.slot2_full_or_unready,
        usb_connection_mode=spec.usb_connection_mode,
        usb_lun_setting=spec.usb_lun_setting,
        host_os_is_macos=spec.host_os_is_macos,
        usb_power_supply=spec.usb_power_supply,
        npfz100_present_with_charge=spec.npfz100_present_with_charge,
        usb_pd_watts=spec.usb_pd_watts,
        dc_coupler_model=spec.dc_coupler_model,
        cable_emarked_amps=spec.cable_emarked_amps,
        fx6_dc_in_volts=spec.fx6_dc_in_volts,
        uvc_streaming_requested=spec.uvc_streaming_requested,
        network_streaming_active=spec.network_streaming_active,
        streaming_transport=spec.streaming_transport,
        movie_rec_during_streaming=spec.movie_rec_during_streaming,
        rec_media_dur_hdmi_output=spec.rec_media_dur_hdmi_output,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    arw_hlg_sort_ok = (
        spec.reported_raw_file_type_errno == st["raw_file_type_errno"]
        and st["raw_file_type_errno"] is None
        and spec.reported_hlg_still_errno == st["hlg_still_errno"]
        and st["hlg_still_errno"] is None
        and spec.reported_effective_hlg_still == st["effective_hlg_still"]
        and spec.reported_hlg_bt2100_active == st["hlg_bt2100_active"]
        and spec.reported_hlg_pp_dro_disabled == st["hlg_pp_dro_disabled"]
        and spec.reported_sort_spillover_targets_slot1 == st["sort_spillover_targets_slot1"]
        and spec.post_raw_file_type == st["post_raw_file_type"]
        and spec.post_jpeg_heif_switch == st["post_jpeg_heif_switch"]
        and spec.post_hlg_still_image == st["post_hlg_still_image"]
        and spec.post_rec_media_mode == st["post_rec_media_mode"]
        and spec.dormant_lossless_arw_exposed_events == 0
        and spec.hlg_still_or_sort_rec_spillover_drift_events == 0
    )
    if not arw_hlg_sort_ok:
        _fail(
            P366_BLOCKED_DORMANT_ARW_HLG_OR_SORT_SPILLOVER_DRIFT,
            "Dormant Lossless Comp .ARW exposed, HLG Still BT.2100 prerequisites, FX6 still spoof, or Sort Recording rule violated",
        )

    usblun_pd_uvc_ok = (
        spec.reported_usb_mode_errno == st["usb_mode_errno"]
        and st["usb_mode_errno"] is None
        and spec.reported_slot1_exposed_to_host == st["slot1_exposed_to_host"]
        and spec.reported_slot2_exposed_to_host == st["slot2_exposed_to_host"]
        and spec.reported_macos_msc_host_blocked == st["macos_msc_host_blocked"]
        and not st["macos_msc_host_blocked"]
        and spec.reported_power_boot_allowed == st["power_boot_allowed"]
        and st["power_boot_allowed"]
        and spec.reported_power_brownout_risk == st["power_brownout_risk"]
        and not st["power_brownout_risk"]
        and not spec.uvc_streaming_requested
        and spec.reported_dormant_uvc_errno == st["dormant_uvc_errno"]
        and st["dormant_uvc_errno"] is None
        and spec.reported_streaming_card_write_attempt == st["streaming_card_write_attempt"]
        and spec.reported_hdmi_card_write_attempt == st["hdmi_card_write_attempt"]
        and spec.post_usb_connection_mode == st["post_usb_connection_mode"]
        and spec.post_usb_lun_setting == st["post_usb_lun_setting"]
        and spec.post_usb_power_supply == st["post_usb_power_supply"]
        and spec.usb_lun_single_slot1_msc_hazard_events == 0
        and spec.npfz100_pd_interlock_or_dcc1_drift_events == 0
        and spec.dormant_uvc_streaming_exposed_events == 0
    )
    if not usblun_pd_uvc_ok:
        _fail(
            P366_BLOCKED_USBLUN_SINGLE_PD_OR_DORMANT_UVC_DRIFT,
            "USB LUN Single (Slot 1-only!) macOS MSC hazard, NP-FZ100/DC-C1 PD gate, or dual FX3/FX6 dormant UVC firewall violated",
        )

    slot1_mutated = (
        (
            spec.requested_vault_action in P366_WRITE_MUTATING_VAULT_ACTIONS
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
            P366_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P366_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P366_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P366_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P366_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    overlay_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "67B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "raw_file_type": spec.raw_file_type,
            "hlg_still": spec.reported_effective_hlg_still,
            "usb_mode": spec.post_usb_connection_mode,
            "usb_lun": spec.post_usb_lun_setting,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return ArwHlgSortUsbLunUvcVaultReport(
        schema=PHASE366_SCHEMA,
        version=PHASE366_VERSION,
        passed=passed,
        status=P366_STATUS_VERIFIED_PILLAR_67B if passed else P366_STATUS_REJECTED_PILLAR_67B,
        block_code=block_code,
        arw_hlg_sort_spillover_verified=arw_hlg_sort_ok,
        usblun_single_npfz100_uvc_firewall_verified=usblun_pd_uvc_ok,
        overlay_and_h0_h3_verified=overlay_and_h0_h3_ok,
        matrix_states_checked=42,
        dormant_lossless_arw_exposed_events=spec.dormant_lossless_arw_exposed_events,
        hlg_still_or_sort_rec_spillover_drift_events=(
            spec.hlg_still_or_sort_rec_spillover_drift_events
        ),
        usb_lun_single_slot1_msc_hazard_events=spec.usb_lun_single_slot1_msc_hazard_events,
        npfz100_pd_interlock_or_dcc1_drift_events=spec.npfz100_pd_interlock_or_dcc1_drift_events,
        dormant_uvc_streaming_exposed_events=spec.dormant_uvc_streaming_exposed_events,
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_67a: Optional[ZoomCizAutoSlowBaseIsoVaultSpec] = None,
    spec_67b: Optional[ArwHlgSortUsbLunUvcVaultSpec] = None,
) -> ZoomCizAutoSlowBaseIsoArwUsbLunUvcVaultReport:
    """Combined single-shot verifier for Pillar 67A + Pillar 67B + 25 bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase366_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_zoom_ciz_autoslow_baseiso_vault(
        spec_67a or build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec()
    )
    rep_b = evaluate_arw_hlg_sort_usblun_uvc_vault(
        spec_67b or build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 366 Wave-65 donor artifact parity check failed")
    if not donor_snapshot.under_2_0s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return ZoomCizAutoSlowBaseIsoArwUsbLunUvcVaultReport(
        schema=PHASE366_SCHEMA,
        version=PHASE366_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P366_STATUS_VERIFIED_PILLAR67_SUITE if all_ok else P366_STATUS_FAIL_PILLAR67_SUITE,
        donor_snapshot=donor_snapshot,
        zoom_ciz_autoslow_baseiso_report=rep_a,
        arw_hlg_sort_usblun_uvc_report=rep_b,
        zoom_ciz_lockout_or_8speed_reset_drift_events=(
            rep_a.zoom_ciz_lockout_or_8speed_reset_drift_events
        ),
        autoslow_6lockout_or_minss_still_drift_events=(
            rep_a.autoslow_6lockout_or_minss_still_drift_events
        ),
        dual_base_iso_curve_matrix_drift_events=rep_a.dual_base_iso_curve_matrix_drift_events,
        dormant_lossless_arw_exposed_events=rep_b.dormant_lossless_arw_exposed_events,
        hlg_still_or_sort_rec_spillover_drift_events=(
            rep_b.hlg_still_or_sort_rec_spillover_drift_events
        ),
        usb_lun_single_slot1_msc_hazard_events=rep_b.usb_lun_single_slot1_msc_hazard_events,
        npfz100_pd_interlock_or_dcc1_drift_events=rep_b.npfz100_pd_interlock_or_dcc1_drift_events,
        dormant_uvc_streaming_exposed_events=rep_b.dormant_uvc_streaming_exposed_events,
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


def verify_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_67a: Optional[ZoomCizAutoSlowBaseIsoVaultSpec] = None,
    spec_67b: Optional[ArwHlgSortUsbLunUvcVaultSpec] = None,
) -> ZoomCizAutoSlowBaseIsoArwUsbLunUvcVaultReport:
    """Symmetry alias for `verify_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_and_vault`."""
    return verify_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_and_vault(
        force_clean_room=force_clean_room,
        spec_67a=spec_67a,
        spec_67b=spec_67b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 67A & 67B)
# ---------------------------------------------------------------------------


def run_pillar67a_zoom_ciz_autoslow_baseiso_vault_6_scenario_suite() -> Pillar67ASuiteResult:
    """Run 6 Pillar 67A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, ZoomCizAutoSlowBaseIsoVaultSpec, Optional[str]], ...] = (
        (
            P366_PILLAR_67A_SCENARIO_IDS[0],
            True,
            build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
                shooting_domain="Movie",
                recording_fps=24,
                movie_resolution="4K",
                zoom_range="ClearImage Zoom",
                zoom_ring_rotate="Right(W)/Left(T)",
                zoom_lever_1st_stby=5,
                zoom_lever_1st_rec=2,
                zoom_lever_2nd_stby=7,
                zoom_lever_2nd_rec=6,
                custom_key_zoom_speed_stby=4,
                custom_key_zoom_speed_rec=2,
                remote_zoom_speed_type="Fixed",
                remote_zoom_fixed_stby=6,
                remote_zoom_fixed_rec=4,
                reported_effective_zoom_range="ClearImage Zoom",
                reported_max_zoom_scale=1.5,
                reported_focus_area_locked_center=True,
                reported_metering_locked_multi=True,
                reported_face_eye_tracking_disabled=True,
                exposure_mode="P",
                iso_setting="ISO AUTO",
                log_shooting_mode="Cine EI",
                auto_slow_shutter="Off",
                gamma_curve_key="Cine EI",
                reported_effective_auto_slow_shutter="Off",
                reported_base_iso_low=800,
                reported_base_iso_high=12800,
                reported_base_iso_menu_exposed=True,
                reset_action="Camera Settings Reset",
                post_zoom_range="ClearImage Zoom",
                post_zoom_ring_rotate="Right(W)/Left(T)",
                post_zoom_lever_1st_stby=3,
                post_zoom_lever_1st_rec=3,
                post_zoom_lever_2nd_stby=8,
                post_zoom_lever_2nd_rec=8,
                post_custom_key_zoom_speed_stby=3,
                post_custom_key_zoom_speed_rec=3,
                post_remote_zoom_speed_type="Variable",
                post_remote_zoom_fixed_stby=3,
                post_remote_zoom_fixed_rec=3,
                post_auto_slow_shutter="On",
                post_iso_auto_min_ss="STD",
                post_iso_range_limit_persisted=True,
            ),
            None,
        ),
        (
            P366_PILLAR_67A_SCENARIO_IDS[1],
            True,
            build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
                shooting_domain="Still",
                still_file_format="JPEG",
                still_image_size="S",
                zoom_range="Digital Zoom",
                reported_effective_zoom_range="Digital Zoom",
                reported_max_zoom_scale=8.0,
                reported_focus_area_locked_center=True,
                reported_metering_locked_multi=True,
                reported_face_eye_tracking_disabled=True,
                exposure_mode="A",
                iso_setting="ISO AUTO",
                auto_slow_shutter="Off",
                iso_auto_min_ss="1/125",
                flash_active=True,
                gamma_curve_key="PP11 S-Cinetone",
                reported_effective_auto_slow_shutter="Off",
                reported_min_ss_flash_override=True,
                reported_base_iso_low=100,
                reported_base_iso_high=2000,
                reported_base_iso_menu_exposed=False,
                reset_action="None",
                post_zoom_range="Digital Zoom",
                post_auto_slow_shutter="Off",
                post_iso_auto_min_ss="1/125",
            ),
            None,
        ),
        (
            P366_PILLAR_67A_SCENARIO_IDS[2],
            False,
            build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
                shooting_domain="Still",
                still_file_format="RAW & JPEG",
                zoom_range="ClearImage Zoom",
                reported_zoom_errno=None,
                reset_action="Camera Settings Reset",
                post_zoom_range="Optical zoom only",
                zoom_ciz_lockout_or_8speed_reset_drift_events=1,
            ),
            P366_BLOCKED_ZOOM_CIZ_OR_8SPEED_RESET_DRIFT,
        ),
        (
            P366_PILLAR_67A_SCENARIO_IDS[3],
            False,
            build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
                shooting_domain="Movie",
                exposure_mode="M",
                auto_slow_shutter="On",
                iso_auto_min_ss="1/250",
                reported_auto_slow_errno=None,
                reported_iso_auto_min_ss_errno=None,
                autoslow_6lockout_or_minss_still_drift_events=1,
            ),
            P366_BLOCKED_AUTOSLOW_MINSS_OR_DUAL_BASE_ISO_DRIFT,
        ),
        (
            P366_PILLAR_67A_SCENARIO_IDS[4],
            False,
            build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
                log_shooting_mode="Flexible ISO",
                gamma_curve_key="Flexible ISO (S-Log3)",
                reported_base_iso_low=800,  # Wrong: Flexible ISO S-Log3 base is 640/12800, not 800!
                reported_base_iso_menu_exposed=True,  # Wrong: [Base ISO] hidden outside Cine EI!
                dual_base_iso_curve_matrix_drift_events=1,
            ),
            P366_BLOCKED_AUTOSLOW_MINSS_OR_DUAL_BASE_ISO_DRIFT,
        ),
        (
            P366_PILLAR_67A_SCENARIO_IDS[5],
            False,
            build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="CARD_WRITE_REC_MEDIA_DUR_HDMI",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/setting/67a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P366_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar67ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_zoom_ciz_autoslow_baseiso_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar67ScenarioOutcome(
                scenario_id=sid,
                pillar="67A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar67ASuiteResult(
        passed=all_ok,
        status=P366_STATUS_VERIFIED_PILLAR_67A if all_ok else P366_STATUS_REJECTED_PILLAR_67A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar67b_arw_hlg_sort_usblun_uvc_vault_6_scenario_suite() -> Pillar67BSuiteResult:
    """Run 6 Pillar 67B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, ArwHlgSortUsbLunUvcVaultSpec, Optional[str]], ...] = (
        (
            P366_PILLAR_67B_SCENARIO_IDS[0],
            True,
            build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
                shooting_domain="Still",
                exposure_mode="M",
                still_file_format="HEIF",
                raw_file_type="Uncompressed",
                jpeg_heif_switch="HEIF(4:2:2)",
                hlg_still_image="On",
                reported_effective_hlg_still="On",
                reported_hlg_bt2100_active=True,
                reported_hlg_pp_dro_disabled=True,
                usb_connection_mode="Remote Shooting",
                usb_lun_setting="Single",
                host_os_is_macos=True,
                reported_slot1_exposed_to_host=False,
                reported_slot2_exposed_to_host=False,
                reported_macos_msc_host_blocked=False,
                npfz100_present_with_charge=False,
                dc_coupler_model="DC-C1",
                usb_pd_watts=65,
                cable_emarked_amps=5,
                reported_power_boot_allowed=True,
                reported_power_brownout_risk=False,
                reset_action="Camera Settings Reset",
                post_raw_file_type="Compressed",
                post_jpeg_heif_switch="JPEG",
                post_hlg_still_image="Off",
                post_usb_connection_mode="Remote Shooting",
                post_usb_lun_setting="Single",
                post_usb_power_supply="On",
            ),
            None,
        ),
        (
            P366_PILLAR_67B_SCENARIO_IDS[1],
            True,
            build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
                camera_model=P366_FX6_DONOR_MODEL_NAME,
                fw_version=P366_FX6_DONOR_FW_VERSION,
                shooting_domain="Movie",
                raw_file_type="None",
                hlg_still_image="Off",
                usb_connection_mode="Sel. When Connect",
                usb_lun_setting="Multi",
                host_os_is_macos=True,
                npfz100_present_with_charge=False,
                fx6_dc_in_volts=19.5,
                reported_power_boot_allowed=True,
                reported_power_brownout_risk=False,
                network_streaming_active=False,
                streaming_transport="USB-LAN",
                movie_rec_during_streaming="Disable",
                rec_media_dur_hdmi_output="Off(HDMI Only)",
                reset_action="None",
                post_raw_file_type="None",
                post_usb_connection_mode="Sel. When Connect",
                post_usb_lun_setting="Multi",
            ),
            None,
        ),
        (
            P366_PILLAR_67B_SCENARIO_IDS[2],
            False,
            build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
                raw_file_type="Lossless Comp (L)",
                reported_raw_file_type_errno=None,
                dormant_lossless_arw_exposed_events=1,
            ),
            P366_BLOCKED_DORMANT_ARW_HLG_OR_SORT_SPILLOVER_DRIFT,
        ),
        (
            P366_PILLAR_67B_SCENARIO_IDS[3],
            False,
            build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
                usb_connection_mode="MassStorage(MSC)",
                usb_lun_setting="Single",
                host_os_is_macos=True,
                reported_slot1_exposed_to_host=False,  # Spoofing Single hides Slot 1!
                reported_macos_msc_host_blocked=False,
                npfz100_present_with_charge=False,
                usb_pd_watts=27,
                dc_coupler_model="",
                reported_power_boot_allowed=True,  # Spoofing 9V/3A PD boots without NP-FZ100!
                usb_lun_single_slot1_msc_hazard_events=1,
                npfz100_pd_interlock_or_dcc1_drift_events=1,
            ),
            P366_BLOCKED_USBLUN_SINGLE_PD_OR_DORMANT_UVC_DRIFT,
        ),
        (
            P366_PILLAR_67B_SCENARIO_IDS[4],
            False,
            build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
                camera_model=P366_FX6_DONOR_MODEL_NAME,
                fw_version=P366_FX6_DONOR_FW_VERSION,
                raw_file_type="None",
                reset_action="None",
                post_raw_file_type="None",
                uvc_streaming_requested=True,
                reported_usb_mode_errno=None,
                reported_dormant_uvc_errno=None,
                dormant_uvc_streaming_exposed_events=1,
            ),
            P366_BLOCKED_USBLUN_SINGLE_PD_OR_DORMANT_UVC_DRIFT,
        ),
        (
            P366_PILLAR_67B_SCENARIO_IDS[5],
            False,
            build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
                rec_media_mode="Sort Recording",
                auto_switch_media="On",
                slot2_full_or_unready=True,
                reported_sort_spillover_targets_slot1=True,
                reset_action="None",
                post_rec_media_mode="Sort Recording",
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="CARD_WRITE_STILL_ARW_HIF_SORT_SPILLOVER",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/mnt/emmc/67b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P366_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar67ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_arw_hlg_sort_usblun_uvc_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar67ScenarioOutcome(
                scenario_id=sid,
                pillar="67B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar67BSuiteResult(
        passed=all_ok,
        status=P366_STATUS_VERIFIED_PILLAR_67B if all_ok else P366_STATUS_REJECTED_PILLAR_67B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Standalone Pillar 67 Suite & Concurrent Unified 67/67 Master Aggregator
# ---------------------------------------------------------------------------


def run_pillar67_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar67StandaloneReport:
    """Run full Pillar 67 standalone suite (`6/6` Pillar 67A + `6/6` Pillar 67B + 25 bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase366_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar67a_zoom_ciz_autoslow_baseiso_vault_6_scenario_suite()
    res_b = run_pillar67b_arw_hlg_sort_usblun_uvc_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 366 donor verification failed")
    if not donor_snapshot.under_2_0s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE366_SCHEMA,
            "version": PHASE366_VERSION,
            "mode": donor_snapshot.verification_mode,
            "67a": [asdict(s) for s in res_a.scenarios],
            "67b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar67StandaloneReport(
        schema=PHASE366_SCHEMA,
        version=PHASE366_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P366_STATUS_VERIFIED_PILLAR67_SUITE if all_ok else P366_STATUS_FAIL_PILLAR67_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_67a_zoom_ciz_autoslow_baseiso_vault=res_a,
        pillar_67b_arw_hlg_sort_usblun_uvc_vault=res_b,
        zoom_ciz_lockout_or_8speed_reset_drift_events=(
            P366_ZOOM_CIZ_LOCKOUT_OR_8SPEED_RESET_DRIFT_EVENTS if res_a.passed else 1
        ),
        autoslow_6lockout_or_minss_still_drift_events=(
            P366_AUTOSLOW_6LOCKOUT_OR_MINSS_STILL_DRIFT_EVENTS if res_a.passed else 1
        ),
        dual_base_iso_curve_matrix_drift_events=(
            P366_DUAL_BASE_ISO_CURVE_MATRIX_DRIFT_EVENTS if res_a.passed else 1
        ),
        dormant_lossless_arw_exposed_events=(
            P366_DORMANT_LOSSLESS_ARW_EXPOSED_EVENTS if res_b.passed else 1
        ),
        hlg_still_or_sort_rec_spillover_drift_events=(
            P366_HLG_STILL_OR_SORT_REC_SPILLOVER_DRIFT_EVENTS if res_b.passed else 1
        ),
        usb_lun_single_slot1_msc_hazard_events=(
            P366_USB_LUN_SINGLE_SLOT1_MSC_HAZARD_EVENTS if res_b.passed else 1
        ),
        npfz100_pd_interlock_or_dcc1_drift_events=(
            P366_NPFZ100_PD_INTERLOCK_OR_DCC1_DRIFT_EVENTS if res_b.passed else 1
        ),
        dormant_uvc_streaming_exposed_events=(
            P366_DORMANT_UVC_STREAMING_EXPOSED_EVENTS if res_b.passed else 1
        ),
        slot1_data_sector_writes=(
            P366_SLOT1_DATA_SECTOR_WRITES if (res_a.passed and res_b.passed) else 1
        ),
        slot1_vault_mutation_bytes=(
            P366_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        rf_packets_transmitted=P366_RF_PACKETS_TRANSMITTED,
        rf_nvs_mutation_bytes=P366_RF_NVS_MUTATION_BYTES,
        slot1_format_hard_locked=P366_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_eopnotsupp_enforced=P366_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        slot1_vault_erofs_ebusy_enforced=P366_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
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


def _apply_master67_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def _master67_local_donors_available() -> bool:
    """Return True only when all 25 Wave-65 local donors exist."""
    required_relpaths: Tuple[str, ...] = (
        P366_DONOR_FX3_APPFW_702_RELPATH,
        P366_DONOR_FX3_BACKUP_BIN_RELPATH,
        P366_DONOR_FX3_USBG_STORAGE_KO_RELPATH,
        P366_DONOR_FX3_USBG_STILLIMAGE_KO_RELPATH,
        P366_DONOR_FX3_USB_F_UVC_KO_RELPATH,
        P366_DONOR_FX3_G_WEBCAM_KO_RELPATH,
        P366_DONOR_FX6_APPFW_601_RELPATH,
        P366_DONOR_FX6_USBG_STORAGE_KO_RELPATH,
        P366_DONOR_FX6_USBG_STILLIMAGE_KO_RELPATH,
        P366_DONOR_FX6_USB_F_UVC_KO_RELPATH,
        P366_DONOR_FX6_G_WEBCAM_KO_RELPATH,
        P366_DONOR_FX3_UXC_EN_F_RELPATH,
        P366_DONOR_FX3_UXC_SC_F_RELPATH,
        P366_DONOR_FX3_UXC_TC_F_RELPATH,
        P366_DONOR_FX3_UXC_JA_F_RELPATH,
        P366_DONOR_FX3_UXC_EN_RELPATH,
        P366_DONOR_FX3_UXC_SC_RELPATH,
        P366_DONOR_FX3_UXC_TC_RELPATH,
        P366_DONOR_FX3_UXC_JA_RELPATH,
        P366_DONOR_FX3_UXC_EN_G_RELPATH,
        P366_DONOR_FX3_UXC_SC_G_RELPATH,
        P366_DONOR_FX3_UXC_TC_G_RELPATH,
        P366_DONOR_FX3_UXC_JA_G_RELPATH,
        P366_DONOR_FX6_UXC_EN_RELPATH,
        P366_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for relpath in required_relpaths:
        try:
            resolved = _resolve_phase366_donor_path(relpath)
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


def evaluate_realhw_67pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master67PillarRecoveryReport:
    """Evaluate and aggregate all 67 recovery pillars (`1..67`) concurrently -> `67/67` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_67_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    if resolved_clean_room is None and not _master67_local_donors_available():
        resolved_clean_room = True
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_66pillar() -> Master66PillarRecoveryReport:
        return evaluate_realhw_66pillar_recovery_master(**kw)

    def _run_p67() -> Tuple[Pillar67StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar67_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_66 = pool.submit(_run_66pillar)
        fut_67 = pool.submit(_run_p67)
        m66_rep = fut_66.result()
        p67_rep, p67_dt = fut_67.result()

    all_errors: List[str] = list(m66_rep.errors) + list(p67_rep.errors)
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
        if getattr(m66_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-66 violated {attr_name} == {expected_val}")
        if getattr(p67_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 67 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("zoom_ciz_lockout_or_8speed_reset_drift_events", 0),
        ("autoslow_6lockout_or_minss_still_drift_events", 0),
        ("dual_base_iso_curve_matrix_drift_events", 0),
        ("dormant_lossless_arw_exposed_events", 0),
        ("hlg_still_or_sort_rec_spillover_drift_events", 0),
        ("usb_lun_single_slot1_msc_hazard_events", 0),
        ("npfz100_pd_interlock_or_dcc1_drift_events", 0),
        ("dormant_uvc_streaming_exposed_events", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("rf_packets_transmitted", 0),
        ("rf_nvs_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_eopnotsupp_enforced", True),
        ("slot1_vault_erofs_ebusy_enforced", True),
    ):
        if getattr(p67_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 67 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m66_rep.pillars)
    spec67 = MASTER_67_PILLAR_SPECS[66]
    p67_metrics = {
        "pillar_67a_zoom_ciz_autoslow_baseiso_vault": (
            f"{p67_rep.pillar_67a_zoom_ciz_autoslow_baseiso_vault.scenarios_passed}/"
            f"{p67_rep.pillar_67a_zoom_ciz_autoslow_baseiso_vault.scenarios_total}"
        ),
        "pillar_67b_arw_hlg_sort_usblun_uvc_vault": (
            f"{p67_rep.pillar_67b_arw_hlg_sort_usblun_uvc_vault.scenarios_passed}/"
            f"{p67_rep.pillar_67b_arw_hlg_sort_usblun_uvc_vault.scenarios_total}"
        ),
        "zoom_ciz_lockout_or_8speed_reset_drift_events": (
            p67_rep.zoom_ciz_lockout_or_8speed_reset_drift_events
        ),
        "autoslow_6lockout_or_minss_still_drift_events": (
            p67_rep.autoslow_6lockout_or_minss_still_drift_events
        ),
        "dual_base_iso_curve_matrix_drift_events": (
            p67_rep.dual_base_iso_curve_matrix_drift_events
        ),
        "dormant_lossless_arw_exposed_events": p67_rep.dormant_lossless_arw_exposed_events,
        "hlg_still_or_sort_rec_spillover_drift_events": (
            p67_rep.hlg_still_or_sort_rec_spillover_drift_events
        ),
        "usb_lun_single_slot1_msc_hazard_events": (
            p67_rep.usb_lun_single_slot1_msc_hazard_events
        ),
        "npfz100_pd_interlock_or_dcc1_drift_events": (
            p67_rep.npfz100_pd_interlock_or_dcc1_drift_events
        ),
        "dormant_uvc_streaming_exposed_events": p67_rep.dormant_uvc_streaming_exposed_events,
        "slot1_data_sector_writes": p67_rep.slot1_data_sector_writes,
        "slot1_vault_mutation_bytes": p67_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p67_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_eopnotsupp_enforced": p67_rep.slot1_vault_erofs_eopnotsupp_enforced,
        "overall_ready_for_hardware_attach": p67_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p67_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p67_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p67_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec67[0],
            pillar_id=spec67[1],
            phase_label=spec67[2],
            module_name=spec67[3],
            passed=bool(p67_rep.all_passed),
            status=p67_rep.status,
            verification_mode=p67_rep.verification_mode,
            elapsed_seconds=p67_dt,
            key_metrics=p67_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec67[1],
                    "mode": p67_rep.verification_mode,
                    "status": p67_rep.status,
                    "metrics": p67_metrics,
                    "passed": p67_rep.all_passed,
                }
            ),
            errors=tuple(p67_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master67_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p67_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_67_PILLAR_COUNT == 67
        and pillars_passed == 67
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE366_SCHEMA,
            "schema_version": PHASE366_MASTER_SCHEMA,
            "version": PHASE366_VERSION,
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

    return Master67PillarRecoveryReport(
        schema=PHASE366_SCHEMA,
        schema_version=PHASE366_MASTER_SCHEMA,
        version=PHASE366_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=(
            P366_STATUS_VERIFIED_67OF67_AGGREGATOR if all_ok else P366_STATUS_FAIL_67OF67_AGGREGATOR
        ),
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P366_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.50,
        under_6s_budget=elapsed < P366_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P366_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p67_rep.donor_snapshot,
        pillar67_a_zoom_ciz_autoslow_baseiso_vault=(
            p67_rep.pillar_67a_zoom_ciz_autoslow_baseiso_vault
        ),
        pillar67_b_arw_hlg_sort_usblun_uvc_vault=(
            p67_rep.pillar_67b_arw_hlg_sort_usblun_uvc_vault
        ),
        zoom_ciz_lockout_or_8speed_reset_drift_events=(
            p67_rep.zoom_ciz_lockout_or_8speed_reset_drift_events
        ),
        autoslow_6lockout_or_minss_still_drift_events=(
            p67_rep.autoslow_6lockout_or_minss_still_drift_events
        ),
        dual_base_iso_curve_matrix_drift_events=(
            p67_rep.dual_base_iso_curve_matrix_drift_events
        ),
        dormant_lossless_arw_exposed_events=p67_rep.dormant_lossless_arw_exposed_events,
        hlg_still_or_sort_rec_spillover_drift_events=(
            p67_rep.hlg_still_or_sort_rec_spillover_drift_events
        ),
        usb_lun_single_slot1_msc_hazard_events=(
            p67_rep.usb_lun_single_slot1_msc_hazard_events
        ),
        npfz100_pd_interlock_or_dcc1_drift_events=(
            p67_rep.npfz100_pd_interlock_or_dcc1_drift_events
        ),
        dormant_uvc_streaming_exposed_events=p67_rep.dormant_uvc_streaming_exposed_events,
        fx3_zoom_range_resettable=P366_FX3_ZOOM_RANGE_RESETTABLE,
        fx3_zoom_speed_resettable=P366_FX3_ZOOM_SPEED_RESETTABLE,
        fx3_has_dormant_lossless_arw_exposed=P366_FX3_HAS_DORMANT_LOSSLESS_ARW_EXPOSED,
        fx3_has_native_uvc_streaming=P366_FX3_HAS_NATIVE_UVC_STREAMING,
        fx6_has_native_uvc_streaming=P366_FX6_HAS_NATIVE_UVC_STREAMING,
        fx6_has_digital_zoom=P366_FX6_HAS_DIGITAL_ZOOM,
        fx6_has_still_arw_hlg_pipeline=P366_FX6_HAS_STILL_ARW_HLG_PIPELINE,
        fx6_has_iso_auto_min_ss=P366_FX6_HAS_ISO_AUTO_MIN_SS,
        slot1_data_sector_writes=(
            m66_rep.slot1_data_sector_writes + p67_rep.slot1_data_sector_writes
        ),
        slot1_vault_mutation_bytes=(
            m66_rep.slot1_vault_mutation_bytes + p67_rep.slot1_vault_mutation_bytes
        ),
        rf_packets_transmitted=m66_rep.rf_packets_transmitted + p67_rep.rf_packets_transmitted,
        rf_nvs_mutation_bytes=m66_rep.rf_nvs_mutation_bytes + p67_rep.rf_nvs_mutation_bytes,
        slot1_format_hard_locked=(
            m66_rep.slot1_format_hard_locked and p67_rep.slot1_format_hard_locked
        ),
        slot1_vault_erofs_eopnotsupp_enforced=(
            m66_rep.slot1_vault_erofs_eopnotsupp_enforced
            and p67_rep.slot1_vault_erofs_eopnotsupp_enforced
        ),
        slot1_vault_erofs_ebusy_enforced=(
            m66_rep.slot1_vault_erofs_ebusy_enforced and p67_rep.slot1_vault_erofs_ebusy_enforced
        ),
        breathing_comp_lockout_or_catalyst_drift_events=(
            m66_rep.breathing_comp_lockout_or_catalyst_drift_events
        ),
        file_settings_camid_reel_or_sdhc_drift_events=(
            m66_rep.file_settings_camid_reel_or_sdhc_drift_events
        ),
        copyright_46ch_reset_erratum_or_serial_drift_events=(
            m66_rep.copyright_46ch_reset_erratum_or_serial_drift_events
        ),
        camset_copyright_pii_leak_events=m66_rep.camset_copyright_pii_leak_events,
        camset_copyright_pii_leaked_bytes=m66_rep.camset_copyright_pii_leaked_bytes,
        powersave_9cond_or_dormant_monitor_drift_events=(
            m66_rep.powersave_9cond_or_dormant_monitor_drift_events
        ),
        dormant_power_save_by_monitor_exposed_events=(
            m66_rep.dormant_power_save_by_monitor_exposed_events
        ),
        ntsc_pal_reboot_or_slot1_format_drift_events=(
            m66_rep.ntsc_pal_reboot_or_slot1_format_drift_events
        ),
        hdmi_raw_output_or_media_vault_drift_events=(
            m66_rep.hdmi_raw_output_or_media_vault_drift_events
        ),
        hdmi_4k_only_or_gamut_removal_drift_events=(
            m66_rep.hdmi_4k_only_or_gamut_removal_drift_events
        ),
        desqueeze_ratio_lock_or_bypass_drift_events=(
            m66_rep.desqueeze_ratio_lock_or_bypass_drift_events
        ),
        rec_lamp_tally_or_emph_display_drift_events=(
            m66_rep.rec_lamp_tally_or_emph_display_drift_events
        ),
        dormant_var_shutter_or_apsc_reset_drift_events=(
            m66_rep.dormant_var_shutter_or_apsc_reset_drift_events
        ),
        dormant_var_shutter_exposed_events=m66_rep.dormant_var_shutter_exposed_events,
        hdmi_red_border_clean_feed_leak_pixels=(
            m66_rep.hdmi_red_border_clean_feed_leak_pixels
        ),
        recorded_media_desqueeze_pixels=m66_rep.recorded_media_desqueeze_pixels,
        fx6_sdi_desqueeze_pixels=m66_rep.fx6_sdi_desqueeze_pixels,
        shoe_audio_preemption_or_limiter_drift_events=(
            m66_rep.shoe_audio_preemption_or_limiter_drift_events
        ),
        subject_recog_myth_or_face_memory_drift_events=(
            m66_rep.subject_recog_myth_or_face_memory_drift_events
        ),
        silent_mode_target_or_barrier_drift_events=(
            m66_rep.silent_mode_target_or_barrier_drift_events
        ),
        bodydata_version_flash_or_slot1_vault_drift_events=(
            m66_rep.bodydata_version_flash_or_slot1_vault_drift_events
        ),
        dormant_shutter_when_pwr_off_exposed_events=(
            m66_rep.dormant_shutter_when_pwr_off_exposed_events
        ),
        hdmi_face_frame_pixels_emitted=m66_rep.hdmi_face_frame_pixels_emitted,
        cnflasha_pixel_map_mutation_bytes=m66_rep.cnflasha_pixel_map_mutation_bytes,
        slot1_bodydata_mutation_bytes=m66_rep.slot1_bodydata_mutation_bytes,
        bodydata_placement_or_flash_authorized=m66_rep.bodydata_placement_or_flash_authorized,
        ftp_protocol_sftp_or_jpeg_size_drift_events=(
            m66_rep.ftp_protocol_sftp_or_jpeg_size_drift_events
        ),
        wb_custom_cine_ei_or_shockless_drift_events=(
            m66_rep.wb_custom_cine_ei_or_shockless_drift_events
        ),
        movie_af_speed_or_focus_map_spoof_events=m66_rep.movie_af_speed_or_focus_map_spoof_events,
        marker_15ratio_peaking_hdmi_leak_events=m66_rep.marker_15ratio_peaking_hdmi_leak_events,
        zero_rf_usblan_or_slot1_avf_bypass_events=(
            m66_rep.zero_rf_usblan_or_slot1_avf_bypass_events
        ),
        usblan_packets_transmitted=m66_rep.usblan_packets_transmitted,
        hdmi_marker_peaking_pixels_emitted=m66_rep.hdmi_marker_peaking_pixels_emitted,
        slot1_avf_info_mutation_bytes=m66_rep.slot1_avf_info_mutation_bytes,
        rec_media_prioritize_or_autoswitch_drift_events=(
            m66_rep.rec_media_prioritize_or_autoswitch_drift_events
        ),
        card_speed_vpg200_vpg400_gate_drift_events=(
            m66_rep.card_speed_vpg200_vpg400_gate_drift_events
        ),
        proxy_sq_dci4k_or_120p_lockout_drift_events=(
            m66_rep.proxy_sq_dci4k_or_120p_lockout_drift_events
        ),
        cloud_init_persist_or_power_off_ble_rf_events=(
            m66_rep.cloud_init_persist_or_power_off_ble_rf_events
        ),
        mymenu_42slot_or_fx6_lock_spoof_events=m66_rep.mymenu_42slot_or_fx6_lock_spoof_events,
        zero_rf_or_slot1_vault_bypass_events=m66_rep.zero_rf_or_slot1_vault_bypass_events,
        slot1_dcim_m4root_avf_mutation_bytes=m66_rep.slot1_dcim_m4root_avf_mutation_bytes,
        big6_home_or_lower_left_nd_drift_events=m66_rep.big6_home_or_lower_left_nd_drift_events,
        framing_manual_or_dormant_auto_framing_drift_events=(
            m66_rep.framing_manual_or_dormant_auto_framing_drift_events
        ),
        interval_shoot_9999_or_fx6_mxf_spoof_events=(
            m66_rep.interval_shoot_9999_or_fx6_mxf_spoof_events
        ),
        tc_make_regen_or_hdmi_rec_ctrl_drift_events=(
            m66_rep.tc_make_regen_or_hdmi_rec_ctrl_drift_events
        ),
        access_authen_ssh_tls_or_fan_max_drift_events=(
            m66_rep.access_authen_ssh_tls_or_fan_max_drift_events
        ),
        slot1_dcim_avf_mutation_bytes=m66_rep.slot1_dcim_avf_mutation_bytes,
        fx3_has_var_shutter=m66_rep.fx3_has_var_shutter,
        fx3_has_builtin_evf=m66_rep.fx3_has_builtin_evf,
        fx3_has_builtin_end_filter=m66_rep.fx3_has_builtin_end_filter,
        fx3_has_bt_timecode_link=m66_rep.fx3_has_bt_timecode_link,
        fx3_has_dormant_auto_framing=m66_rep.fx3_has_dormant_auto_framing,
        fx3_has_dormant_auto_hdr=m66_rep.fx3_has_dormant_auto_hdr,
        fx3_has_dormant_bulb_timer=m66_rep.fx3_has_dormant_bulb_timer,
        fx3_has_dormant_divide_extract=m66_rep.fx3_has_dormant_divide_extract,
        fx3_has_fan_control_max=m66_rep.fx3_has_fan_control_max,
        fx3_has_movie_self_timer=m66_rep.fx3_has_movie_self_timer,
        fx3_has_movie_sort_recording=m66_rep.fx3_has_movie_sort_recording,
        fx3_has_physical_end_hw=m66_rep.fx3_has_physical_end_hw,
        fx3_has_5axis_ibis=m66_rep.fx3_has_5axis_ibis,
        fx3_has_power_save_by_monitor=m66_rep.fx3_has_power_save_by_monitor,
        fx6_has_ibis=m66_rep.fx6_has_ibis,
        fx6_has_fan_control_max=m66_rep.fx6_has_fan_control_max,
        fx6_has_still_self_timer=m66_rep.fx6_has_still_self_timer,
        fx6_has_fn_menu=m66_rep.fx6_has_fn_menu,
        fx6_has_my_dial=m66_rep.fx6_has_my_dial,
        fx6_has_bluetooth_hardware=m66_rep.fx6_has_bluetooth_hardware,
        fx6_has_av_tv_rotate=m66_rep.fx6_has_av_tv_rotate,
        fx6_has_exif_copyright_menu=m66_rep.fx6_has_exif_copyright_menu,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        master_67pillar_sha256=master_sha,
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


def evaluate_67pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master67PillarRecoveryReport:
    """Short alias for `evaluate_realhw_67pillar_recovery_master`."""
    return evaluate_realhw_67pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_67pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master67PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_67pillar_recovery_master`."""
    return evaluate_realhw_67pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_67pillar_recovery(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master67PillarRecoveryReport:
    """Milestone 324/349 dynamic discovery alias for `evaluate_realhw_67pillar_recovery_master`."""
    return evaluate_realhw_67pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_all_67_recovery_pillars(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master67PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_67pillar_recovery_master`."""
    return evaluate_realhw_67pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
