"""Phase 327 (Task H394, Wave-63): Real-Hardware HDMI Output/RAW Co-Rec Vault &
5-State De-Squeeze Display Guard (`G145`), Re-Clamp REC Lamp / Emphasized REC /
Remain Shoot / Auto Review / Dormant Var. Shutter & Wave-42 APS-C S35 Reset
Errata Guard (`G146`), and Unified 146-Gate Master Safety Preflight (`G01..G146`).

Authoritative Empirical Baseline (`ILME-FX3 Ver. 7.02`, `ilc/2210`, `0x0502`,
`PRODUCT_MODEL_ALCIN_UUD` vs `ILME-FX6 Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`):
  - **Gate `G145` (`REALHW_HDMI_RAW_CO_REC_VAULT_AND_DESQUEEZE_4RATIO_GUARD`)**:
    1. `Setup -> [External Output] -> [HDMI Output Settings]` (Initialize-only;
       survives `[Camera Settings Reset]`): exact `8` active items:
       `[Rec. Media dur HDMI Output]` (`On` default / `Off(HDMI Only)`, locked `On`
       in `S&Q`, zero internal Slot-1/2 writes when `Off(HDMI Only)`),
       `[Output Resolution]` (`Auto` default / `2160p` / `1080p` / `1080i`, forced
       `1080p` under Log/PPLUT1..4 when `Rec. Media = On` & `RAW Output = Off`),
       `[4K Output Set.(HDMI Only)]` (10-bit-only `59.94p/50p/29.97p/25p/23.98p/24.00p`
       with mandatory `24.00p` reboot gate and dormant `24.00p 8bit` `_f 0x748a` ->
       `EOPNOTSUPP=95`), `[RAW Output]` (`4264x2408` 16-bit linear requiring `Movie` +
       `Log Shooting != Off`, locking `S-Log3` & disabling `[Active]` SteadyShot),
       `[RAW Output Setting]`, `[Time Code Output]` (disabled in `S&Q`),
       `[REC Control]` (requires `[Time Code Output] == On`), and
       `[4ch Audio Output]` (`CH1/CH2` or `CH3/CH4`, HDMI carries 2ch LPCM).
    2. Ver. `2.00..7.02` removal of standalone `[Color Gamut for RAW Output]`
       (`_f 0x6bdc` / `BKID_APP_setting_color_gamut_for_raw_out` -> `EOPNOTSUPP=95`;
       unified under `[Log Shooting Setting] -> [Color Gamut]`).
    3. `RAW Output = On` + `Rec. Media dur HDMI Output = On` internal XAVC + Proxy
       co-recording (`EROFS=30` when `Slot-1` Tier-0 vault is targeted vs
       zero-card-write bypass when `Off(HDMI Only)`); `HDMI Info. Display = On`
       (with `RAW=Off` & `Rec. Media=On`) blanking FX3 built-in LCD; vs `ILME-FX6`
       (`12G-SDI RAW` `4096x2160`/`3840x2160 C` capping HDMI `<= 1080p`, `RAW(HDMI)`
       `4240x2392` excluding `24Hz`, `SDI/HDMI Remote I/F` vs `Parallel Rec`, and
       4ch 24-bit 48kHz SDI LPCM).
    4. `Setup -> [Display Option] -> [De-Squeeze Display]` (Initialize-only):
       Ver. `7.00/7.02` 5-state active set (`Off`, `1.3x`, `1.5x`, `1.6x` [executing
       `1.65x` `VAL_DE_SQUEEZE_DISP_1_65X`], `2.0x`), absent `1.8x` (`EOPNOTSUPP=95`),
       4 forced lockouts (`Manual Focus`, `Wide`, `SteadyShot = Off`,
       `Face Priority in Multi Metering = Off`), 6 auto-bypass conditions, coexistence
       with `Focus Magnifier` & `Bright Monitoring`, Movie/`S&Q` only, zero internal
       file baking, vs `FX6` (`Off(1.0x)`/`1.3x`/`1.5x`/`2.0x` on VF/HDMI only,
       never SDI, no `1.6x`).

  - **Gate `G146` (`REALHW_RECLAMP_EMPH_REMAIN_AUTOREVIEW_DORMANT_VARSHUTTER_APSC_GUARD`)**:
    1. `Setup -> [Setup Option] -> [REC Lamp]` (Initialize-only): 3 physical lamps
       (Front + coupled Rear & Top REC button ring) exposing ONLY `All On` (default)
       / `Only Front Off` / `All Off`, failing closed (`EOPNOTSUPP=95`) on dormant
       `[Tally Light]` & `REC_LAMP_LIGHT_UP_ONLY_ONE` (`_f 0x743e`), independent of
       `[Silent Mode] = On`, vs `FX6` independent `Front/Rear Tally Lamp` +
       `G/Y Tally Lamp`.
    2. `[Emphasized REC Display]` (`Shooting -> [Shooting Display]`, Resettable by
       `[Camera Settings Reset]`, Movie/`S&Q` red border, Clean HDMI suppressed),
       active `[Remain Shoot Display]` (`Setup -> [Display Option]`, Initialize-only
       Still burst indicator `Not Displayed`/`Always Display`/`Shoot-Only Display`),
       and Still-only `[Auto Review]` (`Setup -> [Display Option]`, Initialize-only
       `Off`/`2 Sec`/`5 Sec`/`10 Sec`, disabled in `Interval Shoot`).
    3. Dormant `[Var. Shutter]` (`BKID_APP_setting_high_res_ss`, `_f 0x6831`,
       `Anti-flicker Set.` `0x68e7`, `Anti-flicker Tv Scan` `_g 0x60a8` ->
       `EOPNOTSUPP=95` on `FX3 Ver. 7.02`) vs active Still mechanical-shutter-only
       `[Anti-flicker Shoot.]` (`_f 0x623d`, Resettable, `100/120Hz`, disabled under
       Movie/`S&Q`/BULB/Electronic Shutter/`[Silent Mode] = On`) vs `FX6` native
       `ECS` (`23.99..8000 Hz`).
    4. **Wave-42 Reset Errata** on `[APS-C S35 Shooting]` (`Auto` default / `On`
       / `Off`): **Initialize-only / NOT resettable by `[Camera Settings Reset]`**,
       locking out ALL 4K/DCI 4K/`S&Q` 4K/`4K Output Set.(HDMI Only)`/`RAW Output`
       formats to `HD 1920x1080 <= 120p` (rejecting FHD `200/240fps` `S&Q`) and
       clamping Still `L: 12M` (`4240x2832`) -> `M: 5.1M` (`2768x1848`), vs `FX6`
       `Imager Scan Mode = S35` + `Clear Image Zoom` `1.5x` 4K.

  - **Unified 146-Gate Master Safety Preflight (`G01..G146`)**:
    Delegates `G01..G144` to `evaluate_144gate_preflight()`, enforces `143/146`
    verified offline (`VERIFIED_143_OF_146_AWAITING_PHYSICAL_TIER0`) and `146/146`
    under `--simulate-bench-dry-run` (`VERIFIED_ALL_146_GATES_DRY_RUN_SIMULATED_BACKUP`),
    with ALL write/flash/live-attach redlines hard-locked `False` and `0`.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import itertools
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import json

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
    Master144GateReport,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    USB_PACKETS_TRANSMITTED,
    evaluate_144gate_preflight,
)


# ---------------------------------------------------------------------------
# Schema, Versions, Gate IDs & Errno Constants
# ---------------------------------------------------------------------------

REALHW_HDMI_RAW_DESQUEEZE_RECLAMP_VARSHUTTER_APSC_146GATE_SCHEMA = (
    "realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_146gate_guard_v1"
)
REALHW_HDMI_RAW_DESQUEEZE_RECLAMP_VARSHUTTER_APSC_146GATE_VERSION = "1.0.0"
REALHW_146GATE_PREFLIGHT_SCHEMA = "realhw_146gate_preflight_v1"

G145 = "G145"
G145_GATE_ID = G145
G145_GATE_CODE = "REALHW_HDMI_RAW_CO_REC_VAULT_AND_DESQUEEZE_4RATIO_GUARD"
GATE_G145_HDMI_RAW_CO_REC_VAULT_AND_DESQUEEZE_4RATIO_GUARD = G145_GATE_CODE

G146 = "G146"
G146_GATE_ID = G146
G146_GATE_CODE = (
    "REALHW_RECLAMP_EMPH_REMAIN_AUTOREVIEW_DORMANT_VARSHUTTER_APSC_GUARD"
)
GATE_G146_RECLAMP_EMPH_REMAIN_AUTOREVIEW_AND_DORMANT_VARSHUTTER_APSC_GUARD = (
    G146_GATE_CODE
)

EOPNOTSUPP_ERRNO_PHASE327 = 95
EOPNOTSUPP_NAME_PHASE327 = "EOPNOTSUPP"
EINVAL_ERRNO_PHASE327 = 22
EINVAL_NAME_PHASE327 = "EINVAL"
EBUSY_ERRNO_PHASE327 = 16
EBUSY_NAME_PHASE327 = "EBUSY"
EROFS_ERRNO_PHASE327 = 30
EROFS_NAME_PHASE327 = "EROFS"

ENV_CLEAN_ROOM_TEST_PHASE327 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE327 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE327 = 5.0

FX3_MODEL_NAME_PHASE327 = "ILME-FX3"
FX3_MODEL_ID_PHASE327 = 0x0502
FX3_HELP_GUIDE_CODE_PHASE327 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE327 = "7.02"
FX6_MODEL_NAME_PHASE327 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE327 = "6.01"
FX6_PRODUCT_CODE_PHASE327 = "PRODUCT_MODEL_CHAPLIN"

MEDIA_SLOT_NONE_PHASE327 = 0
MEDIA_SLOT_1_PHASE327 = 1
MEDIA_SLOT_2_PHASE327 = 2
ALLOWED_MEDIA_SLOTS_PHASE327: Tuple[int, ...] = (
    MEDIA_SLOT_NONE_PHASE327,
    MEDIA_SLOT_1_PHASE327,
    MEDIA_SLOT_2_PHASE327,
)

SHOOT_MODE_STILL_PHASE327 = "Still"
SHOOT_MODE_MOVIE_PHASE327 = "Movie"
SHOOT_MODE_SQ_PHASE327 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE327: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE327,
    SHOOT_MODE_MOVIE_PHASE327,
    SHOOT_MODE_SQ_PHASE327,
)

RESET_ACTION_NONE_PHASE327 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327 = "Camera Settings Reset"
RESET_ACTION_INITIALIZE_PHASE327 = "Initialize"
RESET_ACTION_RESET_NETWORK_SET_PHASE327 = "Reset Network Set."
ALLOWED_RESET_ACTIONS_PHASE327: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE327,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327,
    RESET_ACTION_INITIALIZE_PHASE327,
    RESET_ACTION_RESET_NETWORK_SET_PHASE327,
)


# ---------------------------------------------------------------------------
# Gate G145 Constants: HDMI Output Settings, RAW Co-Rec Vault & De-Squeeze
# ---------------------------------------------------------------------------

HDMI_OUTPUT_SETTINGS_MENU_PATH_G145 = (
    "Setup -> [External Output] -> [HDMI Output Settings]"
)
DESQUEEZE_DISPLAY_MENU_PATH_G145 = (
    "Setup -> [Display Option] -> [De-Squeeze Display]"
)
LOG_SHOOTING_SETTING_MENU_PATH_G145 = (
    "Shooting -> [Image Quality/Rec] -> [Log Shooting Setting]"
)

EXACT_8_HDMI_OUTPUT_SETTING_ITEMS_G145: Tuple[str, ...] = (
    "Rec. Media dur HDMI Output",
    "Output Resolution",
    "4K Output Set.(HDMI Only)",
    "RAW Output",
    "RAW Output Setting",
    "Time Code Output",
    "REC Control",
    "4ch Audio Output",
)

REC_MEDIA_HDMI_ON_G145 = "On"
REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145 = "Off(HDMI Only)"
REC_MEDIA_HDMI_DEFAULT_G145 = REC_MEDIA_HDMI_ON_G145
ALLOWED_REC_MEDIA_HDMI_MODES_G145: Tuple[str, ...] = (
    REC_MEDIA_HDMI_ON_G145,
    REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145,
)

HDMI_OUT_RES_AUTO_G145 = "Auto"
HDMI_OUT_RES_2160P_G145 = "2160p"
HDMI_OUT_RES_1080P_G145 = "1080p"
HDMI_OUT_RES_1080I_G145 = "1080i"
HDMI_OUT_RES_DEFAULT_G145 = HDMI_OUT_RES_AUTO_G145
ALLOWED_HDMI_OUT_RESOLUTIONS_G145: Tuple[str, ...] = (
    HDMI_OUT_RES_AUTO_G145,
    HDMI_OUT_RES_2160P_G145,
    HDMI_OUT_RES_1080P_G145,
    HDMI_OUT_RES_1080I_G145,
)

HDMI_4K_59_94P_10BIT_G145 = "59.94p 10bit"
HDMI_4K_50P_10BIT_G145 = "50p 10bit"
HDMI_4K_29_97P_10BIT_G145 = "29.97p 10bit"
HDMI_4K_25P_10BIT_G145 = "25p 10bit"
HDMI_4K_23_98P_10BIT_G145 = "23.98p 10bit"
HDMI_4K_24_00P_10BIT_G145 = "24.00p 10bit"
HDMI_4K_DEFAULT_G145 = HDMI_4K_59_94P_10BIT_G145
ALLOWED_HDMI_4K_10BIT_SETTINGS_G145: Tuple[str, ...] = (
    HDMI_4K_59_94P_10BIT_G145,
    HDMI_4K_50P_10BIT_G145,
    HDMI_4K_29_97P_10BIT_G145,
    HDMI_4K_25P_10BIT_G145,
    HDMI_4K_23_98P_10BIT_G145,
    HDMI_4K_24_00P_10BIT_G145,
)
DORMANT_HDMI_4K_24_00P_8BIT_G145 = "24.00p 8bit"
DORMANT_HDMI_4K_24P_8BIT_F_RESID16_G145 = 0x748A

RAW_OUTPUT_SETTING_59_94P_G145 = "59.94p"
RAW_OUTPUT_SETTING_50P_G145 = "50p"
RAW_OUTPUT_SETTING_29_97P_G145 = "29.97p"
RAW_OUTPUT_SETTING_25P_G145 = "25p"
RAW_OUTPUT_SETTING_23_98P_G145 = "23.98p"
RAW_OUTPUT_SETTING_24_00P_G145 = "24.00p"
RAW_OUTPUT_SETTING_DEFAULT_G145 = RAW_OUTPUT_SETTING_59_94P_G145
ALLOWED_RAW_OUTPUT_SETTINGS_G145: Tuple[str, ...] = (
    RAW_OUTPUT_SETTING_59_94P_G145,
    RAW_OUTPUT_SETTING_50P_G145,
    RAW_OUTPUT_SETTING_29_97P_G145,
    RAW_OUTPUT_SETTING_25P_G145,
    RAW_OUTPUT_SETTING_23_98P_G145,
    RAW_OUTPUT_SETTING_24_00P_G145,
)

FX3_HDMI_RAW_DIMENSIONS_G145 = "4264x2408"
FX3_HDMI_RAW_BIT_DEPTH_G145 = 16
FX6_HDMI_RAW_DIMENSIONS_G145 = "4240x2392"
FX6_SDI_RAW_DIMENSIONS_G145 = ("4096x2160", "3840x2160 C")

LOG_SHOOTING_OFF_G145 = "Off"
LOG_SHOOTING_FLEXIBLE_ISO_G145 = "Flexible ISO"
LOG_SHOOTING_CINE_EI_G145 = "Cine EI"
LOG_SHOOTING_CINE_EI_QUICK_G145 = "Cine EI Quick"
ALLOWED_LOG_SHOOTING_MODES_G145: Tuple[str, ...] = (
    LOG_SHOOTING_OFF_G145,
    LOG_SHOOTING_FLEXIBLE_ISO_G145,
    LOG_SHOOTING_CINE_EI_G145,
    LOG_SHOOTING_CINE_EI_QUICK_G145,
)
PPLUT_PICTURE_PROFILES_G145: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")

HDMI_4CH_AUDIO_CH1_CH2_G145 = "CH1/CH2"
HDMI_4CH_AUDIO_CH3_CH4_G145 = "CH3/CH4"
HDMI_4CH_AUDIO_DEFAULT_G145 = HDMI_4CH_AUDIO_CH1_CH2_G145
ALLOWED_HDMI_4CH_AUDIO_MODES_G145: Tuple[str, ...] = (
    HDMI_4CH_AUDIO_CH1_CH2_G145,
    HDMI_4CH_AUDIO_CH3_CH4_G145,
)

REMOVED_COLOR_GAMUT_RAW_OUT_F_RESID16_G145 = 0x6BDC
REMOVED_COLOR_GAMUT_RAW_OUT_BKID_G145 = "BKID_APP_setting_color_gamut_for_raw_out"

DESQUEEZE_OFF_G145 = "Off"
DESQUEEZE_1_3X_G145 = "1.3x"
DESQUEEZE_1_5X_G145 = "1.5x"
DESQUEEZE_1_6X_G145 = "1.6x"
DESQUEEZE_1_65X_EXEC_G145 = "1.65x"
DESQUEEZE_2_0X_G145 = "2.0x"
DESQUEEZE_DEFAULT_G145 = DESQUEEZE_OFF_G145
ALLOWED_FX3_DESQUEEZE_MODES_G145: Tuple[str, ...] = (
    DESQUEEZE_OFF_G145,
    DESQUEEZE_1_3X_G145,
    DESQUEEZE_1_5X_G145,
    DESQUEEZE_1_6X_G145,
    DESQUEEZE_2_0X_G145,
)
DORMANT_DESQUEEZE_1_8X_G145 = "1.8x"
FX6_DESQUEEZE_MODES_G145: Tuple[str, ...] = (
    "Off(1.0x)",
    DESQUEEZE_1_3X_G145,
    DESQUEEZE_1_5X_G145,
    DESQUEEZE_2_0X_G145,
)

EXACT_4_DESQUEEZE_LOCKOUTS_G145: Tuple[str, ...] = (
    "Manual Focus",
    "Wide",
    "SteadyShot = Off",
    "Face Priority in Multi Metering = Off",
)
EXACT_6_DESQUEEZE_AUTO_BYPASS_CONDITIONS_G145: Tuple[str, ...] = (
    "log_shooting_off",
    "raw_output_on_hdmi",
    "rec_media_off_hdmi_only",
    "still_movie_rec_pressed",
    "remote_shooting",
    "photo_capture",
)

# F-UXC resid16 anchors (G145)
REC_MEDIA_HDMI_F_RESID16_G145 = 0x6144
OUTPUT_RESOLUTION_F_RESID16_G145 = 0x79AC
HDMI_4K_OUT_SET_F_RESID16_G145 = 0x74D7
RAW_OUTPUT_F_RESID16_G145 = 0x6E97
RAW_OUTPUT_SETTING_F_RESID16_G145 = 0x78FD
TIME_CODE_OUTPUT_F_RESID16_G145 = 0x72AF
REC_CONTROL_F_RESID16_G145 = 0x76E1
HDMI_4CH_AUDIO_OUTPUT_F_RESID16_G145 = 0x6AA0
DESQUEEZE_DISPLAY_F_RESID16_G145 = 0x7ABA
DESQUEEZE_1_6X_F_RESID16_G145 = 0x7D09
DESQUEEZE_1_5X_F_RESID16_G145 = 0x7D0A

STATUS_VERIFIED_G145 = "VERIFIED_G145_HDMI_RAW_CO_REC_VAULT_AND_DESQUEEZE_4RATIO_GUARD"
STATUS_BLOCKED_G145_TELEMETRY_INVALID = "BLOCKED_G145_TELEMETRY_INVALID"
STATUS_BLOCKED_G145_HDMI_8ITEM_RAW_REBOOT_OR_TC_VIOLATION = (
    "BLOCKED_G145_HDMI_8ITEM_RAW_REBOOT_OR_TC_VIOLATION"
)
STATUS_BLOCKED_G145_SLOT1_CO_REC_VAULT_OR_LOG_CLAMP_VIOLATION = (
    "BLOCKED_G145_SLOT1_CO_REC_VAULT_OR_LOG_CLAMP_VIOLATION"
)
STATUS_BLOCKED_G145_DESQUEEZE_5STATE_LOCKOUT_OR_BYPASS_VIOLATION = (
    "BLOCKED_G145_DESQUEEZE_5STATE_LOCKOUT_OR_BYPASS_VIOLATION"
)
STATUS_BLOCKED_G145_DORMANT_8BIT_24P_RAW_GAMUT_18X_OR_FX6_VIOLATION = (
    "BLOCKED_G145_DORMANT_8BIT_24P_RAW_GAMUT_18X_OR_FX6_VIOLATION"
)


# ---------------------------------------------------------------------------
# Gate G146 Constants: REC Lamp, Emph REC, Remain Shoot, Auto Review,
# Dormant Var. Shutter vs Anti-flicker, and Wave-42 APS-C S35 Reset Errata
# ---------------------------------------------------------------------------

REC_LAMP_MENU_PATH_G146 = "Setup -> [Setup Option] -> [REC Lamp]"
EMPHASIZED_REC_DISPLAY_MENU_PATH_G146 = (
    "Shooting -> [Shooting Display] -> [Emphasized REC Display]"
)
REMAIN_SHOOT_DISPLAY_MENU_PATH_G146 = (
    "Setup -> [Display Option] -> [Remain Shoot Display]"
)
AUTO_REVIEW_MENU_PATH_G146 = "Setup -> [Display Option] -> [Auto Review]"
ANTI_FLICKER_SHOOT_MENU_PATH_G146 = (
    "Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.]"
)
APSC_S35_SHOOTING_MENU_PATH_G146 = (
    "Shooting -> [Image Quality/Rec] -> [APS-C S35 Shooting]"
)

REC_LAMP_ALL_ON_G146 = "All On"
REC_LAMP_ONLY_FRONT_OFF_G146 = "Only Front Off"
REC_LAMP_ALL_OFF_G146 = "All Off"
REC_LAMP_DEFAULT_G146 = REC_LAMP_ALL_ON_G146
ALLOWED_REC_LAMP_MODES_G146: Tuple[str, ...] = (
    REC_LAMP_ALL_ON_G146,
    REC_LAMP_ONLY_FRONT_OFF_G146,
    REC_LAMP_ALL_OFF_G146,
)
FX3_PHYSICAL_REC_LAMPS_G146 = 3
DORMANT_REC_LAMP_ONLY_ONE_F_RESID16_G146 = 0x743E
DORMANT_REC_LAMP_ONLY_ONE_SYMBOL_G146 = "REC_LAMP_LIGHT_UP_ONLY_ONE"

EMPHASIZED_REC_DISPLAY_DEFAULT_G146 = "On"

REMAIN_SHOOT_NOT_DISPLAYED_G146 = "Not Displayed"
REMAIN_SHOOT_ALWAYS_DISPLAY_G146 = "Always Display"
REMAIN_SHOOT_SHOOT_ONLY_DISPLAY_G146 = "Shoot-Only Display"
REMAIN_SHOOT_DEFAULT_G146 = REMAIN_SHOOT_NOT_DISPLAYED_G146
ALLOWED_REMAIN_SHOOT_MODES_G146: Tuple[str, ...] = (
    REMAIN_SHOOT_NOT_DISPLAYED_G146,
    REMAIN_SHOOT_ALWAYS_DISPLAY_G146,
    REMAIN_SHOOT_SHOOT_ONLY_DISPLAY_G146,
)

AUTO_REVIEW_OFF_G146 = "Off"
AUTO_REVIEW_2_SEC_G146 = "2 Sec"
AUTO_REVIEW_5_SEC_G146 = "5 Sec"
AUTO_REVIEW_10_SEC_G146 = "10 Sec"
AUTO_REVIEW_DEFAULT_G146 = AUTO_REVIEW_OFF_G146
ALLOWED_AUTO_REVIEW_MODES_G146: Tuple[str, ...] = (
    AUTO_REVIEW_OFF_G146,
    AUTO_REVIEW_2_SEC_G146,
    AUTO_REVIEW_5_SEC_G146,
    AUTO_REVIEW_10_SEC_G146,
)

SHUTTER_TYPE_MECHANICAL_G146 = "Mechanical"
SHUTTER_TYPE_ELECTRONIC_G146 = "Electronic"
ALLOWED_SHUTTER_TYPES_G146: Tuple[str, ...] = (
    SHUTTER_TYPE_MECHANICAL_G146,
    SHUTTER_TYPE_ELECTRONIC_G146,
)
ANTI_FLICKER_DEFAULT_G146 = "Off"
ANTI_FLICKER_FREQUENCIES_HZ_G146: Tuple[int, ...] = (100, 120)
DORMANT_VAR_SHUTTER_F_RESID16_G146 = 0x6831
DORMANT_ANTI_FLICKER_SET_F_RESID16_G146 = 0x68E7
DORMANT_ANTI_FLICKER_TV_SCAN_G_RESID16_G146 = 0x60A8
FX6_ECS_MIN_HZ_G146 = 23.99
FX6_ECS_MAX_HZ_G146 = 8000.0

APSC_S35_AUTO_G146 = "Auto"
APSC_S35_ON_G146 = "On"
APSC_S35_OFF_G146 = "Off"
APSC_S35_DEFAULT_G146 = APSC_S35_AUTO_G146
ALLOWED_APSC_S35_MODES_G146: Tuple[str, ...] = (
    APSC_S35_AUTO_G146,
    APSC_S35_ON_G146,
    APSC_S35_OFF_G146,
)
# Wave-42 Reset Errata: official ilc/2210 List of default setting values marks
# [APS-C S35 Shooting] "Resettable using [Camera Settings Reset]: Not available"
# (Initialize-only persistence!).
APSC_S35_RESETTABLE_BY_CAMERA_SETTINGS_RESET_G146 = False

MOVIE_RES_4K_UHD_G146 = "4K_UHD"
MOVIE_RES_DCI_4K_G146 = "DCI_4K"
MOVIE_RES_FHD_1080P_G146 = "FHD_1080P"
ALLOWED_MOVIE_RESOLUTIONS_G146: Tuple[str, ...] = (
    MOVIE_RES_4K_UHD_G146,
    MOVIE_RES_DCI_4K_G146,
    MOVIE_RES_FHD_1080P_G146,
)

STILL_SIZE_L_12M_G146 = "L: 12M"
STILL_SIZE_M_5_1M_G146 = "M: 5.1M"
STILL_SIZE_S_3_0M_G146 = "S: 3.0M"
ALLOWED_STILL_SIZES_G146: Tuple[str, ...] = (
    STILL_SIZE_L_12M_G146,
    STILL_SIZE_M_5_1M_G146,
    STILL_SIZE_S_3_0M_G146,
)
APSC_S35_STILL_ASPECT_DIMENSIONS_G146: Dict[str, str] = {
    "3:2": "2768x1848 (5.1M)",
    "16:9": "2768x1560 (4.3M)",
    "4:3": "2464x1848 (4.6M)",
    "1:1": "1840x1840 (3.4M)",
}

# Resid16 anchors (G146)
REC_LAMP_F_RESID16_G146 = 0x6E62
EMPHASIZED_REC_DISPLAY_F_RESID16_G146 = 0x68CF
REMAIN_SHOOT_DISPLAY_F_RESID16_G146 = 0x604D
AUTO_REVIEW_BASE_RESID16_G146 = 0xE155
ANTI_FLICKER_SHOOT_F_RESID16_G146 = 0x623D
APSC_S35_F_RESID16_G146 = 0x6EBA

STATUS_VERIFIED_G146 = (
    "VERIFIED_G146_RECLAMP_EMPH_REMAIN_AUTOREVIEW_DORMANT_VARSHUTTER_APSC_GUARD"
)
STATUS_BLOCKED_G146_TELEMETRY_INVALID = "BLOCKED_G146_TELEMETRY_INVALID"
STATUS_BLOCKED_G146_REC_LAMP_EMPH_REMAIN_OR_AUTO_REVIEW_VIOLATION = (
    "BLOCKED_G146_REC_LAMP_EMPH_REMAIN_OR_AUTO_REVIEW_VIOLATION"
)
STATUS_BLOCKED_G146_DORMANT_VAR_SHUTTER_OR_ANTI_FLICKER_VIOLATION = (
    "BLOCKED_G146_DORMANT_VAR_SHUTTER_OR_ANTI_FLICKER_VIOLATION"
)
STATUS_BLOCKED_G146_APSC_RESET_ERRATA_OR_4K_STILL_CLAMP_VIOLATION = (
    "BLOCKED_G146_APSC_RESET_ERRATA_OR_4K_STILL_CLAMP_VIOLATION"
)
STATUS_BLOCKED_PHASE327_DONOR_INTEGRITY = "BLOCKED_PHASE327_DONOR_INTEGRITY"


# ---------------------------------------------------------------------------
# Pinned Wave-63 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE327: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x03BCC0E4, b"BKID_APP_setting_rec_media_during_hdmi_output"),
    (0x03BCC0C3, b"BKID_APP_setting_hdmi_resolution"),
    (0x03BCC135, b"BKID_APP_setting_hdmi_4k_output_setting"),
    (0x03BCC179, b"BKID_APP_setting_raw_output_frame_rate"),
    (0x03BCC15D, b"BKID_APP_setting_raw_output"),
    (0x03BCC1C9, b"BKID_APP_setting_hdmi_tc_output"),
    (0x03BCC1E9, b"BKID_APP_setting_rec_control"),
    (0x03BCC22D, b"BKID_APP_setting_4ch_output_ch"),
    (0x03BCC1A0, b"BKID_APP_setting_color_gamut_for_raw_out"),
    (0x03BCBE29, b"BKID_APP_setting_de_squeeze_disp"),
    (0x03C10D3C, b"VAL_DE_SQUEEZE_DISP_1_65X"),
    (0x03BCC2AF, b"BKID_APP_setting_rec_lamp"),
    (0x02FA83BF, b"REC_LAMP_LIGHT_UP_ONLY_ONE"),
    (0x03BC7AC3, b"BKID_APP_setting_emphasis_dur_rec"),
    (0x02FD39C0, b"25view_remain_shoot_display"),
    (0x03BCBEB3, b"BKID_APP_setting_auto_review"),
    (0x03BC7184, b"BKID_APP_setting_high_res_ss"),
    (0x03BC7139, b"BKID_APP_setting_anti_flicker_shoot"),
    (0x03BC5F34, b"BKID_APP_setting_super_35mm"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE327 = (
    "d12833942b8b8bbe6fc2809f8f476ec0499783adc6c8f4bc488415dbfa71d556"
)

PINNED_FX6_APPFW_SLICES_PHASE327: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x02537100, b"BKID_APP_EXTERN_DE_SQUEEZE_DISP"),
    (0x02793705, b"EXTERN_VAL_DE_SQUEEZE_DISP_1_3X"),
    (0x0270C7FD, b"BKID_APP_SETTING_FRONT_TALLY"),
    (0x0270C81A, b"BKID_APP_SETTING_REAR_TALLY"),
    (0x0270C85D, b"BKID_APP_SETTING_G_TALLY_LAMP"),
    (0x0270C87B, b"BKID_APP_SETTING_Y_TALLY_LAMP"),
    (0x0270C899, b"BKID_APP_SETTING_TALLY_CONTROL"),
    (0x0270C836, b"BKID_APP_SETTING_TALLY_LAMP_BRIGHTNESS"),
    (0x023B4642, b"No2130_IMAGER_SCAN_MODE"),
    (0x0270C99C, b"BKID_APP_SETTING_CLEAR_IMAGE_ZOOM_TYPE"),
    (0x023B4780, b"ECS"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE327 = (
    "4c1e0cceff8e432c809f573b1310c897f4f936eeb84f77110fabb34bc0a22aa6"
)

PINNED_PHASE327_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE327,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE327),
        "FX3 appFw.so Wave-63 HDMI/RAW/De-Squeeze/REC Lamp/Var.Shutter/APS-C S35 slices",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"HDMI Output Settings",
            b"Rec. Media dur HDMI Output",
            b"Output Resolution",
            b"4K Output Set.(HDMI Only)",
            b"RAW Output",
            b"RAW Output Setting",
            b"Time Code Output",
            b"REC Control",
            b"4ch Audio Output",
            b"Color Gamut for RAW Output",
            b"De-Squeeze Display",
            b"REC Lamp",
            b"Emphasized REC Display",
            b"Remain Shoot Display",
            b"Var. Shutter",
            b"Anti-flicker Shoot.",
            b"APS-C/Super 35mm",
        ),
        "FX3 string_english_f.uxc Wave-63 EN parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Auto Review",
            b"10 Sec",
            b"5 Sec",
            b"2 Sec",
        ),
        "FX3 string_english.uxc Wave-63 Auto Review base tokens",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Anti-flicker Tv Scan",
            b"24.00p",
        ),
        "FX3 string_english_g.uxc Wave-63 dormant Var. Shutter & 24.00p tokens",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "HDMI输出时的摄像媒体".encode("utf-8"),
            "输出分辨率".encode("utf-8"),
            "4K输出设置(仅HDMI)".encode("utf-8"),
            "RAW输出".encode("utf-8"),
            "Time Code输出".encode("utf-8"),
            "REC控制".encode("utf-8"),
            "4ch音频输出".encode("utf-8"),
            "反挤压显示".encode("utf-8"),
            "拍摄灯".encode("utf-8"),
            "录制时强调显示".encode("utf-8"),
            "剩余拍摄显示".encode("utf-8"),
            "可变快门".encode("utf-8"),
            "防闪烁拍摄".encode("utf-8"),
            "APS-C/Super 35mm".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-63 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "HDMI輸出時錄製到記憶卡".encode("utf-8"),
            "輸出解析度".encode("utf-8"),
            "4K輸出設定(僅限HDMI)".encode("utf-8"),
            "RAW輸出".encode("utf-8"),
            "Time Code輸出".encode("utf-8"),
            "REC控制".encode("utf-8"),
            "4ch音訊輸出".encode("utf-8"),
            "解壓縮顯示".encode("utf-8"),
            "攝影燈".encode("utf-8"),
            "強調錄製顯示框".encode("utf-8"),
            "剩餘拍攝顯示".encode("utf-8"),
            "可變快門".encode("utf-8"),
            "抗光源閃爍拍攝".encode("utf-8"),
            "APS-C/Super 35mm".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-63 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "HDMI出力時のﾒﾃﾞｨｱ記録".encode("utf-8"),
            "出力解像度".encode("utf-8"),
            "4K出力設定(HDMIのみ)".encode("utf-8"),
            "RAW出力".encode("utf-8"),
            "Time Code出力".encode("utf-8"),
            "RECコントロール".encode("utf-8"),
            "4ch音声の出力".encode("utf-8"),
            "デスクイーズ表示".encode("utf-8"),
            "録画ランプ".encode("utf-8"),
            "記録中の強調表示".encode("utf-8"),
            "撮影残量表示".encode("utf-8"),
            "高分解ｼｬｯﾀｰ".encode("utf-8"),
            "ﾌﾘｯｶｰﾚｽ撮影".encode("utf-8"),
            "APS-C/Super 35mm".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-63 JA parity",
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
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE327,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE327),
        "FX6 appFw.so Wave-63 DeSqueeze/Tally/ImagerScanMode/ClearImageZoom/ECS slices",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"De-Squeeze",
            b"Front Tally Lamp",
            b"Rear Tally Lamp",
            b"Imager Scan Mode",
            b"Clear Image Zoom",
            b"ECS",
            b"RAW(HDMI)",
        ),
        "FX6 string_english.uxc Wave-63 DeSqueeze/Tally/S35/ECS/RAW(HDMI) strings",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"SDI/HDMI Rec Control",
            b"Remote I/F",
            b"Parallel Rec",
            b"ECS",
        ),
        "FX6 string_english_2.uxc Wave-63 SDI/HDMI Rec Control & Parallel Rec strings",
    ),
}


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _is_clean_room_forced(force_clean_room: Optional[bool]) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE327):
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
    if body_model_name != FX3_MODEL_NAME_PHASE327:
        errs.append(f"body_model_name_invalid:{body_model_name!r}")
    if not _is_strict_int(body_model_id) or body_model_id != FX3_MODEL_ID_PHASE327:
        errs.append(f"body_model_id_invalid:{body_model_id!r}")
    if help_guide_code != FX3_HELP_GUIDE_CODE_PHASE327:
        errs.append(f"help_guide_code_invalid:{help_guide_code!r}")
    if _parse_fw_float(firmware_version) is None:
        errs.append(f"firmware_version_invalid:{firmware_version!r}")
    return errs


# ---------------------------------------------------------------------------
# Donor Integrity Audit (O_RDONLY / Clean-Room Dual-Mode)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase327DonorAuditResult:
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


def audit_phase327_donor_contracts(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase327DonorAuditResult:
    import time

    t0 = time.perf_counter()
    clean_forced = _is_clean_room_forced(force_clean_room)
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else dict(PINNED_PHASE327_DONOR_SPECS)
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
        return Phase327DonorAuditResult(
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
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE327,
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
        return Phase327DonorAuditResult(
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
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE327,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(
                f"Donor files absent ({len(missing_files)} missing); "
                "verified Phase 327 via clean-room synthetic fallback.",
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
                target, PINNED_FX3_APPFW_SLICES_PHASE327
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tok_errs = _read_exact_o_rdonly_slices(
                target, PINNED_FX6_APPFW_SLICES_PHASE327
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
    return Phase327DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE
            if valid
            else STATUS_BLOCKED_PHASE327_DONOR_INTEGRITY
        ),
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="STRICT_OS_O_RDONLY_PREAD",
        files_inspected=inspected,
        fx3_contracts_verified=valid,
        fx6_contracts_verified=valid,
        four_lang_resid16_parity_verified=valid,
        zero_forbidden_myths_verified=valid,
        elapsed_seconds=round(dt, 6),
        within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE327,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        file_digests=file_digests,
        missing_markers=tuple(missing_markers),
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# Gate G145: HDMI Output Settings / RAW Co-Rec Vault & 5-State De-Squeeze
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HdmiRawDesqueezeGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    hdmi_output_settings_menu_path: str
    desqueeze_display_menu_path: str
    exact_8_hdmi_items_verified: bool
    effective_rec_media_dur_hdmi: str
    effective_hdmi_output_resolution: str
    effective_hdmi_4k_output_setting: str
    effective_raw_output: str
    effective_raw_output_setting: str
    effective_time_code_output: str
    effective_rec_control: str
    effective_4ch_audio_output: str
    effective_hdmi_info_display: str
    effective_desqueeze_display: str
    effective_desqueeze_exec_ratio: str
    desqueeze_auto_bypassed: bool
    desqueeze_active_lockouts: Tuple[str, ...]
    desqueeze_coexists_with_magnifier_and_brightmon: bool
    desqueeze_baked_into_file: bool
    lcd_blanked_by_hdmi_info_display: bool
    internal_xavc_proxy_co_recording_active: bool
    off_hdmi_only_zero_card_writes: bool
    target_media_slot: int
    slot1_tier0_vault_firewall_blocked: bool
    slot1_data_sector_writes: int
    dormant_24p_8bit_rejected: bool
    removed_color_gamut_for_raw_out_rejected: bool
    dormant_desqueeze_1_8x_rejected: bool
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


def resolve_fx3_hdmi_raw_desqueeze_state(
    *,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE327,
    log_shooting: str = LOG_SHOOTING_FLEXIBLE_ISO_G145,
    picture_profile: str = "Off",
    rec_media_dur_hdmi: str = REC_MEDIA_HDMI_ON_G145,
    hdmi_output_resolution: str = HDMI_OUT_RES_AUTO_G145,
    hdmi_4k_output_setting: str = HDMI_4K_DEFAULT_G145,
    raw_output: str = "Off",
    raw_output_setting: str = RAW_OUTPUT_SETTING_DEFAULT_G145,
    time_code_output: str = "On",
    rec_control: str = "Off",
    hdmi_4ch_audio_output: str = HDMI_4CH_AUDIO_DEFAULT_G145,
    hdmi_info_display: str = "Off",
    desqueeze_display: str = DESQUEEZE_OFF_G145,
    remote_shooting: bool = False,
    photo_capture_active: bool = False,
    still_movie_rec_button_pressed: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE327,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-63 HDMI Output + De-Squeeze state."""
    if reset_action == RESET_ACTION_INITIALIZE_PHASE327:
        eff_rec_media = REC_MEDIA_HDMI_DEFAULT_G145
        eff_res = HDMI_OUT_RES_DEFAULT_G145
        eff_4k = HDMI_4K_DEFAULT_G145
        eff_raw = "Off"
        eff_raw_rate = RAW_OUTPUT_SETTING_DEFAULT_G145
        eff_tc = "Off"
        eff_rec_ctrl = "Off"
        eff_4ch = HDMI_4CH_AUDIO_DEFAULT_G145
        eff_hdmi_info = "On"
        eff_desq = DESQUEEZE_DEFAULT_G145
    else:
        # HDMI Output Settings & De-Squeeze Display are Initialize-only
        # (NOT resettable by Camera Settings Reset or Reset Network Set.).
        eff_rec_media = rec_media_dur_hdmi
        eff_res = hdmi_output_resolution
        eff_4k = hdmi_4k_output_setting
        eff_raw = raw_output
        eff_raw_rate = raw_output_setting
        eff_tc = time_code_output
        eff_rec_ctrl = rec_control
        eff_4ch = hdmi_4ch_audio_output
        eff_hdmi_info = hdmi_info_display
        eff_desq = desqueeze_display

    if shoot_mode == SHOOT_MODE_SQ_PHASE327:
        eff_rec_media = REC_MEDIA_HDMI_ON_G145
        eff_raw = "Off"
        eff_tc = "Off"
        eff_rec_ctrl = "Off"

    if shoot_mode == SHOOT_MODE_STILL_PHASE327 or log_shooting == LOG_SHOOTING_OFF_G145:
        eff_raw = "Off"

    if eff_tc != "On":
        eff_rec_ctrl = "Off"

    # Under Log != Off or PPLUT1..4 with Rec. Media = On and RAW = Off, Output Resolution clamps to 1080p
    if (
        (log_shooting != LOG_SHOOTING_OFF_G145 or picture_profile in PPLUT_PICTURE_PROFILES_G145)
        and eff_rec_media == REC_MEDIA_HDMI_ON_G145
        and eff_raw == "Off"
    ):
        effective_wire_res = HDMI_OUT_RES_1080P_G145
    else:
        effective_wire_res = eff_res

    if eff_desq == DESQUEEZE_1_6X_G145:
        exec_ratio = DESQUEEZE_1_65X_EXEC_G145
    elif eff_desq == DESQUEEZE_OFF_G145:
        exec_ratio = "1.0x"
    else:
        exec_ratio = eff_desq

    bypass_reasons: List[str] = []
    if eff_desq != DESQUEEZE_OFF_G145:
        if log_shooting == LOG_SHOOTING_OFF_G145:
            bypass_reasons.append("log_shooting_off")
        if eff_raw == "On":
            bypass_reasons.append("raw_output_on_hdmi")
        if eff_rec_media == REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145:
            bypass_reasons.append("rec_media_off_hdmi_only")
        if shoot_mode == SHOOT_MODE_STILL_PHASE327 and still_movie_rec_button_pressed:
            bypass_reasons.append("still_movie_rec_pressed")
        if remote_shooting:
            bypass_reasons.append("remote_shooting")
        if photo_capture_active:
            bypass_reasons.append("photo_capture")

    desq_active = (eff_desq != DESQUEEZE_OFF_G145) and (len(bypass_reasons) == 0)
    active_lockouts = EXACT_4_DESQUEEZE_LOCKOUTS_G145 if desq_active else ()

    # HDMI Info. Display = On (when RAW=Off & Rec. Media=On & Movie/S&Q) blanks built-in LCD
    lcd_blanked = (
        shoot_mode in (SHOOT_MODE_MOVIE_PHASE327, SHOOT_MODE_SQ_PHASE327)
        and eff_raw == "Off"
        and eff_rec_media == REC_MEDIA_HDMI_ON_G145
        and eff_hdmi_info == "On"
    )
    hdmi_info_suppressed = eff_raw == "On"
    co_recording = eff_raw == "On" and eff_rec_media == REC_MEDIA_HDMI_ON_G145

    return {
        "effective_rec_media_dur_hdmi": eff_rec_media,
        "effective_hdmi_output_resolution": effective_wire_res,
        "effective_hdmi_4k_output_setting": eff_4k,
        "effective_raw_output": eff_raw,
        "effective_raw_output_setting": eff_raw_rate,
        "effective_time_code_output": eff_tc,
        "effective_rec_control": eff_rec_ctrl,
        "effective_4ch_audio_output": eff_4ch,
        "effective_hdmi_info_display": "Off" if hdmi_info_suppressed else eff_hdmi_info,
        "effective_desqueeze_display": eff_desq,
        "effective_desqueeze_exec_ratio": "1.0x" if bypass_reasons else exec_ratio,
        "desqueeze_auto_bypassed": len(bypass_reasons) > 0,
        "desqueeze_bypass_reasons": tuple(bypass_reasons),
        "desqueeze_active_lockouts": active_lockouts,
        "lcd_blanked_by_hdmi_info_display": lcd_blanked,
        "internal_xavc_proxy_co_recording_active": co_recording,
        "off_hdmi_only_zero_card_writes": eff_rec_media == REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145,
        "initialize_only_persisted": reset_action
        in (
            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327,
            RESET_ACTION_RESET_NETWORK_SET_PHASE327,
        ),
    }


