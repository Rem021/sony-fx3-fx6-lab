"""Phase 199 — Real-Hardware Main Track Part 22:
Gate G69 (`ILME-FX3` `Ver. 7.02` Exact 4-Mode `[Fan Control]` `Auto` / `Minimum` /
`Off in Rec` / `Always Off` — Rejecting Non-FX3 `Auto1`/`Auto2` Tokens, Modeling
`Off in Rec` `0%` Recording PWM + Thermal Emergency Override & `100% MAX PWM`
Standby Active Purge, and Blocking Pre-Backup / High-Load Rehearsal When
`[Fan Control] == Always Off` with `[Auto Power OFF Temp.] = Standard / High`
`CXD90057 / CXD90058` Protection),
Gate G70 (`FX6 Ver. 6.01` `<= 6.01` Legacy LUT Slot Format vs `Stock FX3 Ver. 7.00/7.02`
`7.00+` Optimized `p2:/setting` `User1..User16` LUT Binary Format Split Firewall
Requiring Volatile `/tmp/fx6_lut_overlay` Redirection with `H0 == H3` Invariance,
plus Independent `[Shutter Mode]` `Speed` vs `Angle` `Backup.bin` Slot Storage &
`5.6°..64F` Normal vs `5.6°..360°` `119.88p/100p` / `S&Q` Angle Bounds Immune to
`0.3EV / 0.5EV` Exposure Step),
and 70-Gate Master Safety Preflight (`G01..G70` / `verify-70-gates` / `run_70_gate_preflight`).

Composes `realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard` (`G01..G68`, keeping
`evaluate_58gate_preflight`, `evaluate_60gate_preflight`, `evaluate_62gate_preflight`,
`evaluate_64gate_preflight`, `evaluate_66gate_preflight`, `evaluate_68gate_preflight`,
`verify-58-gates`, `verify-60-gates`, `verify-62-gates`, `verify-64-gates`,
`verify-66-gates`, and `verify-68-gates` 100% intact) while hard-locking all physical
flash/write/transmit redlines:
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`
- `HUMAN_HARDWARE_ATTACH_TOKEN = False`
- `PHYSICAL_USB_PACKETS_EMITTED = 0`
- `RAW_FIRMWARE_BYTES_LEAKED = 0`
- `overall_ready_for_hardware_attach = False`
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
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union

from .exfat_media_integrity_guard import MediaSlotConfig
from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    GateVerdict,
    P12_WLAN_FATAL_GUARD_VMA,
)
from .realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    FX3A_MODEL_NAME,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
)
from .realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard import (
    Master68GateReport,
    evaluate_68gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_FAN_PWM_SHUTTER_ANGLE_LUT_SPLIT_70GATE_SCHEMA: str = (
    "fx3-realhw-fan-pwm-shutter-angle-lut-split-70gate-preflight-v1"
)
REALHW_FAN_PWM_SHUTTER_ANGLE_LUT_SPLIT_70GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

# Gate IDs & Canonical Codes for G69..G70
G69_GATE_ID: str = "G69_fx3_4mode_fan_pwm_and_prebackup_thermal_guard"
G69_GATE_CODE: str = "GATE_G69_FX3_4MODE_FAN_PWM_AND_PREBACKUP_THERMAL_GUARD"
GATE_G69_FX3_4MODE_FAN_PWM_AND_PREBACKUP_THERMAL_GUARD: str = G69_GATE_CODE
G69: str = G69_GATE_CODE

G70_GATE_ID: str = "G70_lut_601_702_binary_split_and_shutter_speed_angle_guard"
G70_GATE_CODE: str = "GATE_G70_LUT_601_702_BINARY_SPLIT_AND_SHUTTER_SPEED_ANGLE_GUARD"
GATE_G70_LUT_601_702_BINARY_SPLIT_AND_SHUTTER_SPEED_ANGLE_GUARD: str = G70_GATE_CODE
G70: str = G70_GATE_CODE

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G69: str = (
    "VERIFIED_FX3_4MODE_FAN_PWM_AND_PREBACKUP_THERMAL_GUARD"
)
STATUS_VERIFIED_G70: str = (
    "VERIFIED_LUT_601_702_BINARY_SPLIT_AND_SHUTTER_SPEED_ANGLE_GUARD"
)

# Gate G69 Violation Codes
STATUS_BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2: str = (
    "BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2"
)
STATUS_BLOCKED_G69_OFF_IN_REC_PWM_CONTRACT_VIOLATION: str = (
    "BLOCKED_G69_OFF_IN_REC_PWM_CONTRACT_VIOLATION"
)
STATUS_BLOCKED_G69_ALWAYS_OFF_PREBACKUP_BLOCKED: str = (
    "BLOCKED_G69_ALWAYS_OFF_PREBACKUP_BLOCKED"
)
STATUS_BLOCKED_G69_PREBACKUP_REQUIRES_FAN_AUTO: str = (
    "BLOCKED_G69_PREBACKUP_REQUIRES_FAN_AUTO"
)
STATUS_BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT: str = (
    "BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT"
)
STATUS_BLOCKED_G69_TELEMETRY_INVALID: str = (
    "BLOCKED_G69_FAN_PWM_THERMAL_TELEMETRY_INVALID"
)

# Gate G70 Violation Codes
STATUS_BLOCKED_G70_STAGEB_601_TO_702_P2_SETTING_LUT_WRITE: str = (
    "BLOCKED_G70_STAGEB_601_TO_702_P2_SETTING_LUT_WRITE"
)
STATUS_BLOCKED_G70_USER_LUT_SLOT_OR_FORMAT_INVALID: str = (
    "BLOCKED_G70_USER_LUT_SLOT_OR_FORMAT_INVALID"
)
STATUS_BLOCKED_G70_H0_H3_P2_SETTING_HASH_DRIFT: str = (
    "BLOCKED_G70_H0_H3_P2_SETTING_HASH_DRIFT"
)
STATUS_BLOCKED_G70_SHUTTER_SPEED_ANGLE_SLOT_COLLISION: str = (
    "BLOCKED_G70_SHUTTER_SPEED_ANGLE_SLOT_COLLISION"
)
STATUS_BLOCKED_G70_SHUTTER_ANGLE_OUT_OF_BOUNDS: str = (
    "BLOCKED_G70_SHUTTER_ANGLE_OUT_OF_BOUNDS"
)
STATUS_BLOCKED_G70_TELEMETRY_INVALID: str = (
    "BLOCKED_G70_LUT_SPLIT_SHUTTER_ANGLE_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE199_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE199_70GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G69 Constants — ILME-FX3 (Ver. 7.02) Exact 4-Mode [Fan Control] & Thermal Guard
FX3_FAN_CONTROL_MENU_PATH: str = (
    "MENU -> Setup -> [Setup Option] -> [Fan Control]"
)
ALLOWED_G69_BODY_MODELS: Tuple[str, ...] = (FX3_MODEL_NAME, FX3A_MODEL_NAME)
FX3_FAN_MIN_FW_VERSION: str = "6.00"
FX3_DEFAULT_FW_VERSION_G69: str = "7.02"

FX3_FAN_MODE_AUTO: str = "AUTO"
FX3_FAN_MODE_MINIMUM: str = "MINIMUM"
FX3_FAN_MODE_OFF_IN_REC: str = "OFF_IN_REC"
FX3_FAN_MODE_ALWAYS_OFF: str = "ALWAYS_OFF"

FX3_EXACT_4_FAN_MODES: Tuple[str, ...] = (
    FX3_FAN_MODE_AUTO,
    FX3_FAN_MODE_MINIMUM,
    FX3_FAN_MODE_OFF_IN_REC,
    FX3_FAN_MODE_ALWAYS_OFF,
)
FX3_EXACT_4_FAN_MENU_LABELS: Tuple[str, ...] = (
    "Auto",
    "Minimum",
    "Off in Rec",
    "Always Off",
)
REJECTED_NON_FX3_FAN_MODES: Tuple[str, ...] = (
    "AUTO1",
    "AUTO2",
    "AUTO_1",
    "AUTO_2",
    "LUMIX_AUTO1",
    "LUMIX_AUTO2",
    "STUDIO_AUTO1",
    "STUDIO_AUTO2",
    "NORMAL",
    "HIGH",
    "TURBO",
)

OFF_IN_REC_RECORDING_NORMAL_PWM_PCT: int = 0
OFF_IN_REC_STANDBY_MAX_PWM_PCT: int = 100
MINIMUM_MODE_QUIET_PWM_PCT: int = 25
AUTO_MODE_BASE_PWM_PCT: int = 35
OFF_IN_REC_EMERGENCY_OVERRIDE_TEMP_C: float = 78.0
PREBACKUP_SOC_MAX_START_TEMP_C: float = 62.0
AUTO_POWER_OFF_STANDARD_MAX_TEMP_C: float = 68.0
AUTO_POWER_OFF_HIGH_MAX_TEMP_C: float = 82.0
CXD90057_CXD90058_CRITICAL_SHUTDOWN_TEMP_C: float = 90.0
MIN_PLAUSIBLE_CAMERA_TEMP_C: float = -20.0
MAX_PLAUSIBLE_CAMERA_TEMP_C: float = 125.0

ALLOWED_AUTO_POWER_OFF_TEMP_MODES: Tuple[str, ...] = ("STANDARD", "HIGH")
CXD90057_PRIMARY_SOC: str = "CXD90057"
CXD90058_COMPANION_SOC: str = "CXD90058"
ALLOWED_PREBACKUP_CONTEXTS: Tuple[str, ...] = (
    "PRE_BACKUP_ADJUST_CONTROL_0X40_P3_75MIB",
    "HIGH_LOAD_DUAL_SYSTEM_REHEARSAL",
    "STAGE_B_REHEARSAL",
    "NORMAL_CAMERA_OPERATION",
)

# Gate G70 Constants — 6.01 vs 7.00/7.02 User LUT Binary Split & Shutter Speed/Angle
DONOR_FX6_FW_VERSION: str = "6.01"
HOST_STOCK_FX3_FW_VERSION: str = "7.02"
LUT_BINARY_SPLIT_BOUNDARY_FW: str = "7.00"
LUT_SLOT_FORMAT_LEGACY_LE_601: str = "LEGACY_V601_USER_LUT_BIN"
LUT_SLOT_FORMAT_OPTIMIZED_GE_700: str = "OPTIMIZED_V700_PLUS_USER_LUT_BIN"

USER_LUT_SLOT_MIN: int = 1
USER_LUT_SLOT_MAX: int = 16
VALID_USER_LUT_SLOTS: Tuple[str, ...] = tuple(
    f"User{i}" for i in range(USER_LUT_SLOT_MIN, USER_LUT_SLOT_MAX + 1)
)
REQUIRED_VOLATILE_LUT_OVERLAY_DIR: str = "/tmp/fx6_lut_overlay"
FORBIDDEN_PERSISTENT_LUT_SETTING_PATHS: Tuple[str, ...] = (
    "p2:/setting",
    "/setting",
    "/dev/nflasha2",
    "/dev/cnflasha2",
    "p2:",
)
DEFAULT_H0_P2_SETTING_SHA256: str = "b" * 64

MIN_SHUTTER_ANGLE_FW_VERSION: str = "6.00"
ALLOWED_SHUTTER_MODES: Tuple[str, ...] = ("SPEED", "ANGLE")
ALLOWED_SHOOTING_MODES_G70: Tuple[str, ...] = ("MOVIE", "S&Q", "BIG6_MOVIE")
SHUTTER_ANGLE_MIN_DEG: float = 5.6
SHUTTER_ANGLE_STD_MAX_DEG: float = 360.0
SHUTTER_ANGLE_MAX_FRAMES_NORMAL: int = 64
SHUTTER_ANGLE_NORMAL_MAX_EQUIV_DEG: float = 360.0 * SHUTTER_ANGLE_MAX_FRAMES_NORMAL
STANDARD_MOVIE_FRAME_RATES: Tuple[str, ...] = (
    "23.98P",
    "24.00P",
    "24P",
    "25P",
    "29.97P",
    "30P",
    "50P",
    "59.94P",
    "60P",
)
HIGH_FPS_ANGLE_CLAMP_RATES: Tuple[str, ...] = (
    "100P",
    "119.88P",
    "120P",
    "200P",
    "239.76P",
    "240P",
)
ALLOWED_EXPOSURE_STEPS_EV: Tuple[float, ...] = (0.3, 0.5)
DEFAULT_SHUTTER_SPEED_BK4_SLOT_ID: int = 0x01120024
DEFAULT_SHUTTER_ANGLE_BK4_SLOT_ID: int = 0x01120028

# Pinned FX3 v7.02 & FX6 v6.01 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE199_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"Fan",
            b"PWM",
            b"Temp",
            b"LUT",
            b"User",
            b"Angle",
            b"Speed",
            b"Shutter",
            b"/setting",
            b"Backup",
            b"cube",
        ),
        "fx3/cpapp-b.bin::{15980568B,ILME-FX3,Fan,PWM,Temp,LUT,User,Angle,Speed,Shutter,/setting,Backup,cube}",
    ),
    "fx3_libfan_so": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libfan.so",
        27_280,
        "c607fc8d3ea3b46ef1082e07c57ba484a910e6841772e638ab5909189942726c",
        (
            b"\x7fELF",
            b"fan",
            b"Backup",
        ),
        "fx3/libfan.so::{27280B,ELF,fan,Backup}",
    ),
    "fx3_bk4_bin": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (
            b"BK4",
            b"ILME-FX3",
            b"/setting",
        ),
        "fx3/FX3-CX95900_ALLLANG-Backup.bin::{2229740B,BK4,ILME-FX3,/setting}",
    ),
    "fx6_bk4_bin": (
        "fx6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (
            b"BK4",
            b"/setting",
        ),
        "fx6/CX95898_NTSC.bin::{2253333B,BK4,/setting}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase199DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
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
class Fx3FanPwmPreBackupThermalResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    body_model_name: str
    body_model_id: int
    body_model_id_hex: str
    firmware_version: str
    menu_path: str
    fan_mode: str
    canonical_fan_mode: str
    exact_4mode_enum_valid: bool
    recording_active: bool
    modeled_pwm_duty_pct: int
    observed_pwm_duty_pct: int
    off_in_rec_recording_normal_pwm_pct: int
    off_in_rec_standby_pwm_pct: int
    off_in_rec_emergency_override_enabled: bool
    emergency_thermal_override_active: bool
    off_in_rec_pwm_contract_valid: bool
    operation_context: str
    pre_backup_or_high_load: bool
    require_auto_for_prebackup: bool
    always_off_prebackup_blocked: bool
    auto_power_off_temp: str
    cxd90057_temp_c: float
    cxd90058_temp_c: float
    effective_thermal_ceiling_c: float
    prebackup_thermal_guard_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Lut601Vs702SplitAndShutterAngleResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    donor_stageb_fw_version: str
    host_stock_fx3_fw_version: str
    donor_lut_slot_format: str
    host_lut_slot_format: str
    generation_format_split_detected: bool
    lut_slot_name: str
    lut_slot_index: int
    stageb_lut_registry_path: str
    volatile_lut_overlay_redirected: bool
    stageb_p2_setting_lut_write_attempted: bool
    cross_generation_raw_slot_inject: bool
    p2_setting_lut_mutation_bytes: int
    p2_setting_mount_ro: bool
    h0_p2_setting_sha256: str
    h3_p2_setting_sha256: str
    h0_equals_h3_p2_setting: bool
    upgraded_from_le_601_stale_lut_unreregistered: bool
    lut_binary_split_firewall_valid: bool
    shutter_mode: str
    shooting_mode: str
    sq_mode_active: bool
    rec_frame_rate: str
    high_fps_or_sq_360_clamp_active: bool
    shutter_angle_deg: float
    shutter_frames_count: int
    shutter_speed_value: str
    shutter_speed_bk4_slot_id: int
    shutter_angle_bk4_slot_id: int
    shutter_speed_bk4_slot_hex: str
    shutter_angle_bk4_slot_hex: str
    speed_and_angle_slots_independent: bool
    mode_toggle_mutated_inactive_slot: bool
    exposure_step_ev: float
    exposure_step_altered_shutter_angle: bool
    shutter_speed_angle_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G69FanPwmThermalGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    fan_pwm_thermal_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G70LutSplitShutterAngleGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    lut_split_shutter_angle_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master70GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_67_gates_verified: bool
    all_70_gates_verified: bool
    g13_to_g70_all_passed: bool
    g69_to_g70_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_68_report: Dict[str, Any]
    g69_result: Dict[str, Any]
    g70_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            k: list(v) if isinstance(v, tuple) else v
            for k, v in self.__dict__.items()
        }


# ---------------------------------------------------------------------------
# Internal Helpers (Strict os.O_RDONLY, zero raw bytes printing)
# ---------------------------------------------------------------------------


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _read_file_o_rdonly(path: Path) -> bytes:
    """Strictly read a file via `os.open(..., os.O_RDONLY)` without leaking raw bytes."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        chunks: List[bytes] = []
        while True:
            chunk = os.read(fd, 1_048_576)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _is_non_negative_int(val: Any) -> bool:
    return isinstance(val, int) and (not isinstance(val, bool)) and val >= 0


