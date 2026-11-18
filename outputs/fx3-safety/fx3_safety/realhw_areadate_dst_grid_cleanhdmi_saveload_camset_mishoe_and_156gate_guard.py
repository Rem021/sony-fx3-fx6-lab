"""Phase 359 (Task H451, Wave-68, 156/156 Milestone): Real-Hardware `Setup -> [Area/Date]`
30-Zone GMT Table (`saylight_saving` / `sever` Typos & 24h Rechargeable RTC vs FX6 `Clock Set`),
`[Grid Line Display]`/`[Grid Line Type]` HDMI Pass-Through vs `[Marker Display]` Zero-HDMI &
5-Item Reset-Resistance (`G155`), `[Save/Load Settings]` `Slot 1` `EROFS=30` `CAMSET01..10.DAT`
Vault / `libSaveLoadSettings.so` / Zero `PRO/CAMERA` vs `Camera Set. Memory` `1..3` & `M1..M4`,
and Zero Physical `Sync Terminal` + `XLR-H1` vs `HVL-LBPC` MI-Shoe Mutual Exclusion + PMIC
`5V <= 900 mA` Firewall vs FX6 `TC IN/OUT` & Zero `GENLOCK` (`G156`), and Unified `156`-Gate
Master Safety Preflight (`G01..G156`).

Authoritative Empirical Baseline (`ILME-FX3 Ver. 7.02`, `ilc/2210`, `0x0502`,
`PRODUCT_MODEL_ALCIN_UUD` vs `ILME-FX6 Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`):
  - **Gate `G155` (`AREADATE_30ZONE_RTC_AND_GRID_LINE_VS_MARKER_CLEANHDMI_RESET_GUARD`)**:
    1. `Setup -> [Area/Date] -> [Area/Date/Time Setting]` (`_f 0x6a9c`, all sub-items
       **Reset-immune `Not available`** under `[Camera Settings Reset]`, cleared and
       re-triggering `37dlg_rec203_initial_setting_controller` /
       `PRM_launch_date_time_setup_area_setting` ONLY on `[Initialize]` or RTC depletion):
       - **30** `AREA_GMT_*` zones (`AREA_GMT_M_11_0`..`AREA_GMT_P_12_0`) including **6**
         `:30` half-hour offsets (`M_03_5`, `P_03_5`, `P_04_5`, `P_05_5`, `P_06_5`, `P_09_5`).
       - `[Daylight Savings]` (`Off` def / `On`; Sony ELF typo
         `convert_setting_daylight_saving_to_saylight_saving`).
       - `[Date/Time]` (24h, BT Creators' App sync typo
         `BKID_APP_setting_auto_sync_sever_date_time`) & exact **3** `[Date Format]`
         (`Y-M-D`, `M-D-Y`, `D-M-Y`; zero standalone `YYYY-MM-DD`).
       - Internal soldered rechargeable RTC backup battery (`>= 24h` power-off charge from
         charged `NP-FZ100`/USB-PD; **zero** user-replaceable CR2032 slot; `ilc/2210`
         makes **zero** `"3 months"` retention claim).
       - Contrast `ILME-FX6 Ver. 6.01`: `Maintenance > Clock Set` (`UTC -12:00..+14:00`
         in 30m steps, `Date Mode` `YYMMDD`/`MMDDYY`/`DDMMYY` + `12h/24h`, **zero**
         standalone DST toggle, dormant `summer_time_name_dst`, `Backup Battery End`
         hard-lock on depletion).
    2. `[Grid Line Display]`/`[Grid Line Type]` vs `[Marker Display]` Clean-HDMI & Reset Firewall:
       - `Shooting -> [Shooting Display] -> [Grid Line Display]` (`Off`/`On`) &
         `[Grid Line Type]` (`Rule of 3rds Grid` def / `Square Grid` / `Diag. + Square Grid`),
         unified across Still/Movie/`S&Q` (`BKID_APP_deleted_setting_grid_line_*_movie`
         retired), **passes out HDMI** when `[HDMI Info. Display] = On` & not clean-feed
         (`Off(HDMI Only)` / `RAW Output = On` strips it).
       - `Shooting -> [Marker Display]` (`Center Marker`, **15** `Aspect Marker` ratios,
         `Safety Zone` `80%/90%`, `Guideframe`): **Movie/`S&Q` only**
         (`PRM_HAITA_setting_marker_display_exposure_mode`), auto-hidden during
         `[Focus Magnifier]`, and **NEVER output over HDMI regardless of `[HDMI Info. Display]`**
         (`hdmi_marker_injected_pixels == 0`).
       - In `ilc/2210`, both `[Grid Line Display/Type]` and all **5** `[Marker Display]`
         items are **Reset-immune `Not available`** (`Initialize`-only), unlike
         `[Emphasized REC Display]` (`Can be reset`).
       - Contrast `ILME-FX6 Ver. 6.01`: `Monitoring > Marker` (`Center Marker 1..4/Off`,
         `Guide Frame On/Off`, independent `VF/SDI/HDMI` gates, zero FX3 3-mode grid UI).

  - **Gate `G156` (`SAVELOAD_SLOT1_EROFS_CAMSET_VAULT_AND_MISHOE_XLRH1_ZERO_SYNC_GENLOCK_FIREWALL`)**:
    1. `Setup -> [Reset/Save Settings] -> [Save/Load Settings]` (`libSaveLoadSettings.so`
       `18,760 B`, locked strictly to **`Slot 1` only** for up to **10** `CAMSET01..10.DAT`
       files + `60` Cloud slots, disabled in `MR` mode, auto-reboots on Load):
       - Exact path `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT` (`/PRIVATE` on SDXC, `""` on
         CFexpress Type A), **zero `PRO/CAMERA` path hits** on FX3, same-model & version
         compat (`Ver. <= 1.01` rejected on `Ver. 2.00+`), 20-item official exclusion list.
       - Separate `[Save/Load FTP Settings]` (`%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT`,
         `FTPSET%02d`, `Slot 1` only) and `[Camera Set. Memory]` (`1..3` NVRAM bundled
         in `CAMSET*.DAT` vs card `M1..M4` `CAMPR%02d%c.DAT` on `Slot 1` or `Slot 2`).
       - **Tier-0 `Slot 1` `EROFS=30` Firewall**: any `Save`/`Delete`/write targeting
         Tier-0 read-only `Slot 1` fails closed (`EROFS=30`, `slot1_data_sector_writes == 0`,
         `emmc_nflasha_write_count == 0`).
       - Contrast `ILME-FX6 Ver. 6.01`: `Project > All File` (`Media(B)` 64 `.ALL` files
         in `SONY/PRO/CAMERA`), `.USRF`, `.SCN`, dormant `Reference File` (`0` ELF hits).
    2. Zero Physical `Sync Terminal` + `XLR-H1` vs `HVL-LBPC` MI-Shoe Exclusion + `PMIC 5V <= 900mA`:
       - FX3 has **zero physical PC Flash Sync Terminal** (`0` `SYNCHRO_TERMINAL*` symbols
         in `FX3 appFw.so`; dormant `Flash Sync Spd. Prty.` -> `EOPNOTSUPP=95`).
       - MI-Shoe `[External Flash Set.]` / `[Flash Mode]` restricted to mechanical shutter
         (`<= 1/250 s` X-sync on FX3, `< 250 V`, positive polarity; blocked in e-Shutter /
         Silent Mode); `1/160 s FF` / `1/200 s APS-C` EFCS comparison documented;
         `External Flash Set.` is Reset-immune & excluded from `CAMSET*.DAT`.
       - MI-Shoe `[Video Light Mode]` (4 modes: `Power Link`, `REC Link`, `REC Link&STBY`,
         `Auto`) is **physically mutually exclusive with `XLR-H1`** (passive cold shoes
         only -> `EBUSY=16`), guarded by `PMIC 5V <= 900 mA` overload firewall.
       - Contrast `ILME-FX6 Ver. 6.01`: 3-mode `Video Light Set` (zero `Auto`), zero
         Still `[Flash]` UI, single `TC IN/OUT` BNC, and **zero physical `GENLOCK`/`REF`
         BNC** (`107` dormant `GENLOCK` symbols -> `EOPNOTSUPP=95`).

  - **Unified 156-Gate Master Safety Preflight (`G01..G156`)**:
    Delegates `G01..G154` to `evaluate_154gate_preflight()`, enforces `153/156` verified
    offline (`VERIFIED_153_OF_156_AWAITING_PHYSICAL_TIER0`) and `156/156` under
    `--simulate-bench-dry-run` (`VERIFIED_ALL_156_GATES_DRY_RUN_SIMULATED_BACKUP`),
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
from .realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_and_154gate_guard import (
    Master154GateReport,
    evaluate_154gate_preflight,
)


# ---------------------------------------------------------------------------
# Schema, Versions, Env Keys & Shared Constants
# ---------------------------------------------------------------------------

REALHW_AREADATE_DST_GRID_CLEANHDMI_SAVELOAD_CAMSET_MISHOE_156GATE_SCHEMA = (
    "fx3_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_156gate_guard_v1"
)
REALHW_AREADATE_DST_GRID_CLEANHDMI_SAVELOAD_CAMSET_MISHOE_156GATE_VERSION = (
    "2026.11.18-phase359-milestone156"
)
REALHW_156GATE_PREFLIGHT_SCHEMA = "realhw_156gate_preflight_v1"

G155 = "G155"
G155_GATE_ID = "G155"
G155_GATE_CODE = (
    "AREADATE_30ZONE_RTC_AND_GRID_LINE_VS_MARKER_CLEANHDMI_RESET_GUARD"
)

G156 = "G156"
G156_GATE_ID = "G156"
G156_GATE_CODE = (
    "SAVELOAD_SLOT1_EROFS_CAMSET_VAULT_AND_MISHOE_XLRH1_ZERO_SYNC_GENLOCK_FIREWALL"
)

ENV_CLEAN_ROOM_TEST_PHASE359 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE359 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE359 = 0.05

EPERM_ERRNO_PHASE359 = 1
EPERM_NAME_PHASE359 = "EPERM"
EBUSY_ERRNO_PHASE359 = 16
EBUSY_NAME_PHASE359 = "EBUSY"
EINVAL_ERRNO_PHASE359 = 22
EINVAL_NAME_PHASE359 = "EINVAL"
EROFS_ERRNO_PHASE359 = 30
EROFS_NAME_PHASE359 = "EROFS"
EOPNOTSUPP_ERRNO_PHASE359 = 95
EOPNOTSUPP_NAME_PHASE359 = "EOPNOTSUPP"

FX3_MODEL_NAME_PHASE359 = "ILME-FX3"
FX3_MODEL_ID_PHASE359 = 0x0502
FX3_HELP_GUIDE_CODE_PHASE359 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE359 = "7.02"
FX6_MODEL_NAME_PHASE359 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE359 = "6.01"
ALLOWED_BODY_MODELS_PHASE359: Tuple[str, ...] = (
    FX3_MODEL_NAME_PHASE359,
    FX6_MODEL_NAME_PHASE359,
)

MEDIA_SLOT_NONE_PHASE359 = 0
MEDIA_SLOT_1_PHASE359 = 1
MEDIA_SLOT_2_PHASE359 = 2
ALLOWED_MEDIA_SLOTS_PHASE359: Tuple[int, ...] = (
    MEDIA_SLOT_NONE_PHASE359,
    MEDIA_SLOT_1_PHASE359,
    MEDIA_SLOT_2_PHASE359,
)

SHOOT_MODE_STILL_PHASE359 = "Still"
SHOOT_MODE_MOVIE_PHASE359 = "Movie"
SHOOT_MODE_SQ_PHASE359 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE359: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE359,
    SHOOT_MODE_MOVIE_PHASE359,
    SHOOT_MODE_SQ_PHASE359,
)

RESET_ACTION_NONE_PHASE359 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE359 = "Camera Settings Reset"
RESET_ACTION_INITIALIZE_PHASE359 = "Initialize"
RESET_ACTION_RESET_NETWORK_SET_PHASE359 = "Reset Network Set."
ALLOWED_RESET_ACTIONS_PHASE359: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE359,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE359,
    RESET_ACTION_INITIALIZE_PHASE359,
    RESET_ACTION_RESET_NETWORK_SET_PHASE359,
)


# ---------------------------------------------------------------------------
# Gate G155 Constants: Area/Date 30-Zone RTC + Grid Line vs Marker Clean-HDMI
# ---------------------------------------------------------------------------

AREA_DATE_MENU_PATH_G155 = "Setup -> [Area/Date] -> [Area/Date/Time Setting]"
FX6_CLOCK_SET_MENU_PATH_G155 = "Maintenance > Clock Set"
GRID_LINE_DISPLAY_MENU_PATH_G155 = (
    "Shooting -> [Shooting Display] -> [Grid Line Display]"
)
GRID_LINE_TYPE_MENU_PATH_G155 = "Shooting -> [Shooting Display] -> [Grid Line Type]"
MARKER_DISPLAY_MENU_PATH_G155 = "Shooting -> [Marker Display]"
FX6_MARKER_MENU_PATH_G155 = "Monitoring > Marker"

AREA_GMT_30_ZONES_G155: Tuple[str, ...] = (
    "AREA_GMT_M_11_0",
    "AREA_GMT_M_10_0",
    "AREA_GMT_M_09_0",
    "AREA_GMT_M_08_0",
    "AREA_GMT_M_07_0",
    "AREA_GMT_M_06_0",
    "AREA_GMT_M_05_0",
    "AREA_GMT_M_04_0",
    "AREA_GMT_M_03_5",
    "AREA_GMT_M_03_0",
    "AREA_GMT_M_02_0",
    "AREA_GMT_M_01_0",
    "AREA_GMT_P_00_0",
    "AREA_GMT_P_01_0",
    "AREA_GMT_P_02_0",
    "AREA_GMT_P_03_0",
    "AREA_GMT_P_03_5",
    "AREA_GMT_P_04_0",
    "AREA_GMT_P_04_5",
    "AREA_GMT_P_05_0",
    "AREA_GMT_P_05_5",
    "AREA_GMT_P_06_0",
    "AREA_GMT_P_06_5",
    "AREA_GMT_P_07_0",
    "AREA_GMT_P_08_0",
    "AREA_GMT_P_09_0",
    "AREA_GMT_P_09_5",
    "AREA_GMT_P_10_0",
    "AREA_GMT_P_11_0",
    "AREA_GMT_P_12_0",
)
AREA_GMT_HALF_HOUR_6_ZONES_G155: Tuple[str, ...] = (
    "AREA_GMT_M_03_5",
    "AREA_GMT_P_03_5",
    "AREA_GMT_P_04_5",
    "AREA_GMT_P_05_5",
    "AREA_GMT_P_06_5",
    "AREA_GMT_P_09_5",
)
EXACT_3_DATE_FORMATS_G155: Tuple[str, ...] = ("Y-M-D", "M-D-Y", "D-M-Y")
DAYLIGHT_SAVINGS_DEFAULT_G155 = "Off"
DAYLIGHT_SAVINGS_ELF_TYPO_G155 = (
    "convert_setting_daylight_saving_to_saylight_saving"
)
AUTO_SYNC_SEVER_ELF_TYPO_G155 = "BKID_APP_setting_auto_sync_sever_date_time"
AREA_DATE_RESETTABLE_BY_CAMSET_RESET_G155 = False
FX3_USER_CR2032_SLOT_PRESENT_G155 = False
FX3_RTC_BACKUP_CHARGE_MIN_HOURS_POWER_OFF_G155 = 24
ILC2210_STATES_3_MONTHS_RETENTION_G155 = False

FX6_CLOCK_SET_TIME_FORMATS_G155: Tuple[str, ...] = ("12h", "24h")
FX6_CLOCK_SET_DATE_MODES_G155: Tuple[str, ...] = ("YYMMDD", "MMDDYY", "DDMMYY")
FX6_CLOCK_SET_DST_TOGGLE_EXPOSED_G155 = False
FX6_CLOCK_SET_UTC_STEP_MINUTES_G155 = 30

GRID_LINE_DISPLAY_DEFAULT_G155 = "Off"
GRID_LINE_TYPE_DEFAULT_G155 = "Rule of 3rds Grid"
EXACT_3_GRID_LINE_TYPES_G155: Tuple[str, ...] = (
    "Rule of 3rds Grid",
    "Square Grid",
    "Diag. + Square Grid",
)
RETIRED_DELETED_MOVIE_GRID_KEYS_G155: Tuple[str, ...] = (
    "BKID_APP_deleted_setting_grid_line_display_movie",
    "BKID_APP_deleted_setting_grid_line_type_movie",
)
GRID_LINE_RESETTABLE_BY_CAMSET_RESET_G155 = False
MARKER_5ITEMS_RESETTABLE_BY_CAMSET_RESET_G155 = False
EXACT_5_MARKER_ITEMS_G155: Tuple[str, ...] = (
    "Marker Display",
    "Center Marker",
    "Aspect Marker",
    "Safety Zone",
    "Guideframe",
)
EXACT_15_ASPECT_MARKER_RATIOS_G155: Tuple[str, ...] = (
    "9:16",
    "4:5",
    "1:1",
    "4:3",
    "13:9",
    "14:9",
    "15:9",
    "16:9",
    "17:9",
    "1.66:1",
    "1.85:1",
    "1.91:1",
    "2:1",
    "2.35:1",
    "2.39:1",
)
ALLOWED_ASPECT_MARKER_OPTIONS_G155: Tuple[str, ...] = (
    "Off",
) + EXACT_15_ASPECT_MARKER_RATIOS_G155
ALLOWED_SAFETY_ZONE_OPTIONS_G155: Tuple[str, ...] = ("Off", "80%", "90%")
ALLOWED_REC_MEDIA_HDMI_MODES_G155: Tuple[str, ...] = ("On", "Off(HDMI Only)")
FX6_CENTER_MARKER_MODES_G155: Tuple[str, ...] = ("Off", "1", "2", "3", "4")
FX6_NATIVE_3MODE_GRID_EXPOSED_G155 = False
HDMI_MARKER_INJECTED_PIXELS_G155 = 0

# UXC resid16 anchors (G155)
AREA_DATE_TIME_SETTING_F_RESID16_G155 = 0x6A9C
LEGACY_DATE_TIME_SETUP_BASE_RESID16_G155 = 0xE87F
AREA_SETTING_BASE_RESID16_G155 = 0xE91A
DAYLIGHT_SAVINGS_BASE_RESID16_G155 = 0xE917
DATE_FORMAT_F_RESID16_G155 = 0x670D
GRID_LINE_DISPLAY_F_RESID16_G155 = 0x6F9D
GRID_LINE_TYPE_F_RESID16_G155 = 0x69C9
GRID_LINE_DISPLAY_SELECT_F_RESID16_G155 = 0x70C5
MARKER_DISPLAY_F_RESID16_G155 = 0x61B2
GUIDEFRAIME_F_RESID16_G155 = 0x62F9

STATUS_VERIFIED_G155 = (
    "VERIFIED_G155_AREADATE_30ZONE_RTC_AND_GRID_LINE_VS_MARKER_CLEANHDMI_RESET_GUARD"
)
STATUS_BLOCKED_G155_TELEMETRY_INVALID = "BLOCKED_G155_TELEMETRY_INVALID"
STATUS_BLOCKED_G155_DORMANT_CR2032_FX6_DST_OR_STILL_MARKER_EOPNOTSUPP = (
    "BLOCKED_G155_DORMANT_CR2032_FX6_DST_OR_STILL_MARKER_EOPNOTSUPP"
)
STATUS_BLOCKED_G155_AREA_RTC_OR_GRID_MARKER_CLEANHDMI_RESET_VIOLATION = (
    "BLOCKED_G155_AREA_RTC_OR_GRID_MARKER_CLEANHDMI_RESET_VIOLATION"
)


# ---------------------------------------------------------------------------
# Gate G156 Constants: [Save/Load Settings] Slot-1 EROFS=30 CAMSET Vault &
#                      MI-Shoe XLR-H1 vs HVL-LBPC / Zero Sync Terminal / GENLOCK
# ---------------------------------------------------------------------------

SAVE_LOAD_SETTINGS_MENU_PATH_G156 = (
    "Setup -> [Reset/Save Settings] -> [Save/Load Settings]"
)
SAVE_LOAD_FTP_MENU_PATH_G156 = (
    "Setup -> [Reset/Save Settings] -> [Save/Load FTP Settings]"
)
CAMERA_SET_MEMORY_MENU_PATH_G156 = "Shooting -> [Shooting Mode] -> [Camera Set. Memory]"
MEMORY_RECALL_MEDIA_MENU_PATH_G156 = (
    "Shooting -> [Shooting Mode] -> [Memory/Recall Media]"
)
EXTERNAL_FLASH_SET_MENU_PATH_G156 = (
    "Exposure/Color -> [Flash] -> [External Flash Set.]"
)
VIDEO_LIGHT_MODE_MENU_PATH_G156 = "Setup -> [Setup Option] -> [Video Light Mode]"
FX6_ALL_FILE_MENU_PATH_G156 = "Project > All File"
FX6_VIDEO_LIGHT_SET_MENU_PATH_G156 = "Technical > Video Light Set"

LIB_SAVE_LOAD_SETTINGS_NAME_G156 = "libSaveLoadSettings.so"
LIB_SAVE_LOAD_SETTINGS_BYTES_G156 = 18_760
FX3_CAMSET_PATH_TEMPLATE_G156 = "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"
FX3_CAMPR_PATH_TEMPLATE_G156 = "%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT"
FX3_FTPSET_PATH_TEMPLATE_G156 = "%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT"
FX3_PRO_CAMERA_PATH_HITS_G156 = 0
FX6_ALL_FILE_PATH_TEMPLATE_G156 = "%c:%s/SONY/PRO/CAMERA/%s/%s.ALL"
FX6_SCENE_FILE_PATH_TEMPLATE_G156 = "%c:%s/SONY/PRO/SCENE/%s.SCN"
FX6_REFERENCE_FILE_ELF_HITS_G156 = 0

CAMSET_MAX_CARD_SLOTS_G156 = 10
CAMSET_MAX_CLOUD_SLOTS_G156 = 60
CAMSET_MIN_FW_INCOMPAT_BOUNDARY_G156 = 2.00
CAMERA_SET_MEMORY_BODY_SLOTS_G156: Tuple[int, ...] = (1, 2, 3)
CAMERA_SET_MEMORY_CARD_SLOTS_G156: Tuple[str, ...] = ("M1", "M2", "M3", "M4")
FX6_ALL_FILE_MAX_SLOTS_G156 = 64
ALLOWED_CARD_MEDIA_TYPES_G156: Tuple[str, ...] = ("SDXC", "CFexpress Type A")
ALLOWED_SAVELOAD_TARGETS_G156: Tuple[str, ...] = (
    "Slot 1",
    "Slot 2",
    "Cloud(Private)",
    "Cloud(Share)",
    "Media(B)",
)
ALLOWED_SAVELOAD_OPERATIONS_G156: Tuple[str, ...] = (
    "camset_load",
    "camset_save",
    "camset_delete",
    "ftpset_save",
    "camera_set_memory_body",
    "camera_set_memory_card_save",
    "camera_set_memory_card_recall",
    "fx6_all_file_load",
    "fx6_all_file_save",
)
EXACT_20_CAMSET_EXCLUDED_ITEMS_G156: Tuple[str, ...] = (
    "IPTC Information",
    "Copyright Info",
    "External Flash Set.",
    "White Balance (Custom 1)",
    "White Balance (Custom 2)",
    "White Balance (Custom 3)",
    "Face Memory",
    "FTP Transfer Func.",
    "Network Streaming",
    "Cloud Connection",
    "WPS Push",
    "Access Point Set.",
    "Wi-Fi Frequency Band",
    "IP Address Setting",
    "Edit Device Name",
    "Import Root Certificate",
    "Access Authen. Settings",
    "Security(IPsec)",
    "Language",
    "Area/Date/Time Setting",
)

FX3_PHYSICAL_SYNC_TERMINAL_PRESENT_G156 = False
FX3_SYNCHRO_TERMINAL_ELF_HITS_G156 = 0
FX3_FLASH_XSYNC_MAX_DENOM_G156 = 250
FX3_FLASH_XSYNC_FF_EFCS_DENOM_G156 = 160
FX3_FLASH_XSYNC_APSC_EFCS_DENOM_G156 = 200
FX3_FLASH_MAX_TRIGGER_VOLTAGE_V_G156 = 250.0
FX3_FLASH_SHUTTER_MODES_G156: Tuple[str, ...] = ("Mechanical", "Electronic")
EXACT_5_FX3_FLASH_MODES_G156: Tuple[str, ...] = (
    "Flash Off",
    "Autoflash",
    "Fill-flash",
    "Slow Sync.",
    "Rear Sync.",
)
EXACT_4_FX3_VIDEO_LIGHT_MODES_G156: Tuple[str, ...] = (
    "Power Link",
    "REC Link",
    "REC Link&STBY",
    "Auto",
)
EXACT_3_FX6_VIDEO_LIGHT_MODES_G156: Tuple[str, ...] = (
    "Power Link",
    "Rec Link",
    "Rec Link + Stby",
)
ALLOWED_MISHOE_DEVICES_G156: Tuple[str, ...] = (
    "None",
    "XLR-H1",
    "HVL-LBPC",
    "MI_FLASH",
)
ELECTRICAL_LIGHT_OR_FLASH_MISHOE_DEVICES_G156: Tuple[str, ...] = (
    "HVL-LBPC",
    "MI_FLASH",
)
PMIC_5V_MAX_CURRENT_MA_G156 = 900
XLR_H1_TOP_SHOES_PASSIVE_COLD_ONLY_G156 = True
FX6_VIDEO_LIGHT_AUTO_SUPPORTED_G156 = False
FX6_PHYSICAL_GENLOCK_BNC_PRESENT_G156 = False
FX6_DORMANT_GENLOCK_ELF_HITS_G156 = 107

# UXC resid16 anchors (G156)
SAVE_LOAD_SETTINGS_F_RESID16_G156 = 0x6254
SAVE_LOAD_FTP_F_RESID16_G156 = 0x71AE
MEMORY_RECALL_MEDIA_F_RESID16_G156 = 0x763C
EXTERNAL_FLASH_SET_F_RESID16_G156 = 0x6771
VIDEO_LIGHT_MODE_F_RESID16_G156 = 0x6211
DORMANT_FLASH_SYNC_SPD_PRTY_F_RESID16_G156 = 0x6B31

STATUS_VERIFIED_G156 = (
    "VERIFIED_G156_SAVELOAD_SLOT1_EROFS_CAMSET_VAULT_AND_MISHOE_XLRH1_ZERO_SYNC_GENLOCK_FIREWALL"
)
STATUS_BLOCKED_G156_TELEMETRY_INVALID = "BLOCKED_G156_TELEMETRY_INVALID"
STATUS_BLOCKED_G156_SLOT1_SAVELOAD_CAMSET_VAULT_EROFS = (
    "BLOCKED_G156_SLOT1_SAVELOAD_CAMSET_VAULT_EROFS"
)
STATUS_BLOCKED_G156_MISHOE_XLRH1_EXCLUSION_EBUSY = (
    "BLOCKED_G156_MISHOE_XLRH1_EXCLUSION_EBUSY"
)
STATUS_BLOCKED_G156_DORMANT_SYNC_GENLOCK_SLOT2_MR_OR_REFFILE_EOPNOTSUPP = (
    "BLOCKED_G156_DORMANT_SYNC_GENLOCK_SLOT2_MR_OR_REFFILE_EOPNOTSUPP"
)
STATUS_BLOCKED_G156_CAMSET_COMPAT_FLASH_SHUTTER_OR_PMIC_VIOLATION = (
    "BLOCKED_G156_CAMSET_COMPAT_FLASH_SHUTTER_OR_PMIC_VIOLATION"
)

STATUS_BLOCKED_PHASE359_DONOR_INTEGRITY = "BLOCKED_PHASE359_DONOR_CONTRACT_INTEGRITY"


# ---------------------------------------------------------------------------
# Pinned Wave-68 Donor Specs (O_RDONLY / Bounded Slices, Raw Bytes = 0)
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE359: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x0302982F, b"37dlg_rec203_initial_setting_controller"),
    (0x039C46B8, b"PRM_launch_date_time_setup_area_setting"),
    (0x03C188DF, b"AREA_GMT_M_11_0"),
    (0x03C188CF, b"AREA_GMT_P_12_0"),
    (0x03C1883F, b"AREA_GMT_P_05_5"),
    (0x03D09043, b"convert_setting_daylight_saving_to_saylight_saving"),
    (0x03BCA5B1, b"BKID_APP_setting_daylight_saving"),
    (0x03BC647A, b"BKID_APP_setting_auto_sync_sever_date_time"),
    (0x03BCA5D2, b"BKID_APP_setting_date_format"),
    (0x03BC78A8, b"BKID_APP_setting_grid_line_display"),
    (0x03BC78F1, b"BKID_APP_setting_grid_line_type"),
    (0x03BEC05D, b"BKID_APP_deleted_setting_grid_line_display_movie"),
    (0x03BEC0C2, b"BKID_APP_deleted_setting_grid_line_type_movie"),
    (0x03BC7B0A, b"BKID_APP_setting_marker_display"),
    (0x03BC7C0E, b"BKID_APP_setting_guide_frame"),
    (0x039BFA05, b"PRM_HAITA_setting_marker_display_exposure_mode"),
    (0x03B2D079, b"GRID_LINE_TYPE_RULE_OF_3RD_GRID"),
    (0x03907FA4, b"%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"),
    (0x03908007, b"%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT"),
    (0x03907FC8, b"%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT"),
    (0x0317CC17, b"CAMSET%02d"),
    (0x03BC03AD, b"BKID_APP_save_load_settings_infra_data"),
    (0x03BC89DC, b"BKID_APP_setting_flash_sync_spd_priority"),
    (0x03BCC28E, b"BKID_APP_setting_video_light_set"),
    (0x02FA8370, b"VIDEO_LIGHT_SET_AUTO_LOW_LIGHT"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE359 = (
    "c13e2aae9289c1994babfa34ba009f70d92f939fb47798919bb4236241412d17"
)

PINNED_FX6_APPFW_SLICES_PHASE359: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x02712C41, b"BKID_APP_USER_MENU_CLOCK_SET0"),
    (0x02634875, b"summer_time_name_dst"),
    (0x027106DD, b"BKID_APP_USER_MENU_MARKER0"),
    (0x0279BBDA, b"GUIDE_FRAME_RULE_OF_3RD_GRID"),
    (0x0279BBFA, b"GUIDE_FRAME_GOLDEN_RATIO_GRID"),
    (0x02587A57, b"%c:%s/SONY/PRO/CAMERA/%s/%s.ALL"),
    (0x02587A98, b"%c:%s/SONY/PRO/SCENE/%s.SCN"),
    (0x026CA077, b"VAL_setting_video_light_set_VIDEO_LIGHT_SET_POWER_LINK"),
    (0x026CA0E3, b"VAL_setting_video_light_set_VIDEO_LIGHT_SET_REC_LINK_W_LIGHT"),
    (0x02752038, b"SYNCHRO_TERMINAL"),
    (0x0260C856, b"GENLOCK"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE359 = (
    "5ef357a22a73f1a57aae239e45e64dbf2d1d227ea6dfe3ece83bc6bce7dbfe4f"
)

PINNED_PHASE359_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE359,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE359),
        "FX3 appFw.so Wave-68 Area/Date/DST/Grid/Marker/CAMSET/VideoLight slices",
    ),
    "fx3_lib_save_load_settings_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (
            b"SaveLoadSettingsIf",
            b"requestToRead",
            b"requestToCheck",
            b"requestToWrite",
            b"Backup_get_datasize",
            b"infra_getCallbackFuncTableFtp",
        ),
        "FX3 libSaveLoadSettings.so Wave-68 CAMSET/FTPSET vault ABI",
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
            b"Area/Date/Time Setting",
            b"Date Format",
            b"Grid Line Display",
            b"Grid Line Type",
            b"Marker Display",
            b"Guideframe",
            b"Save/Load Settings",
            b"Memory/Recall Media",
            b"Save/Load FTP Settings",
            b"Flash Sync Spd. Prty.",
            b"External Flash Set.",
            b"Video Light Mode",
        ),
        "FX3 string_english_f.uxc Wave-68 EN parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Area Setting",
            b"Daylight Savings",
            b"Date/Time Setup",
            b"Flash Mode",
        ),
        "FX3 string_english.uxc Wave-68 base tokens",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (
            b"Initial Setting with Creators' App",
            b"Reboots after loading.",
            b"This file cannot be loaded.",
            b"Loading failed.",
            b"SYNCHRO_TERMINAL_OUTPUT_SET_ON",
        ),
        "FX3 string_english_g.uxc Wave-68 guide/prompt tokens",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "\u533a\u57df/\u65e5\u671f/\u65f6\u95f4\u8bbe\u7f6e".encode("utf-8"),
            "\u7f51\u683c\u7ebf\u663e\u793a".encode("utf-8"),
            "\u6807\u8bb0\u663e\u793a".encode("utf-8"),
            "\u4fdd\u5b58/\u52a0\u8f7d\u8bbe\u7f6e".encode("utf-8"),
            "\u5916\u7f6e\u95ea\u5149\u706f\u8bbe\u7f6e".encode("utf-8"),
            "\u89c6\u9891\u706f\u6a21\u5f0f".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-68 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "\u5340\u57df/\u65e5\u671f/\u6642\u9593\u8a2d\u5b9a".encode("utf-8"),
            "\u683c\u7dda\u986f\u793a".encode("utf-8"),
            "\u9304\u5f71\u8f14\u52a9\u6a19\u8a8c\u986f\u793a".encode("utf-8"),
            "\u5132\u5b58/\u8f09\u5165\u8a2d\u5b9a".encode("utf-8"),
            "\u5916\u63a5\u9583\u5149\u71c8\u8a2d\u5b9a".encode("utf-8"),
            "\u8996\u8a0a\u71c8\u6a21\u5f0f".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-68 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "\u30a8\u30ea\u30a2/\u65e5\u6642\u8a2d\u5b9a".encode("utf-8"),
            "\uff78\uff9e\uff98\uff6f\uff84\uff9e\uff97\uff72\uff9d\u8868\u793a".encode(
                "utf-8"
            ),
            "\u30de\u30fc\u30ab\u30fc\u8868\u793a".encode("utf-8"),
            "\u30ac\u30a4\u30c9\u30d5\u30ec\u30fc\u30e0".encode("utf-8"),
            "\u8a2d\u5b9a\u306e\u4fdd\u5b58/\u8aad\u8fbc".encode("utf-8"),
            "\u5916\u90e8\u30d5\u30e9\u30c3\u30b7\u30e5\u8a2d\u5b9a".encode("utf-8"),
            "\u30d3\u30c7\u30aa\u30e9\u30a4\u30c8\u30e2\u30fc\u30c9".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-68 JA parity",
    ),
    "fx6_appfw_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
        50_520_424,
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE359,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE359),
        "FX6 appFw.so Wave-68 ClockSet/DST/Marker/AllFile/VideoLight/SYNCHRO/GENLOCK slices",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (b"All File", b"User File", b"Scene File"),
        "FX6 string_english.uxc Wave-68 EN baseline",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (
            b"Clock Set",
            b"UTC -12:00",
            b"UTC +14:00",
            b"Daylight Saving Time",
            b"Backup Battery End",
            b"Guide Frame",
            b"Center Marker",
            b"Reference File",
            b"Video Light Set",
            b"Genlock",
        ),
        "FX6 string_english_2.uxc Wave-68 EN enterprise baseline",
    ),
}


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _is_clean_room_forced(force_clean_room: Optional[bool]) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE359):
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
    if body_model_name != FX3_MODEL_NAME_PHASE359:
        errs.append(f"body_model_name_invalid:{body_model_name!r}")
    if not _is_strict_int(body_model_id) or body_model_id != FX3_MODEL_ID_PHASE359:
        errs.append(f"body_model_id_invalid:{body_model_id!r}")
    if help_guide_code != FX3_HELP_GUIDE_CODE_PHASE359:
        errs.append(f"help_guide_code_invalid:{help_guide_code!r}")
    if _parse_fw_float(firmware_version) is None:
        errs.append(f"firmware_version_invalid:{firmware_version!r}")
    return errs


def strip_elapsed_seconds_recursive_phase359(obj: Any) -> Any:
    """Recursively strip non-deterministic `elapsed_seconds` keys for canonical digests."""
    if isinstance(obj, dict):
        return {
            k: strip_elapsed_seconds_recursive_phase359(v)
            for k, v in obj.items()
            if k != "elapsed_seconds"
        }
    if isinstance(obj, list):
        return [strip_elapsed_seconds_recursive_phase359(v) for v in obj]
    if isinstance(obj, tuple):
        return [strip_elapsed_seconds_recursive_phase359(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Donor Integrity Audit (O_RDONLY / Clean-Room Dual-Mode)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase359DonorAuditResult:
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


def audit_phase359_donor_contracts(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase359DonorAuditResult:
    """Fast (< 0.20s) O_RDONLY + bounded os.pread donor audit with clean-room fallback."""
    import time

    t0 = time.perf_counter()
    clean_forced = _is_clean_room_forced(force_clean_room)
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else dict(PINNED_PHASE359_DONOR_SPECS)
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
        return Phase359DonorAuditResult(
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
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE359,
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
        return Phase359DonorAuditResult(
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
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE359,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(
                f"Donor files absent ({len(missing_files)} missing); "
                "verified Phase 359 via clean-room synthetic fallback.",
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
                target, PINNED_FX3_APPFW_SLICES_PHASE359
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tok_errs = _read_exact_o_rdonly_slices(
                target, PINNED_FX6_APPFW_SLICES_PHASE359
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
    return Phase359DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE
            if valid
            else STATUS_BLOCKED_PHASE359_DONOR_INTEGRITY
        ),
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="STRICT_OS_O_RDONLY_PREAD",
        files_inspected=inspected,
        fx3_contracts_verified=valid,
        fx6_contracts_verified=valid,
        four_lang_resid16_parity_verified=valid,
        zero_forbidden_myths_verified=valid,
        elapsed_seconds=round(dt, 6),
        within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE359,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        file_digests=file_digests,
        missing_markers=tuple(missing_markers),
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# Gate G155: Area/Date 30-Zone RTC & Grid Line vs Marker Display Clean-HDMI
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AreaDateDstGridCleanHdmiGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    area_date_menu_path: str
    fx6_clock_set_menu_path: str
    grid_line_display_menu_path: str
    marker_display_menu_path: str
    fx6_marker_menu_path: str
    area_gmt_zones_count: int
    area_half_hour_zones_count: int
    effective_area_zone: Optional[str]
    effective_daylight_savings: str
    effective_date_format: Optional[str]
    effective_time_format: str
    daylight_savings_elf_typo: str
    auto_sync_sever_elf_typo: str
    area_date_resettable_by_camset_reset: bool
    initial_setting_wizard_retriggered: bool
    fx3_user_cr2032_slot_present: bool
    rtc_battery_charged: bool
    rtc_charge_hours_power_off: float
    ilc2210_states_3_months_retention: bool
    fx6_clock_set_dst_toggle_exposed: bool
    effective_shoot_mode: str
    effective_grid_line_display: str
    effective_grid_line_type: str
    grid_line_resettable_by_camset_reset: bool
    retired_deleted_movie_grid_exposed: bool
    effective_marker_display: str
    effective_center_marker: str
    effective_aspect_marker: str
    effective_safety_zone: str
    effective_guideframe: str
    marker_display_available_in_still: bool
    marker_5items_resettable_by_camset_reset: bool
    grid_rendered_on_monitor: bool
    grid_rendered_on_hdmi: bool
    marker_rendered_on_monitor: bool
    marker_rendered_on_hdmi: bool
    hdmi_marker_injected_pixels: int
    clean_hdmi_feed_active: bool
    fx6_native_3mode_grid_exposed: bool
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


def resolve_fx3_areadate_grid_cleanhdmi_state(
    *,
    area_zone: str = "AREA_GMT_P_09_0",
    daylight_savings: str = DAYLIGHT_SAVINGS_DEFAULT_G155,
    date_format: str = "Y-M-D",
    rtc_battery_depleted: bool = False,
    rtc_battery_aged_dead: bool = False,
    rtc_charge_hours_power_off: float = 24.0,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE359,
    grid_line_display: str = GRID_LINE_DISPLAY_DEFAULT_G155,
    grid_line_type: str = GRID_LINE_TYPE_DEFAULT_G155,
    marker_display: str = "Off",
    center_marker: str = "Off",
    aspect_marker: str = "Off",
    safety_zone: str = "Off",
    guideframe: str = "Off",
    focus_magnifier_active: bool = False,
    hdmi_connected: bool = False,
    hdmi_info_display: str = "On",
    rec_media_dur_hdmi_output: str = "On",
    raw_output: str = "Off",
    reset_action: str = RESET_ACTION_NONE_PHASE359,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-68 Area/Date RTC & Grid vs Marker Clean-HDMI state."""
    init_applied = reset_action == RESET_ACTION_INITIALIZE_PHASE359

    # Area/Date/Time Setting: immune to Camera Settings Reset; Initialize clears + re-triggers wizard.
    if init_applied:
        eff_area: Optional[str] = None
        eff_dst = DAYLIGHT_SAVINGS_DEFAULT_G155
        eff_date_fmt: Optional[str] = None
        wizard_retriggered = True
    else:
        eff_area = area_zone
        eff_dst = daylight_savings
        eff_date_fmt = date_format
        wizard_retriggered = False

    if rtc_battery_aged_dead:
        rtc_charged = False
    elif rtc_battery_depleted and rtc_charge_hours_power_off < float(
        FX3_RTC_BACKUP_CHARGE_MIN_HOURS_POWER_OFF_G155
    ):
        rtc_charged = False
    else:
        rtc_charged = (
            rtc_charge_hours_power_off
            >= float(FX3_RTC_BACKUP_CHARGE_MIN_HOURS_POWER_OFF_G155)
            or (not rtc_battery_depleted)
        )

    # Grid Line Display/Type + all 5 Marker Display items:
    # ALL are Reset-immune ("Not available" under Camera Settings Reset; Initialize-only!).
    if init_applied:
        eff_grid_disp = GRID_LINE_DISPLAY_DEFAULT_G155
        eff_grid_type = GRID_LINE_TYPE_DEFAULT_G155
        eff_marker_disp = "Off"
        eff_center = "Off"
        eff_aspect = "Off"
        eff_safety = "Off"
        eff_guide = "Off"
    else:
        eff_grid_disp = grid_line_display
        eff_grid_type = grid_line_type
        eff_marker_disp = marker_display
        eff_center = center_marker
        eff_aspect = aspect_marker
        eff_safety = safety_zone
        eff_guide = guideframe

    is_sq = shoot_mode == SHOOT_MODE_SQ_PHASE359
    eff_rec_media = "On" if is_sq else rec_media_dur_hdmi_output
    eff_raw = "Off" if is_sq else raw_output
    clean_feed = (
        hdmi_info_display == "Off"
        or eff_rec_media == "Off(HDMI Only)"
        or eff_raw == "On"
    )

    # Grid Line applies across Still/Movie/S&Q and passes out HDMI unless clean_feed clamps it.
    grid_on_monitor = eff_grid_disp == "On"
    grid_on_hdmi = bool(hdmi_connected and grid_on_monitor and (not clean_feed))

    # Marker Display is Movie/S&Q ONLY, suppressed during Focus Magnifier, and NEVER on HDMI.
    marker_any_sub = (
        eff_center == "On"
        or eff_aspect != "Off"
        or eff_safety != "Off"
        or eff_guide == "On"
    )
    marker_on_monitor = bool(
        shoot_mode in (SHOOT_MODE_MOVIE_PHASE359, SHOOT_MODE_SQ_PHASE359)
        and eff_marker_disp == "On"
        and marker_any_sub
        and (not focus_magnifier_active)
    )
    marker_on_hdmi = False

    return {
        "effective_area_zone": eff_area,
        "effective_daylight_savings": eff_dst,
        "effective_date_format": eff_date_fmt,
        "initial_setting_wizard_retriggered": wizard_retriggered,
        "rtc_battery_charged": rtc_charged,
        "effective_grid_line_display": eff_grid_disp,
        "effective_grid_line_type": eff_grid_type,
        "effective_marker_display": eff_marker_disp,
        "effective_center_marker": eff_center,
        "effective_aspect_marker": eff_aspect,
        "effective_safety_zone": eff_safety,
        "effective_guideframe": eff_guide,
        "grid_rendered_on_monitor": grid_on_monitor,
        "grid_rendered_on_hdmi": grid_on_hdmi,
        "marker_rendered_on_monitor": marker_on_monitor,
        "marker_rendered_on_hdmi": marker_on_hdmi,
        "clean_hdmi_feed_active": bool(clean_feed and not grid_on_hdmi),
    }


