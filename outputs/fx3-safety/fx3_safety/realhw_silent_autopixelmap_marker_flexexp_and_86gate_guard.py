"""Phase 230 Sony `ILME-FX3` (`Ver. 7.02`) Safety Gates `G85` (`Silent Mode Settings`
`Auto Pixel Mapping` Suppression Target, 5-Function Lockout & Hardware
`Shutter When Pwr OFF` Absence Guard) & `G86` (`Marker Display` 15-Ratio
Non-Resettable Persistence, Local-LCD-Only HDMI Isolation & `Flexible Exp. Mode`
`Av`/`Tv`/`ISO` + `Auto Slow Shutter` Reset Split Guard) + Unified 86-Gate
Master Safety Preflight (`G01..G86`).

Operationalizes Wave-33 official Sony `ILME-FX3` (`Ver. 7.02`) intelligence
(`reports/2026-11-15-global-sony-wave33-silent-mode-autopixelmap-no-pwrshutter-marker-hdmi-isolation-flexexp-intel/README.md`)
as deterministic offline preflight verifiers (`G85` and `G86`) and composes them
with `evaluate_84gate_preflight` (`G01..G84`) into a unified 86-gate master
safety preflight (`G01..G86`):

1. **Gate `G85` (`SILENT_MODE_AUTOPIXELMAP_TARGET_5LOCK_AND_NO_SHUTTER_WHEN_PWR_OFF_GUARD`)**:
   - **Silent Mode (`MENU -> Shooting -> [Shutter/Silent] -> [Silent Mode Settings]`)**:
     When `[Silent Mode] = [On]`, automatically locks `[Shutter Type]` and
     `[Shutter Type in Interval]` to `[Electronic Shutter]`, locks `[Audio signals]`
     to `[Off]`, and disables all **5 shooting functions**:
     1. `Flash` (Flash shooting),
     2. `Long Exposure NR` (`[Long Exposure NR]`),
     3. `e-Front Curtain Shut.` (`[e-Front Curtain Shut.]`),
     4. `BULB` (`BULB` shooting),
     5. `Anti-flicker Shoot.` (`[Anti-flicker Shoot.]`).
   - **`[Target Function Settings]` (`[Aperture Drive in AF]` & `[Auto Pixel Mapping]`)**:
     Models `[Target Function Settings]` governing `[Aperture Drive in AF]`
     (`Not Target` / `Standard` / `Focus Priority` / `Silent Priority`) and
     `[Auto Pixel Mapping]` (`Off` / `Not Target`). Selecting `[Not Target]`
     retains normal `[Auto Pixel Mapping]` behavior (power-off mechanical shutter
     actuation continues even in Silent Mode), whereas targeting `[Auto Pixel Mapping]`
     (`Off`) deterministically suppresses power-off mechanical shutter dark-frame
     actuation and prevents unscheduled `cnflasha` calibration touches during
     controlled bench shutdowns.
   - **Hardware `[Shutter When Pwr OFF]` Absence on `ILME-FX3` (`Ver. 2.00..7.02`)**:
     Physical `ILME-FX3` (`Ver. 2.00..7.02`) exposes only `[Sensor Cleaning]`,
     `[Auto Pixel Mapping]`, and `[Pixel Mapping]` in `Setup` — it does **NOT**
     expose `[Shutter When Pwr OFF]`. Rejects any fabricated `[Shutter When Pwr OFF]`
     menu item or `[Target Function Settings]` assertion fail-closed.

2. **Gate `G86` (`MARKER_15RATIO_NONRESET_HDMI_ISOLATION_AND_FLEXIBLE_EXP_RESET_SPLIT_GUARD`)**:
   - **`[Marker Display]` (`MENU -> Shooting -> [Marker Display]`) & All 15 `Ver. 3.00+/7.02` `[Aspect Marker]` Ratios**:
     Validates `[Marker Display]` (`Off`/`On`), `[Center Marker]` (`Off`/`On`),
     `[Aspect Marker]` (`Off` + all 15 `Ver. 3.00+/7.02` ratios: `9:16`, `4:5`,
     `1:1`, `4:3`, `13:9`, `14:9`, `15:9`, `16:9` [`Ver. 3.00+`], `17:9`, `1.66:1`,
     `1.85:1`, `1.91:1`, `2:1`, `2.35:1`, `2.39:1`), `[Safety Zone]` (`Off`/`80%`/`90%`),
     and `[Guideframe]` (`Off`/`On`).
   - **Local-LCD-Only HDMI Clean-Feed Isolation & Non-Resettable Persistence**:
     Enforces `0` external HDMI marker output (`hdmi_marker_overlay_rendered == False`)
     even when `[HDMI Info. Display] = [On]` (which also blanks the camera's
     built-in LCD panel), and enforces survival of `[Marker Display]` /
     `[Aspect Marker]` across `[Camera Settings Reset]` (cleared to `Off` only by
     `[Initialize]`).
   - **`[Exposure Ctrl Type]` (`P/A/S/M Mode` vs `Flexible Exp. Mode`) Reset Split**:
     Models `[Auto/Manual Swt. Set.]` (`Av`, `Tv`, `ISO` all factory-default
     `Manual`) and `[Auto Slow Shutter]` (factory-default `On`), enforcing that
     both `[Auto/Manual Swt. Set.]` (`-> Manual`) and `[Auto Slow Shutter]`
     (`-> On`) **ARE reset** by `[Camera Settings Reset]`, directly contrasting
     with non-resettable `[Marker Display]` / `[Aspect Marker]`.

3. **Unified 86-Gate Master Safety Preflight (`evaluate_86gate_preflight`)**:
   - Delegates `G01..G84` directly to `evaluate_84gate_preflight()`.
   - Offline default mode: `83/86` pass (`G01..G09`, `G13..G86` pass; `G10..G12`
     await physical Tier-0 receipt -> `overall_ready_for_hardware_attach = False`).
   - `--simulate-bench-dry-run` mode: `86/86` rehearsal pass while keeping all
     hardware write / live-attach redlines (`persistent_emmc_writes_authorized`,
     `hardware_live_attachment_authorized`, `spi_nor_write_authorized`,
     `el3_payload_transmit_authorized`, `overall_ready_for_hardware_attach`)
     hard-locked `False`.

Strictly stdlib-only Python 3.9+, `os.O_RDONLY` local donor inspection bounded to
`< 0.15s` with `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback, zero proprietary
firmware bytes leaked (`raw_firmware_bytes_leaked == 0`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    ENV_FORCE_CLEAN_ROOM,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_VERIFIED_SAFE,
    GateVerdict,
)
from .realhw_cfexpress_ufu_el3_and_52gate_guard import EL3_PAYLOAD_TRANSMIT_AUTHORIZED
from .realhw_dualmedia_bench_interlock_and_58gate_guard import (
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
)
from .realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard import (
    _DONOR_BLOB_CACHE,
)
from .realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import SPI_NOR_WRITE_AUTHORIZED
from .realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard import (
    Master84GateReport,
    evaluate_84gate_preflight,
)
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_SILENT_AUTOPIXELMAP_MARKER_FLEXEXP_86GATE_SCHEMA: str = (
    "fx3-realhw-silent-autopixelmap-marker-flexexp-86gate-v1"
)
REALHW_SILENT_AUTOPIXELMAP_MARKER_FLEXEXP_86GATE_VERSION: str = "1.0.0"

G85_GATE_ID: str = "G85_silent_mode_autopixelmap_target_and_no_pwrshutter_guard"
G85_GATE_CODE: str = (
    "SILENT_MODE_AUTOPIXELMAP_TARGET_5LOCK_AND_NO_SHUTTER_WHEN_PWR_OFF_GUARD"
)

G86_GATE_ID: str = (
    "G86_marker_15ratio_hdmi_isolation_and_flexexp_reset_split_guard"
)
G86_GATE_CODE: str = (
    "MARKER_15RATIO_NONRESET_HDMI_ISOLATION_AND_FLEXIBLE_EXP_RESET_SPLIT_GUARD"
)

G85: str = G85_GATE_ID
G86: str = G86_GATE_ID
GATE_G85_SILENT_MODE_AUTOPIXELMAP_TARGET_5LOCK_AND_NO_SHUTTER_WHEN_PWR_OFF_GUARD: str = (
    G85_GATE_CODE
)
GATE_G86_MARKER_15RATIO_NONRESET_HDMI_ISOLATION_AND_FLEXIBLE_EXP_RESET_SPLIT_GUARD: str = (
    G86_GATE_CODE
)

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS: float = 0.15

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX3_DEFAULT_FW_VERSION_PHASE230: str = "7.02"
FX3_MIN_SUPPORTED_FW_TUPLE_G85: Tuple[int, int] = (2, 0)
FX3_ASPECT_MARKER_16_9_MIN_FW_TUPLE: Tuple[int, int] = (3, 0)

# Status & Violation Codes
STATUS_VERIFIED_G85: str = (
    "VERIFIED_G85_SILENT_AUTOPIXELMAP_TARGET_AND_NO_SHUTTER_WHEN_PWR_OFF_SAFE"
)
STATUS_VERIFIED_G86: str = (
    "VERIFIED_G86_MARKER_15RATIO_HDMI_ISOLATION_AND_FLEXEXP_RESET_SPLIT_SAFE"
)

STATUS_BLOCKED_PHASE230_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE230_DONOR_CONTRACT_INTEGRITY"
)
STATUS_BLOCKED_G85_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCK_VIOLATION: str = (
    "BLOCKED_G85_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCK_VIOLATION"
)
STATUS_BLOCKED_G85_TARGET_FUNCTION_AUTOPIXELMAP_OR_APERTURE_VIOLATION: str = (
    "BLOCKED_G85_TARGET_FUNCTION_AUTOPIXELMAP_OR_APERTURE_VIOLATION"
)
STATUS_BLOCKED_G85_FABRICATED_SHUTTER_WHEN_PWR_OFF_MENU_CLAIM: str = (
    "BLOCKED_G85_FABRICATED_SHUTTER_WHEN_PWR_OFF_MENU_CLAIM"
)
STATUS_BLOCKED_G85_TELEMETRY_INVALID: str = (
    "BLOCKED_G85_SILENT_AUTOPIXELMAP_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G86_MARKER_DISPLAY_OR_15RATIO_INVALID: str = (
    "BLOCKED_G86_MARKER_DISPLAY_OR_15RATIO_INVALID"
)
STATUS_BLOCKED_G86_HDMI_MARKER_OVERLAY_LEAK: str = (
    "BLOCKED_G86_HDMI_MARKER_OVERLAY_LEAK"
)
STATUS_BLOCKED_G86_MARKER_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G86_MARKER_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G86_FLEXIBLE_EXP_AV_TV_ISO_OR_AUTOSLOW_RESET_SPLIT_VIOLATION: str = (
    "BLOCKED_G86_FLEXIBLE_EXP_AV_TV_ISO_OR_AUTOSLOW_RESET_SPLIT_VIOLATION"
)
STATUS_BLOCKED_G86_TELEMETRY_INVALID: str = (
    "BLOCKED_G86_MARKER_FLEXEXP_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G85 Canonical Constants: [Silent Mode Settings], [Target Function Settings],
# 5-Function Lockout & Physical [Shutter When Pwr OFF] Absence
# ---------------------------------------------------------------------------

SILENT_MODE_SETTINGS_MENU_PATH: str = (
    "MENU -> Shooting -> [Shutter/Silent] -> [Silent Mode Settings]"
)
TARGET_FUNCTION_SETTINGS_MENU_PATH: str = (
    "MENU -> Shooting -> [Shutter/Silent] -> [Silent Mode Settings] -> [Target Function Settings]"
)

SILENT_MODE_OFF: str = "Off"
SILENT_MODE_ON: str = "On"
ALLOWED_SILENT_MODES: Tuple[str, ...] = (SILENT_MODE_OFF, SILENT_MODE_ON)
SILENT_MODE_FACTORY_DEFAULT: str = SILENT_MODE_OFF

SHUTTER_TYPE_AUTO: str = "Auto"
SHUTTER_TYPE_MECHANICAL: str = "Mechanical Shutter"
SHUTTER_TYPE_ELECTRONIC: str = "Electronic Shutter"
ALLOWED_SHUTTER_TYPES: Tuple[str, ...] = (
    SHUTTER_TYPE_AUTO,
    SHUTTER_TYPE_MECHANICAL,
    SHUTTER_TYPE_ELECTRONIC,
)

AUDIO_SIGNALS_ON_ALL: str = "On: all"
AUDIO_SIGNALS_ON_SHUTTER_ONLY: str = "On: shutter only"
AUDIO_SIGNALS_OFF: str = "Off"
ALLOWED_AUDIO_SIGNALS_MODES: Tuple[str, ...] = (
    AUDIO_SIGNALS_ON_ALL,
    AUDIO_SIGNALS_ON_SHUTTER_ONLY,
    AUDIO_SIGNALS_OFF,
)

SILENT_MODE_DISABLED_FUNC_FLASH: str = "Flash"
SILENT_MODE_DISABLED_FUNC_LONG_EXP_NR: str = "Long Exposure NR"
SILENT_MODE_DISABLED_FUNC_E_FRONT_CURTAIN: str = "e-Front Curtain Shut."
SILENT_MODE_DISABLED_FUNC_BULB: str = "BULB"
SILENT_MODE_DISABLED_FUNC_ANTI_FLICKER: str = "Anti-flicker Shoot."

SILENT_MODE_5_DISABLED_FUNCTIONS: Tuple[str, ...] = (
    SILENT_MODE_DISABLED_FUNC_FLASH,
    SILENT_MODE_DISABLED_FUNC_LONG_EXP_NR,
    SILENT_MODE_DISABLED_FUNC_E_FRONT_CURTAIN,
    SILENT_MODE_DISABLED_FUNC_BULB,
    SILENT_MODE_DISABLED_FUNC_ANTI_FLICKER,
)

APERTURE_DRIVE_STANDARD: str = "Standard"
APERTURE_DRIVE_FOCUS_PRIORITY: str = "Focus Priority"
APERTURE_DRIVE_SILENT_PRIORITY: str = "Silent Priority"
TARGET_NOT_TARGET: str = "Not Target"

ALLOWED_NORMAL_APERTURE_DRIVE_MODES: Tuple[str, ...] = (
    APERTURE_DRIVE_STANDARD,
    APERTURE_DRIVE_FOCUS_PRIORITY,
    APERTURE_DRIVE_SILENT_PRIORITY,
)
ALLOWED_APERTURE_DRIVE_TARGET_SETTINGS: Tuple[str, ...] = (
    TARGET_NOT_TARGET,
    APERTURE_DRIVE_STANDARD,
    APERTURE_DRIVE_FOCUS_PRIORITY,
    APERTURE_DRIVE_SILENT_PRIORITY,
)

AUTO_PIXEL_MAPPING_ON: str = "On"
AUTO_PIXEL_MAPPING_OFF: str = "Off"
ALLOWED_NORMAL_AUTO_PIXEL_MAPPING_MODES: Tuple[str, ...] = (
    AUTO_PIXEL_MAPPING_ON,
    AUTO_PIXEL_MAPPING_OFF,
)
ALLOWED_AUTO_PIXEL_MAPPING_TARGET_SETTINGS: Tuple[str, ...] = (
    AUTO_PIXEL_MAPPING_OFF,
    TARGET_NOT_TARGET,
)

FX3_EXPOSED_SENSOR_SETUP_ITEMS: Tuple[str, ...] = (
    "Sensor Cleaning",
    "Auto Pixel Mapping",
    "Pixel Mapping",
)
FABRICATED_SHUTTER_WHEN_PWR_OFF_ITEM: str = "Shutter When Pwr OFF"

# ---------------------------------------------------------------------------
# Gate G86 Canonical Constants: [Marker Display] 15-Ratio Persistence,
# Local-LCD-Only HDMI Isolation & [Flexible Exp. Mode] Reset Split
# ---------------------------------------------------------------------------

MARKER_DISPLAY_MENU_PATH: str = "MENU -> Shooting -> [Marker Display]"
EXPOSURE_CTRL_TYPE_MENU_PATH: str = (
    "MENU -> Shooting -> [Shooting Mode] -> [Exposure Ctrl Type]"
)

MARKER_OFF: str = "Off"
MARKER_ON: str = "On"
ALLOWED_MARKER_ON_OFF_MODES: Tuple[str, ...] = (MARKER_OFF, MARKER_ON)

FX3_ASPECT_MARKER_15_RATIOS: Tuple[str, ...] = (
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
ALLOWED_ASPECT_MARKER_SETTINGS: Tuple[str, ...] = (
    MARKER_OFF,
) + FX3_ASPECT_MARKER_15_RATIOS

SAFETY_ZONE_OFF: str = "Off"
SAFETY_ZONE_80_PCT: str = "80%"
SAFETY_ZONE_90_PCT: str = "90%"
ALLOWED_SAFETY_ZONE_SETTINGS: Tuple[str, ...] = (
    SAFETY_ZONE_OFF,
    SAFETY_ZONE_80_PCT,
    SAFETY_ZONE_90_PCT,
)

GUIDEFRAME_OFF: str = "Off"
GUIDEFRAME_ON: str = "On"
ALLOWED_GUIDEFRAME_SETTINGS: Tuple[str, ...] = (GUIDEFRAME_OFF, GUIDEFRAME_ON)

MARKER_FACTORY_DEFAULT_DISPLAY: str = MARKER_OFF
MARKER_FACTORY_DEFAULT_CENTER: str = MARKER_OFF
MARKER_FACTORY_DEFAULT_ASPECT: str = MARKER_OFF
MARKER_FACTORY_DEFAULT_SAFETY_ZONE: str = SAFETY_ZONE_OFF
MARKER_FACTORY_DEFAULT_GUIDEFRAME: str = GUIDEFRAME_OFF

EXPOSURE_CTRL_PASM_MODE: str = "P/A/S/M Mode"
EXPOSURE_CTRL_FLEXIBLE_EXP_MODE: str = "Flexible Exp. Mode"
ALLOWED_EXPOSURE_CTRL_TYPES: Tuple[str, ...] = (
    EXPOSURE_CTRL_PASM_MODE,
    EXPOSURE_CTRL_FLEXIBLE_EXP_MODE,
)

PASM_PROGRAM_AUTO: str = "Program Auto"
PASM_APERTURE_PRIORITY: str = "Aperture Priority"
PASM_SHUTTER_PRIORITY: str = "Shutter Priority"
PASM_MANUAL_EXPOSURE: str = "Manual Exposure"
ALLOWED_PASM_SUBMODES: Tuple[str, ...] = (
    PASM_PROGRAM_AUTO,
    PASM_APERTURE_PRIORITY,
    PASM_SHUTTER_PRIORITY,
    PASM_MANUAL_EXPOSURE,
)

FLEX_EXP_MANUAL: str = "Manual"
FLEX_EXP_AUTO: str = "Auto"
ALLOWED_FLEX_EXP_SW_MODES: Tuple[str, ...] = (FLEX_EXP_MANUAL, FLEX_EXP_AUTO)
FLEX_EXP_FACTORY_DEFAULT_AV: str = FLEX_EXP_MANUAL
FLEX_EXP_FACTORY_DEFAULT_TV: str = FLEX_EXP_MANUAL
FLEX_EXP_FACTORY_DEFAULT_ISO: str = FLEX_EXP_MANUAL

AUTO_SLOW_SHUTTER_ON: str = "On"
AUTO_SLOW_SHUTTER_OFF: str = "Off"
ALLOWED_AUTO_SLOW_SHUTTER_MODES: Tuple[str, ...] = (
    AUTO_SLOW_SHUTTER_ON,
    AUTO_SLOW_SHUTTER_OFF,
)
AUTO_SLOW_SHUTTER_FACTORY_DEFAULT: str = AUTO_SLOW_SHUTTER_ON

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "CAMERA_SETTINGS_RESET"
RESET_ACTION_INITIALIZE: str = "INITIALIZE"
ALLOWED_RESET_ACTIONS_G86: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
)

# Pinned FX3 v7.02 & FX6 v6.01 Donor Specs (bounded <0.15s O_RDONLY verification)
PINNED_PHASE230_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"Silent",
            b"Pixel",
            b"Shutter",
            b"Marker",
            b"Aspect",
            b"Flexible",
            b"Exposure",
            b"Audio",
            b"HDMI",
            b"Reset",
            b"Manual",
            b"Auto",
            b"Slow",
            b"Center",
            b"16:9",
            b"BK4",
            b"/setting",
        ),
        "fx3/cpapp-b.bin::{15980568B,ILME-FX3,Silent,Pixel,Shutter,Marker,Aspect,Flexible,Exposure,Audio,HDMI,Reset,Manual,Auto,Slow,Center,16:9}",
    ),
    "fx3_saveload_so": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (b"\x7fELF", b"SaveLoadSettings", b"Settings", b"Save", b"Backup"),
        "fx3/libSaveLoadSettings.so::{18760B,ELF,SaveLoadSettings,Settings,Save,Backup}",
    ),
    "fx3_bk4_bin": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"FTP", b"TC", b"/setting"),
        "fx3/FX3-CX95900_ALLLANG-Backup.bin::{2229740B,BK4,ILME-FX3,FTP,TC,/setting}",
    ),
    "fx6_bk4_bin": (
        "fx6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"NTSC", b"TC", b"Settings", b"/setting"),
        "fx6/CX95898_NTSC.bin::{2253333B,BK4,NTSC,TC,Settings,/setting}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase230DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    elapsed_seconds: float
    within_budget_150ms: bool
    raw_firmware_bytes_leaked: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    fx6_contracts_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SilentModeAutoPixelMapNoPwrShutterResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    firmware_version: str
    silent_mode: str
    effective_shutter_type: str
    effective_shutter_type_in_interval: str
    effective_audio_signals: str
    disabled_5_functions_expected: Tuple[str, ...]
    all_5_functions_disabled_in_silent: bool
    normal_aperture_drive_in_af: str
    target_aperture_drive_in_af: str
    effective_aperture_drive_in_af: str
    aperture_drive_not_target_retains_normal: bool
    normal_auto_pixel_mapping: str
    target_auto_pixel_mapping: str
    auto_pixel_mapping_targeted_in_silent: bool
    auto_pixel_mapping_not_target_retains_normal: bool
    effective_power_off_auto_pixel_mapping_active: bool
    power_off_mechanical_shutter_sound_expected: bool
    power_off_cnflasha_calibration_touch: bool
    bench_shutdown_require_autopixelmap_suppression: bool
    bench_shutdown_autopixelmap_suppressed: bool
    exposed_sensor_setup_items: Tuple[str, ...]
    shutter_when_pwr_off_menu_claimed: bool
    shutter_when_pwr_off_in_target_functions: bool
    shutter_when_pwr_off_absent_verified: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Marker15RatioHdmiAndFlexExpResetSplitResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    firmware_version: str
    pre_reset_marker_display: str
    pre_reset_center_marker: str
    pre_reset_aspect_marker: str
    pre_reset_safety_zone: str
    pre_reset_guideframe: str
    supported_aspect_marker_15_ratios: Tuple[str, ...]
    aspect_marker_15_ratio_count: int
    any_marker_subitem_enabled: bool
    hdmi_info_display_on: bool
    camera_lcd_blanked_by_hdmi_info: bool
    local_lcd_marker_rendered: bool
    hdmi_marker_overlay_rendered: bool
    external_hdmi_marker_count: int
    hdmi_marker_isolation_enforced: bool
    reset_action: str
    expected_post_reset_marker_display: str
    expected_post_reset_center_marker: str
    expected_post_reset_aspect_marker: str
    expected_post_reset_safety_zone: str
    expected_post_reset_guideframe: str
    effective_post_reset_marker_display: str
    effective_post_reset_center_marker: str
    effective_post_reset_aspect_marker: str
    effective_post_reset_safety_zone: str
    effective_post_reset_guideframe: str
    marker_survived_camera_settings_reset: bool
    exposure_ctrl_type: str
    pasm_submode: str
    pre_reset_flex_av_mode: str
    pre_reset_flex_tv_mode: str
    pre_reset_flex_iso_mode: str
    pre_reset_auto_slow_shutter: str
    expected_post_reset_flex_av_mode: str
    expected_post_reset_flex_tv_mode: str
    expected_post_reset_flex_iso_mode: str
    expected_post_reset_auto_slow_shutter: str
    effective_post_reset_flex_av_mode: str
    effective_post_reset_flex_tv_mode: str
    effective_post_reset_flex_iso_mode: str
    effective_post_reset_auto_slow_shutter: str
    flex_exp_reset_by_camera_settings_reset: bool
    marker_vs_flexexp_reset_split_verified: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G85SilentAutoPixelMapNoPwrShutterGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    silent_autopixelmap_no_pwrshutter_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G86MarkerHdmiAndFlexExpResetSplitGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    marker_hdmi_flexexp_reset_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master86GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_83_gates_verified: bool
    all_86_gates_verified: bool
    g13_to_g86_all_passed: bool
    g85_to_g86_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_84_report: Dict[str, Any]
    g85_result: Dict[str, Any]
    g86_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers & Normalization
# ---------------------------------------------------------------------------


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip() in (
        "1",
        "true",
        "TRUE",
        "yes",
        "YES",
    )


def _read_file_o_rdonly(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    fd = os.open(str(path), flags)
    chunks: List[bytes] = []
    try:
        while True:
            buf = os.read(fd, 1 << 20)
            if not buf:
                break
            chunks.append(buf)
    finally:
        os.close(fd)
    return b"".join(chunks)


def _read_cached_donor_o_rdonly(path: Path) -> Tuple[int, str, bytes]:
    key = str(path.resolve())
    st = os.stat(key)
    cached = _DONOR_BLOB_CACHE.get(key)
    if cached is not None and cached[0] == st.st_size and cached[1] == st.st_mtime:
        return cached[2], cached[3], cached[4]
    blob = _read_file_o_rdonly(path)
    sha = hashlib.sha256(blob).hexdigest()
    _DONOR_BLOB_CACHE[key] = (st.st_size, st.st_mtime, len(blob), sha, blob)
    return len(blob), sha, blob


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _norm_token(val: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", (val or "").strip().upper()).strip("_")


def _parse_fw_tuple(fw_str: str) -> Optional[Tuple[int, int]]:
    m = re.match(r"^\s*[vV]?(\d+)\.(\d+)(?:\.\d+)?\s*$", (fw_str or "").strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _norm_on_off(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t == "ON":
        return "On"
    if t == "OFF":
        return "Off"
    return None


def _norm_shutter_type(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t in ("AUTO", "AUTO_SHUTTER"):
        return SHUTTER_TYPE_AUTO
    if t in ("MECHANICAL_SHUTTER", "MECHANICAL"):
        return SHUTTER_TYPE_MECHANICAL
    if t in ("ELECTRONIC_SHUTTER", "ELECTRONIC"):
        return SHUTTER_TYPE_ELECTRONIC
    return None


def _norm_audio_signals(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t == "OFF":
        return AUDIO_SIGNALS_OFF
    if t in ("ON_ALL", "ON"):
        return AUDIO_SIGNALS_ON_ALL
    if t in ("ON_SHUTTER_ONLY", "SHUTTER_ONLY"):
        return AUDIO_SIGNALS_ON_SHUTTER_ONLY
    return None


def _norm_disabled_5_func(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t in ("FLASH", "FLASH_SHOOTING"):
        return SILENT_MODE_DISABLED_FUNC_FLASH
    if t in ("LONG_EXPOSURE_NR", "LONG_EXP_NR"):
        return SILENT_MODE_DISABLED_FUNC_LONG_EXP_NR
    if t in ("E_FRONT_CURTAIN_SHUT", "E_FRONT_CURTAIN_SHUTTER", "E_FRONT_CURTAIN"):
        return SILENT_MODE_DISABLED_FUNC_E_FRONT_CURTAIN
    if t in ("BULB", "BULB_SHOOTING"):
        return SILENT_MODE_DISABLED_FUNC_BULB
    if t in ("ANTI_FLICKER_SHOOT", "ANTI_FLICKER_SHOOTING", "ANTI_FLICKER"):
        return SILENT_MODE_DISABLED_FUNC_ANTI_FLICKER
    return None


def _norm_aperture_drive(val: str, *, allow_not_target: bool) -> Optional[str]:
    t = _norm_token(val)
    if allow_not_target and t in ("NOT_TARGET", "NOTTARGET"):
        return TARGET_NOT_TARGET
    if t == "STANDARD":
        return APERTURE_DRIVE_STANDARD
    if t == "FOCUS_PRIORITY":
        return APERTURE_DRIVE_FOCUS_PRIORITY
    if t == "SILENT_PRIORITY":
        return APERTURE_DRIVE_SILENT_PRIORITY
    return None


def _norm_auto_pixel_mapping_target(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t in ("OFF", "TARGET", "SUPPRESS", "TARGET_OFF"):
        return AUTO_PIXEL_MAPPING_OFF
    if t in ("NOT_TARGET", "NOTTARGET"):
        return TARGET_NOT_TARGET
    return None


def _norm_sensor_setup_item(val: str) -> str:
    t = _norm_token(val)
    if t in ("SENSOR_CLEANING", "ANTI_DUST_SENSOR_CLEANING"):
        return "Sensor Cleaning"
    if t == "AUTO_PIXEL_MAPPING":
        return "Auto Pixel Mapping"
    if t == "PIXEL_MAPPING":
        return "Pixel Mapping"
    if t in (
        "SHUTTER_WHEN_PWR_OFF",
        "SHUTTER_WHEN_POWER_OFF",
        "ANTI_DUST_SHUTTER_WHEN_PWR_OFF",
    ):
        return FABRICATED_SHUTTER_WHEN_PWR_OFF_ITEM
    return (val or "").strip()


def _norm_aspect_marker(val: str) -> Optional[str]:
    s = (val or "").strip()
    if _norm_token(s) == "OFF":
        return MARKER_OFF
    if s in FX3_ASPECT_MARKER_15_RATIOS:
        return s
    return None


def _norm_safety_zone(val: str) -> Optional[str]:
    s = (val or "").strip()
    t = _norm_token(s)
    if t == "OFF":
        return SAFETY_ZONE_OFF
    if s == "80%" or t in ("80", "80_PCT"):
        return SAFETY_ZONE_80_PCT
    if s == "90%" or t in ("90", "90_PCT"):
        return SAFETY_ZONE_90_PCT
    return None


def _norm_exposure_ctrl_type(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t in ("P_A_S_M_MODE", "PASM_MODE", "P_A_S_M"):
        return EXPOSURE_CTRL_PASM_MODE
    if t in ("FLEXIBLE_EXP_MODE", "FLEXIBLE_EXPOSURE_MODE", "FLEXIBLE_EXP"):
        return EXPOSURE_CTRL_FLEXIBLE_EXP_MODE
    return None


def _norm_pasm_submode(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t in ("PROGRAM_AUTO", "P"):
        return PASM_PROGRAM_AUTO
    if t in ("APERTURE_PRIORITY", "A"):
        return PASM_APERTURE_PRIORITY
    if t in ("SHUTTER_PRIORITY", "S"):
        return PASM_SHUTTER_PRIORITY
    if t in ("MANUAL_EXPOSURE", "M"):
        return PASM_MANUAL_EXPOSURE
    return None


def _norm_flex_sw_mode(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t == "MANUAL":
        return FLEX_EXP_MANUAL
    if t == "AUTO":
        return FLEX_EXP_AUTO
    return None


def _norm_reset_action(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t in ("NONE", "NO_RESET"):
        return RESET_ACTION_NONE
    if t in ("CAMERA_SETTINGS_RESET", "CAM_SETTINGS_RESET"):
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if t in ("INITIALIZE", "FACTORY_INITIALIZE"):
        return RESET_ACTION_INITIALIZE
    return None


# ---------------------------------------------------------------------------
# 1. Bounded `<0.15s` O_RDONLY Local Donor Audit (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
# ---------------------------------------------------------------------------


def audit_phase230_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS,
) -> Phase230DonorAuditResult:
    """Bounded `<0.15s` `O_RDONLY` local donor contract check with deterministic
    `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback (`raw_firmware_bytes_leaked == 0`).
    """
    t0 = time.perf_counter()
    clean_forced = _is_forced_clean_room(force_clean_room)
    resolved_repo = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    paths = resolve_donor_thermal_power_paths(
        work_root=work_root, repo_root=resolved_repo
    )
    effective_work_root: Optional[Path] = (
        Path(work_root) if work_root is not None else paths.work_root
    )

    resolved: Dict[str, Path] = {}
    if effective_work_root is not None:
        for key, (_body, rel_path, *_rest) in PINNED_PHASE230_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        elapsed = time.perf_counter() - t0
        within_budget = elapsed < max_budget_seconds
        return Phase230DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE230_DONOR_INTEGRITY
            ),
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_150ms=within_budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE230_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=within_budget,
            fx6_contracts_verified=within_budget,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE230_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE230_DONOR_SPECS.items()
            },
            errors=()
            if within_budget
            else (
                f"Clean-room donor check exceeded budget ({elapsed:.4f}s >= {max_budget_seconds:.4f}s).",
            ),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []
    passed_keys: Set[str] = set()
    files_inspected = 0

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE230_DONOR_SPECS.items():
        size_b, sha, blob = _read_cached_donor_o_rdonly(resolved[key])
        files_inspected += 1
        shas[key] = sha
        sizes[key] = size_b

        missing_for_file = [m for m in marker_tuple if m not in blob]
        integrity_ok = size_b == exp_size and sha == exp_sha
        if not missing_for_file:
            checked.append(marker_label)
        else:
            missing.append(marker_label)
            errors.append(
                f"Donor {key} missing {len(missing_for_file)} required marker(s) for {marker_label}."
            )
        if not integrity_ok:
            errors.append(
                f"Donor {key} integrity mismatch: size={size_b} (expected {exp_size}), "
                f"sha256={sha} (expected {exp_sha})."
            )
        if not missing_for_file and integrity_ok:
            passed_keys.add(key)

    elapsed = time.perf_counter() - t0
    within_budget = elapsed < max_budget_seconds
    if not within_budget:
        errors.append(
            f"Local O_RDONLY donor audit exceeded {max_budget_seconds:.3f}s budget ({elapsed:.4f}s)."
        )

    fx3_ok = all(
        k in passed_keys
        for k, s in PINNED_PHASE230_DONOR_SPECS.items()
        if s[0] == "fx3"
    )
    fx6_ok = all(
        k in passed_keys
        for k, s in PINNED_PHASE230_DONOR_SPECS.items()
        if s[0] == "fx6"
    )
    valid = fx3_ok and fx6_ok and within_budget and (not errors)
    return Phase230DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE
            if valid
            else STATUS_BLOCKED_PHASE230_DONOR_INTEGRITY
        ),
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_150ms=within_budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_ok,
        fx6_contracts_verified=fx6_ok,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate G85: [Silent Mode Settings] [Auto Pixel Mapping] Suppression Target,
#    5-Function Lockout & Hardware [Shutter When Pwr OFF] Absence Guard
# ---------------------------------------------------------------------------


def resolve_fx3_silent_mode_and_target_functions(
    *,
    silent_mode: str = SILENT_MODE_ON,
    normal_shutter_type: str = SHUTTER_TYPE_AUTO,
    normal_shutter_type_in_interval: str = SHUTTER_TYPE_AUTO,
    normal_audio_signals: str = AUDIO_SIGNALS_ON_ALL,
    normal_aperture_drive_in_af: str = APERTURE_DRIVE_STANDARD,
    target_aperture_drive_in_af: str = APERTURE_DRIVE_SILENT_PRIORITY,
    normal_auto_pixel_mapping: str = AUTO_PIXEL_MAPPING_ON,
    target_auto_pixel_mapping: str = AUTO_PIXEL_MAPPING_OFF,
) -> Dict[str, Any]:
    """Resolve `ILME-FX3` (`Ver. 7.02`) `[Silent Mode Settings]` and
    `[Target Function Settings]` runtime state:

    - `[Silent Mode] = [On]`:
      - Locks `[Shutter Type]` & `[Shutter Type in Interval]` to `[Electronic Shutter]`.
      - Locks `[Audio signals]` to `[Off]`.
      - Disables all 5 functions (`Flash`, `Long Exposure NR`, `e-Front Curtain Shut.`,
        `BULB`, `Anti-flicker Shoot.`).
    - `[Target Function Settings]`:
      - `[Aperture Drive in AF]`: `[Not Target]` retains `normal_aperture_drive_in_af`;
        selecting a target mode overrides `[Aperture Drive in AF]` while `[Silent Mode] = [On]`.
      - `[Auto Pixel Mapping]`: `[Not Target]` retains `normal_auto_pixel_mapping`
        (so power-off mechanical shutter actuation still fires if `normal == On`);
        targeting `[Auto Pixel Mapping]` (`Off`) suppresses power-off mechanical
        shutter dark-frame actuation and `cnflasha` calibration touches while
        `[Silent Mode] = [On]`.
    """
    canon_silent = _norm_on_off(silent_mode)
    canon_shutter = _norm_shutter_type(normal_shutter_type)
    canon_interval_shutter = _norm_shutter_type(normal_shutter_type_in_interval)
    canon_audio = _norm_audio_signals(normal_audio_signals)
    canon_norm_ap = _norm_aperture_drive(
        normal_aperture_drive_in_af, allow_not_target=False
    )
    canon_tgt_ap = _norm_aperture_drive(
        target_aperture_drive_in_af, allow_not_target=True
    )
    canon_norm_apm = _norm_on_off(normal_auto_pixel_mapping)
    canon_tgt_apm = _norm_auto_pixel_mapping_target(target_auto_pixel_mapping)

    is_silent = canon_silent == SILENT_MODE_ON

    expected_shutter = (
        SHUTTER_TYPE_ELECTRONIC
        if is_silent
        else (canon_shutter or SHUTTER_TYPE_AUTO)
    )
    expected_interval_shutter = (
        SHUTTER_TYPE_ELECTRONIC
        if is_silent
        else (canon_interval_shutter or SHUTTER_TYPE_AUTO)
    )
    expected_audio = (
        AUDIO_SIGNALS_OFF
        if is_silent
        else (canon_audio or AUDIO_SIGNALS_ON_ALL)
    )
    expected_disabled_funcs: Tuple[str, ...] = (
        SILENT_MODE_5_DISABLED_FUNCTIONS if is_silent else ()
    )

    ap_not_target = canon_tgt_ap == TARGET_NOT_TARGET
    if is_silent and (not ap_not_target) and canon_tgt_ap is not None:
        expected_ap = canon_tgt_ap
    else:
        expected_ap = canon_norm_ap or APERTURE_DRIVE_STANDARD

    apm_not_target = canon_tgt_apm == TARGET_NOT_TARGET
    apm_targeted_in_silent = is_silent and (canon_tgt_apm == AUTO_PIXEL_MAPPING_OFF)
    norm_apm_on = canon_norm_apm == AUTO_PIXEL_MAPPING_ON
    expected_power_off_apm_active = norm_apm_on and (not apm_targeted_in_silent)

    return {
        "canonical_silent_mode": canon_silent,
        "canonical_normal_shutter": canon_shutter,
        "canonical_normal_interval_shutter": canon_interval_shutter,
        "canonical_normal_audio_signals": canon_audio,
        "canonical_normal_aperture_drive": canon_norm_ap,
        "canonical_target_aperture_drive": canon_tgt_ap,
        "canonical_normal_auto_pixel_mapping": canon_norm_apm,
        "canonical_target_auto_pixel_mapping": canon_tgt_apm,
        "expected_shutter_type": expected_shutter,
        "expected_shutter_type_in_interval": expected_interval_shutter,
        "expected_audio_signals": expected_audio,
        "expected_disabled_5_functions": expected_disabled_funcs,
        "expected_aperture_drive_in_af": expected_ap,
        "aperture_drive_not_target": ap_not_target,
        "auto_pixel_mapping_not_target": apm_not_target,
        "auto_pixel_mapping_targeted_in_silent": apm_targeted_in_silent,
        "expected_power_off_auto_pixel_mapping_active": expected_power_off_apm_active,
        "expected_power_off_shutter_sound": expected_power_off_apm_active,
    }


def verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE230,
    silent_mode: str = SILENT_MODE_ON,
    normal_shutter_type: str = SHUTTER_TYPE_AUTO,
    normal_shutter_type_in_interval: str = SHUTTER_TYPE_AUTO,
    normal_audio_signals: str = AUDIO_SIGNALS_ON_ALL,
    effective_shutter_type: Optional[str] = None,
    effective_shutter_type_in_interval: Optional[str] = None,
    effective_audio_signals: Optional[str] = None,
    disabled_functions_in_silent: Optional[Sequence[str]] = None,
    enabled_function_attempted_in_silent: Optional[str] = None,
    normal_aperture_drive_in_af: str = APERTURE_DRIVE_STANDARD,
    target_aperture_drive_in_af: str = APERTURE_DRIVE_SILENT_PRIORITY,
    effective_aperture_drive_in_af: Optional[str] = None,
    normal_auto_pixel_mapping: str = AUTO_PIXEL_MAPPING_ON,
    target_auto_pixel_mapping: str = AUTO_PIXEL_MAPPING_OFF,
    effective_power_off_auto_pixel_mapping_active: Optional[bool] = None,
    power_off_mechanical_shutter_sound_expected: Optional[bool] = None,
    power_off_cnflasha_calibration_touch: bool = False,
    bench_shutdown_require_autopixelmap_suppression: bool = True,
    claimed_sensor_setup_items: Sequence[str] = FX3_EXPOSED_SENSOR_SETUP_ITEMS,
    shutter_when_pwr_off_menu_claimed: bool = False,
    shutter_when_pwr_off_in_target_functions: bool = False,
    shutter_when_pwr_off_setting: Optional[str] = None,
) -> SilentModeAutoPixelMapNoPwrShutterResult:
    """Verify Gate `G85`: `ILME-FX3` (`Ver. 7.02`) `[Silent Mode Settings]`
    `[Auto Pixel Mapping]` suppression target, 5-function lockout (`Flash`,
    `Long Exposure NR`, `e-Front Curtain Shut.`, `BULB`, `Anti-flicker Shoot.`),
    and physical absence of `[Shutter When Pwr OFF]` across `Ver. 2.00..7.02`.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name.strip().upper() != FX3_MODEL_NAME
        or int(body_model_id) != FX3_MODEL_ID
    ):
        _add_code(codes, STATUS_BLOCKED_G85_TELEMETRY_INVALID)
        errors.append(
            f"Body mismatch for G85: name={body_model_name!r}, id=0x{int(body_model_id):08X}."
        )

    fw_tuple = _parse_fw_tuple(firmware_version)
    if fw_tuple is None or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_G85:
        _add_code(codes, STATUS_BLOCKED_G85_TELEMETRY_INVALID)
        errors.append(
            f"Invalid or unsupported ILME-FX3 firmware_version={firmware_version!r} for Gate G85 (expected >= 2.00)."
        )

    resolved = resolve_fx3_silent_mode_and_target_functions(
        silent_mode=silent_mode,
        normal_shutter_type=normal_shutter_type,
        normal_shutter_type_in_interval=normal_shutter_type_in_interval,
        normal_audio_signals=normal_audio_signals,
        normal_aperture_drive_in_af=normal_aperture_drive_in_af,
        target_aperture_drive_in_af=target_aperture_drive_in_af,
        normal_auto_pixel_mapping=normal_auto_pixel_mapping,
        target_auto_pixel_mapping=target_auto_pixel_mapping,
    )

    canon_silent = resolved["canonical_silent_mode"]
    if (
        canon_silent is None
        or resolved["canonical_normal_shutter"] is None
        or resolved["canonical_normal_interval_shutter"] is None
        or resolved["canonical_normal_audio_signals"] is None
        or resolved["canonical_normal_aperture_drive"] is None
        or resolved["canonical_target_aperture_drive"] is None
        or resolved["canonical_normal_auto_pixel_mapping"] is None
        or resolved["canonical_target_auto_pixel_mapping"] is None
    ):
        _add_code(codes, STATUS_BLOCKED_G85_TELEMETRY_INVALID)
        errors.append(
            "Invalid enum in Gate G85 telemetry: "
            f"silent_mode={silent_mode!r}, normal_shutter={normal_shutter_type!r}, "
            f"interval_shutter={normal_shutter_type_in_interval!r}, audio={normal_audio_signals!r}, "
            f"norm_ap={normal_aperture_drive_in_af!r}, tgt_ap={target_aperture_drive_in_af!r}, "
            f"norm_apm={normal_auto_pixel_mapping!r}, tgt_apm={target_auto_pixel_mapping!r}."
        )

    is_silent = canon_silent == SILENT_MODE_ON

    # 1. [Silent Mode] = [On] -> Electronic Shutter + Audio signals Off + 5-Function Lockout
    eff_shutter = (
        resolved["expected_shutter_type"]
        if effective_shutter_type is None
        else (_norm_shutter_type(effective_shutter_type) or effective_shutter_type)
    )
    eff_interval_shutter = (
        resolved["expected_shutter_type_in_interval"]
        if effective_shutter_type_in_interval is None
        else (
            _norm_shutter_type(effective_shutter_type_in_interval)
            or effective_shutter_type_in_interval
        )
    )
    eff_audio = (
        resolved["expected_audio_signals"]
        if effective_audio_signals is None
        else (_norm_audio_signals(effective_audio_signals) or effective_audio_signals)
    )

    if disabled_functions_in_silent is None:
        canon_disabled_set: Set[str] = (
            set(SILENT_MODE_5_DISABLED_FUNCTIONS) if is_silent else set()
        )
        unknown_disabled: List[str] = []
    else:
        canon_disabled_set = set()
        unknown_disabled = []
        for item in disabled_functions_in_silent:
            nf = _norm_disabled_5_func(item)
            if nf is None:
                unknown_disabled.append(item)
            else:
                canon_disabled_set.add(nf)
        if unknown_disabled:
            _add_code(codes, STATUS_BLOCKED_G85_TELEMETRY_INVALID)
            errors.append(
                f"Unknown Silent Mode disabled function(s): {unknown_disabled!r}."
            )

    attempted_locked_func: Optional[str] = None
    if enabled_function_attempted_in_silent is not None:
        attempted_locked_func = _norm_disabled_5_func(
            enabled_function_attempted_in_silent
        )
        if attempted_locked_func is None:
            _add_code(codes, STATUS_BLOCKED_G85_TELEMETRY_INVALID)
            errors.append(
                f"Unknown enabled_function_attempted_in_silent={enabled_function_attempted_in_silent!r}."
            )

    all_5_disabled = (
        (canon_disabled_set == set(SILENT_MODE_5_DISABLED_FUNCTIONS))
        and (attempted_locked_func is None)
        if is_silent
        else (len(canon_disabled_set) == 0 and attempted_locked_func is None)
    )

    if is_silent and (
        eff_shutter != SHUTTER_TYPE_ELECTRONIC
        or eff_interval_shutter != SHUTTER_TYPE_ELECTRONIC
        or eff_audio != AUDIO_SIGNALS_OFF
        or not all_5_disabled
    ):
        _add_code(
            codes,
            STATUS_BLOCKED_G85_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCK_VIOLATION,
        )
        errors.append(
            "[Silent Mode]=[On] locks [Shutter Type] & [Shutter Type in Interval] to "
            "[Electronic Shutter], [Audio signals] to [Off], and disables all 5 functions "
            f"{SILENT_MODE_5_DISABLED_FUNCTIONS}: got shutter={eff_shutter!r}, "
            f"interval_shutter={eff_interval_shutter!r}, audio={eff_audio!r}, "
            f"disabled={sorted(canon_disabled_set)}, attempted={attempted_locked_func!r}."
        )
    elif (not is_silent) and (
        eff_shutter != resolved["expected_shutter_type"]
        or eff_interval_shutter != resolved["expected_shutter_type_in_interval"]
        or eff_audio != resolved["expected_audio_signals"]
        or bool(canon_disabled_set)
    ):
        _add_code(
            codes,
            STATUS_BLOCKED_G85_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCK_VIOLATION,
        )
        errors.append(
            f"[Silent Mode]=[Off] state mismatch: shutter={eff_shutter!r}, "
            f"interval_shutter={eff_interval_shutter!r}, audio={eff_audio!r}, "
            f"disabled={sorted(canon_disabled_set)}."
        )

    # 2. [Target Function Settings]: [Aperture Drive in AF] & [Auto Pixel Mapping]
    eff_ap = (
        resolved["expected_aperture_drive_in_af"]
        if effective_aperture_drive_in_af is None
        else (
            _norm_aperture_drive(effective_aperture_drive_in_af, allow_not_target=False)
            or effective_aperture_drive_in_af
        )
    )
    eff_apm_active = (
        bool(resolved["expected_power_off_auto_pixel_mapping_active"])
        if effective_power_off_auto_pixel_mapping_active is None
        else bool(effective_power_off_auto_pixel_mapping_active)
    )
    eff_shutter_sound = (
        bool(resolved["expected_power_off_shutter_sound"])
        if power_off_mechanical_shutter_sound_expected is None
        else bool(power_off_mechanical_shutter_sound_expected)
    )
    eff_cnflasha_touch = bool(power_off_cnflasha_calibration_touch)

    bench_suppressed = (not eff_apm_active) and (not eff_cnflasha_touch)

    if (
        eff_ap != resolved["expected_aperture_drive_in_af"]
        or eff_apm_active
        != bool(resolved["expected_power_off_auto_pixel_mapping_active"])
        or eff_shutter_sound != bool(resolved["expected_power_off_shutter_sound"])
        or eff_cnflasha_touch
        or (bool(bench_shutdown_require_autopixelmap_suppression) and not bench_suppressed)
    ):
        _add_code(
            codes,
            STATUS_BLOCKED_G85_TARGET_FUNCTION_AUTOPIXELMAP_OR_APERTURE_VIOLATION,
        )
        errors.append(
            "[Target Function Settings] ([Aperture Drive in AF] / [Auto Pixel Mapping]) "
            "or bench shutdown suppression violated: "
            f"eff_aperture={eff_ap!r} (expected {resolved['expected_aperture_drive_in_af']!r}), "
            f"eff_power_off_apm={eff_apm_active} (expected {resolved['expected_power_off_auto_pixel_mapping_active']}), "
            f"shutter_sound={eff_shutter_sound} (expected {resolved['expected_power_off_shutter_sound']}), "
            f"cnflasha_touch={eff_cnflasha_touch}, "
            f"bench_require_suppression={bool(bench_shutdown_require_autopixelmap_suppression)}."
        )

    # 3. Physical Absence of [Shutter When Pwr OFF] on ILME-FX3 (Ver. 2.00..7.02)
    canon_setup_items = tuple(_norm_sensor_setup_item(x) for x in claimed_sensor_setup_items)
    pwr_shutter_in_setup = FABRICATED_SHUTTER_WHEN_PWR_OFF_ITEM in canon_setup_items
    pwr_shutter_setting_tok = (
        _norm_token(shutter_when_pwr_off_setting)
        if shutter_when_pwr_off_setting is not None
        else ""
    )
    pwr_shutter_setting_claimed = pwr_shutter_setting_tok not in (
        "",
        "NONE",
        "ABSENT",
        "NOT_SUPPORTED_ON_FX3",
    )

    shutter_when_pwr_off_absent_ok = (
        (not bool(shutter_when_pwr_off_menu_claimed))
        and (not bool(shutter_when_pwr_off_in_target_functions))
        and (not pwr_shutter_in_setup)
        and (not pwr_shutter_setting_claimed)
        and set(canon_setup_items) == set(FX3_EXPOSED_SENSOR_SETUP_ITEMS)
    )
    if not shutter_when_pwr_off_absent_ok:
        _add_code(codes, STATUS_BLOCKED_G85_FABRICATED_SHUTTER_WHEN_PWR_OFF_MENU_CLAIM)
        errors.append(
            "Fabricated [Shutter When Pwr OFF] menu/target assertion rejected on physical "
            f"ILME-FX3 (Ver. 2.00..7.02 exposes ONLY {FX3_EXPOSED_SENSOR_SETUP_ITEMS}): "
            f"menu_claimed={bool(shutter_when_pwr_off_menu_claimed)}, "
            f"in_target_functions={bool(shutter_when_pwr_off_in_target_functions)}, "
            f"setting={shutter_when_pwr_off_setting!r}, setup_items={canon_setup_items}."
        )

    valid = not codes
    status = STATUS_VERIFIED_G85 if valid else codes[0]
    return SilentModeAutoPixelMapNoPwrShutterResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{int(body_model_id):08X}",
        firmware_version=firmware_version,
        silent_mode=canon_silent or silent_mode,
        effective_shutter_type=eff_shutter,
        effective_shutter_type_in_interval=eff_interval_shutter,
        effective_audio_signals=eff_audio,
        disabled_5_functions_expected=SILENT_MODE_5_DISABLED_FUNCTIONS,
        all_5_functions_disabled_in_silent=all_5_disabled,
        normal_aperture_drive_in_af=resolved["canonical_normal_aperture_drive"]
        or normal_aperture_drive_in_af,
        target_aperture_drive_in_af=resolved["canonical_target_aperture_drive"]
        or target_aperture_drive_in_af,
        effective_aperture_drive_in_af=eff_ap,
        aperture_drive_not_target_retains_normal=bool(
            resolved["aperture_drive_not_target"]
        ),
        normal_auto_pixel_mapping=resolved["canonical_normal_auto_pixel_mapping"]
        or normal_auto_pixel_mapping,
        target_auto_pixel_mapping=resolved["canonical_target_auto_pixel_mapping"]
        or target_auto_pixel_mapping,
        auto_pixel_mapping_targeted_in_silent=bool(
            resolved["auto_pixel_mapping_targeted_in_silent"]
        ),
        auto_pixel_mapping_not_target_retains_normal=bool(
            resolved["auto_pixel_mapping_not_target"]
        ),
        effective_power_off_auto_pixel_mapping_active=eff_apm_active,
        power_off_mechanical_shutter_sound_expected=eff_shutter_sound,
        power_off_cnflasha_calibration_touch=eff_cnflasha_touch,
        bench_shutdown_require_autopixelmap_suppression=bool(
            bench_shutdown_require_autopixelmap_suppression
        ),
        bench_shutdown_autopixelmap_suppressed=bench_suppressed,
        exposed_sensor_setup_items=FX3_EXPOSED_SENSOR_SETUP_ITEMS,
        shutter_when_pwr_off_menu_claimed=bool(shutter_when_pwr_off_menu_claimed),
        shutter_when_pwr_off_in_target_functions=bool(
            shutter_when_pwr_off_in_target_functions
        ),
        shutter_when_pwr_off_absent_verified=shutter_when_pwr_off_absent_ok,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g85_silent_autopixelmap_no_pwrshutter_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    silent_autopixelmap_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase230DonorAuditResult] = None,
) -> Tuple[GateVerdict, G85SilentAutoPixelMapNoPwrShutterGuardResult]:
    """Evaluate Gate `G85` combining bounded `<0.15s` donor check with `[Silent Mode Settings]`
    `[Auto Pixel Mapping]` suppression target, 5-function lockout, and `[Shutter When Pwr OFF]`
    hardware absence guard.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase230_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
        **dict(silent_autopixelmap_kwargs or {})
    )

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)
    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G85 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G85 if valid else codes[0]

    res = G85SilentAutoPixelMapNoPwrShutterGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        silent_autopixelmap_no_pwrshutter_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, silent={guard.silent_mode}"
        f"(shutter={guard.effective_shutter_type},audio={guard.effective_audio_signals},"
        f"5locks={guard.all_5_functions_disabled_in_silent}), "
        f"target_apm={guard.target_auto_pixel_mapping}"
        f"(suppressed={guard.bench_shutdown_autopixelmap_suppressed}), "
        f"no_pwr_shutter={guard.shutter_when_pwr_off_absent_verified}"
    )
    verdict = GateVerdict(
        gate_id=G85_GATE_ID,
        gate_code=G85_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G86: [Marker Display] 15-Ratio Non-Resettable Persistence,
#    Local-LCD-Only HDMI Isolation & [Flexible Exp. Mode] Reset Split Guard
# ---------------------------------------------------------------------------


def resolve_fx3_marker_display_hdmi_and_reset(
    *,
    pre_reset_marker_display: str = MARKER_ON,
    pre_reset_center_marker: str = MARKER_ON,
    pre_reset_aspect_marker: str = "2.39:1",
    pre_reset_safety_zone: str = SAFETY_ZONE_90_PCT,
    pre_reset_guideframe: str = GUIDEFRAME_ON,
    hdmi_info_display_on: bool = False,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
) -> Dict[str, Any]:
    """Resolve `ILME-FX3` (`Ver. 7.02`) `[Marker Display]` local-LCD-only HDMI
    clean-feed isolation and reset survival asymmetry:

    - Markers are displayed on the camera's built-in LCD monitor ONLY (when
      `[Marker Display] = [On]`, at least one sub-marker is active, and the
      camera LCD is not blanked by `[HDMI Info. Display] = [On]`) and are NEVER
      output externally over HDMI (`expected_hdmi_marker_overlay_rendered = False`,
      `0` external HDMI marker overlays even when `[HDMI Info. Display] = [On]`).
    - `[Camera Settings Reset]` preserves all `[Marker Display]` / `[Aspect Marker]`
      settings unchanged; `[Initialize]` resets them to factory `Off`.
    """
    canon_disp = _norm_on_off(pre_reset_marker_display)
    canon_center = _norm_on_off(pre_reset_center_marker)
    canon_aspect = _norm_aspect_marker(pre_reset_aspect_marker)
    canon_safety = _norm_safety_zone(pre_reset_safety_zone)
    canon_guide = _norm_on_off(pre_reset_guideframe)
    canon_rst = _norm_reset_action(reset_action)

    if canon_rst == RESET_ACTION_INITIALIZE:
        exp_disp = MARKER_FACTORY_DEFAULT_DISPLAY
        exp_center = MARKER_FACTORY_DEFAULT_CENTER
        exp_aspect = MARKER_FACTORY_DEFAULT_ASPECT
        exp_safety = MARKER_FACTORY_DEFAULT_SAFETY_ZONE
        exp_guide = MARKER_FACTORY_DEFAULT_GUIDEFRAME
    else:
        exp_disp = canon_disp or pre_reset_marker_display
        exp_center = canon_center or pre_reset_center_marker
        exp_aspect = canon_aspect or pre_reset_aspect_marker
        exp_safety = canon_safety or pre_reset_safety_zone
        exp_guide = canon_guide or pre_reset_guideframe

    any_subitem_post = (
        exp_center == MARKER_ON
        or exp_aspect != MARKER_OFF
        or exp_safety != SAFETY_ZONE_OFF
        or exp_guide == GUIDEFRAME_ON
    )
    lcd_blanked = bool(hdmi_info_display_on)
    exp_local_lcd_marker = (
        (exp_disp == MARKER_ON) and any_subitem_post and (not lcd_blanked)
    )

    return {
        "canonical_marker_display": canon_disp,
        "canonical_center_marker": canon_center,
        "canonical_aspect_marker": canon_aspect,
        "canonical_safety_zone": canon_safety,
        "canonical_guideframe": canon_guide,
        "canonical_reset_action": canon_rst,
        "any_marker_subitem_enabled": any_subitem_post,
        "camera_lcd_blanked_by_hdmi_info": lcd_blanked,
        "expected_local_lcd_marker_rendered": exp_local_lcd_marker,
        "expected_hdmi_marker_overlay_rendered": False,
        "expected_post_reset_marker_display": exp_disp,
        "expected_post_reset_center_marker": exp_center,
        "expected_post_reset_aspect_marker": exp_aspect,
        "expected_post_reset_safety_zone": exp_safety,
        "expected_post_reset_guideframe": exp_guide,
    }


def resolve_fx3_flexible_exp_reset_split(
    *,
    exposure_ctrl_type: str = EXPOSURE_CTRL_FLEXIBLE_EXP_MODE,
    pasm_submode: str = PASM_MANUAL_EXPOSURE,
    pre_reset_flex_av_mode: str = FLEX_EXP_AUTO,
    pre_reset_flex_tv_mode: str = FLEX_EXP_AUTO,
    pre_reset_flex_iso_mode: str = FLEX_EXP_AUTO,
    pre_reset_auto_slow_shutter: str = AUTO_SLOW_SHUTTER_OFF,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
) -> Dict[str, Any]:
    """Resolve `ILME-FX3` (`Ver. 7.02`) `[Exposure Ctrl Type]` (`P/A/S/M Mode` vs
    `Flexible Exp. Mode`) `[Auto/Manual Swt. Set.]` (`Av`/`Tv`/`ISO`) +
    `[Auto Slow Shutter]` reset split:

    - Factory defaults: `Av = Manual`, `Tv = Manual`, `ISO = Manual`,
      `[Auto Slow Shutter] = On`.
    - Both `[Camera Settings Reset]` AND `[Initialize]` reset `Av`/`Tv`/`ISO`
      back to `Manual` and `[Auto Slow Shutter]` back to `On` (contrasting
      directly with non-resettable `[Marker Display]` / `[Aspect Marker]`).
    """
    canon_ctrl = _norm_exposure_ctrl_type(exposure_ctrl_type)
    canon_pasm = _norm_pasm_submode(pasm_submode)
    canon_av = _norm_flex_sw_mode(pre_reset_flex_av_mode)
    canon_tv = _norm_flex_sw_mode(pre_reset_flex_tv_mode)
    canon_iso = _norm_flex_sw_mode(pre_reset_flex_iso_mode)
    canon_slow = _norm_on_off(pre_reset_auto_slow_shutter)
    canon_rst = _norm_reset_action(reset_action)

    if canon_rst in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        exp_av = FLEX_EXP_FACTORY_DEFAULT_AV
        exp_tv = FLEX_EXP_FACTORY_DEFAULT_TV
        exp_iso = FLEX_EXP_FACTORY_DEFAULT_ISO
        exp_slow = AUTO_SLOW_SHUTTER_FACTORY_DEFAULT
    else:
        exp_av = canon_av or pre_reset_flex_av_mode
        exp_tv = canon_tv or pre_reset_flex_tv_mode
        exp_iso = canon_iso or pre_reset_flex_iso_mode
        exp_slow = canon_slow or pre_reset_auto_slow_shutter

    return {
        "canonical_exposure_ctrl_type": canon_ctrl,
        "canonical_pasm_submode": canon_pasm,
        "canonical_pre_av": canon_av,
        "canonical_pre_tv": canon_tv,
        "canonical_pre_iso": canon_iso,
        "canonical_pre_auto_slow_shutter": canon_slow,
        "canonical_reset_action": canon_rst,
        "expected_post_reset_flex_av_mode": exp_av,
        "expected_post_reset_flex_tv_mode": exp_tv,
        "expected_post_reset_flex_iso_mode": exp_iso,
        "expected_post_reset_auto_slow_shutter": exp_slow,
    }


def verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE230,
    pre_reset_marker_display: str = MARKER_ON,
    pre_reset_center_marker: str = MARKER_ON,
    pre_reset_aspect_marker: str = "2.39:1",
    pre_reset_safety_zone: str = SAFETY_ZONE_90_PCT,
    pre_reset_guideframe: str = GUIDEFRAME_ON,
    claimed_aspect_marker_ratios: Sequence[str] = FX3_ASPECT_MARKER_15_RATIOS,
    hdmi_info_display_on: bool = False,
    local_lcd_marker_rendered: Optional[bool] = None,
    hdmi_marker_overlay_rendered: bool = False,
    external_hdmi_marker_count: int = 0,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    post_reset_marker_display: Optional[str] = None,
    post_reset_center_marker: Optional[str] = None,
    post_reset_aspect_marker: Optional[str] = None,
    post_reset_safety_zone: Optional[str] = None,
    post_reset_guideframe: Optional[str] = None,
    exposure_ctrl_type: str = EXPOSURE_CTRL_FLEXIBLE_EXP_MODE,
    pasm_submode: str = PASM_MANUAL_EXPOSURE,
    pre_reset_flex_av_mode: str = FLEX_EXP_AUTO,
    pre_reset_flex_tv_mode: str = FLEX_EXP_AUTO,
    pre_reset_flex_iso_mode: str = FLEX_EXP_AUTO,
    pre_reset_auto_slow_shutter: str = AUTO_SLOW_SHUTTER_OFF,
    post_reset_flex_av_mode: Optional[str] = None,
    post_reset_flex_tv_mode: Optional[str] = None,
    post_reset_flex_iso_mode: Optional[str] = None,
    post_reset_auto_slow_shutter: Optional[str] = None,
) -> Marker15RatioHdmiAndFlexExpResetSplitResult:
    """Verify Gate `G86`: `[Marker Display]` (`Center Marker`, `Aspect Marker`
    `Off` + all 15 `Ver. 3.00+/7.02` ratios, `Safety Zone` `Off/80%/90%`,
    `Guideframe` `Off/On`) local-LCD-only HDMI isolation + survival across
    `[Camera Settings Reset]`, contrasted against `[Flexible Exp. Mode]`
    `Av`/`Tv`/`ISO` (`-> Manual`) + `[Auto Slow Shutter]` (`-> On`) reset split.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name.strip().upper() != FX3_MODEL_NAME
        or int(body_model_id) != FX3_MODEL_ID
    ):
        _add_code(codes, STATUS_BLOCKED_G86_TELEMETRY_INVALID)
        errors.append(
            f"Body mismatch for G86: name={body_model_name!r}, id=0x{int(body_model_id):08X}."
        )

    fw_tuple = _parse_fw_tuple(firmware_version)
    if fw_tuple is None:
        _add_code(codes, STATUS_BLOCKED_G86_TELEMETRY_INVALID)
        errors.append(f"Malformed firmware_version={firmware_version!r} for Gate G86.")

    m_state = resolve_fx3_marker_display_hdmi_and_reset(
        pre_reset_marker_display=pre_reset_marker_display,
        pre_reset_center_marker=pre_reset_center_marker,
        pre_reset_aspect_marker=pre_reset_aspect_marker,
        pre_reset_safety_zone=pre_reset_safety_zone,
        pre_reset_guideframe=pre_reset_guideframe,
        hdmi_info_display_on=bool(hdmi_info_display_on),
        reset_action=reset_action,
    )

    f_state = resolve_fx3_flexible_exp_reset_split(
        exposure_ctrl_type=exposure_ctrl_type,
        pasm_submode=pasm_submode,
        pre_reset_flex_av_mode=pre_reset_flex_av_mode,
        pre_reset_flex_tv_mode=pre_reset_flex_tv_mode,
        pre_reset_flex_iso_mode=pre_reset_flex_iso_mode,
        pre_reset_auto_slow_shutter=pre_reset_auto_slow_shutter,
        reset_action=reset_action,
    )

    # 1. Validate Marker enums & all 15 Ver. 3.00+/7.02 Aspect Marker ratios
    if (
        m_state["canonical_marker_display"] is None
        or m_state["canonical_center_marker"] is None
        or m_state["canonical_aspect_marker"] is None
        or m_state["canonical_safety_zone"] is None
        or m_state["canonical_guideframe"] is None
    ):
        _add_code(codes, STATUS_BLOCKED_G86_MARKER_DISPLAY_OR_15RATIO_INVALID)
        errors.append(
            "Invalid [Marker Display] sub-item setting: "
            f"marker_display={pre_reset_marker_display!r}, center={pre_reset_center_marker!r}, "
            f"aspect={pre_reset_aspect_marker!r} (allowed={ALLOWED_ASPECT_MARKER_SETTINGS}), "
            f"safety_zone={pre_reset_safety_zone!r}, guideframe={pre_reset_guideframe!r}."
        )

    claimed_ratios_tuple = tuple((r or "").strip() for r in claimed_aspect_marker_ratios)
    if (
        len(claimed_ratios_tuple) != 15
        or set(claimed_ratios_tuple) != set(FX3_ASPECT_MARKER_15_RATIOS)
    ):
        _add_code(codes, STATUS_BLOCKED_G86_MARKER_DISPLAY_OR_15RATIO_INVALID)
        errors.append(
            f"[Aspect Marker] ratio catalog mismatch: got {len(claimed_ratios_tuple)} ratios "
            f"{claimed_ratios_tuple}, expected all 15 Ver. 3.00+/7.02 ratios {FX3_ASPECT_MARKER_15_RATIOS}."
        )

    if (
        m_state["canonical_aspect_marker"] == "16:9"
        and fw_tuple is not None
        and fw_tuple < FX3_ASPECT_MARKER_16_9_MIN_FW_TUPLE
    ):
        _add_code(codes, STATUS_BLOCKED_G86_MARKER_DISPLAY_OR_15RATIO_INVALID)
        errors.append(
            f"[Aspect Marker]=[16:9] requires ILME-FX3 Ver. 3.00+, got {firmware_version!r}."
        )

    if m_state["canonical_reset_action"] is None:
        _add_code(codes, STATUS_BLOCKED_G86_TELEMETRY_INVALID)
        errors.append(
            f"Unsupported reset_action={reset_action!r}; allowed={ALLOWED_RESET_ACTIONS_G86}."
        )

    if (
        f_state["canonical_exposure_ctrl_type"] is None
        or f_state["canonical_pasm_submode"] is None
        or f_state["canonical_pre_av"] is None
        or f_state["canonical_pre_tv"] is None
        or f_state["canonical_pre_iso"] is None
        or f_state["canonical_pre_auto_slow_shutter"] is None
    ):
        _add_code(codes, STATUS_BLOCKED_G86_TELEMETRY_INVALID)
        errors.append(
            "Invalid [Exposure Ctrl Type] / [Flexible Exp. Mode] enum: "
            f"ctrl={exposure_ctrl_type!r}, pasm={pasm_submode!r}, "
            f"av={pre_reset_flex_av_mode!r}, tv={pre_reset_flex_tv_mode!r}, "
            f"iso={pre_reset_flex_iso_mode!r}, auto_slow={pre_reset_auto_slow_shutter!r}."
        )

    if isinstance(external_hdmi_marker_count, bool) or not isinstance(
        external_hdmi_marker_count, int
    ) or external_hdmi_marker_count < 0:
        _add_code(codes, STATUS_BLOCKED_G86_TELEMETRY_INVALID)
        errors.append(
            f"external_hdmi_marker_count={external_hdmi_marker_count!r} must be a non-negative int."
        )
        hdmi_cnt = 1
    else:
        hdmi_cnt = int(external_hdmi_marker_count)

    # 2. Marker post-reset survival vs Initialize wipe
    eff_post_disp = (
        m_state["expected_post_reset_marker_display"]
        if post_reset_marker_display is None
        else (_norm_on_off(post_reset_marker_display) or post_reset_marker_display)
    )
    eff_post_center = (
        m_state["expected_post_reset_center_marker"]
        if post_reset_center_marker is None
        else (_norm_on_off(post_reset_center_marker) or post_reset_center_marker)
    )
    eff_post_aspect = (
        m_state["expected_post_reset_aspect_marker"]
        if post_reset_aspect_marker is None
        else (_norm_aspect_marker(post_reset_aspect_marker) or post_reset_aspect_marker)
    )
    eff_post_safety = (
        m_state["expected_post_reset_safety_zone"]
        if post_reset_safety_zone is None
        else (_norm_safety_zone(post_reset_safety_zone) or post_reset_safety_zone)
    )
    eff_post_guide = (
        m_state["expected_post_reset_guideframe"]
        if post_reset_guideframe is None
        else (_norm_on_off(post_reset_guideframe) or post_reset_guideframe)
    )

    marker_reset_ok = (
        eff_post_disp == m_state["expected_post_reset_marker_display"]
        and eff_post_center == m_state["expected_post_reset_center_marker"]
        and eff_post_aspect == m_state["expected_post_reset_aspect_marker"]
        and eff_post_safety == m_state["expected_post_reset_safety_zone"]
        and eff_post_guide == m_state["expected_post_reset_guideframe"]
    )
    if not marker_reset_ok:
        _add_code(
            codes,
            STATUS_BLOCKED_G86_MARKER_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION,
        )
        errors.append(
            f"[Marker Display] post-reset mismatch under {m_state['canonical_reset_action']}: "
            f"got ({eff_post_disp!r}, {eff_post_center!r}, {eff_post_aspect!r}, "
            f"{eff_post_safety!r}, {eff_post_guide!r}), expected "
            f"({m_state['expected_post_reset_marker_display']!r}, "
            f"{m_state['expected_post_reset_center_marker']!r}, "
            f"{m_state['expected_post_reset_aspect_marker']!r}, "
            f"{m_state['expected_post_reset_safety_zone']!r}, "
            f"{m_state['expected_post_reset_guideframe']!r})."
        )

    # 3. Local-LCD-Only HDMI Marker Isolation (`0` HDMI marker overlays even with [HDMI Info. Display]=On)
    eff_lcd_marker = (
        bool(m_state["expected_local_lcd_marker_rendered"])
        if local_lcd_marker_rendered is None
        else bool(local_lcd_marker_rendered)
    )
    eff_hdmi_marker = bool(hdmi_marker_overlay_rendered)

    hdmi_iso_ok = (
        (not eff_hdmi_marker)
        and (hdmi_cnt == 0)
        and (eff_lcd_marker == bool(m_state["expected_local_lcd_marker_rendered"]))
    )
    if not hdmi_iso_ok:
        _add_code(codes, STATUS_BLOCKED_G86_HDMI_MARKER_OVERLAY_LEAK)
        errors.append(
            "ILME-FX3 [Marker Display] local-monitor-only HDMI isolation violated: "
            f"hdmi_marker_overlay_rendered={eff_hdmi_marker}, "
            f"external_hdmi_marker_count={hdmi_cnt}, "
            f"local_lcd_marker={eff_lcd_marker} (expected {m_state['expected_local_lcd_marker_rendered']}), "
            f"hdmi_info_display_on={bool(hdmi_info_display_on)}."
        )

    # 4. [Flexible Exp. Mode] Av/Tv/ISO (-> Manual) & [Auto Slow Shutter] (-> On) Reset Split
    eff_post_av = (
        f_state["expected_post_reset_flex_av_mode"]
        if post_reset_flex_av_mode is None
        else (_norm_flex_sw_mode(post_reset_flex_av_mode) or post_reset_flex_av_mode)
    )
    eff_post_tv = (
        f_state["expected_post_reset_flex_tv_mode"]
        if post_reset_flex_tv_mode is None
        else (_norm_flex_sw_mode(post_reset_flex_tv_mode) or post_reset_flex_tv_mode)
    )
    eff_post_iso = (
        f_state["expected_post_reset_flex_iso_mode"]
        if post_reset_flex_iso_mode is None
        else (_norm_flex_sw_mode(post_reset_flex_iso_mode) or post_reset_flex_iso_mode)
    )
    eff_post_slow = (
        f_state["expected_post_reset_auto_slow_shutter"]
        if post_reset_auto_slow_shutter is None
        else (
            _norm_on_off(post_reset_auto_slow_shutter) or post_reset_auto_slow_shutter
        )
    )

    flex_reset_ok = (
        eff_post_av == f_state["expected_post_reset_flex_av_mode"]
        and eff_post_tv == f_state["expected_post_reset_flex_tv_mode"]
        and eff_post_iso == f_state["expected_post_reset_flex_iso_mode"]
        and eff_post_slow == f_state["expected_post_reset_auto_slow_shutter"]
    )
    if not flex_reset_ok:
        _add_code(
            codes,
            STATUS_BLOCKED_G86_FLEXIBLE_EXP_AV_TV_ISO_OR_AUTOSLOW_RESET_SPLIT_VIOLATION,
        )
        errors.append(
            f"[Flexible Exp. Mode] Av/Tv/ISO or [Auto Slow Shutter] reset split mismatch "
            f"under {f_state['canonical_reset_action']}: got "
            f"(Av={eff_post_av!r}, Tv={eff_post_tv!r}, ISO={eff_post_iso!r}, AutoSlow={eff_post_slow!r}), "
            f"expected (Av={f_state['expected_post_reset_flex_av_mode']!r}, "
            f"Tv={f_state['expected_post_reset_flex_tv_mode']!r}, "
            f"ISO={f_state['expected_post_reset_flex_iso_mode']!r}, "
            f"AutoSlow={f_state['expected_post_reset_auto_slow_shutter']!r})."
        )

    canon_rst = m_state["canonical_reset_action"]
    marker_survived = (canon_rst != RESET_ACTION_INITIALIZE) and marker_reset_ok
    flex_reset_by_cam_rst = (
        canon_rst in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE)
        and flex_reset_ok
    )
    split_verified = marker_reset_ok and flex_reset_ok

    valid = not codes
    status = STATUS_VERIFIED_G86 if valid else codes[0]
    return Marker15RatioHdmiAndFlexExpResetSplitResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{int(body_model_id):08X}",
        firmware_version=firmware_version,
        pre_reset_marker_display=m_state["canonical_marker_display"]
        or pre_reset_marker_display,
        pre_reset_center_marker=m_state["canonical_center_marker"]
        or pre_reset_center_marker,
        pre_reset_aspect_marker=m_state["canonical_aspect_marker"]
        or pre_reset_aspect_marker,
        pre_reset_safety_zone=m_state["canonical_safety_zone"]
        or pre_reset_safety_zone,
        pre_reset_guideframe=m_state["canonical_guideframe"] or pre_reset_guideframe,
        supported_aspect_marker_15_ratios=FX3_ASPECT_MARKER_15_RATIOS,
        aspect_marker_15_ratio_count=len(FX3_ASPECT_MARKER_15_RATIOS),
        any_marker_subitem_enabled=bool(m_state["any_marker_subitem_enabled"]),
        hdmi_info_display_on=bool(hdmi_info_display_on),
        camera_lcd_blanked_by_hdmi_info=bool(
            m_state["camera_lcd_blanked_by_hdmi_info"]
        ),
        local_lcd_marker_rendered=eff_lcd_marker,
        hdmi_marker_overlay_rendered=eff_hdmi_marker,
        external_hdmi_marker_count=hdmi_cnt,
        hdmi_marker_isolation_enforced=hdmi_iso_ok,
        reset_action=canon_rst or reset_action,
        expected_post_reset_marker_display=m_state[
            "expected_post_reset_marker_display"
        ],
        expected_post_reset_center_marker=m_state["expected_post_reset_center_marker"],
        expected_post_reset_aspect_marker=m_state["expected_post_reset_aspect_marker"],
        expected_post_reset_safety_zone=m_state["expected_post_reset_safety_zone"],
        expected_post_reset_guideframe=m_state["expected_post_reset_guideframe"],
        effective_post_reset_marker_display=eff_post_disp,
        effective_post_reset_center_marker=eff_post_center,
        effective_post_reset_aspect_marker=eff_post_aspect,
        effective_post_reset_safety_zone=eff_post_safety,
        effective_post_reset_guideframe=eff_post_guide,
        marker_survived_camera_settings_reset=marker_survived,
        exposure_ctrl_type=f_state["canonical_exposure_ctrl_type"]
        or exposure_ctrl_type,
        pasm_submode=f_state["canonical_pasm_submode"] or pasm_submode,
        pre_reset_flex_av_mode=f_state["canonical_pre_av"] or pre_reset_flex_av_mode,
        pre_reset_flex_tv_mode=f_state["canonical_pre_tv"] or pre_reset_flex_tv_mode,
        pre_reset_flex_iso_mode=f_state["canonical_pre_iso"] or pre_reset_flex_iso_mode,
        pre_reset_auto_slow_shutter=f_state["canonical_pre_auto_slow_shutter"]
        or pre_reset_auto_slow_shutter,
        expected_post_reset_flex_av_mode=f_state["expected_post_reset_flex_av_mode"],
        expected_post_reset_flex_tv_mode=f_state["expected_post_reset_flex_tv_mode"],
        expected_post_reset_flex_iso_mode=f_state["expected_post_reset_flex_iso_mode"],
        expected_post_reset_auto_slow_shutter=f_state[
            "expected_post_reset_auto_slow_shutter"
        ],
        effective_post_reset_flex_av_mode=eff_post_av,
        effective_post_reset_flex_tv_mode=eff_post_tv,
        effective_post_reset_flex_iso_mode=eff_post_iso,
        effective_post_reset_auto_slow_shutter=eff_post_slow,
        flex_exp_reset_by_camera_settings_reset=flex_reset_by_cam_rst,
        marker_vs_flexexp_reset_split_verified=split_verified,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g86_marker_hdmi_and_flexexp_reset_split_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    marker_flexexp_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase230DonorAuditResult] = None,
) -> Tuple[GateVerdict, G86MarkerHdmiAndFlexExpResetSplitGuardResult]:
    """Evaluate Gate `G86` combining bounded `<0.15s` donor check with `[Marker Display]`
    15-ratio non-resettable persistence + local-LCD-only HDMI isolation and
    `[Flexible Exp. Mode]` `Av`/`Tv`/`ISO` + `[Auto Slow Shutter]` reset split guard.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase230_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
        **dict(marker_flexexp_kwargs or {})
    )

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)
    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G86 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G86 if valid else codes[0]

    res = G86MarkerHdmiAndFlexExpResetSplitGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        marker_hdmi_flexexp_reset_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, marker={guard.effective_post_reset_marker_display}/"
        f"{guard.effective_post_reset_aspect_marker}(ratios={guard.aspect_marker_15_ratio_count},"
        f"hdmi_marker={guard.hdmi_marker_overlay_rendered},rst={guard.reset_action}), "
        f"flex_exp={guard.exposure_ctrl_type}(Av={guard.effective_post_reset_flex_av_mode},"
        f"Tv={guard.effective_post_reset_flex_tv_mode},ISO={guard.effective_post_reset_flex_iso_mode},"
        f"AutoSlow={guard.effective_post_reset_auto_slow_shutter})"
    )
    verdict = GateVerdict(
        gate_id=G86_GATE_ID,
        gate_code=G86_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified 86-Gate Master Safety Preflight (`G01..G86`)
# ---------------------------------------------------------------------------


def evaluate_86gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    silent_autopixelmap_kwargs: Optional[Mapping[str, Any]] = None,
    marker_flexexp_kwargs: Optional[Mapping[str, Any]] = None,
    master_84_override: Optional[Master84GateReport] = None,
    **m84_passthrough_kwargs: Any,
) -> Master86GateReport:
    """Evaluate all 86 Master Safety Gates (`G01..G86`) deterministically by
    delegating `G01..G84` directly to `evaluate_84gate_preflight()`.
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

    m84_report: Master84GateReport = (
        master_84_override
        if master_84_override is not None
        else evaluate_84gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m84_passthrough_kwargs,
        )
    )

    phase230_audit = audit_phase230_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g85_verdict, g85_res = evaluate_g85_silent_autopixelmap_no_pwrshutter_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        silent_autopixelmap_kwargs=silent_autopixelmap_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase230_audit,
    )

    g86_verdict, g86_res = evaluate_g86_marker_hdmi_and_flexexp_reset_split_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        marker_flexexp_kwargs=marker_flexexp_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase230_audit,
    )

    gates_85_to_86 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g85_verdict, g86_verdict)
    ]
    all_gates = tuple(list(m84_report.gates) + gates_85_to_86)

    g01_to_g12_verified = int(m84_report.summary["g01_to_g12_verified"])
    g13_to_g84_verified = (
        int(m84_report.summary["g13_to_g82_verified"])
        + int(m84_report.summary["g83_to_g84_verified"])
    )
    g85_to_g86_verified = sum(1 for v in (g85_verdict, g86_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g84_verified + g85_to_g86_verified

    g85_to_g86_all_passed = g85_to_g86_verified == 2
    g13_to_g86_all_passed = m84_report.g13_to_g84_all_passed and g85_to_g86_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m84_report.gates[:9])

    offline_83_verified = (
        g01_to_g09_ok
        and m84_report.offline_81_gates_verified
        and g85_to_g86_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_86_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g86_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m84_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_83_verified
        and m84_report.h0_h1_trial_entry_allowed
        and g85_to_g86_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m84_report.errors) + list(g85_verdict.errors) + list(g86_verdict.errors)
    )
    warnings: List[str] = (
        list(m84_report.warnings)
        + list(g85_verdict.warnings)
        + list(g86_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m84_report.g13_to_g84_all_passed:
        overall_status = m84_report.status
    elif not g85_verdict.passed:
        overall_status = g85_verdict.status
    elif not g86_verdict.passed:
        overall_status = g86_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_86_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_86_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_86_verified:
        overall_status = "VERIFIED_ALL_86_GATES"
    else:
        overall_status = "VERIFIED_83_OF_86_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m84_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g85_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g86_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 86,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 86 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g84_verified": g13_to_g84_verified,
        "g85_to_g86_verified": g85_to_g86_verified,
        "g13_to_g86_all_passed": g13_to_g86_all_passed,
        "g85_to_g86_all_passed": g85_to_g86_all_passed,
        "offline_83_gates_verified": offline_83_verified,
        "all_86_gates_verified": all_86_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "human_hardware_attach_token": HUMAN_HARDWARE_ATTACH_TOKEN,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master86GateReport(
        schema=REALHW_SILENT_AUTOPIXELMAP_MARKER_FLEXEXP_86GATE_SCHEMA,
        version=REALHW_SILENT_AUTOPIXELMAP_MARKER_FLEXEXP_86GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_83_gates_verified=offline_83_verified,
        all_86_gates_verified=all_86_verified,
        g13_to_g86_all_passed=g13_to_g86_all_passed,
        g85_to_g86_all_passed=g85_to_g86_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_84_report=m84_report.to_dict(),
        g85_result=g85_res.to_dict(),
        g86_result=g86_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_86_master_safety_gates = evaluate_86gate_preflight
run_86_gate_preflight = evaluate_86gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard",
        description=(
            "Phase 230 Safety Gates G85 (Silent Mode Settings Auto Pixel Mapping "
            "Suppression Target, 5-Function Lockout & Hardware Shutter When Pwr OFF "
            "Absence Guard) + G86 (Marker Display 15-Ratio Non-Resettable Persistence, "
            "Local-LCD-Only HDMI Isolation & Flexible Exp. Mode Reset Split Guard) + "
            "Unified 86-Gate Master Safety Preflight"
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
    )
    parser.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_86gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/86 "
            f"g85_to_g86_all_passed={report.g85_to_g86_all_passed} "
            f"all_86_gates_verified={report.all_86_gates_verified} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = report.all_86_gates_verified if args.dry_run_simulated else report.offline_83_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