def _is_finite_number(val: Any) -> bool:
    if isinstance(val, bool):
        return False
    if not isinstance(val, (int, float)):
        return False
    return abs(float(val)) < 1e12 and (float(val) == float(val))


def _normalize_int_value(val: Any) -> Optional[int]:
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        s = val.strip().lower()
        if not s:
            return None
        try:
            return int(s, 16) if s.startswith("0x") else int(s, 10)
        except ValueError:
            return None
    return None


def _norm_token(val: str) -> str:
    s = val.strip().upper()
    s = s.replace("&", "_AND_").replace(".", "_").replace("(", "_").replace(")", "")
    s = re.sub(r"[^A-Z0-9]+", "_", s).strip("_")
    return s


def _parse_version_tuple(ver_str: str) -> Optional[Tuple[int, ...]]:
    s = ver_str.strip()
    if s.lower().startswith("ver."):
        s = s[4:].strip()
    elif s.lower().startswith("v"):
        s = s[1:].strip()
    if not s or not re.fullmatch(r"\d+(?:\.\d+){1,3}", s):
        return None
    return tuple(int(part) for part in s.split("."))


def _version_gte(ver_str: str, floor_str: str) -> bool:
    v = _parse_version_tuple(ver_str)
    f = _parse_version_tuple(floor_str)
    if v is None or f is None:
        return False
    max_len = max(len(v), len(f))
    vp = v + (0,) * (max_len - len(v))
    fp = f + (0,) * (max_len - len(f))
    return vp >= fp


def _norm_fx3_fan_mode(fan_mode: str) -> str:
    t = _norm_token(fan_mode)
    if t in ("AUTO",):
        return FX3_FAN_MODE_AUTO
    if t in ("MINIMUM", "MIN"):
        return FX3_FAN_MODE_MINIMUM
    if t in ("OFF_IN_REC", "OFFINREC"):
        return FX3_FAN_MODE_OFF_IN_REC
    if t in ("ALWAYS_OFF", "ALWAYSOFF"):
        return FX3_FAN_MODE_ALWAYS_OFF
    return t


def _norm_auto_power_off_temp(mode: str) -> str:
    t = _norm_token(mode)
    if t in ("STANDARD", "STD"):
        return "STANDARD"
    if t in ("HIGH",):
        return "HIGH"
    return t


def _parse_user_lut_slot(slot: Union[str, int]) -> Optional[Tuple[str, int]]:
    if isinstance(slot, bool):
        return None
    if isinstance(slot, int):
        if USER_LUT_SLOT_MIN <= slot <= USER_LUT_SLOT_MAX:
            return (f"User{slot}", slot)
        return None
    if isinstance(slot, str):
        s = slot.strip()
        m = re.fullmatch(r"(?i)user\s*_?\s*(\d+)", s)
        if m:
            idx = int(m.group(1))
            if USER_LUT_SLOT_MIN <= idx <= USER_LUT_SLOT_MAX:
                return (f"User{idx}", idx)
            return None
        if s.isdigit():
            idx = int(s)
            if USER_LUT_SLOT_MIN <= idx <= USER_LUT_SLOT_MAX:
                return (f"User{idx}", idx)
    return None


def _is_high_fps_clamp_rate(rec_frame_rate: str) -> Optional[bool]:
    s = rec_frame_rate.strip().upper().replace("FPS", "P").replace(" ", "")
    if not s:
        return None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([PI])?", s)
    if not m:
        return None
    fps_val = float(m.group(1))
    if fps_val <= 0.0 or fps_val > 1000.0:
        return None
    if s in HIGH_FPS_ANGLE_CLAMP_RATES or fps_val >= 100.0:
        return True
    if s in STANDARD_MOVIE_FRAME_RATES or (1.0 <= fps_val < 100.0):
        return False
    return None