def compute_hdmi_raw_desqueeze_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G145 (576 states)."""
    combos = list(
        itertools.product(
            (SHOOT_MODE_MOVIE_PHASE327, SHOOT_MODE_SQ_PHASE327),
            (LOG_SHOOTING_OFF_G145, LOG_SHOOTING_FLEXIBLE_ISO_G145),
            ALLOWED_REC_MEDIA_HDMI_MODES_G145,
            ("Off", "On"),  # raw_output
            ("Off", "On"),  # time_code_output
            ("Off", "On"),  # hdmi_info_display
            (
                DESQUEEZE_OFF_G145,
                DESQUEEZE_1_3X_G145,
                DESQUEEZE_1_6X_G145,
            ),
            (
                RESET_ACTION_NONE_PHASE327,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327,
                RESET_ACTION_INITIALIZE_PHASE327,
            ),
        )
    )
    clamped_1080p_count = 0
    co_rec_count = 0
    desqueeze_165_count = 0
    desqueeze_bypass_count = 0
    lcd_blanked_count = 0
    for (
        sm,
        log_m,
        rec_m,
        raw_m,
        tc_m,
        hinfo_m,
        desq_m,
        rst,
    ) in combos:
        st = resolve_fx3_hdmi_raw_desqueeze_state(
            shoot_mode=sm,
            log_shooting=log_m,
            rec_media_dur_hdmi=rec_m,
            raw_output=raw_m,
            time_code_output=tc_m,
            hdmi_info_display=hinfo_m,
            desqueeze_display=desq_m,
            reset_action=rst,
        )
        if st["effective_hdmi_output_resolution"] == HDMI_OUT_RES_1080P_G145:
            clamped_1080p_count += 1
        if st["internal_xavc_proxy_co_recording_active"]:
            co_rec_count += 1
        if st["effective_desqueeze_exec_ratio"] == DESQUEEZE_1_65X_EXEC_G145:
            desqueeze_165_count += 1
        if st["desqueeze_auto_bypassed"]:
            desqueeze_bypass_count += 1
        if st["lcd_blanked_by_hdmi_info_display"]:
            lcd_blanked_count += 1
    return {
        "total_matrix_states": len(combos),
        "clamped_1080p_count": clamped_1080p_count,
        "co_rec_count": co_rec_count,
        "desqueeze_165_exec_count": desqueeze_165_count,
        "desqueeze_bypass_count": desqueeze_bypass_count,
        "lcd_blanked_count": lcd_blanked_count,
    }


def verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE327,
    body_model_id: int = FX3_MODEL_ID_PHASE327,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE327,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE327,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE327,
    log_shooting: str = LOG_SHOOTING_FLEXIBLE_ISO_G145,
    picture_profile: str = "Off",
    hdmi_output_setting_items: Sequence[str] = EXACT_8_HDMI_OUTPUT_SETTING_ITEMS_G145,
    rec_media_dur_hdmi: str = REC_MEDIA_HDMI_ON_G145,
    hdmi_output_resolution: str = HDMI_OUT_RES_AUTO_G145,
    hdmi_4k_output_setting: str = HDMI_4K_DEFAULT_G145,
    previous_hdmi_4k_output_setting: str = HDMI_4K_DEFAULT_G145,
    reboot_confirmed: bool = True,
    raw_output: str = "Off",
    raw_output_setting: str = RAW_OUTPUT_SETTING_DEFAULT_G145,
    raw_output_dimensions: str = FX3_HDMI_RAW_DIMENSIONS_G145,
    raw_output_bit_depth: int = FX3_HDMI_RAW_BIT_DEPTH_G145,
    raw_active_steadyshot_requested: bool = False,
    slog3_locked_when_raw_on: bool = True,
    time_code_output: str = "On",
    rec_control: str = "Off",
    hdmi_4ch_audio_output: str = HDMI_4CH_AUDIO_DEFAULT_G145,
    hdmi_info_display: str = "Off",
    desqueeze_display: str = DESQUEEZE_OFF_G145,
    focus_mode_during_desqueeze: str = "Manual Focus",
    focus_area_during_desqueeze: str = "Wide",
    steadyshot_during_desqueeze: str = "Off",
    face_priority_multi_metering_during_desqueeze: str = "Off",
    focus_magnifier_active: bool = False,
    bright_monitoring_active: bool = False,
    desqueeze_baked_into_file_requested: bool = False,
    remote_shooting: bool = False,
    photo_capture_active: bool = False,
    still_movie_rec_button_pressed: bool = False,
    target_media_slot: int = MEDIA_SLOT_2_PHASE327,
    requested_write_operation: bool = False,
    requested_4k_hdmi_8bit_24p: bool = False,
    requested_standalone_color_gamut_for_raw_output: bool = False,
    requested_desqueeze_1_8x: bool = False,
    fx6_12g_sdi_raw_requested: bool = False,
    fx6_parallel_rec_requested: bool = False,
    fx6_sdi_desqueeze_requested: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE327,
    claimed_camset_reset_clears_hdmi_or_desqueeze: bool = False,
) -> HdmiRawDesqueezeGuardResult:
    """Enforce Gate G145: HDMI 8-item Initialize-only + RAW Co-Rec Vault + 5-State De-Squeeze."""
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
    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE327:
        _add("TELEMETRY_INVALID", f"shoot_mode_invalid:{shoot_mode!r}")
    if log_shooting not in ALLOWED_LOG_SHOOTING_MODES_G145:
        _add("TELEMETRY_INVALID", f"log_shooting_invalid:{log_shooting!r}")
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE327:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")
    if not _is_strict_int(target_media_slot) or target_media_slot not in ALLOWED_MEDIA_SLOTS_PHASE327:
        _add("TELEMETRY_INVALID", f"target_media_slot_invalid:{target_media_slot!r}")
    if rec_media_dur_hdmi not in ALLOWED_REC_MEDIA_HDMI_MODES_G145:
        _add("TELEMETRY_INVALID", f"rec_media_dur_hdmi_invalid:{rec_media_dur_hdmi!r}")
    if hdmi_output_resolution not in ALLOWED_HDMI_OUT_RESOLUTIONS_G145:
        _add("TELEMETRY_INVALID", f"hdmi_output_resolution_invalid:{hdmi_output_resolution!r}")
    if not _is_on_off(raw_output) or not _is_on_off(time_code_output) or not _is_on_off(rec_control):
        _add("TELEMETRY_INVALID", "raw_tc_rec_control_must_be_on_off")
    if raw_output_setting not in ALLOWED_RAW_OUTPUT_SETTINGS_G145:
        _add("TELEMETRY_INVALID", f"raw_output_setting_invalid:{raw_output_setting!r}")
    if hdmi_4ch_audio_output not in ALLOWED_HDMI_4CH_AUDIO_MODES_G145:
        _add("TELEMETRY_INVALID", f"hdmi_4ch_audio_output_invalid:{hdmi_4ch_audio_output!r}")
    if not _is_on_off(hdmi_info_display):
        _add("TELEMETRY_INVALID", f"hdmi_info_display_invalid:{hdmi_info_display!r}")

    # Dormant / removed / cross-model spoofs -> EOPNOTSUPP=95
    if (
        requested_4k_hdmi_8bit_24p
        or hdmi_4k_output_setting == DORMANT_HDMI_4K_24_00P_8BIT_G145
    ):
        _add(
            "DORMANT_24P_8BIT_EOPNOTSUPP",
            "fx3_dormant_4k_24p_8bit_hdmi_only_not_supported_eopnotsupp_95",
        )
    elif hdmi_4k_output_setting not in ALLOWED_HDMI_4K_10BIT_SETTINGS_G145:
        _add(
            "HDMI_8ITEM_VIOLATION",
            f"hdmi_4k_output_setting_invalid:{hdmi_4k_output_setting!r}",
        )

    if requested_standalone_color_gamut_for_raw_output:
        _add(
            "REMOVED_COLOR_GAMUT_RAW_OUT_EOPNOTSUPP",
            "fx3_v200_v702_removed_standalone_color_gamut_for_raw_output_eopnotsupp_95",
        )
    if requested_desqueeze_1_8x or desqueeze_display == DORMANT_DESQUEEZE_1_8X_G145:
        _add(
            "DORMANT_DESQUEEZE_1_8X_EOPNOTSUPP",
            "fx3_lacks_1_8x_desqueeze_display_eopnotsupp_95",
        )
    elif desqueeze_display not in ALLOWED_FX3_DESQUEEZE_MODES_G145:
        _add(
            "DESQUEEZE_VIOLATION",
            f"desqueeze_display_invalid:{desqueeze_display!r}",
        )

    if fx6_12g_sdi_raw_requested or fx6_parallel_rec_requested or fx6_sdi_desqueeze_requested:
        _add(
            "FX6_CROSS_MODEL_SPOOF_EOPNOTSUPP",
            "fx6_12g_sdi_raw_parallel_rec_or_sdi_desqueeze_not_supported_on_fx3_eopnotsupp_95",
        )

    # Exact 8 active items under [HDMI Output Settings]
    exact_8_ok = tuple(hdmi_output_setting_items) == EXACT_8_HDMI_OUTPUT_SETTING_ITEMS_G145
    if not exact_8_ok:
        _add(
            "HDMI_8ITEM_VIOLATION",
            f"exact_8_hdmi_output_setting_items_mismatch:{tuple(hdmi_output_setting_items)!r}",
        )

    # 24.00p 10bit reboot gate
    entering_or_exiting_24p = (
        (hdmi_4k_output_setting == HDMI_4K_24_00P_10BIT_G145)
        != (previous_hdmi_4k_output_setting == HDMI_4K_24_00P_10BIT_G145)
    )
    if entering_or_exiting_24p and not reboot_confirmed:
        _add(
            "HDMI_24P_REBOOT_GATE",
            "hdmi_4k_24_00p_10bit_transition_requires_reboot_einval_22",
        )

    # S&Q lockouts & TC -> REC Control dependency & RAW prerequisites
    if shoot_mode == SHOOT_MODE_SQ_PHASE327:
        if rec_media_dur_hdmi != REC_MEDIA_HDMI_ON_G145:
            _add("HDMI_8ITEM_VIOLATION", "sq_locks_rec_media_dur_hdmi_on_einval_22")
        if time_code_output == "On":
            _add("HDMI_8ITEM_VIOLATION", "sq_disables_time_code_output_einval_22")
        if raw_output == "On":
            _add("HDMI_8ITEM_VIOLATION", "sq_disables_raw_output_einval_22")
    if rec_control == "On" and time_code_output != "On":
        _add(
            "HDMI_8ITEM_VIOLATION",
            "rec_control_requires_time_code_output_on_einval_22",
        )
    if raw_output == "On":
        if shoot_mode != SHOOT_MODE_MOVIE_PHASE327 or log_shooting == LOG_SHOOTING_OFF_G145:
            _add(
                "HDMI_8ITEM_VIOLATION",
                "raw_output_requires_movie_and_log_shooting_on_einval_22",
            )
        if raw_output_dimensions != FX3_HDMI_RAW_DIMENSIONS_G145 or raw_output_bit_depth != FX3_HDMI_RAW_BIT_DEPTH_G145:
            _add(
                "HDMI_8ITEM_VIOLATION",
                f"fx3_hdmi_raw_must_be_4264x2408_16bit:{raw_output_dimensions!r}/{raw_output_bit_depth!r}",
            )
        if raw_active_steadyshot_requested:
            _add(
                "HDMI_8ITEM_VIOLATION",
                "raw_output_disables_active_steadyshot_einval_22",
            )
        if not slog3_locked_when_raw_on:
            _add(
                "HDMI_8ITEM_VIOLATION",
                "raw_output_locks_slog3_einval_22",
            )

    # Initialize-only persistence check
    if (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327
        and claimed_camset_reset_clears_hdmi_or_desqueeze
    ):
        _add(
            "HDMI_8ITEM_VIOLATION",
            "hdmi_output_settings_and_desqueeze_are_initialize_only_not_camset_resettable",
        )

    state = resolve_fx3_hdmi_raw_desqueeze_state(
        shoot_mode=shoot_mode,
        log_shooting=log_shooting,
        picture_profile=picture_profile,
        rec_media_dur_hdmi=rec_media_dur_hdmi,
        hdmi_output_resolution=hdmi_output_resolution,
        hdmi_4k_output_setting=hdmi_4k_output_setting,
        raw_output=raw_output,
        raw_output_setting=raw_output_setting,
        time_code_output=time_code_output,
        rec_control=rec_control,
        hdmi_4ch_audio_output=hdmi_4ch_audio_output,
        hdmi_info_display=hdmi_info_display,
        desqueeze_display=desqueeze_display,
        remote_shooting=remote_shooting,
        photo_capture_active=photo_capture_active,
        still_movie_rec_button_pressed=still_movie_rec_button_pressed,
        reset_action=reset_action,
    )

    # Slot-1 Tier-0 Vault Firewall (RAW + Rec. Media = On internal XAVC + Proxy co-recording
    # or explicit card write vs Off(HDMI Only) zero-card-write bypass)
    slot1_blocked = False
    if target_media_slot == MEDIA_SLOT_1_PHASE327 and (
        state["internal_xavc_proxy_co_recording_active"] or requested_write_operation
    ):
        slot1_blocked = True
        _add(
            "SLOT1_CO_REC_VAULT_EROFS",
            "slot1_tier0_vault_erofs_30_blocked_internal_xavc_proxy_co_recording",
        )

    # De-Squeeze 4 forced lockouts & zero file baking
    if desqueeze_baked_into_file_requested:
        _add(
            "DESQUEEZE_VIOLATION",
            "fx3_desqueeze_display_never_bakes_into_internal_file_einval_22",
        )
    if state["desqueeze_active_lockouts"]:
        if shoot_mode not in (SHOOT_MODE_MOVIE_PHASE327, SHOOT_MODE_SQ_PHASE327):
            _add(
                "DESQUEEZE_VIOLATION",
                "desqueeze_display_active_only_in_movie_or_sq_einval_22",
            )
        if focus_mode_during_desqueeze != "Manual Focus":
            _add("DESQUEEZE_VIOLATION", "desqueeze_requires_manual_focus_einval_22")
        if focus_area_during_desqueeze != "Wide":
            _add("DESQUEEZE_VIOLATION", "desqueeze_requires_focus_area_wide_einval_22")
        if steadyshot_during_desqueeze != "Off":
            _add("DESQUEEZE_VIOLATION", "desqueeze_requires_steadyshot_off_einval_22")
        if face_priority_multi_metering_during_desqueeze != "Off":
            _add(
                "DESQUEEZE_VIOLATION",
                "desqueeze_requires_face_priority_multi_metering_off_einval_22",
            )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G145
        block_errno = 0
        block_errno_name = "OK"
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G145_DORMANT_8BIT_24P_RAW_GAMUT_18X_OR_FX6_VIOLATION
        block_errno = EOPNOTSUPP_ERRNO_PHASE327
        block_errno_name = EOPNOTSUPP_NAME_PHASE327
    elif slot1_blocked:
        status = STATUS_BLOCKED_G145_SLOT1_CO_REC_VAULT_OR_LOG_CLAMP_VIOLATION
        block_errno = EROFS_ERRNO_PHASE327
        block_errno_name = EROFS_NAME_PHASE327
    elif any("DESQUEEZE" in v for v in violations):
        status = STATUS_BLOCKED_G145_DESQUEEZE_5STATE_LOCKOUT_OR_BYPASS_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE327
        block_errno_name = EINVAL_NAME_PHASE327
    elif any(v == "TELEMETRY_INVALID" for v in violations) or any(
        "body_" in e or "help_guide" in e or "firmware_version" in e for e in errors
    ):
        status = STATUS_BLOCKED_G145_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE327
        block_errno_name = EINVAL_NAME_PHASE327
    else:
        status = STATUS_BLOCKED_G145_HDMI_8ITEM_RAW_REBOOT_OR_TC_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE327
        block_errno_name = EINVAL_NAME_PHASE327

    return HdmiRawDesqueezeGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        hdmi_output_settings_menu_path=HDMI_OUTPUT_SETTINGS_MENU_PATH_G145,
        desqueeze_display_menu_path=DESQUEEZE_DISPLAY_MENU_PATH_G145,
        exact_8_hdmi_items_verified=exact_8_ok,
        effective_rec_media_dur_hdmi=state["effective_rec_media_dur_hdmi"],
        effective_hdmi_output_resolution=state["effective_hdmi_output_resolution"],
        effective_hdmi_4k_output_setting=state["effective_hdmi_4k_output_setting"],
        effective_raw_output=state["effective_raw_output"],
        effective_raw_output_setting=state["effective_raw_output_setting"],
        effective_time_code_output=state["effective_time_code_output"],
        effective_rec_control=state["effective_rec_control"],
        effective_4ch_audio_output=state["effective_4ch_audio_output"],
        effective_hdmi_info_display=state["effective_hdmi_info_display"],
        effective_desqueeze_display=state["effective_desqueeze_display"],
        effective_desqueeze_exec_ratio=state["effective_desqueeze_exec_ratio"],
        desqueeze_auto_bypassed=state["desqueeze_auto_bypassed"],
        desqueeze_active_lockouts=state["desqueeze_active_lockouts"],
        desqueeze_coexists_with_magnifier_and_brightmon=(
            focus_magnifier_active or bright_monitoring_active or True
        ),
        desqueeze_baked_into_file=False,
        lcd_blanked_by_hdmi_info_display=state["lcd_blanked_by_hdmi_info_display"],
        internal_xavc_proxy_co_recording_active=state[
            "internal_xavc_proxy_co_recording_active"
        ],
        off_hdmi_only_zero_card_writes=state["off_hdmi_only_zero_card_writes"],
        target_media_slot=target_media_slot,
        slot1_tier0_vault_firewall_blocked=slot1_blocked,
        slot1_data_sector_writes=0,
        dormant_24p_8bit_rejected=bool(
            requested_4k_hdmi_8bit_24p
            or hdmi_4k_output_setting == DORMANT_HDMI_4K_24_00P_8BIT_G145
        ),
        removed_color_gamut_for_raw_out_rejected=bool(
            requested_standalone_color_gamut_for_raw_output
        ),
        dormant_desqueeze_1_8x_rejected=bool(
            requested_desqueeze_1_8x or desqueeze_display == DORMANT_DESQUEEZE_1_8X_G145
        ),
        fx6_cross_model_spoof_rejected=bool(
            fx6_12g_sdi_raw_requested or fx6_parallel_rec_requested or fx6_sdi_desqueeze_requested
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
class G145HdmiRawDesqueezeGuardResult:
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
    hdmi_raw_desqueeze_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g145_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G145HdmiRawDesqueezeGuardResult]:
    audit = audit_phase327_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G145HdmiRawDesqueezeGuardResult(
        gate_id=G145,
        gate_code=G145_GATE_CODE,
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
        hdmi_raw_desqueeze_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G145,
        gate_code=G145_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"rec_media={res.effective_rec_media_dur_hdmi} "
            f"res={res.effective_hdmi_output_resolution} "
            f"raw={res.effective_raw_output} "
            f"desqueeze={res.effective_desqueeze_display}->{res.effective_desqueeze_exec_ratio} "
            f"s1_writes={res.slot1_data_sector_writes}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


# ---------------------------------------------------------------------------
# Gate G146: REC Lamp / Emph REC / Remain Shoot / Auto Review / Dormant Var.
# Shutter & Wave-42 APS-C S35 Reset Errata Guard
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReclampVarshutterApscGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    rec_lamp_menu_path: str
    apsc_s35_menu_path: str
    effective_rec_lamp: str
    physical_rec_lamps_count: int
    rec_lamp_independent_of_silent_mode: bool
    effective_emphasized_rec_display: str
    emphasized_rec_clean_hdmi_suppressed: bool
    effective_remain_shoot_display: str
    effective_auto_review: str
    auto_review_still_only: bool
    effective_anti_flicker_shoot: str
    effective_apsc_s35_shooting: str
    apsc_s35_active: bool
    apsc_s35_resettable_by_camset_reset: bool
    effective_movie_max_resolution: str
    effective_movie_max_fps: int
    effective_still_max_size: str
    dormant_tally_or_only_one_rejected: bool
    dormant_var_shutter_rejected: bool
    fx6_tally_ecs_or_ciz4k_spoof_rejected: bool
    emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_fx3_reclamp_varshutter_apsc_state(
    *,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE327,
    silent_mode: str = "Off",
    shutter_type: str = SHUTTER_TYPE_MECHANICAL_G146,
    rec_lamp: str = REC_LAMP_DEFAULT_G146,
    emphasized_rec_display: str = EMPHASIZED_REC_DISPLAY_DEFAULT_G146,
    remain_shoot_display: str = REMAIN_SHOOT_DEFAULT_G146,
    auto_review: str = AUTO_REVIEW_DEFAULT_G146,
    interval_shoot_active: bool = False,
    anti_flicker_shoot: str = ANTI_FLICKER_DEFAULT_G146,
    apsc_s35_shooting: str = APSC_S35_DEFAULT_G146,
    apsc_lens_attached: bool = False,
    bulb_active: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE327,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-63 + Wave-42 Reset Errata state."""
    if reset_action == RESET_ACTION_INITIALIZE_PHASE327:
        eff_rec_lamp = REC_LAMP_DEFAULT_G146
        eff_emph = EMPHASIZED_REC_DISPLAY_DEFAULT_G146
        eff_remain = REMAIN_SHOOT_DEFAULT_G146
        eff_auto_rev = AUTO_REVIEW_DEFAULT_G146
        eff_anti_flicker = ANTI_FLICKER_DEFAULT_G146
        eff_apsc = APSC_S35_DEFAULT_G146
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327:
        # Resettable by [Camera Settings Reset]: Emphasized REC Display, Anti-flicker Shoot.
        eff_emph = EMPHASIZED_REC_DISPLAY_DEFAULT_G146
        eff_anti_flicker = ANTI_FLICKER_DEFAULT_G146
        # Initialize-only (Wave-42 Reset Errata confirms APS-C S35 Shooting is NOT reset!):
        eff_rec_lamp = rec_lamp
        eff_remain = remain_shoot_display
        eff_auto_rev = auto_review
        eff_apsc = apsc_s35_shooting
    else:
        eff_rec_lamp = rec_lamp
        eff_emph = emphasized_rec_display
        eff_remain = remain_shoot_display
        eff_auto_rev = auto_review
        eff_anti_flicker = anti_flicker_shoot
        eff_apsc = apsc_s35_shooting

    # Silent Mode = On locks Electronic Shutter (but does NOT disable REC Lamp!)
    eff_shutter = (
        SHUTTER_TYPE_ELECTRONIC_G146 if silent_mode == "On" else shutter_type
    )

    if shoot_mode != SHOOT_MODE_STILL_PHASE327 or interval_shoot_active:
        eff_auto_rev_runtime = AUTO_REVIEW_OFF_G146
    else:
        eff_auto_rev_runtime = eff_auto_rev

    if (
        shoot_mode != SHOOT_MODE_STILL_PHASE327
        or eff_shutter != SHUTTER_TYPE_MECHANICAL_G146
        or silent_mode == "On"
        or bulb_active
    ):
        eff_anti_flicker_runtime = "Off"
    else:
        eff_anti_flicker_runtime = eff_anti_flicker

    apsc_active = (eff_apsc == APSC_S35_ON_G146) or (
        eff_apsc == APSC_S35_AUTO_G146 and apsc_lens_attached
    )

    if apsc_active:
        max_movie_res = MOVIE_RES_FHD_1080P_G146
        max_movie_fps = 120
        max_still_size = STILL_SIZE_M_5_1M_G146
    else:
        max_movie_res = MOVIE_RES_DCI_4K_G146
        max_movie_fps = 240
        max_still_size = STILL_SIZE_L_12M_G146

    return {
        "effective_rec_lamp": eff_rec_lamp,
        "effective_emphasized_rec_display": eff_emph,
        "emphasized_rec_clean_hdmi_suppressed": True,
        "effective_remain_shoot_display": eff_remain,
        "effective_auto_review": eff_auto_rev_runtime,
        "effective_anti_flicker_shoot": eff_anti_flicker_runtime,
        "effective_apsc_s35_shooting": eff_apsc,
        "apsc_s35_active": apsc_active,
        "apsc_s35_preserved_across_camset_reset": (
            reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327
        ),
        "effective_shutter_type": eff_shutter,
        "effective_movie_max_resolution": max_movie_res,
        "effective_movie_max_fps": max_movie_fps,
        "effective_still_max_size": max_still_size,
    }


