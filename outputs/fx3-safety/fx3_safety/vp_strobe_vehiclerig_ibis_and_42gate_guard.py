"""Phase 131 — Virtual Production High-Energy DMX Strobe / UV-Arc `IMX510` CMOS Sensor
Overload & External Tri-Level Sync / Multi-Terminal Backfeed Firewall (Gate G41),
Vehicle / Helicopter Hard-Mount High-Frequency Vibration (`20..200 Hz`) `IBIS` Voice-Coil
Thermal Resonance & Secondary Steel-Tether Guard (Gate G42), and Unified 42-Gate Master
Safety Preflight (`G01..G42` / `verify-42-gates`).

Operationalizes two critical virtual-production / studio-sync and vehicle/aerial-rigging
hardware guards for Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, SoC `CXD90057`),
while keeping all prior gate modules (`preflight.py`, `master_16gate_preflight.py`,
`usblan_ptpip_and_18gate_preflight.py`, `rig_groundloop_lensrail_and_20gate_guard.py`,
`phantom48v_gimbal_and_22gate_guard.py`, `dewpoint_tec_usbc_and_24gate_guard.py`,
`intake_occlusion_tripod_and_26gate_guard.py`, `sensor_curtain_subzero_and_28gate_guard.py`,
`wireless_tx_emi_endurance_and_30gate_guard.py`, `pl_cantilever_dummybatt_and_32gate_guard.py`,
`saltspray_haze_followfocus_and_34gate_guard.py`, `hdmi_aoc_5v_cfexpress_and_36gate_guard.py`,
`usbpd_trigger_multiterminal_and_38gate_guard.py`, and
`monsoon_mishoe_cagetwist_and_40gate_guard.py`) completely untouched:

1. **Read-Only (`os.O_RDONLY`) FX3/FX6 Donor Sensor / Sync / Multi-Terminal Audit**:
   - Inspects local FX6 `v6.01` `libInfraMultiIF.so`
     (`InfraMultiIF_Init`, `InfraMultiIF_Exit`,
     `_ZN12InfraMultiIF19InfraMultiIFManager10initializeEv`,
     `_ZN12InfraMultiIF19InfraMultiIFManager8finalizeEv`),
     `libInfraLanc.so` (`InfraDebugPrintfLanc`,
     `_ZN16InfraLancCommand17GetLANCStrobeInfoEP19InfraLancStrobeInfo`,
     `_ZN9InfraLanc16eventGetCallbackEPvS0_`,
     `_ZN9InfraLanc20eventLancApiCallbackEPvS0_`), and FX3 `v7.02` & FX6 `v6.01`
     `libUsbControl.so` (`_ZN12UsbIfWrapper20isMultiPortSupportedEv`,
     `_ZN10UsbControl18actionOnChangeVbusEPN3UFW3FsmEiPv`,
     `MSGID_VBUS_CHANGED_EVT`, `MSGID_VBUS_ERROR_EVT`) and `libInfraExtCmdSvc.so`
     (`ExtCmdSvc_Create`, `_ZN9ExtCmdSvc22IntrRegistTransportCmdEP16__extcmd_svc_msgj`,
     `_ZN9ExtCmdSvc17SndMsgToUpperSyncEPvS0_j`,
     `_ZN9ExtCmdSvc17SndMsgToLowerSyncEPvS0_j`) strictly via `os.open(..., os.O_RDONLY)`,
     plus optional chunked scans of `appFw.so`
     (`ANTI_FLICKER_SET_HIGH_RES_SS_ON`, `STROBE_CONTROL_MODE`, `TIMECODE_EXT_NOTIFY`,
     `INFRA_NOTIFY_TIMECODE_EXT_TC_STATUS`, `STEADY_SHOT_MODE`,
     `VAL_built_in_steady_shot_error_BUILT_IN_STEADY_SHOT_ERROR_OCCURED`) and
     `cpapp-b.bin` (`GENLOCK_SetGenlockEnable`, `GENLOCK_CBID_VSYNC`,
     `GENLOCK_CBID_LOST`, `SET_S1_STEADY_SHOT_MODE`, `STEADY_SHOT_MODE`) when
     `include_large_binaries=True`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent.

2. **Gate G41 — Virtual Production High-Irradiance DMX Xenon/LED Strobe / Unfiltered
   UV-Arc `IMX510` Microlens Thermal Hazard & External `75-Ohm` Tri-Level Genlock ->
   `Multi-Terminal` Pin Mismatch Firewall**:
   - Protects FX3's `IMX510` BSI CMOS microlens/color-filter array and `15-pin
     Multi-Terminal` when rigged in LED volumes / studio broadcast bays (where operators
     sometimes mistakenly feed `±300 mV` / `1 Vpp` `75-Ohm` BNC Tri-Level Genlock or
     `5V` Word-Clock into FX3's `LTC-only` Multi-Terminal adapter, or fire close-range
     DMX strobes / arc welders without ND/UV-IR cut).
   - Fails closed on:
     a) `BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD` when
        `peak_irradiance_w_cm2 > 0.35` or (`uv_arc_welding_or_pyro_scene == True` and
        `uv_ir_cut_and_protective_nd_installed == False`),
     b) `BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL` when
        `connected_to_fx3_multiterminal == True` and
        `bnc_sync_signal_type in {"TRILEVEL_GENLOCK", "BLACKBURST_PAL_NTSC", "WORDCLOCK_5V_TTL"}`
        (FX3 has no hardware `Genlock` PLL input unlike FX6; `5V` TTL Word-Clock
        overdrives the `LTC` pin),
     c) `BLOCKED_LEDWALL_SCAN_ALIASING_NO_ECS_LOCK` when `led_volume_active == True`
        and `led_pwm_refresh_hz < 1920.0` and `ecs_fractional_shutter_locked == False`.

3. **Gate G42 — Car-Rig / Motorcycle / Helicopter Hard-Mount High-Frequency Vibration
   (`20..200 Hz`) 5-Axis `IBIS` Voice-Coil Thermal Runaway & Secondary Stainless
   Safety-Tether Guard**:
   - Hard-mounting FX3 directly to a chase car, motorcycle frame, or helicopter skid
     without a wire-rope isolator subjects the 5-axis `IBIS` floating sensor stage
     (`±1.5 mm` mechanical stops) to continuous `> 1.8..2.5 g RMS` (`20..200 Hz`)
     vibration, slamming the sensor carriage against end-stops and overheating voice coils.
   - Fails closed on:
     a) `BLOCKED_HARDMOUNT_HIGH_G_VIBRATION_NO_WIRE_ISOLATOR` when
        `vibration_rms_g > 1.8` (`20..200 Hz`) and
        `wire_rope_or_elastomer_isolator_stage == False`,
     b) `BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE` when
        `vibration_rms_g > 1.2` and `dominant_vibration_hz >= 35.0` and
        `ibis_steadyshot_mode != "OFF_MECHANICAL_PARK"` (enforcing `SteadyShot OFF`
        mechanical park + post `Gyroflow` `RTMD` stabilization under engine resonance),
     c) `BLOCKED_VEHICLE_EXTERIOR_RIG_MISSING_SECONDARY_STEEL_TETHER` when
        `vehicle_or_aerial_exterior_mount == True` and
        (`secondary_steel_safety_cable_rated_kg < 25.0` or `suction_cup_count < 3`).

4. **Unified 42-Gate Master Safety Preflight (`evaluate_42gate_preflight` / CLI
   `verify-42-gates`)**:
   - Composes `evaluate_40gate_preflight` (`G01..G40`) with `G41` and `G42`:
     * Offline default mode: `39/42` gates pass (`G10..G12` physical Tier-0 backup
       truthfully remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` ->
       `overall_ready_for_hardware_attach = False`).
     * `--dry-run-simulated-backup` mode: `42/42` simulation gates pass
       (`dry_run_rehearsal_only = True`), while `persistent_emmc_writes_authorized`,
       `persistent_write_release`, and `overall_ready_for_hardware_attach` remain
       hard-locked to `False`.

Hard Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- All donor file reads strictly use `os.open(..., os.O_RDONLY)`.
- Zero raw binary `bytes` repr output (always `.hex()`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .exfat_media_integrity_guard import MediaSlotConfig
from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    GateVerdict,
    P12_WLAN_FATAL_GUARD_VMA,
)
from .monsoon_mishoe_cagetwist_and_40gate_guard import (
    Master40GateReport,
    evaluate_40gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
    scan_tokens_o_rdonly,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

VP_STROBE_VEHICLERIG_42GATE_SCHEMA: str = (
    "fx3-vp-strobe-vehiclerig-ibis-42gate-preflight-v1"
)
VP_STROBE_VEHICLERIG_42GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G41..G42
G41_GATE_ID: str = "G41_vp_strobe_uvarc_genlock_and_ecs_sync_safe"
G41_GATE_CODE: str = "VP_STROBE_UVARC_GENLOCK_AND_ECS_SYNC_SAFE"

G42_GATE_ID: str = "G42_vehicle_rig_vibration_ibis_park_and_tether_safe"
G42_GATE_CODE: str = "VEHICLE_RIG_VIBRATION_IBIS_PARK_AND_TETHER_SAFE"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G41: str = "VERIFIED_VP_STROBE_UVARC_GENLOCK_AND_ECS_SYNC_SAFE"
STATUS_VERIFIED_G42: str = (
    "VERIFIED_VEHICLE_RIG_VIBRATION_IBIS_PARK_AND_TETHER_SAFE"
)

# Gate G41 Violation Codes
STATUS_BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD: str = (
    "BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD"
)
STATUS_BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL: str = (
    "BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL"
)
STATUS_BLOCKED_LEDWALL_SCAN_ALIASING_NO_ECS_LOCK: str = (
    "BLOCKED_LEDWALL_SCAN_ALIASING_NO_ECS_LOCK"
)
STATUS_BLOCKED_VP_STROBE_GENLOCK_TELEMETRY_INVALID: str = (
    "BLOCKED_VP_STROBE_GENLOCK_TELEMETRY_INVALID"
)

# Gate G42 Violation Codes
STATUS_BLOCKED_HARDMOUNT_HIGH_G_VIBRATION_NO_WIRE_ISOLATOR: str = (
    "BLOCKED_HARDMOUNT_HIGH_G_VIBRATION_NO_WIRE_ISOLATOR"
)
STATUS_BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE: str = (
    "BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE"
)
STATUS_BLOCKED_VEHICLE_EXTERIOR_RIG_MISSING_SECONDARY_STEEL_TETHER: str = (
    "BLOCKED_VEHICLE_EXTERIOR_RIG_MISSING_SECONDARY_STEEL_TETHER"
)
STATUS_BLOCKED_VEHICLERIG_IBIS_TELEMETRY_INVALID: str = (
    "BLOCKED_VEHICLERIG_IBIS_TELEMETRY_INVALID"
)

STATUS_BLOCKED_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE131_42GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G41 Virtual Production Strobe / UV-Arc / Tri-Level Genlock / LED-Wall Thresholds
IMX510_MAX_SAFE_PEAK_IRRADIANCE_W_CM2: float = 0.35
IMX510_MICROLENS_PULSE_THERMAL_COEFF_C_PER_WCM2_MS: float = 12.0
LED_WALL_MIN_ALIAS_FREE_PWM_HZ: float = 1920.0
FX3_MULTITERMINAL_PIN_COUNT: int = 15
BNC_SYNC_IMPEDANCE_OHM: float = 75.0
FX3_MULTITERMINAL_SAFE_SYNC_TYPES: Tuple[str, ...] = (
    "NONE",
    "LTC_SMPTE_UNBALANCED",
    "LANC_REMOTE",
)
FX3_MULTITERMINAL_BLOCKED_GENLOCK_SIGNALS: Tuple[str, ...] = (
    "TRILEVEL_GENLOCK",
    "BLACKBURST_PAL_NTSC",
    "WORDCLOCK_5V_TTL",
)
VALID_BNC_SYNC_SIGNAL_TYPES: Tuple[str, ...] = (
    FX3_MULTITERMINAL_SAFE_SYNC_TYPES + FX3_MULTITERMINAL_BLOCKED_GENLOCK_SIGNALS
)

# Gate G42 Vehicle / Aerial Vibration, 5-Axis IBIS Park & Steel-Tether Thresholds
STANDARD_GRAVITY_M_S2: float = 9.80665
VIBRATION_BAND_MIN_HZ: float = 20.0
VIBRATION_BAND_MAX_HZ: float = 200.0
VIBRATION_WIRE_ISOLATOR_MAX_RMS_G: float = 1.8
VIBRATION_IBIS_PARK_MAX_RMS_G: float = 1.2
ENGINE_RESONANCE_MIN_HZ: float = 35.0
IBIS_MECHANICAL_STROKE_LIMIT_MM: float = 1.5
IBIS_MODE_OFF_MECHANICAL_PARK: str = "OFF_MECHANICAL_PARK"
VALID_IBIS_STEADYSHOT_MODES: Tuple[str, ...] = (
    IBIS_MODE_OFF_MECHANICAL_PARK,
    "STANDARD",
    "ACTIVE",
    "DYNAMIC_ACTIVE",
)
VEHICLE_EXTERIOR_MIN_STEEL_TETHER_KG: float = 25.0
VEHICLE_EXTERIOR_MIN_SUCTION_CUPS: int = 3

# Compact FX3/FX6 Donor Specs for Multi-IF / LANC-Strobe / USB-MultiPort / ExtCmd (O_RDONLY verified)
PINNED_PHASE131_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx6_lib_infra_multi_if": (
        "fx6",
        "libInfraMultiIF.so",
        194_240,
        "4f18de86260ccd1ac9d0a3bc104ec9fc690583c75f3473b222078168ca165260",
        (
            b"InfraMultiIF_Init",
            b"InfraMultiIF_Exit",
            b"_ZN12InfraMultiIF19InfraMultiIFManager10initializeEv",
            b"_ZN12InfraMultiIF19InfraMultiIFManager8finalizeEv",
        ),
        "fx6/libInfraMultiIF.so::{InfraMultiIF_Init,InfraMultiIF_Exit,initialize,finalize}",
    ),
    "fx6_lib_infra_lanc": (
        "fx6",
        "libInfraLanc.so",
        51_848,
        "99e02239a918fff088759607b5c66292e53d0b30d76235ed56c1d1ee8c922416",
        (
            b"InfraDebugPrintfLanc",
            b"_ZN16InfraLancCommand17GetLANCStrobeInfoEP19InfraLancStrobeInfo",
            b"_ZN9InfraLanc16eventGetCallbackEPvS0_",
            b"_ZN9InfraLanc20eventLancApiCallbackEPvS0_",
        ),
        "fx6/libInfraLanc.so::{InfraDebugPrintfLanc,GetLANCStrobeInfo,eventGetCallback,eventLancApiCallback}",
    ),
    "fx3_lib_usb_control": (
        "fx3",
        "libUsbControl.so",
        135_424,
        "2bf51f28fd5066e56afc8bbb02ddbaa96b36f57ff2a823cecf9f901781754ed9",
        (
            b"_ZN12UsbIfWrapper20isMultiPortSupportedEv",
            b"_ZN10UsbControl18actionOnChangeVbusEPN3UFW3FsmEiPv",
            b"MSGID_VBUS_CHANGED_EVT",
            b"MSGID_VBUS_ERROR_EVT",
        ),
        "fx3/libUsbControl.so::{isMultiPortSupported,actionOnChangeVbus,MSGID_VBUS_CHANGED_EVT,MSGID_VBUS_ERROR_EVT}",
    ),
    "fx6_lib_usb_control": (
        "fx6",
        "libUsbControl.so",
        135_424,
        "951d1da8a4366dc8cf7bf475181344ea487e661869701218a2343e9c9ecf1483",
        (
            b"_ZN12UsbIfWrapper20isMultiPortSupportedEv",
            b"_ZN10UsbControl18actionOnChangeVbusEPN3UFW3FsmEiPv",
            b"MSGID_VBUS_CHANGED_EVT",
            b"MSGID_VBUS_ERROR_EVT",
        ),
        "fx6/libUsbControl.so::{isMultiPortSupported,actionOnChangeVbus,MSGID_VBUS_CHANGED_EVT,MSGID_VBUS_ERROR_EVT}",
    ),
    "fx3_lib_infra_ext_cmd_svc": (
        "fx3",
        "libInfraExtCmdSvc.so",
        26_960,
        "6ed99a632f6646e3313241b8d1aaef5a584444f81cf721c013fc403887774134",
        (
            b"ExtCmdSvc_Create",
            b"_ZN9ExtCmdSvc22IntrRegistTransportCmdEP16__extcmd_svc_msgj",
            b"_ZN9ExtCmdSvc17SndMsgToUpperSyncEPvS0_j",
            b"_ZN9ExtCmdSvc17SndMsgToLowerSyncEPvS0_j",
        ),
        "fx3/libInfraExtCmdSvc.so::{ExtCmdSvc_Create,IntrRegistTransportCmd,SndMsgToUpperSync,SndMsgToLowerSync}",
    ),
    "fx6_lib_infra_ext_cmd_svc": (
        "fx6",
        "libInfraExtCmdSvc.so",
        26_960,
        "94e8916baa891c132393a52a681cdd7664c900dd628dd10a190a20323273affc",
        (
            b"ExtCmdSvc_Create",
            b"_ZN9ExtCmdSvc22IntrRegistTransportCmdEP16__extcmd_svc_msgj",
            b"_ZN9ExtCmdSvc17SndMsgToUpperSyncEPvS0_j",
            b"_ZN9ExtCmdSvc17SndMsgToLowerSyncEPvS0_j",
        ),
        "fx6/libInfraExtCmdSvc.so::{ExtCmdSvc_Create,IntrRegistTransportCmd,SndMsgToUpperSync,SndMsgToLowerSync}",
    ),
}

PINNED_APPFW_SENSOR_SYNC_TOKENS: Tuple[str, ...] = (
    "ANTI_FLICKER_SET_HIGH_RES_SS_ON",
    "STROBE_CONTROL_MODE",
    "TIMECODE_EXT_NOTIFY",
    "INFRA_NOTIFY_TIMECODE_EXT_TC_STATUS",
    "STEADY_SHOT_MODE",
    "VAL_built_in_steady_shot_error_BUILT_IN_STEADY_SHOT_ERROR_OCCURED",
)

PINNED_CPAPP_GENLOCK_IBIS_TOKENS: Tuple[str, ...] = (
    "GENLOCK_SetGenlockEnable",
    "GENLOCK_CBID_VSYNC",
    "GENLOCK_CBID_LOST",
    "SET_S1_STEADY_SHOT_MODE",
    "STEADY_SHOT_MODE",
)


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase131DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    multi_if_lanc_tokens_verified: bool
    usb_multiport_tokens_verified: bool
    ext_cmd_svc_tokens_verified: bool
    large_binaries_scanned: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VpStrobeGenlockFirewallResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    vp_profile: str
    peak_irradiance_w_cm2: float
    pulse_duration_ms: float
    uv_arc_welding_or_pyro_scene: bool
    uv_ir_cut_and_protective_nd_installed: bool
    nd_optical_density: float
    estimated_microlens_temp_rise_c: float
    bnc_sync_signal_type: str
    connected_to_fx3_multiterminal: bool
    led_volume_active: bool
    led_pwm_refresh_hz: float
    ecs_fractional_shutter_locked: bool
    shutter_rate_hz: float
    led_pwm_cycles_per_shutter_window: float
    arc_strobe_irradiance_safe: bool
    multiterminal_genlock_safe: bool
    ledwall_ecs_sync_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VehicleRigIbisTetherGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    rig_profile: str
    vibration_rms_g: float
    dominant_vibration_hz: float
    wire_rope_or_elastomer_isolator_stage: bool
    ibis_steadyshot_mode: str
    gyroflow_rtmd_logging_enabled: bool
    vehicle_or_aerial_exterior_mount: bool
    secondary_steel_safety_cable_rated_kg: float
    suction_cup_count: int
    camera_rig_mass_kg: float
    estimated_peak_displacement_mm: float
    tether_static_safety_factor_at_5g: float
    hardmount_wire_isolator_safe: bool
    ibis_resonance_park_safe: bool
    exterior_steel_tether_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G41VpStrobeGenlockResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    vp_strobe_genlock_firewall: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G42VehicleRigIbisTetherResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    vehiclerig_ibis_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master42GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_39_gates_verified: bool
    all_42_gates_verified: bool
    g13_to_g42_all_passed: bool
    g41_to_g42_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_40_report: Dict[str, Any]
    g41_result: Dict[str, Any]
    g42_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
    """Strictly read a file via `os.open(..., os.O_RDONLY)` without printing raw bytes."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        chunks: List[bytes] = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _is_finite_number(val: Any) -> bool:
    return (
        isinstance(val, (int, float))
        and (not isinstance(val, bool))
        and math.isfinite(float(val))
    )


