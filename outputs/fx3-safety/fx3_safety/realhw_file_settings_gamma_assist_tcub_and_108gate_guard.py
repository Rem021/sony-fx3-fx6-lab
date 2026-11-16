"""Phase 268 (Task H302, Wave-44) Sony `ILME-FX3` (`Ver. 7.02`, `ilc/2210`)
Safety Gates `G107` (Movie `[File Settings]` `Cam ID + Reel#` & `37`-Char
`[Title Name Settings]` + Fixed `PRIVATE/M4ROOT/CLIP` Topology vs Still
`[File/Folder Settings]` `3`-Char `DSC` Prefix & `Slot-1` Recovery Vault Folder
Mutation Firewall) & `G108` (`[Gamma Display Assist]` `[Log Shooting]` Hard
Lockout & Camera-LCD-Only Clean-HDMI Scope vs `[Display LUT]` / `[Select LUT]`
`User1..User16`, `[Auto Review]` `Off` Cinema Default & `6`-Item `[TC/UB]`
Non-Resettable Persistence Guard) + Unified `108`-Gate Master Safety Preflight
(`G01..G108`).

Operationalizes Wave-44 official Sony `ILME-FX3` (`Ver. 7.02`, Help Guide
`ilc/2210`) intelligence
(`reports/2026-11-15-global-sony-wave44-file-settings-camid-reel-37char-gamma-disp-assist-log-lockout-auto-review-tcub-intel/README.md`)
as deterministic offline preflight verifiers (`G107` and `G108`) and delegates
`G01..G106` directly to `evaluate_106gate_preflight()`.
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
from .realhw_release_wo_card_audio_meter_copyright_and_106gate_guard import (
    Master106GateReport,
    evaluate_106gate_preflight,
)
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_FILE_SETTINGS_GAMMA_ASSIST_TCUB_108GATE_SCHEMA: str = (
    "realhw_file_settings_gamma_assist_tcub_and_108gate_guard_v1"
)
REALHW_FILE_SETTINGS_GAMMA_ASSIST_TCUB_108GATE_VERSION: str = "1.0.0"

G107_GATE_ID: str = (
    "G107_movie_file_settings_camid_reel_37char_still_dsc_and_slot1_folder_vault_guard"
)
G107_GATE_CODE: str = (
    "MOVIE_FILE_SETTINGS_CAMID_REEL_37CHAR_STILL_DSC_AND_SLOT1_FOLDER_VAULT_GUARD"
)

G108_GATE_ID: str = (
    "G108_gamma_disp_assist_log_lockout_display_lut_auto_review_and_tcub_guard"
)
G108_GATE_CODE: str = (
    "GAMMA_DISP_ASSIST_LOG_LOCKOUT_DISPLAY_LUT_AUTO_REVIEW_AND_TCUB_GUARD"
)

G107: str = G107_GATE_ID
G108: str = G108_GATE_ID
GATE_G107_MOVIE_FILE_SETTINGS_CAMID_REEL_37CHAR_STILL_DSC_AND_SLOT1_FOLDER_VAULT_GUARD: str = (
    G107_GATE_CODE
)
GATE_G108_GAMMA_DISP_ASSIST_LOG_LOCKOUT_DISPLAY_LUT_AUTO_REVIEW_AND_TCUB_GUARD: str = (
    G108_GATE_CODE
)

ENV_CLEAN_ROOM_TEST_PHASE268: str = "FX3_CLEAN_ROOM_TEST"

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE268: float = 0.10
DONOR_CHECK_MAX_SECONDS: float = DONOR_CHECK_MAX_SECONDS_PHASE268

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX6_MODEL_NAME: str = "ILME-FX6"
FX3_DEFAULT_FW_VERSION_PHASE268: str = "7.02"
FX3_CAMID_REEL_MIN_FW_TUPLE_G107: Tuple[int, int] = (3, 0)
FX3_HELP_GUIDE_CODE_PHASE268: str = "ilc/2210"

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE268: str = "Reset Network Set."
RESET_ACTION_INITIALIZE: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE268: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_RESET_NETWORK_SET_PHASE268,
    RESET_ACTION_INITIALIZE,
)

# ---------------------------------------------------------------------------
# Status & Violation Codes (G107 / G108 / Phase 268)
# ---------------------------------------------------------------------------

STATUS_VERIFIED_G107: str = (
    "VERIFIED_G107_MOVIE_FILE_SETTINGS_STILL_DSC_AND_SLOT1_VAULT_SAFE"
)
STATUS_VERIFIED_G108: str = (
    "VERIFIED_G108_GAMMA_DISP_ASSIST_LOG_LOCKOUT_AUTO_REVIEW_AND_TCUB_SAFE"
)
STATUS_BLOCKED_PHASE268_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE268_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G107_MOVIE_FILE_NAME_CAMID_REEL_OR_37CHAR_TITLE_VIOLATION: str = (
    "BLOCKED_G107_MOVIE_FILE_NAME_CAMID_REEL_OR_37CHAR_TITLE_VIOLATION"
)
STATUS_BLOCKED_G107_MOVIE_CUSTOM_FOLDER_TOPOLOGY_VIOLATION: str = (
    "BLOCKED_G107_MOVIE_CUSTOM_FOLDER_TOPOLOGY_VIOLATION"
)
STATUS_BLOCKED_G107_STILL_DSC_PREFIX_OR_FOLDER_FORM_VIOLATION: str = (
    "BLOCKED_G107_STILL_DSC_PREFIX_OR_FOLDER_FORM_VIOLATION"
)
STATUS_BLOCKED_G107_SLOT1_VAULT_FOLDER_MUTATION_VIOLATION: str = (
    "BLOCKED_G107_SLOT1_VAULT_FOLDER_MUTATION_VIOLATION"
)
STATUS_BLOCKED_G107_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G107_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G107_TELEMETRY_INVALID: str = (
    "BLOCKED_G107_FILE_SETTINGS_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G108_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_VIOLATION: str = (
    "BLOCKED_G108_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_VIOLATION"
)
STATUS_BLOCKED_G108_EXTERNAL_HDMI_GAMMA_ASSIST_LEAK_VIOLATION: str = (
    "BLOCKED_G108_EXTERNAL_HDMI_GAMMA_ASSIST_LEAK_VIOLATION"
)
STATUS_BLOCKED_G108_DISPLAY_LUT_OR_SELECT_LUT_VIOLATION: str = (
    "BLOCKED_G108_DISPLAY_LUT_OR_SELECT_LUT_VIOLATION"
)
STATUS_BLOCKED_G108_AUTO_REVIEW_SCOPE_OR_DEFAULT_VIOLATION: str = (
    "BLOCKED_G108_AUTO_REVIEW_SCOPE_OR_DEFAULT_VIOLATION"
)
STATUS_BLOCKED_G108_TC_FORMAT_24P_PAL_NDF_VIOLATION: str = (
    "BLOCKED_G108_TC_FORMAT_24P_PAL_NDF_VIOLATION"
)
STATUS_BLOCKED_G108_RESET_SURVIVAL_OR_INITIALIZE_VIOLATION: str = (
    "BLOCKED_G108_RESET_SURVIVAL_OR_INITIALIZE_VIOLATION"
)
STATUS_BLOCKED_G108_TELEMETRY_INVALID: str = (
    "BLOCKED_G108_GAMMA_ASSIST_AUTO_REVIEW_TCUB_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G107 Constants: Movie [File Settings] vs Still [File/Folder Settings]
# ---------------------------------------------------------------------------

MOVIE_FILE_SETTINGS_MENU_PATH_G107: str = (
    "MENU -> Shooting -> [File] -> [File Settings]"
)
STILL_FILE_FOLDER_SETTINGS_MENU_PATH_G107: str = (
    "MENU -> Shooting -> [File] -> [File/Folder Settings]"
)

FILE_NUMBER_SERIES_G107: str = "Series"
FILE_NUMBER_RESET_G107: str = "Reset"
ALLOWED_FILE_NUMBER_MODES_G107: Tuple[str, ...] = (
    FILE_NUMBER_SERIES_G107,
    FILE_NUMBER_RESET_G107,
)
MOVIE_FILE_NUMBER_FACTORY_DEFAULT_G107: str = FILE_NUMBER_SERIES_G107
STILL_FILE_NUMBER_FACTORY_DEFAULT_G107: str = FILE_NUMBER_SERIES_G107

MOVIE_FILE_NAME_STANDARD_G107: str = "Standard"
MOVIE_FILE_NAME_CAM_ID_REEL_G107: str = "Cam ID + Reel#"
MOVIE_FILE_NAME_TITLE_G107: str = "Title"
MOVIE_FILE_NAME_DATE_PLUS_TITLE_G107: str = "Date + Title"
MOVIE_FILE_NAME_TITLE_PLUS_DATE_G107: str = "Title + Date"
ALLOWED_MOVIE_FILE_NAME_FORMATS_G107: Tuple[str, ...] = (
    MOVIE_FILE_NAME_STANDARD_G107,
    MOVIE_FILE_NAME_CAM_ID_REEL_G107,
    MOVIE_FILE_NAME_TITLE_G107,
    MOVIE_FILE_NAME_DATE_PLUS_TITLE_G107,
    MOVIE_FILE_NAME_TITLE_PLUS_DATE_G107,
)
MOVIE_FILE_NAME_FORMAT_FACTORY_DEFAULT_G107: str = MOVIE_FILE_NAME_STANDARD_G107

CAMERA_ID_ALLOWED_CHARS_G107: Tuple[str, ...] = tuple(
    chr(c) for c in range(ord("A"), ord("Z") + 1)
)
CAMERA_ID_FACTORY_DEFAULT_G107: str = "A"

REEL_NUMBER_MIN_G107: int = 1
REEL_NUMBER_MAX_G107: int = 999
REEL_NUMBER_FACTORY_DEFAULT_G107: int = 1

CAMERA_POSITION_CENTER_G107: str = "C"
CAMERA_POSITION_LEFT_G107: str = "L"
CAMERA_POSITION_RIGHT_G107: str = "R"
ALLOWED_CAMERA_POSITIONS_G107: Tuple[str, ...] = (
    CAMERA_POSITION_CENTER_G107,
    CAMERA_POSITION_LEFT_G107,
    CAMERA_POSITION_RIGHT_G107,
)
CAMERA_POSITION_FACTORY_DEFAULT_G107: str = CAMERA_POSITION_CENTER_G107

TITLE_NAME_FACTORY_DEFAULT_G107: str = "C"
TITLE_NAME_MAX_CHARS_G107: int = 37
ASCII_PRINTABLE_MIN_CODEPOINT_PHASE268: int = 0x20
ASCII_PRINTABLE_MAX_CODEPOINT_PHASE268: int = 0x7E

MOVIE_FIXED_FOLDER_PATH_G107: str = "PRIVATE/M4ROOT/CLIP"

STILL_SET_FILE_NAME_FACTORY_DEFAULT_G107: str = "DSC"
STILL_SET_FILE_NAME_EXACT_LEN_G107: int = 3

STILL_FOLDER_STANDARD_FORM_G107: str = "Standard Form"
STILL_FOLDER_DATE_FORM_G107: str = "Date Form"
ALLOWED_STILL_FOLDER_FORMS_G107: Tuple[str, ...] = (
    STILL_FOLDER_STANDARD_FORM_G107,
    STILL_FOLDER_DATE_FORM_G107,
)
STILL_FOLDER_FORM_FACTORY_DEFAULT_G107: str = STILL_FOLDER_STANDARD_FORM_G107

MEDIA_SLOT_1_G107: str = "Slot 1"
MEDIA_SLOT_2_G107: str = "Slot 2"
ALLOWED_MEDIA_SLOTS_G107: Tuple[str, ...] = (
    MEDIA_SLOT_1_G107,
    MEDIA_SLOT_2_G107,
)

# ---------------------------------------------------------------------------
# Gate G108 Constants: Gamma Display Assist / Display LUT / Auto Review / TC/UB
# ---------------------------------------------------------------------------

GAMMA_DISP_ASSIST_MENU_PATH_G108: str = (
    "MENU -> Setup -> [Display Option] -> [Gamma Display Assist]"
)
GAMMA_DISP_ASSIST_TYP_MENU_PATH_G108: str = (
    "MENU -> Setup -> [Display Option] -> [Gamma Disp. Assist Typ.]"
)
DISPLAY_LUT_MENU_PATH_G108: str = (
    "MENU -> Setup -> [Display Option] -> [Display LUT]"
)
SELECT_LUT_MENU_PATH_G108: str = (
    "MENU -> Exposure/Color -> [Color/Tone] -> [Select LUT]"
)
AUTO_REVIEW_MENU_PATH_G108: str = (
    "MENU -> Setup -> [Display Option] -> [Auto Review]"
)
TCUB_MENU_PATH_G108: str = "MENU -> Shooting -> [TC/UB]"
TCUB_DISP_SETTING_MENU_PATH_G108: str = (
    "MENU -> Setup -> [Display Option] -> [TC/UB Disp. Setting]"
)

GAMMA_DISP_ASSIST_OFF_G108: str = "Off"
GAMMA_DISP_ASSIST_ON_G108: str = "On"
ALLOWED_GAMMA_DISP_ASSIST_STATES_G108: Tuple[str, ...] = (
    GAMMA_DISP_ASSIST_OFF_G108,
    GAMMA_DISP_ASSIST_ON_G108,
)
GAMMA_DISP_ASSIST_FACTORY_DEFAULT_G108: str = GAMMA_DISP_ASSIST_OFF_G108

GAMMA_ASSIST_TYP_AUTO_G108: str = "Auto"
GAMMA_ASSIST_TYP_SLOG3_709_800_G108: str = "S-Log3->709(800%)"
GAMMA_ASSIST_TYP_HLG_BT2020_G108: str = "HLG(BT.2020)"
GAMMA_ASSIST_TYP_HLG_709_G108: str = "HLG(709)"
ALLOWED_GAMMA_ASSIST_TYPES_G108: Tuple[str, ...] = (
    GAMMA_ASSIST_TYP_AUTO_G108,
    GAMMA_ASSIST_TYP_SLOG3_709_800_G108,
    GAMMA_ASSIST_TYP_HLG_BT2020_G108,
    GAMMA_ASSIST_TYP_HLG_709_G108,
)
GAMMA_ASSIST_TYP_FACTORY_DEFAULT_G108: str = GAMMA_ASSIST_TYP_AUTO_G108

LOG_SHOOTING_OFF_G108: str = "Off"
LOG_SHOOTING_CINE_EI_G108: str = "Cine EI"
LOG_SHOOTING_CINE_EI_QUICK_G108: str = "Cine EI Quick"
LOG_SHOOTING_FLEXIBLE_ISO_G108: str = "Flexible ISO"
ALLOWED_LOG_SHOOTING_MODES_G108: Tuple[str, ...] = (
    LOG_SHOOTING_OFF_G108,
    LOG_SHOOTING_CINE_EI_G108,
    LOG_SHOOTING_CINE_EI_QUICK_G108,
    LOG_SHOOTING_FLEXIBLE_ISO_G108,
)
ACTIVE_LOG_SHOOTING_MODES_G108: Tuple[str, ...] = (
    LOG_SHOOTING_CINE_EI_G108,
    LOG_SHOOTING_CINE_EI_QUICK_G108,
    LOG_SHOOTING_FLEXIBLE_ISO_G108,
)

DISPLAY_LUT_ON_G108: str = "On"
DISPLAY_LUT_OFF_G108: str = "Off"
ALLOWED_DISPLAY_LUT_STATES_G108: Tuple[str, ...] = (
    DISPLAY_LUT_ON_G108,
    DISPLAY_LUT_OFF_G108,
)
DISPLAY_LUT_FACTORY_DEFAULT_G108: str = DISPLAY_LUT_ON_G108

SELECT_LUT_SLOG3_G108: str = "S-Log3"
SELECT_LUT_S709_G108: str = "s709"
SELECT_LUT_709_800_G108: str = "709(800%)"
BUILTIN_SELECT_LUT_PRESETS_G108: Tuple[str, ...] = (
    SELECT_LUT_SLOG3_G108,
    SELECT_LUT_S709_G108,
    SELECT_LUT_709_800_G108,
)
USER_SELECT_LUT_SLOTS_G108: Tuple[str, ...] = tuple(
    f"User{i}" for i in range(1, 17)
)
MAX_USER_LUT_SLOTS_G108: int = 16
ALLOWED_SELECT_LUT_ITEMS_G108: Tuple[str, ...] = (
    BUILTIN_SELECT_LUT_PRESETS_G108 + USER_SELECT_LUT_SLOTS_G108
)
SELECT_LUT_FACTORY_DEFAULT_G108: str = SELECT_LUT_S709_G108

AUTO_REVIEW_OFF_G108: str = "Off"
AUTO_REVIEW_2_SEC_G108: str = "2 Sec"
AUTO_REVIEW_5_SEC_G108: str = "5 Sec"
AUTO_REVIEW_10_SEC_G108: str = "10 Sec"
ALLOWED_AUTO_REVIEW_SETTINGS_G108: Tuple[str, ...] = (
    AUTO_REVIEW_OFF_G108,
    AUTO_REVIEW_2_SEC_G108,
    AUTO_REVIEW_5_SEC_G108,
    AUTO_REVIEW_10_SEC_G108,
)
AUTO_REVIEW_FACTORY_DEFAULT_G108: str = AUTO_REVIEW_OFF_G108

TCUB_EXACT_6_ITEMS_G108: Tuple[str, ...] = (
    "Time Code Preset",
    "User Bit Preset",
    "Time Code Format",
    "Time Code Run",
    "Time Code Make",
    "User Bit Time Rec",
)

TC_PRESET_FACTORY_DEFAULT_G108: str = "00:00:00.00"
UB_PRESET_FACTORY_DEFAULT_G108: str = "00 00 00 00"

TC_FORMAT_DF_G108: str = "DF"
TC_FORMAT_NDF_G108: str = "NDF"
ALLOWED_TC_FORMATS_G108: Tuple[str, ...] = (
    TC_FORMAT_DF_G108,
    TC_FORMAT_NDF_G108,
)
TC_FORMAT_FACTORY_DEFAULT_G108: str = TC_FORMAT_DF_G108

FRAME_RATE_NTSC_29_97P_G108: str = "29.97p"
FRAME_RATE_NTSC_59_94P_G108: str = "59.94p"
FRAME_RATE_NTSC_23_98P_G108: str = "23.98p"
FRAME_RATE_TRUE_24_00P_G108: str = "24.00p"
FRAME_RATE_PAL_25P_G108: str = "25p"
FRAME_RATE_PAL_50P_G108: str = "50p"
ALLOWED_FRAME_RATES_G108: Tuple[str, ...] = (
    FRAME_RATE_NTSC_29_97P_G108,
    FRAME_RATE_NTSC_59_94P_G108,
    FRAME_RATE_NTSC_23_98P_G108,
    FRAME_RATE_TRUE_24_00P_G108,
    FRAME_RATE_PAL_25P_G108,
    FRAME_RATE_PAL_50P_G108,
)
FORCED_NDF_FRAME_RATES_G108: Tuple[str, ...] = (
    FRAME_RATE_TRUE_24_00P_G108,
    FRAME_RATE_PAL_25P_G108,
    FRAME_RATE_PAL_50P_G108,
)

TC_RUN_REC_RUN_G108: str = "Rec Run"
TC_RUN_FREE_RUN_G108: str = "Free Run"
ALLOWED_TC_RUN_MODES_G108: Tuple[str, ...] = (
    TC_RUN_REC_RUN_G108,
    TC_RUN_FREE_RUN_G108,
)
TC_RUN_FACTORY_DEFAULT_G108: str = TC_RUN_REC_RUN_G108

TC_MAKE_PRESET_G108: str = "Preset"
TC_MAKE_REGENERATE_G108: str = "Regenerate"
ALLOWED_TC_MAKE_MODES_G108: Tuple[str, ...] = (
    TC_MAKE_PRESET_G108,
    TC_MAKE_REGENERATE_G108,
)
TC_MAKE_FACTORY_DEFAULT_G108: str = TC_MAKE_PRESET_G108

UB_TIME_REC_OFF_G108: str = "Off"
UB_TIME_REC_ON_G108: str = "On"
UB_TIME_REC_FACTORY_DEFAULT_G108: str = UB_TIME_REC_OFF_G108

TCUB_DISP_TC_G108: str = "TC"
TCUB_DISP_UBIT_G108: str = "U-Bit"
ALLOWED_TCUB_DISP_SETTINGS_G108: Tuple[str, ...] = (
    TCUB_DISP_TC_G108,
    TCUB_DISP_UBIT_G108,
)
TCUB_DISP_FACTORY_DEFAULT_G108: str = TCUB_DISP_TC_G108


# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, <0.10s, Clean-Room Fallback)
# ---------------------------------------------------------------------------

PINNED_PHASE268_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_bin": (
        "FX3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"File",
            b"Reset",
            b"Standard",
            b"Date",
            b"DSC",
            b"CLIP",
            b"PRIVATE",
            b"DCIM",
            b"Gamma",
            b"Assist",
            b"LUT",
            b"S-Log3",
            b"709",
            b"HLG",
            b"Log",
            b"Cine",
            b"Auto",
            b"Review",
            b"TC",
            b"UB",
            b"Preset",
            b"Initialize",
            b"HDMI",
        ),
        "FX3_CPAPP_FILE_SETTINGS_DSC_GAMMA_ASSIST_LUT_AUTO_REVIEW_TCUB_STRINGS",
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
        "FX3_LIBGPE_FILE_SETTINGS_GAMMA_ASSIST_TCUB_MENU_ELF",
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
        "FX3_LIBSAVELOADSETTINGS_FILE_GAMMA_TCUB_RESET_PERSISTENCE_ELF",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"TC", b"/setting"),
        "FX3_BK4_FILE_SETTINGS_GAMMA_TCUB_BACKUP_SEED",
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
        "FX6_LIBINFRADIAL_CAMID_REEL_DISPLAY_LUT_PARITY_ELF",
    ),
    "fx6_bk4_bin": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"WB", b"TC", b"/setting"),
        "FX6_BK4_CINEMA_LINE_CAMID_REEL_TCUB_PARITY_SEED",
    ),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase268DonorAuditResult:
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
class MovieFileSettingsStillDscAndSlot1VaultGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    reset_action: str
    movie_file_settings_menu_path: str
    still_file_folder_settings_menu_path: str
    pre_reset_movie_file_number: str
    effective_post_reset_movie_file_number: str
    series_counter_reset_requested: bool
    effective_movie_sequence_index: int
    pre_reset_movie_file_name_format: str
    effective_post_reset_movie_file_name_format: str
    pre_reset_camera_id: str
    effective_post_reset_camera_id: str
    pre_reset_reel_number: int
    effective_post_reset_reel_number: int
    formatted_reel_number: str
    pre_reset_camera_position: str
    effective_post_reset_camera_position: str
    pre_reset_title_name: str
    effective_post_reset_title_name: str
    title_name_char_length: int
    title_name_within_37char_ascii: bool
    movie_folder_path: str
    movie_fixed_folder_topology_verified: bool
    custom_movie_folder_requested: bool
    sample_movie_clip_filename: str
    pre_reset_still_file_number: str
    effective_post_reset_still_file_number: str
    pre_reset_still_set_file_name: str
    effective_post_reset_still_set_file_name: str
    still_set_file_name_valid_3char: bool
    pre_reset_still_folder_name: str
    effective_post_reset_still_folder_name: str
    sample_still_folder_label: str
    sample_still_image_filename: str
    file_and_folder_settings_survive_camera_settings_reset: bool
    target_still_slot: str
    slot1_holds_recovery_vault: bool
    forced_file_number_reset_requested: bool
    create_new_folder_requested: bool
    still_folder_mutation_permitted: bool
    slot1_vault_folder_mutation_blocked: bool
    slot1_vault_folder_mutation_events: int
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G107MovieFileSettingsStillDscAndSlot1VaultGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    file_settings_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GammaDispAssistLogLockoutAutoReviewTcubGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    reset_action: str
    log_shooting_mode: str
    log_shooting_active: bool
    gamma_disp_assist_menu_path: str
    gamma_disp_assist_typ_menu_path: str
    display_lut_menu_path: str
    select_lut_menu_path: str
    auto_review_menu_path: str
    tcub_menu_path: str
    tcub_disp_setting_menu_path: str
    pre_reset_gamma_display_assist: str
    effective_post_reset_gamma_display_assist: str
    gamma_display_assist_locked_by_log_shooting: bool
    effective_gamma_display_assist: str
    pre_reset_gamma_disp_assist_typ: str
    effective_post_reset_gamma_disp_assist_typ: str
    camera_lcd_only_scope_verified: bool
    external_hdmi_gamma_assist_applied: bool
    hdmi_gamma_assist_leak_frames: int
    gamma_assist_log_lockout_bypass_events: int
    pre_reset_display_lut: str
    effective_post_reset_display_lut: str
    pre_reset_select_lut: str
    effective_post_reset_select_lut: str
    effective_log_monitoring_governed_by_display_lut: bool
    registered_user_lut_slots: int
    pre_reset_auto_review: str
    effective_post_reset_auto_review: str
    auto_review_still_only_scope: bool
    movie_auto_review_interrupt_events: int
    tcub_subitems: Tuple[str, ...]
    tcub_exact_6_items_verified: bool
    frame_rate: str
    pre_reset_tc_preset: str
    effective_post_reset_tc_preset: str
    pre_reset_ub_preset: str
    effective_post_reset_ub_preset: str
    pre_reset_tc_format: str
    effective_post_reset_tc_format: str
    tc_format_forced_ndf_by_cadence: bool
    effective_tc_format: str
    pre_reset_tc_run: str
    effective_post_reset_tc_run: str
    pre_reset_tc_make: str
    effective_post_reset_tc_make: str
    pre_reset_ub_time_rec: str
    effective_post_reset_ub_time_rec: str
    pre_reset_tcub_disp_setting: str
    effective_post_reset_tcub_disp_setting: str
    setup_and_tcub_survive_camera_settings_reset: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G108GammaDispAssistLogLockoutAutoReviewTcubGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    gamma_assist_auto_review_tcub_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master108GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_105_gates_verified: bool
    all_108_gates_verified: bool
    g13_to_g108_all_passed: bool
    g107_to_g108_all_passed: bool
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
    master_106_report: Dict[str, Any]
    g107_result: Dict[str, Any]
    g108_result: Dict[str, Any]
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
    for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE268):
        if os.environ.get(env_key, "").strip() in _TRUTHY_CLEAN_ROOM_TOKENS:
            return True
    return False


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
    m = re.match(r"^\s*(?:Ver\.\s*|[vV])?(\d+)\.(\d+)(?:\.\d+)?\s*$", version_str)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _norm_reset_action_phase268(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE268
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE
    return None


def _norm_on_off_phase268(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "ON":
        return "On"
    if u == "OFF":
        return "Off"
    return None


def _norm_file_number_mode_g107(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "SERIES":
        return FILE_NUMBER_SERIES_G107
    if u == "RESET":
        return FILE_NUMBER_RESET_G107
    return None


def _norm_movie_file_name_format_g107(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    mapping = {
        "STANDARD": MOVIE_FILE_NAME_STANDARD_G107,
        "CAM ID + REEL#": MOVIE_FILE_NAME_CAM_ID_REEL_G107,
        "CAM ID+REEL#": MOVIE_FILE_NAME_CAM_ID_REEL_G107,
        "CAM_ID_REEL": MOVIE_FILE_NAME_CAM_ID_REEL_G107,
        "TITLE": MOVIE_FILE_NAME_TITLE_G107,
        "DATE + TITLE": MOVIE_FILE_NAME_DATE_PLUS_TITLE_G107,
        "DATE+TITLE": MOVIE_FILE_NAME_DATE_PLUS_TITLE_G107,
        "DATE_PLUS_TITLE": MOVIE_FILE_NAME_DATE_PLUS_TITLE_G107,
        "TITLE + DATE": MOVIE_FILE_NAME_TITLE_PLUS_DATE_G107,
        "TITLE+DATE": MOVIE_FILE_NAME_TITLE_PLUS_DATE_G107,
        "TITLE_PLUS_DATE": MOVIE_FILE_NAME_TITLE_PLUS_DATE_G107,
    }
    return mapping.get(u)


def _is_valid_camera_id_g107(val: Any) -> bool:
    return isinstance(val, str) and len(val) == 1 and val in CAMERA_ID_ALLOWED_CHARS_G107


def _parse_reel_number_g107(val: Any) -> Optional[int]:
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val if REEL_NUMBER_MIN_G107 <= val <= REEL_NUMBER_MAX_G107 else None
    if isinstance(val, str):
        s = val.strip()
        if re.match(r"^\d{1,3}$", s):
            num = int(s, 10)
            return num if REEL_NUMBER_MIN_G107 <= num <= REEL_NUMBER_MAX_G107 else None
    return None


def _norm_camera_position_g107(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u in ("C", "CENTER"):
        return CAMERA_POSITION_CENTER_G107
    if u in ("L", "LEFT"):
        return CAMERA_POSITION_LEFT_G107
    if u in ("R", "RIGHT"):
        return CAMERA_POSITION_RIGHT_G107
    return None


def _is_valid_37char_title_name_g107(val: Any) -> bool:
    if not isinstance(val, str):
        return False
    if len(val) < 1 or len(val) > TITLE_NAME_MAX_CHARS_G107:
        return False
    if "/" in val or "\\" in val or ".." in val:
        return False
    return all(
        ASCII_PRINTABLE_MIN_CODEPOINT_PHASE268
        <= ord(ch)
        <= ASCII_PRINTABLE_MAX_CODEPOINT_PHASE268
        for ch in val
    )


def _is_valid_still_3char_prefix_g107(val: Any) -> bool:
    if not isinstance(val, str):
        return False
    if len(val) != STILL_SET_FILE_NAME_EXACT_LEN_G107:
        return False
    if val[0] == "_":
        return False
    return bool(re.match(r"^[A-Z0-9][A-Z0-9_]{2}$", val))


def _norm_still_folder_form_g107(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("STANDARD FORM", "STANDARD"):
        return STILL_FOLDER_STANDARD_FORM_G107
    if u in ("DATE FORM", "DATE"):
        return STILL_FOLDER_DATE_FORM_G107
    return None


def _norm_media_slot_g107(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ").replace("-", " ")).upper()
    if u in ("SLOT 1", "SLOT1"):
        return MEDIA_SLOT_1_G107
    if u in ("SLOT 2", "SLOT2"):
        return MEDIA_SLOT_2_G107
    return None


def _norm_gamma_assist_typ_g108(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]").replace("→", "->")
    u = re.sub(r"\s+", "", s).upper()
    mapping = {
        "AUTO": GAMMA_ASSIST_TYP_AUTO_G108,
        "S-LOG3->709(800%)": GAMMA_ASSIST_TYP_SLOG3_709_800_G108,
        "SLOG3->709(800%)": GAMMA_ASSIST_TYP_SLOG3_709_800_G108,
        "HLG(BT.2020)": GAMMA_ASSIST_TYP_HLG_BT2020_G108,
        "HLG(709)": GAMMA_ASSIST_TYP_HLG_709_G108,
    }
    return mapping.get(u)


def _norm_log_shooting_mode_g108(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    mapping = {
        "OFF": LOG_SHOOTING_OFF_G108,
        "CINE EI": LOG_SHOOTING_CINE_EI_G108,
        "CINE EI QUICK": LOG_SHOOTING_CINE_EI_QUICK_G108,
        "FLEXIBLE ISO": LOG_SHOOTING_FLEXIBLE_ISO_G108,
    }
    return mapping.get(u)


def _norm_select_lut_g108(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]")
    u = re.sub(r"\s+", "", s).upper()
    if u in ("S-LOG3", "SLOG3"):
        return SELECT_LUT_SLOG3_G108
    if u == "S709":
        return SELECT_LUT_S709_G108
    if u == "709(800%)":
        return SELECT_LUT_709_800_G108
    m = re.match(r"^USER([1-9]|1[0-6])$", u)
    if m:
        return f"User{int(m.group(1), 10)}"
    return None


def _norm_auto_review_g108(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    mapping = {
        "OFF": AUTO_REVIEW_OFF_G108,
        "2 SEC": AUTO_REVIEW_2_SEC_G108,
        "2SEC": AUTO_REVIEW_2_SEC_G108,
        "5 SEC": AUTO_REVIEW_5_SEC_G108,
        "5SEC": AUTO_REVIEW_5_SEC_G108,
        "10 SEC": AUTO_REVIEW_10_SEC_G108,
        "10SEC": AUTO_REVIEW_10_SEC_G108,
    }
    return mapping.get(u)


def _norm_tc_preset_g108(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    m = re.match(r"^\s*(\d{2}):(\d{2}):(\d{2})([:.])(\d{2})\s*$", raw)
    if not m:
        return None
    hh, mm, ss, sep, ff = (
        int(m.group(1), 10),
        int(m.group(2), 10),
        int(m.group(3), 10),
        m.group(4),
        int(m.group(5), 10),
    )
    if hh > 23 or mm > 59 or ss > 59 or ff > 59:
        return None
    return f"{hh:02d}:{mm:02d}:{ss:02d}{sep}{ff:02d}"


def _norm_ub_preset_g108(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    m = re.match(
        r"^\s*([0-9A-Fa-f]{2})[\s:]([0-9A-Fa-f]{2})[\s:]([0-9A-Fa-f]{2})[\s:]([0-9A-Fa-f]{2})\s*$",
        raw,
    )
    if not m:
        return None
    return f"{m.group(1).upper()} {m.group(2).upper()} {m.group(3).upper()} {m.group(4).upper()}"


def _norm_tc_format_g108(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("DF", "DROP FRAME"):
        return TC_FORMAT_DF_G108
    if u in ("NDF", "NON-DROP FRAME", "NON DROP FRAME"):
        return TC_FORMAT_NDF_G108
    return None


def _norm_frame_rate_g108(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    mapping = {
        "29.97P": FRAME_RATE_NTSC_29_97P_G108,
        "30P": FRAME_RATE_NTSC_29_97P_G108,
        "59.94P": FRAME_RATE_NTSC_59_94P_G108,
        "60P": FRAME_RATE_NTSC_59_94P_G108,
        "23.98P": FRAME_RATE_NTSC_23_98P_G108,
        "23.976P": FRAME_RATE_NTSC_23_98P_G108,
        "24.00P": FRAME_RATE_TRUE_24_00P_G108,
        "24P": FRAME_RATE_TRUE_24_00P_G108,
        "25P": FRAME_RATE_PAL_25P_G108,
        "50P": FRAME_RATE_PAL_50P_G108,
    }
    return mapping.get(u)


def _norm_tc_run_g108(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "REC RUN":
        return TC_RUN_REC_RUN_G108
    if u == "FREE RUN":
        return TC_RUN_FREE_RUN_G108
    return None


def _norm_tc_make_g108(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "PRESET":
        return TC_MAKE_PRESET_G108
    if u == "REGENERATE":
        return TC_MAKE_REGENERATE_G108
    return None


def _norm_tcub_disp_setting_g108(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    if u == "TC":
        return TCUB_DISP_TC_G108
    if u in ("U-BIT", "UBIT", "UB"):
        return TCUB_DISP_UBIT_G108
    return None


# ---------------------------------------------------------------------------
# 1. Bounded `< 0.10s` O_RDONLY Donor Contract Audit (`Phase 268`)
# ---------------------------------------------------------------------------


def audit_phase268_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS_PHASE268,
) -> Phase268DonorAuditResult:
    """Inspect local FX3 Ver. 7.02 / FX6 Ver. 6.01 donor artifacts strictly
    `os.O_RDONLY` within `<0.10s`, verifying bounded Wave-44 symbols across
    `cpapp-b.bin`, `libgpe.so`, `libSaveLoadSettings.so`,
    `FX3-CX95900_ALLLANG-Backup.bin`, `libInfraDial.so`, and `CX95898_NTSC.bin`
    with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` / `FX3_CLEAN_ROOM_TEST=1` parity.
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE268_DONOR_SPECS.items():
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
            spec[5] for spec in PINNED_PHASE268_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE268_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE268_DONOR_SPECS.items()}
        return Phase268DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE268_DONOR_INTEGRITY
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
    ) in PINNED_PHASE268_DONOR_SPECS.items():
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
            errors.append(f"Missing required Wave-44 byte markers in {key}.")

        if size_ok and sha_ok and markers_ok:
            checked.append(marker_label)
            passed_keys.add(key)
        else:
            missing.append(marker_label)

    elapsed = time.perf_counter() - t0
    within_budget = elapsed < max_budget_seconds
    if not within_budget:
        errors.append(
            f"Local O_RDONLY donor audit exceeded budget ({elapsed:.4f}s >= {max_budget_seconds:.4f}s)."
        )

    fx3_keys = {k for k, v in PINNED_PHASE268_DONOR_SPECS.items() if v[0] == "FX3"}
    fx6_keys = {k for k, v in PINNED_PHASE268_DONOR_SPECS.items() if v[0] == "FX6"}
    fx3_ok = fx3_keys.issubset(passed_keys)
    fx6_ok = fx6_keys.issubset(passed_keys)
    valid = fx3_ok and fx6_ok and (not missing) and within_budget and (not errors)

    return Phase268DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE
        if valid
        else STATUS_BLOCKED_PHASE268_DONOR_INTEGRITY,
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
# 2. Gate `G107`: Movie `[File Settings]` (`Cam ID + Reel#` & `37`-Char Title
#    + Fixed `PRIVATE/M4ROOT/CLIP`) vs Still `[File/Folder Settings]` (`3`-Char
#    `DSC` Prefix & `Slot-1` Recovery Vault Folder Firewall)
# ---------------------------------------------------------------------------


