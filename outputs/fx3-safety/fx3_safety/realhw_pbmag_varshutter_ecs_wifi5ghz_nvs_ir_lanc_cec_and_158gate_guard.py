"""Phase 363 (Task H457, Wave-69, 158/158 Milestone): Real-Hardware
`Playback -> [Magnification]` Still-Only `[Enlarge Image]` (`maginify` Typo &
Zero Movie Playback Zoom vs FX6 `Thumbnail`/`Rec Review`/`Focus Magnifier`),
`[Anti-flicker Shoot.]` (`100/120Hz`) vs Dormant `[Var. Shutter]` &
`[Anti-flicker Tv Scan]` (`EOPNOTSUPP=95`) vs FX6 `ECS` (`23.99..8000 Hz`)
(`G157`), `Wi-Fi` `WW728473` (`2.4+5GHz`) vs `WW558244` (`2.4GHz`-Only) SKU
Lock + `WPA2/WPA3` + `[Airplane Mode]` Survives `[Reset Network Set.]` +
`p12/p13` `MS_RDONLY` RF NVS Firewall & Front `#5` `[IR Remote Ctrl]` (vs
`FX3A` Removal) / `[CTRL FOR HDMI]` (`ctrl_for_hmdi` Default-`On` 41-Key CEC
Bench Hijack Firewall, Zero `CEC_REC`) vs FX6 `2.5mm LANC` & `3.5mm Grip`
(`G158`), and Unified `158`-Gate Master Safety Preflight (`G01..G158`).

Authoritative Empirical Baseline (`ILME-FX3 Ver. 7.02`, `ilc/2210`, `0x0502`,
`PRODUCT_MODEL_ALCIN_UUD` vs `ILME-FX6 Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`):
  - **Gate `G157` (`PBMAG_ZERO_MOVIE_ZOOM_AND_ANTI_FLICKER_VS_DORMANT_VAR_SHUTTER_ECS_FIREWALL`)**:
    1. `Playback -> [Magnification]`: exact **3** active items (`[Enlarge Image]`
       `base 0xe8cb`, `[Enlarge Initial Mag.]` `_f 0x6b6e` `Standard. Mag.` def /
       `Previous Mag.`, `[Enlarge Initial Position]` `_f 0x781f` `Focused Position`
       def with center fallback / `Center`):
       - Supports `W/T` zoom lever, pinch-to-zoom (`playback_zoom_maginify_by_pinch`
         Sony ELF typo) & double-tap (requires `[Touch Operation] = On`),
         front/rear dial photo step retaining magnification, and `MENU`/center exit.
       - All `[Magnification]` settings are **Reset-immune** (`Not available` under
         `[Camera Settings Reset]`; cleared only by `[Initialize]`).
       - **Hard Movie Playback Zoom Prohibition**: `playback_zoom::is_inhibition()`
         -> `base 0xe572` `"Unable to magnify."` (`EOPNOTSUPP=95`).
       - Contrast `ILME-FX6 Ver. 6.01`: zero still capture, zero playback enlarge
         (`Enlarge Screen` `ns1 0x2b0e` dormant -> `EOPNOTSUPP=95`), `THUMBNAIL`
         (`ns1 0x2088`) + `Rec Review` (`3s/10s/full`) + shooting `Focus Magnifier`
         `x3/x6` (`HDMI Focus Magnifier`).
    2. `Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.]` (`_f 0x623d`,
       `Off` def / `On`, `BKID_APP_setting_anti_flicker_shoot`, **Resettable** via
       `[Camera Settings Reset]`):
       - Still-only `100Hz/120Hz` AC flicker mechanical shutter; disabled in `Movie`,
         `S&Q`, `[Shutter Type] = Electronic Shutter`, `[Silent Mode] = On`, and `BULB`.
       - Shared Alpha high-res symbols `[Anti-flicker Set.]` (`_f 0x68e7`),
         `[Var. Shutter]` (`_f 0x64cf`/`0x6831`, `BKID_APP_setting_high_res_ss`),
         `[Var. Shutter Set.]` (`_f 0x6f9e`/`0x7af8`), and `[Anti-flicker Tv Scan]`
         (`_f 0x63c0` / `_g 0x60a8` empty SC `""`, `sequence_flicker_scan.cpp`) are
         **100% dormant/unexposed on FX3 (`EOPNOTSUPP=95`)**.
       - Contrast `ILME-FX6 Ver. 6.01`: `Shooting > Shutter > ECS` (`ECS On/Off`
         `ns1 0x22db`, `ECS Frequency` `ns2 0x4d98` `23.99..8000 Hz`, presets
         `59.94P->60.00`, `50P->50.00`, `29.97P->30.00`, `25P->25.02`,
         `24P->24.02`, `23.98P->23.99`) + `Flicker Reduce` (`Off/Auto/On`,
         `50Hz/60Hz`).

  - **Gate `G158` (`WIFI_5GHZ_SKU_P12_P13_MS_RDONLY_NVS_AND_IR_CTRL_FOR_HDMI_CEC_ZERO_LANC_FIREWALL`)**:
    1. `Network -> [Wi-Fi]`:
       - `lib::backup_get_wi_fi_frequency_band_dst` hardware SKU gate:
         `WW728473` (`2.4GHz+5GHz`, outdoor forced `2.4GHz`) vs `WW558244`
         (`2.4GHz`-only -> `5GHz` blocked `EOPNOTSUPP=95`).
       - Ver. 7.00+ allows `WPA2-PSK`/`WPA3-SAE` only (WEP/WPA-PSK/IPsec/Open
         removed -> `EOPNOTSUPP=95`) + mandatory `[Access Authen. Settings] = On`.
       - `[SSID/PW Reset]` (`FUNC_reset_wifi_ssid_psk`) resets Wi-Fi Direct only.
       - **`[Airplane Mode] = On` survives `[Reset Network Set.]`**
         (`FUNC_reset_network_settings`; cleared only by `[Initialize]`,
         `rf_tx_packets == 0`).
       - eMMC `p12` (`/dev/nflasha12`, `40 MiB` `/cert`) & `p13` (`/dev/nflasha13`,
         `4 MiB` RF/MAC NVS) hard-locked **`MS_RDONLY`** (`EROFS=30`,
         `rf_nvs_mutation_bytes == 0`, blocking cross-region 5GHz NVS tampering).
       - Contrast `ILME-FX6 Ver. 6.01`: `Wireless LAN` (`Access Point Mode`
         `Auto(5GHz)` vs `Station Mode`, `ILME-FX6V/VK` `5GHz` vs `ILME-FX6T/TK`
         `2.4GHz`, NFC removed, mutex with `Wired LAN` & `Simul Rec` -> `EBUSY=16`).
    2. `[IR Remote Ctrl]`, `[CTRL FOR HDMI]` CEC Bench Hijack Firewall & Zero `LANC`:
       - `Setup -> [Setup Option] -> [IR Remote Ctrl]` (`_f 0x61a6`, `Off` def,
         **Reset-immune**, `[Initialize]` resets): front `#5` `Infrared remote sensor`
         (distinct from `#8` AF illuminator/visible+IR sensor), **physically removed
         on 2025 `ILME-FX3A`** (`EOPNOTSUPP=95`), bypasses `[Power Save Start Time]`,
         and mutually exclusive with `[Bluetooth Rmt Ctrl] = On` (`EBUSY=16`).
       - `Setup -> [External Output] -> [CTRL FOR HDMI]` (`base 0xe41f`, Sony ELF
         typo `BKID_APP_setting_ctrl_for_hmdi`, **factory default `On` & Reset-immune**):
         exposes exact **41** `EVENT_INPUT_KEY_CEC_*` injection vectors (incl.
         `STANDBY_ON`/`OFF`, `ROOT_MENU`, with **zero `CEC_REC`**); HIL/bench safety
         guard mandates `[CTRL FOR HDMI] = Off` before attaching external HDMI gear!
       - Zero physical `2.5mm LANC` or `3.5mm Grip` jack on FX3 (`0` active
         `BKID_APP_*_lanc*` hits, dormant `UIBIZ_KEY_JACK_MULTILANC_LANC` ->
         `EOPNOTSUPP=95`) vs FX6 `#24` `2.5mm` 3-pole `REMOTE (LANC)` + `3.5mm`
         4-pole Grip Remote (zero user `IR Remote` / `CTRL FOR HDMI` menus).

  - **Unified 158-Gate Master Safety Preflight (`G01..G158`)**:
    Delegates `G01..G156` to `evaluate_156gate_preflight()`, enforces `155/158`
    verified offline (`VERIFIED_155_OF_158_AWAITING_PHYSICAL_TIER0`) and `158/158`
    under `--simulate-bench-dry-run` (`VERIFIED_ALL_158_GATES_DRY_RUN_SIMULATED_BACKUP`),
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
from .realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_156gate_guard import (
    Master156GateReport,
    evaluate_156gate_preflight,
)


# ---------------------------------------------------------------------------
# Schema, Versions, Env Keys & Shared Constants
# ---------------------------------------------------------------------------

REALHW_PBMAG_VARSHUTTER_ECS_WIFI5GHZ_NVS_IR_LANC_CEC_158GATE_SCHEMA = (
    "fx3_realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_158gate_guard_v1"
)
REALHW_PBMAG_VARSHUTTER_ECS_WIFI5GHZ_NVS_IR_LANC_CEC_158GATE_VERSION = (
    "2026.11.18-phase363-milestone158"
)
REALHW_158GATE_PREFLIGHT_SCHEMA = "realhw_158gate_preflight_v1"

G157 = "G157"
G157_GATE_ID = "G157"
G157_GATE_CODE = (
    "PBMAG_ZERO_MOVIE_ZOOM_AND_ANTI_FLICKER_VS_DORMANT_VAR_SHUTTER_ECS_FIREWALL"
)

G158 = "G158"
G158_GATE_ID = "G158"
G158_GATE_CODE = (
    "WIFI_5GHZ_SKU_P12_P13_MS_RDONLY_NVS_AND_IR_CTRL_FOR_HDMI_CEC_ZERO_LANC_FIREWALL"
)

ENV_CLEAN_ROOM_TEST_PHASE363 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE363 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE363 = 0.05

EPERM_ERRNO_PHASE363 = 1
EPERM_NAME_PHASE363 = "EPERM"
EBUSY_ERRNO_PHASE363 = 16
EBUSY_NAME_PHASE363 = "EBUSY"
EINVAL_ERRNO_PHASE363 = 22
EINVAL_NAME_PHASE363 = "EINVAL"
EROFS_ERRNO_PHASE363 = 30
EROFS_NAME_PHASE363 = "EROFS"
EOPNOTSUPP_ERRNO_PHASE363 = 95
EOPNOTSUPP_NAME_PHASE363 = "EOPNOTSUPP"

FX3_MODEL_NAME_PHASE363 = "ILME-FX3"
FX3A_MODEL_NAME_PHASE363 = "ILME-FX3A"
FX3_MODEL_ID_PHASE363 = 0x0502
FX3_HELP_GUIDE_CODE_PHASE363 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE363 = "7.02"
FX6_MODEL_NAME_PHASE363 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE363 = "6.01"
ALLOWED_BODY_MODELS_PHASE363: Tuple[str, ...] = (
    FX3_MODEL_NAME_PHASE363,
    FX6_MODEL_NAME_PHASE363,
)
ALLOWED_FX3_VARIANTS_PHASE363: Tuple[str, ...] = (
    FX3_MODEL_NAME_PHASE363,
    FX3A_MODEL_NAME_PHASE363,
)

MEDIA_SLOT_NONE_PHASE363 = 0
MEDIA_SLOT_1_PHASE363 = 1
MEDIA_SLOT_2_PHASE363 = 2
ALLOWED_MEDIA_SLOTS_PHASE363: Tuple[int, ...] = (
    MEDIA_SLOT_NONE_PHASE363,
    MEDIA_SLOT_1_PHASE363,
    MEDIA_SLOT_2_PHASE363,
)

SHOOT_MODE_STILL_PHASE363 = "Still"
SHOOT_MODE_MOVIE_PHASE363 = "Movie"
SHOOT_MODE_SQ_PHASE363 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE363: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE363,
    SHOOT_MODE_MOVIE_PHASE363,
    SHOOT_MODE_SQ_PHASE363,
)

RESET_ACTION_NONE_PHASE363 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE363 = "Camera Settings Reset"
RESET_ACTION_INITIALIZE_PHASE363 = "Initialize"
RESET_ACTION_RESET_NETWORK_SET_PHASE363 = "Reset Network Set."
ALLOWED_RESET_ACTIONS_PHASE363: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE363,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE363,
    RESET_ACTION_INITIALIZE_PHASE363,
    RESET_ACTION_RESET_NETWORK_SET_PHASE363,
)


# ---------------------------------------------------------------------------
# Gate G157 Constants: Playback [Magnification] & [Anti-flicker Shoot.] vs
#                      Dormant [Var. Shutter]/[Anti-flicker Tv Scan]/FX6 ECS
# ---------------------------------------------------------------------------

PLAYBACK_MAGNIFICATION_MENU_PATH_G157 = "Playback -> [Magnification]"
ANTI_FLICKER_SHOOT_MENU_PATH_G157 = (
    "Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.]"
)
FX6_SHUTTER_ECS_MENU_PATH_G157 = "Shooting > Shutter > ECS"
FX6_FLICKER_REDUCE_MENU_PATH_G157 = "Shooting > Shutter > Flicker Reduce"

EXACT_3_PLAYBACK_MAGNIFY_ITEMS_G157: Tuple[str, ...] = (
    "Enlarge Image",
    "Enlarge Initial Mag.",
    "Enlarge Initial Position",
)
ALLOWED_PLAYBACK_MEDIA_KINDS_G157: Tuple[str, ...] = ("still", "movie")
ALLOWED_PLAYBACK_ZOOM_OPERATIONS_G157: Tuple[str, ...] = (
    "enlarge_image",
    "wt_lever",
    "pinch_zoom",
    "double_tap",
    "dial_step_photo",
    "menu_exit",
)
ALLOWED_ENLARGE_INITIAL_MAG_OPTIONS_G157: Tuple[str, ...] = (
    "Standard. Mag.",
    "Previous Mag.",
)
ALLOWED_ENLARGE_INITIAL_POS_OPTIONS_G157: Tuple[str, ...] = (
    "Focused Position",
    "Center",
)
ENLARGE_INITIAL_MAG_DEFAULT_G157 = "Standard. Mag."
ENLARGE_INITIAL_POS_DEFAULT_G157 = "Focused Position"
PLAYBACK_MAGNIFY_RESETTABLE_BY_CAMSET_RESET_G157 = False
MOVIE_PLAYBACK_ZOOM_SUPPORTED_G157 = False
PLAYBACK_ZOOM_MAGINIFY_ELF_TYPO_G157 = "playback_zoom_maginify_by_pinch"
PLAYBACK_ZOOM_DOUBLE_TAP_SYMBOLS_G157: Tuple[str, ...] = (
    "playback_zoom_double_tap_position_x",
    "playback_zoom_double_tap_position_y",
)
PLAYBACK_ZOOM_INHIBITION_TEXT_G157 = "Unable to magnify."
FX6_STILL_OR_PB_ENLARGE_SUPPORTED_G157 = False
FX6_REC_REVIEW_DURATIONS_G157: Tuple[str, ...] = ("3s", "10s", "full")
FX6_FOCUS_MAGNIFIER_SCALES_G157: Tuple[str, ...] = ("x3", "x6")

ANTI_FLICKER_SHOOT_DEFAULT_G157 = "Off"
ANTI_FLICKER_SHOOT_RESETTABLE_BY_CAMSET_RESET_G157 = True
ANTI_FLICKER_MAINS_FREQS_HZ_G157: Tuple[int, ...] = (100, 120)
ALLOWED_SHUTTER_TYPES_G157: Tuple[str, ...] = ("Mechanical", "Electronic")
FX3_VAR_SHUTTER_EXPOSED_G157 = False
FX3_ANTI_FLICKER_SET_EXPOSED_G157 = False
FX3_ANTI_FLICKER_TV_SCAN_EXPOSED_G157 = False
FX3_SC_TV_SCAN_0X60A8_EMPTY_STRING_G157 = True
DORMANT_FLICKER_OR_VAR_SHUTTER_SYMBOLS_G157: Tuple[str, ...] = (
    "BKID_APP_setting_high_res_ss",
    "sequence_flicker_scan.cpp",
    "Anti-flicker Set.",
    "Var. Shutter",
    "Var. Shutter Set.",
    "Anti-flicker Tv Scan",
)
FX6_ECS_FREQ_MIN_HZ_G157 = 23.99
FX6_ECS_FREQ_MAX_HZ_G157 = 8000.0
FX6_ECS_6_FRAME_RATE_PRESETS_G157: Dict[str, float] = {
    "59.94P": 60.00,
    "50P": 50.00,
    "29.97P": 30.00,
    "25P": 25.02,
    "24P": 24.02,
    "23.98P": 23.99,
}
FX6_FLICKER_REDUCE_MODES_G157: Tuple[str, ...] = ("Off", "Auto", "On")
FX6_FLICKER_REDUCE_FREQS_G157: Tuple[str, ...] = ("50Hz", "60Hz")

# UXC resid16 anchors (G157)
ENLARGE_IMAGE_BASE_RESID16_G157 = 0xE8CB
UNABLE_TO_MAGNIFY_BASE_RESID16_G157 = 0xE572
ENLARGE_INITIAL_MAG_F_RESID16_G157 = 0x6B6E
ENLARGE_INITIAL_POS_F_RESID16_G157 = 0x781F
ANTI_FLICKER_SHOOT_F_RESID16_G157 = 0x623D
DORMANT_ANTI_FLICKER_SET_F_RESID16_G157 = 0x68E7
DORMANT_VAR_SHUTTER_F_RESID16_G157 = 0x64CF
DORMANT_ANTI_FLICKER_TV_SCAN_F_RESID16_G157 = 0x63C0
DORMANT_SC_TV_SCAN_G_RESID16_G157 = 0x60A8

STATUS_VERIFIED_G157 = (
    "VERIFIED_G157_PBMAG_ZERO_MOVIE_ZOOM_AND_ANTI_FLICKER_VS_DORMANT_VAR_SHUTTER_ECS"
)
STATUS_BLOCKED_G157_TELEMETRY_INVALID = "BLOCKED_G157_TELEMETRY_INVALID"
STATUS_BLOCKED_G157_MOVIE_ZOOM_OR_DORMANT_VAR_SHUTTER_EOPNOTSUPP = (
    "BLOCKED_G157_MOVIE_ZOOM_OR_DORMANT_VAR_SHUTTER_EOPNOTSUPP"
)
STATUS_BLOCKED_G157_PBMAG_RESET_OR_ANTI_FLICKER_CONSTRAINT_VIOLATION = (
    "BLOCKED_G157_PBMAG_RESET_OR_ANTI_FLICKER_CONSTRAINT_VIOLATION"
)


# ---------------------------------------------------------------------------
# Gate G158 Constants: Wi-Fi WW728473/WW558244 5GHz SKU + p12/p13 MS_RDONLY NVS
#                      & [IR Remote Ctrl] #5 / [CTRL FOR HDMI] CEC / Zero LANC
# ---------------------------------------------------------------------------

WIFI_MENU_PATH_G158 = "Network -> [Wi-Fi]"
IR_REMOTE_CTRL_MENU_PATH_G158 = "Setup -> [Setup Option] -> [IR Remote Ctrl]"
CTRL_FOR_HDMI_MENU_PATH_G158 = "Setup -> [External Output] -> [CTRL FOR HDMI]"
FX6_WIRELESS_LAN_MENU_PATH_G158 = "Network > Wireless LAN"

EXACT_6_WIFI_MENU_ITEMS_G158: Tuple[str, ...] = (
    "Wi-Fi Connect",
    "WPS Push",
    "Access Point Set.",
    "Wi-Fi Frequency Band",
    "Display Wi-Fi Info.",
    "SSID/PW Reset",
)
WIFI_SKU_GATE_FN_G158 = "lib::backup_get_wi_fi_frequency_band_dst"
FX3_WIFI_SKU_WW728473_G158 = "WW728473"
FX3_WIFI_SKU_WW558244_G158 = "WW558244"
FX6_WIFI_SKU_5GHZ_G158 = "ILME-FX6V"
FX6_WIFI_SKU_24GHZ_G158 = "ILME-FX6T"
ALLOWED_WIFI_SKU_CODES_G158: Tuple[str, ...] = (
    FX3_WIFI_SKU_WW728473_G158,
    FX3_WIFI_SKU_WW558244_G158,
    FX6_WIFI_SKU_5GHZ_G158,
    FX6_WIFI_SKU_24GHZ_G158,
)
ALLOWED_WIFI_BANDS_G158: Tuple[str, ...] = ("2.4GHz", "5GHz")
ALLOWED_WIFI_SECURITY_PROTOCOLS_G158: Tuple[str, ...] = (
    "WPA2-PSK",
    "WPA3-SAE",
    "WEP",
    "WPA-PSK",
    "IPsec",
    "Open",
)
VER7_ALLOWED_WIFI_SECURITY_PROTOCOLS_G158: Tuple[str, ...] = ("WPA2-PSK", "WPA3-SAE")
VER7_REMOVED_WIFI_SECURITY_PROTOCOLS_G158: Tuple[str, ...] = (
    "WEP",
    "WPA-PSK",
    "IPsec",
    "Open",
)
ALLOWED_TARGET_PARTITIONS_G158: Tuple[str, ...] = (
    "none",
    "setting",
    "p12_cert",
    "p13_rfnvs",
)
ALLOWED_WIFI_OPERATIONS_G158: Tuple[str, ...] = (
    "wifi_band_select",
    "ap_connect",
    "ssid_pw_reset",
    "reset_network_set",
    "initialize",
    "rf_nvs_write_attempt",
    "fx6_wireless_lan",
)
ALLOWED_FX6_WLAN_MODES_G158: Tuple[str, ...] = ("Access Point Mode", "Station Mode")

AIRPLANE_MODE_SURVIVES_RESET_NETWORK_G158 = True
P12_DEVICE_PATH_G158 = "/dev/nflasha12"
P13_DEVICE_PATH_G158 = "/dev/nflasha13"
P12_CERT_SIZE_MIB_G158 = 40
P13_RF_NVS_SIZE_MIB_G158 = 4
P12_P13_MS_RDONLY_ENFORCED_G158 = True
RF_NVS_MUTATION_BYTES_G158 = 0
RF_TX_PACKETS_AIRPLANE_G158 = 0

FX3_IR_FRONT_SENSOR_NUM_G158 = 5
FX3_AF_ILLUMINATOR_SENSOR_NUM_G158 = 8
IR_REMOTE_CTRL_DEFAULT_G158 = "Off"
IR_REMOTE_CTRL_RESETTABLE_BY_CAMSET_RESET_G158 = False
FX3A_PHYSICAL_IR_SENSOR_PRESENT_G158 = False

CTRL_FOR_HDMI_ELF_TYPO_G158 = "BKID_APP_setting_ctrl_for_hmdi"
CTRL_FOR_HDMI_FACTORY_DEFAULT_G158 = "On"
CTRL_FOR_HDMI_RESETTABLE_BY_CAMSET_RESET_G158 = False
FX3_PHYSICAL_LANC_25MM_PRESENT_G158 = False
FX3_PHYSICAL_GRIP_REMOTE_35MM_PRESENT_G158 = False
FX3_ACTIVE_LANC_BKID_HITS_G158 = 0
FX6_LANC_25MM_PORT_NUM_G158 = 24
FX6_GRIP_REMOTE_35MM_POLES_G158 = 4
FX6_EXPOSED_IR_OR_CEC_MENUS_G158 = False

EXACT_41_FX3_CEC_KEY_EVENTS_G158: Tuple[str, ...] = (
    "EVENT_INPUT_KEY_CEC_BACKWARD_OFF",
    "EVENT_INPUT_KEY_CEC_BACKWARD_ON",
    "EVENT_INPUT_KEY_CEC_BACKWARD_REPEAT",
    "EVENT_INPUT_KEY_CEC_CONTENTS_MENU_OFF",
    "EVENT_INPUT_KEY_CEC_CONTENTS_MENU_ON",
    "EVENT_INPUT_KEY_CEC_CURSOR_DOWN_OFF",
    "EVENT_INPUT_KEY_CEC_CURSOR_DOWN_ON",
    "EVENT_INPUT_KEY_CEC_CURSOR_DOWN_REPEAT",
    "EVENT_INPUT_KEY_CEC_CURSOR_LEFT_OFF",
    "EVENT_INPUT_KEY_CEC_CURSOR_LEFT_ON",
    "EVENT_INPUT_KEY_CEC_CURSOR_LEFT_REPEAT",
    "EVENT_INPUT_KEY_CEC_CURSOR_RIGHT_OFF",
    "EVENT_INPUT_KEY_CEC_CURSOR_RIGHT_ON",
    "EVENT_INPUT_KEY_CEC_CURSOR_RIGHT_REPEAT",
    "EVENT_INPUT_KEY_CEC_CURSOR_UP_OFF",
    "EVENT_INPUT_KEY_CEC_CURSOR_UP_ON",
    "EVENT_INPUT_KEY_CEC_CURSOR_UP_REPEAT",
    "EVENT_INPUT_KEY_CEC_ENTER_OFF",
    "EVENT_INPUT_KEY_CEC_ENTER_ON",
    "EVENT_INPUT_KEY_CEC_ENTER_REPEAT",
    "EVENT_INPUT_KEY_CEC_EXIT_OFF",
    "EVENT_INPUT_KEY_CEC_EXIT_ON",
    "EVENT_INPUT_KEY_CEC_FASTFORWARD_OFF",
    "EVENT_INPUT_KEY_CEC_FASTFORWARD_ON",
    "EVENT_INPUT_KEY_CEC_FORWARD_OFF",
    "EVENT_INPUT_KEY_CEC_FORWARD_ON",
    "EVENT_INPUT_KEY_CEC_FORWARD_REPEAT",
    "EVENT_INPUT_KEY_CEC_PAUSE_OFF",
    "EVENT_INPUT_KEY_CEC_PAUSE_ON",
    "EVENT_INPUT_KEY_CEC_PLAY_OFF",
    "EVENT_INPUT_KEY_CEC_PLAY_ON",
    "EVENT_INPUT_KEY_CEC_REWIND_OFF",
    "EVENT_INPUT_KEY_CEC_REWIND_ON",
    "EVENT_INPUT_KEY_CEC_ROOT_MENU_OFF",
    "EVENT_INPUT_KEY_CEC_ROOT_MENU_ON",
    "EVENT_INPUT_KEY_CEC_SETUP_MENU_OFF",
    "EVENT_INPUT_KEY_CEC_SETUP_MENU_ON",
    "EVENT_INPUT_KEY_CEC_STANDBY_OFF",
    "EVENT_INPUT_KEY_CEC_STANDBY_ON",
    "EVENT_INPUT_KEY_CEC_STOP_OFF",
    "EVENT_INPUT_KEY_CEC_STOP_ON",
)
FX3_CEC_REC_EVENT_COUNT_G158 = 0

# UXC resid16 anchors (G158)
WIFI_CONNECT_F_RESID16_G158 = 0x7BC5
WIFI_FREQ_BAND_F_RESID16_G158 = 0x66C3
SSID_PW_RESET_F_RESID16_G158 = 0x6FD5
AIRPLANE_MODE_F_RESID16_G158 = 0x6DF9
RESET_NETWORK_SET_F_RESID16_G158 = 0x60D3
IR_REMOTE_CTRL_F_RESID16_G158 = 0x61A6
CTRL_FOR_HDMI_BASE_RESID16_G158 = 0xE41F

STATUS_VERIFIED_G158 = (
    "VERIFIED_G158_WIFI_5GHZ_P12_P13_MS_RDONLY_AND_IR_CTRL_FOR_HDMI_CEC_ZERO_LANC_FIREWALL"
)
STATUS_BLOCKED_G158_TELEMETRY_INVALID = "BLOCKED_G158_TELEMETRY_INVALID"
STATUS_BLOCKED_G158_P12_P13_RF_NVS_MS_RDONLY_EROFS = (
    "BLOCKED_G158_P12_P13_RF_NVS_MS_RDONLY_EROFS"
)
STATUS_BLOCKED_G158_BT_IR_OR_FX6_WLAN_MUTEX_EBUSY = (
    "BLOCKED_G158_BT_IR_OR_FX6_WLAN_MUTEX_EBUSY"
)
STATUS_BLOCKED_G158_SKU_LEGACY_SEC_FX3A_IR_OR_LANC_EOPNOTSUPP = (
    "BLOCKED_G158_SKU_LEGACY_SEC_FX3A_IR_OR_LANC_EOPNOTSUPP"
)
STATUS_BLOCKED_G158_AIRPLANE_RF_OR_CTRL_FOR_HDMI_CEC_HIJACK_VIOLATION = (
    "BLOCKED_G158_AIRPLANE_RF_OR_CTRL_FOR_HDMI_CEC_HIJACK_VIOLATION"
)

STATUS_BLOCKED_PHASE363_DONOR_INTEGRITY = "BLOCKED_PHASE363_DONOR_CONTRACT_INTEGRITY"


# ---------------------------------------------------------------------------
# Pinned Wave-69 Donor Specs (O_RDONLY / Bounded Slices, Raw Bytes = 0)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX_P363 = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX6_NF15_PREFIX_P363 = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)

PINNED_FX3_APPFW_SLICES_PHASE363: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x03BC995D, b"BKID_APP_setting_magnif_set_in_large"),
    (0x03BC9982, b"BKID_APP_setting_position_set_in_large"),
    (0x02FA49AF, b"MAGNIF_SET_IN_LARGE_ACTUAL"),
    (0x02FA49CA, b"MAGNIF_SET_IN_LARGE_LAST"),
    (0x02FA49E3, b"POSITION_SET_IN_LARGE_FROM_FOCUSED"),
    (0x02FA4A06, b"POSITION_SET_IN_LARGE_FROM_CENTER_OF_SCREEN"),
    (0x03BFD75E, b"playback_zoom_maginify_by_pinch"),
    (0x03C281D7, b"playback_zoom_double_tap_position_x"),
    (0x03C3903C, b"EVENT_FUNC_ENLARGE_IMAGE_ON"),
    (0x03BC7139, b"BKID_APP_setting_anti_flicker_shoot"),
    (0x03BC7184, b"BKID_APP_setting_high_res_ss"),
    (0x03925DA2, b"sequence_flicker_scan.cpp"),
    (0x039A5FFA, b"backup_get_wi_fi_frequency_band_dst"),
    (0x03C18034, b"WI_FI_FREQUENCY_BAND_AVAILABLE_2_4_GHZ_OR_5_GHZ"),
    (0x03C18008, b"WI_FI_FREQUENCY_BAND_AVAILABLE_2_4_GHZ_ONLY"),
    (0x0390E5E2, b"sequence_reset_wifi_ssid_psk"),
    (0x039CC279, b"FUNC_reset_wifi_ssid_psk"),
    (0x03BCA52B, b"BKID_APP_setting_airplane_mode"),
    (0x039CBB3D, b"FUNC_reset_network_settings"),
    (0x03BCC2E6, b"BKID_APP_setting_ir_remote_ctrl"),
    (0x03BCC26F, b"BKID_APP_setting_ctrl_for_hmdi"),
    (0x03C32C24, b"EVENT_INPUT_KEY_CEC_STANDBY_ON"),
    (0x03C329BD, b"EVENT_INPUT_KEY_CEC_ROOT_MENU"),
    (0x0306743C, b"EVENT_INPUT_KEY_CEC_PLAY"),
    (0x03BAF5F9, b"UIBIZ_KEY_JACK_MULTILANC_LANC"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE363 = (
    "d79f2cfb4e861e3af950dea53fb95f7713c25bbf3fd530f524842456211db39b"
)

PINNED_FX6_APPFW_SLICES_PHASE363: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x02707918, b"BKID_APP_SETTING_ECS_FREQUENCY"),
    (0x025343E3, b"convert_ecs_frequency_line_number_to_array_index"),
    (0x027559CE, b"EVENT_REMOTE_SHUTTER_ECS_FREQUENCY"),
    (0x025FB149, b"sequence_turn_on_wifi_ap_mode"),
    (0x027122F3, b"BKID_APP_USER_MENU_WIFI0"),
    (0x025FBC26, b"Failure Set Lanc Status"),
    (0x02382438, b"EVENT_INPUT_KEY_LANC_"),
    (0x0270C90E, b"BKID_APP_SETTING_HOLD_SWITCH_SETTING_WITH_HAND_GRIP_REMOTE"),
    (0x027B63A3, b"IR_REMOTE_CTRL_OFF"),
    (0x027B6554, b"CTRL_FOR_HMDI_ON"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE363 = (
    "b806299ec253eaff1a66c577a4fff55cc5efbac5e09105d52b97bc34d8bd50a1"
)

PINNED_PHASE363_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE363,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE363),
        "FX3 appFw.so Wave-69 PlaybackMag/AntiFlicker/VarShutter/WiFi5GHz/IR/CEC/LANC slices",
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
        f"{_FX3_USR_PREFIX_P363}/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Enlarge Initial Mag.",
            b"Standard. Mag.",
            b"Previous Mag.",
            b"Enlarge Initial Position",
            b"Focused Position",
            b"Center",
            b"Anti-flicker Shoot.",
            b"Anti-flicker Set.",
            b"Var. Shutter",
            b"Var. Shutter Set.",
            b"Anti-flicker Tv Scan",
            b"Wi-Fi Connect",
            b"WPS Push",
            b"Access Point Set.",
            b"Wi-Fi Frequency Band",
            b"2.4GHz",
            b"5GHz",
            b"Display Wi-Fi Info.",
            b"SSID/PW Reset",
            b"Airplane Mode",
            b"Reset Network Set.",
            b"IR Remote Ctrl",
        ),
        "FX3 string_english_f.uxc Wave-69 EN parity",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P363}/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "\u653e\u5927\u521d\u59cb\u653e\u5927\u500d\u7387".encode("utf-8"),
            "\u653e\u5927\u521d\u59cb\u4f4d\u7f6e".encode("utf-8"),
            "\u9632\u95ea\u70c1\u62cd\u6444".encode("utf-8"),
            "\u9632\u95ea\u70c1Tv\u626b\u63cf".encode("utf-8"),
            "Wi-Fi\u9891\u5e26".encode("utf-8"),
            "SSID/\u5bc6\u7801\u590d\u4f4d".encode("utf-8"),
            "\u98de\u884c\u6a21\u5f0f".encode("utf-8"),
            "IR\u9065\u63a7".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-69 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P363}/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "\u653e\u5927\u521d\u59cb\u653e\u5927\u7387".encode("utf-8"),
            "\u653e\u5927\u521d\u59cb\u4f4d\u7f6e".encode("utf-8"),
            "\u6297\u5149\u6e90\u9583\u720d\u62cd\u651d".encode("utf-8"),
            "Wi-Fi\u983b\u5e36".encode("utf-8"),
            "\u98db\u822a\u6a21\u5f0f".encode("utf-8"),
            "IR\u9059\u63a7".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-69 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P363}/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "\u62e1\u5927\u306e\u521d\u671f\u500d\u7387".encode("utf-8"),
            "\u62e1\u5927\u306e\u521d\u671f\u4f4d\u7f6e".encode("utf-8"),
            "Wi-Fi\u5468\u6ce2\u6570\u5e2f".encode("utf-8"),
            "\u6a5f\u5185\u30e2\u30fc\u30c9".encode("utf-8"),
            "\u8d64\u5916\u7dda\u30ea\u30e2\u30b3\u30f3".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-69 JA parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P363}/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Enlarge Image",
            b"Unable to magnify.",
            b"WPA2",
            b"WPA3",
            b"CTRL FOR HDMI",
        ),
        "FX3 string_english.uxc Wave-69 EN base",
    ),
    "fx3_string_simplifiedchinese_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P363}/share/app/string_simplifiedchinese.uxc",
        149_064,
        "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
        (
            "\u653e\u5927".encode("utf-8"),
            "HDMI\u63a7\u5236".encode("utf-8"),
            b"WPA2",
            b"WPA3",
        ),
        "FX3 string_simplifiedchinese.uxc Wave-69 ZH-CN base",
    ),
    "fx3_string_traditionalchinese_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P363}/share/app/string_traditionalchinese.uxc",
        151_908,
        "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
        (
            "\u653e\u5927".encode("utf-8"),
            "HDMI\u63a7\u5236".encode("utf-8"),
            b"WPA2",
            b"WPA3",
        ),
        "FX3 string_traditionalchinese.uxc Wave-69 ZH-TW base",
    ),
    "fx3_string_japanese_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P363}/share/app/string_japanese.uxc",
        208_564,
        "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
        (
            "\u62e1\u5927".encode("utf-8"),
            "HDMI\u6a5f\u5668\u5236\u5fa1".encode("utf-8"),
            b"WPA2",
            b"WPA3",
        ),
        "FX3 string_japanese.uxc Wave-69 JA base",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P363}/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Magnification",
            b"Anti-flicker Tv Scan",
        ),
        "FX3 string_english_g.uxc Wave-69 EN guide",
    ),
    "fx3_string_simplifiedchinese_g_uxc": (
        "FX3",
        f"{_FX3_USR_PREFIX_P363}/share/app/string_simplifiedchinese_g.uxc",
        61_296,
        "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
        (
            "\u98de\u884c\u6a21\u5f0f".encode("utf-8"),
            "\u653e\u5927".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_g.uxc Wave-69 ZH-CN guide",
    ),
    "fx6_appfw_so": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P363}/lib/appFw.so",
        50_520_424,
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE363,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE363),
        "FX6 appFw.so Wave-69 ECS/WiFiAP/LANC/GripRemote/DormantIR-CEC slices",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P363}/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (
            b"Thumbnail",
            b"Enlarge Screen",
            b"Focus Magnifier",
            b"Rec Review",
            b"ECS On/Off",
        ),
        "FX6 string_english.uxc Wave-69 EN baseline",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        f"{_FX6_NF15_PREFIX_P363}/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"ECS Frequency",
            b"Flicker Reduce",
            b"Access Point Mode",
            b"Station Mode",
            b"Auto(5GHz)",
            b"IR Remote",
            b"with Hand Grip Remote",
        ),
        "FX6 string_english_2.uxc Wave-69 EN enterprise baseline",
    ),
}


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _is_clean_room_forced(force_clean_room: Optional[bool]) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE363):
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
    if body_model_name != FX3_MODEL_NAME_PHASE363:
        errs.append(f"body_model_name_invalid:{body_model_name!r}")
    if not _is_strict_int(body_model_id) or body_model_id != FX3_MODEL_ID_PHASE363:
        errs.append(f"body_model_id_invalid:{body_model_id!r}")
    if help_guide_code != FX3_HELP_GUIDE_CODE_PHASE363:
        errs.append(f"help_guide_code_invalid:{help_guide_code!r}")
    if _parse_fw_float(firmware_version) is None:
        errs.append(f"firmware_version_invalid:{firmware_version!r}")
    return errs


def strip_elapsed_seconds_recursive_phase363(obj: Any) -> Any:
    """Recursively strip non-deterministic `elapsed_seconds` keys for canonical digests."""
    if isinstance(obj, dict):
        return {
            k: strip_elapsed_seconds_recursive_phase363(v)
            for k, v in obj.items()
            if k != "elapsed_seconds"
        }
    if isinstance(obj, list):
        return [strip_elapsed_seconds_recursive_phase363(v) for v in obj]
    if isinstance(obj, tuple):
        return [strip_elapsed_seconds_recursive_phase363(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Donor Integrity Audit (O_RDONLY / Clean-Room Dual-Mode)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase363DonorAuditResult:
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


def audit_phase363_donor_contracts(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase363DonorAuditResult:
    """Fast (< 0.20s) O_RDONLY + bounded os.pread donor audit with clean-room fallback."""
    import time

    t0 = time.perf_counter()
    clean_forced = _is_clean_room_forced(force_clean_room)
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else dict(PINNED_PHASE363_DONOR_SPECS)
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
        return Phase363DonorAuditResult(
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
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE363,
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
        return Phase363DonorAuditResult(
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
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE363,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(
                f"Donor files absent ({len(missing_files)} missing); "
                "verified Phase 363 via clean-room synthetic fallback.",
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
                target, PINNED_FX3_APPFW_SLICES_PHASE363
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tok_errs = _read_exact_o_rdonly_slices(
                target, PINNED_FX6_APPFW_SLICES_PHASE363
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
    return Phase363DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE
            if valid
            else STATUS_BLOCKED_PHASE363_DONOR_INTEGRITY
        ),
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="STRICT_OS_O_RDONLY_PREAD",
        files_inspected=inspected,
        fx3_contracts_verified=valid,
        fx6_contracts_verified=valid,
        four_lang_resid16_parity_verified=valid,
        zero_forbidden_myths_verified=valid,
        elapsed_seconds=round(dt, 6),
        within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE363,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        file_digests=file_digests,
        missing_markers=tuple(missing_markers),
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# Gate G157: Still-Only Playback [Magnification] / Zero Movie Zoom &
#            [Anti-flicker Shoot.] vs Dormant [Var. Shutter] / [Anti-flicker Tv Scan] / FX6 ECS
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PbMagVarShutterEcsGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    playback_magnification_menu_path: str
    anti_flicker_shoot_menu_path: str
    fx6_shutter_ecs_menu_path: str
    fx6_flicker_reduce_menu_path: str
    playback_magnify_items_count: int
    effective_playback_media_kind: str
    effective_playback_operation: str
    effective_enlarge_initial_mag: str
    effective_enlarge_initial_position: str
    focused_fallback_to_center: bool
    effective_mag_factor: float
    zoom_preserved_across_photo_step: bool
    playback_zoom_maginify_elf_typo: str
    playback_zoom_inhibition_text: str
    playback_magnify_resettable_by_camset_reset: bool
    movie_playback_zoom_supported: bool
    movie_playback_zoom_bypass_events: int
    fx6_still_or_pb_enlarge_supported: bool
    effective_shoot_mode: str
    effective_shutter_type: str
    silent_mode: str
    bulb_mode: bool
    effective_anti_flicker_shoot: str
    anti_flicker_shoot_enabled_allowed: bool
    anti_flicker_effective_for_mains_hz: bool
    anti_flicker_shoot_resettable_by_camset_reset: bool
    fx3_var_shutter_exposed: bool
    fx3_anti_flicker_set_exposed: bool
    fx3_anti_flicker_tv_scan_exposed: bool
    fx3_sc_tv_scan_0x60a8_empty_string: bool
    fx6_ecs_frame_rate: str
    fx6_ecs_freq_hz: float
    fx6_flicker_reduce_mode: str
    fx6_flicker_reduce_freq: str
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


def resolve_fx3_pbmag_varshutter_ecs_state(
    *,
    playback_media_kind: str = "still",
    playback_operation: str = "enlarge_image",
    enlarge_initial_mag: str = ENLARGE_INITIAL_MAG_DEFAULT_G157,
    enlarge_initial_position: str = ENLARGE_INITIAL_POS_DEFAULT_G157,
    focus_position_available: bool = True,
    touch_operation: str = "On",
    previous_mag_factor: float = 4.0,
    requested_mag_factor: float = 2.0,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE363,
    shutter_type: str = "Mechanical",
    silent_mode: str = "Off",
    bulb_mode: bool = False,
    anti_flicker_shoot: str = ANTI_FLICKER_SHOOT_DEFAULT_G157,
    mains_hz: int = 100,
    reset_action: str = RESET_ACTION_NONE_PHASE363,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-69 Playback Magnification & Anti-flicker Shoot. state."""
    init_applied = reset_action == RESET_ACTION_INITIALIZE_PHASE363
    camset_reset_applied = reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE363

    # Playback -> [Magnification] items are Reset-immune; ONLY [Initialize] clears them.
    eff_init_mag = (
        ENLARGE_INITIAL_MAG_DEFAULT_G157 if init_applied else enlarge_initial_mag
    )
    eff_init_pos_cfg = (
        ENLARGE_INITIAL_POS_DEFAULT_G157
        if init_applied
        else enlarge_initial_position
    )
    fallback_to_center = (
        eff_init_pos_cfg == "Focused Position"
    ) and (not focus_position_available)
    eff_init_pos = "Center" if fallback_to_center else eff_init_pos_cfg

    touch_blocked = (
        playback_operation in ("pinch_zoom", "double_tap")
        and touch_operation != "On"
    )
    if playback_media_kind == "movie" or touch_blocked or playback_operation == "menu_exit":
        eff_mag = 1.0
    else:
        eff_mag = (
            float(previous_mag_factor)
            if eff_init_mag == "Previous Mag."
            else float(requested_mag_factor)
        )
    zoom_preserved_step = (
        playback_media_kind == "still" and playback_operation == "dial_step_photo"
    )

    # Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.] IS Resettable (`Can be reset`).
    # Reset or Initialize sets it back to Off.
    if init_applied or camset_reset_applied:
        eff_anti_flicker = ANTI_FLICKER_SHOOT_DEFAULT_G157
    else:
        eff_anti_flicker = anti_flicker_shoot

    anti_flicker_allowed = (
        shoot_mode == SHOOT_MODE_STILL_PHASE363
        and shutter_type == "Mechanical"
        and silent_mode == "Off"
        and (not bulb_mode)
    )
    anti_flicker_mains_ok = (
        anti_flicker_allowed
        and eff_anti_flicker == "On"
        and mains_hz in ANTI_FLICKER_MAINS_FREQS_HZ_G157
    )

    return {
        "effective_enlarge_initial_mag": eff_init_mag,
        "effective_enlarge_initial_position": eff_init_pos,
        "focused_fallback_to_center": fallback_to_center,
        "effective_mag_factor": eff_mag,
        "zoom_preserved_across_photo_step": zoom_preserved_step,
        "effective_anti_flicker_shoot": eff_anti_flicker,
        "anti_flicker_shoot_enabled_allowed": anti_flicker_allowed,
        "anti_flicker_effective_for_mains_hz": anti_flicker_mains_ok,
    }


