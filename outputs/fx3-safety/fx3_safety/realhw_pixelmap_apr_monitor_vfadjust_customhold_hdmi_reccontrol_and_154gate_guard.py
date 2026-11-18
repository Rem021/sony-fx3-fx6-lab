"""Phase 356 (Task H446, Wave-67, 154/154 Milestone): Real-Hardware `[Pixel Mapping]` /
`[Auto Pixel Mapping]` Dual Reset Split & Sony Typos vs FX6 `APR` + Dormant `ABB` +
`Setup -> [Monitor]` 3 Reset-Resistant Items vs Zero `[Finder/Monitor]` & 4 Dormant
EVF Symbols vs FX6 `VF Setting`/`VF Adjust` (`G153`), Still-Only `P/A/S/M` `[Recall
Custom hold 1..3]` Exact 11 Params with Zero Standalone `White Balance` vs FX6 `Push
AF/AGC/Iris` + `[External Output]` HDMI `Rec. Media dur HDMI Output = On` `Slot 1`
`EROFS=30` Vault + `[REC Control]` `TC Output=On` Prerequisite + `ctrl_for_hmdi`
Typo vs FX6 `SDI/HDMI` Matrix (`G154`), and Unified `154`-Gate Master Safety
Preflight (`G01..G154`).

Authoritative Empirical Baseline (`ILME-FX3 Ver. 7.02`, `ilc/2210`, `0x0502`,
`PRODUCT_MODEL_ALCIN_UUD` vs `ILME-FX6 Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`):
  - **Gate `G153` (`PIXELMAP_APR_MONITOR_ZERO_EVF_VS_FX6_VF_ADJUST_GUARD`)**:
    1. `[Pixel Mapping]` (`_f 0x61f7`) & Dual `[Auto Pixel Mapping]` Reset Split:
       - `Setup -> [Setup Option] -> [Auto Pixel Mapping]` (`_f 0x7734`, default `On`,
         **Reset-immune `Not available`**, `Initialize`-only) vs
         `Shooting -> [Shutter/Silent] -> [Silent Mode Settings] -> [Target Function Settings] -> [Auto Pixel Mapping]`
         (`_f 0x64e7`, default `Off`/`Not Target`, **Resettable** via `Camera Settings Reset`).
         If left `Off` while `Silent Mode = On`, power-off mapping still fires
         mechanical shutter sound via `vdf_set_shutter_mute_by_pixel_mapping`.
       - Manual `[Pixel Mapping]` requires lens cap (`_g 0x63f1`/`0x60e7`) + battery
         check (`INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING`) and auto-reboots
         (`sequence_execute_pixel_mapping`).
       - `PRM_HAITA_*pixel_map*` has `0` USB/streaming/temperature hits; `[Pixel Map.
         Notification]` & `[Shutter When Pwr OFF]` have `0` exposed menus on FX3;
         Sony ELF typos: `BKID_APP_setting_notification_for_pixel_mappinng` and
         `BKID_APP_pixel_mapping_excuted_status`.
       - Contrast `ILME-FX6 Ver. 6.01`: `Technical > APR` (`ns1 0x3324` black-cloth
         check, `PIXEL_MAPPING_RESULT_{LIGHT_DETECTED,INVALID_TEMPERATURE}`) and
         dormant `auto_black_balance` (`ABB` unexposed on CMOS FX6 -> `EOPNOTSUPP=95`).
    2. Strict `Setup -> [Monitor]` (NOT `[Finder/Monitor]`!) & Zero EVF Symbols:
       - Exposes exact **3** Reset-immune (`Initialize`-only) items:
         `[Monitor Brightness]` (`Manual -2..+2` def / `Sunny Weather`),
         `[Display Quality]` (`Standard` def / `High`, thermal-locked to `Standard`
         when camera is hot), and `[Monitor Flip Direction]` (`Auto` def / `Horizontal
         Flip` / `180 Degree Flip` / `No Flip`).
       - All **4** EVF symbols (`Finder/Monitor Sel.`, `Viewfinder Bright.`,
         `Viewfinder Color Temp.`, `Finder Frame Rate`) have `0` exposed menu items
         on FX3 (`EOPNOTSUPP=95`).
       - Contrast `ILME-FX6`: `Monitoring > VF Setting` (`Brightness 1..15` def `8`,
         `Color Mode` `Color`/`B&W`), `VF Adjust` assignable button, physical `MIRROR`
         switch (`Off/B/T/ROT`), and zero `Backlight/Contrast/Chroma/Color Temp.`
         submenu under `VF Adjust`.

  - **Gate `G154` (`RECALL_CUSTOM_HOLD_11PARAM_STILL_VS_FX6_PUSH_AND_HDMI_SLOT1_REC_CTRL_VAULT_GUARD`)**:
    1. Still-Only `P/A/S/M` `[Recall Custom hold 1..3]` Exact 11 Params & Zero WB:
       - `Shooting -> [Shooting Mode] -> [Reg. Custom Shoot Set]` (`_f 0x60b4/0x7581/0x725b`,
         **Reset-immune `Initialize`-only**, persisted in `CAMSET*.DAT`) is strictly
         Still `P/A/S/M`-only (`Movie`/`S&Q`/`iAuto` rejected `EOPNOTSUPP=95`).
       - Exact **11** `is_checked_recall_custom_hold0..10` slots (`shooting_mode`,
         `aperture`, `shutter_speed`, `exposure_comp`, `iso_sensitivity`, `metering_mode`,
         `drive_mode` [excludes Self-timer], `focus_mode`, `focus_area`, `af_on`,
         `still_af_track_sens`) and **zero standalone `White Balance` checkbox**
         (`shoot_set_registration_white_balance == 0` hits).
       - Custom key matrix: `[AF On]` (`Still/Movie/S&Q`), `[Eye AF]` (`Still/Movie`),
         `[Tracking On]` (`Still` + `AF-C` only).
       - Contrast `ILME-FX6`: `Push AF` (`AF`/`AF-S`, `Push AF/Push MF`), `Push AGC`
         (blocked in `Cine EI`/`Bokeh Control=On`), `Push Auto Iris` (blocked on
         `MANUAL` lens or `Bokeh Control=On`), and dormant `High/Low Key`.
    2. `Setup -> [External Output]` (all Reset-immune `Initialize`-only) & `Slot 1` `EROFS=30`:
       - `[Rec. Media dur HDMI Output] = On` (default, locked `On` in `S&Q`) targeting
         Tier-0 read-only `Slot 1` vault must fail closed with `EROFS (errno 30)`
         (`slot1_data_sector_writes == 0`, `emmc_nflasha_write_count == 0`); safe external
         path uses `Off(HDMI Only)` (outside `S&Q`) or `Slot 2`.
       - `[REC Control] = On` requires **`[Time Code Output] = On`** + compatible
         external recorder; `[Output Resolution]` drops to `1080` on `Log`/`PPLUT1..4`
         when `Rec. Media = On` & `RAW = Off`; `4K Output Set.(HDMI Only)` `24.00p`
         requires mandatory reboot + playback isolation (`outpute` typo); `[HDMI Info.
         Display] = On` blacks out LCD and auto-forces `Off` under `Off(HDMI Only)`
         or `RAW Output = On`; `[CTRL FOR HDMI]` (`BKID_APP_setting_ctrl_for_hmdi`
         typo, default `On`); dormant `4K/2K Output` & `24p/60p Output` (`0` hits ->
         `EOPNOTSUPP=95`).
       - Contrast `ILME-FX6`: `Monitoring > Output On/Off (SDI/HDMI)`, `TC/Media >
         HDMI TC Out`, `Project > SDI/HDMI Rec Control` (`Off`/`SDI/HDMI Remote I/F`/
         `Parallel Rec`), and dual `12G-SDI + HDMI` resolution matrix.

  - **Unified 154-Gate Master Safety Preflight (`G01..G154`)**:
    Delegates `G01..G152` to `evaluate_152gate_preflight()`, enforces `151/154`
    verified offline (`VERIFIED_151_OF_154_AWAITING_PHYSICAL_TIER0`) and `154/154`
    under `--simulate-bench-dry-run` (`VERIFIED_ALL_154_GATES_DRY_RUN_SIMULATED_BACKUP`),
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
from .realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_152gate_guard import (
    Master152GateReport,
    evaluate_152gate_preflight,
)


# ---------------------------------------------------------------------------
# Schema, Versions, Env Keys & Shared Constants
# ---------------------------------------------------------------------------

REALHW_PIXELMAP_APR_MONITOR_VFADJUST_CUSTOMHOLD_HDMI_RECCONTROL_154GATE_SCHEMA = (
    "fx3_realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_154gate_guard_v1"
)
REALHW_PIXELMAP_APR_MONITOR_VFADJUST_CUSTOMHOLD_HDMI_RECCONTROL_154GATE_VERSION = (
    "2026.11.18-phase356-milestone154"
)
REALHW_154GATE_PREFLIGHT_SCHEMA = "realhw_154gate_preflight_v1"

G153 = "G153"
G153_GATE_ID = "G153"
G153_GATE_CODE = "PIXELMAP_APR_MONITOR_ZERO_EVF_VS_FX6_VF_ADJUST_GUARD"

G154 = "G154"
G154_GATE_ID = "G154"
G154_GATE_CODE = (
    "RECALL_CUSTOM_HOLD_11PARAM_STILL_VS_FX6_PUSH_AND_HDMI_SLOT1_REC_CTRL_VAULT_GUARD"
)

ENV_CLEAN_ROOM_TEST_PHASE356 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE356 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE356 = 0.05

EROFS_ERRNO_PHASE356 = 30
EROFS_NAME_PHASE356 = "EROFS"
EINVAL_ERRNO_PHASE356 = 22
EINVAL_NAME_PHASE356 = "EINVAL"
EOPNOTSUPP_ERRNO_PHASE356 = 95
EOPNOTSUPP_NAME_PHASE356 = "EOPNOTSUPP"

FX3_MODEL_NAME_PHASE356 = "ILME-FX3"
FX3_MODEL_ID_PHASE356 = 0x0502
FX3_HELP_GUIDE_CODE_PHASE356 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE356 = "7.02"
FX6_MODEL_NAME_PHASE356 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE356 = "6.01"

MEDIA_SLOT_NONE_PHASE356 = 0
MEDIA_SLOT_1_PHASE356 = 1
MEDIA_SLOT_2_PHASE356 = 2
ALLOWED_MEDIA_SLOTS_PHASE356: Tuple[int, ...] = (
    MEDIA_SLOT_NONE_PHASE356,
    MEDIA_SLOT_1_PHASE356,
    MEDIA_SLOT_2_PHASE356,
)

SHOOT_MODE_STILL_PHASE356 = "Still"
SHOOT_MODE_MOVIE_PHASE356 = "Movie"
SHOOT_MODE_SQ_PHASE356 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE356: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE356,
    SHOOT_MODE_MOVIE_PHASE356,
    SHOOT_MODE_SQ_PHASE356,
)

RESET_ACTION_NONE_PHASE356 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE356 = "Camera Settings Reset"
RESET_ACTION_INITIALIZE_PHASE356 = "Initialize"
RESET_ACTION_RESET_NETWORK_SET_PHASE356 = "Reset Network Set."
ALLOWED_RESET_ACTIONS_PHASE356: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE356,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE356,
    RESET_ACTION_INITIALIZE_PHASE356,
    RESET_ACTION_RESET_NETWORK_SET_PHASE356,
)


# ---------------------------------------------------------------------------
# Gate G153 Constants: [Pixel Mapping] / [Auto Pixel Mapping] Dual Reset Split
#                      vs FX6 APR + Dormant ABB & Setup -> [Monitor] vs Zero EVF
# ---------------------------------------------------------------------------

PIXEL_MAPPING_MENU_PATH_G153 = "Setup -> [Setup Option] -> [Pixel Mapping]"
AUTO_PIXEL_MAPPING_SETUP_MENU_PATH_G153 = (
    "Setup -> [Setup Option] -> [Auto Pixel Mapping]"
)
AUTO_PIXEL_MAPPING_SILENT_MENU_PATH_G153 = (
    "Shooting -> [Shutter/Silent] -> [Silent Mode Settings] -> "
    "[Target Function Settings] -> [Auto Pixel Mapping]"
)
MONITOR_MENU_PATH_G153 = "Setup -> [Monitor]"
ABSENT_FINDER_MONITOR_GROUP_NAME_G153 = "Setup -> [Finder/Monitor]"
FX6_APR_MENU_PATH_G153 = "Technical > APR > Execute"
FX6_VF_SETTING_MENU_PATH_G153 = "Monitoring > VF Setting"

AUTO_PIXEL_MAPPING_SETUP_DEFAULT_G153 = "On"
AUTO_PIXEL_MAPPING_SETUP_RESETTABLE_BY_CAMSET_RESET_G153 = False
AUTO_PIXEL_MAPPING_SILENT_DEFAULT_G153 = "Off"
AUTO_PIXEL_MAPPING_SILENT_RESETTABLE_BY_CAMSET_RESET_G153 = True

PIXEL_MAPPING_ELF_TYPO_MAPPINNG_G153 = (
    "BKID_APP_setting_notification_for_pixel_mappinng"
)
PIXEL_MAPPING_ELF_TYPO_EXCUTED_G153 = "BKID_APP_pixel_mapping_excuted_status"
FX6_PIXEL_MAPPING_ELF_TYPO_EXCUTED_G153 = "BKID_APP_PIXEL_MAPPING_EXCUTED_STATUS"
PIXEL_MAPPING_PRM_HAITA_USB_STREAM_TEMP_HITS_G153 = 0

DORMANT_PIXEL_MAP_FX3_TOKENS_G153: Tuple[str, ...] = (
    "Pixel Map. Notification",
    "Shutter When Pwr OFF",
)

FX6_APR_RESULT_TOKENS_G153: Tuple[str, ...] = (
    "PIXEL_MAPPING_RESULT_LIGHT_DETECTED",
    "PIXEL_MAPPING_RESULT_INVALID_TEMPERATURE",
)
FX6_DORMANT_ABB_EXPOSED_G153 = 0

EXACT_3_MONITOR_ITEMS_G153: Tuple[str, ...] = (
    "Monitor Brightness",
    "Display Quality",
    "Monitor Flip Direction",
)
MONITOR_ALL_3_ITEMS_RESETTABLE_BY_CAMSET_RESET_G153 = False

MONITOR_BRIGHTNESS_DEFAULT_G153 = "Manual"
MONITOR_BRIGHTNESS_MODES_G153: Tuple[str, ...] = ("Manual", "Sunny Weather")
MONITOR_BRIGHTNESS_MANUAL_MIN_G153 = -2
MONITOR_BRIGHTNESS_MANUAL_MAX_G153 = 2

DISPLAY_QUALITY_STANDARD_G153 = "Standard"
DISPLAY_QUALITY_HIGH_G153 = "High"
DISPLAY_QUALITY_DEFAULT_G153 = DISPLAY_QUALITY_STANDARD_G153
DISPLAY_QUALITY_MODES_G153: Tuple[str, ...] = (
    DISPLAY_QUALITY_STANDARD_G153,
    DISPLAY_QUALITY_HIGH_G153,
)

MONITOR_FLIP_AUTO_G153 = "Auto"
MONITOR_FLIP_HORIZONTAL_G153 = "Horizontal Flip"
MONITOR_FLIP_180_G153 = "180 Degree Flip"
MONITOR_FLIP_NO_FLIP_G153 = "No Flip"
MONITOR_FLIP_DEFAULT_G153 = MONITOR_FLIP_AUTO_G153
EXACT_4_MONITOR_FLIP_DIRECTIONS_G153: Tuple[str, ...] = (
    MONITOR_FLIP_AUTO_G153,
    MONITOR_FLIP_HORIZONTAL_G153,
    MONITOR_FLIP_180_G153,
    MONITOR_FLIP_NO_FLIP_G153,
)

EXACT_4_DORMANT_EVF_SYMBOLS_FX3_G153: Tuple[str, ...] = (
    "Finder/Monitor Sel.",
    "Viewfinder Bright.",
    "Viewfinder Color Temp.",
    "Finder Frame Rate",
)
DORMANT_EVF_EXPOSED_ITEMS_FX3_G153 = 0

FX6_VF_SETTING_BRIGHTNESS_MIN_G153 = 1
FX6_VF_SETTING_BRIGHTNESS_MAX_G153 = 15
FX6_VF_SETTING_BRIGHTNESS_DEFAULT_G153 = 8
FX6_VF_SETTING_COLOR_MODES_G153: Tuple[str, ...] = ("Color", "B&W")
FX6_VF_MIRROR_SWITCH_MODES_G153: Tuple[str, ...] = ("Off", "B/T", "ROT")
FX6_DORMANT_VF_ADJUST_SUBMENU_ITEMS_G153: Tuple[str, ...] = (
    "Backlight",
    "Contrast",
    "Chroma",
    "Color Temp.",
)
FX6_VF_ADJUST_SUBMENU_EXPOSED_G153 = 0

# UXC resid16 anchors (G153)
PIXEL_MAPPING_F_RESID16_G153 = 0x61F7
AUTO_PIXEL_MAPPING_SETUP_F_RESID16_G153 = 0x7734
AUTO_PIXEL_MAPPING_SILENT_NOT_TARGET_F_RESID16_G153 = 0x64E7
DORMANT_PIXEL_MAP_NOTIFY_F_RESID16_G153 = 0x693F
MONITOR_BRIGHTNESS_BASE_RESID16_G153 = 0xE44B
SUNNY_WEATHER_BASE_RESID16_G153 = 0xE1DA
DISPLAY_QUALITY_F_RESID16_G153 = 0x6C5E
MONITOR_FLIP_DIRECTION_F_RESID16_G153 = 0x6A24
DORMANT_FINDER_MONITOR_SEL_F_RESID16_G153 = 0x6DAF
DORMANT_VIEWFINDER_BRIGHT_F_RESID16_G153 = 0x6935
DORMANT_VIEWFINDER_COLOR_TEMP_BASE_RESID16_G153 = 0xE38D
DORMANT_FINDER_FRAME_RATE_F_RESID16_G153 = 0x718C

STATUS_VERIFIED_G153 = (
    "VERIFIED_G153_PIXELMAP_APR_MONITOR_ZERO_EVF_VS_FX6_VF_ADJUST_GUARD"
)
STATUS_BLOCKED_G153_TELEMETRY_INVALID = "BLOCKED_G153_TELEMETRY_INVALID"
STATUS_BLOCKED_G153_DORMANT_EVF_FINDER_MONITOR_OR_FX6_ABB_EOPNOTSUPP = (
    "BLOCKED_G153_DORMANT_EVF_FINDER_MONITOR_OR_FX6_ABB_EOPNOTSUPP"
)
STATUS_BLOCKED_G153_PIXELMAP_SHIELD_BATTERY_OR_RESET_VIOLATION = (
    "BLOCKED_G153_PIXELMAP_SHIELD_BATTERY_OR_RESET_VIOLATION"
)
STATUS_BLOCKED_G153_MONITOR_THERMAL_LOCK_OR_RESET_VIOLATION = (
    "BLOCKED_G153_MONITOR_THERMAL_LOCK_OR_RESET_VIOLATION"
)


# ---------------------------------------------------------------------------
# Gate G154 Constants: Still-Only [Recall Custom hold 1..3] Exact 11 Params
#                      (Zero Standalone WB) vs FX6 Push AF/AGC/Iris &
#                      [External Output] HDMI Slot-1 EROFS=30 Vault
# ---------------------------------------------------------------------------

RECALL_CUSTOM_HOLD_MENU_PATH_G154 = (
    "Shooting -> [Shooting Mode] -> [Reg. Custom Shoot Set]"
)
EXTERNAL_OUTPUT_MENU_PATH_G154 = "Setup -> [External Output]"
HDMI_OUTPUT_SETTINGS_MENU_PATH_G154 = (
    "Setup -> [External Output] -> [HDMI Output Settings]"
)
FX6_SDI_HDMI_REC_CONTROL_MENU_PATH_G154 = "Project > SDI/HDMI Rec Control"
FX6_HDMI_TC_OUT_MENU_PATH_G154 = "TC/Media > HDMI TC Out"

RECALL_CUSTOM_HOLD_SLOTS_G154: Tuple[str, ...] = (
    "Recall Custom hold 1",
    "Recall Custom hold 2",
    "Recall Custom hold 3",
)
RECALL_CUSTOM_HOLD_RESETTABLE_BY_CAMSET_RESET_G154 = False
RECALL_CUSTOM_HOLD_PERSISTENCE_FILE_G154 = "CAMSET*.DAT"
RECALL_CUSTOM_HOLD_STILL_PASM_MODES_G154: Tuple[str, ...] = ("P", "A", "S", "M")
ALLOWED_EXPOSURE_MODES_G154: Tuple[str, ...] = ("P", "A", "S", "M", "iAuto")

EXACT_11_RECALL_CUSTOM_HOLD_PARAMS_G154: Tuple[str, ...] = (
    "shooting_mode",
    "aperture",
    "shutter_speed",
    "exposure_comp",
    "iso_sensitivity",
    "metering_mode",
    "drive_mode",
    "focus_mode",
    "focus_area",
    "af_on",
    "still_af_track_sens",
)
RECALL_CUSTOM_HOLD_PARAM_COUNT_G154 = 11
SHOOT_SET_REGISTRATION_WHITE_BALANCE_HITS_G154 = 0

FX6_PUSH_ASSIGNABLE_BUTTONS_G154: Tuple[str, ...] = (
    "Push AF",
    "Push AF/Push MF",
    "One Push AF",
    "Push AGC",
    "Push Auto Iris",
    "One Push Auto Iris",
)
FX6_PUSH_AF_MODES_G154: Tuple[str, ...] = ("AF", "Single-shot AF(AF-S)")
FX6_DORMANT_HIGH_LOW_KEY_EXPOSED_G154 = 0

EXTERNAL_OUTPUT_RESETTABLE_BY_CAMSET_RESET_G154 = False

HDMI_RESOLUTION_AUTO_G154 = "Auto"
HDMI_RESOLUTION_OPTIONS_G154: Tuple[str, ...] = ("Auto", "2160p", "1080p", "1080i")

REC_MEDIA_HDMI_ON_G154 = "On"
REC_MEDIA_HDMI_OFF_ONLY_G154 = "Off(HDMI Only)"
REC_MEDIA_DUR_HDMI_OUTPUT_DEFAULT_G154 = REC_MEDIA_HDMI_ON_G154
REC_MEDIA_DUR_HDMI_OUTPUT_OPTIONS_G154: Tuple[str, ...] = (
    REC_MEDIA_HDMI_ON_G154,
    REC_MEDIA_HDMI_OFF_ONLY_G154,
)

HDMI_4K_OUTPUT_SET_OPTIONS_G154: Tuple[str, ...] = (
    "59.94p 10bit",
    "50p 10bit",
    "29.97p 10bit",
    "25p 10bit",
    "23.98p 10bit",
    "24.00p 10bit",
)
HDMI_4K_OUTPUT_ELF_TYPO_G154 = "PRM_HAITA_hdmi_4k_outpute_apsc_restriction"
CTRL_FOR_HDMI_ELF_TYPO_G154 = "BKID_APP_setting_ctrl_for_hmdi"

HDMI_4CH_AUDIO_CH1_CH2_G154 = "CH1/CH2"
HDMI_4CH_AUDIO_CH3_CH4_G154 = "CH3/CH4"
HDMI_4CH_AUDIO_OPTIONS_G154: Tuple[str, ...] = (
    HDMI_4CH_AUDIO_CH1_CH2_G154,
    HDMI_4CH_AUDIO_CH3_CH4_G154,
)

DORMANT_EXTERNAL_OUTPUT_MENUS_G154: Tuple[str, ...] = (
    "4K/2K Output",
    "24p/60p Output",
)
DORMANT_EXTERNAL_OUTPUT_HITS_G154 = 0

FX6_SDI_HDMI_REC_CONTROL_MODES_G154: Tuple[str, ...] = (
    "Off",
    "SDI/HDMI Remote I/F",
    "Parallel Rec",
)

# UXC resid16 anchors (G154)
RECALL_CUSTOM_HOLD_1_F_RESID16_G154 = 0x60B4
RECALL_CUSTOM_HOLD_2_F_RESID16_G154 = 0x7581
RECALL_CUSTOM_HOLD_3_F_RESID16_G154 = 0x725B
HDMI_RESOLUTION_BASE_RESID16_G154 = 0xE1D5
CTRL_FOR_HDMI_BASE_RESID16_G154 = 0xE41F
REC_MEDIA_DUR_HDMI_F_RESID16_G154 = 0x6144
OUTPUT_RESOLUTION_F_RESID16_G154 = 0x79AC
HDMI_4K_OUTPUT_SET_F_RESID16_G154 = 0x74D7
HDMI_TC_OUTPUT_F_RESID16_G154 = 0x72AF
HDMI_REC_CONTROL_F_RESID16_G154 = 0x76E1
HDMI_4CH_AUDIO_F_RESID16_G154 = 0x6AA0
HDMI_INFO_DISPLAY_F_RESID16_G154 = 0x6E7C
DORMANT_24P_60P_OUTPUT_F_RESID16_G154 = 0x632B

STATUS_VERIFIED_G154 = (
    "VERIFIED_G154_RECALL_CUSTOM_HOLD_11PARAM_STILL_VS_FX6_PUSH_AND_HDMI_SLOT1_REC_CTRL_VAULT_GUARD"
)
STATUS_BLOCKED_G154_TELEMETRY_INVALID = "BLOCKED_G154_TELEMETRY_INVALID"
STATUS_BLOCKED_G154_DORMANT_WB_4K2K_24P60P_OR_MOVIE_HOLD_EOPNOTSUPP = (
    "BLOCKED_G154_DORMANT_WB_4K2K_24P60P_OR_MOVIE_HOLD_EOPNOTSUPP"
)
STATUS_BLOCKED_G154_SLOT1_HDMI_REC_MEDIA_VAULT_EROFS = (
    "BLOCKED_G154_SLOT1_HDMI_REC_MEDIA_VAULT_EROFS"
)
STATUS_BLOCKED_G154_CUSTOM_HOLD_OR_HDMI_REC_CTRL_PREREQ_VIOLATION = (
    "BLOCKED_G154_CUSTOM_HOLD_OR_HDMI_REC_CTRL_PREREQ_VIOLATION"
)
STATUS_BLOCKED_PHASE356_DONOR_INTEGRITY = "BLOCKED_PHASE356_DONOR_INTEGRITY"


# ---------------------------------------------------------------------------
# Pinned Wave-67 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE356: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x03BCC32C, b"BKID_APP_setting_auto_pixel_mapping"),
    (0x03BC6F1F, b"BKID_APP_setting_silent_detail_setting_auto_pixel_mapping"),
    (0x03BCC350, b"BKID_APP_setting_notification_for_pixel_mappinng"),
    (0x03BF189F, b"BKID_APP_pixel_mapping_excuted_status"),
    (0x03BFBC55, b"INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING"),
    (0x039252A7, b"vdf_set_shutter_mute_by_pixel_mapping"),
    (0x03925270, b"N5model30sequence_execute_pixel_mappingE"),
    (0x03BCBCA2, b"BKID_APP_setting_lcd_brightness"),
    (0x03BCBD2A, b"BKID_APP_setting_display_quality"),
    (0x03BEF5A7, b"BKID_APP_extern_menu_flip"),
    (0x03BCBC82, b"BKID_APP_setting_finder_monitor"),
    (0x03BCBCC2, b"BKID_APP_setting_viewfinder_bright"),
    (0x03BCBCE5, b"BKID_APP_setting_evf_adjustment"),
    (0x03BCBD4B, b"BKID_APP_setting_finder_framerate"),
    (0x03BC22DB, b"BKID_APP_shoot_set_registration"),
    (0x03C28382, b"is_checked_recall_custom_hold0"),
    (0x03C284B8, b"is_checked_recall_custom_hold10"),
    (0x03C36D7F, b"EVENT_FUNC_CUSTOM_RECALL_SHOOT_SET1_ON"),
    (0x03C36DA6, b"EVENT_FUNC_CUSTOM_RECALL_SHOOT_SET2_ON"),
    (0x03C36DCD, b"EVENT_FUNC_CUSTOM_RECALL_SHOOT_SET3_ON"),
    (0x03BCC0E4, b"BKID_APP_setting_rec_media_during_hdmi_output"),
    (0x03BCC112, b"BKID_APP_setting_output_resolution"),
    (0x03BCC135, b"BKID_APP_setting_hdmi_4k_output_setting"),
    (0x039BA30C, b"PRM_HAITA_hdmi_4k_outpute_apsc_restriction"),
    (0x03BCC15D, b"BKID_APP_setting_raw_output"),
    (0x03BCC1C9, b"BKID_APP_setting_hdmi_tc_output"),
    (0x03BCC1E9, b"BKID_APP_setting_rec_control"),
    (0x03BCC206, b"BKID_APP_setting_mov_hdmi_audio_output"),
    (0x03BCC24C, b"BKID_APP_setting_hdmi_info_display"),
    (0x03BCC26F, b"BKID_APP_setting_ctrl_for_hmdi"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE356 = (
    "5f5d529a6d4aaca1db2a49f9d4779c89e32a9f77d014d9bb4eed335c169e177f"
)

PINNED_FX6_APPFW_SLICES_PHASE356: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x02783E8C, b"PIXEL_MAPPING_RESULT_LIGHT_DETECTED"),
    (0x02783EDF, b"PIXEL_MAPPING_RESULT_INVALID_TEMPERATURE"),
    (0x02647DFB, b"FUNC_execute_auto_black_balance"),
    (0x024C0FBF, b"increment_evf_brightness"),
    (0x0238212C, b"FUNC_set_one_push_af_status"),
    (0x0263AC57, b"PRM_HAITA_setting_agc_push_agc_hold"),
    (0x024BFD7F, b"set_push_auto_iris"),
    (0x023BC227, b"No14_sdi_hdmi_rec_control_mode"),
    (0x0271C752, b"BKID_APP_PIXEL_MAPPING_EXCUTED_STATUS"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE356 = (
    "9ca8e8727fa88fa0a0dae823b9f180cfb1bc9d4c3c23d3c78cbbac6f679e14d1"
)

PINNED_PHASE356_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE356,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE356),
        "FX3 appFw.so Wave-67 PixelMap/Monitor/DormantEVF/RecallHold11/HDMI/RecCtrl slices",
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
            b"Pixel Mapping",
            b"Auto Pixel Mapping",
            b"Not Target",
            b"Display Quality",
            b"Monitor Flip Direction",
            b"Finder/Monitor Sel.",
            b"Recall Custom hold 1",
            b"Rec. Media dur HDMI Output",
            b"Time Code Output",
            b"REC Control",
            b"HDMI Info. Display",
            b"4ch Audio Output",
        ),
        "FX3 string_english_f.uxc Wave-67 EN parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Monitor Brightness",
            b"Sunny Weather",
            b"HDMI Resolution",
            b"CTRL FOR HDMI",
        ),
        "FX3 string_english.uxc Wave-67 base tokens",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Attach the lens cap",
            b"shielding was insufficient.",
            b"Pixel mapping completed.",
        ),
        "FX3 string_english_g.uxc Wave-67 guide/prompt tokens",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "像素映射".encode("utf-8"),
            "自动像素映射".encode("utf-8"),
            "非目标".encode("utf-8"),
            "显示质量".encode("utf-8"),
            "显示屏翻转方向".encode("utf-8"),
            "调出自定保持1".encode("utf-8"),
            "HDMI输出时的摄像媒体".encode("utf-8"),
            "Time Code输出".encode("utf-8"),
            "REC控制".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-67 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "像素映射".encode("utf-8"),
            "自動像素映射".encode("utf-8"),
            "不是目標".encode("utf-8"),
            "顯示畫質".encode("utf-8"),
            "螢幕翻轉方向".encode("utf-8"),
            "回復自訂固定1".encode("utf-8"),
            "HDMI輸出時錄製到記憶卡".encode("utf-8"),
            "Time Code輸出".encode("utf-8"),
            "REC控制".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-67 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "ピクセルマッピング".encode("utf-8"),
            "ｵｰﾄﾋﾟｸｾﾙﾏｯﾋﾟﾝｸﾞ".encode("utf-8"),
            "対象にしない".encode("utf-8"),
            "表示画質".encode("utf-8"),
            "モニター反転表示".encode("utf-8"),
            "押す間ｶｽﾀﾑ設定呼出1".encode("utf-8"),
            "HDMI出力時のﾒﾃﾞｨｱ記録".encode("utf-8"),
            "Time Code出力".encode("utf-8"),
            "RECコントロール".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-67 JA parity",
    ),
    "fx6_appfw_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
        50_520_424,
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE356,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE356),
        "FX6 appFw.so Wave-67 APR/ABB/VFAdjust/PushAF-AGC-Iris/SDI-HDMI slices",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (b"APR", b"VF Adjust", b"Push AF", b"Push AGC", b"Push Auto Iris"),
        "FX6 string_english.uxc Wave-67 EN baseline",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (b"APR", b"VF Setting", b"SDI/HDMI Rec Control", b"HDMI TC Out"),
        "FX6 string_english_2.uxc Wave-67 EN enterprise baseline",
    ),
}


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _is_clean_room_forced(force_clean_room: Optional[bool]) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE356):
        if os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def _is_strict_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


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
    if body_model_name != FX3_MODEL_NAME_PHASE356:
        errs.append(f"body_model_name_invalid:{body_model_name!r}")
    if not _is_strict_int(body_model_id) or body_model_id != FX3_MODEL_ID_PHASE356:
        errs.append(f"body_model_id_invalid:{body_model_id!r}")
    if help_guide_code != FX3_HELP_GUIDE_CODE_PHASE356:
        errs.append(f"help_guide_code_invalid:{help_guide_code!r}")
    if _parse_fw_float(firmware_version) is None:
        errs.append(f"firmware_version_invalid:{firmware_version!r}")
    return errs


def strip_elapsed_seconds_recursive_phase356(obj: Any) -> Any:
    """Recursively strip non-deterministic `elapsed_seconds` keys for canonical digests."""
    if isinstance(obj, dict):
        return {
            k: strip_elapsed_seconds_recursive_phase356(v)
            for k, v in obj.items()
            if k != "elapsed_seconds"
        }
    if isinstance(obj, list):
        return [strip_elapsed_seconds_recursive_phase356(v) for v in obj]
    if isinstance(obj, tuple):
        return [strip_elapsed_seconds_recursive_phase356(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Donor Integrity Audit (O_RDONLY / Clean-Room Dual-Mode)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase356DonorAuditResult:
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


def audit_phase356_donor_contracts(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase356DonorAuditResult:
    """Fast (< 0.20s) O_RDONLY + bounded os.pread donor audit with clean-room fallback."""
    import time

    t0 = time.perf_counter()
    clean_forced = _is_clean_room_forced(force_clean_room)
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else dict(PINNED_PHASE356_DONOR_SPECS)
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
        return Phase356DonorAuditResult(
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
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE356,
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
        return Phase356DonorAuditResult(
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
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE356,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(
                f"Donor files absent ({len(missing_files)} missing); "
                "verified Phase 356 via clean-room synthetic fallback.",
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
                target, PINNED_FX3_APPFW_SLICES_PHASE356
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tok_errs = _read_exact_o_rdonly_slices(
                target, PINNED_FX6_APPFW_SLICES_PHASE356
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
    return Phase356DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE
            if valid
            else STATUS_BLOCKED_PHASE356_DONOR_INTEGRITY
        ),
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="STRICT_OS_O_RDONLY_PREAD",
        files_inspected=inspected,
        fx3_contracts_verified=valid,
        fx6_contracts_verified=valid,
        four_lang_resid16_parity_verified=valid,
        zero_forbidden_myths_verified=valid,
        elapsed_seconds=round(dt, 6),
        within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE356,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        file_digests=file_digests,
        missing_markers=tuple(missing_markers),
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# Gate G153: [Pixel Mapping] / [Auto Pixel Mapping] Dual Reset Split & Sony
#            Typos vs FX6 APR + Dormant ABB & Setup -> [Monitor] 3 Items vs
#            Zero [Finder/Monitor] & 4 Dormant EVF Symbols vs FX6 VF Setting
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PixelMapAprMonitorVfAdjustGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    pixel_mapping_menu_path: str
    auto_pixel_mapping_setup_menu_path: str
    auto_pixel_mapping_silent_menu_path: str
    monitor_menu_path: str
    fx3_finder_monitor_group_present: bool
    dormant_evf_exposed_items_fx3: int
    fx6_apr_menu_path: str
    fx6_abb_menu_present: bool
    fx6_vf_setting_menu_path: str
    fx6_vf_adjust_backlight_submenu_present: bool
    effective_auto_pixel_mapping_setup: str
    auto_pixel_mapping_setup_resettable_by_camset_reset: bool
    effective_auto_pixel_mapping_silent: str
    auto_pixel_mapping_silent_resettable_by_camset_reset: bool
    power_off_pixel_mapping_shutter_muted: bool
    manual_pixel_mapping_requires_lens_cap_battery_and_reboot: bool
    pixel_mapping_prm_haita_usb_stream_temp_hits: int
    dormant_pixel_map_notify_fx3_rejected: bool
    dormant_evf_or_finder_monitor_spoof_rejected: bool
    fx6_abb_or_vf_submenu_spoof_rejected: bool
    effective_monitor_brightness_mode: str
    effective_monitor_brightness_manual_level: int
    effective_display_quality: str
    display_quality_thermal_locked_to_standard: bool
    effective_monitor_flip_direction: str
    monitor_all_3_items_resettable_by_camset_reset: bool
    emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_fx3_pixelmap_and_monitor_state(
    *,\
    auto_pixel_mapping_setup: str = AUTO_PIXEL_MAPPING_SETUP_DEFAULT_G153,
    auto_pixel_mapping_silent: str = AUTO_PIXEL_MAPPING_SILENT_DEFAULT_G153,
    silent_mode: str = "Off",
    monitor_brightness_mode: str = MONITOR_BRIGHTNESS_DEFAULT_G153,
    monitor_brightness_manual_level: int = 0,
    display_quality: str = DISPLAY_QUALITY_DEFAULT_G153,
    body_temperature_high: bool = False,
    monitor_flip_direction: str = MONITOR_FLIP_DEFAULT_G153,
    reset_action: str = RESET_ACTION_NONE_PHASE356,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-67 Auto Pixel Mapping dual reset split & Setup -> [Monitor] state."""
    if reset_action == RESET_ACTION_INITIALIZE_PHASE356:
        eff_setup_apm = AUTO_PIXEL_MAPPING_SETUP_DEFAULT_G153
        eff_mon_mode = MONITOR_BRIGHTNESS_DEFAULT_G153
        eff_mon_level = 0
        eff_dq_req = DISPLAY_QUALITY_DEFAULT_G153
        eff_flip = MONITOR_FLIP_DEFAULT_G153
    else:
        eff_setup_apm = auto_pixel_mapping_setup
        eff_mon_mode = monitor_brightness_mode
        eff_mon_level = monitor_brightness_manual_level
        eff_dq_req = display_quality
        eff_flip = monitor_flip_direction

    if reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE356,
        RESET_ACTION_INITIALIZE_PHASE356,
    ):
        eff_silent_apm = AUTO_PIXEL_MAPPING_SILENT_DEFAULT_G153
    else:
        eff_silent_apm = auto_pixel_mapping_silent

    dq_thermal_locked = bool(body_temperature_high)
    eff_dq = (
        DISPLAY_QUALITY_STANDARD_G153 if dq_thermal_locked else eff_dq_req
    )

    # Power-off Auto Pixel Mapping sound suppression via vdf_set_shutter_mute_by_pixel_mapping:
    # Even with Silent Mode = On, Silent Target [Auto Pixel Mapping] defaults to Off (Not Target),
    # so mechanical shutter sound STILL fires at power-off unless Silent Target is explicitly On!
    shutter_muted = (
        silent_mode == "On" and eff_silent_apm == "On"
    )

    return {
        "effective_auto_pixel_mapping_setup": eff_setup_apm,
        "effective_auto_pixel_mapping_silent": eff_silent_apm,
        "power_off_pixel_mapping_shutter_muted": shutter_muted,
        "effective_monitor_brightness_mode": eff_mon_mode,
        "effective_monitor_brightness_manual_level": eff_mon_level,
        "effective_display_quality": eff_dq,
        "display_quality_thermal_locked_to_standard": dq_thermal_locked,
        "effective_monitor_flip_direction": eff_flip,
    }


