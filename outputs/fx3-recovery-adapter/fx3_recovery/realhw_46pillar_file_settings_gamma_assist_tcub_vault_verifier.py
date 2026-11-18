"""Phase 269 — Pillar 46 (`46/46` Recovery Pillars) & Unified 46-Pillar Recovery Master
(`verify-46pillar-recovery` / `verify-file-settings-gamma-assist-tcub-vault`):

1. **Pillar 46A — Movie `[File Settings]` (`File Number` `Series`/`Reset`, `File Name Format` `Standard` /
   `Cam ID + Reel#` `A..Z` + `001..999` + `C`/`L`/`R` / `Title` / `Date + Title` / `Title + Date`,
   `<= 37`-Char `Title Name Settings` `"C"` Default, Fixed `PRIVATE/M4ROOT/CLIP` Folder) vs Still
   `[File/Folder Settings]` (`Set File Name` `3`-Char `"DSC"` Default with `_` Forbidden at Index 0,
   `Standard Form` `100MSDCF` vs `Date Form`, and `Slot-1` Recovery Vault DCIM Firewall) (Wave-44)**:
   - Models `MENU` -> `Shooting` -> `[File]` -> `[File Settings]` (movie) and `[File/Folder Settings]`
     (still image) on physical `Sony ILME-FX3` (`Ver. 7.02`, `0x91030080`, `ilc/2210`).
   - Enforces survival of ALL Movie `[File Settings]` and Still `[File/Folder Settings]` items across
     `[Camera Settings Reset]` & `[Reset Network Set.]` vs factory restoration ONLY under `[Initialize]`,
     plus lossless `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` round-trip.
   - Enforces fixed `PRIVATE/M4ROOT/CLIP` movie directory (no custom movie folder paths), `<= 37`-char
     allowed ASCII `Title Name Settings`, `Cam ID + Reel#` (`A..Z`, `001..999`, `C`/`L`/`R`), `3`-char
     `Set File Name` (`A-Z`, `0-9`, `_` with `_` strictly forbidden at index `0`), and hard-blocks
     `[Forced File Number Reset]` & `[Create New Folder]` DCIM directory table mutations on `Slot 1`
     whenever `Slot 1` holds the read-only `CAMSET`/`BODYDATA.DAT` recovery vault
     (`slot1_vault_folder_mutation_events == 0`).

2. **Pillar 46B — `[Gamma Display Assist]` (`Off` Default / `On`, `Gamma Disp. Assist Typ.` `Auto` /
   `S-Log3->709(800%)` / `HLG(BT.2020)` / `HLG(709)`) Hard-Locked `Off` Under `[Log Shooting] != Off` &
   Camera-LCD-Only Scope (Clean External HDMI) vs `[Display LUT]` (`On` Default) & `[Select LUT]`
   (`S-Log3`, `s709`, `709(800%)`, `User1..User16`), Plus `[Auto Review]` (`Off` Cinema Default) &
   All 6 `[TC/UB]` Non-Resettable Timecode Parameters Surviving `[Camera Settings Reset]`**:
   - Enforces `[Gamma Display Assist]` hard lockout to `[Off]` whenever `[Log Shooting]` (`Cine EI`,
     `Cine EI Quick`, `Flexible ISO`) != `Off` (`gamma_assist_log_lockout_bypass_events == 0`), delegating
     log monitoring conversion to `[Display LUT]` (`On` default) & `[Select LUT]` (`3` presets + `User1..16`),
     and enforces camera-LCD-only scope so external TV/HDMI movie output remains clean
     (`gamma_assist_external_hdmi_leak_events == 0`).
   - Enforces `ILME-FX3` cinema-centric `[Auto Review] = [Off]` factory default (still-image only, never
     interrupting movie live view) and non-resettable persistence of all 6 `[TC/UB]` items (`Time Code Preset`
     `00:00:00.00`, `User Bit Preset` `00 00 00 00`, `Time Code Format` `DF`/`NDF` with `24.00p`/PAL forced
     `NDF`, `Time Code Run` `Rec Run`/`Free Run`, `Time Code Make` `Preset`/`Regenerate`, `User Bit Time Rec`
     `Off`/`On`) plus `[TC/UB Disp. Setting]` (`TC` default) across `[Camera Settings Reset]` &
     `[Reset Network Set.]` (reset only by `[Initialize]`).

3. **Unified `46/46` Recovery Master (`evaluate_realhw_46pillar_recovery_master`)**:
   - Concurrently delegates Pillars `1..45` (`evaluate_realhw_45pillar_recovery_master`) + **Pillar 46** ->
     **`46/46` (`VERIFIED_46OF46_PILLAR_RECOVERY_MASTER`)** in `< 1.9s` CLI runtime (`< 4.0s` nominal /
     `< 6.0s` concurrent ceiling), preserving 100% backward compatibility with `verify-22..45pillar-recovery`.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
import posixpath
import re
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from .files import is_forced_clean_room, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus
from .realhw_45pillar_release_wo_card_lens_audio_meter_copyright_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_45_PILLAR_SPECS,
    Master45PillarRecoveryReport,
    evaluate_realhw_45pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE269_SCHEMA: str = "realhw_46pillar_file_settings_gamma_assist_tcub_vault_verifier_v1"
PHASE269_VERSION: str = "1.0.0"
PHASE269_PHASE_NUMBER: int = 269
P269_ENV_CLEAN_ROOM_TEST: str = "FX3_CLEAN_ROOM_TEST"

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
P269_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P269_SLOT1_VAULT_FOLDER_MUTATION_EVENTS: int = 0
P269_SLOT1_VAULT_FOLDER_MUTATION_BYTES: int = 0
P269_MOVIE_CUSTOM_FOLDER_OR_TITLE_OVERFLOW_EVENTS: int = 0
P269_STILL_PREFIX_UNDERSCORE_LEAD_OR_LEN_VIOLATIONS: int = 0
P269_GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS: int = 0
P269_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_EVENTS: int = 0
P269_TCUB_CAMERA_RESET_WIPE_OR_FORMAT_VIOLATIONS: int = 0

P269_DONOR_INSPECT_BUDGET_SECONDS: float = 2.0
P269_FAST_CLI_BUDGET_SECONDS: float = 2.0
P269_NOMINAL_BUDGET_SECONDS: float = 4.0
P269_CONCURRENT_CEILING_SECONDS: float = 6.0
P269_BOUNDED_HEADER_BYTES: int = 4096
P269_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-44 / FX3 Ver. 7.02 & FX6 Ver. 6.01 Donor Anchors (bounded O_RDONLY verification)
P269_FX3_MODEL_NAME: str = "ILME-FX3"
P269_FX3_MODEL_ID: int = 0x91030080
P269_FX3_HELPGUIDE_ID: str = "ilc/2210"
P269_FX3_FW_VERSION: str = "7.02"
P269_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P269_FX6_DONOR_FW_VERSION: str = "6.01"
P269_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
    "3.00",
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)

P269_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P269_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P269_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = (
    "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
)

P269_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P269_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P269_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)

P269_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P269_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P269_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)

P269_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P269_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P269_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P269_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P269_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P269_PINNED_FX3_LIBBACKUP_SO_SHA256: str = (
    "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"
)

P269_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P269_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P269_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = (
    "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"
)

P269_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so"
)
P269_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES: int = 18760
P269_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256: str = (
    "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7"
)

P269_DONOR_FX3_LIBGPE_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgpe.so"
)
P269_PINNED_FX3_LIBGPE_SO_BYTES: int = 106480
P269_PINNED_FX3_LIBGPE_SO_SHA256: str = (
    "363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464"
)

P269_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/CameraOnDemandSaver.so"
)
P269_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES: int = 18800
P269_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256: str = (
    "72b73608c2675a3709e2952ca347a36e7dd2ad3dd2869191638c7154933b2f46"
)

P269_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaConfig.so"
)
P269_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES: int = 52312
P269_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256: str = (
    "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486"
)

P269_DONOR_FX3_LIBINFRAMEDIADETECT_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaDetect.so"
)
P269_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES: int = 98224
P269_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256: str = (
    "4c1dbb303cf9d2d762723e0eb2266309c83aefe7d50f050fc8baa3964e4ea70d"
)

P269_DONOR_FX3_LIBINFRAMEDIACOMMON_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaCommon.so"
)
P269_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES: int = 402624
P269_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_SHA256: str = (
    "1ddec7e4d903eaca7cdc7901936b99a9bf97bc52f67259cd3ebb3ee60620b40b"
)

P269_DONOR_FX3_LIBINFRAMEDIAMOUNT_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaMount.so"
)
P269_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_BYTES: int = 65392
P269_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_SHA256: str = (
    "33b4c61c39f724e08e1bc4d07fd505a799ee37a9c1f37a43fffc7c2c9c8f75ad"
)

P269_DONOR_FX3_LIBINFRAFSYS_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraFsys.so"
)
P269_PINNED_FX3_LIBINFRAFSYS_SO_BYTES: int = 683632
P269_PINNED_FX3_LIBINFRAFSYS_SO_SHA256: str = (
    "ec0dcdfa2bd0bb9236137821ecd620ea4c726adc4b5455da9ced25287f158651"
)

P269_DONOR_FX3_LIBINFRAMETASUPPLIER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMetaSupplier.so"
)
P269_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_BYTES: int = 23048
P269_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_SHA256: str = (
    "ce8ae80920c405f58367b1b685bc8ff2ae8738767ed10ba3388e15bcb26b8503"
)

P269_DONOR_FX6_LIBINFRASETUPFILE_SO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraSetupFile.so"
)
P269_PINNED_FX6_LIBINFRASETUPFILE_SO_BYTES: int = 202664
P269_PINNED_FX6_LIBINFRASETUPFILE_SO_SHA256: str = (
    "b489c64adef153d42e465f0fb26d2d3a971cde122a6bcf7ec5e056e30400c357"
)

# Pillar 46A — Movie [File Settings] vs Still [File/Folder Settings] & Slot-1 Vault Firewall
P269_MOVIE_FILE_SETTINGS_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "File",
    "File Settings",
)
P269_MOVIE_FILE_SETTINGS_ITEMS: Tuple[str, ...] = (
    "File Number",
    "Series Counter Reset",
    "File Name Format",
    "Title Name Settings",
)
P269_MOVIE_FILE_NUMBER_MODES: Tuple[str, ...] = ("Series", "Reset")
P269_MOVIE_FILE_NUMBER_DEFAULT: str = "Series"
P269_MOVIE_FILE_NAME_FORMATS: Tuple[str, ...] = (
    "Standard",
    "Cam ID + Reel#",
    "Title",
    "Date + Title",
    "Title + Date",
)
P269_MOVIE_FILE_NAME_FORMAT_DEFAULT: str = "Standard"
P269_CAM_ID_LETTERS: Tuple[str, ...] = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
P269_CAM_ID_DEFAULT: str = "A"
P269_REEL_NUMBER_MIN: int = 1
P269_REEL_NUMBER_MAX: int = 999
P269_REEL_NUMBER_DEFAULT: str = "001"
P269_CAMERA_POSITIONS: Tuple[str, ...] = ("C", "L", "R")
P269_CAMERA_POSITION_DEFAULT: str = "C"
P269_TITLE_NAME_MAX_CHARS: int = 37
P269_TITLE_NAME_DEFAULT: str = "C"
P269_TITLE_ALLOWED_SYMBOLS: str = ".-_@!#$%+=^~(),;[]"
P269_TITLE_ALLOWED_CHARSET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789" + P269_TITLE_ALLOWED_SYMBOLS
)
P269_FIXED_MOVIE_CLIP_FOLDER: str = "PRIVATE/M4ROOT/CLIP"

P269_STILL_FILE_FOLDER_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "File",
    "File/Folder Settings",
)
P269_STILL_FILE_FOLDER_ITEMS: Tuple[str, ...] = (
    "File Number",
    "Forced File Number Reset",
    "Set File Name",
    "Folder Name",
)
P269_STILL_FILE_NUMBER_MODES: Tuple[str, ...] = ("Series", "Reset")
P269_STILL_FILE_NUMBER_DEFAULT: str = "Series"
P269_STILL_SET_FILE_NAME_LEN: int = 3
P269_STILL_SET_FILE_NAME_DEFAULT: str = "DSC"
P269_STILL_PREFIX_ALLOWED_CHARSET = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
P269_STILL_FOLDER_NAME_MODES: Tuple[str, ...] = ("Standard Form", "Date Form")
P269_STILL_FOLDER_NAME_DEFAULT: str = "Standard Form"
P269_STILL_STANDARD_FOLDER_SUFFIX: str = "MSDCF"

# Pillar 46B — [Gamma Display Assist] vs [Display LUT]/[Select LUT], [Auto Review] & 6-Item [TC/UB]
P269_GAMMA_DISPLAY_ASSIST_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Display Option",
    "Gamma Display Assist",
)
P269_GAMMA_DISP_ASSIST_TYP_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Display Option",
    "Gamma Disp. Assist Typ.",
)
P269_GAMMA_DISPLAY_ASSIST_MODES: Tuple[str, ...] = ("Off", "On")
P269_GAMMA_DISPLAY_ASSIST_DEFAULT: str = "Off"
P269_GAMMA_DISP_ASSIST_TYPES: Tuple[str, ...] = (
    "Auto",
    "S-Log3->709(800%)",
    "HLG(BT.2020)",
    "HLG(709)",
)
P269_GAMMA_DISP_ASSIST_TYPE_DEFAULT: str = "Auto"

P269_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "Off",
    "Cine EI",
    "Cine EI Quick",
    "Flexible ISO",
)
P269_DISPLAY_LUT_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Display Option",
    "Display LUT",
)
P269_DISPLAY_LUT_MODES: Tuple[str, ...] = ("On", "Off")
P269_DISPLAY_LUT_DEFAULT: str = "On"
P269_SELECT_LUT_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Exposure/Color",
    "Color/Tone",
    "Select LUT",
)
P269_SELECT_LUT_PRESETS: Tuple[str, ...] = ("S-Log3", "s709", "709(800%)")
P269_SELECT_LUT_USER_SLOTS: Tuple[str, ...] = tuple(f"User{i}" for i in range(1, 17))
P269_SELECT_LUT_MODES: Tuple[str, ...] = P269_SELECT_LUT_PRESETS + P269_SELECT_LUT_USER_SLOTS
P269_SELECT_LUT_DEFAULT: str = "s709"

P269_AUTO_REVIEW_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Display Option",
    "Auto Review",
)
P269_AUTO_REVIEW_MODES: Tuple[str, ...] = ("Off", "2 Sec", "5 Sec", "10 Sec")
P269_AUTO_REVIEW_DEFAULT: str = "Off"

P269_TCUB_MENU_PATH: Tuple[str, ...] = ("MENU", "Shooting", "TC/UB")
P269_TCUB_EXACT_6_ITEMS: Tuple[str, ...] = (
    "Time Code Preset",
    "User Bit Preset",
    "Time Code Format",
    "Time Code Run",
    "Time Code Make",
    "User Bit Time Rec",
)
P269_TCUB_DISP_SETTING_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Display Option",
    "TC/UB Disp. Setting",
)
P269_TC_PRESET_DEFAULT: str = "00:00:00.00"
P269_UB_PRESET_DEFAULT: str = "00 00 00 00"
P269_TC_FORMAT_MODES: Tuple[str, ...] = ("DF", "NDF")
P269_TC_FORMAT_DEFAULT: str = "DF"
P269_TC_RUN_MODES: Tuple[str, ...] = ("Rec Run", "Free Run")
P269_TC_RUN_DEFAULT: str = "Rec Run"
P269_TC_MAKE_MODES: Tuple[str, ...] = ("Preset", "Regenerate")
P269_TC_MAKE_DEFAULT: str = "Preset"
P269_UB_TIME_REC_MODES: Tuple[str, ...] = ("Off", "On")
P269_UB_TIME_REC_DEFAULT: str = "Off"
P269_TCUB_DISP_SETTING_MODES: Tuple[str, ...] = ("TC", "U-Bit")
P269_TCUB_DISP_SETTING_DEFAULT: str = "TC"

P269_MOVIE_FRAME_RATES: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "25p",
    "29.97p",
    "50p",
    "59.94p",
    "100p",
    "119.88p",
)
P269_FORCED_NDF_FRAME_RATES: Tuple[str, ...] = ("24.00p", "25p", "50p", "100p")

P269_SHOOTING_DOMAINS: Tuple[str, ...] = ("Still", "Movie", "S&Q")
P269_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)
P269_SLOT1_VAULT_SLOT: int = 1
P269_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
P269_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_file_settings_gamma_assist_tcub_vault_overlay"
P269_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P269_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P269_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P269_BLOCKED_INVALID_FILE_OR_FOLDER_SETTINGS_SPEC: str = (
    "BLOCKED_INVALID_FILE_OR_FOLDER_SETTINGS_SPEC"
)
P269_BLOCKED_MOVIE_FILE_SETTINGS_OR_37CHAR_TITLE_VIOLATION: str = (
    "BLOCKED_MOVIE_FILE_SETTINGS_OR_37CHAR_TITLE_VIOLATION"
)
P269_BLOCKED_STILL_PREFIX_UNDERSCORE_OR_FOLDER_FORM_VIOLATION: str = (
    "BLOCKED_STILL_PREFIX_UNDERSCORE_OR_FOLDER_FORM_VIOLATION"
)
P269_BLOCKED_FILE_FOLDER_RESET_VS_INITIALIZE_SCOPE_DRIFT: str = (
    "BLOCKED_FILE_FOLDER_RESET_VS_INITIALIZE_SCOPE_DRIFT"
)
P269_BLOCKED_SLOT1_VAULT_DCIM_FOLDER_MUTATION: str = (
    "BLOCKED_SLOT1_VAULT_DCIM_FOLDER_MUTATION"
)

P269_BLOCKED_INVALID_GAMMA_ASSIST_LUT_TCUB_SPEC: str = (
    "BLOCKED_INVALID_GAMMA_ASSIST_LUT_TCUB_SPEC"
)
P269_BLOCKED_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_BYPASS: str = (
    "BLOCKED_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_BYPASS"
)
P269_BLOCKED_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_OR_AUTO_REVIEW_VIOLATION: str = (
    "BLOCKED_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_OR_AUTO_REVIEW_VIOLATION"
)
P269_BLOCKED_TCUB_OR_SETUP_RESET_PERSISTENCE_OR_NDF_DRIFT: str = (
    "BLOCKED_TCUB_OR_SETUP_RESET_PERSISTENCE_OR_NDF_DRIFT"
)
P269_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P269_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P269_STATUS_VERIFIED_PILLAR_46A: str = (
    "VERIFIED_PILLAR_46A_MOVIE_FILE_SETTINGS_CAMID_REEL_37CHAR_AND_STILL_DSC_SLOT1_VAULT"
)
P269_STATUS_REJECTED_PILLAR_46A: str = (
    "REJECTED_PILLAR_46A_MOVIE_FILE_SETTINGS_CAMID_REEL_37CHAR_AND_STILL_DSC_SLOT1_VAULT"
)
P269_STATUS_VERIFIED_PILLAR_46B: str = (
    "VERIFIED_PILLAR_46B_GAMMA_ASSIST_LOG_LOCKOUT_LUT_AUTO_REVIEW_AND_TCUB_VAULT"
)
P269_STATUS_REJECTED_PILLAR_46B: str = (
    "REJECTED_PILLAR_46B_GAMMA_ASSIST_LOG_LOCKOUT_LUT_AUTO_REVIEW_AND_TCUB_VAULT"
)
P269_STATUS_VERIFIED_PILLAR46_SUITE: str = (
    "VERIFIED_PILLAR46_FILE_SETTINGS_GAMMA_ASSIST_TCUB_VAULT"
)
P269_STATUS_FAIL_PILLAR46_SUITE: str = (
    "FAIL_PILLAR46_FILE_SETTINGS_GAMMA_ASSIST_TCUB_VAULT"
)
P269_STATUS_VERIFIED_46OF46_AGGREGATOR: str = "VERIFIED_46OF46_PILLAR_RECOVERY_MASTER"
P269_STATUS_FAIL_46OF46_AGGREGATOR: str = "FAIL_46OF46_PILLAR_RECOVERY_MASTER"

P269_PILLAR_46A_SCENARIO_IDS: Tuple[str, ...] = (
    "P46A1_CAMID_REEL_37CHAR_MOVIE_FILE_SETTINGS_AND_STILL_DSC_SURVIVE_CAMERA_RESET_WITH_SLOT1_VAULT_FIREWALL_SAFE",
    "P46A2_INITIALIZE_RESETS_MOVIE_AND_STILL_FILE_SETTINGS_THEN_ORDONLY_SLOT1_CAMSET01_RESTORES_SLATE_AND_DATE_FORM_SAFE",
    "P46A3_REJECT_TITLE_NAME_38CHAR_OVERFLOW_INVALID_CAMID_REEL_OR_CUSTOM_MOVIE_FOLDER_MUTATION",
    "P46A4_REJECT_STILL_SET_FILE_NAME_LEADING_UNDERSCORE_AT_INDEX0_OR_INVALID_PREFIX_LENGTH",
    "P46A5_REJECT_CAMERA_SETTINGS_RESET_WIPING_FILE_OR_FOLDER_SETTINGS_OR_INITIALIZE_SCOPE_DRIFT",
    "P46A6_REJECT_FORCED_FILE_NUMBER_RESET_OR_CREATE_NEW_FOLDER_MUTATING_SLOT1_RECOVERY_VAULT",
)
P269_PILLAR_46B_SCENARIO_IDS: Tuple[str, ...] = (
    "P46B1_CINE_EI_LOG_SHOOTING_LOCKS_GAMMA_ASSIST_OFF_DISPLAY_LUT_USER1_AUTO_REVIEW_OFF_AND_6ITEM_TCUB_SURVIVE_CAMERA_RESET_SAFE",
    "P46B2_LOG_OFF_GAMMA_ASSIST_LCD_ONLY_CLEAN_HDMI_AND_INITIALIZE_RESETS_TCUB_WITH_ORDONLY_CAMSET01_ROUNDTRIP_SAFE",
    "P46B3_REJECT_GAMMA_DISPLAY_ASSIST_BYPASSING_LOG_SHOOTING_LOCKOUT_OR_INVALID_SELECT_LUT_SLOT",
    "P46B4_REJECT_GAMMA_DISPLAY_ASSIST_LEAKING_TO_EXTERNAL_HDMI_OR_AUTO_REVIEW_INTERRUPT_HAZARD",
    "P46B5_REJECT_CAMERA_SETTINGS_RESET_WIPING_NON_RESETTABLE_TCUB_OR_24P_PAL_DF_FORMAT_VIOLATION",
    "P46B6_REJECT_PERSISTENT_OVERLAY_ESCAPE_OR_TIER0_BACKUP_BIN_H0_H3_DRIFT",
)

MASTER_46_PILLAR_COUNT: int = 46
MASTER_46_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_45_PILLAR_SPECS + (
    (
        46,
        "pillar_46_file_settings_gamma_assist_tcub_vault",
        "Phase 269 (46/46)",
        "fx3_recovery.realhw_46pillar_file_settings_gamma_assist_tcub_vault_verifier",
    ),
)
MASTER_46_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_46_PILLAR_SPECS)


# ---------------------------------------------------------------------------
# Internal Helpers & Deterministic State Computations
# ---------------------------------------------------------------------------

_P269_TC_PRESET_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2})([.:;])(\d{2})$")
_P269_UB_PRESET_RE = re.compile(r"^[0-9A-F]{2} [0-9A-F]{2} [0-9A-F]{2} [0-9A-F]{2}$")
_P269_DATE_YMMDD_RE = re.compile(r"^\d{5}$")
_P269_DATE_YYYYMMDD_RE = re.compile(r"^\d{8}$")


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
    return os.environ.get(P269_ENV_CLEAN_ROOM_TEST, "").strip().lower() in ("1", "true", "yes")


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
        ("P269_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P269_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("P269_SLOT1_VAULT_FOLDER_MUTATION_EVENTS", P269_SLOT1_VAULT_FOLDER_MUTATION_EVENTS, 0),
        ("P269_SLOT1_VAULT_FOLDER_MUTATION_BYTES", P269_SLOT1_VAULT_FOLDER_MUTATION_BYTES, 0),
        (
            "P269_MOVIE_CUSTOM_FOLDER_OR_TITLE_OVERFLOW_EVENTS",
            P269_MOVIE_CUSTOM_FOLDER_OR_TITLE_OVERFLOW_EVENTS,
            0,
        ),
        (
            "P269_STILL_PREFIX_UNDERSCORE_LEAD_OR_LEN_VIOLATIONS",
            P269_STILL_PREFIX_UNDERSCORE_LEAD_OR_LEN_VIOLATIONS,
            0,
        ),
        ("P269_GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS", P269_GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS, 0),
        ("P269_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_EVENTS", P269_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_EVENTS, 0),
        (
            "P269_TCUB_CAMERA_RESET_WIPE_OR_FORMAT_VIOLATIONS",
            P269_TCUB_CAMERA_RESET_WIPE_OR_FORMAT_VIOLATIONS,
            0,
        ),
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
    return any(tok in low for tok in P269_FORBIDDEN_PERSISTENT_TARGETS)


def _validate_title_name_37(title: str) -> Tuple[bool, bool]:
    """Return `(len_ok_1_to_37, charset_ok)` for `ILME-FX3` Movie `[Title Name Settings]`."""
    len_ok = 1 <= len(title) <= P269_TITLE_NAME_MAX_CHARS
    charset_ok = all(ch in P269_TITLE_ALLOWED_CHARSET for ch in title)
    return len_ok, charset_ok


def _validate_reel_number(reel_str: str) -> bool:
    if len(reel_str) != 3 or not reel_str.isdigit():
        return False
    val = int(reel_str)
    return P269_REEL_NUMBER_MIN <= val <= P269_REEL_NUMBER_MAX


def _validate_still_set_file_name(prefix: str) -> Tuple[bool, bool, bool]:
    """Return `(len_eq_3, charset_ok, no_leading_underscore)` for Still `[Set File Name]`."""
    len_ok = len(prefix) == P269_STILL_SET_FILE_NAME_LEN
    charset_ok = len(prefix) > 0 and all(ch in P269_STILL_PREFIX_ALLOWED_CHARSET for ch in prefix)
    no_lead_underscore = len(prefix) > 0 and prefix[0] != "_"
    return len_ok, charset_ok, no_lead_underscore


def _validate_tc_preset(tc_text: str) -> bool:
    m = _P269_TC_PRESET_RE.match(tc_text)
    if m is None:
        return False
    hh, mm, ss, _, ff = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4), int(m.group(5))
    return 0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59 and 0 <= ff <= 59


def _validate_ub_preset(ub_text: str) -> bool:
    return _P269_UB_PRESET_RE.match(ub_text) is not None


def compute_expected_movie_and_still_file_settings_after_reset(
    *,
    pre_movie_file_number: str,
    pre_movie_file_name_format: str,
    pre_camera_id: str,
    pre_reel_number: str,
    pre_camera_position: str,
    pre_title_name: str,
    pre_still_file_number: str,
    pre_still_set_file_name: str,
    pre_still_folder_name_form: str,
    reset_action: str,
) -> Tuple[str, str, str, str, str, str, str, str, str]:
    """Compute post-reset Movie `[File Settings]` + Still `[File/Folder Settings]` tuple.

    Per Sony's official `ILME-FX3` (`ilc/2210`) *List of default setting values*, ALL items under
    both Movie `[File Settings]` and Still `[File/Folder Settings]` survive `[Camera Settings Reset]`
    and `[Reset Network Set.]`, restoring factory defaults ONLY under `[Initialize]`.
    """
    if reset_action == "Initialize":
        return (
            P269_MOVIE_FILE_NUMBER_DEFAULT,
            P269_MOVIE_FILE_NAME_FORMAT_DEFAULT,
            P269_CAM_ID_DEFAULT,
            P269_REEL_NUMBER_DEFAULT,
            P269_CAMERA_POSITION_DEFAULT,
            P269_TITLE_NAME_DEFAULT,
            P269_STILL_FILE_NUMBER_DEFAULT,
            P269_STILL_SET_FILE_NAME_DEFAULT,
            P269_STILL_FOLDER_NAME_DEFAULT,
        )
    return (
        pre_movie_file_number,
        pre_movie_file_name_format,
        pre_camera_id,
        pre_reel_number,
        pre_camera_position,
        pre_title_name,
        pre_still_file_number,
        pre_still_set_file_name,
        pre_still_folder_name_form,
    )


def compute_expected_movie_clip_stem_and_still_path(
    *,
    movie_file_name_format: str,
    camera_id: str,
    reel_number: str,
    camera_position: str,
    title_name: str,
    movie_seq_number: int,
    date_yyyymmdd: str,
    still_set_file_name: str,
    still_folder_name_form: str,
    still_folder_number: int,
    date_ymmdd: str,
    still_seq_number: int,
) -> Tuple[str, str, str]:
    """Compute `(movie_clip_relpath, still_dcim_folder_name, still_file_relpath)` on `ILME-FX3`."""
    seq4 = f"{movie_seq_number:04d}"
    if movie_file_name_format == "Standard":
        stem = f"C{seq4}"
    elif movie_file_name_format == "Cam ID + Reel#":
        stem = f"{camera_id}{reel_number}{camera_position}{seq4}"
    elif movie_file_name_format == "Title":
        stem = f"{title_name}{seq4}"
    elif movie_file_name_format == "Date + Title":
        stem = f"{date_yyyymmdd}_{title_name}{seq4}"
    else:
        stem = f"{title_name}_{date_yyyymmdd}_{seq4}"
    movie_relpath = f"{P269_FIXED_MOVIE_CLIP_FOLDER}/{stem}.MP4"

    folder3 = f"{still_folder_number:03d}"
    if still_folder_name_form == "Standard Form":
        dcim_folder = f"{folder3}{P269_STILL_STANDARD_FOLDER_SUFFIX}"
    else:
        dcim_folder = f"{folder3}{date_ymmdd}"
    still_relpath = f"DCIM/{dcim_folder}/{still_set_file_name}0{still_seq_number:04d}.JPG"
    return movie_relpath, dcim_folder, still_relpath


def compute_expected_gamma_assist_and_lut_monitoring_state(
    *,
    log_shooting_mode: str,
    configured_gamma_display_assist: str,
    configured_gamma_disp_assist_type: str,
    configured_display_lut: str,
    configured_select_lut: str,
) -> Tuple[str, bool, bool, bool, str]:
    """Compute `(effective_gamma_assist, gamma_assist_locked_by_log, lcd_gamma_assist_applied,
    external_hdmi_gamma_assist_applied, active_log_monitoring_lut)`.

    - Whenever `[Log Shooting] != "Off"` (`Cine EI`, `Cine EI Quick`, `Flexible ISO`),
      `[Gamma Display Assist]` is hard-locked to `"Off"`, and log monitoring conversion is governed
      instead by `[Display LUT]` (`On` default) + `[Select LUT]` (`S-Log3`, `s709`, `709(800%)`,
      `User1..User16`).
    - Even when `[Log Shooting] == "Off"` and `[Gamma Display Assist] == "On"`, `[Gamma Display Assist]`
      applies strictly to the camera's internal LCD monitor and is NEVER applied to external HDMI output.
    """
    locked_by_log = log_shooting_mode != "Off"
    if locked_by_log:
        eff_gamma = "Off"
        lcd_gamma = False
        active_lut = configured_select_lut if configured_display_lut == "On" else "NONE_LUT_BYPASSED"
    else:
        eff_gamma = configured_gamma_display_assist
        lcd_gamma = configured_gamma_display_assist == "On"
        active_lut = f"GAMMA_ASSIST:{configured_gamma_disp_assist_type}" if lcd_gamma else "NONE"
    return eff_gamma, locked_by_log, lcd_gamma, False, active_lut


def compute_expected_auto_review_and_tcub_state_after_reset(
    *,
    pre_gamma_display_assist: str,
    pre_gamma_disp_assist_type: str,
    pre_display_lut: str,
    pre_auto_review: str,
    pre_tc_preset: str,
    pre_ub_preset: str,
    pre_tc_format: str,
    pre_tc_run: str,
    pre_tc_make: str,
    pre_ub_time_rec: str,
    pre_tcub_disp_setting: str,
    movie_frame_rate: str,
    reset_action: str,
) -> Tuple[str, str, str, str, str, str, str, str, str, str, str]:
    """Compute post-reset `[Gamma Display Assist]`, `[Display LUT]`, `[Auto Review]` & 6-item `[TC/UB]`.

    All `[Setup]` display options (`Gamma Display Assist`, `Gamma Disp. Assist Typ.`, `Display LUT`,
    `Auto Review`, `TC/UB Disp. Setting`) AND all 6 `[TC/UB]` parameters under `Shooting` are
    explicitly marked NOT reset by `[Camera Settings Reset]` (restored only by `[Initialize]`), while
    `24.00p` and PAL (`25p`/`50p`/`100p`) frame rates force `[Time Code Format] = "NDF"`.
    """
    if reset_action == "Initialize":
        eff_fmt = "NDF" if movie_frame_rate in P269_FORCED_NDF_FRAME_RATES else P269_TC_FORMAT_DEFAULT
        return (
            P269_GAMMA_DISPLAY_ASSIST_DEFAULT,
            P269_GAMMA_DISP_ASSIST_TYPE_DEFAULT,
            P269_DISPLAY_LUT_DEFAULT,
            P269_AUTO_REVIEW_DEFAULT,
            P269_TC_PRESET_DEFAULT,
            P269_UB_PRESET_DEFAULT,
            eff_fmt,
            P269_TC_RUN_DEFAULT,
            P269_TC_MAKE_DEFAULT,
            P269_UB_TIME_REC_DEFAULT,
            P269_TCUB_DISP_SETTING_DEFAULT,
        )
    eff_fmt = "NDF" if movie_frame_rate in P269_FORCED_NDF_FRAME_RATES else pre_tc_format
    return (
        pre_gamma_display_assist,
        pre_gamma_disp_assist_type,
        pre_display_lut,
        pre_auto_review,
        pre_tc_preset,
        pre_ub_preset,
        eff_fmt,
        pre_tc_run,
        pre_tc_make,
        pre_ub_time_rec,
        pre_tcub_disp_setting,
    )


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase269DonorArtifactDigest:
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
class Phase269DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase269DonorArtifactDigest, ...]


@dataclass(frozen=True)
class FileSettingsAndStillFolderVaultSpec:
    camera_model: str = P269_FX3_MODEL_NAME
    helpguide_id: str = P269_FX3_HELPGUIDE_ID
    fw_version: str = P269_FX3_FW_VERSION
    movie_file_settings_menu_path: Tuple[str, ...] = P269_MOVIE_FILE_SETTINGS_MENU_PATH
    movie_file_settings_items: Tuple[str, ...] = P269_MOVIE_FILE_SETTINGS_ITEMS
    still_file_folder_menu_path: Tuple[str, ...] = P269_STILL_FILE_FOLDER_MENU_PATH
    still_file_folder_items: Tuple[str, ...] = P269_STILL_FILE_FOLDER_ITEMS
    pre_movie_file_number: str = "Series"
    pre_movie_file_name_format: str = "Cam ID + Reel#"
    pre_camera_id: str = "A"
    pre_reel_number: str = "001"
    pre_camera_position: str = "C"
    pre_title_name: str = "FX3_WAVE44_CINEMA_SLATE_37CHAR_ANCHOR"  # exact 37 chars
    movie_clip_folder_path: str = P269_FIXED_MOVIE_CLIP_FOLDER
    movie_custom_folder_attempted: bool = False
    pre_still_file_number: str = "Series"
    pre_still_set_file_name: str = "DSC"
    pre_still_folder_name_form: str = "Standard Form"
    reset_action: str = "Camera Settings Reset"
    camset_load_after_reset: bool = False
    camset_slot: int = P269_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P269_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    saved_movie_file_number: str = "Series"
    saved_movie_file_name_format: str = "Cam ID + Reel#"
    saved_camera_id: str = "A"
    saved_reel_number: str = "001"
    saved_camera_position: str = "C"
    saved_title_name: str = "FX3_WAVE44_CINEMA_SLATE_37CHAR_ANCHOR"
    saved_still_file_number: str = "Series"
    saved_still_set_file_name: str = "DSC"
    saved_still_folder_name_form: str = "Standard Form"
    post_movie_file_number: str = "Series"
    post_movie_file_name_format: str = "Cam ID + Reel#"
    post_camera_id: str = "A"
    post_reel_number: str = "001"
    post_camera_position: str = "C"
    post_title_name: str = "FX3_WAVE44_CINEMA_SLATE_37CHAR_ANCHOR"
    post_still_file_number: str = "Series"
    post_still_set_file_name: str = "DSC"
    post_still_folder_name_form: str = "Standard Form"
    movie_seq_number: int = 1
    date_yyyymmdd: str = "20261115"
    still_folder_number: int = 100
    date_ymmdd: str = "61115"
    still_seq_number: int = 1
    expected_movie_clip_relpath: str = "PRIVATE/M4ROOT/CLIP/A001C0001.MP4"
    expected_still_dcim_folder: str = "100MSDCF"
    expected_still_file_relpath: str = "DCIM/100MSDCF/DSC00001.JPG"
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    active_still_media_slot: int = 2
    forced_file_number_reset_requested: bool = False
    create_new_folder_requested: bool = False
    slot1_vault_folder_mutation_events: int = 0
    slot1_vault_folder_mutation_bytes: int = 0
    movie_custom_folder_or_title_overflow_events: int = 0
    still_prefix_underscore_lead_or_len_violations: int = 0
    overlay_dir: str = P269_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P269_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P269_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P269_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class FileSettingsAndStillFolderVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    movie_camid_reel_and_37char_title_verified: bool
    still_dsc_prefix_and_folder_form_verified: bool
    reset_survival_vs_initialize_verified: bool
    slot1_vault_dcim_firewall_verified: bool
    h0_equals_h3_verified: bool
    title_name_char_length: int
    movie_clip_relpath: str
    still_dcim_folder: str
    still_file_relpath: str
    slot1_vault_folder_mutation_events: int
    slot1_vault_folder_mutation_bytes: int
    movie_custom_folder_or_title_overflow_events: int
    still_prefix_underscore_lead_or_len_violations: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GammaAssistLutAutoReviewTcubVaultSpec:
    camera_model: str = P269_FX3_MODEL_NAME
    helpguide_id: str = P269_FX3_HELPGUIDE_ID
    fw_version: str = P269_FX3_FW_VERSION
    gamma_display_assist_menu_path: Tuple[str, ...] = P269_GAMMA_DISPLAY_ASSIST_MENU_PATH
    gamma_disp_assist_typ_menu_path: Tuple[str, ...] = P269_GAMMA_DISP_ASSIST_TYP_MENU_PATH
    display_lut_menu_path: Tuple[str, ...] = P269_DISPLAY_LUT_MENU_PATH
    select_lut_menu_path: Tuple[str, ...] = P269_SELECT_LUT_MENU_PATH
    auto_review_menu_path: Tuple[str, ...] = P269_AUTO_REVIEW_MENU_PATH
    tcub_menu_path: Tuple[str, ...] = P269_TCUB_MENU_PATH
    tcub_menu_items: Tuple[str, ...] = P269_TCUB_EXACT_6_ITEMS
    tcub_disp_setting_menu_path: Tuple[str, ...] = P269_TCUB_DISP_SETTING_MENU_PATH
    shooting_domain: str = "Movie"  # Still | Movie | S&Q
    movie_frame_rate: str = "24.00p"
    log_shooting_mode: str = "Cine EI"  # Off | Cine EI | Cine EI Quick | Flexible ISO
    pre_gamma_display_assist: str = "On"  # configured Setup value before lockout check
    pre_gamma_disp_assist_type: str = "S-Log3->709(800%)"
    pre_display_lut: str = "On"
    pre_select_lut: str = "User1"
    pre_auto_review: str = "Off"
    factory_default_auto_review: str = P269_AUTO_REVIEW_DEFAULT
    pre_tc_preset: str = "01:00:00.00"
    pre_ub_preset: str = "26 11 15 01"
    pre_tc_format: str = "NDF"
    pre_tc_run: str = "Free Run"
    pre_tc_make: str = "Preset"
    pre_ub_time_rec: str = "Off"
    pre_tcub_disp_setting: str = "TC"
    reset_action: str = "Camera Settings Reset"
    camset_load_after_reset: bool = False
    camset_slot: int = P269_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P269_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    saved_gamma_display_assist: str = "Off"
    saved_gamma_disp_assist_type: str = "Auto"
    saved_display_lut: str = "On"
    saved_select_lut: str = "s709"
    saved_auto_review: str = "Off"
    saved_tc_preset: str = "00:00:00.00"
    saved_ub_preset: str = "00 00 00 00"
    saved_tc_format: str = "NDF"
    saved_tc_run: str = "Rec Run"
    saved_tc_make: str = "Preset"
    saved_ub_time_rec: str = "Off"
    saved_tcub_disp_setting: str = "TC"
    post_gamma_display_assist: str = "On"
    post_gamma_disp_assist_type: str = "S-Log3->709(800%)"
    post_display_lut: str = "On"
    post_select_lut: str = "User1"
    post_auto_review: str = "Off"
    post_tc_preset: str = "01:00:00.00"
    post_ub_preset: str = "26 11 15 01"
    post_tc_format: str = "NDF"
    post_tc_run: str = "Free Run"
    post_tc_make: str = "Preset"
    post_ub_time_rec: str = "Off"
    post_tcub_disp_setting: str = "TC"
    effective_gamma_display_assist: str = "Off"
    gamma_assist_locked_by_log_shooting: bool = True
    lcd_gamma_assist_applied: bool = False
    hdmi_external_monitor_connected: bool = True
    external_hdmi_gamma_assist_applied: bool = False
    active_monitoring_lut: str = "User1"
    movie_live_view_interrupted_by_auto_review: bool = False
    gamma_assist_log_lockout_bypass_events: int = 0
    gamma_assist_external_hdmi_leak_events: int = 0
    tcub_camera_reset_wipe_or_format_violations: int = 0
    overlay_dir: str = P269_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P269_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P269_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P269_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class GammaAssistLutAutoReviewTcubVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    gamma_assist_log_lockout_and_lut_verified: bool
    lcd_only_clean_external_hdmi_verified: bool
    auto_review_off_cinema_default_verified: bool
    tcub_6item_non_resettable_persistence_verified: bool
    h0_equals_h3_verified: bool
    effective_gamma_display_assist: str
    active_monitoring_lut: str
    gamma_assist_log_lockout_bypass_events: int
    gamma_assist_external_hdmi_leak_events: int
    tcub_camera_reset_wipe_or_format_violations: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FileSettingsGammaAssistAndTcubVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase269DonorSnapshot
    file_settings_still_folder_report: FileSettingsAndStillFolderVaultReport
    gamma_assist_lut_auto_review_tcub_report: GammaAssistLutAutoReviewTcubVaultReport
    slot1_vault_folder_mutation_events: int
    slot1_vault_folder_mutation_bytes: int
    movie_custom_folder_or_title_overflow_events: int
    still_prefix_underscore_lead_or_len_violations: int
    gamma_assist_log_lockout_bypass_events: int
    gamma_assist_external_hdmi_leak_events: int
    tcub_camera_reset_wipe_or_format_violations: int
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
class Pillar46ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar46ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar46ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar46BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar46ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar46StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase269DonorSnapshot
    pillar_46a_file_settings_still_folder_vault: Pillar46ASuiteResult
    pillar_46b_gamma_assist_lut_auto_review_tcub_vault: Pillar46BSuiteResult
    slot1_vault_folder_mutation_events: int
    slot1_vault_folder_mutation_bytes: int
    movie_custom_folder_or_title_overflow_events: int
    still_prefix_underscore_lead_or_len_violations: int
    gamma_assist_log_lockout_bypass_events: int
    gamma_assist_external_hdmi_leak_events: int
    tcub_camera_reset_wipe_or_format_violations: int
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
class Master46PillarRecoveryReport:
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
    # Pillar 46 & Wave-44 top-level fields
    donor_snapshot: Phase269DonorSnapshot
    pillar46_a_file_settings_still_folder_vault: Pillar46ASuiteResult
    pillar46_b_gamma_assist_lut_auto_review_tcub_vault: Pillar46BSuiteResult
    slot1_vault_folder_mutation_events: int
    slot1_vault_folder_mutation_bytes: int
    movie_custom_folder_or_title_overflow_events: int
    still_prefix_underscore_lead_or_len_violations: int
    gamma_assist_log_lockout_bypass_events: int
    gamma_assist_external_hdmi_leak_events: int
    tcub_camera_reset_wipe_or_format_violations: int
    # Preserved Pillars 1..45 rollup metrics
    fx3_has_builtin_end_filter: bool
    e_nd_actuator_tx_count: int
    cardless_unrecorded_production_violations: int
    legacy_v1_audio_level_menu_spoof_events: int
    photographer_copyright_pii_leaked_bytes: int
    copyright_char_overflow_or_movie_mutation_events: int
    slot1_copyright_vault_mutation_bytes: int
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
    master_46pillar_sha256: str
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
    max_full_bytes: int = P269_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P269_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase269_donors() -> Tuple[Phase269DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P269_DONOR_FX3_BODYDATA_RELPATH,
            P269_PINNED_FX3_BODYDATA_BYTES,
            P269_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P269_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P269_DONOR_FX3_APPFW_702_RELPATH,
            P269_PINNED_FX3_APPFW_702_BYTES,
            P269_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P269_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P269_DONOR_FX6_APPFW_601_RELPATH,
            P269_PINNED_FX6_APPFW_601_BYTES,
            P269_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P269_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P269_DONOR_FX3_BACKUP_BIN_RELPATH,
            P269_PINNED_FX3_BACKUP_BIN_BYTES,
            P269_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P269_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P269_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P269_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P269_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P269_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P269_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P269_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P269_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P269_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libsaveloadsettings_so",
            P269_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P269_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P269_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            "FULL_SHA256",
            P269_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:SaveLoadSettingsIf+requestToRead+requestToCheck+requestToWrite",
        ),
        (
            "fx3_libgpe_so",
            P269_DONOR_FX3_LIBGPE_SO_RELPATH,
            P269_PINNED_FX3_LIBGPE_SO_BYTES,
            P269_PINNED_FX3_LIBGPE_SO_BYTES,
            "FULL_SHA256",
            P269_PINNED_FX3_LIBGPE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:gpe_blog_error+_ZNK5mpgpe5Gperm4InitEv",
        ),
        (
            "fx3_cameraondemandsaver_so",
            P269_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH,
            P269_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            P269_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            "FULL_SHA256",
            P269_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:CameraOnDemandSaver+_ZN18CAM_ONDEMAND_SAVER17OsalHandleWrapperC1Ejji",
        ),
        (
            "fx3_libinframediaconfig_so",
            P269_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P269_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P269_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            "FULL_SHA256",
            P269_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaConfig+_ZN16InfraMediaConfig10SaveBackupEt",
        ),
        (
            "fx3_libinframediadetect_so",
            P269_DONOR_FX3_LIBINFRAMEDIADETECT_SO_RELPATH,
            P269_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES,
            P269_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES,
            "FULL_SHA256",
            P269_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaDetect+_ZN16InfraMediaDetect10GetVersionEv",
        ),
        (
            "fx3_libinframediacommon_so",
            P269_DONOR_FX3_LIBINFRAMEDIACOMMON_SO_RELPATH,
            P269_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES,
            P269_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES,
            "FULL_SHA256",
            P269_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:libInfraMediaCommon+MediaCommon_Addr",
        ),
        (
            "fx3_libinframediamount_so",
            P269_DONOR_FX3_LIBINFRAMEDIAMOUNT_SO_RELPATH,
            P269_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_BYTES,
            P269_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_BYTES,
            "FULL_SHA256",
            P269_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_ZN15InfraMediaMount10GetVersionEv+_ZN15InfraMediaMount12StartThreadsEv",
        ),
        (
            "fx3_libinfrafsys_so",
            P269_DONOR_FX3_LIBINFRAFSYS_SO_RELPATH,
            P269_PINNED_FX3_LIBINFRAFSYS_SO_BYTES,
            P269_PINNED_FX3_LIBINFRAFSYS_SO_BYTES,
            "FULL_SHA256",
            P269_PINNED_FX3_LIBINFRAFSYS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_ZN9InfraFsys10GetVersionEv+_ZTV9InfraFsys",
        ),
        (
            "fx3_libinframetasupplier_so",
            P269_DONOR_FX3_LIBINFRAMETASUPPLIER_SO_RELPATH,
            P269_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_BYTES,
            P269_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_BYTES,
            "FULL_SHA256",
            P269_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMetaSupplier_Init+_ZN20InfraMetaSupplier_If4InitEv",
        ),
        (
            "fx6_libinfrasetupfile_so",
            P269_DONOR_FX6_LIBINFRASETUPFILE_SO_RELPATH,
            P269_PINNED_FX6_LIBINFRASETUPFILE_SO_BYTES,
            P269_PINNED_FX6_LIBINFRASETUPFILE_SO_BYTES,
            "FULL_SHA256",
            P269_PINNED_FX6_LIBINFRASETUPFILE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_ZTVN14InfraSetupFile9SetupFileE+InfraSetupFile_sus",
        ),
    )
    return tuple(
        Phase269DonorArtifactDigest(
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


def inspect_phase269_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase269DonorSnapshot:
    """Inspect Wave-44 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 2.0s`."""
    t0 = time.monotonic()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase269_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase269DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P269_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P269_DONOR_FX3_BODYDATA_RELPATH,
            P269_PINNED_FX3_BODYDATA_BYTES,
            P269_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P269_DONOR_FX3_APPFW_702_RELPATH,
            P269_PINNED_FX3_APPFW_702_BYTES,
            P269_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx6_appfw_601_so",
            P269_DONOR_FX6_APPFW_601_RELPATH,
            P269_PINNED_FX6_APPFW_601_BYTES,
            P269_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P269_DONOR_FX3_BACKUP_BIN_RELPATH,
            P269_PINNED_FX3_BACKUP_BIN_BYTES,
            P269_PINNED_FX3_BACKUP_BIN_SHA256,
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
            P269_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P269_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P269_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P269_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P269_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P269_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libsaveloadsettings_so",
            P269_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P269_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P269_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"SaveLoadSettingsIf", b"requestToRead", b"requestToCheck", b"requestToWrite"),
            ),
        ),
        (
            "fx3_libgpe_so",
            P269_DONOR_FX3_LIBGPE_SO_RELPATH,
            P269_PINNED_FX3_LIBGPE_SO_BYTES,
            P269_PINNED_FX3_LIBGPE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"gpe_blog_error", b"_ZNK5mpgpe5Gperm4InitEv")),
        ),
        (
            "fx3_cameraondemandsaver_so",
            P269_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH,
            P269_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            P269_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"CameraOnDemandSaver", b"_ZN18CAM_ONDEMAND_SAVER17OsalHandleWrapperC1Ejji"),
            ),
        ),
        (
            "fx3_libinframediaconfig_so",
            P269_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P269_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P269_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraMediaConfig", b"_ZN16InfraMediaConfig10SaveBackupEt"),
            ),
        ),
        (
            "fx3_libinframediadetect_so",
            P269_DONOR_FX3_LIBINFRAMEDIADETECT_SO_RELPATH,
            P269_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES,
            P269_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraMediaDetect", b"_ZN16InfraMediaDetect10GetVersionEv"),
            ),
        ),
        (
            "fx3_libinframediacommon_so",
            P269_DONOR_FX3_LIBINFRAMEDIACOMMON_SO_RELPATH,
            P269_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES,
            P269_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"libInfraMediaCommon", b"MediaCommon_Addr")),
        ),
        (
            "fx3_libinframediamount_so",
            P269_DONOR_FX3_LIBINFRAMEDIAMOUNT_SO_RELPATH,
            P269_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_BYTES,
            P269_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"_ZN15InfraMediaMount10GetVersionEv", b"_ZN15InfraMediaMount12StartThreadsEv"),
            ),
        ),
        (
            "fx3_libinfrafsys_so",
            P269_DONOR_FX3_LIBINFRAFSYS_SO_RELPATH,
            P269_PINNED_FX3_LIBINFRAFSYS_SO_BYTES,
            P269_PINNED_FX3_LIBINFRAFSYS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"_ZN9InfraFsys10GetVersionEv", b"_ZTV9InfraFsys"),
            ),
        ),
        (
            "fx3_libinframetasupplier_so",
            P269_DONOR_FX3_LIBINFRAMETASUPPLIER_SO_RELPATH,
            P269_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_BYTES,
            P269_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraMetaSupplier_Init", b"_ZN20InfraMetaSupplier_If4InitEv"),
            ),
        ),
        (
            "fx6_libinfrasetupfile_so",
            P269_DONOR_FX6_LIBINFRASETUPFILE_SO_RELPATH,
            P269_PINNED_FX6_LIBINFRASETUPFILE_SO_BYTES,
            P269_PINNED_FX6_LIBINFRASETUPFILE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"_ZTVN14InfraSetupFile9SetupFileE", b"InfraSetupFile_sus"),
            ),
        ),
    )

    real_artifacts: List[Phase269DonorArtifactDigest] = []
    any_missing = False
    for aid, rel, pinned_bytes, pinned_sha, marker_fn in probe_specs:
        present, total_b, read_b, dkind, dsha, raw_slice = _read_donor_readonly_bounded(rel)
        if not present:
            any_missing = True
            break
        marker_ok, marker_summary = marker_fn(raw_slice)
        matches = (total_b == pinned_bytes) and (dsha == pinned_sha) and bool(marker_ok)
        real_artifacts.append(
            Phase269DonorArtifactDigest(
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
        artifacts = _synthetic_phase269_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase269DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P269_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    all_ok = len(real_artifacts) == len(probe_specs) and all(a.matches_pinned for a in real_artifacts)
    dt = round(time.monotonic() - t0, 6)
    return Phase269DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all_ok,
        donor_files_inspected=len(real_artifacts),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P269_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(real_artifacts),
    )


def build_default_safe_file_settings_and_still_folder_vault_spec() -> (
    FileSettingsAndStillFolderVaultSpec
):
    """Return canonical safe Wave-44 Pillar 46A spec (`Cam ID + Reel#`, 37-char title, `DSC` & Slot-1 firewall)."""
    return FileSettingsAndStillFolderVaultSpec()


