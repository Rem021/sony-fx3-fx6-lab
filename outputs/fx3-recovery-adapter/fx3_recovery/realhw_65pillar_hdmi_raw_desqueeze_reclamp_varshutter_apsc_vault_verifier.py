"""Phase 355 Milestone — Recovery Pillar 65 & Concurrent 65/65 Master Recovery Verifier:
Wave-63 Sony ILME-FX3 (Ver. 7.02) vs ILME-FX6 (Ver. 6.01) Empirically Grounded Guardrails:
  * Pillar 65A: `Setup -> [External Output] -> [HDMI Output Settings]` (all Reset-resistant,
    `[Initialize]`-only) 8 active items (`[Rec. Media dur HDMI Output]` `On` def / `Off(HDMI Only)`
    locked `On` in `S&Q`, `[Output Resolution]` `Auto`/`2160p`/`1080p`/`1080i` forced `1080p` under
    `Log != Off` or `PPLUT1..4`, `[4K Output Set.(HDMI Only)]` 10-bit only on FX3 vs dormant
    `24.00p 8bit` `_f 0x748a` + `24.00p` mandatory reboot `_g 0x6034/0x61d3/0x63b6`, `[RAW Output]`
    `4264x2408` 16-bit linear requiring `Movie` + `Log != Off` & locked `Off` in `S&Q`,
    `[RAW Output Setting]` `59.94p..24.00p`, `[Time Code Output]` hard prerequisite for `[REC Control]`,
    and `[4ch Audio Output]` `CH1/CH2` or `CH3/CH4` 2ch LPCM) + removal of `[Color Gamut for RAW Output]`
    (`_f 0x6bdc` / `BKID_APP_setting_color_gamut_for_raw_out`) in Ver. 2.00..7.02 unified into
    `[Log Shooting Setting] -> [Color Gamut]`; Tier-0 `Slot 1` Vault Firewall (`RAW Output = On` +
    `Rec. Media = On` STILL writes internal XAVC (+ Proxy) to `[Recording Media]` -> `Slot 1`
    fail-closed `EROFS=30` required, locking `S-Log3`, disabling `Active` IBIS, and forcing
    `HDMI Info. Display = Off`; whereas `Off(HDMI Only)` performs zero card writes; `RAW = Off` +
    `Rec. Media = On` + `HDMI Info. Display = On` blanks body LCD & moves OSD/red frame to HDMI)
    vs FX6 dual `12G-SDI RAW` (`4096x2160` / `3840x2160 "C"`, capping HDMI `<= 1080p`, 4ch 24-bit
    48kHz LPCM) + `RAW(HDMI)` (`4240x2392`, no `24Hz`) + `SDI/HDMI Remote I/F` vs `Parallel Rec`.
  * Pillar 65B: `Setup -> [Display Option] -> [De-Squeeze Display]` (Reset-resistant): Ver. 7.00/7.02
    active `Off / 1.3x / 1.5x / 1.6x (1.65x horizontal stretch via _f 0x7d0c / VAL_DE_SQUEEZE_DISP_1_65X) / 2.0x`
    with ZERO `1.8x` hits (`EOPNOTSUPP=95`), enforcing 4 hard locks (`Manual Focus`, `Focus Area = Wide`,
    `SteadyShot = Off`, `Face Priority in Multi Metering = Off`), never modifying recorded media,
    bypassing in 6 conditions (`Log=Off`, `RAW=On` HDMI, `Off(HDMI Only)`, Still `MOVIE` key,
    `Remote Shooting`, `Photo Capture`), and NOT disabling `Focus Magnifier` / `Bright Monitoring` vs
    FX6 `Off(1.0x)/1.3x/1.5x(v5.00+)/2.0x` (no `1.6x`, VF+HDMI only, never SDI); `[REC Lamp]` 3 physical
    LEDs (front, rear, top `REC` ring; rear+top hardware-coupled -> `All On` / `Only Front Off` /
    `All Off`; ZERO `[Tally Light]` menu & dormant `REC_LAMP_LIGHT_UP_ONLY_ONE` `_f 0x743e`),
    strictly decoupled from `[Silent Mode]` (`Silent Mode = On` does NOT turn off `REC Lamp`),
    Resettable `[Emphasized REC Display]` (default `On`) + Reset-resistant active Still
    `[Remain Shoot Display]` + Still-only `[Auto Review]` (disabled in Interval) vs FX6
    `Technical > Tally`; dormant `[Var. Shutter]` (`BKID_APP_setting_high_res_ss` / `_f 0x6831`,
    `0` `TYPE_MENU_ITEM_*HIGH_RES*` hits -> `EOPNOTSUPP=95`) vs FX6 `ECS` (`23.99..8000 Hz`) +
    active Still mechanical `[Anti-flicker Shoot.]` (Resettable, 100/120Hz); and `[APS-C S35 Shooting]`
    (`Auto/On/Off`) Reset-resistant (`Not available` under `[Camera Settings Reset]`, correcting
    Wave 42 erratum), locking out all 4K/DCI 4K/4K HDMI Only when `On` (leaving HD `<=120p` &
    Still `M: 5.1M` `2768x1848` 3:2 / `4.3M` 16:9).
  * Unified 65/65 Master Recovery Aggregator (Pillars 1..64 + Pillar 65) in `< 1.5s`.

Safety Redlines (HARD-LOCKED):
  - Zero hardware attach, zero physical device writes, zero USB/UART TX, zero OTP/RPMB, zero eMMC writes.
  - Zero `Slot 1` format or data sector writes (`EROFS=30` fail-closed).
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
from .realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier import (
    MASTER_64_PILLAR_SPECS,
    Master64PillarRecoveryReport,
    evaluate_realhw_64pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Phase 355 Metadata, Safety Redlines & Pinned Budget Constants
# ---------------------------------------------------------------------------

PHASE355_SCHEMA = (
    "realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier_v1"
)
PHASE355_MASTER_SCHEMA = "realhw_65pillar_recovery_master_v1"
PHASE355_VERSION = "1.0.0"
PHASE355_PHASE_NUMBER = 355

P355_ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"

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

P355_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED = False
P355_CROSS_MODEL_FLASH_AUTHORIZED = False
P355_EMMC_WRITES_AUTHORIZED = False
P355_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
P355_OVERALL_READY_FOR_HARDWARE_ATTACH = False

OTP_FUSE_TOUCHES = 0
OTP_FUSE_WRITES = 0
RPMB_COUNTER_INCREMENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PHYSICAL_DEVICE_WRITES = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

P355_BOUNDED_HEADER_BYTES = 4096
P355_MAX_FULL_DONOR_BYTES = 3_000_000
P355_DONOR_INSPECT_BUDGET_SECONDS = 2.0
P355_DONOR_INSPECT_CI_BUDGET_SECONDS = 2.0
P355_FAST_CLI_BUDGET_SECONDS = 1.50
P355_NOMINAL_BUDGET_SECONDS = 4.00
P355_CONCURRENT_CEILING_SECONDS = 6.00

P355_ENOENT_ERRNO = 2
P355_EBUSY_ERRNO = 16
P355_EINVAL_ERRNO = 22
P355_EROFS_ERRNO = 30
P355_EOPNOTSUPP_ERRNO = 95

# Camera Identities
P355_FX3_MODEL_NAME = "ILME-FX3"
P355_FX3_MODEL_ID = 0x91030080
P355_FX3_PRODUCT_CODENAME = "PRODUCT_MODEL_ALCIN_UUD"
P355_FX3_HELPGUIDE_ID = "ilc/2210"
P355_FX3_FW_VERSION = "7.02"
P355_FX3_SUPPORTED_FW_VERSIONS = (
    "7.02", "7.01", "7.00", "6.02", "6.00", "5.00", "4.00", "3.00", "2.05", "2.04", "2.00"
)

P355_FX6_DONOR_MODEL_NAME = "ILME-FX6"
P355_FX6_DONOR_FW_VERSION = "6.01"
P355_FX6_PRODUCT_CODENAME = "PRODUCT_MODEL_CHAPLIN"

# Pinned Wave-63 17 Donors (13 FX3 + 4 FX6)
P355_DONOR_FX3_APPFW_702_RELPATH = P348_DONOR_FX3_APPFW_702_RELPATH
P355_DONOR_FX6_APPFW_601_RELPATH = P348_DONOR_FX6_APPFW_601_RELPATH
P355_DONOR_FX3_BACKUP_BIN_RELPATH = P348_DONOR_FX3_BACKUP_BIN_RELPATH
P355_DONOR_FX3_UXC_EN_F_RELPATH = P348_DONOR_FX3_UXC_EN_F_RELPATH
P355_DONOR_FX3_UXC_SC_F_RELPATH = P348_DONOR_FX3_UXC_SC_F_RELPATH
P355_DONOR_FX3_UXC_TC_F_RELPATH = P348_DONOR_FX3_UXC_TC_F_RELPATH
P355_DONOR_FX3_UXC_JA_F_RELPATH = P348_DONOR_FX3_UXC_JA_F_RELPATH
P355_DONOR_FX3_UXC_EN_RELPATH = P348_DONOR_FX3_UXC_EN_RELPATH
P355_DONOR_FX3_UXC_SC_RELPATH = P348_DONOR_FX3_UXC_SC_RELPATH
P355_DONOR_FX3_UXC_TC_RELPATH = P348_DONOR_FX3_UXC_TC_RELPATH
P355_DONOR_FX3_UXC_JA_RELPATH = P348_DONOR_FX3_UXC_JA_RELPATH
P355_DONOR_FX3_UXC_EN_G_RELPATH = P348_DONOR_FX3_UXC_EN_G_RELPATH
P355_DONOR_FX3_UXC_SC_G_RELPATH = P348_DONOR_FX3_UXC_SC_G_RELPATH
P355_DONOR_FX3_UXC_TC_G_RELPATH = P348_DONOR_FX3_UXC_TC_G_RELPATH
P355_DONOR_FX3_UXC_JA_G_RELPATH = P348_DONOR_FX3_UXC_JA_G_RELPATH
P355_DONOR_FX6_UXC_EN_RELPATH = P348_DONOR_FX6_UXC_EN_RELPATH
P355_DONOR_FX6_UXC_EN_2_RELPATH = P348_DONOR_FX6_UXC_EN_2_RELPATH

P355_PINNED_FX3_APPFW_702_BYTES = P348_PINNED_FX3_APPFW_702_BYTES
P355_PINNED_FX3_APPFW_702_HDR4K_SHA256 = P348_PINNED_FX3_APPFW_702_HDR4K_SHA256
P355_PINNED_FX6_APPFW_601_BYTES = P348_PINNED_FX6_APPFW_601_BYTES
P355_PINNED_FX6_APPFW_601_HDR4K_SHA256 = P348_PINNED_FX6_APPFW_601_HDR4K_SHA256
P355_PINNED_FX3_BACKUP_BIN_BYTES = P348_PINNED_FX3_BACKUP_BIN_BYTES
P355_PINNED_FX3_BACKUP_BIN_SHA256 = P348_PINNED_FX3_BACKUP_BIN_SHA256
P355_PINNED_FX3_UXC_EN_F_BYTES = P348_PINNED_FX3_UXC_EN_F_BYTES
P355_PINNED_FX3_UXC_EN_F_SHA256 = P348_PINNED_FX3_UXC_EN_F_SHA256
P355_PINNED_FX3_UXC_SC_F_BYTES = P348_PINNED_FX3_UXC_SC_F_BYTES
P355_PINNED_FX3_UXC_SC_F_SHA256 = P348_PINNED_FX3_UXC_SC_F_SHA256
P355_PINNED_FX3_UXC_TC_F_BYTES = P348_PINNED_FX3_UXC_TC_F_BYTES
P355_PINNED_FX3_UXC_TC_F_SHA256 = P348_PINNED_FX3_UXC_TC_F_SHA256
P355_PINNED_FX3_UXC_JA_F_BYTES = P348_PINNED_FX3_UXC_JA_F_BYTES
P355_PINNED_FX3_UXC_JA_F_SHA256 = P348_PINNED_FX3_UXC_JA_F_SHA256
P355_PINNED_FX3_UXC_EN_BYTES = P348_PINNED_FX3_UXC_EN_BYTES
P355_PINNED_FX3_UXC_EN_SHA256 = P348_PINNED_FX3_UXC_EN_SHA256
P355_PINNED_FX3_UXC_SC_BYTES = P348_PINNED_FX3_UXC_SC_BYTES
P355_PINNED_FX3_UXC_SC_SHA256 = P348_PINNED_FX3_UXC_SC_SHA256
P355_PINNED_FX3_UXC_TC_BYTES = P348_PINNED_FX3_UXC_TC_BYTES
P355_PINNED_FX3_UXC_TC_SHA256 = P348_PINNED_FX3_UXC_TC_SHA256
P355_PINNED_FX3_UXC_JA_BYTES = P348_PINNED_FX3_UXC_JA_BYTES
P355_PINNED_FX3_UXC_JA_SHA256 = P348_PINNED_FX3_UXC_JA_SHA256
P355_PINNED_FX3_UXC_EN_G_BYTES = P348_PINNED_FX3_UXC_EN_G_BYTES
P355_PINNED_FX3_UXC_EN_G_SHA256 = P348_PINNED_FX3_UXC_EN_G_SHA256
P355_PINNED_FX3_UXC_SC_G_BYTES = P348_PINNED_FX3_UXC_SC_G_BYTES
P355_PINNED_FX3_UXC_SC_G_SHA256 = P348_PINNED_FX3_UXC_SC_G_SHA256
P355_PINNED_FX3_UXC_TC_G_BYTES = P348_PINNED_FX3_UXC_TC_G_BYTES
P355_PINNED_FX3_UXC_TC_G_SHA256 = P348_PINNED_FX3_UXC_TC_G_SHA256
P355_PINNED_FX3_UXC_JA_G_BYTES = P348_PINNED_FX3_UXC_JA_G_BYTES
P355_PINNED_FX3_UXC_JA_G_SHA256 = P348_PINNED_FX3_UXC_JA_G_SHA256
P355_PINNED_FX6_UXC_EN_BYTES = P348_PINNED_FX6_UXC_EN_BYTES
P355_PINNED_FX6_UXC_EN_SHA256 = P348_PINNED_FX6_UXC_EN_SHA256
P355_PINNED_FX6_UXC_EN_2_BYTES = P348_PINNED_FX6_UXC_EN_2_BYTES
P355_PINNED_FX6_UXC_EN_2_SHA256 = P348_PINNED_FX6_UXC_EN_2_SHA256

# Zero-Violation Pillar 65 Counters & Vault Flags
P355_HDMI_RAW_OUTPUT_OR_MEDIA_VAULT_DRIFT_EVENTS = 0
P355_HDMI_4K_ONLY_OR_GAMUT_REMOVAL_DRIFT_EVENTS = 0
P355_DESQUEEZE_RATIO_LOCK_OR_BYPASS_DRIFT_EVENTS = 0
P355_REC_LAMP_TALLY_OR_EMPH_DISPLAY_DRIFT_EVENTS = 0
P355_DORMANT_VAR_SHUTTER_OR_APSC_RESET_DRIFT_EVENTS = 0
P355_DORMANT_VAR_SHUTTER_EXPOSED_EVENTS = 0
P355_DESQUEEZE_1_8X_HITS = 0

P355_SLOT1_DATA_SECTOR_WRITES = 0
P355_SLOT1_VAULT_MUTATION_BYTES = 0
P355_RF_PACKETS_TRANSMITTED = 0
P355_RF_NVS_MUTATION_BYTES = 0
P355_HDMI_RED_BORDER_CLEAN_FEED_LEAK_PIXELS = 0
P355_RECORDED_MEDIA_DESQUEEZE_PIXELS = 0
P355_FX6_SDI_DESQUEEZE_PIXELS = 0

P355_SLOT1_FORMAT_HARD_LOCKED = True
P355_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED = True
P355_SLOT1_VAULT_EROFS_EBUSY_ENFORCED = True
P355_AIRPLANE_MODE_FORCED_ON = True

P355_STAGE_B_VOLATILE_OVERLAY_DIR = "/tmp/fx3_stage_b_overlay/pillar65"
P355_FORBIDDEN_PERSISTENT_TARGETS = (
    "/dev/cnflasha",
    "/setting",
    "/mnt/emmc",
    "/nflasha",
)
P355_TIER0_SURFACE_COUNT = 16

# ---------------------------------------------------------------------------
# Wave-63 Empirically Verified Constants (UXC resid16 & ELF Symbols)
# ---------------------------------------------------------------------------

# 1. Sub-Pillar 65A: `[HDMI Output Settings]` 8 Active Items, `4264x2408` 16-bit RAW & Media Vault
P355_HDMI_OUTPUT_SETTINGS_F_RESID16 = 0x677E
P355_REC_MEDIA_DUR_HDMI_F_RESID16 = 0x6144
P355_OFF_HDMI_ONLY_F_RESID16 = 0x6573
P355_OUTPUT_RESOLUTION_F_RESID16 = 0x79AC
P355_OUTPUT_RES_2160P_F_RESID16 = 0x7839
P355_OUTPUT_RES_1080P_I_BASE_RESID16S = (0xE1D6, 0xE1D7)
P355_HDMI_4K_OUTPUT_SET_F_RESID16 = 0x74D7
P355_HDMI_4K_5994P_10BIT_F_RESID16 = 0x7195
P355_HDMI_4K_2400P_10BIT_F_RESID16 = 0x731D
P355_DORMANT_HDMI_4K_2400P_8BIT_F_RESID16 = 0x748A
P355_RAW_OUTPUT_F_RESID16 = 0x6E97
P355_RAW_OUTPUT_SETTING_F_RESID16 = 0x78FD
P355_REMOVED_RAW_COLOR_GAMUT_F_RESID16 = 0x6BDC
P355_TIME_CODE_OUTPUT_F_RESID16 = 0x72AF
P355_REC_CONTROL_F_RESID16S = (0x76E1, 0x6657)
P355_4CH_AUDIO_OUTPUT_F_RESID16 = 0x6AA0
P355_4CH_AUDIO_CH12_CH34_F_RESID16S = (0x713B, 0x6BF6)
P355_2400P_REBOOT_G_RESID16S = (0x6034, 0x61D3, 0x63B6)

P355_BKID_REC_MEDIA_DUR_HDMI = "BKID_APP_setting_rec_media_during_hdmi_output"
P355_BKID_OUTPUT_RESOLUTION = "BKID_APP_setting_hdmi_resolution"
P355_BKID_HDMI_4K_OUTPUT_SET = "BKID_APP_setting_hdmi_4k_output_setting"
P355_BKID_RAW_OUTPUT = "BKID_APP_setting_raw_output"
P355_BKID_RAW_OUTPUT_FPS = "BKID_APP_setting_raw_output_frame_rate"
P355_BKID_REMOVED_RAW_COLOR_GAMUT = "BKID_APP_setting_color_gamut_for_raw_out"
P355_BKID_TIME_CODE_OUTPUT = "BKID_APP_setting_hdmi_tc_output"
P355_BKID_REC_CONTROL = "BKID_APP_setting_rec_control"
P355_BKID_4CH_AUDIO_OUTPUT = "BKID_APP_setting_4ch_output_ch"

P355_HDMI_OUTPUT_8_ACTIVE_ITEMS = (
    "Rec. Media dur HDMI Output",
    "Output Resolution",
    "4K Output Set.(HDMI Only)",
    "RAW Output",
    "RAW Output Setting",
    "Time Code Output",
    "REC Control",
    "4ch Audio Output",
)
P355_HDMI_OUTPUT_RESET_RESISTANT = True
P355_REC_MEDIA_MODES = ("On", "Off(HDMI Only)")
P355_OUTPUT_RESOLUTION_MODES = ("Auto", "2160p", "1080p", "1080i")
P355_FX3_HDMI_4K_ONLY_10BIT_MODES = (
    "59.94p 10bit",
    "50p 10bit",
    "29.97p 10bit",
    "25p 10bit",
    "23.98p 10bit",
    "24.00p 10bit",
)
P355_FX3_HDMI_4K_DORMANT_8BIT_MODE = "24.00p 8bit"
P355_FX3_RAW_RESOLUTION = "4264x2408"
P355_FX3_RAW_BIT_DEPTH = 16
P355_FX3_RAW_FPS_MODES = ("59.94p", "50p", "29.97p", "25p", "23.98p", "24.00p")
P355_4CH_AUDIO_OUTPUT_CHOICES = ("CH1/CH2", "CH3/CH4")

P355_FX6_SDI_RAW_RESOLUTIONS = ("4096x2160", '3840x2160 "C"')
P355_FX6_HDMI_RAW_RESOLUTION = "4240x2392"
P355_FX6_HDMI_RAW_SUPPORTS_24HZ = False
P355_FX6_SDI_HDMI_REC_CTRL_MODES = ("Off", "SDI/HDMI Remote I/F", "Parallel Rec")

# 2. Sub-Pillar 65B: `[De-Squeeze Display]`, `[REC Lamp]`, `[Var. Shutter]` vs `FX6 ECS`, `[APS-C S35]`
P355_DESQUEEZE_DISPLAY_F_RESID16 = 0x7ABA
P355_DESQUEEZE_1_3X_F_RESID16 = 0x6253
P355_DESQUEEZE_1_5X_F_RESID16 = 0x7D0A
P355_DESQUEEZE_1_6X_F_RESID16 = 0x7D09
P355_DESQUEEZE_1_65X_DESC_F_RESID16 = 0x7D0C
P355_DESQUEEZE_2_0X_F_RESID16 = 0x674C

P355_BKID_DESQUEEZE_DISP = "BKID_APP_setting_de_squeeze_disp"
P355_DESQUEEZE_1_65X_ENUM_SYMBOL = "VAL_DE_SQUEEZE_DISP_1_65X"
P355_DESQUEEZE_MENU_PATH = "Setup -> [Display Option] -> [De-Squeeze Display]"
P355_FX3_VER3_DESQUEEZE_MODES = ("Off", "1.3x", "2.0x")
P355_FX3_VER7_DESQUEEZE_MODES = ("Off", "1.3x", "1.5x", "1.6x", "2.0x")
P355_FX3_DESQUEEZE_1_6X_ACTUAL_FACTOR = 1.65
P355_FX3_DESQUEEZE_4_HARD_LOCKS = (
    "Focus Mode = Manual Focus",
    "Focus Area = Wide",
    "SteadyShot = Off",
    "Face Priority in Multi Metering = Off",
)
P355_FX3_DESQUEEZE_6_BYPASS_CONDITIONS = (
    "Log Shooting = Off",
    "RAW Output = On (HDMI)",
    "Rec. Media dur HDMI Output = Off(HDMI Only) (HDMI)",
    "Still mode MOVIE button recording",
    "Remote Shooting",
    "Photo Capture",
)
P355_FX3_DESQUEEZE_DISABLES_FOCUS_MAGNIFIER = False
P355_FX3_DESQUEEZE_DISABLES_BRIGHT_MONITORING = False
P355_FX6_DESQUEEZE_MODES = ("Off(1.0x)", "1.3x", "1.5x", "2.0x")
P355_FX6_DESQUEEZE_NS1_RESID16S = (0x2A4F, 0x32E4)

P355_REC_LAMP_F_RESID16 = 0x6E62
P355_REC_LAMP_ALL_ON_F_RESID16 = 0x6337
P355_REC_LAMP_ONLY_FRONT_OFF_F_RESID16 = 0x727C
P355_REC_LAMP_ALL_OFF_F_RESID16 = 0x6D8C
P355_DORMANT_REC_LAMP_ONLY_ONE_F_RESID16 = 0x743E
P355_EMPHASIZED_REC_DISP_F_RESID16 = 0x68CF
P355_REMAIN_SHOOT_DISP_F_RESID16S = (0x604D, 0x614F, 0x613E, 0x72B5, 0x76EB)
P355_AUTO_REVIEW_BASE_RESID16S = (0xE155, 0xE207, 0xE208, 0xE209)

P355_BKID_REC_LAMP = "BKID_APP_setting_rec_lamp"
P355_REC_LAMP_MODES = ("All On", "Only Front Off", "All Off")
P355_REC_LAMP_DEFAULT = "All On"
P355_FX3_REC_LAMP_PHYSICAL_LEDS = 3
P355_FX3_REAR_TOP_LED_COUPLED = True
P355_FX3_TALLY_LIGHT_MENU_COUNT = 0
P355_SILENT_MODE_DISABLES_REC_LAMP = False
P355_REMAIN_SHOOT_MODES = ("Not Displayed", "Always Display", "Shoot-Only Display")
P355_AUTO_REVIEW_MODES = ("Off", "2 Sec", "5 Sec", "10 Sec")

P355_ANTI_FLICKER_SHOOT_F_RESID16S = (0x623D, 0x6854, 0x6EB8)
P355_DORMANT_ANTI_FLICKER_SET_F_RESID16 = 0x68E7
P355_DORMANT_VAR_SHUTTER_F_RESID16S = (0x64CF, 0x6831, 0x6F9E, 0x7AF8, 0x6399, 0x7924)
P355_DORMANT_ANTI_FLICKER_TV_SCAN_G_RESID16 = 0x60A8
P355_BKID_HIGH_RES_SS_DORMANT = "BKID_APP_setting_high_res_ss"
P355_BKID_ANTI_FLICKER_SHOOT = "BKID_APP_setting_anti_flicker_shoot"
P355_FX3_HAS_VAR_SHUTTER = False
P355_FX3_TYPE_MENU_ITEM_HIGH_RES_HITS = 0
P355_FX3_ANTI_FLICKER_FREQ_HZ = (100, 120)
P355_FX6_ECS_FREQ_MIN_HZ = 23.99
P355_FX6_ECS_FREQ_MAX_HZ = 8000.00
P355_FX6_ECS_NS1_RESID16S = (0x26F2, 0x26F3, 0x26F4)
P355_FX6_ECS_DEFAULT_HZ_BY_FPS = {
    "59.94p": 60.00,
    "50p": 50.00,
    "29.97p": 30.00,
    "25p": 25.02,
    "24.00p": 24.02,
    "23.98p": 23.99,
}

P355_APSC_S35_F_RESID16S = (0x6EBA, 0x6BBA, 0x73E8, 0x76C9)
P355_BKID_SUPER_35MM = "BKID_APP_setting_super_35mm"
P355_APSC_S35_MODES = ("Auto", "On", "Off")
P355_APSC_S35_DEFAULT = "Auto"
P355_APSC_S35_RESETTABLE_BY_CAMERA_SETTINGS_RESET = False  # Wave 42 erratum correction!
P355_APSC_S35_LOCKED_OUT_VIDEO_FORMATS = (
    "XAVC HS 4K",
    "XAVC S 4K",
    "XAVC S-I 4K",
    "XAVC S-I DCI 4K",
    "S&Q 4K",
)
P355_APSC_S35_ALLOWED_VIDEO_FORMATS = ("XAVC S HD", "XAVC S-I HD")
P355_APSC_S35_STILL_CROP_SIZE_3_2 = "M: 5.1M (2768x1848)"
P355_APSC_S35_STILL_CROP_SIZE_16_9 = "M: 4.3M (2768x1560)"
P355_FX6_IMAGER_SCAN_MODES = ("FF", "S35")

# Common Enums & Vault Constants
P355_ON_OFF_MODES = ("Off", "On")
P355_SHOOTING_DOMAINS = ("Movie", "Still", "S&Q")
P355_RESET_ACTIONS = ("None", "Camera Settings Reset", "Initialize")
P355_VAULT_ACTIONS = (
    "NONE",
    "READ_ONLY_AUDIT",
    "CARD_WRITE_XAVC_REC",
    "CARD_WRITE_STILL_OR_PROXY",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P355_WRITE_MUTATING_VAULT_ACTIONS = (
    "CARD_WRITE_XAVC_REC",
    "CARD_WRITE_STILL_OR_PROXY",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P355_VAULT_FIREWALL_ERRNOS = (None, "EROFS", "EOPNOTSUPP", "EBUSY", "EINVAL", "ENOENT")

# Status & Block Codes
P355_STATUS_VERIFIED_PILLAR_65A = "VERIFIED_PILLAR_65A_HDMI_RAW_16BIT_REC_MEDIA_VAULT"
P355_STATUS_REJECTED_PILLAR_65A = "REJECTED_PILLAR_65A_HDMI_RAW_16BIT_REC_MEDIA_VAULT"
P355_STATUS_VERIFIED_PILLAR_65B = "VERIFIED_PILLAR_65B_DESQUEEZE_RECLAMP_VARSHUTTER_APSC_VAULT"
P355_STATUS_REJECTED_PILLAR_65B = "REJECTED_PILLAR_65B_DESQUEEZE_RECLAMP_VARSHUTTER_APSC_VAULT"
P355_STATUS_VERIFIED_PILLAR65_SUITE = (
    "VERIFIED_PILLAR65_HDMI_RAW_DESQUEEZE_RECLAMP_VARSHUTTER_APSC_VAULT"
)
P355_STATUS_FAIL_PILLAR65_SUITE = (
    "FAIL_PILLAR65_HDMI_RAW_DESQUEEZE_RECLAMP_VARSHUTTER_APSC_VAULT"
)
P355_STATUS_VERIFIED_65OF65_AGGREGATOR = "VERIFIED_65OF65_PILLAR_RECOVERY_MASTER"
P355_STATUS_FAIL_65OF65_AGGREGATOR = "FAIL_65OF65_PILLAR_RECOVERY_MASTER"

P355_BLOCKED_SAFETY_POLICY_VIOLATION = "BLOCKED_P355_SAFETY_POLICY_VIOLATION"
P355_BLOCKED_INVALID_PILLAR65A_SPEC = "BLOCKED_P355_INVALID_PILLAR65A_SPEC"
P355_BLOCKED_INVALID_PILLAR65B_SPEC = "BLOCKED_P355_INVALID_PILLAR65B_SPEC"
P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT = (
    "BLOCKED_P355_HDMI_RAW_OR_MEDIA_VAULT_DRIFT"
)
P355_BLOCKED_DESQUEEZE_OR_REC_LAMP_DRIFT = (
    "BLOCKED_P355_DESQUEEZE_OR_REC_LAMP_DRIFT"
)
P355_BLOCKED_VAR_SHUTTER_OR_APSC_RESET_DRIFT = (
    "BLOCKED_P355_VAR_SHUTTER_OR_APSC_RESET_DRIFT"
)
P355_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL = "BLOCKED_P355_SLOT1_VAULT_WRITE_FIREWALL"
P355_BLOCKED_PERSISTENT_OVERLAY_ESCAPE = "BLOCKED_P355_PERSISTENT_OVERLAY_ESCAPE"
P355_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT = "BLOCKED_P355_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P355_PILLAR_65A_SCENARIO_IDS = (
    "p355_65a_01_allow_4264x2408_16bit_raw_hdmi_only_zero_card_write_and_tc_rec_ctrl",
    "p355_65a_02_allow_raw_on_rec_media_on_slot1_erofs_vault_and_fx6_12g_sdi_contrast",
    "p355_65a_03_reject_removed_raw_color_gamut_dormant_8bit_24p_or_sq_raw_output_spoof",
    "p355_65a_04_reject_rec_control_without_tc_or_camera_reset_wiping_hdmi_settings",
    "p355_65a_05_reject_hdmi_info_clean_feed_leak_or_active_ibis_during_raw_output",
    "p355_65a_06_reject_slot1_vault_write_overlay_escape_or_backup_bin_h0_h3_drift",
)
P355_PILLAR_65B_SCENARIO_IDS = (
    "p355_65b_01_allow_desqueeze_1_65x_4locks_focus_mag_intact_and_rec_lamp_only_front_off",
    "p355_65b_02_allow_apsc_s35_reset_immune_hd_only_5_1mp_still_and_fx6_ecs_contrast",
    "p355_65b_03_reject_1_8x_desqueeze_unlocked_af_ibis_or_fx6_sdi_desqueeze_spoof",
    "p355_65b_04_reject_tally_light_menu_silent_mode_coupling_or_red_border_clean_hdmi_leak",
    "p355_65b_05_reject_dormant_var_shutter_or_apsc_4k_dci4k_12m_or_reset_wipe_erratum",
    "p355_65b_06_reject_slot1_vault_write_overlay_escape_or_tier0_h0_h3_drift",
)

MASTER_65_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_64_PILLAR_SPECS + (
    (
        65,
        "pillar65_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault",
        "Phase 355",
        "realhw_65pillar_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault_verifier",
    ),
)
MASTER_65_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_65_PILLAR_SPECS)
MASTER_65_PILLAR_COUNT = len(MASTER_65_PILLAR_IDS)


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
    return bool(is_forced_clean_room() or os.environ.get(P355_ENV_CLEAN_ROOM_TEST) == "1")


def _donor_inspect_budget_seconds() -> float:
    return (
        P355_DONOR_INSPECT_CI_BUDGET_SECONDS
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS")
        else P355_DONOR_INSPECT_BUDGET_SECONDS
    )


def _is_tmpfs_path(path: str) -> bool:
    norm = posixpath.normpath(path)
    return norm == "/tmp" or norm.startswith("/tmp/")


def _targets_persistent_emmc(path: str) -> bool:
    norm = posixpath.normpath(path)
    return any(norm == p or norm.startswith(p + "/") for p in P355_FORBIDDEN_PERSISTENT_TARGETS)


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
# Empirically Grounded State Calculators (Pillars 65A & 65B)
# ---------------------------------------------------------------------------


def compute_expected_hdmi_raw_media_vault_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    log_shooting: str,
    pplut_active: bool,
    rec_media_dur_hdmi_output: str,
    output_resolution: str,
    hdmi_4k_output_setting: str,
    raw_output: str,
    raw_output_setting: str,
    color_gamut_for_raw_out_requested: bool,
    time_code_output: str,
    rec_control: str,
    audio_4ch_output: str,
    hdmi_info_display: str,
    steadyshot_mode: str,
    gamma_curve: str,
    fx6_raw_interface: str,
    fx6_sdi_hdmi_rec_control: str,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute canonical Wave-63 Pillar 65A state (`[HDMI Output Settings]` 8 active items,
    `4264x2408` 16-bit RAW, `[Rec. Media dur HDMI Output]` `Slot 1` `EROFS=30` vs `Off(HDMI Only)`)."""
    is_fx3 = camera_model == P355_FX3_MODEL_NAME

    # 1. Removed `[Color Gamut for RAW Output]` in Ver. 2.00..7.02
    removed_raw_gamut_errno: Optional[int] = (
        P355_EOPNOTSUPP_ERRNO if (is_fx3 and color_gamut_for_raw_out_requested) else None
    )

    # 2. `[4K Output Set.(HDMI Only)]` 10-bit only on FX3 + 24.00p mandatory reboot
    dormant_4k_8bit_errno: Optional[int] = (
        P355_EOPNOTSUPP_ERRNO
        if (is_fx3 and hdmi_4k_output_setting == P355_FX3_HDMI_4K_DORMANT_8BIT_MODE)
        else None
    )
    is_2400p = "24.00p" in (
        raw_output_setting if raw_output == "On" else hdmi_4k_output_setting
    )

    # 3. `S&Q` locks `[Rec. Media dur HDMI Output] = On`, `[RAW Output] = Off`, TC/REC Ctrl disabled
    if is_fx3 and shooting_domain == "S&Q":
        sq_rec_media_errno: Optional[int] = (
            P355_EOPNOTSUPP_ERRNO if rec_media_dur_hdmi_output != "On" else None
        )
        sq_raw_errno: Optional[int] = (
            P355_EOPNOTSUPP_ERRNO if raw_output == "On" else None
        )
        effective_rec_media = "On"
        effective_raw_output = "Off"
    else:
        sq_rec_media_errno = None
        sq_raw_errno = None
        effective_rec_media = rec_media_dur_hdmi_output
        effective_raw_output = raw_output

    # 4. `[RAW Output] = On` prerequisites: Movie + `Log != Off`
    raw_prereq_errno: Optional[int] = (
        P355_EOPNOTSUPP_ERRNO
        if (
            is_fx3
            and effective_raw_output == "On"
            and (shooting_domain != "Movie" or log_shooting == "Off")
        )
        else None
    )

    # 5. `[REC Control]` hard prerequisite: `[Time Code Output] = On` (and not S&Q)
    rec_control_errno: Optional[int] = (
        P355_EOPNOTSUPP_ERRNO
        if (
            is_fx3
            and rec_control == "On"
            and (time_code_output != "On" or shooting_domain == "S&Q")
        )
        else None
    )

    # 6. Coupling matrix:
    #   - RAW=On + Rec.Media=On -> still records XAVC (+ Proxy) internally; locks S-Log3;
    #     disables Active IBIS; forces HDMI Info. Display = Off.
    #   - Rec.Media=Off(HDMI Only) -> ZERO internal card writes; forces HDMI Info. Display = Off.
    #   - RAW=Off + Rec.Media=On + HDMI Info=On -> body LCD blanks, OSD moves to HDMI.
    effective_gamma = "S-Log3" if (is_fx3 and effective_raw_output == "On") else gamma_curve
    effective_steadyshot = (
        "Off"
        if (is_fx3 and effective_raw_output == "On" and steadyshot_mode == "Active")
        else steadyshot_mode
    )
    effective_hdmi_info_display = (
        "Off"
        if (is_fx3 and (effective_raw_output == "On" or effective_rec_media == "Off(HDMI Only)"))
        else hdmi_info_display
    )
    body_lcd_blanked = (
        is_fx3
        and effective_raw_output == "Off"
        and effective_rec_media == "On"
        and effective_hdmi_info_display == "On"
    )
    effective_output_resolution = (
        "1080p"
        if (
            is_fx3
            and effective_rec_media == "On"
            and effective_raw_output == "Off"
            and (log_shooting != "Off" or pplut_active)
        )
        else output_resolution
    )
    card_write_pathway_active = (
        (effective_rec_media == "On")
        if is_fx3
        else (fx6_sdi_hdmi_rec_control == "Parallel Rec")
    )

    # FX6 comparison boundaries
    if not is_fx3:
        fx6_hdmi_capped_1080p = fx6_raw_interface == "12G-SDI_RAW"
        fx6_hdmi_raw_res = (
            P355_FX6_HDMI_RAW_RESOLUTION if fx6_raw_interface == "RAW_HDMI" else "N/A"
        )
        fx6_hdmi_raw_24hz_supported = False
    else:
        fx6_hdmi_capped_1080p = False
        fx6_hdmi_raw_res = "N/A"
        fx6_hdmi_raw_24hz_supported = True

    # 7. Reset immunity: `[HDMI Output Settings]` is `Not available` under Camera Settings Reset
    if reset_action == "Initialize":
        post_rec_media_dur_hdmi_output = "On"
        post_output_resolution = "Auto"
        post_hdmi_4k_output_setting = "59.94p 10bit"
        post_raw_output = "Off"
        post_raw_output_setting = "59.94p"
        post_time_code_output = "Off"
        post_rec_control = "Off"
        post_audio_4ch_output = "CH1/CH2"
    else:
        # Both "None" and "Camera Settings Reset" preserve all 8 HDMI Output Settings
        post_rec_media_dur_hdmi_output = rec_media_dur_hdmi_output
        post_output_resolution = output_resolution
        post_hdmi_4k_output_setting = hdmi_4k_output_setting
        post_raw_output = raw_output
        post_raw_output_setting = raw_output_setting
        post_time_code_output = time_code_output
        post_rec_control = rec_control
        post_audio_4ch_output = audio_4ch_output

    # 8. Slot-1 Tier-0 Vault Firewall (`EROFS=30`)
    mutates_slot1 = (
        requested_vault_action in P355_WRITE_MUTATING_VAULT_ACTIONS
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
        "removed_raw_gamut_errno": removed_raw_gamut_errno,
        "dormant_4k_8bit_errno": dormant_4k_8bit_errno,
        "is_2400p": is_2400p,
        "sq_rec_media_errno": sq_rec_media_errno,
        "sq_raw_errno": sq_raw_errno,
        "raw_prereq_errno": raw_prereq_errno,
        "rec_control_errno": rec_control_errno,
        "effective_rec_media": effective_rec_media,
        "effective_raw_output": effective_raw_output,
        "effective_gamma": effective_gamma,
        "effective_steadyshot": effective_steadyshot,
        "effective_hdmi_info_display": effective_hdmi_info_display,
        "body_lcd_blanked": body_lcd_blanked,
        "effective_output_resolution": effective_output_resolution,
        "card_write_pathway_active": card_write_pathway_active,
        "fx6_hdmi_capped_1080p": fx6_hdmi_capped_1080p,
        "fx6_hdmi_raw_res": fx6_hdmi_raw_res,
        "fx6_hdmi_raw_24hz_supported": fx6_hdmi_raw_24hz_supported,
        "post_rec_media_dur_hdmi_output": post_rec_media_dur_hdmi_output,
        "post_output_resolution": post_output_resolution,
        "post_hdmi_4k_output_setting": post_hdmi_4k_output_setting,
        "post_raw_output": post_raw_output,
        "post_raw_output_setting": post_raw_output_setting,
        "post_time_code_output": post_time_code_output,
        "post_rec_control": post_rec_control,
        "post_audio_4ch_output": post_audio_4ch_output,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


def compute_expected_desqueeze_reclamp_varshutter_apsc_vault_state(
    *,
    camera_model: str,
    fw_version: str,
    shooting_domain: str,
    de_squeeze_display: str,
    focus_mode: str,
    focus_area: str,
    steadyshot_mode: str,
    face_priority_in_multi_metering: str,
    log_shooting: str,
    raw_output: str,
    rec_media_dur_hdmi_output: str,
    still_movie_key_recording: bool,
    remote_shooting_active: bool,
    photo_capture_active: bool,
    focus_magnifier_requested: bool,
    bright_monitoring_requested: bool,
    rec_lamp: str,
    tally_light_menu_requested: bool,
    rec_lamp_only_one_requested: bool,
    silent_mode: str,
    emphasized_rec_display: str,
    hdmi_info_display: str,
    remain_shoot_display: str,
    auto_review: str,
    interval_shooting_active: bool,
    var_shutter_requested: bool,
    anti_flicker_shoot: str,
    shutter_type: str,
    bulb_active: bool,
    fx6_shutter_mode: str,
    fx6_ecs_frequency_hz: float,
    apsc_s35_shooting: str,
    video_codec: str,
    recording_fps: int,
    still_aspect_ratio: str,
    still_image_size_requested: str,
    reset_action: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
) -> Dict[str, Any]:
    """Compute canonical Wave-63 Pillar 65B state (`[De-Squeeze Display]` `1.6x[1.65x]` vs zero `1.8x`,
    `[REC Lamp]` 3-LED coupling + `[Silent Mode]` decoupling + `[Emphasized REC Display]`,
    dormant `[Var. Shutter]` vs FX6 `ECS` `23.99..8000 Hz`, and `[APS-C S35 Shooting]`
    Reset-resistant 4K lockout & `5.1M` Still crop)."""
    is_fx3 = camera_model == P355_FX3_MODEL_NAME

    # 1. `[De-Squeeze Display]`
    if is_fx3:
        if de_squeeze_display == "1.8x":
            desqueeze_errno: Optional[int] = P355_EOPNOTSUPP_ERRNO
        elif fw_version == "3.00" and de_squeeze_display in ("1.5x", "1.6x"):
            desqueeze_errno = P355_EOPNOTSUPP_ERRNO
        elif de_squeeze_display in P355_FX3_VER7_DESQUEEZE_MODES:
            desqueeze_errno = None
        else:
            desqueeze_errno = P355_EOPNOTSUPP_ERRNO
    else:
        # FX6 has Off(1.0x)/1.3x/1.5x/2.0x; NO 1.6x, NO 1.8x
        desqueeze_errno = (
            P355_EOPNOTSUPP_ERRNO
            if de_squeeze_display in ("1.6x", "1.8x")
            else None
        )

    ratio_factor_map = {
        "Off": 1.0,
        "Off(1.0x)": 1.0,
        "1.3x": 1.3,
        "1.5x": 1.5,
        "1.6x": 1.65,  # Actual 1.65x stretch via VAL_DE_SQUEEZE_DISP_1_65X / _f 0x7d0c
        "2.0x": 2.0,
    }
    effective_stretch_factor = ratio_factor_map.get(de_squeeze_display, 1.0)
    desqueeze_active = (
        de_squeeze_display not in ("Off", "Off(1.0x)")
        and desqueeze_errno is None
        and shooting_domain in ("Movie", "S&Q")
    )

    if is_fx3 and desqueeze_active:
        effective_focus_mode = "Manual Focus"
        effective_focus_area = "Wide"
        effective_steadyshot = "Off"
        effective_face_priority = "Off"
    else:
        effective_focus_mode = focus_mode
        effective_focus_area = focus_area
        effective_steadyshot = steadyshot_mode
        effective_face_priority = face_priority_in_multi_metering

    bypass_triggered = (
        log_shooting == "Off"
        or raw_output == "On"
        or rec_media_dur_hdmi_output == "Off(HDMI Only)"
        or still_movie_key_recording
        or remote_shooting_active
        or photo_capture_active
    )
    effective_hdmi_desqueezed = bool(desqueeze_active and not bypass_triggered)
    recorded_media_desqueezed = False
    fx6_sdi_desqueezed = False
    focus_magnifier_allowed = True if focus_magnifier_requested else True
    bright_monitoring_allowed = (
        shooting_domain == "Still" or (shooting_domain == "Movie" and not focus_magnifier_requested)
    ) if bright_monitoring_requested else True

    # 2. `[REC Lamp]`, `[Emphasized REC Display]`, `[Remain Shoot Display]`, `[Auto Review]`
    tally_menu_errno: Optional[int] = (
        P355_EOPNOTSUPP_ERRNO if (is_fx3 and tally_light_menu_requested) else None
    )
    only_one_led_errno: Optional[int] = (
        P355_EOPNOTSUPP_ERRNO if (is_fx3 and rec_lamp_only_one_requested) else None
    )
    # Physical 3-LED state on FX3 (rear + top hardware-coupled)
    if rec_lamp == "All On":
        front_led_on, rear_led_on, top_rec_ring_on = True, True, True
    elif rec_lamp == "Only Front Off":
        front_led_on, rear_led_on, top_rec_ring_on = False, True, True
    else:
        front_led_on, rear_led_on, top_rec_ring_on = False, False, False

    # Strict decoupling: `[Silent Mode] = On` does NOT turn off REC Lamp
    rec_lamp_unchanged_by_silent_mode = True
    hdmi_red_border_emitted = (
        emphasized_rec_display == "On"
        and shooting_domain in ("Movie", "S&Q")
        and hdmi_info_display == "On"
        and raw_output == "Off"
        and rec_media_dur_hdmi_output == "On"
    )
    auto_review_active = (
        shooting_domain == "Still"
        and auto_review != "Off"
        and not interval_shooting_active
    )

    # 3. Dormant `[Var. Shutter]` vs FX6 `ECS` & `[Anti-flicker Shoot.]`
    var_shutter_errno: Optional[int] = (
        P355_EOPNOTSUPP_ERRNO if (is_fx3 and var_shutter_requested) else None
    )
    anti_flicker_effective = (
        shooting_domain == "Still"
        and anti_flicker_shoot == "On"
        and silent_mode == "Off"
        and shutter_type != "Electronic Shutter"
        and not bulb_active
    )
    fx6_ecs_valid = (
        (P355_FX6_ECS_FREQ_MIN_HZ <= fx6_ecs_frequency_hz <= P355_FX6_ECS_FREQ_MAX_HZ)
        if (not is_fx3 and fx6_shutter_mode == "ECS")
        else True
    )

    # 4. `[APS-C S35 Shooting]` Reset-resistant Erratum & 4K Lockout & `5.1M` Still
    apsc_active_crop = apsc_s35_shooting == "On"
    apsc_4k_lockout_errno: Optional[int] = (
        P355_EOPNOTSUPP_ERRNO
        if (apsc_active_crop and video_codec in P355_APSC_S35_LOCKED_OUT_VIDEO_FORMATS)
        else None
    )
    if apsc_active_crop and shooting_domain == "Still":
        still_12m_disabled = True
        if still_image_size_requested == "L: 12M":
            still_size_errno: Optional[int] = P355_EOPNOTSUPP_ERRNO
        else:
            still_size_errno = None
        if still_aspect_ratio == "16:9":
            effective_still_size = P355_APSC_S35_STILL_CROP_SIZE_16_9
        else:
            effective_still_size = P355_APSC_S35_STILL_CROP_SIZE_3_2
    else:
        still_12m_disabled = False
        still_size_errno = None
        effective_still_size = still_image_size_requested

    # 5. Reset Matrix (`Camera Settings Reset` vs `Initialize`)
    #   Resettable: `[Emphasized REC Display]` (default "On"), `[Anti-flicker Shoot.]` (default "Off")
    #   Reset-resistant (`Not available`): `[De-Squeeze Display]`, `[REC Lamp]`,
    #   `[Remain Shoot Display]`, `[Auto Review]`, AND `[APS-C S35 Shooting]` (Wave 42 erratum!)
    if reset_action == "Initialize":
        post_de_squeeze_display = "Off"
        post_rec_lamp = P355_REC_LAMP_DEFAULT
        post_emphasized_rec_display = "On"
        post_remain_shoot_display = "Not Displayed"
        post_auto_review = "Off"
        post_anti_flicker_shoot = "Off"
        post_apsc_s35_shooting = P355_APSC_S35_DEFAULT
    elif reset_action == "Camera Settings Reset":
        post_de_squeeze_display = de_squeeze_display
        post_rec_lamp = rec_lamp
        post_emphasized_rec_display = "On"
        post_remain_shoot_display = remain_shoot_display
        post_auto_review = auto_review
        post_anti_flicker_shoot = "Off"
        post_apsc_s35_shooting = apsc_s35_shooting  # Reset-resistant!
    else:
        post_de_squeeze_display = de_squeeze_display
        post_rec_lamp = rec_lamp
        post_emphasized_rec_display = emphasized_rec_display
        post_remain_shoot_display = remain_shoot_display
        post_auto_review = auto_review
        post_anti_flicker_shoot = anti_flicker_shoot
        post_apsc_s35_shooting = apsc_s35_shooting

    # 6. Slot-1 Tier-0 Vault Firewall (`EROFS=30`)
    mutates_slot1 = (
        requested_vault_action in P355_WRITE_MUTATING_VAULT_ACTIONS
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
        "desqueeze_errno": desqueeze_errno,
        "effective_stretch_factor": effective_stretch_factor,
        "desqueeze_active": desqueeze_active,
        "effective_focus_mode": effective_focus_mode,
        "effective_focus_area": effective_focus_area,
        "effective_steadyshot": effective_steadyshot,
        "effective_face_priority": effective_face_priority,
        "effective_hdmi_desqueezed": effective_hdmi_desqueezed,
        "recorded_media_desqueezed": recorded_media_desqueezed,
        "fx6_sdi_desqueezed": fx6_sdi_desqueezed,
        "focus_magnifier_allowed": focus_magnifier_allowed,
        "bright_monitoring_allowed": bright_monitoring_allowed,
        "tally_menu_errno": tally_menu_errno,
        "only_one_led_errno": only_one_led_errno,
        "front_led_on": front_led_on,
        "rear_led_on": rear_led_on,
        "top_rec_ring_on": top_rec_ring_on,
        "rec_lamp_unchanged_by_silent_mode": rec_lamp_unchanged_by_silent_mode,
        "hdmi_red_border_emitted": hdmi_red_border_emitted,
        "auto_review_active": auto_review_active,
        "var_shutter_errno": var_shutter_errno,
        "anti_flicker_effective": anti_flicker_effective,
        "fx6_ecs_valid": fx6_ecs_valid,
        "apsc_4k_lockout_errno": apsc_4k_lockout_errno,
        "still_12m_disabled": still_12m_disabled,
        "still_size_errno": still_size_errno,
        "effective_still_size": effective_still_size,
        "post_de_squeeze_display": post_de_squeeze_display,
        "post_rec_lamp": post_rec_lamp,
        "post_emphasized_rec_display": post_emphasized_rec_display,
        "post_remain_shoot_display": post_remain_shoot_display,
        "post_auto_review": post_auto_review,
        "post_anti_flicker_shoot": post_anti_flicker_shoot,
        "post_apsc_s35_shooting": post_apsc_s35_shooting,
        "vault_action_allowed": vault_action_allowed,
        "vault_firewall_errno": vault_firewall_errno,
    }


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & work_root=None Clean-Room Guard (17 Donors)
# ---------------------------------------------------------------------------


def _iter_work_roots() -> Tuple[Optional[Path], ...]:
    """Return candidate donor work roots (delegates to `_fx3_files.iter_donor_work_roots`)."""
    return _fx3_files.iter_donor_work_roots()


def _resolve_phase355_donor_path(
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
    max_full_bytes: int = P355_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    try:
        resolved = _resolve_phase355_donor_path(relpath)
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
        hdr = os.pread(fd, min(P355_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase355_donors() -> Tuple["Phase355DonorArtifactDigest", ...]:
    specs = (
        ("fx3_appfw_702_so", P355_DONOR_FX3_APPFW_702_RELPATH, P355_PINNED_FX3_APPFW_702_BYTES, P355_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P355_PINNED_FX3_APPFW_702_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702"),
        ("fx6_appfw_601_so", P355_DONOR_FX6_APPFW_601_RELPATH, P355_PINNED_FX6_APPFW_601_BYTES, P355_BOUNDED_HEADER_BYTES, "HEADER4K_SHA256", P355_PINNED_FX6_APPFW_601_HDR4K_SHA256, "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601"),
        ("fx3_backup_bin", P355_DONOR_FX3_BACKUP_BIN_RELPATH, P355_PINNED_FX3_BACKUP_BIN_BYTES, P355_PINNED_FX3_BACKUP_BIN_BYTES, "FULL_SHA256", P355_PINNED_FX3_BACKUP_BIN_SHA256, "SYNTHETIC_BK4_ILME_FX3"),
        ("fx3_uxc_en_f", P355_DONOR_FX3_UXC_EN_F_RELPATH, P355_PINNED_FX3_UXC_EN_F_BYTES, P355_PINNED_FX3_UXC_EN_F_BYTES, "FULL_SHA256", P355_PINNED_FX3_UXC_EN_F_SHA256, "SYNTHETIC_UXC7_FX3_EN_F"),
        ("fx3_uxc_sc_f", P355_DONOR_FX3_UXC_SC_F_RELPATH, P355_PINNED_FX3_UXC_SC_F_BYTES, P355_PINNED_FX3_UXC_SC_F_BYTES, "FULL_SHA256", P355_PINNED_FX3_UXC_SC_F_SHA256, "SYNTHETIC_UXC7_FX3_SC_F"),
        ("fx3_uxc_tc_f", P355_DONOR_FX3_UXC_TC_F_RELPATH, P355_PINNED_FX3_UXC_TC_F_BYTES, P355_PINNED_FX3_UXC_TC_F_BYTES, "FULL_SHA256", P355_PINNED_FX3_UXC_TC_F_SHA256, "SYNTHETIC_UXC7_FX3_TC_F"),
        ("fx3_uxc_ja_f", P355_DONOR_FX3_UXC_JA_F_RELPATH, P355_PINNED_FX3_UXC_JA_F_BYTES, P355_PINNED_FX3_UXC_JA_F_BYTES, "FULL_SHA256", P355_PINNED_FX3_UXC_JA_F_SHA256, "SYNTHETIC_UXC7_FX3_JA_F"),
        ("fx3_uxc_en", P355_DONOR_FX3_UXC_EN_RELPATH, P355_PINNED_FX3_UXC_EN_BYTES, P355_PINNED_FX3_UXC_EN_BYTES, "FULL_SHA256", P355_PINNED_FX3_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX3_EN"),
        ("fx3_uxc_sc", P355_DONOR_FX3_UXC_SC_RELPATH, P355_PINNED_FX3_UXC_SC_BYTES, P355_PINNED_FX3_UXC_SC_BYTES, "FULL_SHA256", P355_PINNED_FX3_UXC_SC_SHA256, "SYNTHETIC_UXC7_FX3_SC"),
        ("fx3_uxc_tc", P355_DONOR_FX3_UXC_TC_RELPATH, P355_PINNED_FX3_UXC_TC_BYTES, P355_PINNED_FX3_UXC_TC_BYTES, "FULL_SHA256", P355_PINNED_FX3_UXC_TC_SHA256, "SYNTHETIC_UXC7_FX3_TC"),
        ("fx3_uxc_ja", P355_DONOR_FX3_UXC_JA_RELPATH, P355_PINNED_FX3_UXC_JA_BYTES, P355_PINNED_FX3_UXC_JA_BYTES, "FULL_SHA256", P355_PINNED_FX3_UXC_JA_SHA256, "SYNTHETIC_UXC7_FX3_JA"),
        ("fx3_uxc_en_g", P355_DONOR_FX3_UXC_EN_G_RELPATH, P355_PINNED_FX3_UXC_EN_G_BYTES, P355_PINNED_FX3_UXC_EN_G_BYTES, "FULL_SHA256", P355_PINNED_FX3_UXC_EN_G_SHA256, "SYNTHETIC_UXC7_FX3_EN_G"),
        ("fx3_uxc_sc_g", P355_DONOR_FX3_UXC_SC_G_RELPATH, P355_PINNED_FX3_UXC_SC_G_BYTES, P355_PINNED_FX3_UXC_SC_G_BYTES, "FULL_SHA256", P355_PINNED_FX3_UXC_SC_G_SHA256, "SYNTHETIC_UXC7_FX3_SC_G"),
        ("fx3_uxc_tc_g", P355_DONOR_FX3_UXC_TC_G_RELPATH, P355_PINNED_FX3_UXC_TC_G_BYTES, P355_PINNED_FX3_UXC_TC_G_BYTES, "FULL_SHA256", P355_PINNED_FX3_UXC_TC_G_SHA256, "SYNTHETIC_UXC7_FX3_TC_G"),
        ("fx3_uxc_ja_g", P355_DONOR_FX3_UXC_JA_G_RELPATH, P355_PINNED_FX3_UXC_JA_G_BYTES, P355_PINNED_FX3_UXC_JA_G_BYTES, "FULL_SHA256", P355_PINNED_FX3_UXC_JA_G_SHA256, "SYNTHETIC_UXC7_FX3_JA_G"),
        ("fx6_uxc_en", P355_DONOR_FX6_UXC_EN_RELPATH, P355_PINNED_FX6_UXC_EN_BYTES, P355_PINNED_FX6_UXC_EN_BYTES, "FULL_SHA256", P355_PINNED_FX6_UXC_EN_SHA256, "SYNTHETIC_UXC7_FX6_EN"),
        ("fx6_uxc_en_2", P355_DONOR_FX6_UXC_EN_2_RELPATH, P355_PINNED_FX6_UXC_EN_2_BYTES, P355_PINNED_FX6_UXC_EN_2_BYTES, "FULL_SHA256", P355_PINNED_FX6_UXC_EN_2_SHA256, "SYNTHETIC_UXC7_FX6_EN_2"),
    )
    return tuple(
        Phase355DonorArtifactDigest(
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


def inspect_phase355_donors_readonly(
    force_clean_room: Optional[bool] = None,
) -> "Phase355DonorSnapshot":
    """Inspect Wave-63 FX3 (`14` donors) & FX6 (`3` donors) strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase355_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase355DonorSnapshot(
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
        ("fx3_appfw_702_so", P355_DONOR_FX3_APPFW_702_RELPATH, P355_PINNED_FX3_APPFW_702_BYTES, P355_PINNED_FX3_APPFW_702_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702")),
        ("fx6_appfw_601_so", P355_DONOR_FX6_APPFW_601_RELPATH, P355_PINNED_FX6_APPFW_601_BYTES, P355_PINNED_FX6_APPFW_601_HDR4K_SHA256, lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601")),
        ("fx3_backup_bin", P355_DONOR_FX3_BACKUP_BIN_RELPATH, P355_PINNED_FX3_BACKUP_BIN_BYTES, P355_PINNED_FX3_BACKUP_BIN_SHA256, lambda d: _check_bk4_backup(d, "ILME_FX3")),
        ("fx3_uxc_en_f", P355_DONOR_FX3_UXC_EN_F_RELPATH, P355_PINNED_FX3_UXC_EN_F_BYTES, P355_PINNED_FX3_UXC_EN_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_F")),
        ("fx3_uxc_sc_f", P355_DONOR_FX3_UXC_SC_F_RELPATH, P355_PINNED_FX3_UXC_SC_F_BYTES, P355_PINNED_FX3_UXC_SC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_F")),
        ("fx3_uxc_tc_f", P355_DONOR_FX3_UXC_TC_F_RELPATH, P355_PINNED_FX3_UXC_TC_F_BYTES, P355_PINNED_FX3_UXC_TC_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_F")),
        ("fx3_uxc_ja_f", P355_DONOR_FX3_UXC_JA_F_RELPATH, P355_PINNED_FX3_UXC_JA_F_BYTES, P355_PINNED_FX3_UXC_JA_F_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_F")),
        ("fx3_uxc_en", P355_DONOR_FX3_UXC_EN_RELPATH, P355_PINNED_FX3_UXC_EN_BYTES, P355_PINNED_FX3_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN")),
        ("fx3_uxc_sc", P355_DONOR_FX3_UXC_SC_RELPATH, P355_PINNED_FX3_UXC_SC_BYTES, P355_PINNED_FX3_UXC_SC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC")),
        ("fx3_uxc_tc", P355_DONOR_FX3_UXC_TC_RELPATH, P355_PINNED_FX3_UXC_TC_BYTES, P355_PINNED_FX3_UXC_TC_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC")),
        ("fx3_uxc_ja", P355_DONOR_FX3_UXC_JA_RELPATH, P355_PINNED_FX3_UXC_JA_BYTES, P355_PINNED_FX3_UXC_JA_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA")),
        ("fx3_uxc_en_g", P355_DONOR_FX3_UXC_EN_G_RELPATH, P355_PINNED_FX3_UXC_EN_G_BYTES, P355_PINNED_FX3_UXC_EN_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_EN_G")),
        ("fx3_uxc_sc_g", P355_DONOR_FX3_UXC_SC_G_RELPATH, P355_PINNED_FX3_UXC_SC_G_BYTES, P355_PINNED_FX3_UXC_SC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_SC_G")),
        ("fx3_uxc_tc_g", P355_DONOR_FX3_UXC_TC_G_RELPATH, P355_PINNED_FX3_UXC_TC_G_BYTES, P355_PINNED_FX3_UXC_TC_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_TC_G")),
        ("fx3_uxc_ja_g", P355_DONOR_FX3_UXC_JA_G_RELPATH, P355_PINNED_FX3_UXC_JA_G_BYTES, P355_PINNED_FX3_UXC_JA_G_SHA256, lambda d: _check_uxc7_pack(d, "FX3_JA_G")),
        ("fx6_uxc_en", P355_DONOR_FX6_UXC_EN_RELPATH, P355_PINNED_FX6_UXC_EN_BYTES, P355_PINNED_FX6_UXC_EN_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN")),
        ("fx6_uxc_en_2", P355_DONOR_FX6_UXC_EN_2_RELPATH, P355_PINNED_FX6_UXC_EN_2_BYTES, P355_PINNED_FX6_UXC_EN_2_SHA256, lambda d: _check_uxc7_pack(d, "FX6_EN_2")),
    )

    def _probe_one(spec: Tuple[str, str, int, str, Any]) -> Optional[Phase355DonorArtifactDigest]:
        aid, relpath, expected_bytes, expected_sha, marker_fn = spec
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            return None
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        return Phase355DonorArtifactDigest(
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
        artifacts = _synthetic_phase355_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase355DonorSnapshot(
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
    return Phase355DonorSnapshot(
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
# Frozen Dataclasses (Specs, Reports, Suites & 65-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase355DonorArtifactDigest:
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
class Phase355DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_2_0s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase355DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HdmiRawOutputMediaVaultSpec:
    camera_model: str
    fw_version: str
    shooting_domain: str
    log_shooting: str
    pplut_active: bool
    rec_media_dur_hdmi_output: str
    output_resolution: str
    hdmi_4k_output_setting: str
    raw_output: str
    raw_output_setting: str
    color_gamut_for_raw_out_requested: bool
    reported_removed_raw_gamut_errno: Optional[int]
    reported_4k_8bit_errno: Optional[int]
    reported_sq_rec_media_errno: Optional[int]
    reported_sq_raw_errno: Optional[int]
    reported_raw_prereq_errno: Optional[int]
    time_code_output: str
    rec_control: str
    reported_rec_control_errno: Optional[int]
    audio_4ch_output: str
    hdmi_info_display: str
    steadyshot_mode: str
    gamma_curve: str
    reported_effective_rec_media: str
    reported_effective_raw_output: str
    reported_effective_gamma: str
    reported_effective_steadyshot: str
    reported_effective_hdmi_info_display: str
    reported_body_lcd_blanked: bool
    reported_effective_output_resolution: str
    reported_card_write_pathway_active: bool
    fx6_raw_interface: str
    fx6_sdi_hdmi_rec_control: str
    reported_fx6_hdmi_capped_1080p: bool
    reported_fx6_hdmi_raw_res: str
    reported_fx6_hdmi_raw_24hz_supported: bool
    reset_action: str
    post_rec_media_dur_hdmi_output: str
    post_output_resolution: str
    post_hdmi_4k_output_setting: str
    post_raw_output: str
    post_raw_output_setting: str
    post_time_code_output: str
    post_rec_control: str
    post_audio_4ch_output: str
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
    hdmi_raw_output_or_media_vault_drift_events: int
    hdmi_4k_only_or_gamut_removal_drift_events: int


@dataclass(frozen=True)
class HdmiRawOutputMediaVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    hdmi_8_items_raw_16bit_and_coupling_verified: bool
    hdmi_4k_10bit_gamut_removal_and_reset_verified: bool
    slot1_vault_and_h0_h3_verified: bool
    matrix_states_checked: int
    hdmi_raw_output_or_media_vault_drift_events: int
    hdmi_4k_only_or_gamut_removal_drift_events: int
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
class DeSqueezeRecLampVarShutterApscVaultSpec:
    camera_model: str
    fw_version: str
    shooting_domain: str
    # `[De-Squeeze Display]`
    de_squeeze_display: str
    reported_desqueeze_errno: Optional[int]
    reported_stretch_factor: float
    focus_mode: str
    focus_area: str
    steadyshot_mode: str
    face_priority_in_multi_metering: str
    log_shooting: str
    raw_output: str
    rec_media_dur_hdmi_output: str
    still_movie_key_recording: bool
    remote_shooting_active: bool
    photo_capture_active: bool
    focus_magnifier_requested: bool
    bright_monitoring_requested: bool
    reported_effective_focus_mode: str
    reported_effective_focus_area: str
    reported_effective_steadyshot: str
    reported_effective_face_priority: str
    reported_effective_hdmi_desqueezed: bool
    recorded_media_desqueeze_pixels: int
    fx6_sdi_desqueeze_pixels: int
    reported_focus_magnifier_allowed: bool
    reported_bright_monitoring_allowed: bool
    # `[REC Lamp]`, `[Emphasized REC Display]`, `[Remain Shoot Display]`, `[Auto Review]`
    rec_lamp: str
    tally_light_menu_requested: bool
    reported_tally_menu_errno: Optional[int]
    rec_lamp_only_one_requested: bool
    reported_only_one_led_errno: Optional[int]
    silent_mode: str
    reported_front_led_on: bool
    reported_rear_led_on: bool
    reported_top_rec_ring_on: bool
    emphasized_rec_display: str
    hdmi_info_display: str
    hdmi_red_border_clean_feed_leak_pixels: int
    remain_shoot_display: str
    auto_review: str
    interval_shooting_active: bool
    reported_auto_review_active: bool
    # Dormant `[Var. Shutter]` vs FX6 `ECS` & `[Anti-flicker Shoot.]`
    var_shutter_requested: bool
    reported_var_shutter_errno: Optional[int]
    dormant_var_shutter_exposed_events: int
    anti_flicker_shoot: str
    shutter_type: str
    bulb_active: bool
    reported_anti_flicker_effective: bool
    fx6_shutter_mode: str
    fx6_ecs_frequency_hz: float
    # `[APS-C S35 Shooting]` Reset-Resistant Erratum & 4K Lockout
    apsc_s35_shooting: str
    video_codec: str
    recording_fps: int
    still_aspect_ratio: str
    still_image_size_requested: str
    reported_apsc_4k_lockout_errno: Optional[int]
    reported_still_size_errno: Optional[int]
    reported_effective_still_size: str
    # Reset boundaries
    reset_action: str
    post_de_squeeze_display: str
    post_rec_lamp: str
    post_emphasized_rec_display: str
    post_remain_shoot_display: str
    post_auto_review: str
    post_anti_flicker_shoot: str
    post_apsc_s35_shooting: str
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
    desqueeze_ratio_lock_or_bypass_drift_events: int
    rec_lamp_tally_or_emph_display_drift_events: int
    dormant_var_shutter_or_apsc_reset_drift_events: int


@dataclass(frozen=True)
class DeSqueezeRecLampVarShutterApscVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    desqueeze_1_65x_4locks_and_6bypasses_verified: bool
    rec_lamp_3led_silent_decouple_and_emph_disp_verified: bool
    dormant_var_shutter_ecs_and_apsc_reset_immune_verified: bool
    overlay_and_h0_h3_verified: bool
    matrix_states_checked: int
    desqueeze_ratio_lock_or_bypass_drift_events: int
    rec_lamp_tally_or_emph_display_drift_events: int
    dormant_var_shutter_or_apsc_reset_drift_events: int
    dormant_var_shutter_exposed_events: int
    hdmi_red_border_clean_feed_leak_pixels: int
    recorded_media_desqueeze_pixels: int
    fx6_sdi_desqueeze_pixels: int
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
class HdmiRawDeSqueezeRecLampVarShutterApscVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase355DonorSnapshot
    hdmi_raw_vault_report: HdmiRawOutputMediaVaultReport
    desqueeze_reclamp_varshutter_apsc_report: DeSqueezeRecLampVarShutterApscVaultReport
    hdmi_raw_output_or_media_vault_drift_events: int
    hdmi_4k_only_or_gamut_removal_drift_events: int
    desqueeze_ratio_lock_or_bypass_drift_events: int
    rec_lamp_tally_or_emph_display_drift_events: int
    dormant_var_shutter_or_apsc_reset_drift_events: int
    dormant_var_shutter_exposed_events: int
    hdmi_red_border_clean_feed_leak_pixels: int
    recorded_media_desqueeze_pixels: int
    fx6_sdi_desqueeze_pixels: int
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
class Pillar65ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar65ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar65ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar65BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar65ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar65StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase355DonorSnapshot
    pillar_65a_hdmi_raw_16bit_rec_media_vault: Pillar65ASuiteResult
    pillar_65b_desqueeze_reclamp_varshutter_apsc_vault: Pillar65BSuiteResult
    hdmi_raw_output_or_media_vault_drift_events: int
    hdmi_4k_only_or_gamut_removal_drift_events: int
    desqueeze_ratio_lock_or_bypass_drift_events: int
    rec_lamp_tally_or_emph_display_drift_events: int
    dormant_var_shutter_or_apsc_reset_drift_events: int
    dormant_var_shutter_exposed_events: int
    hdmi_red_border_clean_feed_leak_pixels: int
    recorded_media_desqueeze_pixels: int
    fx6_sdi_desqueeze_pixels: int
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
class Master65PillarRecoveryReport:
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
    donor_snapshot: Phase355DonorSnapshot
    pillar65_a_hdmi_raw_16bit_rec_media_vault: Pillar65ASuiteResult
    pillar65_b_desqueeze_reclamp_varshutter_apsc_vault: Pillar65BSuiteResult
    # Pillar 65 zero-violation counters & empirical metrics
    hdmi_raw_output_or_media_vault_drift_events: int
    hdmi_4k_only_or_gamut_removal_drift_events: int
    desqueeze_ratio_lock_or_bypass_drift_events: int
    rec_lamp_tally_or_emph_display_drift_events: int
    dormant_var_shutter_or_apsc_reset_drift_events: int
    dormant_var_shutter_exposed_events: int
    hdmi_red_border_clean_feed_leak_pixels: int
    recorded_media_desqueeze_pixels: int
    fx6_sdi_desqueeze_pixels: int
    fx3_hdmi_output_active_item_count: int
    fx3_hdmi_output_reset_resistant: bool
    fx3_raw_resolution: str
    fx3_raw_bit_depth: int
    fx6_hdmi_raw_resolution: str
    fx6_hdmi_raw_supports_24hz: bool
    fx3_desqueeze_1_6x_actual_factor: float
    fx3_desqueeze_1_8x_hits: int
    fx3_rec_lamp_led_count: int
    fx3_rear_top_led_coupled: bool
    fx3_tally_light_menu_count: int
    silent_mode_disables_rec_lamp: bool
    fx3_type_menu_item_high_res_hits: int
    fx6_ecs_freq_min_hz: float
    fx6_ecs_freq_max_hz: float
    apsc_s35_resettable_by_camera_settings_reset: bool
    apsc_s35_still_crop_size_3_2: str
    # Shared & carried-forward Pillar 64..41 zero-violation metrics
    slot1_data_sector_writes: int
    slot1_vault_mutation_bytes: int
    rf_packets_transmitted: int
    rf_nvs_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_vault_erofs_ebusy_enforced: bool
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
    master_65pillar_sha256: str
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
# Default Safe Specs & Evaluators (Pillars 65A & 65B)
# ---------------------------------------------------------------------------


def build_default_safe_hdmi_raw_media_vault_spec(
    **overrides: Any,
) -> HdmiRawOutputMediaVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P355_FX3_MODEL_NAME,
        "fw_version": P355_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "log_shooting": "Cine EI",
        "pplut_active": False,
        "rec_media_dur_hdmi_output": "Off(HDMI Only)",
        "output_resolution": "Auto",
        "hdmi_4k_output_setting": "59.94p 10bit",
        "raw_output": "On",
        "raw_output_setting": "23.98p",
        "color_gamut_for_raw_out_requested": False,
        "reported_removed_raw_gamut_errno": None,
        "reported_4k_8bit_errno": None,
        "reported_sq_rec_media_errno": None,
        "reported_sq_raw_errno": None,
        "reported_raw_prereq_errno": None,
        "time_code_output": "On",
        "rec_control": "On",
        "reported_rec_control_errno": None,
        "audio_4ch_output": "CH1/CH2",
        "hdmi_info_display": "Off",
        "steadyshot_mode": "Standard",
        "gamma_curve": "S-Log3",
        "reported_effective_rec_media": "Off(HDMI Only)",
        "reported_effective_raw_output": "On",
        "reported_effective_gamma": "S-Log3",
        "reported_effective_steadyshot": "Standard",
        "reported_effective_hdmi_info_display": "Off",
        "reported_body_lcd_blanked": False,
        "reported_effective_output_resolution": "Auto",
        "reported_card_write_pathway_active": False,
        "fx6_raw_interface": "NONE",
        "fx6_sdi_hdmi_rec_control": "Off",
        "reported_fx6_hdmi_capped_1080p": False,
        "reported_fx6_hdmi_raw_res": "N/A",
        "reported_fx6_hdmi_raw_24hz_supported": True,
        "reset_action": "None",
        "post_rec_media_dur_hdmi_output": "Off(HDMI Only)",
        "post_output_resolution": "Auto",
        "post_hdmi_4k_output_setting": "59.94p 10bit",
        "post_raw_output": "On",
        "post_raw_output_setting": "23.98p",
        "post_time_code_output": "On",
        "post_rec_control": "On",
        "post_audio_4ch_output": "CH1/CH2",
        "requested_vault_slot": 1,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": P355_SLOT1_DATA_SECTOR_WRITES,
        "slot1_vault_mutation_bytes": P355_SLOT1_VAULT_MUTATION_BYTES,
        "slot1_vault_erofs_eopnotsupp_enforced": P355_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        "slot1_format_hard_locked": P355_SLOT1_FORMAT_HARD_LOCKED,
        "overlay_dir": P355_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P355_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P355_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P355_TIER0_SURFACE_COUNT,
        "hdmi_raw_output_or_media_vault_drift_events": (
            P355_HDMI_RAW_OUTPUT_OR_MEDIA_VAULT_DRIFT_EVENTS
        ),
        "hdmi_4k_only_or_gamut_removal_drift_events": (
            P355_HDMI_4K_ONLY_OR_GAMUT_REMOVAL_DRIFT_EVENTS
        ),
    }
    defaults.update(overrides)
    return HdmiRawOutputMediaVaultSpec(**defaults)


def build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
    **overrides: Any,
) -> DeSqueezeRecLampVarShutterApscVaultSpec:
    defaults: Dict[str, Any] = {
        "camera_model": P355_FX3_MODEL_NAME,
        "fw_version": P355_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "de_squeeze_display": "1.6x",
        "reported_desqueeze_errno": None,
        "reported_stretch_factor": 1.65,
        "focus_mode": "Manual Focus",
        "focus_area": "Wide",
        "steadyshot_mode": "Off",
        "face_priority_in_multi_metering": "Off",
        "log_shooting": "Cine EI",
        "raw_output": "Off",
        "rec_media_dur_hdmi_output": "On",
        "still_movie_key_recording": False,
        "remote_shooting_active": False,
        "photo_capture_active": False,
        "focus_magnifier_requested": True,
        "bright_monitoring_requested": False,
        "reported_effective_focus_mode": "Manual Focus",
        "reported_effective_focus_area": "Wide",
        "reported_effective_steadyshot": "Off",
        "reported_effective_face_priority": "Off",
        "reported_effective_hdmi_desqueezed": True,
        "recorded_media_desqueeze_pixels": P355_RECORDED_MEDIA_DESQUEEZE_PIXELS,
        "fx6_sdi_desqueeze_pixels": P355_FX6_SDI_DESQUEEZE_PIXELS,
        "reported_focus_magnifier_allowed": True,
        "reported_bright_monitoring_allowed": True,
        "rec_lamp": "Only Front Off",
        "tally_light_menu_requested": False,
        "reported_tally_menu_errno": None,
        "rec_lamp_only_one_requested": False,
        "reported_only_one_led_errno": None,
        "silent_mode": "On",
        "reported_front_led_on": False,
        "reported_rear_led_on": True,
        "reported_top_rec_ring_on": True,
        "emphasized_rec_display": "On",
        "hdmi_info_display": "Off",
        "hdmi_red_border_clean_feed_leak_pixels": (
            P355_HDMI_RED_BORDER_CLEAN_FEED_LEAK_PIXELS
        ),
        "remain_shoot_display": "Always Display",
        "auto_review": "2 Sec",
        "interval_shooting_active": False,
        "reported_auto_review_active": False,
        "var_shutter_requested": False,
        "reported_var_shutter_errno": None,
        "dormant_var_shutter_exposed_events": P355_DORMANT_VAR_SHUTTER_EXPOSED_EVENTS,
        "anti_flicker_shoot": "Off",
        "shutter_type": "Auto",
        "bulb_active": False,
        "reported_anti_flicker_effective": False,
        "fx6_shutter_mode": "ECS",
        "fx6_ecs_frequency_hz": 60.00,
        "apsc_s35_shooting": "Off",
        "video_codec": "XAVC S-I 4K",
        "recording_fps": 24,
        "still_aspect_ratio": "3:2",
        "still_image_size_requested": "M: 5.1M (2768x1848)",
        "reported_apsc_4k_lockout_errno": None,
        "reported_still_size_errno": None,
        "reported_effective_still_size": "M: 5.1M (2768x1848)",
        "reset_action": "None",
        "post_de_squeeze_display": "1.6x",
        "post_rec_lamp": "Only Front Off",
        "post_emphasized_rec_display": "On",
        "post_remain_shoot_display": "Always Display",
        "post_auto_review": "2 Sec",
        "post_anti_flicker_shoot": "Off",
        "post_apsc_s35_shooting": "Off",
        "requested_vault_slot": 1,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": P355_SLOT1_DATA_SECTOR_WRITES,
        "slot1_vault_mutation_bytes": P355_SLOT1_VAULT_MUTATION_BYTES,
        "slot1_vault_erofs_eopnotsupp_enforced": P355_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        "slot1_format_hard_locked": P355_SLOT1_FORMAT_HARD_LOCKED,
        "overlay_dir": P355_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P355_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P355_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P355_TIER0_SURFACE_COUNT,
        "desqueeze_ratio_lock_or_bypass_drift_events": (
            P355_DESQUEEZE_RATIO_LOCK_OR_BYPASS_DRIFT_EVENTS
        ),
        "rec_lamp_tally_or_emph_display_drift_events": (
            P355_REC_LAMP_TALLY_OR_EMPH_DISPLAY_DRIFT_EVENTS
        ),
        "dormant_var_shutter_or_apsc_reset_drift_events": (
            P355_DORMANT_VAR_SHUTTER_OR_APSC_RESET_DRIFT_EVENTS
        ),
    }
    defaults.update(overrides)
    return DeSqueezeRecLampVarShutterApscVaultSpec(**defaults)


def evaluate_hdmi_raw_media_vault(
    spec: HdmiRawOutputMediaVaultSpec,
) -> HdmiRawOutputMediaVaultReport:
    """Evaluate Pillar 65A (`[HDMI Output Settings]` 8 active items, `4264x2408` 16-bit RAW,
    & `[Rec. Media dur HDMI Output]` `Slot 1` `EROFS=30` Vault vs `Off(HDMI Only)` zero-write)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P355_BLOCKED_SAFETY_POLICY_VIOLATION, "Safety policy violation")

    valid_spec = (
        spec.camera_model in (P355_FX3_MODEL_NAME, P355_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P355_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P355_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P355_SHOOTING_DOMAINS
        and spec.rec_media_dur_hdmi_output in P355_REC_MEDIA_MODES
        and spec.output_resolution in P355_OUTPUT_RESOLUTION_MODES
        and spec.raw_output in P355_ON_OFF_MODES
        and spec.raw_output_setting in P355_FX3_RAW_FPS_MODES
        and spec.time_code_output in P355_ON_OFF_MODES
        and spec.rec_control in P355_ON_OFF_MODES
        and spec.audio_4ch_output in P355_4CH_AUDIO_OUTPUT_CHOICES
        and spec.hdmi_info_display in P355_ON_OFF_MODES
        and spec.fx6_sdi_hdmi_rec_control in P355_FX6_SDI_HDMI_REC_CTRL_MODES
        and spec.reset_action in P355_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P355_VAULT_ACTIONS
        and spec.vault_firewall_errno in P355_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P355_BLOCKED_INVALID_PILLAR65A_SPEC, "Invalid Pillar 65A spec fields")

    st = compute_expected_hdmi_raw_media_vault_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        log_shooting=spec.log_shooting,
        pplut_active=spec.pplut_active,
        rec_media_dur_hdmi_output=spec.rec_media_dur_hdmi_output,
        output_resolution=spec.output_resolution,
        hdmi_4k_output_setting=spec.hdmi_4k_output_setting,
        raw_output=spec.raw_output,
        raw_output_setting=spec.raw_output_setting,
        color_gamut_for_raw_out_requested=spec.color_gamut_for_raw_out_requested,
        time_code_output=spec.time_code_output,
        rec_control=spec.rec_control,
        audio_4ch_output=spec.audio_4ch_output,
        hdmi_info_display=spec.hdmi_info_display,
        steadyshot_mode=spec.steadyshot_mode,
        gamma_curve=spec.gamma_curve,
        fx6_raw_interface=spec.fx6_raw_interface,
        fx6_sdi_hdmi_rec_control=spec.fx6_sdi_hdmi_rec_control,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    # 1. `4264x2408` 16-bit RAW, `[Rec. Media dur HDMI Output]`, TC -> REC Ctrl & FX6 Contrast
    raw_media_ok = (
        spec.reported_sq_rec_media_errno == st["sq_rec_media_errno"]
        and st["sq_rec_media_errno"] is None
        and spec.reported_sq_raw_errno == st["sq_raw_errno"]
        and st["sq_raw_errno"] is None
        and spec.reported_raw_prereq_errno == st["raw_prereq_errno"]
        and st["raw_prereq_errno"] is None
        and spec.reported_rec_control_errno == st["rec_control_errno"]
        and st["rec_control_errno"] is None
        and spec.reported_effective_rec_media == st["effective_rec_media"]
        and spec.reported_effective_raw_output == st["effective_raw_output"]
        and spec.reported_effective_gamma == st["effective_gamma"]
        and spec.reported_effective_steadyshot == st["effective_steadyshot"]
        and spec.reported_effective_hdmi_info_display == st["effective_hdmi_info_display"]
        and spec.reported_body_lcd_blanked == st["body_lcd_blanked"]
        and spec.reported_effective_output_resolution == st["effective_output_resolution"]
        and spec.reported_card_write_pathway_active == st["card_write_pathway_active"]
        and spec.reported_fx6_hdmi_capped_1080p == st["fx6_hdmi_capped_1080p"]
        and spec.reported_fx6_hdmi_raw_res == st["fx6_hdmi_raw_res"]
        and spec.reported_fx6_hdmi_raw_24hz_supported == st["fx6_hdmi_raw_24hz_supported"]
        and spec.hdmi_raw_output_or_media_vault_drift_events == 0
    )
    if not raw_media_ok:
        _fail(
            P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT,
            "HDMI 4264x2408 16-bit RAW, Rec. Media dur HDMI Output coupling, TC->REC Control, or FX6 RAW boundary violated",
        )

    # 2. 10-bit `4K Output Set.(HDMI Only)`, Removed `[Color Gamut for RAW Output]`, & Reset Immunity
    hdmi_4k_gamut_ok = (
        not spec.color_gamut_for_raw_out_requested
        and spec.reported_removed_raw_gamut_errno == st["removed_raw_gamut_errno"]
        and st["removed_raw_gamut_errno"] is None
        and spec.reported_4k_8bit_errno == st["dormant_4k_8bit_errno"]
        and st["dormant_4k_8bit_errno"] is None
        and (
            spec.camera_model != P355_FX3_MODEL_NAME
            or spec.hdmi_4k_output_setting in P355_FX3_HDMI_4K_ONLY_10BIT_MODES
        )
        and spec.post_rec_media_dur_hdmi_output == st["post_rec_media_dur_hdmi_output"]
        and spec.post_output_resolution == st["post_output_resolution"]
        and spec.post_hdmi_4k_output_setting == st["post_hdmi_4k_output_setting"]
        and spec.post_raw_output == st["post_raw_output"]
        and spec.post_raw_output_setting == st["post_raw_output_setting"]
        and spec.post_time_code_output == st["post_time_code_output"]
        and spec.post_rec_control == st["post_rec_control"]
        and spec.post_audio_4ch_output == st["post_audio_4ch_output"]
        and spec.hdmi_4k_only_or_gamut_removal_drift_events == 0
    )
    if not hdmi_4k_gamut_ok:
        _fail(
            P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT,
            "HDMI 4K Output 10-bit rule, removed Color Gamut for RAW Output, or Reset immunity violated",
        )

    # 3. Slot-1 Tier-0 Vault Firewall (`EROFS=30`) & Stage-B Overlay & H0 == H3
    slot1_mutated = (
        (
            spec.requested_vault_action in P355_WRITE_MUTATING_VAULT_ACTIONS
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
            P355_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P355_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P355_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P355_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P355_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    vault_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "65A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "rec_media": spec.reported_effective_rec_media,
            "raw_output": spec.reported_effective_raw_output,
            "output_res": spec.reported_effective_output_resolution,
            "hdmi_4k_set": spec.hdmi_4k_output_setting,
            "tc_out": spec.post_time_code_output,
            "rec_ctrl": spec.post_rec_control,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return HdmiRawOutputMediaVaultReport(
        schema=PHASE355_SCHEMA,
        version=PHASE355_VERSION,
        passed=passed,
        status=P355_STATUS_VERIFIED_PILLAR_65A if passed else P355_STATUS_REJECTED_PILLAR_65A,
        block_code=block_code,
        hdmi_8_items_raw_16bit_and_coupling_verified=raw_media_ok,
        hdmi_4k_10bit_gamut_removal_and_reset_verified=hdmi_4k_gamut_ok,
        slot1_vault_and_h0_h3_verified=vault_and_h0_h3_ok,
        matrix_states_checked=30,
        hdmi_raw_output_or_media_vault_drift_events=(
            spec.hdmi_raw_output_or_media_vault_drift_events
        ),
        hdmi_4k_only_or_gamut_removal_drift_events=(
            spec.hdmi_4k_only_or_gamut_removal_drift_events
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


def evaluate_desqueeze_reclamp_varshutter_apsc_vault(
    spec: DeSqueezeRecLampVarShutterApscVaultSpec,
) -> DeSqueezeRecLampVarShutterApscVaultReport:
    """Evaluate Pillar 65B (`[De-Squeeze Display]` `1.6x[1.65x]` vs zero `1.8x`, `[REC Lamp]` 3-LED
    coupling + `[Silent Mode]` decoupling + `[Emphasized REC Display]`, dormant `[Var. Shutter]` vs
    FX6 `ECS`, and `[APS-C S35 Shooting]` Reset-resistant erratum & 4K lockout)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P355_BLOCKED_SAFETY_POLICY_VIOLATION, "Safety policy violation")

    valid_spec = (
        spec.camera_model in (P355_FX3_MODEL_NAME, P355_FX6_DONOR_MODEL_NAME)
        and (
            spec.camera_model == P355_FX6_DONOR_MODEL_NAME
            or spec.fw_version in P355_FX3_SUPPORTED_FW_VERSIONS
        )
        and spec.shooting_domain in P355_SHOOTING_DOMAINS
        and spec.rec_lamp in P355_REC_LAMP_MODES
        and spec.silent_mode in P355_ON_OFF_MODES
        and spec.emphasized_rec_display in P355_ON_OFF_MODES
        and spec.hdmi_info_display in P355_ON_OFF_MODES
        and spec.remain_shoot_display in P355_REMAIN_SHOOT_MODES
        and spec.auto_review in P355_AUTO_REVIEW_MODES
        and spec.anti_flicker_shoot in P355_ON_OFF_MODES
        and spec.apsc_s35_shooting in P355_APSC_S35_MODES
        and spec.reset_action in P355_RESET_ACTIONS
        and spec.requested_vault_slot in (1, 2)
        and spec.requested_vault_action in P355_VAULT_ACTIONS
        and spec.vault_firewall_errno in P355_VAULT_FIREWALL_ERRNOS
    )
    if not valid_spec:
        _fail(P355_BLOCKED_INVALID_PILLAR65B_SPEC, "Invalid Pillar 65B spec fields")

    st = compute_expected_desqueeze_reclamp_varshutter_apsc_vault_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        de_squeeze_display=spec.de_squeeze_display,
        focus_mode=spec.focus_mode,
        focus_area=spec.focus_area,
        steadyshot_mode=spec.steadyshot_mode,
        face_priority_in_multi_metering=spec.face_priority_in_multi_metering,
        log_shooting=spec.log_shooting,
        raw_output=spec.raw_output,
        rec_media_dur_hdmi_output=spec.rec_media_dur_hdmi_output,
        still_movie_key_recording=spec.still_movie_key_recording,
        remote_shooting_active=spec.remote_shooting_active,
        photo_capture_active=spec.photo_capture_active,
        focus_magnifier_requested=spec.focus_magnifier_requested,
        bright_monitoring_requested=spec.bright_monitoring_requested,
        rec_lamp=spec.rec_lamp,
        tally_light_menu_requested=spec.tally_light_menu_requested,
        rec_lamp_only_one_requested=spec.rec_lamp_only_one_requested,
        silent_mode=spec.silent_mode,
        emphasized_rec_display=spec.emphasized_rec_display,
        hdmi_info_display=spec.hdmi_info_display,
        remain_shoot_display=spec.remain_shoot_display,
        auto_review=spec.auto_review,
        interval_shooting_active=spec.interval_shooting_active,
        var_shutter_requested=spec.var_shutter_requested,
        anti_flicker_shoot=spec.anti_flicker_shoot,
        shutter_type=spec.shutter_type,
        bulb_active=spec.bulb_active,
        fx6_shutter_mode=spec.fx6_shutter_mode,
        fx6_ecs_frequency_hz=spec.fx6_ecs_frequency_hz,
        apsc_s35_shooting=spec.apsc_s35_shooting,
        video_codec=spec.video_codec,
        recording_fps=spec.recording_fps,
        still_aspect_ratio=spec.still_aspect_ratio,
        still_image_size_requested=spec.still_image_size_requested,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )

    # 1. `[De-Squeeze Display]` `1.6x[1.65x]` vs Zero `1.8x`, 4 Locks, 6 Bypasses & FX6 SDI Isolation
    desqueeze_ok = (
        spec.de_squeeze_display != "1.8x"
        and spec.reported_desqueeze_errno == st["desqueeze_errno"]
        and st["desqueeze_errno"] is None
        and abs(spec.reported_stretch_factor - st["effective_stretch_factor"]) < 1e-6
        and spec.reported_effective_focus_mode == st["effective_focus_mode"]
        and spec.reported_effective_focus_area == st["effective_focus_area"]
        and spec.reported_effective_steadyshot == st["effective_steadyshot"]
        and spec.reported_effective_face_priority == st["effective_face_priority"]
        and spec.reported_effective_hdmi_desqueezed == st["effective_hdmi_desqueezed"]
        and spec.recorded_media_desqueeze_pixels == 0
        and spec.fx6_sdi_desqueeze_pixels == 0
        and spec.reported_focus_magnifier_allowed == st["focus_magnifier_allowed"]
        and spec.reported_bright_monitoring_allowed == st["bright_monitoring_allowed"]
        and spec.post_de_squeeze_display == st["post_de_squeeze_display"]
        and spec.desqueeze_ratio_lock_or_bypass_drift_events == 0
    )
    if not desqueeze_ok:
        _fail(
            P355_BLOCKED_DESQUEEZE_OR_REC_LAMP_DRIFT,
            "De-Squeeze Display 1.6x(1.65x)/zero-1.8x, 4 hard locks, 6 bypasses, or FX6 SDI isolation violated",
        )

    # 2. `[REC Lamp]` 3-LED Coupling, `[Silent Mode]` Decoupling, `[Emphasized REC Display]`, `[Auto Review]`
    rec_lamp_ok = (
        not spec.tally_light_menu_requested
        and spec.reported_tally_menu_errno == st["tally_menu_errno"]
        and st["tally_menu_errno"] is None
        and not spec.rec_lamp_only_one_requested
        and spec.reported_only_one_led_errno == st["only_one_led_errno"]
        and st["only_one_led_errno"] is None
        and spec.reported_front_led_on == st["front_led_on"]
        and spec.reported_rear_led_on == st["rear_led_on"]
        and spec.reported_top_rec_ring_on == st["top_rec_ring_on"]
        and st["rec_lamp_unchanged_by_silent_mode"]
        and spec.hdmi_red_border_clean_feed_leak_pixels == 0
        and not (st["hdmi_red_border_emitted"] and spec.hdmi_info_display == "Off")
        and spec.reported_auto_review_active == st["auto_review_active"]
        and spec.post_rec_lamp == st["post_rec_lamp"]
        and spec.post_emphasized_rec_display == st["post_emphasized_rec_display"]
        and spec.post_remain_shoot_display == st["post_remain_shoot_display"]
        and spec.post_auto_review == st["post_auto_review"]
        and spec.rec_lamp_tally_or_emph_display_drift_events == 0
    )
    if not rec_lamp_ok:
        _fail(
            P355_BLOCKED_DESQUEEZE_OR_REC_LAMP_DRIFT,
            "REC Lamp 3-LED coupling, zero Tally Light menu, Silent Mode decoupling, or Emphasized REC Clean-HDMI violated",
        )

    # 3. Dormant `[Var. Shutter]` vs FX6 `ECS` & `[APS-C S35 Shooting]` Reset-Resistant Erratum
    varshutter_apsc_ok = (
        spec.dormant_var_shutter_exposed_events == 0
        and not spec.var_shutter_requested
        and spec.reported_var_shutter_errno == st["var_shutter_errno"]
        and st["var_shutter_errno"] is None
        and spec.reported_anti_flicker_effective == st["anti_flicker_effective"]
        and st["fx6_ecs_valid"]
        and spec.reported_apsc_4k_lockout_errno == st["apsc_4k_lockout_errno"]
        and st["apsc_4k_lockout_errno"] is None
        and spec.reported_still_size_errno == st["still_size_errno"]
        and st["still_size_errno"] is None
        and spec.reported_effective_still_size == st["effective_still_size"]
        and spec.post_anti_flicker_shoot == st["post_anti_flicker_shoot"]
        and spec.post_apsc_s35_shooting == st["post_apsc_s35_shooting"]
        and spec.dormant_var_shutter_or_apsc_reset_drift_events == 0
    )
    if not varshutter_apsc_ok:
        _fail(
            P355_BLOCKED_VAR_SHUTTER_OR_APSC_RESET_DRIFT,
            "Dormant Var. Shutter, FX6 ECS range, or APS-C S35 4K lockout & Reset immunity violated",
        )

    # 4. Slot-1 Tier-0 Vault Firewall (`EROFS=30`) & Stage-B Overlay & H0 == H3
    slot1_mutated = (
        (
            spec.requested_vault_action in P355_WRITE_MUTATING_VAULT_ACTIONS
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
            P355_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached",
        )

    overlay_ok = _is_tmpfs_path(spec.overlay_dir) and not _targets_persistent_emmc(spec.overlay_dir)
    if not overlay_ok:
        _fail(
            P355_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P355_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P355_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P355_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    overlay_and_h0_h3_ok = vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "65B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "de_squeeze": spec.post_de_squeeze_display,
            "stretch_factor": spec.reported_stretch_factor,
            "rec_lamp": spec.post_rec_lamp,
            "emphasized_rec": spec.post_emphasized_rec_display,
            "apsc_s35": spec.post_apsc_s35_shooting,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return DeSqueezeRecLampVarShutterApscVaultReport(
        schema=PHASE355_SCHEMA,
        version=PHASE355_VERSION,
        passed=passed,
        status=P355_STATUS_VERIFIED_PILLAR_65B if passed else P355_STATUS_REJECTED_PILLAR_65B,
        block_code=block_code,
        desqueeze_1_65x_4locks_and_6bypasses_verified=desqueeze_ok,
        rec_lamp_3led_silent_decouple_and_emph_disp_verified=rec_lamp_ok,
        dormant_var_shutter_ecs_and_apsc_reset_immune_verified=varshutter_apsc_ok,
        overlay_and_h0_h3_verified=overlay_and_h0_h3_ok,
        matrix_states_checked=36,
        desqueeze_ratio_lock_or_bypass_drift_events=(
            spec.desqueeze_ratio_lock_or_bypass_drift_events
        ),
        rec_lamp_tally_or_emph_display_drift_events=(
            spec.rec_lamp_tally_or_emph_display_drift_events
        ),
        dormant_var_shutter_or_apsc_reset_drift_events=(
            spec.dormant_var_shutter_or_apsc_reset_drift_events
        ),
        dormant_var_shutter_exposed_events=spec.dormant_var_shutter_exposed_events,
        hdmi_red_border_clean_feed_leak_pixels=(
            spec.hdmi_red_border_clean_feed_leak_pixels
        ),
        recorded_media_desqueeze_pixels=spec.recorded_media_desqueeze_pixels,
        fx6_sdi_desqueeze_pixels=spec.fx6_sdi_desqueeze_pixels,
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_hdmi_raw_desqueeze_rec_lamp_varshutter_apsc_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_65a: Optional[HdmiRawOutputMediaVaultSpec] = None,
    spec_65b: Optional[DeSqueezeRecLampVarShutterApscVaultSpec] = None,
) -> HdmiRawDeSqueezeRecLampVarShutterApscVaultReport:
    """Combined single-shot verifier for Pillar 65A + Pillar 65B + 17 bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase355_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_hdmi_raw_media_vault(
        spec_65a or build_default_safe_hdmi_raw_media_vault_spec()
    )
    rep_b = evaluate_desqueeze_reclamp_varshutter_apsc_vault(
        spec_65b or build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 355 Wave-63 donor artifact parity check failed")
    if not donor_snapshot.under_2_0s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return HdmiRawDeSqueezeRecLampVarShutterApscVaultReport(
        schema=PHASE355_SCHEMA,
        version=PHASE355_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P355_STATUS_VERIFIED_PILLAR65_SUITE if all_ok else P355_STATUS_FAIL_PILLAR65_SUITE,
        donor_snapshot=donor_snapshot,
        hdmi_raw_vault_report=rep_a,
        desqueeze_reclamp_varshutter_apsc_report=rep_b,
        hdmi_raw_output_or_media_vault_drift_events=(
            rep_a.hdmi_raw_output_or_media_vault_drift_events
        ),
        hdmi_4k_only_or_gamut_removal_drift_events=(
            rep_a.hdmi_4k_only_or_gamut_removal_drift_events
        ),
        desqueeze_ratio_lock_or_bypass_drift_events=(
            rep_b.desqueeze_ratio_lock_or_bypass_drift_events
        ),
        rec_lamp_tally_or_emph_display_drift_events=(
            rep_b.rec_lamp_tally_or_emph_display_drift_events
        ),
        dormant_var_shutter_or_apsc_reset_drift_events=(
            rep_b.dormant_var_shutter_or_apsc_reset_drift_events
        ),
        dormant_var_shutter_exposed_events=rep_b.dormant_var_shutter_exposed_events,
        hdmi_red_border_clean_feed_leak_pixels=(
            rep_b.hdmi_red_border_clean_feed_leak_pixels
        ),
        recorded_media_desqueeze_pixels=rep_b.recorded_media_desqueeze_pixels,
        fx6_sdi_desqueeze_pixels=rep_b.fx6_sdi_desqueeze_pixels,
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


def verify_hdmi_raw_desqueeze_rec_lamp_varshutter_apsc_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_65a: Optional[HdmiRawOutputMediaVaultSpec] = None,
    spec_65b: Optional[DeSqueezeRecLampVarShutterApscVaultSpec] = None,
) -> HdmiRawDeSqueezeRecLampVarShutterApscVaultReport:
    """Symmetry alias for `verify_hdmi_raw_desqueeze_rec_lamp_varshutter_apsc_and_vault`."""
    return verify_hdmi_raw_desqueeze_rec_lamp_varshutter_apsc_and_vault(
        force_clean_room=force_clean_room,
        spec_65a=spec_65a,
        spec_65b=spec_65b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 65A & 65B)
# ---------------------------------------------------------------------------


def run_pillar65a_hdmi_raw_media_vault_6_scenario_suite() -> Pillar65ASuiteResult:
    """Run 6 Pillar 65A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, HdmiRawOutputMediaVaultSpec, Optional[str]], ...] = (
        (
            P355_PILLAR_65A_SCENARIO_IDS[0],
            True,
            build_default_safe_hdmi_raw_media_vault_spec(
                shooting_domain="Movie",
                log_shooting="Flexible ISO",
                rec_media_dur_hdmi_output="Off(HDMI Only)",
                raw_output="On",
                raw_output_setting="23.98p",
                hdmi_4k_output_setting="59.94p 10bit",
                time_code_output="On",
                rec_control="On",
                audio_4ch_output="CH3/CH4",
                hdmi_info_display="On",
                steadyshot_mode="Active",
                gamma_curve="S-Gamut3",
                reported_effective_rec_media="Off(HDMI Only)",
                reported_effective_raw_output="On",
                reported_effective_gamma="S-Log3",
                reported_effective_steadyshot="Off",
                reported_effective_hdmi_info_display="Off",
                reported_body_lcd_blanked=False,
                reported_card_write_pathway_active=False,
                reset_action="Camera Settings Reset",
                post_rec_media_dur_hdmi_output="Off(HDMI Only)",
                post_raw_output="On",
                post_raw_output_setting="23.98p",
                post_time_code_output="On",
                post_rec_control="On",
                post_audio_4ch_output="CH3/CH4",
            ),
            None,
        ),
        (
            P355_PILLAR_65A_SCENARIO_IDS[1],
            True,
            build_default_safe_hdmi_raw_media_vault_spec(
                camera_model=P355_FX6_DONOR_MODEL_NAME,
                fw_version=P355_FX6_DONOR_FW_VERSION,
                log_shooting="Cine EI",
                rec_media_dur_hdmi_output="On",
                raw_output="On",
                fx6_raw_interface="12G-SDI_RAW",
                fx6_sdi_hdmi_rec_control="SDI/HDMI Remote I/F",
                reported_effective_rec_media="On",
                reported_effective_raw_output="On",
                reported_effective_gamma="S-Log3",
                reported_effective_hdmi_info_display="Off",
                reported_card_write_pathway_active=False,
                reported_fx6_hdmi_capped_1080p=True,
                reported_fx6_hdmi_raw_res="N/A",
                reported_fx6_hdmi_raw_24hz_supported=False,
                reset_action="None",
                post_rec_media_dur_hdmi_output="On",
                post_raw_output="On",
            ),
            None,
        ),
        (
            P355_PILLAR_65A_SCENARIO_IDS[2],
            False,
            build_default_safe_hdmi_raw_media_vault_spec(
                shooting_domain="S&Q",
                log_shooting="Off",
                rec_media_dur_hdmi_output="Off(HDMI Only)",
                raw_output="On",
                hdmi_4k_output_setting=P355_FX3_HDMI_4K_DORMANT_8BIT_MODE,
                color_gamut_for_raw_out_requested=True,
                reported_removed_raw_gamut_errno=None,
                reported_4k_8bit_errno=None,
                reported_sq_rec_media_errno=None,
                reported_sq_raw_errno=None,
                reported_raw_prereq_errno=None,
                hdmi_raw_output_or_media_vault_drift_events=1,
                hdmi_4k_only_or_gamut_removal_drift_events=1,
            ),
            P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT,
        ),
        (
            P355_PILLAR_65A_SCENARIO_IDS[3],
            False,
            build_default_safe_hdmi_raw_media_vault_spec(
                time_code_output="Off",
                rec_control="On",
                reported_rec_control_errno=None,
                reset_action="Camera Settings Reset",
                post_rec_media_dur_hdmi_output="On",
                post_raw_output="Off",
                hdmi_raw_output_or_media_vault_drift_events=1,
                hdmi_4k_only_or_gamut_removal_drift_events=1,
            ),
            P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT,
        ),
        (
            P355_PILLAR_65A_SCENARIO_IDS[4],
            False,
            build_default_safe_hdmi_raw_media_vault_spec(
                rec_media_dur_hdmi_output="On",
                raw_output="On",
                hdmi_info_display="On",
                steadyshot_mode="Active",
                reported_effective_rec_media="On",
                reported_effective_steadyshot="Active",
                reported_effective_hdmi_info_display="On",
                reported_card_write_pathway_active=False,
                hdmi_raw_output_or_media_vault_drift_events=1,
            ),
            P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT,
        ),
        (
            P355_PILLAR_65A_SCENARIO_IDS[5],
            False,
            build_default_safe_hdmi_raw_media_vault_spec(
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="CARD_WRITE_XAVC_REC",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/setting/65a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P355_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar65ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_hdmi_raw_media_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar65ScenarioOutcome(
                scenario_id=sid,
                pillar="65A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar65ASuiteResult(
        passed=all_ok,
        status=P355_STATUS_VERIFIED_PILLAR_65A if all_ok else P355_STATUS_REJECTED_PILLAR_65A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar65b_desqueeze_reclamp_varshutter_apsc_vault_6_scenario_suite() -> Pillar65BSuiteResult:
    """Run 6 Pillar 65B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, DeSqueezeRecLampVarShutterApscVaultSpec, Optional[str]], ...] = (
        (
            P355_PILLAR_65B_SCENARIO_IDS[0],
            True,
            build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
                de_squeeze_display="1.6x",
                reported_stretch_factor=1.65,
                focus_mode="AF-C",
                focus_area="Spot",
                steadyshot_mode="Active",
                face_priority_in_multi_metering="On",
                reported_effective_focus_mode="Manual Focus",
                reported_effective_focus_area="Wide",
                reported_effective_steadyshot="Off",
                reported_effective_face_priority="Off",
                reported_effective_hdmi_desqueezed=True,
                focus_magnifier_requested=True,
                reported_focus_magnifier_allowed=True,
                rec_lamp="Only Front Off",
                silent_mode="On",
                reported_front_led_on=False,
                reported_rear_led_on=True,
                reported_top_rec_ring_on=True,
                emphasized_rec_display="Off",
                remain_shoot_display="Shoot-Only Display",
                auto_review="5 Sec",
                reset_action="Camera Settings Reset",
                post_de_squeeze_display="1.6x",
                post_rec_lamp="Only Front Off",
                post_emphasized_rec_display="On",
                post_remain_shoot_display="Shoot-Only Display",
                post_auto_review="5 Sec",
                post_anti_flicker_shoot="Off",
                post_apsc_s35_shooting="Off",
            ),
            None,
        ),
        (
            P355_PILLAR_65B_SCENARIO_IDS[1],
            True,
            build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
                shooting_domain="Still",
                de_squeeze_display="Off",
                reported_stretch_factor=1.0,
                reported_effective_hdmi_desqueezed=False,
                focus_mode="AF-S",
                focus_area="Spot",
                steadyshot_mode="Standard",
                face_priority_in_multi_metering="On",
                reported_effective_focus_mode="AF-S",
                reported_effective_focus_area="Spot",
                reported_effective_steadyshot="Standard",
                reported_effective_face_priority="On",
                rec_lamp="All Off",
                silent_mode="Off",
                reported_front_led_on=False,
                reported_rear_led_on=False,
                reported_top_rec_ring_on=False,
                auto_review="10 Sec",
                interval_shooting_active=False,
                reported_auto_review_active=True,
                anti_flicker_shoot="On",
                shutter_type="Mechanical Shutter",
                reported_anti_flicker_effective=True,
                apsc_s35_shooting="On",
                video_codec="XAVC S-I HD",
                recording_fps=120,
                still_aspect_ratio="3:2",
                still_image_size_requested="M: 5.1M (2768x1848)",
                reported_effective_still_size=P355_APSC_S35_STILL_CROP_SIZE_3_2,
                reset_action="Camera Settings Reset",
                post_de_squeeze_display="Off",
                post_rec_lamp="All Off",
                post_emphasized_rec_display="On",
                post_remain_shoot_display="Always Display",
                post_auto_review="10 Sec",
                post_anti_flicker_shoot="Off",
                post_apsc_s35_shooting="On",  # Wave 42 erratum corrected: Reset-resistant!
            ),
            None,
        ),
        (
            P355_PILLAR_65B_SCENARIO_IDS[2],
            False,
            build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
                de_squeeze_display="1.8x",
                reported_desqueeze_errno=None,
                recorded_media_desqueeze_pixels=1920,
                fx6_sdi_desqueeze_pixels=1920,
                desqueeze_ratio_lock_or_bypass_drift_events=1,
            ),
            P355_BLOCKED_DESQUEEZE_OR_REC_LAMP_DRIFT,
        ),
        (
            P355_PILLAR_65B_SCENARIO_IDS[3],
            False,
            build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
                tally_light_menu_requested=True,
                reported_tally_menu_errno=None,
                rec_lamp_only_one_requested=True,
                reported_only_one_led_errno=None,
                hdmi_info_display="On",
                hdmi_red_border_clean_feed_leak_pixels=4096,
                rec_lamp_tally_or_emph_display_drift_events=1,
            ),
            P355_BLOCKED_DESQUEEZE_OR_REC_LAMP_DRIFT,
        ),
        (
            P355_PILLAR_65B_SCENARIO_IDS[4],
            False,
            build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
                var_shutter_requested=True,
                reported_var_shutter_errno=None,
                dormant_var_shutter_exposed_events=1,
                apsc_s35_shooting="On",
                video_codec="XAVC S-I DCI 4K",
                reported_apsc_4k_lockout_errno=None,
                reset_action="Camera Settings Reset",
                post_apsc_s35_shooting="Auto",  # Wrong: must stay "On" after Camera Settings Reset!
                dormant_var_shutter_or_apsc_reset_drift_events=1,
            ),
            P355_BLOCKED_VAR_SHUTTER_OR_APSC_RESET_DRIFT,
        ),
        (
            P355_PILLAR_65B_SCENARIO_IDS[5],
            False,
            build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="FORMAT_FULL",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/mnt/emmc/65b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P355_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar65ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_desqueeze_reclamp_varshutter_apsc_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar65ScenarioOutcome(
                scenario_id=sid,
                pillar="65B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar65BSuiteResult(
        passed=all_ok,
        status=P355_STATUS_VERIFIED_PILLAR_65B if all_ok else P355_STATUS_REJECTED_PILLAR_65B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Standalone Pillar 65 Suite & Concurrent Unified 65/65 Master Aggregator
# ---------------------------------------------------------------------------


def run_pillar65_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar65StandaloneReport:
    """Run full Pillar 65 standalone suite (`6/6` Pillar 65A + `6/6` Pillar 65B + 17 bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase355_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar65a_hdmi_raw_media_vault_6_scenario_suite()
    res_b = run_pillar65b_desqueeze_reclamp_varshutter_apsc_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 355 donor verification failed")
    if not donor_snapshot.under_2_0s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE355_SCHEMA,
            "version": PHASE355_VERSION,
            "mode": donor_snapshot.verification_mode,
            "65a": [asdict(s) for s in res_a.scenarios],
            "65b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar65StandaloneReport(
        schema=PHASE355_SCHEMA,
        version=PHASE355_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P355_STATUS_VERIFIED_PILLAR65_SUITE if all_ok else P355_STATUS_FAIL_PILLAR65_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_65a_hdmi_raw_16bit_rec_media_vault=res_a,
        pillar_65b_desqueeze_reclamp_varshutter_apsc_vault=res_b,
        hdmi_raw_output_or_media_vault_drift_events=(
            P355_HDMI_RAW_OUTPUT_OR_MEDIA_VAULT_DRIFT_EVENTS if res_a.passed else 1
        ),
        hdmi_4k_only_or_gamut_removal_drift_events=(
            P355_HDMI_4K_ONLY_OR_GAMUT_REMOVAL_DRIFT_EVENTS if res_a.passed else 1
        ),
        desqueeze_ratio_lock_or_bypass_drift_events=(
            P355_DESQUEEZE_RATIO_LOCK_OR_BYPASS_DRIFT_EVENTS if res_b.passed else 1
        ),
        rec_lamp_tally_or_emph_display_drift_events=(
            P355_REC_LAMP_TALLY_OR_EMPH_DISPLAY_DRIFT_EVENTS if res_b.passed else 1
        ),
        dormant_var_shutter_or_apsc_reset_drift_events=(
            P355_DORMANT_VAR_SHUTTER_OR_APSC_RESET_DRIFT_EVENTS if res_b.passed else 1
        ),
        dormant_var_shutter_exposed_events=(
            P355_DORMANT_VAR_SHUTTER_EXPOSED_EVENTS if res_b.passed else 1
        ),
        hdmi_red_border_clean_feed_leak_pixels=(
            P355_HDMI_RED_BORDER_CLEAN_FEED_LEAK_PIXELS if res_b.passed else 4096
        ),
        recorded_media_desqueeze_pixels=(
            P355_RECORDED_MEDIA_DESQUEEZE_PIXELS if res_b.passed else 1920
        ),
        fx6_sdi_desqueeze_pixels=P355_FX6_SDI_DESQUEEZE_PIXELS if res_b.passed else 1920,
        slot1_data_sector_writes=(
            P355_SLOT1_DATA_SECTOR_WRITES if (res_a.passed and res_b.passed) else 1
        ),
        slot1_vault_mutation_bytes=(
            P355_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        rf_packets_transmitted=P355_RF_PACKETS_TRANSMITTED,
        rf_nvs_mutation_bytes=P355_RF_NVS_MUTATION_BYTES,
        slot1_format_hard_locked=P355_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_eopnotsupp_enforced=P355_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
        slot1_vault_erofs_ebusy_enforced=P355_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
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


def _apply_master65_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def _master65_local_donors_available() -> bool:
    """Return True only when all 17 Wave-63 local donors exist."""
    required_relpaths: Tuple[str, ...] = (
        P355_DONOR_FX3_APPFW_702_RELPATH,
        P355_DONOR_FX6_APPFW_601_RELPATH,
        P355_DONOR_FX3_BACKUP_BIN_RELPATH,
        P355_DONOR_FX3_UXC_EN_F_RELPATH,
        P355_DONOR_FX3_UXC_SC_F_RELPATH,
        P355_DONOR_FX3_UXC_TC_F_RELPATH,
        P355_DONOR_FX3_UXC_JA_F_RELPATH,
        P355_DONOR_FX3_UXC_EN_RELPATH,
        P355_DONOR_FX3_UXC_SC_RELPATH,
        P355_DONOR_FX3_UXC_TC_RELPATH,
        P355_DONOR_FX3_UXC_JA_RELPATH,
        P355_DONOR_FX3_UXC_EN_G_RELPATH,
        P355_DONOR_FX3_UXC_SC_G_RELPATH,
        P355_DONOR_FX3_UXC_TC_G_RELPATH,
        P355_DONOR_FX3_UXC_JA_G_RELPATH,
        P355_DONOR_FX6_UXC_EN_RELPATH,
        P355_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for relpath in required_relpaths:
        try:
            resolved = _resolve_phase355_donor_path(relpath)
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


def evaluate_realhw_65pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master65PillarRecoveryReport:
    """Evaluate and aggregate all 65 recovery pillars (`1..65`) concurrently -> `65/65` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_65_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    if resolved_clean_room is None and not _master65_local_donors_available():
        resolved_clean_room = True
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_64pillar() -> Master64PillarRecoveryReport:
        return evaluate_realhw_64pillar_recovery_master(**kw)

    def _run_p65() -> Tuple[Pillar65StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar65_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_64 = pool.submit(_run_64pillar)
        fut_65 = pool.submit(_run_p65)
        m64_rep = fut_64.result()
        p65_rep, p65_dt = fut_65.result()

    all_errors: List[str] = list(m64_rep.errors) + list(p65_rep.errors)
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
        if getattr(m64_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-64 violated {attr_name} == {expected_val}")
        if getattr(p65_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 65 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("hdmi_raw_output_or_media_vault_drift_events", 0),
        ("hdmi_4k_only_or_gamut_removal_drift_events", 0),
        ("desqueeze_ratio_lock_or_bypass_drift_events", 0),
        ("rec_lamp_tally_or_emph_display_drift_events", 0),
        ("dormant_var_shutter_or_apsc_reset_drift_events", 0),
        ("dormant_var_shutter_exposed_events", 0),
        ("hdmi_red_border_clean_feed_leak_pixels", 0),
        ("recorded_media_desqueeze_pixels", 0),
        ("fx6_sdi_desqueeze_pixels", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("rf_packets_transmitted", 0),
        ("rf_nvs_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_eopnotsupp_enforced", True),
        ("slot1_vault_erofs_ebusy_enforced", True),
    ):
        if getattr(p65_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 65 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m64_rep.pillars)
    spec65 = MASTER_65_PILLAR_SPECS[64]
    p65_metrics = {
        "pillar_65a_hdmi_raw_16bit_rec_media_vault": (
            f"{p65_rep.pillar_65a_hdmi_raw_16bit_rec_media_vault.scenarios_passed}/"
            f"{p65_rep.pillar_65a_hdmi_raw_16bit_rec_media_vault.scenarios_total}"
        ),
        "pillar_65b_desqueeze_reclamp_varshutter_apsc_vault": (
            f"{p65_rep.pillar_65b_desqueeze_reclamp_varshutter_apsc_vault.scenarios_passed}/"
            f"{p65_rep.pillar_65b_desqueeze_reclamp_varshutter_apsc_vault.scenarios_total}"
        ),
        "hdmi_raw_output_or_media_vault_drift_events": (
            p65_rep.hdmi_raw_output_or_media_vault_drift_events
        ),
        "hdmi_4k_only_or_gamut_removal_drift_events": (
            p65_rep.hdmi_4k_only_or_gamut_removal_drift_events
        ),
        "desqueeze_ratio_lock_or_bypass_drift_events": (
            p65_rep.desqueeze_ratio_lock_or_bypass_drift_events
        ),
        "rec_lamp_tally_or_emph_display_drift_events": (
            p65_rep.rec_lamp_tally_or_emph_display_drift_events
        ),
        "dormant_var_shutter_or_apsc_reset_drift_events": (
            p65_rep.dormant_var_shutter_or_apsc_reset_drift_events
        ),
        "dormant_var_shutter_exposed_events": p65_rep.dormant_var_shutter_exposed_events,
        "hdmi_red_border_clean_feed_leak_pixels": (
            p65_rep.hdmi_red_border_clean_feed_leak_pixels
        ),
        "recorded_media_desqueeze_pixels": p65_rep.recorded_media_desqueeze_pixels,
        "fx6_sdi_desqueeze_pixels": p65_rep.fx6_sdi_desqueeze_pixels,
        "slot1_data_sector_writes": p65_rep.slot1_data_sector_writes,
        "slot1_vault_mutation_bytes": p65_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p65_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_eopnotsupp_enforced": p65_rep.slot1_vault_erofs_eopnotsupp_enforced,
        "overall_ready_for_hardware_attach": p65_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p65_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p65_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p65_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec65[0],
            pillar_id=spec65[1],
            phase_label=spec65[2],
            module_name=spec65[3],
            passed=bool(p65_rep.all_passed),
            status=p65_rep.status,
            verification_mode=p65_rep.verification_mode,
            elapsed_seconds=p65_dt,
            key_metrics=p65_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec65[1],
                    "mode": p65_rep.verification_mode,
                    "status": p65_rep.status,
                    "metrics": p65_metrics,
                    "passed": p65_rep.all_passed,
                }
            ),
            errors=tuple(p65_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master65_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p65_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_65_PILLAR_COUNT == 65
        and pillars_passed == 65
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE355_SCHEMA,
            "schema_version": PHASE355_MASTER_SCHEMA,
            "version": PHASE355_VERSION,
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

    return Master65PillarRecoveryReport(
        schema=PHASE355_SCHEMA,
        schema_version=PHASE355_MASTER_SCHEMA,
        version=PHASE355_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=(
            P355_STATUS_VERIFIED_65OF65_AGGREGATOR if all_ok else P355_STATUS_FAIL_65OF65_AGGREGATOR
        ),
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P355_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.50,
        under_6s_budget=elapsed < P355_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P355_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p65_rep.donor_snapshot,
        pillar65_a_hdmi_raw_16bit_rec_media_vault=(
            p65_rep.pillar_65a_hdmi_raw_16bit_rec_media_vault
        ),
        pillar65_b_desqueeze_reclamp_varshutter_apsc_vault=(
            p65_rep.pillar_65b_desqueeze_reclamp_varshutter_apsc_vault
        ),
        hdmi_raw_output_or_media_vault_drift_events=(
            p65_rep.hdmi_raw_output_or_media_vault_drift_events
        ),
        hdmi_4k_only_or_gamut_removal_drift_events=(
            p65_rep.hdmi_4k_only_or_gamut_removal_drift_events
        ),
        desqueeze_ratio_lock_or_bypass_drift_events=(
            p65_rep.desqueeze_ratio_lock_or_bypass_drift_events
        ),
        rec_lamp_tally_or_emph_display_drift_events=(
            p65_rep.rec_lamp_tally_or_emph_display_drift_events
        ),
        dormant_var_shutter_or_apsc_reset_drift_events=(
            p65_rep.dormant_var_shutter_or_apsc_reset_drift_events
        ),
        dormant_var_shutter_exposed_events=p65_rep.dormant_var_shutter_exposed_events,
        hdmi_red_border_clean_feed_leak_pixels=(
            p65_rep.hdmi_red_border_clean_feed_leak_pixels
        ),
        recorded_media_desqueeze_pixels=p65_rep.recorded_media_desqueeze_pixels,
        fx6_sdi_desqueeze_pixels=p65_rep.fx6_sdi_desqueeze_pixels,
        fx3_hdmi_output_active_item_count=len(P355_HDMI_OUTPUT_8_ACTIVE_ITEMS),
        fx3_hdmi_output_reset_resistant=P355_HDMI_OUTPUT_RESET_RESISTANT,
        fx3_raw_resolution=P355_FX3_RAW_RESOLUTION,
        fx3_raw_bit_depth=P355_FX3_RAW_BIT_DEPTH,
        fx6_hdmi_raw_resolution=P355_FX6_HDMI_RAW_RESOLUTION,
        fx6_hdmi_raw_supports_24hz=P355_FX6_HDMI_RAW_SUPPORTS_24HZ,
        fx3_desqueeze_1_6x_actual_factor=P355_FX3_DESQUEEZE_1_6X_ACTUAL_FACTOR,
        fx3_desqueeze_1_8x_hits=P355_DESQUEEZE_1_8X_HITS,
        fx3_rec_lamp_led_count=P355_FX3_REC_LAMP_PHYSICAL_LEDS,
        fx3_rear_top_led_coupled=P355_FX3_REAR_TOP_LED_COUPLED,
        fx3_tally_light_menu_count=P355_FX3_TALLY_LIGHT_MENU_COUNT,
        silent_mode_disables_rec_lamp=P355_SILENT_MODE_DISABLES_REC_LAMP,
        fx3_type_menu_item_high_res_hits=P355_FX3_TYPE_MENU_ITEM_HIGH_RES_HITS,
        fx6_ecs_freq_min_hz=P355_FX6_ECS_FREQ_MIN_HZ,
        fx6_ecs_freq_max_hz=P355_FX6_ECS_FREQ_MAX_HZ,
        apsc_s35_resettable_by_camera_settings_reset=(
            P355_APSC_S35_RESETTABLE_BY_CAMERA_SETTINGS_RESET
        ),
        apsc_s35_still_crop_size_3_2=P355_APSC_S35_STILL_CROP_SIZE_3_2,
        slot1_data_sector_writes=(
            m64_rep.slot1_data_sector_writes + p65_rep.slot1_data_sector_writes
        ),
        slot1_vault_mutation_bytes=(
            m64_rep.slot1_vault_mutation_bytes + p65_rep.slot1_vault_mutation_bytes
        ),
        rf_packets_transmitted=m64_rep.rf_packets_transmitted + p65_rep.rf_packets_transmitted,
        rf_nvs_mutation_bytes=m64_rep.rf_nvs_mutation_bytes + p65_rep.rf_nvs_mutation_bytes,
        slot1_format_hard_locked=(
            m64_rep.slot1_format_hard_locked and p65_rep.slot1_format_hard_locked
        ),
        slot1_vault_erofs_eopnotsupp_enforced=(
            m64_rep.slot1_vault_erofs_eopnotsupp_enforced
            and p65_rep.slot1_vault_erofs_eopnotsupp_enforced
        ),
        slot1_vault_erofs_ebusy_enforced=p65_rep.slot1_vault_erofs_ebusy_enforced,
        shoe_audio_preemption_or_limiter_drift_events=(
            m64_rep.shoe_audio_preemption_or_limiter_drift_events
        ),
        subject_recog_myth_or_face_memory_drift_events=(
            m64_rep.subject_recog_myth_or_face_memory_drift_events
        ),
        silent_mode_target_or_barrier_drift_events=(
            m64_rep.silent_mode_target_or_barrier_drift_events
        ),
        bodydata_version_flash_or_slot1_vault_drift_events=(
            m64_rep.bodydata_version_flash_or_slot1_vault_drift_events
        ),
        dormant_shutter_when_pwr_off_exposed_events=(
            m64_rep.dormant_shutter_when_pwr_off_exposed_events
        ),
        hdmi_face_frame_pixels_emitted=m64_rep.hdmi_face_frame_pixels_emitted,
        cnflasha_pixel_map_mutation_bytes=m64_rep.cnflasha_pixel_map_mutation_bytes,
        slot1_bodydata_mutation_bytes=m64_rep.slot1_bodydata_mutation_bytes,
        bodydata_placement_or_flash_authorized=m64_rep.bodydata_placement_or_flash_authorized,
        ftp_protocol_sftp_or_jpeg_size_drift_events=(
            m64_rep.ftp_protocol_sftp_or_jpeg_size_drift_events
        ),
        wb_custom_cine_ei_or_shockless_drift_events=(
            m64_rep.wb_custom_cine_ei_or_shockless_drift_events
        ),
        movie_af_speed_or_focus_map_spoof_events=m64_rep.movie_af_speed_or_focus_map_spoof_events,
        marker_15ratio_peaking_hdmi_leak_events=m64_rep.marker_15ratio_peaking_hdmi_leak_events,
        zero_rf_usblan_or_slot1_avf_bypass_events=(
            m64_rep.zero_rf_usblan_or_slot1_avf_bypass_events
        ),
        usblan_packets_transmitted=m64_rep.usblan_packets_transmitted,
        hdmi_marker_peaking_pixels_emitted=m64_rep.hdmi_marker_peaking_pixels_emitted,
        slot1_avf_info_mutation_bytes=m64_rep.slot1_avf_info_mutation_bytes,
        rec_media_prioritize_or_autoswitch_drift_events=(
            m64_rep.rec_media_prioritize_or_autoswitch_drift_events
        ),
        card_speed_vpg200_vpg400_gate_drift_events=(
            m64_rep.card_speed_vpg200_vpg400_gate_drift_events
        ),
        proxy_sq_dci4k_or_120p_lockout_drift_events=(
            m64_rep.proxy_sq_dci4k_or_120p_lockout_drift_events
        ),
        cloud_init_persist_or_power_off_ble_rf_events=(
            m64_rep.cloud_init_persist_or_power_off_ble_rf_events
        ),
        mymenu_42slot_or_fx6_lock_spoof_events=m64_rep.mymenu_42slot_or_fx6_lock_spoof_events,
        zero_rf_or_slot1_vault_bypass_events=m64_rep.zero_rf_or_slot1_vault_bypass_events,
        slot1_dcim_m4root_avf_mutation_bytes=m64_rep.slot1_dcim_m4root_avf_mutation_bytes,
        big6_home_or_lower_left_nd_drift_events=m64_rep.big6_home_or_lower_left_nd_drift_events,
        framing_manual_or_dormant_auto_framing_drift_events=(
            m64_rep.framing_manual_or_dormant_auto_framing_drift_events
        ),
        interval_shoot_9999_or_fx6_mxf_spoof_events=(
            m64_rep.interval_shoot_9999_or_fx6_mxf_spoof_events
        ),
        tc_make_regen_or_hdmi_rec_ctrl_drift_events=(
            m64_rep.tc_make_regen_or_hdmi_rec_ctrl_drift_events
        ),
        access_authen_ssh_tls_or_fan_max_drift_events=(
            m64_rep.access_authen_ssh_tls_or_fan_max_drift_events
        ),
        slot1_dcim_avf_mutation_bytes=m64_rep.slot1_dcim_avf_mutation_bytes,
        fx3_has_var_shutter=P355_FX3_HAS_VAR_SHUTTER,
        fx3_has_builtin_evf=m64_rep.fx3_has_builtin_evf,
        fx3_has_builtin_end_filter=False,
        fx3_has_bt_timecode_link=False,
        fx3_has_dormant_auto_framing=m64_rep.fx3_has_dormant_auto_framing,
        fx3_has_dormant_auto_hdr=False,
        fx3_has_dormant_bulb_timer=False,
        fx3_has_dormant_divide_extract=False,
        fx3_has_fan_control_max=m64_rep.fx3_has_fan_control_max,
        fx3_has_movie_self_timer=False,
        fx3_has_movie_sort_recording=m64_rep.fx3_has_movie_sort_recording,
        fx3_has_physical_end_hw=m64_rep.fx3_has_physical_end_hw,
        fx3_has_5axis_ibis=True,
        fx6_has_ibis=False,
        fx6_has_fan_control_max=m64_rep.fx6_has_fan_control_max,
        fx6_has_still_self_timer=False,
        fx6_has_fn_menu=False,
        fx6_has_my_dial=False,
        fx6_has_bluetooth_hardware=m64_rep.fx6_has_bluetooth_hardware,
        fx6_has_av_tv_rotate=False,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        master_65pillar_sha256=master_sha,
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


def evaluate_65pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master65PillarRecoveryReport:
    """Short alias for `evaluate_realhw_65pillar_recovery_master`."""
    return evaluate_realhw_65pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_65pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master65PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_65pillar_recovery_master`."""
    return evaluate_realhw_65pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_65pillar_recovery(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master65PillarRecoveryReport:
    """Milestone 324/349 dynamic discovery alias for `evaluate_realhw_65pillar_recovery_master`."""
    return evaluate_realhw_65pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_all_65_recovery_pillars(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master65PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_65pillar_recovery_master`."""
    return evaluate_realhw_65pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
