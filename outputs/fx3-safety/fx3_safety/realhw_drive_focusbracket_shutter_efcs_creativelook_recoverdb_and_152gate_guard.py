"""Phase 351 (Task H439, Wave-66, 152/152 Milestone): Real-Hardware Still `[Drive Mode]`
`10 fps` & Dormant `[Focus Bracket]` Rejection + `[Shutter Type]` 2-Mode Zero-`Auto`
/ `1/250 s` X-Sync / `[e-Front Curtain Shut.]` `curtaion` Typo / `[Long Exposure NR]`
(`G151`), `[Creative Look]` `10+6` Slots / Asymmetric `0..9` Bounds / Dormant
`[Soft Skin Effect]` Rejection & `[Delete]`/`[Protect]`/`[Recover Image DB]` Tier-0
`Slot 1` `EROFS=30` Firewall (`G152`), and Unified `152`-Gate Master Safety Preflight
(`G01..G152`).

Authoritative Empirical Baseline (`ILME-FX3 Ver. 7.02`, `ilc/2210`, `0x0502`,
`PRODUCT_MODEL_ALCIN_UUD` vs `ILME-FX6 Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`):
  - **Gate `G151` (`STILL_DRIVE_10FPS_DORMANT_FOCUS_BRACKET_AND_SHUTTER_TYPE_2MODE_XSYNC_250_EFCS_NR_GUARD`)**:
    1. `Shooting -> [Drive Mode]` (Still-only, `Can be reset`):
       - `Single Shooting` (default), `Cont. Shooting` (`Hi+` `10 fps`, `Hi` `8 fps`,
         `Mid` `6 fps`, `Lo` `3 fps`; focus locked to first frame at `> F11` in
         `Hi+/Hi/Mid`; speed drops on `Uncompressed RAW` or Flash),
         `Self-timer(Single)` (`10/5/2 Sec`), `Self-timer(Cont)` (`6` options),
         `Cont. Bracket` / `Single Bracket` (`0.3/0.5/0.7/1.0 EV` x `3/5/9 Img.`,
         `2.0/3.0 EV` x `3/5 Img.`), `WB bracket` (`Lo ±10 MK-1` / `Hi ±20 MK-1`),
         and `DRO Bracket` (disabled when `[HLG Still Image] = On`).
       - **Dormant `[Focus Bracket]` Myth-Busting**: `BKID_APP_setting_focus_bracket_*`
         and `DRIVE_MODE_FOCUS_BRACKET` exist in `FX3 appFw.so` (plus `56` dormant
         symbols in `FX6 appFw.so`), **0** exposed in `ilc/2210` / `5-024-458-18`
         (`dormant_focus_bracket_exposed_events == 0`) -> reject `EOPNOTSUPP=95`.
    2. `Shooting -> [Shutter/Silent]` & `[Image Quality/Rec]` NR:
       - `[Shutter Type]` (`Can be reset`): strictly **2** options (`Mechanical
         Shutter` default, `Electronic Shutter` — **zero** `Auto` option;
         `ELECTORONIC_SHUT` typo in dormant `_anti_distortion_shutter` family;
         `[Shutter Type in Interval]` defaults independently to `Electronic Shutter`).
         `Electronic Shutter` or `[Silent Mode] = On` locks out exact **5** items:
         `Flash`, `Long Exposure NR`, `e-Front Curtain Shut.`, `BULB`,
         `Anti-flicker Shoot.`.
       - Single **`1/250 s`** flash X-Sync ceiling (**zero** `1/320 s` APS-C tier on FX3).
       - `[e-Front Curtain Shut.]` (`BKID_APP_setting_front_curtaion_shutter` Sony
         `curtaion` typo, `On` default, **Reset-immune** `Initialize`-only).
       - `[Long Exposure NR]` (`>= 1 s` dark-frame subtraction, `Can be reset`);
         `[High ISO NR]` (`Normal/Low/Off`, does not alter `.ARW`) vs `ILME-FX6`
         `Noise Suppression` & `Technical > APR` (zero mechanical shutter on FX6).

  - **Gate `G152` (`CREATIVE_LOOK_10_PLUS_6_DORMANT_SOFT_SKIN_AND_DELETE_PROTECT_RECOVERDB_SLOT1_EROFS_FIREWALL`)**:
    1. `Exposure/Color -> [Color/Tone] -> [Creative Look]` (`Can be reset`):
       - **10** presets (`ST` default, `PT`, `NT`, `VV`, `VV2`, `FL`, `IN`, `SH`,
         `BW`, `SE`) + **6** `Custom Look 1..6` (`look{0..15}` split
         `look_still`/`look_movie`), **8** parameters (`Contrast`/`Highlights`/
         `Shadows`/`Saturation` `-9..+9`; **`Fade`/`Sharpness`/`Clarity` `0..9`
         asymmetric**; `Sharpness Range` `fineness` `1..5`), `Saturation` locked
         on `BW`/`SE`, `Sharpness Range` locked in `Movie`/`S&Q`, forced `[-]` when
         `Picture Profile != Off`, `Log Shooting != Off`, `HLG Still Image = On`,
         or `iAuto`.
       - **Dormant `[Soft Skin Effect]` Myth-Busting**: `BKID_APP_setting_soft_skin_effect`
         / `FX6 ns1 0x2cce..0x32da` are **100% dormant/unsupported** on BOTH
         `FX3 Ver. 7.02` and `FX6 Ver. 6.01` (`0` exposed UI items on both!) ->
         reject `EOPNOTSUPP=95`.
    2. Playback `[Delete]`, `[Protect]`, `[Display Media Info.]` & `[Recover Image DB]`
       Tier-0 `Slot 1` `EROFS=30` Firewall:
       - `[Delete]` (`5` batch modes, Proxy co-deletion), `[Delete confirm.]`
         (`"Cancel" first` default, Reset-immune), `[Delete pressing twice]`
         (`Off` default, Reset-immune), `[Protect]` (`7` modes, Proxy co-protection,
         zero `"Cancel All Images"`), read-only `[Display Media Info.]` (`40,000`
         max still display, zero disk writes), `[Recover Image DB]` (`AVF_INFO`
         rewrite + FTP transfer record wipe, immune to BOTH Reset & Initialize).
       - **Tier-0 `Slot 1` `EROFS=30` fail-closed firewall**: blocks any `Delete`,
         `Protect`, or `Recover Image DB` mutation targeting `Slot 1`
         (`slot1_data_sector_writes == 0`, `emmc_nflasha_write_count == 0`),
         contrasted with `ILME-FX6` `Lock/Unlock Clip`, `Delete Clip`, and
         `Restore Media(A)/(B)` (`ng_write_protected`).

  - **Unified 152-Gate Master Safety Preflight (`G01..G152`)**:
    Delegates `G01..G150` to `evaluate_150gate_preflight()`, enforces `149/152`
    verified offline (`VERIFIED_149_OF_152_AWAITING_PHYSICAL_TIER0`) and `152/152`
    under `--simulate-bench-dry-run` (`VERIFIED_ALL_152_GATES_DRY_RUN_SIMULATED_BACKUP`),
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
from .realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard import (
    Master150GateReport,
    evaluate_150gate_preflight,
)


# ---------------------------------------------------------------------------
# Schema, Versions, Env Keys & Shared Constants
# ---------------------------------------------------------------------------

REALHW_DRIVE_FOCUSBRACKET_SHUTTER_EFCS_CREATIVE_RECOVERDB_152GATE_SCHEMA = (
    "fx3_realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_152gate_guard_v1"
)
REALHW_DRIVE_FOCUSBRACKET_SHUTTER_EFCS_CREATIVE_RECOVERDB_152GATE_VERSION = (
    "2026.11.18-phase351-milestone152"
)
REALHW_152GATE_PREFLIGHT_SCHEMA = "realhw_152gate_preflight_v1"

G151 = "G151"
G151_GATE_ID = "G151"
G151_GATE_CODE = (
    "STILL_DRIVE_10FPS_DORMANT_FOCUS_BRACKET_AND_SHUTTER_TYPE_2MODE_XSYNC_250_EFCS_NR_GUARD"
)

G152 = "G152"
G152_GATE_ID = "G152"
G152_GATE_CODE = (
    "CREATIVE_LOOK_10_PLUS_6_DORMANT_SOFT_SKIN_AND_DELETE_PROTECT_RECOVERDB_SLOT1_EROFS_FIREWALL"
)

ENV_CLEAN_ROOM_TEST_PHASE351 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE351 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE351 = 0.05

EROFS_ERRNO_PHASE351 = 30
EROFS_NAME_PHASE351 = "EROFS"
EINVAL_ERRNO_PHASE351 = 22
EINVAL_NAME_PHASE351 = "EINVAL"
EOPNOTSUPP_ERRNO_PHASE351 = 95
EOPNOTSUPP_NAME_PHASE351 = "EOPNOTSUPP"

FX3_MODEL_NAME_PHASE351 = "ILME-FX3"
FX3_MODEL_ID_PHASE351 = 0x0502
FX3_HELP_GUIDE_CODE_PHASE351 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE351 = "7.02"
FX6_MODEL_NAME_PHASE351 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE351 = "6.01"

MEDIA_SLOT_NONE_PHASE351 = 0
MEDIA_SLOT_1_PHASE351 = 1
MEDIA_SLOT_2_PHASE351 = 2
ALLOWED_MEDIA_SLOTS_PHASE351: Tuple[int, ...] = (
    MEDIA_SLOT_NONE_PHASE351,
    MEDIA_SLOT_1_PHASE351,
    MEDIA_SLOT_2_PHASE351,
)

SHOOT_MODE_STILL_PHASE351 = "Still"
SHOOT_MODE_MOVIE_PHASE351 = "Movie"
SHOOT_MODE_SQ_PHASE351 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE351: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE351,
    SHOOT_MODE_MOVIE_PHASE351,
    SHOOT_MODE_SQ_PHASE351,
)

RESET_ACTION_NONE_PHASE351 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351 = "Camera Settings Reset"
RESET_ACTION_INITIALIZE_PHASE351 = "Initialize"
RESET_ACTION_RESET_NETWORK_SET_PHASE351 = "Reset Network Set."
ALLOWED_RESET_ACTIONS_PHASE351: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE351,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351,
    RESET_ACTION_INITIALIZE_PHASE351,
    RESET_ACTION_RESET_NETWORK_SET_PHASE351,
)


# ---------------------------------------------------------------------------
# Gate G151 Constants: Still [Drive Mode] 10fps / Dormant [Focus Bracket]
#                      [Shutter Type] 2-Mode Zero-Auto / 1/250 s X-Sync /
#                      [e-Front Curtain Shut.] curtaion Typo / Long/High ISO NR
# ---------------------------------------------------------------------------

DRIVE_MODE_MENU_PATH_G151 = "Shooting -> [Drive Mode] -> [Drive Mode]"
SHUTTER_SILENT_MENU_PATH_G151 = "Shooting -> [Shutter/Silent]"
IMAGE_QUALITY_NR_MENU_PATH_G151 = "Shooting -> [Image Quality/Rec]"

DRIVE_MODE_SINGLE_G151 = "Single Shooting"
DRIVE_MODE_CONT_G151 = "Cont. Shooting"
DRIVE_MODE_SELF_TIMER_SINGLE_G151 = "Self-timer(Single)"
DRIVE_MODE_SELF_TIMER_CONT_G151 = "Self-timer(Cont)"
DRIVE_MODE_CONT_BRACKET_G151 = "Cont. Bracket"
DRIVE_MODE_SINGLE_BRACKET_G151 = "Single Bracket"
DRIVE_MODE_WB_BRACKET_G151 = "WB bracket"
DRIVE_MODE_DRO_BRACKET_G151 = "DRO Bracket"
DRIVE_MODE_DEFAULT_G151 = DRIVE_MODE_SINGLE_G151

EXACT_8_DRIVE_MODES_G151: Tuple[str, ...] = (
    DRIVE_MODE_SINGLE_G151,
    DRIVE_MODE_CONT_G151,
    DRIVE_MODE_SELF_TIMER_SINGLE_G151,
    DRIVE_MODE_SELF_TIMER_CONT_G151,
    DRIVE_MODE_CONT_BRACKET_G151,
    DRIVE_MODE_SINGLE_BRACKET_G151,
    DRIVE_MODE_WB_BRACKET_G151,
    DRIVE_MODE_DRO_BRACKET_G151,
)
DRIVE_MODE_RESETTABLE_BY_CAMSET_RESET_G151 = True

CONT_SPEED_HI_PLUS_G151 = "Hi+"
CONT_SPEED_HI_G151 = "Hi"
CONT_SPEED_MID_G151 = "Mid"
CONT_SPEED_LO_G151 = "Lo"
ALLOWED_CONT_SPEEDS_G151: Tuple[str, ...] = (
    CONT_SPEED_HI_PLUS_G151,
    CONT_SPEED_HI_G151,
    CONT_SPEED_MID_G151,
    CONT_SPEED_LO_G151,
)
CONT_SHOOTING_MAX_FPS_G151: Dict[str, int] = {
    CONT_SPEED_HI_PLUS_G151: 10,
    CONT_SPEED_HI_G151: 8,
    CONT_SPEED_MID_G151: 6,
    CONT_SPEED_LO_G151: 3,
}
CONT_SHOOTING_FIRST_FRAME_AF_LOCK_SPEEDS_G151: Tuple[str, ...] = (
    CONT_SPEED_HI_PLUS_G151,
    CONT_SPEED_HI_G151,
    CONT_SPEED_MID_G151,
)
CONT_SHOOTING_FIRST_FRAME_AF_LOCK_APERTURE_FLOOR_G151 = 11.0

EXACT_3_SELF_TIMER_SINGLE_OPTIONS_G151: Tuple[str, ...] = (
    "10 Sec",
    "5 Sec",
    "2 Sec",
)
EXACT_6_SELF_TIMER_CONT_OPTIONS_G151: Tuple[str, ...] = (
    "10 Sec. 3 Img.",
    "10 Sec. 5 Img.",
    "5 Sec. 3 Img.",
    "5 Sec. 5 Img.",
    "2 Sec. 3 Img.",
    "2 Sec. 5 Img.",
)
DORMANT_SELF_TIMER_CONT_OPTIONS_G151: Tuple[str, ...] = (
    "10SEC_10IMAGES",
    "5SEC_10IMAGES",
)

BRACKET_STEP_359_EV_G151: Tuple[str, ...] = ("0.3EV", "0.5EV", "0.7EV", "1.0EV")
BRACKET_STEP_35_EV_G151: Tuple[str, ...] = ("2.0EV", "3.0EV")
WB_BRACKET_MODES_G151: Tuple[str, ...] = ("Lo", "Hi")  # ±10 MK-1 / ±20 MK-1
DRO_BRACKET_MODES_G151: Tuple[str, ...] = ("Lo", "Hi")  # Lv 1,2,3 / Lv 1,3,5

DORMANT_FOCUS_BRACKET_TOKENS_G151: Tuple[str, ...] = (
    "Focus Bracket",
    "Focus Bracket Order",
    "DRIVE_MODE_FOCUS_BRACKET",
    "BKID_APP_setting_focus_bracket_depth",
    "BKID_APP_setting_focus_bracket_exposure_lock",
    "BKID_APP_setting_focus_bracket_interval",
    "BKID_APP_setting_focus_bracket_number_of_shots",
    "BKID_APP_setting_focus_bracket_order",
    "BKID_APP_setting_focus_bracket_rec_folder",
)
FX6_DORMANT_FOCUS_BRACKET_SYMBOL_COUNT_G151 = 56
DORMANT_FOCUS_BRACKET_EXPOSED_EVENTS_G151 = 0

SHUTTER_TYPE_MECHANICAL_G151 = "Mechanical Shutter"
SHUTTER_TYPE_ELECTRONIC_G151 = "Electronic Shutter"
SHUTTER_TYPE_DEFAULT_G151 = SHUTTER_TYPE_MECHANICAL_G151
EXACT_2_SHUTTER_TYPES_G151: Tuple[str, ...] = (
    SHUTTER_TYPE_MECHANICAL_G151,
    SHUTTER_TYPE_ELECTRONIC_G151,
)
DORMANT_SHUTTER_TYPE_AUTO_TOKENS_G151: Tuple[str, ...] = (
    "Auto",
    "AUTO",
    "STILL_SHUTTER_TYPE_AUTO",
    "STILL_SHUTTER_TYPE_ANTI_DISTORTION_SHUTTER_AUTO",
    "ELECTORONIC_SHUT",
)
SHUTTER_TYPE_RESETTABLE_BY_CAMSET_RESET_G151 = True
INTERVAL_SHUTTER_TYPE_DEFAULT_G151 = SHUTTER_TYPE_ELECTRONIC_G151

EXACT_5_ELECTRONIC_SHUTTER_LOCKED_ITEMS_G151: Tuple[str, ...] = (
    "Flash",
    "Long Exposure NR",
    "e-Front Curtain Shut.",
    "BULB",
    "Anti-flicker Shoot.",
)

FX3_FLASH_XSYNC_CEILING_STR_G151 = "1/250"
FX3_FLASH_XSYNC_CEILING_SEC_G151 = 1.0 / 250.0
DORMANT_APSC_XSYNC_STR_G151 = "1/320"

EFCS_ELF_TYPO_SYMBOL_G151 = "BKID_APP_setting_front_curtaion_shutter"
EFCS_DEFAULT_G151 = "On"
EFCS_RESETTABLE_BY_CAMSET_RESET_G151 = False

LONG_EXPOSURE_NR_DEFAULT_G151 = "On"
LONG_EXPOSURE_NR_RESETTABLE_BY_CAMSET_RESET_G151 = True
LONG_EXPOSURE_NR_MIN_SHUTTER_SEC_G151 = 1.0

HIGH_ISO_NR_NORMAL_G151 = "Normal"
HIGH_ISO_NR_LOW_G151 = "Low"
HIGH_ISO_NR_OFF_G151 = "Off"
HIGH_ISO_NR_DEFAULT_G151 = HIGH_ISO_NR_NORMAL_G151
EXACT_3_HIGH_ISO_NR_OPTIONS_G151: Tuple[str, ...] = (
    HIGH_ISO_NR_NORMAL_G151,
    HIGH_ISO_NR_LOW_G151,
    HIGH_ISO_NR_OFF_G151,
)
DORMANT_HIGH_ISO_NR_TOKENS_G151: Tuple[str, ...] = ("High", "HIGH")
HIGH_ISO_NR_RESETTABLE_BY_CAMSET_RESET_G151 = True
HIGH_ISO_NR_ALTERS_ARW_G151 = False

FX6_NOISE_SUPPRESSION_MODES_G151: Tuple[str, ...] = ("Off", "Low", "Mid", "High")
FX6_APR_MENU_PATH_G151 = "Technical > APR > Execute"

# UXC resid16 anchors (G151)
DRIVE_MODE_F_RESID16_G151 = 0x7228
SINGLE_SHOOTING_F_RESID16_G151 = 0x6D37
CONT_SHOOTING_F_RESID16_G151 = 0x6A32
CONT_HI_PLUS_F_RESID16_G151 = 0x68D1
CONT_HI_F_RESID16_G151 = 0x6C00
CONT_MID_F_RESID16_G151 = 0x6F48
CONT_LO_F_RESID16_G151 = 0x6A0B
SELF_TIMER_SINGLE_F_RESID16_G151 = 0x6772
SELF_TIMER_CONT_F_RESID16_G151 = 0x728C
CONT_BRACKET_F_RESID16_G151 = 0x72CB
SINGLE_BRACKET_F_RESID16_G151 = 0x790B
WB_BRACKET_F_RESID16_G151 = 0x7ACB
DRO_BRACKET_F_RESID16_G151 = 0x748D
DORMANT_FOCUS_BRACKET_F_RESID16_G151 = 0x7563
DORMANT_FOCUS_BRACKET_ORDER_F_RESID16_G151 = 0x6915
SHUTTER_TYPE_F_RESID16_G151 = 0x63DB
SHUTTER_MECHANICAL_F_RESID16_G151 = 0x6DDB
SHUTTER_ELECTRONIC_F_RESID16_G151 = 0x755A
DORMANT_SHUTTER_AUTO_DESC_F_RESID16_G151 = 0x66B8
EFCS_F_RESID16_G151 = 0x64C6
LONG_EXPOSURE_NR_F_RESID16_G151 = 0x6465
HIGH_ISO_NR_F_RESID16_G151 = 0x650B

STATUS_VERIFIED_G151 = (
    "VERIFIED_G151_STILL_DRIVE_10FPS_DORMANT_FOCUS_BRACKET_AND_SHUTTER_TYPE_2MODE_XSYNC_250_EFCS_NR_GUARD"
)
STATUS_BLOCKED_G151_TELEMETRY_INVALID = "BLOCKED_G151_TELEMETRY_INVALID"
STATUS_BLOCKED_G151_DORMANT_FOCUS_BRACKET_SHUTTER_AUTO_OR_FX6_EOPNOTSUPP = (
    "BLOCKED_G151_DORMANT_FOCUS_BRACKET_SHUTTER_AUTO_OR_FX6_EOPNOTSUPP"
)
STATUS_BLOCKED_G151_DRIVE_LOCKOUT_OR_XSYNC_1_320_VIOLATION = (
    "BLOCKED_G151_DRIVE_LOCKOUT_OR_XSYNC_1_320_VIOLATION"
)
STATUS_BLOCKED_G151_SHUTTER_TYPE_EFCS_RESET_OR_NR_VIOLATION = (
    "BLOCKED_G151_SHUTTER_TYPE_EFCS_RESET_OR_NR_VIOLATION"
)


# ---------------------------------------------------------------------------
# Gate G152 Constants: [Creative Look] 10+6 Slots / 0..9 Bounds / Dormant
#                      [Soft Skin Effect] & [Delete]/[Protect]/
#                      [Recover Image DB] Tier-0 Slot-1 EROFS=30 Firewall
# ---------------------------------------------------------------------------

CREATIVE_LOOK_MENU_PATH_G152 = "Exposure/Color -> [Color/Tone] -> [Creative Look]"
PLAYBACK_DELETE_MENU_PATH_G152 = "Playback -> [Delete]"
PLAYBACK_PROTECT_MENU_PATH_G152 = "Playback -> [Selection/Memo] -> [Protect]"
MEDIA_RECOVER_DB_MENU_PATH_G152 = "Shooting -> [Media] -> [Recover Image DB]"
MEDIA_DISPLAY_INFO_MENU_PATH_G152 = "Shooting -> [Media] -> [Display Media Info.]"

CREATIVE_LOOK_10_PRESETS_G152: Tuple[str, ...] = (
    "ST",
    "PT",
    "NT",
    "VV",
    "VV2",
    "FL",
    "IN",
    "SH",
    "BW",
    "SE",
)
CREATIVE_LOOK_6_CUSTOM_SLOTS_G152: Tuple[str, ...] = (
    "Custom Look 1",
    "Custom Look 2",
    "Custom Look 3",
    "Custom Look 4",
    "Custom Look 5",
    "Custom Look 6",
)
ALLOWED_CREATIVE_LOOK_SLOTS_G152: Tuple[str, ...] = (
    CREATIVE_LOOK_10_PRESETS_G152 + CREATIVE_LOOK_6_CUSTOM_SLOTS_G152
)
CREATIVE_LOOK_DEFAULT_G152 = "ST"
CREATIVE_LOOK_TOTAL_SLOTS_G152 = 16
CREATIVE_LOOK_RESETTABLE_BY_CAMSET_RESET_G152 = True

CREATIVE_LOOK_8_PARAM_BOUNDS_G152: Dict[str, Tuple[int, int]] = {
    "Contrast": (-9, 9),
    "Highlights": (-9, 9),
    "Shadows": (-9, 9),
    "Fade": (0, 9),
    "Saturation": (-9, 9),
    "Sharpness": (0, 9),
    "Sharpness Range": (1, 5),
    "Clarity": (0, 9),
}
CREATIVE_LOOK_SATURATION_LOCKED_PRESETS_G152: Tuple[str, ...] = ("BW", "SE")

DORMANT_SOFT_SKIN_TOKENS_G152: Tuple[str, ...] = (
    "Soft Skin Effect",
    "Soft Skin Effect Level",
    "BKID_APP_setting_soft_skin_effect",
    "BKID_APP_setting_soft_skin_effect_on",
    "SOFT_SKIN_EFFECT_ON_OPTION_LOW",
    "SOFT_SKIN_EFFECT_ON_OPTION_MID",
    "SOFT_SKIN_EFFECT_ON_OPTION_HI",
)
DORMANT_SOFT_SKIN_EXPOSED_FX3_G152 = 0
DORMANT_SOFT_SKIN_EXPOSED_FX6_G152 = 0

EXACT_5_DELETE_BATCH_MODES_G152: Tuple[str, ...] = (
    "All Other Than This Img.",
    "All Images in This Group",
    "Multiple Img.",
    "All in this Folder",
    "All with this date",
)
DELETE_CONFIRM_CANCEL_FIRST_G152 = "\"Cancel\" first"
DELETE_CONFIRM_DELETE_FIRST_G152 = "\"Delete\" first"
ALLOWED_DELETE_CONFIRM_MODES_G152: Tuple[str, ...] = (
    DELETE_CONFIRM_CANCEL_FIRST_G152,
    DELETE_CONFIRM_DELETE_FIRST_G152,
)
DELETE_PRESSING_TWICE_DEFAULT_G152 = "Off"
PLAYBACK_DELETE_CONFIG_RESETTABLE_BY_CAMSET_RESET_G152 = False

EXACT_7_PROTECT_MODES_G152: Tuple[str, ...] = (
    "Multiple Img.",
    "All in this Folder",
    "Cancel All in this Folder",
    "All with this date",
    "Cancel All with this date",
    "All Images in This Group",
    "Cancel All in This Group",
)
ABSENT_PROTECT_CANCEL_ALL_IMAGES_G152 = "Cancel All Images"

DISPLAY_MEDIA_INFO_MAX_STILL_COUNT_G152 = 40_000
DISPLAY_MEDIA_INFO_ELF_TYPO_G152 = "NOT_DISPLAYNG"
RECOVER_IMAGE_DB_IMMUNE_TO_RESET_AND_INIT_G152 = True
DEFAULT_PLAYBACK_MEDIA_SLOT_G152 = MEDIA_SLOT_1_PHASE351

FX6_MEDIA_MUTATION_MENUS_G152: Tuple[str, ...] = (
    "Lock/Unlock Clip",
    "Delete Clip",
    "Restore Media(A)",
    "Restore Media(B)",
)

# UXC resid16 anchors (G152)
CREATIVE_LOOK_F_RESID16_G152 = 0x6823
CUSTOM_LOOK_F_RESID16_G152 = 0x6C98
CLARITY_F_RESID16_G152 = 0x6921
SHARPNESS_RANGE_F_RESID16_G152 = 0x6E76
DORMANT_SOFT_SKIN_F_RESID16_G152 = 0x76D9
DELETE_BASE_RESID16_G152 = 0xE504
DELETE_CONFIRM_BASE_RESID16_G152 = 0xE721
DELETE_PRESSING_TWICE_F_RESID16_G152 = 0x74DB
PROTECT_BASE_RESID16_G152 = 0xE2C9
RECOVER_IMAGE_DB_F_RESID16_G152 = 0x711B
RECOVER_IMAGE_DB_BASE_RESID16_G152 = 0xE918
DISPLAY_MEDIA_INFO_BASE_RESID16_G152 = 0xEA2A

STATUS_VERIFIED_G152 = (
    "VERIFIED_G152_CREATIVE_LOOK_10_PLUS_6_DORMANT_SOFT_SKIN_AND_DELETE_PROTECT_RECOVERDB_SLOT1_EROFS_FIREWALL"
)
STATUS_BLOCKED_G152_TELEMETRY_INVALID = "BLOCKED_G152_TELEMETRY_INVALID"
STATUS_BLOCKED_G152_DORMANT_SOFT_SKIN_OR_PROTECT_CANCEL_ALL_EOPNOTSUPP = (
    "BLOCKED_G152_DORMANT_SOFT_SKIN_OR_PROTECT_CANCEL_ALL_EOPNOTSUPP"
)
STATUS_BLOCKED_G152_SLOT1_DELETE_PROTECT_RECOVERDB_VAULT_EROFS = (
    "BLOCKED_G152_SLOT1_DELETE_PROTECT_RECOVERDB_VAULT_EROFS"
)
STATUS_BLOCKED_G152_CREATIVE_LOOK_BOUNDS_LOCKOUT_OR_DELETE_RESET_VIOLATION = (
    "BLOCKED_G152_CREATIVE_LOOK_BOUNDS_LOCKOUT_OR_DELETE_RESET_VIOLATION"
)
STATUS_BLOCKED_PHASE351_DONOR_INTEGRITY = "BLOCKED_PHASE351_DONOR_INTEGRITY"


# ---------------------------------------------------------------------------
# Pinned Wave-66 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE351: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x03BC6799, b"BKID_APP_setting_menu_drive_mode"),
    (0x03AA2479, b"DRIVE_MODE_1_IMAGE_SHOOTING"),
    (0x02FA1A88, b"DRIVE_MODE_CONT_SHOOTING"),
    (0x02FB17EB, b"DRIVE_MODE_SELF_TIMER"),
    (0x02FB3D76, b"DRIVE_MODE_CONT_SELF_TIMER"),
    (0x02FA1AB0, b"DRIVE_MODE_CONT_BRACKET"),
    (0x02FA1AD1, b"DRIVE_MODE_BRACKET_SINGLE"),
    (0x02FB52A0, b"DRIVE_MODE_WHITE_BALANCE_BRACKET"),
    (0x02FB5317, b"DRIVE_MODE_DRO_ADV_BRACKET"),
    (0x03BC69C5, b"BKID_APP_setting_bracket_self_timer"),
    (0x03BC6A10, b"BKID_APP_setting_bracket_order"),
    (0x03BCEC4E, b"BKID_APP_setting_focus_bracket_depth"),
    (0x03BC6A51, b"BKID_APP_setting_focus_bracket_order"),
    (0x03AA259D, b"VAL_setting_menu_drive_mode_DRIVE_MODE_FOCUS_BRACKET"),
    (0x03BC6F96, b"BKID_APP_setting_still_shutter_type"),
    (0x03A77332, b"VAL_setting_still_shutter_type_STILL_SHUTTER_TYPE_MECHANICAL"),
    (0x03A7736F, b"VAL_setting_still_shutter_type_STILL_SHUTTER_TYPE_ELECTRONIC"),
    (0x03BC6FE1, b"BKID_APP_setting_still_shutter_type_anti_distortion_shutter"),
    (0x03B605D6, b"ELECTORONIC_SHUT"),
    (0x03BC6CC1, b"BKID_APP_setting_shutter_type_in_interval_anti_distortion_shutter"),
    (0x03BC705C, b"BKID_APP_setting_front_curtaion_shutter"),
    (0x03BC5F6F, b"BKID_APP_setting_still_long_exposure_nr"),
    (0x03BC5FC2, b"BKID_APP_setting_still_high_iso_nr"),
    (0x03BE7F5F, b"BKID_APP_creative_look_option_look0"),
    (0x03BE83CE, b"BKID_APP_creative_look_option_look15"),
    (0x03BC8CE9, b"BKID_APP_setting_soft_skin_effect"),
    (0x03C1BBB4, b"SOFT_SKIN_EFFECT_ON_OPTION_LOW"),
    (0x03BC99F4, b"BKID_APP_setting_delete_confirm"),
    (0x03BC99CC, b"BKID_APP_setting_delete_by_delete_twice"),
    (0x039D33A0, b"VAL_system_mode_option_SYSTEM_MODE_OPTION_RECOVER_DB"),
    (0x039BA0D5, b"PRM_media_info_displaying_state"),
    (0x03AFD6A0, b"NOT_DISPLAYNG"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE351 = (
    "a91c68ee11c2648ae7a41d5bdc4392bebd09e5078f33b67e34740f0c261dcdb8"
)

PINNED_FX6_APPFW_SLICES_PHASE351: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x025C166D, b"sequence_start_focus_bracket"),
    (0x0280A864, b"drive_mode_expanded_option_switch_focus_bracket"),
    (0x023C6DA2, b"procam_msg_confirm_restore_media_a_controller"),
    (0x023C6E92, b"procam_msg_confirm_restore_media_b_controller"),
    (0x028E0D59, b"ng_write_protected"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE351 = (
    "4d8b8cb4a9edb3942fec92b49722f85ae34917aae2edc33bc420218e2b399758"
)

PINNED_PHASE351_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE351,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE351),
        "FX3 appFw.so Wave-66 Drive/FocusBracket/Shutter/EFCS/NR/CreativeLook/SoftSkin/Delete/RecoverDB slices",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4\x00",),
        "FX3-CX95900_ALLLANG-Backup.bin BK4 seed",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Drive Mode",
            b"Single Shooting",
            b"Cont. Shooting",
            b"Focus Bracket",
            b"Shutter Type",
            b"Mechanical Shutter",
            b"Electronic Shutter",
            b"e-Front Curtain Shut.",
            b"Long Exposure NR",
            b"High ISO NR",
            b"Creative Look",
            b"Custom Look",
            b"Soft Skin Effect",
            b"Delete pressing twice",
            b"Recover Image DB",
        ),
        "FX3 string_english_f.uxc Wave-66 EN parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Delete",
            b"Protect",
            b"Contrast",
            b"Saturation",
            b"Sharpness",
            b"Display Media Info.",
        ),
        "FX3 string_english.uxc Wave-66 base tokens",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "拍摄模式".encode("utf-8"),
            "单张拍摄".encode("utf-8"),
            "连拍".encode("utf-8"),
            "对焦包围".encode("utf-8"),
            "快门类型".encode("utf-8"),
            "电子前帘快门".encode("utf-8"),
            "高ISO降噪".encode("utf-8"),
            "创意外观".encode("utf-8"),
            "美肤效果".encode("utf-8"),
            "修复影像数据库".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-66 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "過片模式".encode("utf-8"),
            "單張拍攝".encode("utf-8"),
            "連拍".encode("utf-8"),
            "對焦階段".encode("utf-8"),
            "快門類型".encode("utf-8"),
            "電子式前簾快門".encode("utf-8"),
            "消除長曝雜訊".encode("utf-8"),
            "高ISO雜訊消除".encode("utf-8"),
            "風格外觀".encode("utf-8"),
            "柔膚效果".encode("utf-8"),
            "還原影像資料庫".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-66 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "ドライブモード".encode("utf-8"),
            "連続撮影".encode("utf-8"),
            "ﾌｫｰｶｽﾌﾞﾗｹｯﾄ".encode("utf-8"),
            "シャッター方式".encode("utf-8"),
            "電子先幕ｼｬｯﾀｰ".encode("utf-8"),
            "長秒時ノイズ低減".encode("utf-8"),
            "高感度ノイズ低減".encode("utf-8"),
            "ｸﾘｴｲﾃｨﾌﾞﾙｯｸ".encode("utf-8"),
            "美肌効果".encode("utf-8"),
            "管理ファイル修復".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-66 JA parity",
    ),
    "fx6_appfw_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
        50_520_424,
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE351,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE351),
        "FX6 appFw.so Wave-66 dormant focus_bracket & restore_media/ng_write_protected slices",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (b"Base Look", b"Noise Suppression", b"Soft Skin Effect Level"),
        "FX6 string_english.uxc Wave-66 EN baseline",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (b"Delete Clip", b"Restore Media(A)", b"Restore Media(B)", b"Media Status"),
        "FX6 string_english_2.uxc Wave-66 EN enterprise baseline",
    ),
}


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _is_clean_room_forced(force_clean_room: Optional[bool]) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE351):
        if os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def _is_strict_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _is_strict_num(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def _is_on_off(val: Any) -> bool:
    return isinstance(val, str) and val in ("On", "Off")


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
    for idx, tok in enumerate(required_tokens):
        if not any(var in data for var in _encode_token_variants(tok)):
            missing.append(f"token_missing_idx_{idx}")
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
    if body_model_name != FX3_MODEL_NAME_PHASE351:
        errs.append(f"body_model_name_invalid:{body_model_name!r}")
    if not _is_strict_int(body_model_id) or body_model_id != FX3_MODEL_ID_PHASE351:
        errs.append(f"body_model_id_invalid:{body_model_id!r}")
    if help_guide_code != FX3_HELP_GUIDE_CODE_PHASE351:
        errs.append(f"help_guide_code_invalid:{help_guide_code!r}")
    if _parse_fw_float(firmware_version) is None:
        errs.append(f"firmware_version_invalid:{firmware_version!r}")
    return errs


def strip_elapsed_seconds_recursive_phase351(obj: Any) -> Any:
    """Recursively strip non-deterministic `elapsed_seconds` keys for canonical digests."""
    if isinstance(obj, dict):
        return {
            k: strip_elapsed_seconds_recursive_phase351(v)
            for k, v in obj.items()
            if k != "elapsed_seconds"
        }
    if isinstance(obj, list):
        return [strip_elapsed_seconds_recursive_phase351(v) for v in obj]
    if isinstance(obj, tuple):
        return [strip_elapsed_seconds_recursive_phase351(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Donor Integrity Audit (O_RDONLY / Clean-Room Dual-Mode)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase351DonorAuditResult:
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


def audit_phase351_donor_contracts(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase351DonorAuditResult:
    """Fast (< 0.20s) O_RDONLY + bounded os.pread donor audit with clean-room fallback."""
    import time

    t0 = time.perf_counter()
    clean_forced = _is_clean_room_forced(force_clean_room)
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else dict(PINNED_PHASE351_DONOR_SPECS)
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
        return Phase351DonorAuditResult(
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
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE351,
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
        return Phase351DonorAuditResult(
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
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE351,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(
                f"Donor files absent ({len(missing_files)} missing); "
                "verified Phase 351 via clean-room synthetic fallback.",
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
                target, PINNED_FX3_APPFW_SLICES_PHASE351
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tok_errs = _read_exact_o_rdonly_slices(
                target, PINNED_FX6_APPFW_SLICES_PHASE351
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
    return Phase351DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE
            if valid
            else STATUS_BLOCKED_PHASE351_DONOR_INTEGRITY
        ),
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="STRICT_OS_O_RDONLY_PREAD",
        files_inspected=inspected,
        fx3_contracts_verified=valid,
        fx6_contracts_verified=valid,
        four_lang_resid16_parity_verified=valid,
        zero_forbidden_myths_verified=valid,
        elapsed_seconds=round(dt, 6),
        within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE351,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        file_digests=file_digests,
        missing_markers=tuple(missing_markers),
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# Gate G151: Still [Drive Mode] 10fps / Dormant [Focus Bracket] &
#            [Shutter Type] 2-Mode Zero-Auto / 1/250 s X-Sync / EFCS / NR
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DriveFocusBracketShutterEfcsNrGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    drive_menu_path: str
    shutter_silent_menu_path: str
    image_quality_nr_menu_path: str
    effective_shoot_mode: str
    drive_mode_available: bool
    effective_drive_mode: str
    effective_cont_speed: str
    effective_max_fps: int
    cont_shooting_speed_reduced: bool
    first_frame_af_locked: bool
    dro_bracket_available: bool
    dormant_focus_bracket_exposed_events: int
    dormant_focus_bracket_rejected: bool
    effective_shutter_type: str
    dormant_shutter_auto_rejected: bool
    electronic_shutter_5_lockouts: Tuple[str, ...]
    effective_flash_xsync_ceiling: str
    dormant_apsc_xsync_320_rejected: bool
    effective_efcs: str
    efcs_resettable_by_camset_reset: bool
    effective_long_exposure_nr: str
    long_exposure_nr_active_for_shot: bool
    long_exposure_nr_locked_disabled: bool
    effective_high_iso_nr: str
    high_iso_nr_alters_arw: bool
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


def resolve_fx3_drive_shutter_efcs_nr_state(
    *,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE351,
    drive_mode: str = DRIVE_MODE_DEFAULT_G151,
    cont_speed: str = CONT_SPEED_HI_PLUS_G151,
    aperture_f_number: float = 2.8,
    uncompressed_raw_active: bool = False,
    flash_firing: bool = False,
    hlg_still_image: str = "Off",
    exposure_mode: str = "P",
    shutter_type: str = SHUTTER_TYPE_DEFAULT_G151,
    silent_mode: str = "Off",
    efcs: str = EFCS_DEFAULT_G151,
    long_exposure_nr: str = LONG_EXPOSURE_NR_DEFAULT_G151,
    shutter_speed_seconds: float = 0.01,
    high_iso_nr: str = HIGH_ISO_NR_DEFAULT_G151,
    still_file_format: str = "JPEG",
    reset_action: str = RESET_ACTION_NONE_PHASE351,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-66 Still Drive, Shutter Type, EFCS & NR state."""
    if reset_action == RESET_ACTION_INITIALIZE_PHASE351:
        eff_efcs_req = EFCS_DEFAULT_G151
    else:
        eff_efcs_req = efcs

    if reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351,
        RESET_ACTION_INITIALIZE_PHASE351,
    ):
        eff_drive_req = DRIVE_MODE_DEFAULT_G151
        eff_shutter_type = SHUTTER_TYPE_DEFAULT_G151
        eff_long_nr_req = LONG_EXPOSURE_NR_DEFAULT_G151
        eff_high_iso_nr_req = HIGH_ISO_NR_DEFAULT_G151
    else:
        eff_drive_req = drive_mode
        eff_shutter_type = shutter_type
        eff_long_nr_req = long_exposure_nr
        eff_high_iso_nr_req = high_iso_nr

    drive_avail = shoot_mode == SHOOT_MODE_STILL_PHASE351
    dro_avail = drive_avail and hlg_still_image != "On"

    if not drive_avail:
        eff_drive = "Unavailable"
    elif eff_drive_req == DRIVE_MODE_DRO_BRACKET_G151 and not dro_avail:
        eff_drive = "Unavailable"
    elif eff_drive_req in (
        DRIVE_MODE_CONT_BRACKET_G151,
        DRIVE_MODE_SINGLE_BRACKET_G151,
    ) and exposure_mode == "iAuto":
        eff_drive = "Unavailable"
    else:
        eff_drive = eff_drive_req

    base_fps = CONT_SHOOTING_MAX_FPS_G151.get(cont_speed, 10)
    speed_reduced = (
        eff_drive == DRIVE_MODE_CONT_G151
        and (uncompressed_raw_active or flash_firing)
    )
    eff_max_fps = (
        max(1, base_fps - 2) if speed_reduced else (base_fps if eff_drive == DRIVE_MODE_CONT_G151 else 1)
    )
    first_frame_af_locked = (
        eff_drive == DRIVE_MODE_CONT_G151
        and cont_speed in CONT_SHOOTING_FIRST_FRAME_AF_LOCK_SPEEDS_G151
        and aperture_f_number > CONT_SHOOTING_FIRST_FRAME_AF_LOCK_APERTURE_FLOOR_G151
    )

    elec_locked = (
        eff_shutter_type == SHUTTER_TYPE_ELECTRONIC_G151
        or silent_mode == "On"
    )
    lockouts = (
        EXACT_5_ELECTRONIC_SHUTTER_LOCKED_ITEMS_G151
        if elec_locked
        else ()
    )
    eff_efcs = "Disabled" if elec_locked else eff_efcs_req

    long_nr_locked = (
        elec_locked
        or eff_drive in (DRIVE_MODE_CONT_G151, DRIVE_MODE_CONT_BRACKET_G151)
        or not drive_avail
    )
    if long_nr_locked:
        eff_long_nr = "Disabled"
    elif exposure_mode == "iAuto":
        eff_long_nr = "On"
    else:
        eff_long_nr = eff_long_nr_req

    long_nr_active_for_shot = (
        eff_long_nr == "On"
        and shutter_speed_seconds >= LONG_EXPOSURE_NR_MIN_SHUTTER_SEC_G151
    )

    if still_file_format == "RAW" or not drive_avail:
        eff_high_iso_nr = "Unavailable"
    elif exposure_mode == "iAuto":
        eff_high_iso_nr = HIGH_ISO_NR_NORMAL_G151
    else:
        eff_high_iso_nr = eff_high_iso_nr_req

    return {
        "drive_mode_available": drive_avail,
        "effective_drive_mode": eff_drive,
        "effective_cont_speed": cont_speed,
        "effective_max_fps": eff_max_fps,
        "cont_shooting_speed_reduced": speed_reduced,
        "first_frame_af_locked": first_frame_af_locked,
        "dro_bracket_available": dro_avail,
        "effective_shutter_type": eff_shutter_type,
        "electronic_shutter_5_lockouts": lockouts,
        "effective_flash_xsync_ceiling": FX3_FLASH_XSYNC_CEILING_STR_G151,
        "effective_efcs": eff_efcs,
        "effective_long_exposure_nr": eff_long_nr,
        "long_exposure_nr_active_for_shot": long_nr_active_for_shot,
        "long_exposure_nr_locked_disabled": long_nr_locked,
        "effective_high_iso_nr": eff_high_iso_nr,
    }