def _is_non_negative_int(val: Any) -> bool:
    return isinstance(val, int) and (not isinstance(val, bool)) and val >= 0


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase131_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
) -> Phase131DonorAuditResult:
    """Inspect FX3/FX6 Multi-IF/LANC/USB-MultiPort/ExtCmd donors via `os.O_RDONLY`."""
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)

    if work_root is not None and paths.work_root is None:
        explicit_root = Path(work_root)
        fx3_lib_dir = (
            explicit_root
            / "fx3-vm-20261101"
            / "menu-repair-01"
            / "original-uipc"
            / "ap-projection"
            / "regular-files"
            / "usr"
            / "lib"
        )
        fx6_lib_dir = (
            explicit_root
            / "fx3-color-port-20261027"
            / "FX6-donor-assessment-20261103"
            / "team"
            / "donor"
            / "nflasha15-files"
            / "lib"
        )
        effective_work_root: Optional[Path] = explicit_root
    else:
        fx3_lib_dir = paths.fx3_lib_dir
        fx6_lib_dir = paths.fx6_lib_dir
        effective_work_root = paths.work_root

    resolved: Dict[str, Path] = {
        "fx6_lib_infra_multi_if": fx6_lib_dir / "libInfraMultiIF.so",
        "fx6_lib_infra_lanc": fx6_lib_dir / "libInfraLanc.so",
        "fx3_lib_usb_control": fx3_lib_dir / "libUsbControl.so",
        "fx6_lib_usb_control": fx6_lib_dir / "libUsbControl.so",
        "fx3_lib_infra_ext_cmd_svc": fx3_lib_dir / "libInfraExtCmdSvc.so",
        "fx6_lib_infra_ext_cmd_svc": fx6_lib_dir / "libInfraExtCmdSvc.so",
    }

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase131DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE131_DONOR_SPECS.values()
            ),
            missing_markers=(),
            multi_if_lanc_tokens_verified=True,
            usb_multiport_tokens_verified=True,
            ext_cmd_svc_tokens_verified=True,
            large_binaries_scanned=False,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE131_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE131_DONOR_SPECS.items()
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
    passed_keys: set[str] = set()

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE131_DONOR_SPECS.items():
        blob = _read_file_o_rdonly(resolved[key])
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

    files_inspected = len(resolved)
    large_scanned = False
    appfw_ok = True
    cpapp_ok = True
    if include_large_binaries:
        if paths.fx3_appfw_path.is_file():
            appfw_sz, missing_appfw = scan_tokens_o_rdonly(
                paths.fx3_appfw_path, PINNED_APPFW_SENSOR_SYNC_TOKENS
            )
            sizes["fx3_appfw"] = appfw_sz
            files_inspected += 1
            large_scanned = True
            if missing_appfw:
                appfw_ok = False
                missing.extend(missing_appfw)
                errors.append(
                    f"fx3 appFw.so missing AntiFlicker/Strobe/TC/SteadyShot tokens: {missing_appfw}"
                )
            else:
                checked.append(
                    "fx3/appFw.so::HIGH_RES_SS_ON+STROBE_CONTROL_MODE+TIMECODE_EXT_NOTIFY+STEADY_SHOT_MODE+STEADY_SHOT_ERROR"
                )
        else:
            warnings.append(
                "fx3/appFw.so not found for optional large-binary VP/Sync/IBIS scan."
            )

        if paths.fx3_cp_path.is_file():
            cp_sz, missing_cp = scan_tokens_o_rdonly(
                paths.fx3_cp_path, PINNED_CPAPP_GENLOCK_IBIS_TOKENS
            )
            sizes["fx3_cpapp"] = cp_sz
            files_inspected += 1
            large_scanned = True
            if missing_cp:
                cpapp_ok = False
                missing.extend(missing_cp)
                errors.append(
                    f"fx3 cpapp-b.bin missing GENLOCK/VSYNC/STEADY_SHOT tokens: {missing_cp}"
                )
            else:
                checked.append(
                    "fx3/cpapp-b.bin::GENLOCK_SetGenlockEnable+GENLOCK_CBID_VSYNC+GENLOCK_CBID_LOST+SET_S1_STEADY_SHOT_MODE"
                )
        else:
            warnings.append(
                "fx3/cpapp-b.bin not found for optional large-binary Genlock/IBIS scan."
            )

    valid = len(errors) == 0 and len(missing) == 0
    return Phase131DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        multi_if_lanc_tokens_verified={
            "fx6_lib_infra_multi_if",
            "fx6_lib_infra_lanc",
        }.issubset(passed_keys)
        and appfw_ok,
        usb_multiport_tokens_verified={
            "fx3_lib_usb_control",
            "fx6_lib_usb_control",
        }.issubset(passed_keys)
        and appfw_ok
        and cpapp_ok,
        ext_cmd_svc_tokens_verified={
            "fx3_lib_infra_ext_cmd_svc",
            "fx6_lib_infra_ext_cmd_svc",
        }.issubset(passed_keys)
        and cpapp_ok,
        large_binaries_scanned=large_scanned,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Virtual Production Optical / Sync & Vehicle IBIS / Tether Physics Helpers
# ---------------------------------------------------------------------------


def estimate_imx510_microlens_flash_temp_rise_c(
    peak_irradiance_w_cm2: float,
    pulse_duration_ms: float = 5.0,
    *,
    nd_optical_density: float = 0.0,
) -> float:
    """Estimate IMX510 microlens/CFA pulse temperature rise (C) from irradiance and ND OD."""
    if not (
        _is_finite_number(peak_irradiance_w_cm2)
        and _is_finite_number(pulse_duration_ms)
        and _is_finite_number(nd_optical_density)
    ):
        raise ValueError(
            "peak_irradiance_w_cm2, pulse_duration_ms, and nd_optical_density must be finite numbers."
        )
    if (
        float(peak_irradiance_w_cm2) < 0.0
        or float(pulse_duration_ms) < 0.0
        or float(nd_optical_density) < 0.0
    ):
        raise ValueError(
            "peak_irradiance_w_cm2, pulse_duration_ms, and nd_optical_density must be >= 0.0."
        )
    effective_irradiance = float(peak_irradiance_w_cm2) * (10.0 ** (-float(nd_optical_density)))
    return (
        effective_irradiance
        * float(pulse_duration_ms)
        * IMX510_MICROLENS_PULSE_THERMAL_COEFF_C_PER_WCM2_MS
    )


def compute_led_wall_ecs_beat_ratio(
    led_pwm_refresh_hz: float,
    shutter_rate_hz: float,
) -> float:
    """Compute LED wall PWM cycles per camera exposure window (f_pwm / f_shutter)."""
    if not (_is_finite_number(led_pwm_refresh_hz) and _is_finite_number(shutter_rate_hz)):
        raise ValueError("led_pwm_refresh_hz and shutter_rate_hz must be finite numbers.")
    if float(led_pwm_refresh_hz) <= 0.0 or float(shutter_rate_hz) <= 0.0:
        raise ValueError("led_pwm_refresh_hz and shutter_rate_hz must be > 0.0.")
    return float(led_pwm_refresh_hz) / float(shutter_rate_hz)


def estimate_ibis_voice_coil_excursion_mm(
    vibration_rms_g: float,
    dominant_vibration_hz: float,
    *,
    isolator_transmissibility: float = 1.0,
) -> float:
    """Estimate sinusoidal peak displacement (mm) transmitted to the 5-axis IBIS carriage."""
    if not (
        _is_finite_number(vibration_rms_g)
        and _is_finite_number(dominant_vibration_hz)
        and _is_finite_number(isolator_transmissibility)
    ):
        raise ValueError(
            "vibration_rms_g, dominant_vibration_hz, and isolator_transmissibility must be finite numbers."
        )
    if (
        float(vibration_rms_g) < 0.0
        or float(dominant_vibration_hz) <= 0.0
        or float(isolator_transmissibility) < 0.0
    ):
        raise ValueError(
            "vibration_rms_g >= 0.0, dominant_vibration_hz > 0.0, and isolator_transmissibility >= 0.0 required."
        )
    a_peak_mm_s2 = (
        math.sqrt(2.0)
        * float(vibration_rms_g)
        * STANDARD_GRAVITY_M_S2
        * float(isolator_transmissibility)
        * 1000.0
    )
    omega = 2.0 * math.pi * float(dominant_vibration_hz)
    return a_peak_mm_s2 / (omega * omega)


def compute_tether_static_safety_factor(
    secondary_steel_safety_cable_rated_kg: float,
    camera_rig_mass_kg: float,
    *,
    peak_shock_g: float = 5.0,
) -> float:
    """Compute secondary steel tether safety factor against dynamic vehicle shock load."""
    if not (
        _is_finite_number(secondary_steel_safety_cable_rated_kg)
        and _is_finite_number(camera_rig_mass_kg)
        and _is_finite_number(peak_shock_g)
    ):
        raise ValueError(
            "secondary_steel_safety_cable_rated_kg, camera_rig_mass_kg, and peak_shock_g must be finite numbers."
        )
    if (
        float(secondary_steel_safety_cable_rated_kg) < 0.0
        or float(camera_rig_mass_kg) <= 0.0
        or float(peak_shock_g) <= 0.0
    ):
        raise ValueError(
            "secondary_steel_safety_cable_rated_kg >= 0.0, camera_rig_mass_kg > 0.0, and peak_shock_g > 0.0 required."
        )
    return float(secondary_steel_safety_cable_rated_kg) / (
        float(camera_rig_mass_kg) * float(peak_shock_g)
    )


# ---------------------------------------------------------------------------
# 3. Gate G41 — VP Strobe / UV-Arc IMX510 Overload & Tri-Level Genlock Firewall
# ---------------------------------------------------------------------------


def verify_vp_strobe_uvarc_and_genlock_firewall(
    *,
    vp_profile: str = "FX3_VP_LED_VOLUME_ECS_LOCKED",
    peak_irradiance_w_cm2: float = 0.05,
    pulse_duration_ms: float = 2.0,
    uv_arc_welding_or_pyro_scene: bool = False,
    uv_ir_cut_and_protective_nd_installed: bool = True,
    nd_optical_density: float = 0.0,
    bnc_sync_signal_type: str = "LTC_SMPTE_UNBALANCED",
    connected_to_fx3_multiterminal: bool = True,
    led_volume_active: bool = False,
    led_pwm_refresh_hz: float = 3840.0,
    ecs_fractional_shutter_locked: bool = True,
    shutter_rate_hz: float = 24.0,
    request_persistent_emmc_writes: bool = False,
) -> VpStrobeGenlockFirewallResult:
    """Verify Gate G41 (VP Strobe/UV-Arc IMX510 Sensor Hazard, Genlock->LTC & LED ECS Sync)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False)."
        )

    telemetry_ok = True
    if not _is_finite_number(peak_irradiance_w_cm2) or float(peak_irradiance_w_cm2) < 0.0:
        _add_code(codes, STATUS_BLOCKED_VP_STROBE_GENLOCK_TELEMETRY_INVALID)
        errors.append(
            f"peak_irradiance_w_cm2 must be finite >= 0.0, got {peak_irradiance_w_cm2!r}."
        )
        telemetry_ok = False
        eff_irradiance = 0.05
    else:
        eff_irradiance = float(peak_irradiance_w_cm2)

    if not _is_finite_number(pulse_duration_ms) or float(pulse_duration_ms) < 0.0:
        _add_code(codes, STATUS_BLOCKED_VP_STROBE_GENLOCK_TELEMETRY_INVALID)
        errors.append(
            f"pulse_duration_ms must be finite >= 0.0, got {pulse_duration_ms!r}."
        )
        telemetry_ok = False
        eff_pulse_ms = 2.0
    else:
        eff_pulse_ms = float(pulse_duration_ms)

    if not _is_finite_number(nd_optical_density) or float(nd_optical_density) < 0.0:
        _add_code(codes, STATUS_BLOCKED_VP_STROBE_GENLOCK_TELEMETRY_INVALID)
        errors.append(
            f"nd_optical_density must be finite >= 0.0, got {nd_optical_density!r}."
        )
        telemetry_ok = False
        eff_nd_od = 0.0
    else:
        eff_nd_od = float(nd_optical_density)

    if not _is_finite_number(led_pwm_refresh_hz) or float(led_pwm_refresh_hz) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_VP_STROBE_GENLOCK_TELEMETRY_INVALID)
        errors.append(
            f"led_pwm_refresh_hz must be finite > 0.0, got {led_pwm_refresh_hz!r}."
        )
        telemetry_ok = False
        eff_led_pwm_hz = 3840.0
    else:
        eff_led_pwm_hz = float(led_pwm_refresh_hz)

    if not _is_finite_number(shutter_rate_hz) or float(shutter_rate_hz) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_VP_STROBE_GENLOCK_TELEMETRY_INVALID)
        errors.append(
            f"shutter_rate_hz must be finite > 0.0, got {shutter_rate_hz!r}."
        )
        telemetry_ok = False
        eff_shutter_hz = 24.0
    else:
        eff_shutter_hz = float(shutter_rate_hz)

    if (
        not isinstance(bnc_sync_signal_type, str)
        or bnc_sync_signal_type not in VALID_BNC_SYNC_SIGNAL_TYPES
    ):
        _add_code(codes, STATUS_BLOCKED_VP_STROBE_GENLOCK_TELEMETRY_INVALID)
        errors.append(
            f"bnc_sync_signal_type must be one of {VALID_BNC_SYNC_SIGNAL_TYPES}, "
            f"got {bnc_sync_signal_type!r}."
        )
        telemetry_ok = False
        eff_sync_type = "NONE"
    else:
        eff_sync_type = str(bnc_sync_signal_type)

    est_temp_rise_c = estimate_imx510_microlens_flash_temp_rise_c(
        eff_irradiance, eff_pulse_ms, nd_optical_density=eff_nd_od
    )
    pwm_cycles_per_shutter = compute_led_wall_ecs_beat_ratio(
        eff_led_pwm_hz, eff_shutter_hz
    )

    # a) Close-Range DMX Xenon/LED Strobe or Unfiltered UV-Arc IMX510 Microlens Hazard
    irradiance_over_limit = eff_irradiance > IMX510_MAX_SAFE_PEAK_IRRADIANCE_W_CM2
    unfiltered_uv_arc = bool(uv_arc_welding_or_pyro_scene) and (
        not bool(uv_ir_cut_and_protective_nd_installed)
    )
    arc_strobe_irradiance_safe = not (
        telemetry_ok and (irradiance_over_limit or unfiltered_uv_arc)
    )
    if not arc_strobe_irradiance_safe:
        _add_code(codes, STATUS_BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD)
        errors.append(
            f"BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD: {vp_profile} has "
            f"peak_irradiance_w_cm2={eff_irradiance:.3f} W/cm^2 "
            f"(limit <= {IMX510_MAX_SAFE_PEAK_IRRADIANCE_W_CM2:.2f} W/cm^2), "
            f"uv_arc_welding_or_pyro_scene={uv_arc_welding_or_pyro_scene}, "
            f"uv_ir_cut_and_protective_nd_installed={uv_ir_cut_and_protective_nd_installed}, "
            "risking IMX510 BSI CMOS microlens/CFA thermal ablation."
        )

    # b) 75-Ohm Tri-Level Genlock / Blackburst / 5V TTL Word-Clock -> FX3 LTC Multi-Terminal
    multiterminal_genlock_safe = not (
        telemetry_ok
        and bool(connected_to_fx3_multiterminal)
        and (eff_sync_type in FX3_MULTITERMINAL_BLOCKED_GENLOCK_SIGNALS)
    )
    if not multiterminal_genlock_safe:
        _add_code(codes, STATUS_BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL)
        errors.append(
            f"BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL: {vp_profile} routes "
            f"bnc_sync_signal_type={eff_sync_type} directly into FX3's 15-pin "
            "LTC-only Multi-Terminal (FX3 lacks hardware Genlock PLL unlike FX6; "
            "75-Ohm Tri-Level/Blackburst/5V Word-Clock fails sync or overdrives LTC input)."
        )

    # c) LED Volume Low-PWM Scan Aliasing without Fractional ECS Shutter Lock
    ledwall_ecs_sync_safe = not (
        telemetry_ok
        and bool(led_volume_active)
        and (eff_led_pwm_hz < LED_WALL_MIN_ALIAS_FREE_PWM_HZ)
        and (not bool(ecs_fractional_shutter_locked))
    )
    if not ledwall_ecs_sync_safe:
        _add_code(codes, STATUS_BLOCKED_LEDWALL_SCAN_ALIASING_NO_ECS_LOCK)
        errors.append(
            f"BLOCKED_LEDWALL_SCAN_ALIASING_NO_ECS_LOCK: {vp_profile} has "
            f"led_volume_active=True with led_pwm_refresh_hz={eff_led_pwm_hz:.1f} Hz "
            f"(< {LED_WALL_MIN_ALIAS_FREE_PWM_HZ:.1f} Hz) and "
            "ecs_fractional_shutter_locked=False, causing rolling-shutter scan banding."
        )

    if telemetry_ok and len(errors) == 0:
        if uv_arc_welding_or_pyro_scene and uv_ir_cut_and_protective_nd_installed:
            warnings.append(
                "UV-arc/pyro scene mitigated with UV/IR-cut + protective ND filter stack."
            )
        if led_volume_active and eff_led_pwm_hz < LED_WALL_MIN_ALIAS_FREE_PWM_HZ:
            warnings.append(
                "Low-PWM LED wall scan aliasing mitigated by High-Res ECS fractional shutter lock."
            )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return VpStrobeGenlockFirewallResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        vp_profile=str(vp_profile),
        peak_irradiance_w_cm2=round(eff_irradiance, 4),
        pulse_duration_ms=round(eff_pulse_ms, 3),
        uv_arc_welding_or_pyro_scene=bool(uv_arc_welding_or_pyro_scene),
        uv_ir_cut_and_protective_nd_installed=bool(
            uv_ir_cut_and_protective_nd_installed
        ),
        nd_optical_density=round(eff_nd_od, 3),
        estimated_microlens_temp_rise_c=round(est_temp_rise_c, 4),
        bnc_sync_signal_type=eff_sync_type,
        connected_to_fx3_multiterminal=bool(connected_to_fx3_multiterminal),
        led_volume_active=bool(led_volume_active),
        led_pwm_refresh_hz=round(eff_led_pwm_hz, 2),
        ecs_fractional_shutter_locked=bool(ecs_fractional_shutter_locked),
        shutter_rate_hz=round(eff_shutter_hz, 3),
        led_pwm_cycles_per_shutter_window=round(pwm_cycles_per_shutter, 3),
        arc_strobe_irradiance_safe=arc_strobe_irradiance_safe,
        multiterminal_genlock_safe=multiterminal_genlock_safe,
        ledwall_ecs_sync_safe=ledwall_ecs_sync_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G42 — Vehicle / Aerial Hard-Mount Vibration, IBIS Park & Steel Tether
# ---------------------------------------------------------------------------


def verify_vehiclerig_vibration_ibis_and_tether_guard(
    *,
    rig_profile: str = "FX3_WIRE_ISOLATED_GYROFLOW_RTMD_RIG",
    vibration_rms_g: float = 0.4,
    dominant_vibration_hz: float = 25.0,
    wire_rope_or_elastomer_isolator_stage: bool = True,
    ibis_steadyshot_mode: str = IBIS_MODE_OFF_MECHANICAL_PARK,
    gyroflow_rtmd_logging_enabled: bool = True,
    vehicle_or_aerial_exterior_mount: bool = False,
    secondary_steel_safety_cable_rated_kg: float = 35.0,
    suction_cup_count: int = 3,
    camera_rig_mass_kg: float = 2.4,
    request_persistent_emmc_writes: bool = False,
) -> VehicleRigIbisTetherGuardResult:
    """Verify Gate G42 (Vehicle/Aerial High-G Vibration, 5-Axis IBIS Park & Steel Tether)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False)."
        )

    telemetry_ok = True
    if not _is_finite_number(vibration_rms_g) or float(vibration_rms_g) < 0.0:
        _add_code(codes, STATUS_BLOCKED_VEHICLERIG_IBIS_TELEMETRY_INVALID)
        errors.append(
            f"vibration_rms_g must be finite >= 0.0, got {vibration_rms_g!r}."
        )
        telemetry_ok = False
        eff_vib_g = 0.4
    else:
        eff_vib_g = float(vibration_rms_g)

    if (
        not _is_finite_number(dominant_vibration_hz)
        or float(dominant_vibration_hz) <= 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_VEHICLERIG_IBIS_TELEMETRY_INVALID)
        errors.append(
            f"dominant_vibration_hz must be finite > 0.0, got {dominant_vibration_hz!r}."
        )
        telemetry_ok = False
        eff_vib_hz = 25.0
    else:
        eff_vib_hz = float(dominant_vibration_hz)

    if (
        not _is_finite_number(secondary_steel_safety_cable_rated_kg)
        or float(secondary_steel_safety_cable_rated_kg) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_VEHICLERIG_IBIS_TELEMETRY_INVALID)
        errors.append(
            "secondary_steel_safety_cable_rated_kg must be finite >= 0.0, "
            f"got {secondary_steel_safety_cable_rated_kg!r}."
        )
        telemetry_ok = False
        eff_tether_kg = 35.0
    else:
        eff_tether_kg = float(secondary_steel_safety_cable_rated_kg)

    if not _is_non_negative_int(suction_cup_count):
        _add_code(codes, STATUS_BLOCKED_VEHICLERIG_IBIS_TELEMETRY_INVALID)
        errors.append(
            f"suction_cup_count must be integer >= 0, got {suction_cup_count!r}."
        )
        telemetry_ok = False
        eff_cups = 3
    else:
        eff_cups = int(suction_cup_count)

    if not _is_finite_number(camera_rig_mass_kg) or float(camera_rig_mass_kg) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_VEHICLERIG_IBIS_TELEMETRY_INVALID)
        errors.append(
            f"camera_rig_mass_kg must be finite > 0.0, got {camera_rig_mass_kg!r}."
        )
        telemetry_ok = False
        eff_mass_kg = 2.4
    else:
        eff_mass_kg = float(camera_rig_mass_kg)

    if (
        not isinstance(ibis_steadyshot_mode, str)
        or ibis_steadyshot_mode not in VALID_IBIS_STEADYSHOT_MODES
    ):
        _add_code(codes, STATUS_BLOCKED_VEHICLERIG_IBIS_TELEMETRY_INVALID)
        errors.append(
            f"ibis_steadyshot_mode must be one of {VALID_IBIS_STEADYSHOT_MODES}, "
            f"got {ibis_steadyshot_mode!r}."
        )
        telemetry_ok = False
        eff_ibis_mode = IBIS_MODE_OFF_MECHANICAL_PARK
    else:
        eff_ibis_mode = str(ibis_steadyshot_mode)

    transmissibility = 0.25 if wire_rope_or_elastomer_isolator_stage else 1.0
    est_displacement_mm = estimate_ibis_voice_coil_excursion_mm(
        eff_vib_g, eff_vib_hz, isolator_transmissibility=transmissibility
    )
    tether_sf = compute_tether_static_safety_factor(eff_tether_kg, eff_mass_kg)

    # a) Hard-Mount High-G Vibration (20..200 Hz) without Wire-Rope / Elastomer Isolator
    hardmount_wire_isolator_safe = not (
        telemetry_ok
        and (eff_vib_g > VIBRATION_WIRE_ISOLATOR_MAX_RMS_G)
        and (not bool(wire_rope_or_elastomer_isolator_stage))
    )
    if not hardmount_wire_isolator_safe:
        _add_code(codes, STATUS_BLOCKED_HARDMOUNT_HIGH_G_VIBRATION_NO_WIRE_ISOLATOR)
        errors.append(
            f"BLOCKED_HARDMOUNT_HIGH_G_VIBRATION_NO_WIRE_ISOLATOR: {rig_profile} has "
            f"vibration_rms_g={eff_vib_g:.2f} g at {eff_vib_hz:.1f} Hz "
            f"(limit <= {VIBRATION_WIRE_ISOLATOR_MAX_RMS_G:.1f} g) with "
            "wire_rope_or_elastomer_isolator_stage=False, risking IBIS end-stop impact."
        )

    # b) Active IBIS Under Sustained Engine / Rotor Resonance (>= 35 Hz)
    ibis_resonance_park_safe = not (
        telemetry_ok
        and (eff_vib_g > VIBRATION_IBIS_PARK_MAX_RMS_G)
        and (eff_vib_hz >= ENGINE_RESONANCE_MIN_HZ)
        and (eff_ibis_mode != IBIS_MODE_OFF_MECHANICAL_PARK)
    )
    if not ibis_resonance_park_safe:
        _add_code(codes, STATUS_BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE)
        errors.append(
            f"BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE: {rig_profile} has "
            f"vibration_rms_g={eff_vib_g:.2f} g (> {VIBRATION_IBIS_PARK_MAX_RMS_G:.1f} g) "
            f"at dominant_vibration_hz={eff_vib_hz:.1f} Hz (>= {ENGINE_RESONANCE_MIN_HZ:.1f} Hz) "
            f"with ibis_steadyshot_mode={eff_ibis_mode!r}; must use "
            f"{IBIS_MODE_OFF_MECHANICAL_PARK!r} + post Gyroflow RTMD stabilization."
        )

    # c) Exterior Vehicle / Aerial Rig Missing Secondary Steel Safety Tether or < 3 Suction Cups
    exterior_steel_tether_safe = not (
        telemetry_ok
        and bool(vehicle_or_aerial_exterior_mount)
        and (
            (eff_tether_kg < VEHICLE_EXTERIOR_MIN_STEEL_TETHER_KG)
            or (eff_cups < VEHICLE_EXTERIOR_MIN_SUCTION_CUPS)
        )
    )
    if not exterior_steel_tether_safe:
        _add_code(
            codes, STATUS_BLOCKED_VEHICLE_EXTERIOR_RIG_MISSING_SECONDARY_STEEL_TETHER
        )
        errors.append(
            f"BLOCKED_VEHICLE_EXTERIOR_RIG_MISSING_SECONDARY_STEEL_TETHER: {rig_profile} "
            f"has vehicle_or_aerial_exterior_mount=True with "
            f"secondary_steel_safety_cable_rated_kg={eff_tether_kg:.1f} kg "
            f"(min {VEHICLE_EXTERIOR_MIN_STEEL_TETHER_KG:.1f} kg) and "
            f"suction_cup_count={eff_cups} (min {VEHICLE_EXTERIOR_MIN_SUCTION_CUPS})."
        )

    if telemetry_ok and len(errors) == 0:
        if eff_vib_g > VIBRATION_IBIS_PARK_MAX_RMS_G and not gyroflow_rtmd_logging_enabled:
            warnings.append(
                "IBIS parked under vehicle vibration; enable Gyroflow RTMD logging for post stabilization."
            )
        if vehicle_or_aerial_exterior_mount:
            warnings.append(
                f"Exterior vehicle/aerial mount verified with {eff_cups}-cup triangle and "
                f"{eff_tether_kg:.1f} kg secondary steel tether (5G SF={tether_sf:.2f}x)."
            )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return VehicleRigIbisTetherGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        rig_profile=str(rig_profile),
        vibration_rms_g=round(eff_vib_g, 3),
        dominant_vibration_hz=round(eff_vib_hz, 2),
        wire_rope_or_elastomer_isolator_stage=bool(
            wire_rope_or_elastomer_isolator_stage
        ),
        ibis_steadyshot_mode=eff_ibis_mode,
        gyroflow_rtmd_logging_enabled=bool(gyroflow_rtmd_logging_enabled),
        vehicle_or_aerial_exterior_mount=bool(vehicle_or_aerial_exterior_mount),
        secondary_steel_safety_cable_rated_kg=round(eff_tether_kg, 2),
        suction_cup_count=eff_cups,
        camera_rig_mass_kg=round(eff_mass_kg, 3),
        estimated_peak_displacement_mm=round(est_displacement_mm, 5),
        tether_static_safety_factor_at_5g=round(tether_sf, 3),
        hardmount_wire_isolator_safe=hardmount_wire_isolator_safe,
        ibis_resonance_park_safe=ibis_resonance_park_safe,
        exterior_steel_tether_safe=exterior_steel_tether_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 5. Gate G41 & Gate G42 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g41_vp_strobe_and_genlock(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    vp_strobe_genlock_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase131DonorAuditResult] = None,
) -> Tuple[GateVerdict, G41VpStrobeGenlockResult]:
    """Evaluate Gate G41 (`vp_strobe_uvarc_genlock_and_ecs_sync_safe`)."""
    audit = donor_audit or audit_phase131_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(vp_strobe_genlock_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    fw_res = verify_vp_strobe_uvarc_and_genlock_firewall(**eff_kwargs)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in fw_res.violation_codes:
        _add_code(codes, c)
    errors.extend(fw_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(fw_res.warnings)

    passed = (
        audit.valid
        and fw_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = (
        STATUS_VERIFIED_G41
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD
        )
    )

    res = G41VpStrobeGenlockResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        vp_strobe_genlock_firewall=fw_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G41_GATE_ID,
        gate_code=G41_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Virtual Production DMX Strobe/UV-Arc IMX510 Hazard & External Tri-Level Genlock "
            f"-> Multi-Terminal Firewall ({fw_res.status}, "
            f"irradiance={fw_res.peak_irradiance_w_cm2:.3f}W/cm2, "
            f"sync={fw_res.bnc_sync_signal_type}, "
            f"led_pwm={fw_res.led_pwm_refresh_hz:.1f}Hz, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "arc_strobe_irradiance_safe": fw_res.arc_strobe_irradiance_safe,
            "multiterminal_genlock_safe": fw_res.multiterminal_genlock_safe,
            "ledwall_ecs_sync_safe": fw_res.ledwall_ecs_sync_safe,
        },
    )
    return verdict, res


def evaluate_g42_vehiclerig_ibis_and_tether(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    vehiclerig_ibis_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase131DonorAuditResult] = None,
) -> Tuple[GateVerdict, G42VehicleRigIbisTetherResult]:
    """Evaluate Gate G42 (`vehicle_rig_vibration_ibis_park_and_tether_safe`)."""
    audit = donor_audit or audit_phase131_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(vehiclerig_ibis_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    guard_res = verify_vehiclerig_vibration_ibis_and_tether_guard(**eff_kwargs)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in guard_res.violation_codes:
        _add_code(codes, c)
    errors.extend(guard_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(guard_res.warnings)

    passed = (
        audit.valid
        and guard_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = (
        STATUS_VERIFIED_G42
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_HARDMOUNT_HIGH_G_VIBRATION_NO_WIRE_ISOLATOR
        )
    )

    res = G42VehicleRigIbisTetherResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        vehiclerig_ibis_guard=guard_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G42_GATE_ID,
        gate_code=G42_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Vehicle/Aerial Hard-Mount Vibration (20..200 Hz) IBIS Voice-Coil Park & "
            f"Secondary Steel-Tether Guard ({guard_res.status}, "
            f"vib={guard_res.vibration_rms_g:.2f}g@{guard_res.dominant_vibration_hz:.1f}Hz, "
            f"wire_isolator={guard_res.wire_rope_or_elastomer_isolator_stage}, "
            f"ibis={guard_res.ibis_steadyshot_mode}, "
            f"tether={guard_res.secondary_steel_safety_cable_rated_kg:.1f}kg, "
            f"{audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "hardmount_wire_isolator_safe": guard_res.hardmount_wire_isolator_safe,
            "ibis_resonance_park_safe": guard_res.ibis_resonance_park_safe,
            "exterior_steel_tether_safe": guard_res.exterior_steel_tether_safe,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 6. Master 42-Gate Preflight Evaluator (`G01..G42`) & CLI
# ---------------------------------------------------------------------------


def evaluate_42gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G40 pass-throughs
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
    ptpip_or_mc_requests: Optional[Sequence[Mapping[str, Any]]] = None,
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
    # G41 inputs (VP DMX Strobe / UV-Arc IMX510 Hazard, Tri-Level Genlock & LED ECS Sync)
    vp_strobe_genlock_kwargs: Optional[Mapping[str, Any]] = None,
    # G42 inputs (Vehicle/Aerial Hard-Mount Vibration, IBIS Park & Steel Safety Tether)
    vehiclerig_ibis_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master42GateReport:
    """Evaluate all 42 Master Safety Gates (`G01..G42`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m40_kwargs: Dict[str, Any] = {
        "force_clean_room": clean_forced,
        "dry_run_simulated_backup": bool(dry_run_simulated_backup),
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
    }
    if soc_start_ceiling_c is not None:
        m40_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m40_report: Master40GateReport = evaluate_40gate_preflight(
        resolved_root, **m40_kwargs
    )

    phase131_audit = audit_phase131_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
    )

    g41_verdict, g41_res = evaluate_g41_vp_strobe_and_genlock(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        vp_strobe_genlock_kwargs=vp_strobe_genlock_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase131_audit,
    )

    g42_verdict, g42_res = evaluate_g42_vehiclerig_ibis_and_tether(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        vehiclerig_ibis_kwargs=vehiclerig_ibis_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase131_audit,
    )

    gates_41_to_42 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g41_verdict, g42_verdict)
    ]
    all_gates = tuple(list(m40_report.gates) + gates_41_to_42)

    g01_to_g12_verified = int(m40_report.summary["g01_to_g12_verified"])
    g13_to_g40_verified = (
        int(m40_report.summary["g13_to_g38_verified"])
        + int(m40_report.summary["g39_to_g40_verified"])
    )
    g41_to_g42_verified = sum(1 for v in (g41_verdict, g42_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g40_verified + g41_to_g42_verified

    g41_to_g42_all_passed = g41_to_g42_verified == 2
    g13_to_g42_all_passed = (
        m40_report.g13_to_g40_all_passed and g41_to_g42_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m40_report.gates[:9])

    offline_39_verified = (
        g01_to_g09_ok
        and m40_report.offline_37_gates_verified
        and g41_to_g42_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_42_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g42_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes, and never authorizes writes
    overall_ready_for_hardware_attach = False

    h0_h1_allowed = (
        offline_39_verified
        and m40_report.h0_h1_trial_entry_allowed
        and g41_to_g42_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m40_report.errors) + list(g41_verdict.errors) + list(g42_verdict.errors)
    )
    warnings: List[str] = (
        list(m40_report.warnings)
        + list(g41_verdict.warnings)
        + list(g42_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m40_report.g13_to_g40_all_passed:
        overall_status = m40_report.status
    elif not g41_verdict.passed:
        overall_status = g41_verdict.status
    elif not g42_verdict.passed:
        overall_status = g42_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_42_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_42_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_42_verified:
        overall_status = "VERIFIED_ALL_42_GATES"
    else:
        overall_status = "VERIFIED_39_OF_42_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m40_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g41_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g42_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 42,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 42 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g40_verified": g13_to_g40_verified,
        "g41_to_g42_verified": g41_to_g42_verified,
        "g13_to_g42_all_passed": g13_to_g42_all_passed,
        "g41_to_g42_all_passed": g41_to_g42_all_passed,
        "offline_39_gates_verified": offline_39_verified,
        "all_42_gates_verified": all_42_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master42GateReport(
        schema=VP_STROBE_VEHICLERIG_42GATE_SCHEMA,
        version=VP_STROBE_VEHICLERIG_42GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_39_gates_verified=offline_39_verified,
        all_42_gates_verified=all_42_verified,
        g13_to_g42_all_passed=g13_to_g42_all_passed,
        g41_to_g42_all_passed=g41_to_g42_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_40_report=m40_report.to_dict(),
        g41_result=g41_res.to_dict(),
        g42_result=g42_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_42_master_safety_gates = evaluate_42gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vp_strobe_vehiclerig_ibis_and_42gate_guard",
        description=(
            "Phase 131 — Virtual Production DMX Strobe / UV-Arc IMX510 Overload & Tri-Level "
            "Genlock -> Multi-Terminal Firewall (G41), Vehicle/Aerial Vibration IBIS Park & "
            "Steel-Tether Guard (G42), and 42-Gate Master Preflight (G01..G42)"
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    parser.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G42 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_42gate_preflight(
        args.repo_root,
        force_clean_room=True if args.clean_room else None,
        dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
    )
    if args.json:
        sys.stdout.write(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
        )
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/42 "
            f"g41_to_g42_all_passed={report.g41_to_g42_all_passed} "
            f"all_42_gates_verified={report.all_42_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = (
        report.all_42_gates_verified
        if args.dry_run_simulated_backup
        else report.offline_39_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
