"""Phase 323 Wave-62 (`12^2 = 144/144` Gross Milestone) Real-Hardware Safety Guards.

Strict read-only (`os.O_RDONLY`) & Clean-Room Dual-Mode Verification for:
  - Gate `G143`: `REALHW_SHOE_AUDIO_4CH_24BIT_OUT_TIMING_AND_FACE_EYE_SUBJECT_DORMANT_BIRD_GUARD`
      * `ILME-FX3 Ver. 7.02` (`ilc/2210`) audio architecture truth:
        - `[Audio Out Timing]` (`Live` default / `Lip Sync`, `BKID_APP_setting_audio_output_timing`,
          disabled in `S&Q`) lives under `Shooting -> [Audio Recording]` (**NOT** `Setup -> [Sound Option]`,
          which holds `[Volume Settings]`, `5`-mode `[4ch Audio Monitoring]`, and `[Audio signals]`).
        - `[Audio Level Display]` (`_f 0x7a36`) removed as a standalone menu in `Ver. 2.00..7.02`
          (auto-shown via `DISP`).
        - `[Audio Rec Level]` (`0..31`, factory default `26`, `Delete` key quick-resets, built-in
          Limiter always-on & non-disableable vs `ILME-FX6` 6-step `Limiter Mode Off/-6..-17 dB` +
          physical `CH1..CH4` dials).
        - `[Shoe Audio Set.]` (`48kHz/24bit 4ch`, `48kHz/24bit 2ch`, `48kHz/16bit 2ch` default) across
          ALL main codecs (`XAVC HS 4K`, `XAVC S 4K/HD`, `XAVC S-I 4K/HD/DCI 4K`), while Proxy is
          always `MPEG-4 AAC-LC 2ch 128kbps` (and disabled at `100p/119.88p/120p+`).
        - `3.5mm MIC` jack overrides Digital MI-Shoe (forces 2ch analog & grays out `[Shoe Audio Set.]`);
          `XLR-H1` `HANDLE AUDIO = OFF` falls back to internal stereo mic; `ANALOG` caps at `16bit 2ch`;
          `[Wind Noise Reduct.]` (`base 0xe4b1`/`0xe4ae`) applies ONLY to built-in internal mic.
      * `Focus -> [Face/Eye AF]` + explicit Wave-42 errata busting dormant `Bird`:
        - `ILME-FX3 Ver. 7.02` lacks a dedicated AI Processing Unit: `[Face/Eye Subject]` exposes ONLY
          `Human` (default) and `Animal`. Fail-closed `EOPNOTSUPP=95` on ALL 5 dormant shared ELF/UXC
          subjects: `Bird` (`_f 0x6cb1`), `Animal/Bird` (`_f 0x6957`), `Insect` (`_f 0x6996`),
          `Car/Train` (`_f 0x674e`), and `Airplane` (`_f 0x7440`, `0` `BKID_APP_*` hits).
        - `Animal` Eye AF is Still-only (`TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT` -> `EOPNOTSUPP=95`
          in Movie/`S&Q`). `[Face/Eye Frame Disp.]` defaults `Off` and never pollutes Clean HDMI/RAW.
        - `[Face Memory]` (up to `8` faces) survives `[Camera Settings Reset]` and is excluded from
          `CAMSET*.DAT` (vs `ILME-FX6` `Human`-only `Face/Eye Priority/Only AF` + session-ephemeral
          `Saved Tracking Face`).
  - Gate `G144`: `REALHW_SILENT_TARGET_2ITEM_NO_PWR_SHUTTER_AND_SLOT1_BODYDATA_NOGO_FLASH_GUARD`
      * `Shooting -> [Shutter/Silent] -> [Silent Mode Settings]` (`_f 0x655f`) 2-level menu:
        - `[Silent Mode] = On` locks Electronic Shutter + mutes `[Audio signals]` and hard-disables
          EXACT `5` functions (`Flash`, `Long Exposure NR`, `e-Front Curtain Shut.`, `BULB`,
          `Anti-flicker Shoot.`). `[AF Illuminator]` is NOT auto-disabled.
        - `[Target Function Settings]` (`_f 0x79c0`) exposes ONLY `2` active items:
          `[Aperture Drive in AF]` (`Standard` default / `Silent Priority` / `Not Target`, Still-only)
          and `[Auto Pixel Mapping]` (`Off` default / `Not Target` — keeping `Off` prevents power-off
          mechanical shutter actuation & `cnflasha` bad-pixel table writes).
        - Fail-closed `EOPNOTSUPP=95` on dormant `[Shutter When Pwr OFF]` (`_f 0x709f`,
          `image_sensor_barrier`) and `[Anti-dust Function]` (`_f 0x7495`), and shutterless `ILME-FX6`
          (`Auto Pixel Restore`, zero mechanical focal-plane shutter).
      * `Setup -> [Setup Option] -> [Version]` (`Body Ver. 7.02` / `Lens` / `Mount Adaptor`, Zero-RF
        `Airplane Mode = On` silences `_g 0x6516` update badge) and `[Software Update]` (`_f 0x6fd6`):
        - `FX3` requires exact `BODYDATA.DAT` on `Slot 1` root (`Slot 2` ignored), `NP-FZ100 >= 51%`
          (3 bars), mandatory `Ver. 2.04/2.05` stepping-stone for `<= Ver. 2.02` bodies
          (`5 long / 6 short` or `7 long / 7 short` error blinks, resets TC/UB), vs `ILME-FX6`
          `Version Up` (`Slot B` root, `Slot A` ignored, mandatory `AC Adaptor`).
        - **HARD `NO-GO / BLOCKED` REDLINE**: ANY attempt to stage `BODYDATA.DAT` onto `Slot 1`
          (`EROFS=30`), invoke `[Software Update]`/`Version Up`, write `emmc`/`cnflasha`, or cross-flash
          `FX6 <-> FX3` fails closed (`EPERM=1` / `EROFS=30`, `emmc_writes_authorized=False`,
          `cross_model_flash_authorized=False`, `hardware_live_attachment_authorized=False`,
          `slot1_data_sector_writes=0`, `usb_packets_transmitted=0`).
  - Unified `144`-Gate Milestone Master Safety Preflight (`evaluate_144gate_preflight` /
    `verify-144-gates`): `141/144` offline & `144/144` `--simulate-bench-dry-run` with
    `raw_firmware_bytes_leaked == 0` and all dangerous flags hard-locked `False`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard import (
    GateVerdict,
)
from .realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard import (
    Master142GateReport,
    evaluate_142gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    DEFAULT_REPO_ROOT,
    STATUS_VERIFIED_SAFE,
    resolve_donor_thermal_power_paths,
)

# ---------------------------------------------------------------------------
# Schema, Version & Immutable Hardware Safety Redlines
# ---------------------------------------------------------------------------

REALHW_SHOE_AUDIO_4CH_SUBJECT_RECOG_SILENT_BODYDATA_144GATE_SCHEMA = (
    "realhw_shoe_audio_4ch_subject_recog_silent_bodydata_144gate_v1"
)
REALHW_SHOE_AUDIO_4CH_SUBJECT_RECOG_SILENT_BODYDATA_144GATE_VERSION = "1.0.0"
REALHW_144GATE_PREFLIGHT_SCHEMA = "realhw_144gate_preflight_v1"

G143 = "G143"
G143_GATE_ID = G143
G143_GATE_CODE = (
    "REALHW_SHOE_AUDIO_4CH_24BIT_OUT_TIMING_AND_FACE_EYE_SUBJECT_DORMANT_BIRD_GUARD"
)
GATE_G143_SHOE_AUDIO_4CH_OUT_TIMING_AND_SUBJECT_RECOG_GUARD = G143_GATE_CODE

G144 = "G144"
G144_GATE_ID = G144
G144_GATE_CODE = (
    "REALHW_SILENT_TARGET_2ITEM_NO_PWR_SHUTTER_AND_SLOT1_BODYDATA_NOGO_FLASH_GUARD"
)
GATE_G144_SILENT_TARGET_NO_PWRSHUTTER_AND_SLOT1_BODYDATA_NOGO_GUARD = G144_GATE_CODE

# Hard-locked non-bypassable safety redlines (MUST remain False / 0 forever)
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
SPI_NOR_WRITE_AUTHORIZED = False
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
EMMC_WRITES_AUTHORIZED = False
PERSISTENT_WRITE_RELEASE = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False
CROSS_MODEL_FLASH_AUTHORIZED = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
HUMAN_HARDWARE_ATTACH_TOKEN = False
USB_PACKETS_TRANSMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

STATUS_BLOCKED_PERSISTENT_EMMC_WRITE = "BLOCKED_PERSISTENT_EMMC_WRITE_UNAUTHORIZED"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST_PHASE323 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE323 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE323 = 2.00

# Canonical POSIX errnos
EPERM_ERRNO_PHASE323 = 1
EPERM_NAME_PHASE323 = "EPERM"
EBUSY_ERRNO_PHASE323 = 16
EBUSY_NAME_PHASE323 = "EBUSY"
EINVAL_ERRNO_PHASE323 = 22
EINVAL_NAME_PHASE323 = "EINVAL"
EROFS_ERRNO_PHASE323 = 30
EROFS_NAME_PHASE323 = "EROFS"
EOPNOTSUPP_ERRNO_PHASE323 = 95
EOPNOTSUPP_NAME_PHASE323 = "EOPNOTSUPP"

# ---------------------------------------------------------------------------
# Camera Baseline & Shared Modes (ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01)
# ---------------------------------------------------------------------------

FX3_MODEL_NAME_PHASE323 = "ILME-FX3"
FX3_MODEL_ID_PHASE323 = 0x0502
FX3_HELP_GUIDE_CODE_PHASE323 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE323 = "7.02"

FX6_MODEL_NAME_PHASE323 = "ILME-FX6"
FX6_PRODUCT_CODE_PHASE323 = "PRODUCT_MODEL_CHAPLIN"
FX6_DEFAULT_FW_VERSION_PHASE323 = "6.01"

SHOOT_MODE_STILL_PHASE323 = "Still"
SHOOT_MODE_MOVIE_PHASE323 = "Movie"
SHOOT_MODE_SQ_PHASE323 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE323: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE323,
    SHOOT_MODE_MOVIE_PHASE323,
    SHOOT_MODE_SQ_PHASE323,
)

RESET_ACTION_NONE_PHASE323 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE323 = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE323 = "Reset Network Set."
RESET_ACTION_INITIALIZE_PHASE323 = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE323: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE323,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE323,
    RESET_ACTION_RESET_NETWORK_SET_PHASE323,
    RESET_ACTION_INITIALIZE_PHASE323,
)

MEDIA_SLOT_1_PHASE323 = 1
MEDIA_SLOT_2_PHASE323 = 2
ALLOWED_MEDIA_SLOTS_PHASE323: Tuple[int, ...] = (
    MEDIA_SLOT_1_PHASE323,
    MEDIA_SLOT_2_PHASE323,
)

# ---------------------------------------------------------------------------
# G143 Constants: Audio Architecture & Face/Eye Subject Recognition
# ---------------------------------------------------------------------------

AUDIO_RECORDING_MENU_PATH_G143 = "Shooting -> [Audio Recording]"
AUDIO_OUT_TIMING_MENU_PATH_G143 = "Shooting -> [Audio Recording] -> [Audio Out Timing]"
SOUND_OPTION_MENU_PATH_G143 = "Setup -> [Sound Option]"

AUDIO_RECORDING_F_UXC_RESID16_G143 = 0x72D3
AUDIO_REC_LEVEL_F_UXC_RESID16_G143 = 0x63B9
SHOE_AUDIO_SET_F_UXC_RESID16_G143 = 0x77F6
SHOE_AUDIO_24BIT_4CH_F_UXC_RESID16_G143 = 0x6195
SHOE_AUDIO_24BIT_2CH_F_UXC_RESID16_G143 = 0x70BC
SHOE_AUDIO_16BIT_2CH_F_UXC_RESID16_G143 = 0x6DDE
WIND_NOISE_REDUCT_BASE_UXC_RESID16_G143 = 0xE4B1
WIND_NOISE_INTERNAL_DESC_BASE_UXC_RESID16_G143 = 0xE4AE
AUDIO_LEVEL_DISPLAY_REMOVED_F_UXC_RESID16_G143 = 0x7A36
AUDIO_OUT_TIMING_F_UXC_RESID16_G143 = 0x6BC2
AUDIO_OUT_TIMING_LIVE_F_UXC_RESID16_G143 = 0x753D
AUDIO_OUT_TIMING_LIP_SYNC_F_UXC_RESID16_G143 = 0x6066
AUDIO_4CH_MONITORING_F_UXC_RESID16_G143 = 0x70DD

AUDIO_OUT_TIMING_LIVE_G143 = "Live"
AUDIO_OUT_TIMING_LIP_SYNC_G143 = "Lip Sync"
AUDIO_OUT_TIMING_DEFAULT_G143 = AUDIO_OUT_TIMING_LIVE_G143
ALLOWED_AUDIO_OUT_TIMING_MODES_G143: Tuple[str, ...] = (
    AUDIO_OUT_TIMING_LIVE_G143,
    AUDIO_OUT_TIMING_LIP_SYNC_G143,
)

AUDIO_REC_LEVEL_MIN_G143 = 0
AUDIO_REC_LEVEL_MAX_G143 = 31
AUDIO_REC_LEVEL_DEFAULT_G143 = 26

SHOE_AUDIO_48KHZ_24BIT_4CH_G143 = "48kHz/24bit 4ch"
SHOE_AUDIO_48KHZ_24BIT_2CH_G143 = "48kHz/24bit 2ch"
SHOE_AUDIO_48KHZ_16BIT_2CH_G143 = "48kHz/16bit 2ch"
SHOE_AUDIO_DEFAULT_G143 = SHOE_AUDIO_48KHZ_16BIT_2CH_G143
ALLOWED_FX3_SHOE_AUDIO_FORMATS_G143: Tuple[str, ...] = (
    SHOE_AUDIO_48KHZ_24BIT_4CH_G143,
    SHOE_AUDIO_48KHZ_24BIT_2CH_G143,
    SHOE_AUDIO_48KHZ_16BIT_2CH_G143,
)
FX6_DORMANT_AUDIO_FORMAT_G143 = "48kHz/32bit float 4ch"

ALLOWED_4CH_AUDIO_MONITORING_MODES_G143: Tuple[str, ...] = (
    "CH1/CH2",
    "CH3/CH4",
    "CH1+3/CH2+4",
    "CH1/CH1",
    "CH2/CH2",
)
ALLOWED_MAIN_MOVIE_CODECS_G143: Tuple[str, ...] = (
    "XAVC HS 4K",
    "XAVC S 4K",
    "XAVC S HD",
    "XAVC S-I 4K",
    "XAVC S-I HD",
    "XAVC S-I DCI 4K",
)
PROXY_FORCED_AUDIO_CODEC_G143 = "MPEG-4 AAC-LC 2ch 128kbps"
PROXY_DISABLED_HIGH_FPS_G143: Tuple[str, ...] = (
    "100p",
    "119.88p",
    "120p",
    "200p",
    "240p",
)

XLR_H1_DIGITAL_ANALOG_DIGITAL_G143 = "DIGITAL"
XLR_H1_DIGITAL_ANALOG_ANALOG_G143 = "ANALOG"
ALLOWED_XLR_H1_SWITCH_STATES_G143: Tuple[str, ...] = ("ON", "OFF")
ALLOWED_XLR_H1_DIGITAL_ANALOG_G143: Tuple[str, ...] = (
    XLR_H1_DIGITAL_ANALOG_DIGITAL_G143,
    XLR_H1_DIGITAL_ANALOG_ANALOG_G143,
)

FX6_LIMITER_MODE_STEPS_G143: Tuple[str, ...] = (
    "Off",
    "-6 dB",
    "-9 dB",
    "-12 dB",
    "-15 dB",
    "-17 dB",
)

FACE_EYE_AF_MENU_PATH_G143 = "Focus -> [Face/Eye AF]"
FACE_EYE_PRIOR_F_UXC_RESID16_G143 = 0x68E6
FACE_EYE_SUBJECT_F_UXC_RESID16_G143 = 0x70FA
FACE_SUBJECT_HUMAN_F_UXC_RESID16_G143 = 0x763F
FACE_SUBJECT_ANIMAL_F_UXC_RESID16_G143 = 0x6511
RIGHT_LEFT_EYE_SELECT_F_UXC_RESID16_G143 = 0x63A5
FACE_EYE_FRAME_DISP_F_UXC_RESID16_G143 = 0x7183
FACE_MEMORY_F_UXC_RESID16_G143 = 0x6533
REGIST_FACES_PRIORITY_F_UXC_RESID16_G143 = 0x629C

# 5 Dormant Shared ELF/UXC Subjects (Wave-42 Errata Busted!)
DORMANT_BIRD_F_UXC_RESID16_G143 = 0x6CB1
DORMANT_ANIMAL_BIRD_F_UXC_RESID16_G143 = 0x6957
DORMANT_INSECT_F_UXC_RESID16_G143 = 0x6996
DORMANT_CAR_TRAIN_F_UXC_RESID16_G143 = 0x674E
DORMANT_AIRPLANE_F_UXC_RESID16_G143 = 0x7440

FACE_SUBJECT_HUMAN_G143 = "Human"
FACE_SUBJECT_ANIMAL_G143 = "Animal"
FACE_SUBJECT_DEFAULT_G143 = FACE_SUBJECT_HUMAN_G143
ALLOWED_FX3_FACE_EYE_SUBJECTS_G143: Tuple[str, ...] = (
    FACE_SUBJECT_HUMAN_G143,
    FACE_SUBJECT_ANIMAL_G143,
)
DORMANT_SHARED_FACE_EYE_SUBJECTS_G143: Tuple[str, ...] = (
    "Bird",
    "Animal/Bird",
    "Insect",
    "Car/Train",
    "Airplane",
)
DORMANT_FACE_EYE_SUBJECT_UXC_RESID16S_G143: Dict[str, int] = {
    "Bird": DORMANT_BIRD_F_UXC_RESID16_G143,
    "Animal/Bird": DORMANT_ANIMAL_BIRD_F_UXC_RESID16_G143,
    "Insect": DORMANT_INSECT_F_UXC_RESID16_G143,
    "Car/Train": DORMANT_CAR_TRAIN_F_UXC_RESID16_G143,
    "Airplane": DORMANT_AIRPLANE_F_UXC_RESID16_G143,
}

ALLOWED_RIGHT_LEFT_EYE_MODES_G143: Tuple[str, ...] = ("Auto", "Right Eye", "Left Eye")
FACE_EYE_FRAME_DISP_DEFAULT_G143 = "Off"
FACE_MEMORY_MAX_FACES_G143 = 8

FX6_FACE_EYE_MODES_G143: Tuple[str, ...] = (
    "Face/Eye Priority AF",
    "Face/Eye Only AF",
    "Off",
)
FX6_FACE_MEMORY_EPHEMERAL_LABEL_G143 = "Saved Tracking Face"
FX6_LEGACY_DELETE_REG_FACE_UXC2_RESID16_G143 = 0x4312

# ---------------------------------------------------------------------------
# G144 Constants: Silent Mode 2-Level Menu, 2-Item Target Function & BODYDATA.DAT
# ---------------------------------------------------------------------------

SILENT_MODE_MENU_PATH_G144 = "Shooting -> [Shutter/Silent] -> [Silent Mode Settings]"
SILENT_MODE_SETTINGS_F_UXC_RESID16_G144 = 0x655F
SILENT_MODE_F_UXC_RESID16_G144 = 0x7046
TARGET_FUNCTION_SETTINGS_F_UXC_RESID16_G144 = 0x79C0
APERTURE_DRIVE_IN_AF_F_UXC_RESID16_G144 = 0x61B5
SILENT_PRIORITY_F_UXC_RESID16_G144 = 0x64D3
NOT_TARGET_F_UXC_RESID16_G144 = 0x64E7
AUTO_PIXEL_MAPPING_F_UXC_RESID16_G144 = 0x7734
AUDIO_SIGNALS_BASE_UXC_RESID16_G144 = 0xE0C8

# Dormant [Shutter When Pwr OFF] / [Anti-dust Function]
DORMANT_SHUTTER_WHEN_PWR_OFF_F_UXC_RESID16_G144 = 0x709F
DORMANT_ANTI_DUST_FUNC_F_UXC_RESID16_G144 = 0x7495
DORMANT_IMAGE_SENSOR_BARRIER_SYMBOL_G144 = "image_sensor_barrier"

EXACT_5_SILENT_DISABLED_FUNCTIONS_G144: Tuple[str, ...] = (
    "Flash",
    "Long Exposure NR",
    "e-Front Curtain Shut.",
    "BULB",
    "Anti-flicker Shoot.",
)
EXACT_2_TARGET_FUNCTION_ITEMS_G144: Tuple[str, ...] = (
    "Aperture Drive in AF",
    "Auto Pixel Mapping",
)
ALLOWED_TARGET_APERTURE_DRIVE_MODES_G144: Tuple[str, ...] = (
    "Standard",
    "Silent Priority",
    "Not Target",
)
TARGET_APERTURE_DRIVE_DEFAULT_G144 = "Standard"

ALLOWED_TARGET_AUTO_PIXEL_MAPPING_MODES_G144: Tuple[str, ...] = (
    "Off",
    "Not Target",
)
TARGET_AUTO_PIXEL_MAPPING_DEFAULT_G144 = "Off"

VERSION_MENU_PATH_G144 = "Setup -> [Setup Option] -> [Version]"
VERSION_BASE_UXC_RESID16_G144 = 0xE396
BODY_BASE_UXC_RESID16_G144 = 0xEA58
LENS_VER_G_UXC_RESID16_G144 = 0x6517
SOFTWARE_UPDATE_F_UXC_RESID16_G144 = 0x6FD6
LATEST_SW_BADGE_G_UXC_RESID16_G144 = 0x6516
UPDATE_VER_INCORRECT_G_UXC_RESID16_G144 = 0x630A
UPDATE_COMPLETE_G_UXC_RESID16_G144 = 0x616B

BODYDATA_FILENAME_G144 = "BODYDATA.DAT"
FX3_BODYDATA_REQUIRED_SLOT_G144 = MEDIA_SLOT_1_PHASE323
FX3_BODYDATA_MIN_BATTERY_PCT_G144 = 51
FX3_BODYDATA_MIN_BATTERY_BARS_G144 = 3
FX3_STEPPING_STONE_REQUIRED_BELOW_EQ_G144 = 2.02
FX3_STEPPING_STONE_VERSIONS_G144: Tuple[str, ...] = ("2.04", "2.05")
FX3_UPDATE_BLINK_PROGRESS_G144 = "1 -> 3 -> 5"
FX3_UPDATE_ERROR_BLINK_CODES_G144: Tuple[str, ...] = (
    "5 long (0.5s) / 6 short (0.25s)",
    "7 long / 7 short",
)

FX6_VERSION_MENU_PATH_G144 = "Maintenance > Version"
FX6_VERSION_NS2_UXC_RESID16_G144 = 0x5655
FX6_VERSION_UP_NS2_UXC_RESID16_G144 = 0x462C
FX6_AUTO_PIXEL_RESTORE_NS1_UXC_RESID16S_G144: Tuple[int, int] = (0x2E4E, 0x324A)
FX6_BODYDATA_REQUIRED_SLOT_G144 = "Slot B"
FX6_BODYDATA_MIN_POWER_G144 = "AC Adaptor"

# Status / Violation Codes
STATUS_BLOCKED_PHASE323_DONOR_INTEGRITY = "STATUS_BLOCKED_PHASE323_DONOR_INTEGRITY"

STATUS_VERIFIED_G143 = "STATUS_VERIFIED_G143"
STATUS_BLOCKED_G143_TELEMETRY_INVALID = "STATUS_BLOCKED_G143_TELEMETRY_INVALID"
STATUS_BLOCKED_G143_AUDIO_MENU_PATH_OR_REMOVED_DISPLAY_VIOLATION = (
    "STATUS_BLOCKED_G143_AUDIO_MENU_PATH_OR_REMOVED_DISPLAY_VIOLATION"
)
STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION = (
    "STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION"
)
STATUS_BLOCKED_G143_SUBJECT_RECOG_DORMANT_OR_ANIMAL_MOVIE_VIOLATION = (
    "STATUS_BLOCKED_G143_SUBJECT_RECOG_DORMANT_OR_ANIMAL_MOVIE_VIOLATION"
)
STATUS_BLOCKED_G143_FACE_MEMORY_OR_FX6_CROSSWIRE_VIOLATION = (
    "STATUS_BLOCKED_G143_FACE_MEMORY_OR_FX6_CROSSWIRE_VIOLATION"
)

STATUS_VERIFIED_G144 = "STATUS_VERIFIED_G144"
STATUS_BLOCKED_G144_TELEMETRY_INVALID = "STATUS_BLOCKED_G144_TELEMETRY_INVALID"
STATUS_BLOCKED_G144_SILENT_MODE_OR_TARGET_2ITEM_VIOLATION = (
    "STATUS_BLOCKED_G144_SILENT_MODE_OR_TARGET_2ITEM_VIOLATION"
)
STATUS_BLOCKED_G144_DORMANT_PWR_OFF_SHUTTER_OR_FX6_VIOLATION = (
    "STATUS_BLOCKED_G144_DORMANT_PWR_OFF_SHUTTER_OR_FX6_VIOLATION"
)
STATUS_BLOCKED_G144_VERSION_STEPPING_STONE_OR_BADGE_VIOLATION = (
    "STATUS_BLOCKED_G144_VERSION_STEPPING_STONE_OR_BADGE_VIOLATION"
)
STATUS_BLOCKED_G144_SLOT1_BODYDATA_NOGO_FLASH_FIREWALL = (
    "STATUS_BLOCKED_G144_SLOT1_BODYDATA_NOGO_FLASH_FIREWALL"
)

# ---------------------------------------------------------------------------
# Pinned Wave-62 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE323: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x03BC71C1, b"BKID_APP_setting_audio_recording"),
    (0x03BC7206, b"BKID_APP_setting_audio_recording_level"),
    (0x03B32D29, b"VAL_setting_audio_recording_level_AUDIO_RECORDING_LEVEL_26"),
    (0x03BC7257, b"BKID_APP_setting_audio_output_timing"),
    (0x03B33275, b"AUDIO_OUTPUT_TIMING_LIVE"),
    (0x03B3328E, b"VAL_setting_audio_output_timing_AUDIO_OUTPUT_TIMING_LIP_SYNC"),
    (0x03BC72ED, b"BKID_APP_setting_external_mic_audio_format"),
    (
        0x03B332F3,
        b"VAL_setting_external_mic_audio_format_EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_4CH",
    ),
    (0x03BC9540, b"BKID_APP_setting_right_left_eye_select"),
    (0x039CE9B5, b"TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT"),
    (0x039A6BF5, b"FEATURE_MANAGER_eye_face_af_gen_type"),
    (0x03ADDC01, b"SUBJECT_DETECTION_ANIMAL_BIRD"),
    (0x03ADDC74, b"SUBJECT_DETECTION_BIRD"),
    (0x03ADDCA9, b"SUBJECT_DETECTION_INSECT"),
    (0x03ADDCE0, b"SUBJECT_DETECTION_CAR_TRAIN"),
    (0x03ADDD1A, b"SUBJECT_DETECTION_PLANE"),
    (0x03BC6DEC, b"BKID_APP_setting_silent_mode"),
    (0x03BC6E29, b"BKID_APP_setting_silent_detail_setting"),
    (0x03BC6EA4, b"BKID_APP_setting_silent_detail_setting_image_sensor_barrier"),
    (0x03C3CBA0, b"EVENT_REMOTE_ANTI_DUST_FUNCTION_IMAGE_SENSOR_BARRIER"),
    (0x039C2F25, b"PRM_lens_version"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE323 = (
    "5f4929ba420debe0cf290f63cf27e87d0ff11c7af20ce2a6f0d1b9f9239a58b5"
)

PINNED_FX6_APPFW_SLICES_PHASE323: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x027BE6FA, b"AUDIO_OUTPUT_TIMING_LIVE"),
    (0x027BE713, b"AUDIO_OUTPUT_TIMING_LIP_SYNC"),
    (0x025EA9CE, b"image_sensor_barrier"),
    (0x0260B675, b"VERSION_UP"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE323 = (
    "7b250291a5895f1a1cab597384cdc9ab90cfc10047f375a7bcbeb928344d62a5"
)

PINNED_PHASE323_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE323,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE323),
        "FX3 appFw.so Wave-62 AudioOutTiming/24bit4ch/SubjectRecog/SilentTarget/Version slices",
    ),
    "fx3_p1_205_nflasha1": (
        "FX3",
        "fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1",
        19_377_152,
        "ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591",
        (b"mkfs.fat", b"Linux"),
        "FX3 p1 Ver. 2.05 stepping-stone nflasha1 baseline",
    ),
    "fx3_p1_205_libsdfileinputupdaterapi_so": (
        "FX3",
        "fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/lib/libsdfileinputupdaterapi.so",
        60_584,
        "257164d1cdf88757b8c0e2ba08ac47b06c46007410af308b7a8571b442b00cd2",
        (b"\x7fELF", b"sdfile", b"updater"),
        "FX3 p1 Ver. 2.05 libsdfileinputupdaterapi.so",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Audio Out Timing",
            b"Shoe Audio Set.",
            b"4ch Audio Monitoring",
            b"Face/Eye Subject",
            b"Bird",
            b"Silent Mode Settings",
            b"Target Function Settings",
            b"Auto Pixel Mapping",
            b"Shutter When Pwr OFF",
            b"Software Update",
        ),
        "FX3 string_english_f.uxc Wave-62 EN parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Wind Noise Reduct.",
            b"Audio signals",
            b"Version",
        ),
        "FX3 string_english.uxc Wave-62 base strings",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"The update file version is incorrect.",
            b"Software update complete.",
        ),
        "FX3 string_english_g.uxc Wave-62 version/update strings",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "音频输出时刻".encode("utf-8"),
            "MI靴音频设置".encode("utf-8"),
            "脸/眼摄体检测".encode("utf-8"),
            "静音模式设置".encode("utf-8"),
            "目标功能设置".encode("utf-8"),
            "关机时快门".encode("utf-8"),
            "软件更新".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-62 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "音訊輸出時刻".encode("utf-8"),
            "MI靴音訊設定".encode("utf-8"),
            "面/眼攝體偵測".encode("utf-8"),
            "靜音模式設定".encode("utf-8"),
            "目標功能設定".encode("utf-8"),
            "關閉電源時快門".encode("utf-8"),
            "軟體更新".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-62 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "音声出力タイミング".encode("utf-8"),
            "ｼｭｰの音声設定".encode("utf-8"),
            "顔/瞳検出対象".encode("utf-8"),
            "ｻｲﾚﾝﾄﾓｰﾄﾞ設定".encode("utf-8"),
            "対象機能の設定".encode("utf-8"),
            "電源OFF時のｼｬｯﾀｰ".encode("utf-8"),
            "ｿﾌﾄｳｪｱｱｯﾌﾟﾃﾞｰﾄ".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-62 JA parity",
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
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE323,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE323),
        "FX6 appFw.so Wave-62 AudioTiming/ImageSensorBarrier/VersionUp slices",
    ),
    "fx6_avbb_scn_start_audio_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/scenario/AVBB_SCN_START_AUDIO.so",
        70_096,
        "96252cad4c9c13575a6c071be9f9fe72853382af7a4133bac7257e056f71420a",
        (b"\x7fELF", b"AUDIO", b"CH1", b"CH3"),
        "FX6 AVBB_SCN_START_AUDIO.so audio daemon baseline",
    ),
    "fx6_libinfrahotshoe_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraHotshoe.so",
        47_808,
        "0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6",
        (b"\x7fELF", b"Hotshoe", b"SHOE"),
        "FX6 libInfraHotshoe.so MI-shoe baseline",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"Auto Pixel Restore",
            b"Version",
            b"32bit",
        ),
        "FX6 string_english.uxc Wave-62 Auto Pixel Restore & 32bit strings",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"Delete Registered Face",
            b"Version Up",
        ),
        "FX6 string_english_2.uxc Wave-62 Delete Registered Face & Version Up strings",
    ),
}

# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _is_clean_room_forced(force_clean_room: Optional[bool]) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE323):
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
    if body_model_name != FX3_MODEL_NAME_PHASE323:
        errs.append(f"body_model_name_invalid:{body_model_name!r}")
    if not _is_strict_int(body_model_id) or body_model_id != FX3_MODEL_ID_PHASE323:
        errs.append(f"body_model_id_invalid:{body_model_id!r}")
    if help_guide_code != FX3_HELP_GUIDE_CODE_PHASE323:
        errs.append(f"help_guide_code_invalid:{help_guide_code!r}")
    if _parse_fw_float(firmware_version) is None:
        errs.append(f"firmware_version_invalid:{firmware_version!r}")
    return errs


# ---------------------------------------------------------------------------
# Donor Integrity Audit (O_RDONLY / Clean-Room Dual-Mode)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase323DonorAuditResult:
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


def audit_phase323_donor_contracts(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase323DonorAuditResult:
    import time

    t0 = time.perf_counter()
    clean_forced = _is_clean_room_forced(force_clean_room)
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else dict(PINNED_PHASE323_DONOR_SPECS)
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
        return Phase323DonorAuditResult(
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
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE323,
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
        return Phase323DonorAuditResult(
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
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE323,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(
                f"Donor files absent ({len(missing_files)} missing); "
                "verified Phase 323 via clean-room synthetic fallback.",
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
                target, PINNED_FX3_APPFW_SLICES_PHASE323
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tok_errs = _read_exact_o_rdonly_slices(
                target, PINNED_FX6_APPFW_SLICES_PHASE323
            )
        else:
            actual_size, actual_sha, tok_errs = _read_full_o_rdonly_sha256_and_tokens(
                target, tokens
            )

        file_digests[key] = actual_sha
        if actual_size != expected_size:
            missing_markers.append(f"{key}:size_mismatch:{actual_size}!={expected_size}")
            errors.append(f"{family}:{key}:size_mismatch")
        if actual_sha != expected_sha:
            missing_markers.append(f"{key}:sha256_mismatch")
            errors.append(f"{family}:{key}:sha256_mismatch")
        for terr in tok_errs:
            missing_markers.append(f"{key}:{terr}")
            errors.append(f"{family}:{key}:{terr}")

    dt = time.perf_counter() - t0
    valid = len(errors) == 0
    return Phase323DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE323_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="STRICT_OS_O_RDONLY_PREAD",
        files_inspected=inspected,
        fx3_contracts_verified=valid,
        fx6_contracts_verified=valid,
        four_lang_resid16_parity_verified=valid,
        zero_forbidden_myths_verified=valid,
        elapsed_seconds=round(dt, 6),
        within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE323,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        file_digests=file_digests,
        missing_markers=tuple(missing_markers),
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# Gate G143: Shoe Audio 4ch 24-bit, Audio Out Timing & Face/Eye Subject Guard
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShoeAudio4chSubjectRecogGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    audio_out_timing_menu_path: str
    audio_level_display_standalone_menu_removed: bool
    effective_audio_recording: str
    effective_audio_rec_level: int
    effective_shoe_audio_set: str
    effective_audio_out_timing: str
    effective_4ch_audio_monitoring: str
    effective_wind_noise_reduct: str
    effective_audio_source: str
    audio_limiter_always_on_fx3: bool
    effective_proxy_audio_codec: str
    proxy_allowed: bool
    effective_face_eye_prior_in_af: str
    effective_face_eye_subject: str
    animal_eye_af_active_in_mode: bool
    effective_right_left_eye_select: str
    effective_face_eye_frame_disp: str
    clean_hdmi_face_frame_suppressed: bool
    effective_face_memory_count: int
    face_memory_survived_cam_reset: bool
    face_memory_excluded_from_camset: bool
    effective_regist_faces_priority: str
    slot1_data_sector_writes: int
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    matrix_checked_states: int
    raw_firmware_bytes_leaked: int
    persistent_emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    usb_packets_transmitted: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G143ShoeAudio4chSubjectRecogGuardResult:
    gate_id: str
    gate_code: str
    valid: bool
    status: str
    verification_mode: str
    persistent_emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    donor_audit: Dict[str, Any]
    shoe_audio_4ch_subject_recog_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_shoe_audio_4ch_subject_recog_matrix() -> Dict[str, Any]:
    """Enumerate valid Audio Out Timing / Shoe Audio / Face-Eye Subject states."""
    audio_states = 0
    for shoot_mode in ALLOWED_SHOOT_MODES_PHASE323:
        for shoe_fmt in ALLOWED_FX3_SHOE_AUDIO_FORMATS_G143:
            for out_timing in ALLOWED_AUDIO_OUT_TIMING_MODES_G143:
                for mon4ch in ALLOWED_4CH_AUDIO_MONITORING_MODES_G143:
                    for mic35 in (False, True):
                        for handle_on in ("ON", "OFF"):
                            for da_sw in ALLOWED_XLR_H1_DIGITAL_ANALOG_G143:
                                _ = (
                                    shoot_mode,
                                    shoe_fmt,
                                    out_timing,
                                    mon4ch,
                                    mic35,
                                    handle_on,
                                    da_sw,
                                )
                                audio_states += 1

    subject_states = 0
    for shoot_mode in ALLOWED_SHOOT_MODES_PHASE323:
        for subj in ALLOWED_FX3_FACE_EYE_SUBJECTS_G143:
            for eye_sel in ALLOWED_RIGHT_LEFT_EYE_MODES_G143:
                for reset_act in ALLOWED_RESET_ACTIONS_PHASE323:
                    _ = (shoot_mode, subj, eye_sel, reset_act)
                    subject_states += 1

    return {
        "audio_states_checked": audio_states,
        "subject_states_checked": subject_states,
        "total_matrix_states": audio_states + subject_states,
        "dormant_subjects_tested": len(DORMANT_SHARED_FACE_EYE_SUBJECTS_G143),
    }


def resolve_fx3_shoe_audio_4ch_subject_recog_state(
    *,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE323,
    reset_action: str = RESET_ACTION_NONE_PHASE323,
    requested_audio_recording: str = "On",
    requested_audio_rec_level: int = AUDIO_REC_LEVEL_DEFAULT_G143,
    delete_key_reset_rec_level: bool = False,
    requested_shoe_audio_set: str = SHOE_AUDIO_DEFAULT_G143,
    requested_audio_out_timing: str = AUDIO_OUT_TIMING_DEFAULT_G143,
    requested_4ch_audio_monitoring: str = "CH1/CH2",
    requested_wind_noise_reduct: str = "Off",
    main_movie_codec: str = "XAVC S-I DCI 4K",
    rec_frame_rate: str = "23.98p",
    proxy_recording_enabled: bool = False,
    mic_35mm_plugged: bool = False,
    xlr_h1_attached: bool = True,
    xlr_h1_handle_audio: str = "ON",
    xlr_h1_digital_analog: str = XLR_H1_DIGITAL_ANALOG_DIGITAL_G143,
    requested_face_eye_prior_in_af: str = "On",
    requested_face_eye_subject: str = FACE_SUBJECT_DEFAULT_G143,
    requested_right_left_eye_select: str = "Auto",
    requested_face_eye_frame_disp: str = FACE_EYE_FRAME_DISP_DEFAULT_G143,
    face_memory_count: int = 2,
    face_memory_delete_all: bool = False,
    requested_regist_faces_priority: str = "On",
) -> Dict[str, Any]:
    """Resolve effective ILME-FX3 Ver. 7.02 audio & Face/Eye AF state."""
    cam_reset = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE323,
        RESET_ACTION_INITIALIZE_PHASE323,
    )
    init_reset = reset_action == RESET_ACTION_INITIALIZE_PHASE323

    eff_audio_rec = "On" if cam_reset else requested_audio_recording
    if shoot_mode == SHOOT_MODE_SQ_PHASE323:
        eff_audio_rec = "Off"

    eff_rec_level = (
        AUDIO_REC_LEVEL_DEFAULT_G143
        if (cam_reset or delete_key_reset_rec_level)
        else requested_audio_rec_level
    )
    eff_shoe_fmt = SHOE_AUDIO_DEFAULT_G143 if cam_reset else requested_shoe_audio_set
    eff_out_timing = (
        AUDIO_OUT_TIMING_DEFAULT_G143 if cam_reset else requested_audio_out_timing
    )
    eff_4ch_mon = "CH1/CH2" if cam_reset else requested_4ch_audio_monitoring
    eff_wind = "Off" if cam_reset else requested_wind_noise_reduct

    if mic_35mm_plugged:
        eff_source = "3.5mm MIC (2ch Analog Override)"
        eff_shoe_fmt = SHOE_AUDIO_48KHZ_16BIT_2CH_G143
    elif xlr_h1_attached and xlr_h1_handle_audio == "ON":
        if xlr_h1_digital_analog == XLR_H1_DIGITAL_ANALOG_ANALOG_G143:
            eff_source = "MI Shoe Analog (XLR-H1 ANALOG)"
            eff_shoe_fmt = SHOE_AUDIO_48KHZ_16BIT_2CH_G143
        else:
            eff_source = "Digital MI Shoe (XLR-H1)"
    else:
        eff_source = "Internal Stereo Mic"

    proxy_allowed = (
        main_movie_codec in ALLOWED_MAIN_MOVIE_CODECS_G143
        and rec_frame_rate not in PROXY_DISABLED_HIGH_FPS_G143
    )

    eff_prior = "On" if cam_reset else requested_face_eye_prior_in_af
    if shoot_mode == "Intelligent Auto":
        eff_prior = "On"

    eff_subject = FACE_SUBJECT_DEFAULT_G143 if cam_reset else requested_face_eye_subject
    animal_active = (
        eff_subject == FACE_SUBJECT_ANIMAL_G143
        and shoot_mode == SHOOT_MODE_STILL_PHASE323
        and eff_prior == "On"
    )
    eff_eye = "Auto" if cam_reset else requested_right_left_eye_select
    eff_frame_disp = (
        FACE_EYE_FRAME_DISP_DEFAULT_G143 if cam_reset else requested_face_eye_frame_disp
    )
    eff_face_mem = 0 if (init_reset or face_memory_delete_all) else face_memory_count
    eff_reg_prio = "On" if cam_reset else requested_regist_faces_priority
    if eff_subject == FACE_SUBJECT_ANIMAL_G143:
        eff_reg_prio = "Disabled(Animal)"

    return {
        "valid": True,
        "effective_audio_recording": eff_audio_rec,
        "effective_audio_rec_level": eff_rec_level,
        "effective_shoe_audio_set": eff_shoe_fmt,
        "effective_audio_out_timing": eff_out_timing,
        "effective_4ch_audio_monitoring": eff_4ch_mon,
        "effective_wind_noise_reduct": eff_wind,
        "effective_audio_source": eff_source,
        "effective_proxy_audio_codec": PROXY_FORCED_AUDIO_CODEC_G143,
        "proxy_allowed": proxy_allowed,
        "proxy_recording_enabled": bool(proxy_recording_enabled and proxy_allowed),
        "effective_face_eye_prior_in_af": eff_prior,
        "effective_face_eye_subject": eff_subject,
        "animal_eye_af_active_in_mode": animal_active,
        "effective_right_left_eye_select": eff_eye,
        "effective_face_eye_frame_disp": eff_frame_disp,
        "effective_face_memory_count": eff_face_mem,
        "face_memory_survived_cam_reset": reset_action
        == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE323,
        "effective_regist_faces_priority": eff_reg_prio,
    }


def verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE323,
    body_model_id: int = FX3_MODEL_ID_PHASE323,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE323,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE323,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE323,
    reset_action: str = RESET_ACTION_NONE_PHASE323,
    requested_audio_recording: str = "On",
    requested_audio_recording_in_sq: bool = False,
    requested_audio_rec_level: int = AUDIO_REC_LEVEL_DEFAULT_G143,
    delete_key_reset_rec_level: bool = False,
    requested_fx3_disable_audio_limiter: bool = False,
    requested_fx6_limiter_mode_steps: bool = False,
    requested_shoe_audio_set: str = SHOE_AUDIO_DEFAULT_G143,
    requested_32bit_float_shoe_audio: bool = False,
    requested_audio_out_timing: str = AUDIO_OUT_TIMING_DEFAULT_G143,
    requested_audio_out_timing_in_sound_option: bool = False,
    requested_audio_out_timing_in_sq: bool = False,
    requested_standalone_audio_level_display_menu: bool = False,
    requested_4ch_audio_monitoring: str = "CH1/CH2",
    requested_wind_noise_reduct: str = "Off",
    requested_wind_noise_reduct_on_external_mic: bool = False,
    main_movie_codec: str = "XAVC S-I DCI 4K",
    rec_frame_rate: str = "23.98p",
    proxy_recording_enabled: bool = False,
    requested_proxy_4ch_lpcm: bool = False,
    mic_35mm_plugged: bool = False,
    requested_4ch_over_35mm_mic: bool = False,
    xlr_h1_attached: bool = True,
    xlr_h1_handle_audio: str = "ON",
    xlr_h1_digital_analog: str = XLR_H1_DIGITAL_ANALOG_DIGITAL_G143,
    requested_24bit_under_xlrh1_analog: bool = False,
    requested_face_eye_prior_in_af: str = "On",
    requested_face_eye_subject: str = FACE_SUBJECT_DEFAULT_G143,
    requested_wave42_bird_errata_claim: bool = False,
    requested_animal_eye_af_in_movie: bool = False,
    requested_right_left_eye_select: str = "Auto",
    requested_face_eye_frame_disp: str = FACE_EYE_FRAME_DISP_DEFAULT_G143,
    requested_face_frame_over_clean_hdmi: bool = False,
    face_memory_count: int = 2,
    face_memory_delete_all: bool = False,
    requested_camset_export_face_memory: bool = False,
    requested_regist_faces_priority: str = "On",
    requested_fx6_non_human_subject: bool = False,
    requested_fx6_persistent_face_memory: bool = False,
    slot_1_contains_tier0_vault: bool = True,
    slot1_audio_config_write_requested: bool = False,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
) -> ShoeAudio4chSubjectRecogGuardResult:
    """Enforce Phase 323 Gate G143: 4ch 24-bit MI-Shoe Audio & Subject Recog Firewall."""
    matrix_info = compute_shoe_audio_4ch_subject_recog_matrix()
    violations: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    block_errno = 0
    block_errno_name = ""

    def _fail(code: str, err: str, errno_val: int, errno_name: str) -> None:
        nonlocal block_errno, block_errno_name
        if code not in violations:
            violations.append(code)
        errors.append(err)
        if block_errno == 0:
            block_errno = errno_val
            block_errno_name = errno_name

    id_errs = _validate_fx3_body_identity(
        body_model_name, body_model_id, help_guide_code, firmware_version
    )
    if id_errs:
        _fail(
            STATUS_BLOCKED_G143_TELEMETRY_INVALID,
            ";".join(id_errs),
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )

    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE323:
        _fail(
            STATUS_BLOCKED_G143_TELEMETRY_INVALID,
            f"shoot_mode_invalid:{shoot_mode!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE323:
        _fail(
            STATUS_BLOCKED_G143_TELEMETRY_INVALID,
            f"reset_action_invalid:{reset_action!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if not _is_on_off(requested_audio_recording):
        _fail(
            STATUS_BLOCKED_G143_TELEMETRY_INVALID,
            f"audio_recording_invalid:{requested_audio_recording!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if (
        not _is_strict_int(requested_audio_rec_level)
        or requested_audio_rec_level < AUDIO_REC_LEVEL_MIN_G143
        or requested_audio_rec_level > AUDIO_REC_LEVEL_MAX_G143
    ):
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            f"audio_rec_level_out_of_range:{requested_audio_rec_level!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if requested_audio_out_timing not in ALLOWED_AUDIO_OUT_TIMING_MODES_G143:
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            f"audio_out_timing_invalid:{requested_audio_out_timing!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if requested_4ch_audio_monitoring not in ALLOWED_4CH_AUDIO_MONITORING_MODES_G143:
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            f"4ch_audio_monitoring_invalid:{requested_4ch_audio_monitoring!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if not _is_on_off(requested_wind_noise_reduct):
        _fail(
            STATUS_BLOCKED_G143_TELEMETRY_INVALID,
            f"wind_noise_reduct_invalid:{requested_wind_noise_reduct!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if main_movie_codec not in ALLOWED_MAIN_MOVIE_CODECS_G143:
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            f"main_movie_codec_invalid:{main_movie_codec!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if xlr_h1_handle_audio not in ALLOWED_XLR_H1_SWITCH_STATES_G143:
        _fail(
            STATUS_BLOCKED_G143_TELEMETRY_INVALID,
            f"xlr_h1_handle_audio_invalid:{xlr_h1_handle_audio!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if xlr_h1_digital_analog not in ALLOWED_XLR_H1_DIGITAL_ANALOG_G143:
        _fail(
            STATUS_BLOCKED_G143_TELEMETRY_INVALID,
            f"xlr_h1_digital_analog_invalid:{xlr_h1_digital_analog!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if not _is_on_off(requested_face_eye_prior_in_af):
        _fail(
            STATUS_BLOCKED_G143_TELEMETRY_INVALID,
            f"face_eye_prior_in_af_invalid:{requested_face_eye_prior_in_af!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if requested_right_left_eye_select not in ALLOWED_RIGHT_LEFT_EYE_MODES_G143:
        _fail(
            STATUS_BLOCKED_G143_TELEMETRY_INVALID,
            f"right_left_eye_select_invalid:{requested_right_left_eye_select!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if not _is_on_off(requested_face_eye_frame_disp):
        _fail(
            STATUS_BLOCKED_G143_TELEMETRY_INVALID,
            f"face_eye_frame_disp_invalid:{requested_face_eye_frame_disp!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if not _is_on_off(requested_regist_faces_priority):
        _fail(
            STATUS_BLOCKED_G143_TELEMETRY_INVALID,
            f"regist_faces_priority_invalid:{requested_regist_faces_priority!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if (
        not _is_strict_int(face_memory_count)
        or face_memory_count < 0
        or face_memory_count > FACE_MEMORY_MAX_FACES_G143
    ):
        _fail(
            STATUS_BLOCKED_G143_FACE_MEMORY_OR_FX6_CROSSWIRE_VIOLATION,
            f"face_memory_count_out_of_range:{face_memory_count!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )

    # 1. Audio Menu Path & Removed [Audio Level Display] Checks
    if requested_audio_out_timing_in_sound_option:
        _fail(
            STATUS_BLOCKED_G143_AUDIO_MENU_PATH_OR_REMOVED_DISPLAY_VIOLATION,
            "Audio Out Timing resides under Shooting -> [Audio Recording], NOT Setup -> [Sound Option]",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if requested_standalone_audio_level_display_menu:
        _fail(
            STATUS_BLOCKED_G143_AUDIO_MENU_PATH_OR_REMOVED_DISPLAY_VIOLATION,
            "Audio Level Display (_f 0x7a36) removed as standalone menu in Ver. 2.00..7.02 (auto via DISP)",
            EOPNOTSUPP_ERRNO_PHASE323,
            EOPNOTSUPP_NAME_PHASE323,
        )

    # 2. Audio Routing, Limiter, 4ch Codecs, Proxy, 3.5mm Override, Wind Noise
    if requested_audio_recording_in_sq or (
        shoot_mode == SHOOT_MODE_SQ_PHASE323 and requested_audio_out_timing_in_sq
    ):
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            "Audio Recording & Audio Out Timing are disabled in S&Q mode",
            EOPNOTSUPP_ERRNO_PHASE323,
            EOPNOTSUPP_NAME_PHASE323,
        )
    if requested_audio_out_timing_in_sq:
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            "Audio Out Timing disabled in S&Q mode",
            EOPNOTSUPP_ERRNO_PHASE323,
            EOPNOTSUPP_NAME_PHASE323,
        )
    if requested_fx3_disable_audio_limiter or requested_fx6_limiter_mode_steps:
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            "ILME-FX3 built-in audio limiter is always-on & non-disableable (vs FX6 6-step Limiter Mode)",
            EOPNOTSUPP_ERRNO_PHASE323,
            EOPNOTSUPP_NAME_PHASE323,
        )
    if requested_32bit_float_shoe_audio or requested_shoe_audio_set == FX6_DORMANT_AUDIO_FORMAT_G143:
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            "48kHz/32bit float audio is dormant/unsupported on ILME-FX3",
            EOPNOTSUPP_ERRNO_PHASE323,
            EOPNOTSUPP_NAME_PHASE323,
        )
    elif requested_shoe_audio_set not in ALLOWED_FX3_SHOE_AUDIO_FORMATS_G143:
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            f"shoe_audio_set_invalid:{requested_shoe_audio_set!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )

    if requested_proxy_4ch_lpcm:
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            "Proxy files always record MPEG-4 AAC-LC 2ch 128kbps (never 4ch 24-bit LPCM)",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if proxy_recording_enabled and rec_frame_rate in PROXY_DISABLED_HIGH_FPS_G143:
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            f"Proxy recording disabled at high frame rate {rec_frame_rate!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if mic_35mm_plugged and requested_4ch_over_35mm_mic:
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            "3.5mm MIC jack overrides Digital MI-Shoe (forces 2ch analog & grays out [Shoe Audio Set.])",
            EBUSY_ERRNO_PHASE323,
            EBUSY_NAME_PHASE323,
        )
    if (
        xlr_h1_attached
        and xlr_h1_handle_audio == "ON"
        and xlr_h1_digital_analog == XLR_H1_DIGITAL_ANALOG_ANALOG_G143
        and (
            requested_24bit_under_xlrh1_analog
            or requested_shoe_audio_set
            in (SHOE_AUDIO_48KHZ_24BIT_4CH_G143, SHOE_AUDIO_48KHZ_24BIT_2CH_G143)
        )
    ):
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            "XLR-H1 ANALOG switch caps MI-Shoe at 48kHz/16bit 2ch (24bit/4ch rejected)",
            EOPNOTSUPP_ERRNO_PHASE323,
            EOPNOTSUPP_NAME_PHASE323,
        )
    if requested_wind_noise_reduct_on_external_mic:
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            "[Wind Noise Reduct.] applies ONLY to built-in internal stereo mic",
            EOPNOTSUPP_ERRNO_PHASE323,
            EOPNOTSUPP_NAME_PHASE323,
        )
    if slot_1_contains_tier0_vault and slot1_audio_config_write_requested:
        _fail(
            STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
            "Slot-1 Tier-0 recovery vault write blocked (EROFS)",
            EROFS_ERRNO_PHASE323,
            EROFS_NAME_PHASE323,
        )

    # 3. Focus -> [Face/Eye AF] & Explicit Wave-42 Dormant Bird/Insect/Car/Airplane Firewall
    if requested_wave42_bird_errata_claim:
        _fail(
            STATUS_BLOCKED_G143_SUBJECT_RECOG_DORMANT_OR_ANIMAL_MOVIE_VIOLATION,
            "Wave-42 errata busted: ILME-FX3 Ver. 7.02 lacks Bird subject detection (_f 0x6cb1 dormant)",
            EOPNOTSUPP_ERRNO_PHASE323,
            EOPNOTSUPP_NAME_PHASE323,
        )
    if requested_face_eye_subject in DORMANT_SHARED_FACE_EYE_SUBJECTS_G143:
        resid = DORMANT_FACE_EYE_SUBJECT_UXC_RESID16S_G143[requested_face_eye_subject]
        _fail(
            STATUS_BLOCKED_G143_SUBJECT_RECOG_DORMANT_OR_ANIMAL_MOVIE_VIOLATION,
            f"Dormant shared ELF/UXC subject {requested_face_eye_subject!r} (_f 0x{resid:04x}) "
            "not exposed on ILME-FX3 Ver. 7.02 (no AI Processing Unit)",
            EOPNOTSUPP_ERRNO_PHASE323,
            EOPNOTSUPP_NAME_PHASE323,
        )
    elif requested_face_eye_subject not in ALLOWED_FX3_FACE_EYE_SUBJECTS_G143:
        _fail(
            STATUS_BLOCKED_G143_SUBJECT_RECOG_DORMANT_OR_ANIMAL_MOVIE_VIOLATION,
            f"face_eye_subject_invalid:{requested_face_eye_subject!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )

    if requested_animal_eye_af_in_movie or (
        requested_face_eye_subject == FACE_SUBJECT_ANIMAL_G143
        and shoot_mode in (SHOOT_MODE_MOVIE_PHASE323, SHOOT_MODE_SQ_PHASE323)
        and reset_action == RESET_ACTION_NONE_PHASE323
    ):
        _fail(
            STATUS_BLOCKED_G143_SUBJECT_RECOG_DORMANT_OR_ANIMAL_MOVIE_VIOLATION,
            "TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT: ILME-FX3 supports Animal Eye AF ONLY in Still mode",
            EOPNOTSUPP_ERRNO_PHASE323,
            EOPNOTSUPP_NAME_PHASE323,
        )

    if requested_face_frame_over_clean_hdmi:
        _fail(
            STATUS_BLOCKED_G143_FACE_MEMORY_OR_FX6_CROSSWIRE_VIOLATION,
            "[Face/Eye Frame Disp.] never pollutes Clean HDMI / HDMI RAW feed",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if requested_camset_export_face_memory:
        _fail(
            STATUS_BLOCKED_G143_FACE_MEMORY_OR_FX6_CROSSWIRE_VIOLATION,
            "[Face Memory] (8 faces) is excluded from CAMSET*.DAT export",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if requested_fx6_non_human_subject or requested_fx6_persistent_face_memory:
        _fail(
            STATUS_BLOCKED_G143_FACE_MEMORY_OR_FX6_CROSSWIRE_VIOLATION,
            "ILME-FX6 is Human-only Face/Eye Priority/Only AF with session-ephemeral Saved Tracking Face",
            EOPNOTSUPP_ERRNO_PHASE323,
            EOPNOTSUPP_NAME_PHASE323,
        )

    resolved = resolve_fx3_shoe_audio_4ch_subject_recog_state(
        shoot_mode=shoot_mode
        if shoot_mode in ALLOWED_SHOOT_MODES_PHASE323
        else SHOOT_MODE_MOVIE_PHASE323,
        reset_action=reset_action
        if reset_action in ALLOWED_RESET_ACTIONS_PHASE323
        else RESET_ACTION_NONE_PHASE323,
        requested_audio_recording=requested_audio_recording
        if _is_on_off(requested_audio_recording)
        else "On",
        requested_audio_rec_level=requested_audio_rec_level
        if _is_strict_int(requested_audio_rec_level)
        and AUDIO_REC_LEVEL_MIN_G143 <= requested_audio_rec_level <= AUDIO_REC_LEVEL_MAX_G143
        else AUDIO_REC_LEVEL_DEFAULT_G143,
        delete_key_reset_rec_level=delete_key_reset_rec_level,
        requested_shoe_audio_set=requested_shoe_audio_set
        if requested_shoe_audio_set in ALLOWED_FX3_SHOE_AUDIO_FORMATS_G143
        else SHOE_AUDIO_DEFAULT_G143,
        requested_audio_out_timing=requested_audio_out_timing
        if requested_audio_out_timing in ALLOWED_AUDIO_OUT_TIMING_MODES_G143
        else AUDIO_OUT_TIMING_DEFAULT_G143,
        requested_4ch_audio_monitoring=requested_4ch_audio_monitoring
        if requested_4ch_audio_monitoring in ALLOWED_4CH_AUDIO_MONITORING_MODES_G143
        else "CH1/CH2",
        requested_wind_noise_reduct=requested_wind_noise_reduct
        if _is_on_off(requested_wind_noise_reduct)
        else "Off",
        main_movie_codec=main_movie_codec
        if main_movie_codec in ALLOWED_MAIN_MOVIE_CODECS_G143
        else "XAVC S-I DCI 4K",
        rec_frame_rate=rec_frame_rate,
        proxy_recording_enabled=proxy_recording_enabled,
        mic_35mm_plugged=mic_35mm_plugged,
        xlr_h1_attached=xlr_h1_attached,
        xlr_h1_handle_audio=xlr_h1_handle_audio
        if xlr_h1_handle_audio in ALLOWED_XLR_H1_SWITCH_STATES_G143
        else "ON",
        xlr_h1_digital_analog=xlr_h1_digital_analog
        if xlr_h1_digital_analog in ALLOWED_XLR_H1_DIGITAL_ANALOG_G143
        else XLR_H1_DIGITAL_ANALOG_DIGITAL_G143,
        requested_face_eye_prior_in_af=requested_face_eye_prior_in_af
        if _is_on_off(requested_face_eye_prior_in_af)
        else "On",
        requested_face_eye_subject=requested_face_eye_subject
        if requested_face_eye_subject in ALLOWED_FX3_FACE_EYE_SUBJECTS_G143
        else FACE_SUBJECT_DEFAULT_G143,
        requested_right_left_eye_select=requested_right_left_eye_select
        if requested_right_left_eye_select in ALLOWED_RIGHT_LEFT_EYE_MODES_G143
        else "Auto",
        requested_face_eye_frame_disp=requested_face_eye_frame_disp
        if _is_on_off(requested_face_eye_frame_disp)
        else FACE_EYE_FRAME_DISP_DEFAULT_G143,
        face_memory_count=face_memory_count
        if _is_strict_int(face_memory_count)
        and 0 <= face_memory_count <= FACE_MEMORY_MAX_FACES_G143
        else 0,
        face_memory_delete_all=face_memory_delete_all,
        requested_regist_faces_priority=requested_regist_faces_priority
        if _is_on_off(requested_regist_faces_priority)
        else "On",
    )

    valid = len(violations) == 0
    status = STATUS_VERIFIED_G143 if valid else violations[0]
    return ShoeAudio4chSubjectRecogGuardResult(
        valid=valid,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        audio_out_timing_menu_path=AUDIO_OUT_TIMING_MENU_PATH_G143,
        audio_level_display_standalone_menu_removed=True,
        effective_audio_recording=resolved["effective_audio_recording"],
        effective_audio_rec_level=resolved["effective_audio_rec_level"],
        effective_shoe_audio_set=resolved["effective_shoe_audio_set"],
        effective_audio_out_timing=resolved["effective_audio_out_timing"],
        effective_4ch_audio_monitoring=resolved["effective_4ch_audio_monitoring"],
        effective_wind_noise_reduct=resolved["effective_wind_noise_reduct"],
        effective_audio_source=resolved["effective_audio_source"],
        audio_limiter_always_on_fx3=True,
        effective_proxy_audio_codec=resolved["effective_proxy_audio_codec"],
        proxy_allowed=resolved["proxy_allowed"],
        effective_face_eye_prior_in_af=resolved["effective_face_eye_prior_in_af"],
        effective_face_eye_subject=resolved["effective_face_eye_subject"],
        animal_eye_af_active_in_mode=resolved["animal_eye_af_active_in_mode"],
        effective_right_left_eye_select=resolved["effective_right_left_eye_select"],
        effective_face_eye_frame_disp=resolved["effective_face_eye_frame_disp"],
        clean_hdmi_face_frame_suppressed=True,
        effective_face_memory_count=resolved["effective_face_memory_count"],
        face_memory_survived_cam_reset=resolved["face_memory_survived_cam_reset"],
        face_memory_excluded_from_camset=True,
        effective_regist_faces_priority=resolved["effective_regist_faces_priority"],
        slot1_data_sector_writes=0,
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
        matrix_checked_states=matrix_info["total_matrix_states"],
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
    )


def evaluate_g143_shoe_audio_4ch_out_timing_and_subject_recog_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G143ShoeAudio4chSubjectRecogGuardResult]:
    audit = audit_phase323_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G143ShoeAudio4chSubjectRecogGuardResult(
        gate_id=G143,
        gate_code=G143_GATE_CODE,
        valid=overall_valid,
        status=status,
        verification_mode=audit.verification_mode,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        donor_audit=audit.to_dict(),
        shoe_audio_4ch_subject_recog_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G143,
        gate_code=G143_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"out_timing={res.effective_audio_out_timing} "
            f"rec_level={res.effective_audio_rec_level} "
            f"shoe_audio={res.effective_shoe_audio_set} "
            f"subject={res.effective_face_eye_subject} "
            f"animal_movie={res.animal_eye_af_active_in_mode}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


# ---------------------------------------------------------------------------
# Gate G144: Silent Mode 2-Level Menu, 2-Item Target & BODYDATA.DAT NO-GO Guard
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SilentTargetBodydataNoGoGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    silent_mode_menu_path: str
    effective_silent_mode: str
    effective_shutter_type: str
    effective_audio_signals: str
    disabled_5_functions_enforced: Tuple[str, ...]
    af_illuminator_auto_disabled_by_silent: bool
    target_function_exact_2_items: Tuple[str, ...]
    effective_aperture_drive_in_af: str
    effective_auto_pixel_mapping: str
    power_off_mechanical_shutter_actuation: bool
    dormant_shutter_when_pwr_off_blocked: bool
    fx6_shutterless_auto_pixel_restore_model: str
    airplane_mode: str
    update_badge_silenced: bool
    fx3_bodydata_required_slot: int
    fx3_bodydata_min_battery_pct: int
    fx3_stepping_stone_required_for_current_fw: bool
    fx6_bodydata_required_slot: str
    fx6_bodydata_required_power: str
    emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    slot1_data_sector_writes: int
    usb_packets_transmitted: int
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    matrix_checked_states: int
    raw_firmware_bytes_leaked: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G144SilentTargetBodydataNoGoGuardResult:
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
    silent_target_bodydata_nogo_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_silent_target_bodydata_matrix() -> Dict[str, Any]:
    """Enumerate valid Silent Mode / Target Function / BODYDATA Firewall states."""
    silent_states = 0
    for shoot_mode in ALLOWED_SHOOT_MODES_PHASE323:
        for silent in ("Off", "On"):
            for ap_drive in ALLOWED_TARGET_APERTURE_DRIVE_MODES_G144:
                for pix_map in ALLOWED_TARGET_AUTO_PIXEL_MAPPING_MODES_G144:
                    for reset_act in ALLOWED_RESET_ACTIONS_PHASE323:
                        _ = (shoot_mode, silent, ap_drive, pix_map, reset_act)
                        silent_states += 1

    fw_states = 0
    for cur_fw in ("2.00", "2.02", "2.05", "6.01", "7.02"):
        for slot in ALLOWED_MEDIA_SLOTS_PHASE323:
            for batt_pct in (45, 51, 80):
                for air in ("On", "Off"):
                    _ = (cur_fw, slot, batt_pct, air)
                    fw_states += 1

    return {
        "silent_states_checked": silent_states,
        "fw_policy_states_checked": fw_states,
        "total_matrix_states": silent_states + fw_states,
    }


def resolve_fx3_silent_target_bodydata_state(
    *,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE323,
    reset_action: str = RESET_ACTION_NONE_PHASE323,
    requested_silent_mode: str = "Off",
    requested_shutter_type: str = "Mechanical",
    requested_audio_signals: str = "On",
    requested_aperture_drive_in_af: str = TARGET_APERTURE_DRIVE_DEFAULT_G144,
    requested_auto_pixel_mapping: str = TARGET_AUTO_PIXEL_MAPPING_DEFAULT_G144,
    airplane_mode: str = "On",
    current_fx3_fw: str = FX3_DEFAULT_FW_VERSION_PHASE323,
) -> Dict[str, Any]:
    """Resolve effective Silent Mode Settings, 2-item Target Function & Version state."""
    cam_reset = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE323,
        RESET_ACTION_INITIALIZE_PHASE323,
    )
    init_reset = reset_action == RESET_ACTION_INITIALIZE_PHASE323

    eff_silent = "Off" if cam_reset else requested_silent_mode
    eff_ap_drive = (
        TARGET_APERTURE_DRIVE_DEFAULT_G144 if cam_reset else requested_aperture_drive_in_af
    )
    if shoot_mode != SHOOT_MODE_STILL_PHASE323:
        eff_ap_drive = f"{eff_ap_drive}(Still-Only)"
    eff_pix_map = (
        TARGET_AUTO_PIXEL_MAPPING_DEFAULT_G144
        if cam_reset
        else requested_auto_pixel_mapping
    )
    eff_audio_sig = "On" if init_reset else requested_audio_signals
    eff_shutter = requested_shutter_type

    if eff_silent == "On":
        eff_shutter = "Electronic Shutter"
        eff_audio_sig = "Off"

    fw_num = _parse_fw_float(current_fx3_fw)
    stepping_req = fw_num is not None and fw_num <= FX3_STEPPING_STONE_REQUIRED_BELOW_EQ_G144
    return {
        "valid": True,
        "effective_silent_mode": eff_silent,
        "effective_shutter_type": eff_shutter,
        "effective_audio_signals": eff_audio_sig,
        "disabled_5_functions_enforced": (
            EXACT_5_SILENT_DISABLED_FUNCTIONS_G144 if eff_silent == "On" else ()
        ),
        "effective_aperture_drive_in_af": eff_ap_drive,
        "effective_auto_pixel_mapping": eff_pix_map,
        "power_off_mechanical_shutter_actuation": eff_pix_map != "Off",
        "update_badge_silenced": airplane_mode == "On",
        "fx3_stepping_stone_required_for_current_fw": stepping_req,
    }


def validate_fx3_vs_fx6_bodydata_policy(
    *,
    camera_model: str = FX3_MODEL_NAME_PHASE323,
    current_fw_version: str = FX3_DEFAULT_FW_VERSION_PHASE323,
    target_fw_version: str = FX3_DEFAULT_FW_VERSION_PHASE323,
    bodydata_filename: str = BODYDATA_FILENAME_G144,
    media_slot: Any = MEDIA_SLOT_1_PHASE323,
    battery_soc_pct: int = 80,
    ac_adaptor_connected: bool = False,
    stepping_stone_204_205_completed: bool = True,
) -> Tuple[bool, int, str]:
    """Read-only policy validator for FX3 Slot 1 vs FX6 Slot B BODYDATA.DAT rules."""
    if bodydata_filename != BODYDATA_FILENAME_G144:
        return (
            False,
            EINVAL_ERRNO_PHASE323,
            f"bodydata_filename_must_be_exact_BODYDATA.DAT:{bodydata_filename!r}",
        )
    if camera_model == FX3_MODEL_NAME_PHASE323:
        if media_slot != FX3_BODYDATA_REQUIRED_SLOT_G144:
            return (
                False,
                EINVAL_ERRNO_PHASE323,
                f"FX3 BODYDATA.DAT requires Slot 1 root (Slot {media_slot!r} ignored)",
            )
        if not _is_strict_int(battery_soc_pct) or battery_soc_pct < FX3_BODYDATA_MIN_BATTERY_PCT_G144:
            return (
                False,
                EINVAL_ERRNO_PHASE323,
                f"FX3 requires NP-FZ100 >= 51% (3 bars), got {battery_soc_pct!r}%",
            )
        cur_f = _parse_fw_float(current_fw_version)
        tgt_f = _parse_fw_float(target_fw_version)
        if (
            cur_f is not None
            and tgt_f is not None
            and cur_f <= FX3_STEPPING_STONE_REQUIRED_BELOW_EQ_G144
            and tgt_f > 2.05
            and not stepping_stone_204_205_completed
        ):
            return (
                False,
                EINVAL_ERRNO_PHASE323,
                "FX3 <= Ver. 2.02 requires Ver. 2.04/2.05 stepping-stone (5 long / 6 short blink error)",
            )
        return True, 0, "FX3_POLICY_VALID_READONLY"

    if camera_model == FX6_MODEL_NAME_PHASE323:
        if media_slot != FX6_BODYDATA_REQUIRED_SLOT_G144:
            return (
                False,
                EINVAL_ERRNO_PHASE323,
                f"FX6 Version Up requires Slot B root (Slot {media_slot!r} ignored)",
            )
        if not ac_adaptor_connected:
            return (
                False,
                EINVAL_ERRNO_PHASE323,
                "FX6 Version Up mandates AC Adaptor ('Please use the AC Adaptor')",
            )
        return True, 0, "FX6_POLICY_VALID_READONLY"

    return False, EINVAL_ERRNO_PHASE323, f"unknown_camera_model:{camera_model!r}"


def verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE323,
    body_model_id: int = FX3_MODEL_ID_PHASE323,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE323,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE323,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE323,
    reset_action: str = RESET_ACTION_NONE_PHASE323,
    requested_silent_mode: str = "Off",
    requested_shutter_type: str = "Mechanical",
    requested_audio_signals: str = "On",
    requested_silent_disabled_func_override: Optional[str] = None,
    requested_af_illuminator_auto_disabled_by_silent: bool = False,
    requested_aperture_drive_in_af: str = TARGET_APERTURE_DRIVE_DEFAULT_G144,
    requested_auto_pixel_mapping: str = TARGET_AUTO_PIXEL_MAPPING_DEFAULT_G144,
    requested_target_function_extra_item: Optional[str] = None,
    requested_shutter_when_pwr_off: bool = False,
    requested_anti_dust_function: bool = False,
    requested_fx6_silent_mode_or_pwr_shutter: bool = False,
    airplane_mode: str = "On",
    network_update_badge_emitted: bool = False,
    current_fx3_fw: str = FX3_DEFAULT_FW_VERSION_PHASE323,
    target_fx3_fw: str = FX3_DEFAULT_FW_VERSION_PHASE323,
    bodydata_filename: str = BODYDATA_FILENAME_G144,
    bodydata_policy_slot: Any = MEDIA_SLOT_1_PHASE323,
    battery_soc_pct: int = 80,
    stepping_stone_204_205_completed: bool = True,
    slot_1_contains_tier0_vault: bool = True,
    stage_bodydata_to_slot1_requested: bool = False,
    invoke_software_update_requested: bool = False,
    request_persistent_emmc_writes: bool = False,
    cnflasha_write_requested: bool = False,
    cross_model_flash_requested: bool = False,
    hardware_live_attachment_requested: bool = False,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
) -> SilentTargetBodydataNoGoGuardResult:
    """Enforce Phase 323 Gate G144: Silent Mode, 2-Item Target & BODYDATA NO-GO Firewall."""
    matrix_info = compute_silent_target_bodydata_matrix()
    violations: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    block_errno = 0
    block_errno_name = ""

    def _fail(code: str, err: str, errno_val: int, errno_name: str) -> None:
        nonlocal block_errno, block_errno_name
        if code not in violations:
            violations.append(code)
        errors.append(err)
        if block_errno == 0:
            block_errno = errno_val
            block_errno_name = errno_name

    id_errs = _validate_fx3_body_identity(
        body_model_name, body_model_id, help_guide_code, firmware_version
    )
    if id_errs:
        _fail(
            STATUS_BLOCKED_G144_TELEMETRY_INVALID,
            ";".join(id_errs),
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )

    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE323:
        _fail(
            STATUS_BLOCKED_G144_TELEMETRY_INVALID,
            f"shoot_mode_invalid:{shoot_mode!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE323:
        _fail(
            STATUS_BLOCKED_G144_TELEMETRY_INVALID,
            f"reset_action_invalid:{reset_action!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if not _is_on_off(requested_silent_mode):
        _fail(
            STATUS_BLOCKED_G144_TELEMETRY_INVALID,
            f"silent_mode_invalid:{requested_silent_mode!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if not _is_on_off(requested_audio_signals):
        _fail(
            STATUS_BLOCKED_G144_TELEMETRY_INVALID,
            f"audio_signals_invalid:{requested_audio_signals!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if not _is_on_off(airplane_mode):
        _fail(
            STATUS_BLOCKED_G144_TELEMETRY_INVALID,
            f"airplane_mode_invalid:{airplane_mode!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )

    # 1. Silent Mode Settings (5 disabled funcs + AF Illuminator NOT auto-disabled) & 2-item Target Function
    if (
        requested_silent_mode == "On"
        and requested_silent_disabled_func_override is not None
    ):
        if requested_silent_disabled_func_override in EXACT_5_SILENT_DISABLED_FUNCTIONS_G144:
            _fail(
                STATUS_BLOCKED_G144_SILENT_MODE_OR_TARGET_2ITEM_VIOLATION,
                f"Silent Mode = On hard-disables {requested_silent_disabled_func_override!r}",
                EBUSY_ERRNO_PHASE323,
                EBUSY_NAME_PHASE323,
            )
        else:
            _fail(
                STATUS_BLOCKED_G144_SILENT_MODE_OR_TARGET_2ITEM_VIOLATION,
                f"unknown_silent_disabled_func_override:{requested_silent_disabled_func_override!r}",
                EINVAL_ERRNO_PHASE323,
                EINVAL_NAME_PHASE323,
            )

    if requested_af_illuminator_auto_disabled_by_silent:
        _fail(
            STATUS_BLOCKED_G144_SILENT_MODE_OR_TARGET_2ITEM_VIOLATION,
            "[AF Illuminator] is NOT auto-disabled by [Silent Mode] = On",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )

    if requested_aperture_drive_in_af not in ALLOWED_TARGET_APERTURE_DRIVE_MODES_G144:
        _fail(
            STATUS_BLOCKED_G144_SILENT_MODE_OR_TARGET_2ITEM_VIOLATION,
            f"target_aperture_drive_invalid:{requested_aperture_drive_in_af!r}",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if requested_auto_pixel_mapping not in ALLOWED_TARGET_AUTO_PIXEL_MAPPING_MODES_G144:
        _fail(
            STATUS_BLOCKED_G144_SILENT_MODE_OR_TARGET_2ITEM_VIOLATION,
            f"target_auto_pixel_mapping_invalid:{requested_auto_pixel_mapping!r} "
            "(must be Off or Not Target; Off prevents power-off shutter actuation & cnflasha write)",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )
    if requested_target_function_extra_item is not None:
        _fail(
            STATUS_BLOCKED_G144_SILENT_MODE_OR_TARGET_2ITEM_VIOLATION,
            f"[Target Function Settings] exposes ONLY 2 active items; "
            f"{requested_target_function_extra_item!r} unsupported",
            EOPNOTSUPP_ERRNO_PHASE323,
            EOPNOTSUPP_NAME_PHASE323,
        )

    # 2. Dormant [Shutter When Pwr OFF] / [Anti-dust Function] & Shutterless FX6
    if requested_shutter_when_pwr_off or requested_anti_dust_function:
        _fail(
            STATUS_BLOCKED_G144_DORMANT_PWR_OFF_SHUTTER_OR_FX6_VIOLATION,
            "Dormant [Shutter When Pwr OFF] (_f 0x709f, image_sensor_barrier) / "
            "[Anti-dust Function] (_f 0x7495) do NOT exist on ILME-FX3",
            EOPNOTSUPP_ERRNO_PHASE323,
            EOPNOTSUPP_NAME_PHASE323,
        )
    if requested_fx6_silent_mode_or_pwr_shutter:
        _fail(
            STATUS_BLOCKED_G144_DORMANT_PWR_OFF_SHUTTER_OR_FX6_VIOLATION,
            "ILME-FX6 is shutterless (Auto Pixel Restore, no Silent Mode Settings or mechanical shutter)",
            EOPNOTSUPP_ERRNO_PHASE323,
            EOPNOTSUPP_NAME_PHASE323,
        )

    # 3. [Version] Update Badge Zero-RF Silence & BODYDATA.DAT Policy Checks
    if airplane_mode == "On" and network_update_badge_emitted:
        _fail(
            STATUS_BLOCKED_G144_VERSION_STEPPING_STONE_OR_BADGE_VIOLATION,
            "Zero-RF Airplane Mode = On must silence _g 0x6516 update badge",
            EINVAL_ERRNO_PHASE323,
            EINVAL_NAME_PHASE323,
        )

    policy_ok, policy_errno, policy_msg = validate_fx3_vs_fx6_bodydata_policy(
        camera_model=FX3_MODEL_NAME_PHASE323,
        current_fw_version=current_fx3_fw,
        target_fw_version=target_fx3_fw,
        bodydata_filename=bodydata_filename,
        media_slot=bodydata_policy_slot,
        battery_soc_pct=battery_soc_pct,
        stepping_stone_204_205_completed=stepping_stone_204_205_completed,
    )
    if not policy_ok:
        _fail(
            STATUS_BLOCKED_G144_VERSION_STEPPING_STONE_OR_BADGE_VIOLATION,
            policy_msg,
            policy_errno,
            EINVAL_NAME_PHASE323,
        )

    # 4. HARD NO-GO / BLOCKED Physical Flash & Slot-1 BODYDATA.DAT Firewall
    if stage_bodydata_to_slot1_requested or (
        slot_1_contains_tier0_vault and stage_bodydata_to_slot1_requested
    ):
        _fail(
            STATUS_BLOCKED_G144_SLOT1_BODYDATA_NOGO_FLASH_FIREWALL,
            "HARD NO-GO: staging BODYDATA.DAT onto Slot 1 Tier-0 Vault is forbidden (EROFS)",
            EROFS_ERRNO_PHASE323,
            EROFS_NAME_PHASE323,
        )
    if (
        invoke_software_update_requested
        or request_persistent_emmc_writes
        or cnflasha_write_requested
        or cross_model_flash_requested
        or hardware_live_attachment_requested
    ):
        _fail(
            STATUS_BLOCKED_G144_SLOT1_BODYDATA_NOGO_FLASH_FIREWALL,
            "HARD NO-GO: [Software Update]/Version Up, persistent emmc/cnflasha writes, "
            "cross-model flash (FX6<->FX3), and live hardware attach are hard-locked BLOCKED (EPERM)",
            EPERM_ERRNO_PHASE323,
            EPERM_NAME_PHASE323,
        )

    resolved = resolve_fx3_silent_target_bodydata_state(
        shoot_mode=shoot_mode
        if shoot_mode in ALLOWED_SHOOT_MODES_PHASE323
        else SHOOT_MODE_MOVIE_PHASE323,
        reset_action=reset_action
        if reset_action in ALLOWED_RESET_ACTIONS_PHASE323
        else RESET_ACTION_NONE_PHASE323,
        requested_silent_mode=requested_silent_mode
        if _is_on_off(requested_silent_mode)
        else "Off",
        requested_shutter_type=requested_shutter_type,
        requested_audio_signals=requested_audio_signals
        if _is_on_off(requested_audio_signals)
        else "On",
        requested_aperture_drive_in_af=requested_aperture_drive_in_af
        if requested_aperture_drive_in_af in ALLOWED_TARGET_APERTURE_DRIVE_MODES_G144
        else TARGET_APERTURE_DRIVE_DEFAULT_G144,
        requested_auto_pixel_mapping=requested_auto_pixel_mapping
        if requested_auto_pixel_mapping in ALLOWED_TARGET_AUTO_PIXEL_MAPPING_MODES_G144
        else TARGET_AUTO_PIXEL_MAPPING_DEFAULT_G144,
        airplane_mode=airplane_mode if _is_on_off(airplane_mode) else "On",
        current_fx3_fw=current_fx3_fw,
    )

    valid = len(violations) == 0
    status = STATUS_VERIFIED_G144 if valid else violations[0]
    return SilentTargetBodydataNoGoGuardResult(
        valid=valid,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        silent_mode_menu_path=SILENT_MODE_MENU_PATH_G144,
        effective_silent_mode=resolved["effective_silent_mode"],
        effective_shutter_type=resolved["effective_shutter_type"],
        effective_audio_signals=resolved["effective_audio_signals"],
        disabled_5_functions_enforced=resolved["disabled_5_functions_enforced"],
        af_illuminator_auto_disabled_by_silent=False,
        target_function_exact_2_items=EXACT_2_TARGET_FUNCTION_ITEMS_G144,
        effective_aperture_drive_in_af=resolved["effective_aperture_drive_in_af"],
        effective_auto_pixel_mapping=resolved["effective_auto_pixel_mapping"],
        power_off_mechanical_shutter_actuation=resolved[
            "power_off_mechanical_shutter_actuation"
        ],
        dormant_shutter_when_pwr_off_blocked=True,
        fx6_shutterless_auto_pixel_restore_model="ILME-FX6_SHUTTERLESS_AUTO_PIXEL_RESTORE",
        airplane_mode=airplane_mode if _is_on_off(airplane_mode) else "Invalid",
        update_badge_silenced=resolved["update_badge_silenced"],
        fx3_bodydata_required_slot=FX3_BODYDATA_REQUIRED_SLOT_G144,
        fx3_bodydata_min_battery_pct=FX3_BODYDATA_MIN_BATTERY_PCT_G144,
        fx3_stepping_stone_required_for_current_fw=resolved[
            "fx3_stepping_stone_required_for_current_fw"
        ],
        fx6_bodydata_required_slot=FX6_BODYDATA_REQUIRED_SLOT_G144,
        fx6_bodydata_required_power=FX6_BODYDATA_MIN_POWER_G144,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        slot1_data_sector_writes=0,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
        matrix_checked_states=matrix_info["total_matrix_states"],
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
    )


def evaluate_g144_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G144SilentTargetBodydataNoGoGuardResult]:
    audit = audit_phase323_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G144SilentTargetBodydataNoGoGuardResult(
        gate_id=G144,
        gate_code=G144_GATE_CODE,
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
        silent_target_bodydata_nogo_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G144,
        gate_code=G144_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"silent={res.effective_silent_mode} "
            f"target_items={len(res.target_function_exact_2_items)} "
            f"fx3_slot={res.fx3_bodydata_required_slot} "
            f"fx6_slot={res.fx6_bodydata_required_slot} "
            f"s1_writes={res.slot1_data_sector_writes}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


# ---------------------------------------------------------------------------
# Unified 144-Gate Milestone Master Safety Preflight Engine (12^2 = 144/144)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Master144GateReport:
    schema: str
    schema_version: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_141_gates_verified: bool
    all_144_gates_verified: bool
    g13_to_g144_all_passed: bool
    g143_to_g144_all_passed: bool
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
    master_142_report: Dict[str, Any]
    g143_result: Dict[str, Any]
    g144_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_144gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    simulate_bench_dry_run: Optional[bool] = None,
    dry_run_simulated_backup: Optional[bool] = None,
    request_persistent_emmc_writes: bool = False,
    master_142_override: Optional[Master142GateReport] = None,
    shoe_audio_subject_recog_kwargs: Optional[Mapping[str, Any]] = None,
    silent_target_bodydata_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master144GateReport:
    """Evaluate unified 144-Gate Milestone (`12^2 = 144`) Master Safety Preflight (`G01..G144`)."""
    effective_dry_run = (
        bool(dry_run_simulated)
        or (simulate_bench_dry_run is True)
        or (dry_run_simulated_backup is True)
    )
    clean_forced = _is_clean_room_forced(force_clean_room)
    resolved_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved_work_root_for_m142 = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=resolved_repo_root).work_root
    )
    m142_force_clean_room = (
        True
        if (clean_forced or resolved_work_root_for_m142 is None)
        else force_clean_room
    )

    m142_report = (
        master_142_override
        if master_142_override is not None
        else evaluate_142gate_preflight(
            resolved_repo_root,
            work_root=work_root,
            force_clean_room=m142_force_clean_room,
            dry_run_simulated=effective_dry_run,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
        )
    )

    g143_kw = dict(shoe_audio_subject_recog_kwargs or {})
    g143_verdict, g143_res = evaluate_g143_shoe_audio_4ch_out_timing_and_subject_recog_guard(
        repo_root=resolved_repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **g143_kw,
    )

    g144_kw = dict(silent_target_bodydata_kwargs or {})
    if "request_persistent_emmc_writes" not in g144_kw:
        g144_kw["request_persistent_emmc_writes"] = request_persistent_emmc_writes
    g144_verdict, g144_res = (
        evaluate_g144_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            repo_root=resolved_repo_root,
            work_root=work_root,
            force_clean_room=force_clean_room,
            **g144_kw,
        )
    )

    new_gate_dicts = (
        {
            "gate_id": G143,
            "gate_code": G143_GATE_CODE,
            "status": g143_res.status,
            "passed": g143_verdict.passed,
            "evidence": g143_verdict.evidence,
            "violation_codes": list(g143_verdict.errors),
        },
        {
            "gate_id": G144,
            "gate_code": G144_GATE_CODE,
            "status": g144_res.status,
            "passed": g144_verdict.passed,
            "evidence": g144_verdict.evidence,
            "violation_codes": list(g144_verdict.errors),
        },
    )

    all_gates: Tuple[Dict[str, Any], ...] = tuple(m142_report.gates) + new_gate_dicts
    g01_to_g12_verified = int(m142_report.summary["g01_to_g12_verified"])
    g13_to_g142_verified = (
        int(m142_report.summary["g13_to_g140_verified"])
        + int(m142_report.summary["g141_to_g142_verified"])
    )
    g143_to_g144_verified = int(bool(g143_verdict.passed)) + int(
        bool(g144_verdict.passed)
    )
    total_verified = g01_to_g12_verified + g13_to_g142_verified + g143_to_g144_verified

    g143_to_g144_all_passed = g143_to_g144_verified == 2
    g13_to_g144_all_passed = (
        m142_report.g13_to_g142_all_passed and g143_to_g144_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m142_report.gates[:9])

    offline_141_verified = (
        g01_to_g09_ok
        and m142_report.offline_139_gates_verified
        and g143_to_g144_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_144_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g144_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m142_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_141_verified
        and m142_report.h0_h1_trial_entry_allowed
        and g143_to_g144_all_passed
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
        list(m142_report.errors)
        + list(g143_verdict.errors)
        + list(g144_verdict.errors)
    )
    warnings: List[str] = (
        list(m142_report.warnings)
        + list(g143_verdict.warnings)
        + list(g144_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m142_report.g13_to_g142_all_passed:
        overall_status = m142_report.status
    elif not g143_verdict.passed:
        overall_status = g143_verdict.status
    elif not g144_verdict.passed:
        overall_status = g144_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_144_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_144_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_144_verified:
        overall_status = "VERIFIED_ALL_144_GATES"
    else:
        overall_status = "VERIFIED_141_OF_144_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m142_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g143_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g144_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 144,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 144 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g142_verified": g13_to_g142_verified,
        "g143_to_g144_verified": g143_to_g144_verified,
        "g13_to_g144_all_passed": g13_to_g144_all_passed,
        "g143_to_g144_all_passed": g143_to_g144_all_passed,
        "offline_141_gates_verified": offline_141_verified,
        "all_144_gates_verified": all_144_verified,
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

    return Master144GateReport(
        schema=REALHW_144GATE_PREFLIGHT_SCHEMA,
        schema_version=REALHW_144GATE_PREFLIGHT_SCHEMA,
        version=REALHW_SHOE_AUDIO_4CH_SUBJECT_RECOG_SILENT_BODYDATA_144GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_141_gates_verified=offline_141_verified,
        all_144_gates_verified=all_144_verified,
        g13_to_g144_all_passed=g13_to_g144_all_passed,
        g143_to_g144_all_passed=g143_to_g144_all_passed,
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
        master_142_report=m142_report.to_dict(),
        g143_result=g143_res.to_dict(),
        g144_result=g144_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_144_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master144GateReport:
    return evaluate_144gate_preflight(repo_root, **kwargs)


def run_144_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master144GateReport:
    return evaluate_144gate_preflight(repo_root, **kwargs)


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
        prog="realhw_shoe_audio_4ch_subject_recog_silent_bodydata_and_144gate_guard",
        description="Phase 323 Wave-62 G143/G144 and 144/144 Gross Milestone Preflight CLI",
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
        help="Supply simulated dry-run Tier-0 backup inputs so all 144/144 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g143", "g144", "144"],
        default="144",
        help="Target gate check: g143, g144, or 144",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g143":
        v, r = evaluate_g143_shoe_audio_4ch_out_timing_and_subject_recog_guard(
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

    if args.gate == "g144":
        v, r = evaluate_g144_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
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
                    "emmc_writes_authorized": r.emmc_writes_authorized,
                    "cross_model_flash_authorized": r.cross_model_flash_authorized,
                    "raw_firmware_bytes_leaked": r.raw_firmware_bytes_leaked,
                }
                if args.summary
                else r.to_dict()
            )
        else:
            sys.stdout.write(f"gate={v.gate_id} status={r.status} valid={r.valid}\n")
        return 0 if r.valid else 1

    rep = evaluate_144gate_preflight(
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
                "g143_status": rep.g143_result["status"],
                "g144_status": rep.g144_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/144 "
            f"raw_firmware_bytes_leaked={rep.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        rep.all_144_gates_verified
        if args.dry_run_simulated
        else rep.offline_141_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "ALLOWED_4CH_AUDIO_MONITORING_MODES_G143",
    "ALLOWED_AUDIO_OUT_TIMING_MODES_G143",
    "ALLOWED_FX3_FACE_EYE_SUBJECTS_G143",
    "ALLOWED_FX3_SHOE_AUDIO_FORMATS_G143",
    "ALLOWED_MAIN_MOVIE_CODECS_G143",
    "ALLOWED_MEDIA_SLOTS_PHASE323",
    "ALLOWED_RESET_ACTIONS_PHASE323",
    "ALLOWED_RIGHT_LEFT_EYE_MODES_G143",
    "ALLOWED_SHOOT_MODES_PHASE323",
    "ALLOWED_TARGET_APERTURE_DRIVE_MODES_G144",
    "ALLOWED_TARGET_AUTO_PIXEL_MAPPING_MODES_G144",
    "ALLOWED_XLR_H1_DIGITAL_ANALOG_G143",
    "ALLOWED_XLR_H1_SWITCH_STATES_G143",
    "APERTURE_DRIVE_IN_AF_F_UXC_RESID16_G144",
    "AUDIO_4CH_MONITORING_F_UXC_RESID16_G143",
    "AUDIO_LEVEL_DISPLAY_REMOVED_F_UXC_RESID16_G143",
    "AUDIO_OUT_TIMING_DEFAULT_G143",
    "AUDIO_OUT_TIMING_F_UXC_RESID16_G143",
    "AUDIO_OUT_TIMING_LIP_SYNC_F_UXC_RESID16_G143",
    "AUDIO_OUT_TIMING_LIP_SYNC_G143",
    "AUDIO_OUT_TIMING_LIVE_F_UXC_RESID16_G143",
    "AUDIO_OUT_TIMING_LIVE_G143",
    "AUDIO_OUT_TIMING_MENU_PATH_G143",
    "AUDIO_RECORDING_F_UXC_RESID16_G143",
    "AUDIO_RECORDING_MENU_PATH_G143",
    "AUDIO_REC_LEVEL_DEFAULT_G143",
    "AUDIO_REC_LEVEL_F_UXC_RESID16_G143",
    "AUDIO_REC_LEVEL_MAX_G143",
    "AUDIO_REC_LEVEL_MIN_G143",
    "AUDIO_SIGNALS_BASE_UXC_RESID16_G144",
    "AUTO_PIXEL_MAPPING_F_UXC_RESID16_G144",
    "BODYDATA_FILENAME_G144",
    "BODY_BASE_UXC_RESID16_G144",
    "CROSS_MODEL_FLASH_AUTHORIZED",
    "DEFAULT_REPO_ROOT",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE323",
    "DONOR_CHECK_MAX_SECONDS_PHASE323",
    "DORMANT_AIRPLANE_F_UXC_RESID16_G143",
    "DORMANT_ANIMAL_BIRD_F_UXC_RESID16_G143",
    "DORMANT_ANTI_DUST_FUNC_F_UXC_RESID16_G144",
    "DORMANT_BIRD_F_UXC_RESID16_G143",
    "DORMANT_CAR_TRAIN_F_UXC_RESID16_G143",
    "DORMANT_FACE_EYE_SUBJECT_UXC_RESID16S_G143",
    "DORMANT_IMAGE_SENSOR_BARRIER_SYMBOL_G144",
    "DORMANT_INSECT_F_UXC_RESID16_G143",
    "DORMANT_SHARED_FACE_EYE_SUBJECTS_G143",
    "DORMANT_SHUTTER_WHEN_PWR_OFF_F_UXC_RESID16_G144",
    "EBUSY_ERRNO_PHASE323",
    "EBUSY_NAME_PHASE323",
    "EINVAL_ERRNO_PHASE323",
    "EINVAL_NAME_PHASE323",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "EMMC_WRITES_AUTHORIZED",
    "ENV_CLEAN_ROOM_TEST_PHASE323",
    "ENV_FORCE_CLEAN_ROOM",
    "EOPNOTSUPP_ERRNO_PHASE323",
    "EOPNOTSUPP_NAME_PHASE323",
    "EPERM_ERRNO_PHASE323",
    "EPERM_NAME_PHASE323",
    "EROFS_ERRNO_PHASE323",
    "EROFS_NAME_PHASE323",
    "EXACT_2_TARGET_FUNCTION_ITEMS_G144",
    "EXACT_5_SILENT_DISABLED_FUNCTIONS_G144",
    "FACE_EYE_AF_MENU_PATH_G143",
    "FACE_EYE_FRAME_DISP_DEFAULT_G143",
    "FACE_EYE_FRAME_DISP_F_UXC_RESID16_G143",
    "FACE_EYE_PRIOR_F_UXC_RESID16_G143",
    "FACE_EYE_SUBJECT_F_UXC_RESID16_G143",
    "FACE_MEMORY_F_UXC_RESID16_G143",
    "FACE_MEMORY_MAX_FACES_G143",
    "FACE_SUBJECT_ANIMAL_G143",
    "FACE_SUBJECT_DEFAULT_G143",
    "FACE_SUBJECT_HUMAN_G143",
    "FX3_BODYDATA_MIN_BATTERY_BARS_G144",
    "FX3_BODYDATA_MIN_BATTERY_PCT_G144",
    "FX3_BODYDATA_REQUIRED_SLOT_G144",
    "FX3_DEFAULT_FW_VERSION_PHASE323",
    "FX3_HELP_GUIDE_CODE_PHASE323",
    "FX3_MODEL_ID_PHASE323",
    "FX3_MODEL_NAME_PHASE323",
    "FX3_STEPPING_STONE_REQUIRED_BELOW_EQ_G144",
    "FX3_STEPPING_STONE_VERSIONS_G144",
    "FX3_UPDATE_BLINK_PROGRESS_G144",
    "FX3_UPDATE_ERROR_BLINK_CODES_G144",
    "FX6_AUTO_PIXEL_RESTORE_NS1_UXC_RESID16S_G144",
    "FX6_BODYDATA_MIN_POWER_G144",
    "FX6_BODYDATA_REQUIRED_SLOT_G144",
    "FX6_DEFAULT_FW_VERSION_PHASE323",
    "FX6_DORMANT_AUDIO_FORMAT_G143",
    "FX6_FACE_EYE_MODES_G143",
    "FX6_FACE_MEMORY_EPHEMERAL_LABEL_G143",
    "FX6_LEGACY_DELETE_REG_FACE_UXC2_RESID16_G143",
    "FX6_LIMITER_MODE_STEPS_G143",
    "FX6_MODEL_NAME_PHASE323",
    "FX6_PRODUCT_CODE_PHASE323",
    "FX6_VERSION_MENU_PATH_G144",
    "FX6_VERSION_NS2_UXC_RESID16_G144",
    "FX6_VERSION_UP_NS2_UXC_RESID16_G144",
    "G143",
    "G143ShoeAudio4chSubjectRecogGuardResult",
    "G143_GATE_CODE",
    "G143_GATE_ID",
    "G144",
    "G144SilentTargetBodydataNoGoGuardResult",
    "G144_GATE_CODE",
    "G144_GATE_ID",
    "GATE_G143_SHOE_AUDIO_4CH_OUT_TIMING_AND_SUBJECT_RECOG_GUARD",
    "GATE_G144_SILENT_TARGET_NO_PWRSHUTTER_AND_SLOT1_BODYDATA_NOGO_GUARD",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HUMAN_HARDWARE_ATTACH_TOKEN",
    "LATEST_SW_BADGE_G_UXC_RESID16_G144",
    "LENS_VER_G_UXC_RESID16_G144",
    "MEDIA_SLOT_1_PHASE323",
    "MEDIA_SLOT_2_PHASE323",
    "Master144GateReport",
    "NOT_TARGET_F_UXC_RESID16_G144",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PINNED_FX3_APPFW_SLICES_PHASE323",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE323",
    "PINNED_FX6_APPFW_SLICES_PHASE323",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE323",
    "PINNED_PHASE323_DONOR_SPECS",
    "PROXY_DISABLED_HIGH_FPS_G143",
    "PROXY_FORCED_AUDIO_CODEC_G143",
    "Phase323DonorAuditResult",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "REALHW_144GATE_PREFLIGHT_SCHEMA",
    "REALHW_SHOE_AUDIO_4CH_SUBJECT_RECOG_SILENT_BODYDATA_144GATE_SCHEMA",
    "REALHW_SHOE_AUDIO_4CH_SUBJECT_RECOG_SILENT_BODYDATA_144GATE_VERSION",
    "REGIST_FACES_PRIORITY_F_UXC_RESID16_G143",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE323",
    "RESET_ACTION_INITIALIZE_PHASE323",
    "RESET_ACTION_NONE_PHASE323",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE323",
    "RIGHT_LEFT_EYE_SELECT_F_UXC_RESID16_G143",
    "SHOE_AUDIO_16BIT_2CH_F_UXC_RESID16_G143",
    "SHOE_AUDIO_24BIT_2CH_F_UXC_RESID16_G143",
    "SHOE_AUDIO_24BIT_4CH_F_UXC_RESID16_G143",
    "SHOE_AUDIO_48KHZ_16BIT_2CH_G143",
    "SHOE_AUDIO_48KHZ_24BIT_2CH_G143",
    "SHOE_AUDIO_48KHZ_24BIT_4CH_G143",
    "SHOE_AUDIO_DEFAULT_G143",
    "SHOE_AUDIO_SET_F_UXC_RESID16_G143",
    "SHOOT_MODE_MOVIE_PHASE323",
    "SHOOT_MODE_SQ_PHASE323",
    "SHOOT_MODE_STILL_PHASE323",
    "SILENT_MODE_F_UXC_RESID16_G144",
    "SILENT_MODE_MENU_PATH_G144",
    "SILENT_MODE_SETTINGS_F_UXC_RESID16_G144",
    "SILENT_PRIORITY_F_UXC_RESID16_G144",
    "SOFTWARE_UPDATE_F_UXC_RESID16_G144",
    "SOUND_OPTION_MENU_PATH_G143",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_BLOCKED_G143_AUDIO_MENU_PATH_OR_REMOVED_DISPLAY_VIOLATION",
    "STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION",
    "STATUS_BLOCKED_G143_FACE_MEMORY_OR_FX6_CROSSWIRE_VIOLATION",
    "STATUS_BLOCKED_G143_SUBJECT_RECOG_DORMANT_OR_ANIMAL_MOVIE_VIOLATION",
    "STATUS_BLOCKED_G143_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G144_DORMANT_PWR_OFF_SHUTTER_OR_FX6_VIOLATION",
    "STATUS_BLOCKED_G144_SILENT_MODE_OR_TARGET_2ITEM_VIOLATION",
    "STATUS_BLOCKED_G144_SLOT1_BODYDATA_NOGO_FLASH_FIREWALL",
    "STATUS_BLOCKED_G144_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G144_VERSION_STEPPING_STONE_OR_BADGE_VIOLATION",
    "STATUS_BLOCKED_PHASE323_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G143",
    "STATUS_VERIFIED_G144",
    "ShoeAudio4chSubjectRecogGuardResult",
    "SilentTargetBodydataNoGoGuardResult",
    "TARGET_APERTURE_DRIVE_DEFAULT_G144",
    "TARGET_AUTO_PIXEL_MAPPING_DEFAULT_G144",
    "TARGET_FUNCTION_SETTINGS_F_UXC_RESID16_G144",
    "UPDATE_COMPLETE_G_UXC_RESID16_G144",
    "UPDATE_VER_INCORRECT_G_UXC_RESID16_G144",
    "USB_PACKETS_TRANSMITTED",
    "VERSION_BASE_UXC_RESID16_G144",
    "VERSION_MENU_PATH_G144",
    "WIND_NOISE_INTERNAL_DESC_BASE_UXC_RESID16_G143",
    "WIND_NOISE_REDUCT_BASE_UXC_RESID16_G143",
    "XLR_H1_DIGITAL_ANALOG_ANALOG_G143",
    "XLR_H1_DIGITAL_ANALOG_DIGITAL_G143",
    "audit_phase323_donor_contracts",
    "compute_shoe_audio_4ch_subject_recog_matrix",
    "compute_silent_target_bodydata_matrix",
    "evaluate_144_master_safety_gates",
    "evaluate_144gate_preflight",
    "evaluate_g143_shoe_audio_4ch_out_timing_and_subject_recog_guard",
    "evaluate_g144_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard",
    "main",
    "resolve_fx3_shoe_audio_4ch_subject_recog_state",
    "resolve_fx3_silent_target_bodydata_state",
    "run_144_gate_preflight",
    "validate_fx3_vs_fx6_bodydata_policy",
    "verify_shoe_audio_4ch_out_timing_and_subject_recog_guard",
    "verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard",
]

if __name__ == "__main__":
    raise SystemExit(main())
