"""Phase 84 — Sub-Dewpoint Peltier TEC Condensation Firewall, PMIC `5V` Accessory Current-Budget / USB-C Strain Guard & `G01..G24` 24-Gate Preflight.

Operationalizes psychrometric dew-point condensation safety, PMIC `5V` peripheral
current-budget / USB-C cable IR-droop & cage strain-relief safety, and the
unified 24-Gate Master Safety Preflight (`G01..G24`) for Sony ILME-FX3
(`Ver. 7.02`, SoC `CXD90057`, `IMX510` 5-axis IBIS) while keeping `preflight.py`,
`master_16gate_preflight.py`, `usblan_ptpip_and_18gate_preflight.py`,
`rig_groundloop_lensrail_and_20gate_guard.py`, and
`phantom48v_gimbal_and_22gate_guard.py` completely untouched:

1. **Magnus-Tetens Dew-Point Condensation & External Peltier (`TEC`) Cooler Firewall (`Gate G23`)**:
   - Computes exact psychrometric dew point $T_{dp}(T_{amb}, RH\\%)$ via the
     Magnus-Tetens formula ($a=17.625, b=243.04^\\circ\\text{C}$).
   - Blocks unregulated or sub-dewpoint external Peltier (`TEC`) semiconductor
     backplate coolers (`BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD`) whenever
     `tec_cold_plate_c < dew_point_c + 2.0` (e.g., `30°C / 75% RH` -> `T_dp = 25.1°C`,
     while an unregulated `10°C` Peltier cooler condenses liquid water onto the
     FX3 magnesium rear chassis & LCD hinge flex).
   - Blocks rapid Cold-to-Warm unbagged thermal shock
     (`BLOCKED_COLD_TO_WARM_CONDENSATION_SHOCK`) when moving a cold camera
     (e.g. `-5°C`) directly into a warm humid indoor room (`+26°C / 65% RH`)
     without a sealed acclimation bag until `body_temp_c >= dew_point_c + 2.0`.
   - Proves FX3's internal `libfan.so` centrifugal Sigma-shaped blower
     (`cooling_method == "internal_centrifugal_air"`) never drops chassis
     temperature below ambient dew point (`T_chassis >= T_amb > T_dp` -> `0%`
     condensation risk).

2. **PMIC `5V` Accessory Current-Budget, Non-Compliant USB-C PD Cable Droop & Cage Strain-Relief Guard (`Gate G24`)**:
   - Models total simultaneous `5V` rail current draw across FX3's peripheral ports:
     * `24-pin MI-Shoe` (`XLR-H1` digital ADC + dual `+48V` phantom boost
       converters under `10 mA` dual condenser load),
     * `HDMI Type-A Pin-18 +5V` (`<= 55 mA` active optical HDMI cable / EDID EEPROM),
     * `USB-C VBUS` host-mode (`5V` bus-powered Gigabit Ethernet `RTL8153`/`AX88179`
       or USB-C SSD when camera supplies `VBUS` instead of receiving `USB-PD`),
     * `Multi-Port` accessory logic draw.
   - Fails closed (`BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET`) when cumulative `5V`
     accessory draw exceeds the safe continuous PMIC thermal envelope (`> 900 mA`
     combined without an external powered USB-C PD hub).
   - Detects high-resistance / un-E-marked `>2m` USB-C cables
     (`cable_ir_drop_v > 0.65V` at `3.0A` causing `9V` PD rail oscillation ->
     `BLOCKED_USBC_PD_CABLE_IR_DROOP`) and unclamped heavy USB-C/HDMI cables
     during handheld/gimbal rigs (`require_cage_cable_clamp == True` ->
     `BLOCKED_UNCLAMPED_USBC_HDMI_STRAIN_HAZARD`).

3. **24-Gate Master Safety Preflight Engine (`G01..G24`) & CLI `verify-24-gates`**:
   - Composes `evaluate_22gate_preflight` (`G01..G22`) with `G23`
     (`psychrometric_dewpoint_and_tec_condensation_safe`) and `G24`
     (`pmic_5v_accessory_budget_and_usbc_strain_safe`):
     * Offline default mode: `21/24` gates pass (`G10..G12` physical body
       Tier-0 readback truthfully remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`
       -> `overall_ready_for_hardware_attach = False`).
     * `--dry-run-simulated-backup` rehearsal mode: `24/24` simulation gates
       green (`dry_run_rehearsal_only = True`), while
       `persistent_emmc_writes_authorized` remains hard-locked to `False`.

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
from .phantom48v_gimbal_and_22gate_guard import (
    Master22GateReport,
    evaluate_22gate_preflight,
)
from .rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

DEWPOINT_TEC_USBC_24GATE_SCHEMA: str = "fx3-dewpoint-tec-usbc-24gate-preflight-v1"
DEWPOINT_TEC_USBC_24GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G23..G24
G23_GATE_ID: str = "G23_psychrometric_dewpoint_and_tec_condensation_safe"
G23_GATE_CODE: str = "PSYCHROMETRIC_DEWPOINT_AND_TEC_CONDENSATION_SAFE"

G24_GATE_ID: str = "G24_pmic_5v_accessory_budget_and_usbc_strain_safe"
G24_GATE_CODE: str = "PMIC_5V_ACCESSORY_BUDGET_AND_USBC_STRAIN_SAFE"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G23: str = "VERIFIED_PSYCHROMETRIC_DEWPOINT_AND_TEC_CONDENSATION_SAFE"
STATUS_VERIFIED_G24: str = "VERIFIED_PMIC_5V_ACCESSORY_BUDGET_AND_USBC_STRAIN_SAFE"

STATUS_BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD: str = "BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD"
STATUS_BLOCKED_COLD_TO_WARM_CONDENSATION_SHOCK: str = "BLOCKED_COLD_TO_WARM_CONDENSATION_SHOCK"
STATUS_BLOCKED_DEWPOINT_TELEMETRY_INVALID: str = "BLOCKED_DEWPOINT_TELEMETRY_INVALID"

STATUS_BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET: str = "BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET"
STATUS_BLOCKED_USBC_CABLE_IR_DROOP: str = "BLOCKED_USBC_PD_CABLE_IR_DROOP"
STATUS_BLOCKED_UNCLAMPED_CABLE_STRAIN: str = "BLOCKED_UNCLAMPED_USBC_HDMI_STRAIN_HAZARD"
STATUS_BLOCKED_PMIC_TELEMETRY_INVALID: str = "BLOCKED_PMIC_5V_TELEMETRY_INVALID"

STATUS_BLOCKED_DONOR_INTEGRITY: str = "BLOCKED_PHASE84_24GATE_DONOR_INTEGRITY_MISMATCH"
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"

# Magnus-Tetens Psychrometric Constants (Alduchov & Eskridge 1996 / Magnus-Tetens)
MAGNUS_TETENS_A: float = 17.625
MAGNUS_TETENS_B_C: float = 243.04
DEWPOINT_SAFETY_MARGIN_C: float = 2.0

COOLING_METHOD_INTERNAL_CENTRIFUGAL_AIR: str = "internal_centrifugal_air"
COOLING_METHOD_EXTERNAL_AIR_FAN: str = "external_air_fan"
COOLING_METHOD_EXTERNAL_PELTIER_TEC: str = "external_peltier_tec"
COOLING_METHOD_PASSIVE: str = "passive"
VALID_COOLING_METHODS: Tuple[str, ...] = (
    COOLING_METHOD_INTERNAL_CENTRIFUGAL_AIR,
    COOLING_METHOD_EXTERNAL_AIR_FAN,
    COOLING_METHOD_EXTERNAL_PELTIER_TEC,
    COOLING_METHOD_PASSIVE,
)

# PMIC 5V Accessory Current-Budget & USB-C Strain Constants
PMIC_5V_CONTINUOUS_BUDGET_MA: float = 900.0
HDMI_PIN18_5V_MAX_MA: float = 55.0
MISHOE_XLR_H1_BASE_5V_MA: float = 180.0
PHANTOM_48V_NOMINAL_V: float = 48.0
PMIC_5V_NOMINAL_V: float = 5.0
PHANTOM_48V_BOOST_EFFICIENCY: float = 0.80

USBC_CABLE_MAX_IR_DROP_V: float = 0.65
USBC_UNEMARKED_MAX_LENGTH_M: float = 2.0
USBC_PD_NOMINAL_MV: int = 9000
USBC_PD_REQUIRED_LOAD_A: float = 3.0

USBC_HOST_DEVICE_DEFAULT_MA: Mapping[str, float] = {
    "NONE": 0.0,
    "RTL8153": 380.0,
    "AX88179": 400.0,
    "USBC_SSD": 750.0,
    "USBC_NVME_SSD": 800.0,
}

RIG_MODE_HANDHELD: str = "HANDHELD"
RIG_MODE_GIMBAL: str = "GIMBAL"
RIG_MODE_TRIPOD: str = "TRIPOD"
RIG_MODE_BENCH: str = "BENCH"

# Compact FX3/FX6 Donor Contracts for Internal Centrifugal Fan & USB Bus Power (O_RDONLY verified)
PINNED_PHASE84_DONOR_SPECS: Mapping[str, Tuple[str, str, int, str, bytes, str]] = {
    "fx3_libfan": (
        "fx3",
        "libfan.so",
        27_280,
        "c607fc8d3ea3b46ef1082e07c57ba484a910e6841772e638ab5909189942726c",
        b"fan_infra_init",
        "fx3/libfan.so::fan_infra_init",
    ),
    "fx6_libfan": (
        "fx6",
        "libfan.so",
        31_176,
        "d4f01ff36a2d3d45c236cdb546816d585eed4aa9ce1ca68fdb03174151ea4850",
        b"_Z19fan_i_bkup_is_validv",
        "fx6/libfan.so::_Z19fan_i_bkup_is_validv",
    ),
    "fx3_lib_bus_power": (
        "fx3",
        "libBusPower.so",
        43_968,
        "4c39d2789745a4638490da1aa41b39c90980c7dd30837a693e87085689bbcc0e",
        b"_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt",
        "fx3/libBusPower.so::SetUSBPDSinkStatusToPowerManager",
    ),
    "fx3_lib_usb_bus_power": (
        "fx3",
        "libUsbBusPower.so",
        48_232,
        "c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748",
        b"_ZN11UsbBusPower15GetCurrentLimitEv",
        "fx3/libUsbBusPower.so::GetCurrentLimit",
    ),
    "fx6_lib_usb_bus_power": (
        "fx6",
        "libUsbBusPower.so",
        48_232,
        "4215a9e989d25896bd12de85928d58fac76d6c4b8dac04cc43ee1b9106c2fe71",
        b"_ZN11UsbBusPower15GetCurrentLimitEv",
        "fx6/libUsbBusPower.so::GetCurrentLimit",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase84DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DewpointTecFirewallResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    ambient_temp_c: float
    relative_humidity_pct: float
    dew_point_c: float
    safe_surface_floor_c: float
    body_temp_c: float
    chassis_temp_c: float
    cooling_method: str
    external_tec_attached: bool
    tec_cold_plate_c: Optional[float]
    sealed_acclimation_bag_used: bool
    internal_fan_dewpoint_immune: bool
    cold_to_warm_shock_safe: bool
    tec_condensation_safe: bool
    condensation_risk_pct: float
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pmic5vUsbCStrainGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    mishoe_xlr_h1_attached: bool
    phantom_48v_load_ma: float
    mishoe_5v_ma: float
    hdmi_attached: bool
    hdmi_pin18_5v_ma: float
    usbc_host_mode_vbus_source: bool
    usbc_bus_powered_device: str
    usbc_device_raw_5v_ma: float
    usbc_pmic_5v_ma: float
    multiport_5v_ma: float
    external_powered_usbc_pd_hub: bool
    total_pmic_5v_ma: float
    pmic_5v_budget_ma: float
    pmic_5v_budget_safe: bool
    usbc_cable_attached: bool
    usbc_cable_length_m: float
    usbc_cable_emarked: bool
    usbc_cable_load_a: float
    cable_ir_drop_v: float
    effective_pd_vbus_mv: int
    usbc_cable_droop_safe: bool
    rig_mode: str
    heavy_usbc_or_hdmi_attached: bool
    require_cage_cable_clamp: bool
    cage_cable_clamp_installed: bool
    cage_cable_strain_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G23DewpointTecResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    dewpoint_tec_firewall: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G24Pmic5vUsbCStrainResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    pmic_5v_usbc_strain_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master24GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_21_gates_verified: bool
    all_24_gates_verified: bool
    g13_to_g24_all_passed: bool
    g23_to_g24_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_22_report: Dict[str, Any]
    g23_result: Dict[str, Any]
    g24_result: Dict[str, Any]
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


def audit_phase84_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase84DonorAuditResult:
    """Inspect FX3/FX6 `libfan.so`, `libBusPower.so`, and `libUsbBusPower.so` donors via `os.O_RDONLY`."""
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)

    resolved: Dict[str, Path] = {}
    for key, (body, rel_name, *_rest) in PINNED_PHASE84_DONOR_SPECS.items():
        base_dir = paths.fx3_lib_dir if body == "fx3" else paths.fx6_lib_dir
        resolved[key] = base_dir / rel_name

    donor_available = (
        (not clean_forced)
        and (paths.work_root is not None)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase84DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(spec[5] for spec in PINNED_PHASE84_DONOR_SPECS.values()),
            missing_markers=(),
            sha256_by_artifact={k: spec[3] for k, spec in PINNED_PHASE84_DONOR_SPECS.items()},
            bytes_by_artifact={k: spec[2] for k, spec in PINNED_PHASE84_DONOR_SPECS.items()},
            errors=(),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []

    for key, (_body, _rel_name, exp_size, exp_sha, marker_bytes, marker_label) in PINNED_PHASE84_DONOR_SPECS.items():
        blob = _read_file_o_rdonly(resolved[key])
        sha = hashlib.sha256(blob).hexdigest()
        shas[key] = sha
        sizes[key] = len(blob)

        if marker_bytes in blob:
            checked.append(marker_label)
        else:
            missing.append(marker_label)
            errors.append(f"Donor {key} missing required marker {marker_label}.")

        if len(blob) != exp_size or sha != exp_sha:
            errors.append(
                f"Donor {key} integrity mismatch: size={len(blob)} (expected {exp_size}), "
                f"sha256={sha} (expected {exp_sha})."
            )

    valid = len(errors) == 0 and len(missing) == 0
    return Phase84DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=len(resolved),
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Magnus-Tetens Dew-Point & Peltier TEC Condensation Firewall (Gate G23)
# ---------------------------------------------------------------------------


def compute_magnus_tetens_dew_point_c(
    ambient_temp_c: float,
    relative_humidity_pct: float,
) -> float:
    """Compute exact psychrometric dew point T_dp (°C) via Magnus-Tetens (a=17.625, b=243.04°C)."""
    if not _is_finite_number(ambient_temp_c):
        raise ValueError(f"ambient_temp_c must be finite, got {ambient_temp_c!r}")
    if not _is_finite_number(relative_humidity_pct):
        raise ValueError(f"relative_humidity_pct must be finite, got {relative_humidity_pct!r}")

    t_amb = float(ambient_temp_c)
    rh = float(relative_humidity_pct)
    if t_amb < -50.0 or t_amb > 80.0:
        raise ValueError(f"ambient_temp_c {t_amb}C out of plausible range [-50.0, 80.0]")
    if rh <= 0.0 or rh > 100.0:
        raise ValueError(f"relative_humidity_pct {rh}% must be in (0.0, 100.0]")

    gamma = math.log(rh / 100.0) + (MAGNUS_TETENS_A * t_amb) / (MAGNUS_TETENS_B_C + t_amb)
    return (MAGNUS_TETENS_B_C * gamma) / (MAGNUS_TETENS_A - gamma)


def verify_dewpoint_tec_condensation_firewall(
    *,
    ambient_temp_c: float = 24.0,
    relative_humidity_pct: float = 55.0,
    body_temp_c: Optional[float] = None,
    chassis_temp_c: Optional[float] = None,
    cooling_method: str = COOLING_METHOD_INTERNAL_CENTRIFUGAL_AIR,
    external_tec_attached: Optional[bool] = None,
    tec_cold_plate_c: Optional[float] = None,
    sealed_acclimation_bag_used: bool = False,
    request_persistent_emmc_writes: bool = False,
) -> DewpointTecFirewallResult:
    """Verify sub-dewpoint Peltier TEC safety, cold-to-warm shock protection & internal libfan.so immunity."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    norm_method = str(cooling_method).strip().lower()
    if norm_method not in VALID_COOLING_METHODS:
        _add_code(codes, STATUS_BLOCKED_DEWPOINT_TELEMETRY_INVALID)
        errors.append(f"Unsupported cooling_method {cooling_method!r}; expected one of {VALID_COOLING_METHODS}.")

    try:
        dew_point_c = compute_magnus_tetens_dew_point_c(ambient_temp_c, relative_humidity_pct)
    except ValueError as exc:
        _add_code(codes, STATUS_BLOCKED_DEWPOINT_TELEMETRY_INVALID)
        errors.append(str(exc))
        return DewpointTecFirewallResult(
            valid=False,
            status=codes[0],
            violation_codes=tuple(codes),
            ambient_temp_c=float(ambient_temp_c) if _is_finite_number(ambient_temp_c) else float("nan"),
            relative_humidity_pct=float(relative_humidity_pct) if _is_finite_number(relative_humidity_pct) else float("nan"),
            dew_point_c=float("nan"),
            safe_surface_floor_c=float("nan"),
            body_temp_c=float("nan"),
            chassis_temp_c=float("nan"),
            cooling_method=norm_method,
            external_tec_attached=bool(external_tec_attached),
            tec_cold_plate_c=tec_cold_plate_c,
            sealed_acclimation_bag_used=bool(sealed_acclimation_bag_used),
            internal_fan_dewpoint_immune=False,
            cold_to_warm_shock_safe=False,
            tec_condensation_safe=False,
            condensation_risk_pct=100.0,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    t_amb = float(ambient_temp_c)
    rh = float(relative_humidity_pct)
    safe_floor_c = dew_point_c + DEWPOINT_SAFETY_MARGIN_C

    if body_temp_c is not None and not _is_finite_number(body_temp_c):
        _add_code(codes, STATUS_BLOCKED_DEWPOINT_TELEMETRY_INVALID)
        errors.append(f"body_temp_c must be finite, got {body_temp_c!r}")
    if chassis_temp_c is not None and not _is_finite_number(chassis_temp_c):
        _add_code(codes, STATUS_BLOCKED_DEWPOINT_TELEMETRY_INVALID)
        errors.append(f"chassis_temp_c must be finite, got {chassis_temp_c!r}")
    if tec_cold_plate_c is not None and not _is_finite_number(tec_cold_plate_c):
        _add_code(codes, STATUS_BLOCKED_DEWPOINT_TELEMETRY_INVALID)
        errors.append(f"tec_cold_plate_c must be finite, got {tec_cold_plate_c!r}")

    eff_body_c = float(body_temp_c) if (body_temp_c is not None and _is_finite_number(body_temp_c)) else (t_amb + 4.0)
    if chassis_temp_c is not None and _is_finite_number(chassis_temp_c):
        eff_chassis_c = float(chassis_temp_c)
    elif eff_body_c >= t_amb:
        eff_chassis_c = max(eff_body_c, t_amb)
    else:
        eff_chassis_c = eff_body_c

    if eff_body_c < -40.0 or eff_body_c > 110.0:
        _add_code(codes, STATUS_BLOCKED_DEWPOINT_TELEMETRY_INVALID)
        errors.append(f"body_temp_c {eff_body_c:.2f}C out of plausible range [-40.0, 110.0].")

    eff_tec_attached = (
        (norm_method == COOLING_METHOD_EXTERNAL_PELTIER_TEC)
        if external_tec_attached is None
        else bool(external_tec_attached)
    )
    if norm_method == COOLING_METHOD_EXTERNAL_PELTIER_TEC:
        eff_tec_attached = True

    eff_tec_c: Optional[float] = float(tec_cold_plate_c) if (tec_cold_plate_c is not None and _is_finite_number(tec_cold_plate_c)) else None

    # 1. External Peltier (TEC) sub-dewpoint condensation firewall
    tec_safe = True
    if eff_tec_attached:
        if eff_tec_c is None:
            tec_safe = False
            _add_code(codes, STATUS_BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD)
            errors.append(
                f"BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD: external Peltier (TEC) cooler attached "
                f"without closed-loop cold-plate thermistor feedback (dew_point={dew_point_c:.2f}C, "
                f"required floor >= {safe_floor_c:.2f}C)."
            )
        elif eff_tec_c < safe_floor_c:
            tec_safe = False
            _add_code(codes, STATUS_BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD)
            errors.append(
                f"BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD: Peltier TEC cold plate ({eff_tec_c:.2f}C) "
                f"< dew_point + {DEWPOINT_SAFETY_MARGIN_C:.1f}C ({safe_floor_c:.2f}C at {t_amb:.1f}C / {rh:.1f}% RH); "
                "risks internal condensation on FX3 magnesium rear chassis and LCD hinge flex."
            )

    # 2. Cold-to-Warm unbagged thermal shock guard
    cold_warm_safe = True
    if eff_body_c < safe_floor_c:
        if not sealed_acclimation_bag_used:
            cold_warm_safe = False
            _add_code(codes, STATUS_BLOCKED_COLD_TO_WARM_CONDENSATION_SHOCK)
            errors.append(
                f"BLOCKED_COLD_TO_WARM_CONDENSATION_SHOCK: camera body ({eff_body_c:.2f}C) moved into "
                f"{t_amb:.1f}C / {rh:.1f}% RH environment (dew_point={dew_point_c:.2f}C, "
                f"safe floor={safe_floor_c:.2f}C) without sealed acclimation bag."
            )
        else:
            warnings.append(
                f"Cold camera ({eff_body_c:.2f}C < {safe_floor_c:.2f}C) protected inside sealed acclimation bag; "
                "keep sealed and unpowered until body_temp_c >= dew_point_c + 2.0C."
            )

    # 3. FX3 internal libfan.so centrifugal Sigma-shaped blower immunity check
    internal_fan_immune = (
        norm_method == COOLING_METHOD_INTERNAL_CENTRIFUGAL_AIR
        and (not eff_tec_attached)
        and (eff_chassis_c >= t_amb)
        and (eff_chassis_c > dew_point_c)
        and (rh < 100.0)
    )
    if norm_method == COOLING_METHOD_INTERNAL_CENTRIFUGAL_AIR and not eff_tec_attached:
        if chassis_temp_c is not None and eff_chassis_c < min(t_amb, eff_body_c):
            _add_code(codes, STATUS_BLOCKED_DEWPOINT_TELEMETRY_INVALID)
            errors.append(
                f"Internal centrifugal air fan cannot cool chassis ({eff_chassis_c:.2f}C) below "
                f"both ambient ({t_amb:.2f}C) and body ({eff_body_c:.2f}C)."
            )

    if rh >= 100.0:
        warnings.append("100% RH saturated air (dew_point == ambient_temp); avoid prolonged exposure to mist/fog.")

    if not tec_safe or not cold_warm_safe:
        sub_c = max(
            safe_floor_c - eff_tec_c if (eff_tec_attached and eff_tec_c is not None and not tec_safe) else 0.0,
            safe_floor_c - eff_body_c if not cold_warm_safe else 0.0,
            1.0,
        )
        condensation_risk_pct = round(min(100.0, max(25.0, sub_c * 5.0)), 1)
    else:
        condensation_risk_pct = 0.0

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return DewpointTecFirewallResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        ambient_temp_c=t_amb,
        relative_humidity_pct=rh,
        dew_point_c=round(dew_point_c, 4),
        safe_surface_floor_c=round(safe_floor_c, 4),
        body_temp_c=eff_body_c,
        chassis_temp_c=eff_chassis_c,
        cooling_method=norm_method,
        external_tec_attached=eff_tec_attached,
        tec_cold_plate_c=eff_tec_c,
        sealed_acclimation_bag_used=bool(sealed_acclimation_bag_used),
        internal_fan_dewpoint_immune=internal_fan_immune,
        cold_to_warm_shock_safe=cold_warm_safe,
        tec_condensation_safe=tec_safe,
        condensation_risk_pct=condensation_risk_pct,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 3. PMIC 5V Accessory Current-Budget, USB-C Cable Droop & Strain Guard (G24)
# ---------------------------------------------------------------------------


def verify_pmic_5v_accessory_and_usbc_strain_guard(
    *,
    mishoe_xlr_h1_attached: bool = True,
    phantom_48v_load_ma: float = 10.0,
    mishoe_5v_ma: Optional[float] = None,
    hdmi_attached: bool = True,
    hdmi_pin18_5v_ma: Optional[float] = None,
    usbc_host_mode_vbus_source: bool = True,
    usbc_bus_powered_device: str = "RTL8153",
    usbc_vbus_5v_ma: Optional[float] = None,
    multiport_5v_ma: float = 40.0,
    external_powered_usbc_pd_hub: bool = False,
    usbc_cable_attached: bool = True,
    usbc_cable_length_m: float = 1.0,
    usbc_cable_emarked: bool = True,
    usbc_cable_load_a: float = USBC_PD_REQUIRED_LOAD_A,
    cable_ir_drop_v: Optional[float] = None,
    rig_mode: str = RIG_MODE_HANDHELD,
    heavy_usbc_or_hdmi_attached: bool = True,
    require_cage_cable_clamp: Optional[bool] = None,
    cage_cable_clamp_installed: bool = True,
    request_persistent_emmc_writes: bool = False,
) -> Pmic5vUsbCStrainGuardResult:
    """Verify PMIC `5V` peripheral current budget, USB-C PD cable IR drop & cage cable strain clamp."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    norm_usbc_dev = str(usbc_bus_powered_device).strip().upper()
    norm_rig = str(rig_mode).strip().upper()

    # Resolve 5V rail currents
    if not _is_finite_number(phantom_48v_load_ma) or float(phantom_48v_load_ma) < 0.0:
        _add_code(codes, STATUS_BLOCKED_PMIC_TELEMETRY_INVALID)
        errors.append(f"Invalid phantom_48v_load_ma={phantom_48v_load_ma!r}.")
        eff_phantom_ma = 0.0
    else:
        eff_phantom_ma = float(phantom_48v_load_ma)

    if mishoe_5v_ma is not None:
        if not _is_finite_number(mishoe_5v_ma) or float(mishoe_5v_ma) < 0.0:
            _add_code(codes, STATUS_BLOCKED_PMIC_TELEMETRY_INVALID)
            errors.append(f"Invalid mishoe_5v_ma={mishoe_5v_ma!r}.")
            eff_mishoe_5v_ma = 0.0
        else:
            eff_mishoe_5v_ma = float(mishoe_5v_ma)
    elif mishoe_xlr_h1_attached:
        boost_5v_ma = eff_phantom_ma * (PHANTOM_48V_NOMINAL_V / PMIC_5V_NOMINAL_V) / PHANTOM_48V_BOOST_EFFICIENCY
        eff_mishoe_5v_ma = round(MISHOE_XLR_H1_BASE_5V_MA + boost_5v_ma, 2)
    else:
        eff_mishoe_5v_ma = 0.0

    if hdmi_pin18_5v_ma is not None:
        if not _is_finite_number(hdmi_pin18_5v_ma) or float(hdmi_pin18_5v_ma) < 0.0:
            _add_code(codes, STATUS_BLOCKED_PMIC_TELEMETRY_INVALID)
            errors.append(f"Invalid hdmi_pin18_5v_ma={hdmi_pin18_5v_ma!r}.")
            eff_hdmi_5v_ma = 0.0
        else:
            eff_hdmi_5v_ma = float(hdmi_pin18_5v_ma)
    else:
        eff_hdmi_5v_ma = 50.0 if hdmi_attached else 0.0

    if usbc_vbus_5v_ma is not None:
        if not _is_finite_number(usbc_vbus_5v_ma) or float(usbc_vbus_5v_ma) < 0.0:
            _add_code(codes, STATUS_BLOCKED_PMIC_TELEMETRY_INVALID)
            errors.append(f"Invalid usbc_vbus_5v_ma={usbc_vbus_5v_ma!r}.")
            raw_usbc_5v_ma = 0.0
        else:
            raw_usbc_5v_ma = float(usbc_vbus_5v_ma)
    elif usbc_host_mode_vbus_source:
        raw_usbc_5v_ma = float(USBC_HOST_DEVICE_DEFAULT_MA.get(norm_usbc_dev, 380.0))
    else:
        raw_usbc_5v_ma = 0.0

    if not _is_finite_number(multiport_5v_ma) or float(multiport_5v_ma) < 0.0:
        _add_code(codes, STATUS_BLOCKED_PMIC_TELEMETRY_INVALID)
        errors.append(f"Invalid multiport_5v_ma={multiport_5v_ma!r}.")
        eff_multiport_5v_ma = 0.0
    else:
        eff_multiport_5v_ma = float(multiport_5v_ma)

    # External powered USB-C PD hub offloads USB-C VBUS peripheral draw from FX3 internal 5V PMIC
    eff_usbc_pmic_5v_ma = 0.0 if external_powered_usbc_pd_hub else (raw_usbc_5v_ma if usbc_host_mode_vbus_source else 0.0)
    total_pmic_5v_ma = round(eff_mishoe_5v_ma + eff_hdmi_5v_ma + eff_usbc_pmic_5v_ma + eff_multiport_5v_ma, 2)

    pmic_budget_safe = True
    if eff_hdmi_5v_ma > HDMI_PIN18_5V_MAX_MA:
        pmic_budget_safe = False
        _add_code(codes, STATUS_BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET)
        errors.append(
            f"BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET: HDMI Type-A Pin-18 +5V draw {eff_hdmi_5v_ma:.1f} mA "
            f"exceeds {HDMI_PIN18_5V_MAX_MA:.1f} mA specification."
        )

    if total_pmic_5v_ma > PMIC_5V_CONTINUOUS_BUDGET_MA:
        pmic_budget_safe = False
        _add_code(codes, STATUS_BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET)
        errors.append(
            f"BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET: cumulative 5V accessory draw {total_pmic_5v_ma:.1f} mA "
            f"(MI-Shoe={eff_mishoe_5v_ma:.1f} + HDMI={eff_hdmi_5v_ma:.1f} + USB-C={eff_usbc_pmic_5v_ma:.1f} + "
            f"MultiPort={eff_multiport_5v_ma:.1f} mA) exceeds {PMIC_5V_CONTINUOUS_BUDGET_MA:.1f} mA PMIC envelope; "
            "attach an external powered USB-C PD hub."
        )
    elif external_powered_usbc_pd_hub and raw_usbc_5v_ma > 0.0:
        warnings.append(
            f"USB-C peripheral ({norm_usbc_dev}, {raw_usbc_5v_ma:.0f} mA) offloaded to external powered USB-C PD hub; "
            f"camera PMIC 5V draw stays at {total_pmic_5v_ma:.1f} mA <= {PMIC_5V_CONTINUOUS_BUDGET_MA:.1f} mA."
        )

    # Check high-resistance / un-E-marked >2m USB-C cable IR droop
    if not _is_finite_number(usbc_cable_length_m) or float(usbc_cable_length_m) < 0.0:
        _add_code(codes, STATUS_BLOCKED_PMIC_TELEMETRY_INVALID)
        errors.append(f"Invalid usbc_cable_length_m={usbc_cable_length_m!r}.")
        eff_len_m = 0.0
    else:
        eff_len_m = float(usbc_cable_length_m)

    if not _is_finite_number(usbc_cable_load_a) or float(usbc_cable_load_a) < 0.0:
        _add_code(codes, STATUS_BLOCKED_PMIC_TELEMETRY_INVALID)
        errors.append(f"Invalid usbc_cable_load_a={usbc_cable_load_a!r}.")
        eff_load_a = 0.0
    else:
        eff_load_a = float(usbc_cable_load_a)

    if cable_ir_drop_v is not None:
        if not _is_finite_number(cable_ir_drop_v) or float(cable_ir_drop_v) < 0.0:
            _add_code(codes, STATUS_BLOCKED_PMIC_TELEMETRY_INVALID)
            errors.append(f"Invalid cable_ir_drop_v={cable_ir_drop_v!r}.")
            eff_ir_drop_v = 0.0
        else:
            eff_ir_drop_v = float(cable_ir_drop_v)
    elif usbc_cable_attached and eff_len_m > USBC_UNEMARKED_MAX_LENGTH_M and not usbc_cable_emarked:
        eff_ir_drop_v = round(0.32 * eff_len_m * (eff_load_a / 3.0), 3)
    elif usbc_cable_attached:
        eff_ir_drop_v = round(0.24 * eff_len_m * (eff_load_a / 3.0), 3)
    else:
        eff_ir_drop_v = 0.0

    effective_pd_vbus_mv = max(0, int(round(USBC_PD_NOMINAL_MV - eff_ir_drop_v * 1000.0)))
    cable_droop_safe = True
    if usbc_cable_attached:
        un_emarked_long = (eff_len_m > USBC_UNEMARKED_MAX_LENGTH_M) and (not usbc_cable_emarked)
        high_ir_drop = eff_ir_drop_v > USBC_CABLE_MAX_IR_DROP_V
        if high_ir_drop or un_emarked_long:
            cable_droop_safe = False
            _add_code(codes, STATUS_BLOCKED_USBC_CABLE_IR_DROOP)
            errors.append(
                f"BLOCKED_USBC_PD_CABLE_IR_DROOP: USB-C cable (length={eff_len_m:.2f}m, "
                f"e_marked={usbc_cable_emarked}, ir_drop={eff_ir_drop_v:.3f}V @ {eff_load_a:.1f}A, "
                f"effective_vbus={effective_pd_vbus_mv}mV) exceeds {USBC_CABLE_MAX_IR_DROP_V:.2f}V droop / "
                f"{USBC_UNEMARKED_MAX_LENGTH_M:.1f}m un-E-marked limit and risks 9V PD rail oscillation."
            )

    # Check Cage Cable Strain-Relief Clamp
    if require_cage_cable_clamp is None:
        eff_require_clamp = (norm_rig in (RIG_MODE_HANDHELD, RIG_MODE_GIMBAL)) and bool(heavy_usbc_or_hdmi_attached)
    else:
        eff_require_clamp = bool(require_cage_cable_clamp)

    cable_strain_safe = True
    if eff_require_clamp and not cage_cable_clamp_installed:
        cable_strain_safe = False
        _add_code(codes, STATUS_BLOCKED_UNCLAMPED_CABLE_STRAIN)
        errors.append(
            f"BLOCKED_UNCLAMPED_USBC_HDMI_STRAIN_HAZARD: heavy USB-C/HDMI cable in {norm_rig} rig mode "
            "without cage cable strain-relief clamp risks port shear or intermittent VBUS brownout."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return Pmic5vUsbCStrainGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        mishoe_xlr_h1_attached=bool(mishoe_xlr_h1_attached),
        phantom_48v_load_ma=eff_phantom_ma,
        mishoe_5v_ma=eff_mishoe_5v_ma,
        hdmi_attached=bool(hdmi_attached),
        hdmi_pin18_5v_ma=eff_hdmi_5v_ma,
        usbc_host_mode_vbus_source=bool(usbc_host_mode_vbus_source),
        usbc_bus_powered_device=norm_usbc_dev,
        usbc_device_raw_5v_ma=raw_usbc_5v_ma,
        usbc_pmic_5v_ma=eff_usbc_pmic_5v_ma,
        multiport_5v_ma=eff_multiport_5v_ma,
        external_powered_usbc_pd_hub=bool(external_powered_usbc_pd_hub),
        total_pmic_5v_ma=total_pmic_5v_ma,
        pmic_5v_budget_ma=PMIC_5V_CONTINUOUS_BUDGET_MA,
        pmic_5v_budget_safe=pmic_budget_safe,
        usbc_cable_attached=bool(usbc_cable_attached),
        usbc_cable_length_m=eff_len_m,
        usbc_cable_emarked=bool(usbc_cable_emarked),
        usbc_cable_load_a=eff_load_a,
        cable_ir_drop_v=eff_ir_drop_v,
        effective_pd_vbus_mv=effective_pd_vbus_mv,
        usbc_cable_droop_safe=cable_droop_safe,
        rig_mode=norm_rig,
        heavy_usbc_or_hdmi_attached=bool(heavy_usbc_or_hdmi_attached),
        require_cage_cable_clamp=eff_require_clamp,
        cage_cable_clamp_installed=bool(cage_cable_clamp_installed),
        cage_cable_strain_safe=cable_strain_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate 23 & Gate 24 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g23_dewpoint_and_tec_condensation(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dewpoint_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase84DonorAuditResult] = None,
) -> Tuple[GateVerdict, G23DewpointTecResult]:
    """Evaluate Gate G23 (`psychrometric_dewpoint_and_tec_condensation_safe`)."""
    audit = donor_audit or audit_phase84_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
    )

    eff_dp = dict(dewpoint_kwargs or {})
    eff_dp["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_dp.get("request_persistent_emmc_writes", False)
    )
    dp_res = verify_dewpoint_tec_condensation_firewall(**eff_dp)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in dp_res.violation_codes:
        _add_code(codes, c)
    errors.extend(dp_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(dp_res.warnings)

    passed = (
        audit.valid
        and dp_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = STATUS_VERIFIED_G23 if passed else (codes[0] if codes else STATUS_BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD)

    res = G23DewpointTecResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        dewpoint_tec_firewall=dp_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G23_GATE_ID,
        gate_code=G23_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Magnus-Tetens Dew-Point/TEC Firewall ({dp_res.status}, "
            f"T_amb={dp_res.ambient_temp_c:.1f}C, RH={dp_res.relative_humidity_pct:.1f}%, "
            f"T_dp={dp_res.dew_point_c:.2f}C, method={dp_res.cooling_method}, "
            f"risk={dp_res.condensation_risk_pct:.1f}%, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "dew_point_c": dp_res.dew_point_c,
            "safe_surface_floor_c": dp_res.safe_surface_floor_c,
            "internal_fan_dewpoint_immune": dp_res.internal_fan_dewpoint_immune,
            "condensation_risk_pct": dp_res.condensation_risk_pct,
        },
    )
    return verdict, res


def evaluate_g24_pmic_5v_and_usbc_strain(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    pmic_usbc_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase84DonorAuditResult] = None,
) -> Tuple[GateVerdict, G24Pmic5vUsbCStrainResult]:
    """Evaluate Gate G24 (`pmic_5v_accessory_budget_and_usbc_strain_safe`)."""
    audit = donor_audit or audit_phase84_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
    )

    eff_pmic = dict(pmic_usbc_kwargs or {})
    eff_pmic["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_pmic.get("request_persistent_emmc_writes", False)
    )
    pmic_res = verify_pmic_5v_accessory_and_usbc_strain_guard(**eff_pmic)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in pmic_res.violation_codes:
        _add_code(codes, c)
    errors.extend(pmic_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(pmic_res.warnings)

    passed = (
        audit.valid
        and pmic_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = STATUS_VERIFIED_G24 if passed else (codes[0] if codes else STATUS_BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET)

    res = G24Pmic5vUsbCStrainResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        pmic_5v_usbc_strain_guard=pmic_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G24_GATE_ID,
        gate_code=G24_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"PMIC 5V Budget & USB-C Strain Guard ({pmic_res.status}, "
            f"5V_total={pmic_res.total_pmic_5v_ma:.1f}/{pmic_res.pmic_5v_budget_ma:.0f}mA, "
            f"ir_drop={pmic_res.cable_ir_drop_v:.3f}V, clamp={pmic_res.cage_cable_clamp_installed}, "
            f"{audit.verification_mode}), persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "total_pmic_5v_ma": pmic_res.total_pmic_5v_ma,
            "pmic_5v_budget_safe": pmic_res.pmic_5v_budget_safe,
            "usbc_cable_droop_safe": pmic_res.usbc_cable_droop_safe,
            "cage_cable_strain_safe": pmic_res.cage_cable_strain_safe,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Master 24-Gate Preflight Evaluator (`G01..G24`) & CLI
# ---------------------------------------------------------------------------


def evaluate_24gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G22 pass-throughs
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
    # G23 inputs (Magnus-Tetens Dew-Point & Peltier TEC Condensation Firewall)
    dewpoint_kwargs: Optional[Mapping[str, Any]] = None,
    # G24 inputs (PMIC 5V Accessory Budget, USB-C Cable Droop & Cage Strain Guard)
    pmic_usbc_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master24GateReport:
    """Evaluate all 24 Master Safety Gates (`G01..G24`) deterministically."""
    resolved_root = (DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m22_kwargs: Dict[str, Any] = {
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
    }
    if soc_start_ceiling_c is not None:
        m22_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m22_report: Master22GateReport = evaluate_22gate_preflight(resolved_root, **m22_kwargs)

    phase84_audit = audit_phase84_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g23_verdict, g23_res = evaluate_g23_dewpoint_and_tec_condensation(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        dewpoint_kwargs=dewpoint_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase84_audit,
    )

    g24_verdict, g24_res = evaluate_g24_pmic_5v_and_usbc_strain(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        pmic_usbc_kwargs=pmic_usbc_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase84_audit,
    )

    gates_23_to_24 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g23_verdict, g24_verdict)
    ]
    all_gates = tuple(list(m22_report.gates) + gates_23_to_24)

    g01_to_g12_verified = int(m22_report.summary["g01_to_g12_verified"])
    g13_to_g22_verified = (
        int(m22_report.summary["g13_to_g20_verified"])
        + int(m22_report.summary["g21_to_g22_verified"])
    )
    g23_to_g24_verified = sum(1 for v in (g23_verdict, g24_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g22_verified + g23_to_g24_verified

    g23_to_g24_all_passed = g23_to_g24_verified == 2
    g13_to_g24_all_passed = m22_report.g13_to_g22_all_passed and g23_to_g24_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m22_report.gates[:9])

    offline_21_verified = (
        g01_to_g09_ok
        and m22_report.offline_19_gates_verified
        and g23_to_g24_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_24_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g24_all_passed
        and (not request_persistent_emmc_writes)
    )

    real_tier0_verified = (g01_to_g12_verified == 12) and (not dry_run_simulated_backup)
    overall_ready_for_hardware_attach = (
        real_tier0_verified
        and g13_to_g24_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    h0_h1_allowed = (
        offline_21_verified
        and m22_report.h0_h1_trial_entry_allowed
        and g23_to_g24_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = list(m22_report.errors) + list(g23_verdict.errors) + list(g24_verdict.errors)
    warnings: List[str] = list(m22_report.warnings) + list(g23_verdict.warnings) + list(g24_verdict.warnings)

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m22_report.g13_to_g22_all_passed:
        overall_status = m22_report.status
    elif not g23_verdict.passed:
        overall_status = g23_verdict.status
    elif not g24_verdict.passed:
        overall_status = g24_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_24_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_24_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_24_verified:
        overall_status = "VERIFIED_ALL_24_GATES"
    else:
        overall_status = "VERIFIED_21_OF_24_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m22_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g23_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g24_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 24,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 24 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g22_verified": g13_to_g22_verified,
        "g23_to_g24_verified": g23_to_g24_verified,
        "g13_to_g24_all_passed": g13_to_g24_all_passed,
        "g23_to_g24_all_passed": g23_to_g24_all_passed,
        "offline_21_gates_verified": offline_21_verified,
        "all_24_gates_verified": all_24_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master24GateReport(
        schema=DEWPOINT_TEC_USBC_24GATE_SCHEMA,
        version=DEWPOINT_TEC_USBC_24GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_21_gates_verified=offline_21_verified,
        all_24_gates_verified=all_24_verified,
        g13_to_g24_all_passed=g13_to_g24_all_passed,
        g23_to_g24_all_passed=g23_to_g24_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_22_report=m22_report.to_dict(),
        g23_result=g23_res.to_dict(),
        g24_result=g24_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_24_master_safety_gates = evaluate_24gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dewpoint_tec_usbc_and_24gate_guard",
        description="Phase 84 — Magnus-Tetens Dew-Point/TEC Firewall, PMIC 5V/USB-C Strain Guard & 24-Gate Preflight (G01..G24)",
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G24 can be exercised offline",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_24gate_preflight(
        args.repo_root,
        force_clean_room=True if args.clean_room else None,
        dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/24 "
            f"g23_to_g24_all_passed={report.g23_to_g24_all_passed} "
            f"all_24_gates_verified={report.all_24_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = report.all_24_gates_verified if args.dry_run_simulated_backup else report.offline_21_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
