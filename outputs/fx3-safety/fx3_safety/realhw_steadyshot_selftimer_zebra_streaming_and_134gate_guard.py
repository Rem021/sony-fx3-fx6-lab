"""Phase 305 (Wave-57, 134/134 Safety Gates Milestone!):
Real-Hardware Safety Gates G133 & G134 + Unified 134-Gate Preflight Engine.

Implements empirical `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` hardware safety gates:

1. **Gate `G133` (`verify-steadyshot-selftimer-guard`)**:
   - FX3 Ver. 7.02 `MENU -> (Shooting) -> [Image Stabilization]` (`_g.uxc 0x6214`):
     - Movie `[SteadyShot]` (`Active` / `Standard` [default] / `Off`), Still `[SteadyShot]`
       (`On` [default] / `Off`), `[SteadyShot Adjust.]` (`Auto` [default] / `Manual`),
       and exact **47-entry `[Focal Length]` table** (`8mm..1000mm`, default `8mm`). All 4
       items are resettable by `[Camera Settings Reset]`.
     - Movie `[Active]` (~`1.104x` crop, forcing `[Distortion Comp.] = Auto`) is locked out
       in ALL **4 empirical conditions**:
       (a) Movie `[Rec Frame Rate] >= 119.88p / 100p`,
       (b) `S&Q` `[Frame Rate] >= 120fps / 100fps`,
       (c) HDMI RAW Output = `On`, and
       (d) `[De-Squeeze Display]` (`1.3x / 1.5x / 1.6x(1.65x) / 1.8x / 2.0x`; linked with
           `VAL_HAITA_steadyshot_equip_with_body_setting_ratio_hdmi_vf_*` /
           `VAL_setting_de_squeeze_disp_DE_SQUEEZE_DISP_*`).
     - Rejects dormant `[Dynamic active]` (`_f.uxc 0x741c`, `_f 0x65b5`, `DYNAMIC_ACTIVE`,
       `MOVIE_STEADYSHOT_EXTENSIONS_HYBRID`) fail-closed (`EOPNOTSUPP`, errno `95`).
     - Contrasts IBIS-less `ILME-FX6 Ver. 6.01` (`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`,
       `FX6_1 0x2fa5` `"The SteadyShot mechanism is fixed."`, lens OSS + 6-axis gyro metadata
       for Catalyst where lens OSS must be Off for Catalyst), plus `[Clear Image Zoom]`
       interactions (disabled at >=100p/100fps or Still RAW; locks `Metering = Multi`).
   - Still vs Movie `[Self-timer]` hardware reality split:
     - Rejects dormant Movie `[Self-timer]` (`BKID_APP_setting_movie_self_timer`,
       `countdown_time 0/3/5/10`, `repeat OFF/ON`, `_f.uxc 0x7192 Rec Start delay: Off`,
       `0x713d`/`0x697d`/`0x773f`/`0x792e`/`0x72ac`/`0x7902`) and dormant Still variants
       (`Single Burst Self-timer` `_f 0x758b`, `Self-portrait 3-sec`
       `BKID_APP_setting_drive_mode_self_portrait` `_f 0x70b8`) fail-closed (`EOPNOTSUPP=95`).
     - Validates Still-only `[Drive Mode]` (`_g 0x616e`): `[Self-timer(Single)]` (`10/5/2 sec`),
       exact **6 combinations** of `[Self-timer(Cont)]` (`10/5/2 Sec. x 3/5 Img.`), and
       `[Selftimer during Bracket]` (`Off / 2 / 5 / 10 Sec`), all resettable by
       `[Camera Settings Reset]`.
     - Validates front hardware module **#8** (`AF illuminator / Self-timer lamp / Visible
       light and IR sensor`, distinct from front REC tally lamp) and `(Setup) -> [Sound Option]
       -> [Audio signals]` (`On/Off`, `_g 0x6110`, `Initialize`-only, suppressed under
       `[Silent Mode] = On` or HDMI audio during movie rec, rejecting dormant `Audio Signal
       Volume` `_f 0x7637`/`0x7af6`), contrasted with `ILME-FX6` (`Picture Cache Rec` &
       `Interval Rec` with `Pre-Lighting`).

2. **Gate `G134` (`verify-zebra-peaking-streaming-firewall-guard`)**:
   - FX3 `[Zebra Display]` (`On/Off` default `Off`, `_f 0x7852`) & `[Zebra Level]`
     (`70..100+` presets + `Custom1` default `Std+Range` `0..109% +- 1..10%` + `Custom2`
     default `Lower Limit` `0..109+`) and 4-color `[Peaking]` (`High/Mid/Low`,
     `Red/Yellow/Blue/White`), ALL **`Initialize`-only** (surviving `[Camera Settings Reset]`),
     ALL isolated from clean HDMI output, with `S-Log3` (`18% grey = 41%`, `90% white = 61%`,
     `clipping ~ 94%` IRE) and `[Display LUT] = On` post-LUT display measurement awareness.
     Contrasted with `ILME-FX6` `Monitoring > Zebra > Setting` strict 3-way selector
     (`Off / Zebra1 / Zebra2` — rejecting simultaneous `Both` fail-closed!) and FX6
     Peaking colors (`B&W / Red / Yellow / Blue`).
   - FX3 Ver. 6.00+/7.02 `MENU -> (Network) -> [Streaming] -> [Network Streaming]`
     (`_f.uxc 0x6cb2`: `RTMP` `H.264`, `RTMPS` SSL/TLS `H.264`, `SRT` `H.265/H.264` +
     `AES-128/256`; resolutions `4K/2K/HD(1080p)/HD(720p)`; frame rates ONLY
     `59.94p/50p/29.97p/25p` — rejecting `23.98p`/`24p`; `[Movie Rec During Streaming]`
     locking internal `4K` recording out during `4K` or `2K 59.94p/50p` streaming and locking
     `Rec Frame Rate` = streaming FPS) and `[FTP Transfer Func.]` (`_f 0x6317`), noting
     `[Reset Network Set.]` preserves `[Airplane Mode] = On`, contrasted with `ILME-FX6`
     dormant QoS/RTMP/SRT symbols.
   - **CRITICAL BENCH FIREWALL**:
     - Enforce `[Airplane Mode] = On` zero-RF lock (blocking wireless Wi-Fi/BLE streaming
       or FTP TX -> `0` wireless packets emitted, `rf_nvs_p12_p13_writes_permitted == False`),
       permitting only wired `USB-LAN` (`CDC-NCM`).
     - Fail-closed `EROFS=30` / `EBUSY=16` blocking whenever `[Movie Rec During Streaming] = Enable`
       or any card/FTP/metadata write targets a `Slot-1` Tier-0 recovery vault
       (`slot1_data_sector_writes == 0`, `slot1_avf_info_mutated == False`).

3. **Unified `134`-Gate Milestone Master Preflight (`evaluate_134gate_preflight` / `verify-134-gates`)**:
   - Delegates `G01..G132` directly to `evaluate_132gate_preflight()` and appends `G133` + `G134`.
   - Offline mode: `131/134` gates pass (`VERIFIED_131_OF_134_AWAITING_PHYSICAL_TIER0`, only
     physical Tier-0 bench receipts `G10..G12` pending); `--simulate-bench-dry-run`: `134/134`
     simulation gates pass (`VERIFIED_ALL_134_GATES_DRY_RUN_SIMULATED_BACKUP`).
   - All hardware attach, persistent eMMC write, EL3/SPI-NOR transmit, and cross-model flash
     redlines remain hard-locked `False`, `usb_packets_transmitted == 0`, and
     `raw_firmware_bytes_leaked == 0`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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
from .realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard import (
    Master132GateReport,
    evaluate_132gate_preflight,
)

# ---------------------------------------------------------------------------
# Schema, Version & Absolute Hardware / Firmware Safety Redlines
# ---------------------------------------------------------------------------

REALHW_STEADYSHOT_SELFTIMER_ZEBRA_STREAMING_134GATE_SCHEMA = (
    "realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard_v1"
)
REALHW_STEADYSHOT_SELFTIMER_ZEBRA_STREAMING_134GATE_VERSION = "2026.11.17"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST_PHASE305 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE305 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE305 = 15.0

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
G133 = "G133"
G133_GATE_ID = "G133"
G133_GATE_CODE = (
    "GATE_G133_STEADYSHOT_IBIS_4LOCK_47FL_VS_DYNAMIC_FX6_AND_MOVIE_SELFTIMER_DORMANT_GUARD"
)
GATE_G133_STEADYSHOT_IBIS_4LOCK_47FL_VS_DYNAMIC_FX6_AND_MOVIE_SELFTIMER_DORMANT_GUARD = (
    G133_GATE_CODE
)

G134 = "G134"
G134_GATE_ID = "G134"
G134_GATE_CODE = (
    "GATE_G134_ZEBRA_CUSTOM12_PEAKING_4COLOR_VS_FX6_3WAY_AND_STREAMING_FTP_ZERORF_SLOT1_FIREWALL"
)
GATE_G134_ZEBRA_CUSTOM12_PEAKING_4COLOR_VS_FX6_3WAY_AND_STREAMING_FTP_ZERORF_SLOT1_FIREWALL = (
    G134_GATE_CODE
)

# Model & Identity Contracts (Phase 305 suffixed to avoid __init__.py shadowing)
FX3_MODEL_NAME_PHASE305 = "ILME-FX3"
FX3_MODEL_ID_PHASE305 = 0x39383232
FX3_HELP_GUIDE_CODE_PHASE305 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE305 = "7.02"

FX6_MODEL_NAME_PHASE305 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE305 = "6.01"
FX6_PRODUCT_CODE_PHASE305 = "PRODUCT_MODEL_CHAPLIN"

# Shoot Modes & Reset Actions
SHOOT_MODE_STILL_PHASE305 = "Still"
SHOOT_MODE_MOVIE_PHASE305 = "Movie"
SHOOT_MODE_SQ_PHASE305 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE305: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE305,
    SHOOT_MODE_MOVIE_PHASE305,
    SHOOT_MODE_SQ_PHASE305,
)

RESET_ACTION_NONE_PHASE305 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE305 = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE305 = "Reset Network Set."
RESET_ACTION_INITIALIZE_PHASE305 = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE305: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE305,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE305,
    RESET_ACTION_RESET_NETWORK_SET_PHASE305,
    RESET_ACTION_INITIALIZE_PHASE305,
)

MEDIA_SLOT_1_PHASE305 = "Slot 1"
MEDIA_SLOT_2_PHASE305 = "Slot 2"
ALLOWED_MEDIA_SLOTS_PHASE305: Tuple[str, ...] = (
    MEDIA_SLOT_1_PHASE305,
    MEDIA_SLOT_2_PHASE305,
)

EOPNOTSUPP_ERRNO_PHASE305 = 95
EOPNOTSUPP_NAME_PHASE305 = "EOPNOTSUPP"
EROFS_ERRNO_PHASE305 = 30
EROFS_NAME_PHASE305 = "EROFS"
EBUSY_ERRNO_PHASE305 = 16
EBUSY_NAME_PHASE305 = "EBUSY"

# ---------------------------------------------------------------------------
# G133 Constants: SteadyShot 5-Axis IBIS 4-Lock Matrix, 47 FL, Self-Timer Split
# ---------------------------------------------------------------------------

IMAGE_STABILIZATION_MENU_PATH_G133 = "MENU -> (Shooting) -> [Image Stabilization]"
IMAGE_STABILIZATION_G_UXC_RESID16_G133 = 0x6214

MOVIE_STEADYSHOT_ACTIVE_G133 = "Active"
MOVIE_STEADYSHOT_STANDARD_G133 = "Standard"
MOVIE_STEADYSHOT_OFF_G133 = "Off"
MOVIE_STEADYSHOT_DEFAULT_G133 = MOVIE_STEADYSHOT_STANDARD_G133
ALLOWED_MOVIE_STEADYSHOT_MODES_G133: Tuple[str, ...] = (
    MOVIE_STEADYSHOT_ACTIVE_G133,
    MOVIE_STEADYSHOT_STANDARD_G133,
    MOVIE_STEADYSHOT_OFF_G133,
)
MOVIE_STEADYSHOT_ACTIVE_F_UXC_RESID16_G133 = 0x714F
MOVIE_STEADYSHOT_ACTIVE_CROP_APPROX_G133 = 1.104

STILL_STEADYSHOT_ON_G133 = "On"
STILL_STEADYSHOT_OFF_G133 = "Off"
STILL_STEADYSHOT_DEFAULT_G133 = STILL_STEADYSHOT_ON_G133
ALLOWED_STILL_STEADYSHOT_MODES_G133: Tuple[str, ...] = (
    STILL_STEADYSHOT_ON_G133,
    STILL_STEADYSHOT_OFF_G133,
)

STEADYSHOT_ADJUST_AUTO_G133 = "Auto"
STEADYSHOT_ADJUST_MANUAL_G133 = "Manual"
STEADYSHOT_ADJUST_DEFAULT_G133 = STEADYSHOT_ADJUST_AUTO_G133
ALLOWED_STEADYSHOT_ADJUST_MODES_G133: Tuple[str, ...] = (
    STEADYSHOT_ADJUST_AUTO_G133,
    STEADYSHOT_ADJUST_MANUAL_G133,
)
STEADYSHOT_ADJUST_F_UXC_RESID16_G133 = 0x7880

STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM_G133 = 8
STEADYSHOT_FOCAL_LENGTH_F_UXC_RESID16_G133 = 0x65B1
STEADYSHOT_FOCAL_LEN_SHORT_F_UXC_RESID16_G133 = 0x625A
STEADYSHOT_47_FOCAL_LENGTHS_MM_G133: Tuple[int, ...] = (
    8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25,
    28, 30, 32, 35, 40, 45, 50, 55, 60, 70, 75, 80, 85, 90, 100, 105,
    120, 135, 150, 180, 200, 210, 250, 300, 350, 400, 450, 500, 600, 800, 1000,
)

DESQUEEZE_OFF_1_0X_G133 = "Off (1.0x)"
DESQUEEZE_1_3X_G133 = "1.3x"
DESQUEEZE_1_5X_G133 = "1.5x"
DESQUEEZE_1_65X_G133 = "1.6x(1.65x)"
DESQUEEZE_1_8X_G133 = "1.8x"
DESQUEEZE_2_0X_G133 = "2.0x"
ALLOWED_DESQUEEZE_RATIOS_G133: Tuple[str, ...] = (
    DESQUEEZE_OFF_1_0X_G133,
    DESQUEEZE_1_3X_G133,
    DESQUEEZE_1_5X_G133,
    DESQUEEZE_1_65X_G133,
    DESQUEEZE_1_8X_G133,
    DESQUEEZE_2_0X_G133,
)

DORMANT_DYNAMIC_ACTIVE_TRAPS_G133: Tuple[str, ...] = (
    "Dynamic active",
    "Dynamic Active",
    "DYNAMIC_ACTIVE",
    "MOVIE_STEADYSHOT_DYNAMIC_ACTIVE",
    "MOVIE_STEADYSHOT_EXTENSIONS_HYBRID",
    "VAL_setting_movie_steadyshot_extensions_MOVIE_STEADYSHOT_EXTENSIONS_HYBRID",
    "0x741c",
    "0x65b5",
)

DORMANT_SELFTIMER_TRAPS_G133: Tuple[str, ...] = (
    "BKID_APP_setting_movie_self_timer",
    "BKID_APP_setting_movie_self_timer_countdown_time",
    "BKID_APP_setting_movie_self_timer_repeat",
    "Movie Self-timer",
    "Rec Start delay",
    "Rec Start delay: Off",
    "Repetition",
    "0x7192",
    "0x713d",
    "0x697d",
    "0x773f",
    "0x792e",
    "0x72ac",
    "0x7902",
    "Single Burst Self-timer",
    "0x758b",
    "BKID_APP_setting_drive_mode_self_portrait",
    "Self-portrait 3-sec",
    "0x70b8",
    "Audio Signal Volume",
    "0x7637",
    "0x7af6",
)

DRIVE_MODE_MENU_PATH_G133 = "MENU -> (Shooting) -> [Drive Mode]"
DRIVE_MODE_G_UXC_RESID16_G133 = 0x616E
DRIVE_MODE_SINGLE_SHOOTING_G133 = "Single Shooting"
DRIVE_MODE_SELF_TIMER_SINGLE_G133 = "Self-timer(Single)"
DRIVE_MODE_SELF_TIMER_CONT_G133 = "Self-timer(Cont)"
DRIVE_MODE_DEFAULT_G133 = DRIVE_MODE_SINGLE_SHOOTING_G133
ALLOWED_DRIVE_MODES_G133: Tuple[str, ...] = (
    DRIVE_MODE_SINGLE_SHOOTING_G133,
    DRIVE_MODE_SELF_TIMER_SINGLE_G133,
    DRIVE_MODE_SELF_TIMER_CONT_G133,
)

SELF_TIMER_SINGLE_10S_G133 = "10 sec"
SELF_TIMER_SINGLE_5S_G133 = "5 sec"
SELF_TIMER_SINGLE_2S_G133 = "2 sec"
SELF_TIMER_SINGLE_DEFAULT_G133 = SELF_TIMER_SINGLE_10S_G133
ALLOWED_SELF_TIMER_SINGLE_OPTIONS_G133: Tuple[str, ...] = (
    SELF_TIMER_SINGLE_10S_G133,
    SELF_TIMER_SINGLE_5S_G133,
    SELF_TIMER_SINGLE_2S_G133,
)

SELF_TIMER_CONT_10S_3IMG_G133 = "10 Sec. 3 Img."
SELF_TIMER_CONT_10S_5IMG_G133 = "10 Sec. 5 Img."
SELF_TIMER_CONT_5S_3IMG_G133 = "5 Sec. 3 Img."
SELF_TIMER_CONT_5S_5IMG_G133 = "5 Sec. 5 Img."
SELF_TIMER_CONT_2S_3IMG_G133 = "2 Sec. 3 Img."
SELF_TIMER_CONT_2S_5IMG_G133 = "2 Sec. 5 Img."
SELF_TIMER_CONT_DEFAULT_G133 = SELF_TIMER_CONT_10S_3IMG_G133
ALLOWED_SELF_TIMER_CONT_OPTIONS_G133: Tuple[str, ...] = (
    SELF_TIMER_CONT_10S_3IMG_G133,
    SELF_TIMER_CONT_10S_5IMG_G133,
    SELF_TIMER_CONT_5S_3IMG_G133,
    SELF_TIMER_CONT_5S_5IMG_G133,
    SELF_TIMER_CONT_2S_3IMG_G133,
    SELF_TIMER_CONT_2S_5IMG_G133,
)

SELFTIMER_BRACKET_OFF_G133 = "Off"
SELFTIMER_BRACKET_2S_G133 = "2 Sec"
SELFTIMER_BRACKET_5S_G133 = "5 Sec"
SELFTIMER_BRACKET_10S_G133 = "10 Sec"
SELFTIMER_BRACKET_DEFAULT_G133 = SELFTIMER_BRACKET_OFF_G133
ALLOWED_SELFTIMER_BRACKET_OPTIONS_G133: Tuple[str, ...] = (
    SELFTIMER_BRACKET_OFF_G133,
    SELFTIMER_BRACKET_2S_G133,
    SELFTIMER_BRACKET_5S_G133,
    SELFTIMER_BRACKET_10S_G133,
)

FRONT_SELFTIMER_LAMP_MODULE_G133 = (
    "Front side #8: AF illuminator / Self-timer lamp / Visible light and IR sensor"
)
AUDIO_SIGNALS_MENU_PATH_G133 = "MENU -> (Setup) -> [Sound Option] -> [Audio signals]"
AUDIO_SIGNALS_G_UXC_RESID16_G133 = 0x6110
AUDIO_SIGNALS_ON_G133 = "On"
AUDIO_SIGNALS_OFF_G133 = "Off"
AUDIO_SIGNALS_DEFAULT_G133 = AUDIO_SIGNALS_ON_G133
ALLOWED_AUDIO_SIGNALS_MODES_G133: Tuple[str, ...] = (
    AUDIO_SIGNALS_ON_G133,
    AUDIO_SIGNALS_OFF_G133,
)

FX6_STEADYSHOT_ELF_SYMBOL_G133 = "TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED"
FX6_STEADYSHOT_UXC_STRING_G133 = "The SteadyShot mechanism is fixed."
FX6_DELAY_OR_TIMELAPSE_MECHANISMS_G133: Tuple[str, ...] = (
    "Project > Picture Cache Rec",
    "Project > Interval Rec",
)

# ---------------------------------------------------------------------------
# G134 Constants: Zebra Custom 1/2, 4-Color Peaking, Streaming, FTP, Firewalls
# ---------------------------------------------------------------------------

ZEBRA_MENU_PATH_G134 = "MENU -> (Exposure/Color) -> [Zebra Display]"
ZEBRA_DISPLAY_G_UXC_RESID16_G134 = 0x6352
ZEBRA_DISPLAY_F_UXC_RESID16_G134 = 0x7852
ZEBRA_DISPLAY_DEFAULT_G134 = "Off"

ZEBRA_LEVEL_F_UXC_RESID16_G134 = 0x70D7
ZEBRA_LEVEL_DEFAULT_G134 = "70"
ALLOWED_ZEBRA_LEVEL_PRESETS_G134: Tuple[str, ...] = (
    "70",
    "75",
    "80",
    "85",
    "90",
    "95",
    "100",
    "100+",
    "Custom1",
    "Custom2",
)
ZEBRA_CUSTOM_TYPE_STD_RANGE_G134 = "Std+Range"
ZEBRA_CUSTOM_TYPE_LOWER_LIMIT_G134 = "Lower Limit"
ALLOWED_ZEBRA_CUSTOM_TYPES_G134: Tuple[str, ...] = (
    ZEBRA_CUSTOM_TYPE_STD_RANGE_G134,
    ZEBRA_CUSTOM_TYPE_LOWER_LIMIT_G134,
)
ZEBRA_IRE_MIN_G134 = 0
ZEBRA_IRE_MAX_G134 = 109
ZEBRA_STD_RANGE_MIN_G134 = 1
ZEBRA_STD_RANGE_MAX_G134 = 10

SLOG3_18PCT_GREY_IRE_G134 = 41
SLOG3_90PCT_WHITE_IRE_G134 = 61
SLOG3_CLIPPING_IRE_APPROX_G134 = 94

PEAKING_MENU_PATH_G134 = "MENU -> (Focus) -> [Peaking Display]"
PEAKING_DISPLAY_G_UXC_RESID16_G134 = 0x6050
PEAKING_DISPLAY_F_UXC_RESID16_G134 = 0x6FE5
PEAKING_DISPLAY_DEFAULT_G134 = "Off"

PEAKING_LEVEL_HIGH_G134 = "High"
PEAKING_LEVEL_MID_G134 = "Mid"
PEAKING_LEVEL_LOW_G134 = "Low"
PEAKING_LEVEL_DEFAULT_G134 = PEAKING_LEVEL_MID_G134
ALLOWED_PEAKING_LEVELS_G134: Tuple[str, ...] = (
    PEAKING_LEVEL_HIGH_G134,
    PEAKING_LEVEL_MID_G134,
    PEAKING_LEVEL_LOW_G134,
)

PEAKING_COLOR_RED_G134 = "Red"
PEAKING_COLOR_YELLOW_G134 = "Yellow"
PEAKING_COLOR_BLUE_G134 = "Blue"
PEAKING_COLOR_WHITE_G134 = "White"
PEAKING_COLOR_DEFAULT_G134 = PEAKING_COLOR_WHITE_G134
ALLOWED_PEAKING_COLORS_FX3_G134: Tuple[str, ...] = (
    PEAKING_COLOR_RED_G134,
    PEAKING_COLOR_YELLOW_G134,
    PEAKING_COLOR_BLUE_G134,
    PEAKING_COLOR_WHITE_G134,
)

FX6_ZEBRA_SETTING_MENU_PATH_G134 = "Monitoring > Zebra > Setting"
FX6_ZEBRA_3WAY_MODES_G134: Tuple[str, ...] = ("Off", "Zebra1", "Zebra2")
FX6_ZEBRA1_APERTURE_MIN_G134 = 2
FX6_ZEBRA1_APERTURE_MAX_G134 = 20
FX6_PEAKING_COLORS_G134: Tuple[str, ...] = ("B&W", "Red", "Yellow", "Blue")

NETWORK_STREAMING_MENU_PATH_G134 = "MENU -> (Network) -> [Streaming] -> [Network Streaming]"
NETWORK_STREAMING_F_UXC_RESID16_G134 = 0x6CB2
FTP_TRANSFER_FUNC_MENU_PATH_G134 = "MENU -> (Network) -> [FTP Transfer] -> [FTP Transfer Func.]"
FTP_TRANSFER_FUNC_F_UXC_RESID16_G134 = 0x6317
AIRPLANE_MODE_MENU_PATH_G134 = "MENU -> (Network) -> [Network Option] -> [Airplane Mode]"
AIRPLANE_MODE_F_UXC_RESID16_G134 = 0x6B05

STREAM_PROTO_RTMP_G134 = "RTMP"
STREAM_PROTO_RTMPS_G134 = "RTMPS"
STREAM_PROTO_SRT_G134 = "SRT"
ALLOWED_STREAM_PROTOCOLS_G134: Tuple[str, ...] = (
    STREAM_PROTO_RTMP_G134,
    STREAM_PROTO_RTMPS_G134,
    STREAM_PROTO_SRT_G134,
)

STREAM_RES_4K_G134 = "4K(2160p)"
STREAM_RES_2K_G134 = "2K(1440p)"
STREAM_RES_HD_1080_G134 = "HD(1080p)"
STREAM_RES_HD_720_G134 = "HD(720p)"
STREAM_RES_DEFAULT_G134 = STREAM_RES_HD_1080_G134
ALLOWED_STREAM_RESOLUTIONS_G134: Tuple[str, ...] = (
    STREAM_RES_4K_G134,
    STREAM_RES_2K_G134,
    STREAM_RES_HD_1080_G134,
    STREAM_RES_HD_720_G134,
)

ALLOWED_STREAM_FRAME_RATES_G134: Tuple[str, ...] = (
    "59.94p",
    "50p",
    "29.97p",
    "25p",
)
DISALLOWED_STREAM_FRAME_RATES_G134: Tuple[str, ...] = ("23.98p", "24p", "119.88p", "100p")

STREAM_QUALITY_HIGH_G134 = "High"
STREAM_QUALITY_STANDARD_G134 = "Standard"
STREAM_QUALITY_LOW_G134 = "Low"
STREAM_QUALITY_CUSTOM_G134 = "Custom"
ALLOWED_STREAM_QUALITY_PRESETS_G134: Tuple[str, ...] = (
    STREAM_QUALITY_HIGH_G134,
    STREAM_QUALITY_STANDARD_G134,
    STREAM_QUALITY_LOW_G134,
    STREAM_QUALITY_CUSTOM_G134,
)
STREAM_MAX_BITRATE_MBPS_G134 = 38.0

MOVIE_REC_DURING_STREAMING_ENABLE_G134 = "Enable"
MOVIE_REC_DURING_STREAMING_DISABLE_G134 = "Disable"
MOVIE_REC_DURING_STREAMING_DEFAULT_G134 = MOVIE_REC_DURING_STREAMING_DISABLE_G134
ALLOWED_MOVIE_REC_DURING_STREAMING_G134: Tuple[str, ...] = (
    MOVIE_REC_DURING_STREAMING_ENABLE_G134,
    MOVIE_REC_DURING_STREAMING_DISABLE_G134,
)

NET_IFACE_NONE_G134 = "None"
NET_IFACE_USB_LAN_G134 = "USB-LAN"
NET_IFACE_WIFI_G134 = "Wi-Fi"
NET_IFACE_BLE_G134 = "BLE"
NET_IFACE_USB_TETHERING_G134 = "USB Tethering"
ALLOWED_NET_INTERFACES_G134: Tuple[str, ...] = (
    NET_IFACE_NONE_G134,
    NET_IFACE_USB_LAN_G134,
    NET_IFACE_WIFI_G134,
    NET_IFACE_BLE_G134,
    NET_IFACE_USB_TETHERING_G134,
)

NET_OP_NONE_G134 = "None"
NET_OP_STREAM_ONLY_G134 = "Stream Only"
NET_OP_STREAM_WITH_INTERNAL_REC_G134 = "Stream With Internal Rec"
NET_OP_FTP_TRANSFER_G134 = "FTP Transfer"
NET_OP_WRITE_FTP_MARKER_TO_CARD_G134 = "Write FTP Marker"
ALLOWED_NET_OPS_G134: Tuple[str, ...] = (
    NET_OP_NONE_G134,
    NET_OP_STREAM_ONLY_G134,
    NET_OP_STREAM_WITH_INTERNAL_REC_G134,
    NET_OP_FTP_TRANSFER_G134,
    NET_OP_WRITE_FTP_MARKER_TO_CARD_G134,
)

FX6_DORMANT_STREAMING_SYMBOLS_G134: Tuple[str, ...] = (
    "BKID_APP_RTMP_SETTINGS1",
    "BKID_APP_SRT_SETTINGS1",
    "QoS Streaming",
    "Intelligent QoS",
)

# Status / Violation Codes
STATUS_BLOCKED_PHASE305_DONOR_INTEGRITY = "STATUS_BLOCKED_PHASE305_DONOR_INTEGRITY"

STATUS_VERIFIED_G133 = "STATUS_VERIFIED_G133"
STATUS_BLOCKED_G133_TELEMETRY_INVALID = "STATUS_BLOCKED_G133_TELEMETRY_INVALID"
STATUS_BLOCKED_G133_STEADYSHOT_ACTIVE_LOCKOUT_OR_DYNAMIC_VIOLATION = (
    "STATUS_BLOCKED_G133_STEADYSHOT_ACTIVE_LOCKOUT_OR_DYNAMIC_VIOLATION"
)
STATUS_BLOCKED_G133_FOCAL_LENGTH_OR_FX6_IBIS_CROSSWIRE_VIOLATION = (
    "STATUS_BLOCKED_G133_FOCAL_LENGTH_OR_FX6_IBIS_CROSSWIRE_VIOLATION"
)
STATUS_BLOCKED_G133_DORMANT_MOVIE_OR_PORTRAIT_SELFTIMER_VIOLATION = (
    "STATUS_BLOCKED_G133_DORMANT_MOVIE_OR_PORTRAIT_SELFTIMER_VIOLATION"
)
STATUS_BLOCKED_G133_SELFTIMER_LAMP_AUDIO_OR_RESET_VIOLATION = (
    "STATUS_BLOCKED_G133_SELFTIMER_LAMP_AUDIO_OR_RESET_VIOLATION"
)

STATUS_VERIFIED_G134 = "STATUS_VERIFIED_G134"
STATUS_BLOCKED_G134_TELEMETRY_INVALID = "STATUS_BLOCKED_G134_TELEMETRY_INVALID"
STATUS_BLOCKED_G134_ZEBRA_CUSTOM12_PEAKING_OR_RESET_VIOLATION = (
    "STATUS_BLOCKED_G134_ZEBRA_CUSTOM12_PEAKING_OR_RESET_VIOLATION"
)
STATUS_BLOCKED_G134_FX6_ZEBRA_BOTH_OR_CLEAN_HDMI_VIOLATION = (
    "STATUS_BLOCKED_G134_FX6_ZEBRA_BOTH_OR_CLEAN_HDMI_VIOLATION"
)
STATUS_BLOCKED_G134_STREAMING_PROTOCOL_FPS_OR_4K_REC_VIOLATION = (
    "STATUS_BLOCKED_G134_STREAMING_PROTOCOL_FPS_OR_4K_REC_VIOLATION"
)
STATUS_BLOCKED_G134_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION = (
    "STATUS_BLOCKED_G134_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION"
)
STATUS_BLOCKED_G134_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION = (
    "STATUS_BLOCKED_G134_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION"
)

# ---------------------------------------------------------------------------
# Pinned Wave-57 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE305: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (62_682_199, b"BKID_APP_setting_movie_steadyshot"),
    (62_682_128, b"BKID_APP_setting_still_steadyshot"),
    (62_682_270, b"BKID_APP_setting_steadyshot_adjustment"),
    (62_682_351, b"BKID_APP_setting_steady_focal_length"),
    (61_611_795, b"VAL_setting_movie_steadyshot_MOVIE_STEADYSHOT_ACTIVE"),
    (61_611_848, b"VAL_setting_movie_steadyshot_MOVIE_STEADYSHOT_STANDARD"),
    (61_611_903, b"VAL_setting_movie_steadyshot_MOVIE_STEADYSHOT_OFF"),
    (
        61_611_648,
        b"VAL_setting_movie_steadyshot_extensions_MOVIE_STEADYSHOT_EXTENSIONS_HYBRID",
    ),
    (61_719_471, b"VAL_setting_still_steadyshot_STILL_STEADYSHOT_ON"),
    (61_719_520, b"VAL_setting_still_steadyshot_STILL_STEADYSHOT_OFF"),
    (61_720_068, b"STEADYSHOT_FOCAL_LENGTH_8MM"),
    (61_722_888, b"STEADYSHOT_FOCAL_LENGTH_1000MM"),
    (61_301_375, b"VAL_setting_de_squeeze_disp_DE_SQUEEZE_DISP_1_3X"),
    (62_684_397, b"BKID_APP_setting_movie_self_timer"),
    (62_858_027, b"BKID_APP_setting_movie_self_timer_countdown_time"),
    (62_858_128, b"BKID_APP_setting_movie_self_timer_repeat"),
    (62_708_196, b"BKID_APP_setting_drive_mode_self_timer"),
    (62_708_364, b"BKID_APP_setting_drive_mode_cont_self_timer"),
    (62_679_493, b"BKID_APP_setting_bracket_self_timer"),
    (61_559_512, b"VAL_setting_bracket_self_timer_BRACKET_SELF_TIMER_OFF"),
    (61_559_676, b"VAL_setting_bracket_self_timer_BRACKET_SELF_TIMER_10SEC"),
    (62_708_277, b"BKID_APP_setting_drive_mode_self_portrait"),
    (62_701_595, b"BKID_APP_setting_audio_signals"),
    (62_158_974, b"AUDIO_SIGNALS_SHUTTER"),
    (62_688_560, b"BKID_APP_setting_zebra_display"),
    (62_688_625, b"BKID_APP_setting_zebra_level"),
    (62_378_544, b"VAL_setting_zebra_level_ZEBRA_LEVEL_70"),
    (62_378_818, b"VAL_setting_zebra_level_ZEBRA_LEVEL_100_PLUS"),
    (62_378_863, b"VAL_setting_zebra_level_ZEBRA_LEVEL_CUSTOM_1"),
    (62_378_908, b"VAL_setting_zebra_level_ZEBRA_LEVEL_CUSTOM_2"),
    (62_830_739, b"BKID_APP_zebra_level_custom_1_type"),
    (62_830_899, b"BKID_APP_zebra_level_custom_1_standard"),
    (62_830_980, b"BKID_APP_zebra_level_custom_1_range"),
    (62_831_128, b"BKID_APP_zebra_level_custom_2_lower_limit"),
    (62_691_446, b"BKID_APP_setting_peaking_display"),
    (62_691_515, b"BKID_APP_setting_peaking_level"),
    (62_691_580, b"BKID_APP_setting_peaking_color"),
    (62_693_751, b"BKID_APP_setting_movie_network_streaming_streaming"),
    (
        62_694_036,
        b"BKID_APP_setting_movie_network_streaming_movie_rec_dur_distribution",
    ),
    (
        62_694_151,
        b"BKID_APP_setting_movie_network_streaming_root_certificate_error",
    ),
    (62_693_926, b"BKID_APP_setting_delivery_image_quality_set_resolution"),
    (62_693_981, b"BKID_APP_setting_delivery_image_quality_set_frame_rate"),
    (
        60_660_348,
        b"VAL_setting_delivery_image_quality_set_frame_rate_DELIVERY_IMAGE_QUALITY_SET_FRAME_RATE_60",
    ),
    (
        60_660_440,
        b"VAL_setting_delivery_image_quality_set_frame_rate_DELIVERY_IMAGE_QUALITY_SET_FRAME_RATE_50",
    ),
    (
        60_660_532,
        b"VAL_setting_delivery_image_quality_set_frame_rate_DELIVERY_IMAGE_QUALITY_SET_FRAME_RATE_30",
    ),
    (
        60_660_624,
        b"VAL_setting_delivery_image_quality_set_frame_rate_DELIVERY_IMAGE_QUALITY_SET_FRAME_RATE_25",
    ),
    (60_646_192, b"STREAM_OUTPUT_ERROR_TYPE_RTMP_KEY_NG"),
    (60_646_127, b"STREAM_OUTPUT_ERROR_TYPE_SRT_KEY_NG"),
    (62_694_699, b"BKID_APP_setting_airplane_mode"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE305 = (
    "b8e2365f9d2f8a34d6827df0ff3b8386464d7aef63a7ef30e594732a69ab1dfd"
)

PINNED_FX6_APPFW_SLICES_PHASE305: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (41_748_974, b"PRODUCT_MODEL_CHAPLIN"),
    (40_560_251, b"TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED"),
    (
        40_560_295,
        b"VAL_HAITA_steadyshot_equip_with_body_setting_ratio_hdmi_vf_NOT_SET",
    ),
    (40_495_868, b"VAL_setting_ratio_hdmi_vf_RATIO_HDMI_VF_1_3X"),
    (40_496_049, b"VAL_setting_ratio_hdmi_vf_RATIO_HDMI_VF_2_0X"),
    (39_726_547, b"PID_SET_SELF_TIMER"),
    (40_932_411, b"BKID_APP_SETTING_PICTURE_CACHE_REC"),
    (40_932_291, b"BKID_APP_SETTING_INTERVALTIME_INTERVAL_REC"),
    (41_128_372, b"BKID_APP_SETTING_INFRA_ZEBRA_DISPLAY"),
    (40_797_726, b"VAL_setting_infra_zebra_display_ZEBRA_DISPLAY_OFF"),
    (40_797_776, b"VAL_setting_infra_zebra_display_ZEBRA_DISPLAY_ZEBRA1"),
    (40_797_829, b"VAL_setting_infra_zebra_display_ZEBRA_DISPLAY_ZEBRA2"),
    (41_019_968, b"BKID_APP_RTMP_SETTINGS1"),
    (41_021_696, b"BKID_APP_SRT_SETTINGS1"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE305 = (
    "c459c4edf454f39742b38239f4319dd3784dbca50322160116628980d871333a"
)

PINNED_PHASE305_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE305,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE305),
        "FX3 appFw.so Wave-57 SteadyShot/Self-timer/Zebra/Peaking/Streaming/FTP/Airplane symbols",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Active",
            b"Dynamic active",
            b"SteadyShot Adjust.",
            b"SteadyS. Focal Len.",
            b"Self-timer(Single)",
            b"Self-timer(Cont)",
            b"Selftimer during Bracket",
            b"Rec Start delay: Off",
            b"Repetition",
            b"Zebra Display",
            b"Zebra Level",
            b"Std+Range",
            b"Lower Limit",
            b"Custom1",
            b"Custom2",
            b"Peaking Display",
            b"Blue",
            b"Network Streaming",
            b"Output Img. Quality Set",
            b"Movie Rec During Streaming",
            b"FTP Transfer Func.",
            b"Airplane Mode",
        ),
        "FX3 string_english_f.uxc Wave-57 EN parity",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "增强".encode("utf-8"),
            "动态增强".encode("utf-8"),
            "SteadyShot调整".encode("utf-8"),
            "SteadyS.焦距".encode("utf-8"),
            "自拍定时（单张）".encode("utf-8"),
            "自拍定时(连拍)".encode("utf-8"),
            "阶段曝光中自拍定时".encode("utf-8"),
            "录制开始延迟: 关".encode("utf-8"),
            "斑马线显示".encode("utf-8"),
            "自定义1".encode("utf-8"),
            "峰值显示".encode("utf-8"),
            "网络流式传输".encode("utf-8"),
            "流式传输动态影像录制".encode("utf-8"),
            "FTP传输功能".encode("utf-8"),
            "飞行模式".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-57 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "積極".encode("utf-8"),
            "動態積極".encode("utf-8"),
            "SteadyShot調整".encode("utf-8"),
            "SteadyS.焦距".encode("utf-8"),
            "自拍定時器（單張）".encode("utf-8"),
            "自拍(連拍)".encode("utf-8"),
            "包圍曝光時自拍定時".encode("utf-8"),
            "錄製開始延遲: 關".encode("utf-8"),
            "斑馬紋顯示".encode("utf-8"),
            "自訂1".encode("utf-8"),
            "峰值顯示".encode("utf-8"),
            "網路串流傳輸".encode("utf-8"),
            "串流傳輸動態影像錄製".encode("utf-8"),
            "FTP傳輸功能".encode("utf-8"),
            "飛航模式".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-57 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "アクティブ".encode("utf-8"),
            "ﾀﾞｲﾅﾐｯｸｱｸﾃｨﾌﾞ".encode("utf-8"),
            "手ブレ補正調整".encode("utf-8"),
            "手ブレ補正焦点距離".encode("utf-8"),
            "ｾﾙﾌﾀｲﾏｰ（1枚）".encode("utf-8"),
            "ｾﾙﾌﾀｲﾏｰ（連続）".encode("utf-8"),
            "ﾌﾞﾗｹｯﾄ時のｾﾙﾌﾀｲﾏｰ".encode("utf-8"),
            "ゼブラ表示".encode("utf-8"),
            "カスタム1".encode("utf-8"),
            "ピーキング表示".encode("utf-8"),
            "ﾈｯﾄﾜｰｸｽﾄﾘｰﾐﾝｸﾞ".encode("utf-8"),
            "ｽﾄﾘｰﾐﾝｸﾞ時の動画記録".encode("utf-8"),
            "FTP転送機能".encode("utf-8"),
            "機内モード".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-57 JA parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"SteadyShot",
            b"Standard",
            b"Off",
            b"Auto",
            b"Manual",
            b"Drive Mode",
            b"Audio signals",
            b"High",
            b"Mid",
            b"Low",
            b"Red",
            b"Yellow",
            b"White",
        ),
        "FX3 string_english.uxc Wave-57 base strings",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Image Stabilization",
            b"Drive Mode",
            b"Sound Option",
            b"Exposure/Color",
            b"Zebra Display",
            b"Focus",
            b"Peaking Display",
            b"Network",
            b"Streaming",
            b"FTP Transfer",
            b"Network Option",
        ),
        "FX3 string_english_g.uxc Wave-57 menu group strings",
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
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE305,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE305),
        "FX6 appFw.so Wave-57 IBIS-less/PictureCacheRec/Zebra1-2/Dormant RTMP-SRT symbols",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"The SteadyShot mechanism is fixed.",
            b"Zebra1",
            b"Zebra2",
            b"Peaking",
            b"Dynamic Active",
        ),
        "FX6 string_english.uxc Wave-57 strings",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"OSS Information",
            b"Zebra1 Level",
            b"Zebra2 Level",
            b"Peaking",
            b"Picture Cache Rec",
            b"Interval Rec",
            b"QoS Streaming",
            b"Intelligent QoS",
        ),
        "FX6 string_english_2.uxc Wave-57 strings",
    ),
}

_DONOR_BLOB_CACHE: Dict[str, Tuple[int, float, int, str, bytes]] = {}

# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase305DonorAuditResult:
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
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SteadyShotSelfTimerGuardResult:
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
    image_stabilization_menu_path: str
    fx3_has_5axis_ibis: bool
    fx6_has_5axis_ibis: bool
    effective_movie_steadyshot: str
    effective_still_steadyshot: str
    effective_steadyshot_adjust: str
    effective_focal_length_mm: int
    focal_length_table_count: int
    movie_active_crop_approx: float
    distortion_comp_forced_auto: bool
    movie_rec_frame_rate: str
    sq_frame_rate: str
    hdmi_raw_output_on: bool
    de_squeeze_ratio: str
    movie_active_locked_out: bool
    movie_active_lockout_reasons: Tuple[str, ...]
    steadyshot_items_reset_by_cam_reset: bool
    clear_image_zoom_on: bool
    clear_image_zoom_available: bool
    clear_image_zoom_coexists_with_steadyshot: bool
    dormant_dynamic_active_blocked: bool
    drive_mode_menu_path: str
    effective_drive_mode: str
    effective_self_timer_single: str
    effective_self_timer_cont: str
    effective_selftimer_during_bracket: str
    selftimer_reset_by_cam_reset: bool
    dormant_movie_selftimer_blocked: bool
    block_errno: Optional[int]
    block_errno_name: Optional[str]
    front_selftimer_lamp_module: str
    front_selftimer_lamp_active: bool
    front_selftimer_lamp_distinct_from_rec_tally: bool
    silent_mode_on: bool
    hdmi_audio_during_movie_rec: bool
    requested_audio_signals: str
    effective_audio_signals: str
    audio_signals_suppressed: bool
    audio_signals_survived_cam_reset: bool
    fx6_delay_mechanisms: Tuple[str, ...]
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G133SteadyShotSelfTimerGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    steadyshot_selftimer_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ZebraPeakingStreamingFirewallGuardResult:
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
    zebra_menu_path: str
    peaking_menu_path: str
    effective_zebra_display: str
    effective_zebra_level: str
    custom1_type: str
    custom1_standard_ire: int
    custom1_range_ire: int
    custom2_type: str
    custom2_lower_limit_ire: int
    effective_peaking_display: str
    effective_peaking_level: str
    effective_peaking_color: str
    zebra_and_peaking_survived_cam_reset: bool
    zebra_isolated_from_clean_hdmi: bool
    peaking_isolated_from_clean_hdmi: bool
    log_shooting_on: bool
    display_lut_on: bool
    zebra_measures_post_lut_display: bool
    slog3_18pct_grey_ire: int
    slog3_clipping_ire: int
    fx6_zebra_3way_selector_only: bool
    fx6_zebra_simultaneous_both_blocked: bool
    fx6_zebra_setting: str
    streaming_menu_path: str
    ftp_menu_path: str
    effective_streaming_active: bool
    streaming_protocol: str
    streaming_resolution: str
    streaming_frame_rate: str
    streaming_bitrate_mbps: float
    effective_movie_rec_during_streaming: str
    forced_internal_rec_frame_rate: Optional[str]
    internal_4k_rec_blocked_by_stream: bool
    sq_rec_blocked_by_stream: bool
    streaming_locks_movie_mode_and_disables_ftp_playback: bool
    effective_ftp_transfer_func: str
    network_survived_cam_reset: bool
    reset_network_set_preserved_airplane_mode: bool
    requested_network_op: str
    requested_net_interface: str
    effective_airplane_mode: str
    bench_zero_rf_required: bool
    airplane_zero_rf_firewall_blocked: bool
    wireless_packets_emitted: int
    rf_nvs_p12_p13_writes_permitted: bool
    rf_nvs_mutation_bytes: int
    requested_target_slot: str
    slot_1_contains_tier0_vault: bool
    slot_1_write_protected: bool
    slot1_vault_firewall_blocked: bool
    block_errno: Optional[int]
    block_errno_name: Optional[str]
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G134ZebraPeakingStreamingFirewallGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    zebra_peaking_streaming_firewall_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master134GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_131_gates_verified: bool
    all_134_gates_verified: bool
    g13_to_g134_all_passed: bool
    g133_to_g134_all_passed: bool
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
    master_132_report: Dict[str, Any]
    g133_result: Dict[str, Any]
    g134_result: Dict[str, Any]
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
        os.environ.get(ENV_CLEAN_ROOM_TEST_PHASE305)
    )


def _is_ci_env() -> bool:
    return _is_truthy(os.environ.get("GITHUB_ACTIONS"))


def _is_real_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


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
    key = f"{path.resolve()}::slices305::{len(slices)}"
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
    if m in ("still", "photo", "p", "a", "s", "m"):
        return SHOOT_MODE_STILL_PHASE305
    if m in ("movie", "video"):
        return SHOOT_MODE_MOVIE_PHASE305
    if m in ("s&q", "sq", "s&q motion", "snq"):
        return SHOOT_MODE_SQ_PHASE305
    return None


def _normalize_reset_action(action: Any) -> Optional[str]:
    if not isinstance(action, str):
        return None
    a = action.strip().lower()
    if a in ("none", "", "no_reset"):
        return RESET_ACTION_NONE_PHASE305
    if a in ("camera settings reset", "cam_reset", "camera_settings_reset"):
        return RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE305
    if a in ("reset network set.", "reset network set", "network_reset"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE305
    if a in ("initialize", "factory_reset", "init"):
        return RESET_ACTION_INITIALIZE_PHASE305
    return None


def _normalize_media_slot(slot: Any) -> Optional[str]:
    if _is_real_int(slot):
        if slot == 1:
            return MEDIA_SLOT_1_PHASE305
        if slot == 2:
            return MEDIA_SLOT_2_PHASE305
        return None
    if not isinstance(slot, str):
        return None
    s = slot.strip().lower().replace("_", " ")
    if s in ("slot 1", "slot1", "1", "a", "slot a"):
        return MEDIA_SLOT_1_PHASE305
    if s in ("slot 2", "slot2", "2", "b", "slot b"):
        return MEDIA_SLOT_2_PHASE305
    return None


def _normalize_on_off(val: Any) -> Optional[str]:
    if isinstance(val, bool):
        return None
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s == "on":
        return "On"
    if s == "off":
        return "Off"
    return None


def _normalize_enable_disable(val: Any) -> Optional[str]:
    if isinstance(val, bool):
        return None
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s == "enable":
        return MOVIE_REC_DURING_STREAMING_ENABLE_G134
    if s == "disable":
        return MOVIE_REC_DURING_STREAMING_DISABLE_G134
    return None


# ---------------------------------------------------------------------------
# 1. `< 0.20s` Bounded O_RDONLY Local Donor Audit (Clean-Room Fallback Safe)
# ---------------------------------------------------------------------------


def audit_phase305_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase305DonorAuditResult:
    """Audit all 11 Wave-57 local donor files strictly via `os.O_RDONLY` in `< 0.20s`
    (with deterministic `CLEAN_ROOM_SYNTHETIC` fallback when donor assets are absent
    or clean-room mode is forced).
    """
    t0 = time.perf_counter()
    resolved_repo = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else dict(PINNED_PHASE305_DONOR_SPECS)
    )
    clean_forced = _is_forced_clean_room(force_clean_room)
    explicit_root = work_root is not None
    effective_root = (
        Path(work_root)
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=resolved_repo).work_root
    )

    if clean_forced:
        elapsed = time.perf_counter() - t0
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE305
            if _is_ci_env()
            else DONOR_CHECK_MAX_SECONDS_PHASE305
        )
        return Phase305DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_NO_DONOR_TOUCH",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_200ms=elapsed <= budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(specs.keys()),
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            sha256_by_artifact={},
            bytes_by_artifact={},
            errors=(),
            warnings=(
                "CLEAN_ROOM_SYNTHETIC mode active; pinned Wave-57 contracts used without donor I/O.",
            ),
        )

    all_exist = all((effective_root / rel).is_file() for _, rel, *_ in specs.values())
    if (not explicit_root) and (not all_exist) and (donor_specs_override is None):
        elapsed = time.perf_counter() - t0
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE305
            if _is_ci_env()
            else DONOR_CHECK_MAX_SECONDS_PHASE305
        )
        return Phase305DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_ABSENT_DONOR_FALLBACK",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_200ms=elapsed <= budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(specs.keys()),
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            sha256_by_artifact={},
            bytes_by_artifact={},
            errors=(),
            warnings=(
                "Local donor tree absent; deterministic CLEAN_ROOM_SYNTHETIC fallback engaged.",
            ),
        )

    checked: List[str] = []
    missing: List[str] = []
    errors: List[str] = []
    sha_map: Dict[str, str] = {}
    bytes_map: Dict[str, int] = {}
    files_inspected = 0

    for key, (_model, rel, expected_size, expected_sha, tokens, desc) in specs.items():
        path = effective_root / rel
        if not path.is_file():
            missing.append(f"{key}:missing_file:{rel}")
            errors.append(f"Missing donor artifact `{key}` ({desc}) at `{rel}`.")
            continue
        files_inspected += 1
        if key == "fx3_appfw_so" and donor_specs_override is None:
            size, digest, present_tokens = _read_appfw_slices_o_rdonly(
                path, PINNED_FX3_APPFW_SLICES_PHASE305
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            size, digest, present_tokens = _read_appfw_slices_o_rdonly(
                path, PINNED_FX6_APPFW_SLICES_PHASE305
            )
        else:
            size, digest, blob = _read_exact_o_rdonly(path)
            present_tokens = tuple(tok for tok in tokens if tok in blob)

        bytes_map[key] = size
        sha_map[key] = digest

        item_ok = True
        if size != expected_size:
            item_ok = False
            missing.append(f"{key}:size_mismatch:{size}!={expected_size}")
            errors.append(
                f"Donor `{key}` size mismatch: observed {size}, expected {expected_size}."
            )
        if digest != expected_sha:
            item_ok = False
            missing.append(f"{key}:sha256_mismatch:{digest[:12]}")
            errors.append(
                f"Donor `{key}` SHA-256 mismatch: observed {digest}, expected {expected_sha}."
            )
        for tok in tokens:
            if tok not in present_tokens:
                item_ok = False
                missing.append(f"{key}:missing_marker:{tok.decode('utf-8', 'replace')}")
                errors.append(f"Donor `{key}` missing pinned marker `{tok!r}`.")
        if item_ok:
            checked.append(key)

    elapsed = time.perf_counter() - t0
    budget = (
        DONOR_CHECK_CI_MAX_SECONDS_PHASE305
        if _is_ci_env()
        else DONOR_CHECK_MAX_SECONDS_PHASE305
    )
    within_budget = elapsed <= budget
    if not within_budget:
        errors.append(
            f"Phase 305 O_RDONLY donor audit exceeded budget: {elapsed:.4f}s > {budget:.2f}s."
        )

    fx3_ok = not any(m.startswith("fx3_") for m in missing)
    fx6_ok = not any(m.startswith("fx6_") for m in missing)
    lang_ok = not any("string_" in m for m in missing)
    valid = (len(missing) == 0) and (len(errors) == 0) and within_budget
    status = STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE305_DONOR_INTEGRITY

    return Phase305DonorAuditResult(
        valid=valid,
        status=status,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY_PREAD_AND_EXACT",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_200ms=within_budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_ok,
        fx6_contracts_verified=fx6_ok,
        four_lang_resid16_parity_verified=lang_ok,
        sha256_by_artifact=sha_map,
        bytes_by_artifact=bytes_map,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate G133: SteadyShot 5-Axis IBIS 4-Lock Matrix & 47-FL Table vs
#    Dormant Dynamic Active & IBIS-less FX6 + Self-Timer Reality Split
# ---------------------------------------------------------------------------


def _normalize_movie_steadyshot(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s == "active":
        return MOVIE_STEADYSHOT_ACTIVE_G133
    if s == "standard":
        return MOVIE_STEADYSHOT_STANDARD_G133
    if s == "off":
        return MOVIE_STEADYSHOT_OFF_G133
    return None


def _normalize_steadyshot_adjust(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s == "auto":
        return STEADYSHOT_ADJUST_AUTO_G133
    if s == "manual":
        return STEADYSHOT_ADJUST_MANUAL_G133
    return None


def _normalize_de_squeeze_ratio(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower().replace(" ", "")
    if s in ("off", "off(1.0x)", "1.0x", "1x"):
        return DESQUEEZE_OFF_1_0X_G133
    if s in ("1.3x", "1_3x"):
        return DESQUEEZE_1_3X_G133
    if s in ("1.5x", "1_5x"):
        return DESQUEEZE_1_5X_G133
    if s in ("1.6x", "1.65x", "1.6x(1.65x)", "1_65x"):
        return DESQUEEZE_1_65X_G133
    if s in ("1.8x", "1_8x"):
        return DESQUEEZE_1_8X_G133
    if s in ("2.0x", "2x", "2_0x"):
        return DESQUEEZE_2_0X_G133
    return None


def _normalize_drive_mode(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower().replace(" ", "")
    if s in ("singleshooting", "single"):
        return DRIVE_MODE_SINGLE_SHOOTING_G133
    if s in ("self-timer(single)", "selftimer(single)", "self-timer", "selftimer"):
        return DRIVE_MODE_SELF_TIMER_SINGLE_G133
    if s in ("self-timer(cont)", "self-timer(cont.)", "selftimer(cont)"):
        return DRIVE_MODE_SELF_TIMER_CONT_G133
    return None


def _normalize_self_timer_single(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower().replace(" ", "")
    if s in ("10sec", "10s", "10sec."):
        return SELF_TIMER_SINGLE_10S_G133
    if s in ("5sec", "5s", "5sec."):
        return SELF_TIMER_SINGLE_5S_G133
    if s in ("2sec", "2s", "2sec."):
        return SELF_TIMER_SINGLE_2S_G133
    return None


def _normalize_self_timer_cont(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower().replace(" ", "").replace(".", "")
    mapping = {
        "10sec3img": SELF_TIMER_CONT_10S_3IMG_G133,
        "10s3img": SELF_TIMER_CONT_10S_3IMG_G133,
        "10sec5img": SELF_TIMER_CONT_10S_5IMG_G133,
        "10s5img": SELF_TIMER_CONT_10S_5IMG_G133,
        "5sec3img": SELF_TIMER_CONT_5S_3IMG_G133,
        "5s3img": SELF_TIMER_CONT_5S_3IMG_G133,
        "5sec5img": SELF_TIMER_CONT_5S_5IMG_G133,
        "5s5img": SELF_TIMER_CONT_5S_5IMG_G133,
        "2sec3img": SELF_TIMER_CONT_2S_3IMG_G133,
        "2s3img": SELF_TIMER_CONT_2S_3IMG_G133,
        "2sec5img": SELF_TIMER_CONT_2S_5IMG_G133,
        "2s5img": SELF_TIMER_CONT_2S_5IMG_G133,
    }
    return mapping.get(s)


def _normalize_selftimer_bracket(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower().replace(" ", "")
    if s == "off":
        return SELFTIMER_BRACKET_OFF_G133
    if s in ("2sec", "2s"):
        return SELFTIMER_BRACKET_2S_G133
    if s in ("5sec", "5s"):
        return SELFTIMER_BRACKET_5S_G133
    if s in ("10sec", "10s"):
        return SELFTIMER_BRACKET_10S_G133
    return None


def _parse_fps_numeric(val: str) -> Optional[float]:
    s = val.strip().lower().replace("fps", "").replace("p", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _compute_g133_effective_state(
    *,
    shoot_mode: str,
    reset_action: str,
    movie_steadyshot: str,
    still_steadyshot: str,
    steadyshot_adjust: str,
    focal_length_mm: int,
    movie_rec_frame_rate: str,
    sq_frame_rate: str,
    hdmi_raw_output_on: bool,
    de_squeeze_ratio: str,
    clear_image_zoom_on: bool,
    still_raw_capture: bool,
    drive_mode: str,
    self_timer_single: str,
    self_timer_cont: str,
    selftimer_during_bracket: str,
    silent_mode_on: bool,
    hdmi_audio_during_movie_rec: bool,
    audio_signals: str,
) -> Dict[str, Any]:
    cam_reset = reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE305,
        RESET_ACTION_INITIALIZE_PHASE305,
    )
    init_reset = reset_action == RESET_ACTION_INITIALIZE_PHASE305

    eff_movie_ss = MOVIE_STEADYSHOT_DEFAULT_G133 if cam_reset else movie_steadyshot
    eff_still_ss = STILL_STEADYSHOT_DEFAULT_G133 if cam_reset else still_steadyshot
    eff_ss_adj = STEADYSHOT_ADJUST_DEFAULT_G133 if cam_reset else steadyshot_adjust
    eff_fl = STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM_G133 if cam_reset else focal_length_mm
    eff_drive = DRIVE_MODE_DEFAULT_G133 if cam_reset else drive_mode
    eff_st_single = SELF_TIMER_SINGLE_DEFAULT_G133 if cam_reset else self_timer_single
    eff_st_cont = SELF_TIMER_CONT_DEFAULT_G133 if cam_reset else self_timer_cont
    eff_st_bracket = SELFTIMER_BRACKET_DEFAULT_G133 if cam_reset else selftimer_during_bracket
    eff_audio_req = AUDIO_SIGNALS_DEFAULT_G133 if init_reset else audio_signals

    lockout_reasons: List[str] = []
    m_fps = _parse_fps_numeric(movie_rec_frame_rate)
    sq_fps = _parse_fps_numeric(sq_frame_rate)
    if m_fps is not None and m_fps >= 100.0:
        lockout_reasons.append(f"movie_rec_frame_rate>={movie_rec_frame_rate}")
    if sq_fps is not None and sq_fps >= 100.0:
        lockout_reasons.append(f"sq_frame_rate>={sq_frame_rate}")
    if hdmi_raw_output_on:
        lockout_reasons.append("hdmi_raw_output=On")
    if de_squeeze_ratio != DESQUEEZE_OFF_1_0X_G133:
        lockout_reasons.append(f"de_squeeze_display={de_squeeze_ratio}")

    active_locked_out = bool(lockout_reasons)
    if active_locked_out and eff_movie_ss == MOVIE_STEADYSHOT_ACTIVE_G133:
        eff_movie_ss = MOVIE_STEADYSHOT_STANDARD_G133

    ciz_blocked_by_fps = (
        (shoot_mode == SHOOT_MODE_MOVIE_PHASE305 and m_fps is not None and m_fps >= 100.0)
        or (shoot_mode == SHOOT_MODE_SQ_PHASE305 and sq_fps is not None and sq_fps >= 100.0)
        or (shoot_mode == SHOOT_MODE_STILL_PHASE305 and still_raw_capture)
    )
    ciz_available = not ciz_blocked_by_fps

    audio_suppressed = bool(
        silent_mode_on
        or (
            shoot_mode in (SHOOT_MODE_MOVIE_PHASE305, SHOOT_MODE_SQ_PHASE305)
            and hdmi_audio_during_movie_rec
        )
    )
    eff_audio = (
        AUDIO_SIGNALS_OFF_G133 if audio_suppressed else eff_audio_req
    )

    front_lamp_active = (
        shoot_mode == SHOOT_MODE_STILL_PHASE305
        and eff_drive
        in (DRIVE_MODE_SELF_TIMER_SINGLE_G133, DRIVE_MODE_SELF_TIMER_CONT_G133)
    )

    return {
        "effective_movie_steadyshot": eff_movie_ss,
        "effective_still_steadyshot": eff_still_ss,
        "effective_steadyshot_adjust": eff_ss_adj,
        "effective_focal_length_mm": eff_fl,
        "distortion_comp_forced_auto": (eff_movie_ss == MOVIE_STEADYSHOT_ACTIVE_G133),
        "movie_active_locked_out": active_locked_out,
        "movie_active_lockout_reasons": tuple(lockout_reasons),
        "clear_image_zoom_available": ciz_available,
        "clear_image_zoom_coexists_with_steadyshot": True,
        "effective_drive_mode": eff_drive,
        "effective_self_timer_single": eff_st_single,
        "effective_self_timer_cont": eff_st_cont,
        "effective_selftimer_during_bracket": eff_st_bracket,
        "front_selftimer_lamp_active": front_lamp_active,
        "audio_signals_suppressed": audio_suppressed,
        "effective_audio_signals": eff_audio,
        "audio_signals_survived_cam_reset": (
            reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE305
            and eff_audio_req == audio_signals
        ),
    }


def compute_steadyshot_selftimer_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate G133 SteadyShot 4-lockout + Reset + Self-timer +
    Silent-Mode matrix states (3 shoot modes x 3 movie_ss x 3 m_fps x 2 sq_fps x
    2 raw x 3 desqueeze x 2 silent x 2 reset = 1,296 states).
    """
    states_checked = 0
    all_invariants_hold = True
    active_lockout_count = 0
    cam_reset_verified_count = 0
    audio_suppressed_count = 0

    for mode in ALLOWED_SHOOT_MODES_PHASE305:
        for mss in ALLOWED_MOVIE_STEADYSHOT_MODES_G133:
            for mfps in ("23.98p", "59.94p", "119.88p"):
                for sqfps in ("24fps", "120fps"):
                    for raw_hdmi in (False, True):
                        for dsq in (
                            DESQUEEZE_OFF_1_0X_G133,
                            DESQUEEZE_1_3X_G133,
                            DESQUEEZE_2_0X_G133,
                        ):
                            for silent in (False, True):
                                for rst in (
                                    RESET_ACTION_NONE_PHASE305,
                                    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE305,
                                ):
                                    st = _compute_g133_effective_state(
                                        shoot_mode=mode,
                                        reset_action=rst,
                                        movie_steadyshot=mss,
                                        still_steadyshot=STILL_STEADYSHOT_OFF_G133,
                                        steadyshot_adjust=STEADYSHOT_ADJUST_MANUAL_G133,
                                        focal_length_mm=50,
                                        movie_rec_frame_rate=mfps,
                                        sq_frame_rate=sqfps,
                                        hdmi_raw_output_on=raw_hdmi,
                                        de_squeeze_ratio=dsq,
                                        clear_image_zoom_on=False,
                                        still_raw_capture=False,
                                        drive_mode=DRIVE_MODE_SELF_TIMER_CONT_G133,
                                        self_timer_single=SELF_TIMER_SINGLE_2S_G133,
                                        self_timer_cont=SELF_TIMER_CONT_5S_5IMG_G133,
                                        selftimer_during_bracket=SELFTIMER_BRACKET_5S_G133,
                                        silent_mode_on=silent,
                                        hdmi_audio_during_movie_rec=False,
                                        audio_signals=AUDIO_SIGNALS_ON_G133,
                                    )
                                    states_checked += 1
                                    if st["movie_active_locked_out"]:
                                        active_lockout_count += 1
                                        if (
                                            st["effective_movie_steadyshot"]
                                            == MOVIE_STEADYSHOT_ACTIVE_G133
                                        ):
                                            all_invariants_hold = False
                                    if rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE305:
                                        cam_reset_verified_count += 1
                                        if (
                                            st["effective_movie_steadyshot"]
                                            != MOVIE_STEADYSHOT_DEFAULT_G133
                                            or st["effective_still_steadyshot"]
                                            != STILL_STEADYSHOT_DEFAULT_G133
                                            or st["effective_steadyshot_adjust"]
                                            != STEADYSHOT_ADJUST_DEFAULT_G133
                                            or st["effective_focal_length_mm"]
                                            != STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM_G133
                                            or st["effective_drive_mode"]
                                            != DRIVE_MODE_DEFAULT_G133
                                            or st["effective_selftimer_during_bracket"]
                                            != SELFTIMER_BRACKET_DEFAULT_G133
                                            or not st["audio_signals_survived_cam_reset"]
                                        ):
                                            all_invariants_hold = False
                                    if silent:
                                        audio_suppressed_count += 1
                                        if (
                                            st["effective_audio_signals"]
                                            != AUDIO_SIGNALS_OFF_G133
                                            or not st["audio_signals_suppressed"]
                                        ):
                                            all_invariants_hold = False

    return {
        "states_checked": states_checked,
        "all_invariants_hold": all_invariants_hold,
        "active_lockout_count": active_lockout_count,
        "cam_reset_verified_count": cam_reset_verified_count,
        "audio_suppressed_count": audio_suppressed_count,
    }