def _parse_exposure_step_ev(val: Union[float, int, str]) -> Optional[float]:
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        v = round(float(val), 2)
        return v if v in ALLOWED_EXPOSURE_STEPS_EV else None
    if isinstance(val, str):
        s = val.strip().upper().replace("EV", "").strip()
        if s in ("1/3", "0.33"):
            return 0.3
        if s in ("1/2",):
            return 0.5
        try:
            v = round(float(s), 2)
            return v if v in ALLOWED_EXPOSURE_STEPS_EV else None
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase199_donor_contracts(
    *_,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase199DonorAuditResult:
    """Inspect FX3 `7.02` `cpapp-b.bin`, `libfan.so`, `FX3-CX95900_ALLLANG-Backup.bin`,
    and FX6 `6.01` `CX95898_NTSC.bin` strictly via `os.open(..., os.O_RDONLY)` with
    deterministic clean-room fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files
    are absent.
    """
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)
    effective_work_root: Optional[Path] = (
        Path(work_root) if work_root is not None else paths.work_root
    )

    resolved: Dict[str, Path] = {}
    if effective_work_root is not None:
        for key, (
            _body,
            rel_path,
            _sz,
            _sha,
            _toks,
            _lbl,
        ) in PINNED_PHASE199_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase199DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE199_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE199_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE199_DONOR_SPECS.items()
            },
            errors=(),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []
    warnings: List[str] = []
    passed_keys: Set[str] = set()
    files_inspected = 0

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE199_DONOR_SPECS.items():
        blob = _read_file_o_rdonly(resolved[key])
        files_inspected += 1
        sha = hashlib.sha256(blob).hexdigest()
        shas[key] = sha
        sizes[key] = len(blob)

        missing_for_file = [m for m in marker_tuple if m not in blob]
        integrity_ok = len(blob) == exp_size and sha == exp_sha

        if not missing_for_file:
            checked.append(marker_label)
        else:
            missing.append(marker_label)
            errors.append(
                f"Donor {key} missing {len(missing_for_file)} required marker(s) for {marker_label}."
            )

        if not integrity_ok:
            errors.append(
                f"Donor {key} integrity mismatch: size={len(blob)} (expected {exp_size}), "
                f"sha256={sha} (expected {exp_sha})."
            )

        if not missing_for_file and integrity_ok:
            passed_keys.add(key)

    fx3_keys = {
        k for k, spec in PINNED_PHASE199_DONOR_SPECS.items() if spec[0] == "fx3"
    }
    fx6_keys = {
        k for k, spec in PINNED_PHASE199_DONOR_SPECS.items() if spec[0] == "fx6"
    }
    valid = len(errors) == 0 and len(missing) == 0
    return Phase199DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE199_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_keys.issubset(passed_keys) and valid,
        fx6_contracts_verified=fx6_keys.issubset(passed_keys) and valid,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Pure Helper Validators (G69 & G70)
# ---------------------------------------------------------------------------


def compute_fx3_702_fan_pwm_duty_pct(
    *,
    fan_mode: str = "Auto",
    recording_active: bool = False,
    cxd90057_temp_c: float = 44.0,
    cxd90058_temp_c: float = 42.0,
) -> int:
    """Compute physical `ILME-FX3` (`Ver. 7.02`) compact blower PWM duty (`0..100%`)
    across the exact 4 `[Fan Control]` modes (`Auto`, `Minimum`, `Off in Rec`, `Always Off`):
    - `Off in Rec`: `0%` during normal recording (`< 78.0°C`), `100%` emergency thermal
      override (`>= 78.0°C` in Rec), and `100% MAX PWM` active purge during standby.
    - `Always Off`: `0%` below emergency override (`< 78.0°C`), `100%` emergency safety override
      at `>= 78.0°C`.
    - `Minimum`: `25%` quiet floor (`< 78.0°C`), `100%` override at `>= 78.0°C`.
    - `Auto`: dynamic `35%..100%` thermal ramp tracking `max(CXD90057, CXD90058)`.
    """
    norm = _norm_fx3_fan_mode(fan_mode)
    peak_c = max(float(cxd90057_temp_c), float(cxd90058_temp_c))
    emergency = peak_c >= OFF_IN_REC_EMERGENCY_OVERRIDE_TEMP_C

    if norm == FX3_FAN_MODE_OFF_IN_REC:
        if recording_active:
            return 100 if emergency else OFF_IN_REC_RECORDING_NORMAL_PWM_PCT
        return OFF_IN_REC_STANDBY_MAX_PWM_PCT

    if norm == FX3_FAN_MODE_ALWAYS_OFF:
        return 100 if emergency else 0

    if norm == FX3_FAN_MODE_MINIMUM:
        if emergency:
            return 100
        if peak_c >= PREBACKUP_SOC_MAX_START_TEMP_C:
            return 50
        return MINIMUM_MODE_QUIET_PWM_PCT

    if norm == FX3_FAN_MODE_AUTO:
        if peak_c >= OFF_IN_REC_EMERGENCY_OVERRIDE_TEMP_C:
            return 100
        if peak_c <= 40.0:
            return AUTO_MODE_BASE_PWM_PCT
        frac = (peak_c - 40.0) / (OFF_IN_REC_EMERGENCY_OVERRIDE_TEMP_C - 40.0)
        return min(100, max(AUTO_MODE_BASE_PWM_PCT, int(round(35.0 + frac * 65.0))))

    raise ValueError(
        f"Unsupported non-FX3 fan mode {fan_mode!r}; expected exact 4-mode enum {FX3_EXACT_4_FAN_MENU_LABELS}."
    )


def validate_fx3_4mode_fan_enum_and_off_in_rec_pwm(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: Union[int, str] = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G69,
    fan_mode: str = "Auto",
    menu_options: Sequence[str] = FX3_EXACT_4_FAN_MENU_LABELS,
    recording_active: bool = False,
    cxd90057_temp_c: float = 44.0,
    cxd90058_temp_c: float = 42.0,
    observed_pwm_duty_pct: Optional[int] = None,
    off_in_rec_recording_normal_pwm_pct: int = OFF_IN_REC_RECORDING_NORMAL_PWM_PCT,
    off_in_rec_standby_pwm_pct: int = OFF_IN_REC_STANDBY_MAX_PWM_PCT,
    off_in_rec_emergency_override_enabled: bool = True,
) -> Tuple[bool, str, List[str]]:
    """Enforce exact 4-mode `ILME-FX3` `[Fan Control]` (`Auto`, `Minimum`, `Off in Rec`,
    `Always Off` — rejecting `Auto1`/`Auto2`) and `Off in Rec` PWM physics (`0%` in Rec
    with thermal emergency override, `100% MAX PWM` active purge in Standby).
    """
    errors: List[str] = []

    model_norm = body_model_name.strip().upper().replace("_", "-")
    b_id = _normalize_int_value(body_model_id)
    fw_ok = _version_gte(firmware_version, FX3_FAN_MIN_FW_VERSION)
    model_ok = model_norm in ALLOWED_G69_BODY_MODELS and (
        b_id == FX3_MODEL_ID
        if model_norm == FX3_MODEL_NAME
        else (b_id is not None and b_id >= 0)
    )
    if not (model_ok and fw_ok):
        errors.append(
            f"Unsupported body/firmware for FX3 4-mode fan guard: model={body_model_name!r}, "
            f"id={body_model_id!r}, fw={firmware_version!r} (>={FX3_FAN_MIN_FW_VERSION})."
        )
        return (False, STATUS_BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2, errors)

    norm_mode = _norm_fx3_fan_mode(fan_mode)
    norm_options = tuple(_norm_fx3_fan_mode(opt) for opt in menu_options)
    if (
        norm_mode in REJECTED_NON_FX3_FAN_MODES
        or norm_mode not in FX3_EXACT_4_FAN_MODES
        or any(opt in REJECTED_NON_FX3_FAN_MODES for opt in norm_options)
        or norm_options != FX3_EXACT_4_FAN_MODES
    ):
        errors.append(
            f"Non-FX3 [Fan Control] enum rejected: fan_mode={fan_mode!r}, "
            f"menu_options={list(menu_options)!r}; ILME-FX3 strictly exposes "
            f"{list(FX3_EXACT_4_FAN_MENU_LABELS)} (Auto1/Auto2 do NOT exist on FX3)."
        )
        return (False, STATUS_BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2, errors)

    expected_pwm = compute_fx3_702_fan_pwm_duty_pct(
        fan_mode=norm_mode,
        recording_active=recording_active,
        cxd90057_temp_c=cxd90057_temp_c,
        cxd90058_temp_c=cxd90058_temp_c,
    )
    actual_pwm = expected_pwm if observed_pwm_duty_pct is None else int(observed_pwm_duty_pct)
    peak_c = max(float(cxd90057_temp_c), float(cxd90058_temp_c))
    emergency = peak_c >= OFF_IN_REC_EMERGENCY_OVERRIDE_TEMP_C

    static_off_in_rec_ok = (
        int(off_in_rec_recording_normal_pwm_pct) == OFF_IN_REC_RECORDING_NORMAL_PWM_PCT
        and int(off_in_rec_standby_pwm_pct) == OFF_IN_REC_STANDBY_MAX_PWM_PCT
        and (off_in_rec_emergency_override_enabled is True)
        and (0 <= actual_pwm <= 100)
    )
    live_off_in_rec_ok = True
    if norm_mode == FX3_FAN_MODE_OFF_IN_REC:
        if recording_active:
            if emergency:
                live_off_in_rec_ok = actual_pwm >= 80
            else:
                live_off_in_rec_ok = actual_pwm == OFF_IN_REC_RECORDING_NORMAL_PWM_PCT
        else:
            live_off_in_rec_ok = actual_pwm == OFF_IN_REC_STANDBY_MAX_PWM_PCT
    elif emergency:
        live_off_in_rec_ok = actual_pwm >= 80

    if not (static_off_in_rec_ok and live_off_in_rec_ok):
        errors.append(
            f"FX3 Off in Rec PWM contract violation: fan_mode={fan_mode!r}, "
            f"recording={recording_active}, peak_temp={peak_c:.1f}C (emergency>={OFF_IN_REC_EMERGENCY_OVERRIDE_TEMP_C:.1f}C), "
            f"observed_pwm={actual_pwm}% (expected={expected_pwm}%), "
            f"rec_normal_pwm={off_in_rec_recording_normal_pwm_pct}% (expected 0%), "
            f"standby_pwm={off_in_rec_standby_pwm_pct}% (expected 100% MAX PWM), "
            f"emergency_override_enabled={off_in_rec_emergency_override_enabled}."
        )
        return (False, STATUS_BLOCKED_G69_OFF_IN_REC_PWM_CONTRACT_VIOLATION, errors)

    return (True, "", errors)


