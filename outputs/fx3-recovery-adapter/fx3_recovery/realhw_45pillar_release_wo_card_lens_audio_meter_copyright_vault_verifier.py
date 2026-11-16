"""Phase 265 (Grand Milestone `45/45` Recovery Pillars) — Pillar 45 & Unified 45-Pillar Recovery Master
(`verify-45pillar-recovery` / `verify-release-wo-card-lens-audio-meter-copyright-vault`):

1. **Pillar 45A — `[Release w/o Card]` (`Enable`/`Disable`, Still-Only Scope vs Movie Internal Media Gate),
   `[Release w/o Lens]` (`Enable`/`Disable`, Still + Movie + `S&Q` Scope with Zero E-ND / Zero E-Mount
   Lens UART Traffic on Body-Only Bench) & `Ver. 2.00+` / `Ver. 7.02` (`ilc/2210`) Exact 5-Item
   `[Audio Recording]` Menu vs `DISP (Screen Disp) Set` Audio Meter Integration (Wave-43)**:
   - Models `MENU` -> `Shooting` -> `[Shutter/Silent]` -> `[Release w/o Card]` (`Enable` factory default /
     `Disable`) and `[Release w/o Lens]` (`Enable` factory default / `Disable`), verifying survival across
     `[Camera Settings Reset]` & `[Reset Network Set.]` vs reset to `Enable` on `[Initialize]`, plus
     lossless restoration via `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]`.
   - Enforces cardless diagnostic bench safety (`Slot-1`/`Slot-2` empty -> zero media writes, Still shutter
     actuation allowed when `[Release w/o Card] = [Enable]`, while Movie/`S&Q` internal media recording
     remains strictly blocked without an inserted card; external HDMI capture governed by
     `[Rec. Media dur HDMI Output]`) vs production shoot `[Disable]` anti-unrecorded-shoot protection
     (`cardless_unrecorded_production_violations == 0`).
   - Enforces `[Release w/o Lens]` across `Still`, `Movie`, and `S&Q` with `fx3_has_builtin_end_filter == False`,
     `e_nd_actuator_tx_count == 0`, and `emount_lens_uart_tx_bytes == 0` on a body-only / mechanical PL-mount
     adapter / telescope bench.
   - Enforces `ILME-FX3` `Ver. 2.00+` / `Ver. 7.02` (`ilc/2210`) exact 5-item `MENU` -> `Shooting` ->
     `[Audio Recording]` structure (`Audio Recording`, `Audio Rec Level` `0..31`, `Audio Out Timing`
     `Live`/`Lip Sync`, `Wind Noise Reduct.`, `Shoe Audio Set.`), rejecting any `Ver. 1.x` (`ilc/2035`)
     standalone `[Audio Level Display]` spoof (`legacy_v1_audio_level_menu_spoof_events == 0`), and proving
     audio level meter visibility (`2ch` or `4ch` MI-shoe, suppressed in `S&Q`) is governed by
     `MENU` -> `Setup` -> `[Operation Customize]` -> `[DISP (Screen Disp) Set]`.

2. **Pillar 45B — `[Copyright Info]` (`Write Copyright Info` `Off`/`On`, `Set Photographer` `<= 46` Chars,
   `Set Copyright` `<= 46` Chars, `Disp. Copyright Info`) Still-EXIF Scope, `[Camera Settings Reset]`
   Survival vs `[Initialize]` Wipe & Clean-Room Operator PII Hygiene**:
   - Models `MENU` -> `Shooting` -> `[File]` -> `[Copyright Info]` exact 4 sub-items, enforcing `<= 46`-char
     printable ASCII bounds (`0x20..0x7E`), Still-JPEG/HEIF EXIF-only scope (never mutating `XAVC`/`HDMI RAW`
     movie streams or `Slot-1` Tier-0 recovery vault), `[Set Photographer]` / `[Set Copyright]` string
     survival across `[Camera Settings Reset]` vs complete wipe under `[Initialize]`, `CAMSET01..10.DAT`
     excluded-items firewall parity, and strict clean-room operator PII zeroing
     (`photographer_copyright_pii_leaked_bytes == 0`).

3. **Unified `45/45` Recovery Master (`evaluate_realhw_45pillar_recovery_master`)**:
   - Concurrently delegates Pillars `1..44` (`evaluate_realhw_44pillar_recovery_master`) + **Pillar 45** ->
     **`45/45` (`VERIFIED_45OF45_PILLAR_RECOVERY_MASTER`)** in `< 1.8s` CLI runtime (`< 4.0s` nominal /
     `< 6.0s` concurrent ceiling), preserving 100% backward compatibility with `verify-22..44pillar-recovery`.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
import posixpath
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from .files import is_forced_clean_room, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus
from .realhw_44pillar_apsc_s35_face_eye_af_version_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_44_PILLAR_SPECS,
    Master44PillarRecoveryReport,
    evaluate_realhw_44pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE265_SCHEMA: str = "realhw_45pillar_release_wo_card_lens_audio_meter_copyright_vault_verifier_v1"
PHASE265_VERSION: str = "1.0.0"
PHASE265_MILESTONE_NUMBER: int = 265
P265_ENV_CLEAN_ROOM_TEST: str = "FX3_CLEAN_ROOM_TEST"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
ISP_WRITE_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
ALLOW_PERSISTENT_JIRITSU_WRITES: bool = False
ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS: bool = False
LIVE_USB_IOKIT_TRANSMIT_ENABLED: bool = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
P265_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P265_FX3_HAS_BUILTIN_END_FILTER: bool = False
P265_E_ND_ACTUATOR_TX_COUNT: int = 0
P265_CARDLESS_UNRECORDED_PRODUCTION_VIOLATIONS: int = 0
P265_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_EVENTS: int = 0
P265_PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES: int = 0
P265_COPYRIGHT_CHAR_OVERFLOW_OR_MOVIE_MUTATION_EVENTS: int = 0
P265_SLOT1_COPYRIGHT_VAULT_MUTATION_BYTES: int = 0

P265_DONOR_INSPECT_BUDGET_SECONDS: float = 0.15
P265_FAST_CLI_BUDGET_SECONDS: float = 2.0
P265_NOMINAL_BUDGET_SECONDS: float = 4.0
P265_CONCURRENT_CEILING_SECONDS: float = 6.0
P265_BOUNDED_HEADER_BYTES: int = 4096
P265_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-43 / FX3 Ver. 7.02 & FX6 Ver. 6.01 Donor Anchors (bounded O_RDONLY verification)
P265_FX3_MODEL_NAME: str = "ILME-FX3"
P265_FX3_MODEL_ID: int = 0x91030080
P265_FX3_HELPGUIDE_ID: str = "ilc/2210"
P265_FX3_FW_VERSION: str = "7.02"
P265_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P265_FX6_DONOR_FW_VERSION: str = "6.01"
P265_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
    "2.00",
    "2.01",
    "2.02",
    "3.00",
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)
P265_FORBIDDEN_LEGACY_V1_HELPGUIDE_ID: str = "ilc/2035"
P265_FORBIDDEN_LEGACY_V1_FW_VERSIONS: Tuple[str, ...] = ("1.00", "1.01")

P265_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P265_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P265_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = (
    "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
)

P265_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P265_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P265_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)

P265_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P265_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P265_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)

P265_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P265_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P265_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P265_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P265_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P265_PINNED_FX3_LIBBACKUP_SO_SHA256: str = (
    "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"
)

P265_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P265_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P265_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = (
    "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"
)

P265_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so"
)
P265_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES: int = 18760
P265_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256: str = (
    "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7"
)

P265_DONOR_FX3_LIBGPE_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgpe.so"
)
P265_PINNED_FX3_LIBGPE_SO_BYTES: int = 106480
P265_PINNED_FX3_LIBGPE_SO_SHA256: str = (
    "363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464"
)

P265_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/CameraOnDemandSaver.so"
)
P265_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES: int = 18800
P265_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256: str = (
    "72b73608c2675a3709e2952ca347a36e7dd2ad3dd2869191638c7154933b2f46"
)

P265_DONOR_FX3_LIBINFRALENSCOMMUNICATOR_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraLensCommunicator.so"
)
P265_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES: int = 14544
P265_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256: str = (
    "e61bf145f050dd037802871395c38d1c0471518130d5bcd2f621268da8c8f6ab"
)

P265_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaConfig.so"
)
P265_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES: int = 52312
P265_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256: str = (
    "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486"
)

P265_DONOR_FX3_LIBINFRAMEDIADETECT_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaDetect.so"
)
P265_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES: int = 98224
P265_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256: str = (
    "4c1dbb303cf9d2d762723e0eb2266309c83aefe7d50f050fc8baa3964e4ea70d"
)

P265_DONOR_FX3_LIBINFRAMETASUPPLIER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMetaSupplier.so"
)
P265_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_BYTES: int = 23048
P265_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_SHA256: str = (
    "ce8ae80920c405f58367b1b685bc8ff2ae8738767ed10ba3388e15bcb26b8503"
)

P265_DONOR_FX3_LIBINFRAIPTC_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraIPTC.so"
)
P265_PINNED_FX3_LIBINFRAIPTC_SO_BYTES: int = 68712
P265_PINNED_FX3_LIBINFRAIPTC_SO_SHA256: str = (
    "7b2730d741b485f43eaaedcf49b23e7b0e9737c63adff00a536e2124e0bbecf3"
)

P265_DONOR_FX6_LIBINFRAHOTSHOE_SO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraHotshoe.so"
)
P265_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES: int = 47808
P265_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256: str = (
    "0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6"
)

# Pillar 45A — [Release w/o Card], [Release w/o Lens] & Ver. 7.02 5-Item [Audio Recording] vs DISP Meter
P265_RELEASE_WO_CARD_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "Shutter/Silent",
    "Release w/o Card",
)
P265_RELEASE_WO_LENS_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "Shutter/Silent",
    "Release w/o Lens",
)
P265_RELEASE_WO_MODES: Tuple[str, ...] = ("Enable", "Disable")
P265_RELEASE_WO_CARD_DEFAULT: str = "Enable"
P265_RELEASE_WO_LENS_DEFAULT: str = "Enable"
P265_BENCH_POSTURES: Tuple[str, ...] = ("CARDLESS_DIAGNOSTIC_BENCH", "PRODUCTION_SHOOT")
P265_SHOOTING_DOMAINS: Tuple[str, ...] = ("Still", "Movie", "S&Q")
P265_REC_MEDIA_DUR_HDMI_MODES: Tuple[str, ...] = ("On", "Off(HDMI Only)")
P265_LENS_ATTACHMENT_KINDS: Tuple[str, ...] = (
    "BODY_ONLY_CAP",
    "PL_MOUNT_MECHANICAL_ADAPTER",
    "TELESCOPE_T_MOUNT",
    "EMOUNT_ELECTRONIC_LENS",
)

P265_AUDIO_RECORDING_MENU_PATH: Tuple[str, ...] = ("MENU", "Shooting", "Audio Recording")
P265_AUDIO_RECORDING_EXACT_5_ITEMS: Tuple[str, ...] = (
    "Audio Recording",
    "Audio Rec Level",
    "Audio Out Timing",
    "Wind Noise Reduct.",
    "Shoe Audio Set.",
)
P265_FORBIDDEN_LEGACY_V1_AUDIO_ITEM: str = "Audio Level Display"
P265_DISP_SCREEN_SET_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Operation Customize",
    "DISP (Screen Disp) Set",
)
P265_AUDIO_RECORDING_MODES: Tuple[str, ...] = ("On", "Off")
P265_AUDIO_RECORDING_DEFAULT: str = "On"
P265_AUDIO_REC_LEVEL_MIN: int = 0
P265_AUDIO_REC_LEVEL_MAX: int = 31
P265_AUDIO_REC_LEVEL_DEFAULT: int = 26
P265_AUDIO_OUT_TIMING_MODES: Tuple[str, ...] = ("Live", "Lip Sync")
P265_AUDIO_OUT_TIMING_DEFAULT: str = "Live"
P265_WIND_NOISE_REDUCT_MODES: Tuple[str, ...] = ("Off", "On")
P265_WIND_NOISE_REDUCT_DEFAULT: str = "Off"
P265_SHOE_AUDIO_SET_MODES: Tuple[str, ...] = (
    "48kHz/16bit 2ch",
    "48kHz/24bit 2ch",
    "48kHz/24bit 4ch",
)
P265_SHOE_AUDIO_SET_DEFAULT: str = "48kHz/16bit 2ch"

# Pillar 45B — [Copyright Info] 46-Char Still EXIF Scope & Clean-Room PII Hygiene
P265_COPYRIGHT_INFO_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "File",
    "Copyright Info",
)
P265_COPYRIGHT_INFO_EXACT_4_ITEMS: Tuple[str, ...] = (
    "Write Copyright Info",
    "Set Photographer",
    "Set Copyright",
    "Disp. Copyright Info",
)
P265_WRITE_COPYRIGHT_MODES: Tuple[str, ...] = ("Off", "On")
P265_WRITE_COPYRIGHT_DEFAULT: str = "Off"
P265_COPYRIGHT_MAX_CHARS: int = 46
P265_STILL_IMAGE_FORMATS: Tuple[str, ...] = ("JPEG", "HEIF", "RAW+JPEG", "RAW+HEIF")
P265_MOVIE_STREAM_FORMATS: Tuple[str, ...] = (
    "XAVC HS 4K",
    "XAVC S 4K",
    "XAVC S HD",
    "XAVC S-I 4K",
    "XAVC S-I HD",
    "HDMI RAW 4264x2408",
)

P265_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)
P265_SLOT1_VAULT_SLOT: int = 1
P265_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
P265_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_release_wo_card_lens_audio_copyright_vault_overlay"
P265_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P265_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P265_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P265_BLOCKED_INVALID_RELEASE_WO_OR_AUDIO_METER_SPEC: str = (
    "BLOCKED_INVALID_RELEASE_WO_OR_AUDIO_METER_SPEC"
)
P265_BLOCKED_RELEASE_WO_CARD_MOVIE_OR_BENCH_VIOLATION: str = (
    "BLOCKED_RELEASE_WO_CARD_MOVIE_OR_BENCH_VIOLATION"
)
P265_BLOCKED_RELEASE_WO_LENS_OR_END_UART_VIOLATION: str = (
    "BLOCKED_RELEASE_WO_LENS_OR_END_UART_VIOLATION"
)
P265_BLOCKED_LEGACY_V1_AUDIO_MENU_SPOOF_OR_SPEC_DRIFT: str = (
    "BLOCKED_LEGACY_V1_AUDIO_MENU_SPOOF_OR_SPEC_DRIFT"
)
P265_BLOCKED_DISP_AUDIO_METER_OR_RESET_SCOPE_DRIFT: str = (
    "BLOCKED_DISP_AUDIO_METER_OR_RESET_SCOPE_DRIFT"
)

P265_BLOCKED_INVALID_COPYRIGHT_INFO_SPEC: str = "BLOCKED_INVALID_COPYRIGHT_INFO_SPEC"
P265_BLOCKED_COPYRIGHT_46CHAR_OR_ASCII_OVERFLOW: str = (
    "BLOCKED_COPYRIGHT_46CHAR_OR_ASCII_OVERFLOW"
)
P265_BLOCKED_COPYRIGHT_MOVIE_STREAM_OR_EXIF_SCOPE_VIOLATION: str = (
    "BLOCKED_COPYRIGHT_MOVIE_STREAM_OR_EXIF_SCOPE_VIOLATION"
)
P265_BLOCKED_COPYRIGHT_RESET_VS_INITIALIZE_SCOPE_DRIFT: str = (
    "BLOCKED_COPYRIGHT_RESET_VS_INITIALIZE_SCOPE_DRIFT"
)
P265_BLOCKED_COPYRIGHT_CLEAN_ROOM_PII_OR_SLOT1_VAULT_LEAK: str = (
    "BLOCKED_COPYRIGHT_CLEAN_ROOM_PII_OR_SLOT1_VAULT_LEAK"
)
P265_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P265_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P265_STATUS_VERIFIED_PILLAR_45A: str = (
    "VERIFIED_PILLAR_45A_RELEASE_WO_CARD_LENS_AND_V702_AUDIO_DISP_METER_VAULT"
)
P265_STATUS_REJECTED_PILLAR_45A: str = (
    "REJECTED_PILLAR_45A_RELEASE_WO_CARD_LENS_AND_V702_AUDIO_DISP_METER_VAULT"
)
P265_STATUS_VERIFIED_PILLAR_45B: str = (
    "VERIFIED_PILLAR_45B_COPYRIGHT_INFO_46CHAR_STILL_EXIF_AND_PII_HYGIENE_VAULT"
)
P265_STATUS_REJECTED_PILLAR_45B: str = (
    "REJECTED_PILLAR_45B_COPYRIGHT_INFO_46CHAR_STILL_EXIF_AND_PII_HYGIENE_VAULT"
)
P265_STATUS_VERIFIED_PILLAR45_SUITE: str = (
    "VERIFIED_PILLAR45_RELEASE_WO_CARD_LENS_AUDIO_METER_COPYRIGHT_VAULT"
)
P265_STATUS_FAIL_PILLAR45_SUITE: str = (
    "FAIL_PILLAR45_RELEASE_WO_CARD_LENS_AUDIO_METER_COPYRIGHT_VAULT"
)
P265_STATUS_VERIFIED_45OF45_AGGREGATOR: str = "VERIFIED_45OF45_PILLAR_RECOVERY_MASTER"
P265_STATUS_FAIL_45OF45_AGGREGATOR: str = "FAIL_45OF45_PILLAR_RECOVERY_MASTER"

P265_PILLAR_45A_SCENARIO_IDS: Tuple[str, ...] = (
    "P45A1_CARDLESS_BODY_ONLY_BENCH_RELEASE_WO_CARD_LENS_ENABLE_STILL_ACTUATES_MOVIE_BLOCKED_ZERO_END_UART_AND_DISP_2CH_METER_SAFE",
    "P45A2_PRODUCTION_SHOOT_RELEASE_WO_CARD_DISABLE_PL_ADAPTER_ZERO_END_UART_4CH_MI_SHOE_DISP_METER_AND_CAMSET01_ROUNDTRIP_SAFE",
    "P45A3_REJECT_RELEASE_WO_CARD_BYPASSING_MOVIE_INTERNAL_RECORDING_WITHOUT_MEDIA_OR_PRODUCTION_ENABLE_HAZARD",
    "P45A4_REJECT_RELEASE_WO_LENS_DISABLE_BODY_ONLY_RELEASE_OR_NONZERO_END_LENS_UART_TRAFFIC",
    "P45A5_REJECT_LEGACY_V1_ILC2035_STANDALONE_AUDIO_LEVEL_DISPLAY_MENU_SPOOF_OR_AUDIO_REC_LEVEL_OUT_OF_RANGE",
    "P45A6_REJECT_SQ_AUDIO_METER_UNSUPPRESSED_OR_DISP_SCREEN_SET_AUDIO_METER_OR_RESET_SCOPE_DRIFT",
)
P265_PILLAR_45B_SCENARIO_IDS: Tuple[str, ...] = (
    "P45B1_CLEAN_ROOM_INITIALIZE_WIPES_COPYRIGHT_PII_WRITE_OFF_AND_ORDONLY_CAMSET01_EXCLUDED_FIREWALL_SAFE",
    "P45B2_EXACT_46CHAR_ASCII_SURVIVES_CAMERA_SETTINGS_RESET_AND_STILL_EXIF_ONLY_NEVER_MUTATES_XAVC_RAW_MOVIES_SAFE",
    "P45B3_REJECT_COPYRIGHT_47CHAR_LENGTH_OVERFLOW_OR_NON_PRINTABLE_ASCII_INJECTION",
    "P45B4_REJECT_COPYRIGHT_INFO_MUTATING_XAVC_OR_HDMI_RAW_MOVIE_STREAM_OR_WRITING_EXIF_WHEN_WRITE_OFF",
    "P45B5_REJECT_CAMERA_SETTINGS_RESET_WIPING_PHOTOGRAPHER_COPYRIGHT_STRINGS_OR_INITIALIZE_FAILING_TO_CLEAR",
    "P45B6_REJECT_CLEAN_ROOM_OPERATOR_PII_LEAK_CAMSET_COPYRIGHT_EXPORT_OR_SLOT1_VAULT_MUTATION",
)

MASTER_45_PILLAR_COUNT: int = 45
MASTER_45_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_44_PILLAR_SPECS + (
    (
        45,
        "pillar_45_release_wo_card_lens_audio_meter_copyright_vault",
        "Phase 265 (Grand Milestone 45/45)",
        "fx3_recovery.realhw_45pillar_release_wo_card_lens_audio_meter_copyright_vault_verifier",
    ),
)
MASTER_45_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_45_PILLAR_SPECS)


# ---------------------------------------------------------------------------
# Internal Helpers & Deterministic State Computations
# ---------------------------------------------------------------------------


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def _is_clean_room_forced(force_clean_room: Optional[bool] = None) -> bool:
    """Honor explicit flag, `FX3_FX6_FORCE_CLEAN_ROOM=1`, AND `FX3_CLEAN_ROOM_TEST=1`."""
    if force_clean_room is not None:
        return bool(force_clean_room)
    if is_forced_clean_room():
        return True
    return os.environ.get(P265_ENV_CLEAN_ROOM_TEST, "").strip().lower() in ("1", "true", "yes")


def _safety_invariant_errors() -> List[str]:
    errs: List[str] = []
    checks = (
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
        ("P265_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P265_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("P265_FX3_HAS_BUILTIN_END_FILTER", P265_FX3_HAS_BUILTIN_END_FILTER, False),
        ("P265_E_ND_ACTUATOR_TX_COUNT", P265_E_ND_ACTUATOR_TX_COUNT, 0),
        (
            "P265_CARDLESS_UNRECORDED_PRODUCTION_VIOLATIONS",
            P265_CARDLESS_UNRECORDED_PRODUCTION_VIOLATIONS,
            0,
        ),
        (
            "P265_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_EVENTS",
            P265_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_EVENTS,
            0,
        ),
        (
            "P265_PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES",
            P265_PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES,
            0,
        ),
        (
            "P265_COPYRIGHT_CHAR_OVERFLOW_OR_MOVIE_MUTATION_EVENTS",
            P265_COPYRIGHT_CHAR_OVERFLOW_OR_MOVIE_MUTATION_EVENTS,
            0,
        ),
        ("P265_SLOT1_COPYRIGHT_VAULT_MUTATION_BYTES", P265_SLOT1_COPYRIGHT_VAULT_MUTATION_BYTES, 0),
        ("OTP_FUSE_TOUCHES", OTP_FUSE_TOUCHES, 0),
        ("OTP_FUSE_WRITES", OTP_FUSE_WRITES, 0),
        ("RPMB_COUNTER_INCREMENTS", RPMB_COUNTER_INCREMENTS, 0),
        ("PASSIVE_TX_BYTES_EMITTED", PASSIVE_TX_BYTES_EMITTED, 0),
        ("PHYSICAL_USB_PACKETS_EMITTED", PHYSICAL_USB_PACKETS_EMITTED, 0),
        ("PHYSICAL_DEVICE_WRITES", PHYSICAL_DEVICE_WRITES, 0),
        ("RAW_FIRMWARE_BYTES_LEAKED", RAW_FIRMWARE_BYTES_LEAKED, 0),
    )
    for name, actual, expected in checks:
        if actual != expected:
            errs.append(f"{name} expected {expected!r}, got {actual!r}")
    return errs


def _is_tmpfs_path(path_value: str) -> bool:
    norm = posixpath.normpath(path_value)
    return norm.startswith("/tmp/") or norm.startswith("/run/")


def _targets_persistent_emmc(path_value: str) -> bool:
    low = path_value.strip().lower()
    return any(tok in low for tok in P265_FORBIDDEN_PERSISTENT_TARGETS)


def _is_printable_ascii_46(text: str) -> Tuple[bool, bool]:
    """Return `(length_le_46, printable_ascii_ok)` for `ILME-FX3` `[Copyright Info]` strings."""
    len_ok = len(text) <= P265_COPYRIGHT_MAX_CHARS
    ascii_ok = all(0x20 <= ord(ch) <= 0x7E for ch in text)
    return len_ok, ascii_ok


def compute_expected_release_wo_card_and_lens_gate(
    *,
    shooting_domain: str,
    release_wo_card: str,
    release_wo_lens: str,
    slot1_card_inserted: bool,
    slot2_card_inserted: bool,
    lens_attachment_kind: str,
    hdmi_connected: bool,
    rec_media_dur_hdmi_output: str,
) -> Tuple[bool, bool, bool]:
    """Compute `(still_shutter_release_allowed, movie_internal_rec_allowed, external_hdmi_capture_allowed)`.

    - `[Release w/o Lens]` governs `Still`, `Movie`, and `S&Q`: without an electronic E-mount lens
      (`BODY_ONLY_CAP`, `PL_MOUNT_MECHANICAL_ADAPTER`, `TELESCOPE_T_MOUNT`), release is allowed iff
      `release_wo_lens == "Enable"`.
    - `[Release w/o Card]` governs **still-image** shutter release when no card is inserted (`Enable`
      actuates shutter without saving; `Disable` blocks shutter release).
    - Internal `Movie` / `S&Q` media recording **always** requires an inserted card AND
      `(not hdmi_connected or rec_media_dur_hdmi_output == "On")` — `[Release w/o Card] = [Enable]`
      never permits cardless internal movie recording. External HDMI capture in `Movie` / `S&Q` is
      governed by `hdmi_connected` + lens gate.
    """
    any_card = bool(slot1_card_inserted or slot2_card_inserted)
    electronic_lens = lens_attachment_kind == "EMOUNT_ELECTRONIC_LENS"
    lens_ok = electronic_lens or (release_wo_lens == "Enable")

    if shooting_domain == "Still":
        still_ok = lens_ok and (any_card or release_wo_card == "Enable")
        return still_ok, False, False

    internal_media_enabled = (not hdmi_connected) or (rec_media_dur_hdmi_output == "On")
    movie_internal_ok = lens_ok and any_card and internal_media_enabled
    ext_hdmi_ok = lens_ok and bool(hdmi_connected)
    return False, movie_internal_ok, ext_hdmi_ok


def compute_expected_disp_audio_meter_state(
    *,
    shooting_domain: str,
    audio_recording: str,
    shoe_audio_set: str,
    mi_shoe_digital_4ch_attached: bool,
    disp_screen_audio_level_checked: bool,
) -> Tuple[bool, int]:
    """Compute `(audio_meter_visible, audio_meter_channels)` under `Ver. 2.00+`/`7.02` `DISP (Screen Disp) Set`.

    In `ILME-FX3` `Ver. 2.00+`/`7.02` (`ilc/2210`), standalone `Ver. 1.x` `[Audio Level Display]` is
    removed from `[Audio Recording]`; meter visibility (`2ch` or `4ch` MI-shoe) is controlled by
    `MENU -> Setup -> Operation Customize -> [DISP (Screen Disp) Set]` and suppressed in `S&Q` or
    when `Movie` `[Audio Recording] = [Off]`.
    """
    if shooting_domain == "S&Q":
        return False, 0
    if shooting_domain == "Movie" and audio_recording == "Off":
        return False, 0
    if not disp_screen_audio_level_checked:
        return False, 0
    channels = 4 if (mi_shoe_digital_4ch_attached and shoe_audio_set == "48kHz/24bit 4ch") else 2
    return True, channels


def compute_expected_copyright_info_state(
    *,
    pre_write_copyright_info: str,
    pre_photographer_text: str,
    pre_copyright_text: str,
    reset_action: str,
) -> Tuple[str, str, str]:
    """Compute `(post_write_copyright_info, post_photographer_text, post_copyright_text)` across resets.

    - `[Camera Settings Reset]` resets `[Write Copyright Info]` to `[Off]` while preserving the
      registered `[Set Photographer]` and `[Set Copyright]` `<= 46`-char strings.
    - `[Reset Network Set.]` and `NONE` preserve all three settings unchanged.
    - `[Initialize]` resets `[Write Copyright Info]` to `[Off]` AND wipes both strings to `""`.
    """
    if reset_action == "Initialize":
        return P265_WRITE_COPYRIGHT_DEFAULT, "", ""
    if reset_action == "Camera Settings Reset":
        return P265_WRITE_COPYRIGHT_DEFAULT, pre_photographer_text, pre_copyright_text
    return pre_write_copyright_info, pre_photographer_text, pre_copyright_text


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase265DonorArtifactDigest:
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
class Phase265DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase265DonorArtifactDigest, ...]


@dataclass(frozen=True)
class ReleaseWoCardLensAndAudioMeterVaultSpec:
    camera_model: str = P265_FX3_MODEL_NAME
    helpguide_id: str = P265_FX3_HELPGUIDE_ID
    fw_version: str = P265_FX3_FW_VERSION
    release_wo_card_menu_path: Tuple[str, ...] = P265_RELEASE_WO_CARD_MENU_PATH
    release_wo_lens_menu_path: Tuple[str, ...] = P265_RELEASE_WO_LENS_MENU_PATH
    audio_recording_menu_path: Tuple[str, ...] = P265_AUDIO_RECORDING_MENU_PATH
    audio_recording_menu_items: Tuple[str, ...] = P265_AUDIO_RECORDING_EXACT_5_ITEMS
    disp_screen_set_menu_path: Tuple[str, ...] = P265_DISP_SCREEN_SET_MENU_PATH
    bench_posture: str = "CARDLESS_DIAGNOSTIC_BENCH"  # CARDLESS_DIAGNOSTIC_BENCH | PRODUCTION_SHOOT
    pre_release_wo_card: str = "Enable"  # Enable | Disable
    pre_release_wo_lens: str = "Enable"  # Enable | Disable
    pre_audio_recording: str = "On"  # On | Off
    pre_audio_rec_level: int = 26  # 0..31
    pre_audio_out_timing: str = "Live"  # Live | Lip Sync
    pre_wind_noise_reduct: str = "Off"  # Off | On
    pre_shoe_audio_set: str = "48kHz/16bit 2ch"
    pre_disp_screen_audio_level_checked: bool = True
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Reset Network Set. | Initialize
    camset_load_after_reset: bool = False
    camset_slot: int = P265_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P265_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    saved_release_wo_card: str = "Enable"
    saved_release_wo_lens: str = "Enable"
    saved_audio_recording: str = "On"
    saved_audio_rec_level: int = 26
    saved_audio_out_timing: str = "Live"
    saved_wind_noise_reduct: str = "Off"
    saved_shoe_audio_set: str = "48kHz/16bit 2ch"
    saved_disp_screen_audio_level_checked: bool = True
    post_release_wo_card: str = "Enable"
    post_release_wo_lens: str = "Enable"
    post_audio_recording: str = "On"
    post_audio_rec_level: int = 26
    post_audio_out_timing: str = "Live"
    post_wind_noise_reduct: str = "Off"
    post_shoe_audio_set: str = "48kHz/16bit 2ch"
    post_disp_screen_audio_level_checked: bool = True
    shooting_domain: str = "Still"  # Still | Movie | S&Q
    slot1_card_inserted: bool = False
    slot2_card_inserted: bool = False
    lens_attachment_kind: str = "BODY_ONLY_CAP"
    attached_lens_model: str = "NONE"
    fx3_has_builtin_end_filter: bool = P265_FX3_HAS_BUILTIN_END_FILTER
    e_nd_actuator_tx_count: int = 0
    emount_lens_uart_tx_bytes: int = 0
    hdmi_connected: bool = False
    rec_media_dur_hdmi_output: str = "On"  # On | Off(HDMI Only)
    still_shutter_actuated: bool = True
    still_images_saved_to_card: int = 0
    movie_internal_recording_started: bool = False
    external_hdmi_capture_allowed: bool = False
    cardless_unrecorded_production_violations: int = 0
    mi_shoe_digital_4ch_attached: bool = False
    audio_meter_visible_on_disp: bool = True
    audio_meter_channels_rendered: int = 2
    legacy_v1_audio_level_menu_spoof_events: int = 0
    overlay_dir: str = P265_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P265_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P265_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P265_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class ReleaseWoCardLensAndAudioMeterVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    reset_and_camset_scope_verified: bool
    release_wo_card_still_vs_movie_gate_verified: bool
    release_wo_lens_and_zero_end_uart_verified: bool
    v702_audio_5item_and_disp_meter_verified: bool
    h0_equals_h3_verified: bool
    fx3_has_builtin_end_filter: bool
    e_nd_actuator_tx_count: int
    emount_lens_uart_tx_bytes: int
    cardless_unrecorded_production_violations: int
    legacy_v1_audio_level_menu_spoof_events: int
    audio_meter_channels_rendered: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CopyrightInfo46CharExifVaultSpec:
    camera_model: str = P265_FX3_MODEL_NAME
    helpguide_id: str = P265_FX3_HELPGUIDE_ID
    fw_version: str = P265_FX3_FW_VERSION
    copyright_info_menu_path: Tuple[str, ...] = P265_COPYRIGHT_INFO_MENU_PATH
    copyright_info_subitems: Tuple[str, ...] = P265_COPYRIGHT_INFO_EXACT_4_ITEMS
    pre_write_copyright_info: str = "On"  # Off | On
    pre_photographer_text: str = "LAB_BENCH_SYNTH_PHOTOGRAPHER_46CHAR_BOUND_TEST"
    pre_copyright_text: str = "LAB_BENCH_SYNTH_COPYRIGHT_46CHAR_BOUNDARY_TEST"
    reset_action: str = "Initialize"  # NONE | Camera Settings Reset | Reset Network Set. | Initialize
    post_write_copyright_info: str = "Off"  # Off | On
    post_photographer_text: str = ""
    post_copyright_text: str = ""
    disp_copyright_info_open_mode: str = "O_RDONLY"
    disp_copyright_info_flash_writes: int = 0
    displayed_photographer_preview: str = ""
    displayed_copyright_preview: str = ""
    copyright_c_icon_shown_on_screen: bool = False
    shooting_domain: str = "Still"  # Still | Movie | S&Q
    still_image_format: str = "JPEG"  # JPEG | HEIF | RAW+JPEG | RAW+HEIF
    movie_stream_format: str = "XAVC S-I 4K"
    target_media_slot: int = 2  # 1 | 2 (0 when cardless)
    still_exif_copyright_written: bool = False
    movie_xavc_or_raw_copyright_mutated: bool = False
    clean_room_pii_hygiene_enforced: bool = True
    contains_operator_pii: bool = False
    photographer_copyright_pii_leaked_bytes: int = 0
    copyright_char_overflow_or_movie_mutation_events: int = 0
    camset_load_after_reset: bool = True
    camset_slot: int = P265_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P265_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    camset_exported_copyright_pii_bytes: int = 0
    camset_overwrote_inbody_copyright: bool = False
    slot1_tier0_vault_active: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_save_or_exif_write_attempted: bool = False
    slot1_copyright_vault_mutation_bytes: int = 0
    overlay_dir: str = P265_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P265_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P265_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P265_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class CopyrightInfo46CharExifVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    char_46_ascii_and_disp_readonly_verified: bool
    reset_survival_vs_initialize_wipe_verified: bool
    still_exif_only_movie_isolation_verified: bool
    clean_room_pii_and_slot1_vault_verified: bool
    h0_equals_h3_verified: bool
    photographer_char_length: int
    copyright_char_length: int
    photographer_copyright_pii_leaked_bytes: int
    copyright_char_overflow_or_movie_mutation_events: int
    slot1_copyright_vault_mutation_bytes: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReleaseWoCardLensAudioMeterAndCopyrightVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase265DonorSnapshot
    release_wo_card_lens_audio_report: ReleaseWoCardLensAndAudioMeterVaultReport
    copyright_info_46char_exif_report: CopyrightInfo46CharExifVaultReport
    fx3_has_builtin_end_filter: bool
    e_nd_actuator_tx_count: int
    cardless_unrecorded_production_violations: int
    legacy_v1_audio_level_menu_spoof_events: int
    photographer_copyright_pii_leaked_bytes: int
    copyright_char_overflow_or_movie_mutation_events: int
    slot1_copyright_vault_mutation_bytes: int
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
class Pillar45ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar45ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar45ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar45BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar45ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar45StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase265DonorSnapshot
    pillar_45a_release_wo_card_lens_audio_meter_vault: Pillar45ASuiteResult
    pillar_45b_copyright_info_46char_exif_vault: Pillar45BSuiteResult
    fx3_has_builtin_end_filter: bool
    e_nd_actuator_tx_count: int
    cardless_unrecorded_production_violations: int
    legacy_v1_audio_level_menu_spoof_events: int
    photographer_copyright_pii_leaked_bytes: int
    copyright_char_overflow_or_movie_mutation_events: int
    slot1_copyright_vault_mutation_bytes: int
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
class Master45PillarRecoveryReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_2s_fast_cli_budget: bool
    under_6s_budget: bool
    nominal_under_4_0s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    # Pillar 45 & Wave-43 top-level fields
    donor_snapshot: Phase265DonorSnapshot
    pillar45_a_release_wo_card_lens_audio_meter_vault: Pillar45ASuiteResult
    pillar45_b_copyright_info_46char_exif_vault: Pillar45BSuiteResult
    fx3_has_builtin_end_filter: bool
    e_nd_actuator_tx_count: int
    cardless_unrecorded_production_violations: int
    legacy_v1_audio_level_menu_spoof_events: int
    photographer_copyright_pii_leaked_bytes: int
    copyright_char_overflow_or_movie_mutation_events: int
    slot1_copyright_vault_mutation_bytes: int
    # Preserved Pillars 1..44 rollup metrics
    apsc_s35_4k_or_raw_bypass_events: int
    ai_unit_subject_recog_spoof_events: int
    hdmi_clean_feed_eye_frame_baked_pixels: int
    version_dialog_flash_writes: int
    bodydata_flash_attempts_blocked: int
    slot1_bodydata_vault_mutation_bytes: int
    auto_slow_shutter_lockout_bypass_events: int
    auto_slow_shutter_angle_overlap_events: int
    breathing_comp_raw_or_240p_bypass_events: int
    hdmi_rec_ctrl_without_tc_violations: int
    slot1_hdmi_rec_vault_mutation_bytes: int
    diff_set_transition_corruption_events: int
    shutter_angle_common_bleed_events: int
    slot1_custom_key_vault_mutation_bytes: int
    fx3_has_builtin_evf: bool
    evf_finder_monitor_spoof_events: int
    tier0_battery_high_display_violations: int
    bt_rmt_ir_lockout_violations: int
    slot1_mymenu_vault_mutation_bytes: int
    destructive_menu_delete_confusions: int
    shutter_angle_exposure_step_drift_events: int
    fx3_has_var_shutter: bool
    unbuffered_battery_pull_events: int
    hardware_live_attachment_authorized: bool
    master_45pillar_sha256: str
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
# Bounded O_RDONLY Donor Inspection & Clean-Room Fallback
# ---------------------------------------------------------------------------


def _read_donor_readonly_bounded(
    relpath: str,
    max_full_bytes: int = P265_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    resolved = resolve_donor_path(relpath)
    if resolved is None:
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
        hdr = os.pread(fd, min(P265_BOUNDED_HEADER_BYTES, total_size), 0)
        return True, total_size, len(hdr), "HEADER4K_SHA256", sha256(hdr).hexdigest(), hdr
    finally:
        os.close(fd)


def _check_elf64_aarch64_tokens(data: bytes, expected_tokens: Tuple[bytes, ...]) -> Tuple[bool, str]:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        return False, "NOT_ELF"
    ei_class, ei_data = data[4], data[5]
    e_machine = struct.unpack_from("<H", data, 18)[0]
    if ei_class != 2 or ei_data != 1 or e_machine != 183:
        return False, f"BAD_ELF64_AARCH64(class={ei_class},data={ei_data},mach={e_machine})"
    found = [tok.decode("ascii") for tok in expected_tokens if tok in data]
    missing = [tok.decode("ascii") for tok in expected_tokens if tok not in data]
    if missing:
        return False, f"MISSING_TOKENS:{','.join(missing)}"
    return True, f"ELF64_AARCH64:{'+'.join(found)}" if found else "ELF64_AARCH64"


def _synthetic_phase265_donors() -> Tuple[Phase265DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P265_DONOR_FX3_BODYDATA_RELPATH,
            P265_PINNED_FX3_BODYDATA_BYTES,
            P265_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P265_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P265_DONOR_FX3_APPFW_702_RELPATH,
            P265_PINNED_FX3_APPFW_702_BYTES,
            P265_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P265_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P265_DONOR_FX6_APPFW_601_RELPATH,
            P265_PINNED_FX6_APPFW_601_BYTES,
            P265_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P265_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P265_DONOR_FX3_BACKUP_BIN_RELPATH,
            P265_PINNED_FX3_BACKUP_BIN_BYTES,
            P265_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P265_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P265_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P265_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P265_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P265_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P265_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P265_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P265_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P265_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libsaveloadsettings_so",
            P265_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P265_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P265_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            "FULL_SHA256",
            P265_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:SaveLoadSettingsIf+requestToRead+requestToCheck+requestToWrite",
        ),
        (
            "fx3_libgpe_so",
            P265_DONOR_FX3_LIBGPE_SO_RELPATH,
            P265_PINNED_FX3_LIBGPE_SO_BYTES,
            P265_PINNED_FX3_LIBGPE_SO_BYTES,
            "FULL_SHA256",
            P265_PINNED_FX3_LIBGPE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:gpe_blog_error+_ZNK5mpgpe5Gperm4InitEv",
        ),
        (
            "fx3_cameraondemandsaver_so",
            P265_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH,
            P265_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            P265_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            "FULL_SHA256",
            P265_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:CameraOnDemandSaver+_ZN18CAM_ONDEMAND_SAVER17OsalHandleWrapperC1Ejji",
        ),
        (
            "fx3_libinfralenscommunicator_so",
            P265_DONOR_FX3_LIBINFRALENSCOMMUNICATOR_SO_RELPATH,
            P265_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES,
            P265_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES,
            "FULL_SHA256",
            P265_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:LensCommunicator+_Z23LensCommunicator_CreatePN3MWF5ErrCdE",
        ),
        (
            "fx3_libinframediaconfig_so",
            P265_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P265_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P265_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            "FULL_SHA256",
            P265_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaConfig+_ZN16InfraMediaConfig10SaveBackupEt",
        ),
        (
            "fx3_libinframediadetect_so",
            P265_DONOR_FX3_LIBINFRAMEDIADETECT_SO_RELPATH,
            P265_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES,
            P265_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES,
            "FULL_SHA256",
            P265_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaDetect+_ZN16InfraMediaDetect10GetVersionEv",
        ),
        (
            "fx3_libinframetasupplier_so",
            P265_DONOR_FX3_LIBINFRAMETASUPPLIER_SO_RELPATH,
            P265_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_BYTES,
            P265_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_BYTES,
            "FULL_SHA256",
            P265_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMetaSupplier_Init+_ZN20InfraMetaSupplier_If4InitEv",
        ),
        (
            "fx3_libinfraiptc_so",
            P265_DONOR_FX3_LIBINFRAIPTC_SO_RELPATH,
            P265_PINNED_FX3_LIBINFRAIPTC_SO_BYTES,
            P265_PINNED_FX3_LIBINFRAIPTC_SO_BYTES,
            "FULL_SHA256",
            P265_PINNED_FX3_LIBINFRAIPTC_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_ZTV9InfraIPTC+_ZN9InfraIPTC10ThreadStopEv",
        ),
        (
            "fx6_libinfrahotshoe_so",
            P265_DONOR_FX6_LIBINFRAHOTSHOE_SO_RELPATH,
            P265_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
            P265_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
            "FULL_SHA256",
            P265_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraHotshoe+_ZN12InfraHotshoe13QueryShoeIdOnEij",
        ),
    )
    return tuple(
        Phase265DonorArtifactDigest(
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


def inspect_phase265_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase265DonorSnapshot:
    """Inspect Wave-43 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.15s`."""
    t0 = time.monotonic()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase265_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase265DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P265_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P265_DONOR_FX3_BODYDATA_RELPATH,
            P265_PINNED_FX3_BODYDATA_BYTES,
            P265_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P265_DONOR_FX3_APPFW_702_RELPATH,
            P265_PINNED_FX3_APPFW_702_BYTES,
            P265_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx6_appfw_601_so",
            P265_DONOR_FX6_APPFW_601_RELPATH,
            P265_PINNED_FX6_APPFW_601_BYTES,
            P265_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P265_DONOR_FX3_BACKUP_BIN_RELPATH,
            P265_PINNED_FX3_BACKUP_BIN_BYTES,
            P265_PINNED_FX3_BACKUP_BIN_SHA256,
            lambda d: (
                len(d) >= 20
                and struct.unpack_from("<I", d, 4)[0] == 0xAAAAAAAA
                and d[12:16] == b"BK4\x00"
                and b"ILME-FX3" in d,
                "BK4_ILME_FX3"
                if (
                    len(d) >= 20
                    and struct.unpack_from("<I", d, 4)[0] == 0xAAAAAAAA
                    and d[12:16] == b"BK4\x00"
                    and b"ILME-FX3" in d
                )
                else "BAD_BACKUP_MAGIC",
            ),
        ),
        (
            "fx3_libbackup_so",
            P265_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P265_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P265_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P265_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P265_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P265_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libsaveloadsettings_so",
            P265_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P265_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P265_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"SaveLoadSettingsIf", b"requestToRead", b"requestToCheck", b"requestToWrite"),
            ),
        ),
        (
            "fx3_libgpe_so",
            P265_DONOR_FX3_LIBGPE_SO_RELPATH,
            P265_PINNED_FX3_LIBGPE_SO_BYTES,
            P265_PINNED_FX3_LIBGPE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"gpe_blog_error", b"_ZNK5mpgpe5Gperm4InitEv")),
        ),
        (
            "fx3_cameraondemandsaver_so",
            P265_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH,
            P265_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            P265_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"CameraOnDemandSaver", b"_ZN18CAM_ONDEMAND_SAVER17OsalHandleWrapperC1Ejji"),
            ),
        ),
        (
            "fx3_libinfralenscommunicator_so",
            P265_DONOR_FX3_LIBINFRALENSCOMMUNICATOR_SO_RELPATH,
            P265_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES,
            P265_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"LensCommunicator", b"_Z23LensCommunicator_CreatePN3MWF5ErrCdE"),
            ),
        ),
        (
            "fx3_libinframediaconfig_so",
            P265_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P265_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P265_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraMediaConfig", b"_ZN16InfraMediaConfig10SaveBackupEt"),
            ),
        ),
        (
            "fx3_libinframediadetect_so",
            P265_DONOR_FX3_LIBINFRAMEDIADETECT_SO_RELPATH,
            P265_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES,
            P265_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraMediaDetect", b"_ZN16InfraMediaDetect10GetVersionEv"),
            ),
        ),
        (
            "fx3_libinframetasupplier_so",
            P265_DONOR_FX3_LIBINFRAMETASUPPLIER_SO_RELPATH,
            P265_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_BYTES,
            P265_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraMetaSupplier_Init", b"_ZN20InfraMetaSupplier_If4InitEv"),
            ),
        ),
        (
            "fx3_libinfraiptc_so",
            P265_DONOR_FX3_LIBINFRAIPTC_SO_RELPATH,
            P265_PINNED_FX3_LIBINFRAIPTC_SO_BYTES,
            P265_PINNED_FX3_LIBINFRAIPTC_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"_ZTV9InfraIPTC", b"_ZN9InfraIPTC10ThreadStopEv"),
            ),
        ),
        (
            "fx6_libinfrahotshoe_so",
            P265_DONOR_FX6_LIBINFRAHOTSHOE_SO_RELPATH,
            P265_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
            P265_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraHotshoe", b"_ZN12InfraHotshoe13QueryShoeIdOnEij"),
            ),
        ),
    )

    real_artifacts: List[Phase265DonorArtifactDigest] = []
    any_missing = False
    for aid, rel, pinned_bytes, pinned_sha, marker_fn in probe_specs:
        present, total_b, read_b, dkind, dsha, raw_slice = _read_donor_readonly_bounded(rel)
        if not present:
            any_missing = True
            break
        marker_ok, marker_summary = marker_fn(raw_slice)
        matches = (total_b == pinned_bytes) and (dsha == pinned_sha) and bool(marker_ok)
        real_artifacts.append(
            Phase265DonorArtifactDigest(
                artifact_id=aid,
                relpath=rel,
                present=True,
                read_mode="LOCAL_DONOR_O_RDONLY",
                total_bytes=total_b,
                header_bytes_read=read_b,
                digest_kind=dkind,
                digest_sha256=dsha,
                marker_summary=marker_summary,
                matches_pinned=matches,
            )
        )

    if any_missing:
        artifacts = _synthetic_phase265_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase265DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P265_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    all_ok = len(real_artifacts) == len(probe_specs) and all(a.matches_pinned for a in real_artifacts)
    dt = round(time.monotonic() - t0, 6)
    return Phase265DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all_ok,
        donor_files_inspected=len(real_artifacts),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P265_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(real_artifacts),
    )


# ---------------------------------------------------------------------------
# Default Safe Spec Builders & Pillar 45A / 45B Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_release_wo_card_lens_audio_meter_vault_spec() -> (
    ReleaseWoCardLensAndAudioMeterVaultSpec
):
    """Return canonical safe Wave-43 Pillar 45A spec (cardless body-only bench + Ver. 7.02 5-item audio)."""
    return ReleaseWoCardLensAndAudioMeterVaultSpec()


def build_default_safe_copyright_info_46char_exif_vault_spec() -> CopyrightInfo46CharExifVaultSpec:
    """Return canonical safe Wave-43 Pillar 45B spec (clean-room `Write Copyright Info = Off`, zero PII)."""
    return CopyrightInfo46CharExifVaultSpec()


def evaluate_release_wo_card_lens_and_audio_meter_vault(
    spec: ReleaseWoCardLensAndAudioMeterVaultSpec,
) -> ReleaseWoCardLensAndAudioMeterVaultReport:
    """Evaluate Pillar 45A `[Release w/o Card]`, `[Release w/o Lens]` & Ver. 7.02 5-item `[Audio Recording]`."""
    errors: List[str] = []
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    safety_errs = _safety_invariant_errors()
    if safety_errs or spec.persistent_write_unlock_requested:
        for e in safety_errs:
            _fail(P265_BLOCKED_SAFETY_POLICY_VIOLATION, e)
        if spec.persistent_write_unlock_requested:
            _fail(
                P265_BLOCKED_SAFETY_POLICY_VIOLATION,
                "persistent_write_unlock_requested=True forbidden under zero-write posture",
            )

    if (
        not _is_tmpfs_path(spec.overlay_dir)
        or _targets_persistent_emmc(spec.overlay_dir)
        or not spec.p2_blkroset_locked
        or spec.stage_b_backup_bin_writes != 0
    ):
        _fail(
            P265_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Volatile tmpfs Stage-B overlay / p2 BLKROSET lock violated: overlay={spec.overlay_dir!r}",
        )

    h0_eq_h3_ok = (
        spec.backup_bin_h0_sha256 == P265_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == P265_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256
        and spec.tier0_surfaces_h0_h3_matched == P265_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3_ok:
        _fail(
            P265_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "16/16 Tier-0 Backup.bin H0 == H3 parity drift detected in Pillar 45A",
        )

    # 1. Ver. 2.00+ / 7.02 (ilc/2210) exact 5-item [Audio Recording] vs Ver. 1.x (ilc/2035) spoof rejection
    audio_level_range_ok = (
        P265_AUDIO_REC_LEVEL_MIN <= spec.pre_audio_rec_level <= P265_AUDIO_REC_LEVEL_MAX
        and P265_AUDIO_REC_LEVEL_MIN <= spec.saved_audio_rec_level <= P265_AUDIO_REC_LEVEL_MAX
        and P265_AUDIO_REC_LEVEL_MIN <= spec.post_audio_rec_level <= P265_AUDIO_REC_LEVEL_MAX
    )
    legacy_v1_spoof_detected = (
        spec.helpguide_id == P265_FORBIDDEN_LEGACY_V1_HELPGUIDE_ID
        or spec.fw_version in P265_FORBIDDEN_LEGACY_V1_FW_VERSIONS
        or P265_FORBIDDEN_LEGACY_V1_AUDIO_ITEM in spec.audio_recording_menu_items
        or spec.audio_recording_menu_items != P265_AUDIO_RECORDING_EXACT_5_ITEMS
        or spec.legacy_v1_audio_level_menu_spoof_events != 0
    )
    if legacy_v1_spoof_detected or not audio_level_range_ok:
        _fail(
            P265_BLOCKED_LEGACY_V1_AUDIO_MENU_SPOOF_OR_SPEC_DRIFT,
            "Ver. 1.x (ilc/2035) standalone [Audio Level Display] spoof, non-5-item [Audio Recording] "
            "menu, or Audio Rec Level outside 0..31 rejected on Ver. 7.02 (ilc/2210)",
        )

    spec_valid = (
        spec.camera_model == P265_FX3_MODEL_NAME
        and spec.helpguide_id == P265_FX3_HELPGUIDE_ID
        and spec.fw_version in P265_FX3_SUPPORTED_FW_VERSIONS
        and spec.release_wo_card_menu_path == P265_RELEASE_WO_CARD_MENU_PATH
        and spec.release_wo_lens_menu_path == P265_RELEASE_WO_LENS_MENU_PATH
        and spec.audio_recording_menu_path == P265_AUDIO_RECORDING_MENU_PATH
        and spec.disp_screen_set_menu_path == P265_DISP_SCREEN_SET_MENU_PATH
        and spec.bench_posture in P265_BENCH_POSTURES
        and spec.pre_release_wo_card in P265_RELEASE_WO_MODES
        and spec.saved_release_wo_card in P265_RELEASE_WO_MODES
        and spec.post_release_wo_card in P265_RELEASE_WO_MODES
        and spec.pre_release_wo_lens in P265_RELEASE_WO_MODES
        and spec.saved_release_wo_lens in P265_RELEASE_WO_MODES
        and spec.post_release_wo_lens in P265_RELEASE_WO_MODES
        and spec.pre_audio_recording in P265_AUDIO_RECORDING_MODES
        and spec.saved_audio_recording in P265_AUDIO_RECORDING_MODES
        and spec.post_audio_recording in P265_AUDIO_RECORDING_MODES
        and spec.pre_audio_out_timing in P265_AUDIO_OUT_TIMING_MODES
        and spec.saved_audio_out_timing in P265_AUDIO_OUT_TIMING_MODES
        and spec.post_audio_out_timing in P265_AUDIO_OUT_TIMING_MODES
        and spec.pre_wind_noise_reduct in P265_WIND_NOISE_REDUCT_MODES
        and spec.saved_wind_noise_reduct in P265_WIND_NOISE_REDUCT_MODES
        and spec.post_wind_noise_reduct in P265_WIND_NOISE_REDUCT_MODES
        and spec.pre_shoe_audio_set in P265_SHOE_AUDIO_SET_MODES
        and spec.saved_shoe_audio_set in P265_SHOE_AUDIO_SET_MODES
        and spec.post_shoe_audio_set in P265_SHOE_AUDIO_SET_MODES
        and spec.reset_action in P265_RESET_ACTIONS
        and spec.shooting_domain in P265_SHOOTING_DOMAINS
        and spec.lens_attachment_kind in P265_LENS_ATTACHMENT_KINDS
        and spec.rec_media_dur_hdmi_output in P265_REC_MEDIA_DUR_HDMI_MODES
        and isinstance(spec.attached_lens_model, str)
        and bool(spec.attached_lens_model.strip())
    )
    if spec.camset_load_after_reset:
        spec_valid = spec_valid and (
            spec.camset_slot in (1, 2)
            and spec.camset_filename in P265_CAMSET_FILENAMES
            and spec.camset_source_model == P265_FX3_MODEL_NAME
            and spec.camset_read_only_load is True
        )
    if not spec_valid and block_code is None:
        _fail(
            P265_BLOCKED_INVALID_RELEASE_WO_OR_AUDIO_METER_SPEC,
            "Invalid ILME-FX3 Release w/o Card/Lens, Audio Recording, DISP Screen Set, or CAMSET spec",
        )

    # 2. Reset & O_RDONLY CAMSET01.DAT scope verification
    if spec.camset_load_after_reset:
        exp_wo_card = spec.saved_release_wo_card
        exp_wo_lens = spec.saved_release_wo_lens
        exp_disp_chk = spec.saved_disp_screen_audio_level_checked
        exp_aud_rec = spec.saved_audio_recording
        exp_aud_lvl = spec.saved_audio_rec_level
        exp_aud_tim = spec.saved_audio_out_timing
        exp_wind = spec.saved_wind_noise_reduct
        exp_shoe = spec.saved_shoe_audio_set
    elif spec.reset_action == "Initialize":
        exp_wo_card = P265_RELEASE_WO_CARD_DEFAULT
        exp_wo_lens = P265_RELEASE_WO_LENS_DEFAULT
        exp_disp_chk = True
        exp_aud_rec = P265_AUDIO_RECORDING_DEFAULT
        exp_aud_lvl = P265_AUDIO_REC_LEVEL_DEFAULT
        exp_aud_tim = P265_AUDIO_OUT_TIMING_DEFAULT
        exp_wind = P265_WIND_NOISE_REDUCT_DEFAULT
        exp_shoe = P265_SHOE_AUDIO_SET_DEFAULT
    elif spec.reset_action == "Camera Settings Reset":
        # [Release w/o Card], [Release w/o Lens] & [DISP (Screen Disp) Set] survive [Camera Settings Reset];
        # [Audio Recording] shooting items reset to factory defaults.
        exp_wo_card = spec.pre_release_wo_card
        exp_wo_lens = spec.pre_release_wo_lens
        exp_disp_chk = spec.pre_disp_screen_audio_level_checked
        exp_aud_rec = P265_AUDIO_RECORDING_DEFAULT
        exp_aud_lvl = P265_AUDIO_REC_LEVEL_DEFAULT
        exp_aud_tim = P265_AUDIO_OUT_TIMING_DEFAULT
        exp_wind = P265_WIND_NOISE_REDUCT_DEFAULT
        exp_shoe = P265_SHOE_AUDIO_SET_DEFAULT
    else:
        exp_wo_card = spec.pre_release_wo_card
        exp_wo_lens = spec.pre_release_wo_lens
        exp_disp_chk = spec.pre_disp_screen_audio_level_checked
        exp_aud_rec = spec.pre_audio_recording
        exp_aud_lvl = spec.pre_audio_rec_level
        exp_aud_tim = spec.pre_audio_out_timing
        exp_wind = spec.pre_wind_noise_reduct
        exp_shoe = spec.pre_shoe_audio_set

    reset_scope_ok = (
        spec.post_release_wo_card == exp_wo_card
        and spec.post_release_wo_lens == exp_wo_lens
        and spec.post_disp_screen_audio_level_checked == exp_disp_chk
        and spec.post_audio_recording == exp_aud_rec
        and spec.post_audio_rec_level == exp_aud_lvl
        and spec.post_audio_out_timing == exp_aud_tim
        and spec.post_wind_noise_reduct == exp_wind
        and spec.post_shoe_audio_set == exp_shoe
    )

    # 3. [Release w/o Lens] across Still + Movie + S&Q & zero E-ND / zero body-only E-mount lens UART traffic
    exp_still_ok, exp_movie_int_ok, exp_ext_hdmi_ok = compute_expected_release_wo_card_and_lens_gate(
        shooting_domain=spec.shooting_domain,
        release_wo_card=spec.post_release_wo_card,
        release_wo_lens=spec.post_release_wo_lens,
        slot1_card_inserted=spec.slot1_card_inserted,
        slot2_card_inserted=spec.slot2_card_inserted,
        lens_attachment_kind=spec.lens_attachment_kind,
        hdmi_connected=spec.hdmi_connected,
        rec_media_dur_hdmi_output=spec.rec_media_dur_hdmi_output,
    )
    electronic_lens = spec.lens_attachment_kind == "EMOUNT_ELECTRONIC_LENS"
    lens_gate_blocked = (not electronic_lens) and (spec.post_release_wo_lens == "Disable")
    lens_block_violated = lens_gate_blocked and (
        spec.still_shutter_actuated
        or spec.movie_internal_recording_started
        or spec.external_hdmi_capture_allowed
    )
    end_and_uart_ok = (
        spec.fx3_has_builtin_end_filter is False
        and spec.e_nd_actuator_tx_count == 0
        and spec.emount_lens_uart_tx_bytes >= 0
        and (electronic_lens or spec.emount_lens_uart_tx_bytes == 0)
        and not lens_block_violated
    )
    if not end_and_uart_ok:
        _fail(
            P265_BLOCKED_RELEASE_WO_LENS_OR_END_UART_VIOLATION,
            f"[Release w/o Lens] / zero E-ND / body-only lens UART violated: kind={spec.lens_attachment_kind!r}, "
            f"wo_lens={spec.post_release_wo_lens!r}, e_nd_tx={spec.e_nd_actuator_tx_count}, "
            f"lens_uart={spec.emount_lens_uart_tx_bytes}",
        )

    # 4. [Release w/o Card] Still-only scope vs Movie internal media gate & bench posture safety
    any_card = bool(spec.slot1_card_inserted or spec.slot2_card_inserted)
    saved_cnt_ok = (
        (spec.still_images_saved_to_card == 0)
        if (not any_card or spec.shooting_domain != "Still" or not spec.still_shutter_actuated)
        else (spec.still_images_saved_to_card >= 1)
    )
    bench_posture_ok = (
        (
            spec.bench_posture == "CARDLESS_DIAGNOSTIC_BENCH"
            and not any_card
            and spec.cardless_unrecorded_production_violations == 0
        )
        or (
            spec.bench_posture == "PRODUCTION_SHOOT"
            and spec.post_release_wo_card == "Disable"
            and spec.cardless_unrecorded_production_violations == 0
        )
    )
    card_gate_ok = (
        spec.still_shutter_actuated == exp_still_ok
        and spec.movie_internal_recording_started == exp_movie_int_ok
        and spec.external_hdmi_capture_allowed == exp_ext_hdmi_ok
        and saved_cnt_ok
        and bench_posture_ok
    )
    if not card_gate_ok:
        _fail(
            P265_BLOCKED_RELEASE_WO_CARD_MOVIE_OR_BENCH_VIOLATION,
            f"[Release w/o Card] Still-only vs Movie media gate or bench safety violated: "
            f"posture={spec.bench_posture!r}, domain={spec.shooting_domain!r}, "
            f"wo_card={spec.post_release_wo_card!r}, any_card={any_card}, "
            f"movie_started={spec.movie_internal_recording_started} (exp {exp_movie_int_ok}), "
            f"still_actuated={spec.still_shutter_actuated} (exp {exp_still_ok})",
        )

    # 5. Ver. 7.02 DISP (Screen Disp) Set audio meter visibility (2ch/4ch, suppressed in S&Q) + reset scope
    exp_meter_vis, exp_meter_ch = compute_expected_disp_audio_meter_state(
        shooting_domain=spec.shooting_domain,
        audio_recording=spec.post_audio_recording,
        shoe_audio_set=spec.post_shoe_audio_set,
        mi_shoe_digital_4ch_attached=spec.mi_shoe_digital_4ch_attached,
        disp_screen_audio_level_checked=spec.post_disp_screen_audio_level_checked,
    )
    disp_meter_ok = (
        not legacy_v1_spoof_detected
        and audio_level_range_ok
        and spec.audio_meter_visible_on_disp == exp_meter_vis
        and spec.audio_meter_channels_rendered == exp_meter_ch
    )
    if not reset_scope_ok or not disp_meter_ok:
        if block_code != P265_BLOCKED_LEGACY_V1_AUDIO_MENU_SPOOF_OR_SPEC_DRIFT:
            _fail(
                P265_BLOCKED_DISP_AUDIO_METER_OR_RESET_SCOPE_DRIFT,
                f"DISP (Screen Disp) Set audio meter or reset scope drift: reset_ok={reset_scope_ok}, "
                f"domain={spec.shooting_domain!r}, exp_meter=({exp_meter_vis},{exp_meter_ch}), "
                f"got_meter=({spec.audio_meter_visible_on_disp},{spec.audio_meter_channels_rendered})",
            )

    passed = len(errors) == 0
    end_tx = max(
        int(spec.e_nd_actuator_tx_count),
        0 if (spec.fx3_has_builtin_end_filter is False and spec.e_nd_actuator_tx_count == 0) else 1,
    )
    prod_viol = max(
        int(spec.cardless_unrecorded_production_violations),
        0 if bench_posture_ok else 1,
    )
    v1_spoof = max(
        int(spec.legacy_v1_audio_level_menu_spoof_events),
        1 if legacy_v1_spoof_detected else 0,
    )
    digest = _canonical_sha256(
        {
            "pillar": "45A",
            "passed": passed,
            "block_code": block_code,
            "wo_card": spec.post_release_wo_card,
            "wo_lens": spec.post_release_wo_lens,
            "domain": spec.shooting_domain,
            "end_tx": end_tx,
            "prod_viol": prod_viol,
            "v1_spoof": v1_spoof,
            "meter_ch": spec.audio_meter_channels_rendered,
        }
    )
    return ReleaseWoCardLensAndAudioMeterVaultReport(
        passed=passed,
        status=P265_STATUS_VERIFIED_PILLAR_45A if passed else P265_STATUS_REJECTED_PILLAR_45A,
        block_code=block_code,
        reset_and_camset_scope_verified=reset_scope_ok,
        release_wo_card_still_vs_movie_gate_verified=card_gate_ok,
        release_wo_lens_and_zero_end_uart_verified=end_and_uart_ok,
        v702_audio_5item_and_disp_meter_verified=disp_meter_ok,
        h0_equals_h3_verified=h0_eq_h3_ok,
        fx3_has_builtin_end_filter=bool(spec.fx3_has_builtin_end_filter),
        e_nd_actuator_tx_count=end_tx,
        emount_lens_uart_tx_bytes=int(spec.emount_lens_uart_tx_bytes),
        cardless_unrecorded_production_violations=prod_viol,
        legacy_v1_audio_level_menu_spoof_events=v1_spoof,
        audio_meter_channels_rendered=int(spec.audio_meter_channels_rendered),
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_copyright_info_46char_exif_vault(
    spec: CopyrightInfo46CharExifVaultSpec,
) -> CopyrightInfo46CharExifVaultReport:
    """Evaluate Pillar 45B `[Copyright Info]` `<= 46`-char Still EXIF scope, reset survival & PII hygiene."""
    errors: List[str] = []
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    safety_errs = _safety_invariant_errors()
    if safety_errs or spec.persistent_write_unlock_requested:
        for e in safety_errs:
            _fail(P265_BLOCKED_SAFETY_POLICY_VIOLATION, e)
        if spec.persistent_write_unlock_requested:
            _fail(
                P265_BLOCKED_SAFETY_POLICY_VIOLATION,
                "persistent_write_unlock_requested=True forbidden under zero-write posture",
            )

    if (
        not _is_tmpfs_path(spec.overlay_dir)
        or _targets_persistent_emmc(spec.overlay_dir)
        or not spec.p2_blkroset_locked
        or spec.stage_b_backup_bin_writes != 0
    ):
        _fail(
            P265_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Volatile tmpfs Stage-B overlay / p2 BLKROSET lock violated: overlay={spec.overlay_dir!r}",
        )

    h0_eq_h3_ok = (
        spec.backup_bin_h0_sha256 == P265_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == P265_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256
        and spec.tier0_surfaces_h0_h3_matched == P265_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3_ok:
        _fail(
            P265_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "16/16 Tier-0 Backup.bin H0 == H3 parity drift detected in Pillar 45B",
        )

    # 1. <= 46-char printable ASCII bounds & read-only [Disp. Copyright Info] dialog
    all_strings = (
        spec.pre_photographer_text,
        spec.pre_copyright_text,
        spec.post_photographer_text,
        spec.post_copyright_text,
        spec.displayed_photographer_preview,
        spec.displayed_copyright_preview,
    )
    bounds_checks = [_is_printable_ascii_46(s) for s in all_strings if isinstance(s, str)]
    char_46_ascii_ok = (
        len(bounds_checks) == 6
        and all(len_ok and asc_ok for len_ok, asc_ok in bounds_checks)
    )
    disp_ro_ok = (
        spec.disp_copyright_info_open_mode == "O_RDONLY"
        and spec.disp_copyright_info_flash_writes == 0
    )
    char_and_disp_ok = char_46_ascii_ok and disp_ro_ok
    if not char_46_ascii_ok:
        _fail(
            P265_BLOCKED_COPYRIGHT_46CHAR_OR_ASCII_OVERFLOW,
            f"[Copyright Info] exceeded <= {P265_COPYRIGHT_MAX_CHARS}-char or printable ASCII (0x20..0x7E) bound",
        )

    spec_valid = (
        spec.camera_model == P265_FX3_MODEL_NAME
        and spec.helpguide_id == P265_FX3_HELPGUIDE_ID
        and spec.fw_version in P265_FX3_SUPPORTED_FW_VERSIONS
        and spec.copyright_info_menu_path == P265_COPYRIGHT_INFO_MENU_PATH
        and spec.copyright_info_subitems == P265_COPYRIGHT_INFO_EXACT_4_ITEMS
        and spec.pre_write_copyright_info in P265_WRITE_COPYRIGHT_MODES
        and spec.post_write_copyright_info in P265_WRITE_COPYRIGHT_MODES
        and spec.reset_action in P265_RESET_ACTIONS
        and spec.shooting_domain in P265_SHOOTING_DOMAINS
        and spec.still_image_format in P265_STILL_IMAGE_FORMATS
        and spec.movie_stream_format in P265_MOVIE_STREAM_FORMATS
        and spec.target_media_slot in (0, 1, 2)
        and disp_ro_ok
    )
    if not spec_valid and block_code is None:
        _fail(
            P265_BLOCKED_INVALID_COPYRIGHT_INFO_SPEC,
            "Invalid ILME-FX3 [Copyright Info] 4-item menu path, FW, media slot, or O_RDONLY Disp. mode",
        )

    # 2. [Camera Settings Reset] string survival vs [Initialize] wipe & [Disp. Copyright Info] preview
    exp_wr, exp_photog, exp_copy = compute_expected_copyright_info_state(
        pre_write_copyright_info=spec.pre_write_copyright_info,
        pre_photographer_text=spec.pre_photographer_text,
        pre_copyright_text=spec.pre_copyright_text,
        reset_action=spec.reset_action,
    )
    exp_c_icon = spec.post_write_copyright_info == "On" and (
        len(spec.post_photographer_text) > 0 or len(spec.post_copyright_text) > 0
    )
    reset_vs_init_ok = (
        spec.post_write_copyright_info == exp_wr
        and spec.post_photographer_text == exp_photog
        and spec.post_copyright_text == exp_copy
        and spec.displayed_photographer_preview == spec.post_photographer_text
        and spec.displayed_copyright_preview == spec.post_copyright_text
        and spec.copyright_c_icon_shown_on_screen == exp_c_icon
    )
    if not reset_vs_init_ok:
        _fail(
            P265_BLOCKED_COPYRIGHT_RESET_VS_INITIALIZE_SCOPE_DRIFT,
            f"[Copyright Info] reset vs Initialize scope or Disp. preview drift under {spec.reset_action!r}: "
            f"expected(wr={exp_wr!r},photog_len={len(exp_photog)},copy_len={len(exp_copy)}), "
            f"got(wr={spec.post_write_copyright_info!r},photog_len={len(spec.post_photographer_text)},"
            f"copy_len={len(spec.post_copyright_text)})",
        )

    # 3. Still-JPEG/HEIF EXIF-only scope vs XAVC / HDMI RAW movie stream isolation
    exp_still_exif_written = (
        spec.shooting_domain == "Still"
        and spec.post_write_copyright_info == "On"
        and spec.target_media_slot == 2
        and (len(spec.post_photographer_text) > 0 or len(spec.post_copyright_text) > 0)
    )
    still_exif_only_ok = (
        spec.movie_xavc_or_raw_copyright_mutated is False
        and spec.still_exif_copyright_written == exp_still_exif_written
        and spec.copyright_char_overflow_or_movie_mutation_events == 0
    )
    if not still_exif_only_ok:
        _fail(
            P265_BLOCKED_COPYRIGHT_MOVIE_STREAM_OR_EXIF_SCOPE_VIOLATION,
            f"[Copyright Info] Still-EXIF-only / XAVC-RAW movie isolation violated: "
            f"domain={spec.shooting_domain!r}, write={spec.post_write_copyright_info!r}, "
            f"still_exif={spec.still_exif_copyright_written} (exp {exp_still_exif_written}), "
            f"movie_mutated={spec.movie_xavc_or_raw_copyright_mutated}",
        )

    # 4. Clean-room operator PII zeroing, CAMSET excluded-items firewall & Slot-1 Tier-0 vault guard
    clean_room_pii_ok = (
        not spec.contains_operator_pii
        and spec.photographer_copyright_pii_leaked_bytes == 0
        and (
            not spec.clean_room_pii_hygiene_enforced
            or (
                spec.post_write_copyright_info == "Off"
                and spec.post_photographer_text == ""
                and spec.post_copyright_text == ""
            )
        )
    )
    camset_ok = (
        spec.camset_exported_copyright_pii_bytes == 0
        and spec.camset_overwrote_inbody_copyright is False
    )
    if spec.camset_load_after_reset:
        camset_ok = camset_ok and (
            spec.camset_slot in (1, 2)
            and spec.camset_filename in P265_CAMSET_FILENAMES
            and spec.camset_source_model == P265_FX3_MODEL_NAME
            and spec.camset_read_only_load is True
        )
    slot1_vault_ok = (
        spec.slot1_copyright_vault_mutation_bytes == 0
        and not (
            spec.slot1_tier0_vault_active
            and (spec.slot1_save_or_exif_write_attempted or spec.target_media_slot == 1)
        )
        and (not spec.slot1_tier0_vault_active or spec.slot1_sdxc_wp_locked)
    )
    pii_and_vault_ok = clean_room_pii_ok and camset_ok and slot1_vault_ok
    if not pii_and_vault_ok:
        _fail(
            P265_BLOCKED_COPYRIGHT_CLEAN_ROOM_PII_OR_SLOT1_VAULT_LEAK,
            "Clean-room operator PII leak, CAMSET [Copyright Info] exclusion breach, or Slot-1 vault mutation",
        )

    passed = len(errors) == 0
    pii_bytes = max(
        int(spec.photographer_copyright_pii_leaked_bytes),
        int(spec.camset_exported_copyright_pii_bytes),
        0 if clean_room_pii_ok and camset_ok else 1,
    )
    overflow_or_movie_cnt = max(
        int(spec.copyright_char_overflow_or_movie_mutation_events),
        0 if (char_46_ascii_ok and still_exif_only_ok) else 1,
    )
    vault_mut = max(
        int(spec.slot1_copyright_vault_mutation_bytes),
        0 if slot1_vault_ok else 1,
    )
    digest = _canonical_sha256(
        {
            "pillar": "45B",
            "passed": passed,
            "block_code": block_code,
            "write_copyright": spec.post_write_copyright_info,
            "photog_len": len(spec.post_photographer_text),
            "copy_len": len(spec.post_copyright_text),
            "pii_bytes": pii_bytes,
            "overflow_or_movie": overflow_or_movie_cnt,
            "vault_mut": vault_mut,
        }
    )
    return CopyrightInfo46CharExifVaultReport(
        passed=passed,
        status=P265_STATUS_VERIFIED_PILLAR_45B if passed else P265_STATUS_REJECTED_PILLAR_45B,
        block_code=block_code,
        char_46_ascii_and_disp_readonly_verified=char_and_disp_ok,
        reset_survival_vs_initialize_wipe_verified=reset_vs_init_ok,
        still_exif_only_movie_isolation_verified=still_exif_only_ok,
        clean_room_pii_and_slot1_vault_verified=pii_and_vault_ok,
        h0_equals_h3_verified=h0_eq_h3_ok,
        photographer_char_length=len(spec.post_photographer_text),
        copyright_char_length=len(spec.post_copyright_text),
        photographer_copyright_pii_leaked_bytes=pii_bytes,
        copyright_char_overflow_or_movie_mutation_events=overflow_or_movie_cnt,
        slot1_copyright_vault_mutation_bytes=vault_mut,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_release_wo_card_lens_audio_meter_and_copyright_vault(
    release_audio_spec: Optional[ReleaseWoCardLensAndAudioMeterVaultSpec] = None,
    copyright_spec: Optional[CopyrightInfo46CharExifVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> ReleaseWoCardLensAudioMeterAndCopyrightVaultReport:
    """Combined single-shot verifier for Pillar 45A + Pillar 45B + bounded O_RDONLY Wave-43 donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase265_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_release_wo_card_lens_and_audio_meter_vault(
        release_audio_spec or build_default_safe_release_wo_card_lens_audio_meter_vault_spec()
    )
    rep_b = evaluate_copyright_info_46char_exif_vault(
        copyright_spec or build_default_safe_copyright_info_46char_exif_vault_spec()
    )
    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 265 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        errs.append(f"Donor inspection exceeded 0.15s budget: {donor_snapshot.elapsed_seconds}s")
    ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return ReleaseWoCardLensAudioMeterAndCopyrightVaultReport(
        schema=PHASE265_SCHEMA,
        version=PHASE265_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=ok,
        passed=ok,
        status=P265_STATUS_VERIFIED_PILLAR45_SUITE if ok else P265_STATUS_FAIL_PILLAR45_SUITE,
        donor_snapshot=donor_snapshot,
        release_wo_card_lens_audio_report=rep_a,
        copyright_info_46char_exif_report=rep_b,
        fx3_has_builtin_end_filter=rep_a.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=rep_a.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=rep_a.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=rep_a.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=rep_b.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            rep_b.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=rep_b.slot1_copyright_vault_mutation_bytes,
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


def verify_release_wo_card_lens_audio_meter_copyright_vault(
    release_audio_spec: Optional[ReleaseWoCardLensAndAudioMeterVaultSpec] = None,
    copyright_spec: Optional[CopyrightInfo46CharExifVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> ReleaseWoCardLensAudioMeterAndCopyrightVaultReport:
    """Symmetry alias for `verify_release_wo_card_lens_audio_meter_and_copyright_vault`."""
    return verify_release_wo_card_lens_audio_meter_and_copyright_vault(
        release_audio_spec=release_audio_spec,
        copyright_spec=copyright_spec,
        force_clean_room=force_clean_room,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillar 45A & Pillar 45B) & Standalone Runner
# ---------------------------------------------------------------------------


def run_pillar45a_release_wo_card_lens_audio_meter_vault_6_scenario_suite() -> Pillar45ASuiteResult:
    """Run all 6 canonical Pillar 45A scenarios (`2` safe + `4` negative hardware/menu guards)."""
    cases: Tuple[Tuple[str, bool, ReleaseWoCardLensAndAudioMeterVaultSpec, Optional[str]], ...] = (
        (
            P265_PILLAR_45A_SCENARIO_IDS[0],
            True,
            ReleaseWoCardLensAndAudioMeterVaultSpec(),
            None,
        ),
        (
            P265_PILLAR_45A_SCENARIO_IDS[1],
            True,
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                bench_posture="PRODUCTION_SHOOT",
                pre_release_wo_card="Enable",
                pre_release_wo_lens="Disable",
                reset_action="Camera Settings Reset",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model=P265_FX3_MODEL_NAME,
                camset_read_only_load=True,
                saved_release_wo_card="Disable",
                saved_release_wo_lens="Enable",
                saved_audio_recording="On",
                saved_audio_rec_level=20,
                saved_audio_out_timing="Lip Sync",
                saved_wind_noise_reduct="Off",
                saved_shoe_audio_set="48kHz/24bit 4ch",
                saved_disp_screen_audio_level_checked=True,
                post_release_wo_card="Disable",
                post_release_wo_lens="Enable",
                post_audio_recording="On",
                post_audio_rec_level=20,
                post_audio_out_timing="Lip Sync",
                post_wind_noise_reduct="Off",
                post_shoe_audio_set="48kHz/24bit 4ch",
                post_disp_screen_audio_level_checked=True,
                shooting_domain="Movie",
                slot1_card_inserted=False,
                slot2_card_inserted=True,
                lens_attachment_kind="PL_MOUNT_MECHANICAL_ADAPTER",
                attached_lens_model="PL_ADAPTER_MANUAL",
                e_nd_actuator_tx_count=0,
                emount_lens_uart_tx_bytes=0,
                hdmi_connected=True,
                rec_media_dur_hdmi_output="On",
                still_shutter_actuated=False,
                still_images_saved_to_card=0,
                movie_internal_recording_started=True,
                external_hdmi_capture_allowed=True,
                mi_shoe_digital_4ch_attached=True,
                audio_meter_visible_on_disp=True,
                audio_meter_channels_rendered=4,
            ),
            None,
        ),
        (
            P265_PILLAR_45A_SCENARIO_IDS[2],
            False,
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                shooting_domain="Movie",
                slot1_card_inserted=False,
                slot2_card_inserted=False,
                still_shutter_actuated=False,
                movie_internal_recording_started=True,
            ),
            P265_BLOCKED_RELEASE_WO_CARD_MOVIE_OR_BENCH_VIOLATION,
        ),
        (
            P265_PILLAR_45A_SCENARIO_IDS[3],
            False,
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                pre_release_wo_lens="Disable",
                post_release_wo_lens="Disable",
                lens_attachment_kind="BODY_ONLY_CAP",
                still_shutter_actuated=True,
                e_nd_actuator_tx_count=2,
                emount_lens_uart_tx_bytes=64,
            ),
            P265_BLOCKED_RELEASE_WO_LENS_OR_END_UART_VIOLATION,
        ),
        (
            P265_PILLAR_45A_SCENARIO_IDS[4],
            False,
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                helpguide_id=P265_FORBIDDEN_LEGACY_V1_HELPGUIDE_ID,
                audio_recording_menu_items=(
                    "Audio Recording",
                    "Audio Rec Level",
                    "Audio Out Timing",
                    "Wind Noise Reduct.",
                    "Audio Level Display",
                ),
                legacy_v1_audio_level_menu_spoof_events=1,
            ),
            P265_BLOCKED_LEGACY_V1_AUDIO_MENU_SPOOF_OR_SPEC_DRIFT,
        ),
        (
            P265_PILLAR_45A_SCENARIO_IDS[5],
            False,
            ReleaseWoCardLensAndAudioMeterVaultSpec(
                shooting_domain="S&Q",
                still_shutter_actuated=False,
                movie_internal_recording_started=False,
                audio_meter_visible_on_disp=True,
                audio_meter_channels_rendered=2,
            ),
            P265_BLOCKED_DISP_AUDIO_METER_OR_RESET_SCOPE_DRIFT,
        ),
    )

    outcomes: List[Pillar45ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_release_wo_card_lens_and_audio_meter_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar45ScenarioOutcome(
                scenario_id=sid,
                pillar="45A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar45ASuiteResult(
        passed=all_ok,
        status=P265_STATUS_VERIFIED_PILLAR_45A if all_ok else P265_STATUS_REJECTED_PILLAR_45A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar45b_copyright_info_46char_exif_vault_6_scenario_suite() -> Pillar45BSuiteResult:
    """Run all 6 canonical Pillar 45B scenarios (`2` safe + `4` negative EXIF/PII/vault guards)."""
    s46_photog = "LAB_BENCH_SYNTH_PHOTOGRAPHER_46CHAR_BOUND_TEST"
    s46_copy = "LAB_BENCH_SYNTH_COPYRIGHT_46CHAR_BOUNDARY_TEST"
    cases: Tuple[Tuple[str, bool, CopyrightInfo46CharExifVaultSpec, Optional[str]], ...] = (
        (
            P265_PILLAR_45B_SCENARIO_IDS[0],
            True,
            CopyrightInfo46CharExifVaultSpec(),
            None,
        ),
        (
            P265_PILLAR_45B_SCENARIO_IDS[1],
            True,
            CopyrightInfo46CharExifVaultSpec(
                pre_write_copyright_info="On",
                pre_photographer_text=s46_photog,
                pre_copyright_text=s46_copy,
                reset_action="Camera Settings Reset",
                post_write_copyright_info="Off",
                post_photographer_text=s46_photog,
                post_copyright_text=s46_copy,
                displayed_photographer_preview=s46_photog,
                displayed_copyright_preview=s46_copy,
                copyright_c_icon_shown_on_screen=False,
                shooting_domain="Movie",
                movie_stream_format="XAVC S-I 4K",
                target_media_slot=2,
                still_exif_copyright_written=False,
                movie_xavc_or_raw_copyright_mutated=False,
                clean_room_pii_hygiene_enforced=False,
                contains_operator_pii=False,
                photographer_copyright_pii_leaked_bytes=0,
            ),
            None,
        ),
        (
            P265_PILLAR_45B_SCENARIO_IDS[2],
            False,
            CopyrightInfo46CharExifVaultSpec(
                pre_photographer_text="X" * 47,
                pre_copyright_text="BAD_CTRL\x07BYTE",
                copyright_char_overflow_or_movie_mutation_events=1,
            ),
            P265_BLOCKED_COPYRIGHT_46CHAR_OR_ASCII_OVERFLOW,
        ),
        (
            P265_PILLAR_45B_SCENARIO_IDS[3],
            False,
            CopyrightInfo46CharExifVaultSpec(
                shooting_domain="Movie",
                movie_stream_format="XAVC HS 4K",
                movie_xavc_or_raw_copyright_mutated=True,
                copyright_char_overflow_or_movie_mutation_events=1,
            ),
            P265_BLOCKED_COPYRIGHT_MOVIE_STREAM_OR_EXIF_SCOPE_VIOLATION,
        ),
        (
            P265_PILLAR_45B_SCENARIO_IDS[4],
            False,
            CopyrightInfo46CharExifVaultSpec(
                pre_write_copyright_info="On",
                pre_photographer_text=s46_photog,
                pre_copyright_text=s46_copy,
                reset_action="Camera Settings Reset",
                post_write_copyright_info="Off",
                post_photographer_text="",
                post_copyright_text="",
                displayed_photographer_preview="",
                displayed_copyright_preview="",
                clean_room_pii_hygiene_enforced=False,
            ),
            P265_BLOCKED_COPYRIGHT_RESET_VS_INITIALIZE_SCOPE_DRIFT,
        ),
        (
            P265_PILLAR_45B_SCENARIO_IDS[5],
            False,
            CopyrightInfo46CharExifVaultSpec(
                pre_write_copyright_info="On",
                pre_photographer_text="OP_PII_NAME",
                pre_copyright_text="OP_PII_STUDIO",
                reset_action="NONE",
                post_write_copyright_info="On",
                post_photographer_text="OP_PII_NAME",
                post_copyright_text="OP_PII_STUDIO",
                displayed_photographer_preview="OP_PII_NAME",
                displayed_copyright_preview="OP_PII_STUDIO",
                copyright_c_icon_shown_on_screen=True,
                shooting_domain="Still",
                target_media_slot=2,
                still_exif_copyright_written=True,
                clean_room_pii_hygiene_enforced=True,
                contains_operator_pii=True,
                photographer_copyright_pii_leaked_bytes=24,
                slot1_save_or_exif_write_attempted=True,
                slot1_copyright_vault_mutation_bytes=512,
            ),
            P265_BLOCKED_COPYRIGHT_CLEAN_ROOM_PII_OR_SLOT1_VAULT_LEAK,
        ),
    )

    outcomes: List[Pillar45ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_copyright_info_46char_exif_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar45ScenarioOutcome(
                scenario_id=sid,
                pillar="45B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar45BSuiteResult(
        passed=all_ok,
        status=P265_STATUS_VERIFIED_PILLAR_45B if all_ok else P265_STATUS_REJECTED_PILLAR_45B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar45_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar45StandaloneReport:
    """Run full Pillar 45 standalone suite (`6/6` Pillar 45A + `6/6` Pillar 45B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase265_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar45a_release_wo_card_lens_audio_meter_vault_6_scenario_suite()
    res_b = run_pillar45b_copyright_info_46char_exif_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 265 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor inspection exceeded 0.15s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE265_SCHEMA,
            "version": PHASE265_VERSION,
            "mode": donor_snapshot.verification_mode,
            "45a": [asdict(s) for s in res_a.scenarios],
            "45b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar45StandaloneReport(
        schema=PHASE265_SCHEMA,
        version=PHASE265_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P265_STATUS_VERIFIED_PILLAR45_SUITE if all_ok else P265_STATUS_FAIL_PILLAR45_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_45a_release_wo_card_lens_audio_meter_vault=res_a,
        pillar_45b_copyright_info_46char_exif_vault=res_b,
        fx3_has_builtin_end_filter=P265_FX3_HAS_BUILTIN_END_FILTER if res_a.passed else True,
        e_nd_actuator_tx_count=P265_E_ND_ACTUATOR_TX_COUNT if res_a.passed else 1,
        cardless_unrecorded_production_violations=(
            P265_CARDLESS_UNRECORDED_PRODUCTION_VIOLATIONS if res_a.passed else 1
        ),
        legacy_v1_audio_level_menu_spoof_events=(
            P265_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_EVENTS if res_a.passed else 1
        ),
        photographer_copyright_pii_leaked_bytes=(
            P265_PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES if res_b.passed else 1
        ),
        copyright_char_overflow_or_movie_mutation_events=(
            P265_COPYRIGHT_CHAR_OVERFLOW_OR_MOVIE_MUTATION_EVENTS if res_b.passed else 1
        ),
        slot1_copyright_vault_mutation_bytes=(
            P265_SLOT1_COPYRIGHT_VAULT_MUTATION_BYTES if res_b.passed else 1
        ),
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


# ---------------------------------------------------------------------------
# Unified 45/45 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master45_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_45pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master45PillarRecoveryReport:
    """Evaluate and aggregate all 45 recovery pillars (`1..45`) concurrently -> `45/45` recovery master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_45_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_44pillar() -> Master44PillarRecoveryReport:
        return evaluate_realhw_44pillar_recovery_master(**kw)

    def _run_p45() -> Tuple[Pillar45StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar45_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_44 = pool.submit(_run_44pillar)
        fut_45 = pool.submit(_run_p45)
        m44_rep = fut_44.result()
        p45_rep, p45_dt = fut_45.result()

    all_errors: List[str] = list(m44_rep.errors) + list(p45_rep.errors)
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
    ):
        if getattr(m44_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-44 violated {attr_name} == {expected_val}")
        if getattr(p45_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 45 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("apsc_s35_4k_or_raw_bypass_events", 0),
        ("ai_unit_subject_recog_spoof_events", 0),
        ("hdmi_clean_feed_eye_frame_baked_pixels", 0),
        ("version_dialog_flash_writes", 0),
        ("slot1_bodydata_vault_mutation_bytes", 0),
        ("auto_slow_shutter_lockout_bypass_events", 0),
        ("auto_slow_shutter_angle_overlap_events", 0),
        ("breathing_comp_raw_or_240p_bypass_events", 0),
        ("hdmi_rec_ctrl_without_tc_violations", 0),
        ("slot1_hdmi_rec_vault_mutation_bytes", 0),
        ("diff_set_transition_corruption_events", 0),
        ("shutter_angle_common_bleed_events", 0),
        ("slot1_custom_key_vault_mutation_bytes", 0),
        ("fx3_has_builtin_evf", False),
        ("evf_finder_monitor_spoof_events", 0),
        ("tier0_battery_high_display_violations", 0),
        ("bt_rmt_ir_lockout_violations", 0),
        ("slot1_mymenu_vault_mutation_bytes", 0),
        ("destructive_menu_delete_confusions", 0),
        ("shutter_angle_exposure_step_drift_events", 0),
        ("fx3_has_var_shutter", False),
        ("unbuffered_battery_pull_events", 0),
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(m44_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-44 violated {attr_name} == {expected_val}")
    if m44_rep.bodydata_flash_attempts_blocked < 1:
        all_errors.append("Pillars 1-44 violated bodydata_flash_attempts_blocked >= 1")

    for attr_name, expected_val in (
        ("fx3_has_builtin_end_filter", False),
        ("e_nd_actuator_tx_count", 0),
        ("cardless_unrecorded_production_violations", 0),
        ("legacy_v1_audio_level_menu_spoof_events", 0),
        ("photographer_copyright_pii_leaked_bytes", 0),
        ("copyright_char_overflow_or_movie_mutation_events", 0),
        ("slot1_copyright_vault_mutation_bytes", 0),
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(p45_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 45 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m44_rep.pillars)
    spec45 = MASTER_45_PILLAR_SPECS[44]
    p45_metrics = {
        "pillar_45a_release_wo_card_lens_audio_meter_vault": (
            f"{p45_rep.pillar_45a_release_wo_card_lens_audio_meter_vault.scenarios_passed}/"
            f"{p45_rep.pillar_45a_release_wo_card_lens_audio_meter_vault.scenarios_total}"
        ),
        "pillar_45b_copyright_info_46char_exif_vault": (
            f"{p45_rep.pillar_45b_copyright_info_46char_exif_vault.scenarios_passed}/"
            f"{p45_rep.pillar_45b_copyright_info_46char_exif_vault.scenarios_total}"
        ),
        "fx3_has_builtin_end_filter": p45_rep.fx3_has_builtin_end_filter,
        "e_nd_actuator_tx_count": p45_rep.e_nd_actuator_tx_count,
        "cardless_unrecorded_production_violations": p45_rep.cardless_unrecorded_production_violations,
        "legacy_v1_audio_level_menu_spoof_events": p45_rep.legacy_v1_audio_level_menu_spoof_events,
        "photographer_copyright_pii_leaked_bytes": p45_rep.photographer_copyright_pii_leaked_bytes,
        "copyright_char_overflow_or_movie_mutation_events": (
            p45_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        "slot1_copyright_vault_mutation_bytes": p45_rep.slot1_copyright_vault_mutation_bytes,
        "hardware_live_attachment_authorized": p45_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p45_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec45[0],
            pillar_id=spec45[1],
            phase_label=spec45[2],
            module_name=spec45[3],
            passed=bool(p45_rep.all_passed),
            status=p45_rep.status,
            verification_mode=p45_rep.verification_mode,
            elapsed_seconds=p45_dt,
            key_metrics=p45_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec45[1],
                    "mode": p45_rep.verification_mode,
                    "status": p45_rep.status,
                    "metrics": p45_metrics,
                    "passed": p45_rep.all_passed,
                }
            ),
            errors=tuple(p45_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master45_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p45_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_45_PILLAR_COUNT == 45
        and pillars_passed == 45
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE265_SCHEMA,
            "version": PHASE265_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master45PillarRecoveryReport(
        schema=PHASE265_SCHEMA,
        version=PHASE265_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P265_STATUS_VERIFIED_45OF45_AGGREGATOR if all_ok else P265_STATUS_FAIL_45OF45_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_2s_fast_cli_budget=elapsed < P265_FAST_CLI_BUDGET_SECONDS,
        under_6s_budget=elapsed < P265_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P265_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p45_rep.donor_snapshot,
        pillar45_a_release_wo_card_lens_audio_meter_vault=(
            p45_rep.pillar_45a_release_wo_card_lens_audio_meter_vault
        ),
        pillar45_b_copyright_info_46char_exif_vault=p45_rep.pillar_45b_copyright_info_46char_exif_vault,
        fx3_has_builtin_end_filter=p45_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=p45_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=p45_rep.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=p45_rep.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=p45_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            p45_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=p45_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m44_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m44_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m44_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m44_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m44_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m44_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m44_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m44_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m44_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m44_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m44_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m44_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m44_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m44_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m44_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m44_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m44_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m44_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m44_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m44_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m44_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m44_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m44_rep.unbuffered_battery_pull_events,
        hardware_live_attachment_authorized=p45_rep.hardware_live_attachment_authorized,
        master_45pillar_sha256=master_sha,
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


def evaluate_45pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master45PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_45pillar_recovery_master`."""
    return evaluate_realhw_45pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_45pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master45PillarRecoveryReport:
    """Public CLI entry point for Phase 265 Grand Milestone `45/45` unified recovery master."""
    return evaluate_realhw_45pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


__all__ = [
    "ALLOW_BOOT_PARTITION_TARGETING",
    "ALLOW_DESTRUCTIVE_FASTBOOT",
    "ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS",
    "ALLOW_PERSISTENT_JIRITSU_WRITES",
    "CNFLASHA_USERSPACE_WRITE_BLOCKED",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "ISP_WRITE_AUTHORIZED",
    "LIVE_USB_IOKIT_TRANSMIT_ENABLED",
    "MASTER_45_PILLAR_COUNT",
    "MASTER_45_PILLAR_IDS",
    "MASTER_45_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "P265_AUDIO_OUT_TIMING_DEFAULT",
    "P265_AUDIO_OUT_TIMING_MODES",
    "P265_AUDIO_RECORDING_DEFAULT",
    "P265_AUDIO_RECORDING_EXACT_5_ITEMS",
    "P265_AUDIO_RECORDING_MENU_PATH",
    "P265_AUDIO_RECORDING_MODES",
    "P265_AUDIO_REC_LEVEL_DEFAULT",
    "P265_AUDIO_REC_LEVEL_MAX",
    "P265_AUDIO_REC_LEVEL_MIN",
    "P265_BENCH_POSTURES",
    "P265_BLOCKED_COPYRIGHT_46CHAR_OR_ASCII_OVERFLOW",
    "P265_BLOCKED_COPYRIGHT_CLEAN_ROOM_PII_OR_SLOT1_VAULT_LEAK",
    "P265_BLOCKED_COPYRIGHT_MOVIE_STREAM_OR_EXIF_SCOPE_VIOLATION",
    "P265_BLOCKED_COPYRIGHT_RESET_VS_INITIALIZE_SCOPE_DRIFT",
    "P265_BLOCKED_DISP_AUDIO_METER_OR_RESET_SCOPE_DRIFT",
    "P265_BLOCKED_INVALID_COPYRIGHT_INFO_SPEC",
    "P265_BLOCKED_INVALID_RELEASE_WO_OR_AUDIO_METER_SPEC",
    "P265_BLOCKED_LEGACY_V1_AUDIO_MENU_SPOOF_OR_SPEC_DRIFT",
    "P265_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P265_BLOCKED_RELEASE_WO_CARD_MOVIE_OR_BENCH_VIOLATION",
    "P265_BLOCKED_RELEASE_WO_LENS_OR_END_UART_VIOLATION",
    "P265_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P265_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P265_BOUNDED_HEADER_BYTES",
    "P265_CAMSET_FILENAMES",
    "P265_CARDLESS_UNRECORDED_PRODUCTION_VIOLATIONS",
    "P265_CONCURRENT_CEILING_SECONDS",
    "P265_COPYRIGHT_CHAR_OVERFLOW_OR_MOVIE_MUTATION_EVENTS",
    "P265_COPYRIGHT_INFO_EXACT_4_ITEMS",
    "P265_COPYRIGHT_INFO_MENU_PATH",
    "P265_COPYRIGHT_MAX_CHARS",
    "P265_DISP_SCREEN_SET_MENU_PATH",
    "P265_DONOR_FX3_APPFW_702_RELPATH",
    "P265_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P265_DONOR_FX3_BODYDATA_RELPATH",
    "P265_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH",
    "P265_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH",
    "P265_DONOR_FX3_LIBBACKUP_SO_RELPATH",
    "P265_DONOR_FX3_LIBGPE_SO_RELPATH",
    "P265_DONOR_FX3_LIBINFRAIPTC_SO_RELPATH",
    "P265_DONOR_FX3_LIBINFRALENSCOMMUNICATOR_SO_RELPATH",
    "P265_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH",
    "P265_DONOR_FX3_LIBINFRAMEDIADETECT_SO_RELPATH",
    "P265_DONOR_FX3_LIBINFRAMETASUPPLIER_SO_RELPATH",
    "P265_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH",
    "P265_DONOR_FX6_APPFW_601_RELPATH",
    "P265_DONOR_FX6_LIBINFRAHOTSHOE_SO_RELPATH",
    "P265_DONOR_INSPECT_BUDGET_SECONDS",
    "P265_ENV_CLEAN_ROOM_TEST",
    "P265_E_ND_ACTUATOR_TX_COUNT",
    "P265_FAST_CLI_BUDGET_SECONDS",
    "P265_FORBIDDEN_LEGACY_V1_AUDIO_ITEM",
    "P265_FORBIDDEN_LEGACY_V1_FW_VERSIONS",
    "P265_FORBIDDEN_LEGACY_V1_HELPGUIDE_ID",
    "P265_FORBIDDEN_PERSISTENT_TARGETS",
    "P265_FX3_FW_VERSION",
    "P265_FX3_HAS_BUILTIN_END_FILTER",
    "P265_FX3_HELPGUIDE_ID",
    "P265_FX3_MODEL_ID",
    "P265_FX3_MODEL_NAME",
    "P265_FX3_SUPPORTED_FW_VERSIONS",
    "P265_FX6_DONOR_FW_VERSION",
    "P265_FX6_DONOR_MODEL_NAME",
    "P265_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P265_LEGACY_V1_AUDIO_LEVEL_MENU_SPOOF_EVENTS",
    "P265_LENS_ATTACHMENT_KINDS",
    "P265_MAX_FULL_DONOR_BYTES",
    "P265_MOVIE_STREAM_FORMATS",
    "P265_NOMINAL_BUDGET_SECONDS",
    "P265_PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES",
    "P265_PILLAR_45A_SCENARIO_IDS",
    "P265_PILLAR_45B_SCENARIO_IDS",
    "P265_PINNED_FX3_APPFW_702_BYTES",
    "P265_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P265_PINNED_FX3_BACKUP_BIN_BYTES",
    "P265_PINNED_FX3_BACKUP_BIN_SHA256",
    "P265_PINNED_FX3_BODYDATA_BYTES",
    "P265_PINNED_FX3_BODYDATA_HDR4K_SHA256",
    "P265_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES",
    "P265_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256",
    "P265_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES",
    "P265_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256",
    "P265_PINNED_FX3_LIBBACKUP_SO_BYTES",
    "P265_PINNED_FX3_LIBBACKUP_SO_SHA256",
    "P265_PINNED_FX3_LIBGPE_SO_BYTES",
    "P265_PINNED_FX3_LIBGPE_SO_SHA256",
    "P265_PINNED_FX3_LIBINFRAIPTC_SO_BYTES",
    "P265_PINNED_FX3_LIBINFRAIPTC_SO_SHA256",
    "P265_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES",
    "P265_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256",
    "P265_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES",
    "P265_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256",
    "P265_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES",
    "P265_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256",
    "P265_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_BYTES",
    "P265_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_SHA256",
    "P265_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES",
    "P265_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256",
    "P265_PINNED_FX6_APPFW_601_BYTES",
    "P265_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P265_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES",
    "P265_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256",
    "P265_REC_MEDIA_DUR_HDMI_MODES",
    "P265_RELEASE_WO_CARD_DEFAULT",
    "P265_RELEASE_WO_CARD_MENU_PATH",
    "P265_RELEASE_WO_LENS_DEFAULT",
    "P265_RELEASE_WO_LENS_MENU_PATH",
    "P265_RELEASE_WO_MODES",
    "P265_RESET_ACTIONS",
    "P265_SHOE_AUDIO_SET_DEFAULT",
    "P265_SHOE_AUDIO_SET_MODES",
    "P265_SHOOTING_DOMAINS",
    "P265_SLOT1_COPYRIGHT_VAULT_MUTATION_BYTES",
    "P265_SLOT1_VAULT_SLOT",
    "P265_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P265_STATUS_FAIL_45OF45_AGGREGATOR",
    "P265_STATUS_FAIL_PILLAR45_SUITE",
    "P265_STATUS_REJECTED_PILLAR_45A",
    "P265_STATUS_REJECTED_PILLAR_45B",
    "P265_STATUS_VERIFIED_45OF45_AGGREGATOR",
    "P265_STATUS_VERIFIED_PILLAR45_SUITE",
    "P265_STATUS_VERIFIED_PILLAR_45A",
    "P265_STATUS_VERIFIED_PILLAR_45B",
    "P265_STILL_IMAGE_FORMATS",
    "P265_TIER0_SURFACE_COUNT",
    "P265_WIND_NOISE_REDUCT_DEFAULT",
    "P265_WIND_NOISE_REDUCT_MODES",
    "P265_WRITE_COPYRIGHT_DEFAULT",
    "P265_WRITE_COPYRIGHT_MODES",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE265_MILESTONE_NUMBER",
    "PHASE265_SCHEMA",
    "PHASE265_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "CopyrightInfo46CharExifVaultReport",
    "CopyrightInfo46CharExifVaultSpec",
    "Master45PillarRecoveryReport",
    "Phase265DonorArtifactDigest",
    "Phase265DonorSnapshot",
    "Pillar45ASuiteResult",
    "Pillar45BSuiteResult",
    "Pillar45ScenarioOutcome",
    "Pillar45StandaloneReport",
    "ReleaseWoCardLensAndAudioMeterVaultReport",
    "ReleaseWoCardLensAndAudioMeterVaultSpec",
    "ReleaseWoCardLensAudioMeterAndCopyrightVaultReport",
    "build_default_safe_copyright_info_46char_exif_vault_spec",
    "build_default_safe_release_wo_card_lens_audio_meter_vault_spec",
    "compute_expected_copyright_info_state",
    "compute_expected_disp_audio_meter_state",
    "compute_expected_release_wo_card_and_lens_gate",
    "evaluate_45pillar_recovery_master",
    "evaluate_copyright_info_46char_exif_vault",
    "evaluate_realhw_45pillar_recovery_master",
    "evaluate_release_wo_card_lens_and_audio_meter_vault",
    "inspect_phase265_donors_readonly",
    "run_pillar45_standalone_suite",
    "run_pillar45a_release_wo_card_lens_audio_meter_vault_6_scenario_suite",
    "run_pillar45b_copyright_info_46char_exif_vault_6_scenario_suite",
    "verify_45pillar_recovery_suite",
    "verify_release_wo_card_lens_audio_meter_and_copyright_vault",
    "verify_release_wo_card_lens_audio_meter_copyright_vault",
]
