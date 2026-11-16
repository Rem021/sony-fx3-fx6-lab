"""Phase 206 — Real-Hardware Main Track Part 24:
Gate G73 (`ILME-FX3` `Ver. 7.02` `[De-Squeeze Display]` `Off / 1.3x / 2.0x / 1.5x / 1.6x=1.65x`
CinemaScope `2.39:1` Horizontal Stretch Factor, Exact 4-Setting Lock
`[Focus Mode]=Manual Focus` + `[Focus Area]=Wide` + `[SteadyShot]=Off` +
`[Face Priority in Multi Metering]=Off`, Automatic De-Squeeze Suppression under
`[RAW Output]=On` / `[Off(HDMI Only)]` (`[HDMI Info. Display]=Off`) / `[Log Shooting]=Off` /
`[Remote Shooting]` / `Still`, Zero In-Body `FX3` `[Focus Map]` Menu/Overlay Block, and
External-Only `M&C` `Focus Map` `< 150fps` PDAF Cutoff Guard),
Gate G74 (Dual-Slot `[Simult. Recording]` + `[Auto Switch Media]` `Ver. 2.00+` Single-Card
Fallback vs `[Auto Switch Media]=Off` Strict Dual-Vault Redundant Parity Guard, plus
`[Shockless WB]` `Off / 1 / 2 / 3` Full-Frame-Rate `24p..240fps` Ramp & Immediate `0`-Frame
Bypass for `[C.Temp./Filter]` Kelvin Edits and `A-B / G-M` Fine-Grid Shifts),
and 74-Gate Master Safety Preflight (`G01..G74` / `verify-74-gates` / `run_74_gate_preflight`).

Composes `realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard` (`G01..G72`, keeping
`verify-58-gates` through `verify-72-gates` 100% intact) while hard-locking all physical
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
from .realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard import (
    Master72GateReport,
    evaluate_72gate_preflight,
)
from .realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_DESQUEEZE_FOCUSMAP_SIMULT_SHOCKLESSWB_74GATE_SCHEMA: str = (
    "fx3-realhw-desqueeze-focusmap-simult-shocklesswb-74gate-preflight-v1"
)
REALHW_DESQUEEZE_FOCUSMAP_SIMULT_SHOCKLESSWB_74GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

# Gate IDs & Canonical Codes for G73..G74
G73_GATE_ID: str = "G73_fx3_desqueeze_165x_4locks_and_external_mc_focusmap_guard"
G73_GATE_CODE: str = "GATE_G73_FX3_DESQUEEZE_165X_4LOCKS_AND_EXTERNAL_MC_FOCUSMAP_GUARD"
GATE_G73_FX3_DESQUEEZE_165X_4LOCKS_AND_EXTERNAL_MC_FOCUSMAP_GUARD: str = G73_GATE_CODE
G73: str = G73_GATE_CODE

G74_GATE_ID: str = "G74_simult_autoswitch_dual_vault_parity_and_shockless_wb_guard"
G74_GATE_CODE: str = "GATE_G74_SIMULT_AUTOSWITCH_DUAL_VAULT_PARITY_AND_SHOCKLESS_WB_GUARD"
GATE_G74_SIMULT_AUTOSWITCH_DUAL_VAULT_PARITY_AND_SHOCKLESS_WB_GUARD: str = G74_GATE_CODE
G74: str = G74_GATE_CODE

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G73: str = (
    "VERIFIED_FX3_DESQUEEZE_165X_4LOCKS_AND_EXTERNAL_MC_FOCUSMAP_GUARD"
)
STATUS_VERIFIED_G74: str = (
    "VERIFIED_SIMULT_AUTOSWITCH_DUAL_VAULT_PARITY_AND_SHOCKLESS_WB_GUARD"
)

# Gate G73 Violation Codes
STATUS_BLOCKED_G73_DESQUEEZE_MENU_OR_FACTOR_MISMATCH: str = (
    "BLOCKED_G73_DESQUEEZE_MENU_OR_FACTOR_MISMATCH"
)
STATUS_BLOCKED_G73_DESQUEEZE_4_LOCK_VIOLATION: str = (
    "BLOCKED_G73_DESQUEEZE_4_LOCK_VIOLATION"
)
STATUS_BLOCKED_G73_DESQUEEZE_SUPPRESSION_OR_ESSENCE_MUTATION: str = (
    "BLOCKED_G73_DESQUEEZE_SUPPRESSION_OR_ESSENCE_MUTATION"
)
STATUS_BLOCKED_G73_IN_BODY_FX3_FOCUS_MAP_FORBIDDEN: str = (
    "BLOCKED_G73_IN_BODY_FX3_FOCUS_MAP_FORBIDDEN"
)
STATUS_BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION: str = (
    "BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION"
)
STATUS_BLOCKED_G73_TELEMETRY_INVALID: str = (
    "BLOCKED_G73_DESQUEEZE_FOCUSMAP_TELEMETRY_INVALID"
)

# Gate G74 Violation Codes
STATUS_BLOCKED_G74_STRICT_DUAL_VAULT_REQUIRES_SIMULT_AUTOSWITCH_OFF: str = (
    "BLOCKED_G74_STRICT_DUAL_VAULT_REQUIRES_SIMULT_AUTOSWITCH_OFF"
)
STATUS_BLOCKED_G74_DUAL_SLOT_PARITY_DEGRADED_SINGLE_CARD: str = (
    "BLOCKED_G74_DUAL_SLOT_PARITY_DEGRADED_SINGLE_CARD"
)
STATUS_BLOCKED_G74_AUTOSWITCH_FIRMWARE_OR_STATE_MISMATCH: str = (
    "BLOCKED_G74_AUTOSWITCH_FIRMWARE_OR_STATE_MISMATCH"
)
STATUS_BLOCKED_G74_SHOCKLESS_WB_SETTING_OR_FPS_INVALID: str = (
    "BLOCKED_G74_SHOCKLESS_WB_SETTING_OR_FPS_INVALID"
)
STATUS_BLOCKED_G74_SHOCKLESS_WB_KELVIN_GRID_BYPASS_VIOLATION: str = (
    "BLOCKED_G74_SHOCKLESS_WB_KELVIN_GRID_BYPASS_VIOLATION"
)
STATUS_BLOCKED_G74_TELEMETRY_INVALID: str = (
    "BLOCKED_G74_SIMULT_AUTOSWITCH_SHOCKLESSWB_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE206_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE206_74GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G73 Constants — [De-Squeeze Display] (1.6x = 1.65x, 4 Locks) & External M&C Focus Map
FX3_DEFAULT_FW_VERSION_G73: str = "7.02"
DESQUEEZE_BASE_MIN_FW_VERSION: str = "2.00"
DESQUEEZE_15X_16X_MIN_FW_VERSION: str = "7.00"
DESQUEEZE_MENU_PATH: str = "MENU -> Setup -> [Display Option] -> [De-Squeeze Display]"

DESQUEEZE_OPTION_TO_HORIZONTAL_FACTOR: Mapping[str, float] = {
    "OFF": 1.0,
    "1.3X": 1.3,
    "2.0X": 2.0,
    "1.5X": 1.5,
    "1.6X": 1.65,
}
ALLOWED_DESQUEEZE_MENU_OPTIONS: Tuple[str, ...] = tuple(
    DESQUEEZE_OPTION_TO_HORIZONTAL_FACTOR.keys()
)
DESQUEEZE_16X_ACTUAL_STRETCH_FACTOR: float = 1.65
DESQUEEZE_16X_TARGET_ASPECT: str = "2.39:1_CINEMASCOPE"

DESQUEEZE_REQUIRED_4_LOCKS: Mapping[str, str] = {
    "focus_mode": "MANUAL_FOCUS",
    "focus_area": "WIDE",
    "steadyshot": "OFF",
    "face_priority_in_multi_metering": "OFF",
}

EXTERNAL_MC_FOCUS_MAP_MIN_FW_VERSION: str = "6.00"
EXTERNAL_MC_APP_MIN_VERSION_G73: str = "2.0.0"
FOCUS_MAP_CUTOFF_MIN_FPS: float = 150.0
ALLOWED_FOCUS_MAP_RENDER_TARGETS_G73: Tuple[str, ...] = (
    "EXTERNAL_MC_APP",
    "DISABLED",
)
FORBIDDEN_IN_BODY_FX3_FOCUS_MAP_TARGETS: Tuple[str, ...] = (
    "IN_BODY_LCD",
    "IN_BODY_EVF",
    "LOCAL_HDMI_OSD",
    "IN_BODY_MENU",
    "STAGEB_LOCAL_FOCUS_MAP_OVERLAY",
)

# Gate G74 Constants — [Simult. Recording] + [Auto Switch Media] & [Shockless WB]
REC_MEDIA_SETTINGS_MENU_PATH: str = "MENU -> Shooting -> [Media] -> [Rec. Media Settings]"
SIMULT_AUTOSWITCH_FALLBACK_MIN_FW_VERSION: str = "2.00"
REC_MEDIA_MODE_SIMULTANEOUS: str = "SIMULTANEOUS_RECORDING"
ALLOWED_REC_MEDIA_MODES_G74: Tuple[str, ...] = (
    "PRIORITIZE_SLOT_1",
    "PRIORITIZE_SLOT_2",
    REC_MEDIA_MODE_SIMULTANEOUS,
    "SORT_RECORDING",
)

SHOCKLESS_WB_MENU_PATH: str = "MENU -> Exposure/Color -> [White Balance] -> [Shockless WB]"
ALLOWED_SHOCKLESS_WB_LEVELS: Tuple[str, ...] = ("OFF", "1", "2", "3")
SHOCKLESS_WB_NOMINAL_RAMP_FRAMES: Mapping[str, int] = {
    "OFF": 0,
    "1": 12,
    "2": 24,
    "3": 48,
}
WB_OP_PRESET_SWITCH: str = "WB_PRESET_SWITCH"
WB_OP_CTEMP_KELVIN_EDIT: str = "CTEMP_KELVIN_EDIT"
WB_OP_AB_GM_GRID_SHIFT: str = "AB_GM_GRID_SHIFT"
ALLOWED_WB_OPERATION_TYPES: Tuple[str, ...] = (
    WB_OP_PRESET_SWITCH,
    WB_OP_CTEMP_KELVIN_EDIT,
    WB_OP_AB_GM_GRID_SHIFT,
)
SHOCKLESS_WB_IMMEDIATE_BYPASS_OPS: Tuple[str, ...] = (
    WB_OP_CTEMP_KELVIN_EDIT,
    WB_OP_AB_GM_GRID_SHIFT,
)
SHOCKLESS_WB_MIN_FPS: float = 1.0
SHOCKLESS_WB_MAX_FPS: float = 240.0
CTEMP_KELVIN_MIN: int = 2500
CTEMP_KELVIN_MAX: int = 9900

# Pinned FX3 v7.02 & FX6 v6.01 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE206_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"DeSqueeze",
            b"Squeeze",
            b"Focus",
            b"HDMI",
            b"RAW",
            b"WB",
            b"Media",
            b"Auto",
            b"BK4",
            b"/setting",
        ),
        "fx3/cpapp-b.bin::{15980568B,ILME-FX3,DeSqueeze,Squeeze,Focus,HDMI,RAW,WB,Media,Auto,BK4,/setting}",
    ),
    "fx3_saveload_so": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (
            b"\x7fELF",
            b"SaveLoadSettings",
            b"Save",
            b"Load",
            b"Settings",
            b"Backup",
        ),
        "fx3/libSaveLoadSettings.so::{18760B,ELF,SaveLoadSettings,Save,Load,Settings,Backup}",
    ),
    "fx3_bk4_bin": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (
            b"BK4",
            b"ILME-FX3",
            b"TC",
            b"/setting",
        ),
        "fx3/FX3-CX95900_ALLLANG-Backup.bin::{2229740B,BK4,ILME-FX3,TC,/setting}",
    ),
    "fx6_bk4_bin": (
        "fx6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (
            b"BK4",
            b"WB",
            b"TC",
            b"/setting",
        ),
        "fx6/CX95898_NTSC.bin::{2253333B,BK4,WB,TC,/setting}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase206DonorAuditResult:
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
class Fx3DeSqueeze4LocksAndExternalFocusMapResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    body_model_name: str
    body_model_id: int
    body_model_id_hex: str
    firmware_version: str
    desqueeze_menu_path: str
    desqueeze_menu_option: str
    canonical_desqueeze_option: str
    nominal_horizontal_factor: float
    effective_horizontal_factor: float
    desqueeze_auto_suppressed: bool
    suppression_reasons: Tuple[str, ...]
    desqueeze_display_engaged: bool
    focus_mode: str
    canonical_focus_mode: str
    focus_area: str
    canonical_focus_area: str
    steadyshot: str
    canonical_steadyshot: str
    face_priority_in_multi_metering: str
    canonical_face_priority: str
    four_locks_enforced: bool
    hdmi_raw_output_on: bool
    rec_media_dur_hdmi_output: str
    hdmi_info_display_on: bool
    log_shooting_on: bool
    remote_shooting_active: bool
    shooting_mode: str
    recorded_essence_desqueezed: bool
    hdmi_raw_pixels_desqueezed: bool
    desqueeze_guard_valid: bool
    in_body_fx3_focus_map_menu_claimed: bool
    stageb_local_focus_map_overlay_injected: bool
    focus_map_render_target: str
    canonical_focus_map_target: str
    external_mc_focus_map_active: bool
    monitor_control_app_version: str
    frame_rate_fps: float
    lens_attached: bool
    mount_adapter_attached: bool
    pdaf_capable_lens: bool
    camera_playback_mode: bool
    external_focus_map_cutoff_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SimultAutoSwitchParityAndShocklessWbResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    body_model_name: str
    firmware_version: str
    rec_media_menu_path: str
    rec_media_mode: str
    canonical_rec_media_mode: str
    auto_switch_media: str
    auto_switch_media_enabled: bool
    strict_dual_vault_parity_required: bool
    slot1_card_present_writable: bool
    slot2_card_present_writable: bool
    slot1_full: bool
    slot2_full: bool
    active_recording_slot_count: int
    single_card_fallback_active: bool
    modeled_dual_slot_state: str
    simult_autoswitch_parity_valid: bool
    shockless_wb_menu_path: str
    shockless_wb_setting: str
    canonical_shockless_wb_level: str
    frame_rate_fps: float
    wb_operation_type: str
    canonical_wb_operation_type: str
    ctemp_kelvin: int
    ab_fine_shift: int
    gm_fine_shift: int
    nominal_preset_ramp_frames: int
    observed_wb_ramp_frames: int
    immediate_zero_frame_bypass_required: bool
    immediate_zero_frame_bypass_observed: bool
    shockless_wb_guard_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G73DeSqueezeFocusMapGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    desqueeze_focusmap_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G74SimultAutoSwitchShocklessWbGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    simult_autoswitch_shocklesswb_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master74GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_71_gates_verified: bool
    all_74_gates_verified: bool
    g13_to_g74_all_passed: bool
    g73_to_g74_all_passed: bool
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
    master_72_report: Dict[str, Any]
    g73_result: Dict[str, Any]
    g74_result: Dict[str, Any]
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


def _is_int_no_bool(val: Any) -> bool:
    return isinstance(val, int) and (not isinstance(val, bool))


def _is_non_negative_int(val: Any) -> bool:
    return _is_int_no_bool(val) and val >= 0


def _is_finite_number(val: Any) -> bool:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
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
    return (v + (0,) * (max_len - len(v))) >= (f + (0,) * (max_len - len(f)))


def _norm_desqueeze_option(val: str) -> str:
    s = val.strip().upper().replace(" ", "")
    if s in ("OFF", "NONE", "1.0X", "DISABLE", "DISABLED"):
        return "OFF"
    if s in ("1.3X", "1.5X", "1.6X", "2.0X"):
        return s
    return s


def _norm_focus_mode(val: str) -> str:
    t = _norm_token(val).replace(".", "_")
    if t in ("MANUAL_FOCUS", "MF", "MANUAL"):
        return "MANUAL_FOCUS"
    if t in ("AF_C", "CONTINUOUS_AF", "AFC"):
        return "AF_C"
    if t in ("AF_S", "SINGLE_SHOT_AF", "AFS"):
        return "AF_S"
    return t


def _norm_focus_area(val: str) -> str:
    t = _norm_token(val).replace(".", "_")
    if t == "WIDE":
        return "WIDE"
    return t


def _norm_on_off_str(val: Union[str, bool]) -> Optional[str]:
    if isinstance(val, bool):
        return "ON" if val else "OFF"
    if isinstance(val, str):
        t = _norm_token(val).replace(".", "_")
        if t in ("ON", "ENABLED", "TRUE"):
            return "ON"
        if t in ("OFF", "DISABLED", "FALSE"):
            return "OFF"
    return None


def _norm_steadyshot(val: str) -> str:
    t = _norm_token(val).replace(".", "_")
    if t in ("OFF", "DISABLED"):
        return "OFF"
    if t in ("ACTIVE", "STANDARD", "ON"):
        return t
    return t


def _norm_rec_media_dur_hdmi(val: str) -> str:
    t = _norm_token(val).replace(".", "_")
    if t in ("ON", "REC_MEDIA_ON", "INTERNAL_AND_HDMI"):
        return "ON"
    if t in ("OFF_HDMI_ONLY", "HDMI_ONLY", "OFF"):
        return "OFF_HDMI_ONLY"
    return t


def _norm_shooting_mode_g73(val: str) -> str:
    t = _norm_token(val).replace(".", "_")
    if t in ("MOVIE", "CINE_EI", "FLEXIBLE_ISO", "CUSTOM_MOVIE", "BIG6_MOVIE"):
        return "MOVIE"
    if t in ("S_AND_Q", "SQ", "SLOW_AND_QUICK"):
        return "S&Q"
    if t in ("STILL", "PHOTO"):
        return "STILL"
    if t in ("PLAYBACK", "PB"):
        return "PLAYBACK"
    return t


def _norm_focus_map_target(val: str) -> str:
    t = _norm_token(val).replace(".", "_")
    if t in ("EXTERNAL_MC_APP", "MONITOR_AND_CONTROL", "MC_APP", "EXTERNAL_M_AND_C"):
        return "EXTERNAL_MC_APP"
    if t in ("DISABLED", "NONE", "OFF"):
        return "DISABLED"
    if t in (
        "IN_BODY_LCD",
        "LCD",
        "BODY_LCD",
        "IN_BODY_EVF",
        "LOCAL_HDMI_OSD",
        "IN_BODY_MENU",
        "STAGEB_LOCAL_FOCUS_MAP_OVERLAY",
    ):
        return "IN_BODY_LCD" if "LCD" in t else t
    return t


def _norm_rec_media_mode(val: str) -> str:
    t = _norm_token(val).replace(".", "_")
    if t in (
        "SIMULTANEOUS_RECORDING",
        "SIMULT_RECORDING",
        "SIMULTANEOUS",
        "SIMULT",
    ):
        return REC_MEDIA_MODE_SIMULTANEOUS
    if t in ("PRIORITIZE_SLOT_1", "PRIORITIZEREC_MEDIA_SLOT_1", "SLOT_1_ONLY", "SLOT_1"):
        return "PRIORITIZE_SLOT_1"
    if t in ("PRIORITIZE_SLOT_2", "PRIORITIZEREC_MEDIA_SLOT_2", "SLOT_2_ONLY", "SLOT_2"):
        return "PRIORITIZE_SLOT_2"
    if t in ("SORT_RECORDING", "SORT"):
        return "SORT_RECORDING"
    return t


def _norm_shockless_wb_level(val: Union[str, int]) -> str:
    if isinstance(val, bool):
        return "INVALID"
    if isinstance(val, int):
        return str(val) if val in (1, 2, 3) else ("OFF" if val == 0 else str(val))
    t = _norm_token(val).replace(".", "_")
    if t in ("OFF", "0", "DISABLED"):
        return "OFF"
    if t in ("1", "1_FAST", "FAST"):
        return "1"
    if t in ("2", "2_NORMAL", "NORMAL", "MID"):
        return "2"
    if t in ("3", "3_SLOW", "SLOW"):
        return "3"
    return t


def _norm_wb_op_type(val: str) -> str:
    t = _norm_token(val).replace(".", "_")
    if t in ("WB_PRESET_SWITCH", "PRESET_SWITCH", "CUSTOM_WB_SWITCH", "ATW_RAMP"):
        return WB_OP_PRESET_SWITCH
    if t in ("CTEMP_KELVIN_EDIT", "KELVIN_EDIT", "C_TEMP_FILTER_EDIT", "CTEMP_EDIT"):
        return WB_OP_CTEMP_KELVIN_EDIT
    if t in ("AB_GM_GRID_SHIFT", "AB_GM_SHIFT", "FINE_GRID_SHIFT", "GRID_SHIFT"):
        return WB_OP_AB_GM_GRID_SHIFT
    return t


def _write_stdout_safe(text: str) -> None:
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.close(devnull)


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase206_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase206DonorAuditResult:
    """Inspect FX3 `7.02` `cpapp-b.bin`, `libSaveLoadSettings.so`,
    `FX3-CX95900_ALLLANG-Backup.bin`, and FX6 `6.01` `CX95898_NTSC.bin` strictly via
    `os.open(..., os.O_RDONLY)` with deterministic clean-room fallback when
    `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent.
    """
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)
    effective_work_root: Optional[Path] = (
        Path(work_root) if work_root is not None else paths.work_root
    )

    resolved: Dict[str, Path] = {}
    if effective_work_root is not None:
        for key, (_body, rel_path, _sz, _sha, _toks, _lbl) in PINNED_PHASE206_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase206DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(spec[5] for spec in PINNED_PHASE206_DONOR_SPECS.values()),
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            sha256_by_artifact={k: spec[3] for k, spec in PINNED_PHASE206_DONOR_SPECS.items()},
            bytes_by_artifact={k: spec[2] for k, spec in PINNED_PHASE206_DONOR_SPECS.items()},
            errors=(),
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
    ) in PINNED_PHASE206_DONOR_SPECS.items():
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

    fx3_keys = {k for k, spec in PINNED_PHASE206_DONOR_SPECS.items() if spec[0] == "fx3"}
    fx6_keys = {k for k, spec in PINNED_PHASE206_DONOR_SPECS.items() if spec[0] == "fx6"}
    valid = len(errors) == 0 and len(missing) == 0
    return Phase206DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE206_DONOR_INTEGRITY,
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
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Pure Helper Functions & Sub-Validators (G73 & G74)
# ---------------------------------------------------------------------------


def resolve_desqueeze_horizontal_factor(desqueeze_menu_option: str) -> Optional[float]:
    """Map `ILME-FX3` `[De-Squeeze Display]` menu label to actual horizontal stretch factor:
    `Off -> 1.0`, `1.3x -> 1.3`, `2.0x -> 2.0`, `1.5x -> 1.5`, `1.6x -> 1.65` (`2.39:1`).
    """
    canon = _norm_desqueeze_option(desqueeze_menu_option)
    return DESQUEEZE_OPTION_TO_HORIZONTAL_FACTOR.get(canon)


def compute_desqueeze_auto_suppression_reasons(
    *,
    hdmi_raw_output_on: bool = False,
    rec_media_dur_hdmi_output: str = "On",
    log_shooting_on: bool = True,
    remote_shooting_active: bool = False,
    shooting_mode: str = "Movie",
) -> Tuple[str, ...]:
    """Return all active hardware conditions that automatically suppress `[De-Squeeze Display]`
    to `1.0x` unscaled monitoring on `ILME-FX3` (`Ver. 7.02`).
    """
    reasons: List[str] = []
    if hdmi_raw_output_on:
        reasons.append("HDMI_RAW_OUTPUT_ON")
    if _norm_rec_media_dur_hdmi(rec_media_dur_hdmi_output) == "OFF_HDMI_ONLY":
        reasons.append("REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY")
    if not log_shooting_on:
        reasons.append("LOG_SHOOTING_OFF")
    if remote_shooting_active:
        reasons.append("REMOTE_SHOOTING_ACTIVE")
    if _norm_shooting_mode_g73(shooting_mode) == "STILL":
        reasons.append("STILL_PHOTO_MODE")
    return tuple(reasons)


def validate_fx3_desqueeze_4locks_and_suppression(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: Union[int, str] = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G73,
    desqueeze_menu_option: str = "1.6x",
    effective_horizontal_factor: Optional[float] = None,
    desqueeze_display_engaged: Optional[bool] = None,
    focus_mode: str = "Manual Focus",
    focus_area: str = "Wide",
    steadyshot: str = "Off",
    face_priority_in_multi_metering: str = "Off",
    hdmi_raw_output_on: bool = False,
    rec_media_dur_hdmi_output: str = "On",
    hdmi_info_display_on: bool = False,
    log_shooting_on: bool = True,
    remote_shooting_active: bool = False,
    shooting_mode: str = "Movie",
    recorded_essence_desqueezed: bool = False,
    hdmi_raw_pixels_desqueezed: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Validate `ILME-FX3` `[De-Squeeze Display]` (`1.6x == 1.65x` CinemaScope), the 4 locked
    settings (`MF`, `Wide`, `SteadyShot=Off`, `Face Priority in Multi Metering=Off`), and
    automatic de-squeeze suppression (`RAW Output=On`, `Off(HDMI Only)` + `HDMI Info=Off`,
    `Log Shooting=Off`, `Remote Shooting`, `Still`).
    """
    errors: List[str] = []
    parsed_id = _normalize_int_value(body_model_id)
    if body_model_name.strip().upper() != FX3_MODEL_NAME or parsed_id != FX3_MODEL_ID:
        errors.append(
            f"Gate G73 requires body={FX3_MODEL_NAME} (0x{FX3_MODEL_ID:08x}); "
            f"got {body_model_name!r} ({body_model_id!r})."
        )
        return False, STATUS_BLOCKED_G73_DESQUEEZE_MENU_OR_FACTOR_MISMATCH, errors

    canon_opt = _norm_desqueeze_option(desqueeze_menu_option)
    nominal_factor = DESQUEEZE_OPTION_TO_HORIZONTAL_FACTOR.get(canon_opt)
    if nominal_factor is None:
        errors.append(
            f"Unsupported [De-Squeeze Display] menu option {desqueeze_menu_option!r}; "
            f"allowed: {ALLOWED_DESQUEEZE_MENU_OPTIONS}."
        )
        return False, STATUS_BLOCKED_G73_DESQUEEZE_MENU_OR_FACTOR_MISMATCH, errors

    req_fw = (
        DESQUEEZE_15X_16X_MIN_FW_VERSION
        if canon_opt in ("1.5X", "1.6X")
        else DESQUEEZE_BASE_MIN_FW_VERSION
    )
    if not _version_gte(firmware_version, req_fw):
        errors.append(
            f"[De-Squeeze Display] option {desqueeze_menu_option!r} requires ILME-FX3 "
            f"firmware >= Ver. {req_fw}; got {firmware_version!r}."
        )
        return False, STATUS_BLOCKED_G73_DESQUEEZE_MENU_OR_FACTOR_MISMATCH, errors

    if recorded_essence_desqueezed or hdmi_raw_pixels_desqueezed:
        errors.append(
            "Anamorphic de-squeeze on ILME-FX3 is strictly a monitoring transform: "
            f"recorded_essence_desqueezed={recorded_essence_desqueezed}, "
            f"hdmi_raw_pixels_desqueezed={hdmi_raw_pixels_desqueezed} (both must be False)."
        )
        return False, STATUS_BLOCKED_G73_DESQUEEZE_SUPPRESSION_OR_ESSENCE_MUTATION, errors

    norm_hdmi_rec = _norm_rec_media_dur_hdmi(rec_media_dur_hdmi_output)
    if norm_hdmi_rec not in ("ON", "OFF_HDMI_ONLY"):
        errors.append(
            f"Invalid [Rec. Media dur HDMI Output] value {rec_media_dur_hdmi_output!r}."
        )
        return False, STATUS_BLOCKED_G73_DESQUEEZE_SUPPRESSION_OR_ESSENCE_MUTATION, errors

    if norm_hdmi_rec == "OFF_HDMI_ONLY" and hdmi_info_display_on:
        errors.append(
            "When [Rec. Media dur HDMI Output] = [Off(HDMI Only)], [HDMI Info. Display] "
            "must be forced Off (hdmi_info_display_on=False) so clean HDMI output is preserved."
        )
        return False, STATUS_BLOCKED_G73_DESQUEEZE_SUPPRESSION_OR_ESSENCE_MUTATION, errors

    suppression_reasons = compute_desqueeze_auto_suppression_reasons(
        hdmi_raw_output_on=hdmi_raw_output_on,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        log_shooting_on=log_shooting_on,
        remote_shooting_active=remote_shooting_active,
        shooting_mode=shooting_mode,
    )
    suppressed = (canon_opt != "OFF") and (len(suppression_reasons) > 0)
    expected_engaged = (canon_opt != "OFF") and (not suppressed)
    expected_factor = nominal_factor if expected_engaged else 1.0

    if desqueeze_display_engaged is not None and desqueeze_display_engaged != expected_engaged:
        if suppressed and desqueeze_display_engaged:
            errors.append(
                f"[De-Squeeze Display] ({desqueeze_menu_option}) must auto-suppress under "
                f"{suppression_reasons}, but desqueeze_display_engaged=True."
            )
            return False, STATUS_BLOCKED_G73_DESQUEEZE_SUPPRESSION_OR_ESSENCE_MUTATION, errors
        errors.append(
            f"desqueeze_display_engaged={desqueeze_display_engaged} mismatches expected "
            f"{expected_engaged} for option={canon_opt}."
        )
        return False, STATUS_BLOCKED_G73_DESQUEEZE_MENU_OR_FACTOR_MISMATCH, errors

    if effective_horizontal_factor is not None:
        if round(float(effective_horizontal_factor), 3) != round(expected_factor, 3):
            code = (
                STATUS_BLOCKED_G73_DESQUEEZE_SUPPRESSION_OR_ESSENCE_MUTATION
                if suppressed
                else STATUS_BLOCKED_G73_DESQUEEZE_MENU_OR_FACTOR_MISMATCH
            )
            errors.append(
                f"Horizontal stretch factor mismatch for option={desqueeze_menu_option!r} "
                f"(suppressed={suppressed}): got {effective_horizontal_factor}x, "
                f"expected {expected_factor}x (note: 1.6x menu applies exact 1.65x stretch)."
            )
            return False, code, errors

    if expected_engaged:
        fm = _norm_focus_mode(focus_mode)
        fa = _norm_focus_area(focus_area)
        ss = _norm_steadyshot(steadyshot)
        fp = _norm_on_off_str(face_priority_in_multi_metering)
        lock_failures: List[str] = []
        if fm != "MANUAL_FOCUS":
            lock_failures.append(f"[Focus Mode]={focus_mode!r} (must be Manual Focus)")
        if fa != "WIDE":
            lock_failures.append(f"[Focus Area]={focus_area!r} (must be Wide)")
        if ss != "OFF":
            lock_failures.append(f"[SteadyShot]={steadyshot!r} (must be Off)")
        if fp != "OFF":
            lock_failures.append(
                f"[Face Priority in Multi Metering]={face_priority_in_multi_metering!r} (must be Off)"
            )
        if lock_failures:
            errors.append(
                f"[De-Squeeze Display] ({desqueeze_menu_option}) enforces 4 locked settings on "
                f"ILME-FX3; violations: {', '.join(lock_failures)}."
            )
            return False, STATUS_BLOCKED_G73_DESQUEEZE_4_LOCK_VIOLATION, errors

    return True, STATUS_SAFE, []


def validate_fx3_external_only_mc_focus_map_cutoff(
    *,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G73,
    in_body_fx3_focus_map_menu_claimed: bool = False,
    stageb_local_focus_map_overlay_injected: bool = False,
    focus_map_render_target: str = "EXTERNAL_MC_APP",
    external_mc_focus_map_active: bool = True,
    monitor_control_app_version: str = "2.4.0",
    frame_rate_fps: float = 23.98,
    lens_attached: bool = True,
    mount_adapter_attached: bool = False,
    pdaf_capable_lens: bool = True,
    shooting_mode: str = "Movie",
    camera_playback_mode: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Validate that `ILME-FX3` never claims an in-body `[Focus Map]` menu/LCD/HDMI overlay
    and enforces external `Monitor & Control` (`M&C`) PDAF `Focus Map` cutoffs (`< 150 fps`,
    native PDAF lens without mount adapter, non-playback).
    """
    errors: List[str] = []
    canon_target = _norm_focus_map_target(focus_map_render_target)

    if (
        in_body_fx3_focus_map_menu_claimed
        or stageb_local_focus_map_overlay_injected
        or canon_target not in ALLOWED_FOCUS_MAP_RENDER_TARGETS_G73
    ):
        errors.append(
            "ILME-FX3 has zero built-in [Focus Map] menu or local LCD/HDMI overlay hardware "
            f"(in_body_menu_claimed={in_body_fx3_focus_map_menu_claimed}, "
            f"stageb_local_overlay_injected={stageb_local_focus_map_overlay_injected}, "
            f"target={focus_map_render_target!r}); Focus Map is external M&C only."
        )
        return False, STATUS_BLOCKED_G73_IN_BODY_FX3_FOCUS_MAP_FORBIDDEN, errors

    fps = float(frame_rate_fps)
    if fps <= 0.0 or fps > 240.0:
        errors.append(f"Out-of-range camera frame rate {frame_rate_fps} fps.")
        return False, STATUS_BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION, errors

    in_playback = bool(camera_playback_mode) or (_norm_shooting_mode_g73(shooting_mode) == "PLAYBACK")

    if external_mc_focus_map_active:
        if canon_target != "EXTERNAL_MC_APP":
            errors.append(
                f"external_mc_focus_map_active=True conflicts with target={focus_map_render_target!r}."
            )
            return False, STATUS_BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION, errors
        if not _version_gte(firmware_version, EXTERNAL_MC_FOCUS_MAP_MIN_FW_VERSION):
            errors.append(
                f"External M&C Focus Map stream on ILME-FX3 requires firmware >= "
                f"Ver. {EXTERNAL_MC_FOCUS_MAP_MIN_FW_VERSION}; got {firmware_version!r}."
            )
            return False, STATUS_BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION, errors
        if not _version_gte(monitor_control_app_version, EXTERNAL_MC_APP_MIN_VERSION_G73):
            errors.append(
                f"Monitor & Control version {monitor_control_app_version!r} below "
                f"Ver. {EXTERNAL_MC_APP_MIN_VERSION_G73} Focus Map floor."
            )
            return False, STATUS_BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION, errors
        if fps >= FOCUS_MAP_CUTOFF_MIN_FPS:
            errors.append(
                f"External M&C Focus Map on ILME-FX3 is hard-disabled at frame rates "
                f">= {FOCUS_MAP_CUTOFF_MIN_FPS:.0f} fps (got {fps} fps)."
            )
            return False, STATUS_BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION, errors
        if (not lens_attached) or mount_adapter_attached or (not pdaf_capable_lens):
            errors.append(
                f"External M&C Focus Map requires native PDAF E-mount lens without mount adapter "
                f"(lens_attached={lens_attached}, mount_adapter={mount_adapter_attached}, "
                f"pdaf_capable={pdaf_capable_lens})."
            )
            return False, STATUS_BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION, errors
        if in_playback:
            errors.append("External M&C Focus Map is disabled during camera Playback mode.")
            return False, STATUS_BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION, errors

    return True, STATUS_SAFE, []


def validate_simult_recording_autoswitch_parity(
    *,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G73,
    rec_media_mode: str = "Simult. Recording",
    auto_switch_media: Union[str, bool] = "Off",
    strict_dual_vault_parity_required: bool = True,
    slot1_card_present_writable: bool = True,
    slot2_card_present_writable: bool = True,
    slot1_full: bool = False,
    slot2_full: bool = False,
    active_recording_slot_count: int = 2,
    single_card_fallback_active: bool = False,
) -> Tuple[bool, str, str, List[str], List[str]]:
    """Validate `[Simult. Recording]` + `[Auto Switch Media]` (`Ver. 2.00+`):
    - Enforces `[Auto Switch Media] = [Off]` whenever `strict_dual_vault_parity_required=True`
      so dual-card redundant/cold-vault capture never silently drops to single-card recording.
    - When `strict_dual_vault_parity_required=False` and `Auto Switch Media=On`, validates
      `Ver. 2.00+` single-card fallback state and emits a warning on single-slot degradation.
    """
    errors: List[str] = []
    warnings: List[str] = []
    canon_mode = _norm_rec_media_mode(rec_media_mode)
    if canon_mode not in ALLOWED_REC_MEDIA_MODES_G74:
        errors.append(
            f"Invalid [Rec. Media Settings] mode {rec_media_mode!r}; allowed: {ALLOWED_REC_MEDIA_MODES_G74}."
        )
        return False, STATUS_BLOCKED_G74_AUTOSWITCH_FIRMWARE_OR_STATE_MISMATCH, "INVALID", errors, warnings

    asw = _norm_on_off_str(auto_switch_media)
    if asw is None:
        errors.append(f"Invalid [Auto Switch Media] value {auto_switch_media!r} (expected On/Off).")
        return False, STATUS_BLOCKED_G74_AUTOSWITCH_FIRMWARE_OR_STATE_MISMATCH, "INVALID", errors, warnings
    autoswitch_on = asw == "ON"

    if strict_dual_vault_parity_required:
        if canon_mode != REC_MEDIA_MODE_SIMULTANEOUS or autoswitch_on:
            errors.append(
                "Strict dual-card vault/redundant parity requires [Rec. Media Settings] = "
                "[Simult. Recording] AND [Auto Switch Media] = [Off] (Ver. 2.00+ Auto Switch "
                "Media = On silently drops to single-card recording when one slot fills); "
                f"got mode={rec_media_mode!r}, auto_switch_media={auto_switch_media!r}."
            )
            return (
                False,
                STATUS_BLOCKED_G74_STRICT_DUAL_VAULT_REQUIRES_SIMULT_AUTOSWITCH_OFF,
                "BLOCKED_AUTOSWITCH_PARITY_RISK",
                errors,
                warnings,
            )
        if (
            (not slot1_card_present_writable)
            or (not slot2_card_present_writable)
            or slot1_full
            or slot2_full
            or active_recording_slot_count != 2
            or single_card_fallback_active
        ):
            errors.append(
                "Dual-slot strict parity degraded: both Slot 1 and Slot 2 must remain writable "
                f"and non-full (slot1_ok={slot1_card_present_writable}, slot2_ok={slot2_card_present_writable}, "
                f"slot1_full={slot1_full}, slot2_full={slot2_full}, active_slots={active_recording_slot_count}, "
                f"single_card_fallback={single_card_fallback_active})."
            )
            return (
                False,
                STATUS_BLOCKED_G74_DUAL_SLOT_PARITY_DEGRADED_SINGLE_CARD,
                "DEGRADED_OR_HALTED",
                errors,
                warnings,
            )
        return True, STATUS_SAFE, "STRICT_DUAL_SLOT_PARITY_LOCKED", [], warnings

    # Non-strict continuous marathon recording mode
    if canon_mode == REC_MEDIA_MODE_SIMULTANEOUS and autoswitch_on:
        if not _version_gte(firmware_version, SIMULT_AUTOSWITCH_FALLBACK_MIN_FW_VERSION):
            errors.append(
                f"[Simult. Recording] + [Auto Switch Media] = [On] requires ILME-FX3 firmware "
                f">= Ver. {SIMULT_AUTOSWITCH_FALLBACK_MIN_FW_VERSION}; got {firmware_version!r}."
            )
            return False, STATUS_BLOCKED_G74_AUTOSWITCH_FIRMWARE_OR_STATE_MISMATCH, "INVALID_FW", errors, warnings

        s1_avail = slot1_card_present_writable and (not slot1_full)
        s2_avail = slot2_card_present_writable and (not slot2_full)
        expected_slots = int(s1_avail) + int(s2_avail)
        expected_fallback = expected_slots == 1 and (slot1_full or slot2_full)

        if active_recording_slot_count != expected_slots or single_card_fallback_active != expected_fallback:
            errors.append(
                f"Simult. + Auto Switch Media state mismatch: expected active_slots={expected_slots}, "
                f"single_card_fallback={expected_fallback}, got active_slots={active_recording_slot_count}, "
                f"single_card_fallback={single_card_fallback_active}."
            )
            return False, STATUS_BLOCKED_G74_AUTOSWITCH_FIRMWARE_OR_STATE_MISMATCH, "STATE_MISMATCH", errors, warnings

        if expected_slots == 0:
            errors.append("Both Slot 1 and Slot 2 are full or unavailable; recording cannot continue.")
            return False, STATUS_BLOCKED_G74_DUAL_SLOT_PARITY_DEGRADED_SINGLE_CARD, "BOTH_SLOTS_FULL_HALTED", errors, warnings

        if expected_fallback:
            warnings.append(
                "Ver. 2.00+ [Simult. Recording] + [Auto Switch Media]=On has silently degraded to "
                "SINGLE-CARD recording after one slot filled; insert a blank card to restore dual-slot parity."
            )
            return True, STATUS_SAFE, "SINGLE_CARD_FALLBACK_ACTIVE", [], warnings
        return True, STATUS_SAFE, "DUAL_SLOT_MARATHON_ACTIVE", [], warnings

    return True, STATUS_SAFE, f"{canon_mode}_CONFIGURED", [], warnings


def validate_shockless_wb_and_immediate_kelvin_grid_bypass(
    *,
    shockless_wb_setting: Union[str, int] = "1",
    frame_rate_fps: float = 23.98,
    wb_operation_type: str = WB_OP_PRESET_SWITCH,
    ctemp_kelvin: int = 5600,
    ab_fine_shift: int = 0,
    gm_fine_shift: int = 0,
    observed_wb_ramp_frames: Optional[int] = None,
    immediate_zero_frame_bypass_observed: Optional[bool] = None,
) -> Tuple[bool, str, List[str]]:
    """Validate `ILME-FX3` `[Shockless WB]` (`Off / 1 / 2 / 3`) across `1..240fps` and enforce
    immediate `0`-frame smoothing bypass on direct `[C.Temp./Filter]` Kelvin edits and
    `A-B / G-M` fine-tuning grid shifts.
    """
    errors: List[str] = []
    canon_lvl = _norm_shockless_wb_level(shockless_wb_setting)
    if canon_lvl not in ALLOWED_SHOCKLESS_WB_LEVELS:
        errors.append(
            f"Invalid [Shockless WB] setting {shockless_wb_setting!r}; allowed: {ALLOWED_SHOCKLESS_WB_LEVELS}."
        )
        return False, STATUS_BLOCKED_G74_SHOCKLESS_WB_SETTING_OR_FPS_INVALID, errors

    fps = float(frame_rate_fps)
    if fps < SHOCKLESS_WB_MIN_FPS or fps > SHOCKLESS_WB_MAX_FPS:
        errors.append(
            f"[Shockless WB] frame rate {frame_rate_fps} fps outside supported FX3 bounds "
            f"[{SHOCKLESS_WB_MIN_FPS}, {SHOCKLESS_WB_MAX_FPS}] fps."
        )
        return False, STATUS_BLOCKED_G74_SHOCKLESS_WB_SETTING_OR_FPS_INVALID, errors

    if ctemp_kelvin < CTEMP_KELVIN_MIN or ctemp_kelvin > CTEMP_KELVIN_MAX:
        errors.append(
            f"[C.Temp./Filter] {ctemp_kelvin}K outside valid Sony bounds [{CTEMP_KELVIN_MIN}K, {CTEMP_KELVIN_MAX}K]."
        )
        return False, STATUS_BLOCKED_G74_SHOCKLESS_WB_SETTING_OR_FPS_INVALID, errors

    if abs(ab_fine_shift) > 9 or abs(gm_fine_shift) > 9:
        errors.append(
            f"WB fine-tuning grid shift out of +/-9 range (A-B={ab_fine_shift}, G-M={gm_fine_shift})."
        )
        return False, STATUS_BLOCKED_G74_SHOCKLESS_WB_SETTING_OR_FPS_INVALID, errors

    canon_op = _norm_wb_op_type(wb_operation_type)
    if canon_op not in ALLOWED_WB_OPERATION_TYPES:
        errors.append(
            f"Invalid WB operation type {wb_operation_type!r}; allowed: {ALLOWED_WB_OPERATION_TYPES}."
        )
        return False, STATUS_BLOCKED_G74_SHOCKLESS_WB_SETTING_OR_FPS_INVALID, errors

    bypass_required = canon_op in SHOCKLESS_WB_IMMEDIATE_BYPASS_OPS or canon_lvl == "OFF"
    nominal_frames = 0 if bypass_required else SHOCKLESS_WB_NOMINAL_RAMP_FRAMES[canon_lvl]
    actual_frames = nominal_frames if observed_wb_ramp_frames is None else int(observed_wb_ramp_frames)
    actual_bypass = (
        (actual_frames == 0)
        if immediate_zero_frame_bypass_observed is None
        else bool(immediate_zero_frame_bypass_observed)
    )

    if canon_op in SHOCKLESS_WB_IMMEDIATE_BYPASS_OPS:
        if actual_frames != 0 or (not actual_bypass):
            errors.append(
                f"Direct {canon_op} edits bypass [Shockless WB] ({canon_lvl}) on ILME-FX3 and "
                f"take effect immediately in 0 frames; got observed_wb_ramp_frames={actual_frames}, "
                f"immediate_zero_frame_bypass_observed={actual_bypass}."
            )
            return False, STATUS_BLOCKED_G74_SHOCKLESS_WB_KELVIN_GRID_BYPASS_VIOLATION, errors
    else:
        if canon_lvl == "OFF":
            if actual_frames != 0 or (not actual_bypass):
                errors.append(
                    f"When [Shockless WB] = Off, WB preset switch must apply in 0 frames; "
                    f"got ramp_frames={actual_frames}, bypass={actual_bypass}."
                )
                return False, STATUS_BLOCKED_G74_SHOCKLESS_WB_KELVIN_GRID_BYPASS_VIOLATION, errors
        else:
            if actual_frames <= 0 or actual_bypass:
                errors.append(
                    f"When [Shockless WB] = {canon_lvl} on WB_PRESET_SWITCH, ramp frames must be "
                    f"> 0 (non-bypassed); got ramp_frames={actual_frames}, bypass={actual_bypass}."
                )
                return False, STATUS_BLOCKED_G74_SHOCKLESS_WB_KELVIN_GRID_BYPASS_VIOLATION, errors

    return True, STATUS_SAFE, []


# ---------------------------------------------------------------------------
# 3. Composite Gate Verifiers (`G73` & `G74`)
# ---------------------------------------------------------------------------


def verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
    *,
    guard_profile: str = "fx3-7.02-desqueeze-165x-4locks-and-external-mc-focusmap-v1",
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: Union[int, str] = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G73,
    desqueeze_menu_option: str = "1.6x",
    effective_horizontal_factor: Optional[float] = None,
    desqueeze_display_engaged: Optional[bool] = None,
    focus_mode: str = "Manual Focus",
    focus_area: str = "Wide",
    steadyshot: str = "Off",
    face_priority_in_multi_metering: str = "Off",
    hdmi_raw_output_on: bool = False,
    rec_media_dur_hdmi_output: str = "On",
    hdmi_info_display_on: bool = False,
    log_shooting_on: bool = True,
    remote_shooting_active: bool = False,
    shooting_mode: str = "Movie",
    recorded_essence_desqueezed: bool = False,
    hdmi_raw_pixels_desqueezed: bool = False,
    in_body_fx3_focus_map_menu_claimed: bool = False,
    stageb_local_focus_map_overlay_injected: bool = False,
    focus_map_render_target: str = "EXTERNAL_MC_APP",
    external_mc_focus_map_active: bool = True,
    monitor_control_app_version: str = "2.4.0",
    frame_rate_fps: float = 23.98,
    lens_attached: bool = True,
    mount_adapter_attached: bool = False,
    pdaf_capable_lens: bool = True,
    camera_playback_mode: bool = False,
) -> Fx3DeSqueeze4LocksAndExternalFocusMapResult:
    """Gate G73 composite verifier: `[De-Squeeze Display]` (`1.6x == 1.65x`, 4-setting lock,
    HDMI RAW / `Off(HDMI Only)` / `Log Off` / `Remote Shooting` auto-suppression) +
    External-Only `M&C` `Focus Map` (`< 150 fps` cutoff, zero in-body FX3 overlay).
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        guard_profile,
        body_model_name,
        firmware_version,
        desqueeze_menu_option,
        focus_mode,
        focus_area,
        steadyshot,
        face_priority_in_multi_metering,
        rec_media_dur_hdmi_output,
        shooting_mode,
        focus_map_render_target,
        monitor_control_app_version,
    )
    req_bools = (
        hdmi_raw_output_on,
        hdmi_info_display_on,
        log_shooting_on,
        remote_shooting_active,
        recorded_essence_desqueezed,
        hdmi_raw_pixels_desqueezed,
        in_body_fx3_focus_map_menu_claimed,
        stageb_local_focus_map_overlay_injected,
        external_mc_focus_map_active,
        lens_attached,
        mount_adapter_attached,
        pdaf_capable_lens,
        camera_playback_mode,
    )
    parsed_body_id = _normalize_int_value(body_model_id)
    opt_factor_ok = effective_horizontal_factor is None or _is_finite_number(
        effective_horizontal_factor
    )
    opt_engaged_ok = desqueeze_display_engaged is None or isinstance(
        desqueeze_display_engaged, bool
    )

    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and all(isinstance(b, bool) for b in req_bools)
        and (parsed_body_id is not None)
        and opt_factor_ok
        and opt_engaged_ok
        and _is_finite_number(frame_rate_fps)
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G73_TELEMETRY_INVALID)
        errors.append(
            "Gate G73 received invalid or malformed De-Squeeze / External Focus Map telemetry."
        )

    desq_ok = False
    fmap_ok = False
    canon_opt = "INVALID"
    nom_factor = -1.0
    eff_factor = -1.0
    supp_reasons: Tuple[str, ...] = ()
    suppressed = False
    engaged = False
    canon_fm = "INVALID"
    canon_fa = "INVALID"
    canon_ss = "INVALID"
    canon_fp = "INVALID"
    locks_ok = False
    canon_fmap_target = "INVALID"

    if telemetry_ok:
        assert parsed_body_id is not None
        canon_opt = _norm_desqueeze_option(desqueeze_menu_option)
        nf = DESQUEEZE_OPTION_TO_HORIZONTAL_FACTOR.get(canon_opt)
        nom_factor = nf if nf is not None else -1.0
        supp_reasons = compute_desqueeze_auto_suppression_reasons(
            hdmi_raw_output_on=hdmi_raw_output_on,
            rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
            log_shooting_on=log_shooting_on,
            remote_shooting_active=remote_shooting_active,
            shooting_mode=shooting_mode,
        )
        suppressed = (canon_opt != "OFF") and (len(supp_reasons) > 0)
        expected_engaged = (canon_opt != "OFF") and (not suppressed) and (nf is not None)
        engaged = (
            bool(desqueeze_display_engaged)
            if desqueeze_display_engaged is not None
            else expected_engaged
        )
        expected_factor = nom_factor if expected_engaged else 1.0
        eff_factor = (
            float(effective_horizontal_factor)
            if effective_horizontal_factor is not None
            else expected_factor
        )
        canon_fm = _norm_focus_mode(focus_mode)
        canon_fa = _norm_focus_area(focus_area)
        canon_ss = _norm_steadyshot(steadyshot)
        fp_norm = _norm_on_off_str(face_priority_in_multi_metering)
        canon_fp = fp_norm if fp_norm is not None else "INVALID"
        locks_ok = (not expected_engaged) or (
            canon_fm == "MANUAL_FOCUS"
            and canon_fa == "WIDE"
            and canon_ss == "OFF"
            and canon_fp == "OFF"
        )
        canon_fmap_target = _norm_focus_map_target(focus_map_render_target)

        desq_ok, d_code, d_errs = validate_fx3_desqueeze_4locks_and_suppression(
            body_model_name=body_model_name,
            body_model_id=parsed_body_id,
            firmware_version=firmware_version,
            desqueeze_menu_option=desqueeze_menu_option,
            effective_horizontal_factor=effective_horizontal_factor,
            desqueeze_display_engaged=desqueeze_display_engaged,
            focus_mode=focus_mode,
            focus_area=focus_area,
            steadyshot=steadyshot,
            face_priority_in_multi_metering=face_priority_in_multi_metering,
            hdmi_raw_output_on=hdmi_raw_output_on,
            rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
            hdmi_info_display_on=hdmi_info_display_on,
            log_shooting_on=log_shooting_on,
            remote_shooting_active=remote_shooting_active,
            shooting_mode=shooting_mode,
            recorded_essence_desqueezed=recorded_essence_desqueezed,
            hdmi_raw_pixels_desqueezed=hdmi_raw_pixels_desqueezed,
        )
        if not desq_ok:
            _add_code(codes, d_code)
            errors.extend(d_errs)

        fmap_ok, f_code, f_errs = validate_fx3_external_only_mc_focus_map_cutoff(
            firmware_version=firmware_version,
            in_body_fx3_focus_map_menu_claimed=in_body_fx3_focus_map_menu_claimed,
            stageb_local_focus_map_overlay_injected=stageb_local_focus_map_overlay_injected,
            focus_map_render_target=focus_map_render_target,
            external_mc_focus_map_active=external_mc_focus_map_active,
            monitor_control_app_version=monitor_control_app_version,
            frame_rate_fps=float(frame_rate_fps),
            lens_attached=lens_attached,
            mount_adapter_attached=mount_adapter_attached,
            pdaf_capable_lens=pdaf_capable_lens,
            shooting_mode=shooting_mode,
            camera_playback_mode=camera_playback_mode,
        )
        if not fmap_ok:
            _add_code(codes, f_code)
            errors.extend(f_errs)

    valid = (
        telemetry_ok
        and desq_ok
        and fmap_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G73 if valid else codes[0]

    return Fx3DeSqueeze4LocksAndExternalFocusMapResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        body_model_name=str(body_model_name) if isinstance(body_model_name, str) else "INVALID",
        body_model_id=int(parsed_body_id) if parsed_body_id is not None else -1,
        body_model_id_hex=(
            f"0x{parsed_body_id:08x}"
            if parsed_body_id is not None and parsed_body_id >= 0
            else "INVALID"
        ),
        firmware_version=str(firmware_version) if isinstance(firmware_version, str) else "INVALID",
        desqueeze_menu_path=DESQUEEZE_MENU_PATH,
        desqueeze_menu_option=(
            str(desqueeze_menu_option) if isinstance(desqueeze_menu_option, str) else "INVALID"
        ),
        canonical_desqueeze_option=canon_opt,
        nominal_horizontal_factor=nom_factor,
        effective_horizontal_factor=eff_factor,
        desqueeze_auto_suppressed=suppressed,
        suppression_reasons=supp_reasons,
        desqueeze_display_engaged=engaged,
        focus_mode=str(focus_mode) if isinstance(focus_mode, str) else "INVALID",
        canonical_focus_mode=canon_fm,
        focus_area=str(focus_area) if isinstance(focus_area, str) else "INVALID",
        canonical_focus_area=canon_fa,
        steadyshot=str(steadyshot) if isinstance(steadyshot, str) else "INVALID",
        canonical_steadyshot=canon_ss,
        face_priority_in_multi_metering=(
            str(face_priority_in_multi_metering)
            if isinstance(face_priority_in_multi_metering, str)
            else "INVALID"
        ),
        canonical_face_priority=canon_fp,
        four_locks_enforced=locks_ok,
        hdmi_raw_output_on=bool(hdmi_raw_output_on) if isinstance(hdmi_raw_output_on, bool) else False,
        rec_media_dur_hdmi_output=(
            str(rec_media_dur_hdmi_output)
            if isinstance(rec_media_dur_hdmi_output, str)
            else "INVALID"
        ),
        hdmi_info_display_on=(
            bool(hdmi_info_display_on) if isinstance(hdmi_info_display_on, bool) else False
        ),
        log_shooting_on=bool(log_shooting_on) if isinstance(log_shooting_on, bool) else False,
        remote_shooting_active=(
            bool(remote_shooting_active) if isinstance(remote_shooting_active, bool) else False
        ),
        shooting_mode=str(shooting_mode) if isinstance(shooting_mode, str) else "INVALID",
        recorded_essence_desqueezed=(
            bool(recorded_essence_desqueezed)
            if isinstance(recorded_essence_desqueezed, bool)
            else True
        ),
        hdmi_raw_pixels_desqueezed=(
            bool(hdmi_raw_pixels_desqueezed)
            if isinstance(hdmi_raw_pixels_desqueezed, bool)
            else True
        ),
        desqueeze_guard_valid=desq_ok,
        in_body_fx3_focus_map_menu_claimed=(
            bool(in_body_fx3_focus_map_menu_claimed)
            if isinstance(in_body_fx3_focus_map_menu_claimed, bool)
            else True
        ),
        stageb_local_focus_map_overlay_injected=(
            bool(stageb_local_focus_map_overlay_injected)
            if isinstance(stageb_local_focus_map_overlay_injected, bool)
            else True
        ),
        focus_map_render_target=(
            str(focus_map_render_target) if isinstance(focus_map_render_target, str) else "INVALID"
        ),
        canonical_focus_map_target=canon_fmap_target,
        external_mc_focus_map_active=(
            bool(external_mc_focus_map_active)
            if isinstance(external_mc_focus_map_active, bool)
            else False
        ),
        monitor_control_app_version=(
            str(monitor_control_app_version)
            if isinstance(monitor_control_app_version, str)
            else "INVALID"
        ),
        frame_rate_fps=float(frame_rate_fps) if _is_finite_number(frame_rate_fps) else -1.0,
        lens_attached=bool(lens_attached) if isinstance(lens_attached, bool) else False,
        mount_adapter_attached=(
            bool(mount_adapter_attached) if isinstance(mount_adapter_attached, bool) else True
        ),
        pdaf_capable_lens=bool(pdaf_capable_lens) if isinstance(pdaf_capable_lens, bool) else False,
        camera_playback_mode=(
            bool(camera_playback_mode) if isinstance(camera_playback_mode, bool) else True
        ),
        external_focus_map_cutoff_valid=fmap_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_simult_autoswitch_parity_and_shockless_wb_guard(
    *,
    guard_profile: str = "fx3-7.02-simult-autoswitch-parity-and-shockless-wb-v1",
    body_model_name: str = FX3_MODEL_NAME,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G73,
    rec_media_mode: str = "Simult. Recording",
    auto_switch_media: Union[str, bool] = "Off",
    strict_dual_vault_parity_required: bool = True,
    slot1_card_present_writable: bool = True,
    slot2_card_present_writable: bool = True,
    slot1_full: bool = False,
    slot2_full: bool = False,
    active_recording_slot_count: int = 2,
    single_card_fallback_active: bool = False,
    shockless_wb_setting: Union[str, int] = "1",
    frame_rate_fps: float = 23.98,
    wb_operation_type: str = WB_OP_PRESET_SWITCH,
    ctemp_kelvin: int = 5600,
    ab_fine_shift: int = 0,
    gm_fine_shift: int = 0,
    observed_wb_ramp_frames: Optional[int] = None,
    immediate_zero_frame_bypass_observed: Optional[bool] = None,
) -> SimultAutoSwitchParityAndShocklessWbResult:
    """Gate G74 composite verifier: Dual-Slot `[Simult. Recording]` + `[Auto Switch Media]`
    Parity Guard (`Off` required for strict dual-vault parity vs `Ver. 2.00+` single-card
    fallback warning) + `[Shockless WB]` (`Off / 1 / 2 / 3`) & Kelvin / `A-B / G-M` Immediate
    `0`-Frame Bypass Guard.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        guard_profile,
        body_model_name,
        firmware_version,
        rec_media_mode,
        wb_operation_type,
    )
    req_bools = (
        strict_dual_vault_parity_required,
        slot1_card_present_writable,
        slot2_card_present_writable,
        slot1_full,
        slot2_full,
        single_card_fallback_active,
    )
    asw_type_ok = isinstance(auto_switch_media, (str, bool)) and (
        bool(auto_switch_media.strip()) if isinstance(auto_switch_media, str) else True
    )
    swb_type_ok = (
        isinstance(shockless_wb_setting, (str, int))
        and (not isinstance(shockless_wb_setting, bool))
        and (bool(shockless_wb_setting.strip()) if isinstance(shockless_wb_setting, str) else True)
    )
    ramp_type_ok = observed_wb_ramp_frames is None or _is_int_no_bool(observed_wb_ramp_frames)
    bypass_type_ok = immediate_zero_frame_bypass_observed is None or isinstance(
        immediate_zero_frame_bypass_observed, bool
    )

    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and all(isinstance(b, bool) for b in req_bools)
        and asw_type_ok
        and swb_type_ok
        and _is_non_negative_int(active_recording_slot_count)
        and _is_finite_number(frame_rate_fps)
        and _is_int_no_bool(ctemp_kelvin)
        and _is_int_no_bool(ab_fine_shift)
        and _is_int_no_bool(gm_fine_shift)
        and ramp_type_ok
        and bypass_type_ok
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G74_TELEMETRY_INVALID)
        errors.append(
            "Gate G74 received invalid or malformed Simult./Auto Switch Media / Shockless WB telemetry."
        )

    simult_ok = False
    swb_ok = False
    canon_rec_mode = "INVALID"
    asw_en = False
    dual_state = "INVALID"
    canon_swb = "INVALID"
    canon_wb_op = "INVALID"
    nom_ramp = -1
    obs_ramp = -1
    bypass_req = False
    bypass_obs = False

    if telemetry_ok:
        if body_model_name.strip().upper() != FX3_MODEL_NAME:
            _add_code(codes, STATUS_BLOCKED_G74_AUTOSWITCH_FIRMWARE_OR_STATE_MISMATCH)
            errors.append(f"Gate G74 requires body={FX3_MODEL_NAME}; got {body_model_name!r}.")
        canon_rec_mode = _norm_rec_media_mode(rec_media_mode)
        asw_tok = _norm_on_off_str(auto_switch_media)
        asw_en = asw_tok == "ON"
        canon_swb = _norm_shockless_wb_level(shockless_wb_setting)
        canon_wb_op = _norm_wb_op_type(wb_operation_type)
        bypass_req = canon_wb_op in SHOCKLESS_WB_IMMEDIATE_BYPASS_OPS or canon_swb == "OFF"
        nom_ramp = (
            0
            if bypass_req
            else SHOCKLESS_WB_NOMINAL_RAMP_FRAMES.get(canon_swb, -1)
        )
        obs_ramp = (
            int(observed_wb_ramp_frames)
            if observed_wb_ramp_frames is not None
            else nom_ramp
        )
        bypass_obs = (
            bool(immediate_zero_frame_bypass_observed)
            if immediate_zero_frame_bypass_observed is not None
            else (obs_ramp == 0)
        )

        simult_ok, s_code, dual_state, s_errs, s_warns = validate_simult_recording_autoswitch_parity(
            firmware_version=firmware_version,
            rec_media_mode=rec_media_mode,
            auto_switch_media=auto_switch_media,
            strict_dual_vault_parity_required=strict_dual_vault_parity_required,
            slot1_card_present_writable=slot1_card_present_writable,
            slot2_card_present_writable=slot2_card_present_writable,
            slot1_full=slot1_full,
            slot2_full=slot2_full,
            active_recording_slot_count=active_recording_slot_count,
            single_card_fallback_active=single_card_fallback_active,
        )
        warnings.extend(s_warns)
        if not simult_ok:
            _add_code(codes, s_code)
            errors.extend(s_errs)

        swb_ok, w_code, w_errs = validate_shockless_wb_and_immediate_kelvin_grid_bypass(
            shockless_wb_setting=shockless_wb_setting,
            frame_rate_fps=float(frame_rate_fps),
            wb_operation_type=wb_operation_type,
            ctemp_kelvin=ctemp_kelvin,
            ab_fine_shift=ab_fine_shift,
            gm_fine_shift=gm_fine_shift,
            observed_wb_ramp_frames=observed_wb_ramp_frames,
            immediate_zero_frame_bypass_observed=immediate_zero_frame_bypass_observed,
        )
        if not swb_ok:
            _add_code(codes, w_code)
            errors.extend(w_errs)

    valid = (
        telemetry_ok
        and simult_ok
        and swb_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G74 if valid else codes[0]

    return SimultAutoSwitchParityAndShocklessWbResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        body_model_name=str(body_model_name) if isinstance(body_model_name, str) else "INVALID",
        firmware_version=str(firmware_version) if isinstance(firmware_version, str) else "INVALID",
        rec_media_menu_path=REC_MEDIA_SETTINGS_MENU_PATH,
        rec_media_mode=str(rec_media_mode) if isinstance(rec_media_mode, str) else "INVALID",
        canonical_rec_media_mode=canon_rec_mode,
        auto_switch_media=str(auto_switch_media),
        auto_switch_media_enabled=asw_en,
        strict_dual_vault_parity_required=(
            bool(strict_dual_vault_parity_required)
            if isinstance(strict_dual_vault_parity_required, bool)
            else True
        ),
        slot1_card_present_writable=(
            bool(slot1_card_present_writable)
            if isinstance(slot1_card_present_writable, bool)
            else False
        ),
        slot2_card_present_writable=(
            bool(slot2_card_present_writable)
            if isinstance(slot2_card_present_writable, bool)
            else False
        ),
        slot1_full=bool(slot1_full) if isinstance(slot1_full, bool) else True,
        slot2_full=bool(slot2_full) if isinstance(slot2_full, bool) else True,
        active_recording_slot_count=(
            int(active_recording_slot_count)
            if _is_non_negative_int(active_recording_slot_count)
            else -1
        ),
        single_card_fallback_active=(
            bool(single_card_fallback_active)
            if isinstance(single_card_fallback_active, bool)
            else True
        ),
        modeled_dual_slot_state=dual_state,
        simult_autoswitch_parity_valid=simult_ok,
        shockless_wb_menu_path=SHOCKLESS_WB_MENU_PATH,
        shockless_wb_setting=str(shockless_wb_setting),
        canonical_shockless_wb_level=canon_swb,
        frame_rate_fps=float(frame_rate_fps) if _is_finite_number(frame_rate_fps) else -1.0,
        wb_operation_type=(
            str(wb_operation_type) if isinstance(wb_operation_type, str) else "INVALID"
        ),
        canonical_wb_operation_type=canon_wb_op,
        ctemp_kelvin=int(ctemp_kelvin) if _is_int_no_bool(ctemp_kelvin) else -1,
        ab_fine_shift=int(ab_fine_shift) if _is_int_no_bool(ab_fine_shift) else 0,
        gm_fine_shift=int(gm_fine_shift) if _is_int_no_bool(gm_fine_shift) else 0,
        nominal_preset_ramp_frames=nom_ramp,
        observed_wb_ramp_frames=obs_ramp,
        immediate_zero_frame_bypass_required=bypass_req,
        immediate_zero_frame_bypass_observed=bypass_obs,
        shockless_wb_guard_valid=swb_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G73 & Gate G74 Evaluators (Donor Audit + Guard -> GateVerdict)
# ---------------------------------------------------------------------------


def evaluate_g73_desqueeze_focusmap_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    desqueeze_focusmap_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase206DonorAuditResult] = None,
) -> Tuple[GateVerdict, G73DeSqueezeFocusMapGuardResult]:
    """Evaluate Gate G73 (`[De-Squeeze Display]` `1.6x=1.65x` 4-Setting Lock / Auto-Suppression &
    External-Only `M&C Focus Map` `< 150fps` Cutoff Guard).
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase206_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
        **dict(desqueeze_focusmap_kwargs or {})
    )

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE206_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G73 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G73 if valid else codes[0]

    res = G73DeSqueezeFocusMapGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        desqueeze_focusmap_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, body={guard.body_model_name}({guard.body_model_id_hex}), "
        f"fw={guard.firmware_version}, desqueeze={guard.canonical_desqueeze_option}->"
        f"{guard.effective_horizontal_factor:.2f}x(suppressed={guard.desqueeze_auto_suppressed}, "
        f"4locks={guard.four_locks_enforced}), focus_map={guard.canonical_focus_map_target}"
        f"@{guard.frame_rate_fps:.2f}fps(cutoff<150fps={guard.external_focus_map_cutoff_valid})"
    )

    verdict = GateVerdict(
        gate_id=G73_GATE_ID,
        gate_code=G73_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


def evaluate_g74_simult_autoswitch_shocklesswb_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    simult_autoswitch_shocklesswb_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase206DonorAuditResult] = None,
) -> Tuple[GateVerdict, G74SimultAutoSwitchShocklessWbGuardResult]:
    """Evaluate Gate G74 (Dual-Slot `[Simult. Recording]` + `[Auto Switch Media]` Parity &
    `[Shockless WB]` `Off/1/2/3` + Kelvin/`A-B`/`G-M` Immediate `0`-Frame Bypass Guard).
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase206_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard = verify_simult_autoswitch_parity_and_shockless_wb_guard(
        **dict(simult_autoswitch_shocklesswb_kwargs or {})
    )

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE206_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G74 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G74 if valid else codes[0]

    res = G74SimultAutoSwitchShocklessWbGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        simult_autoswitch_shocklesswb_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, rec_mode={guard.canonical_rec_media_mode}, "
        f"auto_switch={guard.auto_switch_media_enabled}(strict_parity={guard.strict_dual_vault_parity_required}, "
        f"state={guard.modeled_dual_slot_state}, slots={guard.active_recording_slot_count}), "
        f"shockless_wb={guard.canonical_shockless_wb_level}({guard.canonical_wb_operation_type}, "
        f"ramp={guard.observed_wb_ramp_frames}F@{guard.frame_rate_fps:.2f}fps)"
    )

    verdict = GateVerdict(
        gate_id=G74_GATE_ID,
        gate_code=G74_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Unified 74-Gate Master Safety Preflight (`G01..G74`)
# ---------------------------------------------------------------------------


def evaluate_74gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G01..G72 pass-throughs
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
    fan_pwm_thermal_kwargs: Optional[Mapping[str, Any]] = None,
    lut_split_shutter_angle_kwargs: Optional[Mapping[str, Any]] = None,
    big6_camset_slot1_kwargs: Optional[Mapping[str, Any]] = None,
    vmcbncm1_tcin_hdmi_tcout_kwargs: Optional[Mapping[str, Any]] = None,
    # G73 inputs ([De-Squeeze Display] 1.6x=1.65x 4-Locks & External M&C Focus Map)
    desqueeze_focusmap_kwargs: Optional[Mapping[str, Any]] = None,
    # G74 inputs ([Simult. Recording] + [Auto Switch Media] Parity & [Shockless WB])
    simult_autoswitch_shocklesswb_kwargs: Optional[Mapping[str, Any]] = None,
    master_72_override: Optional[Master72GateReport] = None,
) -> Master74GateReport:
    """Evaluate all 74 Master Safety Gates (`G01..G74`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        if dry_run_simulated_backup is None
        else (dry_run_simulated or dry_run_simulated_backup)
    )

    m72_kwargs: Dict[str, Any] = {
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
        "fan_pwm_thermal_kwargs": fan_pwm_thermal_kwargs,
        "lut_split_shutter_angle_kwargs": lut_split_shutter_angle_kwargs,
        "big6_camset_slot1_kwargs": big6_camset_slot1_kwargs,
        "vmcbncm1_tcin_hdmi_tcout_kwargs": vmcbncm1_tcin_hdmi_tcout_kwargs,
    }
    if soc_start_ceiling_c is not None:
        m72_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m72_report: Master72GateReport = (
        master_72_override
        if master_72_override is not None
        else evaluate_72gate_preflight(resolved_root, **m72_kwargs)
    )

    phase206_audit = audit_phase206_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g73_verdict, g73_res = evaluate_g73_desqueeze_focusmap_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        desqueeze_focusmap_kwargs=desqueeze_focusmap_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase206_audit,
    )

    g74_verdict, g74_res = evaluate_g74_simult_autoswitch_shocklesswb_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        simult_autoswitch_shocklesswb_kwargs=simult_autoswitch_shocklesswb_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase206_audit,
    )

    gates_73_to_74 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g73_verdict, g74_verdict)
    ]
    all_gates = tuple(list(m72_report.gates) + gates_73_to_74)

    g01_to_g12_verified = int(m72_report.summary["g01_to_g12_verified"])
    g13_to_g72_verified = (
        int(m72_report.summary["g13_to_g70_verified"])
        + int(m72_report.summary["g71_to_g72_verified"])
    )
    g73_to_g74_verified = sum(1 for v in (g73_verdict, g74_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g72_verified + g73_to_g74_verified

    g73_to_g74_all_passed = g73_to_g74_verified == 2
    g13_to_g74_all_passed = (
        m72_report.g13_to_g72_all_passed and g73_to_g74_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m72_report.gates[:9])

    offline_71_verified = (
        g01_to_g09_ok
        and m72_report.offline_69_gates_verified
        and g73_to_g74_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_74_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g74_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes
    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m72_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_71_verified
        and m72_report.h0_h1_trial_entry_allowed
        and g73_to_g74_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m72_report.errors) + list(g73_verdict.errors) + list(g74_verdict.errors)
    )
    warnings: List[str] = (
        list(m72_report.warnings)
        + list(g73_verdict.warnings)
        + list(g74_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m72_report.g13_to_g72_all_passed:
        overall_status = m72_report.status
    elif not g73_verdict.passed:
        overall_status = g73_verdict.status
    elif not g74_verdict.passed:
        overall_status = g74_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_74_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_74_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_74_verified:
        overall_status = "VERIFIED_ALL_74_GATES"
    else:
        overall_status = "VERIFIED_71_OF_74_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m72_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g73_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g74_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 74,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 74 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g72_verified": g13_to_g72_verified,
        "g73_to_g74_verified": g73_to_g74_verified,
        "g13_to_g74_all_passed": g13_to_g74_all_passed,
        "g73_to_g74_all_passed": g73_to_g74_all_passed,
        "offline_71_gates_verified": offline_71_verified,
        "all_74_gates_verified": all_74_verified,
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

    return Master74GateReport(
        schema=REALHW_DESQUEEZE_FOCUSMAP_SIMULT_SHOCKLESSWB_74GATE_SCHEMA,
        version=REALHW_DESQUEEZE_FOCUSMAP_SIMULT_SHOCKLESSWB_74GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_71_gates_verified=offline_71_verified,
        all_74_gates_verified=all_74_verified,
        g13_to_g74_all_passed=g13_to_g74_all_passed,
        g73_to_g74_all_passed=g73_to_g74_all_passed,
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
        master_72_report=m72_report.to_dict(),
        g73_result=g73_res.to_dict(),
        g74_result=g74_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_74_master_safety_gates = evaluate_74gate_preflight
run_74_gate_preflight = evaluate_74gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_desqueeze_focusmap_simult_shocklesswb_and_74gate_guard",
        description=(
            "Phase 206 Safety Gates G73 ([De-Squeeze Display] 1.6x=1.65x 4-Locks & External "
            "M&C Focus Map <150fps Cutoff) + G74 ([Simult. + Auto Switch] Parity & [Shockless WB]) "
            "+ 74-Gate Master Safety Preflight"
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
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_74gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        _write_stdout_safe(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        _write_stdout_safe(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/74 "
            f"g73_to_g74_all_passed={report.g73_to_g74_all_passed} "
            f"all_74_gates_verified={report.all_74_gates_verified} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = report.all_74_gates_verified if args.dry_run_simulated else report.offline_71_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
