"""Phase 374 Milestone — 25th Physical Bench Readiness Verifier (`25/25` Milestone).

Implements `preflight-silentmode-dro-fanctrl-hoursmeter-afillum-shutter-flash-and-format`
(short CLI alias `preflight-phase374`) aligned with Global Sony Real-Hardware Empirical
Intelligence Waves 81-82 across Check Groups A-D and the mandatory `16/16 H0 == H3`
dual-media `528 B FX3RCPT1` Tier-0 Receipt Gate:

- **Check Group A** (Wave 81.1-81.2: Silent Mode 2-Item Target Function & DRO vs Dormant
  Auto HDR / Multi Frame NR & FX6 Paint/Look):
  - `[Silent Mode Settings] -> [Target Function Settings]` exposes EXACTLY 2 items
    (`[Aperture Drive in AF]` Standard/Silent Priority/Not Target + `[Auto Pixel Mapping]`
    Off/Not Target); dormant `[Shutter When Pwr OFF]` (`image_sensor_barrier`) &
    `[Anti-dust Function]` are 100% blocked (`EOPNOTSUPP=95`); ALL 3 under Silent Mode
    (`Silent Mode` + 2 Target Function items) are `Can be reset` under `[Camera Settings
    Reset]` (only top-level `Setup -> [Auto Pixel Mapping]` is anti-reset). Enforces 5-item
    Silent Mode lockouts (Flash, Long Exposure NR, e-Front Curtain Shut., BULB, Anti-flicker
    Shoot.) vs FX6 shutterless electronic rolling shutter + `Auto Pixel Restore`.
  - `[D-Range Optimizer]` (`Off`/`Auto`/`Lv1..Lv5`, `Can be reset`, locked `Off` out-of-box
    by default `PP11`, `[Log Shooting] != Off`, or `[HLG Still Image] = On`); zero `Auto HDR`
    and zero `Multi Frame NR` in FX3 (`0` ELF hits) vs FX6 `Custom`-only `Paint/Look` `Black`
    & `Knee` (zero UI `Black Gamma`/`White Clip`).
- **Check Group B** (Wave 81.3-81.4: Audio Signals, 4-Mode Fan Control, Version/LENSDATA
  `NO-GO` & FX6 Hours Meter):
  - FX3 `[Audio signals]` exposes ONLY `On` (default) / `Off` (anti-Camera-Reset; Wave 81
    `G85` erratum: reject dormant `On: all` / `On: shutter only` / `On: e-shutter only`).
  - FX3 `[Fan Control]` exposes EXACTLY 4 modes (`Auto` / `Minimum` / `Off in Rec` /
    `Always Off`, anti-Camera-Reset; Wave 81 `G82` erratum: zero `Auto1`/`Auto2`) vs FX6
    `Technical > Fan Control` EXACTLY 3 modes (`Auto` / `Minimum` / `Off in Rec`; zero `Max`,
    zero UI `Always Off`) + `Alarm Level` (`0..7`).
  - FX3 `[Version]` (`Body`/`Lens`/`Mount Adaptor`), `/BODYDATA.DAT` & `LENSDATA.DAT` / USB
    UUD lens update strictly `NO-GO / BLOCKED` (`Slot 1 EROFS=30`), region-gated
    `[Certification Logo]`, and FX6 `Maintenance > Hours Meter` (`Hours(System)` permanent
    anti-Reset/anti-All-Reset vs `Hours(Reset)` resettable; zero UI exposure on FX3).
- **Check Group C** (Wave 82.1-82.2: Physical AF Illuminator LED, 3 Anti-Reset Still AF
  Controls, 2-Option Shutter Type & Anti-Reset EFCS):
  - FX3 front-panel physical `AF Illuminator` LED (`0.3-3.0 m`, `Auto` default / `Off`,
    `Can be reset`, Still-only, NOT disabled by `[Silent Mode] = On`, disabled in
    Movie/S&Q/AF-C/Focus Mag/Mount Adaptor).
  - Still-only `Focus -> [AF/MF]` triad: `[Aperture Drive in AF]` (Focus Priority/Standard/
    Silent Priority), `[AF w/ Shutter]` (`On`/`Off`), `[Pre-AF]` (`Off`/`On`) — ALL 3
    `Not available` (anti-Camera-Reset, contrasting with Silent Mode Target Function's
    `Can be reset`) vs FX6 zero AF illuminator / zero half-press AF (`Push AF Mode`).
  - FX3 `[Shutter Type]` exposes EXACTLY 2 options (`Mechanical Shutter` default /
    `Electronic Shutter`, ZERO `Auto`, `Can be reset`, `1/8000 s` max both, `BULB`
    mech-only); `[e-Front Curtain Shut.]` (`On` default / `Off`, Sony ELF typo
    `BKID_APP_setting_front_curtaion_shutter`) is anti-Camera-Reset (`Not available`) with
    high-speed wide-aperture bokeh-clipping / 3rd-party lens guidance vs FX6 shutterless
    electronic shutter + `ECS`.
- **Check Group D + Tier-0** (Wave 82.3-82.4 + `16/16 H0 == H3` Dual-Media `528 B FX3RCPT1`):
  - FX3 MI Shoe Flash: strict `1/250 s` mechanical X-sync ceiling (Wave 82 `G156` erratum:
    zero `1/320 s` APS-C, zero `1/160 s`/`1/200 s` EFCS downgrade, 100% locked out in
    Electronic Shutter / Silent Mode; HSS `>1/250 s` via compatible flash; zero PC sync
    terminal; `<250V` positive polarity), `[Exp.comp.set]` anti-reset, `[External Flash Set.]`
    0 body `BKID` (anti-reset & excluded from `CAMSET*.DAT`), and ZERO `[Reg. Flash Shooting
    Set.]` (`EOPNOTSUPP=95`) vs FX6 zero flash sync + `Flash Band Reduce`.
  - FX3 `[Long Exposure NR]` (`On` default, `>= 1 s`/BULB, disabled in Electronic Shutter /
    Cont. Shooting / Cont. Bracket) & `[High ISO NR]` exact 3 levels (`Normal`/`Low`/`Off`,
    zero `High`, never mutates `.ARW`) vs FX6 `Noise Suppression`.
  - FX3 `[Format]` `Quick Format` (`libmpr.so` `:/AVF_INFO` rebuild) vs `Full Format`
    (`(Delete)` toggle -> `fsysDepMCmn_EraseDataFull`, SD `EraseBlock`/`DISCARD`, CFexpress
    `NVME_FORMAT`/`DISCARD`, irreversible) vs FX6 `TC/Media > Format Media` — ALL targeting
    Slot 1 MUST return `EROFS=30` (`slot1_data_sector_writes == 0`).
  - Tier-0 Receipt Gate: Dual-media `528 B FX3RCPT1` Copy A & Copy B with distinct `st_dev`,
    `16/16 H0 == H3`, non-trivial serial/CID, `0x91030080` + fw `7.02`.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from fx3_recovery.realhw_adjustcontrol_streaming_backup_client import (
    COLD_BACKUP_ITEMS,
    SD_RECEIPT_BYTES,
    build_sd_backup_receipt_bytes,
    parse_sd_backup_receipt_bytes,
)

from .donor_paths import (
    is_forced_clean_room,
    iter_work_roots,
    resolve_work_subpath,
)
from .realhw_card_insert_readiness_verifier import (
    BODY_SERIAL_RE,
    DONOR_INSPECTION_MAX_SECONDS,
    FORBIDDEN_TRIVIAL_CIDS,
    FORBIDDEN_TRIVIAL_SERIALS,
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    HEX32_CID_RE,
    REQUIRED_H0_BASELINE_KEYS,
    TARGET_BODY_FW,
    TARGET_MODEL_ID_HEX,
    TARGET_MODEL_ID_INT,
    _is_trivial_hex64,
    build_default_h0_baselines,
)
from .realhw_sd_stageb_bundle_and_uninstaller import SIXTEEN_STORAGE_SURFACES

# ---------------------------------------------------------------------------
# Version / Schema / Go-No-Go / Locked Zero-Telemetry Constants
# ---------------------------------------------------------------------------

P374_VERSION = "phase374_v1"
PHASE374_VERSION = P374_VERSION
PHASE_374_VERSION = P374_VERSION

P374_SCHEMA = (
    "realhw_preflight25_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_format_v1"
)
P374_SCHEMA_VERSION = P374_SCHEMA
PHASE_374_SCHEMA = P374_SCHEMA
REALHW_SILENTMODE_DRO_FANCTRL_HOURSMETER_AFILLUM_SHUTTER_FLASH_FORMAT_SCHEMA = P374_SCHEMA

P374_SONY_HELP_GUIDE_ID = "ilc/2210"
P374_STORAGE_SURFACE_COUNT = 16
P374_HEADER_READ_BYTES = 64

P374_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS = "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
P374_GO_NO_GO_SILENTMODE_DRO_FANCTRL_HOURSMETER_AFILLUM_SHUTTER_FLASH_AND_FORMAT_VERIFIED = (
    "READONLY_PREFLIGHT25_SILENTMODE_DRO_FANCTRL_HOURSMETER_AFILLUM_SHUTTER_FLASH_AND_FORMAT_VERIFIED"
)
P374_GO_NO_GO_BLOCKED_SILENTMODE_DRO_FANCTRL_HOURSMETER_AFILLUM_SHUTTER_FLASH_AND_FORMAT_FAILURE = (
    "BLOCKED_SILENTMODE_DRO_FANCTRL_HOURSMETER_AFILLUM_SHUTTER_FLASH_AND_FORMAT_FAILURE"
)
PHASE_374_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P374_GO_NO_GO_SILENTMODE_DRO_FANCTRL_HOURSMETER_AFILLUM_SHUTTER_FLASH_AND_FORMAT_VERIFIED,
    P374_GO_NO_GO_BLOCKED_SILENTMODE_DRO_FANCTRL_HOURSMETER_AFILLUM_SHUTTER_FLASH_AND_FORMAT_FAILURE,
)

P374_CHECK_GROUP_A_ID = "p374_ga_silentmode_target2_dro_autohdr_fx6_paintlook"
P374_CHECK_GROUP_B_ID = "p374_gb_audiosignals_fanctrl4_version_lensdat_fx6_hoursmeter"
P374_CHECK_GROUP_C_ID = "p374_gc_afillum_antireset_af3_shutter2_efcs_fx6_shutterless"
P374_CHECK_GROUP_D_ID = "p374_gd_flash250_extflash_nr_format_slot1_erofs30_tier0"
PHASE_374_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P374_CHECK_GROUP_A_ID,
    P374_CHECK_GROUP_B_ID,
    P374_CHECK_GROUP_C_ID,
    P374_CHECK_GROUP_D_ID,
)

# Errno constants
P374_ERRNO_EPERM = 1
P374_ERRNO_EBUSY = 16
P374_ERRNO_EINVAL = 22
P374_ERRNO_EROFS = 30
P374_ERRNO_EOPNOTSUPP = 95

# Locked zero telemetry constants
PHASE374_EMMC_WRITE_COUNT = 0
PHASE374_E_ND_ACTUATOR_TX_COUNT = 0
PHASE374_E_ND_I2C_TX_BYTES = 0
PHASE374_RF_TX_PACKETS = 0
PHASE374_RF_PACKETS_TRANSMITTED = 0
PHASE374_WIRELESS_RF_PACKETS_EMITTED = 0
PHASE374_RF_NVS_MUTATION_BYTES = 0
PHASE374_SLOT1_SECTOR_WRITES = 0
PHASE374_SLOT1_DATA_SECTOR_WRITES = 0
PHASE374_USB_PACKETS_TRANSMITTED = 0
PHASE374_PASSIVE_TX_BYTES_EMITTED = 0
PHASE374_RAW_FIRMWARE_BYTES_LEAKED = 0

P374_VALID_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "RESET_NETWORK_SET",
    "INITIALIZE",
)
P374_VALID_SHOOT_MODES: Tuple[str, ...] = ("PHOTO", "MOVIE", "S_AND_Q")
P374_VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "OFF",
    "FLEXIBLE_ISO",
    "CINE_EI_QUICK",
    "CINE_EI",
)
P374_VALID_ON_OFF: Tuple[str, ...] = ("ON", "OFF")
P374_VALID_FOCUS_MODES: Tuple[str, ...] = ("AF_S", "AF_A", "AF_C", "DMF", "MF")
P374_VALID_STILL_DRIVE_MODES: Tuple[str, ...] = (
    "SINGLE_SHOOTING",
    "CONT_SHOOTING",
    "SELF_TIMER_SINGLE",
    "SELF_TIMER_CONT",
    "CONT_BRACKET",
    "SINGLE_BRACKET",
    "WB_BRACKET",
    "DRO_BRACKET",
)

# ---------------------------------------------------------------------------
# Wave 81 Group A Constants: Silent Mode 2-Item Target & DRO vs Auto HDR / FX6 Paint/Look
# ---------------------------------------------------------------------------

P374_SILENT_TARGET_EXACT_2_ITEMS: Tuple[str, ...] = (
    "Aperture Drive in AF",
    "Auto Pixel Mapping",
)
P374_SILENT_TARGET_DORMANT_ITEMS: Tuple[str, ...] = (
    "Shutter When Pwr OFF",
    "Anti-dust Function",
)
P374_SILENT_TARGET_APERTURE_MODES: Tuple[str, ...] = (
    "STANDARD",
    "SILENT_PRIORITY",
    "NOT_TARGET",
)
P374_SILENT_TARGET_APERTURE_DEFAULT = "STANDARD"
P374_SILENT_TARGET_AUTO_PIXEL_MAP_MODES: Tuple[str, ...] = ("OFF", "NOT_TARGET")
P374_SILENT_TARGET_AUTO_PIXEL_MAP_DEFAULT = "OFF"
P374_SILENT_MODE_EXACT_5_LOCKOUTS: Tuple[str, ...] = (
    "FLASH_SHOOTING",
    "LONG_EXPOSURE_NR",
    "E_FRONT_CURTAIN_SHUT",
    "BULB",
    "ANTI_FLICKER_SHOOT",
)
P374_DRO_MODES: Tuple[str, ...] = ("OFF", "AUTO", "LV1", "LV2", "LV3", "LV4", "LV5")
P374_DRO_DEFAULT_UNLOCKED = "AUTO"
P374_DRO_BRACKET_MODES: Tuple[str, ...] = ("NONE", "LO", "HI")
P374_DRO_DORMANT_FEATURES: Tuple[str, ...] = ("AUTO_HDR", "MULTI_FRAME_NR")
P374_FX6_SHOOTING_MODES: Tuple[str, ...] = ("CUSTOM", "CINE_EI", "CINE_EI_QUICK", "FLEXIBLE_ISO")
P374_FX6_KNEE_POINT_MIN_PCT = 75
P374_FX6_KNEE_POINT_MAX_PCT = 109
P374_FX6_KNEE_POINT_DEFAULT_PCT = 90
P374_FX6_KNEE_SLOPE_MIN = -99
P374_FX6_KNEE_SLOPE_MAX = 99
P374_FX6_KNEE_SLOPE_DEFAULT = 0
P374_FX6_BLACK_MIN = -99.0
P374_FX6_BLACK_MAX = 99.0
P374_FX6_BLACK_DEFAULT = 0.0
P374_FX6_DORMANT_PAINT_ITEMS: Tuple[str, ...] = ("BLACK_GAMMA", "WHITE_CLIP")

# ---------------------------------------------------------------------------
# Wave 81 Group B Constants: Audio Signals (G85), 4-Mode Fan (G82), Version & FX6 Hours Meter
# ---------------------------------------------------------------------------

P374_FX3_AUDIO_SIGNALS_EXACT_2_MODES: Tuple[str, ...] = ("ON", "OFF")
P374_FX3_AUDIO_SIGNALS_DEFAULT = "ON"
P374_FX3_AUDIO_SIGNALS_DORMANT_G85_MODES: Tuple[str, ...] = (
    "ON_ALL",
    "ON_SHUTTER_ONLY",
    "ON_ESHUTTER_ONLY",
)
P374_FX3_FAN_CONTROL_EXACT_4_MODES: Tuple[str, ...] = (
    "AUTO",
    "MINIMUM",
    "OFF_IN_REC",
    "ALWAYS_OFF",
)
P374_FX3_FAN_CONTROL_DEFAULT = "AUTO"
P374_FX3_FAN_CONTROL_DORMANT_G82_MODES: Tuple[str, ...] = ("AUTO1", "AUTO2", "MAX")
P374_FX6_FAN_CONTROL_EXACT_3_MODES: Tuple[str, ...] = ("AUTO", "MINIMUM", "OFF_IN_REC")
P374_FX6_FAN_CONTROL_DORMANT_MODES: Tuple[str, ...] = ("MAX", "ALWAYS_OFF")
P374_FX6_ALARM_LEVEL_MIN = 0
P374_FX6_ALARM_LEVEL_MAX = 7
P374_FX6_ALARM_LEVEL_DEFAULT = 4
P374_AUTO_POWER_OFF_TEMP_MODES: Tuple[str, ...] = ("STANDARD", "HIGH")
P374_AUTO_POWER_OFF_TEMP_DEFAULT = "STANDARD"
P374_VERSION_EXACT_3_ENTITIES: Tuple[str, ...] = ("Body", "Lens", "Mount Adaptor")
P374_BODY_UPDATE_FILENAME = "/BODYDATA.DAT"
P374_LENS_UPDATE_FILENAME = "LENSDATA.DAT"
P374_CERT_LOGO_REGIONS: Tuple[str, ...] = ("JP_DOMESTIC", "US_EU_INTL")
P374_FX6_HOURS_RESET_ACTIONS: Tuple[str, ...] = ("NONE", "HOURS_METER_RESET", "ALL_RESET")

# ---------------------------------------------------------------------------
# Wave 82 Group C Constants: AF Illuminator LED, 3 Anti-Reset AF, 2-Opt Shutter Type & EFCS
# ---------------------------------------------------------------------------

P374_AF_ILLUMINATOR_MODES: Tuple[str, ...] = ("AUTO", "OFF")
P374_AF_ILLUMINATOR_DEFAULT = "AUTO"
P374_AF_ILLUMINATOR_RANGE_MIN_M = 0.3
P374_AF_ILLUMINATOR_RANGE_MAX_M = 3.0
P374_AF_FOCUS_TRIAD_ANTIRESET_ITEMS: Tuple[str, ...] = (
    "Aperture Drive in AF",
    "AF w/ Shutter",
    "Pre-AF",
)
P374_FOCUS_APERTURE_DRIVE_MODES: Tuple[str, ...] = (
    "FOCUS_PRIORITY",
    "STANDARD",
    "SILENT_PRIORITY",
)
P374_FOCUS_APERTURE_DRIVE_DEFAULT = "STANDARD"
P374_SHUTTER_TYPE_EXACT_2_OPTIONS: Tuple[str, ...] = (
    "MECHANICAL_SHUTTER",
    "ELECTRONIC_SHUTTER",
)
P374_SHUTTER_TYPE_DEFAULT = "MECHANICAL_SHUTTER"
P374_SHUTTER_TYPE_DORMANT_OPTIONS: Tuple[str, ...] = ("AUTO",)
P374_STILL_MAX_SHUTTER_DENOM = 8000
P374_EFCS_BKID_TYPO = "BKID_APP_setting_front_curtaion_shutter"
P374_EFCS_BOKEH_GUIDANCE_THRESHOLD_DENOM = 1000

# ---------------------------------------------------------------------------
# Wave 82 Group D Constants: MI Flash 1/250 s (G156), External Flash, NR, Quick/Full Format
# ---------------------------------------------------------------------------

P374_FX3_FLASH_XSYNC_MAX_DENOM = 250
P374_FX3_FLASH_HSS_BANDING_WARN_DENOM = 4000
P374_FX3_FLASH_MAX_TRIGGER_VOLTAGE_V = 250.0
P374_FX3_FLASH_MODES: Tuple[str, ...] = (
    "AUTOFLASH",
    "FLASH_OFF",
    "FILL_FLASH",
    "SLOW_SYNC",
    "REAR_SYNC",
)
P374_FX3_EXP_COMP_SET_MODES: Tuple[str, ...] = ("AMBIENT_AND_FLASH", "AMBIENT_ONLY")
P374_FX3_EXP_COMP_SET_DEFAULT = "AMBIENT_AND_FLASH"
P374_FX3_EXTERNAL_FLASH_BODY_BKID_COUNT = 0
P374_FX3_HIGH_ISO_NR_EXACT_3_LEVELS: Tuple[str, ...] = ("NORMAL", "LOW", "OFF")
P374_FX3_HIGH_ISO_NR_DEFAULT = "NORMAL"
P374_FX3_HIGH_ISO_NR_DORMANT_LEVELS: Tuple[str, ...] = ("HIGH",)
P374_FX6_NOISE_SUPPRESSION_LEVELS: Tuple[str, ...] = ("LOW", "MID", "HIGH")
P374_FORMAT_MODES: Tuple[str, ...] = ("NONE", "QUICK_FORMAT", "FULL_FORMAT")
P374_MEDIA_BUS_TYPES: Tuple[str, ...] = ("SDXC_MMCB", "CFEXPRESS_TYPE_A_NVME")
P374_QUICK_FORMAT_AVF_INFO_PATH = ":/AVF_INFO"
P374_FULL_FORMAT_ERASE_SYMBOL = "fsysDepMCmn_EraseDataFull"

# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Paths (Waves 81-82)
# ---------------------------------------------------------------------------

P374_BOUNDED_DONOR_PATHS: Tuple[Tuple[str, str], ...] = (
    ("fx3_appfw_so", "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"),
    ("fx3_cpapp_b_bin", "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"),
    (
        "fx3_libupdaterufp_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libupdaterufp.so",
    ),
    (
        "fx3_libinfragetversion_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraGetVersion.so",
    ),
    (
        "fx3_libinfrafsys_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraFsys.so",
    ),
    (
        "fx3_libinframediacommon_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaCommon.so",
    ),
    (
        "fx3_libmpr_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so",
    ),
    (
        "fx3_libsaveloadsettings_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
    ),
    (
        "fx3_string_english_f_uxc",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
    ),
    (
        "fx6_appfw_so",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
    ),
    (
        "fx6_string_english_2_uxc",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
    ),
)

# ---------------------------------------------------------------------------
# Error Code Constants
# ---------------------------------------------------------------------------

P374_GA_ERR_MODEL_OR_FW_FLOOR = "P374_GA_ERR_MODEL_OR_FW_FLOOR"
P374_GA_ERR_SILENT_TARGET2_OR_DORMANT_BARRIER = "P374_GA_ERR_SILENT_TARGET2_OR_DORMANT_BARRIER"
P374_GA_ERR_SILENT_RESET_BOUNDARY_OR_5LOCKOUT = "P374_GA_ERR_SILENT_RESET_BOUNDARY_OR_5LOCKOUT"
P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR = "P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR"
P374_GA_ERR_FX6_SHUTTERLESS_OR_PAINT_LOOK_BOUNDARY = (
    "P374_GA_ERR_FX6_SHUTTERLESS_OR_PAINT_LOOK_BOUNDARY"
)

P374_GB_ERR_AUDIO_SIGNALS_2OPT_OR_G85_ERRATUM = "P374_GB_ERR_AUDIO_SIGNALS_2OPT_OR_G85_ERRATUM"
P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM = "P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM"
P374_GB_ERR_VERSION_UPDATE_NOGO_SLOT1_EROFS30 = "P374_GB_ERR_VERSION_UPDATE_NOGO_SLOT1_EROFS30"
P374_GB_ERR_CERT_LOGO_REGION_OR_FX6_HOURS_METER = (
    "P374_GB_ERR_CERT_LOGO_REGION_OR_FX6_HOURS_METER"
)

P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT = "P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT"
P374_GC_ERR_AF_TRIAD_ANTIRESET_OR_STILL_ONLY = "P374_GC_ERR_AF_TRIAD_ANTIRESET_OR_STILL_ONLY"
P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB = "P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB"
P374_GC_ERR_EFCS_ANTIRESET_BOKEH_OR_FX6_SHUTTERLESS = (
    "P374_GC_ERR_EFCS_ANTIRESET_BOKEH_OR_FX6_SHUTTERLESS"
)

P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT = (
    "P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT"
)
P374_GD_ERR_EXT_FLASH_BKID0_EXPCOMP_OR_FX6_FBR = "P374_GD_ERR_EXT_FLASH_BKID0_EXPCOMP_OR_FX6_FBR"
P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL = "P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL"
P374_GD_ERR_FORMAT_SLOT1_EROFS30_OR_QUICK_FULL_PATH = (
    "P374_GD_ERR_FORMAT_SLOT1_EROFS30_OR_QUICK_FULL_PATH"
)
P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID = (
    "P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P374_GD_ERR_H0_H3_IMMUTABILITY_DRIFT = "P374_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P374_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION = "P374_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"

# ---------------------------------------------------------------------------
# Timing-Stripping & Deterministic Hashing Helpers
# ---------------------------------------------------------------------------

_TIMING_STRIP_EXACT_KEYS = frozenset(
    {
        "elapsed_seconds",
        "elapsed_s",
        "elapsed_ms",
        "inspection_elapsed_ms",
        "wall_seconds",
    }
)


def _strip_timing_fields(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in value.items():
            if k in _TIMING_STRIP_EXACT_KEYS or (
                isinstance(k, str)
                and (
                    k.endswith("_elapsed_ms")
                    or k.endswith("_elapsed_s")
                    or k.endswith("_elapsed_seconds")
                )
            ):
                continue
            cleaned[k] = _strip_timing_fields(v)
        return cleaned
    if isinstance(value, list):
        return [_strip_timing_fields(item) for item in value]
    if isinstance(value, tuple):
        return [_strip_timing_fields(item) for item in value]
    return value


def _canonical_sha256_dict(payload: Mapping[str, Any]) -> str:
    body = dict(payload)
    body.pop("report_sha256", None)
    stripped = _strip_timing_fields(body)
    raw = json.dumps(stripped, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & Clean-Room Fallback
# ---------------------------------------------------------------------------


def _is_clean_room_env() -> bool:
    return is_forced_clean_room() or (
        os.environ.get("FX3_CLEAN_ROOM_TEST", "").strip().lower() in ("1", "true", "yes")
    )


def _resolve_work_root_or_none() -> Optional[Path]:
    if _is_clean_room_env():
        return None
    for root in iter_work_roots():
        if root.exists():
            return root
    return None


def resolve_phase374_donor_file_or_none(
    work_root: Optional[Path],
    rel_subpath: str,
) -> Optional[Path]:
    if work_root is None:
        return None
    try:
        candidate = resolve_work_subpath(rel_subpath, work_root=work_root)
    except Exception:
        candidate = Path(work_root) / rel_subpath
    return candidate if candidate.exists() and candidate.is_file() else None


def _read_bounded_header_o_rdonly(path: Path, max_bytes: int = P374_HEADER_READ_BYTES) -> bytes:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        return os.read(fd, max_bytes)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class Phase374DonorInspectionResult:
    verification_mode: str
    donor_tree_present: bool
    donors_checked: int
    donors_present: int
    bytes_read_total: int
    header_digests: Dict[str, str]
    raw_firmware_bytes_leaked: int
    elapsed_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def inspect_phase374_donors_bounded(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase374DonorInspectionResult:
    start = time.monotonic()
    forced = bool(force_clean_room) if force_clean_room is not None else _is_clean_room_env()
    resolved_work_root = (
        None if forced else (work_root if work_root is not None else _resolve_work_root_or_none())
    )

    if forced or (resolved_work_root is None and fx6_lib_dir is None and fx3_modules_dir is None):
        return Phase374DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            donors_checked=len(P374_BOUNDED_DONOR_PATHS),
            donors_present=0,
            bytes_read_total=0,
            header_digests={
                lbl: hashlib.sha256(f"clean_room_synthetic:{lbl}".encode("utf-8")).hexdigest()[:16]
                for lbl, _ in P374_BOUNDED_DONOR_PATHS
            },
            raw_firmware_bytes_leaked=PHASE374_RAW_FIRMWARE_BYTES_LEAKED,
            elapsed_seconds=round(time.monotonic() - start, 6),
        )

    digests: Dict[str, str] = {}
    present_count = 0
    bytes_read = 0
    fx3_override_names = {
        "fx3_appfw_so": "appFw.so",
        "fx3_cpapp_b_bin": "cpapp-b.bin",
        "fx3_libupdaterufp_so": "libupdaterufp.so",
        "fx3_libinfragetversion_so": "libInfraGetVersion.so",
        "fx3_libinfrafsys_so": "libInfraFsys.so",
        "fx3_libinframediacommon_so": "libInfraMediaCommon.so",
        "fx3_libmpr_so": "libmpr.so",
        "fx3_libsaveloadsettings_so": "libSaveLoadSettings.so",
    }
    for lbl, rel in P374_BOUNDED_DONOR_PATHS:
        if (time.monotonic() - start) >= max_seconds:
            break
        candidate: Optional[Path] = None
        if lbl == "fx6_appfw_so" and fx6_lib_dir is not None:
            p = Path(fx6_lib_dir) / "appFw.so"
            if p.exists() and p.is_file():
                candidate = p
        elif lbl in fx3_override_names and fx3_modules_dir is not None:
            p = Path(fx3_modules_dir) / fx3_override_names[lbl]
            if p.exists() and p.is_file():
                candidate = p
        if candidate is None:
            candidate = resolve_phase374_donor_file_or_none(resolved_work_root, rel)

        if candidate is not None:
            hdr = _read_bounded_header_o_rdonly(candidate, P374_HEADER_READ_BYTES)
            present_count += 1
            bytes_read += len(hdr)
            digests[lbl] = hashlib.sha256(hdr).hexdigest()[:16]
        else:
            digests[lbl] = hashlib.sha256(f"missing:{lbl}".encode("utf-8")).hexdigest()[:16]

    mode = "LOCAL_DONOR_O_RDONLY" if present_count > 0 else "CLEAN_ROOM_SYNTHETIC"
    return Phase374DonorInspectionResult(
        verification_mode=mode,
        donor_tree_present=present_count > 0,
        donors_checked=len(P374_BOUNDED_DONOR_PATHS),
        donors_present=present_count,
        bytes_read_total=bytes_read,
        header_digests=digests,
        raw_firmware_bytes_leaked=PHASE374_RAW_FIRMWARE_BYTES_LEAKED,
        elapsed_seconds=round(time.monotonic() - start, 6),
    )


# ---------------------------------------------------------------------------
# Simulated Dual-Media Tier-0 Receipt Helper (Dry-Run Only)
# ---------------------------------------------------------------------------


def build_simulated_phase374_tier0_receipts(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    body_serial: str = "FX3SIM70200374",
    emmc_cid: str = "11010030303847333000a1b2c3d49374",
) -> Dict[str, Any]:
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE374_TIER0:{hex(body_model_id)}:{body_fw}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE374_MANIFEST:{body_serial}:{body_fw}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    receipt_a_bytes = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    receipt_b_bytes = bytes(receipt_a_bytes)
    h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    h0_b = dict(h0_a)
    h3 = dict(h0_a)
    return {
        "receipt_a_bytes": receipt_a_bytes,
        "receipt_b_bytes": receipt_b_bytes,
        "st_dev_a": 0x1001,
        "st_dev_b": 0x2002,
        "body_serial": body_serial,
        "emmc_cid": emmc_cid,
        "h0_baselines_a": h0_a,
        "h0_baselines_b": h0_b,
        "h3_baselines": h3,
    }


def _extract_tier0_evidence(
    *,
    simulate_bench_dry_run: bool,
    receipt_a_bytes: Optional[bytes],
    receipt_b_bytes: Optional[bytes],
    receipt_a_path: Optional[Path],
    receipt_b_path: Optional[Path],
    st_dev_a_override: Optional[int],
    st_dev_b_override: Optional[int],
    body_serial: Optional[str],
    emmc_cid: Optional[str],
    h0_baselines_a: Optional[Mapping[str, str]],
    h0_baselines_b: Optional[Mapping[str, str]],
    h3_baselines: Optional[Mapping[str, str]],
    simulated_h0_h3_drifted_surfaces: int,
) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    raw_a = receipt_a_bytes
    raw_b = receipt_b_bytes
    st_dev_a = st_dev_a_override
    st_dev_b = st_dev_b_override

    if receipt_a_path is not None:
        if not receipt_a_path.exists() or not receipt_a_path.is_file():
            errors.append(
                f"{P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a path missing: {receipt_a_path}"
            )
        else:
            st_dev_a = st_dev_a if st_dev_a is not None else int(os.stat(receipt_a_path).st_dev)
            fd = os.open(str(receipt_a_path), os.O_RDONLY)
            try:
                raw_a = os.read(fd, SD_RECEIPT_BYTES + 64)
            finally:
                os.close(fd)

    if receipt_b_path is not None:
        if not receipt_b_path.exists() or not receipt_b_path.is_file():
            errors.append(
                f"{P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b path missing: {receipt_b_path}"
            )
        else:
            st_dev_b = st_dev_b if st_dev_b is not None else int(os.stat(receipt_b_path).st_dev)
            fd = os.open(str(receipt_b_path), os.O_RDONLY)
            try:
                raw_b = os.read(fd, SD_RECEIPT_BYTES + 64)
            finally:
                os.close(fd)

    if simulated_h0_h3_drifted_surfaces != 0:
        errors.append(
            f"{P374_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: simulated H0 != H3 drift ({simulated_h0_h3_drifted_surfaces} surfaces)"
        )

    if raw_a is None and raw_b is None:
        if simulate_bench_dry_run:
            sim = build_simulated_phase374_tier0_receipts(
                body_serial=body_serial or "FX3SIM70200374",
                emmc_cid=emmc_cid or "11010030303847333000a1b2c3d49374",
            )
            raw_a = sim["receipt_a_bytes"]
            raw_b = sim["receipt_b_bytes"]
            st_dev_a = st_dev_a if st_dev_a is not None else sim["st_dev_a"]
            st_dev_b = st_dev_b if st_dev_b is not None else sim["st_dev_b"]
            h0_baselines_a = h0_baselines_a or sim["h0_baselines_a"]
            h0_baselines_b = h0_baselines_b or sim["h0_baselines_b"]
            h3_baselines = h3_baselines or sim["h3_baselines"]
            body_serial = body_serial or sim["body_serial"]
            emmc_cid = emmc_cid or sim["emmc_cid"]
            receipt_mode = "DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH"
        else:
            warnings.append(
                "Offline preflight mode: dual-media 528 B FX3RCPT1 receipts not supplied; "
                "physical hardware attachment remains BLOCKED (`rc=2`)."
            )
            return {
                "tier0_receipt_verified": False,
                "receipt_mode": "AWAITING_PHYSICAL_RECEIPTS",
                "h0_equals_h3_count": 0,
                "st_dev_a": st_dev_a,
                "st_dev_b": st_dev_b,
                "body_serial": body_serial or "",
                "emmc_cid": emmc_cid or "",
                "errors": errors,
                "warnings": warnings,
            }
    else:
        receipt_mode = (
            "DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH"
            if simulate_bench_dry_run
            else "PHYSICAL_TIER0_DUAL_MEDIA_VERIFIED"
        )

    if raw_a is None or raw_b is None:
        errors.append(
            f"{P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: both Copy A and Copy B 528-byte FX3RCPT1 receipts are required"
        )
        return {
            "tier0_receipt_verified": False,
            "receipt_mode": "INVALID_OR_SINGLE_COPY",
            "h0_equals_h3_count": 0,
            "st_dev_a": st_dev_a,
            "st_dev_b": st_dev_b,
            "body_serial": body_serial or "",
            "emmc_cid": emmc_cid or "",
            "errors": errors,
            "warnings": warnings,
        }

    if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES:
        errors.append(
            f"{P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt size must be {SD_RECEIPT_BYTES} B (got A={len(raw_a)}, B={len(raw_b)})"
        )
        return {
            "tier0_receipt_verified": False,
            "receipt_mode": "INVALID_SIZE",
            "h0_equals_h3_count": 0,
            "st_dev_a": st_dev_a,
            "st_dev_b": st_dev_b,
            "body_serial": body_serial or "",
            "emmc_cid": emmc_cid or "",
            "errors": errors,
            "warnings": warnings,
        }

    if raw_a != raw_b:
        errors.append(
            f"{P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: Copy A and Copy B FX3RCPT1 payloads differ"
        )

    if st_dev_a is None or st_dev_b is None or st_dev_a == st_dev_b:
        errors.append(
            f"{P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: Copy A and Copy B must reside on distinct physical devices (st_dev_a={st_dev_a}, st_dev_b={st_dev_b})"
        )

    try:
        parsed_a = parse_sd_backup_receipt_bytes(raw_a)
        parsed_b = parse_sd_backup_receipt_bytes(raw_b)
    except Exception as exc:
        errors.append(
            f"{P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse failure: {exc}"
        )
        return {
            "tier0_receipt_verified": False,
            "receipt_mode": "CORRUPT_FX3RCPT1",
            "h0_equals_h3_count": 0,
            "st_dev_a": st_dev_a,
            "st_dev_b": st_dev_b,
            "body_serial": body_serial or "",
            "emmc_cid": emmc_cid or "",
            "errors": errors,
            "warnings": warnings,
        }

    if not getattr(parsed_a, "valid", False) or not getattr(parsed_b, "valid", False):
        errs_ab = list(getattr(parsed_a, "errors", ())) + list(getattr(parsed_b, "errors", ()))
        errors.append(
            f"{P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 integrity failure ({'; '.join(errs_ab)})"
        )
    if _is_trivial_hex64(str(getattr(parsed_a, "manifest_sha256", ""))) or _is_trivial_hex64(
        str(getattr(parsed_b, "manifest_sha256", ""))
    ):
        errors.append(
            f"{P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: trivial manifest_sha256 in FX3RCPT1"
        )
    if getattr(parsed_a, "entry_count", 0) != len(COLD_BACKUP_ITEMS) or getattr(
        parsed_b, "entry_count", 0
    ) != len(COLD_BACKUP_ITEMS):
        errors.append(
            f"{P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: cold backup item count mismatch ({getattr(parsed_a, 'entry_count', 0)} != {len(COLD_BACKUP_ITEMS)})"
        )

    eff_serial = body_serial if body_serial is not None else ""
    eff_cid = emmc_cid if emmc_cid is not None else ""
    if eff_serial:
        if (
            eff_serial.upper() in FORBIDDEN_TRIVIAL_SERIALS
            or len(set(eff_serial.upper())) == 1
            or not BODY_SERIAL_RE.match(eff_serial)
        ):
            errors.append(
                f"{P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/trivial body_serial {eff_serial!r}"
            )
    else:
        errors.append(
            f"{P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: non-trivial body_serial required for receipt binding"
        )

    if eff_cid:
        if eff_cid.lower() in FORBIDDEN_TRIVIAL_CIDS or not HEX32_CID_RE.match(eff_cid):
            errors.append(
                f"{P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/trivial emmc_cid {eff_cid!r}"
            )
    else:
        errors.append(
            f"{P374_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: non-trivial 32-hex emmc_cid required for receipt binding"
        )

    h0_match = 0
    if not errors and eff_serial and eff_cid:
        h0_a_map = (
            dict(h0_baselines_a)
            if h0_baselines_a is not None
            else build_default_h0_baselines(body_serial=eff_serial, emmc_cid=eff_cid)
        )
        h0_b_map = dict(h0_baselines_b) if h0_baselines_b is not None else dict(h0_a_map)
        h3_map = dict(h3_baselines) if h3_baselines is not None else dict(h0_a_map)
        if set(h0_a_map.keys()) != set(REQUIRED_H0_BASELINE_KEYS):
            errors.append(
                f"{P374_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: h0_baselines_a keys must match {len(REQUIRED_H0_BASELINE_KEYS)} REQUIRED_H0_BASELINE_KEYS"
            )
        elif set(h0_b_map.keys()) != set(REQUIRED_H0_BASELINE_KEYS):
            errors.append(
                f"{P374_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: h0_baselines_b keys must match {len(REQUIRED_H0_BASELINE_KEYS)} REQUIRED_H0_BASELINE_KEYS"
            )
        elif set(h3_map.keys()) != set(REQUIRED_H0_BASELINE_KEYS):
            errors.append(
                f"{P374_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: h3_baselines keys must match {len(REQUIRED_H0_BASELINE_KEYS)} REQUIRED_H0_BASELINE_KEYS"
            )
        elif len(SIXTEEN_STORAGE_SURFACES) != P374_STORAGE_SURFACE_COUNT:
            errors.append(
                f"{P374_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: expected 16 storage surfaces, got {len(SIXTEEN_STORAGE_SURFACES)}"
            )
        else:
            key_mismatches = sum(
                1
                for key in REQUIRED_H0_BASELINE_KEYS
                if _is_trivial_hex64(str(h0_a_map.get(key, "")))
                or _is_trivial_hex64(str(h3_map.get(key, "")))
                or str(h0_a_map.get(key, "")).lower() != str(h0_b_map.get(key, "")).lower()
                or str(h0_a_map.get(key, "")).lower() != str(h3_map.get(key, "")).lower()
            )
            surface_mismatches = sum(
                1
                for surf in SIXTEEN_STORAGE_SURFACES
                if h0_a_map.get(surf) != h0_b_map.get(surf) or h0_a_map.get(surf) != h3_map.get(surf)
            )
            drifted = max(0, int(simulated_h0_h3_drifted_surfaces), key_mismatches, surface_mismatches)
            if drifted > 0:
                errors.append(
                    f"{P374_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 != H3 or trivial digest detected ({drifted} drifted)"
                )
            h0_match = max(0, P374_STORAGE_SURFACE_COUNT - drifted)

    verified = (
        len(errors) == 0
        and h0_match == P374_STORAGE_SURFACE_COUNT
        and simulated_h0_h3_drifted_surfaces == 0
    )
    return {
        "tier0_receipt_verified": verified,
        "receipt_mode": receipt_mode if verified else "BLOCKED_INVALID_RECEIPT",
        "h0_equals_h3_count": h0_match if verified else 0,
        "st_dev_a": st_dev_a,
        "st_dev_b": st_dev_b,
        "body_serial": eff_serial,
        "emmc_cid": eff_cid,
        "errors": errors,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Result Dataclasses (Check Groups A-D & Top-Level Report)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class P374CheckGroupASilentModeTarget2DroAndFx6PaintLookResult:
    group_id: str
    passed: bool
    shoot_mode: str
    log_shooting_mode: str
    picture_profile: str
    hlg_still_image: str
    reset_action: str
    silent_mode: str
    effective_silent_mode_after_reset: str
    silent_target_items_exposed: Tuple[str, ...]
    silent_target_aperture_drive: str
    effective_silent_target_aperture_after_reset: str
    silent_target_auto_pixel_mapping: str
    effective_silent_target_auto_pixel_map_after_reset: str
    setup_auto_pixel_mapping: str
    effective_setup_auto_pixel_mapping_after_reset: str
    silent_mode_lockouts_enforced: Tuple[str, ...]
    shutdown_pixel_map_shutter_click_possible: bool
    dro_mode: str
    dro_locked_off_by_pp_log_or_hlg: bool
    effective_dro_mode: str
    effective_dro_after_reset: str
    dro_bracket_mode: str
    fx3_auto_hdr_supported: bool
    fx3_multi_frame_nr_supported: bool
    fx3_shutter_when_pwr_off_supported: bool
    fx6_shooting_mode: str
    fx6_paint_look_active: bool
    fx6_knee_point_pct: int
    fx6_knee_slope: int
    fx6_master_black: float
    fx6_black_gamma_ui_supported: bool
    fx6_white_clip_ui_supported: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P374CheckGroupBAudioSignalsFanCtrl4VersionAndFx6HoursMeterResult:
    group_id: str
    passed: bool
    reset_action: str
    audio_signals: str
    audio_signals_options_exposed: Tuple[str, ...]
    effective_audio_signals: str
    effective_audio_signals_after_reset: str
    fx3_fan_control: str
    fx3_fan_control_options_exposed: Tuple[str, ...]
    effective_fx3_fan_control_after_reset: str
    auto_power_off_temp: str
    effective_auto_power_off_temp_after_reset: str
    fx6_fan_control: str
    fx6_fan_control_options_exposed: Tuple[str, ...]
    fx6_alarm_level: int
    version_entities_exposed: Tuple[str, ...]
    body_update_filename: str
    lens_update_filename: str
    firmware_update_nogo_enforced: bool
    cert_logo_region: str
    cert_logo_visible: bool
    fx3_hours_meter_ui_exposed: bool
    fx6_hours_system: int
    fx6_hours_reset: int
    fx6_hours_meter_reset_action: str
    effective_fx6_hours_system: int
    effective_fx6_hours_reset: int
    slot1_sector_writes: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P374CheckGroupCAfIlluminatorAntiResetAf3Shutter2AndEfcsResult:
    group_id: str
    passed: bool
    shoot_mode: str
    focus_mode: str
    reset_action: str
    fx3_physical_af_illuminator_led_present: bool
    af_illuminator: str
    af_illuminator_distance_m: float
    af_illuminator_locked_out: bool
    af_illuminator_allowed_under_silent_mode: bool
    effective_af_illuminator_after_reset: str
    focus_af_triad_items: Tuple[str, ...]
    focus_aperture_drive_in_af: str
    effective_focus_aperture_drive_after_reset: str
    af_w_shutter: str
    effective_af_w_shutter_after_reset: str
    pre_af: str
    effective_pre_af_after_reset: str
    lens_pre_af_support: bool
    shutter_type: str
    shutter_type_options_exposed: Tuple[str, ...]
    effective_shutter_type_after_reset: str
    still_shutter_denom: int
    bulb_requested: bool
    fx3_shutter_type_auto_supported: bool
    e_front_curtain_shutter: str
    effective_efcs_after_reset: str
    efcs_bkid_typo_symbol: str
    efcs_bokeh_clipping_guidance_triggered: bool
    fx6_shutterless_ecs_architecture: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P374CheckGroupDFlash250ExtFlashNrFormatSlot1Erofs30Tier0Result:
    group_id: str
    passed: bool
    shoot_mode: str
    reset_action: str
    flash_mode: str
    flash_xsync_max_denom: int
    flash_firing_requested: bool
    flash_sync_shutter_denom: int
    flash_hss_enabled: bool
    flash_hss_banding_warning: bool
    flash_trigger_voltage_v: float
    fx3_pc_sync_terminal_present: bool
    exp_comp_set: str
    effective_exp_comp_set_after_reset: str
    external_flash_body_bkid_count: int
    external_flash_excluded_from_camset: bool
    fx3_reg_flash_shooting_set_supported: bool
    long_exposure_nr: str
    effective_long_exposure_nr_after_reset: str
    long_exposure_nr_locked_out: bool
    high_iso_nr: str
    high_iso_nr_options_exposed: Tuple[str, ...]
    high_iso_nr_mutates_arw_raw: bool
    fx6_noise_suppression_level: str
    format_mode: str
    format_target_slot: int
    format_media_bus: str
    quick_format_avf_info_path: str
    full_format_erase_symbol: str
    slot1_format_blocked_erofs30: bool
    slot1_contains_tier0_dump: bool
    slot1_wp_locked: bool
    slot1_sector_writes: int
    slot1_data_sector_writes: int
    slot1_tier0_vault_mutated: bool
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    st_dev_a: Optional[int]
    st_dev_b: Optional[int]
    receipt_body_serial: str
    receipt_emmc_cid: str
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Phase374ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealHwSilentModeDroFanCtrlHoursMeterAfIllumShutterFlashAndFormatReport:
    schema_version: str
    phase_version: str
    sony_help_guide_id: str
    overall_status: str
    go_no_go: str
    verification_mode: str
    simulate_bench_dry_run: bool
    check_group_count: int
    check_groups_passed: int
    check_group_a: P374CheckGroupASilentModeTarget2DroAndFx6PaintLookResult
    check_group_b: P374CheckGroupBAudioSignalsFanCtrl4VersionAndFx6HoursMeterResult
    check_group_c: P374CheckGroupCAfIlluminatorAntiResetAf3Shutter2AndEfcsResult
    check_group_d: P374CheckGroupDFlash250ExtFlashNrFormatSlot1Erofs30Tier0Result
    donor_inspection: Phase374DonorInspectionResult
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    slot1_tier0_vault_mutated: bool
    ready_for_live_camera_attach: bool
    overall_ready_for_hardware_attach: bool
    live_attach_authorized: bool
    hardware_live_attachment_authorized: bool
    emmc_writes_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    sd_physical_media_written: bool
    cross_model_flash_authorized: bool
    rf_nvs_p12_p13_writes_authorized: bool
    fx3_shutter_when_pwr_off_supported: bool
    fx3_auto_hdr_supported: bool
    fx3_shutter_type_auto_supported: bool
    fx3_reg_flash_shooting_set_supported: bool
    fx3_pc_sync_terminal_present: bool
    fx3_hours_meter_ui_exposed: bool
    lens_or_body_dat_update_authorized: bool
    emmc_write_count: int
    e_nd_actuator_tx_count: int
    e_nd_i2c_tx_bytes: int
    rf_tx_packets: int
    rf_packets_transmitted: int
    wireless_rf_packets_emitted: int
    rf_nvs_mutation_bytes: int
    slot1_sector_writes: int
    slot1_data_sector_writes: int
    usb_packets_transmitted: int
    passive_tx_bytes_emitted: int
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "phase_version": self.phase_version,
            "sony_help_guide_id": self.sony_help_guide_id,
            "overall_status": self.overall_status,
            "go_no_go": self.go_no_go,
            "verification_mode": self.verification_mode,
            "simulate_bench_dry_run": self.simulate_bench_dry_run,
            "check_group_count": self.check_group_count,
            "check_groups_passed": self.check_groups_passed,
            "check_group_a": self.check_group_a.to_dict(),
            "check_group_b": self.check_group_b.to_dict(),
            "check_group_c": self.check_group_c.to_dict(),
            "check_group_d": self.check_group_d.to_dict(),
            "donor_inspection": self.donor_inspection.to_dict(),
            "tier0_receipt_verified": self.tier0_receipt_verified,
            "receipt_mode": self.receipt_mode,
            "h0_equals_h3_count": self.h0_equals_h3_count,
            "h0_h3_surface_count": self.h0_h3_surface_count,
            "slot1_tier0_vault_mutated": self.slot1_tier0_vault_mutated,
            "ready_for_live_camera_attach": self.ready_for_live_camera_attach,
            "overall_ready_for_hardware_attach": self.overall_ready_for_hardware_attach,
            "live_attach_authorized": self.live_attach_authorized,
            "hardware_live_attachment_authorized": self.hardware_live_attachment_authorized,
            "emmc_writes_authorized": self.emmc_writes_authorized,
            "persistent_emmc_writes_authorized": self.persistent_emmc_writes_authorized,
            "persistent_write_release": self.persistent_write_release,
            "spi_nor_write_authorized": self.spi_nor_write_authorized,
            "el3_payload_transmit_authorized": self.el3_payload_transmit_authorized,
            "sd_physical_media_written": self.sd_physical_media_written,
            "cross_model_flash_authorized": self.cross_model_flash_authorized,
            "rf_nvs_p12_p13_writes_authorized": self.rf_nvs_p12_p13_writes_authorized,
            "fx3_shutter_when_pwr_off_supported": self.fx3_shutter_when_pwr_off_supported,
            "fx3_auto_hdr_supported": self.fx3_auto_hdr_supported,
            "fx3_shutter_type_auto_supported": self.fx3_shutter_type_auto_supported,
            "fx3_reg_flash_shooting_set_supported": self.fx3_reg_flash_shooting_set_supported,
            "fx3_pc_sync_terminal_present": self.fx3_pc_sync_terminal_present,
            "fx3_hours_meter_ui_exposed": self.fx3_hours_meter_ui_exposed,
            "lens_or_body_dat_update_authorized": self.lens_or_body_dat_update_authorized,
            "emmc_write_count": self.emmc_write_count,
            "e_nd_actuator_tx_count": self.e_nd_actuator_tx_count,
            "e_nd_i2c_tx_bytes": self.e_nd_i2c_tx_bytes,
            "rf_tx_packets": self.rf_tx_packets,
            "rf_packets_transmitted": self.rf_packets_transmitted,
            "wireless_rf_packets_emitted": self.wireless_rf_packets_emitted,
            "rf_nvs_mutation_bytes": self.rf_nvs_mutation_bytes,
            "slot1_sector_writes": self.slot1_sector_writes,
            "slot1_data_sector_writes": self.slot1_data_sector_writes,
            "usb_packets_transmitted": self.usb_packets_transmitted,
            "passive_tx_bytes_emitted": self.passive_tx_bytes_emitted,
            "raw_firmware_bytes_leaked": self.raw_firmware_bytes_leaked,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "report_sha256": self.report_sha256,
        }

    def to_deterministic_json(self, indent: int = 2) -> str:
        payload = _strip_timing_fields(self.to_dict())
        return json.dumps(payload, indent=indent, sort_keys=True, ensure_ascii=True) + "\n"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _parse_fw_tuple(fw: str) -> Optional[Tuple[int, int]]:
    parts = fw.strip().split(".")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return None
    return int(parts[0]), int(parts[1])


# ---------------------------------------------------------------------------
# Check Group A Evaluator (Wave 81.1-81.2: Silent Mode Target-2 & DRO vs Auto HDR)
# ---------------------------------------------------------------------------


def evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P374_SONY_HELP_GUIDE_ID,
    shoot_mode: str = "PHOTO",
    log_shooting_mode: str = "OFF",
    picture_profile: str = "PP11",
    hlg_still_image: str = "OFF",
    reset_action: str = "NONE",
    # Silent Mode & Exact 2-Item Target Function Settings
    silent_mode: str = "OFF",
    silent_target_items_exposed: Tuple[str, ...] = P374_SILENT_TARGET_EXACT_2_ITEMS,
    silent_target_aperture_drive: str = P374_SILENT_TARGET_APERTURE_DEFAULT,
    silent_target_auto_pixel_mapping: str = P374_SILENT_TARGET_AUTO_PIXEL_MAP_DEFAULT,
    setup_auto_pixel_mapping: str = "ON",
    dormant_silent_target_item_requested: Optional[str] = None,
    silent_mode_lockouts_enforced: Tuple[str, ...] = P374_SILENT_MODE_EXACT_5_LOCKOUTS,
    expect_silent_lockout_feature_active: bool = False,
    claimed_silent_mode_or_target2_resists_camera_reset: bool = False,
    claimed_setup_auto_pixel_mapping_wiped_by_camera_reset: bool = False,
    # D-Range Optimizer vs Dormant Auto HDR / Multi Frame NR
    dro_mode: str = "OFF",
    dro_bracket_mode: str = "NONE",
    expect_dro_active_under_pp11_log_or_hlg: bool = False,
    claimed_dro_resists_camera_reset: bool = False,
    dormant_auto_hdr_requested: bool = False,
    dormant_multi_frame_nr_requested: bool = False,
    claimed_fx3_has_auto_hdr_or_mfnr: bool = False,
    # FX6 Shutterless & Paint/Look Contrast
    claimed_fx6_has_mech_shutter_or_silent_mode: bool = False,
    fx6_shooting_mode: str = "CUSTOM",
    fx6_paint_look_active: bool = True,
    fx6_knee_point_pct: int = P374_FX6_KNEE_POINT_DEFAULT_PCT,
    fx6_knee_slope: int = P374_FX6_KNEE_SLOPE_DEFAULT,
    fx6_master_black: float = P374_FX6_BLACK_DEFAULT,
    dormant_fx6_paint_item_requested: Optional[str] = None,
    claimed_fx6_ui_has_black_gamma_or_white_clip: bool = False,
) -> P374CheckGroupASilentModeTarget2DroAndFx6PaintLookResult:
    errors: List[str] = []
    warnings: List[str] = []

    if body_model_id != TARGET_MODEL_ID_INT:
        errors.append(
            f"{P374_GA_ERR_MODEL_OR_FW_FLOOR}: expected {TARGET_MODEL_ID_HEX}, got 0x{body_model_id:08x}"
        )
    fw_t = _parse_fw_tuple(body_fw)
    if fw_t is None or fw_t < (7, 2):
        errors.append(
            f"{P374_GA_ERR_MODEL_OR_FW_FLOOR}: body_fw must be >= {TARGET_BODY_FW}, got {body_fw!r}"
        )
    if sony_help_guide_id != P374_SONY_HELP_GUIDE_ID:
        errors.append(
            f"{P374_GA_ERR_MODEL_OR_FW_FLOOR}: sony_help_guide_id must be {P374_SONY_HELP_GUIDE_ID}, got {sony_help_guide_id!r}"
        )
    if shoot_mode not in P374_VALID_SHOOT_MODES:
        errors.append(f"{P374_GA_ERR_MODEL_OR_FW_FLOOR}: invalid shoot_mode {shoot_mode!r}")
    if log_shooting_mode not in P374_VALID_LOG_SHOOTING_MODES:
        errors.append(
            f"{P374_GA_ERR_MODEL_OR_FW_FLOOR}: invalid log_shooting_mode {log_shooting_mode!r}"
        )
    if reset_action not in P374_VALID_RESET_ACTIONS:
        errors.append(f"{P374_GA_ERR_MODEL_OR_FW_FLOOR}: invalid reset_action {reset_action!r}")
    if hlg_still_image not in P374_VALID_ON_OFF:
        errors.append(f"{P374_GA_ERR_MODEL_OR_FW_FLOOR}: invalid hlg_still_image {hlg_still_image!r}")

    # Silent Mode 2-Item Target Function Settings
    if silent_mode not in P374_VALID_ON_OFF:
        errors.append(
            f"{P374_GA_ERR_SILENT_TARGET2_OR_DORMANT_BARRIER}: invalid silent_mode {silent_mode!r}"
        )
    if tuple(silent_target_items_exposed) != P374_SILENT_TARGET_EXACT_2_ITEMS:
        errors.append(
            f"{P374_GA_ERR_SILENT_TARGET2_OR_DORMANT_BARRIER}: [Target Function Settings] must expose exact 2 items {P374_SILENT_TARGET_EXACT_2_ITEMS}"
        )
    if silent_target_aperture_drive not in P374_SILENT_TARGET_APERTURE_MODES:
        errors.append(
            f"{P374_GA_ERR_SILENT_TARGET2_OR_DORMANT_BARRIER}: invalid silent_target_aperture_drive {silent_target_aperture_drive!r}"
        )
    if silent_target_auto_pixel_mapping not in P374_SILENT_TARGET_AUTO_PIXEL_MAP_MODES:
        errors.append(
            f"{P374_GA_ERR_SILENT_TARGET2_OR_DORMANT_BARRIER}: invalid silent_target_auto_pixel_mapping {silent_target_auto_pixel_mapping!r}"
        )
    if setup_auto_pixel_mapping not in P374_VALID_ON_OFF:
        errors.append(
            f"{P374_GA_ERR_SILENT_TARGET2_OR_DORMANT_BARRIER}: invalid setup_auto_pixel_mapping {setup_auto_pixel_mapping!r}"
        )
    if dormant_silent_target_item_requested is not None:
        errors.append(
            f"{P374_GA_ERR_SILENT_TARGET2_OR_DORMANT_BARRIER}: dormant item {dormant_silent_target_item_requested!r} (image_sensor_barrier / Anti-dust Function) blocked EOPNOTSUPP={P374_ERRNO_EOPNOTSUPP}"
        )

    # Reset Boundary & 5-Item Lockouts
    if tuple(silent_mode_lockouts_enforced) != P374_SILENT_MODE_EXACT_5_LOCKOUTS:
        errors.append(
            f"{P374_GA_ERR_SILENT_RESET_BOUNDARY_OR_5LOCKOUT}: Silent Mode must enforce exact 5 lockouts {P374_SILENT_MODE_EXACT_5_LOCKOUTS}"
        )
    if expect_silent_lockout_feature_active and silent_mode == "ON":
        errors.append(
            f"{P374_GA_ERR_SILENT_RESET_BOUNDARY_OR_5LOCKOUT}: Silent Mode=ON hard-disables Flash, Long Exposure NR, e-Front Curtain Shut., BULB, and Anti-flicker Shoot."
        )
    if claimed_silent_mode_or_target2_resists_camera_reset:
        errors.append(
            f"{P374_GA_ERR_SILENT_RESET_BOUNDARY_OR_5LOCKOUT}: ALL 3 Silent Mode items (Silent Mode + 2 Target Function items) are Can be reset under [Camera Settings Reset]"
        )
    if claimed_setup_auto_pixel_mapping_wiped_by_camera_reset:
        errors.append(
            f"{P374_GA_ERR_SILENT_RESET_BOUNDARY_OR_5LOCKOUT}: top-level Setup -> [Auto Pixel Mapping] resists [Camera Settings Reset] (Initialize-only)"
        )

    shutdown_click_possible = (
        silent_mode == "ON"
        and silent_target_auto_pixel_mapping == "NOT_TARGET"
        and setup_auto_pixel_mapping == "ON"
    )
    if shutdown_click_possible:
        warnings.append(
            "Silent Mode=ON with Target [Auto Pixel Mapping]=NOT_TARGET and Setup [Auto Pixel Mapping]=ON "
            "may emit a mechanical shutter click on power-off dark-frame mapping."
        )

    # D-Range Optimizer vs Dormant Auto HDR & Multi Frame NR
    if dro_mode not in P374_DRO_MODES:
        errors.append(
            f"{P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR}: invalid dro_mode {dro_mode!r}"
        )
    if dro_bracket_mode not in P374_DRO_BRACKET_MODES:
        errors.append(
            f"{P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR}: invalid dro_bracket_mode {dro_bracket_mode!r}"
        )
    dro_locked_off = (
        picture_profile != "OFF" or log_shooting_mode != "OFF" or hlg_still_image == "ON"
    )
    if dro_locked_off and (dro_mode != "OFF" or expect_dro_active_under_pp11_log_or_hlg):
        errors.append(
            f"{P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR}: [D-Range Optimizer] locked OFF when Picture Profile!=Off (stock PP11), Log Shooting!=Off, or HLG Still Image=On"
        )
    if dro_locked_off and dro_bracket_mode != "NONE":
        errors.append(
            f"{P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR}: [DRO Bracket] unavailable when Picture Profile!=Off, Log Shooting!=Off, or HLG Still Image=On"
        )
    if claimed_dro_resists_camera_reset:
        errors.append(
            f"{P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR}: [D-Range Optimizer] is Can be reset under [Camera Settings Reset]"
        )
    if dormant_auto_hdr_requested or dormant_multi_frame_nr_requested or claimed_fx3_has_auto_hdr_or_mfnr:
        errors.append(
            f"{P374_GA_ERR_DRO_LOCKOUT_OR_DORMANT_AUTOHDR_MFNR}: Auto HDR and Multi Frame NR have 0 ELF hits on FX3 (EOPNOTSUPP={P374_ERRNO_EOPNOTSUPP})"
        )

    # FX6 Shutterless & Paint/Look (Custom-only, zero UI Black Gamma / White Clip)
    if claimed_fx6_has_mech_shutter_or_silent_mode:
        errors.append(
            f"{P374_GA_ERR_FX6_SHUTTERLESS_OR_PAINT_LOOK_BOUNDARY}: ILME-FX6 is shutterless electronic rolling shutter + Auto Pixel Restore (zero mechanical focal-plane shutter / Silent Mode menu)"
        )
    if fx6_shooting_mode not in P374_FX6_SHOOTING_MODES:
        errors.append(
            f"{P374_GA_ERR_FX6_SHUTTERLESS_OR_PAINT_LOOK_BOUNDARY}: invalid fx6_shooting_mode {fx6_shooting_mode!r}"
        )
    if fx6_paint_look_active and fx6_shooting_mode != "CUSTOM":
        errors.append(
            f"{P374_GA_ERR_FX6_SHUTTERLESS_OR_PAINT_LOOK_BOUNDARY}: FX6 Paint/Look Black & Knee are active ONLY in Custom mode (locked out in {fx6_shooting_mode})"
        )
    if not (P374_FX6_KNEE_POINT_MIN_PCT <= fx6_knee_point_pct <= P374_FX6_KNEE_POINT_MAX_PCT):
        errors.append(
            f"{P374_GA_ERR_FX6_SHUTTERLESS_OR_PAINT_LOOK_BOUNDARY}: FX6 Knee Point must be 75..109%%, got {fx6_knee_point_pct}"
        )
    if not (P374_FX6_KNEE_SLOPE_MIN <= fx6_knee_slope <= P374_FX6_KNEE_SLOPE_MAX):
        errors.append(
            f"{P374_GA_ERR_FX6_SHUTTERLESS_OR_PAINT_LOOK_BOUNDARY}: FX6 Knee Slope must be -99..+99, got {fx6_knee_slope}"
        )
    if not (P374_FX6_BLACK_MIN <= fx6_master_black <= P374_FX6_BLACK_MAX):
        errors.append(
            f"{P374_GA_ERR_FX6_SHUTTERLESS_OR_PAINT_LOOK_BOUNDARY}: FX6 Master Black must be -99.0..+99.0, got {fx6_master_black}"
        )
    if dormant_fx6_paint_item_requested is not None or claimed_fx6_ui_has_black_gamma_or_white_clip:
        errors.append(
            f"{P374_GA_ERR_FX6_SHUTTERLESS_OR_PAINT_LOOK_BOUNDARY}: FX6 Paint/Look exposes zero UI Black Gamma or White Clip (dormant FX9/XDCAM residue, EOPNOTSUPP={P374_ERRNO_EOPNOTSUPP})"
        )

    eff_silent = (
        "OFF" if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE") else silent_mode
    )
    eff_target_ap = (
        P374_SILENT_TARGET_APERTURE_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else silent_target_aperture_drive
    )
    eff_target_pm = (
        P374_SILENT_TARGET_AUTO_PIXEL_MAP_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else silent_target_auto_pixel_mapping
    )
    eff_setup_pm = "ON" if reset_action == "INITIALIZE" else setup_auto_pixel_mapping
    eff_dro = "OFF" if dro_locked_off else dro_mode
    eff_dro_after_reset = (
        P374_DRO_DEFAULT_UNLOCKED
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else eff_dro
    )

    return P374CheckGroupASilentModeTarget2DroAndFx6PaintLookResult(
        group_id=P374_CHECK_GROUP_A_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        hlg_still_image=hlg_still_image,
        reset_action=reset_action,
        silent_mode=silent_mode,
        effective_silent_mode_after_reset=eff_silent,
        silent_target_items_exposed=tuple(silent_target_items_exposed),
        silent_target_aperture_drive=silent_target_aperture_drive,
        effective_silent_target_aperture_after_reset=eff_target_ap,
        silent_target_auto_pixel_mapping=silent_target_auto_pixel_mapping,
        effective_silent_target_auto_pixel_map_after_reset=eff_target_pm,
        setup_auto_pixel_mapping=setup_auto_pixel_mapping,
        effective_setup_auto_pixel_mapping_after_reset=eff_setup_pm,
        silent_mode_lockouts_enforced=tuple(silent_mode_lockouts_enforced),
        shutdown_pixel_map_shutter_click_possible=shutdown_click_possible,
        dro_mode=dro_mode,
        dro_locked_off_by_pp_log_or_hlg=dro_locked_off,
        effective_dro_mode=eff_dro,
        effective_dro_after_reset=eff_dro_after_reset,
        dro_bracket_mode=dro_bracket_mode,
        fx3_auto_hdr_supported=False,
        fx3_multi_frame_nr_supported=False,
        fx3_shutter_when_pwr_off_supported=False,
        fx6_shooting_mode=fx6_shooting_mode,
        fx6_paint_look_active=fx6_paint_look_active,
        fx6_knee_point_pct=fx6_knee_point_pct,
        fx6_knee_slope=fx6_knee_slope,
        fx6_master_black=fx6_master_black,
        fx6_black_gamma_ui_supported=False,
        fx6_white_clip_ui_supported=False,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group B Evaluator (Wave 81.3-81.4: Audio Signals, 4-Mode Fan, Version & FX6 Hours Meter)
# ---------------------------------------------------------------------------


def evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
    *,
    reset_action: str = "NONE",
    silent_mode: str = "OFF",
    # Audio Signals (Wave 81 G85 Erratum)
    audio_signals: str = P374_FX3_AUDIO_SIGNALS_DEFAULT,
    audio_signals_options_exposed: Tuple[str, ...] = P374_FX3_AUDIO_SIGNALS_EXACT_2_MODES,
    dormant_audio_signals_g85_mode_requested: Optional[str] = None,
    claimed_audio_signals_wiped_by_camera_reset: bool = False,
    expect_audio_signals_audible_under_silent_mode: bool = False,
    # Fan Control 4-vs-3 (Wave 81 G82 Erratum) + Auto Power OFF Temp + FX6 Alarm Level
    fx3_fan_control: str = P374_FX3_FAN_CONTROL_DEFAULT,
    fx3_fan_control_options_exposed: Tuple[str, ...] = P374_FX3_FAN_CONTROL_EXACT_4_MODES,
    dormant_fx3_fan_g82_mode_requested: Optional[str] = None,
    auto_power_off_temp: str = P374_AUTO_POWER_OFF_TEMP_DEFAULT,
    claimed_fan_or_autotemp_wiped_by_camera_reset: bool = False,
    sustained_bench_recording_under_always_off: bool = False,
    fx6_fan_control: str = "AUTO",
    fx6_fan_control_options_exposed: Tuple[str, ...] = P374_FX6_FAN_CONTROL_EXACT_3_MODES,
    dormant_fx6_fan_mode_requested: Optional[str] = None,
    claimed_fx6_fan_has_max_or_ui_always_off: bool = False,
    fx6_alarm_level: int = P374_FX6_ALARM_LEVEL_DEFAULT,
    # Version, BODYDATA.DAT / LENSDATA.DAT / UUD NO-GO, Certification Logo & FX6 Hours Meter
    version_entities_exposed: Tuple[str, ...] = P374_VERSION_EXACT_3_ENTITIES,
    body_update_filename: str = P374_BODY_UPDATE_FILENAME,
    lens_update_filename: str = P374_LENS_UPDATE_FILENAME,
    bodydata_dat_update_requested: bool = False,
    lensdata_dat_update_requested: bool = False,
    usb_uud_lens_update_requested: bool = False,
    fx6_slot_b_version_up_requested: bool = False,
    claimed_lens_update_safe_on_tier0_bench: bool = False,
    cert_logo_region: str = "US_EU_INTL",
    expect_cert_logo_visible_in_us_eu: bool = False,
    fx6_hours_system: int = 120,
    fx6_hours_reset: int = 15,
    fx6_hours_meter_reset_action: str = "NONE",
    claimed_fx6_hours_system_resettable: bool = False,
    claimed_fx6_hours_saved_in_all_file: bool = False,
    claimed_fx3_exposes_hours_meter_ui: bool = False,
    slot1_sector_writes: int = 0,
) -> P374CheckGroupBAudioSignalsFanCtrl4VersionAndFx6HoursMeterResult:
    errors: List[str] = []
    warnings: List[str] = []

    # Audio Signals (Wave 81 G85 Erratum: strictly On / Off only, anti-Camera-Reset)
    if tuple(audio_signals_options_exposed) != P374_FX3_AUDIO_SIGNALS_EXACT_2_MODES:
        errors.append(
            f"{P374_GB_ERR_AUDIO_SIGNALS_2OPT_OR_G85_ERRATUM}: FX3 [Audio signals] exposes ONLY {P374_FX3_AUDIO_SIGNALS_EXACT_2_MODES} (Wave 81 G85 erratum)"
        )
    if audio_signals not in P374_FX3_AUDIO_SIGNALS_EXACT_2_MODES:
        errors.append(
            f"{P374_GB_ERR_AUDIO_SIGNALS_2OPT_OR_G85_ERRATUM}: invalid audio_signals {audio_signals!r}; only ON/OFF exist on FX3"
        )
    if dormant_audio_signals_g85_mode_requested is not None:
        errors.append(
            f"{P374_GB_ERR_AUDIO_SIGNALS_2OPT_OR_G85_ERRATUM}: dormant G85 Audio signals option {dormant_audio_signals_g85_mode_requested!r} rejected (EOPNOTSUPP={P374_ERRNO_EOPNOTSUPP})"
        )
    if claimed_audio_signals_wiped_by_camera_reset:
        errors.append(
            f"{P374_GB_ERR_AUDIO_SIGNALS_2OPT_OR_G85_ERRATUM}: [Audio signals] resists [Camera Settings Reset] (Initialize-only)"
        )
    if silent_mode == "ON" and expect_audio_signals_audible_under_silent_mode:
        errors.append(
            f"{P374_GB_ERR_AUDIO_SIGNALS_2OPT_OR_G85_ERRATUM}: [Silent Mode]=On forces [Audio signals] muted (OFF)"
        )

    # Fan Control 4 modes on FX3 (Wave 81 G82 erratum: zero Auto1/Auto2) vs 3 modes on FX6
    if tuple(fx3_fan_control_options_exposed) != P374_FX3_FAN_CONTROL_EXACT_4_MODES:
        errors.append(
            f"{P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM}: FX3 [Fan Control] exposes EXACTLY 4 modes {P374_FX3_FAN_CONTROL_EXACT_4_MODES} (Wave 81 G82 erratum: zero Auto1/Auto2)"
        )
    if fx3_fan_control not in P374_FX3_FAN_CONTROL_EXACT_4_MODES:
        errors.append(
            f"{P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM}: invalid fx3_fan_control {fx3_fan_control!r}"
        )
    if dormant_fx3_fan_g82_mode_requested is not None:
        errors.append(
            f"{P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM}: dormant FX3 Fan Control mode {dormant_fx3_fan_g82_mode_requested!r} rejected (zero Auto1/Auto2/Max, EINVAL={P374_ERRNO_EINVAL})"
        )
    if auto_power_off_temp not in P374_AUTO_POWER_OFF_TEMP_MODES:
        errors.append(
            f"{P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM}: invalid auto_power_off_temp {auto_power_off_temp!r}"
        )
    if claimed_fan_or_autotemp_wiped_by_camera_reset:
        errors.append(
            f"{P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM}: [Fan Control] and [Auto Power OFF Temp.] resist [Camera Settings Reset]"
        )
    if fx3_fan_control == "ALWAYS_OFF" and sustained_bench_recording_under_always_off:
        errors.append(
            f"{P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM}: sustained bench recording under Fan Control=ALWAYS_OFF blocked for thermal protection"
        )
    if tuple(fx6_fan_control_options_exposed) != P374_FX6_FAN_CONTROL_EXACT_3_MODES:
        errors.append(
            f"{P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM}: FX6 Technical > Fan Control exposes EXACTLY 3 modes {P374_FX6_FAN_CONTROL_EXACT_3_MODES} (zero Max, zero UI Always Off)"
        )
    if fx6_fan_control not in P374_FX6_FAN_CONTROL_EXACT_3_MODES:
        errors.append(
            f"{P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM}: invalid fx6_fan_control {fx6_fan_control!r}"
        )
    if dormant_fx6_fan_mode_requested is not None or claimed_fx6_fan_has_max_or_ui_always_off:
        errors.append(
            f"{P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM}: FX6 Technical > Fan Control forbids Max and UI Always Off (EOPNOTSUPP={P374_ERRNO_EOPNOTSUPP})"
        )
    if not (P374_FX6_ALARM_LEVEL_MIN <= fx6_alarm_level <= P374_FX6_ALARM_LEVEL_MAX):
        errors.append(
            f"{P374_GB_ERR_FAN_CONTROL_4VS3_OR_G82_ERRATUM}: FX6 Alarm Level must be 0..7, got {fx6_alarm_level}"
        )

    # Version, /BODYDATA.DAT, LENSDATA.DAT & USB UUD NO-GO / BLOCKED (Slot 1 EROFS=30)
    if tuple(version_entities_exposed) != P374_VERSION_EXACT_3_ENTITIES:
        errors.append(
            f"{P374_GB_ERR_VERSION_UPDATE_NOGO_SLOT1_EROFS30}: [Version] must expose {P374_VERSION_EXACT_3_ENTITIES}"
        )
    if body_update_filename != P374_BODY_UPDATE_FILENAME or lens_update_filename != P374_LENS_UPDATE_FILENAME:
        errors.append(
            f"{P374_GB_ERR_VERSION_UPDATE_NOGO_SLOT1_EROFS30}: libupdaterufp.so update filenames must be {P374_BODY_UPDATE_FILENAME} and {P374_LENS_UPDATE_FILENAME}"
        )
    if (
        bodydata_dat_update_requested
        or lensdata_dat_update_requested
        or usb_uud_lens_update_requested
        or fx6_slot_b_version_up_requested
        or claimed_lens_update_safe_on_tier0_bench
    ):
        errors.append(
            f"{P374_GB_ERR_VERSION_UPDATE_NOGO_SLOT1_EROFS30}: /BODYDATA.DAT, LENSDATA.DAT, USB UUD lens update, and FX6 Slot B Version Up are strictly NO-GO / BLOCKED (Slot 1 EROFS={P374_ERRNO_EROFS}, EPERM={P374_ERRNO_EPERM})"
        )
    if slot1_sector_writes != 0:
        errors.append(
            f"{P374_GB_ERR_VERSION_UPDATE_NOGO_SLOT1_EROFS30}: Slot 1 sector writes must remain 0 (EROFS={P374_ERRNO_EROFS})"
        )

    # Certification Logo Region Gate & FX6 Maintenance > Hours Meter
    if cert_logo_region not in P374_CERT_LOGO_REGIONS:
        errors.append(
            f"{P374_GB_ERR_CERT_LOGO_REGION_OR_FX6_HOURS_METER}: invalid cert_logo_region {cert_logo_region!r}"
        )
    cert_logo_visible = cert_logo_region == "JP_DOMESTIC"
    if not cert_logo_visible and expect_cert_logo_visible_in_us_eu:
        errors.append(
            f"{P374_GB_ERR_CERT_LOGO_REGION_OR_FX6_HOURS_METER}: [Certification Logo] is region-gated (hidden in US/EU SKU; visible on JP domestic SKU via certification_logo_radio_act_id)"
        )
    if fx6_hours_meter_reset_action not in P374_FX6_HOURS_RESET_ACTIONS:
        errors.append(
            f"{P374_GB_ERR_CERT_LOGO_REGION_OR_FX6_HOURS_METER}: invalid fx6_hours_meter_reset_action {fx6_hours_meter_reset_action!r}"
        )
    if fx6_hours_system < 0 or fx6_hours_reset < 0 or fx6_hours_reset > fx6_hours_system:
        errors.append(
            f"{P374_GB_ERR_CERT_LOGO_REGION_OR_FX6_HOURS_METER}: invalid FX6 Hours Meter counters (system={fx6_hours_system}, reset={fx6_hours_reset})"
        )
    if claimed_fx6_hours_system_resettable:
        errors.append(
            f"{P374_GB_ERR_CERT_LOGO_REGION_OR_FX6_HOURS_METER}: FX6 Hours(System) is permanently non-resettable (survives Hours Meter > Reset and Maintenance > All Reset)"
        )
    if claimed_fx6_hours_saved_in_all_file:
        errors.append(
            f"{P374_GB_ERR_CERT_LOGO_REGION_OR_FX6_HOURS_METER}: FX6 Hours Meter counters are never written to or loaded from Setup/ALL files"
        )
    if claimed_fx3_exposes_hours_meter_ui:
        errors.append(
            f"{P374_GB_ERR_CERT_LOGO_REGION_OR_FX6_HOURS_METER}: FX3 has zero UI Hours Meter exposure (cpapp-b.bin FRONT_CP_HOURS_METER is non-UI, EOPNOTSUPP={P374_ERRNO_EOPNOTSUPP})"
        )

    eff_audio_now = "OFF" if silent_mode == "ON" else audio_signals
    eff_audio_reset = (
        P374_FX3_AUDIO_SIGNALS_DEFAULT if reset_action == "INITIALIZE" else audio_signals
    )
    eff_fan_reset = (
        P374_FX3_FAN_CONTROL_DEFAULT if reset_action == "INITIALIZE" else fx3_fan_control
    )
    eff_temp_reset = (
        P374_AUTO_POWER_OFF_TEMP_DEFAULT if reset_action == "INITIALIZE" else auto_power_off_temp
    )
    eff_fx6_hours_system = fx6_hours_system
    eff_fx6_hours_reset = (
        0 if fx6_hours_meter_reset_action == "HOURS_METER_RESET" else fx6_hours_reset
    )

    return P374CheckGroupBAudioSignalsFanCtrl4VersionAndFx6HoursMeterResult(
        group_id=P374_CHECK_GROUP_B_ID,
        passed=len(errors) == 0,
        reset_action=reset_action,
        audio_signals=audio_signals,
        audio_signals_options_exposed=tuple(audio_signals_options_exposed),
        effective_audio_signals=eff_audio_now,
        effective_audio_signals_after_reset=eff_audio_reset,
        fx3_fan_control=fx3_fan_control,
        fx3_fan_control_options_exposed=tuple(fx3_fan_control_options_exposed),
        effective_fx3_fan_control_after_reset=eff_fan_reset,
        auto_power_off_temp=auto_power_off_temp,
        effective_auto_power_off_temp_after_reset=eff_temp_reset,
        fx6_fan_control=fx6_fan_control,
        fx6_fan_control_options_exposed=tuple(fx6_fan_control_options_exposed),
        fx6_alarm_level=fx6_alarm_level,
        version_entities_exposed=tuple(version_entities_exposed),
        body_update_filename=body_update_filename,
        lens_update_filename=lens_update_filename,
        firmware_update_nogo_enforced=True,
        cert_logo_region=cert_logo_region,
        cert_logo_visible=cert_logo_visible,
        fx3_hours_meter_ui_exposed=False,
        fx6_hours_system=fx6_hours_system,
        fx6_hours_reset=fx6_hours_reset,
        fx6_hours_meter_reset_action=fx6_hours_meter_reset_action,
        effective_fx6_hours_system=eff_fx6_hours_system,
        effective_fx6_hours_reset=eff_fx6_hours_reset,
        slot1_sector_writes=PHASE374_SLOT1_SECTOR_WRITES,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group C Evaluator (Wave 82.1-82.2: AF Illuminator, 3 Anti-Reset AF, Shutter Type & EFCS)
# ---------------------------------------------------------------------------


def evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
    *,
    shoot_mode: str = "PHOTO",
    focus_mode: str = "AF_S",
    reset_action: str = "NONE",
    silent_mode: str = "OFF",
    # Physical AF Illuminator LED (0.3-3.0 m, Still-only, NOT disabled by Silent Mode)
    af_illuminator: str = P374_AF_ILLUMINATOR_DEFAULT,
    af_illuminator_distance_m: float = 1.5,
    af_a_subject_moving: bool = False,
    focus_magnifier_active: bool = False,
    mount_adaptor_attached: bool = False,
    expect_af_illuminator_fires_under_lockout: bool = False,
    claimed_fx3_lacks_physical_af_illuminator_led: bool = False,
    claimed_silent_mode_disables_af_illuminator: bool = False,
    claimed_af_illuminator_resists_camera_reset: bool = False,
    # Still-only Focus -> [AF/MF] Anti-Reset Triad
    focus_af_triad_items: Tuple[str, ...] = P374_AF_FOCUS_TRIAD_ANTIRESET_ITEMS,
    focus_aperture_drive_in_af: str = P374_FOCUS_APERTURE_DRIVE_DEFAULT,
    af_w_shutter: str = "ON",
    pre_af: str = "OFF",
    lens_pre_af_support: bool = True,
    claimed_focus_af_triad_wiped_by_camera_reset: bool = False,
    expect_focus_af_triad_active_in_movie_or_sq: bool = False,
    claimed_fx6_has_af_illuminator_or_half_press_af: bool = False,
    # 2-Option [Shutter Type] (ZERO Auto) & Anti-Reset [e-Front Curtain Shut.]
    shutter_type: str = P374_SHUTTER_TYPE_DEFAULT,
    shutter_type_options_exposed: Tuple[str, ...] = P374_SHUTTER_TYPE_EXACT_2_OPTIONS,
    dormant_shutter_type_auto_requested: bool = False,
    still_shutter_denom: int = 250,
    bulb_requested: bool = False,
    claimed_shutter_type_resists_camera_reset: bool = False,
    expect_movie_uses_still_shutter_type: bool = False,
    e_front_curtain_shutter: str = "ON",
    efcs_bkid_typo_symbol: str = P374_EFCS_BKID_TYPO,
    aperture_f_number: float = 2.8,
    third_party_lens_attached: bool = False,
    claimed_efcs_wiped_by_camera_reset: bool = False,
    expect_efcs_active_under_eshutter_or_silent: bool = False,
    expect_no_bokeh_clipping_with_efcs_high_speed: bool = False,
    claimed_fx6_has_mechanical_shutter_or_efcs: bool = False,
) -> P374CheckGroupCAfIlluminatorAntiResetAf3Shutter2AndEfcsResult:
    errors: List[str] = []
    warnings: List[str] = []

    if shoot_mode not in P374_VALID_SHOOT_MODES:
        errors.append(
            f"{P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT}: invalid shoot_mode {shoot_mode!r}"
        )
    if focus_mode not in P374_VALID_FOCUS_MODES:
        errors.append(
            f"{P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT}: invalid focus_mode {focus_mode!r}"
        )

    # Physical AF Illuminator LED
    if af_illuminator not in P374_AF_ILLUMINATOR_MODES:
        errors.append(
            f"{P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT}: invalid af_illuminator {af_illuminator!r}"
        )
    if not (P374_AF_ILLUMINATOR_RANGE_MIN_M <= af_illuminator_distance_m <= P374_AF_ILLUMINATOR_RANGE_MAX_M):
        errors.append(
            f"{P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT}: AF Illuminator effective range is 0.3..3.0 m, got {af_illuminator_distance_m} m"
        )
    if claimed_fx3_lacks_physical_af_illuminator_led:
        errors.append(
            f"{P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT}: ILME-FX3 has a physical front-panel AF Illuminator LED (0.3-3.0 m)"
        )
    if claimed_silent_mode_disables_af_illuminator:
        errors.append(
            f"{P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT}: [Silent Mode]=On does NOT disable [AF Illuminator] (must manually set Off for dark stealth shooting)"
        )
    if claimed_af_illuminator_resists_camera_reset:
        errors.append(
            f"{P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT}: [AF Illuminator] is Can be reset under [Camera Settings Reset]"
        )

    af_illum_locked_out = (
        shoot_mode != "PHOTO"
        or focus_mode == "AF_C"
        or (focus_mode == "AF_A" and af_a_subject_moving)
        or focus_magnifier_active
        or mount_adaptor_attached
    )
    if expect_af_illuminator_fires_under_lockout and af_illum_locked_out:
        errors.append(
            f"{P374_GC_ERR_AF_ILLUMINATOR_HARDWARE_OR_LOCKOUT}: [AF Illuminator] is disabled in Movie/S&Q, AF-C, moving AF-A, Focus Magnifier, or Mount Adaptor"
        )

    # Still-only Focus -> [AF/MF] Anti-Reset Triad
    if tuple(focus_af_triad_items) != P374_AF_FOCUS_TRIAD_ANTIRESET_ITEMS:
        errors.append(
            f"{P374_GC_ERR_AF_TRIAD_ANTIRESET_OR_STILL_ONLY}: Focus -> [AF/MF] anti-reset triad must be {P374_AF_FOCUS_TRIAD_ANTIRESET_ITEMS}"
        )
    if focus_aperture_drive_in_af not in P374_FOCUS_APERTURE_DRIVE_MODES:
        errors.append(
            f"{P374_GC_ERR_AF_TRIAD_ANTIRESET_OR_STILL_ONLY}: invalid focus_aperture_drive_in_af {focus_aperture_drive_in_af!r}"
        )
    if af_w_shutter not in P374_VALID_ON_OFF or pre_af not in P374_VALID_ON_OFF:
        errors.append(
            f"{P374_GC_ERR_AF_TRIAD_ANTIRESET_OR_STILL_ONLY}: af_w_shutter and pre_af must be ON/OFF"
        )
    if pre_af == "ON" and not lens_pre_af_support:
        errors.append(
            f"{P374_GC_ERR_AF_TRIAD_ANTIRESET_OR_STILL_ONLY}: [Pre-AF]=ON requires native E-mount lens with LENS_PRE_AF_SUPPORT"
        )
    if claimed_focus_af_triad_wiped_by_camera_reset:
        errors.append(
            f"{P374_GC_ERR_AF_TRIAD_ANTIRESET_OR_STILL_ONLY}: ALL 3 Focus -> [AF/MF] items (Aperture Drive in AF, AF w/ Shutter, Pre-AF) resist [Camera Settings Reset] (Initialize-only)"
        )
    if expect_focus_af_triad_active_in_movie_or_sq and shoot_mode != "PHOTO":
        errors.append(
            f"{P374_GC_ERR_AF_TRIAD_ANTIRESET_OR_STILL_ONLY}: Focus -> [AF/MF] triad (Aperture Drive in AF, AF w/ Shutter, Pre-AF) is strictly Still-only"
        )
    if claimed_fx6_has_af_illuminator_or_half_press_af:
        errors.append(
            f"{P374_GC_ERR_AF_TRIAD_ANTIRESET_OR_STILL_ONLY}: FX6 has zero AF Illuminator and zero half-press AF (uses Push AF Mode / Push AF/Push MF)"
        )

    # 2-Option [Shutter Type] (ZERO Auto, 1/8000 s max both, BULB mech-only)
    if tuple(shutter_type_options_exposed) != P374_SHUTTER_TYPE_EXACT_2_OPTIONS:
        errors.append(
            f"{P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB}: FX3 [Shutter Type] exposes EXACTLY 2 options {P374_SHUTTER_TYPE_EXACT_2_OPTIONS} (ZERO Auto)"
        )
    if shutter_type not in P374_SHUTTER_TYPE_EXACT_2_OPTIONS:
        errors.append(
            f"{P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB}: invalid shutter_type {shutter_type!r}"
        )
    if dormant_shutter_type_auto_requested:
        errors.append(
            f"{P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB}: dormant [Shutter Type]=Auto rejected (EOPNOTSUPP={P374_ERRNO_EOPNOTSUPP})"
        )
    if claimed_shutter_type_resists_camera_reset:
        errors.append(
            f"{P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB}: [Shutter Type] is Can be reset under [Camera Settings Reset] (resets to Mechanical Shutter)"
        )
    if not (1 <= still_shutter_denom <= P374_STILL_MAX_SHUTTER_DENOM):
        errors.append(
            f"{P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB}: Still shutter speed denominator must be 1..{P374_STILL_MAX_SHUTTER_DENOM} (1/8000 s max), got {still_shutter_denom}"
        )
    if bulb_requested and (
        shoot_mode != "PHOTO" or shutter_type == "ELECTRONIC_SHUTTER" or silent_mode == "ON"
    ):
        errors.append(
            f"{P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB}: BULB exposure is strictly Mechanical Shutter in Still mode (locked out in Electronic Shutter / Silent Mode / Movie)"
        )
    if expect_movie_uses_still_shutter_type:
        errors.append(
            f"{P374_GC_ERR_SHUTTER_TYPE_2OPT_NO_AUTO_OR_BULB}: Movie/S&Q always uses sensor electronic rolling readout and ignores Still [Shutter Type]"
        )

    # Anti-Reset [e-Front Curtain Shut.] & Bokeh-Clipping / 3rd-Party Lens Guidance
    if e_front_curtain_shutter not in P374_VALID_ON_OFF:
        errors.append(
            f"{P374_GC_ERR_EFCS_ANTIRESET_BOKEH_OR_FX6_SHUTTERLESS}: invalid e_front_curtain_shutter {e_front_curtain_shutter!r}"
        )
    if efcs_bkid_typo_symbol != P374_EFCS_BKID_TYPO:
        errors.append(
            f"{P374_GC_ERR_EFCS_ANTIRESET_BOKEH_OR_FX6_SHUTTERLESS}: Sony ELF EFCS BKID symbol must match {P374_EFCS_BKID_TYPO!r}"
        )
    if claimed_efcs_wiped_by_camera_reset:
        errors.append(
            f"{P374_GC_ERR_EFCS_ANTIRESET_BOKEH_OR_FX6_SHUTTERLESS}: [e-Front Curtain Shut.] resists [Camera Settings Reset] (Not available; Initialize-only)"
        )
    if expect_efcs_active_under_eshutter_or_silent and (
        shutter_type == "ELECTRONIC_SHUTTER" or silent_mode == "ON"
    ):
        errors.append(
            f"{P374_GC_ERR_EFCS_ANTIRESET_BOKEH_OR_FX6_SHUTTERLESS}: [e-Front Curtain Shut.] is disabled in Electronic Shutter and Silent Mode=On"
        )
    bokeh_guidance = e_front_curtain_shutter == "ON" and (
        (still_shutter_denom > P374_EFCS_BOKEH_GUIDANCE_THRESHOLD_DENOM and aperture_f_number <= 2.0)
        or third_party_lens_attached
    )
    if bokeh_guidance:
        warnings.append(
            "EFCS=ON at high shutter speed (>1/1000 s) with wide aperture (<=F2.0) or 3rd-party lens: "
            "set [e-Front Curtain Shut.]=OFF to prevent bokeh circle clipping or uneven exposure."
        )
    if expect_no_bokeh_clipping_with_efcs_high_speed and bokeh_guidance:
        errors.append(
            f"{P374_GC_ERR_EFCS_ANTIRESET_BOKEH_OR_FX6_SHUTTERLESS}: EFCS=ON at high shutter speed with wide aperture / 3rd-party lens risks bokeh clipping (disable EFCS)"
        )
    if claimed_fx6_has_mechanical_shutter_or_efcs:
        errors.append(
            f"{P374_GC_ERR_EFCS_ANTIRESET_BOKEH_OR_FX6_SHUTTERLESS}: ILME-FX6 is shutterless electronic rolling shutter + ECS (zero mechanical shutter / EFCS)"
        )

    eff_af_illum = (
        P374_AF_ILLUMINATOR_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else af_illuminator
    )
    eff_focus_ap = (
        P374_FOCUS_APERTURE_DRIVE_DEFAULT
        if reset_action == "INITIALIZE"
        else focus_aperture_drive_in_af
    )
    eff_af_shutter = "ON" if reset_action == "INITIALIZE" else af_w_shutter
    eff_pre_af = "OFF" if reset_action == "INITIALIZE" else pre_af
    eff_shutter_type = (
        P374_SHUTTER_TYPE_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else shutter_type
    )
    eff_efcs = "ON" if reset_action == "INITIALIZE" else e_front_curtain_shutter

    return P374CheckGroupCAfIlluminatorAntiResetAf3Shutter2AndEfcsResult(
        group_id=P374_CHECK_GROUP_C_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        focus_mode=focus_mode,
        reset_action=reset_action,
        fx3_physical_af_illuminator_led_present=True,
        af_illuminator=af_illuminator,
        af_illuminator_distance_m=af_illuminator_distance_m,
        af_illuminator_locked_out=af_illum_locked_out,
        af_illuminator_allowed_under_silent_mode=True,
        effective_af_illuminator_after_reset=eff_af_illum,
        focus_af_triad_items=tuple(focus_af_triad_items),
        focus_aperture_drive_in_af=focus_aperture_drive_in_af,
        effective_focus_aperture_drive_after_reset=eff_focus_ap,
        af_w_shutter=af_w_shutter,
        effective_af_w_shutter_after_reset=eff_af_shutter,
        pre_af=pre_af,
        effective_pre_af_after_reset=eff_pre_af,
        lens_pre_af_support=lens_pre_af_support,
        shutter_type=shutter_type,
        shutter_type_options_exposed=tuple(shutter_type_options_exposed),
        effective_shutter_type_after_reset=eff_shutter_type,
        still_shutter_denom=still_shutter_denom,
        bulb_requested=bulb_requested,
        fx3_shutter_type_auto_supported=False,
        e_front_curtain_shutter=e_front_curtain_shutter,
        effective_efcs_after_reset=eff_efcs,
        efcs_bkid_typo_symbol=efcs_bkid_typo_symbol,
        efcs_bokeh_clipping_guidance_triggered=bokeh_guidance,
        fx6_shutterless_ecs_architecture=True,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group D Evaluator (Wave 82.3-82.4: Flash 1/250 s, NR, Quick/Full Format & Tier-0)
# ---------------------------------------------------------------------------


def evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
    *,
    simulate_bench_dry_run: bool = False,
    shoot_mode: str = "PHOTO",
    reset_action: str = "NONE",
    silent_mode: str = "OFF",
    shutter_type: str = P374_SHUTTER_TYPE_DEFAULT,
    still_drive_mode: str = "SINGLE_SHOOTING",
    # MI Shoe Flash (Wave 82 G156 Erratum)
    flash_mode: str = "AUTOFLASH",
    flash_xsync_max_denom: int = P374_FX3_FLASH_XSYNC_MAX_DENOM,
    flash_firing_requested: bool = False,
    flash_sync_shutter_denom: int = 250,
    flash_hss_enabled: bool = False,
    flash_trigger_voltage_v: float = 5.0,
    flash_negative_polarity: bool = False,
    claimed_flash_xsync_320_apsc_or_160_200_efcs_g156: bool = False,
    claimed_fx3_has_pc_sync_terminal: bool = False,
    exp_comp_set: str = P374_FX3_EXP_COMP_SET_DEFAULT,
    claimed_exp_comp_set_wiped_by_camera_reset: bool = False,
    external_flash_body_bkid_count: int = P374_FX3_EXTERNAL_FLASH_BODY_BKID_COUNT,
    claimed_external_flash_saved_in_camset_or_resettable: bool = False,
    dormant_reg_flash_shooting_set_requested: bool = False,
    claimed_fx6_has_flash_sync_or_fbr_is_sync: bool = False,
    # Long Exposure NR & High ISO NR vs FX6 Noise Suppression
    long_exposure_nr: str = "ON",
    expect_long_exp_nr_active_under_lockout: bool = False,
    claimed_long_exp_nr_resists_camera_reset: bool = False,
    high_iso_nr: str = P374_FX3_HIGH_ISO_NR_DEFAULT,
    high_iso_nr_options_exposed: Tuple[str, ...] = P374_FX3_HIGH_ISO_NR_EXACT_3_LEVELS,
    dormant_high_iso_nr_high_requested: bool = False,
    claimed_high_iso_nr_mutates_arw_raw: bool = False,
    fx6_noise_suppression_level: str = "MID",
    # Format Quick vs Full & Slot 1 EROFS=30 Firewall
    format_mode: str = "NONE",
    format_target_slot: int = 2,
    format_media_bus: str = "CFEXPRESS_TYPE_A_NVME",
    quick_format_avf_info_path: str = P374_QUICK_FORMAT_AVF_INFO_PATH,
    full_format_erase_symbol: str = P374_FULL_FORMAT_ERASE_SYMBOL,
    format_hotkey_menu_delete_2s_slot: Optional[int] = None,
    avf_info_rebuild_slot1_requested: bool = False,
    full_format_discard_trim_slot1_requested: bool = False,
    claimed_full_format_cancel_restores_erased_data: bool = False,
    # Tier-0 Vault & Zero-Telemetry Redlines
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_sector_writes: int = 0,
    slot1_data_sector_writes: int = 0,
    emmc_write_count: int = 0,
    e_nd_actuator_tx_count: int = 0,
    rf_tx_packets: int = 0,
    usb_packets_transmitted: int = 0,
    simulated_passive_tx_bytes: int = 0,
    simulated_h0_h3_drifted_surfaces: int = 0,
    claim_hardware_live_attach_authorized: bool = False,
    claim_persistent_emmc_writes_authorized: bool = False,
    claim_cross_model_flash_authorized: bool = False,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    h3_baselines: Optional[Mapping[str, str]] = None,
) -> P374CheckGroupDFlash250ExtFlashNrFormatSlot1Erofs30Tier0Result:
    errors: List[str] = []
    warnings: List[str] = []

    # MI Shoe Flash & Wave 82 G156 Erratum
    if flash_mode not in P374_FX3_FLASH_MODES:
        errors.append(
            f"{P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT}: invalid flash_mode {flash_mode!r}"
        )
    if flash_xsync_max_denom != P374_FX3_FLASH_XSYNC_MAX_DENOM or claimed_flash_xsync_320_apsc_or_160_200_efcs_g156:
        errors.append(
            f"{P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT}: FX3 mechanical X-sync ceiling is strictly 1/250 s (Wave 82 G156 erratum: zero 1/320 s APS-C, zero 1/160 s / 1/200 s EFCS downgrade)"
        )
    if flash_firing_requested:
        if shoot_mode != "PHOTO" or shutter_type == "ELECTRONIC_SHUTTER" or silent_mode == "ON":
            errors.append(
                f"{P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT}: Flash shooting is 100%% locked out in Electronic Shutter, Silent Mode=On, and Movie/S&Q"
            )
        if flash_sync_shutter_denom > P374_FX3_FLASH_XSYNC_MAX_DENOM and not flash_hss_enabled:
            errors.append(
                f"{P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT}: Shutter 1/{flash_sync_shutter_denom} s exceeds 1/250 s mechanical X-sync without compatible HSS flash"
            )
        if flash_sync_shutter_denom > P374_STILL_MAX_SHUTTER_DENOM:
            errors.append(
                f"{P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT}: Flash shutter speed 1/{flash_sync_shutter_denom} s exceeds 1/8000 s ceiling"
            )
    flash_hss_banding = (
        flash_firing_requested
        and flash_hss_enabled
        and flash_sync_shutter_denom > P374_FX3_FLASH_HSS_BANDING_WARN_DENOM
    )
    if flash_hss_banding:
        warnings.append(
            "HSS flash above 1/4000 s may exhibit light/dark banding; Sony ilc/2210 recommends Manual flash >= 1/2 power."
        )
    if flash_trigger_voltage_v < 0.0 or flash_trigger_voltage_v >= P374_FX3_FLASH_MAX_TRIGGER_VOLTAGE_V or flash_negative_polarity:
        errors.append(
            f"{P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT}: MI Shoe requires positive polarity <250V trigger voltage (got {flash_trigger_voltage_v}V, neg_pol={flash_negative_polarity})"
        )
    if claimed_fx3_has_pc_sync_terminal:
        errors.append(
            f"{P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT}: FX3 has zero PC sync terminal (0 SYNCHRO_TERMINAL* hits, EOPNOTSUPP={P374_ERRNO_EOPNOTSUPP})"
        )
    if dormant_reg_flash_shooting_set_requested:
        errors.append(
            f"{P374_GD_ERR_FLASH_XSYNC_250_G156_OR_REG_FLASH_ABSENT}: [Reg. Flash Shooting Set.] has 0 hits in ilc/2210 and FX3 appFw.so (EOPNOTSUPP={P374_ERRNO_EOPNOTSUPP})"
        )

    # Exp.comp.set Anti-Reset, External Flash Set. 0 Body BKID & FX6 Flash Band Reduce
    if exp_comp_set not in P374_FX3_EXP_COMP_SET_MODES:
        errors.append(
            f"{P374_GD_ERR_EXT_FLASH_BKID0_EXPCOMP_OR_FX6_FBR}: invalid exp_comp_set {exp_comp_set!r}"
        )
    if claimed_exp_comp_set_wiped_by_camera_reset:
        errors.append(
            f"{P374_GD_ERR_EXT_FLASH_BKID0_EXPCOMP_OR_FX6_FBR}: [Exp.comp.set] resists [Camera Settings Reset] (Initialize-only)"
        )
    if external_flash_body_bkid_count != P374_FX3_EXTERNAL_FLASH_BODY_BKID_COUNT or claimed_external_flash_saved_in_camset_or_resettable:
        errors.append(
            f"{P374_GD_ERR_EXT_FLASH_BKID0_EXPCOMP_OR_FX6_FBR}: [External Flash Set.] has 0 body BKIDs, resists Reset, and is excluded from CAMSET*.DAT"
        )
    if claimed_fx6_has_flash_sync_or_fbr_is_sync:
        errors.append(
            f"{P374_GD_ERR_EXT_FLASH_BKID0_EXPCOMP_OR_FX6_FBR}: FX6 has zero flash sync; Flash Band Reduce mitigates external flash banding in video"
        )

    # Long Exposure NR & High ISO NR (Exact 3 Levels) vs FX6 Noise Suppression
    if long_exposure_nr not in P374_VALID_ON_OFF:
        errors.append(
            f"{P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL}: invalid long_exposure_nr {long_exposure_nr!r}"
        )
    if still_drive_mode not in P374_VALID_STILL_DRIVE_MODES:
        errors.append(
            f"{P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL}: invalid still_drive_mode {still_drive_mode!r}"
        )
    long_exp_nr_locked = (
        shoot_mode != "PHOTO"
        or shutter_type == "ELECTRONIC_SHUTTER"
        or silent_mode == "ON"
        or still_drive_mode in ("CONT_SHOOTING", "CONT_BRACKET")
    )
    if expect_long_exp_nr_active_under_lockout and long_exp_nr_locked:
        errors.append(
            f"{P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL}: [Long Exposure NR] (>=1s/BULB) is disabled in Electronic Shutter, Silent Mode, Cont. Shooting, Cont. Bracket, and Movie/S&Q"
        )
    if claimed_long_exp_nr_resists_camera_reset:
        errors.append(
            f"{P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL}: [Long Exposure NR] is Can be reset under [Camera Settings Reset]"
        )
    if tuple(high_iso_nr_options_exposed) != P374_FX3_HIGH_ISO_NR_EXACT_3_LEVELS:
        errors.append(
            f"{P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL}: [High ISO NR] exposes exact 3 levels {P374_FX3_HIGH_ISO_NR_EXACT_3_LEVELS} (zero High)"
        )
    if high_iso_nr not in P374_FX3_HIGH_ISO_NR_EXACT_3_LEVELS:
        errors.append(
            f"{P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL}: invalid high_iso_nr {high_iso_nr!r}"
        )
    if dormant_high_iso_nr_high_requested:
        errors.append(
            f"{P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL}: dormant [High ISO NR]=High rejected (EOPNOTSUPP={P374_ERRNO_EOPNOTSUPP})"
        )
    if claimed_high_iso_nr_mutates_arw_raw:
        errors.append(
            f"{P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL}: [High ISO NR] applies to Still JPEG/HEIF only and never mutates .ARW RAW"
        )
    if fx6_noise_suppression_level not in P374_FX6_NOISE_SUPPRESSION_LEVELS:
        errors.append(
            f"{P374_GD_ERR_LONG_EXP_NR_OR_HIGH_ISO_NR_3LEVEL}: invalid fx6_noise_suppression_level {fx6_noise_suppression_level!r}"
        )

    # [Format] Quick Format (:/AVF_INFO) vs Full Format (fsysDepMCmn_EraseDataFull) & Slot 1 EROFS=30
    if format_mode not in P374_FORMAT_MODES:
        errors.append(
            f"{P374_GD_ERR_FORMAT_SLOT1_EROFS30_OR_QUICK_FULL_PATH}: invalid format_mode {format_mode!r}"
        )
    if format_target_slot not in (1, 2):
        errors.append(
            f"{P374_GD_ERR_FORMAT_SLOT1_EROFS30_OR_QUICK_FULL_PATH}: format_target_slot must be 1 or 2, got {format_target_slot}"
        )
    if format_media_bus not in P374_MEDIA_BUS_TYPES:
        errors.append(
            f"{P374_GD_ERR_FORMAT_SLOT1_EROFS30_OR_QUICK_FULL_PATH}: invalid format_media_bus {format_media_bus!r}"
        )
    if quick_format_avf_info_path != P374_QUICK_FORMAT_AVF_INFO_PATH:
        errors.append(
            f"{P374_GD_ERR_FORMAT_SLOT1_EROFS30_OR_QUICK_FULL_PATH}: Quick Format libmpr.so DB path must be {P374_QUICK_FORMAT_AVF_INFO_PATH!r}"
        )
    if full_format_erase_symbol != P374_FULL_FORMAT_ERASE_SYMBOL:
        errors.append(
            f"{P374_GD_ERR_FORMAT_SLOT1_EROFS30_OR_QUICK_FULL_PATH}: Full Format erase symbol must be {P374_FULL_FORMAT_ERASE_SYMBOL!r}"
        )
    if claimed_full_format_cancel_restores_erased_data:
        errors.append(
            f"{P374_GD_ERR_FORMAT_SLOT1_EROFS30_OR_QUICK_FULL_PATH}: Full Format (SD EraseBlock/DISCARD, CFexpress NVME_FORMAT/DISCARD) is irreversible even if cancelled mid-way"
        )
    slot1_format_attempt = (
        (format_mode in ("QUICK_FORMAT", "FULL_FORMAT") and format_target_slot == 1)
        or format_hotkey_menu_delete_2s_slot == 1
        or avf_info_rebuild_slot1_requested
        or full_format_discard_trim_slot1_requested
    )
    if slot1_format_attempt and (slot1_contains_tier0_dump or slot1_wp_locked):
        errors.append(
            f"{P374_GD_ERR_FORMAT_SLOT1_EROFS30_OR_QUICK_FULL_PATH}: Format/Erase/DISCARD/AVF_INFO targeting Slot 1 Tier-0 Vault blocked EROFS={P374_ERRNO_EROFS}"
        )

    # Zero-Telemetry & Fail-Closed Redlines
    if (
        slot1_sector_writes != 0
        or slot1_data_sector_writes != 0
        or emmc_write_count != 0
        or e_nd_actuator_tx_count != 0
        or rf_tx_packets != 0
        or usb_packets_transmitted != 0
        or simulated_passive_tx_bytes != 0
    ):
        errors.append(
            f"{P374_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: telemetry counters must remain 0 "
            f"(slot1={slot1_sector_writes}, slot1_data={slot1_data_sector_writes}, emmc={emmc_write_count}, "
            f"e_nd={e_nd_actuator_tx_count}, rf={rf_tx_packets}, usb={usb_packets_transmitted}, passive={simulated_passive_tx_bytes})"
        )
    if (
        claim_hardware_live_attach_authorized
        or claim_persistent_emmc_writes_authorized
        or claim_cross_model_flash_authorized
    ):
        errors.append(
            f"{P374_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: live attach, persistent eMMC writes, and cross-model flash remain hard-locked False"
        )

    tier0 = _extract_tier0_evidence(
        simulate_bench_dry_run=simulate_bench_dry_run,
        receipt_a_bytes=receipt_a_bytes,
        receipt_b_bytes=receipt_b_bytes,
        receipt_a_path=receipt_a_path,
        receipt_b_path=receipt_b_path,
        st_dev_a_override=st_dev_a_override,
        st_dev_b_override=st_dev_b_override,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_baselines_a,
        h0_baselines_b=h0_baselines_b,
        h3_baselines=h3_baselines,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
    )
    errors.extend(tier0["errors"])
    warnings.extend(tier0["warnings"])

    eff_exp_comp_set = (
        P374_FX3_EXP_COMP_SET_DEFAULT if reset_action == "INITIALIZE" else exp_comp_set
    )
    eff_long_exp_nr = (
        "ON" if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE") else long_exposure_nr
    )

    return P374CheckGroupDFlash250ExtFlashNrFormatSlot1Erofs30Tier0Result(
        group_id=P374_CHECK_GROUP_D_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        flash_mode=flash_mode,
        flash_xsync_max_denom=flash_xsync_max_denom,
        flash_firing_requested=flash_firing_requested,
        flash_sync_shutter_denom=flash_sync_shutter_denom,
        flash_hss_enabled=flash_hss_enabled,
        flash_hss_banding_warning=flash_hss_banding,
        flash_trigger_voltage_v=flash_trigger_voltage_v,
        fx3_pc_sync_terminal_present=False,
        exp_comp_set=exp_comp_set,
        effective_exp_comp_set_after_reset=eff_exp_comp_set,
        external_flash_body_bkid_count=external_flash_body_bkid_count,
        external_flash_excluded_from_camset=True,
        fx3_reg_flash_shooting_set_supported=False,
        long_exposure_nr=long_exposure_nr,
        effective_long_exposure_nr_after_reset=eff_long_exp_nr,
        long_exposure_nr_locked_out=long_exp_nr_locked,
        high_iso_nr=high_iso_nr,
        high_iso_nr_options_exposed=tuple(high_iso_nr_options_exposed),
        high_iso_nr_mutates_arw_raw=False,
        fx6_noise_suppression_level=fx6_noise_suppression_level,
        format_mode=format_mode,
        format_target_slot=format_target_slot,
        format_media_bus=format_media_bus,
        quick_format_avf_info_path=quick_format_avf_info_path,
        full_format_erase_symbol=full_format_erase_symbol,
        slot1_format_blocked_erofs30=True,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_sector_writes=PHASE374_SLOT1_SECTOR_WRITES,
        slot1_data_sector_writes=PHASE374_SLOT1_DATA_SECTOR_WRITES,
        slot1_tier0_vault_mutated=False,
        tier0_receipt_verified=bool(tier0["tier0_receipt_verified"]),
        receipt_mode=str(tier0["receipt_mode"]),
        h0_equals_h3_count=int(tier0["h0_equals_h3_count"]),
        h0_h3_surface_count=P374_STORAGE_SURFACE_COUNT,
        st_dev_a=tier0["st_dev_a"],
        st_dev_b=tier0["st_dev_b"],
        receipt_body_serial=str(tier0["body_serial"]),
        receipt_emmc_cid=str(tier0["emmc_cid"]),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Full Phase 374 Orchestrator & Report Verifier
# ---------------------------------------------------------------------------


def evaluate_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight(
    *,
    simulate_bench_dry_run: bool = False,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P374_SONY_HELP_GUIDE_ID,
    shoot_mode: str = "PHOTO",
    log_shooting_mode: str = "OFF",
    picture_profile: str = "PP11",
    hlg_still_image: str = "OFF",
    reset_action: str = "NONE",
    # Group A
    silent_mode: str = "OFF",
    silent_target_items_exposed: Tuple[str, ...] = P374_SILENT_TARGET_EXACT_2_ITEMS,
    silent_target_aperture_drive: str = P374_SILENT_TARGET_APERTURE_DEFAULT,
    silent_target_auto_pixel_mapping: str = P374_SILENT_TARGET_AUTO_PIXEL_MAP_DEFAULT,
    setup_auto_pixel_mapping: str = "ON",
    dormant_silent_target_item_requested: Optional[str] = None,
    silent_mode_lockouts_enforced: Tuple[str, ...] = P374_SILENT_MODE_EXACT_5_LOCKOUTS,
    expect_silent_lockout_feature_active: bool = False,
    claimed_silent_mode_or_target2_resists_camera_reset: bool = False,
    claimed_setup_auto_pixel_mapping_wiped_by_camera_reset: bool = False,
    dro_mode: str = "OFF",
    dro_bracket_mode: str = "NONE",
    expect_dro_active_under_pp11_log_or_hlg: bool = False,
    claimed_dro_resists_camera_reset: bool = False,
    dormant_auto_hdr_requested: bool = False,
    dormant_multi_frame_nr_requested: bool = False,
    claimed_fx3_has_auto_hdr_or_mfnr: bool = False,
    claimed_fx6_has_mech_shutter_or_silent_mode: bool = False,
    fx6_shooting_mode: str = "CUSTOM",
    fx6_paint_look_active: bool = True,
    fx6_knee_point_pct: int = P374_FX6_KNEE_POINT_DEFAULT_PCT,
    fx6_knee_slope: int = P374_FX6_KNEE_SLOPE_DEFAULT,
    fx6_master_black: float = P374_FX6_BLACK_DEFAULT,
    dormant_fx6_paint_item_requested: Optional[str] = None,
    claimed_fx6_ui_has_black_gamma_or_white_clip: bool = False,
    # Group B
    audio_signals: str = P374_FX3_AUDIO_SIGNALS_DEFAULT,
    audio_signals_options_exposed: Tuple[str, ...] = P374_FX3_AUDIO_SIGNALS_EXACT_2_MODES,
    dormant_audio_signals_g85_mode_requested: Optional[str] = None,
    claimed_audio_signals_wiped_by_camera_reset: bool = False,
    expect_audio_signals_audible_under_silent_mode: bool = False,
    fx3_fan_control: str = P374_FX3_FAN_CONTROL_DEFAULT,
    fx3_fan_control_options_exposed: Tuple[str, ...] = P374_FX3_FAN_CONTROL_EXACT_4_MODES,
    dormant_fx3_fan_g82_mode_requested: Optional[str] = None,
    auto_power_off_temp: str = P374_AUTO_POWER_OFF_TEMP_DEFAULT,
    claimed_fan_or_autotemp_wiped_by_camera_reset: bool = False,
    sustained_bench_recording_under_always_off: bool = False,
    fx6_fan_control: str = "AUTO",
    fx6_fan_control_options_exposed: Tuple[str, ...] = P374_FX6_FAN_CONTROL_EXACT_3_MODES,
    dormant_fx6_fan_mode_requested: Optional[str] = None,
    claimed_fx6_fan_has_max_or_ui_always_off: bool = False,
    fx6_alarm_level: int = P374_FX6_ALARM_LEVEL_DEFAULT,
    version_entities_exposed: Tuple[str, ...] = P374_VERSION_EXACT_3_ENTITIES,
    body_update_filename: str = P374_BODY_UPDATE_FILENAME,
    lens_update_filename: str = P374_LENS_UPDATE_FILENAME,
    bodydata_dat_update_requested: bool = False,
    lensdata_dat_update_requested: bool = False,
    usb_uud_lens_update_requested: bool = False,
    fx6_slot_b_version_up_requested: bool = False,
    claimed_lens_update_safe_on_tier0_bench: bool = False,
    cert_logo_region: str = "US_EU_INTL",
    expect_cert_logo_visible_in_us_eu: bool = False,
    fx6_hours_system: int = 120,
    fx6_hours_reset: int = 15,
    fx6_hours_meter_reset_action: str = "NONE",
    claimed_fx6_hours_system_resettable: bool = False,
    claimed_fx6_hours_saved_in_all_file: bool = False,
    claimed_fx3_exposes_hours_meter_ui: bool = False,
    # Group C
    focus_mode: str = "AF_S",
    af_illuminator: str = P374_AF_ILLUMINATOR_DEFAULT,
    af_illuminator_distance_m: float = 1.5,
    af_a_subject_moving: bool = False,
    focus_magnifier_active: bool = False,
    mount_adaptor_attached: bool = False,
    expect_af_illuminator_fires_under_lockout: bool = False,
    claimed_fx3_lacks_physical_af_illuminator_led: bool = False,
    claimed_silent_mode_disables_af_illuminator: bool = False,
    claimed_af_illuminator_resists_camera_reset: bool = False,
    focus_af_triad_items: Tuple[str, ...] = P374_AF_FOCUS_TRIAD_ANTIRESET_ITEMS,
    focus_aperture_drive_in_af: str = P374_FOCUS_APERTURE_DRIVE_DEFAULT,
    af_w_shutter: str = "ON",
    pre_af: str = "OFF",
    lens_pre_af_support: bool = True,
    claimed_focus_af_triad_wiped_by_camera_reset: bool = False,
    expect_focus_af_triad_active_in_movie_or_sq: bool = False,
    claimed_fx6_has_af_illuminator_or_half_press_af: bool = False,
    shutter_type: str = P374_SHUTTER_TYPE_DEFAULT,
    shutter_type_options_exposed: Tuple[str, ...] = P374_SHUTTER_TYPE_EXACT_2_OPTIONS,
    dormant_shutter_type_auto_requested: bool = False,
    still_shutter_denom: int = 250,
    bulb_requested: bool = False,
    claimed_shutter_type_resists_camera_reset: bool = False,
    expect_movie_uses_still_shutter_type: bool = False,
    e_front_curtain_shutter: str = "ON",
    efcs_bkid_typo_symbol: str = P374_EFCS_BKID_TYPO,
    aperture_f_number: float = 2.8,
    third_party_lens_attached: bool = False,
    claimed_efcs_wiped_by_camera_reset: bool = False,
    expect_efcs_active_under_eshutter_or_silent: bool = False,
    expect_no_bokeh_clipping_with_efcs_high_speed: bool = False,
    claimed_fx6_has_mechanical_shutter_or_efcs: bool = False,
    # Group D + Tier-0
    still_drive_mode: str = "SINGLE_SHOOTING",
    flash_mode: str = "AUTOFLASH",
    flash_xsync_max_denom: int = P374_FX3_FLASH_XSYNC_MAX_DENOM,
    flash_firing_requested: bool = False,
    flash_sync_shutter_denom: int = 250,
    flash_hss_enabled: bool = False,
    flash_trigger_voltage_v: float = 5.0,
    flash_negative_polarity: bool = False,
    claimed_flash_xsync_320_apsc_or_160_200_efcs_g156: bool = False,
    claimed_fx3_has_pc_sync_terminal: bool = False,
    exp_comp_set: str = P374_FX3_EXP_COMP_SET_DEFAULT,
    claimed_exp_comp_set_wiped_by_camera_reset: bool = False,
    external_flash_body_bkid_count: int = P374_FX3_EXTERNAL_FLASH_BODY_BKID_COUNT,
    claimed_external_flash_saved_in_camset_or_resettable: bool = False,
    dormant_reg_flash_shooting_set_requested: bool = False,
    claimed_fx6_has_flash_sync_or_fbr_is_sync: bool = False,
    long_exposure_nr: str = "ON",
    expect_long_exp_nr_active_under_lockout: bool = False,
    claimed_long_exp_nr_resists_camera_reset: bool = False,
    high_iso_nr: str = P374_FX3_HIGH_ISO_NR_DEFAULT,
    high_iso_nr_options_exposed: Tuple[str, ...] = P374_FX3_HIGH_ISO_NR_EXACT_3_LEVELS,
    dormant_high_iso_nr_high_requested: bool = False,
    claimed_high_iso_nr_mutates_arw_raw: bool = False,
    fx6_noise_suppression_level: str = "MID",
    format_mode: str = "NONE",
    format_target_slot: int = 2,
    format_media_bus: str = "CFEXPRESS_TYPE_A_NVME",
    quick_format_avf_info_path: str = P374_QUICK_FORMAT_AVF_INFO_PATH,
    full_format_erase_symbol: str = P374_FULL_FORMAT_ERASE_SYMBOL,
    format_hotkey_menu_delete_2s_slot: Optional[int] = None,
    avf_info_rebuild_slot1_requested: bool = False,
    full_format_discard_trim_slot1_requested: bool = False,
    claimed_full_format_cancel_restores_erased_data: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_sector_writes: int = 0,
    slot1_data_sector_writes: int = 0,
    emmc_write_count: int = 0,
    e_nd_actuator_tx_count: int = 0,
    rf_tx_packets: int = 0,
    usb_packets_transmitted: int = 0,
    simulated_passive_tx_bytes: int = 0,
    simulated_h0_h3_drifted_surfaces: int = 0,
    claim_hardware_live_attach_authorized: bool = False,
    claim_persistent_emmc_writes_authorized: bool = False,
    claim_cross_model_flash_authorized: bool = False,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    h3_baselines: Optional[Mapping[str, str]] = None,
) -> RealHwSilentModeDroFanCtrlHoursMeterAfIllumShutterFlashAndFormatReport:
    donor = inspect_phase374_donors_bounded(
        force_clean_room=force_clean_room,
        work_root=work_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )

    ga = evaluate_p374_check_group_a_silentmode_target2_dro_and_fx6_paintlook(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        hlg_still_image=hlg_still_image,
        reset_action=reset_action,
        silent_mode=silent_mode,
        silent_target_items_exposed=silent_target_items_exposed,
        silent_target_aperture_drive=silent_target_aperture_drive,
        silent_target_auto_pixel_mapping=silent_target_auto_pixel_mapping,
        setup_auto_pixel_mapping=setup_auto_pixel_mapping,
        dormant_silent_target_item_requested=dormant_silent_target_item_requested,
        silent_mode_lockouts_enforced=silent_mode_lockouts_enforced,
        expect_silent_lockout_feature_active=expect_silent_lockout_feature_active,
        claimed_silent_mode_or_target2_resists_camera_reset=claimed_silent_mode_or_target2_resists_camera_reset,
        claimed_setup_auto_pixel_mapping_wiped_by_camera_reset=claimed_setup_auto_pixel_mapping_wiped_by_camera_reset,
        dro_mode=dro_mode,
        dro_bracket_mode=dro_bracket_mode,
        expect_dro_active_under_pp11_log_or_hlg=expect_dro_active_under_pp11_log_or_hlg,
        claimed_dro_resists_camera_reset=claimed_dro_resists_camera_reset,
        dormant_auto_hdr_requested=dormant_auto_hdr_requested,
        dormant_multi_frame_nr_requested=dormant_multi_frame_nr_requested,
        claimed_fx3_has_auto_hdr_or_mfnr=claimed_fx3_has_auto_hdr_or_mfnr,
        claimed_fx6_has_mech_shutter_or_silent_mode=claimed_fx6_has_mech_shutter_or_silent_mode,
        fx6_shooting_mode=fx6_shooting_mode,
        fx6_paint_look_active=fx6_paint_look_active,
        fx6_knee_point_pct=fx6_knee_point_pct,
        fx6_knee_slope=fx6_knee_slope,
        fx6_master_black=fx6_master_black,
        dormant_fx6_paint_item_requested=dormant_fx6_paint_item_requested,
        claimed_fx6_ui_has_black_gamma_or_white_clip=claimed_fx6_ui_has_black_gamma_or_white_clip,
    )

    gb = evaluate_p374_check_group_b_audiosignals_fanctrl4_version_and_fx6_hoursmeter(
        reset_action=reset_action,
        silent_mode=silent_mode,
        audio_signals=audio_signals,
        audio_signals_options_exposed=audio_signals_options_exposed,
        dormant_audio_signals_g85_mode_requested=dormant_audio_signals_g85_mode_requested,
        claimed_audio_signals_wiped_by_camera_reset=claimed_audio_signals_wiped_by_camera_reset,
        expect_audio_signals_audible_under_silent_mode=expect_audio_signals_audible_under_silent_mode,
        fx3_fan_control=fx3_fan_control,
        fx3_fan_control_options_exposed=fx3_fan_control_options_exposed,
        dormant_fx3_fan_g82_mode_requested=dormant_fx3_fan_g82_mode_requested,
        auto_power_off_temp=auto_power_off_temp,
        claimed_fan_or_autotemp_wiped_by_camera_reset=claimed_fan_or_autotemp_wiped_by_camera_reset,
        sustained_bench_recording_under_always_off=sustained_bench_recording_under_always_off,
        fx6_fan_control=fx6_fan_control,
        fx6_fan_control_options_exposed=fx6_fan_control_options_exposed,
        dormant_fx6_fan_mode_requested=dormant_fx6_fan_mode_requested,
        claimed_fx6_fan_has_max_or_ui_always_off=claimed_fx6_fan_has_max_or_ui_always_off,
        fx6_alarm_level=fx6_alarm_level,
        version_entities_exposed=version_entities_exposed,
        body_update_filename=body_update_filename,
        lens_update_filename=lens_update_filename,
        bodydata_dat_update_requested=bodydata_dat_update_requested,
        lensdata_dat_update_requested=lensdata_dat_update_requested,
        usb_uud_lens_update_requested=usb_uud_lens_update_requested,
        fx6_slot_b_version_up_requested=fx6_slot_b_version_up_requested,
        claimed_lens_update_safe_on_tier0_bench=claimed_lens_update_safe_on_tier0_bench,
        cert_logo_region=cert_logo_region,
        expect_cert_logo_visible_in_us_eu=expect_cert_logo_visible_in_us_eu,
        fx6_hours_system=fx6_hours_system,
        fx6_hours_reset=fx6_hours_reset,
        fx6_hours_meter_reset_action=fx6_hours_meter_reset_action,
        claimed_fx6_hours_system_resettable=claimed_fx6_hours_system_resettable,
        claimed_fx6_hours_saved_in_all_file=claimed_fx6_hours_saved_in_all_file,
        claimed_fx3_exposes_hours_meter_ui=claimed_fx3_exposes_hours_meter_ui,
        slot1_sector_writes=slot1_sector_writes,
    )

    gc = evaluate_p374_check_group_c_afillum_antireset_af3_shutter2_and_efcs(
        shoot_mode=shoot_mode,
        focus_mode=focus_mode,
        reset_action=reset_action,
        silent_mode=silent_mode,
        af_illuminator=af_illuminator,
        af_illuminator_distance_m=af_illuminator_distance_m,
        af_a_subject_moving=af_a_subject_moving,
        focus_magnifier_active=focus_magnifier_active,
        mount_adaptor_attached=mount_adaptor_attached,
        expect_af_illuminator_fires_under_lockout=expect_af_illuminator_fires_under_lockout,
        claimed_fx3_lacks_physical_af_illuminator_led=claimed_fx3_lacks_physical_af_illuminator_led,
        claimed_silent_mode_disables_af_illuminator=claimed_silent_mode_disables_af_illuminator,
        claimed_af_illuminator_resists_camera_reset=claimed_af_illuminator_resists_camera_reset,
        focus_af_triad_items=focus_af_triad_items,
        focus_aperture_drive_in_af=focus_aperture_drive_in_af,
        af_w_shutter=af_w_shutter,
        pre_af=pre_af,
        lens_pre_af_support=lens_pre_af_support,
        claimed_focus_af_triad_wiped_by_camera_reset=claimed_focus_af_triad_wiped_by_camera_reset,
        expect_focus_af_triad_active_in_movie_or_sq=expect_focus_af_triad_active_in_movie_or_sq,
        claimed_fx6_has_af_illuminator_or_half_press_af=claimed_fx6_has_af_illuminator_or_half_press_af,
        shutter_type=shutter_type,
        shutter_type_options_exposed=shutter_type_options_exposed,
        dormant_shutter_type_auto_requested=dormant_shutter_type_auto_requested,
        still_shutter_denom=still_shutter_denom,
        bulb_requested=bulb_requested,
        claimed_shutter_type_resists_camera_reset=claimed_shutter_type_resists_camera_reset,
        expect_movie_uses_still_shutter_type=expect_movie_uses_still_shutter_type,
        e_front_curtain_shutter=e_front_curtain_shutter,
        efcs_bkid_typo_symbol=efcs_bkid_typo_symbol,
        aperture_f_number=aperture_f_number,
        third_party_lens_attached=third_party_lens_attached,
        claimed_efcs_wiped_by_camera_reset=claimed_efcs_wiped_by_camera_reset,
        expect_efcs_active_under_eshutter_or_silent=expect_efcs_active_under_eshutter_or_silent,
        expect_no_bokeh_clipping_with_efcs_high_speed=expect_no_bokeh_clipping_with_efcs_high_speed,
        claimed_fx6_has_mechanical_shutter_or_efcs=claimed_fx6_has_mechanical_shutter_or_efcs,
    )

    gd = evaluate_p374_check_group_d_flash250_extflash_nr_format_and_tier0(
        simulate_bench_dry_run=simulate_bench_dry_run,
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        silent_mode=silent_mode,
        shutter_type=shutter_type,
        still_drive_mode=still_drive_mode,
        flash_mode=flash_mode,
        flash_xsync_max_denom=flash_xsync_max_denom,
        flash_firing_requested=flash_firing_requested,
        flash_sync_shutter_denom=flash_sync_shutter_denom,
        flash_hss_enabled=flash_hss_enabled,
        flash_trigger_voltage_v=flash_trigger_voltage_v,
        flash_negative_polarity=flash_negative_polarity,
        claimed_flash_xsync_320_apsc_or_160_200_efcs_g156=claimed_flash_xsync_320_apsc_or_160_200_efcs_g156,
        claimed_fx3_has_pc_sync_terminal=claimed_fx3_has_pc_sync_terminal,
        exp_comp_set=exp_comp_set,
        claimed_exp_comp_set_wiped_by_camera_reset=claimed_exp_comp_set_wiped_by_camera_reset,
        external_flash_body_bkid_count=external_flash_body_bkid_count,
        claimed_external_flash_saved_in_camset_or_resettable=claimed_external_flash_saved_in_camset_or_resettable,
        dormant_reg_flash_shooting_set_requested=dormant_reg_flash_shooting_set_requested,
        claimed_fx6_has_flash_sync_or_fbr_is_sync=claimed_fx6_has_flash_sync_or_fbr_is_sync,
        long_exposure_nr=long_exposure_nr,
        expect_long_exp_nr_active_under_lockout=expect_long_exp_nr_active_under_lockout,
        claimed_long_exp_nr_resists_camera_reset=claimed_long_exp_nr_resists_camera_reset,
        high_iso_nr=high_iso_nr,
        high_iso_nr_options_exposed=high_iso_nr_options_exposed,
        dormant_high_iso_nr_high_requested=dormant_high_iso_nr_high_requested,
        claimed_high_iso_nr_mutates_arw_raw=claimed_high_iso_nr_mutates_arw_raw,
        fx6_noise_suppression_level=fx6_noise_suppression_level,
        format_mode=format_mode,
        format_target_slot=format_target_slot,
        format_media_bus=format_media_bus,
        quick_format_avf_info_path=quick_format_avf_info_path,
        full_format_erase_symbol=full_format_erase_symbol,
        format_hotkey_menu_delete_2s_slot=format_hotkey_menu_delete_2s_slot,
        avf_info_rebuild_slot1_requested=avf_info_rebuild_slot1_requested,
        full_format_discard_trim_slot1_requested=full_format_discard_trim_slot1_requested,
        claimed_full_format_cancel_restores_erased_data=claimed_full_format_cancel_restores_erased_data,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_sector_writes=slot1_sector_writes,
        slot1_data_sector_writes=slot1_data_sector_writes,
        emmc_write_count=emmc_write_count,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        rf_tx_packets=rf_tx_packets,
        usb_packets_transmitted=usb_packets_transmitted,
        simulated_passive_tx_bytes=simulated_passive_tx_bytes,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
        claim_hardware_live_attach_authorized=claim_hardware_live_attach_authorized,
        claim_persistent_emmc_writes_authorized=claim_persistent_emmc_writes_authorized,
        claim_cross_model_flash_authorized=claim_cross_model_flash_authorized,
        receipt_a_bytes=receipt_a_bytes,
        receipt_b_bytes=receipt_b_bytes,
        receipt_a_path=receipt_a_path,
        receipt_b_path=receipt_b_path,
        st_dev_a_override=st_dev_a_override,
        st_dev_b_override=st_dev_b_override,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_baselines_a,
        h0_baselines_b=h0_baselines_b,
        h3_baselines=h3_baselines,
    )

    groups = (ga, gb, gc, gd)
    groups_passed = sum(1 for g in groups if g.passed)
    all_errors = ga.errors + gb.errors + gc.errors + gd.errors
    all_warnings = ga.warnings + gb.warnings + gc.warnings + gd.warnings

    if all_errors:
        go_no_go = (
            P374_GO_NO_GO_BLOCKED_SILENTMODE_DRO_FANCTRL_HOURSMETER_AFILLUM_SHUTTER_FLASH_AND_FORMAT_FAILURE
        )
        overall_status = go_no_go
    elif not gd.tier0_receipt_verified:
        go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        overall_status = P374_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
    elif simulate_bench_dry_run:
        go_no_go = GO_NO_GO_DRY_RUN_SIMULATED_READY
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        go_no_go = (
            P374_GO_NO_GO_SILENTMODE_DRO_FANCTRL_HOURSMETER_AFILLUM_SHUTTER_FLASH_AND_FORMAT_VERIFIED
        )
        overall_status = go_no_go

    report = RealHwSilentModeDroFanCtrlHoursMeterAfIllumShutterFlashAndFormatReport(
        schema_version=P374_SCHEMA,
        phase_version=P374_VERSION,
        sony_help_guide_id=sony_help_guide_id,
        overall_status=overall_status,
        go_no_go=go_no_go,
        verification_mode=donor.verification_mode,
        simulate_bench_dry_run=bool(simulate_bench_dry_run),
        check_group_count=len(groups),
        check_groups_passed=groups_passed,
        check_group_a=ga,
        check_group_b=gb,
        check_group_c=gc,
        check_group_d=gd,
        donor_inspection=donor,
        tier0_receipt_verified=gd.tier0_receipt_verified,
        receipt_mode=gd.receipt_mode,
        h0_equals_h3_count=gd.h0_equals_h3_count,
        h0_h3_surface_count=P374_STORAGE_SURFACE_COUNT,
        slot1_tier0_vault_mutated=False,
        ready_for_live_camera_attach=False,
        overall_ready_for_hardware_attach=False,
        live_attach_authorized=False,
        hardware_live_attachment_authorized=False,
        emmc_writes_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        sd_physical_media_written=False,
        cross_model_flash_authorized=False,
        rf_nvs_p12_p13_writes_authorized=False,
        fx3_shutter_when_pwr_off_supported=False,
        fx3_auto_hdr_supported=False,
        fx3_shutter_type_auto_supported=False,
        fx3_reg_flash_shooting_set_supported=False,
        fx3_pc_sync_terminal_present=False,
        fx3_hours_meter_ui_exposed=False,
        lens_or_body_dat_update_authorized=False,
        emmc_write_count=PHASE374_EMMC_WRITE_COUNT,
        e_nd_actuator_tx_count=PHASE374_E_ND_ACTUATOR_TX_COUNT,
        e_nd_i2c_tx_bytes=PHASE374_E_ND_I2C_TX_BYTES,
        rf_tx_packets=PHASE374_RF_TX_PACKETS,
        rf_packets_transmitted=PHASE374_RF_PACKETS_TRANSMITTED,
        wireless_rf_packets_emitted=PHASE374_WIRELESS_RF_PACKETS_EMITTED,
        rf_nvs_mutation_bytes=PHASE374_RF_NVS_MUTATION_BYTES,
        slot1_sector_writes=PHASE374_SLOT1_SECTOR_WRITES,
        slot1_data_sector_writes=PHASE374_SLOT1_DATA_SECTOR_WRITES,
        usb_packets_transmitted=PHASE374_USB_PACKETS_TRANSMITTED,
        passive_tx_bytes_emitted=PHASE374_PASSIVE_TX_BYTES_EMITTED,
        raw_firmware_bytes_leaked=PHASE374_RAW_FIRMWARE_BYTES_LEAKED,
        errors=all_errors,
        warnings=all_warnings,
        report_sha256="",
    )
    digest = _canonical_sha256_dict(report.to_dict())
    return RealHwSilentModeDroFanCtrlHoursMeterAfIllumShutterFlashAndFormatReport(
        **{
            **report.to_dict(),
            "check_group_a": ga,
            "check_group_b": gb,
            "check_group_c": gc,
            "check_group_d": gd,
            "donor_inspection": donor,
            "errors": report.errors,
            "warnings": report.warnings,
            "report_sha256": digest,
        }
    )


def run_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight(
    **kwargs: Any,
) -> RealHwSilentModeDroFanCtrlHoursMeterAfIllumShutterFlashAndFormatReport:
    return evaluate_realhw_silentmode_dro_fanctrl_hoursmeter_afillum_shutter_flash_and_format_preflight(
        **kwargs
    )


def verify_phase374_report(
    payload: Union[
        Mapping[str, Any],
        RealHwSilentModeDroFanCtrlHoursMeterAfIllumShutterFlashAndFormatReport,
    ],
) -> Phase374ReportVerifyResult:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()  # type: ignore[union-attr]
    errors: List[str] = []
    if payload.get("schema_version") != P374_SCHEMA:
        errors.append(
            f"schema_version mismatch: {payload.get('schema_version')!r} != {P374_SCHEMA!r}"
        )
    if payload.get("sony_help_guide_id") != P374_SONY_HELP_GUIDE_ID:
        errors.append("sony_help_guide_id must remain ilc/2210")
    if payload.get("go_no_go") not in PHASE_374_VALID_GO_NO_GO_VALUES:
        errors.append(f"invalid go_no_go: {payload.get('go_no_go')!r}")

    locked_false_fields = (
        "ready_for_live_camera_attach",
        "overall_ready_for_hardware_attach",
        "live_attach_authorized",
        "hardware_live_attachment_authorized",
        "emmc_writes_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "sd_physical_media_written",
        "cross_model_flash_authorized",
        "rf_nvs_p12_p13_writes_authorized",
        "fx3_shutter_when_pwr_off_supported",
        "fx3_auto_hdr_supported",
        "fx3_shutter_type_auto_supported",
        "fx3_reg_flash_shooting_set_supported",
        "fx3_pc_sync_terminal_present",
        "fx3_hours_meter_ui_exposed",
        "lens_or_body_dat_update_authorized",
    )
    for field in locked_false_fields:
        if payload.get(field) is not False:
            errors.append(f"hard-locked boolean {field} must be False")

    locked_zero_fields = (
        "emmc_write_count",
        "e_nd_actuator_tx_count",
        "e_nd_i2c_tx_bytes",
        "rf_tx_packets",
        "rf_packets_transmitted",
        "wireless_rf_packets_emitted",
        "rf_nvs_mutation_bytes",
        "slot1_sector_writes",
        "slot1_data_sector_writes",
        "usb_packets_transmitted",
        "passive_tx_bytes_emitted",
        "raw_firmware_bytes_leaked",
    )
    for field in locked_zero_fields:
        if payload.get(field) != 0:
            errors.append(f"hard-locked zero telemetry {field} must be 0")

    expected_sha = _canonical_sha256_dict(payload)
    if payload.get("report_sha256") != expected_sha:
        errors.append(
            f"report_sha256 mismatch: {payload.get('report_sha256')!r} != {expected_sha!r}"
        )

    if payload.get("go_no_go") in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P374_GO_NO_GO_SILENTMODE_DRO_FANCTRL_HOURSMETER_AFILLUM_SHUTTER_FLASH_AND_FORMAT_VERIFIED,
    ):
        if payload.get("check_groups_passed") != 4 or payload.get("check_group_count") != 4:
            errors.append("verified report must pass 4/4 check groups")
        if payload.get("tier0_receipt_verified") is not True:
            errors.append("verified report must have tier0_receipt_verified=True")
        if payload.get("h0_equals_h3_count") != 16 or payload.get("h0_h3_surface_count") != 16:
            errors.append("verified report must have 16/16 H0 == H3")
        if payload.get("slot1_tier0_vault_mutated") is not False:
            errors.append("verified report must have slot1_tier0_vault_mutated=False")

    return Phase374ReportVerifyResult(valid=len(errors) == 0, errors=tuple(errors))


def render_phase374_markdown(
    report: RealHwSilentModeDroFanCtrlHoursMeterAfIllumShutterFlashAndFormatReport,
) -> str:
    lines = [
        f"# Phase 374 — 25th Physical Bench Readiness Preflight (`25/25` Milestone, `{report.schema_version}`)",
        "",
        f"- **Overall Status**: `{report.overall_status}`",
        f"- **Go/No-Go**: `{report.go_no_go}`",
        f"- **Verification Mode**: `{report.verification_mode}` (Dry Run: `{report.simulate_bench_dry_run}`)",
        f"- **Check Groups Passed**: `{report.check_groups_passed}/{report.check_group_count}`",
        f"- **Tier-0 Receipt Verified**: `{report.tier0_receipt_verified}` (`{report.receipt_mode}`)",
        f"- **H0 == H3 Surfaces**: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`",
        f"- **Safety Redlines**: `overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}`, "
        f"`live_attach_authorized={report.live_attach_authorized}`, "
        f"`emmc_writes_authorized={report.emmc_writes_authorized}`, "
        f"`rf_tx_packets={report.rf_tx_packets}`, `slot1_sector_writes={report.slot1_sector_writes}`, "
        f"`slot1_data_sector_writes={report.slot1_data_sector_writes}`, "
        f"`raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}`",
        f"- **Report SHA-256**: `{report.report_sha256}`",
        "",
        "## Check Groups",
        f"- **Group A (`{report.check_group_a.group_id}`)**: passed=`{report.check_group_a.passed}`, "
        f"silent_target={len(report.check_group_a.silent_target_items_exposed)}, "
        f"dro=`{report.check_group_a.effective_dro_mode}`, "
        f"auto_hdr=`{report.check_group_a.fx3_auto_hdr_supported}`, "
        f"fx6_mode=`{report.check_group_a.fx6_shooting_mode}`",
        f"- **Group B (`{report.check_group_b.group_id}`)**: passed=`{report.check_group_b.passed}`, "
        f"audio_signals=`{report.check_group_b.effective_audio_signals}` ({len(report.check_group_b.audio_signals_options_exposed)} opts), "
        f"fx3_fan=`{report.check_group_b.fx3_fan_control}` ({len(report.check_group_b.fx3_fan_control_options_exposed)} opts), "
        f"fx6_fan=`{report.check_group_b.fx6_fan_control}` ({len(report.check_group_b.fx6_fan_control_options_exposed)} opts), "
        f"fx6_hours=`{report.check_group_b.effective_fx6_hours_system}/{report.check_group_b.effective_fx6_hours_reset}`",
        f"- **Group C (`{report.check_group_c.group_id}`)**: passed=`{report.check_group_c.passed}`, "
        f"af_illum=`{report.check_group_c.af_illuminator}` (led={report.check_group_c.fx3_physical_af_illuminator_led_present}), "
        f"shutter=`{report.check_group_c.shutter_type}` ({len(report.check_group_c.shutter_type_options_exposed)} opts), "
        f"efcs=`{report.check_group_c.e_front_curtain_shutter}`",
        f"- **Group D (`{report.check_group_d.group_id}`)**: passed=`{report.check_group_d.passed}`, "
        f"xsync=`1/{report.check_group_d.flash_xsync_max_denom}s`, "
        f"ext_flash_bkid={report.check_group_d.external_flash_body_bkid_count}, "
        f"high_iso_nr=`{report.check_group_d.high_iso_nr}` ({len(report.check_group_d.high_iso_nr_options_exposed)} levels), "
        f"format=`{report.check_group_d.format_mode}` (slot={report.check_group_d.format_target_slot}), "
        f"slot1_mut={report.check_group_d.slot1_tier0_vault_mutated}",
    ]
    if report.errors:
        lines.extend(["", "## Errors"] + [f"- `{err}`" for err in report.errors])
    if report.warnings:
        lines.extend(["", "## Warnings"] + [f"- {warn}" for warn in report.warnings])
    return "\n".join(lines) + "\n"
