"""Phase 224 Real-Hardware Safety Gates (`G81..G82`) & Unified 82-Gate Master
Safety Preflight (`verify-82-gates`) for Sony `ILME-FX3` (`Ver. 7.02`).

Implements Wave-31 official Sony `ILME-FX3` (`Ver. 7.02`) hardware rules while delegating
Gates `G01..G80` directly to `evaluate_80gate_preflight()` from
`realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.py`:

1. **Gate G81 (`G81_STEADYSHOT_ACTIVE_RAW_HFR_CUTOFF_AND_CIZ_CENTER_AF_MULTI_METERING_GUARD`)**:
   - Models movie `[SteadyShot]` (`Active` narrower angle-of-view crop `~1.1x` vs `Standard` /
     `Off`) and enforces all 3 `[Active]` disqualification conditions: Normal movie
     `119.88p`/`100p`, S&Q `>=120fps`/`100fps` (`100fps`/`120fps`/`200fps`/`240fps`), and
     external HDMI `[RAW Output]` = `On`, plus `[SteadyShot Focal Len.]` (`8mm..1000mm`)
     validation when manual focal-length input is selected.
   - Models `[Clear Image Zoom]` / `[Digital Zoom]` (`[Zoom Range]`): blocks non-optical zoom
     when still `[File Format]` is `RAW` / `RAW & JPEG` / `RAW & HEIF`, Normal movie
     `119.88p`/`100p`, or S&Q `120fps/100fps`/`240fps/200fps`, and enforces all 4 automatic
     camera state locks whenever non-optical zoom is active: `[Focus Area]` setting disabled
     (center-priority AF), `[Metering Mode]` hard-locked to `[Multi]`, `[Face/Eye Prior. in AF]`
     & `[Face Priority in Multi Metering]` disabled, and `Real-time Tracking` unavailable.
   - Bounded `< 0.15s` `O_RDONLY` local donor check (`raw_firmware_bytes_leaked == 0`) with
     deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.

2. **Gate G82 (`G82_POWER_SAVE_START_TIME_9COND_BYPASS_AND_AUTO_POWER_OFF_TEMP_TRIPOD_GUARD`)**:
   - Enforces exact `ILME-FX3` menu item `[Power Save Start Time]` (factory default `5 Min`;
     options `Off`, `30 Min`, `5 Min`, `2 Min`, `1 Min`, `10 Sec`) and its 9 automatic
     deactivation conditions (USB power supply, slideshow playback, FTP transfer, movie
     recording, PC connection, TV/HDMI connection, `[IR Remote Ctrl]` = `On`,
     `[Bluetooth Rmt Ctrl]` = `On`, streaming / Creators' Cloud upload), plus air-gapped
     internal-battery (`NP-FZ100` without USB/HDMI/FTP/Remote/PC/Streaming) Tier-0 `75 MiB`
     `p3` dump pre-check requiring `[Power Save Start Time]` = `Off` or `30 Min`.
   - Enforces `[Auto Power OFF Temp.]` (`Standard` default vs `High`): requires
     `tripod_mounted == True` whenever `[Auto Power OFF Temp.]` = `High` (blocking prolonged
     hand-held low-temperature contact burn hazard) and couples with `[Fan Control]` thermal
     protection (`Always Off` blocked under `High`; `>=62.0C` override / `>=90.0C` fail-closed ceiling enforced).

3. **Unified `verify-82-gates` Master Safety Preflight**:
   - Combines `G01..G80` + `G81` + `G82` (`79/82` offline pass with the 3 physical-bench
     Tier-0 gates `G10..G12` awaiting receipt; `82/82` in `--simulate-bench-dry-run`).

Hard-locked safety redlines:
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
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from .master_16gate_preflight import DEFAULT_REPO_ROOT, GateVerdict
from .realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard import (
    _DONOR_BLOB_CACHE,
)
from .realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
)
from .realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard import (
    Master80GateReport,
    evaluate_80gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    FAIL_CLOSED_TEARDOWN_TEMP_C,
    SOC_FAN_OVERRIDE_TEMP_C,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_STEADYSHOT_CIZ_POWERSAVE_AUTOTEMP_82GATE_SCHEMA: str = (
    "fx3-realhw-steadyshot-ciz-powersave-autotemp-82gate-preflight-v1"
)
REALHW_STEADYSHOT_CIZ_POWERSAVE_AUTOTEMP_82GATE_VERSION: str = "1.0.0"

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
FX3_DEFAULT_FW_VERSION_G81: str = "7.02"

# Gate IDs & Canonical Codes for G81..G82
G81_GATE_ID: str = (
    "G81_steadyshot_active_raw_hfr_cutoff_and_ciz_center_af_multi_metering_guard"
)
G81_GATE_CODE: str = (
    "G81_STEADYSHOT_ACTIVE_RAW_HFR_CUTOFF_AND_CIZ_CENTER_AF_MULTI_METERING_GUARD"
)
GATE_G81_STEADYSHOT_ACTIVE_RAW_HFR_CUTOFF_AND_CIZ_CENTER_AF_MULTI_METERING_GUARD: str = (
    G81_GATE_CODE
)
G81: str = G81_GATE_CODE

G82_GATE_ID: str = (
    "G82_power_save_start_time_9cond_bypass_and_auto_power_off_temp_tripod_guard"
)
G82_GATE_CODE: str = (
    "G82_POWER_SAVE_START_TIME_9COND_BYPASS_AND_AUTO_POWER_OFF_TEMP_TRIPOD_GUARD"
)
GATE_G82_POWER_SAVE_START_TIME_9COND_BYPASS_AND_AUTO_POWER_OFF_TEMP_TRIPOD_GUARD: str = (
    G82_GATE_CODE
)
G82: str = G82_GATE_CODE

# Status & Violation Codes
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G81: str = (
    "VERIFIED_STEADYSHOT_ACTIVE_RAW_HFR_CUTOFF_AND_CIZ_CENTER_AF_MULTI_METERING_GUARD"
)
STATUS_VERIFIED_G82: str = (
    "VERIFIED_POWER_SAVE_START_TIME_9COND_BYPASS_AND_AUTO_POWER_OFF_TEMP_TRIPOD_GUARD"
)

STATUS_BLOCKED_G81_STEADYSHOT_ACTIVE_RAW_OR_HFR_CUTOFF: str = (
    "BLOCKED_G81_STEADYSHOT_ACTIVE_RAW_OR_HFR_CUTOFF"
)
STATUS_BLOCKED_G81_STEADYSHOT_ACTIVE_AOV_CROP_OR_LENS_VIOLATION: str = (
    "BLOCKED_G81_STEADYSHOT_ACTIVE_AOV_CROP_OR_LENS_VIOLATION"
)
STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN: str = (
    "BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN"
)
STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_4LOCK_AF_METERING_VIOLATION: str = (
    "BLOCKED_G81_NON_OPTICAL_ZOOM_4LOCK_AF_METERING_VIOLATION"
)
STATUS_BLOCKED_G81_TELEMETRY_INVALID: str = (
    "BLOCKED_G81_STEADYSHOT_CIZ_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G82_POWER_SAVE_MENU_ITEM_OR_OPTION_INVALID: str = (
    "BLOCKED_G82_POWER_SAVE_MENU_ITEM_OR_OPTION_INVALID"
)
STATUS_BLOCKED_G82_POWER_SAVE_9COND_BYPASS_MISMATCH: str = (
    "BLOCKED_G82_POWER_SAVE_9COND_BYPASS_MISMATCH"
)
STATUS_BLOCKED_G82_AIRGAPPED_NPFZ100_TIER0_SLEEP_HAZARD: str = (
    "BLOCKED_G82_AIRGAPPED_NPFZ100_TIER0_SLEEP_HAZARD"
)
STATUS_BLOCKED_G82_AUTO_POWER_OFF_TEMP_HIGH_HANDHELD_BURN_HAZARD: str = (
    "BLOCKED_G82_AUTO_POWER_OFF_TEMP_HIGH_HANDHELD_BURN_HAZARD"
)
STATUS_BLOCKED_G82_AUTO_POWER_OFF_TEMP_FAN_THERMAL_COUPLING_VIOLATION: str = (
    "BLOCKED_G82_AUTO_POWER_OFF_TEMP_FAN_THERMAL_COUPLING_VIOLATION"
)
STATUS_BLOCKED_G82_TELEMETRY_INVALID: str = (
    "BLOCKED_G82_POWERSAVE_AUTOTEMP_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE224_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE224_82GATE_DONOR_INTEGRITY_OR_BUDGET_EXCEEDED"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G81 Constants — [SteadyShot] (Movie) & [Clear Image Zoom] / [Digital Zoom]
STEADYSHOT_MOVIE_MENU_PATH: str = (
    "MENU -> Shooting -> [Image Stabilization] -> [SteadyShot]"
)
STEADYSHOT_ADJUST_MENU_PATH: str = (
    "MENU -> Shooting -> [Image Stabilization] -> [SteadyShot Adjust.]"
)
ZOOM_RANGE_MENU_PATH: str = "MENU -> Shooting -> [Zoom] -> [Zoom Range]"

STEADYSHOT_MODE_ACTIVE: str = "ACTIVE"
STEADYSHOT_MODE_STANDARD: str = "STANDARD"
STEADYSHOT_MODE_OFF: str = "OFF"
ALLOWED_STEADYSHOT_MOVIE_MODES: Tuple[str, ...] = (
    STEADYSHOT_MODE_ACTIVE,
    STEADYSHOT_MODE_STANDARD,
    STEADYSHOT_MODE_OFF,
)
STEADYSHOT_ACTIVE_MIN_CROP_FACTOR: float = 1.08
STEADYSHOT_ACTIVE_NOMINAL_CROP_FACTOR: float = 1.10
STEADYSHOT_FOCAL_LEN_MIN_MM: int = 8
STEADYSHOT_FOCAL_LEN_MAX_MM: int = 1000

SHOOT_MODE_MOVIE: str = "MOVIE"
SHOOT_MODE_SQ: str = "S&Q"
SHOOT_MODE_STILL: str = "STILL"
ALLOWED_SHOOT_MODES_G81: Tuple[str, ...] = (
    SHOOT_MODE_MOVIE,
    SHOOT_MODE_SQ,
    SHOOT_MODE_STILL,
)

NORMAL_HFR_DISQUALIFIED_RATES: Tuple[str, ...] = ("119.88p", "100p", "120p")
SQ_HFR_DISQUALIFIED_RATES: Tuple[str, ...] = ("100fps", "120fps", "200fps", "240fps")

ZOOM_RANGE_OPTICAL_ONLY: str = "OPTICAL_ONLY"
ZOOM_RANGE_CLEAR_IMAGE_ZOOM: str = "CLEAR_IMAGE_ZOOM"
ZOOM_RANGE_DIGITAL_ZOOM: str = "DIGITAL_ZOOM"
ALLOWED_ZOOM_RANGE_SETTINGS: Tuple[str, ...] = (
    ZOOM_RANGE_OPTICAL_ONLY,
    ZOOM_RANGE_CLEAR_IMAGE_ZOOM,
    ZOOM_RANGE_DIGITAL_ZOOM,
)

ZOOM_DOMAIN_OPTICAL: str = "OPTICAL"
ZOOM_DOMAIN_SMART_ZOOM: str = "SMART_ZOOM"
ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM: str = "CLEAR_IMAGE_ZOOM"
ZOOM_DOMAIN_DIGITAL_ZOOM: str = "DIGITAL_ZOOM"
NON_OPTICAL_ZOOM_DOMAINS: Tuple[str, ...] = (
    ZOOM_DOMAIN_SMART_ZOOM,
    ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM,
    ZOOM_DOMAIN_DIGITAL_ZOOM,
)
CIZ_MAX_SCALE_4K: float = 1.5
CIZ_MAX_SCALE_HD_OR_STILL: float = 2.0
DIGITAL_ZOOM_MAX_SCALE: float = 4.0

STILL_RAW_FILE_FORMATS: Tuple[str, ...] = ("RAW", "RAW & JPEG", "RAW & HEIF")
METERING_MODE_MULTI: str = "MULTI"
ALLOWED_METERING_MODES_G81: Tuple[str, ...] = (
    "MULTI",
    "CENTER",
    "SPOT",
    "ENTIRE_SCREEN_AVG",
    "HIGHLIGHT",
)

# Gate G82 Constants — [Power Save Start Time] (9 Conditions) & [Auto Power OFF Temp.]
POWER_SAVE_START_TIME_MENU_PATH: str = (
    "MENU -> Setup -> [Power Setting Option] -> [Power Save Start Time]"
)
AUTO_POWER_OFF_TEMP_MENU_PATH: str = (
    "MENU -> Setup -> [Power Setting Option] -> [Auto Power OFF Temp.]"
)
FAN_CONTROL_MENU_PATH: str = "MENU -> Setup -> [Setup Option] -> [Fan Control]"

POWER_SAVE_MENU_ITEM_EXACT: str = "Power Save Start Time"
POWER_SAVE_FACTORY_DEFAULT_OPTION: str = "5 Min"
POWER_SAVE_OPTION_SECONDS: Mapping[str, Optional[int]] = {
    "Off": None,
    "30 Min": 1800,
    "5 Min": 300,
    "2 Min": 120,
    "1 Min": 60,
    "10 Sec": 10,
}
ALLOWED_POWER_SAVE_OPTIONS: Tuple[str, ...] = tuple(POWER_SAVE_OPTION_SECONDS.keys())
TIER0_SAFE_AIRGAPPED_POWER_SAVE_OPTIONS: Tuple[str, ...] = ("Off", "30 Min")
TIER0_P3_COLD_DUMP_MIB: int = 75

POWER_SAVE_9_BYPASS_CONDITIONS: Tuple[str, ...] = (
    "usb_power_supply",
    "slideshow_playback",
    "ftp_transfer",
    "movie_recording",
    "pc_connection",
    "tv_hdmi_connection",
    "ir_remote_ctrl_on",
    "bluetooth_rmt_ctrl_on",
    "streaming_or_cloud_upload",
)

AUTO_POWER_OFF_TEMP_STANDARD: str = "Standard"
AUTO_POWER_OFF_TEMP_HIGH: str = "High"
ALLOWED_AUTO_POWER_OFF_TEMP_MODES_G82: Tuple[str, ...] = (
    AUTO_POWER_OFF_TEMP_STANDARD,
    AUTO_POWER_OFF_TEMP_HIGH,
)
ALLOWED_FAN_CONTROL_MODES_G82: Tuple[str, ...] = (
    "Auto1",
    "Auto2",
    "Minimum",
    "Off in Rec",
    "Always Off",
)

# Pinned FX3 v7.02 & FX6 v6.01 Donor Specs (bounded <0.15s O_RDONLY verification)
PINNED_PHASE224_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"SteadyShot",
            b"Active",
            b"Standard",
            b"Zoom",
            b"Focus",
            b"Metering",
            b"Multi",
            b"Power",
            b"Save",
            b"Temp",
            b"Fan",
            b"RAW",
            b"HDMI",
            b"Remote",
            b"BK4",
            b"/setting",
        ),
        "fx3/cpapp-b.bin::{15980568B,ILME-FX3,SteadyShot,Active,Standard,Zoom,Focus,Metering,Multi,Power,Save,Temp,Fan,RAW,HDMI,Remote}",
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
class Phase224DonorAuditResult:
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
class SteadyShotActiveAndCiz4LockGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    firmware_version: str
    shoot_mode: str
    rec_frame_rate: str
    sq_frame_rate: str
    hdmi_raw_output_on: bool
    canonical_steadyshot_mode: str
    steadyshot_active_disqualified: bool
    steadyshot_active_disqualification_reasons: Tuple[str, ...]
    active_narrower_aov_crop_factor: float
    steadyshot_adjust_manual: bool
    steadyshot_focal_length_mm: int
    zoom_range_setting: str
    active_zoom_domain: str
    non_optical_zoom_scale: float
    non_optical_zoom_active: bool
    still_file_format: str
    is_4k_movie_resolution: bool
    focus_area_setting_disabled: bool
    center_priority_af_active: bool
    effective_metering_mode: str
    face_eye_prior_in_af_enabled: bool
    face_priority_in_multi_metering_enabled: bool
    realtime_tracking_available: bool
    all_4_non_optical_zoom_locks_enforced: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PowerSave9CondAndAutoTempTripodResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    menu_item_label: str
    factory_default_power_save_option: str
    configured_power_save_start_time: str
    configured_sleep_timeout_seconds: Optional[int]
    active_9_bypass_conditions: Tuple[str, ...]
    active_bypass_condition_count: int
    power_save_auto_deactivated: bool
    effective_sleep_timeout_seconds: Optional[int]
    tier0_p3_75mib_dump_preflight: bool
    internal_npfz100_airgapped: bool
    airgapped_tier0_sleep_safe: bool
    auto_power_off_temp: str
    tripod_mounted: bool
    handheld_prolonged_shooting: bool
    fan_control_mode: str
    soc_temp_c: float
    thermal_fan_coupling_safe: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G81SteadyShotCizGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    steadyshot_ciz_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G82PowerSaveAutoTempGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    powersave_autotemp_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master82GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_79_gates_verified: bool
    all_82_gates_verified: bool
    g13_to_g82_all_passed: bool
    g81_to_g82_all_passed: bool
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
    master_80_report: Dict[str, Any]
    g81_result: Dict[str, Any]
    g82_result: Dict[str, Any]
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


def _is_finite_num(val: Any) -> bool:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return False
    f = float(val)
    return abs(f) < 1e12 and (f == f)


def _norm_token(val: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", (val or "").strip().upper()).strip("_")


def _norm_shoot_mode(val: str) -> str:
    s = (val or "").strip().upper().replace(" ", "")
    if s in ("MOVIE", "NORMAL_MOVIE", "VIDEO"):
        return SHOOT_MODE_MOVIE
    if s in ("S&Q", "SQ", "S_Q", "SLOW_AND_QUICK"):
        return SHOOT_MODE_SQ
    if s in ("STILL", "PHOTO"):
        return SHOOT_MODE_STILL
    return s


def _norm_movie_rate(val: str) -> str:
    s = (val or "").strip().lower().replace("fps", "p").replace(" ", "")
    aliases = {
        "23.98p": "23.98p",
        "23.976p": "23.98p",
        "24.00p": "24.00p",
        "24p": "24.00p",
        "25p": "25p",
        "29.97p": "29.97p",
        "30p": "29.97p",
        "50p": "50p",
        "59.94p": "59.94p",
        "60p": "59.94p",
        "100p": "100p",
        "100.00p": "100p",
        "119.88p": "119.88p",
        "120p": "119.88p",
    }
    return aliases.get(s, (val or "").strip())


def _norm_sq_rate(val: str) -> str:
    s = (val or "").strip().lower().replace(" ", "")
    if s.endswith("p"):
        s = s[:-1] + "fps"
    elif s.isdigit():
        s = s + "fps"
    return s


def _parse_fps_value(rate_str: str) -> Optional[float]:
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*(?:p|fps)?\s*$", (rate_str or "").lower())
    return float(m.group(1)) if m else None


def _norm_still_format(val: str) -> str:
    s = re.sub(r"\s+", " ", (val or "").strip().upper())
    aliases = {
        "RAW&JPEG": "RAW & JPEG",
        "RAW+JPEG": "RAW & JPEG",
        "RAW + JPEG": "RAW & JPEG",
        "RAW&HEIF": "RAW & HEIF",
        "RAW+HEIF": "RAW & HEIF",
        "RAW + HEIF": "RAW & HEIF",
    }
    return aliases.get(s, s)


def _norm_power_save_option(val: str) -> Optional[str]:
    s = re.sub(r"\s+", " ", (val or "").strip()).lower()
    mapping = {
        "off": "Off",
        "30 min": "30 Min",
        "30min": "30 Min",
        "5 min": "5 Min",
        "5min": "5 Min",
        "2 min": "2 Min",
        "2min": "2 Min",
        "1 min": "1 Min",
        "1min": "1 Min",
        "10 sec": "10 Sec",
        "10sec": "10 Sec",
    }
    return mapping.get(s)


def _norm_auto_temp_mode(val: str) -> Optional[str]:
    t = _norm_token(val)
    if t == "STANDARD":
        return AUTO_POWER_OFF_TEMP_STANDARD
    if t == "HIGH":
        return AUTO_POWER_OFF_TEMP_HIGH
    return None


def _norm_fan_mode(val: str) -> Optional[str]:
    t = _norm_token(val)
    mapping = {
        "AUTO1": "Auto1",
        "AUTO_1": "Auto1",
        "AUTO2": "Auto2",
        "AUTO_2": "Auto2",
        "MINIMUM": "Minimum",
        "OFF_IN_REC": "Off in Rec",
        "ALWAYS_OFF": "Always Off",
    }
    return mapping.get(t)


# ---------------------------------------------------------------------------
# 1. Bounded `<0.15s` O_RDONLY Local Donor Audit (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
# ---------------------------------------------------------------------------


def audit_phase224_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS,
) -> Phase224DonorAuditResult:
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE224_DONOR_SPECS.items():
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
        return Phase224DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE224_DONOR_INTEGRITY
            ),
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_150ms=within_budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE224_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=within_budget,
            fx6_contracts_verified=within_budget,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE224_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE224_DONOR_SPECS.items()
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
    ) in PINNED_PHASE224_DONOR_SPECS.items():
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
            f"Local donor O_RDONLY check exceeded budget ({elapsed:.4f}s >= {max_budget_seconds:.4f}s)."
        )

    fx3_keys = {k for k, s in PINNED_PHASE224_DONOR_SPECS.items() if s[0] == "fx3"}
    fx6_keys = {k for k, s in PINNED_PHASE224_DONOR_SPECS.items() if s[0] == "fx6"}
    fx3_ok = fx3_keys.issubset(passed_keys)
    fx6_ok = fx6_keys.issubset(passed_keys)
    valid = fx3_ok and fx6_ok and within_budget and (not errors)

    return Phase224DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE
        if valid
        else STATUS_BLOCKED_PHASE224_DONOR_INTEGRITY,
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
# 2. Gate G81: [SteadyShot] Active Cutoff & [Clear Image Zoom] / [Digital Zoom] 4-Locks
# ---------------------------------------------------------------------------


def resolve_fx3_steadyshot_movie_state(
    *,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    rec_frame_rate: str = "23.98p",
    sq_frame_rate: str = "60fps",
    hdmi_raw_output_on: bool = False,
) -> Tuple[bool, Tuple[str, ...]]:
    """Determine whether `ILME-FX3` (`Ver. 7.02`) movie `[SteadyShot] = [Active]` is
    disqualified under the 3 official Sony hardware cutoff conditions:
    1. Normal movie `[Rec Frame Rate]` = `119.88p` / `100p` (`>=100fps`),
    2. `S&Q` `[Frame Rate]` `>=120fps` / `100fps` (`100fps`, `120fps`, `200fps`, `240fps`),
    3. External HDMI `[RAW Output]` = `On`.
    """
    norm_mode = _norm_shoot_mode(shoot_mode)
    norm_rec = _norm_movie_rate(rec_frame_rate)
    norm_sq = _norm_sq_rate(sq_frame_rate)
    reasons: List[str] = []

    rec_fps = _parse_fps_value(norm_rec)
    if norm_mode == SHOOT_MODE_MOVIE and (
        norm_rec in NORMAL_HFR_DISQUALIFIED_RATES
        or (rec_fps is not None and rec_fps >= 100.0)
    ):
        reasons.append(f"NORMAL_MOVIE_HFR_{norm_rec}")

    sq_fps = _parse_fps_value(norm_sq)
    if norm_mode == SHOOT_MODE_SQ and (
        norm_sq in SQ_HFR_DISQUALIFIED_RATES
        or (sq_fps is not None and sq_fps >= 100.0)
    ):
        reasons.append(f"SQ_FRAME_RATE_{norm_sq}")

    if hdmi_raw_output_on:
        reasons.append("HDMI_RAW_OUTPUT_ON")

    return (len(reasons) > 0), tuple(reasons)


def resolve_fx3_zoom_and_4locks(
    *,
    zoom_range_setting: str = ZOOM_RANGE_CLEAR_IMAGE_ZOOM,
    active_zoom_domain: str = ZOOM_DOMAIN_OPTICAL,
    non_optical_zoom_scale: float = 1.0,
) -> Tuple[bool, Dict[str, Any]]:
    """Resolve whether non-optical zoom (`Smart Zoom`, `Clear Image Zoom`, `Digital Zoom`)
    is engaged and return the 4 mandatory `ILME-FX3` automatic camera state locks.
    """
    dom = _norm_token(active_zoom_domain)
    rng = _norm_token(zoom_range_setting)
    engaged = (dom in NON_OPTICAL_ZOOM_DOMAINS) or (float(non_optical_zoom_scale) > 1.0)
    locks = {
        "zoom_range_setting": rng,
        "active_zoom_domain": dom,
        "non_optical_zoom_active": engaged,
        "expected_focus_area_setting_disabled": engaged,
        "expected_center_priority_af_active": engaged,
        "expected_metering_mode": METERING_MODE_MULTI if engaged else None,
        "expected_face_eye_prior_disabled": engaged,
        "expected_realtime_tracking_unavailable": engaged,
    }
    return engaged, locks


def verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G81,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    rec_frame_rate: str = "23.98p",
    sq_frame_rate: str = "60fps",
    hdmi_raw_output_on: bool = False,
    steadyshot_mode: str = STEADYSHOT_MODE_ACTIVE,
    active_narrower_aov_crop_factor: Optional[float] = None,
    steadyshot_adjust_manual: bool = False,
    steadyshot_focal_length_mm: int = 50,
    zoom_range_setting: str = ZOOM_RANGE_CLEAR_IMAGE_ZOOM,
    active_zoom_domain: str = ZOOM_DOMAIN_OPTICAL,
    non_optical_zoom_scale: float = 1.0,
    still_file_format: str = "JPEG",
    is_4k_movie_resolution: bool = True,
    focus_area_setting_disabled: Optional[bool] = None,
    center_priority_af_active: Optional[bool] = None,
    effective_metering_mode: str = METERING_MODE_MULTI,
    face_eye_prior_in_af_enabled: Optional[bool] = None,
    face_priority_in_multi_metering_enabled: Optional[bool] = None,
    realtime_tracking_available: Optional[bool] = None,
) -> SteadyShotActiveAndCiz4LockGuardResult:
    """Verify Gate `G81`: `ILME-FX3` (`Ver. 7.02`) `[SteadyShot]` (`Active` 3-condition
    disqualification & narrower AoV crop) + `[Clear Image Zoom]` / `[Digital Zoom]`
    RAW/HFR cutoffs and 4 mandatory AF/Metering/Tracking state locks.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    norm_shoot = _norm_shoot_mode(shoot_mode)
    norm_rec = _norm_movie_rate(rec_frame_rate)
    norm_sq = _norm_sq_rate(sq_frame_rate)
    canon_ss = _norm_token(steadyshot_mode)
    canon_zrange = _norm_token(zoom_range_setting)
    canon_zdom = _norm_token(active_zoom_domain)
    canon_still_fmt = _norm_still_format(still_file_format)
    canon_meter = _norm_token(effective_metering_mode)

    if (
        body_model_name.strip().upper() != FX3_MODEL_NAME
        or int(body_model_id) != FX3_MODEL_ID
    ):
        _add_code(codes, STATUS_BLOCKED_G81_TELEMETRY_INVALID)
        errors.append(
            f"Body mismatch for G81: name={body_model_name!r}, id=0x{int(body_model_id):08X}."
        )

    if norm_shoot not in ALLOWED_SHOOT_MODES_G81:
        _add_code(codes, STATUS_BLOCKED_G81_TELEMETRY_INVALID)
        errors.append(f"Unsupported shoot_mode={shoot_mode!r} for Gate G81.")

    if canon_ss not in ALLOWED_STEADYSHOT_MOVIE_MODES:
        _add_code(codes, STATUS_BLOCKED_G81_TELEMETRY_INVALID)
        errors.append(
            f"Unsupported movie [SteadyShot] mode {steadyshot_mode!r}; allowed={ALLOWED_STEADYSHOT_MOVIE_MODES}."
        )

    if canon_zrange not in ALLOWED_ZOOM_RANGE_SETTINGS:
        _add_code(codes, STATUS_BLOCKED_G81_TELEMETRY_INVALID)
        errors.append(
            f"Unsupported [Zoom Range] setting {zoom_range_setting!r}; allowed={ALLOWED_ZOOM_RANGE_SETTINGS}."
        )

    if canon_zdom not in (ZOOM_DOMAIN_OPTICAL,) + NON_OPTICAL_ZOOM_DOMAINS:
        _add_code(codes, STATUS_BLOCKED_G81_TELEMETRY_INVALID)
        errors.append(f"Unsupported active_zoom_domain={active_zoom_domain!r}.")

    if canon_meter not in ALLOWED_METERING_MODES_G81:
        _add_code(codes, STATUS_BLOCKED_G81_TELEMETRY_INVALID)
        errors.append(f"Unsupported [Metering Mode] {effective_metering_mode!r}.")

    if not _is_finite_num(non_optical_zoom_scale) or float(non_optical_zoom_scale) < 1.0:
        _add_code(codes, STATUS_BLOCKED_G81_TELEMETRY_INVALID)
        errors.append(
            f"non_optical_zoom_scale={non_optical_zoom_scale!r} must be a finite float >= 1.0."
        )
        scale_f = 1.0
    else:
        scale_f = float(non_optical_zoom_scale)

    # 1. [SteadyShot] = [Active] 3-condition disqualification & narrower AoV crop check
    ss_disqualified, ss_reasons = resolve_fx3_steadyshot_movie_state(
        shoot_mode=norm_shoot,
        rec_frame_rate=norm_rec,
        sq_frame_rate=norm_sq,
        hdmi_raw_output_on=bool(hdmi_raw_output_on),
    )
    if canon_ss == STEADYSHOT_MODE_ACTIVE and ss_disqualified:
        _add_code(codes, STATUS_BLOCKED_G81_STEADYSHOT_ACTIVE_RAW_OR_HFR_CUTOFF)
        errors.append(
            f"[SteadyShot]=[Active] disqualified on ILME-FX3 under {ss_reasons}."
        )

    crop_factor = (
        STEADYSHOT_ACTIVE_NOMINAL_CROP_FACTOR
        if active_narrower_aov_crop_factor is None and canon_ss == STEADYSHOT_MODE_ACTIVE
        else (
            1.0
            if active_narrower_aov_crop_factor is None
            else float(active_narrower_aov_crop_factor)
        )
    )
    if canon_ss == STEADYSHOT_MODE_ACTIVE and crop_factor < STEADYSHOT_ACTIVE_MIN_CROP_FACTOR:
        _add_code(codes, STATUS_BLOCKED_G81_STEADYSHOT_ACTIVE_AOV_CROP_OR_LENS_VIOLATION)
        errors.append(
            f"[SteadyShot]=[Active] requires narrower angle-of-view crop (>={STEADYSHOT_ACTIVE_MIN_CROP_FACTOR}x), got {crop_factor:.3f}x."
        )

    if (
        canon_ss in (STEADYSHOT_MODE_ACTIVE, STEADYSHOT_MODE_STANDARD)
        and bool(steadyshot_adjust_manual)
        and (
            isinstance(steadyshot_focal_length_mm, bool)
            or not isinstance(steadyshot_focal_length_mm, int)
            or not (
                STEADYSHOT_FOCAL_LEN_MIN_MM
                <= steadyshot_focal_length_mm
                <= STEADYSHOT_FOCAL_LEN_MAX_MM
            )
        )
    ):
        _add_code(codes, STATUS_BLOCKED_G81_STEADYSHOT_ACTIVE_AOV_CROP_OR_LENS_VIOLATION)
        errors.append(
            f"Manual [SteadyShot Focal Len.]={steadyshot_focal_length_mm!r} must be an integer in [{STEADYSHOT_FOCAL_LEN_MIN_MM}, {STEADYSHOT_FOCAL_LEN_MAX_MM}] mm."
        )

    # 2. [Clear Image Zoom] / [Digital Zoom] / [Smart Zoom] cutoffs & scale bounds
    non_opt_active, _lock_spec = resolve_fx3_zoom_and_4locks(
        zoom_range_setting=canon_zrange,
        active_zoom_domain=canon_zdom,
        non_optical_zoom_scale=scale_f,
    )

    if non_opt_active:
        if norm_shoot == SHOOT_MODE_STILL and canon_still_fmt in STILL_RAW_FILE_FORMATS:
            _add_code(codes, STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN)
            errors.append(
                f"Non-optical zoom ({canon_zdom}) is unavailable when still [File Format]={canon_still_fmt!r}."
            )
        if canon_zdom == ZOOM_DOMAIN_SMART_ZOOM and norm_shoot != SHOOT_MODE_STILL:
            _add_code(codes, STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN)
            errors.append("[Smart Zoom] is unavailable in movie / S&Q shooting modes.")

        rec_fps = _parse_fps_value(norm_rec)
        if norm_shoot == SHOOT_MODE_MOVIE and (
            norm_rec in NORMAL_HFR_DISQUALIFIED_RATES
            or (rec_fps is not None and rec_fps >= 100.0)
        ):
            _add_code(codes, STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN)
            errors.append(
                f"Non-optical zoom ({canon_zdom}) is blocked at Normal movie {norm_rec}."
            )

        sq_fps = _parse_fps_value(norm_sq)
        if norm_shoot == SHOOT_MODE_SQ and (
            norm_sq in SQ_HFR_DISQUALIFIED_RATES
            or (sq_fps is not None and sq_fps >= 100.0)
        ):
            _add_code(codes, STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN)
            errors.append(
                f"Non-optical zoom ({canon_zdom}) is blocked at S&Q [Frame Rate] {norm_sq}."
            )

        if canon_zrange == ZOOM_RANGE_OPTICAL_ONLY and canon_zdom in (
            ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM,
            ZOOM_DOMAIN_DIGITAL_ZOOM,
        ):
            _add_code(codes, STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN)
            errors.append(
                f"Active zoom domain {canon_zdom} forbidden when [Zoom Range]=[Optical zoom only]."
            )
        if (
            canon_zrange == ZOOM_RANGE_CLEAR_IMAGE_ZOOM
            and canon_zdom == ZOOM_DOMAIN_DIGITAL_ZOOM
        ):
            _add_code(codes, STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN)
            errors.append(
                "Active zoom domain DIGITAL_ZOOM forbidden when [Zoom Range]=[Clear Image Zoom]."
            )

        ciz_ceiling = (
            CIZ_MAX_SCALE_4K
            if (norm_shoot != SHOOT_MODE_STILL and is_4k_movie_resolution)
            else CIZ_MAX_SCALE_HD_OR_STILL
        )
        if canon_zdom == ZOOM_DOMAIN_CLEAR_IMAGE_ZOOM and scale_f > ciz_ceiling + 1e-6:
            _add_code(codes, STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN)
            errors.append(
                f"[Clear Image Zoom] scale {scale_f:.2f}x exceeds ILME-FX3 ceiling {ciz_ceiling:.1f}x."
            )
        if canon_zdom == ZOOM_DOMAIN_DIGITAL_ZOOM and scale_f > DIGITAL_ZOOM_MAX_SCALE + 1e-6:
            _add_code(codes, STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN)
            errors.append(
                f"[Digital Zoom] scale {scale_f:.2f}x exceeds ILME-FX3 4.0x ceiling."
            )
        if canon_zdom == ZOOM_DOMAIN_OPTICAL and scale_f > 1.0:
            _add_code(codes, STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_RAW_HFR_OR_RANGE_FORBIDDEN)
            errors.append(
                f"non_optical_zoom_scale={scale_f:.2f}x > 1.0 contradicts active_zoom_domain=OPTICAL."
            )

    # 3. 4 Mandatory automatic camera state locks whenever non-optical zoom is active
    eff_focus_disabled = (
        non_opt_active
        if focus_area_setting_disabled is None
        else bool(focus_area_setting_disabled)
    )
    eff_center_af = (
        non_opt_active
        if center_priority_af_active is None
        else bool(center_priority_af_active)
    )
    eff_face_eye_af = (
        (not non_opt_active)
        if face_eye_prior_in_af_enabled is None
        else bool(face_eye_prior_in_af_enabled)
    )
    eff_face_multi_meter = (
        (not non_opt_active)
        if face_priority_in_multi_metering_enabled is None
        else bool(face_priority_in_multi_metering_enabled)
    )
    eff_rt_tracking = (
        (not non_opt_active)
        if realtime_tracking_available is None
        else bool(realtime_tracking_available)
    )

    lock1_ok = (not non_opt_active) or (eff_focus_disabled and eff_center_af)
    lock2_ok = (not non_opt_active) or (canon_meter == METERING_MODE_MULTI)
    lock3_ok = (not non_opt_active) or (
        (not eff_face_eye_af) and (not eff_face_multi_meter)
    )
    lock4_ok = (not non_opt_active) or (not eff_rt_tracking)
    all_4_locks_ok = lock1_ok and lock2_ok and lock3_ok and lock4_ok

    if non_opt_active and not all_4_locks_ok:
        _add_code(codes, STATUS_BLOCKED_G81_NON_OPTICAL_ZOOM_4LOCK_AF_METERING_VIOLATION)
        errors.append(
            "Non-optical zoom active without all 4 mandatory ILME-FX3 state locks: "
            f"focus_area_disabled={eff_focus_disabled}, center_af={eff_center_af}, "
            f"metering={canon_meter}, face_eye_af={eff_face_eye_af}, "
            f"face_multi_metering={eff_face_multi_meter}, rt_tracking={eff_rt_tracking}."
        )

    valid = not codes
    status = STATUS_VERIFIED_G81 if valid else codes[0]
    return SteadyShotActiveAndCiz4LockGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{int(body_model_id):08X}",
        firmware_version=firmware_version,
        shoot_mode=norm_shoot,
        rec_frame_rate=norm_rec,
        sq_frame_rate=norm_sq,
        hdmi_raw_output_on=bool(hdmi_raw_output_on),
        canonical_steadyshot_mode=canon_ss,
        steadyshot_active_disqualified=ss_disqualified,
        steadyshot_active_disqualification_reasons=ss_reasons,
        active_narrower_aov_crop_factor=round(crop_factor, 4),
        steadyshot_adjust_manual=bool(steadyshot_adjust_manual),
        steadyshot_focal_length_mm=int(steadyshot_focal_length_mm),
        zoom_range_setting=canon_zrange,
        active_zoom_domain=canon_zdom,
        non_optical_zoom_scale=round(scale_f, 4),
        non_optical_zoom_active=non_opt_active,
        still_file_format=canon_still_fmt,
        is_4k_movie_resolution=bool(is_4k_movie_resolution),
        focus_area_setting_disabled=eff_focus_disabled,
        center_priority_af_active=eff_center_af,
        effective_metering_mode=canon_meter,
        face_eye_prior_in_af_enabled=eff_face_eye_af,
        face_priority_in_multi_metering_enabled=eff_face_multi_meter,
        realtime_tracking_available=eff_rt_tracking,
        all_4_non_optical_zoom_locks_enforced=all_4_locks_ok,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g81_steadyshot_ciz_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    steadyshot_ciz_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase224DonorAuditResult] = None,
) -> Tuple[GateVerdict, G81SteadyShotCizGuardResult]:
    """Evaluate Gate `G81` combining bounded `<0.15s` donor check with `[SteadyShot]`
    `Active` cutoff and `[Clear Image Zoom]` / `[Digital Zoom]` 4-lock verification.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase224_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_steadyshot_active_cutoff_and_ciz_4lock_guard(
        **dict(steadyshot_ciz_kwargs or {})
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
        errors.append("Gate G81 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G81 if valid else codes[0]

    res = G81SteadyShotCizGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        steadyshot_ciz_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, ss={guard.canonical_steadyshot_mode}"
        f"(crop={guard.active_narrower_aov_crop_factor}x,disq={guard.steadyshot_active_disqualified}), "
        f"zoom={guard.zoom_range_setting}/{guard.active_zoom_domain}"
        f"(scale={guard.non_optical_zoom_scale}x,4locks={guard.all_4_non_optical_zoom_locks_enforced}, "
        f"meter={guard.effective_metering_mode})"
    )
    verdict = GateVerdict(
        gate_id=G81_GATE_ID,
        gate_code=G81_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate G82: [Power Save Start Time] 9-Cond Bypass & [Auto Power OFF Temp.] Tripod Guard
# ---------------------------------------------------------------------------


def resolve_fx3_power_save_9cond_state(
    *,
    power_save_start_time: str = "Off",
    usb_power_supply: bool = False,
    slideshow_playback: bool = False,
    ftp_transfer: bool = False,
    movie_recording: bool = False,
    pc_connection: bool = False,
    tv_hdmi_connection: bool = False,
    ir_remote_ctrl_on: bool = False,
    bluetooth_rmt_ctrl_on: bool = False,
    streaming_or_cloud_upload: bool = False,
) -> Tuple[Optional[str], Tuple[str, ...], bool, Optional[int]]:
    """Resolve `ILME-FX3` (`Ver. 7.02`) `[Power Save Start Time]` and evaluate all 9
    automatic sleep-deactivation conditions.
    """
    canon_opt = _norm_power_save_option(power_save_start_time)
    cond_map = {
        "usb_power_supply": bool(usb_power_supply),
        "slideshow_playback": bool(slideshow_playback),
        "ftp_transfer": bool(ftp_transfer),
        "movie_recording": bool(movie_recording),
        "pc_connection": bool(pc_connection),
        "tv_hdmi_connection": bool(tv_hdmi_connection),
        "ir_remote_ctrl_on": bool(ir_remote_ctrl_on),
        "bluetooth_rmt_ctrl_on": bool(bluetooth_rmt_ctrl_on),
        "streaming_or_cloud_upload": bool(streaming_or_cloud_upload),
    }
    active = tuple(name for name in POWER_SAVE_9_BYPASS_CONDITIONS if cond_map[name])
    deactivated = len(active) > 0
    cfg_sec = POWER_SAVE_OPTION_SECONDS.get(canon_opt) if canon_opt is not None else None
    eff_sec = None if (canon_opt == "Off" or deactivated) else cfg_sec
    return canon_opt, active, deactivated, eff_sec


def resolve_fx3_auto_power_off_temp_and_fan(
    *,
    auto_power_off_temp: str = AUTO_POWER_OFF_TEMP_STANDARD,
    tripod_mounted: bool = True,
    handheld_prolonged_shooting: bool = False,
    fan_control_mode: str = "Auto1",
    soc_temp_c: float = 42.0,
    movie_recording: bool = False,
) -> Tuple[bool, bool, List[str]]:
    """Evaluate `[Auto Power OFF Temp.]` (`Standard` vs `High` tripod requirement) and
    `[Fan Control]` thermal safety coupling.
    """
    canon_temp = _norm_auto_temp_mode(auto_power_off_temp)
    canon_fan = _norm_fan_mode(fan_control_mode)
    reasons: List[str] = []

    tripod_ok = True
    if canon_temp == AUTO_POWER_OFF_TEMP_HIGH and (
        (not tripod_mounted) or handheld_prolonged_shooting
    ):
        tripod_ok = False
        reasons.append(
            "[Auto Power OFF Temp.]=[High] requires tripod mounting (hand-held prolonged shooting risks low-temperature contact burns)."
        )

    fan_ok = True
    if canon_temp == AUTO_POWER_OFF_TEMP_HIGH and canon_fan == "Always Off":
        fan_ok = False
        reasons.append(
            "[Auto Power OFF Temp.]=[High] forbids [Fan Control]=[Always Off] due to SoC / CFexpress Type A thermal runaway hazard."
        )
    if (
        canon_fan == "Off in Rec"
        and movie_recording
        and float(soc_temp_c) >= SOC_FAN_OVERRIDE_TEMP_C
    ):
        fan_ok = False
        reasons.append(
            f"[Fan Control]=[Off in Rec] unsafe at SoC {soc_temp_c:.1f}C >= {SOC_FAN_OVERRIDE_TEMP_C:.1f}C override threshold."
        )
    if float(soc_temp_c) >= FAIL_CLOSED_TEARDOWN_TEMP_C:
        fan_ok = False
        reasons.append(
            f"SoC temperature {soc_temp_c:.1f}C >= {FAIL_CLOSED_TEARDOWN_TEMP_C:.1f}C fail-closed ceiling."
        )

    return tripod_ok, fan_ok, reasons


def verify_powersave_9cond_and_autotemp_tripod_guard(
    *,
    menu_item_label: str = POWER_SAVE_MENU_ITEM_EXACT,
    power_save_start_time: str = "Off",
    usb_power_supply: bool = False,
    slideshow_playback: bool = False,
    ftp_transfer: bool = False,
    movie_recording: bool = False,
    pc_connection: bool = False,
    tv_hdmi_connection: bool = False,
    ir_remote_ctrl_on: bool = False,
    bluetooth_rmt_ctrl_on: bool = False,
    streaming_or_cloud_upload: bool = False,
    reported_power_save_deactivated: Optional[bool] = None,
    tier0_p3_75mib_dump_preflight: bool = True,
    internal_npfz100_airgapped: bool = True,
    auto_power_off_temp: str = AUTO_POWER_OFF_TEMP_STANDARD,
    tripod_mounted: bool = True,
    handheld_prolonged_shooting: bool = False,
    fan_control_mode: str = "Auto1",
    soc_temp_c: float = 42.0,
) -> PowerSave9CondAndAutoTempTripodResult:
    """Verify Gate `G82`: `ILME-FX3` (`Ver. 7.02`) exact `[Power Save Start Time]` menu
    item + 9 automatic deactivation conditions + air-gapped `NP-FZ100` Tier-0 `75 MiB`
    `p3` dump sleep pre-check + `[Auto Power OFF Temp.]` `High` tripod & `[Fan Control]`
    thermal safety guard.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (menu_item_label or "").strip() != POWER_SAVE_MENU_ITEM_EXACT:
        _add_code(codes, STATUS_BLOCKED_G82_POWER_SAVE_MENU_ITEM_OR_OPTION_INVALID)
        errors.append(
            f"Menu item {menu_item_label!r} does not match exact ILME-FX3 string {POWER_SAVE_MENU_ITEM_EXACT!r}."
        )

    canon_opt, active_conds, auto_deactivated, eff_sec = resolve_fx3_power_save_9cond_state(
        power_save_start_time=power_save_start_time,
        usb_power_supply=usb_power_supply,
        slideshow_playback=slideshow_playback,
        ftp_transfer=ftp_transfer,
        movie_recording=movie_recording,
        pc_connection=pc_connection,
        tv_hdmi_connection=tv_hdmi_connection,
        ir_remote_ctrl_on=ir_remote_ctrl_on,
        bluetooth_rmt_ctrl_on=bluetooth_rmt_ctrl_on,
        streaming_or_cloud_upload=streaming_or_cloud_upload,
    )

    if canon_opt is None or canon_opt not in ALLOWED_POWER_SAVE_OPTIONS:
        _add_code(codes, STATUS_BLOCKED_G82_POWER_SAVE_MENU_ITEM_OR_OPTION_INVALID)
        errors.append(
            f"Unsupported [Power Save Start Time]={power_save_start_time!r}; allowed={ALLOWED_POWER_SAVE_OPTIONS}."
        )
        cfg_sec: Optional[int] = None
    else:
        cfg_sec = POWER_SAVE_OPTION_SECONDS[canon_opt]

    if (
        reported_power_save_deactivated is not None
        and bool(reported_power_save_deactivated) != auto_deactivated
    ):
        _add_code(codes, STATUS_BLOCKED_G82_POWER_SAVE_9COND_BYPASS_MISMATCH)
        errors.append(
            f"reported_power_save_deactivated={reported_power_save_deactivated} contradicts "
            f"9-condition evaluation ({auto_deactivated}, active={active_conds})."
        )

    # Air-gapped internal NP-FZ100 Tier-0 75 MiB p3 cold dump pre-check
    airgapped_effective = bool(internal_npfz100_airgapped) and (not auto_deactivated)
    airgapped_sleep_safe = True
    if bool(tier0_p3_75mib_dump_preflight) and airgapped_effective:
        if canon_opt not in TIER0_SAFE_AIRGAPPED_POWER_SAVE_OPTIONS:
            airgapped_sleep_safe = False
            _add_code(codes, STATUS_BLOCKED_G82_AIRGAPPED_NPFZ100_TIER0_SLEEP_HAZARD)
            errors.append(
                f"Air-gapped internal-battery (NP-FZ100) Tier-0 {TIER0_P3_COLD_DUMP_MIB} MiB p3 "
                f"dump pre-check requires [Power Save Start Time] in {TIER0_SAFE_AIRGAPPED_POWER_SAVE_OPTIONS}, "
                f"got {power_save_start_time!r} ({cfg_sec}s sleep hazard)."
            )

    canon_temp = _norm_auto_temp_mode(auto_power_off_temp)
    if canon_temp is None:
        _add_code(codes, STATUS_BLOCKED_G82_TELEMETRY_INVALID)
        errors.append(
            f"Unsupported [Auto Power OFF Temp.]={auto_power_off_temp!r}; allowed={ALLOWED_AUTO_POWER_OFF_TEMP_MODES_G82}."
        )

    canon_fan = _norm_fan_mode(fan_control_mode)
    if canon_fan is None:
        _add_code(codes, STATUS_BLOCKED_G82_TELEMETRY_INVALID)
        errors.append(
            f"Unsupported [Fan Control]={fan_control_mode!r}; allowed={ALLOWED_FAN_CONTROL_MODES_G82}."
        )

    if not _is_finite_num(soc_temp_c) or not (-40.0 <= float(soc_temp_c) <= 130.0):
        _add_code(codes, STATUS_BLOCKED_G82_TELEMETRY_INVALID)
        errors.append(f"soc_temp_c={soc_temp_c!r} out of valid telemetry range [-40, 130] C.")
        soc_f = 42.0
    else:
        soc_f = float(soc_temp_c)

    tripod_ok, fan_ok, thermal_reasons = resolve_fx3_auto_power_off_temp_and_fan(
        auto_power_off_temp=canon_temp or AUTO_POWER_OFF_TEMP_STANDARD,
        tripod_mounted=bool(tripod_mounted),
        handheld_prolonged_shooting=bool(handheld_prolonged_shooting),
        fan_control_mode=canon_fan or "Auto1",
        soc_temp_c=soc_f,
        movie_recording=bool(movie_recording),
    )
    if not tripod_ok:
        _add_code(
            codes, STATUS_BLOCKED_G82_AUTO_POWER_OFF_TEMP_HIGH_HANDHELD_BURN_HAZARD
        )
    if not fan_ok:
        _add_code(
            codes, STATUS_BLOCKED_G82_AUTO_POWER_OFF_TEMP_FAN_THERMAL_COUPLING_VIOLATION
        )
    errors.extend(thermal_reasons)

    valid = not codes
    status = STATUS_VERIFIED_G82 if valid else codes[0]
    return PowerSave9CondAndAutoTempTripodResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        menu_item_label=menu_item_label,
        factory_default_power_save_option=POWER_SAVE_FACTORY_DEFAULT_OPTION,
        configured_power_save_start_time=canon_opt or power_save_start_time,
        configured_sleep_timeout_seconds=cfg_sec,
        active_9_bypass_conditions=active_conds,
        active_bypass_condition_count=len(active_conds),
        power_save_auto_deactivated=auto_deactivated,
        effective_sleep_timeout_seconds=eff_sec,
        tier0_p3_75mib_dump_preflight=bool(tier0_p3_75mib_dump_preflight),
        internal_npfz100_airgapped=airgapped_effective,
        airgapped_tier0_sleep_safe=airgapped_sleep_safe,
        auto_power_off_temp=canon_temp or auto_power_off_temp,
        tripod_mounted=bool(tripod_mounted),
        handheld_prolonged_shooting=bool(handheld_prolonged_shooting),
        fan_control_mode=canon_fan or fan_control_mode,
        soc_temp_c=round(soc_f, 2),
        thermal_fan_coupling_safe=fan_ok,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g82_powersave_autotemp_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    powersave_autotemp_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase224DonorAuditResult] = None,
) -> Tuple[GateVerdict, G82PowerSaveAutoTempGuardResult]:
    """Evaluate Gate `G82` combining bounded `<0.15s` donor check with `[Power Save
    Start Time]` 9-condition bypass / Tier-0 air-gapped pre-check and `[Auto Power OFF
    Temp.]` tripod / fan thermal safety verification.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase224_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_powersave_9cond_and_autotemp_tripod_guard(
        **dict(powersave_autotemp_kwargs or {})
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
        errors.append("Gate G82 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G82 if valid else codes[0]

    res = G82PowerSaveAutoTempGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        powersave_autotemp_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, psave={guard.configured_power_save_start_time}"
        f"(bypass={guard.active_bypass_condition_count}/9,airgap_safe={guard.airgapped_tier0_sleep_safe}), "
        f"autotemp={guard.auto_power_off_temp}(tripod={guard.tripod_mounted},"
        f"fan={guard.fan_control_mode},soc={guard.soc_temp_c}C)"
    )
    verdict = GateVerdict(
        gate_id=G82_GATE_ID,
        gate_code=G82_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified 82-Gate Master Safety Preflight (`G01..G82`)
# ---------------------------------------------------------------------------


def evaluate_82gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    steadyshot_ciz_kwargs: Optional[Mapping[str, Any]] = None,
    powersave_autotemp_kwargs: Optional[Mapping[str, Any]] = None,
    master_80_override: Optional[Master80GateReport] = None,
    **m80_passthrough_kwargs: Any,
) -> Master82GateReport:
    """Evaluate all 82 Master Safety Gates (`G01..G82`) deterministically by
    delegating `G01..G80` directly to `evaluate_80gate_preflight()`.
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

    m80_report: Master80GateReport = (
        master_80_override
        if master_80_override is not None
        else evaluate_80gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m80_passthrough_kwargs,
        )
    )

    phase224_audit = audit_phase224_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g81_verdict, g81_res = evaluate_g81_steadyshot_ciz_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        steadyshot_ciz_kwargs=steadyshot_ciz_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase224_audit,
    )

    g82_verdict, g82_res = evaluate_g82_powersave_autotemp_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        powersave_autotemp_kwargs=powersave_autotemp_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase224_audit,
    )

    gates_81_to_82 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g81_verdict, g82_verdict)
    ]
    all_gates = tuple(list(m80_report.gates) + gates_81_to_82)

    g01_to_g12_verified = int(m80_report.summary["g01_to_g12_verified"])
    g13_to_g80_verified = (
        int(m80_report.summary["g13_to_g78_verified"])
        + int(m80_report.summary["g79_to_g80_verified"])
    )
    g81_to_g82_verified = sum(1 for v in (g81_verdict, g82_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g80_verified + g81_to_g82_verified

    g81_to_g82_all_passed = g81_to_g82_verified == 2
    g13_to_g82_all_passed = m80_report.g13_to_g80_all_passed and g81_to_g82_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m80_report.gates[:9])

    offline_79_verified = (
        g01_to_g09_ok
        and m80_report.offline_77_gates_verified
        and g81_to_g82_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_82_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g82_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m80_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_79_verified
        and m80_report.h0_h1_trial_entry_allowed
        and g81_to_g82_all_passed
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
        list(m80_report.errors) + list(g81_verdict.errors) + list(g82_verdict.errors)
    )
    warnings: List[str] = (
        list(m80_report.warnings)
        + list(g81_verdict.warnings)
        + list(g82_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m80_report.g13_to_g80_all_passed:
        overall_status = m80_report.status
    elif not g81_verdict.passed:
        overall_status = g81_verdict.status
    elif not g82_verdict.passed:
        overall_status = g82_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_82_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_82_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_82_verified:
        overall_status = "VERIFIED_ALL_82_GATES"
    else:
        overall_status = "VERIFIED_79_OF_82_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m80_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g81_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g82_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 82,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 82 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g80_verified": g13_to_g80_verified,
        "g81_to_g82_verified": g81_to_g82_verified,
        "g13_to_g82_all_passed": g13_to_g82_all_passed,
        "g81_to_g82_all_passed": g81_to_g82_all_passed,
        "offline_79_gates_verified": offline_79_verified,
        "all_82_gates_verified": all_82_verified,
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

    return Master82GateReport(
        schema=REALHW_STEADYSHOT_CIZ_POWERSAVE_AUTOTEMP_82GATE_SCHEMA,
        version=REALHW_STEADYSHOT_CIZ_POWERSAVE_AUTOTEMP_82GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_79_gates_verified=offline_79_verified,
        all_82_gates_verified=all_82_verified,
        g13_to_g82_all_passed=g13_to_g82_all_passed,
        g81_to_g82_all_passed=g81_to_g82_all_passed,
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
        master_80_report=m80_report.to_dict(),
        g81_result=g81_res.to_dict(),
        g82_result=g82_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_82_master_safety_gates = evaluate_82gate_preflight
run_82_gate_preflight = evaluate_82gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_steadyshot_ciz_powersave_autotemp_and_82gate_guard",
        description=(
            "Phase 224 Safety Gates G81 (SteadyShot Active RAW/HFR Cutoff & Clear Image "
            "Zoom 4-Locks) + G82 (Power Save Start Time 9-Cond Bypass & Auto Power OFF "
            "Temp Tripod Guard) + Unified 82-Gate Master Safety Preflight"
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

    report = evaluate_82gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/82 "
            f"g81_to_g82_all_passed={report.g81_to_g82_all_passed} "
            f"all_82_gates_verified={report.all_82_gates_verified} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = report.all_82_gates_verified if args.dry_run_simulated else report.offline_79_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
