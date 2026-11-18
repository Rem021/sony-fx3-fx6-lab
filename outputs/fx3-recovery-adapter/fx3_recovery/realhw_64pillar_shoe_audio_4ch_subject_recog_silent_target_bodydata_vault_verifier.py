"""Phase 352 Milestone — Recovery Pillar 64 & Concurrent 64/64 Master Recovery Verifier:
Wave-62 Sony ILME-FX3 (Ver. 7.02) vs ILME-FX6 (Ver. 6.01) Empirically Grounded Guardrails:
  * Pillar 64A: Digital MI Shoe `[Shoe Audio Set.]` (`48kHz/24bit 4ch`, `48kHz/24bit 2ch`,
    `48kHz/16bit 2ch` def), `[Audio Recording]` (`On` def/`Off`, disabled in `S&Q`),
    `[Audio Rec Level]` (`0..31`, def `26`, Delete resets, always-on body Limiter),
    `[Wind Noise Reduct.]` (internal mic only), `[Audio Out Timing]` (`Live` def / `Lip Sync`,
    under `Shooting -> [Audio Recording]`, NOT `Setup -> [Sound Option]`), removal of standalone
    `[Audio Level Display]` in Ver. 2.00..7.02 (`_f 0x7a36` dormant -> `EOPNOTSUPP=95`),
    `[4ch Audio Monitoring]` 5 stereo mixes (`CH1/CH2`, `CH3/CH4`, `CH1+3/CH2+4`, `CH1/CH1`,
    `CH2/CH2`), all main codecs supporting `24-bit 4ch LPCM` vs Proxy forced `MPEG-4 AAC-LC 2ch
    128 kbps` & disabled at `>= 100p/120p+`, hardware preemption (`3.5mm MIC` preempts MI Shoe &
    grays `[Shoe Audio Set.]`; `XLR-H1 HANDLE AUDIO=OFF` -> internal mic; `ANALOG` -> `48kHz/16bit
    2ch`; `INPUT1->CH1, INPUT2->CH2, INPUT3->CH3/CH4`) vs FX6 native `4ch 24-bit 48kHz`, physical
    `CH1..CH4` dials, 6-step `Limiter Mode` (`Off/-6/-9/-12/-15/-17 dB`), dormant `32bit float`;
    and `[Face/Eye AF] -> [Face/Eye Subject]` (`Human` def, `Animal` Still-only for Animal Eye AF
    via `VAL_HAITA_..._TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT` -> `EOPNOTSUPP=95` in Movie/S&Q,
    ZERO `Bird`/`Insect`/`Car/Train`/`Airplane` on FX3 Ver. 7.02 despite dormant BIONZ XR symbols
    and `BKID_APP_*airplane* == 0`), active `[Face Memory]` (max `8` faces, Reset-immune, NOT in
    `CAMSET*.DAT`, cleared by `Delete All`/`Initialize`), `[Face/Eye Frame Disp.]` def `Off`
    (`0 px` Clean-HDMI), vs FX6 `Human`-only `Face/Eye Detection AF` & session `Saved Tracking Face`.
  * Pillar 64B: `Shooting -> [Shutter/Silent] -> [Silent Mode Settings]` (`[Silent Mode]` `Off`
    def/`On` forcing electronic shutter + `[Audio signals]=Off` + locking 5 features: Flash,
    `Long Exposure NR`, `e-Front Curtain Shut.`, `BULB`, `Anti-flicker Shoot.`, while
    `[AF Illuminator]` is NOT auto-disabled) + `[Target Function Settings]` strictly `2` items
    (`[Aperture Drive in AF]` Still-only `Standard`/`Silent Priority`/`Not Target`;
    `[Auto Pixel Mapping]` `Off` def/`Not Target` suppressing shutdown shutter actuation &
    `cnflasha` defect-map write), ZERO exposed `[Shutter When Pwr OFF]` on FX3 Ver. 7.02
    (`dormant_shutter_when_pwr_off_exposed_events == 0` -> `EOPNOTSUPP=95`; FX6 has 0 mechanical
    shutter); `Setup -> [Setup Option] -> [Version]` & `[Software Update]` (`BODYDATA.DAT`
    strictly `Slot 1` root, `Slot 2` ignored vs FX6 `Slot B` root + mandatory `AC Adaptor`,
    `NP-FZ100 >= 51%`, mandatory `Ver. 2.04/2.05` stepping-stone before `Ver. 7.02` from
    `<= Ver. 2.02`, `5 long/6 short` & `7 long/7 short` LED error codes, TC/UB reset); and Hard
    Safety & Tier-0 Recovery Vault Firewall (`bodydata_placement_or_flash_authorized == False`,
    `cross_model_flash_authorized == False`, `emmc_writes_authorized == False`,
    `hardware_live_attachment_authorized == False`, `Slot 1` staging/write -> `EROFS=30`,
    `slot1_data_sector_writes == 0`, Stage-B `/tmp` overlay, `Backup.bin H0 == H3`).
  * Unified 64/64 Master Recovery Aggregator (Pillars 1..63 + Pillar 64).

Safety Redlines (HARD-LOCKED):
  - Zero hardware attach, zero physical device writes, zero USB/UART TX, zero OTP/RPMB, zero eMMC writes.
  - Zero `BODYDATA.DAT` staging/placement or cross-model flash (`NO-GO`).
  - Zero raw firmware bytes leaked (`raw_firmware_bytes_leaked == 0`).
  - Bounded `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` donor inspection (`<= 2.0s` budget) with explicit
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
    MASTER_63_PILLAR_SPECS,
    Master63PillarRecoveryReport,
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
    evaluate_realhw_63pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Phase 352 Metadata, Safety Redlines & Pinned Budget Constants
# ---------------------------------------------------------------------------

PHASE352_SCHEMA = (
    "realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier_v1"
)
PHASE352_MASTER_SCHEMA = "realhw_64pillar_recovery_master_v1"
PHASE352_VERSION = "1.0.0"
PHASE352_PHASE_NUMBER = 352

P352_ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"

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

P352_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED = False
P352_CROSS_MODEL_FLASH_AUTHORIZED = False
P352_EMMC_WRITES_AUTHORIZED = False
P352_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
P352_OVERALL_READY_FOR_HARDWARE_ATTACH = False

OTP_FUSE_TOUCHES = 0
OTP_FUSE_WRITES = 0
RPMB_COUNTER_INCREMENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PHYSICAL_DEVICE_WRITES = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

P352_BOUNDED_HEADER_BYTES = 4096
P352_MAX_FULL_DONOR_BYTES = 3_000_000
P352_DONOR_INSPECT_BUDGET_SECONDS = 2.0
P352_DONOR_INSPECT_CI_BUDGET_SECONDS = 2.0
P352_FAST_CLI_BUDGET_SECONDS = 1.50
P352_NOMINAL_BUDGET_SECONDS = 4.00
P352_CONCURRENT_CEILING_SECONDS = 6.00

P352_ENOENT_ERRNO = 2
P352_EBUSY_ERRNO = 16
P352_EINVAL_ERRNO = 22
P352_EROFS_ERRNO = 30
P352_EOPNOTSUPP_ERRNO = 95

# Camera Identities
P352_FX3_MODEL_NAME = "ILME-FX3"
P352_FX3_MODEL_ID = 0x91030080
P352_FX3_PRODUCT_CODENAME = "PRODUCT_MODEL_ALCIN_UUD"
P352_FX3_HELPGUIDE_ID = "ilc/2210"
P352_FX3_FW_VERSION = "7.02"
P352_FX3_SUPPORTED_FW_VERSIONS = (
    "7.02", "7.01", "7.00", "6.02", "6.00", "5.00", "4.00", "3.00", "2.05", "2.04", "2.02", "2.00"
)
P352_FX3_STEPPING_STONE_VERSIONS = ("2.04", "2.05")
P352_FX3_LEGACY_PRE_STEPPING_VERSIONS = ("2.02", "2.00", "1.01", "1.00")

P352_FX6_DONOR_MODEL_NAME = "ILME-FX6"
P352_FX6_DONOR_FW_VERSION = "6.01"
P352_FX6_PRODUCT_CODENAME = "PRODUCT_MODEL_CHAPLIN"

# Pinned Donor Relpaths & Digests (21 Wave-62 donors: 16 FX3 + 5 FX6)
P352_DONOR_FX3_APPFW_702_RELPATH = P348_DONOR_FX3_APPFW_702_RELPATH
P352_DONOR_FX6_APPFW_601_RELPATH = P348_DONOR_FX6_APPFW_601_RELPATH
P352_DONOR_FX3_BACKUP_BIN_RELPATH = P348_DONOR_FX3_BACKUP_BIN_RELPATH
P352_DONOR_FX3_UXC_EN_F_RELPATH = P348_DONOR_FX3_UXC_EN_F_RELPATH
P352_DONOR_FX3_UXC_SC_F_RELPATH = P348_DONOR_FX3_UXC_SC_F_RELPATH
P352_DONOR_FX3_UXC_TC_F_RELPATH = P348_DONOR_FX3_UXC_TC_F_RELPATH
P352_DONOR_FX3_UXC_JA_F_RELPATH = P348_DONOR_FX3_UXC_JA_F_RELPATH
P352_DONOR_FX3_UXC_EN_RELPATH = P348_DONOR_FX3_UXC_EN_RELPATH
P352_DONOR_FX3_UXC_SC_RELPATH = P348_DONOR_FX3_UXC_SC_RELPATH
P352_DONOR_FX3_UXC_TC_RELPATH = P348_DONOR_FX3_UXC_TC_RELPATH
P352_DONOR_FX3_UXC_JA_RELPATH = P348_DONOR_FX3_UXC_JA_RELPATH
P352_DONOR_FX3_UXC_EN_G_RELPATH = P348_DONOR_FX3_UXC_EN_G_RELPATH
P352_DONOR_FX3_UXC_SC_G_RELPATH = P348_DONOR_FX3_UXC_SC_G_RELPATH
P352_DONOR_FX3_UXC_TC_G_RELPATH = P348_DONOR_FX3_UXC_TC_G_RELPATH
P352_DONOR_FX3_UXC_JA_G_RELPATH = P348_DONOR_FX3_UXC_JA_G_RELPATH
P352_DONOR_FX6_UXC_EN_RELPATH = P348_DONOR_FX6_UXC_EN_RELPATH
P352_DONOR_FX6_UXC_EN_2_RELPATH = P348_DONOR_FX6_UXC_EN_2_RELPATH
P352_DONOR_FX3_LIBSDFILEUPDATER_RELPATH = (
    "fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/lib/libsdfileinputupdaterapi.so"
)
P352_DONOR_FX3_702_BODYDATA_RELPATH = "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P352_DONOR_FX6_AVBB_AUDIO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/scenario/AVBB_SCN_START_AUDIO.so"
)
P352_DONOR_FX6_LIBINFRAHOTSHOE_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraHotshoe.so"
)

P352_PINNED_FX3_APPFW_702_BYTES = P348_PINNED_FX3_APPFW_702_BYTES
P352_PINNED_FX3_APPFW_702_HDR4K_SHA256 = P348_PINNED_FX3_APPFW_702_HDR4K_SHA256
P352_PINNED_FX6_APPFW_601_BYTES = P348_PINNED_FX6_APPFW_601_BYTES
P352_PINNED_FX6_APPFW_601_HDR4K_SHA256 = P348_PINNED_FX6_APPFW_601_HDR4K_SHA256
P352_PINNED_FX3_BACKUP_BIN_BYTES = P348_PINNED_FX3_BACKUP_BIN_BYTES
P352_PINNED_FX3_BACKUP_BIN_SHA256 = P348_PINNED_FX3_BACKUP_BIN_SHA256
P352_PINNED_FX3_UXC_EN_F_BYTES = P348_PINNED_FX3_UXC_EN_F_BYTES
P352_PINNED_FX3_UXC_EN_F_SHA256 = P348_PINNED_FX3_UXC_EN_F_SHA256
P352_PINNED_FX3_UXC_SC_F_BYTES = P348_PINNED_FX3_UXC_SC_F_BYTES
P352_PINNED_FX3_UXC_SC_F_SHA256 = P348_PINNED_FX3_UXC_SC_F_SHA256
P352_PINNED_FX3_UXC_TC_F_BYTES = P348_PINNED_FX3_UXC_TC_F_BYTES
P352_PINNED_FX3_UXC_TC_F_SHA256 = P348_PINNED_FX3_UXC_TC_F_SHA256
P352_PINNED_FX3_UXC_JA_F_BYTES = P348_PINNED_FX3_UXC_JA_F_BYTES
P352_PINNED_FX3_UXC_JA_F_SHA256 = P348_PINNED_FX3_UXC_JA_F_SHA256
P352_PINNED_FX3_UXC_EN_BYTES = P348_PINNED_FX3_UXC_EN_BYTES
P352_PINNED_FX3_UXC_EN_SHA256 = P348_PINNED_FX3_UXC_EN_SHA256
P352_PINNED_FX3_UXC_SC_BYTES = P348_PINNED_FX3_UXC_SC_BYTES
P352_PINNED_FX3_UXC_SC_SHA256 = P348_PINNED_FX3_UXC_SC_SHA256
P352_PINNED_FX3_UXC_TC_BYTES = P348_PINNED_FX3_UXC_TC_BYTES
P352_PINNED_FX3_UXC_TC_SHA256 = P348_PINNED_FX3_UXC_TC_SHA256
P352_PINNED_FX3_UXC_JA_BYTES = P348_PINNED_FX3_UXC_JA_BYTES
P352_PINNED_FX3_UXC_JA_SHA256 = P348_PINNED_FX3_UXC_JA_SHA256
P352_PINNED_FX3_UXC_EN_G_BYTES = P348_PINNED_FX3_UXC_EN_G_BYTES
P352_PINNED_FX3_UXC_EN_G_SHA256 = P348_PINNED_FX3_UXC_EN_G_SHA256
P352_PINNED_FX3_UXC_SC_G_BYTES = P348_PINNED_FX3_UXC_SC_G_BYTES
P352_PINNED_FX3_UXC_SC_G_SHA256 = P348_PINNED_FX3_UXC_SC_G_SHA256
P352_PINNED_FX3_UXC_TC_G_BYTES = P348_PINNED_FX3_UXC_TC_G_BYTES
P352_PINNED_FX3_UXC_TC_G_SHA256 = P348_PINNED_FX3_UXC_TC_G_SHA256
P352_PINNED_FX3_UXC_JA_G_BYTES = P348_PINNED_FX3_UXC_JA_G_BYTES
P352_PINNED_FX3_UXC_JA_G_SHA256 = P348_PINNED_FX3_UXC_JA_G_SHA256
P352_PINNED_FX6_UXC_EN_BYTES = P348_PINNED_FX6_UXC_EN_BYTES
P352_PINNED_FX6_UXC_EN_SHA256 = P348_PINNED_FX6_UXC_EN_SHA256
P352_PINNED_FX6_UXC_EN_2_BYTES = P348_PINNED_FX6_UXC_EN_2_BYTES
P352_PINNED_FX6_UXC_EN_2_SHA256 = P348_PINNED_FX6_UXC_EN_2_SHA256
P352_PINNED_FX3_LIBSDFILEUPDATER_BYTES = 60584
P352_PINNED_FX3_LIBSDFILEUPDATER_SHA256 = (
    "257164d1cdf88757b8c0e2ba08ac47b06c46007410af308b7a8571b442b00cd2"
)
P352_PINNED_FX3_702_BODYDATA_BYTES = 811876768
P352_PINNED_FX3_702_BODYDATA_HDR4K_SHA256 = (
    "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
)
P352_PINNED_FX6_AVBB_AUDIO_BYTES = 70096
P352_PINNED_FX6_AVBB_AUDIO_SHA256 = (
    "96252cad4c9c13575a6c071be9f9fe72853382af7a4133bac7257e056f71420a"
)
P352_PINNED_FX6_LIBINFRAHOTSHOE_BYTES = 47808
P352_PINNED_FX6_LIBINFRAHOTSHOE_SHA256 = (
    "0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6"
)

# Zero-Violation Pillar 64 Counters & Vault Flags
P352_SHOE_AUDIO_PREEMPTION_OR_LIMITER_DRIFT_EVENTS = 0
P352_SUBJECT_RECOG_MYTH_OR_FACE_MEMORY_DRIFT_EVENTS = 0
P352_SILENT_MODE_TARGET_OR_BARRIER_DRIFT_EVENTS = 0
P352_BODYDATA_VERSION_FLASH_OR_SLOT1_VAULT_DRIFT_EVENTS = 0
P352_DORMANT_SHUTTER_WHEN_PWR_OFF_EXPOSED_EVENTS = 0

P352_SLOT1_DATA_SECTOR_WRITES = 0
P352_SLOT1_BODYDATA_MUTATION_BYTES = 0
P352_SLOT1_VAULT_MUTATION_BYTES = 0
P352_CNFLASHA_PIXEL_MAP_MUTATION_BYTES = 0
P352_HDMI_FACE_FRAME_LEAK_PIXELS = 0
P352_RF_PACKETS_TRANSMITTED = 0
P352_RF_NVS_MUTATION_BYTES = 0
P352_SLOT1_FORMAT_HARD_LOCKED = True
P352_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True
P352_AIRPLANE_MODE_FORCED_ON = True

P352_STAGE_B_VOLATILE_OVERLAY_DIR = "/tmp/fx3_stage_b_overlay/pillar64"
P352_FORBIDDEN_PERSISTENT_TARGETS = (
    "/dev/cnflasha",
    "/setting",
    "/mnt/emmc",
    "/nflasha",
)
P352_TIER0_SURFACE_COUNT = 16

# ---------------------------------------------------------------------------
# Wave-62 Empirically Verified Constants (UXC resid16 & ELF Symbols)
# ---------------------------------------------------------------------------

# 1. Digital MI Shoe `[Shoe Audio Set.]`, `XLR-H1` / `3.5mm` Preemption & `[Audio Out Timing]`
P352_AUDIO_RECORDING_F_RESID16 = 0x72D3
P352_AUDIO_RECORDING_BASE_RESID16 = 0xE72E
P352_AUDIO_REC_LEVEL_F_RESID16S = (0x63B9, 0x6F0A)
P352_SHOE_AUDIO_SET_F_RESID16 = 0x77F6
P352_SHOE_AUDIO_OPTION_F_RESID16S = (0x6195, 0x70BC, 0x6DDE)
P352_WIND_NOISE_REDUCT_F_RESID16 = 0x7B2A
P352_WIND_NOISE_REDUCT_BASE_RESID16S = (0xE4B1, 0xE4AE)
P352_AUDIO_OUT_TIMING_F_RESID16S = (0x62D8, 0x6BC2)
P352_AUDIO_OUT_LIVE_F_RESID16S = (0x753D, 0x7AF3)
P352_AUDIO_OUT_LIP_SYNC_F_RESID16S = (0x6066, 0x6BBC)
P352_DORMANT_AUDIO_LEVEL_DISPLAY_F_RESID16 = 0x7A36
P352_4CH_AUDIO_MONITORING_F_RESID16S = (0x70DD, 0x776E)

P352_BKID_AUDIO_REC = "BKID_APP_setting_audio_recording"
P352_BKID_AUDIO_REC_LEVEL = "BKID_APP_setting_audio_recording_level"
P352_BKID_SHOE_AUDIO_SET = "BKID_APP_setting_external_mic_audio_format"
P352_BKID_WIND_NOISE = "BKID_APP_setting_wind_noise_reduction"
P352_BKID_AUDIO_OUT_TIMING = "BKID_APP_setting_audio_output_timing"
P352_BKID_AUDIO_LEVEL_DISP_REMOVED = "BKID_APP_setting_audio_recording_level_display"
P352_BKID_4CH_AUDIO_MON = "BKID_APP_setting_4ch_audio_monitoring"
P352_BKID_HDMI_4CH_AUDIO_OUT = "BKID_APP_setting_hdmi_4ch_audio_output"

P352_AUDIO_REC_LEVEL_MIN = 0
P352_AUDIO_REC_LEVEL_MAX = 31
P352_AUDIO_REC_LEVEL_DEFAULT = 26
P352_FX3_LIMITER_CONFIGURABLE = False
P352_FX3_UI_EXPOSES_AUDIO_LEVEL_DISPLAY = False
P352_SHOE_AUDIO_FORMATS = ("48kHz/24bit 4ch", "48kHz/24bit 2ch", "48kHz/16bit 2ch")
P352_SHOE_AUDIO_FORMAT_DEFAULT = "48kHz/16bit 2ch"
P352_AUDIO_OUT_TIMINGS = ("Live", "Lip Sync")
P352_AUDIO_OUT_TIMING_DEFAULT = "Live"
P352_AUDIO_OUT_TIMING_MENU_PATH = "Shooting -> [Audio Recording]"
P352_SOUND_OPTION_MENU_PATH = "Setup -> [Sound Option]"
P352_4CH_AUDIO_MONITORING_MIXES = (
    "CH1/CH2",
    "CH3/CH4",
    "CH1+3/CH2+4",
    "CH1/CH1",
    "CH2/CH2",
)
P352_4CH_AUDIO_OUTPUT_CHANNELS = ("CH1/CH2", "CH3/CH4")
P352_FX3_MAIN_VIDEO_CODECS = (
    "XAVC HS 4K",
    "XAVC S 4K",
    "XAVC S HD",
    "XAVC S-I 4K",
    "XAVC S-I HD",
    "XAVC S-I DCI 4K",
)
P352_FX3_PROXY_AUDIO_SPEC = "MPEG-4 AAC-LC 2ch 128 kbps"
P352_FX3_PROXY_DISABLED_MIN_FPS = 100
P352_MI_SHOE_ATTACHED_DEVICES = ("NONE", "XLR-H1", "ECM-B1M", "ECM-B10", "LEGACY_ANALOG_SHOE")
P352_XLR_H1_SWITCH_MODES = ("DIGITAL", "ANALOG")
P352_FX6_LIMITER_MODES = ("Off", "-6 dB", "-9 dB", "-12 dB", "-15 dB", "-17 dB")
P352_FX6_DORMANT_32BIT_FLOAT_RESID16 = 0x3215
P352_FX6_32BIT_FLOAT_ACTIVE = False

# 2. `[Face/Eye AF]` Subject Myth-Busting (`Human`/`Animal`-Only vs Dormant Bird/Insect/Car/Train/Airplane)
P352_FACE_EYE_PRIOR_F_RESID16S = (0x68E6, 0x6BDD)
P352_FACE_EYE_SUBJECT_F_RESID16S = (0x70FA, 0x7643)
P352_SUBJECT_HUMAN_F_RESID16 = 0x763F
P352_SUBJECT_ANIMAL_F_RESID16 = 0x6511
P352_DORMANT_SUBJECT_F_RESID16S = {
    "Bird": 0x6CB1,
    "Animal/Bird": 0x6957,
    "Insect": 0x6996,
    "Car/Train": 0x674E,
    "Airplane": 0x7440,
}
P352_RIGHT_LEFT_EYE_SELECT_F_RESID16S = (0x63A5, 0x69FC)
P352_FACE_EYE_FRAME_DISP_F_RESID16S = (0x7183, 0x74E3)
P352_FACE_MEMORY_F_RESID16S = (0x6533, 0x6D87)
P352_REGIST_FACES_PRIORITY_F_RESID16S = (0x629C, 0x7063)

P352_ANIMAL_EYE_MOVIE_NOT_SUPPORT_SYMBOL = (
    "VAL_HAITA_setting_face_eye_af_subject_TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT"
)
P352_FX3_EXPOSED_SUBJECTS = ("Human", "Animal")
P352_FX3_DORMANT_SUBJECTS = ("Bird", "Animal/Bird", "Insect", "Car/Train", "Airplane")
P352_ALL_SUBJECT_TOKENS = P352_FX3_EXPOSED_SUBJECTS + P352_FX3_DORMANT_SUBJECTS
P352_FX3_SUBJECT_DEFAULT = "Human"
P352_FX3_BKID_APP_AIRPLANE_HITS = 0
P352_FX3_FACE_MEMORY_MAX_FACES = 8
P352_FX3_FACE_MEMORY_IN_CAMSET = False
P352_FX3_FACE_FRAME_DISP_DEFAULT = "Off"
P352_RIGHT_LEFT_EYE_MODES = ("Auto", "Right Eye", "Left Eye")
P352_FX6_FACE_EYE_MODES = ("Face/Eye Priority AF", "Face/Eye Only AF", "Off")
P352_FX6_DORMANT_REG_FACE_2UXC_RESID16 = 0x4312

# 3. `[Silent Mode Settings]` 2-Item `[Target Function Settings]` & Dormant `[Shutter When Pwr OFF]`
P352_SILENT_MODE_SETTINGS_F_RESID16S = (0x655F, 0x72DF)
P352_SILENT_MODE_F_RESID16 = 0x7046
P352_TARGET_FUNCTION_SETTINGS_F_RESID16 = 0x79C0
P352_APERTURE_DRIVE_IN_AF_F_RESID16 = 0x61B5
P352_SILENT_PRIORITY_F_RESID16 = 0x64D3
P352_NOT_TARGET_F_RESID16 = 0x64E7
P352_AUTO_PIXEL_MAPPING_F_RESID16 = 0x7734
P352_DORMANT_SHUTTER_PWR_OFF_F_RESID16 = 0x709F
P352_DORMANT_ANTI_DUST_F_RESID16 = 0x7495
P352_AUDIO_SIGNALS_BASE_RESID16 = 0xE0C8

P352_SILENT_TARGET_EXPOSED_ITEMS = ("Aperture Drive in AF", "Auto Pixel Mapping")
P352_SILENT_MODE_LOCKED_FEATURES = (
    "Flash",
    "Long Exposure NR",
    "e-Front Curtain Shut.",
    "BULB",
    "Anti-flicker Shoot.",
)
P352_SILENT_MODE_AF_ILLUMINATOR_AUTO_DISABLED = False
P352_APERTURE_DRIVE_MODES = ("Standard", "Silent Priority", "Not Target")
P352_APERTURE_DRIVE_DEFAULT = "Standard"
P352_AUTO_PIXEL_MAPPING_MODES = ("Off", "Not Target")
P352_AUTO_PIXEL_MAPPING_DEFAULT = "Off"
P352_FX3_SHUTTER_WHEN_PWR_OFF_EXPOSED = False
P352_FX6_HAS_MECHANICAL_SHUTTER = False
P352_FX6_AUTO_PIXEL_RESTORE_NS1_RESID16S = (0x2E4E, 0x324A)

# 4. `[Version]`, `BODYDATA.DAT` `Slot 1` Root & `NO-GO` Flash Firewall
P352_VERSION_BASE_RESID16 = 0xE396
P352_BODY_BASE_RESID16 = 0xEA58
P352_SOFTWARE_UPDATE_F_RESID16S = (0x6FD6, 0x7283)
P352_UPDATE_BADGE_G_RESID16 = 0x6516
P352_LENS_VERSION_G_RESID16 = 0x6517
P352_UPDATE_VERSION_ERR_G_RESID16 = 0x630A
P352_FX6_VERSION_NS2_RESID16 = 0x5655
P352_FX6_VERSION_UP_2UXC_RESID16 = 0x462C

P352_BODYDATA_FILENAME = "BODYDATA.DAT"
P352_FX3_UPDATE_SLOT = "Slot 1"
P352_FX6_UPDATE_SLOT = "Slot B"
P352_FX3_MIN_BATTERY_PCT = 51
P352_FX3_MIN_BATTERY_BARS = 3
P352_FX3_LED_ERROR_CODES = ("5 long / 6 short", "7 long / 7 short")
P352_FX3_VALID_LED_PROGRESS = (1, 3, 5)
P352_FX3_TC_UB_RESET_ON_UPDATE = True

# Common Enums & Vault Constants
P352_ON_OFF_MODES = ("Off", "On")
P352_SHOOTING_DOMAINS = ("Movie", "Still", "S&Q")
P352_RESET_ACTIONS = ("None", "Camera Settings Reset", "Delete All", "Initialize")
P352_VAULT_ACTIONS = (
    "NONE",
    "READ_ONLY_AUDIT",
    "STAGE_BODYDATA_SLOT1",
    "TRIGGER_SOFTWARE_UPDATE_SLOT1",
    "CROSS_MODEL_FLASH_FX6_TO_FX3",
    "CNFLASHA_DEFECT_MAP_WRITE",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P352_WRITE_MUTATING_VAULT_ACTIONS = (
    "STAGE_BODYDATA_SLOT1",
    "TRIGGER_SOFTWARE_UPDATE_SLOT1",
    "CROSS_MODEL_FLASH_FX6_TO_FX3",
    "CNFLASHA_DEFECT_MAP_WRITE",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P352_VAULT_FIREWALL_ERRNOS = (None, "EROFS", "EOPNOTSUPP", "EBUSY", "EINVAL", "ENOENT")

# Status & Block Codes
P352_STATUS_VERIFIED_PILLAR_64A = "VERIFIED_PILLAR_64A_SHOE_AUDIO_4CH_SUBJECT_RECOG_VAULT"
P352_STATUS_REJECTED_PILLAR_64A = "REJECTED_PILLAR_64A_SHOE_AUDIO_4CH_SUBJECT_RECOG_VAULT"
P352_STATUS_VERIFIED_PILLAR_64B = "VERIFIED_PILLAR_64B_SILENT_TARGET_VERSION_BODYDATA_VAULT"
P352_STATUS_REJECTED_PILLAR_64B = "REJECTED_PILLAR_64B_SILENT_TARGET_VERSION_BODYDATA_VAULT"
P352_STATUS_VERIFIED_PILLAR64_SUITE = (
    "VERIFIED_PILLAR64_SHOE_AUDIO_4CH_SUBJECT_RECOG_SILENT_TARGET_BODYDATA_VAULT"
)
P352_STATUS_FAIL_PILLAR64_SUITE = (
    "FAIL_PILLAR64_SHOE_AUDIO_4CH_SUBJECT_RECOG_SILENT_TARGET_BODYDATA_VAULT"
)
P352_STATUS_VERIFIED_64OF64_AGGREGATOR = "VERIFIED_64OF64_PILLAR_RECOVERY_MASTER"
P352_STATUS_FAIL_64OF64_AGGREGATOR = "FAIL_64OF64_PILLAR_RECOVERY_MASTER"

P352_BLOCKED_SAFETY_POLICY_VIOLATION = "BLOCKED_P352_SAFETY_POLICY_VIOLATION"
P352_BLOCKED_INVALID_PILLAR64A_SPEC = "BLOCKED_P352_INVALID_PILLAR64A_SPEC"
P352_BLOCKED_INVALID_PILLAR64B_SPEC = "BLOCKED_P352_INVALID_PILLAR64B_SPEC"
P352_BLOCKED_SHOE_AUDIO_PREEMPTION_OR_LIMITER_DRIFT = (
    "BLOCKED_P352_SHOE_AUDIO_PREEMPTION_OR_LIMITER_DRIFT"
)
P352_BLOCKED_SUBJECT_RECOG_MYTH_OR_FACE_MEMORY_DRIFT = (
    "BLOCKED_P352_SUBJECT_RECOG_MYTH_OR_FACE_MEMORY_DRIFT"
)
P352_BLOCKED_SILENT_TARGET_OR_SHUTTER_BARRIER_DRIFT = (
    "BLOCKED_P352_SILENT_TARGET_OR_SHUTTER_BARRIER_DRIFT"
)
P352_BLOCKED_BODYDATA_VERSION_FLASH_OR_SLOT1_VAULT = (
    "BLOCKED_P352_BODYDATA_VERSION_FLASH_OR_SLOT1_VAULT"
)
P352_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL = "BLOCKED_P352_SLOT1_VAULT_WRITE_FIREWALL"
P352_BLOCKED_PERSISTENT_OVERLAY_ESCAPE = "BLOCKED_P352_PERSISTENT_OVERLAY_ESCAPE"
P352_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT = "BLOCKED_P352_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P352_PILLAR_64A_SCENARIO_IDS = (
    "p352_64a_01_allow_xlr_h1_48khz_24bit_4ch_audio_out_timing_live_and_proxy_aac_2ch",
    "p352_64a_02_allow_human_animal_still_only_face_memory_8_reset_immune_and_fx6_contrast",
    "p352_64a_03_reject_35mm_preempt_xlrh1_analog_cap_sq_audio_or_removed_audio_level_disp",
    "p352_64a_04_reject_dormant_bird_insect_car_airplane_or_movie_animal_eye_af_spoof",
    "p352_64a_05_reject_face_memory_camset_leak_or_hdmi_frame_disp_clean_hdmi_leak",
    "p352_64a_06_reject_slot1_vault_write_overlay_escape_or_backup_bin_h0_h3_drift",
)
P352_PILLAR_64B_SCENARIO_IDS = (
    "p352_64b_01_allow_silent_mode_5locks_2item_target_auto_pixel_off_and_af_illum_intact",
    "p352_64b_02_allow_fx3_slot1_readonly_version_audit_stepping_stone_and_fx6_slotb_contrast",
    "p352_64b_03_reject_exposed_shutter_when_pwr_off_or_3rd_silent_target_item_spoof",
    "p352_64b_04_reject_bypassing_ver204_stepping_stone_low_battery_or_slot2_bodydata_spoof",
    "p352_64b_05_reject_bodydata_slot1_stage_trigger_update_or_cross_model_flash_nogo",
    "p352_64b_06_reject_cnflasha_pixel_map_write_overlay_escape_or_tier0_h0_h3_drift",
)

MASTER_64_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_63_PILLAR_SPECS + (
    (
        64,
        "pillar64_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault",
        "Phase 352",
        "realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier",
    ),
)
MASTER_64_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_64_PILLAR_SPECS)
MASTER_64_PILLAR_COUNT = len(MASTER_64_PILLAR_IDS)


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
    return bool(is_forced_clean_room() or os.environ.get(P352_ENV_CLEAN_ROOM_TEST) == "1")


def _donor_inspect_budget_seconds() -> float:
    return (
        P352_DONOR_INSPECT_CI_BUDGET_SECONDS
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS")
        else P352_DONOR_INSPECT_BUDGET_SECONDS
    )


def _is_tmpfs_path(path: str) -> bool:
    norm = posixpath.normpath(path)
    return norm == "/tmp" or norm.startswith("/tmp/")


def _targets_persistent_emmc(path: str) -> bool:
    norm = posixpath.normpath(path)
    return any(norm == p or norm.startswith(p + "/") for p in P352_FORBIDDEN_PERSISTENT_TARGETS)


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
        ("BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED", BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED, False),
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
# Empirically Grounded State Calculators (Pillars 64A & 64B)
# ---------------------------------------------------------------------------


def compute_expected_shoe_audio_subject_recog_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    audio_recording_enabled: bool,
    audio_rec_level: int,
    shoe_audio_set: str,
    wind_noise_reduct: str,
    audio_out_timing: str,
    audio_out_timing_menu_location: str,
    audio_level_display_menu_requested: bool,
    monitoring_4ch_mix: str,
    hdmi_4ch_audio_out: str,
    video_codec: str,
    recording_fps: int,
    proxy_recording_enabled: bool,
    jack_35mm_mic_inserted: bool,
    mi_shoe_device: str,
    xlr_h1_handle_audio_on: bool,
    xlr_h1_digital_analog_switch: str,
    xlr_h1_input_select: str,
    fx3_limiter_configurable_requested: bool,
    fx6_limiter_mode: str,
    fx6_32bit_float_requested: bool,
    face_eye_prior_in_af: str,
    face_eye_subject: str,
    right_left_eye_select: str,
    face_eye_frame_disp: str,
    face_memory_count: int,
    face_memory_exported_in_camset: bool,
    regist_faces_priority: str,
    hdmi_info_display: str,
    fx6_face_eye_detection_mode: str,
    fx6_saved_tracking_face_active: bool,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute canonical Wave-62 Pillar 64A state:
    - `[Audio Recording]` (`On` def/`Off`, disabled in `S&Q`), `[Audio Rec Level]` (`0..31` def `26`),
      `[Shoe Audio Set.]` (`48kHz/24bit 4ch`, `48kHz/24bit 2ch`, `48kHz/16bit 2ch` def),
      `[Wind Noise Reduct.]` (internal mic only), `[Audio Out Timing]` (`Live`/`Lip Sync`) under
      `Shooting -> [Audio Recording]`, removal of standalone `[Audio Level Display]` in Ver. 2+,
      all main codecs supporting `24-bit 4ch LPCM` vs Proxy forced `MPEG-4 AAC-LC 2ch 128 kbps` &
      disabled `>= 100p`, and hardware preemption (`3.5mm` > MI Shoe, `XLR-H1 HANDLE AUDIO=OFF`
      -> internal mic, `ANALOG` -> `48kHz/16bit 2ch`, `INPUT1->CH1/INPUT2->CH2/INPUT3->CH3+4`).
    - `[Face/Eye Subject]`: strictly `Human`/`Animal` on FX3 Ver. 7.02; `Animal` is Still-only for
      Eye AF (`EOPNOTSUPP=95` in Movie/S&Q); ZERO `Bird`/`Insect`/`Car/Train`/`Airplane`
      (`EOPNOTSUPP=95`), active `[Face Memory]` (`<= 8` faces, Reset-immune, NOT in `CAMSET*.DAT`),
      and `0 px` Clean-HDMI Face/Eye frame isolation."""
    is_fx3 = camera_model == P352_FX3_MODEL_NAME

    # 1. Audio Recording, 24-bit 4ch Codec/Proxy Matrix & Preemption Hierarchy
    sq_audio_errno: Optional[int] = (
        P352_EOPNOTSUPP_ERRNO if (shooting_domain == "S&Q" and audio_recording_enabled) else None
    )
    rec_level_valid = P352_AUDIO_REC_LEVEL_MIN <= audio_rec_level <= P352_AUDIO_REC_LEVEL_MAX
    audio_level_display_errno: Optional[int] = (
        P352_EOPNOTSUPP_ERRNO if (is_fx3 and audio_level_display_menu_requested) else None
    )
    audio_out_timing_path_ok = (
        (not is_fx3) or (audio_out_timing_menu_location == P352_AUDIO_OUT_TIMING_MENU_PATH)
    )
    limiter_errno: Optional[int] = (
        P352_EOPNOTSUPP_ERRNO if (is_fx3 and fx3_limiter_configurable_requested) else None
    )
    fx6_32bit_float_errno: Optional[int] = (
        P352_EOPNOTSUPP_ERRNO if fx6_32bit_float_requested else None
    )

    # Hardware input routing & preemption priority:
    #   1) 3.5mm MIC jack inserted -> forces 3.5mm 2ch analog & grays out [Shoe Audio Set.]
    #   2) MI Shoe digital device (`XLR-H1` w/ HANDLE AUDIO=ON or `ECM-B1M`/`ECM-B10`)
    #   3) Fallback to Internal Stereo Mic (also when XLR-H1 HANDLE AUDIO=OFF)
    if is_fx3:
        if jack_35mm_mic_inserted:
            effective_audio_source = "3.5mm_MIC_2CH_ANALOG"
            shoe_audio_set_grayed = True
            effective_shoe_audio_format = "48kHz/16bit 2ch"
            wind_noise_effective = "Off"
            ch12_source = "3.5mm_MIC"
            ch34_source = "NONE"
        elif mi_shoe_device == "XLR-H1" and not xlr_h1_handle_audio_on:
            effective_audio_source = "INTERNAL_MIC"
            shoe_audio_set_grayed = True
            effective_shoe_audio_format = "48kHz/16bit 2ch"
            wind_noise_effective = wind_noise_reduct
            ch12_source = "INTERNAL_MIC"
            ch34_source = "NONE"
        elif mi_shoe_device in ("XLR-H1", "ECM-B1M", "ECM-B10"):
            is_analog_shoe = (
                mi_shoe_device == "XLR-H1" and xlr_h1_digital_analog_switch == "ANALOG"
            )
            effective_audio_source = f"MI_SHOE_{mi_shoe_device}_{'ANALOG' if is_analog_shoe else 'DIGITAL'}"
            shoe_audio_set_grayed = False
            if is_analog_shoe:
                effective_shoe_audio_format = "48kHz/16bit 2ch"
                ch12_source = "INPUT1_INPUT2" if xlr_h1_input_select == "IN1_IN2" else "INPUT1_MIRROR"
                ch34_source = "NONE"
            else:
                effective_shoe_audio_format = shoe_audio_set
                if mi_shoe_device == "XLR-H1":
                    ch12_source = (
                        "INPUT1_INPUT2" if xlr_h1_input_select == "IN1_IN2" else "INPUT1_MIRROR"
                    )
                    ch34_source = "INPUT3_LR" if effective_shoe_audio_format == "48kHz/24bit 4ch" else "NONE"
                else:
                    ch12_source = mi_shoe_device
                    ch34_source = mi_shoe_device if effective_shoe_audio_format == "48kHz/24bit 4ch" else "NONE"
            wind_noise_effective = "Off"
        elif mi_shoe_device == "LEGACY_ANALOG_SHOE":
            effective_audio_source = "MI_SHOE_LEGACY_ANALOG"
            shoe_audio_set_grayed = True
            effective_shoe_audio_format = "48kHz/16bit 2ch"
            wind_noise_effective = "Off"
            ch12_source = "LEGACY_ANALOG_SHOE"
            ch34_source = "NONE"
        else:
            effective_audio_source = "INTERNAL_MIC"
            shoe_audio_set_grayed = True
            effective_shoe_audio_format = "48kHz/16bit 2ch"
            wind_noise_effective = wind_noise_reduct
            ch12_source = "INTERNAL_MIC"
            ch34_source = "NONE"
    else:
        effective_audio_source = "FX6_NATIVE_4CH_24BIT"
        shoe_audio_set_grayed = False
        effective_shoe_audio_format = "48kHz/24bit 4ch"
        wind_noise_effective = wind_noise_reduct
        ch12_source = "FX6_INPUT1_2"
        ch34_source = "FX6_CH3_CH4"

    main_codec_supports_24bit_4ch = video_codec in P352_FX3_MAIN_VIDEO_CODECS
    effective_main_audio_format = (
        "DISABLED_SQ"
        if shooting_domain == "S&Q" or not audio_recording_enabled
        else effective_shoe_audio_format
    )
    effective_proxy_allowed = (
        proxy_recording_enabled
        and shooting_domain == "Movie"
        and recording_fps < P352_FX3_PROXY_DISABLED_MIN_FPS
    )
    effective_proxy_audio_spec = (
        P352_FX3_PROXY_AUDIO_SPEC if effective_proxy_allowed else "DISABLED"
    )
    shoe_format_errno: Optional[int] = (
        P352_EOPNOTSUPP_ERRNO
        if (
            is_fx3
            and shoe_audio_set != "48kHz/16bit 2ch"
            and (
                jack_35mm_mic_inserted
                or (mi_shoe_device == "XLR-H1" and not xlr_h1_handle_audio_on)
                or (mi_shoe_device == "XLR-H1" and xlr_h1_digital_analog_switch == "ANALOG")
                or mi_shoe_device in ("NONE", "LEGACY_ANALOG_SHOE")
            )
        )
        else None
    )

    # 2. `[Face/Eye Subject]` Myth-Busting & `[Face Memory]` Matrix
    if is_fx3:
        subject_errno: Optional[int] = (
            None if face_eye_subject in P352_FX3_EXPOSED_SUBJECTS else P352_EOPNOTSUPP_ERRNO
        )
        # Animal Eye AF on ILME-FX3 Ver. 7.02 is Still-ONLY (`TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT`)
        animal_eye_af_effective = (
            face_eye_prior_in_af == "On"
            and face_eye_subject == "Animal"
            and shooting_domain == "Still"
        )
        animal_movie_errno: Optional[int] = (
            P352_EOPNOTSUPP_ERRNO
            if (face_eye_subject == "Animal" and shooting_domain != "Still")
            else None
        )
        regist_faces_priority_enabled = (
            face_eye_subject == "Human" and face_memory_count > 0
        )
    else:
        subject_errno = None if face_eye_subject == "Human" else P352_EOPNOTSUPP_ERRNO
        animal_eye_af_effective = False
        animal_movie_errno = P352_EOPNOTSUPP_ERRNO if face_eye_subject != "Human" else None
        regist_faces_priority_enabled = False

    face_memory_count_valid = 0 <= face_memory_count <= P352_FX3_FACE_MEMORY_MAX_FACES
    face_memory_camset_excluded_ok = not face_memory_exported_in_camset
    hdmi_face_frame_pixels_emitted = 0  # Clean-HDMI NEVER carries Face/Eye overlay!

    # 3. Reset Matrix (`Camera Settings Reset` vs `Delete All` vs `Initialize`)
    if reset_action == "Initialize":
        post_audio_recording_enabled = True
        post_audio_rec_level = P352_AUDIO_REC_LEVEL_DEFAULT
        post_shoe_audio_set = P352_SHOE_AUDIO_FORMAT_DEFAULT
        post_wind_noise_reduct = "Off"
        post_audio_out_timing = P352_AUDIO_OUT_TIMING_DEFAULT
        post_monitoring_4ch_mix = "CH1/CH2"
        post_face_eye_prior_in_af = "On"
        post_face_eye_subject = P352_FX3_SUBJECT_DEFAULT
        post_right_left_eye_select = "Auto"
        post_face_eye_frame_disp = P352_FX3_FACE_FRAME_DISP_DEFAULT
        post_regist_faces_priority = "On"
        post_face_memory_count = 0
    elif reset_action == "Delete All":
        post_audio_recording_enabled = audio_recording_enabled
        post_audio_rec_level = audio_rec_level
        post_shoe_audio_set = shoe_audio_set
        post_wind_noise_reduct = wind_noise_reduct
        post_audio_out_timing = audio_out_timing
        post_monitoring_4ch_mix = monitoring_4ch_mix
        post_face_eye_prior_in_af = face_eye_prior_in_af
        post_face_eye_subject = face_eye_subject
        post_right_left_eye_select = right_left_eye_select
        post_face_eye_frame_disp = face_eye_frame_disp
        post_regist_faces_priority = regist_faces_priority
        post_face_memory_count = 0
    elif reset_action == "Camera Settings Reset":
        post_audio_recording_enabled = True
        post_audio_rec_level = P352_AUDIO_REC_LEVEL_DEFAULT
        post_shoe_audio_set = P352_SHOE_AUDIO_FORMAT_DEFAULT
        post_wind_noise_reduct = "Off"
        post_audio_out_timing = P352_AUDIO_OUT_TIMING_DEFAULT
        post_monitoring_4ch_mix = "CH1/CH2"
        post_face_eye_prior_in_af = "On"
        post_face_eye_subject = P352_FX3_SUBJECT_DEFAULT
        post_right_left_eye_select = "Auto"
        post_face_eye_frame_disp = P352_FX3_FACE_FRAME_DISP_DEFAULT
        post_regist_faces_priority = "On"
        # [Face Memory] SURVIVES Camera Settings Reset!
        post_face_memory_count = face_memory_count
    else:
        post_audio_recording_enabled = audio_recording_enabled
        post_audio_rec_level = audio_rec_level
        post_shoe_audio_set = shoe_audio_set
        post_wind_noise_reduct = wind_noise_reduct
        post_audio_out_timing = audio_out_timing
        post_monitoring_4ch_mix = monitoring_4ch_mix
        post_face_eye_prior_in_af = face_eye_prior_in_af
        post_face_eye_subject = face_eye_subject
        post_right_left_eye_select = right_left_eye_select
        post_face_eye_frame_disp = face_eye_frame_disp
        post_regist_faces_priority = regist_faces_priority
        post_face_memory_count = face_memory_count

    # 4. Slot-1 Tier-0 Vault Firewall (`EROFS=30`)
    mutates_slot1 = (
        requested_vault_action in P352_WRITE_MUTATING_VAULT_ACTIONS
        or (
            requested_vault_slot == 1
            and requested_vault_action not in ("NONE", "READ_ONLY_AUDIT")
        )
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
        "sq_audio_errno": sq_audio_errno,
        "rec_level_valid": rec_level_valid,
        "audio_level_display_errno": audio_level_display_errno,
        "audio_out_timing_path_ok": audio_out_timing_path_ok,
        "limiter_errno": limiter_errno,
        "fx6_32bit_float_errno": fx6_32bit_float_errno,
        "effective_audio_source": effective_audio_source,
        "shoe_audio_set_grayed": shoe_audio_set_grayed,
        "effective_shoe_audio_format": effective_shoe_audio_format,
        "wind_noise_effective": wind_noise_effective,
        "ch12_source": ch12_source,
        "ch34_source": ch34_source,
        "main_codec_supports_24bit_4ch": main_codec_supports_24bit_4ch,
        "effective_main_audio_format": effective_main_audio_format,
        "effective_proxy_allowed": effective_proxy_allowed,
        "effective_proxy_audio_spec": effective_proxy_audio_spec,
        "shoe_format_errno": shoe_format_errno,
        "subject_errno": subject_errno,
        "animal_eye_af_effective": animal_eye_af_effective,
        "animal_movie_errno": animal_movie_errno,
        "regist_faces_priority_enabled": regist_faces_priority_enabled,
        "face_memory_count_valid": face_memory_count_valid,
        "face_memory_camset_excluded_ok": face_memory_camset_excluded_ok,
        "hdmi_face_frame_pixels_emitted": hdmi_face_frame_pixels_emitted,
        "post_audio_recording_enabled": post_audio_recording_enabled,
        "post_audio_rec_level": post_audio_rec_level,
        "post_shoe_audio_set": post_shoe_audio_set,
        "post_wind_noise_reduct": post_wind_noise_reduct,
        "post_audio_out_timing": post_audio_out_timing,
        "post_monitoring_4ch_mix": post_monitoring_4ch_mix,
        "post_face_eye_prior_in_af": post_face_eye_prior_in_af,
        "post_face_eye_subject": post_face_eye_subject,
        "post_right_left_eye_select": post_right_left_eye_select,
        "post_face_eye_frame_disp": post_face_eye_frame_disp,
        "post_regist_faces_priority": post_regist_faces_priority,
        "post_face_memory_count": post_face_memory_count,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


def compute_expected_silent_target_version_bodydata_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    silent_mode: str,
    target_aperture_drive_in_af: str,
    target_auto_pixel_mapping: str,
    requested_silent_target_extra_items: Tuple[str, ...],
    shutter_when_pwr_off_exposed_requested: bool,
    af_illuminator_setting: str,
    audio_signals_setting: str,
    shutter_type_setting: str,
    flash_requested: bool,
    long_exposure_nr_requested: bool,
    efcs_requested: bool,
    bulb_requested: bool,
    anti_flicker_requested: bool,
    lens_mounted_supports_fw_update: bool,
    airplane_mode: str,
    battery_percent: int,
    ac_adaptor_connected: bool,
    current_body_fw_version: str,
    target_body_fw_version: str,
    bodydata_filename: str,
    bodydata_target_slot: str,
    bodydata_stage_or_flash_requested: bool,
    cross_model_flash_requested: bool,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute canonical Wave-62 Pillar 64B state:
    - `[Silent Mode Settings]` (`Off` def / `On`): forces Electronic Shutter, `[Audio signals]=Off`,
      hard-locks 5 features (`Flash`, `Long Exposure NR`, `e-Front Curtain Shut.`, `BULB`,
      `Anti-flicker Shoot.`), leaves `[AF Illuminator]` NOT auto-disabled.
    - `[Target Function Settings]`: strictly `2` items (`[Aperture Drive in AF]`, `[Auto Pixel Mapping]`),
      ZERO exposed `[Shutter When Pwr OFF]` (`EOPNOTSUPP=95`), FX6 has zero mechanical shutter.
    - `[Version]` & `[Software Update]`: `BODYDATA.DAT` strictly read from `Slot 1` root (`Slot 2`
      ignored -> `ENOENT`/`EOPNOTSUPP`; FX6 strictly `Slot B` root + mandatory `AC Adaptor`),
      `NP-FZ100 >= 51%`, mandatory `Ver. 2.04/2.05` stepping-stone before `Ver. 7.02` from
      `<= Ver. 2.02`, TC/UB reset on update, and `NO-GO` fail-closed firewall (`EROFS=30`)."""
    is_fx3 = camera_model == P352_FX3_MODEL_NAME

    # 1. `[Silent Mode Settings]` + 2-Item `[Target Function Settings]` + Dormant `[Shutter When Pwr OFF]`
    silent_on = silent_mode == "On"
    if silent_on and is_fx3:
        effective_shutter_type = "Electronic Shutter"
        effective_audio_signals = "Off"
        effective_af_illuminator = af_illuminator_setting  # NOT auto-disabled!
        locked_features_disabled = list(P352_SILENT_MODE_LOCKED_FEATURES)
        silent_feature_errno: Optional[int] = (
            P352_EOPNOTSUPP_ERRNO
            if any(
                (
                    flash_requested,
                    long_exposure_nr_requested,
                    efcs_requested,
                    bulb_requested,
                    anti_flicker_requested,
                )
            )
            else None
        )
    else:
        effective_shutter_type = shutter_type_setting if is_fx3 else "Electronic Shutter"
        effective_audio_signals = audio_signals_setting
        effective_af_illuminator = af_illuminator_setting
        locked_features_disabled = []
        silent_feature_errno = None

    # Strictly 2 items in `[Target Function Settings]`; any extra item -> EOPNOTSUPP=95
    extra_target_item_errno: Optional[int] = (
        P352_EOPNOTSUPP_ERRNO if len(requested_silent_target_extra_items) > 0 else None
    )
    shutter_when_pwr_off_errno: Optional[int] = (
        P352_EOPNOTSUPP_ERRNO if shutter_when_pwr_off_exposed_requested else None
    )
    # Bench safety requires Auto Pixel Mapping = Off to prevent shutdown shutter actuation & cnflasha write
    bench_auto_pixel_mapping_safe = target_auto_pixel_mapping == "Off"

    # 2. `[Version]` & `BODYDATA.DAT` Preconditions + Hard `NO-GO` Flash Firewall
    lens_version_visible = lens_mounted_supports_fw_update
    update_red_dot_suppressed = airplane_mode == "On"

    def _ver_tuple(v: str) -> Tuple[int, ...]:
        return tuple(int(p) for p in v.strip().split(".") if p.isdigit())

    cur_v = _ver_tuple(current_body_fw_version)
    tgt_v = _ver_tuple(target_body_fw_version)
    if is_fx3:
        slot_valid = bodydata_target_slot == P352_FX3_UPDATE_SLOT
        power_valid = battery_percent >= P352_FX3_MIN_BATTERY_PCT
        stepping_stone_needed = cur_v <= _ver_tuple("2.02") and tgt_v > _ver_tuple("2.05")
    else:
        slot_valid = bodydata_target_slot == P352_FX6_UPDATE_SLOT
        power_valid = ac_adaptor_connected
        stepping_stone_needed = False

    filename_valid = bodydata_filename == P352_BODYDATA_FILENAME

    # Any attempt to stage/flash BODYDATA.DAT or cross-model flash is unconditionally NO-GO!
    flash_blocked_reasons: List[str] = []
    if cross_model_flash_requested:
        flash_blocked_reasons.append("CROSS_MODEL_FLASH_NO_GO")
    if stepping_stone_needed:
        flash_blocked_reasons.append("MISSING_VER_204_205_STEPPING_STONE_5LONG_6SHORT")
    if not slot_valid:
        flash_blocked_reasons.append("INVALID_BODYDATA_CARD_SLOT")
    if not filename_valid:
        flash_blocked_reasons.append("INVALID_BODYDATA_FILENAME")
    if not power_valid:
        flash_blocked_reasons.append("INSUFFICIENT_POWER_FOR_UPDATE")
    if bodydata_stage_or_flash_requested:
        flash_blocked_reasons.append("TIER0_BODYDATA_FLASH_FIREWALL_NO_GO")

    if bodydata_stage_or_flash_requested or cross_model_flash_requested:
        bodydata_action_allowed = False
        bodydata_errno: Optional[int] = P352_EROFS_ERRNO
    else:
        bodydata_action_allowed = (
            slot_valid
            and filename_valid
            and power_valid
            and not stepping_stone_needed
        )
        bodydata_errno = (
            None
            if bodydata_action_allowed
            else (P352_ENOENT_ERRNO if not slot_valid else P352_EOPNOTSUPP_ERRNO)
        )

    # 3. Reset Matrix (`Camera Settings Reset` vs `Initialize`)
    if reset_action in ("Camera Settings Reset", "Initialize"):
        post_silent_mode = "Off"
        post_aperture_drive_in_af = P352_APERTURE_DRIVE_DEFAULT
        post_auto_pixel_mapping = P352_AUTO_PIXEL_MAPPING_DEFAULT
    else:
        post_silent_mode = silent_mode
        post_aperture_drive_in_af = target_aperture_drive_in_af
        post_auto_pixel_mapping = target_auto_pixel_mapping

    # 4. Slot-1 Tier-0 Vault Firewall (`EROFS=30`)
    mutates_slot1 = (
        requested_vault_action in P352_WRITE_MUTATING_VAULT_ACTIONS
        or bodydata_stage_or_flash_requested
        or cross_model_flash_requested
        or (
            requested_vault_slot == 1
            and requested_vault_action not in ("NONE", "READ_ONLY_AUDIT")
        )
    )
    if (mutates_slot1 and slot1_holds_tier0_vault) or requested_vault_action in (
        "FORMAT_QUICK",
        "FORMAT_FULL",
    ):
        vault_action_allowed = False
        vault_firewall_errno: Optional[str] = "EROFS"
    elif requested_vault_action == "READ_ONLY_AUDIT" and not bodydata_stage_or_flash_requested:
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
        "effective_shutter_type": effective_shutter_type,
        "effective_audio_signals": effective_audio_signals,
        "effective_af_illuminator": effective_af_illuminator,
        "locked_features_disabled": tuple(locked_features_disabled),
        "silent_feature_errno": silent_feature_errno,
        "extra_target_item_errno": extra_target_item_errno,
        "shutter_when_pwr_off_errno": shutter_when_pwr_off_errno,
        "bench_auto_pixel_mapping_safe": bench_auto_pixel_mapping_safe,
        "lens_version_visible": lens_version_visible,
        "update_red_dot_suppressed": update_red_dot_suppressed,
        "slot_valid": slot_valid,
        "filename_valid": filename_valid,
        "power_valid": power_valid,
        "stepping_stone_needed": stepping_stone_needed,
        "flash_blocked_reasons": tuple(flash_blocked_reasons),
        "bodydata_action_allowed": bodydata_action_allowed,
        "bodydata_errno": bodydata_errno,
        "post_silent_mode": post_silent_mode,
        "post_aperture_drive_in_af": post_aperture_drive_in_af,
        "post_auto_pixel_mapping": post_auto_pixel_mapping,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & work_root=None Clean-Room Guard (21 Donors)
# ---------------------------------------------------------------------------


def _iter_work_roots() -> Tuple[Optional[Path], ...]:
    """Return candidate donor work roots (delegates to `_fx3_files.iter_donor_work_roots`)."""
    return _fx3_files.iter_donor_work_roots()


def _resolve_phase352_donor_path(
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
    max_full_bytes: int = P352_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    try:
        resolved = _resolve_phase352_donor_path(relpath)
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
        hdr = os.pread(fd, min(P352_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _check_bodydata_header(data: bytes, label: str) -> Tuple[bool, str]:
    if len(data) < P352_BOUNDED_HEADER_BYTES:
        return False, f"SHORT_BODYDATA:{label}"
    return True, f"BODYDATA_HDR4K:{label}"


def _synthetic_phase352_donors() -> Tuple["Phase352DonorArtifactDigest", ...]:
    specs = (
        ("fx3_appfw_702_so", P352_DONOR_FX3_APPFW_702_RELPATH, P352_PINNED_FX3_APPFW_702_BYTES, P352_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P352_PINNED_FX3_APPFW_702_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702"),
        ("fx6_appfw_601_so", P352_DONOR_FX6_APPFW_601_RELPATH, P352_PINNED_FX6_APPFW_601_BYTES, P352_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P352_PINNED_FX6_APPFW_601_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601"),
        ("fx3_backup_bin", P352_DONOR_FX3_BACKUP_BIN_RELPATH, P352_PINNED_FX3_BACKUP_BIN_BYTES, P352_PINNED_FX3_BACKUP_BIN_BYTES, "FULL_SHA256", P352_PINNED_FX3_BACKUP_BIN_SHA256, "SYNTHETIC_BK4_ILME_FX3"),
        ("fx3_libsdfileinputupdaterapi_so", P352_DONOR_FX3_LIBSDFILEUPDATER_RELPATH, P352_PINNED_FX3_LIBSDFILEUPDATER_BYTES, P352_PINNED_FX3_LIBSDFILEUPDATER_BYTES, "FULL_SHA256", P352_PINNED_FX3_LIBSDFILEUPDATER_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_SDUPDATER"),
        ("fx3_702_bodydata_dat", P352_DONOR_FX3_702_BODYDATA_RELPATH, P352_PINNED_FX3_702_BODYDATA_BYTES, P352_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P352_PINNED_FX3_702_BODYDATA_HDR4K_SHA256, "SYNTHETIC_BODYDATA_HDR4K_FX3_702"),
        ("fx6_avbb_scn_start_audio_so", P352_DONOR_FX6_AVBB_AUDIO_RELPATH, P352_PINNED_FX6_AVBB_AUDIO_BYTES, P352_PINNED_FX6_AVBB_AUDIO_BYTES, "FULL_SHA256", P352_PINNED_FX6_AVBB_AUDIO_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_AVBB_AUDIO"),
        ("fx6_libinfrahotshoe_so", P352_DONOR_FX6_LIBINFRAHOTSHOE_RELPATH, P352_PINNED_FX6_LIBINFRAHOTSHOE_BYTES, P352_PINNED_FX6_LIBINFRAHOTSHOE_BYTES, "FULL_SHA256", P352_PINNED_FX6_LIBINFRAHOTSHOE_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_HOTSHOE"),
        ("fx3_uxc_en_f", P352_DONOR_FX3_UXC_EN_F_RELPATH, P352_PINNED_FX3_UXC_EN_F_BYTES, P352_PINNED_FX3_UXC_EN_F_BYTES, "FULL_SHA256", P352_PINNED_FX3_UXC_EN_F_SHA256, "SYNTHETIC_UXC7_FX3_EN_F"),
        ("fx3_uxc_sc_f", P352_DONOR_FX3_UXC_SC_F_RELPATH, P352_PINNED_FX3_UXC_SC_F_BYTES, P352_PINNED_FX3_UXC_SC_F_BYTES, "FULL_SHA256", P352_PINNED_FX3_UXC_SC_F_SHA256, "SYNTHETIC_UXC7_FX3_SC_F"),
        ("fx3_uxc_tc_f", P352_DONOR_FX3_UXC_TC_F_RELPATH, P352_PINNED_FX3_UXC_TC_F_BYTES, P352_PINNED_FX3_UXC_TC_F_BYTES, "FULL_SHA256", P352_PINNED_FX3_UXC_TC_F_SHA256, "SYNTHETIC_UXC7_FX3_TC_F"),
        ("fx3_uxc_ja_f", P352_DONOR_FX3_UXC_JA_F_RELPATH, P352_PINNED_FX3_UXC_JA_F_BYTES, P352_PINNED_FX3_UXC_JA_F_BYTES, "FULL_SHA256", P352_PINNED_FX3_UXC_JA_F_SHA256, "SYNTHETIC_UXC7_FX3_JA_F"),
        ("fx3_uxc_en", P352_DONOR_FX3_UXC_EN_RELPATH, P352_PINNED_FX3_UXC_EN_BYTES, P352_PINNED_FX3_UXC_EN_BYTES, "FULL_SHA256", P352_PINNED_FX3_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX3_EN"),
        ("fx3_uxc_sc", P352_DONOR_FX3_UXC_SC_RELPATH, P352_PINNED_FX3_UXC_SC_BYTES, P352_PINNED_FX3_UXC_SC_BYTES, "FULL_SHA256", P352_PINNED_FX3_UXC_SC_SHA256, "SYNTHETIC_UXC7_FX3_SC"),
        ("fx3_uxc_tc", P352_DONOR_FX3_UXC_TC_RELPATH, P352_PINNED_FX3_UXC_TC_BYTES, P352_PINNED_FX3_UXC_TC_BYTES, "FULL_SHA256", P352_PINNED_FX3_UXC_TC_SHA256, "SYNTHETIC_UXC7_FX3_TC"),
        ("fx3_uxc_ja", P352_DONOR_FX3_UXC_JA_RELPATH, P352_PINNED_FX3_UXC_JA_BYTES, P352_PINNED_FX3_UXC_JA_BYTES, "FULL_SHA256", P352_PINNED_FX3_UXC_JA_SHA256, "SYNTHETIC_UXC7_FX3_JA"),
        ("fx3_uxc_en_g", P352_DONOR_FX3_UXC_EN_G_RELPATH, P352_PINNED_FX3_UXC_EN_G_BYTES, P352_PINNED_FX3_UXC_EN_G_BYTES, "FULL_SHA256", P352_PINNED_FX3_UXC_EN_G_SHA256, "SYNTHETIC_UXC7_FX3_EN_G"),
        ("fx3_uxc_sc_g", P352_DONOR_FX3_UXC_SC_G_RELPATH, P352_PINNED_FX3_UXC_SC_G_BYTES, P352_PINNED_FX3_UXC_SC_G_BYTES, "FULL_SHA256", P352_PINNED_FX3_UXC_SC_G_SHA256, "SYNTHETIC_UXC7_FX3_SC_G"),
        ("fx3_uxc_tc_g", P352_DONOR_FX3_UXC_TC_G_RELPATH, P352_PINNED_FX3_UXC_TC_G_BYTES, P352_PINNED_FX3_UXC_TC_G_BYTES, "FULL_SHA256", P352_PINNED_FX3_UXC_TC_G_SHA256, "SYNTHETIC_UXC7_FX3_TC_G"),
        ("fx3_uxc_ja_g", P352_DONOR_FX3_UXC_JA_G_RELPATH, P352_PINNED_FX3_UXC_JA_G_BYTES, P352_PINNED_FX3_UXC_JA_G_BYTES, "FULL_SHA256", P352_PINNED_FX3_UXC_JA_G_SHA256, "SYNTHETIC_UXC7_FX3_JA_G"),
        ("fx6_uxc_en", P352_DONOR_FX6_UXC_EN_RELPATH, P352_PINNED_FX6_UXC_EN_BYTES, P352_PINNED_FX6_UXC_EN_BYTES, "FULL_SHA256", P352_PINNED_FX6_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX6_EN"),
        ("fx6_uxc_en_2", P352_DONOR_FX6_UXC_EN_2_RELPATH, P352_PINNED_FX6_UXC_EN_2_BYTES, P352_PINNED_FX6_UXC_EN_2_BYTES, "FULL_SHA256", P352_PINNED_FX6_UXC_EN_2_SHA256, "SYNTHETIC_UXC7_FX6_EN_2"),
    )
    return tuple(
        Phase352DonorArtifactDigest(
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


def inspect_phase352_donors_readonly(
    force_clean_room: Optional[bool] = None,
) -> "Phase352DonorSnapshot":
    """Inspect Wave-62 FX3 (`16` donors) & FX6 (`5` donors) strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase352_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase352DonorSnapshot(
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
        ("fx3_appfw_702_so", P352_DONOR_FX3_APPFW_702_RELPATH, P352_PINNED_FX3_APPFW_702_BYTES, P352_PINNED_FX3_APPFW_702_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702")),
        ("fx6_appfw_601_so", P352_DONOR_FX6_APPFW_601_RELPATH, P352_PINNED_FX6_APPFW_601_BYTES, P352_PINNED_FX6_APPFW_601_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601")),
        ("fx3_backup_bin", P352_DONOR_FX3_BACKUP_BIN_RELPATH, P352_PINNED_FX3_BACKUP_BIN_BYTES, P352_PINNED_FX3_BACKUP_BIN_SHA256, lambda d: _check_bk4_backup(d, "ILME_FX3")),
        ("fx3_libsdfileinputupdaterapi_so", P352_DONOR_FX3_LIBSDFILEUPDATER_RELPATH, P352_PINNED_FX3_LIBSDFILEUPDATER_BYTES, P352_PINNED_FX3_LIBSDFILEUPDATER_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_SDUPDATER")),
        ("fx3_702_bodydata_dat", P352_DONOR_FX3_702_BODYDATA_RELPATH, P352_PINNED_FX3_702_BODYDATA_BYTES, P352_PINNED_FX3_702_BODYDATA_HDR4K_SHA256, lambda d: _check_bodydata_header(d, "FX3_702_BODYDATA")),
        ("fx6_avbb_scn_start_audio_so", P352_DONOR_FX6_AVBB_AUDIO_RELPATH, P352_PINNED_FX6_AVBB_AUDIO_BYTES, P352_PINNED_FX6_AVBB_AUDIO_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_AVBB_AUDIO")),
        ("fx6_libinfrahotshoe_so", P352_DONOR_FX6_LIBINFRAHOTSHOE_RELPATH, P352_PINNED_FX6_LIBINFRAHOTSHOE_BYTES, P352_PINNED_FX6_LIBINFRAHOTSHOE_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_HOTSHOE")),
        ("fx3_uxc_en_f", P352_DONOR_FX3_UXC_EN_F_RELPATH, P352_PINNED_FX3_UXC_EN_F_BYTES, P352_PINNED_FX3_UXC_EN_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_F")),
        ("fx3_uxc_sc_f", P352_DONOR_FX3_UXC_SC_F_RELPATH, P352_PINNED_FX3_UXC_SC_F_BYTES, P352_PINNED_FX3_UXC_SC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_F")),
        ("fx3_uxc_tc_f", P352_DONOR_FX3_UXC_TC_F_RELPATH, P352_PINNED_FX3_UXC_TC_F_BYTES, P352_PINNED_FX3_UXC_TC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_F")),
        ("fx3_uxc_ja_f", P352_DONOR_FX3_UXC_JA_F_RELPATH, P352_PINNED_FX3_UXC_JA_F_BYTES, P352_PINNED_FX3_UXC_JA_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_F")),
        ("fx3_uxc_en", P352_DONOR_FX3_UXC_EN_RELPATH, P352_PINNED_FX3_UXC_EN_BYTES, P352_PINNED_FX3_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN")),
        ("fx3_uxc_sc", P352_DONOR_FX3_UXC_SC_RELPATH, P352_PINNED_FX3_UXC_SC_BYTES, P352_PINNED_FX3_UXC_SC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC")),
        ("fx3_uxc_tc", P352_DONOR_FX3_UXC_TC_RELPATH, P352_PINNED_FX3_UXC_TC_BYTES, P352_PINNED_FX3_UXC_TC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC")),
        ("fx3_uxc_ja", P352_DONOR_FX3_UXC_JA_RELPATH, P352_PINNED_FX3_UXC_JA_BYTES, P352_PINNED_FX3_UXC_JA_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA")),
        ("fx3_uxc_en_g", P352_DONOR_FX3_UXC_EN_G_RELPATH, P352_PINNED_FX3_UXC_EN_G_BYTES, P352_PINNED_FX3_UXC_EN_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_G")),
        ("fx3_uxc_sc_g", P352_DONOR_FX3_UXC_SC_G_RELPATH, P352_PINNED_FX3_UXC_SC_G_BYTES, P352_PINNED_FX3_UXC_SC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_G")),
        ("fx3_uxc_tc_g", P352_DONOR_FX3_UXC_TC_G_RELPATH, P352_PINNED_FX3_UXC_TC_G_BYTES, P352_PINNED_FX3_UXC_TC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_G")),
        ("fx3_uxc_ja_g", P352_DONOR_FX3_UXC_JA_G_RELPATH, P352_PINNED_FX3_UXC_JA_G_BYTES, P352_PINNED_FX3_UXC_JA_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_G")),
        ("fx6_uxc_en", P352_DONOR_FX6_UXC_EN_RELPATH, P352_PINNED_FX6_UXC_EN_BYTES, P352_PINNED_FX6_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN")),
        ("fx6_uxc_en_2", P352_DONOR_FX6_UXC_EN_2_RELPATH, P352_PINNED_FX6_UXC_EN_2_BYTES, P352_PINNED_FX6_UXC_EN_2_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN_2")),
    )

    def _probe_one(spec: Tuple[str, str, int, str, Any]) -> Optional[Phase352DonorArtifactDigest]:
        aid, relpath, expected_bytes, expected_sha, marker_fn = spec
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            return None
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        return Phase352DonorArtifactDigest(
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
        artifacts = _synthetic_phase352_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase352DonorSnapshot(
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
    return Phase352DonorSnapshot(
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
# Frozen Dataclasses (Specs, Reports, Suites & 64-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase352DonorArtifactDigest:
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
class Phase352DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_2_0s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase352DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ShoeAudio4chSubjectRecogVaultSpec:
    # Audio Recording, `[Shoe Audio Set.]`, Preemption & `[Audio Out Timing]`
    camera_model: str
    fw_version: str
    shooting_domain: str
    audio_recording_enabled: bool
    reported_sq_audio_errno: Optional[int]
    audio_rec_level: int
    shoe_audio_set: str
    wind_noise_reduct: str
    audio_out_timing: str
    audio_out_timing_menu_location: str
    audio_level_display_menu_requested: bool
    reported_audio_level_display_errno: Optional[int]
    monitoring_4ch_mix: str
    hdmi_4ch_audio_out: str
    video_codec: str
    recording_fps: int
    proxy_recording_enabled: bool
    reported_effective_proxy_audio_spec: str
    jack_35mm_mic_inserted: bool
    mi_shoe_device: str
    xlr_h1_handle_audio_on: bool
    xlr_h1_digital_analog_switch: str
    xlr_h1_input_select: str
    reported_effective_audio_source: str
    reported_shoe_audio_set_grayed: bool
    reported_effective_shoe_audio_format: str
    reported_shoe_format_errno: Optional[int]
    reported_wind_noise_effective: str
    fx3_limiter_configurable_requested: bool
    reported_limiter_errno: Optional[int]
    fx6_limiter_mode: str
    fx6_32bit_float_requested: bool
    reported_fx6_32bit_float_errno: Optional[int]
    # `[Face/Eye AF]` -> `[Face/Eye Subject]` & `[Face Memory]`
    face_eye_prior_in_af: str
    face_eye_subject: str
    fx3_bkid_app_airplane_hits: int
    reported_subject_errno: Optional[int]
    reported_animal_eye_af_effective: bool
    reported_animal_movie_errno: Optional[int]
    right_left_eye_select: str
    face_eye_frame_disp: str
    hdmi_info_display: str
    hdmi_face_frame_pixels_emitted: int
    face_memory_count: int
    face_memory_exported_in_camset: bool
    regist_faces_priority: str
    reported_regist_faces_priority_enabled: bool
    fx6_face_eye_detection_mode: str
    fx6_saved_tracking_face_active: bool
    # Reset boundary
    reset_action: str
    post_audio_recording_enabled: bool
    post_audio_rec_level: int
    post_shoe_audio_set: str
    post_wind_noise_reduct: str
    post_audio_out_timing: str
    post_monitoring_4ch_mix: str
    post_face_eye_prior_in_af: str
    post_face_eye_subject: str
    post_right_left_eye_select: str
    post_face_eye_frame_disp: str
    post_regist_faces_priority: str
    post_face_memory_count: int
    # Tier-0 Vault & H0 == H3
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
    shoe_audio_preemption_or_limiter_drift_events: int
    subject_recog_myth_or_face_memory_drift_events: int


@dataclass(frozen=True)
class ShoeAudio4chSubjectRecogVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    shoe_audio_4ch_preemption_and_timing_verified: bool
    subject_recog_human_animal_and_face_memory_verified: bool
    slot1_vault_and_h0_h3_verified: bool
    matrix_states_checked: int
    shoe_audio_preemption_or_limiter_drift_events: int
    subject_recog_myth_or_face_memory_drift_events: int
    hdmi_face_frame_pixels_emitted: int
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
class SilentTargetVersionBodydataVaultSpec:
    # `[Silent Mode Settings]`, 2-Item `[Target Function Settings]` & Dormant `[Shutter When Pwr OFF]`
    camera_model: str
    fw_version: str
    shooting_domain: str
    silent_mode: str
    target_aperture_drive_in_af: str
    target_auto_pixel_mapping: str
    requested_silent_target_extra_items: Tuple[str, ...]
    reported_extra_target_item_errno: Optional[int]
    shutter_when_pwr_off_exposed_requested: bool
    reported_shutter_when_pwr_off_errno: Optional[int]
    dormant_shutter_when_pwr_off_exposed_events: int
    af_illuminator_setting: str
    audio_signals_setting: str
    shutter_type_setting: str
    flash_requested: bool
    long_exposure_nr_requested: bool
    efcs_requested: bool
    bulb_requested: bool
    anti_flicker_requested: bool
    reported_effective_shutter_type: str
    reported_effective_audio_signals: str
    reported_effective_af_illuminator: str
    reported_silent_feature_errno: Optional[int]
    cnflasha_pixel_map_mutation_bytes: int
    # `[Version]` & `BODYDATA.DAT` `Slot 1` Root & `NO-GO` Firewall
    lens_mounted_supports_fw_update: bool
    reported_lens_version_visible: bool
    airplane_mode: str
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    reported_update_red_dot_suppressed: bool
    battery_percent: int
    ac_adaptor_connected: bool
    current_body_fw_version: str
    target_body_fw_version: str
    bodydata_filename: str
    bodydata_target_slot: str
    bodydata_stage_or_flash_requested: bool
    cross_model_flash_requested: bool
    reported_bodydata_action_allowed: bool
    reported_bodydata_errno: Optional[int]
    slot1_bodydata_mutation_bytes: int
    # Reset boundary
    reset_action: str
    post_silent_mode: str
    post_aperture_drive_in_af: str
    post_auto_pixel_mapping: str
    # Tier-0 Vault & Stage-B Overlay & H0 == H3
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
    silent_mode_target_or_barrier_drift_events: int
    bodydata_version_flash_or_slot1_vault_drift_events: int


@dataclass(frozen=True)
class SilentTargetVersionBodydataVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    silent_mode_2item_target_and_zero_barrier_verified: bool
    version_bodydata_slot1_nogo_and_vault_verified: bool
    overlay_and_h0_h3_verified: bool
    matrix_states_checked: int
    silent_mode_target_or_barrier_drift_events: int
    bodydata_version_flash_or_slot1_vault_drift_events: int
    dormant_shutter_when_pwr_off_exposed_events: int
    cnflasha_pixel_map_mutation_bytes: int
    slot1_bodydata_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_vault_mutation_bytes: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    bodydata_placement_or_flash_authorized: bool
    cross_model_flash_authorized: bool
    emmc_writes_authorized: bool
    hardware_live_attachment_authorized: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ShoeAudioSubjectSilentTargetBodydataVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase352DonorSnapshot
    shoe_audio_subject_report: ShoeAudio4chSubjectRecogVaultReport
    silent_target_bodydata_report: SilentTargetVersionBodydataVaultReport
    shoe_audio_preemption_or_limiter_drift_events: int
    subject_recog_myth_or_face_memory_drift_events: int
    silent_mode_target_or_barrier_drift_events: int
    bodydata_version_flash_or_slot1_vault_drift_events: int
    dormant_shutter_when_pwr_off_exposed_events: int
    hdmi_face_frame_pixels_emitted: int
    cnflasha_pixel_map_mutation_bytes: int
    slot1_bodydata_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_vault_mutation_bytes: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
    bodydata_placement_or_flash_authorized: bool
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
class Pillar64ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar64ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar64ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar64BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar64ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar64StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase352DonorSnapshot
    pillar_64a_shoe_audio_4ch_subject_recog_vault: Pillar64ASuiteResult
    pillar_64b_silent_target_version_bodydata_vault: Pillar64BSuiteResult
    shoe_audio_preemption_or_limiter_drift_events: int
    subject_recog_myth_or_face_memory_drift_events: int
    silent_mode_target_or_barrier_drift_events: int
    bodydata_version_flash_or_slot1_vault_drift_events: int
    dormant_shutter_when_pwr_off_exposed_events: int
    hdmi_face_frame_pixels_emitted: int
    cnflasha_pixel_map_mutation_bytes: int
    slot1_bodydata_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_vault_mutation_bytes: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
    bodydata_placement_or_flash_authorized: bool
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
class Master64PillarRecoveryReport:
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
    donor_snapshot: Phase352DonorSnapshot
    pillar64_a_shoe_audio_4ch_subject_recog_vault: Pillar64ASuiteResult
    pillar64_b_silent_target_version_bodydata_vault: Pillar64BSuiteResult
    # Pillar 64 zero-violation counters & empirical metrics
    shoe_audio_preemption_or_limiter_drift_events: int
    subject_recog_myth_or_face_memory_drift_events: int
    silent_mode_target_or_barrier_drift_events: int
    bodydata_version_flash_or_slot1_vault_drift_events: int
    dormant_shutter_when_pwr_off_exposed_events: int
    hdmi_face_frame_pixels_emitted: int
    cnflasha_pixel_map_mutation_bytes: int
    slot1_bodydata_mutation_bytes: int
    slot1_data_sector_writes: int
    slot1_vault_mutation_bytes: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
    fx3_audio_rec_level_default: int
    fx3_audio_rec_level_max: int
    fx3_audio_out_timing_menu_path: str
    fx3_ui_exposes_audio_level_display: bool
    fx3_limiter_configurable: bool
    fx6_32bit_float_active: bool
    fx3_exposed_subject_count: int
    fx3_bkid_app_airplane_hits: int
    fx3_face_memory_max_faces: int
    fx3_silent_target_item_count: int
    fx3_silent_mode_locked_feature_count: int
    fx3_shutter_when_pwr_off_exposed: bool
    fx6_mechanical_shutter_present: bool
    fx3_bodydata_slot: str
    fx6_bodydata_slot: str
    fx3_min_battery_percent_for_update: int
    bodydata_placement_or_flash_authorized: bool
    # Carried forward Pillar 63 metrics
    ftp_protocol_sftp_or_jpeg_size_drift_events: int
    wb_custom_cine_ei_or_shockless_drift_events: int
    movie_af_speed_or_focus_map_spoof_events: int
    marker_15ratio_peaking_hdmi_leak_events: int
    zero_rf_usblan_or_slot1_avf_bypass_events: int
    usblan_packets_transmitted: int
    hdmi_marker_peaking_pixels_emitted: int
    slot1_avf_info_mutation_bytes: int
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
    # Carried forward Pillar 62..41 metrics
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
    master_64pillar_sha256: str
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
# Default Safe Specs & Evaluators (Pillars 64A & 64B)
# ---------------------------------------------------------------------------


def build_default_safe_shoe_audio_subject_recog_vault_spec(
    **overrides: Any,
) -> ShoeAudio4chSubjectRecogVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P352_FX3_MODEL_NAME,
        "fw_version": P352_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "audio_recording_enabled": True,
        "reported_sq_audio_errno": None,
        "audio_rec_level": P352_AUDIO_REC_LEVEL_DEFAULT,
        "shoe_audio_set": "48kHz/24bit 4ch",
        "wind_noise_reduct": "Off",
        "audio_out_timing": P352_AUDIO_OUT_TIMING_DEFAULT,
        "audio_out_timing_menu_location": P352_AUDIO_OUT_TIMING_MENU_PATH,
        "audio_level_display_menu_requested": False,
        "reported_audio_level_display_errno": None,
        "monitoring_4ch_mix": "CH1/CH2",
        "hdmi_4ch_audio_out": "CH1/CH2",
        "video_codec": "XAVC S-I DCI 4K",
        "recording_fps": 24,
        "proxy_recording_enabled": True,
        "reported_effective_proxy_audio_spec": P352_FX3_PROXY_AUDIO_SPEC,
        "jack_35mm_mic_inserted": False,
        "mi_shoe_device": "XLR-H1",
        "xlr_h1_handle_audio_on": True,
        "xlr_h1_digital_analog_switch": "DIGITAL",
        "xlr_h1_input_select": "IN1_IN2",
        "reported_effective_audio_source": "MI_SHOE_XLR-H1_DIGITAL",
        "reported_shoe_audio_set_grayed": False,
        "reported_effective_shoe_audio_format": "48kHz/24bit 4ch",
        "reported_shoe_format_errno": None,
        "reported_wind_noise_effective": "Off",
        "fx3_limiter_configurable_requested": False,
        "reported_limiter_errno": None,
        "fx6_limiter_mode": "-12 dB",
        "fx6_32bit_float_requested": False,
        "reported_fx6_32bit_float_errno": None,
        "face_eye_prior_in_af": "On",
        "face_eye_subject": P352_FX3_SUBJECT_DEFAULT,
        "fx3_bkid_app_airplane_hits": P352_FX3_BKID_APP_AIRPLANE_HITS,
        "reported_subject_errno": None,
        "reported_animal_eye_af_effective": False,
        "reported_animal_movie_errno": None,
        "right_left_eye_select": "Auto",
        "face_eye_frame_disp": P352_FX3_FACE_FRAME_DISP_DEFAULT,
        "hdmi_info_display": "Off",
        "hdmi_face_frame_pixels_emitted": P352_HDMI_FACE_FRAME_LEAK_PIXELS,
        "face_memory_count": 3,
        "face_memory_exported_in_camset": False,
        "regist_faces_priority": "On",
        "reported_regist_faces_priority_enabled": True,
        "fx6_face_eye_detection_mode": "Face/Eye Priority AF",
        "fx6_saved_tracking_face_active": False,
        "reset_action": "None",
        "post_audio_recording_enabled": True,
        "post_audio_rec_level": P352_AUDIO_REC_LEVEL_DEFAULT,
        "post_shoe_audio_set": "48kHz/24bit 4ch",
        "post_wind_noise_reduct": "Off",
        "post_audio_out_timing": P352_AUDIO_OUT_TIMING_DEFAULT,
        "post_monitoring_4ch_mix": "CH1/CH2",
        "post_face_eye_prior_in_af": "On",
        "post_face_eye_subject": P352_FX3_SUBJECT_DEFAULT,
        "post_right_left_eye_select": "Auto",
        "post_face_eye_frame_disp": P352_FX3_FACE_FRAME_DISP_DEFAULT,
        "post_regist_faces_priority": "On",
        "post_face_memory_count": 3,
        "requested_vault_slot": 1,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": P352_SLOT1_DATA_SECTOR_WRITES,
        "slot1_vault_mutation_bytes": P352_SLOT1_VAULT_MUTATION_BYTES,
        "slot1_vault_erofs_eopnotsupp_enforced": P352_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        "slot1_format_hard_locked": P352_SLOT1_FORMAT_HARD_LOCKED,
        "overlay_dir": P352_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P352_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P352_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P352_TIER0_SURFACE_COUNT,
        "shoe_audio_preemption_or_limiter_drift_events": (
            P352_SHOE_AUDIO_PREEMPTION_OR_LIMITER_DRIFT_EVENTS
        ),
        "subject_recog_myth_or_face_memory_drift_events": (
            P352_SUBJECT_RECOG_MYTH_OR_FACE_MEMORY_DRIFT_EVENTS
        ),
    }
    defaults.update(overrides)
    return ShoeAudio4chSubjectRecogVaultSpec(**defaults)


def build_default_safe_silent_target_bodydata_vault_spec(
    **overrides: Any,
) -> SilentTargetVersionBodydataVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P352_FX3_MODEL_NAME,
        "fw_version": P352_FX3_FW_VERSION,
        "shooting_domain": "Still",
        "silent_mode": "Off",
        "target_aperture_drive_in_af": P352_APERTURE_DRIVE_DEFAULT,
        "target_auto_pixel_mapping": P352_AUTO_PIXEL_MAPPING_DEFAULT,
        "requested_silent_target_extra_items": (),
        "reported_extra_target_item_errno": None,
        "shutter_when_pwr_off_exposed_requested": False,
        "reported_shutter_when_pwr_off_errno": None,
        "dormant_shutter_when_pwr_off_exposed_events": (
            P352_DORMANT_SHUTTER_WHEN_PWR_OFF_EXPOSED_EVENTS
        ),
        "af_illuminator_setting": "Auto",
        "audio_signals_setting": "On",
        "shutter_type_setting": "Auto",
        "flash_requested": False,
        "long_exposure_nr_requested": False,
        "efcs_requested": False,
        "bulb_requested": False,
        "anti_flicker_requested": False,
        "reported_effective_shutter_type": "Auto",
        "reported_effective_audio_signals": "On",
        "reported_effective_af_illuminator": "Auto",
        "reported_silent_feature_errno": None,
        "cnflasha_pixel_map_mutation_bytes": P352_CNFLASHA_PIXEL_MAP_MUTATION_BYTES,
        "lens_mounted_supports_fw_update": True,
        "reported_lens_version_visible": True,
        "airplane_mode": "On",
        "rf_packets_transmitted": P352_RF_PACKETS_TRANSMITTED,
        "rf_nvs_mutation_bytes": P352_RF_NVS_MUTATION_BYTES,
        "reported_update_red_dot_suppressed": True,
        "battery_percent": 75,
        "ac_adaptor_connected": False,
        "current_body_fw_version": "2.05",
        "target_body_fw_version": "7.02",
        "bodydata_filename": P352_BODYDATA_FILENAME,
        "bodydata_target_slot": P352_FX3_UPDATE_SLOT,
        "bodydata_stage_or_flash_requested": False,
        "cross_model_flash_requested": False,
        "reported_bodydata_action_allowed": True,
        "reported_bodydata_errno": None,
        "slot1_bodydata_mutation_bytes": P352_SLOT1_BODYDATA_MUTATION_BYTES,
        "reset_action": "None",
        "post_silent_mode": "Off",
        "post_aperture_drive_in_af": P352_APERTURE_DRIVE_DEFAULT,
        "post_auto_pixel_mapping": P352_AUTO_PIXEL_MAPPING_DEFAULT,
        "requested_vault_slot": 1,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": P352_SLOT1_DATA_SECTOR_WRITES,
        "slot1_vault_mutation_bytes": P352_SLOT1_VAULT_MUTATION_BYTES,
        "slot1_vault_erofs_eopnotsupp_enforced": P352_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        "slot1_format_hard_locked": P352_SLOT1_FORMAT_HARD_LOCKED,
        "overlay_dir": P352_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P352_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P352_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P352_TIER0_SURFACE_COUNT,
        "silent_mode_target_or_barrier_drift_events": (
            P352_SILENT_MODE_TARGET_OR_BARRIER_DRIFT_EVENTS
        ),
        "bodydata_version_flash_or_slot1_vault_drift_events": (
            P352_BODYDATA_VERSION_FLASH_OR_SLOT1_VAULT_DRIFT_EVENTS
        ),
    }
    defaults.update(overrides)
    return SilentTargetVersionBodydataVaultSpec(**defaults)


def evaluate_shoe_audio_subject_recog_vault(
    spec: ShoeAudio4chSubjectRecogVaultSpec,
) -> ShoeAudio4chSubjectRecogVaultReport:
    """Evaluate Pillar 64A (`[Shoe Audio Set.]` 4ch 24-bit, Preemption, `[Audio Out Timing]`, `[Face/Eye Subject]` & `[Face Memory]`)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P352_BLOCKED_SAFETY_POLICY_VIOLATION, "Safety policy violation")

    valid_spec = (
        spec.camera_model in (P352_FX3_MODEL_NAME, P352_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P352_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P352_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P352_SHOOTING_DOMAINS
        and spec.shoe_audio_set in P352_SHOE_AUDIO_FORMATS
        and spec.wind_noise_reduct in P352_ON_OFF_MODES
        and spec.audio_out_timing in P352_AUDIO_OUT_TIMINGS
        and spec.monitoring_4ch_mix in P352_4CH_AUDIO_MONITORING_MIXES
        and spec.hdmi_4ch_audio_out in P352_4CH_AUDIO_OUTPUT_CHANNELS
        and spec.mi_shoe_device in P352_MI_SHOE_ATTACHED_DEVICES
        and spec.xlr_h1_digital_analog_switch in P352_XLR_H1_SWITCH_MODES
        and spec.fx6_limiter_mode in P352_FX6_LIMITER_MODES
        and spec.face_eye_prior_in_af in P352_ON_OFF_MODES
        and spec.right_left_eye_select in P352_RIGHT_LEFT_EYE_MODES
        and spec.face_eye_frame_disp in P352_ON_OFF_MODES
        and spec.hdmi_info_display in P352_ON_OFF_MODES
        and spec.regist_faces_priority in P352_ON_OFF_MODES
        and spec.fx6_face_eye_detection_mode in P352_FX6_FACE_EYE_MODES
        and spec.reset_action in P352_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P352_VAULT_ACTIONS
        and spec.vault_firewall_errno in P352_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P352_BLOCKED_INVALID_PILLAR64A_SPEC, "Invalid Pillar 64A spec fields")

    st = compute_expected_shoe_audio_subject_recog_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        audio_recording_enabled=spec.audio_recording_enabled,
        audio_rec_level=spec.audio_rec_level,
        shoe_audio_set=spec.shoe_audio_set,
        wind_noise_reduct=spec.wind_noise_reduct,
        audio_out_timing=spec.audio_out_timing,
        audio_out_timing_menu_location=spec.audio_out_timing_menu_location,
        audio_level_display_menu_requested=spec.audio_level_display_menu_requested,
        monitoring_4ch_mix=spec.monitoring_4ch_mix,
        hdmi_4ch_audio_out=spec.hdmi_4ch_audio_out,
        video_codec=spec.video_codec,
        recording_fps=spec.recording_fps,
        proxy_recording_enabled=spec.proxy_recording_enabled,
        jack_35mm_mic_inserted=spec.jack_35mm_mic_inserted,
        mi_shoe_device=spec.mi_shoe_device,
        xlr_h1_handle_audio_on=spec.xlr_h1_handle_audio_on,
        xlr_h1_digital_analog_switch=spec.xlr_h1_digital_analog_switch,
        xlr_h1_input_select=spec.xlr_h1_input_select,
        fx3_limiter_configurable_requested=spec.fx3_limiter_configurable_requested,
        fx6_limiter_mode=spec.fx6_limiter_mode,
        fx6_32bit_float_requested=spec.fx6_32bit_float_requested,
        face_eye_prior_in_af=spec.face_eye_prior_in_af,
        face_eye_subject=spec.face_eye_subject,
        right_left_eye_select=spec.right_left_eye_select,
        face_eye_frame_disp=spec.face_eye_frame_disp,
        face_memory_count=spec.face_memory_count,
        face_memory_exported_in_camset=spec.face_memory_exported_in_camset,
        regist_faces_priority=spec.regist_faces_priority,
        hdmi_info_display=spec.hdmi_info_display,
        fx6_face_eye_detection_mode=spec.fx6_face_eye_detection_mode,
        fx6_saved_tracking_face_active=spec.fx6_saved_tracking_face_active,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    # 1. Digital MI Shoe 4ch 24-bit, Hardware Preemption, Timing & Removed Audio Level Display
    audio_ok = (
        st["rec_level_valid"]
        and st["audio_out_timing_path_ok"]
        and st["main_codec_supports_24bit_4ch"]
        and spec.reported_sq_audio_errno == st["sq_audio_errno"]
        and st["sq_audio_errno"] is None
        and spec.reported_audio_level_display_errno == st["audio_level_display_errno"]
        and st["audio_level_display_errno"] is None
        and spec.reported_limiter_errno == st["limiter_errno"]
        and st["limiter_errno"] is None
        and spec.reported_fx6_32bit_float_errno == st["fx6_32bit_float_errno"]
        and st["fx6_32bit_float_errno"] is None
        and spec.reported_shoe_format_errno == st["shoe_format_errno"]
        and st["shoe_format_errno"] is None
        and spec.reported_effective_audio_source == st["effective_audio_source"]
        and spec.reported_shoe_audio_set_grayed == st["shoe_audio_set_grayed"]
        and spec.reported_effective_shoe_audio_format == st["effective_shoe_audio_format"]
        and spec.reported_wind_noise_effective == st["wind_noise_effective"]
        and spec.reported_effective_proxy_audio_spec == st["effective_proxy_audio_spec"]
        and spec.post_audio_recording_enabled == st["post_audio_recording_enabled"]
        and spec.post_audio_rec_level == st["post_audio_rec_level"]
        and spec.post_shoe_audio_set == st["post_shoe_audio_set"]
        and spec.post_wind_noise_reduct == st["post_wind_noise_reduct"]
        and spec.post_audio_out_timing == st["post_audio_out_timing"]
        and spec.post_monitoring_4ch_mix == st["post_monitoring_4ch_mix"]
        and spec.shoe_audio_preemption_or_limiter_drift_events == 0
    )
    if not audio_ok:
        _fail(
            P352_BLOCKED_SHOE_AUDIO_PREEMPTION_OR_LIMITER_DRIFT,
            "Shoe Audio 4ch 24-bit, hardware preemption, Audio Out Timing path, or Limiter/32bit-float boundary violated",
        )

    # 2. `[Face/Eye Subject]` (`Human`/`Animal`-Only vs Dormant Bird/Insect/Car/Airplane) & `[Face Memory]`
    subject_ok = (
        spec.fx3_bkid_app_airplane_hits == P352_FX3_BKID_APP_AIRPLANE_HITS
        and st["face_memory_count_valid"]
        and st["face_memory_camset_excluded_ok"]
        and spec.reported_subject_errno == st["subject_errno"]
        and st["subject_errno"] is None
        and spec.reported_animal_eye_af_effective == st["animal_eye_af_effective"]
        and spec.reported_animal_movie_errno == st["animal_movie_errno"]
        and st["animal_movie_errno"] is None
        and spec.reported_regist_faces_priority_enabled == st["regist_faces_priority_enabled"]
        and spec.hdmi_face_frame_pixels_emitted == st["hdmi_face_frame_pixels_emitted"]
        and spec.hdmi_face_frame_pixels_emitted == 0
        and spec.post_face_eye_prior_in_af == st["post_face_eye_prior_in_af"]
        and spec.post_face_eye_subject == st["post_face_eye_subject"]
        and spec.post_right_left_eye_select == st["post_right_left_eye_select"]
        and spec.post_face_eye_frame_disp == st["post_face_eye_frame_disp"]
        and spec.post_regist_faces_priority == st["post_regist_faces_priority"]
        and spec.post_face_memory_count == st["post_face_memory_count"]
        and spec.subject_recog_myth_or_face_memory_drift_events == 0
    )
    if not subject_ok:
        _fail(
            P352_BLOCKED_SUBJECT_RECOG_MYTH_OR_FACE_MEMORY_DRIFT,
            "Face/Eye Subject Human/Animal-only Still-only Eye AF, Face Memory 8-face CAMSET exclusion, or Clean-HDMI 0px violated",
        )

    # 3. Slot-1 Tier-0 Vault Firewall (`EROFS=30`) & Stage-B Overlay & H0 == H3
    slot1_mutated = (
        (
            spec.requested_vault_action in P352_WRITE_MUTATING_VAULT_ACTIONS
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
            P352_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P352_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P352_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P352_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P352_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    vault_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "64A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "effective_audio_source": spec.reported_effective_audio_source,
            "shoe_audio_format": spec.reported_effective_shoe_audio_format,
            "audio_out_timing": spec.post_audio_out_timing,
            "face_eye_subject": spec.post_face_eye_subject,
            "post_face_memory_count": spec.post_face_memory_count,
            "hdmi_pixels": spec.hdmi_face_frame_pixels_emitted,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return ShoeAudio4chSubjectRecogVaultReport(
        schema=PHASE352_SCHEMA,
        version=PHASE352_VERSION,
        passed=passed,
        status=P352_STATUS_VERIFIED_PILLAR_64A if passed else P352_STATUS_REJECTED_PILLAR_64A,
        block_code=block_code,
        shoe_audio_4ch_preemption_and_timing_verified=audio_ok,
        subject_recog_human_animal_and_face_memory_verified=subject_ok,
        slot1_vault_and_h0_h3_verified=vault_and_h0_h3_ok,
        matrix_states_checked=30,
        shoe_audio_preemption_or_limiter_drift_events=(
            spec.shoe_audio_preemption_or_limiter_drift_events
        ),
        subject_recog_myth_or_face_memory_drift_events=(
            spec.subject_recog_myth_or_face_memory_drift_events
        ),
        hdmi_face_frame_pixels_emitted=spec.hdmi_face_frame_pixels_emitted,
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_silent_target_bodydata_vault(
    spec: SilentTargetVersionBodydataVaultSpec,
) -> SilentTargetVersionBodydataVaultReport:
    """Evaluate Pillar 64B (`[Silent Mode Settings]` 2-item Target Matrix, dormant `[Shutter When Pwr OFF]` & `[Version]` `BODYDATA.DAT` `Slot 1` `EROFS=30` + `NO-GO`)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P352_BLOCKED_SAFETY_POLICY_VIOLATION, "Safety policy violation")

    valid_spec = (
        spec.camera_model in (P352_FX3_MODEL_NAME, P352_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P352_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P352_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P352_SHOOTING_DOMAINS
        and spec.silent_mode in P352_ON_OFF_MODES
        and spec.target_aperture_drive_in_af in P352_APERTURE_DRIVE_MODES
        and spec.target_auto_pixel_mapping in P352_AUTO_PIXEL_MAPPING_MODES
        and spec.af_illuminator_setting in ("Auto", "Off")
        and spec.audio_signals_setting in P352_ON_OFF_MODES
        and spec.airplane_mode in P352_ON_OFF_MODES
        and 0 <= spec.battery_percent <= 100
        and spec.reset_action in P352_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P352_VAULT_ACTIONS
        and spec.vault_firewall_errno in P352_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P352_BLOCKED_INVALID_PILLAR64B_SPEC, "Invalid Pillar 64B spec fields")

    st = compute_expected_silent_target_version_bodydata_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        silent_mode=spec.silent_mode,
        target_aperture_drive_in_af=spec.target_aperture_drive_in_af,
        target_auto_pixel_mapping=spec.target_auto_pixel_mapping,
        requested_silent_target_extra_items=spec.requested_silent_target_extra_items,
        shutter_when_pwr_off_exposed_requested=spec.shutter_when_pwr_off_exposed_requested,
        af_illuminator_setting=spec.af_illuminator_setting,
        audio_signals_setting=spec.audio_signals_setting,
        shutter_type_setting=spec.shutter_type_setting,
        flash_requested=spec.flash_requested,
        long_exposure_nr_requested=spec.long_exposure_nr_requested,
        efcs_requested=spec.efcs_requested,
        bulb_requested=spec.bulb_requested,
        anti_flicker_requested=spec.anti_flicker_requested,
        lens_mounted_supports_fw_update=spec.lens_mounted_supports_fw_update,
        airplane_mode=spec.airplane_mode,
        battery_percent=spec.battery_percent,
        ac_adaptor_connected=spec.ac_adaptor_connected,
        current_body_fw_version=spec.current_body_fw_version,
        target_body_fw_version=spec.target_body_fw_version,
        bodydata_filename=spec.bodydata_filename,
        bodydata_target_slot=spec.bodydata_target_slot,
        bodydata_stage_or_flash_requested=spec.bodydata_stage_or_flash_requested,
        cross_model_flash_requested=spec.cross_model_flash_requested,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    # 1. `[Silent Mode Settings]` 5-Feature Lockout + `[AF Illuminator]` Intact + 2-Item `[Target Function Settings]` + Zero `[Shutter When Pwr OFF]`
    silent_ok = (
        spec.dormant_shutter_when_pwr_off_exposed_events == 0
        and not spec.shutter_when_pwr_off_exposed_requested
        and spec.reported_shutter_when_pwr_off_errno == st["shutter_when_pwr_off_errno"]
        and st["shutter_when_pwr_off_errno"] is None
        and spec.reported_extra_target_item_errno == st["extra_target_item_errno"]
        and st["extra_target_item_errno"] is None
        and st["bench_auto_pixel_mapping_safe"]
        and spec.cnflasha_pixel_map_mutation_bytes == 0
        and spec.reported_effective_shutter_type == st["effective_shutter_type"]
        and spec.reported_effective_audio_signals == st["effective_audio_signals"]
        and spec.reported_effective_af_illuminator == st["effective_af_illuminator"]
        and spec.reported_silent_feature_errno == st["silent_feature_errno"]
        and st["silent_feature_errno"] is None
        and spec.post_silent_mode == st["post_silent_mode"]
        and spec.post_aperture_drive_in_af == st["post_aperture_drive_in_af"]
        and spec.post_auto_pixel_mapping == st["post_auto_pixel_mapping"]
        and spec.silent_mode_target_or_barrier_drift_events == 0
    )
    if not silent_ok:
        _fail(
            P352_BLOCKED_SILENT_TARGET_OR_SHUTTER_BARRIER_DRIFT,
            "Silent Mode 5-lockout, 2-item Target Function matrix, dormant Shutter When Pwr OFF, or cnflasha Auto Pixel Mapping guard violated",
        )

    # 2. `[Version]`, `BODYDATA.DAT` `Slot 1` Root & `NO-GO` Flash Firewall + Tier-0 `Slot 1` Vault
    slot1_mutated = (
        (
            spec.requested_vault_action in P352_WRITE_MUTATING_VAULT_ACTIONS
            or spec.bodydata_stage_or_flash_requested
            or spec.cross_model_flash_requested
            or (
                spec.requested_vault_slot == 1
                and spec.requested_vault_action not in ("NONE", "READ_ONLY_AUDIT")
            )
        )
        and spec.reported_vault_action_allowed
    )
    version_bodydata_ok = (
        not spec.bodydata_stage_or_flash_requested
        and not spec.cross_model_flash_requested
        and not BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED
        and not CROSS_MODEL_FLASH_AUTHORIZED
        and not PERSISTENT_EMMC_WRITES_AUTHORIZED
        and not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED
        and st["bodydata_action_allowed"]
        and st["bodydata_errno"] is None
        and spec.reported_bodydata_action_allowed == st["bodydata_action_allowed"]
        and spec.reported_bodydata_errno == st["bodydata_errno"]
        and spec.reported_lens_version_visible == st["lens_version_visible"]
        and spec.reported_update_red_dot_suppressed == st["update_red_dot_suppressed"]
        and spec.airplane_mode == "On"
        and spec.rf_packets_transmitted == 0
        and spec.rf_nvs_mutation_bytes == 0
        and spec.slot1_bodydata_mutation_bytes == 0
        and not slot1_mutated
        and spec.reported_vault_action_allowed == st["vault_action_allowed"]
        and spec.vault_firewall_errno == st["vault_firewall_errno"]
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_format_hard_locked
        and spec.bodydata_version_flash_or_slot1_vault_drift_events == 0
    )
    if not version_bodydata_ok:
        _fail(
            P352_BLOCKED_BODYDATA_VERSION_FLASH_OR_SLOT1_VAULT,
            "BODYDATA.DAT Slot-1 root, Ver. 2.04/2.05 stepping-stone gate, Zero-RF update badge guard, or NO-GO flash EROFS=30 firewall violated",
        )

    # 3. Stage-B Volatile Overlay & H0 == H3
    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P352_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P352_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P352_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P352_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    overlay_and_h0_h3_ok = overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "64B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "silent_mode": spec.post_silent_mode,
            "target_auto_pixel_mapping": spec.post_auto_pixel_mapping,
            "current_body_fw_version": spec.current_body_fw_version,
            "target_body_fw_version": spec.target_body_fw_version,
            "bodydata_target_slot": spec.bodydata_target_slot,
            "slot1_bodydata_mutation_bytes": spec.slot1_bodydata_mutation_bytes,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return SilentTargetVersionBodydataVaultReport(
        schema=PHASE352_SCHEMA,
        version=PHASE352_VERSION,
        passed=passed,
        status=P352_STATUS_VERIFIED_PILLAR_64B if passed else P352_STATUS_REJECTED_PILLAR_64B,
        block_code=block_code,
        silent_mode_2item_target_and_zero_barrier_verified=silent_ok,
        version_bodydata_slot1_nogo_and_vault_verified=version_bodydata_ok,
        overlay_and_h0_h3_verified=overlay_and_h0_h3_ok,
        matrix_states_checked=30,
        silent_mode_target_or_barrier_drift_events=(
            spec.silent_mode_target_or_barrier_drift_events
        ),
        bodydata_version_flash_or_slot1_vault_drift_events=(
            spec.bodydata_version_flash_or_slot1_vault_drift_events
        ),
        dormant_shutter_when_pwr_off_exposed_events=(
            spec.dormant_shutter_when_pwr_off_exposed_events
        ),
        cnflasha_pixel_map_mutation_bytes=spec.cnflasha_pixel_map_mutation_bytes,
        slot1_bodydata_mutation_bytes=spec.slot1_bodydata_mutation_bytes,
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        rf_packets_transmitted=spec.rf_packets_transmitted,
        rf_nvs_mutation_bytes=spec.rf_nvs_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        bodydata_placement_or_flash_authorized=BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_shoe_audio_4ch_subject_recog_silent_target_bodydata_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_64a: Optional[ShoeAudio4chSubjectRecogVaultSpec] = None,
    spec_64b: Optional[SilentTargetVersionBodydataVaultSpec] = None,
) -> ShoeAudioSubjectSilentTargetBodydataVaultReport:
    """Combined single-shot verifier for Pillar 64A + Pillar 64B + 21 bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase352_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_shoe_audio_subject_recog_vault(
        spec_64a or build_default_safe_shoe_audio_subject_recog_vault_spec()
    )
    rep_b = evaluate_silent_target_bodydata_vault(
        spec_64b or build_default_safe_silent_target_bodydata_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 352 Wave-62 donor artifact parity check failed")
    if not donor_snapshot.under_2_0s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return ShoeAudioSubjectSilentTargetBodydataVaultReport(
        schema=PHASE352_SCHEMA,
        version=PHASE352_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P352_STATUS_VERIFIED_PILLAR64_SUITE if all_ok else P352_STATUS_FAIL_PILLAR64_SUITE,
        donor_snapshot=donor_snapshot,
        shoe_audio_subject_report=rep_a,
        silent_target_bodydata_report=rep_b,
        shoe_audio_preemption_or_limiter_drift_events=(
            rep_a.shoe_audio_preemption_or_limiter_drift_events
        ),
        subject_recog_myth_or_face_memory_drift_events=(
            rep_a.subject_recog_myth_or_face_memory_drift_events
        ),
        silent_mode_target_or_barrier_drift_events=(
            rep_b.silent_mode_target_or_barrier_drift_events
        ),
        bodydata_version_flash_or_slot1_vault_drift_events=(
            rep_b.bodydata_version_flash_or_slot1_vault_drift_events
        ),
        dormant_shutter_when_pwr_off_exposed_events=(
            rep_b.dormant_shutter_when_pwr_off_exposed_events
        ),
        hdmi_face_frame_pixels_emitted=rep_a.hdmi_face_frame_pixels_emitted,
        cnflasha_pixel_map_mutation_bytes=rep_b.cnflasha_pixel_map_mutation_bytes,
        slot1_bodydata_mutation_bytes=rep_b.slot1_bodydata_mutation_bytes,
        slot1_data_sector_writes=rep_a.slot1_data_sector_writes + rep_b.slot1_data_sector_writes,
        slot1_vault_mutation_bytes=(
            rep_a.slot1_vault_mutation_bytes + rep_b.slot1_vault_mutation_bytes
        ),
        rf_packets_transmitted=rep_b.rf_packets_transmitted,
        rf_nvs_mutation_bytes=rep_b.rf_nvs_mutation_bytes,
        slot1_format_hard_locked=(rep_a.slot1_format_hard_locked and rep_b.slot1_format_hard_locked),
        slot1_vault_erofs_eopnotsupp_enforced=(
            rep_a.slot1_vault_erofs_eopnotsupp_enforced
            and rep_b.slot1_vault_erofs_eopnotsupp_enforced
        ),
        bodydata_placement_or_flash_authorized=BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
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


def verify_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_64a: Optional[ShoeAudio4chSubjectRecogVaultSpec] = None,
    spec_64b: Optional[SilentTargetVersionBodydataVaultSpec] = None,
) -> ShoeAudioSubjectSilentTargetBodydataVaultReport:
    """Symmetry alias for `verify_shoe_audio_4ch_subject_recog_silent_target_bodydata_and_vault`."""
    return verify_shoe_audio_4ch_subject_recog_silent_target_bodydata_and_vault(
        force_clean_room=force_clean_room,
        spec_64a=spec_64a,
        spec_64b=spec_64b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 64A & 64B)
# ---------------------------------------------------------------------------


def run_pillar64a_shoe_audio_subject_recog_vault_6_scenario_suite() -> Pillar64ASuiteResult:
    """Run 6 Pillar 64A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, ShoeAudio4chSubjectRecogVaultSpec, Optional[str]], ...] = (
        (
            P352_PILLAR_64A_SCENARIO_IDS[0],
            True,
            build_default_safe_shoe_audio_subject_recog_vault_spec(
                audio_recording_enabled=True,
                audio_rec_level=28,
                shoe_audio_set="48kHz/24bit 4ch",
                audio_out_timing="Lip Sync",
                audio_out_timing_menu_location=P352_AUDIO_OUT_TIMING_MENU_PATH,
                video_codec="XAVC S-I DCI 4K",
                recording_fps=24,
                proxy_recording_enabled=True,
                reported_effective_proxy_audio_spec=P352_FX3_PROXY_AUDIO_SPEC,
                mi_shoe_device="XLR-H1",
                xlr_h1_handle_audio_on=True,
                xlr_h1_digital_analog_switch="DIGITAL",
                xlr_h1_input_select="IN1_IN2",
                reported_effective_audio_source="MI_SHOE_XLR-H1_DIGITAL",
                reported_shoe_audio_set_grayed=False,
                reported_effective_shoe_audio_format="48kHz/24bit 4ch",
                face_memory_count=8,
                reset_action="Camera Settings Reset",
                post_audio_recording_enabled=True,
                post_audio_rec_level=P352_AUDIO_REC_LEVEL_DEFAULT,
                post_shoe_audio_set=P352_SHOE_AUDIO_FORMAT_DEFAULT,
                post_wind_noise_reduct="Off",
                post_audio_out_timing=P352_AUDIO_OUT_TIMING_DEFAULT,
                post_monitoring_4ch_mix="CH1/CH2",
                post_face_eye_prior_in_af="On",
                post_face_eye_subject=P352_FX3_SUBJECT_DEFAULT,
                post_right_left_eye_select="Auto",
                post_face_eye_frame_disp=P352_FX3_FACE_FRAME_DISP_DEFAULT,
                post_regist_faces_priority="On",
                post_face_memory_count=8,
            ),
            None,
        ),
        (
            P352_PILLAR_64A_SCENARIO_IDS[1],
            True,
            build_default_safe_shoe_audio_subject_recog_vault_spec(
                shooting_domain="Still",
                audio_recording_enabled=True,
                shoe_audio_set="48kHz/24bit 2ch",
                mi_shoe_device="ECM-B1M",
                reported_effective_audio_source="MI_SHOE_ECM-B1M_DIGITAL",
                reported_shoe_audio_set_grayed=False,
                reported_effective_shoe_audio_format="48kHz/24bit 2ch",
                proxy_recording_enabled=False,
                reported_effective_proxy_audio_spec="DISABLED",
                face_eye_subject="Animal",
                reported_animal_eye_af_effective=True,
                reported_animal_movie_errno=None,
                face_memory_count=8,
                reported_regist_faces_priority_enabled=False,
                reset_action="Delete All",
                post_shoe_audio_set="48kHz/24bit 2ch",
                post_face_eye_subject="Animal",
                post_face_memory_count=0,
            ),
            None,
        ),
        (
            P352_PILLAR_64A_SCENARIO_IDS[2],
            False,
            build_default_safe_shoe_audio_subject_recog_vault_spec(
                shooting_domain="S&Q",
                audio_recording_enabled=True,
                reported_sq_audio_errno=None,
                jack_35mm_mic_inserted=True,
                mi_shoe_device="XLR-H1",
                xlr_h1_digital_analog_switch="ANALOG",
                shoe_audio_set="48kHz/24bit 4ch",
                reported_effective_audio_source="MI_SHOE_XLR-H1_DIGITAL",
                reported_shoe_audio_set_grayed=False,
                reported_effective_shoe_audio_format="48kHz/24bit 4ch",
                reported_shoe_format_errno=None,
                audio_level_display_menu_requested=True,
                reported_audio_level_display_errno=None,
                fx3_limiter_configurable_requested=True,
                reported_limiter_errno=None,
                shoe_audio_preemption_or_limiter_drift_events=1,
            ),
            P352_BLOCKED_SHOE_AUDIO_PREEMPTION_OR_LIMITER_DRIFT,
        ),
        (
            P352_PILLAR_64A_SCENARIO_IDS[3],
            False,
            build_default_safe_shoe_audio_subject_recog_vault_spec(
                shooting_domain="Movie",
                face_eye_subject="Airplane",
                fx3_bkid_app_airplane_hits=1,
                reported_subject_errno=None,
                subject_recog_myth_or_face_memory_drift_events=1,
            ),
            P352_BLOCKED_SUBJECT_RECOG_MYTH_OR_FACE_MEMORY_DRIFT,
        ),
        (
            P352_PILLAR_64A_SCENARIO_IDS[4],
            False,
            build_default_safe_shoe_audio_subject_recog_vault_spec(
                face_memory_count=8,
                face_memory_exported_in_camset=True,
                face_eye_frame_disp="On",
                hdmi_info_display="Off",
                hdmi_face_frame_pixels_emitted=2048,
                subject_recog_myth_or_face_memory_drift_events=1,
            ),
            P352_BLOCKED_SUBJECT_RECOG_MYTH_OR_FACE_MEMORY_DRIFT,
        ),
        (
            P352_PILLAR_64A_SCENARIO_IDS[5],
            False,
            build_default_safe_shoe_audio_subject_recog_vault_spec(
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="FORMAT_QUICK",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/setting/64a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P352_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar64ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_shoe_audio_subject_recog_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar64ScenarioOutcome(
                scenario_id=sid,
                pillar="64A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar64ASuiteResult(
        passed=all_ok,
        status=P352_STATUS_VERIFIED_PILLAR_64A if all_ok else P352_STATUS_REJECTED_PILLAR_64A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar64b_silent_target_bodydata_vault_6_scenario_suite() -> Pillar64BSuiteResult:
    """Run 6 Pillar 64B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, SilentTargetVersionBodydataVaultSpec, Optional[str]], ...] = (
        (
            P352_PILLAR_64B_SCENARIO_IDS[0],
            True,
            build_default_safe_silent_target_bodydata_vault_spec(
                silent_mode="On",
                target_aperture_drive_in_af="Silent Priority",
                target_auto_pixel_mapping="Off",
                af_illuminator_setting="Auto",
                audio_signals_setting="On",
                shutter_type_setting="Auto",
                reported_effective_shutter_type="Electronic Shutter",
                reported_effective_audio_signals="Off",
                reported_effective_af_illuminator="Auto",
                reset_action="Camera Settings Reset",
                post_silent_mode="Off",
                post_aperture_drive_in_af=P352_APERTURE_DRIVE_DEFAULT,
                post_auto_pixel_mapping=P352_AUTO_PIXEL_MAPPING_DEFAULT,
            ),
            None,
        ),
        (
            P352_PILLAR_64B_SCENARIO_IDS[1],
            True,
            build_default_safe_silent_target_bodydata_vault_spec(
                current_body_fw_version="2.04",
                target_body_fw_version="7.02",
                bodydata_filename="BODYDATA.DAT",
                bodydata_target_slot="Slot 1",
                battery_percent=60,
                airplane_mode="On",
                reported_update_red_dot_suppressed=True,
                bodydata_stage_or_flash_requested=False,
                cross_model_flash_requested=False,
                reported_bodydata_action_allowed=True,
                reported_bodydata_errno=None,
            ),
            None,
        ),
        (
            P352_PILLAR_64B_SCENARIO_IDS[2],
            False,
            build_default_safe_silent_target_bodydata_vault_spec(
                silent_mode="On",
                requested_silent_target_extra_items=("Shutter When Pwr OFF",),
                reported_extra_target_item_errno=None,
                shutter_when_pwr_off_exposed_requested=True,
                reported_shutter_when_pwr_off_errno=None,
                dormant_shutter_when_pwr_off_exposed_events=1,
                flash_requested=True,
                reported_silent_feature_errno=None,
                silent_mode_target_or_barrier_drift_events=1,
            ),
            P352_BLOCKED_SILENT_TARGET_OR_SHUTTER_BARRIER_DRIFT,
        ),
        (
            P352_PILLAR_64B_SCENARIO_IDS[3],
            False,
            build_default_safe_silent_target_bodydata_vault_spec(
                current_body_fw_version="2.02",
                target_body_fw_version="7.02",
                bodydata_target_slot="Slot 2",
                battery_percent=30,
                reported_bodydata_action_allowed=True,
                reported_bodydata_errno=None,
                bodydata_version_flash_or_slot1_vault_drift_events=1,
            ),
            P352_BLOCKED_BODYDATA_VERSION_FLASH_OR_SLOT1_VAULT,
        ),
        (
            P352_PILLAR_64B_SCENARIO_IDS[4],
            False,
            build_default_safe_silent_target_bodydata_vault_spec(
                bodydata_stage_or_flash_requested=True,
                cross_model_flash_requested=True,
                requested_vault_action="STAGE_BODYDATA_SLOT1",
                reported_bodydata_action_allowed=True,
                reported_bodydata_errno=None,
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_bodydata_mutation_bytes=4096,
                slot1_data_sector_writes=4096,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                bodydata_version_flash_or_slot1_vault_drift_events=1,
            ),
            P352_BLOCKED_BODYDATA_VERSION_FLASH_OR_SLOT1_VAULT,
        ),
        (
            P352_PILLAR_64B_SCENARIO_IDS[5],
            False,
            build_default_safe_silent_target_bodydata_vault_spec(
                target_auto_pixel_mapping="Not Target",
                cnflasha_pixel_map_mutation_bytes=4096,
                requested_vault_action="CNFLASHA_DEFECT_MAP_WRITE",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
                slot1_vault_mutation_bytes=4096,
                overlay_dir="/setting/64b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P352_BLOCKED_SILENT_TARGET_OR_SHUTTER_BARRIER_DRIFT,
        ),
    )

    outcomes: List[Pillar64ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_silent_target_bodydata_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar64ScenarioOutcome(
                scenario_id=sid,
                pillar="64B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar64BSuiteResult(
        passed=all_ok,
        status=P352_STATUS_VERIFIED_PILLAR_64B if all_ok else P352_STATUS_REJECTED_PILLAR_64B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Standalone Pillar 64 Suite & Concurrent Unified 64/64 Master Aggregator
# ---------------------------------------------------------------------------


def run_pillar64_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar64StandaloneReport:
    """Run full Pillar 64 standalone suite (`6/6` Pillar 64A + `6/6` Pillar 64B + 21 bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase352_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar64a_shoe_audio_subject_recog_vault_6_scenario_suite()
    res_b = run_pillar64b_silent_target_bodydata_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 352 donor verification failed")
    if not donor_snapshot.under_2_0s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE352_SCHEMA,
            "version": PHASE352_VERSION,
            "mode": donor_snapshot.verification_mode,
            "64a": [asdict(s) for s in res_a.scenarios],
            "64b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar64StandaloneReport(
        schema=PHASE352_SCHEMA,
        version=PHASE352_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P352_STATUS_VERIFIED_PILLAR64_SUITE if all_ok else P352_STATUS_FAIL_PILLAR64_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_64a_shoe_audio_4ch_subject_recog_vault=res_a,
        pillar_64b_silent_target_version_bodydata_vault=res_b,
        shoe_audio_preemption_or_limiter_drift_events=(
            P352_SHOE_AUDIO_PREEMPTION_OR_LIMITER_DRIFT_EVENTS if res_a.passed else 1
        ),
        subject_recog_myth_or_face_memory_drift_events=(
            P352_SUBJECT_RECOG_MYTH_OR_FACE_MEMORY_DRIFT_EVENTS if res_a.passed else 1
        ),
        silent_mode_target_or_barrier_drift_events=(
            P352_SILENT_MODE_TARGET_OR_BARRIER_DRIFT_EVENTS if res_b.passed else 1
        ),
        bodydata_version_flash_or_slot1_vault_drift_events=(
            P352_BODYDATA_VERSION_FLASH_OR_SLOT1_VAULT_DRIFT_EVENTS if res_b.passed else 1
        ),
        dormant_shutter_when_pwr_off_exposed_events=(
            P352_DORMANT_SHUTTER_WHEN_PWR_OFF_EXPOSED_EVENTS if res_b.passed else 1
        ),
        hdmi_face_frame_pixels_emitted=(
            P352_HDMI_FACE_FRAME_LEAK_PIXELS if res_a.passed else 2048
        ),
        cnflasha_pixel_map_mutation_bytes=(
            P352_CNFLASHA_PIXEL_MAP_MUTATION_BYTES if res_b.passed else 4096
        ),
        slot1_bodydata_mutation_bytes=(
            P352_SLOT1_BODYDATA_MUTATION_BYTES if res_b.passed else 4096
        ),
        slot1_data_sector_writes=(
            P352_SLOT1_DATA_SECTOR_WRITES if (res_a.passed and res_b.passed) else 1
        ),
        slot1_vault_mutation_bytes=(
            P352_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        rf_packets_transmitted=P352_RF_PACKETS_TRANSMITTED if res_b.passed else 1,
        rf_nvs_mutation_bytes=P352_RF_NVS_MUTATION_BYTES if res_b.passed else 64,
        slot1_format_hard_locked=P352_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_eopnotsupp_enforced=P352_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        bodydata_placement_or_flash_authorized=BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
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


def _apply_master64_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def _master64_local_donors_available() -> bool:
    """Return True only when all 21 Wave-62 local donors exist."""
    required_relpaths: Tuple[str, ...] = (
        P352_DONOR_FX3_APPFW_702_RELPATH,
        P352_DONOR_FX6_APPFW_601_RELPATH,
        P352_DONOR_FX3_BACKUP_BIN_RELPATH,
        P352_DONOR_FX3_LIBSDFILEUPDATER_RELPATH,
        P352_DONOR_FX3_702_BODYDATA_RELPATH,
        P352_DONOR_FX6_AVBB_AUDIO_RELPATH,
        P352_DONOR_FX6_LIBINFRAHOTSHOE_RELPATH,
        P352_DONOR_FX3_UXC_EN_F_RELPATH,
        P352_DONOR_FX3_UXC_SC_F_RELPATH,
        P352_DONOR_FX3_UXC_TC_F_RELPATH,
        P352_DONOR_FX3_UXC_JA_F_RELPATH,
        P352_DONOR_FX3_UXC_EN_RELPATH,
        P352_DONOR_FX3_UXC_SC_RELPATH,
        P352_DONOR_FX3_UXC_TC_RELPATH,
        P352_DONOR_FX3_UXC_JA_RELPATH,
        P352_DONOR_FX3_UXC_EN_G_RELPATH,
        P352_DONOR_FX3_UXC_SC_G_RELPATH,
        P352_DONOR_FX3_UXC_TC_G_RELPATH,
        P352_DONOR_FX3_UXC_JA_G_RELPATH,
        P352_DONOR_FX6_UXC_EN_RELPATH,
        P352_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for relpath in required_relpaths:
        try:
            resolved = _resolve_phase352_donor_path(relpath)
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


def evaluate_realhw_64pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master64PillarRecoveryReport:
    """Evaluate and aggregate all 64 recovery pillars (`1..64`) concurrently -> `64/64` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_64_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    if resolved_clean_room is None and not _master64_local_donors_available():
        resolved_clean_room = True
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_63pillar() -> Master63PillarRecoveryReport:
        return evaluate_realhw_63pillar_recovery_master(**kw)

    def _run_p64() -> Tuple[Pillar64StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar64_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_63 = pool.submit(_run_63pillar)
        fut_64 = pool.submit(_run_p64)
        m63_rep = fut_63.result()
        p64_rep, p64_dt = fut_64.result()

    all_errors: List[str] = list(m63_rep.errors) + list(p64_rep.errors)
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
        if getattr(m63_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-63 violated {attr_name} == {expected_val}")
        if getattr(p64_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 64 violated {attr_name} == {expected_val}")

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
        if getattr(m63_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-63 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("shoe_audio_preemption_or_limiter_drift_events", 0),
        ("subject_recog_myth_or_face_memory_drift_events", 0),
        ("silent_mode_target_or_barrier_drift_events", 0),
        ("bodydata_version_flash_or_slot1_vault_drift_events", 0),
        ("dormant_shutter_when_pwr_off_exposed_events", 0),
        ("hdmi_face_frame_pixels_emitted", 0),
        ("cnflasha_pixel_map_mutation_bytes", 0),
        ("slot1_bodydata_mutation_bytes", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("rf_packets_transmitted", 0),
        ("rf_nvs_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_eopnotsupp_enforced", True),
        ("bodydata_placement_or_flash_authorized", False),
    ):
        if getattr(p64_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 64 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m63_rep.pillars)
    spec64 = MASTER_64_PILLAR_SPECS[63]
    p64_metrics = {
        "pillar_64a_shoe_audio_4ch_subject_recog_vault": (
            f"{p64_rep.pillar_64a_shoe_audio_4ch_subject_recog_vault.scenarios_passed}/"
            f"{p64_rep.pillar_64a_shoe_audio_4ch_subject_recog_vault.scenarios_total}"
        ),
        "pillar_64b_silent_target_version_bodydata_vault": (
            f"{p64_rep.pillar_64b_silent_target_version_bodydata_vault.scenarios_passed}/"
            f"{p64_rep.pillar_64b_silent_target_version_bodydata_vault.scenarios_total}"
        ),
        "shoe_audio_preemption_or_limiter_drift_events": (
            p64_rep.shoe_audio_preemption_or_limiter_drift_events
        ),
        "subject_recog_myth_or_face_memory_drift_events": (
            p64_rep.subject_recog_myth_or_face_memory_drift_events
        ),
        "silent_mode_target_or_barrier_drift_events": (
            p64_rep.silent_mode_target_or_barrier_drift_events
        ),
        "bodydata_version_flash_or_slot1_vault_drift_events": (
            p64_rep.bodydata_version_flash_or_slot1_vault_drift_events
        ),
        "dormant_shutter_when_pwr_off_exposed_events": (
            p64_rep.dormant_shutter_when_pwr_off_exposed_events
        ),
        "hdmi_face_frame_pixels_emitted": p64_rep.hdmi_face_frame_pixels_emitted,
        "cnflasha_pixel_map_mutation_bytes": p64_rep.cnflasha_pixel_map_mutation_bytes,
        "slot1_bodydata_mutation_bytes": p64_rep.slot1_bodydata_mutation_bytes,
        "slot1_data_sector_writes": p64_rep.slot1_data_sector_writes,
        "slot1_vault_mutation_bytes": p64_rep.slot1_vault_mutation_bytes,
        "rf_packets_transmitted": p64_rep.rf_packets_transmitted,
        "rf_nvs_mutation_bytes": p64_rep.rf_nvs_mutation_bytes,
        "slot1_format_hard_locked": p64_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_eopnotsupp_enforced": p64_rep.slot1_vault_erofs_eopnotsupp_enforced,
        "bodydata_placement_or_flash_authorized": p64_rep.bodydata_placement_or_flash_authorized,
        "overall_ready_for_hardware_attach": p64_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p64_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p64_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p64_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec64[0],
            pillar_id=spec64[1],
            phase_label=spec64[2],
            module_name=spec64[3],
            passed=bool(p64_rep.all_passed),
            status=p64_rep.status,
            verification_mode=p64_rep.verification_mode,
            elapsed_seconds=p64_dt,
            key_metrics=p64_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec64[1],
                    "mode": p64_rep.verification_mode,
                    "status": p64_rep.status,
                    "metrics": p64_metrics,
                    "passed": p64_rep.all_passed,
                }
            ),
            errors=tuple(p64_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master64_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p64_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_64_PILLAR_COUNT == 64
        and pillars_passed == 64
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE352_SCHEMA,
            "schema_version": PHASE352_MASTER_SCHEMA,
            "version": PHASE352_VERSION,
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

    return Master64PillarRecoveryReport(
        schema=PHASE352_SCHEMA,
        schema_version=PHASE352_MASTER_SCHEMA,
        version=PHASE352_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=(
            P352_STATUS_VERIFIED_64OF64_AGGREGATOR if all_ok else P352_STATUS_FAIL_64OF64_AGGREGATOR
        ),
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P352_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.50,
        under_6s_budget=elapsed < P352_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P352_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p64_rep.donor_snapshot,
        pillar64_a_shoe_audio_4ch_subject_recog_vault=(
            p64_rep.pillar_64a_shoe_audio_4ch_subject_recog_vault
        ),
        pillar64_b_silent_target_version_bodydata_vault=(
            p64_rep.pillar_64b_silent_target_version_bodydata_vault
        ),
        shoe_audio_preemption_or_limiter_drift_events=(
            p64_rep.shoe_audio_preemption_or_limiter_drift_events
        ),
        subject_recog_myth_or_face_memory_drift_events=(
            p64_rep.subject_recog_myth_or_face_memory_drift_events
        ),
        silent_mode_target_or_barrier_drift_events=(
            p64_rep.silent_mode_target_or_barrier_drift_events
        ),
        bodydata_version_flash_or_slot1_vault_drift_events=(
            p64_rep.bodydata_version_flash_or_slot1_vault_drift_events
        ),
        dormant_shutter_when_pwr_off_exposed_events=(
            p64_rep.dormant_shutter_when_pwr_off_exposed_events
        ),
        hdmi_face_frame_pixels_emitted=p64_rep.hdmi_face_frame_pixels_emitted,
        cnflasha_pixel_map_mutation_bytes=p64_rep.cnflasha_pixel_map_mutation_bytes,
        slot1_bodydata_mutation_bytes=p64_rep.slot1_bodydata_mutation_bytes,
        slot1_data_sector_writes=p64_rep.slot1_data_sector_writes,
        slot1_vault_mutation_bytes=p64_rep.slot1_vault_mutation_bytes,
        rf_packets_transmitted=p64_rep.rf_packets_transmitted,
        rf_nvs_mutation_bytes=p64_rep.rf_nvs_mutation_bytes,
        slot1_format_hard_locked=p64_rep.slot1_format_hard_locked,
        slot1_vault_erofs_eopnotsupp_enforced=p64_rep.slot1_vault_erofs_eopnotsupp_enforced,
        fx3_audio_rec_level_default=P352_AUDIO_REC_LEVEL_DEFAULT,
        fx3_audio_rec_level_max=P352_AUDIO_REC_LEVEL_MAX,
        fx3_audio_out_timing_menu_path=P352_AUDIO_OUT_TIMING_MENU_PATH,
        fx3_ui_exposes_audio_level_display=P352_FX3_UI_EXPOSES_AUDIO_LEVEL_DISPLAY,
        fx3_limiter_configurable=P352_FX3_LIMITER_CONFIGURABLE,
        fx6_32bit_float_active=P352_FX6_32BIT_FLOAT_ACTIVE,
        fx3_exposed_subject_count=len(P352_FX3_EXPOSED_SUBJECTS),
        fx3_bkid_app_airplane_hits=P352_FX3_BKID_APP_AIRPLANE_HITS,
        fx3_face_memory_max_faces=P352_FX3_FACE_MEMORY_MAX_FACES,
        fx3_silent_target_item_count=len(P352_SILENT_TARGET_EXPOSED_ITEMS),
        fx3_silent_mode_locked_feature_count=len(P352_SILENT_MODE_LOCKED_FEATURES),
        fx3_shutter_when_pwr_off_exposed=P352_FX3_SHUTTER_WHEN_PWR_OFF_EXPOSED,
        fx6_mechanical_shutter_present=P352_FX6_HAS_MECHANICAL_SHUTTER,
        fx3_bodydata_slot=P352_FX3_UPDATE_SLOT,
        fx6_bodydata_slot=P352_FX6_UPDATE_SLOT,
        fx3_min_battery_percent_for_update=P352_FX3_MIN_BATTERY_PCT,
        bodydata_placement_or_flash_authorized=BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
        ftp_protocol_sftp_or_jpeg_size_drift_events=(
            m63_rep.ftp_protocol_sftp_or_jpeg_size_drift_events
        ),
        wb_custom_cine_ei_or_shockless_drift_events=(
            m63_rep.wb_custom_cine_ei_or_shockless_drift_events
        ),
        movie_af_speed_or_focus_map_spoof_events=(
            m63_rep.movie_af_speed_or_focus_map_spoof_events
        ),
        marker_15ratio_peaking_hdmi_leak_events=(
            m63_rep.marker_15ratio_peaking_hdmi_leak_events
        ),
        zero_rf_usblan_or_slot1_avf_bypass_events=(
            m63_rep.zero_rf_usblan_or_slot1_avf_bypass_events
        ),
        usblan_packets_transmitted=m63_rep.usblan_packets_transmitted,
        hdmi_marker_peaking_pixels_emitted=m63_rep.hdmi_marker_peaking_pixels_emitted,
        slot1_avf_info_mutation_bytes=m63_rep.slot1_avf_info_mutation_bytes,
        fx3_appfw_sftp_hits=m63_rep.fx3_appfw_sftp_hits,
        fx3_appfw_passive_mode_hits=m63_rep.fx3_appfw_passive_mode_hits,
        fx3_appfw_transfer_jpeg_heif_size_hits=(
            m63_rep.fx3_appfw_transfer_jpeg_heif_size_hits
        ),
        fx3_ftp_server_slot_count=m63_rep.fx3_ftp_server_slot_count,
        fx3_ftp_passive_mode_only=m63_rep.fx3_ftp_passive_mode_only,
        fx3_usblan_bypasses_airplane_mode=m63_rep.fx3_usblan_bypasses_airplane_mode,
        fx3_wb_custom_slots=m63_rep.fx3_wb_custom_slots,
        fx3_shutter_awb_lock_reset_immune=m63_rep.fx3_shutter_awb_lock_reset_immune,
        fx3_af_transition_speed_max=m63_rep.fx3_af_transition_speed_max,
        fx3_af_subj_shift_sens_max=m63_rep.fx3_af_subj_shift_sens_max,
        fx6_af_subj_shift_sens_max=m63_rep.fx6_af_subj_shift_sens_max,
        fx3_in_body_focus_map_bkid_hits=m63_rep.fx3_in_body_focus_map_bkid_hits,
        fx3_focus_map_app_only_since_fw=m63_rep.fx3_focus_map_app_only_since_fw,
        fx3_aspect_marker_active_ratio_count=m63_rep.fx3_aspect_marker_active_ratio_count,
        fx3_peaking_color_count=m63_rep.fx3_peaking_color_count,
        fx3_reset_immune_assist_item_count=m63_rep.fx3_reset_immune_assist_item_count,
        rec_media_prioritize_or_autoswitch_drift_events=(
            m63_rep.rec_media_prioritize_or_autoswitch_drift_events
        ),
        card_speed_vpg200_vpg400_gate_drift_events=(
            m63_rep.card_speed_vpg200_vpg400_gate_drift_events
        ),
        proxy_sq_dci4k_or_120p_lockout_drift_events=(
            m63_rep.proxy_sq_dci4k_or_120p_lockout_drift_events
        ),
        cloud_init_persist_or_power_off_ble_rf_events=(
            m63_rep.cloud_init_persist_or_power_off_ble_rf_events
        ),
        mymenu_42slot_or_fx6_lock_spoof_events=m63_rep.mymenu_42slot_or_fx6_lock_spoof_events,
        zero_rf_or_slot1_vault_bypass_events=m63_rep.zero_rf_or_slot1_vault_bypass_events,
        slot1_dcim_m4root_avf_mutation_bytes=m63_rep.slot1_dcim_m4root_avf_mutation_bytes,
        fx3_appfw_prioritize_hits=m63_rep.fx3_appfw_prioritize_hits,
        fx3_appfw_prm_haita_proxy_hits=m63_rep.fx3_appfw_prm_haita_proxy_hits,
        fx3_has_movie_sort_recording=m63_rep.fx3_has_movie_sort_recording,
        fx3_proxy_dci4k_allowed=m63_rep.fx3_proxy_dci4k_allowed,
        fx3_cloud_star_survives_initialize=m63_rep.fx3_cloud_star_survives_initialize,
        fx3_power_off_ble_forced_off=m63_rep.fx3_power_off_ble_forced_off,
        fx3_mymenu_slot_capacity=m63_rep.fx3_mymenu_slot_capacity,
        fx6_user_menu_max_items=m63_rep.fx6_user_menu_max_items,
        fx6_has_bluetooth_hardware=m63_rep.fx6_has_bluetooth_hardware,
        big6_home_or_lower_left_nd_drift_events=m63_rep.big6_home_or_lower_left_nd_drift_events,
        framing_manual_or_dormant_auto_framing_drift_events=(
            m63_rep.framing_manual_or_dormant_auto_framing_drift_events
        ),
        interval_shoot_9999_or_fx6_mxf_spoof_events=(
            m63_rep.interval_shoot_9999_or_fx6_mxf_spoof_events
        ),
        tc_make_regen_or_hdmi_rec_ctrl_drift_events=(
            m63_rep.tc_make_regen_or_hdmi_rec_ctrl_drift_events
        ),
        access_authen_ssh_tls_or_fan_max_drift_events=(
            m63_rep.access_authen_ssh_tls_or_fan_max_drift_events
        ),
        slot1_dcim_avf_mutation_bytes=m63_rep.slot1_dcim_avf_mutation_bytes,
        fx3_big6_tile_count=m63_rep.fx3_big6_tile_count,
        fx3_has_physical_end_hw=m63_rep.fx3_has_physical_end_hw,
        fx3_has_dormant_auto_framing=m63_rep.fx3_has_dormant_auto_framing,
        fx3_interval_subitem_count=m63_rep.fx3_interval_subitem_count,
        fx3_interval_max_shots=m63_rep.fx3_interval_max_shots,
        fx3_access_authen_http_digest_hits=m63_rep.fx3_access_authen_http_digest_hits,
        fx3_fan_control_mode_count=m63_rep.fx3_fan_control_mode_count,
        fx6_fan_control_mode_count=m63_rep.fx6_fan_control_mode_count,
        fx3_has_fan_control_max=m63_rep.fx3_has_fan_control_max,
        fx6_has_fan_control_max=m63_rep.fx6_has_fan_control_max,
        fx3_has_builtin_evf=m63_rep.fx3_has_builtin_evf,
        fx3_has_var_shutter=m63_rep.fx3_has_var_shutter,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        master_64pillar_sha256=master_sha,
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


def evaluate_64pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master64PillarRecoveryReport:
    """Short alias for `evaluate_realhw_64pillar_recovery_master`."""
    return evaluate_realhw_64pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_64pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master64PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_64pillar_recovery_master`."""
    return evaluate_realhw_64pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_64pillar_recovery(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master64PillarRecoveryReport:
    """Milestone 324 dynamic discovery alias for `evaluate_realhw_64pillar_recovery_master`."""
    return evaluate_realhw_64pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )

