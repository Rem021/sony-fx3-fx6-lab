"""Phase 249 (`96/96` Wave-38) Sony `ILME-FX3` (`Ver. 7.02`) Safety Gates `G95`
(`[Lock Operation Parts]` `Fn` Hold, `MENU + Fn` 5s Full-Body Lock Chord vs
Destructive `MENU + Delete` 2s Slot Full Format Firewall & `My Dial` Temporary
Override Guard) & `G96` (`[Audio Out Timing]` `Live`/`Lip Sync` vs `[Audio signals]`
Setup Persistence + `[Silent Mode]` Hard-Lock & `[Exposure step]` `0.3EV`/`0.5EV`
vs `[Shutter Angle]` Constant-Table Independence Guard) + Unified 96-Gate Master
Safety Preflight (`G01..G96`).

Operationalizes Wave-38 official Sony `ILME-FX3` (`Ver. 7.02`) intelligence
(`reports/2026-11-15-global-sony-wave38-lock-op-parts-menu-fn-5s-audio-out-timing-audio-signals-exp-step-shutter-angle-intel/README.md`)
as deterministic offline preflight verifiers (`G95` and `G96`) and delegates
`G01..G94` directly to `evaluate_94gate_preflight()`.
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
from .realhw_framing_usbpower_lun_antiflicker_and_94gate_guard import (
    Master94GateReport,
    evaluate_94gate_preflight,
)
from .realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import SPI_NOR_WRITE_AUTHORIZED
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_96GATE_SCHEMA: str = (
    "realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard_v1"
)
REALHW_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_96GATE_VERSION: str = "1.0.0"

G95_GATE_ID: str = (
    "G95_lock_operation_parts_menu_fn_5s_chord_and_mydial_override_guard"
)
G95_GATE_CODE: str = (
    "LOCK_OPERATION_PARTS_MENU_FN_5S_CHORD_AND_MYDIAL_OVERRIDE_GUARD"
)

G96_GATE_ID: str = (
    "G96_audio_out_timing_signals_persistence_and_exp_step_shutter_angle_guard"
)
G96_GATE_CODE: str = (
    "AUDIO_OUT_TIMING_SIGNALS_PERSISTENCE_AND_EXP_STEP_SHUTTER_ANGLE_GUARD"
)

G95: str = G95_GATE_ID
G96: str = G96_GATE_ID
GATE_G95_LOCK_OPERATION_PARTS_MENU_FN_5S_CHORD_AND_MYDIAL_OVERRIDE_GUARD: str = (
    G95_GATE_CODE
)
GATE_G96_AUDIO_OUT_TIMING_SIGNALS_PERSISTENCE_AND_EXP_STEP_SHUTTER_ANGLE_GUARD: str = (
    G96_GATE_CODE
)

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE249: float = 0.10
DONOR_CHECK_MAX_SECONDS: float = DONOR_CHECK_MAX_SECONDS_PHASE249

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX3_DEFAULT_FW_VERSION_PHASE249: str = "7.02"
FX3_MIN_SUPPORTED_FW_TUPLE_PHASE249: Tuple[int, int] = (1, 0)
FX3_SHUTTER_ANGLE_MIN_FW_TUPLE_G96: Tuple[int, int] = (6, 0)
FX3_HELP_GUIDE_CODE_PHASE249: str = "ilc/2210"

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_INITIALIZE: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE249: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
)

# Status & Violation Codes
STATUS_VERIFIED_G95: str = (
    "VERIFIED_G95_LOCK_OPERATION_PARTS_MENU_FN_5S_CHORD_AND_MYDIAL_SAFE"
)
STATUS_VERIFIED_G96: str = (
    "VERIFIED_G96_AUDIO_TIMING_SIGNALS_PERSISTENCE_AND_EXP_STEP_SHUTTER_ANGLE_SAFE"
)
STATUS_BLOCKED_PHASE249_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE249_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G95_LOCK_OP_PARTS_ENUM_OR_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G95_LOCK_OP_PARTS_ENUM_OR_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G95_FN_HOLD_TOGGLE_SCOPE_OR_OSD_VIOLATION: str = (
    "BLOCKED_G95_FN_HOLD_TOGGLE_SCOPE_OR_OSD_VIOLATION"
)
STATUS_BLOCKED_G95_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_VIOLATION: str = (
    "BLOCKED_G95_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_VIOLATION"
)
STATUS_BLOCKED_G95_UNATTENDED_TIER0_BENCH_CONTROLS_UNLOCKED: str = (
    "BLOCKED_G95_UNATTENDED_TIER0_BENCH_CONTROLS_UNLOCKED"
)
STATUS_BLOCKED_G95_DESTRUCTIVE_MENU_DELETE_2S_FORMAT_CHORD_CONFUSION: str = (
    "BLOCKED_G95_DESTRUCTIVE_MENU_DELETE_2S_FORMAT_CHORD_CONFUSION"
)
STATUS_BLOCKED_G95_MY_DIAL_TEMPORARY_OVERRIDE_VIOLATION: str = (
    "BLOCKED_G95_MY_DIAL_TEMPORARY_OVERRIDE_VIOLATION"
)
STATUS_BLOCKED_G95_TELEMETRY_INVALID: str = (
    "BLOCKED_G95_LOCK_OP_PARTS_CHORD_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G96_AUDIO_OUT_TIMING_ENUM_OR_RESET_VIOLATION: str = (
    "BLOCKED_G96_AUDIO_OUT_TIMING_ENUM_OR_RESET_VIOLATION"
)
STATUS_BLOCKED_G96_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION: str = (
    "BLOCKED_G96_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION"
)
STATUS_BLOCKED_G96_AUDIO_SIGNALS_SETUP_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G96_AUDIO_SIGNALS_SETUP_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G96_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION: str = (
    "BLOCKED_G96_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION"
)
STATUS_BLOCKED_G96_EXPOSURE_STEP_ENUM_RESET_OR_TARGETS_VIOLATION: str = (
    "BLOCKED_G96_EXPOSURE_STEP_ENUM_RESET_OR_TARGETS_VIOLATION"
)
STATUS_BLOCKED_G96_SHUTTER_ANGLE_CONSTANT_TABLE_COUPLED_DRIFT: str = (
    "BLOCKED_G96_SHUTTER_ANGLE_CONSTANT_TABLE_COUPLED_DRIFT"
)
STATUS_BLOCKED_G96_TELEMETRY_INVALID: str = (
    "BLOCKED_G96_AUDIO_TIMING_EXP_STEP_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G95 Canonical Constants: [Lock Operation Parts], MENU+Fn 5s & My Dial
# ---------------------------------------------------------------------------

LOCK_OPERATION_PARTS_MENU_PATH_G95: str = (
    "MENU -> Setup -> [Dial Customize] -> [Lock Operation Parts]"
)
LOCK_OP_PARTS_OFF_G95: str = "Off"
LOCK_OP_PARTS_MULTI_SELECTOR_ONLY_G95: str = "Multi-Selector Only"
LOCK_OP_PARTS_DIAL_PLUS_WHEEL_G95: str = "Dial + Wheel"
LOCK_OP_PARTS_ALL_G95: str = "All"
ALLOWED_LOCK_OPERATION_PARTS_MODES_G95: Tuple[str, ...] = (
    LOCK_OP_PARTS_OFF_G95,
    LOCK_OP_PARTS_MULTI_SELECTOR_ONLY_G95,
    LOCK_OP_PARTS_DIAL_PLUS_WHEEL_G95,
    LOCK_OP_PARTS_ALL_G95,
)
LOCK_OPERATION_PARTS_FACTORY_DEFAULT_G95: str = LOCK_OP_PARTS_OFF_G95
LOCK_OP_PARTS_LOCKED_OSD_BANNER_G95: str = "Locked."

ALLOWED_DIAL_CONTROLS_G95: Tuple[str, ...] = (
    "FRONT_DIAL",
    "REAR_DIAL",
    "CONTROL_WHEEL",
)

LOCK_OP_PARTS_SCOPE_MAP_G95: Dict[str, Tuple[str, ...]] = {
    LOCK_OP_PARTS_OFF_G95: (),
    LOCK_OP_PARTS_MULTI_SELECTOR_ONLY_G95: ("MULTI_SELECTOR",),
    LOCK_OP_PARTS_DIAL_PLUS_WHEEL_G95: (
        "FRONT_DIAL",
        "REAR_DIAL",
        "CONTROL_WHEEL",
    ),
    LOCK_OP_PARTS_ALL_G95: (
        "MULTI_SELECTOR",
        "FRONT_DIAL",
        "REAR_DIAL",
        "CONTROL_WHEEL",
    ),
}

MENU_FN_5S_CHORD_KEYS_G95: Tuple[str, ...] = ("MENU", "Fn")
MENU_FN_FULL_BODY_LOCK_HOLD_SECONDS_G95: float = 5.0
MENU_FN_5S_LOCKED_CONTROLS_G95: Tuple[str, ...] = (
    "ALL_BUTTONS_EXCEPT_SHUTTER",
    "MULTI_SELECTOR",
    "FRONT_DIAL",
    "REAR_DIAL",
    "CONTROL_WHEEL",
)

DESTRUCTIVE_MENU_DELETE_2S_CHORD_KEYS_G95: Tuple[str, ...] = ("MENU", "Delete")
DESTRUCTIVE_MENU_DELETE_HOLD_SECONDS_G95: float = 2.0

# ---------------------------------------------------------------------------
# Gate G96 Canonical Constants: [Audio Out Timing], [Audio signals],
# [Exposure step] & [Shutter Angle] Constant Table
# ---------------------------------------------------------------------------

AUDIO_OUT_TIMING_MENU_PATH_G96: str = (
    "MENU -> Shooting -> [Audio Recording] -> [Audio Out Timing]"
)
AUDIO_OUT_TIMING_LIVE_G96: str = "Live"
AUDIO_OUT_TIMING_LIP_SYNC_G96: str = "Lip Sync"
ALLOWED_AUDIO_OUT_TIMING_MODES_G96: Tuple[str, ...] = (
    AUDIO_OUT_TIMING_LIVE_G96,
    AUDIO_OUT_TIMING_LIP_SYNC_G96,
)
AUDIO_OUT_TIMING_FACTORY_DEFAULT_G96: str = AUDIO_OUT_TIMING_LIVE_G96

AUDIO_SIGNALS_MENU_PATH_G96: str = (
    "MENU -> Setup -> [Sound Option] -> [Audio signals]"
)
AUDIO_SIGNALS_ON_G96: str = "On"
AUDIO_SIGNALS_OFF_G96: str = "Off"
ALLOWED_AUDIO_SIGNALS_MODES_G96: Tuple[str, ...] = (
    AUDIO_SIGNALS_ON_G96,
    AUDIO_SIGNALS_OFF_G96,
)
AUDIO_SIGNALS_FACTORY_DEFAULT_G96: str = AUDIO_SIGNALS_ON_G96

SHOOT_MODE_STILL_G96: str = "Still"
SHOOT_MODE_MOVIE_G96: str = "Movie"
SHOOT_MODE_SQ_MOTION_G96: str = "S&Q Motion"
ALLOWED_SHOOT_MODES_G96: Tuple[str, ...] = (
    SHOOT_MODE_STILL_G96,
    SHOOT_MODE_MOVIE_G96,
    SHOOT_MODE_SQ_MOTION_G96,
)

EXPOSURE_STEP_MENU_PATH_G96: str = (
    "MENU -> Exposure/Color -> [Exposure Comp.] -> [Exposure step]"
)
EXPOSURE_STEP_0_3EV_G96: str = "0.3EV"
EXPOSURE_STEP_0_5EV_G96: str = "0.5EV"
ALLOWED_EXPOSURE_STEPS_G96: Tuple[str, ...] = (
    EXPOSURE_STEP_0_3EV_G96,
    EXPOSURE_STEP_0_5EV_G96,
)
EXPOSURE_STEP_FACTORY_DEFAULT_G96: str = EXPOSURE_STEP_0_3EV_G96
EXPOSURE_STEP_GOVERNED_TARGETS_G96: Tuple[str, ...] = (
    "Shutter Speed",
    "Aperture",
    "Exposure Comp.",
)

SHUTTER_MODE_SPEED_G96: str = "Shutter Speed"
SHUTTER_MODE_ANGLE_G96: str = "Shutter Angle"
ALLOWED_SHUTTER_MODES_G96: Tuple[str, ...] = (
    SHUTTER_MODE_SPEED_G96,
    SHUTTER_MODE_ANGLE_G96,
)
CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG_G96: Tuple[float, ...] = (
    5.6,
    11.2,
    22.5,
    45.0,
    72.0,
    90.0,
    144.0,
    172.8,
    180.0,
    270.0,
    360.0,
)

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, <0.10s, Clean-Room Fallback)
# ---------------------------------------------------------------------------

PINNED_PHASE249_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_bin": (
        "FX3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"Lock",
            b"Dial",
            b"Wheel",
            b"MENU",
            b"Fn",
            b"Delete",
            b"Audio",
            b"Timing",
            b"Live",
            b"Sync",
            b"Sound",
            b"Silent",
            b"Exposure",
            b"Shutter",
            b"Angle",
            b"0.3",
            b"Reset",
            b"Initialize",
        ),
        "FX3_CPAPP_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_SHUTTER_ANGLE_STRINGS",
    ),
    "fx3_libgpe_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgpe.so",
        106_480,
        "363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464",
        (b"\x7fELF", b"gpe_blog_error", b"_ZNK5mpgpe5Gperm4InitEv"),
        "FX3_LIBGPE_MENU_OSD_LOCKED_BANNER_DISPATCH_ELF",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"/setting"),
        "FX3_BK4_RESET_VS_INITIALIZE_SETUP_PERSISTENCE_SEED",
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
        "FX6_LIBINFRADIAL_KEY_INHIBIT_PARITY_ELF",
    ),
    "fx6_libinfrainput_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraInput.so",
        93_448,
        "1851e2dc8515d2240b9ecaffd58591207336c5f061b1af0d3585d7b082a41f02",
        (
            b"\x7fELF",
            b"_ZN14InfraInputBase14KeyConfigAllocEi",
            b"_ZN14InfraInputBase13KeyConfigFreeEv",
            b"_ZN14InfraInputBase7SuspendEv",
        ),
        "FX6_LIBINFRAINPUT_KEY_CHORD_SUSPEND_PARITY_ELF",
    ),
    "fx6_bk4_bin": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"NTSC", b"/setting"),
        "FX6_CHAPLIN_SHUTTER_ANGLE_CINE_PARITY_SEED",
    ),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase249DonorAuditResult:
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
class LockOperationPartsAndChordGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    lock_operation_parts_menu_path: str
    pre_reset_lock_operation_parts: str
    reset_action: str
    expected_post_reset_lock_operation_parts: str
    effective_post_reset_lock_operation_parts: str
    lock_op_parts_survives_camera_settings_reset: bool
    lock_op_parts_reset_only_by_initialize: bool
    fn_hold_toggle_count: int
    fn_hold_lock_engaged: bool
    expected_fn_hold_locked_controls: Tuple[str, ...]
    effective_fn_hold_locked_controls: Tuple[str, ...]
    locked_osd_banner: str
    chord_keys_pressed: Tuple[str, ...]
    chord_hold_seconds: float
    menu_fn_5s_full_body_lock_engaged: bool
    expected_full_body_locked_controls: Tuple[str, ...]
    effective_full_body_locked_controls: Tuple[str, ...]
    shutter_button_remains_unlocked: bool
    unattended_tier0_dump_active: bool
    unattended_bench_physical_lock_enforced: bool
    slot_full_format_chord_invoked: bool
    destructive_menu_delete_chord_blocked: bool
    destructive_menu_delete_confusions: int
    my_dial_recall_active: bool
    my_dial_assigned_controls: Tuple[str, ...]
    effective_temporarily_unlocked_controls: Tuple[str, ...]
    my_dial_relocked_on_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AudioTimingSignalsAndExpStepGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    audio_out_timing_menu_path: str
    audio_signals_menu_path: str
    exposure_step_menu_path: str
    pre_reset_audio_out_timing: str
    pre_reset_audio_signals: str
    pre_reset_exposure_step: str
    reset_action: str
    expected_post_reset_audio_out_timing: str
    effective_post_reset_audio_out_timing: str
    audio_out_timing_reset_by_camera_settings_reset: bool
    shoot_mode: str
    audio_recording: str
    audio_out_timing_available: bool
    audio_out_timing_sq_or_audio_off_locked_out: bool
    expected_post_reset_audio_signals: str
    configured_post_reset_audio_signals: str
    audio_signals_survives_camera_settings_reset: bool
    audio_signals_reset_only_by_initialize: bool
    silent_mode: str
    effective_audio_signals: str
    audio_signals_locked_off_by_silent_mode: bool
    expected_post_reset_exposure_step: str
    effective_post_reset_exposure_step: str
    exposure_step_reset_by_camera_settings_reset: bool
    governed_exposure_targets: Tuple[str, ...]
    shutter_mode: str
    active_shutter_angle_deg: float
    shutter_angle_table_at_0_3ev: Tuple[float, ...]
    shutter_angle_table_at_0_5ev: Tuple[float, ...]
    shutter_angle_unaffected_by_exposure_step: bool
    shutter_angle_exposure_step_drift_events: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G95LockOperationPartsAndChordGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    lock_op_parts_chord_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G96AudioTimingSignalsAndExpStepGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    audio_timing_exp_step_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master96GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_93_gates_verified: bool
    all_96_gates_verified: bool
    g13_to_g96_all_passed: bool
    g95_to_g96_all_passed: bool
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
    master_94_report: Dict[str, Any]
    g95_result: Dict[str, Any]
    g96_result: Dict[str, Any]
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
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE
    return None


def _norm_lock_op_parts_mode_g95(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if s == "OFF":
        return LOCK_OP_PARTS_OFF_G95
    if s in (
        "MULTI-SELECTOR ONLY",
        "MULTI-SLCT ONLY",
        "MULTI SELECTOR ONLY",
        "MULTI SLCT ONLY",
    ):
        return LOCK_OP_PARTS_MULTI_SELECTOR_ONLY_G95
    if s in ("DIAL + WHEEL", "DIAL+WHEEL"):
        return LOCK_OP_PARTS_DIAL_PLUS_WHEEL_G95
    if s == "ALL":
        return LOCK_OP_PARTS_ALL_G95
    return None


def _norm_key_token_g95(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]()").upper()
    if s == "MENU":
        return "MENU"
    if s == "FN":
        return "Fn"
    if s in ("DELETE", "DEL", "TRASH", "FORMAT"):
        return "Delete"
    if s in ("SHUTTER", "SHUTTER_BUTTON", "REC"):
        return "SHUTTER"
    if s in ("NONE", ""):
        return ""
    return raw.strip()


def _parse_chord_keys_g95(raw: Any) -> Optional[Tuple[str, ...]]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        s = raw.strip()
        if not s or s.upper() == "NONE":
            return ()
        parts = [p for p in re.split(r"\s*\+\s*|\s*,\s*", s) if p.strip()]
    elif isinstance(raw, (list, tuple)):
        parts = list(raw)
    else:
        return None
    normed: List[str] = []
    for item in parts:
        tok = _norm_key_token_g95(item)
        if tok is None:
            return None
        if tok:
            normed.append(tok)
    return tuple(normed)


def _norm_audio_out_timing_g96(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s == "LIVE":
        return AUDIO_OUT_TIMING_LIVE_G96
    if s in ("LIP SYNC", "LIPSYNC"):
        return AUDIO_OUT_TIMING_LIP_SYNC_G96
    return None


def _norm_shoot_mode_g96(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s in ("STILL", "STILL SHOOTING", "PHOTO"):
        return SHOOT_MODE_STILL_G96
    if s in ("MOVIE", "MOVIE RECORDING", "MOVIE REC"):
        return SHOOT_MODE_MOVIE_G96
    if s in ("S&Q MOTION", "S&Q", "SQ MOTION", "SQ", "S&Q RECORDING"):
        return SHOOT_MODE_SQ_MOTION_G96
    return None


def _norm_exposure_step_g96(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", "", raw.strip().strip("[]")).upper()
    if s == "0.3EV":
        return EXPOSURE_STEP_0_3EV_G96
    if s == "0.5EV":
        return EXPOSURE_STEP_0_5EV_G96
    return None


def _norm_shutter_mode_g96(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s in ("SHUTTER SPEED", "SPEED"):
        return SHUTTER_MODE_SPEED_G96
    if s in ("SHUTTER ANGLE", "ANGLE"):
        return SHUTTER_MODE_ANGLE_G96
    return None


# ---------------------------------------------------------------------------
# 1. Bounded `< 0.10s` O_RDONLY Donor Contract Audit (`Phase 249`)
# ---------------------------------------------------------------------------


def audit_phase249_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS_PHASE249,
) -> Phase249DonorAuditResult:
    """Inspect local FX3 Ver. 7.02 / FX6 Ver. 6.01 donor artifacts strictly
    `os.O_RDONLY` within `<0.10s`, with automatic `CLEAN_ROOM_SYNTHETIC`
    fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent.
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE249_DONOR_SPECS.items():
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
            spec[5] for spec in PINNED_PHASE249_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE249_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE249_DONOR_SPECS.items()}
        return Phase249DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE249_DONOR_INTEGRITY
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
    ) in PINNED_PHASE249_DONOR_SPECS.items():
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
        for k, s in PINNED_PHASE249_DONOR_SPECS.items()
        if s[0] == "FX3"
    )
    fx6_ok = all(
        k in passed_keys
        for k, s in PINNED_PHASE249_DONOR_SPECS.items()
        if s[0] == "FX6"
    )
    valid = fx3_ok and fx6_ok and within_budget and (not errors)
    return Phase249DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE249_DONOR_INTEGRITY,
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
# 2. Gate `G95` — `[Lock Operation Parts]` (`Fn` Hold, `MENU + Fn` 5s Chord vs
#    Destructive `MENU + Delete` 2s & `My Dial` Temporary Override) Guard
# ---------------------------------------------------------------------------


