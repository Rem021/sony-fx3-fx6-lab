"""Phase 214 — Real-Hardware Main Track Part 26:
Gate G77 (`ILME-FX3` `Ver. 7.02` `[File Settings]` 5-Mode `[File Name Format]`
`Standard / Cam ID + Reel# / Title / Date + Title / Title + Date` across Slot 1 & Slot 2,
`[File Number]` `Series / Reset` + `Series Counter Reset`, `[Title Name Settings]` Max `37`
ASCII Characters & Exact Allowed Charset, SDHC `<=32GB` FAT32 Forced `[Standard]` Lock &
Custom Movie Folder Prohibition, and `[Shot Mark]` `Add Shot Mark1/2` + `Add/Delete Shot Mark1/2`
`M4ROOT/CLIP/*M01.XML` Non-Real-Time Metadata Sidecar + `[Image Jump Setting]` +
`[Only Shot Mark Mov.]` / `[Only Shot Mark]` FTP/Smartphone Transfer Filter Guard),
Gate G78 (`ILME-FX3` `Ver. 7.02` `[TC/UB]` `[Time Code Make]=[Regenerate]` Forced `[Rec Run]`
Advancement & Exclusive **Slot 1** Last-TC Read under `[Simult. Recording]`, `VMC-BNCM1`
`EXT-LK` Prerequisite `Movie + [Preset] + [Free Run]` & Immediate Release on `TC Make`/`TC Run`
Switch, S&Q Lockout of `[Time Code Run]` & HDMI `[Time Code Output]`, Physical `[REC Lamp]`
3-State Coupled Rear+Top-`REC`-Button Tally `All On / Only Front Off / All Off` + Independent
`[Emphasized REC Display]` HDMI Red Frame, and `[Silent Mode]=[On] -> [Audio signals]=[Off]`
Hard Lock Guard),
and Unified 78-Gate Master Safety Preflight (`G01..G78` / `verify-78-gates`).

Delegates `G01..G76` directly to `evaluate_76gate_preflight()` from
`realhw_hdmi_log1080_proxy_focusmag_brightmon_and_76gate_guard` while hard-locking:
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`
- `USB_PACKETS_TRANSMITTED = 0`
- `RAW_FIRMWARE_BYTES_LEAKED = 0`
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
from typing import Any, Dict, FrozenSet, List, Mapping, Optional, Sequence, Set, Tuple, Union

from .master_16gate_preflight import DEFAULT_REPO_ROOT, GateVerdict
from .realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
)
from .realhw_hdmi_log1080_proxy_focusmag_brightmon_and_76gate_guard import (
    Master76GateReport,
    evaluate_76gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_FILESETTINGS_SHOTMARK_TCREGEN_RECLAMP_78GATE_SCHEMA: str = (
    "fx3-realhw-filesettings-shotmark-tcregen-reclamp-78gate-preflight-v1"
)
REALHW_FILESETTINGS_SHOTMARK_TCREGEN_RECLAMP_78GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

DONOR_CHECK_MAX_SECONDS: float = 0.15
FX3_DEFAULT_FW_VERSION_G77: str = "7.02"

# Gate IDs & Canonical Codes for G77..G78
G77_GATE_ID: str = "G77_file_settings_sdhc_37char_lock_and_shotmark_xml_filter_guard"
G77_GATE_CODE: str = "G77_FILE_SETTINGS_SDHC_37CHAR_LOCK_AND_SHOTMARK_XML_FILTER_GUARD"
GATE_G77_FILE_SETTINGS_SDHC_37CHAR_LOCK_AND_SHOTMARK_XML_FILTER_GUARD: str = G77_GATE_CODE
G77: str = G77_GATE_CODE

G78_GATE_ID: str = "G78_tc_regenerate_slot1_extlk_release_and_reclamp_coupled_tally_guard"
G78_GATE_CODE: str = "G78_TC_REGENERATE_SLOT1_EXTLK_RELEASE_AND_RECLAMP_COUPLED_TALLY_GUARD"
GATE_G78_TC_REGENERATE_SLOT1_EXTLK_RELEASE_AND_RECLAMP_COUPLED_TALLY_GUARD: str = G78_GATE_CODE
G78: str = G78_GATE_CODE

# Status & Violation Codes
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G77: str = (
    "VERIFIED_FILE_SETTINGS_SDHC_37CHAR_LOCK_AND_SHOTMARK_XML_FILTER_GUARD"
)
STATUS_VERIFIED_G78: str = (
    "VERIFIED_TC_REGENERATE_SLOT1_EXTLK_RELEASE_AND_RECLAMP_COUPLED_TALLY_GUARD"
)

STATUS_BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID: str = (
    "BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID"
)
STATUS_BLOCKED_G77_TITLE_NAME_LENGTH_OR_CHARSET_INVALID: str = (
    "BLOCKED_G77_TITLE_NAME_LENGTH_OR_CHARSET_INVALID"
)
STATUS_BLOCKED_G77_SDHC_STANDARD_LOCK_OR_CUSTOM_FOLDER_FORBIDDEN: str = (
    "BLOCKED_G77_SDHC_STANDARD_LOCK_OR_CUSTOM_FOLDER_FORBIDDEN"
)
STATUS_BLOCKED_G77_SHOTMARK_XML_SIDECAR_OR_MODE_VIOLATION: str = (
    "BLOCKED_G77_SHOTMARK_XML_SIDECAR_OR_MODE_VIOLATION"
)
STATUS_BLOCKED_G77_SHOTMARK_JUMP_OR_TRANSFER_FILTER_VIOLATION: str = (
    "BLOCKED_G77_SHOTMARK_JUMP_OR_TRANSFER_FILTER_VIOLATION"
)
STATUS_BLOCKED_G77_TELEMETRY_INVALID: str = (
    "BLOCKED_G77_FILE_SETTINGS_SHOTMARK_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G78_TC_REGENERATE_REC_RUN_OR_SLOT1_VIOLATION: str = (
    "BLOCKED_G78_TC_REGENERATE_REC_RUN_OR_SLOT1_VIOLATION"
)
STATUS_BLOCKED_G78_VMC_BNCM1_EXT_LK_PREREQ_OR_RELEASE_VIOLATION: str = (
    "BLOCKED_G78_VMC_BNCM1_EXT_LK_PREREQ_OR_RELEASE_VIOLATION"
)
STATUS_BLOCKED_G78_SQ_TC_RUN_OR_HDMI_TCOUT_LOCKOUT: str = (
    "BLOCKED_G78_SQ_TC_RUN_OR_HDMI_TCOUT_LOCKOUT"
)
STATUS_BLOCKED_G78_REC_LAMP_COUPLED_TALLY_OR_OSD_VIOLATION: str = (
    "BLOCKED_G78_REC_LAMP_COUPLED_TALLY_OR_OSD_VIOLATION"
)
STATUS_BLOCKED_G78_SILENT_MODE_AUDIO_SIGNALS_LOCK_VIOLATION: str = (
    "BLOCKED_G78_SILENT_MODE_AUDIO_SIGNALS_LOCK_VIOLATION"
)
STATUS_BLOCKED_G78_TELEMETRY_INVALID: str = (
    "BLOCKED_G78_TCREGEN_RECLAMP_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE214_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE214_78GATE_DONOR_INTEGRITY_OR_BUDGET_EXCEEDED"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G77 Constants — [File Settings], 37-Char Title, SDHC Lock & Shot Mark1/2 XML
FILE_SETTINGS_MENU_PATH: str = "MENU -> Shooting -> [File] -> [File Settings]"
FILE_NAME_FORMAT_STANDARD: str = "STANDARD"
FILE_NAME_FORMAT_CAM_ID_REEL: str = "CAM_ID_PLUS_REEL"
FILE_NAME_FORMAT_TITLE: str = "TITLE"
FILE_NAME_FORMAT_DATE_TITLE: str = "DATE_PLUS_TITLE"
FILE_NAME_FORMAT_TITLE_DATE: str = "TITLE_PLUS_DATE"
ALLOWED_FILE_NAME_FORMATS: Tuple[str, ...] = (
    FILE_NAME_FORMAT_STANDARD,
    FILE_NAME_FORMAT_CAM_ID_REEL,
    FILE_NAME_FORMAT_TITLE,
    FILE_NAME_FORMAT_DATE_TITLE,
    FILE_NAME_FORMAT_TITLE_DATE,
)
ALLOWED_FILE_NUMBER_MODES: Tuple[str, ...] = ("SERIES", "RESET")
TITLE_NAME_DEFAULT: str = "C"
TITLE_NAME_MAX_CHARS: int = 37
TITLE_NAME_ALLOWED_SYMBOLS: str = ".-_@!#$%+=^~(),;[]"
TITLE_NAME_ALLOWED_ASCII_CHARS: FrozenSet[str] = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    + TITLE_NAME_ALLOWED_SYMBOLS
)
SDHC_MAX_CAPACITY_GB: float = 32.0
ALLOWED_SLOT_MEDIA_TYPES_G77: Tuple[str, ...] = (
    "CFEXPRESS_A",
    "SDXC",
    "SDHC",
    "NONE",
)
STANDARD_MOVIE_CLIP_FOLDER: str = "M4ROOT/CLIP"
SHOTMARK_XML_SIDECAR_SUFFIX: str = "M01.XML"
ALLOWED_SHOTMARK_REC_KEYS: Tuple[str, ...] = (
    "NONE",
    "ADD_SHOT_MARK1",
    "ADD_SHOT_MARK2",
)
ALLOWED_SHOTMARK_PLAYBACK_OPS: Tuple[str, ...] = (
    "NONE",
    "ADD_DELETE_SHOT_MARK1",
    "ADD_DELETE_SHOT_MARK2",
)
ALLOWED_SHOTMARK_IMAGE_JUMP_SETTINGS: Tuple[str, ...] = (
    "SHOT_MARK_ONLY",
    "SHOT_MARK1_ONLY",
    "SHOT_MARK2_ONLY",
    "NO_SHOT_MARK",
)
ALLOWED_SHOTMARK_TRANSFER_TARGETS: Tuple[str, ...] = (
    "ALL",
    "ONLY_SHOT_MARK_MOV",
    "ONLY_SHOT_MARK",
)

# Gate G78 Constants — [TC/UB] Regenerate Slot-1, EXT-LK Release, Coupled REC Lamp & Silent Mode
TC_UB_MENU_PATH: str = "MENU -> Shooting -> [TC/UB]"
REC_LAMP_MENU_PATH: str = "MENU -> Setup -> [Setup Option] -> [REC Lamp]"
AUDIO_SIGNALS_MENU_PATH: str = "MENU -> Setup -> [Sound Option] -> [Audio signals]"

TC_MAKE_PRESET: str = "PRESET"
TC_MAKE_REGENERATE: str = "REGENERATE"
ALLOWED_TIME_CODE_MAKE_MODES: Tuple[str, ...] = (TC_MAKE_PRESET, TC_MAKE_REGENERATE)

TC_RUN_REC_RUN: str = "REC_RUN"
TC_RUN_FREE_RUN: str = "FREE_RUN"
ALLOWED_TIME_CODE_RUN_MODES: Tuple[str, ...] = (TC_RUN_REC_RUN, TC_RUN_FREE_RUN)

REC_MEDIA_SLOT_1: str = "SLOT_1"
REC_MEDIA_SLOT_2: str = "SLOT_2"
REC_MEDIA_SIMULT_RECORDING: str = "SIMULT_RECORDING"
ALLOWED_RECORDING_MEDIA_MODES_G78: Tuple[str, ...] = (
    REC_MEDIA_SLOT_1,
    REC_MEDIA_SLOT_2,
    REC_MEDIA_SIMULT_RECORDING,
)

REC_LAMP_ALL_ON: str = "ALL_ON"
REC_LAMP_ONLY_FRONT_OFF: str = "ONLY_FRONT_OFF"
REC_LAMP_ALL_OFF: str = "ALL_OFF"
ALLOWED_FX3_REC_LAMP_MODES: Tuple[str, ...] = (
    REC_LAMP_ALL_ON,
    REC_LAMP_ONLY_FRONT_OFF,
    REC_LAMP_ALL_OFF,
)

# Pinned FX3 v7.02 & FX6 v6.01 Donor Specs (bounded <0.15s O_RDONLY verification)
PINNED_PHASE214_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"File",
            b"Shot",
            b"Mark",
            b"CLIP",
            b"TC",
            b"UB",
            b"Preset",
            b"Free",
            b"Lamp",
            b"REC",
            b"Silent",
            b"Audio",
            b"HDMI",
            b"BK4",
            b"/setting",
        ),
        "fx3/cpapp-b.bin::{15980568B,ILME-FX3,File,Shot,Mark,CLIP,TC,UB,Preset,Free,Lamp,REC,Silent,Audio,HDMI}",
    ),
    "fx3_saveload_so": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (b"\x7fELF", b"SaveLoadSettings", b"Settings", b"Backup"),
        "fx3/libSaveLoadSettings.so::{18760B,ELF,SaveLoadSettings,Settings,Backup}",
    ),
    "fx3_bk4_bin": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"TC", b"/setting"),
        "fx3/FX3-CX95900_ALLLANG-Backup.bin::{2229740B,BK4,ILME-FX3,TC,/setting}",
    ),
    "fx6_bk4_bin": (
        "fx6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"WB", b"TC", b"/setting"),
        "fx6/CX95898_NTSC.bin::{2253333B,BK4,WB,TC,/setting}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase214DonorAuditResult:
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
class FileSettingsSdhcAndShotMarkGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    firmware_version: str
    canonical_file_name_format: str
    effective_file_name_format: str
    canonical_file_number_mode: str
    series_counter_reset_applied: bool
    modeled_next_clip_number: int
    title_name: str
    title_name_length: int
    sdhc_card_detected: bool
    sdhc_standard_lock_active: bool
    custom_movie_folder_prohibited: bool
    canonical_slot1_media_type: str
    canonical_slot2_media_type: str
    shot_mark1_present: bool
    shot_mark2_present: bool
    shot_mark_xml_sidecar_path: str
    canonical_image_jump_setting: str
    image_jump_matched: bool
    canonical_transfer_target_movie: str
    transfer_filter_eligible: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TcRegenerateSlot1AndRecLampTallyResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    canonical_shooting_mode: str
    canonical_time_code_make: str
    canonical_time_code_run_menu: str
    effective_time_code_run: str
    regenerate_forced_rec_run: bool
    canonical_recording_media: str
    regenerate_reference_slot: Optional[str]
    vmc_bncm1_attached: bool
    modeled_ext_lk_active: bool
    ext_lk_released_on_tc_change: bool
    sq_tc_run_locked_out: bool
    hdmi_time_code_output_on: bool
    canonical_rec_lamp_mode: str
    front_tally_led_on: bool
    rear_tally_led_on: bool
    top_rec_button_led_on: bool
    rear_and_top_tally_coupled: bool
    emphasized_rec_display_on: bool
    hdmi_info_display_on: bool
    hdmi_red_rec_frame_active: bool
    silent_mode_on: bool
    effective_audio_signals_on: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G77FileSettingsShotMarkGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    filesettings_shotmark_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G78TcRegenRecLampGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    tcregen_reclamp_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master78GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_75_gates_verified: bool
    all_78_gates_verified: bool
    g13_to_g78_all_passed: bool
    g77_to_g78_all_passed: bool
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
    master_76_report: Dict[str, Any]
    g77_result: Dict[str, Any]
    g78_result: Dict[str, Any]
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


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _is_finite_num(val: Any) -> bool:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return False
    f = float(val)
    return abs(f) < 1e12 and (f == f)


def _norm_file_name_format(val: str) -> str:
    s = val.strip().upper().replace("+", "_PLUS_").replace("#", "")
    t = re.sub(r"[^A-Z0-9]+", "_", s).strip("_")
    aliases = {
        "STANDARD": FILE_NAME_FORMAT_STANDARD,
        "CAM_ID_PLUS_REEL": FILE_NAME_FORMAT_CAM_ID_REEL,
        "CAMID_PLUS_REEL": FILE_NAME_FORMAT_CAM_ID_REEL,
        "TITLE": FILE_NAME_FORMAT_TITLE,
        "DATE_PLUS_TITLE": FILE_NAME_FORMAT_DATE_TITLE,
        "TITLE_PLUS_DATE": FILE_NAME_FORMAT_TITLE_DATE,
    }
    return aliases.get(t, t)


def _norm_slot_media_type(val: str) -> str:
    t = re.sub(r"[^A-Z0-9]+", "_", val.strip().upper()).strip("_")
    if t in ("CFEXPRESS_A", "CFEXPRESS_TYPE_A", "CFE_A"):
        return "CFEXPRESS_A"
    if t in ("SDXC", "SD_XC"):
        return "SDXC"
    if t in ("SDHC", "SD_HC"):
        return "SDHC"
    if t in ("NONE", "EMPTY", "NOT_INSERTED"):
        return "NONE"
    return t


def _norm_image_jump_setting(val: str) -> str:
    t = re.sub(r"[^A-Z0-9]+", "_", val.strip().upper()).strip("_")
    return t


def _norm_transfer_target(val: str) -> str:
    t = re.sub(r"[^A-Z0-9]+", "_", val.strip().upper()).strip("_")
    if t in ("ALL", "ALL_MOVIES", "ALL_IMAGES"):
        return "ALL"
    if t in ("ONLY_SHOT_MARK_MOV", "ONLY_SHOT_MARK_MOVIE", "ONLY_SHOT_MARK_MOVIES"):
        return "ONLY_SHOT_MARK_MOV"
    if t == "ONLY_SHOT_MARK":
        return "ONLY_SHOT_MARK"
    return t


def _norm_shooting_mode_g78(val: str) -> str:
    s = val.strip().upper().replace("&", "_AND_")
    t = re.sub(r"[^A-Z0-9]+", "_", s).strip("_")
    if t in ("MOVIE", "CINE_EI", "FLEXIBLE_ISO", "BIG6_MOVIE"):
        return "MOVIE"
    if t in ("S_AND_Q", "SQ", "SLOW_AND_QUICK"):
        return "S&Q"
    if t in ("STILL", "PHOTO"):
        return "STILL"
    return t


def _norm_recording_media_g78(val: str) -> str:
    t = re.sub(r"[^A-Z0-9]+", "_", val.strip().upper()).strip("_")
    if t in ("SLOT_1", "SLOT1"):
        return REC_MEDIA_SLOT_1
    if t in ("SLOT_2", "SLOT2"):
        return REC_MEDIA_SLOT_2
    if t in ("SIMULT_RECORDING", "SIMULTANEOUS_RECORDING", "SIMULT"):
        return REC_MEDIA_SIMULT_RECORDING
    return t


def _norm_rec_lamp_mode(val: str) -> str:
    t = re.sub(r"[^A-Z0-9]+", "_", val.strip().upper()).strip("_")
    return t


# ---------------------------------------------------------------------------
# 1. Bounded `<0.15s` O_RDONLY Local Donor Audit (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
# ---------------------------------------------------------------------------

_DONOR_BLOB_CACHE: Dict[str, Tuple[int, float, int, str, bytes]] = {}


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


def audit_phase214_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS,
) -> Phase214DonorAuditResult:
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE214_DONOR_SPECS.items():
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
        return Phase214DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE214_DONOR_INTEGRITY
            ),
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_150ms=within_budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE214_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=within_budget,
            fx6_contracts_verified=within_budget,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE214_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE214_DONOR_SPECS.items()
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
    ) in PINNED_PHASE214_DONOR_SPECS.items():
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
            f"Local O_RDONLY donor check exceeded {max_budget_seconds:.3f}s budget ({elapsed:.4f}s)."
        )

    fx3_keys = {k for k, s in PINNED_PHASE214_DONOR_SPECS.items() if s[0] == "fx3"}
    fx6_keys = {k for k, s in PINNED_PHASE214_DONOR_SPECS.items() if s[0] == "fx6"}
    valid = (len(errors) == 0) and (len(missing) == 0) and within_budget
    return Phase214DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE214_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_150ms=within_budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_keys.issubset(passed_keys) and valid,
        fx6_contracts_verified=fx6_keys.issubset(passed_keys) and valid,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate G77 Validators (`G77_FILE_SETTINGS_SDHC_37CHAR_LOCK_AND_SHOTMARK_XML_FILTER_GUARD`)
# ---------------------------------------------------------------------------


def validate_fx3_title_name(title_name: str) -> Tuple[bool, Tuple[str, ...]]:
    """Validate `[Title Name Settings]` string (`1..37` chars, exact Sony FX3 ASCII charset)."""
    if not isinstance(title_name, str) or not (1 <= len(title_name) <= TITLE_NAME_MAX_CHARS):
        return False, ()
    bad: List[str] = []
    for ch in title_name:
        if ch not in TITLE_NAME_ALLOWED_ASCII_CHARS and ch not in bad:
            bad.append(ch)
    return len(bad) == 0, tuple(bad)


def resolve_effective_fx3_file_name_format(
    file_name_format: str = "Standard",
    *,
    slot1_media_type: str = "CFEXPRESS_A",
    slot2_media_type: str = "SDXC",
    slot1_capacity_gb: Optional[float] = None,
    slot2_capacity_gb: Optional[float] = None,
    slot1_filesystem: Optional[str] = None,
    slot2_filesystem: Optional[str] = None,
) -> Tuple[str, bool]:
    """Return `(effective_file_name_format, sdhc_standard_lock_active)` across Slot 1 & Slot 2."""
    canon_fmt = _norm_file_name_format(file_name_format)
    s1 = _norm_slot_media_type(slot1_media_type)
    s2 = _norm_slot_media_type(slot2_media_type)
    fs1 = (slot1_filesystem or ("FAT32" if s1 == "SDHC" else "exFAT")).strip().upper()
    fs2 = (slot2_filesystem or ("FAT32" if s2 == "SDHC" else "exFAT")).strip().upper()
    cap1 = (32.0 if s1 == "SDHC" else 160.0) if slot1_capacity_gb is None else float(slot1_capacity_gb)
    cap2 = (32.0 if s2 == "SDHC" else 128.0) if slot2_capacity_gb is None else float(slot2_capacity_gb)

    s1_sdhc = (s1 != "NONE") and (s1 == "SDHC" or fs1 == "FAT32" or cap1 <= SDHC_MAX_CAPACITY_GB)
    s2_sdhc = (s2 != "NONE") and (s2 == "SDHC" or fs2 == "FAT32" or cap2 <= SDHC_MAX_CAPACITY_GB)
    sdhc_locked = s1_sdhc or s2_sdhc
    return (FILE_NAME_FORMAT_STANDARD if sdhc_locked else canon_fmt), sdhc_locked


def evaluate_shotmark_jump_and_transfer_match(
    *,
    shot_mark1: bool,
    shot_mark2: bool,
    image_jump_setting: str = "Shot Mark Only",
    transfer_target_movie: str = "Only Shot Mark Mov.",
) -> Tuple[bool, bool]:
    """Return `(image_jump_matched, transfer_filter_eligible)` for a clip's Shot Mark1/2 flags."""
    jump = _norm_image_jump_setting(image_jump_setting)
    target = _norm_transfer_target(transfer_target_movie)
    any_mark = bool(shot_mark1 or shot_mark2)

    if jump == "SHOT_MARK_ONLY":
        jump_ok = any_mark
    elif jump == "SHOT_MARK1_ONLY":
        jump_ok = bool(shot_mark1)
    elif jump == "SHOT_MARK2_ONLY":
        jump_ok = bool(shot_mark2)
    elif jump == "NO_SHOT_MARK":
        jump_ok = not any_mark
    else:
        jump_ok = False

    if target == "ALL":
        xfer_ok = True
    elif target in ("ONLY_SHOT_MARK_MOV", "ONLY_SHOT_MARK"):
        xfer_ok = any_mark
    else:
        xfer_ok = False
    return jump_ok, xfer_ok