def validate_prebackup_fan_and_auto_power_off_temp(
    *,
    fan_mode: str = "Auto",
    operation_context: str = "PRE_BACKUP_ADJUST_CONTROL_0X40_P3_75MIB",
    pre_backup_or_high_load: bool = True,
    require_auto_for_prebackup: bool = True,
    auto_power_off_temp: str = "High",
    cxd90057_temp_c: float = 44.0,
    cxd90058_temp_c: float = 42.0,
) -> Tuple[bool, str, List[str]]:
    """Fail-close pre-backup (`AdjustControl 0x40` 75 MiB `p3`) or high-load dual-boot
    rehearsal when `[Fan Control] == Always Off` (requiring `Auto` when
    `require_auto_for_prebackup=True`) and enforce `[Auto Power OFF Temp.] = Standard / High`
    thermal ceilings protecting `CXD90057 / CXD90058`.
    """
    errors: List[str] = []

    norm_mode = _norm_fx3_fan_mode(fan_mode)
    ctx_norm = _norm_token(operation_context)
    apo_norm = _norm_auto_power_off_temp(auto_power_off_temp)

    if ctx_norm not in ALLOWED_PREBACKUP_CONTEXTS:
        errors.append(
            f"Unsupported thermal operation_context {operation_context!r}; "
            f"expected one of {ALLOWED_PREBACKUP_CONTEXTS}."
        )
        return (False, STATUS_BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT, errors)

    if apo_norm not in ALLOWED_AUTO_POWER_OFF_TEMP_MODES:
        errors.append(
            f"Invalid [Auto Power OFF Temp.] mode {auto_power_off_temp!r}; "
            f"expected 'Standard' or 'High'."
        )
        return (False, STATUS_BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT, errors)

    is_prebackup_ctx = pre_backup_or_high_load or (
        ctx_norm != "NORMAL_CAMERA_OPERATION"
    )

    if is_prebackup_ctx and norm_mode == FX3_FAN_MODE_ALWAYS_OFF:
        errors.append(
            f"Pre-backup / high-load rehearsal BLOCKED: [Fan Control] is 'Always Off' "
            f"during {ctx_norm}. Switch [Fan Control] to 'Auto' before AdjustControl (0x40) "
            f"75 MiB p3 cold backup or Stage-B rehearsal to prevent CXD90057/CXD90058 thermal cutoff."
        )
        return (False, STATUS_BLOCKED_G69_ALWAYS_OFF_PREBACKUP_BLOCKED, errors)

    if is_prebackup_ctx and require_auto_for_prebackup and norm_mode != FX3_FAN_MODE_AUTO:
        errors.append(
            f"Pre-backup / high-load rehearsal requires [Fan Control] = 'Auto' "
            f"(got {fan_mode!r} in {ctx_norm}) to guarantee sustained active cooling."
        )
        return (False, STATUS_BLOCKED_G69_PREBACKUP_REQUIRES_FAN_AUTO, errors)

    t57 = float(cxd90057_temp_c)
    t58 = float(cxd90058_temp_c)
    peak_c = max(t57, t58)
    op_ceiling = (
        AUTO_POWER_OFF_HIGH_MAX_TEMP_C
        if apo_norm == "HIGH"
        else AUTO_POWER_OFF_STANDARD_MAX_TEMP_C
    )
    effective_ceiling = (
        min(PREBACKUP_SOC_MAX_START_TEMP_C, op_ceiling)
        if is_prebackup_ctx
        else op_ceiling
    )

    plausible = (
        MIN_PLAUSIBLE_CAMERA_TEMP_C <= t57 <= MAX_PLAUSIBLE_CAMERA_TEMP_C
        and MIN_PLAUSIBLE_CAMERA_TEMP_C <= t58 <= MAX_PLAUSIBLE_CAMERA_TEMP_C
    )
    if (
        (not plausible)
        or peak_c >= CXD90057_CXD90058_CRITICAL_SHUTDOWN_TEMP_C
        or peak_c > effective_ceiling
    ):
        errors.append(
            f"CXD90057/CXD90058 thermal ceiling exceeded: CXD90057={t57:.1f}C, "
            f"CXD90058={t58:.1f}C, [Auto Power OFF Temp.]={auto_power_off_temp!r}, "
            f"effective_ceiling={effective_ceiling:.1f}C (critical={CXD90057_CXD90058_CRITICAL_SHUTDOWN_TEMP_C:.1f}C)."
        )
        return (False, STATUS_BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT, errors)

    return (True, "", errors)


def classify_user_lut_slot_binary_format(firmware_version: str) -> str:
    """Classify Sony `p2:/setting` `User1..User16` compiled LUT slot serialization
    generation: `<= 6.01` (`LEGACY_V601_USER_LUT_BIN`) vs `7.00+` (`OPTIMIZED_V700_PLUS_USER_LUT_BIN`).
    """
    parsed = _parse_version_tuple(firmware_version)
    if parsed is None:
        return "INVALID_FW_VERSION"
    if _version_gte(firmware_version, LUT_BINARY_SPLIT_BOUNDARY_FW):
        return LUT_SLOT_FORMAT_OPTIMIZED_GE_700
    return LUT_SLOT_FORMAT_LEGACY_LE_601


