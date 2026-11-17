"""Phase 271 (Task H306, Milestone 110/110 Safety Gates, Wave-45) Sony `ILME-FX3`
(`Ver. 7.02`, `ilc/2210`) Safety Gates `G109` (`[Focus Assistant]`
`[Auto Magnifier in MF]` vs Legacy `MF Assist`, `Custom Button 5`,
`[Focus Magnif. Time] = [No Limit]`, Separate Still/Movie `[Initial Focus Mag.]`
`[x1.0]`, Still-Only `[AF in Focus Mag.]`, `[Peaking Display]` Clean-HDMI
Isolation & Still-Only `[AF Illuminator]`) & `G110` (`[Area/Date/Time Setting]`
vs Legacy `Date/Time Setup`, `[Camera Settings Reset]` Survival, Zero-RF
Creators' App Suppression, `[Video Light Mode] = [Power Link]` + MI-Shoe `5V`
`<= 900 mA` Rail Budget & `[HDMI Resolution] = [Auto]` + Log Internal-Recording
`1080p` Downshift Override) + Unified `110`-Gate Master Safety Preflight
(`G01..G110`).

Operationalizes Wave-45 official Sony `ILME-FX3` (`Ver. 7.02`, Help Guide
`ilc/2210`) intelligence
(`reports/2026-11-15-global-sony-wave45-milestone-focus-magnifier-auto-mag-mf-area-datetime-video-light-hdmi-res-intel/README.md`)
as deterministic offline preflight verifiers (`G109` and `G110`) and delegates
`G01..G108` directly to `evaluate_108gate_preflight()`.
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
from .realhw_file_settings_gamma_assist_tcub_and_108gate_guard import (
    Master108GateReport,
    evaluate_108gate_preflight,
)
from .realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard import (
    _DONOR_BLOB_CACHE,
)
from .realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import SPI_NOR_WRITE_AUTHORIZED
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_FOCUS_MAG_DATETIME_VIDEOLIGHT_HDMIRES_110GATE_SCHEMA: str = (
    "realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard_v1"
)
REALHW_FOCUS_MAG_DATETIME_VIDEOLIGHT_HDMIRES_110GATE_VERSION: str = "1.0.0"

G109_GATE_ID: str = (
    "G109_focus_magnifier_auto_mag_mf_initial_x10_peaking_and_still_af_illuminator_guard"
)
G109_GATE_CODE: str = (
    "FOCUS_MAGNIFIER_AUTO_MAG_MF_INITIAL_X10_PEAKING_AND_STILL_AF_ILLUMINATOR_GUARD"
)

G110_GATE_ID: str = (
    "G110_area_datetime_zero_rf_video_light_power_link_and_hdmi_res_log_override_guard"
)
G110_GATE_CODE: str = (
    "AREA_DATETIME_ZERO_RF_VIDEO_LIGHT_POWER_LINK_AND_HDMI_RES_LOG_OVERRIDE_GUARD"
)

G109: str = G109_GATE_ID
G110: str = G110_GATE_ID
GATE_G109_FOCUS_MAGNIFIER_AUTO_MAG_MF_INITIAL_X10_PEAKING_AND_STILL_AF_ILLUMINATOR_GUARD: str = (
    G109_GATE_CODE
)
GATE_G110_AREA_DATETIME_ZERO_RF_VIDEO_LIGHT_POWER_LINK_AND_HDMI_RES_LOG_OVERRIDE_GUARD: str = (
    G110_GATE_CODE
)

ENV_CLEAN_ROOM_TEST_PHASE271: str = "FX3_CLEAN_ROOM_TEST"

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE271: float = 0.10
DONOR_CHECK_CI_MAX_SECONDS_PHASE271: float = 0.50
DONOR_CHECK_MAX_SECONDS: float = DONOR_CHECK_MAX_SECONDS_PHASE271

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX6_MODEL_NAME: str = "ILME-FX6"
FX3_DEFAULT_FW_VERSION_PHASE271: str = "7.02"
FX3_HELP_GUIDE_CODE_PHASE271: str = "ilc/2210"

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE271: str = "Reset Network Set."
RESET_ACTION_INITIALIZE: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE271: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_RESET_NETWORK_SET_PHASE271,
    RESET_ACTION_INITIALIZE,
)

# ---------------------------------------------------------------------------
# Status & Violation Codes (G109 / G110 / Phase 271)
# ---------------------------------------------------------------------------

STATUS_VERIFIED_G109: str = (
    "VERIFIED_G109_FOCUS_MAG_PEAKING_CLEAN_HDMI_AND_STILL_AF_ILLUMINATOR_SAFE"
)
STATUS_VERIFIED_G110: str = (
    "VERIFIED_G110_AREA_DATETIME_ZERO_RF_VIDEO_LIGHT_AND_HDMI_RES_SAFE"
)
STATUS_BLOCKED_PHASE271_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE271_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G109_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF_VIOLATION: str = (
    "BLOCKED_G109_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G109_FOCUS_MAG_DEFAULTS_OR_CUSTOM_BTN5_VIOLATION: str = (
    "BLOCKED_G109_FOCUS_MAG_DEFAULTS_OR_CUSTOM_BTN5_VIOLATION"
)
STATUS_BLOCKED_G109_HDMI_CLEAN_FEED_OVERLAY_LEAK_VIOLATION: str = (
    "BLOCKED_G109_HDMI_CLEAN_FEED_OVERLAY_LEAK_VIOLATION"
)
STATUS_BLOCKED_G109_STILL_ONLY_AF_ILLUMINATOR_OR_AF_IN_MAG_VIOLATION: str = (
    "BLOCKED_G109_STILL_ONLY_AF_ILLUMINATOR_OR_AF_IN_MAG_VIOLATION"
)
STATUS_BLOCKED_G109_RESET_BEHAVIOR_VIOLATION: str = (
    "BLOCKED_G109_RESET_BEHAVIOR_VIOLATION"
)
STATUS_BLOCKED_G109_TELEMETRY_INVALID: str = (
    "BLOCKED_G109_FOCUS_MAG_PEAKING_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G110_LEGACY_DATETIME_SETUP_SPOOF_VIOLATION: str = (
    "BLOCKED_G110_LEGACY_DATETIME_SETUP_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G110_ZERO_RF_CREATORS_APP_SYNC_VIOLATION: str = (
    "BLOCKED_G110_ZERO_RF_CREATORS_APP_SYNC_VIOLATION"
)
STATUS_BLOCKED_G110_MISHOE_5V_OVERCURRENT_VIOLATION: str = (
    "BLOCKED_G110_MISHOE_5V_OVERCURRENT_VIOLATION"
)
STATUS_BLOCKED_G110_HDMI_RES_LOG_1080P_OVERRIDE_VIOLATION: str = (
    "BLOCKED_G110_HDMI_RES_LOG_1080P_OVERRIDE_VIOLATION"
)
STATUS_BLOCKED_G110_SETUP_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G110_SETUP_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G110_TELEMETRY_INVALID: str = (
    "BLOCKED_G110_AREA_DATETIME_VIDEOLIGHT_HDMIRES_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G109 Constants: [Focus Assistant], [Peaking Display] & [AF Illuminator]
# ---------------------------------------------------------------------------

FOCUS_ASSISTANT_MENU_PATH_G109: str = "MENU -> Focus -> [Focus Assistant]"
PEAKING_DISPLAY_MENU_PATH_G109: str = "MENU -> Focus -> [Peaking Display]"
AF_ILLUMINATOR_MENU_PATH_G109: str = "MENU -> Focus -> [AF/MF] -> [AF Illuminator]"
HDMI_INFO_DISPLAY_MENU_PATH_G109: str = (
    "MENU -> Setup -> [External Output] -> [HDMI Info. Display]"
)

CANONICAL_AUTO_MAG_IN_MF_LABEL_G109: str = "Auto Magnifier in MF"
LEGACY_SPOOF_MF_ASSIST_LABEL_G109: str = "MF Assist"

SHOOT_MODE_STILL_G109: str = "Still"
SHOOT_MODE_MOVIE_G109: str = "Movie"
SHOOT_MODE_SQ_G109: str = "S&Q"
ALLOWED_SHOOT_MODES_G109: Tuple[str, ...] = (
    SHOOT_MODE_STILL_G109,
    SHOOT_MODE_MOVIE_G109,
    SHOOT_MODE_SQ_G109,
)

FOCUS_MODE_MF_G109: str = "MF"
FOCUS_MODE_DMF_G109: str = "DMF"
FOCUS_MODE_AF_S_G109: str = "AF-S"
FOCUS_MODE_AF_C_G109: str = "AF-C"
ALLOWED_FOCUS_MODES_G109: Tuple[str, ...] = (
    FOCUS_MODE_MF_G109,
    FOCUS_MODE_DMF_G109,
    FOCUS_MODE_AF_S_G109,
    FOCUS_MODE_AF_C_G109,
)

ON_G109: str = "On"
OFF_G109: str = "Off"
ALLOWED_ON_OFF_STATES_G109: Tuple[str, ...] = (ON_G109, OFF_G109)

AUTO_MAG_IN_MF_FACTORY_DEFAULT_G109: str = ON_G109
FOCUS_MAG_CUSTOM_BUTTON_DEFAULT_G109: str = "Custom Button 5"

FOCUS_MAG_TIME_2_SEC_G109: str = "2 Sec"
FOCUS_MAG_TIME_5_SEC_G109: str = "5 Sec"
FOCUS_MAG_TIME_NO_LIMIT_G109: str = "No Limit"
ALLOWED_FOCUS_MAG_TIMES_G109: Tuple[str, ...] = (
    FOCUS_MAG_TIME_2_SEC_G109,
    FOCUS_MAG_TIME_5_SEC_G109,
    FOCUS_MAG_TIME_NO_LIMIT_G109,
)
FOCUS_MAG_TIME_FACTORY_DEFAULT_G109: str = FOCUS_MAG_TIME_NO_LIMIT_G109

INITIAL_FOCUS_MAG_X1_0_G109: str = "x1.0"
INITIAL_FOCUS_MAG_X4_0_G109: str = "x4.0"
ALLOWED_INITIAL_FOCUS_MAGS_G109: Tuple[str, ...] = (
    INITIAL_FOCUS_MAG_X1_0_G109,
    INITIAL_FOCUS_MAG_X4_0_G109,
)
INITIAL_FOCUS_MAG_STILL_FACTORY_DEFAULT_G109: str = INITIAL_FOCUS_MAG_X1_0_G109
INITIAL_FOCUS_MAG_MOVIE_FACTORY_DEFAULT_G109: str = INITIAL_FOCUS_MAG_X1_0_G109

AF_IN_FOCUS_MAG_FACTORY_DEFAULT_G109: str = ON_G109

PEAKING_DISPLAY_FACTORY_DEFAULT_G109: str = OFF_G109
PEAKING_SELECT_DEFAULT_BUTTON_G109: str = "Control Wheel Right"

PEAKING_LEVEL_HIGH_G109: str = "High"
PEAKING_LEVEL_MID_G109: str = "Mid"
PEAKING_LEVEL_LOW_G109: str = "Low"
ALLOWED_PEAKING_LEVELS_G109: Tuple[str, ...] = (
    PEAKING_LEVEL_HIGH_G109,
    PEAKING_LEVEL_MID_G109,
    PEAKING_LEVEL_LOW_G109,
)
PEAKING_LEVEL_FACTORY_DEFAULT_G109: str = PEAKING_LEVEL_MID_G109

PEAKING_COLOR_RED_G109: str = "Red"
PEAKING_COLOR_YELLOW_G109: str = "Yellow"
PEAKING_COLOR_BLUE_G109: str = "Blue"
PEAKING_COLOR_WHITE_G109: str = "White"
ALLOWED_PEAKING_COLORS_G109: Tuple[str, ...] = (
    PEAKING_COLOR_RED_G109,
    PEAKING_COLOR_YELLOW_G109,
    PEAKING_COLOR_BLUE_G109,
    PEAKING_COLOR_WHITE_G109,
)
PEAKING_COLOR_FACTORY_DEFAULT_G109: str = PEAKING_COLOR_WHITE_G109

AF_ILLUMINATOR_AUTO_G109: str = "Auto"
AF_ILLUMINATOR_OFF_G109: str = "Off"
ALLOWED_AF_ILLUMINATOR_MODES_G109: Tuple[str, ...] = (
    AF_ILLUMINATOR_AUTO_G109,
    AF_ILLUMINATOR_OFF_G109,
)
AF_ILLUMINATOR_FACTORY_DEFAULT_G109: str = AF_ILLUMINATOR_AUTO_G109

HDMI_FEED_INFO_ON_G109: str = "Info On"
HDMI_FEED_INFO_OFF_G109: str = "Info Off"
HDMI_FEED_RAW_G109: str = "HDMI RAW"
ALLOWED_HDMI_FEED_MODES_G109: Tuple[str, ...] = (
    HDMI_FEED_INFO_ON_G109,
    HDMI_FEED_INFO_OFF_G109,
    HDMI_FEED_RAW_G109,
)

# ---------------------------------------------------------------------------
# Gate G110 Constants: [Area/Date/Time Setting], [Video Light Mode], [HDMI Resolution]
# ---------------------------------------------------------------------------

AREA_DATE_TIME_MENU_PATH_G110: str = (
    "MENU -> Setup -> [Area/Date] -> [Area/Date/Time Setting]"
)
VIDEO_LIGHT_MODE_MENU_PATH_G110: str = (
    "MENU -> Setup -> [Setup Option] -> [Video Light Mode]"
)
HDMI_RESOLUTION_MENU_PATH_G110: str = (
    "MENU -> Setup -> [External Output] -> [HDMI Resolution]"
)
AIRPLANE_MODE_MENU_PATH_G110: str = (
    "MENU -> Network -> [Network Option] -> [Airplane Mode]"
)

CANONICAL_AREA_DATETIME_LABEL_G110: str = "Area/Date/Time Setting"
LEGACY_SPOOF_DATETIME_SETUP_LABEL_G110: str = "Date/Time Setup"

AREA_DATETIME_EXACT_4_SUBITEMS_G110: Tuple[str, ...] = (
    "Area Setting",
    "Daylight Savings",
    "Date/Time",
    "Date Format",
)
AREA_SETTING_UNCONFIGURED_DEFAULT_G110: str = "—"

DAYLIGHT_SAVINGS_OFF_G110: str = "Off"
DAYLIGHT_SAVINGS_ON_G110: str = "On"
ALLOWED_DAYLIGHT_SAVINGS_STATES_G110: Tuple[str, ...] = (
    DAYLIGHT_SAVINGS_OFF_G110,
    DAYLIGHT_SAVINGS_ON_G110,
)
DAYLIGHT_SAVINGS_FACTORY_DEFAULT_G110: str = DAYLIGHT_SAVINGS_OFF_G110

DATE_FORMAT_YMD_G110: str = "YYYY-MM-DD"
DATE_FORMAT_MDY_G110: str = "MM-DD-YYYY"
DATE_FORMAT_DMY_G110: str = "DD-MM-YYYY"
ALLOWED_DATE_FORMATS_G110: Tuple[str, ...] = (
    DATE_FORMAT_YMD_G110,
    DATE_FORMAT_MDY_G110,
    DATE_FORMAT_DMY_G110,
)
DATE_FORMAT_FACTORY_DEFAULT_G110: str = DATE_FORMAT_YMD_G110

AIRPLANE_MODE_ON_G110: str = "On"
AIRPLANE_MODE_OFF_G110: str = "Off"
ALLOWED_AIRPLANE_MODES_G110: Tuple[str, ...] = (
    AIRPLANE_MODE_ON_G110,
    AIRPLANE_MODE_OFF_G110,
)

VIDEO_LIGHT_POWER_LINK_G110: str = "Power Link"
VIDEO_LIGHT_REC_LINK_G110: str = "REC Link"
VIDEO_LIGHT_REC_LINK_STBY_G110: str = "REC Link & STBY"
VIDEO_LIGHT_AUTO_G110: str = "Auto"
ALLOWED_VIDEO_LIGHT_MODES_G110: Tuple[str, ...] = (
    VIDEO_LIGHT_POWER_LINK_G110,
    VIDEO_LIGHT_REC_LINK_G110,
    VIDEO_LIGHT_REC_LINK_STBY_G110,
    VIDEO_LIGHT_AUTO_G110,
)
VIDEO_LIGHT_MODE_FACTORY_DEFAULT_G110: str = VIDEO_LIGHT_POWER_LINK_G110

MISHOE_5V_MAX_BUDGET_MA_G110: int = 900

HDMI_RES_AUTO_G110: str = "Auto"
HDMI_RES_2160P_G110: str = "2160p"
HDMI_RES_1080P_G110: str = "1080p"
HDMI_RES_1080I_G110: str = "1080i"
ALLOWED_HDMI_RESOLUTIONS_G110: Tuple[str, ...] = (
    HDMI_RES_AUTO_G110,
    HDMI_RES_2160P_G110,
    HDMI_RES_1080P_G110,
    HDMI_RES_1080I_G110,
)
HDMI_RES_FACTORY_DEFAULT_G110: str = HDMI_RES_AUTO_G110

LOG_SHOOTING_OFF_G110: str = "Off"
LOG_SHOOTING_CINE_EI_G110: str = "Cine EI"
LOG_SHOOTING_CINE_EI_QUICK_G110: str = "Cine EI Quick"
LOG_SHOOTING_FLEXIBLE_ISO_G110: str = "Flexible ISO"
ALLOWED_LOG_SHOOTING_MODES_G110: Tuple[str, ...] = (
    LOG_SHOOTING_OFF_G110,
    LOG_SHOOTING_CINE_EI_G110,
    LOG_SHOOTING_CINE_EI_QUICK_G110,
    LOG_SHOOTING_FLEXIBLE_ISO_G110,
)
ACTIVE_LOG_SHOOTING_MODES_G110: Tuple[str, ...] = (
    LOG_SHOOTING_CINE_EI_G110,
    LOG_SHOOTING_CINE_EI_QUICK_G110,
    LOG_SHOOTING_FLEXIBLE_ISO_G110,
)

REC_MEDIA_DUR_HDMI_ON_G110: str = "On"
REC_MEDIA_DUR_HDMI_OFF_G110: str = "Off(HDMI Only)"
ALLOWED_REC_MEDIA_DUR_HDMI_STATES_G110: Tuple[str, ...] = (
    REC_MEDIA_DUR_HDMI_ON_G110,
    REC_MEDIA_DUR_HDMI_OFF_G110,
)

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, <0.10s, Clean-Room Fallback)
# ---------------------------------------------------------------------------

PINNED_PHASE271_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_bin": (
        "FX3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"Focus",
            b"Magnifier",
            b"Magnif",
            b"Assist",
            b"Peaking",
            b"AF",
            b"MF",
            b"Mid",
            b"White",
            b"Area",
            b"Date",
            b"Time",
            b"Light",
            b"HDMI",
            b"Resolution",
            b"1080i",
            b"Log",
            b"Reset",
            b"Initialize",
            b"Still",
            b"Movie",
            b"Auto",
            b"Custom",
        ),
        "FX3_CPAPP_FOCUS_MAG_PEAKING_AREA_DATE_LIGHT_HDMI_RES_STRINGS",
    ),
    "fx3_libgpe_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgpe.so",
        106_480,
        "363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464",
        (
            b"\x7fELF",
            b"gpe_blog_error",
            b"_ZNK5mpgpe5Gperm4InitEv",
        ),
        "FX3_LIBGPE_FOCUS_MAG_PEAKING_SETUP_MENU_ELF",
    ),
    "fx3_libsaveloadsettings_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (
            b"\x7fELF",
            b"infra_saveLoadSettings_init",
            b"_ZN16SaveLoadSettings13requestToReadEN18SaveLoadSettingsIf11RequestTypeE",
            b"_ZN16SaveLoadSettings14requestToCheckEN18SaveLoadSettingsIf11RequestType",
        ),
        "FX3_LIBSAVELOADSETTINGS_AREA_DATE_VIDEOLIGHT_HDMIRES_PERSISTENCE_ELF",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"TC", b"/setting"),
        "FX3_BK4_FOCUS_AREA_DATE_HDMI_BACKUP_SEED",
    ),
    "fx6_libinfradial_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraDial.so",
        31_232,
        "b2034d6c85372027444e783d5d2ed913bb5a8cd2fe4051b10cf63caae875db33",
        (
            b"\x7fELF",
            b"_ZN9InfraDial4InitEv",
            b"_ZN9InfraDial10set4KeyInhEb",
            b"_ZN10InfraInput12SetKeyInhExtEibi",
        ),
        "FX6_LIBINFRADIAL_CUSTOM_BTN5_WHEEL_RIGHT_PARITY_ELF",
    ),
    "fx6_bk4_bin": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"WB", b"TC", b"/setting"),
        "FX6_BK4_CINEMA_LINE_DATETIME_HDMI_PARITY_SEED",
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase271DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    elapsed_seconds: float
    within_budget_100ms: bool
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
class FocusMagPeakingAfIlluminatorGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    reset_action: str
    shoot_mode: str
    focus_mode: str
    hdmi_feed_mode: str
    focus_assistant_menu_path: str
    peaking_display_menu_path: str
    af_illuminator_menu_path: str
    hdmi_info_display_menu_path: str
    auto_mag_menu_label: str
    legacy_mf_assist_spoof_events: int
    pre_reset_auto_mag_in_mf: str
    effective_post_reset_auto_mag_in_mf: str
    focus_magnifier_custom_button: str
    pre_reset_focus_mag_time: str
    effective_post_reset_focus_mag_time: str
    pre_reset_still_initial_focus_mag: str
    effective_post_reset_still_initial_focus_mag: str
    pre_reset_movie_initial_focus_mag: str
    effective_post_reset_movie_initial_focus_mag: str
    still_movie_initial_mag_registers_independent: bool
    pre_reset_af_in_focus_mag: str
    effective_post_reset_af_in_focus_mag: str
    af_in_focus_mag_still_only_armed: bool
    movie_af_in_focus_mag_events: int
    pre_reset_peaking_display: str
    effective_post_reset_peaking_display: str
    peaking_select_button: str
    pre_reset_peaking_level: str
    effective_post_reset_peaking_level: str
    pre_reset_peaking_color: str
    effective_post_reset_peaking_color: str
    hdmi_clean_feed_active: bool
    hdmi_clean_feed_focus_mag_or_peaking_leak_pixels: int
    pre_reset_af_illuminator: str
    effective_post_reset_af_illuminator: str
    af_illuminator_still_only_armed: bool
    movie_sq_af_illuminator_fire_events: int
    focus_assistant_peaking_reset_contract_verified: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G109FocusMagPeakingAfIlluminatorGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    focus_mag_peaking_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AreaDateTimeVideoLightHdmiResGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    reset_action: str
    rtc_backup_battery_lost: bool
    area_date_time_menu_path: str
    video_light_mode_menu_path: str
    hdmi_resolution_menu_path: str
    airplane_mode_menu_path: str
    area_datetime_menu_label: str
    legacy_datetime_setup_spoof_events: int
    area_datetime_subitems: Tuple[str, ...]
    pre_reset_area_setting: str
    effective_post_reset_area_setting: str
    pre_reset_daylight_savings: str
    effective_post_reset_daylight_savings: str
    pre_reset_datetime_value: str
    effective_post_reset_datetime_value: str
    pre_reset_date_format: str
    effective_post_reset_date_format: str
    datetime_reprompt_required: bool
    airplane_mode: str
    zero_rf_bench_enforced: bool
    requested_auto_time_correction: str
    effective_auto_time_correction: str
    requested_auto_area_adjustment: str
    effective_auto_area_adjustment: str
    passive_tx_bytes_emitted: int
    unsolicited_rtc_timezone_jump_events: int
    pre_reset_video_light_mode: str
    effective_post_reset_video_light_mode: str
    mishoe_5v_draw_ma: int
    mishoe_5v_budget_ma: int
    mishoe_5v_overcurrent_events: int
    log_shooting_mode: str
    internal_recording_active: bool
    rec_media_dur_hdmi: str
    pre_reset_hdmi_resolution: str
    effective_post_reset_hdmi_resolution: str
    effective_hdmi_output_resolution: str
    log_internal_rec_1080p_downshift_active: bool
    hdmi_res_log_internal_rec_2160p_bypass_events: int
    setup_items_survive_camera_settings_reset: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G110AreaDateTimeVideoLightHdmiResGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    area_datetime_videolight_hdmires_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master110GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_107_gates_verified: bool
    all_110_gates_verified: bool
    g13_to_g110_all_passed: bool
    g109_to_g110_all_passed: bool
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
    master_108_report: Dict[str, Any]
    g109_result: Dict[str, Any]
    g110_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers & Normalization
# ---------------------------------------------------------------------------

_TRUTHY_CLEAN_ROOM_TOKENS: Tuple[str, ...] = ("1", "true", "TRUE", "yes", "YES")


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE271):
        if os.environ.get(env_key, "").strip() in _TRUTHY_CLEAN_ROOM_TOKENS:
            return True
    return False


def _default_donor_budget_seconds_phase271() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return DONOR_CHECK_CI_MAX_SECONDS_PHASE271
    return DONOR_CHECK_MAX_SECONDS_PHASE271


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


def _norm_reset_action_phase271(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE271
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE
    return None


def _norm_on_off_phase271(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "ON":
        return ON_G109
    if u == "OFF":
        return OFF_G109
    return None


def _norm_shoot_mode_g109(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    if u == "STILL":
        return SHOOT_MODE_STILL_G109
    if u == "MOVIE":
        return SHOOT_MODE_MOVIE_G109
    if u in ("S&Q", "SQ"):
        return SHOOT_MODE_SQ_G109
    return None


def _norm_focus_mode_g109(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]").replace("_", "-")).upper()
    mapping = {
        "MF": FOCUS_MODE_MF_G109,
        "DMF": FOCUS_MODE_DMF_G109,
        "AF-S": FOCUS_MODE_AF_S_G109,
        "AFS": FOCUS_MODE_AF_S_G109,
        "AF-C": FOCUS_MODE_AF_C_G109,
        "AFC": FOCUS_MODE_AF_C_G109,
    }
    return mapping.get(u)


def _norm_focus_mag_time_g109(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    mapping = {
        "2 SEC": FOCUS_MAG_TIME_2_SEC_G109,
        "2SEC": FOCUS_MAG_TIME_2_SEC_G109,
        "5 SEC": FOCUS_MAG_TIME_5_SEC_G109,
        "5SEC": FOCUS_MAG_TIME_5_SEC_G109,
        "NO LIMIT": FOCUS_MAG_TIME_NO_LIMIT_G109,
        "NOLIMIT": FOCUS_MAG_TIME_NO_LIMIT_G109,
    }
    return mapping.get(u)


def _norm_initial_focus_mag_g109(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).lower()
    if u in ("x1.0", "1.0x", "1.0", "x1"):
        return INITIAL_FOCUS_MAG_X1_0_G109
    if u in ("x4.0", "4.0x", "4.0", "x4"):
        return INITIAL_FOCUS_MAG_X4_0_G109
    return None


def _norm_peaking_level_g109(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    mapping = {
        "HIGH": PEAKING_LEVEL_HIGH_G109,
        "MID": PEAKING_LEVEL_MID_G109,
        "LOW": PEAKING_LEVEL_LOW_G109,
    }
    return mapping.get(u)


def _norm_peaking_color_g109(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    mapping = {
        "RED": PEAKING_COLOR_RED_G109,
        "YELLOW": PEAKING_COLOR_YELLOW_G109,
        "BLUE": PEAKING_COLOR_BLUE_G109,
        "WHITE": PEAKING_COLOR_WHITE_G109,
    }
    return mapping.get(u)


def _norm_af_illuminator_g109(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "AUTO":
        return AF_ILLUMINATOR_AUTO_G109
    if u == "OFF":
        return AF_ILLUMINATOR_OFF_G109
    return None


def _norm_hdmi_feed_mode_g109(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    mapping = {
        "INFO ON": HDMI_FEED_INFO_ON_G109,
        "INFO DISPLAY ON": HDMI_FEED_INFO_ON_G109,
        "ON": HDMI_FEED_INFO_ON_G109,
        "INFO OFF": HDMI_FEED_INFO_OFF_G109,
        "INFO DISPLAY OFF": HDMI_FEED_INFO_OFF_G109,
        "OFF": HDMI_FEED_INFO_OFF_G109,
        "HDMI RAW": HDMI_FEED_RAW_G109,
        "RAW": HDMI_FEED_RAW_G109,
    }
    return mapping.get(u)


def _norm_date_format_g110(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    mapping = {
        "YYYY-MM-DD": DATE_FORMAT_YMD_G110,
        "MM-DD-YYYY": DATE_FORMAT_MDY_G110,
        "DD-MM-YYYY": DATE_FORMAT_DMY_G110,
    }
    return mapping.get(u)


def _norm_video_light_mode_g110(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    mapping = {
        "POWER LINK": VIDEO_LIGHT_POWER_LINK_G110,
        "REC LINK": VIDEO_LIGHT_REC_LINK_G110,
        "REC LINK & STBY": VIDEO_LIGHT_REC_LINK_STBY_G110,
        "REC LINK&STBY": VIDEO_LIGHT_REC_LINK_STBY_G110,
        "AUTO": VIDEO_LIGHT_AUTO_G110,
    }
    return mapping.get(u)


def _norm_hdmi_resolution_g110(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    mapping = {
        "AUTO": HDMI_RES_AUTO_G110,
        "2160P": HDMI_RES_2160P_G110,
        "1080P": HDMI_RES_1080P_G110,
        "1080I": HDMI_RES_1080I_G110,
    }
    return mapping.get(u)


def _norm_log_shooting_mode_g110(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    mapping = {
        "OFF": LOG_SHOOTING_OFF_G110,
        "CINE EI": LOG_SHOOTING_CINE_EI_G110,
        "CINE EI QUICK": LOG_SHOOTING_CINE_EI_QUICK_G110,
        "FLEXIBLE ISO": LOG_SHOOTING_FLEXIBLE_ISO_G110,
    }
    return mapping.get(u)


def _norm_rec_media_dur_hdmi_g110(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]").replace("_", "")).upper()
    if u == "ON":
        return REC_MEDIA_DUR_HDMI_ON_G110
    if u in ("OFF(HDMIONLY)", "OFF"):
        return REC_MEDIA_DUR_HDMI_OFF_G110
    return None


# ---------------------------------------------------------------------------
# 1. Bounded `< 0.10s` O_RDONLY Donor Contract Audit (`Phase 271`)
# ---------------------------------------------------------------------------


def audit_phase271_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: Optional[float] = None,
) -> Phase271DonorAuditResult:
    """Inspect local FX3 Ver. 7.02 / FX6 Ver. 6.01 donor artifacts strictly
    `os.O_RDONLY` within `<0.10s` (`0.50s` under `GITHUB_ACTIONS=true`),
    verifying bounded Wave-45 symbols across `cpapp-b.bin`, `libgpe.so`,
    `libSaveLoadSettings.so`, `FX3-CX95900_ALLLANG-Backup.bin`,
    `libInfraDial.so`, and `CX95898_NTSC.bin` with deterministic
    `FX3_FX6_FORCE_CLEAN_ROOM=1` / `FX3_CLEAN_ROOM_TEST=1` parity.
    """
    t0 = time.perf_counter()
    budget = (
        _default_donor_budget_seconds_phase271()
        if max_budget_seconds is None
        else float(max_budget_seconds)
    )
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE271_DONOR_SPECS.items():
            fp = candidate_root / rel_path
            if fp.is_file():
                resolved[key] = fp
            else:
                all_present = False
                break

    if clean_forced or not all_present:
        elapsed = time.perf_counter() - t0
        within_budget = elapsed < budget
        synthetic_markers = tuple(
            spec[5] for spec in PINNED_PHASE271_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE271_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE271_DONOR_SPECS.items()}
        return Phase271DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE271_DONOR_INTEGRITY
            ),
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_CLEAN_ROOM",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_100ms=within_budget,
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
                f"Clean-room donor check exceeded budget ({elapsed:.4f}s >= {budget:.4f}s).",
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
    ) in PINNED_PHASE271_DONOR_SPECS.items():
        fp = resolved[key]
        try:
            actual_size, actual_sha, blob = _read_cached_donor_o_rdonly(fp)
            files_inspected += 1
        except OSError as exc:
            missing.append(marker_label)
            errors.append(f"O_RDONLY read failed for {key}: {exc}")
            continue

        sizes[key] = actual_size
        shas[key] = actual_sha
        size_ok = actual_size == exp_size
        sha_ok = actual_sha == exp_sha
        markers_ok = all(m in blob for m in marker_tuple)

        if not size_ok:
            errors.append(
                f"Donor size mismatch for {key}: got {actual_size}, expected {exp_size}."
            )
        if not sha_ok:
            errors.append(
                f"Donor SHA-256 mismatch for {key}: got {actual_sha}, expected {exp_sha}."
            )
        if not markers_ok:
            errors.append(f"Missing required Wave-45 byte markers in {key}.")

        if size_ok and sha_ok and markers_ok:
            checked.append(marker_label)
            passed_keys.add(key)
        else:
            missing.append(marker_label)

    elapsed = time.perf_counter() - t0
    within_budget = elapsed < budget
    if not within_budget:
        errors.append(
            f"Local O_RDONLY donor audit exceeded budget ({elapsed:.4f}s >= {budget:.4f}s)."
        )

    fx3_keys = {k for k, v in PINNED_PHASE271_DONOR_SPECS.items() if v[0] == "FX3"}
    fx6_keys = {k for k, v in PINNED_PHASE271_DONOR_SPECS.items() if v[0] == "FX6"}
    fx3_ok = fx3_keys.issubset(passed_keys)
    fx6_ok = fx6_keys.issubset(passed_keys)
    valid = fx3_ok and fx6_ok and (not missing) and within_budget and (not errors)

    return Phase271DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE
        if valid
        else STATUS_BLOCKED_PHASE271_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_100ms=within_budget,
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
# 2. Gate G109: [Focus Assistant], [Peaking Display] & Still-Only [AF Illuminator]
# ---------------------------------------------------------------------------


def compute_focus_mag_peaking_af_illuminator_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate 144 combinations across shoot modes, HDMI clean-feed
    states, Still/Movie [Initial Focus Mag.] independence, [Peaking Display], and
    [AF Illuminator] Still-only confinement.
    """
    states_checked = 0
    hdmi_clean_feed_leaks = 0
    movie_sq_af_illuminator_fires = 0
    still_movie_initial_mag_couplings = 0

    for shoot_mode in ALLOWED_SHOOT_MODES_G109:
        for hdmi_mode in ALLOWED_HDMI_FEED_MODES_G109:
            for still_mag in ALLOWED_INITIAL_FOCUS_MAGS_G109:
                for movie_mag in ALLOWED_INITIAL_FOCUS_MAGS_G109:
                    for peaking in ALLOWED_ON_OFF_STATES_G109:
                        for af_illum in ALLOWED_AF_ILLUMINATOR_MODES_G109:
                            resolved = resolve_fx3_focus_mag_peaking_and_af_illuminator_state(
                                shoot_mode=shoot_mode,
                                hdmi_feed_mode=hdmi_mode,
                                pre_reset_still_initial_focus_mag=still_mag,
                                pre_reset_movie_initial_focus_mag=movie_mag,
                                pre_reset_peaking_display=peaking,
                                pre_reset_af_illuminator=af_illum,
                            )
                            states_checked += 1
                            if resolved["hdmi_clean_feed_active"] and (
                                resolved["hdmi_clean_feed_focus_mag_leak"]
                                or resolved["hdmi_clean_feed_peaking_leak"]
                            ):
                                hdmi_clean_feed_leaks += 1
                            if (
                                shoot_mode != SHOOT_MODE_STILL_G109
                                and resolved["af_illuminator_still_only_armed"]
                            ):
                                movie_sq_af_illuminator_fires += 1
                            if (
                                resolved["effective_post_reset_still_initial_focus_mag"]
                                != still_mag
                                or resolved["effective_post_reset_movie_initial_focus_mag"]
                                != movie_mag
                            ):
                                still_movie_initial_mag_couplings += 1

    return {
        "states_checked": states_checked,
        "hdmi_clean_feed_leaks": hdmi_clean_feed_leaks,
        "movie_sq_af_illuminator_fires": movie_sq_af_illuminator_fires,
        "still_movie_initial_mag_couplings": still_movie_initial_mag_couplings,
        "all_invariants_hold": (
            states_checked == 144
            and hdmi_clean_feed_leaks == 0
            and movie_sq_af_illuminator_fires == 0
            and still_movie_initial_mag_couplings == 0
        ),
    }