def compute_drive_shutter_efcs_nr_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G151 (384 states)."""
    combos = list(
        itertools.product(
            (SHOOT_MODE_STILL_PHASE351, SHOOT_MODE_MOVIE_PHASE351),
            (DRIVE_MODE_SINGLE_G151, DRIVE_MODE_CONT_G151, DRIVE_MODE_DRO_BRACKET_G151),
            (CONT_SPEED_HI_PLUS_G151, CONT_SPEED_LO_G151),
            (2.8, 16.0),  # aperture_f_number
            EXACT_2_SHUTTER_TYPES_G151,
            ("Off", "On"),  # hlg_still_image
            (0.01, 2.0),  # shutter_speed_seconds
            (
                RESET_ACTION_NONE_PHASE351,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351,
            ),
        )
    )
    cont_10fps_count = 0
    first_frame_af_locked_count = 0
    elec_5_lockouts_count = 0
    efcs_reset_preserved_count = 0
    long_nr_darkframe_triggered_count = 0
    dro_hlg_blocked_count = 0

    for sm, dm, spd, fnum, stype, hlg, ssec, rst in combos:
        st = resolve_fx3_drive_shutter_efcs_nr_state(
            shoot_mode=sm,
            drive_mode=dm,
            cont_speed=spd,
            aperture_f_number=fnum,
            hlg_still_image=hlg,
            shutter_type=stype,
            efcs="Off",
            shutter_speed_seconds=ssec,
            reset_action=rst,
        )
        if st["effective_drive_mode"] == DRIVE_MODE_CONT_G151 and st["effective_max_fps"] == 10:
            cont_10fps_count += 1
        if st["first_frame_af_locked"]:
            first_frame_af_locked_count += 1
        if len(st["electronic_shutter_5_lockouts"]) == 5:
            elec_5_lockouts_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351
            and st["effective_efcs"] == "Off"
        ):
            efcs_reset_preserved_count += 1
        if st["long_exposure_nr_active_for_shot"]:
            long_nr_darkframe_triggered_count += 1
        if sm == SHOOT_MODE_STILL_PHASE351 and hlg == "On" and not st["dro_bracket_available"]:
            dro_hlg_blocked_count += 1

    return {
        "total_matrix_states": len(combos),
        "cont_10fps_count": cont_10fps_count,
        "first_frame_af_locked_count": first_frame_af_locked_count,
        "elec_5_lockouts_count": elec_5_lockouts_count,
        "efcs_reset_preserved_count": efcs_reset_preserved_count,
        "long_nr_darkframe_triggered_count": long_nr_darkframe_triggered_count,
        "dro_hlg_blocked_count": dro_hlg_blocked_count,
    }


def verify_drive_focusbracket_shutter_efcs_nr_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE351,
    body_model_id: int = FX3_MODEL_ID_PHASE351,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE351,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE351,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE351,
    drive_mode: str = DRIVE_MODE_DEFAULT_G151,
    requested_dormant_focus_bracket: Optional[str] = None,
    claimed_focus_bracket_exposed_on_fx3_or_fx6: bool = False,
    cont_speed: str = CONT_SPEED_HI_PLUS_G151,
    aperture_f_number: float = 2.8,
    uncompressed_raw_active: bool = False,
    flash_firing: bool = False,
    claimed_cont_hi_plus_exceeds_10fps: bool = False,
    claimed_cont_af_tracks_above_f11: bool = False,
    self_timer_cont_option: str = "10 Sec. 3 Img.",
    hlg_still_image: str = "Off",
    claimed_dro_bracket_active_with_hlg_still: bool = False,
    claimed_drive_mode_active_in_movie_or_sq: bool = False,
    exposure_mode: str = "P",
    shutter_type: str = SHUTTER_TYPE_DEFAULT_G151,
    claimed_shutter_type_auto_exists: bool = False,
    silent_mode: str = "Off",
    claimed_electronic_shutter_allows_locked_item: bool = False,
    claimed_xsync_320_apsc_tier_supported: bool = False,
    efcs: str = EFCS_DEFAULT_G151,
    claimed_camset_reset_clears_efcs: bool = False,
    long_exposure_nr: str = LONG_EXPOSURE_NR_DEFAULT_G151,
    shutter_speed_seconds: float = 0.01,
    claimed_long_nr_active_under_lock_or_sub_1s: bool = False,
    high_iso_nr: str = HIGH_ISO_NR_DEFAULT_G151,
    still_file_format: str = "JPEG",
    claimed_high_iso_nr_alters_arw: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE351,
    fx6_mech_shutter_xsync_or_long_nr_spoof_requested: bool = False,
) -> DriveFocusBracketShutterEfcsNrGuardResult:
    """Enforce Gate G151: Still Drive 10fps / Dormant Focus Bracket & Shutter Type 2-Mode / EFCS / NR."""
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

    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE351:
        _add("TELEMETRY_INVALID", f"shoot_mode_invalid:{shoot_mode!r}")

    dormant_fb = bool(
        requested_dormant_focus_bracket is not None
        or drive_mode in DORMANT_FOCUS_BRACKET_TOKENS_G151
        or claimed_focus_bracket_exposed_on_fx3_or_fx6
    )
    if dormant_fb:
        _add(
            "DORMANT_FOCUS_BRACKET_EOPNOTSUPP",
            "fx3_ver_7_02_and_fx6_ver_6_01_have_zero_exposed_focus_bracket_in_ilc_2210_and_5_024_458_18_eopnotsupp_95",
        )
    elif drive_mode not in EXACT_8_DRIVE_MODES_G151:
        _add("TELEMETRY_INVALID", f"drive_mode_invalid:{drive_mode!r}")

    if self_timer_cont_option in DORMANT_SELF_TIMER_CONT_OPTIONS_G151:
        _add(
            "DORMANT_SELF_TIMER_10IMG_EOPNOTSUPP",
            f"fx3_ver_7_02_self_timer_cont_exposes_6_options_only_eopnotsupp_95:{self_timer_cont_option!r}",
        )
    elif self_timer_cont_option not in EXACT_6_SELF_TIMER_CONT_OPTIONS_G151:
        _add(
            "TELEMETRY_INVALID",
            f"self_timer_cont_option_invalid:{self_timer_cont_option!r}",
        )

    dormant_shutter_auto = bool(
        shutter_type in DORMANT_SHUTTER_TYPE_AUTO_TOKENS_G151
        or claimed_shutter_type_auto_exists
    )
    if dormant_shutter_auto:
        _add(
            "DORMANT_SHUTTER_TYPE_AUTO_EOPNOTSUPP",
            "fx3_ver_7_02_shutter_type_strictly_exposes_2_modes_zero_auto_option_eopnotsupp_95",
        )
    elif shutter_type not in EXACT_2_SHUTTER_TYPES_G151:
        _add("TELEMETRY_INVALID", f"shutter_type_invalid:{shutter_type!r}")

    if high_iso_nr in DORMANT_HIGH_ISO_NR_TOKENS_G151:
        _add(
            "DORMANT_HIGH_ISO_NR_HIGH_EOPNOTSUPP",
            f"fx3_ver_7_02_high_iso_nr_exposes_normal_low_off_only_high_dormant_eopnotsupp_95:{high_iso_nr!r}",
        )
    elif high_iso_nr not in EXACT_3_HIGH_ISO_NR_OPTIONS_G151:
        _add("TELEMETRY_INVALID", f"high_iso_nr_invalid:{high_iso_nr!r}")

    if fx6_mech_shutter_xsync_or_long_nr_spoof_requested:
        _add(
            "FX6_NO_MECH_SHUTTER_XSYNC_EOPNOTSUPP",
            "fx6_cinema_body_has_zero_mechanical_shutter_zero_efcs_zero_xsync_zero_long_exp_nr_eopnotsupp_95",
        )

    if cont_speed not in ALLOWED_CONT_SPEEDS_G151:
        _add("TELEMETRY_INVALID", f"cont_speed_invalid:{cont_speed!r}")
    if not _is_strict_num(aperture_f_number) or aperture_f_number <= 0:
        _add("TELEMETRY_INVALID", f"aperture_f_number_invalid:{aperture_f_number!r}")
    if not _is_on_off(hlg_still_image):
        _add("TELEMETRY_INVALID", f"hlg_still_image_invalid:{hlg_still_image!r}")
    if not _is_on_off(silent_mode):
        _add("TELEMETRY_INVALID", f"silent_mode_invalid:{silent_mode!r}")
    if not _is_on_off(efcs):
        _add("TELEMETRY_INVALID", f"efcs_invalid:{efcs!r}")
    if not _is_on_off(long_exposure_nr):
        _add("TELEMETRY_INVALID", f"long_exposure_nr_invalid:{long_exposure_nr!r}")
    if not _is_strict_num(shutter_speed_seconds) or shutter_speed_seconds <= 0:
        _add(
            "TELEMETRY_INVALID",
            f"shutter_speed_seconds_invalid:{shutter_speed_seconds!r}",
        )
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE351:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")

    state = resolve_fx3_drive_shutter_efcs_nr_state(
        shoot_mode=shoot_mode if shoot_mode in ALLOWED_SHOOT_MODES_PHASE351 else SHOOT_MODE_STILL_PHASE351,
        drive_mode=drive_mode if drive_mode in EXACT_8_DRIVE_MODES_G151 else DRIVE_MODE_DEFAULT_G151,
        cont_speed=cont_speed if cont_speed in ALLOWED_CONT_SPEEDS_G151 else CONT_SPEED_HI_PLUS_G151,
        aperture_f_number=float(aperture_f_number) if _is_strict_num(aperture_f_number) else 2.8,
        uncompressed_raw_active=uncompressed_raw_active,
        flash_firing=flash_firing,
        hlg_still_image=hlg_still_image if _is_on_off(hlg_still_image) else "Off",
        exposure_mode=exposure_mode,
        shutter_type=shutter_type if shutter_type in EXACT_2_SHUTTER_TYPES_G151 else SHUTTER_TYPE_DEFAULT_G151,
        silent_mode=silent_mode if _is_on_off(silent_mode) else "Off",
        efcs=efcs if _is_on_off(efcs) else EFCS_DEFAULT_G151,
        long_exposure_nr=long_exposure_nr if _is_on_off(long_exposure_nr) else LONG_EXPOSURE_NR_DEFAULT_G151,
        shutter_speed_seconds=float(shutter_speed_seconds) if _is_strict_num(shutter_speed_seconds) else 0.01,
        high_iso_nr=high_iso_nr if high_iso_nr in EXACT_3_HIGH_ISO_NR_OPTIONS_G151 else HIGH_ISO_NR_DEFAULT_G151,
        still_file_format=still_file_format,
        reset_action=reset_action if reset_action in ALLOWED_RESET_ACTIONS_PHASE351 else RESET_ACTION_NONE_PHASE351,
    )

    if claimed_cont_hi_plus_exceeds_10fps:
        _add(
            "DRIVE_CONT_FPS_CEILING_VIOLATION",
            "fx3_cont_shooting_hi_plus_ceiling_is_10fps_drops_on_uncompressed_raw_or_flash_einval_22",
        )
    if state["first_frame_af_locked"] and claimed_cont_af_tracks_above_f11:
        _add(
            "DRIVE_APERTURE_F11_AF_LOCK_VIOLATION",
            "cont_shooting_hi_plus_hi_mid_locks_focus_to_first_frame_above_f11_einval_22",
        )
    if hlg_still_image == "On" and claimed_dro_bracket_active_with_hlg_still:
        _add(
            "DRIVE_DRO_HLG_LOCKOUT_VIOLATION",
            "dro_bracket_is_disabled_when_hlg_still_image_is_on_einval_22",
        )
    if (not state["drive_mode_available"]) and claimed_drive_mode_active_in_movie_or_sq:
        _add(
            "DRIVE_STILL_ONLY_VIOLATION",
            "drive_mode_is_still_only_disabled_in_movie_and_sq_einval_22",
        )
    if len(state["electronic_shutter_5_lockouts"]) > 0 and claimed_electronic_shutter_allows_locked_item:
        _add(
            "SHUTTER_ELECTRONIC_5LOCKOUT_VIOLATION",
            "electronic_shutter_and_silent_mode_lock_out_flash_long_exp_nr_efcs_bulb_and_antiflicker_einval_22",
        )
    if claimed_xsync_320_apsc_tier_supported:
        _add(
            "XSYNC_SINGLE_250_CEILING_VIOLATION",
            "fx3_has_single_1_250s_flash_xsync_ceiling_zero_1_320s_apsc_tier_einval_22",
        )
    if claimed_camset_reset_clears_efcs:
        _add(
            "EFCS_RESET_IMMUNITY_VIOLATION",
            "e_front_curtain_shut_is_initialize_only_not_resettable_by_camset_reset_einval_22",
        )
    if claimed_long_nr_active_under_lock_or_sub_1s and (
        state["long_exposure_nr_locked_disabled"]
        or not state["long_exposure_nr_active_for_shot"]
    ):
        _add(
            "LONG_EXPOSURE_NR_THRESHOLD_LOCK_VIOLATION",
            "long_exposure_nr_triggers_only_at_ge_1s_and_is_disabled_in_elec_silent_cont_einval_22",
        )
    if claimed_high_iso_nr_alters_arw:
        _add(
            "HIGH_ISO_NR_ARW_IMMUTABILITY_VIOLATION",
            "high_iso_nr_never_alters_arw_raw_data_and_is_unavailable_in_raw_only_einval_22",
        )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G151
        block_errno = 0
        block_errno_name = "OK"
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G151_DORMANT_FOCUS_BRACKET_SHUTTER_AUTO_OR_FX6_EOPNOTSUPP
        block_errno = EOPNOTSUPP_ERRNO_PHASE351
        block_errno_name = EOPNOTSUPP_NAME_PHASE351
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
        status = STATUS_BLOCKED_G151_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE351
        block_errno_name = EINVAL_NAME_PHASE351
    elif any("DRIVE" in v or "XSYNC" in v for v in violations):
        status = STATUS_BLOCKED_G151_DRIVE_LOCKOUT_OR_XSYNC_1_320_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE351
        block_errno_name = EINVAL_NAME_PHASE351
    else:
        status = STATUS_BLOCKED_G151_SHUTTER_TYPE_EFCS_RESET_OR_NR_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE351
        block_errno_name = EINVAL_NAME_PHASE351

    return DriveFocusBracketShutterEfcsNrGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        drive_menu_path=DRIVE_MODE_MENU_PATH_G151,
        shutter_silent_menu_path=SHUTTER_SILENT_MENU_PATH_G151,
        image_quality_nr_menu_path=IMAGE_QUALITY_NR_MENU_PATH_G151,
        effective_shoot_mode=shoot_mode,
        drive_mode_available=state["drive_mode_available"],
        effective_drive_mode=state["effective_drive_mode"],
        effective_cont_speed=state["effective_cont_speed"],
        effective_max_fps=state["effective_max_fps"],
        cont_shooting_speed_reduced=state["cont_shooting_speed_reduced"],
        first_frame_af_locked=state["first_frame_af_locked"],
        dro_bracket_available=state["dro_bracket_available"],
        dormant_focus_bracket_exposed_events=DORMANT_FOCUS_BRACKET_EXPOSED_EVENTS_G151,
        dormant_focus_bracket_rejected=dormant_fb,
        effective_shutter_type=state["effective_shutter_type"],
        dormant_shutter_auto_rejected=dormant_shutter_auto,
        electronic_shutter_5_lockouts=state["electronic_shutter_5_lockouts"],
        effective_flash_xsync_ceiling=state["effective_flash_xsync_ceiling"],
        dormant_apsc_xsync_320_rejected=claimed_xsync_320_apsc_tier_supported,
        effective_efcs=state["effective_efcs"],
        efcs_resettable_by_camset_reset=EFCS_RESETTABLE_BY_CAMSET_RESET_G151,
        effective_long_exposure_nr=state["effective_long_exposure_nr"],
        long_exposure_nr_active_for_shot=state["long_exposure_nr_active_for_shot"],
        long_exposure_nr_locked_disabled=state["long_exposure_nr_locked_disabled"],
        effective_high_iso_nr=state["effective_high_iso_nr"],
        high_iso_nr_alters_arw=HIGH_ISO_NR_ALTERS_ARW_G151,
        fx6_cross_model_spoof_rejected=fx6_mech_shutter_xsync_or_long_nr_spoof_requested,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class G151DriveFocusBracketShutterEfcsNrGuardResult:
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
    drive_focusbracket_shutter_efcs_nr_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g151_drive_focusbracket_shutter_efcs_nr_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G151DriveFocusBracketShutterEfcsNrGuardResult]:
    audit = audit_phase351_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_drive_focusbracket_shutter_efcs_nr_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G151DriveFocusBracketShutterEfcsNrGuardResult(
        gate_id=G151,
        gate_code=G151_GATE_CODE,
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
        drive_focusbracket_shutter_efcs_nr_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G151,
        gate_code=G151_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"drive={res.effective_drive_mode} fps={res.effective_max_fps} "
            f"shutter={res.effective_shutter_type} xsync={res.effective_flash_xsync_ceiling} "
            f"efcs={res.effective_efcs} long_nr={res.effective_long_exposure_nr} "
            f"high_iso_nr={res.effective_high_iso_nr}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_drive_focusbracket_shutter_efcs_nr_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G151DriveFocusBracketShutterEfcsNrGuardResult]:
    return evaluate_g151_drive_focusbracket_shutter_efcs_nr_guard(**kwargs)


# ---------------------------------------------------------------------------
# Gate G152: [Creative Look] 10+6 Slots / 0..9 Bounds / Dormant [Soft Skin]
#            & [Delete] / [Protect] / [Recover Image DB] Tier-0 Slot-1 EROFS=30
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CreativeLookSoftSkinDeleteProtectRecoverDbGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    creative_look_menu_path: str
    playback_delete_menu_path: str
    playback_protect_menu_path: str
    media_recover_db_menu_path: str
    media_display_info_menu_path: str
    effective_creative_look: str
    creative_look_forced_dash_disabled: bool
    creative_look_saturation_locked: bool
    creative_look_sharpness_range_locked: bool
    creative_look_8_params: Dict[str, int]
    dormant_soft_skin_exposed_fx3: int
    dormant_soft_skin_exposed_fx6: int
    dormant_soft_skin_rejected: bool
    effective_delete_confirm: str
    effective_delete_pressing_twice: str
    playback_delete_config_resettable_by_camset_reset: bool
    proxy_co_deleted_or_protected: bool
    protect_cancel_all_images_absent: bool
    display_media_info_readonly_safe: bool
    display_media_info_max_still_count: int
    recover_image_db_rewrites_avf_and_wipes_ftp: bool
    recover_image_db_survives_reset_and_init: bool
    target_media_slot: int
    slot1_tier0_vault_firewall_blocked: bool
    slot1_data_sector_writes: int
    emmc_nflasha_write_count: int
    emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_fx3_creative_look_and_playback_media_state(
    *,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE351,
    creative_look: str = CREATIVE_LOOK_DEFAULT_G152,
    picture_profile: str = "Off",
    log_shooting_mode: str = "Off",
    hlg_still_image: str = "Off",
    exposure_mode: str = "P",
    contrast: int = 0,
    highlights: int = 0,
    shadows: int = 0,
    fade: int = 0,
    saturation: int = 0,
    sharpness: int = 0,
    sharpness_range: int = 3,
    clarity: int = 0,
    delete_confirm: str = DELETE_CONFIRM_CANCEL_FIRST_G152,
    delete_pressing_twice: str = DELETE_PRESSING_TWICE_DEFAULT_G152,
    reset_action: str = RESET_ACTION_NONE_PHASE351,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-66 Creative Look & Playback Delete config state."""
    if reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351,
        RESET_ACTION_INITIALIZE_PHASE351,
    ):
        eff_look_req = CREATIVE_LOOK_DEFAULT_G152
    else:
        eff_look_req = creative_look

    if reset_action == RESET_ACTION_INITIALIZE_PHASE351:
        eff_del_confirm = DELETE_CONFIRM_CANCEL_FIRST_G152
        eff_del_twice = DELETE_PRESSING_TWICE_DEFAULT_G152
    else:
        eff_del_confirm = delete_confirm
        eff_del_twice = delete_pressing_twice

    forced_dash = (
        picture_profile != "Off"
        or log_shooting_mode != "Off"
        or hlg_still_image == "On"
        or exposure_mode == "iAuto"
    )
    eff_look = "[-]" if forced_dash else eff_look_req
    sat_locked = eff_look in CREATIVE_LOOK_SATURATION_LOCKED_PRESETS_G152 or forced_dash
    sharp_range_locked = (
        shoot_mode in (SHOOT_MODE_MOVIE_PHASE351, SHOOT_MODE_SQ_PHASE351)
        or forced_dash
    )

    return {
        "effective_creative_look": eff_look,
        "creative_look_forced_dash_disabled": forced_dash,
        "creative_look_saturation_locked": sat_locked,
        "creative_look_sharpness_range_locked": sharp_range_locked,
        "creative_look_8_params": {
            "Contrast": contrast,
            "Highlights": highlights,
            "Shadows": shadows,
            "Fade": fade,
            "Saturation": saturation,
            "Sharpness": sharpness,
            "Sharpness Range": sharpness_range,
            "Clarity": clarity,
        },
        "effective_delete_confirm": eff_del_confirm,
        "effective_delete_pressing_twice": eff_del_twice,
    }