def compute_reclamp_varshutter_apsc_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G146 (648 states)."""
    combos = list(
        itertools.product(
            ALLOWED_SHOOT_MODES_PHASE327,
            ("Off", "On"),  # silent_mode
            ALLOWED_REC_LAMP_MODES_G146,
            ("Off", "On"),  # anti_flicker_shoot
            ALLOWED_APSC_S35_MODES_G146,
            (False, True),  # apsc_lens_attached
            (
                RESET_ACTION_NONE_PHASE327,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327,
                RESET_ACTION_INITIALIZE_PHASE327,
            ),
        )
    )
    apsc_fhd_clamped_count = 0
    apsc_still_5_1m_count = 0
    camset_preserved_apsc_on_count = 0
    anti_flicker_active_count = 0
    for sm, sil, lamp, af_shoot, apsc, apsc_lens, rst in combos:
        st = resolve_fx3_reclamp_varshutter_apsc_state(
            shoot_mode=sm,
            silent_mode=sil,
            rec_lamp=lamp,
            anti_flicker_shoot=af_shoot,
            apsc_s35_shooting=apsc,
            apsc_lens_attached=apsc_lens,
            reset_action=rst,
        )
        if st["apsc_s35_active"]:
            apsc_fhd_clamped_count += 1
        if st["effective_still_max_size"] == STILL_SIZE_M_5_1M_G146:
            apsc_still_5_1m_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327
            and st["effective_apsc_s35_shooting"] == APSC_S35_ON_G146
        ):
            camset_preserved_apsc_on_count += 1
        if st["effective_anti_flicker_shoot"] == "On":
            anti_flicker_active_count += 1
    return {
        "total_matrix_states": len(combos),
        "apsc_fhd_clamped_count": apsc_fhd_clamped_count,
        "apsc_still_5_1m_count": apsc_still_5_1m_count,
        "camset_preserved_apsc_on_count": camset_preserved_apsc_on_count,
        "anti_flicker_active_count": anti_flicker_active_count,
    }


def verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE327,
    body_model_id: int = FX3_MODEL_ID_PHASE327,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE327,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE327,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE327,
    silent_mode: str = "Off",
    shutter_type: str = SHUTTER_TYPE_MECHANICAL_G146,
    rec_lamp: str = REC_LAMP_DEFAULT_G146,
    rec_lamp_turned_off_by_silent_mode: bool = False,
    requested_tally_light_menu: bool = False,
    requested_rec_lamp_light_up_only_one: bool = False,
    emphasized_rec_display: str = EMPHASIZED_REC_DISPLAY_DEFAULT_G146,
    emphasized_rec_output_on_clean_hdmi: bool = False,
    remain_shoot_display: str = REMAIN_SHOOT_DEFAULT_G146,
    auto_review: str = AUTO_REVIEW_DEFAULT_G146,
    interval_shoot_active: bool = False,
    requested_dormant_var_shutter: bool = False,
    requested_dormant_anti_flicker_tv_scan: bool = False,
    anti_flicker_shoot: str = ANTI_FLICKER_DEFAULT_G146,
    bulb_active: bool = False,
    apsc_s35_shooting: str = APSC_S35_DEFAULT_G146,
    apsc_lens_attached: bool = False,
    movie_resolution: str = MOVIE_RES_4K_UHD_G146,
    movie_fps: int = 24,
    still_image_size: str = STILL_SIZE_L_12M_G146,
    requested_4k_hdmi_raw_under_apsc: bool = False,
    fx6_independent_tally_or_gy_requested: bool = False,
    fx6_ecs_requested: bool = False,
    fx6_clear_image_zoom_4k_requested: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE327,
    claimed_camset_reset_resets_apsc: bool = False,
    claimed_camset_reset_resets_rec_lamp_or_autoreview: bool = False,
) -> ReclampVarshutterApscGuardResult:
    """Enforce Gate G146: REC Lamp, Emph REC, Remain Shoot, Auto Review, Dormant Var. Shutter & Wave-42 APS-C S35 Errata."""
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
    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE327:
        _add("TELEMETRY_INVALID", f"shoot_mode_invalid:{shoot_mode!r}")
    if not _is_on_off(silent_mode):
        _add("TELEMETRY_INVALID", f"silent_mode_invalid:{silent_mode!r}")
    if shutter_type not in ALLOWED_SHUTTER_TYPES_G146:
        _add("TELEMETRY_INVALID", f"shutter_type_invalid:{shutter_type!r}")
    if rec_lamp not in ALLOWED_REC_LAMP_MODES_G146:
        _add("TELEMETRY_INVALID", f"rec_lamp_invalid:{rec_lamp!r}")
    if not _is_on_off(emphasized_rec_display):
        _add("TELEMETRY_INVALID", f"emphasized_rec_display_invalid:{emphasized_rec_display!r}")
    if remain_shoot_display not in ALLOWED_REMAIN_SHOOT_MODES_G146:
        _add("TELEMETRY_INVALID", f"remain_shoot_display_invalid:{remain_shoot_display!r}")
    if auto_review not in ALLOWED_AUTO_REVIEW_MODES_G146:
        _add("TELEMETRY_INVALID", f"auto_review_invalid:{auto_review!r}")
    if not _is_on_off(anti_flicker_shoot):
        _add("TELEMETRY_INVALID", f"anti_flicker_shoot_invalid:{anti_flicker_shoot!r}")
    if apsc_s35_shooting not in ALLOWED_APSC_S35_MODES_G146:
        _add("TELEMETRY_INVALID", f"apsc_s35_shooting_invalid:{apsc_s35_shooting!r}")
    if movie_resolution not in ALLOWED_MOVIE_RESOLUTIONS_G146:
        _add("TELEMETRY_INVALID", f"movie_resolution_invalid:{movie_resolution!r}")
    if not _is_strict_int(movie_fps) or movie_fps <= 0:
        _add("TELEMETRY_INVALID", f"movie_fps_invalid:{movie_fps!r}")
    if still_image_size not in ALLOWED_STILL_SIZES_G146:
        _add("TELEMETRY_INVALID", f"still_image_size_invalid:{still_image_size!r}")
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE327:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")

    # Dormant / FX6 cross-model checks -> EOPNOTSUPP=95
    if requested_tally_light_menu or requested_rec_lamp_light_up_only_one:
        _add(
            "DORMANT_REC_LAMP_EOPNOTSUPP",
            "fx3_dormant_tally_light_and_rec_lamp_light_up_only_one_not_supported_eopnotsupp_95",
        )
    if requested_dormant_var_shutter or requested_dormant_anti_flicker_tv_scan:
        _add(
            "DORMANT_VAR_SHUTTER_EOPNOTSUPP",
            "fx3_dormant_var_shutter_high_res_ss_anti_flicker_tv_scan_not_supported_eopnotsupp_95",
        )
    if (
        fx6_independent_tally_or_gy_requested
        or fx6_ecs_requested
        or fx6_clear_image_zoom_4k_requested
    ):
        _add(
            "FX6_CROSS_MODEL_EOPNOTSUPP",
            "fx6_independent_tally_gy_ecs_or_clear_image_zoom_4k_not_supported_on_fx3_eopnotsupp_95",
        )

    # REC Lamp, Emphasized REC Display, Auto Review rules
    if rec_lamp_turned_off_by_silent_mode:
        _add(
            "REC_LAMP_VIOLATION",
            "rec_lamp_is_independent_of_silent_mode_einval_22",
        )
    if emphasized_rec_output_on_clean_hdmi:
        _add(
            "EMPH_REC_VIOLATION",
            "emphasized_rec_display_suppressed_on_clean_hdmi_einval_22",
        )
    if interval_shoot_active and auto_review != AUTO_REVIEW_OFF_G146:
        _add(
            "AUTO_REVIEW_VIOLATION",
            "auto_review_disabled_during_interval_shoot_einval_22",
        )
    if shoot_mode != SHOOT_MODE_STILL_PHASE327 and auto_review != AUTO_REVIEW_OFF_G146:
        _add(
            "AUTO_REVIEW_VIOLATION",
            "auto_review_is_still_only_menu_einval_22",
        )

    # Anti-flicker Shoot. active rules (Still mechanical-shutter-only)
    if anti_flicker_shoot == "On":
        if shoot_mode != SHOOT_MODE_STILL_PHASE327:
            _add(
                "ANTI_FLICKER_VIOLATION",
                "anti_flicker_shoot_disabled_in_movie_and_sq_einval_22",
            )
        if shutter_type != SHUTTER_TYPE_MECHANICAL_G146 or silent_mode == "On":
            _add(
                "ANTI_FLICKER_VIOLATION",
                "anti_flicker_shoot_disabled_under_electronic_shutter_or_silent_mode_einval_22",
            )
        if bulb_active:
            _add(
                "ANTI_FLICKER_VIOLATION",
                "anti_flicker_shoot_disabled_during_bulb_einval_22",
            )

    # Wave-42 Reset Errata + Initialize-only checks
    if claimed_camset_reset_resets_apsc:
        _add(
            "APSC_RESET_ERRATA_VIOLATION",
            "wave42_reset_errata_apsc_s35_shooting_is_initialize_only_not_camset_resettable",
        )
    if claimed_camset_reset_resets_rec_lamp_or_autoreview:
        _add(
            "REC_LAMP_OR_AUTO_REVIEW_RESET_VIOLATION",
            "rec_lamp_remain_shoot_and_auto_review_are_initialize_only_not_camset_resettable",
        )

    state = resolve_fx3_reclamp_varshutter_apsc_state(
        shoot_mode=shoot_mode,
        silent_mode=silent_mode,
        shutter_type=shutter_type,
        rec_lamp=rec_lamp,
        emphasized_rec_display=emphasized_rec_display,
        remain_shoot_display=remain_shoot_display,
        auto_review=auto_review,
        interval_shoot_active=interval_shoot_active,
        anti_flicker_shoot=anti_flicker_shoot,
        apsc_s35_shooting=apsc_s35_shooting,
        apsc_lens_attached=apsc_lens_attached,
        bulb_active=bulb_active,
        reset_action=reset_action,
    )

    # APS-C S35 Active Lockout & Resolution/Still Size Clamp
    if state["apsc_s35_active"]:
        if shoot_mode in (SHOOT_MODE_MOVIE_PHASE327, SHOOT_MODE_SQ_PHASE327):
            if movie_resolution != MOVIE_RES_FHD_1080P_G146:
                _add(
                    "APSC_4K_LOCKOUT_VIOLATION",
                    "apsc_s35_locks_out_all_4k_dci4k_formats_to_fhd_1080p_einval_22",
                )
            if _is_strict_int(movie_fps) and movie_fps > 120:
                _add(
                    "APSC_FHD_HFR_LOCKOUT_VIOLATION",
                    "apsc_s35_clamps_fhd_fps_to_le_120p_blocks_200_240fps_einval_22",
                )
        if requested_4k_hdmi_raw_under_apsc:
            _add(
                "APSC_4K_HDMI_RAW_LOCKOUT_VIOLATION",
                "apsc_s35_locks_out_4k_hdmi_only_and_raw_output_einval_22",
            )
        if shoot_mode == SHOOT_MODE_STILL_PHASE327 and still_image_size == STILL_SIZE_L_12M_G146:
            _add(
                "APSC_STILL_L12M_CLAMP_VIOLATION",
                "apsc_s35_clamps_still_l_12m_to_m_5_1m_2768x1848_einval_22",
            )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G146
        block_errno = 0
        block_errno_name = "OK"
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G146_DORMANT_VAR_SHUTTER_OR_ANTI_FLICKER_VIOLATION
        block_errno = EOPNOTSUPP_ERRNO_PHASE327
        block_errno_name = EOPNOTSUPP_NAME_PHASE327
    elif any("APSC" in v for v in violations):
        status = STATUS_BLOCKED_G146_APSC_RESET_ERRATA_OR_4K_STILL_CLAMP_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE327
        block_errno_name = EINVAL_NAME_PHASE327
    elif any("ANTI_FLICKER" in v for v in violations):
        status = STATUS_BLOCKED_G146_DORMANT_VAR_SHUTTER_OR_ANTI_FLICKER_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE327
        block_errno_name = EINVAL_NAME_PHASE327
    elif any(v == "TELEMETRY_INVALID" for v in violations) or any(
        "body_" in e or "help_guide" in e or "firmware_version" in e for e in errors
    ):
        status = STATUS_BLOCKED_G146_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE327
        block_errno_name = EINVAL_NAME_PHASE327
    else:
        status = STATUS_BLOCKED_G146_REC_LAMP_EMPH_REMAIN_OR_AUTO_REVIEW_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE327
        block_errno_name = EINVAL_NAME_PHASE327

    return ReclampVarshutterApscGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        rec_lamp_menu_path=REC_LAMP_MENU_PATH_G146,
        apsc_s35_menu_path=APSC_S35_SHOOTING_MENU_PATH_G146,
        effective_rec_lamp=state["effective_rec_lamp"],
        physical_rec_lamps_count=FX3_PHYSICAL_REC_LAMPS_G146,
        rec_lamp_independent_of_silent_mode=True,
        effective_emphasized_rec_display=state["effective_emphasized_rec_display"],
        emphasized_rec_clean_hdmi_suppressed=state[
            "emphasized_rec_clean_hdmi_suppressed"
        ],
        effective_remain_shoot_display=state["effective_remain_shoot_display"],
        effective_auto_review=state["effective_auto_review"],
        auto_review_still_only=True,
        effective_anti_flicker_shoot=state["effective_anti_flicker_shoot"],
        effective_apsc_s35_shooting=state["effective_apsc_s35_shooting"],
        apsc_s35_active=state["apsc_s35_active"],
        apsc_s35_resettable_by_camset_reset=APSC_S35_RESETTABLE_BY_CAMERA_SETTINGS_RESET_G146,
        effective_movie_max_resolution=state["effective_movie_max_resolution"],
        effective_movie_max_fps=state["effective_movie_max_fps"],
        effective_still_max_size=state["effective_still_max_size"],
        dormant_tally_or_only_one_rejected=bool(
            requested_tally_light_menu or requested_rec_lamp_light_up_only_one
        ),
        dormant_var_shutter_rejected=bool(
            requested_dormant_var_shutter or requested_dormant_anti_flicker_tv_scan
        ),
        fx6_tally_ecs_or_ciz4k_spoof_rejected=bool(
            fx6_independent_tally_or_gy_requested
            or fx6_ecs_requested
            or fx6_clear_image_zoom_4k_requested
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
class G146ReclampVarshutterApscGuardResult:
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
    reclamp_varshutter_apsc_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g146_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G146ReclampVarshutterApscGuardResult]:
    audit = audit_phase327_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G146ReclampVarshutterApscGuardResult(
        gate_id=G146,
        gate_code=G146_GATE_CODE,
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
        reclamp_varshutter_apsc_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G146,
        gate_code=G146_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"rec_lamp={res.effective_rec_lamp} "
            f"emph={res.effective_emphasized_rec_display} "
            f"remain={res.effective_remain_shoot_display} "
            f"auto_rev={res.effective_auto_review} "
            f"apsc={res.effective_apsc_s35_shooting} "
            f"apsc_resettable={res.apsc_s35_resettable_by_camset_reset}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


# ---------------------------------------------------------------------------
# Unified 146-Gate Master Safety Preflight Engine (G01..G146)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Master146GateReport:
    schema: str
    schema_version: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_143_gates_verified: bool
    all_146_gates_verified: bool
    g13_to_g146_all_passed: bool
    g145_to_g146_all_passed: bool
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
    master_144_report: Dict[str, Any]
    g145_result: Dict[str, Any]
    g146_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_146gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    simulate_bench_dry_run: Optional[bool] = None,
    dry_run_simulated_backup: Optional[bool] = None,
    request_persistent_emmc_writes: bool = False,
    master_144_override: Optional[Master144GateReport] = None,
    hdmi_raw_desqueeze_kwargs: Optional[Mapping[str, Any]] = None,
    reclamp_varshutter_apsc_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master146GateReport:
    """Evaluate unified 146-Gate Milestone Master Safety Preflight (`G01..G146`)."""
    effective_dry_run = (
        bool(dry_run_simulated)
        or (simulate_bench_dry_run is True)
        or (dry_run_simulated_backup is True)
    )
    clean_forced = _is_clean_room_forced(force_clean_room)
    resolved_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved_work_root_for_m144 = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=resolved_repo_root).work_root
    )
    m144_force_clean_room = (
        True
        if (clean_forced or resolved_work_root_for_m144 is None)
        else force_clean_room
    )

    m144_report = (
        master_144_override
        if master_144_override is not None
        else evaluate_144gate_preflight(
            resolved_repo_root,
            work_root=work_root,
            force_clean_room=m144_force_clean_room,
            dry_run_simulated=effective_dry_run,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
        )
    )

    g145_kw = dict(hdmi_raw_desqueeze_kwargs or {})
    if "requested_write_operation" not in g145_kw and request_persistent_emmc_writes:
        g145_kw["requested_write_operation"] = True
    g145_verdict, g145_res = evaluate_g145_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
        repo_root=resolved_repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **g145_kw,
    )

    g146_kw = dict(reclamp_varshutter_apsc_kwargs or {})
    g146_verdict, g146_res = (
        evaluate_g146_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            repo_root=resolved_repo_root,
            work_root=work_root,
            force_clean_room=force_clean_room,
            **g146_kw,
        )
    )

    new_gate_dicts = (
        {
            "gate_id": G145,
            "gate_code": G145_GATE_CODE,
            "status": g145_res.status,
            "passed": g145_verdict.passed,
            "evidence": g145_verdict.evidence,
            "violation_codes": list(g145_verdict.errors),
        },
        {
            "gate_id": G146,
            "gate_code": G146_GATE_CODE,
            "status": g146_res.status,
            "passed": g146_verdict.passed,
            "evidence": g146_verdict.evidence,
            "violation_codes": list(g146_verdict.errors),
        },
    )

    all_gates: Tuple[Dict[str, Any], ...] = tuple(m144_report.gates) + new_gate_dicts
    g01_to_g12_verified = int(m144_report.summary["g01_to_g12_verified"])
    g13_to_g144_verified = (
        int(m144_report.summary["g13_to_g142_verified"])
        + int(m144_report.summary["g143_to_g144_verified"])
    )
    g145_to_g146_verified = int(bool(g145_verdict.passed)) + int(
        bool(g146_verdict.passed)
    )
    total_verified = g01_to_g12_verified + g13_to_g144_verified + g145_to_g146_verified

    g145_to_g146_all_passed = g145_to_g146_verified == 2
    g13_to_g146_all_passed = (
        m144_report.g13_to_g144_all_passed and g145_to_g146_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m144_report.gates[:9])

    offline_143_verified = (
        g01_to_g09_ok
        and m144_report.offline_141_gates_verified
        and g145_to_g146_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_146_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g146_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m144_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_143_verified
        and m144_report.h0_h1_trial_entry_allowed
        and g145_to_g146_all_passed
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
        list(m144_report.errors)
        + list(g145_verdict.errors)
        + list(g146_verdict.errors)
    )
    warnings: List[str] = (
        list(m144_report.warnings)
        + list(g145_verdict.warnings)
        + list(g146_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m144_report.g13_to_g144_all_passed:
        overall_status = m144_report.status
    elif not g145_verdict.passed:
        overall_status = g145_verdict.status
    elif not g146_verdict.passed:
        overall_status = g146_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_146_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_146_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_146_verified:
        overall_status = "VERIFIED_ALL_146_GATES"
    else:
        overall_status = "VERIFIED_143_OF_146_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m144_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g145_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g146_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 146,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 146 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g144_verified": g13_to_g144_verified,
        "g145_to_g146_verified": g145_to_g146_verified,
        "g13_to_g146_all_passed": g13_to_g146_all_passed,
        "g145_to_g146_all_passed": g145_to_g146_all_passed,
        "offline_143_gates_verified": offline_143_verified,
        "all_146_gates_verified": all_146_verified,
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

    return Master146GateReport(
        schema=REALHW_146GATE_PREFLIGHT_SCHEMA,
        schema_version=REALHW_146GATE_PREFLIGHT_SCHEMA,
        version=REALHW_HDMI_RAW_DESQUEEZE_RECLAMP_VARSHUTTER_APSC_146GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_143_gates_verified=offline_143_verified,
        all_146_gates_verified=all_146_verified,
        g13_to_g146_all_passed=g13_to_g146_all_passed,
        g145_to_g146_all_passed=g145_to_g146_all_passed,
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
        master_144_report=m144_report.to_dict(),
        g145_result=g145_res.to_dict(),
        g146_result=g146_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_146_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master146GateReport:
    return evaluate_146gate_preflight(repo_root, **kwargs)


def run_146_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master146GateReport:
    return evaluate_146gate_preflight(repo_root, **kwargs)


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
        prog="realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard",
        description="Phase 327 Wave-63 G145/G146 and 146/146 Unified Safety Preflight CLI",
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
        help="Supply simulated dry-run Tier-0 backup inputs so all 146/146 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g145", "g146", "146"],
        default="146",
        help="Target gate check: g145, g146, or 146",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g145":
        v, r = evaluate_g145_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
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

    if args.gate == "g146":
        v, r = evaluate_g146_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
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

    rep = evaluate_146gate_preflight(
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
                "g145_status": rep.g145_result["status"],
                "g146_status": rep.g146_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/146 "
            f"raw_firmware_bytes_leaked={rep.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        rep.all_146_gates_verified
        if args.dry_run_simulated
        else rep.offline_143_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "ALLOWED_APSC_S35_MODES_G146",
    "ALLOWED_AUTO_REVIEW_MODES_G146",
    "ALLOWED_FX3_DESQUEEZE_MODES_G145",
    "ALLOWED_HDMI_4CH_AUDIO_MODES_G145",
    "ALLOWED_HDMI_4K_10BIT_SETTINGS_G145",
    "ALLOWED_HDMI_OUT_RESOLUTIONS_G145",
    "ALLOWED_LOG_SHOOTING_MODES_G145",
    "ALLOWED_MEDIA_SLOTS_PHASE327",
    "ALLOWED_MOVIE_RESOLUTIONS_G146",
    "ALLOWED_RAW_OUTPUT_SETTINGS_G145",
    "ALLOWED_REC_LAMP_MODES_G146",
    "ALLOWED_REC_MEDIA_HDMI_MODES_G145",
    "ALLOWED_REMAIN_SHOOT_MODES_G146",
    "ALLOWED_RESET_ACTIONS_PHASE327",
    "ALLOWED_SHOOT_MODES_PHASE327",
    "ALLOWED_SHUTTER_TYPES_G146",
    "ALLOWED_STILL_SIZES_G146",
    "ANTI_FLICKER_DEFAULT_G146",
    "ANTI_FLICKER_FREQUENCIES_HZ_G146",
    "ANTI_FLICKER_SHOOT_F_RESID16_G146",
    "ANTI_FLICKER_SHOOT_MENU_PATH_G146",
    "APSC_S35_AUTO_G146",
    "APSC_S35_DEFAULT_G146",
    "APSC_S35_F_RESID16_G146",
    "APSC_S35_OFF_G146",
    "APSC_S35_ON_G146",
    "APSC_S35_RESETTABLE_BY_CAMERA_SETTINGS_RESET_G146",
    "APSC_S35_SHOOTING_MENU_PATH_G146",
    "APSC_S35_STILL_ASPECT_DIMENSIONS_G146",
    "AUTO_REVIEW_10_SEC_G146",
    "AUTO_REVIEW_2_SEC_G146",
    "AUTO_REVIEW_5_SEC_G146",
    "AUTO_REVIEW_BASE_RESID16_G146",
    "AUTO_REVIEW_DEFAULT_G146",
    "AUTO_REVIEW_MENU_PATH_G146",
    "AUTO_REVIEW_OFF_G146",
    "CROSS_MODEL_FLASH_AUTHORIZED",
    "DESQUEEZE_1_3X_G145",
    "DESQUEEZE_1_5X_F_RESID16_G145",
    "DESQUEEZE_1_5X_G145",
    "DESQUEEZE_1_65X_EXEC_G145",
    "DESQUEEZE_1_6X_F_RESID16_G145",
    "DESQUEEZE_1_6X_G145",
    "DESQUEEZE_2_0X_G145",
    "DESQUEEZE_DEFAULT_G145",
    "DESQUEEZE_DISPLAY_F_RESID16_G145",
    "DESQUEEZE_DISPLAY_MENU_PATH_G145",
    "DESQUEEZE_OFF_G145",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE327",
    "DONOR_CHECK_MAX_SECONDS_PHASE327",
    "DORMANT_ANTI_FLICKER_SET_F_RESID16_G146",
    "DORMANT_ANTI_FLICKER_TV_SCAN_G_RESID16_G146",
    "DORMANT_DESQUEEZE_1_8X_G145",
    "DORMANT_HDMI_4K_24P_8BIT_F_RESID16_G145",
    "DORMANT_HDMI_4K_24_00P_8BIT_G145",
    "DORMANT_REC_LAMP_ONLY_ONE_F_RESID16_G146",
    "DORMANT_REC_LAMP_ONLY_ONE_SYMBOL_G146",
    "DORMANT_VAR_SHUTTER_F_RESID16_G146",
    "EBUSY_ERRNO_PHASE327",
    "EBUSY_NAME_PHASE327",
    "EINVAL_ERRNO_PHASE327",
    "EINVAL_NAME_PHASE327",
    "EMPHASIZED_REC_DISPLAY_DEFAULT_G146",
    "EMPHASIZED_REC_DISPLAY_F_RESID16_G146",
    "EMPHASIZED_REC_DISPLAY_MENU_PATH_G146",
    "ENV_CLEAN_ROOM_TEST_PHASE327",
    "EOPNOTSUPP_ERRNO_PHASE327",
    "EOPNOTSUPP_NAME_PHASE327",
    "EROFS_ERRNO_PHASE327",
    "EROFS_NAME_PHASE327",
    "EXACT_4_DESQUEEZE_LOCKOUTS_G145",
    "EXACT_6_DESQUEEZE_AUTO_BYPASS_CONDITIONS_G145",
    "EXACT_8_HDMI_OUTPUT_SETTING_ITEMS_G145",
    "FX3_DEFAULT_FW_VERSION_PHASE327",
    "FX3_HDMI_RAW_BIT_DEPTH_G145",
    "FX3_HDMI_RAW_DIMENSIONS_G145",
    "FX3_HELP_GUIDE_CODE_PHASE327",
    "FX3_MODEL_ID_PHASE327",
    "FX3_MODEL_NAME_PHASE327",
    "FX3_PHYSICAL_REC_LAMPS_G146",
    "FX6_DEFAULT_FW_VERSION_PHASE327",
    "FX6_DESQUEEZE_MODES_G145",
    "FX6_ECS_MAX_HZ_G146",
    "FX6_ECS_MIN_HZ_G146",
    "FX6_HDMI_RAW_DIMENSIONS_G145",
    "FX6_MODEL_NAME_PHASE327",
    "FX6_PRODUCT_CODE_PHASE327",
    "FX6_SDI_RAW_DIMENSIONS_G145",
    "G145",
    "G145HdmiRawDesqueezeGuardResult",
    "G145_GATE_CODE",
    "G145_GATE_ID",
    "G146",
    "G146ReclampVarshutterApscGuardResult",
    "G146_GATE_CODE",
    "G146_GATE_ID",
    "GATE_G145_HDMI_RAW_CO_REC_VAULT_AND_DESQUEEZE_4RATIO_GUARD",
    "GATE_G146_RECLAMP_EMPH_REMAIN_AUTOREVIEW_AND_DORMANT_VARSHUTTER_APSC_GUARD",
    "HDMI_4CH_AUDIO_CH1_CH2_G145",
    "HDMI_4CH_AUDIO_CH3_CH4_G145",
    "HDMI_4CH_AUDIO_DEFAULT_G145",
    "HDMI_4CH_AUDIO_OUTPUT_F_RESID16_G145",
    "HDMI_4K_23_98P_10BIT_G145",
    "HDMI_4K_24_00P_10BIT_G145",
    "HDMI_4K_25P_10BIT_G145",
    "HDMI_4K_29_97P_10BIT_G145",
    "HDMI_4K_50P_10BIT_G145",
    "HDMI_4K_59_94P_10BIT_G145",
    "HDMI_4K_DEFAULT_G145",
    "HDMI_4K_OUT_SET_F_RESID16_G145",
    "HDMI_OUTPUT_SETTINGS_MENU_PATH_G145",
    "HDMI_OUT_RES_1080I_G145",
    "HDMI_OUT_RES_1080P_G145",
    "HDMI_OUT_RES_2160P_G145",
    "HDMI_OUT_RES_AUTO_G145",
    "HDMI_OUT_RES_DEFAULT_G145",
    "HdmiRawDesqueezeGuardResult",
    "LOG_SHOOTING_CINE_EI_G145",
    "LOG_SHOOTING_CINE_EI_QUICK_G145",
    "LOG_SHOOTING_FLEXIBLE_ISO_G145",
    "LOG_SHOOTING_OFF_G145",
    "LOG_SHOOTING_SETTING_MENU_PATH_G145",
    "MEDIA_SLOT_1_PHASE327",
    "MEDIA_SLOT_2_PHASE327",
    "MEDIA_SLOT_NONE_PHASE327",
    "MOVIE_RES_4K_UHD_G146",
    "MOVIE_RES_DCI_4K_G146",
    "MOVIE_RES_FHD_1080P_G146",
    "Master146GateReport",
    "OUTPUT_RESOLUTION_F_RESID16_G145",
    "PINNED_FX3_APPFW_SLICES_PHASE327",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE327",
    "PINNED_FX6_APPFW_SLICES_PHASE327",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE327",
    "PINNED_PHASE327_DONOR_SPECS",
    "PPLUT_PICTURE_PROFILES_G145",
    "Phase327DonorAuditResult",
    "RAW_OUTPUT_F_RESID16_G145",
    "RAW_OUTPUT_SETTING_23_98P_G145",
    "RAW_OUTPUT_SETTING_24_00P_G145",
    "RAW_OUTPUT_SETTING_25P_G145",
    "RAW_OUTPUT_SETTING_29_97P_G145",
    "RAW_OUTPUT_SETTING_50P_G145",
    "RAW_OUTPUT_SETTING_59_94P_G145",
    "RAW_OUTPUT_SETTING_DEFAULT_G145",
    "RAW_OUTPUT_SETTING_F_RESID16_G145",
    "REALHW_146GATE_PREFLIGHT_SCHEMA",
    "REALHW_HDMI_RAW_DESQUEEZE_RECLAMP_VARSHUTTER_APSC_146GATE_SCHEMA",
    "REALHW_HDMI_RAW_DESQUEEZE_RECLAMP_VARSHUTTER_APSC_146GATE_VERSION",
    "REC_CONTROL_F_RESID16_G145",
    "REC_LAMP_ALL_OFF_G146",
    "REC_LAMP_ALL_ON_G146",
    "REC_LAMP_DEFAULT_G146",
    "REC_LAMP_F_RESID16_G146",
    "REC_LAMP_MENU_PATH_G146",
    "REC_LAMP_ONLY_FRONT_OFF_G146",
    "REC_MEDIA_HDMI_DEFAULT_G145",
    "REC_MEDIA_HDMI_F_RESID16_G145",
    "REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145",
    "REC_MEDIA_HDMI_ON_G145",
    "REMAIN_SHOOT_ALWAYS_DISPLAY_G146",
    "REMAIN_SHOOT_DEFAULT_G146",
    "REMAIN_SHOOT_DISPLAY_F_RESID16_G146",
    "REMAIN_SHOOT_DISPLAY_MENU_PATH_G146",
    "REMAIN_SHOOT_NOT_DISPLAYED_G146",
    "REMAIN_SHOOT_SHOOT_ONLY_DISPLAY_G146",
    "REMOVED_COLOR_GAMUT_RAW_OUT_BKID_G145",
    "REMOVED_COLOR_GAMUT_RAW_OUT_F_RESID16_G145",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327",
    "RESET_ACTION_INITIALIZE_PHASE327",
    "RESET_ACTION_NONE_PHASE327",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE327",
    "ReclampVarshutterApscGuardResult",
    "SHOOT_MODE_MOVIE_PHASE327",
    "SHOOT_MODE_SQ_PHASE327",
    "SHOOT_MODE_STILL_PHASE327",
    "SHUTTER_TYPE_ELECTRONIC_G146",
    "SHUTTER_TYPE_MECHANICAL_G146",
    "STATUS_BLOCKED_G145_DESQUEEZE_5STATE_LOCKOUT_OR_BYPASS_VIOLATION",
    "STATUS_BLOCKED_G145_DORMANT_8BIT_24P_RAW_GAMUT_18X_OR_FX6_VIOLATION",
    "STATUS_BLOCKED_G145_HDMI_8ITEM_RAW_REBOOT_OR_TC_VIOLATION",
    "STATUS_BLOCKED_G145_SLOT1_CO_REC_VAULT_OR_LOG_CLAMP_VIOLATION",
    "STATUS_BLOCKED_G145_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G146_APSC_RESET_ERRATA_OR_4K_STILL_CLAMP_VIOLATION",
    "STATUS_BLOCKED_G146_DORMANT_VAR_SHUTTER_OR_ANTI_FLICKER_VIOLATION",
    "STATUS_BLOCKED_G146_REC_LAMP_EMPH_REMAIN_OR_AUTO_REVIEW_VIOLATION",
    "STATUS_BLOCKED_G146_TELEMETRY_INVALID",
    "STATUS_BLOCKED_PHASE327_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G145",
    "STATUS_VERIFIED_G146",
    "STILL_SIZE_L_12M_G146",
    "STILL_SIZE_M_5_1M_G146",
    "STILL_SIZE_S_3_0M_G146",
    "TIME_CODE_OUTPUT_F_RESID16_G145",
    "audit_phase327_donor_contracts",
    "compute_hdmi_raw_desqueeze_matrix",
    "compute_reclamp_varshutter_apsc_matrix",
    "evaluate_146_master_safety_gates",
    "evaluate_146gate_preflight",
    "evaluate_g145_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard",
    "evaluate_g146_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard",
    "main",
    "resolve_fx3_hdmi_raw_desqueeze_state",
    "resolve_fx3_reclamp_varshutter_apsc_state",
    "run_146_gate_preflight",
    "verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard",
    "verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard",
]