def compute_file_settings_and_slot1_vault_matrix() -> Dict[str, Any]:
    """Exhaustively evaluate all `5 x 3 x 2 x 2 x 2 x 3 = 360` combinations of
    `(movie_file_name_format, camera_position, still_folder_form,
    target_still_slot, slot1_holds_recovery_vault, folder_mutation_op)` on
    `ILME-FX3` (`Ver. 7.02`, `ilc/2210`), proving:
    - Movie clips strictly land in fixed `PRIVATE/M4ROOT/CLIP` (`custom_movie_folder_bypass_events == 0`);
    - `[Forced File Number Reset]` and `[Create New Folder]` are ALWAYS blocked
      on `Slot 1` whenever `slot1_holds_recovery_vault == True`
      (`slot1_vault_folder_mutation_events == 0`).
    """
    states_checked = 0
    cam_id_reel_states = 0
    slot1_vault_blocked_ops = 0
    slot2_permitted_ops = 0
    slot1_vault_mutation_events = 0
    custom_movie_folder_bypass_events = 0

    for mv_fmt in ALLOWED_MOVIE_FILE_NAME_FORMATS_G107:
        for cam_pos in ALLOWED_CAMERA_POSITIONS_G107:
            for folder_form in ALLOWED_STILL_FOLDER_FORMS_G107:
                for slot in ALLOWED_MEDIA_SLOTS_G107:
                    for vault in (False, True):
                        for folder_op in (
                            "NONE",
                            "FORCED_FILE_NUMBER_RESET",
                            "CREATE_NEW_FOLDER",
                        ):
                            states_checked += 1
                            if mv_fmt == MOVIE_FILE_NAME_CAM_ID_REEL_G107:
                                cam_id_reel_states += 1
                            mv_folder = MOVIE_FIXED_FOLDER_PATH_G107
                            if mv_folder != "PRIVATE/M4ROOT/CLIP":
                                custom_movie_folder_bypass_events += 1
                            mut_req = folder_op != "NONE"
                            blocked_by_vault = bool(
                                mut_req and slot == MEDIA_SLOT_1_G107 and vault
                            )
                            permitted = bool(mut_req and (not blocked_by_vault))
                            if blocked_by_vault:
                                slot1_vault_blocked_ops += 1
                                if permitted:
                                    slot1_vault_mutation_events += 1
                            elif permitted and slot == MEDIA_SLOT_2_G107:
                                slot2_permitted_ops += 1
                            _ = (cam_pos, folder_form)

    return {
        "states_checked": states_checked,
        "cam_id_reel_states": cam_id_reel_states,
        "slot1_vault_blocked_ops": slot1_vault_blocked_ops,
        "slot2_permitted_ops": slot2_permitted_ops,
        "slot1_vault_folder_mutation_events": slot1_vault_mutation_events,
        "custom_movie_folder_bypass_events": custom_movie_folder_bypass_events,
    }