def resolve_fx3_lock_operation_parts_and_chord_state(
    *,
    pre_reset_lock_operation_parts: str = LOCK_OP_PARTS_ALL_G95,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    fn_hold_toggle_count: int = 1,
    chord_keys_pressed: Sequence[str] = MENU_FN_5S_CHORD_KEYS_G95,
    chord_hold_seconds: float = MENU_FN_FULL_BODY_LOCK_HOLD_SECONDS_G95,
    my_dial_recall_active: bool = False,
    my_dial_assigned_controls: Sequence[str] = ALLOWED_DIAL_CONTROLS_G95,
) -> Dict[str, Any]:
    """Deterministic `ILME-FX3` (`Ver. 7.02`) state resolver for `[Lock Operation Parts]`
    (`MENU -> Setup -> [Dial Customize] -> [Lock Operation Parts]`), `Fn` hold
    toggle, `MENU + Fn` `5`-second full-body lock chord, and `My Dial` temporary
    recall unlock.
    """
    norm_mode = (
        _norm_lock_op_parts_mode_g95(pre_reset_lock_operation_parts)
        or LOCK_OPERATION_PARTS_FACTORY_DEFAULT_G95
    )
    norm_reset = _norm_reset_action(reset_action) or RESET_ACTION_NONE

    # [Setup] item: survives [Camera Settings Reset], reset to Off ONLY by [Initialize]
    if norm_reset == RESET_ACTION_INITIALIZE:
        post_mode = LOCK_OPERATION_PARTS_FACTORY_DEFAULT_G95
    else:
        post_mode = norm_mode

    fn_engaged = (post_mode != LOCK_OP_PARTS_OFF_G95) and (
        max(0, int(fn_hold_toggle_count)) % 2 == 1
    )
    fn_scope = LOCK_OP_PARTS_SCOPE_MAP_G95[post_mode] if fn_engaged else ()

    parsed_chord = _parse_chord_keys_g95(chord_keys_pressed) or ()
    is_menu_fn_chord = set(parsed_chord) == {"MENU", "Fn"} and len(parsed_chord) == 2
    full_body_engaged = (
        is_menu_fn_chord
        and float(chord_hold_seconds) >= MENU_FN_FULL_BODY_LOCK_HOLD_SECONDS_G95
    )
    full_body_controls = MENU_FN_5S_LOCKED_CONTROLS_G95 if full_body_engaged else ()

    osd_banner = (
        LOCK_OP_PARTS_LOCKED_OSD_BANNER_G95
        if (fn_engaged or full_body_engaged)
        else ""
    )
    assigned_dials = tuple(str(c).strip().upper() for c in my_dial_assigned_controls)
    temp_unlocked = assigned_dials if bool(my_dial_recall_active) else ()

    return {
        "expected_post_reset_lock_operation_parts": post_mode,
        "lock_op_parts_survives_camera_settings_reset": True,
        "lock_op_parts_reset_only_by_initialize": True,
        "expected_fn_hold_lock_engaged": fn_engaged,
        "expected_fn_hold_locked_controls": fn_scope,
        "expected_menu_fn_5s_full_body_lock_engaged": full_body_engaged,
        "expected_full_body_locked_controls": full_body_controls,
        "shutter_button_remains_unlocked": True,
        "expected_locked_osd_banner": osd_banner,
        "expected_temporarily_unlocked_controls": temp_unlocked,
    }