def validate_lut_601_vs_702_p2_setting_split_firewall(
    *,
    donor_stageb_fw_version: str = DONOR_FX6_FW_VERSION,
    host_stock_fx3_fw_version: str = HOST_STOCK_FX3_FW_VERSION,
    lut_slot: Union[str, int] = "User1",
    stageb_lut_registry_path: str = "/tmp/fx6_lut_overlay/User1.lutbin",
    stageb_p2_setting_lut_write_attempted: bool = False,
    cross_generation_raw_slot_inject: bool = False,
    p2_setting_lut_mutation_bytes: int = 0,
    p2_setting_mount_ro: bool = True,
    h0_p2_setting_sha256: str = DEFAULT_H0_P2_SETTING_SHA256,
    h3_p2_setting_sha256: str = DEFAULT_H0_P2_SETTING_SHA256,
    upgraded_from_le_601_stale_lut_unreregistered: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Block Stage-B `FX6 Ver. 6.01` (`<= 6.01` legacy LUT binary slot format) writes
    into Stock `FX3 Ver. 7.00/7.02` (`7.00+` optimized LUT binary slot format)
    `p2:/setting` `User1..User16` slots, requiring volatile `/tmp/fx6_lut_overlay`
    redirection and `H0 == H3` `p2:/setting` hash invariance.
    """
    errors: List[str] = []

    donor_fmt = classify_user_lut_slot_binary_format(donor_stageb_fw_version)
    host_fmt = classify_user_lut_slot_binary_format(host_stock_fx3_fw_version)
    slot_parsed = _parse_user_lut_slot(lut_slot)

    if (
        donor_fmt == "INVALID_FW_VERSION"
        or host_fmt == "INVALID_FW_VERSION"
        or slot_parsed is None
        or (not _version_gte(host_stock_fx3_fw_version, LUT_BINARY_SPLIT_BOUNDARY_FW))
        or _version_gte(donor_stageb_fw_version, LUT_BINARY_SPLIT_BOUNDARY_FW)
        or upgraded_from_le_601_stale_lut_unreregistered
    ):
        errors.append(
            f"User LUT slot/version format check failed: donor_fw={donor_stageb_fw_version!r} ({donor_fmt}), "
            f"host_fw={host_stock_fx3_fw_version!r} ({host_fmt}), slot={lut_slot!r} (expected User1..User16), "
            f"stale_601_unreregistered={upgraded_from_le_601_stale_lut_unreregistered}."
        )
        return (False, STATUS_BLOCKED_G70_USER_LUT_SLOT_OR_FORMAT_INVALID, errors)

    reg_norm = stageb_lut_registry_path.strip().replace("\\", "/")
    reg_lower = reg_norm.lower()
    targets_forbidden_p2 = any(
        reg_lower.startswith(pref.lower())
        for pref in FORBIDDEN_PERSISTENT_LUT_SETTING_PATHS
    )
    redirected_to_tmp_overlay = (
        reg_norm == REQUIRED_VOLATILE_LUT_OVERLAY_DIR
        or reg_norm.startswith(REQUIRED_VOLATILE_LUT_OVERLAY_DIR + "/")
    )

    if (
        stageb_p2_setting_lut_write_attempted
        or cross_generation_raw_slot_inject
        or int(p2_setting_lut_mutation_bytes) != 0
        or (not p2_setting_mount_ro)
        or targets_forbidden_p2
        or (not redirected_to_tmp_overlay)
    ):
        errors.append(
            f"Stage-B Ver. {donor_stageb_fw_version} ({donor_fmt}) -> Stock FX3 Ver. {host_stock_fx3_fw_version} "
            f"({host_fmt}) p2:/setting User LUT write BLOCKED: slot={slot_parsed[0]}, "
            f"registry_path={stageb_lut_registry_path!r} (must use {REQUIRED_VOLATILE_LUT_OVERLAY_DIR!r}), "
            f"write_attempted={stageb_p2_setting_lut_write_attempted}, "
            f"raw_inject={cross_generation_raw_slot_inject}, "
            f"mutation_bytes={p2_setting_lut_mutation_bytes}, p2_ro={p2_setting_mount_ro}."
        )
        return (False, STATUS_BLOCKED_G70_STAGEB_601_TO_702_P2_SETTING_LUT_WRITE, errors)

    h0_clean = h0_p2_setting_sha256.strip().lower()
    h3_clean = h3_p2_setting_sha256.strip().lower()
    if (not h0_clean) or (not h3_clean) or (h0_clean != h3_clean):
        errors.append(
            f"p2:/setting H0 == H3 hash invariance violated: H0={h0_p2_setting_sha256!r}, "
            f"H3={h3_p2_setting_sha256!r}."
        )
        return (False, STATUS_BLOCKED_G70_H0_H3_P2_SETTING_HASH_DRIFT, errors)

    return (True, "", errors)


def validate_independent_shutter_speed_angle_bounds(
    *,
    firmware_version: str = HOST_STOCK_FX3_FW_VERSION,
    shutter_mode: str = "Angle",
    shooting_mode: str = "MOVIE",
    sq_mode_active: bool = False,
    rec_frame_rate: str = "23.98p",
    shutter_angle_deg: float = 180.0,
    shutter_frames_count: int = 1,
    shutter_speed_value: str = "1/48",
    shutter_speed_bk4_slot_id: Union[int, str] = DEFAULT_SHUTTER_SPEED_BK4_SLOT_ID,
    shutter_angle_bk4_slot_id: Union[int, str] = DEFAULT_SHUTTER_ANGLE_BK4_SLOT_ID,
    speed_and_angle_slots_independent: bool = True,
    mode_toggle_mutated_inactive_slot: bool = False,
    exposure_step_ev: Union[float, int, str] = 0.3,
    exposure_step_altered_shutter_angle: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Validate `[Shutter Mode]` (`Speed` vs `Angle`, `Ver. 6.00+` / `7.00` / `7.02` / `BIG6`)
    independent `Backup.bin` slot storage, `[Exposure step]` (`0.3EV / 0.5EV`) immunity,
    and angle range bounds (`5.6°..64F` in normal Movie vs `5.6°..360°` at `119.88p/100p`
    and in `S&Q`).
    """
    errors: List[str] = []

    fw_ok = _version_gte(firmware_version, MIN_SHUTTER_ANGLE_FW_VERSION)
    sm_norm = _norm_token(shutter_mode)
    shoot_raw = shooting_mode.strip().upper()
    shoot_ok = shoot_raw in ALLOWED_SHOOTING_MODES_G70
    is_sq = bool(sq_mode_active) or (shoot_raw == "S&Q")
    high_fps_flag = _is_high_fps_clamp_rate(rec_frame_rate)

    spd_slot = _normalize_int_value(shutter_speed_bk4_slot_id)
    ang_slot = _normalize_int_value(shutter_angle_bk4_slot_id)
    exp_ev = _parse_exposure_step_ev(exposure_step_ev)

    slots_ok = (
        fw_ok
        and (sm_norm in ALLOWED_SHUTTER_MODES)
        and shoot_ok
        and bool(shutter_speed_value.strip())
        and (spd_slot is not None and spd_slot > 0)
        and (ang_slot is not None and ang_slot > 0)
        and (spd_slot != ang_slot)
        and (speed_and_angle_slots_independent is True)
        and (mode_toggle_mutated_inactive_slot is False)
        and (exp_ev is not None)
        and (exposure_step_altered_shutter_angle is False)
    )
    if not slots_ok:
        errors.append(
            f"Shutter Speed/Angle independent storage or Exposure-Step immunity failed: "
            f"fw={firmware_version!r} (>={MIN_SHUTTER_ANGLE_FW_VERSION}), shutter_mode={shutter_mode!r}, "
            f"shooting_mode={shooting_mode!r}, speed_val={shutter_speed_value!r}, "
            f"speed_slot={shutter_speed_bk4_slot_id!r}, angle_slot={shutter_angle_bk4_slot_id!r}, "
            f"independent={speed_and_angle_slots_independent}, "
            f"toggle_mutated={mode_toggle_mutated_inactive_slot}, "
            f"exposure_step_ev={exposure_step_ev!r} (allowed 0.3/0.5), "
            f"step_altered_angle={exposure_step_altered_shutter_angle}."
        )
        return (False, STATUS_BLOCKED_G70_SHUTTER_SPEED_ANGLE_SLOT_COLLISION, errors)

    if high_fps_flag is None:
        errors.append(f"Invalid [Rec Frame Rate] token {rec_frame_rate!r}.")
        return (False, STATUS_BLOCKED_G70_SHUTTER_ANGLE_OUT_OF_BOUNDS, errors)

    clamp_360 = bool(high_fps_flag) or is_sq
    deg = float(shutter_angle_deg)
    frames = int(shutter_frames_count)

    if clamp_360:
        bounds_ok = (
            (frames == 1)
            and (SHUTTER_ANGLE_MIN_DEG <= deg <= SHUTTER_ANGLE_STD_MAX_DEG)
        )
    else:
        if frames == 1:
            bounds_ok = SHUTTER_ANGLE_MIN_DEG <= deg <= SHUTTER_ANGLE_NORMAL_MAX_EQUIV_DEG
        elif 2 <= frames <= SHUTTER_ANGLE_MAX_FRAMES_NORMAL:
            expected_equiv = frames * 360.0
            bounds_ok = (deg == 360.0) or (abs(deg - expected_equiv) <= 1e-3)
        else:
            bounds_ok = False

    if not bounds_ok:
        limit_desc = "5.6°..360.0° (1F)" if clamp_360 else "5.6°..64F (23040.0°)"
        errors.append(
            f"Shutter Angle out of bounds: angle={shutter_angle_deg}°, frames={shutter_frames_count}F, "
            f"rec_fps={rec_frame_rate!r}, sq_mode={is_sq} (allowed {limit_desc})."
        )
        return (False, STATUS_BLOCKED_G70_SHUTTER_ANGLE_OUT_OF_BOUNDS, errors)

    return (True, "", errors)


# ---------------------------------------------------------------------------
# 3. Core Guard Functions (`verify_fx3_4mode_fan_pwm_and_prebackup_guard`,
#    `verify_lut_601_702_split_and_shutter_angle_guard`)
# ---------------------------------------------------------------------------


def verify_fx3_4mode_fan_pwm_and_prebackup_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: Union[int, str] = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G69,
    fan_mode: str = "Auto",
    menu_options: Sequence[str] = FX3_EXACT_4_FAN_MENU_LABELS,
    recording_active: bool = False,
    observed_pwm_duty_pct: Optional[int] = None,
    off_in_rec_recording_normal_pwm_pct: int = OFF_IN_REC_RECORDING_NORMAL_PWM_PCT,
    off_in_rec_standby_pwm_pct: int = OFF_IN_REC_STANDBY_MAX_PWM_PCT,
    off_in_rec_emergency_override_enabled: bool = True,
    operation_context: str = "PRE_BACKUP_ADJUST_CONTROL_0X40_P3_75MIB",
    pre_backup_or_high_load: bool = True,
    require_auto_for_prebackup: bool = True,
    auto_power_off_temp: str = "High",
    cxd90057_temp_c: float = 44.0,
    cxd90058_temp_c: float = 42.0,
    guard_profile: str = "FX3_REALHW_G69_4MODE_FAN_PWM_GUARD_DEFAULT",
) -> Fx3FanPwmPreBackupThermalResult:
    """Verify Gate G69 (`ILME-FX3` Exact 4-Mode `[Fan Control]` & Pre-Backup Thermal Guard)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        body_model_name,
        firmware_version,
        fan_mode,
        operation_context,
        auto_power_off_temp,
        guard_profile,
    )
    bools = (
        recording_active,
        off_in_rec_emergency_override_enabled,
        pre_backup_or_high_load,
        require_auto_for_prebackup,
    )
    menu_seq_ok = (
        isinstance(menu_options, (list, tuple))
        and len(menu_options) > 0
        and all(isinstance(m, str) and bool(m.strip()) for m in menu_options)
    )
    b_id = _normalize_int_value(body_model_id)
    obs_pwm_ok = (
        observed_pwm_duty_pct is None
        or (_is_non_negative_int(observed_pwm_duty_pct) and int(observed_pwm_duty_pct) <= 100)
    )

    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and menu_seq_ok
        and all(isinstance(b, bool) for b in bools)
        and (b_id is not None and b_id >= 0)
        and obs_pwm_ok
        and _is_non_negative_int(off_in_rec_recording_normal_pwm_pct)
        and _is_non_negative_int(off_in_rec_standby_pwm_pct)
        and _is_finite_number(cxd90057_temp_c)
        and _is_finite_number(cxd90058_temp_c)
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G69_TELEMETRY_INVALID)
        errors.append("Gate G69 received invalid or malformed Fan PWM / Thermal telemetry.")

    enum_valid = False
    off_in_rec_valid = False
    prebackup_valid = False
    modeled_pwm = -1
    observed_pwm = -1
    canon_mode = "INVALID"
    emergency_active = False
    effective_ceiling = PREBACKUP_SOC_MAX_START_TEMP_C

    if telemetry_ok:
        canon_mode = _norm_fx3_fan_mode(fan_mode)
        peak_c = max(float(cxd90057_temp_c), float(cxd90058_temp_c))
        emergency_active = peak_c >= OFF_IN_REC_EMERGENCY_OVERRIDE_TEMP_C

        f_ok, f_code, f_errs = validate_fx3_4mode_fan_enum_and_off_in_rec_pwm(
            body_model_name=body_model_name,
            body_model_id=b_id,
            firmware_version=firmware_version,
            fan_mode=fan_mode,
            menu_options=menu_options,
            recording_active=recording_active,
            cxd90057_temp_c=float(cxd90057_temp_c),
            cxd90058_temp_c=float(cxd90058_temp_c),
            observed_pwm_duty_pct=observed_pwm_duty_pct,
            off_in_rec_recording_normal_pwm_pct=off_in_rec_recording_normal_pwm_pct,
            off_in_rec_standby_pwm_pct=off_in_rec_standby_pwm_pct,
            off_in_rec_emergency_override_enabled=off_in_rec_emergency_override_enabled,
        )
        if canon_mode in FX3_EXACT_4_FAN_MODES:
            modeled_pwm = compute_fx3_702_fan_pwm_duty_pct(
                fan_mode=canon_mode,
                recording_active=recording_active,
                cxd90057_temp_c=float(cxd90057_temp_c),
                cxd90058_temp_c=float(cxd90058_temp_c),
            )
            observed_pwm = (
                modeled_pwm
                if observed_pwm_duty_pct is None
                else int(observed_pwm_duty_pct)
            )
        if not f_ok:
            _add_code(codes, f_code)
            errors.extend(f_errs)
            enum_valid = f_code != STATUS_BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2
            off_in_rec_valid = (
                f_code != STATUS_BLOCKED_G69_OFF_IN_REC_PWM_CONTRACT_VIOLATION
                and enum_valid
            )
        else:
            enum_valid = True
            off_in_rec_valid = True

        apo_norm = _norm_auto_power_off_temp(auto_power_off_temp)
        op_ceiling = (
            AUTO_POWER_OFF_HIGH_MAX_TEMP_C
            if apo_norm == "HIGH"
            else AUTO_POWER_OFF_STANDARD_MAX_TEMP_C
        )
        is_pre_ctx = pre_backup_or_high_load or (
            _norm_token(operation_context) != "NORMAL_CAMERA_OPERATION"
        )
        effective_ceiling = (
            min(PREBACKUP_SOC_MAX_START_TEMP_C, op_ceiling)
            if is_pre_ctx
            else op_ceiling
        )

        p_ok, p_code, p_errs = validate_prebackup_fan_and_auto_power_off_temp(
            fan_mode=fan_mode,
            operation_context=operation_context,
            pre_backup_or_high_load=pre_backup_or_high_load,
            require_auto_for_prebackup=require_auto_for_prebackup,
            auto_power_off_temp=auto_power_off_temp,
            cxd90057_temp_c=float(cxd90057_temp_c),
            cxd90058_temp_c=float(cxd90058_temp_c),
        )
        if not p_ok:
            _add_code(codes, p_code)
            errors.extend(p_errs)
            prebackup_valid = False
        else:
            prebackup_valid = True
            if apo_norm == "STANDARD" and is_pre_ctx:
                warnings.append(
                    "[Auto Power OFF Temp.] is 'Standard'; 'High' is recommended during supervised bench cold backup."
                )

    valid = (
        telemetry_ok
        and enum_valid
        and off_in_rec_valid
        and prebackup_valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G69 if valid else codes[0]

    return Fx3FanPwmPreBackupThermalResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        body_model_name=str(body_model_name) if isinstance(body_model_name, str) else "INVALID",
        body_model_id=int(b_id) if b_id is not None else -1,
        body_model_id_hex=f"0x{b_id:08x}" if b_id is not None else "INVALID",
        firmware_version=str(firmware_version) if isinstance(firmware_version, str) else "INVALID",
        menu_path=FX3_FAN_CONTROL_MENU_PATH,
        fan_mode=str(fan_mode) if isinstance(fan_mode, str) else "INVALID",
        canonical_fan_mode=canon_mode,
        exact_4mode_enum_valid=enum_valid,
        recording_active=bool(recording_active) if isinstance(recording_active, bool) else False,
        modeled_pwm_duty_pct=modeled_pwm,
        observed_pwm_duty_pct=observed_pwm,
        off_in_rec_recording_normal_pwm_pct=int(off_in_rec_recording_normal_pwm_pct) if _is_non_negative_int(off_in_rec_recording_normal_pwm_pct) else -1,
        off_in_rec_standby_pwm_pct=int(off_in_rec_standby_pwm_pct) if _is_non_negative_int(off_in_rec_standby_pwm_pct) else -1,
        off_in_rec_emergency_override_enabled=bool(off_in_rec_emergency_override_enabled) if isinstance(off_in_rec_emergency_override_enabled, bool) else False,
        emergency_thermal_override_active=emergency_active,
        off_in_rec_pwm_contract_valid=off_in_rec_valid,
        operation_context=str(operation_context) if isinstance(operation_context, str) else "INVALID",
        pre_backup_or_high_load=bool(pre_backup_or_high_load) if isinstance(pre_backup_or_high_load, bool) else True,
        require_auto_for_prebackup=bool(require_auto_for_prebackup) if isinstance(require_auto_for_prebackup, bool) else True,
        always_off_prebackup_blocked=(STATUS_BLOCKED_G69_ALWAYS_OFF_PREBACKUP_BLOCKED in codes),
        auto_power_off_temp=str(auto_power_off_temp) if isinstance(auto_power_off_temp, str) else "INVALID",
        cxd90057_temp_c=float(cxd90057_temp_c) if _is_finite_number(cxd90057_temp_c) else -999.0,
        cxd90058_temp_c=float(cxd90058_temp_c) if _is_finite_number(cxd90058_temp_c) else -999.0,
        effective_thermal_ceiling_c=effective_ceiling,
        prebackup_thermal_guard_valid=prebackup_valid,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_lut_601_702_split_and_shutter_angle_guard(
    *,
    donor_stageb_fw_version: str = DONOR_FX6_FW_VERSION,
    host_stock_fx3_fw_version: str = HOST_STOCK_FX3_FW_VERSION,
    lut_slot: Union[str, int] = "User1",
    stageb_lut_registry_path: str = "/tmp/fx6_lut_overlay/User1.lutbin",
    stageb_p2_setting_lut_write_attempted: bool = False,
    cross_generation_raw_slot_inject: bool = False,
    p2_setting_lut_mutation_bytes: int = 0,
    p2_setting_mount_ro: bool = True,
    h0_p2_setting_sha256: str = DEFAULT_H0_P2_SETTING_SHA256,
    h3_p2_setting_sha256: str = DEFAULT_H0_P2_SETTING_SHA256,
    upgraded_from_le_601_stale_lut_unreregistered: bool = False,
    shutter_mode: str = "Angle",
    shooting_mode: str = "MOVIE",
    sq_mode_active: bool = False,
    rec_frame_rate: str = "23.98p",
    shutter_angle_deg: float = 180.0,
    shutter_frames_count: int = 1,
    shutter_speed_value: str = "1/48",
    shutter_speed_bk4_slot_id: Union[int, str] = DEFAULT_SHUTTER_SPEED_BK4_SLOT_ID,
    shutter_angle_bk4_slot_id: Union[int, str] = DEFAULT_SHUTTER_ANGLE_BK4_SLOT_ID,
    speed_and_angle_slots_independent: bool = True,
    mode_toggle_mutated_inactive_slot: bool = False,
    exposure_step_ev: Union[float, int, str] = 0.3,
    exposure_step_altered_shutter_angle: bool = False,
    guard_profile: str = "FX3_REALHW_G70_LUT_SPLIT_SHUTTER_ANGLE_GUARD_DEFAULT",
) -> Lut601Vs702SplitAndShutterAngleResult:
    """Verify Gate G70 (`Ver. 6.01` vs `Ver. 7.00/7.02` `p2:/setting` User LUT Binary
    Format Split Firewall & Independent `[Shutter Mode]` `Speed` vs `Angle` Bounds).
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        donor_stageb_fw_version,
        host_stock_fx3_fw_version,
        stageb_lut_registry_path,
        h0_p2_setting_sha256,
        h3_p2_setting_sha256,
        shutter_mode,
        shooting_mode,
        rec_frame_rate,
        shutter_speed_value,
        guard_profile,
    )
    bools = (
        stageb_p2_setting_lut_write_attempted,
        cross_generation_raw_slot_inject,
        p2_setting_mount_ro,
        upgraded_from_le_601_stale_lut_unreregistered,
        sq_mode_active,
        speed_and_angle_slots_independent,
        mode_toggle_mutated_inactive_slot,
        exposure_step_altered_shutter_angle,
    )
    slot_type_ok = isinstance(lut_slot, (str, int)) and (not isinstance(lut_slot, bool)) and (
        bool(lut_slot.strip()) if isinstance(lut_slot, str) else True
    )
    spd_slot = _normalize_int_value(shutter_speed_bk4_slot_id)
    ang_slot = _normalize_int_value(shutter_angle_bk4_slot_id)
    exp_type_ok = isinstance(exposure_step_ev, (int, float, str)) and (
        not isinstance(exposure_step_ev, bool)
    )

    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and slot_type_ok
        and exp_type_ok
        and all(isinstance(b, bool) for b in bools)
        and _is_non_negative_int(p2_setting_lut_mutation_bytes)
        and _is_finite_number(shutter_angle_deg)
        and isinstance(shutter_frames_count, int)
        and (not isinstance(shutter_frames_count, bool))
        and (spd_slot is not None)
        and (ang_slot is not None)
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G70_TELEMETRY_INVALID)
        errors.append(
            "Gate G70 received invalid or malformed LUT binary-split / Shutter Speed-Angle telemetry."
        )

    lut_ok = False
    shutter_ok = False
    donor_fmt = "INVALID_FW_VERSION"
    host_fmt = "INVALID_FW_VERSION"
    slot_name = "INVALID"
    slot_idx = -1
    redirected_ok = False
    h0_eq_h3 = False
    clamp_360 = False
    exp_ev_val = -1.0

    if telemetry_ok:
        donor_fmt = classify_user_lut_slot_binary_format(donor_stageb_fw_version)
        host_fmt = classify_user_lut_slot_binary_format(host_stock_fx3_fw_version)
        sp = _parse_user_lut_slot(lut_slot)
        if sp is not None:
            slot_name, slot_idx = sp
        reg_norm = stageb_lut_registry_path.strip().replace("\\", "/")
        redirected_ok = (
            reg_norm == REQUIRED_VOLATILE_LUT_OVERLAY_DIR
            or reg_norm.startswith(REQUIRED_VOLATILE_LUT_OVERLAY_DIR + "/")
        )
        h0_eq_h3 = (
            h0_p2_setting_sha256.strip().lower() == h3_p2_setting_sha256.strip().lower()
        )
        parsed_ev = _parse_exposure_step_ev(exposure_step_ev)
        if parsed_ev is not None:
            exp_ev_val = parsed_ev
        hfps = _is_high_fps_clamp_rate(rec_frame_rate)
        clamp_360 = bool(hfps) or bool(sq_mode_active) or (shooting_mode.strip().upper() == "S&Q")

        lut_ok, l_code, l_errs = validate_lut_601_vs_702_p2_setting_split_firewall(
            donor_stageb_fw_version=donor_stageb_fw_version,
            host_stock_fx3_fw_version=host_stock_fx3_fw_version,
            lut_slot=lut_slot,
            stageb_lut_registry_path=stageb_lut_registry_path,
            stageb_p2_setting_lut_write_attempted=stageb_p2_setting_lut_write_attempted,
            cross_generation_raw_slot_inject=cross_generation_raw_slot_inject,
            p2_setting_lut_mutation_bytes=p2_setting_lut_mutation_bytes,
            p2_setting_mount_ro=p2_setting_mount_ro,
            h0_p2_setting_sha256=h0_p2_setting_sha256,
            h3_p2_setting_sha256=h3_p2_setting_sha256,
            upgraded_from_le_601_stale_lut_unreregistered=upgraded_from_le_601_stale_lut_unreregistered,
        )
        if not lut_ok:
            _add_code(codes, l_code)
            errors.extend(l_errs)

        shutter_ok, s_code, s_errs = validate_independent_shutter_speed_angle_bounds(
            firmware_version=host_stock_fx3_fw_version,
            shutter_mode=shutter_mode,
            shooting_mode=shooting_mode,
            sq_mode_active=sq_mode_active,
            rec_frame_rate=rec_frame_rate,
            shutter_angle_deg=float(shutter_angle_deg),
            shutter_frames_count=shutter_frames_count,
            shutter_speed_value=shutter_speed_value,
            shutter_speed_bk4_slot_id=spd_slot,
            shutter_angle_bk4_slot_id=ang_slot,
            speed_and_angle_slots_independent=speed_and_angle_slots_independent,
            mode_toggle_mutated_inactive_slot=mode_toggle_mutated_inactive_slot,
            exposure_step_ev=exposure_step_ev,
            exposure_step_altered_shutter_angle=exposure_step_altered_shutter_angle,
        )
        if not shutter_ok:
            _add_code(codes, s_code)
            errors.extend(s_errs)

    valid = (
        telemetry_ok
        and lut_ok
        and shutter_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G70 if valid else codes[0]

    return Lut601Vs702SplitAndShutterAngleResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        donor_stageb_fw_version=str(donor_stageb_fw_version) if isinstance(donor_stageb_fw_version, str) else "INVALID",
        host_stock_fx3_fw_version=str(host_stock_fx3_fw_version) if isinstance(host_stock_fx3_fw_version, str) else "INVALID",
        donor_lut_slot_format=donor_fmt,
        host_lut_slot_format=host_fmt,
        generation_format_split_detected=(donor_fmt != host_fmt and donor_fmt != "INVALID_FW_VERSION" and host_fmt != "INVALID_FW_VERSION"),
        lut_slot_name=slot_name,
        lut_slot_index=slot_idx,
        stageb_lut_registry_path=str(stageb_lut_registry_path) if isinstance(stageb_lut_registry_path, str) else "INVALID",
        volatile_lut_overlay_redirected=redirected_ok,
        stageb_p2_setting_lut_write_attempted=bool(stageb_p2_setting_lut_write_attempted) if isinstance(stageb_p2_setting_lut_write_attempted, bool) else True,
        cross_generation_raw_slot_inject=bool(cross_generation_raw_slot_inject) if isinstance(cross_generation_raw_slot_inject, bool) else True,
        p2_setting_lut_mutation_bytes=int(p2_setting_lut_mutation_bytes) if _is_non_negative_int(p2_setting_lut_mutation_bytes) else -1,
        p2_setting_mount_ro=bool(p2_setting_mount_ro) if isinstance(p2_setting_mount_ro, bool) else False,
        h0_p2_setting_sha256=str(h0_p2_setting_sha256) if isinstance(h0_p2_setting_sha256, str) else "INVALID",
        h3_p2_setting_sha256=str(h3_p2_setting_sha256) if isinstance(h3_p2_setting_sha256, str) else "INVALID",
        h0_equals_h3_p2_setting=h0_eq_h3,
        upgraded_from_le_601_stale_lut_unreregistered=bool(upgraded_from_le_601_stale_lut_unreregistered) if isinstance(upgraded_from_le_601_stale_lut_unreregistered, bool) else True,
        lut_binary_split_firewall_valid=lut_ok,
        shutter_mode=str(shutter_mode) if isinstance(shutter_mode, str) else "INVALID",
        shooting_mode=str(shooting_mode) if isinstance(shooting_mode, str) else "INVALID",
        sq_mode_active=bool(sq_mode_active) if isinstance(sq_mode_active, bool) else False,
        rec_frame_rate=str(rec_frame_rate) if isinstance(rec_frame_rate, str) else "INVALID",
        high_fps_or_sq_360_clamp_active=clamp_360,
        shutter_angle_deg=float(shutter_angle_deg) if _is_finite_number(shutter_angle_deg) else -1.0,
        shutter_frames_count=int(shutter_frames_count) if isinstance(shutter_frames_count, int) and not isinstance(shutter_frames_count, bool) else -1,
        shutter_speed_value=str(shutter_speed_value) if isinstance(shutter_speed_value, str) else "INVALID",
        shutter_speed_bk4_slot_id=int(spd_slot) if spd_slot is not None else -1,
        shutter_angle_bk4_slot_id=int(ang_slot) if ang_slot is not None else -1,
        shutter_speed_bk4_slot_hex=f"0x{spd_slot:08x}" if spd_slot is not None and spd_slot >= 0 else "INVALID",
        shutter_angle_bk4_slot_hex=f"0x{ang_slot:08x}" if ang_slot is not None and ang_slot >= 0 else "INVALID",
        speed_and_angle_slots_independent=bool(speed_and_angle_slots_independent) if isinstance(speed_and_angle_slots_independent, bool) else False,
        mode_toggle_mutated_inactive_slot=bool(mode_toggle_mutated_inactive_slot) if isinstance(mode_toggle_mutated_inactive_slot, bool) else True,
        exposure_step_ev=exp_ev_val,
        exposure_step_altered_shutter_angle=bool(exposure_step_altered_shutter_angle) if isinstance(exposure_step_altered_shutter_angle, bool) else True,
        shutter_speed_angle_valid=shutter_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G69 & Gate G70 Evaluators (Donor Audit + Guard -> GateVerdict)
# ---------------------------------------------------------------------------


def evaluate_g69_fan_pwm_thermal_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    fan_pwm_thermal_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase199DonorAuditResult] = None,
) -> Tuple[GateVerdict, G69FanPwmThermalGuardResult]:
    """Evaluate Gate G69 (`ILME-FX3` Exact 4-Mode `[Fan Control]` & Pre-Backup Thermal Guard)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase199_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(fan_pwm_thermal_kwargs or {})
    guard = verify_fx3_4mode_fan_pwm_and_prebackup_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE199_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G69 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G69 if valid else codes[0]

    res = G69FanPwmThermalGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        fan_pwm_thermal_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, body={guard.body_model_name}({guard.body_model_id_hex}), "
        f"fw={guard.firmware_version}, fan={guard.canonical_fan_mode}(pwm={guard.observed_pwm_duty_pct}%, "
        f"off_in_rec_rec={guard.off_in_rec_recording_normal_pwm_pct}%, "
        f"off_in_rec_stby={guard.off_in_rec_standby_pwm_pct}%), "
        f"apo_temp={guard.auto_power_off_temp}, "
        f"cxd90057={guard.cxd90057_temp_c:.1f}C, cxd90058={guard.cxd90058_temp_c:.1f}C"
    )

    verdict = GateVerdict(
        gate_id=G69_GATE_ID,
        gate_code=G69_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


def evaluate_g70_lut_split_shutter_angle_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    lut_split_shutter_angle_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase199DonorAuditResult] = None,
) -> Tuple[GateVerdict, G70LutSplitShutterAngleGuardResult]:
    """Evaluate Gate G70 (`Ver. 6.01` vs `Ver. 7.00/7.02` `p2:/setting` User LUT Binary
    Format Split Firewall & Independent `[Shutter Mode]` `Speed` vs `Angle` Guard).
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase199_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(lut_split_shutter_angle_kwargs or {})
    guard = verify_lut_601_702_split_and_shutter_angle_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE199_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G70 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G70 if valid else codes[0]

    res = G70LutSplitShutterAngleGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        lut_split_shutter_angle_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, lut_split={guard.donor_stageb_fw_version}({guard.donor_lut_slot_format})"
        f"->{guard.host_stock_fx3_fw_version}({guard.host_lut_slot_format}), "
        f"slot={guard.lut_slot_name}, overlay={guard.volatile_lut_overlay_redirected}, "
        f"h0_eq_h3={guard.h0_equals_h3_p2_setting}, "
        f"shutter={guard.shutter_mode}({guard.shutter_angle_deg:.1f}deg/{guard.shutter_frames_count}F@"
        f"{guard.rec_frame_rate}, step={guard.exposure_step_ev}EV)"
    )

    verdict = GateVerdict(
        gate_id=G70_GATE_ID,
        gate_code=G70_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Unified 70-Gate Master Safety Preflight (`G01..G70`)
# ---------------------------------------------------------------------------


def evaluate_70gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G01..G68 pass-throughs
    tier0_manifest: Optional[Dict[str, object]] = None,
    worker_syscall_trace: Optional[List[Dict[str, object]]] = None,
    init2_failsafe_hook: Optional[str] = None,
    candidate_bundle_verified: Optional[bool] = None,
    allow_dry_run_gate12: bool = False,
    gate12_kwargs: Optional[Mapping[str, Any]] = None,
    ltc_kwargs: Optional[Mapping[str, Any]] = None,
    mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    crsdk_requests: Optional[Sequence[Mapping[str, Any]]] = None,
    crsdk_kwargs: Optional[Mapping[str, Any]] = None,
    spacc_operations: Optional[Sequence[Mapping[str, Any]]] = None,
    spacc_script_text: str = "",
    spacc_sector0_bytes: Optional[bytes] = None,
    harness_kwargs: Optional[Mapping[str, Any]] = None,
    fan_kwargs: Optional[Mapping[str, Any]] = None,
    power_kwargs: Optional[Mapping[str, Any]] = None,
    soc_start_ceiling_c: Optional[float] = None,
    planned_mounts: Sequence[str] = (),
    planned_writes: Sequence[str] = (),
    c2pa_calibration_script_text: str = "",
    calibration_mutation_bytes: int = 0,
    c2pa_keystore_writes_attempted: bool = False,
    exfat_dirty_bit_present: bool = False,
    exfat_unfinalized_rsv_present: bool = False,
    allow_c2pa_or_calibration_write: bool = False,
    p12_vma: int = P12_WLAN_FATAL_GUARD_VMA,
    p12_patched_rc: int = 0,
    p12_guard_enabled: bool = True,
    bk4_airplane_shadow: Optional[Mapping[int, int]] = None,
    wf12_bootloop_immune: bool = True,
    wbi_mutation_bytes: int = 0,
    cp_mutation_bytes: int = 0,
    nvram_persistent_writes: int = 0,
    request_persistent_emmc_writes: bool = False,
    slot_a: Optional[MediaSlotConfig] = None,
    slot_b: Optional[MediaSlotConfig] = None,
    p1_vbr_bytes: Optional[bytes] = None,
    p1_image_path: Optional[Path] = None,
    p1_device_node: str = "/dev/nflasha1",
    require_at_least_one_lab_card: bool = True,
    usblan_kwargs: Optional[Mapping[str, Any]] = None,
    ptpip_or_mc_requests: Optional[Sequence[Any]] = None,
    ptpip_authenticated: bool = True,
    allow_protocol_3_00: bool = False,
    rig_kwargs: Optional[Mapping[str, Any]] = None,
    emount_kwargs: Optional[Mapping[str, Any]] = None,
    power_failover_kwargs: Optional[Mapping[str, Any]] = None,
    rsv_bytes: Optional[bytes] = None,
    rsv_path: Optional[Path] = None,
    xlr_kwargs: Optional[Mapping[str, Any]] = None,
    gimbal_kwargs: Optional[Mapping[str, Any]] = None,
    dewpoint_kwargs: Optional[Mapping[str, Any]] = None,
    pmic_usbc_kwargs: Optional[Mapping[str, Any]] = None,
    intake_fan_kwargs: Optional[Mapping[str, Any]] = None,
    tripod_housing_kwargs: Optional[Mapping[str, Any]] = None,
    sensor_curtain_kwargs: Optional[Mapping[str, Any]] = None,
    subzero_altitude_kwargs: Optional[Mapping[str, Any]] = None,
    wireless_tx_emi_kwargs: Optional[Mapping[str, Any]] = None,
    longform_endurance_kwargs: Optional[Mapping[str, Any]] = None,
    pl_cantilever_kwargs: Optional[Mapping[str, Any]] = None,
    dummy_battery_kwargs: Optional[Mapping[str, Any]] = None,
    saltspray_haze_kwargs: Optional[Mapping[str, Any]] = None,
    followfocus_gimbal_kwargs: Optional[Mapping[str, Any]] = None,
    hdmi_aoc_kwargs: Optional[Mapping[str, Any]] = None,
    cfexpress_media_kwargs: Optional[Mapping[str, Any]] = None,
    usbpd_uvc_kwargs: Optional[Mapping[str, Any]] = None,
    multiterminal_ptp_kwargs: Optional[Mapping[str, Any]] = None,
    monsoon_mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    cagetwist_xlrh1_kwargs: Optional[Mapping[str, Any]] = None,
    vp_strobe_genlock_kwargs: Optional[Mapping[str, Any]] = None,
    vehiclerig_ibis_kwargs: Optional[Mapping[str, Any]] = None,
    jiritsu_service_kwargs: Optional[Mapping[str, Any]] = None,
    cnflasha_dualboot_kwargs: Optional[Mapping[str, Any]] = None,
    service_0336_canary_kwargs: Optional[Mapping[str, Any]] = None,
    stageb_mpr_ibis_p18_kwargs: Optional[Mapping[str, Any]] = None,
    pnflasha_mtdro_kwargs: Optional[Mapping[str, Any]] = None,
    rfnvs_fan_power_kwargs: Optional[Mapping[str, Any]] = None,
    uart1v8_isp_kwargs: Optional[Mapping[str, Any]] = None,
    imx510_sensor_cal_kwargs: Optional[Mapping[str, Any]] = None,
    cfexpress_ufu_kwargs: Optional[Mapping[str, Any]] = None,
    five_tier_el3_kwargs: Optional[Mapping[str, Any]] = None,
    cxd90058_sabin_kwargs: Optional[Mapping[str, Any]] = None,
    factory_seal_kwargs: Optional[Mapping[str, Any]] = None,
    c2pa_cert_kwargs: Optional[Mapping[str, Any]] = None,
    tc_gyro_meta_kwargs: Optional[Mapping[str, Any]] = None,
    dualmedia_vault_kwargs: Optional[Mapping[str, Any]] = None,
    bench_interlock_kwargs: Optional[Mapping[str, Any]] = None,
    ssboot_wbi2_kwargs: Optional[Mapping[str, Any]] = None,
    slot1_ufu_c2pa_kwargs: Optional[Mapping[str, Any]] = None,
    emount_breathing_kwargs: Optional[Mapping[str, Any]] = None,
    hdmi_raw_kwargs: Optional[Mapping[str, Any]] = None,
    fx3a_firewall_kwargs: Optional[Mapping[str, Any]] = None,
    xlrh1_mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    nouvc_dcc1_pd_kwargs: Optional[Mapping[str, Any]] = None,
    lut_path_cineei_bt_kwargs: Optional[Mapping[str, Any]] = None,
    usblan_rtmp_kwargs: Optional[Mapping[str, Any]] = None,
    clipflag_anamorphic_kwargs: Optional[Mapping[str, Any]] = None,
    # G69 inputs (4-Mode [Fan Control] Off in Rec Standby MAX PWM & Always Off Pre-Backup Guard)
    fan_pwm_thermal_kwargs: Optional[Mapping[str, Any]] = None,
    # G70 inputs (6.01 vs 7.00/7.02 p2:/setting LUT Split Firewall & Shutter Speed/Angle Bounds)
    lut_split_shutter_angle_kwargs: Optional[Mapping[str, Any]] = None,
    master_68_override: Optional[Master68GateReport] = None,
) -> Master70GateReport:
    """Evaluate all 70 Master Safety Gates (`G01..G70`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        if dry_run_simulated_backup is None
        else (dry_run_simulated or dry_run_simulated_backup)
    )

    m68_kwargs: Dict[str, Any] = {
        "force_clean_room": clean_forced,
        "dry_run_simulated": effective_dry_run,
        "include_large_binaries": include_large_binaries,
        "work_root": work_root,
        "tier0_manifest": tier0_manifest,
        "worker_syscall_trace": worker_syscall_trace,
        "init2_failsafe_hook": init2_failsafe_hook,
        "candidate_bundle_verified": candidate_bundle_verified,
        "allow_dry_run_gate12": allow_dry_run_gate12,
        "gate12_kwargs": gate12_kwargs,
        "ltc_kwargs": ltc_kwargs,
        "mishoe_kwargs": mishoe_kwargs,
        "crsdk_requests": crsdk_requests,
        "crsdk_kwargs": crsdk_kwargs,
        "spacc_operations": spacc_operations,
        "spacc_script_text": spacc_script_text,
        "spacc_sector0_bytes": spacc_sector0_bytes,
        "harness_kwargs": harness_kwargs,
        "fan_kwargs": fan_kwargs,
        "power_kwargs": power_kwargs,
        "planned_mounts": planned_mounts,
        "planned_writes": planned_writes,
        "c2pa_calibration_script_text": c2pa_calibration_script_text,
        "calibration_mutation_bytes": calibration_mutation_bytes,
        "c2pa_keystore_writes_attempted": c2pa_keystore_writes_attempted,
        "exfat_dirty_bit_present": exfat_dirty_bit_present,
        "exfat_unfinalized_rsv_present": exfat_unfinalized_rsv_present,
        "allow_c2pa_or_calibration_write": allow_c2pa_or_calibration_write,
        "p12_vma": p12_vma,
        "p12_patched_rc": p12_patched_rc,
        "p12_guard_enabled": p12_guard_enabled,
        "bk4_airplane_shadow": bk4_airplane_shadow,
        "wf12_bootloop_immune": wf12_bootloop_immune,
        "wbi_mutation_bytes": wbi_mutation_bytes,
        "cp_mutation_bytes": cp_mutation_bytes,
        "nvram_persistent_writes": nvram_persistent_writes,
        "request_persistent_emmc_writes": request_persistent_emmc_writes,
        "slot_a": slot_a,
        "slot_b": slot_b,
        "p1_vbr_bytes": p1_vbr_bytes,
        "p1_image_path": p1_image_path,
        "p1_device_node": p1_device_node,
        "require_at_least_one_lab_card": require_at_least_one_lab_card,
        "usblan_kwargs": usblan_kwargs,
        "ptpip_or_mc_requests": ptpip_or_mc_requests,
        "ptpip_authenticated": ptpip_authenticated,
        "allow_protocol_3_00": allow_protocol_3_00,
        "rig_kwargs": rig_kwargs,
        "emount_kwargs": emount_kwargs,
        "power_failover_kwargs": power_failover_kwargs,
        "rsv_bytes": rsv_bytes,
        "rsv_path": rsv_path,
        "xlr_kwargs": xlr_kwargs,
        "gimbal_kwargs": gimbal_kwargs,
        "dewpoint_kwargs": dewpoint_kwargs,
        "pmic_usbc_kwargs": pmic_usbc_kwargs,
        "intake_fan_kwargs": intake_fan_kwargs,
        "tripod_housing_kwargs": tripod_housing_kwargs,
        "sensor_curtain_kwargs": sensor_curtain_kwargs,
        "subzero_altitude_kwargs": subzero_altitude_kwargs,
        "wireless_tx_emi_kwargs": wireless_tx_emi_kwargs,
        "longform_endurance_kwargs": longform_endurance_kwargs,
        "pl_cantilever_kwargs": pl_cantilever_kwargs,
        "dummy_battery_kwargs": dummy_battery_kwargs,
        "saltspray_haze_kwargs": saltspray_haze_kwargs,
        "followfocus_gimbal_kwargs": followfocus_gimbal_kwargs,
        "hdmi_aoc_kwargs": hdmi_aoc_kwargs,
        "cfexpress_media_kwargs": cfexpress_media_kwargs,
        "usbpd_uvc_kwargs": usbpd_uvc_kwargs,
        "multiterminal_ptp_kwargs": multiterminal_ptp_kwargs,
        "monsoon_mishoe_kwargs": monsoon_mishoe_kwargs,
        "cagetwist_xlrh1_kwargs": cagetwist_xlrh1_kwargs,
        "vp_strobe_genlock_kwargs": vp_strobe_genlock_kwargs,
        "vehiclerig_ibis_kwargs": vehiclerig_ibis_kwargs,
        "jiritsu_service_kwargs": jiritsu_service_kwargs,
        "cnflasha_dualboot_kwargs": cnflasha_dualboot_kwargs,
        "service_0336_canary_kwargs": service_0336_canary_kwargs,
        "stageb_mpr_ibis_p18_kwargs": stageb_mpr_ibis_p18_kwargs,
        "pnflasha_mtdro_kwargs": pnflasha_mtdro_kwargs,
        "rfnvs_fan_power_kwargs": rfnvs_fan_power_kwargs,
        "uart1v8_isp_kwargs": uart1v8_isp_kwargs,
        "imx510_sensor_cal_kwargs": imx510_sensor_cal_kwargs,
        "cfexpress_ufu_kwargs": cfexpress_ufu_kwargs,
        "five_tier_el3_kwargs": five_tier_el3_kwargs,
        "cxd90058_sabin_kwargs": cxd90058_sabin_kwargs,
        "factory_seal_kwargs": factory_seal_kwargs,
        "c2pa_cert_kwargs": c2pa_cert_kwargs,
        "tc_gyro_meta_kwargs": tc_gyro_meta_kwargs,
        "dualmedia_vault_kwargs": dualmedia_vault_kwargs,
        "bench_interlock_kwargs": bench_interlock_kwargs,
        "ssboot_wbi2_kwargs": ssboot_wbi2_kwargs,
        "slot1_ufu_c2pa_kwargs": slot1_ufu_c2pa_kwargs,
        "emount_breathing_kwargs": emount_breathing_kwargs,
        "hdmi_raw_kwargs": hdmi_raw_kwargs,
        "fx3a_firewall_kwargs": fx3a_firewall_kwargs,
        "xlrh1_mishoe_kwargs": xlrh1_mishoe_kwargs,
        "nouvc_dcc1_pd_kwargs": nouvc_dcc1_pd_kwargs,
        "lut_path_cineei_bt_kwargs": lut_path_cineei_bt_kwargs,
        "usblan_rtmp_kwargs": usblan_rtmp_kwargs,
        "clipflag_anamorphic_kwargs": clipflag_anamorphic_kwargs,
    }
    if soc_start_ceiling_c is not None:
        m68_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m68_report: Master68GateReport = (
        master_68_override
        if master_68_override is not None
        else evaluate_68gate_preflight(resolved_root, **m68_kwargs)
    )

    phase199_audit = audit_phase199_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g69_verdict, g69_res = evaluate_g69_fan_pwm_thermal_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        fan_pwm_thermal_kwargs=fan_pwm_thermal_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase199_audit,
    )

    g70_verdict, g70_res = evaluate_g70_lut_split_shutter_angle_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        lut_split_shutter_angle_kwargs=lut_split_shutter_angle_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase199_audit,
    )

    gates_69_to_70 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g69_verdict, g70_verdict)
    ]
    all_gates = tuple(list(m68_report.gates) + gates_69_to_70)

    g01_to_g12_verified = int(m68_report.summary["g01_to_g12_verified"])
    g13_to_g68_verified = (
        int(m68_report.summary["g13_to_g66_verified"])
        + int(m68_report.summary["g67_to_g68_verified"])
    )
    g69_to_g70_verified = sum(1 for v in (g69_verdict, g70_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g68_verified + g69_to_g70_verified

    g69_to_g70_all_passed = g69_to_g70_verified == 2
    g13_to_g70_all_passed = (
        m68_report.g13_to_g68_all_passed and g69_to_g70_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m68_report.gates[:9])

    offline_67_verified = (
        g01_to_g09_ok
        and m68_report.offline_65_gates_verified
        and g69_to_g70_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_70_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g70_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes
    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m68_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_67_verified
        and m68_report.h0_h1_trial_entry_allowed
        and g69_to_g70_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m68_report.errors) + list(g69_verdict.errors) + list(g70_verdict.errors)
    )
    warnings: List[str] = (
        list(m68_report.warnings)
        + list(g69_verdict.warnings)
        + list(g70_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m68_report.g13_to_g68_all_passed:
        overall_status = m68_report.status
    elif not g69_verdict.passed:
        overall_status = g69_verdict.status
    elif not g70_verdict.passed:
        overall_status = g70_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_70_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_70_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_70_verified:
        overall_status = "VERIFIED_ALL_70_GATES"
    else:
        overall_status = "VERIFIED_67_OF_70_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m68_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g69_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g70_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 70,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 70 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g68_verified": g13_to_g68_verified,
        "g69_to_g70_verified": g69_to_g70_verified,
        "g13_to_g70_all_passed": g13_to_g70_all_passed,
        "g69_to_g70_all_passed": g69_to_g70_all_passed,
        "offline_67_gates_verified": offline_67_verified,
        "all_70_gates_verified": all_70_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "human_hardware_attach_token": HUMAN_HARDWARE_ATTACH_TOKEN,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master70GateReport(
        schema=REALHW_FAN_PWM_SHUTTER_ANGLE_LUT_SPLIT_70GATE_SCHEMA,
        version=REALHW_FAN_PWM_SHUTTER_ANGLE_LUT_SPLIT_70GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_67_gates_verified=offline_67_verified,
        all_70_gates_verified=all_70_verified,
        g13_to_g70_all_passed=g13_to_g70_all_passed,
        g69_to_g70_all_passed=g69_to_g70_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_68_report=m68_report.to_dict(),
        g69_result=g69_res.to_dict(),
        g70_result=g70_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_70_master_safety_gates = evaluate_70gate_preflight
run_70_gate_preflight = evaluate_70gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard",
        description=(
            "Phase 199 — ILME-FX3 4-Mode [Fan Control] Off in Rec Standby MAX PWM & "
            "Always Off Pre-Backup Thermal Guard (G69), Ver. 6.01 vs 7.00/7.02 p2:/setting "
            "User LUT Binary Split Firewall & Independent Shutter Speed/Angle Guard (G70), "
            "and 70-Gate Master Preflight (G01..G70)"
        ),
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
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G70 can be rehearsed offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_70gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        sys.stdout.write(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
        )
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/70 "
            f"g69_to_g70_all_passed={report.g69_to_g70_all_passed} "
            f"all_70_gates_verified={report.all_70_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
            f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
            f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
            f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        report.all_70_gates_verified
        if args.dry_run_simulated
        else report.offline_67_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