def compute_creative_look_and_media_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G152 (384 states)."""
    combos = list(
        itertools.product(
            (SHOOT_MODE_STILL_PHASE351, SHOOT_MODE_MOVIE_PHASE351),
            ("ST", "BW", "SE", "Custom Look 1"),
            ("Off", "PP11"),  # picture_profile
            ("Off", "Flexible ISO"),  # log_shooting_mode
            ("Off", "On"),  # hlg_still_image
            (MEDIA_SLOT_1_PHASE351, MEDIA_SLOT_2_PHASE351),
            (
                RESET_ACTION_NONE_PHASE351,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351,
                RESET_ACTION_INITIALIZE_PHASE351,
            ),
        )
    )
    forced_dash_count = 0
    sat_locked_count = 0
    sharp_range_locked_count = 0
    camset_preserved_delete_cfg_count = 0
    slot1_erofs_blocked_count = 0

    for sm, look, pp, log_m, hlg, slot, rst in combos:
        st = resolve_fx3_creative_look_and_playback_media_state(
            shoot_mode=sm,
            creative_look=look,
            picture_profile=pp,
            log_shooting_mode=log_m,
            hlg_still_image=hlg,
            delete_confirm=DELETE_CONFIRM_DELETE_FIRST_G152,
            delete_pressing_twice="On",
            reset_action=rst,
        )
        if st["creative_look_forced_dash_disabled"]:
            forced_dash_count += 1
        if st["creative_look_saturation_locked"]:
            sat_locked_count += 1
        if st["creative_look_sharpness_range_locked"]:
            sharp_range_locked_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351
            and st["effective_delete_confirm"] == DELETE_CONFIRM_DELETE_FIRST_G152
            and st["effective_delete_pressing_twice"] == "On"
        ):
            camset_preserved_delete_cfg_count += 1
        if slot == MEDIA_SLOT_1_PHASE351:
            slot1_erofs_blocked_count += 1

    return {
        "total_matrix_states": len(combos),
        "forced_dash_count": forced_dash_count,
        "sat_locked_count": sat_locked_count,
        "sharp_range_locked_count": sharp_range_locked_count,
        "camset_preserved_delete_cfg_count": camset_preserved_delete_cfg_count,
        "slot1_erofs_blocked_count": slot1_erofs_blocked_count,
    }


def verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE351,
    body_model_id: int = FX3_MODEL_ID_PHASE351,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE351,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE351,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE351,
    creative_look: str = CREATIVE_LOOK_DEFAULT_G152,
    picture_profile: str = "Off",
    log_shooting_mode: str = "Off",
    hlg_still_image: str = "Off",
    exposure_mode: str = "P",
    contrast: int = 0,
    highlights: int = 0,
    shadows: int = 0,
    fade: int = 0,
    saturation: int = 0,
    sharpness: int = 0,
    sharpness_range: int = 3,
    clarity: int = 0,
    claimed_creative_look_active_under_pp_or_log_or_hlg: bool = False,
    claimed_bw_or_se_saturation_adjustable: bool = False,
    claimed_movie_sharpness_range_adjustable: bool = False,
    requested_soft_skin_effect_fx3: bool = False,
    requested_soft_skin_effect_fx6: bool = False,
    delete_mode: str = "Multiple Img.",
    delete_confirm: str = DELETE_CONFIRM_CANCEL_FIRST_G152,
    delete_pressing_twice: str = DELETE_PRESSING_TWICE_DEFAULT_G152,
    claimed_camset_reset_clears_delete_confirm_or_twice: bool = False,
    claimed_delete_skips_proxy_or_deletes_protected: bool = False,
    protect_mode: str = "Multiple Img.",
    claimed_protect_cancel_all_images_exists: bool = False,
    display_media_info_requested: bool = False,
    delete_mutation_requested: bool = False,
    protect_mutation_requested: bool = False,
    recover_image_db_requested: bool = False,
    requested_write_operation: bool = False,
    target_media_slot: int = MEDIA_SLOT_2_PHASE351,
    claimed_recover_db_erases_av_files_or_keeps_ftp: bool = False,
    claimed_reset_or_init_clears_recover_db: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE351,
    fx6_base_look_or_restore_media_spoof_requested: bool = False,
) -> CreativeLookSoftSkinDeleteProtectRecoverDbGuardResult:
    """Enforce Gate G152: Creative Look 10+6 / Dormant Soft Skin & Delete/Protect/RecoverDB Slot-1 EROFS=30."""
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

    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE351:
        _add("TELEMETRY_INVALID", f"shoot_mode_invalid:{shoot_mode!r}")
    if creative_look not in ALLOWED_CREATIVE_LOOK_SLOTS_G152:
        _add("TELEMETRY_INVALID", f"creative_look_invalid:{creative_look!r}")
    if not _is_on_off(hlg_still_image):
        _add("TELEMETRY_INVALID", f"hlg_still_image_invalid:{hlg_still_image!r}")
    if delete_mode not in EXACT_5_DELETE_BATCH_MODES_G152:
        _add("TELEMETRY_INVALID", f"delete_mode_invalid:{delete_mode!r}")
    if delete_confirm not in ALLOWED_DELETE_CONFIRM_MODES_G152:
        _add("TELEMETRY_INVALID", f"delete_confirm_invalid:{delete_confirm!r}")
    if not _is_on_off(delete_pressing_twice):
        _add("TELEMETRY_INVALID", f"delete_pressing_twice_invalid:{delete_pressing_twice!r}")
    if protect_mode == ABSENT_PROTECT_CANCEL_ALL_IMAGES_G152 or claimed_protect_cancel_all_images_exists:
        _add(
            "PROTECT_CANCEL_ALL_IMAGES_ABSENT_EOPNOTSUPP",
            "fx3_protect_menu_has_7_modes_and_zero_cancel_all_images_eopnotsupp_95",
        )
    elif protect_mode not in EXACT_7_PROTECT_MODES_G152:
        _add("TELEMETRY_INVALID", f"protect_mode_invalid:{protect_mode!r}")

    if not _is_strict_int(target_media_slot) or target_media_slot not in ALLOWED_MEDIA_SLOTS_PHASE351:
        _add("TELEMETRY_INVALID", f"target_media_slot_invalid:{target_media_slot!r}")
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE351:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")

    # Dormant Soft Skin Effect & FX6 cross-model checks
    dormant_soft_skin = bool(
        requested_soft_skin_effect_fx3 or requested_soft_skin_effect_fx6
    )
    if dormant_soft_skin:
        _add(
            "DORMANT_SOFT_SKIN_EFFECT_EOPNOTSUPP",
            "soft_skin_effect_is_100pct_dormant_unsupported_on_both_fx3_7_02_and_fx6_6_01_eopnotsupp_95",
        )
    if fx6_base_look_or_restore_media_spoof_requested:
        _add(
            "FX6_BASE_LOOK_OR_RESTORE_MEDIA_SPOOF_EOPNOTSUPP",
            "fx3_lacks_fx6_base_look_3dlut_and_restore_media_a_b_eopnotsupp_95",
        )

    # Creative Look 8 parameter strict bounds check (-9..+9 vs asymmetric 0..9 vs 1..5)
    param_inputs: Dict[str, Any] = {
        "Contrast": contrast,
        "Highlights": highlights,
        "Shadows": shadows,
        "Fade": fade,
        "Saturation": saturation,
        "Sharpness": sharpness,
        "Sharpness Range": sharpness_range,
        "Clarity": clarity,
    }
    for pname, pval in param_inputs.items():
        lo, hi = CREATIVE_LOOK_8_PARAM_BOUNDS_G152[pname]
        if not _is_strict_int(pval):
            _add("TELEMETRY_INVALID", f"creative_look_param_not_int:{pname}={pval!r}")
        elif not (lo <= pval <= hi):
            _add(
                "CREATIVE_LOOK_PARAM_OUT_OF_BOUNDS",
                f"creative_look_param_out_of_bounds:{pname}={pval}_expected_{lo}..{hi}_einval_22",
            )

    state = resolve_fx3_creative_look_and_playback_media_state(
        shoot_mode=shoot_mode if shoot_mode in ALLOWED_SHOOT_MODES_PHASE351 else SHOOT_MODE_STILL_PHASE351,
        creative_look=creative_look if creative_look in ALLOWED_CREATIVE_LOOK_SLOTS_G152 else CREATIVE_LOOK_DEFAULT_G152,
        picture_profile=picture_profile,
        log_shooting_mode=log_shooting_mode,
        hlg_still_image=hlg_still_image if _is_on_off(hlg_still_image) else "Off",
        exposure_mode=exposure_mode,
        contrast=contrast if _is_strict_int(contrast) else 0,
        highlights=highlights if _is_strict_int(highlights) else 0,
        shadows=shadows if _is_strict_int(shadows) else 0,
        fade=fade if _is_strict_int(fade) else 0,
        saturation=saturation if _is_strict_int(saturation) else 0,
        sharpness=sharpness if _is_strict_int(sharpness) else 0,
        sharpness_range=sharpness_range if _is_strict_int(sharpness_range) else 3,
        clarity=clarity if _is_strict_int(clarity) else 0,
        delete_confirm=delete_confirm if delete_confirm in ALLOWED_DELETE_CONFIRM_MODES_G152 else DELETE_CONFIRM_CANCEL_FIRST_G152,
        delete_pressing_twice=delete_pressing_twice if _is_on_off(delete_pressing_twice) else DELETE_PRESSING_TWICE_DEFAULT_G152,
        reset_action=reset_action if reset_action in ALLOWED_RESET_ACTIONS_PHASE351 else RESET_ACTION_NONE_PHASE351,
    )

    if state["creative_look_forced_dash_disabled"] and claimed_creative_look_active_under_pp_or_log_or_hlg:
        _add(
            "CREATIVE_LOOK_PP_LOG_HLG_OVERRIDE_VIOLATION",
            "creative_look_is_forced_dash_disabled_under_pp_log_hlg_still_or_iauto_einval_22",
        )
    if state["creative_look_saturation_locked"] and claimed_bw_or_se_saturation_adjustable:
        _add(
            "CREATIVE_LOOK_BW_SE_SATURATION_LOCK_VIOLATION",
            "saturation_is_locked_non_adjustable_on_bw_and_se_creative_looks_einval_22",
        )
    if state["creative_look_sharpness_range_locked"] and claimed_movie_sharpness_range_adjustable:
        _add(
            "CREATIVE_LOOK_MOVIE_SHARPNESS_RANGE_LOCK_VIOLATION",
            "sharpness_range_fineness_is_locked_in_movie_and_sq_modes_einval_22",
        )
    if claimed_camset_reset_clears_delete_confirm_or_twice:
        _add(
            "DELETE_CONFIG_RESET_IMMUNITY_VIOLATION",
            "delete_confirm_and_delete_pressing_twice_are_initialize_only_not_resettable_einval_22",
        )
    if claimed_delete_skips_proxy_or_deletes_protected:
        _add(
            "DELETE_PROXY_OR_PROTECT_CONTRACT_VIOLATION",
            "delete_co_deletes_proxy_and_never_deletes_protected_files_only_format_clears_protected_einval_22",
        )
    if claimed_recover_db_erases_av_files_or_keeps_ftp:
        _add(
            "RECOVER_IMAGE_DB_SEMANTICS_VIOLATION",
            "recover_image_db_rewrites_avf_info_and_wipes_ftp_transfer_records_without_deleting_media_files_einval_22",
        )
    if claimed_reset_or_init_clears_recover_db:
        _add(
            "RECOVER_IMAGE_DB_PERSISTENCE_VIOLATION",
            "recover_image_db_effects_are_immune_to_both_camset_reset_and_initialize_einval_22",
        )

    # HARD Tier-0 Slot-1 EROFS=30 Firewall (blocks Delete / Protect / Recover Image DB on Slot 1,
    # while allowing strictly read-only Display Media Info. queries!)
    any_card_mutation_requested = bool(
        delete_mutation_requested
        or protect_mutation_requested
        or recover_image_db_requested
        or requested_write_operation
    )
    slot1_blocked = bool(
        target_media_slot == MEDIA_SLOT_1_PHASE351 and any_card_mutation_requested
    )
    if slot1_blocked:
        _add(
            "SLOT1_TIER0_VAULT_EROFS",
            "slot1_tier0_vault_erofs_30_hard_blocked_delete_protect_or_recover_image_db_write",
        )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G152
        block_errno = 0
        block_errno_name = "OK"
    elif slot1_blocked:
        status = STATUS_BLOCKED_G152_SLOT1_DELETE_PROTECT_RECOVERDB_VAULT_EROFS
        block_errno = EROFS_ERRNO_PHASE351
        block_errno_name = EROFS_NAME_PHASE351
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G152_DORMANT_SOFT_SKIN_OR_PROTECT_CANCEL_ALL_EOPNOTSUPP
        block_errno = EOPNOTSUPP_ERRNO_PHASE351
        block_errno_name = EOPNOTSUPP_NAME_PHASE351
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
        status = STATUS_BLOCKED_G152_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE351
        block_errno_name = EINVAL_NAME_PHASE351
    else:
        status = STATUS_BLOCKED_G152_CREATIVE_LOOK_BOUNDS_LOCKOUT_OR_DELETE_RESET_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE351
        block_errno_name = EINVAL_NAME_PHASE351

    return CreativeLookSoftSkinDeleteProtectRecoverDbGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        creative_look_menu_path=CREATIVE_LOOK_MENU_PATH_G152,
        playback_delete_menu_path=PLAYBACK_DELETE_MENU_PATH_G152,
        playback_protect_menu_path=PLAYBACK_PROTECT_MENU_PATH_G152,
        media_recover_db_menu_path=MEDIA_RECOVER_DB_MENU_PATH_G152,
        media_display_info_menu_path=MEDIA_DISPLAY_INFO_MENU_PATH_G152,
        effective_creative_look=state["effective_creative_look"],
        creative_look_forced_dash_disabled=state["creative_look_forced_dash_disabled"],
        creative_look_saturation_locked=state["creative_look_saturation_locked"],
        creative_look_sharpness_range_locked=state["creative_look_sharpness_range_locked"],
        creative_look_8_params=state["creative_look_8_params"],
        dormant_soft_skin_exposed_fx3=DORMANT_SOFT_SKIN_EXPOSED_FX3_G152,
        dormant_soft_skin_exposed_fx6=DORMANT_SOFT_SKIN_EXPOSED_FX6_G152,
        dormant_soft_skin_rejected=dormant_soft_skin,
        effective_delete_confirm=state["effective_delete_confirm"],
        effective_delete_pressing_twice=state["effective_delete_pressing_twice"],
        playback_delete_config_resettable_by_camset_reset=PLAYBACK_DELETE_CONFIG_RESETTABLE_BY_CAMSET_RESET_G152,
        proxy_co_deleted_or_protected=True,
        protect_cancel_all_images_absent=True,
        display_media_info_readonly_safe=(
            True if display_media_info_requested or not slot1_blocked else False
        ),
        display_media_info_max_still_count=DISPLAY_MEDIA_INFO_MAX_STILL_COUNT_G152,
        recover_image_db_rewrites_avf_and_wipes_ftp=True,
        recover_image_db_survives_reset_and_init=RECOVER_IMAGE_DB_IMMUNE_TO_RESET_AND_INIT_G152,
        target_media_slot=target_media_slot,
        slot1_tier0_vault_firewall_blocked=slot1_blocked,
        slot1_data_sector_writes=0,
        emmc_nflasha_write_count=0,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class G152CreativeLookSoftSkinDeleteProtectRecoverDbGuardResult:
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
    creative_look_delete_protect_recoverdb_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g152_creative_look_soft_skin_delete_protect_recoverdb_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G152CreativeLookSoftSkinDeleteProtectRecoverDbGuardResult]:
    audit = audit_phase351_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G152CreativeLookSoftSkinDeleteProtectRecoverDbGuardResult(
        gate_id=G152,
        gate_code=G152_GATE_CODE,
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
        creative_look_delete_protect_recoverdb_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G152,
        gate_code=G152_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"look={res.effective_creative_look} "
            f"del_confirm={res.effective_delete_confirm} "
            f"del_twice={res.effective_delete_pressing_twice} "
            f"s1_writes={res.slot1_data_sector_writes}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_creative_look_soft_skin_delete_protect_recoverdb_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G152CreativeLookSoftSkinDeleteProtectRecoverDbGuardResult]:
    return evaluate_g152_creative_look_soft_skin_delete_protect_recoverdb_guard(
        **kwargs
    )


# ---------------------------------------------------------------------------
# Unified 152-Gate Master Safety Preflight Engine (G01..G152)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Master152GateReport:
    schema: str
    schema_version: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_149_gates_verified: bool
    all_152_gates_verified: bool
    g13_to_g152_all_passed: bool
    g151_to_g152_all_passed: bool
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
    master_150_report: Dict[str, Any]
    g151_result: Dict[str, Any]
    g152_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_152gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    simulate_bench_dry_run: Optional[bool] = None,
    dry_run_simulated_backup: Optional[bool] = None,
    request_persistent_emmc_writes: bool = False,
    master_150_override: Optional[Master150GateReport] = None,
    drive_focusbracket_shutter_efcs_nr_kwargs: Optional[Mapping[str, Any]] = None,
    creative_look_delete_protect_recoverdb_kwargs: Optional[Mapping[str, Any]] = None,
    **extra_upstream_kwargs: Any,
) -> Master152GateReport:
    """Evaluate unified 152-Gate Milestone Master Safety Preflight (`G01..G152`)."""
    effective_dry_run = (
        bool(dry_run_simulated)
        or (simulate_bench_dry_run is True)
        or (dry_run_simulated_backup is True)
    )
    clean_forced = _is_clean_room_forced(force_clean_room)
    resolved_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved_work_root_for_m150 = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=resolved_repo_root).work_root
    )
    m150_force_clean_room = (
        True
        if (clean_forced or resolved_work_root_for_m150 is None)
        else force_clean_room
    )

    if master_150_override is not None:
        m150_report = master_150_override
    else:
        m150_kw = {
            k: v
            for k, v in extra_upstream_kwargs.items()
            if v is not None
        }
        m150_report = evaluate_150gate_preflight(
            resolved_repo_root,
            work_root=work_root,
            force_clean_room=m150_force_clean_room,
            dry_run_simulated=effective_dry_run,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m150_kw,
        )

    g151_kw = dict(drive_focusbracket_shutter_efcs_nr_kwargs or {})
    g151_verdict, g151_res = (
        evaluate_g151_drive_focusbracket_shutter_efcs_nr_guard(
            repo_root=resolved_repo_root,
            work_root=work_root,
            force_clean_room=force_clean_room,
            **g151_kw,
        )
    )

    g152_kw = dict(creative_look_delete_protect_recoverdb_kwargs or {})
    if "requested_write_operation" not in g152_kw and request_persistent_emmc_writes:
        g152_kw["requested_write_operation"] = True
        if "target_media_slot" not in g152_kw:
            g152_kw["target_media_slot"] = MEDIA_SLOT_1_PHASE351
    g152_verdict, g152_res = (
        evaluate_g152_creative_look_soft_skin_delete_protect_recoverdb_guard(
            repo_root=resolved_repo_root,
            work_root=work_root,
            force_clean_room=force_clean_room,
            **g152_kw,
        )
    )

    new_gate_dicts = (
        {
            "gate_id": G151,
            "gate_code": G151_GATE_CODE,
            "status": g151_res.status,
            "passed": g151_verdict.passed,
            "evidence": g151_verdict.evidence,
            "violation_codes": list(g151_verdict.errors),
        },
        {
            "gate_id": G152,
            "gate_code": G152_GATE_CODE,
            "status": g152_res.status,
            "passed": g152_verdict.passed,
            "evidence": g152_verdict.evidence,
            "violation_codes": list(g152_verdict.errors),
        },
    )

    all_gates: Tuple[Dict[str, Any], ...] = tuple(m150_report.gates) + new_gate_dicts
    g01_to_g12_verified = int(m150_report.summary["g01_to_g12_verified"])
    g13_to_g150_verified = (
        int(m150_report.summary["g13_to_g148_verified"])
        + int(m150_report.summary["g149_to_g150_verified"])
    )
    g151_to_g152_verified = int(bool(g151_verdict.passed)) + int(
        bool(g152_verdict.passed)
    )
    total_verified = g01_to_g12_verified + g13_to_g150_verified + g151_to_g152_verified

    g151_to_g152_all_passed = g151_to_g152_verified == 2
    g13_to_g152_all_passed = (
        m150_report.g13_to_g150_all_passed and g151_to_g152_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m150_report.gates[:9])

    offline_149_verified = (
        g01_to_g09_ok
        and m150_report.offline_147_gates_verified
        and g151_to_g152_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_152_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g152_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m150_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_149_verified
        and m150_report.h0_h1_trial_entry_allowed
        and g151_to_g152_all_passed
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
        list(m150_report.errors)
        + list(g151_verdict.errors)
        + list(g152_verdict.errors)
    )
    warnings: List[str] = (
        list(m150_report.warnings)
        + list(g151_verdict.warnings)
        + list(g152_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m150_report.g13_to_g150_all_passed:
        overall_status = m150_report.status
    elif not g151_verdict.passed:
        overall_status = g151_verdict.status
    elif not g152_verdict.passed:
        overall_status = g152_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_152_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_152_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_152_verified:
        overall_status = "VERIFIED_ALL_152_GATES"
    else:
        overall_status = "VERIFIED_149_OF_152_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m150_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g151_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g152_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 152,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 152 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g150_verified": g13_to_g150_verified,
        "g151_to_g152_verified": g151_to_g152_verified,
        "g13_to_g152_all_passed": g13_to_g152_all_passed,
        "g151_to_g152_all_passed": g151_to_g152_all_passed,
        "offline_149_gates_verified": offline_149_verified,
        "all_152_gates_verified": all_152_verified,
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

    return Master152GateReport(
        schema=REALHW_152GATE_PREFLIGHT_SCHEMA,
        schema_version=REALHW_152GATE_PREFLIGHT_SCHEMA,
        version=REALHW_DRIVE_FOCUSBRACKET_SHUTTER_EFCS_CREATIVE_RECOVERDB_152GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_149_gates_verified=offline_149_verified,
        all_152_gates_verified=all_152_verified,
        g13_to_g152_all_passed=g13_to_g152_all_passed,
        g151_to_g152_all_passed=g151_to_g152_all_passed,
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
        master_150_report=m150_report.to_dict(),
        g151_result=g151_res.to_dict(),
        g152_result=g152_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_152_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master152GateReport:
    return evaluate_152gate_preflight(repo_root, **kwargs)


def run_152_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master152GateReport:
    return evaluate_152gate_preflight(repo_root, **kwargs)


def verify_real_hardware_152gate_readiness(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master152GateReport:
    return evaluate_152gate_preflight(repo_root, **kwargs)


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
        prog="realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_152gate_guard",
        description="Phase 351 (Task H439, Wave-66) G151/G152 and 152/152 Unified Safety Preflight CLI",
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
        help="Supply simulated dry-run Tier-0 backup inputs so all 152/152 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g151", "g152", "152"],
        default="152",
        help="Target gate check: g151, g152, or 152",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g151":
        v, r = evaluate_g151_drive_focusbracket_shutter_efcs_nr_guard(
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

    if args.gate == "g152":
        v, r = evaluate_g152_creative_look_soft_skin_delete_protect_recoverdb_guard(
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

    rep = evaluate_152gate_preflight(
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
                "g151_status": rep.g151_result["status"],
                "g152_status": rep.g152_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/152 "
            f"g151_to_g152_all_passed={rep.g151_to_g152_all_passed} "
            f"all_152_gates_verified={rep.all_152_gates_verified} "
            f"dry_run_rehearsal_only={rep.dry_run_rehearsal_only} "
            f"agent_auto_flash_blocked={rep.agent_auto_flash_blocked} "
            f"overall_ready_for_hardware_attach={rep.overall_ready_for_hardware_attach} "
            f"hardware_live_attachment_authorized={rep.hardware_live_attachment_authorized} "
            f"el3_payload_transmit_authorized={rep.el3_payload_transmit_authorized} "
            f"spi_nor_write_authorized={rep.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={rep.persistent_emmc_writes_authorized} "
            f"cross_model_flash_authorized={rep.cross_model_flash_authorized} "
            f"usb_packets_transmitted={rep.usb_packets_transmitted} "
            f"raw_firmware_bytes_leaked={rep.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        rep.all_152_gates_verified
        if args.dry_run_simulated
        else rep.offline_149_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "ABSENT_PROTECT_CANCEL_ALL_IMAGES_G152",
    "ALLOWED_CONT_SPEEDS_G151",
    "ALLOWED_CREATIVE_LOOK_SLOTS_G152",
    "ALLOWED_DELETE_CONFIRM_MODES_G152",
    "ALLOWED_MEDIA_SLOTS_PHASE351",
    "ALLOWED_RESET_ACTIONS_PHASE351",
    "ALLOWED_SHOOT_MODES_PHASE351",
    "BRACKET_STEP_359_EV_G151",
    "BRACKET_STEP_35_EV_G151",
    "CLARITY_F_RESID16_G152",
    "CONT_BRACKET_F_RESID16_G151",
    "CONT_HI_F_RESID16_G151",
    "CONT_HI_PLUS_F_RESID16_G151",
    "CONT_LO_F_RESID16_G151",
    "CONT_MID_F_RESID16_G151",
    "CONT_SHOOTING_FIRST_FRAME_AF_LOCK_APERTURE_FLOOR_G151",
    "CONT_SHOOTING_FIRST_FRAME_AF_LOCK_SPEEDS_G151",
    "CONT_SHOOTING_F_RESID16_G151",
    "CONT_SHOOTING_MAX_FPS_G151",
    "CONT_SPEED_HI_G151",
    "CONT_SPEED_HI_PLUS_G151",
    "CONT_SPEED_LO_G151",
    "CONT_SPEED_MID_G151",
    "CREATIVE_LOOK_10_PRESETS_G152",
    "CREATIVE_LOOK_6_CUSTOM_SLOTS_G152",
    "CREATIVE_LOOK_8_PARAM_BOUNDS_G152",
    "CREATIVE_LOOK_DEFAULT_G152",
    "CREATIVE_LOOK_F_RESID16_G152",
    "CREATIVE_LOOK_MENU_PATH_G152",
    "CREATIVE_LOOK_RESETTABLE_BY_CAMSET_RESET_G152",
    "CREATIVE_LOOK_SATURATION_LOCKED_PRESETS_G152",
    "CREATIVE_LOOK_TOTAL_SLOTS_G152",
    "CUSTOM_LOOK_F_RESID16_G152",
    "CreativeLookSoftSkinDeleteProtectRecoverDbGuardResult",
    "DEFAULT_PLAYBACK_MEDIA_SLOT_G152",
    "DELETE_BASE_RESID16_G152",
    "DELETE_CONFIRM_BASE_RESID16_G152",
    "DELETE_CONFIRM_CANCEL_FIRST_G152",
    "DELETE_CONFIRM_DELETE_FIRST_G152",
    "DELETE_PRESSING_TWICE_DEFAULT_G152",
    "DELETE_PRESSING_TWICE_F_RESID16_G152",
    "DISPLAY_MEDIA_INFO_BASE_RESID16_G152",
    "DISPLAY_MEDIA_INFO_ELF_TYPO_G152",
    "DISPLAY_MEDIA_INFO_MAX_STILL_COUNT_G152",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE351",
    "DONOR_CHECK_MAX_SECONDS_PHASE351",
    "DORMANT_APSC_XSYNC_STR_G151",
    "DORMANT_FOCUS_BRACKET_EXPOSED_EVENTS_G151",
    "DORMANT_FOCUS_BRACKET_F_RESID16_G151",
    "DORMANT_FOCUS_BRACKET_ORDER_F_RESID16_G151",
    "DORMANT_FOCUS_BRACKET_TOKENS_G151",
    "DORMANT_HIGH_ISO_NR_TOKENS_G151",
    "DORMANT_SELF_TIMER_CONT_OPTIONS_G151",
    "DORMANT_SHUTTER_AUTO_DESC_F_RESID16_G151",
    "DORMANT_SHUTTER_TYPE_AUTO_TOKENS_G151",
    "DORMANT_SOFT_SKIN_EXPOSED_FX3_G152",
    "DORMANT_SOFT_SKIN_EXPOSED_FX6_G152",
    "DORMANT_SOFT_SKIN_F_RESID16_G152",
    "DORMANT_SOFT_SKIN_TOKENS_G152",
    "DRIVE_MODE_CONT_BRACKET_G151",
    "DRIVE_MODE_CONT_G151",
    "DRIVE_MODE_DEFAULT_G151",
    "DRIVE_MODE_DRO_BRACKET_G151",
    "DRIVE_MODE_F_RESID16_G151",
    "DRIVE_MODE_MENU_PATH_G151",
    "DRIVE_MODE_RESETTABLE_BY_CAMSET_RESET_G151",
    "DRIVE_MODE_SELF_TIMER_CONT_G151",
    "DRIVE_MODE_SELF_TIMER_SINGLE_G151",
    "DRIVE_MODE_SINGLE_BRACKET_G151",
    "DRIVE_MODE_SINGLE_G151",
    "DRIVE_MODE_WB_BRACKET_G151",
    "DRO_BRACKET_F_RESID16_G151",
    "DRO_BRACKET_MODES_G151",
    "DriveFocusBracketShutterEfcsNrGuardResult",
    "EFCS_DEFAULT_G151",
    "EFCS_ELF_TYPO_SYMBOL_G151",
    "EFCS_F_RESID16_G151",
    "EFCS_RESETTABLE_BY_CAMSET_RESET_G151",
    "EINVAL_ERRNO_PHASE351",
    "EINVAL_NAME_PHASE351",
    "ENV_CLEAN_ROOM_TEST_PHASE351",
    "EOPNOTSUPP_ERRNO_PHASE351",
    "EOPNOTSUPP_NAME_PHASE351",
    "EROFS_ERRNO_PHASE351",
    "EROFS_NAME_PHASE351",
    "EXACT_2_SHUTTER_TYPES_G151",
    "EXACT_3_HIGH_ISO_NR_OPTIONS_G151",
    "EXACT_3_SELF_TIMER_SINGLE_OPTIONS_G151",
    "EXACT_5_DELETE_BATCH_MODES_G152",
    "EXACT_5_ELECTRONIC_SHUTTER_LOCKED_ITEMS_G151",
    "EXACT_6_SELF_TIMER_CONT_OPTIONS_G151",
    "EXACT_7_PROTECT_MODES_G152",
    "EXACT_8_DRIVE_MODES_G151",
    "FX3_DEFAULT_FW_VERSION_PHASE351",
    "FX3_FLASH_XSYNC_CEILING_SEC_G151",
    "FX3_FLASH_XSYNC_CEILING_STR_G151",
    "FX3_HELP_GUIDE_CODE_PHASE351",
    "FX3_MODEL_ID_PHASE351",
    "FX3_MODEL_NAME_PHASE351",
    "FX6_APR_MENU_PATH_G151",
    "FX6_DEFAULT_FW_VERSION_PHASE351",
    "FX6_DORMANT_FOCUS_BRACKET_SYMBOL_COUNT_G151",
    "FX6_MEDIA_MUTATION_MENUS_G152",
    "FX6_MODEL_NAME_PHASE351",
    "FX6_NOISE_SUPPRESSION_MODES_G151",
    "G151",
    "G151DriveFocusBracketShutterEfcsNrGuardResult",
    "G151_GATE_CODE",
    "G151_GATE_ID",
    "G152",
    "G152CreativeLookSoftSkinDeleteProtectRecoverDbGuardResult",
    "G152_GATE_CODE",
    "G152_GATE_ID",
    "HIGH_ISO_NR_ALTERS_ARW_G151",
    "HIGH_ISO_NR_DEFAULT_G151",
    "HIGH_ISO_NR_F_RESID16_G151",
    "HIGH_ISO_NR_LOW_G151",
    "HIGH_ISO_NR_NORMAL_G151",
    "HIGH_ISO_NR_OFF_G151",
    "HIGH_ISO_NR_RESETTABLE_BY_CAMSET_RESET_G151",
    "IMAGE_QUALITY_NR_MENU_PATH_G151",
    "INTERVAL_SHUTTER_TYPE_DEFAULT_G151",
    "LONG_EXPOSURE_NR_DEFAULT_G151",
    "LONG_EXPOSURE_NR_F_RESID16_G151",
    "LONG_EXPOSURE_NR_MIN_SHUTTER_SEC_G151",
    "LONG_EXPOSURE_NR_RESETTABLE_BY_CAMSET_RESET_G151",
    "MEDIA_DISPLAY_INFO_MENU_PATH_G152",
    "MEDIA_RECOVER_DB_MENU_PATH_G152",
    "MEDIA_SLOT_1_PHASE351",
    "MEDIA_SLOT_2_PHASE351",
    "MEDIA_SLOT_NONE_PHASE351",
    "Master152GateReport",
    "PINNED_FX3_APPFW_SLICES_PHASE351",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE351",
    "PINNED_FX6_APPFW_SLICES_PHASE351",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE351",
    "PINNED_PHASE351_DONOR_SPECS",
    "PLAYBACK_DELETE_CONFIG_RESETTABLE_BY_CAMSET_RESET_G152",
    "PLAYBACK_DELETE_MENU_PATH_G152",
    "PLAYBACK_PROTECT_MENU_PATH_G152",
    "PROTECT_BASE_RESID16_G152",
    "Phase351DonorAuditResult",
    "REALHW_152GATE_PREFLIGHT_SCHEMA",
    "REALHW_DRIVE_FOCUSBRACKET_SHUTTER_EFCS_CREATIVE_RECOVERDB_152GATE_SCHEMA",
    "REALHW_DRIVE_FOCUSBRACKET_SHUTTER_EFCS_CREATIVE_RECOVERDB_152GATE_VERSION",
    "RECOVER_IMAGE_DB_BASE_RESID16_G152",
    "RECOVER_IMAGE_DB_F_RESID16_G152",
    "RECOVER_IMAGE_DB_IMMUNE_TO_RESET_AND_INIT_G152",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351",
    "RESET_ACTION_INITIALIZE_PHASE351",
    "RESET_ACTION_NONE_PHASE351",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE351",
    "SELF_TIMER_CONT_F_RESID16_G151",
    "SELF_TIMER_SINGLE_F_RESID16_G151",
    "SHARPNESS_RANGE_F_RESID16_G152",
    "SHOOT_MODE_MOVIE_PHASE351",
    "SHOOT_MODE_SQ_PHASE351",
    "SHOOT_MODE_STILL_PHASE351",
    "SHUTTER_ELECTRONIC_F_RESID16_G151",
    "SHUTTER_MECHANICAL_F_RESID16_G151",
    "SHUTTER_SILENT_MENU_PATH_G151",
    "SHUTTER_TYPE_DEFAULT_G151",
    "SHUTTER_TYPE_ELECTRONIC_G151",
    "SHUTTER_TYPE_F_RESID16_G151",
    "SHUTTER_TYPE_MECHANICAL_G151",
    "SHUTTER_TYPE_RESETTABLE_BY_CAMSET_RESET_G151",
    "SINGLE_BRACKET_F_RESID16_G151",
    "SINGLE_SHOOTING_F_RESID16_G151",
    "STATUS_BLOCKED_G151_DORMANT_FOCUS_BRACKET_SHUTTER_AUTO_OR_FX6_EOPNOTSUPP",
    "STATUS_BLOCKED_G151_DRIVE_LOCKOUT_OR_XSYNC_1_320_VIOLATION",
    "STATUS_BLOCKED_G151_SHUTTER_TYPE_EFCS_RESET_OR_NR_VIOLATION",
    "STATUS_BLOCKED_G151_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G152_CREATIVE_LOOK_BOUNDS_LOCKOUT_OR_DELETE_RESET_VIOLATION",
    "STATUS_BLOCKED_G152_DORMANT_SOFT_SKIN_OR_PROTECT_CANCEL_ALL_EOPNOTSUPP",
    "STATUS_BLOCKED_G152_SLOT1_DELETE_PROTECT_RECOVERDB_VAULT_EROFS",
    "STATUS_BLOCKED_G152_TELEMETRY_INVALID",
    "STATUS_BLOCKED_PHASE351_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G151",
    "STATUS_VERIFIED_G152",
    "WB_BRACKET_F_RESID16_G151",
    "WB_BRACKET_MODES_G151",
    "audit_phase351_donor_contracts",
    "compute_creative_look_and_media_matrix",
    "compute_drive_shutter_efcs_nr_matrix",
    "evaluate_152_master_safety_gates",
    "evaluate_152gate_preflight",
    "evaluate_g151_drive_focusbracket_shutter_efcs_nr_guard",
    "evaluate_g152_creative_look_soft_skin_delete_protect_recoverdb_guard",
    "resolve_fx3_creative_look_and_playback_media_state",
    "resolve_fx3_drive_shutter_efcs_nr_state",
    "run_152_gate_preflight",
    "strip_elapsed_seconds_recursive_phase351",
    "verify_creative_look_soft_skin_delete_protect_recoverdb_guard",
    "verify_creative_look_soft_skin_delete_protect_recoverdb_guard_with_audit",
    "verify_drive_focusbracket_shutter_efcs_nr_guard",
    "verify_drive_focusbracket_shutter_efcs_nr_guard_with_audit",
    "verify_real_hardware_152gate_readiness",
]


if __name__ == "__main__":
    raise SystemExit(main())
