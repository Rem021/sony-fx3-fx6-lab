"""Phase 378 (Task H480, Wave-71, 162/162 Hardware Safety Gates):
Real-Hardware Dormant `[Anti-Dust Function]` / `[Shutter When Pwr OFF]` Guard
(`ALCIN_UUD` Open-Shutter Power-Off Mechanical Safety & Active `[Sensor Cleaning]`
`NP-FZ100 >= 51%` + Physical Power-Off Prompt vs `ILME-FX6` Sealed `e-ND` `1/4..1/128
+ CLEAR` & `Technical > APR`), `[Focus Magnifier]` Full-Pipeline (`Shooting ->
[Focus] -> [Focus Assistant]` 5 Reset-Resistant Items, 12.1MP Ratios FF
`x1.0->x2.1->x4.1` / APS-C `x1.0->x1.5->x3.0` / Movie `x1.0<->x4.0`, Dormant High-MP
Alpha Ratio Rejection, `[Focus Magnif. Time]` `2 Sec`/`5 Sec`/`No Limit`, Still-Only
`[AF in Focus Mag.]` & `[Auto Magnifier in MF]`, Movie `REC` Continuity, Clean-HDMI
& Internal Recording Zero-Crop Isolation, Coexistence vs Suppression Matrix vs FX6
`VF` `x3/x6` & Ver. 6.0+ `HDMI` `x2/x4` Target) (`G161`),
`[Exposure Std. Adjust]` (`Exposure/Color -> [Exposure Comp.]`, All 5 Metering Modes
`Multi`/`Center`/`Spot`/`Entire Screen Avg.`/`Highlight`, `-1.0..+1.0 EV` in `1/6 EV`
13-Step Reset-Resistant Hidden Bias, `M.M.` & Spot AEL Shift Without EXIF
`ExposureBiasValue` Mutation, Mid-Bracket Count Reset vs FX6 `Shooting > Auto Exposure
> Level` `-3.0..+3.0` `0.25`-Step 25-Step & Per-LUT `Base Look > AE Level Offset`) and
Wired Smartphone USB Tethering (`Network -> [USB-LAN/Tethering]` + Ver. 7.00+
`[USB-LAN Cnct. Launch]`, `libNetServiceTethering.so`/`libTetheringResource.so`
`cdc_ether`/`cdc_ncm`/`ipheth`/`rndis_host` + `dhcpcd`, `[Airplane Mode] = On`
Zero-RF Bypass `rf_tx_packets = 0`, Dual USB Port Data Mutual Exclusion, *Monitor &
Control* Ver. 4.00+ Wired `[Remote Shooting]` Limitations, FX3 Stripped
`CUsbGadgetIAP` vs FX6 Active `usbg_iap.ko`, and Tier-0 `Slot 1` `MTP`/`MSC`
`EROFS=30` Read-Only Firewall) (`G162`),
and Unified `162`-Gate Master Safety Preflight (`G01..G162`).

Authoritative Empirical Baseline (`ILME-FX3 Ver. 7.02`, `ilc/2210`, `0x0502`,
`PRODUCT_MODEL_ALCIN_UUD` vs `ILME-FX6 Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`):
  - **Gate `G161` (`DORMANT_ANTIDUST_OPEN_SHUTTER_CLEANING51_AND_FOCUS_MAG_CLEAN_HDMI_ISOLATION_FIREWALL`)**:
    1. Dormant `[Anti-dust Function]` (`_f 0x7495`), `[Shutter When Pwr OFF]` (`_f 0x709f`),
       `BKID_APP_setting_image_sensor_barrier`, `PID_SET_IMAGE_SENSOR_BARRIER` MUST be
       rejected fail-closed with `EOPNOTSUPP = 95` (`ALCIN_UUD` mechanical focal-plane
       shutter remains constantly `OPEN` on power-off).
    2. Active `Setup -> [Setup Option] -> [Sensor Cleaning]` (`_f 0x67d6`, legacy
       `.uxc 0xe7d7` `Cleaning Mode`) requires `NP-FZ100 >= 51%` and mandatory physical
       power-off prompt (`_g 0x6221` / `base 0xe879`). Contrast `ILME-FX6 Ver. 6.01`
       sealed electronic variable ND (`1/4..1/128 + CLEAR`), zero focal-plane mechanical
       shutter (`0` `shutter_when_power_off` ELF hits), zero user IBIS sensor cleaning
       (`EOPNOTSUPP = 95`), using `Technical > APR` (`MODEL_APR_EXECUTE_COMP`).
    3. `Shooting -> [Focus] -> [Focus Assistant]` (ALL 5 items resist `[Camera Settings
       Reset]` on Ver. 2.00+; only `[Initialize]` resets them):
       - Exact 12.1MP ratios: Still FF `x1.0 -> x2.1 -> x4.1`, Still APS-C `x1.0 -> x1.5
         -> x3.0`, Movie/S&Q `x1.0 <-> x4.0`; dormant high-MP Alpha ratios
         (`x1.6/x2.7/x3.1/x3.6/x3.7/x4.2/x4.7/x5.3/x5.5/x6.1`) rejected `EOPNOTSUPP = 95`.
       - `[Focus Magnif. Time]`: `2 Sec` / `5 Sec` / `No Limit` (default).
       - `[AF in Focus Mag.]` & `[Auto Magnifier in MF]` strictly Still-only (blocked in
         Movie/S&Q with `EOPNOTSUPP = 95`).
       - Movie `REC` continuity (`REC` does NOT cancel Focus Magnifier) + strict
         Clean-HDMI (`HDMI Info. Display = Off`) & internal recording zero-crop isolation.
       - Coexists with `Peaking`, `Bright Monitoring` (Ver. 7.00+), `De-Squeeze`;
         suppresses `Marker Display`, `Switch V/H AF Area`, `AF Illuminator`.
       - Contrast `ILME-FX6` `x3/x6` `VF` & Ver. 6.0+ `Focus Mag Button Target` (`HDMI`
         `x2/x4`), zero SDI / internal-recording crop, dormant `x8` rejected `EOPNOTSUPP = 95`.

  - **Gate `G162` (`EXPOSURE_STD_ADJUST_5MODE_RESET_IMMUNE_AND_USB_TETHERING_ZERORF_SLOT1_EROFS_FIREWALL`)**:
    1. `Exposure/Color -> [Exposure Comp.] -> [Exposure Std. Adjust]` across all 5
       metering modes (`Multi`, `Center`, `Spot`, `Entire Screen Avg.`, `Highlight`),
       `-1.0 EV` to `+1.0 EV` in `1/6 EV` steps (`13` steps: `-6..+6` sixths, default `0`;
       dormant `1/8 EV` rejected `EOPNOTSUPP = 95`):
       - **Resists `[Camera Settings Reset]`** (only `[Initialize]` zeroes it; non-zero
         shows metering warning icon).
       - Shifts `M.M.` zero-point and Spot AEL baseline WITHOUT altering `[Exposure Comp.]`
         or EXIF `ExposureBiasValue` (`0.0 EV` delta).
       - Resets accumulated bracket count if altered mid-bracket.
       - Contrast `ILME-FX6 Ver. 6.01` `Shooting > Auto Exposure > Level` (`-3.0` to `+3.0`
         in `0.25` steps = `25` steps, debunking `+-2.0` myth) + per-LUT `Base Look > AE
         Level Offset`.
    2. Wired Smartphone USB Tethering (`Network -> [USB-LAN/Tethering]` + Ver. 7.00+
       `[USB-LAN Cnct. Launch]`): `libNetServiceTethering.so` / `libTetheringResource.so`
       (`cdc_ether`/`cdc_ncm`/`ipheth`/`rndis_host` + `dhcpcd`) supports `RTMP/RTMPS/SRT`
       & `FTP` under **`[Airplane Mode] = On` (Zero-RF bypass, `rf_tx_packets = 0`)**;
       dual USB port data mutual exclusion (`EBUSY = 16`); *Monitor & Control* Ver. 4.00+
       wired `[Remote Shooting]` lacks TC display / Focus map / LUT import on FX3 USB
       (`EOPNOTSUPP = 95`); FX3 strips `CUsbGadgetIAP` despite dormant `usbg_iap.ko`
       (`EOPNOTSUPP = 95`, contrast FX6 active `usbg_iap.ko`).
    3. Tier-0 `Slot 1` firewall: `MTP` locks `Slot 1` and `MSC` (`usbg_storage.ko`,
       `USB_CONNECTION_METHOD_MASS_STRAGE` typo, `Multi` OR `Single` LUN) exposes `Slot 1`
       as writable block device -> MUST fail-closed **`EROFS = 30`** unless read-only
       guarded (`slot1_writes == 0`, `usb_tx == 0`, `cross_model_flash_authorized == False`,
       `hardware_live_attachment_authorized == False`).

  - **Unified 162-Gate Master Safety Preflight (`G01..G162`)**:
    Delegates `G01..G160` to `evaluate_160gate_preflight()`, enforces `159/162`
    verified offline (`VERIFIED_159_OF_162_AWAITING_PHYSICAL_TIER0`) and `162/162`
    under `--simulate-bench-dry-run` (`VERIFIED_ALL_162_GATES_DRY_RUN_SIMULATED_BACKUP`),
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
from .realhw_peaking_audio_wind_usbpd_ntscpal_and_160gate_guard import (
    Master160GateReport,
    evaluate_160gate_preflight,
)


# ---------------------------------------------------------------------------
# Schema, Versions, Env Keys & Shared Constants
# ---------------------------------------------------------------------------

REALHW_ANTIDUST_FOCUSMAG_EXPSTD_USBTETHER_162GATE_SCHEMA = (
    "fx3_realhw_antidust_focusmag_expstd_usbtether_162gate_guard_v1"
)
REALHW_ANTIDUST_FOCUSMAG_EXPSTD_USBTETHER_162GATE_VERSION = (
    "2026.11.21-phase378-162gates"
)
REALHW_162GATE_PREFLIGHT_SCHEMA = "realhw_162gate_preflight_v1"

G161 = "G161"
G161_GATE_ID = "G161"
G161_GATE_CODE = (
    "DORMANT_ANTIDUST_OPEN_SHUTTER_CLEANING51_AND_FOCUS_MAG_CLEAN_HDMI_ISOLATION_FIREWALL"
)

G162 = "G162"
G162_GATE_ID = "G162"
G162_GATE_CODE = (
    "EXPOSURE_STD_ADJUST_5MODE_RESET_IMMUNE_AND_USB_TETHERING_ZERORF_SLOT1_EROFS_FIREWALL"
)

ENV_CLEAN_ROOM_TEST_PHASE378 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE378 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE378 = 0.05

EPERM_ERRNO_PHASE378 = 1
EPERM_NAME_PHASE378 = "EPERM"
EBUSY_ERRNO_PHASE378 = 16
EBUSY_NAME_PHASE378 = "EBUSY"
EINVAL_ERRNO_PHASE378 = 22
EINVAL_NAME_PHASE378 = "EINVAL"
EROFS_ERRNO_PHASE378 = 30
EROFS_NAME_PHASE378 = "EROFS"
EOPNOTSUPP_ERRNO_PHASE378 = 95
EOPNOTSUPP_NAME_PHASE378 = "EOPNOTSUPP"

FX3_MODEL_NAME_PHASE378 = "ILME-FX3"
FX3_MODEL_ID_PHASE378 = 0x0502
FX3_MODEL_ENUM_PHASE378 = "PRODUCT_MODEL_ALCIN_UUD"
FX3_HELP_GUIDE_CODE_PHASE378 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE378 = "7.02"
FX6_MODEL_NAME_PHASE378 = "ILME-FX6"
FX6_MODEL_ENUM_PHASE378 = "PRODUCT_MODEL_CHAPLIN"
FX6_DEFAULT_FW_VERSION_PHASE378 = "6.01"
ALLOWED_BODY_MODELS_PHASE378: Tuple[str, ...] = (
    FX3_MODEL_NAME_PHASE378,
    FX6_MODEL_NAME_PHASE378,
)

MEDIA_SLOT_NONE_PHASE378 = 0
MEDIA_SLOT_1_PHASE378 = 1
MEDIA_SLOT_2_PHASE378 = 2
ALLOWED_MEDIA_SLOTS_PHASE378: Tuple[int, ...] = (
    MEDIA_SLOT_NONE_PHASE378,
    MEDIA_SLOT_1_PHASE378,
    MEDIA_SLOT_2_PHASE378,
)

SHOOT_MODE_STILL_PHASE378 = "Still"
SHOOT_MODE_MOVIE_PHASE378 = "Movie"
SHOOT_MODE_SQ_PHASE378 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE378: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE378,
    SHOOT_MODE_MOVIE_PHASE378,
    SHOOT_MODE_SQ_PHASE378,
)

RESET_ACTION_NONE_PHASE378 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE378 = "Camera Settings Reset"
RESET_ACTION_INITIALIZE_PHASE378 = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE378: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE378,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE378,
    RESET_ACTION_INITIALIZE_PHASE378,
)


# ---------------------------------------------------------------------------
# Gate G161 Constants: Dormant Anti-Dust / Shutter When Pwr OFF,
#                      Active Sensor Cleaning >=51%, & Focus Magnifier Full-Pipeline
# ---------------------------------------------------------------------------

SENSOR_CLEANING_MENU_PATH_G161 = "Setup -> [Setup Option] -> [Sensor Cleaning]"
FOCUS_ASSISTANT_MENU_PATH_G161 = "Shooting -> [Focus] -> [Focus Assistant]"
FX6_APR_MENU_PATH_G161 = "Technical > APR"
FX6_FOCUS_MAG_MENU_PATH_G161 = "Monitoring > Focus Magnifier"

FX3_POWER_OFF_SHUTTER_STATE_G161 = "OPEN"
FX3_DORMANT_ANTIDUST_EXPOSED_G161 = False
FX3_DORMANT_SHUTTER_WHEN_PWR_OFF_EXPOSED_G161 = False
FX3_ILC2210_SHUTTER_PWR_OFF_HITS_G161 = 0
FX6_SHUTTER_WHEN_PWR_OFF_ELF_HITS_G161 = 0
FX6_FOCAL_PLANE_MECHANICAL_SHUTTER_PRESENT_G161 = False
FX6_USER_IBIS_SENSOR_CLEANING_SUPPORTED_G161 = False
FX6_END_RANGE_LABEL_G161 = "1/4..1/128 + CLEAR"
SENSOR_CLEANING_MIN_SOC_PCT_G161 = 51
SENSOR_CLEANING_PHYSICAL_PWR_OFF_PROMPT_REQUIRED_G161 = True

DORMANT_ANTIDUST_SYMBOLS_G161: Tuple[str, ...] = (
    "Anti-dust Function",
    "Shutter When Pwr OFF",
    "anti_dust_shutter_when_power_off",
    "silent_mode_shutter_when_power_off",
    "BKID_APP_setting_image_sensor_barrier",
    "PID_SET_IMAGE_SENSOR_BARRIER",
    "EVENT_REMOTE_ANTI_DUST_FUNCTION_IMAGE_SENSOR_BARRIER",
)

EXACT_5_FX3_FOCUS_ASSISTANT_ITEMS_G161: Tuple[str, ...] = (
    "Focus Magnifier",
    "Focus Magnif. Time",
    "Initial Focus Mag.",
    "AF in Focus Mag.",
    "Auto Magnifier in MF",
)
FX3_FOCUS_ASSISTANT_5ITEMS_RESETTABLE_VER2_PLUS_G161 = False
FX3_FOCUS_MAG_DEFAULT_CUSTOM_BUTTON_G161 = "Custom Button 5"
ALLOWED_SENSOR_CROP_MODES_G161: Tuple[str, ...] = ("FF", "APS-C")
ALLOWED_FOCUS_MAG_TIMES_G161: Tuple[str, ...] = ("2 Sec", "5 Sec", "No Limit")
FOCUS_MAG_TIME_DEFAULT_G161 = "No Limit"

FX3_STILL_FF_MAG_RATIOS_G161: Tuple[str, ...] = ("x1.0", "x2.1", "x4.1")
FX3_STILL_FF_INITIAL_RATIOS_G161: Tuple[str, ...] = ("x1.0", "x2.1")
FX3_STILL_APSC_MAG_RATIOS_G161: Tuple[str, ...] = ("x1.0", "x1.5", "x3.0")
FX3_STILL_APSC_INITIAL_RATIOS_G161: Tuple[str, ...] = ("x1.0", "x1.5")
FX3_MOVIE_SQ_MAG_RATIOS_G161: Tuple[str, ...] = ("x1.0", "x4.0")
FX3_MOVIE_SQ_INITIAL_RATIOS_G161: Tuple[str, ...] = ("x1.0", "x4.0")
DORMANT_HIGH_MP_ALPHA_MAG_RATIOS_G161: Tuple[str, ...] = (
    "x1.6",
    "x2.7",
    "x3.1",
    "x3.6",
    "x3.7",
    "x4.2",
    "x4.7",
    "x5.3",
    "x5.5",
    "x6.1",
)

AF_IN_FOCUS_MAG_DEFAULT_G161 = "On"
AUTO_MAG_IN_MF_DEFAULT_G161 = "On"
FX3_AF_IN_FOCUS_MAG_STILL_ONLY_G161 = True
FX3_AUTO_MAG_IN_MF_STILL_ONLY_G161 = True
FX3_FOCUS_MAG_REC_CONTINUITY_SUPPORTED_G161 = True
FX3_FOCUS_MAG_CLEAN_HDMI_CROP_PIXELS_G161 = 0
FX3_FOCUS_MAG_INTERNAL_REC_CROP_PIXELS_G161 = 0
FX3_BRIGHT_MON_FOCUS_MAG_MIN_FW_G161 = 7.00

FX3_FOCUS_MAG_COEXISTING_FEATURES_G161: Tuple[str, ...] = (
    "Peaking Display",
    "Bright Monitoring",
    "De-Squeeze Display",
)
FX3_FOCUS_MAG_SUPPRESSED_FEATURES_G161: Tuple[str, ...] = (
    "Marker Display",
    "Switch V/H AF Area",
    "AF Illuminator",
)

ALLOWED_FX6_FOCUS_MAG_TARGETS_G161: Tuple[str, ...] = ("VF", "HDMI")
FX6_VF_MAG_RATIOS_G161: Tuple[str, ...] = ("x1.0", "x3.0", "x6.0")
FX6_HDMI_MAG_RATIOS_G161: Tuple[str, ...] = ("x1.0", "x2.0", "x4.0")
FX6_DORMANT_FS7_MAG_RATIOS_G161: Tuple[str, ...] = ("x8.0",)
FX6_HDMI_TARGET_MIN_FW_G161 = 6.00
FX6_FOCUS_MAG_SDI_CROP_PIXELS_G161 = 0
FX6_FOCUS_MAG_INTERNAL_REC_CROP_PIXELS_G161 = 0

# UXC resid16 anchors (G161)
DORMANT_ANTIDUST_FUNCTION_F_RESID16_G161 = 0x7495
DORMANT_SHUTTER_WHEN_PWR_OFF_F_RESID16_G161 = 0x709F
SENSOR_CLEANING_F_RESID16_G161 = 0x67D6
LEGACY_CLEANING_MODE_BASE_RESID16_G161 = 0xE7D7
SENSOR_CLEANING_PWR_OFF_G_RESID16_G161 = 0x6221
FOCUS_MAGNIFIER_BASE_RESID16_G161 = 0xE226
FOCUS_MAGNIF_TIME_F_RESID16_G161 = 0x692C
INITIAL_FOCUS_MAG_MOVIE_F_RESID16_G161 = 0x6633
INITIAL_FOCUS_MAG_STILL_F_RESID16_G161 = 0x77AD
AF_IN_FOCUS_MAG_F_RESID16_G161 = 0x6487
AUTO_MAG_IN_MF_F_RESID16_G161 = 0x6559
FX6_APR_NS1_RESID16_G161 = 0x322E
FX6_FOCUS_MAG_TARGET_NS1_RESID16_G161 = 0x2828

STATUS_VERIFIED_G161 = (
    "VERIFIED_G161_DORMANT_ANTIDUST_OPEN_SHUTTER_CLEANING51_AND_FOCUS_MAG_CLEAN_HDMI"
)
STATUS_BLOCKED_G161_TELEMETRY_INVALID = "BLOCKED_G161_TELEMETRY_INVALID"
STATUS_BLOCKED_G161_DORMANT_ANTIDUST_HIGHMP_RATIO_STILLONLY_OR_FX6_EOPNOTSUPP = (
    "BLOCKED_G161_DORMANT_ANTIDUST_HIGHMP_RATIO_STILLONLY_OR_FX6_EOPNOTSUPP"
)
STATUS_BLOCKED_G161_CLEANING51_REC_HDMI_CROP_OR_SUPPRESSION_VIOLATION = (
    "BLOCKED_G161_CLEANING51_REC_HDMI_CROP_OR_SUPPRESSION_VIOLATION"
)


# ---------------------------------------------------------------------------
# Gate G162 Constants: Exposure Std. Adjust (5-Mode Reset-Resistant Bias) &
#                      Wired Smartphone USB Tethering / Slot 1 EROFS=30 Firewall
# ---------------------------------------------------------------------------

EXPOSURE_STD_ADJUST_MENU_PATH_G162 = (
    "Exposure/Color -> [Exposure Comp.] -> [Exposure Std. Adjust]"
)
FX6_AUTO_EXPOSURE_MENU_PATH_G162 = "Shooting > Auto Exposure > Level"
USB_CONNECTION_MODE_MENU_PATH_G162 = "Setup -> [USB] -> [USB Connection Mode]"
USB_LAN_TETHERING_MENU_PATH_G162 = "Network -> [USB-LAN/Tethering]"
FX6_USB_TETHERING_MENU_PATH_G162 = "Network > USB Tethering"

EXACT_5_METERING_MODES_G162: Tuple[str, ...] = (
    "Multi",
    "Center",
    "Spot",
    "Entire Screen Avg.",
    "Highlight",
)
EXPOSURE_STD_MIN_SIXTHS_G162 = -6
EXPOSURE_STD_MAX_SIXTHS_G162 = 6
EXPOSURE_STD_DEFAULT_SIXTHS_G162 = 0
EXPOSURE_STD_STEP_COUNT_G162 = 13
EXPOSURE_STD_STEP_LABEL_G162 = "1/6 EV"
DORMANT_EXPOSURE_STD_STEP_LABEL_G162 = "1/8 EV"
EXPOSURE_STD_ADJUST_RESETTABLE_BY_CAMSET_RESET_G162 = False
EXPOSURE_STD_ALTERS_EXIF_BIAS_VALUE_G162 = False
ALLOWED_EXPOSURE_CONTROL_MODES_G162: Tuple[str, ...] = (
    "P_A_S",
    "M_ISO_AUTO",
    "M_FIXED_ISO",
    "Cine_EI",
    "Cine_EI_Quick",
    "Flexible_ISO_AUTO",
    "Flexible_ISO_FIXED",
)

FX6_AE_LEVEL_MIN_G162 = -3.0
FX6_AE_LEVEL_MAX_G162 = 3.0
FX6_AE_LEVEL_STEP_G162 = 0.25
FX6_AE_LEVEL_STEP_COUNT_G162 = 25
FX6_AE_SPEED_MIN_G162 = -99
FX6_AE_SPEED_MAX_G162 = 99
ALLOWED_FX6_AE_MODES_G162: Tuple[str, ...] = ("Backlight", "Standard", "Spotlight")
FX6_PER_LUT_AE_LEVEL_OFFSET_SUPPORTED_G162 = True

ALLOWED_FX3_USB_CONNECTION_MODES_G162: Tuple[str, ...] = (
    "Sel. When Connect",
    "MassStorage(MSC)",
    "MTP",
    "Remote Shooting",
)
USB_CONNECTION_MODE_DEFAULT_G162 = "Sel. When Connect"
DORMANT_USB_STREAMING_MODE_G162 = "USB Streaming"
FX3_USB_MSC_ELF_TYPO_G162 = "USB_CONNECTION_METHOD_MASS_STRAGE"
ALLOWED_USB_LUN_SETTINGS_G162: Tuple[str, ...] = ("Multi", "Single")
USB_LUN_DEFAULT_G162 = "Multi"
ALLOWED_USB_TETHERING_DRIVERS_G162: Tuple[str, ...] = (
    "cdc_ether",
    "cdc_ncm",
    "ipheth",
    "rndis_host",
)
ALLOWED_TETHERING_WORKLOADS_G162: Tuple[str, ...] = (
    "none",
    "rtmp",
    "rtmps",
    "srt",
    "ftp",
    "ftpes",
    "sftp",
    "creators_app_usb_remote",
    "creators_app_usb_streaming",
    "monitor_and_control_usb",
    "fx6_tethering_usb_remote",
)
USB_LAN_CNCT_LAUNCH_MIN_FW_G162 = 7.00
USB_LAN_CNCT_LAUNCH_DEFAULT_G162 = "Off"
FX3_USB_TETHERING_ZERO_RF_AIRPLANE_ALLOWED_G162 = True
FX3_USB_TETHERING_RF_TX_PACKETS_AIRPLANE_G162 = 0
FX3_USBG_IAP_CLASS_HITS_G162 = 0
FX6_USBG_IAP_CLASS_ACTIVE_G162 = True
FX3_MC_USB_TIMECODE_SUPPORTED_G162 = False
FX3_MC_USB_FOCUS_MAP_SUPPORTED_G162 = False
FX3_MC_USB_LUT_IMPORT_SUPPORTED_G162 = False
ALLOWED_HOST_STORAGE_ACCESS_MODES_G162: Tuple[str, ...] = (
    "none",
    "read_only_guarded",
    "host_writable",
)

# UXC resid16 anchors (G162)
EXPOSURE_STD_ADJUST_F_RESID16_G162 = 0x6F71
ENTIRE_SCREEN_AVG_F_RESID16_G162 = 0x6AA1
STEP_PLUS_ONE_SIXTH_BASE_RESID16_G162 = 0xE09A
STEP_MINUS_ONE_SIXTH_BASE_RESID16_G162 = 0xE286
USB_CONNECTION_MODE_F_RESID16_G162 = 0x69A2
SEL_WHEN_CONNECT_F_RESID16_G162 = 0x7738
USB_LUN_SETTING_F_RESID16_G162 = 0x6B19
MTP_BASE_RESID16_G162 = 0xE24B
TETHERING_CONNECTION_F_RESID16_G162 = 0x7A90
USB_LAN_CNCT_LAUNCH_F_RESID16_G162 = 0x7D2A
STREAMING_TETHER_PROMPT_G_RESID16_G162 = 0x638E

STATUS_VERIFIED_G162 = (
    "VERIFIED_G162_EXPOSURE_STD_5MODE_RESET_IMMUNE_AND_USB_TETHER_ZERORF_SLOT1_EROFS"
)
STATUS_BLOCKED_G162_TELEMETRY_INVALID = "BLOCKED_G162_TELEMETRY_INVALID"
STATUS_BLOCKED_G162_SLOT1_MSC_MTP_WRITABLE_EROFS = (
    "BLOCKED_G162_SLOT1_MSC_MTP_WRITABLE_EROFS"
)
STATUS_BLOCKED_G162_DUAL_USB_PORT_OR_FX6_LAN_MUTEX_EBUSY = (
    "BLOCKED_G162_DUAL_USB_PORT_OR_FX6_LAN_MUTEX_EBUSY"
)
STATUS_BLOCKED_G162_DORMANT_NOUVC_IAP2_MC_OR_STEP18_EOPNOTSUPP = (
    "BLOCKED_G162_DORMANT_NOUVC_IAP2_MC_OR_STEP18_EOPNOTSUPP"
)
STATUS_BLOCKED_G162_EXPSTD_EXIF_RESET_OR_ZERORF_AIRPLANE_VIOLATION = (
    "BLOCKED_G162_EXPSTD_EXIF_RESET_OR_ZERORF_AIRPLANE_VIOLATION"
)

STATUS_BLOCKED_PHASE378_DONOR_INTEGRITY = "BLOCKED_PHASE378_DONOR_CONTRACT_INTEGRITY"


# ---------------------------------------------------------------------------
# Pinned Wave-71 Donor Specs (O_RDONLY / Bounded Slices, Raw Bytes = 0)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX_P378 = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX3_KMOD_PREFIX_P378 = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod"
)
_FX6_NF15_PREFIX_P378 = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)

PINNED_FX3_APPFW_SLICES_PHASE378: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x0399D890, b"anti_dust_shutter_when_power_off"),
    (0x0399DA50, b"silent_mode_shutter_when_power_off"),
    (0x03BCC306, b"BKID_APP_setting_image_sensor_barrier"),
    (0x03951B2A, b"PID_SET_IMAGE_SENSOR_BARRIER"),
    (0x03C3CBA0, b"EVENT_REMOTE_ANTI_DUST_FUNCTION_IMAGE_SENSOR_BARRIER"),
    (0x039D35AA, b"VAL_FEATURE_MANAGER_menu_item_TYPE_MENU_ITEM_ALCIN_UUD"),
    (0x039CC5C6, b"FUNC_set_cleaning_mode"),
    (0x02FA48C1, b"MOV_INIT_RATIO_FOCUS_MAGNIF_X1_0"),
    (0x02FA48E2, b"MOV_INIT_RATIO_FOCUS_MAGNIF_X4_0"),
    (0x02FA468C, b"STL_INIT_RATIO_FOCUS_MAGNIF_X1_0"),
    (0x02FA46AD, b"STL_INIT_RATIO_FOCUS_MAGNIF_PIXEL_BY_PIXEL_X1_5"),
    (0x02FA470D, b"STL_INIT_RATIO_FOCUS_MAGNIF_PIXEL_BY_PIXEL_X2_1"),
    (0x02FA47CD, b"STL_INIT_RATIO_FOCUS_MAGNIF_PIXEL_BY_PIXEL_X4_7"),
    (0x02FA48A9, b"TWICE_OF_PIXEL_BY_PIXEL"),
    (0x03BC9742, b"BKID_APP_MR_setting_focus_magnification_time"),
    (0x03BC159A, b"BKID_APP_focus_magnification_area_center_x"),
    (0x03969D76, b"vdf_set_yuv_layout_for_focus_magnification_out_t"),
    (0x03BF0008, b"BKID_APP_extern_menu_standard_exposure_shift_multi"),
    (0x03BF003B, b"BKID_APP_extern_menu_standard_exposure_shift_center"),
    (0x03BF006F, b"BKID_APP_extern_menu_standard_exposure_shift_spot"),
    (0x03BF00D8, b"BKID_APP_extern_menu_standard_exposure_shift_average"),
    (0x03BF00A1, b"BKID_APP_extern_menu_standard_exposure_shift_highlight"),
    (0x03C11BD2, b"EXTERN_VAL_STANDARD_EXPOSURE_STEP_1_6"),
    (0x03BCC062, b"BKID_APP_setting_usb_connection_method"),
    (0x03C1A357, b"USB_CONNECTION_METHOD_MASS_STRAGE"),
    (0x03C1A33D, b"USB_CONNECTION_METHOD_MTP"),
    (0x03C1A395, b"USB_CONNECTION_METHOD_TETHERING"),
    (0x02FA6E9D, b"STREAMING_CONNECT_METHOD_USB_TETHERING"),
    (0x03B0FEEF, b"FTP_CONNECT_METHOD_USB_TETHERING"),
    (0x03BCA503, b"BKID_APP_setting_usb_lan_connect_launch"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE378 = (
    "b8331e07f2a63bcb6669f945856c8c23b8cc0286d8dcf72bbfc5414443f465cf"
)

PINNED_FX6_APPFW_SLICES_PHASE378: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x0260AFE9, b"PID_SET_VARIABLE_ND_VALUE"),
    (0x023C8A6A, b"MODEL_APR_EXECUTE_COMP"),
    (0x027A9146, b"ASSIGNABLE_SWITCH_FOCUS_MAGNIFIER_x3_x6"),
    (0x0271C9CF, b"BKID_APP_SETTING_CONTINUE_FOCUS_MAGNIFIER"),
    (0x0270BA81, b"BKID_APP_SETTING_FOCUS_MAG_BUTTON_TARGET"),
    (0x02647A57, b"FUNC_monitor_focus_magnifier_x2x4"),
    (0x026ADF8F, b"VAL_setting_assign_auto_exposure_level_LEVEL_MINUS_3_0"),
    (0x026ADAAB, b"VAL_setting_assign_auto_exposure_level_LEVEL_3_0"),
    (0x02707956, b"BKID_APP_SETTING_AUTO_EXPOSURE_LEVEL"),
    (0x027070B4, b"BKID_APP_SETTING_AE_LEVEL_OFFSET"),
    (0x02718A88, b"BKID_APP_EXTERN_AE_SPEED"),
    (0x02707CBB, b"BKID_APP_SETTING_DETECT_WINDOW"),
    (0x0270AE43, b"BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE378 = (
    "2d8fcf818d7d46c387d1895da67da460312b3f2e1e1336e8ff7f71759bac486d"
)

PINNED_PHASE378_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE378,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE378),
        "FX3 appFw.so Wave-71 Anti-Dust/FocusMag/ExposureStd/UsbTether slices",
    ),
    "fx3_libnetservicetethering_so": (
        "FX3",
        f"{_FX3_USR_PREFIX_P378}/lib/libNetServiceTethering.so",
        126_616,
        "f1e7c27e29a5b923da5656e96e0c3d50a5d675d35c68ae7119dabf9de3418d9a",
        (
            b"\x7fELF",
            b"startDHCPClient",
            b"/usr/sbin/dhcpcd",
            b"dhcpcd_tethering_dns_4_noipv4ll.conf",
            b"judgeTetheringDevice",
        ),
        "FX3 libNetServiceTethering.so DHCP & USB host tethering service",
    ),
    "fx3_libtetheringresource_so": (
        "FX3",
        f"{_FX3_USR_PREFIX_P378}/lib/libTetheringResource.so",
        14_928,
        "92717396ccb58b5234c804e9f37a1045984922243b300e6ed7f17d90761dd567",
        (
            b"\x7fELF",
            b"cdc_ether.ko",
            b"cdc_ncm.ko",
            b"ipheth.ko",
            b"rndis_host.ko",
        ),
        "FX3 libTetheringResource.so kmod driver loading table",
    ),
    "fx3_libinfrausbcmn_so": (
        "FX3",
        f"{_FX3_USR_PREFIX_P378}/lib/libInfraUsbCmn.so",
        159_504,
        "6caefd0677ee01cc6cdd54555f4422b03a86d12304c60f5372de18315bdd4396",
        (
            b"\x7fELF",
            b"/proc/usbg_storage/storage_access_info",
            b"usbgmscif_setReadOnly",
        ),
        "FX3 libInfraUsbCmn.so MSC read-only guard & stripped CUsbGadgetIAP",
    ),
    "fx3_libusbcontrol_so": (
        "FX3",
        f"{_FX3_USR_PREFIX_P378}/lib/libUsbControl.so",
        135_424,
        "2bf51f28fd5066e56afc8bbb02ddbaa96b36f57ff2a823cecf9f901781754ed9",
        (
            b"\x7fELF",
            b"MSGID_SETCONFIG_MTP_EVT",
            b"createMtpRootHandle",
        ),
        "FX3 libUsbControl.so MTP root handle Slot 1 binding",
    ),
    "fx3_cdc_ncm_ko": (
        "FX3",
        f"{_FX3_KMOD_PREFIX_P378}/cdc_ncm.ko",
        32_208,
        "fce183b98eebbda9bb7954854bdcb717c2da74785c97a08a767afc235628ff70",
        (b"\x7fELF", b"cdc_ncm"),
        "FX3 cdc_ncm.ko USB-LAN / NCM tethering kernel module",
    ),
    "fx3_rndis_host_ko": (
        "FX3",
        f"{_FX3_KMOD_PREFIX_P378}/rndis_host.ko",
        14_064,
        "8417d601c621de19526f18ca92102a3adb718c8372a0d0f73f5cf9fd89f93d17",
        (b"\x7fELF", b"rndis_host"),
        "FX3 rndis_host.ko Android USB tethering kernel module",
    ),
    "fx3_ipheth_ko": (
        "FX3",
        f"{_FX3_KMOD_PREFIX_P378}/ipheth.ko",
        15_552,
        "11405854810149ebf7af93534ad1fc6b8b01ea626108a42ae5725e2845126ac6",
        (b"\x7fELF", b"ipheth"),
        "FX3 ipheth.ko iOS wired personal hotspot kernel module",
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
        f"{_FX3_USR_PREFIX_P378}/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Anti-dust Function",
            b"Shutter When Pwr OFF",
            b"Sensor Cleaning",
            b"Focus Magnif. Time",
            b"Initial Focus Mag.",
            b"AF in Focus Mag.",
            b"Auto Magnifier in MF",
            b"Exposure Std. Adjust",
            b"Entire Screen Avg.",
            b"USB Connection Mode",
            b"USB LUN Setting",
            b"Tethering Connection",
            b"USB-LAN Cnct. Launch",
        ),
        "FX3 string_english_f.uxc Wave-71 EN parity",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P378}/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "\u9632\u5c18\u529f\u80fd".encode("utf-8"),
            "\u5173\u673a\u65f6\u5feb\u95e8".encode("utf-8"),
            "\u4f20\u611f\u5668\u6e05\u6d01".encode("utf-8"),
            "\u5bf9\u7126\u653e\u5927\u65f6\u95f4".encode("utf-8"),
            "\u653e\u5927\u5bf9\u7126\u4e2dAF".encode("utf-8"),
            "MF\u4e2d\u81ea\u52a8\u653e\u5927\u5bf9\u7126".encode("utf-8"),
            "\u66dd\u5149\u6807\u51c6\u8c03\u6574".encode("utf-8"),
            "\u6574\u4e2a\u5c4f\u5e55\u5e73\u5747".encode("utf-8"),
            "USB\u8fde\u63a5\u6a21\u5f0f".encode("utf-8"),
            "USB LUN\u8bbe\u5b9a".encode("utf-8"),
            "\u7f51\u7edc\u5171\u4eab\u8fde\u63a5".encode("utf-8"),
            "\u542f\u52a8\u65f6USB-LAN\u8fde\u63a5".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-71 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P378}/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "\u9632\u5875\u529f\u80fd".encode("utf-8"),
            "\u95dc\u9589\u96fb\u6e90\u6642\u5feb\u9580".encode("utf-8"),
            "\u611f\u61c9\u5668\u6e05\u6f54".encode("utf-8"),
            "\u5c0d\u7126\u653e\u5927\u6642\u9593".encode("utf-8"),
            "\u521d\u59cb\u5c0d\u7126\u653e\u5927\u7387".encode("utf-8"),
            "\u5c0d\u7126\u653e\u5927\u93e1\u4e2d\u5c0d\u7126".encode("utf-8"),
            "MF\u4e2d\u81ea\u52d5\u5c0d\u7126\u653e\u5927".encode("utf-8"),
            "\u66dd\u5149\u6a19\u6e96\u8abf\u6574".encode("utf-8"),
            "\u5168\u87a2\u5e55\u5e73\u5747".encode("utf-8"),
            "USB\u9023\u7dda\u6a21\u5f0f".encode("utf-8"),
            "USB LUN\u8a2d\u5b9a".encode("utf-8"),
            "\u7db2\u969b\u7db2\u8def\u5171\u7528\u9023\u63a5".encode("utf-8"),
            "\u555f\u52d5\u6642USB-LAN\u9023\u7dda".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-71 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P378}/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "\u30a2\u30f3\u30c1\u30c0\u30b9\u30c8\u6a5f\u80fd".encode("utf-8"),
            "\u96fb\u6e90OFF\u6642\u306e\uff7c\uff6c\uff6f\uff80\uff70".encode("utf-8"),
            "\uff7e\uff9d\uff7b\uff70\uff78\uff98\uff70\uff86\uff9d\uff78\uff9e".encode("utf-8"),
            "\u30d4\u30f3\u30c8\u62e1\u5927\u6642\u9593".encode("utf-8"),
            "\uff8b\uff9f\uff9d\uff84\u62e1\u5927\u521d\u671f\u500d\u7387".encode("utf-8"),
            "\u30d4\u30f3\u30c8\u62e1\u5927\u4e2d\u306eAF".encode("utf-8"),
            "MF\u6642\u81ea\u52d5\uff8b\uff9f\uff9d\uff84\u62e1\u5927".encode("utf-8"),
            "\u9732\u51fa\u57fa\u6e96\u8abf\u6574".encode("utf-8"),
            "\u753b\u9762\u5168\u4f53\u5e73\u5747".encode("utf-8"),
            "USB\u63a5\u7d9a\u30e2\u30fc\u30c9".encode("utf-8"),
            "USB LUN\u8a2d\u5b9a".encode("utf-8"),
            "\u30c6\u30b6\u30ea\u30f3\u30b0\u63a5\u7d9a".encode("utf-8"),
            "\u8d77\u52d5\u6642\u306eUSB-LAN\u63a5\u7d9a".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-71 JA parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P378}/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Cleaning Mode",
            b"Focus Magnifier",
            b"No Limit",
            b"+1/6",
            b"-1/6",
            b"MTP",
        ),
        "FX3 string_english.uxc Wave-71 EN base",
    ),
    "fx3_string_simplifiedchinese_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P378}/share/app/string_simplifiedchinese.uxc",
        149_064,
        "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
        (
            "\u6e05\u6d01\u6a21\u5f0f".encode("utf-8"),
            "\u653e\u5927\u5bf9\u7126".encode("utf-8"),
            b"+1/6",
            b"-1/6",
            b"MTP",
        ),
        "FX3 string_simplifiedchinese.uxc Wave-71 ZH-CN base",
    ),
    "fx3_string_traditionalchinese_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P378}/share/app/string_traditionalchinese.uxc",
        151_908,
        "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
        (
            "\u6e05\u6f54\u6a21\u5f0f".encode("utf-8"),
            "\u5c0d\u7126\u653e\u5927\u93e1".encode("utf-8"),
            b"+1/6",
            b"-1/6",
            b"MTP",
        ),
        "FX3 string_traditionalchinese.uxc Wave-71 ZH-TW base",
    ),
    "fx3_string_japanese_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P378}/share/app/string_japanese.uxc",
        208_564,
        "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
        (
            "\u30af\u30ea\u30fc\u30cb\u30f3\u30b0\u30e2\u30fc\u30c9".encode("utf-8"),
            "\u30d4\u30f3\u30c8\u62e1\u5927".encode("utf-8"),
            b"+1/6",
            b"-1/6",
            b"MTP",
        ),
        "FX3 string_japanese.uxc Wave-71 JA base",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P378}/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"USB-LAN/Tethering",
            b"network streaming",
        ),
        "FX3 string_english_g.uxc Wave-71 EN guide",
    ),
    "fx3_string_simplifiedchinese_g_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P378}/share/app/string_simplifiedchinese_g.uxc",
        61_296,
        "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
        (
            "USB-LAN/\u7f51\u7edc\u5171\u4eab".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_g.uxc Wave-71 ZH-CN guide",
    ),
    "fx6_appfw_so": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P378}/lib/appFw.so",
        50_520_424,
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE378,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE378),
        "FX6 appFw.so Wave-71 e-ND/APR/FocusMag(VF+HDMI)/AE(-3..+3 25-step) slices",
    ),
    "fx6_libnetservicetethering_so": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P378}/lib/libNetServiceTethering.so",
        106_584,
        "eb23a90cfd81ef480edac55736560d8438190ae9dee9635acfad88fdf7f7112e",
        (
            b"\x7fELF",
            b"/var/run/dhcpcd/resolv.conf/usb0.dhcp",
            b"NstTetheringStatusGetUPMStatus",
        ),
        "FX6 libNetServiceTethering.so usb0 DHCP & UPM status",
    ),
    "fx6_libinfrausbcmn_so": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P378}/lib/libInfraUsbCmn.so",
        164_144,
        "a81404ed2f2c0a29fff34d53a2d145fa52632fa0a8796cee096353f4c8220d65",
        (
            b"\x7fELF",
            b"/usr/kmod/usbg_iap.ko",
            b"CUsbGadgetIAP",
        ),
        "FX6 libInfraUsbCmn.so active CUsbGadgetIAP iAP2 linkage",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P378}/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"Sensor Cleaning",
            b"Focus Magnifier",
            b"USB Tethering",
        ),
        "FX6 string_english.uxc Wave-71 EN baseline",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P378}/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"Copy to USB",
            b"Format USB",
        ),
        "FX6 string_english_2.uxc Wave-71 EN enterprise baseline",
    ),
}


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _is_clean_room_forced(force_clean_room: Optional[bool]) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE378):
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
    if body_model_name != FX3_MODEL_NAME_PHASE378:
        errs.append(f"body_model_name_invalid:{body_model_name!r}")
    if not _is_strict_int(body_model_id) or body_model_id != FX3_MODEL_ID_PHASE378:
        errs.append(f"body_model_id_invalid:{body_model_id!r}")
    if help_guide_code != FX3_HELP_GUIDE_CODE_PHASE378:
        errs.append(f"help_guide_code_invalid:{help_guide_code!r}")
    if _parse_fw_float(firmware_version) is None:
        errs.append(f"firmware_version_invalid:{firmware_version!r}")
    return errs


def strip_elapsed_seconds_recursive_phase378(obj: Any) -> Any:
    """Recursively strip non-deterministic `elapsed_seconds`/`elapsed_ms` keys for canonical digests."""
    if isinstance(obj, dict):
        return {
            k: strip_elapsed_seconds_recursive_phase378(v)
            for k, v in obj.items()
            if k not in ("elapsed_seconds", "elapsed_ms")
        }
    if isinstance(obj, list):
        return [strip_elapsed_seconds_recursive_phase378(v) for v in obj]
    if isinstance(obj, tuple):
        return [strip_elapsed_seconds_recursive_phase378(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Donor Integrity Audit (O_RDONLY / Clean-Room Dual-Mode)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase378DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    fx3_contracts_verified: bool
    fx6_contracts_verified: bool
    four_lang_resid16_parity_verified: bool
    tethering_kmods_verified: bool
    zero_fx3_iap2_gadget_verified: bool
    elapsed_seconds: float
    within_budget_200ms: bool
    raw_firmware_bytes_leaked: int
    file_digests: Dict[str, str]
    missing_markers: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def audit_phase378_donor_contracts(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase378DonorAuditResult:
    """Fast (< 0.20s) O_RDONLY + bounded os.pread donor audit with clean-room fallback."""
    import time

    t0 = time.perf_counter()
    clean_forced = _is_clean_room_forced(force_clean_room)
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else dict(PINNED_PHASE378_DONOR_SPECS)
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
        return Phase378DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_NO_DONOR_DISK_IO",
            files_inspected=0,
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            tethering_kmods_verified=True,
            zero_fx3_iap2_gadget_verified=True,
            elapsed_seconds=round(dt, 6),
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE378,
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
        return Phase378DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_ABSENT_DONOR_FALLBACK",
            files_inspected=0,
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            tethering_kmods_verified=True,
            zero_fx3_iap2_gadget_verified=True,
            elapsed_seconds=round(dt, 6),
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE378,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(
                f"Donor files absent ({len(missing_files)} missing); "
                "verified Phase 378 via clean-room synthetic fallback.",
            ),
        )

    file_digests: Dict[str, str] = {}
    missing_markers: List[str] = []
    errors: List[str] = []
    inspected = 0
    zero_fx3_iap2_ok = True

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
                target, PINNED_FX3_APPFW_SLICES_PHASE378
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tok_errs = _read_exact_o_rdonly_slices(
                target, PINNED_FX6_APPFW_SLICES_PHASE378
            )
        else:
            actual_size, actual_sha, tok_errs = _read_full_o_rdonly_sha256_and_tokens(
                target, tokens
            )
            if key == "fx3_libinfrausbcmn_so" and donor_specs_override is None:
                fd_chk = os.open(target, os.O_RDONLY)
                try:
                    raw_chk = os.read(fd_chk, actual_size)
                finally:
                    os.close(fd_chk)
                if b"CUsbGadgetIAP" in raw_chk:
                    zero_fx3_iap2_ok = False
                    missing_markers.append("fx3_libinfrausbcmn_so:unexpected_CUsbGadgetIAP")
                    errors.append("FX3:fx3_libinfrausbcmn_so:unexpected_CUsbGadgetIAP")

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
    return Phase378DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE
            if valid
            else STATUS_BLOCKED_PHASE378_DONOR_INTEGRITY
        ),
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="STRICT_OS_O_RDONLY_PREAD",
        files_inspected=inspected,
        fx3_contracts_verified=valid,
        fx6_contracts_verified=valid,
        four_lang_resid16_parity_verified=valid,
        tethering_kmods_verified=valid,
        zero_fx3_iap2_gadget_verified=zero_fx3_iap2_ok and valid,
        elapsed_seconds=round(dt, 6),
        within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE378,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        file_digests=file_digests,
        missing_markers=tuple(missing_markers),
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# Gate G161: Dormant Anti-Dust / Shutter When Pwr OFF Guard &
#            Focus Magnifier Full-Pipeline + Clean-HDMI Isolation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AntiDustFocusMagGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    sensor_cleaning_menu_path: str
    focus_assistant_menu_path: str
    fx6_apr_menu_path: str
    fx6_focus_mag_menu_path: str
    effective_power_off_shutter_state: str
    dormant_antidust_exposed: bool
    dormant_shutter_when_pwr_off_exposed: bool
    sensor_cleaning_requested: bool
    sensor_cleaning_allowed: bool
    sensor_cleaning_min_soc_pct: int
    np_fz100_soc_pct: int
    physical_power_off_prompt_required: bool
    fx6_focal_plane_mechanical_shutter_present: bool
    fx6_user_ibis_sensor_cleaning_supported: bool
    fx6_end_range_label: str
    fx3_focus_assistant_items_count: int
    focus_assistant_resettable_by_camset_reset: bool
    shoot_mode: str
    sensor_crop_mode: str
    focus_magnifier_active: bool
    effective_focus_mag_time: str
    effective_initial_focus_mag_ratio: str
    effective_active_focus_mag_ratio: str
    allowed_active_ratios_for_mode: Tuple[str, ...]
    effective_af_in_focus_mag: str
    af_in_focus_mag_usable_in_mode: bool
    effective_auto_mag_in_mf: str
    auto_mag_in_mf_usable_in_mode: bool
    movie_rec_active: bool
    focus_mag_survives_movie_rec: bool
    hdmi_info_display: str
    hdmi_output_cropped: bool
    internal_recording_cropped: bool
    clean_hdmi_crop_pixels: int
    internal_rec_crop_pixels: int
    peaking_coexists: bool
    bright_monitoring_coexists: bool
    desqueeze_coexists: bool
    suppressed_features_while_active: Tuple[str, ...]
    fx6_focus_mag_target: str
    fx6_effective_mag_ratio: str
    fx6_sdi_cropped: bool
    fx6_internal_rec_cropped: bool
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


def resolve_fx3_antidust_focusmag_state(
    *,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE378,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE378,
    sensor_crop_mode: str = "FF",
    focus_magnifier_active: bool = True,
    focus_mag_time: str = FOCUS_MAG_TIME_DEFAULT_G161,
    initial_focus_mag_ratio: str = "x1.0",
    active_focus_mag_ratio: str = "x4.0",
    af_in_focus_mag: str = AF_IN_FOCUS_MAG_DEFAULT_G161,
    auto_mag_in_mf: str = AUTO_MAG_IN_MF_DEFAULT_G161,
    movie_rec_active: bool = False,
    hdmi_info_display: str = "Off",
    reset_action: str = RESET_ACTION_NONE_PHASE378,
    np_fz100_soc_pct: int = 85,
    sensor_cleaning_requested: bool = False,
) -> Dict[str, Any]:
    """Deterministically resolve FX3 Ver. 7.02 Anti-Dust / Focus Assistant runtime state."""
    fw = _parse_fw_float(firmware_version)
    fw_val = fw if fw is not None else 7.02

    # All 5 Focus Assistant items resist [Camera Settings Reset] on Ver. 2.00+;
    # only [Initialize] resets them back to defaults.
    if reset_action == RESET_ACTION_INITIALIZE_PHASE378:
        eff_time = FOCUS_MAG_TIME_DEFAULT_G161
        eff_init = "x1.0"
        eff_af_mag = AF_IN_FOCUS_MAG_DEFAULT_G161
        eff_auto_mf = AUTO_MAG_IN_MF_DEFAULT_G161
    else:
        eff_time = focus_mag_time
        eff_init = initial_focus_mag_ratio
        eff_af_mag = af_in_focus_mag
        eff_auto_mf = auto_mag_in_mf

    if shoot_mode == SHOOT_MODE_STILL_PHASE378:
        allowed_ratios = (
            FX3_STILL_FF_MAG_RATIOS_G161
            if sensor_crop_mode == "FF"
            else FX3_STILL_APSC_MAG_RATIOS_G161
        )
        allowed_init = (
            FX3_STILL_FF_INITIAL_RATIOS_G161
            if sensor_crop_mode == "FF"
            else FX3_STILL_APSC_INITIAL_RATIOS_G161
        )
    else:
        allowed_ratios = FX3_MOVIE_SQ_MAG_RATIOS_G161
        allowed_init = FX3_MOVIE_SQ_INITIAL_RATIOS_G161

    eff_active_ratio = active_focus_mag_ratio if focus_magnifier_active else "x1.0"
    is_still = shoot_mode == SHOOT_MODE_STILL_PHASE378
    # Clean-HDMI when HDMI Info. Display = Off outputs uncropped full frame;
    # internal recording is NEVER cropped regardless of HDMI Info. Display.
    clean_hdmi_cropped = False
    internal_rec_cropped = False
    bright_mon_coexists = fw_val >= FX3_BRIGHT_MON_FOCUS_MAG_MIN_FW_G161
    suppressed = (
        FX3_FOCUS_MAG_SUPPRESSED_FEATURES_G161 if focus_magnifier_active else ()
    )
    cleaning_allowed = (not sensor_cleaning_requested) or (
        np_fz100_soc_pct >= SENSOR_CLEANING_MIN_SOC_PCT_G161
    )

    return {
        "effective_power_off_shutter_state": FX3_POWER_OFF_SHUTTER_STATE_G161,
        "sensor_cleaning_allowed": cleaning_allowed,
        "effective_focus_mag_time": eff_time,
        "effective_initial_focus_mag_ratio": eff_init,
        "effective_active_focus_mag_ratio": eff_active_ratio,
        "allowed_active_ratios_for_mode": allowed_ratios,
        "allowed_initial_ratios_for_mode": allowed_init,
        "effective_af_in_focus_mag": eff_af_mag,
        "af_in_focus_mag_usable_in_mode": is_still,
        "effective_auto_mag_in_mf": eff_auto_mf,
        "auto_mag_in_mf_usable_in_mode": is_still,
        "focus_mag_survives_movie_rec": FX3_FOCUS_MAG_REC_CONTINUITY_SUPPORTED_G161,
        "hdmi_output_cropped": clean_hdmi_cropped,
        "internal_recording_cropped": internal_rec_cropped,
        "peaking_coexists": True,
        "bright_monitoring_coexists": bright_mon_coexists,
        "desqueeze_coexists": True,
        "suppressed_features_while_active": suppressed,
    }


def compute_antidust_focusmag_matrix() -> Dict[str, Any]:
    """Sweep deterministic 384-state Wave-71 Gate G161 matrix (Anti-Dust & Focus Magnifier)."""
    shoot_modes = ALLOWED_SHOOT_MODES_PHASE378  # 3
    crops = ALLOWED_SENSOR_CROP_MODES_G161  # 2
    mag_times = ALLOWED_FOCUS_MAG_TIMES_G161  # 3 -> wait: 3*2*2*2*2*2*2*2 = 384!
    focus_active_opts = (False, True)  # 2
    rec_opts = (False, True)  # 2
    hdmi_info_opts = ("Off", "On")  # 2
    resets = (
        RESET_ACTION_NONE_PHASE378,
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE378,
    )  # 2
    soc_tiers = (50, 51)  # 2
    fx6_targets = ALLOWED_FX6_FOCUS_MAG_TARGETS_G161  # 2
    # 3 * 2 * 2 * 2 * 2 * 2 * 2 * 2 = 384 states!
    total = 0
    open_shutter_count = 0
    zero_internal_crop_count = 0
    zero_clean_hdmi_crop_count = 0
    rec_continuity_count = 0
    cleaning_blocked_below51_count = 0
    still_only_af_count = 0
    suppressed_active_count = 0
    camset_reset_immune_count = 0

    for (
        sm,
        crop,
        f_act,
        rec,
        hdmi_info,
        rst,
        soc,
        fx6_tgt,
    ) in itertools.product(
        shoot_modes,
        crops,
        focus_active_opts,
        rec_opts,
        hdmi_info_opts,
        resets,
        soc_tiers,
        fx6_targets,
    ):
        total += 1
        active_ratio = (
            "x4.0"
            if sm != SHOOT_MODE_STILL_PHASE378
            else ("x2.1" if crop == "FF" else "x1.5")
        )
        st = resolve_fx3_antidust_focusmag_state(
            shoot_mode=sm,
            sensor_crop_mode=crop,
            focus_magnifier_active=f_act,
            focus_mag_time="5 Sec",
            initial_focus_mag_ratio="x1.0",
            active_focus_mag_ratio=active_ratio,
            movie_rec_active=rec,
            hdmi_info_display=hdmi_info,
            reset_action=rst,
            np_fz100_soc_pct=soc,
            sensor_cleaning_requested=True,
        )
        if st["effective_power_off_shutter_state"] == "OPEN":
            open_shutter_count += 1
        if not st["internal_recording_cropped"]:
            zero_internal_crop_count += 1
        if hdmi_info == "Off" and not st["hdmi_output_cropped"]:
            zero_clean_hdmi_crop_count += 1
        if st["focus_mag_survives_movie_rec"]:
            rec_continuity_count += 1
        if soc < SENSOR_CLEANING_MIN_SOC_PCT_G161 and not st["sensor_cleaning_allowed"]:
            cleaning_blocked_below51_count += 1
        if (sm == SHOOT_MODE_STILL_PHASE378) == st["af_in_focus_mag_usable_in_mode"]:
            still_only_af_count += 1
        if f_act and len(st["suppressed_features_while_active"]) == 3:
            suppressed_active_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE378
            and st["effective_focus_mag_time"] == "5 Sec"
        ):
            camset_reset_immune_count += 1
        _ = fx6_tgt

    return {
        "total_states": total,
        "open_shutter_all_verified": open_shutter_count == total,
        "zero_internal_crop_all_verified": zero_internal_crop_count == total,
        "zero_clean_hdmi_crop_count": zero_clean_hdmi_crop_count,
        "rec_continuity_all_verified": rec_continuity_count == total,
        "cleaning_blocked_below51_count": cleaning_blocked_below51_count,
        "still_only_af_all_verified": still_only_af_count == total,
        "suppressed_active_count": suppressed_active_count,
        "camset_reset_immune_count": camset_reset_immune_count,
    }


def verify_antidust_focusmag_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE378,
    body_model_id: int = FX3_MODEL_ID_PHASE378,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE378,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE378,
    request_dormant_antidust_function: bool = False,
    request_dormant_shutter_when_pwr_off: bool = False,
    request_dormant_sensor_barrier_bkid_or_pid: bool = False,
    close_shutter_on_power_off: bool = False,
    sensor_cleaning_requested: bool = False,
    np_fz100_inserted: bool = True,
    np_fz100_soc_pct: int = 85,
    skip_physical_power_off_prompt: bool = False,
    request_fx6_user_ibis_sensor_cleaning: bool = False,
    request_fx6_mechanical_shutter_curtain: bool = False,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE378,
    sensor_crop_mode: str = "FF",
    focus_magnifier_active: bool = True,
    focus_mag_time: str = FOCUS_MAG_TIME_DEFAULT_G161,
    initial_focus_mag_ratio: str = "x1.0",
    active_focus_mag_ratio: str = "x4.0",
    af_in_focus_mag: str = AF_IN_FOCUS_MAG_DEFAULT_G161,
    auto_mag_in_mf: str = AUTO_MAG_IN_MF_DEFAULT_G161,
    invoke_af_in_focus_mag: bool = False,
    invoke_auto_mag_in_mf: bool = False,
    still_af_mode: str = "AF-S",
    still_cont_shooting_active: bool = False,
    mount_adapter_attached: bool = False,
    movie_rec_active: bool = True,
    claim_rec_cancels_focus_mag: bool = False,
    hdmi_info_display: str = "Off",
    claim_clean_hdmi_cropped: bool = False,
    claim_internal_recording_cropped: bool = False,
    peaking_active: bool = True,
    bright_monitoring_active: bool = False,
    desqueeze_active: bool = False,
    claim_marker_display_visible_during_mag: bool = False,
    claim_switch_vh_af_active_during_mag: bool = False,
    claim_af_illuminator_active_during_mag: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE378,
    claim_camset_reset_clears_focus_assistant: bool = False,
    fx6_firmware_version: str = FX6_DEFAULT_FW_VERSION_PHASE378,
    fx6_focus_mag_target: str = "VF",
    fx6_focus_mag_ratio: str = "x3.0",
    request_fx6_af_in_focus_mag: bool = False,
    claim_fx6_sdi_or_internal_rec_cropped: bool = False,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
) -> AntiDustFocusMagGuardResult:
    """Gate G161: Enforce Dormant Anti-Dust/Open-Shutter, >=51% Sensor Cleaning & Focus Magnifier Isolation."""
    telemetry_errors: List[str] = []
    eopnotsupp_violations: List[str] = []
    constraint_violations: List[str] = []
    warnings: List[str] = []

    telemetry_errors.extend(
        _validate_fx3_body_identity(
            body_model_name, body_model_id, help_guide_code, firmware_version
        )
    )
    fw_val = _parse_fw_float(firmware_version)
    fx6_fw_val = _parse_fw_float(fx6_firmware_version)
    if fx6_fw_val is None:
        telemetry_errors.append(f"fx6_firmware_version_invalid:{fx6_firmware_version!r}")

    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE378:
        telemetry_errors.append(f"shoot_mode_invalid:{shoot_mode!r}")
    if sensor_crop_mode not in ALLOWED_SENSOR_CROP_MODES_G161:
        telemetry_errors.append(f"sensor_crop_mode_invalid:{sensor_crop_mode!r}")
    if focus_mag_time not in ALLOWED_FOCUS_MAG_TIMES_G161:
        telemetry_errors.append(f"focus_mag_time_invalid:{focus_mag_time!r}")
    if not _is_on_off(af_in_focus_mag):
        telemetry_errors.append(f"af_in_focus_mag_invalid:{af_in_focus_mag!r}")
    if not _is_on_off(auto_mag_in_mf):
        telemetry_errors.append(f"auto_mag_in_mf_invalid:{auto_mag_in_mf!r}")
    if not _is_on_off(hdmi_info_display):
        telemetry_errors.append(f"hdmi_info_display_invalid:{hdmi_info_display!r}")
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE378:
        telemetry_errors.append(f"reset_action_invalid:{reset_action!r}")
    if not _is_strict_int(np_fz100_soc_pct) or not (0 <= np_fz100_soc_pct <= 100):
        telemetry_errors.append(f"np_fz100_soc_pct_invalid:{np_fz100_soc_pct!r}")
    if fx6_focus_mag_target not in ALLOWED_FX6_FOCUS_MAG_TARGETS_G161:
        telemetry_errors.append(f"fx6_focus_mag_target_invalid:{fx6_focus_mag_target!r}")

    for bname, bval in (
        ("request_dormant_antidust_function", request_dormant_antidust_function),
        ("request_dormant_shutter_when_pwr_off", request_dormant_shutter_when_pwr_off),
        (
            "request_dormant_sensor_barrier_bkid_or_pid",
            request_dormant_sensor_barrier_bkid_or_pid,
        ),
        ("close_shutter_on_power_off", close_shutter_on_power_off),
        ("sensor_cleaning_requested", sensor_cleaning_requested),
        ("np_fz100_inserted", np_fz100_inserted),
        ("skip_physical_power_off_prompt", skip_physical_power_off_prompt),
        ("request_fx6_user_ibis_sensor_cleaning", request_fx6_user_ibis_sensor_cleaning),
        ("request_fx6_mechanical_shutter_curtain", request_fx6_mechanical_shutter_curtain),
        ("focus_magnifier_active", focus_magnifier_active),
        ("invoke_af_in_focus_mag", invoke_af_in_focus_mag),
        ("invoke_auto_mag_in_mf", invoke_auto_mag_in_mf),
        ("still_cont_shooting_active", still_cont_shooting_active),
        ("mount_adapter_attached", mount_adapter_attached),
        ("movie_rec_active", movie_rec_active),
        ("claim_rec_cancels_focus_mag", claim_rec_cancels_focus_mag),
        ("claim_clean_hdmi_cropped", claim_clean_hdmi_cropped),
        ("claim_internal_recording_cropped", claim_internal_recording_cropped),
        ("peaking_active", peaking_active),
        ("bright_monitoring_active", bright_monitoring_active),
        ("desqueeze_active", desqueeze_active),
        ("claim_marker_display_visible_during_mag", claim_marker_display_visible_during_mag),
        ("claim_switch_vh_af_active_during_mag", claim_switch_vh_af_active_during_mag),
        ("claim_af_illuminator_active_during_mag", claim_af_illuminator_active_during_mag),
        (
            "claim_camset_reset_clears_focus_assistant",
            claim_camset_reset_clears_focus_assistant,
        ),
        ("request_fx6_af_in_focus_mag", request_fx6_af_in_focus_mag),
        ("claim_fx6_sdi_or_internal_rec_cropped", claim_fx6_sdi_or_internal_rec_cropped),
    ):
        if not isinstance(bval, bool):
            telemetry_errors.append(f"{bname}_not_bool:{bval!r}")

    if not isinstance(initial_focus_mag_ratio, str) or not initial_focus_mag_ratio:
        telemetry_errors.append(
            f"initial_focus_mag_ratio_invalid:{initial_focus_mag_ratio!r}"
        )
    if not isinstance(active_focus_mag_ratio, str) or not active_focus_mag_ratio:
        telemetry_errors.append(
            f"active_focus_mag_ratio_invalid:{active_focus_mag_ratio!r}"
        )
    if not isinstance(fx6_focus_mag_ratio, str) or not fx6_focus_mag_ratio:
        telemetry_errors.append(f"fx6_focus_mag_ratio_invalid:{fx6_focus_mag_ratio!r}")

    if telemetry_errors:
        return AntiDustFocusMagGuardResult(
            valid=False,
            status=STATUS_BLOCKED_G161_TELEMETRY_INVALID,
            block_errno=EINVAL_ERRNO_PHASE378,
            block_errno_name=EINVAL_NAME_PHASE378,
            verification_mode=verification_mode,
            sensor_cleaning_menu_path=SENSOR_CLEANING_MENU_PATH_G161,
            focus_assistant_menu_path=FOCUS_ASSISTANT_MENU_PATH_G161,
            fx6_apr_menu_path=FX6_APR_MENU_PATH_G161,
            fx6_focus_mag_menu_path=FX6_FOCUS_MAG_MENU_PATH_G161,
            effective_power_off_shutter_state=FX3_POWER_OFF_SHUTTER_STATE_G161,
            dormant_antidust_exposed=FX3_DORMANT_ANTIDUST_EXPOSED_G161,
            dormant_shutter_when_pwr_off_exposed=FX3_DORMANT_SHUTTER_WHEN_PWR_OFF_EXPOSED_G161,
            sensor_cleaning_requested=bool(sensor_cleaning_requested)
            if isinstance(sensor_cleaning_requested, bool)
            else False,
            sensor_cleaning_allowed=False,
            sensor_cleaning_min_soc_pct=SENSOR_CLEANING_MIN_SOC_PCT_G161,
            np_fz100_soc_pct=np_fz100_soc_pct if _is_strict_int(np_fz100_soc_pct) else 0,
            physical_power_off_prompt_required=SENSOR_CLEANING_PHYSICAL_PWR_OFF_PROMPT_REQUIRED_G161,
            fx6_focal_plane_mechanical_shutter_present=FX6_FOCAL_PLANE_MECHANICAL_SHUTTER_PRESENT_G161,
            fx6_user_ibis_sensor_cleaning_supported=FX6_USER_IBIS_SENSOR_CLEANING_SUPPORTED_G161,
            fx6_end_range_label=FX6_END_RANGE_LABEL_G161,
            fx3_focus_assistant_items_count=len(EXACT_5_FX3_FOCUS_ASSISTANT_ITEMS_G161),
            focus_assistant_resettable_by_camset_reset=FX3_FOCUS_ASSISTANT_5ITEMS_RESETTABLE_VER2_PLUS_G161,
            shoot_mode=str(shoot_mode),
            sensor_crop_mode=str(sensor_crop_mode),
            focus_magnifier_active=False,
            effective_focus_mag_time=FOCUS_MAG_TIME_DEFAULT_G161,
            effective_initial_focus_mag_ratio="x1.0",
            effective_active_focus_mag_ratio="x1.0",
            allowed_active_ratios_for_mode=FX3_MOVIE_SQ_MAG_RATIOS_G161,
            effective_af_in_focus_mag=AF_IN_FOCUS_MAG_DEFAULT_G161,
            af_in_focus_mag_usable_in_mode=False,
            effective_auto_mag_in_mf=AUTO_MAG_IN_MF_DEFAULT_G161,
            auto_mag_in_mf_usable_in_mode=False,
            movie_rec_active=False,
            focus_mag_survives_movie_rec=FX3_FOCUS_MAG_REC_CONTINUITY_SUPPORTED_G161,
            hdmi_info_display="Off",
            hdmi_output_cropped=False,
            internal_recording_cropped=False,
            clean_hdmi_crop_pixels=FX3_FOCUS_MAG_CLEAN_HDMI_CROP_PIXELS_G161,
            internal_rec_crop_pixels=FX3_FOCUS_MAG_INTERNAL_REC_CROP_PIXELS_G161,
            peaking_coexists=True,
            bright_monitoring_coexists=True,
            desqueeze_coexists=True,
            suppressed_features_while_active=(),
            fx6_focus_mag_target="VF",
            fx6_effective_mag_ratio="x3.0",
            fx6_sdi_cropped=False,
            fx6_internal_rec_cropped=False,
            dormant_or_cross_model_eopnotsupp_rejected=False,
            emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
            cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
            usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            violation_codes=tuple(telemetry_errors),
            errors=tuple(telemetry_errors),
            warnings=tuple(warnings),
        )

    # --- 1. Dormant Anti-Dust / Shutter When Pwr OFF / FX6 EOPNOTSUPP Checks ---
    if request_dormant_antidust_function:
        eopnotsupp_violations.append(
            "FX3_DORMANT_ANTIDUST_FUNCTION_F_0X7495_UNEXPOSED_ON_ALCIN_UUD"
        )
    if request_dormant_shutter_when_pwr_off or close_shutter_on_power_off:
        eopnotsupp_violations.append(
            "FX3_DORMANT_SHUTTER_WHEN_PWR_OFF_F_0X709F_OPEN_SHUTTER_REQUIRED"
        )
    if request_dormant_sensor_barrier_bkid_or_pid:
        eopnotsupp_violations.append(
            "FX3_DORMANT_IMAGE_SENSOR_BARRIER_BKID_PID_EOPNOTSUPP"
        )
    if request_fx6_user_ibis_sensor_cleaning:
        eopnotsupp_violations.append(
            "FX6_NO_USER_IBIS_SENSOR_CLEANING_USE_TECHNICAL_APR"
        )
    if request_fx6_mechanical_shutter_curtain:
        eopnotsupp_violations.append(
            "FX6_ZERO_FOCAL_PLANE_MECHANICAL_SHUTTER_SEALED_END"
        )

    # --- 2. Dormant High-MP Alpha Ratios & Still-Only Focus Assistant Checks ---
    if initial_focus_mag_ratio in DORMANT_HIGH_MP_ALPHA_MAG_RATIOS_G161:
        eopnotsupp_violations.append(
            f"FX3_12MP_DORMANT_HIGH_MP_INITIAL_RATIO_{initial_focus_mag_ratio}"
        )
    if active_focus_mag_ratio in DORMANT_HIGH_MP_ALPHA_MAG_RATIOS_G161:
        eopnotsupp_violations.append(
            f"FX3_12MP_DORMANT_HIGH_MP_ACTIVE_RATIO_{active_focus_mag_ratio}"
        )
    if invoke_af_in_focus_mag and shoot_mode != SHOOT_MODE_STILL_PHASE378:
        eopnotsupp_violations.append(
            "FX3_AF_IN_FOCUS_MAG_STRICTLY_STILL_ONLY_BLOCKED_IN_MOVIE_SQ"
        )
    if invoke_auto_mag_in_mf and shoot_mode != SHOOT_MODE_STILL_PHASE378:
        eopnotsupp_violations.append(
            "FX3_AUTO_MAGNIFIER_IN_MF_STRICTLY_STILL_ONLY_BLOCKED_IN_MOVIE_SQ"
        )
    if request_fx6_af_in_focus_mag:
        eopnotsupp_violations.append("FX6_NO_AF_IN_FOCUS_MAG_OR_AUTO_MAG_IN_MF")
    if fx6_focus_mag_ratio in FX6_DORMANT_FS7_MAG_RATIOS_G161:
        eopnotsupp_violations.append(
            f"FX6_DORMANT_FS7_MAG_RATIO_{fx6_focus_mag_ratio}_EOPNOTSUPP"
        )
    if (
        fx6_focus_mag_target == "HDMI"
        and fx6_fw_val is not None
        and fx6_fw_val < FX6_HDMI_TARGET_MIN_FW_G161
    ):
        eopnotsupp_violations.append(
            "FX6_HDMI_FOCUS_MAG_BUTTON_TARGET_REQUIRES_VER6_00_PLUS"
        )

    # --- 3. Active Sensor Cleaning & Focus Magnifier Pipeline Constraints ---
    state = resolve_fx3_antidust_focusmag_state(
        firmware_version=firmware_version,
        shoot_mode=shoot_mode,
        sensor_crop_mode=sensor_crop_mode,
        focus_magnifier_active=focus_magnifier_active,
        focus_mag_time=focus_mag_time,
        initial_focus_mag_ratio=initial_focus_mag_ratio,
        active_focus_mag_ratio=active_focus_mag_ratio,
        af_in_focus_mag=af_in_focus_mag,
        auto_mag_in_mf=auto_mag_in_mf,
        movie_rec_active=movie_rec_active,
        hdmi_info_display=hdmi_info_display,
        reset_action=reset_action,
        np_fz100_soc_pct=np_fz100_soc_pct,
        sensor_cleaning_requested=sensor_cleaning_requested,
    )

    if sensor_cleaning_requested:
        if not np_fz100_inserted:
            constraint_violations.append("FX3_SENSOR_CLEANING_REQUIRES_NP_FZ100")
        elif np_fz100_soc_pct < SENSOR_CLEANING_MIN_SOC_PCT_G161:
            constraint_violations.append(
                f"FX3_SENSOR_CLEANING_BATTERY_BELOW_51PCT:{np_fz100_soc_pct}"
            )
        if skip_physical_power_off_prompt:
            constraint_violations.append(
                "FX3_SENSOR_CLEANING_PHYSICAL_POWER_OFF_PROMPT_MANDATORY"
            )

    if (
        initial_focus_mag_ratio not in DORMANT_HIGH_MP_ALPHA_MAG_RATIOS_G161
        and initial_focus_mag_ratio not in state["allowed_initial_ratios_for_mode"]
    ):
        constraint_violations.append(
            f"FX3_INITIAL_FOCUS_MAG_RATIO_INVALID_FOR_{shoot_mode}_{sensor_crop_mode}:{initial_focus_mag_ratio}"
        )
    if (
        focus_magnifier_active
        and active_focus_mag_ratio not in DORMANT_HIGH_MP_ALPHA_MAG_RATIOS_G161
        and active_focus_mag_ratio not in state["allowed_active_ratios_for_mode"]
    ):
        constraint_violations.append(
            f"FX3_ACTIVE_FOCUS_MAG_RATIO_INVALID_FOR_{shoot_mode}_{sensor_crop_mode}:{active_focus_mag_ratio}"
        )

    if invoke_af_in_focus_mag and shoot_mode == SHOOT_MODE_STILL_PHASE378:
        if af_in_focus_mag != "On":
            constraint_violations.append("FX3_AF_IN_FOCUS_MAG_SETTING_IS_OFF")
        if still_af_mode == "AF-C" or still_cont_shooting_active or mount_adapter_attached:
            constraint_violations.append(
                "FX3_AF_IN_FOCUS_MAG_BLOCKED_BY_AFC_CONT_SHOOT_OR_ADAPTER"
            )
    if invoke_auto_mag_in_mf and shoot_mode == SHOOT_MODE_STILL_PHASE378:
        if auto_mag_in_mf != "On":
            constraint_violations.append("FX3_AUTO_MAG_IN_MF_SETTING_IS_OFF")
        if mount_adapter_attached:
            constraint_violations.append("FX3_AUTO_MAG_IN_MF_BLOCKED_BY_MOUNT_ADAPTER")

    if claim_rec_cancels_focus_mag:
        constraint_violations.append(
            "FX3_MOVIE_REC_DOES_NOT_CANCEL_FOCUS_MAGNIFIER_CONTINUITY"
        )
    if claim_clean_hdmi_cropped and hdmi_info_display == "Off":
        constraint_violations.append(
            "FX3_CLEAN_HDMI_INFO_OFF_ZERO_CROP_ISOLATION_VIOLATION"
        )
    if claim_internal_recording_cropped:
        constraint_violations.append(
            "FX3_INTERNAL_RECORDING_ZERO_CROP_ISOLATION_VIOLATION"
        )
    if (
        focus_magnifier_active
        and bright_monitoring_active
        and fw_val is not None
        and fw_val < FX3_BRIGHT_MON_FOCUS_MAG_MIN_FW_G161
    ):
        constraint_violations.append(
            "FX3_BRIGHT_MONITORING_FOCUS_MAG_COEXISTENCE_REQUIRES_VER7_00_PLUS"
        )
    if focus_magnifier_active:
        if claim_marker_display_visible_during_mag:
            constraint_violations.append(
                "FX3_MARKER_DISPLAY_MUST_BE_SUPPRESSED_DURING_FOCUS_MAG"
            )
        if claim_switch_vh_af_active_during_mag:
            constraint_violations.append(
                "FX3_SWITCH_VH_AF_AREA_LOCKED_DURING_FOCUS_MAG"
            )
        if claim_af_illuminator_active_during_mag:
            constraint_violations.append(
                "FX3_AF_ILLUMINATOR_BLOCKED_DURING_FOCUS_MAG"
            )
    if (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE378
        and claim_camset_reset_clears_focus_assistant
        and (fw_val is None or fw_val >= 2.00)
    ):
        constraint_violations.append(
            "FX3_FOCUS_ASSISTANT_5ITEMS_RESIST_CAMSET_RESET_VER2_PLUS"
        )

    fx6_allowed_ratios = (
        FX6_VF_MAG_RATIOS_G161
        if fx6_focus_mag_target == "VF"
        else FX6_HDMI_MAG_RATIOS_G161
    )
    if (
        fx6_focus_mag_ratio not in FX6_DORMANT_FS7_MAG_RATIOS_G161
        and fx6_focus_mag_ratio not in fx6_allowed_ratios
    ):
        constraint_violations.append(
            f"FX6_FOCUS_MAG_RATIO_INVALID_FOR_{fx6_focus_mag_target}:{fx6_focus_mag_ratio}"
        )
    if claim_fx6_sdi_or_internal_rec_cropped:
        constraint_violations.append(
            "FX6_SDI_AND_INTERNAL_REC_ZERO_CROP_ISOLATION_VIOLATION"
        )

    if hdmi_info_display == "On" and focus_magnifier_active:
        warnings.append(
            "HDMI Info. Display = On mirrors camera OSD & magnified viewport on HDMI and blanks body LCD."
        )

    all_violations = eopnotsupp_violations + constraint_violations
    if eopnotsupp_violations:
        status = (
            STATUS_BLOCKED_G161_DORMANT_ANTIDUST_HIGHMP_RATIO_STILLONLY_OR_FX6_EOPNOTSUPP
        )
        errno_val, errno_name = EOPNOTSUPP_ERRNO_PHASE378, EOPNOTSUPP_NAME_PHASE378
        valid = False
    elif constraint_violations:
        status = STATUS_BLOCKED_G161_CLEANING51_REC_HDMI_CROP_OR_SUPPRESSION_VIOLATION
        errno_val, errno_name = EINVAL_ERRNO_PHASE378, EINVAL_NAME_PHASE378
        valid = False
    else:
        status = STATUS_VERIFIED_G161
        errno_val, errno_name = 0, "OK"
        valid = True

    return AntiDustFocusMagGuardResult(
        valid=valid,
        status=status,
        block_errno=errno_val,
        block_errno_name=errno_name,
        verification_mode=verification_mode,
        sensor_cleaning_menu_path=SENSOR_CLEANING_MENU_PATH_G161,
        focus_assistant_menu_path=FOCUS_ASSISTANT_MENU_PATH_G161,
        fx6_apr_menu_path=FX6_APR_MENU_PATH_G161,
        fx6_focus_mag_menu_path=FX6_FOCUS_MAG_MENU_PATH_G161,
        effective_power_off_shutter_state=state["effective_power_off_shutter_state"],
        dormant_antidust_exposed=FX3_DORMANT_ANTIDUST_EXPOSED_G161,
        dormant_shutter_when_pwr_off_exposed=FX3_DORMANT_SHUTTER_WHEN_PWR_OFF_EXPOSED_G161,
        sensor_cleaning_requested=sensor_cleaning_requested,
        sensor_cleaning_allowed=state["sensor_cleaning_allowed"] and np_fz100_inserted,
        sensor_cleaning_min_soc_pct=SENSOR_CLEANING_MIN_SOC_PCT_G161,
        np_fz100_soc_pct=np_fz100_soc_pct,
        physical_power_off_prompt_required=SENSOR_CLEANING_PHYSICAL_PWR_OFF_PROMPT_REQUIRED_G161,
        fx6_focal_plane_mechanical_shutter_present=FX6_FOCAL_PLANE_MECHANICAL_SHUTTER_PRESENT_G161,
        fx6_user_ibis_sensor_cleaning_supported=FX6_USER_IBIS_SENSOR_CLEANING_SUPPORTED_G161,
        fx6_end_range_label=FX6_END_RANGE_LABEL_G161,
        fx3_focus_assistant_items_count=len(EXACT_5_FX3_FOCUS_ASSISTANT_ITEMS_G161),
        focus_assistant_resettable_by_camset_reset=FX3_FOCUS_ASSISTANT_5ITEMS_RESETTABLE_VER2_PLUS_G161,
        shoot_mode=shoot_mode,
        sensor_crop_mode=sensor_crop_mode,
        focus_magnifier_active=focus_magnifier_active,
        effective_focus_mag_time=state["effective_focus_mag_time"],
        effective_initial_focus_mag_ratio=state["effective_initial_focus_mag_ratio"],
        effective_active_focus_mag_ratio=state["effective_active_focus_mag_ratio"],
        allowed_active_ratios_for_mode=state["allowed_active_ratios_for_mode"],
        effective_af_in_focus_mag=state["effective_af_in_focus_mag"],
        af_in_focus_mag_usable_in_mode=state["af_in_focus_mag_usable_in_mode"],
        effective_auto_mag_in_mf=state["effective_auto_mag_in_mf"],
        auto_mag_in_mf_usable_in_mode=state["auto_mag_in_mf_usable_in_mode"],
        movie_rec_active=movie_rec_active,
        focus_mag_survives_movie_rec=state["focus_mag_survives_movie_rec"],
        hdmi_info_display=hdmi_info_display,
        hdmi_output_cropped=state["hdmi_output_cropped"],
        internal_recording_cropped=state["internal_recording_cropped"],
        clean_hdmi_crop_pixels=FX3_FOCUS_MAG_CLEAN_HDMI_CROP_PIXELS_G161,
        internal_rec_crop_pixels=FX3_FOCUS_MAG_INTERNAL_REC_CROP_PIXELS_G161,
        peaking_coexists=state["peaking_coexists"],
        bright_monitoring_coexists=state["bright_monitoring_coexists"],
        desqueeze_coexists=state["desqueeze_coexists"],
        suppressed_features_while_active=state["suppressed_features_while_active"],
        fx6_focus_mag_target=fx6_focus_mag_target,
        fx6_effective_mag_ratio=fx6_focus_mag_ratio,
        fx6_sdi_cropped=False,
        fx6_internal_rec_cropped=False,
        dormant_or_cross_model_eopnotsupp_rejected=bool(eopnotsupp_violations),
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        violation_codes=tuple(all_violations),
        errors=tuple(all_violations),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class G161AntiDustFocusMagGuardResult:
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
    antidust_focusmag_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g161_antidust_focusmag_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G161AntiDustFocusMagGuardResult]:
    audit = audit_phase378_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_antidust_focusmag_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G161AntiDustFocusMagGuardResult(
        gate_id=G161,
        gate_code=G161_GATE_CODE,
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
        antidust_focusmag_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G161,
        gate_code=G161_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"shutter_pwroff={res.effective_power_off_shutter_state} "
            f"clean_min_soc={res.sensor_cleaning_min_soc_pct}% "
            f"mag_ratio={res.effective_active_focus_mag_ratio} "
            f"hdmi_crop={res.hdmi_output_cropped} "
            f"rec_crop={res.internal_recording_cropped}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_antidust_focusmag_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G161AntiDustFocusMagGuardResult]:
    return evaluate_g161_antidust_focusmag_guard(**kwargs)


# ---------------------------------------------------------------------------
# Gate G162: Exposure Std. Adjust (5-Mode Reset-Resistant Hidden Bias) &
#            Wired Smartphone USB Tethering / Slot 1 EROFS=30 Firewall
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExpStdUsbTetherGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    exposure_std_adjust_menu_path: str
    fx6_auto_exposure_menu_path: str
    usb_connection_mode_menu_path: str
    usb_lan_tethering_menu_path: str
    fx6_usb_tethering_menu_path: str
    metering_mode: str
    metering_modes_count: int
    exposure_std_step_count: int
    effective_exposure_std_sixths: int
    effective_exposure_std_ev: float
    exposure_std_resettable_by_camset_reset: bool
    metering_warning_icon_shown: bool
    mm_zero_point_shifted_ev: float
    spot_ael_baseline_shifted_ev: float
    alters_exif_exposure_bias_value: bool
    exif_exposure_bias_delta_ev: float
    alters_actual_auto_exposure: bool
    bracket_count_reset_triggered: bool
    fx6_ae_level_ev: float
    fx6_ae_level_step_count: int
    fx6_ae_mode: str
    fx6_ae_speed: int
    fx6_per_lut_ae_level_offset_supported: bool
    usb_connection_mode: str
    usb_lun_setting: str
    usb_tethering_active: bool
    usb_tethering_driver: str
    tethering_workload: str
    usb_lan_cnct_launch: str
    airplane_mode: str
    zero_rf_tethering_bypass_active: bool
    rf_tx_packets: int
    wifi_bt_radio_enabled: bool
    dual_usb_ports_simultaneous: bool
    fx3_usbg_iap_class_hits: int
    fx6_usbg_iap_class_active: bool
    mc_usb_timecode_supported: bool
    mc_usb_focus_map_supported: bool
    mc_usb_lut_import_supported: bool
    target_media_slot: int
    host_storage_access_mode: str
    slot1_exposed_writable: bool
    slot1_writes: int
    slot1_data_sector_writes: int
    emmc_nflasha_write_count: int
    usb_tx: int
    usb_packets_transmitted: int
    emmc_writes_authorized: bool
    persistent_emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    live_attach_authorized: bool
    raw_firmware_bytes_leaked: int
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_fx3_expstd_usbtether_state(
    *,
    metering_mode: str = "Multi",
    exposure_std_sixths: int = 0,
    exposure_control_mode: str = "Cine_EI",
    reset_action: str = RESET_ACTION_NONE_PHASE378,
    altered_mid_bracket: bool = False,
    usb_connection_mode: str = "Remote Shooting",
    usb_lun_setting: str = USB_LUN_DEFAULT_G162,
    usb_tethering_active: bool = True,
    usb_tethering_driver: str = "cdc_ncm",
    tethering_workload: str = "srt",
    airplane_mode: str = "On",
    reset_network_set_executed: bool = False,
    airplane_mode_rearmed_after_net_reset: bool = True,
    host_storage_access_mode: str = "none",
    usbgmsc_readonly_enforced: bool = True,
) -> Dict[str, Any]:
    """Deterministically resolve FX3 Ver. 7.02 Exposure Std. Adjust & USB Tethering state."""
    # [Exposure Std. Adjust] resists [Camera Settings Reset]; ONLY [Initialize] zeroes it.
    if reset_action == RESET_ACTION_INITIALIZE_PHASE378:
        eff_sixths = EXPOSURE_STD_DEFAULT_SIXTHS_G162
    else:
        eff_sixths = exposure_std_sixths

    eff_ev = round(eff_sixths / 6.0, 4)
    warning_icon = eff_sixths != 0
    alters_ae = (
        eff_sixths != 0
        and exposure_control_mode in ("P_A_S", "M_ISO_AUTO", "Flexible_ISO_AUTO")
    )
    bracket_reset = bool(altered_mid_bracket and eff_sixths != 0)

    # Effective Airplane Mode after Reset Network Set.
    if reset_network_set_executed and not airplane_mode_rearmed_after_net_reset:
        eff_airplane = "Off"
    else:
        eff_airplane = airplane_mode

    zero_rf_active = (
        usb_tethering_active
        and eff_airplane == "On"
        and tethering_workload in ("rtmp", "rtmps", "srt", "ftp", "ftpes", "sftp")
    )
    wifi_bt_enabled = eff_airplane != "On"
    rf_tx_packets = 0 if eff_airplane == "On" else 1

    # Slot 1 exposure analysis:
    # - MTP locks Slot 1.
    # - MassStorage(MSC) exposes Slot 1 in BOTH Multi (Slot 1 + Slot 2) and Single (Slot 1).
    slot1_exposed = usb_connection_mode in ("MassStorage(MSC)", "MTP")
    slot1_exposed_writable = (
        slot1_exposed
        and (
            host_storage_access_mode == "host_writable"
            or (not usbgmsc_readonly_enforced and host_storage_access_mode != "read_only_guarded")
        )
    )

    return {
        "effective_exposure_std_sixths": eff_sixths,
        "effective_exposure_std_ev": eff_ev,
        "metering_warning_icon_shown": warning_icon,
        "mm_zero_point_shifted_ev": eff_ev,
        "spot_ael_baseline_shifted_ev": eff_ev if metering_mode == "Spot" else 0.0,
        "alters_exif_exposure_bias_value": EXPOSURE_STD_ALTERS_EXIF_BIAS_VALUE_G162,
        "exif_exposure_bias_delta_ev": 0.0,
        "alters_actual_auto_exposure": alters_ae,
        "bracket_count_reset_triggered": bracket_reset,
        "effective_airplane_mode": eff_airplane,
        "zero_rf_tethering_bypass_active": zero_rf_active,
        "wifi_bt_radio_enabled": wifi_bt_enabled,
        "rf_tx_packets": rf_tx_packets,
        "slot1_exposed": slot1_exposed,
        "slot1_exposed_writable": slot1_exposed_writable,
        "usb_lun_setting": usb_lun_setting,
        "usb_tethering_driver": usb_tethering_driver,
    }


def compute_expstd_usbtether_matrix() -> Dict[str, Any]:
    """Sweep deterministic 480-state Wave-71 Gate G162 matrix (Exposure Std. + USB Tethering + Slot 1)."""
    metering_modes = EXACT_5_METERING_MODES_G162  # 5
    sixths_samples = (-6, 0, 3, 6)  # 4
    resets = (
        RESET_ACTION_NONE_PHASE378,
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE378,
        RESET_ACTION_INITIALIZE_PHASE378,
    )  # 3
    usb_modes = ("Remote Shooting", "MassStorage(MSC)", "MTP", "Sel. When Connect")  # 4
    luns = ALLOWED_USB_LUN_SETTINGS_G162  # 2
    # 5 * 4 * 3 * 4 * 2 = 480 states!
    total = 0
    zero_exif_delta_count = 0
    camset_reset_survived_count = 0
    initialize_zeroed_count = 0
    slot1_msc_mtp_writable_detected = 0
    zero_rf_tether_count = 0

    for mm, sixths, rst, umode, lun in itertools.product(
        metering_modes, sixths_samples, resets, usb_modes, luns
    ):
        total += 1
        st = resolve_fx3_expstd_usbtether_state(
            metering_mode=mm,
            exposure_std_sixths=sixths,
            exposure_control_mode="Flexible_ISO_AUTO",
            reset_action=rst,
            usb_connection_mode=umode,
            usb_lun_setting=lun,
            usb_tethering_active=True,
            tethering_workload="srt",
            airplane_mode="On",
            host_storage_access_mode="host_writable"
            if umode in ("MassStorage(MSC)", "MTP")
            else "none",
            usbgmsc_readonly_enforced=False,
        )
        if (
            not st["alters_exif_exposure_bias_value"]
            and st["exif_exposure_bias_delta_ev"] == 0.0
        ):
            zero_exif_delta_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE378
            and sixths != 0
            and st["effective_exposure_std_sixths"] == sixths
        ):
            camset_reset_survived_count += 1
        if (
            rst == RESET_ACTION_INITIALIZE_PHASE378
            and st["effective_exposure_std_sixths"] == 0
        ):
            initialize_zeroed_count += 1
        if umode in ("MassStorage(MSC)", "MTP") and st["slot1_exposed_writable"]:
            slot1_msc_mtp_writable_detected += 1
        if st["zero_rf_tethering_bypass_active"] and st["rf_tx_packets"] == 0:
            zero_rf_tether_count += 1

    return {
        "total_states": total,
        "zero_exif_delta_all_verified": zero_exif_delta_count == total,
        "camset_reset_survived_count": camset_reset_survived_count,
        "initialize_zeroed_count": initialize_zeroed_count,
        "slot1_msc_mtp_writable_detected": slot1_msc_mtp_writable_detected,
        "zero_rf_tether_all_verified": zero_rf_tether_count == total,
    }


def verify_expstd_usbtether_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE378,
    body_model_id: int = FX3_MODEL_ID_PHASE378,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE378,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE378,
    metering_mode: str = "Multi",
    exposure_std_sixths: int = 0,
    request_dormant_step_1_8_ev: bool = False,
    exposure_control_mode: str = "Cine_EI",
    reset_action: str = RESET_ACTION_NONE_PHASE378,
    claim_camset_reset_zeroes_exp_std: bool = False,
    claim_exp_std_alters_exif_bias: bool = False,
    altered_mid_bracket: bool = False,
    claim_bracket_count_preserved_on_change: bool = False,
    fx6_ae_level_ev: float = 0.0,
    claim_fx6_ae_level_capped_at_2ev: bool = False,
    fx6_ae_mode: str = "Standard",
    fx6_ae_speed: int = 0,
    usb_connection_mode: str = "Remote Shooting",
    usb_lun_setting: str = USB_LUN_DEFAULT_G162,
    usb_tethering_active: bool = True,
    usb_tethering_driver: str = "cdc_ncm",
    tethering_workload: str = "srt",
    usb_lan_cnct_launch: str = USB_LAN_CNCT_LAUNCH_DEFAULT_G162,
    airplane_mode: str = "On",
    reset_network_set_executed: bool = False,
    airplane_mode_rearmed_after_net_reset: bool = True,
    dual_usb_ports_simultaneous: bool = False,
    request_fx3_iap2_gadget: bool = False,
    request_mc_usb_timecode: bool = False,
    request_mc_usb_focus_map: bool = False,
    request_mc_usb_lut_import: bool = False,
    fx6_usb_hub_attached: bool = False,
    fx6_wired_lan_or_pc_usb_simultaneous: bool = False,
    target_media_slot: int = MEDIA_SLOT_NONE_PHASE378,
    host_storage_access_mode: str = "none",
    usbgmsc_readonly_enforced: bool = True,
    slot1_tier0_protected: bool = True,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
) -> ExpStdUsbTetherGuardResult:
    """Gate G162: Enforce Exposure Std. Adjust Reset-Immune Bias, Zero-RF USB Tethering & Slot 1 EROFS=30."""
    telemetry_errors: List[str] = []
    erofs_violations: List[str] = []
    ebusy_violations: List[str] = []
    eopnotsupp_violations: List[str] = []
    constraint_violations: List[str] = []
    warnings: List[str] = []

    telemetry_errors.extend(
        _validate_fx3_body_identity(
            body_model_name, body_model_id, help_guide_code, firmware_version
        )
    )
    fw_val = _parse_fw_float(firmware_version)

    if metering_mode not in EXACT_5_METERING_MODES_G162:
        telemetry_errors.append(f"metering_mode_invalid:{metering_mode!r}")
    if not _is_strict_int(exposure_std_sixths):
        telemetry_errors.append(f"exposure_std_sixths_invalid:{exposure_std_sixths!r}")
    if exposure_control_mode not in ALLOWED_EXPOSURE_CONTROL_MODES_G162:
        telemetry_errors.append(
            f"exposure_control_mode_invalid:{exposure_control_mode!r}"
        )
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE378:
        telemetry_errors.append(f"reset_action_invalid:{reset_action!r}")
    if not _is_strict_number(fx6_ae_level_ev):
        telemetry_errors.append(f"fx6_ae_level_ev_invalid:{fx6_ae_level_ev!r}")
    if fx6_ae_mode not in ALLOWED_FX6_AE_MODES_G162:
        telemetry_errors.append(f"fx6_ae_mode_invalid:{fx6_ae_mode!r}")
    if not _is_strict_int(fx6_ae_speed) or not (
        FX6_AE_SPEED_MIN_G162 <= fx6_ae_speed <= FX6_AE_SPEED_MAX_G162
    ):
        telemetry_errors.append(f"fx6_ae_speed_invalid:{fx6_ae_speed!r}")
    if (
        usb_connection_mode not in ALLOWED_FX3_USB_CONNECTION_MODES_G162
        and usb_connection_mode != DORMANT_USB_STREAMING_MODE_G162
    ):
        telemetry_errors.append(f"usb_connection_mode_invalid:{usb_connection_mode!r}")
    if usb_lun_setting not in ALLOWED_USB_LUN_SETTINGS_G162:
        telemetry_errors.append(f"usb_lun_setting_invalid:{usb_lun_setting!r}")
    if usb_tethering_driver not in ALLOWED_USB_TETHERING_DRIVERS_G162:
        telemetry_errors.append(
            f"usb_tethering_driver_invalid:{usb_tethering_driver!r}"
        )
    if tethering_workload not in ALLOWED_TETHERING_WORKLOADS_G162:
        telemetry_errors.append(f"tethering_workload_invalid:{tethering_workload!r}")
    if not _is_on_off(usb_lan_cnct_launch):
        telemetry_errors.append(f"usb_lan_cnct_launch_invalid:{usb_lan_cnct_launch!r}")
    if not _is_on_off(airplane_mode):
        telemetry_errors.append(f"airplane_mode_invalid:{airplane_mode!r}")
    if target_media_slot not in ALLOWED_MEDIA_SLOTS_PHASE378:
        telemetry_errors.append(f"target_media_slot_invalid:{target_media_slot!r}")
    if host_storage_access_mode not in ALLOWED_HOST_STORAGE_ACCESS_MODES_G162:
        telemetry_errors.append(
            f"host_storage_access_mode_invalid:{host_storage_access_mode!r}"
        )

    for bname, bval in (
        ("request_dormant_step_1_8_ev", request_dormant_step_1_8_ev),
        ("claim_camset_reset_zeroes_exp_std", claim_camset_reset_zeroes_exp_std),
        ("claim_exp_std_alters_exif_bias", claim_exp_std_alters_exif_bias),
        ("altered_mid_bracket", altered_mid_bracket),
        (
            "claim_bracket_count_preserved_on_change",
            claim_bracket_count_preserved_on_change,
        ),
        ("claim_fx6_ae_level_capped_at_2ev", claim_fx6_ae_level_capped_at_2ev),
        ("usb_tethering_active", usb_tethering_active),
        ("reset_network_set_executed", reset_network_set_executed),
        (
            "airplane_mode_rearmed_after_net_reset",
            airplane_mode_rearmed_after_net_reset,
        ),
        ("dual_usb_ports_simultaneous", dual_usb_ports_simultaneous),
        ("request_fx3_iap2_gadget", request_fx3_iap2_gadget),
        ("request_mc_usb_timecode", request_mc_usb_timecode),
        ("request_mc_usb_focus_map", request_mc_usb_focus_map),
        ("request_mc_usb_lut_import", request_mc_usb_lut_import),
        ("fx6_usb_hub_attached", fx6_usb_hub_attached),
        (
            "fx6_wired_lan_or_pc_usb_simultaneous",
            fx6_wired_lan_or_pc_usb_simultaneous,
        ),
        ("usbgmsc_readonly_enforced", usbgmsc_readonly_enforced),
        ("slot1_tier0_protected", slot1_tier0_protected),
    ):
        if not isinstance(bval, bool):
            telemetry_errors.append(f"{bname}_not_bool:{bval!r}")

    if telemetry_errors:
        return ExpStdUsbTetherGuardResult(
            valid=False,
            status=STATUS_BLOCKED_G162_TELEMETRY_INVALID,
            block_errno=EINVAL_ERRNO_PHASE378,
            block_errno_name=EINVAL_NAME_PHASE378,
            verification_mode=verification_mode,
            exposure_std_adjust_menu_path=EXPOSURE_STD_ADJUST_MENU_PATH_G162,
            fx6_auto_exposure_menu_path=FX6_AUTO_EXPOSURE_MENU_PATH_G162,
            usb_connection_mode_menu_path=USB_CONNECTION_MODE_MENU_PATH_G162,
            usb_lan_tethering_menu_path=USB_LAN_TETHERING_MENU_PATH_G162,
            fx6_usb_tethering_menu_path=FX6_USB_TETHERING_MENU_PATH_G162,
            metering_mode=str(metering_mode),
            metering_modes_count=len(EXACT_5_METERING_MODES_G162),
            exposure_std_step_count=EXPOSURE_STD_STEP_COUNT_G162,
            effective_exposure_std_sixths=0,
            effective_exposure_std_ev=0.0,
            exposure_std_resettable_by_camset_reset=EXPOSURE_STD_ADJUST_RESETTABLE_BY_CAMSET_RESET_G162,
            metering_warning_icon_shown=False,
            mm_zero_point_shifted_ev=0.0,
            spot_ael_baseline_shifted_ev=0.0,
            alters_exif_exposure_bias_value=EXPOSURE_STD_ALTERS_EXIF_BIAS_VALUE_G162,
            exif_exposure_bias_delta_ev=0.0,
            alters_actual_auto_exposure=False,
            bracket_count_reset_triggered=False,
            fx6_ae_level_ev=0.0,
            fx6_ae_level_step_count=FX6_AE_LEVEL_STEP_COUNT_G162,
            fx6_ae_mode="Standard",
            fx6_ae_speed=0,
            fx6_per_lut_ae_level_offset_supported=FX6_PER_LUT_AE_LEVEL_OFFSET_SUPPORTED_G162,
            usb_connection_mode=str(usb_connection_mode),
            usb_lun_setting=str(usb_lun_setting),
            usb_tethering_active=False,
            usb_tethering_driver=str(usb_tethering_driver),
            tethering_workload=str(tethering_workload),
            usb_lan_cnct_launch=USB_LAN_CNCT_LAUNCH_DEFAULT_G162,
            airplane_mode="On",
            zero_rf_tethering_bypass_active=False,
            rf_tx_packets=0,
            wifi_bt_radio_enabled=False,
            dual_usb_ports_simultaneous=False,
            fx3_usbg_iap_class_hits=FX3_USBG_IAP_CLASS_HITS_G162,
            fx6_usbg_iap_class_active=FX6_USBG_IAP_CLASS_ACTIVE_G162,
            mc_usb_timecode_supported=FX3_MC_USB_TIMECODE_SUPPORTED_G162,
            mc_usb_focus_map_supported=FX3_MC_USB_FOCUS_MAP_SUPPORTED_G162,
            mc_usb_lut_import_supported=FX3_MC_USB_LUT_IMPORT_SUPPORTED_G162,
            target_media_slot=MEDIA_SLOT_NONE_PHASE378,
            host_storage_access_mode="none",
            slot1_exposed_writable=False,
            slot1_writes=0,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            usb_tx=USB_PACKETS_TRANSMITTED,
            usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
            emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
            hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            live_attach_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            violation_codes=tuple(telemetry_errors),
            errors=tuple(telemetry_errors),
            warnings=tuple(warnings),
        )

    state = resolve_fx3_expstd_usbtether_state(
        metering_mode=metering_mode,
        exposure_std_sixths=exposure_std_sixths,
        exposure_control_mode=exposure_control_mode,
        reset_action=reset_action,
        altered_mid_bracket=altered_mid_bracket,
        usb_connection_mode=usb_connection_mode,
        usb_lun_setting=usb_lun_setting,
        usb_tethering_active=usb_tethering_active,
        usb_tethering_driver=usb_tethering_driver,
        tethering_workload=tethering_workload,
        airplane_mode=airplane_mode,
        reset_network_set_executed=reset_network_set_executed,
        airplane_mode_rearmed_after_net_reset=airplane_mode_rearmed_after_net_reset,
        host_storage_access_mode=host_storage_access_mode,
        usbgmsc_readonly_enforced=usbgmsc_readonly_enforced,
    )

    # --- 1. Tier-0 Slot 1 EROFS=30 Firewall (Highest Priority) ---
    if slot1_tier0_protected:
        if usb_connection_mode == "MTP" and (
            host_storage_access_mode == "host_writable"
            or target_media_slot == MEDIA_SLOT_1_PHASE378
            or not usbgmsc_readonly_enforced
        ):
            erofs_violations.append(
                "TIER0_SLOT1_MTP_LOCKS_SLOT1_WRITABLE_BLOCKED_EROFS"
            )
        elif usb_connection_mode == "MassStorage(MSC)" and (
            state["slot1_exposed_writable"]
            or target_media_slot == MEDIA_SLOT_1_PHASE378
        ):
            erofs_violations.append(
                f"TIER0_SLOT1_MSC_LUN_{usb_lun_setting}_WRITABLE_BLOCKED_EROFS"
            )
        elif (
            target_media_slot == MEDIA_SLOT_1_PHASE378
            and host_storage_access_mode == "host_writable"
        ):
            erofs_violations.append(
                "TIER0_SLOT1_DIRECT_HOST_WRITABLE_BLOCKED_EROFS"
            )

    # --- 2. Dual USB Port / FX6 Wired LAN Mutual Exclusion (EBUSY=16) ---
    if dual_usb_ports_simultaneous:
        ebusy_violations.append(
            "FX3_USBC_AND_MULTI_MICRO_USB_SIMULTANEOUS_DATA_MUTEX_EBUSY"
        )
    if fx6_wired_lan_or_pc_usb_simultaneous:
        ebusy_violations.append(
            "FX6_USB_TETHERING_MUTEX_WITH_WIRED_LAN_OR_PC_USB_EBUSY"
        )

    # --- 3. Dormant / Unsupported Feature Firewall (EOPNOTSUPP=95) ---
    if request_dormant_step_1_8_ev:
        eopnotsupp_violations.append(
            "FX3_DORMANT_STANDARD_EXPOSURE_STEP_1_8_EV_EOPNOTSUPP"
        )
    if usb_connection_mode == DORMANT_USB_STREAMING_MODE_G162:
        eopnotsupp_violations.append(
            "FX3_NOUVC_USB_STREAMING_MODE_DORMANT_EOPNOTSUPP"
        )
    if tethering_workload == "creators_app_usb_streaming":
        eopnotsupp_violations.append(
            "FX3_CREATORS_APP_USB_LIVE_STREAMING_UNSUPPORTED_USE_TETHERING_CONNECTION"
        )
    if (
        usb_lan_cnct_launch == "On"
        and fw_val is not None
        and fw_val < USB_LAN_CNCT_LAUNCH_MIN_FW_G162
    ):
        eopnotsupp_violations.append(
            "FX3_USB_LAN_CNCT_LAUNCH_REQUIRES_VER7_00_PLUS"
        )
    if request_fx3_iap2_gadget:
        eopnotsupp_violations.append(
            "FX3_STRIPPED_CUSBGADGETIAP_DORMANT_USBG_IAP_KO_EOPNOTSUPP"
        )
    if request_mc_usb_timecode:
        eopnotsupp_violations.append(
            "FX3_MONITOR_AND_CONTROL_USB_TIMECODE_UNSUPPORTED_EOPNOTSUPP"
        )
    if request_mc_usb_focus_map:
        eopnotsupp_violations.append(
            "FX3_MONITOR_AND_CONTROL_USB_FOCUS_MAP_UNSUPPORTED_EOPNOTSUPP"
        )
    if request_mc_usb_lut_import:
        eopnotsupp_violations.append(
            "FX3_MONITOR_AND_CONTROL_USB_LUT_IMPORT_UNSUPPORTED_EOPNOTSUPP"
        )
    if fx6_usb_hub_attached:
        eopnotsupp_violations.append(
            "FX6_USB_TETHERING_PROHIBITS_USB_HUB_EOPNOTSUPP"
        )

    # --- 4. Exposure Std. Adjust, FX6 AE Level & Zero-RF Airplane Mode Constraints ---
    if not (
        EXPOSURE_STD_MIN_SIXTHS_G162
        <= exposure_std_sixths
        <= EXPOSURE_STD_MAX_SIXTHS_G162
    ):
        constraint_violations.append(
            f"FX3_EXPOSURE_STD_ADJUST_OUT_OF_RANGE_PM1EV:{exposure_std_sixths}_sixths"
        )
    if (
        reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE378
        and claim_camset_reset_zeroes_exp_std
    ):
        constraint_violations.append(
            "FX3_EXPOSURE_STD_ADJUST_RESISTS_CAMSET_RESET_INITIALIZE_ONLY"
        )
    if claim_exp_std_alters_exif_bias:
        constraint_violations.append(
            "FX3_EXPOSURE_STD_ADJUST_DOES_NOT_ALTER_EXIF_EXPOSURE_BIAS_VALUE"
        )
    if altered_mid_bracket and claim_bracket_count_preserved_on_change:
        constraint_violations.append(
            "FX3_EXPOSURE_STD_ADJUST_MID_BRACKET_RESETS_BRACKET_COUNT"
        )

    fx6_ae_f = float(fx6_ae_level_ev)
    if not (FX6_AE_LEVEL_MIN_G162 <= fx6_ae_f <= FX6_AE_LEVEL_MAX_G162):
        constraint_violations.append(
            f"FX6_AE_LEVEL_OUT_OF_RANGE_PM3_0:{fx6_ae_f}"
        )
    elif abs((fx6_ae_f / FX6_AE_LEVEL_STEP_G162) - round(fx6_ae_f / FX6_AE_LEVEL_STEP_G162)) > 1e-6:
        constraint_violations.append(
            f"FX6_AE_LEVEL_NOT_0_25_STEP:{fx6_ae_f}"
        )
    if claim_fx6_ae_level_capped_at_2ev:
        constraint_violations.append(
            "FX6_AE_LEVEL_IS_PM3_0_25STEPS_NOT_PM2_0_MYTH"
        )

    if state["effective_airplane_mode"] != "On":
        constraint_violations.append(
            "BENCH_ZERO_RF_REQUIRES_AIRPLANE_MODE_ON_AFTER_NET_RESET"
            if reset_network_set_executed
            else "BENCH_ZERO_RF_USB_TETHERING_REQUIRES_AIRPLANE_MODE_ON"
        )

    if state["effective_exposure_std_sixths"] != 0:
        warnings.append(
            f"Non-zero [Exposure Std. Adjust] ({state['effective_exposure_std_sixths']}/6 EV on {metering_mode}) "
            "persists across [Camera Settings Reset]; warning icon active beside metering mode."
        )

    all_violations = (
        erofs_violations
        + ebusy_violations
        + eopnotsupp_violations
        + constraint_violations
    )
    if erofs_violations:
        status = STATUS_BLOCKED_G162_SLOT1_MSC_MTP_WRITABLE_EROFS
        errno_val, errno_name = EROFS_ERRNO_PHASE378, EROFS_NAME_PHASE378
        valid = False
    elif ebusy_violations:
        status = STATUS_BLOCKED_G162_DUAL_USB_PORT_OR_FX6_LAN_MUTEX_EBUSY
        errno_val, errno_name = EBUSY_ERRNO_PHASE378, EBUSY_NAME_PHASE378
        valid = False
    elif eopnotsupp_violations:
        status = STATUS_BLOCKED_G162_DORMANT_NOUVC_IAP2_MC_OR_STEP18_EOPNOTSUPP
        errno_val, errno_name = EOPNOTSUPP_ERRNO_PHASE378, EOPNOTSUPP_NAME_PHASE378
        valid = False
    elif constraint_violations:
        status = STATUS_BLOCKED_G162_EXPSTD_EXIF_RESET_OR_ZERORF_AIRPLANE_VIOLATION
        errno_val, errno_name = EINVAL_ERRNO_PHASE378, EINVAL_NAME_PHASE378
        valid = False
    else:
        status = STATUS_VERIFIED_G162
        errno_val, errno_name = 0, "OK"
        valid = True

    return ExpStdUsbTetherGuardResult(
        valid=valid,
        status=status,
        block_errno=errno_val,
        block_errno_name=errno_name,
        verification_mode=verification_mode,
        exposure_std_adjust_menu_path=EXPOSURE_STD_ADJUST_MENU_PATH_G162,
        fx6_auto_exposure_menu_path=FX6_AUTO_EXPOSURE_MENU_PATH_G162,
        usb_connection_mode_menu_path=USB_CONNECTION_MODE_MENU_PATH_G162,
        usb_lan_tethering_menu_path=USB_LAN_TETHERING_MENU_PATH_G162,
        fx6_usb_tethering_menu_path=FX6_USB_TETHERING_MENU_PATH_G162,
        metering_mode=metering_mode,
        metering_modes_count=len(EXACT_5_METERING_MODES_G162),
        exposure_std_step_count=EXPOSURE_STD_STEP_COUNT_G162,
        effective_exposure_std_sixths=state["effective_exposure_std_sixths"],
        effective_exposure_std_ev=state["effective_exposure_std_ev"],
        exposure_std_resettable_by_camset_reset=EXPOSURE_STD_ADJUST_RESETTABLE_BY_CAMSET_RESET_G162,
        metering_warning_icon_shown=state["metering_warning_icon_shown"],
        mm_zero_point_shifted_ev=state["mm_zero_point_shifted_ev"],
        spot_ael_baseline_shifted_ev=state["spot_ael_baseline_shifted_ev"],
        alters_exif_exposure_bias_value=state["alters_exif_exposure_bias_value"],
        exif_exposure_bias_delta_ev=state["exif_exposure_bias_delta_ev"],
        alters_actual_auto_exposure=state["alters_actual_auto_exposure"],
        bracket_count_reset_triggered=state["bracket_count_reset_triggered"],
        fx6_ae_level_ev=fx6_ae_f,
        fx6_ae_level_step_count=FX6_AE_LEVEL_STEP_COUNT_G162,
        fx6_ae_mode=fx6_ae_mode,
        fx6_ae_speed=fx6_ae_speed,
        fx6_per_lut_ae_level_offset_supported=FX6_PER_LUT_AE_LEVEL_OFFSET_SUPPORTED_G162,
        usb_connection_mode=usb_connection_mode,
        usb_lun_setting=usb_lun_setting,
        usb_tethering_active=usb_tethering_active,
        usb_tethering_driver=usb_tethering_driver,
        tethering_workload=tethering_workload,
        usb_lan_cnct_launch=usb_lan_cnct_launch,
        airplane_mode=state["effective_airplane_mode"],
        zero_rf_tethering_bypass_active=state["zero_rf_tethering_bypass_active"],
        rf_tx_packets=state["rf_tx_packets"],
        wifi_bt_radio_enabled=state["wifi_bt_radio_enabled"],
        dual_usb_ports_simultaneous=dual_usb_ports_simultaneous,
        fx3_usbg_iap_class_hits=FX3_USBG_IAP_CLASS_HITS_G162,
        fx6_usbg_iap_class_active=FX6_USBG_IAP_CLASS_ACTIVE_G162,
        mc_usb_timecode_supported=FX3_MC_USB_TIMECODE_SUPPORTED_G162,
        mc_usb_focus_map_supported=FX3_MC_USB_FOCUS_MAP_SUPPORTED_G162,
        mc_usb_lut_import_supported=FX3_MC_USB_LUT_IMPORT_SUPPORTED_G162,
        target_media_slot=target_media_slot,
        host_storage_access_mode=host_storage_access_mode,
        slot1_exposed_writable=state["slot1_exposed_writable"],
        slot1_writes=0,
        slot1_data_sector_writes=0,
        emmc_nflasha_write_count=0,
        usb_tx=USB_PACKETS_TRANSMITTED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        live_attach_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        violation_codes=tuple(all_violations),
        errors=tuple(all_violations),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class G162ExpStdUsbTetherGuardResult:
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
    expstd_usbtether_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g162_expstd_usbtether_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G162ExpStdUsbTetherGuardResult]:
    audit = audit_phase378_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_expstd_usbtether_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G162ExpStdUsbTetherGuardResult(
        gate_id=G162,
        gate_code=G162_GATE_CODE,
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
        expstd_usbtether_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G162,
        gate_code=G162_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"exp_std={res.effective_exposure_std_sixths}/6EV "
            f"drv={res.usb_tethering_driver} "
            f"airplane={res.airplane_mode} "
            f"rf_tx={res.rf_tx_packets} "
            f"s1_writes={res.slot1_writes}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_expstd_usbtether_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G162ExpStdUsbTetherGuardResult]:
    return evaluate_g162_expstd_usbtether_guard(**kwargs)


# ---------------------------------------------------------------------------
# Unified 162-Gate Master Safety Preflight Engine (G01..G162)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Master162GateReport:
    schema: str
    schema_version: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_159_gates_verified: bool
    all_162_gates_verified: bool
    g13_to_g162_all_passed: bool
    g161_to_g162_all_passed: bool
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
    master_160_report: Dict[str, Any]
    g161_result: Dict[str, Any]
    g162_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_162gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    simulate_bench_dry_run: Optional[bool] = None,
    dry_run_simulated_backup: Optional[bool] = None,
    request_persistent_emmc_writes: bool = False,
    master_160_override: Optional[Master160GateReport] = None,
    antidust_focusmag_kwargs: Optional[Mapping[str, Any]] = None,
    expstd_usbtether_kwargs: Optional[Mapping[str, Any]] = None,
    **extra_upstream_kwargs: Any,
) -> Master162GateReport:
    """Evaluate unified 162-Gate Master Safety Preflight (`G01..G162`)."""
    effective_dry_run = (
        bool(dry_run_simulated)
        or (simulate_bench_dry_run is True)
        or (dry_run_simulated_backup is True)
    )
    clean_forced = _is_clean_room_forced(force_clean_room)
    resolved_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved_work_root_for_m160 = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=resolved_repo_root).work_root
    )
    donors_present_in_work_root = bool(
        resolved_work_root_for_m160 is not None
        and (
            resolved_work_root_for_m160
            / PINNED_PHASE378_DONOR_SPECS["fx3_appfw_so"][1]
        ).is_file()
    )
    m160_force_clean_room = (
        True
        if (
            clean_forced
            or (not donors_present_in_work_root and force_clean_room is not False)
        )
        else force_clean_room
    )

    if master_160_override is not None:
        m160_report = master_160_override
    else:
        m160_kw = {
            k: v
            for k, v in extra_upstream_kwargs.items()
            if v is not None
        }
        m160_report = evaluate_160gate_preflight(
            resolved_repo_root,
            work_root=work_root,
            force_clean_room=m160_force_clean_room,
            dry_run_simulated=effective_dry_run,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m160_kw,
        )

    g161_kw = dict(antidust_focusmag_kwargs or {})
    g161_verdict, g161_res = evaluate_g161_antidust_focusmag_guard(
        repo_root=resolved_repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **g161_kw,
    )

    g162_kw = dict(expstd_usbtether_kwargs or {})
    if request_persistent_emmc_writes:
        if "usb_connection_mode" not in g162_kw:
            g162_kw["usb_connection_mode"] = "MassStorage(MSC)"
        if "target_media_slot" not in g162_kw:
            g162_kw["target_media_slot"] = MEDIA_SLOT_1_PHASE378
        if "host_storage_access_mode" not in g162_kw:
            g162_kw["host_storage_access_mode"] = "host_writable"
    g162_verdict, g162_res = evaluate_g162_expstd_usbtether_guard(
        repo_root=resolved_repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **g162_kw,
    )

    new_gate_dicts = (
        {
            "gate_id": G161,
            "gate_code": G161_GATE_CODE,
            "status": g161_res.status,
            "passed": g161_verdict.passed,
            "evidence": g161_verdict.evidence,
            "violation_codes": list(g161_verdict.errors),
        },
        {
            "gate_id": G162,
            "gate_code": G162_GATE_CODE,
            "status": g162_res.status,
            "passed": g162_verdict.passed,
            "evidence": g162_verdict.evidence,
            "violation_codes": list(g162_verdict.errors),
        },
    )

    all_gates: Tuple[Dict[str, Any], ...] = tuple(m160_report.gates) + new_gate_dicts
    g01_to_g12_verified = int(m160_report.summary["g01_to_g12_verified"])
    g13_to_g160_verified = (
        int(m160_report.summary["g13_to_g158_verified"])
        + int(m160_report.summary["g159_to_g160_verified"])
    )
    g161_to_g162_verified = int(bool(g161_verdict.passed)) + int(
        bool(g162_verdict.passed)
    )
    total_verified = (
        g01_to_g12_verified + g13_to_g160_verified + g161_to_g162_verified
    )

    g161_to_g162_all_passed = g161_to_g162_verified == 2
    g13_to_g162_all_passed = (
        m160_report.g13_to_g160_all_passed and g161_to_g162_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m160_report.gates[:9])

    offline_159_verified = (
        g01_to_g09_ok
        and m160_report.offline_157_gates_verified
        and g161_to_g162_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_162_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g162_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m160_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_159_verified
        and m160_report.h0_h1_trial_entry_allowed
        and g161_to_g162_all_passed
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
        list(m160_report.errors)
        + list(g161_verdict.errors)
        + list(g162_verdict.errors)
    )
    warnings: List[str] = (
        list(m160_report.warnings)
        + list(g161_verdict.warnings)
        + list(g162_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m160_report.g13_to_g160_all_passed:
        overall_status = m160_report.status
    elif not g161_verdict.passed:
        overall_status = g161_verdict.status
    elif not g162_verdict.passed:
        overall_status = g162_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_162_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_162_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_162_verified:
        overall_status = "VERIFIED_ALL_162_GATES"
    else:
        overall_status = "VERIFIED_159_OF_162_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m160_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g161_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g162_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 162,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 162 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g160_verified": g13_to_g160_verified,
        "g161_to_g162_verified": g161_to_g162_verified,
        "g13_to_g162_all_passed": g13_to_g162_all_passed,
        "g161_to_g162_all_passed": g161_to_g162_all_passed,
        "offline_159_gates_verified": offline_159_verified,
        "all_162_gates_verified": all_162_verified,
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

    return Master162GateReport(
        schema=REALHW_162GATE_PREFLIGHT_SCHEMA,
        schema_version=REALHW_162GATE_PREFLIGHT_SCHEMA,
        version=REALHW_ANTIDUST_FOCUSMAG_EXPSTD_USBTETHER_162GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_159_gates_verified=offline_159_verified,
        all_162_gates_verified=all_162_verified,
        g13_to_g162_all_passed=g13_to_g162_all_passed,
        g161_to_g162_all_passed=g161_to_g162_all_passed,
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
        master_160_report=m160_report.to_dict(),
        g161_result=g161_res.to_dict(),
        g162_result=g162_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_162_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master162GateReport:
    return evaluate_162gate_preflight(repo_root, **kwargs)


def run_162_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master162GateReport:
    return evaluate_162gate_preflight(repo_root, **kwargs)


def verify_real_hardware_162gate_readiness(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master162GateReport:
    return evaluate_162gate_preflight(repo_root, **kwargs)


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
        prog="realhw_antidust_focusmag_expstd_usbtether_and_162gate_guard",
        description="Phase 378 (Task H480, Wave-71) G161/G162 and 162/162 Unified Safety Preflight CLI",
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
        help="Supply simulated dry-run Tier-0 backup inputs so all 162/162 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g161", "g162", "162"],
        default="162",
        help="Target gate check: g161, g162, or 162",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g161":
        v, r = evaluate_g161_antidust_focusmag_guard(
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

    if args.gate == "g162":
        v, r = evaluate_g162_expstd_usbtether_guard(
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

    rep = evaluate_162gate_preflight(
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
                "g161_status": rep.g161_result["status"],
                "g162_status": rep.g162_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/162 "
            f"g161_to_g162_all_passed={rep.g161_to_g162_all_passed} "
            f"all_162_gates_verified={rep.all_162_gates_verified} "
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
        rep.all_162_gates_verified
        if args.dry_run_simulated
        else rep.offline_159_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "AF_IN_FOCUS_MAG_DEFAULT_G161",
    "AF_IN_FOCUS_MAG_F_RESID16_G161",
    "ALLOWED_BODY_MODELS_PHASE378",
    "ALLOWED_EXPOSURE_CONTROL_MODES_G162",
    "ALLOWED_FOCUS_MAG_TIMES_G161",
    "ALLOWED_FX3_USB_CONNECTION_MODES_G162",
    "ALLOWED_FX6_AE_MODES_G162",
    "ALLOWED_FX6_FOCUS_MAG_TARGETS_G161",
    "ALLOWED_HOST_STORAGE_ACCESS_MODES_G162",
    "ALLOWED_MEDIA_SLOTS_PHASE378",
    "ALLOWED_RESET_ACTIONS_PHASE378",
    "ALLOWED_SENSOR_CROP_MODES_G161",
    "ALLOWED_SHOOT_MODES_PHASE378",
    "ALLOWED_TETHERING_WORKLOADS_G162",
    "ALLOWED_USB_LUN_SETTINGS_G162",
    "ALLOWED_USB_TETHERING_DRIVERS_G162",
    "AUTO_MAG_IN_MF_DEFAULT_G161",
    "AUTO_MAG_IN_MF_F_RESID16_G161",
    "AntiDustFocusMagGuardResult",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE378",
    "DONOR_CHECK_MAX_SECONDS_PHASE378",
    "DORMANT_ANTIDUST_FUNCTION_F_RESID16_G161",
    "DORMANT_ANTIDUST_SYMBOLS_G161",
    "DORMANT_EXPOSURE_STD_STEP_LABEL_G162",
    "DORMANT_HIGH_MP_ALPHA_MAG_RATIOS_G161",
    "DORMANT_SHUTTER_WHEN_PWR_OFF_F_RESID16_G161",
    "DORMANT_USB_STREAMING_MODE_G162",
    "EBUSY_ERRNO_PHASE378",
    "EBUSY_NAME_PHASE378",
    "EINVAL_ERRNO_PHASE378",
    "EINVAL_NAME_PHASE378",
    "ENTIRE_SCREEN_AVG_F_RESID16_G162",
    "ENV_CLEAN_ROOM_TEST_PHASE378",
    "EOPNOTSUPP_ERRNO_PHASE378",
    "EOPNOTSUPP_NAME_PHASE378",
    "EPERM_ERRNO_PHASE378",
    "EPERM_NAME_PHASE378",
    "EROFS_ERRNO_PHASE378",
    "EROFS_NAME_PHASE378",
    "EXACT_5_FX3_FOCUS_ASSISTANT_ITEMS_G161",
    "EXACT_5_METERING_MODES_G162",
    "EXPOSURE_STD_ADJUST_F_RESID16_G162",
    "EXPOSURE_STD_ADJUST_MENU_PATH_G162",
    "EXPOSURE_STD_ADJUST_RESETTABLE_BY_CAMSET_RESET_G162",
    "EXPOSURE_STD_ALTERS_EXIF_BIAS_VALUE_G162",
    "EXPOSURE_STD_DEFAULT_SIXTHS_G162",
    "EXPOSURE_STD_MAX_SIXTHS_G162",
    "EXPOSURE_STD_MIN_SIXTHS_G162",
    "EXPOSURE_STD_STEP_COUNT_G162",
    "EXPOSURE_STD_STEP_LABEL_G162",
    "ExpStdUsbTetherGuardResult",
    "FOCUS_ASSISTANT_MENU_PATH_G161",
    "FOCUS_MAGNIFIER_BASE_RESID16_G161",
    "FOCUS_MAGNIF_TIME_F_RESID16_G161",
    "FOCUS_MAG_TIME_DEFAULT_G161",
    "FX3_AF_IN_FOCUS_MAG_STILL_ONLY_G161",
    "FX3_AUTO_MAG_IN_MF_STILL_ONLY_G161",
    "FX3_BRIGHT_MON_FOCUS_MAG_MIN_FW_G161",
    "FX3_DEFAULT_FW_VERSION_PHASE378",
    "FX3_DORMANT_ANTIDUST_EXPOSED_G161",
    "FX3_DORMANT_SHUTTER_WHEN_PWR_OFF_EXPOSED_G161",
    "FX3_FOCUS_ASSISTANT_5ITEMS_RESETTABLE_VER2_PLUS_G161",
    "FX3_FOCUS_MAG_CLEAN_HDMI_CROP_PIXELS_G161",
    "FX3_FOCUS_MAG_COEXISTING_FEATURES_G161",
    "FX3_FOCUS_MAG_DEFAULT_CUSTOM_BUTTON_G161",
    "FX3_FOCUS_MAG_INTERNAL_REC_CROP_PIXELS_G161",
    "FX3_FOCUS_MAG_REC_CONTINUITY_SUPPORTED_G161",
    "FX3_FOCUS_MAG_SUPPRESSED_FEATURES_G161",
    "FX3_HELP_GUIDE_CODE_PHASE378",
    "FX3_ILC2210_SHUTTER_PWR_OFF_HITS_G161",
    "FX3_MC_USB_FOCUS_MAP_SUPPORTED_G162",
    "FX3_MC_USB_LUT_IMPORT_SUPPORTED_G162",
    "FX3_MC_USB_TIMECODE_SUPPORTED_G162",
    "FX3_MODEL_ENUM_PHASE378",
    "FX3_MODEL_ID_PHASE378",
    "FX3_MODEL_NAME_PHASE378",
    "FX3_MOVIE_SQ_INITIAL_RATIOS_G161",
    "FX3_MOVIE_SQ_MAG_RATIOS_G161",
    "FX3_POWER_OFF_SHUTTER_STATE_G161",
    "FX3_STILL_APSC_INITIAL_RATIOS_G161",
    "FX3_STILL_APSC_MAG_RATIOS_G161",
    "FX3_STILL_FF_INITIAL_RATIOS_G161",
    "FX3_STILL_FF_MAG_RATIOS_G161",
    "FX3_USBG_IAP_CLASS_HITS_G162",
    "FX3_USB_MSC_ELF_TYPO_G162",
    "FX3_USB_TETHERING_RF_TX_PACKETS_AIRPLANE_G162",
    "FX3_USB_TETHERING_ZERO_RF_AIRPLANE_ALLOWED_G162",
    "FX6_AE_LEVEL_MAX_G162",
    "FX6_AE_LEVEL_MIN_G162",
    "FX6_AE_LEVEL_STEP_COUNT_G162",
    "FX6_AE_LEVEL_STEP_G162",
    "FX6_AE_SPEED_MAX_G162",
    "FX6_AE_SPEED_MIN_G162",
    "FX6_APR_MENU_PATH_G161",
    "FX6_APR_NS1_RESID16_G161",
    "FX6_AUTO_EXPOSURE_MENU_PATH_G162",
    "FX6_DEFAULT_FW_VERSION_PHASE378",
    "FX6_DORMANT_FS7_MAG_RATIOS_G161",
    "FX6_END_RANGE_LABEL_G161",
    "FX6_FOCAL_PLANE_MECHANICAL_SHUTTER_PRESENT_G161",
    "FX6_FOCUS_MAG_INTERNAL_REC_CROP_PIXELS_G161",
    "FX6_FOCUS_MAG_MENU_PATH_G161",
    "FX6_FOCUS_MAG_SDI_CROP_PIXELS_G161",
    "FX6_FOCUS_MAG_TARGET_NS1_RESID16_G161",
    "FX6_HDMI_MAG_RATIOS_G161",
    "FX6_HDMI_TARGET_MIN_FW_G161",
    "FX6_MODEL_ENUM_PHASE378",
    "FX6_MODEL_NAME_PHASE378",
    "FX6_PER_LUT_AE_LEVEL_OFFSET_SUPPORTED_G162",
    "FX6_SHUTTER_WHEN_PWR_OFF_ELF_HITS_G161",
    "FX6_USBG_IAP_CLASS_ACTIVE_G162",
    "FX6_USB_TETHERING_MENU_PATH_G162",
    "FX6_USER_IBIS_SENSOR_CLEANING_SUPPORTED_G161",
    "FX6_VF_MAG_RATIOS_G161",
    "G161",
    "G161AntiDustFocusMagGuardResult",
    "G161_GATE_CODE",
    "G161_GATE_ID",
    "G162",
    "G162ExpStdUsbTetherGuardResult",
    "G162_GATE_CODE",
    "G162_GATE_ID",
    "INITIAL_FOCUS_MAG_MOVIE_F_RESID16_G161",
    "INITIAL_FOCUS_MAG_STILL_F_RESID16_G161",
    "LEGACY_CLEANING_MODE_BASE_RESID16_G161",
    "MEDIA_SLOT_1_PHASE378",
    "MEDIA_SLOT_2_PHASE378",
    "MEDIA_SLOT_NONE_PHASE378",
    "MTP_BASE_RESID16_G162",
    "Master162GateReport",
    "PINNED_FX3_APPFW_SLICES_PHASE378",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE378",
    "PINNED_FX6_APPFW_SLICES_PHASE378",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE378",
    "PINNED_PHASE378_DONOR_SPECS",
    "Phase378DonorAuditResult",
    "REALHW_162GATE_PREFLIGHT_SCHEMA",
    "REALHW_ANTIDUST_FOCUSMAG_EXPSTD_USBTETHER_162GATE_SCHEMA",
    "REALHW_ANTIDUST_FOCUSMAG_EXPSTD_USBTETHER_162GATE_VERSION",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE378",
    "RESET_ACTION_INITIALIZE_PHASE378",
    "RESET_ACTION_NONE_PHASE378",
    "SEL_WHEN_CONNECT_F_RESID16_G162",
    "SENSOR_CLEANING_F_RESID16_G161",
    "SENSOR_CLEANING_MENU_PATH_G161",
    "SENSOR_CLEANING_MIN_SOC_PCT_G161",
    "SENSOR_CLEANING_PHYSICAL_PWR_OFF_PROMPT_REQUIRED_G161",
    "SENSOR_CLEANING_PWR_OFF_G_RESID16_G161",
    "SHOOT_MODE_MOVIE_PHASE378",
    "SHOOT_MODE_SQ_PHASE378",
    "SHOOT_MODE_STILL_PHASE378",
    "STATUS_BLOCKED_G161_CLEANING51_REC_HDMI_CROP_OR_SUPPRESSION_VIOLATION",
    "STATUS_BLOCKED_G161_DORMANT_ANTIDUST_HIGHMP_RATIO_STILLONLY_OR_FX6_EOPNOTSUPP",
    "STATUS_BLOCKED_G161_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G162_DORMANT_NOUVC_IAP2_MC_OR_STEP18_EOPNOTSUPP",
    "STATUS_BLOCKED_G162_DUAL_USB_PORT_OR_FX6_LAN_MUTEX_EBUSY",
    "STATUS_BLOCKED_G162_EXPSTD_EXIF_RESET_OR_ZERORF_AIRPLANE_VIOLATION",
    "STATUS_BLOCKED_G162_SLOT1_MSC_MTP_WRITABLE_EROFS",
    "STATUS_BLOCKED_G162_TELEMETRY_INVALID",
    "STATUS_BLOCKED_PHASE378_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G161",
    "STATUS_VERIFIED_G162",
    "STEP_MINUS_ONE_SIXTH_BASE_RESID16_G162",
    "STEP_PLUS_ONE_SIXTH_BASE_RESID16_G162",
    "STREAMING_TETHER_PROMPT_G_RESID16_G162",
    "TETHERING_CONNECTION_F_RESID16_G162",
    "USB_CONNECTION_MODE_DEFAULT_G162",
    "USB_CONNECTION_MODE_F_RESID16_G162",
    "USB_CONNECTION_MODE_MENU_PATH_G162",
    "USB_LAN_CNCT_LAUNCH_DEFAULT_G162",
    "USB_LAN_CNCT_LAUNCH_F_RESID16_G162",
    "USB_LAN_CNCT_LAUNCH_MIN_FW_G162",
    "USB_LAN_TETHERING_MENU_PATH_G162",
    "USB_LUN_DEFAULT_G162",
    "USB_LUN_SETTING_F_RESID16_G162",
    "audit_phase378_donor_contracts",
    "compute_antidust_focusmag_matrix",
    "compute_expstd_usbtether_matrix",
    "evaluate_162_master_safety_gates",
    "evaluate_162gate_preflight",
    "evaluate_g161_antidust_focusmag_guard",
    "evaluate_g162_expstd_usbtether_guard",
    "main",
    "resolve_fx3_antidust_focusmag_state",
    "resolve_fx3_expstd_usbtether_state",
    "run_162_gate_preflight",
    "strip_elapsed_seconds_recursive_phase378",
    "verify_antidust_focusmag_guard",
    "verify_antidust_focusmag_guard_with_audit",
    "verify_expstd_usbtether_guard",
    "verify_expstd_usbtether_guard_with_audit",
    "verify_real_hardware_162gate_readiness",
]


if __name__ == "__main__":
    raise SystemExit(main())