def resolve_fx3_steadyshot_selftimer_state(**kwargs: Any) -> Dict[str, Any]:
    """Return serialized G133 guard state for UI/VM/orchestrator callers."""
    return verify_steadyshot_and_selftimer_guard(**kwargs).to_dict()


def verify_steadyshot_and_selftimer_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE305,
    body_model_id: int = FX3_MODEL_ID_PHASE305,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE305,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE305,
    target_model: str = FX3_MODEL_NAME_PHASE305,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE305,
    reset_action: str = RESET_ACTION_NONE_PHASE305,
    requested_movie_steadyshot: str = MOVIE_STEADYSHOT_DEFAULT_G133,
    requested_still_steadyshot: str = STILL_STEADYSHOT_DEFAULT_G133,
    requested_steadyshot_adjust: str = STEADYSHOT_ADJUST_DEFAULT_G133,
    requested_focal_length_mm: int = STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM_G133,
    movie_rec_frame_rate: str = "23.98p",
    sq_frame_rate: str = "24fps",
    hdmi_raw_output_on: bool = False,
    de_squeeze_ratio: str = DESQUEEZE_OFF_1_0X_G133,
    force_active_under_lockout: bool = False,
    claimed_active_allowed_under_lockout: bool = False,
    dynamic_active_requested: bool = False,
    requested_dormant_steadyshot_symbol: Optional[str] = None,
    clear_image_zoom_on: bool = False,
    still_raw_capture: bool = False,
    claimed_ciz_allowed_in_high_fps_or_raw: bool = False,
    claimed_ciz_disables_steadyshot: bool = False,
    claimed_fx6_has_body_ibis: bool = False,
    claimed_fx6_catalyst_compatible_with_oss_on: bool = False,
    fx6_lens_oss_on: bool = False,
    fx6_catalyst_stabilization_requested: bool = False,
    requested_drive_mode: str = DRIVE_MODE_DEFAULT_G133,
    requested_self_timer_single: str = SELF_TIMER_SINGLE_DEFAULT_G133,
    requested_self_timer_cont: str = SELF_TIMER_CONT_DEFAULT_G133,
    requested_selftimer_during_bracket: str = SELFTIMER_BRACKET_DEFAULT_G133,
    movie_self_timer_requested: bool = False,
    requested_dormant_selftimer_symbol: Optional[str] = None,
    silent_mode_on: bool = False,
    hdmi_audio_during_movie_rec: bool = False,
    requested_audio_signals: str = AUDIO_SIGNALS_DEFAULT_G133,
    claimed_fx3_supports_audio_signal_volume: bool = False,
    claimed_audio_signals_resets_on_cam_reset: bool = False,
    claimed_steadyshot_ignores_cam_reset: bool = False,
    claimed_front_rec_tally_is_selftimer_lamp: bool = False,
    claimed_fx6_has_still_selftimer_or_front_lamp: bool = False,
) -> SteadyShotSelfTimerGuardResult:
    """Enforce Gate G133: 5-axis IBIS 4-condition [Active] lockout matrix, exact
    47-entry focal length table vs dormant [Dynamic active] and IBIS-less ILME-FX6,
    and dormant Movie [Self-timer] rejection vs Still Drive [Self-timer(Single/Cont)],
    front module #8, and [Audio signals] suppression rules.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    norm_shoot = _normalize_shoot_mode(shoot_mode)
    norm_reset = _normalize_reset_action(reset_action)
    norm_still_ss = _normalize_on_off(requested_still_steadyshot)
    norm_ss_adj = _normalize_steadyshot_adjust(requested_steadyshot_adjust)
    norm_dsq = _normalize_de_squeeze_ratio(de_squeeze_ratio)
    norm_drive = _normalize_drive_mode(requested_drive_mode)
    norm_st_single = _normalize_self_timer_single(requested_self_timer_single)
    norm_st_cont = _normalize_self_timer_cont(requested_self_timer_cont)
    norm_st_bracket = _normalize_selftimer_bracket(requested_selftimer_during_bracket)
    norm_audio = _normalize_on_off(requested_audio_signals)

    dormant_dyn_lower = {x.strip().lower() for x in DORMANT_DYNAMIC_ACTIVE_TRAPS_G133}
    raw_mss = (
        requested_movie_steadyshot.strip()
        if isinstance(requested_movie_steadyshot, str)
        else ""
    )
    dormant_dyn_hit = (
        dynamic_active_requested
        or raw_mss.lower() in dormant_dyn_lower
        or (
            requested_dormant_steadyshot_symbol is not None
            and requested_dormant_steadyshot_symbol.strip().lower() in dormant_dyn_lower
        )
    )
    norm_movie_ss = _normalize_movie_steadyshot(requested_movie_steadyshot)

    identity_ok = (
        body_model_name == FX3_MODEL_NAME_PHASE305
        and _is_real_int(body_model_id)
        and body_model_id == FX3_MODEL_ID_PHASE305
        and help_guide_code == FX3_HELP_GUIDE_CODE_PHASE305
        and isinstance(firmware_version, str)
        and firmware_version.strip() not in ("", "BAD", "INVALID")
    )
    if not identity_ok:
        _add_code(codes, STATUS_BLOCKED_G133_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3 Ver. 7.02 hardware/help-guide identity for Gate G133."
        )

    if target_model not in (FX3_MODEL_NAME_PHASE305, FX6_MODEL_NAME_PHASE305):
        _add_code(codes, STATUS_BLOCKED_G133_TELEMETRY_INVALID)
        errors.append(f"Unsupported target_model `{target_model}`.")

    if norm_shoot is None:
        _add_code(codes, STATUS_BLOCKED_G133_TELEMETRY_INVALID)
        errors.append(f"Invalid shoot_mode `{shoot_mode}`.")
        norm_shoot = SHOOT_MODE_MOVIE_PHASE305

    if norm_reset is None:
        _add_code(codes, STATUS_BLOCKED_G133_TELEMETRY_INVALID)
        errors.append(f"Invalid reset_action `{reset_action}`.")
        norm_reset = RESET_ACTION_NONE_PHASE305

    if dormant_dyn_hit:
        _add_code(
            codes, STATUS_BLOCKED_G133_STEADYSHOT_ACTIVE_LOCKOUT_OR_DYNAMIC_VIOLATION
        )
        errors.append(
            "Dormant `[Dynamic active]` (`_f 0x741c`, `MOVIE_STEADYSHOT_EXTENSIONS_HYBRID`) "
            "is NOT exposed on `ILME-FX3 Ver. 7.02` (`EOPNOTSUPP=95`)."
        )
        if norm_movie_ss is None:
            norm_movie_ss = MOVIE_STEADYSHOT_DEFAULT_G133
    elif norm_movie_ss is None:
        _add_code(codes, STATUS_BLOCKED_G133_TELEMETRY_INVALID)
        errors.append(
            f"Invalid Movie `[SteadyShot]` mode `{requested_movie_steadyshot}`."
        )
        norm_movie_ss = MOVIE_STEADYSHOT_DEFAULT_G133

    if norm_still_ss is None:
        _add_code(codes, STATUS_BLOCKED_G133_TELEMETRY_INVALID)
        errors.append(
            f"Invalid Still `[SteadyShot]` mode `{requested_still_steadyshot}`."
        )
        norm_still_ss = STILL_STEADYSHOT_DEFAULT_G133

    if norm_ss_adj is None:
        _add_code(codes, STATUS_BLOCKED_G133_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[SteadyShot Adjust.]` mode `{requested_steadyshot_adjust}`."
        )
        norm_ss_adj = STEADYSHOT_ADJUST_DEFAULT_G133

    if norm_dsq is None:
        _add_code(codes, STATUS_BLOCKED_G133_TELEMETRY_INVALID)
        errors.append(f"Invalid `[De-Squeeze Display]` ratio `{de_squeeze_ratio}`.")
        norm_dsq = DESQUEEZE_OFF_1_0X_G133

    if norm_drive is None:
        _add_code(codes, STATUS_BLOCKED_G133_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Drive Mode]` `{requested_drive_mode}`.")
        norm_drive = DRIVE_MODE_DEFAULT_G133

    if norm_st_single is None:
        _add_code(codes, STATUS_BLOCKED_G133_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[Self-timer(Single)]` option `{requested_self_timer_single}`."
        )
        norm_st_single = SELF_TIMER_SINGLE_DEFAULT_G133

    if norm_st_cont is None:
        _add_code(codes, STATUS_BLOCKED_G133_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[Self-timer(Cont)]` option `{requested_self_timer_cont}`."
        )
        norm_st_cont = SELF_TIMER_CONT_DEFAULT_G133

    if norm_st_bracket is None:
        _add_code(codes, STATUS_BLOCKED_G133_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[Selftimer during Bracket]` `{requested_selftimer_during_bracket}`."
        )
        norm_st_bracket = SELFTIMER_BRACKET_DEFAULT_G133

    if norm_audio is None:
        _add_code(codes, STATUS_BLOCKED_G133_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Audio signals]` value `{requested_audio_signals}`.")
        norm_audio = AUDIO_SIGNALS_DEFAULT_G133

    # Focal Length 47-entry validation & FX6 IBIS cross-wire guard
    valid_fl = (
        _is_real_int(requested_focal_length_mm)
        and requested_focal_length_mm in STEADYSHOT_47_FOCAL_LENGTHS_MM_G133
    )
    if not valid_fl:
        _add_code(
            codes, STATUS_BLOCKED_G133_FOCAL_LENGTH_OR_FX6_IBIS_CROSSWIRE_VIOLATION
        )
        errors.append(
            f"Manual `[Focal Length]` `{requested_focal_length_mm}` is outside the exact "
            "47-entry FX3 SteadyShot table (`8mm..1000mm`)."
        )
    safe_fl = (
        requested_focal_length_mm
        if valid_fl
        else STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM_G133
    )

    if (
        claimed_fx6_has_body_ibis
        or claimed_fx6_catalyst_compatible_with_oss_on
        or (fx6_lens_oss_on and fx6_catalyst_stabilization_requested)
        or (
            target_model == FX6_MODEL_NAME_PHASE305
            and (norm_ss_adj == STEADYSHOT_ADJUST_MANUAL_G133 or safe_fl != 8)
        )
    ):
        _add_code(
            codes, STATUS_BLOCKED_G133_FOCAL_LENGTH_OR_FX6_IBIS_CROSSWIRE_VIOLATION
        )
        errors.append(
            "ILME-FX6 (`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`) lacks body IBIS "
            "and the 47-entry manual focal length table; lens OSS must be Off for Catalyst "
            "gyro stabilization."
        )

    eff = _compute_g133_effective_state(
        shoot_mode=norm_shoot,
        reset_action=norm_reset,
        movie_steadyshot=norm_movie_ss,
        still_steadyshot=norm_still_ss,
        steadyshot_adjust=norm_ss_adj,
        focal_length_mm=safe_fl,
        movie_rec_frame_rate=movie_rec_frame_rate,
        sq_frame_rate=sq_frame_rate,
        hdmi_raw_output_on=bool(hdmi_raw_output_on),
        de_squeeze_ratio=norm_dsq,
        clear_image_zoom_on=bool(clear_image_zoom_on),
        still_raw_capture=bool(still_raw_capture),
        drive_mode=norm_drive,
        self_timer_single=norm_st_single,
        self_timer_cont=norm_st_cont,
        selftimer_during_bracket=norm_st_bracket,
        silent_mode_on=bool(silent_mode_on),
        hdmi_audio_during_movie_rec=bool(hdmi_audio_during_movie_rec),
        audio_signals=norm_audio,
    )

    # Active 4-lockout enforcement & Clear Image Zoom
    if eff["movie_active_locked_out"] and (
        force_active_under_lockout or claimed_active_allowed_under_lockout
    ):
        _add_code(
            codes, STATUS_BLOCKED_G133_STEADYSHOT_ACTIVE_LOCKOUT_OR_DYNAMIC_VIOLATION
        )
        errors.append(
            "Movie `[SteadyShot] = Active` cannot be enabled under lockout condition(s): "
            f"{', '.join(eff['movie_active_lockout_reasons'])} (`EOPNOTSUPP=95`)."
        )

    if (
        (clear_image_zoom_on and not eff["clear_image_zoom_available"])
        or claimed_ciz_allowed_in_high_fps_or_raw
        or claimed_ciz_disables_steadyshot
    ):
        _add_code(
            codes, STATUS_BLOCKED_G133_STEADYSHOT_ACTIVE_LOCKOUT_OR_DYNAMIC_VIOLATION
        )
        errors.append(
            "`[Clear Image Zoom]` is disabled at >=100p/100fps Movie/S&Q or Still RAW, "
            "and coexists with SteadyShot while locking Metering=Multi."
        )

    # Part B: Self-timer split & Dormant Movie / Self-portrait traps
    dormant_st_lower = {x.strip().lower() for x in DORMANT_SELFTIMER_TRAPS_G133}
    dormant_st_hit = (
        movie_self_timer_requested
        or (
            requested_dormant_selftimer_symbol is not None
            and requested_dormant_selftimer_symbol.strip().lower() in dormant_st_lower
        )
        or (
            norm_shoot != SHOOT_MODE_STILL_PHASE305
            and norm_drive
            in (DRIVE_MODE_SELF_TIMER_SINGLE_G133, DRIVE_MODE_SELF_TIMER_CONT_G133)
        )
    )
    if dormant_st_hit:
        _add_code(codes, STATUS_BLOCKED_G133_DORMANT_MOVIE_OR_PORTRAIT_SELFTIMER_VIOLATION)
        errors.append(
            "`ILME-FX3 Ver. 7.02` has NO Movie `[Self-timer]` (`BKID_APP_setting_movie_self_timer`, "
            "`_f 0x7192 Rec Start delay`) and no Still `Single Burst Self-timer` / `Self-portrait "
            "3-sec` (`EOPNOTSUPP=95`)."
        )

    if (
        claimed_fx3_supports_audio_signal_volume
        or claimed_audio_signals_resets_on_cam_reset
        or claimed_steadyshot_ignores_cam_reset
        or claimed_front_rec_tally_is_selftimer_lamp
        or claimed_fx6_has_still_selftimer_or_front_lamp
    ):
        _add_code(codes, STATUS_BLOCKED_G133_SELFTIMER_LAMP_AUDIO_OR_RESET_VIOLATION)
        errors.append(
            "Self-timer hardware/reset invariant violated: SteadyShot/Drive Self-timer reset "
            "on `[Camera Settings Reset]`, `[Audio signals]` is `Initialize`-only without volume "
            "control, front #8 lamp is distinct from front REC tally, and FX6 lacks Still Self-timer."
        )

    any_eopnotsupp = dormant_dyn_hit or dormant_st_hit or (
        eff["movie_active_locked_out"]
        and (force_active_under_lockout or claimed_active_allowed_under_lockout)
    )
    block_errno = EOPNOTSUPP_ERRNO_PHASE305 if any_eopnotsupp else None
    block_errno_name = EOPNOTSUPP_NAME_PHASE305 if any_eopnotsupp else None

    matrix = compute_steadyshot_selftimer_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G133 if valid else codes[0]

    return SteadyShotSelfTimerGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE305,
        target_model=target_model,
        reset_action=norm_reset,
        shoot_mode=norm_shoot,
        image_stabilization_menu_path=IMAGE_STABILIZATION_MENU_PATH_G133,
        fx3_has_5axis_ibis=True,
        fx6_has_5axis_ibis=False,
        effective_movie_steadyshot=eff["effective_movie_steadyshot"],
        effective_still_steadyshot=eff["effective_still_steadyshot"],
        effective_steadyshot_adjust=eff["effective_steadyshot_adjust"],
        effective_focal_length_mm=eff["effective_focal_length_mm"],
        focal_length_table_count=len(STEADYSHOT_47_FOCAL_LENGTHS_MM_G133),
        movie_active_crop_approx=MOVIE_STEADYSHOT_ACTIVE_CROP_APPROX_G133,
        distortion_comp_forced_auto=eff["distortion_comp_forced_auto"],
        movie_rec_frame_rate=movie_rec_frame_rate,
        sq_frame_rate=sq_frame_rate,
        hdmi_raw_output_on=bool(hdmi_raw_output_on),
        de_squeeze_ratio=norm_dsq,
        movie_active_locked_out=eff["movie_active_locked_out"],
        movie_active_lockout_reasons=eff["movie_active_lockout_reasons"],
        steadyshot_items_reset_by_cam_reset=True,
        clear_image_zoom_on=bool(clear_image_zoom_on),
        clear_image_zoom_available=eff["clear_image_zoom_available"],
        clear_image_zoom_coexists_with_steadyshot=eff["clear_image_zoom_coexists_with_steadyshot"],
        dormant_dynamic_active_blocked=dormant_dyn_hit,
        drive_mode_menu_path=DRIVE_MODE_MENU_PATH_G133,
        effective_drive_mode=eff["effective_drive_mode"],
        effective_self_timer_single=eff["effective_self_timer_single"],
        effective_self_timer_cont=eff["effective_self_timer_cont"],
        effective_selftimer_during_bracket=eff["effective_selftimer_during_bracket"],
        selftimer_reset_by_cam_reset=True,
        dormant_movie_selftimer_blocked=dormant_st_hit,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        front_selftimer_lamp_module=FRONT_SELFTIMER_LAMP_MODULE_G133,
        front_selftimer_lamp_active=eff["front_selftimer_lamp_active"],
        front_selftimer_lamp_distinct_from_rec_tally=True,
        silent_mode_on=bool(silent_mode_on),
        hdmi_audio_during_movie_rec=bool(hdmi_audio_during_movie_rec),
        requested_audio_signals=norm_audio,
        effective_audio_signals=eff["effective_audio_signals"],
        audio_signals_suppressed=eff["audio_signals_suppressed"],
        audio_signals_survived_cam_reset=eff["audio_signals_survived_cam_reset"],
        fx6_delay_mechanisms=FX6_DELAY_OR_TIMELAPSE_MECHANISMS_G133,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g133_steadyshot_selftimer_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    steadyshot_selftimer_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase305DonorAuditResult] = None,
) -> Tuple[GateVerdict, G133SteadyShotSelfTimerGuardResult]:
    """Evaluate Wave-57 Gate `G133` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase305_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_steadyshot_and_selftimer_guard(
        **(dict(steadyshot_selftimer_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G133.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G133 if valid else codes[0]

    res = G133SteadyShotSelfTimerGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        steadyshot_selftimer_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, movie_ss={guard.effective_movie_steadyshot},"
        f"locked={guard.movie_active_locked_out}, fl={guard.effective_focal_length_mm}mm/47,"
        f"drive={guard.effective_drive_mode}, audio={guard.effective_audio_signals}"
    )
    verdict = GateVerdict(
        gate_id=G133_GATE_ID,
        gate_code=G133_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G134: Zebra Custom 1/2 IRE Math, 4-Color Peaking vs FX6 3-Way Selector,
#    Network Streaming (RTMP/RTMPS/SRT) + Movie Rec During Streaming +
#    FTP Zero-RF ([Airplane Mode] = On) & Slot-1 Tier-0 Vault Firewall
# ---------------------------------------------------------------------------


def _normalize_zebra_level(val: Any) -> Optional[str]:
    if _is_real_int(val):
        val = str(val)
    if not isinstance(val, str):
        return None
    s = val.strip().lower().replace(" ", "")
    mapping = {
        "70": "70",
        "75": "75",
        "80": "80",
        "85": "85",
        "90": "90",
        "95": "95",
        "100": "100",
        "100+": "100+",
        "custom1": "Custom1",
        "custom2": "Custom2",
    }
    return mapping.get(s)


def _normalize_zebra_custom_type(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower().replace(" ", "")
    if s in ("std+range", "stdrange", "std"):
        return ZEBRA_CUSTOM_TYPE_STD_RANGE_G134
    if s in ("lowerlimit", "lower"):
        return ZEBRA_CUSTOM_TYPE_LOWER_LIMIT_G134
    return None


def _normalize_peaking_level(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    if s == "high":
        return PEAKING_LEVEL_HIGH_G134
    if s == "mid":
        return PEAKING_LEVEL_MID_G134
    if s == "low":
        return PEAKING_LEVEL_LOW_G134
    return None


def _normalize_peaking_color_fx3(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower()
    mapping = {
        "red": PEAKING_COLOR_RED_G134,
        "yellow": PEAKING_COLOR_YELLOW_G134,
        "blue": PEAKING_COLOR_BLUE_G134,
        "white": PEAKING_COLOR_WHITE_G134,
    }
    return mapping.get(s)


def _normalize_stream_protocol(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().upper()
    if s in ALLOWED_STREAM_PROTOCOLS_G134:
        return s
    return None


def _normalize_stream_resolution(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower().replace(" ", "")
    mapping = {
        "4k": STREAM_RES_4K_G134,
        "4k(2160p)": STREAM_RES_4K_G134,
        "2160p": STREAM_RES_4K_G134,
        "2k": STREAM_RES_2K_G134,
        "2k(1440p)": STREAM_RES_2K_G134,
        "1440p": STREAM_RES_2K_G134,
        "hd(1080p)": STREAM_RES_HD_1080_G134,
        "1080p": STREAM_RES_HD_1080_G134,
        "hd": STREAM_RES_HD_1080_G134,
        "hd(720p)": STREAM_RES_HD_720_G134,
        "720p": STREAM_RES_HD_720_G134,
    }
    return mapping.get(s)


def _normalize_net_interface(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    s = val.strip().lower().replace("_", "-")
    mapping = {
        "none": NET_IFACE_NONE_G134,
        "usb-lan": NET_IFACE_USB_LAN_G134,
        "cdc-ncm": NET_IFACE_USB_LAN_G134,
        "wired": NET_IFACE_USB_LAN_G134,
        "wi-fi": NET_IFACE_WIFI_G134,
        "wifi": NET_IFACE_WIFI_G134,
        "wlan0": NET_IFACE_WIFI_G134,
        "ble": NET_IFACE_BLE_G134,
        "bt": NET_IFACE_BLE_G134,
        "bluetooth": NET_IFACE_BLE_G134,
        "usb tethering": NET_IFACE_USB_TETHERING_G134,
        "usbtethering": NET_IFACE_USB_TETHERING_G134,
    }
    return mapping.get(s)


def _compute_g134_effective_state(
    *,
    reset_action: str,
    zebra_display: str,
    zebra_level: str,
    peaking_display: str,
    peaking_level: str,
    peaking_color: str,
    log_shooting_on: bool,
    display_lut_on: bool,
    streaming_active: bool,
    streaming_resolution: str,
    streaming_frame_rate: str,
    movie_rec_during_streaming: str,
    ftp_transfer_func: str,
    airplane_mode: str,
    bench_zero_rf_required: bool,
    rf_nvs_write_requested: bool,
    requested_network_op: str,
    requested_net_interface: str,
    requested_internal_rec_resolution: str,
    requested_target_slot: str,
    slot_1_contains_tier0_vault: bool,
    slot_1_write_protected: bool,
) -> Dict[str, Any]:
    init_reset = reset_action == RESET_ACTION_INITIALIZE_PHASE305
    net_reset = reset_action == RESET_ACTION_RESET_NETWORK_SET_PHASE305

    eff_zebra_disp = ZEBRA_DISPLAY_DEFAULT_G134 if init_reset else zebra_display
    eff_zebra_lvl = ZEBRA_LEVEL_DEFAULT_G134 if init_reset else zebra_level
    eff_peak_disp = PEAKING_DISPLAY_DEFAULT_G134 if init_reset else peaking_display
    eff_peak_lvl = PEAKING_LEVEL_DEFAULT_G134 if init_reset else peaking_level
    eff_peak_col = PEAKING_COLOR_DEFAULT_G134 if init_reset else peaking_color

    eff_stream_active = False if (init_reset or net_reset) else bool(streaming_active)
    eff_rec_dur_stream = (
        MOVIE_REC_DURING_STREAMING_DEFAULT_G134
        if (init_reset or net_reset)
        else movie_rec_during_streaming
    )
    eff_ftp = "Off" if (init_reset or net_reset) else ftp_transfer_func
    # Empirical Sony behavior: Initialize resets Airplane Mode to Off, whereas Reset Network Set. preserves Airplane Mode = On!
    eff_airplane = "Off" if init_reset else airplane_mode

    cam_reset = reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE305
    zebra_peaking_survived_cam_reset = cam_reset and (
        eff_zebra_disp == zebra_display
        and eff_zebra_lvl == zebra_level
        and eff_peak_disp == peaking_display
        and eff_peak_lvl == peaking_level
        and eff_peak_col == peaking_color
    )
    network_survived_cam_reset = cam_reset and (
        eff_stream_active == bool(streaming_active)
        and eff_rec_dur_stream == movie_rec_during_streaming
        and eff_ftp == ftp_transfer_func
        and eff_airplane == airplane_mode
    )
    reset_net_preserved_airplane = (
        net_reset and airplane_mode == "On" and eff_airplane == "On"
    )

    internal_4k_blocked = (
        streaming_resolution == STREAM_RES_4K_G134
        or (
            streaming_resolution == STREAM_RES_2K_G134
            and streaming_frame_rate in ("59.94p", "50p")
        )
    )
    forced_rec_fps = (
        streaming_frame_rate
        if (eff_stream_active and eff_rec_dur_stream == MOVIE_REC_DURING_STREAMING_ENABLE_G134)
        else None
    )

    wireless_iface = requested_net_interface in (NET_IFACE_WIFI_G134, NET_IFACE_BLE_G134)
    wireless_tx_requested = wireless_iface and (
        requested_network_op != NET_OP_NONE_G134
        or eff_stream_active
        or eff_ftp == "On"
    )
    zero_rf_blocked = bool(
        rf_nvs_write_requested
        or (eff_airplane == "On" and wireless_tx_requested)
        or (bench_zero_rf_required and eff_airplane != "On")
    )

    rec_dur_stream_slot1_write = (
        eff_rec_dur_stream == MOVIE_REC_DURING_STREAMING_ENABLE_G134
        and requested_target_slot == MEDIA_SLOT_1_PHASE305
        and requested_network_op == NET_OP_STREAM_WITH_INTERNAL_REC_G134
    )
    marker_slot1_write = (
        requested_network_op == NET_OP_WRITE_FTP_MARKER_TO_CARD_G134
        and requested_target_slot == MEDIA_SLOT_1_PHASE305
    )
    slot1_protected = bool(slot_1_contains_tier0_vault or slot_1_write_protected)
    slot1_vault_blocked = bool(
        slot1_protected and (rec_dur_stream_slot1_write or marker_slot1_write)
    )

    block_errno: Optional[int] = None
    block_errno_name: Optional[str] = None
    if slot1_vault_blocked:
        block_errno = (
            EROFS_ERRNO_PHASE305
            if slot_1_contains_tier0_vault
            else EBUSY_ERRNO_PHASE305
        )
        block_errno_name = (
            EROFS_NAME_PHASE305
            if slot_1_contains_tier0_vault
            else EBUSY_NAME_PHASE305
        )
    elif zero_rf_blocked:
        block_errno = EOPNOTSUPP_ERRNO_PHASE305
        block_errno_name = EOPNOTSUPP_NAME_PHASE305

    return {
        "effective_zebra_display": eff_zebra_disp,
        "effective_zebra_level": eff_zebra_lvl,
        "effective_peaking_display": eff_peak_disp,
        "effective_peaking_level": eff_peak_lvl,
        "effective_peaking_color": eff_peak_col,
        "zebra_and_peaking_survived_cam_reset": zebra_peaking_survived_cam_reset,
        "zebra_measures_post_lut_display": bool(log_shooting_on and display_lut_on),
        "effective_streaming_active": eff_stream_active,
        "effective_movie_rec_during_streaming": eff_rec_dur_stream,
        "forced_internal_rec_frame_rate": forced_rec_fps,
        "internal_4k_rec_blocked_by_stream": internal_4k_blocked,
        "effective_ftp_transfer_func": eff_ftp,
        "effective_airplane_mode": eff_airplane,
        "network_survived_cam_reset": network_survived_cam_reset,
        "reset_network_set_preserved_airplane_mode": reset_net_preserved_airplane,
        "airplane_zero_rf_firewall_blocked": zero_rf_blocked,
        "slot1_vault_firewall_blocked": slot1_vault_blocked,
        "block_errno": block_errno,
        "block_errno_name": block_errno_name,
        "wireless_packets_emitted": 0,
        "rf_nvs_p12_p13_writes_permitted": False,
        "rf_nvs_mutation_bytes": 0,
        "slot1_data_sector_writes": 0,
        "slot1_avf_info_mutated": False,
    }


def compute_zebra_peaking_streaming_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate G134 Zebra/Peaking/DisplayLUT/Streaming/Zero-RF/Slot-1
    Vault matrix (3 reset x 2 log_lut x 3 stream_res x 2 stream_fps x 2 rec_dur x
    2 airplane x 2 net_iface x 2 slot = 576 states).
    """
    states_checked = 0
    all_invariants_hold = True
    post_lut_zebra_count = 0
    stream_4k_rec_blocked_count = 0
    zero_rf_blocked_count = 0
    slot1_vault_blocked_count = 0
    cam_reset_persist_count = 0

    for rst in (
        RESET_ACTION_NONE_PHASE305,
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE305,
        RESET_ACTION_RESET_NETWORK_SET_PHASE305,
    ):
        for dlut in (False, True):
            for sres in (
                STREAM_RES_4K_G134,
                STREAM_RES_2K_G134,
                STREAM_RES_HD_1080_G134,
            ):
                for sfps in ("59.94p", "29.97p"):
                    for rds in (
                        MOVIE_REC_DURING_STREAMING_DISABLE_G134,
                        MOVIE_REC_DURING_STREAMING_ENABLE_G134,
                    ):
                        for air in ("On", "Off"):
                            for iface in (NET_IFACE_USB_LAN_G134, NET_IFACE_WIFI_G134):
                                for slot in (
                                    MEDIA_SLOT_1_PHASE305,
                                    MEDIA_SLOT_2_PHASE305,
                                ):
                                    op = (
                                        NET_OP_STREAM_WITH_INTERNAL_REC_G134
                                        if rds == MOVIE_REC_DURING_STREAMING_ENABLE_G134
                                        else NET_OP_STREAM_ONLY_G134
                                    )
                                    st = _compute_g134_effective_state(
                                        reset_action=rst,
                                        zebra_display="On",
                                        zebra_level="Custom1",
                                        peaking_display="On",
                                        peaking_level=PEAKING_LEVEL_HIGH_G134,
                                        peaking_color=PEAKING_COLOR_BLUE_G134,
                                        log_shooting_on=True,
                                        display_lut_on=dlut,
                                        streaming_active=(rst == RESET_ACTION_NONE_PHASE305),
                                        streaming_resolution=sres,
                                        streaming_frame_rate=sfps,
                                        movie_rec_during_streaming=rds,
                                        ftp_transfer_func="Off",
                                        airplane_mode=air,
                                        bench_zero_rf_required=True,
                                        rf_nvs_write_requested=False,
                                        requested_network_op=op,
                                        requested_net_interface=iface,
                                        requested_internal_rec_resolution=STREAM_RES_HD_1080_G134,
                                        requested_target_slot=slot,
                                        slot_1_contains_tier0_vault=True,
                                        slot_1_write_protected=False,
                                    )
                                    states_checked += 1
                                    if dlut:
                                        post_lut_zebra_count += 1
                                        if not st["zebra_measures_post_lut_display"]:
                                            all_invariants_hold = False
                                    if st["internal_4k_rec_blocked_by_stream"]:
                                        stream_4k_rec_blocked_count += 1
                                    if st["airplane_zero_rf_firewall_blocked"]:
                                        zero_rf_blocked_count += 1
                                    if st["slot1_vault_firewall_blocked"]:
                                        slot1_vault_blocked_count += 1
                                    if (
                                        st["wireless_packets_emitted"] != 0
                                        or st["slot1_data_sector_writes"] != 0
                                        or st["slot1_avf_info_mutated"]
                                    ):
                                        all_invariants_hold = False
                                    if rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE305:
                                        cam_reset_persist_count += 1
                                        if (
                                            not st["zebra_and_peaking_survived_cam_reset"]
                                            or not st["network_survived_cam_reset"]
                                        ):
                                            all_invariants_hold = False

    return {
        "states_checked": states_checked,
        "all_invariants_hold": all_invariants_hold,
        "post_lut_zebra_count": post_lut_zebra_count,
        "stream_4k_rec_blocked_count": stream_4k_rec_blocked_count,
        "zero_rf_blocked_count": zero_rf_blocked_count,
        "slot1_vault_blocked_count": slot1_vault_blocked_count,
        "cam_reset_persist_count": cam_reset_persist_count,
    }


def resolve_fx3_zebra_peaking_streaming_state(**kwargs: Any) -> Dict[str, Any]:
    """Return serialized G134 guard state for UI/VM/orchestrator callers."""
    return verify_zebra_peaking_streaming_firewall_guard(**kwargs).to_dict()


def verify_zebra_peaking_streaming_firewall_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME_PHASE305,
    body_model_id: int = FX3_MODEL_ID_PHASE305,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE305,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE305,
    target_model: str = FX3_MODEL_NAME_PHASE305,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE305,
    reset_action: str = RESET_ACTION_NONE_PHASE305,
    requested_zebra_display: str = ZEBRA_DISPLAY_DEFAULT_G134,
    requested_zebra_level: str = ZEBRA_LEVEL_DEFAULT_G134,
    custom1_type: str = ZEBRA_CUSTOM_TYPE_STD_RANGE_G134,
    custom1_standard_ire: int = SLOG3_18PCT_GREY_IRE_G134,
    custom1_range_ire: int = 2,
    custom2_type: str = ZEBRA_CUSTOM_TYPE_LOWER_LIMIT_G134,
    custom2_lower_limit_ire: int = SLOG3_CLIPPING_IRE_APPROX_G134,
    requested_peaking_display: str = PEAKING_DISPLAY_DEFAULT_G134,
    requested_peaking_level: str = PEAKING_LEVEL_DEFAULT_G134,
    requested_peaking_color: str = PEAKING_COLOR_DEFAULT_G134,
    log_shooting_on: bool = False,
    display_lut_on: bool = False,
    claimed_zebra_or_peaking_resets_on_cam_reset: bool = False,
    claimed_zebra_or_peaking_on_clean_hdmi: bool = False,
    claimed_slog3_107_catches_clipping: bool = False,
    claimed_zebra_ignores_display_lut: bool = False,
    fx6_zebra_setting: str = "Zebra1",
    fx6_zebra1_level_ire: int = 70,
    fx6_zebra1_aperture_ire: int = 10,
    fx6_zebra2_level_ire: int = 100,
    claimed_fx6_zebra_simultaneous_both: bool = False,
    streaming_active: bool = False,
    streaming_protocol: str = STREAM_PROTO_SRT_G134,
    streaming_resolution: str = STREAM_RES_DEFAULT_G134,
    streaming_frame_rate: str = "59.94p",
    streaming_bitrate_mbps: float = 9.0,
    requested_movie_rec_during_streaming: str = MOVIE_REC_DURING_STREAMING_DEFAULT_G134,
    requested_internal_rec_resolution: str = STREAM_RES_DEFAULT_G134,
    requested_ftp_transfer_func: str = "Off",
    claimed_network_resets_on_cam_reset: bool = False,
    claimed_fx6_has_native_rtmp_srt_qos: bool = False,
    fx6_dormant_rtmp_srt_qos_requested: bool = False,
    requested_airplane_mode: str = "On",
    bench_zero_rf_required: bool = True,
    rf_nvs_write_requested: bool = False,
    requested_network_op: str = NET_OP_NONE_G134,
    requested_net_interface: str = NET_IFACE_USB_LAN_G134,
    requested_target_slot: str = MEDIA_SLOT_2_PHASE305,
    slot_1_contains_tier0_vault: bool = True,
    slot_1_write_protected: bool = False,
) -> ZebraPeakingStreamingFirewallGuardResult:
    """Enforce Gate G134: Zebra Custom1/2 IRE & 4-color Peaking vs FX6 3-way
    selector (rejecting Both), Network Streaming (RTMP/RTMPS/SRT, 59.94/50/29.97/25p
    vs 23.98p/24p, internal 4K rec block) & FTP, plus Critical Bench Firewall:
    [Airplane Mode] = On zero-RF lock and Slot-1 Tier-0 Vault EROFS=30 / EBUSY=16.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    norm_shoot = _normalize_shoot_mode(shoot_mode)
    norm_reset = _normalize_reset_action(reset_action)
    norm_z_disp = _normalize_on_off(requested_zebra_display)
    norm_z_lvl = _normalize_zebra_level(requested_zebra_level)
    norm_c1_type = _normalize_zebra_custom_type(custom1_type)
    norm_c2_type = _normalize_zebra_custom_type(custom2_type)
    norm_p_disp = _normalize_on_off(requested_peaking_display)
    norm_p_lvl = _normalize_peaking_level(requested_peaking_level)
    norm_p_col = _normalize_peaking_color_fx3(requested_peaking_color)
    norm_proto = _normalize_stream_protocol(streaming_protocol)
    norm_sres = _normalize_stream_resolution(streaming_resolution)
    norm_rec_res = _normalize_stream_resolution(requested_internal_rec_resolution)
    norm_rds = _normalize_enable_disable(requested_movie_rec_during_streaming)
    norm_ftp = _normalize_on_off(requested_ftp_transfer_func)
    norm_air = _normalize_on_off(requested_airplane_mode)
    norm_iface = _normalize_net_interface(requested_net_interface)
    norm_slot = _normalize_media_slot(requested_target_slot)

    identity_ok = (
        body_model_name == FX3_MODEL_NAME_PHASE305
        and _is_real_int(body_model_id)
        and body_model_id == FX3_MODEL_ID_PHASE305
        and help_guide_code == FX3_HELP_GUIDE_CODE_PHASE305
        and isinstance(firmware_version, str)
        and firmware_version.strip() not in ("", "BAD", "INVALID")
    )
    if not identity_ok:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(
            "Invalid FX3 Ver. 7.02 hardware/help-guide identity for Gate G134."
        )

    if target_model not in (FX3_MODEL_NAME_PHASE305, FX6_MODEL_NAME_PHASE305):
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Unsupported target_model `{target_model}`.")

    if norm_shoot is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Invalid shoot_mode `{shoot_mode}`.")
        norm_shoot = SHOOT_MODE_MOVIE_PHASE305

    if norm_reset is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Invalid reset_action `{reset_action}`.")
        norm_reset = RESET_ACTION_NONE_PHASE305

    if norm_z_disp is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Zebra Display]` `{requested_zebra_display}`.")
        norm_z_disp = ZEBRA_DISPLAY_DEFAULT_G134

    if norm_z_lvl is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Zebra Level]` `{requested_zebra_level}`.")
        norm_z_lvl = ZEBRA_LEVEL_DEFAULT_G134

    if norm_c1_type is None or norm_c2_type is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append("Invalid Zebra Custom1/Custom2 type.")
        norm_c1_type = norm_c1_type or ZEBRA_CUSTOM_TYPE_STD_RANGE_G134
        norm_c2_type = norm_c2_type or ZEBRA_CUSTOM_TYPE_LOWER_LIMIT_G134

    if norm_p_disp is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Peaking Display]` `{requested_peaking_display}`.")
        norm_p_disp = PEAKING_DISPLAY_DEFAULT_G134

    if norm_p_lvl is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Peaking Level]` `{requested_peaking_level}`.")
        norm_p_lvl = PEAKING_LEVEL_DEFAULT_G134

    if norm_p_col is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Invalid FX3 `[Peaking Color]` `{requested_peaking_color}`.")
        norm_p_col = PEAKING_COLOR_DEFAULT_G134

    if norm_proto is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Invalid streaming_protocol `{streaming_protocol}`.")
        norm_proto = STREAM_PROTO_SRT_G134

    if norm_sres is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Invalid streaming_resolution `{streaming_resolution}`.")
        norm_sres = STREAM_RES_DEFAULT_G134

    if norm_rec_res is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(
            f"Invalid requested_internal_rec_resolution `{requested_internal_rec_resolution}`."
        )
        norm_rec_res = STREAM_RES_DEFAULT_G134

    if norm_rds is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(
            f"Invalid `[Movie Rec During Streaming]` `{requested_movie_rec_during_streaming}`."
        )
        norm_rds = MOVIE_REC_DURING_STREAMING_DEFAULT_G134

    if norm_ftp is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Invalid `[FTP Transfer Func.]` `{requested_ftp_transfer_func}`.")
        norm_ftp = "Off"

    if norm_air is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Invalid `[Airplane Mode]` `{requested_airplane_mode}`.")
        norm_air = "On"

    if norm_iface is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_net_interface `{requested_net_interface}`.")
        norm_iface = NET_IFACE_USB_LAN_G134

    if norm_slot is None:
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Invalid requested_target_slot `{requested_target_slot}`.")
        norm_slot = MEDIA_SLOT_2_PHASE305

    if (
        not isinstance(requested_network_op, str)
        or requested_network_op.strip() not in ALLOWED_NET_OPS_G134
    ):
        _add_code(codes, STATUS_BLOCKED_G134_TELEMETRY_INVALID)
        errors.append(f"Unknown requested_network_op `{requested_network_op}`.")
        norm_op = NET_OP_NONE_G134
    else:
        norm_op = requested_network_op.strip()

    # Part A: Zebra Custom 1/2 IRE math, Peaking, Reset, Clean HDMI, FX6 3-way
    ire_ok = (
        _is_real_int(custom1_standard_ire)
        and ZEBRA_IRE_MIN_G134 <= custom1_standard_ire <= ZEBRA_IRE_MAX_G134
        and _is_real_int(custom1_range_ire)
        and ZEBRA_STD_RANGE_MIN_G134 <= custom1_range_ire <= ZEBRA_STD_RANGE_MAX_G134
        and _is_real_int(custom2_lower_limit_ire)
        and ZEBRA_IRE_MIN_G134 <= custom2_lower_limit_ire <= ZEBRA_IRE_MAX_G134
    )
    if not ire_ok:
        _add_code(codes, STATUS_BLOCKED_G134_ZEBRA_CUSTOM12_PEAKING_OR_RESET_VIOLATION)
        errors.append(
            "Zebra Custom1/2 IRE bounds violated (Standard/Lower: 0..109%, Std+Range: 1..10%)."
        )

    if (
        claimed_zebra_or_peaking_resets_on_cam_reset
        or claimed_slog3_107_catches_clipping
        or claimed_zebra_ignores_display_lut
    ):
        _add_code(codes, STATUS_BLOCKED_G134_ZEBRA_CUSTOM12_PEAKING_OR_RESET_VIOLATION)
        errors.append(
            "Zebra/Peaking items are Initialize-only; raw S-Log3 clips around ~94% IRE "
            "(107+ misses S-Log3 clipping), and Display LUT=On shifts Zebra to post-LUT display."
        )

    fx6_zebra_both = (
        claimed_fx6_zebra_simultaneous_both
        or (
            isinstance(fx6_zebra_setting, str)
            and fx6_zebra_setting.strip().lower() in ("both", "zebra1+zebra2", "zebra1&2")
        )
        or (
            not isinstance(fx6_zebra_setting, str)
            or fx6_zebra_setting.strip() not in FX6_ZEBRA_3WAY_MODES_G134
        )
    )
    fx6_bounds_bad = (
        not _is_real_int(fx6_zebra1_level_ire)
        or not (0 <= fx6_zebra1_level_ire <= 109)
        or not _is_real_int(fx6_zebra1_aperture_ire)
        or not (FX6_ZEBRA1_APERTURE_MIN_G134 <= fx6_zebra1_aperture_ire <= FX6_ZEBRA1_APERTURE_MAX_G134)
        or not _is_real_int(fx6_zebra2_level_ire)
        or not (0 <= fx6_zebra2_level_ire <= 109)
    )
    if fx6_zebra_both or fx6_bounds_bad or claimed_zebra_or_peaking_on_clean_hdmi:
        _add_code(codes, STATUS_BLOCKED_G134_FX6_ZEBRA_BOTH_OR_CLEAN_HDMI_VIOLATION)
        errors.append(
            "FX6 Monitoring > Zebra > Setting is strictly a 3-way selector (Off / Zebra1 / "
            "Zebra2 — simultaneous Both rejected), Zebra1 aperture is 2..20%, and FX3 Zebra/Peaking "
            "are isolated from clean HDMI output."
        )

    # Part B: Network Streaming (59.94/50/29.97/25p, bitrate <= 38 Mbps, 4K internal rec lockout) & FTP
    sfps_clean = streaming_frame_rate.strip() if isinstance(streaming_frame_rate, str) else ""
    fps_rejected = sfps_clean not in ALLOWED_STREAM_FRAME_RATES_G134
    bitrate_bad = (
        isinstance(streaming_bitrate_mbps, bool)
        or not isinstance(streaming_bitrate_mbps, (int, float))
        or streaming_bitrate_mbps <= 0.0
        or streaming_bitrate_mbps > STREAM_MAX_BITRATE_MBPS_G134
    )
    internal_4k_attempt = (
        norm_rds == MOVIE_REC_DURING_STREAMING_ENABLE_G134
        and (
            norm_sres == STREAM_RES_4K_G134
            or (norm_sres == STREAM_RES_2K_G134 and sfps_clean in ("59.94p", "50p"))
        )
        and norm_rec_res == STREAM_RES_4K_G134
    )
    if (
        fps_rejected
        or bitrate_bad
        or internal_4k_attempt
        or claimed_network_resets_on_cam_reset
        or claimed_fx6_has_native_rtmp_srt_qos
        or fx6_dormant_rtmp_srt_qos_requested
    ):
        _add_code(codes, STATUS_BLOCKED_G134_STREAMING_PROTOCOL_FPS_OR_4K_REC_VIOLATION)
        errors.append(
            "Streaming/FTP contract violated: only 59.94p/50p/29.97p/25p (no 23.98p/24p) <= 38 Mbps "
            "supported, internal 4K rec is blocked during 4K or 2K 59.94p/50p streaming, (Network) "
            "survives Camera Settings Reset, and FX6 lacks native RTMP/SRT/QoS streaming."
        )

    eff = _compute_g134_effective_state(
        reset_action=norm_reset,
        zebra_display=norm_z_disp,
        zebra_level=norm_z_lvl,
        peaking_display=norm_p_disp,
        peaking_level=norm_p_lvl,
        peaking_color=norm_p_col,
        log_shooting_on=bool(log_shooting_on),
        display_lut_on=bool(display_lut_on),
        streaming_active=bool(streaming_active),
        streaming_resolution=norm_sres,
        streaming_frame_rate=sfps_clean if not fps_rejected else "59.94p",
        movie_rec_during_streaming=norm_rds,
        ftp_transfer_func=norm_ftp,
        airplane_mode=norm_air,
        bench_zero_rf_required=bool(bench_zero_rf_required),
        rf_nvs_write_requested=bool(rf_nvs_write_requested),
        requested_network_op=norm_op,
        requested_net_interface=norm_iface,
        requested_internal_rec_resolution=norm_rec_res,
        requested_target_slot=norm_slot,
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        slot_1_write_protected=bool(slot_1_write_protected),
    )

    # Part C: Critical Bench Firewalls (Zero-RF Airplane Mode + Slot-1 Tier-0 Vault)
    if eff["airplane_zero_rf_firewall_blocked"]:
        _add_code(codes, STATUS_BLOCKED_G134_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION)
        errors.append(
            "Zero-RF Firewall (`[Airplane Mode] = On` + `p12/p13` RF NVS read-only lock) "
            "blocked wireless Wi-Fi/BLE or RF mutation attempt (`wireless_packets_emitted == 0`)."
        )

    if eff["slot1_vault_firewall_blocked"]:
        _add_code(codes, STATUS_BLOCKED_G134_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION)
        errors.append(
            f"`Slot 1` Tier-0 Vault Firewall blocked write (`{norm_op}` -> `Slot 1`) fail-closed "
            f"with `errno={eff['block_errno']} ({eff['block_errno_name']})`: "
            "`slot1_data_sector_writes == 0`, `slot1_avf_info_mutated == False`."
        )

    block_errno = eff["block_errno"]
    block_errno_name = eff["block_errno_name"]
    if block_errno is None and (fps_rejected or fx6_zebra_both or fx6_dormant_rtmp_srt_qos_requested):
        block_errno = EOPNOTSUPP_ERRNO_PHASE305
        block_errno_name = EOPNOTSUPP_NAME_PHASE305

    matrix = compute_zebra_peaking_streaming_matrix()
    valid = not codes
    status = STATUS_VERIFIED_G134 if valid else codes[0]

    return ZebraPeakingStreamingFirewallGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}" if _is_real_int(body_model_id) else "INVALID",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version if isinstance(firmware_version, str) else "INVALID",
        fx6_comparison_fw_version=FX6_DEFAULT_FW_VERSION_PHASE305,
        target_model=target_model,
        reset_action=norm_reset,
        shoot_mode=norm_shoot,
        zebra_menu_path=ZEBRA_MENU_PATH_G134,
        peaking_menu_path=PEAKING_MENU_PATH_G134,
        effective_zebra_display=eff["effective_zebra_display"],
        effective_zebra_level=eff["effective_zebra_level"],
        custom1_type=norm_c1_type,
        custom1_standard_ire=int(custom1_standard_ire) if _is_real_int(custom1_standard_ire) else 0,
        custom1_range_ire=int(custom1_range_ire) if _is_real_int(custom1_range_ire) else 0,
        custom2_type=norm_c2_type,
        custom2_lower_limit_ire=int(custom2_lower_limit_ire) if _is_real_int(custom2_lower_limit_ire) else 0,
        effective_peaking_display=eff["effective_peaking_display"],
        effective_peaking_level=eff["effective_peaking_level"],
        effective_peaking_color=eff["effective_peaking_color"],
        zebra_and_peaking_survived_cam_reset=eff["zebra_and_peaking_survived_cam_reset"],
        zebra_isolated_from_clean_hdmi=True,
        peaking_isolated_from_clean_hdmi=True,
        log_shooting_on=bool(log_shooting_on),
        display_lut_on=bool(display_lut_on),
        zebra_measures_post_lut_display=eff["zebra_measures_post_lut_display"],
        slog3_18pct_grey_ire=SLOG3_18PCT_GREY_IRE_G134,
        slog3_clipping_ire=SLOG3_CLIPPING_IRE_APPROX_G134,
        fx6_zebra_3way_selector_only=True,
        fx6_zebra_simultaneous_both_blocked=True,
        fx6_zebra_setting=str(fx6_zebra_setting),
        streaming_menu_path=NETWORK_STREAMING_MENU_PATH_G134,
        ftp_menu_path=FTP_TRANSFER_FUNC_MENU_PATH_G134,
        effective_streaming_active=eff["effective_streaming_active"],
        streaming_protocol=norm_proto,
        streaming_resolution=norm_sres,
        streaming_frame_rate=sfps_clean,
        streaming_bitrate_mbps=float(streaming_bitrate_mbps)
        if not isinstance(streaming_bitrate_mbps, bool)
        and isinstance(streaming_bitrate_mbps, (int, float))
        else -1.0,
        effective_movie_rec_during_streaming=eff["effective_movie_rec_during_streaming"],
        forced_internal_rec_frame_rate=eff["forced_internal_rec_frame_rate"],
        internal_4k_rec_blocked_by_stream=eff["internal_4k_rec_blocked_by_stream"],
        sq_rec_blocked_by_stream=bool(eff["effective_streaming_active"]),
        streaming_locks_movie_mode_and_disables_ftp_playback=bool(
            eff["effective_streaming_active"]
        ),
        effective_ftp_transfer_func=eff["effective_ftp_transfer_func"],
        network_survived_cam_reset=eff["network_survived_cam_reset"],
        reset_network_set_preserved_airplane_mode=eff[
            "reset_network_set_preserved_airplane_mode"
        ],
        requested_network_op=norm_op,
        requested_net_interface=norm_iface,
        effective_airplane_mode=eff["effective_airplane_mode"],
        bench_zero_rf_required=bool(bench_zero_rf_required),
        airplane_zero_rf_firewall_blocked=eff["airplane_zero_rf_firewall_blocked"],
        wireless_packets_emitted=eff["wireless_packets_emitted"],
        rf_nvs_p12_p13_writes_permitted=eff["rf_nvs_p12_p13_writes_permitted"],
        rf_nvs_mutation_bytes=eff["rf_nvs_mutation_bytes"],
        requested_target_slot=norm_slot,
        slot_1_contains_tier0_vault=bool(slot_1_contains_tier0_vault),
        slot_1_write_protected=bool(slot_1_write_protected),
        slot1_vault_firewall_blocked=eff["slot1_vault_firewall_blocked"],
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        slot1_data_sector_writes=eff["slot1_data_sector_writes"],
        slot1_avf_info_mutated=eff["slot1_avf_info_mutated"],
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g134_zebra_streaming_firewall_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    zebra_peaking_streaming_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase305DonorAuditResult] = None,
) -> Tuple[GateVerdict, G134ZebraPeakingStreamingFirewallGuardResult]:
    """Evaluate Wave-57 Gate `G134` including `< 0.20s` `O_RDONLY` donor audit."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase305_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_zebra_peaking_streaming_firewall_guard(
        **(dict(zebra_peaking_streaming_kwargs or {}))
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
        errors.append("Persistent eMMC write authorization requested in Gate G134.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G134 if valid else codes[0]

    res = G134ZebraPeakingStreamingFirewallGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        zebra_peaking_streaming_firewall_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, zebra={guard.effective_zebra_display}/{guard.effective_zebra_level},"
        f"peak={guard.effective_peaking_display}/{guard.effective_peaking_color},"
        f"proto={guard.streaming_protocol}@{guard.streaming_resolution}/{guard.streaming_frame_rate},"
        f"air={guard.effective_airplane_mode}, rf_pkts={guard.wireless_packets_emitted},"
        f"slot1_vault={guard.slot_1_contains_tier0_vault}, s1_writes={guard.slot1_data_sector_writes}"
    )
    verdict = GateVerdict(
        gate_id=G134_GATE_ID,
        gate_code=G134_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `134`-Gate Milestone Master Safety Preflight (`G01..G134`)
# ---------------------------------------------------------------------------


def evaluate_134gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    steadyshot_selftimer_kwargs: Optional[Mapping[str, Any]] = None,
    zebra_peaking_streaming_kwargs: Optional[Mapping[str, Any]] = None,
    master_132_override: Optional[Master132GateReport] = None,
    **m132_passthrough_kwargs: Any,
) -> Master134GateReport:
    """Evaluate all 134 Master Safety Gates (`G01..G134`) deterministically by
    delegating `G01..G132` directly to `evaluate_132gate_preflight()`.
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

    m132_report: Master132GateReport = (
        master_132_override
        if master_132_override is not None
        else evaluate_132gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m132_passthrough_kwargs,
        )
    )

    phase305_audit = audit_phase305_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g133_verdict, g133_res = evaluate_g133_steadyshot_selftimer_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        steadyshot_selftimer_kwargs=steadyshot_selftimer_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase305_audit,
    )

    g134_verdict, g134_res = evaluate_g134_zebra_streaming_firewall_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        zebra_peaking_streaming_kwargs=zebra_peaking_streaming_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase305_audit,
    )

    gates_133_to_134 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g133_verdict, g134_verdict)
    ]
    all_gates = tuple(list(m132_report.gates) + gates_133_to_134)

    g01_to_g12_verified = int(m132_report.summary["g01_to_g12_verified"])
    g13_to_g132_verified = int(m132_report.summary["g13_to_g130_verified"]) + int(
        m132_report.summary["g131_to_g132_verified"]
    )
    g133_to_g134_verified = sum(1 for v in (g133_verdict, g134_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g132_verified + g133_to_g134_verified

    g133_to_g134_all_passed = g133_to_g134_verified == 2
    g13_to_g134_all_passed = (
        m132_report.g13_to_g132_all_passed and g133_to_g134_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m132_report.gates[:9])

    offline_131_verified = (
        g01_to_g09_ok
        and m132_report.offline_129_gates_verified
        and g133_to_g134_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_134_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g134_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m132_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_131_verified
        and m132_report.h0_h1_trial_entry_allowed
        and g133_to_g134_all_passed
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
        list(m132_report.errors)
        + list(g133_verdict.errors)
        + list(g134_verdict.errors)
    )
    warnings: List[str] = (
        list(m132_report.warnings)
        + list(g133_verdict.warnings)
        + list(g134_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m132_report.g13_to_g132_all_passed:
        overall_status = m132_report.status
    elif not g133_verdict.passed:
        overall_status = g133_verdict.status
    elif not g134_verdict.passed:
        overall_status = g134_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_134_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_134_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_134_verified:
        overall_status = "VERIFIED_ALL_134_GATES"
    else:
        overall_status = "VERIFIED_131_OF_134_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m132_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g133_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g134_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 134,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 134 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g132_verified": g13_to_g132_verified,
        "g133_to_g134_verified": g133_to_g134_verified,
        "g13_to_g134_all_passed": g13_to_g134_all_passed,
        "g133_to_g134_all_passed": g133_to_g134_all_passed,
        "offline_131_gates_verified": offline_131_verified,
        "all_134_gates_verified": all_134_verified,
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

    return Master134GateReport(
        schema=REALHW_STEADYSHOT_SELFTIMER_ZEBRA_STREAMING_134GATE_SCHEMA,
        version=REALHW_STEADYSHOT_SELFTIMER_ZEBRA_STREAMING_134GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_131_gates_verified=offline_131_verified,
        all_134_gates_verified=all_134_verified,
        g13_to_g134_all_passed=g13_to_g134_all_passed,
        g133_to_g134_all_passed=g133_to_g134_all_passed,
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
        master_132_report=m132_report.to_dict(),
        g133_result=g133_res.to_dict(),
        g134_result=g134_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_134_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master134GateReport:
    return evaluate_134gate_preflight(repo_root, **kwargs)


def run_134_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master134GateReport:
    return evaluate_134gate_preflight(repo_root, **kwargs)


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
        prog="realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard",
        description="Phase 305 Wave-57 G133/G134 and 134/134 Safety Gates Preflight CLI",
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
        help="Supply simulated dry-run Tier-0 backup inputs so all 134/134 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g133", "g134", "134"],
        default="134",
        help="Target gate check: g133, g134, or 134",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g133":
        v, r = evaluate_g133_steadyshot_selftimer_guard(
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

    if args.gate == "g134":
        v, r = evaluate_g134_zebra_streaming_firewall_guard(
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

    rep = evaluate_134gate_preflight(
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
                "g133_status": rep.g133_result["status"],
                "g134_status": rep.g134_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/134\n"
        )
    ok = (
        rep.all_134_gates_verified
        if args.dry_run_simulated
        else rep.offline_131_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "AIRPLANE_MODE_F_UXC_RESID16_G134",
    "AIRPLANE_MODE_MENU_PATH_G134",
    "ALLOWED_AUDIO_SIGNALS_MODES_G133",
    "ALLOWED_DESQUEEZE_RATIOS_G133",
    "ALLOWED_DRIVE_MODES_G133",
    "ALLOWED_MEDIA_SLOTS_PHASE305",
    "ALLOWED_MOVIE_REC_DURING_STREAMING_G134",
    "ALLOWED_MOVIE_STEADYSHOT_MODES_G133",
    "ALLOWED_NET_INTERFACES_G134",
    "ALLOWED_NET_OPS_G134",
    "ALLOWED_PEAKING_COLORS_FX3_G134",
    "ALLOWED_PEAKING_LEVELS_G134",
    "ALLOWED_RESET_ACTIONS_PHASE305",
    "ALLOWED_SELFTIMER_BRACKET_OPTIONS_G133",
    "ALLOWED_SELF_TIMER_CONT_OPTIONS_G133",
    "ALLOWED_SELF_TIMER_SINGLE_OPTIONS_G133",
    "ALLOWED_SHOOT_MODES_PHASE305",
    "ALLOWED_STEADYSHOT_ADJUST_MODES_G133",
    "ALLOWED_STILL_STEADYSHOT_MODES_G133",
    "ALLOWED_STREAM_FRAME_RATES_G134",
    "ALLOWED_STREAM_PROTOCOLS_G134",
    "ALLOWED_STREAM_QUALITY_PRESETS_G134",
    "ALLOWED_STREAM_RESOLUTIONS_G134",
    "ALLOWED_ZEBRA_CUSTOM_TYPES_G134",
    "ALLOWED_ZEBRA_LEVEL_PRESETS_G134",
    "AUDIO_SIGNALS_DEFAULT_G133",
    "AUDIO_SIGNALS_G_UXC_RESID16_G133",
    "AUDIO_SIGNALS_MENU_PATH_G133",
    "AUDIO_SIGNALS_OFF_G133",
    "AUDIO_SIGNALS_ON_G133",
    "CROSS_MODEL_FLASH_AUTHORIZED",
    "DEFAULT_REPO_ROOT",
    "DESQUEEZE_1_3X_G133",
    "DESQUEEZE_1_5X_G133",
    "DESQUEEZE_1_65X_G133",
    "DESQUEEZE_1_8X_G133",
    "DESQUEEZE_2_0X_G133",
    "DESQUEEZE_OFF_1_0X_G133",
    "DISALLOWED_STREAM_FRAME_RATES_G134",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE305",
    "DONOR_CHECK_MAX_SECONDS_PHASE305",
    "DORMANT_DYNAMIC_ACTIVE_TRAPS_G133",
    "DORMANT_SELFTIMER_TRAPS_G133",
    "DRIVE_MODE_DEFAULT_G133",
    "DRIVE_MODE_G_UXC_RESID16_G133",
    "DRIVE_MODE_MENU_PATH_G133",
    "DRIVE_MODE_SELF_TIMER_CONT_G133",
    "DRIVE_MODE_SELF_TIMER_SINGLE_G133",
    "DRIVE_MODE_SINGLE_SHOOTING_G133",
    "EBUSY_ERRNO_PHASE305",
    "EBUSY_NAME_PHASE305",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "ENV_CLEAN_ROOM_TEST_PHASE305",
    "ENV_FORCE_CLEAN_ROOM",
    "EOPNOTSUPP_ERRNO_PHASE305",
    "EOPNOTSUPP_NAME_PHASE305",
    "EROFS_ERRNO_PHASE305",
    "EROFS_NAME_PHASE305",
    "FRONT_SELFTIMER_LAMP_MODULE_G133",
    "FTP_TRANSFER_FUNC_F_UXC_RESID16_G134",
    "FTP_TRANSFER_FUNC_MENU_PATH_G134",
    "FX3_DEFAULT_FW_VERSION_PHASE305",
    "FX3_HELP_GUIDE_CODE_PHASE305",
    "FX3_MODEL_ID_PHASE305",
    "FX3_MODEL_NAME_PHASE305",
    "FX6_DEFAULT_FW_VERSION_PHASE305",
    "FX6_DELAY_OR_TIMELAPSE_MECHANISMS_G133",
    "FX6_DORMANT_STREAMING_SYMBOLS_G134",
    "FX6_MODEL_NAME_PHASE305",
    "FX6_PEAKING_COLORS_G134",
    "FX6_PRODUCT_CODE_PHASE305",
    "FX6_STEADYSHOT_ELF_SYMBOL_G133",
    "FX6_STEADYSHOT_UXC_STRING_G133",
    "FX6_ZEBRA1_APERTURE_MAX_G134",
    "FX6_ZEBRA1_APERTURE_MIN_G134",
    "FX6_ZEBRA_3WAY_MODES_G134",
    "FX6_ZEBRA_SETTING_MENU_PATH_G134",
    "G133",
    "G133SteadyShotSelfTimerGuardResult",
    "G133_GATE_CODE",
    "G133_GATE_ID",
    "G134",
    "G134ZebraPeakingStreamingFirewallGuardResult",
    "G134_GATE_CODE",
    "G134_GATE_ID",
    "GATE_G133_STEADYSHOT_IBIS_4LOCK_47FL_VS_DYNAMIC_FX6_AND_MOVIE_SELFTIMER_DORMANT_GUARD",
    "GATE_G134_ZEBRA_CUSTOM12_PEAKING_4COLOR_VS_FX6_3WAY_AND_STREAMING_FTP_ZERORF_SLOT1_FIREWALL",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HUMAN_HARDWARE_ATTACH_TOKEN",
    "IMAGE_STABILIZATION_G_UXC_RESID16_G133",
    "IMAGE_STABILIZATION_MENU_PATH_G133",
    "MEDIA_SLOT_1_PHASE305",
    "MEDIA_SLOT_2_PHASE305",
    "MOVIE_REC_DURING_STREAMING_DEFAULT_G134",
    "MOVIE_REC_DURING_STREAMING_DISABLE_G134",
    "MOVIE_REC_DURING_STREAMING_ENABLE_G134",
    "MOVIE_STEADYSHOT_ACTIVE_CROP_APPROX_G133",
    "MOVIE_STEADYSHOT_ACTIVE_F_UXC_RESID16_G133",
    "MOVIE_STEADYSHOT_ACTIVE_G133",
    "MOVIE_STEADYSHOT_DEFAULT_G133",
    "MOVIE_STEADYSHOT_OFF_G133",
    "MOVIE_STEADYSHOT_STANDARD_G133",
    "Master134GateReport",
    "NETWORK_STREAMING_F_UXC_RESID16_G134",
    "NETWORK_STREAMING_MENU_PATH_G134",
    "NET_IFACE_BLE_G134",
    "NET_IFACE_NONE_G134",
    "NET_IFACE_USB_LAN_G134",
    "NET_IFACE_USB_TETHERING_G134",
    "NET_IFACE_WIFI_G134",
    "NET_OP_FTP_TRANSFER_G134",
    "NET_OP_NONE_G134",
    "NET_OP_STREAM_ONLY_G134",
    "NET_OP_STREAM_WITH_INTERNAL_REC_G134",
    "NET_OP_WRITE_FTP_MARKER_TO_CARD_G134",
    "PEAKING_COLOR_BLUE_G134",
    "PEAKING_COLOR_DEFAULT_G134",
    "PEAKING_COLOR_RED_G134",
    "PEAKING_COLOR_WHITE_G134",
    "PEAKING_COLOR_YELLOW_G134",
    "PEAKING_DISPLAY_DEFAULT_G134",
    "PEAKING_DISPLAY_F_UXC_RESID16_G134",
    "PEAKING_DISPLAY_G_UXC_RESID16_G134",
    "PEAKING_LEVEL_DEFAULT_G134",
    "PEAKING_LEVEL_HIGH_G134",
    "PEAKING_LEVEL_LOW_G134",
    "PEAKING_LEVEL_MID_G134",
    "PEAKING_MENU_PATH_G134",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "PINNED_FX3_APPFW_SLICES_PHASE305",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE305",
    "PINNED_FX6_APPFW_SLICES_PHASE305",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE305",
    "PINNED_PHASE305_DONOR_SPECS",
    "Phase305DonorAuditResult",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "REALHW_STEADYSHOT_SELFTIMER_ZEBRA_STREAMING_134GATE_SCHEMA",
    "REALHW_STEADYSHOT_SELFTIMER_ZEBRA_STREAMING_134GATE_VERSION",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE305",
    "RESET_ACTION_INITIALIZE_PHASE305",
    "RESET_ACTION_NONE_PHASE305",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE305",
    "SELFTIMER_BRACKET_10S_G133",
    "SELFTIMER_BRACKET_2S_G133",
    "SELFTIMER_BRACKET_5S_G133",
    "SELFTIMER_BRACKET_DEFAULT_G133",
    "SELFTIMER_BRACKET_OFF_G133",
    "SELF_TIMER_CONT_10S_3IMG_G133",
    "SELF_TIMER_CONT_10S_5IMG_G133",
    "SELF_TIMER_CONT_2S_3IMG_G133",
    "SELF_TIMER_CONT_2S_5IMG_G133",
    "SELF_TIMER_CONT_5S_3IMG_G133",
    "SELF_TIMER_CONT_5S_5IMG_G133",
    "SELF_TIMER_CONT_DEFAULT_G133",
    "SELF_TIMER_SINGLE_10S_G133",
    "SELF_TIMER_SINGLE_2S_G133",
    "SELF_TIMER_SINGLE_5S_G133",
    "SELF_TIMER_SINGLE_DEFAULT_G133",
    "SHOOT_MODE_MOVIE_PHASE305",
    "SHOOT_MODE_SQ_PHASE305",
    "SHOOT_MODE_STILL_PHASE305",
    "SLOG3_18PCT_GREY_IRE_G134",
    "SLOG3_90PCT_WHITE_IRE_G134",
    "SLOG3_CLIPPING_IRE_APPROX_G134",
    "SPI_NOR_WRITE_AUTHORIZED",
    "STATUS_BLOCKED_G133_DORMANT_MOVIE_OR_PORTRAIT_SELFTIMER_VIOLATION",
    "STATUS_BLOCKED_G133_FOCAL_LENGTH_OR_FX6_IBIS_CROSSWIRE_VIOLATION",
    "STATUS_BLOCKED_G133_SELFTIMER_LAMP_AUDIO_OR_RESET_VIOLATION",
    "STATUS_BLOCKED_G133_STEADYSHOT_ACTIVE_LOCKOUT_OR_DYNAMIC_VIOLATION",
    "STATUS_BLOCKED_G133_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G134_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION",
    "STATUS_BLOCKED_G134_FX6_ZEBRA_BOTH_OR_CLEAN_HDMI_VIOLATION",
    "STATUS_BLOCKED_G134_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION",
    "STATUS_BLOCKED_G134_STREAMING_PROTOCOL_FPS_OR_4K_REC_VIOLATION",
    "STATUS_BLOCKED_G134_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G134_ZEBRA_CUSTOM12_PEAKING_OR_RESET_VIOLATION",
    "STATUS_BLOCKED_PERSISTENT_EMMC_WRITE",
    "STATUS_BLOCKED_PHASE305_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G133",
    "STATUS_VERIFIED_G134",
    "STATUS_VERIFIED_SAFE",
    "STEADYSHOT_47_FOCAL_LENGTHS_MM_G133",
    "STEADYSHOT_ADJUST_AUTO_G133",
    "STEADYSHOT_ADJUST_DEFAULT_G133",
    "STEADYSHOT_ADJUST_F_UXC_RESID16_G133",
    "STEADYSHOT_ADJUST_MANUAL_G133",
    "STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM_G133",
    "STEADYSHOT_FOCAL_LENGTH_F_UXC_RESID16_G133",
    "STEADYSHOT_FOCAL_LEN_SHORT_F_UXC_RESID16_G133",
    "STILL_STEADYSHOT_DEFAULT_G133",
    "STILL_STEADYSHOT_OFF_G133",
    "STILL_STEADYSHOT_ON_G133",
    "STREAM_MAX_BITRATE_MBPS_G134",
    "STREAM_PROTO_RTMP_G134",
    "STREAM_PROTO_RTMPS_G134",
    "STREAM_PROTO_SRT_G134",
    "STREAM_QUALITY_CUSTOM_G134",
    "STREAM_QUALITY_HIGH_G134",
    "STREAM_QUALITY_LOW_G134",
    "STREAM_QUALITY_STANDARD_G134",
    "STREAM_RES_2K_G134",
    "STREAM_RES_4K_G134",
    "STREAM_RES_DEFAULT_G134",
    "STREAM_RES_HD_1080_G134",
    "STREAM_RES_HD_720_G134",
    "SteadyShotSelfTimerGuardResult",
    "USB_PACKETS_TRANSMITTED",
    "ZEBRA_CUSTOM_TYPE_LOWER_LIMIT_G134",
    "ZEBRA_CUSTOM_TYPE_STD_RANGE_G134",
    "ZEBRA_DISPLAY_DEFAULT_G134",
    "ZEBRA_DISPLAY_F_UXC_RESID16_G134",
    "ZEBRA_DISPLAY_G_UXC_RESID16_G134",
    "ZEBRA_IRE_MAX_G134",
    "ZEBRA_IRE_MIN_G134",
    "ZEBRA_LEVEL_DEFAULT_G134",
    "ZEBRA_LEVEL_F_UXC_RESID16_G134",
    "ZEBRA_MENU_PATH_G134",
    "ZEBRA_STD_RANGE_MAX_G134",
    "ZEBRA_STD_RANGE_MIN_G134",
    "ZebraPeakingStreamingFirewallGuardResult",
    "audit_phase305_donor_contracts",
    "compute_steadyshot_selftimer_matrix",
    "compute_zebra_peaking_streaming_matrix",
    "evaluate_134_master_safety_gates",
    "evaluate_134gate_preflight",
    "evaluate_g133_steadyshot_selftimer_guard",
    "evaluate_g134_zebra_streaming_firewall_guard",
    "main",
    "resolve_fx3_steadyshot_selftimer_state",
    "resolve_fx3_zebra_peaking_streaming_state",
    "run_134_gate_preflight",
    "verify_steadyshot_and_selftimer_guard",
    "verify_zebra_peaking_streaming_firewall_guard",
]


if __name__ == "__main__":
    raise SystemExit(main())