def verify_file_settings_sdhc_37char_and_shotmark_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: Union[int, str] = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G77,
    file_name_format: str = "Cam ID + Reel#",
    slot2_file_name_format: Optional[str] = None,
    file_number_mode: str = "Series",
    series_counter_reset_executed: bool = False,
    previous_clip_number: int = 41,
    card_swapped_to_empty: bool = False,
    claimed_next_clip_number: Optional[int] = None,
    cam_id: str = "A",
    reel_number: int = 1,
    title_name: str = "FX3_MainCam_A-Roll_Scene01",
    retroactive_existing_clip_rename_claimed: bool = False,
    slot1_media_type: str = "CFEXPRESS_A",
    slot2_media_type: str = "SDXC",
    slot1_capacity_gb: Optional[float] = None,
    slot2_capacity_gb: Optional[float] = None,
    slot1_filesystem: Optional[str] = None,
    slot2_filesystem: Optional[str] = None,
    claimed_effective_file_name_format: Optional[str] = None,
    custom_movie_folder_requested: bool = False,
    movie_clip_folder: str = STANDARD_MOVIE_CLIP_FOLDER,
    shooting_mode: str = "Movie",
    rec_shot_mark_key: str = "Add Shot Mark1",
    playback_shot_mark_op: str = "None",
    shot_mark1_present: bool = True,
    shot_mark2_present: bool = False,
    shot_mark_xml_path: str = "M4ROOT/CLIP/A001C0042_261115_ABCDM01.XML",
    video_essence_mutated_by_shotmark: bool = False,
    image_jump_setting: str = "Shot Mark Only",
    claimed_image_jump_matched: Optional[bool] = None,
    transfer_target_movie: str = "Only Shot Mark Mov.",
    clip_selected_for_transfer: bool = True,
    unmarked_clip_transferred_under_shotmark_filter: bool = False,
) -> FileSettingsSdhcAndShotMarkGuardResult:
    """Validate `ILME-FX3 Ver. 7.02` Gate G77 `[File Settings]` 5-mode `[File Name Format]`,
    `[File Number]`, 37-char ASCII `[Title Name Settings]`, SDHC `[Standard]` lock & custom
    movie folder prohibition, and `[Shot Mark]` `*M01.XML` + `[Image Jump Setting]` + FTP/App
    `[Only Shot Mark Mov.]` / `[Only Shot Mark]` transfer filter semantics.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        not isinstance(body_model_name, str)
        or not isinstance(firmware_version, str)
        or not isinstance(file_name_format, str)
        or not isinstance(file_number_mode, str)
        or not isinstance(title_name, str)
        or not isinstance(cam_id, str)
        or not isinstance(slot1_media_type, str)
        or not isinstance(slot2_media_type, str)
        or not isinstance(movie_clip_folder, str)
        or not isinstance(shooting_mode, str)
        or not isinstance(rec_shot_mark_key, str)
        or not isinstance(playback_shot_mark_op, str)
        or not isinstance(shot_mark_xml_path, str)
        or not isinstance(image_jump_setting, str)
        or not isinstance(transfer_target_movie, str)
        or not isinstance(series_counter_reset_executed, bool)
        or not isinstance(card_swapped_to_empty, bool)
        or not isinstance(retroactive_existing_clip_rename_claimed, bool)
        or not isinstance(custom_movie_folder_requested, bool)
        or not isinstance(shot_mark1_present, bool)
        or not isinstance(shot_mark2_present, bool)
        or not isinstance(video_essence_mutated_by_shotmark, bool)
        or not isinstance(clip_selected_for_transfer, bool)
        or not isinstance(unmarked_clip_transferred_under_shotmark_filter, bool)
        or isinstance(previous_clip_number, bool)
        or not isinstance(previous_clip_number, int)
        or isinstance(reel_number, bool)
        or not isinstance(reel_number, int)
        or (slot1_capacity_gb is not None and not _is_finite_num(slot1_capacity_gb))
        or (slot2_capacity_gb is not None and not _is_finite_num(slot2_capacity_gb))
    ):
        _add_code(codes, STATUS_BLOCKED_G77_TELEMETRY_INVALID)
        errors.append("Gate G77 received invalid telemetry argument types.")
        return FileSettingsSdhcAndShotMarkGuardResult(
            valid=False,
            status=codes[0],
            violation_codes=tuple(codes),
            body_model_name=str(body_model_name),
            body_model_id_hex=hex(FX3_MODEL_ID),
            firmware_version=str(firmware_version),
            canonical_file_name_format="INVALID",
            effective_file_name_format="INVALID",
            canonical_file_number_mode="INVALID",
            series_counter_reset_applied=False,
            modeled_next_clip_number=0,
            title_name="",
            title_name_length=0,
            sdhc_card_detected=False,
            sdhc_standard_lock_active=False,
            custom_movie_folder_prohibited=False,
            canonical_slot1_media_type="INVALID",
            canonical_slot2_media_type="INVALID",
            shot_mark1_present=False,
            shot_mark2_present=False,
            shot_mark_xml_sidecar_path="",
            canonical_image_jump_setting="INVALID",
            image_jump_matched=False,
            canonical_transfer_target_movie="INVALID",
            transfer_filter_eligible=False,
            errors=tuple(errors),
            warnings=(),
        )

    model_id_int = (
        body_model_id
        if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
        else int(str(body_model_id), 0)
        if isinstance(body_model_id, str) and str(body_model_id).strip()
        else -1
    )
    if body_model_name.strip().upper() != FX3_MODEL_NAME or model_id_int != FX3_MODEL_ID:
        _add_code(codes, STATUS_BLOCKED_G77_TELEMETRY_INVALID)
        errors.append(
            f"Gate G77 requires {FX3_MODEL_NAME} ({hex(FX3_MODEL_ID)}), got "
            f"{body_model_name!r} ({hex(max(model_id_int, 0))})."
        )

    canon_fmt = _norm_file_name_format(file_name_format)
    canon_fnum = re.sub(r"[^A-Z0-9]+", "_", file_number_mode.strip().upper()).strip("_")
    canon_s1 = _norm_slot_media_type(slot1_media_type)
    canon_s2 = _norm_slot_media_type(slot2_media_type)

    # 1. [File Name Format] (5 modes across Slot 1 & Slot 2) & [File Number] (Series/Reset)
    if canon_fmt not in ALLOWED_FILE_NAME_FORMATS:
        _add_code(codes, STATUS_BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID)
        errors.append(
            f"Invalid [File Name Format]={file_name_format!r}; expected {ALLOWED_FILE_NAME_FORMATS}."
        )
    if slot2_file_name_format is not None and _norm_file_name_format(slot2_file_name_format) != canon_fmt:
        _add_code(codes, STATUS_BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID)
        errors.append(
            "FX3 [File Settings] -> [File Name Format] applies uniformly across both Slot 1 and Slot 2."
        )
    if canon_fnum not in ALLOWED_FILE_NUMBER_MODES:
        _add_code(codes, STATUS_BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID)
        errors.append(
            f"Invalid [File Number]={file_number_mode!r}; expected Series or Reset."
        )
    if not (0 <= previous_clip_number <= 9999) or not (1 <= reel_number <= 999) or (
        len(cam_id.strip()) != 1 or not ("A" <= cam_id.strip().upper() <= "Z")
    ):
        _add_code(codes, STATUS_BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID)
        errors.append(
            "Invalid Cam ID (A..Z), Reel# (1..999), or previous clip counter (0..9999)."
        )

    if series_counter_reset_executed or (canon_fnum == "RESET" and card_swapped_to_empty):
        modeled_next_num = 1
    else:
        modeled_next_num = 1 if previous_clip_number >= 9999 else (previous_clip_number + 1)

    if claimed_next_clip_number is not None and claimed_next_clip_number != modeled_next_num:
        _add_code(codes, STATUS_BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID)
        errors.append(
            f"Claimed next clip number {claimed_next_clip_number} mismatches modeled {modeled_next_num} "
            f"(mode={canon_fnum}, series_reset={series_counter_reset_executed})."
        )

    # 2. [Title Name Settings] max 37 ASCII chars & exact allowed symbol set + forward-only apply
    title_ok, bad_chars = validate_fx3_title_name(title_name)
    if not title_ok or retroactive_existing_clip_rename_claimed:
        _add_code(codes, STATUS_BLOCKED_G77_TITLE_NAME_LENGTH_OR_CHARSET_INVALID)
        errors.append(
            f"[Title Name Settings]={title_name!r} invalid (len={len(title_name)}/{TITLE_NAME_MAX_CHARS}, "
            f"bad_chars={bad_chars}, retroactive={retroactive_existing_clip_rename_claimed})."
        )

    # 3. SDHC (<=32GB FAT32) forced [Standard] lock & custom movie folder prohibition
    if canon_s1 not in ALLOWED_SLOT_MEDIA_TYPES_G77 or canon_s2 not in ALLOWED_SLOT_MEDIA_TYPES_G77 or (
        canon_s1 == "NONE" and canon_s2 == "NONE"
    ):
        _add_code(codes, STATUS_BLOCKED_G77_TELEMETRY_INVALID)
        errors.append(
            f"Invalid media slot topology ({slot1_media_type!r}, {slot2_media_type!r})."
        )

    eff_fmt, sdhc_lock = resolve_effective_fx3_file_name_format(
        canon_fmt,
        slot1_media_type=canon_s1,
        slot2_media_type=canon_s2,
        slot1_capacity_gb=slot1_capacity_gb,
        slot2_capacity_gb=slot2_capacity_gb,
        slot1_filesystem=slot1_filesystem,
        slot2_filesystem=slot2_filesystem,
    )
    folder_norm = movie_clip_folder.strip().upper().rstrip("/")
    standard_folder_ok = folder_norm in ("M4ROOT/CLIP", "PRIVATE/M4ROOT/CLIP")
    if sdhc_lock and canon_fmt != FILE_NAME_FORMAT_STANDARD:
        _add_code(codes, STATUS_BLOCKED_G77_SDHC_STANDARD_LOCK_OR_CUSTOM_FOLDER_FORBIDDEN)
        errors.append(
            f"SDHC card (<=32GB FAT32) force-locks [File Name Format] to [Standard]; "
            f"requested {file_name_format!r} is blocked."
        )
    if (
        claimed_effective_file_name_format is not None
        and _norm_file_name_format(claimed_effective_file_name_format) != eff_fmt
    ):
        _add_code(codes, STATUS_BLOCKED_G77_SDHC_STANDARD_LOCK_OR_CUSTOM_FOLDER_FORBIDDEN)
        errors.append(
            f"Claimed effective [File Name Format] {claimed_effective_file_name_format!r} "
            f"mismatches {eff_fmt!r}."
        )
    if custom_movie_folder_requested or not standard_folder_ok:
        _add_code(codes, STATUS_BLOCKED_G77_SDHC_STANDARD_LOCK_OR_CUSTOM_FOLDER_FORBIDDEN)
        errors.append(
            f"Custom movie folder names are prohibited on ILME-FX3 (got {movie_clip_folder!r})."
        )

    # 4. [Shot Mark] (Add Shot Mark1/2 in Rec, Add/Delete Shot Mark1/2 in Playback) & *M01.XML
    canon_mode = _norm_shooting_mode_g78(shooting_mode)
    canon_rec_key = re.sub(r"[^A-Z0-9]+", "_", rec_shot_mark_key.strip().upper()).strip("_")
    canon_pb_op = re.sub(r"[^A-Z0-9]+", "_", playback_shot_mark_op.strip().upper()).strip("_")
    xml_upper = shot_mark_xml_path.strip().upper().replace("\\", "/")
    xml_ok = (
        ("M4ROOT/CLIP/" in xml_upper)
        and xml_upper.endswith(SHOTMARK_XML_SIDECAR_SUFFIX)
        and len(Path(xml_upper).name) > len(SHOTMARK_XML_SIDECAR_SUFFIX)
    )
    if (
        canon_rec_key not in ALLOWED_SHOTMARK_REC_KEYS
        or canon_pb_op not in ALLOWED_SHOTMARK_PLAYBACK_OPS
        or (canon_mode == "STILL" and canon_rec_key != "NONE")
        or (not xml_ok)
        or video_essence_mutated_by_shotmark
    ):
        _add_code(codes, STATUS_BLOCKED_G77_SHOTMARK_XML_SIDECAR_OR_MODE_VIOLATION)
        errors.append(
            "Shot Mark1/2 must persist strictly in M4ROOT/CLIP/*M01.XML without MP4 essence "
            "mutation and is unavailable in Still photo mode."
        )

    # 5. [Image Jump Setting] & [Only Shot Mark Mov.] / [Only Shot Mark] transfer filter
    canon_jump = _norm_image_jump_setting(image_jump_setting)
    canon_xfer = _norm_transfer_target(transfer_target_movie)
    jump_matched, xfer_eligible = evaluate_shotmark_jump_and_transfer_match(
        shot_mark1=shot_mark1_present,
        shot_mark2=shot_mark2_present,
        image_jump_setting=canon_jump,
        transfer_target_movie=canon_xfer,
    )
    if (
        canon_jump not in ALLOWED_SHOTMARK_IMAGE_JUMP_SETTINGS
        or canon_xfer not in ALLOWED_SHOTMARK_TRANSFER_TARGETS
        or (claimed_image_jump_matched is not None and bool(claimed_image_jump_matched) != jump_matched)
        or (clip_selected_for_transfer and not xfer_eligible)
        or unmarked_clip_transferred_under_shotmark_filter
    ):
        _add_code(codes, STATUS_BLOCKED_G77_SHOTMARK_JUMP_OR_TRANSFER_FILTER_VIOLATION)
        errors.append(
            f"[Image Jump Setting]={image_jump_setting!r} or transfer filter "
            f"[Target Movie]={transfer_target_movie!r} violated for ShotMark=({shot_mark1_present},{shot_mark2_present})."
        )

    valid = len(codes) == 0
    return FileSettingsSdhcAndShotMarkGuardResult(
        valid=valid,
        status=STATUS_VERIFIED_G77 if valid else codes[0],
        violation_codes=tuple(codes),
        body_model_name=FX3_MODEL_NAME,
        body_model_id_hex=hex(FX3_MODEL_ID),
        firmware_version=firmware_version.strip(),
        canonical_file_name_format=canon_fmt,
        effective_file_name_format=eff_fmt,
        canonical_file_number_mode=canon_fnum,
        series_counter_reset_applied=series_counter_reset_executed,
        modeled_next_clip_number=modeled_next_num,
        title_name=title_name,
        title_name_length=len(title_name),
        sdhc_card_detected=sdhc_lock,
        sdhc_standard_lock_active=sdhc_lock,
        custom_movie_folder_prohibited=(not custom_movie_folder_requested) and standard_folder_ok,
        canonical_slot1_media_type=canon_s1,
        canonical_slot2_media_type=canon_s2,
        shot_mark1_present=shot_mark1_present,
        shot_mark2_present=shot_mark2_present,
        shot_mark_xml_sidecar_path=shot_mark_xml_path.strip(),
        canonical_image_jump_setting=canon_jump,
        image_jump_matched=jump_matched,
        canonical_transfer_target_movie=canon_xfer,
        transfer_filter_eligible=xfer_eligible,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 3. Gate G78 Validators (`G78_TC_REGENERATE_SLOT1_EXTLK_RELEASE_AND_RECLAMP_COUPLED_TALLY_GUARD`)
# ---------------------------------------------------------------------------


def resolve_tc_regenerate_slot_and_extlk(
    *,
    shooting_mode: str = "Movie",
    time_code_make: str = "Regenerate",
    time_code_run: str = "Free Run",
    recording_media: str = "Simult. Recording",
    vmc_bncm1_attached: bool = False,
    tc_make_switched_after_lock: bool = False,
    tc_run_switched_after_lock: bool = False,
) -> Tuple[str, Optional[str], bool]:
    """Return `(effective_tc_run, regenerate_reference_slot, modeled_ext_lk_active)`."""
    mode = _norm_shooting_mode_g78(shooting_mode)
    tc_make = re.sub(r"[^A-Z0-9]+", "_", time_code_make.strip().upper()).strip("_")
    tc_run = re.sub(r"[^A-Z0-9]+", "_", time_code_run.strip().upper()).strip("_")
    rec_media = _norm_recording_media_g78(recording_media)

    eff_run = TC_RUN_REC_RUN if tc_make == TC_MAKE_REGENERATE else tc_run
    if tc_make == TC_MAKE_REGENERATE:
        ref_slot: Optional[str] = (
            REC_MEDIA_SLOT_1 if rec_media == REC_MEDIA_SIMULT_RECORDING else rec_media
        )
    else:
        ref_slot = None

    ext_lk_active = (
        bool(vmc_bncm1_attached)
        and mode == "MOVIE"
        and tc_make == TC_MAKE_PRESET
        and tc_run == TC_RUN_FREE_RUN
        and (not tc_make_switched_after_lock)
        and (not tc_run_switched_after_lock)
    )
    return eff_run, ref_slot, ext_lk_active


def resolve_fx3_rec_lamp_coupled_tally(
    *,
    rec_lamp_mode: str = "Only Front Off",
    is_recording: bool = True,
    emphasized_rec_display_on: bool = True,
    hdmi_info_display_on: bool = False,
) -> Tuple[bool, bool, bool, bool, bool]:
    """Return `(front_led, rear_led, top_rec_button_led, osd_red_frame, hdmi_red_frame)`."""
    mode = _norm_rec_lamp_mode(rec_lamp_mode)
    if not is_recording:
        return False, False, False, False, False
    if mode == REC_LAMP_ALL_ON:
        front_on, rear_on, top_on = True, True, True
    elif mode == REC_LAMP_ONLY_FRONT_OFF:
        front_on, rear_on, top_on = False, True, True
    else:
        front_on, rear_on, top_on = False, False, False
    osd_red = bool(emphasized_rec_display_on)
    hdmi_red = bool(emphasized_rec_display_on and hdmi_info_display_on)
    return front_on, rear_on, top_on, osd_red, hdmi_red


def verify_tc_regenerate_extlk_and_reclamp_tally_guard(
    *,
    shooting_mode: str = "Movie",
    time_code_make: str = "Regenerate",
    time_code_run: str = "Free Run",
    claimed_effective_time_code_run: Optional[str] = None,
    recording_media: str = "Simult. Recording",
    regenerate_reference_slot: Optional[str] = None,
    slot1_last_clip_end_tc: str = "01:12:34:18",
    slot2_last_clip_end_tc: str = "02:45:00:00",
    claimed_regenerated_start_tc: Optional[str] = None,
    vmc_bncm1_attached: bool = False,
    tc_make_switched_after_lock: bool = False,
    tc_run_switched_after_lock: bool = False,
    claimed_ext_lk_active: Optional[bool] = None,
    sq_time_code_run_selectable_claimed: bool = False,
    hdmi_time_code_output_on: bool = False,
    rec_lamp_mode: str = "Only Front Off",
    is_recording: bool = True,
    front_tally_led_on: Optional[bool] = None,
    rear_tally_led_on: Optional[bool] = None,
    top_rec_button_led_on: Optional[bool] = None,
    emphasized_rec_display_on: bool = True,
    hdmi_info_display_on: bool = False,
    hdmi_red_rec_frame_active: Optional[bool] = None,
    silent_mode_on: bool = False,
    audio_signals_menu_on: bool = True,
    effective_audio_signals_on: Optional[bool] = None,
    audio_signals_editable_in_silent_mode_claimed: bool = False,
    af_or_selftimer_beep_emitted: bool = False,
) -> TcRegenerateSlot1AndRecLampTallyResult:
    """Validate `ILME-FX3 Ver. 7.02` Gate G78 `[TC/UB]` `[Regenerate]` forced `[Rec Run]`
    & Slot-1 master read, `VMC-BNCM1` `EXT-LK` prerequisite & immediate release, S&Q TC Run /
    HDMI TC Out lockout, 3-state coupled Rear+Top `[REC Lamp]` + `[Emphasized REC Display]`,
    and `[Silent Mode] -> [Audio signals]=Off` hard lock.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        not isinstance(shooting_mode, str)
        or not isinstance(time_code_make, str)
        or not isinstance(time_code_run, str)
        or not isinstance(recording_media, str)
        or not isinstance(slot1_last_clip_end_tc, str)
        or not isinstance(slot2_last_clip_end_tc, str)
        or not isinstance(rec_lamp_mode, str)
        or not isinstance(vmc_bncm1_attached, bool)
        or not isinstance(tc_make_switched_after_lock, bool)
        or not isinstance(tc_run_switched_after_lock, bool)
        or not isinstance(sq_time_code_run_selectable_claimed, bool)
        or not isinstance(hdmi_time_code_output_on, bool)
        or not isinstance(is_recording, bool)
        or not isinstance(emphasized_rec_display_on, bool)
        or not isinstance(hdmi_info_display_on, bool)
        or not isinstance(silent_mode_on, bool)
        or not isinstance(audio_signals_menu_on, bool)
        or not isinstance(audio_signals_editable_in_silent_mode_claimed, bool)
        or not isinstance(af_or_selftimer_beep_emitted, bool)
    ):
        _add_code(codes, STATUS_BLOCKED_G78_TELEMETRY_INVALID)
        errors.append("Gate G78 received invalid telemetry argument types.")
        return TcRegenerateSlot1AndRecLampTallyResult(
            valid=False,
            status=codes[0],
            violation_codes=tuple(codes),
            canonical_shooting_mode="INVALID",
            canonical_time_code_make="INVALID",
            canonical_time_code_run_menu="INVALID",
            effective_time_code_run="INVALID",
            regenerate_forced_rec_run=False,
            canonical_recording_media="INVALID",
            regenerate_reference_slot=None,
            vmc_bncm1_attached=False,
            modeled_ext_lk_active=False,
            ext_lk_released_on_tc_change=False,
            sq_tc_run_locked_out=False,
            hdmi_time_code_output_on=False,
            canonical_rec_lamp_mode="INVALID",
            front_tally_led_on=False,
            rear_tally_led_on=False,
            top_rec_button_led_on=False,
            rear_and_top_tally_coupled=False,
            emphasized_rec_display_on=False,
            hdmi_info_display_on=False,
            hdmi_red_rec_frame_active=False,
            silent_mode_on=False,
            effective_audio_signals_on=False,
            errors=tuple(errors),
            warnings=(),
        )

    canon_mode = _norm_shooting_mode_g78(shooting_mode)
    canon_make = re.sub(r"[^A-Z0-9]+", "_", time_code_make.strip().upper()).strip("_")
    canon_run = re.sub(r"[^A-Z0-9]+", "_", time_code_run.strip().upper()).strip("_")
    canon_media = _norm_recording_media_g78(recording_media)
    canon_lamp = _norm_rec_lamp_mode(rec_lamp_mode)

    if (
        canon_mode not in ("MOVIE", "S&Q", "STILL")
        or canon_make not in ALLOWED_TIME_CODE_MAKE_MODES
        or canon_run not in ALLOWED_TIME_CODE_RUN_MODES
        or canon_media not in ALLOWED_RECORDING_MEDIA_MODES_G78
    ):
        _add_code(codes, STATUS_BLOCKED_G78_TELEMETRY_INVALID)
        errors.append(
            f"Unsupported G78 mode/TC/media enum ({shooting_mode!r}, {time_code_make!r}, "
            f"{time_code_run!r}, {recording_media!r})."
        )

    eff_run, modeled_ref_slot, modeled_ext_lk = resolve_tc_regenerate_slot_and_extlk(
        shooting_mode=canon_mode,
        time_code_make=canon_make,
        time_code_run=canon_run,
        recording_media=canon_media,
        vmc_bncm1_attached=vmc_bncm1_attached,
        tc_make_switched_after_lock=tc_make_switched_after_lock,
        tc_run_switched_after_lock=tc_run_switched_after_lock,
    )

    # 1. [Regenerate] forces [Rec Run] & reads exclusively from Slot 1 under [Simult. Recording]
    eff_ref_slot = (
        modeled_ref_slot
        if regenerate_reference_slot is None
        else _norm_recording_media_g78(regenerate_reference_slot)
    )
    if canon_make == TC_MAKE_REGENERATE:
        if claimed_effective_time_code_run is not None:
            c_run = re.sub(
                r"[^A-Z0-9]+", "_", claimed_effective_time_code_run.strip().upper()
            ).strip("_")
            if c_run != TC_RUN_REC_RUN:
                _add_code(codes, STATUS_BLOCKED_G78_TC_REGENERATE_REC_RUN_OR_SLOT1_VIOLATION)
                errors.append(
                    "[Time Code Make]=[Regenerate] forces advancement in [Rec Run] regardless of [Time Code Run]."
                )
        if eff_ref_slot != modeled_ref_slot:
            _add_code(codes, STATUS_BLOCKED_G78_TC_REGENERATE_REC_RUN_OR_SLOT1_VIOLATION)
            errors.append(
                f"[Time Code Make]=[Regenerate] under {canon_media} must read last TC from "
                f"{modeled_ref_slot}, got {regenerate_reference_slot!r}."
            )
        expected_tc = (
            slot1_last_clip_end_tc.strip()
            if modeled_ref_slot == REC_MEDIA_SLOT_1
            else slot2_last_clip_end_tc.strip()
        )
        if (
            claimed_regenerated_start_tc is not None
            and claimed_regenerated_start_tc.strip() != expected_tc
        ):
            _add_code(codes, STATUS_BLOCKED_G78_TC_REGENERATE_REC_RUN_OR_SLOT1_VIOLATION)
            errors.append(
                f"Regenerated TC {claimed_regenerated_start_tc!r} did not continue from "
                f"{modeled_ref_slot} end TC {expected_tc!r}."
            )

    # 2. VMC-BNCM1 EXT-LK prerequisite (Movie + Preset + Free Run) & immediate release
    ext_lk_released = bool(
        vmc_bncm1_attached
        and (
            tc_make_switched_after_lock
            or tc_run_switched_after_lock
            or canon_make != TC_MAKE_PRESET
            or canon_run != TC_RUN_FREE_RUN
            or canon_mode != "MOVIE"
        )
    )
    if claimed_ext_lk_active is not None and bool(claimed_ext_lk_active) != modeled_ext_lk:
        _add_code(codes, STATUS_BLOCKED_G78_VMC_BNCM1_EXT_LK_PREREQ_OR_RELEASE_VIOLATION)
        errors.append(
            "VMC-BNCM1 EXT-LK requires Movie + [Preset] + [Free Run] and releases immediately "
            "upon changing [Time Code Make] or [Time Code Run]."
        )

    # 3. S&Q lockout of [Time Code Run] and HDMI [Time Code Output]
    sq_locked = canon_mode == "S&Q"
    if sq_locked and (sq_time_code_run_selectable_claimed or hdmi_time_code_output_on):
        _add_code(codes, STATUS_BLOCKED_G78_SQ_TC_RUN_OR_HDMI_TCOUT_LOCKOUT)
        errors.append(
            "During S&Q shooting, both [Time Code Run] and HDMI [Time Code Output] are unavailable."
        )

    # 4. Physical [REC Lamp] 3-state coupled Rear + Top REC button tally & HDMI red frame
    if canon_lamp not in ALLOWED_FX3_REC_LAMP_MODES:
        _add_code(codes, STATUS_BLOCKED_G78_REC_LAMP_COUPLED_TALLY_OR_OSD_VIOLATION)
        errors.append(
            f"ILME-FX3 [REC Lamp] exposes strictly All On / Only Front Off / All Off, got {rec_lamp_mode!r}."
        )
    m_front, m_rear, m_top, _m_osd, m_hdmi_red = resolve_fx3_rec_lamp_coupled_tally(
        rec_lamp_mode=canon_lamp,
        is_recording=is_recording,
        emphasized_rec_display_on=emphasized_rec_display_on,
        hdmi_info_display_on=hdmi_info_display_on,
    )
    eff_front = m_front if front_tally_led_on is None else bool(front_tally_led_on)
    eff_rear = m_rear if rear_tally_led_on is None else bool(rear_tally_led_on)
    eff_top = m_top if top_rec_button_led_on is None else bool(top_rec_button_led_on)
    eff_hdmi_red = (
        m_hdmi_red if hdmi_red_rec_frame_active is None else bool(hdmi_red_rec_frame_active)
    )
    coupled_ok = eff_rear == eff_top
    if (
        (not coupled_ok)
        or (eff_front != m_front)
        or (eff_rear != m_rear)
        or (eff_top != m_top)
        or (eff_hdmi_red != m_hdmi_red)
    ):
        _add_code(codes, STATUS_BLOCKED_G78_REC_LAMP_COUPLED_TALLY_OR_OSD_VIOLATION)
        errors.append(
            "FX3 top REC button LED is hardware-coupled to the rear recording lamp, and "
            "[Emphasized REC Display] outputs to HDMI strictly when [HDMI Info. Display]=[On]."
        )

    # 5. [Silent Mode]=[On] -> [Audio signals]=[Off] hard lock
    modeled_audio_sig = False if silent_mode_on else bool(audio_signals_menu_on)
    eff_audio_sig = (
        modeled_audio_sig
        if effective_audio_signals_on is None
        else bool(effective_audio_signals_on)
    )
    if silent_mode_on and (
        eff_audio_sig
        or audio_signals_editable_in_silent_mode_claimed
        or af_or_selftimer_beep_emitted
    ):
        _add_code(codes, STATUS_BLOCKED_G78_SILENT_MODE_AUDIO_SIGNALS_LOCK_VIOLATION)
        errors.append(
            "Enabling [Silent Mode]=[On] hard-locks [Audio signals] to [Off] (silencing AF/self-timer beeps)."
        )

    valid = len(codes) == 0
    return TcRegenerateSlot1AndRecLampTallyResult(
        valid=valid,
        status=STATUS_VERIFIED_G78 if valid else codes[0],
        violation_codes=tuple(codes),
        canonical_shooting_mode=canon_mode,
        canonical_time_code_make=canon_make,
        canonical_time_code_run_menu=canon_run,
        effective_time_code_run=eff_run,
        regenerate_forced_rec_run=(canon_make == TC_MAKE_REGENERATE),
        canonical_recording_media=canon_media,
        regenerate_reference_slot=eff_ref_slot,
        vmc_bncm1_attached=vmc_bncm1_attached,
        modeled_ext_lk_active=modeled_ext_lk,
        ext_lk_released_on_tc_change=ext_lk_released,
        sq_tc_run_locked_out=sq_locked,
        hdmi_time_code_output_on=hdmi_time_code_output_on,
        canonical_rec_lamp_mode=canon_lamp,
        front_tally_led_on=eff_front,
        rear_tally_led_on=eff_rear,
        top_rec_button_led_on=eff_top,
        rear_and_top_tally_coupled=coupled_ok,
        emphasized_rec_display_on=emphasized_rec_display_on,
        hdmi_info_display_on=hdmi_info_display_on,
        hdmi_red_rec_frame_active=eff_hdmi_red,
        silent_mode_on=silent_mode_on,
        effective_audio_signals_on=eff_audio_sig,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G77 & Gate G78 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g77_filesettings_shotmark_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    filesettings_shotmark_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase214DonorAuditResult] = None,
) -> Tuple[GateVerdict, G77FileSettingsShotMarkGuardResult]:
    """Evaluate Gate G77 (`G77_FILE_SETTINGS_SDHC_37CHAR_LOCK_AND_SHOTMARK_XML_FILTER_GUARD`)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase214_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_file_settings_sdhc_37char_and_shotmark_guard(
        **dict(filesettings_shotmark_kwargs or {})
    )

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE214_DONOR_INTEGRITY)
    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G77 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G77 if valid else codes[0]

    res = G77FileSettingsShotMarkGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        filesettings_shotmark_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, fmt={guard.effective_file_name_format}"
        f"(sdhc_lock={guard.sdhc_standard_lock_active}), fnum={guard.canonical_file_number_mode}"
        f"->#{guard.modeled_next_clip_number:04d}, title_len={guard.title_name_length}/{TITLE_NAME_MAX_CHARS}, "
        f"shotmark=({guard.shot_mark1_present},{guard.shot_mark2_present})@{guard.canonical_image_jump_setting}"
    )
    verdict = GateVerdict(
        gate_id=G77_GATE_ID,
        gate_code=G77_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


def evaluate_g78_tcregen_reclamp_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    tcregen_reclamp_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase214DonorAuditResult] = None,
) -> Tuple[GateVerdict, G78TcRegenRecLampGuardResult]:
    """Evaluate Gate G78 (`G78_TC_REGENERATE_SLOT1_EXTLK_RELEASE_AND_RECLAMP_COUPLED_TALLY_GUARD`)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase214_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
        **dict(tcregen_reclamp_kwargs or {})
    )

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE214_DONOR_INTEGRITY)
    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G78 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G78 if valid else codes[0]

    res = G78TcRegenRecLampGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        tcregen_reclamp_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, tc={guard.canonical_time_code_make}->"
        f"{guard.effective_time_code_run}(src={guard.regenerate_reference_slot}), "
        f"ext_lk={guard.modeled_ext_lk_active}, lamp={guard.canonical_rec_lamp_mode}"
        f"(F={guard.front_tally_led_on},R={guard.rear_tally_led_on},Top={guard.top_rec_button_led_on}), "
        f"silent={guard.silent_mode_on}(audio_sig={guard.effective_audio_signals_on})"
    )
    verdict = GateVerdict(
        gate_id=G78_GATE_ID,
        gate_code=G78_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Unified 78-Gate Master Safety Preflight (`G01..G78`)
# ---------------------------------------------------------------------------


def evaluate_78gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    filesettings_shotmark_kwargs: Optional[Mapping[str, Any]] = None,
    tcregen_reclamp_kwargs: Optional[Mapping[str, Any]] = None,
    master_76_override: Optional[Master76GateReport] = None,
    **m76_passthrough_kwargs: Any,
) -> Master78GateReport:
    """Evaluate all 78 Master Safety Gates (`G01..G78`) deterministically by delegating
    `G01..G76` directly to `evaluate_76gate_preflight()`.
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

    m76_report: Master76GateReport = (
        master_76_override
        if master_76_override is not None
        else evaluate_76gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m76_passthrough_kwargs,
        )
    )

    phase214_audit = audit_phase214_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g77_verdict, g77_res = evaluate_g77_filesettings_shotmark_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        filesettings_shotmark_kwargs=filesettings_shotmark_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase214_audit,
    )

    g78_verdict, g78_res = evaluate_g78_tcregen_reclamp_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        tcregen_reclamp_kwargs=tcregen_reclamp_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase214_audit,
    )

    gates_77_to_78 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g77_verdict, g78_verdict)
    ]
    all_gates = tuple(list(m76_report.gates) + gates_77_to_78)

    g01_to_g12_verified = int(m76_report.summary["g01_to_g12_verified"])
    g13_to_g76_verified = (
        int(m76_report.summary["g13_to_g74_verified"])
        + int(m76_report.summary["g75_to_g76_verified"])
    )
    g77_to_g78_verified = sum(1 for v in (g77_verdict, g78_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g76_verified + g77_to_g78_verified

    g77_to_g78_all_passed = g77_to_g78_verified == 2
    g13_to_g78_all_passed = m76_report.g13_to_g76_all_passed and g77_to_g78_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m76_report.gates[:9])

    offline_75_verified = (
        g01_to_g09_ok
        and m76_report.offline_73_gates_verified
        and g77_to_g78_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_78_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g78_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m76_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_75_verified
        and m76_report.h0_h1_trial_entry_allowed
        and g77_to_g78_all_passed
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
        list(m76_report.errors) + list(g77_verdict.errors) + list(g78_verdict.errors)
    )
    warnings: List[str] = (
        list(m76_report.warnings)
        + list(g77_verdict.warnings)
        + list(g78_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m76_report.g13_to_g76_all_passed:
        overall_status = m76_report.status
    elif not g77_verdict.passed:
        overall_status = g77_verdict.status
    elif not g78_verdict.passed:
        overall_status = g78_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_78_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_78_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_78_verified:
        overall_status = "VERIFIED_ALL_78_GATES"
    else:
        overall_status = "VERIFIED_75_OF_78_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m76_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g77_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g78_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 78,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 78 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g76_verified": g13_to_g76_verified,
        "g77_to_g78_verified": g77_to_g78_verified,
        "g13_to_g78_all_passed": g13_to_g78_all_passed,
        "g77_to_g78_all_passed": g77_to_g78_all_passed,
        "offline_75_gates_verified": offline_75_verified,
        "all_78_gates_verified": all_78_verified,
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

    return Master78GateReport(
        schema=REALHW_FILESETTINGS_SHOTMARK_TCREGEN_RECLAMP_78GATE_SCHEMA,
        version=REALHW_FILESETTINGS_SHOTMARK_TCREGEN_RECLAMP_78GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_75_gates_verified=offline_75_verified,
        all_78_gates_verified=all_78_verified,
        g13_to_g78_all_passed=g13_to_g78_all_passed,
        g77_to_g78_all_passed=g77_to_g78_all_passed,
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
        master_76_report=m76_report.to_dict(),
        g77_result=g77_res.to_dict(),
        g78_result=g78_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_78_master_safety_gates = evaluate_78gate_preflight
run_78_gate_preflight = evaluate_78gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard",
        description=(
            "Phase 214 Safety Gates G77 (File Settings 37-Char & SDHC Lock + Shot Mark1/2 XML "
            "Filter Guard) + G78 (TC Regenerate Slot-1, EXT-LK Release & Coupled REC Lamp Tally "
            "Guard) + Unified 78-Gate Master Safety Preflight"
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

    report = evaluate_78gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/78 "
            f"g77_to_g78_all_passed={report.g77_to_g78_all_passed} "
            f"all_78_gates_verified={report.all_78_gates_verified} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = report.all_78_gates_verified if args.dry_run_simulated else report.offline_75_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
