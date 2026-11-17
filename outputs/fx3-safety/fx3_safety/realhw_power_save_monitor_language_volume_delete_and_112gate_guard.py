"""Phase 273 (Task H309, 112/112 Safety Gates, Wave-46) Sony `ILME-FX3`
(`Ver. 7.02`, `ilc/2210`) vs `ILME-FX6` (`Ver. 6.01`) Safety Gates `G111`
(`[Power Save by Monitor]` `appFw.so` 4-Mode vs `ILME-FX3` 2-Item `[Power
Setting Option]` Reality Split, `[Power Save Start Time]` 9-Deactivation Bench
Guard & `[Language]` `BK_LANG` `0x02cf019c` 34-vs-29 Parity / Reset Survival)
& `G112` (`[Volume Settings]` `0..15` Default `7` + `XLR-H1` Acoustic Feedback
Guard, `[4ch Audio Monitoring]` 5 Routes + `3.5 mm` 2ch Boundary, and
`[Delete confirm.]` `"Cancel" first` Default + `Slot-1` Recovery Vault
Delete/Format Firewall) + Unified `112`-Gate Master Safety Preflight
(`G01..G112`).

Operationalizes Wave-46 official Sony `ILME-FX3` (`Ver. 7.02`, Help Guide
`ilc/2210`) & `ILME-FX6` (`Ver. 6.01`) intelligence
(`reports/2026-11-17-global-sony-wave46-power-save-by-monitor-language-volume-delete-confirm-intel/README.md`)
as deterministic offline preflight verifiers (`G111` and `G112`) and delegates
`G01..G110` directly to `evaluate_110gate_preflight()`.
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
from .realhw_focus_mag_datetime_videolight_hdmires_and_110gate_guard import (
    Master110GateReport,
    evaluate_110gate_preflight,
)
from .realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import SPI_NOR_WRITE_AUTHORIZED
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_POWER_SAVE_MONITOR_LANGUAGE_VOLUME_DELETE_112GATE_SCHEMA: str = (
    "realhw_power_save_monitor_language_volume_delete_and_112gate_guard_v1"
)
REALHW_POWER_SAVE_MONITOR_LANGUAGE_VOLUME_DELETE_112GATE_VERSION: str = "1.0.0"

G111_GATE_ID: str = (
    "G111_power_save_monitor_split_start_time_9cond_and_language_bk_lang_guard"
)
G111_GATE_CODE: str = (
    "POWER_SAVE_MONITOR_SPLIT_START_TIME_9COND_AND_LANGUAGE_BK_LANG_GUARD"
)

G112_GATE_ID: str = (
    "G112_volume_settings_4ch_audio_monitoring_and_delete_confirm_slot1_vault_guard"
)
G112_GATE_CODE: str = (
    "VOLUME_SETTINGS_4CH_AUDIO_MONITORING_AND_DELETE_CONFIRM_SLOT1_VAULT_GUARD"
)

G111: str = G111_GATE_ID
G112: str = G112_GATE_ID
GATE_G111_POWER_SAVE_MONITOR_SPLIT_START_TIME_9COND_AND_LANGUAGE_BK_LANG_GUARD: str = (
    G111_GATE_CODE
)
GATE_G112_VOLUME_SETTINGS_4CH_AUDIO_MONITORING_AND_DELETE_CONFIRM_SLOT1_VAULT_GUARD: str = (
    G112_GATE_CODE
)

ENV_CLEAN_ROOM_TEST_PHASE273: str = "FX3_CLEAN_ROOM_TEST"

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE273: float = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE273: float = 1.00
DONOR_CHECK_MAX_SECONDS: float = DONOR_CHECK_MAX_SECONDS_PHASE273

FX3_MODEL_NAME: str = "ILME-FX3"
FX3A_MODEL_NAME: str = "ILME-FX3A"
FX3_MODEL_ID: int = 0x91030080
FX6_MODEL_NAME: str = "ILME-FX6"
FX3_DEFAULT_FW_VERSION_PHASE273: str = "7.02"
FX6_DEFAULT_FW_VERSION_PHASE273: str = "6.01"
FX3_HELP_GUIDE_CODE_PHASE273: str = "ilc/2210"

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE273: str = "Reset Network Set."
RESET_ACTION_INITIALIZE: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE273: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_RESET_NETWORK_SET_PHASE273,
    RESET_ACTION_INITIALIZE,
)

# ---------------------------------------------------------------------------
# Status & Violation Codes (G111 / G112 / Phase 273)
# ---------------------------------------------------------------------------

STATUS_VERIFIED_G111: str = (
    "VERIFIED_G111_POWER_SAVE_MONITOR_SPLIT_START_TIME_AND_LANGUAGE_SAFE"
)
STATUS_VERIFIED_G112: str = (
    "VERIFIED_G112_VOLUME_4CH_MONITORING_AND_DELETE_CONFIRM_VAULT_SAFE"
)
STATUS_BLOCKED_PHASE273_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE273_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G111_POWER_SAVE_MONITOR_UI_SPOOF_VIOLATION: str = (
    "BLOCKED_G111_POWER_SAVE_MONITOR_UI_SPOOF_VIOLATION"
)
STATUS_BLOCKED_G111_HEADLESS_MONITOR_CLOSE_SLEEP_HAZARD: str = (
    "BLOCKED_G111_HEADLESS_MONITOR_CLOSE_SLEEP_HAZARD"
)
STATUS_BLOCKED_G111_BATTERY_BENCH_IDLE_SLEEP_HAZARD: str = (
    "BLOCKED_G111_BATTERY_BENCH_IDLE_SLEEP_HAZARD"
)
STATUS_BLOCKED_G111_LANGUAGE_RESET_OR_BANK_VIOLATION: str = (
    "BLOCKED_G111_LANGUAGE_RESET_OR_BANK_VIOLATION"
)
STATUS_BLOCKED_G111_TELEMETRY_INVALID: str = (
    "BLOCKED_G111_POWER_SAVE_MONITOR_LANGUAGE_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G112_VOLUME_RANGE_OR_XLR_FEEDBACK_VIOLATION: str = (
    "BLOCKED_G112_VOLUME_RANGE_OR_XLR_FEEDBACK_VIOLATION"
)
STATUS_BLOCKED_G112_4CH_MONITORING_ROUTE_VIOLATION: str = (
    "BLOCKED_G112_4CH_MONITORING_ROUTE_VIOLATION"
)
STATUS_BLOCKED_G112_SLOT1_VAULT_DELETE_OR_FORMAT_VIOLATION: str = (
    "BLOCKED_G112_SLOT1_VAULT_DELETE_OR_FORMAT_VIOLATION"
)
STATUS_BLOCKED_G112_TELEMETRY_INVALID: str = (
    "BLOCKED_G112_VOLUME_4CH_MONITORING_DELETE_CONFIRM_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G111 Constants: [Power Save by Monitor], [Power Save Start Time] & [Language]
# ---------------------------------------------------------------------------

POWER_SETTING_OPTION_MENU_PATH_G111: str = "MENU -> Setup -> [Power Setting Option]"
POWER_SAVE_START_TIME_MENU_PATH_G111: str = (
    "MENU -> Setup -> [Power Setting Option] -> [Power Save Start Time]"
)
AUTO_POWER_OFF_TEMP_MENU_PATH_G111: str = (
    "MENU -> Setup -> [Power Setting Option] -> [Auto Power OFF Temp.]"
)
LANGUAGE_MENU_PATH_G111: str = "MENU -> Setup -> [Area/Date] -> [Language]"

FX3_POWER_SETTING_OPTION_EXACT_2_ITEMS_G111: Tuple[str, ...] = (
    "Power Save Start Time",
    "Auto Power OFF Temp.",
)
FX3_UI_EXPOSES_POWER_SAVE_BY_MONITOR_G111: bool = False
FX3_NON_EXPOSING_BODY_MODELS_G111: Tuple[str, ...] = (
    FX3_MODEL_NAME,
    FX3A_MODEL_NAME,
    FX6_MODEL_NAME,
)
SIBLING_EXPOSING_BODY_MODELS_G111: Tuple[str, ...] = (
    "ILME-FX2",
    "ILCE-7M4",
    "ZV-E1",
    "ILCE-6700",
)

SPOOF_FAKE_MONITOR_MODE_G111: str = "Open: On/Close: Off"
POWER_SAVE_BY_MONITOR_APPFW_TITLE_G111: str = "Power Save by Monitor"
POWER_SAVE_BY_MONITOR_RESID16_G111: int = 0x60B9

MONITOR_POWER_LINKAGE_BOTH_LINKED_G111: str = "Both Linked"
MONITOR_POWER_LINKAGE_OPEN_RETURN_G111: str = "Open: Return"
MONITOR_POWER_LINKAGE_CLOSE_POWER_SAVE_G111: str = "Close: Power Save"
MONITOR_POWER_LINKAGE_DOES_NOT_LINK_G111: str = "Does Not Link"

ALLOWED_MONITOR_POWER_LINKAGE_MODES_G111: Tuple[str, ...] = (
    MONITOR_POWER_LINKAGE_BOTH_LINKED_G111,
    MONITOR_POWER_LINKAGE_OPEN_RETURN_G111,
    MONITOR_POWER_LINKAGE_CLOSE_POWER_SAVE_G111,
    MONITOR_POWER_LINKAGE_DOES_NOT_LINK_G111,
)
SAFE_HEADLESS_MONITOR_POWER_LINKAGE_MODES_G111: Tuple[str, ...] = (
    MONITOR_POWER_LINKAGE_DOES_NOT_LINK_G111,
    MONITOR_POWER_LINKAGE_OPEN_RETURN_G111,
)
MONITOR_POWER_LINKAGE_FACTORY_DEFAULT_G111: str = MONITOR_POWER_LINKAGE_BOTH_LINKED_G111

MONITOR_POWER_LINKAGE_UXC_METADATA_G111: Dict[str, Tuple[int, str]] = {
    MONITOR_POWER_LINKAGE_BOTH_LINKED_G111: (0x6DB5, "ON_ALL"),
    MONITOR_POWER_LINKAGE_OPEN_RETURN_G111: (0x6DB6, "ON_OPEN"),
    MONITOR_POWER_LINKAGE_CLOSE_POWER_SAVE_G111: (0x60A8, "ON_CLOSE"),
    MONITOR_POWER_LINKAGE_DOES_NOT_LINK_G111: (0x6B2E, "OFF"),
}

POWER_SAVE_START_TIME_OFF_G111: str = "Off"
POWER_SAVE_START_TIME_30_MIN_G111: str = "30 Min"
POWER_SAVE_START_TIME_5_MIN_G111: str = "5 Min"
POWER_SAVE_START_TIME_2_MIN_G111: str = "2 Min"
POWER_SAVE_START_TIME_1_MIN_G111: str = "1 Min"
POWER_SAVE_START_TIME_10_SEC_G111: str = "10 Sec"
ALLOWED_POWER_SAVE_START_TIMES_G111: Tuple[str, ...] = (
    POWER_SAVE_START_TIME_OFF_G111,
    POWER_SAVE_START_TIME_30_MIN_G111,
    POWER_SAVE_START_TIME_5_MIN_G111,
    POWER_SAVE_START_TIME_2_MIN_G111,
    POWER_SAVE_START_TIME_1_MIN_G111,
    POWER_SAVE_START_TIME_10_SEC_G111,
)
POWER_SAVE_START_TIME_FACTORY_DEFAULT_G111: str = POWER_SAVE_START_TIME_5_MIN_G111
BATTERY_BENCH_SAFE_POWER_SAVE_TIMES_G111: Tuple[str, ...] = (
    POWER_SAVE_START_TIME_OFF_G111,
    POWER_SAVE_START_TIME_30_MIN_G111,
)

POWER_SAVE_9_DEACTIVATION_CONDITIONS_G111: Tuple[str, ...] = (
    "USB power supply",
    "slideshow playback",
    "FTP transfer",
    "movie recording",
    "PC connection",
    "TV/HDMI connection",
    "IR Remote Ctrl = On",
    "Bluetooth Rmt Ctrl = On",
    "streaming / Creators' Cloud upload",
)

AUTO_POWER_OFF_TEMP_STANDARD_G111: str = "Standard"
AUTO_POWER_OFF_TEMP_HIGH_G111: str = "High"
ALLOWED_AUTO_POWER_OFF_TEMP_MODES_G111: Tuple[str, ...] = (
    AUTO_POWER_OFF_TEMP_STANDARD_G111,
    AUTO_POWER_OFF_TEMP_HIGH_G111,
)
AUTO_POWER_OFF_TEMP_FACTORY_DEFAULT_G111: str = AUTO_POWER_OFF_TEMP_STANDARD_G111

BK_LANG_PROPERTY_ID_G111: int = 0x02CF019C
LANGUAGE_UXC_RESID16_G111: int = 0xE397
FX3_LANGUAGE_COUNT_G111: int = 34
FX6_LANGUAGE_COUNT_G111: int = 29
FX3_BK4_LANG_OFFSET_G111: int = 0x90FF0
FX3_BK4_LANG_WIDTH_BYTES_G111: int = 4
FX6_BK4_LANG_OFFSET_G111: int = 0x89242
FX6_BK4_LANG_WIDTH_BYTES_G111: int = 1
FX3_ALLLANG_BK_LANG_SEED_G111: int = 0x00
FX6_NTSC_BK_LANG_SEED_G111: int = 0x00
FX6_CN1_BK_LANG_SEED_G111: int = 0x19

LANGUAGE_OOB_PROMPT_DEFAULT_G111: str = "—"
LANGUAGE_CODE_EN_G111: str = "en"
LANGUAGE_CODE_SCHINESE_G111: str = "schinese"
LANGUAGE_CODE_TCHINESE_G111: str = "tchinese"
LANGUAGE_CODE_JAPANESE_G111: str = "japanese"
ALLOWED_STAGE_B_LANGUAGES_G111: Tuple[str, ...] = (
    LANGUAGE_CODE_EN_G111,
    LANGUAGE_CODE_SCHINESE_G111,
    LANGUAGE_CODE_TCHINESE_G111,
    LANGUAGE_CODE_JAPANESE_G111,
)

STAGE_B_4_LANGUAGE_PARITY_TABLE_G111: Dict[str, Dict[str, Any]] = {
    LANGUAGE_CODE_EN_G111: {
        "bk_lang_id": 0x00,
        "appfw_enum": "0x2b2f_LANGUAGE_ENGLISH",
        "switch_bank": 0,
        "font_str_pair": (4, 4),
        "ltt_font": "UniversOTS-SJ_wIcon.ltt",
        "fx3_f_uxc_bytes": 373_820,
        "fx3_uxc_bytes": 165_740,
        "fx6_uxc_bytes": 118_208,
    },
    LANGUAGE_CODE_SCHINESE_G111: {
        "bk_lang_id": 0x19,
        "appfw_enum": "0x2b45_CHINESE_SIMPLIFIED",
        "switch_bank": 23,
        "font_str_pair": (19, 19),
        "ltt_font": "MYingHeiC-GB18030-SJ_wIcon.ltt",
        "fx3_f_uxc_bytes": 322_652,
        "fx3_uxc_bytes": 149_064,
        "fx6_uxc_bytes": 118_644,
    },
    LANGUAGE_CODE_TCHINESE_G111: {
        "bk_lang_id": 0x18,
        "appfw_enum": "0x2b44_LANGUAGE_CHINESE_TRADITIONAL",
        "switch_bank": 27,
        "font_str_pair": (22, 22),
        "ltt_font": "MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
        "fx3_f_uxc_bytes": 324_148,
        "fx3_uxc_bytes": 151_908,
        "fx6_uxc_bytes": 119_168,
    },
    LANGUAGE_CODE_JAPANESE_G111: {
        "bk_lang_id": 0x01,
        "appfw_enum": "0x2b30_LANGUAGE_JAPANESE",
        "switch_bank": 1,
        "font_str_pair": (12, 12),
        "ltt_font": "HeiseiKakuGothW5-SJ_wIcon.ltt",
        "fx3_f_uxc_bytes": 447_840,
        "fx3_uxc_bytes": 208_564,
        "fx6_uxc_bytes": 141_692,
    },
}

# ---------------------------------------------------------------------------
# Gate G112 Constants: [Volume Settings], [4ch Audio Monitoring] & [Delete confirm.]
# ---------------------------------------------------------------------------

VOLUME_SETTINGS_MENU_PATH_G112: str = (
    "MENU -> Setup -> [Sound Option] -> [Volume Settings]"
)
AUDIO_MONITORING_4CH_MENU_PATH_G112: str = (
    "MENU -> Setup -> [Sound Option] -> [4ch Audio Monitoring]"
)
HDMI_4CH_AUDIO_OUTPUT_MENU_PATH_G112: str = (
    "MENU -> Setup -> [External Output] -> [HDMI Output Settings] -> [4ch Audio Output]"
)
DELETE_CONFIRM_MENU_PATH_G112: str = (
    "MENU -> Playback -> [Delete] -> [Delete confirm.]"
)
DELETE_PRESSING_TWICE_MENU_PATH_G112: str = (
    "MENU -> Playback -> [Delete] -> [Delete pressing twice]"
)

VOLUME_SETTINGS_RESID16_G112: int = 0xE8C9
VOLUME_SETTINGS_MIN_G112: int = 0
VOLUME_SETTINGS_MAX_G112: int = 15
VOLUME_SETTINGS_FACTORY_DEFAULT_G112: int = 7
ALLOWED_VOLUME_SETTINGS_G112: Tuple[int, ...] = tuple(
    range(VOLUME_SETTINGS_MIN_G112, VOLUME_SETTINGS_MAX_G112 + 1)
)
XLR_H1_INTERNAL_SPEAKER_SAFE_MAX_VOLUME_G112: int = 7

AUDIO_MON_CH1_CH2_G112: str = "CH1/CH2"
AUDIO_MON_CH3_CH4_G112: str = "CH3/CH4"
AUDIO_MON_CH1_3_CH2_4_G112: str = "CH1+3/CH2+4"
AUDIO_MON_CH1_CH1_G112: str = "CH1/CH1"
AUDIO_MON_CH2_CH2_G112: str = "CH2/CH2"
ALLOWED_4CH_AUDIO_MONITORING_ROUTES_G112: Tuple[str, ...] = (
    AUDIO_MON_CH1_CH2_G112,
    AUDIO_MON_CH3_CH4_G112,
    AUDIO_MON_CH1_3_CH2_4_G112,
    AUDIO_MON_CH1_CH1_G112,
    AUDIO_MON_CH2_CH2_G112,
)
AUDIO_MON_FACTORY_DEFAULT_G112: str = AUDIO_MON_CH1_CH2_G112
AUDIO_MON_ROUTE_METADATA_G112: Dict[str, Tuple[str, int, str, str]] = {
    AUDIO_MON_CH1_CH2_G112: ("AUDIO_MONITORING_CH_1CH_2CH", 0x713B, "CH1", "CH2"),
    AUDIO_MON_CH3_CH4_G112: ("AUDIO_MONITORING_CH_3CH_4CH", 0x6BF6, "CH3", "CH4"),
    AUDIO_MON_CH1_3_CH2_4_G112: (
        "AUDIO_MONITORING_CH_MIX_ALL",
        0x6C2E,
        "CH1+CH3",
        "CH2+CH4",
    ),
    AUDIO_MON_CH1_CH1_G112: ("AUDIO_MONITORING_CH_1CH", 0x6F9C, "CH1", "CH1"),
    AUDIO_MON_CH2_CH2_G112: ("AUDIO_MONITORING_CH_2CH", 0x7A26, "CH2", "CH2"),
}
HEADPHONE_35MM_MAX_DISCRETE_CHANNELS_G112: int = 2
HDMI_4CH_AUDIO_OUTPUT_ROUTES_G112: Tuple[str, str] = ("CH1/CH2", "CH3/CH4")
HDMI_4CH_AUDIO_OUTPUT_RESID16_G112: int = 0x6AA0

DELETE_CONFIRM_CANCEL_FIRST_G112: str = '"Cancel" first'
DELETE_CONFIRM_DELETE_FIRST_G112: str = '"Delete" first'
ALLOWED_DELETE_CONFIRM_MODES_G112: Tuple[str, ...] = (
    DELETE_CONFIRM_CANCEL_FIRST_G112,
    DELETE_CONFIRM_DELETE_FIRST_G112,
)
DELETE_CONFIRM_FACTORY_DEFAULT_G112: str = DELETE_CONFIRM_CANCEL_FIRST_G112
DELETE_CONFIRM_RESID16_MAP_G112: Dict[str, Tuple[int, int, str]] = {
    DELETE_CONFIRM_CANCEL_FIRST_G112: (
        0xE724,
        0x6A5E,
        "VAL_setting_delete_confirm_DELETE_CONFIRM_CANCEL_FIRST",
    ),
    DELETE_CONFIRM_DELETE_FIRST_G112: (
        0xE725,
        0x6E0A,
        "VAL_setting_delete_confirm_DELETE_CONFIRM_DELETE_FIRST",
    ),
}

DELETE_PRESSING_TWICE_OFF_G112: str = "Off"
DELETE_PRESSING_TWICE_ON_G112: str = "On"
ALLOWED_DELETE_PRESSING_TWICE_MODES_G112: Tuple[str, ...] = (
    DELETE_PRESSING_TWICE_OFF_G112,
    DELETE_PRESSING_TWICE_ON_G112,
)
DELETE_PRESSING_TWICE_FACTORY_DEFAULT_G112: str = DELETE_PRESSING_TWICE_OFF_G112
DELETE_PRESSING_TWICE_RESID16_G112: int = 0x74DB

MEDIA_OP_NONE_G112: str = "NONE"
MEDIA_OP_DELETE_SINGLE_G112: str = "DELETE_SINGLE"
MEDIA_OP_DELETE_MULTIPLE_G112: str = "DELETE_MULTIPLE"
MEDIA_OP_DELETE_FOLDER_G112: str = "DELETE_FOLDER"
MEDIA_OP_DELETE_DATE_G112: str = "DELETE_DATE"
MEDIA_OP_DELETE_PRESSING_TWICE_G112: str = "DELETE_PRESSING_TWICE"
MEDIA_OP_FORMAT_QUICK_G112: str = "FORMAT_QUICK"
MEDIA_OP_FORMAT_FULL_G112: str = "FORMAT_FULL"
ALLOWED_MEDIA_OPS_G112: Tuple[str, ...] = (
    MEDIA_OP_NONE_G112,
    MEDIA_OP_DELETE_SINGLE_G112,
    MEDIA_OP_DELETE_MULTIPLE_G112,
    MEDIA_OP_DELETE_FOLDER_G112,
    MEDIA_OP_DELETE_DATE_G112,
    MEDIA_OP_DELETE_PRESSING_TWICE_G112,
    MEDIA_OP_FORMAT_QUICK_G112,
    MEDIA_OP_FORMAT_FULL_G112,
)

TARGET_SLOT_NONE_G112: str = "NONE"
TARGET_SLOT_1_G112: str = "Slot 1"
TARGET_SLOT_2_G112: str = "Slot 2"
ALLOWED_TARGET_SLOTS_G112: Tuple[str, ...] = (
    TARGET_SLOT_NONE_G112,
    TARGET_SLOT_1_G112,
    TARGET_SLOT_2_G112,
)

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, Targeted Pread on appFw.so, <0.20s)
# ---------------------------------------------------------------------------

PINNED_APPFW_SLICES_PHASE273: Tuple[Tuple[int, bytes], ...] = (
    (0, b"\x7fELF"),
    (62_701_414, b"BKID_APP_setting_monitor_power_linkage"),
    (62_996_724, b"EXTERN_VAL_MONITOR_POWER_LINKAGE_ON_ALL"),
    (62_701_378, b"BKID_APP_setting_start_power_saving"),
    (62_694_807, b"BKID_APP_setting_language"),
    (62_701_525, b"BKID_APP_setting_volume_settings"),
    (49_971_386, b"VOLUME_SETTINGS_0"),
    (49_971_110, b"VOLUME_SETTINGS_15"),
    (62_701_558, b"BKID_APP_setting_audio_monitoring_ch"),
    (49_971_404, b"AUDIO_MONITORING_CH_1CH_2CH"),
    (49_971_460, b"AUDIO_MONITORING_CH_MIX_ALL"),
    (62_702_125, b"BKID_APP_setting_4ch_output_ch"),
    (62_691_828, b"BKID_APP_setting_delete_confirm"),
    (62_193_553, b"VAL_setting_delete_confirm_DELETE_CONFIRM_CANCEL_FIRST"),
    (62_193_498, b"VAL_setting_delete_confirm_DELETE_CONFIRM_DELETE_FIRST"),
    (62_691_788, b"BKID_APP_setting_delete_by_delete_twice"),
)
PINNED_APPFW_SLICES_SHA256_PHASE273: str = (
    "8724dfd01427cb55f9f9e85f462fa49864ead445ee68d766fb3061a3cb4b073e"
)
PINNED_APPFW_FULL_SHA256_PHASE273: str = (
    "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f"
)

PINNED_PHASE273_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_APPFW_SLICES_SHA256_PHASE273,
        tuple(tok for _off, tok in PINNED_APPFW_SLICES_PHASE273),
        "FX3_APPFW_WAVE46_MONITOR_LINKAGE_LANG_VOL_4CH_DEL_SLICES",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Power Save by Monitor",
            b"Both Linked",
            b"Open: Return",
            b"Close: Power Save",
            b"Does Not Link",
            b"4ch Audio Monitoring",
            b"CH1+3/CH2+4",
            b'"Cancel" first',
            b'"Delete" first',
            b"Delete pressing twice",
        ),
        "FX3_UXC_F_MONITOR_4CH_DELETE_STRINGS",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (
            b"Language",
            b"Volume Settings",
            b"Delete confirm.",
            b'"Cancel" first',
            b'"Delete" first',
        ),
        "FX3_UXC_LANG_VOLUME_DELETE_CONFIRM_STRINGS",
    ),
    "fx3_libsaveloadsettings_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (
            b"\x7fELF",
            b"Backup_get_datasize",
            b"Backup_read",
            b"Backup_write",
            b"requestToRead",
            b"requestToWrite",
        ),
        "FX3_LIBSAVELOADSETTINGS_SETUP_PLAYBACK_RESET_ELF",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4\x00", b"ILME-FX3"),
        "FX3_BK4_ALLLANG_BK_LANG_0X02CF019C_SEED",
    ),
    "fx6_bk4_ntsc_bin": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4\x00",),
        "FX6_BK4_NTSC_BK_LANG_0X00_SEED",
    ),
    "fx6_bk4_cn1_bin": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95899_CN1.bin",
        2_253_333,
        "0c98d1ad9035f0f56a60462efe0d0440c6b29d5584fd3f1e8ffd6a59366f0a28",
        (b"BK4\x00",),
        "FX6_BK4_CN1_BK_LANG_0X19_SEED",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (b"Language Select", b"Monitor CH", b"Delete Clip?"),
        "FX6_UXC_LANGUAGE_SELECT_MONITOR_CH_DELETE_CLIP",
    ),
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase273DonorAuditResult:
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
    fx3_bk_lang_seed_value: int
    fx6_ntsc_bk_lang_seed_value: int
    fx6_cn1_bk_lang_seed_value: int
    spoof_open_on_close_off_absent_in_uxc: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PowerSaveMonitorAndLanguageGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    reset_action: str
    power_setting_option_menu_path: str
    power_save_start_time_menu_path: str
    auto_power_off_temp_menu_path: str
    language_menu_path: str
    fx3_ui_exposes_power_save_by_monitor: bool
    power_setting_option_items: Tuple[str, ...]
    power_save_monitor_ui_spoof_events: int
    appfw_monitor_power_linkage_modes: Tuple[str, ...]
    monitor_power_linkage_audit_active: bool
    audit_body_model: str
    pre_reset_monitor_power_linkage: str
    effective_post_reset_monitor_power_linkage: str
    lcd_folded_inward_headless_hdmi: bool
    headless_monitor_close_sleep_events: int
    pre_reset_power_save_start_time: str
    effective_post_reset_power_save_start_time: str
    pre_reset_auto_power_off_temp: str
    effective_post_reset_auto_power_off_temp: str
    nine_deactivation_conditions: Tuple[str, ...]
    active_deactivation_conditions: Tuple[str, ...]
    power_save_bypass_active: bool
    air_gapped_battery_bench: bool
    battery_bench_idle_sleep_events: int
    bk_lang_property_id_hex: str
    fx3_language_count: int
    fx6_language_count: int
    selected_stage_b_language: str
    pre_reset_language: str
    effective_post_reset_language: str
    stage_b_4lang_parity_verified: bool
    setup_items_survive_camera_settings_and_network_reset: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G111PowerSaveMonitorAndLanguageGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    power_save_monitor_language_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Volume4chMonDeleteConfirmGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    reset_action: str
    volume_settings_menu_path: str
    audio_monitoring_4ch_menu_path: str
    hdmi_4ch_audio_output_menu_path: str
    delete_confirm_menu_path: str
    delete_pressing_twice_menu_path: str
    pre_reset_volume_setting: int
    effective_post_reset_volume_setting: int
    audio_signals_conflated: bool
    xlr_h1_mic_active: bool
    headphones_connected: bool
    internal_speaker_active: bool
    xlr_acoustic_feedback_events: int
    pre_reset_4ch_audio_monitoring: str
    effective_post_reset_4ch_audio_monitoring: str
    hdmi_4ch_audio_output: str
    headphone_35mm_output_channels: int
    discrete_4ch_35mm_claimed: bool
    pre_reset_delete_confirm: str
    effective_post_reset_delete_confirm: str
    pre_reset_delete_pressing_twice: str
    effective_post_reset_delete_pressing_twice: str
    slot1_holds_recovery_vault: bool
    slot1_format_hard_locked: bool
    requested_media_op: str
    target_slot: str
    slot1_vault_delete_events: int
    setup_playback_reset_contract_verified: bool
    matrix_states_checked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G112Volume4chMonDeleteConfirmGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    volume_4chmon_delete_confirm_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master112GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_109_gates_verified: bool
    all_112_gates_verified: bool
    g13_to_g112_all_passed: bool
    g111_to_g112_all_passed: bool
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
    master_110_report: Dict[str, Any]
    g111_result: Dict[str, Any]
    g112_result: Dict[str, Any]
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
    for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE273):
        if os.environ.get(env_key, "").strip() in _TRUTHY_CLEAN_ROOM_TOKENS:
            return True
    return False


def _default_donor_budget_seconds_phase273() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return DONOR_CHECK_CI_MAX_SECONDS_PHASE273
    return DONOR_CHECK_MAX_SECONDS_PHASE273


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


def _read_targeted_slices_o_rdonly(
    path: Path, slices_spec: Sequence[Tuple[int, bytes]]
) -> Tuple[int, str, bool]:
    """Read targeted byte slices via `os.open(..., os.O_RDONLY)` + `os.pread`
    (with `os.lseek`/`os.read` fallback on platforms lacking `os.pread`) so large
    79 MiB shared `appFw.so` binaries are audited in < 1 ms without full hashing.
    """
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    fd = os.open(str(path), flags)
    try:
        st = os.fstat(fd)
        file_size = int(st.st_size)
        chunks: List[bytes] = []
        all_matched = True
        pread_fn = getattr(os, "pread", None)
        for offset, token in slices_spec:
            if offset + len(token) > file_size:
                all_matched = False
                chunks.append(b"")
                continue
            if pread_fn is not None:
                chunk = pread_fn(fd, len(token), offset)
            else:
                os.lseek(fd, offset, os.SEEK_SET)
                chunk = os.read(fd, len(token))
            chunks.append(chunk)
            if chunk != token:
                all_matched = False
        slice_sha = hashlib.sha256(b"".join(chunks)).hexdigest()
        return file_size, slice_sha, all_matched
    finally:
        os.close(fd)


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


def _norm_reset_action_phase273(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE273
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE
    return None


def _norm_on_off_phase273(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u == "ON":
        return "On"
    if u == "OFF":
        return "Off"
    return None


def _norm_monitor_power_linkage_g111(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip().strip("[]")
    if cleaned == SPOOF_FAKE_MONITOR_MODE_G111:
        return None
    u = re.sub(r"\s+", " ", cleaned.replace("_", " ")).upper()
    mapping = {
        "BOTH LINKED": MONITOR_POWER_LINKAGE_BOTH_LINKED_G111,
        "ON ALL": MONITOR_POWER_LINKAGE_BOTH_LINKED_G111,
        "OPEN: RETURN": MONITOR_POWER_LINKAGE_OPEN_RETURN_G111,
        "OPEN:RETURN": MONITOR_POWER_LINKAGE_OPEN_RETURN_G111,
        "ON OPEN": MONITOR_POWER_LINKAGE_OPEN_RETURN_G111,
        "CLOSE: POWER SAVE": MONITOR_POWER_LINKAGE_CLOSE_POWER_SAVE_G111,
        "CLOSE:POWER SAVE": MONITOR_POWER_LINKAGE_CLOSE_POWER_SAVE_G111,
        "ON CLOSE": MONITOR_POWER_LINKAGE_CLOSE_POWER_SAVE_G111,
        "DOES NOT LINK": MONITOR_POWER_LINKAGE_DOES_NOT_LINK_G111,
        "OFF": MONITOR_POWER_LINKAGE_DOES_NOT_LINK_G111,
    }
    return mapping.get(u)


def _norm_power_save_start_time_g111(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    mapping = {
        "OFF": POWER_SAVE_START_TIME_OFF_G111,
        "30 MIN": POWER_SAVE_START_TIME_30_MIN_G111,
        "30MIN": POWER_SAVE_START_TIME_30_MIN_G111,
        "5 MIN": POWER_SAVE_START_TIME_5_MIN_G111,
        "5MIN": POWER_SAVE_START_TIME_5_MIN_G111,
        "2 MIN": POWER_SAVE_START_TIME_2_MIN_G111,
        "2MIN": POWER_SAVE_START_TIME_2_MIN_G111,
        "1 MIN": POWER_SAVE_START_TIME_1_MIN_G111,
        "1MIN": POWER_SAVE_START_TIME_1_MIN_G111,
        "10 SEC": POWER_SAVE_START_TIME_10_SEC_G111,
        "10SEC": POWER_SAVE_START_TIME_10_SEC_G111,
    }
    return mapping.get(u)


def _norm_auto_power_off_temp_g111(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").upper()
    if u == "STANDARD":
        return AUTO_POWER_OFF_TEMP_STANDARD_G111
    if u == "HIGH":
        return AUTO_POWER_OFF_TEMP_HIGH_G111
    return None


def _norm_stage_b_language_g111(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = raw.strip().strip("[]").lower()
    mapping = {
        "en": LANGUAGE_CODE_EN_G111,
        "english": LANGUAGE_CODE_EN_G111,
        "schinese": LANGUAGE_CODE_SCHINESE_G111,
        "simplifiedchinese": LANGUAGE_CODE_SCHINESE_G111,
        "zh-cn": LANGUAGE_CODE_SCHINESE_G111,
        "tchinese": LANGUAGE_CODE_TCHINESE_G111,
        "traditionalchinese": LANGUAGE_CODE_TCHINESE_G111,
        "zh-tw": LANGUAGE_CODE_TCHINESE_G111,
        "japanese": LANGUAGE_CODE_JAPANESE_G111,
        "ja": LANGUAGE_CODE_JAPANESE_G111,
        "—": LANGUAGE_OOB_PROMPT_DEFAULT_G111,
        "-": LANGUAGE_OOB_PROMPT_DEFAULT_G111,
    }
    return mapping.get(u)


def _norm_4ch_audio_monitoring_g112(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    mapping = {
        "CH1/CH2": AUDIO_MON_CH1_CH2_G112,
        "CH3/CH4": AUDIO_MON_CH3_CH4_G112,
        "CH1+3/CH2+4": AUDIO_MON_CH1_3_CH2_4_G112,
        "CH1/CH1": AUDIO_MON_CH1_CH1_G112,
        "CH2/CH2": AUDIO_MON_CH2_CH2_G112,
    }
    return mapping.get(u)


def _norm_hdmi_4ch_audio_output_g112(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    if u == "CH1/CH2":
        return "CH1/CH2"
    if u == "CH3/CH4":
        return "CH3/CH4"
    return None


def _norm_delete_confirm_g112(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]")).lower()
    if u in ('"cancel" first', "cancel first"):
        return DELETE_CONFIRM_CANCEL_FIRST_G112
    if u in ('"delete" first', "delete first"):
        return DELETE_CONFIRM_DELETE_FIRST_G112
    return None


def _norm_media_op_g112(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "_", raw.strip().strip("[]")).upper()
    if u in ALLOWED_MEDIA_OPS_G112:
        return u
    return None


def _norm_target_slot_g112(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    mapping = {
        "NONE": TARGET_SLOT_NONE_G112,
        "": TARGET_SLOT_NONE_G112,
        "SLOT1": TARGET_SLOT_1_G112,
        "SLOT_1": TARGET_SLOT_1_G112,
        "SLOTA": TARGET_SLOT_1_G112,
        "SLOT2": TARGET_SLOT_2_G112,
        "SLOT_2": TARGET_SLOT_2_G112,
        "SLOTB": TARGET_SLOT_2_G112,
    }
    return mapping.get(u)


# ---------------------------------------------------------------------------
# 1. Fast `< 0.20s` O_RDONLY Donor Contract Audit (`Phase 273`)
# ---------------------------------------------------------------------------


def audit_phase273_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: Optional[float] = None,
) -> Phase273DonorAuditResult:
    """Inspect local FX3 Ver. 7.02 / FX6 Ver. 6.01 donor artifacts strictly via
    `os.open(..., os.O_RDONLY)` within `<0.20s` (`1.00s` under
    `GITHUB_ACTIONS=true`), using targeted `os.pread` slices on the 79 MiB
    `appFw.so` and full `O_RDONLY` SHA-256 verification on `.uxc`,
    `libSaveLoadSettings.so`, and `BK4` seeds (`FX3-CX95900_ALLLANG-Backup.bin`
    `0x90ff0=0`, `CX95898_NTSC.bin` `0x89242=0x00`, `CX95899_CN1.bin`
    `0x89242=0x19`), with deterministic `CLEAN_ROOM_SYNTHETIC` fallback.
    """
    t0 = time.perf_counter()
    budget = (
        _default_donor_budget_seconds_phase273()
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE273_DONOR_SPECS.items():
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
            spec[5] for spec in PINNED_PHASE273_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE273_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE273_DONOR_SPECS.items()}
        return Phase273DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE273_DONOR_INTEGRITY
            ),
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_CLEAN_ROOM",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_200ms=within_budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=synthetic_markers,
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            fx3_bk_lang_seed_value=FX3_ALLLANG_BK_LANG_SEED_G111,
            fx6_ntsc_bk_lang_seed_value=FX6_NTSC_BK_LANG_SEED_G111,
            fx6_cn1_bk_lang_seed_value=FX6_CN1_BK_LANG_SEED_G111,
            spoof_open_on_close_off_absent_in_uxc=True,
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

    fx3_bk_lang_val = -1
    fx6_ntsc_lang_val = -1
    fx6_cn1_lang_val = -1
    spoof_absent_in_uxc = False

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE273_DONOR_SPECS.items():
        fp = resolved[key]
        if key == "fx3_appfw_so":
            try:
                actual_size, actual_sha, slices_ok = _read_targeted_slices_o_rdonly(
                    fp, PINNED_APPFW_SLICES_PHASE273
                )
                files_inspected += 1
            except OSError as exc:
                missing.append(marker_label)
                errors.append(f"O_RDONLY targeted pread failed for {key}: {exc}")
                continue
            sizes[key] = actual_size
            shas[key] = actual_sha
            size_ok = actual_size == exp_size
            sha_ok = actual_sha == exp_sha
            markers_ok = bool(slices_ok)
            extra_ok = True
        else:
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
            extra_ok = True

            if key == "fx3_string_english_f_uxc":
                spoof_absent_in_uxc = SPOOF_FAKE_MONITOR_MODE_G111.encode("utf-8") not in blob
                if not spoof_absent_in_uxc:
                    extra_ok = False
                    errors.append(
                        f"Unexpected spoof string {SPOOF_FAKE_MONITOR_MODE_G111!r} found in {key}."
                    )
            elif key == "fx3_bk4_bin":
                if len(blob) >= FX3_BK4_LANG_OFFSET_G111 + FX3_BK4_LANG_WIDTH_BYTES_G111:
                    fx3_bk_lang_val = int.from_bytes(
                        blob[
                            FX3_BK4_LANG_OFFSET_G111 : FX3_BK4_LANG_OFFSET_G111
                            + FX3_BK4_LANG_WIDTH_BYTES_G111
                        ],
                        "little",
                    )
                    if fx3_bk_lang_val != FX3_ALLLANG_BK_LANG_SEED_G111:
                        extra_ok = False
                        errors.append(
                            f"FX3 BK_LANG @ 0x{FX3_BK4_LANG_OFFSET_G111:x} mismatch: got {fx3_bk_lang_val}."
                        )
                else:
                    extra_ok = False
                    errors.append("FX3 BK4 bin truncated before BK_LANG offset.")
            elif key == "fx6_bk4_ntsc_bin":
                if len(blob) > FX6_BK4_LANG_OFFSET_G111:
                    fx6_ntsc_lang_val = blob[FX6_BK4_LANG_OFFSET_G111]
                    if fx6_ntsc_lang_val != FX6_NTSC_BK_LANG_SEED_G111:
                        extra_ok = False
                        errors.append(
                            f"FX6 NTSC BK_LANG @ 0x{FX6_BK4_LANG_OFFSET_G111:x} mismatch: got 0x{fx6_ntsc_lang_val:02x}."
                        )
                else:
                    extra_ok = False
                    errors.append("FX6 NTSC BK4 bin truncated before BK_LANG offset.")
            elif key == "fx6_bk4_cn1_bin":
                if len(blob) > FX6_BK4_LANG_OFFSET_G111:
                    fx6_cn1_lang_val = blob[FX6_BK4_LANG_OFFSET_G111]
                    if fx6_cn1_lang_val != FX6_CN1_BK_LANG_SEED_G111:
                        extra_ok = False
                        errors.append(
                            f"FX6 CN1 BK_LANG @ 0x{FX6_BK4_LANG_OFFSET_G111:x} mismatch: got 0x{fx6_cn1_lang_val:02x}."
                        )
                else:
                    extra_ok = False
                    errors.append("FX6 CN1 BK4 bin truncated before BK_LANG offset.")

        if not size_ok:
            errors.append(
                f"Donor size mismatch for {key}: got {actual_size}, expected {exp_size}."
            )
        if not sha_ok:
            errors.append(
                f"Donor SHA-256 mismatch for {key}: got {actual_sha}, expected {exp_sha}."
            )
        if not markers_ok:
            errors.append(f"Missing required Wave-46 byte markers in {key}.")

        if size_ok and sha_ok and markers_ok and extra_ok:
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

    fx3_keys = {k for k, v in PINNED_PHASE273_DONOR_SPECS.items() if v[0] == "FX3"}
    fx6_keys = {k for k, v in PINNED_PHASE273_DONOR_SPECS.items() if v[0] == "FX6"}
    fx3_ok = fx3_keys.issubset(passed_keys)
    fx6_ok = fx6_keys.issubset(passed_keys)
    valid = (
        fx3_ok
        and fx6_ok
        and spoof_absent_in_uxc
        and (not missing)
        and within_budget
        and (not errors)
    )

    return Phase273DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE
        if valid
        else STATUS_BLOCKED_PHASE273_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_200ms=within_budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_ok,
        fx6_contracts_verified=fx6_ok,
        fx3_bk_lang_seed_value=fx3_bk_lang_val,
        fx6_ntsc_bk_lang_seed_value=fx6_ntsc_lang_val,
        fx6_cn1_bk_lang_seed_value=fx6_cn1_lang_val,
        spoof_open_on_close_off_absent_in_uxc=spoof_absent_in_uxc,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate G111: [Power Save by Monitor] Split, 9-Bypass Start Time & [Language]
# ---------------------------------------------------------------------------


def compute_power_save_monitor_and_language_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate 192 states across the 4 `appFw.so`
    `BKID_APP_setting_monitor_power_linkage` modes, 6 `[Power Save Start Time]`
    options, 4 reset actions, and 2 bench postures (headless LCD-closed HDMI vs
    air-gapped battery bench).
    """
    states_checked = 0
    setup_reset_corruptions = 0
    headless_unsafe_modes_detected = 0
    battery_bench_unsafe_times_detected = 0

    for mon_mode in ALLOWED_MONITOR_POWER_LINKAGE_MODES_G111:
        for pss_time in ALLOWED_POWER_SAVE_START_TIMES_G111:
            for r_act in ALLOWED_RESET_ACTIONS_PHASE273:
                for air_gapped in (False, True):
                    resolved = resolve_fx3_power_save_monitor_and_language_state(
                        reset_action=r_act,
                        pre_reset_monitor_power_linkage=mon_mode,
                        pre_reset_power_save_start_time=pss_time,
                        pre_reset_auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH_G111,
                        pre_reset_language=LANGUAGE_CODE_SCHINESE_G111,
                        air_gapped_battery_bench=air_gapped,
                        active_deactivation_conditions=(
                            () if air_gapped else ("TV/HDMI connection",)
                        ),
                    )
                    states_checked += 1
                    survives = r_act in (
                        RESET_ACTION_NONE,
                        RESET_ACTION_CAMERA_SETTINGS_RESET,
                        RESET_ACTION_RESET_NETWORK_SET_PHASE273,
                    )
                    if survives and (
                        resolved["effective_post_reset_monitor_power_linkage"]
                        != mon_mode
                        or resolved["effective_post_reset_power_save_start_time"]
                        != pss_time
                        or resolved["effective_post_reset_language"]
                        != LANGUAGE_CODE_SCHINESE_G111
                    ):
                        setup_reset_corruptions += 1
                    if r_act == RESET_ACTION_INITIALIZE and (
                        resolved["effective_post_reset_monitor_power_linkage"]
                        != MONITOR_POWER_LINKAGE_FACTORY_DEFAULT_G111
                        or resolved["effective_post_reset_power_save_start_time"]
                        != POWER_SAVE_START_TIME_FACTORY_DEFAULT_G111
                        or resolved["effective_post_reset_language"]
                        != LANGUAGE_OOB_PROMPT_DEFAULT_G111
                    ):
                        setup_reset_corruptions += 1
                    if (
                        resolved["effective_post_reset_monitor_power_linkage"]
                        not in SAFE_HEADLESS_MONITOR_POWER_LINKAGE_MODES_G111
                    ):
                        headless_unsafe_modes_detected += 1
                    if (
                        air_gapped
                        and resolved["effective_post_reset_power_save_start_time"]
                        not in BATTERY_BENCH_SAFE_POWER_SAVE_TIMES_G111
                    ):
                        battery_bench_unsafe_times_detected += 1

    return {
        "states_checked": states_checked,
        "setup_reset_corruptions": setup_reset_corruptions,
        "headless_unsafe_modes_detected": headless_unsafe_modes_detected,
        "battery_bench_unsafe_times_detected": battery_bench_unsafe_times_detected,
        "all_invariants_hold": (
            states_checked == 192 and setup_reset_corruptions == 0
        ),
    }


