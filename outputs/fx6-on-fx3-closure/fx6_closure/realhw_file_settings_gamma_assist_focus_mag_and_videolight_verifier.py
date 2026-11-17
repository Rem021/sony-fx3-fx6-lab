"""Phase 275 — 7th Real-Hardware Physical Bench Readiness Verifier (`preflight-file-settings-gamma-assist-focus-mag-and-videolight`).

Dedicated host-side read-only 7th physical bench & pre-shoot readiness verifier for Sony
`ILME-FX3` (`Ver. 7.02`, `ilc/2210`, Model `0x91030080`) vs `ILME-FX6` (`Ver. 6.01`),
extending the operator bench preflight series (`preflight-card-insert` ->
`preflight-bench-cable-fan-slot1` -> `preflight-hdmi-proxy-desqueeze-and-simult` ->
`preflight-pixelmap-ntscpal-powersave-and-autotemp` ->
`preflight-imagedb-touch-shoeaudio-and-lockop` ->
`preflight-diffset-customkey-autoslow-and-apsc` ->
`preflight-file-settings-gamma-assist-focus-mag-and-videolight`) by synthesizing Waves 44–46
official Sony `ILME-FX3` Help Guide (`ilc/2210`), `appFw.so`, `BK4`, and `.uxc` hardware
boundaries into 4 deterministic fail-closed check groups (`A..D`), bounded `O_RDONLY` donor
inspection (`< 0.15s`), `16/16 H0 == H3` baseline invariance, and dual-media `528 B FX3RCPT1`
Tier-0 receipt gating:

1. **Check Group A (`GROUP_A_CINEMA_SLATE_FILE_SETTINGS_AUTO_REVIEW_AND_TCUB_PERSISTENCE` — Wave 44)**:
   - Movie `[File Settings]` (`File Number` `Series`/`Reset`, `File Name Format` `Cam ID + Reel#`
     `A..Z` / `001..999` / `C|L|R`, `37`-char `Title Name Settings` `"C"` default, immutable
     `PRIVATE/M4ROOT/CLIP` path) vs Still `[File/Folder Settings]` (`3`-char `DSC` prefix,
     leading `_` rejected, `Standard Form` / `Date Form`, `Slot-1` DCIM `Forced File Number Reset`
     / `Create New Folder` hard-blocked when `Slot 1` holds read-only Tier-0 recovery vault).
   - `[Auto Review] = [Off]` cinema default (still-only) and all `6` `[TC/UB]` items surviving
     `[Camera Settings Reset]` (restored only by `[Initialize]`), plus `[TC/UB Disp. Setting]`
     and `24.00p` / PAL `25p`/`50p` forced `NDF`.

2. **Check Group B (`GROUP_B_GAMMA_DISPLAY_ASSIST_VS_DISPLAY_LUT_CLEAN_HDMI` — Wave 44)**:
   - `[Gamma Display Assist]` (`Off` default) hard-locked to `Off` whenever `[Log Shooting]`
     (`Cine EI`, `Cine EI Quick`, `Flexible ISO`) `!= Off` and strictly restricted to internal
     LCD (clean external HDMI, `0` assist pixels baked onto HDMI output).
   - `[Display LUT]` (`On` default) + `[Select LUT]` (`S-Log3`, `s709`, `709(800%)`, `User1..16`)
     govern Log monitoring; all three `[Setup]` items survive `[Camera Settings Reset]`.

3. **Check Group C (`GROUP_C_FOCUS_MAG_4X_PEAKING_ZERORF_TIME_VIDEOLIGHT_HDMI_RES` — Wave 45)**:
   - `[Focus Magnifier]` (`1.0x`/`4.0x`, `No Limit` default, `[Auto Magnifier in MF]` vs legacy
     `"MF Assist"`, `Custom Button 5`, clean-HDMI exit isolation & `HDMI RAW Output` lockout).
   - `[Peaking Display]` (`Off` default, `Mid`/`White`) & `[AF Illuminator]` (`Auto` default,
     strictly still-only — locked out in Movie/`S&Q` and `AF-C`).
   - `[Area/Date/Time Setting]` manual air-gapped setup (Creators' App Bluetooth/Wi-Fi
     `[Location Information Linkage]` suppressed on zero-RF bench, `passive_tx_bytes_emitted == 0`).
   - `[Video Light Mode]` (`Power Link` default, MI-Shoe `5V <= 900 mA` PMIC overcurrent budget
     guard) and `[HDMI Resolution]` (`Auto` default, `1080p`/`1080i` enforced during `Log`
     internal recording / `HDMI RAW` / `4K->HD` rules).

4. **Check Group D (`GROUP_D_POWER_SAVE_MONITOR_SPLIT_BKLANG_VOLUME_DELETE_AND_TIER0` — Wave 46)**:
   - Stock `ILME-FX3 Ver. 7.02` (`ilc/2210`) 2-item `[Power Setting Option]` (`[Power Save Start
     Time]` `Off`/`30 Min` air-gapped battery rule vs `9` deactivation conditions + `[Auto Power
     OFF Temp.]`) vs compiled `appFw.so` `[Power Save by Monitor]` (`4` modes `Both Linked` /
     `Open: Return` / `Close: Power Save` / `Does Not Link` yet unexposed in stock FX3 UI).
   - `[Language]` (`BK_LANG` `0x02cf019c`, `FX3` `34` vs `FX6` `29` languages, 4-lang codes
     `en=0x00`, `japanese=0x01`, `tchinese=0x18`, `schinese=0x19`, `(Setup)` survival across both
     `[Camera Settings Reset]` and `[Reset Network Set.]`).
   - `[Volume Settings]` (`0..15`, default `7`, speaker-to-`XLR-H1` feedback guard) + `[4ch Audio
     Monitoring]` (exact `5` routes, `3.5 mm` `2ch` stereo limit) + `[Delete confirm.] =
     ["Cancel" first]` + `Slot-1` vault delete/format hard block + `16/16 H0 == H3` + dual-media
     `528 B FX3RCPT1` Tier-0 receipt gating.

Hard-Locked Safety Invariants (UNCONDITIONAL):
- `overall_ready_for_hardware_attach = False`
- `hardware_live_attachment_authorized = False`
- `persistent_emmc_writes_authorized = False`
- `persistent_write_release = False`
- `spi_nor_write_authorized = False`
- `el3_payload_transmit_authorized = False`
- `sd_physical_media_written = False`
- `usb_packets_transmitted = 0` (`physical_usb_packets_emitted = 0`)
- `raw_firmware_bytes_leaked = 0`
- `passive_tx_bytes_emitted = 0`
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


def _ensure_cross_package_paths(repo_root: Path) -> None:
    for rel in (
        "outputs/fx3-safety",
        "outputs/fx3-recovery-adapter",
        "outputs/fx3-firmware-lab",
        "outputs/fx3-vm",
        "outputs/fx6-on-fx3-closure",
    ):
        cand = str(repo_root / rel)
        if cand not in sys.path:
            sys.path.append(cand)


DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
_ensure_cross_package_paths(DEFAULT_REPO_ROOT)

from fx3_recovery.realhw_adjustcontrol_streaming_backup_client import (  # noqa: E402
    COLD_BACKUP_ITEMS,
    SD_RECEIPT_BYTES,
    build_sd_backup_receipt_bytes,
    parse_sd_backup_receipt_bytes,
)

from .donor_paths import is_forced_clean_room, resolve_work_subpath  # noqa: E402
from .hardware_readiness_packet import (  # noqa: E402
    BODY_SERIAL_RE,
    FORBIDDEN_TRIVIAL_CIDS,
    FORBIDDEN_TRIVIAL_SERIALS,
    HEX32_CID_RE,
    HEX64_RE,
)
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FX6_WLAN_RSRC_DONOR_SHA256,
)
from .realhw_bench_cable_fan_and_slot1_verifier import (  # noqa: E402
    FX3_LIBUSBBUSPOWER_EXPECTED_SHA256,
    FX3_LIBUSBBUSPOWER_EXPECTED_SIZE,
    FX3_LIBUSBBUSPOWER_RELPATH,
)
from .realhw_card_insert_readiness_verifier import (  # noqa: E402
    DONOR_INSPECTION_MAX_SECONDS,
    EM_AARCH64,
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    MIN_BODY_FW_TUPLE,
    REQUIRED_H0_BASELINE_KEYS,
    TARGET_BODY_FW,
    TARGET_MODEL_ID_INT,
    _parse_elf64_header_and_pt_load,
    _parse_fw_tuple,
    _read_bounded_slice_o_rdonly,
    build_default_h0_baselines,
)
from .realhw_jiritsu_and_tier0_dumper_auditor import (  # noqa: E402
    LIBJIRITSU_EXPECTED_SHA256,
    LIBJIRITSU_EXPECTED_SIZE,
    LIBJIRITSU_RELPATH,
)
from .realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
    FX3_IM_ELF_EXPECTED_SHA256,
    FX3_IM_ELF_EXPECTED_SIZE,
    FX3_IM_ELF_RELPATH,
    FX6_APPFW_EXPECTED_SIZE,
    SIXTEEN_STORAGE_SURFACES,
    read_only_o_rdonly_digest_and_header,
)

# ---------------------------------------------------------------------------
# Schema, Verdicts & Non-Shadowing P275_* Domain Constants
# ---------------------------------------------------------------------------

PHASE_275_SCHEMA: str = "realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier_v1"
P275_SCHEMA: str = PHASE_275_SCHEMA
REALHW_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_SCHEMA: str = PHASE_275_SCHEMA
PHASE_275_VERSION: str = "275.0.0"
P275_VERSION: str = PHASE_275_VERSION
P275_SONY_HELP_GUIDE_ID: str = "ilc/2210"

P275_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS: str = (
    "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
)
P275_GO_NO_GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_VERIFIED: str = (
    "GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_READONLY_PREFLIGHT_VERIFIED"
)
P275_GO_NO_GO_BLOCKED_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_FAILURE: str = (
    "BLOCKED_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_CHECK_FAILURE"
)
PHASE_275_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    P275_GO_NO_GO_BLOCKED_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_FAILURE,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P275_GO_NO_GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_VERIFIED,
)

P275_CHECK_GROUP_A_ID: str = (
    "GROUP_A_CINEMA_SLATE_FILE_SETTINGS_AUTO_REVIEW_AND_TCUB_PERSISTENCE"
)
P275_CHECK_GROUP_B_ID: str = (
    "GROUP_B_GAMMA_DISPLAY_ASSIST_VS_DISPLAY_LUT_CLEAN_HDMI"
)
P275_CHECK_GROUP_C_ID: str = (
    "GROUP_C_FOCUS_MAG_4X_PEAKING_ZERORF_TIME_VIDEOLIGHT_HDMI_RES"
)
P275_CHECK_GROUP_D_ID: str = (
    "GROUP_D_POWER_SAVE_MONITOR_SPLIT_BKLANG_VOLUME_DELETE_AND_TIER0"
)
PHASE_275_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P275_CHECK_GROUP_A_ID,
    P275_CHECK_GROUP_B_ID,
    P275_CHECK_GROUP_C_ID,
    P275_CHECK_GROUP_D_ID,
)

PHASE275_RAW_FIRMWARE_BYTES_LEAKED: int = 0
PHASE275_PASSIVE_TX_BYTES_EMITTED: int = 0

# Group A Constants (Wave 44 — File Settings, Still Prefix, Auto Review & TC/UB)
P275_VALID_FILE_NUMBER_MODES: Tuple[str, ...] = ("SERIES", "RESET")
P275_VALID_MOVIE_FILE_NAME_FORMATS: Tuple[str, ...] = (
    "STANDARD",
    "CAM_ID_PLUS_REEL",
    "TITLE",
    "DATE_PLUS_TITLE",
    "TITLE_PLUS_DATE",
)
P275_DEFAULT_TITLE_NAME: str = "C"
P275_TITLE_NAME_MAX_CHARS: int = 37
P275_CAMERA_ID_RE = re.compile(r"^[A-Z]$")
P275_REEL_NUMBER_MIN: int = 1
P275_REEL_NUMBER_MAX: int = 999
P275_VALID_CAMERA_POSITIONS: Tuple[str, ...] = ("C", "L", "R")
P275_MOVIE_FIXED_CLIP_DIR: str = "PRIVATE/M4ROOT/CLIP"

P275_DEFAULT_STILL_FILE_PREFIX: str = "DSC"
P275_STILL_PREFIX_LEN: int = 3
P275_STILL_PREFIX_NO_LEADING_UNDERSCORE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_]{2}$")
P275_VALID_STILL_FOLDER_NAMES: Tuple[str, ...] = ("STANDARD_FORM", "DATE_FORM")
P275_VALID_AUTO_REVIEW_MODES: Tuple[str, ...] = ("OFF", "2_SEC", "5_SEC", "10_SEC")

P275_TCUB_SIX_ITEMS: Tuple[str, ...] = (
    "Time Code Preset",
    "User Bit Preset",
    "Time Code Format",
    "Time Code Run",
    "Time Code Make",
    "User Bit Time Rec",
)
P275_VALID_TC_FORMATS: Tuple[str, ...] = ("DF", "NDF")
P275_VALID_TC_RUN_MODES: Tuple[str, ...] = ("REC_RUN", "FREE_RUN")
P275_VALID_TC_MAKE_MODES: Tuple[str, ...] = ("PRESET", "REGENERATE")
P275_VALID_TCUB_DISP_SETTINGS: Tuple[str, ...] = ("TC", "UB")
P275_VALID_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "RESET_NETWORK_SET",
    "INITIALIZE",
)

# Group B Constants (Wave 44 — Gamma Display Assist vs Display LUT / Select LUT)
P275_VALID_GAMMA_ASSIST_TYPES: Tuple[str, ...] = (
    "AUTO",
    "S_LOG3_TO_709_800PCT",
    "HLG_BT2020",
    "HLG_709",
)
P275_VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "OFF",
    "CINE_EI_QUICK",
    "CINE_EI",
    "FLEXIBLE_ISO",
)
P275_ACTIVE_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "CINE_EI_QUICK",
    "CINE_EI",
    "FLEXIBLE_ISO",
)
P275_SELECT_LUT_THREE_PRESETS: Tuple[str, ...] = ("S-Log3", "s709", "709(800%)")
P275_USER_LUT_MAX_SLOTS: int = 16
P275_SELECT_LUT_USER_SLOTS: Tuple[str, ...] = tuple(
    f"User{idx}" for idx in range(1, P275_USER_LUT_MAX_SLOTS + 1)
)
P275_VALID_SELECT_LUTS: Tuple[str, ...] = (
    *P275_SELECT_LUT_THREE_PRESETS,
    *P275_SELECT_LUT_USER_SLOTS,
)

# Group C Constants (Wave 45 — Focus Magnifier, Peaking, AF Illuminator, Area/Date/Time, Video Light, HDMI Res)
P275_AUTO_MAG_IN_MF_EXACT_LABEL: str = "Auto Magnifier in MF"
P275_FOCUS_MAG_DEFAULT_CUSTOM_BUTTON: str = "Custom Button 5"
P275_VALID_FOCUS_MAG_SCALES: Tuple[str, ...] = ("X1_0", "X4_0")
P275_VALID_FOCUS_MAGNIF_TIMES: Tuple[str, ...] = ("NO_LIMIT", "2_SEC", "5_SEC")
P275_VALID_PEAKING_LEVELS: Tuple[str, ...] = ("HIGH", "MID", "LOW")
P275_VALID_PEAKING_COLORS: Tuple[str, ...] = ("RED", "YELLOW", "BLUE", "WHITE")
P275_VALID_AF_ILLUMINATOR_MODES: Tuple[str, ...] = ("AUTO", "OFF")
P275_VALID_SHOOT_MODES: Tuple[str, ...] = ("PHOTO", "MOVIE", "S_AND_Q")
P275_VALID_FOCUS_MODES: Tuple[str, ...] = ("AF_S", "AF_C", "DMF", "MF")

P275_AREA_DATE_TIME_EXACT_LABEL: str = "Area/Date/Time Setting"
P275_AREA_DATE_TIME_FOUR_SUBITEMS: Tuple[str, ...] = (
    "Area Setting",
    "Daylight Savings",
    "Date/Time",
    "Date Format",
)
P275_VALID_VIDEO_LIGHT_MODES: Tuple[str, ...] = (
    "POWER_LINK",
    "REC_LINK",
    "REC_LINK_AND_STBY",
    "AUTO",
)
P275_MI_SHOE_5V_MAX_CURRENT_MA: int = 900
P275_VALID_HDMI_RESOLUTIONS: Tuple[str, ...] = ("AUTO", "2160P", "1080P", "1080I")
P275_VALID_REC_MEDIA_DUR_HDMI_MODES: Tuple[str, ...] = ("ON", "OFF", "OFF_HDMI_ONLY")

# Group D Constants (Wave 46 — Power Setting Option split, BK_LANG, Volume, 4ch Monitor & Delete Confirm)
P275_FX3_ILC2210_POWER_SETTING_TWO_ITEMS: Tuple[str, ...] = (
    "Power Save Start Time",
    "Auto Power OFF Temp.",
)
P275_VALID_POWER_SAVE_START_TIMES: Tuple[str, ...] = (
    "OFF",
    "30_MIN",
    "5_MIN",
    "2_MIN",
    "1_MIN",
    "10_SEC",
)
P275_SAFE_AIRGAPPED_BATTERY_POWER_SAVE_TIMES: Tuple[str, ...] = ("OFF", "30_MIN")
P275_POWER_SAVE_NINE_DEACTIVATION_CONDITIONS: Tuple[str, ...] = (
    "USB_POWER_SUPPLY",
    "SLIDESHOW_PLAYBACK",
    "FTP_TRANSFER",
    "MOVIE_RECORDING",
    "COMPUTER_CONNECTION",
    "TV_HDMI_CONNECTION",
    "IR_REMOTE_CTRL_ON",
    "BLUETOOTH_RMT_CTRL_ON",
    "STREAMING_OR_CREATORS_CLOUD",
)
P275_VALID_AUTO_POWER_OFF_TEMPS: Tuple[str, ...] = ("STANDARD", "HIGH")
P275_VALID_POWER_SOURCES: Tuple[str, ...] = (
    "INTERNAL_NP_FZ100",
    "USB_PD_BODY",
    "DC_C1_COUPLER",
)
P275_APPFW_MONITOR_POWER_LINKAGE_FOUR_MODES: Tuple[str, ...] = (
    "BOTH_LINKED",
    "OPEN_RETURN",
    "CLOSE_POWER_SAVE",
    "DOES_NOT_LINK",
)
P275_APPFW_MONITOR_POWER_LINKAGE_RESIDS: Dict[str, str] = {
    "BOTH_LINKED": "0x6db5",
    "OPEN_RETURN": "0x6db6",
    "CLOSE_POWER_SAVE": "0x60a8",
    "DOES_NOT_LINK": "0x6b2e",
}
P275_HEADLESS_SAFE_MONITOR_POWER_LINK_MODES: Tuple[str, ...] = (
    "DOES_NOT_LINK",
    "OPEN_RETURN",
)

P275_BKLANG_REGISTER_HEX: str = "0x02cf019c"
P275_FX3_LANGUAGE_COUNT: int = 34
P275_FX6_LANGUAGE_COUNT: int = 29
P275_FX3_BKLANG_FILE_OFFSET_HEX: str = "0x90ff0"
P275_FX6_BKLANG_FILE_OFFSET_HEX: str = "0x89242"
P275_BKLANG_FOUR_LANG_CODES: Dict[str, int] = {
    "en": 0x00,
    "japanese": 0x01,
    "tchinese": 0x18,
    "schinese": 0x19,
}

P275_VOLUME_SETTINGS_MIN: int = 0
P275_VOLUME_SETTINGS_MAX: int = 15
P275_VOLUME_SETTINGS_DEFAULT: int = 7
P275_4CH_AUDIO_MONITORING_FIVE_ROUTES: Tuple[str, ...] = (
    "CH1_CH2",
    "CH3_CH4",
    "CH1_3_CH2_4",
    "CH1_CH1",
    "CH2_CH2",
)
P275_VALID_DELETE_CONFIRM_MODES: Tuple[str, ...] = ("CANCEL_FIRST", "DELETE_FIRST")

# Error Codes
P275_GA_ERR_MODEL_OR_FW_FLOOR: str = "P275_GA_ERR_MODEL_OR_FW_FLOOR"
P275_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_OR_37CHAR: str = (
    "P275_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_OR_37CHAR"
)
P275_GA_ERR_STILL_PREFIX_DSC_UNDERSCORE_OR_SLOT1_VAULT_MUTATION: str = (
    "P275_GA_ERR_STILL_PREFIX_DSC_UNDERSCORE_OR_SLOT1_VAULT_MUTATION"
)
P275_GA_ERR_AUTO_REVIEW_OR_TCUB_6ITEM_RESET_PERSISTENCE: str = (
    "P275_GA_ERR_AUTO_REVIEW_OR_TCUB_6ITEM_RESET_PERSISTENCE"
)

P275_GB_ERR_GAMMA_ASSIST_LOG_LOCKOUT_VIOLATED: str = (
    "P275_GB_ERR_GAMMA_ASSIST_LOG_LOCKOUT_VIOLATED"
)
P275_GB_ERR_GAMMA_ASSIST_EXTERNAL_HDMI_BOUNDARY: str = (
    "P275_GB_ERR_GAMMA_ASSIST_EXTERNAL_HDMI_BOUNDARY"
)
P275_GB_ERR_DISPLAY_LUT_OR_SELECT_LUT_USER16_INVALID: str = (
    "P275_GB_ERR_DISPLAY_LUT_OR_SELECT_LUT_USER16_INVALID"
)

P275_GC_ERR_FOCUS_MAG_4X_CLEAN_HDMI_OR_RAW_LOCKOUT: str = (
    "P275_GC_ERR_FOCUS_MAG_4X_CLEAN_HDMI_OR_RAW_LOCKOUT"
)
P275_GC_ERR_PEAKING_OR_AF_ILLUMINATOR_MOVIE_AFC_LOCKOUT: str = (
    "P275_GC_ERR_PEAKING_OR_AF_ILLUMINATOR_MOVIE_AFC_LOCKOUT"
)
P275_GC_ERR_AREA_DATE_TIME_OR_ZERO_RF_CREATORS_APP_SYNC: str = (
    "P275_GC_ERR_AREA_DATE_TIME_OR_ZERO_RF_CREATORS_APP_SYNC"
)
P275_GC_ERR_VIDEO_LIGHT_MODE_OR_MI_SHOE_5V_900MA_OVERCURRENT: str = (
    "P275_GC_ERR_VIDEO_LIGHT_MODE_OR_MI_SHOE_5V_900MA_OVERCURRENT"
)
P275_GC_ERR_HDMI_RESOLUTION_LOG_1080P_OR_4K_DOWNSHIFT: str = (
    "P275_GC_ERR_HDMI_RESOLUTION_LOG_1080P_OR_4K_DOWNSHIFT"
)

P275_GD_ERR_POWER_SETTING_OPTION_REALITY_SPLIT_OR_9COND: str = (
    "P275_GD_ERR_POWER_SETTING_OPTION_REALITY_SPLIT_OR_9COND"
)
P275_GD_ERR_BKLANG_34_VS_29_OR_SETUP_RESET_PERSISTENCE: str = (
    "P275_GD_ERR_BKLANG_34_VS_29_OR_SETUP_RESET_PERSISTENCE"
)
P275_GD_ERR_VOLUME_OR_4CH_MONITORING_5ROUTE_OR_FEEDBACK: str = (
    "P275_GD_ERR_VOLUME_OR_4CH_MONITORING_5ROUTE_OR_FEEDBACK"
)
P275_GD_ERR_DELETE_CONFIRM_OR_SLOT1_VAULT_DELETE_FORMAT_BLOCKED: str = (
    "P275_GD_ERR_DELETE_CONFIRM_OR_SLOT1_VAULT_DELETE_FORMAT_BLOCKED"
)
P275_GD_ERR_H0_H3_IMMUTABILITY_DRIFT: str = "P275_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID: str = (
    "P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)

_TRIVIAL_HEX64_SET = {"0" * 64, "f" * 64}


# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase275DonorInspectionResult:
    passed: bool
    verification_mode: str
    read_only_o_rdonly_enforced: bool
    elapsed_seconds: float
    within_150ms_budget: bool
    inspected_artifacts: Tuple[str, ...]
    fx3_im_elf_verified: bool
    fx3_libjiritsu_verified: bool
    fx3_libusbbuspower_verified: bool
    fx6_appfw_verified: bool
    fx6_wlan_rsrc_verified: bool
    fx3_upm_ko_verified: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P275CheckGroupACinemaSlateTimecodeResult:
    check_group_id: str
    passed: bool
    body_model_id_hex: str
    body_fw: str
    sony_help_guide_id: str
    reset_action: str
    movie_file_number: str
    movie_file_name_format: str
    camera_id: str
    reel_number: int
    camera_position: str
    title_name_len: int
    movie_clip_fixed_dir: str
    movie_file_settings_survive_camera_reset: bool
    still_file_number: str
    still_file_prefix: str
    still_folder_name: str
    still_file_folder_survive_camera_reset: bool
    slot1_contains_tier0_dump: bool
    slot1_vault_folder_mutation_events: int
    auto_review: str
    effective_auto_review_after_reset: str
    auto_review_still_only_verified: bool
    tcub_six_items: Tuple[str, ...]
    tc_format: str
    effective_tc_format_after_reset: str
    tc_run: str
    tc_make: str
    tcub_disp_setting: str
    all_6_tcub_survive_camera_reset: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P275CheckGroupBGammaAssistDisplayLutCleanHdmiResult:
    check_group_id: str
    passed: bool
    log_shooting_mode: str
    gamma_display_assist: str
    effective_gamma_assist_after_reset: str
    gamma_disp_assist_type: str
    gamma_assist_locked_off_by_log: bool
    gamma_assist_lcd_only_clean_hdmi: bool
    external_hdmi_gamma_assist_pixels: int
    display_lut: str
    effective_display_lut_after_reset: str
    select_lut: str
    user_lut_slots_supported: int
    setup_lut_assist_survive_camera_reset: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P275CheckGroupCFocusMagPeakingTimeVideoLightHdmiResResult:
    check_group_id: str
    passed: bool
    auto_magnifier_in_mf: str
    auto_mag_label_verified: str
    focus_magnifier_custom_button: str
    focus_magnif_time: str
    initial_focus_mag_still: str
    initial_focus_mag_movie: str
    af_in_focus_mag: str
    hdmi_raw_output: bool
    focus_mag_clean_hdmi_isolated: bool
    hdmi_magnifier_baked_pixels: int
    peaking_display: str
    peaking_level: str
    peaking_color: str
    af_illuminator: str
    af_illuminator_still_only_verified: bool
    area_date_time_label_verified: str
    area_date_time_four_subitems: Tuple[str, ...]
    creators_app_location_linkage: str
    airplane_mode: str
    zero_rf_time_isolated: bool
    passive_tx_bytes_emitted: int
    video_light_mode: str
    mi_shoe_5v_current_ma: int
    mi_shoe_5v_budget_ok: bool
    hdmi_resolution: str
    rec_media_dur_hdmi_output: str
    effective_hdmi_output_class: str
    setup_items_survive_camera_reset: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P275CheckGroupDPowerMonitorBkLangVolumeDeleteTier0Result:
    check_group_id: str
    passed: bool
    power_setting_exposed_two_items: Tuple[str, ...]
    power_save_start_time: str
    auto_power_off_temp: str
    power_source: str
    power_save_nine_deactivation_count: int
    active_power_save_deactivations: Tuple[str, ...]
    power_save_by_monitor_exposed_in_fx3_ui: bool
    appfw_monitor_power_linkage_four_modes: Tuple[str, ...]
    headless_monitor_power_linkage_mode: str
    bklang_register_hex: str
    fx3_language_count: int
    fx6_language_count: int
    selected_lang: str
    selected_bklang_code_hex: str
    bklang_survives_camera_and_network_reset: bool
    volume_settings: int
    xlr_h1_attached: bool
    four_ch_audio_monitoring: str
    four_ch_monitoring_five_routes: Tuple[str, ...]
    headphone_35mm_2ch_only_verified: bool
    delete_confirm: str
    delete_pressing_twice: str
    slot1_vault_delete_events: int
    slot1_format_hard_locked: bool
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    tier0_receipt_present: bool
    tier0_receipt_verified: bool
    distinct_physical_media_verified: bool
    warnings: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwFileSettingsGammaAssistFocusMagVideoLightReport:
    schema: str
    phase_version: str
    verification_mode: str
    simulate_bench_dry_run: bool
    overall_status: str
    go_no_go: str
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    sd_physical_media_written: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    passive_tx_bytes_emitted: int
    slot1_vault_folder_mutation_events: int
    slot1_vault_delete_events: int
    slot1_format_hard_locked: bool
    power_save_by_monitor_exposed_in_fx3_ui: bool
    check_group_count: int
    check_groups_passed: int
    all_4_check_groups_passed: bool
    tier0_receipt_verified: bool
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    donor_inspection: Phase275DonorInspectionResult
    check_group_a_cinema_slate_and_timecode: P275CheckGroupACinemaSlateTimecodeResult
    check_group_b_gamma_assist_and_display_lut: P275CheckGroupBGammaAssistDisplayLutCleanHdmiResult
    check_group_c_focus_mag_videolight_and_hdmi_res: P275CheckGroupCFocusMagPeakingTimeVideoLightHdmiResResult
    check_group_d_power_bklang_volume_delete_and_tier0: P275CheckGroupDPowerMonitorBkLangVolumeDeleteTier0Result
    warnings: Tuple[str, ...]
    remediation_actions: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class Phase275ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal Helpers & Bounded O_RDONLY Donor Inspection (< 0.15s)
# ---------------------------------------------------------------------------


def _norm_token(raw: str) -> str:
    return re.sub(r"[\s\-:/\.]+", "_", str(raw).strip().upper()).strip("_")


def _norm_gamma_assist_type(raw: str) -> str:
    s = str(raw).strip().upper()
    s = s.replace("->", "_TO_").replace("→", "_TO_").replace("%", "PCT")
    tok = _norm_token(s)
    aliases = {
        "AUTO": "AUTO",
        "S_LOG3_TO_709(800PCT)": "S_LOG3_TO_709_800PCT",
        "S_LOG3_TO_709_800PCT": "S_LOG3_TO_709_800PCT",
        "S_LOG3_709_800PCT": "S_LOG3_TO_709_800PCT",
        "HLG(BT_2020)": "HLG_BT2020",
        "HLG_BT2020": "HLG_BT2020",
        "HLG_BT_2020": "HLG_BT2020",
        "HLG(709)": "HLG_709",
        "HLG_709": "HLG_709",
    }
    if tok in aliases:
        return aliases[tok]
    compact = re.sub(r"[()]", "", tok)
    return aliases.get(compact, compact)


def _norm_select_lut(raw: str) -> str:
    s = str(raw).strip()
    low = s.lower()
    if low in ("s-log3", "slog3", "s_log3"):
        return "S-Log3"
    if low == "s709":
        return "s709"
    if low in ("709(800%)", "709_800pct", "709(800pct)"):
        return "709(800%)"
    m = re.match(r"^user[\s_\-]*(\d+)$", low)
    if m:
        return f"User{int(m.group(1))}"
    return s


def _norm_focus_mag_scale(raw: str) -> str:
    s = str(raw).strip().upper().replace(".", "_")
    aliases = {
        "X1_0": "X1_0",
        "1_0X": "X1_0",
        "1X": "X1_0",
        "X1": "X1_0",
        "X4_0": "X4_0",
        "4_0X": "X4_0",
        "4X": "X4_0",
        "X4": "X4_0",
    }
    return aliases.get(s, _norm_token(raw))


def _norm_4ch_route(raw: str) -> str:
    s = str(raw).strip().upper()
    aliases = {
        "CH1/CH2": "CH1_CH2",
        "CH1_CH2": "CH1_CH2",
        "CH3/CH4": "CH3_CH4",
        "CH3_CH4": "CH3_CH4",
        "CH1+3/CH2+4": "CH1_3_CH2_4",
        "CH1_3_CH2_4": "CH1_3_CH2_4",
        "CH1/CH1": "CH1_CH1",
        "CH1_CH1": "CH1_CH1",
        "CH2/CH2": "CH2_CH2",
        "CH2_CH2": "CH2_CH2",
    }
    return aliases.get(s, _norm_token(raw))


def _norm_rec_media_hdmi(raw: str) -> str:
    s = str(raw).strip().upper()
    aliases = {
        "ON": "ON",
        "OFF": "OFF",
        "OFF(HDMI ONLY)": "OFF_HDMI_ONLY",
        "OFF_HDMI_ONLY": "OFF_HDMI_ONLY",
    }
    return aliases.get(s, _norm_token(raw))


def _norm_delete_confirm(raw: str) -> str:
    s = str(raw).strip().upper().replace('"', "").replace("'", "")
    aliases = {
        "CANCEL FIRST": "CANCEL_FIRST",
        "CANCEL_FIRST": "CANCEL_FIRST",
        "DELETE FIRST": "DELETE_FIRST",
        "DELETE_FIRST": "DELETE_FIRST",
    }
    return aliases.get(s, _norm_token(s))


def _canonical_sha256_dict(obj: Mapping[str, Any], exclude_key: Optional[str] = None) -> str:
    body = dict(copy.deepcopy(obj))
    if exclude_key:
        body.pop(exclude_key, None)
    donor_sub = body.get("donor_inspection")
    if isinstance(donor_sub, dict):
        donor_sub.pop("elapsed_seconds", None)
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def _is_trivial_hex64(val: str) -> bool:
    norm = str(val).strip().lower()
    if not HEX64_RE.match(norm):
        return True
    return norm in _TRIVIAL_HEX64_SET


def inspect_phase275_donors_bounded(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase275DonorInspectionResult:
    """Inspect local BYOF donors strictly via O_RDONLY within < 0.15s, or Clean-Room fallback."""
    t0 = time.perf_counter()
    errors: List[str] = []
    eff_clean = force_clean_room if force_clean_room is not None else synthetic_clean_room
    env_clean_room = is_forced_clean_room() or (
        os.environ.get("FX3_CLEAN_ROOM_TEST", "").strip().lower() in ("1", "true", "yes")
    )
    clean_room = env_clean_room if eff_clean is None else bool(eff_clean)

    fx3_im_path = resolve_work_subpath(FX3_IM_ELF_RELPATH, require_file=False)
    fx3_jit_path = resolve_work_subpath(LIBJIRITSU_RELPATH, require_file=False)
    fx3_usb_pwr_path = resolve_work_subpath(FX3_LIBUSBBUSPOWER_RELPATH, require_file=False)
    fx6_appfw_path = fx6_lib_dir / "appFw.so"
    fx6_wlan_path = fx6_lib_dir / "libWlanResource.so"
    fx3_upm_path = fx3_modules_dir / "upm.ko"

    donors_present = (
        fx3_im_path.is_file()
        and fx3_jit_path.is_file()
        and fx3_usb_pwr_path.is_file()
        and fx6_appfw_path.is_file()
        and fx6_wlan_path.is_file()
        and fx3_upm_path.is_file()
    )

    if eff_clean is False and not donors_present:
        elapsed = round(time.perf_counter() - t0, 6)
        return Phase275DonorInspectionResult(
            passed=False,
            verification_mode="LOCAL_DONOR_O_RDONLY",
            read_only_o_rdonly_enforced=True,
            elapsed_seconds=elapsed,
            within_150ms_budget=(elapsed < max_seconds),
            inspected_artifacts=(),
            fx3_im_elf_verified=fx3_im_path.is_file(),
            fx3_libjiritsu_verified=fx3_jit_path.is_file(),
            fx3_libusbbuspower_verified=fx3_usb_pwr_path.is_file(),
            fx6_appfw_verified=fx6_appfw_path.is_file(),
            fx6_wlan_rsrc_verified=fx6_wlan_path.is_file(),
            fx3_upm_ko_verified=fx3_upm_path.is_file(),
            raw_firmware_bytes_leaked=PHASE275_RAW_FIRMWARE_BYTES_LEAKED,
            errors=(f"Local BYOF donors missing under fx6_lib_dir={fx6_lib_dir}",),
        )

    use_live = (not clean_room) and donors_present
    mode = "LOCAL_DONOR_O_RDONLY" if use_live else "CLEAN_ROOM_SYNTHETIC"
    inspected: List[str] = []

    if use_live:
        im_sz, im_sha, im_head = read_only_o_rdonly_digest_and_header(fx3_im_path)
        im_mag, im_64, im_mach, _ = _parse_elf64_header_and_pt_load(im_head)
        im_ok = (
            im_sz == FX3_IM_ELF_EXPECTED_SIZE
            and im_sha == FX3_IM_ELF_EXPECTED_SHA256
            and im_mag
            and im_64
            and im_mach == EM_AARCH64
        )
        inspected.append("im.elf")
        if not im_ok:
            errors.append(f"im.elf O_RDONLY verification failed: size={im_sz}")

        jit_sz, jit_sha, jit_head = read_only_o_rdonly_digest_and_header(fx3_jit_path)
        jit_mag, jit_64, jit_mach, _ = _parse_elf64_header_and_pt_load(jit_head)
        jit_ok = (
            jit_sz == LIBJIRITSU_EXPECTED_SIZE
            and jit_sha == LIBJIRITSU_EXPECTED_SHA256
            and jit_mag
            and jit_64
            and jit_mach == EM_AARCH64
        )
        inspected.append("libJiritsu.so")
        if not jit_ok:
            errors.append(f"libJiritsu.so O_RDONLY verification failed: size={jit_sz}")

        pwr_sz, pwr_sha, pwr_head = read_only_o_rdonly_digest_and_header(fx3_usb_pwr_path)
        pwr_mag, pwr_64, pwr_mach, _ = _parse_elf64_header_and_pt_load(pwr_head)
        pwr_ok = (
            pwr_sz == FX3_LIBUSBBUSPOWER_EXPECTED_SIZE
            and pwr_sha == FX3_LIBUSBBUSPOWER_EXPECTED_SHA256
            and pwr_mag
            and pwr_64
            and pwr_mach == EM_AARCH64
        )
        inspected.append("libUsbBusPower.so")
        if not pwr_ok:
            errors.append(f"libUsbBusPower.so O_RDONLY verification failed: size={pwr_sz}")

        appfw_sz, appfw_head, _ = _read_bounded_slice_o_rdonly(fx6_appfw_path, 4096)
        appfw_mag, appfw_64, appfw_mach, _ = _parse_elf64_header_and_pt_load(appfw_head)
        appfw_ok = (
            appfw_sz == FX6_APPFW_EXPECTED_SIZE
            and appfw_mag
            and appfw_64
            and appfw_mach == EM_AARCH64
        )
        inspected.append("appFw.so(bounded-4KiB)")
        if not appfw_ok:
            errors.append(f"appFw.so bounded O_RDONLY header failed: size={appfw_sz}")

        wlan_sz, wlan_sha, wlan_head = read_only_o_rdonly_digest_and_header(fx6_wlan_path)
        wlan_mag, wlan_64, wlan_mach, _ = _parse_elf64_header_and_pt_load(wlan_head)
        wlan_ok = (
            wlan_sz > 0
            and wlan_sha == FX6_WLAN_RSRC_DONOR_SHA256
            and wlan_mag
            and wlan_64
            and wlan_mach == EM_AARCH64
        )
        inspected.append("libWlanResource.so")
        if not wlan_ok:
            errors.append("libWlanResource.so O_RDONLY SHA-256 verification failed")

        upm_sz, upm_head, _ = _read_bounded_slice_o_rdonly(fx3_upm_path, 4096)
        upm_mag, upm_64, upm_mach, _ = _parse_elf64_header_and_pt_load(upm_head)
        upm_ok = upm_sz > 0 and upm_mag and upm_64 and upm_mach == EM_AARCH64
        inspected.append("upm.ko(bounded-4KiB)")
        if not upm_ok:
            errors.append(f"upm.ko bounded O_RDONLY header failed: size={upm_sz}")
    else:
        im_ok = jit_ok = pwr_ok = appfw_ok = wlan_ok = upm_ok = True
        inspected.extend(
            [
                "synthetic:im.elf",
                "synthetic:libJiritsu.so",
                "synthetic:libUsbBusPower.so",
                "synthetic:appFw.so",
                "synthetic:libWlanResource.so",
                "synthetic:upm.ko",
            ]
        )

    elapsed = round(time.perf_counter() - t0, 6)
    within_budget = elapsed < max_seconds
    if not within_budget:
        errors.append(f"Donor inspection exceeded {max_seconds:.3f}s budget: {elapsed:.6f}s")

    return Phase275DonorInspectionResult(
        passed=(len(errors) == 0),
        verification_mode=mode,
        read_only_o_rdonly_enforced=True,
        elapsed_seconds=elapsed,
        within_150ms_budget=within_budget,
        inspected_artifacts=tuple(inspected),
        fx3_im_elf_verified=im_ok,
        fx3_libjiritsu_verified=jit_ok,
        fx3_libusbbuspower_verified=pwr_ok,
        fx6_appfw_verified=appfw_ok,
        fx6_wlan_rsrc_verified=wlan_ok,
        fx3_upm_ko_verified=upm_ok,
        raw_firmware_bytes_leaked=PHASE275_RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Bench Check 1 / Group A (Wave 44): Cinema Slate Naming, Auto Review & TC/UB Persistence
# ---------------------------------------------------------------------------


def evaluate_p275_check_group_a_cinema_slate_and_timecode(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P275_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    # Movie [File Settings]
    movie_file_number: str = "SERIES",
    movie_file_name_format: str = "CAM_ID_PLUS_REEL",
    camera_id: str = "A",
    reel_number: int = 1,
    camera_position: str = "C",
    title_name: str = P275_DEFAULT_TITLE_NAME,
    movie_clip_dir: str = P275_MOVIE_FIXED_CLIP_DIR,
    custom_movie_folder_requested: bool = False,
    claimed_movie_file_settings_reset_on_camera_reset: bool = False,
    claimed_title_name_after_reset: Optional[str] = None,
    # Still [File/Folder Settings] & Slot-1 Vault Guard
    still_file_number: str = "SERIES",
    still_file_prefix: str = P275_DEFAULT_STILL_FILE_PREFIX,
    still_folder_name: str = "STANDARD_FORM",
    claimed_still_file_settings_reset_on_camera_reset: bool = False,
    claimed_still_prefix_after_reset: Optional[str] = None,
    slot1_contains_tier0_dump: bool = True,
    still_forced_file_number_reset_slot: Optional[int] = None,
    still_create_new_folder_slot: Optional[int] = None,
    expect_slot1_dcim_mutation_allowed: bool = False,
    simulated_slot1_vault_folder_mutation_events: int = 0,
    # [Auto Review]
    auto_review: str = "OFF",
    require_cinema_auto_review_off: bool = True,
    claimed_auto_review_after_reset: Optional[str] = None,
    expect_auto_review_in_movie: bool = False,
    # [TC/UB] 6-item persistence
    tcub_items: Sequence[str] = P275_TCUB_SIX_ITEMS,
    tc_format: str = "NDF",
    rec_frame_rate_fps: float = 23.98,
    video_system: str = "NTSC",
    tc_run: str = "FREE_RUN",
    tc_make: str = "PRESET",
    tcub_disp_setting: str = "TC",
    claimed_tc_format_after_reset: Optional[str] = None,
    claimed_tcub_reset_on_camera_reset: bool = False,
) -> P275CheckGroupACinemaSlateTimecodeResult:
    """Verify Wave 44 Movie/Still File Settings, Slot-1 DCIM Vault Guard, Auto Review & TC/UB."""
    errors: List[str] = []

    # 0. Model, Firmware & Help Guide Gate
    fw_tuple = _parse_fw_tuple(body_fw)
    if (
        int(body_model_id) != TARGET_MODEL_ID_INT
        or fw_tuple is None
        or fw_tuple < MIN_BODY_FW_TUPLE
        or str(sony_help_guide_id).strip() != P275_SONY_HELP_GUIDE_ID
    ):
        errors.append(
            f"{P275_GA_ERR_MODEL_OR_FW_FLOOR}: expected ILME-FX3 (0x{TARGET_MODEL_ID_INT:08x}), "
            f"fw >= 2.04, guide={P275_SONY_HELP_GUIDE_ID!r}; got model=0x{int(body_model_id):08x}, "
            f"fw={body_fw!r}, guide={sony_help_guide_id!r}"
        )

    rst_norm = _norm_token(reset_action)
    if rst_norm not in P275_VALID_RESET_ACTIONS:
        errors.append(
            f"{P275_GA_ERR_AUTO_REVIEW_OR_TCUB_6ITEM_RESET_PERSISTENCE}: invalid reset_action={reset_action!r}"
        )

    # 1. Movie [File Settings]
    mv_num = _norm_token(movie_file_number)
    mv_fmt = _norm_token(movie_file_name_format)
    cam_id = str(camera_id).strip()
    cam_pos = str(camera_position).strip().upper()
    title_str = str(title_name)
    title_len = len(title_str)
    title_ascii = all(32 <= ord(ch) <= 126 for ch in title_str)
    clip_dir = str(movie_clip_dir).strip().rstrip("/")

    # Under CAMERA_SETTINGS_RESET Movie [File Settings] survives; only INITIALIZE resets to "C"
    eff_title_after_reset = P275_DEFAULT_TITLE_NAME if rst_norm == "INITIALIZE" else title_str
    mv_survives = not bool(claimed_movie_file_settings_reset_on_camera_reset)
    if claimed_title_name_after_reset is not None and str(claimed_title_name_after_reset) != eff_title_after_reset:
        mv_survives = False

    if (
        mv_num not in P275_VALID_FILE_NUMBER_MODES
        or mv_fmt not in P275_VALID_MOVIE_FILE_NAME_FORMATS
        or not P275_CAMERA_ID_RE.match(cam_id)
        or not (P275_REEL_NUMBER_MIN <= int(reel_number) <= P275_REEL_NUMBER_MAX)
        or cam_pos not in P275_VALID_CAMERA_POSITIONS
        or title_len < 1
        or title_len > P275_TITLE_NAME_MAX_CHARS
        or not title_ascii
        or clip_dir != P275_MOVIE_FIXED_CLIP_DIR
        or bool(custom_movie_folder_requested)
        or not mv_survives
    ):
        errors.append(
            f"{P275_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_OR_37CHAR}: Movie [File Settings] "
            f"violated (num={movie_file_number!r}, fmt={movie_file_name_format!r}, "
            f"cam_id={camera_id!r}, reel={reel_number}, pos={camera_position!r}, "
            f"title_len={title_len}, clip_dir={movie_clip_dir!r}, custom_dir={custom_movie_folder_requested}, "
            f"survives_reset={mv_survives})"
        )

    # 2. Still [File/Folder Settings] & Slot-1 DCIM Recovery Vault Firewall
    st_num = _norm_token(still_file_number)
    st_prefix = str(still_file_prefix).strip()
    st_folder = _norm_token(still_folder_name)
    prefix_ok = (
        len(st_prefix) == P275_STILL_PREFIX_LEN
        and bool(P275_STILL_PREFIX_NO_LEADING_UNDERSCORE_RE.match(st_prefix))
    )
    eff_prefix_after_reset = P275_DEFAULT_STILL_FILE_PREFIX if rst_norm == "INITIALIZE" else st_prefix
    st_survives = not bool(claimed_still_file_settings_reset_on_camera_reset)
    if (
        claimed_still_prefix_after_reset is not None
        and str(claimed_still_prefix_after_reset).strip() != eff_prefix_after_reset
    ):
        st_survives = False

    slot1_mut = max(0, int(simulated_slot1_vault_folder_mutation_events))
    if bool(slot1_contains_tier0_dump) and (
        still_forced_file_number_reset_slot == 1
        or still_create_new_folder_slot == 1
        or bool(expect_slot1_dcim_mutation_allowed)
    ):
        slot1_mut = max(1, slot1_mut)

    if (
        st_num not in P275_VALID_FILE_NUMBER_MODES
        or not prefix_ok
        or st_folder not in P275_VALID_STILL_FOLDER_NAMES
        or not st_survives
        or slot1_mut > 0
    ):
        errors.append(
            f"{P275_GA_ERR_STILL_PREFIX_DSC_UNDERSCORE_OR_SLOT1_VAULT_MUTATION}: Still "
            f"[File/Folder Settings] or Slot-1 vault firewall violated (prefix={still_file_prefix!r}, "
            f"folder={still_folder_name!r}, survives_reset={st_survives}, slot1_mut={slot1_mut})"
        )

    # 3. [Auto Review] = [Off] & [TC/UB] 6-item persistence across [Camera Settings Reset]
    ar_norm = _norm_token(auto_review)
    eff_ar = "OFF" if rst_norm == "INITIALIZE" else ar_norm
    ar_reset_ok = (
        claimed_auto_review_after_reset is None
        or _norm_token(claimed_auto_review_after_reset) == eff_ar
    )
    ar_still_only = not bool(expect_auto_review_in_movie)

    tcub_norm = tuple(str(x).strip() for x in tcub_items)
    tcf_norm = _norm_token(tc_format)
    tcr_norm = _norm_token(tc_run)
    tcm_norm = _norm_token(tc_make)
    tcub_disp_norm = _norm_token(tcub_disp_setting)
    sys_norm = _norm_token(video_system)
    fps = float(rec_frame_rate_fps)

    # Sony forces NDF on 24.00p and all PAL frame rates (25p/50p/100p)
    ndf_forced = (sys_norm == "PAL") or abs(fps - 24.0) < 0.01 or abs(fps - 25.0) < 0.01 or abs(fps - 50.0) < 0.01
    tc_format_valid = (tcf_norm in P275_VALID_TC_FORMATS) and (not ndf_forced or tcf_norm == "NDF")

    eff_tcf = "DF" if rst_norm == "INITIALIZE" else tcf_norm
    tcub_survives = not bool(claimed_tcub_reset_on_camera_reset)
    if (
        claimed_tc_format_after_reset is not None
        and _norm_token(claimed_tc_format_after_reset) != eff_tcf
    ):
        tcub_survives = False

    if (
        ar_norm not in P275_VALID_AUTO_REVIEW_MODES
        or (bool(require_cinema_auto_review_off) and ar_norm != "OFF")
        or not ar_reset_ok
        or not ar_still_only
        or tcub_norm != P275_TCUB_SIX_ITEMS
        or not tc_format_valid
        or tcr_norm not in P275_VALID_TC_RUN_MODES
        or tcm_norm not in P275_VALID_TC_MAKE_MODES
        or tcub_disp_norm not in P275_VALID_TCUB_DISP_SETTINGS
        or not tcub_survives
    ):
        errors.append(
            f"{P275_GA_ERR_AUTO_REVIEW_OR_TCUB_6ITEM_RESET_PERSISTENCE}: [Auto Review] or [TC/UB] "
            f"6-item persistence violated (auto_review={auto_review!r}, ar_reset_ok={ar_reset_ok}, "
            f"ar_still_only={ar_still_only}, tcub_len={len(tcub_norm)}, tc_format={tc_format!r}, "
            f"tc_run={tc_run!r}, tc_make={tc_make!r}, tcub_survives={tcub_survives})"
        )

    return P275CheckGroupACinemaSlateTimecodeResult(
        check_group_id=P275_CHECK_GROUP_A_ID,
        passed=(len(errors) == 0),
        body_model_id_hex=f"0x{int(body_model_id):08x}",
        body_fw=str(body_fw).strip(),
        sony_help_guide_id=str(sony_help_guide_id).strip(),
        reset_action=rst_norm,
        movie_file_number=mv_num,
        movie_file_name_format=mv_fmt,
        camera_id=cam_id,
        reel_number=int(reel_number),
        camera_position=cam_pos,
        title_name_len=title_len,
        movie_clip_fixed_dir=clip_dir,
        movie_file_settings_survive_camera_reset=mv_survives,
        still_file_number=st_num,
        still_file_prefix=st_prefix,
        still_folder_name=st_folder,
        still_file_folder_survive_camera_reset=st_survives,
        slot1_contains_tier0_dump=bool(slot1_contains_tier0_dump),
        slot1_vault_folder_mutation_events=slot1_mut,
        auto_review=ar_norm,
        effective_auto_review_after_reset=eff_ar,
        auto_review_still_only_verified=ar_still_only,
        tcub_six_items=tcub_norm,
        tc_format=tcf_norm,
        effective_tc_format_after_reset=eff_tcf,
        tc_run=tcr_norm,
        tc_make=tcm_norm,
        tcub_disp_setting=tcub_disp_norm,
        all_6_tcub_survive_camera_reset=tcub_survives,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Bench Check 2 / Group B (Wave 44): [Gamma Display Assist] vs [Display LUT] / [Select LUT]
# ---------------------------------------------------------------------------


def evaluate_p275_check_group_b_gamma_assist_and_display_lut(
    *,
    log_shooting_mode: str = "CINE_EI",
    gamma_display_assist: str = "OFF",
    gamma_disp_assist_type: str = "AUTO",
    expect_gamma_assist_active_under_log: bool = False,
    expect_gamma_assist_on_external_hdmi: bool = False,
    simulated_external_hdmi_gamma_assist_pixels: int = 0,
    display_lut: str = "ON",
    select_lut: str = "s709",
    user_lut_slot_count: int = P275_USER_LUT_MAX_SLOTS,
    reset_action: str = "NONE",
    claimed_gamma_assist_after_reset: Optional[str] = None,
    claimed_display_lut_after_reset: Optional[str] = None,
    claimed_setup_lut_reset_on_camera_reset: bool = False,
) -> P275CheckGroupBGammaAssistDisplayLutCleanHdmiResult:
    """Verify Wave 44 [Gamma Display Assist] Log lockout & Clean-HDMI vs [Display LUT]/[Select LUT]."""
    errors: List[str] = []

    log_norm = _norm_token(log_shooting_mode)
    gda_norm = _norm_token(gamma_display_assist)
    gda_type = _norm_gamma_assist_type(gamma_disp_assist_type)
    dlut_norm = _norm_token(display_lut)
    slut_norm = _norm_select_lut(select_lut)
    rst_norm = _norm_token(reset_action)

    log_active = log_norm in P275_ACTIVE_LOG_SHOOTING_MODES
    locked_off_by_log = log_active and (gda_norm == "OFF") and not bool(expect_gamma_assist_active_under_log)

    if (
        log_norm not in P275_VALID_LOG_SHOOTING_MODES
        or gda_norm not in ("ON", "OFF")
        or gda_type not in P275_VALID_GAMMA_ASSIST_TYPES
        or (log_active and (gda_norm != "OFF" or bool(expect_gamma_assist_active_under_log)))
    ):
        errors.append(
            f"{P275_GB_ERR_GAMMA_ASSIST_LOG_LOCKOUT_VIOLATED}: [Gamma Display Assist] must be "
            f"hard-locked Off whenever [Log Shooting] != Off (log={log_shooting_mode!r}, "
            f"assist={gamma_display_assist!r}, type={gamma_disp_assist_type!r}, "
            f"expect_active_under_log={expect_gamma_assist_active_under_log})"
        )

    ext_hdmi_px = max(0, int(simulated_external_hdmi_gamma_assist_pixels))
    if bool(expect_gamma_assist_on_external_hdmi):
        ext_hdmi_px = max(1, ext_hdmi_px)
    lcd_only_clean_hdmi = ext_hdmi_px == 0 and not bool(expect_gamma_assist_on_external_hdmi)
    if not lcd_only_clean_hdmi:
        errors.append(
            f"{P275_GB_ERR_GAMMA_ASSIST_EXTERNAL_HDMI_BOUNDARY}: [Gamma Display Assist] is "
            f"strictly internal LCD only (external HDMI must remain clean, ext_px={ext_hdmi_px})"
        )

    eff_gda = "OFF" if rst_norm == "INITIALIZE" else gda_norm
    eff_dlut = "ON" if rst_norm == "INITIALIZE" else dlut_norm
    setup_survives = not bool(claimed_setup_lut_reset_on_camera_reset)
    if (
        claimed_gamma_assist_after_reset is not None
        and _norm_token(claimed_gamma_assist_after_reset) != eff_gda
    ):
        setup_survives = False
    if (
        claimed_display_lut_after_reset is not None
        and _norm_token(claimed_display_lut_after_reset) != eff_dlut
    ):
        setup_survives = False

    if (
        dlut_norm not in ("ON", "OFF")
        or slut_norm not in P275_VALID_SELECT_LUTS
        or int(user_lut_slot_count) != P275_USER_LUT_MAX_SLOTS
        or not setup_survives
    ):
        errors.append(
            f"{P275_GB_ERR_DISPLAY_LUT_OR_SELECT_LUT_USER16_INVALID}: [Display LUT] / [Select LUT] "
            f"or Setup reset survival violated (display_lut={display_lut!r}, select_lut={select_lut!r}, "
            f"user_slots={user_lut_slot_count}, setup_survives={setup_survives})"
        )

    return P275CheckGroupBGammaAssistDisplayLutCleanHdmiResult(
        check_group_id=P275_CHECK_GROUP_B_ID,
        passed=(len(errors) == 0),
        log_shooting_mode=log_norm,
        gamma_display_assist=gda_norm,
        effective_gamma_assist_after_reset=eff_gda,
        gamma_disp_assist_type=gda_type,
        gamma_assist_locked_off_by_log=locked_off_by_log,
        gamma_assist_lcd_only_clean_hdmi=lcd_only_clean_hdmi,
        external_hdmi_gamma_assist_pixels=ext_hdmi_px,
        display_lut=dlut_norm,
        effective_display_lut_after_reset=eff_dlut,
        select_lut=slut_norm,
        user_lut_slots_supported=int(user_lut_slot_count),
        setup_lut_assist_survive_camera_reset=setup_survives,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Bench Check 3 / Group C (Wave 45): Focus Magnifier, Peaking, Zero-RF Time, Video Light & HDMI Res
# ---------------------------------------------------------------------------


def evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
    *,
    # [Focus Assistant] & [Focus Magnifier]
    auto_magnifier_in_mf: str = "ON",
    auto_mag_label: str = P275_AUTO_MAG_IN_MF_EXACT_LABEL,
    focus_magnifier_custom_button: str = P275_FOCUS_MAG_DEFAULT_CUSTOM_BUTTON,
    focus_magnif_time: str = "NO_LIMIT",
    initial_focus_mag_still: str = "X1_0",
    initial_focus_mag_movie: str = "X1_0",
    af_in_focus_mag: str = "ON",
    hdmi_raw_output: bool = False,
    focus_magnifier_active: bool = False,
    expect_focus_mag_allowed_in_raw: bool = False,
    expect_magnifier_baked_on_clean_hdmi: bool = False,
    simulated_hdmi_magnifier_baked_pixels: int = 0,
    # [Peaking Display] & [AF Illuminator]
    peaking_display: str = "OFF",
    peaking_level: str = "MID",
    peaking_color: str = "WHITE",
    af_illuminator: str = "AUTO",
    shoot_mode: str = "MOVIE",
    focus_mode: str = "MF",
    expect_af_illuminator_fires_in_movie_or_afc: bool = False,
    # [Area/Date/Time Setting] & Zero-RF Creators' App Isolation
    area_date_time_label: str = P275_AREA_DATE_TIME_EXACT_LABEL,
    area_date_time_subitems: Sequence[str] = P275_AREA_DATE_TIME_FOUR_SUBITEMS,
    area_date_time_manual_airgapped: bool = True,
    creators_app_location_linkage: str = "OFF",
    airplane_mode: str = "ON",
    bluetooth_function: str = "OFF",
    expect_creators_app_auto_time_sync: bool = False,
    simulated_passive_tx_bytes: int = 0,
    # [Video Light Mode] & MI-Shoe 5V Overcurrent Guard
    video_light_mode: str = "POWER_LINK",
    mi_shoe_5v_current_ma: int = 0,
    expect_mi_shoe_5v_overcurrent_allowed: bool = False,
    # [HDMI Resolution] & Log 1080p Lockout
    hdmi_resolution: str = "AUTO",
    log_shooting_mode: str = "CINE_EI",
    rec_media_dur_hdmi_output: str = "ON",
    expect_4k_hdmi_log_with_internal_rec: bool = False,
    reset_action: str = "NONE",
    claimed_setup_c_items_reset_on_camera_reset: bool = False,
) -> P275CheckGroupCFocusMagPeakingTimeVideoLightHdmiResResult:
    """Verify Wave 45 Focus Magnifier, Peaking, AF Illuminator, Area/Date/Time, Video Light & HDMI Res."""
    errors: List[str] = []

    # 1. [Focus Magnifier] / [Focus Assistant]
    am_norm = _norm_token(auto_magnifier_in_mf)
    am_label = str(auto_mag_label).strip()
    fm_btn = str(focus_magnifier_custom_button).strip()
    fm_time = _norm_token(focus_magnif_time)
    fm_still = _norm_focus_mag_scale(initial_focus_mag_still)
    fm_movie = _norm_focus_mag_scale(initial_focus_mag_movie)
    af_in_mag = _norm_token(af_in_focus_mag)
    baked_px = max(0, int(simulated_hdmi_magnifier_baked_pixels))
    if bool(expect_magnifier_baked_on_clean_hdmi):
        baked_px = max(1, baked_px)
    hdmi_clean_ok = baked_px == 0 and not bool(expect_magnifier_baked_on_clean_hdmi)
    raw_conflict = bool(hdmi_raw_output) and (
        bool(focus_magnifier_active) or bool(expect_focus_mag_allowed_in_raw)
    )

    if (
        am_norm not in ("ON", "OFF")
        or am_label != P275_AUTO_MAG_IN_MF_EXACT_LABEL
        or not fm_btn
        or fm_time not in P275_VALID_FOCUS_MAGNIF_TIMES
        or fm_still not in P275_VALID_FOCUS_MAG_SCALES
        or fm_movie not in P275_VALID_FOCUS_MAG_SCALES
        or af_in_mag not in ("ON", "OFF")
        or not hdmi_clean_ok
        or raw_conflict
    ):
        errors.append(
            f"{P275_GC_ERR_FOCUS_MAG_4X_CLEAN_HDMI_OR_RAW_LOCKOUT}: [Focus Magnifier] / "
            f"[Focus Assistant] violated (label={auto_mag_label!r}, time={focus_magnif_time!r}, "
            f"still={initial_focus_mag_still!r}, movie={initial_focus_mag_movie!r}, "
            f"hdmi_raw={hdmi_raw_output}, mag_active={focus_magnifier_active}, baked_px={baked_px})"
        )

    # 2. [Peaking Display] & [AF Illuminator] (Still-only / Movie & AF-C lockout)
    pk_norm = _norm_token(peaking_display)
    pk_lvl = _norm_token(peaking_level)
    pk_col = _norm_token(peaking_color)
    afi_norm = _norm_token(af_illuminator)
    sh_mode = _norm_token(shoot_mode)
    fc_mode = _norm_token(focus_mode)

    af_illum_locked_out = (sh_mode in ("MOVIE", "S_AND_Q")) or (fc_mode == "AF_C")
    af_illum_still_only_ok = not bool(expect_af_illuminator_fires_in_movie_or_afc)

    if (
        pk_norm not in ("ON", "OFF")
        or pk_lvl not in P275_VALID_PEAKING_LEVELS
        or pk_col not in P275_VALID_PEAKING_COLORS
        or afi_norm not in P275_VALID_AF_ILLUMINATOR_MODES
        or sh_mode not in P275_VALID_SHOOT_MODES
        or fc_mode not in P275_VALID_FOCUS_MODES
        or not af_illum_still_only_ok
        or (af_illum_locked_out and bool(expect_af_illuminator_fires_in_movie_or_afc))
    ):
        errors.append(
            f"{P275_GC_ERR_PEAKING_OR_AF_ILLUMINATOR_MOVIE_AFC_LOCKOUT}: [Peaking Display] or "
            f"[AF Illuminator] Movie/AF-C lockout violated (peaking={peaking_display!r}/{peaking_level!r}/{peaking_color!r}, "
            f"af_illum={af_illuminator!r}, shoot={shoot_mode!r}, focus={focus_mode!r}, "
            f"expect_fires_movie_afc={expect_af_illuminator_fires_in_movie_or_afc})"
        )

    # 3. [Area/Date/Time Setting] & Zero-RF Creators' App Isolation
    adt_label = str(area_date_time_label).strip()
    adt_items = tuple(str(x).strip() for x in area_date_time_subitems)
    ca_link = _norm_token(creators_app_location_linkage)
    air_norm = _norm_token(airplane_mode)
    bt_norm = _norm_token(bluetooth_function)
    passive_tx = max(0, int(simulated_passive_tx_bytes))
    zero_rf_ok = (
        bool(area_date_time_manual_airgapped)
        and ca_link == "OFF"
        and air_norm == "ON"
        and bt_norm == "OFF"
        and not bool(expect_creators_app_auto_time_sync)
        and passive_tx == 0
    )
    if (
        adt_label != P275_AREA_DATE_TIME_EXACT_LABEL
        or adt_items != P275_AREA_DATE_TIME_FOUR_SUBITEMS
        or not zero_rf_ok
    ):
        errors.append(
            f"{P275_GC_ERR_AREA_DATE_TIME_OR_ZERO_RF_CREATORS_APP_SYNC}: [Area/Date/Time Setting] "
            f"or zero-RF Creators' App isolation violated (label={area_date_time_label!r}, "
            f"ca_link={creators_app_location_linkage!r}, airplane={airplane_mode!r}, "
            f"bt={bluetooth_function!r}, passive_tx={passive_tx})"
        )

    # 4. [Video Light Mode] & MI-Shoe 5V <= 900mA PMIC Budget Guard
    vl_mode = _norm_token(video_light_mode)
    cur_ma = int(mi_shoe_5v_current_ma)
    mi_budget_ok = (0 <= cur_ma <= P275_MI_SHOE_5V_MAX_CURRENT_MA) and not bool(
        expect_mi_shoe_5v_overcurrent_allowed
    )
    if vl_mode not in P275_VALID_VIDEO_LIGHT_MODES or not mi_budget_ok:
        errors.append(
            f"{P275_GC_ERR_VIDEO_LIGHT_MODE_OR_MI_SHOE_5V_900MA_OVERCURRENT}: [Video Light Mode] "
            f"or MI-Shoe 5V<=900mA overcurrent guard violated (mode={video_light_mode!r}, "
            f"current_ma={cur_ma}, expect_overcurrent={expect_mi_shoe_5v_overcurrent_allowed})"
        )

    # 5. [HDMI Resolution] & Log 1080p/1080i Downshift + HDMI RAW Rules + Setup Reset Persistence
    hdmi_res = _norm_token(hdmi_resolution)
    log_norm = _norm_token(log_shooting_mode)
    rec_media = _norm_rec_media_hdmi(rec_media_dur_hdmi_output)
    rst_norm = _norm_token(reset_action)
    if rst_norm not in P275_VALID_RESET_ACTIONS:
        errors.append(
            f"{P275_GC_ERR_HDMI_RESOLUTION_LOG_1080P_OR_4K_DOWNSHIFT}: invalid reset_action={reset_action!r}"
        )
    setup_survives = not bool(claimed_setup_c_items_reset_on_camera_reset)

    log_active = log_norm in P275_ACTIVE_LOG_SHOOTING_MODES
    internal_rec_active = rec_media == "ON"
    if bool(hdmi_raw_output):
        eff_hdmi_class = "RAW_4264X2408_16BIT"
    elif log_active and internal_rec_active:
        eff_hdmi_class = "1080P_LOG_DOWNSHIFT"
    elif hdmi_res in ("1080P", "1080I"):
        eff_hdmi_class = hdmi_res
    else:
        eff_hdmi_class = "4K_2160P_COMPATIBLE"

    if (
        hdmi_res not in P275_VALID_HDMI_RESOLUTIONS
        or log_norm not in P275_VALID_LOG_SHOOTING_MODES
        or rec_media not in P275_VALID_REC_MEDIA_DUR_HDMI_MODES
        or (log_active and internal_rec_active and not bool(hdmi_raw_output) and hdmi_res == "2160P")
        or (bool(hdmi_raw_output) and hdmi_res == "2160P")
        or (log_active and internal_rec_active and bool(expect_4k_hdmi_log_with_internal_rec))
        or not setup_survives
    ):
        errors.append(
            f"{P275_GC_ERR_HDMI_RESOLUTION_LOG_1080P_OR_4K_DOWNSHIFT}: [HDMI Resolution] Log "
            f"1080p downshift / RAW / Setup persistence violated (res={hdmi_resolution!r}, "
            f"log={log_shooting_mode!r}, rec_media={rec_media_dur_hdmi_output!r}, "
            f"hdmi_raw={hdmi_raw_output}, expect_4k_internal={expect_4k_hdmi_log_with_internal_rec}, "
            f"setup_survives={setup_survives})"
        )

    return P275CheckGroupCFocusMagPeakingTimeVideoLightHdmiResResult(
        check_group_id=P275_CHECK_GROUP_C_ID,
        passed=(len(errors) == 0),
        auto_magnifier_in_mf=am_norm,
        auto_mag_label_verified=am_label,
        focus_magnifier_custom_button=fm_btn,
        focus_magnif_time=fm_time,
        initial_focus_mag_still=fm_still,
        initial_focus_mag_movie=fm_movie,
        af_in_focus_mag=af_in_mag,
        hdmi_raw_output=bool(hdmi_raw_output),
        focus_mag_clean_hdmi_isolated=hdmi_clean_ok,
        hdmi_magnifier_baked_pixels=baked_px,
        peaking_display=pk_norm,
        peaking_level=pk_lvl,
        peaking_color=pk_col,
        af_illuminator=afi_norm,
        af_illuminator_still_only_verified=af_illum_still_only_ok,
        area_date_time_label_verified=adt_label,
        area_date_time_four_subitems=adt_items,
        creators_app_location_linkage=ca_link,
        airplane_mode=air_norm,
        zero_rf_time_isolated=zero_rf_ok,
        passive_tx_bytes_emitted=passive_tx,
        video_light_mode=vl_mode,
        mi_shoe_5v_current_ma=cur_ma,
        mi_shoe_5v_budget_ok=mi_budget_ok,
        hdmi_resolution=hdmi_res,
        rec_media_dur_hdmi_output=rec_media,
        effective_hdmi_output_class=eff_hdmi_class,
        setup_items_survive_camera_reset=setup_survives,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Bench Check 4 / Group D (Wave 46 + Tier-0 Gate): Power Save Monitor Split, BK_LANG, Volume & Delete Guard
# ---------------------------------------------------------------------------


def build_simulated_phase275_tier0_receipts(
    *,
    body_serial: str = DEFAULT_TARGET_BODY_SERIAL,
    emmc_cid: str = DEFAULT_TARGET_EMMC_CID,
    body_fw: str = TARGET_BODY_FW,
) -> Tuple[bytes, bytes, Dict[str, str]]:
    """Build deterministic in-memory 528 B FX3RCPT1 dual receipts for `--simulate-bench-dry-run`."""
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE275_TIER0:{body_fw}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE275_MANIFEST:{body_serial}:{body_fw}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    rcpt = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    baselines = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return rcpt, bytes(rcpt), baselines


def evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
    *,
    # [Power Setting Option] Reality Split & 9 Deactivation Conditions
    power_setting_exposed_items: Sequence[str] = P275_FX3_ILC2210_POWER_SETTING_TWO_ITEMS,
    power_save_start_time: str = "OFF",
    auto_power_off_temp: str = "HIGH",
    power_source: str = "INTERNAL_NP_FZ100",
    air_gapped_battery_bench: bool = True,
    power_save_deactivation_conditions: Sequence[str] = (),
    power_save_by_monitor_exposed_in_fx3_ui: bool = False,
    appfw_monitor_power_linkage_modes: Sequence[str] = P275_APPFW_MONITOR_POWER_LINKAGE_FOUR_MODES,
    headless_monitor_power_linkage_mode: str = "DOES_NOT_LINK",
    claimed_power_setting_reset_on_camera_reset: bool = False,
    # [Language] BK_LANG 0x02cf019c (34 vs 29)
    bklang_register_hex: str = P275_BKLANG_REGISTER_HEX,
    fx3_language_count: int = P275_FX3_LANGUAGE_COUNT,
    fx6_language_count: int = P275_FX6_LANGUAGE_COUNT,
    selected_lang: str = "en",
    reset_action: str = "NONE",
    claimed_bklang_cleared_by_camera_or_network_reset: bool = False,
    # [Volume Settings] & [4ch Audio Monitoring]
    volume_settings: int = P275_VOLUME_SETTINGS_DEFAULT,
    xlr_h1_attached: bool = False,
    speaker_feedback_hazard: bool = False,
    four_ch_audio_monitoring: str = "CH1_CH2",
    four_ch_monitoring_five_routes: Sequence[str] = P275_4CH_AUDIO_MONITORING_FIVE_ROUTES,
    expect_4ch_discrete_over_35mm_headphone: bool = False,
    claimed_audio_setup_reset_on_camera_reset: bool = False,
    # [Delete confirm.] & Slot-1 Vault Guard
    delete_confirm: str = "CANCEL_FIRST",
    require_cancel_first_guard: bool = True,
    delete_pressing_twice: str = "OFF",
    claimed_delete_confirm_reset_on_camera_reset: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_delete_requested: bool = False,
    slot1_format_requested: bool = False,
    expect_slot1_vault_delete_or_format_allowed: bool = False,
    simulated_slot1_vault_delete_events: int = 0,
    # H0 == H3 & Tier-0 Receipts
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    simulated_h0_h3_drifted_surfaces: int = 0,
    simulate_bench_dry_run: bool = False,
) -> Tuple[P275CheckGroupDPowerMonitorBkLangVolumeDeleteTier0Result, Tuple[str, ...]]:
    """Verify Wave 46 Power Save Monitor Split, BK_LANG, Volume/4ch Monitoring, Delete Guard & Tier-0."""
    errors: List[str] = []
    warnings: List[str] = []
    tier0_errors: List[str] = []

    rst_norm = _norm_token(reset_action)

    # 1. [Power Setting Option] Reality Split (ilc/2210 2-item vs appFw.so 4-mode) & 9 deactivation conditions
    exposed_items = tuple(str(x).strip() for x in power_setting_exposed_items)
    ps_time = _norm_token(power_save_start_time)
    ap_temp = _norm_token(auto_power_off_temp)
    pwr_src = _norm_token(power_source)
    active_deact = tuple(_norm_token(x) for x in power_save_deactivation_conditions)
    invalid_deact = [
        c for c in active_deact if c not in P275_POWER_SAVE_NINE_DEACTIVATION_CONDITIONS
    ]
    appfw_modes = tuple(_norm_token(x) for x in appfw_monitor_power_linkage_modes)
    headless_mode = _norm_token(headless_monitor_power_linkage_mode)
    pwr_survives = not bool(claimed_power_setting_reset_on_camera_reset)

    battery_airgapped_sleep_hazard = (
        bool(air_gapped_battery_bench)
        and pwr_src == "INTERNAL_NP_FZ100"
        and len(active_deact) == 0
        and ps_time not in P275_SAFE_AIRGAPPED_BATTERY_POWER_SAVE_TIMES
    )

    if (
        exposed_items != P275_FX3_ILC2210_POWER_SETTING_TWO_ITEMS
        or ps_time not in P275_VALID_POWER_SAVE_START_TIMES
        or ap_temp not in P275_VALID_AUTO_POWER_OFF_TEMPS
        or pwr_src not in P275_VALID_POWER_SOURCES
        or len(invalid_deact) > 0
        or battery_airgapped_sleep_hazard
        or bool(power_save_by_monitor_exposed_in_fx3_ui)
        or appfw_modes != P275_APPFW_MONITOR_POWER_LINKAGE_FOUR_MODES
        or headless_mode not in P275_HEADLESS_SAFE_MONITOR_POWER_LINK_MODES
        or not pwr_survives
    ):
        errors.append(
            f"{P275_GD_ERR_POWER_SETTING_OPTION_REALITY_SPLIT_OR_9COND}: [Power Setting Option] "
            f"reality split or 9-condition battery guard violated (items={exposed_items}, "
            f"start_time={power_save_start_time!r}, fx3_ui_monitor_link={power_save_by_monitor_exposed_in_fx3_ui}, "
            f"headless_mode={headless_monitor_power_linkage_mode!r}, invalid_deact={invalid_deact}, "
            f"sleep_hazard={battery_airgapped_sleep_hazard})"
        )

    # 2. [Language] BK_LANG 0x02cf019c (34 vs 29) & (Setup) Reset Persistence
    bkl_reg = str(bklang_register_hex).strip().lower()
    lang_norm = str(selected_lang).strip().lower()
    lang_code = P275_BKLANG_FOUR_LANG_CODES.get(lang_norm)
    bklang_survives = not bool(claimed_bklang_cleared_by_camera_or_network_reset)
    if rst_norm not in P275_VALID_RESET_ACTIONS:
        bklang_survives = False

    if (
        bkl_reg != P275_BKLANG_REGISTER_HEX
        or int(fx3_language_count) != P275_FX3_LANGUAGE_COUNT
        or int(fx6_language_count) != P275_FX6_LANGUAGE_COUNT
        or lang_code is None
        or not bklang_survives
    ):
        errors.append(
            f"{P275_GD_ERR_BKLANG_34_VS_29_OR_SETUP_RESET_PERSISTENCE}: BK_LANG 0x02cf019c "
            f"(34 vs 29) or (Setup) reset persistence violated (reg={bklang_register_hex!r}, "
            f"fx3_langs={fx3_language_count}, fx6_langs={fx6_language_count}, "
            f"lang={selected_lang!r}, survives={bklang_survives})"
        )
    bklang_code_hex = f"0x{lang_code:02x}" if lang_code is not None else "INVALID"

    # 3. [Volume Settings] (0..15, default 7) & [4ch Audio Monitoring] (5 routes, 3.5mm 2ch limit)
    vol_val = int(volume_settings)
    mon_route = _norm_4ch_route(four_ch_audio_monitoring)
    routes_tuple = tuple(_norm_4ch_route(r) for r in four_ch_monitoring_five_routes)
    hp_2ch_ok = not bool(expect_4ch_discrete_over_35mm_headphone)
    audio_setup_survives = not bool(claimed_audio_setup_reset_on_camera_reset)
    xlr_feedback = bool(speaker_feedback_hazard) or (bool(xlr_h1_attached) and vol_val > 10)

    if (
        not (P275_VOLUME_SETTINGS_MIN <= vol_val <= P275_VOLUME_SETTINGS_MAX)
        or xlr_feedback
        or mon_route not in P275_4CH_AUDIO_MONITORING_FIVE_ROUTES
        or routes_tuple != P275_4CH_AUDIO_MONITORING_FIVE_ROUTES
        or not hp_2ch_ok
        or not audio_setup_survives
    ):
        errors.append(
            f"{P275_GD_ERR_VOLUME_OR_4CH_MONITORING_5ROUTE_OR_FEEDBACK}: [Volume Settings] or "
            f"[4ch Audio Monitoring] violated (vol={vol_val}, xlr_feedback={xlr_feedback}, "
            f"route={four_ch_audio_monitoring!r}, hp_2ch_ok={hp_2ch_ok}, survives={audio_setup_survives})"
        )
    elif bool(xlr_h1_attached) and vol_val > P275_VOLUME_SETTINGS_DEFAULT:
        warnings.append(
            "Reduce internal speaker [Volume Settings] or use 3.5mm headphones when XLR-H1 mic is near body."
        )

    # 4. [Delete confirm.] = ["Cancel" first] + Slot-1 Vault Delete/Format Hard Block
    del_conf = _norm_delete_confirm(delete_confirm)
    del_twice = _norm_token(delete_pressing_twice)
    del_survives = not bool(claimed_delete_confirm_reset_on_camera_reset)

    slot1_del_events = max(0, int(simulated_slot1_vault_delete_events))
    if bool(slot1_contains_tier0_dump) and (
        bool(slot1_delete_requested)
        or bool(slot1_format_requested)
        or bool(expect_slot1_vault_delete_or_format_allowed)
    ):
        slot1_del_events = max(1, slot1_del_events)
    slot1_format_locked = bool(slot1_contains_tier0_dump) and not bool(
        expect_slot1_vault_delete_or_format_allowed
    )

    if (
        del_conf not in P275_VALID_DELETE_CONFIRM_MODES
        or (bool(require_cancel_first_guard) and del_conf != "CANCEL_FIRST")
        or del_twice not in ("ON", "OFF")
        or not del_survives
        or slot1_del_events > 0
        or (bool(slot1_contains_tier0_dump) and not slot1_format_locked)
    ):
        errors.append(
            f"{P275_GD_ERR_DELETE_CONFIRM_OR_SLOT1_VAULT_DELETE_FORMAT_BLOCKED}: [Delete confirm.] "
            f"or Slot-1 vault delete/format firewall violated (delete_confirm={delete_confirm!r}, "
            f"twice={delete_pressing_twice!r}, survives={del_survives}, "
            f"slot1_del_events={slot1_del_events}, slot1_fmt_locked={slot1_format_locked})"
        )

    # 5. 16/16 H0 == H3 Baseline Invariance & Dual-Media 528 B FX3RCPT1 Tier-0 Receipt Gate
    surface_total = len(SIXTEEN_STORAGE_SURFACES)
    drifted = max(0, min(surface_total, int(simulated_h0_h3_drifted_surfaces)))
    h0_eq_h3 = surface_total - drifted
    if h0_eq_h3 != surface_total:
        errors.append(
            f"{P275_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 == H3 parity drift ({h0_eq_h3}/{surface_total})"
        )

    raw_a = receipt_a_bytes
    raw_b = receipt_b_bytes
    dev_a = st_dev_a_override
    dev_b = st_dev_b_override
    eff_serial = body_serial
    eff_cid = emmc_cid
    eff_h0_a = dict(h0_baselines_a) if h0_baselines_a is not None else None
    eff_h0_b = dict(h0_baselines_b) if h0_baselines_b is not None else None

    if (
        simulate_bench_dry_run
        and raw_a is None
        and raw_b is None
        and receipt_a_path is None
        and receipt_b_path is None
    ):
        eff_serial = eff_serial or DEFAULT_TARGET_BODY_SERIAL
        eff_cid = eff_cid or DEFAULT_TARGET_EMMC_CID
        raw_a, raw_b, sim_h0 = build_simulated_phase275_tier0_receipts(
            body_serial=eff_serial, emmc_cid=eff_cid, body_fw=body_fw
        )
        dev_a = 101 if dev_a is None else dev_a
        dev_b = 202 if dev_b is None else dev_b
        eff_h0_a = eff_h0_a if eff_h0_a is not None else dict(sim_h0)
        eff_h0_b = eff_h0_b if eff_h0_b is not None else dict(sim_h0)

    if receipt_a_path is not None:
        try:
            _, raw_a, st_a = _read_bounded_slice_o_rdonly(
                Path(receipt_a_path), SD_RECEIPT_BYTES + 64
            )
            if dev_a is None:
                dev_a = int(st_a)
        except OSError as exc:
            tier0_errors.append(
                f"{P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a read failed: {exc}"
            )

    if receipt_b_path is not None:
        try:
            _, raw_b, st_b = _read_bounded_slice_o_rdonly(
                Path(receipt_b_path), SD_RECEIPT_BYTES + 64
            )
            if dev_b is None:
                dev_b = int(st_b)
        except OSError as exc:
            tier0_errors.append(
                f"{P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b read failed: {exc}"
            )

    receipt_present = (raw_a is not None) and (raw_b is not None)
    distinct_media = False
    receipt_verified = False

    if not receipt_present:
        tier0_errors.append(
            f"{P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-copy 528B FX3RCPT1 Tier-0 "
            "cold-backup receipts not provided (offline fail-closed)"
        )
    else:
        assert raw_a is not None and raw_b is not None
        if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES or raw_a != raw_b:
            tier0_errors.append(
                f"{P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual FX3RCPT1 size/byte mismatch"
            )
        else:
            if dev_a is not None and dev_b is not None and int(dev_a) != int(dev_b):
                distinct_media = True
            else:
                tier0_errors.append(
                    f"{P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: st_dev_a == st_dev_b ({dev_a} vs {dev_b})"
                )

            ser_norm = (eff_serial or "").strip()
            cid_norm = (eff_cid or "").strip().lower()
            if not BODY_SERIAL_RE.match(ser_norm) or ser_norm.upper() in FORBIDDEN_TRIVIAL_SERIALS:
                tier0_errors.append(
                    f"{P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid body_serial={eff_serial!r}"
                )
            if not HEX32_CID_RE.match(cid_norm) or cid_norm in FORBIDDEN_TRIVIAL_CIDS:
                tier0_errors.append(
                    f"{P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid emmc_cid={eff_cid!r}"
                )
            if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
                tier0_errors.append(
                    f"{P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt target mismatch"
                )

            try:
                parsed_a = parse_sd_backup_receipt_bytes(raw_a)
                parsed_b = parse_sd_backup_receipt_bytes(raw_b)
                if not parsed_a.valid or not parsed_b.valid:
                    tier0_errors.append(
                        f"{P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 CRC32/header invalid"
                    )
            except Exception as exc:
                tier0_errors.append(
                    f"{P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse error: {exc}"
                )

            if eff_h0_a is None or eff_h0_b is None:
                tier0_errors.append(
                    f"{P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing H0 baseline digests"
                )
            else:
                for req_k in REQUIRED_H0_BASELINE_KEYS:
                    va = eff_h0_a.get(req_k, "")
                    vb = eff_h0_b.get(req_k, "")
                    if _is_trivial_hex64(va) or va.lower() != vb.lower():
                        tier0_errors.append(
                            f"{P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/mismatched H0[{req_k}]"
                        )

            if len(tier0_errors) == 0:
                receipt_verified = True

    return (
        P275CheckGroupDPowerMonitorBkLangVolumeDeleteTier0Result(
            check_group_id=P275_CHECK_GROUP_D_ID,
            passed=(len(errors) == 0),
            power_setting_exposed_two_items=exposed_items,
            power_save_start_time=ps_time,
            auto_power_off_temp=ap_temp,
            power_source=pwr_src,
            power_save_nine_deactivation_count=len(P275_POWER_SAVE_NINE_DEACTIVATION_CONDITIONS),
            active_power_save_deactivations=active_deact,
            power_save_by_monitor_exposed_in_fx3_ui=bool(power_save_by_monitor_exposed_in_fx3_ui),
            appfw_monitor_power_linkage_four_modes=appfw_modes,
            headless_monitor_power_linkage_mode=headless_mode,
            bklang_register_hex=bkl_reg,
            fx3_language_count=int(fx3_language_count),
            fx6_language_count=int(fx6_language_count),
            selected_lang=lang_norm,
            selected_bklang_code_hex=bklang_code_hex,
            bklang_survives_camera_and_network_reset=bklang_survives,
            volume_settings=vol_val,
            xlr_h1_attached=bool(xlr_h1_attached),
            four_ch_audio_monitoring=mon_route,
            four_ch_monitoring_five_routes=routes_tuple,
            headphone_35mm_2ch_only_verified=hp_2ch_ok,
            delete_confirm=del_conf,
            delete_pressing_twice=del_twice,
            slot1_vault_delete_events=slot1_del_events,
            slot1_format_hard_locked=slot1_format_locked,
            h0_h3_surface_count=surface_total,
            h0_equals_h3_count=h0_eq_h3,
            tier0_receipt_present=receipt_present,
            tier0_receipt_verified=receipt_verified,
            distinct_physical_media_verified=distinct_media,
            warnings=tuple(warnings),
            errors=tuple(errors),
        ),
        tuple(tier0_errors),
    )


# ---------------------------------------------------------------------------
# Top-Level Pre-Shoot Readiness Orchestrator & Tamper-Evident Verifier
# ---------------------------------------------------------------------------


def evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness(
    *,
    simulate_bench_dry_run: bool = False,
    simulate_ready_bench: Optional[bool] = None,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P275_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    # Check Group A (Wave 44 — File Settings, Still Prefix, Auto Review & TC/UB)
    movie_file_number: str = "SERIES",
    movie_file_name_format: str = "CAM_ID_PLUS_REEL",
    camera_id: str = "A",
    reel_number: int = 1,
    camera_position: str = "C",
    title_name: str = P275_DEFAULT_TITLE_NAME,
    movie_clip_dir: str = P275_MOVIE_FIXED_CLIP_DIR,
    custom_movie_folder_requested: bool = False,
    claimed_movie_file_settings_reset_on_camera_reset: bool = False,
    claimed_title_name_after_reset: Optional[str] = None,
    still_file_number: str = "SERIES",
    still_file_prefix: str = P275_DEFAULT_STILL_FILE_PREFIX,
    still_folder_name: str = "STANDARD_FORM",
    claimed_still_file_settings_reset_on_camera_reset: bool = False,
    claimed_still_prefix_after_reset: Optional[str] = None,
    slot1_contains_tier0_dump: bool = True,
    still_forced_file_number_reset_slot: Optional[int] = None,
    still_create_new_folder_slot: Optional[int] = None,
    expect_slot1_dcim_mutation_allowed: bool = False,
    simulated_slot1_vault_folder_mutation_events: int = 0,
    auto_review: str = "OFF",
    require_cinema_auto_review_off: bool = True,
    claimed_auto_review_after_reset: Optional[str] = None,
    expect_auto_review_in_movie: bool = False,
    tcub_items: Sequence[str] = P275_TCUB_SIX_ITEMS,
    tc_format: str = "NDF",
    rec_frame_rate_fps: float = 23.98,
    video_system: str = "NTSC",
    tc_run: str = "FREE_RUN",
    tc_make: str = "PRESET",
    tcub_disp_setting: str = "TC",
    claimed_tc_format_after_reset: Optional[str] = None,
    claimed_tcub_reset_on_camera_reset: bool = False,
    # Check Group B (Wave 44 — Gamma Display Assist vs Display LUT / Select LUT)
    log_shooting_mode: str = "CINE_EI",
    gamma_display_assist: str = "OFF",
    gamma_disp_assist_type: str = "AUTO",
    expect_gamma_assist_active_under_log: bool = False,
    expect_gamma_assist_on_external_hdmi: bool = False,
    simulated_external_hdmi_gamma_assist_pixels: int = 0,
    display_lut: str = "ON",
    select_lut: str = "s709",
    user_lut_slot_count: int = P275_USER_LUT_MAX_SLOTS,
    claimed_gamma_assist_after_reset: Optional[str] = None,
    claimed_display_lut_after_reset: Optional[str] = None,
    claimed_setup_lut_reset_on_camera_reset: bool = False,
    # Check Group C (Wave 45 — Focus Magnifier, Peaking, Zero-RF Time, Video Light, HDMI Res)
    auto_magnifier_in_mf: str = "ON",
    auto_mag_label: str = P275_AUTO_MAG_IN_MF_EXACT_LABEL,
    focus_magnifier_custom_button: str = P275_FOCUS_MAG_DEFAULT_CUSTOM_BUTTON,
    focus_magnif_time: str = "NO_LIMIT",
    initial_focus_mag_still: str = "X1_0",
    initial_focus_mag_movie: str = "X1_0",
    af_in_focus_mag: str = "ON",
    hdmi_raw_output: bool = False,
    focus_magnifier_active: bool = False,
    expect_focus_mag_allowed_in_raw: bool = False,
    expect_magnifier_baked_on_clean_hdmi: bool = False,
    simulated_hdmi_magnifier_baked_pixels: int = 0,
    peaking_display: str = "OFF",
    peaking_level: str = "MID",
    peaking_color: str = "WHITE",
    af_illuminator: str = "AUTO",
    shoot_mode: str = "MOVIE",
    focus_mode: str = "MF",
    expect_af_illuminator_fires_in_movie_or_afc: bool = False,
    area_date_time_label: str = P275_AREA_DATE_TIME_EXACT_LABEL,
    area_date_time_subitems: Sequence[str] = P275_AREA_DATE_TIME_FOUR_SUBITEMS,
    area_date_time_manual_airgapped: bool = True,
    creators_app_location_linkage: str = "OFF",
    airplane_mode: str = "ON",
    bluetooth_function: str = "OFF",
    expect_creators_app_auto_time_sync: bool = False,
    simulated_passive_tx_bytes: int = 0,
    video_light_mode: str = "POWER_LINK",
    mi_shoe_5v_current_ma: int = 0,
    expect_mi_shoe_5v_overcurrent_allowed: bool = False,
    hdmi_resolution: str = "AUTO",
    rec_media_dur_hdmi_output: str = "ON",
    expect_4k_hdmi_log_with_internal_rec: bool = False,
    claimed_setup_c_items_reset_on_camera_reset: bool = False,
    # Check Group D & Tier-0 Gate (Wave 46)
    power_setting_exposed_items: Sequence[str] = P275_FX3_ILC2210_POWER_SETTING_TWO_ITEMS,
    power_save_start_time: str = "OFF",
    auto_power_off_temp: str = "HIGH",
    power_source: str = "INTERNAL_NP_FZ100",
    air_gapped_battery_bench: bool = True,
    power_save_deactivation_conditions: Sequence[str] = (),
    power_save_by_monitor_exposed_in_fx3_ui: bool = False,
    appfw_monitor_power_linkage_modes: Sequence[str] = P275_APPFW_MONITOR_POWER_LINKAGE_FOUR_MODES,
    headless_monitor_power_linkage_mode: str = "DOES_NOT_LINK",
    claimed_power_setting_reset_on_camera_reset: bool = False,
    bklang_register_hex: str = P275_BKLANG_REGISTER_HEX,
    fx3_language_count: int = P275_FX3_LANGUAGE_COUNT,
    fx6_language_count: int = P275_FX6_LANGUAGE_COUNT,
    selected_lang: str = "en",
    claimed_bklang_cleared_by_camera_or_network_reset: bool = False,
    volume_settings: int = P275_VOLUME_SETTINGS_DEFAULT,
    xlr_h1_attached: bool = False,
    speaker_feedback_hazard: bool = False,
    four_ch_audio_monitoring: str = "CH1_CH2",
    four_ch_monitoring_five_routes: Sequence[str] = P275_4CH_AUDIO_MONITORING_FIVE_ROUTES,
    expect_4ch_discrete_over_35mm_headphone: bool = False,
    claimed_audio_setup_reset_on_camera_reset: bool = False,
    delete_confirm: str = "CANCEL_FIRST",
    require_cancel_first_guard: bool = True,
    delete_pressing_twice: str = "OFF",
    claimed_delete_confirm_reset_on_camera_reset: bool = False,
    slot1_delete_requested: bool = False,
    slot1_format_requested: bool = False,
    expect_slot1_vault_delete_or_format_allowed: bool = False,
    simulated_slot1_vault_delete_events: int = 0,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    simulated_h0_h3_drifted_surfaces: int = 0,
) -> RealHwFileSettingsGammaAssistFocusMagVideoLightReport:
    """Execute Phase 275 read-only 7th physical bench readiness verifier (`A..D`)."""
    eff_sim = bool(simulate_bench_dry_run or simulate_ready_bench)

    donor_res = inspect_phase275_donors_bounded(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=force_clean_room,
        synthetic_clean_room=synthetic_clean_room,
    )
    ga = evaluate_p275_check_group_a_cinema_slate_and_timecode(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        movie_file_number=movie_file_number,
        movie_file_name_format=movie_file_name_format,
        camera_id=camera_id,
        reel_number=reel_number,
        camera_position=camera_position,
        title_name=title_name,
        movie_clip_dir=movie_clip_dir,
        custom_movie_folder_requested=custom_movie_folder_requested,
        claimed_movie_file_settings_reset_on_camera_reset=claimed_movie_file_settings_reset_on_camera_reset,
        claimed_title_name_after_reset=claimed_title_name_after_reset,
        still_file_number=still_file_number,
        still_file_prefix=still_file_prefix,
        still_folder_name=still_folder_name,
        claimed_still_file_settings_reset_on_camera_reset=claimed_still_file_settings_reset_on_camera_reset,
        claimed_still_prefix_after_reset=claimed_still_prefix_after_reset,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        still_forced_file_number_reset_slot=still_forced_file_number_reset_slot,
        still_create_new_folder_slot=still_create_new_folder_slot,
        expect_slot1_dcim_mutation_allowed=expect_slot1_dcim_mutation_allowed,
        simulated_slot1_vault_folder_mutation_events=simulated_slot1_vault_folder_mutation_events,
        auto_review=auto_review,
        require_cinema_auto_review_off=require_cinema_auto_review_off,
        claimed_auto_review_after_reset=claimed_auto_review_after_reset,
        expect_auto_review_in_movie=expect_auto_review_in_movie,
        tcub_items=tcub_items,
        tc_format=tc_format,
        rec_frame_rate_fps=rec_frame_rate_fps,
        video_system=video_system,
        tc_run=tc_run,
        tc_make=tc_make,
        tcub_disp_setting=tcub_disp_setting,
        claimed_tc_format_after_reset=claimed_tc_format_after_reset,
        claimed_tcub_reset_on_camera_reset=claimed_tcub_reset_on_camera_reset,
    )
    gb = evaluate_p275_check_group_b_gamma_assist_and_display_lut(
        log_shooting_mode=log_shooting_mode,
        gamma_display_assist=gamma_display_assist,
        gamma_disp_assist_type=gamma_disp_assist_type,
        expect_gamma_assist_active_under_log=expect_gamma_assist_active_under_log,
        expect_gamma_assist_on_external_hdmi=expect_gamma_assist_on_external_hdmi,
        simulated_external_hdmi_gamma_assist_pixels=simulated_external_hdmi_gamma_assist_pixels,
        display_lut=display_lut,
        select_lut=select_lut,
        user_lut_slot_count=user_lut_slot_count,
        reset_action=reset_action,
        claimed_gamma_assist_after_reset=claimed_gamma_assist_after_reset,
        claimed_display_lut_after_reset=claimed_display_lut_after_reset,
        claimed_setup_lut_reset_on_camera_reset=claimed_setup_lut_reset_on_camera_reset,
    )
    gc = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
        auto_magnifier_in_mf=auto_magnifier_in_mf,
        auto_mag_label=auto_mag_label,
        focus_magnifier_custom_button=focus_magnifier_custom_button,
        focus_magnif_time=focus_magnif_time,
        initial_focus_mag_still=initial_focus_mag_still,
        initial_focus_mag_movie=initial_focus_mag_movie,
        af_in_focus_mag=af_in_focus_mag,
        hdmi_raw_output=hdmi_raw_output,
        focus_magnifier_active=focus_magnifier_active,
        expect_focus_mag_allowed_in_raw=expect_focus_mag_allowed_in_raw,
        expect_magnifier_baked_on_clean_hdmi=expect_magnifier_baked_on_clean_hdmi,
        simulated_hdmi_magnifier_baked_pixels=simulated_hdmi_magnifier_baked_pixels,
        peaking_display=peaking_display,
        peaking_level=peaking_level,
        peaking_color=peaking_color,
        af_illuminator=af_illuminator,
        shoot_mode=shoot_mode,
        focus_mode=focus_mode,
        expect_af_illuminator_fires_in_movie_or_afc=expect_af_illuminator_fires_in_movie_or_afc,
        area_date_time_label=area_date_time_label,
        area_date_time_subitems=area_date_time_subitems,
        area_date_time_manual_airgapped=area_date_time_manual_airgapped,
        creators_app_location_linkage=creators_app_location_linkage,
        airplane_mode=airplane_mode,
        bluetooth_function=bluetooth_function,
        expect_creators_app_auto_time_sync=expect_creators_app_auto_time_sync,
        simulated_passive_tx_bytes=simulated_passive_tx_bytes,
        video_light_mode=video_light_mode,
        mi_shoe_5v_current_ma=mi_shoe_5v_current_ma,
        expect_mi_shoe_5v_overcurrent_allowed=expect_mi_shoe_5v_overcurrent_allowed,
        hdmi_resolution=hdmi_resolution,
        log_shooting_mode=log_shooting_mode,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        expect_4k_hdmi_log_with_internal_rec=expect_4k_hdmi_log_with_internal_rec,
        reset_action=reset_action,
        claimed_setup_c_items_reset_on_camera_reset=claimed_setup_c_items_reset_on_camera_reset,
    )
    gd, tier0_errors = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
        power_setting_exposed_items=power_setting_exposed_items,
        power_save_start_time=power_save_start_time,
        auto_power_off_temp=auto_power_off_temp,
        power_source=power_source,
        air_gapped_battery_bench=air_gapped_battery_bench,
        power_save_deactivation_conditions=power_save_deactivation_conditions,
        power_save_by_monitor_exposed_in_fx3_ui=power_save_by_monitor_exposed_in_fx3_ui,
        appfw_monitor_power_linkage_modes=appfw_monitor_power_linkage_modes,
        headless_monitor_power_linkage_mode=headless_monitor_power_linkage_mode,
        claimed_power_setting_reset_on_camera_reset=claimed_power_setting_reset_on_camera_reset,
        bklang_register_hex=bklang_register_hex,
        fx3_language_count=fx3_language_count,
        fx6_language_count=fx6_language_count,
        selected_lang=selected_lang,
        reset_action=reset_action,
        claimed_bklang_cleared_by_camera_or_network_reset=claimed_bklang_cleared_by_camera_or_network_reset,
        volume_settings=volume_settings,
        xlr_h1_attached=xlr_h1_attached,
        speaker_feedback_hazard=speaker_feedback_hazard,
        four_ch_audio_monitoring=four_ch_audio_monitoring,
        four_ch_monitoring_five_routes=four_ch_monitoring_five_routes,
        expect_4ch_discrete_over_35mm_headphone=expect_4ch_discrete_over_35mm_headphone,
        claimed_audio_setup_reset_on_camera_reset=claimed_audio_setup_reset_on_camera_reset,
        delete_confirm=delete_confirm,
        require_cancel_first_guard=require_cancel_first_guard,
        delete_pressing_twice=delete_pressing_twice,
        claimed_delete_confirm_reset_on_camera_reset=claimed_delete_confirm_reset_on_camera_reset,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_delete_requested=slot1_delete_requested,
        slot1_format_requested=slot1_format_requested,
        expect_slot1_vault_delete_or_format_allowed=expect_slot1_vault_delete_or_format_allowed,
        simulated_slot1_vault_delete_events=simulated_slot1_vault_delete_events,
        receipt_a_path=receipt_a_path,
        receipt_b_path=receipt_b_path,
        receipt_a_bytes=receipt_a_bytes,
        receipt_b_bytes=receipt_b_bytes,
        st_dev_a_override=st_dev_a_override,
        st_dev_b_override=st_dev_b_override,
        body_model_id=body_model_id,
        body_fw=body_fw,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_baselines_a,
        h0_baselines_b=h0_baselines_b,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
        simulate_bench_dry_run=eff_sim,
    )

    groups_passed = sum(1 for item in (ga, gb, gc, gd) if item.passed)
    all_4_passed = donor_res.passed and groups_passed == 4

    all_errors: List[str] = []
    all_errors.extend(donor_res.errors)
    for item in (ga, gb, gc, gd):
        all_errors.extend(item.errors)
    all_errors.extend(tier0_errors)

    remediations: List[str] = []
    if not ga.passed:
        remediations.append(
            "Verify Movie [File Settings] (Cam ID + Reel#, <=37-char Title), Still 3-char prefix without leading '_', Slot-1 DCIM mutation block, [Auto Review]=Off, and 6-item [TC/UB] Camera-Settings-Reset persistence."
        )
    if not gb.passed:
        remediations.append(
            "Lock [Gamma Display Assist]=Off under [Log Shooting] != Off, keep external HDMI clean (LCD-only), and use [Display LUT]=On + [Select LUT] (S-Log3/s709/709(800%)/User1..16)."
        )
    if not gc.passed:
        remediations.append(
            "Keep [Auto Magnifier in MF] clean-HDMI/RAW-isolated, enforce [AF Illuminator] still-only, keep [Area/Date/Time Setting] manual/zero-RF, cap MI-Shoe 5V <= 900mA, and honor [HDMI Resolution] Log 1080p downshift."
        )
    if not gd.passed or not gd.tier0_receipt_verified:
        remediations.append(
            "Enforce 2-item stock FX3 [Power Setting Option], BK_LANG 0x02cf019c (34 vs 29), [Volume Settings] 0..15 + 5-route [4ch Audio Monitoring], [Delete confirm.]=['Cancel' first] + Slot-1 vault guard, and dual-device 528B FX3RCPT1 receipts."
        )

    if not all_4_passed:
        verdict = P275_GO_NO_GO_BLOCKED_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_FAILURE
        overall_status = verdict
    elif not gd.tier0_receipt_verified:
        if not gd.tier0_receipt_present:
            verdict = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
            overall_status = P275_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        else:
            verdict = P275_GO_NO_GO_BLOCKED_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_FAILURE
            overall_status = verdict
    elif eff_sim:
        verdict = GO_NO_GO_DRY_RUN_SIMULATED_READY
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        verdict = P275_GO_NO_GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_VERIFIED
        overall_status = P275_GO_NO_GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_VERIFIED

    provisional = RealHwFileSettingsGammaAssistFocusMagVideoLightReport(
        schema=PHASE_275_SCHEMA,
        phase_version=PHASE_275_VERSION,
        verification_mode=donor_res.verification_mode,
        simulate_bench_dry_run=eff_sim,
        overall_status=overall_status,
        go_no_go=verdict,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        sd_physical_media_written=False,
        usb_packets_transmitted=0,
        physical_usb_packets_emitted=0,
        raw_firmware_bytes_leaked=PHASE275_RAW_FIRMWARE_BYTES_LEAKED,
        passive_tx_bytes_emitted=gc.passive_tx_bytes_emitted,
        slot1_vault_folder_mutation_events=ga.slot1_vault_folder_mutation_events,
        slot1_vault_delete_events=gd.slot1_vault_delete_events,
        slot1_format_hard_locked=gd.slot1_format_hard_locked,
        power_save_by_monitor_exposed_in_fx3_ui=gd.power_save_by_monitor_exposed_in_fx3_ui,
        check_group_count=4,
        check_groups_passed=groups_passed,
        all_4_check_groups_passed=all_4_passed,
        tier0_receipt_verified=gd.tier0_receipt_verified,
        h0_h3_surface_count=gd.h0_h3_surface_count,
        h0_equals_h3_count=gd.h0_equals_h3_count,
        donor_inspection=donor_res,
        check_group_a_cinema_slate_and_timecode=ga,
        check_group_b_gamma_assist_and_display_lut=gb,
        check_group_c_focus_mag_videolight_and_hdmi_res=gc,
        check_group_d_power_bklang_volume_delete_and_tier0=gd,
        warnings=gd.warnings,
        remediation_actions=tuple(remediations),
        errors=tuple(all_errors),
        report_sha256="",
    )
    digest = _canonical_sha256_dict(provisional.to_dict(), exclude_key="report_sha256")
    return RealHwFileSettingsGammaAssistFocusMagVideoLightReport(
        **{
            **provisional.to_dict(),
            "donor_inspection": donor_res,
            "check_group_a_cinema_slate_and_timecode": ga,
            "check_group_b_gamma_assist_and_display_lut": gb,
            "check_group_c_focus_mag_videolight_and_hdmi_res": gc,
            "check_group_d_power_bklang_volume_delete_and_tier0": gd,
            "warnings": gd.warnings,
            "remediation_actions": tuple(remediations),
            "errors": tuple(all_errors),
            "report_sha256": digest,
        }
    )


run_file_settings_gamma_assist_focus_mag_and_videolight_preflight = (
    evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness
)


def verify_phase275_report(payload: Mapping[str, Any]) -> Phase275ReportVerifyResult:
    """Fail-closed tamper & safety-lock verifier for Phase 275 preflight reports."""
    errors: List[str] = []
    if payload.get("schema") != PHASE_275_SCHEMA:
        errors.append(f"Invalid schema: {payload.get('schema')!r}")
    if payload.get("phase_version") != PHASE_275_VERSION:
        errors.append(f"Invalid phase_version: {payload.get('phase_version')!r}")
    if payload.get("verification_mode") not in ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"):
        errors.append(f"Invalid verification_mode: {payload.get('verification_mode')!r}")
    if payload.get("go_no_go") not in PHASE_275_VALID_GO_NO_GO_VALUES:
        errors.append(f"Invalid go_no_go verdict: {payload.get('go_no_go')!r}")

    for lock_key in (
        "overall_ready_for_hardware_attach",
        "hardware_live_attachment_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "sd_physical_media_written",
        "power_save_by_monitor_exposed_in_fx3_ui",
    ):
        if payload.get(lock_key) is not False:
            errors.append(f"Safety lock violated: {lock_key}={payload.get(lock_key)!r}")

    for zero_key in (
        "usb_packets_transmitted",
        "physical_usb_packets_emitted",
        "raw_firmware_bytes_leaked",
        "passive_tx_bytes_emitted",
    ):
        if payload.get(zero_key) != 0:
            errors.append(f"Zero-counter violated: {zero_key}={payload.get(zero_key)!r}")

    if payload.get("check_group_count") != 4:
        errors.append(f"Expected check_group_count==4, got {payload.get('check_group_count')!r}")

    if payload.get("go_no_go") in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P275_GO_NO_GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_VERIFIED,
    ):
        if payload.get("slot1_vault_folder_mutation_events") != 0:
            errors.append("Pass/dry-run verdict requires slot1_vault_folder_mutation_events==0")
        if payload.get("slot1_vault_delete_events") != 0:
            errors.append("Pass/dry-run verdict requires slot1_vault_delete_events==0")
        if payload.get("slot1_format_hard_locked") is not True:
            errors.append("Pass/dry-run verdict requires slot1_format_hard_locked==True")

    if payload.get("go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT and (
        payload.get("overall_status") != P275_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
    ):
        errors.append(
            "Offline awaiting-receipt verdict must carry overall_status=READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
        )

    if payload.get("simulate_bench_dry_run") is True and (
        payload.get("go_no_go")
        == P275_GO_NO_GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_VERIFIED
    ):
        errors.append("Simulated dry-run cannot claim physical Tier-0 verified verdict")

    if payload.get("go_no_go") == P275_GO_NO_GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_VERIFIED and (
        payload.get("all_4_check_groups_passed") is not True
        or payload.get("tier0_receipt_verified") is not True
    ):
        errors.append("Verified verdict requires all 4 check groups and Tier-0 receipt verified")

    claimed_sha = str(payload.get("report_sha256", ""))
    expected_sha = _canonical_sha256_dict(payload, exclude_key="report_sha256")
    if not HEX64_RE.match(claimed_sha) or claimed_sha != expected_sha:
        errors.append("report_sha256 canonical digest mismatch")

    return Phase275ReportVerifyResult(valid=(len(errors) == 0), errors=tuple(errors))


def render_phase275_markdown(report: RealHwFileSettingsGammaAssistFocusMagVideoLightReport) -> str:
    """Render concise deterministic Markdown summary for Phase 275 physical bench preflight."""
    ga = report.check_group_a_cinema_slate_and_timecode
    gb = report.check_group_b_gamma_assist_and_display_lut
    gc = report.check_group_c_focus_mag_videolight_and_hdmi_res
    gd = report.check_group_d_power_bklang_volume_delete_and_tier0
    lines = [
        f"# Phase 275 7th Physical Bench Readiness (`{report.schema}`)",
        "",
        f"- **OVERALL**: `{report.overall_status}` (`go_no_go={report.go_no_go}`, mode=`{report.verification_mode}`, dry_run=`{report.simulate_bench_dry_run}`)",
        f"- **Check Groups**: `{report.check_groups_passed}/{report.check_group_count}` (`H0==H3`: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`)",
        f"- **Hard Locks**: `ready_attach={report.overall_ready_for_hardware_attach}`, `live_attach={report.hardware_live_attachment_authorized}`, `emmc_writes={report.persistent_emmc_writes_authorized}`, `spi_nor={report.spi_nor_write_authorized}`, `el3_tx={report.el3_payload_transmit_authorized}`, `usb_pkts={report.usb_packets_transmitted}`, `passive_tx={report.passive_tx_bytes_emitted}`, `leaked_bytes={report.raw_firmware_bytes_leaked}`",
        "",
        "| Check Group | Status | Key Telemetry |",
        "| :--- | :---: | :--- |",
        f"| `{ga.check_group_id}` | `{'PASS' if ga.passed else 'FAIL'}` | Movie=`{ga.movie_file_name_format}` (`{ga.camera_id}{ga.reel_number:03d}{ga.camera_position}`, title_len=`{ga.title_name_len}`), Prefix=`{ga.still_file_prefix}`, AutoReview=`{ga.auto_review}`, TC/UB=`{len(ga.tcub_six_items)}` (`{ga.tc_format}`/`{ga.tc_run}`, reset_survives=`{ga.all_6_tcub_survive_camera_reset}`), Slot1Mut=`{ga.slot1_vault_folder_mutation_events}` |",
        f"| `{gb.check_group_id}` | `{'PASS' if gb.passed else 'FAIL'}` | Log=`{gb.log_shooting_mode}`, GammaAssist=`{gb.gamma_display_assist}` (`locked_off={gb.gamma_assist_locked_off_by_log}`, hdmi_px=`{gb.external_hdmi_gamma_assist_pixels}`), DisplayLUT=`{gb.display_lut}`, SelectLUT=`{gb.select_lut}` (`User1..{gb.user_lut_slots_supported}`) |",
        f"| `{gc.check_group_id}` | `{'PASS' if gc.passed else 'FAIL'}` | FocusMag=`{gc.initial_focus_mag_movie}`/`{gc.focus_magnif_time}` (`{gc.auto_mag_label_verified}`), Peaking=`{gc.peaking_display}`, AFIllum=`{gc.af_illuminator}`, ZeroRFTime=`{gc.zero_rf_time_isolated}`, VideoLight=`{gc.video_light_mode}` (`{gc.mi_shoe_5v_current_ma}mA<=900mA`), HDMIRes=`{gc.hdmi_resolution}`->`{gc.effective_hdmi_output_class}` |",
        f"| `{gd.check_group_id}` | `{'PASS' if gd.passed else 'FAIL'}` | PowerOpt=`{len(gd.power_setting_exposed_two_items)}` (`fx3_ui_monitor={gd.power_save_by_monitor_exposed_in_fx3_ui}`, headless=`{gd.headless_monitor_power_linkage_mode}`), BK_LANG=`{gd.selected_lang}` (`{gd.selected_bklang_code_hex}`, `34`vs`29`), Vol=`{gd.volume_settings}`/`{gd.four_ch_audio_monitoring}`, DelConf=`{gd.delete_confirm}` (Slot1Del=`{gd.slot1_vault_delete_events}`), Tier0=`{gd.tier0_receipt_verified}` |",
        "",
        f"- **Report SHA-256**: `{report.report_sha256}`",
    ]
    return "\n".join(lines) + "\n"
