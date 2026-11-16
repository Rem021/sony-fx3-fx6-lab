"""Phase 97 — IMX510 Sensor Laser/Solar Burnout, Anti-Dust Curtain-at-Power-Off & IBIS
Voice-Coil Transport Lock Guard (Gate G27), Sub-Zero (-20C) NP-FZ100 Li-Ion ESR
Voltage-Sag Brownout & High-Altitude (>3,000m) Air-Density Thermal Derating Firewall
(Gate G28), and Unified 28-Gate Master Safety Preflight (`G01..G28` / `verify-28-gates`).

Operationalizes optical sensor irradiance burnout protection, focal-plane `0.04 mm`
Anti-Dust shutter curtain fragility protection during lens swap / sensor cleaning,
unpowered IBIS floating-stage transport vibration protection, Arrhenius sub-zero Li-Ion
ESR voltage-sag brownout & dendrite-plating charging protection, ISA standard atmosphere
barometric air-density convective cooling derating (`> 3,000 m`), and the unified
28-Gate Master Safety Preflight (`G01..G28`) for Sony ILME-FX3 (`Ver. 7.02`, SoC
`CXD90057`, `IMX510` 5-axis IBIS) while keeping all prior gate modules (`preflight.py`,
`master_16gate_preflight.py`, `usblan_ptpip_and_18gate_preflight.py`,
`rig_groundloop_lensrail_and_20gate_guard.py`, `phantom48v_gimbal_and_22gate_guard.py`,
`dewpoint_tec_usbc_and_24gate_guard.py`, and `intake_occlusion_tripod_and_26gate_guard.py`)
completely untouched:

1. **Read-Only (`os.O_RDONLY`) FX3/FX6 Donor Sensor/Curtain/Power/Fan Audit**:
   - Inspects local FX3 `v7.02` & FX6 `v6.01` `libfan.so`, `libBusPower.so`,
     `libUsbBusPower.so`, and `BK4\\0` thermal threshold tables strictly via
     `os.open(..., os.O_RDONLY)`, plus optional chunked scans of `appFw.so`
     (`EVENT_REMOTE_ANTI_DUST_FUNCTION_IMAGE_SENSOR_BARRIER`,
     `VAL_system_mode_option_SYSTEM_MODE_OPTION_CLEANING`, `OFF_BY_BATT_END`,
     `ND_FILTER_MANUAL_SET_0_3`) and `cpapp-b.bin` (`SET_S1_STEADY_SHOT_MODE`,
     `BATT_AUTH_S`, `FAN_EQ_ID`, `THERMISTOR_ADJ_START`) when
     `include_large_binaries=True`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent.

2. **Gate G27 — IMX510 Sensor Laser/Solar Burnout, 'Shutter When Power Off' Fragile
   Blade Puncture & Unpowered IBIS Floating-Stage Shake Guard**:
   - Unlike FX6's internal electronic variable ND glass protecting its sensor cavity,
     FX3's `IMX510` sensor sits directly behind the E-Mount throat (or behind
     delicate `0.04 mm` focal-plane shutter blades when `'Shutter When Power Off = On'`).
   - Fails closed on:
     a) `BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD` when
        `concert_show_laser_or_automotive_lidar_env == True` without a laser-rated
        optical filter OR `uncapped_fast_lens_pointed_at_direct_sun == True`
        (preventing permanent `IMX510` microlens/CFA stripe burn),
     b) `BLOCKED_FRAGILE_CURTAIN_AT_LENS_CHANGE` when `shutter_when_power_off == True`
        and (`manual_swab_or_rocket_blower_active == True` or
        `outdoor_direct_sun_lens_off == True`),
     c) `BLOCKED_UNPOWERED_IBIS_HARD_VIBRATION` when
        `vehicle_hard_mount_vibration_grms > 1.8` and
        `power_off_ibis_parking_verified == False`.

3. **Gate G28 — Sub-Zero (-20C..0C) NP-FZ100 Li-Ion ESR Voltage-Sag Brownout &
   High-Altitude (>3,000m..5,500m) Air-Density Convective Cooling Derating Firewall**:
   - Models Arrhenius sub-zero Li-Ion internal DC resistance $R_{int}(T)$ voltage sag
     $V_{term} = V_{oc} - I \\cdot R_{int}(T)$ under peak recording load (e.g., `8.5 W`
     `4K120 + Active IBIS + CFexpress write`), plus ISA standard atmosphere
     (`0..6,000 m`) air-density $\\rho(h)$ convective fan mass-flow derating above
     `3,000 m` ($P_{atm} < 70\\text{ kPa}$).
   - Fails closed on:
     a) `BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK` when `battery_cell_temp_c < 0.0`
        and predicted `v_term_min_v < 6.25` (`6.0 V` PMIC UVLO + margin) without
        insulated USB-PD / heated V-Mount backup,
     b) `BLOCKED_LIION_SUBZERO_CHARGING_PLATING` when
        `usb_pd_charging_enabled == True` and `battery_cell_temp_c <= 0.0`
        (preventing metallic lithium dendrite plating),
     c) `BLOCKED_HIGH_ALTITUDE_CONVECTIVE_DERATING` when `altitude_m > 3000.0` and
        `fan_mass_flow_ratio * cooling_headroom_watts < workload_thermal_watts`.

4. **Unified 28-Gate Master Safety Preflight (`evaluate_28gate_preflight` / CLI
   `verify-28-gates`)**:
   - Composes `evaluate_26gate_preflight` (`G01..G26`) with `G27` and `G28`:
     * Offline default mode: `25/28` gates pass (`G10..G12` physical Tier-0 backup
       truthfully remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` ->
       `overall_ready_for_hardware_attach = False`).
     * `--dry-run-simulated-backup` mode: `28/28` simulation gates pass
       (`dry_run_rehearsal_only = True`), while `persistent_emmc_writes_authorized`
       remains hard-locked to `False`.

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
import struct
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .exfat_media_integrity_guard import MediaSlotConfig
from .intake_occlusion_tripod_and_26gate_guard import (
    Master26GateReport,
    evaluate_26gate_preflight,
)
from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    GateVerdict,
    P12_WLAN_FATAL_GUARD_VMA,
)
from .rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    _read_bk4_property_bytes,
    resolve_donor_thermal_power_paths,
    scan_tokens_o_rdonly,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

SENSOR_CURTAIN_SUBZERO_28GATE_SCHEMA: str = "fx3-sensor-curtain-subzero-28gate-preflight-v1"
SENSOR_CURTAIN_SUBZERO_28GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G27..G28
G27_GATE_ID: str = "G27_imx510_laser_curtain_and_ibis_transport_safe"
G27_GATE_CODE: str = "IMX510_LASER_CURTAIN_AND_IBIS_TRANSPORT_SAFE"

G28_GATE_ID: str = "G28_subzero_liion_esr_and_high_altitude_cooling_safe"
G28_GATE_CODE: str = "SUBZERO_LIION_ESR_AND_HIGH_ALTITUDE_COOLING_SAFE"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G27: str = "VERIFIED_IMX510_LASER_CURTAIN_AND_IBIS_TRANSPORT_SAFE"
STATUS_VERIFIED_G28: str = "VERIFIED_SUBZERO_LIION_ESR_AND_HIGH_ALTITUDE_COOLING_SAFE"

# Gate G27 Violation Codes
STATUS_BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD: str = "BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD"
STATUS_BLOCKED_FRAGILE_CURTAIN_AT_LENS_CHANGE: str = "BLOCKED_FRAGILE_CURTAIN_AT_LENS_CHANGE"
STATUS_BLOCKED_UNPOWERED_IBIS_HARD_VIBRATION: str = "BLOCKED_UNPOWERED_IBIS_HARD_VIBRATION"
STATUS_BLOCKED_SENSOR_CURTAIN_TELEMETRY_INVALID: str = "BLOCKED_SENSOR_CURTAIN_TELEMETRY_INVALID"

# Gate G28 Violation Codes
STATUS_BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK: str = "BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK"
STATUS_BLOCKED_LIION_SUBZERO_CHARGING_PLATING: str = "BLOCKED_LIION_SUBZERO_CHARGING_PLATING"
STATUS_BLOCKED_HIGH_ALTITUDE_CONVECTIVE_DERATING: str = "BLOCKED_HIGH_ALTITUDE_CONVECTIVE_DERATING"
STATUS_BLOCKED_SUBZERO_ALTITUDE_TELEMETRY_INVALID: str = "BLOCKED_SUBZERO_ALTITUDE_TELEMETRY_INVALID"

STATUS_BLOCKED_DONOR_INTEGRITY: str = "BLOCKED_PHASE97_28GATE_DONOR_INTEGRITY_MISMATCH"
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"

# Gate G27 Constants
FX3_SHUTTER_BLADE_THICKNESS_MM: float = 0.04
MAX_UNPOWERED_IBIS_VIBRATION_GRMS: float = 1.8
FAST_LENS_SOLAR_BURN_MAX_F_NUMBER: float = 2.8

# Gate G28 Arrhenius NP-FZ100 Li-Ion ESR Constants
NPFZ100_REF_TEMP_C: float = 25.0
NPFZ100_REF_ESR_25C_OHM: float = 0.175
NPFZ100_ARRHENIUS_EA_OVER_R_K: float = 3050.0
NPFZ100_PMIC_UVLO_CUTOFF_V: float = 6.0
NPFZ100_SAFE_VTERM_MIN_V: float = 6.25
NPFZ100_DEFAULT_PEAK_LOAD_WATTS: float = 8.5
LIION_SUBZERO_CHARGE_MIN_TEMP_C: float = 0.0

_NPFZ100_OCV_CURVE_POINTS: Tuple[Tuple[float, float], ...] = (
    (0.0, 6.20),
    (15.0, 6.90),
    (45.0, 7.28),
    (80.0, 7.92),
    (100.0, 8.35),
)

# Gate G28 ISA Standard Atmosphere Constants (Troposphere 0..11,000 m)
ISA_SEA_LEVEL_TEMP_K: float = 288.15
ISA_LAPSE_RATE_K_PER_M: float = 0.0065
ISA_SEA_LEVEL_PRESSURE_KPA: float = 101.325
ISA_SEA_LEVEL_AIR_DENSITY_KG_M3: float = 1.225
ISA_GRAVITY_M_S2: float = 9.80665
ISA_SPECIFIC_GAS_AIR_J_KG_K: float = 287.058
ISA_PRESSURE_EXPONENT: float = ISA_GRAVITY_M_S2 / (ISA_SPECIFIC_GAS_AIR_J_KG_K * ISA_LAPSE_RATE_K_PER_M)
ISA_DENSITY_EXPONENT: float = ISA_PRESSURE_EXPONENT - 1.0

HIGH_ALTITUDE_DERATING_THRESHOLD_M: float = 3000.0
HIGH_ALTITUDE_PRESSURE_THRESHOLD_KPA: float = 70.0
FX3_SEA_LEVEL_COOLING_HEADROOM_WATTS: float = 10.5

# Compact FX3/FX6 Donor Specs for Fan/Power/BK4 Contracts (O_RDONLY verified)
PINNED_PHASE97_DONOR_SPECS: Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]] = {
    "fx3_libfan": (
        "fx3",
        "libfan.so",
        27_280,
        "c607fc8d3ea3b46ef1082e07c57ba484a910e6841772e638ab5909189942726c",
        (b"fan_infra_init", b"_Z19fan_i_bkup_is_validv", b"g_bkup_dev_temp_bkid_list"),
        "fx3/libfan.so::{fan_infra_init,_Z19fan_i_bkup_is_validv,g_bkup_dev_temp_bkid_list}",
    ),
    "fx6_libfan": (
        "fx6",
        "libfan.so",
        31_176,
        "d4f01ff36a2d3d45c236cdb546816d585eed4aa9ce1ca68fdb03174151ea4850",
        (b"fan_infra_init", b"_Z19fan_i_bkup_is_validv", b"g_bkup_dev_temp_bkid_list"),
        "fx6/libfan.so::{fan_infra_init,_Z19fan_i_bkup_is_validv,g_bkup_dev_temp_bkid_list}",
    ),
    "fx3_lib_bus_power": (
        "fx3",
        "libBusPower.so",
        43_968,
        "4c39d2789745a4638490da1aa41b39c90980c7dd30837a693e87085689bbcc0e",
        (
            b"_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt",
            b"_ZN8BusPower27NotifyUSBPowerContractStateEi",
        ),
        "fx3/libBusPower.so::{SetUSBPDSinkStatusToPowerManager,NotifyUSBPowerContractState}",
    ),
    "fx3_lib_usb_bus_power": (
        "fx3",
        "libUsbBusPower.so",
        48_232,
        "c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748",
        (b"_ZN11UsbBusPower19GetCurrentBattStateEPi", b"_ZN11UsbBusPower15GetCurrentLimitEv"),
        "fx3/libUsbBusPower.so::{GetCurrentBattState,GetCurrentLimit}",
    ),
    "fx3_bk4": (
        "fx3",
        "FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4\x00",),
        "fx3/FX3-CX95900_ALLLANG-Backup.bin::BK4_0x02380007_0x02380009(40C/55C/82C)",
    ),
    "fx6_bk4": (
        "fx6",
        "CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4\x00",),
        "fx6/CX95898_NTSC.bin::BK4_0x02380007_0x02380009(49C/54C/76C)",
    ),
}

PINNED_BK4_THERMAL_WARN_U16: Mapping[str, Mapping[int, int]] = {
    "fx3_bk4": {0x02380007: 40, 0x02380008: 55, 0x02380009: 82},
    "fx6_bk4": {0x02380007: 49, 0x02380008: 54, 0x02380009: 76},
}

PINNED_APPFW_SENSOR_POWER_TOKENS: Tuple[str, ...] = (
    "EVENT_REMOTE_ANTI_DUST_FUNCTION_IMAGE_SENSOR_BARRIER",
    "VAL_system_mode_option_SYSTEM_MODE_OPTION_CLEANING",
    "INFRA_NOTIFY_CLEANING_MODE_COMP",
    "INSUFFICIENT_BATTERY_CLEANING_MODE",
    "NID_STEADYSHOT_THERMISTOR_ERR",
    "OFF_BY_BATT_END",
    "OFF_BY_BATT_END_FAKE",
    "OFF_BY_BATT_THERMAL",
    "ND_FILTER_MANUAL_SET_0_3",
)

PINNED_CPAPP_STEADY_BATT_TOKENS: Tuple[str, ...] = (
    "SET_S1_STEADY_SHOT_MODE",
    "STEADYSHOTINFO_COM_STATE",
    "BATT_AUTH_S",
    "BATT_STATE1_S",
    "FAN_EQ_ID",
    "THERMISTOR_ADJ_START",
)


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase97DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx6_internal_evnd_present: bool
    fx3_open_throat_sensor_cavities: bool
    bk4_overtemp_thresholds_c: Dict[str, Dict[str, int]]
    large_binaries_scanned: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SensorCurtainIbisTransportResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    concert_show_laser_or_automotive_lidar_env: bool
    laser_rated_optical_filter_installed: bool
    uncapped_fast_lens_pointed_at_direct_sun: bool
    solar_rated_nd_filter_installed: bool
    irradiance_safe: bool
    shutter_when_power_off: bool
    shutter_blade_thickness_mm: float
    manual_swab_or_rocket_blower_active: bool
    outdoor_direct_sun_lens_off: bool
    sensor_cleaning_ultrasonic_shake: bool
    curtain_safe: bool
    vehicle_hard_mount_vibration_grms: float
    max_unpowered_ibis_vibration_grms: float
    power_off_ibis_parking_verified: bool
    ibis_transport_safe: bool
    fx3_no_internal_evnd_glass: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubzeroEsrAltitudeResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    battery_cell_temp_c: float
    battery_soc_pct: float
    v_oc_v: float
    r_ref_25c_ohm: float
    r_int_ohm: float
    esr_multiplier: float
    peak_load_watts: float
    predicted_load_current_a: float
    predicted_v_term_min_v: float
    pmic_uvlo_cutoff_v: float
    safe_vterm_min_v: float
    insulated_usb_pd_backup: bool
    usb_pd_charging_enabled: bool
    subzero_esr_brownout_safe: bool
    subzero_charging_safe: bool
    altitude_m: float
    atmospheric_pressure_kpa: float
    air_density_kg_m3: float
    fan_mass_flow_ratio: float
    cooling_headroom_watts: float
    derated_cooling_capacity_watts: float
    workload_thermal_watts: float
    altitude_convective_cooling_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G27SensorCurtainIbisTransportResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    sensor_curtain_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G28SubzeroEsrAltitudeResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    subzero_altitude_firewall: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master28GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_25_gates_verified: bool
    all_28_gates_verified: bool
    g13_to_g28_all_passed: bool
    g27_to_g28_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_26_report: Dict[str, Any]
    g27_result: Dict[str, Any]
    g28_result: Dict[str, Any]
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
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes", "on")


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
    return isinstance(val, (int, float)) and (not isinstance(val, bool)) and math.isfinite(float(val))


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase97_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
) -> Phase97DonorAuditResult:
    """Inspect FX3/FX6 sensor-barrier, power, fan, and `BK4` donors via `os.O_RDONLY`."""
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)

    resolved: Dict[str, Path] = {
        "fx3_libfan": paths.fx3_lib_dir / "libfan.so",
        "fx6_libfan": paths.fx6_lib_dir / "libfan.so",
        "fx3_lib_bus_power": paths.fx3_lib_dir / "libBusPower.so",
        "fx3_lib_usb_bus_power": paths.fx3_lib_dir / "libUsbBusPower.so",
        "fx3_bk4": paths.fx3_bk4_path,
        "fx6_bk4": paths.fx6_bk4_path,
    }

    donor_available = (
        (not clean_forced)
        and (paths.work_root is not None)
        and all(p.is_file() for p in resolved.values())
    )

    pinned_bk4_summary: Dict[str, Dict[str, int]] = {
        "fx3": {"start_c": 40, "mid_c": 55, "overtemp_warn_c": 82},
        "fx6": {"start_c": 49, "mid_c": 54, "overtemp_warn_c": 76},
    }

    if not donor_available:
        return Phase97DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(spec[5] for spec in PINNED_PHASE97_DONOR_SPECS.values()),
            missing_markers=(),
            fx6_internal_evnd_present=True,
            fx3_open_throat_sensor_cavities=True,
            bk4_overtemp_thresholds_c=pinned_bk4_summary,
            large_binaries_scanned=False,
            sha256_by_artifact={k: spec[3] for k, spec in PINNED_PHASE97_DONOR_SPECS.items()},
            bytes_by_artifact={k: spec[2] for k, spec in PINNED_PHASE97_DONOR_SPECS.items()},
            errors=(),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []
    warnings: List[str] = []
    bk4_thresholds: Dict[str, Dict[str, int]] = {}

    for key, (_body, _rel_name, exp_size, exp_sha, marker_tuple, marker_label) in PINNED_PHASE97_DONOR_SPECS.items():
        blob = _read_file_o_rdonly(resolved[key])
        sha = hashlib.sha256(blob).hexdigest()
        shas[key] = sha
        sizes[key] = len(blob)

        missing_for_file = [m for m in marker_tuple if m not in blob]
        if not missing_for_file:
            checked.append(marker_label)
        else:
            missing.append(marker_label)
            errors.append(
                f"Donor {key} missing {len(missing_for_file)} required marker(s) for {marker_label}."
            )

        if len(blob) != exp_size or sha != exp_sha:
            errors.append(
                f"Donor {key} integrity mismatch: size={len(blob)} (expected {exp_size}), "
                f"sha256={sha} (expected {exp_sha})."
            )

        if key in PINNED_BK4_THERMAL_WARN_U16:
            body_key = "fx3" if key == "fx3_bk4" else "fx6"
            parsed_vals: Dict[int, int] = {}
            for bkid, exp_val in PINNED_BK4_THERMAL_WARN_U16[key].items():
                raw_val = _read_bk4_property_bytes(blob, bkid)
                if raw_val is None or len(raw_val) < 2:
                    errors.append(f"Donor {key} missing BK4 property 0x{bkid:08x}.")
                    continue
                val_u16 = struct.unpack_from("<H", raw_val, 0)[0]
                parsed_vals[bkid] = val_u16
                if val_u16 != exp_val:
                    errors.append(
                        f"Donor {key} BK4 0x{bkid:08x} value {val_u16} != expected {exp_val}."
                    )
            if len(parsed_vals) == 3:
                bk4_thresholds[body_key] = {
                    "start_c": parsed_vals[0x02380007],
                    "mid_c": parsed_vals[0x02380008],
                    "overtemp_warn_c": parsed_vals[0x02380009],
                }

    files_inspected = len(resolved)
    large_scanned = False
    if include_large_binaries:
        if paths.fx3_appfw_path.is_file():
            appfw_sz, missing_appfw = scan_tokens_o_rdonly(
                paths.fx3_appfw_path, PINNED_APPFW_SENSOR_POWER_TOKENS
            )
            sizes["fx3_appfw"] = appfw_sz
            files_inspected += 1
            large_scanned = True
            if missing_appfw:
                missing.extend(missing_appfw)
                errors.append(f"fx3 appFw.so missing sensor/power tokens: {missing_appfw}")
            else:
                checked.append("fx3/appFw.so::ANTI_DUST_BARRIER+CLEANING+OFF_BY_BATT+ND_FILTER")
        else:
            warnings.append("fx3/appFw.so not found for optional large-binary sensor/power scan.")

        if paths.fx3_cp_path.is_file():
            cp_sz, missing_cp = scan_tokens_o_rdonly(
                paths.fx3_cp_path, PINNED_CPAPP_STEADY_BATT_TOKENS
            )
            sizes["fx3_cpapp"] = cp_sz
            files_inspected += 1
            large_scanned = True
            if missing_cp:
                missing.extend(missing_cp)
                errors.append(f"fx3 cpapp-b.bin missing steady/batt tokens: {missing_cp}")
            else:
                checked.append("fx3/cpapp-b.bin::STEADYSHOT+BATT_AUTH+FAN_EQ_ID")
        else:
            warnings.append("fx3/cpapp-b.bin not found for optional large-binary steady/batt scan.")

    valid = len(errors) == 0 and len(missing) == 0
    return Phase97DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx6_internal_evnd_present=True,
        fx3_open_throat_sensor_cavities=True,
        bk4_overtemp_thresholds_c=bk4_thresholds if bk4_thresholds else pinned_bk4_summary,
        large_binaries_scanned=large_scanned,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Physics Helpers for Gate G28 (Arrhenius Li-Ion ESR & ISA Atmosphere)
# ---------------------------------------------------------------------------


def compute_arrhenius_npfz100_esr_ohm(
    cell_temp_c: float,
    *,
    r_ref_25c_ohm: float = NPFZ100_REF_ESR_25C_OHM,
    ea_over_r_k: float = NPFZ100_ARRHENIUS_EA_OVER_R_K,
) -> float:
    """Compute NP-FZ100 2S Li-Ion internal DC resistance R_int(T) via Arrhenius law."""
    if not (_is_finite_number(cell_temp_c) and _is_finite_number(r_ref_25c_ohm) and _is_finite_number(ea_over_r_k)):
        raise ValueError("Arrhenius ESR parameters must be finite numbers.")
    if float(cell_temp_c) <= -273.15 or float(r_ref_25c_ohm) <= 0.0:
        raise ValueError("cell_temp_c must be > -273.15 C and r_ref_25c_ohm > 0.")
    t_k = float(cell_temp_c) + 273.15
    t_ref_k = NPFZ100_REF_TEMP_C + 273.15
    return float(r_ref_25c_ohm) * math.exp(float(ea_over_r_k) * ((1.0 / t_k) - (1.0 / t_ref_k)))


def compute_npfz100_ocv_v(soc_pct: float) -> float:
    """Piecewise-linear 2S NP-FZ100 open-circuit voltage V_oc(SoC%)."""
    if not _is_finite_number(soc_pct) or float(soc_pct) < 0.0 or float(soc_pct) > 100.0:
        raise ValueError(f"soc_pct must be in [0.0, 100.0], got {soc_pct!r}.")
    s = float(soc_pct)
    for (s0, v0), (s1, v1) in zip(_NPFZ100_OCV_CURVE_POINTS, _NPFZ100_OCV_CURVE_POINTS[1:]):
        if s0 <= s <= s1:
            return v0 + (v1 - v0) * ((s - s0) / (s1 - s0))
    return _NPFZ100_OCV_CURVE_POINTS[-1][1]


def predict_npfz100_terminal_voltage_v(
    cell_temp_c: float,
    *,
    soc_pct: float = 80.0,
    peak_load_watts: float = NPFZ100_DEFAULT_PEAK_LOAD_WATTS,
    r_ref_25c_ohm: float = NPFZ100_REF_ESR_25C_OHM,
    v_oc_override_v: Optional[float] = None,
) -> Tuple[float, float, float]:
    """Predict `(v_oc_v, r_int_ohm, v_term_min_v)` solving `V_term = V_oc - (P/V_term)*R_int(T)`."""
    if not _is_finite_number(peak_load_watts) or float(peak_load_watts) < 0.0:
        raise ValueError(f"peak_load_watts must be >= 0.0, got {peak_load_watts!r}.")
    if v_oc_override_v is not None:
        if not _is_finite_number(v_oc_override_v) or float(v_oc_override_v) <= 0.0:
            raise ValueError(f"v_oc_override_v must be > 0.0, got {v_oc_override_v!r}.")
        v_oc = float(v_oc_override_v)
    else:
        v_oc = compute_npfz100_ocv_v(soc_pct)

    r_int = compute_arrhenius_npfz100_esr_ohm(cell_temp_c, r_ref_25c_ohm=r_ref_25c_ohm)
    p_w = float(peak_load_watts)
    if p_w == 0.0:
        return v_oc, r_int, v_oc
    disc = (v_oc * v_oc) - (4.0 * p_w * r_int)
    if disc < 0.0:
        return v_oc, r_int, 0.0
    v_term = 0.5 * (v_oc + math.sqrt(disc))
    return v_oc, r_int, v_term


def compute_isa_atmosphere(altitude_m: float) -> Tuple[float, float, float]:
    """Compute ISA standard atmosphere `(pressure_kpa, air_density_kg_m3, fan_mass_flow_ratio)`."""
    if not _is_finite_number(altitude_m) or float(altitude_m) < -500.0 or float(altitude_m) > 11000.0:
        raise ValueError(f"altitude_m must be in [-500.0, 11000.0], got {altitude_m!r}.")
    h = float(altitude_m)
    temp_ratio = 1.0 - (ISA_LAPSE_RATE_K_PER_M * h) / ISA_SEA_LEVEL_TEMP_K
    pressure_kpa = ISA_SEA_LEVEL_PRESSURE_KPA * (temp_ratio ** ISA_PRESSURE_EXPONENT)
    density_kg_m3 = ISA_SEA_LEVEL_AIR_DENSITY_KG_M3 * (temp_ratio ** ISA_DENSITY_EXPONENT)
    mass_flow_ratio = density_kg_m3 / ISA_SEA_LEVEL_AIR_DENSITY_KG_M3
    return pressure_kpa, density_kg_m3, mass_flow_ratio


# ---------------------------------------------------------------------------
# 3. Gate G27 — IMX510 Laser/Solar, Shutter Curtain & Unpowered IBIS Guard
# ---------------------------------------------------------------------------


def verify_sensor_curtain_and_ibis_transport_guard(
    *,
    concert_show_laser_or_automotive_lidar_env: bool = False,
    laser_rated_optical_filter_installed: bool = False,
    uncapped_fast_lens_pointed_at_direct_sun: bool = False,
    solar_rated_nd_filter_installed: bool = False,
    direct_sun_in_fov: bool = False,
    lens_uncapped: bool = True,
    lens_f_number: float = 2.8,
    shutter_when_power_off: bool = False,
    shutter_blade_thickness_mm: float = FX3_SHUTTER_BLADE_THICKNESS_MM,
    manual_swab_or_rocket_blower_active: bool = False,
    outdoor_direct_sun_lens_off: bool = False,
    sensor_cleaning_ultrasonic_shake: bool = False,
    vehicle_hard_mount_vibration_grms: float = 0.25,
    power_off_ibis_parking_verified: bool = True,
    request_persistent_emmc_writes: bool = False,
) -> SensorCurtainIbisTransportResult:
    """Verify Gate G27 (`IMX510` laser/solar burnout, `0.04 mm` shutter curtain & IBIS lock)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    # Validate numeric telemetry
    if not _is_finite_number(lens_f_number) or float(lens_f_number) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_SENSOR_CURTAIN_TELEMETRY_INVALID)
        errors.append(f"lens_f_number must be finite > 0.0, got {lens_f_number!r}.")
        eff_f_num = 2.8
    else:
        eff_f_num = float(lens_f_number)

    if not _is_finite_number(shutter_blade_thickness_mm) or float(shutter_blade_thickness_mm) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_SENSOR_CURTAIN_TELEMETRY_INVALID)
        errors.append(f"shutter_blade_thickness_mm must be finite > 0.0, got {shutter_blade_thickness_mm!r}.")
        eff_blade_mm = FX3_SHUTTER_BLADE_THICKNESS_MM
    else:
        eff_blade_mm = float(shutter_blade_thickness_mm)

    if not _is_finite_number(vehicle_hard_mount_vibration_grms) or float(vehicle_hard_mount_vibration_grms) < 0.0:
        _add_code(codes, STATUS_BLOCKED_SENSOR_CURTAIN_TELEMETRY_INVALID)
        errors.append(
            f"vehicle_hard_mount_vibration_grms must be finite >= 0.0, got {vehicle_hard_mount_vibration_grms!r}."
        )
        eff_grms = 0.0
    else:
        eff_grms = float(vehicle_hard_mount_vibration_grms)

    # a) Laser / LiDAR / Direct Solar Irradiance Burnout Guard
    eff_solar_direct = bool(uncapped_fast_lens_pointed_at_direct_sun) or (
        bool(direct_sun_in_fov)
        and bool(lens_uncapped)
        and (eff_f_num <= FAST_LENS_SOLAR_BURN_MAX_F_NUMBER)
        and (not bool(solar_rated_nd_filter_installed))
    )
    laser_hazard = bool(concert_show_laser_or_automotive_lidar_env) and (
        not bool(laser_rated_optical_filter_installed)
    )
    solar_hazard = eff_solar_direct and (not bool(solar_rated_nd_filter_installed))
    irradiance_safe = not (laser_hazard or solar_hazard)

    if not irradiance_safe:
        _add_code(codes, STATUS_BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD)
        reasons: List[str] = []
        if laser_hazard:
            reasons.append("concert/show laser or automotive LiDAR without laser-rated optical filter")
        if solar_hazard:
            reasons.append(f"uncapped fast lens (f/{eff_f_num:.1f}) aimed at direct sun without solar ND filter")
        errors.append(
            "BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD: FX3 has no FX6-style internal e-VND glass; "
            + "; ".join(reasons)
            + " risks permanent IMX510 microlens/CFA stripe burn."
        )

    # b) Anti-Dust 'Shutter When Power Off = On' Fragile 0.04 mm Curtain Guard
    curtain_hazard = bool(shutter_when_power_off) and (
        bool(manual_swab_or_rocket_blower_active) or bool(outdoor_direct_sun_lens_off)
    )
    curtain_safe = not curtain_hazard
    if not curtain_safe:
        _add_code(codes, STATUS_BLOCKED_FRAGILE_CURTAIN_AT_LENS_CHANGE)
        c_reasons: List[str] = []
        if manual_swab_or_rocket_blower_active:
            c_reasons.append("manual swab/rocket blower active against closed focal-plane curtain")
        if outdoor_direct_sun_lens_off:
            c_reasons.append("outdoor direct sunlight hitting closed black shutter blades during lens-off swap")
        errors.append(
            f"BLOCKED_FRAGILE_CURTAIN_AT_LENS_CHANGE: shutter_when_power_off=True exposes delicate "
            f"{eff_blade_mm:.2f} mm shutter blades ("
            + "; ".join(c_reasons)
            + "); disable Shutter When Power Off or move indoors/shade before cleaning or swapping lenses."
        )
    elif bool(shutter_when_power_off):
        warnings.append(
            f"shutter_when_power_off=True ({eff_blade_mm:.2f} mm blades closed); never insert blower tips "
            "or swabs while powered off and shield E-Mount throat from direct sunlight."
        )

    if bool(sensor_cleaning_ultrasonic_shake) and bool(shutter_when_power_off) and curtain_safe:
        warnings.append(
            "Ultrasonic IBIS sensor-cleaning shake requires powered-on open-shutter cleaning mode."
        )

    # c) Unpowered IBIS Floating-Stage Hard-Mount Transport Vibration Guard
    ibis_transport_safe = not (
        eff_grms > MAX_UNPOWERED_IBIS_VIBRATION_GRMS and (not bool(power_off_ibis_parking_verified))
    )
    if not ibis_transport_safe:
        _add_code(codes, STATUS_BLOCKED_UNPOWERED_IBIS_HARD_VIBRATION)
        errors.append(
            f"BLOCKED_UNPOWERED_IBIS_HARD_VIBRATION: vehicle_hard_mount_vibration={eff_grms:.2f} Grms > "
            f"{MAX_UNPOWERED_IBIS_VIBRATION_GRMS:.1f} Grms with power_off_ibis_parking_verified=False; "
            "unenergized IMX510 VCM coils slam floating sensor stage against mechanical stops."
        )
    elif eff_grms > MAX_UNPOWERED_IBIS_VIBRATION_GRMS:
        warnings.append(
            f"High vehicle vibration ({eff_grms:.2f} Grms > {MAX_UNPOWERED_IBIS_VIBRATION_GRMS:.1f} Grms) "
            "mitigated by verified IBIS transport lock / isolator."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return SensorCurtainIbisTransportResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        concert_show_laser_or_automotive_lidar_env=bool(concert_show_laser_or_automotive_lidar_env),
        laser_rated_optical_filter_installed=bool(laser_rated_optical_filter_installed),
        uncapped_fast_lens_pointed_at_direct_sun=eff_solar_direct,
        solar_rated_nd_filter_installed=bool(solar_rated_nd_filter_installed),
        irradiance_safe=irradiance_safe,
        shutter_when_power_off=bool(shutter_when_power_off),
        shutter_blade_thickness_mm=eff_blade_mm,
        manual_swab_or_rocket_blower_active=bool(manual_swab_or_rocket_blower_active),
        outdoor_direct_sun_lens_off=bool(outdoor_direct_sun_lens_off),
        sensor_cleaning_ultrasonic_shake=bool(sensor_cleaning_ultrasonic_shake),
        curtain_safe=curtain_safe,
        vehicle_hard_mount_vibration_grms=eff_grms,
        max_unpowered_ibis_vibration_grms=MAX_UNPOWERED_IBIS_VIBRATION_GRMS,
        power_off_ibis_parking_verified=bool(power_off_ibis_parking_verified),
        ibis_transport_safe=ibis_transport_safe,
        fx3_no_internal_evnd_glass=True,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G28 — Sub-Zero NP-FZ100 ESR Sag & High-Altitude Cooling Firewall
# ---------------------------------------------------------------------------


def verify_subzero_esr_and_altitude_firewall(
    *,
    battery_cell_temp_c: float = 20.0,
    battery_soc_pct: float = 85.0,
    peak_load_watts: float = NPFZ100_DEFAULT_PEAK_LOAD_WATTS,
    r_ref_25c_ohm: float = NPFZ100_REF_ESR_25C_OHM,
    v_oc_override_v: Optional[float] = None,
    insulated_usb_pd_backup: bool = False,
    usb_pd_charging_enabled: bool = False,
    altitude_m: float = 150.0,
    cooling_headroom_watts: float = FX3_SEA_LEVEL_COOLING_HEADROOM_WATTS,
    workload_thermal_watts: float = 5.5,
    request_persistent_emmc_writes: bool = False,
) -> SubzeroEsrAltitudeResult:
    """Verify Gate G28 (Arrhenius sub-zero NP-FZ100 ESR sag, dendrite plating & ISA >3,000m cooling)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    # Validate telemetry ranges
    telemetry_ok = True
    if not _is_finite_number(battery_cell_temp_c) or float(battery_cell_temp_c) < -40.0 or float(battery_cell_temp_c) > 85.0:
        _add_code(codes, STATUS_BLOCKED_SUBZERO_ALTITUDE_TELEMETRY_INVALID)
        errors.append(f"battery_cell_temp_c must be in [-40.0, 85.0], got {battery_cell_temp_c!r}.")
        telemetry_ok = False
        eff_temp_c = 20.0
    else:
        eff_temp_c = float(battery_cell_temp_c)

    if not _is_finite_number(battery_soc_pct) or float(battery_soc_pct) < 0.0 or float(battery_soc_pct) > 100.0:
        _add_code(codes, STATUS_BLOCKED_SUBZERO_ALTITUDE_TELEMETRY_INVALID)
        errors.append(f"battery_soc_pct must be in [0.0, 100.0], got {battery_soc_pct!r}.")
        telemetry_ok = False
        eff_soc = 85.0
    else:
        eff_soc = float(battery_soc_pct)

    if not _is_finite_number(peak_load_watts) or float(peak_load_watts) < 0.0:
        _add_code(codes, STATUS_BLOCKED_SUBZERO_ALTITUDE_TELEMETRY_INVALID)
        errors.append(f"peak_load_watts must be finite >= 0.0, got {peak_load_watts!r}.")
        telemetry_ok = False
        eff_peak_w = NPFZ100_DEFAULT_PEAK_LOAD_WATTS
    else:
        eff_peak_w = float(peak_load_watts)

    if not _is_finite_number(r_ref_25c_ohm) or float(r_ref_25c_ohm) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_SUBZERO_ALTITUDE_TELEMETRY_INVALID)
        errors.append(f"r_ref_25c_ohm must be finite > 0.0, got {r_ref_25c_ohm!r}.")
        telemetry_ok = False
        eff_r_ref = NPFZ100_REF_ESR_25C_OHM
    else:
        eff_r_ref = float(r_ref_25c_ohm)

    if v_oc_override_v is not None and (not _is_finite_number(v_oc_override_v) or float(v_oc_override_v) <= 0.0):
        _add_code(codes, STATUS_BLOCKED_SUBZERO_ALTITUDE_TELEMETRY_INVALID)
        errors.append(f"v_oc_override_v must be finite > 0.0, got {v_oc_override_v!r}.")
        telemetry_ok = False
        eff_voc_override = None
    else:
        eff_voc_override = float(v_oc_override_v) if v_oc_override_v is not None else None

    if not _is_finite_number(altitude_m) or float(altitude_m) < -500.0 or float(altitude_m) > 9000.0:
        _add_code(codes, STATUS_BLOCKED_SUBZERO_ALTITUDE_TELEMETRY_INVALID)
        errors.append(f"altitude_m must be in [-500.0, 9000.0], got {altitude_m!r}.")
        telemetry_ok = False
        eff_alt_m = 150.0
    else:
        eff_alt_m = float(altitude_m)

    if not _is_finite_number(cooling_headroom_watts) or float(cooling_headroom_watts) < 0.0:
        _add_code(codes, STATUS_BLOCKED_SUBZERO_ALTITUDE_TELEMETRY_INVALID)
        errors.append(f"cooling_headroom_watts must be finite >= 0.0, got {cooling_headroom_watts!r}.")
        telemetry_ok = False
        eff_headroom_w = FX3_SEA_LEVEL_COOLING_HEADROOM_WATTS
    else:
        eff_headroom_w = float(cooling_headroom_watts)

    if not _is_finite_number(workload_thermal_watts) or float(workload_thermal_watts) < 0.0:
        _add_code(codes, STATUS_BLOCKED_SUBZERO_ALTITUDE_TELEMETRY_INVALID)
        errors.append(f"workload_thermal_watts must be finite >= 0.0, got {workload_thermal_watts!r}.")
        telemetry_ok = False
        eff_workload_w = 5.5
    else:
        eff_workload_w = float(workload_thermal_watts)

    # Physics calculations (safe defaults already substituted if telemetry_ok was False)
    v_oc_v, r_int_ohm, v_term_min_v = predict_npfz100_terminal_voltage_v(
        eff_temp_c,
        soc_pct=eff_soc,
        peak_load_watts=eff_peak_w,
        r_ref_25c_ohm=eff_r_ref,
        v_oc_override_v=eff_voc_override,
    )
    esr_multiplier = r_int_ohm / eff_r_ref
    pred_current_a = (eff_peak_w / v_term_min_v) if v_term_min_v > 0.0 else float("inf")

    p_atm_kpa, air_density, mass_flow_ratio = compute_isa_atmosphere(eff_alt_m)
    derated_cooling_w = mass_flow_ratio * eff_headroom_w

    # a) Sub-zero Li-Ion ESR brownout risk
    subzero_esr_safe = True
    if telemetry_ok and eff_temp_c < 0.0 and v_term_min_v < NPFZ100_SAFE_VTERM_MIN_V and (not bool(insulated_usb_pd_backup)):
        subzero_esr_safe = False
        _add_code(codes, STATUS_BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK)
        errors.append(
            f"BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK: at {eff_temp_c:.1f}C and {eff_soc:.1f}% SoC, "
            f"Arrhenius R_int={r_int_ohm*1000.0:.1f} mOhm ({esr_multiplier:.2f}x) sags V_term_min to "
            f"{v_term_min_v:.3f} V < {NPFZ100_SAFE_VTERM_MIN_V:.2f} V ({NPFZ100_PMIC_UVLO_CUTOFF_V:.1f} V UVLO + margin) "
            f"under {eff_peak_w:.1f} W peak load without insulated USB-PD/heated V-Mount backup."
        )
    elif telemetry_ok and eff_temp_c < 0.0 and v_term_min_v < NPFZ100_SAFE_VTERM_MIN_V and bool(insulated_usb_pd_backup):
        warnings.append(
            f"Sub-zero NP-FZ100 V_term_min={v_term_min_v:.2f}V at {eff_temp_c:.1f}C mitigated by "
            "external insulated USB-PD / heated V-Mount backup."
        )

    # b) Sub-zero Li-Ion charging lithium dendrite plating guard
    subzero_charge_safe = True
    if telemetry_ok and bool(usb_pd_charging_enabled) and eff_temp_c <= LIION_SUBZERO_CHARGE_MIN_TEMP_C:
        subzero_charge_safe = False
        _add_code(codes, STATUS_BLOCKED_LIION_SUBZERO_CHARGING_PLATING)
        errors.append(
            f"BLOCKED_LIION_SUBZERO_CHARGING_PLATING: usb_pd_charging_enabled=True at cell temp "
            f"{eff_temp_c:.1f}C <= {LIION_SUBZERO_CHARGE_MIN_TEMP_C:.1f}C causes irreversible metallic "
            "lithium dendrite plating; warm battery above 0C before enabling USB-PD charging."
        )

    # c) High-altitude (> 3,000 m) barometric air-density convective cooling derating
    altitude_cooling_safe = True
    if telemetry_ok and eff_alt_m > HIGH_ALTITUDE_DERATING_THRESHOLD_M and derated_cooling_w < eff_workload_w:
        altitude_cooling_safe = False
        _add_code(codes, STATUS_BLOCKED_HIGH_ALTITUDE_CONVECTIVE_DERATING)
        errors.append(
            f"BLOCKED_HIGH_ALTITUDE_CONVECTIVE_DERATING: altitude={eff_alt_m:.0f} m "
            f"(P_atm={p_atm_kpa:.2f} kPa, rho={air_density:.4f} kg/m3, flow_ratio={mass_flow_ratio:.3f}) "
            f"derates Sigma fan convective capacity to {derated_cooling_w:.2f} W < workload {eff_workload_w:.2f} W."
        )
    elif telemetry_ok and eff_alt_m > HIGH_ALTITUDE_DERATING_THRESHOLD_M:
        warnings.append(
            f"High-altitude operation at {eff_alt_m:.0f} m (P_atm={p_atm_kpa:.1f} kPa, "
            f"air_density_ratio={mass_flow_ratio:.3f}): derated cooling {derated_cooling_w:.2f} W >= "
            f"{eff_workload_w:.2f} W workload."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return SubzeroEsrAltitudeResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        battery_cell_temp_c=round(eff_temp_c, 3),
        battery_soc_pct=round(eff_soc, 3),
        v_oc_v=round(v_oc_v, 4),
        r_ref_25c_ohm=round(eff_r_ref, 5),
        r_int_ohm=round(r_int_ohm, 5),
        esr_multiplier=round(esr_multiplier, 4),
        peak_load_watts=round(eff_peak_w, 3),
        predicted_load_current_a=round(pred_current_a, 4) if math.isfinite(pred_current_a) else 999.0,
        predicted_v_term_min_v=round(v_term_min_v, 4),
        pmic_uvlo_cutoff_v=NPFZ100_PMIC_UVLO_CUTOFF_V,
        safe_vterm_min_v=NPFZ100_SAFE_VTERM_MIN_V,
        insulated_usb_pd_backup=bool(insulated_usb_pd_backup),
        usb_pd_charging_enabled=bool(usb_pd_charging_enabled),
        subzero_esr_brownout_safe=subzero_esr_safe,
        subzero_charging_safe=subzero_charge_safe,
        altitude_m=round(eff_alt_m, 2),
        atmospheric_pressure_kpa=round(p_atm_kpa, 3),
        air_density_kg_m3=round(air_density, 5),
        fan_mass_flow_ratio=round(mass_flow_ratio, 5),
        cooling_headroom_watts=round(eff_headroom_w, 3),
        derated_cooling_capacity_watts=round(derated_cooling_w, 3),
        workload_thermal_watts=round(eff_workload_w, 3),
        altitude_convective_cooling_safe=altitude_cooling_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 5. Gate G27 & Gate G28 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g27_sensor_curtain_and_ibis_transport(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    sensor_curtain_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase97DonorAuditResult] = None,
) -> Tuple[GateVerdict, G27SensorCurtainIbisTransportResult]:
    """Evaluate Gate G27 (`imx510_laser_curtain_and_ibis_transport_safe`)."""
    audit = donor_audit or audit_phase97_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(sensor_curtain_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    sc_res = verify_sensor_curtain_and_ibis_transport_guard(**eff_kwargs)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in sc_res.violation_codes:
        _add_code(codes, c)
    errors.extend(sc_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(sc_res.warnings)

    passed = (
        audit.valid
        and sc_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = STATUS_VERIFIED_G27 if passed else (codes[0] if codes else STATUS_BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD)

    res = G27SensorCurtainIbisTransportResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        sensor_curtain_guard=sc_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G27_GATE_ID,
        gate_code=G27_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"IMX510 Irradiance, 0.04mm Shutter Curtain & IBIS Transport Lock ({sc_res.status}, "
            f"shutter_off_closed={sc_res.shutter_when_power_off}, grms={sc_res.vehicle_hard_mount_vibration_grms:.2f}, "
            f"ibis_park_ok={sc_res.power_off_ibis_parking_verified}, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "irradiance_safe": sc_res.irradiance_safe,
            "curtain_safe": sc_res.curtain_safe,
            "ibis_transport_safe": sc_res.ibis_transport_safe,
        },
    )
    return verdict, res


def evaluate_g28_subzero_esr_and_altitude(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    subzero_altitude_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase97DonorAuditResult] = None,
) -> Tuple[GateVerdict, G28SubzeroEsrAltitudeResult]:
    """Evaluate Gate G28 (`subzero_liion_esr_and_high_altitude_cooling_safe`)."""
    audit = donor_audit or audit_phase97_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(subzero_altitude_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    sa_res = verify_subzero_esr_and_altitude_firewall(**eff_kwargs)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in sa_res.violation_codes:
        _add_code(codes, c)
    errors.extend(sa_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(sa_res.warnings)

    passed = (
        audit.valid
        and sa_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = STATUS_VERIFIED_G28 if passed else (codes[0] if codes else STATUS_BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK)

    res = G28SubzeroEsrAltitudeResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        subzero_altitude_firewall=sa_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G28_GATE_ID,
        gate_code=G28_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Sub-Zero NP-FZ100 ESR & High-Altitude Cooling Firewall ({sa_res.status}, "
            f"T_cell={sa_res.battery_cell_temp_c:.1f}C, V_term_min={sa_res.predicted_v_term_min_v:.2f}V, "
            f"alt={sa_res.altitude_m:.0f}m, flow={sa_res.fan_mass_flow_ratio:.3f}, "
            f"cooling={sa_res.derated_cooling_capacity_watts:.2f}/{sa_res.workload_thermal_watts:.2f}W, "
            f"{audit.verification_mode}), persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "subzero_esr_brownout_safe": sa_res.subzero_esr_brownout_safe,
            "subzero_charging_safe": sa_res.subzero_charging_safe,
            "altitude_convective_cooling_safe": sa_res.altitude_convective_cooling_safe,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 6. Master 28-Gate Preflight Evaluator (`G01..G28`) & CLI
# ---------------------------------------------------------------------------


def evaluate_28gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G26 pass-throughs
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
    # G27 inputs (IMX510 Laser/Solar, Shutter Curtain & Unpowered IBIS Guard)
    sensor_curtain_kwargs: Optional[Mapping[str, Any]] = None,
    # G28 inputs (Sub-Zero NP-FZ100 ESR Sag & High-Altitude Cooling Firewall)
    subzero_altitude_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master28GateReport:
    """Evaluate all 28 Master Safety Gates (`G01..G28`) deterministically."""
    resolved_root = (DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m26_kwargs: Dict[str, Any] = {
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
    }
    if soc_start_ceiling_c is not None:
        m26_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m26_report: Master26GateReport = evaluate_26gate_preflight(resolved_root, **m26_kwargs)

    phase97_audit = audit_phase97_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
    )

    g27_verdict, g27_res = evaluate_g27_sensor_curtain_and_ibis_transport(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        sensor_curtain_kwargs=sensor_curtain_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase97_audit,
    )

    g28_verdict, g28_res = evaluate_g28_subzero_esr_and_altitude(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        subzero_altitude_kwargs=subzero_altitude_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase97_audit,
    )

    gates_27_to_28 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g27_verdict, g28_verdict)
    ]
    all_gates = tuple(list(m26_report.gates) + gates_27_to_28)

    g01_to_g12_verified = int(m26_report.summary["g01_to_g12_verified"])
    g13_to_g26_verified = (
        int(m26_report.summary["g13_to_g24_verified"])
        + int(m26_report.summary["g25_to_g26_verified"])
    )
    g27_to_g28_verified = sum(1 for v in (g27_verdict, g28_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g26_verified + g27_to_g28_verified

    g27_to_g28_all_passed = g27_to_g28_verified == 2
    g13_to_g28_all_passed = m26_report.g13_to_g26_all_passed and g27_to_g28_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m26_report.gates[:9])

    offline_25_verified = (
        g01_to_g09_ok
        and m26_report.offline_23_gates_verified
        and g27_to_g28_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_28_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g28_all_passed
        and (not request_persistent_emmc_writes)
    )

    real_tier0_verified = (g01_to_g12_verified == 12) and (not dry_run_simulated_backup)
    overall_ready_for_hardware_attach = (
        real_tier0_verified
        and g13_to_g28_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    h0_h1_allowed = (
        offline_25_verified
        and m26_report.h0_h1_trial_entry_allowed
        and g27_to_g28_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = list(m26_report.errors) + list(g27_verdict.errors) + list(g28_verdict.errors)
    warnings: List[str] = list(m26_report.warnings) + list(g27_verdict.warnings) + list(g28_verdict.warnings)

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m26_report.g13_to_g26_all_passed:
        overall_status = m26_report.status
    elif not g27_verdict.passed:
        overall_status = g27_verdict.status
    elif not g28_verdict.passed:
        overall_status = g28_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_28_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_28_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_28_verified:
        overall_status = "VERIFIED_ALL_28_GATES"
    else:
        overall_status = "VERIFIED_25_OF_28_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m26_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g27_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g28_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 28,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 28 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g26_verified": g13_to_g26_verified,
        "g27_to_g28_verified": g27_to_g28_verified,
        "g13_to_g28_all_passed": g13_to_g28_all_passed,
        "g27_to_g28_all_passed": g27_to_g28_all_passed,
        "offline_25_gates_verified": offline_25_verified,
        "all_28_gates_verified": all_28_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master28GateReport(
        schema=SENSOR_CURTAIN_SUBZERO_28GATE_SCHEMA,
        version=SENSOR_CURTAIN_SUBZERO_28GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_25_gates_verified=offline_25_verified,
        all_28_gates_verified=all_28_verified,
        g13_to_g28_all_passed=g13_to_g28_all_passed,
        g27_to_g28_all_passed=g27_to_g28_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_26_report=m26_report.to_dict(),
        g27_result=g27_res.to_dict(),
        g28_result=g28_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_28_master_safety_gates = evaluate_28gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sensor_curtain_subzero_and_28gate_guard",
        description="Phase 97 — IMX510 Sensor/Curtain/IBIS Guard, Sub-Zero ESR/Altitude Firewall & 28-Gate Preflight (G01..G28)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    parser.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G28 can be exercised offline",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_28gate_preflight(
        args.repo_root,
        force_clean_room=True if args.clean_room else None,
        dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/28 "
            f"g27_to_g28_all_passed={report.g27_to_g28_all_passed} "
            f"all_28_gates_verified={report.all_28_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = report.all_28_gates_verified if args.dry_run_simulated_backup else report.offline_25_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
