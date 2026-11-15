"""Phase 237 (`90/90` Milestone) Sony `ILME-FX3` (`Ver. 7.02`) Safety Gates `G89`
(`Emphasized REC Display` & `Grid Line` HDMI Info Routing vs Forced
`Off(HDMI Only)` / `RAW` Clean-Feed Suppression) & `G90` (`Touch Operation`
4-Item `Camera Settings Reset` Survival + Bench Accidental-Tap Lock & `Monitor Brightness`
`Manual` `-2..+2` vs `Sunny Weather` Indoor Guard) + Unified 90-Gate Master
Safety Preflight (`G01..G90`).

Operationalizes Wave-35 official Sony `ILME-FX3` (`Ver. 7.02`) intelligence
(`reports/2026-11-15-global-sony-wave35-emphasized-rec-grid-hdmi-split-touch-op-reset-persist-sunny-weather-intel/README.md`)
as deterministic offline preflight verifiers (`G89` and `G90`) and composes them
with `evaluate_88gate_preflight` (`G01..G88`) into the unified `90/90` Milestone
Master Safety Preflight (`G01..G90`):

1. **Gate `G89` (`EMPHASIZED_REC_AND_GRID_LINE_HDMI_INFO_ROUTING_VS_FORCED_HDMIONLY_RAW_SUPPRESSION_GUARD`)**:
   - **`[Emphasized REC Display]` (`MENU -> Shooting -> [Shooting Display] -> [Emphasized REC Display]`)**:
     Displays a bold red frame around monitor edges during Movie and `S&Q`
     recording (`On` factory default on `ILME-FX3`, inactive during Standby and
     Still shooting, and **resettable** back to `On` via `[Camera Settings Reset]`).
   - **`[Grid Line Display]` & `[Grid Line Type]` (`MENU -> Shooting -> [Shooting Display]`)**:
     `[Grid Line Display]` (`Off` factory default / `On`) and `[Grid Line Type]`
     (`Rule of 3rds Grid` factory default, `Square Grid`, `Diag. + Square Grid`)
     are **NOT reset** by `[Camera Settings Reset]` (restored exclusively by
     `[Initialize]`), creating a direct `[Camera Settings Reset]` split against
     resettable `[Emphasized REC Display]`.
   - **HDMI Info Routing vs Local-LCD-Only Assist Overlays**:
     Unlike strictly local-LCD-only `[Marker Display]`, `[Zebra Display]`, and
     `[Peaking Display]` (`0` HDMI pixels even when `[HDMI Info. Display] = [On]`),
     both `[Emphasized REC Display]` (when `On` during Movie/`S&Q` recording) and
     `[Grid Line Display]` (when `On`) **ARE routed to external HDMI** when
     effective `[HDMI Info. Display] = [On]` (which simultaneously blanks the
     built-in camera LCD).
   - **Two Automatic Hardware `[HDMI Info. Display] -> [Off]` Clean-Feed Clamps**:
     Whenever `[Rec. Media dur HDMI Output] = [Off(HDMI Only)]` OR HDMI `RAW`
     movie output (`[RAW Output] = [On]`) is active, `[HDMI Info. Display]` is
     **temporarily forced to `[Off]`**, guaranteeing `0` red REC border, `0`
     grid lines, and `0` status OSD pixels (`hdmi_baked_overlay_pixels == 0`)
     are baked into external HDMI recorder master streams.

2. **Gate `G90` (`TOUCH_OPERATION_4ITEM_RESET_SURVIVAL_BENCH_TAP_LOCK_AND_SUNNY_WEATHER_INDOOR_GUARD`)**:
   - **Four Setup `[Touch Operation]` Items Immune to `[Camera Settings Reset]`**:
     Under `MENU -> Setup -> [Touch Operation]`, all 4 items —
     `[Touch Operation]` (`On` default / `On: Playback Only` / `Off`),
     `[Touch Sensitivity]` (`Standard` default / `Sensitive`),
     `[Swipe Up]` (`Open the Fn Menu` default / `Off`), and
     `[Touch Func. in Shooting]` (`Touch Tracking` default / `Touch Focus` / `Off`) —
     **survive `[Camera Settings Reset]`** and are restored to factory defaults
     exclusively by `[Initialize]`.
   - **Unattended Bench Tier-0 Capacitive Accidental-Tap Lock**:
     During unattended physical bench rehearsals or Tier-0 card vault dumps
     (`bench_unattended_tier0_active == True`), requires post-reset
     `[Touch Operation]` to remain `Off` or `On: Playback Only` so accidental
     screen contact or harness brush cannot trigger `Swipe Up -> Open the Fn Menu`
     or `Touch Tracking` / `Touch Focus` in shooting view.
   - **`[Monitor Brightness]` (`Manual` `-2..+2` vs `Sunny Weather` Indoor Guard & Reset Survival)**:
     Under `MENU -> Setup -> [Monitor] -> [Monitor Brightness]`, validates
     `Manual` (`-2..+2`, default `0`) vs `Sunny Weather`, enforces survival
     across `[Camera Settings Reset]` (cleared only by `[Initialize]`), and
     blocks `[Sunny Weather]` during indoor `NP-FZ100` bench runs
     (`indoor_bench_environment == True`) to prevent indoor visual exposure
     misjudgment and excess LCD backlight thermal/battery draw.

3. **Unified `90/90` Milestone Master Safety Preflight (`evaluate_90gate_preflight`)**:
   - Delegates `G01..G88` directly to `evaluate_88gate_preflight()`.
   - Offline default mode: `87/90` pass (`G01..G09`, `G13..G90` pass; `G10..G12`
     await physical Tier-0 receipt -> `overall_ready_for_hardware_attach = False`).
   - `--simulate-bench-dry-run` mode: `90/90` rehearsal pass while keeping all
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
from .realhw_recover_imagedb_monitor_flip_af_sens_and_88gate_guard import (
    Master88GateReport,
    evaluate_88gate_preflight,
)
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_EMPHASIZED_REC_GRID_HDMI_TOUCH_SUNNY_90GATE_SCHEMA: str = (
    "fx3-realhw-emphasized-rec-grid-hdmi-touch-sunny-90gate-v1"
)
REALHW_EMPHASIZED_REC_GRID_HDMI_TOUCH_SUNNY_90GATE_VERSION: str = "1.0.0"

G89_GATE_ID: str = "G89_emphasized_rec_and_grid_hdmi_routing_vs_cleanfeed_guard"
G89_GATE_CODE: str = (
    "EMPHASIZED_REC_AND_GRID_LINE_HDMI_INFO_ROUTING_VS_FORCED_HDMIONLY_RAW_SUPPRESSION_GUARD"
)

G90_GATE_ID: str = (
    "G90_touch_op_4item_reset_survival_and_sunny_weather_bench_guard"
)
G90_GATE_CODE: str = (
    "TOUCH_OPERATION_4ITEM_RESET_SURVIVAL_BENCH_TAP_LOCK_AND_SUNNY_WEATHER_INDOOR_GUARD"
)

G89: str = G89_GATE_ID
G90: str = G90_GATE_ID
GATE_G89_EMPHASIZED_REC_AND_GRID_LINE_HDMI_INFO_ROUTING_VS_FORCED_HDMIONLY_RAW_SUPPRESSION_GUARD: str = (
    G89_GATE_CODE
)
GATE_G90_TOUCH_OPERATION_4ITEM_RESET_SURVIVAL_BENCH_TAP_LOCK_AND_SUNNY_WEATHER_INDOOR_GUARD: str = (
    G90_GATE_CODE
)

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS: float = 0.15

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX3_DEFAULT_FW_VERSION_PHASE237: str = "7.02"
FX3_MIN_SUPPORTED_FW_TUPLE_PHASE237: Tuple[int, int] = (1, 0)

# Status & Violation Codes
STATUS_VERIFIED_G89: str = (
    "VERIFIED_G89_EMPHASIZED_REC_AND_GRID_HDMI_ROUTING_VS_CLEANFEED_SAFE"
)
STATUS_VERIFIED_G90: str = (
    "VERIFIED_G90_TOUCH_OP_4ITEM_RESET_SURVIVAL_AND_SUNNY_WEATHER_BENCH_SAFE"
)

STATUS_BLOCKED_PHASE237_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE237_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION: str = (
    "BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION"
)
STATUS_BLOCKED_G89_HDMI_INFO_ROUTING_OR_LCD_BLANKING_MISMATCH: str = (
    "BLOCKED_G89_HDMI_INFO_ROUTING_OR_LCD_BLANKING_MISMATCH"
)
STATUS_BLOCKED_G89_FORCED_HDMIONLY_OR_RAW_CLEANFEED_CLAMP_LEAK: str = (
    "BLOCKED_G89_FORCED_HDMIONLY_OR_RAW_CLEANFEED_CLAMP_LEAK"
)
STATUS_BLOCKED_G89_LOCAL_LCD_ONLY_ASSIST_HDMI_LEAK: str = (
    "BLOCKED_G89_LOCAL_LCD_ONLY_ASSIST_HDMI_LEAK"
)
STATUS_BLOCKED_G89_TELEMETRY_INVALID: str = (
    "BLOCKED_G89_EMPHASIZED_REC_GRID_HDMI_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G90_TOUCH_OPERATION_4ITEM_INVALID_OR_RESET_VIOLATION: str = (
    "BLOCKED_G90_TOUCH_OPERATION_4ITEM_INVALID_OR_RESET_VIOLATION"
)
STATUS_BLOCKED_G90_BENCH_UNATTENDED_TOUCH_SHOOTING_LIVE_HAZARD: str = (
    "BLOCKED_G90_BENCH_UNATTENDED_TOUCH_SHOOTING_LIVE_HAZARD"
)
STATUS_BLOCKED_G90_MONITOR_BRIGHTNESS_INVALID_OR_RESET_VIOLATION: str = (
    "BLOCKED_G90_MONITOR_BRIGHTNESS_INVALID_OR_RESET_VIOLATION"
)
STATUS_BLOCKED_G90_SUNNY_WEATHER_INDOOR_BENCH_BRIGHTNESS_OR_POWER_HAZARD: str = (
    "BLOCKED_G90_SUNNY_WEATHER_INDOOR_BENCH_BRIGHTNESS_OR_POWER_HAZARD"
)
STATUS_BLOCKED_G90_TELEMETRY_INVALID: str = (
    "BLOCKED_G90_TOUCH_OP_SUNNY_WEATHER_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G89 Canonical Constants: [Emphasized REC Display], [Grid Line Display],
# [Grid Line Type], [HDMI Info. Display] & Forced [Off(HDMI Only)] / RAW Clamps
# ---------------------------------------------------------------------------

EMPHASIZED_REC_DISPLAY_MENU_PATH: str = (
    "MENU -> Shooting -> [Shooting Display] -> [Emphasized REC Display]"
)
EMPHASIZED_REC_ON: str = "On"
EMPHASIZED_REC_OFF: str = "Off"
ALLOWED_EMPHASIZED_REC_MODES: Tuple[str, ...] = (
    EMPHASIZED_REC_ON,
    EMPHASIZED_REC_OFF,
)
EMPHASIZED_REC_FACTORY_DEFAULT: str = EMPHASIZED_REC_ON

GRID_LINE_DISPLAY_MENU_PATH: str = (
    "MENU -> Shooting -> [Shooting Display] -> [Grid Line Display]"
)
GRID_LINE_DISPLAY_ON: str = "On"
GRID_LINE_DISPLAY_OFF: str = "Off"
ALLOWED_GRID_LINE_DISPLAY_MODES: Tuple[str, ...] = (
    GRID_LINE_DISPLAY_OFF,
    GRID_LINE_DISPLAY_ON,
)
GRID_LINE_DISPLAY_FACTORY_DEFAULT: str = GRID_LINE_DISPLAY_OFF

GRID_LINE_TYPE_MENU_PATH: str = (
    "MENU -> Shooting -> [Shooting Display] -> [Grid Line Type]"
)
GRID_LINE_TYPE_RULE_OF_3RDS: str = "Rule of 3rds Grid"
GRID_LINE_TYPE_SQUARE: str = "Square Grid"
GRID_LINE_TYPE_DIAG_PLUS_SQUARE: str = "Diag. + Square Grid"
ALLOWED_GRID_LINE_TYPES: Tuple[str, ...] = (
    GRID_LINE_TYPE_RULE_OF_3RDS,
    GRID_LINE_TYPE_SQUARE,
    GRID_LINE_TYPE_DIAG_PLUS_SQUARE,
)
GRID_LINE_TYPE_FACTORY_DEFAULT: str = GRID_LINE_TYPE_RULE_OF_3RDS

SHOOTING_STATE_MOVIE_REC: str = "Movie Recording"
SHOOTING_STATE_SQ_REC: str = "S&Q Recording"
SHOOTING_STATE_STANDBY: str = "Standby"
SHOOTING_STATE_STILL: str = "Still Shooting"
ALLOWED_SHOOTING_STATES_G89: Tuple[str, ...] = (
    SHOOTING_STATE_MOVIE_REC,
    SHOOTING_STATE_SQ_REC,
    SHOOTING_STATE_STANDBY,
    SHOOTING_STATE_STILL,
)
ACTIVE_MOVIE_OR_SQ_REC_STATES: Tuple[str, ...] = (
    SHOOTING_STATE_MOVIE_REC,
    SHOOTING_STATE_SQ_REC,
)

HDMI_INFO_DISPLAY_MENU_PATH: str = (
    "MENU -> Setup -> [External Output] -> [HDMI Info. Display]"
)
HDMI_INFO_ON: str = "On"
HDMI_INFO_OFF: str = "Off"
ALLOWED_HDMI_INFO_DISPLAY_MODES: Tuple[str, ...] = (
    HDMI_INFO_OFF,
    HDMI_INFO_ON,
)
HDMI_INFO_FACTORY_DEFAULT: str = HDMI_INFO_OFF

REC_MEDIA_DUR_HDMI_MENU_PATH: str = (
    "MENU -> Setup -> [External Output] -> [Rec. Media dur HDMI Output]"
)
REC_MEDIA_DUR_HDMI_ON: str = "On"
REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY: str = "Off(HDMI Only)"
ALLOWED_REC_MEDIA_DUR_HDMI_MODES: Tuple[str, ...] = (
    REC_MEDIA_DUR_HDMI_ON,
    REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY,
)

HDMI_RAW_OUTPUT_MENU_PATH: str = (
    "MENU -> Setup -> [External Output] -> [RAW Output]"
)
HDMI_RAW_OUTPUT_OFF: str = "Off"
HDMI_RAW_OUTPUT_ON: str = "On"
ALLOWED_HDMI_RAW_OUTPUT_MODES: Tuple[str, ...] = (
    HDMI_RAW_OUTPUT_OFF,
    HDMI_RAW_OUTPUT_ON,
)

LOCAL_LCD_ONLY_ASSIST_OVERLAYS_G89: Tuple[str, ...] = (
    "Marker Display",
    "Zebra Display",
    "Peaking Display",
)

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_INITIALIZE: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE237: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
)

# ---------------------------------------------------------------------------
# Gate G90 Canonical Constants: 4-Item [Touch Operation] Setup Persistence,
# Bench Accidental-Tap Lock & [Monitor Brightness] Manual vs Sunny Weather
# ---------------------------------------------------------------------------

TOUCH_OPERATION_MENU_PATH: str = "MENU -> Setup -> [Touch Operation]"

TOUCH_OP_ON: str = "On"
TOUCH_OP_PLAYBACK_ONLY: str = "On: Playback Only"
TOUCH_OP_OFF: str = "Off"
ALLOWED_TOUCH_OPERATION_MODES: Tuple[str, ...] = (
    TOUCH_OP_ON,
    TOUCH_OP_PLAYBACK_ONLY,
    TOUCH_OP_OFF,
)
TOUCH_OPERATION_FACTORY_DEFAULT: str = TOUCH_OP_ON
SAFE_BENCH_UNATTENDED_TOUCH_OPERATION_MODES: Tuple[str, ...] = (
    TOUCH_OP_OFF,
    TOUCH_OP_PLAYBACK_ONLY,
)

TOUCH_SENSITIVITY_STANDARD: str = "Standard"
TOUCH_SENSITIVITY_SENSITIVE: str = "Sensitive"
ALLOWED_TOUCH_SENSITIVITY_MODES: Tuple[str, ...] = (
    TOUCH_SENSITIVITY_STANDARD,
    TOUCH_SENSITIVITY_SENSITIVE,
)
TOUCH_SENSITIVITY_FACTORY_DEFAULT: str = TOUCH_SENSITIVITY_STANDARD

SWIPE_UP_OPEN_FN_MENU: str = "Open the Fn Menu"
SWIPE_UP_OFF: str = "Off"
ALLOWED_SWIPE_UP_MODES: Tuple[str, ...] = (
    SWIPE_UP_OPEN_FN_MENU,
    SWIPE_UP_OFF,
)
SWIPE_UP_FACTORY_DEFAULT: str = SWIPE_UP_OPEN_FN_MENU

TOUCH_FUNC_SHOOTING_TRACKING: str = "Touch Tracking"
TOUCH_FUNC_SHOOTING_FOCUS: str = "Touch Focus"
TOUCH_FUNC_SHOOTING_OFF: str = "Off"
ALLOWED_TOUCH_FUNC_IN_SHOOTING_MODES: Tuple[str, ...] = (
    TOUCH_FUNC_SHOOTING_TRACKING,
    TOUCH_FUNC_SHOOTING_FOCUS,
    TOUCH_FUNC_SHOOTING_OFF,
)
TOUCH_FUNC_IN_SHOOTING_FACTORY_DEFAULT: str = TOUCH_FUNC_SHOOTING_TRACKING

TOUCH_OPERATION_4_SETUP_ITEMS: Tuple[str, ...] = (
    "Touch Operation",
    "Touch Sensitivity",
    "Swipe Up",
    "Touch Func. in Shooting",
)

MONITOR_BRIGHTNESS_MENU_PATH: str = (
    "MENU -> Setup -> [Monitor] -> [Monitor Brightness]"
)
MONITOR_BRIGHTNESS_MANUAL: str = "Manual"
MONITOR_BRIGHTNESS_SUNNY_WEATHER: str = "Sunny Weather"
ALLOWED_MONITOR_BRIGHTNESS_MODES: Tuple[str, ...] = (
    MONITOR_BRIGHTNESS_MANUAL,
    MONITOR_BRIGHTNESS_SUNNY_WEATHER,
)
MONITOR_BRIGHTNESS_FACTORY_DEFAULT_MODE: str = MONITOR_BRIGHTNESS_MANUAL
MONITOR_BRIGHTNESS_MANUAL_MIN: int = -2
MONITOR_BRIGHTNESS_MANUAL_MAX: int = 2
MONITOR_BRIGHTNESS_MANUAL_FACTORY_DEFAULT_LEVEL: int = 0
ALLOWED_MONITOR_BRIGHTNESS_MANUAL_LEVELS: Tuple[int, ...] = (-2, -1, 0, 1, 2)

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, <0.15s, Clean-Room Fallback)
# ---------------------------------------------------------------------------

PINNED_PHASE237_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_bin": (
        "FX3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"REC",
            b"Grid",
            b"Line",
            b"HDMI",
            b"Info",
            b"Touch",
            b"Sensitivity",
            b"Tracking",
            b"Monitor",
            b"Brightness",
            b"Manual",
            b"Reset",
            b"Initialize",
        ),
        "FX3_CPAPP_EMPHASIZED_REC_GRID_HDMI_TOUCH_BRIGHTNESS_STRINGS",
    ),
    "fx3_saveload_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (b"\x7fELF", b"SaveLoadSettings", b"Settings", b"Save", b"Backup"),
        "FX3_SAVELOAD_SETTINGS_PERSISTENCE_ELF",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"FTP", b"TC", b"/setting"),
        "FX3_BK4_RESET_VS_INITIALIZE_SEED",
    ),
    "fx6_bk4_bin": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"NTSC", b"TC", b"Settings", b"/setting"),
        "FX6_CHAPLIN_BK4_TALLY_AND_TOUCH_BOUNDARY_REFERENCE",
    ),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase237DonorAuditResult:
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
class EmphasizedRecAndGridHdmiCleanFeedResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    firmware_version: str
    emphasized_rec_menu_path: str
    grid_line_display_menu_path: str
    grid_line_type_menu_path: str
    hdmi_info_display_menu_path: str
    pre_reset_emphasized_rec_display: str
    pre_reset_grid_line_display: str
    pre_reset_grid_line_type: str
    reset_action: str
    expected_post_reset_emphasized_rec_display: str
    effective_post_reset_emphasized_rec_display: str
    emphasized_rec_reset_by_camera_settings_reset: bool
    expected_post_reset_grid_line_display: str
    effective_post_reset_grid_line_display: str
    expected_post_reset_grid_line_type: str
    effective_post_reset_grid_line_type: str
    grid_line_survived_camera_settings_reset: bool
    emphasized_rec_vs_grid_reset_split_verified: bool
    shooting_state: str
    movie_or_sq_recording_active: bool
    configured_hdmi_info_display: str
    rec_media_dur_hdmi_output: str
    hdmi_raw_output: str
    forced_off_by_hdmi_only_clamp: bool
    forced_off_by_hdmi_raw_clamp: bool
    hdmi_clean_feed_clamp_active: bool
    expected_effective_hdmi_info_display: str
    effective_hdmi_info_display: str
    camera_lcd_blanked_by_hdmi_info: bool
    local_lcd_emphasized_rec_rendered: bool
    local_lcd_grid_line_rendered: bool
    hdmi_emphasized_rec_rendered: bool
    hdmi_grid_line_rendered: bool
    hdmi_status_osd_rendered: bool
    hdmi_local_only_marker_rendered: bool
    hdmi_local_only_zebra_rendered: bool
    hdmi_local_only_peaking_rendered: bool
    hdmi_baked_overlay_pixels: int
    hdmi_routing_and_cleanfeed_enforced: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TouchOpResetSurvivalAndSunnyWeatherResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    firmware_version: str
    touch_operation_menu_path: str
    monitor_brightness_menu_path: str
    pre_reset_touch_operation: str
    pre_reset_touch_sensitivity: str
    pre_reset_swipe_up: str
    pre_reset_touch_func_in_shooting: str
    reset_action: str
    expected_post_reset_touch_operation: str
    effective_post_reset_touch_operation: str
    expected_post_reset_touch_sensitivity: str
    effective_post_reset_touch_sensitivity: str
    expected_post_reset_swipe_up: str
    effective_post_reset_swipe_up: str
    expected_post_reset_touch_func_in_shooting: str
    effective_post_reset_touch_func_in_shooting: str
    all_4_touch_items_survived_camera_settings_reset: bool
    bench_unattended_tier0_active: bool
    shooting_capacitive_touch_locked: bool
    accidental_fn_swipe_or_tracking_blocked: bool
    bench_touch_tap_lock_enforced: bool
    pre_reset_monitor_brightness_mode: str
    pre_reset_manual_brightness_level: int
    expected_post_reset_monitor_brightness_mode: str
    effective_post_reset_monitor_brightness_mode: str
    expected_post_reset_manual_brightness_level: int
    effective_post_reset_manual_brightness_level: int
    monitor_brightness_survived_camera_settings_reset: bool
    indoor_bench_environment: bool
    npfz100_internal_battery_active: bool
    sunny_weather_indoor_blocked: bool
    indoor_brightness_and_power_guard_enforced: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G89EmphasizedRecAndGridHdmiGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    emphasized_rec_grid_hdmi_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G90TouchOpResetAndSunnyWeatherGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    touch_op_sunny_weather_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master90GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_87_gates_verified: bool
    all_90_gates_verified: bool
    g13_to_g90_all_passed: bool
    g89_to_g90_all_passed: bool
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
    master_88_report: Dict[str, Any]
    g89_result: Dict[str, Any]
    g90_result: Dict[str, Any]
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


def _parse_fw_tuple(version_str: str) -> Optional[Tuple[int, int]]:
    if not isinstance(version_str, str):
        return None
    m = re.match(r"^\s*[vV]?(\d+)\.(\d+)(?:\.\d+)?\s*$", version_str)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _norm_on_off(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]").upper()
    if s == "ON":
        return "On"
    if s == "OFF":
        return "Off"
    return None


def _norm_reset_action(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]")
    u = s.upper().replace("_", " ")
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE
    return None


def _norm_grid_line_type(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if s in ("RULE OF 3RDS GRID", "RULE_OF_3RDS_GRID"):
        return GRID_LINE_TYPE_RULE_OF_3RDS
    if s in ("SQUARE GRID", "SQUARE_GRID"):
        return GRID_LINE_TYPE_SQUARE
    if s in (
        "DIAG. + SQUARE GRID",
        "DIAG + SQUARE GRID",
        "DIAG.+SQUARE GRID",
        "DIAG_PLUS_SQUARE_GRID",
    ):
        return GRID_LINE_TYPE_DIAG_PLUS_SQUARE
    return None


def _norm_shooting_state(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if s in ("MOVIE RECORDING", "MOVIE_RECORDING", "MOVIE REC", "MOVIE"):
        return SHOOTING_STATE_MOVIE_REC
    if s in ("S&Q RECORDING", "S&Q REC", "SQ RECORDING", "S&Q", "SQ"):
        return SHOOTING_STATE_SQ_REC
    if s in ("STANDBY", "STBY", "IDLE"):
        return SHOOTING_STATE_STANDBY
    if s in ("STILL SHOOTING", "STILL_SHOOTING", "STILL", "PHOTO"):
        return SHOOTING_STATE_STILL
    return None


def _norm_rec_media_dur_hdmi(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if s == "ON":
        return REC_MEDIA_DUR_HDMI_ON
    if s in ("OFF(HDMI ONLY)", "OFF (HDMI ONLY)", "OFF_HDMI_ONLY", "HDMI ONLY"):
        return REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY
    return None


def _norm_touch_operation(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if s == "ON":
        return TOUCH_OP_ON
    if s in (
        "ON: PLAYBACK ONLY",
        "ON : PLAYBACK ONLY",
        "ON_PLAYBACK_ONLY",
        "PLAYBACK ONLY",
    ):
        return TOUCH_OP_PLAYBACK_ONLY
    if s == "OFF":
        return TOUCH_OP_OFF
    return None


def _norm_touch_sensitivity(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]").upper()
    if s == "STANDARD":
        return TOUCH_SENSITIVITY_STANDARD
    if s == "SENSITIVE":
        return TOUCH_SENSITIVITY_SENSITIVE
    return None


def _norm_swipe_up(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if s in ("OPEN THE FN MENU", "OPEN_THE_FN_MENU"):
        return SWIPE_UP_OPEN_FN_MENU
    if s == "OFF":
        return SWIPE_UP_OFF
    return None


def _norm_touch_func_in_shooting(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if s in ("TOUCH TRACKING", "TOUCH_TRACKING"):
        return TOUCH_FUNC_SHOOTING_TRACKING
    if s in ("TOUCH FOCUS", "TOUCH_FOCUS"):
        return TOUCH_FUNC_SHOOTING_FOCUS
    if s == "OFF":
        return TOUCH_FUNC_SHOOTING_OFF
    return None


def _norm_monitor_brightness_mode(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if s == "MANUAL":
        return MONITOR_BRIGHTNESS_MANUAL
    if s in ("SUNNY WEATHER", "SUNNY_WEATHER"):
        return MONITOR_BRIGHTNESS_SUNNY_WEATHER
    return None


def _parse_manual_brightness_level(raw: Any) -> Optional[int]:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return (
            raw
            if MONITOR_BRIGHTNESS_MANUAL_MIN <= raw <= MONITOR_BRIGHTNESS_MANUAL_MAX
            else None
        )
    if isinstance(raw, str):
        s = raw.strip().strip("[]")
        m = re.match(r"^([+-]?\d+)$", s)
        if m:
            val = int(m.group(1))
            if MONITOR_BRIGHTNESS_MANUAL_MIN <= val <= MONITOR_BRIGHTNESS_MANUAL_MAX:
                return val
    return None


# ---------------------------------------------------------------------------
# 1. Bounded `< 0.15s` O_RDONLY Donor Contract Audit (`Phase 237`)
# ---------------------------------------------------------------------------


def audit_phase237_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS,
) -> Phase237DonorAuditResult:
    """Inspect local FX3/FX6 donor artifacts strictly `O_RDONLY` within `<0.15s`,
    falling back deterministically to `CLEAN_ROOM_SYNTHETIC` when
    `FX3_FX6_FORCE_CLEAN_ROOM=1` is set or local donor files are absent.
    """
    t0 = time.perf_counter()
    clean_forced = _is_forced_clean_room(force_clean_room)
    resolved_repo = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()

    candidate_root: Optional[Path] = None
    if not clean_forced:
        if work_root is not None:
            candidate_root = Path(work_root)
        else:
            paths = resolve_donor_thermal_power_paths(
                work_root=work_root, repo_root=resolved_repo
            )
            candidate_root = paths.work_root

    resolved: Dict[str, Path] = {}
    all_present = False
    if not clean_forced and candidate_root is not None and candidate_root.is_dir():
        all_present = True
        for key, (_body, rel_path, *_rest) in PINNED_PHASE237_DONOR_SPECS.items():
            fp = candidate_root / rel_path
            if fp.is_file():
                resolved[key] = fp
            else:
                all_present = False
                break

    if clean_forced or not all_present:
        elapsed = time.perf_counter() - t0
        within_budget = elapsed < max_budget_seconds
        synthetic_markers = tuple(
            spec[5] for spec in PINNED_PHASE237_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE237_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE237_DONOR_SPECS.items()}
        return Phase237DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE237_DONOR_INTEGRITY
            ),
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_CLEAN_ROOM",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_150ms=within_budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=synthetic_markers,
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            sha256_by_artifact=synthetic_shas,
            bytes_by_artifact=synthetic_sizes,
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
    ) in PINNED_PHASE237_DONOR_SPECS.items():
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
        for k, s in PINNED_PHASE237_DONOR_SPECS.items()
        if s[0] == "FX3"
    )
    fx6_ok = all(
        k in passed_keys
        for k, s in PINNED_PHASE237_DONOR_SPECS.items()
        if s[0] == "FX6"
    )
    valid = fx3_ok and fx6_ok and within_budget and (not errors)
    return Phase237DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE237_DONOR_INTEGRITY,
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
# 2. Gate `G89`: `[Emphasized REC Display]` & `[Grid Line]` HDMI Info Routing
#    vs Forced `[Off(HDMI Only)]` / `RAW` Clean-Feed Suppression
# ---------------------------------------------------------------------------


def resolve_fx3_emphasized_rec_and_grid_hdmi_routing(
    *,
    pre_reset_emphasized_rec_display: str = EMPHASIZED_REC_OFF,
    pre_reset_grid_line_display: str = GRID_LINE_DISPLAY_ON,
    pre_reset_grid_line_type: str = GRID_LINE_TYPE_DIAG_PLUS_SQUARE,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    shooting_state: str = SHOOTING_STATE_MOVIE_REC,
    configured_hdmi_info_display: str = HDMI_INFO_ON,
    rec_media_dur_hdmi_output: str = REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY,
    hdmi_raw_output: str = HDMI_RAW_OUTPUT_OFF,
) -> Dict[str, Any]:
    """Deterministically resolve `ILME-FX3` `[Emphasized REC Display]` (`On`
    default, resettable via `[Camera Settings Reset]`) vs `[Grid Line Display]` /
    `[Grid Line Type]` (`Off` / `Rule of 3rds Grid` default, NOT reset by
    `[Camera Settings Reset]`), external HDMI Info routing vs LCD blanking, and
    the two automatic `[Off(HDMI Only)]` / `RAW` clean-feed clamps.
    """
    c_emp = _norm_on_off(pre_reset_emphasized_rec_display)
    c_grid_disp = _norm_on_off(pre_reset_grid_line_display)
    c_grid_type = _norm_grid_line_type(pre_reset_grid_line_type)
    c_rst = _norm_reset_action(reset_action)
    c_shoot = _norm_shooting_state(shooting_state)
    c_hdmi_info = _norm_on_off(configured_hdmi_info_display)
    c_rec_media = _norm_rec_media_dur_hdmi(rec_media_dur_hdmi_output)
    c_raw = _norm_on_off(hdmi_raw_output)

    # [Emphasized REC Display] IS reset by [Camera Settings Reset] AND [Initialize]
    if c_rst in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        exp_post_emp = EMPHASIZED_REC_FACTORY_DEFAULT
    else:
        exp_post_emp = c_emp or EMPHASIZED_REC_FACTORY_DEFAULT

    # [Grid Line Display] & [Grid Line Type] are NOT reset by [Camera Settings Reset]
    # (restored to factory defaults exclusively by [Initialize])
    if c_rst == RESET_ACTION_INITIALIZE:
        exp_post_grid_disp = GRID_LINE_DISPLAY_FACTORY_DEFAULT
        exp_post_grid_type = GRID_LINE_TYPE_FACTORY_DEFAULT
    else:
        exp_post_grid_disp = c_grid_disp or GRID_LINE_DISPLAY_FACTORY_DEFAULT
        exp_post_grid_type = c_grid_type or GRID_LINE_TYPE_FACTORY_DEFAULT

    rec_movie_or_sq = c_shoot in ACTIVE_MOVIE_OR_SQ_REC_STATES

    clamp_hdmionly = c_rec_media == REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY
    clamp_raw = c_raw == HDMI_RAW_OUTPUT_ON
    cleanfeed_clamp_active = clamp_hdmionly or clamp_raw

    if cleanfeed_clamp_active:
        exp_eff_hdmi_info = HDMI_INFO_OFF
    else:
        exp_eff_hdmi_info = c_hdmi_info or HDMI_INFO_FACTORY_DEFAULT

    hdmi_info_routed = exp_eff_hdmi_info == HDMI_INFO_ON
    lcd_blanked_by_hdmi_info = hdmi_info_routed

    emp_active_for_state = (exp_post_emp == EMPHASIZED_REC_ON) and rec_movie_or_sq
    grid_active = exp_post_grid_disp == GRID_LINE_DISPLAY_ON

    exp_hdmi_emp = hdmi_info_routed and emp_active_for_state
    exp_hdmi_grid = hdmi_info_routed and grid_active
    exp_hdmi_osd = hdmi_info_routed

    exp_lcd_emp = (not lcd_blanked_by_hdmi_info) and emp_active_for_state
    exp_lcd_grid = (not lcd_blanked_by_hdmi_info) and grid_active

    return {
        "canonical_pre_emphasized_rec": c_emp,
        "canonical_pre_grid_display": c_grid_disp,
        "canonical_pre_grid_type": c_grid_type,
        "canonical_reset_action": c_rst,
        "canonical_shooting_state": c_shoot,
        "canonical_configured_hdmi_info": c_hdmi_info,
        "canonical_rec_media_dur_hdmi": c_rec_media,
        "canonical_hdmi_raw_output": c_raw,
        "expected_post_emphasized_rec": exp_post_emp,
        "expected_post_grid_display": exp_post_grid_disp,
        "expected_post_grid_type": exp_post_grid_type,
        "movie_or_sq_recording_active": rec_movie_or_sq,
        "forced_off_by_hdmi_only_clamp": clamp_hdmionly,
        "forced_off_by_hdmi_raw_clamp": clamp_raw,
        "hdmi_clean_feed_clamp_active": cleanfeed_clamp_active,
        "expected_effective_hdmi_info_display": exp_eff_hdmi_info,
        "expected_camera_lcd_blanked_by_hdmi_info": lcd_blanked_by_hdmi_info,
        "expected_local_lcd_emphasized_rec": exp_lcd_emp,
        "expected_local_lcd_grid_line": exp_lcd_grid,
        "expected_hdmi_emphasized_rec": exp_hdmi_emp,
        "expected_hdmi_grid_line": exp_hdmi_grid,
        "expected_hdmi_status_osd": exp_hdmi_osd,
        "expected_hdmi_local_only_marker": False,
        "expected_hdmi_local_only_zebra": False,
        "expected_hdmi_local_only_peaking": False,
    }


def verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE237,
    pre_reset_emphasized_rec_display: str = EMPHASIZED_REC_OFF,
    pre_reset_grid_line_display: str = GRID_LINE_DISPLAY_ON,
    pre_reset_grid_line_type: str = GRID_LINE_TYPE_DIAG_PLUS_SQUARE,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    observed_post_reset_emphasized_rec_display: Optional[str] = None,
    observed_post_reset_grid_line_display: Optional[str] = None,
    observed_post_reset_grid_line_type: Optional[str] = None,
    claimed_emphasized_rec_factory_default: str = EMPHASIZED_REC_FACTORY_DEFAULT,
    shooting_state: str = SHOOTING_STATE_MOVIE_REC,
    configured_hdmi_info_display: str = HDMI_INFO_ON,
    rec_media_dur_hdmi_output: str = REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY,
    hdmi_raw_output: str = HDMI_RAW_OUTPUT_OFF,
    observed_effective_hdmi_info_display: Optional[str] = None,
    observed_camera_lcd_blanked_by_hdmi_info: Optional[bool] = None,
    observed_local_lcd_emphasized_rec_rendered: Optional[bool] = None,
    observed_local_lcd_grid_line_rendered: Optional[bool] = None,
    observed_hdmi_emphasized_rec_rendered: Optional[bool] = None,
    observed_hdmi_grid_line_rendered: Optional[bool] = None,
    observed_hdmi_status_osd_rendered: Optional[bool] = None,
    observed_hdmi_local_only_marker_rendered: bool = False,
    observed_hdmi_local_only_zebra_rendered: bool = False,
    observed_hdmi_local_only_peaking_rendered: bool = False,
    observed_hdmi_baked_overlay_pixels: Optional[int] = None,
) -> EmphasizedRecAndGridHdmiCleanFeedResult:
    """Verify Gate `G89` invariants across `[Emphasized REC Display]` (`On`
    default, resettable) vs `[Grid Line Display]` / `[Grid Line Type]` (`Off` /
    `Rule of 3rds Grid` default, non-resettable across `[Camera Settings Reset]`),
    HDMI Info routing vs local-LCD-only assist overlays, and automatic
    `[Off(HDMI Only)]` / `RAW` clean-feed suppression clamps.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        body_model_name.strip().upper() != FX3_MODEL_NAME
        or int(body_model_id) != FX3_MODEL_ID
    ):
        _add_code(codes, STATUS_BLOCKED_G89_TELEMETRY_INVALID)
        errors.append(
            f"Gate G89 requires ILME-FX3 (0x{FX3_MODEL_ID:08X}); got {body_model_name!r} (0x{int(body_model_id):08X})."
        )
    if fw_tuple is None or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE237:
        _add_code(codes, STATUS_BLOCKED_G89_TELEMETRY_INVALID)
        errors.append(
            f"Gate G89 requires valid ILME-FX3 firmware version (>= 1.00); got {firmware_version!r}."
        )

    if observed_hdmi_baked_overlay_pixels is not None and (
        isinstance(observed_hdmi_baked_overlay_pixels, bool)
        or not isinstance(observed_hdmi_baked_overlay_pixels, int)
        or observed_hdmi_baked_overlay_pixels < 0
    ):
        _add_code(codes, STATUS_BLOCKED_G89_TELEMETRY_INVALID)
        errors.append(
            f"Invalid observed_hdmi_baked_overlay_pixels={observed_hdmi_baked_overlay_pixels!r}."
        )

    st = resolve_fx3_emphasized_rec_and_grid_hdmi_routing(
        pre_reset_emphasized_rec_display=pre_reset_emphasized_rec_display,
        pre_reset_grid_line_display=pre_reset_grid_line_display,
        pre_reset_grid_line_type=pre_reset_grid_line_type,
        reset_action=reset_action,
        shooting_state=shooting_state,
        configured_hdmi_info_display=configured_hdmi_info_display,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        hdmi_raw_output=hdmi_raw_output,
    )

    c_emp = st["canonical_pre_emphasized_rec"]
    c_grid_disp = st["canonical_pre_grid_display"]
    c_grid_type = st["canonical_pre_grid_type"]
    c_rst = st["canonical_reset_action"]
    c_shoot = st["canonical_shooting_state"]
    c_hdmi_info = st["canonical_configured_hdmi_info"]
    c_rec_media = st["canonical_rec_media_dur_hdmi"]
    c_raw = st["canonical_hdmi_raw_output"]

    if c_rst is None:
        _add_code(codes, STATUS_BLOCKED_G89_TELEMETRY_INVALID)
        errors.append(
            f"Invalid reset_action={reset_action!r}; expected {ALLOWED_RESET_ACTIONS_PHASE237}."
        )
    if c_shoot is None:
        _add_code(codes, STATUS_BLOCKED_G89_TELEMETRY_INVALID)
        errors.append(
            f"Invalid shooting_state={shooting_state!r}; expected {ALLOWED_SHOOTING_STATES_G89}."
        )
    if c_hdmi_info is None:
        _add_code(codes, STATUS_BLOCKED_G89_TELEMETRY_INVALID)
        errors.append(
            f"Invalid configured_hdmi_info_display={configured_hdmi_info_display!r}; expected {ALLOWED_HDMI_INFO_DISPLAY_MODES}."
        )
    if c_rec_media is None:
        _add_code(codes, STATUS_BLOCKED_G89_TELEMETRY_INVALID)
        errors.append(
            f"Invalid rec_media_dur_hdmi_output={rec_media_dur_hdmi_output!r}; expected {ALLOWED_REC_MEDIA_DUR_HDMI_MODES}."
        )
    if c_raw is None:
        _add_code(codes, STATUS_BLOCKED_G89_TELEMETRY_INVALID)
        errors.append(
            f"Invalid hdmi_raw_output={hdmi_raw_output!r}; expected {ALLOWED_HDMI_RAW_OUTPUT_MODES}."
        )

    # 1. [Emphasized REC Display] vs [Grid Line Display]/[Grid Line Type] Reset Split
    norm_claimed_def = _norm_on_off(claimed_emphasized_rec_factory_default)
    reset_split_ok = True
    if norm_claimed_def != EMPHASIZED_REC_FACTORY_DEFAULT:
        reset_split_ok = False
        _add_code(codes, STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION)
        errors.append(
            f"ILME-FX3 [Emphasized REC Display] factory default is {EMPHASIZED_REC_FACTORY_DEFAULT!r}; "
            f"got {claimed_emphasized_rec_factory_default!r}."
        )
    if c_emp is None:
        reset_split_ok = False
        _add_code(codes, STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION)
        errors.append(
            f"Invalid [Emphasized REC Display]={pre_reset_emphasized_rec_display!r}; expected {ALLOWED_EMPHASIZED_REC_MODES}."
        )
    if c_grid_disp is None:
        reset_split_ok = False
        _add_code(codes, STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION)
        errors.append(
            f"Invalid [Grid Line Display]={pre_reset_grid_line_display!r}; expected {ALLOWED_GRID_LINE_DISPLAY_MODES}."
        )
    if c_grid_type is None:
        reset_split_ok = False
        _add_code(codes, STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION)
        errors.append(
            f"Invalid [Grid Line Type]={pre_reset_grid_line_type!r}; expected {ALLOWED_GRID_LINE_TYPES}."
        )

    exp_post_emp = st["expected_post_emphasized_rec"]
    exp_post_grid_disp = st["expected_post_grid_display"]
    exp_post_grid_type = st["expected_post_grid_type"]

    if observed_post_reset_emphasized_rec_display is None:
        eff_post_emp = exp_post_emp
    else:
        n_obs_emp = _norm_on_off(observed_post_reset_emphasized_rec_display)
        eff_post_emp = (
            n_obs_emp
            if n_obs_emp is not None
            else observed_post_reset_emphasized_rec_display
        )
        if n_obs_emp is None or eff_post_emp != exp_post_emp:
            reset_split_ok = False
            _add_code(
                codes,
                STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION,
            )
            errors.append(
                f"[Emphasized REC Display] post-reset mismatch under {c_rst!r}: "
                f"got {eff_post_emp!r}, expected {exp_post_emp!r} "
                "(reset to 'On' by both [Camera Settings Reset] and [Initialize])."
            )

    if observed_post_reset_grid_line_display is None:
        eff_post_grid_disp = exp_post_grid_disp
    else:
        n_obs_gd = _norm_on_off(observed_post_reset_grid_line_display)
        eff_post_grid_disp = (
            n_obs_gd if n_obs_gd is not None else observed_post_reset_grid_line_display
        )
        if n_obs_gd is None or eff_post_grid_disp != exp_post_grid_disp:
            reset_split_ok = False
            _add_code(
                codes,
                STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION,
            )
            errors.append(
                f"[Grid Line Display] post-reset mismatch under {c_rst!r}: "
                f"got {eff_post_grid_disp!r}, expected {exp_post_grid_disp!r} "
                "(survives [Camera Settings Reset]; restored to 'Off' only by [Initialize])."
            )

    if observed_post_reset_grid_line_type is None:
        eff_post_grid_type = exp_post_grid_type
    else:
        n_obs_gt = _norm_grid_line_type(observed_post_reset_grid_line_type)
        eff_post_grid_type = (
            n_obs_gt if n_obs_gt is not None else observed_post_reset_grid_line_type
        )
        if n_obs_gt is None or eff_post_grid_type != exp_post_grid_type:
            reset_split_ok = False
            _add_code(
                codes,
                STATUS_BLOCKED_G89_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_VIOLATION,
            )
            errors.append(
                f"[Grid Line Type] post-reset mismatch under {c_rst!r}: "
                f"got {eff_post_grid_type!r}, expected {exp_post_grid_type!r} "
                "(survives [Camera Settings Reset]; restored to 'Rule of 3rds Grid' only by [Initialize])."
            )

    # 2. Forced [Off(HDMI Only)] / RAW Clean-Feed Clamps & HDMI Info Routing
    clamp_hdmionly = bool(st["forced_off_by_hdmi_only_clamp"])
    clamp_raw = bool(st["forced_off_by_hdmi_raw_clamp"])
    clamp_active = bool(st["hdmi_clean_feed_clamp_active"])
    exp_eff_hdmi_info = st["expected_effective_hdmi_info_display"]

    if observed_effective_hdmi_info_display is None:
        eff_hdmi_info = exp_eff_hdmi_info
    else:
        n_eff_hi = _norm_on_off(observed_effective_hdmi_info_display)
        eff_hdmi_info = (
            n_eff_hi
            if n_eff_hi is not None
            else observed_effective_hdmi_info_display
        )
        if n_eff_hi is None:
            _add_code(codes, STATUS_BLOCKED_G89_TELEMETRY_INVALID)
            errors.append(
                f"Invalid observed_effective_hdmi_info_display={observed_effective_hdmi_info_display!r}."
            )

    eff_lcd_blanked = (
        bool(st["expected_camera_lcd_blanked_by_hdmi_info"])
        if observed_camera_lcd_blanked_by_hdmi_info is None
        else bool(observed_camera_lcd_blanked_by_hdmi_info)
    )
    eff_lcd_emp = (
        bool(st["expected_local_lcd_emphasized_rec"])
        if observed_local_lcd_emphasized_rec_rendered is None
        else bool(observed_local_lcd_emphasized_rec_rendered)
    )
    eff_lcd_grid = (
        bool(st["expected_local_lcd_grid_line"])
        if observed_local_lcd_grid_line_rendered is None
        else bool(observed_local_lcd_grid_line_rendered)
    )
    eff_hdmi_emp = (
        bool(st["expected_hdmi_emphasized_rec"])
        if observed_hdmi_emphasized_rec_rendered is None
        else bool(observed_hdmi_emphasized_rec_rendered)
    )
    eff_hdmi_grid = (
        bool(st["expected_hdmi_grid_line"])
        if observed_hdmi_grid_line_rendered is None
        else bool(observed_hdmi_grid_line_rendered)
    )
    eff_hdmi_osd = (
        bool(st["expected_hdmi_status_osd"])
        if observed_hdmi_status_osd_rendered is None
        else bool(observed_hdmi_status_osd_rendered)
    )

    default_baked_px = (
        0
        if exp_eff_hdmi_info == HDMI_INFO_OFF
        else (1 if (eff_hdmi_emp or eff_hdmi_grid or eff_hdmi_osd) else 0)
    )
    eff_baked_px = (
        default_baked_px
        if observed_hdmi_baked_overlay_pixels is None
        else int(observed_hdmi_baked_overlay_pixels)
    )

    cleanfeed_ok = True
    if clamp_active and (
        eff_hdmi_info != HDMI_INFO_OFF
        or eff_hdmi_emp
        or eff_hdmi_grid
        or eff_hdmi_osd
        or eff_baked_px != 0
    ):
        cleanfeed_ok = False
        _add_code(
            codes,
            STATUS_BLOCKED_G89_FORCED_HDMIONLY_OR_RAW_CLEANFEED_CLAMP_LEAK,
        )
        errors.append(
            "Automatic HDMI clean-feed clamp violated while [Rec. Media dur HDMI Output]=Off(HDMI Only) "
            f"or HDMI RAW active: effective_hdmi_info={eff_hdmi_info!r}, hdmi_emp={eff_hdmi_emp}, "
            f"hdmi_grid={eff_hdmi_grid}, hdmi_osd={eff_hdmi_osd}, baked_pixels={eff_baked_px} (must all be Off/0)."
        )

    # 3. Local-LCD-Only Assist Overlays ([Marker], [Zebra], [Peaking]) Isolation
    local_only_ok = not (
        bool(observed_hdmi_local_only_marker_rendered)
        or bool(observed_hdmi_local_only_zebra_rendered)
        or bool(observed_hdmi_local_only_peaking_rendered)
    )
    if not local_only_ok:
        _add_code(codes, STATUS_BLOCKED_G89_LOCAL_LCD_ONLY_ASSIST_HDMI_LEAK)
        errors.append(
            "[Marker Display], [Zebra Display], and [Peaking Display] are strictly local-LCD-only "
            "on ILME-FX3 even when [HDMI Info. Display]=On: "
            f"marker={observed_hdmi_local_only_marker_rendered}, "
            f"zebra={observed_hdmi_local_only_zebra_rendered}, "
            f"peaking={observed_hdmi_local_only_peaking_rendered}."
        )

    # 4. HDMI Info Routing & Built-In LCD Blanking Consistency (when not clamped or when Off)
    routing_ok = (
        eff_hdmi_info == exp_eff_hdmi_info
        and eff_lcd_blanked == bool(st["expected_camera_lcd_blanked_by_hdmi_info"])
        and eff_lcd_emp == bool(st["expected_local_lcd_emphasized_rec"])
        and eff_lcd_grid == bool(st["expected_local_lcd_grid_line"])
        and eff_hdmi_emp == bool(st["expected_hdmi_emphasized_rec"])
        and eff_hdmi_grid == bool(st["expected_hdmi_grid_line"])
        and eff_hdmi_osd == bool(st["expected_hdmi_status_osd"])
        and ((exp_eff_hdmi_info != HDMI_INFO_OFF) or (eff_baked_px == 0))
    )
    if not routing_ok and cleanfeed_ok:
        _add_code(codes, STATUS_BLOCKED_G89_HDMI_INFO_ROUTING_OR_LCD_BLANKING_MISMATCH)
        errors.append(
            "HDMI Info routing / LCD blanking / Emphasized REC / Grid Line state mismatch: "
            f"eff_hdmi_info={eff_hdmi_info!r} (exp {exp_eff_hdmi_info!r}), "
            f"lcd_blanked={eff_lcd_blanked} (exp {st['expected_camera_lcd_blanked_by_hdmi_info']}), "
            f"hdmi_emp={eff_hdmi_emp} (exp {st['expected_hdmi_emphasized_rec']}), "
            f"hdmi_grid={eff_hdmi_grid} (exp {st['expected_hdmi_grid_line']}), "
            f"lcd_emp={eff_lcd_emp} (exp {st['expected_local_lcd_emphasized_rec']}), "
            f"lcd_grid={eff_lcd_grid} (exp {st['expected_local_lcd_grid_line']}), "
            f"baked_px={eff_baked_px}."
        )

    emp_reset_by_cam_rst = (
        c_rst in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE)
        and reset_split_ok
    )
    grid_survived_cam_rst = (c_rst != RESET_ACTION_INITIALIZE) and reset_split_ok

    valid = not codes
    status = STATUS_VERIFIED_G89 if valid else codes[0]
    return EmphasizedRecAndGridHdmiCleanFeedResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{int(body_model_id):08X}",
        firmware_version=firmware_version,
        emphasized_rec_menu_path=EMPHASIZED_REC_DISPLAY_MENU_PATH,
        grid_line_display_menu_path=GRID_LINE_DISPLAY_MENU_PATH,
        grid_line_type_menu_path=GRID_LINE_TYPE_MENU_PATH,
        hdmi_info_display_menu_path=HDMI_INFO_DISPLAY_MENU_PATH,
        pre_reset_emphasized_rec_display=c_emp or pre_reset_emphasized_rec_display,
        pre_reset_grid_line_display=c_grid_disp or pre_reset_grid_line_display,
        pre_reset_grid_line_type=c_grid_type or pre_reset_grid_line_type,
        reset_action=c_rst or reset_action,
        expected_post_reset_emphasized_rec_display=exp_post_emp,
        effective_post_reset_emphasized_rec_display=eff_post_emp,
        emphasized_rec_reset_by_camera_settings_reset=emp_reset_by_cam_rst,
        expected_post_reset_grid_line_display=exp_post_grid_disp,
        effective_post_reset_grid_line_display=eff_post_grid_disp,
        expected_post_reset_grid_line_type=exp_post_grid_type,
        effective_post_reset_grid_line_type=eff_post_grid_type,
        grid_line_survived_camera_settings_reset=grid_survived_cam_rst,
        emphasized_rec_vs_grid_reset_split_verified=reset_split_ok,
        shooting_state=c_shoot or shooting_state,
        movie_or_sq_recording_active=bool(st["movie_or_sq_recording_active"]),
        configured_hdmi_info_display=c_hdmi_info or configured_hdmi_info_display,
        rec_media_dur_hdmi_output=c_rec_media or rec_media_dur_hdmi_output,
        hdmi_raw_output=c_raw or hdmi_raw_output,
        forced_off_by_hdmi_only_clamp=clamp_hdmionly,
        forced_off_by_hdmi_raw_clamp=clamp_raw,
        hdmi_clean_feed_clamp_active=clamp_active,
        expected_effective_hdmi_info_display=exp_eff_hdmi_info,
        effective_hdmi_info_display=eff_hdmi_info,
        camera_lcd_blanked_by_hdmi_info=eff_lcd_blanked,
        local_lcd_emphasized_rec_rendered=eff_lcd_emp,
        local_lcd_grid_line_rendered=eff_lcd_grid,
        hdmi_emphasized_rec_rendered=eff_hdmi_emp,
        hdmi_grid_line_rendered=eff_hdmi_grid,
        hdmi_status_osd_rendered=eff_hdmi_osd,
        hdmi_local_only_marker_rendered=bool(observed_hdmi_local_only_marker_rendered),
        hdmi_local_only_zebra_rendered=bool(observed_hdmi_local_only_zebra_rendered),
        hdmi_local_only_peaking_rendered=bool(
            observed_hdmi_local_only_peaking_rendered
        ),
        hdmi_baked_overlay_pixels=eff_baked_px,
        hdmi_routing_and_cleanfeed_enforced=cleanfeed_ok
        and local_only_ok
        and routing_ok,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g89_emphasized_rec_and_grid_hdmi_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    emphasized_rec_grid_hdmi_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase237DonorAuditResult] = None,
) -> Tuple[GateVerdict, G89EmphasizedRecAndGridHdmiGuardResult]:
    """Evaluate Gate `G89` combining bounded `<0.15s` donor check with
    `[Emphasized REC Display]` & `[Grid Line]` HDMI Info routing vs forced
    `[Off(HDMI Only)]` / `RAW` clean-feed suppression guard.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase237_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_emphasized_rec_and_grid_hdmi_cleanfeed_guard(
        **dict(emphasized_rec_grid_hdmi_kwargs or {})
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
        errors.append("Gate G89 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G89 if valid else codes[0]

    res = G89EmphasizedRecAndGridHdmiGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        emphasized_rec_grid_hdmi_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, emp_rec={guard.effective_post_reset_emphasized_rec_display}, "
        f"grid={guard.effective_post_reset_grid_line_display}/{guard.effective_post_reset_grid_line_type}"
        f"(rst={guard.reset_action}), hdmi_info={guard.configured_hdmi_info_display}->{guard.effective_hdmi_info_display}"
        f"(clamp={guard.hdmi_clean_feed_clamp_active},baked_px={guard.hdmi_baked_overlay_pixels})"
    )
    verdict = GateVerdict(
        gate_id=G89_GATE_ID,
        gate_code=G89_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate `G90`: `[Touch Operation]` 4-Item `[Camera Settings Reset]` Survival,
#    Bench Accidental-Tap Lock & `[Monitor Brightness]` `Sunny Weather` Guard
# ---------------------------------------------------------------------------


def resolve_fx3_touch_op_4item_reset_and_bench_lock(
    *,
    pre_reset_touch_operation: str = TOUCH_OP_OFF,
    pre_reset_touch_sensitivity: str = TOUCH_SENSITIVITY_SENSITIVE,
    pre_reset_swipe_up: str = SWIPE_UP_OPEN_FN_MENU,
    pre_reset_touch_func_in_shooting: str = TOUCH_FUNC_SHOOTING_FOCUS,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    bench_unattended_tier0_active: bool = True,
) -> Dict[str, Any]:
    """Deterministically resolve all 4 `MENU -> Setup -> [Touch Operation]`
    items across `[Camera Settings Reset]` vs `[Initialize]` and evaluate
    unattended Tier-0 bench accidental-tap lock state.
    """
    c_touch_op = _norm_touch_operation(pre_reset_touch_operation)
    c_sens = _norm_touch_sensitivity(pre_reset_touch_sensitivity)
    c_swipe = _norm_swipe_up(pre_reset_swipe_up)
    c_func = _norm_touch_func_in_shooting(pre_reset_touch_func_in_shooting)
    c_rst = _norm_reset_action(reset_action)

    # All 4 Setup touch settings survive [Camera Settings Reset]; reset ONLY by [Initialize]
    if c_rst == RESET_ACTION_INITIALIZE:
        exp_touch_op = TOUCH_OPERATION_FACTORY_DEFAULT
        exp_sens = TOUCH_SENSITIVITY_FACTORY_DEFAULT
        exp_swipe = SWIPE_UP_FACTORY_DEFAULT
        exp_func = TOUCH_FUNC_IN_SHOOTING_FACTORY_DEFAULT
    else:
        exp_touch_op = c_touch_op or TOUCH_OPERATION_FACTORY_DEFAULT
        exp_sens = c_sens or TOUCH_SENSITIVITY_FACTORY_DEFAULT
        exp_swipe = c_swipe or SWIPE_UP_FACTORY_DEFAULT
        exp_func = c_func or TOUCH_FUNC_IN_SHOOTING_FACTORY_DEFAULT

    shooting_touch_locked = exp_touch_op in SAFE_BENCH_UNATTENDED_TOUCH_OPERATION_MODES
    bench_safe = (not bench_unattended_tier0_active) or shooting_touch_locked

    return {
        "canonical_pre_touch_operation": c_touch_op,
        "canonical_pre_touch_sensitivity": c_sens,
        "canonical_pre_swipe_up": c_swipe,
        "canonical_pre_touch_func_in_shooting": c_func,
        "canonical_reset_action": c_rst,
        "expected_post_touch_operation": exp_touch_op,
        "expected_post_touch_sensitivity": exp_sens,
        "expected_post_swipe_up": exp_swipe,
        "expected_post_touch_func_in_shooting": exp_func,
        "shooting_capacitive_touch_locked": shooting_touch_locked,
        "bench_touch_tap_lock_safe": bench_safe,
    }


def resolve_fx3_monitor_brightness_reset_and_sunny_guard(
    *,
    pre_reset_monitor_brightness_mode: str = MONITOR_BRIGHTNESS_MANUAL,
    pre_reset_manual_brightness_level: Any = MONITOR_BRIGHTNESS_MANUAL_FACTORY_DEFAULT_LEVEL,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    indoor_bench_environment: bool = True,
    npfz100_internal_battery_active: bool = True,
) -> Dict[str, Any]:
    """Deterministically resolve `MENU -> Setup -> [Monitor] -> [Monitor Brightness]`
    (`Manual` `-2..+2` vs `Sunny Weather`) across `[Camera Settings Reset]` vs
    `[Initialize]` and evaluate the indoor `NP-FZ100` bench `[Sunny Weather]` block.
    """
    c_mode = _norm_monitor_brightness_mode(pre_reset_monitor_brightness_mode)
    c_lvl = _parse_manual_brightness_level(pre_reset_manual_brightness_level)
    c_rst = _norm_reset_action(reset_action)

    # Setup [Monitor Brightness] survives [Camera Settings Reset]; reset ONLY by [Initialize]
    if c_rst == RESET_ACTION_INITIALIZE:
        exp_mode = MONITOR_BRIGHTNESS_FACTORY_DEFAULT_MODE
        exp_lvl = MONITOR_BRIGHTNESS_MANUAL_FACTORY_DEFAULT_LEVEL
    else:
        exp_mode = c_mode or MONITOR_BRIGHTNESS_FACTORY_DEFAULT_MODE
        exp_lvl = (
            c_lvl
            if c_lvl is not None
            else MONITOR_BRIGHTNESS_MANUAL_FACTORY_DEFAULT_LEVEL
        )

    sunny_indoor_violation = bool(indoor_bench_environment) and (
        exp_mode == MONITOR_BRIGHTNESS_SUNNY_WEATHER
    )

    return {
        "canonical_pre_mode": c_mode,
        "canonical_pre_manual_level": c_lvl,
        "canonical_reset_action": c_rst,
        "expected_post_mode": exp_mode,
        "expected_post_manual_level": exp_lvl,
        "indoor_bench_environment": bool(indoor_bench_environment),
        "npfz100_internal_battery_active": bool(npfz100_internal_battery_active),
        "sunny_weather_indoor_violation": sunny_indoor_violation,
        "sunny_weather_indoor_blocked": not sunny_indoor_violation,
    }


def verify_touch_op_reset_and_sunny_weather_bench_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE237,
    pre_reset_touch_operation: str = TOUCH_OP_OFF,
    pre_reset_touch_sensitivity: str = TOUCH_SENSITIVITY_SENSITIVE,
    pre_reset_swipe_up: str = SWIPE_UP_OPEN_FN_MENU,
    pre_reset_touch_func_in_shooting: str = TOUCH_FUNC_SHOOTING_FOCUS,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    observed_post_reset_touch_operation: Optional[str] = None,
    observed_post_reset_touch_sensitivity: Optional[str] = None,
    observed_post_reset_swipe_up: Optional[str] = None,
    observed_post_reset_touch_func_in_shooting: Optional[str] = None,
    bench_unattended_tier0_active: bool = True,
    observed_accidental_fn_swipe_triggered: bool = False,
    observed_accidental_touch_tracking_triggered: bool = False,
    pre_reset_monitor_brightness_mode: str = MONITOR_BRIGHTNESS_MANUAL,
    pre_reset_manual_brightness_level: Any = MONITOR_BRIGHTNESS_MANUAL_FACTORY_DEFAULT_LEVEL,
    observed_post_reset_monitor_brightness_mode: Optional[str] = None,
    observed_post_reset_manual_brightness_level: Optional[Any] = None,
    indoor_bench_environment: bool = True,
    npfz100_internal_battery_active: bool = True,
) -> TouchOpResetSurvivalAndSunnyWeatherResult:
    """Verify Gate `G90` invariants across all 4 `[Touch Operation]` Setup items
    surviving `[Camera Settings Reset]`, unattended Tier-0 bench capacitive tap
    lockout (`Off` / `On: Playback Only`), and `[Monitor Brightness]` (`Manual`
    `-2..+2` vs `Sunny Weather`) reset survival + indoor `NP-FZ100` bench guard.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        body_model_name.strip().upper() != FX3_MODEL_NAME
        or int(body_model_id) != FX3_MODEL_ID
    ):
        _add_code(codes, STATUS_BLOCKED_G90_TELEMETRY_INVALID)
        errors.append(
            f"Gate G90 requires ILME-FX3 (0x{FX3_MODEL_ID:08X}); got {body_model_name!r} (0x{int(body_model_id):08X})."
        )
    if fw_tuple is None or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE237:
        _add_code(codes, STATUS_BLOCKED_G90_TELEMETRY_INVALID)
        errors.append(
            f"Gate G90 requires valid ILME-FX3 firmware version (>= 1.00); got {firmware_version!r}."
        )

    t_state = resolve_fx3_touch_op_4item_reset_and_bench_lock(
        pre_reset_touch_operation=pre_reset_touch_operation,
        pre_reset_touch_sensitivity=pre_reset_touch_sensitivity,
        pre_reset_swipe_up=pre_reset_swipe_up,
        pre_reset_touch_func_in_shooting=pre_reset_touch_func_in_shooting,
        reset_action=reset_action,
        bench_unattended_tier0_active=bench_unattended_tier0_active,
    )
    b_state = resolve_fx3_monitor_brightness_reset_and_sunny_guard(
        pre_reset_monitor_brightness_mode=pre_reset_monitor_brightness_mode,
        pre_reset_manual_brightness_level=pre_reset_manual_brightness_level,
        reset_action=reset_action,
        indoor_bench_environment=indoor_bench_environment,
        npfz100_internal_battery_active=npfz100_internal_battery_active,
    )

    c_rst = t_state["canonical_reset_action"]
    if c_rst is None:
        _add_code(codes, STATUS_BLOCKED_G90_TELEMETRY_INVALID)
        errors.append(
            f"Invalid reset_action={reset_action!r}; expected {ALLOWED_RESET_ACTIONS_PHASE237}."
        )

    # 1. Validate all 4 [Touch Operation] Setup items & [Camera Settings Reset] survival
    touch_4item_ok = True
    c_pre_op = t_state["canonical_pre_touch_operation"]
    c_pre_sens = t_state["canonical_pre_touch_sensitivity"]
    c_pre_swipe = t_state["canonical_pre_swipe_up"]
    c_pre_func = t_state["canonical_pre_touch_func_in_shooting"]

    if c_pre_op is None:
        touch_4item_ok = False
        _add_code(codes, STATUS_BLOCKED_G90_TOUCH_OPERATION_4ITEM_INVALID_OR_RESET_VIOLATION)
        errors.append(
            f"Invalid [Touch Operation]={pre_reset_touch_operation!r}; expected {ALLOWED_TOUCH_OPERATION_MODES}."
        )
    if c_pre_sens is None:
        touch_4item_ok = False
        _add_code(codes, STATUS_BLOCKED_G90_TOUCH_OPERATION_4ITEM_INVALID_OR_RESET_VIOLATION)
        errors.append(
            f"Invalid [Touch Sensitivity]={pre_reset_touch_sensitivity!r}; expected {ALLOWED_TOUCH_SENSITIVITY_MODES}."
        )
    if c_pre_swipe is None:
        touch_4item_ok = False
        _add_code(codes, STATUS_BLOCKED_G90_TOUCH_OPERATION_4ITEM_INVALID_OR_RESET_VIOLATION)
        errors.append(
            f"Invalid [Swipe Up]={pre_reset_swipe_up!r}; expected {ALLOWED_SWIPE_UP_MODES}."
        )
    if c_pre_func is None:
        touch_4item_ok = False
        _add_code(codes, STATUS_BLOCKED_G90_TOUCH_OPERATION_4ITEM_INVALID_OR_RESET_VIOLATION)
        errors.append(
            f"Invalid [Touch Func. in Shooting]={pre_reset_touch_func_in_shooting!r}; expected {ALLOWED_TOUCH_FUNC_IN_SHOOTING_MODES}."
        )

    exp_op = t_state["expected_post_touch_operation"]
    exp_sens = t_state["expected_post_touch_sensitivity"]
    exp_swipe = t_state["expected_post_swipe_up"]
    exp_func = t_state["expected_post_touch_func_in_shooting"]

    if observed_post_reset_touch_operation is None:
        eff_op = exp_op
    else:
        n_op = _norm_touch_operation(observed_post_reset_touch_operation)
        eff_op = n_op if n_op is not None else observed_post_reset_touch_operation
        if n_op is None or eff_op != exp_op:
            touch_4item_ok = False
            _add_code(
                codes,
                STATUS_BLOCKED_G90_TOUCH_OPERATION_4ITEM_INVALID_OR_RESET_VIOLATION,
            )
            errors.append(
                f"[Touch Operation] post-reset mismatch under {c_rst!r}: got {eff_op!r}, expected {exp_op!r}."
            )

    if observed_post_reset_touch_sensitivity is None:
        eff_sens = exp_sens
    else:
        n_sens = _norm_touch_sensitivity(observed_post_reset_touch_sensitivity)
        eff_sens = (
            n_sens if n_sens is not None else observed_post_reset_touch_sensitivity
        )
        if n_sens is None or eff_sens != exp_sens:
            touch_4item_ok = False
            _add_code(
                codes,
                STATUS_BLOCKED_G90_TOUCH_OPERATION_4ITEM_INVALID_OR_RESET_VIOLATION,
            )
            errors.append(
                f"[Touch Sensitivity] post-reset mismatch under {c_rst!r}: got {eff_sens!r}, expected {exp_sens!r}."
            )

    if observed_post_reset_swipe_up is None:
        eff_swipe = exp_swipe
    else:
        n_sw = _norm_swipe_up(observed_post_reset_swipe_up)
        eff_swipe = n_sw if n_sw is not None else observed_post_reset_swipe_up
        if n_sw is None or eff_swipe != exp_swipe:
            touch_4item_ok = False
            _add_code(
                codes,
                STATUS_BLOCKED_G90_TOUCH_OPERATION_4ITEM_INVALID_OR_RESET_VIOLATION,
            )
            errors.append(
                f"[Swipe Up] post-reset mismatch under {c_rst!r}: got {eff_swipe!r}, expected {exp_swipe!r}."
            )

    if observed_post_reset_touch_func_in_shooting is None:
        eff_func = exp_func
    else:
        n_fn = _norm_touch_func_in_shooting(observed_post_reset_touch_func_in_shooting)
        eff_func = (
            n_fn if n_fn is not None else observed_post_reset_touch_func_in_shooting
        )
        if n_fn is None or eff_func != exp_func:
            touch_4item_ok = False
            _add_code(
                codes,
                STATUS_BLOCKED_G90_TOUCH_OPERATION_4ITEM_INVALID_OR_RESET_VIOLATION,
            )
            errors.append(
                f"[Touch Func. in Shooting] post-reset mismatch under {c_rst!r}: got {eff_func!r}, expected {exp_func!r}."
            )

    # 2. Bench Unattended Tier-0 Capacitive Accidental-Tap Lock
    shooting_touch_locked = eff_op in SAFE_BENCH_UNATTENDED_TOUCH_OPERATION_MODES
    no_accidental_triggers = not (
        bool(observed_accidental_fn_swipe_triggered)
        or bool(observed_accidental_touch_tracking_triggered)
    )
    bench_tap_ok = True
    if bool(bench_unattended_tier0_active) and (
        not shooting_touch_locked or not no_accidental_triggers
    ):
        bench_tap_ok = False
        _add_code(codes, STATUS_BLOCKED_G90_BENCH_UNATTENDED_TOUCH_SHOOTING_LIVE_HAZARD)
        errors.append(
            "Unattended Tier-0 bench run requires [Touch Operation] in ('Off', 'On: Playback Only') "
            "with zero accidental Fn swipe / Touch Tracking triggers: "
            f"effective_touch_op={eff_op!r}, fn_swipe={observed_accidental_fn_swipe_triggered}, "
            f"touch_tracking={observed_accidental_touch_tracking_triggered}."
        )
    elif not no_accidental_triggers:
        bench_tap_ok = False
        _add_code(codes, STATUS_BLOCKED_G90_BENCH_UNATTENDED_TOUCH_SHOOTING_LIVE_HAZARD)
        errors.append(
            "Accidental capacitive Fn swipe or Touch Tracking trigger detected while shooting touch was locked."
        )

    # 3. [Monitor Brightness] Manual (-2..+2) vs Sunny Weather Persistence & Indoor Guard
    brightness_persist_ok = True
    c_pre_mode = b_state["canonical_pre_mode"]
    c_pre_lvl = b_state["canonical_pre_manual_level"]

    if c_pre_mode is None:
        brightness_persist_ok = False
        _add_code(
            codes,
            STATUS_BLOCKED_G90_MONITOR_BRIGHTNESS_INVALID_OR_RESET_VIOLATION,
        )
        errors.append(
            f"Invalid [Monitor Brightness] mode={pre_reset_monitor_brightness_mode!r}; "
            f"expected {ALLOWED_MONITOR_BRIGHTNESS_MODES}."
        )
    if c_pre_lvl is None:
        brightness_persist_ok = False
        _add_code(
            codes,
            STATUS_BLOCKED_G90_MONITOR_BRIGHTNESS_INVALID_OR_RESET_VIOLATION,
        )
        errors.append(
            f"Invalid [Monitor Brightness] Manual level={pre_reset_manual_brightness_level!r}; "
            f"expected integer in {MONITOR_BRIGHTNESS_MANUAL_MIN}..+{MONITOR_BRIGHTNESS_MANUAL_MAX}."
        )

    exp_b_mode = b_state["expected_post_mode"]
    exp_b_lvl = b_state["expected_post_manual_level"]

    if observed_post_reset_monitor_brightness_mode is None:
        eff_b_mode = exp_b_mode
    else:
        n_bm = _norm_monitor_brightness_mode(
            observed_post_reset_monitor_brightness_mode
        )
        eff_b_mode = (
            n_bm
            if n_bm is not None
            else observed_post_reset_monitor_brightness_mode
        )
        if n_bm is None or eff_b_mode != exp_b_mode:
            brightness_persist_ok = False
            _add_code(
                codes,
                STATUS_BLOCKED_G90_MONITOR_BRIGHTNESS_INVALID_OR_RESET_VIOLATION,
            )
            errors.append(
                f"[Monitor Brightness] mode post-reset mismatch under {c_rst!r}: "
                f"got {eff_b_mode!r}, expected {exp_b_mode!r} "
                "(survives [Camera Settings Reset]; restored to 'Manual' only by [Initialize])."
            )

    if observed_post_reset_manual_brightness_level is None:
        eff_b_lvl = exp_b_lvl
    else:
        p_bl = _parse_manual_brightness_level(
            observed_post_reset_manual_brightness_level
        )
        if p_bl is None or p_bl != exp_b_lvl:
            brightness_persist_ok = False
            eff_b_lvl = p_bl if p_bl is not None else -99
            _add_code(
                codes,
                STATUS_BLOCKED_G90_MONITOR_BRIGHTNESS_INVALID_OR_RESET_VIOLATION,
            )
            errors.append(
                f"[Monitor Brightness] Manual level post-reset mismatch under {c_rst!r}: "
                f"got {observed_post_reset_manual_brightness_level!r}, expected {exp_b_lvl!r}."
            )
        else:
            eff_b_lvl = p_bl

    # 4. Indoor NP-FZ100 Bench [Sunny Weather] Block
    sunny_indoor_ok = not (
        bool(indoor_bench_environment)
        and eff_b_mode == MONITOR_BRIGHTNESS_SUNNY_WEATHER
    )
    if not sunny_indoor_ok:
        _add_code(
            codes,
            STATUS_BLOCKED_G90_SUNNY_WEATHER_INDOOR_BENCH_BRIGHTNESS_OR_POWER_HAZARD,
        )
        errors.append(
            "[Monitor Brightness]=[Sunny Weather] is blocked during indoor shooting / NP-FZ100 bench runs "
            "(too bright for indoor exposure judgment and increases LCD backlight thermal/battery draw; "
            "lock to [Manual] -2..+2)."
        )

    touch_survived_cam_rst = (c_rst != RESET_ACTION_INITIALIZE) and touch_4item_ok
    brightness_survived_cam_rst = (
        c_rst != RESET_ACTION_INITIALIZE
    ) and brightness_persist_ok

    valid = not codes
    status = STATUS_VERIFIED_G90 if valid else codes[0]
    return TouchOpResetSurvivalAndSunnyWeatherResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{int(body_model_id):08X}",
        firmware_version=firmware_version,
        touch_operation_menu_path=TOUCH_OPERATION_MENU_PATH,
        monitor_brightness_menu_path=MONITOR_BRIGHTNESS_MENU_PATH,
        pre_reset_touch_operation=c_pre_op or pre_reset_touch_operation,
        pre_reset_touch_sensitivity=c_pre_sens or pre_reset_touch_sensitivity,
        pre_reset_swipe_up=c_pre_swipe or pre_reset_swipe_up,
        pre_reset_touch_func_in_shooting=c_pre_func
        or pre_reset_touch_func_in_shooting,
        reset_action=c_rst or reset_action,
        expected_post_reset_touch_operation=exp_op,
        effective_post_reset_touch_operation=eff_op,
        expected_post_reset_touch_sensitivity=exp_sens,
        effective_post_reset_touch_sensitivity=eff_sens,
        expected_post_reset_swipe_up=exp_swipe,
        effective_post_reset_swipe_up=eff_swipe,
        expected_post_reset_touch_func_in_shooting=exp_func,
        effective_post_reset_touch_func_in_shooting=eff_func,
        all_4_touch_items_survived_camera_settings_reset=touch_survived_cam_rst,
        bench_unattended_tier0_active=bool(bench_unattended_tier0_active),
        shooting_capacitive_touch_locked=shooting_touch_locked,
        accidental_fn_swipe_or_tracking_blocked=no_accidental_triggers,
        bench_touch_tap_lock_enforced=bench_tap_ok,
        pre_reset_monitor_brightness_mode=c_pre_mode
        or pre_reset_monitor_brightness_mode,
        pre_reset_manual_brightness_level=c_pre_lvl if c_pre_lvl is not None else -99,
        expected_post_reset_monitor_brightness_mode=exp_b_mode,
        effective_post_reset_monitor_brightness_mode=eff_b_mode,
        expected_post_reset_manual_brightness_level=exp_b_lvl,
        effective_post_reset_manual_brightness_level=eff_b_lvl,
        monitor_brightness_survived_camera_settings_reset=brightness_survived_cam_rst,
        indoor_bench_environment=bool(indoor_bench_environment),
        npfz100_internal_battery_active=bool(npfz100_internal_battery_active),
        sunny_weather_indoor_blocked=sunny_indoor_ok,
        indoor_brightness_and_power_guard_enforced=brightness_persist_ok
        and sunny_indoor_ok,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g90_touch_op_reset_and_sunny_weather_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    touch_op_sunny_weather_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase237DonorAuditResult] = None,
) -> Tuple[GateVerdict, G90TouchOpResetAndSunnyWeatherGuardResult]:
    """Evaluate Gate `G90` combining bounded `<0.15s` donor check with 4-item
    `[Touch Operation]` `[Camera Settings Reset]` survival + unattended bench
    capacitive tap lock and `[Monitor Brightness]` `Sunny Weather` indoor guard.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase237_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_touch_op_reset_and_sunny_weather_bench_guard(
        **dict(touch_op_sunny_weather_kwargs or {})
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
        errors.append("Gate G90 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G90 if valid else codes[0]

    res = G90TouchOpResetAndSunnyWeatherGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        touch_op_sunny_weather_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, touch=({guard.effective_post_reset_touch_operation},"
        f"{guard.effective_post_reset_touch_sensitivity},{guard.effective_post_reset_swipe_up},"
        f"{guard.effective_post_reset_touch_func_in_shooting};rst={guard.reset_action};"
        f"bench_locked={guard.shooting_capacitive_touch_locked}), "
        f"brightness={guard.effective_post_reset_monitor_brightness_mode}({guard.effective_post_reset_manual_brightness_level})"
    )
    verdict = GateVerdict(
        gate_id=G90_GATE_ID,
        gate_code=G90_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `90/90` Milestone Master Safety Preflight (`G01..G90`)
# ---------------------------------------------------------------------------


def evaluate_90gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    emphasized_rec_grid_hdmi_kwargs: Optional[Mapping[str, Any]] = None,
    touch_op_sunny_weather_kwargs: Optional[Mapping[str, Any]] = None,
    master_88_override: Optional[Master88GateReport] = None,
    **m88_passthrough_kwargs: Any,
) -> Master90GateReport:
    """Evaluate all 90 Master Safety Gates (`G01..G90`) deterministically by
    delegating `G01..G88` directly to `evaluate_88gate_preflight()`.
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

    m88_report: Master88GateReport = (
        master_88_override
        if master_88_override is not None
        else evaluate_88gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m88_passthrough_kwargs,
        )
    )

    phase237_audit = audit_phase237_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g89_verdict, g89_res = evaluate_g89_emphasized_rec_and_grid_hdmi_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        emphasized_rec_grid_hdmi_kwargs=emphasized_rec_grid_hdmi_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase237_audit,
    )

    g90_verdict, g90_res = evaluate_g90_touch_op_reset_and_sunny_weather_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        touch_op_sunny_weather_kwargs=touch_op_sunny_weather_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase237_audit,
    )

    gates_89_to_90 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g89_verdict, g90_verdict)
    ]
    all_gates = tuple(list(m88_report.gates) + gates_89_to_90)

    g01_to_g12_verified = int(m88_report.summary["g01_to_g12_verified"])
    g13_to_g88_verified = (
        int(m88_report.summary["g13_to_g86_verified"])
        + int(m88_report.summary["g87_to_g88_verified"])
    )
    g89_to_g90_verified = sum(1 for v in (g89_verdict, g90_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g88_verified + g89_to_g90_verified

    g89_to_g90_all_passed = g89_to_g90_verified == 2
    g13_to_g90_all_passed = m88_report.g13_to_g88_all_passed and g89_to_g90_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m88_report.gates[:9])

    offline_87_verified = (
        g01_to_g09_ok
        and m88_report.offline_85_gates_verified
        and g89_to_g90_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_90_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g90_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m88_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_87_verified
        and m88_report.h0_h1_trial_entry_allowed
        and g89_to_g90_all_passed
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
        list(m88_report.errors) + list(g89_verdict.errors) + list(g90_verdict.errors)
    )
    warnings: List[str] = (
        list(m88_report.warnings)
        + list(g89_verdict.warnings)
        + list(g90_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m88_report.g13_to_g88_all_passed:
        overall_status = m88_report.status
    elif not g89_verdict.passed:
        overall_status = g89_verdict.status
    elif not g90_verdict.passed:
        overall_status = g90_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_90_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_90_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_90_verified:
        overall_status = "VERIFIED_ALL_90_GATES"
    else:
        overall_status = "VERIFIED_87_OF_90_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m88_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g89_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g90_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 90,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 90 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g88_verified": g13_to_g88_verified,
        "g89_to_g90_verified": g89_to_g90_verified,
        "g13_to_g90_all_passed": g13_to_g90_all_passed,
        "g89_to_g90_all_passed": g89_to_g90_all_passed,
        "offline_87_gates_verified": offline_87_verified,
        "all_90_gates_verified": all_90_verified,
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

    return Master90GateReport(
        schema=REALHW_EMPHASIZED_REC_GRID_HDMI_TOUCH_SUNNY_90GATE_SCHEMA,
        version=REALHW_EMPHASIZED_REC_GRID_HDMI_TOUCH_SUNNY_90GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_87_gates_verified=offline_87_verified,
        all_90_gates_verified=all_90_verified,
        g13_to_g90_all_passed=g13_to_g90_all_passed,
        g89_to_g90_all_passed=g89_to_g90_all_passed,
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
        master_88_report=m88_report.to_dict(),
        g89_result=g89_res.to_dict(),
        g90_result=g90_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_90_master_safety_gates = evaluate_90gate_preflight
run_90_gate_preflight = evaluate_90gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_emphasized_rec_grid_hdmi_touch_sunny_and_90gate_guard",
        description=(
            "Phase 237 (90/90 Milestone) Safety Gates G89 (Emphasized REC Display & "
            "Grid Line HDMI Info Routing vs Forced Off(HDMI Only)/RAW Clean-Feed "
            "Suppression) + G90 (Touch Operation 4-Item Camera Settings Reset Survival "
            "+ Bench Accidental-Tap Lock & Monitor Brightness Manual vs Sunny Weather "
            "Indoor Guard) + Unified 90-Gate Master Safety Preflight"
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

    report = evaluate_90gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        try:
            sys.stdout.write(
                json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
            )
            sys.stdout.flush()
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            os.close(devnull)
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/90 "
            f"g89_to_g90_all_passed={report.g89_to_g90_all_passed} "
            f"all_90_gates_verified={report.all_90_gates_verified} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
            f"usb_packets_transmitted={report.usb_packets_transmitted} "
            f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        report.all_90_gates_verified
        if args.dry_run_simulated
        else report.offline_87_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
