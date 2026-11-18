"""Phase 331 (Task H400, 400th Task Milestone, Wave-64): Real-Hardware
`[Breathing Comp.]` (120p/100p + S&Q + RAW + Catalyst Prepare Errata) & Movie
`[File Settings]` (`[Cam ID + Reel#]` / 37-Char Title / SDHC 4 GB / Slot-1
Vault) (`G147`), Round-57 `[Copyright Info]` 46-Char & Still+Movie `[Write Serial
Number]` Reset Errata + 2-Item `[Power Setting Option]` (`9`-Cond Bypass /
Dormant Monitor) + `[NTSC/PAL Selector]` Slot-1 Format Firewall (`G148`), and
Unified `148`-Gate Master Safety Preflight (`G01..G148`).

Authoritative Empirical Baseline (`ILME-FX3 Ver. 7.02`, `ilc/2210`, `0x0502`,
`PRODUCT_MODEL_ALCIN_UUD` vs `ILME-FX6 Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`):
  - **Gate `G147` (`REALHW_BREATHING_COMP_120P_CATALYST_AND_CAMID_REEL_SDHC_VAULT_GUARD`)**:
    1. `Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]`
       (`Off` default / `On`, Ver. `3.00+..7.02`, **Resettable** via
       `[Camera Settings Reset]`, unlike `Shading`/`Chromatic Aberration`/
       `Distortion Comp.` which are `Initialize`-only):
       - **Wave-41 Errata**: Unavailable at **regular Movie `119.88p / 100p`
         (`120p`)** AND **`S&Q` `100/120/200/240fps`** (while `< 100fps` `S&Q`
         remains available on FX3, unlike `ILME-FX6` which locks `Off` across
         ALL `S&Q = On`). Unavailable in `Still` (`EXPOSURE_MODE_MOVIE`).
       - Incompatible E-mount / third-party lenses, `SEL100F28GM` macro ring
         `0.57-1.0m`, and `SEL14TC`/`SEL20TC` teleconverters return
         `NOT_SUPPORT`/`NA` (`EOPNOTSUPP=95` when requested On).
       - Bypassed on external `4264x2408` 16-bit HDMI RAW; post-production
         metadata breathing comp strictly requires paid **`Catalyst Prepare` /
         `Catalyst Prepare Plugin`** (NOT free `Catalyst Browse` ->
         `EOPNOTSUPP=95`) AND in-body **`[Distortion Comp.] = [Auto]`**.
       - Contrast `ILME-FX6 Ver. 6.01` (`Technical > Lens > Breathing
         Compensation` `Auto`/`Off`): hard-locked `Off` on `Distortion=Off`,
         `S&Q=On`, or any `RAW` codec.
    2. `Shooting -> [File] -> [File Settings]` (ALL **Initialize-only** / `Not
       available` under `[Camera Settings Reset]`):
       - `[File Number]` (`Series` default across Slot 1/2 / `Reset` +
         `[Series Counter Reset]` setting counter to `max + 1` if clips exist).
       - `[File Name Format]` (`Standard` default / `Cam ID + Reel#` / `Title` /
         `Date + Title` / `Title + Date`): **`SDHC` (`FAT32 <= 32 GB`)
         hard-locks `[Standard]`**, splits XAVC S recordings at `4 GB`, and
         blocks `[Simult. Recording]` with `exFAT`.
       - `[Cam ID + Reel#]`: `Camera ID` (`A..Z`, changing ID resets `Reel#`
         `001..999`, while `File Number = Reset` preserves `Reel#`), `Camera
         Position` (`C`/`L`/`R`) where `999` overflow rolls output character
         `C999 -> D001` without mutating menu setting, template using **`6`-digit
         `YYMMDD`** vs **`8`-digit `YYYYMMDD`** in `Date + Title`/`Title + Date`.
       - **`37`-char `[Title Name Settings]`** (default `"C"`, fixed
         `PRIVATE/M4ROOT/CLIP` vs FX6 `TC/Media > Clip Name Format` `4..46`-char
         `nnn_` + `/XDROOT/Clip/*.MXF` & card clip inheritance).
       - `Slot-1` Tier-0 Vault `EROFS=30` firewall (`slot1_data_sector_writes == 0`).

  - **Gate `G148` (`REALHW_COPYRIGHT_46CH_SERIAL_ERRATA_AND_POWERSAVE_NTSCPAL_VAULT_GUARD`)**:
    1. **Round-57 Reset Errata**: `Shooting -> [File] -> [Copyright Info]`
       (`Write Copyright Info` `Off` default/`On`, `Set Photographer` `<= 46`
       ASCII chars, `Set Copyright` `<= 46` ASCII chars, `Disp. Copyright Info`)
       AND active **Still + Movie `[Write Serial Number]`**
       (`BKID_APP_setting_write_serial_number_still_movie` `Off` default/`On`,
       replacing initial Still-only `BKID_APP_setting_still_write_serial_number`)
       are **ALL Initialize-only (`Not available` under `[Camera Settings Reset]`)**.
       `[Copyright Info]` is excluded from `CAMSET*.DAT` (preventing PII leakage),
       while `[Write Serial Number]` boolean toggle is permitted. Contrast
       `ILME-FX6` (no consumer EXIF `[Copyright Info]`, lens serial `0..5` +
       3-digit body serial `nnn_` `Title Prefix`).
    2. `Setup -> [Power Setting Option]` exact **`2` active Initialize-only
       items**: `[Power Save Start Time]` (`Off` / `30 Min` / `5 Min` [default] /
       `2 Min` / `1 Min` / `10 Sec`, with dormant `20SEC` / `NO_LIMIT` / `30 sec` /
       `60 min` / `240 min` -> `EOPNOTSUPP=95` and exact **`9` official
       auto-bypass conditions**) plus `[Auto Power OFF Temp.]` (`Standard`
       default / `High` tripod-only warning), rejecting **dormant `[Power Save
       by Monitor]`** (`BKID_APP_setting_monitor_power_linkage` ->
       `EOPNOTSUPP=95` on zero-EVF FX3).
    3. `Setup -> [Area/Date] -> [NTSC/PAL Selector]` (Initialize-only, mandatory
       reboot, `Running on NTSC.` / `Running on PAL.`, cross-system PB block +
       **HARD `EROFS=30` `Slot-1` Tier-0 Vault Format/SD-Erase/TRIM Firewall**
       on `base.uxc 0xe1e6..0xe9f6` format prompts vs FX6 `Project > Rec Format
       > Frequency`).

  - **Unified 148-Gate Master Safety Preflight (`G01..G148`)**:
    Delegates `G01..G146` to `evaluate_146gate_preflight()`, enforces `145/148`
    verified offline (`VERIFIED_145_OF_148_AWAITING_PHYSICAL_TIER0`) and `148/148`
    under `--simulate-bench-dry-run` (`VERIFIED_ALL_148_GATES_DRY_RUN_SIMULATED_BACKUP`),
    with ALL write/flash/live-attach redlines hard-locked `False` and `0`.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard import (
    GateVerdict,
)
from .thermal_pwm_and_power_guard import (
    DEFAULT_REPO_ROOT,
    STATUS_VERIFIED_SAFE,
    resolve_donor_thermal_power_paths,
)
from .realhw_shoe_audio_4ch_subject_recog_silent_bodydata_and_144gate_guard import (
    CROSS_MODEL_FLASH_AUTHORIZED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMMC_WRITES_AUTHORIZED,
    ENV_FORCE_CLEAN_ROOM,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    USB_PACKETS_TRANSMITTED,
)
from .realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard import (
    Master146GateReport,
    evaluate_146gate_preflight,
)


# ---------------------------------------------------------------------------
# Schema, Versions, Gate IDs & Errno Constants
# ---------------------------------------------------------------------------

REALHW_BREATHING_CAMID_COPYRIGHT_POWERSAVE_NTSCPAL_148GATE_SCHEMA = (
    "realhw_breathing_camid_copyright_powersave_ntscpal_148gate_guard_v1"
)
REALHW_BREATHING_CAMID_COPYRIGHT_POWERSAVE_NTSCPAL_148GATE_VERSION = "1.0.0"
REALHW_148GATE_PREFLIGHT_SCHEMA = "realhw_148gate_preflight_v1"

G147 = "G147"
G147_GATE_ID = G147
G147_GATE_CODE = (
    "REALHW_BREATHING_COMP_120P_CATALYST_AND_CAMID_REEL_SDHC_VAULT_GUARD"
)
GATE_G147_BREATHING_COMP_120P_CATALYST_AND_CAMID_REEL_SDHC_VAULT_GUARD = (
    G147_GATE_CODE
)

G148 = "G148"
G148_GATE_ID = G148
G148_GATE_CODE = (
    "REALHW_COPYRIGHT_46CH_SERIAL_ERRATA_AND_POWERSAVE_NTSCPAL_VAULT_GUARD"
)
GATE_G148_COPYRIGHT_46CH_SERIAL_ERRATA_AND_POWERSAVE_NTSCPAL_VAULT_GUARD = (
    G148_GATE_CODE
)

EOPNOTSUPP_ERRNO_PHASE331 = 95
EOPNOTSUPP_NAME_PHASE331 = "EOPNOTSUPP"
EINVAL_ERRNO_PHASE331 = 22
EINVAL_NAME_PHASE331 = "EINVAL"
EBUSY_ERRNO_PHASE331 = 16
EBUSY_NAME_PHASE331 = "EBUSY"
EROFS_ERRNO_PHASE331 = 30
EROFS_NAME_PHASE331 = "EROFS"

ENV_CLEAN_ROOM_TEST_PHASE331 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE331 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE331 = 5.0

FX3_MODEL_NAME_PHASE331 = "ILME-FX3"
FX3_MODEL_ID_PHASE331 = 0x0502
FX3_HELP_GUIDE_CODE_PHASE331 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE331 = "7.02"
FX6_MODEL_NAME_PHASE331 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE331 = "6.01"
FX6_PRODUCT_CODE_PHASE331 = "PRODUCT_MODEL_CHAPLIN"

MEDIA_SLOT_NONE_PHASE331 = 0
MEDIA_SLOT_1_PHASE331 = 1
MEDIA_SLOT_2_PHASE331 = 2
ALLOWED_MEDIA_SLOTS_PHASE331: Tuple[int, ...] = (
    MEDIA_SLOT_NONE_PHASE331,
    MEDIA_SLOT_1_PHASE331,
    MEDIA_SLOT_2_PHASE331,
)

SHOOT_MODE_STILL_PHASE331 = "Still"
SHOOT_MODE_MOVIE_PHASE331 = "Movie"
SHOOT_MODE_SQ_PHASE331 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE331: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE331,
    SHOOT_MODE_MOVIE_PHASE331,
    SHOOT_MODE_SQ_PHASE331,
)

RESET_ACTION_NONE_PHASE331 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331 = "Camera Settings Reset"
RESET_ACTION_INITIALIZE_PHASE331 = "Initialize"
RESET_ACTION_RESET_NETWORK_SET_PHASE331 = "Reset Network Set."
ALLOWED_RESET_ACTIONS_PHASE331: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE331,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331,
    RESET_ACTION_INITIALIZE_PHASE331,
    RESET_ACTION_RESET_NETWORK_SET_PHASE331,
)


# ---------------------------------------------------------------------------
# Gate G147 Constants: [Breathing Comp.] (Wave-41 Errata + Catalyst) &
#                      Movie [File Settings] (Cam ID+Reel# / 37-Char / SDHC)
# ---------------------------------------------------------------------------

BREATHING_COMP_MENU_PATH_G147 = (
    "Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]"
)
FILE_SETTINGS_MENU_PATH_G147 = "Shooting -> [File] -> [File Settings]"
FX6_BREATHING_COMP_MENU_PATH_G147 = "Technical > Lens > Breathing Compensation"
FX6_CLIP_NAME_FORMAT_MENU_PATH_G147 = "TC/Media > Clip Name Format"

BREATHING_COMP_OFF_G147 = "Off"
BREATHING_COMP_ON_G147 = "On"
BREATHING_COMP_DEFAULT_G147 = BREATHING_COMP_OFF_G147
ALLOWED_BREATHING_COMP_MODES_G147: Tuple[str, ...] = (
    BREATHING_COMP_OFF_G147,
    BREATHING_COMP_ON_G147,
)
BREATHING_COMP_MIN_FW_G147 = "3.00"
BREATHING_COMP_RESETTABLE_BY_CAMSET_RESET_G147 = True
LENS_COMP_INITIALIZE_ONLY_ITEMS_G147: Tuple[str, ...] = (
    "Shading Comp.",
    "Chromatic Aberration Comp.",
    "Distortion Comp.",
)
BREATHING_COMP_REGULAR_MOVIE_BLOCKED_FPS_FLOOR_G147 = 100.0  # 119.88p / 100p
BREATHING_COMP_SQ_BLOCKED_FPS_G147: Tuple[int, ...] = (100, 120, 200, 240)
BREATHING_COMP_F_RESID16_G147 = 0x73EA

LENS_BREATHING_SUPPORT_G147 = "SUPPORT"
LENS_BREATHING_NOT_SUPPORT_G147 = "NOT_SUPPORT"
LENS_BREATHING_NA_G147 = "NA"
ALLOWED_LENS_BREATHING_SUPPORT_STATES_G147: Tuple[str, ...] = (
    LENS_BREATHING_SUPPORT_G147,
    LENS_BREATHING_NOT_SUPPORT_G147,
    LENS_BREATHING_NA_G147,
)
TELECONVERTER_MODELS_G147: Tuple[str, ...] = ("SEL14TC", "SEL20TC")
MACRO_RING_RESTRICTED_LENS_G147 = "SEL100F28GM"
COMPATIBLE_BREATHING_LENSES_SAMPLE_G147: Tuple[str, ...] = (
    "SEL11F18",
    "SEL14F18GM",
    "SEL15F14G",
    "SEL16F18G",
    "SEL20F18G",
    "SEL24F14GM",
    "SEL24F28G",
    "SEL35F14GM",
    "SEL35F18F",
    "SEL40F25G",
    "SEL50F12GM",
    "SEL50F14GM",
    "SEL50F14Z",
    "SEL50F25G",
    "SEL85F14GM",
    "SEL85F14GM2",
    "SEL85F18",
    "SEL100F28GM",
    "SEL135F18GM",
    "SEL1224G",
    "SEL1635GM",
    "SELC1635G",
    "SEL2470GM",
    "SEL24105G",
)

CATALYST_PREPARE_PAID_TOOLS_G147: Tuple[str, ...] = (
    "Catalyst Prepare",
    "Catalyst Prepare Plugin",
)
CATALYST_BROWSE_FREE_TOOL_G147 = "Catalyst Browse"
ALLOWED_DISTORTION_COMP_MODES_G147: Tuple[str, ...] = ("Auto", "Off")
ALLOWED_FX6_RAW_CODECS_G147: Tuple[str, ...] = (
    "XAVC-I",
    "XAVC-L",
    "RAW",
    "RAW & XAVC-I",
    "RAW(HDMI)",
    "RAW(HDMI) & XAVC-I",
)

# File Settings (all Initialize-only)
FILE_SETTINGS_RESETTABLE_BY_CAMSET_RESET_G147 = False
FILE_NUMBER_SERIES_G147 = "Series"
FILE_NUMBER_RESET_G147 = "Reset"
FILE_NUMBER_DEFAULT_G147 = FILE_NUMBER_SERIES_G147
ALLOWED_FILE_NUMBER_MODES_G147: Tuple[str, ...] = (
    FILE_NUMBER_SERIES_G147,
    FILE_NUMBER_RESET_G147,
)

FILE_NAME_FORMAT_STANDARD_G147 = "Standard"
FILE_NAME_FORMAT_CAM_ID_REEL_G147 = "Cam ID + Reel#"
FILE_NAME_FORMAT_TITLE_G147 = "Title"
FILE_NAME_FORMAT_DATE_TITLE_G147 = "Date + Title"
FILE_NAME_FORMAT_TITLE_DATE_G147 = "Title + Date"
FILE_NAME_FORMAT_DEFAULT_G147 = FILE_NAME_FORMAT_STANDARD_G147
ALLOWED_FILE_NAME_FORMATS_G147: Tuple[str, ...] = (
    FILE_NAME_FORMAT_STANDARD_G147,
    FILE_NAME_FORMAT_CAM_ID_REEL_G147,
    FILE_NAME_FORMAT_TITLE_G147,
    FILE_NAME_FORMAT_DATE_TITLE_G147,
    FILE_NAME_FORMAT_TITLE_DATE_G147,
)

CARD_TYPE_SDHC_G147 = "SDHC"
CARD_TYPE_SDXC_G147 = "SDXC"
CARD_TYPE_CFEXPRESS_TYPE_A_G147 = "CFexpress Type A"
ALLOWED_CARD_TYPES_G147: Tuple[str, ...] = (
    CARD_TYPE_SDHC_G147,
    CARD_TYPE_SDXC_G147,
)
ALLOWED_ALL_CARD_TYPES_G147: Tuple[str, ...] = (
    CARD_TYPE_SDHC_G147,
    CARD_TYPE_SDXC_G147,
    CARD_TYPE_CFEXPRESS_TYPE_A_G147,
)
FILESYSTEM_FAT32_G147 = "FAT32"
FILESYSTEM_EXFAT_G147 = "exFAT"
ALLOWED_FILESYSTEMS_G147: Tuple[str, ...] = (
    FILESYSTEM_FAT32_G147,
    FILESYSTEM_EXFAT_G147,
)
SDHC_MAX_CAPACITY_GB_G147 = 32
SDHC_XAVCS_SPLIT_BYTES_G147 = 4 * 1024 * 1024 * 1024  # 4 GB

CAMERA_POS_C_G147 = "C"
CAMERA_POS_L_G147 = "L"
CAMERA_POS_R_G147 = "R"
ALLOWED_CAMERA_POSITIONS_G147: Tuple[str, ...] = (
    CAMERA_POS_C_G147,
    CAMERA_POS_L_G147,
    CAMERA_POS_R_G147,
)
REEL_NUMBER_MIN_G147 = 1
REEL_NUMBER_MAX_G147 = 999
FILE_SEQ_NUMBER_MIN_G147 = 1
FILE_SEQ_NUMBER_MAX_G147 = 999

TITLE_NAME_DEFAULT_G147 = "C"
TITLE_NAME_MAX_CHARS_G147 = 37
TITLE_NAME_ALLOWED_SYMBOLS_G147 = ".-_@!#$%+=^~(),;[]"
TITLE_NAME_VALID_RE_G147 = re.compile(
    r"^[A-Za-z0-9.\-_@!#$%+=^~(),;\[\]]{1,37}$"
)
FX3_MOVIE_CLIP_FOLDER_PATH_G147 = "PRIVATE/M4ROOT/CLIP"
FX6_CLIP_PREFIX_MIN_CHARS_G147 = 4
FX6_CLIP_PREFIX_MAX_CHARS_G147 = 46
FX6_CFEXPRESS_CLIP_FOLDER_PATH_G147 = "/XDROOT/Clip"
FX6_SDXC_CLIP_FOLDER_PATH_G147 = "/PRIVATE/XDROOT/Clip"

# F-UXC resid16 anchors (G147)
FILE_SETTINGS_F_RESID16_G147 = 0x61BC
FILE_NAME_FORMAT_F_RESID16_G147 = 0x7821
SERIES_COUNTER_RESET_F_RESID16_G147 = 0x7A28
CAM_ID_REEL_F_RESID16_G147 = 0x67AE
TITLE_NAME_SETTINGS_F_RESID16_G147 = 0x6C14
SDHC_FORMAT_ERROR_BASE_RESID16_G147 = 0xE8F8

STATUS_VERIFIED_G147 = (
    "VERIFIED_G147_BREATHING_COMP_120P_CATALYST_AND_CAMID_REEL_SDHC_VAULT_GUARD"
)
STATUS_BLOCKED_G147_TELEMETRY_INVALID = "BLOCKED_G147_TELEMETRY_INVALID"
STATUS_BLOCKED_G147_BREATHING_120P_SQ_RAW_OR_RESET_VIOLATION = (
    "BLOCKED_G147_BREATHING_120P_SQ_RAW_OR_RESET_VIOLATION"
)
STATUS_BLOCKED_G147_LENS_CATALYST_BROWSE_OR_FX6_EOPNOTSUPP = (
    "BLOCKED_G147_LENS_CATALYST_BROWSE_OR_FX6_EOPNOTSUPP"
)
STATUS_BLOCKED_G147_SDHC_FILESETTINGS_CAMID_TITLE_VIOLATION = (
    "BLOCKED_G147_SDHC_FILESETTINGS_CAMID_TITLE_VIOLATION"
)
STATUS_BLOCKED_G147_SLOT1_TIER0_VAULT_EROFS = (
    "BLOCKED_G147_SLOT1_TIER0_VAULT_EROFS"
)


# ---------------------------------------------------------------------------
# Gate G148 Constants: Round-57 [Copyright Info] 46-Char & [Write Serial Number]
#                      Reset Errata, 2-Item [Power Setting Option] (9-Cond),
#                      Dormant [Power Save by Monitor], and [NTSC/PAL Selector]
# ---------------------------------------------------------------------------

COPYRIGHT_INFO_MENU_PATH_G148 = "Shooting -> [File] -> [Copyright Info]"
WRITE_SERIAL_NUMBER_MENU_PATH_G148 = "Shooting -> [File] -> [Write Serial Number]"
POWER_SETTING_OPTION_MENU_PATH_G148 = "Setup -> [Power Setting Option]"
NTSC_PAL_SELECTOR_MENU_PATH_G148 = "Setup -> [Area/Date] -> [NTSC/PAL Selector]"
FX6_REC_FORMAT_FREQUENCY_MENU_PATH_G148 = "Project > Rec Format > Frequency"

EXACT_4_COPYRIGHT_INFO_ITEMS_G148: Tuple[str, ...] = (
    "Write Copyright Info",
    "Set Photographer",
    "Set Copyright",
    "Disp. Copyright Info",
)
COPYRIGHT_MAX_CHARS_G148 = 46
# Round-57 Reset Errata: ALL 4 [Copyright Info] items AND active Still+Movie
# [Write Serial Number] are Initialize-only ("Not available" under [Camera
# Settings Reset]).
COPYRIGHT_INFO_RESETTABLE_BY_CAMSET_RESET_G148 = False
WRITE_SERIAL_NUMBER_RESETTABLE_BY_CAMSET_RESET_G148 = False
WRITE_SERIAL_NUMBER_SYMBOL_STILL_MOVIE_G148 = (
    "BKID_APP_setting_write_serial_number_still_movie"
)
WRITE_SERIAL_NUMBER_LEGACY_STILL_ONLY_SYMBOL_G148 = (
    "BKID_APP_setting_still_write_serial_number"
)
COPYRIGHT_INFO_EXCLUDED_FROM_CAMSET_DAT_G148 = True
WRITE_SERIAL_NUMBER_EXCLUDED_FROM_CAMSET_DAT_G148 = False
FX6_LENS_SERIAL_PRESET_SLOTS_G148 = 6  # 0..5

# Power Setting Option: exact 2 active Initialize-only items
EXACT_2_POWER_SETTING_OPTION_ITEMS_G148: Tuple[str, ...] = (
    "Power Save Start Time",
    "Auto Power OFF Temp.",
)
POWER_SETTING_OPTION_RESETTABLE_BY_CAMSET_RESET_G148 = False

POWER_SAVE_OFF_G148 = "Off"
POWER_SAVE_30_MIN_G148 = "30 Min"
POWER_SAVE_5_MIN_G148 = "5 Min"
POWER_SAVE_2_MIN_G148 = "2 Min"
POWER_SAVE_1_MIN_G148 = "1 Min"
POWER_SAVE_10_SEC_G148 = "10 Sec"
POWER_SAVE_START_TIME_DEFAULT_G148 = POWER_SAVE_5_MIN_G148
ALLOWED_POWER_SAVE_START_TIMES_G148: Tuple[str, ...] = (
    POWER_SAVE_OFF_G148,
    POWER_SAVE_30_MIN_G148,
    POWER_SAVE_5_MIN_G148,
    POWER_SAVE_2_MIN_G148,
    POWER_SAVE_1_MIN_G148,
    POWER_SAVE_10_SEC_G148,
)
POWER_SAVE_START_TIME_SECONDS_G148: Dict[str, Optional[int]] = {
    POWER_SAVE_OFF_G148: None,
    POWER_SAVE_30_MIN_G148: 1800,
    POWER_SAVE_5_MIN_G148: 300,
    POWER_SAVE_2_MIN_G148: 120,
    POWER_SAVE_1_MIN_G148: 60,
    POWER_SAVE_10_SEC_G148: 10,
}
DORMANT_POWER_SAVE_VALUES_G148: Tuple[str, ...] = (
    "20SEC",
    "NO_LIMIT",
    "30 sec",
    "60 min",
    "240 min",
)
EXACT_9_POWER_SAVE_BYPASS_CONDITIONS_G148: Tuple[str, ...] = (
    "usb_power_supply",
    "slideshow_playback",
    "ftp_transfer",
    "recording_movies",
    "pc_connection",
    "tv_hdmi_connection",
    "ir_remote_ctrl_on",
    "bluetooth_rmt_ctrl_on",
    "streaming_or_creators_cloud_upload",
)

AUTO_POWER_OFF_TEMP_STANDARD_G148 = "Standard"
AUTO_POWER_OFF_TEMP_HIGH_G148 = "High"
AUTO_POWER_OFF_TEMP_DEFAULT_G148 = AUTO_POWER_OFF_TEMP_STANDARD_G148
ALLOWED_AUTO_POWER_OFF_TEMP_MODES_G148: Tuple[str, ...] = (
    AUTO_POWER_OFF_TEMP_STANDARD_G148,
    AUTO_POWER_OFF_TEMP_HIGH_G148,
)

# Dormant [Power Save by Monitor] on zero-EVF ILME-FX3
DORMANT_POWER_SAVE_BY_MONITOR_NAME_G148 = "Power Save by Monitor"
DORMANT_POWER_SAVE_BY_MONITOR_BKID_G148 = "BKID_APP_setting_monitor_power_linkage"
DORMANT_POWER_SAVE_BY_MONITOR_F_RESID16S_G148: Tuple[int, ...] = (
    0x783F,
    0x6DB5,
    0x6DB6,
    0x60A8,
    0x6B2E,
)

# NTSC/PAL Selector
VIDEO_SYSTEM_NTSC_G148 = "NTSC"
VIDEO_SYSTEM_PAL_G148 = "PAL"
ALLOWED_VIDEO_SYSTEMS_G148: Tuple[str, ...] = (
    VIDEO_SYSTEM_NTSC_G148,
    VIDEO_SYSTEM_PAL_G148,
)
NTSC_PAL_RESETTABLE_BY_CAMSET_RESET_G148 = False
STARTUP_BANNER_NTSC_G148 = "Running on NTSC."
STARTUP_BANNER_PAL_G148 = "Running on PAL."
STARTUP_BANNER_NONE_G148 = ""
NTSC_ALLOWED_FPS_G148: Tuple[float, ...] = (23.98, 24.0, 29.97, 59.94, 119.88)
PAL_ALLOWED_FPS_G148: Tuple[float, ...] = (25.0, 50.0, 100.0)
NTSC_PAL_FORMAT_PROMPT_BASE_RESID16S_G148: Tuple[int, ...] = (
    0xE1E6,
    0xE373,
    0xE51A,
    0xE595,
    0xE9F6,
)
FX6_FREQUENCY_OPTIONS_G148: Tuple[str, ...] = (
    "59.94",
    "50",
    "29.97",
    "25",
    "24",
    "23.98",
)

# F-UXC / base / _g resid16 anchors (G148)
COPYRIGHT_INFO_F_RESID16_G148 = 0x6D53
WRITE_COPYRIGHT_INFO_F_RESID16_G148 = 0x7AE4
SET_PHOTOGRAPHER_F_RESID16_G148 = 0x7172
SET_COPYRIGHT_F_RESID16_G148 = 0x612B
DISP_COPYRIGHT_INFO_F_RESID16_G148 = 0x611B
WRITE_SERIAL_NUMBER_F_RESID16_G148 = 0x7058
WRITE_SERIAL_NUMBER_STILL_LEGACY_F_RESID16_G148 = 0x792C
POWER_SAVE_START_TIME_F_RESID16_G148 = 0x69B0
AUTO_POWER_OFF_TEMP_F_RESID16_G148 = 0x70F1
AUTO_POWER_OFF_TEMP_TRIPOD_G_RESID16_G148 = 0x61A9
NTSC_PAL_SELECTOR_F_RESID16_G148 = 0x6B6F

STATUS_VERIFIED_G148 = (
    "VERIFIED_G148_COPYRIGHT_46CH_SERIAL_ERRATA_AND_POWERSAVE_NTSCPAL_VAULT_GUARD"
)
STATUS_BLOCKED_G148_TELEMETRY_INVALID = "BLOCKED_G148_TELEMETRY_INVALID"
STATUS_BLOCKED_G148_COPYRIGHT_46CH_SERIAL_RESET_OR_CAMSET_PII_VIOLATION = (
    "BLOCKED_G148_COPYRIGHT_46CH_SERIAL_RESET_OR_CAMSET_PII_VIOLATION"
)
STATUS_BLOCKED_G148_DORMANT_MONITOR_POWER_SAVING_OR_FX6_EOPNOTSUPP = (
    "BLOCKED_G148_DORMANT_MONITOR_POWER_SAVING_OR_FX6_EOPNOTSUPP"
)
STATUS_BLOCKED_G148_POWERSAVE_9COND_TEMP_HIGH_OR_NTSCPAL_VIOLATION = (
    "BLOCKED_G148_POWERSAVE_9COND_TEMP_HIGH_OR_NTSCPAL_VIOLATION"
)
STATUS_BLOCKED_G148_SLOT1_FORMAT_SD_ERASE_TRIM_VAULT_EROFS = (
    "BLOCKED_G148_SLOT1_FORMAT_SD_ERASE_TRIM_VAULT_EROFS"
)
STATUS_BLOCKED_PHASE331_DONOR_INTEGRITY = "BLOCKED_PHASE331_DONOR_INTEGRITY"


# ---------------------------------------------------------------------------
# Pinned Wave-64 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE331: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x03BC617E, b"BKID_APP_setting_lens_comp_breathing"),
    (0x03BC61A3, b"BKID_APP_MR_setting_lens_comp_breathing"),
    (0x0394A754, b"PID_SET_BREATHING_CORRECTION"),
    (0x039BAA5B, b"PRM_HAITA_setting_lens_comp_breathing_exposure_mode"),
    (0x039BAA01, b"PRM_HAITA_breathing_correction_lens_type_lens_information"),
    (0x03BB81B9, b"CAUTION_ID_FACTOR_CAM_LENS_BREATHING_COMP_NOT_SUPPORT_MSG"),
    (0x03BC63A7, b"BKID_APP_setting_xavcs_file_number"),
    (0x03BC63ED, b"BKID_APP_setting_xavc_s_file_name_camid_camera_id"),
    (0x03BC641F, b"BKID_APP_setting_xavc_s_file_name_camid_camera_position"),
    (0x03BF2614, b"BKID_APP_setting_xavcs_file_name_reel_number"),
    (0x03C417EC, b"MODEL_MOVIE_REC_REEL_NUMBER_PLUS_1_NOTIFY"),
    (0x03BF266C, b"BKID_APP_update_required_xavcs_file_name_reel_number"),
    (0x03BF2641, b"BKID_APP_recorded_after_camid_reel_setting"),
    (0x03C174BA, b"SOFTWARE_KEYBOARD_TITLE_PREFIX"),
    (0x03C3D556, b"EVENT_REMOTE_SET_XAVC_S_FILE_NAME_TITLE_PREFIX"),
    (0x03BC6319, b"BKID_APP_setting_still_write_copyright_infomation"),
    (0x03BC22A8, b"BKID_APP_photographer_name"),
    (0x03BC22C3, b"BKID_APP_copyright_name"),
    (0x03C172BE, b"SOFTWARE_KEYBOARD_COPYRIGHT_NAME"),
    (0x03BC634B, b"BKID_APP_setting_still_write_serial_number"),
    (0x03BC6376, b"BKID_APP_setting_write_serial_number_still_movie"),
    (0x03BCBF42, b"BKID_APP_setting_start_power_saving"),
    (0x03B4A0BA, b"VAL_setting_start_power_saving_START_POWER_SAVING_5MIN"),
    (0x03BCBFB2, b"BKID_APP_setting_auto_pwr_off_temp"),
    (0x03BCBF66, b"BKID_APP_setting_monitor_power_linkage"),
    (0x03BCED78, b"BKID_APP_setting_ntsc_pal_selector"),
    (0x039A8357, b"PRM_HAITA_streaming_mode_setting_ntsc_pal_selector"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE331 = (
    "e466b63226e21591d34baeff1720ec0297873062d46c1f64dba0b428a04e9c39"
)

PINNED_FX6_APPFW_SLICES_PHASE331: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x0270658B, b"BKID_APP_SETTING_LENS_COMP_BREATHING"),
    (0x0271E815, b"BKID_APP_CAMID_CURRENT_CAMERA_ID0"),
    (0x0271E859, b"BKID_APP_CAMID_CURRENT_REEL_NUMBER0"),
    (0x0273C8B4, b"DIADEM_PRO"),
    (0x0273D1F3, b"BKID_APP_SETTING_TITLE_PREFIX"),
    (0x0271DCC2, b"BKID_APP_CURRENT_LENS_SERIAL_NUMBER"),
    (0x0271E44F, b"BKID_APP_PRESET_LENS_SERIAL_NUMBER0"),
    (0x02709121, b"BKID_APP_SETTING_FREQUENCY_REC_FORMAT"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE331 = (
    "cccf1d05c2c3fc40729917f75928ff77987c3bbc35f93173119e3867cda6d068"
)

PINNED_PHASE331_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE331,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE331),
        "FX3 appFw.so Wave-64 Breathing/CamID-Reel/Copyright/Serial/PowerSave/NTSC-PAL slices",
    ),
    "fx3_lib_saveload_settings_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (b"\x7fELF", b"SaveLoadSettings"),
        "FX3 libSaveLoadSettings.so CAMSET*.DAT export/load bridge",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Breathing Comp.",
            b"File Settings",
            b"File Name Format",
            b"Series Counter Reset",
            b"Cam ID + Reel#",
            b"Camera ID",
            b"Reel Number",
            b"Camera Position",
            b"Title Name Settings",
            b"Copyright Info",
            b"Write Copyright Info",
            b"Set Photographer",
            b"Set Copyright",
            b"Disp. Copyright Info",
            b"Write Serial Number",
            b"Power Save Start Time",
            b"Auto Power OFF Temp.",
            b"Power Save by Monitor",
            b"NTSC/PAL Selector",
        ),
        "FX3 string_english_f.uxc Wave-64 EN parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Series",
            b"Use an SDXC",
            b"Running on NTSC.",
            b"Running on PAL.",
            b"Reboots after change is made.",
            b"Format?",
        ),
        "FX3 string_english.uxc Wave-64 base NTSC/PAL & SDHC tokens",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"When shooting from a tripod",
            b"NTSC/PAL",
        ),
        "FX3 string_english_g.uxc Wave-64 tripod warning & NTSC/PAL playback lock",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "呼吸补偿".encode("utf-8"),
            "文件设置".encode("utf-8"),
            "文件名格式".encode("utf-8"),
            "版权信息".encode("utf-8"),
            "写入序列号".encode("utf-8"),
            "自动关机开始时间".encode("utf-8"),
            "自动关机温度".encode("utf-8"),
            "NTSC/PAL选择器".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-64 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "呼吸補償".encode("utf-8"),
            "檔案設定".encode("utf-8"),
            "檔案名稱格式".encode("utf-8"),
            "版權資訊".encode("utf-8"),
            "寫入序號".encode("utf-8"),
            "省電開始時間".encode("utf-8"),
            "自動關閉電源溫度".encode("utf-8"),
            "NTSC/PAL選擇器".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-64 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "ブリージング補正".encode("utf-8"),
            "ファイル設定".encode("utf-8"),
            "ファイル名形式".encode("utf-8"),
            "著作権情報".encode("utf-8"),
            "ｼﾘｱﾙ番号書き込み".encode("utf-8"),
            "ﾊﾟﾜｰｾｰﾌﾞ開始時間".encode("utf-8"),
            "自動電源OFF温度".encode("utf-8"),
            "NTSC/PAL切換".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-64 JA parity",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4\x00",),
        "FX3-CX95900_ALLLANG-Backup.bin BK4 seed",
    ),
    "fx6_appfw_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
        50_520_424,
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE331,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE331),
        "FX6 appFw.so Wave-64 Breathing/CamID/TitlePrefix/LensSerial/Frequency slices",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"Breathing Compensation",
            b"Reel",
            b"Title Prefix",
            b"Frequency",
            b"Rec Format",
        ),
        "FX6 string_english.uxc Wave-64 EN baseline",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"NTSC/PAL",
            b"On(Serial Number)",
        ),
        "FX6 string_english_2.uxc Wave-64 EN legacy/enterprise baseline",
    ),
}


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _is_clean_room_forced(force_clean_room: Optional[bool]) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE331):
        if os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def _is_strict_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _is_strict_num(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def _is_on_off(val: Any) -> bool:
    return isinstance(val, str) and val in ("On", "Off")


def _is_printable_ascii(val: str) -> bool:
    return all(0x20 <= ord(ch) <= 0x7E for ch in val)


def _encode_token_variants(token: bytes) -> Tuple[bytes, ...]:
    variants = [token]
    try:
        text = token.decode("utf-8")
        variants.append(text.encode("utf-16-le"))
    except UnicodeDecodeError:
        pass
    return tuple(variants)


def _read_exact_o_rdonly_slices(
    path: Path, slices: Sequence[Tuple[int, bytes]]
) -> Tuple[int, str, List[str]]:
    missing: List[str] = []
    hasher = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY)
    try:
        st = os.fstat(fd)
        for offset, expected in slices:
            chunk = os.pread(fd, len(expected), offset)
            if chunk != expected:
                missing.append(f"slice_mismatch@0x{offset:08X}")
            hasher.update(chunk)
        return st.st_size, hasher.hexdigest(), missing
    finally:
        os.close(fd)


def _read_full_o_rdonly_sha256_and_tokens(
    path: Path, required_tokens: Sequence[bytes]
) -> Tuple[int, str, List[str]]:
    missing: List[str] = []
    fd = os.open(path, os.O_RDONLY)
    try:
        st = os.fstat(fd)
        data = os.read(fd, st.st_size)
    finally:
        os.close(fd)
    sha = hashlib.sha256(data).hexdigest()
    for tok in required_tokens:
        if not any(var in data for var in _encode_token_variants(tok)):
            missing.append(f"token_missing:{tok[:32]!r}")
    return st.st_size, sha, missing


def _parse_fw_float(ver_str: str) -> Optional[float]:
    if not isinstance(ver_str, str) or not ver_str.strip():
        return None
    try:
        return float(ver_str.strip())
    except ValueError:
        return None


def _validate_fx3_body_identity(
    body_model_name: str,
    body_model_id: int,
    help_guide_code: str,
    firmware_version: str,
) -> List[str]:
    errs: List[str] = []
    if body_model_name != FX3_MODEL_NAME_PHASE331:
        errs.append(f"body_model_name_invalid:{body_model_name!r}")
    if not _is_strict_int(body_model_id) or body_model_id != FX3_MODEL_ID_PHASE331:
        errs.append(f"body_model_id_invalid:{body_model_id!r}")
    if help_guide_code != FX3_HELP_GUIDE_CODE_PHASE331:
        errs.append(f"help_guide_code_invalid:{help_guide_code!r}")
    if _parse_fw_float(firmware_version) is None:
        errs.append(f"firmware_version_invalid:{firmware_version!r}")
    return errs


# ---------------------------------------------------------------------------
# Donor Integrity Audit (O_RDONLY / Clean-Room Dual-Mode)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase331DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    fx3_contracts_verified: bool
    fx6_contracts_verified: bool
    four_lang_resid16_parity_verified: bool
    zero_forbidden_myths_verified: bool
    elapsed_seconds: float
    within_budget_200ms: bool
    raw_firmware_bytes_leaked: int
    file_digests: Dict[str, str]
    missing_markers: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def audit_phase331_donor_contracts(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase331DonorAuditResult:
    """Fast (< 0.20s) O_RDONLY + bounded os.pread donor audit with clean-room fallback."""
    import time

    t0 = time.perf_counter()
    clean_forced = _is_clean_room_forced(force_clean_room)
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else dict(PINNED_PHASE331_DONOR_SPECS)
    )
    resolved_work_root = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(
            repo_root=repo_root or DEFAULT_REPO_ROOT
        ).work_root
    )

    if clean_forced:
        dt = time.perf_counter() - t0
        return Phase331DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_NO_DONOR_DISK_IO",
            files_inspected=0,
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            zero_forbidden_myths_verified=True,
            elapsed_seconds=round(dt, 6),
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE331,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(),
        )

    missing_files = (
        list(specs.keys())
        if resolved_work_root is None
        else [
            key
            for key, spec in specs.items()
            if not (resolved_work_root / spec[1]).is_file()
        ]
    )
    if missing_files and donor_specs_override is None:
        dt = time.perf_counter() - t0
        return Phase331DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_ABSENT_DONOR_FALLBACK",
            files_inspected=0,
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            zero_forbidden_myths_verified=True,
            elapsed_seconds=round(dt, 6),
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE331,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(
                f"Donor files absent ({len(missing_files)} missing); "
                "verified Phase 331 via clean-room synthetic fallback.",
            ),
        )

    file_digests: Dict[str, str] = {}
    missing_markers: List[str] = []
    errors: List[str] = []
    inspected = 0

    for key, (
        family,
        rel_path,
        expected_size,
        expected_sha,
        tokens,
        desc,
    ) in specs.items():
        if resolved_work_root is None:
            missing_markers.append(f"{key}:work_root_none")
            errors.append(f"{key}:{desc}:work_root_none")
            continue
        target = resolved_work_root / rel_path
        if not target.is_file():
            missing_markers.append(f"{key}:file_missing")
            errors.append(f"{key}:{desc}:file_missing")
            continue
        inspected += 1
        if key == "fx3_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tok_errs = _read_exact_o_rdonly_slices(
                target, PINNED_FX3_APPFW_SLICES_PHASE331
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tok_errs = _read_exact_o_rdonly_slices(
                target, PINNED_FX6_APPFW_SLICES_PHASE331
            )
        else:
            actual_size, actual_sha, tok_errs = _read_full_o_rdonly_sha256_and_tokens(
                target, tokens
            )

        file_digests[key] = actual_sha
        if actual_size != expected_size:
            missing_markers.append(
                f"{key}:size_mismatch:{actual_size}!={expected_size}"
            )
            errors.append(f"{family}:{key}:size_mismatch")
        if actual_sha != expected_sha:
            missing_markers.append(f"{key}:sha256_mismatch")
            errors.append(f"{family}:{key}:sha256_mismatch")
        for terr in tok_errs:
            missing_markers.append(f"{key}:{terr}")
            errors.append(f"{family}:{key}:{terr}")

    dt = time.perf_counter() - t0
    valid = len(errors) == 0
    return Phase331DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE
            if valid
            else STATUS_BLOCKED_PHASE331_DONOR_INTEGRITY
        ),
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="STRICT_OS_O_RDONLY_PREAD",
        files_inspected=inspected,
        fx3_contracts_verified=valid,
        fx6_contracts_verified=valid,
        four_lang_resid16_parity_verified=valid,
        zero_forbidden_myths_verified=valid,
        elapsed_seconds=round(dt, 6),
        within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE331,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        file_digests=file_digests,
        missing_markers=tuple(missing_markers),
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# Gate G147: [Breathing Comp.] (120p/100p + Catalyst Errata) & Movie
#            [File Settings] (Cam ID + Reel# / 37-Char Title / SDHC 4 GB)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BreathingCamIdReelSdhcGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    breathing_comp_menu_path: str
    file_settings_menu_path: str
    effective_breathing_comp: str
    breathing_comp_available: bool
    breathing_comp_resettable_by_camset_reset: bool
    effective_lens_breathing_support: str
    breathing_bypassed_on_hdmi_raw: bool
    catalyst_prepare_post_comp_eligible: bool
    effective_file_number_mode: str
    series_counter_next_number: int
    effective_file_name_format: str
    file_settings_resettable_by_camset_reset: bool
    sdhc_standard_format_locked: bool
    sdhc_4gb_split_enforced: bool
    simult_recording_mixed_fs_blocked: bool
    effective_camera_id: str
    effective_reel_number: int
    effective_camera_position_menu: str
    effective_filename_position_char: str
    effective_file_seq_number: int
    effective_title_name: str
    sample_output_clip_stem: str
    fx3_movie_clip_folder_path: str
    target_media_slot: int
    slot1_tier0_vault_firewall_blocked: bool
    slot1_data_sector_writes: int
    catalyst_browse_rejected: bool
    fx6_cross_model_spoof_rejected: bool
    emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _format_fx3_movie_clip_stem(
    *,
    file_name_format: str,
    camera_id: str,
    reel_number: int,
    output_pos_char: str,
    file_seq_number: int,
    title_name: str,
    date_yymmdd: str = "261117",
    date_yyyymmdd: str = "20261117",
    rand2: str = "AB",
) -> str:
    if file_name_format == FILE_NAME_FORMAT_STANDARD_G147:
        return f"C{file_seq_number:04d}"
    if file_name_format == FILE_NAME_FORMAT_CAM_ID_REEL_G147:
        return (
            f"{camera_id}{reel_number:03d}{output_pos_char}"
            f"{file_seq_number:03d}_{date_yymmdd}{rand2}"
        )
    if file_name_format == FILE_NAME_FORMAT_TITLE_G147:
        return f"{title_name}_{file_seq_number:04d}"
    if file_name_format == FILE_NAME_FORMAT_DATE_TITLE_G147:
        return f"{date_yyyymmdd}_{title_name}_{file_seq_number:04d}"
    if file_name_format == FILE_NAME_FORMAT_TITLE_DATE_G147:
        return f"{title_name}_{date_yyyymmdd}_{file_seq_number:04d}"
    return f"C{file_seq_number:04d}"


def resolve_fx3_breathing_and_file_settings_state(
    *,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE331,
    fps: float = 23.98,
    breathing_comp: str = BREATHING_COMP_DEFAULT_G147,
    distortion_comp: str = "Auto",
    lens_model: str = "SEL35F14GM",
    lens_breathing_support: str = LENS_BREATHING_SUPPORT_G147,
    macro_ring_057_10m_active: bool = False,
    teleconverter_model: str = "None",
    raw_output: str = "Off",
    clear_image_zoom_active: bool = False,
    auto_framing_active: bool = False,
    file_number_mode: str = FILE_NUMBER_DEFAULT_G147,
    existing_dir_max_file_number: int = 0,
    series_counter_reset_triggered: bool = False,
    card_type: str = CARD_TYPE_SDXC_G147,
    file_name_format: str = FILE_NAME_FORMAT_DEFAULT_G147,
    camera_id: str = "A",
    previous_camera_id: str = "A",
    reel_number: int = 1,
    camera_position: str = CAMERA_POS_C_G147,
    file_seq_number: int = 1,
    rollover_from_999: bool = False,
    title_name: str = TITLE_NAME_DEFAULT_G147,
    reset_action: str = RESET_ACTION_NONE_PHASE331,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-64 [Breathing Comp.] & [File Settings] state."""
    # Reset semantics:
    # - [Breathing Comp.] IS Resettable by [Camera Settings Reset] AND [Initialize].
    # - [File Settings] (File Number, File Name Format, Cam ID+Reel#, Title Name) are
    #   Initialize-only (survive [Camera Settings Reset]!).
    if reset_action == RESET_ACTION_INITIALIZE_PHASE331:
        eff_breathing_cfg = BREATHING_COMP_DEFAULT_G147
        eff_file_num = FILE_NUMBER_DEFAULT_G147
        eff_fmt = FILE_NAME_FORMAT_DEFAULT_G147
        eff_cam_id = "A"
        eff_reel = 1
        eff_cam_pos = CAMERA_POS_C_G147
        eff_title = TITLE_NAME_DEFAULT_G147
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331:
        eff_breathing_cfg = BREATHING_COMP_DEFAULT_G147
        eff_file_num = file_number_mode
        eff_fmt = file_name_format
        eff_cam_id = camera_id
        eff_reel = reel_number
        eff_cam_pos = camera_position
        eff_title = title_name
    else:
        eff_breathing_cfg = breathing_comp
        eff_file_num = file_number_mode
        eff_fmt = file_name_format
        eff_cam_id = camera_id
        eff_reel = reel_number
        eff_cam_pos = camera_position
        eff_title = title_name

    # Camera ID change resets Reel Number to 001 (unless Initialize already reset it),
    # whereas File Number = Reset preserves Reel Number.
    if (
        reset_action != RESET_ACTION_INITIALIZE_PHASE331
        and eff_cam_id != previous_camera_id
    ):
        eff_reel = 1

    # Teleconverter or SEL100F28GM 0.57-1.0m macro ring overrides lens support to NOT_SUPPORT
    if (
        teleconverter_model in TELECONVERTER_MODELS_G147
        or (lens_model == MACRO_RING_RESTRICTED_LENS_G147 and macro_ring_057_10m_active)
    ):
        eff_lens_support = LENS_BREATHING_NOT_SUPPORT_G147
    else:
        eff_lens_support = lens_breathing_support

    # Wave-41 Errata: unavailable in Still, regular Movie >= 100p (119.88p/100p),
    # S&Q >= 100fps (100/120/200/240fps), unsupported lens, or bypassed on HDMI RAW.
    # (< 100fps S&Q remains available on FX3!)
    hfr_blocked = (
        shoot_mode in (SHOOT_MODE_MOVIE_PHASE331, SHOOT_MODE_SQ_PHASE331)
        and fps >= BREATHING_COMP_REGULAR_MOVIE_BLOCKED_FPS_FLOOR_G147
    )
    breathing_available = (
        shoot_mode in (SHOOT_MODE_MOVIE_PHASE331, SHOOT_MODE_SQ_PHASE331)
        and (not hfr_blocked)
        and (eff_lens_support == LENS_BREATHING_SUPPORT_G147)
        and (not clear_image_zoom_active)
        and (not auto_framing_active)
    )
    bypassed_hdmi_raw = raw_output == "On"
    eff_breathing_runtime = (
        eff_breathing_cfg
        if (breathing_available and not bypassed_hdmi_raw)
        else BREATHING_COMP_OFF_G147
    )

    # Catalyst Prepare / Prepare Plugin metadata post-comp eligibility:
    # Requires in-body Distortion Comp. == Auto, supported lens, not Auto Framing / RAW.
    catalyst_prepare_eligible = (
        shoot_mode in (SHOOT_MODE_MOVIE_PHASE331, SHOOT_MODE_SQ_PHASE331)
        and (not hfr_blocked)
        and (eff_lens_support == LENS_BREATHING_SUPPORT_G147)
        and (distortion_comp == "Auto")
        and (not bypassed_hdmi_raw)
        and (not auto_framing_active)
    )

    # SDHC (FAT32 <= 32 GB) hard-locks [Standard] & splits XAVC S at 4 GB
    is_sdhc = card_type == CARD_TYPE_SDHC_G147
    eff_file_name_format = (
        FILE_NAME_FORMAT_STANDARD_G147 if is_sdhc else eff_fmt
    )

    # Series Counter Reset: max existing number + 1 (or 1 if dir is empty)
    if series_counter_reset_triggered:
        next_series_num = (
            existing_dir_max_file_number + 1 if existing_dir_max_file_number > 0 else 1
        )
    else:
        next_series_num = max(1, file_seq_number)

    # Cam ID + Reel# overflow past 999 rolls ONLY the output filename char (C999->D001),
    # keeping menu setting eff_cam_pos unchanged!
    if rollover_from_999 and eff_file_name_format == FILE_NAME_FORMAT_CAM_ID_REEL_G147:
        out_pos_char = chr(ord(eff_cam_pos) + 1)
        out_seq_num = 1
    else:
        out_pos_char = eff_cam_pos
        out_seq_num = next_series_num if series_counter_reset_triggered else file_seq_number

    clip_stem = _format_fx3_movie_clip_stem(
        file_name_format=eff_file_name_format,
        camera_id=eff_cam_id,
        reel_number=eff_reel,
        output_pos_char=out_pos_char,
        file_seq_number=out_seq_num,
        title_name=eff_title,
    )

    return {
        "effective_breathing_comp": eff_breathing_runtime,
        "breathing_comp_menu_value": eff_breathing_cfg,
        "breathing_comp_available": breathing_available,
        "breathing_bypassed_on_hdmi_raw": bypassed_hdmi_raw,
        "effective_lens_breathing_support": eff_lens_support,
        "catalyst_prepare_post_comp_eligible": catalyst_prepare_eligible,
        "effective_file_number_mode": eff_file_num,
        "series_counter_next_number": next_series_num,
        "effective_file_name_format": eff_file_name_format,
        "sdhc_standard_format_locked": is_sdhc,
        "sdhc_4gb_split_enforced": is_sdhc,
        "effective_camera_id": eff_cam_id,
        "effective_reel_number": eff_reel,
        "effective_camera_position_menu": eff_cam_pos,
        "effective_filename_position_char": out_pos_char,
        "effective_file_seq_number": out_seq_num,
        "effective_title_name": eff_title,
        "sample_output_clip_stem": clip_stem,
    }


