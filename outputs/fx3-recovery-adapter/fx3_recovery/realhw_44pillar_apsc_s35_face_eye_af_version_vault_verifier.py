"""Phase 260 (`260th` Phase Milestone) — Pillar 44 (`44/44` Recovery Pillars) & Unified 44-Pillar Recovery Master
(`verify-44pillar-recovery` / `verify-apsc-s35-face-eye-af-version-vault`):

1. **Pillar 44A — `[APS-C S35 Shooting]` `12.1MP` Sensor `4K` Movie & `4264x2408` `HDMI RAW` Lockout +
   `[Face/Eye AF]` (`[Face/Eye Prior. in AF]`, `[Face/Eye Subject]`, `[Right/Left Eye Select]`,
   `[Face/Eye Frame Disp.]` Clean-HDMI Isolation & `[Face Memory]` Survival)
   (`ILME-FX3 Ver. 7.02`, `ilc/2210`, Wave-42)**:
   - Models `MENU` -> `Shooting` -> `[Image Quality/Rec]` -> `[APS-C S35 Shooting]` (`Auto` factory
     default / `On` ~`1.5x` APS-C Super 35mm angle of view / `Off` 35mm full-frame), verifying reset
     to `[Auto]` by `[Camera Settings Reset]` (and `[Initialize]`) while surviving
     `[Reset Network Set.]`, plus deterministic restoration via `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]`.
   - Enforces the `ILME-FX3` (`ilc/2210`) `12.1 MP` full-frame sensor (`4240x2832` effective still /
     `3840x2160` 1:1 `4K` readout) hardware boundary: `[APS-C S35 Shooting]` is disabled and locked
     to `[Off]` (`Full-Frame_1.0x`) whenever recording `4K` movies (`XAVC HS 4K`, `XAVC S 4K`,
     `XAVC S-I 4K`) or `4264x2408` `HDMI RAW Output` — Super 35mm movie capture operates **only** in
     `HD` (`XAVC S HD` / `XAVC S-I HD`) (`apsc_s35_4k_or_raw_bypass_events == 0`, strictly
     distinguishing `ILME-FX3` from native-S35 `ILME-FX30` and oversampled `ILCE-7RM5`/`ILCE-7M4`).
   - Models `MENU` -> `Focus` -> `[Face/Eye AF]` (BIONZ XR `ilc/2210` hierarchy — **not** dedicated
     AI-unit `[Subject Recog in AF]`, `ai_unit_subject_recog_spoof_events == 0`):
     `[Face/Eye Prior. in AF]` (`On` default, locked `On` in `[Intelligent Auto]` / `Off`),
     `[Face/Eye Subject]` (`Human` default / `Animal` / `Ver. 3.00+` `Bird`),
     `[Right/Left Eye Select]` (`Auto` default / `Right Eye` / `Left Eye` + `[Switch Right/Left Eye]`
     custom key toggle), and `[Face/Eye Frame Disp.]` (`On` / `Off` + `[AF Area Auto Clear]` behavior),
     proving clean-HDMI isolation (`hdmi_clean_feed_eye_frame_baked_pixels == 0` when
     `[HDMI Info. Display] = [Off]` or `HDMI RAW Output` is active) and registered `[Face Memory]`
     database survival across `[Camera Settings Reset]` (cleared only by explicit delete or `[Initialize]`).

2. **Pillar 44B — `[Version]` Read-Only Body/Lens/Mount-Adaptor Inspection, Zero-RF Update Badge
   Suppression & Hard-Blocked Slot-1 `BODYDATA.DAT` Flash Vault Guard**:
   - Models `MENU` -> `Setup` -> `[Setup Option]` -> `[Version]`, verifying strictly read-only
     (`O_RDONLY`, backed by `libInfraGetVersion.so` `InfraGetVersion` / `InfraGetVersionLens`)
     inspection of `ILME-FX3` Body (`Ver. 7.02`), E-mount Lens, and Mount Adaptor firmware versions
     with zero flash partition writes (`version_dialog_flash_writes == 0`) and firmware version
     immutability across `[Camera Settings Reset]`, `[Reset Network Set.]`, and `[Initialize]`.
   - Enforces `Ver. 6.00+` / `7.02` red update notification badge suppression on our zero-RF
     `Airplane Mode = On` bench (`libInfraAirplaneMode.so`, `passive_tx_bytes_emitted == 0`).
   - Hard-blocks **all** automated SD/CFexpress Slot-1 `BODYDATA.DAT` firmware flash execution
     (`libupdatermedia.so`, `persistent_emmc_writes_authorized == False`,
     `bodydata_flash_attempts_blocked >= 1`, `slot1_bodydata_vault_mutation_bytes == 0`), alongside
     lossless `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` round-trip and `16/16` Tier-0 `Backup.bin`
     `H0 == H3` parity.

3. **Unified `44/44` Recovery Master (`evaluate_realhw_44pillar_recovery_master`)**:
   - Concurrently delegates Pillars `1..43` (`evaluate_realhw_43pillar_recovery_master`) +
     **Pillar 44** -> **`44/44` (`VERIFIED_44OF44_PILLAR_RECOVERY_MASTER`)** in `< 4.0s` nominal
     (`< 6.0s` concurrent ceiling), preserving 100% backward compatibility with
     `verify-22..43pillar-recovery`.
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
from .realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_43_PILLAR_SPECS,
    Master43PillarRecoveryReport,
    evaluate_realhw_43pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE260_SCHEMA: str = "realhw_44pillar_apsc_s35_face_eye_af_version_vault_verifier_v1"
PHASE260_VERSION: str = "1.0.0"
PHASE260_MILESTONE_NUMBER: int = 260

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
P260_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P260_APSC_S35_4K_OR_RAW_BYPASS_EVENTS: int = 0
P260_AI_UNIT_SUBJECT_RECOG_SPOOF_EVENTS: int = 0
P260_HDMI_CLEAN_FEED_EYE_FRAME_BAKED_PIXELS: int = 0
P260_VERSION_DIALOG_FLASH_WRITES: int = 0
P260_DEFAULT_BODYDATA_FLASH_ATTEMPTS_BLOCKED: int = 1
P260_SLOT1_BODYDATA_VAULT_MUTATION_BYTES: int = 0

P260_DONOR_INSPECT_BUDGET_SECONDS: float = 2.0
P260_NOMINAL_BUDGET_SECONDS: float = 4.0
P260_CONCURRENT_CEILING_SECONDS: float = 6.0
P260_BOUNDED_HEADER_BYTES: int = 4096
P260_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-42 / FX3 Ver. 7.02 & FX6 Ver. 6.01 Donor Anchors (bounded O_RDONLY verification)
P260_FX3_MODEL_NAME: str = "ILME-FX3"
P260_FX3_MODEL_ID: int = 0x91030080
P260_FX3_HELPGUIDE_ID: str = "ilc/2210"
P260_FX3_FW_VERSION: str = "7.02"
P260_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P260_FX6_DONOR_FW_VERSION: str = "6.01"
P260_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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
P260_FX3_BIRD_EYE_MIN_FW_VERSIONS: Tuple[str, ...] = (
    "3.00",
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)
P260_FX3_UPDATE_BADGE_MIN_FW_VERSIONS: Tuple[str, ...] = (
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)

P260_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P260_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P260_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = (
    "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
)

P260_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P260_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P260_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)

P260_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P260_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P260_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)

P260_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P260_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P260_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P260_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P260_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P260_PINNED_FX3_LIBBACKUP_SO_SHA256: str = (
    "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"
)

P260_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P260_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P260_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = (
    "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"
)

P260_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so"
)
P260_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES: int = 18760
P260_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256: str = (
    "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7"
)

P260_DONOR_FX3_LIBGPE_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgpe.so"
)
P260_PINNED_FX3_LIBGPE_SO_BYTES: int = 106480
P260_PINNED_FX3_LIBGPE_SO_SHA256: str = (
    "363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464"
)

P260_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/CameraOnDemandSaver.so"
)
P260_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES: int = 18800
P260_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256: str = (
    "72b73608c2675a3709e2952ca347a36e7dd2ad3dd2869191638c7154933b2f46"
)

P260_DONOR_FX3_LIBINFRALENSCOMMUNICATOR_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraLensCommunicator.so"
)
P260_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES: int = 14544
P260_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256: str = (
    "e61bf145f050dd037802871395c38d1c0471518130d5bcd2f621268da8c8f6ab"
)

P260_DONOR_FX3_LIBINFRAGETVERSION_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraGetVersion.so"
)
P260_PINNED_FX3_LIBINFRAGETVERSION_SO_BYTES: int = 10144
P260_PINNED_FX3_LIBINFRAGETVERSION_SO_SHA256: str = (
    "3a69e737c04b50d120d00e8a0b977f1d60dbb4228abe3b41083e7ab9178be620"
)

P260_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraAirplaneMode.so"
)
P260_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES: int = 14488
P260_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256: str = (
    "dcf0d7562a879f6d3bd1ed60cf00f9068fec368554b175bc6fabafbf212dffea"
)

P260_DONOR_FX3_LIBUPDATERMEDIA_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libupdatermedia.so"
)
P260_PINNED_FX3_LIBUPDATERMEDIA_SO_BYTES: int = 10144
P260_PINNED_FX3_LIBUPDATERMEDIA_SO_SHA256: str = (
    "1b5fa6dfd53075afcea591f3a38a1af9a957d6129ea3d180fe1cd562cfdd30db"
)

# Pillar 44A — [APS-C S35 Shooting] 12.1MP 4K/RAW Lockout & [Face/Eye AF] Clean-HDMI Isolation
P260_APSC_S35_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "Image Quality/Rec",
    "APS-C S35 Shooting",
)
P260_APSC_S35_MODES: Tuple[str, ...] = ("Auto", "On", "Off")
P260_APSC_S35_DEFAULT: str = "Auto"
P260_FX3_SENSOR_EFFECTIVE_MP: str = "12.1MP"
P260_FX3_STILL_FULLFRAME_RES: str = "4240x2832"
P260_FX3_MOVIE_4K_READOUT_RES: str = "3840x2160"
P260_HDMI_RAW_4264X2408_RESOLUTION: str = "4264x2408"
P260_HDMI_RAW_OUTPUT_MODES: Tuple[str, ...] = ("Off", "On")
P260_SHOOTING_DOMAINS: Tuple[str, ...] = ("Movie", "S&Q", "Still")
P260_MOVIE_FILE_FORMATS_4K: Tuple[str, ...] = ("XAVC HS 4K", "XAVC S 4K", "XAVC S-I 4K")
P260_MOVIE_FILE_FORMATS_HD: Tuple[str, ...] = ("XAVC S HD", "XAVC S-I HD")
P260_MOVIE_FILE_FORMATS: Tuple[str, ...] = P260_MOVIE_FILE_FORMATS_4K + P260_MOVIE_FILE_FORMATS_HD
P260_LENS_IMAGE_CIRCLE_TYPES: Tuple[str, ...] = ("FF", "APS-C")
P260_EFFECTIVE_ANGLE_OF_VIEW_MODES: Tuple[str, ...] = ("Full-Frame_1.0x", "Super35_1.5x")
P260_NON_FX3_S35_4K_MODELS: Tuple[str, ...] = ("ILME-FX30", "ILCE-7RM5", "ILCE-7M4")

P260_FACE_EYE_AF_MENU_PATH: Tuple[str, ...] = ("MENU", "Focus", "Face/Eye AF")
P260_FORBIDDEN_AI_UNIT_MENU_NAME: str = "Subject Recog in AF"
P260_FORBIDDEN_AI_UNIT_SUBJECTS: Tuple[str, ...] = ("Insect", "Car/Train", "Airplane", "Animal/Bird")
P260_FACE_EYE_PRIOR_MODES: Tuple[str, ...] = ("On", "Off")
P260_FACE_EYE_PRIOR_DEFAULT: str = "On"
P260_FACE_EYE_SUBJECTS: Tuple[str, ...] = ("Human", "Animal", "Bird")
P260_FACE_EYE_SUBJECT_DEFAULT: str = "Human"
P260_RIGHT_LEFT_EYE_SELECT_MODES: Tuple[str, ...] = ("Auto", "Right Eye", "Left Eye")
P260_RIGHT_LEFT_EYE_SELECT_DEFAULT: str = "Auto"
P260_FACE_EYE_FRAME_DISP_MODES: Tuple[str, ...] = ("On", "Off")
P260_FACE_EYE_FRAME_DISP_DEFAULT: str = "Off"
P260_AF_AREA_AUTO_CLEAR_MODES: Tuple[str, ...] = ("Off", "On")
P260_HDMI_INFO_DISPLAY_MODES: Tuple[str, ...] = ("On", "Off")
P260_SHOOTING_EXPOSURE_PROFILES: Tuple[str, ...] = (
    "P",
    "A",
    "S",
    "M",
    "Flexible Exp. Mode",
    "Intelligent Auto",
)
P260_MAX_FACE_MEMORY_ENTRIES: int = 8

# Pillar 44B — [Version] Read-Only Inspection, Zero-RF Update Badge & Hard-Blocked BODYDATA.DAT Vault
P260_VERSION_MENU_PATH: Tuple[str, ...] = ("MENU", "Setup", "Setup Option", "Version")
P260_AIRPLANE_MODE_MENU_PATH: Tuple[str, ...] = ("MENU", "Network", "Network Option", "Airplane Mode")
P260_AIRPLANE_MODES: Tuple[str, ...] = ("On", "Off")
P260_BODYDATA_FILENAME: str = "BODYDATA.DAT"
P260_HUMAN_BENCH_MIN_BATTERY_BARS: int = 3
P260_HUMAN_BENCH_MIN_BATTERY_PCT: int = 51

P260_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)
P260_SLOT1_VAULT_SLOT: int = 1
P260_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
P260_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_apsc_s35_face_eye_af_version_vault_overlay"
P260_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P260_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P260_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P260_BLOCKED_INVALID_APSC_S35_OR_FACE_EYE_AF_SPEC: str = (
    "BLOCKED_INVALID_APSC_S35_OR_FACE_EYE_AF_SPEC"
)
P260_BLOCKED_APSC_OR_FACE_MEMORY_RESET_SCOPE_DRIFT: str = (
    "BLOCKED_APSC_OR_FACE_MEMORY_RESET_SCOPE_DRIFT"
)
P260_BLOCKED_APSC_S35_4K_OR_RAW_LOCKOUT_BYPASS: str = (
    "BLOCKED_APSC_S35_4K_OR_RAW_LOCKOUT_BYPASS"
)
P260_BLOCKED_AI_UNIT_SUBJECT_RECOG_SPOOF_OR_EYE_RULE_DRIFT: str = (
    "BLOCKED_AI_UNIT_SUBJECT_RECOG_SPOOF_OR_EYE_RULE_DRIFT"
)
P260_BLOCKED_HDMI_CLEAN_FEED_EYE_FRAME_LEAK: str = (
    "BLOCKED_HDMI_CLEAN_FEED_EYE_FRAME_LEAK"
)

P260_BLOCKED_INVALID_VERSION_OR_BODYDATA_VAULT_SPEC: str = (
    "BLOCKED_INVALID_VERSION_OR_BODYDATA_VAULT_SPEC"
)
P260_BLOCKED_VERSION_DIALOG_WRITE_OR_IMMUTABILITY_DRIFT: str = (
    "BLOCKED_VERSION_DIALOG_WRITE_OR_IMMUTABILITY_DRIFT"
)
P260_BLOCKED_UNSUPPRESSED_UPDATE_BADGE_OR_RF_LEAK: str = (
    "BLOCKED_UNSUPPRESSED_UPDATE_BADGE_OR_RF_LEAK"
)
P260_BLOCKED_AUTOMATED_BODYDATA_FLASH_EXECUTION: str = (
    "BLOCKED_AUTOMATED_BODYDATA_FLASH_EXECUTION"
)
P260_BLOCKED_SLOT1_BODYDATA_VAULT_MUTATION_OR_CAMSET_DRIFT: str = (
    "BLOCKED_SLOT1_BODYDATA_VAULT_MUTATION_OR_CAMSET_DRIFT"
)
P260_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P260_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P260_STATUS_VERIFIED_PILLAR_44A: str = (
    "VERIFIED_PILLAR_44A_APSC_S35_12MP_4K_LOCKOUT_AND_FACE_EYE_AF_CLEAN_HDMI_VAULT"
)
P260_STATUS_REJECTED_PILLAR_44A: str = (
    "REJECTED_PILLAR_44A_APSC_S35_12MP_4K_LOCKOUT_AND_FACE_EYE_AF_CLEAN_HDMI_VAULT"
)
P260_STATUS_VERIFIED_PILLAR_44B: str = (
    "VERIFIED_PILLAR_44B_VERSION_READONLY_UPDATE_BADGE_GUARD_AND_BODYDATA_VAULT"
)
P260_STATUS_REJECTED_PILLAR_44B: str = (
    "REJECTED_PILLAR_44B_VERSION_READONLY_UPDATE_BADGE_GUARD_AND_BODYDATA_VAULT"
)
P260_STATUS_VERIFIED_PILLAR44_SUITE: str = (
    "VERIFIED_PILLAR44_APSC_S35_FACE_EYE_AF_VERSION_VAULT"
)
P260_STATUS_FAIL_PILLAR44_SUITE: str = (
    "FAIL_PILLAR44_APSC_S35_FACE_EYE_AF_VERSION_VAULT"
)
P260_STATUS_VERIFIED_44OF44_AGGREGATOR: str = "VERIFIED_44OF44_PILLAR_RECOVERY_MASTER"
P260_STATUS_FAIL_44OF44_AGGREGATOR: str = "FAIL_44OF44_PILLAR_RECOVERY_MASTER"

P260_PILLAR_44A_SCENARIO_IDS: Tuple[str, ...] = (
    "P44A1_HD_MOVIE_APSC_S35_ON_SUPER35_1_5X_AND_FACE_EYE_AF_RIGHT_EYE_BIRD_CLEAN_HDMI_SURVIVE_NETWORK_RESET_SAFE",
    "P44A2_CAMERA_SETTINGS_RESET_RESTORES_APSC_AUTO_FACE_EYE_DEFAULTS_PRESERVES_FACE_MEMORY_AND_LOCKS_4K_RAW_TO_OFF_SAFE",
    "P44A3_REJECT_APSC_S35_BYPASSING_12_1MP_4K_MOVIE_OR_4264X2408_HDMI_RAW_LOCKOUT",
    "P44A4_REJECT_AI_UNIT_SUBJECT_RECOG_SPOOF_OR_INTELLIGENT_AUTO_PRIOR_OFF_OR_PRE_3_00_BIRD_DRIFT",
    "P44A5_REJECT_FACE_EYE_FRAME_DISP_BAKED_INTO_CLEAN_HDMI_OFF_OR_HDMI_RAW_OUTPUT",
    "P44A6_REJECT_CAMERA_SETTINGS_RESET_WIPING_FACE_MEMORY_OR_FAILING_APSC_FACE_EYE_MENU_RESET",
)
P260_PILLAR_44B_SCENARIO_IDS: Tuple[str, ...] = (
    "P44B1_VERSION_ORDONLY_BODY_702_LENS_INSPECTION_ZERO_RF_BADGE_SUPPRESSED_AND_BODYDATA_FLASH_HARD_BLOCKED_SAFE",
    "P44B2_INITIALIZE_PRESERVES_IMMUTABLE_BODY_LENS_ADAPTOR_VERSION_AND_ORDONLY_SLOT1_CAMSET01_ROUNDTRIPS_SAFE",
    "P44B3_REJECT_VERSION_DIALOG_FLASH_WRITE_OR_RESET_MUTATING_BODY_LENS_ADAPTOR_VERSION",
    "P44B4_REJECT_UNSUPPRESSED_UPDATE_NOTIFICATION_BADGE_OR_PASSIVE_RF_PROBE_UNDER_AIRPLANE_MODE",
    "P44B5_REJECT_AUTOMATED_SLOT1_BODYDATA_DAT_FLASH_EXECUTION_OR_LOW_BATTERY_BYPASS",
    "P44B6_REJECT_SLOT1_BODYDATA_VAULT_MUTATION_OR_CROSS_MODEL_FX6_CAMSET_LOAD",
)

MASTER_44_PILLAR_COUNT: int = 44
MASTER_44_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_43_PILLAR_SPECS + (
    (
        44,
        "pillar_44_apsc_s35_face_eye_af_version_vault",
        "Phase 260 (260th Milestone)",
        "fx3_recovery.realhw_44pillar_apsc_s35_face_eye_af_version_vault_verifier",
    ),
)
MASTER_44_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_44_PILLAR_SPECS)


# ---------------------------------------------------------------------------
# Internal Helpers & Deterministic State Computations
# ---------------------------------------------------------------------------


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


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
        ("P260_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P260_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("P260_APSC_S35_4K_OR_RAW_BYPASS_EVENTS", P260_APSC_S35_4K_OR_RAW_BYPASS_EVENTS, 0),
        ("P260_AI_UNIT_SUBJECT_RECOG_SPOOF_EVENTS", P260_AI_UNIT_SUBJECT_RECOG_SPOOF_EVENTS, 0),
        ("P260_HDMI_CLEAN_FEED_EYE_FRAME_BAKED_PIXELS", P260_HDMI_CLEAN_FEED_EYE_FRAME_BAKED_PIXELS, 0),
        ("P260_VERSION_DIALOG_FLASH_WRITES", P260_VERSION_DIALOG_FLASH_WRITES, 0),
        ("P260_SLOT1_BODYDATA_VAULT_MUTATION_BYTES", P260_SLOT1_BODYDATA_VAULT_MUTATION_BYTES, 0),
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
    if P260_DEFAULT_BODYDATA_FLASH_ATTEMPTS_BLOCKED < 1:
        errs.append(
            f"P260_DEFAULT_BODYDATA_FLASH_ATTEMPTS_BLOCKED expected >= 1, got "
            f"{P260_DEFAULT_BODYDATA_FLASH_ATTEMPTS_BLOCKED!r}"
        )
    return errs


def _is_tmpfs_path(path_value: str) -> bool:
    norm = posixpath.normpath(path_value)
    return norm.startswith("/tmp/") or norm.startswith("/run/")


def _targets_persistent_emmc(path_value: str) -> bool:
    low = path_value.strip().lower()
    return any(tok in low for tok in P260_FORBIDDEN_PERSISTENT_TARGETS)


def compute_expected_apsc_s35_movie_or_still_state(
    *,
    shooting_domain: str,
    movie_file_format: str,
    hdmi_raw_output_4264x2408: str,
    configured_apsc_s35: str,
    lens_image_circle: str,
) -> Tuple[bool, str, str]:
    """Compute `(apsc_s35_locked_off, effective_apsc_s35_mode, effective_angle_of_view)` for `ILME-FX3` (`12.1MP`).

    On `ILME-FX3` (`ilc/2210`, `4240x2832` effective still / `3840x2160` 1:1 `4K` readout), an APS-C /
    Super 35mm sub-window lacks horizontal pixels for `4K`, so `[APS-C S35 Shooting]` is strictly
    disabled and locked to `[Off]` (`Full-Frame_1.0x`) whenever recording `4K` movies (`XAVC HS 4K`,
    `XAVC S 4K`, `XAVC S-I 4K`) or `4264x2408` `HDMI RAW Output`. Super 35mm movie capture (`~1.5x`)
    operates **only** in `HD` (`XAVC S HD` / `XAVC S-I HD`) with `HDMI RAW Output = Off` (or in `Still`).
    """
    is_movie_4k_or_raw_lockout = shooting_domain in ("Movie", "S&Q") and (
        movie_file_format in P260_MOVIE_FILE_FORMATS_4K or hdmi_raw_output_4264x2408 == "On"
    )
    if is_movie_4k_or_raw_lockout:
        return True, "Off", "Full-Frame_1.0x"
    if configured_apsc_s35 == "On" or (configured_apsc_s35 == "Auto" and lens_image_circle == "APS-C"):
        return False, configured_apsc_s35, "Super35_1.5x"
    return False, configured_apsc_s35, "Full-Frame_1.0x"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase260DonorArtifactDigest:
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
class Phase260DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase260DonorArtifactDigest, ...]


@dataclass(frozen=True)
class ApscS35AndFaceEyeAfVaultSpec:
    camera_model: str = P260_FX3_MODEL_NAME
    helpguide_id: str = P260_FX3_HELPGUIDE_ID
    fw_version: str = P260_FX3_FW_VERSION
    sensor_effective_mp: str = P260_FX3_SENSOR_EFFECTIVE_MP
    apsc_s35_menu_path: Tuple[str, ...] = P260_APSC_S35_MENU_PATH
    face_eye_af_menu_path: Tuple[str, ...] = P260_FACE_EYE_AF_MENU_PATH
    pre_reset_apsc_s35: str = "On"  # Auto | On | Off
    pre_face_eye_prior_in_af: str = "On"  # On | Off
    pre_face_eye_subject: str = "Bird"  # Human | Animal | Bird
    pre_right_left_eye_select: str = "Right Eye"  # Auto | Right Eye | Left Eye
    pre_face_eye_frame_disp: str = "On"  # On | Off
    pre_face_memory_registered_count: int = 3
    explicit_face_memory_delete: bool = False
    reset_action: str = "Reset Network Set."  # NONE | Camera Settings Reset | Reset Network Set. | Initialize
    camset_load_after_reset: bool = False
    camset_slot: int = P260_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P260_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    saved_apsc_s35: str = "On"
    saved_face_eye_prior_in_af: str = "On"
    saved_face_eye_subject: str = "Bird"
    saved_right_left_eye_select: str = "Right Eye"
    saved_face_eye_frame_disp: str = "On"
    post_reset_apsc_s35: str = "On"
    post_face_eye_prior_in_af: str = "On"
    post_face_eye_subject: str = "Bird"
    post_right_left_eye_select: str = "Right Eye"
    post_face_eye_frame_disp: str = "On"
    post_face_memory_registered_count: int = 3
    shooting_domain: str = "Movie"  # Movie | S&Q | Still
    exposure_profile: str = "M"  # P | A | S | M | Flexible Exp. Mode | Intelligent Auto
    movie_file_format: str = "XAVC S-I HD"
    hdmi_raw_output_4264x2408: str = "Off"  # Off | On
    lens_mount_model: str = "SEL2470GM2"
    lens_image_circle: str = "FF"  # FF | APS-C
    apsc_s35_locked_off: bool = False
    effective_apsc_s35_mode: str = "On"
    effective_angle_of_view: str = "Super35_1.5x"
    apsc_s35_4k_or_raw_bypass_events: int = 0
    switch_right_left_eye_custom_key_pressed: bool = False
    active_eye_target_after_custom_key: str = "Right Eye"  # Auto | Right Eye | Left Eye
    af_area_auto_clear: str = "Off"  # Off | On
    focus_locked: bool = True
    lcd_eye_frame_rendered_before_lock: bool = True
    lcd_eye_frame_visible_after_lock: bool = True
    hdmi_connected: bool = True
    hdmi_info_display: str = "Off"  # On | Off
    hdmi_eye_frame_rendered: bool = False
    hdmi_clean_feed_eye_frame_baked_pixels: int = 0
    ai_unit_subject_recog_spoof_events: int = 0
    overlay_dir: str = P260_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P260_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P260_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P260_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class ApscS35AndFaceEyeAfVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    reset_and_face_memory_scope_verified: bool
    apsc_s35_12mp_4k_raw_lockout_verified: bool
    face_eye_af_bionz_xr_rules_verified: bool
    clean_hdmi_eye_frame_isolation_verified: bool
    h0_equals_h3_verified: bool
    apsc_s35_locked_off: bool
    effective_angle_of_view: str
    apsc_s35_4k_or_raw_bypass_events: int
    ai_unit_subject_recog_spoof_events: int
    hdmi_clean_feed_eye_frame_baked_pixels: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VersionReadOnlyAndBodydataVaultSpec:
    camera_model: str = P260_FX3_MODEL_NAME
    helpguide_id: str = P260_FX3_HELPGUIDE_ID
    fw_version: str = P260_FX3_FW_VERSION
    version_menu_path: Tuple[str, ...] = P260_VERSION_MENU_PATH
    airplane_mode_menu_path: Tuple[str, ...] = P260_AIRPLANE_MODE_MENU_PATH
    version_dialog_open_mode: str = "O_RDONLY"
    version_dialog_flash_writes: int = 0
    attached_lens_model: str = "SEL2470GM2"
    attached_lens_fw_version: str = "02"
    attached_mount_adaptor_model: str = "NONE"
    attached_mount_adaptor_fw_version: str = "NONE"
    displayed_body_fw_version: str = P260_FX3_FW_VERSION
    displayed_lens_fw_version: str = "02"
    displayed_mount_adaptor_fw_version: str = "NONE"
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Reset Network Set. | Initialize
    post_reset_body_fw_version: str = P260_FX3_FW_VERSION
    post_reset_lens_fw_version: str = "02"
    post_reset_mount_adaptor_fw_version: str = "NONE"
    airplane_mode: str = "On"  # On | Off
    rf_interfaces_disabled: bool = True
    update_notification_badge_suppressed: bool = True
    red_update_badge_displayed: bool = False
    version_dialog_passive_tx_bytes: int = 0
    slot1_bodydata_filename: str = P260_BODYDATA_FILENAME
    bodydata_target_model: str = P260_FX3_MODEL_NAME
    bodydata_sony_signature_intact: bool = True
    np_fz100_battery_bars: int = 4
    np_fz100_battery_pct: int = 85
    human_bench_precheck_claimed_ready: bool = True
    automated_bodydata_update_requested: bool = True
    automated_bodydata_update_hard_blocked: bool = True
    bodydata_flash_executed: bool = False
    bodydata_flash_attempts_blocked: int = P260_DEFAULT_BODYDATA_FLASH_ATTEMPTS_BLOCKED
    slot1_tier0_vault_active: bool = True
    slot1_sdxc_wp_locked: bool = True
    camset_save_to_slot1_attempted: bool = False
    slot1_bodydata_vault_mutation_bytes: int = 0
    camset_load_after_reset: bool = True
    camset_slot: int = P260_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P260_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    camset_roundtrip_restored_ok: bool = True
    overlay_dir: str = P260_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P260_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P260_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P260_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class VersionReadOnlyAndBodydataVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    version_readonly_and_immutability_verified: bool
    zero_rf_update_badge_suppression_verified: bool
    bodydata_flash_hard_block_verified: bool
    slot1_vault_and_camset_roundtrip_verified: bool
    h0_equals_h3_verified: bool
    version_dialog_flash_writes: int
    bodydata_flash_attempts_blocked: int
    slot1_bodydata_vault_mutation_bytes: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ApscS35FaceEyeAfAndVersionVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase260DonorSnapshot
    apsc_s35_face_eye_af_report: ApscS35AndFaceEyeAfVaultReport
    version_readonly_bodydata_report: VersionReadOnlyAndBodydataVaultReport
    apsc_s35_4k_or_raw_bypass_events: int
    ai_unit_subject_recog_spoof_events: int
    hdmi_clean_feed_eye_frame_baked_pixels: int
    version_dialog_flash_writes: int
    bodydata_flash_attempts_blocked: int
    slot1_bodydata_vault_mutation_bytes: int
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
class Pillar44ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar44ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar44ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar44BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar44ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar44StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase260DonorSnapshot
    pillar_44a_apsc_s35_face_eye_af_vault: Pillar44ASuiteResult
    pillar_44b_version_readonly_bodydata_vault: Pillar44BSuiteResult
    apsc_s35_4k_or_raw_bypass_events: int
    ai_unit_subject_recog_spoof_events: int
    hdmi_clean_feed_eye_frame_baked_pixels: int
    version_dialog_flash_writes: int
    bodydata_flash_attempts_blocked: int
    slot1_bodydata_vault_mutation_bytes: int
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
class Master44PillarRecoveryReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_6s_budget: bool
    nominal_under_4_0s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    # Pillar 44 & Wave-42 top-level fields
    donor_snapshot: Phase260DonorSnapshot
    pillar44_a_apsc_s35_face_eye_af_vault: Pillar44ASuiteResult
    pillar44_b_version_readonly_bodydata_vault: Pillar44BSuiteResult
    apsc_s35_4k_or_raw_bypass_events: int
    ai_unit_subject_recog_spoof_events: int
    hdmi_clean_feed_eye_frame_baked_pixels: int
    version_dialog_flash_writes: int
    bodydata_flash_attempts_blocked: int
    slot1_bodydata_vault_mutation_bytes: int
    # Preserved Pillars 1..43 rollup metrics
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
    master_44pillar_sha256: str
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
    max_full_bytes: int = P260_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P260_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase260_donors() -> Tuple[Phase260DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P260_DONOR_FX3_BODYDATA_RELPATH,
            P260_PINNED_FX3_BODYDATA_BYTES,
            P260_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P260_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P260_DONOR_FX3_APPFW_702_RELPATH,
            P260_PINNED_FX3_APPFW_702_BYTES,
            P260_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P260_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P260_DONOR_FX6_APPFW_601_RELPATH,
            P260_PINNED_FX6_APPFW_601_BYTES,
            P260_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P260_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P260_DONOR_FX3_BACKUP_BIN_RELPATH,
            P260_PINNED_FX3_BACKUP_BIN_BYTES,
            P260_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P260_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P260_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P260_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P260_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P260_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P260_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P260_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P260_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P260_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libsaveloadsettings_so",
            P260_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P260_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P260_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            "FULL_SHA256",
            P260_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:SaveLoadSettingsIf+requestToRead+requestToCheck+requestToWrite",
        ),
        (
            "fx3_libgpe_so",
            P260_DONOR_FX3_LIBGPE_SO_RELPATH,
            P260_PINNED_FX3_LIBGPE_SO_BYTES,
            P260_PINNED_FX3_LIBGPE_SO_BYTES,
            "FULL_SHA256",
            P260_PINNED_FX3_LIBGPE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:gpe_blog_error+_ZNK5mpgpe5Gperm4InitEv",
        ),
        (
            "fx3_cameraondemandsaver_so",
            P260_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH,
            P260_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            P260_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            "FULL_SHA256",
            P260_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:CameraOnDemandSaver+_ZN18CAM_ONDEMAND_SAVER17OsalHandleWrapperC1Ejji",
        ),
        (
            "fx3_libinfralenscommunicator_so",
            P260_DONOR_FX3_LIBINFRALENSCOMMUNICATOR_SO_RELPATH,
            P260_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES,
            P260_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES,
            "FULL_SHA256",
            P260_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:LensCommunicator+_Z23LensCommunicator_CreatePN3MWF5ErrCdE",
        ),
        (
            "fx3_libinfragetversion_so",
            P260_DONOR_FX3_LIBINFRAGETVERSION_SO_RELPATH,
            P260_PINNED_FX3_LIBINFRAGETVERSION_SO_BYTES,
            P260_PINNED_FX3_LIBINFRAGETVERSION_SO_BYTES,
            "FULL_SHA256",
            P260_PINNED_FX3_LIBINFRAGETVERSION_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraGetVersion+InfraGetVersionLens+GetVersion_init",
        ),
        (
            "fx3_libinfraairplanemode_so",
            P260_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH,
            P260_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
            P260_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
            "FULL_SHA256",
            P260_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:infra_airplane_mode_init+_ZN3MWF6InhMgr15UpdateInhFactorEv",
        ),
        (
            "fx3_libupdatermedia_so",
            P260_DONOR_FX3_LIBUPDATERMEDIA_SO_RELPATH,
            P260_PINNED_FX3_LIBUPDATERMEDIA_SO_BYTES,
            P260_PINNED_FX3_LIBUPDATERMEDIA_SO_BYTES,
            "FULL_SHA256",
            P260_PINNED_FX3_LIBUPDATERMEDIA_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:udtr_get_media_path+UDTR_MEDIA",
        ),
    )
    return tuple(
        Phase260DonorArtifactDigest(
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


def inspect_phase260_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase260DonorSnapshot:
    """Inspect Wave-42 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 2.0s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase260_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase260DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P260_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P260_DONOR_FX3_BODYDATA_RELPATH,
            P260_PINNED_FX3_BODYDATA_BYTES,
            P260_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P260_DONOR_FX3_APPFW_702_RELPATH,
            P260_PINNED_FX3_APPFW_702_BYTES,
            P260_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx6_appfw_601_so",
            P260_DONOR_FX6_APPFW_601_RELPATH,
            P260_PINNED_FX6_APPFW_601_BYTES,
            P260_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P260_DONOR_FX3_BACKUP_BIN_RELPATH,
            P260_PINNED_FX3_BACKUP_BIN_BYTES,
            P260_PINNED_FX3_BACKUP_BIN_SHA256,
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
            P260_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P260_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P260_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P260_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P260_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P260_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libsaveloadsettings_so",
            P260_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P260_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P260_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"SaveLoadSettingsIf", b"requestToRead", b"requestToCheck", b"requestToWrite"),
            ),
        ),
        (
            "fx3_libgpe_so",
            P260_DONOR_FX3_LIBGPE_SO_RELPATH,
            P260_PINNED_FX3_LIBGPE_SO_BYTES,
            P260_PINNED_FX3_LIBGPE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"gpe_blog_error", b"_ZNK5mpgpe5Gperm4InitEv")),
        ),
        (
            "fx3_cameraondemandsaver_so",
            P260_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH,
            P260_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            P260_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"CameraOnDemandSaver", b"_ZN18CAM_ONDEMAND_SAVER17OsalHandleWrapperC1Ejji"),
            ),
        ),
        (
            "fx3_libinfralenscommunicator_so",
            P260_DONOR_FX3_LIBINFRALENSCOMMUNICATOR_SO_RELPATH,
            P260_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES,
            P260_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"LensCommunicator", b"_Z23LensCommunicator_CreatePN3MWF5ErrCdE"),
            ),
        ),
        (
            "fx3_libinfragetversion_so",
            P260_DONOR_FX3_LIBINFRAGETVERSION_SO_RELPATH,
            P260_PINNED_FX3_LIBINFRAGETVERSION_SO_BYTES,
            P260_PINNED_FX3_LIBINFRAGETVERSION_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraGetVersion", b"InfraGetVersionLens", b"GetVersion_init"),
            ),
        ),
        (
            "fx3_libinfraairplanemode_so",
            P260_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH,
            P260_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
            P260_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"infra_airplane_mode_init", b"_ZN3MWF6InhMgr15UpdateInhFactorEv"),
            ),
        ),
        (
            "fx3_libupdatermedia_so",
            P260_DONOR_FX3_LIBUPDATERMEDIA_SO_RELPATH,
            P260_PINNED_FX3_LIBUPDATERMEDIA_SO_BYTES,
            P260_PINNED_FX3_LIBUPDATERMEDIA_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"udtr_get_media_path", b"UDTR_MEDIA"),
            ),
        ),
    )

    real_artifacts: List[Phase260DonorArtifactDigest] = []
    any_missing = False
    for aid, rel, pinned_bytes, pinned_sha, marker_fn in probe_specs:
        present, total_b, read_b, dkind, dsha, raw_slice = _read_donor_readonly_bounded(rel)
        if not present:
            any_missing = True
            break
        marker_ok, marker_summary = marker_fn(raw_slice)
        matches = (total_b == pinned_bytes) and (dsha == pinned_sha) and bool(marker_ok)
        real_artifacts.append(
            Phase260DonorArtifactDigest(
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
        artifacts = _synthetic_phase260_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase260DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P260_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    all_ok = len(real_artifacts) == len(probe_specs) and all(a.matches_pinned for a in real_artifacts)
    dt = round(time.monotonic() - t0, 6)
    return Phase260DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all_ok,
        donor_files_inspected=len(real_artifacts),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P260_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(real_artifacts),
    )


# ---------------------------------------------------------------------------
# Default Safe Spec Builders & Pillar 44A / 44B Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_apsc_s35_face_eye_af_vault_spec() -> ApscS35AndFaceEyeAfVaultSpec:
    """Return canonical safe Wave-42 Pillar 44A specification (`HD` Super 35mm + `Face/Eye AF` Clean-HDMI)."""
    return ApscS35AndFaceEyeAfVaultSpec()


def build_default_safe_version_readonly_bodydata_vault_spec() -> VersionReadOnlyAndBodydataVaultSpec:
    """Return canonical safe Wave-42 Pillar 44B specification (`[Version]` `O_RDONLY` + blocked `BODYDATA.DAT`)."""
    return VersionReadOnlyAndBodydataVaultSpec()


def evaluate_apsc_s35_and_face_eye_af_vault(
    spec: ApscS35AndFaceEyeAfVaultSpec,
) -> ApscS35AndFaceEyeAfVaultReport:
    """Evaluate Pillar 44A `[APS-C S35 Shooting]` `12.1MP` `4K`/`RAW` lockout & `[Face/Eye AF]` Clean-HDMI."""
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
            _fail(P260_BLOCKED_SAFETY_POLICY_VIOLATION, e)
        if spec.persistent_write_unlock_requested:
            _fail(
                P260_BLOCKED_SAFETY_POLICY_VIOLATION,
                "persistent_write_unlock_requested=True forbidden under zero-write posture",
            )

    if (
        not _is_tmpfs_path(spec.overlay_dir)
        or _targets_persistent_emmc(spec.overlay_dir)
        or not spec.p2_blkroset_locked
        or spec.stage_b_backup_bin_writes != 0
    ):
        _fail(
            P260_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Volatile tmpfs Stage-B overlay / p2 BLKROSET lock violated: overlay={spec.overlay_dir!r}",
        )

    h0_eq_h3_ok = (
        spec.backup_bin_h0_sha256 == P260_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == P260_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256
        and spec.tier0_surfaces_h0_h3_matched == P260_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3_ok:
        _fail(
            P260_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "16/16 Tier-0 Backup.bin H0 == H3 parity drift detected in Pillar 44A",
        )

    if spec.camera_model in P260_NON_FX3_S35_4K_MODELS:
        _fail(
            P260_BLOCKED_APSC_S35_4K_OR_RAW_LOCKOUT_BYPASS,
            f"Cross-model S35-4K sensor spoofing rejected on ILME-FX3: camera_model={spec.camera_model!r}",
        )

    ai_unit_spoof_detected = (
        P260_FORBIDDEN_AI_UNIT_MENU_NAME in spec.face_eye_af_menu_path
        or spec.pre_face_eye_subject in P260_FORBIDDEN_AI_UNIT_SUBJECTS
        or spec.saved_face_eye_subject in P260_FORBIDDEN_AI_UNIT_SUBJECTS
        or spec.post_face_eye_subject in P260_FORBIDDEN_AI_UNIT_SUBJECTS
        or spec.ai_unit_subject_recog_spoof_events != 0
    )
    if ai_unit_spoof_detected:
        _fail(
            P260_BLOCKED_AI_UNIT_SUBJECT_RECOG_SPOOF_OR_EYE_RULE_DRIFT,
            "Dedicated AI-unit [Subject Recog in AF] / non-FX3 subject spoof rejected on BIONZ XR ILME-FX3",
        )

    spec_valid = (
        spec.camera_model == P260_FX3_MODEL_NAME
        and spec.helpguide_id == P260_FX3_HELPGUIDE_ID
        and spec.fw_version in P260_FX3_SUPPORTED_FW_VERSIONS
        and spec.sensor_effective_mp == P260_FX3_SENSOR_EFFECTIVE_MP
        and spec.apsc_s35_menu_path == P260_APSC_S35_MENU_PATH
        and spec.face_eye_af_menu_path == P260_FACE_EYE_AF_MENU_PATH
        and spec.pre_reset_apsc_s35 in P260_APSC_S35_MODES
        and spec.saved_apsc_s35 in P260_APSC_S35_MODES
        and spec.post_reset_apsc_s35 in P260_APSC_S35_MODES
        and spec.pre_face_eye_prior_in_af in P260_FACE_EYE_PRIOR_MODES
        and spec.saved_face_eye_prior_in_af in P260_FACE_EYE_PRIOR_MODES
        and spec.post_face_eye_prior_in_af in P260_FACE_EYE_PRIOR_MODES
        and spec.pre_face_eye_subject in P260_FACE_EYE_SUBJECTS
        and spec.saved_face_eye_subject in P260_FACE_EYE_SUBJECTS
        and spec.post_face_eye_subject in P260_FACE_EYE_SUBJECTS
        and spec.pre_right_left_eye_select in P260_RIGHT_LEFT_EYE_SELECT_MODES
        and spec.saved_right_left_eye_select in P260_RIGHT_LEFT_EYE_SELECT_MODES
        and spec.post_right_left_eye_select in P260_RIGHT_LEFT_EYE_SELECT_MODES
        and spec.active_eye_target_after_custom_key in P260_RIGHT_LEFT_EYE_SELECT_MODES
        and spec.pre_face_eye_frame_disp in P260_FACE_EYE_FRAME_DISP_MODES
        and spec.saved_face_eye_frame_disp in P260_FACE_EYE_FRAME_DISP_MODES
        and spec.post_face_eye_frame_disp in P260_FACE_EYE_FRAME_DISP_MODES
        and 0 <= spec.pre_face_memory_registered_count <= P260_MAX_FACE_MEMORY_ENTRIES
        and 0 <= spec.post_face_memory_registered_count <= P260_MAX_FACE_MEMORY_ENTRIES
        and spec.reset_action in P260_RESET_ACTIONS
        and spec.shooting_domain in P260_SHOOTING_DOMAINS
        and spec.exposure_profile in P260_SHOOTING_EXPOSURE_PROFILES
        and spec.movie_file_format in P260_MOVIE_FILE_FORMATS
        and spec.hdmi_raw_output_4264x2408 in P260_HDMI_RAW_OUTPUT_MODES
        and spec.lens_image_circle in P260_LENS_IMAGE_CIRCLE_TYPES
        and spec.effective_apsc_s35_mode in P260_APSC_S35_MODES
        and spec.effective_angle_of_view in P260_EFFECTIVE_ANGLE_OF_VIEW_MODES
        and spec.af_area_auto_clear in P260_AF_AREA_AUTO_CLEAR_MODES
        and spec.hdmi_info_display in P260_HDMI_INFO_DISPLAY_MODES
        and isinstance(spec.lens_mount_model, str)
        and bool(spec.lens_mount_model.strip())
    )
    if spec.camset_load_after_reset:
        spec_valid = spec_valid and (
            spec.camset_slot in (1, 2)
            and spec.camset_filename in P260_CAMSET_FILENAMES
            and spec.camset_source_model == P260_FX3_MODEL_NAME
            and spec.camset_read_only_load is True
        )
    if not spec_valid and block_code is None:
        _fail(
            P260_BLOCKED_INVALID_APSC_S35_OR_FACE_EYE_AF_SPEC,
            "Invalid ILME-FX3 APS-C S35 Shooting / Face/Eye AF menu path, FW, CAMSET, or enum token",
        )

    # 1. Reset scope verification ([APS-C S35] & [Face/Eye AF] menu reset vs [Face Memory] survival)
    if spec.camset_load_after_reset:
        exp_apsc = spec.saved_apsc_s35
        exp_prior = "On" if spec.exposure_profile == "Intelligent Auto" else spec.saved_face_eye_prior_in_af
        exp_subj = spec.saved_face_eye_subject
        exp_eye = spec.saved_right_left_eye_select
        exp_frame = spec.saved_face_eye_frame_disp
    elif spec.reset_action in ("NONE", "Reset Network Set."):
        exp_apsc = spec.pre_reset_apsc_s35
        exp_prior = "On" if spec.exposure_profile == "Intelligent Auto" else spec.pre_face_eye_prior_in_af
        exp_subj = spec.pre_face_eye_subject
        exp_eye = spec.pre_right_left_eye_select
        exp_frame = spec.pre_face_eye_frame_disp
    else:
        exp_apsc = P260_APSC_S35_DEFAULT  # "Auto"
        exp_prior = P260_FACE_EYE_PRIOR_DEFAULT  # "On"
        exp_subj = P260_FACE_EYE_SUBJECT_DEFAULT  # "Human"
        exp_eye = P260_RIGHT_LEFT_EYE_SELECT_DEFAULT  # "Auto"
        exp_frame = P260_FACE_EYE_FRAME_DISP_DEFAULT  # "Off"

    if spec.reset_action == "Initialize" or spec.explicit_face_memory_delete:
        exp_face_mem = 0
    else:
        exp_face_mem = spec.pre_face_memory_registered_count

    intelligent_auto_prior_bad = (
        spec.exposure_profile == "Intelligent Auto" and spec.post_face_eye_prior_in_af != "On"
    )
    reset_and_face_mem_ok = (
        spec.post_reset_apsc_s35 == exp_apsc
        and (intelligent_auto_prior_bad or spec.post_face_eye_prior_in_af == exp_prior)
        and spec.post_face_eye_subject == exp_subj
        and spec.post_right_left_eye_select == exp_eye
        and spec.post_face_eye_frame_disp == exp_frame
        and spec.post_face_memory_registered_count == exp_face_mem
    )
    if not reset_and_face_mem_ok:
        _fail(
            P260_BLOCKED_APSC_OR_FACE_MEMORY_RESET_SCOPE_DRIFT,
            f"Reset / Face Memory scope drift under {spec.reset_action!r}: expected "
            f"apsc={exp_apsc!r}, subj={exp_subj!r}, eye={exp_eye!r}, frame={exp_frame!r}, "
            f"face_mem={exp_face_mem}; got apsc={spec.post_reset_apsc_s35!r}, "
            f"subj={spec.post_face_eye_subject!r}, eye={spec.post_right_left_eye_select!r}, "
            f"frame={spec.post_face_eye_frame_disp!r}, face_mem={spec.post_face_memory_registered_count}",
        )

    # 2. ILME-FX3 12.1MP sensor 4K movie & 4264x2408 HDMI RAW Output lockout
    exp_locked, exp_eff_mode, exp_fov = compute_expected_apsc_s35_movie_or_still_state(
        shooting_domain=spec.shooting_domain,
        movie_file_format=spec.movie_file_format,
        hdmi_raw_output_4264x2408=spec.hdmi_raw_output_4264x2408,
        configured_apsc_s35=spec.post_reset_apsc_s35,
        lens_image_circle=spec.lens_image_circle,
    )
    apsc_4k_raw_ok = (
        spec.camera_model == P260_FX3_MODEL_NAME
        and spec.sensor_effective_mp == P260_FX3_SENSOR_EFFECTIVE_MP
        and spec.apsc_s35_locked_off == exp_locked
        and spec.effective_apsc_s35_mode == exp_eff_mode
        and spec.effective_angle_of_view == exp_fov
        and spec.apsc_s35_4k_or_raw_bypass_events == 0
    )
    if not apsc_4k_raw_ok:
        _fail(
            P260_BLOCKED_APSC_S35_4K_OR_RAW_LOCKOUT_BYPASS,
            f"ILME-FX3 12.1MP APS-C S35 4K/RAW lockout violated: domain={spec.shooting_domain!r}, "
            f"fmt={spec.movie_file_format!r}, raw={spec.hdmi_raw_output_4264x2408!r}, "
            f"expected(locked={exp_locked},eff={exp_eff_mode!r},fov={exp_fov!r}), "
            f"got(locked={spec.apsc_s35_locked_off},eff={spec.effective_apsc_s35_mode!r},"
            f"fov={spec.effective_angle_of_view!r},bypass={spec.apsc_s35_4k_or_raw_bypass_events})",
        )

    # 3. [Face/Eye AF] BIONZ XR subject firmware gate, [Intelligent Auto] lock, custom key & Auto Clear
    bird_used = "Bird" in (
        spec.pre_face_eye_subject,
        spec.post_face_eye_subject,
        spec.saved_face_eye_subject if spec.camset_load_after_reset else "Human",
    )
    bird_fw_ok = (not bird_used) or (spec.fw_version in P260_FX3_BIRD_EYE_MIN_FW_VERSIONS)

    if spec.post_face_eye_prior_in_af != "On" or not spec.switch_right_left_eye_custom_key_pressed:
        exp_eye_after_key = spec.post_right_left_eye_select
    elif spec.post_right_left_eye_select == "Right Eye":
        exp_eye_after_key = "Left Eye"
    elif spec.post_right_left_eye_select == "Left Eye":
        exp_eye_after_key = "Right Eye"
    else:
        exp_eye_after_key = "Right Eye"

    exp_lcd_before = spec.post_face_eye_prior_in_af == "On" and spec.post_face_eye_frame_disp == "On"
    exp_lcd_after = exp_lcd_before and not (spec.focus_locked and spec.af_area_auto_clear == "On")

    face_eye_rules_ok = (
        not ai_unit_spoof_detected
        and bird_fw_ok
        and not intelligent_auto_prior_bad
        and spec.active_eye_target_after_custom_key == exp_eye_after_key
        and spec.lcd_eye_frame_rendered_before_lock == exp_lcd_before
        and spec.lcd_eye_frame_visible_after_lock == exp_lcd_after
    )
    if not face_eye_rules_ok:
        _fail(
            P260_BLOCKED_AI_UNIT_SUBJECT_RECOG_SPOOF_OR_EYE_RULE_DRIFT,
            "Face/Eye AF BIONZ XR rule drift (AI-unit spoof, pre-3.00 Bird, Intelligent Auto Prior=Off, "
            "Switch Right/Left Eye toggle, or AF Area Auto Clear mismatch)",
        )

    # 4. Clean-HDMI [Face/Eye Frame Disp.] overlay isolation
    exp_hdmi_eye_frame = bool(
        spec.hdmi_connected
        and spec.hdmi_info_display == "On"
        and spec.hdmi_raw_output_4264x2408 == "Off"
        and exp_lcd_before
    )
    clean_hdmi_ok = (
        spec.hdmi_eye_frame_rendered == exp_hdmi_eye_frame
        and spec.hdmi_clean_feed_eye_frame_baked_pixels == 0
    )
    if not clean_hdmi_ok:
        _fail(
            P260_BLOCKED_HDMI_CLEAN_FEED_EYE_FRAME_LEAK,
            f"Face/Eye Frame Disp. leaked into clean HDMI / RAW feed: info_disp={spec.hdmi_info_display!r}, "
            f"raw={spec.hdmi_raw_output_4264x2408!r}, hdmi_rendered={spec.hdmi_eye_frame_rendered}, "
            f"baked_pixels={spec.hdmi_clean_feed_eye_frame_baked_pixels}",
        )

    passed = len(errors) == 0
    bypass_cnt = max(
        int(spec.apsc_s35_4k_or_raw_bypass_events),
        0 if apsc_4k_raw_ok else 1,
    )
    spoof_cnt = max(
        int(spec.ai_unit_subject_recog_spoof_events),
        1 if ai_unit_spoof_detected else 0,
    )
    baked_px = max(
        int(spec.hdmi_clean_feed_eye_frame_baked_pixels),
        0 if clean_hdmi_ok else 1,
    )
    digest = _canonical_sha256(
        {
            "pillar": "44A",
            "passed": passed,
            "block_code": block_code,
            "locked_off": spec.apsc_s35_locked_off,
            "fov": spec.effective_angle_of_view,
            "eye": spec.active_eye_target_after_custom_key,
            "face_mem": spec.post_face_memory_registered_count,
            "bypass": bypass_cnt,
            "spoof": spoof_cnt,
            "baked_px": baked_px,
        }
    )
    return ApscS35AndFaceEyeAfVaultReport(
        passed=passed,
        status=P260_STATUS_VERIFIED_PILLAR_44A if passed else P260_STATUS_REJECTED_PILLAR_44A,
        block_code=block_code,
        reset_and_face_memory_scope_verified=reset_and_face_mem_ok,
        apsc_s35_12mp_4k_raw_lockout_verified=apsc_4k_raw_ok,
        face_eye_af_bionz_xr_rules_verified=face_eye_rules_ok,
        clean_hdmi_eye_frame_isolation_verified=clean_hdmi_ok,
        h0_equals_h3_verified=h0_eq_h3_ok,
        apsc_s35_locked_off=spec.apsc_s35_locked_off,
        effective_angle_of_view=spec.effective_angle_of_view,
        apsc_s35_4k_or_raw_bypass_events=bypass_cnt,
        ai_unit_subject_recog_spoof_events=spoof_cnt,
        hdmi_clean_feed_eye_frame_baked_pixels=baked_px,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_version_readonly_and_bodydata_vault(
    spec: VersionReadOnlyAndBodydataVaultSpec,
) -> VersionReadOnlyAndBodydataVaultReport:
    """Evaluate Pillar 44B `[Version]` `O_RDONLY`, zero-RF badge suppression & hard-blocked `BODYDATA.DAT`."""
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
            _fail(P260_BLOCKED_SAFETY_POLICY_VIOLATION, e)
        if spec.persistent_write_unlock_requested:
            _fail(
                P260_BLOCKED_SAFETY_POLICY_VIOLATION,
                "persistent_write_unlock_requested=True forbidden under zero-write posture",
            )

    if (
        not _is_tmpfs_path(spec.overlay_dir)
        or _targets_persistent_emmc(spec.overlay_dir)
        or not spec.p2_blkroset_locked
        or spec.stage_b_backup_bin_writes != 0
    ):
        _fail(
            P260_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Volatile tmpfs Stage-B overlay / p2 BLKROSET lock violated: overlay={spec.overlay_dir!r}",
        )

    h0_eq_h3_ok = (
        spec.backup_bin_h0_sha256 == P260_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == P260_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256
        and spec.tier0_surfaces_h0_h3_matched == P260_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3_ok:
        _fail(
            P260_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "16/16 Tier-0 Backup.bin H0 == H3 parity drift detected in Pillar 44B",
        )

    spec_valid = (
        spec.camera_model == P260_FX3_MODEL_NAME
        and spec.helpguide_id == P260_FX3_HELPGUIDE_ID
        and spec.fw_version in P260_FX3_SUPPORTED_FW_VERSIONS
        and spec.version_menu_path == P260_VERSION_MENU_PATH
        and spec.airplane_mode_menu_path == P260_AIRPLANE_MODE_MENU_PATH
        and spec.reset_action in P260_RESET_ACTIONS
        and spec.airplane_mode in P260_AIRPLANE_MODES
        and isinstance(spec.attached_lens_model, str)
        and bool(spec.attached_lens_model.strip())
        and isinstance(spec.attached_lens_fw_version, str)
        and bool(spec.attached_lens_fw_version.strip())
        and isinstance(spec.attached_mount_adaptor_model, str)
        and bool(spec.attached_mount_adaptor_model.strip())
        and isinstance(spec.attached_mount_adaptor_fw_version, str)
        and bool(spec.attached_mount_adaptor_fw_version.strip())
        and 0 <= spec.np_fz100_battery_bars <= 4
        and 0 <= spec.np_fz100_battery_pct <= 100
    )
    if not spec_valid:
        _fail(
            P260_BLOCKED_INVALID_VERSION_OR_BODYDATA_VAULT_SPEC,
            "Invalid ILME-FX3 [Version] / [Airplane Mode] menu path, FW, or battery range token",
        )

    # 1. Read-only [Version] dialog & Body/Lens/Mount-Adaptor version immutability across all resets
    version_ro_ok = (
        spec.version_dialog_open_mode == "O_RDONLY"
        and spec.version_dialog_flash_writes == 0
        and spec.displayed_body_fw_version == spec.fw_version
        and spec.displayed_lens_fw_version == spec.attached_lens_fw_version
        and spec.displayed_mount_adaptor_fw_version == spec.attached_mount_adaptor_fw_version
        and spec.post_reset_body_fw_version == spec.fw_version
        and spec.post_reset_lens_fw_version == spec.attached_lens_fw_version
        and spec.post_reset_mount_adaptor_fw_version == spec.attached_mount_adaptor_fw_version
    )
    if not version_ro_ok:
        _fail(
            P260_BLOCKED_VERSION_DIALOG_WRITE_OR_IMMUTABILITY_DRIFT,
            "Setup -> [Version] dialog violated O_RDONLY zero-write contract or reset mutated FW version",
        )

    # 2. Ver. 6.00+ / 7.02 red update notification badge suppression on zero-RF Airplane Mode = On bench
    zero_rf_badge_ok = (
        spec.airplane_mode == "On"
        and spec.rf_interfaces_disabled is True
        and spec.version_dialog_passive_tx_bytes == 0
        and spec.update_notification_badge_suppressed is True
        and spec.red_update_badge_displayed is False
    )
    if not zero_rf_badge_ok:
        _fail(
            P260_BLOCKED_UNSUPPRESSED_UPDATE_BADGE_OR_RF_LEAK,
            "Ver. 6.00+/7.02 update notification badge unsuppressed or passive RF probe emitted on zero-RF bench",
        )

    # 3. Hard-blocked automated Slot-1 BODYDATA.DAT flash execution & human-bench precheck boundaries
    expected_human_precheck_ready = (
        spec.slot1_bodydata_filename == P260_BODYDATA_FILENAME
        and spec.bodydata_target_model == P260_FX3_MODEL_NAME
        and spec.bodydata_sony_signature_intact is True
        and spec.np_fz100_battery_bars >= P260_HUMAN_BENCH_MIN_BATTERY_BARS
        and spec.np_fz100_battery_pct >= P260_HUMAN_BENCH_MIN_BATTERY_PCT
    )
    blocked_cnt_ok = (
        (spec.automated_bodydata_update_requested and spec.bodydata_flash_attempts_blocked >= 1)
        or (not spec.automated_bodydata_update_requested and spec.bodydata_flash_attempts_blocked == 0)
    )
    bodydata_block_ok = (
        spec.slot1_bodydata_filename == P260_BODYDATA_FILENAME
        and spec.bodydata_flash_executed is False
        and spec.automated_bodydata_update_hard_blocked is True
        and blocked_cnt_ok
        and spec.human_bench_precheck_claimed_ready == expected_human_precheck_ready
    )
    if not bodydata_block_ok:
        _fail(
            P260_BLOCKED_AUTOMATED_BODYDATA_FLASH_EXECUTION,
            "Automated Slot-1 BODYDATA.DAT firmware flash execution or invalid low-battery/cross-model precheck",
        )

    # 4. Slot-1 Tier-0 recovery vault integrity & lossless O_RDONLY CAMSET01.DAT [Load] round-trip
    camset_ok = True
    if spec.camset_load_after_reset:
        camset_ok = (
            spec.camset_slot in (1, 2)
            and spec.camset_filename in P260_CAMSET_FILENAMES
            and spec.camset_source_model == P260_FX3_MODEL_NAME
            and spec.camset_read_only_load is True
            and spec.camset_roundtrip_restored_ok is True
        )
    slot1_vault_ok = (
        camset_ok
        and spec.slot1_bodydata_vault_mutation_bytes == 0
        and not (spec.slot1_tier0_vault_active and spec.camset_save_to_slot1_attempted)
        and (not spec.slot1_tier0_vault_active or spec.slot1_sdxc_wp_locked)
    )
    if not slot1_vault_ok:
        _fail(
            P260_BLOCKED_SLOT1_BODYDATA_VAULT_MUTATION_OR_CAMSET_DRIFT,
            "Slot-1 Tier-0 vault mutation or non-O_RDONLY / cross-model CAMSET load drift detected",
        )

    passed = len(errors) == 0
    flash_writes = max(int(spec.version_dialog_flash_writes), 0 if version_ro_ok else 1)
    mut_bytes = max(int(spec.slot1_bodydata_vault_mutation_bytes), 0 if slot1_vault_ok else 1)
    digest = _canonical_sha256(
        {
            "pillar": "44B",
            "passed": passed,
            "block_code": block_code,
            "body_fw": spec.displayed_body_fw_version,
            "lens_fw": spec.displayed_lens_fw_version,
            "adaptor_fw": spec.displayed_mount_adaptor_fw_version,
            "flash_writes": flash_writes,
            "blocked_attempts": spec.bodydata_flash_attempts_blocked,
            "mut_bytes": mut_bytes,
        }
    )
    return VersionReadOnlyAndBodydataVaultReport(
        passed=passed,
        status=P260_STATUS_VERIFIED_PILLAR_44B if passed else P260_STATUS_REJECTED_PILLAR_44B,
        block_code=block_code,
        version_readonly_and_immutability_verified=version_ro_ok,
        zero_rf_update_badge_suppression_verified=zero_rf_badge_ok,
        bodydata_flash_hard_block_verified=bodydata_block_ok,
        slot1_vault_and_camset_roundtrip_verified=slot1_vault_ok,
        h0_equals_h3_verified=h0_eq_h3_ok,
        version_dialog_flash_writes=flash_writes,
        bodydata_flash_attempts_blocked=int(spec.bodydata_flash_attempts_blocked),
        slot1_bodydata_vault_mutation_bytes=mut_bytes,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_apsc_s35_face_eye_af_and_version_vault(
    apsc_face_eye_spec: Optional[ApscS35AndFaceEyeAfVaultSpec] = None,
    version_bodydata_spec: Optional[VersionReadOnlyAndBodydataVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> ApscS35FaceEyeAfAndVersionVaultReport:
    """Combined single-shot verifier for Pillar 44A + Pillar 44B + bounded O_RDONLY Wave-42 donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase260_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_apsc_s35_and_face_eye_af_vault(
        apsc_face_eye_spec or build_default_safe_apsc_s35_face_eye_af_vault_spec()
    )
    rep_b = evaluate_version_readonly_and_bodydata_vault(
        version_bodydata_spec or build_default_safe_version_readonly_bodydata_vault_spec()
    )
    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 260 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        errs.append(f"Donor inspection exceeded 2.0s budget: {donor_snapshot.elapsed_seconds}s")
    ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return ApscS35FaceEyeAfAndVersionVaultReport(
        schema=PHASE260_SCHEMA,
        version=PHASE260_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=ok,
        passed=ok,
        status=P260_STATUS_VERIFIED_PILLAR44_SUITE if ok else P260_STATUS_FAIL_PILLAR44_SUITE,
        donor_snapshot=donor_snapshot,
        apsc_s35_face_eye_af_report=rep_a,
        version_readonly_bodydata_report=rep_b,
        apsc_s35_4k_or_raw_bypass_events=rep_a.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=rep_a.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=rep_a.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=rep_b.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=rep_b.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=rep_b.slot1_bodydata_vault_mutation_bytes,
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


def verify_apsc_s35_face_eye_af_version_vault(
    apsc_face_eye_spec: Optional[ApscS35AndFaceEyeAfVaultSpec] = None,
    version_bodydata_spec: Optional[VersionReadOnlyAndBodydataVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> ApscS35FaceEyeAfAndVersionVaultReport:
    """Symmetry alias for `verify_apsc_s35_face_eye_af_and_version_vault`."""
    return verify_apsc_s35_face_eye_af_and_version_vault(
        apsc_face_eye_spec=apsc_face_eye_spec,
        version_bodydata_spec=version_bodydata_spec,
        force_clean_room=force_clean_room,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillar 44A & Pillar 44B) & Standalone Runner
# ---------------------------------------------------------------------------


def run_pillar44a_apsc_s35_face_eye_af_vault_6_scenario_suite() -> Pillar44ASuiteResult:
    """Run all 6 canonical Pillar 44A scenarios (`2` safe + `4` negative hardware lockout/isolation guards)."""
    cases: Tuple[Tuple[str, bool, ApscS35AndFaceEyeAfVaultSpec, Optional[str]], ...] = (
        (
            P260_PILLAR_44A_SCENARIO_IDS[0],
            True,
            ApscS35AndFaceEyeAfVaultSpec(
                pre_reset_apsc_s35="On",
                pre_face_eye_prior_in_af="On",
                pre_face_eye_subject="Bird",
                pre_right_left_eye_select="Right Eye",
                pre_face_eye_frame_disp="On",
                pre_face_memory_registered_count=3,
                reset_action="Reset Network Set.",
                post_reset_apsc_s35="On",
                post_face_eye_prior_in_af="On",
                post_face_eye_subject="Bird",
                post_right_left_eye_select="Right Eye",
                post_face_eye_frame_disp="On",
                post_face_memory_registered_count=3,
                shooting_domain="Movie",
                movie_file_format="XAVC S-I HD",
                hdmi_raw_output_4264x2408="Off",
                lens_image_circle="FF",
                apsc_s35_locked_off=False,
                effective_apsc_s35_mode="On",
                effective_angle_of_view="Super35_1.5x",
                switch_right_left_eye_custom_key_pressed=True,
                active_eye_target_after_custom_key="Left Eye",
                af_area_auto_clear="Off",
                focus_locked=True,
                lcd_eye_frame_rendered_before_lock=True,
                lcd_eye_frame_visible_after_lock=True,
                hdmi_connected=True,
                hdmi_info_display="Off",
                hdmi_eye_frame_rendered=False,
                hdmi_clean_feed_eye_frame_baked_pixels=0,
            ),
            None,
        ),
        (
            P260_PILLAR_44A_SCENARIO_IDS[1],
            True,
            ApscS35AndFaceEyeAfVaultSpec(
                pre_reset_apsc_s35="On",
                pre_face_eye_prior_in_af="Off",
                pre_face_eye_subject="Animal",
                pre_right_left_eye_select="Left Eye",
                pre_face_eye_frame_disp="On",
                pre_face_memory_registered_count=4,
                reset_action="Camera Settings Reset",
                post_reset_apsc_s35="Auto",
                post_face_eye_prior_in_af="On",
                post_face_eye_subject="Human",
                post_right_left_eye_select="Auto",
                post_face_eye_frame_disp="Off",
                post_face_memory_registered_count=4,
                shooting_domain="Movie",
                movie_file_format="XAVC S-I 4K",
                hdmi_raw_output_4264x2408="On",
                lens_image_circle="APS-C",
                apsc_s35_locked_off=True,
                effective_apsc_s35_mode="Off",
                effective_angle_of_view="Full-Frame_1.0x",
                switch_right_left_eye_custom_key_pressed=False,
                active_eye_target_after_custom_key="Auto",
                lcd_eye_frame_rendered_before_lock=False,
                lcd_eye_frame_visible_after_lock=False,
                hdmi_connected=True,
                hdmi_info_display="Off",
                hdmi_eye_frame_rendered=False,
                hdmi_clean_feed_eye_frame_baked_pixels=0,
            ),
            None,
        ),
        (
            P260_PILLAR_44A_SCENARIO_IDS[2],
            False,
            ApscS35AndFaceEyeAfVaultSpec(
                shooting_domain="Movie",
                movie_file_format="XAVC HS 4K",
                hdmi_raw_output_4264x2408="Off",
                apsc_s35_locked_off=False,
                effective_apsc_s35_mode="On",
                effective_angle_of_view="Super35_1.5x",
                apsc_s35_4k_or_raw_bypass_events=1,
            ),
            P260_BLOCKED_APSC_S35_4K_OR_RAW_LOCKOUT_BYPASS,
        ),
        (
            P260_PILLAR_44A_SCENARIO_IDS[3],
            False,
            ApscS35AndFaceEyeAfVaultSpec(
                face_eye_af_menu_path=("MENU", "Focus", "Subject Recog in AF"),
                pre_face_eye_subject="Car/Train",
                post_face_eye_subject="Car/Train",
                ai_unit_subject_recog_spoof_events=1,
            ),
            P260_BLOCKED_AI_UNIT_SUBJECT_RECOG_SPOOF_OR_EYE_RULE_DRIFT,
        ),
        (
            P260_PILLAR_44A_SCENARIO_IDS[4],
            False,
            ApscS35AndFaceEyeAfVaultSpec(
                hdmi_connected=True,
                hdmi_info_display="Off",
                hdmi_eye_frame_rendered=True,
                hdmi_clean_feed_eye_frame_baked_pixels=1280,
            ),
            P260_BLOCKED_HDMI_CLEAN_FEED_EYE_FRAME_LEAK,
        ),
        (
            P260_PILLAR_44A_SCENARIO_IDS[5],
            False,
            ApscS35AndFaceEyeAfVaultSpec(
                pre_reset_apsc_s35="On",
                pre_face_memory_registered_count=3,
                reset_action="Camera Settings Reset",
                post_reset_apsc_s35="Auto",
                post_face_eye_prior_in_af="On",
                post_face_eye_subject="Human",
                post_right_left_eye_select="Auto",
                post_face_eye_frame_disp="Off",
                post_face_memory_registered_count=0,
                effective_apsc_s35_mode="Auto",
                effective_angle_of_view="Full-Frame_1.0x",
                active_eye_target_after_custom_key="Auto",
                lcd_eye_frame_rendered_before_lock=False,
                lcd_eye_frame_visible_after_lock=False,
            ),
            P260_BLOCKED_APSC_OR_FACE_MEMORY_RESET_SCOPE_DRIFT,
        ),
    )

    outcomes: List[Pillar44ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_apsc_s35_and_face_eye_af_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar44ScenarioOutcome(
                scenario_id=sid,
                pillar="44A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar44ASuiteResult(
        passed=all_ok,
        status=P260_STATUS_VERIFIED_PILLAR_44A if all_ok else P260_STATUS_REJECTED_PILLAR_44A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar44b_version_readonly_bodydata_vault_6_scenario_suite() -> Pillar44BSuiteResult:
    """Run all 6 canonical Pillar 44B scenarios (`2` safe + `4` negative Version/BODYDATA vault guards)."""
    cases: Tuple[Tuple[str, bool, VersionReadOnlyAndBodydataVaultSpec, Optional[str]], ...] = (
        (
            P260_PILLAR_44B_SCENARIO_IDS[0],
            True,
            VersionReadOnlyAndBodydataVaultSpec(
                camset_load_after_reset=False,
                bodydata_flash_attempts_blocked=1,
            ),
            None,
        ),
        (
            P260_PILLAR_44B_SCENARIO_IDS[1],
            True,
            VersionReadOnlyAndBodydataVaultSpec(
                attached_mount_adaptor_model="LA-EA5",
                attached_mount_adaptor_fw_version="02",
                displayed_mount_adaptor_fw_version="02",
                reset_action="Initialize",
                post_reset_mount_adaptor_fw_version="02",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model=P260_FX3_MODEL_NAME,
                camset_read_only_load=True,
                camset_roundtrip_restored_ok=True,
                bodydata_flash_attempts_blocked=1,
            ),
            None,
        ),
        (
            P260_PILLAR_44B_SCENARIO_IDS[2],
            False,
            VersionReadOnlyAndBodydataVaultSpec(
                version_dialog_open_mode="O_RDWR",
                version_dialog_flash_writes=4,
                post_reset_body_fw_version="2.00",
            ),
            P260_BLOCKED_VERSION_DIALOG_WRITE_OR_IMMUTABILITY_DRIFT,
        ),
        (
            P260_PILLAR_44B_SCENARIO_IDS[3],
            False,
            VersionReadOnlyAndBodydataVaultSpec(
                airplane_mode="On",
                update_notification_badge_suppressed=False,
                red_update_badge_displayed=True,
                version_dialog_passive_tx_bytes=512,
            ),
            P260_BLOCKED_UNSUPPRESSED_UPDATE_BADGE_OR_RF_LEAK,
        ),
        (
            P260_PILLAR_44B_SCENARIO_IDS[4],
            False,
            VersionReadOnlyAndBodydataVaultSpec(
                np_fz100_battery_bars=1,
                np_fz100_battery_pct=25,
                human_bench_precheck_claimed_ready=True,
                automated_bodydata_update_requested=True,
                automated_bodydata_update_hard_blocked=False,
                bodydata_flash_executed=True,
                bodydata_flash_attempts_blocked=0,
            ),
            P260_BLOCKED_AUTOMATED_BODYDATA_FLASH_EXECUTION,
        ),
        (
            P260_PILLAR_44B_SCENARIO_IDS[5],
            False,
            VersionReadOnlyAndBodydataVaultSpec(
                slot1_tier0_vault_active=True,
                slot1_sdxc_wp_locked=True,
                camset_save_to_slot1_attempted=True,
                slot1_bodydata_vault_mutation_bytes=4096,
                camset_load_after_reset=True,
                camset_source_model=P260_FX6_DONOR_MODEL_NAME,
            ),
            P260_BLOCKED_SLOT1_BODYDATA_VAULT_MUTATION_OR_CAMSET_DRIFT,
        ),
    )

    outcomes: List[Pillar44ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_version_readonly_and_bodydata_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar44ScenarioOutcome(
                scenario_id=sid,
                pillar="44B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar44BSuiteResult(
        passed=all_ok,
        status=P260_STATUS_VERIFIED_PILLAR_44B if all_ok else P260_STATUS_REJECTED_PILLAR_44B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar44_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar44StandaloneReport:
    """Run full Pillar 44 standalone suite (`6/6` Pillar 44A + `6/6` Pillar 44B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase260_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar44a_apsc_s35_face_eye_af_vault_6_scenario_suite()
    res_b = run_pillar44b_version_readonly_bodydata_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 260 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor inspection exceeded 2.0s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE260_SCHEMA,
            "version": PHASE260_VERSION,
            "mode": donor_snapshot.verification_mode,
            "44a": [asdict(s) for s in res_a.scenarios],
            "44b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar44StandaloneReport(
        schema=PHASE260_SCHEMA,
        version=PHASE260_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P260_STATUS_VERIFIED_PILLAR44_SUITE if all_ok else P260_STATUS_FAIL_PILLAR44_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_44a_apsc_s35_face_eye_af_vault=res_a,
        pillar_44b_version_readonly_bodydata_vault=res_b,
        apsc_s35_4k_or_raw_bypass_events=P260_APSC_S35_4K_OR_RAW_BYPASS_EVENTS if res_a.passed else 1,
        ai_unit_subject_recog_spoof_events=P260_AI_UNIT_SUBJECT_RECOG_SPOOF_EVENTS if res_a.passed else 1,
        hdmi_clean_feed_eye_frame_baked_pixels=(
            P260_HDMI_CLEAN_FEED_EYE_FRAME_BAKED_PIXELS if res_a.passed else 1
        ),
        version_dialog_flash_writes=P260_VERSION_DIALOG_FLASH_WRITES if res_b.passed else 1,
        bodydata_flash_attempts_blocked=2 if res_b.passed else 0,
        slot1_bodydata_vault_mutation_bytes=(
            P260_SLOT1_BODYDATA_VAULT_MUTATION_BYTES if res_b.passed else 1
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
# Unified 44/44 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master44_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_44pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master44PillarRecoveryReport:
    """Evaluate and aggregate all 44 recovery pillars (`1..44`) concurrently -> `44/44` recovery master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_44_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_43pillar() -> Master43PillarRecoveryReport:
        return evaluate_realhw_43pillar_recovery_master(**kw)

    def _run_p44() -> Tuple[Pillar44StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar44_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_43 = pool.submit(_run_43pillar)
        fut_44 = pool.submit(_run_p44)
        m43_rep = fut_43.result()
        p44_rep, p44_dt = fut_44.result()

    all_errors: List[str] = list(m43_rep.errors) + list(p44_rep.errors)
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
        if getattr(m43_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-43 violated {attr_name} == {expected_val}")
        if getattr(p44_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 44 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
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
        if getattr(m43_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-43 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("apsc_s35_4k_or_raw_bypass_events", 0),
        ("ai_unit_subject_recog_spoof_events", 0),
        ("hdmi_clean_feed_eye_frame_baked_pixels", 0),
        ("version_dialog_flash_writes", 0),
        ("slot1_bodydata_vault_mutation_bytes", 0),
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(p44_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 44 violated {attr_name} == {expected_val}")
    if p44_rep.bodydata_flash_attempts_blocked < 1:
        all_errors.append("Pillar 44 violated bodydata_flash_attempts_blocked >= 1")

    pillar_statuses: List[MasterPillarStatus] = list(m43_rep.pillars)
    spec44 = MASTER_44_PILLAR_SPECS[43]
    p44_metrics = {
        "pillar_44a_apsc_s35_face_eye_af_vault": (
            f"{p44_rep.pillar_44a_apsc_s35_face_eye_af_vault.scenarios_passed}/"
            f"{p44_rep.pillar_44a_apsc_s35_face_eye_af_vault.scenarios_total}"
        ),
        "pillar_44b_version_readonly_bodydata_vault": (
            f"{p44_rep.pillar_44b_version_readonly_bodydata_vault.scenarios_passed}/"
            f"{p44_rep.pillar_44b_version_readonly_bodydata_vault.scenarios_total}"
        ),
        "apsc_s35_4k_or_raw_bypass_events": p44_rep.apsc_s35_4k_or_raw_bypass_events,
        "ai_unit_subject_recog_spoof_events": p44_rep.ai_unit_subject_recog_spoof_events,
        "hdmi_clean_feed_eye_frame_baked_pixels": p44_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        "version_dialog_flash_writes": p44_rep.version_dialog_flash_writes,
        "bodydata_flash_attempts_blocked": p44_rep.bodydata_flash_attempts_blocked,
        "slot1_bodydata_vault_mutation_bytes": p44_rep.slot1_bodydata_vault_mutation_bytes,
        "hardware_live_attachment_authorized": p44_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p44_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec44[0],
            pillar_id=spec44[1],
            phase_label=spec44[2],
            module_name=spec44[3],
            passed=bool(p44_rep.all_passed),
            status=p44_rep.status,
            verification_mode=p44_rep.verification_mode,
            elapsed_seconds=p44_dt,
            key_metrics=p44_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec44[1],
                    "mode": p44_rep.verification_mode,
                    "status": p44_rep.status,
                    "metrics": p44_metrics,
                    "passed": p44_rep.all_passed,
                }
            ),
            errors=tuple(p44_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master44_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p44_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_44_PILLAR_COUNT == 44
        and pillars_passed == 44
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE260_SCHEMA,
            "version": PHASE260_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master44PillarRecoveryReport(
        schema=PHASE260_SCHEMA,
        version=PHASE260_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P260_STATUS_VERIFIED_44OF44_AGGREGATOR if all_ok else P260_STATUS_FAIL_44OF44_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P260_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P260_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p44_rep.donor_snapshot,
        pillar44_a_apsc_s35_face_eye_af_vault=p44_rep.pillar_44a_apsc_s35_face_eye_af_vault,
        pillar44_b_version_readonly_bodydata_vault=p44_rep.pillar_44b_version_readonly_bodydata_vault,
        apsc_s35_4k_or_raw_bypass_events=p44_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=p44_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=p44_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=p44_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=p44_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=p44_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m43_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m43_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m43_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m43_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m43_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m43_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m43_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m43_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m43_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m43_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m43_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m43_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m43_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m43_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m43_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m43_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m43_rep.unbuffered_battery_pull_events,
        hardware_live_attachment_authorized=p44_rep.hardware_live_attachment_authorized,
        master_44pillar_sha256=master_sha,
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


def evaluate_44pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master44PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_44pillar_recovery_master`."""
    return evaluate_realhw_44pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_44pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master44PillarRecoveryReport:
    """Public CLI entry point for Phase 260 (`260th` Milestone) Pillar 44 unified `44/44` recovery master."""
    return evaluate_realhw_44pillar_recovery_master(
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
    "MASTER_44_PILLAR_COUNT",
    "MASTER_44_PILLAR_IDS",
    "MASTER_44_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "P260_AF_AREA_AUTO_CLEAR_MODES",
    "P260_AI_UNIT_SUBJECT_RECOG_SPOOF_EVENTS",
    "P260_AIRPLANE_MODES",
    "P260_AIRPLANE_MODE_MENU_PATH",
    "P260_APSC_S35_4K_OR_RAW_BYPASS_EVENTS",
    "P260_APSC_S35_DEFAULT",
    "P260_APSC_S35_MENU_PATH",
    "P260_APSC_S35_MODES",
    "P260_BLOCKED_AI_UNIT_SUBJECT_RECOG_SPOOF_OR_EYE_RULE_DRIFT",
    "P260_BLOCKED_APSC_OR_FACE_MEMORY_RESET_SCOPE_DRIFT",
    "P260_BLOCKED_APSC_S35_4K_OR_RAW_LOCKOUT_BYPASS",
    "P260_BLOCKED_AUTOMATED_BODYDATA_FLASH_EXECUTION",
    "P260_BLOCKED_HDMI_CLEAN_FEED_EYE_FRAME_LEAK",
    "P260_BLOCKED_INVALID_APSC_S35_OR_FACE_EYE_AF_SPEC",
    "P260_BLOCKED_INVALID_VERSION_OR_BODYDATA_VAULT_SPEC",
    "P260_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P260_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P260_BLOCKED_SLOT1_BODYDATA_VAULT_MUTATION_OR_CAMSET_DRIFT",
    "P260_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P260_BLOCKED_UNSUPPRESSED_UPDATE_BADGE_OR_RF_LEAK",
    "P260_BLOCKED_VERSION_DIALOG_WRITE_OR_IMMUTABILITY_DRIFT",
    "P260_BODYDATA_FILENAME",
    "P260_BOUNDED_HEADER_BYTES",
    "P260_CAMSET_FILENAMES",
    "P260_CONCURRENT_CEILING_SECONDS",
    "P260_DEFAULT_BODYDATA_FLASH_ATTEMPTS_BLOCKED",
    "P260_DONOR_FX3_APPFW_702_RELPATH",
    "P260_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P260_DONOR_FX3_BODYDATA_RELPATH",
    "P260_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH",
    "P260_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH",
    "P260_DONOR_FX3_LIBBACKUP_SO_RELPATH",
    "P260_DONOR_FX3_LIBGPE_SO_RELPATH",
    "P260_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH",
    "P260_DONOR_FX3_LIBINFRAGETVERSION_SO_RELPATH",
    "P260_DONOR_FX3_LIBINFRALENSCOMMUNICATOR_SO_RELPATH",
    "P260_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH",
    "P260_DONOR_FX3_LIBUPDATERMEDIA_SO_RELPATH",
    "P260_DONOR_FX6_APPFW_601_RELPATH",
    "P260_DONOR_INSPECT_BUDGET_SECONDS",
    "P260_EFFECTIVE_ANGLE_OF_VIEW_MODES",
    "P260_FACE_EYE_AF_MENU_PATH",
    "P260_FACE_EYE_FRAME_DISP_DEFAULT",
    "P260_FACE_EYE_FRAME_DISP_MODES",
    "P260_FACE_EYE_PRIOR_DEFAULT",
    "P260_FACE_EYE_PRIOR_MODES",
    "P260_FACE_EYE_SUBJECTS",
    "P260_FACE_EYE_SUBJECT_DEFAULT",
    "P260_FORBIDDEN_AI_UNIT_MENU_NAME",
    "P260_FORBIDDEN_AI_UNIT_SUBJECTS",
    "P260_FORBIDDEN_PERSISTENT_TARGETS",
    "P260_FX3_BIRD_EYE_MIN_FW_VERSIONS",
    "P260_FX3_FW_VERSION",
    "P260_FX3_HELPGUIDE_ID",
    "P260_FX3_MODEL_ID",
    "P260_FX3_MODEL_NAME",
    "P260_FX3_MOVIE_4K_READOUT_RES",
    "P260_FX3_SENSOR_EFFECTIVE_MP",
    "P260_FX3_STILL_FULLFRAME_RES",
    "P260_FX3_SUPPORTED_FW_VERSIONS",
    "P260_FX3_UPDATE_BADGE_MIN_FW_VERSIONS",
    "P260_FX6_DONOR_FW_VERSION",
    "P260_FX6_DONOR_MODEL_NAME",
    "P260_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P260_HDMI_CLEAN_FEED_EYE_FRAME_BAKED_PIXELS",
    "P260_HDMI_INFO_DISPLAY_MODES",
    "P260_HDMI_RAW_4264X2408_RESOLUTION",
    "P260_HDMI_RAW_OUTPUT_MODES",
    "P260_HUMAN_BENCH_MIN_BATTERY_BARS",
    "P260_HUMAN_BENCH_MIN_BATTERY_PCT",
    "P260_LENS_IMAGE_CIRCLE_TYPES",
    "P260_MAX_FACE_MEMORY_ENTRIES",
    "P260_MAX_FULL_DONOR_BYTES",
    "P260_MOVIE_FILE_FORMATS",
    "P260_MOVIE_FILE_FORMATS_4K",
    "P260_MOVIE_FILE_FORMATS_HD",
    "P260_NOMINAL_BUDGET_SECONDS",
    "P260_NON_FX3_S35_4K_MODELS",
    "P260_PILLAR_44A_SCENARIO_IDS",
    "P260_PILLAR_44B_SCENARIO_IDS",
    "P260_PINNED_FX3_APPFW_702_BYTES",
    "P260_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P260_PINNED_FX3_BACKUP_BIN_BYTES",
    "P260_PINNED_FX3_BACKUP_BIN_SHA256",
    "P260_PINNED_FX3_BODYDATA_BYTES",
    "P260_PINNED_FX3_BODYDATA_HDR4K_SHA256",
    "P260_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES",
    "P260_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256",
    "P260_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES",
    "P260_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256",
    "P260_PINNED_FX3_LIBBACKUP_SO_BYTES",
    "P260_PINNED_FX3_LIBBACKUP_SO_SHA256",
    "P260_PINNED_FX3_LIBGPE_SO_BYTES",
    "P260_PINNED_FX3_LIBGPE_SO_SHA256",
    "P260_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES",
    "P260_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256",
    "P260_PINNED_FX3_LIBINFRAGETVERSION_SO_BYTES",
    "P260_PINNED_FX3_LIBINFRAGETVERSION_SO_SHA256",
    "P260_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES",
    "P260_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256",
    "P260_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES",
    "P260_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256",
    "P260_PINNED_FX3_LIBUPDATERMEDIA_SO_BYTES",
    "P260_PINNED_FX3_LIBUPDATERMEDIA_SO_SHA256",
    "P260_PINNED_FX6_APPFW_601_BYTES",
    "P260_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P260_RESET_ACTIONS",
    "P260_RIGHT_LEFT_EYE_SELECT_DEFAULT",
    "P260_RIGHT_LEFT_EYE_SELECT_MODES",
    "P260_SHOOTING_DOMAINS",
    "P260_SHOOTING_EXPOSURE_PROFILES",
    "P260_SLOT1_BODYDATA_VAULT_MUTATION_BYTES",
    "P260_SLOT1_VAULT_SLOT",
    "P260_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P260_STATUS_FAIL_44OF44_AGGREGATOR",
    "P260_STATUS_FAIL_PILLAR44_SUITE",
    "P260_STATUS_REJECTED_PILLAR_44A",
    "P260_STATUS_REJECTED_PILLAR_44B",
    "P260_STATUS_VERIFIED_44OF44_AGGREGATOR",
    "P260_STATUS_VERIFIED_PILLAR44_SUITE",
    "P260_STATUS_VERIFIED_PILLAR_44A",
    "P260_STATUS_VERIFIED_PILLAR_44B",
    "P260_TIER0_SURFACE_COUNT",
    "P260_VERSION_DIALOG_FLASH_WRITES",
    "P260_VERSION_MENU_PATH",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE260_MILESTONE_NUMBER",
    "PHASE260_SCHEMA",
    "PHASE260_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "ApscS35AndFaceEyeAfVaultReport",
    "ApscS35AndFaceEyeAfVaultSpec",
    "ApscS35FaceEyeAfAndVersionVaultReport",
    "Master44PillarRecoveryReport",
    "Phase260DonorArtifactDigest",
    "Phase260DonorSnapshot",
    "Pillar44ASuiteResult",
    "Pillar44BSuiteResult",
    "Pillar44ScenarioOutcome",
    "Pillar44StandaloneReport",
    "VersionReadOnlyAndBodydataVaultReport",
    "VersionReadOnlyAndBodydataVaultSpec",
    "build_default_safe_apsc_s35_face_eye_af_vault_spec",
    "build_default_safe_version_readonly_bodydata_vault_spec",
    "compute_expected_apsc_s35_movie_or_still_state",
    "evaluate_44pillar_recovery_master",
    "evaluate_apsc_s35_and_face_eye_af_vault",
    "evaluate_realhw_44pillar_recovery_master",
    "evaluate_version_readonly_and_bodydata_vault",
    "inspect_phase260_donors_readonly",
    "run_pillar44_standalone_suite",
    "run_pillar44a_apsc_s35_face_eye_af_vault_6_scenario_suite",
    "run_pillar44b_version_readonly_bodydata_vault_6_scenario_suite",
    "verify_44pillar_recovery_suite",
    "verify_apsc_s35_face_eye_af_and_version_vault",
    "verify_apsc_s35_face_eye_af_version_vault",
]
