"""Phase 370 Milestone — Recovery Pillar 68 (`68A`/`68B`) & Concurrent 68/68 Master Recovery Verifier:
Wave-66 Sony ILME-FX3 (Ver. 7.02) vs ILME-FX6 (Ver. 6.01) Empirically Grounded Guardrails:
  * Pillar 68A (Still `[Drive Mode]` 10fps / Dormant `[Focus Bracket]` Rejection + 2-Option `[Shutter Type]` /
    `1/250 s` X-Sync / `[e-Front Curtain Shut.]` / `[Long Exposure NR]` / `[High ISO NR]`):
    1. `Shooting -> [Drive Mode]` (Still-only, grayed in Movie/`S&Q`; ALL `Can be reset` under
       `Camera Settings Reset`): `Single Shooting` (def), `Cont. Shooting` (`Hi+` ~10 fps non-live-view
       refresh / `Hi` ~8 fps / `Mid` ~6 fps / `Lo` ~3 fps; `> F11` locks focus on first frame in `Hi+/Hi/Mid`;
       rate drops on `Uncompressed RAW` or Flash), `Self-timer(Single)` (`10/5/2 Sec`), `Self-timer(Cont)`
       (strictly 6 combos `10/5/2 Sec` x `3/5 Img.`; dormant `10SEC_10IMAGES` rejected `EOPNOTSUPP=95`),
       `Cont. Bracket` & `Single Bracket` (`0.3/0.5/0.7/1.0 EV` x `3/5/9 Img.`, `2.0/3.0 EV` x `3/5 Img.`,
       disabled in `iAuto`), `WB bracket` (`Lo +-10 MK-1` / `Hi +-20 MK-1`), `DRO Bracket` (`Lo Lv 1,2,3` /
       `Hi Lv 1,3,5`, disabled under `[HLG Still Image] = On`), `[Bracket Settings]` (`Off/2/5/10 Sec`,
       `0->-->+` def / `-->0->+`), and `[Interval Shoot Func.]` (still sequence only, independent
       `[Shutter Type in Interval]` defaulting to `Electronic Shutter`). Explicitly reject dormant
       `[Focus Bracket]` (`0` `ilc/2210` hits despite shared ELF `BKID_APP_setting_focus_bracket_*` and
       `_f 0x7563`/`0x6915`) on BOTH `ILME-FX3 Ver. 7.02` and pure-cinema `ILME-FX6 Ver. 6.01` (zero Still
       `Drive Mode` and zero `Focus Bracket`).
    2. `[Shutter Type]` (`Shooting -> [Shutter/Silent]`, `Can be reset`): strictly 2 exposed options
       (`Mechanical Shutter` def `_f 0x6ddb` / `Electronic Shutter` `_f 0x755a`; NO `Auto` option — reject
       dormant `ANTI_DISTORTION_SHUTTER_AUTO` / `_f 0x66b8` `EOPNOTSUPP=95`). `Electronic Shutter` or
       `[Silent Mode] = On` hard-locks 5 features (`Flash`, `Long Exposure NR`, `e-Front Curtain Shut.`,
       `BULB`, `Anti-flicker Shoot.`). Mechanical flash X-Sync ceiling strictly `1/250 s` (`0` `1/320` hits).
       `[e-Front Curtain Shut.]` (`_f 0x64c6`, Sony typo `BKID_APP_setting_front_curtaion_shutter`):
       `On` (def) / `Off`, **Resists `Camera Settings Reset` (`Not available`, cleared only on `Initialize`)**,
       locked out under `Electronic Shutter` / `Silent Mode = On`. `[Long Exposure NR]` (`_f 0x6465`,
       `Can be reset`, `>= 1 s` dark-frame subtraction `NID_LONG_EXP_NR_PROGRESS`, disabled in
       `Electronic Shutter` / `Silent` / `Cont. Shooting` / `Cont. Bracket`, locked `On` in `iAuto`) &
       `[High ISO NR]` (`_f 0x650b`, `Can be reset`, strictly 3 levels `Normal` def / `Low` / `Off`, dormant
       `HIGH` rejected `EOPNOTSUPP=95`, fixed `Normal` in `iAuto`, unavailable in pure `RAW`, never alters
       `.ARW` RAW) vs FX6 `Shooting > Noise Suppression` + `Technical > APR > Execute`.
  * Pillar 68B (`[Creative Look]` 10 Presets + 6 Custom + 8 Asymmetric Params / Dormant `[Soft Skin Effect]`
    Rejection + `[Delete]` / `[Protect]` / `[Recover Image DB]` Tier-0 `Slot 1 EROFS=30` Vault Firewall):
    1. `Exposure/Color -> [Color/Tone] -> [Creative Look]` (`_f 0x6823`/`0x6c22`, Still/Movie/`S&Q`,
       `Can be reset`): 10 presets (`ST` def, `PT`, `NT`, `VV`, `VV2`, `FL`, `IN`, `SH`, `BW`, `SE`) +
       `Custom Look 1..6` (`look_still0..15` & `look_movie0..15`, 16 slots). 8 sub-parameters with asymmetric
       ranges: `-9..+9` (`Contrast`, `Highlights`, `Shadows`, `Saturation`), **`0..9`** (`Fade`,
       `Sharpness`, **`Clarity`** — asymmetric non-negative!), **`1..5`** (`Sharpness Range` / `fineness`).
       `Saturation` locked on `BW`/`SE`; `Sharpness Range` locked in Movie/`S&Q`; forced `[-]` disabled
       under `Picture Profile != Off`, `Log Shooting != Off`, `HLG Still Image = On`, or `iAuto`.
       Reject dormant `[Soft Skin Effect]` on BOTH FX3 and FX6 (`0` `ilc/2210` hits, SDK `-`) vs FX6
       `Paint/Look > Base Look`, `Scene File`, `Detail`, `Matrix`/`Multi Matrix`.
    2. Playback `[Delete]` (`All Other Than This Img.`, `All Images in This Group`, `Multiple Img.`,
       `All in this Folder`, `All with this date`; skips Protected, coupled Proxy delete), `[Delete confirm.]`
       (`"Cancel" first` def / `"Delete" first`), `[Delete pressing twice]` (`Off` def / `On`; both resist
       `Camera Settings Reset`, cleared only on `Initialize`), `[Protect]` (DCF/`Fsys_Chmod` + coupled Proxy
       protect; `Copy` does not copy protect status), and `Shooting -> [Media] -> [Recover Image DB]`
       (`AVF_INFO` rebuild + FTP result wipe without deleting AV files, battery-gated, unaffected by BOTH
       `Camera Settings Reset` AND `Initialize`) vs safe read-only `[Display Media Info.]` (`40,000` still cap).
       Enforce fail-closed **`EROFS (errno 30)`** (`slot1_sector_writes == 0`, `slot1_data_sector_writes == 0`,
       `cnflasha_writes == 0`, `emmc_writes_authorized == False`, `raw_firmware_bytes_leaked == 0`) against
       any `[Delete]`, `[Protect]`, or `[Recover Image DB]` targeting Tier-0 read-only `Slot 1` (and FX6
       `Restore Media(A)`), plus Stage-B `/tmp` overlay & `Backup.bin H0 == H3` (`16/16`).
  * Unified `68/68` Master Recovery Aggregator (Pillars `1..67` + Pillar `68`) running concurrently.

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
from .realhw_67pillar_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault_verifier import (
    MASTER_67_PILLAR_SPECS,
    Master67PillarRecoveryReport,
    evaluate_realhw_67pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Phase 370 Metadata, Safety Redlines & Pinned Budget Constants
# ---------------------------------------------------------------------------

PHASE370_SCHEMA = (
    "realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier_v1"
)
PHASE370_MASTER_SCHEMA = "realhw_68pillar_recovery_master_v1"
PHASE370_VERSION = "1.0.0"
PHASE370_PHASE_NUMBER = 370

P370_ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"

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

P370_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED = False
P370_CROSS_MODEL_FLASH_AUTHORIZED = False
P370_EMMC_WRITES_AUTHORIZED = False
P370_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
P370_OVERALL_READY_FOR_HARDWARE_ATTACH = False

OTP_FUSE_TOUCHES = 0
OTP_FUSE_WRITES = 0
RPMB_COUNTER_INCREMENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PHYSICAL_DEVICE_WRITES = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

P370_BOUNDED_HEADER_BYTES = 4096
P370_MAX_FULL_DONOR_BYTES = 3_000_000
P370_DONOR_INSPECT_BUDGET_SECONDS = 2.0
P370_DONOR_INSPECT_CI_BUDGET_SECONDS = 2.0
P370_FAST_CLI_BUDGET_SECONDS = 1.50
P370_NOMINAL_BUDGET_SECONDS = 4.00
P370_CONCURRENT_CEILING_SECONDS = 6.00

P370_ENOENT_ERRNO = 2
P370_EBUSY_ERRNO = 16
P370_EINVAL_ERRNO = 22
P370_EROFS_ERRNO = 30
P370_EOPNOTSUPP_ERRNO = 95

# Camera Identities
P370_FX3_MODEL_NAME = "ILME-FX3"
P370_FX3_MODEL_ID = 0x91030080
P370_FX3_PRODUCT_CODENAME = "PRODUCT_MODEL_ALCIN_UUD"
P370_FX3_HELPGUIDE_ID = "ilc/2210"
P370_FX3_FW_VERSION = "7.02"
P370_FX3_SUPPORTED_FW_VERSIONS = (
    "7.02", "7.01", "7.00", "6.02", "6.00", "5.00", "4.00", "3.00", "2.05", "2.04", "2.00"
)

P370_FX6_DONOR_MODEL_NAME = "ILME-FX6"
P370_FX6_DONOR_FW_VERSION = "6.01"
P370_FX6_PRODUCT_CODENAME = "PRODUCT_MODEL_CHAPLIN"

# Pinned Wave-66 17 Donors (14 FX3 + 3 FX6)
P370_DONOR_FX3_APPFW_702_RELPATH = P348_DONOR_FX3_APPFW_702_RELPATH
P370_DONOR_FX3_BACKUP_BIN_RELPATH = P348_DONOR_FX3_BACKUP_BIN_RELPATH
P370_DONOR_FX6_APPFW_601_RELPATH = P348_DONOR_FX6_APPFW_601_RELPATH
P370_DONOR_FX3_UXC_EN_F_RELPATH = P348_DONOR_FX3_UXC_EN_F_RELPATH
P370_DONOR_FX3_UXC_SC_F_RELPATH = P348_DONOR_FX3_UXC_SC_F_RELPATH
P370_DONOR_FX3_UXC_TC_F_RELPATH = P348_DONOR_FX3_UXC_TC_F_RELPATH
P370_DONOR_FX3_UXC_JA_F_RELPATH = P348_DONOR_FX3_UXC_JA_F_RELPATH
P370_DONOR_FX3_UXC_EN_RELPATH = P348_DONOR_FX3_UXC_EN_RELPATH
P370_DONOR_FX3_UXC_SC_RELPATH = P348_DONOR_FX3_UXC_SC_RELPATH
P370_DONOR_FX3_UXC_TC_RELPATH = P348_DONOR_FX3_UXC_TC_RELPATH
P370_DONOR_FX3_UXC_JA_RELPATH = P348_DONOR_FX3_UXC_JA_RELPATH
P370_DONOR_FX3_UXC_EN_G_RELPATH = P348_DONOR_FX3_UXC_EN_G_RELPATH
P370_DONOR_FX3_UXC_SC_G_RELPATH = P348_DONOR_FX3_UXC_SC_G_RELPATH
P370_DONOR_FX3_UXC_TC_G_RELPATH = P348_DONOR_FX3_UXC_TC_G_RELPATH
P370_DONOR_FX3_UXC_JA_G_RELPATH = P348_DONOR_FX3_UXC_JA_G_RELPATH
P370_DONOR_FX6_UXC_EN_RELPATH = P348_DONOR_FX6_UXC_EN_RELPATH
P370_DONOR_FX6_UXC_EN_2_RELPATH = P348_DONOR_FX6_UXC_EN_2_RELPATH

P370_PINNED_FX3_APPFW_702_BYTES = P348_PINNED_FX3_APPFW_702_BYTES
P370_PINNED_FX3_APPFW_702_HDR4K_SHA256 = P348_PINNED_FX3_APPFW_702_HDR4K_SHA256
P370_PINNED_FX3_BACKUP_BIN_BYTES = P348_PINNED_FX3_BACKUP_BIN_BYTES
P370_PINNED_FX3_BACKUP_BIN_SHA256 = P348_PINNED_FX3_BACKUP_BIN_SHA256
P370_PINNED_FX6_APPFW_601_BYTES = P348_PINNED_FX6_APPFW_601_BYTES
P370_PINNED_FX6_APPFW_601_HDR4K_SHA256 = P348_PINNED_FX6_APPFW_601_HDR4K_SHA256

P370_PINNED_FX3_UXC_EN_F_BYTES = P348_PINNED_FX3_UXC_EN_F_BYTES
P370_PINNED_FX3_UXC_EN_F_SHA256 = P348_PINNED_FX3_UXC_EN_F_SHA256
P370_PINNED_FX3_UXC_SC_F_BYTES = P348_PINNED_FX3_UXC_SC_F_BYTES
P370_PINNED_FX3_UXC_SC_F_SHA256 = P348_PINNED_FX3_UXC_SC_F_SHA256
P370_PINNED_FX3_UXC_TC_F_BYTES = P348_PINNED_FX3_UXC_TC_F_BYTES
P370_PINNED_FX3_UXC_TC_F_SHA256 = P348_PINNED_FX3_UXC_TC_F_SHA256
P370_PINNED_FX3_UXC_JA_F_BYTES = P348_PINNED_FX3_UXC_JA_F_BYTES
P370_PINNED_FX3_UXC_JA_F_SHA256 = P348_PINNED_FX3_UXC_JA_F_SHA256
P370_PINNED_FX3_UXC_EN_BYTES = P348_PINNED_FX3_UXC_EN_BYTES
P370_PINNED_FX3_UXC_EN_SHA256 = P348_PINNED_FX3_UXC_EN_SHA256
P370_PINNED_FX3_UXC_SC_BYTES = P348_PINNED_FX3_UXC_SC_BYTES
P370_PINNED_FX3_UXC_SC_SHA256 = P348_PINNED_FX3_UXC_SC_SHA256
P370_PINNED_FX3_UXC_TC_BYTES = P348_PINNED_FX3_UXC_TC_BYTES
P370_PINNED_FX3_UXC_TC_SHA256 = P348_PINNED_FX3_UXC_TC_SHA256
P370_PINNED_FX3_UXC_JA_BYTES = P348_PINNED_FX3_UXC_JA_BYTES
P370_PINNED_FX3_UXC_JA_SHA256 = P348_PINNED_FX3_UXC_JA_SHA256
P370_PINNED_FX3_UXC_EN_G_BYTES = P348_PINNED_FX3_UXC_EN_G_BYTES
P370_PINNED_FX3_UXC_EN_G_SHA256 = P348_PINNED_FX3_UXC_EN_G_SHA256
P370_PINNED_FX3_UXC_SC_G_BYTES = P348_PINNED_FX3_UXC_SC_G_BYTES
P370_PINNED_FX3_UXC_SC_G_SHA256 = P348_PINNED_FX3_UXC_SC_G_SHA256
P370_PINNED_FX3_UXC_TC_G_BYTES = P348_PINNED_FX3_UXC_TC_G_BYTES
P370_PINNED_FX3_UXC_TC_G_SHA256 = P348_PINNED_FX3_UXC_TC_G_SHA256
P370_PINNED_FX3_UXC_JA_G_BYTES = P348_PINNED_FX3_UXC_JA_G_BYTES
P370_PINNED_FX3_UXC_JA_G_SHA256 = P348_PINNED_FX3_UXC_JA_G_SHA256
P370_PINNED_FX6_UXC_EN_BYTES = P348_PINNED_FX6_UXC_EN_BYTES
P370_PINNED_FX6_UXC_EN_SHA256 = P348_PINNED_FX6_UXC_EN_SHA256
P370_PINNED_FX6_UXC_EN_2_BYTES = P348_PINNED_FX6_UXC_EN_2_BYTES
P370_PINNED_FX6_UXC_EN_2_SHA256 = P348_PINNED_FX6_UXC_EN_2_SHA256

# Zero-Violation Pillar 68 Counters & Vault Flags
P370_DRIVE_MODE_OR_DORMANT_FOCUS_BRACKET_DRIFT_EVENTS = 0
P370_SHUTTER_2OPT_XSYNC_EFCS_OR_NR_DRIFT_EVENTS = 0
P370_CREATIVE_LOOK_8PARAM_OVERRIDE_OR_SOFTSKIN_DRIFT_EVENTS = 0
P370_DELETE_PROTECT_RECOVERDB_SLOT1_VAULT_DRIFT_EVENTS = 0

P370_SLOT1_DATA_SECTOR_WRITES = 0
P370_SLOT1_SECTOR_WRITES = 0
P370_SLOT1_VAULT_MUTATION_BYTES = 0
P370_CNFLASHA_WRITES = 0
P370_RF_PACKETS_TRANSMITTED = 0
P370_RF_NVS_MUTATION_BYTES = 0

P370_SLOT1_FORMAT_HARD_LOCKED = True
P370_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True
P370_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True
P370_AIRPLANE_MODE_FORCED_ON = True

P370_STAGE_B_VOLATILE_OVERLAY_DIR = "/tmp/fx3_stage_b_overlay/pillar68"
P370_FORBIDDEN_PERSISTENT_TARGETS = (
    "/dev/cnflasha",
    "/setting",
    "/mnt/emmc",
    "/nflasha",
)
P370_TIER0_SURFACE_COUNT = 16

# ---------------------------------------------------------------------------
# Wave-66 Empirically Verified Constants (UXC resid16, ELF & Help Guide)
# ---------------------------------------------------------------------------

# 1. Sub-Pillar 68A-1: Still `[Drive Mode]`, `10 fps` & Dormant `[Focus Bracket]` Rejection
P370_DRIVE_MODE_F_RESID16 = 0x7228
P370_SINGLE_SHOOTING_RESID16S = (0x6D37, 0xE842)
P370_CONT_SHOOTING_F_RESID16S = (0x6A32, 0x68D1, 0x6C00, 0x6F48, 0x6A0B)
P370_SELF_TIMER_SINGLE_F_RESID16S = (0x6772, 0x6E8A)
P370_SELF_TIMER_CONT_RESID16S = (0x728C, 0xE6E7)
P370_BRACKET_MODES_F_RESID16S = (0x72CB, 0x790B, 0x7ACB, 0x748D, 0x6466)
P370_INTERVAL_SHOOT_F_RESID16 = 0x7027
P370_DORMANT_FOCUS_BRACKET_F_RESID16S = (0x7563, 0x6915)

P370_FX3_ACTIVE_DRIVE_MODES = (
    "Single Shooting",
    "Cont. Shooting",
    "Self-timer(Single)",
    "Self-timer(Cont)",
    "Cont. Bracket",
    "Single Bracket",
    "WB bracket",
    "DRO Bracket",
    "Interval Shoot Func.",
)
P370_FX3_DRIVE_MODE_DEFAULT = "Single Shooting"
P370_FX3_DRIVE_MODE_RESETTABLE = True
P370_FX3_CONT_SHOOT_SPEEDS_FPS: Dict[str, float] = {
    "Hi+": 10.0,
    "Hi": 8.0,
    "Mid": 6.0,
    "Lo": 3.0,
}
P370_FX3_CONT_FIRST_FRAME_AF_LOCK_F_THRESHOLD = 11.0
P370_FX3_SELF_TIMER_SINGLE_OPTIONS = ("10 Sec", "5 Sec", "2 Sec")
P370_FX3_SELF_TIMER_CONT_ACTIVE_OPTIONS = (
    "10 Sec. 3 Img.",
    "10 Sec. 5 Img.",
    "5 Sec. 3 Img.",
    "5 Sec. 5 Img.",
    "2 Sec. 3 Img.",
    "2 Sec. 5 Img.",
)
P370_FX3_SELF_TIMER_CONT_DORMANT_OPTIONS = (
    "10 Sec. 10 Img.",
    "10SEC_10IMAGES",
    "DRIVE_MODE_CONT_SELF_TIMER_10SEC_10IMAGES",
)
P370_FX3_EXP_BRACKET_STEPS_COUNTS: Dict[float, Tuple[int, ...]] = {
    0.3: (3, 5, 9),
    0.5: (3, 5, 9),
    0.7: (3, 5, 9),
    1.0: (3, 5, 9),
    2.0: (3, 5),
    3.0: (3, 5),
}
P370_FX3_WB_BRACKET_MODES = ("Lo", "Hi")  # +-10 MK-1 / +-20 MK-1 (3 Img.)
P370_FX3_DRO_BRACKET_MODES = ("Lo", "Hi")  # Lv 1,2,3 / Lv 1,3,5 (3 Img.)
P370_FX3_BRACKET_SELFTIMER_OPTIONS = ("Off", "2 Sec", "5 Sec", "10 Sec")
P370_FX3_BRACKET_ORDER_OPTIONS = ("0->-->+", "-->0->+")
P370_FX3_INTERVAL_SHUTTER_DEFAULT = "Electronic Shutter"
P370_FX3_HAS_DORMANT_FOCUS_BRACKET_EXPOSED = False
P370_FX6_HAS_STILL_DRIVE_MODE = False
P370_FX6_HAS_FOCUS_BRACKET = False

# 2. Sub-Pillar 68A-2: `[Shutter Type]` (2-Option No Auto), `1/250 s` X-Sync, `[e-Front Curtain Shut.]`, NR
P370_SHUTTER_TYPE_F_RESID16S = (0x63DB, 0x6DDB, 0x755A)
P370_DORMANT_SHUTTER_AUTO_F_RESID16 = 0x66B8
P370_EFCS_F_RESID16 = 0x64C6
P370_BKID_EFCS_SONY_TYPO = "BKID_APP_setting_front_curtaion_shutter"
P370_LONG_EXPOSURE_NR_F_RESID16 = 0x6465
P370_HIGH_ISO_NR_F_RESID16S = (0x650B, 0x688F)
P370_HIGH_ISO_NR_BASE_RESID16S = (0xE9AE, 0xE6AB, 0xEA17)

P370_FX3_ACTIVE_SHUTTER_TYPES = ("Mechanical Shutter", "Electronic Shutter")
P370_FX3_SHUTTER_TYPE_DEFAULT = "Mechanical Shutter"
P370_FX3_SHUTTER_TYPE_RESETTABLE = True
P370_FX3_DORMANT_SHUTTER_TYPES = (
    "Auto",
    "ANTI_DISTORTION_SHUTTER_AUTO",
    "STILL_SHUTTER_TYPE_ANTI_DISTORTION_SHUTTER_AUTO",
)
P370_FX3_HAS_SHUTTER_TYPE_AUTO_EXPOSED = False
P370_FX3_ELECTRONIC_OR_SILENT_LOCKED_FEATURES = (
    "Flash",
    "Long Exposure NR",
    "e-Front Curtain Shut.",
    "BULB",
    "Anti-flicker Shoot.",
)
P370_FX3_FLASH_XSYNC_CEILING = "1/250 s"
P370_FX3_FLASH_XSYNC_CEILING_RECIPROCAL = 250
P370_FX3_EFCS_DEFAULT = "On"
P370_FX3_EFCS_RESETTABLE = False  # Resists Camera Settings Reset (Not available)
P370_FX3_LONG_EXP_NR_DEFAULT = "On"
P370_FX3_LONG_EXP_NR_RESETTABLE = True
P370_FX3_LONG_EXP_NR_MIN_SHUTTER_SECONDS = 1.0
P370_FX3_HIGH_ISO_NR_ACTIVE_LEVELS = ("Normal", "Low", "Off")
P370_FX3_HIGH_ISO_NR_DORMANT_LEVELS = ("High", "HIGH")
P370_FX3_HIGH_ISO_NR_DEFAULT = "Normal"
P370_FX3_HIGH_ISO_NR_RESETTABLE = True
P370_FX6_HAS_MECHANICAL_SHUTTER = False
P370_FX6_HAS_EFCS = False
P370_FX6_HAS_LONG_EXP_NR = False
P370_FX6_NOISE_SUPPRESSION_MODES = ("Off", "Low", "Mid", "High")

# 3. Sub-Pillar 68B-1: `[Creative Look]` 10 Presets + 6 Custom + 8 Asymmetric Params / Dormant `[Soft Skin Effect]`
P370_CREATIVE_LOOK_F_RESID16S = (0x6823, 0x6C22, 0x6C98)
P370_CREATIVE_LOOK_PRESET_F_RESID16S = (
    0x770C, 0x69BA, 0x7652, 0x6AB8, 0x7864, 0x6CB6, 0x69C6, 0x6B10, 0x7091, 0x7702
)
P370_CREATIVE_LOOK_PARAM_RESID16S = (
    0xE9FB, 0x665B, 0x71B9, 0x6C64, 0xE8D0, 0xE9FD, 0x6E76, 0x6921
)
P370_DORMANT_SOFT_SKIN_F_RESID16 = 0x76D9

P370_FX3_CREATIVE_LOOK_PRESETS = ("ST", "PT", "NT", "VV", "VV2", "FL", "IN", "SH", "BW", "SE")
P370_FX3_CREATIVE_LOOK_CUSTOM_SLOTS = (
    "Custom Look 1",
    "Custom Look 2",
    "Custom Look 3",
    "Custom Look 4",
    "Custom Look 5",
    "Custom Look 6",
)
P370_FX3_CREATIVE_LOOK_ALL_SLOTS = (
    P370_FX3_CREATIVE_LOOK_PRESETS + P370_FX3_CREATIVE_LOOK_CUSTOM_SLOTS
)
P370_FX3_CREATIVE_LOOK_DEFAULT = "ST"
P370_FX3_CREATIVE_LOOK_RESETTABLE = True
P370_FX3_CREATIVE_LOOK_PARAM_BOUNDS: Dict[str, Tuple[int, int]] = {
    "contrast": (-9, 9),
    "highlights": (-9, 9),
    "shadows": (-9, 9),
    "fade": (0, 9),
    "saturation": (-9, 9),
    "sharpness": (0, 9),
    "sharpness_range": (1, 5),
    "clarity": (0, 9),
}
P370_FX3_CREATIVE_LOOK_SATURATION_LOCKED_PRESETS = ("BW", "SE")
P370_FX3_HAS_DORMANT_SOFT_SKIN_EXPOSED = False
P370_FX6_HAS_CREATIVE_LOOK = False
P370_FX6_HAS_SOFT_SKIN_EFFECT = False
P370_FX6_BASE_LOOK_MODES = ("Custom SDR", "Custom HDR", "Log")

# 4. Sub-Pillar 68B-2: `[Delete]` / `[Protect]` / `[Recover Image DB]` / `[Display Media Info.]` & Slot-1 `EROFS=30`
P370_DELETE_BASE_RESID16S = (0xE504, 0xE5AD, 0xE721, 0xE724, 0xE725)
P370_DELETE_F_RESID16S = (0x6848, 0x69F7, 0x6A5E, 0x6E0A, 0x74DB)
P370_PROTECT_BASE_RESID16S = (0xE2C9, 0xE553)
P370_RECOVER_DB_F_RESID16 = 0x711B
P370_RECOVER_DB_BASE_RESID16 = 0xE918
P370_DISPLAY_MEDIA_INFO_BASE_RESID16 = 0xEA2A

P370_FX3_DELETE_SCOPES = (
    "None",
    "This Image",
    "All Other Than This Img.",
    "All Images in This Group",
    "Multiple Img.",
    "All in this Folder",
    "All with this date",
)
P370_FX3_DELETE_CONFIRM_OPTIONS = ('"Cancel" first', '"Delete" first')
P370_FX3_DELETE_CONFIRM_DEFAULT = '"Cancel" first'
P370_FX3_DELETE_CONFIRM_RESETTABLE = False  # Resists Camera Settings Reset
P370_FX3_DELETE_TWICE_RESETTABLE = False  # Resists Camera Settings Reset
P370_FX3_PROTECT_SCOPES = (
    "None",
    "Multiple Img.",
    "All in this Folder",
    "Cancel All in this Folder",
    "All with this date",
    "Cancel All with this date",
    "All Images in This Group",
    "Cancel All in This Group",
)
P370_FX3_DISPLAY_MEDIA_INFO_STILL_CAP = 40_000
P370_FX3_PLAYBACK_DEFAULT_MEDIA_SLOT = 1

# Common Enums & Vault Constants
P370_ON_OFF_MODES = ("Off", "On")
P370_SHOOTING_DOMAINS = ("Still", "Movie", "S&Q")
P370_EXPOSURE_MODES = ("P", "A", "S", "M", "Flexible Exp.", "iAuto")
P370_STILL_FILE_FORMATS = ("JPEG", "HEIF", "RAW", "RAW & JPEG", "RAW & HEIF")
P370_RAW_FILE_TYPES = ("None", "Compressed", "Uncompressed")
P370_RESET_ACTIONS = ("None", "Camera Settings Reset", "Initialize")
P370_VAULT_ACTIONS = (
    "NONE",
    "READ_ONLY_AUDIT",
    "DISPLAY_MEDIA_INFO_READ_ONLY",
    "DELETE_FILES_SLOT1",
    "DELETE_FOLDER_OR_DATE_SLOT1",
    "PROTECT_FSYS_CHMOD_SLOT1",
    "RECOVER_IMAGE_DB_AVF_INFO_SLOT1",
    "FX6_RESTORE_MEDIA_A",
)
P370_WRITE_MUTATING_VAULT_ACTIONS = (
    "DELETE_FILES_SLOT1",
    "DELETE_FOLDER_OR_DATE_SLOT1",
    "PROTECT_FSYS_CHMOD_SLOT1",
    "RECOVER_IMAGE_DB_AVF_INFO_SLOT1",
    "FX6_RESTORE_MEDIA_A",
)
P370_VAULT_FIREWALL_ERRNOS = (None, "EROFS", "EOPNOTSUPP", "EBUSY", "EINVAL", "ENOENT")

# Status & Block Codes
P370_STATUS_VERIFIED_PILLAR_68A = (
    "VERIFIED_PILLAR_68A_DRIVE_10FPS_FOCUSBRACKET_SHUTTER_2OPT_XSYNC250_EFCS_NR_VAULT"
)
P370_STATUS_REJECTED_PILLAR_68A = (
    "REJECTED_PILLAR_68A_DRIVE_10FPS_FOCUSBRACKET_SHUTTER_2OPT_XSYNC250_EFCS_NR_VAULT"
)
P370_STATUS_VERIFIED_PILLAR_68B = (
    "VERIFIED_PILLAR_68B_CREATIVELOOK_10PRESETS_8PARAMS_SOFTSKIN_DELETE_PROTECT_RECOVERDB_VAULT"
)
P370_STATUS_REJECTED_PILLAR_68B = (
    "REJECTED_PILLAR_68B_CREATIVELOOK_10PRESETS_8PARAMS_SOFTSKIN_DELETE_PROTECT_RECOVERDB_VAULT"
)
P370_STATUS_VERIFIED_PILLAR68_SUITE = (
    "VERIFIED_PILLAR68_DRIVE_FOCUSBRACKET_SHUTTER_EFCS_CREATIVELOOK_RECOVERDB_VAULT"
)
P370_STATUS_FAIL_PILLAR68_SUITE = (
    "FAIL_PILLAR68_DRIVE_FOCUSBRACKET_SHUTTER_EFCS_CREATIVELOOK_RECOVERDB_VAULT"
)
P370_STATUS_VERIFIED_68OF68_AGGREGATOR = "VERIFIED_68OF68_PILLAR_RECOVERY_MASTER"
P370_STATUS_FAIL_68OF68_AGGREGATOR = "FAIL_68OF68_PILLAR_RECOVERY_MASTER"

P370_BLOCKED_SAFETY_POLICY_VIOLATION = "BLOCKED_P370_SAFETY_POLICY_VIOLATION"
P370_BLOCKED_INVALID_PILLAR68A_SPEC = "BLOCKED_P370_INVALID_PILLAR68A_SPEC"
P370_BLOCKED_INVALID_PILLAR68B_SPEC = "BLOCKED_P370_INVALID_PILLAR68B_SPEC"
P370_BLOCKED_DRIVE_MODE_OR_DORMANT_FOCUS_BRACKET = (
    "BLOCKED_P370_DRIVE_MODE_OR_DORMANT_FOCUS_BRACKET"
)
P370_BLOCKED_SHUTTER_2OPT_XSYNC_EFCS_OR_NR_DRIFT = (
    "BLOCKED_P370_SHUTTER_2OPT_XSYNC_EFCS_OR_NR_DRIFT"
)
P370_BLOCKED_CREATIVE_LOOK_8PARAM_OVERRIDE_OR_SOFTSKIN = (
    "BLOCKED_P370_CREATIVE_LOOK_8PARAM_OVERRIDE_OR_SOFTSKIN"
)
P370_BLOCKED_DELETE_PROTECT_OR_RECOVERDB_DRIFT = (
    "BLOCKED_P370_DELETE_PROTECT_OR_RECOVERDB_DRIFT"
)
P370_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL = "BLOCKED_P370_SLOT1_VAULT_WRITE_FIREWALL"
P370_BLOCKED_PERSISTENT_OVERLAY_ESCAPE = "BLOCKED_P370_PERSISTENT_OVERLAY_ESCAPE"
P370_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT = "BLOCKED_P370_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P370_PILLAR_68A_SCENARIO_IDS = (
    "p370_68a_01_allow_still_drive_hi_plus_10fps_f11_lock_bracket_interval_and_efcs_reset_resist",
    "p370_68a_02_allow_electronic_shutter_5lockout_longexp_nr_1s_highiso_nr_raw_untouched_and_fx6_ns_apr",
    "p370_68a_03_reject_dormant_focus_bracket_fx3_fx6_10sec_10images_dro_under_hlg_or_fx6_still_drive",
    "p370_68a_04_reject_dormant_shutter_auto_1_320_xsync_spoof_or_efcs_wiped_by_camera_settings_reset",
    "p370_68a_05_reject_electronic_5lockout_bypass_dormant_high_iso_nr_or_arw_nr_mutation_drift",
    "p370_68a_06_reject_slot1_vault_write_overlay_escape_or_backup_bin_h0_h3_drift",
)
P370_PILLAR_68B_SCENARIO_IDS = (
    "p370_68b_01_allow_creative_look_st_custom6_asymmetric_0_9_clarity_1_5_fineness_and_bw_sat_lock",
    "p370_68b_02_allow_pp_log_hlg_iauto_override_display_media_info_40k_and_fx6_base_look_contrast",
    "p370_68b_03_reject_negative_clarity_saturation_on_bw_movie_fineness_or_pp_log_bypass_drift",
    "p370_68b_04_reject_dormant_soft_skin_effect_on_fx3_or_fx6_and_delete_confirm_reset_wipe",
    "p370_68b_05_reject_slot1_delete_protect_fsys_chmod_or_recover_image_db_avf_info_bypass",
    "p370_68b_06_reject_fx6_restore_media_a_slot1_write_overlay_escape_or_backup_bin_h0_h3_drift",
)

MASTER_68_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_67_PILLAR_SPECS + (
    (
        68,
        "pillar68_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault",
        "Phase 370",
        "realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier",
    ),
)
MASTER_68_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_68_PILLAR_SPECS)
MASTER_68_PILLAR_COUNT = len(MASTER_68_PILLAR_IDS)


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
    return bool(is_forced_clean_room() or os.environ.get(P370_ENV_CLEAN_ROOM_TEST) == "1")


def _donor_inspect_budget_seconds() -> float:
    return (
        P370_DONOR_INSPECT_CI_BUDGET_SECONDS
        if os.environ.get("CI")
        else P370_DONOR_INSPECT_BUDGET_SECONDS
    )


def _is_tmpfs_path(path: str) -> bool:
    norm = posixpath.normpath(path)
    return norm == "/tmp" or norm.startswith("/tmp/")


def _targets_persistent_emmc(path: str) -> bool:
    norm = posixpath.normpath(path)
    return any(
        norm == t or norm.startswith(f"{t}/")
        for t in P370_FORBIDDEN_PERSISTENT_TARGETS
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
# Pure Deterministic Ground-Truth State Evaluators (68A & 68B)
# ---------------------------------------------------------------------------


def compute_expected_drive_focusbracket_shutter_efcs_nr_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    exposure_mode: str,
    still_file_format: str,
    raw_file_type: str,
    hlg_still_image: str,
    flash_active: bool,
    aperture_f_number: float,
    # `[Drive Mode]` & Dormant `[Focus Bracket]`
    drive_mode: str,
    cont_shoot_speed: str,
    self_timer_single_sec: str,
    self_timer_cont_option: str,
    bracket_step_ev: float,
    bracket_img_count: int,
    wb_bracket_mode: str,
    dro_bracket_mode: str,
    bracket_selftimer: str,
    bracket_order: str,
    interval_shoot_active: bool,
    interval_output_is_movie: bool,
    shutter_type_in_interval: str,
    focus_bracket_requested: bool,
    # `[Shutter Type]`, X-Sync, `[e-Front Curtain Shut.]`, `[Long Exposure NR]`, `[High ISO NR]`
    shutter_type: str,
    silent_mode: str,
    requested_flash_sync_reciprocal: int,
    efcs_enabled: str,
    bulb_requested: bool,
    anti_flicker_shoot_requested: bool,
    shutter_speed_seconds: float,
    long_exposure_nr: str,
    high_iso_nr: str,
    fx6_noise_suppression: str,
    fx6_apr_lens_cap_covered: bool,
    # Reset & Vault
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute exact Wave-66 Pillar 68A expected state (Drive Mode 10fps / Dormant Focus Bracket /
    2-Option Shutter Type / 1/250 s X-Sync / EFCS Reset-Resistance / Long Exposure & High ISO NR)."""
    is_fx3 = camera_model == P370_FX3_MODEL_NAME
    is_fx6 = camera_model == P370_FX6_DONOR_MODEL_NAME

    # 1. `[Drive Mode]` & Dormant `[Focus Bracket]`
    drive_mode_errno: Optional[int] = None
    focus_bracket_errno: Optional[int] = P370_EOPNOTSUPP_ERRNO if focus_bracket_requested else None

    if is_fx6:
        if (
            drive_mode != "None"
            or focus_bracket_requested
            or interval_shoot_active
        ):
            drive_mode_errno = P370_EOPNOTSUPP_ERRNO
        effective_drive_mode = "None"
        nominal_cont_fps = 0.0
        drive_rate_reduced = False
        live_view_realtime_refresh = True
        focus_locked_first_frame = False
    else:
        still_domain_ok = shooting_domain == "Still"
        if drive_mode == "Focus Bracket" or focus_bracket_requested:
            drive_mode_errno = P370_EOPNOTSUPP_ERRNO
            focus_bracket_errno = P370_EOPNOTSUPP_ERRNO
            effective_drive_mode = P370_FX3_DRIVE_MODE_DEFAULT
        elif drive_mode not in P370_FX3_ACTIVE_DRIVE_MODES:
            drive_mode_errno = P370_EOPNOTSUPP_ERRNO
            effective_drive_mode = P370_FX3_DRIVE_MODE_DEFAULT
        elif not still_domain_ok and drive_mode != P370_FX3_DRIVE_MODE_DEFAULT:
            drive_mode_errno = P370_EOPNOTSUPP_ERRNO
            effective_drive_mode = P370_FX3_DRIVE_MODE_DEFAULT
        elif drive_mode == "Self-timer(Cont)" and (
            self_timer_cont_option in P370_FX3_SELF_TIMER_CONT_DORMANT_OPTIONS
            or self_timer_cont_option not in P370_FX3_SELF_TIMER_CONT_ACTIVE_OPTIONS
        ):
            drive_mode_errno = P370_EOPNOTSUPP_ERRNO
            effective_drive_mode = P370_FX3_DRIVE_MODE_DEFAULT
        elif drive_mode in ("Cont. Bracket", "Single Bracket") and (
            exposure_mode == "iAuto"
            or bracket_img_count not in P370_FX3_EXP_BRACKET_STEPS_COUNTS.get(bracket_step_ev, ())
        ):
            drive_mode_errno = P370_EOPNOTSUPP_ERRNO
            effective_drive_mode = P370_FX3_DRIVE_MODE_DEFAULT
        elif drive_mode == "DRO Bracket" and hlg_still_image == "On":
            drive_mode_errno = P370_EOPNOTSUPP_ERRNO
            effective_drive_mode = P370_FX3_DRIVE_MODE_DEFAULT
        elif interval_shoot_active and (not still_domain_ok or interval_output_is_movie):
            drive_mode_errno = P370_EOPNOTSUPP_ERRNO
            effective_drive_mode = P370_FX3_DRIVE_MODE_DEFAULT
        else:
            effective_drive_mode = drive_mode

        if effective_drive_mode == "Cont. Shooting":
            nominal_cont_fps = P370_FX3_CONT_SHOOT_SPEEDS_FPS.get(cont_shoot_speed, 0.0)
            uncompressed_raw = ("RAW" in still_file_format) and raw_file_type == "Uncompressed"
            drive_rate_reduced = uncompressed_raw or flash_active
            live_view_realtime_refresh = cont_shoot_speed != "Hi+"
            focus_locked_first_frame = (
                aperture_f_number > P370_FX3_CONT_FIRST_FRAME_AF_LOCK_F_THRESHOLD
                and cont_shoot_speed in ("Hi+", "Hi", "Mid")
            )
        else:
            nominal_cont_fps = 0.0
            drive_rate_reduced = False
            live_view_realtime_refresh = True
            focus_locked_first_frame = False

    # 2. `[Shutter Type]` (Strictly 2 Options, No `Auto`), `1/250 s` X-Sync, `[e-Front Curtain Shut.]`, NR
    shutter_errno: Optional[int] = None
    xsync_errno: Optional[int] = None
    nr_errno: Optional[int] = None
    arw_raw_untouched = True
    electronic_or_silent_active = bool(
        is_fx3 and (shutter_type == "Electronic Shutter" or silent_mode == "On")
    )

    if is_fx6:
        if shutter_type != "None" or efcs_enabled != "None" or requested_flash_sync_reciprocal > 0:
            shutter_errno = P370_EOPNOTSUPP_ERRNO
        if long_exposure_nr != "None" or high_iso_nr != "None":
            nr_errno = P370_EOPNOTSUPP_ERRNO
        if fx6_noise_suppression not in P370_FX6_NOISE_SUPPRESSION_MODES:
            nr_errno = P370_EOPNOTSUPP_ERRNO
        effective_shutter_type = "None"
        effective_efcs = "None"
        effective_long_exp_nr = "None"
        effective_high_iso_nr = "None"
        long_exp_nr_subtraction_active = False
        locked_features_under_electronic: Tuple[str, ...] = ()
    else:
        if shutter_type in P370_FX3_DORMANT_SHUTTER_TYPES or shutter_type not in P370_FX3_ACTIVE_SHUTTER_TYPES:
            shutter_errno = P370_EOPNOTSUPP_ERRNO
            effective_shutter_type = P370_FX3_SHUTTER_TYPE_DEFAULT
        else:
            effective_shutter_type = shutter_type

        electronic_or_silent_active = bool(
            effective_shutter_type == "Electronic Shutter" or silent_mode == "On"
        )
        locked_features_under_electronic = (
            P370_FX3_ELECTRONIC_OR_SILENT_LOCKED_FEATURES if electronic_or_silent_active else ()
        )

        # Mechanical Flash X-Sync ceiling strictly 1/250 s
        if requested_flash_sync_reciprocal > P370_FX3_FLASH_XSYNC_CEILING_RECIPROCAL:
            xsync_errno = P370_EOPNOTSUPP_ERRNO
        if electronic_or_silent_active and (flash_active or bulb_requested or anti_flicker_shoot_requested):
            shutter_errno = P370_EOPNOTSUPP_ERRNO

        # `[e-Front Curtain Shut.]` locked out in Electronic Shutter or Silent Mode = On
        if electronic_or_silent_active and efcs_enabled == "On":
            effective_efcs = "Off"
        else:
            effective_efcs = efcs_enabled

        # `[Long Exposure NR]` (`>= 1.0 s`, disabled in Electronic/Silent/Cont. Shooting/Cont. Bracket; locked On in iAuto)
        long_exp_nr_locked_off = (
            electronic_or_silent_active
            or effective_drive_mode in ("Cont. Shooting", "Cont. Bracket")
        )
        if exposure_mode == "iAuto" and long_exposure_nr == "Off":
            nr_errno = P370_EOPNOTSUPP_ERRNO
            effective_long_exp_nr = "On"
        elif long_exposure_nr == "On" and long_exp_nr_locked_off:
            nr_errno = P370_EOPNOTSUPP_ERRNO
            effective_long_exp_nr = "Off"
        else:
            effective_long_exp_nr = long_exposure_nr

        long_exp_nr_subtraction_active = bool(
            effective_long_exp_nr == "On"
            and not long_exp_nr_locked_off
            and shutter_speed_seconds >= P370_FX3_LONG_EXP_NR_MIN_SHUTTER_SECONDS
        )

        # `[High ISO NR]` (`Normal` / `Low` / `Off`, reject dormant `HIGH`, unavailable in pure `RAW`, fixed `Normal` in `iAuto`)
        if high_iso_nr in P370_FX3_HIGH_ISO_NR_DORMANT_LEVELS or high_iso_nr not in P370_FX3_HIGH_ISO_NR_ACTIVE_LEVELS:
            nr_errno = P370_EOPNOTSUPP_ERRNO
            effective_high_iso_nr = P370_FX3_HIGH_ISO_NR_DEFAULT
        elif still_file_format == "RAW":
            effective_high_iso_nr = "Off"
        elif exposure_mode == "iAuto":
            effective_high_iso_nr = "Normal"
        else:
            effective_high_iso_nr = high_iso_nr

    # 3. `[Camera Settings Reset]` vs `[Initialize]` Persistence Boundaries
    if is_fx6:
        post_drive_mode = "None"
        post_shutter_type = "None"
        post_shutter_type_in_interval = "None"
        post_efcs = "None"
        post_long_exposure_nr = "None"
        post_high_iso_nr = "None"
    elif reset_action == "Initialize":
        post_drive_mode = P370_FX3_DRIVE_MODE_DEFAULT
        post_shutter_type = P370_FX3_SHUTTER_TYPE_DEFAULT
        post_shutter_type_in_interval = P370_FX3_INTERVAL_SHUTTER_DEFAULT
        post_efcs = P370_FX3_EFCS_DEFAULT
        post_long_exposure_nr = P370_FX3_LONG_EXP_NR_DEFAULT
        post_high_iso_nr = P370_FX3_HIGH_ISO_NR_DEFAULT
    elif reset_action == "Camera Settings Reset":
        post_drive_mode = P370_FX3_DRIVE_MODE_DEFAULT  # Can be reset!
        post_shutter_type = P370_FX3_SHUTTER_TYPE_DEFAULT  # Can be reset!
        post_shutter_type_in_interval = P370_FX3_INTERVAL_SHUTTER_DEFAULT  # Can be reset!
        post_efcs = efcs_enabled  # Not available! Resists Camera Settings Reset!
        post_long_exposure_nr = P370_FX3_LONG_EXP_NR_DEFAULT  # Can be reset!
        post_high_iso_nr = P370_FX3_HIGH_ISO_NR_DEFAULT  # Can be reset!
    else:
        post_drive_mode = effective_drive_mode
        post_shutter_type = effective_shutter_type
        post_shutter_type_in_interval = shutter_type_in_interval
        post_efcs = efcs_enabled
        post_long_exposure_nr = effective_long_exp_nr
        post_high_iso_nr = effective_high_iso_nr

    write_blocked_erofs = (
        requested_vault_slot == 1
        and slot1_holds_tier0_vault
        and requested_vault_action in P370_WRITE_MUTATING_VAULT_ACTIONS
    )
    vault_action_allowed = not write_blocked_erofs and (
        requested_vault_action in ("NONE", "READ_ONLY_AUDIT", "DISPLAY_MEDIA_INFO_READ_ONLY")
    )
    vault_firewall_errno: Optional[str] = "EROFS" if write_blocked_erofs else None

    return {
        "drive_mode_errno": drive_mode_errno,
        "focus_bracket_errno": focus_bracket_errno,
        "effective_drive_mode": effective_drive_mode,
        "nominal_cont_fps": nominal_cont_fps,
        "drive_rate_reduced": drive_rate_reduced,
        "live_view_realtime_refresh": live_view_realtime_refresh,
        "focus_locked_first_frame": focus_locked_first_frame,
        "shutter_errno": shutter_errno,
        "xsync_errno": xsync_errno,
        "nr_errno": nr_errno,
        "effective_shutter_type": effective_shutter_type,
        "electronic_or_silent_active": electronic_or_silent_active,
        "locked_features_under_electronic": locked_features_under_electronic,
        "effective_efcs": effective_efcs,
        "effective_long_exp_nr": effective_long_exp_nr,
        "long_exp_nr_subtraction_active": long_exp_nr_subtraction_active,
        "effective_high_iso_nr": effective_high_iso_nr,
        "arw_raw_untouched": arw_raw_untouched,
        "post_drive_mode": post_drive_mode,
        "post_shutter_type": post_shutter_type,
        "post_shutter_type_in_interval": post_shutter_type_in_interval,
        "post_efcs": post_efcs,
        "post_long_exposure_nr": post_long_exposure_nr,
        "post_high_iso_nr": post_high_iso_nr,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


def compute_expected_creativelook_softskin_recoverdb_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    exposure_mode: str,
    picture_profile: str,
    log_shooting_mode: str,
    hlg_still_image: str,
    # `[Creative Look]` 10 Presets + 6 Custom + 8 Asymmetric Params & Dormant `[Soft Skin Effect]`
    creative_look: str,
    cl_contrast: int,
    cl_highlights: int,
    cl_shadows: int,
    cl_fade: int,
    cl_saturation: int,
    cl_sharpness: int,
    cl_sharpness_range: int,
    cl_clarity: int,
    attempt_edit_saturation_on_bw_se: bool,
    attempt_edit_sharpness_range_in_movie: bool,
    soft_skin_effect_requested: bool,
    fx6_base_look_mode: str,
    # Playback `[Delete]` / `[Delete confirm.]` / `[Delete pressing twice]` / `[Protect]` / `[Recover Image DB]` / `[Display Media Info.]`
    selected_playback_slot: int,
    delete_scope: str,
    delete_item_protected: bool,
    delete_has_coupled_proxy: bool,
    delete_confirm_mode: str,
    delete_pressing_twice: str,
    protect_scope: str,
    protect_has_coupled_proxy: bool,
    copy_preserves_protect: bool,
    recover_image_db_requested: bool,
    battery_sufficient_for_recover_db: bool,
    display_media_info_still_cap: int,
    # Reset & Tier-0 Slot-1 Vault
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute exact Wave-66 Pillar 68B expected state (`Creative Look` 10 presets + 6 Custom + 8 asymmetric params,
    Dormant `Soft Skin Effect`, and `Delete`/`Protect`/`Recover Image DB` Slot-1 Tier-0 `EROFS=30` Firewall)."""
    is_fx3 = camera_model == P370_FX3_MODEL_NAME
    is_fx6 = camera_model == P370_FX6_DONOR_MODEL_NAME

    # 1. `[Creative Look]` 10 Presets + 6 Custom + 8 Asymmetric Params + Dormant `[Soft Skin Effect]`
    creative_look_errno: Optional[int] = None
    soft_skin_errno: Optional[int] = P370_EOPNOTSUPP_ERRNO if soft_skin_effect_requested else None

    if is_fx6:
        if creative_look != "None" or soft_skin_effect_requested:
            creative_look_errno = P370_EOPNOTSUPP_ERRNO
        creative_look_forced_disabled = True
        effective_creative_look = "None"
        saturation_locked = True
        sharpness_range_locked = True
    else:
        overridden_dash = (
            picture_profile != "Off"
            or log_shooting_mode != "Off"
            or hlg_still_image == "On"
            or exposure_mode == "iAuto"
        )
        creative_look_forced_disabled = overridden_dash

        # Validate 8 asymmetric parameter ranges
        bounds = P370_FX3_CREATIVE_LOOK_PARAM_BOUNDS
        param_vals = {
            "contrast": cl_contrast,
            "highlights": cl_highlights,
            "shadows": cl_shadows,
            "fade": cl_fade,
            "saturation": cl_saturation,
            "sharpness": cl_sharpness,
            "sharpness_range": cl_sharpness_range,
            "clarity": cl_clarity,
        }
        bounds_ok = all(bounds[k][0] <= v <= bounds[k][1] for k, v in param_vals.items())
        slot_valid = creative_look in P370_FX3_CREATIVE_LOOK_ALL_SLOTS

        saturation_locked = creative_look in P370_FX3_CREATIVE_LOOK_SATURATION_LOCKED_PRESETS or overridden_dash
        sharpness_range_locked = shooting_domain in ("Movie", "S&Q") or overridden_dash

        if not slot_valid or not bounds_ok:
            creative_look_errno = P370_EINVAL_ERRNO if slot_valid else P370_EOPNOTSUPP_ERRNO
            effective_creative_look = "[-]" if overridden_dash else P370_FX3_CREATIVE_LOOK_DEFAULT
        elif overridden_dash and creative_look != "[-]":
            # In overridden modes Creative Look is forced fixed to `[-]`
            effective_creative_look = "[-]"
            if creative_look != P370_FX3_CREATIVE_LOOK_DEFAULT:
                creative_look_errno = P370_EOPNOTSUPP_ERRNO
        elif attempt_edit_saturation_on_bw_se and saturation_locked:
            creative_look_errno = P370_EOPNOTSUPP_ERRNO
            effective_creative_look = creative_look
        elif attempt_edit_sharpness_range_in_movie and sharpness_range_locked:
            creative_look_errno = P370_EOPNOTSUPP_ERRNO
            effective_creative_look = creative_look
        else:
            effective_creative_look = "[-]" if overridden_dash else creative_look

    # 2. Playback `[Delete]` / `[Delete confirm.]` / `[Delete pressing twice]` / `[Protect]` / `[Recover Image DB]`
    playback_action_errno: Optional[int] = None
    delete_coupled_proxy = bool(is_fx3 and delete_scope != "None" and delete_has_coupled_proxy and not delete_item_protected)
    delete_protected_skipped = bool(is_fx3 and delete_scope != "None" and delete_item_protected)
    protect_coupled_proxy = bool(is_fx3 and protect_scope != "None" and protect_has_coupled_proxy)
    quick_delete_hazard = bool(
        is_fx3 and (delete_confirm_mode == '"Delete" first' or delete_pressing_twice == "On")
    )

    recover_db_avf_info_rebuilt = False
    recover_db_ftp_history_wiped = False
    if recover_image_db_requested:
        if not battery_sufficient_for_recover_db:
            playback_action_errno = P370_EBUSY_ERRNO
        else:
            recover_db_avf_info_rebuilt = True
            recover_db_ftp_history_wiped = True

    media_info_still_cap_ok = (
        0 <= display_media_info_still_cap <= P370_FX3_DISPLAY_MEDIA_INFO_STILL_CAP
    )

    # 3. `[Camera Settings Reset]` vs `[Initialize]` Persistence
    if is_fx6:
        post_creative_look = "None"
        post_delete_confirm_mode = "None"
        post_delete_pressing_twice = "None"
        post_image_db_recovered_persisted = True
    elif reset_action == "Initialize":
        post_creative_look = "[-]" if creative_look_forced_disabled else P370_FX3_CREATIVE_LOOK_DEFAULT
        post_delete_confirm_mode = P370_FX3_DELETE_CONFIRM_DEFAULT
        post_delete_pressing_twice = "Off"
        post_image_db_recovered_persisted = True  # Recover Image DB survives BOTH Reset & Initialize!
    elif reset_action == "Camera Settings Reset":
        post_creative_look = "[-]" if creative_look_forced_disabled else P370_FX3_CREATIVE_LOOK_DEFAULT  # Can be reset!
        post_delete_confirm_mode = delete_confirm_mode  # Resists Reset!
        post_delete_pressing_twice = delete_pressing_twice  # Resists Reset!
        post_image_db_recovered_persisted = True  # Resists Reset!
    else:
        post_creative_look = effective_creative_look
        post_delete_confirm_mode = delete_confirm_mode
        post_delete_pressing_twice = delete_pressing_twice
        post_image_db_recovered_persisted = True

    # 4. Tier-0 `Slot 1 EROFS=30` Vault Firewall
    targets_slot1_or_media_a = (requested_vault_slot == 1) or (
        requested_vault_action == "FX6_RESTORE_MEDIA_A"
    )
    write_blocked_erofs = (
        targets_slot1_or_media_a
        and slot1_holds_tier0_vault
        and requested_vault_action in P370_WRITE_MUTATING_VAULT_ACTIONS
    )
    vault_action_allowed = not write_blocked_erofs and (
        requested_vault_action in ("NONE", "READ_ONLY_AUDIT", "DISPLAY_MEDIA_INFO_READ_ONLY")
    )
    vault_firewall_errno: Optional[str] = "EROFS" if write_blocked_erofs else None

    return {
        "creative_look_errno": creative_look_errno,
        "soft_skin_errno": soft_skin_errno,
        "creative_look_forced_disabled": creative_look_forced_disabled,
        "effective_creative_look": effective_creative_look,
        "saturation_locked": saturation_locked,
        "sharpness_range_locked": sharpness_range_locked,
        "playback_action_errno": playback_action_errno,
        "delete_coupled_proxy": delete_coupled_proxy,
        "delete_protected_skipped": delete_protected_skipped,
        "protect_coupled_proxy": protect_coupled_proxy,
        "quick_delete_hazard": quick_delete_hazard,
        "recover_db_avf_info_rebuilt": recover_db_avf_info_rebuilt,
        "recover_db_ftp_history_wiped": recover_db_ftp_history_wiped,
        "media_info_still_cap_ok": media_info_still_cap_ok,
        "post_creative_look": post_creative_look,
        "post_delete_confirm_mode": post_delete_confirm_mode,
        "post_delete_pressing_twice": post_delete_pressing_twice,
        "post_image_db_recovered_persisted": post_image_db_recovered_persisted,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


# ---------------------------------------------------------------------------
# Bounded Read-Only Donor Inspection (`O_RDONLY | O_NOFOLLOW | O_NONBLOCK`, 17 Donors)
# ---------------------------------------------------------------------------


def _iter_work_roots() -> Tuple[Optional[Path], ...]:
    return _fx3_files.iter_donor_work_roots()


def _resolve_phase370_donor_path(
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
    max_full_bytes: int = P370_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    try:
        resolved = _resolve_phase370_donor_path(relpath)
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
        hdr = os.pread(fd, min(P370_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase370_donors() -> Tuple["Phase370DonorArtifactDigest", ...]:
    specs = (
        ("fx3_appfw_702_so", P370_DONOR_FX3_APPFW_702_RELPATH, P370_PINNED_FX3_APPFW_702_BYTES, P370_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P370_PINNED_FX3_APPFW_702_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702"),
        ("fx3_backup_bin", P370_DONOR_FX3_BACKUP_BIN_RELPATH, P370_PINNED_FX3_BACKUP_BIN_BYTES, P370_PINNED_FX3_BACKUP_BIN_BYTES, "FULL_SHA256", P370_PINNED_FX3_BACKUP_BIN_SHA256, "SYNTHETIC_BK4_ILME_FX3"),
        ("fx6_appfw_601_so", P370_DONOR_FX6_APPFW_601_RELPATH, P370_PINNED_FX6_APPFW_601_BYTES, P370_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P370_PINNED_FX6_APPFW_601_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601"),
        ("fx3_uxc_en_f", P370_DONOR_FX3_UXC_EN_F_RELPATH, P370_PINNED_FX3_UXC_EN_F_BYTES, P370_PINNED_FX3_UXC_EN_F_BYTES, "FULL_SHA256", P370_PINNED_FX3_UXC_EN_F_SHA256, "SYNTHETIC_UXC7_FX3_EN_F"),
        ("fx3_uxc_sc_f", P370_DONOR_FX3_UXC_SC_F_RELPATH, P370_PINNED_FX3_UXC_SC_F_BYTES, P370_PINNED_FX3_UXC_SC_F_BYTES, "FULL_SHA256", P370_PINNED_FX3_UXC_SC_F_SHA256, "SYNTHETIC_UXC7_FX3_SC_F"),
        ("fx3_uxc_tc_f", P370_DONOR_FX3_UXC_TC_F_RELPATH, P370_PINNED_FX3_UXC_TC_F_BYTES, P370_PINNED_FX3_UXC_TC_F_BYTES, "FULL_SHA256", P370_PINNED_FX3_UXC_TC_F_SHA256, "SYNTHETIC_UXC7_FX3_TC_F"),
        ("fx3_uxc_ja_f", P370_DONOR_FX3_UXC_JA_F_RELPATH, P370_PINNED_FX3_UXC_JA_F_BYTES, P370_PINNED_FX3_UXC_JA_F_BYTES, "FULL_SHA256", P370_PINNED_FX3_UXC_JA_F_SHA256, "SYNTHETIC_UXC7_FX3_JA_F"),
        ("fx3_uxc_en", P370_DONOR_FX3_UXC_EN_RELPATH, P370_PINNED_FX3_UXC_EN_BYTES, P370_PINNED_FX3_UXC_EN_BYTES, "FULL_SHA256", P370_PINNED_FX3_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX3_EN"),
        ("fx3_uxc_sc", P370_DONOR_FX3_UXC_SC_RELPATH, P370_PINNED_FX3_UXC_SC_BYTES, P370_PINNED_FX3_UXC_SC_BYTES, "FULL_SHA256", P370_PINNED_FX3_UXC_SC_SHA256, "SYNTHETIC_UXC7_FX3_SC"),
        ("fx3_uxc_tc", P370_DONOR_FX3_UXC_TC_RELPATH, P370_PINNED_FX3_UXC_TC_BYTES, P370_PINNED_FX3_UXC_TC_BYTES, "FULL_SHA256", P370_PINNED_FX3_UXC_TC_SHA256, "SYNTHETIC_UXC7_FX3_TC"),
        ("fx3_uxc_ja", P370_DONOR_FX3_UXC_JA_RELPATH, P370_PINNED_FX3_UXC_JA_BYTES, P370_PINNED_FX3_UXC_JA_BYTES, "FULL_SHA256", P370_PINNED_FX3_UXC_JA_SHA256, "SYNTHETIC_UXC7_FX3_JA"),
        ("fx3_uxc_en_g", P370_DONOR_FX3_UXC_EN_G_RELPATH, P370_PINNED_FX3_UXC_EN_G_BYTES, P370_PINNED_FX3_UXC_EN_G_BYTES, "FULL_SHA256", P370_PINNED_FX3_UXC_EN_G_SHA256, "SYNTHETIC_UXC7_FX3_EN_G"),
        ("fx3_uxc_sc_g", P370_DONOR_FX3_UXC_SC_G_RELPATH, P370_PINNED_FX3_UXC_SC_G_BYTES, P370_PINNED_FX3_UXC_SC_G_BYTES, "FULL_SHA256", P370_PINNED_FX3_UXC_SC_G_SHA256, "SYNTHETIC_UXC7_FX3_SC_G"),
        ("fx3_uxc_tc_g", P370_DONOR_FX3_UXC_TC_G_RELPATH, P370_PINNED_FX3_UXC_TC_G_BYTES, P370_PINNED_FX3_UXC_TC_G_BYTES, "FULL_SHA256", P370_PINNED_FX3_UXC_TC_G_SHA256, "SYNTHETIC_UXC7_FX3_TC_G"),
        ("fx3_uxc_ja_g", P370_DONOR_FX3_UXC_JA_G_RELPATH, P370_PINNED_FX3_UXC_JA_G_BYTES, P370_PINNED_FX3_UXC_JA_G_BYTES, "FULL_SHA256", P370_PINNED_FX3_UXC_JA_G_SHA256, "SYNTHETIC_UXC7_FX3_JA_G"),
        ("fx6_uxc_en", P370_DONOR_FX6_UXC_EN_RELPATH, P370_PINNED_FX6_UXC_EN_BYTES, P370_PINNED_FX6_UXC_EN_BYTES, "FULL_SHA256", P370_PINNED_FX6_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX6_EN"),
        ("fx6_uxc_en_2", P370_DONOR_FX6_UXC_EN_2_RELPATH, P370_PINNED_FX6_UXC_EN_2_BYTES, P370_PINNED_FX6_UXC_EN_2_BYTES, "FULL_SHA256", P370_PINNED_FX6_UXC_EN_2_SHA256, "SYNTHETIC_UXC7_FX6_EN_2"),
    )
    return tuple(
        Phase370DonorArtifactDigest(
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


def inspect_phase370_donors_readonly(
    force_clean_room: Optional[bool] = None,
) -> "Phase370DonorSnapshot":
    """Inspect Wave-66 FX3 (`14` donors) & FX6 (`3` donors) strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase370_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase370DonorSnapshot(
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
        ("fx3_appfw_702_so", P370_DONOR_FX3_APPFW_702_RELPATH, P370_PINNED_FX3_APPFW_702_BYTES, P370_PINNED_FX3_APPFW_702_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702")),
        ("fx3_backup_bin", P370_DONOR_FX3_BACKUP_BIN_RELPATH, P370_PINNED_FX3_BACKUP_BIN_BYTES, P370_PINNED_FX3_BACKUP_BIN_SHA256, lambda d: _check_bk4_backup(d, "ILME_FX3")),
        ("fx6_appfw_601_so", P370_DONOR_FX6_APPFW_601_RELPATH, P370_PINNED_FX6_APPFW_601_BYTES, P370_PINNED_FX6_APPFW_601_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601")),
        ("fx3_uxc_en_f", P370_DONOR_FX3_UXC_EN_F_RELPATH, P370_PINNED_FX3_UXC_EN_F_BYTES, P370_PINNED_FX3_UXC_EN_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_F")),
        ("fx3_uxc_sc_f", P370_DONOR_FX3_UXC_SC_F_RELPATH, P370_PINNED_FX3_UXC_SC_F_BYTES, P370_PINNED_FX3_UXC_SC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_F")),
        ("fx3_uxc_tc_f", P370_DONOR_FX3_UXC_TC_F_RELPATH, P370_PINNED_FX3_UXC_TC_F_BYTES, P370_PINNED_FX3_UXC_TC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_F")),
        ("fx3_uxc_ja_f", P370_DONOR_FX3_UXC_JA_F_RELPATH, P370_PINNED_FX3_UXC_JA_F_BYTES, P370_PINNED_FX3_UXC_JA_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_F")),
        ("fx3_uxc_en", P370_DONOR_FX3_UXC_EN_RELPATH, P370_PINNED_FX3_UXC_EN_BYTES, P370_PINNED_FX3_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN")),
        ("fx3_uxc_sc", P370_DONOR_FX3_UXC_SC_RELPATH, P370_PINNED_FX3_UXC_SC_BYTES, P370_PINNED_FX3_UXC_SC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC")),
        ("fx3_uxc_tc", P370_DONOR_FX3_UXC_TC_RELPATH, P370_PINNED_FX3_UXC_TC_BYTES, P370_PINNED_FX3_UXC_TC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC")),
        ("fx3_uxc_ja", P370_DONOR_FX3_UXC_JA_RELPATH, P370_PINNED_FX3_UXC_JA_BYTES, P370_PINNED_FX3_UXC_JA_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA")),
        ("fx3_uxc_en_g", P370_DONOR_FX3_UXC_EN_G_RELPATH, P370_PINNED_FX3_UXC_EN_G_BYTES, P370_PINNED_FX3_UXC_EN_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_G")),
        ("fx3_uxc_sc_g", P370_DONOR_FX3_UXC_SC_G_RELPATH, P370_PINNED_FX3_UXC_SC_G_BYTES, P370_PINNED_FX3_UXC_SC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_G")),
        ("fx3_uxc_tc_g", P370_DONOR_FX3_UXC_TC_G_RELPATH, P370_PINNED_FX3_UXC_TC_G_BYTES, P370_PINNED_FX3_UXC_TC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_G")),
        ("fx3_uxc_ja_g", P370_DONOR_FX3_UXC_JA_G_RELPATH, P370_PINNED_FX3_UXC_JA_G_BYTES, P370_PINNED_FX3_UXC_JA_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_G")),
        ("fx6_uxc_en", P370_DONOR_FX6_UXC_EN_RELPATH, P370_PINNED_FX6_UXC_EN_BYTES, P370_PINNED_FX6_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN")),
        ("fx6_uxc_en_2", P370_DONOR_FX6_UXC_EN_2_RELPATH, P370_PINNED_FX6_UXC_EN_2_BYTES, P370_PINNED_FX6_UXC_EN_2_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN_2")),
    )

    def _probe_one(spec: Tuple[str, str, int, str, Any]) -> Optional[Phase370DonorArtifactDigest]:
        aid, relpath, expected_bytes, expected_sha, marker_fn = spec
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            return None
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        return Phase370DonorArtifactDigest(
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
        artifacts = _synthetic_phase370_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase370DonorSnapshot(
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
    return Phase370DonorSnapshot(
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
# Frozen Dataclasses (Specs, Reports, Suites & 68-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase370DonorArtifactDigest:
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
class Phase370DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_2_0s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase370DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DriveModeFocusBracketShutterEfcsNrVaultSpec:
    camera_model: str
    fw_version: str
    shooting_domain: str
    exposure_mode: str
    still_file_format: str
    raw_file_type: str
    hlg_still_image: str
    flash_active: bool
    aperture_f_number: float
    # Still `[Drive Mode]` 10fps & Dormant `[Focus Bracket]`
    drive_mode: str
    cont_shoot_speed: str
    self_timer_single_sec: str
    self_timer_cont_option: str
    bracket_step_ev: float
    bracket_img_count: int
    wb_bracket_mode: str
    dro_bracket_mode: str
    bracket_selftimer: str
    bracket_order: str
    interval_shoot_active: bool
    interval_output_is_movie: bool
    shutter_type_in_interval: str
    focus_bracket_requested: bool
    reported_drive_mode_errno: Optional[int]
    reported_focus_bracket_errno: Optional[int]
    reported_effective_drive_mode: str
    reported_nominal_cont_fps: float
    reported_drive_rate_reduced: bool
    reported_live_view_realtime_refresh: bool
    reported_focus_locked_first_frame: bool
    # `[Shutter Type]` (2-Option No Auto), `1/250 s` X-Sync, `[e-Front Curtain Shut.]`, NR
    shutter_type: str
    silent_mode: str
    requested_flash_sync_reciprocal: int
    efcs_enabled: str
    bulb_requested: bool
    anti_flicker_shoot_requested: bool
    shutter_speed_seconds: float
    long_exposure_nr: str
    high_iso_nr: str
    fx6_noise_suppression: str
    fx6_apr_lens_cap_covered: bool
    reported_shutter_errno: Optional[int]
    reported_xsync_errno: Optional[int]
    reported_nr_errno: Optional[int]
    reported_effective_shutter_type: str
    reported_electronic_or_silent_active: bool
    reported_locked_features_under_electronic: Tuple[str, ...]
    reported_effective_efcs: str
    reported_effective_long_exp_nr: str
    reported_long_exp_nr_subtraction_active: bool
    reported_effective_high_iso_nr: str
    reported_arw_raw_untouched: bool
    # Reset boundaries (`Drive Mode` / `Shutter Type` / `Interval Shutter` / `NR` Can be reset; `EFCS` Not available!)
    reset_action: str
    post_drive_mode: str
    post_shutter_type: str
    post_shutter_type_in_interval: str
    post_efcs: str
    post_long_exposure_nr: str
    post_high_iso_nr: str
    # Vault & Overlay & H0==H3
    requested_vault_slot: int
    slot1_holds_tier0_vault: bool
    requested_vault_action: str
    reported_vault_action_allowed: bool
    vault_firewall_errno: Optional[str]
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
    drive_mode_or_dormant_focus_bracket_drift_events: int
    shutter_2opt_xsync_efcs_or_nr_drift_events: int


@dataclass(frozen=True)
class DriveModeFocusBracketShutterEfcsNrVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    drive_mode_and_dormant_focus_bracket_verified: bool
    shutter_2opt_xsync_efcs_nr_verified: bool
    slot1_vault_and_h0_h3_verified: bool
    matrix_states_checked: int
    drive_mode_or_dormant_focus_bracket_drift_events: int
    shutter_2opt_xsync_efcs_or_nr_drift_events: int
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
class CreativeLookSoftSkinDeleteProtectRecoverDbVaultSpec:
    camera_model: str
    fw_version: str
    shooting_domain: str
    exposure_mode: str
    picture_profile: str
    log_shooting_mode: str
    hlg_still_image: str
    # `[Creative Look]` 10 Presets + 6 Custom + 8 Asymmetric Params & Dormant `[Soft Skin Effect]`
    creative_look: str
    cl_contrast: int
    cl_highlights: int
    cl_shadows: int
    cl_fade: int
    cl_saturation: int
    cl_sharpness: int
    cl_sharpness_range: int
    cl_clarity: int
    attempt_edit_saturation_on_bw_se: bool
    attempt_edit_sharpness_range_in_movie: bool
    soft_skin_effect_requested: bool
    fx6_base_look_mode: str
    reported_creative_look_errno: Optional[int]
    reported_soft_skin_errno: Optional[int]
    reported_creative_look_forced_disabled: bool
    reported_effective_creative_look: str
    reported_saturation_locked: bool
    reported_sharpness_range_locked: bool
    # Playback `[Delete]` / `[Delete confirm.]` / `[Delete pressing twice]` / `[Protect]` / `[Recover Image DB]`
    selected_playback_slot: int
    delete_scope: str
    delete_item_protected: bool
    delete_has_coupled_proxy: bool
    delete_confirm_mode: str
    delete_pressing_twice: str
    protect_scope: str
    protect_has_coupled_proxy: bool
    copy_preserves_protect: bool
    recover_image_db_requested: bool
    battery_sufficient_for_recover_db: bool
    display_media_info_still_cap: int
    reported_playback_action_errno: Optional[int]
    reported_delete_coupled_proxy: bool
    reported_delete_protected_skipped: bool
    reported_protect_coupled_proxy: bool
    reported_quick_delete_hazard: bool
    reported_recover_db_avf_info_rebuilt: bool
    reported_recover_db_ftp_history_wiped: bool
    reported_media_info_still_cap_ok: bool
    # Reset persistence (`Creative Look` Can be reset; `Delete confirm.`/`pressing twice` Not available; `Recover Image DB` survives Reset & Init!)
    reset_action: str
    post_creative_look: str
    post_delete_confirm_mode: str
    post_delete_pressing_twice: str
    post_image_db_recovered_persisted: bool
    # Vault & Overlay & H0==H3
    requested_vault_slot: int
    slot1_holds_tier0_vault: bool
    requested_vault_action: str
    reported_vault_action_allowed: bool
    vault_firewall_errno: Optional[str]
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
    creative_look_8param_override_or_softskin_drift_events: int
    delete_protect_recoverdb_slot1_vault_drift_events: int


@dataclass(frozen=True)
class CreativeLookSoftSkinDeleteProtectRecoverDbVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    creative_look_8param_and_softskin_verified: bool
    delete_protect_recoverdb_persistence_verified: bool
    overlay_and_h0_h3_verified: bool
    matrix_states_checked: int
    creative_look_8param_override_or_softskin_drift_events: int
    delete_protect_recoverdb_slot1_vault_drift_events: int
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
class DriveFocusBracketShutterEfcsCreativeLookRecoverDbVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase370DonorSnapshot
    drive_focusbracket_shutter_efcs_nr_report: DriveModeFocusBracketShutterEfcsNrVaultReport
    creative_look_softskin_recoverdb_report: CreativeLookSoftSkinDeleteProtectRecoverDbVaultReport
    drive_mode_or_dormant_focus_bracket_drift_events: int
    shutter_2opt_xsync_efcs_or_nr_drift_events: int
    creative_look_8param_override_or_softskin_drift_events: int
    delete_protect_recoverdb_slot1_vault_drift_events: int
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
class Pillar68ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar68ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar68ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar68BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar68ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar68StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase370DonorSnapshot
    pillar_68a_drive_focusbracket_shutter_efcs_nr_vault: Pillar68ASuiteResult
    pillar_68b_creativelook_softskin_recoverdb_vault: Pillar68BSuiteResult
    drive_mode_or_dormant_focus_bracket_drift_events: int
    shutter_2opt_xsync_efcs_or_nr_drift_events: int
    creative_look_8param_override_or_softskin_drift_events: int
    delete_protect_recoverdb_slot1_vault_drift_events: int
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
class Master68PillarRecoveryReport:
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
    donor_snapshot: Phase370DonorSnapshot
    pillar68_a_drive_focusbracket_shutter_efcs_nr_vault: Pillar68ASuiteResult
    pillar68_b_creativelook_softskin_recoverdb_vault: Pillar68BSuiteResult
    # Pillar 68 zero-violation counters & empirical capability booleans
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
    slot1_sector_writes: int
    cnflasha_writes: int
    emmc_writes_authorized: bool
    # Carried-forward Pillar 67..41 zero-violation metrics
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
    # Safety lock flags
    overall_ready_for_hardware_attach: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    master_68pillar_sha256: str
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
# Default Safe Specs & Evaluators (Pillars 68A & 68B)
# ---------------------------------------------------------------------------


def build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
    **overrides: Any,
) -> DriveModeFocusBracketShutterEfcsNrVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P370_FX3_MODEL_NAME,
        "fw_version": P370_FX3_FW_VERSION,
        "shooting_domain": "Still",
        "exposure_mode": "A",
        "still_file_format": "RAW & JPEG",
        "raw_file_type": "Compressed",
        "hlg_still_image": "Off",
        "flash_active": False,
        "aperture_f_number": 4.0,
        "drive_mode": "Single Shooting",
        "cont_shoot_speed": "Hi+",
        "self_timer_single_sec": "10 Sec",
        "self_timer_cont_option": "10 Sec. 3 Img.",
        "bracket_step_ev": 0.3,
        "bracket_img_count": 3,
        "wb_bracket_mode": "Lo",
        "dro_bracket_mode": "Lo",
        "bracket_selftimer": "Off",
        "bracket_order": "0->-->+",
        "interval_shoot_active": False,
        "interval_output_is_movie": False,
        "shutter_type_in_interval": "Electronic Shutter",
        "focus_bracket_requested": False,
        "reported_drive_mode_errno": None,
        "reported_focus_bracket_errno": None,
        "reported_effective_drive_mode": "Single Shooting",
        "reported_nominal_cont_fps": 0.0,
        "reported_drive_rate_reduced": False,
        "reported_live_view_realtime_refresh": True,
        "reported_focus_locked_first_frame": False,
        "shutter_type": "Mechanical Shutter",
        "silent_mode": "Off",
        "requested_flash_sync_reciprocal": 250,
        "efcs_enabled": "On",
        "bulb_requested": False,
        "anti_flicker_shoot_requested": False,
        "shutter_speed_seconds": 1.0 / 250.0,
        "long_exposure_nr": "On",
        "high_iso_nr": "Normal",
        "fx6_noise_suppression": "Off",
        "fx6_apr_lens_cap_covered": True,
        "reported_shutter_errno": None,
        "reported_xsync_errno": None,
        "reported_nr_errno": None,
        "reported_effective_shutter_type": "Mechanical Shutter",
        "reported_electronic_or_silent_active": False,
        "reported_locked_features_under_electronic": (),
        "reported_effective_efcs": "On",
        "reported_effective_long_exp_nr": "On",
        "reported_long_exp_nr_subtraction_active": False,
        "reported_effective_high_iso_nr": "Normal",
        "reported_arw_raw_untouched": True,
        "reset_action": "Camera Settings Reset",
        "post_drive_mode": "Single Shooting",
        "post_shutter_type": "Mechanical Shutter",
        "post_shutter_type_in_interval": "Electronic Shutter",
        "post_efcs": "On",
        "post_long_exposure_nr": "On",
        "post_high_iso_nr": "Normal",
        "requested_vault_slot": 1,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": 0,
        "slot1_sector_writes": 0,
        "slot1_vault_mutation_bytes": 0,
        "cnflasha_writes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P370_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P370_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P370_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P370_TIER0_SURFACE_COUNT,
        "drive_mode_or_dormant_focus_bracket_drift_events": 0,
        "shutter_2opt_xsync_efcs_or_nr_drift_events": 0,
    }
    defaults.update(overrides)
    return DriveModeFocusBracketShutterEfcsNrVaultSpec(**defaults)


def build_default_safe_creativelook_softskin_recoverdb_vault_spec(
    **overrides: Any,
) -> CreativeLookSoftSkinDeleteProtectRecoverDbVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P370_FX3_MODEL_NAME,
        "fw_version": P370_FX3_FW_VERSION,
        "shooting_domain": "Still",
        "exposure_mode": "M",
        "picture_profile": "Off",
        "log_shooting_mode": "Off",
        "hlg_still_image": "Off",
        "creative_look": "ST",
        "cl_contrast": 0,
        "cl_highlights": 0,
        "cl_shadows": 0,
        "cl_fade": 0,
        "cl_saturation": 0,
        "cl_sharpness": 0,
        "cl_sharpness_range": 3,
        "cl_clarity": 0,
        "attempt_edit_saturation_on_bw_se": False,
        "attempt_edit_sharpness_range_in_movie": False,
        "soft_skin_effect_requested": False,
        "fx6_base_look_mode": "Custom SDR",
        "reported_creative_look_errno": None,
        "reported_soft_skin_errno": None,
        "reported_creative_look_forced_disabled": False,
        "reported_effective_creative_look": "ST",
        "reported_saturation_locked": False,
        "reported_sharpness_range_locked": False,
        "selected_playback_slot": 1,
        "delete_scope": "None",
        "delete_item_protected": False,
        "delete_has_coupled_proxy": False,
        "delete_confirm_mode": '"Cancel" first',
        "delete_pressing_twice": "Off",
        "protect_scope": "None",
        "protect_has_coupled_proxy": False,
        "copy_preserves_protect": False,
        "recover_image_db_requested": False,
        "battery_sufficient_for_recover_db": True,
        "display_media_info_still_cap": 40_000,
        "reported_playback_action_errno": None,
        "reported_delete_coupled_proxy": False,
        "reported_delete_protected_skipped": False,
        "reported_protect_coupled_proxy": False,
        "reported_quick_delete_hazard": False,
        "reported_recover_db_avf_info_rebuilt": False,
        "reported_recover_db_ftp_history_wiped": False,
        "reported_media_info_still_cap_ok": True,
        "reset_action": "Camera Settings Reset",
        "post_creative_look": "ST",
        "post_delete_confirm_mode": '"Cancel" first',
        "post_delete_pressing_twice": "Off",
        "post_image_db_recovered_persisted": True,
        "requested_vault_slot": 1,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": 0,
        "slot1_sector_writes": 0,
        "slot1_vault_mutation_bytes": 0,
        "cnflasha_writes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P370_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P370_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P370_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P370_TIER0_SURFACE_COUNT,
        "creative_look_8param_override_or_softskin_drift_events": 0,
        "delete_protect_recoverdb_slot1_vault_drift_events": 0,
    }
    defaults.update(overrides)
    return CreativeLookSoftSkinDeleteProtectRecoverDbVaultSpec(**defaults)


def evaluate_drive_focusbracket_shutter_efcs_nr_vault(
    spec: DriveModeFocusBracketShutterEfcsNrVaultSpec,
) -> DriveModeFocusBracketShutterEfcsNrVaultReport:
    """Evaluate Pillar 68A (`[Drive Mode]` 10fps / Dormant `[Focus Bracket]` Rejection,
    2-Option `[Shutter Type]` No Auto, `1/250 s` X-Sync, `[e-Front Curtain Shut.]`, NR)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P370_BLOCKED_SAFETY_POLICY_VIOLATION, "Safety policy violation")

    valid_spec = (
        spec.camera_model in (P370_FX3_MODEL_NAME, P370_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P370_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P370_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P370_SHOOTING_DOMAINS
        and spec.exposure_mode in P370_EXPOSURE_MODES
        and spec.still_file_format in P370_STILL_FILE_FORMATS
        and spec.raw_file_type in P370_RAW_FILE_TYPES
        and spec.hlg_still_image in P370_ON_OFF_MODES
        and spec.self_timer_single_sec in P370_FX3_SELF_TIMER_SINGLE_OPTIONS
        and spec.wb_bracket_mode in P370_FX3_WB_BRACKET_MODES
        and spec.dro_bracket_mode in P370_FX3_DRO_BRACKET_MODES
        and spec.bracket_selftimer in P370_FX3_BRACKET_SELFTIMER_OPTIONS
        and spec.bracket_order in P370_FX3_BRACKET_ORDER_OPTIONS
        and spec.silent_mode in P370_ON_OFF_MODES
        and spec.efcs_enabled in ("None", "Off", "On")
        and spec.long_exposure_nr in ("None", "Off", "On")
        and spec.reset_action in P370_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P370_VAULT_ACTIONS
        and spec.vault_firewall_errno in P370_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P370_BLOCKED_INVALID_PILLAR68A_SPEC, "Invalid Pillar 68A spec fields")

    st = compute_expected_drive_focusbracket_shutter_efcs_nr_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        exposure_mode=spec.exposure_mode,
        still_file_format=spec.still_file_format,
        raw_file_type=spec.raw_file_type,
        hlg_still_image=spec.hlg_still_image,
        flash_active=spec.flash_active,
        aperture_f_number=spec.aperture_f_number,
        drive_mode=spec.drive_mode,
        cont_shoot_speed=spec.cont_shoot_speed,
        self_timer_single_sec=spec.self_timer_single_sec,
        self_timer_cont_option=spec.self_timer_cont_option,
        bracket_step_ev=spec.bracket_step_ev,
        bracket_img_count=spec.bracket_img_count,
        wb_bracket_mode=spec.wb_bracket_mode,
        dro_bracket_mode=spec.dro_bracket_mode,
        bracket_selftimer=spec.bracket_selftimer,
        bracket_order=spec.bracket_order,
        interval_shoot_active=spec.interval_shoot_active,
        interval_output_is_movie=spec.interval_output_is_movie,
        shutter_type_in_interval=spec.shutter_type_in_interval,
        focus_bracket_requested=spec.focus_bracket_requested,
        shutter_type=spec.shutter_type,
        silent_mode=spec.silent_mode,
        requested_flash_sync_reciprocal=spec.requested_flash_sync_reciprocal,
        efcs_enabled=spec.efcs_enabled,
        bulb_requested=spec.bulb_requested,
        anti_flicker_shoot_requested=spec.anti_flicker_shoot_requested,
        shutter_speed_seconds=spec.shutter_speed_seconds,
        long_exposure_nr=spec.long_exposure_nr,
        high_iso_nr=spec.high_iso_nr,
        fx6_noise_suppression=spec.fx6_noise_suppression,
        fx6_apr_lens_cap_covered=spec.fx6_apr_lens_cap_covered,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    drive_ok = (
        spec.reported_drive_mode_errno == st["drive_mode_errno"]
        and st["drive_mode_errno"] is None
        and spec.reported_focus_bracket_errno == st["focus_bracket_errno"]
        and st["focus_bracket_errno"] is None
        and not spec.focus_bracket_requested
        and spec.reported_effective_drive_mode == st["effective_drive_mode"]
        and abs(spec.reported_nominal_cont_fps - st["nominal_cont_fps"]) < 1e-9
        and spec.reported_drive_rate_reduced == st["drive_rate_reduced"]
        and spec.reported_live_view_realtime_refresh == st["live_view_realtime_refresh"]
        and spec.reported_focus_locked_first_frame == st["focus_locked_first_frame"]
        and spec.post_drive_mode == st["post_drive_mode"]
        and spec.post_shutter_type_in_interval == st["post_shutter_type_in_interval"]
        and spec.drive_mode_or_dormant_focus_bracket_drift_events == 0
    )
    if not drive_ok:
        _fail(
            P370_BLOCKED_DRIVE_MODE_OR_DORMANT_FOCUS_BRACKET,
            "Drive Mode 10fps/rate/F11/DRO-HLG/Self-timer(Cont) 6-combo, Interval Shutter, or Dormant Focus Bracket rule violated",
        )

    shutter_nr_ok = (
        spec.reported_shutter_errno == st["shutter_errno"]
        and st["shutter_errno"] is None
        and spec.reported_xsync_errno == st["xsync_errno"]
        and st["xsync_errno"] is None
        and spec.reported_nr_errno == st["nr_errno"]
        and st["nr_errno"] is None
        and spec.reported_effective_shutter_type == st["effective_shutter_type"]
        and spec.reported_electronic_or_silent_active == st["electronic_or_silent_active"]
        and tuple(spec.reported_locked_features_under_electronic)
        == tuple(st["locked_features_under_electronic"])
        and spec.reported_effective_efcs == st["effective_efcs"]
        and spec.reported_effective_long_exp_nr == st["effective_long_exp_nr"]
        and spec.reported_long_exp_nr_subtraction_active == st["long_exp_nr_subtraction_active"]
        and spec.reported_effective_high_iso_nr == st["effective_high_iso_nr"]
        and spec.reported_arw_raw_untouched == st["arw_raw_untouched"]
        and spec.reported_arw_raw_untouched
        and spec.post_shutter_type == st["post_shutter_type"]
        and spec.post_efcs == st["post_efcs"]
        and spec.post_long_exposure_nr == st["post_long_exposure_nr"]
        and spec.post_high_iso_nr == st["post_high_iso_nr"]
        and spec.shutter_2opt_xsync_efcs_or_nr_drift_events == 0
    )
    if not shutter_nr_ok:
        _fail(
            P370_BLOCKED_SHUTTER_2OPT_XSYNC_EFCS_OR_NR_DRIFT,
            "2-Option Shutter Type (no Auto), Electronic 5-lockout, 1/250s X-Sync, EFCS Reset-resistance, Long Exp NR, or High ISO NR violated",
        )

    slot1_mutated = (
        (
            spec.requested_vault_action in P370_WRITE_MUTATING_VAULT_ACTIONS
            or (
                spec.requested_vault_slot == 1
                and spec.requested_vault_action not in ("NONE", "READ_ONLY_AUDIT", "DISPLAY_MEDIA_INFO_READ_ONLY")
            )
        )
        and spec.reported_vault_action_allowed
    )
    vault_ok = (
        not slot1_mutated
        and spec.reported_vault_action_allowed == st["vault_action_allowed"]
        and spec.vault_firewall_errno == st["vault_firewall_errno"]
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_sector_writes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.cnflasha_writes == 0
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_format_hard_locked
    )
    if not vault_ok:
        _fail(
            P370_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P370_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P370_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P370_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P370_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    vault_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "68A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "effective_drive_mode": spec.reported_effective_drive_mode,
            "effective_shutter_type": spec.reported_effective_shutter_type,
            "effective_efcs": spec.reported_effective_efcs,
            "effective_long_exp_nr": spec.reported_effective_long_exp_nr,
            "effective_high_iso_nr": spec.reported_effective_high_iso_nr,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return DriveModeFocusBracketShutterEfcsNrVaultReport(
        schema=PHASE370_SCHEMA,
        version=PHASE370_VERSION,
        passed=passed,
        status=P370_STATUS_VERIFIED_PILLAR_68A if passed else P370_STATUS_REJECTED_PILLAR_68A,
        block_code=block_code,
        drive_mode_and_dormant_focus_bracket_verified=drive_ok,
        shutter_2opt_xsync_efcs_nr_verified=shutter_nr_ok,
        slot1_vault_and_h0_h3_verified=vault_and_h0_h3_ok,
        matrix_states_checked=46,
        drive_mode_or_dormant_focus_bracket_drift_events=(
            spec.drive_mode_or_dormant_focus_bracket_drift_events
        ),
        shutter_2opt_xsync_efcs_or_nr_drift_events=(
            spec.shutter_2opt_xsync_efcs_or_nr_drift_events
        ),
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


def evaluate_creativelook_softskin_recoverdb_vault(
    spec: CreativeLookSoftSkinDeleteProtectRecoverDbVaultSpec,
) -> CreativeLookSoftSkinDeleteProtectRecoverDbVaultReport:
    """Evaluate Pillar 68B (`[Creative Look]` 10 Presets + 6 Custom + 8 Asymmetric Params /
    Dormant `[Soft Skin Effect]` Rejection + `[Delete]`/`[Protect]`/`[Recover Image DB]` Slot-1 EROFS=30)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P370_BLOCKED_SAFETY_POLICY_VIOLATION, "Safety policy violation")

    valid_spec = (
        spec.camera_model in (P370_FX3_MODEL_NAME, P370_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P370_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P370_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P370_SHOOTING_DOMAINS
        and spec.exposure_mode in P370_EXPOSURE_MODES
        and spec.hlg_still_image in P370_ON_OFF_MODES
        and spec.selected_playback_slot in (1, 2)
        and spec.delete_scope in P370_FX3_DELETE_SCOPES
        and spec.delete_confirm_mode in (("None",) + P370_FX3_DELETE_CONFIRM_OPTIONS)
        and spec.delete_pressing_twice in ("None", "Off", "On")
        and spec.protect_scope in P370_FX3_PROTECT_SCOPES
        and spec.reset_action in P370_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P370_VAULT_ACTIONS
        and spec.vault_firewall_errno in P370_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P370_BLOCKED_INVALID_PILLAR68B_SPEC, "Invalid Pillar 68B spec fields")

    st = compute_expected_creativelook_softskin_recoverdb_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        exposure_mode=spec.exposure_mode,
        picture_profile=spec.picture_profile,
        log_shooting_mode=spec.log_shooting_mode,
        hlg_still_image=spec.hlg_still_image,
        creative_look=spec.creative_look,
        cl_contrast=spec.cl_contrast,
        cl_highlights=spec.cl_highlights,
        cl_shadows=spec.cl_shadows,
        cl_fade=spec.cl_fade,
        cl_saturation=spec.cl_saturation,
        cl_sharpness=spec.cl_sharpness,
        cl_sharpness_range=spec.cl_sharpness_range,
        cl_clarity=spec.cl_clarity,
        attempt_edit_saturation_on_bw_se=spec.attempt_edit_saturation_on_bw_se,
        attempt_edit_sharpness_range_in_movie=spec.attempt_edit_sharpness_range_in_movie,
        soft_skin_effect_requested=spec.soft_skin_effect_requested,
        fx6_base_look_mode=spec.fx6_base_look_mode,
        selected_playback_slot=spec.selected_playback_slot,
        delete_scope=spec.delete_scope,
        delete_item_protected=spec.delete_item_protected,
        delete_has_coupled_proxy=spec.delete_has_coupled_proxy,
        delete_confirm_mode=spec.delete_confirm_mode,
        delete_pressing_twice=spec.delete_pressing_twice,
        protect_scope=spec.protect_scope,
        protect_has_coupled_proxy=spec.protect_has_coupled_proxy,
        copy_preserves_protect=spec.copy_preserves_protect,
        recover_image_db_requested=spec.recover_image_db_requested,
        battery_sufficient_for_recover_db=spec.battery_sufficient_for_recover_db,
        display_media_info_still_cap=spec.display_media_info_still_cap,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    creative_look_ok = (
        spec.reported_creative_look_errno == st["creative_look_errno"]
        and st["creative_look_errno"] is None
        and spec.reported_soft_skin_errno == st["soft_skin_errno"]
        and st["soft_skin_errno"] is None
        and not spec.soft_skin_effect_requested
        and spec.reported_creative_look_forced_disabled == st["creative_look_forced_disabled"]
        and spec.reported_effective_creative_look == st["effective_creative_look"]
        and spec.reported_saturation_locked == st["saturation_locked"]
        and spec.reported_sharpness_range_locked == st["sharpness_range_locked"]
        and spec.post_creative_look == st["post_creative_look"]
        and spec.creative_look_8param_override_or_softskin_drift_events == 0
    )
    if not creative_look_ok:
        _fail(
            P370_BLOCKED_CREATIVE_LOOK_8PARAM_OVERRIDE_OR_SOFTSKIN,
            "Creative Look 10-preset/6-Custom/8-asymmetric param bounds, PP/Log/HLG/iAuto override, or Dormant Soft Skin Effect rule violated",
        )

    playback_ok = (
        spec.reported_playback_action_errno == st["playback_action_errno"]
        and st["playback_action_errno"] is None
        and spec.reported_delete_coupled_proxy == st["delete_coupled_proxy"]
        and spec.reported_delete_protected_skipped == st["delete_protected_skipped"]
        and spec.reported_protect_coupled_proxy == st["protect_coupled_proxy"]
        and not spec.copy_preserves_protect
        and spec.reported_quick_delete_hazard == st["quick_delete_hazard"]
        and spec.reported_recover_db_avf_info_rebuilt == st["recover_db_avf_info_rebuilt"]
        and spec.reported_recover_db_ftp_history_wiped == st["recover_db_ftp_history_wiped"]
        and spec.reported_media_info_still_cap_ok == st["media_info_still_cap_ok"]
        and st["media_info_still_cap_ok"]
        and spec.post_delete_confirm_mode == st["post_delete_confirm_mode"]
        and spec.post_delete_pressing_twice == st["post_delete_pressing_twice"]
        and spec.post_image_db_recovered_persisted == st["post_image_db_recovered_persisted"]
        and spec.delete_protect_recoverdb_slot1_vault_drift_events == 0
    )
    if not playback_ok:
        _fail(
            P370_BLOCKED_DELETE_PROTECT_OR_RECOVERDB_DRIFT,
            "Playback Delete/Confirm/Twice, Protect coupled proxy, Recover Image DB persistence, or Display Media Info 40k rule violated",
        )

    targets_slot1_or_media_a = (spec.requested_vault_slot == 1) or (
        spec.requested_vault_action == "FX6_RESTORE_MEDIA_A"
    )
    slot1_mutated = (
        (
            spec.requested_vault_action in P370_WRITE_MUTATING_VAULT_ACTIONS
            or (
                targets_slot1_or_media_a
                and spec.requested_vault_action not in ("NONE", "READ_ONLY_AUDIT", "DISPLAY_MEDIA_INFO_READ_ONLY")
            )
        )
        and spec.reported_vault_action_allowed
    )
    vault_ok = (
        not slot1_mutated
        and spec.reported_vault_action_allowed == st["vault_action_allowed"]
        and spec.vault_firewall_errno == st["vault_firewall_errno"]
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_sector_writes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.cnflasha_writes == 0
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_format_hard_locked
    )
    if not vault_ok:
        _fail(
            P370_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P370_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P370_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P370_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P370_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    overlay_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "68B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "effective_creative_look": spec.reported_effective_creative_look,
            "delete_confirm": spec.post_delete_confirm_mode,
            "recover_db_persisted": spec.post_image_db_recovered_persisted,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return CreativeLookSoftSkinDeleteProtectRecoverDbVaultReport(
        schema=PHASE370_SCHEMA,
        version=PHASE370_VERSION,
        passed=passed,
        status=P370_STATUS_VERIFIED_PILLAR_68B if passed else P370_STATUS_REJECTED_PILLAR_68B,
        block_code=block_code,
        creative_look_8param_and_softskin_verified=creative_look_ok,
        delete_protect_recoverdb_persistence_verified=playback_ok,
        overlay_and_h0_h3_verified=overlay_and_h0_h3_ok,
        matrix_states_checked=46,
        creative_look_8param_override_or_softskin_drift_events=(
            spec.creative_look_8param_override_or_softskin_drift_events
        ),
        delete_protect_recoverdb_slot1_vault_drift_events=(
            spec.delete_protect_recoverdb_slot1_vault_drift_events
        ),
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


def verify_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_68a: Optional[DriveModeFocusBracketShutterEfcsNrVaultSpec] = None,
    spec_68b: Optional[CreativeLookSoftSkinDeleteProtectRecoverDbVaultSpec] = None,
) -> DriveFocusBracketShutterEfcsCreativeLookRecoverDbVaultReport:
    """Combined single-shot verifier for Pillar 68A + Pillar 68B + 17 bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase370_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_drive_focusbracket_shutter_efcs_nr_vault(
        spec_68a or build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec()
    )
    rep_b = evaluate_creativelook_softskin_recoverdb_vault(
        spec_68b or build_default_safe_creativelook_softskin_recoverdb_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 370 Wave-66 donor artifact parity check failed")
    if not donor_snapshot.under_2_0s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return DriveFocusBracketShutterEfcsCreativeLookRecoverDbVaultReport(
        schema=PHASE370_SCHEMA,
        version=PHASE370_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P370_STATUS_VERIFIED_PILLAR68_SUITE if all_ok else P370_STATUS_FAIL_PILLAR68_SUITE,
        donor_snapshot=donor_snapshot,
        drive_focusbracket_shutter_efcs_nr_report=rep_a,
        creative_look_softskin_recoverdb_report=rep_b,
        drive_mode_or_dormant_focus_bracket_drift_events=(
            rep_a.drive_mode_or_dormant_focus_bracket_drift_events
        ),
        shutter_2opt_xsync_efcs_or_nr_drift_events=(
            rep_a.shutter_2opt_xsync_efcs_or_nr_drift_events
        ),
        creative_look_8param_override_or_softskin_drift_events=(
            rep_b.creative_look_8param_override_or_softskin_drift_events
        ),
        delete_protect_recoverdb_slot1_vault_drift_events=(
            rep_b.delete_protect_recoverdb_slot1_vault_drift_events
        ),
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
        emmc_writes_authorized=P370_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(errs),
    )


def verify_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_68a: Optional[DriveModeFocusBracketShutterEfcsNrVaultSpec] = None,
    spec_68b: Optional[CreativeLookSoftSkinDeleteProtectRecoverDbVaultSpec] = None,
) -> DriveFocusBracketShutterEfcsCreativeLookRecoverDbVaultReport:
    """Symmetry alias for `verify_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_vault`."""
    return verify_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_vault(
        force_clean_room=force_clean_room,
        spec_68a=spec_68a,
        spec_68b=spec_68b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 68A & 68B)
# ---------------------------------------------------------------------------


def run_pillar68a_drive_focusbracket_shutter_efcs_nr_vault_6_scenario_suite() -> Pillar68ASuiteResult:
    """Run 6 Pillar 68A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, DriveModeFocusBracketShutterEfcsNrVaultSpec, Optional[str]], ...] = (
        (
            P370_PILLAR_68A_SCENARIO_IDS[0],
            True,
            build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
                shooting_domain="Still",
                still_file_format="RAW & JPEG",
                raw_file_type="Uncompressed",
                aperture_f_number=16.0,
                drive_mode="Cont. Shooting",
                cont_shoot_speed="Hi+",
                reported_effective_drive_mode="Cont. Shooting",
                reported_nominal_cont_fps=10.0,
                reported_drive_rate_reduced=True,
                reported_live_view_realtime_refresh=False,
                reported_focus_locked_first_frame=True,
                shutter_type="Mechanical Shutter",
                requested_flash_sync_reciprocal=250,
                efcs_enabled="Off",
                long_exposure_nr="Off",
                high_iso_nr="Low",
                reported_effective_shutter_type="Mechanical Shutter",
                reported_effective_efcs="Off",
                reported_effective_long_exp_nr="Off",
                reported_effective_high_iso_nr="Low",
                reset_action="Camera Settings Reset",
                post_drive_mode="Single Shooting",
                post_shutter_type="Mechanical Shutter",
                post_shutter_type_in_interval="Electronic Shutter",
                post_efcs="Off",  # Resists Camera Settings Reset!
                post_long_exposure_nr="On",
                post_high_iso_nr="Normal",
            ),
            None,
        ),
        (
            P370_PILLAR_68A_SCENARIO_IDS[1],
            True,
            build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
                shooting_domain="Still",
                still_file_format="RAW & HEIF",
                raw_file_type="Compressed",
                drive_mode="Single Shooting",
                shutter_type="Electronic Shutter",
                efcs_enabled="Off",
                long_exposure_nr="Off",
                high_iso_nr="Off",
                reported_effective_shutter_type="Electronic Shutter",
                reported_electronic_or_silent_active=True,
                reported_locked_features_under_electronic=P370_FX3_ELECTRONIC_OR_SILENT_LOCKED_FEATURES,
                reported_effective_efcs="Off",
                reported_effective_long_exp_nr="Off",
                reported_effective_high_iso_nr="Off",
                reported_arw_raw_untouched=True,
                reset_action="None",
                post_drive_mode="Single Shooting",
                post_shutter_type="Electronic Shutter",
                post_efcs="Off",
                post_long_exposure_nr="Off",
                post_high_iso_nr="Off",
            ),
            None,
        ),
        (
            P370_PILLAR_68A_SCENARIO_IDS[2],
            False,
            build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
                drive_mode="Focus Bracket",
                focus_bracket_requested=True,
                self_timer_cont_option="10SEC_10IMAGES",
                reported_drive_mode_errno=None,
                reported_focus_bracket_errno=None,
                drive_mode_or_dormant_focus_bracket_drift_events=1,
            ),
            P370_BLOCKED_DRIVE_MODE_OR_DORMANT_FOCUS_BRACKET,
        ),
        (
            P370_PILLAR_68A_SCENARIO_IDS[3],
            False,
            build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
                shutter_type="Auto",
                requested_flash_sync_reciprocal=320,
                efcs_enabled="Off",
                reset_action="Camera Settings Reset",
                post_efcs="On",  # Wrong: EFCS resists Camera Settings Reset!
                reported_shutter_errno=None,
                reported_xsync_errno=None,
                shutter_2opt_xsync_efcs_or_nr_drift_events=1,
            ),
            P370_BLOCKED_SHUTTER_2OPT_XSYNC_EFCS_OR_NR_DRIFT,
        ),
        (
            P370_PILLAR_68A_SCENARIO_IDS[4],
            False,
            build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
                shutter_type="Electronic Shutter",
                flash_active=True,
                bulb_requested=True,
                high_iso_nr="HIGH",
                reported_arw_raw_untouched=False,
                reported_shutter_errno=None,
                reported_nr_errno=None,
                shutter_2opt_xsync_efcs_or_nr_drift_events=1,
            ),
            P370_BLOCKED_SHUTTER_2OPT_XSYNC_EFCS_OR_NR_DRIFT,
        ),
        (
            P370_PILLAR_68A_SCENARIO_IDS[5],
            False,
            build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="RECOVER_IMAGE_DB_AVF_INFO_SLOT1",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
                slot1_sector_writes=8,
                slot1_vault_mutation_bytes=4096,
                cnflasha_writes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/setting/68a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P370_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar68ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar68ScenarioOutcome(
                scenario_id=sid,
                pillar="68A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar68ASuiteResult(
        passed=all_ok,
        status=P370_STATUS_VERIFIED_PILLAR_68A if all_ok else P370_STATUS_REJECTED_PILLAR_68A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar68b_creativelook_softskin_recoverdb_vault_6_scenario_suite() -> Pillar68BSuiteResult:
    """Run 6 Pillar 68B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, CreativeLookSoftSkinDeleteProtectRecoverDbVaultSpec, Optional[str]], ...] = (
        (
            P370_PILLAR_68B_SCENARIO_IDS[0],
            True,
            build_default_safe_creativelook_softskin_recoverdb_vault_spec(
                shooting_domain="Still",
                creative_look="Custom Look 6",
                cl_contrast=4,
                cl_highlights=-2,
                cl_shadows=3,
                cl_fade=2,
                cl_saturation=1,
                cl_sharpness=5,
                cl_sharpness_range=4,
                cl_clarity=7,
                reported_effective_creative_look="Custom Look 6",
                delete_confirm_mode='"Delete" first',
                delete_pressing_twice="On",
                reported_quick_delete_hazard=True,
                reset_action="Camera Settings Reset",
                post_creative_look="ST",
                post_delete_confirm_mode='"Delete" first',
                post_delete_pressing_twice="On",
            ),
            None,
        ),
        (
            P370_PILLAR_68B_SCENARIO_IDS[1],
            True,
            build_default_safe_creativelook_softskin_recoverdb_vault_spec(
                camera_model=P370_FX6_DONOR_MODEL_NAME,
                fw_version=P370_FX6_DONOR_FW_VERSION,
                shooting_domain="Movie",
                creative_look="None",
                fx6_base_look_mode="Log",
                reported_creative_look_forced_disabled=True,
                reported_effective_creative_look="None",
                reported_saturation_locked=True,
                reported_sharpness_range_locked=True,
                delete_confirm_mode="None",
                delete_pressing_twice="None",
                display_media_info_still_cap=40_000,
                reported_media_info_still_cap_ok=True,
                reset_action="None",
                post_creative_look="None",
                post_delete_confirm_mode="None",
                post_delete_pressing_twice="None",
                requested_vault_action="DISPLAY_MEDIA_INFO_READ_ONLY",
            ),
            None,
        ),
        (
            P370_PILLAR_68B_SCENARIO_IDS[2],
            False,
            build_default_safe_creativelook_softskin_recoverdb_vault_spec(
                shooting_domain="Movie",
                creative_look="BW",
                cl_clarity=-3,  # Invalid! Clarity is 0..9!
                attempt_edit_saturation_on_bw_se=True,
                attempt_edit_sharpness_range_in_movie=True,
                picture_profile="PP11",
                reported_creative_look_errno=None,
                creative_look_8param_override_or_softskin_drift_events=1,
            ),
            P370_BLOCKED_CREATIVE_LOOK_8PARAM_OVERRIDE_OR_SOFTSKIN,
        ),
        (
            P370_PILLAR_68B_SCENARIO_IDS[3],
            False,
            build_default_safe_creativelook_softskin_recoverdb_vault_spec(
                soft_skin_effect_requested=True,
                reported_soft_skin_errno=None,
                creative_look_8param_override_or_softskin_drift_events=1,
            ),
            P370_BLOCKED_CREATIVE_LOOK_8PARAM_OVERRIDE_OR_SOFTSKIN,
        ),
        (
            P370_PILLAR_68B_SCENARIO_IDS[4],
            False,
            build_default_safe_creativelook_softskin_recoverdb_vault_spec(
                delete_confirm_mode='"Delete" first',
                reset_action="Camera Settings Reset",
                post_delete_confirm_mode='"Cancel" first',  # Wrong: resists Reset!
                copy_preserves_protect=True,
                display_media_info_still_cap=50_000,
                delete_protect_recoverdb_slot1_vault_drift_events=1,
            ),
            P370_BLOCKED_DELETE_PROTECT_OR_RECOVERDB_DRIFT,
        ),
        (
            P370_PILLAR_68B_SCENARIO_IDS[5],
            False,
            build_default_safe_creativelook_softskin_recoverdb_vault_spec(
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="FX6_RESTORE_MEDIA_A",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
                slot1_sector_writes=8,
                slot1_vault_mutation_bytes=4096,
                cnflasha_writes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/mnt/emmc/68b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P370_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar68ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_creativelook_softskin_recoverdb_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar68ScenarioOutcome(
                scenario_id=sid,
                pillar="68B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar68BSuiteResult(
        passed=all_ok,
        status=P370_STATUS_VERIFIED_PILLAR_68B if all_ok else P370_STATUS_REJECTED_PILLAR_68B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Standalone Pillar 68 Suite & Concurrent Unified 68/68 Master Aggregator
# ---------------------------------------------------------------------------


def run_pillar68_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar68StandaloneReport:
    """Run full Pillar 68 standalone suite (`6/6` Pillar 68A + `6/6` Pillar 68B + 17 bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase370_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar68a_drive_focusbracket_shutter_efcs_nr_vault_6_scenario_suite()
    res_b = run_pillar68b_creativelook_softskin_recoverdb_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 370 donor verification failed")
    if not donor_snapshot.under_2_0s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE370_SCHEMA,
            "version": PHASE370_VERSION,
            "mode": donor_snapshot.verification_mode,
            "68a": [asdict(s) for s in res_a.scenarios],
            "68b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar68StandaloneReport(
        schema=PHASE370_SCHEMA,
        version=PHASE370_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P370_STATUS_VERIFIED_PILLAR68_SUITE if all_ok else P370_STATUS_FAIL_PILLAR68_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_68a_drive_focusbracket_shutter_efcs_nr_vault=res_a,
        pillar_68b_creativelook_softskin_recoverdb_vault=res_b,
        drive_mode_or_dormant_focus_bracket_drift_events=(
            P370_DRIVE_MODE_OR_DORMANT_FOCUS_BRACKET_DRIFT_EVENTS if res_a.passed else 1
        ),
        shutter_2opt_xsync_efcs_or_nr_drift_events=(
            P370_SHUTTER_2OPT_XSYNC_EFCS_OR_NR_DRIFT_EVENTS if res_a.passed else 1
        ),
        creative_look_8param_override_or_softskin_drift_events=(
            P370_CREATIVE_LOOK_8PARAM_OVERRIDE_OR_SOFTSKIN_DRIFT_EVENTS if res_b.passed else 1
        ),
        delete_protect_recoverdb_slot1_vault_drift_events=(
            P370_DELETE_PROTECT_RECOVERDB_SLOT1_VAULT_DRIFT_EVENTS if res_b.passed else 1
        ),
        slot1_data_sector_writes=(
            P370_SLOT1_DATA_SECTOR_WRITES if (res_a.passed and res_b.passed) else 1
        ),
        slot1_sector_writes=(
            P370_SLOT1_SECTOR_WRITES if (res_a.passed and res_b.passed) else 1
        ),
        slot1_vault_mutation_bytes=(
            P370_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        cnflasha_writes=(P370_CNFLASHA_WRITES if (res_a.passed and res_b.passed) else 4096),
        rf_packets_transmitted=P370_RF_PACKETS_TRANSMITTED,
        rf_nvs_mutation_bytes=P370_RF_NVS_MUTATION_BYTES,
        slot1_format_hard_locked=P370_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_eopnotsupp_enforced=P370_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        slot1_vault_erofs_ebusy_enforced=P370_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
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
        emmc_writes_authorized=P370_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(safety_errs),
    )


def _apply_master68_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def _master68_local_donors_available() -> bool:
    """Return True only when all 17 Wave-66 local donors exist."""
    required_relpaths: Tuple[str, ...] = (
        P370_DONOR_FX3_APPFW_702_RELPATH,
        P370_DONOR_FX3_BACKUP_BIN_RELPATH,
        P370_DONOR_FX6_APPFW_601_RELPATH,
        P370_DONOR_FX3_UXC_EN_F_RELPATH,
        P370_DONOR_FX3_UXC_SC_F_RELPATH,
        P370_DONOR_FX3_UXC_TC_F_RELPATH,
        P370_DONOR_FX3_UXC_JA_F_RELPATH,
        P370_DONOR_FX3_UXC_EN_RELPATH,
        P370_DONOR_FX3_UXC_SC_RELPATH,
        P370_DONOR_FX3_UXC_TC_RELPATH,
        P370_DONOR_FX3_UXC_JA_RELPATH,
        P370_DONOR_FX3_UXC_EN_G_RELPATH,
        P370_DONOR_FX3_UXC_SC_G_RELPATH,
        P370_DONOR_FX3_UXC_TC_G_RELPATH,
        P370_DONOR_FX3_UXC_JA_G_RELPATH,
        P370_DONOR_FX6_UXC_EN_RELPATH,
        P370_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for relpath in required_relpaths:
        try:
            resolved = _resolve_phase370_donor_path(relpath)
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


def evaluate_realhw_68pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master68PillarRecoveryReport:
    """Evaluate and aggregate all 68 recovery pillars (`1..68`) concurrently -> `68/68` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_68_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    if resolved_clean_room is None and not _master68_local_donors_available():
        resolved_clean_room = True
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_67pillar() -> Master67PillarRecoveryReport:
        return evaluate_realhw_67pillar_recovery_master(**kw)

    def _run_p68() -> Tuple[Pillar68StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar68_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_67 = pool.submit(_run_67pillar)
        fut_68 = pool.submit(_run_p68)
        m67_rep = fut_67.result()
        p68_rep, p68_dt = fut_68.result()

    all_errors: List[str] = list(m67_rep.errors) + list(p68_rep.errors)
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
        if getattr(m67_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-67 violated {attr_name} == {expected_val}")
        if getattr(p68_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 68 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("drive_mode_or_dormant_focus_bracket_drift_events", 0),
        ("shutter_2opt_xsync_efcs_or_nr_drift_events", 0),
        ("creative_look_8param_override_or_softskin_drift_events", 0),
        ("delete_protect_recoverdb_slot1_vault_drift_events", 0),
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
        if getattr(p68_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 68 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m67_rep.pillars)
    spec68 = MASTER_68_PILLAR_SPECS[67]
    p68_metrics = {
        "pillar_68a_drive_focusbracket_shutter_efcs_nr_vault": (
            f"{p68_rep.pillar_68a_drive_focusbracket_shutter_efcs_nr_vault.scenarios_passed}/"
            f"{p68_rep.pillar_68a_drive_focusbracket_shutter_efcs_nr_vault.scenarios_total}"
        ),
        "pillar_68b_creativelook_softskin_recoverdb_vault": (
            f"{p68_rep.pillar_68b_creativelook_softskin_recoverdb_vault.scenarios_passed}/"
            f"{p68_rep.pillar_68b_creativelook_softskin_recoverdb_vault.scenarios_total}"
        ),
        "drive_mode_or_dormant_focus_bracket_drift_events": (
            p68_rep.drive_mode_or_dormant_focus_bracket_drift_events
        ),
        "shutter_2opt_xsync_efcs_or_nr_drift_events": (
            p68_rep.shutter_2opt_xsync_efcs_or_nr_drift_events
        ),
        "creative_look_8param_override_or_softskin_drift_events": (
            p68_rep.creative_look_8param_override_or_softskin_drift_events
        ),
        "delete_protect_recoverdb_slot1_vault_drift_events": (
            p68_rep.delete_protect_recoverdb_slot1_vault_drift_events
        ),
        "slot1_data_sector_writes": p68_rep.slot1_data_sector_writes,
        "slot1_sector_writes": p68_rep.slot1_sector_writes,
        "slot1_vault_mutation_bytes": p68_rep.slot1_vault_mutation_bytes,
        "cnflasha_writes": p68_rep.cnflasha_writes,
        "slot1_format_hard_locked": p68_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_eopnotsupp_enforced": p68_rep.slot1_vault_erofs_eopnotsupp_enforced,
        "overall_ready_for_hardware_attach": p68_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p68_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p68_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p68_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec68[0],
            pillar_id=spec68[1],
            phase_label=spec68[2],
            module_name=spec68[3],
            passed=bool(p68_rep.all_passed),
            status=p68_rep.status,
            verification_mode=p68_rep.verification_mode,
            elapsed_seconds=p68_dt,
            key_metrics=p68_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec68[1],
                    "mode": p68_rep.verification_mode,
                    "status": p68_rep.status,
                    "metrics": p68_metrics,
                    "passed": p68_rep.all_passed,
                }
            ),
            errors=tuple(p68_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master68_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p68_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_68_PILLAR_COUNT == 68
        and pillars_passed == 68
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE370_SCHEMA,
            "schema_version": PHASE370_MASTER_SCHEMA,
            "version": PHASE370_VERSION,
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

    return Master68PillarRecoveryReport(
        schema=PHASE370_SCHEMA,
        schema_version=PHASE370_MASTER_SCHEMA,
        version=PHASE370_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=(
            P370_STATUS_VERIFIED_68OF68_AGGREGATOR if all_ok else P370_STATUS_FAIL_68OF68_AGGREGATOR
        ),
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P370_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.50,
        under_6s_budget=elapsed < P370_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P370_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p68_rep.donor_snapshot,
        pillar68_a_drive_focusbracket_shutter_efcs_nr_vault=(
            p68_rep.pillar_68a_drive_focusbracket_shutter_efcs_nr_vault
        ),
        pillar68_b_creativelook_softskin_recoverdb_vault=(
            p68_rep.pillar_68b_creativelook_softskin_recoverdb_vault
        ),
        drive_mode_or_dormant_focus_bracket_drift_events=(
            p68_rep.drive_mode_or_dormant_focus_bracket_drift_events
        ),
        shutter_2opt_xsync_efcs_or_nr_drift_events=(
            p68_rep.shutter_2opt_xsync_efcs_or_nr_drift_events
        ),
        creative_look_8param_override_or_softskin_drift_events=(
            p68_rep.creative_look_8param_override_or_softskin_drift_events
        ),
        delete_protect_recoverdb_slot1_vault_drift_events=(
            p68_rep.delete_protect_recoverdb_slot1_vault_drift_events
        ),
        fx3_has_dormant_focus_bracket_exposed=P370_FX3_HAS_DORMANT_FOCUS_BRACKET_EXPOSED,
        fx3_has_shutter_type_auto_exposed=P370_FX3_HAS_SHUTTER_TYPE_AUTO_EXPOSED,
        fx3_has_dormant_soft_skin_exposed=P370_FX3_HAS_DORMANT_SOFT_SKIN_EXPOSED,
        fx6_has_still_drive_mode=P370_FX6_HAS_STILL_DRIVE_MODE,
        fx6_has_focus_bracket=P370_FX6_HAS_FOCUS_BRACKET,
        fx6_has_mechanical_shutter=P370_FX6_HAS_MECHANICAL_SHUTTER,
        fx6_has_efcs=P370_FX6_HAS_EFCS,
        fx6_has_long_exp_nr=P370_FX6_HAS_LONG_EXP_NR,
        fx6_has_creative_look=P370_FX6_HAS_CREATIVE_LOOK,
        fx6_has_soft_skin_effect=P370_FX6_HAS_SOFT_SKIN_EFFECT,
        fx3_drive_mode_resettable=P370_FX3_DRIVE_MODE_RESETTABLE,
        fx3_efcs_resettable=P370_FX3_EFCS_RESETTABLE,
        fx3_creative_look_resettable=P370_FX3_CREATIVE_LOOK_RESETTABLE,
        fx3_delete_confirm_resettable=P370_FX3_DELETE_CONFIRM_RESETTABLE,
        slot1_sector_writes=p68_rep.slot1_sector_writes,
        cnflasha_writes=p68_rep.cnflasha_writes,
        emmc_writes_authorized=P370_EMMC_WRITES_AUTHORIZED,
        zoom_ciz_lockout_or_8speed_reset_drift_events=(
            m67_rep.zoom_ciz_lockout_or_8speed_reset_drift_events
        ),
        autoslow_6lockout_or_minss_still_drift_events=(
            m67_rep.autoslow_6lockout_or_minss_still_drift_events
        ),
        dual_base_iso_curve_matrix_drift_events=m67_rep.dual_base_iso_curve_matrix_drift_events,
        dormant_lossless_arw_exposed_events=m67_rep.dormant_lossless_arw_exposed_events,
        hlg_still_or_sort_rec_spillover_drift_events=(
            m67_rep.hlg_still_or_sort_rec_spillover_drift_events
        ),
        usb_lun_single_slot1_msc_hazard_events=m67_rep.usb_lun_single_slot1_msc_hazard_events,
        npfz100_pd_interlock_or_dcc1_drift_events=m67_rep.npfz100_pd_interlock_or_dcc1_drift_events,
        dormant_uvc_streaming_exposed_events=m67_rep.dormant_uvc_streaming_exposed_events,
        fx3_zoom_range_resettable=m67_rep.fx3_zoom_range_resettable,
        fx3_zoom_speed_resettable=m67_rep.fx3_zoom_speed_resettable,
        fx3_has_dormant_lossless_arw_exposed=m67_rep.fx3_has_dormant_lossless_arw_exposed,
        fx3_has_native_uvc_streaming=m67_rep.fx3_has_native_uvc_streaming,
        fx6_has_native_uvc_streaming=m67_rep.fx6_has_native_uvc_streaming,
        fx6_has_digital_zoom=m67_rep.fx6_has_digital_zoom,
        fx6_has_still_arw_hlg_pipeline=m67_rep.fx6_has_still_arw_hlg_pipeline,
        fx6_has_iso_auto_min_ss=m67_rep.fx6_has_iso_auto_min_ss,
        slot1_data_sector_writes=(
            m67_rep.slot1_data_sector_writes + p68_rep.slot1_data_sector_writes
        ),
        slot1_vault_mutation_bytes=(
            m67_rep.slot1_vault_mutation_bytes + p68_rep.slot1_vault_mutation_bytes
        ),
        rf_packets_transmitted=m67_rep.rf_packets_transmitted + p68_rep.rf_packets_transmitted,
        rf_nvs_mutation_bytes=m67_rep.rf_nvs_mutation_bytes + p68_rep.rf_nvs_mutation_bytes,
        slot1_format_hard_locked=(
            m67_rep.slot1_format_hard_locked and p68_rep.slot1_format_hard_locked
        ),
        slot1_vault_erofs_eopnotsupp_enforced=(
            m67_rep.slot1_vault_erofs_eopnotsupp_enforced
            and p68_rep.slot1_vault_erofs_eopnotsupp_enforced
        ),
        slot1_vault_erofs_ebusy_enforced=(
            m67_rep.slot1_vault_erofs_ebusy_enforced and p68_rep.slot1_vault_erofs_ebusy_enforced
        ),
        breathing_comp_lockout_or_catalyst_drift_events=(
            m67_rep.breathing_comp_lockout_or_catalyst_drift_events
        ),
        file_settings_camid_reel_or_sdhc_drift_events=(
            m67_rep.file_settings_camid_reel_or_sdhc_drift_events
        ),
        copyright_46ch_reset_erratum_or_serial_drift_events=(
            m67_rep.copyright_46ch_reset_erratum_or_serial_drift_events
        ),
        camset_copyright_pii_leak_events=m67_rep.camset_copyright_pii_leak_events,
        camset_copyright_pii_leaked_bytes=m67_rep.camset_copyright_pii_leaked_bytes,
        powersave_9cond_or_dormant_monitor_drift_events=(
            m67_rep.powersave_9cond_or_dormant_monitor_drift_events
        ),
        dormant_power_save_by_monitor_exposed_events=(
            m67_rep.dormant_power_save_by_monitor_exposed_events
        ),
        ntsc_pal_reboot_or_slot1_format_drift_events=(
            m67_rep.ntsc_pal_reboot_or_slot1_format_drift_events
        ),
        hdmi_raw_output_or_media_vault_drift_events=(
            m67_rep.hdmi_raw_output_or_media_vault_drift_events
        ),
        hdmi_4k_only_or_gamut_removal_drift_events=(
            m67_rep.hdmi_4k_only_or_gamut_removal_drift_events
        ),
        desqueeze_ratio_lock_or_bypass_drift_events=(
            m67_rep.desqueeze_ratio_lock_or_bypass_drift_events
        ),
        rec_lamp_tally_or_emph_display_drift_events=(
            m67_rep.rec_lamp_tally_or_emph_display_drift_events
        ),
        dormant_var_shutter_or_apsc_reset_drift_events=(
            m67_rep.dormant_var_shutter_or_apsc_reset_drift_events
        ),
        dormant_var_shutter_exposed_events=m67_rep.dormant_var_shutter_exposed_events,
        hdmi_red_border_clean_feed_leak_pixels=(
            m67_rep.hdmi_red_border_clean_feed_leak_pixels
        ),
        recorded_media_desqueeze_pixels=m67_rep.recorded_media_desqueeze_pixels,
        fx6_sdi_desqueeze_pixels=m67_rep.fx6_sdi_desqueeze_pixels,
        shoe_audio_preemption_or_limiter_drift_events=(
            m67_rep.shoe_audio_preemption_or_limiter_drift_events
        ),
        subject_recog_myth_or_face_memory_drift_events=(
            m67_rep.subject_recog_myth_or_face_memory_drift_events
        ),
        silent_mode_target_or_barrier_drift_events=(
            m67_rep.silent_mode_target_or_barrier_drift_events
        ),
        bodydata_version_flash_or_slot1_vault_drift_events=(
            m67_rep.bodydata_version_flash_or_slot1_vault_drift_events
        ),
        dormant_shutter_when_pwr_off_exposed_events=(
            m67_rep.dormant_shutter_when_pwr_off_exposed_events
        ),
        hdmi_face_frame_pixels_emitted=m67_rep.hdmi_face_frame_pixels_emitted,
        cnflasha_pixel_map_mutation_bytes=m67_rep.cnflasha_pixel_map_mutation_bytes,
        slot1_bodydata_mutation_bytes=m67_rep.slot1_bodydata_mutation_bytes,
        bodydata_placement_or_flash_authorized=m67_rep.bodydata_placement_or_flash_authorized,
        ftp_protocol_sftp_or_jpeg_size_drift_events=(
            m67_rep.ftp_protocol_sftp_or_jpeg_size_drift_events
        ),
        wb_custom_cine_ei_or_shockless_drift_events=(
            m67_rep.wb_custom_cine_ei_or_shockless_drift_events
        ),
        movie_af_speed_or_focus_map_spoof_events=m67_rep.movie_af_speed_or_focus_map_spoof_events,
        marker_15ratio_peaking_hdmi_leak_events=m67_rep.marker_15ratio_peaking_hdmi_leak_events,
        zero_rf_usblan_or_slot1_avf_bypass_events=(
            m67_rep.zero_rf_usblan_or_slot1_avf_bypass_events
        ),
        usblan_packets_transmitted=m67_rep.usblan_packets_transmitted,
        hdmi_marker_peaking_pixels_emitted=m67_rep.hdmi_marker_peaking_pixels_emitted,
        slot1_avf_info_mutation_bytes=m67_rep.slot1_avf_info_mutation_bytes,
        rec_media_prioritize_or_autoswitch_drift_events=(
            m67_rep.rec_media_prioritize_or_autoswitch_drift_events
        ),
        card_speed_vpg200_vpg400_gate_drift_events=(
            m67_rep.card_speed_vpg200_vpg400_gate_drift_events
        ),
        proxy_sq_dci4k_or_120p_lockout_drift_events=(
            m67_rep.proxy_sq_dci4k_or_120p_lockout_drift_events
        ),
        cloud_init_persist_or_power_off_ble_rf_events=(
            m67_rep.cloud_init_persist_or_power_off_ble_rf_events
        ),
        mymenu_42slot_or_fx6_lock_spoof_events=m67_rep.mymenu_42slot_or_fx6_lock_spoof_events,
        zero_rf_or_slot1_vault_bypass_events=m67_rep.zero_rf_or_slot1_vault_bypass_events,
        slot1_dcim_m4root_avf_mutation_bytes=m67_rep.slot1_dcim_m4root_avf_mutation_bytes,
        big6_home_or_lower_left_nd_drift_events=m67_rep.big6_home_or_lower_left_nd_drift_events,
        framing_manual_or_dormant_auto_framing_drift_events=(
            m67_rep.framing_manual_or_dormant_auto_framing_drift_events
        ),
        interval_shoot_9999_or_fx6_mxf_spoof_events=(
            m67_rep.interval_shoot_9999_or_fx6_mxf_spoof_events
        ),
        tc_make_regen_or_hdmi_rec_ctrl_drift_events=(
            m67_rep.tc_make_regen_or_hdmi_rec_ctrl_drift_events
        ),
        access_authen_ssh_tls_or_fan_max_drift_events=(
            m67_rep.access_authen_ssh_tls_or_fan_max_drift_events
        ),
        slot1_dcim_avf_mutation_bytes=m67_rep.slot1_dcim_avf_mutation_bytes,
        fx3_has_var_shutter=m67_rep.fx3_has_var_shutter,
        fx3_has_builtin_evf=m67_rep.fx3_has_builtin_evf,
        fx3_has_builtin_end_filter=m67_rep.fx3_has_builtin_end_filter,
        fx3_has_bt_timecode_link=m67_rep.fx3_has_bt_timecode_link,
        fx3_has_dormant_auto_framing=m67_rep.fx3_has_dormant_auto_framing,
        fx3_has_dormant_auto_hdr=m67_rep.fx3_has_dormant_auto_hdr,
        fx3_has_dormant_bulb_timer=m67_rep.fx3_has_dormant_bulb_timer,
        fx3_has_dormant_divide_extract=m67_rep.fx3_has_dormant_divide_extract,
        fx3_has_fan_control_max=m67_rep.fx3_has_fan_control_max,
        fx3_has_movie_self_timer=m67_rep.fx3_has_movie_self_timer,
        fx3_has_movie_sort_recording=m67_rep.fx3_has_movie_sort_recording,
        fx3_has_physical_end_hw=m67_rep.fx3_has_physical_end_hw,
        fx3_has_5axis_ibis=m67_rep.fx3_has_5axis_ibis,
        fx3_has_power_save_by_monitor=m67_rep.fx3_has_power_save_by_monitor,
        fx6_has_ibis=m67_rep.fx6_has_ibis,
        fx6_has_fan_control_max=m67_rep.fx6_has_fan_control_max,
        fx6_has_still_self_timer=m67_rep.fx6_has_still_self_timer,
        fx6_has_fn_menu=m67_rep.fx6_has_fn_menu,
        fx6_has_my_dial=m67_rep.fx6_has_my_dial,
        fx6_has_bluetooth_hardware=m67_rep.fx6_has_bluetooth_hardware,
        fx6_has_av_tv_rotate=m67_rep.fx6_has_av_tv_rotate,
        fx6_has_exif_copyright_menu=m67_rep.fx6_has_exif_copyright_menu,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        master_68pillar_sha256=master_sha,
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


def evaluate_68pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master68PillarRecoveryReport:
    """Short alias for `evaluate_realhw_68pillar_recovery_master`."""
    return evaluate_realhw_68pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_68pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master68PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_68pillar_recovery_master`."""
    return evaluate_realhw_68pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_68pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master68PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_68pillar_recovery_master`."""
    return evaluate_realhw_68pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_68pillar_recovery(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master68PillarRecoveryReport:
    """Milestone 364 dynamic discovery alias for `evaluate_realhw_68pillar_recovery_master`."""
    return evaluate_realhw_68pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_all_68_recovery_pillars(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master68PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_68pillar_recovery_master`."""
    return evaluate_realhw_68pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