def resolve_fx3_focus_mag_peaking_and_af_illuminator_state(
    *,
    shoot_mode: str = SHOOT_MODE_MOVIE_G109,
    focus_mode: str = FOCUS_MODE_MF_G109,
    hdmi_feed_mode: str = HDMI_FEED_INFO_OFF_G109,
    reset_action: str = RESET_ACTION_NONE,
    pre_reset_auto_mag_in_mf: str = AUTO_MAG_IN_MF_FACTORY_DEFAULT_G109,
    pre_reset_focus_mag_time: str = FOCUS_MAG_TIME_FACTORY_DEFAULT_G109,
    pre_reset_still_initial_focus_mag: str = INITIAL_FOCUS_MAG_STILL_FACTORY_DEFAULT_G109,
    pre_reset_movie_initial_focus_mag: str = INITIAL_FOCUS_MAG_MOVIE_FACTORY_DEFAULT_G109,
    pre_reset_af_in_focus_mag: str = AF_IN_FOCUS_MAG_FACTORY_DEFAULT_G109,
    pre_reset_peaking_display: str = PEAKING_DISPLAY_FACTORY_DEFAULT_G109,
    pre_reset_peaking_level: str = PEAKING_LEVEL_FACTORY_DEFAULT_G109,
    pre_reset_peaking_color: str = PEAKING_COLOR_FACTORY_DEFAULT_G109,
    pre_reset_af_illuminator: str = AF_ILLUMINATOR_FACTORY_DEFAULT_G109,
    focus_magnifier_custom_button: str = FOCUS_MAG_CUSTOM_BUTTON_DEFAULT_G109,
) -> Dict[str, Any]:
    s_mode = _norm_shoot_mode_g109(shoot_mode) or SHOOT_MODE_MOVIE_G109
    f_mode = _norm_focus_mode_g109(focus_mode) or FOCUS_MODE_MF_G109
    h_mode = _norm_hdmi_feed_mode_g109(hdmi_feed_mode) or HDMI_FEED_INFO_OFF_G109
    r_act = _norm_reset_action_phase271(reset_action) or RESET_ACTION_NONE

    auto_mag = _norm_on_off_phase271(pre_reset_auto_mag_in_mf) or AUTO_MAG_IN_MF_FACTORY_DEFAULT_G109
    mag_time = _norm_focus_mag_time_g109(pre_reset_focus_mag_time) or FOCUS_MAG_TIME_FACTORY_DEFAULT_G109
    still_mag = _norm_initial_focus_mag_g109(pre_reset_still_initial_focus_mag) or INITIAL_FOCUS_MAG_STILL_FACTORY_DEFAULT_G109
    movie_mag = _norm_initial_focus_mag_g109(pre_reset_movie_initial_focus_mag) or INITIAL_FOCUS_MAG_MOVIE_FACTORY_DEFAULT_G109
    af_in_mag = _norm_on_off_phase271(pre_reset_af_in_focus_mag) or AF_IN_FOCUS_MAG_FACTORY_DEFAULT_G109
    peaking_disp = _norm_on_off_phase271(pre_reset_peaking_display) or PEAKING_DISPLAY_FACTORY_DEFAULT_G109
    peaking_lvl = _norm_peaking_level_g109(pre_reset_peaking_level) or PEAKING_LEVEL_FACTORY_DEFAULT_G109
    peaking_clr = _norm_peaking_color_g109(pre_reset_peaking_color) or PEAKING_COLOR_FACTORY_DEFAULT_G109
    af_illum = _norm_af_illuminator_g109(pre_reset_af_illuminator) or AF_ILLUMINATOR_FACTORY_DEFAULT_G109

    # Shooting/Focus parameters reset on BOTH [Camera Settings Reset] and [Initialize],
    # while surviving [Reset Network Set.] and NONE.
    resets_shooting = r_act in (
        RESET_ACTION_CAMERA_SETTINGS_RESET,
        RESET_ACTION_INITIALIZE,
    )
    eff_auto_mag = AUTO_MAG_IN_MF_FACTORY_DEFAULT_G109 if resets_shooting else auto_mag
    eff_mag_time = FOCUS_MAG_TIME_FACTORY_DEFAULT_G109 if resets_shooting else mag_time
    eff_still_mag = INITIAL_FOCUS_MAG_STILL_FACTORY_DEFAULT_G109 if resets_shooting else still_mag
    eff_movie_mag = INITIAL_FOCUS_MAG_MOVIE_FACTORY_DEFAULT_G109 if resets_shooting else movie_mag
    eff_af_in_mag = AF_IN_FOCUS_MAG_FACTORY_DEFAULT_G109 if resets_shooting else af_in_mag
    eff_peaking_disp = PEAKING_DISPLAY_FACTORY_DEFAULT_G109 if resets_shooting else peaking_disp
    eff_peaking_lvl = PEAKING_LEVEL_FACTORY_DEFAULT_G109 if resets_shooting else peaking_lvl
    eff_peaking_clr = PEAKING_COLOR_FACTORY_DEFAULT_G109 if resets_shooting else peaking_clr
    eff_af_illum = AF_ILLUMINATOR_FACTORY_DEFAULT_G109 if resets_shooting else af_illum

    # [Custom Key/Dial Set.] assignment survives [Camera Settings Reset] and [Reset Network Set.],
    # resetting only via [Initialize].
    eff_custom_btn = (
        FOCUS_MAG_CUSTOM_BUTTON_DEFAULT_G109
        if r_act == RESET_ACTION_INITIALIZE
        else focus_magnifier_custom_button
    )

    hdmi_clean_feed_active = h_mode in (HDMI_FEED_INFO_OFF_G109, HDMI_FEED_RAW_G109)
    af_in_focus_mag_still_only_armed = (
        s_mode == SHOOT_MODE_STILL_G109 and eff_af_in_mag == ON_G109
    )
    af_illuminator_still_only_armed = (
        s_mode == SHOOT_MODE_STILL_G109 and eff_af_illum == AF_ILLUMINATOR_AUTO_G109
    )

    return {
        "shoot_mode": s_mode,
        "focus_mode": f_mode,
        "hdmi_feed_mode": h_mode,
        "reset_action": r_act,
        "effective_post_reset_auto_mag_in_mf": eff_auto_mag,
        "effective_post_reset_focus_mag_time": eff_mag_time,
        "effective_post_reset_still_initial_focus_mag": eff_still_mag,
        "effective_post_reset_movie_initial_focus_mag": eff_movie_mag,
        "effective_post_reset_af_in_focus_mag": eff_af_in_mag,
        "effective_post_reset_peaking_display": eff_peaking_disp,
        "effective_post_reset_peaking_level": eff_peaking_lvl,
        "effective_post_reset_peaking_color": eff_peaking_clr,
        "effective_post_reset_af_illuminator": eff_af_illum,
        "effective_post_reset_focus_mag_custom_button": eff_custom_btn,
        "hdmi_clean_feed_active": hdmi_clean_feed_active,
        "hdmi_clean_feed_focus_mag_leak": False,
        "hdmi_clean_feed_peaking_leak": False,
        "af_in_focus_mag_still_only_armed": af_in_focus_mag_still_only_armed,
        "af_illuminator_still_only_armed": af_illuminator_still_only_armed,
    }