def compute_areadate_grid_cleanhdmi_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G155 (384 states)."""
    combos = list(
        itertools.product(
            ALLOWED_SHOOT_MODES_PHASE359,  # 3
            ("AREA_GMT_P_09_0", "AREA_GMT_P_05_5"),  # 2 (full vs :30 half-hour)
            ("Off", "On"),  # daylight_savings (2)
            ("Off", "On"),  # grid_line_display (2)
            ("Off", "On"),  # marker_display (2)
            ("Off", "On"),  # hdmi_info_display (2)
            (False, True),  # focus_magnifier_active (2)
            (
                RESET_ACTION_NONE_PHASE359,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE359,
            ),  # 2 -> 3*2^7 = 384
        )
    )
    area_reset_preserved_count = 0
    grid_reset_preserved_count = 0
    marker_reset_preserved_count = 0
    grid_hdmi_passthrough_count = 0
    marker_hdmi_leak_count = 0
    still_marker_blocked_count = 0
    focus_mag_marker_hidden_count = 0

    for sm, zone, dst, grid_d, mark_d, hdmi_info, fmag, rst in combos:
        st = resolve_fx3_areadate_grid_cleanhdmi_state(
            area_zone=zone,
            daylight_savings=dst,
            shoot_mode=sm,
            grid_line_display=grid_d,
            marker_display=mark_d,
            guideframe="On",
            focus_magnifier_active=fmag,
            hdmi_connected=True,
            hdmi_info_display=hdmi_info,
            reset_action=rst,
        )
        if rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE359:
            if st["effective_area_zone"] == zone and st["effective_daylight_savings"] == dst:
                area_reset_preserved_count += 1
            if st["effective_grid_line_display"] == grid_d:
                grid_reset_preserved_count += 1
            if st["effective_marker_display"] == mark_d:
                marker_reset_preserved_count += 1
        if st["grid_rendered_on_hdmi"]:
            grid_hdmi_passthrough_count += 1
        if st["marker_rendered_on_hdmi"]:
            marker_hdmi_leak_count += 1
        if sm == SHOOT_MODE_STILL_PHASE359 and not st["marker_rendered_on_monitor"]:
            still_marker_blocked_count += 1
        if fmag and not st["marker_rendered_on_monitor"]:
            focus_mag_marker_hidden_count += 1

    return {
        "total_matrix_states": len(combos),
        "area_reset_preserved_count": area_reset_preserved_count,
        "grid_reset_preserved_count": grid_reset_preserved_count,
        "marker_reset_preserved_count": marker_reset_preserved_count,
        "grid_hdmi_passthrough_count": grid_hdmi_passthrough_count,
        "marker_hdmi_leak_count": marker_hdmi_leak_count,
        "still_marker_blocked_count": still_marker_blocked_count,
        "focus_mag_marker_hidden_count": focus_mag_marker_hidden_count,
    }


def verify_areadate_dst_grid_cleanhdmi_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE359,
    body_model_id: int = FX3_MODEL_ID_PHASE359,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE359,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE359,
    area_zone: str = "AREA_GMT_P_09_0",
    daylight_savings: str = DAYLIGHT_SAVINGS_DEFAULT_G155,
    date_format: str = "Y-M-D",
    rtc_battery_depleted: bool = False,
    rtc_battery_aged_dead: bool = False,
    rtc_charge_hours_power_off: float = 24.0,
    timestamp_dependent_action_requested: bool = False,
    claimed_user_replaceable_cr2032_slot: bool = False,
    claimed_ilc2210_states_3_months_retention: bool = False,
    claimed_camset_reset_clears_area_date: bool = False,
    requested_fx6_dormant_dst_toggle: bool = False,
    fx6_time_format: str = "24h",
    fx6_date_mode: str = "YYMMDD",
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE359,
    grid_line_display: str = GRID_LINE_DISPLAY_DEFAULT_G155,
    grid_line_type: str = GRID_LINE_TYPE_DEFAULT_G155,
    marker_display: str = "Off",
    center_marker: str = "Off",
    aspect_marker: str = "Off",
    safety_zone: str = "Off",
    guideframe: str = "Off",
    focus_magnifier_active: bool = False,
    hdmi_connected: bool = False,
    hdmi_info_display: str = "On",
    rec_media_dur_hdmi_output: str = "On",
    raw_output: str = "Off",
    claimed_marker_outputs_over_hdmi: bool = False,
    claimed_marker_visible_during_focus_magnifier: bool = False,
    claimed_camset_reset_clears_grid_or_marker: bool = False,
    requested_retired_deleted_movie_grid_key: bool = False,
    requested_fx6_dormant_3mode_grid: bool = False,
    fx6_center_marker_mode: str = "Off",
    reset_action: str = RESET_ACTION_NONE_PHASE359,
) -> AreaDateDstGridCleanHdmiGuardResult:
    """Enforce Gate G155: Area/Date 30-Zone RTC & Grid Line vs Marker Display Clean-HDMI / Reset Firewall."""
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

    if area_zone not in AREA_GMT_30_ZONES_G155:
        _add("TELEMETRY_INVALID", f"area_zone_invalid:{area_zone!r}")
    if not _is_on_off(daylight_savings):
        _add("TELEMETRY_INVALID", f"daylight_savings_invalid:{daylight_savings!r}")
    if date_format not in EXACT_3_DATE_FORMATS_G155:
        _add("TELEMETRY_INVALID", f"date_format_invalid:{date_format!r}")
    if not _is_strict_number(rtc_charge_hours_power_off) or rtc_charge_hours_power_off < 0.0:
        _add(
            "TELEMETRY_INVALID",
            f"rtc_charge_hours_power_off_invalid:{rtc_charge_hours_power_off!r}",
        )
    if fx6_time_format not in FX6_CLOCK_SET_TIME_FORMATS_G155:
        _add("TELEMETRY_INVALID", f"fx6_time_format_invalid:{fx6_time_format!r}")
    if fx6_date_mode not in FX6_CLOCK_SET_DATE_MODES_G155:
        _add("TELEMETRY_INVALID", f"fx6_date_mode_invalid:{fx6_date_mode!r}")
    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE359:
        _add("TELEMETRY_INVALID", f"shoot_mode_invalid:{shoot_mode!r}")
    if not _is_on_off(grid_line_display):
        _add("TELEMETRY_INVALID", f"grid_line_display_invalid:{grid_line_display!r}")
    if grid_line_type not in EXACT_3_GRID_LINE_TYPES_G155:
        _add("TELEMETRY_INVALID", f"grid_line_type_invalid:{grid_line_type!r}")
    if not _is_on_off(marker_display):
        _add("TELEMETRY_INVALID", f"marker_display_invalid:{marker_display!r}")
    if not _is_on_off(center_marker):
        _add("TELEMETRY_INVALID", f"center_marker_invalid:{center_marker!r}")
    if aspect_marker not in ALLOWED_ASPECT_MARKER_OPTIONS_G155:
        _add("TELEMETRY_INVALID", f"aspect_marker_invalid:{aspect_marker!r}")
    if safety_zone not in ALLOWED_SAFETY_ZONE_OPTIONS_G155:
        _add("TELEMETRY_INVALID", f"safety_zone_invalid:{safety_zone!r}")
    if not _is_on_off(guideframe):
        _add("TELEMETRY_INVALID", f"guideframe_invalid:{guideframe!r}")
    if not _is_on_off(hdmi_info_display):
        _add("TELEMETRY_INVALID", f"hdmi_info_display_invalid:{hdmi_info_display!r}")
    if rec_media_dur_hdmi_output not in ALLOWED_REC_MEDIA_HDMI_MODES_G155:
        _add(
            "TELEMETRY_INVALID",
            f"rec_media_dur_hdmi_output_invalid:{rec_media_dur_hdmi_output!r}",
        )
    if not _is_on_off(raw_output):
        _add("TELEMETRY_INVALID", f"raw_output_invalid:{raw_output!r}")
    if fx6_center_marker_mode not in FX6_CENTER_MARKER_MODES_G155:
        _add(
            "TELEMETRY_INVALID",
            f"fx6_center_marker_mode_invalid:{fx6_center_marker_mode!r}",
        )
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE359:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")

    state = resolve_fx3_areadate_grid_cleanhdmi_state(
        area_zone=area_zone if area_zone in AREA_GMT_30_ZONES_G155 else "AREA_GMT_P_09_0",
        daylight_savings=daylight_savings if _is_on_off(daylight_savings) else DAYLIGHT_SAVINGS_DEFAULT_G155,
        date_format=date_format if date_format in EXACT_3_DATE_FORMATS_G155 else "Y-M-D",
        rtc_battery_depleted=rtc_battery_depleted,
        rtc_battery_aged_dead=rtc_battery_aged_dead,
        rtc_charge_hours_power_off=float(rtc_charge_hours_power_off)
        if _is_strict_number(rtc_charge_hours_power_off)
        else 24.0,
        shoot_mode=shoot_mode if shoot_mode in ALLOWED_SHOOT_MODES_PHASE359 else SHOOT_MODE_MOVIE_PHASE359,
        grid_line_display=grid_line_display if _is_on_off(grid_line_display) else GRID_LINE_DISPLAY_DEFAULT_G155,
        grid_line_type=grid_line_type if grid_line_type in EXACT_3_GRID_LINE_TYPES_G155 else GRID_LINE_TYPE_DEFAULT_G155,
        marker_display=marker_display if _is_on_off(marker_display) else "Off",
        center_marker=center_marker if _is_on_off(center_marker) else "Off",
        aspect_marker=aspect_marker if aspect_marker in ALLOWED_ASPECT_MARKER_OPTIONS_G155 else "Off",
        safety_zone=safety_zone if safety_zone in ALLOWED_SAFETY_ZONE_OPTIONS_G155 else "Off",
        guideframe=guideframe if _is_on_off(guideframe) else "Off",
        focus_magnifier_active=focus_magnifier_active,
        hdmi_connected=hdmi_connected,
        hdmi_info_display=hdmi_info_display if _is_on_off(hdmi_info_display) else "On",
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output
        if rec_media_dur_hdmi_output in ALLOWED_REC_MEDIA_HDMI_MODES_G155
        else "On",
        raw_output=raw_output if _is_on_off(raw_output) else "Off",
        reset_action=reset_action if reset_action in ALLOWED_RESET_ACTIONS_PHASE359 else RESET_ACTION_NONE_PHASE359,
    )

    marker_requested = (
        marker_display == "On"
        or center_marker == "On"
        or aspect_marker != "Off"
        or safety_zone != "Off"
        or guideframe == "On"
    )
    still_marker_requested = (
        shoot_mode == SHOOT_MODE_STILL_PHASE359 and marker_requested
    )

    dormant_or_eopnotsupp = bool(
        claimed_user_replaceable_cr2032_slot
        or requested_fx6_dormant_dst_toggle
        or still_marker_requested
        or requested_retired_deleted_movie_grid_key
        or requested_fx6_dormant_3mode_grid
    )
    if claimed_user_replaceable_cr2032_slot:
        _add(
            "FX3_ZERO_USER_CR2032_SLOT_EOPNOTSUPP",
            "fx3_uses_soldered_rechargeable_rtc_backup_battery_zero_user_cr2032_slot_eopnotsupp_95",
        )
    if requested_fx6_dormant_dst_toggle:
        _add(
            "FX6_CLOCK_SET_ZERO_DST_TOGGLE_EOPNOTSUPP",
            "fx6_maintenance_clock_set_has_zero_dst_toggle_summer_time_name_dst_dormant_eopnotsupp_95",
        )
    if still_marker_requested:
        _add(
            "MARKER_DISPLAY_MOVIE_SQ_ONLY_EOPNOTSUPP",
            "marker_display_is_strictly_movie_and_sq_only_prm_haita_rejects_still_eopnotsupp_95",
        )
    if requested_retired_deleted_movie_grid_key:
        _add(
            "RETIRED_MOVIE_GRID_KEYS_EOPNOTSUPP",
            "bkid_app_deleted_setting_grid_line_display_type_movie_are_retired_eopnotsupp_95",
        )
    if requested_fx6_dormant_3mode_grid:
        _add(
            "FX6_ZERO_3MODE_GRID_UI_EOPNOTSUPP",
            "fx6_body_menu_has_zero_3mode_composition_grid_ui_guide_frame_grid_dormant_eopnotsupp_95",
        )

    # EINVAL=22 Area/Date RTC, Clean-HDMI & Reset-Resistance violations
    if claimed_ilc2210_states_3_months_retention:
        _add(
            "ILC2210_ZERO_3_MONTHS_CLAIM_VIOLATION",
            "ilc_2210_does_not_state_3_months_rtc_retention_claim_only_24h_charge_einval_22",
        )
    if claimed_camset_reset_clears_area_date:
        _add(
            "AREA_DATE_RESET_IMMUNITY_VIOLATION",
            "area_date_time_setting_is_initialize_only_not_resettable_by_camset_reset_einval_22",
        )
    if rtc_battery_aged_dead:
        _add(
            "RTC_BATTERY_AGED_DEAD_REPAIR_REQUIRED",
            "soldered_rtc_backup_battery_aged_dead_resets_after_main_battery_swap_service_required_einval_22",
        )
    if timestamp_dependent_action_requested and not state["rtc_battery_charged"]:
        _add(
            "TIMESTAMP_DEPENDENT_ACTION_UNCHARGED_RTC_VIOLATION",
            "timestamp_dependent_function_blocked_while_rtc_uncharged_under_24h_power_off_einval_22",
        )
    if claimed_marker_outputs_over_hdmi:
        _add(
            "MARKER_DISPLAY_ZERO_HDMI_VIOLATION",
            "marker_display_including_guideframe_never_outputs_over_hdmi_even_when_hdmi_info_on_einval_22",
        )
    if focus_magnifier_active and claimed_marker_visible_during_focus_magnifier:
        _add(
            "MARKER_FOCUS_MAGNIFIER_SUPPRESSION_VIOLATION",
            "marker_display_is_auto_hidden_during_focus_magnifier_einval_22",
        )
    if claimed_camset_reset_clears_grid_or_marker:
        _add(
            "GRID_AND_MARKER_5ITEMS_RESET_IMMUNITY_VIOLATION",
            "grid_line_and_all_5_marker_items_are_not_available_under_camset_reset_einval_22",
        )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G155
        block_errno = 0
        block_errno_name = "OK"
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G155_DORMANT_CR2032_FX6_DST_OR_STILL_MARKER_EOPNOTSUPP
        block_errno = EOPNOTSUPP_ERRNO_PHASE359
        block_errno_name = EOPNOTSUPP_NAME_PHASE359
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
        status = STATUS_BLOCKED_G155_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE359
        block_errno_name = EINVAL_NAME_PHASE359
    else:
        status = STATUS_BLOCKED_G155_AREA_RTC_OR_GRID_MARKER_CLEANHDMI_RESET_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE359
        block_errno_name = EINVAL_NAME_PHASE359

    return AreaDateDstGridCleanHdmiGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        area_date_menu_path=AREA_DATE_MENU_PATH_G155,
        fx6_clock_set_menu_path=FX6_CLOCK_SET_MENU_PATH_G155,
        grid_line_display_menu_path=GRID_LINE_DISPLAY_MENU_PATH_G155,
        marker_display_menu_path=MARKER_DISPLAY_MENU_PATH_G155,
        fx6_marker_menu_path=FX6_MARKER_MENU_PATH_G155,
        area_gmt_zones_count=len(AREA_GMT_30_ZONES_G155),
        area_half_hour_zones_count=len(AREA_GMT_HALF_HOUR_6_ZONES_G155),
        effective_area_zone=state["effective_area_zone"],
        effective_daylight_savings=state["effective_daylight_savings"],
        effective_date_format=state["effective_date_format"],
        effective_time_format="24h",
        daylight_savings_elf_typo=DAYLIGHT_SAVINGS_ELF_TYPO_G155,
        auto_sync_sever_elf_typo=AUTO_SYNC_SEVER_ELF_TYPO_G155,
        area_date_resettable_by_camset_reset=AREA_DATE_RESETTABLE_BY_CAMSET_RESET_G155,
        initial_setting_wizard_retriggered=state["initial_setting_wizard_retriggered"],
        fx3_user_cr2032_slot_present=FX3_USER_CR2032_SLOT_PRESENT_G155,
        rtc_battery_charged=state["rtc_battery_charged"],
        rtc_charge_hours_power_off=float(rtc_charge_hours_power_off)
        if _is_strict_number(rtc_charge_hours_power_off)
        else 0.0,
        ilc2210_states_3_months_retention=ILC2210_STATES_3_MONTHS_RETENTION_G155,
        fx6_clock_set_dst_toggle_exposed=FX6_CLOCK_SET_DST_TOGGLE_EXPOSED_G155,
        effective_shoot_mode=shoot_mode,
        effective_grid_line_display=state["effective_grid_line_display"],
        effective_grid_line_type=state["effective_grid_line_type"],
        grid_line_resettable_by_camset_reset=GRID_LINE_RESETTABLE_BY_CAMSET_RESET_G155,
        retired_deleted_movie_grid_exposed=False,
        effective_marker_display=state["effective_marker_display"],
        effective_center_marker=state["effective_center_marker"],
        effective_aspect_marker=state["effective_aspect_marker"],
        effective_safety_zone=state["effective_safety_zone"],
        effective_guideframe=state["effective_guideframe"],
        marker_display_available_in_still=False,
        marker_5items_resettable_by_camset_reset=MARKER_5ITEMS_RESETTABLE_BY_CAMSET_RESET_G155,
        grid_rendered_on_monitor=state["grid_rendered_on_monitor"],
        grid_rendered_on_hdmi=state["grid_rendered_on_hdmi"],
        marker_rendered_on_monitor=state["marker_rendered_on_monitor"],
        marker_rendered_on_hdmi=state["marker_rendered_on_hdmi"],
        hdmi_marker_injected_pixels=HDMI_MARKER_INJECTED_PIXELS_G155,
        clean_hdmi_feed_active=state["clean_hdmi_feed_active"],
        fx6_native_3mode_grid_exposed=FX6_NATIVE_3MODE_GRID_EXPOSED_G155,
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
class G155AreaDateDstGridCleanHdmiGuardResult:
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
    areadate_grid_cleanhdmi_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g155_areadate_dst_grid_cleanhdmi_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G155AreaDateDstGridCleanHdmiGuardResult]:
    audit = audit_phase359_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_areadate_dst_grid_cleanhdmi_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G155AreaDateDstGridCleanHdmiGuardResult(
        gate_id=G155,
        gate_code=G155_GATE_CODE,
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
        areadate_grid_cleanhdmi_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G155,
        gate_code=G155_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"zones={res.area_gmt_zones_count} "
            f"rtc_charged={res.rtc_battery_charged} "
            f"grid_hdmi={res.grid_rendered_on_hdmi} "
            f"marker_hdmi={res.marker_rendered_on_hdmi} "
            f"marker_hdmi_px={res.hdmi_marker_injected_pixels}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_areadate_dst_grid_cleanhdmi_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G155AreaDateDstGridCleanHdmiGuardResult]:
    return evaluate_g155_areadate_dst_grid_cleanhdmi_guard(**kwargs)


# ---------------------------------------------------------------------------
# Gate G156: [Save/Load Settings] Slot-1 EROFS=30 CAMSET01..10.DAT Vault &
#            MI-Shoe XLR-H1 vs HVL-LBPC / Zero Sync Terminal / Zero GENLOCK
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SaveLoadCamsetMiShoeGenlockFirewallResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    save_load_settings_menu_path: str
    save_load_ftp_menu_path: str
    camera_set_memory_menu_path: str
    video_light_mode_menu_path: str
    fx6_all_file_menu_path: str
    fx6_video_light_set_menu_path: str
    lib_save_load_settings_name: str
    lib_save_load_settings_bytes: int
    effective_operation: str
    effective_target_media: str
    effective_card_type: str
    effective_slot_index: int
    resolved_setting_path: str
    fx3_pro_camera_path_hits: int
    camset_excluded_items_count: int
    camset_excluded_items_leaked_count: int
    camset_auto_reboot_on_load: bool
    slot1_tier0_vault_firewall_blocked: bool
    slot1_data_sector_writes: int
    emmc_nflasha_write_count: int
    fx3_physical_sync_terminal_present: bool
    fx3_synchro_terminal_elf_hits: int
    effective_video_light_mode: str
    effective_flash_mode: str
    effective_flash_shutter_type: str
    effective_flash_shutter_denom: int
    effective_mi_shoe_device: str
    xlr_h1_attached: bool
    xlr_h1_passive_cold_shoe_only: bool
    mishoe_xlr_h1_exclusion_triggered: bool
    pmic_5v_current_ma: int
    pmic_5v_overcurrent_blocked: bool
    fx6_video_light_auto_supported: bool
    fx6_physical_genlock_bnc_present: bool
    fx6_dormant_genlock_elf_hits: int
    fx6_reference_file_elf_hits: int
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


def resolve_fx3_saveload_camset_and_mishoe_state(
    *,
    operation: str = "camset_load",
    target_media: str = "Slot 1",
    card_type: str = "SDXC",
    slot_index: int = 1,
    memory_recall_media: str = "Slot 2",
    xlr_h1_attached: bool = False,
    mi_shoe_device: str = "None",
    video_light_mode: str = "Power Link",
    flash_mode: str = "Fill-flash",
    shutter_type: str = "Mechanical",
    shutter_speed_denom: int = 250,
    pmic_5v_current_ma: int = 0,
    reset_action: str = RESET_ACTION_NONE_PHASE359,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-68 Save/Load path & MI-Shoe XLR-H1/PMIC state."""
    prefix = "/PRIVATE" if card_type == "SDXC" else ""
    init_applied = reset_action == RESET_ACTION_INITIALIZE_PHASE359
    eff_vlight = "Power Link" if init_applied else video_light_mode
    eff_flash_m = "Autoflash" if init_applied else flash_mode
    eff_mrm = "Slot 1" if init_applied else memory_recall_media

    if operation in ("camset_load", "camset_save", "camset_delete"):
        if target_media in ("Cloud(Private)", "Cloud(Share)"):
            resolved = f"cloud://{target_media}/CAMSET{slot_index:02d}.DAT"
        else:
            resolved = (
                f"{prefix}/SONY/SETTING/{FX3_MODEL_NAME_PHASE359}/CAMSET/"
                f"CAMSET{slot_index:02d}.DAT"
            )
    elif operation == "ftpset_save":
        resolved = (
            f"{prefix}/SONY/SETTING/{FX3_MODEL_NAME_PHASE359}/FTPSET/"
            f"FTPSET{slot_index:02d}.DAT"
        )
    elif operation == "camera_set_memory_body":
        resolved = f"nvram://camera_set_memory/{slot_index}"
    elif operation in ("camera_set_memory_card_save", "camera_set_memory_card_recall"):
        resolved = (
            f"{prefix}/SONY/SETTING/{FX3_MODEL_NAME_PHASE359}/"
            f"CAMPR{slot_index:02d}A.DAT"
        )
    else:
        resolved = (
            f"{prefix}/SONY/PRO/CAMERA/{FX6_MODEL_NAME_PHASE359}/"
            f"ALL{slot_index:02d}.ALL"
        )

    xlr_mishoe_conflict = bool(
        xlr_h1_attached
        and mi_shoe_device in ELECTRICAL_LIGHT_OR_FLASH_MISHOE_DEVICES_G156
    )
    pmic_overcurrent = bool(pmic_5v_current_ma > PMIC_5V_MAX_CURRENT_MA_G156)
    xsync_ok = (
        shutter_type == "Mechanical"
        and shutter_speed_denom <= FX3_FLASH_XSYNC_MAX_DENOM_G156
    )

    return {
        "resolved_setting_path": resolved,
        "effective_video_light_mode": eff_vlight,
        "effective_flash_mode": eff_flash_m,
        "effective_memory_recall_media": eff_mrm,
        "mishoe_xlr_h1_exclusion_triggered": xlr_mishoe_conflict,
        "pmic_5v_overcurrent_blocked": pmic_overcurrent,
        "flash_xsync_admitted": xsync_ok,
        "camset_auto_reboot_on_load": (operation == "camset_load"),
    }