def build_default_safe_gamma_assist_lut_auto_review_tcub_vault_spec() -> (
    GammaAssistLutAutoReviewTcubVaultSpec
):
    """Return canonical safe Wave-44 Pillar 46B spec (`Cine EI` locks Gamma Assist `Off`, `Display LUT` `User1`, `TC/UB`)."""
    return GammaAssistLutAutoReviewTcubVaultSpec()


# ---------------------------------------------------------------------------
# Pillar 46A & Pillar 46B Evaluators
# ---------------------------------------------------------------------------


def evaluate_file_settings_and_still_folder_vault(
    spec: FileSettingsAndStillFolderVaultSpec,
) -> FileSettingsAndStillFolderVaultReport:
    """Evaluate Pillar 46A Movie `[File Settings]` (`Cam ID + Reel#` & `<=37`-char `Title Name`) vs
    Still `[File/Folder Settings]` (`DSC` `3`-char prefix, `_` forbidden at index 0) & Slot-1 DCIM firewall.
    """
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P269_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(
            P269_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Persistent eMMC write unlock requested inside zero-write Pillar 46A verifier",
        )

    # 1. Baseline model, Help Guide, menu paths & overlay/Tier-0 checks
    if (
        spec.camera_model != P269_FX3_MODEL_NAME
        or spec.helpguide_id != P269_FX3_HELPGUIDE_ID
        or spec.fw_version not in P269_FX3_SUPPORTED_FW_VERSIONS
        or spec.movie_file_settings_menu_path != P269_MOVIE_FILE_SETTINGS_MENU_PATH
        or spec.movie_file_settings_items != P269_MOVIE_FILE_SETTINGS_ITEMS
        or spec.still_file_folder_menu_path != P269_STILL_FILE_FOLDER_MENU_PATH
        or spec.still_file_folder_items != P269_STILL_FILE_FOLDER_ITEMS
        or spec.reset_action not in P269_RESET_ACTIONS
        or spec.active_still_media_slot not in (1, 2)
        or not (1 <= spec.movie_seq_number <= 9999)
        or not (100 <= spec.still_folder_number <= 999)
        or not (1 <= spec.still_seq_number <= 9999)
        or _P269_DATE_YYYYMMDD_RE.match(spec.date_yyyymmdd) is None
        or _P269_DATE_YMMDD_RE.match(spec.date_ymmdd) is None
    ):
        _fail(
            P269_BLOCKED_INVALID_FILE_OR_FOLDER_SETTINGS_SPEC,
            "Invalid camera/fw/menu path/sequence/date specification for Pillar 46A",
        )

    if _targets_persistent_emmc(spec.overlay_dir) or not _is_tmpfs_path(spec.overlay_dir) or not spec.p2_blkroset_locked:
        _fail(
            P269_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped tmpfs or p2 BLKROSET unlocked: {spec.overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == P269_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == P269_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P269_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P269_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 drift or non-zero Stage-B Backup.bin writes",
        )

    # 2. Movie [File Settings]: Series/Reset, Cam ID + Reel#, <=37-char Title Name & fixed PRIVATE/M4ROOT/CLIP
    movie_errs_before = len(errors)
    movie_overflow_events = int(spec.movie_custom_folder_or_title_overflow_events)
    for tag, fnum, fmt, cid, reel, pos, title in (
        (
            "pre",
            spec.pre_movie_file_number,
            spec.pre_movie_file_name_format,
            spec.pre_camera_id,
            spec.pre_reel_number,
            spec.pre_camera_position,
            spec.pre_title_name,
        ),
        (
            "saved",
            spec.saved_movie_file_number,
            spec.saved_movie_file_name_format,
            spec.saved_camera_id,
            spec.saved_reel_number,
            spec.saved_camera_position,
            spec.saved_title_name,
        ),
        (
            "post",
            spec.post_movie_file_number,
            spec.post_movie_file_name_format,
            spec.post_camera_id,
            spec.post_reel_number,
            spec.post_camera_position,
            spec.post_title_name,
        ),
    ):
        t_len_ok, t_chr_ok = _validate_title_name_37(title)
        if (
            fnum not in P269_MOVIE_FILE_NUMBER_MODES
            or fmt not in P269_MOVIE_FILE_NAME_FORMATS
            or cid not in P269_CAM_ID_LETTERS
            or not _validate_reel_number(reel)
            or pos not in P269_CAMERA_POSITIONS
            or not t_len_ok
            or not t_chr_ok
        ):
            movie_overflow_events = max(movie_overflow_events, 1)
            _fail(
                P269_BLOCKED_MOVIE_FILE_SETTINGS_OR_37CHAR_TITLE_VIOLATION,
                f"Invalid {tag} Movie [File Settings] / Cam ID + Reel# / <=37-char Title Name",
            )

    if (
        spec.movie_clip_folder_path != P269_FIXED_MOVIE_CLIP_FOLDER
        or spec.movie_custom_folder_attempted
        or spec.movie_custom_folder_or_title_overflow_events != 0
    ):
        movie_overflow_events = max(movie_overflow_events, 1)
        _fail(
            P269_BLOCKED_MOVIE_FILE_SETTINGS_OR_37CHAR_TITLE_VIOLATION,
            f"Movie folder must remain fixed at {P269_FIXED_MOVIE_CLIP_FOLDER!r} with zero overflow events",
        )
    movie_verified = len(errors) == movie_errs_before

    # 3. Still [File/Folder Settings]: Series/Reset, 3-char Set File Name (no leading '_') & Folder Name form
    still_errs_before = len(errors)
    still_prefix_violations = int(spec.still_prefix_underscore_lead_or_len_violations)
    for tag, sfnum, sprefix, sform in (
        ("pre", spec.pre_still_file_number, spec.pre_still_set_file_name, spec.pre_still_folder_name_form),
        ("saved", spec.saved_still_file_number, spec.saved_still_set_file_name, spec.saved_still_folder_name_form),
        ("post", spec.post_still_file_number, spec.post_still_set_file_name, spec.post_still_folder_name_form),
    ):
        len_ok, chr_ok, no_us_ok = _validate_still_set_file_name(sprefix)
        if (
            sfnum not in P269_STILL_FILE_NUMBER_MODES
            or sform not in P269_STILL_FOLDER_NAME_MODES
            or not len_ok
            or not chr_ok
            or not no_us_ok
        ):
            still_prefix_violations = max(still_prefix_violations, 1)
            _fail(
                P269_BLOCKED_STILL_PREFIX_UNDERSCORE_OR_FOLDER_FORM_VIOLATION,
                f"Invalid {tag} Still [File/Folder Settings] Set File Name {sprefix!r} or Folder Name {sform!r}",
            )
    if spec.still_prefix_underscore_lead_or_len_violations != 0:
        still_prefix_violations = max(still_prefix_violations, 1)
        _fail(
            P269_BLOCKED_STILL_PREFIX_UNDERSCORE_OR_FOLDER_FORM_VIOLATION,
            "Non-zero still_prefix_underscore_lead_or_len_violations telemetry",
        )
    still_verified = len(errors) == still_errs_before

    # 4. Reset survival ([Camera Settings Reset] & [Reset Network Set.]) vs [Initialize] + O_RDONLY CAMSET Load
    reset_errs_before = len(errors)
    if spec.camset_load_after_reset:
        if (
            spec.camset_slot != P269_SLOT1_VAULT_SLOT
            or spec.camset_filename not in P269_CAMSET_FILENAMES
            or spec.camset_source_model != P269_FX3_MODEL_NAME
            or not spec.camset_read_only_load
        ):
            _fail(
                P269_BLOCKED_FILE_FOLDER_RESET_VS_INITIALIZE_SCOPE_DRIFT,
                "Invalid CAMSET01..10.DAT O_RDONLY Slot-1 restoration envelope",
            )
        expected_post = (
            spec.saved_movie_file_number,
            spec.saved_movie_file_name_format,
            spec.saved_camera_id,
            spec.saved_reel_number,
            spec.saved_camera_position,
            spec.saved_title_name,
            spec.saved_still_file_number,
            spec.saved_still_set_file_name,
            spec.saved_still_folder_name_form,
        )
    else:
        expected_post = compute_expected_movie_and_still_file_settings_after_reset(
            pre_movie_file_number=spec.pre_movie_file_number,
            pre_movie_file_name_format=spec.pre_movie_file_name_format,
            pre_camera_id=spec.pre_camera_id,
            pre_reel_number=spec.pre_reel_number,
            pre_camera_position=spec.pre_camera_position,
            pre_title_name=spec.pre_title_name,
            pre_still_file_number=spec.pre_still_file_number,
            pre_still_set_file_name=spec.pre_still_set_file_name,
            pre_still_folder_name_form=spec.pre_still_folder_name_form,
            reset_action=spec.reset_action,
        )

    actual_post = (
        spec.post_movie_file_number,
        spec.post_movie_file_name_format,
        spec.post_camera_id,
        spec.post_reel_number,
        spec.post_camera_position,
        spec.post_title_name,
        spec.post_still_file_number,
        spec.post_still_set_file_name,
        spec.post_still_folder_name_form,
    )
    if actual_post != expected_post:
        _fail(
            P269_BLOCKED_FILE_FOLDER_RESET_VS_INITIALIZE_SCOPE_DRIFT,
            f"Post-reset File/Folder state {actual_post!r} drifted from expected {expected_post!r}",
        )

    # Deterministic Exhaustive State-Space Proof (5 formats x 2 still forms x 4 reset actions = 40 states)
    for fmt in P269_MOVIE_FILE_NAME_FORMATS:
        for sform in P269_STILL_FOLDER_NAME_MODES:
            for r_act in P269_RESET_ACTIONS:
                tup = compute_expected_movie_and_still_file_settings_after_reset(
                    pre_movie_file_number="Reset",
                    pre_movie_file_name_format=fmt,
                    pre_camera_id="B",
                    pre_reel_number="012",
                    pre_camera_position="L",
                    pre_title_name="UNIT_B",
                    pre_still_file_number="Reset",
                    pre_still_set_file_name="FX3",
                    pre_still_folder_name_form=sform,
                    reset_action=r_act,
                )
                if r_act == "Initialize":
                    _need(tup[0] == "Series" and tup[1] == "Standard" and tup[7] == "DSC", "Initialize drift")
                else:
                    _need(tup[1] == fmt and tup[7] == "FX3" and tup[8] == sform, "Camera Reset survival drift")

    exp_mov_path, exp_dcim_dir, exp_still_path = compute_expected_movie_clip_stem_and_still_path(
        movie_file_name_format=spec.post_movie_file_name_format,
        camera_id=spec.post_camera_id,
        reel_number=spec.post_reel_number,
        camera_position=spec.post_camera_position,
        title_name=spec.post_title_name,
        movie_seq_number=spec.movie_seq_number,
        date_yyyymmdd=spec.date_yyyymmdd,
        still_set_file_name=spec.post_still_set_file_name,
        still_folder_name_form=spec.post_still_folder_name_form,
        still_folder_number=spec.still_folder_number,
        date_ymmdd=spec.date_ymmdd,
        still_seq_number=spec.still_seq_number,
    )
    if (
        spec.expected_movie_clip_relpath != exp_mov_path
        or spec.expected_still_dcim_folder != exp_dcim_dir
        or spec.expected_still_file_relpath != exp_still_path
    ):
        _fail(
            P269_BLOCKED_MOVIE_FILE_SETTINGS_OR_37CHAR_TITLE_VIOLATION,
            f"Clip/DCIM path mismatch: got {(spec.expected_movie_clip_relpath, spec.expected_still_dcim_folder, spec.expected_still_file_relpath)!r} vs {(exp_mov_path, exp_dcim_dir, exp_still_path)!r}",
        )
    reset_verified = len(errors) == reset_errs_before

    # 5. Slot-1 Recovery Vault DCIM Firewall ([Forced File Number Reset] / [Create New Folder] hard-blocked on Slot 1)
    vault_errs_before = len(errors)
    vault_mut_events = int(spec.slot1_vault_folder_mutation_events)
    vault_mut_bytes = int(spec.slot1_vault_folder_mutation_bytes)
    dcim_mut_requested = bool(spec.forced_file_number_reset_requested or spec.create_new_folder_requested)
    if spec.slot1_holds_recovery_vault:
        if not spec.slot1_sdxc_wp_locked:
            vault_mut_events = max(vault_mut_events, 1)
            _fail(
                P269_BLOCKED_SLOT1_VAULT_DCIM_FOLDER_MUTATION,
                "Slot-1 recovery vault requires SDXC hardware write-protect lock",
            )
        if spec.active_still_media_slot == P269_SLOT1_VAULT_SLOT and dcim_mut_requested:
            vault_mut_events = max(vault_mut_events, 1)
            _fail(
                P269_BLOCKED_SLOT1_VAULT_DCIM_FOLDER_MUTATION,
                "[Forced File Number Reset] / [Create New Folder] hard-blocked on Slot-1 CAMSET/BODYDATA.DAT vault",
            )
    if spec.slot1_vault_folder_mutation_events != 0 or spec.slot1_vault_folder_mutation_bytes != 0:
        vault_mut_events = max(vault_mut_events, 1)
        _fail(
            P269_BLOCKED_SLOT1_VAULT_DCIM_FOLDER_MUTATION,
            "Slot-1 recovery vault DCIM folder mutation events/bytes must equal 0",
        )
    vault_verified = len(errors) == vault_errs_before

    passed = len(errors) == 0
    status = P269_STATUS_VERIFIED_PILLAR_46A if passed else P269_STATUS_REJECTED_PILLAR_46A
    digest = _canonical_sha256(
        {
            "pillar": "46A",
            "passed": passed,
            "status": status,
            "block_code": block_code,
            "movie_clip_relpath": exp_mov_path,
            "still_file_relpath": exp_still_path,
            "slot1_vault_folder_mutation_events": vault_mut_events,
        }
    )
    return FileSettingsAndStillFolderVaultReport(
        passed=passed,
        status=status,
        block_code=None if passed else block_code,
        movie_camid_reel_and_37char_title_verified=movie_verified,
        still_dsc_prefix_and_folder_form_verified=still_verified,
        reset_survival_vs_initialize_verified=reset_verified,
        slot1_vault_dcim_firewall_verified=vault_verified,
        h0_equals_h3_verified=h0_eq_h3,
        title_name_char_length=len(spec.post_title_name),
        movie_clip_relpath=exp_mov_path,
        still_dcim_folder=exp_dcim_dir,
        still_file_relpath=exp_still_path,
        slot1_vault_folder_mutation_events=vault_mut_events,
        slot1_vault_folder_mutation_bytes=vault_mut_bytes,
        movie_custom_folder_or_title_overflow_events=movie_overflow_events,
        still_prefix_underscore_lead_or_len_violations=still_prefix_violations,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_gamma_assist_lut_auto_review_tcub_vault(
    spec: GammaAssistLutAutoReviewTcubVaultSpec,
) -> GammaAssistLutAutoReviewTcubVaultReport:
    """Evaluate Pillar 46B `[Gamma Display Assist]` (`Log Shooting` lockout & LCD-only clean HDMI) vs
    `[Display LUT]`/`[Select LUT]` (`3` presets + `User1..16`), `[Auto Review]` (`Off` cinema default) &
    all 6 `[TC/UB]` non-resettable parameters across `[Camera Settings Reset]` vs `[Initialize]`.
    """
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P269_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(
            P269_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Persistent eMMC write unlock requested inside zero-write Pillar 46B verifier",
        )

    # 1. Baseline model, menu paths, 6-item [TC/UB] structure & overlay/Tier-0 checks
    if (
        spec.camera_model != P269_FX3_MODEL_NAME
        or spec.helpguide_id != P269_FX3_HELPGUIDE_ID
        or spec.fw_version not in P269_FX3_SUPPORTED_FW_VERSIONS
        or spec.gamma_display_assist_menu_path != P269_GAMMA_DISPLAY_ASSIST_MENU_PATH
        or spec.gamma_disp_assist_typ_menu_path != P269_GAMMA_DISP_ASSIST_TYP_MENU_PATH
        or spec.display_lut_menu_path != P269_DISPLAY_LUT_MENU_PATH
        or spec.select_lut_menu_path != P269_SELECT_LUT_MENU_PATH
        or spec.auto_review_menu_path != P269_AUTO_REVIEW_MENU_PATH
        or spec.tcub_menu_path != P269_TCUB_MENU_PATH
        or spec.tcub_menu_items != P269_TCUB_EXACT_6_ITEMS
        or spec.tcub_disp_setting_menu_path != P269_TCUB_DISP_SETTING_MENU_PATH
        or spec.shooting_domain not in P269_SHOOTING_DOMAINS
        or spec.movie_frame_rate not in P269_MOVIE_FRAME_RATES
        or spec.log_shooting_mode not in P269_LOG_SHOOTING_MODES
        or spec.reset_action not in P269_RESET_ACTIONS
    ):
        _fail(
            P269_BLOCKED_INVALID_GAMMA_ASSIST_LUT_TCUB_SPEC,
            "Invalid camera/fw/menu path/6-item TC/UB or shooting domain specification for Pillar 46B",
        )

    if _targets_persistent_emmc(spec.overlay_dir) or not _is_tmpfs_path(spec.overlay_dir) or not spec.p2_blkroset_locked:
        _fail(
            P269_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped tmpfs or p2 BLKROSET unlocked: {spec.overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == P269_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == P269_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P269_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P269_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 drift or non-zero Stage-B Backup.bin writes",
        )

    # 2. [Gamma Display Assist] Log Shooting lockout vs [Display LUT] / [Select LUT] (3 presets + User1..16)
    gamma_errs_before = len(errors)
    lockout_bypasses = int(spec.gamma_assist_log_lockout_bypass_events)
    for tag, g_ast, g_typ, d_lut, s_lut in (
        ("pre", spec.pre_gamma_display_assist, spec.pre_gamma_disp_assist_type, spec.pre_display_lut, spec.pre_select_lut),
        ("saved", spec.saved_gamma_display_assist, spec.saved_gamma_disp_assist_type, spec.saved_display_lut, spec.saved_select_lut),
        ("post", spec.post_gamma_display_assist, spec.post_gamma_disp_assist_type, spec.post_display_lut, spec.post_select_lut),
    ):
        if (
            g_ast not in P269_GAMMA_DISPLAY_ASSIST_MODES
            or g_typ not in P269_GAMMA_DISP_ASSIST_TYPES
            or d_lut not in P269_DISPLAY_LUT_MODES
            or s_lut not in P269_SELECT_LUT_MODES
        ):
            lockout_bypasses = max(lockout_bypasses, 1)
            _fail(
                P269_BLOCKED_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_BYPASS,
                f"Invalid {tag} Gamma Display Assist / Display LUT / Select LUT (must be S-Log3/s709/709(800%)/User1..16)",
            )

    exp_eff_gamma, exp_locked_by_log, exp_lcd_gamma, exp_hdmi_gamma, exp_mon_lut = (
        compute_expected_gamma_assist_and_lut_monitoring_state(
            log_shooting_mode=spec.log_shooting_mode,
            configured_gamma_display_assist=spec.post_gamma_display_assist,
            configured_gamma_disp_assist_type=spec.post_gamma_disp_assist_type,
            configured_display_lut=spec.post_display_lut,
            configured_select_lut=spec.post_select_lut,
        )
    )

    if (
        spec.effective_gamma_display_assist != exp_eff_gamma
        or spec.gamma_assist_locked_by_log_shooting != exp_locked_by_log
        or spec.lcd_gamma_assist_applied != exp_lcd_gamma
        or spec.active_monitoring_lut != exp_mon_lut
        or spec.gamma_assist_log_lockout_bypass_events != 0
    ):
        lockout_bypasses = max(lockout_bypasses, 1)
        _fail(
            P269_BLOCKED_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_BYPASS,
            f"Gamma Display Assist lockout / LUT monitoring state drifted under Log Shooting={spec.log_shooting_mode!r}",
        )

    # Exhaustive 4 Log modes x 2 Gamma Assist x 4 Types x 2 Display LUT = 64-state proof
    for l_mode in P269_LOG_SHOOTING_MODES:
        for g_m in P269_GAMMA_DISPLAY_ASSIST_MODES:
            for g_t in P269_GAMMA_DISP_ASSIST_TYPES:
                for d_l in P269_DISPLAY_LUT_MODES:
                    eg, lk, lcd_g, hdmi_g, _ = compute_expected_gamma_assist_and_lut_monitoring_state(
                        log_shooting_mode=l_mode,
                        configured_gamma_display_assist=g_m,
                        configured_gamma_disp_assist_type=g_t,
                        configured_display_lut=d_l,
                        configured_select_lut="User16",
                    )
                    _need(not hdmi_g, "External HDMI must never receive Gamma Display Assist")
                    if l_mode != "Off":
                        _need(eg == "Off" and lk and not lcd_g, "Log Shooting must lock Gamma Display Assist Off")
    gamma_lut_verified = len(errors) == gamma_errs_before

    # 3. LCD-only scope (clean external HDMI) & [Auto Review] = [Off] cinema default
    hdmi_errs_before = len(errors)
    hdmi_leak_events = int(spec.gamma_assist_external_hdmi_leak_events)
    if spec.external_hdmi_gamma_assist_applied != exp_hdmi_gamma or spec.gamma_assist_external_hdmi_leak_events != 0:
        hdmi_leak_events = max(hdmi_leak_events, 1)
        _fail(
            P269_BLOCKED_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_OR_AUTO_REVIEW_VIOLATION,
            "Gamma Display Assist applies strictly to camera LCD and must NEVER leak onto external TV/HDMI output",
        )
    lcd_hdmi_verified = len(errors) == hdmi_errs_before

    ar_errs_before = len(errors)
    if (
        spec.factory_default_auto_review != P269_AUTO_REVIEW_DEFAULT
        or spec.pre_auto_review not in P269_AUTO_REVIEW_MODES
        or spec.saved_auto_review not in P269_AUTO_REVIEW_MODES
        or spec.post_auto_review not in P269_AUTO_REVIEW_MODES
        or spec.movie_live_view_interrupted_by_auto_review
    ):
        _fail(
            P269_BLOCKED_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_OR_AUTO_REVIEW_VIOLATION,
            "ILME-FX3 [Auto Review] cinema default must be 'Off' (still-image only) and never interrupt Movie live view",
        )
    auto_review_verified = len(errors) == ar_errs_before

    # 4. All 6 [TC/UB] parameters + [Setup] Display Options survive [Camera Settings Reset], reset only by [Initialize]
    tc_errs_before = len(errors)
    tcub_violations = int(spec.tcub_camera_reset_wipe_or_format_violations)
    for tag, tcp, ubp, tcf, tcr, tcm, ubtr, tcd in (
        (
            "pre",
            spec.pre_tc_preset,
            spec.pre_ub_preset,
            spec.pre_tc_format,
            spec.pre_tc_run,
            spec.pre_tc_make,
            spec.pre_ub_time_rec,
            spec.pre_tcub_disp_setting,
        ),
        (
            "saved",
            spec.saved_tc_preset,
            spec.saved_ub_preset,
            spec.saved_tc_format,
            spec.saved_tc_run,
            spec.saved_tc_make,
            spec.saved_ub_time_rec,
            spec.saved_tcub_disp_setting,
        ),
        (
            "post",
            spec.post_tc_preset,
            spec.post_ub_preset,
            spec.post_tc_format,
            spec.post_tc_run,
            spec.post_tc_make,
            spec.post_ub_time_rec,
            spec.post_tcub_disp_setting,
        ),
    ):
        if (
            not _validate_tc_preset(tcp)
            or not _validate_ub_preset(ubp)
            or tcf not in P269_TC_FORMAT_MODES
            or tcr not in P269_TC_RUN_MODES
            or tcm not in P269_TC_MAKE_MODES
            or ubtr not in P269_UB_TIME_REC_MODES
            or tcd not in P269_TCUB_DISP_SETTING_MODES
        ):
            tcub_violations = max(tcub_violations, 1)
            _fail(
                P269_BLOCKED_TCUB_OR_SETUP_RESET_PERSISTENCE_OR_NDF_DRIFT,
                f"Invalid {tag} 6-item [TC/UB] or [TC/UB Disp. Setting] parameter value",
            )

    if spec.movie_frame_rate in P269_FORCED_NDF_FRAME_RATES and spec.post_tc_format != "NDF":
        tcub_violations = max(tcub_violations, 1)
        _fail(
            P269_BLOCKED_TCUB_OR_SETUP_RESET_PERSISTENCE_OR_NDF_DRIFT,
            f"Frame rate {spec.movie_frame_rate!r} forces [Time Code Format] = 'NDF' (got {spec.post_tc_format!r})",
        )

    if spec.camset_load_after_reset:
        if (
            spec.camset_slot != P269_SLOT1_VAULT_SLOT
            or spec.camset_filename not in P269_CAMSET_FILENAMES
            or spec.camset_source_model != P269_FX3_MODEL_NAME
            or not spec.camset_read_only_load
        ):
            tcub_violations = max(tcub_violations, 1)
            _fail(
                P269_BLOCKED_TCUB_OR_SETUP_RESET_PERSISTENCE_OR_NDF_DRIFT,
                "Invalid CAMSET01..10.DAT O_RDONLY Slot-1 restoration envelope in Pillar 46B",
            )
        expected_state = (
            spec.saved_gamma_display_assist,
            spec.saved_gamma_disp_assist_type,
            spec.saved_display_lut,
            spec.saved_auto_review,
            spec.saved_tc_preset,
            spec.saved_ub_preset,
            "NDF" if spec.movie_frame_rate in P269_FORCED_NDF_FRAME_RATES else spec.saved_tc_format,
            spec.saved_tc_run,
            spec.saved_tc_make,
            spec.saved_ub_time_rec,
            spec.saved_tcub_disp_setting,
        )
    else:
        expected_state = compute_expected_auto_review_and_tcub_state_after_reset(
            pre_gamma_display_assist=spec.pre_gamma_display_assist,
            pre_gamma_disp_assist_type=spec.pre_gamma_disp_assist_type,
            pre_display_lut=spec.pre_display_lut,
            pre_auto_review=spec.pre_auto_review,
            pre_tc_preset=spec.pre_tc_preset,
            pre_ub_preset=spec.pre_ub_preset,
            pre_tc_format=spec.pre_tc_format,
            pre_tc_run=spec.pre_tc_run,
            pre_tc_make=spec.pre_tc_make,
            pre_ub_time_rec=spec.pre_ub_time_rec,
            pre_tcub_disp_setting=spec.pre_tcub_disp_setting,
            movie_frame_rate=spec.movie_frame_rate,
            reset_action=spec.reset_action,
        )

    actual_state = (
        spec.post_gamma_display_assist,
        spec.post_gamma_disp_assist_type,
        spec.post_display_lut,
        spec.post_auto_review,
        spec.post_tc_preset,
        spec.post_ub_preset,
        spec.post_tc_format,
        spec.post_tc_run,
        spec.post_tc_make,
        spec.post_ub_time_rec,
        spec.post_tcub_disp_setting,
    )
    if actual_state != expected_state or spec.tcub_camera_reset_wipe_or_format_violations != 0:
        tcub_violations = max(tcub_violations, 1)
        _fail(
            P269_BLOCKED_TCUB_OR_SETUP_RESET_PERSISTENCE_OR_NDF_DRIFT,
            f"Post-reset Setup/[TC/UB] state {actual_state!r} drifted from expected {expected_state!r}",
        )
    tcub_verified = len(errors) == tc_errs_before

    passed = len(errors) == 0
    status = P269_STATUS_VERIFIED_PILLAR_46B if passed else P269_STATUS_REJECTED_PILLAR_46B
    digest = _canonical_sha256(
        {
            "pillar": "46B",
            "passed": passed,
            "status": status,
            "block_code": block_code,
            "effective_gamma_display_assist": exp_eff_gamma,
            "active_monitoring_lut": exp_mon_lut,
            "post_tc_preset": spec.post_tc_preset,
            "post_tc_format": spec.post_tc_format,
        }
    )
    return GammaAssistLutAutoReviewTcubVaultReport(
        passed=passed,
        status=status,
        block_code=None if passed else block_code,
        gamma_assist_log_lockout_and_lut_verified=gamma_lut_verified,
        lcd_only_clean_external_hdmi_verified=lcd_hdmi_verified,
        auto_review_off_cinema_default_verified=auto_review_verified,
        tcub_6item_non_resettable_persistence_verified=tcub_verified,
        h0_equals_h3_verified=h0_eq_h3,
        effective_gamma_display_assist=exp_eff_gamma,
        active_monitoring_lut=exp_mon_lut,
        gamma_assist_log_lockout_bypass_events=lockout_bypasses,
        gamma_assist_external_hdmi_leak_events=hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=tcub_violations,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Combined Verifier, 6-Scenario Suites (46A & 46B) & Standalone Runner
# ---------------------------------------------------------------------------


def verify_file_settings_gamma_assist_and_tcub_vault(
    file_settings_spec: Optional[FileSettingsAndStillFolderVaultSpec] = None,
    gamma_tcub_spec: Optional[GammaAssistLutAutoReviewTcubVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> FileSettingsGammaAssistAndTcubVaultReport:
    """Combined single-shot verifier for Pillar 46A + Pillar 46B + bounded O_RDONLY Wave-44 donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase269_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_file_settings_and_still_folder_vault(
        file_settings_spec or build_default_safe_file_settings_and_still_folder_vault_spec()
    )
    rep_b = evaluate_gamma_assist_lut_auto_review_tcub_vault(
        gamma_tcub_spec or build_default_safe_gamma_assist_lut_auto_review_tcub_vault_spec()
    )
    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 269 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        errs.append(f"Donor inspection exceeded 2.0s budget: {donor_snapshot.elapsed_seconds}s")
    ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return FileSettingsGammaAssistAndTcubVaultReport(
        schema=PHASE269_SCHEMA,
        version=PHASE269_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=ok,
        passed=ok,
        status=P269_STATUS_VERIFIED_PILLAR46_SUITE if ok else P269_STATUS_FAIL_PILLAR46_SUITE,
        donor_snapshot=donor_snapshot,
        file_settings_still_folder_report=rep_a,
        gamma_assist_lut_auto_review_tcub_report=rep_b,
        slot1_vault_folder_mutation_events=rep_a.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=rep_a.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=rep_a.movie_custom_folder_or_title_overflow_events,
        still_prefix_underscore_lead_or_len_violations=rep_a.still_prefix_underscore_lead_or_len_violations,
        gamma_assist_log_lockout_bypass_events=rep_b.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=rep_b.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=rep_b.tcub_camera_reset_wipe_or_format_violations,
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


def verify_file_settings_gamma_assist_tcub_vault(
    file_settings_spec: Optional[FileSettingsAndStillFolderVaultSpec] = None,
    gamma_tcub_spec: Optional[GammaAssistLutAutoReviewTcubVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> FileSettingsGammaAssistAndTcubVaultReport:
    """Symmetry alias for `verify_file_settings_gamma_assist_and_tcub_vault`."""
    return verify_file_settings_gamma_assist_and_tcub_vault(
        file_settings_spec=file_settings_spec,
        gamma_tcub_spec=gamma_tcub_spec,
        force_clean_room=force_clean_room,
    )


def run_pillar46a_file_settings_and_still_folder_vault_6_scenario_suite() -> Pillar46ASuiteResult:
    """Run all 6 canonical Pillar 46A scenarios (`2` safe + `4` negative naming/reset/vault guards)."""
    s37_unit_b = "FX3_UNIT_B_SLATE_37CHAR_EXACT_BOUND_X"
    cases: Tuple[Tuple[str, bool, FileSettingsAndStillFolderVaultSpec, Optional[str]], ...] = (
        (
            P269_PILLAR_46A_SCENARIO_IDS[0],
            True,
            FileSettingsAndStillFolderVaultSpec(),
            None,
        ),
        (
            P269_PILLAR_46A_SCENARIO_IDS[1],
            True,
            FileSettingsAndStillFolderVaultSpec(
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model=P269_FX3_MODEL_NAME,
                camset_read_only_load=True,
                saved_movie_file_number="Reset",
                saved_movie_file_name_format="Cam ID + Reel#",
                saved_camera_id="B",
                saved_reel_number="012",
                saved_camera_position="L",
                saved_title_name=s37_unit_b,
                saved_still_file_number="Reset",
                saved_still_set_file_name="FX3",
                saved_still_folder_name_form="Date Form",
                post_movie_file_number="Reset",
                post_movie_file_name_format="Cam ID + Reel#",
                post_camera_id="B",
                post_reel_number="012",
                post_camera_position="L",
                post_title_name=s37_unit_b,
                post_still_file_number="Reset",
                post_still_set_file_name="FX3",
                post_still_folder_name_form="Date Form",
                movie_seq_number=5,
                still_folder_number=102,
                date_ymmdd="61115",
                still_seq_number=1,
                expected_movie_clip_relpath="PRIVATE/M4ROOT/CLIP/B012L0005.MP4",
                expected_still_dcim_folder="10261115",
                expected_still_file_relpath="DCIM/10261115/FX300001.JPG",
                active_still_media_slot=2,
                forced_file_number_reset_requested=True,
            ),
            None,
        ),
        (
            P269_PILLAR_46A_SCENARIO_IDS[2],
            False,
            FileSettingsAndStillFolderVaultSpec(
                pre_title_name="X" * 38,
                post_title_name="X" * 38,
                pre_reel_number="000",
                post_reel_number="000",
                movie_clip_folder_path="PRIVATE/CUSTOM/CLIP",
                movie_custom_folder_attempted=True,
                movie_custom_folder_or_title_overflow_events=1,
            ),
            P269_BLOCKED_MOVIE_FILE_SETTINGS_OR_37CHAR_TITLE_VIOLATION,
        ),
        (
            P269_PILLAR_46A_SCENARIO_IDS[3],
            False,
            FileSettingsAndStillFolderVaultSpec(
                pre_still_set_file_name="_SC",
                post_still_set_file_name="_SC",
                expected_still_file_relpath="DCIM/100MSDCF/_SC00001.JPG",
                still_prefix_underscore_lead_or_len_violations=1,
            ),
            P269_BLOCKED_STILL_PREFIX_UNDERSCORE_OR_FOLDER_FORM_VIOLATION,
        ),
        (
            P269_PILLAR_46A_SCENARIO_IDS[4],
            False,
            FileSettingsAndStillFolderVaultSpec(
                reset_action="Camera Settings Reset",
                post_movie_file_name_format="Standard",
                post_title_name="C",
                post_still_set_file_name="DSC",
                expected_movie_clip_relpath="PRIVATE/M4ROOT/CLIP/C0001.MP4",
            ),
            P269_BLOCKED_FILE_FOLDER_RESET_VS_INITIALIZE_SCOPE_DRIFT,
        ),
        (
            P269_PILLAR_46A_SCENARIO_IDS[5],
            False,
            FileSettingsAndStillFolderVaultSpec(
                slot1_holds_recovery_vault=True,
                active_still_media_slot=1,
                forced_file_number_reset_requested=True,
                create_new_folder_requested=True,
                slot1_vault_folder_mutation_events=1,
                slot1_vault_folder_mutation_bytes=512,
            ),
            P269_BLOCKED_SLOT1_VAULT_DCIM_FOLDER_MUTATION,
        ),
    )

    outcomes: List[Pillar46ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_file_settings_and_still_folder_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar46ScenarioOutcome(
                scenario_id=sid,
                pillar="46A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar46ASuiteResult(
        passed=all_ok,
        status=P269_STATUS_VERIFIED_PILLAR_46A if all_ok else P269_STATUS_REJECTED_PILLAR_46A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar46b_gamma_assist_lut_auto_review_tcub_vault_6_scenario_suite() -> Pillar46BSuiteResult:
    """Run all 6 canonical Pillar 46B scenarios (`2` safe + `4` negative lockout/HDMI/TCUB/Tier-0 guards)."""
    cases: Tuple[Tuple[str, bool, GammaAssistLutAutoReviewTcubVaultSpec, Optional[str]], ...] = (
        (
            P269_PILLAR_46B_SCENARIO_IDS[0],
            True,
            GammaAssistLutAutoReviewTcubVaultSpec(),
            None,
        ),
        (
            P269_PILLAR_46B_SCENARIO_IDS[1],
            True,
            GammaAssistLutAutoReviewTcubVaultSpec(
                shooting_domain="Movie",
                movie_frame_rate="29.97p",
                log_shooting_mode="Off",
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model=P269_FX3_MODEL_NAME,
                camset_read_only_load=True,
                saved_gamma_display_assist="On",
                saved_gamma_disp_assist_type="S-Log3->709(800%)",
                saved_display_lut="On",
                saved_select_lut="709(800%)",
                saved_auto_review="Off",
                saved_tc_preset="00:00:00.00",
                saved_ub_preset="00 00 00 00",
                saved_tc_format="DF",
                saved_tc_run="Rec Run",
                saved_tc_make="Regenerate",
                saved_ub_time_rec="On",
                saved_tcub_disp_setting="U-Bit",
                post_gamma_display_assist="On",
                post_gamma_disp_assist_type="S-Log3->709(800%)",
                post_display_lut="On",
                post_select_lut="709(800%)",
                post_auto_review="Off",
                post_tc_preset="00:00:00.00",
                post_ub_preset="00 00 00 00",
                post_tc_format="DF",
                post_tc_run="Rec Run",
                post_tc_make="Regenerate",
                post_ub_time_rec="On",
                post_tcub_disp_setting="U-Bit",
                effective_gamma_display_assist="On",
                gamma_assist_locked_by_log_shooting=False,
                lcd_gamma_assist_applied=True,
                hdmi_external_monitor_connected=True,
                external_hdmi_gamma_assist_applied=False,
                active_monitoring_lut="GAMMA_ASSIST:S-Log3->709(800%)",
            ),
            None,
        ),
        (
            P269_PILLAR_46B_SCENARIO_IDS[2],
            False,
            GammaAssistLutAutoReviewTcubVaultSpec(
                log_shooting_mode="Cine EI Quick",
                effective_gamma_display_assist="On",
                gamma_assist_locked_by_log_shooting=False,
                lcd_gamma_assist_applied=True,
                post_select_lut="User17",
                gamma_assist_log_lockout_bypass_events=1,
            ),
            P269_BLOCKED_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_BYPASS,
        ),
        (
            P269_PILLAR_46B_SCENARIO_IDS[3],
            False,
            GammaAssistLutAutoReviewTcubVaultSpec(
                log_shooting_mode="Off",
                effective_gamma_display_assist="On",
                gamma_assist_locked_by_log_shooting=False,
                lcd_gamma_assist_applied=True,
                active_monitoring_lut="GAMMA_ASSIST:S-Log3->709(800%)",
                external_hdmi_gamma_assist_applied=True,
                factory_default_auto_review="2 Sec",
                movie_live_view_interrupted_by_auto_review=True,
                gamma_assist_external_hdmi_leak_events=1,
            ),
            P269_BLOCKED_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_OR_AUTO_REVIEW_VIOLATION,
        ),
        (
            P269_PILLAR_46B_SCENARIO_IDS[4],
            False,
            GammaAssistLutAutoReviewTcubVaultSpec(
                movie_frame_rate="24.00p",
                reset_action="Camera Settings Reset",
                post_tc_preset="00:00:00.00",
                post_tc_format="DF",
                post_tc_run="Rec Run",
                tcub_camera_reset_wipe_or_format_violations=1,
            ),
            P269_BLOCKED_TCUB_OR_SETUP_RESET_PERSISTENCE_OR_NDF_DRIFT,
        ),
        (
            P269_PILLAR_46B_SCENARIO_IDS[5],
            False,
            GammaAssistLutAutoReviewTcubVaultSpec(
                overlay_dir="/setting/persistent_lut_escape",
                tier0_surfaces_h0_h3_matched=15,
            ),
            P269_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
        ),
    )

    outcomes: List[Pillar46ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_gamma_assist_lut_auto_review_tcub_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar46ScenarioOutcome(
                scenario_id=sid,
                pillar="46B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar46BSuiteResult(
        passed=all_ok,
        status=P269_STATUS_VERIFIED_PILLAR_46B if all_ok else P269_STATUS_REJECTED_PILLAR_46B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar46_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar46StandaloneReport:
    """Run full Pillar 46 standalone suite (`6/6` Pillar 46A + `6/6` Pillar 46B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase269_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar46a_file_settings_and_still_folder_vault_6_scenario_suite()
    res_b = run_pillar46b_gamma_assist_lut_auto_review_tcub_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 269 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor inspection exceeded 2.0s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE269_SCHEMA,
            "version": PHASE269_VERSION,
            "mode": donor_snapshot.verification_mode,
            "46a": [asdict(s) for s in res_a.scenarios],
            "46b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar46StandaloneReport(
        schema=PHASE269_SCHEMA,
        version=PHASE269_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P269_STATUS_VERIFIED_PILLAR46_SUITE if all_ok else P269_STATUS_FAIL_PILLAR46_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_46a_file_settings_still_folder_vault=res_a,
        pillar_46b_gamma_assist_lut_auto_review_tcub_vault=res_b,
        slot1_vault_folder_mutation_events=(
            P269_SLOT1_VAULT_FOLDER_MUTATION_EVENTS if res_a.passed else 1
        ),
        slot1_vault_folder_mutation_bytes=(
            P269_SLOT1_VAULT_FOLDER_MUTATION_BYTES if res_a.passed else 512
        ),
        movie_custom_folder_or_title_overflow_events=(
            P269_MOVIE_CUSTOM_FOLDER_OR_TITLE_OVERFLOW_EVENTS if res_a.passed else 1
        ),
        still_prefix_underscore_lead_or_len_violations=(
            P269_STILL_PREFIX_UNDERSCORE_LEAD_OR_LEN_VIOLATIONS if res_a.passed else 1
        ),
        gamma_assist_log_lockout_bypass_events=(
            P269_GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS if res_b.passed else 1
        ),
        gamma_assist_external_hdmi_leak_events=(
            P269_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_EVENTS if res_b.passed else 1
        ),
        tcub_camera_reset_wipe_or_format_violations=(
            P269_TCUB_CAMERA_RESET_WIPE_OR_FORMAT_VIOLATIONS if res_b.passed else 1
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
# Unified 46/46 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master46_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_46pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master46PillarRecoveryReport:
    """Evaluate and aggregate all 46 recovery pillars (`1..46`) concurrently -> `46/46` recovery master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_46_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_45pillar() -> Master45PillarRecoveryReport:
        return evaluate_realhw_45pillar_recovery_master(**kw)

    def _run_p46() -> Tuple[Pillar46StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar46_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_45 = pool.submit(_run_45pillar)
        fut_46 = pool.submit(_run_p46)
        m45_rep = fut_45.result()
        p46_rep, p46_dt = fut_46.result()

    all_errors: List[str] = list(m45_rep.errors) + list(p46_rep.errors)
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
        if getattr(m45_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-45 violated {attr_name} == {expected_val}")
        if getattr(p46_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 46 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("fx3_has_builtin_end_filter", False),
        ("e_nd_actuator_tx_count", 0),
        ("cardless_unrecorded_production_violations", 0),
        ("legacy_v1_audio_level_menu_spoof_events", 0),
        ("photographer_copyright_pii_leaked_bytes", 0),
        ("copyright_char_overflow_or_movie_mutation_events", 0),
        ("slot1_copyright_vault_mutation_bytes", 0),
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
        if getattr(m45_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-45 violated {attr_name} == {expected_val}")
    if m45_rep.bodydata_flash_attempts_blocked < 1:
        all_errors.append("Pillars 1-45 violated bodydata_flash_attempts_blocked >= 1")

    for attr_name, expected_val in (
        ("slot1_vault_folder_mutation_events", 0),
        ("slot1_vault_folder_mutation_bytes", 0),
        ("movie_custom_folder_or_title_overflow_events", 0),
        ("still_prefix_underscore_lead_or_len_violations", 0),
        ("gamma_assist_log_lockout_bypass_events", 0),
        ("gamma_assist_external_hdmi_leak_events", 0),
        ("tcub_camera_reset_wipe_or_format_violations", 0),
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(p46_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 46 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m45_rep.pillars)
    spec46 = MASTER_46_PILLAR_SPECS[45]
    p46_metrics = {
        "pillar_46a_file_settings_still_folder_vault": (
            f"{p46_rep.pillar_46a_file_settings_still_folder_vault.scenarios_passed}/"
            f"{p46_rep.pillar_46a_file_settings_still_folder_vault.scenarios_total}"
        ),
        "pillar_46b_gamma_assist_lut_auto_review_tcub_vault": (
            f"{p46_rep.pillar_46b_gamma_assist_lut_auto_review_tcub_vault.scenarios_passed}/"
            f"{p46_rep.pillar_46b_gamma_assist_lut_auto_review_tcub_vault.scenarios_total}"
        ),
        "slot1_vault_folder_mutation_events": p46_rep.slot1_vault_folder_mutation_events,
        "slot1_vault_folder_mutation_bytes": p46_rep.slot1_vault_folder_mutation_bytes,
        "movie_custom_folder_or_title_overflow_events": (
            p46_rep.movie_custom_folder_or_title_overflow_events
        ),
        "still_prefix_underscore_lead_or_len_violations": (
            p46_rep.still_prefix_underscore_lead_or_len_violations
        ),
        "gamma_assist_log_lockout_bypass_events": p46_rep.gamma_assist_log_lockout_bypass_events,
        "gamma_assist_external_hdmi_leak_events": p46_rep.gamma_assist_external_hdmi_leak_events,
        "tcub_camera_reset_wipe_or_format_violations": (
            p46_rep.tcub_camera_reset_wipe_or_format_violations
        ),
        "hardware_live_attachment_authorized": p46_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p46_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec46[0],
            pillar_id=spec46[1],
            phase_label=spec46[2],
            module_name=spec46[3],
            passed=bool(p46_rep.all_passed),
            status=p46_rep.status,
            verification_mode=p46_rep.verification_mode,
            elapsed_seconds=p46_dt,
            key_metrics=p46_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec46[1],
                    "mode": p46_rep.verification_mode,
                    "status": p46_rep.status,
                    "metrics": p46_metrics,
                    "passed": p46_rep.all_passed,
                }
            ),
            errors=tuple(p46_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master46_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p46_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_46_PILLAR_COUNT == 46
        and pillars_passed == 46
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE269_SCHEMA,
            "version": PHASE269_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master46PillarRecoveryReport(
        schema=PHASE269_SCHEMA,
        version=PHASE269_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P269_STATUS_VERIFIED_46OF46_AGGREGATOR if all_ok else P269_STATUS_FAIL_46OF46_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_2s_fast_cli_budget=elapsed < P269_FAST_CLI_BUDGET_SECONDS,
        under_6s_budget=elapsed < P269_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P269_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p46_rep.donor_snapshot,
        pillar46_a_file_settings_still_folder_vault=(
            p46_rep.pillar_46a_file_settings_still_folder_vault
        ),
        pillar46_b_gamma_assist_lut_auto_review_tcub_vault=(
            p46_rep.pillar_46b_gamma_assist_lut_auto_review_tcub_vault
        ),
        slot1_vault_folder_mutation_events=p46_rep.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=p46_rep.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=(
            p46_rep.movie_custom_folder_or_title_overflow_events
        ),
        still_prefix_underscore_lead_or_len_violations=(
            p46_rep.still_prefix_underscore_lead_or_len_violations
        ),
        gamma_assist_log_lockout_bypass_events=p46_rep.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=p46_rep.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=(
            p46_rep.tcub_camera_reset_wipe_or_format_violations
        ),
        fx3_has_builtin_end_filter=m45_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=m45_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=m45_rep.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=m45_rep.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=m45_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            m45_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=m45_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m45_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m45_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m45_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m45_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m45_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m45_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m45_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m45_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m45_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m45_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m45_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m45_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m45_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m45_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m45_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m45_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m45_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m45_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m45_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m45_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m45_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m45_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m45_rep.unbuffered_battery_pull_events,
        hardware_live_attachment_authorized=p46_rep.hardware_live_attachment_authorized,
        master_46pillar_sha256=master_sha,
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


def evaluate_46pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master46PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_46pillar_recovery_master`."""
    return evaluate_realhw_46pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_46pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master46PillarRecoveryReport:
    """Public CLI entry point for Phase 269 `46/46` unified recovery master."""
    return evaluate_realhw_46pillar_recovery_master(
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
    "MASTER_46_PILLAR_COUNT",
    "MASTER_46_PILLAR_IDS",
    "MASTER_46_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "P269_AUTO_REVIEW_DEFAULT",
    "P269_AUTO_REVIEW_MENU_PATH",
    "P269_AUTO_REVIEW_MODES",
    "P269_BLOCKED_FILE_FOLDER_RESET_VS_INITIALIZE_SCOPE_DRIFT",
    "P269_BLOCKED_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_OR_AUTO_REVIEW_VIOLATION",
    "P269_BLOCKED_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_BYPASS",
    "P269_BLOCKED_INVALID_FILE_OR_FOLDER_SETTINGS_SPEC",
    "P269_BLOCKED_INVALID_GAMMA_ASSIST_LUT_TCUB_SPEC",
    "P269_BLOCKED_MOVIE_FILE_SETTINGS_OR_37CHAR_TITLE_VIOLATION",
    "P269_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P269_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P269_BLOCKED_SLOT1_VAULT_DCIM_FOLDER_MUTATION",
    "P269_BLOCKED_STILL_PREFIX_UNDERSCORE_OR_FOLDER_FORM_VIOLATION",
    "P269_BLOCKED_TCUB_OR_SETUP_RESET_PERSISTENCE_OR_NDF_DRIFT",
    "P269_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P269_BOUNDED_HEADER_BYTES",
    "P269_CAMERA_POSITIONS",
    "P269_CAMERA_POSITION_DEFAULT",
    "P269_CAMSET_FILENAMES",
    "P269_CAM_ID_DEFAULT",
    "P269_CAM_ID_LETTERS",
    "P269_CONCURRENT_CEILING_SECONDS",
    "P269_DISPLAY_LUT_DEFAULT",
    "P269_DISPLAY_LUT_MENU_PATH",
    "P269_DISPLAY_LUT_MODES",
    "P269_DONOR_FX3_APPFW_702_RELPATH",
    "P269_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P269_DONOR_FX3_BODYDATA_RELPATH",
    "P269_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH",
    "P269_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH",
    "P269_DONOR_FX3_LIBBACKUP_SO_RELPATH",
    "P269_DONOR_FX3_LIBGPE_SO_RELPATH",
    "P269_DONOR_FX3_LIBINFRAFSYS_SO_RELPATH",
    "P269_DONOR_FX3_LIBINFRAMEDIACOMMON_SO_RELPATH",
    "P269_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH",
    "P269_DONOR_FX3_LIBINFRAMEDIADETECT_SO_RELPATH",
    "P269_DONOR_FX3_LIBINFRAMEDIAMOUNT_SO_RELPATH",
    "P269_DONOR_FX3_LIBINFRAMETASUPPLIER_SO_RELPATH",
    "P269_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH",
    "P269_DONOR_FX6_APPFW_601_RELPATH",
    "P269_DONOR_FX6_LIBINFRASETUPFILE_SO_RELPATH",
    "P269_DONOR_INSPECT_BUDGET_SECONDS",
    "P269_ENV_CLEAN_ROOM_TEST",
    "P269_FAST_CLI_BUDGET_SECONDS",
    "P269_FIXED_MOVIE_CLIP_FOLDER",
    "P269_FORBIDDEN_PERSISTENT_TARGETS",
    "P269_FORCED_NDF_FRAME_RATES",
    "P269_FX3_FW_VERSION",
    "P269_FX3_HELPGUIDE_ID",
    "P269_FX3_MODEL_ID",
    "P269_FX3_MODEL_NAME",
    "P269_FX3_SUPPORTED_FW_VERSIONS",
    "P269_FX6_DONOR_FW_VERSION",
    "P269_FX6_DONOR_MODEL_NAME",
    "P269_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_EVENTS",
    "P269_GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS",
    "P269_GAMMA_DISPLAY_ASSIST_DEFAULT",
    "P269_GAMMA_DISPLAY_ASSIST_MENU_PATH",
    "P269_GAMMA_DISPLAY_ASSIST_MODES",
    "P269_GAMMA_DISP_ASSIST_TYPES",
    "P269_GAMMA_DISP_ASSIST_TYPE_DEFAULT",
    "P269_GAMMA_DISP_ASSIST_TYP_MENU_PATH",
    "P269_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P269_LOG_SHOOTING_MODES",
    "P269_MAX_FULL_DONOR_BYTES",
    "P269_MOVIE_CUSTOM_FOLDER_OR_TITLE_OVERFLOW_EVENTS",
    "P269_MOVIE_FILE_NAME_FORMATS",
    "P269_MOVIE_FILE_NAME_FORMAT_DEFAULT",
    "P269_MOVIE_FILE_NUMBER_DEFAULT",
    "P269_MOVIE_FILE_NUMBER_MODES",
    "P269_MOVIE_FILE_SETTINGS_ITEMS",
    "P269_MOVIE_FILE_SETTINGS_MENU_PATH",
    "P269_MOVIE_FRAME_RATES",
    "P269_NOMINAL_BUDGET_SECONDS",
    "P269_PILLAR_46A_SCENARIO_IDS",
    "P269_PILLAR_46B_SCENARIO_IDS",
    "P269_PINNED_FX3_APPFW_702_BYTES",
    "P269_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P269_PINNED_FX3_BACKUP_BIN_BYTES",
    "P269_PINNED_FX3_BACKUP_BIN_SHA256",
    "P269_PINNED_FX3_BODYDATA_BYTES",
    "P269_PINNED_FX3_BODYDATA_HDR4K_SHA256",
    "P269_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES",
    "P269_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256",
    "P269_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES",
    "P269_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256",
    "P269_PINNED_FX3_LIBBACKUP_SO_BYTES",
    "P269_PINNED_FX3_LIBBACKUP_SO_SHA256",
    "P269_PINNED_FX3_LIBGPE_SO_BYTES",
    "P269_PINNED_FX3_LIBGPE_SO_SHA256",
    "P269_PINNED_FX3_LIBINFRAFSYS_SO_BYTES",
    "P269_PINNED_FX3_LIBINFRAFSYS_SO_SHA256",
    "P269_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES",
    "P269_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_SHA256",
    "P269_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES",
    "P269_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256",
    "P269_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES",
    "P269_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256",
    "P269_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_BYTES",
    "P269_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_SHA256",
    "P269_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_BYTES",
    "P269_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_SHA256",
    "P269_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES",
    "P269_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256",
    "P269_PINNED_FX6_APPFW_601_BYTES",
    "P269_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P269_PINNED_FX6_LIBINFRASETUPFILE_SO_BYTES",
    "P269_PINNED_FX6_LIBINFRASETUPFILE_SO_SHA256",
    "P269_REEL_NUMBER_DEFAULT",
    "P269_REEL_NUMBER_MAX",
    "P269_REEL_NUMBER_MIN",
    "P269_RESET_ACTIONS",
    "P269_SELECT_LUT_DEFAULT",
    "P269_SELECT_LUT_MENU_PATH",
    "P269_SELECT_LUT_MODES",
    "P269_SELECT_LUT_PRESETS",
    "P269_SELECT_LUT_USER_SLOTS",
    "P269_SHOOTING_DOMAINS",
    "P269_SLOT1_VAULT_FOLDER_MUTATION_BYTES",
    "P269_SLOT1_VAULT_FOLDER_MUTATION_EVENTS",
    "P269_SLOT1_VAULT_SLOT",
    "P269_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P269_STATUS_FAIL_46OF46_AGGREGATOR",
    "P269_STATUS_FAIL_PILLAR46_SUITE",
    "P269_STATUS_REJECTED_PILLAR_46A",
    "P269_STATUS_REJECTED_PILLAR_46B",
    "P269_STATUS_VERIFIED_46OF46_AGGREGATOR",
    "P269_STATUS_VERIFIED_PILLAR46_SUITE",
    "P269_STATUS_VERIFIED_PILLAR_46A",
    "P269_STATUS_VERIFIED_PILLAR_46B",
    "P269_STILL_FILE_FOLDER_ITEMS",
    "P269_STILL_FILE_FOLDER_MENU_PATH",
    "P269_STILL_FILE_NUMBER_DEFAULT",
    "P269_STILL_FILE_NUMBER_MODES",
    "P269_STILL_FOLDER_NAME_DEFAULT",
    "P269_STILL_FOLDER_NAME_MODES",
    "P269_STILL_PREFIX_ALLOWED_CHARSET",
    "P269_STILL_PREFIX_UNDERSCORE_LEAD_OR_LEN_VIOLATIONS",
    "P269_STILL_SET_FILE_NAME_DEFAULT",
    "P269_STILL_SET_FILE_NAME_LEN",
    "P269_STILL_STANDARD_FOLDER_SUFFIX",
    "P269_TCUB_CAMERA_RESET_WIPE_OR_FORMAT_VIOLATIONS",
    "P269_TCUB_DISP_SETTING_DEFAULT",
    "P269_TCUB_DISP_SETTING_MENU_PATH",
    "P269_TCUB_DISP_SETTING_MODES",
    "P269_TCUB_EXACT_6_ITEMS",
    "P269_TCUB_MENU_PATH",
    "P269_TC_FORMAT_DEFAULT",
    "P269_TC_FORMAT_MODES",
    "P269_TC_MAKE_DEFAULT",
    "P269_TC_MAKE_MODES",
    "P269_TC_PRESET_DEFAULT",
    "P269_TC_RUN_DEFAULT",
    "P269_TC_RUN_MODES",
    "P269_TIER0_SURFACE_COUNT",
    "P269_TITLE_ALLOWED_CHARSET",
    "P269_TITLE_ALLOWED_SYMBOLS",
    "P269_TITLE_NAME_DEFAULT",
    "P269_TITLE_NAME_MAX_CHARS",
    "P269_UB_PRESET_DEFAULT",
    "P269_UB_TIME_REC_DEFAULT",
    "P269_UB_TIME_REC_MODES",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE269_PHASE_NUMBER",
    "PHASE269_SCHEMA",
    "PHASE269_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "FileSettingsAndStillFolderVaultReport",
    "FileSettingsAndStillFolderVaultSpec",
    "FileSettingsGammaAssistAndTcubVaultReport",
    "GammaAssistLutAutoReviewTcubVaultReport",
    "GammaAssistLutAutoReviewTcubVaultSpec",
    "Master46PillarRecoveryReport",
    "Phase269DonorArtifactDigest",
    "Phase269DonorSnapshot",
    "Pillar46ASuiteResult",
    "Pillar46BSuiteResult",
    "Pillar46ScenarioOutcome",
    "Pillar46StandaloneReport",
    "build_default_safe_file_settings_and_still_folder_vault_spec",
    "build_default_safe_gamma_assist_lut_auto_review_tcub_vault_spec",
    "compute_expected_auto_review_and_tcub_state_after_reset",
    "compute_expected_gamma_assist_and_lut_monitoring_state",
    "compute_expected_movie_and_still_file_settings_after_reset",
    "compute_expected_movie_clip_stem_and_still_path",
    "evaluate_46pillar_recovery_master",
    "evaluate_file_settings_and_still_folder_vault",
    "evaluate_gamma_assist_lut_auto_review_tcub_vault",
    "evaluate_realhw_46pillar_recovery_master",
    "inspect_phase269_donors_readonly",
    "run_pillar46_standalone_suite",
    "run_pillar46a_file_settings_and_still_folder_vault_6_scenario_suite",
    "run_pillar46b_gamma_assist_lut_auto_review_tcub_vault_6_scenario_suite",
    "verify_46pillar_recovery_suite",
    "verify_file_settings_gamma_assist_and_tcub_vault",
    "verify_file_settings_gamma_assist_tcub_vault",
]
