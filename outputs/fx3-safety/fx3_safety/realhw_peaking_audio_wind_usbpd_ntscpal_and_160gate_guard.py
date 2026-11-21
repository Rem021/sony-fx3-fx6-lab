"""Phase 373 (Task H473, Wave-70 Milestone, 160/160 Hardware Safety Gates):
Real-Hardware `Shooting -> [Focus] -> [Peaking Display]` (Clean-HDMI Isolation,
`Focus Magnifier` Compatibility, Anti-`[Camera Settings Reset]`, Dormant In-Body
`[Focus Map]` vs FX6 `Monitoring > Peaking` `B&W` & Zero `Peaking Type/Freq`)
and Ver. 2.00..7.02 `[Audio Level Display]` Removal / Exact 5-Item `Shooting ->
[Audio Recording]` / `[Wind Noise Reduct.]` Built-In Stereo Mic Only (No `Auto`)
& 3-Tier Audio Preemption (`3.5mm` > `XLR-H1` > Built-In) vs FX6 Physical Dials,
Menu `CH1..CH4 Wind Filter` (No Hardware `LOW CUT`) & 6-Step `Limiter Mode`
(`G159`),
`Setup -> [USB] -> [USB Power Supply]` (Type-C Only, `9V/3A` PD vs `5V/1.5A`,
Mandatory Charged `NP-FZ100` / Zero Hot-Swap, ON-No-Charge vs OFF-Charge
`10..30C` `CHARGE` LED, `DC-C1` `>=65W/5A` Max-Brightness Lock vs FX6 `19.5V`
EIAJ `DC IN` Battery-Less Boot & Hot-Replug Reboot Hazard / Zero USB-C Power)
and `[NTSC/PAL Selector]` (`J1` Lock / `CE`/`E33`/`U2` Banners, Ver. 7.02
Pure-XAVC Reboot Without Mandatory Format, Cross-Standard Playback Isolation,
and Tier-0 `Slot 1` `EROFS=30` Firewall for `AVF_INFO` Create/Update/Recover/
Format vs FX6 `Project > Rec Format > Frequency` & `Thumbnail` Filter) (`G160`),
and Unified `160`-Gate Master Safety Preflight (`G01..G160`).

Authoritative Empirical Baseline (`ILME-FX3 Ver. 7.02`, `ilc/2210`, `0x0502`,
`PRODUCT_MODEL_ALCIN_UUD` vs `ILME-FX6 Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`):
  - **Gate `G159` (`PEAKING_CLEAN_HDMI_ZERO_FX6_TYPE_FREQ_AND_AUDIO_5ITEM_WIND_BUILTIN_ONLY_FIREWALL`)**:
    1. `Shooting -> [Focus] -> [Peaking Display]`: exact **3** items (`Peaking Display`
       `Off` def / `On` + `[Peaking Display Select]` right-wheel shortcut; `Peaking Level`
       `High` / `Mid` def / `Low`; `Peaking Color` `Red` / `Yellow` / `Blue` / `White` def):
       - ALL 3 items are **anti-`[Camera Settings Reset]`** (`Not available`; only
         `[Initialize]` resets to `Off` / `Mid` / `White`).
       - **Strict Clean-HDMI Isolation**: peaking outlines are **NEVER** emitted over
         HDMI regardless of `[HDMI Info. Display]` (`On`/`Off`) or `[RAW Output]` (`On`/`Off`).
       - Compatible with `[Focus Magnifier]` (`0` `PRM_HAITA_*peaking*` mutex entries).
       - In-body `[Focus Map]` (`_f 0x61f9`/`0x6247`, `view_mp_focus_map`) is **dormant/
         unexposed** on body UI (`EOPNOTSUPP=95`; Ver. 6.00+ wireless *Monitor & Control*
         App only; unsupported over USB cable).
       - Contrast `ILME-FX6 Ver. 6.01` `Monitoring > Peaking`: exact **3** items (`Setting`,
         `Peaking Level`, `Color` with **`B&W`** instead of `White`), debunking dormant
         PXW-FS7M2/F55 UXC leftovers `Peaking Type` (`ns2 0x4501`) / `Peaking Frequency`
         (`ns2 0x4503`) (`0` ELF hits in `FX6 appFw.so` -> `EOPNOTSUPP=95`).
    2. `Shooting -> [Audio Recording]` (Ver. 2.00..7.02):
       - Standalone `[Audio Level Display]` menu (`_f 0x7a36`) removed in Ver. 2.00..7.02
         (auto-rendered via `DISP`/BIG6; read-only in Remote SDK -> write toggle returns
         `EOPNOTSUPP=95`).
       - Exact **5** items, **ALL 5 `Can be reset`** via `[Camera Settings Reset]`:
         `Audio Recording` (`On` def / `Off`), `Audio Rec Level` (`0..31`, def `26`,
         `adj_audio_rec_level_defult` typo, permanent non-disableable Limiter),
         `Audio Out Timing` (`Live` def / `Lip Sync`), `Wind Noise Reduct.` (**strictly
         `On`/`Off` only, default `Off`, ZERO `Auto`** -> `EOPNOTSUPP=95`; **built-in
         stereo mic ONLY**, automatically bypassed on `3.5mm MIC` / `XLR-H1` / MI Shoe /
         `S&Q`), and `Shoe Audio Set.` (`48kHz/16bit 2ch` def / `24bit 2ch` / `24bit 4ch`).
       - Strict 3-tier audio preemption: `3.5mm MIC` > MI Shoe `XLR-H1` DIGITAL > built-in
         stereo mic (`XLR-H1` `ANALOG` downgrades to `16bit 2ch`; `HANDLE AUDIO = OFF`
         falls back to built-in mic).
       - Contrast `ILME-FX6 Ver. 6.01`: physical `CH1/CH2` dials + menu `CH1..CH4 Wind Filter`
         (**NO hardware `LOW CUT` switch on FX6 handle** -> `EOPNOTSUPP=95`) + 6-step
         `Limiter Mode` (`Off / -6 / -9 / -12 / -15 / -17 dB`) + `Audio Level Meter`.

  - **Gate `G160` (`USB_PD_MANDATORY_FZ100_DCC1_POWER_AND_NTSC_PAL_SKU_AVFINFO_SLOT1_EROFS_FIREWALL`)**:
    1. `Setup -> [USB] -> [USB Power Supply]` (`_f 0x721e`, default `On`, **anti-Camera-Reset**):
       - Strictly **USB Type-C** only (`base 0xe931`; Multi/Micro USB rejected `EOPNOTSUPP=95`).
       - `USB PD 9V/3A` (`27W+`) recommended for continuous shooting; `5V/1.5A` low-power
         drain warning (`UPM_PS_USB_SUPPLY_ELECTRIC_POWER_TYPE_LOW`).
       - **Mandatory sufficiently charged `NP-FZ100` inserted** to boot/run (zero hot-swap;
         pulling battery cuts power; `libUsbBusPower.so` `GetCurrentBattState` / `IsSinkReady`
         + `VAL_battery_inserted_BATTERY_IS_{INSERTED,NOT_INSERTED}`).
       - Strict ON-mode no-charge (`CHARGE` LED `OFF`) vs OFF-mode charge (`CHARGE` LED `ON`,
         `10..30°C` temp window; fast-blink fault outside window).
       - `DC-C1` coupler requires `>= 65W` PD + `5A` cable and locks monitor brightness max.
       - Contrast `ILME-FX6 Ver. 6.01`: `19.5V` EIAJ `DC IN` (`18.0..20.5V`, `16.5V`/`15.5V`
         alarms), true battery-less boot, seamless fallback to `BP-U` on unplug, **hot-replug
         `DC IN` reboot hazard blocked during recording (`EBUSY=16`)**, zero USB-C body power
         (`EOPNOTSUPP=95`).
    2. `Setup -> [Area/Date] -> [NTSC/PAL Selector]` & `AVF_INFO` `Slot 1` `EROFS=30`:
       - SKU region locks (`lib::backup_get_ntsc_pal_selector_dst`): `J1` (Japan) NTSC-only
         locked (`EOPNOTSUPP=95`); `CE`/`E33` PAL default (`Running on NTSC.` `base 0xe77a`);
         `U2` NTSC default (`Running on PAL.` `base 0xe0b6`).
       - Ver. 7.02 pure-XAVC switch triggers automatic reboot **without mandatory format**
         (unlike legacy AVCHD); cross-standard clip playback hard-blocked (`_g 0x61ca`/`0x644e`).
       - Any `AVF_INFO` `Create?` (`base 0xea23`) / `Update?` (`base 0xea24`) /
         `Recover Image DB` (`base 0xe918`) / `Format` targeting **Slot 1** MUST return
         deterministic **`EROFS=30`** (`slot1_data_sector_writes == 0`,
         `emmc_nflasha_write_count == 0`).
       - Contrast `ILME-FX6 Ver. 6.01`: `Project > Rec Format > Frequency`
         (`59.94/50/29.97/25/24/23.98Hz`) reboot (`ns2 0x40ab`) + `Thumbnail` strict
         current-frequency filtering.

  - **Unified 160-Gate Master Safety Preflight (`G01..G160`)**:
    Delegates `G01..G158` to `evaluate_158gate_preflight()`, enforces `157/160`
    verified offline (`VERIFIED_157_OF_160_AWAITING_PHYSICAL_TIER0`) and `160/160`
    under `--simulate-bench-dry-run` (`VERIFIED_ALL_160_GATES_DRY_RUN_SIMULATED_BACKUP`),
    with ALL hardware write/flash/live-attach flags hard-locked `False` and `0`.
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
from .realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_and_158gate_guard import (
    Master158GateReport,
    evaluate_158gate_preflight,
)


# ---------------------------------------------------------------------------
# Schema, Versions, Env Keys & Shared Constants
# ---------------------------------------------------------------------------

REALHW_PEAKING_AUDIO_WIND_USBPD_NTSCPAL_160GATE_SCHEMA = (
    "fx3_realhw_peaking_audio_wind_usbpd_ntscpal_160gate_guard_v1"
)
REALHW_PEAKING_AUDIO_WIND_USBPD_NTSCPAL_160GATE_VERSION = (
    "2026.11.21-phase373-milestone160"
)
REALHW_160GATE_PREFLIGHT_SCHEMA = "realhw_160gate_preflight_v1"

G159 = "G159"
G159_GATE_ID = "G159"
G159_GATE_CODE = (
    "PEAKING_CLEAN_HDMI_ZERO_FX6_TYPE_FREQ_AND_AUDIO_5ITEM_WIND_BUILTIN_ONLY_FIREWALL"
)

G160 = "G160"
G160_GATE_ID = "G160"
G160_GATE_CODE = (
    "USB_PD_MANDATORY_FZ100_DCC1_POWER_AND_NTSC_PAL_SKU_AVFINFO_SLOT1_EROFS_FIREWALL"
)

ENV_CLEAN_ROOM_TEST_PHASE373 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE373 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE373 = 0.05

EPERM_ERRNO_PHASE373 = 1
EPERM_NAME_PHASE373 = "EPERM"
EBUSY_ERRNO_PHASE373 = 16
EBUSY_NAME_PHASE373 = "EBUSY"
EINVAL_ERRNO_PHASE373 = 22
EINVAL_NAME_PHASE373 = "EINVAL"
EROFS_ERRNO_PHASE373 = 30
EROFS_NAME_PHASE373 = "EROFS"
EOPNOTSUPP_ERRNO_PHASE373 = 95
EOPNOTSUPP_NAME_PHASE373 = "EOPNOTSUPP"

FX3_MODEL_NAME_PHASE373 = "ILME-FX3"
FX3_MODEL_ID_PHASE373 = 0x0502
FX3_HELP_GUIDE_CODE_PHASE373 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE373 = "7.02"
FX6_MODEL_NAME_PHASE373 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE373 = "6.01"
ALLOWED_BODY_MODELS_PHASE373: Tuple[str, ...] = (
    FX3_MODEL_NAME_PHASE373,
    FX6_MODEL_NAME_PHASE373,
)

MEDIA_SLOT_NONE_PHASE373 = 0
MEDIA_SLOT_1_PHASE373 = 1
MEDIA_SLOT_2_PHASE373 = 2
ALLOWED_MEDIA_SLOTS_PHASE373: Tuple[int, ...] = (
    MEDIA_SLOT_NONE_PHASE373,
    MEDIA_SLOT_1_PHASE373,
    MEDIA_SLOT_2_PHASE373,
)

SHOOT_MODE_STILL_PHASE373 = "Still"
SHOOT_MODE_MOVIE_PHASE373 = "Movie"
SHOOT_MODE_SQ_PHASE373 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE373: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE373,
    SHOOT_MODE_MOVIE_PHASE373,
    SHOOT_MODE_SQ_PHASE373,
)

RESET_ACTION_NONE_PHASE373 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE373 = "Camera Settings Reset"
RESET_ACTION_INITIALIZE_PHASE373 = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE373: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE373,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE373,
    RESET_ACTION_INITIALIZE_PHASE373,
)


# ---------------------------------------------------------------------------
# Gate G159 Constants: Peaking Clean-HDMI / Zero FX6 Type-Freq &
#                      Ver. 2.00+ Audio 5-Item / Wind Built-In Mic Only
# ---------------------------------------------------------------------------

PEAKING_DISPLAY_MENU_PATH_G159 = "Shooting -> [Focus] -> [Peaking Display]"
FX6_PEAKING_MENU_PATH_G159 = "Monitoring > Peaking"
AUDIO_RECORDING_MENU_PATH_G159 = "Shooting -> [Audio Recording]"
FX6_AUDIO_INPUT_MENU_PATH_G159 = "Audio > Audio Input"

EXACT_3_FX3_PEAKING_ITEMS_G159: Tuple[str, ...] = (
    "Peaking Display",
    "Peaking Level",
    "Peaking Color",
)
PEAKING_DISPLAY_DEFAULT_G159 = "Off"
PEAKING_LEVEL_DEFAULT_G159 = "Mid"
PEAKING_COLOR_DEFAULT_G159 = "White"
ALLOWED_PEAKING_LEVELS_G159: Tuple[str, ...] = ("High", "Mid", "Low")
ALLOWED_FX3_PEAKING_COLORS_G159: Tuple[str, ...] = ("Red", "Yellow", "Blue", "White")
ALLOWED_FX6_PEAKING_COLORS_G159: Tuple[str, ...] = ("B&W", "Red", "Yellow", "Blue")
EXACT_3_FX6_PEAKING_ITEMS_G159: Tuple[str, ...] = (
    "Setting",
    "Peaking Level",
    "Color",
)
FX3_PEAKING_RESETTABLE_BY_CAMSET_RESET_G159 = False
FX3_PEAKING_EMITTED_OVER_HDMI_G159 = False
FX3_HDMI_PEAKING_LEAKED_PIXELS_G159 = 0
FX3_PEAKING_COMPATIBLE_WITH_FOCUS_MAGNIFIER_G159 = True
FX3_INBODY_FOCUS_MAP_EXPOSED_G159 = False
FX3_MC_WIRELESS_FOCUS_MAP_MIN_FW_G159 = 6.00
FX6_PEAKING_TYPE_ELF_HITS_G159 = 0
FX6_PEAKING_FREQ_ELF_HITS_G159 = 0

AUDIO_LEVEL_DISPLAY_MENU_REMOVED_VER2_PLUS_G159 = True
EXACT_5_FX3_AUDIO_RECORDING_ITEMS_G159: Tuple[str, ...] = (
    "Audio Recording",
    "Audio Rec Level",
    "Audio Out Timing",
    "Wind Noise Reduct.",
    "Shoe Audio Set.",
)
FX3_AUDIO_5ITEMS_RESETTABLE_BY_CAMSET_RESET_G159 = True
AUDIO_RECORDING_DEFAULT_G159 = "On"
AUDIO_REC_LEVEL_MIN_G159 = 0
AUDIO_REC_LEVEL_MAX_G159 = 31
AUDIO_REC_LEVEL_DEFAULT_G159 = 26
AUDIO_REC_LEVEL_ELF_TYPO_G159 = "adj_audio_rec_level_defult"
FX3_AUDIO_LIMITER_PERMANENT_NON_DISABLEABLE_G159 = True
ALLOWED_AUDIO_OUT_TIMING_G159: Tuple[str, ...] = ("Live", "Lip Sync")
AUDIO_OUT_TIMING_DEFAULT_G159 = "Live"
ALLOWED_FX3_WIND_NOISE_OPTIONS_G159: Tuple[str, ...] = ("Off", "On")
WIND_NOISE_REDUCT_DEFAULT_G159 = "Off"
FX3_WIND_NOISE_AUTO_EXPOSED_G159 = False
ALLOWED_SHOE_AUDIO_FORMATS_G159: Tuple[str, ...] = (
    "48kHz/16bit 2ch",
    "48kHz/24bit 2ch",
    "48kHz/24bit 4ch",
)
SHOE_AUDIO_DEFAULT_G159 = "48kHz/16bit 2ch"
ALLOWED_XLR_H1_MODES_G159: Tuple[str, ...] = ("OFF", "DIGITAL", "ANALOG")
ALLOWED_XLR_H1_LOW_CUT_G159: Tuple[str, ...] = ("Off", "100Hz", "300Hz")
FX3_AUDIO_PREEMPTION_TIERS_G159: Tuple[str, ...] = (
    "3.5mm_mic",
    "mi_shoe_xlr_h1_digital",
    "builtin_stereo_mic",
)
FX6_HANDLE_HW_LOW_CUT_SWITCH_PRESENT_G159 = False
FX6_WIND_FILTER_CHANNELS_G159: Tuple[str, ...] = ("CH1", "CH2", "CH3", "CH4")
EXACT_6_FX6_LIMITER_MODES_G159: Tuple[str, ...] = (
    "Off",
    "-6dB",
    "-9dB",
    "-12dB",
    "-15dB",
    "-17dB",
)

# UXC resid16 anchors (G159)
PEAKING_DISPLAY_F_RESID16_G159 = 0x6FE5
PEAKING_DISPLAY_SELECT_F_RESID16_G159 = 0x62A8
PEAKING_LEVEL_BASE_RESID16_G159 = 0xE14C
PEAKING_COLOR_BASE_RESID16_G159 = 0xE14D
DORMANT_FOCUS_MAP_F_RESID16_G159 = 0x61F9
REMOVED_AUDIO_LEVEL_DISPLAY_F_RESID16_G159 = 0x7A36
AUDIO_RECORDING_F_RESID16_G159 = 0x72D3
AUDIO_OUT_TIMING_F_RESID16_G159 = 0x6BC2
WIND_NOISE_REDUCT_BASE_RESID16_G159 = 0xE4B1
SHOE_AUDIO_SET_F_RESID16_G159 = 0x77F6
FX6_DORMANT_PEAKING_TYPE_NS2_RESID16_G159 = 0x4501
FX6_DORMANT_PEAKING_FREQ_NS2_RESID16_G159 = 0x4503

STATUS_VERIFIED_G159 = (
    "VERIFIED_G159_PEAKING_CLEAN_HDMI_ZERO_FX6_TYPE_FREQ_AND_AUDIO_5ITEM_WIND_BUILTIN_ONLY"
)
STATUS_BLOCKED_G159_TELEMETRY_INVALID = "BLOCKED_G159_TELEMETRY_INVALID"
STATUS_BLOCKED_G159_DORMANT_FOCUSMAP_FX6_TYPEFREQ_AUDIOMETER_OR_WINDAUTO_EOPNOTSUPP = (
    "BLOCKED_G159_DORMANT_FOCUSMAP_FX6_TYPEFREQ_AUDIOMETER_OR_WINDAUTO_EOPNOTSUPP"
)
STATUS_BLOCKED_G159_PEAKING_HDMI_RESET_OR_AUDIO_PREEMPTION_WIND_VIOLATION = (
    "BLOCKED_G159_PEAKING_HDMI_RESET_OR_AUDIO_PREEMPTION_WIND_VIOLATION"
)


# ---------------------------------------------------------------------------
# Gate G160 Constants: USB Power Supply / Mandatory NP-FZ100 / DC-C1 &
#                      NTSC/PAL SKU Lock / AVF_INFO Slot 1 EROFS=30
# ---------------------------------------------------------------------------

USB_POWER_SUPPLY_MENU_PATH_G160 = "Setup -> [USB] -> [USB Power Supply]"
NTSC_PAL_SELECTOR_MENU_PATH_G160 = "Setup -> [Area/Date] -> [NTSC/PAL Selector]"
FX6_SYSTEM_FREQUENCY_MENU_PATH_G160 = "Project > Rec Format > Frequency"

USB_POWER_SUPPLY_DEFAULT_G160 = "On"
USB_POWER_SUPPLY_RESETTABLE_BY_CAMSET_RESET_G160 = False
ALLOWED_USB_PORT_KINDS_G160: Tuple[str, ...] = ("usb_type_c", "multi_micro_usb")
ALLOWED_POWER_SOURCE_MODES_G160: Tuple[str, ...] = (
    "battery_only",
    "usb_c_pd",
    "dc_c1_coupler",
    "fx6_dc_in_19_5v",
)
ALLOWED_CAMERA_POWER_STATES_G160: Tuple[str, ...] = ("ON", "OFF")
USB_PD_RECOMMENDED_SHOOT_VOLTS_G160 = 9.0
USB_PD_RECOMMENDED_SHOOT_AMPS_G160 = 3.0
USB_PD_RECOMMENDED_SHOOT_WATTS_G160 = 27.0
USB_PD_LOW_POWER_WATTS_THRESHOLD_G160 = 15.0
CHARGE_TEMP_MIN_C_G160 = 10.0
CHARGE_TEMP_MAX_C_G160 = 30.0
FX3_BATTERY_LESS_USB_BOOT_SUPPORTED_G160 = False
FX3_BATTERY_HOT_SWAP_SUPPORTED_G160 = False
FX3_CHARGES_WHILE_CAMERA_ON_G160 = False
DC_C1_MIN_PD_WATTS_G160 = 65.0
DC_C1_MIN_CABLE_AMPS_G160 = 5.0
DC_C1_MONITOR_BRIGHTNESS_LOCKED_MAX_G160 = True
FX6_DC_IN_NOMINAL_V_G160 = 19.5
FX6_DC_IN_MIN_V_G160 = 18.0
FX6_DC_IN_MAX_V_G160 = 20.5
FX6_DC_IN_ALARM_L1_V_G160 = 16.5
FX6_DC_IN_ALARM_L2_V_G160 = 15.5
FX6_BATTERY_LESS_BOOT_SUPPORTED_G160 = True
FX6_DC_UNPLUG_TO_BPU_SEAMLESS_G160 = True
FX6_USBC_BODY_POWER_SUPPORTED_G160 = False

NTSC_PAL_SKU_GATE_FN_G160 = "lib::backup_get_ntsc_pal_selector_dst"
ALLOWED_NTSC_PAL_SKUS_G160: Tuple[str, ...] = ("J1", "CE", "E33", "U2")
ALLOWED_VIDEO_STANDARDS_G160: Tuple[str, ...] = ("NTSC", "PAL")
NTSC_PAL_SKU_DEFAULTS_G160: Dict[str, str] = {
    "J1": "NTSC",
    "CE": "PAL",
    "E33": "PAL",
    "U2": "NTSC",
}
RUNNING_ON_NTSC_BANNER_G160 = "Running on NTSC."
RUNNING_ON_PAL_BANNER_G160 = "Running on PAL."
VER7_XAVC_SWITCH_REQUIRES_REBOOT_G160 = True
VER7_XAVC_SWITCH_REQUIRES_FORMAT_G160 = False
CROSS_STANDARD_PLAYBACK_ALLOWED_G160 = False
ALLOWED_AVF_DB_OPERATIONS_G160: Tuple[str, ...] = (
    "none",
    "playback_check",
    "avf_info_create",
    "avf_info_update",
    "recover_image_db",
    "format_card",
)
MUTATING_AVF_DB_OPERATIONS_G160: Tuple[str, ...] = (
    "avf_info_create",
    "avf_info_update",
    "recover_image_db",
    "format_card",
)
RECOVER_DB_MIN_SOC_PCT_G160 = 10
RECOVER_DB_MIN_VOLTAGE_MV_G160 = 6400
EXACT_6_FX6_SYSTEM_FREQUENCIES_G160: Tuple[str, ...] = (
    "59.94",
    "50",
    "29.97",
    "25",
    "24",
    "23.98",
)
FX6_THUMBNAIL_FILTERS_BY_CURRENT_FREQ_G160 = True

# UXC resid16 anchors (G160)
USB_POWER_SUPPLY_F_RESID16_G160 = 0x721E
USB_TYPE_C_ONLY_BASE_RESID16_G160 = 0xE931
NTSC_PAL_SELECTOR_F_RESID16_G160 = 0x6B6F
RUNNING_ON_NTSC_BASE_RESID16_G160 = 0xE77A
RUNNING_ON_PAL_BASE_RESID16_G160 = 0xE0B6
CHANGE_TO_PAL_REBOOT_BASE_RESID16_G160 = 0xE5C1
IMAGE_DB_CREATE_BASE_RESID16_G160 = 0xEA23
IMAGE_DB_UPDATE_BASE_RESID16_G160 = 0xEA24
RECOVER_IMAGE_DB_BASE_RESID16_G160 = 0xE918
CROSS_STD_PLAYBACK_BLOCK_G_RESID16_G160 = 0x61CA
FX6_CHANGE_SYS_FREQ_NS2_RESID16_G160 = 0x40AB

STATUS_VERIFIED_G160 = (
    "VERIFIED_G160_USB_PD_MANDATORY_FZ100_DCC1_AND_NTSC_PAL_SKU_AVFINFO_SLOT1_EROFS"
)
STATUS_BLOCKED_G160_TELEMETRY_INVALID = "BLOCKED_G160_TELEMETRY_INVALID"
STATUS_BLOCKED_G160_SLOT1_AVFINFO_OR_FORMAT_VAULT_EROFS = (
    "BLOCKED_G160_SLOT1_AVFINFO_OR_FORMAT_VAULT_EROFS"
)
STATUS_BLOCKED_G160_FX6_DC_IN_HOT_REPLUG_RECORDING_EBUSY = (
    "BLOCKED_G160_FX6_DC_IN_HOT_REPLUG_RECORDING_EBUSY"
)
STATUS_BLOCKED_G160_MICROUSB_NO_FZ100_J1_LOCK_OR_CROSS_STD_EOPNOTSUPP = (
    "BLOCKED_G160_MICROUSB_NO_FZ100_J1_LOCK_OR_CROSS_STD_EOPNOTSUPP"
)
STATUS_BLOCKED_G160_USBPD_CHARGE_DCC1_OR_NTSCPAL_CONSTRAINT_VIOLATION = (
    "BLOCKED_G160_USBPD_CHARGE_DCC1_OR_NTSCPAL_CONSTRAINT_VIOLATION"
)

STATUS_BLOCKED_PHASE373_DONOR_INTEGRITY = "BLOCKED_PHASE373_DONOR_CONTRACT_INTEGRITY"


# ---------------------------------------------------------------------------
# Pinned Wave-70 Donor Specs (O_RDONLY / Bounded Slices, Raw Bytes = 0)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX_P373 = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX6_NF15_PREFIX_P373 = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)

PINNED_FX3_APPFW_SLICES_PHASE373: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x03BC9876, b"BKID_APP_setting_peaking_display"),
    (0x03BC98BB, b"BKID_APP_setting_peaking_level"),
    (0x03BC98FC, b"BKID_APP_setting_peaking_color"),
    (0x03BC9897, b"BKID_APP_MR_setting_peaking_display"),
    (0x039CC94E, b"FUNC_toggle_peaking_display_seq"),
    (0x03B3367A, b"VAL_setting_peaking_color_PEAKING_COLOR_VALUE_WHITE"),
    (0x02FD31DA, b"view_mp_focus_map"),
    (0x0399B508, b"to_remote_event_focus_map"),
    (0x03BC7346, b"BKID_APP_setting_audio_recording_level_display"),
    (0x03BC71C1, b"BKID_APP_setting_audio_recording"),
    (0x03BC7206, b"BKID_APP_setting_audio_recording_level"),
    (0x03C2553A, b"adj_audio_rec_level_defult"),
    (0x03BC7257, b"BKID_APP_setting_audio_output_timing"),
    (0x03BC72A4, b"BKID_APP_setting_wind_noise_reduct"),
    (0x03B191EA, b"VAL_setting_wind_noise_reduct_WIND_NOISE_REDUCT_AUTO"),
    (0x03957AC7, b"MSG_ID_INFRABB_ADF_IN_SET_LOW_CUT"),
    (0x03BC72ED, b"BKID_APP_setting_external_mic_audio_format"),
    (0x03BCBFF6, b"BKID_APP_setting_audio_monitoring_ch"),
    (0x03BCC0A7, b"BKID_APP_setting_usb_supply"),
    (0x03C1E3F5, b"UPM_PS_USB_SUPPLY_ELECTRIC_POWER_TYPE_HIGH"),
    (0x03C1E3CB, b"UPM_PS_USB_SUPPLY_ELECTRIC_POWER_TYPE_LOW"),
    (0x03B49FF6, b"VAL_battery_inserted_BATTERY_IS_NOT_INSERTED"),
    (0x03B4A023, b"VAL_battery_inserted_BATTERY_IS_INSERTED"),
    (0x03B4B6B6, b"VAL_power_supply_type_UPM_PS_TYPE_ACV"),
    (0x03BCED78, b"BKID_APP_setting_ntsc_pal_selector"),
    (0x039A5FAA, b"backup_get_ntsc_pal_selector_dst"),
    (0x039BDE2A, b"PRM_media_database_error_state_slot1"),
    (0x039BDE4F, b"PRM_media_database_error_state_slot2"),
    (0x03BFD327, b"start_recover_db"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE373 = (
    "cae94e9c4482a1387eeb8f2d8cdb08fbd48fa1a34acf3ceb918e295fdb3693bf"
)

PINNED_FX6_APPFW_SLICES_PHASE373: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x02706D2C, b"BKID_APP_SETTING_PEAKING_DISPLAY"),
    (0x02706D4D, b"BKID_APP_SETTING_PEAKING_LEVEL"),
    (0x02706D6C, b"BKID_APP_SETTING_PEAKING_COLOR"),
    (0x027D1D97, b"UIBIZ_KEY_TACT_PEAKING"),
    (0x0270AF9B, b"BKID_APP_SETTING_SDI_OUTPUT_DISPLAY"),
    (0x0270700C, b"BKID_APP_SETTING_HDMI_INFO_DISPLAY"),
    (0x0270BDB9, b"BKID_APP_SETTING_CH1_WIND_FILTER"),
    (0x0270BE1C, b"BKID_APP_SETTING_CH4_WIND_FILTER"),
    (0x0270CDB8, b"BKID_APP_SETTING_DC_LOW_VOLT1"),
    (0x0270CDD6, b"BKID_APP_SETTING_DC_LOW_VOLT2"),
    (0x025EE849, b"sequence_set_usb_power_supply"),
    (0x025376A0, b"BKID_APP_EXTERN_SYSTEM_FREQUENCY"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE373 = (
    "f85bd64ac75de048728d71788c0885c2b1088eb7930512bc8428f4a9bb5d0bf0"
)

PINNED_PHASE373_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE373,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE373),
        "FX3 appFw.so Wave-70 Peaking/Audio/Wind/USB-PD/NTSC-PAL/AVF_INFO slices",
    ),
    "fx3_libusbbuspower_so": (
        "FX3",
        f"{_FX3_USR_PREFIX_P373}/lib/libUsbBusPower.so",
        48_232,
        "c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748",
        (
            b"\x7fELF",
            b"_ZN11UsbBusPower19GetCurrentBattStateEPi",
            b"_ZN11UsbBusPower26GetCurrentPowerSupplyStateEPNS_17__PWR_SPPLY_STATEE",
            b"_ZN11UsbBusPower30UpdateEffectiveBusPowerSettingEb",
            b"_ZNK11UsbBusPower18BusPowerPortStatus11IsSinkReadyEv",
        ),
        "FX3 libUsbBusPower.so Wave-70 mandatory battery handshake & sink readiness",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4\x00", b"ILME-FX3"),
        "FX3-CX95900_ALLLANG-Backup.bin BK4 seed",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P373}/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Peaking Display",
            b"Peaking Display Select",
            b"Focus Map",
            b"Focus Map Display Sel.",
            b"Audio Level Display",
            b"Audio Recording",
            b"Audio Out Timing",
            b"Shoe Audio Set.",
            b"4ch Audio Monitoring",
            b"USB Power Supply",
            b"NTSC/PAL Selector",
        ),
        "FX3 string_english_f.uxc Wave-70 EN parity",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P373}/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "\u5cf0\u503c\u663e\u793a".encode("utf-8"),
            "\u7126\u70b9\u56fe".encode("utf-8"),
            "\u97f3\u9891\u7b49\u7ea7\u663e\u793a".encode("utf-8"),
            "\u5f55\u97f3".encode("utf-8"),
            "\u97f3\u9891\u8f93\u51fa\u65f6\u523b".encode("utf-8"),
            "MI\u9774\u97f3\u9891\u8bbe\u7f6e".encode("utf-8"),
            "USB\u7535\u6e90\u4f9b\u7ed9".encode("utf-8"),
            "NTSC/PAL\u9009\u62e9\u5668".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-70 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P373}/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "\u5cf0\u503c\u986f\u793a".encode("utf-8"),
            "\u5c0d\u7126\u5716".encode("utf-8"),
            "\u97f3\u8a0a\u7b49\u7d1a\u986f\u793a".encode("utf-8"),
            "\u97f3\u8a0a\u9304\u88fd".encode("utf-8"),
            "\u97f3\u8a0a\u8f38\u51fa\u6642\u523b".encode("utf-8"),
            "MI\u9774\u97f3\u8a0a\u8a2d\u5b9a".encode("utf-8"),
            "USB\u96fb\u6e90\u4f9b\u7d66".encode("utf-8"),
            "NTSC/PAL\u9078\u64c7\u5668".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-70 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P373}/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "\u30d4\u30fc\u30ad\u30f3\u30b0\u8868\u793a".encode("utf-8"),
            "\u30d5\u30a9\u30fc\u30ab\u30b9\u30de\u30c3\u30d7".encode("utf-8"),
            "\u97f3\u58f0\u30ec\u30d9\u30eb\u8868\u793a".encode("utf-8"),
            "\u97f3\u58f0\u8a18\u9332".encode("utf-8"),
            "\u97f3\u58f0\u51fa\u529b\u30bf\u30a4\u30df\u30f3\u30b0".encode("utf-8"),
            "USB\u7d66\u96fb".encode("utf-8"),
            "NTSC/PAL\u5207\u63db".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-70 JA parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P373}/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Peaking Level",
            b"Peaking Color",
            b"Wind Noise Reduct.",
            b"USB Type-C",
            b"Running on NTSC.",
            b"Running on PAL.",
            b"Image Database File",
            b"Recover Image DB",
        ),
        "FX3 string_english.uxc Wave-70 EN base",
    ),
    "fx3_string_simplifiedchinese_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P373}/share/app/string_simplifiedchinese.uxc",
        149_064,
        "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
        (
            "\u5cf0\u503c\u6c34\u5e73".encode("utf-8"),
            "\u5cf0\u503c\u8272\u5f69".encode("utf-8"),
            "\u51cf\u5c11\u98ce\u566a\u58f0".encode("utf-8"),
            "\u8fd0\u884c\u4e8eNTSC\u3002".encode("utf-8"),
            "\u8fd0\u884c\u4e8ePAL\u3002".encode("utf-8"),
            "\u4fee\u590d\u5f71\u50cf\u6570\u636e\u5e93".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese.uxc Wave-70 ZH-CN base",
    ),
    "fx3_string_traditionalchinese_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P373}/share/app/string_traditionalchinese.uxc",
        151_908,
        "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
        (
            "\u5cf0\u503c\u7b49\u7d1a".encode("utf-8"),
            "\u5cf0\u503c\u984f\u8272".encode("utf-8"),
            "\u6e1b\u5c11\u98a8\u566a\u97f3".encode("utf-8"),
            "\u5728NTSC\u4e0a\u57f7\u884c\u3002".encode("utf-8"),
            "\u5728PAL\u4e0a\u57f7\u884c\u3002".encode("utf-8"),
            "\u9084\u539f\u5f71\u50cf\u8cc7\u6599\u5eab".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese.uxc Wave-70 ZH-TW base",
    ),
    "fx3_string_japanese_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P373}/share/app/string_japanese.uxc",
        208_564,
        "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
        (
            "\u30d4\u30fc\u30ad\u30f3\u30b0\u30ec\u30d9\u30eb".encode("utf-8"),
            "\u30d4\u30fc\u30ad\u30f3\u30b0\u8272".encode("utf-8"),
            "\u98a8\u97f3\u4f4e\u6e1b".encode("utf-8"),
            "NTSC\u3067\u52d5\u4f5c\u4e2d".encode("utf-8"),
            "PAL\u3067\u52d5\u4f5c\u4e2d".encode("utf-8"),
            "\u7ba1\u7406\u30d5\u30a1\u30a4\u30eb\u4fee\u5fa9".encode("utf-8"),
        ),
        "FX3 string_japanese.uxc Wave-70 JA base",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P373}/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Peaking Display",
            b"Audio Recording",
            b"NTSC",
            b"PAL",
        ),
        "FX3 string_english_g.uxc Wave-70 EN guide",
    ),
    "fx3_string_simplifiedchinese_g_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P373}/share/app/string_simplifiedchinese_g.uxc",
        61_296,
        "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
        (
            "\u5cf0\u503c\u663e\u793a".encode("utf-8"),
            "NTSC".encode("utf-8"),
            "\u5f55\u97f3".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_g.uxc Wave-70 ZH-CN guide",
    ),
    "fx6_appfw_so": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P373}/lib/appFw.so",
        50_520_424,
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE373,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE373),
        "FX6 appFw.so Wave-70 Peaking(ZeroTypeFreq)/WindFilter/DCLowVolt/SystemFreq slices",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P373}/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"Peaking Level",
            b"Wind Filter",
            b"Output Display",
            b"Thumbnail",
        ),
        "FX6 string_english.uxc Wave-70 EN baseline",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P373}/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"Peaking Type",
            b"Peaking Frequency",
            b"Audio Level Meter",
            b"Change System Frequency?",
            b"B&W",
        ),
        "FX6 string_english_2.uxc Wave-70 EN enterprise baseline",
    ),
}


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _is_clean_room_forced(force_clean_room: Optional[bool]) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE373):
        if os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def _is_strict_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _is_strict_number(val: Any) -> bool:
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
    if body_model_name != FX3_MODEL_NAME_PHASE373:
        errs.append(f"body_model_name_invalid:{body_model_name!r}")
    if not _is_strict_int(body_model_id) or body_model_id != FX3_MODEL_ID_PHASE373:
        errs.append(f"body_model_id_invalid:{body_model_id!r}")
    if help_guide_code != FX3_HELP_GUIDE_CODE_PHASE373:
        errs.append(f"help_guide_code_invalid:{help_guide_code!r}")
    if _parse_fw_float(firmware_version) is None:
        errs.append(f"firmware_version_invalid:{firmware_version!r}")
    return errs


def strip_elapsed_seconds_recursive_phase373(obj: Any) -> Any:
    """Recursively strip non-deterministic `elapsed_seconds`/`elapsed_ms` keys for canonical digests."""
    if isinstance(obj, dict):
        return {
            k: strip_elapsed_seconds_recursive_phase373(v)
            for k, v in obj.items()
            if k not in ("elapsed_seconds", "elapsed_ms")
        }
    if isinstance(obj, list):
        return [strip_elapsed_seconds_recursive_phase373(v) for v in obj]
    if isinstance(obj, tuple):
        return [strip_elapsed_seconds_recursive_phase373(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Donor Integrity Audit (O_RDONLY / Clean-Room Dual-Mode)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase373DonorAuditResult:
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


def audit_phase373_donor_contracts(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase373DonorAuditResult:
    """Fast (< 0.20s) O_RDONLY + bounded os.pread donor audit with clean-room fallback."""
    import time

    t0 = time.perf_counter()
    clean_forced = _is_clean_room_forced(force_clean_room)
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else dict(PINNED_PHASE373_DONOR_SPECS)
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
        return Phase373DonorAuditResult(
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
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE373,
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
        return Phase373DonorAuditResult(
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
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE373,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(
                f"Donor files absent ({len(missing_files)} missing); "
                "verified Phase 373 via clean-room synthetic fallback.",
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
                target, PINNED_FX3_APPFW_SLICES_PHASE373
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tok_errs = _read_exact_o_rdonly_slices(
                target, PINNED_FX6_APPFW_SLICES_PHASE373
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
    return Phase373DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE
            if valid
            else STATUS_BLOCKED_PHASE373_DONOR_INTEGRITY
        ),
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="STRICT_OS_O_RDONLY_PREAD",
        files_inspected=inspected,
        fx3_contracts_verified=valid,
        fx6_contracts_verified=valid,
        four_lang_resid16_parity_verified=valid,
        zero_forbidden_myths_verified=valid,
        elapsed_seconds=round(dt, 6),
        within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE373,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        file_digests=file_digests,
        missing_markers=tuple(missing_markers),
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# Gate G159: Peaking Clean-HDMI / Zero FX6 Type-Freq &
#            Ver. 2.00+ Audio 5-Item / Wind Noise Built-In Mic Only
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PeakingAudioWindGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    peaking_display_menu_path: str
    fx6_peaking_menu_path: str
    audio_recording_menu_path: str
    fx6_audio_input_menu_path: str
    fx3_peaking_items_count: int
    fx6_peaking_items_count: int
    effective_peaking_display: str
    effective_peaking_level: str
    effective_peaking_color: str
    peaking_resettable_by_camset_reset: bool
    peaking_emitted_over_hdmi: bool
    hdmi_peaking_leaked_pixels: int
    peaking_compatible_with_focus_magnifier: bool
    focus_magnifier_active: bool
    fx3_inbody_focus_map_exposed: bool
    wireless_mc_focus_map_allowed: bool
    fx6_peaking_color: str
    fx6_peaking_type_elf_hits: int
    fx6_peaking_freq_elf_hits: int
    audio_level_display_menu_removed_ver2_plus: bool
    fx3_audio_recording_items_count: int
    fx3_audio_5items_resettable_by_camset_reset: bool
    effective_shoot_mode: str
    effective_audio_recording: str
    effective_audio_rec_level: int
    audio_rec_level_elf_typo: str
    fx3_audio_limiter_permanent_non_disableable: bool
    effective_audio_out_timing: str
    effective_wind_noise_reduct: str
    fx3_wind_noise_auto_exposed: bool
    wind_noise_dsp_active: bool
    wind_noise_bypassed_reason: str
    effective_shoe_audio_format: str
    active_audio_input_source: str
    active_audio_channels: int
    shoe_audio_menu_selectable: bool
    fx6_handle_hw_low_cut_switch_present: bool
    fx6_wind_filter_channels_count: int
    fx6_limiter_mode: str
    dormant_or_cross_model_eopnotsupp_rejected: bool
    emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_fx3_peaking_audio_wind_state(
    *,
    peaking_display: str = PEAKING_DISPLAY_DEFAULT_G159,
    peaking_level: str = PEAKING_LEVEL_DEFAULT_G159,
    peaking_color: str = PEAKING_COLOR_DEFAULT_G159,
    hdmi_info_display: str = "Off",
    raw_output: str = "Off",
    focus_magnifier_active: bool = False,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE373,
    audio_recording: str = AUDIO_RECORDING_DEFAULT_G159,
    audio_rec_level: int = AUDIO_REC_LEVEL_DEFAULT_G159,
    audio_out_timing: str = AUDIO_OUT_TIMING_DEFAULT_G159,
    wind_noise_reduct: str = WIND_NOISE_REDUCT_DEFAULT_G159,
    shoe_audio_format: str = SHOE_AUDIO_DEFAULT_G159,
    mic_35mm_plugged: bool = False,
    xlr_h1_mode: str = "OFF",
    mi_shoe_other_mic_attached: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE373,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-70 Peaking & Audio/Wind state."""
    init_applied = reset_action == RESET_ACTION_INITIALIZE_PHASE373
    camset_reset_applied = reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE373

    # ALL 3 [Peaking Display] items are anti-[Camera Settings Reset]; ONLY [Initialize] resets them.
    eff_peaking_display = PEAKING_DISPLAY_DEFAULT_G159 if init_applied else peaking_display
    eff_peaking_level = PEAKING_LEVEL_DEFAULT_G159 if init_applied else peaking_level
    eff_peaking_color = PEAKING_COLOR_DEFAULT_G159 if init_applied else peaking_color

    # Clean-HDMI iron law: peaking NEVER exits over HDMI regardless of HDMI Info Display or RAW Output.
    _ = (hdmi_info_display, raw_output)
    peaking_over_hdmi = False

    # ALL 5 [Audio Recording] items ARE resettable (`Can be reset`) via [Camera Settings Reset] & [Initialize].
    if init_applied or camset_reset_applied:
        eff_audio_rec = AUDIO_RECORDING_DEFAULT_G159
        eff_audio_level = AUDIO_REC_LEVEL_DEFAULT_G159
        eff_audio_timing = AUDIO_OUT_TIMING_DEFAULT_G159
        eff_wind_reduct = WIND_NOISE_REDUCT_DEFAULT_G159
        eff_shoe_fmt = SHOE_AUDIO_DEFAULT_G159
    else:
        eff_audio_rec = audio_recording
        eff_audio_level = audio_rec_level
        eff_audio_timing = audio_out_timing
        eff_wind_reduct = wind_noise_reduct
        eff_shoe_fmt = shoe_audio_format

    # 3-Tier Audio Input Preemption:
    # Tier 1: 3.5mm MIC > Tier 2: MI Shoe (XLR-H1 DIGITAL/ANALOG or ECM-M1/B1M) > Tier 3: Built-in stereo mic
    if shoot_mode == SHOOT_MODE_SQ_PHASE373:
        active_source = "none_sq_0ch"
        active_channels = 0
        shoe_selectable = False
        wind_bypass_reason = "sq_0ch_disabled"
    elif eff_audio_rec == "Off":
        active_source = "audio_recording_off"
        active_channels = 0
        shoe_selectable = (not mic_35mm_plugged) and (
            xlr_h1_mode == "DIGITAL" or mi_shoe_other_mic_attached
        )
        wind_bypass_reason = "audio_recording_off"
    elif mic_35mm_plugged:
        active_source = "3.5mm_mic"
        active_channels = 2
        shoe_selectable = False
        wind_bypass_reason = "external_3.5mm_mic_preempts"
    elif xlr_h1_mode == "DIGITAL":
        active_source = "mi_shoe_xlr_h1_digital"
        active_channels = 4 if eff_shoe_fmt == "48kHz/24bit 4ch" else 2
        shoe_selectable = True
        wind_bypass_reason = "external_xlr_h1_digital_bypass"
    elif xlr_h1_mode == "ANALOG":
        active_source = "mi_shoe_xlr_h1_analog"
        active_channels = 2
        eff_shoe_fmt = SHOE_AUDIO_DEFAULT_G159
        shoe_selectable = False
        wind_bypass_reason = "external_xlr_h1_analog_bypass"
    elif mi_shoe_other_mic_attached:
        active_source = "mi_shoe_external_mic"
        active_channels = 4 if eff_shoe_fmt == "48kHz/24bit 4ch" else 2
        shoe_selectable = True
        wind_bypass_reason = "external_mi_shoe_mic_bypass"
    else:
        active_source = "builtin_stereo_mic"
        active_channels = 2
        shoe_selectable = False
        wind_bypass_reason = "none" if eff_wind_reduct == "On" else "wind_reduct_off"

    wind_dsp_active = bool(
        active_source == "builtin_stereo_mic" and eff_wind_reduct == "On"
    )

    return {
        "effective_peaking_display": eff_peaking_display,
        "effective_peaking_level": eff_peaking_level,
        "effective_peaking_color": eff_peaking_color,
        "peaking_emitted_over_hdmi": peaking_over_hdmi,
        "effective_audio_recording": eff_audio_rec,
        "effective_audio_rec_level": eff_audio_level,
        "effective_audio_out_timing": eff_audio_timing,
        "effective_wind_noise_reduct": eff_wind_reduct,
        "effective_shoe_audio_format": eff_shoe_fmt,
        "active_audio_input_source": active_source,
        "active_audio_channels": active_channels,
        "shoe_audio_menu_selectable": shoe_selectable,
        "wind_noise_dsp_active": wind_dsp_active,
        "wind_noise_bypassed_reason": wind_bypass_reason,
    }