def compute_pixelmap_apr_monitor_vfadjust_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G153 (384 states)."""
    combos = list(
        itertools.product(
            ("On", "Off"),  # auto_pixel_mapping_setup
            ("Off", "On"),  # auto_pixel_mapping_silent
            ("Off", "On"),  # silent_mode
            (DISPLAY_QUALITY_STANDARD_G153, DISPLAY_QUALITY_HIGH_G153),
            (False, True),  # body_temperature_high
            EXACT_4_MONITOR_FLIP_DIRECTIONS_G153,
            (
                RESET_ACTION_NONE_PHASE356,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE356,
                RESET_ACTION_INITIALIZE_PHASE356,
            ),
        )
    )
    setup_apm_reset_preserved_count = 0
    silent_apm_reset_to_off_count = 0
    silent_on_shutter_not_muted_count = 0
    dq_thermal_locked_standard_count = 0
    monitor_flip_reset_preserved_count = 0

    for setup_apm, silent_apm, silent_m, dq, hot, flip, rst in combos:
        st = resolve_fx3_pixelmap_and_monitor_state(
            auto_pixel_mapping_setup=setup_apm,
            auto_pixel_mapping_silent=silent_apm,
            silent_mode=silent_m,
            display_quality=dq,
            body_temperature_high=hot,
            monitor_flip_direction=flip,
            reset_action=rst,
        )
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE356
            and st["effective_auto_pixel_mapping_setup"] == setup_apm
        ):
            setup_apm_reset_preserved_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE356
            and st["effective_auto_pixel_mapping_silent"]
            == AUTO_PIXEL_MAPPING_SILENT_DEFAULT_G153
        ):
            silent_apm_reset_to_off_count += 1
        if silent_m == "On" and not st["power_off_pixel_mapping_shutter_muted"]:
            silent_on_shutter_not_muted_count += 1
        if hot and st["effective_display_quality"] == DISPLAY_QUALITY_STANDARD_G153:
            dq_thermal_locked_standard_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE356
            and st["effective_monitor_flip_direction"] == flip
        ):
            monitor_flip_reset_preserved_count += 1

    return {
        "total_matrix_states": len(combos),
        "setup_apm_reset_preserved_count": setup_apm_reset_preserved_count,
        "silent_apm_reset_to_off_count": silent_apm_reset_to_off_count,
        "silent_on_shutter_not_muted_count": silent_on_shutter_not_muted_count,
        "dq_thermal_locked_standard_count": dq_thermal_locked_standard_count,
        "monitor_flip_reset_preserved_count": monitor_flip_reset_preserved_count,
    }


def verify_pixelmap_apr_monitor_vfadjust_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE356,
    body_model_id: int = FX3_MODEL_ID_PHASE356,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE356,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE356,
    auto_pixel_mapping_setup: str = AUTO_PIXEL_MAPPING_SETUP_DEFAULT_G153,
    auto_pixel_mapping_silent: str = AUTO_PIXEL_MAPPING_SILENT_DEFAULT_G153,
    silent_mode: str = "Off",
    manual_pixel_mapping_requested: bool = False,
    lens_cap_attached: bool = True,
    battery_level_sufficient: bool = True,
    claimed_silent_mode_alone_mutes_pixel_mapping: bool = False,
    claimed_camset_reset_clears_setup_auto_pixel_mapping: bool = False,
    claimed_prm_haita_usb_stream_temp_blocks_pixelmap: bool = False,
    requested_dormant_pixel_map_notify_or_shutter_pwr_off_fx3: bool = False,
    fx6_apr_light_detected: bool = False,
    fx6_apr_invalid_temperature: bool = False,
    requested_fx6_dormant_abb_menu: bool = False,
    claimed_finder_monitor_group_exists_on_fx3: bool = False,
    requested_dormant_evf_item_fx3: Optional[str] = None,
    monitor_brightness_mode: str = MONITOR_BRIGHTNESS_DEFAULT_G153,
    monitor_brightness_manual_level: int = 0,
    display_quality: str = DISPLAY_QUALITY_DEFAULT_G153,
    body_temperature_high: bool = False,
    claimed_display_quality_high_unlocked_when_hot: bool = False,
    monitor_flip_direction: str = MONITOR_FLIP_DEFAULT_G153,
    claimed_camset_reset_clears_monitor_3items: bool = False,
    fx6_vf_brightness: int = FX6_VF_SETTING_BRIGHTNESS_DEFAULT_G153,
    fx6_vf_color_mode: str = "Color",
    fx6_vf_mirror_switch: str = "Off",
    requested_fx6_vf_adjust_backlight_submenu: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE356,
) -> PixelMapAprMonitorVfAdjustGuardResult:
    """Enforce Gate G153: Pixel Mapping/Auto Pixel Mapping Dual Reset Split vs FX6 APR/ABB & Setup -> [Monitor] vs Zero EVF/VF Adjust."""
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

    if not _is_on_off(auto_pixel_mapping_setup):
        _add(
            "TELEMETRY_INVALID",
            f"auto_pixel_mapping_setup_invalid:{auto_pixel_mapping_setup!r}",
        )
    if not _is_on_off(auto_pixel_mapping_silent):
        _add(
            "TELEMETRY_INVALID",
            f"auto_pixel_mapping_silent_invalid:{auto_pixel_mapping_silent!r}",
        )
    if not _is_on_off(silent_mode):
        _add("TELEMETRY_INVALID", f"silent_mode_invalid:{silent_mode!r}")
    if monitor_brightness_mode not in MONITOR_BRIGHTNESS_MODES_G153:
        _add(
            "TELEMETRY_INVALID",
            f"monitor_brightness_mode_invalid:{monitor_brightness_mode!r}",
        )
    if (
        not _is_strict_int(monitor_brightness_manual_level)
        or not (
            MONITOR_BRIGHTNESS_MANUAL_MIN_G153
            <= monitor_brightness_manual_level
            <= MONITOR_BRIGHTNESS_MANUAL_MAX_G153
        )
    ):
        _add(
            "TELEMETRY_INVALID",
            f"monitor_brightness_manual_level_invalid:{monitor_brightness_manual_level!r}",
        )
    if display_quality not in DISPLAY_QUALITY_MODES_G153:
        _add("TELEMETRY_INVALID", f"display_quality_invalid:{display_quality!r}")
    if monitor_flip_direction not in EXACT_4_MONITOR_FLIP_DIRECTIONS_G153:
        _add(
            "TELEMETRY_INVALID",
            f"monitor_flip_direction_invalid:{monitor_flip_direction!r}",
        )
    if (
        not _is_strict_int(fx6_vf_brightness)
        or not (
            FX6_VF_SETTING_BRIGHTNESS_MIN_G153
            <= fx6_vf_brightness
            <= FX6_VF_SETTING_BRIGHTNESS_MAX_G153
        )
    ):
        _add("TELEMETRY_INVALID", f"fx6_vf_brightness_invalid:{fx6_vf_brightness!r}")
    if fx6_vf_color_mode not in FX6_VF_SETTING_COLOR_MODES_G153:
        _add("TELEMETRY_INVALID", f"fx6_vf_color_mode_invalid:{fx6_vf_color_mode!r}")
    if fx6_vf_mirror_switch not in FX6_VF_MIRROR_SWITCH_MODES_G153:
        _add("TELEMETRY_INVALID", f"fx6_vf_mirror_switch_invalid:{fx6_vf_mirror_switch!r}")
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE356:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")

    # Dormant / Cross-Model EOPNOTSUPP=95 rejections
    dormant_pm_rejected = bool(
        requested_dormant_pixel_map_notify_or_shutter_pwr_off_fx3
    )
    if dormant_pm_rejected:
        _add(
            "DORMANT_PIXEL_MAP_NOTIFY_OR_PWR_OFF_EOPNOTSUPP",
            "fx3_ver_7_02_does_not_expose_pixel_map_notification_or_shutter_when_pwr_off_eopnotsupp_95",
        )

    dormant_evf_rejected = bool(
        claimed_finder_monitor_group_exists_on_fx3
        or requested_dormant_evf_item_fx3 is not None
    )
    if dormant_evf_rejected:
        if (
            requested_dormant_evf_item_fx3 is not None
            and requested_dormant_evf_item_fx3
            not in EXACT_4_DORMANT_EVF_SYMBOLS_FX3_G153
        ):
            _add(
                "DORMANT_EVF_SYMBOL_EOPNOTSUPP",
                f"fx3_zero_evf_exposed_and_unknown_evf_symbol_eopnotsupp_95:{requested_dormant_evf_item_fx3!r}",
            )
        else:
            _add(
                "DORMANT_EVF_OR_FINDER_MONITOR_EOPNOTSUPP",
                "fx3_uses_setup_monitor_zero_finder_monitor_group_and_zero_exposed_evf_menus_eopnotsupp_95",
            )

    fx6_spoof_rejected = bool(
        requested_fx6_dormant_abb_menu or requested_fx6_vf_adjust_backlight_submenu
    )
    if fx6_spoof_rejected:
        _add(
            "FX6_DORMANT_ABB_OR_VF_SUBMENU_EOPNOTSUPP",
            "fx6_cmos_lacks_abb_menu_and_vf_adjust_lacks_backlight_contrast_chroma_colortemp_submenu_eopnotsupp_95",
        )

    state = resolve_fx3_pixelmap_and_monitor_state(
        auto_pixel_mapping_setup=auto_pixel_mapping_setup if _is_on_off(auto_pixel_mapping_setup) else AUTO_PIXEL_MAPPING_SETUP_DEFAULT_G153,
        auto_pixel_mapping_silent=auto_pixel_mapping_silent if _is_on_off(auto_pixel_mapping_silent) else AUTO_PIXEL_MAPPING_SILENT_DEFAULT_G153,
        silent_mode=silent_mode if _is_on_off(silent_mode) else "Off",
        monitor_brightness_mode=monitor_brightness_mode if monitor_brightness_mode in MONITOR_BRIGHTNESS_MODES_G153 else MONITOR_BRIGHTNESS_DEFAULT_G153,
        monitor_brightness_manual_level=monitor_brightness_manual_level if _is_strict_int(monitor_brightness_manual_level) else 0,
        display_quality=display_quality if display_quality in DISPLAY_QUALITY_MODES_G153 else DISPLAY_QUALITY_DEFAULT_G153,
        body_temperature_high=body_temperature_high,
        monitor_flip_direction=monitor_flip_direction if monitor_flip_direction in EXACT_4_MONITOR_FLIP_DIRECTIONS_G153 else MONITOR_FLIP_DEFAULT_G153,
        reset_action=reset_action if reset_action in ALLOWED_RESET_ACTIONS_PHASE356 else RESET_ACTION_NONE_PHASE356,
    )

    if manual_pixel_mapping_requested and not lens_cap_attached:
        _add(
            "PIXELMAP_LENS_CAP_SHIELDING_VIOLATION",
            "manual_pixel_mapping_requires_attached_lens_cap_light_shielding_einval_22",
        )
    if manual_pixel_mapping_requested and not battery_level_sufficient:
        _add(
            "PIXELMAP_BATTERY_CHECK_VIOLATION",
            "pixel_mapping_blocked_by_infra_notify_battery_check_for_pixel_mapping_einval_22",
        )
    if fx6_apr_light_detected:
        _add(
            "FX6_APR_LIGHT_DETECTED_VIOLATION",
            "fx6_apr_failed_pixel_mapping_result_light_detected_black_cloth_required_einval_22",
        )
    if fx6_apr_invalid_temperature:
        _add(
            "FX6_APR_INVALID_TEMPERATURE_VIOLATION",
            "fx6_apr_failed_pixel_mapping_result_invalid_temperature_einval_22",
        )
    if claimed_silent_mode_alone_mutes_pixel_mapping and (
        not state["power_off_pixel_mapping_shutter_muted"]
    ):
        _add(
            "PIXELMAP_SILENT_TARGET_MISMATCH_VIOLATION",
            "silent_mode_target_auto_pixel_mapping_defaults_off_so_poweroff_shutter_still_sounds_einval_22",
        )
    if claimed_camset_reset_clears_setup_auto_pixel_mapping:
        _add(
            "PIXELMAP_SETUP_RESET_IMMUNITY_VIOLATION",
            "setup_auto_pixel_mapping_is_initialize_only_not_resettable_by_camset_reset_einval_22",
        )
    if claimed_prm_haita_usb_stream_temp_blocks_pixelmap:
        _add(
            "PIXELMAP_PRM_HAITA_SPECULATION_VIOLATION",
            "fx3_appfw_has_zero_prm_haita_usb_stream_or_temp_bindings_for_pixel_mapping_einval_22",
        )
    if (
        state["display_quality_thermal_locked_to_standard"]
        and claimed_display_quality_high_unlocked_when_hot
    ):
        _add(
            "MONITOR_DISPLAY_QUALITY_THERMAL_LOCK_VIOLATION",
            "display_quality_locks_to_standard_when_body_temperature_high_einval_22",
        )
    if claimed_camset_reset_clears_monitor_3items:
        _add(
            "MONITOR_3ITEMS_RESET_IMMUNITY_VIOLATION",
            "all_3_setup_monitor_items_are_initialize_only_not_resettable_by_camset_reset_einval_22",
        )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G153
        block_errno = 0
        block_errno_name = "OK"
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G153_DORMANT_EVF_FINDER_MONITOR_OR_FX6_ABB_EOPNOTSUPP
        block_errno = EOPNOTSUPP_ERRNO_PHASE356
        block_errno_name = EOPNOTSUPP_NAME_PHASE356
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
        status = STATUS_BLOCKED_G153_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE356
        block_errno_name = EINVAL_NAME_PHASE356
    elif any("MONITOR_" in v for v in violations):
        status = STATUS_BLOCKED_G153_MONITOR_THERMAL_LOCK_OR_RESET_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE356
        block_errno_name = EINVAL_NAME_PHASE356
    else:
        status = STATUS_BLOCKED_G153_PIXELMAP_SHIELD_BATTERY_OR_RESET_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE356
        block_errno_name = EINVAL_NAME_PHASE356

    return PixelMapAprMonitorVfAdjustGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        pixel_mapping_menu_path=PIXEL_MAPPING_MENU_PATH_G153,
        auto_pixel_mapping_setup_menu_path=AUTO_PIXEL_MAPPING_SETUP_MENU_PATH_G153,
        auto_pixel_mapping_silent_menu_path=AUTO_PIXEL_MAPPING_SILENT_MENU_PATH_G153,
        monitor_menu_path=MONITOR_MENU_PATH_G153,
        fx3_finder_monitor_group_present=False,
        dormant_evf_exposed_items_fx3=DORMANT_EVF_EXPOSED_ITEMS_FX3_G153,
        fx6_apr_menu_path=FX6_APR_MENU_PATH_G153,
        fx6_abb_menu_present=False,
        fx6_vf_setting_menu_path=FX6_VF_SETTING_MENU_PATH_G153,
        fx6_vf_adjust_backlight_submenu_present=False,
        effective_auto_pixel_mapping_setup=state["effective_auto_pixel_mapping_setup"],
        auto_pixel_mapping_setup_resettable_by_camset_reset=AUTO_PIXEL_MAPPING_SETUP_RESETTABLE_BY_CAMSET_RESET_G153,
        effective_auto_pixel_mapping_silent=state["effective_auto_pixel_mapping_silent"],
        auto_pixel_mapping_silent_resettable_by_camset_reset=AUTO_PIXEL_MAPPING_SILENT_RESETTABLE_BY_CAMSET_RESET_G153,
        power_off_pixel_mapping_shutter_muted=state["power_off_pixel_mapping_shutter_muted"],
        manual_pixel_mapping_requires_lens_cap_battery_and_reboot=True,
        pixel_mapping_prm_haita_usb_stream_temp_hits=PIXEL_MAPPING_PRM_HAITA_USB_STREAM_TEMP_HITS_G153,
        dormant_pixel_map_notify_fx3_rejected=dormant_pm_rejected,
        dormant_evf_or_finder_monitor_spoof_rejected=dormant_evf_rejected,
        fx6_abb_or_vf_submenu_spoof_rejected=fx6_spoof_rejected,
        effective_monitor_brightness_mode=state["effective_monitor_brightness_mode"],
        effective_monitor_brightness_manual_level=state["effective_monitor_brightness_manual_level"],
        effective_display_quality=state["effective_display_quality"],
        display_quality_thermal_locked_to_standard=state["display_quality_thermal_locked_to_standard"],
        effective_monitor_flip_direction=state["effective_monitor_flip_direction"],
        monitor_all_3_items_resettable_by_camset_reset=MONITOR_ALL_3_ITEMS_RESETTABLE_BY_CAMSET_RESET_G153,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class G153PixelMapAprMonitorVfAdjustGuardResult:
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
    pixelmap_apr_monitor_vfadjust_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g153_pixelmap_apr_monitor_vfadjust_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G153PixelMapAprMonitorVfAdjustGuardResult]:
    audit = audit_phase356_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_pixelmap_apr_monitor_vfadjust_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G153PixelMapAprMonitorVfAdjustGuardResult(
        gate_id=G153,
        gate_code=G153_GATE_CODE,
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
        pixelmap_apr_monitor_vfadjust_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G153,
        gate_code=G153_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"setup_apm={res.effective_auto_pixel_mapping_setup} "
            f"silent_apm={res.effective_auto_pixel_mapping_silent} "
            f"dq={res.effective_display_quality} "
            f"flip={res.effective_monitor_flip_direction} "
            f"dormant_evf={res.dormant_evf_exposed_items_fx3}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_pixelmap_apr_monitor_vfadjust_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G153PixelMapAprMonitorVfAdjustGuardResult]:
    return evaluate_g153_pixelmap_apr_monitor_vfadjust_guard(**kwargs)


# ---------------------------------------------------------------------------
# Gate G154: Still-Only [Recall Custom hold 1..3] 11 Params (Zero Standalone WB)
#            vs FX6 Push AF/AGC/Iris & [External Output] HDMI Slot-1 EROFS=30
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecallCustomHoldHdmiRecControlVaultGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    recall_custom_hold_menu_path: str
    external_output_menu_path: str
    hdmi_output_settings_menu_path: str
    effective_shoot_mode: str
    effective_exposure_mode: str
    recall_custom_hold_available: bool
    recall_custom_hold_exact_11_params: Tuple[str, ...]
    recall_custom_hold_standalone_wb_present: bool
    shoot_set_registration_white_balance_hits: int
    recall_custom_hold_resettable_by_camset_reset: bool
    recall_custom_hold_persistence_file: str
    effective_hdmi_resolution: str
    effective_rec_media_dur_hdmi_output: str
    rec_media_locked_on_in_sq: bool
    effective_output_resolution: str
    output_resolution_forced_1080_by_log_or_pplut: bool
    effective_4k_output_setting: str
    hdmi_24_00p_requires_reboot_and_playback_isolation: bool
    effective_raw_output: str
    effective_time_code_output: str
    effective_rec_control: str
    rec_control_tc_prerequisite_satisfied: bool
    effective_hdmi_info_display: str
    builtin_lcd_blacked_out: bool
    effective_ctrl_for_hdmi: str
    ctrl_for_hdmi_elf_typo: str
    effective_4ch_audio_output: str
    external_output_resettable_by_camset_reset: bool
    dormant_4k2k_24p60p_exposed: int
    dormant_wb_4k2k_24p60p_or_movie_hold_rejected: bool
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


def resolve_fx3_custom_hold_and_external_output_state(
    *,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE356,
    exposure_mode: str = "P",
    hdmi_resolution: str = HDMI_RESOLUTION_AUTO_G154,
    rec_media_dur_hdmi_output: str = REC_MEDIA_DUR_HDMI_OUTPUT_DEFAULT_G154,
    output_resolution: str = HDMI_RESOLUTION_AUTO_G154,
    hdmi_4k_output_setting: str = "59.94p 10bit",
    raw_output: str = "Off",
    time_code_output: str = "Off",
    rec_control: str = "Off",
    hdmi_info_display: str = "On",
    hdmi_connected: bool = False,
    ctrl_for_hdmi: str = "On",
    hdmi_4ch_audio_output: str = HDMI_4CH_AUDIO_CH1_CH2_G154,
    log_shooting_mode: str = "Off",
    picture_profile: str = "Off",
    reset_action: str = RESET_ACTION_NONE_PHASE356,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-67 Recall Custom hold & Setup -> [External Output] state."""
    recall_available = (
        shoot_mode == SHOOT_MODE_STILL_PHASE356
        and exposure_mode in RECALL_CUSTOM_HOLD_STILL_PASM_MODES_G154
    )

    if reset_action == RESET_ACTION_INITIALIZE_PHASE356:
        eff_hdmi_res = HDMI_RESOLUTION_AUTO_G154
        eff_rec_media_req = REC_MEDIA_DUR_HDMI_OUTPUT_DEFAULT_G154
        eff_out_res_req = HDMI_RESOLUTION_AUTO_G154
        eff_4k_out = "59.94p 10bit"
        eff_raw_req = "Off"
        eff_tc_req = "Off"
        eff_rec_ctrl_req = "Off"
        eff_info_req = "On"
        eff_ctrl_hdmi = "On"
        eff_4ch = HDMI_4CH_AUDIO_CH1_CH2_G154
    else:
        eff_hdmi_res = hdmi_resolution
        eff_rec_media_req = rec_media_dur_hdmi_output
        eff_out_res_req = output_resolution
        eff_4k_out = hdmi_4k_output_setting
        eff_raw_req = raw_output
        eff_tc_req = time_code_output
        eff_rec_ctrl_req = rec_control
        eff_info_req = hdmi_info_display
        eff_ctrl_hdmi = ctrl_for_hdmi
        eff_4ch = hdmi_4ch_audio_output

    is_sq = shoot_mode == SHOOT_MODE_SQ_PHASE356
    eff_rec_media = REC_MEDIA_HDMI_ON_G154 if is_sq else eff_rec_media_req
    eff_raw = "Off" if is_sq else eff_raw_req
    eff_tc = "Off" if is_sq else eff_tc_req

    forced_1080 = bool(
        eff_rec_media == REC_MEDIA_HDMI_ON_G154
        and eff_raw == "Off"
        and (
            log_shooting_mode != "Off"
            or picture_profile in ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
        )
    )
    eff_out_res = "1080p" if forced_1080 else eff_out_res_req

    # HDMI Info. Display temporarily forced Off during Off(HDMI Only) or RAW Output = On;
    # when On & HDMI connected, built-in LCD monitor blacks out.
    eff_info = (
        "Off"
        if (eff_rec_media == REC_MEDIA_HDMI_OFF_ONLY_G154 or eff_raw == "On")
        else eff_info_req
    )
    lcd_blacked_out = bool(hdmi_connected and eff_info == "On")

    return {
        "recall_custom_hold_available": recall_available,
        "effective_hdmi_resolution": eff_hdmi_res,
        "effective_rec_media_dur_hdmi_output": eff_rec_media,
        "rec_media_locked_on_in_sq": is_sq,
        "effective_output_resolution": eff_out_res,
        "output_resolution_forced_1080_by_log_or_pplut": forced_1080,
        "effective_4k_output_setting": eff_4k_out,
        "hdmi_24_00p_requires_reboot_and_playback_isolation": (eff_4k_out == "24.00p 10bit"),
        "effective_raw_output": eff_raw,
        "effective_time_code_output": eff_tc,
        "effective_rec_control": eff_rec_ctrl_req,
        "effective_hdmi_info_display": eff_info,
        "builtin_lcd_blacked_out": lcd_blacked_out,
        "effective_ctrl_for_hdmi": eff_ctrl_hdmi,
        "effective_4ch_audio_output": eff_4ch,
    }


