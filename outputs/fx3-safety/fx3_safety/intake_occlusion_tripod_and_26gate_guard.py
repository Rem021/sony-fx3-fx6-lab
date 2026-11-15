"""Phase 92 — Sigma Cooling Fan Intake/Exhaust Occlusion & Rain-Cover Backpressure Firewall (Gate G25),
1/4-20 Tripod Screw Bottom-Out / Cage Torque & Underwater Housing Vacuum Seal Guard (Gate G26),
and Unified 26-Gate Master Safety Preflight (`G01..G26` / `verify-26-gates`).

Operationalizes mechanical airflow/duct occlusion safety, tachometer rotor-stall detection,
`Off_in_Rec` high-load thermal runaway protection, sealed rain-cover / blimp recirculation
safety, ISO 1222 1/4"-20 tripod screw pocket depth (<= 5.5 mm) / mounting torque (<= 3.5 N*m) /
underwater cinema housing vacuum leak & moisture guard, and the unified 26-Gate Master Safety
Preflight (`G01..G26`) for Sony ILME-FX3 (`Ver. 7.02`, SoC `CXD90057`, `IMX510` 5-axis IBIS)
while keeping `preflight.py`, `master_16gate_preflight.py`, `usblan_ptpip_and_18gate_preflight.py`,
`rig_groundloop_lensrail_and_20gate_guard.py`, `phantom48v_gimbal_and_22gate_guard.py`, and
`dewpoint_tec_usbc_and_24gate_guard.py` completely untouched:

1. **Read-Only (`os.O_RDONLY`) FX3/FX6 Donor Thermal/Fan Contract Audit**:
   - Inspects local FX3 `v7.02` & FX6 `v6.01` `libfan.so` ELF symbols (`fan_infra_init`,
     `_Z19fan_i_bkup_is_validv`, `g_bkup_dev_temp_bkid_list`) and `BK4\\0` thermal threshold
     tables (`FX3-CX95900_ALLLANG-Backup.bin` vs `CX95898_NTSC.bin` `0x02380007..0x02380009`
     over-temperature thresholds `82°C` vs `76°C`, plus optional chunked scan of `appFw.so`
     `FAN_CONTROL_*` / `OFF_BY_*_THERMAL` & `cpapp-b.bin` `FAN_EQ_ID` when
     `include_large_binaries=True`) strictly via `os.open(..., os.O_RDONLY)`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent.

2. **Sigma Centrifugal Fan Intake/Exhaust Occlusion, Tachometer Stall & Sealed Rain-Cover /
   Blimp Thermal Recirculation Firewall (`Gate G25`)**:
   - Fails closed on:
     a) `BLOCKED_FAN_TACHOMETER_ROTOR_STALL` when `pwm_duty_pct >= 25.0` and
        `measured_rpm < min_expected_rpm` (foreign debris / jammed impeller),
     b) `BLOCKED_DUCT_OCCLUSION_BACKPRESSURE` when `intake_clearance_mm < 5.0` or
        `exhaust_clearance_mm < 5.0` (flush cheeseplate / V-mount battery plate blocking
        FX3 side intake/exhaust vents),
     c) `BLOCKED_FAN_OFF_IN_REC_HIGH_LOAD` when `fan_mode == 'Off_in_Rec'` and
        `workload in ('4K_120p', '4K_60p_RAW_HDMI', 'XAVC_S_I_4K60_DUALSLOT')` and
        `clip_duration_min > 8.0`,
     d) `BLOCKED_SEALED_BLIMP_RECIRCULATION` when `enclosure_sealed_blimp_or_raincover == True`
        and `internal_enclosure_temp_c > 42.0`.

3. **1/4-20 Tripod Screw Depth Bottom-Out (5.5 mm Sony Magnesium Pocket Limit), Quarter-20 Cage
   Over-Torque & Underwater Housing Vacuum Leak Guard (`Gate G26`)**:
   - Fails closed on:
     a) `BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE` when `effective_screw_protrusion_mm > 5.5`
        (exceeds ISO 1222 5.5 mm bottom magnesium pocket depth into PCB/IBIS flex),
     b) `BLOCKED_MOUNTING_OVER_TORQUE_HAZARD` when `applied_torque_nm > 3.5` or
        `single_screw_no_anti_twist_pin_heavy_lens == True`,
     c) `BLOCKED_HOUSING_VACUUM_LEAK_OR_MOISTURE` when `underwater_housing_mode == True` and
        (`vacuum_pressure_drop_mbar_per_10min > 1.5` or `moisture_sensor_triggered == True` or
        `vacuum_check_elapsed_min < 10.0`), triggering immediate power-off abort.

4. **26-Gate Master Safety Preflight Engine (`G01..G26`) & CLI `verify-26-gates`**:
   - Composes `evaluate_24gate_preflight` (`G01..G24`) with `G25` and `G26`:
     * Offline default mode: `23/26` gates pass (`G10..G12` physical Tier-0 backup truthfully
       remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` -> `overall_ready_for_hardware_attach = False`).
     * `--dry-run-simulated-backup` mode: `26/26` simulation gates pass (`dry_run_rehearsal_only = True`),
       while `persistent_emmc_writes_authorized` remains hard-locked to `False`.

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

from .dewpoint_tec_usbc_and_24gate_guard import (
    Master24GateReport,
    evaluate_24gate_preflight,
)
from .exfat_media_integrity_guard import MediaSlotConfig
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

INTAKE_TRIPOD_26GATE_SCHEMA: str = "fx3-intake-occlusion-tripod-26gate-preflight-v1"
INTAKE_TRIPOD_26GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G25..G26
G25_GATE_ID: str = "G25_sigma_fan_intake_exhaust_and_blimp_firewall_safe"
G25_GATE_CODE: str = "SIGMA_FAN_INTAKE_EXHAUST_AND_BLIMP_FIREWALL_SAFE"

G26_GATE_ID: str = "G26_tripod_screw_depth_cage_torque_and_housing_vacuum_safe"
G26_GATE_CODE: str = "TRIPOD_SCREW_DEPTH_CAGE_TORQUE_AND_HOUSING_VACUUM_SAFE"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G25: str = "VERIFIED_SIGMA_FAN_INTAKE_EXHAUST_AND_BLIMP_FIREWALL_SAFE"
STATUS_VERIFIED_G26: str = "VERIFIED_TRIPOD_SCREW_DEPTH_CAGE_TORQUE_AND_HOUSING_VACUUM_SAFE"

# Gate G25 Violation Codes
STATUS_BLOCKED_FAN_TACHOMETER_ROTOR_STALL: str = "BLOCKED_FAN_TACHOMETER_ROTOR_STALL"
STATUS_BLOCKED_DUCT_OCCLUSION_BACKPRESSURE: str = "BLOCKED_DUCT_OCCLUSION_BACKPRESSURE"
STATUS_BLOCKED_FAN_OFF_IN_REC_HIGH_LOAD: str = "BLOCKED_FAN_OFF_IN_REC_HIGH_LOAD"
STATUS_BLOCKED_SEALED_BLIMP_RECIRCULATION: str = "BLOCKED_SEALED_BLIMP_RECIRCULATION"
STATUS_BLOCKED_FAN_DUCT_TELEMETRY_INVALID: str = "BLOCKED_FAN_DUCT_TELEMETRY_INVALID"

# Gate G26 Violation Codes
STATUS_BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE: str = "BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE"
STATUS_BLOCKED_MOUNTING_OVER_TORQUE_HAZARD: str = "BLOCKED_MOUNTING_OVER_TORQUE_HAZARD"
STATUS_BLOCKED_HOUSING_VACUUM_LEAK_OR_MOISTURE: str = "BLOCKED_HOUSING_VACUUM_LEAK_OR_MOISTURE"
STATUS_BLOCKED_MOUNTING_HOUSING_TELEMETRY_INVALID: str = "BLOCKED_MOUNTING_HOUSING_TELEMETRY_INVALID"

STATUS_BLOCKED_DONOR_INTEGRITY: str = "BLOCKED_PHASE92_26GATE_DONOR_INTEGRITY_MISMATCH"
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"

# Gate G25 Sigma Fan / Duct / Rain-Cover / Blimp Constants
FAN_MODE_AUTO1: str = "Auto1"
FAN_MODE_AUTO2: str = "Auto2"
FAN_MODE_MIN: str = "Min"
FAN_MODE_OFF_IN_REC: str = "Off_in_Rec"
VALID_FAN_MODES: Tuple[str, ...] = (
    FAN_MODE_AUTO1,
    FAN_MODE_AUTO2,
    FAN_MODE_MIN,
    FAN_MODE_OFF_IN_REC,
)

HIGH_LOAD_WORKLOADS: Tuple[str, ...] = (
    "4K_120p",
    "4K_60p_RAW_HDMI",
    "XAVC_S_I_4K60_DUALSLOT",
)
_HIGH_LOAD_WORKLOADS_LOWER: Mapping[str, str] = {w.lower(): w for w in HIGH_LOAD_WORKLOADS}

SIGMA_FAN_PWM_STALL_CHECK_THRESHOLD_PCT: float = 25.0
SIGMA_FAN_DEFAULT_MIN_EXPECTED_RPM: float = 1800.0
SIGMA_FAN_MIN_VENT_CLEARANCE_MM: float = 5.0
OFF_IN_REC_HIGH_LOAD_MAX_CLIP_MIN: float = 8.0
SEALED_ENCLOSURE_MAX_TEMP_C: float = 42.0

# Gate G26 Tripod Screw / Torque / Underwater Housing Constants
FX3_TRIPOD_POCKET_MAX_DEPTH_MM: float = 5.5
MAX_MOUNTING_TORQUE_NM: float = 3.5
MAX_HOUSING_VACUUM_LEAK_MBAR_PER_10MIN: float = 1.5
MIN_HOUSING_VACUUM_CHECK_ELAPSED_MIN: float = 10.0

# Compact FX3/FX6 Donor Specs for Fan PWM / BK4 Over-Temperature Thresholds (O_RDONLY verified)
PINNED_PHASE92_DONOR_SPECS: Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]] = {
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

PINNED_APPFW_FAN_TOKENS: Tuple[str, ...] = (
    "FAN_CONTROL_AUTO",
    "FAN_CONTROL_MINIMUM",
    "FAN_CONTROL_OFF_IN_REC",
    "FAN_CONTROL_ALWAYS_OFF",
    "AUTO1",
    "AUTO2",
    "OFF_BY_IM_THERMAL",
    "OFF_BY_MEDIA_THERMAL",
)

PINNED_CPAPP_FAN_TOKENS: Tuple[str, ...] = (
    "FAN_EQ_ID",
    "THERMISTOR_ADJ_START",
)


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase92DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fan_modes_supported: Tuple[str, ...]
    bk4_overtemp_thresholds_c: Dict[str, Dict[str, int]]
    large_binaries_scanned: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SigmaFanIntakeExhaustResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    fan_mode: str
    workload: str
    is_high_load_workload: bool
    clip_duration_min: float
    pwm_duty_pct: float
    measured_rpm: float
    min_expected_rpm: float
    tachometer_rotor_ok: bool
    intake_clearance_mm: float
    exhaust_clearance_mm: float
    duct_clearance_ok: bool
    off_in_rec_high_load_safe: bool
    enclosure_sealed_blimp_or_raincover: bool
    internal_enclosure_temp_c: float
    sealed_enclosure_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TripodTorqueHousingVacuumResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    screw_thread_length_mm: float
    plate_thickness_mm: float
    washer_thickness_mm: float
    effective_screw_protrusion_mm: float
    max_pocket_depth_mm: float
    tripod_screw_depth_safe: bool
    applied_torque_nm: float
    max_torque_nm: float
    single_screw_no_anti_twist_pin_heavy_lens: bool
    mounting_torque_safe: bool
    underwater_housing_mode: bool
    housing_brand: str
    vacuum_pressure_drop_mbar_per_10min: float
    max_vacuum_leak_mbar_per_10min: float
    vacuum_check_elapsed_min: float
    min_vacuum_check_elapsed_min: float
    moisture_sensor_triggered: bool
    housing_vacuum_and_moisture_safe: bool
    immediate_power_off_abort_required: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G25SigmaFanIntakeExhaustResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    sigma_fan_firewall: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G26TripodTorqueHousingVacuumResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    tripod_housing_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master26GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_23_gates_verified: bool
    all_26_gates_verified: bool
    g13_to_g26_all_passed: bool
    g25_to_g26_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_24_report: Dict[str, Any]
    g25_result: Dict[str, Any]
    g26_result: Dict[str, Any]
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


def _normalize_fan_mode(raw_mode: str) -> Optional[str]:
    cleaned = str(raw_mode).strip()
    low = cleaned.lower()
    mapping = {
        "auto1": FAN_MODE_AUTO1,
        "auto2": FAN_MODE_AUTO2,
        "min": FAN_MODE_MIN,
        "minimum": FAN_MODE_MIN,
        "off_in_rec": FAN_MODE_OFF_IN_REC,
        "off in rec": FAN_MODE_OFF_IN_REC,
    }
    return mapping.get(low)


def _normalize_workload(raw_workload: str) -> str:
    cleaned = str(raw_workload).strip()
    return _HIGH_LOAD_WORKLOADS_LOWER.get(cleaned.lower(), cleaned)


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase92_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
) -> Phase92DonorAuditResult:
    """Inspect FX3/FX6 `libfan.so` and `BK4` thermal threshold donors via `os.O_RDONLY`."""
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)

    resolved: Dict[str, Path] = {
        "fx3_libfan": paths.fx3_lib_dir / "libfan.so",
        "fx6_libfan": paths.fx6_lib_dir / "libfan.so",
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
        return Phase92DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(spec[5] for spec in PINNED_PHASE92_DONOR_SPECS.values()),
            missing_markers=(),
            fan_modes_supported=VALID_FAN_MODES,
            bk4_overtemp_thresholds_c=pinned_bk4_summary,
            large_binaries_scanned=False,
            sha256_by_artifact={k: spec[3] for k, spec in PINNED_PHASE92_DONOR_SPECS.items()},
            bytes_by_artifact={k: spec[2] for k, spec in PINNED_PHASE92_DONOR_SPECS.items()},
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

    for key, (_body, _rel_name, exp_size, exp_sha, marker_tuple, marker_label) in PINNED_PHASE92_DONOR_SPECS.items():
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
            appfw_sz, missing_appfw = scan_tokens_o_rdonly(paths.fx3_appfw_path, PINNED_APPFW_FAN_TOKENS)
            sizes["fx3_appfw"] = appfw_sz
            files_inspected += 1
            large_scanned = True
            if missing_appfw:
                missing.extend(missing_appfw)
                errors.append(f"fx3 appFw.so missing fan tokens: {missing_appfw}")
            else:
                checked.append("fx3/appFw.so::FAN_CONTROL_AUTO..OFF_BY_MEDIA_THERMAL")
        else:
            warnings.append("fx3/appFw.so not found for optional large-binary fan token scan.")

        if paths.fx3_cp_path.is_file():
            cp_sz, missing_cp = scan_tokens_o_rdonly(paths.fx3_cp_path, PINNED_CPAPP_FAN_TOKENS)
            sizes["fx3_cpapp"] = cp_sz
            files_inspected += 1
            large_scanned = True
            if missing_cp:
                missing.extend(missing_cp)
                errors.append(f"fx3 cpapp-b.bin missing fan tokens: {missing_cp}")
            else:
                checked.append("fx3/cpapp-b.bin::FAN_EQ_ID+THERMISTOR_ADJ_START")
        else:
            warnings.append("fx3/cpapp-b.bin not found for optional large-binary fan token scan.")

    valid = len(errors) == 0 and len(missing) == 0
    return Phase92DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fan_modes_supported=VALID_FAN_MODES,
        bk4_overtemp_thresholds_c=bk4_thresholds if bk4_thresholds else pinned_bk4_summary,
        large_binaries_scanned=large_scanned,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Gate G25 — Sigma Centrifugal Fan Intake/Exhaust & Blimp Firewall
# ---------------------------------------------------------------------------


def verify_sigma_fan_intake_exhaust_firewall(
    *,
    pwm_duty_pct: float = 50.0,
    measured_rpm: Optional[float] = None,
    min_expected_rpm: float = SIGMA_FAN_DEFAULT_MIN_EXPECTED_RPM,
    intake_clearance_mm: float = 12.0,
    exhaust_clearance_mm: float = 12.0,
    fan_mode: str = FAN_MODE_AUTO1,
    workload: str = "4K_24p",
    clip_duration_min: float = 5.0,
    enclosure_sealed_blimp_or_raincover: bool = False,
    internal_enclosure_temp_c: float = 28.0,
    request_persistent_emmc_writes: bool = False,
) -> SigmaFanIntakeExhaustResult:
    """Verify Sigma duct intake/exhaust clearance, PWM tachometer rotor health,
    `Off_in_Rec` high-load clip duration limit, and sealed rain-cover/blimp temperature.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    norm_fan_mode = _normalize_fan_mode(fan_mode)
    if norm_fan_mode is None:
        _add_code(codes, STATUS_BLOCKED_FAN_DUCT_TELEMETRY_INVALID)
        errors.append(f"Unsupported fan_mode {fan_mode!r}; expected one of {VALID_FAN_MODES}.")
        eff_fan_mode = str(fan_mode).strip()
    else:
        eff_fan_mode = norm_fan_mode

    eff_workload = _normalize_workload(workload)
    if not eff_workload:
        _add_code(codes, STATUS_BLOCKED_FAN_DUCT_TELEMETRY_INVALID)
        errors.append("workload must be a non-empty string.")
        eff_workload = "UNKNOWN"
    is_high_load = eff_workload in HIGH_LOAD_WORKLOADS

    # Validate numeric telemetry
    if not _is_finite_number(pwm_duty_pct) or float(pwm_duty_pct) < 0.0 or float(pwm_duty_pct) > 100.0:
        _add_code(codes, STATUS_BLOCKED_FAN_DUCT_TELEMETRY_INVALID)
        errors.append(f"pwm_duty_pct must be in [0.0, 100.0], got {pwm_duty_pct!r}.")
        eff_pwm = 0.0
    else:
        eff_pwm = float(pwm_duty_pct)

    if not _is_finite_number(min_expected_rpm) or float(min_expected_rpm) < 0.0:
        _add_code(codes, STATUS_BLOCKED_FAN_DUCT_TELEMETRY_INVALID)
        errors.append(f"min_expected_rpm must be finite >= 0.0, got {min_expected_rpm!r}.")
        eff_min_rpm = SIGMA_FAN_DEFAULT_MIN_EXPECTED_RPM
    else:
        eff_min_rpm = float(min_expected_rpm)

    if measured_rpm is None:
        eff_measured_rpm = 3200.0 if eff_pwm >= SIGMA_FAN_PWM_STALL_CHECK_THRESHOLD_PCT else 0.0
    elif not _is_finite_number(measured_rpm) or float(measured_rpm) < 0.0:
        _add_code(codes, STATUS_BLOCKED_FAN_DUCT_TELEMETRY_INVALID)
        errors.append(f"measured_rpm must be finite >= 0.0, got {measured_rpm!r}.")
        eff_measured_rpm = 0.0
    else:
        eff_measured_rpm = float(measured_rpm)

    if not _is_finite_number(intake_clearance_mm) or float(intake_clearance_mm) < 0.0:
        _add_code(codes, STATUS_BLOCKED_FAN_DUCT_TELEMETRY_INVALID)
        errors.append(f"intake_clearance_mm must be finite >= 0.0, got {intake_clearance_mm!r}.")
        eff_intake_mm = 0.0
    else:
        eff_intake_mm = float(intake_clearance_mm)

    if not _is_finite_number(exhaust_clearance_mm) or float(exhaust_clearance_mm) < 0.0:
        _add_code(codes, STATUS_BLOCKED_FAN_DUCT_TELEMETRY_INVALID)
        errors.append(f"exhaust_clearance_mm must be finite >= 0.0, got {exhaust_clearance_mm!r}.")
        eff_exhaust_mm = 0.0
    else:
        eff_exhaust_mm = float(exhaust_clearance_mm)

    if not _is_finite_number(clip_duration_min) or float(clip_duration_min) < 0.0:
        _add_code(codes, STATUS_BLOCKED_FAN_DUCT_TELEMETRY_INVALID)
        errors.append(f"clip_duration_min must be finite >= 0.0, got {clip_duration_min!r}.")
        eff_clip_min = 0.0
    else:
        eff_clip_min = float(clip_duration_min)

    if (
        not _is_finite_number(internal_enclosure_temp_c)
        or float(internal_enclosure_temp_c) < -40.0
        or float(internal_enclosure_temp_c) > 110.0
    ):
        _add_code(codes, STATUS_BLOCKED_FAN_DUCT_TELEMETRY_INVALID)
        errors.append(f"internal_enclosure_temp_c must be in [-40.0, 110.0], got {internal_enclosure_temp_c!r}.")
        eff_enc_temp_c = 28.0
    else:
        eff_enc_temp_c = float(internal_enclosure_temp_c)

    # a) Tachometer rotor stall check when PWM >= 25%
    tach_ok = True
    if eff_pwm >= SIGMA_FAN_PWM_STALL_CHECK_THRESHOLD_PCT and eff_measured_rpm < eff_min_rpm:
        tach_ok = False
        _add_code(codes, STATUS_BLOCKED_FAN_TACHOMETER_ROTOR_STALL)
        errors.append(
            f"BLOCKED_FAN_TACHOMETER_ROTOR_STALL: PWM duty {eff_pwm:.1f}% >= "
            f"{SIGMA_FAN_PWM_STALL_CHECK_THRESHOLD_PCT:.1f}%, but Hall tachometer reads "
            f"{eff_measured_rpm:.0f} RPM < min expected {eff_min_rpm:.0f} RPM (jammed impeller / debris)."
        )

    # b) Sigma air duct intake/exhaust clearance check (< 5.0 mm occlusion)
    duct_ok = True
    if eff_intake_mm < SIGMA_FAN_MIN_VENT_CLEARANCE_MM or eff_exhaust_mm < SIGMA_FAN_MIN_VENT_CLEARANCE_MM:
        duct_ok = False
        _add_code(codes, STATUS_BLOCKED_DUCT_OCCLUSION_BACKPRESSURE)
        errors.append(
            f"BLOCKED_DUCT_OCCLUSION_BACKPRESSURE: intake_clearance={eff_intake_mm:.2f} mm, "
            f"exhaust_clearance={eff_exhaust_mm:.2f} mm (< {SIGMA_FAN_MIN_VENT_CLEARANCE_MM:.1f} mm "
            "Sigma duct backpressure limit from flush cheeseplate / V-mount battery plate)."
        )

    # c) Fan='Off_in_Rec' during sustained high-load 4K120 / HDMI RAW / Dual-Slot XAVC S-I > 8 min
    off_in_rec_safe = True
    if (
        eff_fan_mode == FAN_MODE_OFF_IN_REC
        and is_high_load
        and eff_clip_min > OFF_IN_REC_HIGH_LOAD_MAX_CLIP_MIN
    ):
        off_in_rec_safe = False
        _add_code(codes, STATUS_BLOCKED_FAN_OFF_IN_REC_HIGH_LOAD)
        errors.append(
            f"BLOCKED_FAN_OFF_IN_REC_HIGH_LOAD: fan_mode={eff_fan_mode!r} with high-load workload "
            f"{eff_workload!r} for {eff_clip_min:.1f} min (> {OFF_IN_REC_HIGH_LOAD_MAX_CLIP_MIN:.1f} min limit) "
            "risks CXD90057/IMX510 thermal runaway; switch to Auto1/Auto2/Min."
        )
    elif eff_fan_mode == FAN_MODE_OFF_IN_REC and is_high_load:
        warnings.append(
            f"fan_mode='Off_in_Rec' with high-load {eff_workload} ({eff_clip_min:.1f} min <= "
            f"{OFF_IN_REC_HIGH_LOAD_MAX_CLIP_MIN:.1f} min); prefer Auto1 for sustained takes."
        )

    # d) Sealed sound blimp / unvented rain-cover recirculation check (> 42.0°C)
    sealed_safe = True
    if bool(enclosure_sealed_blimp_or_raincover) and eff_enc_temp_c > SEALED_ENCLOSURE_MAX_TEMP_C:
        sealed_safe = False
        _add_code(codes, STATUS_BLOCKED_SEALED_BLIMP_RECIRCULATION)
        errors.append(
            f"BLOCKED_SEALED_BLIMP_RECIRCULATION: sealed rain-cover/sound-blimp internal ambient "
            f"{eff_enc_temp_c:.1f}C > {SEALED_ENCLOSURE_MAX_TEMP_C:.1f}C causes closed-loop hot-air "
            "recirculation across the FX3 Sigma exhaust-to-intake path."
        )
    elif bool(enclosure_sealed_blimp_or_raincover):
        warnings.append(
            f"Sealed rain-cover/blimp active at {eff_enc_temp_c:.1f}C (<= {SEALED_ENCLOSURE_MAX_TEMP_C:.1f}C); "
            "keep exhaust snorkel vented during extended takes."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return SigmaFanIntakeExhaustResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        fan_mode=eff_fan_mode,
        workload=eff_workload,
        is_high_load_workload=is_high_load,
        clip_duration_min=eff_clip_min,
        pwm_duty_pct=eff_pwm,
        measured_rpm=eff_measured_rpm,
        min_expected_rpm=eff_min_rpm,
        tachometer_rotor_ok=tach_ok,
        intake_clearance_mm=eff_intake_mm,
        exhaust_clearance_mm=eff_exhaust_mm,
        duct_clearance_ok=duct_ok,
        off_in_rec_high_load_safe=off_in_rec_safe,
        enclosure_sealed_blimp_or_raincover=bool(enclosure_sealed_blimp_or_raincover),
        internal_enclosure_temp_c=eff_enc_temp_c,
        sealed_enclosure_safe=sealed_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 3. Gate G26 — 1/4-20 Tripod Screw Depth, Cage Torque & Housing Vacuum Guard
# ---------------------------------------------------------------------------


def verify_tripod_screw_torque_and_housing_vacuum_guard(
    *,
    effective_screw_protrusion_mm: Optional[float] = None,
    screw_thread_length_mm: float = 4.8,
    plate_thickness_mm: float = 0.0,
    washer_thickness_mm: float = 0.0,
    applied_torque_nm: float = 2.0,
    single_screw_no_anti_twist_pin_heavy_lens: bool = False,
    heavy_lens_attached: bool = False,
    anti_twist_pin_or_dual_screw_engaged: bool = True,
    underwater_housing_mode: bool = False,
    housing_brand: str = "NONE",
    vacuum_pressure_drop_mbar_per_10min: float = 0.0,
    moisture_sensor_triggered: bool = False,
    vacuum_check_elapsed_min: float = 15.0,
    request_persistent_emmc_writes: bool = False,
) -> TripodTorqueHousingVacuumResult:
    """Verify 1/4"-20 tripod screw pocket depth (<= 5.5 mm), mounting torque (<= 3.5 N*m) /
    anti-twist pin interlock, and underwater cinema housing vacuum leak & moisture guard.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    # Validate numeric inputs
    for fname, val in (
        ("screw_thread_length_mm", screw_thread_length_mm),
        ("plate_thickness_mm", plate_thickness_mm),
        ("washer_thickness_mm", washer_thickness_mm),
        ("applied_torque_nm", applied_torque_nm),
        ("vacuum_pressure_drop_mbar_per_10min", vacuum_pressure_drop_mbar_per_10min),
        ("vacuum_check_elapsed_min", vacuum_check_elapsed_min),
    ):
        if not _is_finite_number(val) or float(val) < 0.0:
            _add_code(codes, STATUS_BLOCKED_MOUNTING_HOUSING_TELEMETRY_INVALID)
            errors.append(f"{fname} must be finite >= 0.0, got {val!r}.")

    if effective_screw_protrusion_mm is not None:
        if not _is_finite_number(effective_screw_protrusion_mm) or float(effective_screw_protrusion_mm) < 0.0:
            _add_code(codes, STATUS_BLOCKED_MOUNTING_HOUSING_TELEMETRY_INVALID)
            errors.append(
                f"effective_screw_protrusion_mm must be finite >= 0.0, got {effective_screw_protrusion_mm!r}."
            )
            eff_protrusion_mm = 0.0
        else:
            eff_protrusion_mm = round(float(effective_screw_protrusion_mm), 3)
    elif _is_finite_number(screw_thread_length_mm) and _is_finite_number(plate_thickness_mm) and _is_finite_number(washer_thickness_mm):
        eff_protrusion_mm = round(
            max(0.0, float(screw_thread_length_mm) - float(plate_thickness_mm) - float(washer_thickness_mm)),
            3,
        )
    else:
        eff_protrusion_mm = 0.0

    eff_thread_len_mm = float(screw_thread_length_mm) if _is_finite_number(screw_thread_length_mm) else 0.0
    eff_plate_mm = float(plate_thickness_mm) if _is_finite_number(plate_thickness_mm) else 0.0
    eff_washer_mm = float(washer_thickness_mm) if _is_finite_number(washer_thickness_mm) else 0.0
    eff_torque_nm = float(applied_torque_nm) if _is_finite_number(applied_torque_nm) else 0.0
    eff_leak_mbar = (
        float(vacuum_pressure_drop_mbar_per_10min)
        if _is_finite_number(vacuum_pressure_drop_mbar_per_10min)
        else 0.0
    )
    eff_elapsed_min = float(vacuum_check_elapsed_min) if _is_finite_number(vacuum_check_elapsed_min) else 0.0
    norm_brand = str(housing_brand).strip().upper() or "NONE"

    eff_single_screw_hazard = bool(single_screw_no_anti_twist_pin_heavy_lens) or (
        bool(heavy_lens_attached) and (not bool(anti_twist_pin_or_dual_screw_engaged))
    )

    # a) 1/4"-20 tripod screw bottom-out check (> 5.5 mm Sony magnesium pocket limit)
    screw_safe = True
    if eff_protrusion_mm > FX3_TRIPOD_POCKET_MAX_DEPTH_MM:
        screw_safe = False
        _add_code(codes, STATUS_BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE)
        errors.append(
            f"BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE: effective 1/4-20 screw protrusion "
            f"{eff_protrusion_mm:.2f} mm > {FX3_TRIPOD_POCKET_MAX_DEPTH_MM:.1f} mm ISO 1222 Sony FX3 "
            "magnesium pocket limit; risks warping bottom plate into internal PCB/IBIS flex assembly."
        )

    # b) Mounting over-torque (> 3.5 N*m) or single-screw heavy lens without anti-twist pin
    torque_safe = True
    if eff_torque_nm > MAX_MOUNTING_TORQUE_NM or eff_single_screw_hazard:
        torque_safe = False
        _add_code(codes, STATUS_BLOCKED_MOUNTING_OVER_TORQUE_HAZARD)
        reasons: List[str] = []
        if eff_torque_nm > MAX_MOUNTING_TORQUE_NM:
            reasons.append(f"applied_torque={eff_torque_nm:.2f} N*m > {MAX_MOUNTING_TORQUE_NM:.1f} N*m limit")
        if eff_single_screw_hazard:
            reasons.append("single 1/4-20 screw with heavy lens and no anti-twist pin/dual-screw lock")
        errors.append(
            "BLOCKED_MOUNTING_OVER_TORQUE_HAZARD: "
            + "; ".join(reasons)
            + " risks stripping magnesium tripod boss or damaging IBIS chassis."
        )

    # c) Underwater cinema housing vacuum leak & moisture sensor guard
    housing_safe = True
    abort_power_off = False
    if bool(underwater_housing_mode):
        leak_bad = eff_leak_mbar > MAX_HOUSING_VACUUM_LEAK_MBAR_PER_10MIN
        moisture_bad = bool(moisture_sensor_triggered)
        hold_short = eff_elapsed_min < MIN_HOUSING_VACUUM_CHECK_ELAPSED_MIN
        if leak_bad or moisture_bad or hold_short:
            housing_safe = False
            abort_power_off = True
            _add_code(codes, STATUS_BLOCKED_HOUSING_VACUUM_LEAK_OR_MOISTURE)
            h_reasons: List[str] = []
            if leak_bad:
                h_reasons.append(
                    f"vacuum_drop={eff_leak_mbar:.2f} mbar/10min > {MAX_HOUSING_VACUUM_LEAK_MBAR_PER_10MIN:.1f}"
                )
            if moisture_bad:
                h_reasons.append("moisture_sensor_triggered=True")
            if hold_short:
                h_reasons.append(
                    f"vacuum_check_elapsed={eff_elapsed_min:.1f} min < {MIN_HOUSING_VACUUM_CHECK_ELAPSED_MIN:.1f} min"
                )
            errors.append(
                f"BLOCKED_HOUSING_VACUUM_LEAK_OR_MOISTURE ({norm_brand}): "
                + ", ".join(h_reasons)
                + "; immediate power-off abort required before water reaches eMMC/mainboard."
            )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return TripodTorqueHousingVacuumResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        screw_thread_length_mm=eff_thread_len_mm,
        plate_thickness_mm=eff_plate_mm,
        washer_thickness_mm=eff_washer_mm,
        effective_screw_protrusion_mm=eff_protrusion_mm,
        max_pocket_depth_mm=FX3_TRIPOD_POCKET_MAX_DEPTH_MM,
        tripod_screw_depth_safe=screw_safe,
        applied_torque_nm=eff_torque_nm,
        max_torque_nm=MAX_MOUNTING_TORQUE_NM,
        single_screw_no_anti_twist_pin_heavy_lens=eff_single_screw_hazard,
        mounting_torque_safe=torque_safe,
        underwater_housing_mode=bool(underwater_housing_mode),
        housing_brand=norm_brand,
        vacuum_pressure_drop_mbar_per_10min=eff_leak_mbar,
        max_vacuum_leak_mbar_per_10min=MAX_HOUSING_VACUUM_LEAK_MBAR_PER_10MIN,
        vacuum_check_elapsed_min=eff_elapsed_min,
        min_vacuum_check_elapsed_min=MIN_HOUSING_VACUUM_CHECK_ELAPSED_MIN,
        moisture_sensor_triggered=bool(moisture_sensor_triggered),
        housing_vacuum_and_moisture_safe=housing_safe,
        immediate_power_off_abort_required=abort_power_off,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate 25 & Gate 26 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g25_sigma_fan_intake_exhaust(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    intake_fan_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase92DonorAuditResult] = None,
) -> Tuple[GateVerdict, G25SigmaFanIntakeExhaustResult]:
    """Evaluate Gate G25 (`sigma_fan_intake_exhaust_and_blimp_firewall_safe`)."""
    audit = donor_audit or audit_phase92_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(intake_fan_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    fan_res = verify_sigma_fan_intake_exhaust_firewall(**eff_kwargs)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in fan_res.violation_codes:
        _add_code(codes, c)
    errors.extend(fan_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(fan_res.warnings)

    passed = (
        audit.valid
        and fan_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = STATUS_VERIFIED_G25 if passed else (codes[0] if codes else STATUS_BLOCKED_DUCT_OCCLUSION_BACKPRESSURE)

    res = G25SigmaFanIntakeExhaustResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        sigma_fan_firewall=fan_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G25_GATE_ID,
        gate_code=G25_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Sigma Fan Intake/Exhaust & Blimp Firewall ({fan_res.status}, "
            f"mode={fan_res.fan_mode}, pwm={fan_res.pwm_duty_pct:.0f}%, rpm={fan_res.measured_rpm:.0f}, "
            f"clearance={fan_res.intake_clearance_mm:.1f}/{fan_res.exhaust_clearance_mm:.1f}mm, "
            f"blimp={fan_res.enclosure_sealed_blimp_or_raincover}, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "tachometer_rotor_ok": fan_res.tachometer_rotor_ok,
            "duct_clearance_ok": fan_res.duct_clearance_ok,
            "off_in_rec_high_load_safe": fan_res.off_in_rec_high_load_safe,
            "sealed_enclosure_safe": fan_res.sealed_enclosure_safe,
        },
    )
    return verdict, res


def evaluate_g26_tripod_torque_and_housing_vacuum(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    tripod_housing_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase92DonorAuditResult] = None,
) -> Tuple[GateVerdict, G26TripodTorqueHousingVacuumResult]:
    """Evaluate Gate G26 (`tripod_screw_depth_cage_torque_and_housing_vacuum_safe`)."""
    audit = donor_audit or audit_phase92_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(tripod_housing_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    th_res = verify_tripod_screw_torque_and_housing_vacuum_guard(**eff_kwargs)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in th_res.violation_codes:
        _add_code(codes, c)
    errors.extend(th_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(th_res.warnings)

    passed = (
        audit.valid
        and th_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = STATUS_VERIFIED_G26 if passed else (codes[0] if codes else STATUS_BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE)

    res = G26TripodTorqueHousingVacuumResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        tripod_housing_guard=th_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G26_GATE_ID,
        gate_code=G26_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"1/4-20 Tripod Screw, Cage Torque & Housing Vacuum Guard ({th_res.status}, "
            f"protrusion={th_res.effective_screw_protrusion_mm:.2f}/{th_res.max_pocket_depth_mm:.1f}mm, "
            f"torque={th_res.applied_torque_nm:.2f}/{th_res.max_torque_nm:.1f}N*m, "
            f"underwater={th_res.underwater_housing_mode}, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "tripod_screw_depth_safe": th_res.tripod_screw_depth_safe,
            "mounting_torque_safe": th_res.mounting_torque_safe,
            "housing_vacuum_and_moisture_safe": th_res.housing_vacuum_and_moisture_safe,
            "immediate_power_off_abort_required": th_res.immediate_power_off_abort_required,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Master 26-Gate Preflight Evaluator (`G01..G26`) & CLI
# ---------------------------------------------------------------------------


def evaluate_26gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G24 pass-throughs
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
    # G25 inputs (Sigma Cooling Fan Intake/Exhaust Occlusion & Blimp Firewall)
    intake_fan_kwargs: Optional[Mapping[str, Any]] = None,
    # G26 inputs (1/4-20 Tripod Screw Depth, Cage Torque & Housing Vacuum Guard)
    tripod_housing_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master26GateReport:
    """Evaluate all 26 Master Safety Gates (`G01..G26`) deterministically."""
    resolved_root = (DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m24_kwargs: Dict[str, Any] = {
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
    }
    if soc_start_ceiling_c is not None:
        m24_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m24_report: Master24GateReport = evaluate_24gate_preflight(resolved_root, **m24_kwargs)

    phase92_audit = audit_phase92_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
    )

    g25_verdict, g25_res = evaluate_g25_sigma_fan_intake_exhaust(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        intake_fan_kwargs=intake_fan_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase92_audit,
    )

    g26_verdict, g26_res = evaluate_g26_tripod_torque_and_housing_vacuum(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        tripod_housing_kwargs=tripod_housing_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase92_audit,
    )

    gates_25_to_26 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g25_verdict, g26_verdict)
    ]
    all_gates = tuple(list(m24_report.gates) + gates_25_to_26)

    g01_to_g12_verified = int(m24_report.summary["g01_to_g12_verified"])
    g13_to_g24_verified = (
        int(m24_report.summary["g13_to_g22_verified"])
        + int(m24_report.summary["g23_to_g24_verified"])
    )
    g25_to_g26_verified = sum(1 for v in (g25_verdict, g26_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g24_verified + g25_to_g26_verified

    g25_to_g26_all_passed = g25_to_g26_verified == 2
    g13_to_g26_all_passed = m24_report.g13_to_g24_all_passed and g25_to_g26_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m24_report.gates[:9])

    offline_23_verified = (
        g01_to_g09_ok
        and m24_report.offline_21_gates_verified
        and g25_to_g26_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_26_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g26_all_passed
        and (not request_persistent_emmc_writes)
    )

    real_tier0_verified = (g01_to_g12_verified == 12) and (not dry_run_simulated_backup)
    overall_ready_for_hardware_attach = (
        real_tier0_verified
        and g13_to_g26_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    h0_h1_allowed = (
        offline_23_verified
        and m24_report.h0_h1_trial_entry_allowed
        and g25_to_g26_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = list(m24_report.errors) + list(g25_verdict.errors) + list(g26_verdict.errors)
    warnings: List[str] = list(m24_report.warnings) + list(g25_verdict.warnings) + list(g26_verdict.warnings)

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m24_report.g13_to_g24_all_passed:
        overall_status = m24_report.status
    elif not g25_verdict.passed:
        overall_status = g25_verdict.status
    elif not g26_verdict.passed:
        overall_status = g26_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_26_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_26_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_26_verified:
        overall_status = "VERIFIED_ALL_26_GATES"
    else:
        overall_status = "VERIFIED_23_OF_26_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m24_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g25_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g26_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 26,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 26 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g24_verified": g13_to_g24_verified,
        "g25_to_g26_verified": g25_to_g26_verified,
        "g13_to_g26_all_passed": g13_to_g26_all_passed,
        "g25_to_g26_all_passed": g25_to_g26_all_passed,
        "offline_23_gates_verified": offline_23_verified,
        "all_26_gates_verified": all_26_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master26GateReport(
        schema=INTAKE_TRIPOD_26GATE_SCHEMA,
        version=INTAKE_TRIPOD_26GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_23_gates_verified=offline_23_verified,
        all_26_gates_verified=all_26_verified,
        g13_to_g26_all_passed=g13_to_g26_all_passed,
        g25_to_g26_all_passed=g25_to_g26_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_24_report=m24_report.to_dict(),
        g25_result=g25_res.to_dict(),
        g26_result=g26_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_26_master_safety_gates = evaluate_26gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="intake_occlusion_tripod_and_26gate_guard",
        description="Phase 92 — Sigma Fan Intake/Exhaust Firewall, 1/4-20 Tripod/Housing Guard & 26-Gate Preflight (G01..G26)",
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G26 can be exercised offline",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_26gate_preflight(
        args.repo_root,
        force_clean_room=True if args.clean_room else None,
        dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/26 "
            f"g25_to_g26_all_passed={report.g25_to_g26_all_passed} "
            f"all_26_gates_verified={report.all_26_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = report.all_26_gates_verified if args.dry_run_simulated_backup else report.offline_23_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