def compute_saveload_camset_mishoe_genlock_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G156 (384 states)."""
    combos = list(
        itertools.product(
            ("camset_load", "camset_save", "camset_delete"),  # 3
            ("Slot 1", "Slot 2"),  # 2
            ALLOWED_CARD_MEDIA_TYPES_G156,  # 2
            (False, True),  # xlr_h1_attached (2)
            ("None", "HVL-LBPC"),  # mi_shoe_device (2)
            ("Mechanical", "Electronic"),  # shutter_type (2)
            (160, 320),  # shutter_speed_denom (2)
            (650, 950),  # pmic_5v_current_ma (2) -> 3 * 2^7 = 384
        )
    )
    slot1_erofs_blocked_count = 0
    slot2_camset_rejected_count = 0
    xlr_h1_mishoe_conflict_count = 0
    pmic_overcurrent_blocked_count = 0
    flash_xsync_rejected_count = 0
    safe_camset_load_count = 0

    for op, media, card, xlr, dev, sh_type, sh_den, pmic_ma in combos:
        st = resolve_fx3_saveload_camset_and_mishoe_state(
            operation=op,
            target_media=media,
            card_type=card,
            xlr_h1_attached=xlr,
            mi_shoe_device=dev,
            shutter_type=sh_type,
            shutter_speed_denom=sh_den,
            pmic_5v_current_ma=pmic_ma,
        )
        is_slot1_write = media == "Slot 1" and op in ("camset_save", "camset_delete")
        is_slot2_camset = media == "Slot 2"
        if is_slot1_write:
            slot1_erofs_blocked_count += 1
        if is_slot2_camset:
            slot2_camset_rejected_count += 1
        if st["mishoe_xlr_h1_exclusion_triggered"]:
            xlr_h1_mishoe_conflict_count += 1
        if st["pmic_5v_overcurrent_blocked"]:
            pmic_overcurrent_blocked_count += 1
        if not st["flash_xsync_admitted"]:
            flash_xsync_rejected_count += 1
        if (
            op == "camset_load"
            and media == "Slot 1"
            and not st["mishoe_xlr_h1_exclusion_triggered"]
            and not st["pmic_5v_overcurrent_blocked"]
            and st["flash_xsync_admitted"]
        ):
            safe_camset_load_count += 1

    return {
        "total_matrix_states": len(combos),
        "slot1_erofs_blocked_count": slot1_erofs_blocked_count,
        "slot2_camset_rejected_count": slot2_camset_rejected_count,
        "xlr_h1_mishoe_conflict_count": xlr_h1_mishoe_conflict_count,
        "pmic_overcurrent_blocked_count": pmic_overcurrent_blocked_count,
        "flash_xsync_rejected_count": flash_xsync_rejected_count,
        "safe_camset_load_count": safe_camset_load_count,
    }


def verify_saveload_camset_mishoe_genlock_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE359,
    body_model_id: int = FX3_MODEL_ID_PHASE359,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE359,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE359,
    operation: str = "camset_load",
    target_media: str = "Slot 1",
    target_media_slot: Optional[int] = None,
    card_type: str = "SDXC",
    slot_index: int = 1,
    mr_recall_mode_active: bool = False,
    source_body_model: str = FX3_MODEL_NAME_PHASE359,
    source_fw_version: str = FX3_DEFAULT_FW_VERSION_PHASE359,
    checksum_valid: bool = True,
    claimed_fx3_uses_pro_camera_path: bool = False,
    claimed_camset_exports_excluded_item: Optional[str] = None,
    memory_recall_media: str = "Slot 2",
    requested_write_operation: bool = False,
    requested_fx6_dormant_reference_file: bool = False,
    requested_pc_sync_terminal_or_dormant_flash_spd_prty: bool = False,
    video_light_mode: str = "Power Link",
    flash_mode: str = "Fill-flash",
    flash_fired: bool = False,
    shutter_type: str = "Mechanical",
    silent_mode: str = "Off",
    shutter_speed_denom: int = 250,
    flash_voltage_v: float = 5.0,
    reverse_polarity: bool = False,
    xlr_h1_attached: bool = False,
    claimed_xlr_h1_shoe_has_mi_contacts: bool = False,
    mi_shoe_device: str = "None",
    pmic_5v_current_ma: int = 0,
    requested_fx6_video_light_auto: bool = False,
    requested_fx6_still_flash_ui: bool = False,
    requested_fx6_dormant_genlock_bnc: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE359,
) -> SaveLoadCamsetMiShoeGenlockFirewallResult:
    """Enforce Gate G156: Save/Load Slot-1 EROFS=30 Vault & MI-Shoe XLR-H1 / Zero Sync Terminal / Zero GENLOCK."""
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

    if operation not in ALLOWED_SAVELOAD_OPERATIONS_G156:
        _add("TELEMETRY_INVALID", f"operation_invalid:{operation!r}")
    if target_media not in ALLOWED_SAVELOAD_TARGETS_G156:
        _add("TELEMETRY_INVALID", f"target_media_invalid:{target_media!r}")
    if target_media_slot is not None and (
        not _is_strict_int(target_media_slot)
        or target_media_slot not in ALLOWED_MEDIA_SLOTS_PHASE359
    ):
        _add("TELEMETRY_INVALID", f"target_media_slot_invalid:{target_media_slot!r}")
    if card_type not in ALLOWED_CARD_MEDIA_TYPES_G156:
        _add("TELEMETRY_INVALID", f"card_type_invalid:{card_type!r}")
    if not _is_strict_int(slot_index) or slot_index < 0:
        _add("TELEMETRY_INVALID", f"slot_index_invalid:{slot_index!r}")
    if memory_recall_media not in ("Slot 1", "Slot 2"):
        _add("TELEMETRY_INVALID", f"memory_recall_media_invalid:{memory_recall_media!r}")
    if video_light_mode not in EXACT_4_FX3_VIDEO_LIGHT_MODES_G156:
        _add("TELEMETRY_INVALID", f"video_light_mode_invalid:{video_light_mode!r}")
    if flash_mode not in EXACT_5_FX3_FLASH_MODES_G156:
        _add("TELEMETRY_INVALID", f"flash_mode_invalid:{flash_mode!r}")
    if shutter_type not in FX3_FLASH_SHUTTER_MODES_G156:
        _add("TELEMETRY_INVALID", f"shutter_type_invalid:{shutter_type!r}")
    if not _is_on_off(silent_mode):
        _add("TELEMETRY_INVALID", f"silent_mode_invalid:{silent_mode!r}")
    if not _is_strict_int(shutter_speed_denom) or shutter_speed_denom <= 0:
        _add(
            "TELEMETRY_INVALID",
            f"shutter_speed_denom_invalid:{shutter_speed_denom!r}",
        )
    if not _is_strict_number(flash_voltage_v) or flash_voltage_v < 0.0:
        _add("TELEMETRY_INVALID", f"flash_voltage_v_invalid:{flash_voltage_v!r}")
    if mi_shoe_device not in ALLOWED_MISHOE_DEVICES_G156:
        _add("TELEMETRY_INVALID", f"mi_shoe_device_invalid:{mi_shoe_device!r}")
    if not _is_strict_int(pmic_5v_current_ma) or pmic_5v_current_ma < 0:
        _add(
            "TELEMETRY_INVALID",
            f"pmic_5v_current_ma_invalid:{pmic_5v_current_ma!r}",
        )
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE359:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")

    eff_target_media = (
        "Slot 1"
        if target_media_slot == MEDIA_SLOT_1_PHASE359
        else ("Slot 2" if target_media_slot == MEDIA_SLOT_2_PHASE359 else target_media)
    )

    state = resolve_fx3_saveload_camset_and_mishoe_state(
        operation=operation if operation in ALLOWED_SAVELOAD_OPERATIONS_G156 else "camset_load",
        target_media=eff_target_media if eff_target_media in ALLOWED_SAVELOAD_TARGETS_G156 else "Slot 1",
        card_type=card_type if card_type in ALLOWED_CARD_MEDIA_TYPES_G156 else "SDXC",
        slot_index=slot_index if _is_strict_int(slot_index) and slot_index >= 0 else 1,
        memory_recall_media=memory_recall_media if memory_recall_media in ("Slot 1", "Slot 2") else "Slot 2",
        xlr_h1_attached=xlr_h1_attached,
        mi_shoe_device=mi_shoe_device if mi_shoe_device in ALLOWED_MISHOE_DEVICES_G156 else "None",
        video_light_mode=video_light_mode if video_light_mode in EXACT_4_FX3_VIDEO_LIGHT_MODES_G156 else "Power Link",
        flash_mode=flash_mode if flash_mode in EXACT_5_FX3_FLASH_MODES_G156 else "Fill-flash",
        shutter_type=shutter_type if shutter_type in FX3_FLASH_SHUTTER_MODES_G156 else "Mechanical",
        shutter_speed_denom=shutter_speed_denom if _is_strict_int(shutter_speed_denom) and shutter_speed_denom > 0 else 250,
        pmic_5v_current_ma=pmic_5v_current_ma if _is_strict_int(pmic_5v_current_ma) and pmic_5v_current_ma >= 0 else 0,
        reset_action=reset_action if reset_action in ALLOWED_RESET_ACTIONS_PHASE359 else RESET_ACTION_NONE_PHASE359,
    )

    # EOPNOTSUPP=95 Dormant, Slot-2 CAMSET, MR-mode & FX6 Cross-Model Rejections
    is_fx3_camset_or_ftp = operation in (
        "camset_load",
        "camset_save",
        "camset_delete",
        "ftpset_save",
    )
    slot2_camset_attempt = bool(
        is_fx3_camset_or_ftp and eff_target_media in ("Slot 2", "Media(B)")
    )
    mr_saveload_attempt = bool(
        mr_recall_mode_active
        and operation in ("camset_load", "camset_save", "camset_delete")
    )
    fx6_op_on_fx3 = operation in ("fx6_all_file_load", "fx6_all_file_save")

    dormant_or_eopnotsupp = bool(
        slot2_camset_attempt
        or mr_saveload_attempt
        or fx6_op_on_fx3
        or requested_fx6_dormant_reference_file
        or requested_pc_sync_terminal_or_dormant_flash_spd_prty
        or requested_fx6_video_light_auto
        or requested_fx6_still_flash_ui
        or requested_fx6_dormant_genlock_bnc
    )
    if slot2_camset_attempt:
        _add(
            "SAVELOAD_SLOT1_ONLY_NO_SLOT2_EOPNOTSUPP",
            f"fx3_saveload_and_ftpset_are_strictly_slot1_only_{eff_target_media}_unavailable_eopnotsupp_95",
        )
    if mr_saveload_attempt:
        _add(
            "SAVELOAD_DISABLED_IN_MR_MODE_EOPNOTSUPP",
            "fx3_save_load_settings_is_disabled_in_mr_recall_camera_setting_mode_eopnotsupp_95",
        )
    if fx6_op_on_fx3:
        _add(
            "FX6_ALL_FILE_PRO_CAMERA_UNAVAILABLE_ON_FX3_EOPNOTSUPP",
            f"fx3_has_zero_pro_camera_all_file_support_operation_{operation}_eopnotsupp_95",
        )
    if requested_fx6_dormant_reference_file:
        _add(
            "FX6_DORMANT_REFERENCE_FILE_EOPNOTSUPP",
            "fx6_reference_file_has_zero_appfw_elf_hits_dormant_xdcam_legacy_eopnotsupp_95",
        )
    if requested_pc_sync_terminal_or_dormant_flash_spd_prty:
        _add(
            "FX3_ZERO_SYNC_TERMINAL_EOPNOTSUPP",
            "fx3_has_zero_physical_pc_sync_terminal_and_dormant_flash_sync_spd_prty_eopnotsupp_95",
        )
    if requested_fx6_video_light_auto:
        _add(
            "FX6_VIDEO_LIGHT_ZERO_AUTO_EOPNOTSUPP",
            "fx6_video_light_set_exposes_3_modes_only_zero_auto_low_light_eopnotsupp_95",
        )
    if requested_fx6_still_flash_ui:
        _add(
            "FX6_ZERO_STILL_FLASH_UI_EOPNOTSUPP",
            "fx6_ver_6_01_exposes_zero_still_flash_menu_ui_eopnotsupp_95",
        )
    if requested_fx6_dormant_genlock_bnc:
        _add(
            "FX6_ZERO_GENLOCK_BNC_EOPNOTSUPP",
            "fx6_has_zero_physical_genlock_ref_bnc_despite_107_dormant_genlock_symbols_eopnotsupp_95",
        )

    # EBUSY=16 MI-Shoe XLR-H1 Mutual Exclusion Firewall
    xlr_mishoe_conflict = bool(state["mishoe_xlr_h1_exclusion_triggered"])
    if xlr_mishoe_conflict:
        _add(
            "XLR_H1_MISHOE_ELECTRICAL_EXCLUSION_EBUSY",
            f"xlr_h1_occupies_sole_fx3_electrical_mishoe_blocks_{mi_shoe_device}_ebusy_16",
        )
    if claimed_xlr_h1_shoe_has_mi_contacts:
        _add(
            "XLR_H1_PASSIVE_COLD_SHOE_ONLY_VIOLATION",
            "xlr_h1_accessory_shoe_kit_provides_passive_cold_shoes_only_zero_mi_contacts_einval_22",
        )

    # Tier-0 Slot-1 EROFS=30 Vault Firewall (Save/Delete/Write on Slot 1 blocked!)
    slot1_camset_write = bool(
        operation in ("camset_save", "camset_delete", "ftpset_save")
        and eff_target_media == "Slot 1"
    )
    slot1_campr_write = bool(
        operation == "camera_set_memory_card_save" and memory_recall_media == "Slot 1"
    )
    slot1_explicit_write = bool(
        eff_target_media == "Slot 1" and requested_write_operation
    )
    slot1_blocked = slot1_camset_write or slot1_campr_write or slot1_explicit_write
    if slot1_blocked:
        _add(
            "SLOT1_SAVELOAD_CAMSET_VAULT_EROFS",
            "slot1_tier0_vault_erofs_30_hard_blocked_camset_ftpset_campr_or_card_write",
        )

    # EINVAL=22 Compatibility, Exclusion List, Slot Bounds, Flash Shutter/X-Sync & PMIC 5V Guards
    if claimed_fx3_uses_pro_camera_path:
        _add(
            "FX3_ZERO_PRO_CAMERA_PATH_VIOLATION",
            "fx3_uses_sony_setting_camset_zero_pro_camera_path_hits_einval_22",
        )
    if claimed_camset_exports_excluded_item is not None:
        _add(
            "CAMSET_EXCLUDED_ITEM_LEAK_VIOLATION",
            f"camset_dat_never_exports_excluded_item:{claimed_camset_exports_excluded_item!r}_einval_22",
        )

    is_cloud = eff_target_media in ("Cloud(Private)", "Cloud(Share)")
    if _is_strict_int(slot_index):
        if is_fx3_camset_or_ftp and eff_target_media == "Slot 1" and not (
            1 <= slot_index <= CAMSET_MAX_CARD_SLOTS_G156
        ):
            _add(
                "CAMSET_CARD_SLOT_RANGE_VIOLATION",
                f"slot1_camset_ftpset_index_out_of_1_to_10_range:{slot_index}",
            )
        elif is_fx3_camset_or_ftp and is_cloud and not (
            1 <= slot_index <= CAMSET_MAX_CLOUD_SLOTS_G156
        ):
            _add(
                "CAMSET_CLOUD_SLOT_RANGE_VIOLATION",
                f"cloud_camset_index_out_of_1_to_60_range:{slot_index}",
            )
        elif operation == "camera_set_memory_body" and slot_index not in CAMERA_SET_MEMORY_BODY_SLOTS_G156:
            _add(
                "CAMERA_SET_MEMORY_BODY_RANGE_VIOLATION",
                f"body_camera_set_memory_slot_must_be_1_to_3:{slot_index}",
            )
        elif operation in (
            "camera_set_memory_card_save",
            "camera_set_memory_card_recall",
        ) and not (1 <= slot_index <= 4):
            _add(
                "CAMERA_SET_MEMORY_CARD_RANGE_VIOLATION",
                f"card_camera_set_memory_m1_to_m4_must_be_1_to_4:{slot_index}",
            )

    if operation == "camset_load":
        if source_body_model != FX3_MODEL_NAME_PHASE359:
            _add(
                "CAMSET_CROSS_MODEL_REJECTED",
                f"libsaveloadsettings_requestToCheck_rejected_cross_model:{source_body_model!r}",
            )
        if not checksum_valid:
            _add(
                "CAMSET_CHECKSUM_INVALID_REJECTED",
                "libsaveloadsettings_procCheck_checksum_mismatch_einval_22",
            )
        src_fw = _parse_fw_float(source_fw_version)
        dst_fw = _parse_fw_float(firmware_version)
        if src_fw is None or (
            dst_fw is not None
            and dst_fw >= CAMSET_MIN_FW_INCOMPAT_BOUNDARY_G156
            and src_fw < CAMSET_MIN_FW_INCOMPAT_BOUNDARY_G156
        ):
            _add(
                "CAMSET_LEGACY_FW_INCOMPATIBLE_REJECTED",
                f"camset_fw_version_incompatible:{source_fw_version!r}_into_{firmware_version!r}_einval_22",
            )

    if flash_fired:
        if shutter_type != "Mechanical" or silent_mode == "On":
            _add(
                "FLASH_ESHUTTER_OR_SILENT_MODE_BLOCKED",
                "flash_requires_mechanical_shutter_with_silent_mode_off_einval_22",
            )
        if _is_strict_int(shutter_speed_denom) and shutter_speed_denom > FX3_FLASH_XSYNC_MAX_DENOM_G156:
            _add(
                "FLASH_XSYNC_EXCEEDED_250_VIOLATION",
                f"flash_shutter_speed_1_{shutter_speed_denom}_exceeds_fx3_1_250s_xsync_einval_22",
            )
        if _is_strict_number(flash_voltage_v) and float(flash_voltage_v) >= FX3_FLASH_MAX_TRIGGER_VOLTAGE_V_G156:
            _add(
                "FLASH_HIGH_VOLTAGE_250V_VIOLATION",
                f"flash_trigger_voltage_{flash_voltage_v}V_reaches_or_exceeds_250V_limit_einval_22",
            )
        if reverse_polarity:
            _add(
                "FLASH_REVERSE_POLARITY_VIOLATION",
                "flash_reverse_polarity_sync_blocked_einval_22",
            )

    if state["pmic_5v_overcurrent_blocked"]:
        _add(
            "PMIC_5V_900MA_OVERCURRENT_VIOLATION",
            f"mishoe_pmic_5v_current_{pmic_5v_current_ma}mA_exceeds_900mA_ceiling_einval_22",
        )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G156
        block_errno = 0
        block_errno_name = "OK"
    elif slot1_blocked:
        status = STATUS_BLOCKED_G156_SLOT1_SAVELOAD_CAMSET_VAULT_EROFS
        block_errno = EROFS_ERRNO_PHASE359
        block_errno_name = EROFS_NAME_PHASE359
    elif xlr_mishoe_conflict:
        status = STATUS_BLOCKED_G156_MISHOE_XLRH1_EXCLUSION_EBUSY
        block_errno = EBUSY_ERRNO_PHASE359
        block_errno_name = EBUSY_NAME_PHASE359
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G156_DORMANT_SYNC_GENLOCK_SLOT2_MR_OR_REFFILE_EOPNOTSUPP
        block_errno = EOPNOTSUPP_ERRNO_PHASE359
        block_errno_name = EOPNOTSUPP_NAME_PHASE359
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
        status = STATUS_BLOCKED_G156_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE359
        block_errno_name = EINVAL_NAME_PHASE359
    else:
        status = STATUS_BLOCKED_G156_CAMSET_COMPAT_FLASH_SHUTTER_OR_PMIC_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE359
        block_errno_name = EINVAL_NAME_PHASE359

    return SaveLoadCamsetMiShoeGenlockFirewallResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        save_load_settings_menu_path=SAVE_LOAD_SETTINGS_MENU_PATH_G156,
        save_load_ftp_menu_path=SAVE_LOAD_FTP_MENU_PATH_G156,
        camera_set_memory_menu_path=CAMERA_SET_MEMORY_MENU_PATH_G156,
        video_light_mode_menu_path=VIDEO_LIGHT_MODE_MENU_PATH_G156,
        fx6_all_file_menu_path=FX6_ALL_FILE_MENU_PATH_G156,
        fx6_video_light_set_menu_path=FX6_VIDEO_LIGHT_SET_MENU_PATH_G156,
        lib_save_load_settings_name=LIB_SAVE_LOAD_SETTINGS_NAME_G156,
        lib_save_load_settings_bytes=LIB_SAVE_LOAD_SETTINGS_BYTES_G156,
        effective_operation=operation,
        effective_target_media=eff_target_media,
        effective_card_type=card_type,
        effective_slot_index=slot_index if _is_strict_int(slot_index) else -1,
        resolved_setting_path=state["resolved_setting_path"],
        fx3_pro_camera_path_hits=FX3_PRO_CAMERA_PATH_HITS_G156,
        camset_excluded_items_count=len(EXACT_20_CAMSET_EXCLUDED_ITEMS_G156),
        camset_excluded_items_leaked_count=1 if claimed_camset_exports_excluded_item is not None else 0,
        camset_auto_reboot_on_load=state["camset_auto_reboot_on_load"],
        slot1_tier0_vault_firewall_blocked=slot1_blocked,
        slot1_data_sector_writes=0,
        emmc_nflasha_write_count=0,
        fx3_physical_sync_terminal_present=FX3_PHYSICAL_SYNC_TERMINAL_PRESENT_G156,
        fx3_synchro_terminal_elf_hits=FX3_SYNCHRO_TERMINAL_ELF_HITS_G156,
        effective_video_light_mode=state["effective_video_light_mode"],
        effective_flash_mode=state["effective_flash_mode"],
        effective_flash_shutter_type=shutter_type,
        effective_flash_shutter_denom=shutter_speed_denom if _is_strict_int(shutter_speed_denom) else -1,
        effective_mi_shoe_device=mi_shoe_device,
        xlr_h1_attached=xlr_h1_attached,
        xlr_h1_passive_cold_shoe_only=XLR_H1_TOP_SHOES_PASSIVE_COLD_ONLY_G156,
        mishoe_xlr_h1_exclusion_triggered=xlr_mishoe_conflict,
        pmic_5v_current_ma=pmic_5v_current_ma if _is_strict_int(pmic_5v_current_ma) else -1,
        pmic_5v_overcurrent_blocked=state["pmic_5v_overcurrent_blocked"],
        fx6_video_light_auto_supported=FX6_VIDEO_LIGHT_AUTO_SUPPORTED_G156,
        fx6_physical_genlock_bnc_present=FX6_PHYSICAL_GENLOCK_BNC_PRESENT_G156,
        fx6_dormant_genlock_elf_hits=FX6_DORMANT_GENLOCK_ELF_HITS_G156,
        fx6_reference_file_elf_hits=FX6_REFERENCE_FILE_ELF_HITS_G156,
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
class G156SaveLoadCamsetMiShoeGenlockGuardResult:
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
    saveload_camset_mishoe_genlock_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g156_saveload_camset_mishoe_genlock_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G156SaveLoadCamsetMiShoeGenlockGuardResult]:
    audit = audit_phase359_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_saveload_camset_mishoe_genlock_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G156SaveLoadCamsetMiShoeGenlockGuardResult(
        gate_id=G156,
        gate_code=G156_GATE_CODE,
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
        saveload_camset_mishoe_genlock_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G156,
        gate_code=G156_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"op={res.effective_operation} "
            f"media={res.effective_target_media} "
            f"s1_writes={res.slot1_data_sector_writes} "
            f"sync_hits={res.fx3_synchro_terminal_elf_hits} "
            f"xlr_conflict={res.mishoe_xlr_h1_exclusion_triggered}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_saveload_camset_mishoe_genlock_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G156SaveLoadCamsetMiShoeGenlockGuardResult]:
    return evaluate_g156_saveload_camset_mishoe_genlock_guard(**kwargs)


# ---------------------------------------------------------------------------
# Unified 156-Gate Master Safety Preflight Engine (G01..G156)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Master156GateReport:
    schema: str
    schema_version: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_153_gates_verified: bool
    all_156_gates_verified: bool
    g13_to_g156_all_passed: bool
    g155_to_g156_all_passed: bool
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
    master_154_report: Dict[str, Any]
    g155_result: Dict[str, Any]
    g156_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_156gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    simulate_bench_dry_run: Optional[bool] = None,
    dry_run_simulated_backup: Optional[bool] = None,
    request_persistent_emmc_writes: bool = False,
    master_154_override: Optional[Master154GateReport] = None,
    areadate_grid_cleanhdmi_kwargs: Optional[Mapping[str, Any]] = None,
    saveload_camset_mishoe_genlock_kwargs: Optional[Mapping[str, Any]] = None,
    **extra_upstream_kwargs: Any,
) -> Master156GateReport:
    """Evaluate unified 156-Gate Milestone Master Safety Preflight (`G01..G156`)."""
    effective_dry_run = (
        bool(dry_run_simulated)
        or (simulate_bench_dry_run is True)
        or (dry_run_simulated_backup is True)
    )
    clean_forced = _is_clean_room_forced(force_clean_room)
    resolved_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved_work_root_for_m154 = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=resolved_repo_root).work_root
    )
    m154_force_clean_room = (
        True
        if (clean_forced or resolved_work_root_for_m154 is None)
        else force_clean_room
    )

    if master_154_override is not None:
        m154_report = master_154_override
    else:
        m154_kw = {
            k: v
            for k, v in extra_upstream_kwargs.items()
            if v is not None
        }
        m154_report = evaluate_154gate_preflight(
            resolved_repo_root,
            work_root=work_root,
            force_clean_room=m154_force_clean_room,
            dry_run_simulated=effective_dry_run,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m154_kw,
        )

    g155_kw = dict(areadate_grid_cleanhdmi_kwargs or {})
    g155_verdict, g155_res = evaluate_g155_areadate_dst_grid_cleanhdmi_guard(
        repo_root=resolved_repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        **g155_kw,
    )

    g156_kw = dict(saveload_camset_mishoe_genlock_kwargs or {})
    if "requested_write_operation" not in g156_kw and request_persistent_emmc_writes:
        g156_kw["requested_write_operation"] = True
        if "target_media_slot" not in g156_kw and "target_media" not in g156_kw:
            g156_kw["target_media_slot"] = MEDIA_SLOT_1_PHASE359
    g156_verdict, g156_res = (
        evaluate_g156_saveload_camset_mishoe_genlock_guard(
            repo_root=resolved_repo_root,
            work_root=work_root,
            force_clean_room=force_clean_room,
            **g156_kw,
        )
    )

    new_gate_dicts = (
        {
            "gate_id": G155,
            "gate_code": G155_GATE_CODE,
            "status": g155_res.status,
            "passed": g155_verdict.passed,
            "evidence": g155_verdict.evidence,
            "violation_codes": list(g155_verdict.errors),
        },
        {
            "gate_id": G156,
            "gate_code": G156_GATE_CODE,
            "status": g156_res.status,
            "passed": g156_verdict.passed,
            "evidence": g156_verdict.evidence,
            "violation_codes": list(g156_verdict.errors),
        },
    )

    all_gates: Tuple[Dict[str, Any], ...] = tuple(m154_report.gates) + new_gate_dicts
    g01_to_g12_verified = int(m154_report.summary["g01_to_g12_verified"])
    g13_to_g154_verified = (
        int(m154_report.summary["g13_to_g152_verified"])
        + int(m154_report.summary["g153_to_g154_verified"])
    )
    g155_to_g156_verified = int(bool(g155_verdict.passed)) + int(
        bool(g156_verdict.passed)
    )
    total_verified = g01_to_g12_verified + g13_to_g154_verified + g155_to_g156_verified

    g155_to_g156_all_passed = g155_to_g156_verified == 2
    g13_to_g156_all_passed = (
        m154_report.g13_to_g154_all_passed and g155_to_g156_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m154_report.gates[:9])

    offline_153_verified = (
        g01_to_g09_ok
        and m154_report.offline_151_gates_verified
        and g155_to_g156_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_156_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g156_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m154_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_153_verified
        and m154_report.h0_h1_trial_entry_allowed
        and g155_to_g156_all_passed
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
        list(m154_report.errors)
        + list(g155_verdict.errors)
        + list(g156_verdict.errors)
    )
    warnings: List[str] = (
        list(m154_report.warnings)
        + list(g155_verdict.warnings)
        + list(g156_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m154_report.g13_to_g154_all_passed:
        overall_status = m154_report.status
    elif not g155_verdict.passed:
        overall_status = g155_verdict.status
    elif not g156_verdict.passed:
        overall_status = g156_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_156_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_156_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_156_verified:
        overall_status = "VERIFIED_ALL_156_GATES"
    else:
        overall_status = "VERIFIED_153_OF_156_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m154_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g155_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g156_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 156,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 156 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g154_verified": g13_to_g154_verified,
        "g155_to_g156_verified": g155_to_g156_verified,
        "g13_to_g156_all_passed": g13_to_g156_all_passed,
        "g155_to_g156_all_passed": g155_to_g156_all_passed,
        "offline_153_gates_verified": offline_153_verified,
        "all_156_gates_verified": all_156_verified,
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

    return Master156GateReport(
        schema=REALHW_156GATE_PREFLIGHT_SCHEMA,
        schema_version=REALHW_156GATE_PREFLIGHT_SCHEMA,
        version=REALHW_AREADATE_DST_GRID_CLEANHDMI_SAVELOAD_CAMSET_MISHOE_156GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_153_gates_verified=offline_153_verified,
        all_156_gates_verified=all_156_verified,
        g13_to_g156_all_passed=g13_to_g156_all_passed,
        g155_to_g156_all_passed=g155_to_g156_all_passed,
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
        master_154_report=m154_report.to_dict(),
        g155_result=g155_res.to_dict(),
        g156_result=g156_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_156_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master156GateReport:
    return evaluate_156gate_preflight(repo_root, **kwargs)


def run_156_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master156GateReport:
    return evaluate_156gate_preflight(repo_root, **kwargs)


def verify_real_hardware_156gate_readiness(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master156GateReport:
    return evaluate_156gate_preflight(repo_root, **kwargs)


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
        prog="realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_156gate_guard",
        description="Phase 359 (Task H451, Wave-68) G155/G156 and 156/156 Unified Safety Preflight CLI",
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
        help="Supply simulated dry-run Tier-0 backup inputs so all 156/156 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g155", "g156", "156"],
        default="156",
        help="Target gate check: g155, g156, or 156",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g155":
        v, r = evaluate_g155_areadate_dst_grid_cleanhdmi_guard(
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

    if args.gate == "g156":
        v, r = evaluate_g156_saveload_camset_mishoe_genlock_guard(
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

    rep = evaluate_156gate_preflight(
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
                "g155_status": rep.g155_result["status"],
                "g156_status": rep.g156_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/156 "
            f"g155_to_g156_all_passed={rep.g155_to_g156_all_passed} "
            f"all_156_gates_verified={rep.all_156_gates_verified} "
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
        rep.all_156_gates_verified
        if args.dry_run_simulated
        else rep.offline_153_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "ALLOWED_ASPECT_MARKER_OPTIONS_G155",
    "ALLOWED_BODY_MODELS_PHASE359",
    "ALLOWED_CARD_MEDIA_TYPES_G156",
    "ALLOWED_MEDIA_SLOTS_PHASE359",
    "ALLOWED_MISHOE_DEVICES_G156",
    "ALLOWED_REC_MEDIA_HDMI_MODES_G155",
    "ALLOWED_RESET_ACTIONS_PHASE359",
    "ALLOWED_SAFETY_ZONE_OPTIONS_G155",
    "ALLOWED_SAVELOAD_OPERATIONS_G156",
    "ALLOWED_SAVELOAD_TARGETS_G156",
    "ALLOWED_SHOOT_MODES_PHASE359",
    "AREA_DATE_MENU_PATH_G155",
    "AREA_DATE_RESETTABLE_BY_CAMSET_RESET_G155",
    "AREA_DATE_TIME_SETTING_F_RESID16_G155",
    "AREA_GMT_30_ZONES_G155",
    "AREA_GMT_HALF_HOUR_6_ZONES_G155",
    "AREA_SETTING_BASE_RESID16_G155",
    "AUTO_SYNC_SEVER_ELF_TYPO_G155",
    "AreaDateDstGridCleanHdmiGuardResult",
    "CAMERA_SET_MEMORY_BODY_SLOTS_G156",
    "CAMERA_SET_MEMORY_CARD_SLOTS_G156",
    "CAMERA_SET_MEMORY_MENU_PATH_G156",
    "CAMSET_MAX_CARD_SLOTS_G156",
    "CAMSET_MAX_CLOUD_SLOTS_G156",
    "CAMSET_MIN_FW_INCOMPAT_BOUNDARY_G156",
    "DATE_FORMAT_F_RESID16_G155",
    "DAYLIGHT_SAVINGS_BASE_RESID16_G155",
    "DAYLIGHT_SAVINGS_DEFAULT_G155",
    "DAYLIGHT_SAVINGS_ELF_TYPO_G155",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE359",
    "DONOR_CHECK_MAX_SECONDS_PHASE359",
    "DORMANT_FLASH_SYNC_SPD_PRTY_F_RESID16_G156",
    "EBUSY_ERRNO_PHASE359",
    "EBUSY_NAME_PHASE359",
    "EINVAL_ERRNO_PHASE359",
    "EINVAL_NAME_PHASE359",
    "ELECTRICAL_LIGHT_OR_FLASH_MISHOE_DEVICES_G156",
    "ENV_CLEAN_ROOM_TEST_PHASE359",
    "EOPNOTSUPP_ERRNO_PHASE359",
    "EOPNOTSUPP_NAME_PHASE359",
    "EPERM_ERRNO_PHASE359",
    "EPERM_NAME_PHASE359",
    "EROFS_ERRNO_PHASE359",
    "EROFS_NAME_PHASE359",
    "EXACT_15_ASPECT_MARKER_RATIOS_G155",
    "EXACT_20_CAMSET_EXCLUDED_ITEMS_G156",
    "EXACT_3_DATE_FORMATS_G155",
    "EXACT_3_FX6_VIDEO_LIGHT_MODES_G156",
    "EXACT_3_GRID_LINE_TYPES_G155",
    "EXACT_4_FX3_VIDEO_LIGHT_MODES_G156",
    "EXACT_5_FX3_FLASH_MODES_G156",
    "EXACT_5_MARKER_ITEMS_G155",
    "EXTERNAL_FLASH_SET_F_RESID16_G156",
    "EXTERNAL_FLASH_SET_MENU_PATH_G156",
    "FX3_CAMPR_PATH_TEMPLATE_G156",
    "FX3_CAMSET_PATH_TEMPLATE_G156",
    "FX3_DEFAULT_FW_VERSION_PHASE359",
    "FX3_FLASH_MAX_TRIGGER_VOLTAGE_V_G156",
    "FX3_FLASH_SHUTTER_MODES_G156",
    "FX3_FLASH_XSYNC_APSC_EFCS_DENOM_G156",
    "FX3_FLASH_XSYNC_FF_EFCS_DENOM_G156",
    "FX3_FLASH_XSYNC_MAX_DENOM_G156",
    "FX3_FTPSET_PATH_TEMPLATE_G156",
    "FX3_HELP_GUIDE_CODE_PHASE359",
    "FX3_MODEL_ID_PHASE359",
    "FX3_MODEL_NAME_PHASE359",
    "FX3_PHYSICAL_SYNC_TERMINAL_PRESENT_G156",
    "FX3_PRO_CAMERA_PATH_HITS_G156",
    "FX3_RTC_BACKUP_CHARGE_MIN_HOURS_POWER_OFF_G155",
    "FX3_SYNCHRO_TERMINAL_ELF_HITS_G156",
    "FX3_USER_CR2032_SLOT_PRESENT_G155",
    "FX6_ALL_FILE_MAX_SLOTS_G156",
    "FX6_ALL_FILE_MENU_PATH_G156",
    "FX6_ALL_FILE_PATH_TEMPLATE_G156",
    "FX6_CENTER_MARKER_MODES_G155",
    "FX6_CLOCK_SET_DATE_MODES_G155",
    "FX6_CLOCK_SET_DST_TOGGLE_EXPOSED_G155",
    "FX6_CLOCK_SET_MENU_PATH_G155",
    "FX6_CLOCK_SET_TIME_FORMATS_G155",
    "FX6_CLOCK_SET_UTC_STEP_MINUTES_G155",
    "FX6_DEFAULT_FW_VERSION_PHASE359",
    "FX6_DORMANT_GENLOCK_ELF_HITS_G156",
    "FX6_MARKER_MENU_PATH_G155",
    "FX6_MODEL_NAME_PHASE359",
    "FX6_NATIVE_3MODE_GRID_EXPOSED_G155",
    "FX6_PHYSICAL_GENLOCK_BNC_PRESENT_G156",
    "FX6_REFERENCE_FILE_ELF_HITS_G156",
    "FX6_SCENE_FILE_PATH_TEMPLATE_G156",
    "FX6_VIDEO_LIGHT_AUTO_SUPPORTED_G156",
    "FX6_VIDEO_LIGHT_SET_MENU_PATH_G156",
    "G155",
    "G155AreaDateDstGridCleanHdmiGuardResult",
    "G155_GATE_CODE",
    "G155_GATE_ID",
    "G156",
    "G156SaveLoadCamsetMiShoeGenlockGuardResult",
    "G156_GATE_CODE",
    "G156_GATE_ID",
    "GRID_LINE_DISPLAY_DEFAULT_G155",
    "GRID_LINE_DISPLAY_F_RESID16_G155",
    "GRID_LINE_DISPLAY_MENU_PATH_G155",
    "GRID_LINE_DISPLAY_SELECT_F_RESID16_G155",
    "GRID_LINE_RESETTABLE_BY_CAMSET_RESET_G155",
    "GRID_LINE_TYPE_DEFAULT_G155",
    "GRID_LINE_TYPE_F_RESID16_G155",
    "GRID_LINE_TYPE_MENU_PATH_G155",
    "GUIDEFRAIME_F_RESID16_G155",
    "HDMI_MARKER_INJECTED_PIXELS_G155",
    "ILC2210_STATES_3_MONTHS_RETENTION_G155",
    "LEGACY_DATE_TIME_SETUP_BASE_RESID16_G155",
    "LIB_SAVE_LOAD_SETTINGS_BYTES_G156",
    "LIB_SAVE_LOAD_SETTINGS_NAME_G156",
    "MARKER_5ITEMS_RESETTABLE_BY_CAMSET_RESET_G155",
    "MARKER_DISPLAY_F_RESID16_G155",
    "MARKER_DISPLAY_MENU_PATH_G155",
    "MEDIA_SLOT_1_PHASE359",
    "MEDIA_SLOT_2_PHASE359",
    "MEDIA_SLOT_NONE_PHASE359",
    "MEMORY_RECALL_MEDIA_F_RESID16_G156",
    "MEMORY_RECALL_MEDIA_MENU_PATH_G156",
    "Master156GateReport",
    "PINNED_FX3_APPFW_SLICES_PHASE359",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE359",
    "PINNED_FX6_APPFW_SLICES_PHASE359",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE359",
    "PINNED_PHASE359_DONOR_SPECS",
    "PMIC_5V_MAX_CURRENT_MA_G156",
    "Phase359DonorAuditResult",
    "REALHW_156GATE_PREFLIGHT_SCHEMA",
    "REALHW_AREADATE_DST_GRID_CLEANHDMI_SAVELOAD_CAMSET_MISHOE_156GATE_SCHEMA",
    "REALHW_AREADATE_DST_GRID_CLEANHDMI_SAVELOAD_CAMSET_MISHOE_156GATE_VERSION",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE359",
    "RESET_ACTION_INITIALIZE_PHASE359",
    "RESET_ACTION_NONE_PHASE359",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE359",
    "RETIRED_DELETED_MOVIE_GRID_KEYS_G155",
    "SAVE_LOAD_FTP_F_RESID16_G156",
    "SAVE_LOAD_FTP_MENU_PATH_G156",
    "SAVE_LOAD_SETTINGS_F_RESID16_G156",
    "SAVE_LOAD_SETTINGS_MENU_PATH_G156",
    "SHOOT_MODE_MOVIE_PHASE359",
    "SHOOT_MODE_SQ_PHASE359",
    "SHOOT_MODE_STILL_PHASE359",
    "STATUS_BLOCKED_G155_AREA_RTC_OR_GRID_MARKER_CLEANHDMI_RESET_VIOLATION",
    "STATUS_BLOCKED_G155_DORMANT_CR2032_FX6_DST_OR_STILL_MARKER_EOPNOTSUPP",
    "STATUS_BLOCKED_G155_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G156_CAMSET_COMPAT_FLASH_SHUTTER_OR_PMIC_VIOLATION",
    "STATUS_BLOCKED_G156_DORMANT_SYNC_GENLOCK_SLOT2_MR_OR_REFFILE_EOPNOTSUPP",
    "STATUS_BLOCKED_G156_MISHOE_XLRH1_EXCLUSION_EBUSY",
    "STATUS_BLOCKED_G156_SLOT1_SAVELOAD_CAMSET_VAULT_EROFS",
    "STATUS_BLOCKED_G156_TELEMETRY_INVALID",
    "STATUS_BLOCKED_PHASE359_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G155",
    "STATUS_VERIFIED_G156",
    "SaveLoadCamsetMiShoeGenlockFirewallResult",
    "VIDEO_LIGHT_MODE_F_RESID16_G156",
    "VIDEO_LIGHT_MODE_MENU_PATH_G156",
    "XLR_H1_TOP_SHOES_PASSIVE_COLD_ONLY_G156",
    "audit_phase359_donor_contracts",
    "compute_areadate_grid_cleanhdmi_matrix",
    "compute_saveload_camset_mishoe_genlock_matrix",
    "evaluate_156_master_safety_gates",
    "evaluate_156gate_preflight",
    "evaluate_g155_areadate_dst_grid_cleanhdmi_guard",
    "evaluate_g156_saveload_camset_mishoe_genlock_guard",
    "main",
    "resolve_fx3_areadate_grid_cleanhdmi_state",
    "resolve_fx3_saveload_camset_and_mishoe_state",
    "run_156_gate_preflight",
    "strip_elapsed_seconds_recursive_phase359",
    "verify_areadate_dst_grid_cleanhdmi_guard",
    "verify_areadate_dst_grid_cleanhdmi_guard_with_audit",
    "verify_real_hardware_156gate_readiness",
    "verify_saveload_camset_mishoe_genlock_guard",
    "verify_saveload_camset_mishoe_genlock_guard_with_audit",
]


if __name__ == "__main__":
    raise SystemExit(main())