def verify_focus_mag_peaking_af_illuminator_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE271,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE271,
    reset_action: str = RESET_ACTION_NONE,
    shoot_mode: str = SHOOT_MODE_MOVIE_G109,
    focus_mode: str = FOCUS_MODE_MF_G109,
    hdmi_feed_mode: str = HDMI_FEED_INFO_OFF_G109,
    claimed_auto_mag_menu_label: str = CANONICAL_AUTO_MAG_IN_MF_LABEL_G109,
    claimed_legacy_mf_assist_spoof_events: int = 0,
    pre_reset_auto_mag_in_mf: str = AUTO_MAG_IN_MF_FACTORY_DEFAULT_G109,
    claimed_post_reset_auto_mag_in_mf: Optional[str] = None,
    focus_magnifier_custom_button: str = FOCUS_MAG_CUSTOM_BUTTON_DEFAULT_G109,
    pre_reset_focus_mag_time: str = FOCUS_MAG_TIME_FACTORY_DEFAULT_G109,
    claimed_post_reset_focus_mag_time: Optional[str] = None,
    pre_reset_still_initial_focus_mag: str = INITIAL_FOCUS_MAG_STILL_FACTORY_DEFAULT_G109,
    claimed_post_reset_still_initial_focus_mag: Optional[str] = None,
    pre_reset_movie_initial_focus_mag: str = INITIAL_FOCUS_MAG_MOVIE_FACTORY_DEFAULT_G109,
    claimed_post_reset_movie_initial_focus_mag: Optional[str] = None,
    pre_reset_af_in_focus_mag: str = AF_IN_FOCUS_MAG_FACTORY_DEFAULT_G109,
    claimed_post_reset_af_in_focus_mag: Optional[str] = None,
    claimed_movie_af_in_focus_mag_events: int = 0,
    pre_reset_peaking_display: str = PEAKING_DISPLAY_FACTORY_DEFAULT_G109,
    claimed_post_reset_peaking_display: Optional[str] = None,
    peaking_select_button: str = PEAKING_SELECT_DEFAULT_BUTTON_G109,
    pre_reset_peaking_level: str = PEAKING_LEVEL_FACTORY_DEFAULT_G109,
    claimed_post_reset_peaking_level: Optional[str] = None,
    pre_reset_peaking_color: str = PEAKING_COLOR_FACTORY_DEFAULT_G109,
    claimed_post_reset_peaking_color: Optional[str] = None,
    claimed_external_hdmi_focus_mag_or_peaking_applied: bool = False,
    claimed_hdmi_clean_feed_focus_mag_or_peaking_leak_pixels: int = 0,
    pre_reset_af_illuminator: str = AF_ILLUMINATOR_FACTORY_DEFAULT_G109,
    claimed_post_reset_af_illuminator: Optional[str] = None,
    claimed_movie_sq_af_illuminator_fire_events: int = 0,
) -> FocusMagPeakingAfIlluminatorGuardResult:
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME
        or isinstance(body_model_id, bool)
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE271
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G109_TELEMETRY_INVALID)
        errors.append(
            "Gate G109 requires ILME-FX3 (0x91030080, Help Guide ilc/2210, Ver. 7.02)."
        )

    norm_reset = _norm_reset_action_phase271(reset_action)
    norm_shoot = _norm_shoot_mode_g109(shoot_mode)
    norm_focus = _norm_focus_mode_g109(focus_mode)
    norm_hdmi = _norm_hdmi_feed_mode_g109(hdmi_feed_mode)
    norm_auto_mag = _norm_on_off_phase271(pre_reset_auto_mag_in_mf)
    norm_mag_time = _norm_focus_mag_time_g109(pre_reset_focus_mag_time)
    norm_still_mag = _norm_initial_focus_mag_g109(pre_reset_still_initial_focus_mag)
    norm_movie_mag = _norm_initial_focus_mag_g109(pre_reset_movie_initial_focus_mag)
    norm_af_in_mag = _norm_on_off_phase271(pre_reset_af_in_focus_mag)
    norm_peaking_disp = _norm_on_off_phase271(pre_reset_peaking_display)
    norm_peaking_lvl = _norm_peaking_level_g109(pre_reset_peaking_level)
    norm_peaking_clr = _norm_peaking_color_g109(pre_reset_peaking_color)
    norm_af_illum = _norm_af_illuminator_g109(pre_reset_af_illuminator)

    if any(
        x is None
        for x in (
            norm_reset,
            norm_shoot,
            norm_focus,
            norm_hdmi,
            norm_auto_mag,
            norm_mag_time,
            norm_still_mag,
            norm_movie_mag,
            norm_af_in_mag,
            norm_peaking_disp,
            norm_peaking_lvl,
            norm_peaking_clr,
            norm_af_illum,
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G109_TELEMETRY_INVALID)
        errors.append("Invalid or unrecognized G109 Focus/Peaking/HDMI/Reset enum value.")

    for int_val, name in (
        (claimed_legacy_mf_assist_spoof_events, "claimed_legacy_mf_assist_spoof_events"),
        (claimed_movie_af_in_focus_mag_events, "claimed_movie_af_in_focus_mag_events"),
        (
            claimed_hdmi_clean_feed_focus_mag_or_peaking_leak_pixels,
            "claimed_hdmi_clean_feed_focus_mag_or_peaking_leak_pixels",
        ),
        (
            claimed_movie_sq_af_illuminator_fire_events,
            "claimed_movie_sq_af_illuminator_fire_events",
        ),
    ):
        if isinstance(int_val, bool) or not isinstance(int_val, int) or int_val < 0:
            _add_code(codes, STATUS_BLOCKED_G109_TELEMETRY_INVALID)
            errors.append(f"{name} must be a non-negative integer.")

    if not isinstance(claimed_external_hdmi_focus_mag_or_peaking_applied, bool):
        _add_code(codes, STATUS_BLOCKED_G109_TELEMETRY_INVALID)
        errors.append("claimed_external_hdmi_focus_mag_or_peaking_applied must be a bool.")

    # Nomenclature spoof check: must be [Auto Magnifier in MF], never legacy "MF Assist"
    spoof_events = (
        claimed_legacy_mf_assist_spoof_events
        if isinstance(claimed_legacy_mf_assist_spoof_events, int)
        and not isinstance(claimed_legacy_mf_assist_spoof_events, bool)
        else 1
    )
    if (
        not isinstance(claimed_auto_mag_menu_label, str)
        or claimed_auto_mag_menu_label.strip().strip("[]")
        != CANONICAL_AUTO_MAG_IN_MF_LABEL_G109
    ):
        spoof_events = max(1, spoof_events)
    if spoof_events != 0:
        _add_code(codes, STATUS_BLOCKED_G109_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF_VIOLATION)
        errors.append(
            "ILME-FX3 Ver. 7.02 uses [Auto Magnifier in MF], rejecting legacy 'MF Assist' spoofing."
        )

    # Custom Button 5 & Control Wheel Right default assignment guard
    if (
        not isinstance(focus_magnifier_custom_button, str)
        or focus_magnifier_custom_button.strip() != FOCUS_MAG_CUSTOM_BUTTON_DEFAULT_G109
        or not isinstance(peaking_select_button, str)
        or peaking_select_button.strip() != PEAKING_SELECT_DEFAULT_BUTTON_G109
    ):
        _add_code(codes, STATUS_BLOCKED_G109_FOCUS_MAG_DEFAULTS_OR_CUSTOM_BTN5_VIOLATION)
        errors.append(
            "Default Focus Magnifier (Custom Button 5) and Peaking Display Select (Control Wheel Right) bindings must hold."
        )

    resolved = resolve_fx3_focus_mag_peaking_and_af_illuminator_state(
        shoot_mode=norm_shoot or SHOOT_MODE_MOVIE_G109,
        focus_mode=norm_focus or FOCUS_MODE_MF_G109,
        hdmi_feed_mode=norm_hdmi or HDMI_FEED_INFO_OFF_G109,
        reset_action=norm_reset or RESET_ACTION_NONE,
        pre_reset_auto_mag_in_mf=norm_auto_mag or AUTO_MAG_IN_MF_FACTORY_DEFAULT_G109,
        pre_reset_focus_mag_time=norm_mag_time or FOCUS_MAG_TIME_FACTORY_DEFAULT_G109,
        pre_reset_still_initial_focus_mag=norm_still_mag or INITIAL_FOCUS_MAG_STILL_FACTORY_DEFAULT_G109,
        pre_reset_movie_initial_focus_mag=norm_movie_mag or INITIAL_FOCUS_MAG_MOVIE_FACTORY_DEFAULT_G109,
        pre_reset_af_in_focus_mag=norm_af_in_mag or AF_IN_FOCUS_MAG_FACTORY_DEFAULT_G109,
        pre_reset_peaking_display=norm_peaking_disp or PEAKING_DISPLAY_FACTORY_DEFAULT_G109,
        pre_reset_peaking_level=norm_peaking_lvl or PEAKING_LEVEL_FACTORY_DEFAULT_G109,
        pre_reset_peaking_color=norm_peaking_clr or PEAKING_COLOR_FACTORY_DEFAULT_G109,
        pre_reset_af_illuminator=norm_af_illum or AF_ILLUMINATOR_FACTORY_DEFAULT_G109,
        focus_magnifier_custom_button=(
            focus_magnifier_custom_button
            if isinstance(focus_magnifier_custom_button, str)
            else FOCUS_MAG_CUSTOM_BUTTON_DEFAULT_G109
        ),
    )

    matrix = compute_focus_mag_peaking_af_illuminator_matrix()
    if not matrix["all_invariants_hold"]:
        _add_code(codes, STATUS_BLOCKED_G109_TELEMETRY_INVALID)
        errors.append("G109 Focus Magnifier / Peaking / AF Illuminator matrix failed.")

    # Clean-HDMI isolation guard
    leak_pixels = (
        claimed_hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        if isinstance(claimed_hdmi_clean_feed_focus_mag_or_peaking_leak_pixels, int)
        and not isinstance(
            claimed_hdmi_clean_feed_focus_mag_or_peaking_leak_pixels, bool
        )
        else 1
    )
    if (
        (resolved["hdmi_clean_feed_active"] and claimed_external_hdmi_focus_mag_or_peaking_applied)
        or (claimed_external_hdmi_focus_mag_or_peaking_applied)
        or (leak_pixels > 0)
    ):
        _add_code(codes, STATUS_BLOCKED_G109_HDMI_CLEAN_FEED_OVERLAY_LEAK_VIOLATION)
        errors.append(
            "Focus Magnifier and Peaking overlays are camera-LCD-only on clean HDMI / HDMI RAW feeds."
        )

    # Still-only [AF in Focus Mag.] & [AF Illuminator] confinement
    mv_af_mag_events = (
        claimed_movie_af_in_focus_mag_events
        if isinstance(claimed_movie_af_in_focus_mag_events, int)
        and not isinstance(claimed_movie_af_in_focus_mag_events, bool)
        else 1
    )
    mv_sq_illum_events = (
        claimed_movie_sq_af_illuminator_fire_events
        if isinstance(claimed_movie_sq_af_illuminator_fire_events, int)
        and not isinstance(claimed_movie_sq_af_illuminator_fire_events, bool)
        else 1
    )
    if mv_af_mag_events != 0 or mv_sq_illum_events != 0:
        _add_code(
            codes, STATUS_BLOCKED_G109_STILL_ONLY_AF_ILLUMINATOR_OR_AF_IN_MAG_VIOLATION
        )
        errors.append(
            "[AF in Focus Mag.] and [AF Illuminator] are strictly Still-only and must emit 0 Movie/S&Q events."
        )

    # Reset contract verification
    reset_pairs = (
        (
            claimed_post_reset_auto_mag_in_mf,
            resolved["effective_post_reset_auto_mag_in_mf"],
            _norm_on_off_phase271,
        ),
        (
            claimed_post_reset_focus_mag_time,
            resolved["effective_post_reset_focus_mag_time"],
            _norm_focus_mag_time_g109,
        ),
        (
            claimed_post_reset_still_initial_focus_mag,
            resolved["effective_post_reset_still_initial_focus_mag"],
            _norm_initial_focus_mag_g109,
        ),
        (
            claimed_post_reset_movie_initial_focus_mag,
            resolved["effective_post_reset_movie_initial_focus_mag"],
            _norm_initial_focus_mag_g109,
        ),
        (
            claimed_post_reset_af_in_focus_mag,
            resolved["effective_post_reset_af_in_focus_mag"],
            _norm_on_off_phase271,
        ),
        (
            claimed_post_reset_peaking_display,
            resolved["effective_post_reset_peaking_display"],
            _norm_on_off_phase271,
        ),
        (
            claimed_post_reset_peaking_level,
            resolved["effective_post_reset_peaking_level"],
            _norm_peaking_level_g109,
        ),
        (
            claimed_post_reset_peaking_color,
            resolved["effective_post_reset_peaking_color"],
            _norm_peaking_color_g109,
        ),
        (
            claimed_post_reset_af_illuminator,
            resolved["effective_post_reset_af_illuminator"],
            _norm_af_illuminator_g109,
        ),
    )
    reset_ok = True
    for claimed_raw, expected_val, norm_fn in reset_pairs:
        if claimed_raw is not None:
            norm_claimed = norm_fn(claimed_raw)
            if norm_claimed != expected_val:
                reset_ok = False
                break
    if not reset_ok:
        _add_code(codes, STATUS_BLOCKED_G109_RESET_BEHAVIOR_VIOLATION)
        errors.append(
            "Focus Assistant, Peaking, and AF Illuminator must reset under [Camera Settings Reset] and [Initialize], while surviving [Reset Network Set.]."
        )

    valid = not codes
    status = STATUS_VERIFIED_G109 if valid else codes[0]

    return FocusMagPeakingAfIlluminatorGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}"
        if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
        else "invalid",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        reset_action=resolved["reset_action"],
        shoot_mode=resolved["shoot_mode"],
        focus_mode=resolved["focus_mode"],
        hdmi_feed_mode=resolved["hdmi_feed_mode"],
        focus_assistant_menu_path=FOCUS_ASSISTANT_MENU_PATH_G109,
        peaking_display_menu_path=PEAKING_DISPLAY_MENU_PATH_G109,
        af_illuminator_menu_path=AF_ILLUMINATOR_MENU_PATH_G109,
        hdmi_info_display_menu_path=HDMI_INFO_DISPLAY_MENU_PATH_G109,
        auto_mag_menu_label=str(claimed_auto_mag_menu_label),
        legacy_mf_assist_spoof_events=spoof_events,
        pre_reset_auto_mag_in_mf=norm_auto_mag or str(pre_reset_auto_mag_in_mf),
        effective_post_reset_auto_mag_in_mf=resolved[
            "effective_post_reset_auto_mag_in_mf"
        ],
        focus_magnifier_custom_button=str(focus_magnifier_custom_button),
        pre_reset_focus_mag_time=norm_mag_time or str(pre_reset_focus_mag_time),
        effective_post_reset_focus_mag_time=resolved[
            "effective_post_reset_focus_mag_time"
        ],
        pre_reset_still_initial_focus_mag=norm_still_mag
        or str(pre_reset_still_initial_focus_mag),
        effective_post_reset_still_initial_focus_mag=resolved[
            "effective_post_reset_still_initial_focus_mag"
        ],
        pre_reset_movie_initial_focus_mag=norm_movie_mag
        or str(pre_reset_movie_initial_focus_mag),
        effective_post_reset_movie_initial_focus_mag=resolved[
            "effective_post_reset_movie_initial_focus_mag"
        ],
        still_movie_initial_mag_registers_independent=bool(
            matrix["still_movie_initial_mag_couplings"] == 0
        ),
        pre_reset_af_in_focus_mag=norm_af_in_mag or str(pre_reset_af_in_focus_mag),
        effective_post_reset_af_in_focus_mag=resolved[
            "effective_post_reset_af_in_focus_mag"
        ],
        af_in_focus_mag_still_only_armed=resolved["af_in_focus_mag_still_only_armed"],
        movie_af_in_focus_mag_events=mv_af_mag_events,
        pre_reset_peaking_display=norm_peaking_disp or str(pre_reset_peaking_display),
        effective_post_reset_peaking_display=resolved[
            "effective_post_reset_peaking_display"
        ],
        peaking_select_button=str(peaking_select_button),
        pre_reset_peaking_level=norm_peaking_lvl or str(pre_reset_peaking_level),
        effective_post_reset_peaking_level=resolved[
            "effective_post_reset_peaking_level"
        ],
        pre_reset_peaking_color=norm_peaking_clr or str(pre_reset_peaking_color),
        effective_post_reset_peaking_color=resolved[
            "effective_post_reset_peaking_color"
        ],
        hdmi_clean_feed_active=resolved["hdmi_clean_feed_active"],
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=leak_pixels,
        pre_reset_af_illuminator=norm_af_illum or str(pre_reset_af_illuminator),
        effective_post_reset_af_illuminator=resolved[
            "effective_post_reset_af_illuminator"
        ],
        af_illuminator_still_only_armed=resolved["af_illuminator_still_only_armed"],
        movie_sq_af_illuminator_fire_events=mv_sq_illum_events,
        focus_assistant_peaking_reset_contract_verified=reset_ok,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g109_focus_mag_peaking_af_illuminator_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    focus_mag_peaking_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase271DonorAuditResult] = None,
) -> Tuple[GateVerdict, G109FocusMagPeakingAfIlluminatorGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase271_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_focus_mag_peaking_af_illuminator_guard(
        **dict(focus_mag_peaking_kwargs or {})
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
        errors.append("Persistent eMMC write authorization requested in Gate G109.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G109 if valid else codes[0]

    res = G109FocusMagPeakingAfIlluminatorGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        focus_mag_peaking_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, auto_mag={guard.effective_post_reset_auto_mag_in_mf}"
        f"(btn={guard.focus_magnifier_custom_button},time={guard.effective_post_reset_focus_mag_time}), "
        f"init_mag=Still:{guard.effective_post_reset_still_initial_focus_mag}/"
        f"Movie:{guard.effective_post_reset_movie_initial_focus_mag}, "
        f"peaking={guard.effective_post_reset_peaking_display}({guard.effective_post_reset_peaking_level}/"
        f"{guard.effective_post_reset_peaking_color},hdmi_leak={guard.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels}), "
        f"af_illum={guard.effective_post_reset_af_illuminator}(mv_sq_fire={guard.movie_sq_af_illuminator_fire_events})"
    )
    verdict = GateVerdict(
        gate_id=G109_GATE_ID,
        gate_code=G109_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G110: [Area/Date/Time Setting], Zero-RF Sync, [Video Light Mode] & [HDMI Resolution]
# ---------------------------------------------------------------------------


def compute_area_datetime_videolight_hdmires_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate 256 combinations across [Video Light Mode],
    [HDMI Resolution], [Log Shooting], [Rec. Media dur HDMI Output], and
    [Airplane Mode] zero-RF posture.
    """
    states_checked = 0
    zero_rf_creators_app_leaks = 0
    log_internal_rec_2160p_bypasses = 0
    setup_reset_corruptions = 0

    for vlight in ALLOWED_VIDEO_LIGHT_MODES_G110:
        for hres in ALLOWED_HDMI_RESOLUTIONS_G110:
            for log_mode in ALLOWED_LOG_SHOOTING_MODES_G110:
                for rec_media in ALLOWED_REC_MEDIA_DUR_HDMI_STATES_G110:
                    for airplane in ALLOWED_AIRPLANE_MODES_G110:
                        resolved = resolve_fx3_area_datetime_videolight_and_hdmires_state(
                            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
                            pre_reset_area_setting="America/Los_Angeles",
                            pre_reset_daylight_savings=DAYLIGHT_SAVINGS_ON_G110,
                            pre_reset_datetime_value="2026-11-17 14:38:00",
                            pre_reset_date_format=DATE_FORMAT_YMD_G110,
                            airplane_mode=airplane,
                            requested_auto_time_correction="On",
                            requested_auto_area_adjustment="On",
                            pre_reset_video_light_mode=vlight,
                            pre_reset_hdmi_resolution=hres,
                            log_shooting_mode=log_mode,
                            internal_recording_active=(
                                rec_media == REC_MEDIA_DUR_HDMI_ON_G110
                            ),
                            rec_media_dur_hdmi=rec_media,
                        )
                        states_checked += 1
                        if airplane == AIRPLANE_MODE_ON_G110 and (
                            resolved["effective_auto_time_correction"] != "Off"
                            or resolved["effective_auto_area_adjustment"] != "Off"
                        ):
                            zero_rf_creators_app_leaks += 1
                        if (
                            log_mode in ACTIVE_LOG_SHOOTING_MODES_G110
                            and rec_media == REC_MEDIA_DUR_HDMI_ON_G110
                            and hres in (HDMI_RES_AUTO_G110, HDMI_RES_2160P_G110)
                            and resolved["effective_hdmi_output_resolution"]
                            != HDMI_RES_1080P_G110
                        ):
                            log_internal_rec_2160p_bypasses += 1
                        if (
                            resolved["effective_post_reset_video_light_mode"] != vlight
                            or resolved["effective_post_reset_hdmi_resolution"] != hres
                            or resolved["effective_post_reset_area_setting"]
                            != "America/Los_Angeles"
                        ):
                            setup_reset_corruptions += 1

    return {
        "states_checked": states_checked,
        "zero_rf_creators_app_leaks": zero_rf_creators_app_leaks,
        "log_internal_rec_2160p_bypasses": log_internal_rec_2160p_bypasses,
        "setup_reset_corruptions": setup_reset_corruptions,
        "all_invariants_hold": (
            states_checked == 256
            and zero_rf_creators_app_leaks == 0
            and log_internal_rec_2160p_bypasses == 0
            and setup_reset_corruptions == 0
        ),
    }


def resolve_fx3_area_datetime_videolight_and_hdmires_state(
    *,
    reset_action: str = RESET_ACTION_NONE,
    rtc_backup_battery_lost: bool = False,
    pre_reset_area_setting: str = AREA_SETTING_UNCONFIGURED_DEFAULT_G110,
    pre_reset_daylight_savings: str = DAYLIGHT_SAVINGS_FACTORY_DEFAULT_G110,
    pre_reset_datetime_value: str = "2026-11-17 14:38:00",
    pre_reset_date_format: str = DATE_FORMAT_FACTORY_DEFAULT_G110,
    airplane_mode: str = AIRPLANE_MODE_ON_G110,
    requested_auto_time_correction: str = "Off",
    requested_auto_area_adjustment: str = "Off",
    pre_reset_video_light_mode: str = VIDEO_LIGHT_MODE_FACTORY_DEFAULT_G110,
    pre_reset_hdmi_resolution: str = HDMI_RES_FACTORY_DEFAULT_G110,
    log_shooting_mode: str = LOG_SHOOTING_OFF_G110,
    internal_recording_active: bool = False,
    rec_media_dur_hdmi: str = REC_MEDIA_DUR_HDMI_ON_G110,
) -> Dict[str, Any]:
    r_act = _norm_reset_action_phase271(reset_action) or RESET_ACTION_NONE
    dst = _norm_on_off_phase271(pre_reset_daylight_savings) or DAYLIGHT_SAVINGS_FACTORY_DEFAULT_G110
    d_fmt = _norm_date_format_g110(pre_reset_date_format) or DATE_FORMAT_FACTORY_DEFAULT_G110
    ap_mode = _norm_on_off_phase271(airplane_mode) or AIRPLANE_MODE_ON_G110
    req_time_corr = _norm_on_off_phase271(requested_auto_time_correction) or "Off"
    req_area_adj = _norm_on_off_phase271(requested_auto_area_adjustment) or "Off"
    vlight = _norm_video_light_mode_g110(pre_reset_video_light_mode) or VIDEO_LIGHT_MODE_FACTORY_DEFAULT_G110
    hres = _norm_hdmi_resolution_g110(pre_reset_hdmi_resolution) or HDMI_RES_FACTORY_DEFAULT_G110
    log_m = _norm_log_shooting_mode_g110(log_shooting_mode) or LOG_SHOOTING_OFF_G110
    rec_hdmi = _norm_rec_media_dur_hdmi_g110(rec_media_dur_hdmi) or REC_MEDIA_DUR_HDMI_ON_G110

    # [Setup] items survive [Camera Settings Reset] and [Reset Network Set.].
    # [Area/Date/Time Setting] clears only on [Initialize] or RTC backup battery loss.
    datetime_cleared = (r_act == RESET_ACTION_INITIALIZE) or bool(rtc_backup_battery_lost)
    setup_initialized = r_act == RESET_ACTION_INITIALIZE

    eff_area = AREA_SETTING_UNCONFIGURED_DEFAULT_G110 if datetime_cleared else pre_reset_area_setting
    eff_dst = DAYLIGHT_SAVINGS_FACTORY_DEFAULT_G110 if datetime_cleared else dst
    eff_dt_val = "2020-01-01 00:00:00" if datetime_cleared else pre_reset_datetime_value
    eff_d_fmt = DATE_FORMAT_FACTORY_DEFAULT_G110 if datetime_cleared else d_fmt
    datetime_reprompt = datetime_cleared

    eff_vlight = VIDEO_LIGHT_MODE_FACTORY_DEFAULT_G110 if setup_initialized else vlight
    eff_hres = HDMI_RES_FACTORY_DEFAULT_G110 if setup_initialized else hres

    # Zero-RF isolation: Creators' App [Auto Time Correction] / [Auto Area Adjustment]
    # require BT/smartphone radio link, so [Airplane Mode] = [On] forces both Off.
    if ap_mode == AIRPLANE_MODE_ON_G110:
        eff_auto_time_corr = "Off"
        eff_auto_area_adj = "Off"
    else:
        eff_auto_time_corr = req_time_corr
        eff_auto_area_adj = req_area_adj

    # Hardware Log internal-recording 1080p downshift override:
    # When [Log Shooting] != Off AND internal card recording is active with
    # [Rec. Media dur HDMI Output] = On, manual 2160p (and Auto 4K negotiation)
    # is forced down to 1080p.
    log_downshift_active = (
        log_m in ACTIVE_LOG_SHOOTING_MODES_G110
        and bool(internal_recording_active)
        and rec_hdmi == REC_MEDIA_DUR_HDMI_ON_G110
    )
    if log_downshift_active and eff_hres in (HDMI_RES_AUTO_G110, HDMI_RES_2160P_G110):
        eff_hdmi_out_res = HDMI_RES_1080P_G110
    else:
        eff_hdmi_out_res = eff_hres

    return {
        "reset_action": r_act,
        "rtc_backup_battery_lost": bool(rtc_backup_battery_lost),
        "effective_post_reset_area_setting": eff_area,
        "effective_post_reset_daylight_savings": eff_dst,
        "effective_post_reset_datetime_value": eff_dt_val,
        "effective_post_reset_date_format": eff_d_fmt,
        "datetime_reprompt_required": datetime_reprompt,
        "airplane_mode": ap_mode,
        "effective_auto_time_correction": eff_auto_time_corr,
        "effective_auto_area_adjustment": eff_auto_area_adj,
        "effective_post_reset_video_light_mode": eff_vlight,
        "effective_post_reset_hdmi_resolution": eff_hres,
        "log_shooting_mode": log_m,
        "internal_recording_active": bool(internal_recording_active),
        "rec_media_dur_hdmi": rec_hdmi,
        "log_internal_rec_1080p_downshift_active": log_downshift_active,
        "effective_hdmi_output_resolution": eff_hdmi_out_res,
    }


def verify_area_datetime_videolight_hdmires_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE271,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE271,
    reset_action: str = RESET_ACTION_NONE,
    rtc_backup_battery_lost: bool = False,
    claimed_area_datetime_menu_label: str = CANONICAL_AREA_DATETIME_LABEL_G110,
    claimed_legacy_datetime_setup_spoof_events: int = 0,
    area_datetime_subitems: Sequence[str] = AREA_DATETIME_EXACT_4_SUBITEMS_G110,
    pre_reset_area_setting: str = AREA_SETTING_UNCONFIGURED_DEFAULT_G110,
    claimed_post_reset_area_setting: Optional[str] = None,
    pre_reset_daylight_savings: str = DAYLIGHT_SAVINGS_FACTORY_DEFAULT_G110,
    claimed_post_reset_daylight_savings: Optional[str] = None,
    pre_reset_datetime_value: str = "2026-11-17 14:38:00",
    claimed_post_reset_datetime_value: Optional[str] = None,
    pre_reset_date_format: str = DATE_FORMAT_FACTORY_DEFAULT_G110,
    claimed_post_reset_date_format: Optional[str] = None,
    airplane_mode: str = AIRPLANE_MODE_ON_G110,
    zero_rf_bench_required: bool = True,
    requested_auto_time_correction: str = "Off",
    claimed_effective_auto_time_correction: Optional[str] = None,
    requested_auto_area_adjustment: str = "Off",
    claimed_effective_auto_area_adjustment: Optional[str] = None,
    claimed_passive_tx_bytes_emitted: int = 0,
    claimed_unsolicited_rtc_timezone_jump_events: int = 0,
    pre_reset_video_light_mode: str = VIDEO_LIGHT_MODE_FACTORY_DEFAULT_G110,
    claimed_post_reset_video_light_mode: Optional[str] = None,
    mishoe_5v_draw_ma: int = 0,
    claimed_mishoe_5v_overcurrent_events: int = 0,
    pre_reset_hdmi_resolution: str = HDMI_RES_FACTORY_DEFAULT_G110,
    claimed_post_reset_hdmi_resolution: Optional[str] = None,
    log_shooting_mode: str = LOG_SHOOTING_OFF_G110,
    internal_recording_active: bool = False,
    rec_media_dur_hdmi: str = REC_MEDIA_DUR_HDMI_ON_G110,
    claimed_effective_hdmi_output_resolution: Optional[str] = None,
    claimed_hdmi_res_log_internal_rec_2160p_bypass_events: int = 0,
) -> AreaDateTimeVideoLightHdmiResGuardResult:
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME
        or isinstance(body_model_id, bool)
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE271
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G110_TELEMETRY_INVALID)
        errors.append(
            "Gate G110 requires ILME-FX3 (0x91030080, Help Guide ilc/2210, Ver. 7.02)."
        )

    norm_reset = _norm_reset_action_phase271(reset_action)
    norm_dst = _norm_on_off_phase271(pre_reset_daylight_savings)
    norm_d_fmt = _norm_date_format_g110(pre_reset_date_format)
    norm_airplane = _norm_on_off_phase271(airplane_mode)
    norm_req_time = _norm_on_off_phase271(requested_auto_time_correction)
    norm_req_area = _norm_on_off_phase271(requested_auto_area_adjustment)
    norm_vlight = _norm_video_light_mode_g110(pre_reset_video_light_mode)
    norm_hres = _norm_hdmi_resolution_g110(pre_reset_hdmi_resolution)
    norm_log = _norm_log_shooting_mode_g110(log_shooting_mode)
    norm_rec_hdmi = _norm_rec_media_dur_hdmi_g110(rec_media_dur_hdmi)

    if (
        any(
            x is None
            for x in (
                norm_reset,
                norm_dst,
                norm_d_fmt,
                norm_airplane,
                norm_req_time,
                norm_req_area,
                norm_vlight,
                norm_hres,
                norm_log,
                norm_rec_hdmi,
            )
        )
        or not isinstance(rtc_backup_battery_lost, bool)
        or not isinstance(zero_rf_bench_required, bool)
        or not isinstance(internal_recording_active, bool)
        or not isinstance(pre_reset_area_setting, str)
        or not pre_reset_area_setting.strip()
        or not isinstance(pre_reset_datetime_value, str)
        or not pre_reset_datetime_value.strip()
        or tuple(area_datetime_subitems) != AREA_DATETIME_EXACT_4_SUBITEMS_G110
    ):
        _add_code(codes, STATUS_BLOCKED_G110_TELEMETRY_INVALID)
        errors.append("Invalid or unrecognized G110 Area/Date/VideoLight/HDMI enum or subitems.")

    for int_val, name in (
        (
            claimed_legacy_datetime_setup_spoof_events,
            "claimed_legacy_datetime_setup_spoof_events",
        ),
        (claimed_passive_tx_bytes_emitted, "claimed_passive_tx_bytes_emitted"),
        (
            claimed_unsolicited_rtc_timezone_jump_events,
            "claimed_unsolicited_rtc_timezone_jump_events",
        ),
        (mishoe_5v_draw_ma, "mishoe_5v_draw_ma"),
        (claimed_mishoe_5v_overcurrent_events, "claimed_mishoe_5v_overcurrent_events"),
        (
            claimed_hdmi_res_log_internal_rec_2160p_bypass_events,
            "claimed_hdmi_res_log_internal_rec_2160p_bypass_events",
        ),
    ):
        if isinstance(int_val, bool) or not isinstance(int_val, int) or int_val < 0:
            _add_code(codes, STATUS_BLOCKED_G110_TELEMETRY_INVALID)
            errors.append(f"{name} must be a non-negative integer.")

    # Legacy "Date/Time Setup" nomenclature spoofing check
    dt_spoof_events = (
        claimed_legacy_datetime_setup_spoof_events
        if isinstance(claimed_legacy_datetime_setup_spoof_events, int)
        and not isinstance(claimed_legacy_datetime_setup_spoof_events, bool)
        else 1
    )
    if (
        not isinstance(claimed_area_datetime_menu_label, str)
        or claimed_area_datetime_menu_label.strip().strip("[]")
        != CANONICAL_AREA_DATETIME_LABEL_G110
    ):
        dt_spoof_events = max(1, dt_spoof_events)
    if dt_spoof_events != 0:
        _add_code(codes, STATUS_BLOCKED_G110_LEGACY_DATETIME_SETUP_SPOOF_VIOLATION)
        errors.append(
            "ILME-FX3 Ver. 7.02 uses [Area/Date/Time Setting], rejecting legacy 'Date/Time Setup' spoofing."
        )

    resolved = resolve_fx3_area_datetime_videolight_and_hdmires_state(
        reset_action=norm_reset or RESET_ACTION_NONE,
        rtc_backup_battery_lost=bool(rtc_backup_battery_lost),
        pre_reset_area_setting=(
            pre_reset_area_setting
            if isinstance(pre_reset_area_setting, str)
            else AREA_SETTING_UNCONFIGURED_DEFAULT_G110
        ),
        pre_reset_daylight_savings=norm_dst or DAYLIGHT_SAVINGS_FACTORY_DEFAULT_G110,
        pre_reset_datetime_value=(
            pre_reset_datetime_value
            if isinstance(pre_reset_datetime_value, str)
            else "2026-11-17 14:38:00"
        ),
        pre_reset_date_format=norm_d_fmt or DATE_FORMAT_FACTORY_DEFAULT_G110,
        airplane_mode=norm_airplane or AIRPLANE_MODE_ON_G110,
        requested_auto_time_correction=norm_req_time or "Off",
        requested_auto_area_adjustment=norm_req_area or "Off",
        pre_reset_video_light_mode=norm_vlight or VIDEO_LIGHT_MODE_FACTORY_DEFAULT_G110,
        pre_reset_hdmi_resolution=norm_hres or HDMI_RES_FACTORY_DEFAULT_G110,
        log_shooting_mode=norm_log or LOG_SHOOTING_OFF_G110,
        internal_recording_active=bool(internal_recording_active),
        rec_media_dur_hdmi=norm_rec_hdmi or REC_MEDIA_DUR_HDMI_ON_G110,
    )

    matrix = compute_area_datetime_videolight_hdmires_matrix()
    if not matrix["all_invariants_hold"]:
        _add_code(codes, STATUS_BLOCKED_G110_TELEMETRY_INVALID)
        errors.append("G110 Area/Date/Time / Video Light / HDMI Resolution matrix failed.")

    # Zero-RF Creators' App suppression guard
    tx_bytes = (
        claimed_passive_tx_bytes_emitted
        if isinstance(claimed_passive_tx_bytes_emitted, int)
        and not isinstance(claimed_passive_tx_bytes_emitted, bool)
        else 1
    )
    rtc_jumps = (
        claimed_unsolicited_rtc_timezone_jump_events
        if isinstance(claimed_unsolicited_rtc_timezone_jump_events, int)
        and not isinstance(claimed_unsolicited_rtc_timezone_jump_events, bool)
        else 1
    )
    eff_time_corr = (
        _norm_on_off_phase271(claimed_effective_auto_time_correction)
        if claimed_effective_auto_time_correction is not None
        else resolved["effective_auto_time_correction"]
    )
    eff_area_adj = (
        _norm_on_off_phase271(claimed_effective_auto_area_adjustment)
        if claimed_effective_auto_area_adjustment is not None
        else resolved["effective_auto_area_adjustment"]
    )
    if (
        (zero_rf_bench_required and resolved["airplane_mode"] != AIRPLANE_MODE_ON_G110)
        or (
            resolved["airplane_mode"] == AIRPLANE_MODE_ON_G110
            and (eff_time_corr != "Off" or eff_area_adj != "Off")
        )
        or tx_bytes != 0
        or rtc_jumps != 0
    ):
        _add_code(codes, STATUS_BLOCKED_G110_ZERO_RF_CREATORS_APP_SYNC_VIOLATION)
        errors.append(
            "Zero-RF bench posture requires [Airplane Mode] = [On], Creators' App Auto Time/Area suppression, 0 TX bytes, and 0 unsolicited RTC/timezone jumps."
        )

    # MI-Shoe 5V <= 900 mA (G24) rail budget check
    overcurrent_events = (
        claimed_mishoe_5v_overcurrent_events
        if isinstance(claimed_mishoe_5v_overcurrent_events, int)
        and not isinstance(claimed_mishoe_5v_overcurrent_events, bool)
        else 1
    )
    draw_ma = (
        mishoe_5v_draw_ma
        if isinstance(mishoe_5v_draw_ma, int) and not isinstance(mishoe_5v_draw_ma, bool)
        else MISHOE_5V_MAX_BUDGET_MA_G110 + 1
    )
    if draw_ma > MISHOE_5V_MAX_BUDGET_MA_G110:
        overcurrent_events = max(1, overcurrent_events)
    if overcurrent_events != 0:
        _add_code(codes, STATUS_BLOCKED_G110_MISHOE_5V_OVERCURRENT_VIOLATION)
        errors.append(
            f"MI-Shoe 5V accessory load ({draw_ma} mA) exceeds Gate G24 budget ({MISHOE_5V_MAX_BUDGET_MA_G110} mA)."
        )

    # Hardware Log internal-recording 1080p downshift override check
    log_bypass_events = (
        claimed_hdmi_res_log_internal_rec_2160p_bypass_events
        if isinstance(claimed_hdmi_res_log_internal_rec_2160p_bypass_events, int)
        and not isinstance(claimed_hdmi_res_log_internal_rec_2160p_bypass_events, bool)
        else 1
    )
    claimed_eff_hres = (
        _norm_hdmi_resolution_g110(claimed_effective_hdmi_output_resolution)
        if claimed_effective_hdmi_output_resolution is not None
        else resolved["effective_hdmi_output_resolution"]
    )
    if (
        claimed_effective_hdmi_output_resolution is not None
        and claimed_eff_hres != resolved["effective_hdmi_output_resolution"]
    ):
        if resolved["log_internal_rec_1080p_downshift_active"]:
            log_bypass_events = max(1, log_bypass_events)
        else:
            _add_code(codes, STATUS_BLOCKED_G110_HDMI_RES_LOG_1080P_OVERRIDE_VIOLATION)
            errors.append("Effective HDMI output resolution mismatches Log/RecMedia state.")
    if log_bypass_events != 0:
        _add_code(codes, STATUS_BLOCKED_G110_HDMI_RES_LOG_1080P_OVERRIDE_VIOLATION)
        errors.append(
            "Log internal recording with [Rec. Media dur HDMI Output] = [On] must enforce 1080p downshift over manual 2160p."
        )

    # Setup reset persistence verification
    setup_pairs = (
        (
            claimed_post_reset_area_setting,
            resolved["effective_post_reset_area_setting"],
            lambda s: s if isinstance(s, str) else None,
        ),
        (
            claimed_post_reset_daylight_savings,
            resolved["effective_post_reset_daylight_savings"],
            _norm_on_off_phase271,
        ),
        (
            claimed_post_reset_datetime_value,
            resolved["effective_post_reset_datetime_value"],
            lambda s: s if isinstance(s, str) else None,
        ),
        (
            claimed_post_reset_date_format,
            resolved["effective_post_reset_date_format"],
            _norm_date_format_g110,
        ),
        (
            claimed_post_reset_video_light_mode,
            resolved["effective_post_reset_video_light_mode"],
            _norm_video_light_mode_g110,
        ),
        (
            claimed_post_reset_hdmi_resolution,
            resolved["effective_post_reset_hdmi_resolution"],
            _norm_hdmi_resolution_g110,
        ),
    )
    survives_ok = True
    for claimed_raw, expected_val, norm_fn in setup_pairs:
        if claimed_raw is not None:
            if norm_fn(claimed_raw) != expected_val:
                survives_ok = False
                break
    if not survives_ok:
        _add_code(codes, STATUS_BLOCKED_G110_SETUP_RESET_PERSISTENCE_VIOLATION)
        errors.append(
            "[Area/Date/Time Setting], [Video Light Mode], and [HDMI Resolution] reside under [Setup] and must survive [Camera Settings Reset], clearing only on [Initialize] (or RTC loss for clock)."
        )

    valid = not codes
    status = STATUS_VERIFIED_G110 if valid else codes[0]

    return AreaDateTimeVideoLightHdmiResGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}"
        if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
        else "invalid",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        reset_action=resolved["reset_action"],
        rtc_backup_battery_lost=resolved["rtc_backup_battery_lost"],
        area_date_time_menu_path=AREA_DATE_TIME_MENU_PATH_G110,
        video_light_mode_menu_path=VIDEO_LIGHT_MODE_MENU_PATH_G110,
        hdmi_resolution_menu_path=HDMI_RESOLUTION_MENU_PATH_G110,
        airplane_mode_menu_path=AIRPLANE_MODE_MENU_PATH_G110,
        area_datetime_menu_label=str(claimed_area_datetime_menu_label),
        legacy_datetime_setup_spoof_events=dt_spoof_events,
        area_datetime_subitems=tuple(area_datetime_subitems),
        pre_reset_area_setting=str(pre_reset_area_setting),
        effective_post_reset_area_setting=resolved[
            "effective_post_reset_area_setting"
        ],
        pre_reset_daylight_savings=norm_dst or str(pre_reset_daylight_savings),
        effective_post_reset_daylight_savings=resolved[
            "effective_post_reset_daylight_savings"
        ],
        pre_reset_datetime_value=str(pre_reset_datetime_value),
        effective_post_reset_datetime_value=resolved[
            "effective_post_reset_datetime_value"
        ],
        pre_reset_date_format=norm_d_fmt or str(pre_reset_date_format),
        effective_post_reset_date_format=resolved["effective_post_reset_date_format"],
        datetime_reprompt_required=resolved["datetime_reprompt_required"],
        airplane_mode=resolved["airplane_mode"],
        zero_rf_bench_enforced=bool(
            resolved["airplane_mode"] == AIRPLANE_MODE_ON_G110 and tx_bytes == 0
        ),
        requested_auto_time_correction=norm_req_time
        or str(requested_auto_time_correction),
        effective_auto_time_correction=str(eff_time_corr),
        requested_auto_area_adjustment=norm_req_area
        or str(requested_auto_area_adjustment),
        effective_auto_area_adjustment=str(eff_area_adj),
        passive_tx_bytes_emitted=tx_bytes,
        unsolicited_rtc_timezone_jump_events=rtc_jumps,
        pre_reset_video_light_mode=norm_vlight or str(pre_reset_video_light_mode),
        effective_post_reset_video_light_mode=resolved[
            "effective_post_reset_video_light_mode"
        ],
        mishoe_5v_draw_ma=draw_ma,
        mishoe_5v_budget_ma=MISHOE_5V_MAX_BUDGET_MA_G110,
        mishoe_5v_overcurrent_events=overcurrent_events,
        log_shooting_mode=resolved["log_shooting_mode"],
        internal_recording_active=resolved["internal_recording_active"],
        rec_media_dur_hdmi=resolved["rec_media_dur_hdmi"],
        pre_reset_hdmi_resolution=norm_hres or str(pre_reset_hdmi_resolution),
        effective_post_reset_hdmi_resolution=resolved[
            "effective_post_reset_hdmi_resolution"
        ],
        effective_hdmi_output_resolution=str(claimed_eff_hres),
        log_internal_rec_1080p_downshift_active=resolved[
            "log_internal_rec_1080p_downshift_active"
        ],
        hdmi_res_log_internal_rec_2160p_bypass_events=log_bypass_events,
        setup_items_survive_camera_settings_reset=survives_ok,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g110_area_datetime_videolight_hdmires_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    area_datetime_videolight_hdmires_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase271DonorAuditResult] = None,
) -> Tuple[GateVerdict, G110AreaDateTimeVideoLightHdmiResGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase271_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_area_datetime_videolight_hdmires_guard(
        **dict(area_datetime_videolight_hdmires_kwargs or {})
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
        errors.append("Persistent eMMC write authorization requested in Gate G110.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G110 if valid else codes[0]

    res = G110AreaDateTimeVideoLightHdmiResGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        area_datetime_videolight_hdmires_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, area_dt={guard.area_datetime_menu_label}"
        f"(airplane={guard.airplane_mode},tx={guard.passive_tx_bytes_emitted},jumps={guard.unsolicited_rtc_timezone_jump_events}), "
        f"vlight={guard.effective_post_reset_video_light_mode}"
        f"(5v={guard.mishoe_5v_draw_ma}/{guard.mishoe_5v_budget_ma}mA), "
        f"hdmi_res={guard.effective_post_reset_hdmi_resolution}->"
        f"{guard.effective_hdmi_output_resolution}(bypass={guard.hdmi_res_log_internal_rec_2160p_bypass_events})"
    )
    verdict = GateVerdict(
        gate_id=G110_GATE_ID,
        gate_code=G110_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `110`-Gate Master Safety Preflight (`G01..G110`)
# ---------------------------------------------------------------------------


def evaluate_110gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    focus_mag_peaking_kwargs: Optional[Mapping[str, Any]] = None,
    area_datetime_videolight_hdmires_kwargs: Optional[Mapping[str, Any]] = None,
    master_108_override: Optional[Master108GateReport] = None,
    **m108_passthrough_kwargs: Any,
) -> Master110GateReport:
    """Evaluate all 110 Master Safety Gates (`G01..G110`) deterministically by
    delegating `G01..G108` directly to `evaluate_108gate_preflight()`.
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

    m108_report: Master108GateReport = (
        master_108_override
        if master_108_override is not None
        else evaluate_108gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m108_passthrough_kwargs,
        )
    )

    phase271_audit = audit_phase271_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g109_verdict, g109_res = evaluate_g109_focus_mag_peaking_af_illuminator_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        focus_mag_peaking_kwargs=focus_mag_peaking_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase271_audit,
    )

    g110_verdict, g110_res = evaluate_g110_area_datetime_videolight_hdmires_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        area_datetime_videolight_hdmires_kwargs=area_datetime_videolight_hdmires_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase271_audit,
    )

    gates_109_to_110 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g109_verdict, g110_verdict)
    ]
    all_gates = tuple(list(m108_report.gates) + gates_109_to_110)

    g01_to_g12_verified = int(m108_report.summary["g01_to_g12_verified"])
    g13_to_g108_verified = int(m108_report.summary["g13_to_g106_verified"]) + int(
        m108_report.summary["g107_to_g108_verified"]
    )
    g109_to_g110_verified = sum(1 for v in (g109_verdict, g110_verdict) if v.passed)
    total_verified = (
        g01_to_g12_verified + g13_to_g108_verified + g109_to_g110_verified
    )

    g109_to_g110_all_passed = g109_to_g110_verified == 2
    g13_to_g110_all_passed = (
        m108_report.g13_to_g108_all_passed and g109_to_g110_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m108_report.gates[:9])

    offline_107_verified = (
        g01_to_g09_ok
        and m108_report.offline_105_gates_verified
        and g109_to_g110_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_110_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g110_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m108_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_107_verified
        and m108_report.h0_h1_trial_entry_allowed
        and g109_to_g110_all_passed
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
        list(m108_report.errors)
        + list(g109_verdict.errors)
        + list(g110_verdict.errors)
    )
    warnings: List[str] = (
        list(m108_report.warnings)
        + list(g109_verdict.warnings)
        + list(g110_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m108_report.g13_to_g108_all_passed:
        overall_status = m108_report.status
    elif not g109_verdict.passed:
        overall_status = g109_verdict.status
    elif not g110_verdict.passed:
        overall_status = g110_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_110_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_110_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_110_verified:
        overall_status = "VERIFIED_ALL_110_GATES"
    else:
        overall_status = "VERIFIED_107_OF_110_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m108_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g109_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g110_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 110,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 110 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g108_verified": g13_to_g108_verified,
        "g109_to_g110_verified": g109_to_g110_verified,
        "g13_to_g110_all_passed": g13_to_g110_all_passed,
        "g109_to_g110_all_passed": g109_to_g110_all_passed,
        "offline_107_gates_verified": offline_107_verified,
        "all_110_gates_verified": all_110_verified,
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

    return Master110GateReport(
        schema=REALHW_FOCUS_MAG_DATETIME_VIDEOLIGHT_HDMIRES_110GATE_SCHEMA,
        version=REALHW_FOCUS_MAG_DATETIME_VIDEOLIGHT_HDMIRES_110GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_107_gates_verified=offline_107_verified,
        all_110_gates_verified=all_110_verified,
        g13_to_g110_all_passed=g13_to_g110_all_passed,
        g109_to_g110_all_passed=g109_to_g110_all_passed,
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
        master_108_report=m108_report.to_dict(),
        g109_result=g109_res.to_dict(),
        g110_result=g110_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_110_master_safety_gates = evaluate_110gate_preflight
run_110_gate_preflight = evaluate_110gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard",
        description=(
            "Phase 271 (110/110 Safety Gate Milestone) Gates G109 ([Focus Assistant] "
            "[Auto Magnifier in MF], Custom Button 5, [Initial Focus Mag.] x1.0, "
            "[Peaking Display] Clean-HDMI Isolation & Still-Only [AF Illuminator]) "
            "+ G110 ([Area/Date/Time Setting], Zero-RF Creators' App Suppression, "
            "[Video Light Mode] Power Link & MI-Shoe 5V <= 900 mA, [HDMI Resolution] "
            "Auto & Log 1080p Downshift) + Unified 110-Gate Master Safety Preflight"
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

    report = evaluate_110gate_preflight(
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
            f"verified={report.summary['verified_gates']}/110 "
            f"g109_to_g110_all_passed={report.g109_to_g110_all_passed} "
            f"all_110_gates_verified={report.all_110_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = (
        report.all_110_gates_verified
        if args.dry_run_simulated
        else report.offline_107_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