def resolve_fx3_power_save_monitor_and_language_state(
    *,
    reset_action: str = RESET_ACTION_NONE,
    pre_reset_monitor_power_linkage: str = MONITOR_POWER_LINKAGE_DOES_NOT_LINK_G111,
    pre_reset_power_save_start_time: str = POWER_SAVE_START_TIME_OFF_G111,
    pre_reset_auto_power_off_temp: str = AUTO_POWER_OFF_TEMP_FACTORY_DEFAULT_G111,
    pre_reset_language: str = LANGUAGE_CODE_EN_G111,
    air_gapped_battery_bench: bool = False,
    active_deactivation_conditions: Sequence[str] = ("TV/HDMI connection",),
) -> Dict[str, Any]:
    r_act = _norm_reset_action_phase273(reset_action) or RESET_ACTION_NONE
    mon_mode = (
        _norm_monitor_power_linkage_g111(pre_reset_monitor_power_linkage)
        or MONITOR_POWER_LINKAGE_DOES_NOT_LINK_G111
    )
    pss_time = (
        _norm_power_save_start_time_g111(pre_reset_power_save_start_time)
        or POWER_SAVE_START_TIME_OFF_G111
    )
    auto_temp = (
        _norm_auto_power_off_temp_g111(pre_reset_auto_power_off_temp)
        or AUTO_POWER_OFF_TEMP_FACTORY_DEFAULT_G111
    )
    lang = _norm_stage_b_language_g111(pre_reset_language) or LANGUAGE_CODE_EN_G111

    # All items under (Setup) -> [Power Setting Option] and [Area/Date] -> [Language]
    # survive BOTH [Camera Settings Reset] and [Reset Network Set.], restoring
    # defaults / OOB language prompt ONLY on [Initialize].
    initialized = r_act == RESET_ACTION_INITIALIZE
    eff_mon_mode = (
        MONITOR_POWER_LINKAGE_FACTORY_DEFAULT_G111 if initialized else mon_mode
    )
    eff_pss_time = (
        POWER_SAVE_START_TIME_FACTORY_DEFAULT_G111 if initialized else pss_time
    )
    eff_auto_temp = (
        AUTO_POWER_OFF_TEMP_FACTORY_DEFAULT_G111 if initialized else auto_temp
    )
    eff_lang = LANGUAGE_OOB_PROMPT_DEFAULT_G111 if initialized else lang

    active_bypasses = tuple(active_deactivation_conditions)
    bypass_active = bool(active_bypasses) and not air_gapped_battery_bench

    return {
        "reset_action": r_act,
        "effective_post_reset_monitor_power_linkage": eff_mon_mode,
        "effective_post_reset_power_save_start_time": eff_pss_time,
        "effective_post_reset_auto_power_off_temp": eff_auto_temp,
        "effective_post_reset_language": eff_lang,
        "active_deactivation_conditions": active_bypasses,
        "power_save_bypass_active": bypass_active,
    }