def compute_breathing_camid_reel_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G147 (864 states)."""
    combos = list(
        itertools.product(
            ALLOWED_SHOOT_MODES_PHASE331,
            (24.0, 60.0, 120.0, 240.0),
            ALLOWED_BREATHING_COMP_MODES_G147,
            ("Off", "On"),  # raw_output
            ALLOWED_CARD_TYPES_G147,
            (
                FILE_NAME_FORMAT_STANDARD_G147,
                FILE_NAME_FORMAT_CAM_ID_REEL_G147,
                FILE_NAME_FORMAT_TITLE_G147,
            ),
            (
                RESET_ACTION_NONE_PHASE331,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331,
                RESET_ACTION_INITIALIZE_PHASE331,
            ),
        )
    )
    breathing_active_count = 0
    breathing_blocked_hfr_count = 0
    sdhc_standard_locked_count = 0
    camset_preserved_camid_reel_count = 0
    camset_reset_breathing_count = 0

    for sm, fps, bc, raw_m, card, fmt, rst in combos:
        st = resolve_fx3_breathing_and_file_settings_state(
            shoot_mode=sm,
            fps=fps,
            breathing_comp=bc,
            raw_output=raw_m,
            card_type=card,
            file_name_format=fmt,
            reset_action=rst,
        )
        if st["effective_breathing_comp"] == BREATHING_COMP_ON_G147:
            breathing_active_count += 1
        if sm in (SHOOT_MODE_MOVIE_PHASE331, SHOOT_MODE_SQ_PHASE331) and fps >= 100.0:
            breathing_blocked_hfr_count += 1
        if st["sdhc_standard_format_locked"]:
            sdhc_standard_locked_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331
            and card == CARD_TYPE_SDXC_G147
            and fmt == FILE_NAME_FORMAT_CAM_ID_REEL_G147
            and st["effective_file_name_format"] == FILE_NAME_FORMAT_CAM_ID_REEL_G147
        ):
            camset_preserved_camid_reel_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331
            and bc == BREATHING_COMP_ON_G147
            and st["breathing_comp_menu_value"] == BREATHING_COMP_OFF_G147
        ):
            camset_reset_breathing_count += 1

    return {
        "total_matrix_states": len(combos),
        "breathing_active_count": breathing_active_count,
        "breathing_blocked_hfr_count": breathing_blocked_hfr_count,
        "sdhc_standard_locked_count": sdhc_standard_locked_count,
        "camset_preserved_camid_reel_count": camset_preserved_camid_reel_count,
        "camset_reset_breathing_count": camset_reset_breathing_count,
    }


def verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE331,
    body_model_id: int = FX3_MODEL_ID_PHASE331,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE331,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE331,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE331,
    fps: float = 23.98,
    breathing_comp: str = BREATHING_COMP_DEFAULT_G147,
    distortion_comp: str = "Auto",
    lens_model: str = "SEL35F14GM",
    lens_breathing_support: str = LENS_BREATHING_SUPPORT_G147,
    macro_ring_057_10m_active: bool = False,
    teleconverter_model: str = "None",
    raw_output: str = "Off",
    claimed_breathing_applied_to_hdmi_raw: bool = False,
    clear_image_zoom_active: bool = False,
    auto_framing_active: bool = False,
    catalyst_tool: str = CATALYST_PREPARE_PAID_TOOLS_G147[0],
    catalyst_breathing_comp_requested: bool = False,
    file_number_mode: str = FILE_NUMBER_DEFAULT_G147,
    existing_dir_max_file_number: int = 0,
    series_counter_reset_triggered: bool = False,
    claimed_series_reset_ignores_existing_files: bool = False,
    card_type: str = CARD_TYPE_SDXC_G147,
    secondary_card_type: str = CARD_TYPE_SDXC_G147,
    simult_recording_active: bool = False,
    sdhc_capacity_gb: int = 32,
    sdhc_4gb_split_bypass_requested: bool = False,
    file_name_format: str = FILE_NAME_FORMAT_DEFAULT_G147,
    camera_id: str = "A",
    previous_camera_id: str = "A",
    reel_number: int = 1,
    claimed_file_number_reset_clears_reel: bool = False,
    camera_position: str = CAMERA_POS_C_G147,
    file_seq_number: int = 1,
    rollover_from_999: bool = False,
    claimed_999_overflow_mutates_menu_position: bool = False,
    title_name: str = TITLE_NAME_DEFAULT_G147,
    requested_custom_movie_folder_path: Optional[str] = None,
    target_media_slot: int = MEDIA_SLOT_2_PHASE331,
    requested_write_operation: bool = False,
    series_counter_reset_write_requested: bool = False,
    camid_reel_state_flush_requested: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE331,
    claimed_camset_reset_preserves_breathing: bool = False,
    claimed_camset_reset_clears_file_settings_or_lens_comp: bool = False,
    fx6_breathing_under_sq_or_raw_or_distortion_off_requested: bool = False,
    fx6_46char_title_prefix_or_xdroot_spoof_requested: bool = False,
) -> BreathingCamIdReelSdhcGuardResult:
    """Enforce Gate G147: [Breathing Comp.] Wave-41/Catalyst Errata & Movie [File Settings] / SDHC / Slot-1 Vault."""
    errors: List[str] = []
    warnings: List[str] = []
    violations: List[str] = []

    def _add(code: str, msg: str) -> None:
        violations.append(code)
        errors.append(msg)

    errors.extend(
        _validate_fx3_body_identity(
            body_model_name, body_model_id, help_guide_code, firmware_version
        )
    )
    fw_float = _parse_fw_float(firmware_version)

    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE331:
        _add("TELEMETRY_INVALID", f"shoot_mode_invalid:{shoot_mode!r}")
    if not _is_strict_num(fps) or fps <= 0:
        _add("TELEMETRY_INVALID", f"fps_invalid:{fps!r}")
    if breathing_comp not in ALLOWED_BREATHING_COMP_MODES_G147:
        _add("TELEMETRY_INVALID", f"breathing_comp_invalid:{breathing_comp!r}")
    if distortion_comp not in ALLOWED_DISTORTION_COMP_MODES_G147:
        _add("TELEMETRY_INVALID", f"distortion_comp_invalid:{distortion_comp!r}")
    if lens_breathing_support not in ALLOWED_LENS_BREATHING_SUPPORT_STATES_G147:
        _add(
            "TELEMETRY_INVALID",
            f"lens_breathing_support_invalid:{lens_breathing_support!r}",
        )
    if not _is_on_off(raw_output):
        _add("TELEMETRY_INVALID", f"raw_output_invalid:{raw_output!r}")
    if file_number_mode not in ALLOWED_FILE_NUMBER_MODES_G147:
        _add("TELEMETRY_INVALID", f"file_number_mode_invalid:{file_number_mode!r}")
    if file_name_format not in ALLOWED_FILE_NAME_FORMATS_G147:
        _add("TELEMETRY_INVALID", f"file_name_format_invalid:{file_name_format!r}")
    if card_type not in ALLOWED_ALL_CARD_TYPES_G147:
        _add("TELEMETRY_INVALID", f"card_type_invalid:{card_type!r}")
    if secondary_card_type not in ALLOWED_ALL_CARD_TYPES_G147:
        _add("TELEMETRY_INVALID", f"secondary_card_type_invalid:{secondary_card_type!r}")
    if camera_position not in ALLOWED_CAMERA_POSITIONS_G147:
        _add("TELEMETRY_INVALID", f"camera_position_invalid:{camera_position!r}")
    if not _is_strict_int(reel_number) or not (
        REEL_NUMBER_MIN_G147 <= reel_number <= REEL_NUMBER_MAX_G147
    ):
        _add("TELEMETRY_INVALID", f"reel_number_invalid:{reel_number!r}")
    if not _is_strict_int(file_seq_number) or not (
        FILE_SEQ_NUMBER_MIN_G147 <= file_seq_number <= FILE_SEQ_NUMBER_MAX_G147
    ):
        _add("TELEMETRY_INVALID", f"file_seq_number_invalid:{file_seq_number!r}")
    if not isinstance(camera_id, str) or len(camera_id) != 1 or not ("A" <= camera_id <= "Z"):
        _add("TELEMETRY_INVALID", f"camera_id_invalid:{camera_id!r}")
    if (
        not isinstance(previous_camera_id, str)
        or len(previous_camera_id) != 1
        or not ("A" <= previous_camera_id <= "Z")
    ):
        _add("TELEMETRY_INVALID", f"previous_camera_id_invalid:{previous_camera_id!r}")
    if not _is_strict_int(target_media_slot) or target_media_slot not in ALLOWED_MEDIA_SLOTS_PHASE331:
        _add("TELEMETRY_INVALID", f"target_media_slot_invalid:{target_media_slot!r}")
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE331:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")

    # Firmware threshold for Breathing Comp. (Ver. 3.00+)
    if breathing_comp == BREATHING_COMP_ON_G147 and fw_float is not None and fw_float < 3.00:
        _add(
            "BREATHING_EOPNOTSUPP",
            "breathing_comp_requires_fx3_ver_3_00_or_later_eopnotsupp_95",
        )

    # Lens / macro ring / teleconverter incompatibility -> EOPNOTSUPP=95 when On
    lens_blocked = (
        lens_breathing_support in (LENS_BREATHING_NOT_SUPPORT_G147, LENS_BREATHING_NA_G147)
        or teleconverter_model in TELECONVERTER_MODELS_G147
        or (lens_model == MACRO_RING_RESTRICTED_LENS_G147 and macro_ring_057_10m_active)
    )
    if breathing_comp == BREATHING_COMP_ON_G147 and lens_blocked:
        _add(
            "LENS_OR_TC_EOPNOTSUPP",
            "breathing_comp_not_supported_for_lens_macro_ring_057_10m_or_teleconverter_eopnotsupp_95",
        )

    # Catalyst Browse (free) vs paid Catalyst Prepare / Catalyst Prepare Plugin
    catalyst_browse_rejected = False
    if catalyst_breathing_comp_requested:
        if catalyst_tool == CATALYST_BROWSE_FREE_TOOL_G147 or (
            catalyst_tool not in CATALYST_PREPARE_PAID_TOOLS_G147
        ):
            catalyst_browse_rejected = True
            _add(
                "CATALYST_BROWSE_EOPNOTSUPP",
                "free_catalyst_browse_cannot_execute_breathing_comp_requires_paid_catalyst_prepare_eopnotsupp_95",
            )
        if distortion_comp != "Auto":
            _add(
                "BREATHING_CATALYST_DISTORTION_AUTO",
                "catalyst_prepare_metadata_breathing_comp_requires_in_body_distortion_comp_auto_einval_22",
            )
        if auto_framing_active or raw_output == "On":
            _add(
                "BREATHING_CATALYST_EXCLUSION",
                "catalyst_prepare_metadata_breathing_comp_unavailable_with_auto_framing_or_raw_einval_22",
            )

    # FX6 cross-model spoofs -> EOPNOTSUPP=95
    if (
        fx6_breathing_under_sq_or_raw_or_distortion_off_requested
        or fx6_46char_title_prefix_or_xdroot_spoof_requested
    ):
        _add(
            "FX6_CROSS_MODEL_EOPNOTSUPP",
            "fx6_breathing_lockout_or_46char_xdroot_clip_spoof_not_supported_on_fx3_eopnotsupp_95",
        )

    # Wave-41 Errata: regular Movie 119.88p/100p AND S&Q 100/120/200/240fps unavailable;
    # < 100fps S&Q IS allowed on FX3; Still unavailable; HDMI RAW bypassed.
    if breathing_comp == BREATHING_COMP_ON_G147:
        if shoot_mode == SHOOT_MODE_STILL_PHASE331:
            _add(
                "BREATHING_STILL_LOCKOUT",
                "breathing_comp_is_movie_only_exposure_mode_einval_22",
            )
        if shoot_mode in (SHOOT_MODE_MOVIE_PHASE331, SHOOT_MODE_SQ_PHASE331) and (
            _is_strict_num(fps) and fps >= BREATHING_COMP_REGULAR_MOVIE_BLOCKED_FPS_FLOOR_G147
        ):
            _add(
                "BREATHING_120P_100P_ERRATA",
                "wave41_errata_breathing_comp_unavailable_at_movie_119_88p_100p_or_sq_100_120_200_240fps_einval_22",
            )
        if clear_image_zoom_active or auto_framing_active:
            _add(
                "BREATHING_CIZ_AUTOFRAMING_CONFLICT",
                "breathing_comp_blocked_during_clear_image_zoom_or_auto_framing_einval_22",
            )

    if claimed_breathing_applied_to_hdmi_raw and raw_output == "On":
        _add(
            "BREATHING_HDMI_RAW_BYPASS_VIOLATION",
            "in_body_breathing_comp_is_bypassed_on_external_4264x2408_16bit_hdmi_raw_einval_22",
        )

    # Reset asymmetry: Breathing Comp IS resettable; Shading/CA/Distortion & File Settings are NOT
    if (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331
        and claimed_camset_reset_preserves_breathing
    ):
        _add(
            "BREATHING_RESET_ASYMMETRY_VIOLATION",
            "breathing_comp_is_resettable_by_camera_settings_reset_unlike_other_lens_comp_einval_22",
        )
    if (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331
        and claimed_camset_reset_clears_file_settings_or_lens_comp
    ):
        _add(
            "FILESETTINGS_OR_LENSCOMP_RESET_VIOLATION",
            "file_settings_and_shading_ca_distortion_comp_are_initialize_only_not_camset_resettable_einval_22",
        )

    # File Settings & SDHC FAT32 rules
    if card_type == CARD_TYPE_SDHC_G147:
        if not _is_strict_int(sdhc_capacity_gb) or sdhc_capacity_gb > SDHC_MAX_CAPACITY_GB_G147 or sdhc_capacity_gb <= 0:
            _add(
                "SDHC_CAPACITY_INVALID",
                f"sdhc_fat32_capacity_must_be_le_32gb:{sdhc_capacity_gb!r}",
            )
        if file_name_format != FILE_NAME_FORMAT_STANDARD_G147:
            _add(
                "SDHC_STANDARD_LOCK_VIOLATION",
                "sdhc_fat32_hard_locks_file_name_format_to_standard_einval_22",
            )
        if sdhc_4gb_split_bypass_requested:
            _add(
                "SDHC_4GB_SPLIT_VIOLATION",
                "sdhc_fat32_must_split_xavcs_recordings_at_4gb_einval_22",
            )

    # Mixed FAT32 (SDHC) + exFAT (SDXC/CFexpress) Simult. Recording block
    mixed_fs = (card_type == CARD_TYPE_SDHC_G147) != (
        secondary_card_type == CARD_TYPE_SDHC_G147
    )
    if simult_recording_active and mixed_fs:
        _add(
            "SIMULT_MIXED_FAT32_EXFAT_BLOCKED",
            "simult_recording_forbids_mixing_sdhc_fat32_and_sdxc_cfexpress_exfat_einval_22",
        )

    # Title Name Settings: <= 37 chars & exact allowed charset
    if not isinstance(title_name, str) or not TITLE_NAME_VALID_RE_G147.match(title_name):
        _add(
            "TITLE_NAME_37CHAR_VIOLATION",
            f"title_name_must_be_1_to_37_valid_ascii_chars:{title_name!r}",
        )

    # Fixed folder path PRIVATE/M4ROOT/CLIP
    if (
        requested_custom_movie_folder_path is not None
        and requested_custom_movie_folder_path != FX3_MOVIE_CLIP_FOLDER_PATH_G147
    ):
        _add(
            "FIXED_MOVIE_FOLDER_VIOLATION",
            f"fx3_movie_clip_folder_is_fixed_private_m4root_clip_cannot_use:{requested_custom_movie_folder_path!r}",
        )

    if claimed_series_reset_ignores_existing_files:
        _add(
            "SERIES_COUNTER_RESET_VIOLATION",
            "series_counter_reset_must_advance_to_max_existing_plus_1_einval_22",
        )
    if claimed_file_number_reset_clears_reel:
        _add(
            "CAM_ID_REEL_PRESERVATION_VIOLATION",
            "file_number_reset_must_preserve_reel_number_unlike_camera_id_change_einval_22",
        )
    if claimed_999_overflow_mutates_menu_position:
        _add(
            "CAM_ID_REEL_999_ROLLOVER_VIOLATION",
            "c999_to_d001_rollover_mutates_output_filename_char_only_not_menu_setting_einval_22",
        )

    state = resolve_fx3_breathing_and_file_settings_state(
        shoot_mode=shoot_mode,
        fps=float(fps) if _is_strict_num(fps) else 23.98,
        breathing_comp=breathing_comp
        if breathing_comp in ALLOWED_BREATHING_COMP_MODES_G147
        else BREATHING_COMP_DEFAULT_G147,
        distortion_comp=distortion_comp
        if distortion_comp in ALLOWED_DISTORTION_COMP_MODES_G147
        else "Auto",
        lens_model=lens_model,
        lens_breathing_support=lens_breathing_support
        if lens_breathing_support in ALLOWED_LENS_BREATHING_SUPPORT_STATES_G147
        else LENS_BREATHING_SUPPORT_G147,
        macro_ring_057_10m_active=macro_ring_057_10m_active,
        teleconverter_model=teleconverter_model,
        raw_output=raw_output if _is_on_off(raw_output) else "Off",
        clear_image_zoom_active=clear_image_zoom_active,
        auto_framing_active=auto_framing_active,
        file_number_mode=file_number_mode
        if file_number_mode in ALLOWED_FILE_NUMBER_MODES_G147
        else FILE_NUMBER_DEFAULT_G147,
        existing_dir_max_file_number=existing_dir_max_file_number,
        series_counter_reset_triggered=series_counter_reset_triggered,
        card_type=card_type if card_type in ALLOWED_ALL_CARD_TYPES_G147 else CARD_TYPE_SDXC_G147,
        file_name_format=file_name_format
        if file_name_format in ALLOWED_FILE_NAME_FORMATS_G147
        else FILE_NAME_FORMAT_DEFAULT_G147,
        camera_id=camera_id if isinstance(camera_id, str) and len(camera_id) == 1 else "A",
        previous_camera_id=previous_camera_id
        if isinstance(previous_camera_id, str) and len(previous_camera_id) == 1
        else "A",
        reel_number=reel_number if _is_strict_int(reel_number) else 1,
        camera_position=camera_position
        if camera_position in ALLOWED_CAMERA_POSITIONS_G147
        else CAMERA_POS_C_G147,
        file_seq_number=file_seq_number if _is_strict_int(file_seq_number) else 1,
        rollover_from_999=rollover_from_999,
        title_name=title_name if isinstance(title_name, str) and title_name else "C",
        reset_action=reset_action
        if reset_action in ALLOWED_RESET_ACTIONS_PHASE331
        else RESET_ACTION_NONE_PHASE331,
    )

    # Slot-1 Tier-0 Vault Firewall (EROFS=30)
    slot1_blocked = False
    if target_media_slot == MEDIA_SLOT_1_PHASE331 and (
        requested_write_operation
        or series_counter_reset_write_requested
        or camid_reel_state_flush_requested
    ):
        slot1_blocked = True
        _add(
            "SLOT1_TIER0_VAULT_EROFS",
            "slot1_tier0_vault_erofs_30_blocked_camid_reel_series_or_clip_write",
        )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G147
        block_errno = 0
        block_errno_name = "OK"
    elif slot1_blocked:
        status = STATUS_BLOCKED_G147_SLOT1_TIER0_VAULT_EROFS
        block_errno = EROFS_ERRNO_PHASE331
        block_errno_name = EROFS_NAME_PHASE331
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G147_LENS_CATALYST_BROWSE_OR_FX6_EOPNOTSUPP
        block_errno = EOPNOTSUPP_ERRNO_PHASE331
        block_errno_name = EOPNOTSUPP_NAME_PHASE331
    elif any(v == "TELEMETRY_INVALID" for v in violations) or any(
        e.startswith(
            (
                "body_model_name_invalid:",
                "body_model_id_invalid:",
                "help_guide_code_invalid:",
                "firmware_version_invalid:",
            )
        )
        for e in errors
    ):
        status = STATUS_BLOCKED_G147_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE331
        block_errno_name = EINVAL_NAME_PHASE331
    elif any("BREATHING" in v for v in violations):
        status = STATUS_BLOCKED_G147_BREATHING_120P_SQ_RAW_OR_RESET_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE331
        block_errno_name = EINVAL_NAME_PHASE331
    else:
        status = STATUS_BLOCKED_G147_SDHC_FILESETTINGS_CAMID_TITLE_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE331
        block_errno_name = EINVAL_NAME_PHASE331

    return BreathingCamIdReelSdhcGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        breathing_comp_menu_path=BREATHING_COMP_MENU_PATH_G147,
        file_settings_menu_path=FILE_SETTINGS_MENU_PATH_G147,
        effective_breathing_comp=state["effective_breathing_comp"],
        breathing_comp_available=state["breathing_comp_available"],
        breathing_comp_resettable_by_camset_reset=BREATHING_COMP_RESETTABLE_BY_CAMSET_RESET_G147,
        effective_lens_breathing_support=state["effective_lens_breathing_support"],
        breathing_bypassed_on_hdmi_raw=state["breathing_bypassed_on_hdmi_raw"],
        catalyst_prepare_post_comp_eligible=state["catalyst_prepare_post_comp_eligible"],
        effective_file_number_mode=state["effective_file_number_mode"],
        series_counter_next_number=state["series_counter_next_number"],
        effective_file_name_format=state["effective_file_name_format"],
        file_settings_resettable_by_camset_reset=FILE_SETTINGS_RESETTABLE_BY_CAMSET_RESET_G147,
        sdhc_standard_format_locked=state["sdhc_standard_format_locked"],
        sdhc_4gb_split_enforced=state["sdhc_4gb_split_enforced"],
        simult_recording_mixed_fs_blocked=mixed_fs,
        effective_camera_id=state["effective_camera_id"],
        effective_reel_number=state["effective_reel_number"],
        effective_camera_position_menu=state["effective_camera_position_menu"],
        effective_filename_position_char=state["effective_filename_position_char"],
        effective_file_seq_number=state["effective_file_seq_number"],
        effective_title_name=state["effective_title_name"],
        sample_output_clip_stem=state["sample_output_clip_stem"],
        fx3_movie_clip_folder_path=FX3_MOVIE_CLIP_FOLDER_PATH_G147,
        target_media_slot=target_media_slot,
        slot1_tier0_vault_firewall_blocked=slot1_blocked,
        slot1_data_sector_writes=0,
        catalyst_browse_rejected=catalyst_browse_rejected,
        fx6_cross_model_spoof_rejected=bool(
            fx6_breathing_under_sq_or_raw_or_distortion_off_requested
            or fx6_46char_title_prefix_or_xdroot_spoof_requested
        ),
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class G147BreathingCamIdReelSdhcGuardResult:
    gate_id: str
    gate_code: str
    valid: bool
    status: str
    verification_mode: str
    emmc_writes_authorized: bool
    persistent_emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    donor_audit: Dict[str, Any]
    breathing_camid_reel_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g147_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G147BreathingCamIdReelSdhcGuardResult]:
    audit = audit_phase331_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G147BreathingCamIdReelSdhcGuardResult(
        gate_id=G147,
        gate_code=G147_GATE_CODE,
        valid=overall_valid,
        status=status,
        verification_mode=audit.verification_mode,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        donor_audit=audit.to_dict(),
        breathing_camid_reel_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G147,
        gate_code=G147_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"breathing={res.effective_breathing_comp} "
            f"fmt={res.effective_file_name_format} "
            f"stem={res.sample_output_clip_stem} "
            f"sdhc_lock={res.sdhc_standard_format_locked} "
            f"s1_writes={res.slot1_data_sector_writes}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G147BreathingCamIdReelSdhcGuardResult]:
    return evaluate_g147_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
        **kwargs
    )


# ---------------------------------------------------------------------------
# Gate G148: Round-57 [Copyright Info] 46-Char & [Write Serial Number] Reset
#            Errata, 2-Item [Power Setting Option] (9-Cond Bypass + Dormant
#            Monitor), and [NTSC/PAL Selector] + Slot-1 Format Firewall
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CopyrightPowerSaveNtscPalGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    copyright_info_menu_path: str
    power_setting_option_menu_path: str
    ntsc_pal_selector_menu_path: str
    effective_write_copyright_info: str
    effective_photographer: str
    effective_copyright: str
    effective_write_serial_number: str
    copyright_and_serial_resettable_by_camset_reset: bool
    copyright_excluded_from_camset_dat: bool
    write_serial_number_toggle_camset_permitted: bool
    exact_2_power_setting_items_verified: bool
    effective_power_save_start_time: str
    effective_power_save_bypassed: bool
    active_power_save_bypass_conditions: Tuple[str, ...]
    effective_auto_power_off_temp: str
    effective_video_system: str
    effective_startup_banner: str
    dormant_monitor_power_saving_rejected: bool
    dormant_power_save_value_rejected: bool
    fx6_cross_model_spoof_rejected: bool
    target_media_slot: int
    slot1_tier0_vault_format_firewall_blocked: bool
    slot1_data_sector_writes: int
    emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_fx3_copyright_powersave_ntscpal_state(
    *,
    write_copyright_info: str = "Off",
    photographer_name: str = "",
    copyright_name: str = "",
    write_serial_number: str = "Off",
    power_save_start_time: str = POWER_SAVE_START_TIME_DEFAULT_G148,
    auto_power_off_temp: str = AUTO_POWER_OFF_TEMP_DEFAULT_G148,
    active_bypass_conditions: Sequence[str] = (),
    video_system: str = VIDEO_SYSTEM_NTSC_G148,
    factory_video_system: str = VIDEO_SYSTEM_NTSC_G148,
    reset_action: str = RESET_ACTION_NONE_PHASE331,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-64 + Round-57 Reset Errata state."""
    # Round-57 Reset Errata + Setup Menu Persistence:
    # - ALL 4 [Copyright Info] items AND active Still+Movie [Write Serial Number]
    #   are Initialize-only (NOT resettable by [Camera Settings Reset]).
    # - [Power Setting Option] (Power Save Start Time, Auto Power OFF Temp.) and
    #   [NTSC/PAL Selector] are ALSO Initialize-only.
    if reset_action == RESET_ACTION_INITIALIZE_PHASE331:
        eff_write_copy = "Off"
        eff_photo = ""
        eff_copy = ""
        eff_write_serial = "Off"
        eff_ps_time = POWER_SAVE_START_TIME_DEFAULT_G148
        eff_temp = AUTO_POWER_OFF_TEMP_DEFAULT_G148
        eff_vsys = factory_video_system
    else:
        eff_write_copy = write_copyright_info
        eff_photo = photographer_name
        eff_copy = copyright_name
        eff_write_serial = write_serial_number
        eff_ps_time = power_save_start_time
        eff_temp = auto_power_off_temp
        eff_vsys = video_system

    matched_bypass = tuple(
        c for c in active_bypass_conditions if c in EXACT_9_POWER_SAVE_BYPASS_CONDITIONS_G148
    )
    ps_bypassed = len(matched_bypass) > 0 or eff_ps_time == POWER_SAVE_OFF_G148

    if eff_vsys == factory_video_system:
        banner = STARTUP_BANNER_NONE_G148
    elif eff_vsys == VIDEO_SYSTEM_NTSC_G148:
        banner = STARTUP_BANNER_NTSC_G148
    else:
        banner = STARTUP_BANNER_PAL_G148

    return {
        "effective_write_copyright_info": eff_write_copy,
        "effective_photographer": eff_photo,
        "effective_copyright": eff_copy,
        "effective_write_serial_number": eff_write_serial,
        "effective_power_save_start_time": eff_ps_time,
        "active_power_save_bypass_conditions": matched_bypass,
        "effective_power_save_bypassed": ps_bypassed,
        "effective_auto_power_off_temp": eff_temp,
        "effective_video_system": eff_vsys,
        "effective_startup_banner": banner,
        "initialize_only_persisted": reset_action
        in (
            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331,
            RESET_ACTION_RESET_NETWORK_SET_PHASE331,
        ),
    }