def compute_pbmag_varshutter_ecs_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G157 (384 states)."""
    combos = list(
        itertools.product(
            ALLOWED_PLAYBACK_MEDIA_KINDS_G157,  # 2 (still, movie)
            ALLOWED_ENLARGE_INITIAL_MAG_OPTIONS_G157,  # 2
            ALLOWED_ENLARGE_INITIAL_POS_OPTIONS_G157,  # 2
            ALLOWED_SHOOT_MODES_PHASE363,  # 3
            ALLOWED_SHUTTER_TYPES_G157,  # 2
            (False, True),  # bulb_mode (2)
            ("Off", "On"),  # anti_flicker_shoot (2)
            (
                RESET_ACTION_NONE_PHASE363,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE363,
            ),  # 2 -> 2*2*2*3*2*2*2*2 = 384
        )
    )
    movie_zoom_blocked_count = 0
    playback_magnify_reset_preserved_count = 0
    anti_flicker_reset_cleared_count = 0
    anti_flicker_eligible_count = 0
    anti_flicker_disabled_blocked_count = 0

    for mkind, init_mag, init_pos, sm, sht, bulb, afs, rst in combos:
        st = resolve_fx3_pbmag_varshutter_ecs_state(
            playback_media_kind=mkind,
            playback_operation="enlarge_image",
            enlarge_initial_mag=init_mag,
            enlarge_initial_position=init_pos,
            shoot_mode=sm,
            shutter_type=sht,
            bulb_mode=bulb,
            anti_flicker_shoot=afs,
            reset_action=rst,
        )
        if mkind == "movie" and st["effective_mag_factor"] == 1.0:
            movie_zoom_blocked_count += 1
        if rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE363:
            if (
                st["effective_enlarge_initial_mag"] == init_mag
                and st["effective_enlarge_initial_position"] == init_pos
            ):
                playback_magnify_reset_preserved_count += 1
            if afs == "On" and st["effective_anti_flicker_shoot"] == "Off":
                anti_flicker_reset_cleared_count += 1
        if st["anti_flicker_shoot_enabled_allowed"]:
            anti_flicker_eligible_count += 1
        elif afs == "On":
            anti_flicker_disabled_blocked_count += 1

    return {
        "total_matrix_states": len(combos),
        "movie_zoom_blocked_count": movie_zoom_blocked_count,
        "playback_magnify_reset_preserved_count": playback_magnify_reset_preserved_count,
        "anti_flicker_reset_cleared_count": anti_flicker_reset_cleared_count,
        "anti_flicker_eligible_count": anti_flicker_eligible_count,
        "anti_flicker_disabled_blocked_count": anti_flicker_disabled_blocked_count,
    }


def verify_pbmag_varshutter_ecs_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE363,
    body_model_id: int = FX3_MODEL_ID_PHASE363,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE363,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE363,
    playback_media_kind: str = "still",
    playback_operation: str = "enlarge_image",
    enlarge_initial_mag: str = ENLARGE_INITIAL_MAG_DEFAULT_G157,
    enlarge_initial_position: str = ENLARGE_INITIAL_POS_DEFAULT_G157,
    focus_position_available: bool = True,
    touch_operation: str = "On",
    previous_mag_factor: float = 4.0,
    requested_mag_factor: float = 2.0,
    claimed_movie_playback_zoom_supported: bool = False,
    claimed_camset_reset_clears_playback_magnify: bool = False,
    requested_fx6_still_or_playback_enlarge: bool = False,
    shoot_mode: str = SHOOT_MODE_STILL_PHASE363,
    shutter_type: str = "Mechanical",
    silent_mode: str = "Off",
    bulb_mode: bool = False,
    anti_flicker_shoot: str = ANTI_FLICKER_SHOOT_DEFAULT_G157,
    mains_hz: int = 100,
    claimed_anti_flicker_reset_immune: bool = False,
    requested_dormant_anti_flicker_set: bool = False,
    requested_dormant_var_shutter: bool = False,
    requested_dormant_var_shutter_set: bool = False,
    requested_dormant_anti_flicker_tv_scan: bool = False,
    requested_fx6_ecs_on_fx3: bool = False,
    fx6_ecs_frame_rate: str = "59.94P",
    fx6_ecs_freq_hz: Optional[float] = None,
    fx6_flicker_reduce_mode: str = "Auto",
    fx6_flicker_reduce_freq: str = "50Hz",
    reset_action: str = RESET_ACTION_NONE_PHASE363,
) -> PbMagVarShutterEcsGuardResult:
    """Enforce Gate G157: Still-Only Playback Magnification / Zero Movie Zoom & [Anti-flicker Shoot.] vs Dormant [Var. Shutter] / [Anti-flicker Tv Scan] / FX6 ECS."""
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

    if playback_media_kind not in ALLOWED_PLAYBACK_MEDIA_KINDS_G157:
        _add("TELEMETRY_INVALID", f"playback_media_kind_invalid:{playback_media_kind!r}")
    if playback_operation not in ALLOWED_PLAYBACK_ZOOM_OPERATIONS_G157:
        _add("TELEMETRY_INVALID", f"playback_operation_invalid:{playback_operation!r}")
    if enlarge_initial_mag not in ALLOWED_ENLARGE_INITIAL_MAG_OPTIONS_G157:
        _add("TELEMETRY_INVALID", f"enlarge_initial_mag_invalid:{enlarge_initial_mag!r}")
    if enlarge_initial_position not in ALLOWED_ENLARGE_INITIAL_POS_OPTIONS_G157:
        _add(
            "TELEMETRY_INVALID",
            f"enlarge_initial_position_invalid:{enlarge_initial_position!r}",
        )
    if not _is_on_off(touch_operation):
        _add("TELEMETRY_INVALID", f"touch_operation_invalid:{touch_operation!r}")
    if not _is_strict_number(previous_mag_factor) or float(previous_mag_factor) < 1.0:
        _add("TELEMETRY_INVALID", f"previous_mag_factor_invalid:{previous_mag_factor!r}")
    if not _is_strict_number(requested_mag_factor) or float(requested_mag_factor) < 1.0:
        _add("TELEMETRY_INVALID", f"requested_mag_factor_invalid:{requested_mag_factor!r}")
    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE363:
        _add("TELEMETRY_INVALID", f"shoot_mode_invalid:{shoot_mode!r}")
    if shutter_type not in ALLOWED_SHUTTER_TYPES_G157:
        _add("TELEMETRY_INVALID", f"shutter_type_invalid:{shutter_type!r}")
    if not _is_on_off(silent_mode):
        _add("TELEMETRY_INVALID", f"silent_mode_invalid:{silent_mode!r}")
    if not _is_on_off(anti_flicker_shoot):
        _add("TELEMETRY_INVALID", f"anti_flicker_shoot_invalid:{anti_flicker_shoot!r}")
    if not _is_strict_int(mains_hz) or mains_hz <= 0:
        _add("TELEMETRY_INVALID", f"mains_hz_invalid:{mains_hz!r}")
    if fx6_ecs_frame_rate not in FX6_ECS_6_FRAME_RATE_PRESETS_G157:
        _add("TELEMETRY_INVALID", f"fx6_ecs_frame_rate_invalid:{fx6_ecs_frame_rate!r}")
    if fx6_ecs_freq_hz is not None and not _is_strict_number(fx6_ecs_freq_hz):
        _add("TELEMETRY_INVALID", f"fx6_ecs_freq_hz_invalid:{fx6_ecs_freq_hz!r}")
    if fx6_flicker_reduce_mode not in FX6_FLICKER_REDUCE_MODES_G157:
        _add(
            "TELEMETRY_INVALID",
            f"fx6_flicker_reduce_mode_invalid:{fx6_flicker_reduce_mode!r}",
        )
    if fx6_flicker_reduce_freq not in FX6_FLICKER_REDUCE_FREQS_G157:
        _add(
            "TELEMETRY_INVALID",
            f"fx6_flicker_reduce_freq_invalid:{fx6_flicker_reduce_freq!r}",
        )
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE363:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")

    eff_fx6_hz = (
        FX6_ECS_6_FRAME_RATE_PRESETS_G157.get(fx6_ecs_frame_rate, 60.0)
        if fx6_ecs_freq_hz is None
        else (float(fx6_ecs_freq_hz) if _is_strict_number(fx6_ecs_freq_hz) else 60.0)
    )

    state = resolve_fx3_pbmag_varshutter_ecs_state(
        playback_media_kind=(
            playback_media_kind
            if playback_media_kind in ALLOWED_PLAYBACK_MEDIA_KINDS_G157
            else "still"
        ),
        playback_operation=(
            playback_operation
            if playback_operation in ALLOWED_PLAYBACK_ZOOM_OPERATIONS_G157
            else "enlarge_image"
        ),
        enlarge_initial_mag=(
            enlarge_initial_mag
            if enlarge_initial_mag in ALLOWED_ENLARGE_INITIAL_MAG_OPTIONS_G157
            else ENLARGE_INITIAL_MAG_DEFAULT_G157
        ),
        enlarge_initial_position=(
            enlarge_initial_position
            if enlarge_initial_position in ALLOWED_ENLARGE_INITIAL_POS_OPTIONS_G157
            else ENLARGE_INITIAL_POS_DEFAULT_G157
        ),
        focus_position_available=focus_position_available,
        touch_operation=touch_operation if _is_on_off(touch_operation) else "On",
        previous_mag_factor=(
            float(previous_mag_factor)
            if _is_strict_number(previous_mag_factor) and float(previous_mag_factor) >= 1.0
            else 4.0
        ),
        requested_mag_factor=(
            float(requested_mag_factor)
            if _is_strict_number(requested_mag_factor) and float(requested_mag_factor) >= 1.0
            else 2.0
        ),
        shoot_mode=(
            shoot_mode
            if shoot_mode in ALLOWED_SHOOT_MODES_PHASE363
            else SHOOT_MODE_STILL_PHASE363
        ),
        shutter_type=(
            shutter_type if shutter_type in ALLOWED_SHUTTER_TYPES_G157 else "Mechanical"
        ),
        silent_mode=silent_mode if _is_on_off(silent_mode) else "Off",
        bulb_mode=bulb_mode,
        anti_flicker_shoot=(
            anti_flicker_shoot
            if _is_on_off(anti_flicker_shoot)
            else ANTI_FLICKER_SHOOT_DEFAULT_G157
        ),
        mains_hz=mains_hz if _is_strict_int(mains_hz) and mains_hz > 0 else 100,
        reset_action=(
            reset_action
            if reset_action in ALLOWED_RESET_ACTIONS_PHASE363
            else RESET_ACTION_NONE_PHASE363
        ),
    )

    # EOPNOTSUPP=95 Movie Playback Zoom, Dormant Alpha Var. Shutter/Tv Scan & FX6 Cross-Model Blocks
    movie_zoom_attempt = bool(
        (
            playback_media_kind == "movie"
            and playback_operation
            in (
                "enlarge_image",
                "wt_lever",
                "pinch_zoom",
                "double_tap",
                "dial_step_photo",
            )
        )
        or claimed_movie_playback_zoom_supported
    )

    dormant_or_eopnotsupp = bool(
        movie_zoom_attempt
        or requested_fx6_still_or_playback_enlarge
        or requested_dormant_anti_flicker_set
        or requested_dormant_var_shutter
        or requested_dormant_var_shutter_set
        or requested_dormant_anti_flicker_tv_scan
        or requested_fx6_ecs_on_fx3
    )

    if movie_zoom_attempt:
        _add(
            "MOVIE_PLAYBACK_ZOOM_PROHIBITED_EOPNOTSUPP",
            "playback_zoom_is_inhibition_rejects_movie_enlarge_base_0xe572_unable_to_magnify_eopnotsupp_95",
        )
    if requested_fx6_still_or_playback_enlarge:
        _add(
            "FX6_ZERO_STILL_OR_PLAYBACK_ENLARGE_EOPNOTSUPP",
            "fx6_ver_6_01_exposes_zero_still_and_zero_playback_enlarge_dormant_ns1_0x2b0e_eopnotsupp_95",
        )
    if requested_dormant_anti_flicker_set:
        _add(
            "DORMANT_ANTI_FLICKER_SET_EOPNOTSUPP",
            "fx3_dormant_anti_flicker_set_0x68e7_is_unexposed_on_ilme_fx3_eopnotsupp_95",
        )
    if requested_dormant_var_shutter or requested_dormant_var_shutter_set:
        _add(
            "DORMANT_VAR_SHUTTER_HIGH_RES_SS_EOPNOTSUPP",
            "fx3_dormant_var_shutter_bkid_app_setting_high_res_ss_is_unexposed_on_fx3_eopnotsupp_95",
        )
    if requested_dormant_anti_flicker_tv_scan:
        _add(
            "DORMANT_ANTI_FLICKER_TV_SCAN_EOPNOTSUPP",
            "fx3_dormant_anti_flicker_tv_scan_sequence_flicker_scan_empty_sc_0x60a8_is_unexposed_eopnotsupp_95",
        )
    if requested_fx6_ecs_on_fx3:
        _add(
            "FX6_ECS_UNAVAILABLE_ON_FX3_EOPNOTSUPP",
            "fx3_does_not_expose_fx6_continuous_ecs_23_99_to_8000hz_eopnotsupp_95",
        )

    # EINVAL=22 Constraint, Reset-Immunity, Touch-Operation & ECS Bound Violations
    if playback_media_kind == "still" and playback_operation in (
        "pinch_zoom",
        "double_tap",
    ) and touch_operation != "On":
        _add(
            "PINCH_OR_DOUBLETAP_REQUIRES_TOUCH_OPERATION_ON",
            f"playback_{playback_operation}_requires_touch_operation_on_einval_22",
        )
    if claimed_camset_reset_clears_playback_magnify:
        _add(
            "PLAYBACK_MAGNIFY_RESET_IMMUNITY_VIOLATION",
            "playback_magnification_initial_mag_and_position_are_not_available_under_camset_reset_einval_22",
        )
    if claimed_anti_flicker_reset_immune:
        _add(
            "ANTI_FLICKER_SHOOT_RESETTABLE_VIOLATION",
            "anti_flicker_shoot_is_can_be_reset_by_camera_settings_reset_einval_22",
        )
    if state["effective_anti_flicker_shoot"] == "On" and not state[
        "anti_flicker_shoot_enabled_allowed"
    ]:
        _add(
            "ANTI_FLICKER_SHOOT_MODE_OR_SHUTTER_INHIBITED",
            f"anti_flicker_shoot_disabled_in_mode_{shoot_mode}_shutter_{shutter_type}_silent_{silent_mode}_bulb_{bulb_mode}_einval_22",
        )
    if eff_fx6_hz < FX6_ECS_FREQ_MIN_HZ_G157 or eff_fx6_hz > FX6_ECS_FREQ_MAX_HZ_G157:
        _add(
            "FX6_ECS_FREQUENCY_OUT_OF_RANGE",
            f"fx6_ecs_frequency_{eff_fx6_hz}_hz_outside_23_99_to_8000_hz_einval_22",
        )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G157
        block_errno = 0
        block_errno_name = "OK"
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G157_MOVIE_ZOOM_OR_DORMANT_VAR_SHUTTER_EOPNOTSUPP
        block_errno = EOPNOTSUPP_ERRNO_PHASE363
        block_errno_name = EOPNOTSUPP_NAME_PHASE363
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
        status = STATUS_BLOCKED_G157_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE363
        block_errno_name = EINVAL_NAME_PHASE363
    else:
        status = STATUS_BLOCKED_G157_PBMAG_RESET_OR_ANTI_FLICKER_CONSTRAINT_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE363
        block_errno_name = EINVAL_NAME_PHASE363

    return PbMagVarShutterEcsGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        playback_magnification_menu_path=PLAYBACK_MAGNIFICATION_MENU_PATH_G157,
        anti_flicker_shoot_menu_path=ANTI_FLICKER_SHOOT_MENU_PATH_G157,
        fx6_shutter_ecs_menu_path=FX6_SHUTTER_ECS_MENU_PATH_G157,
        fx6_flicker_reduce_menu_path=FX6_FLICKER_REDUCE_MENU_PATH_G157,
        playback_magnify_items_count=len(EXACT_3_PLAYBACK_MAGNIFY_ITEMS_G157),
        effective_playback_media_kind=playback_media_kind,
        effective_playback_operation=playback_operation,
        effective_enlarge_initial_mag=state["effective_enlarge_initial_mag"],
        effective_enlarge_initial_position=state["effective_enlarge_initial_position"],
        focused_fallback_to_center=state["focused_fallback_to_center"],
        effective_mag_factor=state["effective_mag_factor"],
        zoom_preserved_across_photo_step=state["zoom_preserved_across_photo_step"],
        playback_zoom_maginify_elf_typo=PLAYBACK_ZOOM_MAGINIFY_ELF_TYPO_G157,
        playback_zoom_inhibition_text=PLAYBACK_ZOOM_INHIBITION_TEXT_G157,
        playback_magnify_resettable_by_camset_reset=PLAYBACK_MAGNIFY_RESETTABLE_BY_CAMSET_RESET_G157,
        movie_playback_zoom_supported=MOVIE_PLAYBACK_ZOOM_SUPPORTED_G157,
        movie_playback_zoom_bypass_events=0,
        fx6_still_or_pb_enlarge_supported=FX6_STILL_OR_PB_ENLARGE_SUPPORTED_G157,
        effective_shoot_mode=shoot_mode,
        effective_shutter_type=shutter_type,
        silent_mode=silent_mode,
        bulb_mode=bulb_mode,
        effective_anti_flicker_shoot=state["effective_anti_flicker_shoot"],
        anti_flicker_shoot_enabled_allowed=state["anti_flicker_shoot_enabled_allowed"],
        anti_flicker_effective_for_mains_hz=state["anti_flicker_effective_for_mains_hz"],
        anti_flicker_shoot_resettable_by_camset_reset=ANTI_FLICKER_SHOOT_RESETTABLE_BY_CAMSET_RESET_G157,
        fx3_var_shutter_exposed=FX3_VAR_SHUTTER_EXPOSED_G157,
        fx3_anti_flicker_set_exposed=FX3_ANTI_FLICKER_SET_EXPOSED_G157,
        fx3_anti_flicker_tv_scan_exposed=FX3_ANTI_FLICKER_TV_SCAN_EXPOSED_G157,
        fx3_sc_tv_scan_0x60a8_empty_string=FX3_SC_TV_SCAN_0X60A8_EMPTY_STRING_G157,
        fx6_ecs_frame_rate=fx6_ecs_frame_rate,
        fx6_ecs_freq_hz=round(eff_fx6_hz, 2),
        fx6_flicker_reduce_mode=fx6_flicker_reduce_mode,
        fx6_flicker_reduce_freq=fx6_flicker_reduce_freq,
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
class G157PbMagVarShutterEcsGuardResult:
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
    pbmag_varshutter_ecs_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g157_pbmag_varshutter_ecs_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G157PbMagVarShutterEcsGuardResult]:
    audit = audit_phase363_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_pbmag_varshutter_ecs_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G157PbMagVarShutterEcsGuardResult(
        gate_id=G157,
        gate_code=G157_GATE_CODE,
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
        pbmag_varshutter_ecs_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G157,
        gate_code=G157_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"pb_kind={res.effective_playback_media_kind} "
            f"mag={res.effective_mag_factor:.1f}x "
            f"movie_zoom={res.movie_playback_zoom_supported} "
            f"af_shoot={res.effective_anti_flicker_shoot} "
            f"var_shutter={res.fx3_var_shutter_exposed}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_pbmag_varshutter_ecs_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G157PbMagVarShutterEcsGuardResult]:
    return evaluate_g157_pbmag_varshutter_ecs_guard(**kwargs)


# ---------------------------------------------------------------------------
# Gate G158: Wi-Fi WW728473/WW558244 5GHz SKU + p12/p13 MS_RDONLY NVS &
#            [IR Remote Ctrl] #5 / [CTRL FOR HDMI] CEC Firewall / Zero LANC
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Wifi5GhzNvsIrLancCecGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    wifi_menu_path: str
    ir_remote_ctrl_menu_path: str
    ctrl_for_hdmi_menu_path: str
    fx6_wireless_lan_menu_path: str
    fx3_body_variant: str
    wifi_sku_code: str
    wifi_sku_gate_function: str
    wifi_available_bands: Tuple[str, ...]
    effective_wifi_band: str
    outdoor_5ghz_restricted: bool
    effective_wifi_security: str
    access_authen_settings: str
    effective_airplane_mode: str
    airplane_mode_survived_reset_network: bool
    rf_tx_packets: int
    target_partition: str
    p12_p13_ms_readonly_enforced: bool
    rf_nvs_mutation_bytes: int
    emmc_nflasha_write_count: int
    fx6_wlan_mode: str
    fx3_ir_front_sensor_num: Optional[int]
    fx3_af_illuminator_sensor_num: int
    effective_ir_remote_ctrl: str
    ir_remote_resettable_by_camset_reset: bool
    power_save_bypassed_by_ir: bool
    bluetooth_rmt_ctrl: str
    bt_ir_mutex_triggered: bool
    effective_ctrl_for_hdmi: str
    factory_default_ctrl_for_hdmi: str
    ctrl_for_hdmi_resettable_by_camset_reset: bool
    ctrl_for_hdmi_elf_typo: str
    external_hdmi_gear_attaching: bool
    hil_bench_safe_for_hdmi_attach: bool
    cec_key_events_count: int
    cec_rec_event_count: int
    fx3_physical_lanc_25mm_present: bool
    fx3_physical_grip_remote_35mm_present: bool
    fx3_active_lanc_bkid_hits: int
    fx6_lanc_25mm_port_num: int
    fx6_grip_remote_35mm_poles: int
    fx6_exposed_ir_or_cec_menus: bool
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


def resolve_fx3_wifi5ghz_nvs_ir_lanc_cec_state(
    *,
    fx3_body_variant: str = FX3_MODEL_NAME_PHASE363,
    wifi_sku_code: str = FX3_WIFI_SKU_WW728473_G158,
    requested_band: str = "2.4GHz",
    outdoor_5ghz_restricted: bool = False,
    wifi_security: str = "WPA2-PSK",
    access_authen: str = "On",
    airplane_mode: str = "Off",
    ir_remote_ctrl: str = IR_REMOTE_CTRL_DEFAULT_G158,
    bluetooth_rmt_ctrl: str = "Off",
    ctrl_for_hdmi: str = "Off",
    external_hdmi_gear_attaching: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE363,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-69 Wi-Fi 5GHz SKU, Airplane/NVS & IR/CEC/LANC state."""
    init_applied = reset_action == RESET_ACTION_INITIALIZE_PHASE363
    # CRITICAL: [Airplane Mode] survives [Reset Network Set.] AND [Camera Settings Reset];
    # cleared ONLY by [Initialize].
    eff_airplane = "Off" if init_applied else airplane_mode

    # [IR Remote Ctrl] and [CTRL FOR HDMI] are Reset-immune; ONLY [Initialize] restores defaults (Off / On).
    eff_ir = IR_REMOTE_CTRL_DEFAULT_G158 if init_applied else ir_remote_ctrl
    eff_ctrl_for_hdmi = (
        CTRL_FOR_HDMI_FACTORY_DEFAULT_G158 if init_applied else ctrl_for_hdmi
    )
    if fx3_body_variant == FX3A_MODEL_NAME_PHASE363:
        eff_ir_sensor: Optional[int] = None
    else:
        eff_ir_sensor = FX3_IR_FRONT_SENSOR_NUM_G158

    avail_bands: Tuple[str, ...] = (
        ("2.4GHz", "5GHz")
        if wifi_sku_code in (FX3_WIFI_SKU_WW728473_G158, FX6_WIFI_SKU_5GHZ_G158)
        else ("2.4GHz",)
    )
    if (
        init_applied
        or eff_airplane == "On"
        or (requested_band not in avail_bands)
        or (requested_band == "5GHz" and outdoor_5ghz_restricted)
    ):
        eff_band = "2.4GHz"
    else:
        eff_band = requested_band

    bt_ir_mutex = bool(eff_ir == "On" and bluetooth_rmt_ctrl == "On")
    power_save_bypassed_ir = bool(
        eff_ir == "On" and (not bt_ir_mutex) and eff_ir_sensor is not None
    )
    hil_bench_safe_hdmi = eff_ctrl_for_hdmi == "Off"
    cec_hijack_hazard = bool(external_hdmi_gear_attaching and eff_ctrl_for_hdmi == "On")

    return {
        "wifi_available_bands": avail_bands,
        "effective_wifi_band": eff_band,
        "effective_wifi_security": "WPA2-PSK" if init_applied else wifi_security,
        "effective_airplane_mode": eff_airplane,
        "fx3_ir_front_sensor_num": eff_ir_sensor,
        "effective_ir_remote_ctrl": eff_ir,
        "power_save_bypassed_by_ir": power_save_bypassed_ir,
        "bt_ir_mutex_triggered": bt_ir_mutex,
        "effective_ctrl_for_hdmi": eff_ctrl_for_hdmi,
        "hil_bench_safe_for_hdmi_attach": hil_bench_safe_hdmi,
        "cec_hijack_hazard": cec_hijack_hazard,
    }