def verify_power_save_monitor_and_language_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE273,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE273,
    reset_action: str = RESET_ACTION_NONE,
    claimed_fx3_ui_exposes_power_save_by_monitor: bool = False,
    claimed_power_setting_option_items: Sequence[str] = (
        FX3_POWER_SETTING_OPTION_EXACT_2_ITEMS_G111
    ),
    claimed_power_save_monitor_spoof_events: int = 0,
    monitor_power_linkage_audit_active: bool = False,
    audit_body_model: str = FX3_MODEL_NAME,
    pre_reset_monitor_power_linkage: str = MONITOR_POWER_LINKAGE_DOES_NOT_LINK_G111,
    claimed_post_reset_monitor_power_linkage: Optional[str] = None,
    lcd_folded_inward_headless_hdmi: bool = True,
    claimed_headless_monitor_close_sleep_events: int = 0,
    pre_reset_power_save_start_time: str = POWER_SAVE_START_TIME_OFF_G111,
    claimed_post_reset_power_save_start_time: Optional[str] = None,
    pre_reset_auto_power_off_temp: str = AUTO_POWER_OFF_TEMP_FACTORY_DEFAULT_G111,
    claimed_post_reset_auto_power_off_temp: Optional[str] = None,
    active_deactivation_conditions: Sequence[str] = ("TV/HDMI connection",),
    air_gapped_battery_bench: bool = False,
    claimed_battery_bench_idle_sleep_events: int = 0,
    bk_lang_property_id: int = BK_LANG_PROPERTY_ID_G111,
    fx3_language_count: int = FX3_LANGUAGE_COUNT_G111,
    fx6_language_count: int = FX6_LANGUAGE_COUNT_G111,
    selected_stage_b_language: str = LANGUAGE_CODE_EN_G111,
    claimed_post_reset_language: Optional[str] = None,
    claimed_stage_b_4lang_parity_verified: bool = True,
) -> PowerSaveMonitorAndLanguageGuardResult:
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME
        or isinstance(body_model_id, bool)
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE273
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G111_TELEMETRY_INVALID)
        errors.append(
            "Gate G111 requires ILME-FX3 (0x91030080, Help Guide ilc/2210, Ver. 7.02)."
        )

    norm_reset = _norm_reset_action_phase273(reset_action)
    norm_pss_time = _norm_power_save_start_time_g111(pre_reset_power_save_start_time)
    norm_auto_temp = _norm_auto_power_off_temp_g111(pre_reset_auto_power_off_temp)
    norm_lang = _norm_stage_b_language_g111(selected_stage_b_language)

    # Check spoof before generic enum invalid so spoofed "Open: On/Close: Off"
    # deterministically yields STATUS_BLOCKED_G111_POWER_SAVE_MONITOR_UI_SPOOF_VIOLATION.
    spoof_events = (
        claimed_power_save_monitor_spoof_events
        if isinstance(claimed_power_save_monitor_spoof_events, int)
        and not isinstance(claimed_power_save_monitor_spoof_events, bool)
        else 1
    )
    spoof_string_hit = (
        isinstance(pre_reset_monitor_power_linkage, str)
        and pre_reset_monitor_power_linkage.strip().strip("[]")
        == SPOOF_FAKE_MONITOR_MODE_G111
    ) or (
        isinstance(claimed_post_reset_monitor_power_linkage, str)
        and claimed_post_reset_monitor_power_linkage.strip().strip("[]")
        == SPOOF_FAKE_MONITOR_MODE_G111
    )
    if spoof_string_hit:
        spoof_events = max(1, spoof_events)

    norm_mon_mode = _norm_monitor_power_linkage_g111(pre_reset_monitor_power_linkage)

    if (
        norm_reset is None
        or (norm_mon_mode is None and not spoof_string_hit)
        or norm_pss_time is None
        or norm_auto_temp is None
        or norm_lang is None
        or not isinstance(claimed_fx3_ui_exposes_power_save_by_monitor, bool)
        or not isinstance(monitor_power_linkage_audit_active, bool)
        or not isinstance(audit_body_model, str)
        or not audit_body_model.strip()
        or not isinstance(lcd_folded_inward_headless_hdmi, bool)
        or not isinstance(air_gapped_battery_bench, bool)
        or not isinstance(claimed_stage_b_4lang_parity_verified, bool)
        or isinstance(bk_lang_property_id, bool)
        or not isinstance(bk_lang_property_id, int)
        or isinstance(fx3_language_count, bool)
        or not isinstance(fx3_language_count, int)
        or isinstance(fx6_language_count, bool)
        or not isinstance(fx6_language_count, int)
    ):
        _add_code(codes, STATUS_BLOCKED_G111_TELEMETRY_INVALID)
        errors.append("Invalid or unrecognized G111 telemetry or enum value.")

    for int_val, name in (
        (claimed_power_save_monitor_spoof_events, "claimed_power_save_monitor_spoof_events"),
        (
            claimed_headless_monitor_close_sleep_events,
            "claimed_headless_monitor_close_sleep_events",
        ),
        (claimed_battery_bench_idle_sleep_events, "claimed_battery_bench_idle_sleep_events"),
    ):
        if isinstance(int_val, bool) or not isinstance(int_val, int) or int_val < 0:
            _add_code(codes, STATUS_BLOCKED_G111_TELEMETRY_INVALID)
            errors.append(f"{name} must be a non-negative integer.")

    # Validate active deactivation conditions belong to the exact 9 official Sony bypasses
    active_bypasses = tuple(active_deactivation_conditions)
    for cond in active_bypasses:
        if cond not in POWER_SAVE_9_DEACTIVATION_CONDITIONS_G111:
            _add_code(codes, STATUS_BLOCKED_G111_TELEMETRY_INVALID)
            errors.append(
                f"Unrecognized Power Save deactivation condition: {cond!r}."
            )

    # 1. [Power Save by Monitor] Reality Split & Spoof Rejection
    items_tuple = tuple(claimed_power_setting_option_items)
    if (
        claimed_fx3_ui_exposes_power_save_by_monitor
        or items_tuple != FX3_POWER_SETTING_OPTION_EXACT_2_ITEMS_G111
        or spoof_events != 0
    ):
        spoof_events = max(1, spoof_events)
        _add_code(codes, STATUS_BLOCKED_G111_POWER_SAVE_MONITOR_UI_SPOOF_VIOLATION)
        errors.append(
            "Stock ILME-FX3 Ver. 7.02 (ilc/2210) [Power Setting Option] exposes ONLY 2 items "
            "([Power Save Start Time], [Auto Power OFF Temp.]); [Power Save by Monitor] is NOT exposed "
            "and 'Open: On/Close: Off' is rejected."
        )

    resolved = resolve_fx3_power_save_monitor_and_language_state(
        reset_action=norm_reset or RESET_ACTION_NONE,
        pre_reset_monitor_power_linkage=norm_mon_mode
        or MONITOR_POWER_LINKAGE_DOES_NOT_LINK_G111,
        pre_reset_power_save_start_time=norm_pss_time
        or POWER_SAVE_START_TIME_OFF_G111,
        pre_reset_auto_power_off_temp=norm_auto_temp
        or AUTO_POWER_OFF_TEMP_FACTORY_DEFAULT_G111,
        pre_reset_language=norm_lang or LANGUAGE_CODE_EN_G111,
        air_gapped_battery_bench=bool(air_gapped_battery_bench),
        active_deactivation_conditions=active_bypasses,
    )

    matrix = compute_power_save_monitor_and_language_matrix()
    if not matrix["all_invariants_hold"]:
        _add_code(codes, STATUS_BLOCKED_G111_TELEMETRY_INVALID)
        errors.append("G111 matrix verification failed.")

    # 2. Sibling Body / Cross-Body Profile Headless Closed-LCD HDMI Guard
    eff_mon_mode = resolved["effective_post_reset_monitor_power_linkage"]
    headless_sleep_events = (
        claimed_headless_monitor_close_sleep_events
        if isinstance(claimed_headless_monitor_close_sleep_events, int)
        and not isinstance(claimed_headless_monitor_close_sleep_events, bool)
        else 1
    )
    exposing_body_audit = (
        monitor_power_linkage_audit_active
        or audit_body_model in SIBLING_EXPOSING_BODY_MODELS_G111
    )
    if (
        exposing_body_audit
        and lcd_folded_inward_headless_hdmi
        and eff_mon_mode not in SAFE_HEADLESS_MONITOR_POWER_LINKAGE_MODES_G111
    ):
        headless_sleep_events = max(1, headless_sleep_events)
    if headless_sleep_events != 0:
        _add_code(codes, STATUS_BLOCKED_G111_HEADLESS_MONITOR_CLOSE_SLEEP_HAZARD)
        errors.append(
            "Headless/closed-LCD HDMI bench on BIONZ XR bodies exposing [Power Save by Monitor] "
            "requires [Does Not Link] or [Open: Return]."
        )

    # 3. [Power Save Start Time] 9-Deactivation Air-Gapped Battery Bench Guard
    eff_pss_time = resolved["effective_post_reset_power_save_start_time"]
    batt_sleep_events = (
        claimed_battery_bench_idle_sleep_events
        if isinstance(claimed_battery_bench_idle_sleep_events, int)
        and not isinstance(claimed_battery_bench_idle_sleep_events, bool)
        else 1
    )
    if (
        air_gapped_battery_bench
        and not resolved["power_save_bypass_active"]
        and eff_pss_time not in BATTERY_BENCH_SAFE_POWER_SAVE_TIMES_G111
    ):
        batt_sleep_events = max(1, batt_sleep_events)
    if batt_sleep_events != 0:
        _add_code(codes, STATUS_BLOCKED_G111_BATTERY_BENCH_IDLE_SLEEP_HAZARD)
        errors.append(
            "Air-gapped battery bench runs with 0 active Power Save deactivation conditions "
            "require [Power Save Start Time] = [Off] or [30 Min]."
        )

    # 4. [Language] BK_LANG (0x02cf019c) 34-vs-29 Parity & (Setup) Reset Survival
    reset_ok = True
    reset_checks: Tuple[
        Tuple[Optional[str], str, Any], ...
    ] = (
        (
            claimed_post_reset_monitor_power_linkage,
            eff_mon_mode,
            _norm_monitor_power_linkage_g111,
        ),
        (
            claimed_post_reset_power_save_start_time,
            eff_pss_time,
            _norm_power_save_start_time_g111,
        ),
        (
            claimed_post_reset_auto_power_off_temp,
            resolved["effective_post_reset_auto_power_off_temp"],
            _norm_auto_power_off_temp_g111,
        ),
        (
            claimed_post_reset_language,
            resolved["effective_post_reset_language"],
            _norm_stage_b_language_g111,
        ),
    )
    for claimed_raw, expected_val, norm_fn in reset_checks:
        if claimed_raw is not None:
            if norm_fn(claimed_raw) != expected_val:
                reset_ok = False
                break

    lang_parity_ok = (
        bk_lang_property_id == BK_LANG_PROPERTY_ID_G111
        and fx3_language_count == FX3_LANGUAGE_COUNT_G111
        and fx6_language_count == FX6_LANGUAGE_COUNT_G111
        and bool(claimed_stage_b_4lang_parity_verified)
        and len(STAGE_B_4_LANGUAGE_PARITY_TABLE_G111) == 4
        and reset_ok
    )
    if not lang_parity_ok:
        _add_code(codes, STATUS_BLOCKED_G111_LANGUAGE_RESET_OR_BANK_VIOLATION)
        errors.append(
            "[Language] (BK_LANG 0x02cf019c: FX3=34 vs FX6=29, Stage-B 4-language parity) "
            "and (Setup) [Power Setting Option] must survive [Camera Settings Reset] & "
            "[Reset Network Set.], clearing only via [Initialize]."
        )

    valid = not codes
    status = STATUS_VERIFIED_G111 if valid else codes[0]

    return PowerSaveMonitorAndLanguageGuardResult(
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
        power_setting_option_menu_path=POWER_SETTING_OPTION_MENU_PATH_G111,
        power_save_start_time_menu_path=POWER_SAVE_START_TIME_MENU_PATH_G111,
        auto_power_off_temp_menu_path=AUTO_POWER_OFF_TEMP_MENU_PATH_G111,
        language_menu_path=LANGUAGE_MENU_PATH_G111,
        fx3_ui_exposes_power_save_by_monitor=FX3_UI_EXPOSES_POWER_SAVE_BY_MONITOR_G111,
        power_setting_option_items=items_tuple,
        power_save_monitor_ui_spoof_events=spoof_events,
        appfw_monitor_power_linkage_modes=ALLOWED_MONITOR_POWER_LINKAGE_MODES_G111,
        monitor_power_linkage_audit_active=monitor_power_linkage_audit_active,
        audit_body_model=audit_body_model,
        pre_reset_monitor_power_linkage=norm_mon_mode
        or str(pre_reset_monitor_power_linkage),
        effective_post_reset_monitor_power_linkage=eff_mon_mode,
        lcd_folded_inward_headless_hdmi=lcd_folded_inward_headless_hdmi,
        headless_monitor_close_sleep_events=headless_sleep_events,
        pre_reset_power_save_start_time=norm_pss_time
        or str(pre_reset_power_save_start_time),
        effective_post_reset_power_save_start_time=eff_pss_time,
        pre_reset_auto_power_off_temp=norm_auto_temp
        or str(pre_reset_auto_power_off_temp),
        effective_post_reset_auto_power_off_temp=resolved[
            "effective_post_reset_auto_power_off_temp"
        ],
        nine_deactivation_conditions=POWER_SAVE_9_DEACTIVATION_CONDITIONS_G111,
        active_deactivation_conditions=active_bypasses,
        power_save_bypass_active=resolved["power_save_bypass_active"],
        air_gapped_battery_bench=air_gapped_battery_bench,
        battery_bench_idle_sleep_events=batt_sleep_events,
        bk_lang_property_id_hex=f"0x{bk_lang_property_id:08x}"
        if isinstance(bk_lang_property_id, int)
        and not isinstance(bk_lang_property_id, bool)
        else "invalid",
        fx3_language_count=fx3_language_count,
        fx6_language_count=fx6_language_count,
        selected_stage_b_language=norm_lang or str(selected_stage_b_language),
        pre_reset_language=norm_lang or str(selected_stage_b_language),
        effective_post_reset_language=resolved["effective_post_reset_language"],
        stage_b_4lang_parity_verified=lang_parity_ok,
        setup_items_survive_camera_settings_and_network_reset=reset_ok,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g111_power_save_monitor_and_language_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    power_save_monitor_language_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase273DonorAuditResult] = None,
) -> Tuple[GateVerdict, G111PowerSaveMonitorAndLanguageGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase273_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_power_save_monitor_and_language_guard(
        **dict(power_save_monitor_language_kwargs or {})
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
        errors.append("Persistent eMMC write authorization requested in Gate G111.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G111 if valid else codes[0]

    res = G111PowerSaveMonitorAndLanguageGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        power_save_monitor_language_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, fx3_power_opt_items={len(guard.power_setting_option_items)}"
        f"(fx3_mon_exposed={guard.fx3_ui_exposes_power_save_by_monitor},spoof={guard.power_save_monitor_ui_spoof_events}), "
        f"mon_linkage={guard.effective_post_reset_monitor_power_linkage}, "
        f"pss_time={guard.effective_post_reset_power_save_start_time}(9cond_bypass={guard.power_save_bypass_active}), "
        f"bk_lang={guard.bk_lang_property_id_hex}(fx3={guard.fx3_language_count}/fx6={guard.fx6_language_count},"
        f"lang={guard.effective_post_reset_language})"
    )
    verdict = GateVerdict(
        gate_id=G111_GATE_ID,
        gate_code=G111_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G112: [Volume Settings], [4ch Audio Monitoring] & [Delete confirm.]
# ---------------------------------------------------------------------------


def compute_volume_4chmon_and_delete_confirm_matrix() -> Dict[str, Any]:
    """Exhaustively enumerate 240 combinations across representative `[Volume
    Settings]` (`0`, `7`, `15`), all `5` `[4ch Audio Monitoring]` routes, both
    `[Delete confirm.]` modes, both `[Delete pressing twice]` modes, and all `4`
    reset actions, verifying `(Setup)`/`(Playback)` reset survival and `Slot-1`
    recovery vault immutability (`slot1_vault_delete_events == 0`).
    """
    states_checked = 0
    reset_corruptions = 0
    slot1_vault_mutations = 0
    discrete_4ch_35mm_breaches = 0

    for vol in (0, 7, 15):
        for route in ALLOWED_4CH_AUDIO_MONITORING_ROUTES_G112:
            for del_conf in ALLOWED_DELETE_CONFIRM_MODES_G112:
                for del_twice in ALLOWED_DELETE_PRESSING_TWICE_MODES_G112:
                    for r_act in ALLOWED_RESET_ACTIONS_PHASE273:
                        resolved = resolve_fx3_volume_4chmon_and_delete_confirm_state(
                            reset_action=r_act,
                            pre_reset_volume_setting=vol,
                            pre_reset_4ch_audio_monitoring=route,
                            pre_reset_delete_confirm=del_conf,
                            pre_reset_delete_pressing_twice=del_twice,
                        )
                        states_checked += 1
                        survives = r_act in (
                            RESET_ACTION_NONE,
                            RESET_ACTION_CAMERA_SETTINGS_RESET,
                            RESET_ACTION_RESET_NETWORK_SET_PHASE273,
                        )
                        if survives and (
                            resolved["effective_post_reset_volume_setting"] != vol
                            or resolved["effective_post_reset_4ch_audio_monitoring"]
                            != route
                            or resolved["effective_post_reset_delete_confirm"]
                            != del_conf
                            or resolved["effective_post_reset_delete_pressing_twice"]
                            != del_twice
                        ):
                            reset_corruptions += 1
                        if r_act == RESET_ACTION_INITIALIZE and (
                            resolved["effective_post_reset_volume_setting"]
                            != VOLUME_SETTINGS_FACTORY_DEFAULT_G112
                            or resolved["effective_post_reset_4ch_audio_monitoring"]
                            != AUDIO_MON_FACTORY_DEFAULT_G112
                            or resolved["effective_post_reset_delete_confirm"]
                            != DELETE_CONFIRM_FACTORY_DEFAULT_G112
                            or resolved["effective_post_reset_delete_pressing_twice"]
                            != DELETE_PRESSING_TWICE_FACTORY_DEFAULT_G112
                        ):
                            reset_corruptions += 1
                        if not resolved["slot1_format_hard_locked"]:
                            slot1_vault_mutations += 1
                        if (
                            resolved["headphone_35mm_output_channels"]
                            != HEADPHONE_35MM_MAX_DISCRETE_CHANNELS_G112
                        ):
                            discrete_4ch_35mm_breaches += 1

    return {
        "states_checked": states_checked,
        "reset_corruptions": reset_corruptions,
        "slot1_vault_mutations": slot1_vault_mutations,
        "discrete_4ch_35mm_breaches": discrete_4ch_35mm_breaches,
        "all_invariants_hold": (
            states_checked == 240
            and reset_corruptions == 0
            and slot1_vault_mutations == 0
            and discrete_4ch_35mm_breaches == 0
        ),
    }


def resolve_fx3_volume_4chmon_and_delete_confirm_state(
    *,
    reset_action: str = RESET_ACTION_NONE,
    pre_reset_volume_setting: int = VOLUME_SETTINGS_FACTORY_DEFAULT_G112,
    pre_reset_4ch_audio_monitoring: str = AUDIO_MON_FACTORY_DEFAULT_G112,
    pre_reset_delete_confirm: str = DELETE_CONFIRM_FACTORY_DEFAULT_G112,
    pre_reset_delete_pressing_twice: str = DELETE_PRESSING_TWICE_FACTORY_DEFAULT_G112,
    slot1_holds_recovery_vault: bool = True,
) -> Dict[str, Any]:
    r_act = _norm_reset_action_phase273(reset_action) or RESET_ACTION_NONE
    vol = (
        pre_reset_volume_setting
        if (
            not isinstance(pre_reset_volume_setting, bool)
            and isinstance(pre_reset_volume_setting, int)
            and VOLUME_SETTINGS_MIN_G112
            <= pre_reset_volume_setting
            <= VOLUME_SETTINGS_MAX_G112
        )
        else VOLUME_SETTINGS_FACTORY_DEFAULT_G112
    )
    route = (
        _norm_4ch_audio_monitoring_g112(pre_reset_4ch_audio_monitoring)
        or AUDIO_MON_FACTORY_DEFAULT_G112
    )
    del_conf = (
        _norm_delete_confirm_g112(pre_reset_delete_confirm)
        or DELETE_CONFIRM_FACTORY_DEFAULT_G112
    )
    del_twice = (
        _norm_on_off_phase273(pre_reset_delete_pressing_twice)
        or DELETE_PRESSING_TWICE_FACTORY_DEFAULT_G112
    )

    # [Volume Settings] & [4ch Audio Monitoring] reside under (Setup), while
    # [Delete confirm.] & [Delete pressing twice] reside under (Playback).
    # Both survive [Camera Settings Reset] & [Reset Network Set.], resetting ONLY
    # via [Initialize].
    initialized = r_act == RESET_ACTION_INITIALIZE
    eff_vol = VOLUME_SETTINGS_FACTORY_DEFAULT_G112 if initialized else vol
    eff_route = AUDIO_MON_FACTORY_DEFAULT_G112 if initialized else route
    eff_del_conf = DELETE_CONFIRM_FACTORY_DEFAULT_G112 if initialized else del_conf
    eff_del_twice = (
        DELETE_PRESSING_TWICE_FACTORY_DEFAULT_G112 if initialized else del_twice
    )

    return {
        "reset_action": r_act,
        "effective_post_reset_volume_setting": eff_vol,
        "effective_post_reset_4ch_audio_monitoring": eff_route,
        "effective_post_reset_delete_confirm": eff_del_conf,
        "effective_post_reset_delete_pressing_twice": eff_del_twice,
        "headphone_35mm_output_channels": HEADPHONE_35MM_MAX_DISCRETE_CHANNELS_G112,
        "slot1_format_hard_locked": bool(slot1_holds_recovery_vault),
    }


def verify_volume_4chmon_delete_confirm_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE273,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE273,
    reset_action: str = RESET_ACTION_NONE,
    pre_reset_volume_setting: int = VOLUME_SETTINGS_FACTORY_DEFAULT_G112,
    claimed_post_reset_volume_setting: Optional[int] = None,
    audio_signals_conflated: bool = False,
    xlr_h1_mic_active: bool = False,
    headphones_connected: bool = False,
    internal_speaker_active: Optional[bool] = None,
    claimed_xlr_acoustic_feedback_events: int = 0,
    pre_reset_4ch_audio_monitoring: str = AUDIO_MON_FACTORY_DEFAULT_G112,
    claimed_post_reset_4ch_audio_monitoring: Optional[str] = None,
    hdmi_4ch_audio_output: str = "CH1/CH2",
    headphone_35mm_output_channels: int = HEADPHONE_35MM_MAX_DISCRETE_CHANNELS_G112,
    claimed_discrete_4ch_35mm_output: bool = False,
    pre_reset_delete_confirm: str = DELETE_CONFIRM_FACTORY_DEFAULT_G112,
    claimed_post_reset_delete_confirm: Optional[str] = None,
    pre_reset_delete_pressing_twice: str = DELETE_PRESSING_TWICE_FACTORY_DEFAULT_G112,
    claimed_post_reset_delete_pressing_twice: Optional[str] = None,
    slot1_holds_recovery_vault: bool = True,
    requested_media_op: str = MEDIA_OP_NONE_G112,
    target_slot: str = TARGET_SLOT_NONE_G112,
    claimed_slot1_vault_delete_events: int = 0,
) -> Volume4chMonDeleteConfirmGuardResult:
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_name != FX3_MODEL_NAME
        or isinstance(body_model_id, bool)
        or body_model_id != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE273
        or not isinstance(firmware_version, str)
        or not firmware_version.strip()
    ):
        _add_code(codes, STATUS_BLOCKED_G112_TELEMETRY_INVALID)
        errors.append(
            "Gate G112 requires ILME-FX3 (0x91030080, Help Guide ilc/2210, Ver. 7.02)."
        )

    norm_reset = _norm_reset_action_phase273(reset_action)
    norm_route = _norm_4ch_audio_monitoring_g112(pre_reset_4ch_audio_monitoring)
    norm_hdmi_4ch = _norm_hdmi_4ch_audio_output_g112(hdmi_4ch_audio_output)
    norm_del_conf = _norm_delete_confirm_g112(pre_reset_delete_confirm)
    norm_del_twice = _norm_on_off_phase273(pre_reset_delete_pressing_twice)
    norm_media_op = _norm_media_op_g112(requested_media_op)
    norm_slot = _norm_target_slot_g112(target_slot)

    # Check invalid volume range (must be int 0..15) before generic invalid check
    vol_type_ok = (
        not isinstance(pre_reset_volume_setting, bool)
        and isinstance(pre_reset_volume_setting, int)
    )
    vol_in_range = (
        vol_type_ok
        and VOLUME_SETTINGS_MIN_G112
        <= pre_reset_volume_setting
        <= VOLUME_SETTINGS_MAX_G112
    )

    if (
        norm_reset is None
        or not vol_type_ok
        or not isinstance(audio_signals_conflated, bool)
        or not isinstance(xlr_h1_mic_active, bool)
        or not isinstance(headphones_connected, bool)
        or (
            internal_speaker_active is not None
            and not isinstance(internal_speaker_active, bool)
        )
        or not isinstance(claimed_discrete_4ch_35mm_output, bool)
        or not isinstance(slot1_holds_recovery_vault, bool)
        or norm_del_conf is None
        or norm_del_twice is None
        or norm_media_op is None
        or norm_slot is None
        or isinstance(headphone_35mm_output_channels, bool)
        or not isinstance(headphone_35mm_output_channels, int)
    ):
        _add_code(codes, STATUS_BLOCKED_G112_TELEMETRY_INVALID)
        errors.append("Invalid or unrecognized G112 telemetry or enum value.")

    for int_val, name in (
        (claimed_xlr_acoustic_feedback_events, "claimed_xlr_acoustic_feedback_events"),
        (claimed_slot1_vault_delete_events, "claimed_slot1_vault_delete_events"),
    ):
        if isinstance(int_val, bool) or not isinstance(int_val, int) or int_val < 0:
            _add_code(codes, STATUS_BLOCKED_G112_TELEMETRY_INVALID)
            errors.append(f"{name} must be a non-negative integer.")

    resolved = resolve_fx3_volume_4chmon_and_delete_confirm_state(
        reset_action=norm_reset or RESET_ACTION_NONE,
        pre_reset_volume_setting=pre_reset_volume_setting if vol_in_range else 7,
        pre_reset_4ch_audio_monitoring=norm_route or AUDIO_MON_FACTORY_DEFAULT_G112,
        pre_reset_delete_confirm=norm_del_conf or DELETE_CONFIRM_FACTORY_DEFAULT_G112,
        pre_reset_delete_pressing_twice=norm_del_twice
        or DELETE_PRESSING_TWICE_FACTORY_DEFAULT_G112,
        slot1_holds_recovery_vault=bool(slot1_holds_recovery_vault),
    )

    matrix = compute_volume_4chmon_and_delete_confirm_matrix()
    if not matrix["all_invariants_hold"]:
        _add_code(codes, STATUS_BLOCKED_G112_TELEMETRY_INVALID)
        errors.append("G112 Volume/4chMon/DeleteConfirm matrix failed.")

    # 1. [Volume Settings] (0..15, Default 7), [Audio signals] Separation & XLR-H1 Acoustic Feedback Guard
    eff_speaker_active = (
        bool(internal_speaker_active)
        if isinstance(internal_speaker_active, bool)
        else (not bool(headphones_connected))
    )
    eff_vol = resolved["effective_post_reset_volume_setting"]
    feedback_events = (
        claimed_xlr_acoustic_feedback_events
        if isinstance(claimed_xlr_acoustic_feedback_events, int)
        and not isinstance(claimed_xlr_acoustic_feedback_events, bool)
        else 1
    )
    if (
        xlr_h1_mic_active
        and (not headphones_connected)
        and eff_speaker_active
        and eff_vol > XLR_H1_INTERNAL_SPEAKER_SAFE_MAX_VOLUME_G112
    ):
        feedback_events = max(1, feedback_events)

    vol_reset_ok = True
    if claimed_post_reset_volume_setting is not None:
        if (
            isinstance(claimed_post_reset_volume_setting, bool)
            or not isinstance(claimed_post_reset_volume_setting, int)
            or claimed_post_reset_volume_setting != eff_vol
        ):
            vol_reset_ok = False

    if (
        not vol_in_range
        or audio_signals_conflated
        or feedback_events != 0
        or not vol_reset_ok
    ):
        _add_code(codes, STATUS_BLOCKED_G112_VOLUME_RANGE_OR_XLR_FEEDBACK_VIOLATION)
        errors.append(
            "[Volume Settings] must stay in discrete 0..15 (default 7), remain distinct from "
            "[Audio signals], survive [Camera Settings Reset], and avoid high speaker playback "
            "with XLR-H1 mic active without headphones."
        )

    # 2. [4ch Audio Monitoring] (5 Routes) & 3.5 mm Stereo 2ch Boundary
    route_reset_ok = True
    if claimed_post_reset_4ch_audio_monitoring is not None:
        if (
            _norm_4ch_audio_monitoring_g112(claimed_post_reset_4ch_audio_monitoring)
            != resolved["effective_post_reset_4ch_audio_monitoring"]
        ):
            route_reset_ok = False

    if (
        norm_route is None
        or norm_hdmi_4ch is None
        or claimed_discrete_4ch_35mm_output
        or headphone_35mm_output_channels != HEADPHONE_35MM_MAX_DISCRETE_CHANNELS_G112
        or not route_reset_ok
    ):
        _add_code(codes, STATUS_BLOCKED_G112_4CH_MONITORING_ROUTE_VIOLATION)
        errors.append(
            "[4ch Audio Monitoring] permits only the 5 Sony routes (CH1/CH2, CH3/CH4, CH1+3/CH2+4, "
            "CH1/CH1, CH2/CH2), distinct from HDMI [4ch Audio Output] (CH1/CH2 vs CH3/CH4), "
            "across a 2ch stereo 3.5 mm headphone boundary."
        )

    # 3. [Delete confirm.] ("Cancel" first Default), (Playback) Reset Survival & Slot-1 Vault Firewall
    del_reset_ok = True
    if claimed_post_reset_delete_confirm is not None:
        if (
            _norm_delete_confirm_g112(claimed_post_reset_delete_confirm)
            != resolved["effective_post_reset_delete_confirm"]
        ):
            del_reset_ok = False
    if claimed_post_reset_delete_pressing_twice is not None:
        if (
            _norm_on_off_phase273(claimed_post_reset_delete_pressing_twice)
            != resolved["effective_post_reset_delete_pressing_twice"]
        ):
            del_reset_ok = False

    slot1_delete_events = (
        claimed_slot1_vault_delete_events
        if isinstance(claimed_slot1_vault_delete_events, int)
        and not isinstance(claimed_slot1_vault_delete_events, bool)
        else 1
    )
    if (
        slot1_holds_recovery_vault
        and norm_slot == TARGET_SLOT_1_G112
        and norm_media_op is not None
        and norm_media_op != MEDIA_OP_NONE_G112
    ):
        slot1_delete_events = max(1, slot1_delete_events)

    if slot1_delete_events != 0 or not del_reset_ok:
        _add_code(codes, STATUS_BLOCKED_G112_SLOT1_VAULT_DELETE_OR_FORMAT_VIOLATION)
        errors.append(
            "[Delete confirm.] ('Cancel' first default) & [Delete pressing twice] (Off default) "
            "survive [Camera Settings Reset] under (Playback), and ANY Delete/Format targeting "
            "Slot-1 recovery vault is hard-blocked."
        )

    setup_playback_reset_ok = vol_reset_ok and route_reset_ok and del_reset_ok
    valid = not codes
    status = STATUS_VERIFIED_G112 if valid else codes[0]

    return Volume4chMonDeleteConfirmGuardResult(
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
        volume_settings_menu_path=VOLUME_SETTINGS_MENU_PATH_G112,
        audio_monitoring_4ch_menu_path=AUDIO_MONITORING_4CH_MENU_PATH_G112,
        hdmi_4ch_audio_output_menu_path=HDMI_4CH_AUDIO_OUTPUT_MENU_PATH_G112,
        delete_confirm_menu_path=DELETE_CONFIRM_MENU_PATH_G112,
        delete_pressing_twice_menu_path=DELETE_PRESSING_TWICE_MENU_PATH_G112,
        pre_reset_volume_setting=pre_reset_volume_setting
        if vol_type_ok
        else -1,
        effective_post_reset_volume_setting=eff_vol,
        audio_signals_conflated=bool(audio_signals_conflated),
        xlr_h1_mic_active=bool(xlr_h1_mic_active),
        headphones_connected=bool(headphones_connected),
        internal_speaker_active=eff_speaker_active,
        xlr_acoustic_feedback_events=feedback_events,
        pre_reset_4ch_audio_monitoring=norm_route
        or str(pre_reset_4ch_audio_monitoring),
        effective_post_reset_4ch_audio_monitoring=resolved[
            "effective_post_reset_4ch_audio_monitoring"
        ],
        hdmi_4ch_audio_output=norm_hdmi_4ch or str(hdmi_4ch_audio_output),
        headphone_35mm_output_channels=headphone_35mm_output_channels
        if isinstance(headphone_35mm_output_channels, int)
        and not isinstance(headphone_35mm_output_channels, bool)
        else -1,
        discrete_4ch_35mm_claimed=bool(claimed_discrete_4ch_35mm_output),
        pre_reset_delete_confirm=norm_del_conf or str(pre_reset_delete_confirm),
        effective_post_reset_delete_confirm=resolved[
            "effective_post_reset_delete_confirm"
        ],
        pre_reset_delete_pressing_twice=norm_del_twice
        or str(pre_reset_delete_pressing_twice),
        effective_post_reset_delete_pressing_twice=resolved[
            "effective_post_reset_delete_pressing_twice"
        ],
        slot1_holds_recovery_vault=bool(slot1_holds_recovery_vault),
        slot1_format_hard_locked=bool(slot1_holds_recovery_vault),
        requested_media_op=norm_media_op or str(requested_media_op),
        target_slot=norm_slot or str(target_slot),
        slot1_vault_delete_events=slot1_delete_events,
        setup_playback_reset_contract_verified=setup_playback_reset_ok,
        matrix_states_checked=matrix["states_checked"],
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g112_volume_4chmon_delete_confirm_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    volume_4chmon_delete_confirm_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase273DonorAuditResult] = None,
) -> Tuple[GateVerdict, G112Volume4chMonDeleteConfirmGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase273_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_volume_4chmon_delete_confirm_guard(
        **dict(volume_4chmon_delete_confirm_kwargs or {})
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
        errors.append("Persistent eMMC write authorization requested in Gate G112.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G112 if valid else codes[0]

    res = G112Volume4chMonDeleteConfirmGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        volume_4chmon_delete_confirm_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, vol={guard.effective_post_reset_volume_setting}/15"
        f"(xlr_fb={guard.xlr_acoustic_feedback_events}), "
        f"4ch_mon={guard.effective_post_reset_4ch_audio_monitoring}"
        f"(35mm_ch={guard.headphone_35mm_output_channels}), "
        f"del_confirm={guard.effective_post_reset_delete_confirm}"
        f"(del_twice={guard.effective_post_reset_delete_pressing_twice},"
        f"slot1_del={guard.slot1_vault_delete_events},"
        f"slot1_fmt_lock={guard.slot1_format_hard_locked})"
    )
    verdict = GateVerdict(
        gate_id=G112_GATE_ID,
        gate_code=G112_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `112`-Gate Master Safety Preflight (`G01..G112`)
# ---------------------------------------------------------------------------


def evaluate_112gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    power_save_monitor_language_kwargs: Optional[Mapping[str, Any]] = None,
    volume_4chmon_delete_confirm_kwargs: Optional[Mapping[str, Any]] = None,
    master_110_override: Optional[Master110GateReport] = None,
    **m110_passthrough_kwargs: Any,
) -> Master112GateReport:
    """Evaluate all 112 Master Safety Gates (`G01..G112`) deterministically by
    delegating `G01..G110` directly to `evaluate_110gate_preflight()`.
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

    m110_report: Master110GateReport = (
        master_110_override
        if master_110_override is not None
        else evaluate_110gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m110_passthrough_kwargs,
        )
    )

    phase273_audit = audit_phase273_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g111_verdict, g111_res = evaluate_g111_power_save_monitor_and_language_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        power_save_monitor_language_kwargs=power_save_monitor_language_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase273_audit,
    )

    g112_verdict, g112_res = evaluate_g112_volume_4chmon_delete_confirm_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        volume_4chmon_delete_confirm_kwargs=volume_4chmon_delete_confirm_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase273_audit,
    )

    gates_111_to_112 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g111_verdict, g112_verdict)
    ]
    all_gates = tuple(list(m110_report.gates) + gates_111_to_112)

    g01_to_g12_verified = int(m110_report.summary["g01_to_g12_verified"])
    g13_to_g110_verified = int(m110_report.summary["g13_to_g108_verified"]) + int(
        m110_report.summary["g109_to_g110_verified"]
    )
    g111_to_g112_verified = sum(1 for v in (g111_verdict, g112_verdict) if v.passed)
    total_verified = (
        g01_to_g12_verified + g13_to_g110_verified + g111_to_g112_verified
    )

    g111_to_g112_all_passed = g111_to_g112_verified == 2
    g13_to_g112_all_passed = (
        m110_report.g13_to_g110_all_passed and g111_to_g112_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m110_report.gates[:9])

    offline_109_verified = (
        g01_to_g09_ok
        and m110_report.offline_107_gates_verified
        and g111_to_g112_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_112_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g112_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m110_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_109_verified
        and m110_report.h0_h1_trial_entry_allowed
        and g111_to_g112_all_passed
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
        list(m110_report.errors)
        + list(g111_verdict.errors)
        + list(g112_verdict.errors)
    )
    warnings: List[str] = (
        list(m110_report.warnings)
        + list(g111_verdict.warnings)
        + list(g112_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m110_report.g13_to_g110_all_passed:
        overall_status = m110_report.status
    elif not g111_verdict.passed:
        overall_status = g111_verdict.status
    elif not g112_verdict.passed:
        overall_status = g112_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_112_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_112_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_112_verified:
        overall_status = "VERIFIED_ALL_112_GATES"
    else:
        overall_status = "VERIFIED_109_OF_112_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m110_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g111_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g112_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 112,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 112 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g110_verified": g13_to_g110_verified,
        "g111_to_g112_verified": g111_to_g112_verified,
        "g13_to_g112_all_passed": g13_to_g112_all_passed,
        "g111_to_g112_all_passed": g111_to_g112_all_passed,
        "offline_109_gates_verified": offline_109_verified,
        "all_112_gates_verified": all_112_verified,
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

    return Master112GateReport(
        schema=REALHW_POWER_SAVE_MONITOR_LANGUAGE_VOLUME_DELETE_112GATE_SCHEMA,
        version=REALHW_POWER_SAVE_MONITOR_LANGUAGE_VOLUME_DELETE_112GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_109_gates_verified=offline_109_verified,
        all_112_gates_verified=all_112_verified,
        g13_to_g112_all_passed=g13_to_g112_all_passed,
        g111_to_g112_all_passed=g111_to_g112_all_passed,
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
        master_110_report=m110_report.to_dict(),
        g111_result=g111_res.to_dict(),
        g112_result=g112_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_112_master_safety_gates = evaluate_112gate_preflight
run_112_gate_preflight = evaluate_112gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_power_save_monitor_language_volume_delete_and_112gate_guard",
        description=(
            "Phase 273 (112/112 Safety Gates, Wave-46) Gates G111 ([Power Save by "
            "Monitor] appFw.so 4-Mode vs ILME-FX3 2-Item [Power Setting Option] "
            "Reality Split, [Power Save Start Time] 9-Deactivation Bench Guard & "
            "[Language] BK_LANG 0x02cf019c 34-vs-29 Parity) + G112 ([Volume "
            "Settings] 0..15 Default 7, [4ch Audio Monitoring] 5 Routes & [Delete "
            "confirm.] 'Cancel' first + Slot-1 Vault Firewall) + Unified 112-Gate "
            "Master Safety Preflight"
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

    report = evaluate_112gate_preflight(
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
            f"verified={report.summary['verified_gates']}/112 "
            f"g111_to_g112_all_passed={report.g111_to_g112_all_passed} "
            f"all_112_gates_verified={report.all_112_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = (
        report.all_112_gates_verified
        if args.dry_run_simulated
        else report.offline_109_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