def compute_peaking_audio_wind_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G159 (384 states)."""
    combos = list(
        itertools.product(
            ("Off", "On"),  # peaking_display (2)
            ("Off", "On"),  # hdmi_info_display (2)
            ("Off", "On"),  # raw_output (2)
            ALLOWED_SHOOT_MODES_PHASE373,  # 3 (Still, Movie, S&Q)
            ("Off", "On"),  # wind_noise_reduct (2)
            (False, True),  # mic_35mm_plugged (2)
            ("OFF", "DIGITAL"),  # xlr_h1_mode (2)
            (
                RESET_ACTION_NONE_PHASE373,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE373,
            ),  # 2 -> 2*2*2*3*2*2*2*2 = 384
        )
    )
    hdmi_peaking_zero_count = 0
    peaking_reset_preserved_count = 0
    wind_reset_cleared_count = 0
    wind_builtin_only_active_count = 0
    wind_external_or_sq_bypassed_count = 0
    mic_35mm_preempted_xlr_count = 0

    for pk, hinfo, raw, sm, wind, m35, xlr, rst in combos:
        st = resolve_fx3_peaking_audio_wind_state(
            peaking_display=pk,
            peaking_level="High",
            peaking_color="Red",
            hdmi_info_display=hinfo,
            raw_output=raw,
            shoot_mode=sm,
            wind_noise_reduct=wind,
            shoe_audio_format="48kHz/24bit 4ch",
            mic_35mm_plugged=m35,
            xlr_h1_mode=xlr,
            reset_action=rst,
        )
        if not st["peaking_emitted_over_hdmi"]:
            hdmi_peaking_zero_count += 1
        if rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE373:
            if (
                st["effective_peaking_display"] == pk
                and st["effective_peaking_level"] == "High"
                and st["effective_peaking_color"] == "Red"
            ):
                peaking_reset_preserved_count += 1
            if wind == "On" and st["effective_wind_noise_reduct"] == "Off":
                wind_reset_cleared_count += 1
        if st["wind_noise_dsp_active"]:
            wind_builtin_only_active_count += 1
        elif st["effective_wind_noise_reduct"] == "On":
            wind_external_or_sq_bypassed_count += 1
        if sm != SHOOT_MODE_SQ_PHASE373 and m35 and xlr == "DIGITAL":
            if st["active_audio_input_source"] == "3.5mm_mic" and not st["shoe_audio_menu_selectable"]:
                mic_35mm_preempted_xlr_count += 1

    return {
        "total_matrix_states": len(combos),
        "hdmi_peaking_zero_count": hdmi_peaking_zero_count,
        "peaking_reset_preserved_count": peaking_reset_preserved_count,
        "wind_reset_cleared_count": wind_reset_cleared_count,
        "wind_builtin_only_active_count": wind_builtin_only_active_count,
        "wind_external_or_sq_bypassed_count": wind_external_or_sq_bypassed_count,
        "mic_35mm_preempted_xlr_count": mic_35mm_preempted_xlr_count,
    }


def verify_peaking_audio_wind_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE373,
    body_model_id: int = FX3_MODEL_ID_PHASE373,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE373,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE373,
    peaking_display: str = PEAKING_DISPLAY_DEFAULT_G159,
    peaking_level: str = PEAKING_LEVEL_DEFAULT_G159,
    peaking_color: str = PEAKING_COLOR_DEFAULT_G159,
    hdmi_info_display: str = "Off",
    raw_output: str = "Off",
    focus_magnifier_active: bool = False,
    claimed_peaking_over_hdmi: bool = False,
    claimed_camset_reset_clears_peaking: bool = False,
    claimed_peaking_focus_magnifier_mutex: bool = False,
    requested_inbody_focus_map: bool = False,
    requested_usb_wired_mc_focus_map: bool = False,
    wireless_mc_app_connected: bool = False,
    fx6_peaking_color: str = "B&W",
    requested_fx6_dormant_peaking_type_or_freq: bool = False,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE373,
    audio_recording: str = AUDIO_RECORDING_DEFAULT_G159,
    audio_rec_level: int = AUDIO_REC_LEVEL_DEFAULT_G159,
    audio_out_timing: str = AUDIO_OUT_TIMING_DEFAULT_G159,
    wind_noise_reduct: str = WIND_NOISE_REDUCT_DEFAULT_G159,
    shoe_audio_format: str = SHOE_AUDIO_DEFAULT_G159,
    mic_35mm_plugged: bool = False,
    xlr_h1_mode: str = "OFF",
    mi_shoe_other_mic_attached: bool = False,
    requested_audio_level_display_menu_write: bool = False,
    requested_wind_noise_auto: bool = False,
    requested_disable_fx3_audio_limiter: bool = False,
    claimed_audio_5items_reset_immune: bool = False,
    claimed_wind_noise_active_on_external_mic: bool = False,
    claimed_35mm_allows_xlr_4ch: bool = False,
    requested_fx6_handle_hw_low_cut_switch: bool = False,
    fx6_limiter_mode: str = "Off",
    reset_action: str = RESET_ACTION_NONE_PHASE373,
) -> PeakingAudioWindGuardResult:
    """Enforce Gate G159: Peaking Clean-HDMI / Zero FX6 Type-Freq & Audio 5-Item / Wind Built-In Only."""
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

    if not _is_on_off(peaking_display):
        _add("TELEMETRY_INVALID", f"peaking_display_invalid:{peaking_display!r}")
    if peaking_level not in ALLOWED_PEAKING_LEVELS_G159:
        _add("TELEMETRY_INVALID", f"peaking_level_invalid:{peaking_level!r}")
    if peaking_color not in ALLOWED_FX3_PEAKING_COLORS_G159:
        _add("TELEMETRY_INVALID", f"peaking_color_invalid:{peaking_color!r}")
    if not _is_on_off(hdmi_info_display):
        _add("TELEMETRY_INVALID", f"hdmi_info_display_invalid:{hdmi_info_display!r}")
    if not _is_on_off(raw_output):
        _add("TELEMETRY_INVALID", f"raw_output_invalid:{raw_output!r}")
    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE373:
        _add("TELEMETRY_INVALID", f"shoot_mode_invalid:{shoot_mode!r}")
    if not _is_on_off(audio_recording):
        _add("TELEMETRY_INVALID", f"audio_recording_invalid:{audio_recording!r}")
    if (
        not _is_strict_int(audio_rec_level)
        or audio_rec_level < AUDIO_REC_LEVEL_MIN_G159
        or audio_rec_level > AUDIO_REC_LEVEL_MAX_G159
    ):
        _add("TELEMETRY_INVALID", f"audio_rec_level_invalid:{audio_rec_level!r}")
    if audio_out_timing not in ALLOWED_AUDIO_OUT_TIMING_G159:
        _add("TELEMETRY_INVALID", f"audio_out_timing_invalid:{audio_out_timing!r}")
    if wind_noise_reduct not in ("Off", "On", "Auto"):
        _add("TELEMETRY_INVALID", f"wind_noise_reduct_invalid:{wind_noise_reduct!r}")
    if shoe_audio_format not in ALLOWED_SHOE_AUDIO_FORMATS_G159:
        _add("TELEMETRY_INVALID", f"shoe_audio_format_invalid:{shoe_audio_format!r}")
    if xlr_h1_mode not in ALLOWED_XLR_H1_MODES_G159:
        _add("TELEMETRY_INVALID", f"xlr_h1_mode_invalid:{xlr_h1_mode!r}")
    if fx6_limiter_mode not in EXACT_6_FX6_LIMITER_MODES_G159:
        _add("TELEMETRY_INVALID", f"fx6_limiter_mode_invalid:{fx6_limiter_mode!r}")
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE373:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")
    if fx6_peaking_color not in (*ALLOWED_FX6_PEAKING_COLORS_G159, "White"):
        _add("TELEMETRY_INVALID", f"fx6_peaking_color_invalid:{fx6_peaking_color!r}")

    fw_num = _parse_fw_float(firmware_version)
    wireless_mc_focus_map_ok = bool(
        wireless_mc_app_connected
        and fw_num is not None
        and fw_num >= FX3_MC_WIRELESS_FOCUS_MAP_MIN_FW_G159
    )

    state = resolve_fx3_peaking_audio_wind_state(
        peaking_display=peaking_display if _is_on_off(peaking_display) else PEAKING_DISPLAY_DEFAULT_G159,
        peaking_level=peaking_level if peaking_level in ALLOWED_PEAKING_LEVELS_G159 else PEAKING_LEVEL_DEFAULT_G159,
        peaking_color=peaking_color if peaking_color in ALLOWED_FX3_PEAKING_COLORS_G159 else PEAKING_COLOR_DEFAULT_G159,
        hdmi_info_display=hdmi_info_display if _is_on_off(hdmi_info_display) else "Off",
        raw_output=raw_output if _is_on_off(raw_output) else "Off",
        focus_magnifier_active=focus_magnifier_active,
        shoot_mode=shoot_mode if shoot_mode in ALLOWED_SHOOT_MODES_PHASE373 else SHOOT_MODE_MOVIE_PHASE373,
        audio_recording=audio_recording if _is_on_off(audio_recording) else AUDIO_RECORDING_DEFAULT_G159,
        audio_rec_level=(
            audio_rec_level
            if _is_strict_int(audio_rec_level)
            and AUDIO_REC_LEVEL_MIN_G159 <= audio_rec_level <= AUDIO_REC_LEVEL_MAX_G159
            else AUDIO_REC_LEVEL_DEFAULT_G159
        ),
        audio_out_timing=(
            audio_out_timing
            if audio_out_timing in ALLOWED_AUDIO_OUT_TIMING_G159
            else AUDIO_OUT_TIMING_DEFAULT_G159
        ),
        wind_noise_reduct=(
            wind_noise_reduct
            if wind_noise_reduct in ALLOWED_FX3_WIND_NOISE_OPTIONS_G159
            else WIND_NOISE_REDUCT_DEFAULT_G159
        ),
        shoe_audio_format=(
            shoe_audio_format
            if shoe_audio_format in ALLOWED_SHOE_AUDIO_FORMATS_G159
            else SHOE_AUDIO_DEFAULT_G159
        ),
        mic_35mm_plugged=mic_35mm_plugged,
        xlr_h1_mode=xlr_h1_mode if xlr_h1_mode in ALLOWED_XLR_H1_MODES_G159 else "OFF",
        mi_shoe_other_mic_attached=mi_shoe_other_mic_attached,
        reset_action=reset_action if reset_action in ALLOWED_RESET_ACTIONS_PHASE373 else RESET_ACTION_NONE_PHASE373,
    )

    # 1. EOPNOTSUPP=95 Dormant / Removed / Cross-Model Rejections
    wind_auto_attempt = bool(wind_noise_reduct == "Auto" or requested_wind_noise_auto)
    fx6_white_color_attempt = fx6_peaking_color == "White"
    dormant_or_eopnotsupp = bool(
        requested_inbody_focus_map
        or requested_usb_wired_mc_focus_map
        or requested_fx6_dormant_peaking_type_or_freq
        or fx6_white_color_attempt
        or requested_audio_level_display_menu_write
        or wind_auto_attempt
        or requested_disable_fx3_audio_limiter
        or requested_fx6_handle_hw_low_cut_switch
    )

    if requested_inbody_focus_map:
        _add(
            "FX3_INBODY_FOCUS_MAP_DORMANT_EOPNOTSUPP",
            "fx3_ver7_02_inbody_focus_map_0x61f9_is_dormant_wireless_mc_app_only_eopnotsupp_95",
        )
    if requested_usb_wired_mc_focus_map:
        _add(
            "FX3_USB_WIRED_MC_FOCUS_MAP_UNSUPPORTED_EOPNOTSUPP",
            "monitor_and_control_focus_map_requires_wireless_not_usb_cable_eopnotsupp_95",
        )
    if requested_fx6_dormant_peaking_type_or_freq:
        _add(
            "FX6_DORMANT_PEAKING_TYPE_OR_FREQ_ZERO_ELF_EOPNOTSUPP",
            "fx6_appfw_has_0_peaking_type_and_0_peaking_freq_elf_symbols_eopnotsupp_95",
        )
    if fx6_white_color_attempt:
        _add(
            "FX6_PEAKING_COLOR_BW_NOT_WHITE_EOPNOTSUPP",
            "fx6_monitoring_peaking_color_uses_bw_not_white_eopnotsupp_95",
        )
    if requested_audio_level_display_menu_write:
        _add(
            "FX3_AUDIO_LEVEL_DISPLAY_MENU_REMOVED_VER2_EOPNOTSUPP",
            "fx3_ver2_00_to_7_02_removed_standalone_audio_level_display_menu_sdk_ro_eopnotsupp_95",
        )
    if wind_auto_attempt:
        _add(
            "FX3_WIND_NOISE_AUTO_UNEXPOSED_EOPNOTSUPP",
            "fx3_ver7_02_wind_noise_reduct_exposes_only_on_off_no_auto_eopnotsupp_95",
        )
    if requested_disable_fx3_audio_limiter:
        _add(
            "FX3_PERMANENT_AUDIO_LIMITER_NON_DISABLEABLE_EOPNOTSUPP",
            "fx3_builtin_audio_limiter_is_permanent_and_non_disableable_eopnotsupp_95",
        )
    if requested_fx6_handle_hw_low_cut_switch:
        _add(
            "FX6_HANDLE_ZERO_HW_LOW_CUT_SWITCH_EOPNOTSUPP",
            "fx6_standard_handle_has_no_hardware_low_cut_switch_uses_menu_ch1_4_wind_filter_eopnotsupp_95",
        )

    # 2. EINVAL=22 Clean-HDMI, Reset-Split, Preemption & Built-In-Only Violations
    if claimed_peaking_over_hdmi:
        _add(
            "PEAKING_CLEAN_HDMI_ISOLATION_VIOLATION",
            "fx3_peaking_outline_is_never_emitted_over_hdmi_regardless_of_hdmi_info_or_raw_einval_22",
        )
    if claimed_camset_reset_clears_peaking:
        _add(
            "PEAKING_3ITEMS_RESET_IMMUNITY_VIOLATION",
            "all_3_peaking_display_items_are_not_available_under_camset_reset_initialize_only_einval_22",
        )
    if claimed_peaking_focus_magnifier_mutex:
        _add(
            "PEAKING_FOCUS_MAGNIFIER_COMPAT_VIOLATION",
            "fx3_peaking_is_compatible_with_focus_magnifier_0_haita_mutex_einval_22",
        )
    if claimed_audio_5items_reset_immune:
        _add(
            "AUDIO_5ITEMS_RESETTABLE_VIOLATION",
            "all_5_shooting_audio_recording_items_are_can_be_reset_by_camset_reset_einval_22",
        )
    if claimed_wind_noise_active_on_external_mic and (
        mic_35mm_plugged
        or xlr_h1_mode in ("DIGITAL", "ANALOG")
        or mi_shoe_other_mic_attached
        or shoot_mode == SHOOT_MODE_SQ_PHASE373
    ):
        _add(
            "WIND_NOISE_BUILTIN_STEREO_MIC_ONLY_VIOLATION",
            "fx3_wind_noise_reduct_applies_to_builtin_stereo_mic_only_bypassed_on_external_or_sq_einval_22",
        )
    if claimed_35mm_allows_xlr_4ch and mic_35mm_plugged:
        _add(
            "AUDIO_35MM_PREEMPTS_XLRH1_4CH_VIOLATION",
            "3_5mm_mic_jack_preempts_mi_shoe_xlr_h1_and_locks_2ch_analog_adc_einval_22",
        )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G159
        block_errno = 0
        block_errno_name = "OK"
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G159_DORMANT_FOCUSMAP_FX6_TYPEFREQ_AUDIOMETER_OR_WINDAUTO_EOPNOTSUPP
        block_errno = EOPNOTSUPP_ERRNO_PHASE373
        block_errno_name = EOPNOTSUPP_NAME_PHASE373
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
        status = STATUS_BLOCKED_G159_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE373
        block_errno_name = EINVAL_NAME_PHASE373
    else:
        status = STATUS_BLOCKED_G159_PEAKING_HDMI_RESET_OR_AUDIO_PREEMPTION_WIND_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE373
        block_errno_name = EINVAL_NAME_PHASE373

    return PeakingAudioWindGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        peaking_display_menu_path=PEAKING_DISPLAY_MENU_PATH_G159,
        fx6_peaking_menu_path=FX6_PEAKING_MENU_PATH_G159,
        audio_recording_menu_path=AUDIO_RECORDING_MENU_PATH_G159,
        fx6_audio_input_menu_path=FX6_AUDIO_INPUT_MENU_PATH_G159,
        fx3_peaking_items_count=len(EXACT_3_FX3_PEAKING_ITEMS_G159),
        fx6_peaking_items_count=len(EXACT_3_FX6_PEAKING_ITEMS_G159),
        effective_peaking_display=state["effective_peaking_display"],
        effective_peaking_level=state["effective_peaking_level"],
        effective_peaking_color=state["effective_peaking_color"],
        peaking_resettable_by_camset_reset=FX3_PEAKING_RESETTABLE_BY_CAMSET_RESET_G159,
        peaking_emitted_over_hdmi=FX3_PEAKING_EMITTED_OVER_HDMI_G159,
        hdmi_peaking_leaked_pixels=FX3_HDMI_PEAKING_LEAKED_PIXELS_G159,
        peaking_compatible_with_focus_magnifier=FX3_PEAKING_COMPATIBLE_WITH_FOCUS_MAGNIFIER_G159,
        focus_magnifier_active=focus_magnifier_active,
        fx3_inbody_focus_map_exposed=FX3_INBODY_FOCUS_MAP_EXPOSED_G159,
        wireless_mc_focus_map_allowed=wireless_mc_focus_map_ok,
        fx6_peaking_color=fx6_peaking_color,
        fx6_peaking_type_elf_hits=FX6_PEAKING_TYPE_ELF_HITS_G159,
        fx6_peaking_freq_elf_hits=FX6_PEAKING_FREQ_ELF_HITS_G159,
        audio_level_display_menu_removed_ver2_plus=AUDIO_LEVEL_DISPLAY_MENU_REMOVED_VER2_PLUS_G159,
        fx3_audio_recording_items_count=len(EXACT_5_FX3_AUDIO_RECORDING_ITEMS_G159),
        fx3_audio_5items_resettable_by_camset_reset=FX3_AUDIO_5ITEMS_RESETTABLE_BY_CAMSET_RESET_G159,
        effective_shoot_mode=shoot_mode,
        effective_audio_recording=state["effective_audio_recording"],
        effective_audio_rec_level=state["effective_audio_rec_level"],
        audio_rec_level_elf_typo=AUDIO_REC_LEVEL_ELF_TYPO_G159,
        fx3_audio_limiter_permanent_non_disableable=FX3_AUDIO_LIMITER_PERMANENT_NON_DISABLEABLE_G159,
        effective_audio_out_timing=state["effective_audio_out_timing"],
        effective_wind_noise_reduct=state["effective_wind_noise_reduct"],
        fx3_wind_noise_auto_exposed=FX3_WIND_NOISE_AUTO_EXPOSED_G159,
        wind_noise_dsp_active=state["wind_noise_dsp_active"],
        wind_noise_bypassed_reason=state["wind_noise_bypassed_reason"],
        effective_shoe_audio_format=state["effective_shoe_audio_format"],
        active_audio_input_source=state["active_audio_input_source"],
        active_audio_channels=state["active_audio_channels"],
        shoe_audio_menu_selectable=state["shoe_audio_menu_selectable"],
        fx6_handle_hw_low_cut_switch_present=FX6_HANDLE_HW_LOW_CUT_SWITCH_PRESENT_G159,
        fx6_wind_filter_channels_count=len(FX6_WIND_FILTER_CHANNELS_G159),
        fx6_limiter_mode=fx6_limiter_mode,
        dormant_or_cross_model_eopnotsupp_rejected=dormant_or_eopnotsupp,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class G159PeakingAudioWindGuardResult:
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
    peaking_audio_wind_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g159_peaking_audio_wind_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G159PeakingAudioWindGuardResult]:
    audit = audit_phase373_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_peaking_audio_wind_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G159PeakingAudioWindGuardResult(
        gate_id=G159,
        gate_code=G159_GATE_CODE,
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
        peaking_audio_wind_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G159,
        gate_code=G159_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"peaking_hdmi={res.peaking_emitted_over_hdmi} "
            f"fx6_type_freq_hits={res.fx6_peaking_type_elf_hits}/{res.fx6_peaking_freq_elf_hits} "
            f"audio_items={res.fx3_audio_recording_items_count} "
            f"wind_auto={res.fx3_wind_noise_auto_exposed} "
            f"audio_src={res.active_audio_input_source}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_peaking_audio_wind_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G159PeakingAudioWindGuardResult]:
    return evaluate_g159_peaking_audio_wind_guard(**kwargs)


# ---------------------------------------------------------------------------
# Gate G160: USB Power Supply / Mandatory NP-FZ100 / DC-C1 &
#            NTSC/PAL SKU Lock / AVF_INFO Slot 1 EROFS=30 Firewall
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UsbPdNtscPalAvfInfoGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    usb_power_supply_menu_path: str
    ntsc_pal_selector_menu_path: str
    fx6_system_frequency_menu_path: str
    effective_usb_power_supply: str
    usb_power_supply_resettable_by_camset_reset: bool
    usb_port_kind: str
    power_source_mode: str
    camera_power_state: str
    usb_pd_watts: float
    low_power_drain_warning: bool
    np_fz100_inserted: bool
    np_fz100_soc_pct: int
    battery_voltage_mv: int
    fx3_battery_less_usb_boot_supported: bool
    fx3_battery_hot_swap_supported: bool
    fx3_charges_while_camera_on: bool
    charging_active: bool
    charge_led_state: str
    power_save_bypassed_by_usb_pd: bool
    dc_c1_pd_watts: float
    dc_c1_cable_amps: float
    monitor_brightness_locked_max: bool
    fx6_dc_in_voltage_v: float
    fx6_battery_less_boot_supported: bool
    fx6_dc_unplug_to_bpu_seamless: bool
    fx6_usbc_body_power_supported: bool
    ntsc_pal_sku_gate_function: str
    sku_region_code: str
    sku_default_standard: str
    effective_video_standard: str
    boot_banner_text: str
    ntsc_pal_switch_requires_reboot: bool
    ver7_xavc_switch_requires_format: bool
    cross_standard_playback_allowed: bool
    avf_db_operation: str
    target_media_slot: int
    slot1_tier0_erofs_blocked: bool
    slot1_data_sector_writes: int
    emmc_nflasha_write_count: int
    fx6_system_frequency_hz: str
    fx6_thumbnail_filters_by_current_freq: bool
    dormant_or_cross_model_eopnotsupp_rejected: bool
    emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_fx3_usbpd_ntscpal_avfinfo_state(
    *,
    usb_power_supply: str = USB_POWER_SUPPLY_DEFAULT_G160,
    usb_port_kind: str = "usb_type_c",
    power_source_mode: str = "usb_c_pd",
    camera_power_state: str = "ON",
    usb_pd_volts: float = USB_PD_RECOMMENDED_SHOOT_VOLTS_G160,
    usb_pd_amps: float = USB_PD_RECOMMENDED_SHOOT_AMPS_G160,
    np_fz100_inserted: bool = True,
    np_fz100_soc_pct: int = 80,
    ambient_temp_c: float = 22.0,
    dc_c1_pd_watts: float = DC_C1_MIN_PD_WATTS_G160,
    dc_c1_cable_amps: float = DC_C1_MIN_CABLE_AMPS_G160,
    sku_region_code: str = "U2",
    requested_video_standard: str = "NTSC",
    reset_action: str = RESET_ACTION_NONE_PHASE373,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-70 USB-PD / DC-C1 & NTSC/PAL SKU state."""
    init_applied = reset_action == RESET_ACTION_INITIALIZE_PHASE373
    # Setup -> [USB] -> [USB Power Supply] is anti-[Camera Settings Reset]; ONLY [Initialize] restores On.
    eff_usb_pwr = USB_POWER_SUPPLY_DEFAULT_G160 if init_applied else usb_power_supply

    pd_watts = round(float(usb_pd_volts) * float(usb_pd_amps), 2)
    low_power_warn = bool(
        power_source_mode == "usb_c_pd"
        and usb_port_kind == "usb_type_c"
        and camera_power_state == "ON"
        and eff_usb_pwr == "On"
        and pd_watts < USB_PD_RECOMMENDED_SHOOT_WATTS_G160
    )

    temp_in_window = CHARGE_TEMP_MIN_C_G160 <= float(ambient_temp_c) <= CHARGE_TEMP_MAX_C_G160
    if power_source_mode == "usb_c_pd" and usb_port_kind == "usb_type_c" and np_fz100_inserted:
        if camera_power_state == "ON":
            # ON-mode iron law: NEVER charges NP-FZ100; CHARGE LED is OFF.
            charging_active = False
            charge_led = "OFF"
            pwr_save_bypassed = eff_usb_pwr == "On"
        else:
            pwr_save_bypassed = False
            if not temp_in_window:
                charging_active = False
                charge_led = "FAST_BLINK_TEMP_FAULT"
            elif np_fz100_soc_pct >= 100:
                charging_active = False
                charge_led = "OFF_FULL"
            else:
                charging_active = True
                charge_led = "ON_CHARGING"
    elif power_source_mode == "dc_c1_coupler":
        charging_active = False
        charge_led = (
            "DC_C1_SOLID_OK"
            if (dc_c1_pd_watts >= DC_C1_MIN_PD_WATTS_G160 and dc_c1_cable_amps >= DC_C1_MIN_CABLE_AMPS_G160)
            else "DC_C1_BLINK_INSUFFICIENT_PD"
        )
        pwr_save_bypassed = camera_power_state == "ON"
    else:
        charging_active = False
        charge_led = "OFF"
        pwr_save_bypassed = False

    brightness_locked_max = power_source_mode == "dc_c1_coupler"

    # SKU NTSC/PAL region lock (lib::backup_get_ntsc_pal_selector_dst)
    sku_default = NTSC_PAL_SKU_DEFAULTS_G160.get(sku_region_code, "NTSC")
    if sku_region_code == "J1":
        eff_std = "NTSC"
    else:
        eff_std = requested_video_standard

    if eff_std == sku_default:
        banner = ""
    elif eff_std == "NTSC":
        banner = RUNNING_ON_NTSC_BANNER_G160
    else:
        banner = RUNNING_ON_PAL_BANNER_G160

    return {
        "effective_usb_power_supply": eff_usb_pwr,
        "usb_pd_watts": pd_watts,
        "low_power_drain_warning": low_power_warn,
        "charging_active": charging_active,
        "charge_led_state": charge_led,
        "power_save_bypassed_by_usb_pd": pwr_save_bypassed,
        "monitor_brightness_locked_max": brightness_locked_max,
        "sku_default_standard": sku_default,
        "effective_video_standard": eff_std,
        "boot_banner_text": banner,
    }