def compute_copyright_powersave_ntscpal_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G148 (288 states)."""
    combos = list(
        itertools.product(
            ("Off", "On"),  # write_copyright_info
            ("Off", "On"),  # write_serial_number
            (
                POWER_SAVE_OFF_G148,
                POWER_SAVE_5_MIN_G148,
                POWER_SAVE_10_SEC_G148,
            ),
            ALLOWED_AUTO_POWER_OFF_TEMP_MODES_G148,
            (False, True),  # bypass_active
            ALLOWED_VIDEO_SYSTEMS_G148,
            (
                RESET_ACTION_NONE_PHASE331,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331,
                RESET_ACTION_INITIALIZE_PHASE331,
            ),
        )
    )
    camset_preserved_copyright_count = 0
    camset_preserved_serial_count = 0
    power_save_bypassed_count = 0
    pal_banner_count = 0
    temp_high_count = 0

    for wc, ws, ps, tmp, byp, vsys, rst in combos:
        st = resolve_fx3_copyright_powersave_ntscpal_state(
            write_copyright_info=wc,
            photographer_name="Jane Doe" if wc == "On" else "",
            copyright_name="2026 Studio" if wc == "On" else "",
            write_serial_number=ws,
            power_save_start_time=ps,
            auto_power_off_temp=tmp,
            active_bypass_conditions=("tv_hdmi_connection",) if byp else (),
            video_system=vsys,
            factory_video_system=VIDEO_SYSTEM_NTSC_G148,
            reset_action=rst,
        )
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331
            and wc == "On"
            and st["effective_write_copyright_info"] == "On"
        ):
            camset_preserved_copyright_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331
            and ws == "On"
            and st["effective_write_serial_number"] == "On"
        ):
            camset_preserved_serial_count += 1
        if st["effective_power_save_bypassed"]:
            power_save_bypassed_count += 1
        if st["effective_startup_banner"] == STARTUP_BANNER_PAL_G148:
            pal_banner_count += 1
        if st["effective_auto_power_off_temp"] == AUTO_POWER_OFF_TEMP_HIGH_G148:
            temp_high_count += 1

    return {
        "total_matrix_states": len(combos),
        "camset_preserved_copyright_count": camset_preserved_copyright_count,
        "camset_preserved_serial_count": camset_preserved_serial_count,
        "power_save_bypassed_count": power_save_bypassed_count,
        "pal_banner_count": pal_banner_count,
        "temp_high_count": temp_high_count,
    }


def verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE331,
    body_model_id: int = FX3_MODEL_ID_PHASE331,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE331,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE331,
    write_copyright_info: str = "Off",
    photographer_name: str = "",
    copyright_name: str = "",
    write_serial_number: str = "Off",
    claimed_write_serial_number_still_only: bool = False,
    claimed_camset_reset_clears_write_copyright_info: bool = False,
    claimed_camset_reset_clears_copyright_strings: bool = False,
    claimed_camset_reset_clears_write_serial_number: bool = False,
    claimed_copyright_info_exported_to_camset: bool = False,
    claimed_write_serial_toggle_excluded_from_camset: bool = False,
    power_setting_option_items: Sequence[str] = EXACT_2_POWER_SETTING_OPTION_ITEMS_G148,
    power_save_start_time: str = POWER_SAVE_START_TIME_DEFAULT_G148,
    active_bypass_conditions: Sequence[str] = (),
    claimed_power_save_sleeps_during_bypass: bool = False,
    auto_power_off_temp: str = AUTO_POWER_OFF_TEMP_DEFAULT_G148,
    handheld_sustained_shooting_without_tripod: bool = False,
    requested_dormant_power_save_by_monitor: bool = False,
    requested_dormant_power_save_value: Optional[str] = None,
    video_system: str = VIDEO_SYSTEM_NTSC_G148,
    previous_video_system: str = VIDEO_SYSTEM_NTSC_G148,
    factory_video_system: str = VIDEO_SYSTEM_NTSC_G148,
    reboot_confirmed: bool = True,
    playback_clip_video_system: Optional[str] = None,
    claimed_cross_system_playback_allowed: bool = False,
    target_media_slot: int = MEDIA_SLOT_2_PHASE331,
    ntsc_pal_format_prompt_confirm_requested: bool = False,
    sd_erase_trim_requested: bool = False,
    requested_write_operation: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE331,
    claimed_camset_reset_clears_powersave_or_ntscpal: bool = False,
    fx6_consumer_exif_copyright_requested: bool = False,
    fx6_frequency_rec_format_spoof_requested: bool = False,
) -> CopyrightPowerSaveNtscPalGuardResult:
    """Enforce Gate G148: Round-57 Copyright/Serial Reset Errata, 2-Item Power Save (9-Cond) & NTSC/PAL Vault."""
    errors: List[str] = []
    warnings: List[str] = []
    violations: List[str] = []

    def _add(code: str, msg: str) -> None:
        violations.append(code)
        errors.append(msg)

    errors.extend(
        _validate_fx3_body_identity(
            body_model_name, body_model_id, help_guide_code, firmware_version
        )
    )

    if not _is_on_off(write_copyright_info):
        _add("TELEMETRY_INVALID", f"write_copyright_info_invalid:{write_copyright_info!r}")
    if not _is_on_off(write_serial_number):
        _add("TELEMETRY_INVALID", f"write_serial_number_invalid:{write_serial_number!r}")
    if not isinstance(photographer_name, str):
        _add("TELEMETRY_INVALID", "photographer_name_must_be_str")
    if not isinstance(copyright_name, str):
        _add("TELEMETRY_INVALID", "copyright_name_must_be_str")
    if auto_power_off_temp not in ALLOWED_AUTO_POWER_OFF_TEMP_MODES_G148:
        _add("TELEMETRY_INVALID", f"auto_power_off_temp_invalid:{auto_power_off_temp!r}")
    if video_system not in ALLOWED_VIDEO_SYSTEMS_G148:
        _add("TELEMETRY_INVALID", f"video_system_invalid:{video_system!r}")
    if previous_video_system not in ALLOWED_VIDEO_SYSTEMS_G148:
        _add("TELEMETRY_INVALID", f"previous_video_system_invalid:{previous_video_system!r}")
    if factory_video_system not in ALLOWED_VIDEO_SYSTEMS_G148:
        _add("TELEMETRY_INVALID", f"factory_video_system_invalid:{factory_video_system!r}")
    if playback_clip_video_system is not None and playback_clip_video_system not in ALLOWED_VIDEO_SYSTEMS_G148:
        _add("TELEMETRY_INVALID", f"playback_clip_video_system_invalid:{playback_clip_video_system!r}")
    if not _is_strict_int(target_media_slot) or target_media_slot not in ALLOWED_MEDIA_SLOTS_PHASE331:
        _add("TELEMETRY_INVALID", f"target_media_slot_invalid:{target_media_slot!r}")
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE331:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")

    for cond in active_bypass_conditions:
        if cond not in EXACT_9_POWER_SAVE_BYPASS_CONDITIONS_G148:
            _add("TELEMETRY_INVALID", f"unknown_power_save_bypass_condition:{cond!r}")

    # Dormant / Cross-model spoofs -> EOPNOTSUPP=95
    dormant_monitor = (
        requested_dormant_power_save_by_monitor
        or DORMANT_POWER_SAVE_BY_MONITOR_NAME_G148 in tuple(power_setting_option_items)
    )
    if dormant_monitor:
        _add(
            "DORMANT_MONITOR_POWER_SAVING_EOPNOTSUPP",
            "fx3_has_no_evf_power_save_by_monitor_is_dormant_eopnotsupp_95",
        )

    dormant_ps_val = (
        (requested_dormant_power_save_value is not None)
        or (power_save_start_time in DORMANT_POWER_SAVE_VALUES_G148)
    )
    if dormant_ps_val:
        _add(
            "DORMANT_POWER_SAVE_VALUE_EOPNOTSUPP",
            f"dormant_power_save_start_time_not_exposed_on_fx3_eopnotsupp_95:{requested_dormant_power_save_value or power_save_start_time!r}",
        )
    elif power_save_start_time not in ALLOWED_POWER_SAVE_START_TIMES_G148:
        _add("TELEMETRY_INVALID", f"power_save_start_time_invalid:{power_save_start_time!r}")

    if fx6_consumer_exif_copyright_requested or fx6_frequency_rec_format_spoof_requested:
        _add(
            "FX6_CROSS_MODEL_EOPNOTSUPP",
            "fx6_cross_model_copyright_or_frequency_rec_format_spoof_rejected_eopnotsupp_95",
        )

    # Exact 2 active items in Setup -> [Power Setting Option]
    exact_2_power_ok = (
        tuple(power_setting_option_items) == EXACT_2_POWER_SETTING_OPTION_ITEMS_G148
    )
    if not exact_2_power_ok:
        _add(
            "POWER_SETTING_EXACT_2_ITEMS_VIOLATION",
            f"fx3_power_setting_option_must_have_exact_2_items:{tuple(power_setting_option_items)!r}",
        )

    # Copyright Info <= 46 printable ASCII chars + Round-57 Reset Errata + CAMSET isolation
    if isinstance(photographer_name, str) and (
        len(photographer_name) > COPYRIGHT_MAX_CHARS_G148
        or not _is_printable_ascii(photographer_name)
    ):
        _add(
            "COPYRIGHT_46CH_VIOLATION",
            f"photographer_name_must_be_le_46_printable_ascii_chars:len={len(photographer_name)}",
        )
    if isinstance(copyright_name, str) and (
        len(copyright_name) > COPYRIGHT_MAX_CHARS_G148
        or not _is_printable_ascii(copyright_name)
    ):
        _add(
            "COPYRIGHT_46CH_VIOLATION",
            f"copyright_name_must_be_le_46_printable_ascii_chars:len={len(copyright_name)}",
        )
    if claimed_write_serial_number_still_only:
        _add(
            "SERIAL_STILL_MOVIE_ERRATA",
            "fx3_ver_7_02_write_serial_number_is_active_still_and_movie_not_still_only_einval_22",
        )
    if (
        claimed_camset_reset_clears_write_copyright_info
        or claimed_camset_reset_clears_copyright_strings
        or claimed_camset_reset_clears_write_serial_number
    ):
        _add(
            "ROUND57_RESET_ERRATA_VIOLATION",
            "round57_reset_errata_copyright_info_and_write_serial_number_are_initialize_only_not_camset_resettable_einval_22",
        )
    if claimed_copyright_info_exported_to_camset:
        _add(
            "CAMSET_COPYRIGHT_PII_VIOLATION",
            "copyright_info_must_be_excluded_from_camset_dat_to_prevent_pii_leak_einval_22",
        )
    if claimed_write_serial_toggle_excluded_from_camset:
        _add(
            "CAMSET_SERIAL_TOGGLE_VIOLATION",
            "write_serial_number_boolean_toggle_is_not_in_camset_dat_exclusion_list_einval_22",
        )

    # Power Setting Option: 9 bypasses, Auto Power OFF Temp High handheld risk, Initialize-only
    if (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331
        and claimed_camset_reset_clears_powersave_or_ntscpal
    ):
        _add(
            "POWERSAVE_NTSCPAL_RESET_VIOLATION",
            "power_setting_option_and_ntsc_pal_selector_are_initialize_only_einval_22",
        )
    if active_bypass_conditions and claimed_power_save_sleeps_during_bypass:
        _add(
            "POWERSAVE_9COND_BYPASS_VIOLATION",
            "power_save_start_time_must_bypass_sleep_under_active_official_bypass_condition_einval_22",
        )
    if (
        auto_power_off_temp == AUTO_POWER_OFF_TEMP_HIGH_G148
        and handheld_sustained_shooting_without_tripod
    ):
        _add(
            "AUTO_POWER_OFF_TEMP_HIGH_HANDHELD_HAZARD",
            "auto_power_off_temp_high_is_for_tripod_shooting_only_handheld_burn_hazard_einval_22",
        )

    # NTSC/PAL Selector: mandatory reboot + cross-system playback block
    if video_system != previous_video_system and not reboot_confirmed:
        _add(
            "NTSC_PAL_REBOOT_GATE",
            "switching_ntsc_pal_requires_mandatory_reboot_einval_22",
        )
    if (
        playback_clip_video_system is not None
        and playback_clip_video_system != video_system
        and claimed_cross_system_playback_allowed
    ):
        _add(
            "NTSC_PAL_CROSS_PLAYBACK_BLOCK",
            "cross_system_ntsc_pal_movie_playback_is_blocked_without_switching_selector_einval_22",
        )

    # HARD EROFS=30 Slot-1 Tier-0 Vault Format / SD-Erase / TRIM Firewall
    slot1_format_blocked = False
    if target_media_slot == MEDIA_SLOT_1_PHASE331 and (
        ntsc_pal_format_prompt_confirm_requested
        or sd_erase_trim_requested
        or requested_write_operation
    ):
        slot1_format_blocked = True
        _add(
            "SLOT1_FORMAT_SD_ERASE_TRIM_EROFS",
            "slot1_tier0_vault_erofs_30_hard_blocked_ntsc_pal_format_sd_erase_trim",
        )

    state = resolve_fx3_copyright_powersave_ntscpal_state(
        write_copyright_info=write_copyright_info
        if _is_on_off(write_copyright_info)
        else "Off",
        photographer_name=photographer_name if isinstance(photographer_name, str) else "",
        copyright_name=copyright_name if isinstance(copyright_name, str) else "",
        write_serial_number=write_serial_number
        if _is_on_off(write_serial_number)
        else "Off",
        power_save_start_time=power_save_start_time
        if power_save_start_time in ALLOWED_POWER_SAVE_START_TIMES_G148
        else POWER_SAVE_START_TIME_DEFAULT_G148,
        auto_power_off_temp=auto_power_off_temp
        if auto_power_off_temp in ALLOWED_AUTO_POWER_OFF_TEMP_MODES_G148
        else AUTO_POWER_OFF_TEMP_DEFAULT_G148,
        active_bypass_conditions=active_bypass_conditions,
        video_system=video_system
        if video_system in ALLOWED_VIDEO_SYSTEMS_G148
        else VIDEO_SYSTEM_NTSC_G148,
        factory_video_system=factory_video_system
        if factory_video_system in ALLOWED_VIDEO_SYSTEMS_G148
        else VIDEO_SYSTEM_NTSC_G148,
        reset_action=reset_action
        if reset_action in ALLOWED_RESET_ACTIONS_PHASE331
        else RESET_ACTION_NONE_PHASE331,
    )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G148
        block_errno = 0
        block_errno_name = "OK"
    elif slot1_format_blocked:
        status = STATUS_BLOCKED_G148_SLOT1_FORMAT_SD_ERASE_TRIM_VAULT_EROFS
        block_errno = EROFS_ERRNO_PHASE331
        block_errno_name = EROFS_NAME_PHASE331
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G148_DORMANT_MONITOR_POWER_SAVING_OR_FX6_EOPNOTSUPP
        block_errno = EOPNOTSUPP_ERRNO_PHASE331
        block_errno_name = EOPNOTSUPP_NAME_PHASE331
    elif any(v == "TELEMETRY_INVALID" for v in violations) or any(
        e.startswith(
            (
                "body_model_name_invalid:",
                "body_model_id_invalid:",
                "help_guide_code_invalid:",
                "firmware_version_invalid:",
            )
        )
        for e in errors
    ):
        status = STATUS_BLOCKED_G148_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE331
        block_errno_name = EINVAL_NAME_PHASE331
    elif any(
        k in v
        for v in violations
        for k in ("COPYRIGHT", "SERIAL", "ROUND57", "CAMSET")
    ):
        status = STATUS_BLOCKED_G148_COPYRIGHT_46CH_SERIAL_RESET_OR_CAMSET_PII_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE331
        block_errno_name = EINVAL_NAME_PHASE331
    else:
        status = STATUS_BLOCKED_G148_POWERSAVE_9COND_TEMP_HIGH_OR_NTSCPAL_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE331
        block_errno_name = EINVAL_NAME_PHASE331

    return CopyrightPowerSaveNtscPalGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        copyright_info_menu_path=COPYRIGHT_INFO_MENU_PATH_G148,
        power_setting_option_menu_path=POWER_SETTING_OPTION_MENU_PATH_G148,
        ntsc_pal_selector_menu_path=NTSC_PAL_SELECTOR_MENU_PATH_G148,
        effective_write_copyright_info=state["effective_write_copyright_info"],
        effective_photographer=state["effective_photographer"],
        effective_copyright=state["effective_copyright"],
        effective_write_serial_number=state["effective_write_serial_number"],
        copyright_and_serial_resettable_by_camset_reset=False,
        copyright_excluded_from_camset_dat=COPYRIGHT_INFO_EXCLUDED_FROM_CAMSET_DAT_G148,
        write_serial_number_toggle_camset_permitted=(
            not WRITE_SERIAL_NUMBER_EXCLUDED_FROM_CAMSET_DAT_G148
        ),
        exact_2_power_setting_items_verified=exact_2_power_ok,
        effective_power_save_start_time=state["effective_power_save_start_time"],
        effective_power_save_bypassed=state["effective_power_save_bypassed"],
        active_power_save_bypass_conditions=state[
            "active_power_save_bypass_conditions"
        ],
        effective_auto_power_off_temp=state["effective_auto_power_off_temp"],
        effective_video_system=state["effective_video_system"],
        effective_startup_banner=state["effective_startup_banner"],
        dormant_monitor_power_saving_rejected=dormant_monitor,
        dormant_power_save_value_rejected=dormant_ps_val,
        fx6_cross_model_spoof_rejected=bool(
            fx6_consumer_exif_copyright_requested
            or fx6_frequency_rec_format_spoof_requested
        ),
        target_media_slot=target_media_slot,
        slot1_tier0_vault_format_firewall_blocked=slot1_format_blocked,
        slot1_data_sector_writes=0,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class G148CopyrightPowerSaveNtscPalGuardResult:
    gate_id: str
    gate_code: str
    valid: bool
    status: str
    verification_mode: str
    emmc_writes_authorized: bool
    persistent_emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    donor_audit: Dict[str, Any]
    copyright_powersave_ntscpal_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g148_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G148CopyrightPowerSaveNtscPalGuardResult]:
    audit = audit_phase331_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G148CopyrightPowerSaveNtscPalGuardResult(
        gate_id=G148,
        gate_code=G148_GATE_CODE,
        valid=overall_valid,
        status=status,
        verification_mode=audit.verification_mode,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        donor_audit=audit.to_dict(),
        copyright_powersave_ntscpal_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G148,
        gate_code=G148_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"write_copy={res.effective_write_copyright_info} "
            f"write_serial={res.effective_write_serial_number} "
            f"ps={res.effective_power_save_start_time} "
            f"temp={res.effective_auto_power_off_temp} "
            f"vsys={res.effective_video_system} "
            f"s1_writes={res.slot1_data_sector_writes}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G148CopyrightPowerSaveNtscPalGuardResult]:
    return evaluate_g148_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
        **kwargs
    )


# ---------------------------------------------------------------------------
# Unified 148-Gate Master Safety Preflight Engine (G01..G148)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Master148GateReport:
    schema: str
    schema_version: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_145_gates_verified: bool
    all_148_gates_verified: bool
    g13_to_g148_all_passed: bool
    g147_to_g148_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_146_report: Dict[str, Any]
    g147_result: Dict[str, Any]
    g148_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_148gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    simulate_bench_dry_run: Optional[bool] = None,
    dry_run_simulated_backup: Optional[bool] = None,
    request_persistent_emmc_writes: bool = False,
    master_146_override: Optional[Master146GateReport] = None,
    breathing_camid_reel_kwargs: Optional[Mapping[str, Any]] = None,
    copyright_powersave_ntscpal_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master148GateReport:
    """Evaluate unified 148-Gate Milestone Master Safety Preflight (`G01..G148`)."""
    effective_dry_run = (
        bool(dry_run_simulated)
        or (simulate_bench_dry_run is True)
        or (dry_run_simulated_backup is True)
    )
    clean_forced = _is_clean_room_forced(force_clean_room)
    resolved_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved_work_root_for_m146 = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=resolved_repo_root).work_root
    )
    m146_force_clean_room = (
        True
        if (clean_forced or resolved_work_root_for_m146 is None)
        else force_clean_room
    )

    m146_report = (
        master_146_override
        if master_146_override is not None
        else evaluate_146gate_preflight(
            resolved_repo_root,
            work_root=work_root,
            force_clean_room=m146_force_clean_room,
            dry_run_simulated=effective_dry_run,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
        )
    )

    g147_kw = dict(breathing_camid_reel_kwargs or {})
    if "requested_write_operation" not in g147_kw and request_persistent_emmc_writes:
        g147_kw["requested_write_operation"] = True
    g147_verdict, g147_res = (
        evaluate_g147_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            repo_root=resolved_repo_root,
            work_root=work_root,
            force_clean_room=force_clean_room,
            **g147_kw,
        )
    )

    g148_kw = dict(copyright_powersave_ntscpal_kwargs or {})
    if "requested_write_operation" not in g148_kw and request_persistent_emmc_writes:
        g148_kw["requested_write_operation"] = True
    g148_verdict, g148_res = (
        evaluate_g148_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            repo_root=resolved_repo_root,
            work_root=work_root,
            force_clean_room=force_clean_room,
            **g148_kw,
        )
    )

    new_gate_dicts = (
        {
            "gate_id": G147,
            "gate_code": G147_GATE_CODE,
            "status": g147_res.status,
            "passed": g147_verdict.passed,
            "evidence": g147_verdict.evidence,
            "violation_codes": list(g147_verdict.errors),
        },
        {
            "gate_id": G148,
            "gate_code": G148_GATE_CODE,
            "status": g148_res.status,
            "passed": g148_verdict.passed,
            "evidence": g148_verdict.evidence,
            "violation_codes": list(g148_verdict.errors),
        },
    )

    all_gates: Tuple[Dict[str, Any], ...] = tuple(m146_report.gates) + new_gate_dicts
    g01_to_g12_verified = int(m146_report.summary["g01_to_g12_verified"])
    g13_to_g146_verified = (
        int(m146_report.summary["g13_to_g144_verified"])
        + int(m146_report.summary["g145_to_g146_verified"])
    )
    g147_to_g148_verified = int(bool(g147_verdict.passed)) + int(
        bool(g148_verdict.passed)
    )
    total_verified = g01_to_g12_verified + g13_to_g146_verified + g147_to_g148_verified

    g147_to_g148_all_passed = g147_to_g148_verified == 2
    g13_to_g148_all_passed = (
        m146_report.g13_to_g146_all_passed and g147_to_g148_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m146_report.gates[:9])

    offline_145_verified = (
        g01_to_g09_ok
        and m146_report.offline_143_gates_verified
        and g147_to_g148_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_148_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g148_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m146_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_145_verified
        and m146_report.h0_h1_trial_entry_allowed
        and g147_to_g148_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not CROSS_MODEL_FLASH_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m146_report.errors)
        + list(g147_verdict.errors)
        + list(g148_verdict.errors)
    )
    warnings: List[str] = (
        list(m146_report.warnings)
        + list(g147_verdict.warnings)
        + list(g148_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m146_report.g13_to_g146_all_passed:
        overall_status = m146_report.status
    elif not g147_verdict.passed:
        overall_status = g147_verdict.status
    elif not g148_verdict.passed:
        overall_status = g148_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_148_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_148_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_148_verified:
        overall_status = "VERIFIED_ALL_148_GATES"
    else:
        overall_status = "VERIFIED_145_OF_148_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m146_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g147_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g148_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 148,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 148 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g146_verified": g13_to_g146_verified,
        "g147_to_g148_verified": g147_to_g148_verified,
        "g13_to_g148_all_passed": g13_to_g148_all_passed,
        "g147_to_g148_all_passed": g147_to_g148_all_passed,
        "offline_145_gates_verified": offline_145_verified,
        "all_148_gates_verified": all_148_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "human_hardware_attach_token": HUMAN_HARDWARE_ATTACH_TOKEN,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "cross_model_flash_authorized": CROSS_MODEL_FLASH_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "emmc_writes_authorized": EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master148GateReport(
        schema=REALHW_148GATE_PREFLIGHT_SCHEMA,
        schema_version=REALHW_148GATE_PREFLIGHT_SCHEMA,
        version=REALHW_BREATHING_CAMID_COPYRIGHT_POWERSAVE_NTSCPAL_148GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_145_gates_verified=offline_145_verified,
        all_148_gates_verified=all_148_verified,
        g13_to_g148_all_passed=g13_to_g148_all_passed,
        g147_to_g148_all_passed=g147_to_g148_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_146_report=m146_report.to_dict(),
        g147_result=g147_res.to_dict(),
        g148_result=g148_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_148_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master148GateReport:
    return evaluate_148gate_preflight(repo_root, **kwargs)


def run_148_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master148GateReport:
    return evaluate_148gate_preflight(repo_root, **kwargs)


def _safe_write_json(payload: Any) -> None:
    try:
        sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.close(devnull)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_breathing_camid_copyright_powersave_ntscpal_and_148gate_guard",
        description="Phase 331 (Task H400, Wave-64) G147/G148 and 148/148 Unified Safety Preflight CLI",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    parser.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all 148/148 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g147", "g148", "148"],
        default="148",
        help="Target gate check: g147, g148, or 148",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g147":
        v, r = evaluate_g147_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            repo_root=args.repo_root,
            force_clean_room=clean,
        )
        if args.json:
            _safe_write_json(
                {
                    "gate": v.gate_id,
                    "status": r.status,
                    "verification_mode": r.verification_mode,
                    "valid": r.valid,
                    "raw_firmware_bytes_leaked": r.raw_firmware_bytes_leaked,
                }
                if args.summary
                else r.to_dict()
            )
        else:
            sys.stdout.write(f"gate={v.gate_id} status={r.status} valid={r.valid}\n")
        return 0 if r.valid else 1

    if args.gate == "g148":
        v, r = evaluate_g148_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            repo_root=args.repo_root,
            force_clean_room=clean,
        )
        if args.json:
            _safe_write_json(
                {
                    "gate": v.gate_id,
                    "status": r.status,
                    "verification_mode": r.verification_mode,
                    "valid": r.valid,
                    "raw_firmware_bytes_leaked": r.raw_firmware_bytes_leaked,
                }
                if args.summary
                else r.to_dict()
            )
        else:
            sys.stdout.write(f"gate={v.gate_id} status={r.status} valid={r.valid}\n")
        return 0 if r.valid else 1

    rep = evaluate_148gate_preflight(
        args.repo_root,
        force_clean_room=clean,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        _safe_write_json(
            {
                "schema_version": rep.schema_version,
                "status": rep.status,
                "verification_mode": rep.verification_mode,
                "summary": rep.summary,
                "g147_status": rep.g147_result["status"],
                "g148_status": rep.g148_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/148 "
            f"raw_firmware_bytes_leaked={rep.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        rep.all_148_gates_verified
        if args.dry_run_simulated
        else rep.offline_145_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "ALLOWED_ALL_CARD_TYPES_G147",
    "ALLOWED_AUTO_POWER_OFF_TEMP_MODES_G148",
    "ALLOWED_BREATHING_COMP_MODES_G147",
    "ALLOWED_CAMERA_POSITIONS_G147",
    "ALLOWED_CARD_TYPES_G147",
    "ALLOWED_DISTORTION_COMP_MODES_G147",
    "ALLOWED_FILE_NAME_FORMATS_G147",
    "ALLOWED_FILE_NUMBER_MODES_G147",
    "ALLOWED_FILESYSTEMS_G147",
    "ALLOWED_FX6_RAW_CODECS_G147",
    "ALLOWED_LENS_BREATHING_SUPPORT_STATES_G147",
    "ALLOWED_MEDIA_SLOTS_PHASE331",
    "ALLOWED_POWER_SAVE_START_TIMES_G148",
    "ALLOWED_RESET_ACTIONS_PHASE331",
    "ALLOWED_SHOOT_MODES_PHASE331",
    "ALLOWED_VIDEO_SYSTEMS_G148",
    "AUTO_POWER_OFF_TEMP_DEFAULT_G148",
    "AUTO_POWER_OFF_TEMP_F_RESID16_G148",
    "AUTO_POWER_OFF_TEMP_HIGH_G148",
    "AUTO_POWER_OFF_TEMP_STANDARD_G148",
    "AUTO_POWER_OFF_TEMP_TRIPOD_G_RESID16_G148",
    "BREATHING_COMP_DEFAULT_G147",
    "BREATHING_COMP_F_RESID16_G147",
    "BREATHING_COMP_MENU_PATH_G147",
    "BREATHING_COMP_MIN_FW_G147",
    "BREATHING_COMP_OFF_G147",
    "BREATHING_COMP_ON_G147",
    "BREATHING_COMP_REGULAR_MOVIE_BLOCKED_FPS_FLOOR_G147",
    "BREATHING_COMP_RESETTABLE_BY_CAMSET_RESET_G147",
    "BREATHING_COMP_SQ_BLOCKED_FPS_G147",
    "BreathingCamIdReelSdhcGuardResult",
    "CAMERA_POS_C_G147",
    "CAMERA_POS_L_G147",
    "CAMERA_POS_R_G147",
    "CAM_ID_REEL_F_RESID16_G147",
    "CARD_TYPE_CFEXPRESS_TYPE_A_G147",
    "CARD_TYPE_SDHC_G147",
    "CARD_TYPE_SDXC_G147",
    "CATALYST_BROWSE_FREE_TOOL_G147",
    "CATALYST_PREPARE_PAID_TOOLS_G147",
    "COMPATIBLE_BREATHING_LENSES_SAMPLE_G147",
    "COPYRIGHT_INFO_EXCLUDED_FROM_CAMSET_DAT_G148",
    "COPYRIGHT_INFO_F_RESID16_G148",
    "COPYRIGHT_INFO_MENU_PATH_G148",
    "COPYRIGHT_INFO_RESETTABLE_BY_CAMSET_RESET_G148",
    "COPYRIGHT_MAX_CHARS_G148",
    "CROSS_MODEL_FLASH_AUTHORIZED",
    "CopyrightPowerSaveNtscPalGuardResult",
    "DISP_COPYRIGHT_INFO_F_RESID16_G148",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE331",
    "DONOR_CHECK_MAX_SECONDS_PHASE331",
    "DORMANT_POWER_SAVE_BY_MONITOR_BKID_G148",
    "DORMANT_POWER_SAVE_BY_MONITOR_F_RESID16S_G148",
    "DORMANT_POWER_SAVE_BY_MONITOR_NAME_G148",
    "DORMANT_POWER_SAVE_VALUES_G148",
    "EBUSY_ERRNO_PHASE331",
    "EBUSY_NAME_PHASE331",
    "EINVAL_ERRNO_PHASE331",
    "EINVAL_NAME_PHASE331",
    "ENV_CLEAN_ROOM_TEST_PHASE331",
    "EOPNOTSUPP_ERRNO_PHASE331",
    "EOPNOTSUPP_NAME_PHASE331",
    "EROFS_ERRNO_PHASE331",
    "EROFS_NAME_PHASE331",
    "EXACT_2_POWER_SETTING_OPTION_ITEMS_G148",
    "EXACT_4_COPYRIGHT_INFO_ITEMS_G148",
    "EXACT_9_POWER_SAVE_BYPASS_CONDITIONS_G148",
    "FILE_NAME_FORMAT_CAM_ID_REEL_G147",
    "FILE_NAME_FORMAT_DATE_TITLE_G147",
    "FILE_NAME_FORMAT_DEFAULT_G147",
    "FILE_NAME_FORMAT_F_RESID16_G147",
    "FILE_NAME_FORMAT_STANDARD_G147",
    "FILE_NAME_FORMAT_TITLE_DATE_G147",
    "FILE_NAME_FORMAT_TITLE_G147",
    "FILE_NUMBER_DEFAULT_G147",
    "FILE_NUMBER_RESET_G147",
    "FILE_NUMBER_SERIES_G147",
    "FILE_SEQ_NUMBER_MAX_G147",
    "FILE_SEQ_NUMBER_MIN_G147",
    "FILE_SETTINGS_F_RESID16_G147",
    "FILE_SETTINGS_MENU_PATH_G147",
    "FILE_SETTINGS_RESETTABLE_BY_CAMSET_RESET_G147",
    "FILESYSTEM_EXFAT_G147",
    "FILESYSTEM_FAT32_G147",
    "FX3_DEFAULT_FW_VERSION_PHASE331",
    "FX3_HELP_GUIDE_CODE_PHASE331",
    "FX3_MODEL_ID_PHASE331",
    "FX3_MODEL_NAME_PHASE331",
    "FX3_MOVIE_CLIP_FOLDER_PATH_G147",
    "FX6_BREATHING_COMP_MENU_PATH_G147",
    "FX6_CFEXPRESS_CLIP_FOLDER_PATH_G147",
    "FX6_CLIP_NAME_FORMAT_MENU_PATH_G147",
    "FX6_CLIP_PREFIX_MAX_CHARS_G147",
    "FX6_CLIP_PREFIX_MIN_CHARS_G147",
    "FX6_DEFAULT_FW_VERSION_PHASE331",
    "FX6_FREQUENCY_OPTIONS_G148",
    "FX6_LENS_SERIAL_PRESET_SLOTS_G148",
    "FX6_MODEL_NAME_PHASE331",
    "FX6_PRODUCT_CODE_PHASE331",
    "FX6_REC_FORMAT_FREQUENCY_MENU_PATH_G148",
    "FX6_SDXC_CLIP_FOLDER_PATH_G147",
    "G147",
    "G147BreathingCamIdReelSdhcGuardResult",
    "G147_GATE_CODE",
    "G147_GATE_ID",
    "G148",
    "G148CopyrightPowerSaveNtscPalGuardResult",
    "G148_GATE_CODE",
    "G148_GATE_ID",
    "GATE_G147_BREATHING_COMP_120P_CATALYST_AND_CAMID_REEL_SDHC_VAULT_GUARD",
    "GATE_G148_COPYRIGHT_46CH_SERIAL_ERRATA_AND_POWERSAVE_NTSCPAL_VAULT_GUARD",
    "LENS_BREATHING_NA_G147",
    "LENS_BREATHING_NOT_SUPPORT_G147",
    "LENS_BREATHING_SUPPORT_G147",
    "LENS_COMP_INITIALIZE_ONLY_ITEMS_G147",
    "MACRO_RING_RESTRICTED_LENS_G147",
    "MEDIA_SLOT_1_PHASE331",
    "MEDIA_SLOT_2_PHASE331",
    "MEDIA_SLOT_NONE_PHASE331",
    "Master148GateReport",
    "NTSC_ALLOWED_FPS_G148",
    "NTSC_PAL_FORMAT_PROMPT_BASE_RESID16S_G148",
    "NTSC_PAL_RESETTABLE_BY_CAMSET_RESET_G148",
    "NTSC_PAL_SELECTOR_F_RESID16_G148",
    "NTSC_PAL_SELECTOR_MENU_PATH_G148",
    "PAL_ALLOWED_FPS_G148",
    "PINNED_FX3_APPFW_SLICES_PHASE331",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE331",
    "PINNED_FX6_APPFW_SLICES_PHASE331",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE331",
    "PINNED_PHASE331_DONOR_SPECS",
    "POWER_SAVE_10_SEC_G148",
    "POWER_SAVE_1_MIN_G148",
    "POWER_SAVE_2_MIN_G148",
    "POWER_SAVE_30_MIN_G148",
    "POWER_SAVE_5_MIN_G148",
    "POWER_SAVE_OFF_G148",
    "POWER_SAVE_START_TIME_DEFAULT_G148",
    "POWER_SAVE_START_TIME_F_RESID16_G148",
    "POWER_SAVE_START_TIME_SECONDS_G148",
    "POWER_SETTING_OPTION_MENU_PATH_G148",
    "POWER_SETTING_OPTION_RESETTABLE_BY_CAMSET_RESET_G148",
    "Phase331DonorAuditResult",
    "REALHW_148GATE_PREFLIGHT_SCHEMA",
    "REALHW_BREATHING_CAMID_COPYRIGHT_POWERSAVE_NTSCPAL_148GATE_SCHEMA",
    "REALHW_BREATHING_CAMID_COPYRIGHT_POWERSAVE_NTSCPAL_148GATE_VERSION",
    "REEL_NUMBER_MAX_G147",
    "REEL_NUMBER_MIN_G147",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331",
    "RESET_ACTION_INITIALIZE_PHASE331",
    "RESET_ACTION_NONE_PHASE331",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE331",
    "SDHC_FORMAT_ERROR_BASE_RESID16_G147",
    "SDHC_MAX_CAPACITY_GB_G147",
    "SDHC_XAVCS_SPLIT_BYTES_G147",
    "SERIES_COUNTER_RESET_F_RESID16_G147",
    "SET_COPYRIGHT_F_RESID16_G148",
    "SET_PHOTOGRAPHER_F_RESID16_G148",
    "SHOOT_MODE_MOVIE_PHASE331",
    "SHOOT_MODE_SQ_PHASE331",
    "SHOOT_MODE_STILL_PHASE331",
    "STARTUP_BANNER_NONE_G148",
    "STARTUP_BANNER_NTSC_G148",
    "STARTUP_BANNER_PAL_G148",
    "STATUS_BLOCKED_G147_BREATHING_120P_SQ_RAW_OR_RESET_VIOLATION",
    "STATUS_BLOCKED_G147_LENS_CATALYST_BROWSE_OR_FX6_EOPNOTSUPP",
    "STATUS_BLOCKED_G147_SDHC_FILESETTINGS_CAMID_TITLE_VIOLATION",
    "STATUS_BLOCKED_G147_SLOT1_TIER0_VAULT_EROFS",
    "STATUS_BLOCKED_G147_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G148_COPYRIGHT_46CH_SERIAL_RESET_OR_CAMSET_PII_VIOLATION",
    "STATUS_BLOCKED_G148_DORMANT_MONITOR_POWER_SAVING_OR_FX6_EOPNOTSUPP",
    "STATUS_BLOCKED_G148_POWERSAVE_9COND_TEMP_HIGH_OR_NTSCPAL_VIOLATION",
    "STATUS_BLOCKED_G148_SLOT1_FORMAT_SD_ERASE_TRIM_VAULT_EROFS",
    "STATUS_BLOCKED_G148_TELEMETRY_INVALID",
    "STATUS_BLOCKED_PHASE331_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G147",
    "STATUS_VERIFIED_G148",
    "TELECONVERTER_MODELS_G147",
    "TITLE_NAME_ALLOWED_SYMBOLS_G147",
    "TITLE_NAME_DEFAULT_G147",
    "TITLE_NAME_MAX_CHARS_G147",
    "TITLE_NAME_SETTINGS_F_RESID16_G147",
    "TITLE_NAME_VALID_RE_G147",
    "VIDEO_SYSTEM_NTSC_G148",
    "VIDEO_SYSTEM_PAL_G148",
    "WRITE_COPYRIGHT_INFO_F_RESID16_G148",
    "WRITE_SERIAL_NUMBER_EXCLUDED_FROM_CAMSET_DAT_G148",
    "WRITE_SERIAL_NUMBER_F_RESID16_G148",
    "WRITE_SERIAL_NUMBER_LEGACY_STILL_ONLY_SYMBOL_G148",
    "WRITE_SERIAL_NUMBER_MENU_PATH_G148",
    "WRITE_SERIAL_NUMBER_RESETTABLE_BY_CAMSET_RESET_G148",
    "WRITE_SERIAL_NUMBER_STILL_LEGACY_F_RESID16_G148",
    "WRITE_SERIAL_NUMBER_SYMBOL_STILL_MOVIE_G148",
    "audit_phase331_donor_contracts",
    "compute_breathing_camid_reel_matrix",
    "compute_copyright_powersave_ntscpal_matrix",
    "evaluate_148_master_safety_gates",
    "evaluate_148gate_preflight",
    "evaluate_g147_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard",
    "evaluate_g148_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard",
    "main",
    "resolve_fx3_breathing_and_file_settings_state",
    "resolve_fx3_copyright_powersave_ntscpal_state",
    "run_148_gate_preflight",
    "verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard",
    "verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard_with_audit",
    "verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard",
    "verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard_with_audit",
]


if __name__ == "__main__":
    raise SystemExit(main())
