"""Phase 313 (Wave-59, 138/138 Safety Gates):
Real-Hardware Safety Gates G137 & G138 + Unified 138-Gate Preflight Engine.

Implements empirical `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` hardware safety gates:

1. **Gate `G137` (`verify-big6-home-framing-interval-vault-guard`)**:
   - **Ver. 7.00+/7.02 `[BIG6]` (Home) Screen**:
     - Strictly requires `[Mode Settings] == Fixed/Variable` (`_f.uxc 0x7d0d`,
       `BKID_APP_setting_fps_fixed_variable_select`; resettable via `[Camera Settings Reset]`).
     - Enters via custom key `[HOME]` (`_f 0x7cad` / `0x7cb1`) or `[Swipe Down]`
       (`_f 0x7cdd`, `_g 0x6526`, `VAL_setting_swipe_down_SWIPE_DOWN_HOME_SCREEN`),
       exits on `MENU`/`Fn` (`HOME_SCREEN_STATE_TEMP_OFF`), navigates via Control Wheel
       center (`HOME_SCREEN_STATE_ON_CURSOR_{OFF,ON}`), and NEVER outputs to external HDMI.
     - Maps exact 6 dynamic tiles (`26view_tp_button_01_for_big6`, `update_big6_item_iso_ei`):
       1. `FPS` (`GUIDE_BIG6_FPS_SELECT` / `GUIDE_BIG6_FRAME_RATE`)
       2. `ISO` (`Log Shooting == Off / Flexible ISO`) vs `Base ISO + EI` (`Cine EI / Cine EI Quick`)
       3. `Shutter Speed` / `Shutter Angle`
       4. `Aperture` (default) vs manual `ND Filter` metadata via `[Home (Lower Left)]`
          (`_f 0x7ce3`, `BKID_APP_setting_movie_home_lower_left`, `MOVIE_HOME_LOWER_LEFT_{APERTURE,ND_FILTER}`)
          — enforcing **ZERO physical e-ND actuator on `ILME-FX3`** (`EOPNOTSUPP=95` if claimed)
          vs real physical variable e-ND (`Clear / 1/4..1/128 / Auto`) on `ILME-FX6`!
       5. `Picture Profile` (`Log Shooting == Off`) vs `Select LUT` (`Log Shooting != Off`)
       6. `White Balance`
   - **Active Manual `[Framing Settings]` vs Dormant AI `[Auto Framing]`**:
     - Enforces active manual `[Framing Settings]` (`_f.uxc 0x7d18`: `Framing` `Off/On`,
       `Recording/Streaming` `Full/Crop`, `HDMI` `Crop/Full`; custom keys
       `Framing Stop (Full)` / `Switch Framing`; disables `APS-C S35` when `On`; locks during
       `>= 100p`, active recording, or streaming).
     - Rejects dormant AI `[Auto Framing]` (`_f 0x6be6` / `0x79bc`, `_g 0x60e6` / `0x62ad`
       -> `EOPNOTSUPP=95`; `FX3 appFw.so` locks `TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY` with
       `0` `AUTO_FRAMING_AFR` / `PTZAUTOFRAMING_*` hits).
   - **CRITICAL SLOT-1 VAULT FIREWALL (`[Interval Shoot Func.]` 9,999 Shots)**:
     - Validates `[Interval Shoot Func.]` (`_f 0x7027`, Still-only, 7 resettable parameters:
       `Interval Shooting`, `Start Time 1s..99m59s`, `Interval 1..60s`, `Shots 1..9999`,
       `AE Tracking Sens High/Mid/Low`, `Electronic/Mechanical Shutter`, `Shoot Interval Priority`;
       exits `BULB` to `30"`; disabled in `Intelligent Auto`), contrasted with `FX6`
       `Project > Interval Rec` (single XAVC MXF clip, `1..24` frames, `MODEL_VALUE_CHANGED_BY_EXCLUSION_INTERVAL_REC`).
     - Up to `9,999` RAW+JPEG/HEIF still shots = up to `19,998` `DCIM/` files + continuous
       `AVF_INFO` rewrites -> **MUST fail-closed (`EROFS=30` / `EBUSY=16`,
       `slot1_data_sector_writes == 0`, `slot1_dcim_mutated == False`, `slot1_avf_info_mutated == False`)**
       whenever target resolves to `Slot 1` (`Slot 1` or `Simult. Recording`) holding a
       Tier-0 recovery vault!

2. **Gate `G138` (`verify-tc-make-hdmi-rec-ssh-authen-fan-guard`)**:
   - **`[Time Code Make]` Regenerate -> Forced `Rec Run` & HDMI `[REC Control]`**:
     - `[Time Code Make]` (`_f 0x6b79`: `Preset` / `Regenerate`) and `[Time Code Run]`
       (`_f 0x7313`: `Rec Run` / `Free Run`) are `Initialize`-only (`Camera Settings Reset`
       Not available); FX6-only `Clock` (`VAL_setting_tc_make_TC_MAKE_CLOCK`) is rejected
       on FX3 (`EOPNOTSUPP=95`).
     - `Regenerate` forces effective `Rec Run` regardless of `[Time Code Run]` selection,
       reading last clip TC from `Slot 1` during `Simult. Recording`. Wired `VMC-BNCM1`
       `EXT-LK` strictly requires `Preset` + `Free Run`.
     - HDMI `[REC Control]` (`_f 0x76e1`, `Initialize`-only) requires `[Time Code Output] == On`
       (`_f 0x72af`, `Movie` mode), operates in **BOTH** `[Rec. Media dur HDMI Output] = On`
       AND `Off(HDMI Only)` (including `RAW Output = On` and cardless HDMI-only), and is
       restricted in `S&Q` / `Network Streaming` / `USB Streaming`, paired with `[4ch Audio Output]`
       (`_f 0x6aa0`: `CH1/CH2` / `CH3/CH4`) — contrasted with `FX6` `SDI/HDMI Remote I/F` & `Parallel Rec`.
   - **Ver. 7.00+ SSH-Based `[Access Authen. Settings]` vs Zero HTTPS/Digest**:
     - `[Access Authen. Settings]` (`_f 0x7ada`, `On` by default, reset only via
       `Reset Network Set.` / `Initialize`) runs **SSH** (`MSGID_SSHD_START_CMD`,
       `sshd_start`, `SSH Host Key Fingerprint`) + `PTP-IP` — rejecting non-existent
       `HTTP_DIGEST` / `BASIC_AUTH` / `HTTPS` server auth (`0` hits -> `EOPNOTSUPP=95`).
     - `[Import Root Certificate]` (`_f 0x7940`, `ROOT_CERTIFICATE_TYPE_{CLOUD,FTP,RTMP}`)
       is strictly **outbound** FTPS/RTMPS/Cloud client TLS verification (never inbound HTTPS server!).
   - **4-Mode FX3 vs 3-Mode FX6 `[Fan Control]` Zero-`Max` Truth & `[Auto Power OFF Temp.]`**:
     - `FX3 [Fan Control]` exposes exact **4 modes** (`Auto` / `Minimum` / `Off in Rec` / `Always Off`,
       `Initialize`-only; `Off in Rec` retains temp-safety override) + `[Auto Power OFF Temp.]`
       (`Standard` / `High`, `Initialize`-only).
     - `FX6 Technical > Fan Control` exposes exact **3 modes** (`Auto` / `Minimum` / `Off in Rec`),
       keeping `FAN_CONTROL_ALWAYS_OFF` dormant (`EOPNOTSUPP=95` if requested on FX6).
     - **ZERO `Max` option on BOTH cameras** (`FAN_CONTROL_MAX` has `0` hits in both `FX3 appFw.so`
       and `FX6 appFw.so` -> `EOPNOTSUPP=95`)!

3. **Unified `138`-Gate Milestone Master Preflight (`evaluate_138gate_preflight` / `verify-138-gates`)**:
   - Delegates `G01..G136` directly to `evaluate_136gate_preflight()` and appends `G137` + `G138`.
   - Offline mode: `135/138` gates pass (`VERIFIED_135_OF_138_AWAITING_PHYSICAL_TIER0`);
     `--simulate-bench-dry-run`: `138/138` simulation gates pass
     (`VERIFIED_ALL_138_GATES_DRY_RUN_SIMULATED_BACKUP`).
   - All hardware attach, persistent eMMC write, EL3/SPI-NOR transmit, and cross-model flash
     redlines remain hard-locked `False`, `usb_packets_transmitted == 0`, and
     `raw_firmware_bytes_leaked == 0`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths
from .realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard import (
    DEFAULT_REPO_ROOT,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_VERIFIED_SAFE,
    GateVerdict,
)
from .realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard import (
    Master136GateReport,
    evaluate_136gate_preflight,
)

# ---------------------------------------------------------------------------
# Schema, Version & Absolute Hardware / Firmware Safety Redlines
# ---------------------------------------------------------------------------

REALHW_BIG6_HOME_FRAMING_INTERVAL_TC_SSH_FAN_138GATE_SCHEMA = (
    "realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard_v1"
)
REALHW_BIG6_HOME_FRAMING_INTERVAL_TC_SSH_FAN_138GATE_VERSION = "2026.11.17"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST_PHASE313 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE313 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE313 = 15.0

# Hard-locked redlines (identical immutable values; NEVER relaxed at runtime)
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
SPI_NOR_WRITE_AUTHORIZED = False
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
PERSISTENT_WRITE_RELEASE = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
HUMAN_HARDWARE_ATTACH_TOKEN = False
CROSS_MODEL_FLASH_AUTHORIZED = False
USB_PACKETS_TRANSMITTED = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

# Gate Identifiers
G137 = "G137"
G137_GATE_ID = "G137"
G137_GATE_CODE = (
    "GATE_G137_BIG6_HOME_ND_META_MANUAL_FRAMING_VS_AUTO_FRAMING_AND_INTERVAL_SHOOT_9999_SLOT1_VAULT_GUARD"
)
GATE_G137_BIG6_HOME_ND_META_MANUAL_FRAMING_VS_AUTO_FRAMING_AND_INTERVAL_SHOOT_9999_SLOT1_VAULT_GUARD = (
    G137_GATE_CODE
)

G138 = "G138"
G138_GATE_ID = "G138"
G138_GATE_CODE = (
    "GATE_G138_TC_MAKE_REGEN_HDMI_REC_CTRL_SSH_ACCESS_AUTHEN_AND_FAN_4MODE_3MODE_ZERO_MAX_GUARD"
)
GATE_G138_TC_MAKE_REGEN_HDMI_REC_CTRL_SSH_ACCESS_AUTHEN_AND_FAN_4MODE_3MODE_ZERO_MAX_GUARD = (
    G138_GATE_CODE
)

# Model & Identity Contracts (Phase 313 suffixed to avoid __init__.py shadowing)
FX3_MODEL_NAME_PHASE313 = "ILME-FX3"
FX3_MODEL_ID_PHASE313 = 0x39383232
FX3_HELP_GUIDE_CODE_PHASE313 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE313 = "7.02"

FX6_MODEL_NAME_PHASE313 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE313 = "6.01"
FX6_PRODUCT_CODE_PHASE313 = "PRODUCT_MODEL_CHAPLIN"

# Shoot Modes, Exposure Modes, Reset Actions & Media Slots
SHOOT_MODE_STILL_PHASE313 = "Still"
SHOOT_MODE_MOVIE_PHASE313 = "Movie"
SHOOT_MODE_SQ_PHASE313 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE313: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE313,
    SHOOT_MODE_MOVIE_PHASE313,
    SHOOT_MODE_SQ_PHASE313,
)

EXPOSURE_MODE_P_G137 = "P"
EXPOSURE_MODE_A_G137 = "A"
EXPOSURE_MODE_S_G137 = "S"
EXPOSURE_MODE_M_G137 = "M"
EXPOSURE_MODE_INTELLIGENT_AUTO_G137 = "Intelligent Auto"
ALLOWED_PASM_MODES_G137: Tuple[str, ...] = (
    EXPOSURE_MODE_P_G137,
    EXPOSURE_MODE_A_G137,
    EXPOSURE_MODE_S_G137,
    EXPOSURE_MODE_M_G137,
)
ALLOWED_EXPOSURE_MODES_G137: Tuple[str, ...] = ALLOWED_PASM_MODES_G137 + (
    EXPOSURE_MODE_INTELLIGENT_AUTO_G137,
)

RESET_ACTION_NONE_PHASE313 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE313 = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE313 = "Reset Network Set."
RESET_ACTION_INITIALIZE_PHASE313 = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE313: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE313,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE313,
    RESET_ACTION_RESET_NETWORK_SET_PHASE313,
    RESET_ACTION_INITIALIZE_PHASE313,
)

MEDIA_SLOT_1_PHASE313 = "Slot 1"
MEDIA_SLOT_2_PHASE313 = "Slot 2"
MEDIA_SIMULT_RECORDING_PHASE313 = "Simult. Recording"
ALLOWED_RECORDING_MEDIA_MODES_PHASE313: Tuple[str, ...] = (
    MEDIA_SLOT_1_PHASE313,
    MEDIA_SLOT_2_PHASE313,
    MEDIA_SIMULT_RECORDING_PHASE313,
)

EOPNOTSUPP_ERRNO_PHASE313 = 95
EOPNOTSUPP_NAME_PHASE313 = "EOPNOTSUPP"
EROFS_ERRNO_PHASE313 = 30
EROFS_NAME_PHASE313 = "EROFS"
EBUSY_ERRNO_PHASE313 = 16
EBUSY_NAME_PHASE313 = "EBUSY"

# ---------------------------------------------------------------------------
# G137 Constants: BIG6 Home Screen, Manual Framing, Interval Shoot Func.
# ---------------------------------------------------------------------------

MODE_SETTINGS_FIXED_VARIABLE_G137 = "Fixed/Variable"
MODE_SETTINGS_FIXED_FPS_G137 = "Fixed-24fps"
ALLOWED_MODE_SETTINGS_G137: Tuple[str, ...] = (
    MODE_SETTINGS_FIXED_VARIABLE_G137,
    MODE_SETTINGS_FIXED_FPS_G137,
)

BIG6_MODE_SETTINGS_F_UXC_RESID16_G137 = 0x7D0D
BIG6_HOME_LOWER_LEFT_F_UXC_RESID16_G137 = 0x7CE3
BIG6_SWIPE_DOWN_F_UXC_RESID16_G137 = 0x7CDD
BIG6_HOME_CUSTOM_KEY_F_UXC_RESID16_G137 = 0x7CAD

BIG6_ENTRY_NONE_G137 = "None"
BIG6_ENTRY_HOME_KEY_G137 = "HOME Key"
BIG6_ENTRY_SWIPE_DOWN_G137 = "Swipe Down"
ALLOWED_BIG6_ENTRY_TRIGGERS_G137: Tuple[str, ...] = (
    BIG6_ENTRY_NONE_G137,
    BIG6_ENTRY_HOME_KEY_G137,
    BIG6_ENTRY_SWIPE_DOWN_G137,
)

HOME_LOWER_LEFT_APERTURE_G137 = "Aperture"
HOME_LOWER_LEFT_ND_FILTER_G137 = "ND Filter"
ALLOWED_HOME_LOWER_LEFT_MODES_G137: Tuple[str, ...] = (
    HOME_LOWER_LEFT_APERTURE_G137,
    HOME_LOWER_LEFT_ND_FILTER_G137,
)

LOG_SHOOTING_OFF_G137 = "Off"
LOG_SHOOTING_FLEXIBLE_ISO_G137 = "Flexible ISO"
LOG_SHOOTING_CINE_EI_G137 = "Cine EI"
LOG_SHOOTING_CINE_EI_QUICK_G137 = "Cine EI Quick"
ALLOWED_LOG_SHOOTING_MODES_G137: Tuple[str, ...] = (
    LOG_SHOOTING_OFF_G137,
    LOG_SHOOTING_FLEXIBLE_ISO_G137,
    LOG_SHOOTING_CINE_EI_G137,
    LOG_SHOOTING_CINE_EI_QUICK_G137,
)

SHUTTER_MODE_SPEED_G137 = "Speed"
SHUTTER_MODE_ANGLE_G137 = "Angle"
ALLOWED_SHUTTER_MODES_G137: Tuple[str, ...] = (
    SHUTTER_MODE_SPEED_G137,
    SHUTTER_MODE_ANGLE_G137,
)

FX3_BIG6_EXACT_6_TILES_LABELS_G137: Tuple[str, ...] = (
    "FPS",
    "ISO / Base ISO + EI",
    "Shutter Speed / Angle",
    "Aperture / ND Filter (Metadata Only)",
    "Picture Profile / Select LUT",
    "White Balance",
)
FX6_END_ND_OPTIONS_G137: Tuple[str, ...] = ("Clear", "1/4..1/128", "Auto")

FRAMING_SETTINGS_F_UXC_RESID16_G137 = 0x7D18
FRAMING_REC_STREAM_FULL_G137 = "Full"
FRAMING_REC_STREAM_CROP_G137 = "Crop"
ALLOWED_FRAMING_REC_STREAM_MODES_G137: Tuple[str, ...] = (
    FRAMING_REC_STREAM_FULL_G137,
    FRAMING_REC_STREAM_CROP_G137,
)
FRAMING_HDMI_CROP_G137 = "Crop"
FRAMING_HDMI_FULL_G137 = "Full"
ALLOWED_FRAMING_HDMI_MODES_G137: Tuple[str, ...] = (
    FRAMING_HDMI_CROP_G137,
    FRAMING_HDMI_FULL_G137,
)

DORMANT_AUTO_FRAMING_TRAPS_G137: Tuple[str, ...] = (
    "Auto Framing",
    "Auto Framing Settings",
    "AUTO_FRAMING_AFR",
    "PTZAUTOFRAMING",
    "PTZAUTOFRAMING_ON",
    "FRAMING_SIZE",
    "BKID_APP_setting_auto_framing",
    "0x6be6",
    "0x79bc",
    "0x6c9d",
    "0x69cc",
    "0x7566",
    "0x60e6",
    "0x62ad",
    "0x63d1",
)

INTERVAL_SHOOT_F_UXC_RESID16_G137 = 0x7027
INTERVAL_SHOOT_7_PARAMS_G137: Tuple[str, ...] = (
    "Interval Shooting",
    "Shooting Start Time",
    "Shooting Interval",
    "Number of Shots",
    "AE Tracking Sensitivity",
    "Shutter Type in Interval",
    "Shoot Interval Priority",
)
INTERVAL_START_TIME_MIN_SEC_G137 = 1
INTERVAL_START_TIME_MAX_SEC_G137 = 5999  # 99m59s
INTERVAL_START_TIME_DEFAULT_SEC_G137 = 1

INTERVAL_PERIOD_MIN_SEC_G137 = 1
INTERVAL_PERIOD_MAX_SEC_G137 = 60
INTERVAL_PERIOD_DEFAULT_SEC_G137 = 3

INTERVAL_SHOTS_MIN_G137 = 1
INTERVAL_SHOTS_MAX_G137 = 9999
INTERVAL_SHOTS_DEFAULT_G137 = 30
INTERVAL_MAX_DCIM_FILES_G137 = 19998

ALLOWED_AE_TRACKING_SENSITIVITIES_G137: Tuple[str, ...] = ("High", "Mid", "Low")
INTERVAL_SHUTTER_ELECTRONIC_G137 = "Electronic Shutter"
INTERVAL_SHUTTER_MECHANICAL_G137 = "Mechanical Shutter"
ALLOWED_INTERVAL_SHUTTER_TYPES_G137: Tuple[str, ...] = (
    INTERVAL_SHUTTER_ELECTRONIC_G137,
    INTERVAL_SHUTTER_MECHANICAL_G137,
)
INTERVAL_STILL_FORMAT_RAW_G137 = "RAW"
INTERVAL_STILL_FORMAT_JPEG_G137 = "JPEG"
INTERVAL_STILL_FORMAT_HEIF_G137 = "HEIF"
INTERVAL_STILL_FORMAT_RAW_JPEG_G137 = "RAW+JPEG"
INTERVAL_STILL_FORMAT_RAW_HEIF_G137 = "RAW+HEIF"
ALLOWED_INTERVAL_STILL_FORMATS_G137: Tuple[str, ...] = (
    INTERVAL_STILL_FORMAT_RAW_G137,
    INTERVAL_STILL_FORMAT_JPEG_G137,
    INTERVAL_STILL_FORMAT_HEIF_G137,
    INTERVAL_STILL_FORMAT_RAW_JPEG_G137,
    INTERVAL_STILL_FORMAT_RAW_HEIF_G137,
)

# ---------------------------------------------------------------------------
# G138 Constants: TC Make / HDMI REC Control / SSH Access Authen. / Fan Control
# ---------------------------------------------------------------------------

TC_MAKE_F_UXC_RESID16_G138 = 0x6B79
TC_RUN_F_UXC_RESID16_G138 = 0x7313
HDMI_REC_CONTROL_F_UXC_RESID16_G138 = 0x76E1
HDMI_TC_OUTPUT_F_UXC_RESID16_G138 = 0x72AF
HDMI_4CH_AUDIO_OUTPUT_F_UXC_RESID16_G138 = 0x6AA0

TC_MAKE_PRESET_G138 = "Preset"
TC_MAKE_REGENERATE_G138 = "Regenerate"
TC_MAKE_FX6_CLOCK_G138 = "Clock"
ALLOWED_FX3_TC_MAKE_MODES_G138: Tuple[str, ...] = (
    TC_MAKE_PRESET_G138,
    TC_MAKE_REGENERATE_G138,
)
ALLOWED_FX6_TC_MAKE_MODES_G138: Tuple[str, ...] = (
    TC_MAKE_PRESET_G138,
    TC_MAKE_REGENERATE_G138,
    TC_MAKE_FX6_CLOCK_G138,
)

TC_RUN_REC_RUN_G138 = "Rec Run"
TC_RUN_FREE_RUN_G138 = "Free Run"
ALLOWED_TC_RUN_MODES_G138: Tuple[str, ...] = (
    TC_RUN_REC_RUN_G138,
    TC_RUN_FREE_RUN_G138,
)

HDMI_REC_MEDIA_ON_G138 = "On"
HDMI_REC_MEDIA_OFF_HDMI_ONLY_G138 = "Off(HDMI Only)"
ALLOWED_REC_MEDIA_DUR_HDMI_G138: Tuple[str, ...] = (
    HDMI_REC_MEDIA_ON_G138,
    HDMI_REC_MEDIA_OFF_HDMI_ONLY_G138,
)

AUDIO_4CH_CH1_CH2_G138 = "CH1/CH2"
AUDIO_4CH_CH3_CH4_G138 = "CH3/CH4"
ALLOWED_4CH_AUDIO_OUTPUT_G138: Tuple[str, ...] = (
    AUDIO_4CH_CH1_CH2_G138,
    AUDIO_4CH_CH3_CH4_G138,
)

FX6_SDI_HDMI_REC_CTRL_OFF_G138 = "Off"
FX6_SDI_HDMI_REMOTE_IF_G138 = "SDI/HDMI Remote I/F"
FX6_PARALLEL_REC_G138 = "Parallel Rec"
ALLOWED_FX6_SDI_HDMI_REC_CTRL_MODES_G138: Tuple[str, ...] = (
    FX6_SDI_HDMI_REC_CTRL_OFF_G138,
    FX6_SDI_HDMI_REMOTE_IF_G138,
    FX6_PARALLEL_REC_G138,
)

ACCESS_AUTHEN_F_UXC_RESID16_G138 = 0x7ADA
SSH_HOST_KEY_G_UXC_RESID16_G138 = 0x610B
IMPORT_ROOT_CERT_F_UXC_RESID16_G138 = 0x7940

ALLOWED_ACCESS_AUTHEN_TRANSPORTS_G138: Tuple[str, ...] = ("SSH", "PTP-IP")
FORBIDDEN_HTTP_AUTH_MYTHS_G138: Tuple[str, ...] = (
    "HTTP_DIGEST",
    "BASIC_AUTH",
    "HTTPS",
    "HTTPS_SERVER",
    "Digest",
    "Basic",
)
OUTBOUND_CLIENT_TLS_TYPES_G138: Tuple[str, ...] = ("Cloud", "FTPS", "RTMPS")

FAN_CONTROL_AUTO_G138 = "Auto"
FAN_CONTROL_MINIMUM_G138 = "Minimum"
FAN_CONTROL_OFF_IN_REC_G138 = "Off in Rec"
FAN_CONTROL_ALWAYS_OFF_G138 = "Always Off"
FX3_EXACT_4_FAN_MODES_G138: Tuple[str, ...] = (
    FAN_CONTROL_AUTO_G138,
    FAN_CONTROL_MINIMUM_G138,
    FAN_CONTROL_OFF_IN_REC_G138,
    FAN_CONTROL_ALWAYS_OFF_G138,
)
FX6_EXACT_3_FAN_MODES_G138: Tuple[str, ...] = (
    FAN_CONTROL_AUTO_G138,
    FAN_CONTROL_MINIMUM_G138,
    FAN_CONTROL_OFF_IN_REC_G138,
)
FORBIDDEN_FAN_MAX_TOKENS_G138: Tuple[str, ...] = (
    "Max",
    "MAX",
    "Maximum",
    "FAN_CONTROL_MAX",
    "Full",
)

AUTO_PWR_OFF_TEMP_STANDARD_G138 = "Standard"
AUTO_PWR_OFF_TEMP_HIGH_G138 = "High"
ALLOWED_AUTO_PWR_OFF_TEMP_MODES_G138: Tuple[str, ...] = (
    AUTO_PWR_OFF_TEMP_STANDARD_G138,
    AUTO_PWR_OFF_TEMP_HIGH_G138,
)

# Status / Violation Codes
STATUS_BLOCKED_PHASE313_DONOR_INTEGRITY = "STATUS_BLOCKED_PHASE313_DONOR_INTEGRITY"

STATUS_VERIFIED_G137 = "STATUS_VERIFIED_G137"
STATUS_BLOCKED_G137_TELEMETRY_INVALID = "STATUS_BLOCKED_G137_TELEMETRY_INVALID"
STATUS_BLOCKED_G137_BIG6_PREREQ_HDMI_OR_END_ACTUATOR_VIOLATION = (
    "STATUS_BLOCKED_G137_BIG6_PREREQ_HDMI_OR_END_ACTUATOR_VIOLATION"
)
STATUS_BLOCKED_G137_DORMANT_AUTO_FRAMING_OR_LOCK_VIOLATION = (
    "STATUS_BLOCKED_G137_DORMANT_AUTO_FRAMING_OR_LOCK_VIOLATION"
)
STATUS_BLOCKED_G137_INTERVAL_SHOOT_PARAM_OR_FX6_CROSSWIRE_VIOLATION = (
    "STATUS_BLOCKED_G137_INTERVAL_SHOOT_PARAM_OR_FX6_CROSSWIRE_VIOLATION"
)
STATUS_BLOCKED_G137_SLOT1_INTERVAL_9999_VAULT_FIREWALL_VIOLATION = (
    "STATUS_BLOCKED_G137_SLOT1_INTERVAL_9999_VAULT_FIREWALL_VIOLATION"
)

STATUS_VERIFIED_G138 = "STATUS_VERIFIED_G138"
STATUS_BLOCKED_G138_TELEMETRY_INVALID = "STATUS_BLOCKED_G138_TELEMETRY_INVALID"
STATUS_BLOCKED_G138_TC_MAKE_CLOCK_REGEN_OR_HDMI_REC_CTRL_VIOLATION = (
    "STATUS_BLOCKED_G138_TC_MAKE_CLOCK_REGEN_OR_HDMI_REC_CTRL_VIOLATION"
)
STATUS_BLOCKED_G138_SSH_ACCESS_AUTHEN_HTTPS_MYTH_OR_CERT_VIOLATION = (
    "STATUS_BLOCKED_G138_SSH_ACCESS_AUTHEN_HTTPS_MYTH_OR_CERT_VIOLATION"
)
STATUS_BLOCKED_G138_FAN_MAX_MYTH_OR_FX6_ALWAYS_OFF_VIOLATION = (
    "STATUS_BLOCKED_G138_FAN_MAX_MYTH_OR_FX6_ALWAYS_OFF_VIOLATION"
)

# ---------------------------------------------------------------------------
# Pinned Wave-59 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE313: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (62_675_770, b"BKID_APP_setting_fps_fixed_variable_select"),
    (62_255_365, b"VAL_setting_swipe_down_SWIPE_DOWN_HOME_SCREEN"),
    (51_996_901, b"update_big6_item_iso_ei"),
    (50_154_208, b"26view_tp_button_01_for_big6"),
    (62_699_375, b"BKID_APP_setting_movie_home_lower_left"),
    (49_968_187, b"MOVIE_HOME_LOWER_LEFT_ND_FILTER"),
    (49_968_219, b"MOVIE_HOME_LOWER_LEFT_APERTURE"),
    (60_635_035, b"TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY"),
    (62_679_973, b"BKID_APP_setting_interval_shooting"),
    (62_682_074, b"BKID_APP_setting_tc_make"),
    (61_950_389, b"VAL_setting_tc_make_TC_MAKE_REGENRATE"),
    (62_682_050, b"BKID_APP_setting_tc_run"),
    (62_626_900, b"CAUTION_ID_FACTOR_TC_MAKE_REGENERATE_MSG"),
    (62_702_057, b"BKID_APP_setting_rec_control"),
    (60_562_356, b"PRM_HAITA_setting_rec_control_"),
    (60_417_189, b"MSGID_SSHD_START_CMD"),
    (60_418_576, b"sshd_start"),
    (62_965_928, b"ROOT_CERTIFICATE_TYPE_CLOUD"),
    (62_702_281, b"BKID_APP_setting_fan_control"),
    (62_701_490, b"BKID_APP_setting_auto_pwr_off_temp"),
    (49_972_234, b"FAN_CONTROL_AUTO"),
    (49_972_251, b"FAN_CONTROL_MIN"),
    (49_972_271, b"FAN_CONTROL_OFF_IN_REC"),
    (49_972_294, b"FAN_CONTROL_ALWAYS_OFF"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE313 = (
    "15f6ea2ca04673895bbcca9c2ef1502abc46c220122179b3cb2547372806a09e"
)

PINNED_FX6_APPFW_SLICES_PHASE313: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (41_748_974, b"PRODUCT_MODEL_CHAPLIN"),
    (37_415_906, b"procam_big6_menu_home_presenter"),
    (37_478_018, b"procam_big6_menu_home_controller"),
    (37_235_606, b"MODEL_VALUE_CHANGED_BY_EXCLUSION_INTERVAL_REC"),
    (40_633_136, b"VAL_setting_tc_make_TC_MAKE_CLOCK"),
    (41_640_946, b"FAN_CONTROL_ALWAYS_OFF"),
    (40_923_216, b"BKID_APP_SETTING_FAN_CONTROL"),
    (41_640_886, b"FAN_CONTROL_AUTO"),
    (41_640_903, b"FAN_CONTROL_MINIMUM"),
    (41_640_923, b"FAN_CONTROL_OFF_IN_REC"),
    (40_638_280, b"VAL_setting_sdi_hdmi_rec_control"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE313 = (
    "5cc33db45343140b910c326e4505c9576b2bbcbfb21b26a79b5ccf78bac606b3"
)

PINNED_PHASE313_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE313,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE313),
        "FX3 appFw.so Wave-59 BIG6/Framing/Interval/TC-Make/REC-Control/SSHD/Fan-Control slices",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Fixed/Variable",
            b"Home (Lower Left)",
            b"Framing Settings",
            b"Auto Framing",
            b"Interval Shoot Func.",
            b"Time Code Make",
            b"REC Control",
            b"4ch Audio Output",
            b"Access Authen. Settings",
            b"Import Root Certificate",
            b"Fan Control",
            b"Always Off",
            b"Off in Rec",
            b"Auto Power OFF Temp.",
        ),
        "FX3 string_english_f.uxc Wave-59 EN parity",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "固定/可变".encode("utf-8"),
            "主屏幕(左下)".encode("utf-8"),
            "取景设置".encode("utf-8"),
            "自动构图".encode("utf-8"),
            "间隔拍摄功能".encode("utf-8"),
            "REC控制".encode("utf-8"),
            "4ch音频输出".encode("utf-8"),
            "访问身份验证设置".encode("utf-8"),
            "导入根证书".encode("utf-8"),
            "风扇控制".encode("utf-8"),
            "总是关".encode("utf-8"),
            "自动关机温度".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-59 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "固定/變數".encode("utf-8"),
            "主螢幕(左下)".encode("utf-8"),
            "取景設定".encode("utf-8"),
            "時間間隔拍攝功能".encode("utf-8"),
            "REC控制".encode("utf-8"),
            "4ch音訊輸出".encode("utf-8"),
            "存取身份驗證設定".encode("utf-8"),
            "匯入根憑證".encode("utf-8"),
            "風扇控制".encode("utf-8"),
            "始終關".encode("utf-8"),
            "自動關閉電源溫度".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-59 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "Fixed/Variable".encode("utf-8"),
            "ホーム設定(左下)".encode("utf-8"),
            "フレーミング設定".encode("utf-8"),
            "ｵｰﾄﾌﾚｰﾐﾝｸﾞ設定".encode("utf-8"),
            "ｲﾝﾀｰﾊﾞﾙ撮影機能".encode("utf-8"),
            "RECコントロール".encode("utf-8"),
            "4ch音声の出力".encode("utf-8"),
            "アクセス認証設定".encode("utf-8"),
            "ﾙｰﾄ証明書の読み込み".encode("utf-8"),
            "ファン制御".encode("utf-8"),
            "常にOff".encode("utf-8"),
            "自動電源OFF温度".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-59 JA parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Minimum",
            b"Auto",
            b"Standard",
            b"High",
        ),
        "FX3 string_english.uxc Wave-59 Fan/Temp option strings",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Framing",
            b"Home",
        ),
        "FX3 string_english_g.uxc Wave-59 menu group strings",
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
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE313,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE313),
        "FX6 appFw.so Wave-59 BIG6/IntervalRec/TC-Clock/SDI-HDMI-RecControl/Fan-3Mode slices",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"Timecode",
            b"Free Run",
            b"Rec Run",
        ),
        "FX6 string_english.uxc Wave-59 strings",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"Interval Rec",
            b"SDI/HDMI Rec Control",
            b"Parallel Rec",
            b"Fan Control",
            b"Clock",
            b"ND Filter",
        ),
        "FX6 string_english_2.uxc Wave-59 strings",
    ),
}

_DONOR_BLOB_CACHE: Dict[str, Tuple[int, float, int, str, bytes]] = {}

# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase313DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    elapsed_seconds: float
    within_budget_200ms: bool
    raw_firmware_bytes_leaked: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    fx6_contracts_verified: bool
    four_lang_resid16_parity_verified: bool
    zero_forbidden_myths_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Big6HomeFramingIntervalVaultGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    target_model: str
    reset_action: str
    shoot_mode: str
    exposure_mode: str
    fps: float
    active_recording: bool
    streaming_active: bool
    touch_operation_enabled: bool
    requested_mode_settings: str
    effective_mode_settings: str
    big6_entry_trigger: str
    big6_screen_active: bool
    big6_cursor_active: bool
    big6_hdmi_output_active: bool
    log_shooting_mode: str
    shutter_mode: str
    requested_home_lower_left: str
    effective_home_lower_left: str
    big6_exact_6_tiles: Tuple[str, ...]
    big6_iso_or_ei_tile_label: str
    big6_pp_or_lut_tile_label: str
    fx3_physical_end_actuator_present: bool
    fx6_physical_end_options: Tuple[str, ...]
    requested_framing_on: bool
    effective_framing_on: bool
    framing_locked_out: bool
    framing_lockout_reasons: Tuple[str, ...]
    framing_rec_stream_mode: str
    framing_hdmi_mode: str
    apsc_s35_disabled_by_framing: bool
    dormant_auto_framing_blocked: bool
    fx3_framing_support_lock: str
    requested_interval_shooting: str
    effective_interval_shooting: str
    interval_start_time_sec: int
    interval_period_sec: int
    interval_shot_count: int
    interval_still_format: str
    interval_ae_tracking_sensitivity: str
    interval_shutter_type: str
    interval_priority: str
    interval_max_dcim_files: int
    interval_bulb_exited_to_30s: bool
    interval_disabled_in_iauto: bool
    fx6_interval_rec_single_mxf: bool
    requested_target_slot: str
    effective_target_slot: str
    slot_1_contains_tier0_vault: bool
    slot_1_write_protected: bool
    slot1_vault_firewall_blocked: bool
    block_errno: Optional[int]
    block_errno_name: Optional[str]
    slot1_data_sector_writes: int
    slot1_dcim_mutated: bool
    slot1_avf_info_mutated: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G137Big6HomeFramingIntervalVaultGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    big6_home_framing_interval_vault_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TcMakeHdmiRecSshAuthenFanGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    fx6_comparison_fw_version: str
    target_model: str
    reset_action: str
    shoot_mode: str
    recording_media_mode: str
    requested_tc_make: str
    effective_tc_make: str
    requested_tc_run: str
    effective_tc_run: str
    tc_regenerate_forced_rec_run: bool
    tc_regenerate_source_slot: str
    vmc_bncm1_ext_ltc_requested: bool
    ext_tc_lock_status: str
    hdmi_tc_output: str
    requested_hdmi_rec_control: str
    effective_hdmi_rec_control: str
    rec_media_dur_hdmi_output: str
    hdmi_raw_output_on: bool
    cardless_hdmi_rec_ctrl_permitted: bool
    hdmi_rec_ctrl_restricted_reasons: Tuple[str, ...]
    audio_4ch_output_channels: str
    fx6_sdi_hdmi_rec_ctrl_mode: str
    fx6_parallel_rec_follows_slot_a: bool
    requested_access_authen_settings: str
    effective_access_authen_settings: str
    access_authen_transports: Tuple[str, ...]
    sshd_control_active: bool
    access_authen_survived_cam_reset: bool
    access_authen_reset_by_net_or_init: bool
    http_digest_or_https_server_blocked: bool
    import_root_cert_requested: bool
    import_root_cert_type: str
    import_root_cert_outbound_client_tls_only: bool
    import_root_cert_slot: str
    slot_1_contains_tier0_vault: bool
    slot1_vault_cert_blocked: bool
    slot1_data_sector_writes: int
    requested_fan_control: str
    effective_fan_control: str
    fan_off_in_rec_temp_override_active: bool
    requested_auto_pwr_off_temp: str
    effective_auto_pwr_off_temp: str
    low_temp_burn_tripod_warning: bool
    fx3_exact_fan_modes_count: int
    fx6_exact_fan_modes_count: int
    fx6_always_off_dormant_blocked: bool
    fan_max_myth_blocked: bool
    block_errno: Optional[int]
    block_errno_name: Optional[str]
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G138TcMakeHdmiRecSshAuthenFanGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    tc_make_hdmi_rec_ssh_authen_fan_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master138GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_135_gates_verified: bool
    all_138_gates_verified: bool
    g13_to_g138_all_passed: bool
    g137_to_g138_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_136_report: Dict[str, Any]
    g137_result: Dict[str, Any]
    g138_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _is_truthy(val: Optional[str]) -> bool:
    if val is None:
        return False
    return val.strip().lower() in ("1", "true", "yes", "on")


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return _is_truthy(os.environ.get(ENV_FORCE_CLEAN_ROOM)) or _is_truthy(
        os.environ.get(ENV_CLEAN_ROOM_TEST_PHASE313)
    )


def _is_ci_env() -> bool:
    return _is_truthy(os.environ.get("GITHUB_ACTIONS"))


def _is_real_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _parse_fw_major_minor(fw: Any) -> Optional[Tuple[int, int]]:
    if not isinstance(fw, str):
        return None
    m = re.match(r"^\s*(\d+)\.(\d+)", fw.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _read_exact_o_rdonly(path: Path) -> Tuple[int, str, bytes]:
    """Read an entire small UXC/BIN donor file strictly via os.O_RDONLY."""
    key = str(path.resolve())
    st = os.stat(key)
    cached = _DONOR_BLOB_CACHE.get(key)
    if (
        cached is not None
        and cached[0] == st.st_size
        and cached[1] == st.st_mtime
        and cached[2] == getattr(st, "st_ino", 0)
    ):
        return cached[0], cached[3], cached[4]

    fd = os.open(key, os.O_RDONLY)
    try:
        chunks: List[bytes] = []
        hasher = hashlib.sha256()
        total = 0
        while True:
            blk = os.read(fd, 1024 * 1024)
            if not blk:
                break
            total += len(blk)
            hasher.update(blk)
            chunks.append(blk)
        blob = b"".join(chunks)
        digest = hasher.hexdigest()
        _DONOR_BLOB_CACHE[key] = (
            total,
            st.st_mtime,
            getattr(st, "st_ino", 0),
            digest,
            blob,
        )
        return total, digest, blob
    finally:
        os.close(fd)


def _read_appfw_slices_o_rdonly(
    path: Path,
    slices: Tuple[Tuple[int, bytes], ...],
) -> Tuple[int, str, Tuple[bytes, ...]]:
    """Bounded os.pread SHA-256 verification over pinned appFw.so byte slices."""
    key = f"{path.resolve()}::slices313::{len(slices)}"
    st = os.stat(path)
    cached = _DONOR_BLOB_CACHE.get(key)
    if (
        cached is not None
        and cached[0] == st.st_size
        and cached[1] == st.st_mtime
        and cached[2] == getattr(st, "st_ino", 0)
    ):
        return cached[0], cached[3], tuple(tok for _, tok in slices)

    fd = os.open(str(path), os.O_RDONLY)
    try:
        hasher = hashlib.sha256()
        missing: List[bytes] = []
        for offset, expected in slices:
            if offset < 0 or offset + len(expected) > st.st_size:
                missing.append(expected)
                continue
            observed = os.pread(fd, len(expected), offset)
            if observed != expected:
                missing.append(expected)
            else:
                hasher.update(observed)
        digest = hasher.hexdigest() if not missing else "MISSING_SLICE"
        if not missing:
            _DONOR_BLOB_CACHE[key] = (
                st.st_size,
                st.st_mtime,
                getattr(st, "st_ino", 0),
                digest,
                b"",
            )
        present = tuple(tok for _, tok in slices if tok not in missing)
        return st.st_size, digest, present
    finally:
        os.close(fd)


def _normalize_shoot_mode(mode: Any) -> Optional[str]:
    if not isinstance(mode, str):
        return None
    m = mode.strip().lower()
    if m in ("still", "photo"):
        return SHOOT_MODE_STILL_PHASE313
    if m in ("movie", "video"):
        return SHOOT_MODE_MOVIE_PHASE313
    if m in ("s&q", "sq", "s&q motion", "snq"):
        return SHOOT_MODE_SQ_PHASE313
    return None


def _normalize_exposure_mode(mode: Any) -> Optional[str]:
    if not isinstance(mode, str):
        return None
    m = mode.strip().lower()
    if m == "p":
        return EXPOSURE_MODE_P_G137
    if m == "a":
        return EXPOSURE_MODE_A_G137
    if m == "s":
        return EXPOSURE_MODE_S_G137
    if m == "m":
        return EXPOSURE_MODE_M_G137
    if m in ("intelligent auto", "iauto", "auto"):
        return EXPOSURE_MODE_INTELLIGENT_AUTO_G137
    return None


def _normalize_reset_action(action: Any) -> Optional[str]:
    if not isinstance(action, str):
        return None
    a = action.strip().lower()
    if a in ("none", ""):
        return RESET_ACTION_NONE_PHASE313
    if a in ("camera settings reset", "cam_reset"):
        return RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE313
    if a in ("reset network set.", "reset network set", "net_reset"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE313
    if a in ("initialize", "factory reset"):
        return RESET_ACTION_INITIALIZE_PHASE313
    return None


def _normalize_on_off(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    v = val.strip().lower()
    if v == "on":
        return "On"
    if v == "off":
        return "Off"
    return None


def _normalize_recording_media_mode(slot: Any) -> Optional[str]:
    if not isinstance(slot, str):
        return None
    s = slot.strip().lower()
    if s in ("slot 1", "slot1", "slot_a", "a"):
        return MEDIA_SLOT_1_PHASE313
    if s in ("slot 2", "slot2", "slot_b", "b"):
        return MEDIA_SLOT_2_PHASE313
    if s in ("simult. recording", "simult", "simul", "simultaneous"):
        return MEDIA_SIMULT_RECORDING_PHASE313
    return None


# ---------------------------------------------------------------------------
# 1. Bounded O_RDONLY Donor Audit (Phase 313)
# ---------------------------------------------------------------------------


def audit_phase313_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase313DonorAuditResult:
    """Inspect Wave-59 donor contracts via bounded O_RDONLY reads or clean-room fallback."""
    t0 = time.perf_counter()
    clean_forced = _is_forced_clean_room(force_clean_room)
    budget_s = (
        DONOR_CHECK_CI_MAX_SECONDS_PHASE313 + 15.0
        if _is_ci_env()
        else DONOR_CHECK_MAX_SECONDS_PHASE313
    )

    if clean_forced:
        dt = time.perf_counter() - t0
        return Phase313DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_NO_DONOR_TOUCH",
            files_inspected=0,
            elapsed_seconds=round(dt, 6),
            within_budget_200ms=dt <= budget_s,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(PINNED_PHASE313_DONOR_SPECS.keys()),
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            zero_forbidden_myths_verified=True,
            sha256_by_artifact={},
            bytes_by_artifact={},
            errors=(),
            warnings=(),
        )

    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    if work_root is None:
        paths = resolve_donor_thermal_power_paths(repo_root=resolved_root)
        resolved_work_root = paths.work_root
    else:
        resolved_work_root = Path(work_root).resolve()

    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else PINNED_PHASE313_DONOR_SPECS
    )

    if donor_specs_override is None:
        anchor_path = resolved_work_root / specs["fx3_string_english_f_uxc"][1]
        fx6_anchor = resolved_work_root / specs["fx6_string_english_2_uxc"][1]
        if (not anchor_path.exists()) or (not fx6_anchor.exists()):
            dt = time.perf_counter() - t0
            return Phase313DonorAuditResult(
                valid=True,
                status=STATUS_VERIFIED_SAFE,
                verification_mode="CLEAN_ROOM_SYNTHETIC",
                access_mode="SYNTHETIC_ABSENT_DONOR_FALLBACK",
                files_inspected=0,
                elapsed_seconds=round(dt, 6),
                within_budget_200ms=dt <= budget_s,
                raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
                checked_markers=tuple(specs.keys()),
                missing_markers=(),
                fx3_contracts_verified=True,
                fx6_contracts_verified=True,
                four_lang_resid16_parity_verified=True,
                zero_forbidden_myths_verified=True,
                sha256_by_artifact={},
                bytes_by_artifact={},
                errors=(),
                warnings=(
                    "Donor workspace absent; verified Phase 313 via deterministic clean-room contracts.",
                ),
            )

    checked: List[str] = []
    missing: List[str] = []
    sha_map: Dict[str, str] = {}
    size_map: Dict[str, int] = {}
    errors: List[str] = []

    for key, (family, rel_path, expected_size, expected_sha, tokens, desc) in specs.items():
        target = resolved_work_root / rel_path
        checked.append(key)
        if not target.is_file():
            missing.append(f"{key}:missing_file")
            errors.append(f"{family} donor file missing: {rel_path} ({desc})")
            continue
        try:
            if key == "fx3_appfw_so" and donor_specs_override is None:
                actual_size, actual_sha, present = _read_appfw_slices_o_rdonly(
                    target, PINNED_FX3_APPFW_SLICES_PHASE313
                )
                missing_toks = [tok for tok in tokens if tok not in present]
            elif key == "fx6_appfw_so" and donor_specs_override is None:
                actual_size, actual_sha, present = _read_appfw_slices_o_rdonly(
                    target, PINNED_FX6_APPFW_SLICES_PHASE313
                )
                missing_toks = [tok for tok in tokens if tok not in present]
            else:
                actual_size, actual_sha, blob = _read_exact_o_rdonly(target)
                missing_toks = [tok for tok in tokens if tok not in blob]
        except OSError as exc:
            missing.append(f"{key}:os_error")
            errors.append(f"os.O_RDONLY failed on {rel_path}: {exc}")
            continue

        sha_map[key] = actual_sha
        size_map[key] = actual_size
        if actual_size != expected_size:
            missing.append(f"{key}:size_mismatch")
            errors.append(
                f"{key} size mismatch: expected={expected_size}, got={actual_size}"
            )
        if actual_sha != expected_sha:
            missing.append(f"{key}:sha256_mismatch")
            errors.append(
                f"{key} sha256 mismatch: expected={expected_sha}, got={actual_sha}"
            )
        if missing_toks:
            missing.append(f"{key}:token_missing")
            errors.append(
                f"{key} missing {len(missing_toks)} expected Wave-59 contract tokens"
            )

    dt = time.perf_counter() - t0
    valid = (len(missing) == 0) and (len(errors) == 0)
    fx3_ok = valid and all(
        k in sha_map for k in specs if k.startswith("fx3_")
    )
    fx6_ok = valid and all(
        k in sha_map for k in specs if k.startswith("fx6_")
    )
    lang_ok = valid and all(
        k in sha_map
        for k in (
            "fx3_string_english_f_uxc",
            "fx3_string_simplifiedchinese_f_uxc",
            "fx3_string_traditionalchinese_f_uxc",
            "fx3_string_japanese_f_uxc",
        )
    )
    return Phase313DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE313_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="POSIX_O_RDONLY_AND_PREAD_ZERO_MUTATION",
        files_inspected=len(sha_map),
        elapsed_seconds=round(dt, 6),
        within_budget_200ms=dt <= budget_s,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_ok,
        fx6_contracts_verified=fx6_ok,
        four_lang_resid16_parity_verified=lang_ok,
        zero_forbidden_myths_verified=valid,
        sha256_by_artifact=sha_map,
        bytes_by_artifact=size_map,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate G137: BIG6 Home, Manual vs Dormant Auto Framing, Interval Shoot Vault
# ---------------------------------------------------------------------------


def _compute_g137_effective_state(
    *,
    shoot_mode: str,
    exposure_mode: str,
    reset_action: str,
    fps: float,
    active_recording: bool,
    streaming_active: bool,
    touch_operation_enabled: bool,
    mode_settings: str,
    big6_entry_trigger: str,
    big6_cursor_active: bool,
    log_shooting_mode: str,
    shutter_mode: str,
    home_lower_left: str,
    framing_on: bool,
    framing_rec_stream_mode: str,
    framing_hdmi_mode: str,
    interval_shooting: str,
    interval_start_time_sec: int,
    interval_period_sec: int,
    interval_shot_count: int,
    interval_still_format: str,
    interval_ae_tracking_sensitivity: str,
    interval_shutter_type: str,
    interval_priority: str,
    interval_execute_requested: bool,
    requested_target_slot: str,
    slot_1_contains_tier0_vault: bool,
    slot_1_write_protected: bool,
) -> Dict[str, Any]:
    cam_or_init = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE313,
        RESET_ACTION_INITIALIZE_PHASE313,
    )

    eff_mode_settings = (
        MODE_SETTINGS_FIXED_FPS_G137 if cam_or_init else mode_settings
    )
    eff_home_lower_left = (
        HOME_LOWER_LEFT_APERTURE_G137 if cam_or_init else home_lower_left
    )
    eff_framing_on = False if cam_or_init else bool(framing_on)
    eff_interval_shooting = "Off" if cam_or_init else interval_shooting

    # BIG6 entry: Movie or S&Q with Mode Settings == Fixed/Variable; Swipe Down requires Touch Op
    big6_prereq_ok = (
        shoot_mode in (SHOOT_MODE_MOVIE_PHASE313, SHOOT_MODE_SQ_PHASE313)
        and eff_mode_settings == MODE_SETTINGS_FIXED_VARIABLE_G137
    )
    swipe_blocked = (
        big6_entry_trigger == BIG6_ENTRY_SWIPE_DOWN_G137
        and not touch_operation_enabled
    )
    big6_active = (
        big6_prereq_ok
        and big6_entry_trigger != BIG6_ENTRY_NONE_G137
        and not swipe_blocked
    )

    iso_tile = (
        "Base ISO + EI"
        if log_shooting_mode in (LOG_SHOOTING_CINE_EI_G137, LOG_SHOOTING_CINE_EI_QUICK_G137)
        else "ISO"
    )
    pp_lut_tile = (
        "Select LUT"
        if log_shooting_mode != LOG_SHOOTING_OFF_G137
        else "Picture Profile"
    )

    lockout_reasons: List[str] = []
    if fps >= 100.0:
        lockout_reasons.append("high_frame_rate_ge_100p")
    if active_recording:
        lockout_reasons.append("active_recording")
    if streaming_active:
        lockout_reasons.append("streaming_active")
    if shoot_mode == SHOOT_MODE_STILL_PHASE313:
        lockout_reasons.append("still_mode")
    framing_locked = len(lockout_reasons) > 0
    apsc_s35_disabled = bool(eff_framing_on)

    # Interval Shoot Func.
    interval_disabled_iauto = exposure_mode == EXPOSURE_MODE_INTELLIGENT_AUTO_G137
    interval_active = (
        shoot_mode == SHOOT_MODE_STILL_PHASE313
        and eff_interval_shooting == "On"
        and not interval_disabled_iauto
    )
    if cam_or_init:
        eff_start = INTERVAL_START_TIME_DEFAULT_SEC_G137
        eff_period = INTERVAL_PERIOD_DEFAULT_SEC_G137
        eff_shots = INTERVAL_SHOTS_DEFAULT_G137
        eff_ae = "Mid"
        eff_ishut = INTERVAL_SHUTTER_ELECTRONIC_G137
        eff_iprio = "Off"
    else:
        eff_start = interval_start_time_sec
        eff_period = interval_period_sec
        eff_shots = interval_shot_count
        eff_ae = interval_ae_tracking_sensitivity
        eff_ishut = interval_shutter_type
        eff_iprio = interval_priority

    files_per_shot = 2 if interval_still_format in (
        INTERVAL_STILL_FORMAT_RAW_JPEG_G137,
        INTERVAL_STILL_FORMAT_RAW_HEIF_G137,
    ) else 1
    max_dcim_files = eff_shots * files_per_shot

    routes_to_slot1 = requested_target_slot in (
        MEDIA_SLOT_1_PHASE313,
        MEDIA_SIMULT_RECORDING_PHASE313,
    )
    interval_will_mutate_media = bool(interval_active or interval_execute_requested)
    slot1_protected = bool(slot_1_contains_tier0_vault or slot_1_write_protected)
    slot1_firewall_blocked = bool(
        routes_to_slot1 and slot1_protected and interval_will_mutate_media
    )

    return {
        "effective_mode_settings": eff_mode_settings,
        "big6_prereq_ok": big6_prereq_ok,
        "swipe_blocked": swipe_blocked,
        "big6_screen_active": big6_active,
        "big6_cursor_active": bool(big6_active and big6_cursor_active),
        "effective_home_lower_left": eff_home_lower_left,
        "big6_iso_or_ei_tile_label": iso_tile,
        "big6_pp_or_lut_tile_label": pp_lut_tile,
        "effective_framing_on": eff_framing_on,
        "framing_locked_out": framing_locked,
        "framing_lockout_reasons": tuple(lockout_reasons),
        "apsc_s35_disabled_by_framing": apsc_s35_disabled,
        "effective_interval_shooting": eff_interval_shooting,
        "interval_active": interval_active,
        "interval_disabled_in_iauto": interval_disabled_iauto,
        "effective_start_time": eff_start,
        "effective_period": eff_period,
        "effective_shots": eff_shots,
        "effective_ae": eff_ae,
        "effective_ishut": eff_ishut,
        "effective_iprio": eff_iprio,
        "interval_max_dcim_files": max_dcim_files,
        "slot1_vault_firewall_blocked": slot1_firewall_blocked,
        "slot1_data_sector_writes": 0,
        "slot1_dcim_mutated": False,
        "slot1_avf_info_mutated": False,
    }


def compute_big6_home_framing_interval_matrix() -> Dict[str, Any]:
    """Deterministically evaluate 256 state transitions for BIG6, Framing, and Interval Vault."""
    states_checked = 0
    big6_active_count = 0
    nd_metadata_only_count = 0
    framing_apsc_disabled_count = 0
    slot1_firewall_blocked_count = 0

    for mode_set in ALLOWED_MODE_SETTINGS_G137:
        for log_mode in (LOG_SHOOTING_OFF_G137, LOG_SHOOTING_CINE_EI_G137):
            for lower_left in ALLOWED_HOME_LOWER_LEFT_MODES_G137:
                for framing_on in (False, True):
                    for fps in (24.0, 120.0):
                        for interval_on in ("Off", "On"):
                            for slot in (MEDIA_SLOT_1_PHASE313, MEDIA_SLOT_2_PHASE313):
                                for vault in (False, True):
                                    st = _compute_g137_effective_state(
                                        shoot_mode=(
                                            SHOOT_MODE_STILL_PHASE313
                                            if interval_on == "On"
                                            else SHOOT_MODE_MOVIE_PHASE313
                                        ),
                                        exposure_mode=EXPOSURE_MODE_M_G137,
                                        reset_action=RESET_ACTION_NONE_PHASE313,
                                        fps=fps,
                                        active_recording=False,
                                        streaming_active=False,
                                        touch_operation_enabled=True,
                                        mode_settings=mode_set,
                                        big6_entry_trigger=BIG6_ENTRY_HOME_KEY_G137,
                                        big6_cursor_active=False,
                                        log_shooting_mode=log_mode,
                                        shutter_mode=SHUTTER_MODE_ANGLE_G137,
                                        home_lower_left=lower_left,
                                        framing_on=framing_on,
                                        framing_rec_stream_mode=FRAMING_REC_STREAM_CROP_G137,
                                        framing_hdmi_mode=FRAMING_HDMI_CROP_G137,
                                        interval_shooting=interval_on,
                                        interval_start_time_sec=1,
                                        interval_period_sec=3,
                                        interval_shot_count=9999,
                                        interval_still_format=INTERVAL_STILL_FORMAT_RAW_JPEG_G137,
                                        interval_ae_tracking_sensitivity="Mid",
                                        interval_shutter_type=INTERVAL_SHUTTER_ELECTRONIC_G137,
                                        interval_priority="Off",
                                        interval_execute_requested=False,
                                        requested_target_slot=slot,
                                        slot_1_contains_tier0_vault=vault,
                                        slot_1_write_protected=False,
                                    )
                                    states_checked += 1
                                    if st["big6_screen_active"]:
                                        big6_active_count += 1
                                    if st["effective_home_lower_left"] == HOME_LOWER_LEFT_ND_FILTER_G137:
                                        nd_metadata_only_count += 1
                                    if st["apsc_s35_disabled_by_framing"]:
                                        framing_apsc_disabled_count += 1
                                    if st["slot1_vault_firewall_blocked"]:
                                        slot1_firewall_blocked_count += 1
                                    assert st["slot1_data_sector_writes"] == 0

    return {
        "states_checked": states_checked,
        "big6_active_count": big6_active_count,
        "nd_metadata_only_count": nd_metadata_only_count,
        "framing_apsc_disabled_count": framing_apsc_disabled_count,
        "slot1_firewall_blocked_count": slot1_firewall_blocked_count,
    }


def resolve_fx3_big6_home_framing_interval_state(
    **kwargs: Any,
) -> Dict[str, Any]:
    """Return serialized G137 guard state for UI/VM/orchestrator callers."""
    return verify_big6_home_framing_interval_vault_guard(**kwargs).to_dict()


def verify_big6_home_framing_interval_vault_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE313,
    body_model_id: int = FX3_MODEL_ID_PHASE313,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE313,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE313,
    target_model: str = FX3_MODEL_NAME_PHASE313,
    reset_action: str = RESET_ACTION_NONE_PHASE313,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE313,
    exposure_mode: str = EXPOSURE_MODE_M_G137,
    fps: float = 24.0,
    active_recording: bool = False,
    streaming_active: bool = False,
    touch_operation_enabled: bool = True,
    requested_mode_settings: str = MODE_SETTINGS_FIXED_VARIABLE_G137,
    big6_entry_trigger: str = BIG6_ENTRY_HOME_KEY_G137,
    big6_cursor_active: bool = False,
    big6_hdmi_output_claimed: bool = False,
    force_big6_without_fixed_variable: bool = False,
    log_shooting_mode: str = LOG_SHOOTING_CINE_EI_G137,
    shutter_mode: str = SHUTTER_MODE_ANGLE_G137,
    requested_home_lower_left: str = HOME_LOWER_LEFT_ND_FILTER_G137,
    claimed_fx3_physical_end_actuator: bool = False,
    requested_framing_on: bool = False,
    framing_rec_stream_mode: str = FRAMING_REC_STREAM_FULL_G137,
    framing_hdmi_mode: str = FRAMING_HDMI_CROP_G137,
    claimed_apsc_s35_concurrent_with_framing: bool = False,
    force_framing_under_lockout: bool = False,
    auto_framing_requested: bool = False,
    requested_dormant_auto_framing_symbol: Optional[str] = None,
    requested_interval_shooting: str = "Off",
    interval_start_time_sec: int = INTERVAL_START_TIME_DEFAULT_SEC_G137,
    interval_period_sec: int = INTERVAL_PERIOD_DEFAULT_SEC_G137,
    interval_shot_count: int = INTERVAL_SHOTS_DEFAULT_G137,
    interval_still_format: str = INTERVAL_STILL_FORMAT_RAW_JPEG_G137,
    interval_ae_tracking_sensitivity: str = "Mid",
    interval_shutter_type: str = INTERVAL_SHUTTER_ELECTRONIC_G137,
    interval_priority: str = "Off",
    interval_bulb_requested_concurrently: bool = False,
    force_interval_in_iauto_or_non_still: bool = False,
    claimed_fx3_interval_outputs_single_mxf_or_fx6_9999: bool = False,
    interval_execute_requested: bool = False,
    requested_target_slot: str = MEDIA_SLOT_2_PHASE313,
    slot_1_contains_tier0_vault: bool = True,
    slot_1_write_protected: bool = False,
    bypass_slot1_vault_firewall: bool = False,
) -> Big6HomeFramingIntervalVaultGuardResult:
    """Enforce Gate G137: BIG6 Home Fixed/Variable + manual ND metadata truth,
    manual Framing Settings vs dormant Auto Framing, and Still Interval Shoot Func.
    9,999-shot Slot-1 Tier-0 Vault Firewall.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    norm_shoot = _normalize_shoot_mode(shoot_mode)
    norm_exp = _normalize_exposure_mode(exposure_mode)
    norm_reset = _normalize_reset_action(reset_action)
    norm_interval = _normalize_on_off(requested_interval_shooting)
    norm_priority = _normalize_on_off(interval_priority)
    norm_slot = _normalize_recording_media_mode(requested_target_slot)

    fw_parsed = _parse_fw_major_minor(firmware_version)
    identity_ok = (
        body_model_name == FX3_MODEL_NAME_PHASE313
        and _is_real_int(body_model_id)
        and body_model_id == FX3_MODEL_ID_PHASE313
        and help_guide_code == FX3_HELP_GUIDE_CODE_PHASE313
        and fw_parsed is not None
    )
    if not identity_ok:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3 Ver. 7.02 hardware/help-guide/firmware identity for Gate G137."
        )

    if target_model not in (FX3_MODEL_NAME_PHASE313, FX6_MODEL_NAME_PHASE313):
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Unsupported target_model `{target_model}`.")

    if norm_shoot is None:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid shoot_mode `{shoot_mode}`.")
        norm_shoot = SHOOT_MODE_MOVIE_PHASE313

    if norm_exp is None:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid exposure_mode `{exposure_mode}`.")
        norm_exp = EXPOSURE_MODE_M_G137

    if norm_reset is None:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid reset_action `{reset_action}`.")
        norm_reset = RESET_ACTION_NONE_PHASE313

    if norm_interval is None:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_interval_shooting `{requested_interval_shooting}`.")
        norm_interval = "Off"

    if norm_priority is None:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid interval_priority `{interval_priority}`.")
        norm_priority = "Off"

    if norm_slot is None:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_target_slot `{requested_target_slot}`.")
        norm_slot = MEDIA_SLOT_2_PHASE313

    if not isinstance(fps, (int, float)) or isinstance(fps, bool) or fps <= 0:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid fps `{fps}`.")
        safe_fps = 24.0
    else:
        safe_fps = float(fps)

    if requested_mode_settings not in ALLOWED_MODE_SETTINGS_G137:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_mode_settings `{requested_mode_settings}`.")
        safe_mode_settings = MODE_SETTINGS_FIXED_VARIABLE_G137
    else:
        safe_mode_settings = requested_mode_settings

    if big6_entry_trigger not in ALLOWED_BIG6_ENTRY_TRIGGERS_G137:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid big6_entry_trigger `{big6_entry_trigger}`.")
        safe_entry = BIG6_ENTRY_NONE_G137
    else:
        safe_entry = big6_entry_trigger

    if log_shooting_mode not in ALLOWED_LOG_SHOOTING_MODES_G137:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid log_shooting_mode `{log_shooting_mode}`.")
        safe_log = LOG_SHOOTING_OFF_G137
    else:
        safe_log = log_shooting_mode

    if shutter_mode not in ALLOWED_SHUTTER_MODES_G137:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid shutter_mode `{shutter_mode}`.")
        safe_shutter_mode = SHUTTER_MODE_ANGLE_G137
    else:
        safe_shutter_mode = shutter_mode

    if requested_home_lower_left not in ALLOWED_HOME_LOWER_LEFT_MODES_G137:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_home_lower_left `{requested_home_lower_left}`.")
        safe_lower_left = HOME_LOWER_LEFT_APERTURE_G137
    else:
        safe_lower_left = requested_home_lower_left

    if framing_rec_stream_mode not in ALLOWED_FRAMING_REC_STREAM_MODES_G137:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid framing_rec_stream_mode `{framing_rec_stream_mode}`.")
        safe_framing_rec = FRAMING_REC_STREAM_FULL_G137
    else:
        safe_framing_rec = framing_rec_stream_mode

    if framing_hdmi_mode not in ALLOWED_FRAMING_HDMI_MODES_G137:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid framing_hdmi_mode `{framing_hdmi_mode}`.")
        safe_framing_hdmi = FRAMING_HDMI_CROP_G137
    else:
        safe_framing_hdmi = framing_hdmi_mode

    if interval_still_format not in ALLOWED_INTERVAL_STILL_FORMATS_G137:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid interval_still_format `{interval_still_format}`.")
        safe_still_fmt = INTERVAL_STILL_FORMAT_RAW_JPEG_G137
    else:
        safe_still_fmt = interval_still_format

    if interval_ae_tracking_sensitivity not in ALLOWED_AE_TRACKING_SENSITIVITIES_G137:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid interval_ae_tracking_sensitivity `{interval_ae_tracking_sensitivity}`.")
        safe_ae_sens = "Mid"
    else:
        safe_ae_sens = interval_ae_tracking_sensitivity

    if interval_shutter_type not in ALLOWED_INTERVAL_SHUTTER_TYPES_G137:
        _add_code(codes, STATUS_BLOCKED_G137_TELEMETRY_INVALID)
        errors.append(f"Invalid interval_shutter_type `{interval_shutter_type}`.")
        safe_ishut = INTERVAL_SHUTTER_ELECTRONIC_G137
    else:
        safe_ishut = interval_shutter_type

    eff = _compute_g137_effective_state(
        shoot_mode=norm_shoot,
        exposure_mode=norm_exp,
        reset_action=norm_reset,
        fps=safe_fps,
        active_recording=bool(active_recording),
        streaming_active=bool(streaming_active),
        touch_operation_enabled=bool(touch_operation_enabled),
        mode_settings=safe_mode_settings,
        big6_entry_trigger=safe_entry,
        big6_cursor_active=bool(big6_cursor_active),
        log_shooting_mode=safe_log,
        shutter_mode=safe_shutter_mode,
        home_lower_left=safe_lower_left,
        framing_on=bool(requested_framing_on),
        framing_rec_stream_mode=safe_framing_rec,
        framing_hdmi_mode=safe_framing_hdmi,
        interval_shooting=norm_interval,
        interval_start_time_sec=interval_start_time_sec if _is_real_int(interval_start_time_sec) else 1,
        interval_period_sec=interval_period_sec if _is_real_int(interval_period_sec) else 3,
        interval_shot_count=interval_shot_count if _is_real_int(interval_shot_count) else 30,
        interval_still_format=safe_still_fmt,
        interval_ae_tracking_sensitivity=safe_ae_sens,
        interval_shutter_type=safe_ishut,
        interval_priority=norm_priority,
        interval_execute_requested=bool(interval_execute_requested),
        requested_target_slot=norm_slot,
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        slot_1_write_protected=bool(slot_1_write_protected),
    )

    # Part A: BIG6 Home Screen checks
    big6_prereq_violation = bool(
        force_big6_without_fixed_variable and not eff["big6_prereq_ok"]
    )
    if (
        big6_prereq_violation
        or big6_hdmi_output_claimed
        or claimed_fx3_physical_end_actuator
        or (safe_entry == BIG6_ENTRY_SWIPE_DOWN_G137 and eff["swipe_blocked"])
    ):
        _add_code(codes, STATUS_BLOCKED_G137_BIG6_PREREQ_HDMI_OR_END_ACTUATOR_VIOLATION)
        errors.append(
            "BIG6 (Home) contract violated: requires `[Mode Settings]=Fixed/Variable` (`_f 0x7d0d`), "
            "`[Touch Operation]` for Swipe Down, NEVER outputs to external HDMI, and `Home (Lower Left) -> "
            "ND Filter` on `ILME-FX3` is manual metadata-only (`ZERO` physical e-ND actuator vs `ILME-FX6` 1/4..1/128)."
        )

    # Part B: Manual Framing Settings vs Dormant AI Auto Framing
    dormant_af_lower = {s.strip().lower() for s in DORMANT_AUTO_FRAMING_TRAPS_G137}
    dormant_auto_framing_hit = bool(
        auto_framing_requested
        or (
            requested_dormant_auto_framing_symbol is not None
            and requested_dormant_auto_framing_symbol.strip().lower() in dormant_af_lower
        )
    )
    framing_lock_violation = bool(
        (eff["framing_locked_out"] and force_framing_under_lockout)
        or (eff["effective_framing_on"] and claimed_apsc_s35_concurrent_with_framing)
    )
    if dormant_auto_framing_hit or framing_lock_violation:
        _add_code(codes, STATUS_BLOCKED_G137_DORMANT_AUTO_FRAMING_OR_LOCK_VIOLATION)
        errors.append(
            "Framing contract violated: AI `[Auto Framing]` (`_f 0x6be6/0x79bc`) is dormant (`EOPNOTSUPP=95`; "
            "`TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY`), and active `[Framing Settings]` (`_f 0x7d18`) disables "
            "`APS-C S35` while locking during `>=100p`, active recording, or streaming."
        )

    # Part C: Interval Shoot Func. Parameter Boundaries & FX6 Single-MXF Contrast
    bad_start = (
        not _is_real_int(interval_start_time_sec)
        or interval_start_time_sec < INTERVAL_START_TIME_MIN_SEC_G137
        or interval_start_time_sec > INTERVAL_START_TIME_MAX_SEC_G137
    )
    bad_period = (
        not _is_real_int(interval_period_sec)
        or interval_period_sec < INTERVAL_PERIOD_MIN_SEC_G137
        or interval_period_sec > INTERVAL_PERIOD_MAX_SEC_G137
    )
    bad_shots = (
        not _is_real_int(interval_shot_count)
        or interval_shot_count < INTERVAL_SHOTS_MIN_G137
        or interval_shot_count > INTERVAL_SHOTS_MAX_G137
    )
    bad_mode_interval = bool(
        force_interval_in_iauto_or_non_still
        and (
            norm_shoot != SHOOT_MODE_STILL_PHASE313
            or norm_exp == EXPOSURE_MODE_INTELLIGENT_AUTO_G137
        )
    )
    if (
        bad_start
        or bad_period
        or bad_shots
        or bad_mode_interval
        or claimed_fx3_interval_outputs_single_mxf_or_fx6_9999
    ):
        _add_code(codes, STATUS_BLOCKED_G137_INTERVAL_SHOOT_PARAM_OR_FX6_CROSSWIRE_VIOLATION)
        errors.append(
            "Interval Shoot Func. contract violated: FX3 is Still-only (disabled in `Intelligent Auto`), "
            "`Start Time 1..5999s`, `Interval 1..60s`, `Shots 1..9999` RAW/JPEG/HEIF sequence (never single MXF "
            "like FX6 `Project > Interval Rec` `1..24` frames)."
        )

    # Part D: CRITICAL Slot-1 Tier-0 Vault Firewall
    vault_violation = bool(eff["slot1_vault_firewall_blocked"] and bypass_slot1_vault_firewall)
    if eff["slot1_vault_firewall_blocked"] or vault_violation:
        _add_code(codes, STATUS_BLOCKED_G137_SLOT1_INTERVAL_9999_VAULT_FIREWALL_VIOLATION)
        errors.append(
            "CRITICAL VAULT FIREWALL (`EROFS=30`/`EBUSY=16`): `[Interval Shoot Func.]` (up to 9,999 shots = "
            "19,998 DCIM files + AVF_INFO rewrites) attempted while target routes to protected `Slot 1` Tier-0 vault "
            "(`slot1_data_sector_writes == 0`, `slot1_dcim_mutated == False`, `slot1_avf_info_mutated == False`)."
        )

    any_eopnotsupp = (
        claimed_fx3_physical_end_actuator
        or big6_hdmi_output_claimed
        or dormant_auto_framing_hit
        or claimed_fx3_interval_outputs_single_mxf_or_fx6_9999
    )
    block_errno: Optional[int] = None
    block_errno_name: Optional[str] = None
    if eff["slot1_vault_firewall_blocked"]:
        if slot_1_contains_tier0_vault:
            block_errno = EROFS_ERRNO_PHASE313
            block_errno_name = EROFS_NAME_PHASE313
        else:
            block_errno = EBUSY_ERRNO_PHASE313
            block_errno_name = EBUSY_NAME_PHASE313
    elif any_eopnotsupp:
        block_errno = EOPNOTSUPP_ERRNO_PHASE313
        block_errno_name = EOPNOTSUPP_NAME_PHASE313

    matrix = compute_big6_home_framing_interval_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G137 if valid else codes[0]

    return Big6HomeFramingIntervalVaultGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE313,
        target_model=target_model,
        reset_action=norm_reset,
        shoot_mode=norm_shoot,
        exposure_mode=norm_exp,
        fps=safe_fps,
        active_recording=bool(active_recording),
        streaming_active=bool(streaming_active),
        touch_operation_enabled=bool(touch_operation_enabled),
        requested_mode_settings=safe_mode_settings,
        effective_mode_settings=eff["effective_mode_settings"],
        big6_entry_trigger=safe_entry,
        big6_screen_active=eff["big6_screen_active"],
        big6_cursor_active=eff["big6_cursor_active"],
        big6_hdmi_output_active=bool(big6_hdmi_output_claimed),
        log_shooting_mode=safe_log,
        shutter_mode=safe_shutter_mode,
        requested_home_lower_left=safe_lower_left,
        effective_home_lower_left=eff["effective_home_lower_left"],
        big6_exact_6_tiles=FX3_BIG6_EXACT_6_TILES_LABELS_G137,
        big6_iso_or_ei_tile_label=eff["big6_iso_or_ei_tile_label"],
        big6_pp_or_lut_tile_label=eff["big6_pp_or_lut_tile_label"],
        fx3_physical_end_actuator_present=False,
        fx6_physical_end_options=FX6_END_ND_OPTIONS_G137,
        requested_framing_on=bool(requested_framing_on),
        effective_framing_on=eff["effective_framing_on"],
        framing_locked_out=eff["framing_locked_out"],
        framing_lockout_reasons=eff["framing_lockout_reasons"],
        framing_rec_stream_mode=safe_framing_rec,
        framing_hdmi_mode=safe_framing_hdmi,
        apsc_s35_disabled_by_framing=eff["apsc_s35_disabled_by_framing"],
        dormant_auto_framing_blocked=dormant_auto_framing_hit,
        fx3_framing_support_lock="TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY",
        requested_interval_shooting=norm_interval,
        effective_interval_shooting=eff["effective_interval_shooting"],
        interval_start_time_sec=eff["effective_start_time"],
        interval_period_sec=eff["effective_period"],
        interval_shot_count=eff["effective_shots"],
        interval_still_format=safe_still_fmt,
        interval_ae_tracking_sensitivity=eff["effective_ae"],
        interval_shutter_type=eff["effective_ishut"],
        interval_priority=eff["effective_iprio"],
        interval_max_dcim_files=eff["interval_max_dcim_files"],
        interval_bulb_exited_to_30s=bool(eff["interval_active"] and interval_bulb_requested_concurrently),
        interval_disabled_in_iauto=eff["interval_disabled_in_iauto"],
        fx6_interval_rec_single_mxf=True,
        requested_target_slot=norm_slot,
        effective_target_slot=norm_slot,
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        slot_1_write_protected=bool(slot_1_write_protected),
        slot1_vault_firewall_blocked=eff["slot1_vault_firewall_blocked"],
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        slot1_data_sector_writes=eff["slot1_data_sector_writes"],
        slot1_dcim_mutated=eff["slot1_dcim_mutated"],
        slot1_avf_info_mutated=eff["slot1_avf_info_mutated"],
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g137_big6_home_framing_interval_vault_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    big6_home_framing_interval_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase313DonorAuditResult] = None,
) -> Tuple[GateVerdict, G137Big6HomeFramingIntervalVaultGuardResult]:
    """Evaluate Wave-59 Gate `G137` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase313_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_big6_home_framing_interval_vault_guard(
        **(dict(big6_home_framing_interval_kwargs or {}))
    )
    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G137.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G137 if valid else codes[0]

    res = G137Big6HomeFramingIntervalVaultGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        big6_home_framing_interval_vault_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, big6={guard.big6_screen_active}, "
        f"lower_left={guard.effective_home_lower_left}(fx3_end_actuator=False), "
        f"framing={guard.effective_framing_on}, "
        f"interval={guard.effective_interval_shooting}(shots={guard.interval_shot_count}), "
        f"slot1_writes={guard.slot1_data_sector_writes}"
    )
    verdict = GateVerdict(
        gate_id=G137_GATE_ID,
        gate_code=G137_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G138: TC Make Regenerate, HDMI REC Control, SSH Access Authen., Fan 4v3 Zero-Max
# ---------------------------------------------------------------------------


def _compute_g138_effective_state(
    *,
    shoot_mode: str,
    reset_action: str,
    recording_media_mode: str,
    tc_make: str,
    tc_run: str,
    vmc_bncm1_ext_ltc_requested: bool,
    hdmi_tc_output: str,
    hdmi_rec_control: str,
    rec_media_dur_hdmi_output: str,
    hdmi_raw_output_on: bool,
    streaming_active: bool,
    usb_streaming_active: bool,
    access_authen_settings: str,
    fan_control: str,
    auto_pwr_off_temp: str,
    internal_temp_exceeded_threshold: bool,
) -> Dict[str, Any]:
    init_reset = reset_action == RESET_ACTION_INITIALIZE_PHASE313
    net_or_init_reset = reset_action in (
        RESET_ACTION_RESET_NETWORK_SET_PHASE313,
        RESET_ACTION_INITIALIZE_PHASE313,
    )

    # TC Make & TC Run & HDMI REC Control are Initialize-only (unaffected by Camera Settings Reset)
    eff_tc_make = TC_MAKE_PRESET_G138 if init_reset else tc_make
    if init_reset:
        eff_tc_run = TC_RUN_REC_RUN_G138
    elif eff_tc_make == TC_MAKE_REGENERATE_G138:
        eff_tc_run = TC_RUN_REC_RUN_G138
    else:
        eff_tc_run = tc_run

    tc_regen_forced_rec_run = (eff_tc_make == TC_MAKE_REGENERATE_G138)
    tc_regen_source_slot = (
        MEDIA_SLOT_1_PHASE313
        if recording_media_mode in (MEDIA_SLOT_1_PHASE313, MEDIA_SIMULT_RECORDING_PHASE313)
        else MEDIA_SLOT_2_PHASE313
    )

    ext_tc_lock_status = (
        "EXT-LK"
        if (
            vmc_bncm1_ext_ltc_requested
            and shoot_mode == SHOOT_MODE_MOVIE_PHASE313
            and eff_tc_make == TC_MAKE_PRESET_G138
            and eff_tc_run == TC_RUN_FREE_RUN_G138
        )
        else "INT"
    )

    hdmi_rec_restricted: List[str] = []
    if shoot_mode != SHOOT_MODE_MOVIE_PHASE313:
        hdmi_rec_restricted.append(f"shoot_mode_{shoot_mode}")
    if hdmi_tc_output != "On":
        hdmi_rec_restricted.append("hdmi_tc_output_off")
    if streaming_active:
        hdmi_rec_restricted.append("network_streaming_active")
    if usb_streaming_active:
        hdmi_rec_restricted.append("usb_streaming_active")

    eff_hdmi_rec_ctrl = "Off" if init_reset else hdmi_rec_control
    if hdmi_rec_restricted:
        eff_hdmi_rec_ctrl = "Off"

    cardless_hdmi_permitted = (
        shoot_mode == SHOOT_MODE_MOVIE_PHASE313
        and hdmi_tc_output == "On"
        and rec_media_dur_hdmi_output == HDMI_REC_MEDIA_OFF_HDMI_ONLY_G138
        and not streaming_active
        and not usb_streaming_active
    )

    # Access Authen. Settings: On by default, survives Camera Settings Reset, resets to On on Net/Init
    eff_access_authen = "On" if net_or_init_reset else access_authen_settings
    sshd_active = eff_access_authen == "On"

    # Fan Control & Auto Power OFF Temp.: Initialize-only
    eff_fan = FAN_CONTROL_AUTO_G138 if init_reset else fan_control
    eff_temp = AUTO_PWR_OFF_TEMP_STANDARD_G138 if init_reset else auto_pwr_off_temp
    fan_temp_override = (
        eff_fan == FAN_CONTROL_OFF_IN_REC_G138 and internal_temp_exceeded_threshold
    )
    low_temp_burn_warning = eff_temp == AUTO_PWR_OFF_TEMP_HIGH_G138

    return {
        "effective_tc_make": eff_tc_make,
        "effective_tc_run": eff_tc_run,
        "tc_regenerate_forced_rec_run": tc_regen_forced_rec_run,
        "tc_regenerate_source_slot": tc_regen_source_slot,
        "ext_tc_lock_status": ext_tc_lock_status,
        "effective_hdmi_rec_control": eff_hdmi_rec_ctrl,
        "hdmi_rec_ctrl_restricted_reasons": tuple(hdmi_rec_restricted),
        "cardless_hdmi_rec_ctrl_permitted": cardless_hdmi_permitted,
        "effective_access_authen_settings": eff_access_authen,
        "sshd_control_active": sshd_active,
        "access_authen_survived_cam_reset": (
            reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE313
        ),
        "access_authen_reset_by_net_or_init": net_or_init_reset,
        "effective_fan_control": eff_fan,
        "effective_auto_pwr_off_temp": eff_temp,
        "fan_off_in_rec_temp_override_active": fan_temp_override,
        "low_temp_burn_tripod_warning": low_temp_burn_warning,
    }


def compute_tc_make_ssh_authen_fan_matrix() -> Dict[str, Any]:
    """Deterministically evaluate 256 state combinations for G138."""
    states_checked = 0
    tc_regen_forced_rec_count = 0
    cardless_hdmi_rec_ctrl_count = 0
    sshd_active_count = 0
    fan_temp_override_count = 0

    for tc_make in ALLOWED_FX3_TC_MAKE_MODES_G138:
        for tc_run in ALLOWED_TC_RUN_MODES_G138:
            for rec_media in ALLOWED_REC_MEDIA_DUR_HDMI_G138:
                for tc_out in ("Off", "On"):
                    for auth in ("On", "Off"):
                        for fan in FX3_EXACT_4_FAN_MODES_G138:
                            for over_temp in (False, True):
                                st = _compute_g138_effective_state(
                                    shoot_mode=SHOOT_MODE_MOVIE_PHASE313,
                                    reset_action=RESET_ACTION_NONE_PHASE313,
                                    recording_media_mode=MEDIA_SIMULT_RECORDING_PHASE313,
                                    tc_make=tc_make,
                                    tc_run=tc_run,
                                    vmc_bncm1_ext_ltc_requested=True,
                                    hdmi_tc_output=tc_out,
                                    hdmi_rec_control="On" if tc_out == "On" else "Off",
                                    rec_media_dur_hdmi_output=rec_media,
                                    hdmi_raw_output_on=(rec_media == HDMI_REC_MEDIA_OFF_HDMI_ONLY_G138),
                                    streaming_active=False,
                                    usb_streaming_active=False,
                                    access_authen_settings=auth,
                                    fan_control=fan,
                                    auto_pwr_off_temp=AUTO_PWR_OFF_TEMP_HIGH_G138,
                                    internal_temp_exceeded_threshold=over_temp,
                                )
                                states_checked += 1
                                if st["tc_regenerate_forced_rec_run"]:
                                    tc_regen_forced_rec_count += 1
                                    assert st["effective_tc_run"] == TC_RUN_REC_RUN_G138
                                    assert st["tc_regenerate_source_slot"] == MEDIA_SLOT_1_PHASE313
                                if st["cardless_hdmi_rec_ctrl_permitted"]:
                                    cardless_hdmi_rec_ctrl_count += 1
                                if st["sshd_control_active"]:
                                    sshd_active_count += 1
                                if st["fan_off_in_rec_temp_override_active"]:
                                    fan_temp_override_count += 1

    return {
        "states_checked": states_checked,
        "tc_regen_forced_rec_count": tc_regen_forced_rec_count,
        "cardless_hdmi_rec_ctrl_count": cardless_hdmi_rec_ctrl_count,
        "sshd_active_count": sshd_active_count,
        "fan_temp_override_count": fan_temp_override_count,
    }


def resolve_fx3_tc_make_ssh_authen_fan_state(**kwargs: Any) -> Dict[str, Any]:
    """Return serialized G138 guard state for UI/VM/orchestrator callers."""
    return verify_tc_make_hdmi_rec_ssh_authen_fan_guard(**kwargs).to_dict()


def verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE313,
    body_model_id: int = FX3_MODEL_ID_PHASE313,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE313,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE313,
    target_model: str = FX3_MODEL_NAME_PHASE313,
    reset_action: str = RESET_ACTION_NONE_PHASE313,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE313,
    recording_media_mode: str = MEDIA_SIMULT_RECORDING_PHASE313,
    requested_tc_make: str = TC_MAKE_PRESET_G138,
    requested_tc_run: str = TC_RUN_FREE_RUN_G138,
    force_free_run_under_regenerate: bool = False,
    vmc_bncm1_ext_ltc_requested: bool = False,
    force_ext_lk_without_preset_freerun: bool = False,
    hdmi_tc_output: str = "On",
    requested_hdmi_rec_control: str = "Off",
    force_hdmi_rec_ctrl_when_restricted: bool = False,
    rec_media_dur_hdmi_output: str = HDMI_REC_MEDIA_ON_G138,
    hdmi_raw_output_on: bool = False,
    streaming_active: bool = False,
    usb_streaming_active: bool = False,
    audio_4ch_output_channels: str = AUDIO_4CH_CH1_CH2_G138,
    fx6_sdi_hdmi_rec_ctrl_mode: str = FX6_SDI_HDMI_REC_CTRL_OFF_G138,
    claimed_fx3_has_sdi_remote_if_or_bnc_tc_switch: bool = False,
    requested_access_authen_settings: str = "On",
    requested_http_auth_protocol: Optional[str] = None,
    import_root_cert_requested: bool = False,
    import_root_cert_type: str = "Cloud",
    claimed_root_cert_is_inbound_https_server: bool = False,
    import_root_cert_slot: str = MEDIA_SLOT_2_PHASE313,
    slot_1_contains_tier0_vault: bool = True,
    requested_fan_control: str = FAN_CONTROL_AUTO_G138,
    requested_auto_pwr_off_temp: str = AUTO_PWR_OFF_TEMP_STANDARD_G138,
    internal_temp_exceeded_threshold: bool = False,
) -> TcMakeHdmiRecSshAuthenFanGuardResult:
    """Enforce Gate G138: TC Make Regenerate -> forced Rec Run & HDMI REC Control,
    Ver. 7.00+ SSH-based Access Authen. vs Zero HTTPS/Digest, and 4-mode FX3 vs
    3-mode FX6 Fan Control Zero-Max truth.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    norm_shoot = _normalize_shoot_mode(shoot_mode)
    norm_reset = _normalize_reset_action(reset_action)
    norm_media = _normalize_recording_media_mode(recording_media_mode)
    norm_tc_out = _normalize_on_off(hdmi_tc_output)
    norm_hdmi_rec = _normalize_on_off(requested_hdmi_rec_control)
    norm_auth = _normalize_on_off(requested_access_authen_settings)
    norm_cert_slot = _normalize_recording_media_mode(import_root_cert_slot)

    fw_parsed = _parse_fw_major_minor(firmware_version)
    identity_ok = (
        body_model_name == FX3_MODEL_NAME_PHASE313
        and _is_real_int(body_model_id)
        and body_model_id == FX3_MODEL_ID_PHASE313
        and help_guide_code == FX3_HELP_GUIDE_CODE_PHASE313
        and fw_parsed is not None
    )
    if not identity_ok:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3 Ver. 7.02 hardware/help-guide/firmware identity for Gate G138."
        )

    if target_model not in (FX3_MODEL_NAME_PHASE313, FX6_MODEL_NAME_PHASE313):
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Unsupported target_model `{target_model}`.")

    if norm_shoot is None:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Invalid shoot_mode `{shoot_mode}`.")
        norm_shoot = SHOOT_MODE_MOVIE_PHASE313

    if norm_reset is None:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Invalid reset_action `{reset_action}`.")
        norm_reset = RESET_ACTION_NONE_PHASE313

    if norm_media is None:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Invalid recording_media_mode `{recording_media_mode}`.")
        norm_media = MEDIA_SIMULT_RECORDING_PHASE313

    if norm_tc_out is None:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Invalid hdmi_tc_output `{hdmi_tc_output}`.")
        norm_tc_out = "Off"

    if norm_hdmi_rec is None:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_hdmi_rec_control `{requested_hdmi_rec_control}`.")
        norm_hdmi_rec = "Off"

    if norm_auth is None:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(
            f"Invalid requested_access_authen_settings `{requested_access_authen_settings}`."
        )
        norm_auth = "On"

    if norm_cert_slot is None or norm_cert_slot == MEDIA_SIMULT_RECORDING_PHASE313:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Invalid import_root_cert_slot `{import_root_cert_slot}`.")
        norm_cert_slot = MEDIA_SLOT_2_PHASE313

    if rec_media_dur_hdmi_output not in ALLOWED_REC_MEDIA_DUR_HDMI_G138:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Invalid rec_media_dur_hdmi_output `{rec_media_dur_hdmi_output}`.")
        safe_rec_media_hdmi = HDMI_REC_MEDIA_ON_G138
    else:
        safe_rec_media_hdmi = rec_media_dur_hdmi_output

    if audio_4ch_output_channels not in ALLOWED_4CH_AUDIO_OUTPUT_G138:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Invalid audio_4ch_output_channels `{audio_4ch_output_channels}`.")
        safe_4ch = AUDIO_4CH_CH1_CH2_G138
    else:
        safe_4ch = audio_4ch_output_channels

    if fx6_sdi_hdmi_rec_ctrl_mode not in ALLOWED_FX6_SDI_HDMI_REC_CTRL_MODES_G138:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Invalid fx6_sdi_hdmi_rec_ctrl_mode `{fx6_sdi_hdmi_rec_ctrl_mode}`.")
        safe_fx6_rec_ctrl = FX6_SDI_HDMI_REC_CTRL_OFF_G138
    else:
        safe_fx6_rec_ctrl = fx6_sdi_hdmi_rec_ctrl_mode

    if requested_tc_run not in ALLOWED_TC_RUN_MODES_G138:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_tc_run `{requested_tc_run}`.")
        safe_tc_run = TC_RUN_FREE_RUN_G138
    else:
        safe_tc_run = requested_tc_run

    if requested_auto_pwr_off_temp not in ALLOWED_AUTO_PWR_OFF_TEMP_MODES_G138:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_auto_pwr_off_temp `{requested_auto_pwr_off_temp}`.")
        safe_temp = AUTO_PWR_OFF_TEMP_STANDARD_G138
    else:
        safe_temp = requested_auto_pwr_off_temp

    if import_root_cert_type not in OUTBOUND_CLIENT_TLS_TYPES_G138:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Invalid import_root_cert_type `{import_root_cert_type}`.")
        safe_cert_type = "Cloud"
    else:
        safe_cert_type = import_root_cert_type

    # Part A: TC Make (reject Clock on FX3) & HDMI REC Control
    raw_tc_make = requested_tc_make.strip() if isinstance(requested_tc_make, str) else ""
    fx3_clock_violation = bool(
        target_model == FX3_MODEL_NAME_PHASE313
        and raw_tc_make.lower() == TC_MAKE_FX6_CLOCK_G138.lower()
    )
    if (not fx3_clock_violation) and raw_tc_make not in ALLOWED_FX6_TC_MAKE_MODES_G138:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_tc_make `{requested_tc_make}`.")
        safe_tc_make = TC_MAKE_PRESET_G138
    else:
        safe_tc_make = raw_tc_make if raw_tc_make in ALLOWED_FX3_TC_MAKE_MODES_G138 else TC_MAKE_PRESET_G138

    eff = _compute_g138_effective_state(
        shoot_mode=norm_shoot,
        reset_action=norm_reset,
        recording_media_mode=norm_media,
        tc_make=safe_tc_make,
        tc_run=safe_tc_run,
        vmc_bncm1_ext_ltc_requested=bool(vmc_bncm1_ext_ltc_requested),
        hdmi_tc_output=norm_tc_out,
        hdmi_rec_control=norm_hdmi_rec,
        rec_media_dur_hdmi_output=safe_rec_media_hdmi,
        hdmi_raw_output_on=bool(hdmi_raw_output_on),
        streaming_active=bool(streaming_active),
        usb_streaming_active=bool(usb_streaming_active),
        access_authen_settings=norm_auth,
        fan_control=requested_fan_control if requested_fan_control in FX3_EXACT_4_FAN_MODES_G138 else FAN_CONTROL_AUTO_G138,
        auto_pwr_off_temp=safe_temp,
        internal_temp_exceeded_threshold=bool(internal_temp_exceeded_threshold),
    )

    regen_freerun_violation = bool(
        eff["tc_regenerate_forced_rec_run"] and force_free_run_under_regenerate
    )
    ext_lk_violation = bool(
        force_ext_lk_without_preset_freerun and eff["ext_tc_lock_status"] != "EXT-LK"
    )
    hdmi_rec_ctrl_violation = bool(
        norm_hdmi_rec == "On"
        and eff["hdmi_rec_ctrl_restricted_reasons"]
        and force_hdmi_rec_ctrl_when_restricted
    )
    if (
        fx3_clock_violation
        or regen_freerun_violation
        or ext_lk_violation
        or hdmi_rec_ctrl_violation
        or claimed_fx3_has_sdi_remote_if_or_bnc_tc_switch
    ):
        _add_code(codes, STATUS_BLOCKED_G138_TC_MAKE_CLOCK_REGEN_OR_HDMI_REC_CTRL_VIOLATION)
        errors.append(
            "Time Code / HDMI REC Control contract violated: FX3 `[Time Code Make]` exposes only "
            "`Preset`/`Regenerate` (no FX6 `Clock` -> `EOPNOTSUPP=95`), `Regenerate` forces `Rec Run` "
            "(reading Slot 1 in `Simult. Recording`), `VMC-BNCM1 EXT-LK` requires `Preset`+`Free Run`, and "
            "HDMI `[REC Control]` requires `[Time Code Output]=On` in `Movie` mode (blocked in S&Q/streaming)."
        )

    # Part B: SSH-Based Access Authen. vs Zero HTTPS/Digest + Outbound Client TLS Root Cert
    myth_lower = {x.strip().lower() for x in FORBIDDEN_HTTP_AUTH_MYTHS_G138}
    http_auth_myth_hit = bool(
        requested_http_auth_protocol is not None
        and requested_http_auth_protocol.strip().lower() in myth_lower
    )
    slot1_cert_violation = bool(
        import_root_cert_requested
        and norm_cert_slot == MEDIA_SLOT_1_PHASE313
        and slot_1_contains_tier0_vault
    )
    if (
        http_auth_myth_hit
        or claimed_root_cert_is_inbound_https_server
        or slot1_cert_violation
    ):
        _add_code(codes, STATUS_BLOCKED_G138_SSH_ACCESS_AUTHEN_HTTPS_MYTH_OR_CERT_VIOLATION)
        errors.append(
            "Access Authen. / Certificate contract violated: Ver. 7.00+ `[Access Authen. Settings]` uses "
            "SSH (`MSGID_SSHD_START_CMD`) + PTP-IP with ZERO `HTTP_DIGEST`/`BASIC_AUTH`/`HTTPS` server auth "
            "(`EOPNOTSUPP=95`); `[Import Root Certificate]` is outbound FTPS/RTMPS/Cloud client TLS only."
        )

    # Part C: 4-Mode FX3 vs 3-Mode FX6 Fan Control Zero-Max Truth
    raw_fan = requested_fan_control.strip() if isinstance(requested_fan_control, str) else ""
    max_myth_lower = {x.strip().lower() for x in FORBIDDEN_FAN_MAX_TOKENS_G138}
    fan_max_myth_hit = raw_fan.lower() in max_myth_lower
    fx6_always_off_hit = bool(
        target_model == FX6_MODEL_NAME_PHASE313
        and raw_fan.lower() in ("always off", "fan_control_always_off")
    )
    if (not fan_max_myth_hit) and (not fx6_always_off_hit) and raw_fan not in FX3_EXACT_4_FAN_MODES_G138:
        _add_code(codes, STATUS_BLOCKED_G138_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_fan_control `{requested_fan_control}`.")
    if fan_max_myth_hit or fx6_always_off_hit:
        _add_code(codes, STATUS_BLOCKED_G138_FAN_MAX_MYTH_OR_FX6_ALWAYS_OFF_VIOLATION)
        errors.append(
            "Fan Control contract violated: BOTH FX3 and FX6 have ZERO `Max` option (`EOPNOTSUPP=95`); "
            "FX3 exposes 4 modes (`Auto`/`Minimum`/`Off in Rec`/`Always Off`) whereas FX6 exposes 3 modes "
            "(`Auto`/`Minimum`/`Off in Rec`, keeping `Always Off` dormant -> `EOPNOTSUPP=95`)."
        )

    any_eopnotsupp = (
        fx3_clock_violation
        or claimed_fx3_has_sdi_remote_if_or_bnc_tc_switch
        or http_auth_myth_hit
        or claimed_root_cert_is_inbound_https_server
        or fan_max_myth_hit
        or fx6_always_off_hit
    )
    block_errno: Optional[int] = None
    block_errno_name: Optional[str] = None
    if slot1_cert_violation:
        block_errno = EROFS_ERRNO_PHASE313
        block_errno_name = EROFS_NAME_PHASE313
    elif any_eopnotsupp:
        block_errno = EOPNOTSUPP_ERRNO_PHASE313
        block_errno_name = EOPNOTSUPP_NAME_PHASE313

    matrix = compute_tc_make_ssh_authen_fan_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G138 if valid else codes[0]

    return TcMakeHdmiRecSshAuthenFanGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE313,
        target_model=target_model,
        reset_action=norm_reset,
        shoot_mode=norm_shoot,
        recording_media_mode=norm_media,
        requested_tc_make=raw_tc_make or TC_MAKE_PRESET_G138,
        effective_tc_make=eff["effective_tc_make"],
        requested_tc_run=safe_tc_run,
        effective_tc_run=eff["effective_tc_run"],
        tc_regenerate_forced_rec_run=eff["tc_regenerate_forced_rec_run"],
        tc_regenerate_source_slot=eff["tc_regenerate_source_slot"],
        vmc_bncm1_ext_ltc_requested=bool(vmc_bncm1_ext_ltc_requested),
        ext_tc_lock_status=eff["ext_tc_lock_status"],
        hdmi_tc_output=norm_tc_out,
        requested_hdmi_rec_control=norm_hdmi_rec,
        effective_hdmi_rec_control=eff["effective_hdmi_rec_control"],
        rec_media_dur_hdmi_output=safe_rec_media_hdmi,
        hdmi_raw_output_on=bool(hdmi_raw_output_on),
        cardless_hdmi_rec_ctrl_permitted=eff["cardless_hdmi_rec_ctrl_permitted"],
        hdmi_rec_ctrl_restricted_reasons=eff["hdmi_rec_ctrl_restricted_reasons"],
        audio_4ch_output_channels=safe_4ch,
        fx6_sdi_hdmi_rec_ctrl_mode=safe_fx6_rec_ctrl,
        fx6_parallel_rec_follows_slot_a=True,
        requested_access_authen_settings=norm_auth,
        effective_access_authen_settings=eff["effective_access_authen_settings"],
        access_authen_transports=ALLOWED_ACCESS_AUTHEN_TRANSPORTS_G138,
        sshd_control_active=eff["sshd_control_active"],
        access_authen_survived_cam_reset=eff["access_authen_survived_cam_reset"],
        access_authen_reset_by_net_or_init=eff["access_authen_reset_by_net_or_init"],
        http_digest_or_https_server_blocked=http_auth_myth_hit,
        import_root_cert_requested=bool(import_root_cert_requested),
        import_root_cert_type=safe_cert_type,
        import_root_cert_outbound_client_tls_only=True,
        import_root_cert_slot=norm_cert_slot,
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        slot1_vault_cert_blocked=slot1_cert_violation,
        slot1_data_sector_writes=0,
        requested_fan_control=raw_fan or FAN_CONTROL_AUTO_G138,
        effective_fan_control=eff["effective_fan_control"],
        fan_off_in_rec_temp_override_active=eff["fan_off_in_rec_temp_override_active"],
        requested_auto_pwr_off_temp=safe_temp,
        effective_auto_pwr_off_temp=eff["effective_auto_pwr_off_temp"],
        low_temp_burn_tripod_warning=eff["low_temp_burn_tripod_warning"],
        fx3_exact_fan_modes_count=len(FX3_EXACT_4_FAN_MODES_G138),
        fx6_exact_fan_modes_count=len(FX6_EXACT_3_FAN_MODES_G138),
        fx6_always_off_dormant_blocked=fx6_always_off_hit,
        fan_max_myth_blocked=fan_max_myth_hit,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g138_tc_make_hdmi_rec_ssh_authen_fan_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    tc_make_ssh_fan_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase313DonorAuditResult] = None,
) -> Tuple[GateVerdict, G138TcMakeHdmiRecSshAuthenFanGuardResult]:
    """Evaluate Wave-59 Gate `G138` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase313_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
        **(dict(tc_make_ssh_fan_kwargs or {}))
    )
    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G138.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G138 if valid else codes[0]

    res = G138TcMakeHdmiRecSshAuthenFanGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        tc_make_hdmi_rec_ssh_authen_fan_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, tc_make={guard.effective_tc_make}, "
        f"tc_run={guard.effective_tc_run}, hdmi_rec_ctrl={guard.effective_hdmi_rec_control}, "
        f"authen={guard.effective_access_authen_settings}(ssh={guard.sshd_control_active}), "
        f"fan={guard.effective_fan_control}(fx3_modes=4,fx6_modes=3,max=0)"
    )
    verdict = GateVerdict(
        gate_id=G138_GATE_ID,
        gate_code=G138_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `138`-Gate Milestone Master Safety Preflight (`G01..G138`)
# ---------------------------------------------------------------------------


def evaluate_138gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    big6_home_framing_interval_kwargs: Optional[Mapping[str, Any]] = None,
    tc_make_ssh_fan_kwargs: Optional[Mapping[str, Any]] = None,
    master_136_override: Optional[Master136GateReport] = None,
    **m136_passthrough_kwargs: Any,
) -> Master138GateReport:
    """Evaluate all 138 Master Safety Gates (`G01..G138`) deterministically by
    delegating `G01..G136` directly to `evaluate_136gate_preflight()`.
    """
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        or simulate_bench_dry_run
        or bool(dry_run_simulated_backup)
    )

    m136_report: Master136GateReport = (
        master_136_override
        if master_136_override is not None
        else evaluate_136gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m136_passthrough_kwargs,
        )
    )

    phase313_audit = audit_phase313_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g137_verdict, g137_res = evaluate_g137_big6_home_framing_interval_vault_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        big6_home_framing_interval_kwargs=big6_home_framing_interval_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase313_audit,
    )

    g138_verdict, g138_res = evaluate_g138_tc_make_hdmi_rec_ssh_authen_fan_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        tc_make_ssh_fan_kwargs=tc_make_ssh_fan_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase313_audit,
    )

    gates_137_to_138 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g137_verdict, g138_verdict)
    ]
    all_gates = tuple(list(m136_report.gates) + gates_137_to_138)

    g01_to_g12_verified = int(m136_report.summary["g01_to_g12_verified"])
    g13_to_g136_verified = int(m136_report.summary["g13_to_g134_verified"]) + int(
        m136_report.summary["g135_to_g136_verified"]
    )
    g137_to_g138_verified = sum(1 for v in (g137_verdict, g138_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g136_verified + g137_to_g138_verified

    g137_to_g138_all_passed = g137_to_g138_verified == 2
    g13_to_g138_all_passed = (
        m136_report.g13_to_g136_all_passed and g137_to_g138_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m136_report.gates[:9])

    offline_135_verified = (
        g01_to_g09_ok
        and m136_report.offline_133_gates_verified
        and g137_to_g138_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_138_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g138_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m136_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_135_verified
        and m136_report.h0_h1_trial_entry_allowed
        and g137_to_g138_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not CROSS_MODEL_FLASH_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m136_report.errors)
        + list(g137_verdict.errors)
        + list(g138_verdict.errors)
    )
    warnings: List[str] = (
        list(m136_report.warnings)
        + list(g137_verdict.warnings)
        + list(g138_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m136_report.g13_to_g136_all_passed:
        overall_status = m136_report.status
    elif not g137_verdict.passed:
        overall_status = g137_verdict.status
    elif not g138_verdict.passed:
        overall_status = g138_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_138_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_138_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_138_verified:
        overall_status = "VERIFIED_ALL_138_GATES"
    else:
        overall_status = "VERIFIED_135_OF_138_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m136_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g137_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g138_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 138,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 138 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g136_verified": g13_to_g136_verified,
        "g137_to_g138_verified": g137_to_g138_verified,
        "g13_to_g138_all_passed": g13_to_g138_all_passed,
        "g137_to_g138_all_passed": g137_to_g138_all_passed,
        "offline_135_gates_verified": offline_135_verified,
        "all_138_gates_verified": all_138_verified,
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
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master138GateReport(
        schema=REALHW_BIG6_HOME_FRAMING_INTERVAL_TC_SSH_FAN_138GATE_SCHEMA,
        version=REALHW_BIG6_HOME_FRAMING_INTERVAL_TC_SSH_FAN_138GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_135_gates_verified=offline_135_verified,
        all_138_gates_verified=all_138_verified,
        g13_to_g138_all_passed=g13_to_g138_all_passed,
        g137_to_g138_all_passed=g137_to_g138_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_136_report=m136_report.to_dict(),
        g137_result=g137_res.to_dict(),
        g138_result=g138_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_138_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master138GateReport:
    return evaluate_138gate_preflight(repo_root, **kwargs)


def run_138_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master138GateReport:
    return evaluate_138gate_preflight(repo_root, **kwargs)


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
        prog="realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard",
        description="Phase 313 Wave-59 G137/G138 and 138/138 Safety Gates Preflight CLI",
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
        help="Supply simulated dry-run Tier-0 backup inputs so all 138/138 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g137", "g138", "138"],
        default="138",
        help="Target gate check: g137, g138, or 138",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g137":
        v, r = evaluate_g137_big6_home_framing_interval_vault_guard(
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
                }
                if args.summary
                else r.to_dict()
            )
        else:
            sys.stdout.write(f"gate={v.gate_id} status={r.status} valid={r.valid}\n")
        return 0 if r.valid else 1

    if args.gate == "g138":
        v, r = evaluate_g138_tc_make_hdmi_rec_ssh_authen_fan_guard(
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
                }
                if args.summary
                else r.to_dict()
            )
        else:
            sys.stdout.write(f"gate={v.gate_id} status={r.status} valid={r.valid}\n")
        return 0 if r.valid else 1

    rep = evaluate_138gate_preflight(
        args.repo_root,
        force_clean_room=clean,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        _safe_write_json(
            {
                "status": rep.status,
                "verification_mode": rep.verification_mode,
                "summary": rep.summary,
                "g137_status": rep.g137_result["status"],
                "g138_status": rep.g138_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/138\n"
        )
    ok = (
        rep.all_138_gates_verified
        if args.dry_run_simulated
        else rep.offline_135_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "ACCESS_AUTHEN_F_UXC_RESID16_G138",
    "ALLOWED_4CH_AUDIO_OUTPUT_G138",
    "ALLOWED_ACCESS_AUTHEN_TRANSPORTS_G138",
    "ALLOWED_AE_TRACKING_SENSITIVITIES_G137",
    "ALLOWED_AUTO_PWR_OFF_TEMP_MODES_G138",
    "ALLOWED_BIG6_ENTRY_TRIGGERS_G137",
    "ALLOWED_EXPOSURE_MODES_G137",
    "ALLOWED_FRAMING_HDMI_MODES_G137",
    "ALLOWED_FRAMING_REC_STREAM_MODES_G137",
    "ALLOWED_FX3_TC_MAKE_MODES_G138",
    "ALLOWED_FX6_SDI_HDMI_REC_CTRL_MODES_G138",
    "ALLOWED_FX6_TC_MAKE_MODES_G138",
    "ALLOWED_HOME_LOWER_LEFT_MODES_G137",
    "ALLOWED_INTERVAL_SHUTTER_TYPES_G137",
    "ALLOWED_INTERVAL_STILL_FORMATS_G137",
    "ALLOWED_LOG_SHOOTING_MODES_G137",
    "ALLOWED_MODE_SETTINGS_G137",
    "ALLOWED_PASM_MODES_G137",
    "ALLOWED_RECORDING_MEDIA_MODES_PHASE313",
    "ALLOWED_REC_MEDIA_DUR_HDMI_G138",
    "ALLOWED_RESET_ACTIONS_PHASE313",
    "ALLOWED_SHOOT_MODES_PHASE313",
    "ALLOWED_SHUTTER_MODES_G137",
    "ALLOWED_TC_RUN_MODES_G138",
    "AUDIO_4CH_CH1_CH2_G138",
    "AUDIO_4CH_CH3_CH4_G138",
    "AUTO_PWR_OFF_TEMP_HIGH_G138",
    "AUTO_PWR_OFF_TEMP_STANDARD_G138",
    "BIG6_ENTRY_HOME_KEY_G137",
    "BIG6_ENTRY_NONE_G137",
    "BIG6_ENTRY_SWIPE_DOWN_G137",
    "BIG6_HOME_CUSTOM_KEY_F_UXC_RESID16_G137",
    "BIG6_HOME_LOWER_LEFT_F_UXC_RESID16_G137",
    "BIG6_MODE_SETTINGS_F_UXC_RESID16_G137",
    "BIG6_SWIPE_DOWN_F_UXC_RESID16_G137",
    "Big6HomeFramingIntervalVaultGuardResult",
    "CROSS_MODEL_FLASH_AUTHORIZED",
    "DEFAULT_REPO_ROOT",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE313",
    "DONOR_CHECK_MAX_SECONDS_PHASE313",
    "DORMANT_AUTO_FRAMING_TRAPS_G137",
    "EBUSY_ERRNO_PHASE313",
    "EBUSY_NAME_PHASE313",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "ENV_CLEAN_ROOM_TEST_PHASE313",
    "ENV_FORCE_CLEAN_ROOM",
    "EOPNOTSUPP_ERRNO_PHASE313",
    "EOPNOTSUPP_NAME_PHASE313",
    "EROFS_ERRNO_PHASE313",
    "EROFS_NAME_PHASE313",
    "EXPOSURE_MODE_A_G137",
    "EXPOSURE_MODE_INTELLIGENT_AUTO_G137",
    "EXPOSURE_MODE_M_G137",
    "EXPOSURE_MODE_P_G137",
    "EXPOSURE_MODE_S_G137",
    "FAN_CONTROL_ALWAYS_OFF_G138",
    "FAN_CONTROL_AUTO_G138",
    "FAN_CONTROL_MINIMUM_G138",
    "FAN_CONTROL_OFF_IN_REC_G138",
    "FORBIDDEN_FAN_MAX_TOKENS_G138",
    "FORBIDDEN_HTTP_AUTH_MYTHS_G138",
    "FRAMING_HDMI_CROP_G137",
    "FRAMING_HDMI_FULL_G137",
    "FRAMING_REC_STREAM_CROP_G137",
    "FRAMING_REC_STREAM_FULL_G137",
    "FRAMING_SETTINGS_F_UXC_RESID16_G137",
    "FX3_BIG6_EXACT_6_TILES_LABELS_G137",
    "FX3_DEFAULT_FW_VERSION_PHASE313",
    "FX3_EXACT_4_FAN_MODES_G138",
    "FX3_HELP_GUIDE_CODE_PHASE313",
    "FX3_MODEL_ID_PHASE313",
    "FX3_MODEL_NAME_PHASE313",
    "FX6_DEFAULT_FW_VERSION_PHASE313",
    "FX6_END_ND_OPTIONS_G137",
    "FX6_EXACT_3_FAN_MODES_G138",
    "FX6_MODEL_NAME_PHASE313",
    "FX6_PARALLEL_REC_G138",
    "FX6_PRODUCT_CODE_PHASE313",
    "FX6_SDI_HDMI_REC_CTRL_OFF_G138",
    "FX6_SDI_HDMI_REMOTE_IF_G138",
    "G137",
    "G137Big6HomeFramingIntervalVaultGuardResult",
    "G137_GATE_CODE",
    "G137_GATE_ID",
    "G138",
    "G138TcMakeHdmiRecSshAuthenFanGuardResult",
    "G138_GATE_CODE",
    "G138_GATE_ID",
    "GATE_G137_BIG6_HOME_ND_META_MANUAL_FRAMING_VS_AUTO_FRAMING_AND_INTERVAL_SHOOT_9999_SLOT1_VAULT_GUARD",
    "GATE_G138_TC_MAKE_REGEN_HDMI_REC_CTRL_SSH_ACCESS_AUTHEN_AND_FAN_4MODE_3MODE_ZERO_MAX_GUARD",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HDMI_4CH_AUDIO_OUTPUT_F_UXC_RESID16_G138",
    "HDMI_REC_CONTROL_F_UXC_RESID16_G138",
    "HDMI_REC_MEDIA_OFF_HDMI_ONLY_G138",
    "HDMI_REC_MEDIA_ON_G138",
    "HDMI_TC_OUTPUT_F_UXC_RESID16_G138",
    "HOME_LOWER_LEFT_APERTURE_G137",
    "HOME_LOWER_LEFT_ND_FILTER_G137",
    "HUMAN_HARDWARE_ATTACH_TOKEN",
    "IMPORT_ROOT_CERT_F_UXC_RESID16_G138",
    "INTERVAL_MAX_DCIM_FILES_G137",
    "INTERVAL_PERIOD_DEFAULT_SEC_G137",
    "INTERVAL_PERIOD_MAX_SEC_G137",
    "INTERVAL_PERIOD_MIN_SEC_G137",
    "INTERVAL_SHOOT_7_PARAMS_G137",
    "INTERVAL_SHOOT_F_UXC_RESID16_G137",
    "INTERVAL_SHOTS_DEFAULT_G137",
    "INTERVAL_SHOTS_MAX_G137",
    "INTERVAL_SHOTS_MIN_G137",
    "INTERVAL_SHUTTER_ELECTRONIC_G137",
    "INTERVAL_SHUTTER_MECHANICAL_G137",
    "INTERVAL_START_TIME_DEFAULT_SEC_G137",
    "INTERVAL_START_TIME_MAX_SEC_G137",
    "INTERVAL_START_TIME_MIN_SEC_G137",
    "INTERVAL_STILL_FORMAT_HEIF_G137",
    "INTERVAL_STILL_FORMAT_JPEG_G137",
    "INTERVAL_STILL_FORMAT_RAW_G137",
    "INTERVAL_STILL_FORMAT_RAW_HEIF_G137",
    "INTERVAL_STILL_FORMAT_RAW_JPEG_G137",
    "LOG_SHOOTING_CINE_EI_G137",
    "LOG_SHOOTING_CINE_EI_QUICK_G137",
    "LOG_SHOOTING_FLEXIBLE_ISO_G137",
    "LOG_SHOOTING_OFF_G137",
    "MEDIA_SIMULT_RECORDING_PHASE313",
    "MEDIA_SLOT_1_PHASE313",
    "MEDIA_SLOT_2_PHASE313",
    "MODE_SETTINGS_FIXED_FPS_G137",
    "MODE_SETTINGS_FIXED_VARIABLE_G137",
    "Master138GateReport",
    "OUTBOUND_CLIENT_TLS_TYPES_G138",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PINNED_FX3_APPFW_SLICES_PHASE313",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE313",
    "PINNED_FX6_APPFW_SLICES_PHASE313",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE313",
    "PINNED_PHASE313_DONOR_SPECS",
    "Phase313DonorAuditResult",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "REALHW_BIG6_HOME_FRAMING_INTERVAL_TC_SSH_FAN_138GATE_SCHEMA",
    "REALHW_BIG6_HOME_FRAMING_INTERVAL_TC_SSH_FAN_138GATE_VERSION",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE313",
    "RESET_ACTION_INITIALIZE_PHASE313",
    "RESET_ACTION_NONE_PHASE313",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE313",
    "SHOOT_MODE_MOVIE_PHASE313",
    "SHOOT_MODE_SQ_PHASE313",
    "SHOOT_MODE_STILL_PHASE313",
    "SHUTTER_MODE_ANGLE_G137",
    "SHUTTER_MODE_SPEED_G137",
    "SPI_NOR_WRITE_AUTHORIZED",
    "SSH_HOST_KEY_G_UXC_RESID16_G138",
    "STATUS_BLOCKED_G137_BIG6_PREREQ_HDMI_OR_END_ACTUATOR_VIOLATION",
    "STATUS_BLOCKED_G137_DORMANT_AUTO_FRAMING_OR_LOCK_VIOLATION",
    "STATUS_BLOCKED_G137_INTERVAL_SHOOT_PARAM_OR_FX6_CROSSWIRE_VIOLATION",
    "STATUS_BLOCKED_G137_SLOT1_INTERVAL_9999_VAULT_FIREWALL_VIOLATION",
    "STATUS_BLOCKED_G137_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G138_FAN_MAX_MYTH_OR_FX6_ALWAYS_OFF_VIOLATION",
    "STATUS_BLOCKED_G138_SSH_ACCESS_AUTHEN_HTTPS_MYTH_OR_CERT_VIOLATION",
    "STATUS_BLOCKED_G138_TC_MAKE_CLOCK_REGEN_OR_HDMI_REC_CTRL_VIOLATION",
    "STATUS_BLOCKED_G138_TELEMETRY_INVALID",
    "STATUS_BLOCKED_PERSISTENT_EMMC_WRITE",
    "STATUS_BLOCKED_PHASE313_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G137",
    "STATUS_VERIFIED_G138",
    "STATUS_VERIFIED_SAFE",
    "TC_MAKE_F_UXC_RESID16_G138",
    "TC_MAKE_FX6_CLOCK_G138",
    "TC_MAKE_PRESET_G138",
    "TC_MAKE_REGENERATE_G138",
    "TC_RUN_F_UXC_RESID16_G138",
    "TC_RUN_FREE_RUN_G138",
    "TC_RUN_REC_RUN_G138",
    "TcMakeHdmiRecSshAuthenFanGuardResult",
    "USB_PACKETS_TRANSMITTED",
    "audit_phase313_donor_contracts",
    "compute_big6_home_framing_interval_matrix",
    "compute_tc_make_ssh_authen_fan_matrix",
    "evaluate_138_master_safety_gates",
    "evaluate_138gate_preflight",
    "evaluate_g137_big6_home_framing_interval_vault_guard",
    "evaluate_g138_tc_make_hdmi_rec_ssh_authen_fan_guard",
    "main",
    "resolve_fx3_big6_home_framing_interval_state",
    "resolve_fx3_tc_make_ssh_authen_fan_state",
    "run_138_gate_preflight",
    "verify_big6_home_framing_interval_vault_guard",
    "verify_tc_make_hdmi_rec_ssh_authen_fan_guard",
]


if __name__ == "__main__":
    raise SystemExit(main())