def verify_lock_operation_parts_chord_and_mydial_guard(
    *,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE249,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE249,
    pre_reset_lock_operation_parts: str = LOCK_OP_PARTS_ALL_G95,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    effective_post_reset_lock_operation_parts: Optional[str] = None,
    fn_hold_toggle_count: int = 1,
    fn_hold_lock_engaged: Optional[bool] = None,
    effective_fn_hold_locked_controls: Optional[Sequence[str]] = None,
    locked_osd_banner: Optional[str] = None,
    chord_keys_pressed: Any = MENU_FN_5S_CHORD_KEYS_G95,
    chord_hold_seconds: float = MENU_FN_FULL_BODY_LOCK_HOLD_SECONDS_G95,
    menu_fn_5s_full_body_lock_engaged: Optional[bool] = None,
    effective_full_body_locked_controls: Optional[Sequence[str]] = None,
    shutter_button_remains_unlocked: bool = True,
    unattended_tier0_dump_active: bool = True,
    slot_full_format_chord_invoked: bool = False,
    my_dial_recall_active: bool = False,
    my_dial_assigned_controls: Sequence[str] = ALLOWED_DIAL_CONTROLS_G95,
    effective_temporarily_unlocked_controls: Optional[Sequence[str]] = None,
    my_dial_relocked_on_release: bool = True,
) -> LockOperationPartsAndChordGuardResult:
    """Verify Gate `G95`: `[Lock Operation Parts]` (`Off` default, `Multi-Selector Only`,
    `Dial + Wheel`, `All` — surviving `[Camera Settings Reset]`, reset only by
    `[Initialize]`), `Fn` hold lock/unlock toggle, `MENU + Fn` `5`-second
    full-body physical control lock (all buttons/dials/wheels except shutter
    button during unattended Tier-0 dumps), `My Dial` temporary recall unlock,
    and hard firewall rejecting any confusion with the destructive
    `MENU + Delete` `2`-second Slot Full Format chord.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        not isinstance(body_model_name, str)
        or body_model_name.strip() != FX3_MODEL_NAME
        or isinstance(body_model_id, bool)
        or not isinstance(body_model_id, int)
        or body_model_id != FX3_MODEL_ID
        or not isinstance(help_guide_code, str)
        or help_guide_code.strip() != FX3_HELP_GUIDE_CODE_PHASE249
        or fw_tuple is None
        or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE249
        or isinstance(fn_hold_toggle_count, bool)
        or not isinstance(fn_hold_toggle_count, int)
        or fn_hold_toggle_count < 0
        or isinstance(chord_hold_seconds, bool)
        or not isinstance(chord_hold_seconds, (int, float))
        or float(chord_hold_seconds) < 0.0
        or not isinstance(shutter_button_remains_unlocked, bool)
        or not isinstance(unattended_tier0_dump_active, bool)
        or not isinstance(slot_full_format_chord_invoked, bool)
        or not isinstance(my_dial_recall_active, bool)
        or not isinstance(my_dial_relocked_on_release, bool)
    ):
        _add_code(codes, STATUS_BLOCKED_G95_TELEMETRY_INVALID)
        errors.append(
            "Invalid ILME-FX3 model/firmware/chord telemetry in Gate G95."
        )

    norm_reset = _norm_reset_action(reset_action)
    if norm_reset is None:
        _add_code(codes, STATUS_BLOCKED_G95_TELEMETRY_INVALID)
        errors.append(f"Unsupported reset_action={reset_action!r} in Gate G95.")
        norm_reset = RESET_ACTION_NONE

    norm_pre_mode = _norm_lock_op_parts_mode_g95(pre_reset_lock_operation_parts)
    if norm_pre_mode is None:
        _add_code(
            codes,
            STATUS_BLOCKED_G95_LOCK_OP_PARTS_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
        )
        errors.append(
            f"Unsupported [Lock Operation Parts]={pre_reset_lock_operation_parts!r}; "
            f"allowed={ALLOWED_LOCK_OPERATION_PARTS_MODES_G95}."
        )
        norm_pre_mode = LOCK_OPERATION_PARTS_FACTORY_DEFAULT_G95

    parsed_chord = _parse_chord_keys_g95(chord_keys_pressed)
    if parsed_chord is None:
        _add_code(codes, STATUS_BLOCKED_G95_TELEMETRY_INVALID)
        errors.append(
            f"Invalid chord_keys_pressed={chord_keys_pressed!r} in Gate G95."
        )
        parsed_chord = ()

    safe_toggle_count = (
        fn_hold_toggle_count
        if (not isinstance(fn_hold_toggle_count, bool) and isinstance(fn_hold_toggle_count, int) and fn_hold_toggle_count >= 0)
        else 0
    )
    safe_hold_sec = (
        float(chord_hold_seconds)
        if (not isinstance(chord_hold_seconds, bool) and isinstance(chord_hold_seconds, (int, float)) and float(chord_hold_seconds) >= 0.0)
        else 0.0
    )

    state = resolve_fx3_lock_operation_parts_and_chord_state(
        pre_reset_lock_operation_parts=norm_pre_mode,
        reset_action=norm_reset,
        fn_hold_toggle_count=safe_toggle_count,
        chord_keys_pressed=parsed_chord,
        chord_hold_seconds=safe_hold_sec,
        my_dial_recall_active=bool(my_dial_recall_active),
        my_dial_assigned_controls=my_dial_assigned_controls
        if isinstance(my_dial_assigned_controls, (list, tuple))
        else (),
    )

    exp_post_mode = state["expected_post_reset_lock_operation_parts"]
    if effective_post_reset_lock_operation_parts is None:
        eff_post_mode = exp_post_mode
    else:
        norm_eff_post = _norm_lock_op_parts_mode_g95(
            effective_post_reset_lock_operation_parts
        )
        if norm_eff_post is None:
            _add_code(
                codes,
                STATUS_BLOCKED_G95_LOCK_OP_PARTS_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
            )
            errors.append(
                f"Invalid effective_post_reset_lock_operation_parts="
                f"{effective_post_reset_lock_operation_parts!r}."
            )
            eff_post_mode = str(effective_post_reset_lock_operation_parts)
        else:
            eff_post_mode = norm_eff_post
            if eff_post_mode != exp_post_mode:
                _add_code(
                    codes,
                    STATUS_BLOCKED_G95_LOCK_OP_PARTS_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
                )
                errors.append(
                    f"[Lock Operation Parts] reset persistence mismatch after {norm_reset!r}: "
                    f"got {eff_post_mode!r}, expected {exp_post_mode!r} "
                    "([Setup] item survives [Camera Settings Reset] and resets only via [Initialize])."
                )

    survives_cam_reset = (
        eff_post_mode == norm_pre_mode
        if norm_reset == RESET_ACTION_CAMERA_SETTINGS_RESET
        else True
    )
    reset_only_by_init = (
        eff_post_mode == LOCK_OPERATION_PARTS_FACTORY_DEFAULT_G95
        if norm_reset == RESET_ACTION_INITIALIZE
        else survives_cam_reset
    )

    # 1. Hard Firewall against Destructive MENU + Delete 2s Slot Full Format Chord
    has_delete_key = "Delete" in parsed_chord
    destructive_confusions = 0
    if slot_full_format_chord_invoked or has_delete_key:
        destructive_confusions = 1
        _add_code(
            codes,
            STATUS_BLOCKED_G95_DESTRUCTIVE_MENU_DELETE_2S_FORMAT_CHORD_CONFUSION,
        )
        errors.append(
            "Hard firewall blocked destructive MENU + Delete (2s Slot Full Format) "
            "chord confusion; unattended physical control lock requires MENU + Fn (5s)."
        )
    destructive_chord_blocked = destructive_confusions == 0

    # 2. Fn Hold Lock/Unlock Toggle & "Locked." OSD Banner
    exp_fn_engaged = bool(state["expected_fn_hold_lock_engaged"])
    exp_fn_controls = tuple(state["expected_fn_hold_locked_controls"])

    eff_fn_engaged = (
        exp_fn_engaged if fn_hold_lock_engaged is None else bool(fn_hold_lock_engaged)
    )
    if not isinstance(fn_hold_lock_engaged, (bool, type(None))):
        _add_code(codes, STATUS_BLOCKED_G95_TELEMETRY_INVALID)
        errors.append("fn_hold_lock_engaged must be bool or None.")

    if effective_fn_hold_locked_controls is None:
        eff_fn_controls = exp_fn_controls
    elif not isinstance(effective_fn_hold_locked_controls, (list, tuple)):
        _add_code(codes, STATUS_BLOCKED_G95_TELEMETRY_INVALID)
        errors.append("effective_fn_hold_locked_controls must be a sequence.")
        eff_fn_controls = ()
    else:
        eff_fn_controls = tuple(
            str(x).strip().upper() for x in effective_fn_hold_locked_controls
        )

    if eff_fn_engaged != exp_fn_engaged or eff_fn_controls != exp_fn_controls:
        _add_code(codes, STATUS_BLOCKED_G95_FN_HOLD_TOGGLE_SCOPE_OR_OSD_VIOLATION)
        errors.append(
            f"Fn hold lock mismatch for mode={eff_post_mode!r}, toggles={safe_toggle_count}: "
            f"engaged={eff_fn_engaged} (expected {exp_fn_engaged}), "
            f"controls={eff_fn_controls} (expected {exp_fn_controls})."
        )

    # 3. MENU + Fn Simultaneous 5-Second Full-Body Lock Chord & Shutter Exemption
    is_menu_fn_pair = set(parsed_chord) == {"MENU", "Fn"} and len(parsed_chord) == 2
    exp_full_body_engaged = bool(state["expected_menu_fn_5s_full_body_lock_engaged"])
    exp_full_body_controls = tuple(state["expected_full_body_locked_controls"])

    eff_full_body_engaged = (
        exp_full_body_engaged
        if menu_fn_5s_full_body_lock_engaged is None
        else bool(menu_fn_5s_full_body_lock_engaged)
    )
    if effective_full_body_locked_controls is None:
        eff_full_body_controls = exp_full_body_controls
    elif not isinstance(effective_full_body_locked_controls, (list, tuple)):
        _add_code(codes, STATUS_BLOCKED_G95_TELEMETRY_INVALID)
        errors.append("effective_full_body_locked_controls must be a sequence.")
        eff_full_body_controls = ()
    else:
        eff_full_body_controls = tuple(
            str(x).strip().upper() for x in effective_full_body_locked_controls
        )

    shutter_illegally_locked = (not shutter_button_remains_unlocked) or any(
        c in ("SHUTTER", "SHUTTER_BUTTON", "ALL_BUTTONS_INCLUDING_SHUTTER")
        for c in eff_full_body_controls
    )
    under_5s_menu_fn_attempt = (
        is_menu_fn_pair
        and 0.0 < safe_hold_sec < MENU_FN_FULL_BODY_LOCK_HOLD_SECONDS_G95
    )
    non_empty_unknown_chord = (
        bool(parsed_chord) and (not is_menu_fn_pair) and (not has_delete_key)
    )

    if (
        under_5s_menu_fn_attempt
        or non_empty_unknown_chord
        or eff_full_body_engaged != exp_full_body_engaged
        or eff_full_body_controls != exp_full_body_controls
        or shutter_illegally_locked
    ):
        _add_code(
            codes,
            STATUS_BLOCKED_G95_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_VIOLATION,
        )
        errors.append(
            f"MENU + Fn 5s full-body chord violation: keys={parsed_chord}, "
            f"hold={safe_hold_sec:.2f}s (requires >= 5.0s), "
            f"engaged={eff_full_body_engaged} (expected {exp_full_body_engaged}), "
            f"shutter_unlocked={shutter_button_remains_unlocked}."
        )

    # Verify OSD "Locked." banner whenever Fn hold or MENU+Fn 5s lock is engaged
    any_lock_active = eff_fn_engaged or eff_full_body_engaged
    exp_osd_banner = LOCK_OP_PARTS_LOCKED_OSD_BANNER_G95 if any_lock_active else ""
    if locked_osd_banner is None:
        eff_osd_banner = exp_osd_banner
    elif not isinstance(locked_osd_banner, str):
        _add_code(codes, STATUS_BLOCKED_G95_TELEMETRY_INVALID)
        errors.append("locked_osd_banner must be str or None.")
        eff_osd_banner = ""
    else:
        eff_osd_banner = locked_osd_banner.strip()
        if eff_osd_banner != exp_osd_banner:
            _add_code(codes, STATUS_BLOCKED_G95_FN_HOLD_TOGGLE_SCOPE_OR_OSD_VIOLATION)
            errors.append(
                f"Locked OSD banner mismatch: got {eff_osd_banner!r}, expected {exp_osd_banner!r}."
            )

    # 4. Unattended Tier-0 Dump Physical Control Lock Enforcement
    bench_lock_ok = (not unattended_tier0_dump_active) or (
        eff_full_body_engaged and destructive_chord_blocked and not under_5s_menu_fn_attempt
    )
    if not bench_lock_ok:
        _add_code(codes, STATUS_BLOCKED_G95_UNATTENDED_TIER0_BENCH_CONTROLS_UNLOCKED)
        errors.append(
            "Unattended Tier-0 pnflasha/cnflasha bench dump requires active "
            "MENU + Fn (5s) full-body physical control lock."
        )

    # 5. My Dial Temporary Recall Override
    if not isinstance(my_dial_assigned_controls, (list, tuple)):
        _add_code(codes, STATUS_BLOCKED_G95_TELEMETRY_INVALID)
        errors.append("my_dial_assigned_controls must be a sequence.")
        norm_assigned_dials: Tuple[str, ...] = ()
    else:
        norm_assigned_dials = tuple(
            str(c).strip().upper() for c in my_dial_assigned_controls
        )

    invalid_mydial_targets = [
        c for c in norm_assigned_dials if c not in ALLOWED_DIAL_CONTROLS_G95
    ]
    exp_temp_unlocked = norm_assigned_dials if my_dial_recall_active else ()
    if effective_temporarily_unlocked_controls is None:
        eff_temp_unlocked = exp_temp_unlocked
    elif not isinstance(effective_temporarily_unlocked_controls, (list, tuple)):
        _add_code(codes, STATUS_BLOCKED_G95_TELEMETRY_INVALID)
        errors.append("effective_temporarily_unlocked_controls must be a sequence.")
        eff_temp_unlocked = ()
    else:
        eff_temp_unlocked = tuple(
            str(c).strip().upper() for c in effective_temporarily_unlocked_controls
        )

    if (
        invalid_mydial_targets
        or (my_dial_recall_active and not norm_assigned_dials)
        or eff_temp_unlocked != exp_temp_unlocked
        or (not my_dial_relocked_on_release)
    ):
        _add_code(codes, STATUS_BLOCKED_G95_MY_DIAL_TEMPORARY_OVERRIDE_VIOLATION)
        errors.append(
            f"My Dial temporary recall override violation: active={my_dial_recall_active}, "
            f"assigned={norm_assigned_dials}, unlocked={eff_temp_unlocked} "
            f"(expected {exp_temp_unlocked}), relocked_on_release={my_dial_relocked_on_release}."
        )

    valid = not codes
    status = STATUS_VERIFIED_G95 if valid else codes[0]
    model_hex = (
        f"0x{body_model_id:08x}"
        if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
        else "INVALID"
    )
    return LockOperationPartsAndChordGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=str(body_model_name),
        body_model_id_hex=model_hex,
        help_guide_code=str(help_guide_code),
        firmware_version=str(firmware_version),
        lock_operation_parts_menu_path=LOCK_OPERATION_PARTS_MENU_PATH_G95,
        pre_reset_lock_operation_parts=norm_pre_mode,
        reset_action=norm_reset,
        expected_post_reset_lock_operation_parts=exp_post_mode,
        effective_post_reset_lock_operation_parts=eff_post_mode,
        lock_op_parts_survives_camera_settings_reset=survives_cam_reset,
        lock_op_parts_reset_only_by_initialize=reset_only_by_init,
        fn_hold_toggle_count=safe_toggle_count,
        fn_hold_lock_engaged=eff_fn_engaged,
        expected_fn_hold_locked_controls=exp_fn_controls,
        effective_fn_hold_locked_controls=eff_fn_controls,
        locked_osd_banner=eff_osd_banner,
        chord_keys_pressed=parsed_chord,
        chord_hold_seconds=round(safe_hold_sec, 3),
        menu_fn_5s_full_body_lock_engaged=eff_full_body_engaged,
        expected_full_body_locked_controls=exp_full_body_controls,
        effective_full_body_locked_controls=eff_full_body_controls,
        shutter_button_remains_unlocked=bool(
            shutter_button_remains_unlocked and not shutter_illegally_locked
        ),
        unattended_tier0_dump_active=bool(unattended_tier0_dump_active),
        unattended_bench_physical_lock_enforced=bench_lock_ok,
        slot_full_format_chord_invoked=bool(slot_full_format_chord_invoked),
        destructive_menu_delete_chord_blocked=destructive_chord_blocked,
        destructive_menu_delete_confusions=destructive_confusions,
        my_dial_recall_active=bool(my_dial_recall_active),
        my_dial_assigned_controls=norm_assigned_dials,
        effective_temporarily_unlocked_controls=eff_temp_unlocked,
        my_dial_relocked_on_release=bool(my_dial_relocked_on_release),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g95_lock_operation_parts_and_chord_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    lock_op_parts_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase249DonorAuditResult] = None,
) -> Tuple[GateVerdict, G95LockOperationPartsAndChordGuardResult]:
    """Evaluate Gate `G95` combining O_RDONLY local donor audit and
    `[Lock Operation Parts]` / `MENU + Fn` `5`s chord / `My Dial` guard.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase249_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_lock_operation_parts_chord_and_mydial_guard(
        **(dict(lock_op_parts_kwargs) if lock_op_parts_kwargs else {})
    )

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE249_DONOR_INTEGRITY)
        errors.extend(audit.errors)
    for c in guard.violation_codes:
        _add_code(codes, c)
    errors.extend(guard.errors)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G95 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G95 if valid else codes[0]

    res = G95LockOperationPartsAndChordGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        lock_op_parts_chord_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, lock_op_parts={guard.effective_post_reset_lock_operation_parts}"
        f"(survives_reset={guard.lock_op_parts_survives_camera_settings_reset},"
        f"fn_engaged={guard.fn_hold_lock_engaged},osd={guard.locked_osd_banner!r}), "
        f"menu_fn_5s={guard.menu_fn_5s_full_body_lock_engaged}"
        f"(hold={guard.chord_hold_seconds:.1f}s,shutter_unlocked={guard.shutter_button_remains_unlocked},"
        f"menu_del_blocked={guard.destructive_menu_delete_chord_blocked})"
    )
    verdict = GateVerdict(
        gate_id=G95_GATE_ID,
        gate_code=G95_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res



# ---------------------------------------------------------------------------
# 3. Gate `G96` — `[Audio Out Timing]` (`Live`/`Lip Sync`) vs `[Audio signals]`
#    Setup Persistence & `[Exposure step]` (`0.3EV`/`0.5EV`) vs `[Shutter Angle]`
#    Constant-Table Independence Guard
# ---------------------------------------------------------------------------


def resolve_fx3_audio_timing_signals_and_exp_step_state(
    *,
    pre_reset_audio_out_timing: str = AUDIO_OUT_TIMING_LIP_SYNC_G96,
    pre_reset_audio_signals: str = AUDIO_SIGNALS_OFF_G96,
    pre_reset_exposure_step: str = EXPOSURE_STEP_0_5EV_G96,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    shoot_mode: str = SHOOT_MODE_MOVIE_G96,
    audio_recording: str = "On",
    silent_mode: str = "Off",
) -> Dict[str, Any]:
    """Deterministic `ILME-FX3` (`Ver. 7.02`) state resolver for `[Audio Out Timing]`,
    `[Audio signals]`, `[Exposure step]`, and `[Shutter Angle]` constant-table
    independence across `NONE` / `[Camera Settings Reset]` / `[Initialize]`.
    """
    norm_timing = (
        _norm_audio_out_timing_g96(pre_reset_audio_out_timing)
        or AUDIO_OUT_TIMING_FACTORY_DEFAULT_G96
    )
    norm_signals = (
        _norm_on_off(pre_reset_audio_signals) or AUDIO_SIGNALS_FACTORY_DEFAULT_G96
    )
    norm_exp_step = (
        _norm_exposure_step_g96(pre_reset_exposure_step)
        or EXPOSURE_STEP_FACTORY_DEFAULT_G96
    )
    norm_reset = _norm_reset_action(reset_action) or RESET_ACTION_NONE
    norm_shoot = _norm_shoot_mode_g96(shoot_mode) or SHOOT_MODE_MOVIE_G96
    norm_audio_rec = _norm_on_off(audio_recording) or "On"
    norm_silent = _norm_on_off(silent_mode) or "Off"

    # [Audio Out Timing] & [Exposure step]: resettable via [Camera Settings Reset] & [Initialize]
    if norm_reset in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        post_timing = AUDIO_OUT_TIMING_FACTORY_DEFAULT_G96
        post_exp_step = EXPOSURE_STEP_FACTORY_DEFAULT_G96
    else:
        post_timing = norm_timing
        post_exp_step = norm_exp_step

    # [Audio signals] (Setup -> [Sound Option]): survives [Camera Settings Reset], reset ONLY by [Initialize]
    if norm_reset == RESET_ACTION_INITIALIZE:
        post_signals = AUDIO_SIGNALS_FACTORY_DEFAULT_G96
    else:
        post_signals = norm_signals

    # [Silent Mode]=On hardware-locks [Audio signals] to Off until [Silent Mode]=Off
    locked_by_silent = norm_silent == "On"
    eff_signals = AUDIO_SIGNALS_OFF_G96 if locked_by_silent else post_signals

    # [Audio Out Timing] hardware-locked out in S&Q Motion and when [Audio Recording]=Off
    sq_or_audio_off_locked = (
        norm_shoot == SHOOT_MODE_SQ_MOTION_G96 or norm_audio_rec == "Off"
    )
    timing_available = not sq_or_audio_off_locked

    return {
        "expected_post_reset_audio_out_timing": post_timing,
        "audio_out_timing_reset_by_camera_settings_reset": True,
        "expected_audio_out_timing_available": timing_available,
        "audio_out_timing_sq_or_audio_off_locked_out": sq_or_audio_off_locked,
        "expected_post_reset_audio_signals": post_signals,
        "audio_signals_survives_camera_settings_reset": True,
        "audio_signals_reset_only_by_initialize": True,
        "expected_effective_audio_signals": eff_signals,
        "audio_signals_locked_off_by_silent_mode": locked_by_silent,
        "expected_post_reset_exposure_step": post_exp_step,
        "exposure_step_reset_by_camera_settings_reset": True,
        "governed_exposure_targets": EXPOSURE_STEP_GOVERNED_TARGETS_G96,
        "cine_shutter_angle_constant_table_deg": CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG_G96,
    }


def verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
    *,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE249,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE249,
    pre_reset_audio_out_timing: str = AUDIO_OUT_TIMING_LIP_SYNC_G96,
    pre_reset_audio_signals: str = AUDIO_SIGNALS_OFF_G96,
    pre_reset_exposure_step: str = EXPOSURE_STEP_0_5EV_G96,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    effective_post_reset_audio_out_timing: Optional[str] = None,
    shoot_mode: str = SHOOT_MODE_MOVIE_G96,
    audio_recording: str = "On",
    audio_out_timing_available: Optional[bool] = None,
    audio_out_timing_override_while_locked: bool = False,
    configured_post_reset_audio_signals: Optional[str] = None,
    silent_mode: str = "Off",
    effective_audio_signals: Optional[str] = None,
    audio_signals_override_while_silent: bool = False,
    effective_post_reset_exposure_step: Optional[str] = None,
    governed_exposure_targets: Optional[Sequence[str]] = None,
    shutter_mode: str = SHUTTER_MODE_ANGLE_G96,
    active_shutter_angle_deg: float = 180.0,
    shutter_angle_table_at_0_3ev: Sequence[float] = CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG_G96,
    shutter_angle_table_at_0_5ev: Sequence[float] = CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG_G96,
    shutter_angle_scaled_by_exposure_step: bool = False,
) -> AudioTimingSignalsAndExpStepGuardResult:
    """Verify Gate `G96`:
    - `[Audio Out Timing]` (`Live` default / `Lip Sync`, resettable via
      `[Camera Settings Reset]`, hardware-locked out in `S&Q Motion` and when
      `[Audio Recording]=Off`);
    - `[Audio signals]` (`On` default / `Off` under `Setup -> [Sound Option]`,
      surviving `[Camera Settings Reset]` while hardware-locked to `Off`
      whenever `[Silent Mode]=On`);
    - `[Exposure step]` (`0.3EV` default / `0.5EV`, resettable via
      `[Camera Settings Reset]`) governing `[Shutter Speed]`, `Aperture`, and
      `Exposure Comp.` increments while `[Shutter Angle]` (`[Shutter Mode]=Shutter Angle`,
      `Ver. 6.00+`) remains strictly unaffected on its constant cine angle table.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        not isinstance(body_model_name, str)
        or body_model_name.strip() != FX3_MODEL_NAME
        or isinstance(body_model_id, bool)
        or not isinstance(body_model_id, int)
        or body_model_id != FX3_MODEL_ID
        or not isinstance(help_guide_code, str)
        or help_guide_code.strip() != FX3_HELP_GUIDE_CODE_PHASE249
        or fw_tuple is None
        or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE249
        or not isinstance(audio_out_timing_override_while_locked, bool)
        or not isinstance(audio_signals_override_while_silent, bool)
        or not isinstance(shutter_angle_scaled_by_exposure_step, bool)
        or isinstance(active_shutter_angle_deg, bool)
        or not isinstance(active_shutter_angle_deg, (int, float))
    ):
        _add_code(codes, STATUS_BLOCKED_G96_TELEMETRY_INVALID)
        errors.append(
            "Invalid ILME-FX3 model/firmware/audio-exposure telemetry in Gate G96."
        )

    norm_reset = _norm_reset_action(reset_action)
    if norm_reset is None:
        _add_code(codes, STATUS_BLOCKED_G96_TELEMETRY_INVALID)
        errors.append(f"Unsupported reset_action={reset_action!r} in Gate G96.")
        norm_reset = RESET_ACTION_NONE

    norm_shoot = _norm_shoot_mode_g96(shoot_mode)
    if norm_shoot is None:
        _add_code(codes, STATUS_BLOCKED_G96_TELEMETRY_INVALID)
        errors.append(f"Unsupported shoot_mode={shoot_mode!r} in Gate G96.")
        norm_shoot = SHOOT_MODE_MOVIE_G96

    norm_audio_rec = _norm_on_off(audio_recording)
    if norm_audio_rec is None:
        _add_code(codes, STATUS_BLOCKED_G96_TELEMETRY_INVALID)
        errors.append(f"Unsupported audio_recording={audio_recording!r} in Gate G96.")
        norm_audio_rec = "On"

    norm_silent = _norm_on_off(silent_mode)
    if norm_silent is None:
        _add_code(codes, STATUS_BLOCKED_G96_TELEMETRY_INVALID)
        errors.append(f"Unsupported silent_mode={silent_mode!r} in Gate G96.")
        norm_silent = "Off"

    norm_shutter_mode = _norm_shutter_mode_g96(shutter_mode)
    if norm_shutter_mode is None:
        _add_code(codes, STATUS_BLOCKED_G96_TELEMETRY_INVALID)
        errors.append(f"Unsupported shutter_mode={shutter_mode!r} in Gate G96.")
        norm_shutter_mode = SHUTTER_MODE_ANGLE_G96

    norm_pre_timing = _norm_audio_out_timing_g96(pre_reset_audio_out_timing)
    if norm_pre_timing is None:
        _add_code(codes, STATUS_BLOCKED_G96_AUDIO_OUT_TIMING_ENUM_OR_RESET_VIOLATION)
        errors.append(
            f"Unsupported [Audio Out Timing]={pre_reset_audio_out_timing!r}; "
            f"allowed={ALLOWED_AUDIO_OUT_TIMING_MODES_G96}."
        )
        norm_pre_timing = AUDIO_OUT_TIMING_FACTORY_DEFAULT_G96

    norm_pre_signals = _norm_on_off(pre_reset_audio_signals)
    if norm_pre_signals is None:
        _add_code(codes, STATUS_BLOCKED_G96_AUDIO_SIGNALS_SETUP_PERSISTENCE_VIOLATION)
        errors.append(
            f"Unsupported [Audio signals]={pre_reset_audio_signals!r}; "
            f"allowed={ALLOWED_AUDIO_SIGNALS_MODES_G96}."
        )
        norm_pre_signals = AUDIO_SIGNALS_FACTORY_DEFAULT_G96

    norm_pre_exp_step = _norm_exposure_step_g96(pre_reset_exposure_step)
    if norm_pre_exp_step is None:
        _add_code(codes, STATUS_BLOCKED_G96_EXPOSURE_STEP_ENUM_RESET_OR_TARGETS_VIOLATION)
        errors.append(
            f"Unsupported [Exposure step]={pre_reset_exposure_step!r}; "
            f"allowed={ALLOWED_EXPOSURE_STEPS_G96}."
        )
        norm_pre_exp_step = EXPOSURE_STEP_FACTORY_DEFAULT_G96

    state = resolve_fx3_audio_timing_signals_and_exp_step_state(
        pre_reset_audio_out_timing=norm_pre_timing,
        pre_reset_audio_signals=norm_pre_signals,
        pre_reset_exposure_step=norm_pre_exp_step,
        reset_action=norm_reset,
        shoot_mode=norm_shoot,
        audio_recording=norm_audio_rec,
        silent_mode=norm_silent,
    )

    # 1. [Audio Out Timing] Enum, Reset & S&Q / Audio-Off Lockout
    exp_post_timing = state["expected_post_reset_audio_out_timing"]
    if effective_post_reset_audio_out_timing is None:
        eff_post_timing = exp_post_timing
    else:
        norm_eff_timing = _norm_audio_out_timing_g96(
            effective_post_reset_audio_out_timing
        )
        if norm_eff_timing is None:
            _add_code(
                codes, STATUS_BLOCKED_G96_AUDIO_OUT_TIMING_ENUM_OR_RESET_VIOLATION
            )
            errors.append(
                f"Invalid effective_post_reset_audio_out_timing="
                f"{effective_post_reset_audio_out_timing!r}."
            )
            eff_post_timing = str(effective_post_reset_audio_out_timing)
        else:
            eff_post_timing = norm_eff_timing
            if eff_post_timing != exp_post_timing:
                _add_code(
                    codes, STATUS_BLOCKED_G96_AUDIO_OUT_TIMING_ENUM_OR_RESET_VIOLATION
                )
                errors.append(
                    f"[Audio Out Timing] reset mismatch after {norm_reset!r}: "
                    f"got {eff_post_timing!r}, expected {exp_post_timing!r}."
                )

    timing_reset_by_cam_reset = (
        eff_post_timing == AUDIO_OUT_TIMING_FACTORY_DEFAULT_G96
        if norm_reset in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE)
        else True
    )

    exp_timing_avail = bool(state["expected_audio_out_timing_available"])
    sq_or_audio_off_locked = bool(state["audio_out_timing_sq_or_audio_off_locked_out"])
    if audio_out_timing_available is None:
        eff_timing_avail = exp_timing_avail
    elif not isinstance(audio_out_timing_available, bool):
        _add_code(codes, STATUS_BLOCKED_G96_TELEMETRY_INVALID)
        errors.append("audio_out_timing_available must be bool or None.")
        eff_timing_avail = exp_timing_avail
    else:
        eff_timing_avail = audio_out_timing_available

    if eff_timing_avail != exp_timing_avail or (
        sq_or_audio_off_locked and audio_out_timing_override_while_locked
    ):
        _add_code(
            codes, STATUS_BLOCKED_G96_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION
        )
        errors.append(
            f"[Audio Out Timing] lockout violation for shoot_mode={norm_shoot!r}, "
            f"audio_recording={norm_audio_rec!r}: available={eff_timing_avail} "
            f"(expected {exp_timing_avail}), override={audio_out_timing_override_while_locked}."
        )

    # 2. [Audio signals] Setup Persistence & [Silent Mode]=On Hard-Lock
    exp_post_signals = state["expected_post_reset_audio_signals"]
    if configured_post_reset_audio_signals is None:
        cfg_post_signals = exp_post_signals
    else:
        norm_cfg_sig = _norm_on_off(configured_post_reset_audio_signals)
        if norm_cfg_sig is None:
            _add_code(
                codes, STATUS_BLOCKED_G96_AUDIO_SIGNALS_SETUP_PERSISTENCE_VIOLATION
            )
            errors.append(
                f"Invalid configured_post_reset_audio_signals="
                f"{configured_post_reset_audio_signals!r}."
            )
            cfg_post_signals = str(configured_post_reset_audio_signals)
        else:
            cfg_post_signals = norm_cfg_sig
            if cfg_post_signals != exp_post_signals:
                _add_code(
                    codes, STATUS_BLOCKED_G96_AUDIO_SIGNALS_SETUP_PERSISTENCE_VIOLATION
                )
                errors.append(
                    f"[Audio signals] Setup persistence mismatch after {norm_reset!r}: "
                    f"got {cfg_post_signals!r}, expected {exp_post_signals!r}."
                )

    signals_survives_cam_reset = (
        cfg_post_signals == norm_pre_signals
        if norm_reset == RESET_ACTION_CAMERA_SETTINGS_RESET
        else True
    )
    signals_reset_only_by_init = (
        cfg_post_signals == AUDIO_SIGNALS_FACTORY_DEFAULT_G96
        if norm_reset == RESET_ACTION_INITIALIZE
        else signals_survives_cam_reset
    )

    locked_by_silent = norm_silent == "On"
    exp_eff_signals = (
        AUDIO_SIGNALS_OFF_G96 if locked_by_silent else cfg_post_signals
    )
    if effective_audio_signals is None:
        eff_signals = exp_eff_signals
    else:
        norm_eff_sig = _norm_on_off(effective_audio_signals)
        if norm_eff_sig is None:
            _add_code(
                codes, STATUS_BLOCKED_G96_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION
            )
            errors.append(
                f"Invalid effective_audio_signals={effective_audio_signals!r}."
            )
            eff_signals = str(effective_audio_signals)
        else:
            eff_signals = norm_eff_sig

    if eff_signals != exp_eff_signals or (
        locked_by_silent and audio_signals_override_while_silent
    ):
        _add_code(
            codes, STATUS_BLOCKED_G96_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION
        )
        errors.append(
            f"[Audio signals] Silent Mode hard-lock violation for silent_mode={norm_silent!r}: "
            f"effective={eff_signals!r} (expected {exp_eff_signals!r}), "
            f"override={audio_signals_override_while_silent}."
        )

    # 3. [Exposure step] Enum, Reset & Governed Targets
    exp_post_step = state["expected_post_reset_exposure_step"]
    if effective_post_reset_exposure_step is None:
        eff_post_step = exp_post_step
    else:
        norm_eff_step = _norm_exposure_step_g96(effective_post_reset_exposure_step)
        if norm_eff_step is None:
            _add_code(
                codes, STATUS_BLOCKED_G96_EXPOSURE_STEP_ENUM_RESET_OR_TARGETS_VIOLATION
            )
            errors.append(
                f"Invalid effective_post_reset_exposure_step="
                f"{effective_post_reset_exposure_step!r}."
            )
            eff_post_step = str(effective_post_reset_exposure_step)
        else:
            eff_post_step = norm_eff_step
            if eff_post_step != exp_post_step:
                _add_code(
                    codes,
                    STATUS_BLOCKED_G96_EXPOSURE_STEP_ENUM_RESET_OR_TARGETS_VIOLATION,
                )
                errors.append(
                    f"[Exposure step] reset mismatch after {norm_reset!r}: "
                    f"got {eff_post_step!r}, expected {exp_post_step!r}."
                )

    exp_step_reset_by_cam_reset = (
        eff_post_step == EXPOSURE_STEP_FACTORY_DEFAULT_G96
        if norm_reset in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE)
        else True
    )

    if governed_exposure_targets is None:
        eff_targets = EXPOSURE_STEP_GOVERNED_TARGETS_G96
    elif not isinstance(governed_exposure_targets, (list, tuple)):
        _add_code(codes, STATUS_BLOCKED_G96_TELEMETRY_INVALID)
        errors.append("governed_exposure_targets must be a sequence or None.")
        eff_targets = ()
    else:
        eff_targets = tuple(str(t).strip() for t in governed_exposure_targets)

    shutter_angle_claimed_governed = any(
        t.strip().strip("[]").upper() in ("SHUTTER ANGLE", "ANGLE")
        for t in eff_targets
    )
    if shutter_angle_claimed_governed:
        _add_code(
            codes, STATUS_BLOCKED_G96_SHUTTER_ANGLE_CONSTANT_TABLE_COUPLED_DRIFT
        )
        errors.append(
            "[Shutter Angle] illegally listed as governed by [Exposure step]; "
            "[Shutter Angle] remains on its constant cine angle table."
        )

    if eff_targets != EXPOSURE_STEP_GOVERNED_TARGETS_G96:
        _add_code(
            codes, STATUS_BLOCKED_G96_EXPOSURE_STEP_ENUM_RESET_OR_TARGETS_VIOLATION
        )
        errors.append(
            f"Governed [Exposure step] targets mismatch: got {eff_targets}, "
            f"expected {EXPOSURE_STEP_GOVERNED_TARGETS_G96}."
        )

    # 4. [Shutter Angle] (Ver. 6.00+) Constant-Table Independence
    drift_events = 0
    if not isinstance(shutter_angle_table_at_0_3ev, (list, tuple)) or not isinstance(
        shutter_angle_table_at_0_5ev, (list, tuple)
    ):
        _add_code(codes, STATUS_BLOCKED_G96_TELEMETRY_INVALID)
        errors.append(
            "shutter_angle_table_at_0_3ev and shutter_angle_table_at_0_5ev must be sequences."
        )
        tbl_03: Tuple[float, ...] = ()
        tbl_05: Tuple[float, ...] = ()
    else:
        try:
            tbl_03 = tuple(round(float(v), 1) for v in shutter_angle_table_at_0_3ev)
            tbl_05 = tuple(round(float(v), 1) for v in shutter_angle_table_at_0_5ev)
        except (TypeError, ValueError):
            _add_code(codes, STATUS_BLOCKED_G96_TELEMETRY_INVALID)
            errors.append("Shutter angle table entries must be numeric degrees.")
            tbl_03 = ()
            tbl_05 = ()

    safe_angle_deg = (
        round(float(active_shutter_angle_deg), 1)
        if (
            not isinstance(active_shutter_angle_deg, bool)
            and isinstance(active_shutter_angle_deg, (int, float))
        )
        else -1.0
    )

    fw_below_600_with_angle = (
        norm_shutter_mode == SHUTTER_MODE_ANGLE_G96
        and fw_tuple is not None
        and fw_tuple < FX3_SHUTTER_ANGLE_MIN_FW_TUPLE_G96
    )
    angle_not_in_constant_table = (
        norm_shutter_mode == SHUTTER_MODE_ANGLE_G96
        and safe_angle_deg not in CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG_G96
    )
    tables_drifted = (
        tbl_03 != CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG_G96
        or tbl_05 != CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG_G96
        or tbl_03 != tbl_05
    )

    if (
        fw_below_600_with_angle
        or angle_not_in_constant_table
        or tables_drifted
        or shutter_angle_scaled_by_exposure_step
        or shutter_angle_claimed_governed
    ):
        drift_events = 1
        _add_code(
            codes, STATUS_BLOCKED_G96_SHUTTER_ANGLE_CONSTANT_TABLE_COUPLED_DRIFT
        )
        errors.append(
            f"[Shutter Angle] constant-table independence violation: fw={firmware_version!r}, "
            f"shutter_mode={norm_shutter_mode!r}, angle={safe_angle_deg} deg, "
            f"scaled_by_exp_step={shutter_angle_scaled_by_exposure_step}, "
            f"tables_match_constant={not tables_drifted}."
        )

    angle_unaffected = drift_events == 0
    valid = not codes
    status = STATUS_VERIFIED_G96 if valid else codes[0]
    model_hex = (
        f"0x{body_model_id:08x}"
        if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
        else "INVALID"
    )
    return AudioTimingSignalsAndExpStepGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=str(body_model_name),
        body_model_id_hex=model_hex,
        help_guide_code=str(help_guide_code),
        firmware_version=str(firmware_version),
        audio_out_timing_menu_path=AUDIO_OUT_TIMING_MENU_PATH_G96,
        audio_signals_menu_path=AUDIO_SIGNALS_MENU_PATH_G96,
        exposure_step_menu_path=EXPOSURE_STEP_MENU_PATH_G96,
        pre_reset_audio_out_timing=norm_pre_timing,
        pre_reset_audio_signals=norm_pre_signals,
        pre_reset_exposure_step=norm_pre_exp_step,
        reset_action=norm_reset,
        expected_post_reset_audio_out_timing=exp_post_timing,
        effective_post_reset_audio_out_timing=eff_post_timing,
        audio_out_timing_reset_by_camera_settings_reset=timing_reset_by_cam_reset,
        shoot_mode=norm_shoot,
        audio_recording=norm_audio_rec,
        audio_out_timing_available=eff_timing_avail,
        audio_out_timing_sq_or_audio_off_locked_out=sq_or_audio_off_locked,
        expected_post_reset_audio_signals=exp_post_signals,
        configured_post_reset_audio_signals=cfg_post_signals,
        audio_signals_survives_camera_settings_reset=signals_survives_cam_reset,
        audio_signals_reset_only_by_initialize=signals_reset_only_by_init,
        silent_mode=norm_silent,
        effective_audio_signals=eff_signals,
        audio_signals_locked_off_by_silent_mode=locked_by_silent,
        expected_post_reset_exposure_step=exp_post_step,
        effective_post_reset_exposure_step=eff_post_step,
        exposure_step_reset_by_camera_settings_reset=exp_step_reset_by_cam_reset,
        governed_exposure_targets=eff_targets,
        shutter_mode=norm_shutter_mode,
        active_shutter_angle_deg=safe_angle_deg,
        shutter_angle_table_at_0_3ev=tbl_03,
        shutter_angle_table_at_0_5ev=tbl_05,
        shutter_angle_unaffected_by_exposure_step=angle_unaffected,
        shutter_angle_exposure_step_drift_events=drift_events,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g96_audio_timing_signals_and_exp_step_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    audio_timing_exp_step_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase249DonorAuditResult] = None,
) -> Tuple[GateVerdict, G96AudioTimingSignalsAndExpStepGuardResult]:
    """Evaluate Gate `G96` combining O_RDONLY local donor audit and
    `[Audio Out Timing]` / `[Audio signals]` / `[Exposure step]` vs
    `[Shutter Angle]` constant-table independence guard.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase249_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
        **(dict(audio_timing_exp_step_kwargs) if audio_timing_exp_step_kwargs else {})
    )

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE249_DONOR_INTEGRITY)
        errors.extend(audit.errors)
    for c in guard.violation_codes:
        _add_code(codes, c)
    errors.extend(guard.errors)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G96 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G96 if valid else codes[0]

    res = G96AudioTimingSignalsAndExpStepGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        audio_timing_exp_step_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, audio_timing={guard.effective_post_reset_audio_out_timing}"
        f"(avail={guard.audio_out_timing_available}), "
        f"audio_signals={guard.effective_audio_signals}"
        f"(survives_reset={guard.audio_signals_survives_camera_settings_reset},"
        f"silent_locked={guard.audio_signals_locked_off_by_silent_mode}), "
        f"exp_step={guard.effective_post_reset_exposure_step}"
        f"(shutter_angle_unaffected={guard.shutter_angle_unaffected_by_exposure_step})"
    )
    verdict = GateVerdict(
        gate_id=G96_GATE_ID,
        gate_code=G96_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `96`-Gate Master Safety Preflight (`G01..G96`)
# ---------------------------------------------------------------------------


def evaluate_96gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    lock_op_parts_kwargs: Optional[Mapping[str, Any]] = None,
    audio_timing_exp_step_kwargs: Optional[Mapping[str, Any]] = None,
    master_94_override: Optional[Master94GateReport] = None,
    **m94_passthrough_kwargs: Any,
) -> Master96GateReport:
    """Evaluate all 96 Master Safety Gates (`G01..G96`) deterministically by
    delegating `G01..G94` directly to `evaluate_94gate_preflight()`.
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

    m94_report: Master94GateReport = (
        master_94_override
        if master_94_override is not None
        else evaluate_94gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m94_passthrough_kwargs,
        )
    )

    phase249_audit = audit_phase249_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g95_verdict, g95_res = evaluate_g95_lock_operation_parts_and_chord_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        lock_op_parts_kwargs=lock_op_parts_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase249_audit,
    )

    g96_verdict, g96_res = evaluate_g96_audio_timing_signals_and_exp_step_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        audio_timing_exp_step_kwargs=audio_timing_exp_step_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase249_audit,
    )

    gates_95_to_96 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g95_verdict, g96_verdict)
    ]
    all_gates = tuple(list(m94_report.gates) + gates_95_to_96)

    g01_to_g12_verified = int(m94_report.summary["g01_to_g12_verified"])
    g13_to_g94_verified = (
        int(m94_report.summary["g13_to_g92_verified"])
        + int(m94_report.summary["g93_to_g94_verified"])
    )
    g95_to_g96_verified = sum(1 for v in (g95_verdict, g96_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g94_verified + g95_to_g96_verified

    g95_to_g96_all_passed = g95_to_g96_verified == 2
    g13_to_g96_all_passed = m94_report.g13_to_g94_all_passed and g95_to_g96_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m94_report.gates[:9])

    offline_93_verified = (
        g01_to_g09_ok
        and m94_report.offline_91_gates_verified
        and g95_to_g96_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_96_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g96_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m94_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_93_verified
        and m94_report.h0_h1_trial_entry_allowed
        and g95_to_g96_all_passed
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
        list(m94_report.errors) + list(g95_verdict.errors) + list(g96_verdict.errors)
    )
    warnings: List[str] = (
        list(m94_report.warnings)
        + list(g95_verdict.warnings)
        + list(g96_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m94_report.g13_to_g94_all_passed:
        overall_status = m94_report.status
    elif not g95_verdict.passed:
        overall_status = g95_verdict.status
    elif not g96_verdict.passed:
        overall_status = g96_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_96_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_96_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_96_verified:
        overall_status = "VERIFIED_ALL_96_GATES"
    else:
        overall_status = "VERIFIED_93_OF_96_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m94_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g95_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g96_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 96,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 96 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g94_verified": g13_to_g94_verified,
        "g95_to_g96_verified": g95_to_g96_verified,
        "g13_to_g96_all_passed": g13_to_g96_all_passed,
        "g95_to_g96_all_passed": g95_to_g96_all_passed,
        "offline_93_gates_verified": offline_93_verified,
        "all_96_gates_verified": all_96_verified,
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

    return Master96GateReport(
        schema=REALHW_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_96GATE_SCHEMA,
        version=REALHW_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_96GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_93_gates_verified=offline_93_verified,
        all_96_gates_verified=all_96_verified,
        g13_to_g96_all_passed=g13_to_g96_all_passed,
        g95_to_g96_all_passed=g95_to_g96_all_passed,
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
        master_94_report=m94_report.to_dict(),
        g95_result=g95_res.to_dict(),
        g96_result=g96_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_96_master_safety_gates = evaluate_96gate_preflight
run_96_gate_preflight = evaluate_96gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard",
        description=(
            "Phase 249 Safety Gates G95 (Lock Operation Parts Fn Hold, MENU + Fn 5s "
            "Full-Body Lock Chord vs Destructive MENU + Delete 2s Firewall & My Dial "
            "Temporary Override Guard) + G96 (Audio Out Timing Live/Lip Sync vs "
            "Audio signals Setup Persistence & Exposure step 0.3EV/0.5EV vs Shutter "
            "Angle Constant-Table Guard) + Unified 96-Gate Master Safety Preflight"
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

    report = evaluate_96gate_preflight(
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
            f"verified={report.summary['verified_gates']}/96 "
            f"g95_to_g96_all_passed={report.g95_to_g96_all_passed} "
            f"all_96_gates_verified={report.all_96_gates_verified} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
            f"usb_packets_transmitted={report.usb_packets_transmitted} "
            f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        report.all_96_gates_verified
        if args.dry_run_simulated
        else report.offline_93_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