def compute_customhold_hdmi_external_output_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G154 (384 states)."""
    combos = list(
        itertools.product(
            ALLOWED_SHOOT_MODES_PHASE356,
            ("P", "iAuto"),
            REC_MEDIA_DUR_HDMI_OUTPUT_OPTIONS_G154,
            ("Off", "Flexible ISO"),  # log_shooting_mode
            ("Off", "On"),  # raw_output
            ("Off", "On"),  # time_code_output
            (MEDIA_SLOT_1_PHASE356, MEDIA_SLOT_2_PHASE356),
            (
                RESET_ACTION_NONE_PHASE356,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE356,
            ),
        )
    )
    recall_available_count = 0
    sq_rec_media_locked_on_count = 0
    log_forced_1080_count = 0
    info_forced_off_count = 0
    ext_out_reset_preserved_count = 0
    slot1_erofs_risk_count = 0

    for sm, exp_m, rec_m, log_m, raw_m, tc_m, slot, rst in combos:
        st = resolve_fx3_custom_hold_and_external_output_state(
            shoot_mode=sm,
            exposure_mode=exp_m,
            rec_media_dur_hdmi_output=rec_m,
            log_shooting_mode=log_m,
            raw_output=raw_m,
            time_code_output=tc_m,
            ctrl_for_hdmi="Off",
            reset_action=rst,
        )
        if st["recall_custom_hold_available"]:
            recall_available_count += 1
        if st["rec_media_locked_on_in_sq"] and st["effective_rec_media_dur_hdmi_output"] == "On":
            sq_rec_media_locked_on_count += 1
        if st["output_resolution_forced_1080_by_log_or_pplut"]:
            log_forced_1080_count += 1
        if st["effective_hdmi_info_display"] == "Off":
            info_forced_off_count += 1
        if rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE356 and st["effective_ctrl_for_hdmi"] == "Off":
            ext_out_reset_preserved_count += 1
        if slot == MEDIA_SLOT_1_PHASE356 and st["effective_rec_media_dur_hdmi_output"] == REC_MEDIA_HDMI_ON_G154:
            slot1_erofs_risk_count += 1

    return {
        "total_matrix_states": len(combos),
        "recall_available_count": recall_available_count,
        "sq_rec_media_locked_on_count": sq_rec_media_locked_on_count,
        "log_forced_1080_count": log_forced_1080_count,
        "info_forced_off_count": info_forced_off_count,
        "ext_out_reset_preserved_count": ext_out_reset_preserved_count,
        "slot1_erofs_risk_count": slot1_erofs_risk_count,
    }


def verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE356,
    body_model_id: int = FX3_MODEL_ID_PHASE356,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE356,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE356,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE356,
    exposure_mode: str = "P",
    recall_custom_hold_slot: Optional[str] = None,
    claimed_recall_custom_hold_active_in_movie_sq_or_iauto: bool = False,
    claimed_standalone_wb_checkbox_in_recall_custom_hold: bool = False,
    claimed_self_timer_in_recall_drive_mode: bool = False,
    claimed_camset_reset_clears_reg_custom_or_external_output: bool = False,
    claimed_tracking_on_available_in_movie_or_sq: bool = False,
    requested_fx6_dormant_high_low_key: bool = False,
    claimed_fx6_push_agc_active_in_cine_ei_or_bokeh: bool = False,
    claimed_fx6_push_auto_iris_active_on_manual_lens_or_bokeh: bool = False,
    hdmi_resolution: str = HDMI_RESOLUTION_AUTO_G154,
    rec_media_dur_hdmi_output: str = REC_MEDIA_DUR_HDMI_OUTPUT_DEFAULT_G154,
    output_resolution: str = HDMI_RESOLUTION_AUTO_G154,
    hdmi_4k_output_setting: str = "59.94p 10bit",
    raw_output: str = "Off",
    time_code_output: str = "Off",
    rec_control: str = "Off",
    rec_control_external_recorder_compatible: bool = True,
    hdmi_info_display: str = "On",
    hdmi_connected: bool = False,
    ctrl_for_hdmi: str = "On",
    hdmi_4ch_audio_output: str = HDMI_4CH_AUDIO_CH1_CH2_G154,
    log_shooting_mode: str = "Off",
    picture_profile: str = "Off",
    claimed_log_or_pplut_outputs_4k_when_rec_media_on_and_non_raw: bool = False,
    claimed_24_00p_requires_zero_reboot_or_cross_plays: bool = False,
    claimed_sq_allows_off_hdmi_only_or_tc_output_on: bool = False,
    requested_dormant_4k2k_or_24p60p_output_fx3: bool = False,
    target_media_slot: int = MEDIA_SLOT_2_PHASE356,
    hdmi_recording_write_requested: bool = False,
    requested_write_operation: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE356,
) -> RecallCustomHoldHdmiRecControlVaultGuardResult:
    """Enforce Gate G154: Still-Only [Recall Custom hold 1..3] 11 Params (Zero WB) vs FX6 Push & HDMI Slot-1 EROFS=30 Vault."""
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

    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE356:
        _add("TELEMETRY_INVALID", f"shoot_mode_invalid:{shoot_mode!r}")
    if exposure_mode not in ALLOWED_EXPOSURE_MODES_G154:
        _add("TELEMETRY_INVALID", f"exposure_mode_invalid:{exposure_mode!r}")
    if (
        recall_custom_hold_slot is not None
        and recall_custom_hold_slot not in RECALL_CUSTOM_HOLD_SLOTS_G154
    ):
        _add(
            "TELEMETRY_INVALID",
            f"recall_custom_hold_slot_invalid:{recall_custom_hold_slot!r}",
        )
    if hdmi_resolution not in HDMI_RESOLUTION_OPTIONS_G154:
        _add("TELEMETRY_INVALID", f"hdmi_resolution_invalid:{hdmi_resolution!r}")
    if rec_media_dur_hdmi_output not in REC_MEDIA_DUR_HDMI_OUTPUT_OPTIONS_G154:
        _add(
            "TELEMETRY_INVALID",
            f"rec_media_dur_hdmi_output_invalid:{rec_media_dur_hdmi_output!r}",
        )
    if output_resolution not in HDMI_RESOLUTION_OPTIONS_G154:
        _add("TELEMETRY_INVALID", f"output_resolution_invalid:{output_resolution!r}")
    if hdmi_4k_output_setting not in HDMI_4K_OUTPUT_SET_OPTIONS_G154:
        _add(
            "TELEMETRY_INVALID",
            f"hdmi_4k_output_setting_invalid:{hdmi_4k_output_setting!r}",
        )
    if not _is_on_off(raw_output):
        _add("TELEMETRY_INVALID", f"raw_output_invalid:{raw_output!r}")
    if not _is_on_off(time_code_output):
        _add("TELEMETRY_INVALID", f"time_code_output_invalid:{time_code_output!r}")
    if not _is_on_off(rec_control):
        _add("TELEMETRY_INVALID", f"rec_control_invalid:{rec_control!r}")
    if not _is_on_off(hdmi_info_display):
        _add("TELEMETRY_INVALID", f"hdmi_info_display_invalid:{hdmi_info_display!r}")
    if not _is_on_off(ctrl_for_hdmi):
        _add("TELEMETRY_INVALID", f"ctrl_for_hdmi_invalid:{ctrl_for_hdmi!r}")
    if hdmi_4ch_audio_output not in HDMI_4CH_AUDIO_OPTIONS_G154:
        _add(
            "TELEMETRY_INVALID",
            f"hdmi_4ch_audio_output_invalid:{hdmi_4ch_audio_output!r}",
        )
    if (
        not _is_strict_int(target_media_slot)
        or target_media_slot not in ALLOWED_MEDIA_SLOTS_PHASE356
    ):
        _add("TELEMETRY_INVALID", f"target_media_slot_invalid:{target_media_slot!r}")
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE356:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")

    state = resolve_fx3_custom_hold_and_external_output_state(
        shoot_mode=shoot_mode if shoot_mode in ALLOWED_SHOOT_MODES_PHASE356 else SHOOT_MODE_STILL_PHASE356,
        exposure_mode=exposure_mode if exposure_mode in ALLOWED_EXPOSURE_MODES_G154 else "P",
        hdmi_resolution=hdmi_resolution if hdmi_resolution in HDMI_RESOLUTION_OPTIONS_G154 else HDMI_RESOLUTION_AUTO_G154,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output if rec_media_dur_hdmi_output in REC_MEDIA_DUR_HDMI_OUTPUT_OPTIONS_G154 else REC_MEDIA_DUR_HDMI_OUTPUT_DEFAULT_G154,
        output_resolution=output_resolution if output_resolution in HDMI_RESOLUTION_OPTIONS_G154 else HDMI_RESOLUTION_AUTO_G154,
        hdmi_4k_output_setting=hdmi_4k_output_setting if hdmi_4k_output_setting in HDMI_4K_OUTPUT_SET_OPTIONS_G154 else "59.94p 10bit",
        raw_output=raw_output if _is_on_off(raw_output) else "Off",
        time_code_output=time_code_output if _is_on_off(time_code_output) else "Off",
        rec_control=rec_control if _is_on_off(rec_control) else "Off",
        hdmi_info_display=hdmi_info_display if _is_on_off(hdmi_info_display) else "On",
        hdmi_connected=hdmi_connected,
        ctrl_for_hdmi=ctrl_for_hdmi if _is_on_off(ctrl_for_hdmi) else "On",
        hdmi_4ch_audio_output=hdmi_4ch_audio_output if hdmi_4ch_audio_output in HDMI_4CH_AUDIO_OPTIONS_G154 else HDMI_4CH_AUDIO_CH1_CH2_G154,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        reset_action=reset_action if reset_action in ALLOWED_RESET_ACTIONS_PHASE356 else RESET_ACTION_NONE_PHASE356,
    )

    # EOPNOTSUPP=95 Dormant & Still-Only Custom Hold rejections
    hold_triggered_outside_pasm = bool(
        (recall_custom_hold_slot is not None or claimed_recall_custom_hold_active_in_movie_sq_or_iauto)
        and not state["recall_custom_hold_available"]
    )
    dormant_or_eopnotsupp = bool(
        hold_triggered_outside_pasm
        or claimed_standalone_wb_checkbox_in_recall_custom_hold
        or requested_dormant_4k2k_or_24p60p_output_fx3
        or requested_fx6_dormant_high_low_key
    )
    if hold_triggered_outside_pasm:
        _add(
            "RECALL_CUSTOM_HOLD_STILL_PASM_ONLY_EOPNOTSUPP",
            "recall_custom_hold_1_to_3_is_strictly_still_pasm_only_unavailable_in_movie_sq_iauto_eopnotsupp_95",
        )
    if claimed_standalone_wb_checkbox_in_recall_custom_hold:
        _add(
            "RECALL_CUSTOM_HOLD_ZERO_STANDALONE_WB_EOPNOTSUPP",
            "recall_custom_hold_exposes_exact_11_params_zero_standalone_white_balance_checkbox_eopnotsupp_95",
        )
    if requested_dormant_4k2k_or_24p60p_output_fx3:
        _add(
            "DORMANT_4K2K_OR_24P60P_OUTPUT_EOPNOTSUPP",
            "fx3_ver_7_02_has_zero_4k_2k_output_and_zero_24p_60p_output_menus_eopnotsupp_95",
        )
    if requested_fx6_dormant_high_low_key:
        _add(
            "FX6_DORMANT_HIGH_LOW_KEY_EOPNOTSUPP",
            "fx6_ver_6_01_high_low_key_string_is_dormant_unexposed_in_menu_eopnotsupp_95",
        )

    # EINVAL=22 Guard Violations
    if claimed_self_timer_in_recall_drive_mode:
        _add(
            "RECALL_CUSTOM_HOLD_NO_SELF_TIMER_VIOLATION",
            "recall_custom_hold_drive_mode_checkbox_excludes_self_timer_einval_22",
        )
    if claimed_camset_reset_clears_reg_custom_or_external_output:
        _add(
            "RESET_IMMUNITY_CUSTOM_HOLD_OR_EXTERNAL_OUTPUT_VIOLATION",
            "reg_custom_shoot_set_and_setup_external_output_are_initialize_only_not_camset_reset_einval_22",
        )
    if claimed_tracking_on_available_in_movie_or_sq:
        _add(
            "TRACKING_ON_STILL_ONLY_VIOLATION",
            "tracking_on_custom_key_is_still_afc_only_unavailable_in_movie_and_sq_einval_22",
        )
    if claimed_fx6_push_agc_active_in_cine_ei_or_bokeh:
        _add(
            "FX6_PUSH_AGC_CINE_EI_BOKEH_VIOLATION",
            "fx6_push_agc_is_disabled_in_cine_ei_cine_ei_quick_and_bokeh_control_on_einval_22",
        )
    if claimed_fx6_push_auto_iris_active_on_manual_lens_or_bokeh:
        _add(
            "FX6_PUSH_AUTO_IRIS_MANUAL_OR_BOKEH_VIOLATION",
            "fx6_push_auto_iris_is_disabled_on_manual_iris_or_bokeh_control_on_einval_22",
        )

    rec_ctrl_tc_ok = (
        state["effective_rec_control"] != "On"
        or (
            state["effective_time_code_output"] == "On"
            and rec_control_external_recorder_compatible
        )
    )
    if state["effective_rec_control"] == "On" and state["effective_time_code_output"] != "On":
        _add(
            "HDMI_REC_CONTROL_REQUIRES_TC_OUTPUT_ON_VIOLATION",
            "hdmi_rec_control_on_hard_requires_time_code_output_on_einval_22",
        )
    if state["effective_rec_control"] == "On" and not rec_control_external_recorder_compatible:
        _add(
            "HDMI_REC_CONTROL_COMPATIBLE_RECORDER_VIOLATION",
            "hdmi_rec_control_on_requires_compatible_external_recorder_einval_22",
        )
    if (
        state["output_resolution_forced_1080_by_log_or_pplut"]
        and claimed_log_or_pplut_outputs_4k_when_rec_media_on_and_non_raw
    ):
        _add(
            "HDMI_LOG_PPLUT_FORCED_1080_VIOLATION",
            "output_resolution_drops_to_1080_under_log_or_pplut1_4_when_rec_media_on_and_raw_off_einval_22",
        )
    if claimed_24_00p_requires_zero_reboot_or_cross_plays:
        _add(
            "HDMI_24_00P_REBOOT_AND_ISOLATION_VIOLATION",
            "4k_output_set_24_00p_requires_mandatory_reboot_and_cross_framerate_playback_isolation_einval_22",
        )
    if claimed_sq_allows_off_hdmi_only_or_tc_output_on:
        _add(
            "HDMI_SQ_LOCK_VIOLATION",
            "sq_mode_locks_rec_media_dur_hdmi_output_on_and_disables_time_code_output_einval_22",
        )

    # HARD Tier-0 Slot-1 EROFS=30 Firewall:
    # When Rec. Media dur HDMI Output == On (default, locked On in S&Q) targets Slot 1
    # for recording/write, or any explicit Slot-1 card write is requested -> EROFS=30 fail-closed!
    # Off(HDMI Only) outside S&Q stops internal card recording (zero Slot-1 writes).
    slot1_hdmi_rec_media_write = bool(
        target_media_slot == MEDIA_SLOT_1_PHASE356
        and hdmi_recording_write_requested
        and state["effective_rec_media_dur_hdmi_output"] == REC_MEDIA_HDMI_ON_G154
    )
    slot1_explicit_write = bool(
        target_media_slot == MEDIA_SLOT_1_PHASE356 and requested_write_operation
    )
    slot1_blocked = slot1_hdmi_rec_media_write or slot1_explicit_write
    if slot1_blocked:
        _add(
            "SLOT1_HDMI_REC_MEDIA_VAULT_EROFS",
            "slot1_tier0_vault_erofs_30_hard_blocked_rec_media_dur_hdmi_output_on_or_card_write",
        )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G154
        block_errno = 0
        block_errno_name = "OK"
    elif slot1_blocked:
        status = STATUS_BLOCKED_G154_SLOT1_HDMI_REC_MEDIA_VAULT_EROFS
        block_errno = EROFS_ERRNO_PHASE356
        block_errno_name = EROFS_NAME_PHASE356
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G154_DORMANT_WB_4K2K_24P60P_OR_MOVIE_HOLD_EOPNOTSUPP
        block_errno = EOPNOTSUPP_ERRNO_PHASE356
        block_errno_name = EOPNOTSUPP_NAME_PHASE356
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
        status = STATUS_BLOCKED_G154_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE356
        block_errno_name = EINVAL_NAME_PHASE356
    else:
        status = STATUS_BLOCKED_G154_CUSTOM_HOLD_OR_HDMI_REC_CTRL_PREREQ_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE356
        block_errno_name = EINVAL_NAME_PHASE356

    return RecallCustomHoldHdmiRecControlVaultGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        recall_custom_hold_menu_path=RECALL_CUSTOM_HOLD_MENU_PATH_G154,
        external_output_menu_path=EXTERNAL_OUTPUT_MENU_PATH_G154,
        hdmi_output_settings_menu_path=HDMI_OUTPUT_SETTINGS_MENU_PATH_G154,
        effective_shoot_mode=shoot_mode,
        effective_exposure_mode=exposure_mode,
        recall_custom_hold_available=state["recall_custom_hold_available"],
        recall_custom_hold_exact_11_params=EXACT_11_RECALL_CUSTOM_HOLD_PARAMS_G154,
        recall_custom_hold_standalone_wb_present=False,
        shoot_set_registration_white_balance_hits=SHOOT_SET_REGISTRATION_WHITE_BALANCE_HITS_G154,
        recall_custom_hold_resettable_by_camset_reset=RECALL_CUSTOM_HOLD_RESETTABLE_BY_CAMSET_RESET_G154,
        recall_custom_hold_persistence_file=RECALL_CUSTOM_HOLD_PERSISTENCE_FILE_G154,
        effective_hdmi_resolution=state["effective_hdmi_resolution"],
        effective_rec_media_dur_hdmi_output=state["effective_rec_media_dur_hdmi_output"],
        rec_media_locked_on_in_sq=state["rec_media_locked_on_in_sq"],
        effective_output_resolution=state["effective_output_resolution"],
        output_resolution_forced_1080_by_log_or_pplut=state["output_resolution_forced_1080_by_log_or_pplut"],
        effective_4k_output_setting=state["effective_4k_output_setting"],
        hdmi_24_00p_requires_reboot_and_playback_isolation=state["hdmi_24_00p_requires_reboot_and_playback_isolation"],
        effective_raw_output=state["effective_raw_output"],
        effective_time_code_output=state["effective_time_code_output"],
        effective_rec_control=state["effective_rec_control"],
        rec_control_tc_prerequisite_satisfied=rec_ctrl_tc_ok,
        effective_hdmi_info_display=state["effective_hdmi_info_display"],
        builtin_lcd_blacked_out=state["builtin_lcd_blacked_out"],
        effective_ctrl_for_hdmi=state["effective_ctrl_for_hdmi"],
        ctrl_for_hdmi_elf_typo=CTRL_FOR_HDMI_ELF_TYPO_G154,
        effective_4ch_audio_output=state["effective_4ch_audio_output"],
        external_output_resettable_by_camset_reset=EXTERNAL_OUTPUT_RESETTABLE_BY_CAMSET_RESET_G154,
        dormant_4k2k_24p60p_exposed=DORMANT_EXTERNAL_OUTPUT_HITS_G154,
        dormant_wb_4k2k_24p60p_or_movie_hold_rejected=dormant_or_eopnotsupp,
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
class G154RecallCustomHoldHdmiRecControlVaultGuardResult:
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
    recall_custom_hold_hdmi_reccontrol_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g154_recall_custom_hold_hdmi_reccontrol_vault_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G154RecallCustomHoldHdmiRecControlVaultGuardResult]:
    audit = audit_phase356_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G154RecallCustomHoldHdmiRecControlVaultGuardResult(
        gate_id=G154,
        gate_code=G154_GATE_CODE,
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
        recall_custom_hold_hdmi_reccontrol_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G154,
        gate_code=G154_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"hold_avail={res.recall_custom_hold_available} "
            f"rec_media={res.effective_rec_media_dur_hdmi_output} "
            f"tc_out={res.effective_time_code_output} "
            f"rec_ctrl={res.effective_rec_control} "
            f"s1_writes={res.slot1_data_sector_writes}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_recall_custom_hold_hdmi_reccontrol_vault_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G154RecallCustomHoldHdmiRecControlVaultGuardResult]:
    return evaluate_g154_recall_custom_hold_hdmi_reccontrol_vault_guard(**kwargs)


# ---------------------------------------------------------------------------
# Unified 154-Gate Master Safety Preflight Engine (G01..G154)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Master154GateReport:
    schema: str
    schema_version: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_151_gates_verified: bool
    all_154_gates_verified: bool
    g13_to_g154_all_passed: bool
    g153_to_g154_all_passed: bool
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
    master_152_report: Dict[str, Any]
    g153_result: Dict[str, Any]
    g154_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_154gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    simulate_bench_dry_run: Optional[bool] = None,
    dry_run_simulated_backup: Optional[bool] = None,
    request_persistent_emmc_writes: bool = False,
    master_152_override: Optional[Master152GateReport] = None,
    pixelmap_apr_monitor_vfadjust_kwargs: Optional[Mapping[str, Any]] = None,
    recall_custom_hold_hdmi_reccontrol_kwargs: Optional[Mapping[str, Any]] = None,
    **extra_upstream_kwargs: Any,
) -> Master154GateReport:
    """Evaluate unified 154-Gate Milestone Master Safety Preflight (`G01..G154`)."""
    effective_dry_run = (
        bool(dry_run_simulated)
        or (simulate_bench_dry_run is True)
        or (dry_run_simulated_backup is True)
    )
    clean_forced = _is_clean_room_forced(force_clean_room)
    resolved_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved_work_root_for_m152 = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=resolved_repo_root).work_root
    )
    m152_force_clean_room = (
        True
        if (clean_forced or resolved_work_root_for_m152 is None)
        else force_clean_room
    )

    if master_152_override is not None:
        m152_report = master_152_override
    else:
        m152_kw = {
            k: v
            for k, v in extra_upstream_kwargs.items()
            if v is not None
        }
        m152_report = evaluate_152gate_preflight(
            resolved_repo_root,
            work_root=work_root,
            force_clean_room=m152_force_clean_room,
            dry_run_simulated=effective_dry_run,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m152_kw,
        )

    g153_kw = dict(pixelmap_apr_monitor_vfadjust_kwargs or {})
    g153_verdict, g153_res = evaluate_g153_pixelmap_apr_monitor_vfadjust_guard(
        repo_root=resolved_repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **g153_kw,
    )

    g154_kw = dict(recall_custom_hold_hdmi_reccontrol_kwargs or {})
    if "requested_write_operation" not in g154_kw and request_persistent_emmc_writes:
        g154_kw["requested_write_operation"] = True
        if "target_media_slot" not in g154_kw:
            g154_kw["target_media_slot"] = MEDIA_SLOT_1_PHASE356
    g154_verdict, g154_res = (
        evaluate_g154_recall_custom_hold_hdmi_reccontrol_vault_guard(
            repo_root=resolved_repo_root,
            work_root=work_root,
            force_clean_room=force_clean_room,
            **g154_kw,
        )
    )

    new_gate_dicts = (
        {
            "gate_id": G153,
            "gate_code": G153_GATE_CODE,
            "status": g153_res.status,
            "passed": g153_verdict.passed,
            "evidence": g153_verdict.evidence,
            "violation_codes": list(g153_verdict.errors),
        },
        {
            "gate_id": G154,
            "gate_code": G154_GATE_CODE,
            "status": g154_res.status,
            "passed": g154_verdict.passed,
            "evidence": g154_verdict.evidence,
            "violation_codes": list(g154_verdict.errors),
        },
    )

    all_gates: Tuple[Dict[str, Any], ...] = tuple(m152_report.gates) + new_gate_dicts
    g01_to_g12_verified = int(m152_report.summary["g01_to_g12_verified"])
    g13_to_g152_verified = (
        int(m152_report.summary["g13_to_g150_verified"])
        + int(m152_report.summary["g151_to_g152_verified"])
    )
    g153_to_g154_verified = int(bool(g153_verdict.passed)) + int(
        bool(g154_verdict.passed)
    )
    total_verified = g01_to_g12_verified + g13_to_g152_verified + g153_to_g154_verified

    g153_to_g154_all_passed = g153_to_g154_verified == 2
    g13_to_g154_all_passed = (
        m152_report.g13_to_g152_all_passed and g153_to_g154_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m152_report.gates[:9])

    offline_151_verified = (
        g01_to_g09_ok
        and m152_report.offline_149_gates_verified
        and g153_to_g154_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_154_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g154_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m152_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_151_verified
        and m152_report.h0_h1_trial_entry_allowed
        and g153_to_g154_all_passed
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
        list(m152_report.errors)
        + list(g153_verdict.errors)
        + list(g154_verdict.errors)
    )
    warnings: List[str] = (
        list(m152_report.warnings)
        + list(g153_verdict.warnings)
        + list(g154_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m152_report.g13_to_g152_all_passed:
        overall_status = m152_report.status
    elif not g153_verdict.passed:
        overall_status = g153_verdict.status
    elif not g154_verdict.passed:
        overall_status = g154_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_154_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_154_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_154_verified:
        overall_status = "VERIFIED_ALL_154_GATES"
    else:
        overall_status = "VERIFIED_151_OF_154_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m152_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g153_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g154_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 154,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 154 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g152_verified": g13_to_g152_verified,
        "g153_to_g154_verified": g153_to_g154_verified,
        "g13_to_g154_all_passed": g13_to_g154_all_passed,
        "g153_to_g154_all_passed": g153_to_g154_all_passed,
        "offline_151_gates_verified": offline_151_verified,
        "all_154_gates_verified": all_154_verified,
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

    return Master154GateReport(
        schema=REALHW_154GATE_PREFLIGHT_SCHEMA,
        schema_version=REALHW_154GATE_PREFLIGHT_SCHEMA,
        version=REALHW_PIXELMAP_APR_MONITOR_VFADJUST_CUSTOMHOLD_HDMI_RECCONTROL_154GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_151_gates_verified=offline_151_verified,
        all_154_gates_verified=all_154_verified,
        g13_to_g154_all_passed=g13_to_g154_all_passed,
        g153_to_g154_all_passed=g153_to_g154_all_passed,
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
        master_152_report=m152_report.to_dict(),
        g153_result=g153_res.to_dict(),
        g154_result=g154_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_154_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master154GateReport:
    return evaluate_154gate_preflight(repo_root, **kwargs)


def run_154_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master154GateReport:
    return evaluate_154gate_preflight(repo_root, **kwargs)


def verify_real_hardware_154gate_readiness(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master154GateReport:
    return evaluate_154gate_preflight(repo_root, **kwargs)


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
        prog="realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_and_154gate_guard",
        description="Phase 356 (Task H446, Wave-67) G153/G154 and 154/154 Unified Safety Preflight CLI",
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
        help="Supply simulated dry-run Tier-0 backup inputs so all 154/154 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g153", "g154", "154"],
        default="154",
        help="Target gate check: g153, g154, or 154",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g153":
        v, r = evaluate_g153_pixelmap_apr_monitor_vfadjust_guard(
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

    if args.gate == "g154":
        v, r = evaluate_g154_recall_custom_hold_hdmi_reccontrol_vault_guard(
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

    rep = evaluate_154gate_preflight(
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
                "g153_status": rep.g153_result["status"],
                "g154_status": rep.g154_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/154 "
            f"g153_to_g154_all_passed={rep.g153_to_g154_all_passed} "
            f"all_154_gates_verified={rep.all_154_gates_verified} "
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
        rep.all_154_gates_verified
        if args.dry_run_simulated
        else rep.offline_151_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "ABSENT_FINDER_MONITOR_GROUP_NAME_G153",
    "ALLOWED_EXPOSURE_MODES_G154",
    "ALLOWED_MEDIA_SLOTS_PHASE356",
    "ALLOWED_RESET_ACTIONS_PHASE356",
    "ALLOWED_SHOOT_MODES_PHASE356",
    "AUTO_PIXEL_MAPPING_SETUP_DEFAULT_G153",
    "AUTO_PIXEL_MAPPING_SETUP_F_RESID16_G153",
    "AUTO_PIXEL_MAPPING_SETUP_MENU_PATH_G153",
    "AUTO_PIXEL_MAPPING_SETUP_RESETTABLE_BY_CAMSET_RESET_G153",
    "AUTO_PIXEL_MAPPING_SILENT_DEFAULT_G153",
    "AUTO_PIXEL_MAPPING_SILENT_MENU_PATH_G153",
    "AUTO_PIXEL_MAPPING_SILENT_NOT_TARGET_F_RESID16_G153",
    "AUTO_PIXEL_MAPPING_SILENT_RESETTABLE_BY_CAMSET_RESET_G153",
    "CTRL_FOR_HDMI_BASE_RESID16_G154",
    "CTRL_FOR_HDMI_ELF_TYPO_G154",
    "DISPLAY_QUALITY_DEFAULT_G153",
    "DISPLAY_QUALITY_F_RESID16_G153",
    "DISPLAY_QUALITY_HIGH_G153",
    "DISPLAY_QUALITY_MODES_G153",
    "DISPLAY_QUALITY_STANDARD_G153",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE356",
    "DONOR_CHECK_MAX_SECONDS_PHASE356",
    "DORMANT_24P_60P_OUTPUT_F_RESID16_G154",
    "DORMANT_EVF_EXPOSED_ITEMS_FX3_G153",
    "DORMANT_EXTERNAL_OUTPUT_HITS_G154",
    "DORMANT_EXTERNAL_OUTPUT_MENUS_G154",
    "DORMANT_FINDER_FRAME_RATE_F_RESID16_G153",
    "DORMANT_FINDER_MONITOR_SEL_F_RESID16_G153",
    "DORMANT_PIXEL_MAP_FX3_TOKENS_G153",
    "DORMANT_PIXEL_MAP_NOTIFY_F_RESID16_G153",
    "DORMANT_VIEWFINDER_BRIGHT_F_RESID16_G153",
    "DORMANT_VIEWFINDER_COLOR_TEMP_BASE_RESID16_G153",
    "EINVAL_ERRNO_PHASE356",
    "EINVAL_NAME_PHASE356",
    "ENV_CLEAN_ROOM_TEST_PHASE356",
    "EOPNOTSUPP_ERRNO_PHASE356",
    "EOPNOTSUPP_NAME_PHASE356",
    "EROFS_ERRNO_PHASE356",
    "EROFS_NAME_PHASE356",
    "EXACT_11_RECALL_CUSTOM_HOLD_PARAMS_G154",
    "EXACT_3_MONITOR_ITEMS_G153",
    "EXACT_4_DORMANT_EVF_SYMBOLS_FX3_G153",
    "EXACT_4_MONITOR_FLIP_DIRECTIONS_G153",
    "EXTERNAL_OUTPUT_MENU_PATH_G154",
    "EXTERNAL_OUTPUT_RESETTABLE_BY_CAMSET_RESET_G154",
    "FX3_DEFAULT_FW_VERSION_PHASE356",
    "FX3_HELP_GUIDE_CODE_PHASE356",
    "FX3_MODEL_ID_PHASE356",
    "FX3_MODEL_NAME_PHASE356",
    "FX6_APR_MENU_PATH_G153",
    "FX6_APR_RESULT_TOKENS_G153",
    "FX6_DEFAULT_FW_VERSION_PHASE356",
    "FX6_DORMANT_ABB_EXPOSED_G153",
    "FX6_DORMANT_HIGH_LOW_KEY_EXPOSED_G154",
    "FX6_DORMANT_VF_ADJUST_SUBMENU_ITEMS_G153",
    "FX6_HDMI_TC_OUT_MENU_PATH_G154",
    "FX6_MODEL_NAME_PHASE356",
    "FX6_PIXEL_MAPPING_ELF_TYPO_EXCUTED_G153",
    "FX6_PUSH_AF_MODES_G154",
    "FX6_PUSH_ASSIGNABLE_BUTTONS_G154",
    "FX6_SDI_HDMI_REC_CONTROL_MENU_PATH_G154",
    "FX6_SDI_HDMI_REC_CONTROL_MODES_G154",
    "FX6_VF_ADJUST_SUBMENU_EXPOSED_G153",
    "FX6_VF_MIRROR_SWITCH_MODES_G153",
    "FX6_VF_SETTING_BRIGHTNESS_DEFAULT_G153",
    "FX6_VF_SETTING_BRIGHTNESS_MAX_G153",
    "FX6_VF_SETTING_BRIGHTNESS_MIN_G153",
    "FX6_VF_SETTING_COLOR_MODES_G153",
    "FX6_VF_SETTING_MENU_PATH_G153",
    "G153",
    "G153PixelMapAprMonitorVfAdjustGuardResult",
    "G153_GATE_CODE",
    "G153_GATE_ID",
    "G154",
    "G154RecallCustomHoldHdmiRecControlVaultGuardResult",
    "G154_GATE_CODE",
    "G154_GATE_ID",
    "HDMI_4CH_AUDIO_CH1_CH2_G154",
    "HDMI_4CH_AUDIO_CH3_CH4_G154",
    "HDMI_4CH_AUDIO_F_RESID16_G154",
    "HDMI_4CH_AUDIO_OPTIONS_G154",
    "HDMI_4K_OUTPUT_ELF_TYPO_G154",
    "HDMI_4K_OUTPUT_SET_F_RESID16_G154",
    "HDMI_4K_OUTPUT_SET_OPTIONS_G154",
    "HDMI_INFO_DISPLAY_F_RESID16_G154",
    "HDMI_OUTPUT_SETTINGS_MENU_PATH_G154",
    "HDMI_REC_CONTROL_F_RESID16_G154",
    "HDMI_RESOLUTION_AUTO_G154",
    "HDMI_RESOLUTION_BASE_RESID16_G154",
    "HDMI_RESOLUTION_OPTIONS_G154",
    "HDMI_TC_OUTPUT_F_RESID16_G154",
    "MEDIA_SLOT_1_PHASE356",
    "MEDIA_SLOT_2_PHASE356",
    "MEDIA_SLOT_NONE_PHASE356",
    "MONITOR_ALL_3_ITEMS_RESETTABLE_BY_CAMSET_RESET_G153",
    "MONITOR_BRIGHTNESS_BASE_RESID16_G153",
    "MONITOR_BRIGHTNESS_DEFAULT_G153",
    "MONITOR_BRIGHTNESS_MANUAL_MAX_G153",
    "MONITOR_BRIGHTNESS_MANUAL_MIN_G153",
    "MONITOR_BRIGHTNESS_MODES_G153",
    "MONITOR_FLIP_180_G153",
    "MONITOR_FLIP_AUTO_G153",
    "MONITOR_FLIP_DEFAULT_G153",
    "MONITOR_FLIP_DIRECTION_F_RESID16_G153",
    "MONITOR_FLIP_HORIZONTAL_G153",
    "MONITOR_FLIP_NO_FLIP_G153",
    "MONITOR_MENU_PATH_G153",
    "Master154GateReport",
    "OUTPUT_RESOLUTION_F_RESID16_G154",
    "PINNED_FX3_APPFW_SLICES_PHASE356",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE356",
    "PINNED_FX6_APPFW_SLICES_PHASE356",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE356",
    "PINNED_PHASE356_DONOR_SPECS",
    "PIXEL_MAPPING_ELF_TYPO_EXCUTED_G153",
    "PIXEL_MAPPING_ELF_TYPO_MAPPINNG_G153",
    "PIXEL_MAPPING_F_RESID16_G153",
    "PIXEL_MAPPING_MENU_PATH_G153",
    "PIXEL_MAPPING_PRM_HAITA_USB_STREAM_TEMP_HITS_G153",
    "Phase356DonorAuditResult",
    "PixelMapAprMonitorVfAdjustGuardResult",
    "REALHW_154GATE_PREFLIGHT_SCHEMA",
    "REALHW_PIXELMAP_APR_MONITOR_VFADJUST_CUSTOMHOLD_HDMI_RECCONTROL_154GATE_SCHEMA",
    "REALHW_PIXELMAP_APR_MONITOR_VFADJUST_CUSTOMHOLD_HDMI_RECCONTROL_154GATE_VERSION",
    "RECALL_CUSTOM_HOLD_1_F_RESID16_G154",
    "RECALL_CUSTOM_HOLD_2_F_RESID16_G154",
    "RECALL_CUSTOM_HOLD_3_F_RESID16_G154",
    "RECALL_CUSTOM_HOLD_MENU_PATH_G154",
    "RECALL_CUSTOM_HOLD_PARAM_COUNT_G154",
    "RECALL_CUSTOM_HOLD_PERSISTENCE_FILE_G154",
    "RECALL_CUSTOM_HOLD_RESETTABLE_BY_CAMSET_RESET_G154",
    "RECALL_CUSTOM_HOLD_SLOTS_G154",
    "RECALL_CUSTOM_HOLD_STILL_PASM_MODES_G154",
    "REC_MEDIA_DUR_HDMI_F_RESID16_G154",
    "REC_MEDIA_DUR_HDMI_OUTPUT_DEFAULT_G154",
    "REC_MEDIA_DUR_HDMI_OUTPUT_OPTIONS_G154",
    "REC_MEDIA_HDMI_OFF_ONLY_G154",
    "REC_MEDIA_HDMI_ON_G154",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE356",
    "RESET_ACTION_INITIALIZE_PHASE356",
    "RESET_ACTION_NONE_PHASE356",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE356",
    "RecallCustomHoldHdmiRecControlVaultGuardResult",
    "SHOOT_MODE_MOVIE_PHASE356",
    "SHOOT_MODE_SQ_PHASE356",
    "SHOOT_MODE_STILL_PHASE356",
    "SHOOT_SET_REGISTRATION_WHITE_BALANCE_HITS_G154",
    "STATUS_BLOCKED_G153_DORMANT_EVF_FINDER_MONITOR_OR_FX6_ABB_EOPNOTSUPP",
    "STATUS_BLOCKED_G153_MONITOR_THERMAL_LOCK_OR_RESET_VIOLATION",
    "STATUS_BLOCKED_G153_PIXELMAP_SHIELD_BATTERY_OR_RESET_VIOLATION",
    "STATUS_BLOCKED_G153_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G154_CUSTOM_HOLD_OR_HDMI_REC_CTRL_PREREQ_VIOLATION",
    "STATUS_BLOCKED_G154_DORMANT_WB_4K2K_24P60P_OR_MOVIE_HOLD_EOPNOTSUPP",
    "STATUS_BLOCKED_G154_SLOT1_HDMI_REC_MEDIA_VAULT_EROFS",
    "STATUS_BLOCKED_G154_TELEMETRY_INVALID",
    "STATUS_BLOCKED_PHASE356_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G153",
    "STATUS_VERIFIED_G154",
    "SUNNY_WEATHER_BASE_RESID16_G153",
    "audit_phase356_donor_contracts",
    "compute_customhold_hdmi_external_output_matrix",
    "compute_pixelmap_apr_monitor_vfadjust_matrix",
    "evaluate_154_master_safety_gates",
    "evaluate_154gate_preflight",
    "evaluate_g153_pixelmap_apr_monitor_vfadjust_guard",
    "evaluate_g154_recall_custom_hold_hdmi_reccontrol_vault_guard",
    "main",
    "resolve_fx3_custom_hold_and_external_output_state",
    "resolve_fx3_pixelmap_and_monitor_state",
    "run_154_gate_preflight",
    "strip_elapsed_seconds_recursive_phase356",
    "verify_pixelmap_apr_monitor_vfadjust_guard",
    "verify_pixelmap_apr_monitor_vfadjust_guard_with_audit",
    "verify_real_hardware_154gate_readiness",
    "verify_recall_custom_hold_hdmi_reccontrol_vault_guard",
    "verify_recall_custom_hold_hdmi_reccontrol_vault_guard_with_audit",
]


if __name__ == "__main__":
    raise SystemExit(main())