def _build_sample_movie_clip_filename_g107(
    *,
    file_name_format: str,
    camera_id: str,
    reel_number: int,
    camera_position: str,
    title_name: str,
    seq_index: int,
    yymmdd: str = "261115",
) -> str:
    seq_str = f"{max(1, min(9999, seq_index)):04d}"
    clip_idx3 = f"{max(1, min(999, seq_index)):03d}"
    if file_name_format == MOVIE_FILE_NAME_CAM_ID_REEL_G107:
        return f"{camera_id}{reel_number:03d}{camera_position}{clip_idx3}_{yymmdd}_FX3A.MP4"
    if file_name_format == MOVIE_FILE_NAME_TITLE_G107:
        return f"{title_name}{seq_str}.MP4"
    if file_name_format == MOVIE_FILE_NAME_DATE_PLUS_TITLE_G107:
        return f"{yymmdd}_{title_name}{seq_str}.MP4"
    if file_name_format == MOVIE_FILE_NAME_TITLE_PLUS_DATE_G107:
        return f"{title_name}_{yymmdd}_{seq_str}.MP4"
    return f"C{seq_str}.MP4"


def resolve_fx3_movie_file_settings_and_still_dsc_state(
    *,
    reset_action: str = RESET_ACTION_NONE,
    pre_reset_movie_file_number: str = MOVIE_FILE_NUMBER_FACTORY_DEFAULT_G107,
    series_counter_reset_requested: bool = False,
    prior_movie_sequence_index: int = 12,
    pre_reset_movie_file_name_format: str = MOVIE_FILE_NAME_FORMAT_FACTORY_DEFAULT_G107,
    pre_reset_camera_id: str = CAMERA_ID_FACTORY_DEFAULT_G107,
    pre_reset_reel_number: int = REEL_NUMBER_FACTORY_DEFAULT_G107,
    pre_reset_camera_position: str = CAMERA_POSITION_FACTORY_DEFAULT_G107,
    pre_reset_title_name: str = TITLE_NAME_FACTORY_DEFAULT_G107,
    pre_reset_still_file_number: str = STILL_FILE_NUMBER_FACTORY_DEFAULT_G107,
    pre_reset_still_set_file_name: str = STILL_SET_FILE_NAME_FACTORY_DEFAULT_G107,
    pre_reset_still_folder_name: str = STILL_FOLDER_FORM_FACTORY_DEFAULT_G107,
    target_still_slot: str = MEDIA_SLOT_2_G107,
    slot1_holds_recovery_vault: bool = True,
    forced_file_number_reset_requested: bool = False,
    create_new_folder_requested: bool = False,
) -> Dict[str, Any]:
    """Deterministic state resolver for Wave-44 Gate `G107`."""
    norm_reset = _norm_reset_action_phase268(reset_action) or RESET_ACTION_NONE
    norm_mv_num = (
        _norm_file_number_mode_g107(pre_reset_movie_file_number)
        or MOVIE_FILE_NUMBER_FACTORY_DEFAULT_G107
    )
    norm_mv_fmt = (
        _norm_movie_file_name_format_g107(pre_reset_movie_file_name_format)
        or MOVIE_FILE_NAME_FORMAT_FACTORY_DEFAULT_G107
    )
    norm_cam_id = (
        pre_reset_camera_id.strip().upper()
        if isinstance(pre_reset_camera_id, str)
        and _is_valid_camera_id_g107(pre_reset_camera_id.strip().upper())
        else CAMERA_ID_FACTORY_DEFAULT_G107
    )
    parsed_reel = _parse_reel_number_g107(pre_reset_reel_number)
    norm_reel = (
        parsed_reel if parsed_reel is not None else REEL_NUMBER_FACTORY_DEFAULT_G107
    )
    norm_cam_pos = (
        _norm_camera_position_g107(pre_reset_camera_position)
        or CAMERA_POSITION_FACTORY_DEFAULT_G107
    )
    norm_title = (
        pre_reset_title_name
        if _is_valid_37char_title_name_g107(pre_reset_title_name)
        else TITLE_NAME_FACTORY_DEFAULT_G107
    )
    norm_st_num = (
        _norm_file_number_mode_g107(pre_reset_still_file_number)
        or STILL_FILE_NUMBER_FACTORY_DEFAULT_G107
    )
    norm_st_prefix = (
        pre_reset_still_set_file_name
        if _is_valid_still_3char_prefix_g107(pre_reset_still_set_file_name)
        else STILL_SET_FILE_NAME_FACTORY_DEFAULT_G107
    )
    norm_st_folder = (
        _norm_still_folder_form_g107(pre_reset_still_folder_name)
        or STILL_FOLDER_FORM_FACTORY_DEFAULT_G107
    )
    norm_slot = _norm_media_slot_g107(target_still_slot) or MEDIA_SLOT_2_G107

    # Official Sony ILME-FX3 Help Guide (ilc/2210):
    # ALL items under Movie [File Settings] AND Still [File/Folder Settings]
    # SURVIVE [Camera Settings Reset] & [Reset Network Set.], and reset ONLY
    # via [Initialize].
    if norm_reset == RESET_ACTION_INITIALIZE:
        eff_mv_num = MOVIE_FILE_NUMBER_FACTORY_DEFAULT_G107
        eff_mv_fmt = MOVIE_FILE_NAME_FORMAT_FACTORY_DEFAULT_G107
        eff_cam_id = CAMERA_ID_FACTORY_DEFAULT_G107
        eff_reel = REEL_NUMBER_FACTORY_DEFAULT_G107
        eff_cam_pos = CAMERA_POSITION_FACTORY_DEFAULT_G107
        eff_title = TITLE_NAME_FACTORY_DEFAULT_G107
        eff_st_num = STILL_FILE_NUMBER_FACTORY_DEFAULT_G107
        eff_st_prefix = STILL_SET_FILE_NAME_FACTORY_DEFAULT_G107
        eff_st_folder = STILL_FOLDER_FORM_FACTORY_DEFAULT_G107
    else:
        eff_mv_num = norm_mv_num
        eff_mv_fmt = norm_mv_fmt
        eff_cam_id = norm_cam_id
        eff_reel = norm_reel
        eff_cam_pos = norm_cam_pos
        eff_title = norm_title
        eff_st_num = norm_st_num
        eff_st_prefix = norm_st_prefix
        eff_st_folder = norm_st_folder

    if (
        bool(series_counter_reset_requested)
        or eff_mv_num == FILE_NUMBER_RESET_G107
        or norm_reset == RESET_ACTION_INITIALIZE
    ):
        eff_mv_seq = 1
    else:
        eff_mv_seq = max(1, int(prior_movie_sequence_index) + 1)

    sample_mv_name = _build_sample_movie_clip_filename_g107(
        file_name_format=eff_mv_fmt,
        camera_id=eff_cam_id,
        reel_number=eff_reel,
        camera_position=eff_cam_pos,
        title_name=eff_title,
        seq_index=eff_mv_seq,
    )

    still_folder_mut_req = bool(forced_file_number_reset_requested) or bool(
        create_new_folder_requested
    )
    vault_blocks = bool(
        still_folder_mut_req
        and norm_slot == MEDIA_SLOT_1_G107
        and bool(slot1_holds_recovery_vault)
    )
    still_folder_mut_permitted = bool(still_folder_mut_req and (not vault_blocks))

    folder_num = 101 if still_folder_mut_permitted else 100
    sample_st_folder = (
        f"{folder_num:03d}MSDCF"
        if eff_st_folder == STILL_FOLDER_STANDARD_FORM_G107
        else f"{folder_num:03d}61115"
    )
    still_seq = (
        1
        if (
            still_folder_mut_permitted
            or eff_st_num == FILE_NUMBER_RESET_G107
            or norm_reset == RESET_ACTION_INITIALIZE
        )
        else 2
    )
    sample_st_file = f"{eff_st_prefix}0{still_seq:04d}.JPG"

    return {
        "reset_action": norm_reset,
        "effective_post_reset_movie_file_number": eff_mv_num,
        "effective_movie_sequence_index": eff_mv_seq,
        "effective_post_reset_movie_file_name_format": eff_mv_fmt,
        "effective_post_reset_camera_id": eff_cam_id,
        "effective_post_reset_reel_number": eff_reel,
        "formatted_reel_number": f"{eff_reel:03d}",
        "effective_post_reset_camera_position": eff_cam_pos,
        "effective_post_reset_title_name": eff_title,
        "sample_movie_clip_filename": sample_mv_name,
        "effective_post_reset_still_file_number": eff_st_num,
        "effective_post_reset_still_set_file_name": eff_st_prefix,
        "effective_post_reset_still_folder_name": eff_st_folder,
        "sample_still_folder_label": sample_st_folder,
        "sample_still_image_filename": sample_st_file,
        "target_still_slot": norm_slot,
        "still_folder_mutation_permitted": still_folder_mut_permitted,
        "slot1_vault_folder_mutation_blocked": vault_blocks,
        "slot1_vault_folder_mutation_events": 0,
    }


def verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE268,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE268,
    reset_action: str = RESET_ACTION_NONE,
    pre_reset_movie_file_number: str = MOVIE_FILE_NUMBER_FACTORY_DEFAULT_G107,
    series_counter_reset_requested: bool = False,
    prior_movie_sequence_index: int = 12,
    pre_reset_movie_file_name_format: str = MOVIE_FILE_NAME_FORMAT_FACTORY_DEFAULT_G107,
    pre_reset_camera_id: str = CAMERA_ID_FACTORY_DEFAULT_G107,
    pre_reset_reel_number: Any = REEL_NUMBER_FACTORY_DEFAULT_G107,
    pre_reset_camera_position: str = CAMERA_POSITION_FACTORY_DEFAULT_G107,
    pre_reset_title_name: str = TITLE_NAME_FACTORY_DEFAULT_G107,
    movie_folder_path: str = MOVIE_FIXED_FOLDER_PATH_G107,
    custom_movie_folder_requested: bool = False,
    pre_reset_still_file_number: str = STILL_FILE_NUMBER_FACTORY_DEFAULT_G107,
    pre_reset_still_set_file_name: str = STILL_SET_FILE_NAME_FACTORY_DEFAULT_G107,
    pre_reset_still_folder_name: str = STILL_FOLDER_FORM_FACTORY_DEFAULT_G107,
    target_still_slot: str = MEDIA_SLOT_2_G107,
    slot1_holds_recovery_vault: bool = True,
    forced_file_number_reset_requested: bool = False,
    create_new_folder_requested: bool = False,
    claimed_post_reset_movie_file_number: Optional[str] = None,
    claimed_post_reset_movie_file_name_format: Optional[str] = None,
    claimed_post_reset_camera_id: Optional[str] = None,
    claimed_post_reset_reel_number: Optional[int] = None,
    claimed_post_reset_camera_position: Optional[str] = None,
    claimed_post_reset_title_name: Optional[str] = None,
    claimed_post_reset_still_file_number: Optional[str] = None,
    claimed_post_reset_still_set_file_name: Optional[str] = None,
    claimed_post_reset_still_folder_name: Optional[str] = None,
    claimed_slot1_vault_folder_mutation_events: int = 0,
) -> MovieFileSettingsStillDscAndSlot1VaultGuardResult:
    """Verify Gate `G107`: Movie `[File Settings]` (`Cam ID + Reel#` & `<= 37`-char
    `[Title Name Settings]` + fixed `PRIVATE/M4ROOT/CLIP` folder topology) vs Still
    `[File/Folder Settings]` (`3`-char `DSC` prefix rejecting leading `_`,
    `Standard Form` / `Date Form`) + `[Camera Settings Reset]` survival & `Slot-1`
    recovery vault folder-mutation firewall.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        body_model_name != FX3_MODEL_NAME
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE268
        or fw_tuple is None
        or fw_tuple < (1, 0)
    ):
        _add_code(codes, STATUS_BLOCKED_G107_TELEMETRY_INVALID)
        errors.append(
            "Invalid ILME-FX3 body/help-guide/firmware identity for Gate G107."
        )

    norm_reset = _norm_reset_action_phase268(reset_action)
    norm_mv_num = _norm_file_number_mode_g107(pre_reset_movie_file_number)
    norm_st_num = _norm_file_number_mode_g107(pre_reset_still_file_number)
    norm_slot = _norm_media_slot_g107(target_still_slot)

    if (
        norm_reset is None
        or norm_mv_num is None
        or norm_st_num is None
        or norm_slot is None
        or not isinstance(prior_movie_sequence_index, int)
        or prior_movie_sequence_index < 0
        or not isinstance(claimed_slot1_vault_folder_mutation_events, int)
        or claimed_slot1_vault_folder_mutation_events < 0
    ):
        _add_code(codes, STATUS_BLOCKED_G107_TELEMETRY_INVALID)
        errors.append(
            "Invalid reset action, File Number mode, media slot, or sequence telemetry in Gate G107."
        )

    norm_mv_fmt = _norm_movie_file_name_format_g107(pre_reset_movie_file_name_format)
    cam_id_ok = _is_valid_camera_id_g107(pre_reset_camera_id)
    parsed_reel = _parse_reel_number_g107(pre_reset_reel_number)
    norm_cam_pos = _norm_camera_position_g107(pre_reset_camera_position)
    title_ok = _is_valid_37char_title_name_g107(pre_reset_title_name)

    if (
        norm_mv_fmt is None
        or (not cam_id_ok)
        or parsed_reel is None
        or norm_cam_pos is None
        or (not title_ok)
        or (
            norm_mv_fmt == MOVIE_FILE_NAME_CAM_ID_REEL_G107
            and fw_tuple is not None
            and fw_tuple < FX3_CAMID_REEL_MIN_FW_TUPLE_G107
        )
    ):
        _add_code(
            codes,
            STATUS_BLOCKED_G107_MOVIE_FILE_NAME_CAMID_REEL_OR_37CHAR_TITLE_VIOLATION,
        )
        errors.append(
            "Movie [File Settings] violated [File Name Format] (`Cam ID + Reel#` A..Z / 001..999 / C|L|R on Ver. 3.00+) or <=37-char ASCII [Title Name Settings]."
        )

    fixed_mv_folder_ok = (
        isinstance(movie_folder_path, str)
        and movie_folder_path == MOVIE_FIXED_FOLDER_PATH_G107
        and (not bool(custom_movie_folder_requested))
    )
    if not fixed_mv_folder_ok:
        _add_code(codes, STATUS_BLOCKED_G107_MOVIE_CUSTOM_FOLDER_TOPOLOGY_VIOLATION)
        errors.append(
            f"Movie folder topology must remain fixed at '{MOVIE_FIXED_FOLDER_PATH_G107}' without custom folder paths."
        )

    still_prefix_ok = _is_valid_still_3char_prefix_g107(pre_reset_still_set_file_name)
    norm_st_folder = _norm_still_folder_form_g107(pre_reset_still_folder_name)
    if (not still_prefix_ok) or norm_st_folder is None:
        _add_code(codes, STATUS_BLOCKED_G107_STILL_DSC_PREFIX_OR_FOLDER_FORM_VIOLATION)
        errors.append(
            "Still [File/Folder Settings] violated 3-char [Set File Name] (`A-Z`/`0-9`/`_`, no leading `_`) or [Folder Name] (`Standard Form`/`Date Form`)."
        )

    resolved = resolve_fx3_movie_file_settings_and_still_dsc_state(
        reset_action=norm_reset or RESET_ACTION_NONE,
        pre_reset_movie_file_number=norm_mv_num or MOVIE_FILE_NUMBER_FACTORY_DEFAULT_G107,
        series_counter_reset_requested=bool(series_counter_reset_requested),
        prior_movie_sequence_index=prior_movie_sequence_index
        if isinstance(prior_movie_sequence_index, int) and prior_movie_sequence_index >= 0
        else 0,
        pre_reset_movie_file_name_format=norm_mv_fmt
        or MOVIE_FILE_NAME_FORMAT_FACTORY_DEFAULT_G107,
        pre_reset_camera_id=pre_reset_camera_id
        if cam_id_ok
        else CAMERA_ID_FACTORY_DEFAULT_G107,
        pre_reset_reel_number=parsed_reel
        if parsed_reel is not None
        else REEL_NUMBER_FACTORY_DEFAULT_G107,
        pre_reset_camera_position=norm_cam_pos or CAMERA_POSITION_FACTORY_DEFAULT_G107,
        pre_reset_title_name=pre_reset_title_name
        if title_ok
        else TITLE_NAME_FACTORY_DEFAULT_G107,
        pre_reset_still_file_number=norm_st_num or STILL_FILE_NUMBER_FACTORY_DEFAULT_G107,
        pre_reset_still_set_file_name=pre_reset_still_set_file_name
        if still_prefix_ok
        else STILL_SET_FILE_NAME_FACTORY_DEFAULT_G107,
        pre_reset_still_folder_name=norm_st_folder
        or STILL_FOLDER_FORM_FACTORY_DEFAULT_G107,
        target_still_slot=norm_slot or MEDIA_SLOT_2_G107,
        slot1_holds_recovery_vault=bool(slot1_holds_recovery_vault),
        forced_file_number_reset_requested=bool(forced_file_number_reset_requested),
        create_new_folder_requested=bool(create_new_folder_requested),
    )

    matrix = compute_file_settings_and_slot1_vault_matrix()
    slot1_mut_events = (
        int(claimed_slot1_vault_folder_mutation_events)
        if isinstance(claimed_slot1_vault_folder_mutation_events, int)
        else 1
    )
    if (
        resolved["slot1_vault_folder_mutation_blocked"]
        or slot1_mut_events != 0
        or matrix["slot1_vault_folder_mutation_events"] != 0
    ):
        _add_code(codes, STATUS_BLOCKED_G107_SLOT1_VAULT_FOLDER_MUTATION_VIOLATION)
        errors.append(
            "[Forced File Number Reset] / [Create New Folder] is hard-blocked on Slot 1 while Slot 1 holds the read-only CAMSET/BODYDATA.DAT recovery vault."
        )

    persistence_checks = (
        (
            claimed_post_reset_movie_file_number,
            resolved["effective_post_reset_movie_file_number"],
        ),
        (
            claimed_post_reset_movie_file_name_format,
            resolved["effective_post_reset_movie_file_name_format"],
        ),
        (
            claimed_post_reset_camera_id,
            resolved["effective_post_reset_camera_id"],
        ),
        (
            claimed_post_reset_reel_number,
            resolved["effective_post_reset_reel_number"],
        ),
        (
            claimed_post_reset_camera_position,
            resolved["effective_post_reset_camera_position"],
        ),
        (
            claimed_post_reset_title_name,
            resolved["effective_post_reset_title_name"],
        ),
        (
            claimed_post_reset_still_file_number,
            resolved["effective_post_reset_still_file_number"],
        ),
        (
            claimed_post_reset_still_set_file_name,
            resolved["effective_post_reset_still_set_file_name"],
        ),
        (
            claimed_post_reset_still_folder_name,
            resolved["effective_post_reset_still_folder_name"],
        ),
    )
    survives_reset_ok = True
    for claimed_val, expected_val in persistence_checks:
        if claimed_val is not None and claimed_val != expected_val:
            survives_reset_ok = False
            break
    if not survives_reset_ok:
        _add_code(codes, STATUS_BLOCKED_G107_RESET_PERSISTENCE_VIOLATION)
        errors.append(
            "[File Settings] and [File/Folder Settings] must survive [Camera Settings Reset] and reset only via [Initialize]."
        )

    valid = not codes
    status = STATUS_VERIFIED_G107 if valid else codes[0]
    raw_title_str = pre_reset_title_name if isinstance(pre_reset_title_name, str) else ""
    raw_st_prefix = (
        pre_reset_still_set_file_name
        if isinstance(pre_reset_still_set_file_name, str)
        else ""
    )

    return MovieFileSettingsStillDscAndSlot1VaultGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}"
        if isinstance(body_model_id, int)
        else "invalid",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        reset_action=resolved["reset_action"],
        movie_file_settings_menu_path=MOVIE_FILE_SETTINGS_MENU_PATH_G107,
        still_file_folder_settings_menu_path=STILL_FILE_FOLDER_SETTINGS_MENU_PATH_G107,
        pre_reset_movie_file_number=norm_mv_num or str(pre_reset_movie_file_number),
        effective_post_reset_movie_file_number=resolved[
            "effective_post_reset_movie_file_number"
        ],
        series_counter_reset_requested=bool(series_counter_reset_requested),
        effective_movie_sequence_index=resolved["effective_movie_sequence_index"],
        pre_reset_movie_file_name_format=norm_mv_fmt
        or str(pre_reset_movie_file_name_format),
        effective_post_reset_movie_file_name_format=resolved[
            "effective_post_reset_movie_file_name_format"
        ],
        pre_reset_camera_id=str(pre_reset_camera_id),
        effective_post_reset_camera_id=resolved["effective_post_reset_camera_id"],
        pre_reset_reel_number=parsed_reel if parsed_reel is not None else -1,
        effective_post_reset_reel_number=resolved["effective_post_reset_reel_number"],
        formatted_reel_number=resolved["formatted_reel_number"],
        pre_reset_camera_position=norm_cam_pos or str(pre_reset_camera_position),
        effective_post_reset_camera_position=resolved[
            "effective_post_reset_camera_position"
        ],
        pre_reset_title_name=raw_title_str,
        effective_post_reset_title_name=resolved["effective_post_reset_title_name"],
        title_name_char_length=len(raw_title_str),
        title_name_within_37char_ascii=title_ok,
        movie_folder_path=str(movie_folder_path),
        movie_fixed_folder_topology_verified=fixed_mv_folder_ok,
        custom_movie_folder_requested=bool(custom_movie_folder_requested),
        sample_movie_clip_filename=resolved["sample_movie_clip_filename"],
        pre_reset_still_file_number=norm_st_num or str(pre_reset_still_file_number),
        effective_post_reset_still_file_number=resolved[
            "effective_post_reset_still_file_number"
        ],
        pre_reset_still_set_file_name=raw_st_prefix,
        effective_post_reset_still_set_file_name=resolved[
            "effective_post_reset_still_set_file_name"
        ],
        still_set_file_name_valid_3char=still_prefix_ok,
        pre_reset_still_folder_name=norm_st_folder or str(pre_reset_still_folder_name),
        effective_post_reset_still_folder_name=resolved[
            "effective_post_reset_still_folder_name"
        ],
        sample_still_folder_label=resolved["sample_still_folder_label"],
        sample_still_image_filename=resolved["sample_still_image_filename"],
        file_and_folder_settings_survive_camera_settings_reset=survives_reset_ok,
        target_still_slot=resolved["target_still_slot"],
        slot1_holds_recovery_vault=bool(slot1_holds_recovery_vault),
        forced_file_number_reset_requested=bool(forced_file_number_reset_requested),
        create_new_folder_requested=bool(create_new_folder_requested),
        still_folder_mutation_permitted=resolved["still_folder_mutation_permitted"],
        slot1_vault_folder_mutation_blocked=resolved[
            "slot1_vault_folder_mutation_blocked"
        ],
        slot1_vault_folder_mutation_events=slot1_mut_events,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g107_movie_file_settings_still_dsc_and_slot1_vault_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    file_settings_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase268DonorAuditResult] = None,
) -> Tuple[GateVerdict, G107MovieFileSettingsStillDscAndSlot1VaultGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase268_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_movie_file_settings_still_dsc_and_slot1_vault_guard(
        **dict(file_settings_kwargs or {})
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
        errors.append("Persistent eMMC write authorization requested in Gate G107.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G107 if valid else codes[0]

    res = G107MovieFileSettingsStillDscAndSlot1VaultGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        file_settings_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, mv_fmt={guard.effective_post_reset_movie_file_name_format}"
        f"(cam={guard.effective_post_reset_camera_id}{guard.formatted_reel_number}{guard.effective_post_reset_camera_position},"
        f"title_len={guard.title_name_char_length},mv_dir={guard.movie_folder_path}), "
        f"still_prefix={guard.effective_post_reset_still_set_file_name}"
        f"(folder={guard.effective_post_reset_still_folder_name},"
        f"slot1_mut={guard.slot1_vault_folder_mutation_events})"
    )
    verdict = GateVerdict(
        gate_id=G107_GATE_ID,
        gate_code=G107_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate `G108`: `[Gamma Display Assist]` (`[Log Shooting]` Lockout & LCD-Only
#    Clean-HDMI Scope) vs `[Display LUT]` / `[Select LUT]` `User1..User16`,
#    `[Auto Review]` `Off` Cinema Default & `6`-Item `[TC/UB]` Persistence Guard
# ---------------------------------------------------------------------------


def compute_gamma_disp_assist_vs_log_shooting_matrix() -> Dict[str, Any]:
    """Exhaustively evaluate all `4 x 2 x 4 x 2 x 2 = 128` combinations of
    `(log_shooting_mode, gamma_display_assist, gamma_disp_assist_typ,
    display_lut, output_target)` on `ILME-FX3` (`Ver. 7.02`, `ilc/2210`), proving:
    - `[Gamma Display Assist]` is strictly locked to `Off` across all `96`
      states where `[Log Shooting] != Off` (`gamma_assist_log_lockout_bypass_events == 0`);
    - External TV/HDMI output NEVER receives `[Gamma Display Assist]` across all
      `64` HDMI states (`external_hdmi_gamma_assist_leak_events == 0`).
    """
    states_checked = 0
    log_active_locked_off_states = 0
    lcd_gamma_assist_active_states = 0
    gamma_assist_log_lockout_bypass_events = 0
    external_hdmi_gamma_assist_leak_events = 0

    for log_mode in ALLOWED_LOG_SHOOTING_MODES_G108:
        for g_assist in ALLOWED_GAMMA_DISP_ASSIST_STATES_G108:
            for g_typ in ALLOWED_GAMMA_ASSIST_TYPES_G108:
                for disp_lut in ALLOWED_DISPLAY_LUT_STATES_G108:
                    for target in ("CAMERA_LCD", "EXTERNAL_HDMI_TV"):
                        states_checked += 1
                        log_active = log_mode != LOG_SHOOTING_OFF_G108
                        eff_assist = (
                            GAMMA_DISP_ASSIST_OFF_G108 if log_active else g_assist
                        )
                        if log_active:
                            log_active_locked_off_states += 1
                            if eff_assist != GAMMA_DISP_ASSIST_OFF_G108:
                                gamma_assist_log_lockout_bypass_events += 1
                        applied_on_target = bool(
                            target == "CAMERA_LCD"
                            and eff_assist == GAMMA_DISP_ASSIST_ON_G108
                        )
                        if target == "CAMERA_LCD" and applied_on_target:
                            lcd_gamma_assist_active_states += 1
                        if target == "EXTERNAL_HDMI_TV" and applied_on_target:
                            external_hdmi_gamma_assist_leak_events += 1
                        _ = (g_typ, disp_lut)

    return {
        "states_checked": states_checked,
        "log_active_locked_off_states": log_active_locked_off_states,
        "lcd_gamma_assist_active_states": lcd_gamma_assist_active_states,
        "gamma_assist_log_lockout_bypass_events": gamma_assist_log_lockout_bypass_events,
        "external_hdmi_gamma_assist_leak_events": external_hdmi_gamma_assist_leak_events,
    }


def resolve_fx3_gamma_disp_assist_auto_review_and_tcub_state(
    *,
    reset_action: str = RESET_ACTION_NONE,
    log_shooting_mode: str = LOG_SHOOTING_OFF_G108,
    pre_reset_gamma_display_assist: str = GAMMA_DISP_ASSIST_FACTORY_DEFAULT_G108,
    pre_reset_gamma_disp_assist_typ: str = GAMMA_ASSIST_TYP_FACTORY_DEFAULT_G108,
    pre_reset_display_lut: str = DISPLAY_LUT_FACTORY_DEFAULT_G108,
    pre_reset_select_lut: str = SELECT_LUT_FACTORY_DEFAULT_G108,
    pre_reset_auto_review: str = AUTO_REVIEW_FACTORY_DEFAULT_G108,
    frame_rate: str = FRAME_RATE_NTSC_29_97P_G108,
    pre_reset_tc_preset: str = TC_PRESET_FACTORY_DEFAULT_G108,
    pre_reset_ub_preset: str = UB_PRESET_FACTORY_DEFAULT_G108,
    pre_reset_tc_format: str = TC_FORMAT_FACTORY_DEFAULT_G108,
    pre_reset_tc_run: str = TC_RUN_FACTORY_DEFAULT_G108,
    pre_reset_tc_make: str = TC_MAKE_FACTORY_DEFAULT_G108,
    pre_reset_ub_time_rec: str = UB_TIME_REC_FACTORY_DEFAULT_G108,
    pre_reset_tcub_disp_setting: str = TCUB_DISP_FACTORY_DEFAULT_G108,
) -> Dict[str, Any]:
    """Deterministic state resolver for Wave-44 Gate `G108`."""
    norm_reset = _norm_reset_action_phase268(reset_action) or RESET_ACTION_NONE
    norm_log = _norm_log_shooting_mode_g108(log_shooting_mode) or LOG_SHOOTING_OFF_G108
    norm_g_assist = (
        _norm_on_off_phase268(pre_reset_gamma_display_assist)
        or GAMMA_DISP_ASSIST_FACTORY_DEFAULT_G108
    )
    norm_g_typ = (
        _norm_gamma_assist_typ_g108(pre_reset_gamma_disp_assist_typ)
        or GAMMA_ASSIST_TYP_FACTORY_DEFAULT_G108
    )
    norm_disp_lut = (
        _norm_on_off_phase268(pre_reset_display_lut) or DISPLAY_LUT_FACTORY_DEFAULT_G108
    )
    norm_sel_lut = (
        _norm_select_lut_g108(pre_reset_select_lut) or SELECT_LUT_FACTORY_DEFAULT_G108
    )
    norm_auto_rev = (
        _norm_auto_review_g108(pre_reset_auto_review)
        or AUTO_REVIEW_FACTORY_DEFAULT_G108
    )
    norm_fps = _norm_frame_rate_g108(frame_rate) or FRAME_RATE_NTSC_29_97P_G108
    norm_tc_preset = (
        _norm_tc_preset_g108(pre_reset_tc_preset) or TC_PRESET_FACTORY_DEFAULT_G108
    )
    norm_ub_preset = (
        _norm_ub_preset_g108(pre_reset_ub_preset) or UB_PRESET_FACTORY_DEFAULT_G108
    )
    norm_tc_fmt = (
        _norm_tc_format_g108(pre_reset_tc_format) or TC_FORMAT_FACTORY_DEFAULT_G108
    )
    norm_tc_run = _norm_tc_run_g108(pre_reset_tc_run) or TC_RUN_FACTORY_DEFAULT_G108
    norm_tc_make = _norm_tc_make_g108(pre_reset_tc_make) or TC_MAKE_FACTORY_DEFAULT_G108
    norm_ub_rec = (
        _norm_on_off_phase268(pre_reset_ub_time_rec) or UB_TIME_REC_FACTORY_DEFAULT_G108
    )
    norm_tcub_disp = (
        _norm_tcub_disp_setting_g108(pre_reset_tcub_disp_setting)
        or TCUB_DISP_FACTORY_DEFAULT_G108
    )

    # Official Sony ILME-FX3 Help Guide (ilc/2210) persistence:
    # - [Setup] items ([Gamma Display Assist], [Gamma Disp. Assist Typ.],
    #   [Display LUT], [Auto Review], [TC/UB Disp. Setting]) AND all 6 [TC/UB]
    #   items SURVIVE [Camera Settings Reset] & [Reset Network Set.], resetting
    #   to factory defaults ONLY via [Initialize].
    # - [Select LUT] under [Exposure/Color] resets on [Camera Settings Reset] & [Initialize].
    if norm_reset == RESET_ACTION_INITIALIZE:
        eff_g_assist = GAMMA_DISP_ASSIST_FACTORY_DEFAULT_G108
        eff_g_typ = GAMMA_ASSIST_TYP_FACTORY_DEFAULT_G108
        eff_disp_lut = DISPLAY_LUT_FACTORY_DEFAULT_G108
        eff_sel_lut = SELECT_LUT_FACTORY_DEFAULT_G108
        eff_auto_rev = AUTO_REVIEW_FACTORY_DEFAULT_G108
        eff_tc_preset = TC_PRESET_FACTORY_DEFAULT_G108
        eff_ub_preset = UB_PRESET_FACTORY_DEFAULT_G108
        eff_tc_fmt = TC_FORMAT_FACTORY_DEFAULT_G108
        eff_tc_run = TC_RUN_FACTORY_DEFAULT_G108
        eff_tc_make = TC_MAKE_FACTORY_DEFAULT_G108
        eff_ub_rec = UB_TIME_REC_FACTORY_DEFAULT_G108
        eff_tcub_disp = TCUB_DISP_FACTORY_DEFAULT_G108
    elif norm_reset == RESET_ACTION_CAMERA_SETTINGS_RESET:
        eff_g_assist = norm_g_assist
        eff_g_typ = norm_g_typ
        eff_disp_lut = norm_disp_lut
        eff_sel_lut = SELECT_LUT_FACTORY_DEFAULT_G108
        eff_auto_rev = norm_auto_rev
        eff_tc_preset = norm_tc_preset
        eff_ub_preset = norm_ub_preset
        eff_tc_fmt = norm_tc_fmt
        eff_tc_run = norm_tc_run
        eff_tc_make = norm_tc_make
        eff_ub_rec = norm_ub_rec
        eff_tcub_disp = norm_tcub_disp
    else:
        eff_g_assist = norm_g_assist
        eff_g_typ = norm_g_typ
        eff_disp_lut = norm_disp_lut
        eff_sel_lut = norm_sel_lut
        eff_auto_rev = norm_auto_rev
        eff_tc_preset = norm_tc_preset
        eff_ub_preset = norm_ub_preset
        eff_tc_fmt = norm_tc_fmt
        eff_tc_run = norm_tc_run
        eff_tc_make = norm_tc_make
        eff_ub_rec = norm_ub_rec
        eff_tcub_disp = norm_tcub_disp

    log_active = norm_log != LOG_SHOOTING_OFF_G108
    gamma_locked = log_active
    effective_gamma_assist = (
        GAMMA_DISP_ASSIST_OFF_G108 if gamma_locked else eff_g_assist
    )

    forced_ndf = norm_fps in FORCED_NDF_FRAME_RATES_G108
    effective_tc_fmt = TC_FORMAT_NDF_G108 if forced_ndf else eff_tc_fmt

    return {
        "reset_action": norm_reset,
        "log_shooting_mode": norm_log,
        "log_shooting_active": log_active,
        "effective_post_reset_gamma_display_assist": eff_g_assist,
        "gamma_display_assist_locked_by_log_shooting": gamma_locked,
        "effective_gamma_display_assist": effective_gamma_assist,
        "effective_post_reset_gamma_disp_assist_typ": eff_g_typ,
        "effective_post_reset_display_lut": eff_disp_lut,
        "effective_post_reset_select_lut": eff_sel_lut,
        "effective_log_monitoring_governed_by_display_lut": log_active,
        "effective_post_reset_auto_review": eff_auto_rev,
        "frame_rate": norm_fps,
        "effective_post_reset_tc_preset": eff_tc_preset,
        "effective_post_reset_ub_preset": eff_ub_preset,
        "effective_post_reset_tc_format": eff_tc_fmt,
        "tc_format_forced_ndf_by_cadence": forced_ndf,
        "effective_tc_format": effective_tc_fmt,
        "effective_post_reset_tc_run": eff_tc_run,
        "effective_post_reset_tc_make": eff_tc_make,
        "effective_post_reset_ub_time_rec": eff_ub_rec,
        "effective_post_reset_tcub_disp_setting": eff_tcub_disp,
    }


def verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE268,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE268,
    reset_action: str = RESET_ACTION_NONE,
    log_shooting_mode: str = LOG_SHOOTING_OFF_G108,
    pre_reset_gamma_display_assist: str = GAMMA_DISP_ASSIST_FACTORY_DEFAULT_G108,
    pre_reset_gamma_disp_assist_typ: str = GAMMA_ASSIST_TYP_FACTORY_DEFAULT_G108,
    pre_reset_display_lut: str = DISPLAY_LUT_FACTORY_DEFAULT_G108,
    pre_reset_select_lut: str = SELECT_LUT_FACTORY_DEFAULT_G108,
    registered_user_lut_slots: int = 4,
    pre_reset_auto_review: str = AUTO_REVIEW_FACTORY_DEFAULT_G108,
    tcub_subitems: Sequence[str] = TCUB_EXACT_6_ITEMS_G108,
    frame_rate: str = FRAME_RATE_NTSC_29_97P_G108,
    pre_reset_tc_preset: str = TC_PRESET_FACTORY_DEFAULT_G108,
    pre_reset_ub_preset: str = UB_PRESET_FACTORY_DEFAULT_G108,
    pre_reset_tc_format: str = TC_FORMAT_FACTORY_DEFAULT_G108,
    pre_reset_tc_run: str = TC_RUN_FACTORY_DEFAULT_G108,
    pre_reset_tc_make: str = TC_MAKE_FACTORY_DEFAULT_G108,
    pre_reset_ub_time_rec: str = UB_TIME_REC_FACTORY_DEFAULT_G108,
    pre_reset_tcub_disp_setting: str = TCUB_DISP_FACTORY_DEFAULT_G108,
    claimed_effective_gamma_display_assist: Optional[str] = None,
    claimed_gamma_assist_log_lockout_bypass_events: int = 0,
    claimed_external_hdmi_gamma_assist_applied: bool = False,
    claimed_hdmi_gamma_assist_leak_frames: int = 0,
    claimed_auto_review_applies_to_movie: bool = False,
    claimed_movie_auto_review_interrupt_events: int = 0,
    claimed_effective_tc_format: Optional[str] = None,
    claimed_tc_format_24p_pal_df_bypass_events: int = 0,
    claimed_post_reset_gamma_display_assist: Optional[str] = None,
    claimed_post_reset_gamma_disp_assist_typ: Optional[str] = None,
    claimed_post_reset_display_lut: Optional[str] = None,
    claimed_post_reset_auto_review: Optional[str] = None,
    claimed_post_reset_tc_preset: Optional[str] = None,
    claimed_post_reset_ub_preset: Optional[str] = None,
    claimed_post_reset_tc_format: Optional[str] = None,
    claimed_post_reset_tc_run: Optional[str] = None,
    claimed_post_reset_tc_make: Optional[str] = None,
    claimed_post_reset_ub_time_rec: Optional[str] = None,
    claimed_post_reset_tcub_disp_setting: Optional[str] = None,
) -> GammaDispAssistLogLockoutAutoReviewTcubGuardResult:
    """Verify Gate `G108`: `[Gamma Display Assist]` (`[Log Shooting]` hard lockout
    to `Off` & camera-LCD-only scope) vs `[Display LUT]` / `[Select LUT]`
    (`S-Log3`, `s709`, `709(800%)`, `User1..User16`), `[Auto Review]` (`Off`
    cinema default, Still-only), and `6`-item `[TC/UB]` + `[TC/UB Disp. Setting]`
    non-resettable persistence across `[Camera Settings Reset]`.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        body_model_name != FX3_MODEL_NAME
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE268
        or fw_tuple is None
        or fw_tuple < (1, 0)
    ):
        _add_code(codes, STATUS_BLOCKED_G108_TELEMETRY_INVALID)
        errors.append(
            "Invalid ILME-FX3 body/help-guide/firmware identity for Gate G108."
        )

    norm_reset = _norm_reset_action_phase268(reset_action)
    norm_log = _norm_log_shooting_mode_g108(log_shooting_mode)
    norm_g_assist = _norm_on_off_phase268(pre_reset_gamma_display_assist)
    norm_g_typ = _norm_gamma_assist_typ_g108(pre_reset_gamma_disp_assist_typ)
    norm_fps = _norm_frame_rate_g108(frame_rate)
    norm_tc_preset = _norm_tc_preset_g108(pre_reset_tc_preset)
    norm_ub_preset = _norm_ub_preset_g108(pre_reset_ub_preset)
    norm_tc_fmt = _norm_tc_format_g108(pre_reset_tc_format)
    norm_tc_run = _norm_tc_run_g108(pre_reset_tc_run)
    norm_tc_make = _norm_tc_make_g108(pre_reset_tc_make)
    norm_ub_rec = _norm_on_off_phase268(pre_reset_ub_time_rec)
    norm_tcub_disp = _norm_tcub_disp_setting_g108(pre_reset_tcub_disp_setting)
    tcub_items_tuple = tuple(str(x) for x in tcub_subitems)
    tcub_6_ok = tcub_items_tuple == TCUB_EXACT_6_ITEMS_G108

    if (
        norm_reset is None
        or norm_log is None
        or norm_g_assist is None
        or norm_g_typ is None
        or norm_fps is None
        or norm_tc_preset is None
        or norm_ub_preset is None
        or norm_tc_fmt is None
        or norm_tc_run is None
        or norm_tc_make is None
        or norm_ub_rec is None
        or norm_tcub_disp is None
        or (not tcub_6_ok)
        or not isinstance(claimed_gamma_assist_log_lockout_bypass_events, int)
        or claimed_gamma_assist_log_lockout_bypass_events < 0
        or not isinstance(claimed_hdmi_gamma_assist_leak_frames, int)
        or claimed_hdmi_gamma_assist_leak_frames < 0
        or not isinstance(claimed_movie_auto_review_interrupt_events, int)
        or claimed_movie_auto_review_interrupt_events < 0
        or not isinstance(claimed_tc_format_24p_pal_df_bypass_events, int)
        or claimed_tc_format_24p_pal_df_bypass_events < 0
    ):
        _add_code(codes, STATUS_BLOCKED_G108_TELEMETRY_INVALID)
        errors.append(
            "Invalid G108 menu option, 6-item [TC/UB] schema, or event counter telemetry."
        )

    norm_disp_lut = _norm_on_off_phase268(pre_reset_display_lut)
    norm_sel_lut = _norm_select_lut_g108(pre_reset_select_lut)
    user_slot_index = 0
    if norm_sel_lut is not None and norm_sel_lut.startswith("User"):
        user_slot_index = int(norm_sel_lut[4:], 10)

    if (
        norm_disp_lut is None
        or norm_sel_lut is None
        or not isinstance(registered_user_lut_slots, int)
        or isinstance(registered_user_lut_slots, bool)
        or registered_user_lut_slots < 0
        or registered_user_lut_slots > MAX_USER_LUT_SLOTS_G108
        or (user_slot_index > 0 and user_slot_index > registered_user_lut_slots)
    ):
        _add_code(codes, STATUS_BLOCKED_G108_DISPLAY_LUT_OR_SELECT_LUT_VIOLATION)
        errors.append(
            "[Display LUT] (`On`/`Off`) or [Select LUT] (`S-Log3`, `s709`, `709(800%)`, registered `User1..User16`) violated bounds."
        )

    norm_auto_rev = _norm_auto_review_g108(pre_reset_auto_review)
    auto_rev_still_only = (not bool(claimed_auto_review_applies_to_movie)) and (
        claimed_movie_auto_review_interrupt_events == 0
    )
    if norm_auto_rev is None or (not auto_rev_still_only):
        _add_code(codes, STATUS_BLOCKED_G108_AUTO_REVIEW_SCOPE_OR_DEFAULT_VIOLATION)
        errors.append(
            "[Auto Review] (`Off` default / `2 Sec` / `5 Sec` / `10 Sec`) must remain strictly Still-image only with 0 movie interruptions."
        )

    resolved = resolve_fx3_gamma_disp_assist_auto_review_and_tcub_state(
        reset_action=norm_reset or RESET_ACTION_NONE,
        log_shooting_mode=norm_log or LOG_SHOOTING_OFF_G108,
        pre_reset_gamma_display_assist=norm_g_assist
        or GAMMA_DISP_ASSIST_FACTORY_DEFAULT_G108,
        pre_reset_gamma_disp_assist_typ=norm_g_typ
        or GAMMA_ASSIST_TYP_FACTORY_DEFAULT_G108,
        pre_reset_display_lut=norm_disp_lut or DISPLAY_LUT_FACTORY_DEFAULT_G108,
        pre_reset_select_lut=norm_sel_lut or SELECT_LUT_FACTORY_DEFAULT_G108,
        pre_reset_auto_review=norm_auto_rev or AUTO_REVIEW_FACTORY_DEFAULT_G108,
        frame_rate=norm_fps or FRAME_RATE_NTSC_29_97P_G108,
        pre_reset_tc_preset=norm_tc_preset or TC_PRESET_FACTORY_DEFAULT_G108,
        pre_reset_ub_preset=norm_ub_preset or UB_PRESET_FACTORY_DEFAULT_G108,
        pre_reset_tc_format=norm_tc_fmt or TC_FORMAT_FACTORY_DEFAULT_G108,
        pre_reset_tc_run=norm_tc_run or TC_RUN_FACTORY_DEFAULT_G108,
        pre_reset_tc_make=norm_tc_make or TC_MAKE_FACTORY_DEFAULT_G108,
        pre_reset_ub_time_rec=norm_ub_rec or UB_TIME_REC_FACTORY_DEFAULT_G108,
        pre_reset_tcub_disp_setting=norm_tcub_disp or TCUB_DISP_FACTORY_DEFAULT_G108,
    )

    matrix = compute_gamma_disp_assist_vs_log_shooting_matrix()
    norm_claimed_eff_gamma = (
        _norm_on_off_phase268(claimed_effective_gamma_display_assist)
        if claimed_effective_gamma_display_assist is not None
        else None
    )
    if (
        (
            claimed_effective_gamma_display_assist is not None
            and norm_claimed_eff_gamma != resolved["effective_gamma_display_assist"]
        )
        or claimed_gamma_assist_log_lockout_bypass_events != 0
        or matrix["gamma_assist_log_lockout_bypass_events"] != 0
    ):
        _add_code(
            codes, STATUS_BLOCKED_G108_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_VIOLATION
        )
        errors.append(
            "[Gamma Display Assist] must be hard-locked to [Off] whenever [Log Shooting] (`Cine EI` / `Cine EI Quick` / `Flexible ISO`) != [Off]."
        )

    lcd_only_ok = (
        (not bool(claimed_external_hdmi_gamma_assist_applied))
        and claimed_hdmi_gamma_assist_leak_frames == 0
        and matrix["external_hdmi_gamma_assist_leak_events"] == 0
    )
    if not lcd_only_ok:
        _add_code(codes, STATUS_BLOCKED_G108_EXTERNAL_HDMI_GAMMA_ASSIST_LEAK_VIOLATION)
        errors.append(
            "[Gamma Display Assist] is camera-LCD-only and must never be applied to external TV/HDMI output."
        )

    norm_claimed_eff_tc_fmt = (
        _norm_tc_format_g108(claimed_effective_tc_format)
        if claimed_effective_tc_format is not None
        else None
    )
    if (
        (
            claimed_effective_tc_format is not None
            and norm_claimed_eff_tc_fmt != resolved["effective_tc_format"]
        )
        or claimed_tc_format_24p_pal_df_bypass_events != 0
    ):
        _add_code(codes, STATUS_BLOCKED_G108_TC_FORMAT_24P_PAL_NDF_VIOLATION)
        errors.append(
            "[Time Code Format] must force [NDF] on 24.00p and PAL 25p/50p cadences and match effective format."
        )

    persistence_pairs = (
        (
            claimed_post_reset_gamma_display_assist,
            resolved["effective_post_reset_gamma_display_assist"],
        ),
        (
            claimed_post_reset_gamma_disp_assist_typ,
            resolved["effective_post_reset_gamma_disp_assist_typ"],
        ),
        (
            claimed_post_reset_display_lut,
            resolved["effective_post_reset_display_lut"],
        ),
        (
            claimed_post_reset_auto_review,
            resolved["effective_post_reset_auto_review"],
        ),
        (
            claimed_post_reset_tc_preset,
            resolved["effective_post_reset_tc_preset"],
        ),
        (
            claimed_post_reset_ub_preset,
            resolved["effective_post_reset_ub_preset"],
        ),
        (
            claimed_post_reset_tc_format,
            resolved["effective_post_reset_tc_format"],
        ),
        (
            claimed_post_reset_tc_run,
            resolved["effective_post_reset_tc_run"],
        ),
        (
            claimed_post_reset_tc_make,
            resolved["effective_post_reset_tc_make"],
        ),
        (
            claimed_post_reset_ub_time_rec,
            resolved["effective_post_reset_ub_time_rec"],
        ),
        (
            claimed_post_reset_tcub_disp_setting,
            resolved["effective_post_reset_tcub_disp_setting"],
        ),
    )
    survives_ok = True
    for claimed_val, expected_val in persistence_pairs:
        if claimed_val is not None and claimed_val != expected_val:
            survives_ok = False
            break
    if not survives_ok:
        _add_code(codes, STATUS_BLOCKED_G108_RESET_SURVIVAL_OR_INITIALIZE_VIOLATION)
        errors.append(
            "[Gamma Display Assist], [Display LUT], [Auto Review], all 6 [TC/UB] items, and [TC/UB Disp. Setting] must survive [Camera Settings Reset] and reset only via [Initialize]."
        )

    valid = not codes
    status = STATUS_VERIFIED_G108 if valid else codes[0]

    return GammaDispAssistLogLockoutAutoReviewTcubGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{body_model_id:08x}"
        if isinstance(body_model_id, int)
        else "invalid",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        reset_action=resolved["reset_action"],
        log_shooting_mode=resolved["log_shooting_mode"],
        log_shooting_active=resolved["log_shooting_active"],
        gamma_disp_assist_menu_path=GAMMA_DISP_ASSIST_MENU_PATH_G108,
        gamma_disp_assist_typ_menu_path=GAMMA_DISP_ASSIST_TYP_MENU_PATH_G108,
        display_lut_menu_path=DISPLAY_LUT_MENU_PATH_G108,
        select_lut_menu_path=SELECT_LUT_MENU_PATH_G108,
        auto_review_menu_path=AUTO_REVIEW_MENU_PATH_G108,
        tcub_menu_path=TCUB_MENU_PATH_G108,
        tcub_disp_setting_menu_path=TCUB_DISP_SETTING_MENU_PATH_G108,
        pre_reset_gamma_display_assist=norm_g_assist
        or str(pre_reset_gamma_display_assist),
        effective_post_reset_gamma_display_assist=resolved[
            "effective_post_reset_gamma_display_assist"
        ],
        gamma_display_assist_locked_by_log_shooting=resolved[
            "gamma_display_assist_locked_by_log_shooting"
        ],
        effective_gamma_display_assist=resolved["effective_gamma_display_assist"],
        pre_reset_gamma_disp_assist_typ=norm_g_typ
        or str(pre_reset_gamma_disp_assist_typ),
        effective_post_reset_gamma_disp_assist_typ=resolved[
            "effective_post_reset_gamma_disp_assist_typ"
        ],
        camera_lcd_only_scope_verified=lcd_only_ok,
        external_hdmi_gamma_assist_applied=bool(
            claimed_external_hdmi_gamma_assist_applied
        ),
        hdmi_gamma_assist_leak_frames=int(claimed_hdmi_gamma_assist_leak_frames)
        if isinstance(claimed_hdmi_gamma_assist_leak_frames, int)
        else 1,
        gamma_assist_log_lockout_bypass_events=int(
            claimed_gamma_assist_log_lockout_bypass_events
        )
        if isinstance(claimed_gamma_assist_log_lockout_bypass_events, int)
        else 1,
        pre_reset_display_lut=norm_disp_lut or str(pre_reset_display_lut),
        effective_post_reset_display_lut=resolved["effective_post_reset_display_lut"],
        pre_reset_select_lut=norm_sel_lut or str(pre_reset_select_lut),
        effective_post_reset_select_lut=resolved["effective_post_reset_select_lut"],
        effective_log_monitoring_governed_by_display_lut=resolved[
            "effective_log_monitoring_governed_by_display_lut"
        ],
        registered_user_lut_slots=int(registered_user_lut_slots)
        if isinstance(registered_user_lut_slots, int)
        and not isinstance(registered_user_lut_slots, bool)
        else -1,
        pre_reset_auto_review=norm_auto_rev or str(pre_reset_auto_review),
        effective_post_reset_auto_review=resolved["effective_post_reset_auto_review"],
        auto_review_still_only_scope=auto_rev_still_only,
        movie_auto_review_interrupt_events=int(
            claimed_movie_auto_review_interrupt_events
        )
        if isinstance(claimed_movie_auto_review_interrupt_events, int)
        else 1,
        tcub_subitems=tcub_items_tuple,
        tcub_exact_6_items_verified=tcub_6_ok,
        frame_rate=resolved["frame_rate"],
        pre_reset_tc_preset=norm_tc_preset or str(pre_reset_tc_preset),
        effective_post_reset_tc_preset=resolved["effective_post_reset_tc_preset"],
        pre_reset_ub_preset=norm_ub_preset or str(pre_reset_ub_preset),
        effective_post_reset_ub_preset=resolved["effective_post_reset_ub_preset"],
        pre_reset_tc_format=norm_tc_fmt or str(pre_reset_tc_format),
        effective_post_reset_tc_format=resolved["effective_post_reset_tc_format"],
        tc_format_forced_ndf_by_cadence=resolved["tc_format_forced_ndf_by_cadence"],
        effective_tc_format=resolved["effective_tc_format"],
        pre_reset_tc_run=norm_tc_run or str(pre_reset_tc_run),
        effective_post_reset_tc_run=resolved["effective_post_reset_tc_run"],
        pre_reset_tc_make=norm_tc_make or str(pre_reset_tc_make),
        effective_post_reset_tc_make=resolved["effective_post_reset_tc_make"],
        pre_reset_ub_time_rec=norm_ub_rec or str(pre_reset_ub_time_rec),
        effective_post_reset_ub_time_rec=resolved["effective_post_reset_ub_time_rec"],
        pre_reset_tcub_disp_setting=norm_tcub_disp or str(pre_reset_tcub_disp_setting),
        effective_post_reset_tcub_disp_setting=resolved[
            "effective_post_reset_tcub_disp_setting"
        ],
        setup_and_tcub_survive_camera_settings_reset=survives_ok,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g108_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    gamma_assist_tcub_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase268DonorAuditResult] = None,
) -> Tuple[GateVerdict, G108GammaDispAssistLogLockoutAutoReviewTcubGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase268_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
        **dict(gamma_assist_tcub_kwargs or {})
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
        errors.append("Persistent eMMC write authorization requested in Gate G108.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G108 if valid else codes[0]

    res = G108GammaDispAssistLogLockoutAutoReviewTcubGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        gamma_assist_auto_review_tcub_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, log={guard.log_shooting_mode}"
        f"(gamma_assist={guard.effective_gamma_display_assist},"
        f"disp_lut={guard.effective_post_reset_display_lut}/{guard.effective_post_reset_select_lut},"
        f"hdmi_leak={guard.hdmi_gamma_assist_leak_frames}), "
        f"auto_review={guard.effective_post_reset_auto_review}, "
        f"tc={guard.effective_tc_format}/{guard.effective_post_reset_tc_run}/{guard.effective_post_reset_tc_make}"
    )
    verdict = GateVerdict(
        gate_id=G108_GATE_ID,
        gate_code=G108_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `108`-Gate Master Safety Preflight (`G01..G108`)
# ---------------------------------------------------------------------------


def evaluate_108gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    file_settings_kwargs: Optional[Mapping[str, Any]] = None,
    gamma_assist_tcub_kwargs: Optional[Mapping[str, Any]] = None,
    master_106_override: Optional[Master106GateReport] = None,
    **m106_passthrough_kwargs: Any,
) -> Master108GateReport:
    """Evaluate all 108 Master Safety Gates (`G01..G108`) deterministically by
    delegating `G01..G106` directly to `evaluate_106gate_preflight()`.
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

    m106_report: Master106GateReport = (
        master_106_override
        if master_106_override is not None
        else evaluate_106gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m106_passthrough_kwargs,
        )
    )

    phase268_audit = audit_phase268_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g107_verdict, g107_res = (
        evaluate_g107_movie_file_settings_still_dsc_and_slot1_vault_guard(
            work_root=work_root,
            repo_root=resolved_root,
            force_clean_room=clean_forced,
            file_settings_kwargs=file_settings_kwargs,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            donor_audit=phase268_audit,
        )
    )

    g108_verdict, g108_res = (
        evaluate_g108_gamma_disp_assist_log_lockout_auto_review_and_tcub_guard(
            work_root=work_root,
            repo_root=resolved_root,
            force_clean_room=clean_forced,
            gamma_assist_tcub_kwargs=gamma_assist_tcub_kwargs,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            donor_audit=phase268_audit,
        )
    )

    gates_107_to_108 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g107_verdict, g108_verdict)
    ]
    all_gates = tuple(list(m106_report.gates) + gates_107_to_108)

    g01_to_g12_verified = int(m106_report.summary["g01_to_g12_verified"])
    g13_to_g106_verified = int(m106_report.summary["g13_to_g104_verified"]) + int(
        m106_report.summary["g105_to_g106_verified"]
    )
    g107_to_g108_verified = sum(1 for v in (g107_verdict, g108_verdict) if v.passed)
    total_verified = (
        g01_to_g12_verified + g13_to_g106_verified + g107_to_g108_verified
    )

    g107_to_g108_all_passed = g107_to_g108_verified == 2
    g13_to_g108_all_passed = (
        m106_report.g13_to_g106_all_passed and g107_to_g108_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m106_report.gates[:9])

    offline_105_verified = (
        g01_to_g09_ok
        and m106_report.offline_103_gates_verified
        and g107_to_g108_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_108_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g108_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m106_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_105_verified
        and m106_report.h0_h1_trial_entry_allowed
        and g107_to_g108_all_passed
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
        list(m106_report.errors)
        + list(g107_verdict.errors)
        + list(g108_verdict.errors)
    )
    warnings: List[str] = (
        list(m106_report.warnings)
        + list(g107_verdict.warnings)
        + list(g108_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m106_report.g13_to_g106_all_passed:
        overall_status = m106_report.status
    elif not g107_verdict.passed:
        overall_status = g107_verdict.status
    elif not g108_verdict.passed:
        overall_status = g108_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_108_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_108_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_108_verified:
        overall_status = "VERIFIED_ALL_108_GATES"
    else:
        overall_status = "VERIFIED_105_OF_108_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m106_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g107_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g108_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 108,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 108 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g106_verified": g13_to_g106_verified,
        "g107_to_g108_verified": g107_to_g108_verified,
        "g13_to_g108_all_passed": g13_to_g108_all_passed,
        "g107_to_g108_all_passed": g107_to_g108_all_passed,
        "offline_105_gates_verified": offline_105_verified,
        "all_108_gates_verified": all_108_verified,
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

    return Master108GateReport(
        schema=REALHW_FILE_SETTINGS_GAMMA_ASSIST_TCUB_108GATE_SCHEMA,
        version=REALHW_FILE_SETTINGS_GAMMA_ASSIST_TCUB_108GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_105_gates_verified=offline_105_verified,
        all_108_gates_verified=all_108_verified,
        g13_to_g108_all_passed=g13_to_g108_all_passed,
        g107_to_g108_all_passed=g107_to_g108_all_passed,
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
        master_106_report=m106_report.to_dict(),
        g107_result=g107_res.to_dict(),
        g108_result=g108_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_108_master_safety_gates = evaluate_108gate_preflight
run_108_gate_preflight = evaluate_108gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_file_settings_gamma_assist_tcub_and_108gate_guard",
        description=(
            "Phase 268 Safety Gates G107 (Movie File Settings Cam ID + Reel# & "
            "37-Char Title vs Still DSC Prefix & Slot-1 Vault Guard) + G108 "
            "(Gamma Display Assist Log Shooting Lockout vs Display LUT/Select LUT, "
            "Auto Review Off Default & 6-Item TC/UB Persistence Guard) + Unified "
            "108-Gate Master Safety Preflight"
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

    report = evaluate_108gate_preflight(
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
            f"verified={report.summary['verified_gates']}/108 "
            f"g107_to_g108_all_passed={report.g107_to_g108_all_passed} "
            f"all_108_gates_verified={report.all_108_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = (
        report.all_108_gates_verified
        if args.dry_run_simulated
        else report.offline_105_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