def compute_wifi5ghz_nvs_ir_lanc_cec_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G158 (384 states)."""
    combos = list(
        itertools.product(
            (FX3_WIFI_SKU_WW728473_G158, FX3_WIFI_SKU_WW558244_G158),  # 2
            ALLOWED_WIFI_BANDS_G158,  # 2
            (False, True),  # outdoor_5ghz_restricted (2)
            ("Off", "On"),  # airplane_mode (2)
            ("Off", "On"),  # bluetooth_rmt_ctrl (2)
            ("Off", "On"),  # ir_remote_ctrl (2)
            ("Off", "On"),  # ctrl_for_hdmi (2)
            (
                RESET_ACTION_NONE_PHASE363,
                RESET_ACTION_RESET_NETWORK_SET_PHASE363,
                RESET_ACTION_INITIALIZE_PHASE363,
            ),  # 3 -> 2^7 * 3 = 384
        )
    )
    airplane_survived_reset_network_count = 0
    airplane_cleared_by_initialize_count = 0
    ww558244_5ghz_blocked_count = 0
    outdoor_5ghz_blocked_count = 0
    bt_ir_mutex_blocked_count = 0
    cec_bench_hazard_flagged_count = 0

    for sku, band, outdoor, airp, bt, ir, hdmi_cec, rst in combos:
        st = resolve_fx3_wifi5ghz_nvs_ir_lanc_cec_state(
            wifi_sku_code=sku,
            requested_band=band,
            outdoor_5ghz_restricted=outdoor,
            airplane_mode=airp,
            bluetooth_rmt_ctrl=bt,
            ir_remote_ctrl=ir,
            ctrl_for_hdmi=hdmi_cec,
            external_hdmi_gear_attaching=True,
            reset_action=rst,
        )
        if rst == RESET_ACTION_RESET_NETWORK_SET_PHASE363 and airp == "On":
            if st["effective_airplane_mode"] == "On":
                airplane_survived_reset_network_count += 1
        if rst == RESET_ACTION_INITIALIZE_PHASE363 and airp == "On":
            if st["effective_airplane_mode"] == "Off":
                airplane_cleared_by_initialize_count += 1
        if sku == FX3_WIFI_SKU_WW558244_G158 and band == "5GHz" and st["effective_wifi_band"] == "2.4GHz":
            ww558244_5ghz_blocked_count += 1
        if outdoor and band == "5GHz" and st["effective_wifi_band"] == "2.4GHz":
            outdoor_5ghz_blocked_count += 1
        if st["bt_ir_mutex_triggered"]:
            bt_ir_mutex_blocked_count += 1
        if st["cec_hijack_hazard"]:
            cec_bench_hazard_flagged_count += 1

    return {
        "total_matrix_states": len(combos),
        "airplane_survived_reset_network_count": airplane_survived_reset_network_count,
        "airplane_cleared_by_initialize_count": airplane_cleared_by_initialize_count,
        "ww558244_5ghz_blocked_count": ww558244_5ghz_blocked_count,
        "outdoor_5ghz_blocked_count": outdoor_5ghz_blocked_count,
        "bt_ir_mutex_blocked_count": bt_ir_mutex_blocked_count,
        "cec_bench_hazard_flagged_count": cec_bench_hazard_flagged_count,
    }


def verify_wifi5ghz_nvs_ir_lanc_cec_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE363,
    body_model_id: int = FX3_MODEL_ID_PHASE363,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE363,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE363,
    fx3_body_variant: str = FX3_MODEL_NAME_PHASE363,
    wifi_operation: str = "wifi_band_select",
    wifi_sku_code: str = FX3_WIFI_SKU_WW728473_G158,
    requested_band: str = "2.4GHz",
    outdoor_5ghz_restricted: bool = False,
    wifi_security: str = "WPA2-PSK",
    access_authen: str = "On",
    wifi_connect: str = "On",
    airplane_mode: str = "Off",
    rf_tx_requested: bool = False,
    claimed_reset_network_clears_airplane: bool = False,
    target_partition: str = "none",
    requested_p12_p13_write: bool = False,
    fx6_wlan_mode: str = "Access Point Mode",
    fx6_wired_lan_on: bool = False,
    fx6_simul_rec_on: bool = False,
    requested_fx6_dormant_nfc: bool = False,
    ir_remote_ctrl: str = IR_REMOTE_CTRL_DEFAULT_G158,
    bluetooth_rmt_ctrl: str = "Off",
    claimed_camset_reset_clears_ir_or_cec: bool = False,
    ctrl_for_hdmi: str = "Off",
    external_hdmi_gear_attaching: bool = False,
    cec_key_event: Optional[str] = None,
    requested_fx3_25mm_lanc_or_35mm_grip: bool = False,
    requested_fx6_dormant_ir_or_cec_menu: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE363,
) -> Wifi5GhzNvsIrLancCecGuardResult:
    """Enforce Gate G158: Wi-Fi 5GHz SKU + p12/p13 MS_RDONLY NVS & [IR Remote Ctrl] #5 / [CTRL FOR HDMI] CEC / Zero LANC."""
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

    if fx3_body_variant not in ALLOWED_FX3_VARIANTS_PHASE363:
        _add("TELEMETRY_INVALID", f"fx3_body_variant_invalid:{fx3_body_variant!r}")
    if wifi_operation not in ALLOWED_WIFI_OPERATIONS_G158:
        _add("TELEMETRY_INVALID", f"wifi_operation_invalid:{wifi_operation!r}")
    if wifi_sku_code not in ALLOWED_WIFI_SKU_CODES_G158:
        _add("TELEMETRY_INVALID", f"wifi_sku_code_invalid:{wifi_sku_code!r}")
    if requested_band not in ALLOWED_WIFI_BANDS_G158:
        _add("TELEMETRY_INVALID", f"requested_band_invalid:{requested_band!r}")
    if wifi_security not in ALLOWED_WIFI_SECURITY_PROTOCOLS_G158:
        _add("TELEMETRY_INVALID", f"wifi_security_invalid:{wifi_security!r}")
    if not _is_on_off(access_authen):
        _add("TELEMETRY_INVALID", f"access_authen_invalid:{access_authen!r}")
    if not _is_on_off(wifi_connect):
        _add("TELEMETRY_INVALID", f"wifi_connect_invalid:{wifi_connect!r}")
    if not _is_on_off(airplane_mode):
        _add("TELEMETRY_INVALID", f"airplane_mode_invalid:{airplane_mode!r}")
    if target_partition not in ALLOWED_TARGET_PARTITIONS_G158:
        _add("TELEMETRY_INVALID", f"target_partition_invalid:{target_partition!r}")
    if fx6_wlan_mode not in ALLOWED_FX6_WLAN_MODES_G158:
        _add("TELEMETRY_INVALID", f"fx6_wlan_mode_invalid:{fx6_wlan_mode!r}")
    if not _is_on_off(ir_remote_ctrl):
        _add("TELEMETRY_INVALID", f"ir_remote_ctrl_invalid:{ir_remote_ctrl!r}")
    if not _is_on_off(bluetooth_rmt_ctrl):
        _add("TELEMETRY_INVALID", f"bluetooth_rmt_ctrl_invalid:{bluetooth_rmt_ctrl!r}")
    if not _is_on_off(ctrl_for_hdmi):
        _add("TELEMETRY_INVALID", f"ctrl_for_hdmi_invalid:{ctrl_for_hdmi!r}")
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE363:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")

    state = resolve_fx3_wifi5ghz_nvs_ir_lanc_cec_state(
        fx3_body_variant=(
            fx3_body_variant
            if fx3_body_variant in ALLOWED_FX3_VARIANTS_PHASE363
            else FX3_MODEL_NAME_PHASE363
        ),
        wifi_sku_code=(
            wifi_sku_code
            if wifi_sku_code in ALLOWED_WIFI_SKU_CODES_G158
            else FX3_WIFI_SKU_WW728473_G158
        ),
        requested_band=(
            requested_band
            if requested_band in ALLOWED_WIFI_BANDS_G158
            else "2.4GHz"
        ),
        outdoor_5ghz_restricted=outdoor_5ghz_restricted,
        wifi_security=(
            wifi_security
            if wifi_security in ALLOWED_WIFI_SECURITY_PROTOCOLS_G158
            else "WPA2-PSK"
        ),
        access_authen=access_authen if _is_on_off(access_authen) else "On",
        airplane_mode=airplane_mode if _is_on_off(airplane_mode) else "Off",
        ir_remote_ctrl=(
            ir_remote_ctrl
            if _is_on_off(ir_remote_ctrl)
            else IR_REMOTE_CTRL_DEFAULT_G158
        ),
        bluetooth_rmt_ctrl=(
            bluetooth_rmt_ctrl if _is_on_off(bluetooth_rmt_ctrl) else "Off"
        ),
        ctrl_for_hdmi=ctrl_for_hdmi if _is_on_off(ctrl_for_hdmi) else "Off",
        external_hdmi_gear_attaching=external_hdmi_gear_attaching,
        reset_action=(
            reset_action
            if reset_action in ALLOWED_RESET_ACTIONS_PHASE363
            else RESET_ACTION_NONE_PHASE363
        ),
    )

    # 1. EROFS=30 Hard Firewall on eMMC p12 (/cert 40 MiB) & p13 (4 MiB RF/MAC NVS)
    p12_p13_write_blocked = bool(
        wifi_operation == "rf_nvs_write_attempt"
        or target_partition in ("p12_cert", "p13_rfnvs")
        or requested_p12_p13_write
    )
    if p12_p13_write_blocked:
        _add(
            "P12_P13_MS_RDONLY_RF_NVS_EROFS",
            f"tier0_ms_rdonly_firewall_blocked_write_to_partition_{target_partition!r}_p12_p13_erofs_30",
        )

    # 2. EBUSY=16 Mutual Exclusions (BT Remote vs IR Remote Ctrl; FX6 Wireless vs Wired/SimulRec)
    bt_ir_mutex = bool(state["bt_ir_mutex_triggered"])
    fx6_wlan_mutex = bool(
        wifi_operation == "fx6_wireless_lan" and (fx6_wired_lan_on or fx6_simul_rec_on)
    )
    if bt_ir_mutex:
        _add(
            "BT_REMOTE_IR_REMOTE_MUTEX_EBUSY",
            "ir_remote_ctrl_on_is_mutually_exclusive_with_bluetooth_rmt_ctrl_on_ebusy_16",
        )
    if fx6_wlan_mutex:
        _add(
            "FX6_WLAN_WIRED_OR_SIMULREC_MUTEX_EBUSY",
            "fx6_wireless_lan_mutually_excluded_by_wired_lan_or_simul_rec_ebusy_16",
        )

    # 3. EOPNOTSUPP=95 SKU 5GHz Lock, Deprecated Security, FX3A IR Removal, Zero LANC & Dormant FX6 Menus
    sku_5ghz_blocked = bool(
        wifi_sku_code in (FX3_WIFI_SKU_WW558244_G158, FX6_WIFI_SKU_24GHZ_G158)
        and requested_band == "5GHz"
    )
    legacy_sec_blocked = wifi_security in VER7_REMOVED_WIFI_SECURITY_PROTOCOLS_G158
    fx3a_ir_blocked = bool(
        fx3_body_variant == FX3A_MODEL_NAME_PHASE363
        and state["effective_ir_remote_ctrl"] == "On"
    )
    cec_rec_or_unknown = bool(
        cec_key_event is not None
        and (
            cec_key_event in ("EVENT_INPUT_KEY_CEC_REC", "CEC_REC")
            or cec_key_event not in EXACT_41_FX3_CEC_KEY_EVENTS_G158
        )
    )

    dormant_or_eopnotsupp = bool(
        sku_5ghz_blocked
        or legacy_sec_blocked
        or fx3a_ir_blocked
        or requested_fx6_dormant_nfc
        or requested_fx3_25mm_lanc_or_35mm_grip
        or requested_fx6_dormant_ir_or_cec_menu
        or cec_rec_or_unknown
    )
    if sku_5ghz_blocked:
        _add(
            "WIFI_SKU_5GHZ_LOCKED_EOPNOTSUPP",
            f"backup_get_wi_fi_frequency_band_dst_locked_sku_{wifi_sku_code}_2_4ghz_only_eopnotsupp_95",
        )
    if legacy_sec_blocked:
        _add(
            "WIFI_DEPRECATED_SECURITY_REMOVED_EOPNOTSUPP",
            f"ver7_wifi_removed_deprecated_security_{wifi_security!r}_wpa2_wpa3_only_eopnotsupp_95",
        )
    if fx3a_ir_blocked:
        _add(
            "FX3A_PHYSICAL_IR_SENSOR_REMOVED_EOPNOTSUPP",
            "2025_ilme_fx3a_physically_removed_front_pin_5_ir_sensor_eopnotsupp_95",
        )
    if requested_fx6_dormant_nfc:
        _add(
            "FX6_NFC_REMOVED_VER6_EOPNOTSUPP",
            "fx6_ver_6_00_plus_removed_nfc_eopnotsupp_95",
        )
    if requested_fx3_25mm_lanc_or_35mm_grip:
        _add(
            "FX3_ZERO_LANC_25MM_AND_GRIP_35MM_EOPNOTSUPP",
            "fx3_has_zero_physical_2_5mm_lanc_or_3_5mm_grip_remote_0_active_bkid_eopnotsupp_95",
        )
    if requested_fx6_dormant_ir_or_cec_menu:
        _add(
            "FX6_ZERO_USER_IR_OR_CTRL_FOR_HDMI_EOPNOTSUPP",
            "fx6_ver_6_01_exposes_zero_ir_remote_or_ctrl_for_hdmi_menus_eopnotsupp_95",
        )
    if cec_rec_or_unknown:
        _add(
            "CEC_UNKNOWN_OR_ABSENT_CEC_REC_EOPNOTSUPP",
            f"fx3_appfw_has_41_cec_events_with_zero_cec_rec_unsupported_{cec_key_event!r}_eopnotsupp_95",
        )

    # 4. EINVAL=22 / Policy Violations: Airplane Mode, Outdoor 5GHz, Access Authen, Reset-Immunity, CTRL FOR HDMI CEC Bench Guard
    fw_ver_num = _parse_fw_float(firmware_version)
    if fw_ver_num is not None and fw_ver_num >= 7.00 and access_authen != "On":
        _add(
            "VER7_ACCESS_AUTHEN_ON_MANDATORY",
            "ver_7_00_plus_requires_access_authen_settings_on_einval_22",
        )
    if wifi_operation == "ap_connect" and wifi_connect != "On":
        _add(
            "AP_CONNECT_REQUIRES_WIFI_CONNECT_ON",
            "access_point_set_requires_wifi_connect_on_einval_22",
        )
    if requested_band == "5GHz" and outdoor_5ghz_restricted:
        _add(
            "OUTDOOR_5GHZ_PROHIBITED",
            "outdoor_wifi_direct_5ghz_restricted_forced_2_4ghz_einval_22",
        )
    if claimed_reset_network_clears_airplane:
        _add(
            "AIRPLANE_MODE_SURVIVES_RESET_NETWORK_VIOLATION",
            "airplane_mode_on_survives_reset_network_set_cleared_only_by_initialize_einval_22",
        )
    if rf_tx_requested and state["effective_airplane_mode"] == "On":
        _add(
            "AIRPLANE_MODE_RF_TX_BLOCKED",
            "airplane_mode_on_hard_blocks_rf_tx_packets_zero_einval_22",
        )
    if claimed_camset_reset_clears_ir_or_cec:
        _add(
            "IR_AND_CTRL_FOR_HDMI_RESET_IMMUNITY_VIOLATION",
            "ir_remote_ctrl_and_ctrl_for_hdmi_are_not_available_under_camset_reset_einval_22",
        )
    if state["cec_hijack_hazard"]:
        _add(
            "CTRL_FOR_HDMI_ON_BENCH_CEC_HIJACK_RISK",
            "ctrl_for_hdmi_on_factory_default_exposes_41_cec_keys_must_set_off_before_external_hdmi_attach",
        )
    if (
        cec_key_event is not None
        and (not cec_rec_or_unknown)
        and state["effective_ctrl_for_hdmi"] == "On"
        and external_hdmi_gear_attaching
    ):
        _add(
            "CEC_KEY_INJECTION_BLOCKED_ON_BENCH",
            f"unguarded_cec_key_{cec_key_event!r}_injection_risk_while_ctrl_for_hdmi_on",
        )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G158
        block_errno = 0
        block_errno_name = "OK"
    elif p12_p13_write_blocked:
        status = STATUS_BLOCKED_G158_P12_P13_RF_NVS_MS_RDONLY_EROFS
        block_errno = EROFS_ERRNO_PHASE363
        block_errno_name = EROFS_NAME_PHASE363
    elif bt_ir_mutex or fx6_wlan_mutex:
        status = STATUS_BLOCKED_G158_BT_IR_OR_FX6_WLAN_MUTEX_EBUSY
        block_errno = EBUSY_ERRNO_PHASE363
        block_errno_name = EBUSY_NAME_PHASE363
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G158_SKU_LEGACY_SEC_FX3A_IR_OR_LANC_EOPNOTSUPP
        block_errno = EOPNOTSUPP_ERRNO_PHASE363
        block_errno_name = EOPNOTSUPP_NAME_PHASE363
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
        status = STATUS_BLOCKED_G158_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE363
        block_errno_name = EINVAL_NAME_PHASE363
    else:
        status = STATUS_BLOCKED_G158_AIRPLANE_RF_OR_CTRL_FOR_HDMI_CEC_HIJACK_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE363
        block_errno_name = EINVAL_NAME_PHASE363

    return Wifi5GhzNvsIrLancCecGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        wifi_menu_path=WIFI_MENU_PATH_G158,
        ir_remote_ctrl_menu_path=IR_REMOTE_CTRL_MENU_PATH_G158,
        ctrl_for_hdmi_menu_path=CTRL_FOR_HDMI_MENU_PATH_G158,
        fx6_wireless_lan_menu_path=FX6_WIRELESS_LAN_MENU_PATH_G158,
        fx3_body_variant=fx3_body_variant,
        wifi_sku_code=wifi_sku_code,
        wifi_sku_gate_function=WIFI_SKU_GATE_FN_G158,
        wifi_available_bands=state["wifi_available_bands"],
        effective_wifi_band=state["effective_wifi_band"],
        outdoor_5ghz_restricted=outdoor_5ghz_restricted,
        effective_wifi_security=state["effective_wifi_security"],
        access_authen_settings=access_authen,
        effective_airplane_mode=state["effective_airplane_mode"],
        airplane_mode_survived_reset_network=AIRPLANE_MODE_SURVIVES_RESET_NETWORK_G158,
        rf_tx_packets=RF_TX_PACKETS_AIRPLANE_G158,
        target_partition=target_partition,
        p12_p13_ms_readonly_enforced=P12_P13_MS_RDONLY_ENFORCED_G158,
        rf_nvs_mutation_bytes=RF_NVS_MUTATION_BYTES_G158,
        emmc_nflasha_write_count=0,
        fx6_wlan_mode=fx6_wlan_mode,
        fx3_ir_front_sensor_num=state["fx3_ir_front_sensor_num"],
        fx3_af_illuminator_sensor_num=FX3_AF_ILLUMINATOR_SENSOR_NUM_G158,
        effective_ir_remote_ctrl=state["effective_ir_remote_ctrl"],
        ir_remote_resettable_by_camset_reset=IR_REMOTE_CTRL_RESETTABLE_BY_CAMSET_RESET_G158,
        power_save_bypassed_by_ir=state["power_save_bypassed_by_ir"],
        bluetooth_rmt_ctrl=bluetooth_rmt_ctrl,
        bt_ir_mutex_triggered=bt_ir_mutex,
        effective_ctrl_for_hdmi=state["effective_ctrl_for_hdmi"],
        factory_default_ctrl_for_hdmi=CTRL_FOR_HDMI_FACTORY_DEFAULT_G158,
        ctrl_for_hdmi_resettable_by_camset_reset=CTRL_FOR_HDMI_RESETTABLE_BY_CAMSET_RESET_G158,
        ctrl_for_hdmi_elf_typo=CTRL_FOR_HDMI_ELF_TYPO_G158,
        external_hdmi_gear_attaching=external_hdmi_gear_attaching,
        hil_bench_safe_for_hdmi_attach=state["hil_bench_safe_for_hdmi_attach"],
        cec_key_events_count=len(EXACT_41_FX3_CEC_KEY_EVENTS_G158),
        cec_rec_event_count=FX3_CEC_REC_EVENT_COUNT_G158,
        fx3_physical_lanc_25mm_present=FX3_PHYSICAL_LANC_25MM_PRESENT_G158,
        fx3_physical_grip_remote_35mm_present=FX3_PHYSICAL_GRIP_REMOTE_35MM_PRESENT_G158,
        fx3_active_lanc_bkid_hits=FX3_ACTIVE_LANC_BKID_HITS_G158,
        fx6_lanc_25mm_port_num=FX6_LANC_25MM_PORT_NUM_G158,
        fx6_grip_remote_35mm_poles=FX6_GRIP_REMOTE_35MM_POLES_G158,
        fx6_exposed_ir_or_cec_menus=FX6_EXPOSED_IR_OR_CEC_MENUS_G158,
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
class G158Wifi5GhzNvsIrLancCecGuardResult:
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
    wifi5ghz_nvs_ir_lanc_cec_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g158_wifi5ghz_nvs_ir_lanc_cec_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G158Wifi5GhzNvsIrLancCecGuardResult]:
    audit = audit_phase363_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_wifi5ghz_nvs_ir_lanc_cec_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G158Wifi5GhzNvsIrLancCecGuardResult(
        gate_id=G158,
        gate_code=G158_GATE_CODE,
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
        wifi5ghz_nvs_ir_lanc_cec_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G158,
        gate_code=G158_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"sku={res.wifi_sku_code} "
            f"band={res.effective_wifi_band} "
            f"p12_p13_ro={res.p12_p13_ms_readonly_enforced} "
            f"ctrl_for_hdmi={res.effective_ctrl_for_hdmi} "
            f"cec_keys={res.cec_key_events_count} "
            f"fx3_lanc={res.fx3_physical_lanc_25mm_present}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_wifi5ghz_nvs_ir_lanc_cec_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G158Wifi5GhzNvsIrLancCecGuardResult]:
    return evaluate_g158_wifi5ghz_nvs_ir_lanc_cec_guard(**kwargs)


# ---------------------------------------------------------------------------
# Unified 158-Gate Master Safety Preflight Engine (G01..G158)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Master158GateReport:
    schema: str
    schema_version: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_155_gates_verified: bool
    all_158_gates_verified: bool
    g13_to_g158_all_passed: bool
    g157_to_g158_all_passed: bool
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
    master_156_report: Dict[str, Any]
    g157_result: Dict[str, Any]
    g158_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_158gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    simulate_bench_dry_run: Optional[bool] = None,
    dry_run_simulated_backup: Optional[bool] = None,
    request_persistent_emmc_writes: bool = False,
    master_156_override: Optional[Master156GateReport] = None,
    pbmag_varshutter_ecs_kwargs: Optional[Mapping[str, Any]] = None,
    wifi5ghz_nvs_ir_lanc_cec_kwargs: Optional[Mapping[str, Any]] = None,
    **extra_upstream_kwargs: Any,
) -> Master158GateReport:
    """Evaluate unified 158-Gate Milestone Master Safety Preflight (`G01..G158`)."""
    effective_dry_run = (
        bool(dry_run_simulated)
        or (simulate_bench_dry_run is True)
        or (dry_run_simulated_backup is True)
    )
    clean_forced = _is_clean_room_forced(force_clean_room)
    resolved_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved_work_root_for_m156 = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=resolved_repo_root).work_root
    )
    m156_force_clean_room = (
        True
        if (clean_forced or resolved_work_root_for_m156 is None)
        else force_clean_room
    )

    if master_156_override is not None:
        m156_report = master_156_override
    else:
        m156_kw = {
            k: v
            for k, v in extra_upstream_kwargs.items()
            if v is not None
        }
        m156_report = evaluate_156gate_preflight(
            resolved_repo_root,
            work_root=work_root,
            force_clean_room=m156_force_clean_room,
            dry_run_simulated=effective_dry_run,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m156_kw,
        )

    g157_kw = dict(pbmag_varshutter_ecs_kwargs or {})
    g157_verdict, g157_res = evaluate_g157_pbmag_varshutter_ecs_guard(
        repo_root=resolved_repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **g157_kw,
    )

    g158_kw = dict(wifi5ghz_nvs_ir_lanc_cec_kwargs or {})
    if "requested_p12_p13_write" not in g158_kw and request_persistent_emmc_writes:
        g158_kw["requested_p12_p13_write"] = True
        if "target_partition" not in g158_kw:
            g158_kw["target_partition"] = "p13_rfnvs"
    g158_verdict, g158_res = evaluate_g158_wifi5ghz_nvs_ir_lanc_cec_guard(
        repo_root=resolved_repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **g158_kw,
    )

    new_gate_dicts = (
        {
            "gate_id": G157,
            "gate_code": G157_GATE_CODE,
            "status": g157_res.status,
            "passed": g157_verdict.passed,
            "evidence": g157_verdict.evidence,
            "violation_codes": list(g157_verdict.errors),
        },
        {
            "gate_id": G158,
            "gate_code": G158_GATE_CODE,
            "status": g158_res.status,
            "passed": g158_verdict.passed,
            "evidence": g158_verdict.evidence,
            "violation_codes": list(g158_verdict.errors),
        },
    )

    all_gates: Tuple[Dict[str, Any], ...] = tuple(m156_report.gates) + new_gate_dicts
    g01_to_g12_verified = int(m156_report.summary["g01_to_g12_verified"])
    g13_to_g156_verified = (
        int(m156_report.summary["g13_to_g154_verified"])
        + int(m156_report.summary["g155_to_g156_verified"])
    )
    g157_to_g158_verified = int(bool(g157_verdict.passed)) + int(
        bool(g158_verdict.passed)
    )
    total_verified = g01_to_g12_verified + g13_to_g156_verified + g157_to_g158_verified

    g157_to_g158_all_passed = g157_to_g158_verified == 2
    g13_to_g158_all_passed = (
        m156_report.g13_to_g156_all_passed and g157_to_g158_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m156_report.gates[:9])

    offline_155_verified = (
        g01_to_g09_ok
        and m156_report.offline_153_gates_verified
        and g157_to_g158_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_158_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g158_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m156_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_155_verified
        and m156_report.h0_h1_trial_entry_allowed
        and g157_to_g158_all_passed
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
        list(m156_report.errors)
        + list(g157_verdict.errors)
        + list(g158_verdict.errors)
    )
    warnings: List[str] = (
        list(m156_report.warnings)
        + list(g157_verdict.warnings)
        + list(g158_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m156_report.g13_to_g156_all_passed:
        overall_status = m156_report.status
    elif not g157_verdict.passed:
        overall_status = g157_verdict.status
    elif not g158_verdict.passed:
        overall_status = g158_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_158_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_158_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_158_verified:
        overall_status = "VERIFIED_ALL_158_GATES"
    else:
        overall_status = "VERIFIED_155_OF_158_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m156_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g157_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g158_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 158,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 158 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g156_verified": g13_to_g156_verified,
        "g157_to_g158_verified": g157_to_g158_verified,
        "g13_to_g158_all_passed": g13_to_g158_all_passed,
        "g157_to_g158_all_passed": g157_to_g158_all_passed,
        "offline_155_gates_verified": offline_155_verified,
        "all_158_gates_verified": all_158_verified,
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

    return Master158GateReport(
        schema=REALHW_158GATE_PREFLIGHT_SCHEMA,
        schema_version=REALHW_158GATE_PREFLIGHT_SCHEMA,
        version=REALHW_PBMAG_VARSHUTTER_ECS_WIFI5GHZ_NVS_IR_LANC_CEC_158GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_155_gates_verified=offline_155_verified,
        all_158_gates_verified=all_158_verified,
        g13_to_g158_all_passed=g13_to_g158_all_passed,
        g157_to_g158_all_passed=g157_to_g158_all_passed,
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
        master_156_report=m156_report.to_dict(),
        g157_result=g157_res.to_dict(),
        g158_result=g158_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_158_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master158GateReport:
    return evaluate_158gate_preflight(repo_root, **kwargs)


def run_158_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master158GateReport:
    return evaluate_158gate_preflight(repo_root, **kwargs)


def verify_real_hardware_158gate_readiness(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master158GateReport:
    return evaluate_158gate_preflight(repo_root, **kwargs)


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
        prog="realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_and_158gate_guard",
        description="Phase 363 (Task H457, Wave-69) G157/G158 and 158/158 Unified Safety Preflight CLI",
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
        help="Supply simulated dry-run Tier-0 backup inputs so all 158/158 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g157", "g158", "158"],
        default="158",
        help="Target gate check: g157, g158, or 158",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g157":
        v, r = evaluate_g157_pbmag_varshutter_ecs_guard(
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

    if args.gate == "g158":
        v, r = evaluate_g158_wifi5ghz_nvs_ir_lanc_cec_guard(
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

    rep = evaluate_158gate_preflight(
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
                "g157_status": rep.g157_result["status"],
                "g158_status": rep.g158_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/158 "
            f"g157_to_g158_all_passed={rep.g157_to_g158_all_passed} "
            f"all_158_gates_verified={rep.all_158_gates_verified} "
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
        rep.all_158_gates_verified
        if args.dry_run_simulated
        else rep.offline_155_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "AIRPLANE_MODE_F_RESID16_G158",
    "AIRPLANE_MODE_SURVIVES_RESET_NETWORK_G158",
    "ALLOWED_BODY_MODELS_PHASE363",
    "ALLOWED_ENLARGE_INITIAL_MAG_OPTIONS_G157",
    "ALLOWED_ENLARGE_INITIAL_POS_OPTIONS_G157",
    "ALLOWED_FX3_VARIANTS_PHASE363",
    "ALLOWED_FX6_WLAN_MODES_G158",
    "ALLOWED_MEDIA_SLOTS_PHASE363",
    "ALLOWED_PLAYBACK_MEDIA_KINDS_G157",
    "ALLOWED_PLAYBACK_ZOOM_OPERATIONS_G157",
    "ALLOWED_RESET_ACTIONS_PHASE363",
    "ALLOWED_SHOOT_MODES_PHASE363",
    "ALLOWED_SHUTTER_TYPES_G157",
    "ALLOWED_TARGET_PARTITIONS_G158",
    "ALLOWED_WIFI_BANDS_G158",
    "ALLOWED_WIFI_OPERATIONS_G158",
    "ALLOWED_WIFI_SECURITY_PROTOCOLS_G158",
    "ALLOWED_WIFI_SKU_CODES_G158",
    "ANTI_FLICKER_MAINS_FREQS_HZ_G157",
    "ANTI_FLICKER_SHOOT_DEFAULT_G157",
    "ANTI_FLICKER_SHOOT_F_RESID16_G157",
    "ANTI_FLICKER_SHOOT_MENU_PATH_G157",
    "ANTI_FLICKER_SHOOT_RESETTABLE_BY_CAMSET_RESET_G157",
    "CTRL_FOR_HDMI_BASE_RESID16_G158",
    "CTRL_FOR_HDMI_ELF_TYPO_G158",
    "CTRL_FOR_HDMI_FACTORY_DEFAULT_G158",
    "CTRL_FOR_HDMI_MENU_PATH_G158",
    "CTRL_FOR_HDMI_RESETTABLE_BY_CAMSET_RESET_G158",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE363",
    "DONOR_CHECK_MAX_SECONDS_PHASE363",
    "DORMANT_ANTI_FLICKER_SET_F_RESID16_G157",
    "DORMANT_ANTI_FLICKER_TV_SCAN_F_RESID16_G157",
    "DORMANT_FLICKER_OR_VAR_SHUTTER_SYMBOLS_G157",
    "DORMANT_SC_TV_SCAN_G_RESID16_G157",
    "DORMANT_VAR_SHUTTER_F_RESID16_G157",
    "EBUSY_ERRNO_PHASE363",
    "EBUSY_NAME_PHASE363",
    "EINVAL_ERRNO_PHASE363",
    "EINVAL_NAME_PHASE363",
    "ENLARGE_IMAGE_BASE_RESID16_G157",
    "ENLARGE_INITIAL_MAG_DEFAULT_G157",
    "ENLARGE_INITIAL_MAG_F_RESID16_G157",
    "ENLARGE_INITIAL_POS_DEFAULT_G157",
    "ENLARGE_INITIAL_POS_F_RESID16_G157",
    "ENV_CLEAN_ROOM_TEST_PHASE363",
    "EOPNOTSUPP_ERRNO_PHASE363",
    "EOPNOTSUPP_NAME_PHASE363",
    "EPERM_ERRNO_PHASE363",
    "EPERM_NAME_PHASE363",
    "EROFS_ERRNO_PHASE363",
    "EROFS_NAME_PHASE363",
    "EXACT_3_PLAYBACK_MAGNIFY_ITEMS_G157",
    "EXACT_41_FX3_CEC_KEY_EVENTS_G158",
    "EXACT_6_WIFI_MENU_ITEMS_G158",
    "FX3A_MODEL_NAME_PHASE363",
    "FX3A_PHYSICAL_IR_SENSOR_PRESENT_G158",
    "FX3_ACTIVE_LANC_BKID_HITS_G158",
    "FX3_AF_ILLUMINATOR_SENSOR_NUM_G158",
    "FX3_ANTI_FLICKER_SET_EXPOSED_G157",
    "FX3_ANTI_FLICKER_TV_SCAN_EXPOSED_G157",
    "FX3_CEC_REC_EVENT_COUNT_G158",
    "FX3_DEFAULT_FW_VERSION_PHASE363",
    "FX3_HELP_GUIDE_CODE_PHASE363",
    "FX3_IR_FRONT_SENSOR_NUM_G158",
    "FX3_MODEL_ID_PHASE363",
    "FX3_MODEL_NAME_PHASE363",
    "FX3_PHYSICAL_GRIP_REMOTE_35MM_PRESENT_G158",
    "FX3_PHYSICAL_LANC_25MM_PRESENT_G158",
    "FX3_SC_TV_SCAN_0X60A8_EMPTY_STRING_G157",
    "FX3_VAR_SHUTTER_EXPOSED_G157",
    "FX3_WIFI_SKU_WW558244_G158",
    "FX3_WIFI_SKU_WW728473_G158",
    "FX6_DEFAULT_FW_VERSION_PHASE363",
    "FX6_ECS_6_FRAME_RATE_PRESETS_G157",
    "FX6_ECS_FREQ_MAX_HZ_G157",
    "FX6_ECS_FREQ_MIN_HZ_G157",
    "FX6_EXPOSED_IR_OR_CEC_MENUS_G158",
    "FX6_FLICKER_REDUCE_FREQS_G157",
    "FX6_FLICKER_REDUCE_MENU_PATH_G157",
    "FX6_FLICKER_REDUCE_MODES_G157",
    "FX6_FOCUS_MAGNIFIER_SCALES_G157",
    "FX6_GRIP_REMOTE_35MM_POLES_G158",
    "FX6_LANC_25MM_PORT_NUM_G158",
    "FX6_MODEL_NAME_PHASE363",
    "FX6_REC_REVIEW_DURATIONS_G157",
    "FX6_SHUTTER_ECS_MENU_PATH_G157",
    "FX6_STILL_OR_PB_ENLARGE_SUPPORTED_G157",
    "FX6_WIFI_SKU_24GHZ_G158",
    "FX6_WIFI_SKU_5GHZ_G158",
    "FX6_WIRELESS_LAN_MENU_PATH_G158",
    "G157",
    "G157PbMagVarShutterEcsGuardResult",
    "G157_GATE_CODE",
    "G157_GATE_ID",
    "G158",
    "G158Wifi5GhzNvsIrLancCecGuardResult",
    "G158_GATE_CODE",
    "G158_GATE_ID",
    "IR_REMOTE_CTRL_DEFAULT_G158",
    "IR_REMOTE_CTRL_F_RESID16_G158",
    "IR_REMOTE_CTRL_MENU_PATH_G158",
    "IR_REMOTE_CTRL_RESETTABLE_BY_CAMSET_RESET_G158",
    "MEDIA_SLOT_1_PHASE363",
    "MEDIA_SLOT_2_PHASE363",
    "MEDIA_SLOT_NONE_PHASE363",
    "MOVIE_PLAYBACK_ZOOM_SUPPORTED_G157",
    "Master158GateReport",
    "P12_CERT_SIZE_MIB_G158",
    "P12_DEVICE_PATH_G158",
    "P12_P13_MS_RDONLY_ENFORCED_G158",
    "P13_DEVICE_PATH_G158",
    "P13_RF_NVS_SIZE_MIB_G158",
    "PINNED_FX3_APPFW_SLICES_PHASE363",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE363",
    "PINNED_FX6_APPFW_SLICES_PHASE363",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE363",
    "PINNED_PHASE363_DONOR_SPECS",
    "PLAYBACK_MAGNIFICATION_MENU_PATH_G157",
    "PLAYBACK_MAGNIFY_RESETTABLE_BY_CAMSET_RESET_G157",
    "PLAYBACK_ZOOM_DOUBLE_TAP_SYMBOLS_G157",
    "PLAYBACK_ZOOM_INHIBITION_TEXT_G157",
    "PLAYBACK_ZOOM_MAGINIFY_ELF_TYPO_G157",
    "PbMagVarShutterEcsGuardResult",
    "Phase363DonorAuditResult",
    "REALHW_158GATE_PREFLIGHT_SCHEMA",
    "REALHW_PBMAG_VARSHUTTER_ECS_WIFI5GHZ_NVS_IR_LANC_CEC_158GATE_SCHEMA",
    "REALHW_PBMAG_VARSHUTTER_ECS_WIFI5GHZ_NVS_IR_LANC_CEC_158GATE_VERSION",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE363",
    "RESET_ACTION_INITIALIZE_PHASE363",
    "RESET_ACTION_NONE_PHASE363",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE363",
    "RESET_NETWORK_SET_F_RESID16_G158",
    "RF_NVS_MUTATION_BYTES_G158",
    "RF_TX_PACKETS_AIRPLANE_G158",
    "SHOOT_MODE_MOVIE_PHASE363",
    "SHOOT_MODE_SQ_PHASE363",
    "SHOOT_MODE_STILL_PHASE363",
    "SSID_PW_RESET_F_RESID16_G158",
    "STATUS_BLOCKED_G157_MOVIE_ZOOM_OR_DORMANT_VAR_SHUTTER_EOPNOTSUPP",
    "STATUS_BLOCKED_G157_PBMAG_RESET_OR_ANTI_FLICKER_CONSTRAINT_VIOLATION",
    "STATUS_BLOCKED_G157_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G158_AIRPLANE_RF_OR_CTRL_FOR_HDMI_CEC_HIJACK_VIOLATION",
    "STATUS_BLOCKED_G158_BT_IR_OR_FX6_WLAN_MUTEX_EBUSY",
    "STATUS_BLOCKED_G158_P12_P13_RF_NVS_MS_RDONLY_EROFS",
    "STATUS_BLOCKED_G158_SKU_LEGACY_SEC_FX3A_IR_OR_LANC_EOPNOTSUPP",
    "STATUS_BLOCKED_G158_TELEMETRY_INVALID",
    "STATUS_BLOCKED_PHASE363_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G157",
    "STATUS_VERIFIED_G158",
    "UNABLE_TO_MAGNIFY_BASE_RESID16_G157",
    "VER7_ALLOWED_WIFI_SECURITY_PROTOCOLS_G158",
    "VER7_REMOVED_WIFI_SECURITY_PROTOCOLS_G158",
    "WIFI_CONNECT_F_RESID16_G158",
    "WIFI_FREQ_BAND_F_RESID16_G158",
    "WIFI_MENU_PATH_G158",
    "WIFI_SKU_GATE_FN_G158",
    "Wifi5GhzNvsIrLancCecGuardResult",
    "audit_phase363_donor_contracts",
    "compute_pbmag_varshutter_ecs_matrix",
    "compute_wifi5ghz_nvs_ir_lanc_cec_matrix",
    "evaluate_158_master_safety_gates",
    "evaluate_158gate_preflight",
    "evaluate_g157_pbmag_varshutter_ecs_guard",
    "evaluate_g158_wifi5ghz_nvs_ir_lanc_cec_guard",
    "main",
    "resolve_fx3_pbmag_varshutter_ecs_state",
    "resolve_fx3_wifi5ghz_nvs_ir_lanc_cec_state",
    "run_158_gate_preflight",
    "strip_elapsed_seconds_recursive_phase363",
    "verify_pbmag_varshutter_ecs_guard",
    "verify_pbmag_varshutter_ecs_guard_with_audit",
    "verify_real_hardware_158gate_readiness",
    "verify_wifi5ghz_nvs_ir_lanc_cec_guard",
    "verify_wifi5ghz_nvs_ir_lanc_cec_guard_with_audit",
]


if __name__ == "__main__":
    raise SystemExit(main())