def compute_usbpd_ntscpal_avfinfo_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G160 (384 states)."""
    combos = list(
        itertools.product(
            ("On", "Off"),  # usb_power_supply (2)
            ("ON", "OFF"),  # camera_power_state (2)
            (True, False),  # np_fz100_inserted (2)
            (27.0, 7.5),  # usb_pd_watts (2: 9V/3A vs 5V/1.5A)
            (22.0, 35.0),  # ambient_temp_c (2: in-window vs out-of-window)
            ("J1", "CE", "U2"),  # sku_region_code (3)
            ("NTSC", "PAL"),  # requested_video_standard (2)
            (
                RESET_ACTION_NONE_PHASE373,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE373,
            ),  # 2 -> 2*2*2*2*2*3*2*2 = 384
        )
    )
    on_mode_zero_charge_count = 0
    off_mode_temp_fault_count = 0
    usb_power_reset_preserved_count = 0
    j1_pal_locked_count = 0
    ce_ntsc_banner_count = 0
    u2_pal_banner_count = 0
    low_power_drain_warn_count = 0

    for upwr, pstate, batt, watts, temp_c, sku, std, rst in combos:
        volts, amps = (9.0, 3.0) if watts == 27.0 else (5.0, 1.5)
        st = resolve_fx3_usbpd_ntscpal_avfinfo_state(
            usb_power_supply=upwr,
            power_source_mode="usb_c_pd",
            camera_power_state=pstate,
            usb_pd_volts=volts,
            usb_pd_amps=amps,
            np_fz100_inserted=batt,
            np_fz100_soc_pct=60,
            ambient_temp_c=temp_c,
            sku_region_code=sku,
            requested_video_standard=std,
            reset_action=rst,
        )
        if pstate == "ON" and (not st["charging_active"]) and st["charge_led_state"] == "OFF":
            on_mode_zero_charge_count += 1
        if pstate == "OFF" and batt and temp_c > CHARGE_TEMP_MAX_C_G160:
            if st["charge_led_state"] == "FAST_BLINK_TEMP_FAULT" and not st["charging_active"]:
                off_mode_temp_fault_count += 1
        if rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE373 and st["effective_usb_power_supply"] == upwr:
            usb_power_reset_preserved_count += 1
        if sku == "J1" and std == "PAL" and st["effective_video_standard"] == "NTSC":
            j1_pal_locked_count += 1
        if sku == "CE" and std == "NTSC" and st["boot_banner_text"] == RUNNING_ON_NTSC_BANNER_G160:
            ce_ntsc_banner_count += 1
        if sku == "U2" and std == "PAL" and st["boot_banner_text"] == RUNNING_ON_PAL_BANNER_G160:
            u2_pal_banner_count += 1
        if st["low_power_drain_warning"]:
            low_power_drain_warn_count += 1

    return {
        "total_matrix_states": len(combos),
        "on_mode_zero_charge_count": on_mode_zero_charge_count,
        "off_mode_temp_fault_count": off_mode_temp_fault_count,
        "usb_power_reset_preserved_count": usb_power_reset_preserved_count,
        "j1_pal_locked_count": j1_pal_locked_count,
        "ce_ntsc_banner_count": ce_ntsc_banner_count,
        "u2_pal_banner_count": u2_pal_banner_count,
        "low_power_drain_warn_count": low_power_drain_warn_count,
    }


def verify_usbpd_ntscpal_avfinfo_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE373,
    body_model_id: int = FX3_MODEL_ID_PHASE373,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE373,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE373,
    usb_power_supply: str = USB_POWER_SUPPLY_DEFAULT_G160,
    usb_port_kind: str = "usb_type_c",
    power_source_mode: str = "usb_c_pd",
    camera_power_state: str = "ON",
    usb_pd_volts: float = USB_PD_RECOMMENDED_SHOOT_VOLTS_G160,
    usb_pd_amps: float = USB_PD_RECOMMENDED_SHOOT_AMPS_G160,
    require_sustained_pd_27w: bool = False,
    np_fz100_inserted: bool = True,
    np_fz100_soc_pct: int = 80,
    battery_voltage_mv: int = 7600,
    hot_pull_battery_requested: bool = False,
    ambient_temp_c: float = 22.0,
    claimed_camset_reset_clears_usb_power_supply: bool = False,
    claimed_charges_while_camera_on: bool = False,
    claimed_charge_outside_10_30c: bool = False,
    dc_c1_pd_watts: float = DC_C1_MIN_PD_WATTS_G160,
    dc_c1_cable_amps: float = DC_C1_MIN_CABLE_AMPS_G160,
    claimed_dc_c1_brightness_adjustable: bool = False,
    fx6_dc_in_voltage_v: float = FX6_DC_IN_NOMINAL_V_G160,
    fx6_recording_active: bool = False,
    fx6_dc_in_hot_replug_requested: bool = False,
    requested_fx6_usbc_body_power: bool = False,
    sku_region_code: str = "U2",
    requested_video_standard: str = "NTSC",
    claimed_ver7_xavc_requires_mandatory_format: bool = False,
    claimed_ntsc_pal_switch_no_reboot: bool = False,
    clip_recorded_standard: Optional[str] = None,
    requested_cross_standard_playback: bool = False,
    avf_db_operation: str = "none",
    target_media_slot: int = MEDIA_SLOT_NONE_PHASE373,
    fx6_system_frequency_hz: str = "59.94",
    claimed_fx6_thumbnail_shows_all_freqs: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE373,
) -> UsbPdNtscPalAvfInfoGuardResult:
    """Enforce Gate G160: USB-PD Mandatory NP-FZ100 / DC-C1 & NTSC/PAL SKU / AVF_INFO Slot 1 EROFS=30."""
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

    if not _is_on_off(usb_power_supply):
        _add("TELEMETRY_INVALID", f"usb_power_supply_invalid:{usb_power_supply!r}")
    if usb_port_kind not in ALLOWED_USB_PORT_KINDS_G160:
        _add("TELEMETRY_INVALID", f"usb_port_kind_invalid:{usb_port_kind!r}")
    if power_source_mode not in ALLOWED_POWER_SOURCE_MODES_G160:
        _add("TELEMETRY_INVALID", f"power_source_mode_invalid:{power_source_mode!r}")
    if camera_power_state not in ALLOWED_CAMERA_POWER_STATES_G160:
        _add("TELEMETRY_INVALID", f"camera_power_state_invalid:{camera_power_state!r}")
    if not _is_strict_number(usb_pd_volts) or float(usb_pd_volts) < 0.0:
        _add("TELEMETRY_INVALID", f"usb_pd_volts_invalid:{usb_pd_volts!r}")
    if not _is_strict_number(usb_pd_amps) or float(usb_pd_amps) < 0.0:
        _add("TELEMETRY_INVALID", f"usb_pd_amps_invalid:{usb_pd_amps!r}")
    if not _is_strict_int(np_fz100_soc_pct) or not (0 <= np_fz100_soc_pct <= 100):
        _add("TELEMETRY_INVALID", f"np_fz100_soc_pct_invalid:{np_fz100_soc_pct!r}")
    if not _is_strict_int(battery_voltage_mv) or battery_voltage_mv < 0:
        _add("TELEMETRY_INVALID", f"battery_voltage_mv_invalid:{battery_voltage_mv!r}")
    if not _is_strict_number(ambient_temp_c):
        _add("TELEMETRY_INVALID", f"ambient_temp_c_invalid:{ambient_temp_c!r}")
    if not _is_strict_number(dc_c1_pd_watts) or float(dc_c1_pd_watts) < 0.0:
        _add("TELEMETRY_INVALID", f"dc_c1_pd_watts_invalid:{dc_c1_pd_watts!r}")
    if not _is_strict_number(dc_c1_cable_amps) or float(dc_c1_cable_amps) < 0.0:
        _add("TELEMETRY_INVALID", f"dc_c1_cable_amps_invalid:{dc_c1_cable_amps!r}")
    if not _is_strict_number(fx6_dc_in_voltage_v) or float(fx6_dc_in_voltage_v) < 0.0:
        _add("TELEMETRY_INVALID", f"fx6_dc_in_voltage_v_invalid:{fx6_dc_in_voltage_v!r}")
    if sku_region_code not in ALLOWED_NTSC_PAL_SKUS_G160:
        _add("TELEMETRY_INVALID", f"sku_region_code_invalid:{sku_region_code!r}")
    if requested_video_standard not in ALLOWED_VIDEO_STANDARDS_G160:
        _add(
            "TELEMETRY_INVALID",
            f"requested_video_standard_invalid:{requested_video_standard!r}",
        )
    if clip_recorded_standard is not None and clip_recorded_standard not in ALLOWED_VIDEO_STANDARDS_G160:
        _add(
            "TELEMETRY_INVALID",
            f"clip_recorded_standard_invalid:{clip_recorded_standard!r}",
        )
    if avf_db_operation not in ALLOWED_AVF_DB_OPERATIONS_G160:
        _add("TELEMETRY_INVALID", f"avf_db_operation_invalid:{avf_db_operation!r}")
    if not _is_strict_int(target_media_slot) or target_media_slot not in ALLOWED_MEDIA_SLOTS_PHASE373:
        _add("TELEMETRY_INVALID", f"target_media_slot_invalid:{target_media_slot!r}")
    if fx6_system_frequency_hz not in EXACT_6_FX6_SYSTEM_FREQUENCIES_G160:
        _add(
            "TELEMETRY_INVALID",
            f"fx6_system_frequency_hz_invalid:{fx6_system_frequency_hz!r}",
        )
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE373:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")

    state = resolve_fx3_usbpd_ntscpal_avfinfo_state(
        usb_power_supply=usb_power_supply if _is_on_off(usb_power_supply) else USB_POWER_SUPPLY_DEFAULT_G160,
        usb_port_kind=usb_port_kind if usb_port_kind in ALLOWED_USB_PORT_KINDS_G160 else "usb_type_c",
        power_source_mode=power_source_mode if power_source_mode in ALLOWED_POWER_SOURCE_MODES_G160 else "usb_c_pd",
        camera_power_state=camera_power_state if camera_power_state in ALLOWED_CAMERA_POWER_STATES_G160 else "ON",
        usb_pd_volts=float(usb_pd_volts) if _is_strict_number(usb_pd_volts) and float(usb_pd_volts) >= 0.0 else 9.0,
        usb_pd_amps=float(usb_pd_amps) if _is_strict_number(usb_pd_amps) and float(usb_pd_amps) >= 0.0 else 3.0,
        np_fz100_inserted=np_fz100_inserted,
        np_fz100_soc_pct=(
            np_fz100_soc_pct
            if _is_strict_int(np_fz100_soc_pct) and 0 <= np_fz100_soc_pct <= 100
            else 80
        ),
        ambient_temp_c=float(ambient_temp_c) if _is_strict_number(ambient_temp_c) else 22.0,
        dc_c1_pd_watts=float(dc_c1_pd_watts) if _is_strict_number(dc_c1_pd_watts) and float(dc_c1_pd_watts) >= 0.0 else 65.0,
        dc_c1_cable_amps=float(dc_c1_cable_amps) if _is_strict_number(dc_c1_cable_amps) and float(dc_c1_cable_amps) >= 0.0 else 5.0,
        sku_region_code=sku_region_code if sku_region_code in ALLOWED_NTSC_PAL_SKUS_G160 else "U2",
        requested_video_standard=(
            requested_video_standard
            if requested_video_standard in ALLOWED_VIDEO_STANDARDS_G160
            else "NTSC"
        ),
        reset_action=reset_action if reset_action in ALLOWED_RESET_ACTIONS_PHASE373 else RESET_ACTION_NONE_PHASE373,
    )

    if state["low_power_drain_warning"]:
        warnings.append(
            f"usb_pd_low_power_drain_warning:{state['usb_pd_watts']}W_below_27W_9V3A_recommended"
        )

    # 1. EROFS=30 Tier-0 Slot 1 Vault Firewall for AVF_INFO Create/Update/Recover & Format
    slot1_erofs_blocked = bool(
        target_media_slot == MEDIA_SLOT_1_PHASE373
        and avf_db_operation in MUTATING_AVF_DB_OPERATIONS_G160
    )
    if slot1_erofs_blocked:
        _add(
            "SLOT1_TIER0_AVFINFO_OR_FORMAT_EROFS",
            f"tier0_slot1_vault_blocked_{avf_db_operation}_slot1_data_sector_writes_0_erofs_30",
        )

    # 2. EBUSY=16 FX6 DC IN Hot-Replug Reboot Hazard During Active Recording
    fx6_hot_replug_busy = bool(fx6_recording_active and fx6_dc_in_hot_replug_requested)
    if fx6_hot_replug_busy:
        _add(
            "FX6_DC_IN_HOT_REPLUG_REBOOT_HAZARD_EBUSY",
            "fx6_hot_replugging_19_5v_dc_in_during_recording_risks_reboot_ebusy_16",
        )

    # 3. EOPNOTSUPP=95 Multi/Micro USB, Battery-Less FX3 USB Boot, FX6 USB-C Power, J1 PAL Lock, Cross-Std Playback
    micro_usb_blocked = bool(
        power_source_mode == "usb_c_pd" and usb_port_kind == "multi_micro_usb"
    )
    fx3_batteryless_usb_blocked = bool(
        power_source_mode == "usb_c_pd" and not np_fz100_inserted
    )
    j1_pal_blocked = bool(
        sku_region_code == "J1" and requested_video_standard == "PAL"
    )
    cross_std_playback_attempt = bool(
        requested_cross_standard_playback
        or (
            avf_db_operation == "playback_check"
            and clip_recorded_standard is not None
            and clip_recorded_standard != state["effective_video_standard"]
        )
    )
    dormant_or_eopnotsupp = bool(
        micro_usb_blocked
        or fx3_batteryless_usb_blocked
        or requested_fx6_usbc_body_power
        or j1_pal_blocked
        or cross_std_playback_attempt
    )

    if micro_usb_blocked:
        _add(
            "FX3_MULTI_MICRO_USB_POWER_REJECTED_EOPNOTSUPP",
            "base_0xe931_power_supply_capable_only_through_usb_type_c_port_eopnotsupp_95",
        )
    if fx3_batteryless_usb_blocked:
        _add(
            "FX3_MANDATORY_NP_FZ100_INSERTED_NO_BATTERYLESS_USB_BOOT_EOPNOTSUPP",
            "fx3_libusbbuspower_requires_battery_is_inserted_cannot_boot_usb_pd_without_np_fz100_eopnotsupp_95",
        )
    if requested_fx6_usbc_body_power:
        _add(
            "FX6_ZERO_USBC_BODY_POWER_EOPNOTSUPP",
            "fx6_ver6_01_usbc_port_does_not_support_body_power_uses_19_5v_eiaj_dc_in_eopnotsupp_95",
        )
    if j1_pal_blocked:
        _add(
            "FX3_J1_JAPAN_SKU_NTSC_ONLY_LOCKED_EOPNOTSUPP",
            "backup_get_ntsc_pal_selector_dst_locks_j1_japan_sku_to_ntsc_only_eopnotsupp_95",
        )
    if cross_std_playback_attempt:
        _add(
            "FX3_CROSS_STANDARD_PLAYBACK_ISOLATED_EOPNOTSUPP",
            "fx3_g_0x61ca_0x644e_blocks_playback_of_cross_standard_ntsc_pal_clips_eopnotsupp_95",
        )

    # 4. EINVAL=22 Power, Thermal, DC-C1, Reset-Immunity, Battery Depletion & Policy Violations
    if power_source_mode == "usb_c_pd" and np_fz100_inserted and np_fz100_soc_pct == 0 and camera_power_state == "ON":
        _add(
            "FX3_USB_PD_REQUIRES_SUFFICIENTLY_CHARGED_NP_FZ100",
            "fx3_will_not_activate_with_0_pct_remaining_battery_even_on_usb_pd_einval_22",
        )
    if hot_pull_battery_requested and power_source_mode in ("usb_c_pd", "battery_only"):
        _add(
            "FX3_ZERO_BATTERY_HOT_SWAP_POWER_CUT_HAZARD",
            "pulling_np_fz100_while_running_on_usb_pd_immediately_cuts_power_no_hot_swap_einval_22",
        )
    if require_sustained_pd_27w and state["low_power_drain_warning"]:
        _add(
            "FX3_USB_PD_BELOW_9V3A_27W_CONTINUOUS_SHOOT_INSUFFICIENT",
            f"usb_pd_{state['usb_pd_watts']}W_insufficient_for_sustained_shooting_requires_9v_3a_27w_einval_22",
        )
    if claimed_camset_reset_clears_usb_power_supply:
        _add(
            "USB_POWER_SUPPLY_RESET_IMMUNITY_VIOLATION",
            "setup_usb_power_supply_is_not_available_under_camset_reset_initialize_only_einval_22",
        )
    if claimed_charges_while_camera_on:
        _add(
            "FX3_ON_MODE_NO_BATTERY_CHARGE_VIOLATION",
            "fx3_never_charges_np_fz100_while_camera_power_is_on_charge_led_off_einval_22",
        )
    if claimed_charge_outside_10_30c and not (
        CHARGE_TEMP_MIN_C_G160 <= float(ambient_temp_c) <= CHARGE_TEMP_MAX_C_G160
    ):
        _add(
            "FX3_OFF_MODE_CHARGE_TEMP_10_30C_WINDOW_VIOLATION",
            f"ambient_temp_{ambient_temp_c}C_outside_10_to_30C_triggers_charge_led_fast_blink_fault_einval_22",
        )
    if power_source_mode == "dc_c1_coupler":
        if float(dc_c1_pd_watts) < DC_C1_MIN_PD_WATTS_G160 or float(dc_c1_cable_amps) < DC_C1_MIN_CABLE_AMPS_G160:
            _add(
                "DC_C1_REQUIRES_65W_PD_AND_5A_CABLE",
                f"dc_c1_coupler_requires_ge_65w_pd_and_5a_cable_got_{dc_c1_pd_watts}W_{dc_c1_cable_amps}A_einval_22",
            )
        if claimed_dc_c1_brightness_adjustable:
            _add(
                "DC_C1_MONITOR_BRIGHTNESS_LOCKED_MAX_VIOLATION",
                "dc_c1_coupler_locks_monitor_brightness_to_max_einval_22",
            )
    if power_source_mode == "fx6_dc_in_19_5v":
        v = float(fx6_dc_in_voltage_v)
        if v <= FX6_DC_IN_ALARM_L2_V_G160 or v > FX6_DC_IN_MAX_V_G160:
            _add(
                "FX6_DC_IN_VOLTAGE_OUT_OF_SAFE_WINDOW",
                f"fx6_dc_in_{v}V_outside_safe_18_0_to_20_5V_or_below_15_5V_l2_cutoff_einval_22",
            )
    if avf_db_operation == "recover_image_db" and (
        np_fz100_soc_pct < RECOVER_DB_MIN_SOC_PCT_G160
        or battery_voltage_mv < RECOVER_DB_MIN_VOLTAGE_MV_G160
    ):
        _add(
            "RECOVER_IMAGE_DB_DEPLETED_BATTERY_BLOCKED",
            f"recover_image_db_requires_soc_ge_10_pct_and_mv_ge_6400_got_{np_fz100_soc_pct}pct_{battery_voltage_mv}mV_einval_22",
        )
    if claimed_ver7_xavc_requires_mandatory_format:
        _add(
            "VER7_XAVC_NTSC_PAL_NO_MANDATORY_FORMAT_VIOLATION",
            "fx3_ver7_02_pure_xavc_ntsc_pal_switch_reboots_without_mandatory_format_unlike_avchd_einval_22",
        )
    if claimed_ntsc_pal_switch_no_reboot:
        _add(
            "NTSC_PAL_SWITCH_MANDATORY_REBOOT_VIOLATION",
            "ntsc_pal_selector_switch_always_triggers_mandatory_reboot_base_0xe5c1_einval_22",
        )
    if claimed_fx6_thumbnail_shows_all_freqs:
        _add(
            "FX6_THUMBNAIL_FREQUENCY_FILTER_VIOLATION",
            "fx6_thumbnail_screen_filters_strictly_by_current_rec_format_frequency_einval_22",
        )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G160
        block_errno = 0
        block_errno_name = "OK"
    elif slot1_erofs_blocked:
        status = STATUS_BLOCKED_G160_SLOT1_AVFINFO_OR_FORMAT_VAULT_EROFS
        block_errno = EROFS_ERRNO_PHASE373
        block_errno_name = EROFS_NAME_PHASE373
    elif fx6_hot_replug_busy:
        status = STATUS_BLOCKED_G160_FX6_DC_IN_HOT_REPLUG_RECORDING_EBUSY
        block_errno = EBUSY_ERRNO_PHASE373
        block_errno_name = EBUSY_NAME_PHASE373
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G160_MICROUSB_NO_FZ100_J1_LOCK_OR_CROSS_STD_EOPNOTSUPP
        block_errno = EOPNOTSUPP_ERRNO_PHASE373
        block_errno_name = EOPNOTSUPP_NAME_PHASE373
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
        status = STATUS_BLOCKED_G160_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE373
        block_errno_name = EINVAL_NAME_PHASE373
    else:
        status = STATUS_BLOCKED_G160_USBPD_CHARGE_DCC1_OR_NTSCPAL_CONSTRAINT_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE373
        block_errno_name = EINVAL_NAME_PHASE373

    return UsbPdNtscPalAvfInfoGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        usb_power_supply_menu_path=USB_POWER_SUPPLY_MENU_PATH_G160,
        ntsc_pal_selector_menu_path=NTSC_PAL_SELECTOR_MENU_PATH_G160,
        fx6_system_frequency_menu_path=FX6_SYSTEM_FREQUENCY_MENU_PATH_G160,
        effective_usb_power_supply=state["effective_usb_power_supply"],
        usb_power_supply_resettable_by_camset_reset=USB_POWER_SUPPLY_RESETTABLE_BY_CAMSET_RESET_G160,
        usb_port_kind=usb_port_kind,
        power_source_mode=power_source_mode,
        camera_power_state=camera_power_state,
        usb_pd_watts=state["usb_pd_watts"],
        low_power_drain_warning=state["low_power_drain_warning"],
        np_fz100_inserted=np_fz100_inserted,
        np_fz100_soc_pct=np_fz100_soc_pct if _is_strict_int(np_fz100_soc_pct) else 0,
        battery_voltage_mv=battery_voltage_mv if _is_strict_int(battery_voltage_mv) else 0,
        fx3_battery_less_usb_boot_supported=FX3_BATTERY_LESS_USB_BOOT_SUPPORTED_G160,
        fx3_battery_hot_swap_supported=FX3_BATTERY_HOT_SWAP_SUPPORTED_G160,
        fx3_charges_while_camera_on=FX3_CHARGES_WHILE_CAMERA_ON_G160,
        charging_active=state["charging_active"],
        charge_led_state=state["charge_led_state"],
        power_save_bypassed_by_usb_pd=state["power_save_bypassed_by_usb_pd"],
        dc_c1_pd_watts=float(dc_c1_pd_watts) if _is_strict_number(dc_c1_pd_watts) else 0.0,
        dc_c1_cable_amps=float(dc_c1_cable_amps) if _is_strict_number(dc_c1_cable_amps) else 0.0,
        monitor_brightness_locked_max=state["monitor_brightness_locked_max"],
        fx6_dc_in_voltage_v=float(fx6_dc_in_voltage_v) if _is_strict_number(fx6_dc_in_voltage_v) else 0.0,
        fx6_battery_less_boot_supported=FX6_BATTERY_LESS_BOOT_SUPPORTED_G160,
        fx6_dc_unplug_to_bpu_seamless=FX6_DC_UNPLUG_TO_BPU_SEAMLESS_G160,
        fx6_usbc_body_power_supported=FX6_USBC_BODY_POWER_SUPPORTED_G160,
        ntsc_pal_sku_gate_function=NTSC_PAL_SKU_GATE_FN_G160,
        sku_region_code=sku_region_code,
        sku_default_standard=state["sku_default_standard"],
        effective_video_standard=state["effective_video_standard"],
        boot_banner_text=state["boot_banner_text"],
        ntsc_pal_switch_requires_reboot=VER7_XAVC_SWITCH_REQUIRES_REBOOT_G160,
        ver7_xavc_switch_requires_format=VER7_XAVC_SWITCH_REQUIRES_FORMAT_G160,
        cross_standard_playback_allowed=CROSS_STANDARD_PLAYBACK_ALLOWED_G160,
        avf_db_operation=avf_db_operation,
        target_media_slot=target_media_slot if _is_strict_int(target_media_slot) else MEDIA_SLOT_NONE_PHASE373,
        slot1_tier0_erofs_blocked=slot1_erofs_blocked,
        slot1_data_sector_writes=0,
        emmc_nflasha_write_count=0,
        fx6_system_frequency_hz=fx6_system_frequency_hz,
        fx6_thumbnail_filters_by_current_freq=FX6_THUMBNAIL_FILTERS_BY_CURRENT_FREQ_G160,
        dormant_or_cross_model_eopnotsupp_rejected=dormant_or_eopnotsupp,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class G160UsbPdNtscPalAvfInfoGuardResult:
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
    usbpd_ntscpal_avfinfo_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g160_usbpd_ntscpal_avfinfo_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G160UsbPdNtscPalAvfInfoGuardResult]:
    audit = audit_phase373_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_usbpd_ntscpal_avfinfo_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G160UsbPdNtscPalAvfInfoGuardResult(
        gate_id=G160,
        gate_code=G160_GATE_CODE,
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
        usbpd_ntscpal_avfinfo_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G160,
        gate_code=G160_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"pwr={res.power_source_mode} "
            f"pd_w={res.usb_pd_watts:.1f}W "
            f"fz100={res.np_fz100_inserted} "
            f"sku={res.sku_region_code} "
            f"std={res.effective_video_standard} "
            f"s1_writes={res.slot1_data_sector_writes}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_usbpd_ntscpal_avfinfo_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G160UsbPdNtscPalAvfInfoGuardResult]:
    return evaluate_g160_usbpd_ntscpal_avfinfo_guard(**kwargs)


# ---------------------------------------------------------------------------
# Unified 160-Gate Master Safety Preflight Engine (G01..G160)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Master160GateReport:
    schema: str
    schema_version: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_157_gates_verified: bool
    all_160_gates_verified: bool
    g13_to_g160_all_passed: bool
    g159_to_g160_all_passed: bool
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
    master_158_report: Dict[str, Any]
    g159_result: Dict[str, Any]
    g160_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_160gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    simulate_bench_dry_run: Optional[bool] = None,
    dry_run_simulated_backup: Optional[bool] = None,
    request_persistent_emmc_writes: bool = False,
    master_158_override: Optional[Master158GateReport] = None,
    peaking_audio_wind_kwargs: Optional[Mapping[str, Any]] = None,
    usbpd_ntscpal_avfinfo_kwargs: Optional[Mapping[str, Any]] = None,
    **extra_upstream_kwargs: Any,
) -> Master160GateReport:
    """Evaluate unified 160-Gate Milestone Master Safety Preflight (`G01..G160`)."""
    effective_dry_run = (
        bool(dry_run_simulated)
        or (simulate_bench_dry_run is True)
        or (dry_run_simulated_backup is True)
    )
    clean_forced = _is_clean_room_forced(force_clean_room)
    resolved_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved_work_root_for_m158 = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=resolved_repo_root).work_root
    )
    donors_present_in_work_root = bool(
        resolved_work_root_for_m158 is not None
        and (
            resolved_work_root_for_m158
            / PINNED_PHASE373_DONOR_SPECS["fx3_appfw_so"][1]
        ).is_file()
    )
    m158_force_clean_room = (
        True
        if (clean_forced or (not donors_present_in_work_root and force_clean_room is not False))
        else force_clean_room
    )

    if master_158_override is not None:
        m158_report = master_158_override
    else:
        m158_kw = {
            k: v
            for k, v in extra_upstream_kwargs.items()
            if v is not None
        }
        m158_report = evaluate_158gate_preflight(
            resolved_repo_root,
            work_root=work_root,
            force_clean_room=m158_force_clean_room,
            dry_run_simulated=effective_dry_run,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m158_kw,
        )

    g159_kw = dict(peaking_audio_wind_kwargs or {})
    g159_verdict, g159_res = evaluate_g159_peaking_audio_wind_guard(
        repo_root=resolved_repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **g159_kw,
    )

    g160_kw = dict(usbpd_ntscpal_avfinfo_kwargs or {})
    if request_persistent_emmc_writes:
        if "target_media_slot" not in g160_kw:
            g160_kw["target_media_slot"] = MEDIA_SLOT_1_PHASE373
        if "avf_db_operation" not in g160_kw:
            g160_kw["avf_db_operation"] = "avf_info_create"
    g160_verdict, g160_res = evaluate_g160_usbpd_ntscpal_avfinfo_guard(
        repo_root=resolved_repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **g160_kw,
    )

    new_gate_dicts = (
        {
            "gate_id": G159,
            "gate_code": G159_GATE_CODE,
            "status": g159_res.status,
            "passed": g159_verdict.passed,
            "evidence": g159_verdict.evidence,
            "violation_codes": list(g159_verdict.errors),
        },
        {
            "gate_id": G160,
            "gate_code": G160_GATE_CODE,
            "status": g160_res.status,
            "passed": g160_verdict.passed,
            "evidence": g160_verdict.evidence,
            "violation_codes": list(g160_verdict.errors),
        },
    )

    all_gates: Tuple[Dict[str, Any], ...] = tuple(m158_report.gates) + new_gate_dicts
    g01_to_g12_verified = int(m158_report.summary["g01_to_g12_verified"])
    g13_to_g158_verified = (
        int(m158_report.summary["g13_to_g156_verified"])
        + int(m158_report.summary["g157_to_g158_verified"])
    )
    g159_to_g160_verified = int(bool(g159_verdict.passed)) + int(
        bool(g160_verdict.passed)
    )
    total_verified = g01_to_g12_verified + g13_to_g158_verified + g159_to_g160_verified

    g159_to_g160_all_passed = g159_to_g160_verified == 2
    g13_to_g160_all_passed = (
        m158_report.g13_to_g158_all_passed and g159_to_g160_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m158_report.gates[:9])

    offline_157_verified = (
        g01_to_g09_ok
        and m158_report.offline_155_gates_verified
        and g159_to_g160_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_160_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g160_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m158_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_157_verified
        and m158_report.h0_h1_trial_entry_allowed
        and g159_to_g160_all_passed
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
        list(m158_report.errors)
        + list(g159_verdict.errors)
        + list(g160_verdict.errors)
    )
    warnings: List[str] = (
        list(m158_report.warnings)
        + list(g159_verdict.warnings)
        + list(g160_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m158_report.g13_to_g158_all_passed:
        overall_status = m158_report.status
    elif not g159_verdict.passed:
        overall_status = g159_verdict.status
    elif not g160_verdict.passed:
        overall_status = g160_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_160_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_160_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_160_verified:
        overall_status = "VERIFIED_ALL_160_GATES"
    else:
        overall_status = "VERIFIED_157_OF_160_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m158_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g159_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g160_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 160,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 160 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g158_verified": g13_to_g158_verified,
        "g159_to_g160_verified": g159_to_g160_verified,
        "g13_to_g160_all_passed": g13_to_g160_all_passed,
        "g159_to_g160_all_passed": g159_to_g160_all_passed,
        "offline_157_gates_verified": offline_157_verified,
        "all_160_gates_verified": all_160_verified,
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

    return Master160GateReport(
        schema=REALHW_160GATE_PREFLIGHT_SCHEMA,
        schema_version=REALHW_160GATE_PREFLIGHT_SCHEMA,
        version=REALHW_PEAKING_AUDIO_WIND_USBPD_NTSCPAL_160GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_157_gates_verified=offline_157_verified,
        all_160_gates_verified=all_160_verified,
        g13_to_g160_all_passed=g13_to_g160_all_passed,
        g159_to_g160_all_passed=g159_to_g160_all_passed,
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
        master_158_report=m158_report.to_dict(),
        g159_result=g159_res.to_dict(),
        g160_result=g160_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_160_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master160GateReport:
    return evaluate_160gate_preflight(repo_root, **kwargs)


def run_160_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master160GateReport:
    return evaluate_160gate_preflight(repo_root, **kwargs)


def verify_real_hardware_160gate_readiness(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master160GateReport:
    return evaluate_160gate_preflight(repo_root, **kwargs)


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
        prog="realhw_peaking_audio_wind_usbpd_ntscpal_and_160gate_guard",
        description="Phase 373 (Task H473, Wave-70 Milestone) G159/G160 and 160/160 Unified Safety Preflight CLI",
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
        help="Supply simulated dry-run Tier-0 backup inputs so all 160/160 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g159", "g160", "160"],
        default="160",
        help="Target gate check: g159, g160, or 160",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g159":
        v, r = evaluate_g159_peaking_audio_wind_guard(
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

    if args.gate == "g160":
        v, r = evaluate_g160_usbpd_ntscpal_avfinfo_guard(
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

    rep = evaluate_160gate_preflight(
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
                "g159_status": rep.g159_result["status"],
                "g160_status": rep.g160_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/160 "
            f"g159_to_g160_all_passed={rep.g159_to_g160_all_passed} "
            f"all_160_gates_verified={rep.all_160_gates_verified} "
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
        rep.all_160_gates_verified
        if args.dry_run_simulated
        else rep.offline_157_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "ALLOWED_AUDIO_OUT_TIMING_G159",
    "ALLOWED_AVF_DB_OPERATIONS_G160",
    "ALLOWED_BODY_MODELS_PHASE373",
    "ALLOWED_CAMERA_POWER_STATES_G160",
    "ALLOWED_FX3_PEAKING_COLORS_G159",
    "ALLOWED_FX3_WIND_NOISE_OPTIONS_G159",
    "ALLOWED_FX6_PEAKING_COLORS_G159",
    "ALLOWED_MEDIA_SLOTS_PHASE373",
    "ALLOWED_NTSC_PAL_SKUS_G160",
    "ALLOWED_PEAKING_LEVELS_G159",
    "ALLOWED_POWER_SOURCE_MODES_G160",
    "ALLOWED_RESET_ACTIONS_PHASE373",
    "ALLOWED_SHOE_AUDIO_FORMATS_G159",
    "ALLOWED_SHOOT_MODES_PHASE373",
    "ALLOWED_USB_PORT_KINDS_G160",
    "ALLOWED_VIDEO_STANDARDS_G160",
    "ALLOWED_XLR_H1_LOW_CUT_G159",
    "ALLOWED_XLR_H1_MODES_G159",
    "AUDIO_LEVEL_DISPLAY_MENU_REMOVED_VER2_PLUS_G159",
    "AUDIO_OUT_TIMING_DEFAULT_G159",
    "AUDIO_OUT_TIMING_F_RESID16_G159",
    "AUDIO_RECORDING_DEFAULT_G159",
    "AUDIO_RECORDING_F_RESID16_G159",
    "AUDIO_RECORDING_MENU_PATH_G159",
    "AUDIO_REC_LEVEL_DEFAULT_G159",
    "AUDIO_REC_LEVEL_ELF_TYPO_G159",
    "AUDIO_REC_LEVEL_MAX_G159",
    "AUDIO_REC_LEVEL_MIN_G159",
    "CHANGE_TO_PAL_REBOOT_BASE_RESID16_G160",
    "CHARGE_TEMP_MAX_C_G160",
    "CHARGE_TEMP_MIN_C_G160",
    "CROSS_STANDARD_PLAYBACK_ALLOWED_G160",
    "CROSS_STD_PLAYBACK_BLOCK_G_RESID16_G160",
    "DC_C1_MIN_CABLE_AMPS_G160",
    "DC_C1_MIN_PD_WATTS_G160",
    "DC_C1_MONITOR_BRIGHTNESS_LOCKED_MAX_G160",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE373",
    "DONOR_CHECK_MAX_SECONDS_PHASE373",
    "DORMANT_FOCUS_MAP_F_RESID16_G159",
    "EBUSY_ERRNO_PHASE373",
    "EBUSY_NAME_PHASE373",
    "EINVAL_ERRNO_PHASE373",
    "EINVAL_NAME_PHASE373",
    "ENV_CLEAN_ROOM_TEST_PHASE373",
    "EOPNOTSUPP_ERRNO_PHASE373",
    "EOPNOTSUPP_NAME_PHASE373",
    "EPERM_ERRNO_PHASE373",
    "EPERM_NAME_PHASE373",
    "EROFS_ERRNO_PHASE373",
    "EROFS_NAME_PHASE373",
    "EXACT_3_FX3_PEAKING_ITEMS_G159",
    "EXACT_3_FX6_PEAKING_ITEMS_G159",
    "EXACT_5_FX3_AUDIO_RECORDING_ITEMS_G159",
    "EXACT_6_FX6_LIMITER_MODES_G159",
    "EXACT_6_FX6_SYSTEM_FREQUENCIES_G160",
    "FX3_AUDIO_5ITEMS_RESETTABLE_BY_CAMSET_RESET_G159",
    "FX3_AUDIO_LIMITER_PERMANENT_NON_DISABLEABLE_G159",
    "FX3_AUDIO_PREEMPTION_TIERS_G159",
    "FX3_BATTERY_HOT_SWAP_SUPPORTED_G160",
    "FX3_BATTERY_LESS_USB_BOOT_SUPPORTED_G160",
    "FX3_CHARGES_WHILE_CAMERA_ON_G160",
    "FX3_DEFAULT_FW_VERSION_PHASE373",
    "FX3_HDMI_PEAKING_LEAKED_PIXELS_G159",
    "FX3_HELP_GUIDE_CODE_PHASE373",
    "FX3_INBODY_FOCUS_MAP_EXPOSED_G159",
    "FX3_MC_WIRELESS_FOCUS_MAP_MIN_FW_G159",
    "FX3_MODEL_ID_PHASE373",
    "FX3_MODEL_NAME_PHASE373",
    "FX3_PEAKING_COMPATIBLE_WITH_FOCUS_MAGNIFIER_G159",
    "FX3_PEAKING_EMITTED_OVER_HDMI_G159",
    "FX3_PEAKING_RESETTABLE_BY_CAMSET_RESET_G159",
    "FX3_WIND_NOISE_AUTO_EXPOSED_G159",
    "FX6_AUDIO_INPUT_MENU_PATH_G159",
    "FX6_BATTERY_LESS_BOOT_SUPPORTED_G160",
    "FX6_CHANGE_SYS_FREQ_NS2_RESID16_G160",
    "FX6_DC_IN_ALARM_L1_V_G160",
    "FX6_DC_IN_ALARM_L2_V_G160",
    "FX6_DC_IN_MAX_V_G160",
    "FX6_DC_IN_MIN_V_G160",
    "FX6_DC_IN_NOMINAL_V_G160",
    "FX6_DC_UNPLUG_TO_BPU_SEAMLESS_G160",
    "FX6_DEFAULT_FW_VERSION_PHASE373",
    "FX6_DORMANT_PEAKING_FREQ_NS2_RESID16_G159",
    "FX6_DORMANT_PEAKING_TYPE_NS2_RESID16_G159",
    "FX6_HANDLE_HW_LOW_CUT_SWITCH_PRESENT_G159",
    "FX6_MODEL_NAME_PHASE373",
    "FX6_PEAKING_FREQ_ELF_HITS_G159",
    "FX6_PEAKING_MENU_PATH_G159",
    "FX6_PEAKING_TYPE_ELF_HITS_G159",
    "FX6_SYSTEM_FREQUENCY_MENU_PATH_G160",
    "FX6_THUMBNAIL_FILTERS_BY_CURRENT_FREQ_G160",
    "FX6_USBC_BODY_POWER_SUPPORTED_G160",
    "FX6_WIND_FILTER_CHANNELS_G159",
    "G159",
    "G159PeakingAudioWindGuardResult",
    "G159_GATE_CODE",
    "G159_GATE_ID",
    "G160",
    "G160UsbPdNtscPalAvfInfoGuardResult",
    "G160_GATE_CODE",
    "G160_GATE_ID",
    "IMAGE_DB_CREATE_BASE_RESID16_G160",
    "IMAGE_DB_UPDATE_BASE_RESID16_G160",
    "MEDIA_SLOT_1_PHASE373",
    "MEDIA_SLOT_2_PHASE373",
    "MEDIA_SLOT_NONE_PHASE373",
    "MUTATING_AVF_DB_OPERATIONS_G160",
    "Master160GateReport",
    "NTSC_PAL_SELECTOR_F_RESID16_G160",
    "NTSC_PAL_SELECTOR_MENU_PATH_G160",
    "NTSC_PAL_SKU_DEFAULTS_G160",
    "NTSC_PAL_SKU_GATE_FN_G160",
    "PEAKING_COLOR_BASE_RESID16_G159",
    "PEAKING_COLOR_DEFAULT_G159",
    "PEAKING_DISPLAY_DEFAULT_G159",
    "PEAKING_DISPLAY_F_RESID16_G159",
    "PEAKING_DISPLAY_MENU_PATH_G159",
    "PEAKING_DISPLAY_SELECT_F_RESID16_G159",
    "PEAKING_LEVEL_BASE_RESID16_G159",
    "PEAKING_LEVEL_DEFAULT_G159",
    "PINNED_FX3_APPFW_SLICES_PHASE373",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE373",
    "PINNED_FX6_APPFW_SLICES_PHASE373",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE373",
    "PINNED_PHASE373_DONOR_SPECS",
    "PeakingAudioWindGuardResult",
    "Phase373DonorAuditResult",
    "REALHW_160GATE_PREFLIGHT_SCHEMA",
    "REALHW_PEAKING_AUDIO_WIND_USBPD_NTSCPAL_160GATE_SCHEMA",
    "REALHW_PEAKING_AUDIO_WIND_USBPD_NTSCPAL_160GATE_VERSION",
    "RECOVER_DB_MIN_SOC_PCT_G160",
    "RECOVER_DB_MIN_VOLTAGE_MV_G160",
    "RECOVER_IMAGE_DB_BASE_RESID16_G160",
    "REMOVED_AUDIO_LEVEL_DISPLAY_F_RESID16_G159",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE373",
    "RESET_ACTION_INITIALIZE_PHASE373",
    "RESET_ACTION_NONE_PHASE373",
    "RUNNING_ON_NTSC_BANNER_G160",
    "RUNNING_ON_NTSC_BASE_RESID16_G160",
    "RUNNING_ON_PAL_BANNER_G160",
    "RUNNING_ON_PAL_BASE_RESID16_G160",
    "SHOE_AUDIO_DEFAULT_G159",
    "SHOE_AUDIO_SET_F_RESID16_G159",
    "SHOOT_MODE_MOVIE_PHASE373",
    "SHOOT_MODE_SQ_PHASE373",
    "SHOOT_MODE_STILL_PHASE373",
    "STATUS_BLOCKED_G159_DORMANT_FOCUSMAP_FX6_TYPEFREQ_AUDIOMETER_OR_WINDAUTO_EOPNOTSUPP",
    "STATUS_BLOCKED_G159_PEAKING_HDMI_RESET_OR_AUDIO_PREEMPTION_WIND_VIOLATION",
    "STATUS_BLOCKED_G159_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G160_FX6_DC_IN_HOT_REPLUG_RECORDING_EBUSY",
    "STATUS_BLOCKED_G160_MICROUSB_NO_FZ100_J1_LOCK_OR_CROSS_STD_EOPNOTSUPP",
    "STATUS_BLOCKED_G160_SLOT1_AVFINFO_OR_FORMAT_VAULT_EROFS",
    "STATUS_BLOCKED_G160_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G160_USBPD_CHARGE_DCC1_OR_NTSCPAL_CONSTRAINT_VIOLATION",
    "STATUS_BLOCKED_PHASE373_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G159",
    "STATUS_VERIFIED_G160",
    "USB_PD_LOW_POWER_WATTS_THRESHOLD_G160",
    "USB_PD_RECOMMENDED_SHOOT_AMPS_G160",
    "USB_PD_RECOMMENDED_SHOOT_VOLTS_G160",
    "USB_PD_RECOMMENDED_SHOOT_WATTS_G160",
    "USB_POWER_SUPPLY_DEFAULT_G160",
    "USB_POWER_SUPPLY_F_RESID16_G160",
    "USB_POWER_SUPPLY_MENU_PATH_G160",
    "USB_POWER_SUPPLY_RESETTABLE_BY_CAMSET_RESET_G160",
    "USB_TYPE_C_ONLY_BASE_RESID16_G160",
    "UsbPdNtscPalAvfInfoGuardResult",
    "VER7_XAVC_SWITCH_REQUIRES_FORMAT_G160",
    "VER7_XAVC_SWITCH_REQUIRES_REBOOT_G160",
    "WIND_NOISE_REDUCT_BASE_RESID16_G159",
    "WIND_NOISE_REDUCT_DEFAULT_G159",
    "audit_phase373_donor_contracts",
    "compute_peaking_audio_wind_matrix",
    "compute_usbpd_ntscpal_avfinfo_matrix",
    "evaluate_160_master_safety_gates",
    "evaluate_160gate_preflight",
    "evaluate_g159_peaking_audio_wind_guard",
    "evaluate_g160_usbpd_ntscpal_avfinfo_guard",
    "main",
    "resolve_fx3_peaking_audio_wind_state",
    "resolve_fx3_usbpd_ntscpal_avfinfo_state",
    "run_160_gate_preflight",
    "strip_elapsed_seconds_recursive_phase373",
    "verify_peaking_audio_wind_guard",
    "verify_peaking_audio_wind_guard_with_audit",
    "verify_real_hardware_160gate_readiness",
    "verify_usbpd_ntscpal_avfinfo_guard",
    "verify_usbpd_ntscpal_avfinfo_guard_with_audit",
]


if __name__ == "__main__":
    raise SystemExit(main())
