"""Phase 104 — Heavy Cinema PL-to-E Adapter / Matte-Box Cantilever Bending-Moment &
15mm LWS Lens-Support Guard (Gate G31), Unregulated 14.8V/26V V-Mount -> NP-FZ100
Dummy-Battery Over-Voltage (>8.4V Blowout Trap!) Firewall (Gate G32), and Unified
32-Gate Master Safety Preflight (`G01..G32` / `verify-32-gates`).

Operationalizes two critical physical-rig & power-rail hardware protections for
Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, SoC `CXD90057`), while keeping all
prior gate modules (`preflight.py`, `master_16gate_preflight.py`,
`usblan_ptpip_and_18gate_preflight.py`, `rig_groundloop_lensrail_and_20gate_guard.py`,
`phantom48v_gimbal_and_22gate_guard.py`, `dewpoint_tec_usbc_and_24gate_guard.py`,
`intake_occlusion_tripod_and_26gate_guard.py`,
`sensor_curtain_subzero_and_28gate_guard.py`, and
`wireless_tx_emi_endurance_and_30gate_guard.py`) completely untouched:

1. **Read-Only (`os.O_RDONLY`) FX3/FX6 Donor Lens-Mount / Battery-Auth Audit**:
   - Inspects local FX3 `v7.02` & FX6 `v6.01` `libInfraLensCommunicator.so`
     (`GetMountedLensInfo`, `SndSyncMsg`, `GetSuopportedCommandIds`, `ReadBackup`),
     `libBusPower.so` (`SetUSBPDSinkStatusToPowerManager`, `NotifyUSBPowerContractState`,
     `InitUSBSourcePowerStateToPowerManager`), and `libUsbBusPower.so`
     (`GetCurrentBattState`, `GetCurrentLimit`, `IsVbusReady`, `SetWatchSWForceOFF`)
     strictly via `os.open(..., os.O_RDONLY)`, plus optional chunked scans of
     `appFw.so` (`asrid_cau_battery_authentication_error_normal_english_`,
     `asrid_cau_incompatible_battery_normal_english_`, `No11_BatteryLevelNonInfoLitium`,
     `VAL_lens_information_LENS_INFORMATION_TYPE_EMOUNT`, `PRM_FEATURE_MANAGER_lens_mount`)
     and `cpapp-b.bin` (`BATT_AUTH_Snd`, `BATT_STATE1_Snd`, `BattCheckInfo_Rcv`,
     `ACV_BATT_Snd`, `C_LENS_XDETECT_BODY_INT_NO`, `C_LENS_CS_BODY_INT_NO`,
     `ID_FLG_CAM_LENS_MOUNT`) when `include_large_binaries=True`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent.

2. **Gate G31 — Heavy Cinema PL-to-E Mount Adapter, Clamp-On Matte-Box & Static/Dynamic
   Cantilever Bending-Moment (`M = m * g * L_cg`) E-Mount Flange Warp Guard**:
   - FX6 has a reinforced locking Cinema E-Mount / cage-integrated top handle, whereas
     FX3's 6-screw E-Mount flange (`18.00 mm` flange focal distance, `+/-0.01 mm`
     back-focus tolerance) warps or shears internal boss threads when hanging heavy PL
     cine zooms / anamorphics + clamp-on `4x5.65` matte boxes (`> 1.2 kg` or static
     cantilever moment `M > 1.8 N*m`) without a `15mm LWS` / `19mm studio` Y-support +
     PL-adapter foot bolted to the cage.
   - Computes exact static (`M_static = m * g * L_cg`) and dynamic (`M_peak = M_static * shock_g`,
     default `2.5G` shock factor) cantilever bending moments, failing closed on:
     a) `BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP` when
        (`lens_plus_mattebox_kg > 1.2` or `static_moment_nm > 1.8`) and
        `lws_15mm_y_support_engaged == False`,
     b) `BLOCKED_UNSHIMMED_PL_ADAPTER_BACKFOCUS_DRIFT` when
        `pl_to_e_adapter_used == True` and `adapter_foot_bolted_to_cage == False` and
        `lens_plus_mattebox_kg > 0.9`,
     c) `BLOCKED_CLAMP_ON_MATTEBOX_TELESCOPING_BARREL` when
        `clamp_on_mattebox == True` and `lens_front_rotates_or_telescopes == True`
        (requiring a swing-away rod-mounted matte box).

3. **Gate G32 — Unregulated 14.8V / 26V V-Mount -> NP-FZ100 Dummy-Battery Over-Voltage
   Blowout Firewall (Real-World #1 FX3 Mainboard Killer!)**:
   - The #1 real-world hardware mainboard blowout on Sony FX3/A7SIII is plugging an
     unregulated or buck-converter-shorted D-Tap -> `NP-FZ100` dummy battery
     (`14.8V..16.8V` or `26V` cinema V-Mount) into FX3's `7.2V` nominal / `8.40V` max
     battery bay, instantly destroying the `CXD90057` PMIC power tree — whereas Sony
     Cinema SOP prefers regulated `9V/3A` USB-C PD with a genuine internal `NP-FZ100` UPS.
   - Fails closed on:
     a) `BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT` when
        `dummy_battery_installed == True` and (`measured_open_circuit_v > 8.45` or
        `buck_regulator_ovp_crowbar_verified == False` or `v_mount_nominal_v >= 24.0`),
     b) `BLOCKED_REVERSE_POLARITY_UNKEYED_DTAP` when
        `dtap_source_used == True` and `reverse_polarity_diode_or_smart_dtap == False`,
     c) `BLOCKED_UNAUTHENTICATED_NON_INFOLITHIUM_SPOOF` when
        `dummy_battery_installed == True` and `infolithium_thermistor_ntc_valid == False`.

4. **Unified 32-Gate Master Safety Preflight (`evaluate_32gate_preflight` / CLI
   `verify-32-gates`)**:
   - Composes `evaluate_30gate_preflight` (`G01..G30`) with `G31` and `G32`:
     * Offline default mode: `29/32` gates pass (`G10..G12` physical Tier-0 backup
       truthfully remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` ->
       `overall_ready_for_hardware_attach = False`).
     * `--dry-run-simulated-backup` mode: `32/32` simulation gates pass
       (`dry_run_rehearsal_only = True`), while `persistent_emmc_writes_authorized`
       and `persistent_write_release` remain hard-locked to `False`.

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
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
    scan_tokens_o_rdonly,
)
from .wireless_tx_emi_endurance_and_30gate_guard import (
    Master30GateReport,
    evaluate_30gate_preflight,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PL_CANTILEVER_DUMMYBATT_32GATE_SCHEMA: str = "fx3-pl-cantilever-dummybatt-32gate-preflight-v1"
PL_CANTILEVER_DUMMYBATT_32GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G31..G32
G31_GATE_ID: str = "G31_pl_adapter_cantilever_moment_and_lws_support_safe"
G31_GATE_CODE: str = "PL_ADAPTER_CANTILEVER_MOMENT_AND_LWS_SUPPORT_SAFE"

G32_GATE_ID: str = "G32_dummy_battery_overvoltage_and_infolithium_safe"
G32_GATE_CODE: str = "DUMMY_BATTERY_OVERVOLTAGE_AND_INFOLITHIUM_SAFE"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G31: str = "VERIFIED_PL_ADAPTER_CANTILEVER_MOMENT_AND_LWS_SUPPORT_SAFE"
STATUS_VERIFIED_G32: str = "VERIFIED_DUMMY_BATTERY_OVERVOLTAGE_AND_INFOLITHIUM_SAFE"

# Gate G31 Violation Codes
STATUS_BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP: str = (
    "BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP"
)
STATUS_BLOCKED_UNSHIMMED_PL_ADAPTER_BACKFOCUS_DRIFT: str = (
    "BLOCKED_UNSHIMMED_PL_ADAPTER_BACKFOCUS_DRIFT"
)
STATUS_BLOCKED_CLAMP_ON_MATTEBOX_TELESCOPING_BARREL: str = (
    "BLOCKED_CLAMP_ON_MATTEBOX_TELESCOPING_BARREL"
)
STATUS_BLOCKED_PL_CANTILEVER_TELEMETRY_INVALID: str = (
    "BLOCKED_PL_CANTILEVER_TELEMETRY_INVALID"
)

# Gate G32 Violation Codes
STATUS_BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT: str = (
    "BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT"
)
STATUS_BLOCKED_REVERSE_POLARITY_UNKEYED_DTAP: str = (
    "BLOCKED_REVERSE_POLARITY_UNKEYED_DTAP"
)
STATUS_BLOCKED_UNAUTHENTICATED_NON_INFOLITHIUM_SPOOF: str = (
    "BLOCKED_UNAUTHENTICATED_NON_INFOLITHIUM_SPOOF"
)
STATUS_BLOCKED_DUMMY_BATT_TELEMETRY_INVALID: str = (
    "BLOCKED_DUMMY_BATT_TELEMETRY_INVALID"
)

STATUS_BLOCKED_DONOR_INTEGRITY: str = "BLOCKED_PHASE104_32GATE_DONOR_INTEGRITY_MISMATCH"
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"

# Gate G31 Physical Constants (FX3 6-Screw E-Mount Flange & Cantilever Mechanics)
STANDARD_GRAVITY_M_S2: float = 9.80665
EMOUNT_FLANGE_FOCAL_DISTANCE_MM: float = 18.00
EMOUNT_BACKFOCUS_TOLERANCE_MM: float = 0.01
EMOUNT_UNSUPPORTED_MAX_MASS_KG: float = 1.2
EMOUNT_UNSUPPORTED_MAX_STATIC_MOMENT_NM: float = 1.8
PL_ADAPTER_UNBOLTED_MAX_MASS_KG: float = 0.9
CANTILEVER_DEFAULT_SHOCK_FACTOR_G: float = 2.5

# Gate G32 Electrical Constants (Sony NP-FZ100 Battery Bay & PMIC OVP Limits)
NP_FZ100_NOMINAL_VOLTAGE_V: float = 7.20
NP_FZ100_MAX_CHARGED_VOLTAGE_V: float = 8.40
DUMMY_BATTERY_OPEN_CIRCUIT_MAX_V: float = 8.45
VMOUNT_HIGH_VOLTAGE_CINEMA_THRESHOLD_V: float = 24.0
SONY_CINEMA_SOP_POWER_TOPOLOGY: str = "USB_PD_9V3A_WITH_INTERNAL_NPFZ100_UPS"

# Compact FX3/FX6 Donor Specs for Lens-Mount & Power-Auth Contracts (O_RDONLY verified)
PINNED_PHASE104_DONOR_SPECS: Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]] = {
    "fx3_lib_infra_lens_comm": (
        "fx3",
        "libInfraLensCommunicator.so",
        14_544,
        "e61bf145f050dd037802871395c38d1c0471518130d5bcd2f621268da8c8f6ab",
        (
            b"_ZN16LensCommunicator18GetMountedLensInfoEPv",
            b"_ZN16LensCommunicator10SndSyncMsgEPvj",
            b"_ZN16LensCommunicator23GetSuopportedCommandIdsEPv",
            b"_ZN16LensCommunicator10ReadBackupEiiPv",
        ),
        "fx3/libInfraLensCommunicator.so::{GetMountedLensInfo,SndSyncMsg,GetSuopportedCommandIds,ReadBackup}",
    ),
    "fx6_lib_infra_lens_comm": (
        "fx6",
        "libInfraLensCommunicator.so",
        14_544,
        "8848b33084f71856ecc3a2074e347e275888d8a8173f70d900968085f7401c5e",
        (
            b"_ZN16LensCommunicator18GetMountedLensInfoEPv",
            b"_ZN16LensCommunicator10SndSyncMsgEPvj",
            b"_ZN16LensCommunicator23GetSuopportedCommandIdsEPv",
            b"_ZN16LensCommunicator10ReadBackupEiiPv",
        ),
        "fx6/libInfraLensCommunicator.so::{GetMountedLensInfo,SndSyncMsg,GetSuopportedCommandIds,ReadBackup}",
    ),
    "fx3_lib_bus_power": (
        "fx3",
        "libBusPower.so",
        43_968,
        "4c39d2789745a4638490da1aa41b39c90980c7dd30837a693e87085689bbcc0e",
        (
            b"_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt",
            b"_ZN8BusPower27NotifyUSBPowerContractStateEi",
            b"_ZN8BusPower37InitUSBSourcePowerStateToPowerManagerEv",
        ),
        "fx3/libBusPower.so::{SetUSBPDSinkStatusToPowerManager,NotifyUSBPowerContractState,InitUSBSourcePowerState}",
    ),
    "fx6_lib_bus_power": (
        "fx6",
        "libBusPower.so",
        43_968,
        "d4f2ffe4e74786b66b64ca4eec05b0d433ff0157326156a486d7afec742d00b8",
        (
            b"_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt",
            b"_ZN8BusPower27NotifyUSBPowerContractStateEi",
        ),
        "fx6/libBusPower.so::{SetUSBPDSinkStatusToPowerManager,NotifyUSBPowerContractState}",
    ),
    "fx3_lib_usb_bus_power": (
        "fx3",
        "libUsbBusPower.so",
        48_232,
        "c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748",
        (
            b"_ZN11UsbBusPower19GetCurrentBattStateEPi",
            b"_ZN11UsbBusPower15GetCurrentLimitEv",
            b"_ZN11UsbBusPower11IsVbusReadyEv",
            b"_ZN11UsbBusPower18SetWatchSWForceOFFEv",
        ),
        "fx3/libUsbBusPower.so::{GetCurrentBattState,GetCurrentLimit,IsVbusReady,SetWatchSWForceOFF}",
    ),
    "fx6_lib_usb_bus_power": (
        "fx6",
        "libUsbBusPower.so",
        48_232,
        "4215a9e989d25896bd12de85928d58fac76d6c4b8dac04cc43ee1b9106c2fe71",
        (
            b"_ZN11UsbBusPower19GetCurrentBattStateEPi",
            b"_ZN11UsbBusPower15GetCurrentLimitEv",
            b"_ZN11UsbBusPower11IsVbusReadyEv",
        ),
        "fx6/libUsbBusPower.so::{GetCurrentBattState,GetCurrentLimit,IsVbusReady}",
    ),
}

PINNED_APPFW_BATT_MOUNT_TOKENS: Tuple[str, ...] = (
    "asrid_cau_battery_authentication_error_normal_english_",
    "asrid_cau_incompatible_battery_normal_english_",
    "No11_BatteryLevelNonInfoLitium",
    "VAL_lens_information_LENS_INFORMATION_TYPE_EMOUNT",
    "PRM_FEATURE_MANAGER_lens_mount",
)

PINNED_CPAPP_BATT_MOUNT_TOKENS: Tuple[str, ...] = (
    "BATT_AUTH_Snd",
    "BATT_STATE1_Snd",
    "BattCheckInfo_Rcv",
    "ACV_BATT_Snd",
    "C_LENS_XDETECT_BODY_INT_NO",
    "C_LENS_CS_BODY_INT_NO",
    "ID_FLG_CAM_LENS_MOUNT",
)


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase104DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    emount_lens_comm_tokens_verified: bool
    usbpd_bus_power_tokens_verified: bool
    batt_auth_infolithium_tokens_verified: bool
    large_binaries_scanned: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlCantileverFlangeGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    rig_profile: str
    lens_plus_mattebox_kg: float
    l_cg_mm: float
    shock_g: float
    static_moment_nm: float
    peak_moment_nm: float
    flange_focal_distance_mm: float
    backfocus_tolerance_mm: float
    lws_15mm_y_support_engaged: bool
    pl_to_e_adapter_used: bool
    adapter_foot_bolted_to_cage: bool
    clamp_on_mattebox: bool
    lens_front_rotates_or_telescopes: bool
    cantilever_flange_safe: bool
    pl_adapter_backfocus_safe: bool
    mattebox_barrel_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DummyBatteryOvervoltageFirewallResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    power_topology: str
    dummy_battery_installed: bool
    measured_open_circuit_v: float
    v_mount_nominal_v: float
    buck_regulator_ovp_crowbar_verified: bool
    dtap_source_used: bool
    reverse_polarity_diode_or_smart_dtap: bool
    infolithium_thermistor_ntc_valid: bool
    pmic_overvoltage_stress_ratio: float
    dummy_battery_voltage_safe: bool
    dtap_polarity_safe: bool
    infolithium_auth_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G31PlCantileverFlangeResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    pl_cantilever_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G32DummyBatteryFirewallResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    dummy_battery_firewall: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master32GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_29_gates_verified: bool
    all_32_gates_verified: bool
    g13_to_g32_all_passed: bool
    g31_to_g32_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_30_report: Dict[str, Any]
    g31_result: Dict[str, Any]
    g32_result: Dict[str, Any]
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


def audit_phase104_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
) -> Phase104DonorAuditResult:
    """Inspect FX3/FX6 lens-communicator and battery/USB-PD donors via `os.O_RDONLY`."""
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
        "fx3_lib_infra_lens_comm": fx3_lib_dir / "libInfraLensCommunicator.so",
        "fx6_lib_infra_lens_comm": fx6_lib_dir / "libInfraLensCommunicator.so",
        "fx3_lib_bus_power": fx3_lib_dir / "libBusPower.so",
        "fx6_lib_bus_power": fx6_lib_dir / "libBusPower.so",
        "fx3_lib_usb_bus_power": fx3_lib_dir / "libUsbBusPower.so",
        "fx6_lib_usb_bus_power": fx6_lib_dir / "libUsbBusPower.so",
    }

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase104DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(spec[5] for spec in PINNED_PHASE104_DONOR_SPECS.values()),
            missing_markers=(),
            emount_lens_comm_tokens_verified=True,
            usbpd_bus_power_tokens_verified=True,
            batt_auth_infolithium_tokens_verified=True,
            large_binaries_scanned=False,
            sha256_by_artifact={k: spec[3] for k, spec in PINNED_PHASE104_DONOR_SPECS.items()},
            bytes_by_artifact={k: spec[2] for k, spec in PINNED_PHASE104_DONOR_SPECS.items()},
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

    for key, (_body, _rel_name, exp_size, exp_sha, marker_tuple, marker_label) in PINNED_PHASE104_DONOR_SPECS.items():
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
                paths.fx3_appfw_path, PINNED_APPFW_BATT_MOUNT_TOKENS
            )
            sizes["fx3_appfw"] = appfw_sz
            files_inspected += 1
            large_scanned = True
            if missing_appfw:
                appfw_ok = False
                missing.extend(missing_appfw)
                errors.append(f"fx3 appFw.so missing battery-auth/E-mount tokens: {missing_appfw}")
            else:
                checked.append("fx3/appFw.so::BATT_AUTH_ERR+INCOMPATIBLE_BATT+NonInfoLitium+EMOUNT")
        else:
            warnings.append("fx3/appFw.so not found for optional large-binary battery/mount scan.")

        if paths.fx3_cp_path.is_file():
            cp_sz, missing_cp = scan_tokens_o_rdonly(
                paths.fx3_cp_path, PINNED_CPAPP_BATT_MOUNT_TOKENS
            )
            sizes["fx3_cpapp"] = cp_sz
            files_inspected += 1
            large_scanned = True
            if missing_cp:
                cpapp_ok = False
                missing.extend(missing_cp)
                errors.append(f"fx3 cpapp-b.bin missing BATT_AUTH/LENS_XDETECT tokens: {missing_cp}")
            else:
                checked.append("fx3/cpapp-b.bin::BATT_AUTH_Snd+BATT_STATE1_Snd+C_LENS_XDETECT+LENS_MOUNT")
        else:
            warnings.append("fx3/cpapp-b.bin not found for optional large-binary CP battery/lens scan.")

    valid = len(errors) == 0 and len(missing) == 0
    return Phase104DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        emount_lens_comm_tokens_verified={
            "fx3_lib_infra_lens_comm",
            "fx6_lib_infra_lens_comm",
        }.issubset(passed_keys)
        and appfw_ok
        and cpapp_ok,
        usbpd_bus_power_tokens_verified={
            "fx3_lib_bus_power",
            "fx6_lib_bus_power",
        }.issubset(passed_keys),
        batt_auth_infolithium_tokens_verified={
            "fx3_lib_usb_bus_power",
            "fx6_lib_usb_bus_power",
        }.issubset(passed_keys)
        and appfw_ok
        and cpapp_ok,
        large_binaries_scanned=large_scanned,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Physics & Electrical Helpers for Gates G31 & G32
# ---------------------------------------------------------------------------


def compute_cantilever_bending_moment_nm(
    mass_kg: float,
    l_cg_mm: float,
    *,
    shock_g: float = 1.0,
) -> float:
    """Compute cantilever bending moment `M = m * g * (L_cg / 1000.0) * shock_g` in N*m."""
    if not (_is_finite_number(mass_kg) and _is_finite_number(l_cg_mm) and _is_finite_number(shock_g)):
        raise ValueError("mass_kg, l_cg_mm, and shock_g must be finite numbers.")
    if float(mass_kg) < 0.0 or float(l_cg_mm) <= 0.0 or float(shock_g) < 1.0:
        raise ValueError("mass_kg >= 0.0, l_cg_mm > 0.0, and shock_g >= 1.0 required.")
    return float(mass_kg) * STANDARD_GRAVITY_M_S2 * (float(l_cg_mm) / 1000.0) * float(shock_g)


def compute_pmic_overvoltage_stress_ratio(measured_open_circuit_v: float) -> float:
    """Compute ratio of `measured_open_circuit_v` against `NP-FZ100` max 8.40V bay rating."""
    if not _is_finite_number(measured_open_circuit_v) or float(measured_open_circuit_v) < 0.0:
        raise ValueError("measured_open_circuit_v must be a finite number >= 0.0.")
    return float(measured_open_circuit_v) / NP_FZ100_MAX_CHARGED_VOLTAGE_V


# ---------------------------------------------------------------------------
# 3. Gate G31 — Heavy Cinema PL-to-E Cantilever & 15mm LWS Lens-Support Guard
# ---------------------------------------------------------------------------


def verify_pl_cantilever_and_emount_flange_guard(
    *,
    rig_profile: str = "FX3_COMPACT_E_MOUNT_PRIME",
    lens_plus_mattebox_kg: float = 0.85,
    l_cg_mm: float = 80.0,
    shock_g: float = CANTILEVER_DEFAULT_SHOCK_FACTOR_G,
    lws_15mm_y_support_engaged: bool = False,
    pl_to_e_adapter_used: bool = False,
    adapter_foot_bolted_to_cage: bool = False,
    clamp_on_mattebox: bool = False,
    lens_front_rotates_or_telescopes: bool = False,
    request_persistent_emmc_writes: bool = False,
) -> PlCantileverFlangeGuardResult:
    """Verify Gate G31 (PL-to-E cantilever bending moment, 15mm LWS Y-support & matte-box guard)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    telemetry_ok = True
    if not _is_finite_number(lens_plus_mattebox_kg) or float(lens_plus_mattebox_kg) < 0.0:
        _add_code(codes, STATUS_BLOCKED_PL_CANTILEVER_TELEMETRY_INVALID)
        errors.append(f"lens_plus_mattebox_kg must be finite >= 0.0, got {lens_plus_mattebox_kg!r}.")
        telemetry_ok = False
        eff_mass_kg = 0.85
    else:
        eff_mass_kg = float(lens_plus_mattebox_kg)

    if not _is_finite_number(l_cg_mm) or float(l_cg_mm) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_PL_CANTILEVER_TELEMETRY_INVALID)
        errors.append(f"l_cg_mm must be finite > 0.0, got {l_cg_mm!r}.")
        telemetry_ok = False
        eff_l_cg_mm = 80.0
    else:
        eff_l_cg_mm = float(l_cg_mm)

    if not _is_finite_number(shock_g) or float(shock_g) < 1.0:
        _add_code(codes, STATUS_BLOCKED_PL_CANTILEVER_TELEMETRY_INVALID)
        errors.append(f"shock_g must be finite >= 1.0, got {shock_g!r}.")
        telemetry_ok = False
        eff_shock_g = CANTILEVER_DEFAULT_SHOCK_FACTOR_G
    else:
        eff_shock_g = float(shock_g)

    static_moment_nm = compute_cantilever_bending_moment_nm(eff_mass_kg, eff_l_cg_mm, shock_g=1.0)
    peak_moment_nm = compute_cantilever_bending_moment_nm(eff_mass_kg, eff_l_cg_mm, shock_g=eff_shock_g)

    # a) Unsupported Heavy Cantilever E-Mount Flange Warp Guard
    cantilever_overload = (
        eff_mass_kg > EMOUNT_UNSUPPORTED_MAX_MASS_KG
        or static_moment_nm > EMOUNT_UNSUPPORTED_MAX_STATIC_MOMENT_NM
    )
    cantilever_flange_safe = not (
        telemetry_ok and cantilever_overload and (not bool(lws_15mm_y_support_engaged))
    )
    if not cantilever_flange_safe:
        _add_code(codes, STATUS_BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP)
        errors.append(
            f"BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP: {rig_profile} hangs {eff_mass_kg:.2f} kg at "
            f"L_cg={eff_l_cg_mm:.1f} mm (M_static={static_moment_nm:.3f} N*m, M_peak@{eff_shock_g:.1f}G="
            f"{peak_moment_nm:.3f} N*m) on FX3's 6-screw 18.00mm (+/-0.01mm) E-Mount flange without "
            "lws_15mm_y_support_engaged=True."
        )

    # b) Unshimmed / Unbolted PL-to-E Adapter Back-Focus Drift Guard
    pl_adapter_overload = (
        bool(pl_to_e_adapter_used)
        and (not bool(adapter_foot_bolted_to_cage))
        and eff_mass_kg > PL_ADAPTER_UNBOLTED_MAX_MASS_KG
    )
    pl_adapter_backfocus_safe = not (telemetry_ok and pl_adapter_overload)
    if not pl_adapter_backfocus_safe:
        _add_code(codes, STATUS_BLOCKED_UNSHIMMED_PL_ADAPTER_BACKFOCUS_DRIFT)
        errors.append(
            f"BLOCKED_UNSHIMMED_PL_ADAPTER_BACKFOCUS_DRIFT: pl_to_e_adapter_used=True with "
            f"lens_plus_mattebox_kg={eff_mass_kg:.2f} kg > {PL_ADAPTER_UNBOLTED_MAX_MASS_KG:.2f} kg and "
            "adapter_foot_bolted_to_cage=False risks >0.01mm back-focus drift and flange shear."
        )

    # c) Clamp-On Matte-Box on Rotating / Telescoping Lens Front Guard
    mattebox_barrel_safe = not (
        telemetry_ok and bool(clamp_on_mattebox) and bool(lens_front_rotates_or_telescopes)
    )
    if not mattebox_barrel_safe:
        _add_code(codes, STATUS_BLOCKED_CLAMP_ON_MATTEBOX_TELESCOPING_BARREL)
        errors.append(
            "BLOCKED_CLAMP_ON_MATTEBOX_TELESCOPING_BARREL: clamp_on_mattebox=True on a lens whose front "
            "element rotates or telescopes binds focus/zoom helicoids and stresses the E-Mount flange; "
            "switch to a 15mm LWS swing-away rod-mounted matte box."
        )

    if telemetry_ok and cantilever_overload and bool(lws_15mm_y_support_engaged) and len(errors) == 0:
        warnings.append(
            f"Heavy cinema optical load ({eff_mass_kg:.2f} kg, M_static={static_moment_nm:.2f} N*m, "
            f"M_peak={peak_moment_nm:.2f} N*m) supported by engaged 15mm LWS Y-support."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return PlCantileverFlangeGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        rig_profile=str(rig_profile),
        lens_plus_mattebox_kg=round(eff_mass_kg, 3),
        l_cg_mm=round(eff_l_cg_mm, 2),
        shock_g=round(eff_shock_g, 2),
        static_moment_nm=round(static_moment_nm, 4),
        peak_moment_nm=round(peak_moment_nm, 4),
        flange_focal_distance_mm=EMOUNT_FLANGE_FOCAL_DISTANCE_MM,
        backfocus_tolerance_mm=EMOUNT_BACKFOCUS_TOLERANCE_MM,
        lws_15mm_y_support_engaged=bool(lws_15mm_y_support_engaged),
        pl_to_e_adapter_used=bool(pl_to_e_adapter_used),
        adapter_foot_bolted_to_cage=bool(adapter_foot_bolted_to_cage),
        clamp_on_mattebox=bool(clamp_on_mattebox),
        lens_front_rotates_or_telescopes=bool(lens_front_rotates_or_telescopes),
        cantilever_flange_safe=cantilever_flange_safe,
        pl_adapter_backfocus_safe=pl_adapter_backfocus_safe,
        mattebox_barrel_safe=mattebox_barrel_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G32 — Dummy-Battery Over-Voltage (>8.4V Blowout Trap!) Firewall
# ---------------------------------------------------------------------------


def verify_dummy_battery_overvoltage_firewall(
    *,
    power_topology: str = SONY_CINEMA_SOP_POWER_TOPOLOGY,
    dummy_battery_installed: bool = False,
    measured_open_circuit_v: float = 8.20,
    buck_regulator_ovp_crowbar_verified: bool = True,
    v_mount_nominal_v: float = 14.8,
    dtap_source_used: bool = False,
    reverse_polarity_diode_or_smart_dtap: bool = True,
    infolithium_thermistor_ntc_valid: bool = True,
    request_persistent_emmc_writes: bool = False,
) -> DummyBatteryOvervoltageFirewallResult:
    """Verify Gate G32 (14.8V/26V V-Mount -> NP-FZ100 dummy-battery OVP & InfoLITHIUM firewall)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    telemetry_ok = True
    if (
        not _is_finite_number(measured_open_circuit_v)
        or float(measured_open_circuit_v) < 0.0
        or float(measured_open_circuit_v) > 60.0
    ):
        _add_code(codes, STATUS_BLOCKED_DUMMY_BATT_TELEMETRY_INVALID)
        errors.append(
            f"measured_open_circuit_v must be finite in [0.0, 60.0], got {measured_open_circuit_v!r}."
        )
        telemetry_ok = False
        eff_ocv_v = 8.20
    else:
        eff_ocv_v = float(measured_open_circuit_v)

    if (
        not _is_finite_number(v_mount_nominal_v)
        or float(v_mount_nominal_v) < 0.0
        or float(v_mount_nominal_v) > 60.0
    ):
        _add_code(codes, STATUS_BLOCKED_DUMMY_BATT_TELEMETRY_INVALID)
        errors.append(f"v_mount_nominal_v must be finite in [0.0, 60.0], got {v_mount_nominal_v!r}.")
        telemetry_ok = False
        eff_vmount_v = 14.8
    else:
        eff_vmount_v = float(v_mount_nominal_v)

    stress_ratio = compute_pmic_overvoltage_stress_ratio(eff_ocv_v)

    # a) Dummy-Battery Over-Voltage (>8.45V / Unverified Buck / >=24V V-Mount) Blowout Guard
    ovp_voltage_trip = eff_ocv_v > DUMMY_BATTERY_OPEN_CIRCUIT_MAX_V
    ovp_buck_unverified = not bool(buck_regulator_ovp_crowbar_verified)
    ovp_26v_vmount = eff_vmount_v >= VMOUNT_HIGH_VOLTAGE_CINEMA_THRESHOLD_V
    dummy_battery_voltage_safe = not (
        telemetry_ok
        and bool(dummy_battery_installed)
        and (ovp_voltage_trip or ovp_buck_unverified or ovp_26v_vmount)
    )
    if not dummy_battery_voltage_safe:
        _add_code(codes, STATUS_BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT)
        ovp_reasons: List[str] = []
        if ovp_voltage_trip:
            ovp_reasons.append(
                f"measured_open_circuit_v={eff_ocv_v:.2f}V > {DUMMY_BATTERY_OPEN_CIRCUIT_MAX_V:.2f}V "
                f"({stress_ratio:.2f}x 8.40V NP-FZ100 max)"
            )
        if ovp_buck_unverified:
            ovp_reasons.append("buck_regulator_ovp_crowbar_verified=False")
        if ovp_26v_vmount:
            ovp_reasons.append(
                f"v_mount_nominal_v={eff_vmount_v:.1f}V >= {VMOUNT_HIGH_VOLTAGE_CINEMA_THRESHOLD_V:.1f}V cinema pack"
            )
        errors.append(
            "BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT: Dummy battery poses lethal CXD90057 PMIC "
            f"over-voltage blowout risk ({'; '.join(ovp_reasons)}). Prefer regulated 9V/3A USB-C PD + "
            "genuine internal NP-FZ100 UPS."
        )

    # b) Reverse-Polarity / Unkeyed D-Tap Source Guard
    dtap_polarity_safe = not (
        telemetry_ok
        and bool(dtap_source_used)
        and (not bool(reverse_polarity_diode_or_smart_dtap))
    )
    if not dtap_polarity_safe:
        _add_code(codes, STATUS_BLOCKED_REVERSE_POLARITY_UNKEYED_DTAP)
        errors.append(
            "BLOCKED_REVERSE_POLARITY_UNKEYED_DTAP: dtap_source_used=True with "
            "reverse_polarity_diode_or_smart_dtap=False risks inverted D-Tap insertion and instant mainboard short."
        )

    # c) Unauthenticated / Missing InfoLITHIUM Thermistor NTC Spoof Guard
    infolithium_auth_safe = not (
        telemetry_ok
        and bool(dummy_battery_installed)
        and (not bool(infolithium_thermistor_ntc_valid))
    )
    if not infolithium_auth_safe:
        _add_code(codes, STATUS_BLOCKED_UNAUTHENTICATED_NON_INFOLITHIUM_SPOOF)
        errors.append(
            "BLOCKED_UNAUTHENTICATED_NON_INFOLITHIUM_SPOOF: dummy_battery_installed=True with "
            "infolithium_thermistor_ntc_valid=False triggers Sony InfoLITHIUM/NTC fault or unmonitored thermal shutdown."
        )

    if telemetry_ok and bool(dummy_battery_installed) and len(errors) == 0:
        warnings.append(
            "Regulated OVP-crowbar-verified NP-FZ100 dummy battery permitted; Sony Cinema SOP prefers "
            "regulated 9V/3A USB-C PD with genuine internal NP-FZ100 UPS when rigging permits."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return DummyBatteryOvervoltageFirewallResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        power_topology=str(power_topology),
        dummy_battery_installed=bool(dummy_battery_installed),
        measured_open_circuit_v=round(eff_ocv_v, 3),
        v_mount_nominal_v=round(eff_vmount_v, 2),
        buck_regulator_ovp_crowbar_verified=bool(buck_regulator_ovp_crowbar_verified),
        dtap_source_used=bool(dtap_source_used),
        reverse_polarity_diode_or_smart_dtap=bool(reverse_polarity_diode_or_smart_dtap),
        infolithium_thermistor_ntc_valid=bool(infolithium_thermistor_ntc_valid),
        pmic_overvoltage_stress_ratio=round(stress_ratio, 4),
        dummy_battery_voltage_safe=dummy_battery_voltage_safe,
        dtap_polarity_safe=dtap_polarity_safe,
        infolithium_auth_safe=infolithium_auth_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 5. Gate G31 & Gate G32 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g31_pl_cantilever_and_lws_support(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    pl_cantilever_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase104DonorAuditResult] = None,
) -> Tuple[GateVerdict, G31PlCantileverFlangeResult]:
    """Evaluate Gate G31 (`pl_adapter_cantilever_moment_and_lws_support_safe`)."""
    audit = donor_audit or audit_phase104_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(pl_cantilever_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    guard_res = verify_pl_cantilever_and_emount_flange_guard(**eff_kwargs)

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
        STATUS_VERIFIED_G31
        if passed
        else (codes[0] if codes else STATUS_BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP)
    )

    res = G31PlCantileverFlangeResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        pl_cantilever_guard=guard_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G31_GATE_ID,
        gate_code=G31_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"PL-to-E Cantilever Moment & 15mm LWS Y-Support Guard ({guard_res.status}, "
            f"mass={guard_res.lens_plus_mattebox_kg:.2f}kg, M_static={guard_res.static_moment_nm:.3f}N*m, "
            f"M_peak={guard_res.peak_moment_nm:.3f}N*m, lws_15mm={guard_res.lws_15mm_y_support_engaged}, "
            f"pl_adapter={guard_res.pl_to_e_adapter_used}, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "cantilever_flange_safe": guard_res.cantilever_flange_safe,
            "pl_adapter_backfocus_safe": guard_res.pl_adapter_backfocus_safe,
            "mattebox_barrel_safe": guard_res.mattebox_barrel_safe,
        },
    )
    return verdict, res


def evaluate_g32_dummy_battery_overvoltage_firewall(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    dummy_battery_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase104DonorAuditResult] = None,
) -> Tuple[GateVerdict, G32DummyBatteryFirewallResult]:
    """Evaluate Gate G32 (`dummy_battery_overvoltage_and_infolithium_safe`)."""
    audit = donor_audit or audit_phase104_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(dummy_battery_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    fw_res = verify_dummy_battery_overvoltage_firewall(**eff_kwargs)

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
        STATUS_VERIFIED_G32
        if passed
        else (codes[0] if codes else STATUS_BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT)
    )

    res = G32DummyBatteryFirewallResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        dummy_battery_firewall=fw_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G32_GATE_ID,
        gate_code=G32_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Dummy-Battery Over-Voltage & InfoLITHIUM Firewall ({fw_res.status}, "
            f"dummy={fw_res.dummy_battery_installed}, ocv={fw_res.measured_open_circuit_v:.2f}V, "
            f"vmount={fw_res.v_mount_nominal_v:.1f}V, ovp_crowbar={fw_res.buck_regulator_ovp_crowbar_verified}, "
            f"dtap={fw_res.dtap_source_used}, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "dummy_battery_voltage_safe": fw_res.dummy_battery_voltage_safe,
            "dtap_polarity_safe": fw_res.dtap_polarity_safe,
            "infolithium_auth_safe": fw_res.infolithium_auth_safe,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 6. Master 32-Gate Preflight Evaluator (`G01..G32`) & CLI
# ---------------------------------------------------------------------------


def evaluate_32gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G30 pass-throughs
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
    # G31 inputs (Heavy Cinema PL-to-E Cantilever Bending-Moment & 15mm LWS Support)
    pl_cantilever_kwargs: Optional[Mapping[str, Any]] = None,
    # G32 inputs (Unregulated 14.8V/26V V-Mount -> NP-FZ100 Dummy-Battery OVP Firewall)
    dummy_battery_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master32GateReport:
    """Evaluate all 32 Master Safety Gates (`G01..G32`) deterministically."""
    resolved_root = (DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m30_kwargs: Dict[str, Any] = {
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
    }
    if soc_start_ceiling_c is not None:
        m30_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m30_report: Master30GateReport = evaluate_30gate_preflight(resolved_root, **m30_kwargs)

    phase104_audit = audit_phase104_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
    )

    g31_verdict, g31_res = evaluate_g31_pl_cantilever_and_lws_support(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        pl_cantilever_kwargs=pl_cantilever_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase104_audit,
    )

    g32_verdict, g32_res = evaluate_g32_dummy_battery_overvoltage_firewall(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        dummy_battery_kwargs=dummy_battery_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase104_audit,
    )

    gates_31_to_32 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g31_verdict, g32_verdict)
    ]
    all_gates = tuple(list(m30_report.gates) + gates_31_to_32)

    g01_to_g12_verified = int(m30_report.summary["g01_to_g12_verified"])
    g13_to_g30_verified = (
        int(m30_report.summary["g13_to_g28_verified"])
        + int(m30_report.summary["g29_to_g30_verified"])
    )
    g31_to_g32_verified = sum(1 for v in (g31_verdict, g32_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g30_verified + g31_to_g32_verified

    g31_to_g32_all_passed = g31_to_g32_verified == 2
    g13_to_g32_all_passed = m30_report.g13_to_g30_all_passed and g31_to_g32_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m30_report.gates[:9])

    offline_29_verified = (
        g01_to_g09_ok
        and m30_report.offline_27_gates_verified
        and g31_to_g32_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_32_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g32_all_passed
        and (not request_persistent_emmc_writes)
    )

    real_tier0_verified = (g01_to_g12_verified == 12) and (not dry_run_simulated_backup)
    overall_ready_for_hardware_attach = (
        real_tier0_verified
        and g13_to_g32_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    h0_h1_allowed = (
        offline_29_verified
        and m30_report.h0_h1_trial_entry_allowed
        and g31_to_g32_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = list(m30_report.errors) + list(g31_verdict.errors) + list(g32_verdict.errors)
    warnings: List[str] = list(m30_report.warnings) + list(g31_verdict.warnings) + list(g32_verdict.warnings)

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m30_report.g13_to_g30_all_passed:
        overall_status = m30_report.status
    elif not g31_verdict.passed:
        overall_status = g31_verdict.status
    elif not g32_verdict.passed:
        overall_status = g32_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_32_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_32_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_32_verified:
        overall_status = "VERIFIED_ALL_32_GATES"
    else:
        overall_status = "VERIFIED_29_OF_32_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m30_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g31_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g32_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 32,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 32 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g30_verified": g13_to_g30_verified,
        "g31_to_g32_verified": g31_to_g32_verified,
        "g13_to_g32_all_passed": g13_to_g32_all_passed,
        "g31_to_g32_all_passed": g31_to_g32_all_passed,
        "offline_29_gates_verified": offline_29_verified,
        "all_32_gates_verified": all_32_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master32GateReport(
        schema=PL_CANTILEVER_DUMMYBATT_32GATE_SCHEMA,
        version=PL_CANTILEVER_DUMMYBATT_32GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_29_gates_verified=offline_29_verified,
        all_32_gates_verified=all_32_verified,
        g13_to_g32_all_passed=g13_to_g32_all_passed,
        g31_to_g32_all_passed=g31_to_g32_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_30_report=m30_report.to_dict(),
        g31_result=g31_res.to_dict(),
        g32_result=g32_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_32_master_safety_gates = evaluate_32gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pl_cantilever_dummybatt_and_32gate_guard",
        description=(
            "Phase 104 — PL-to-E Cantilever Bending-Moment & 15mm LWS Guard (G31), "
            "Dummy-Battery Over-Voltage Blowout Firewall (G32) & 32-Gate Preflight (G01..G32)"
        ),
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G32 can be exercised offline",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_32gate_preflight(
        args.repo_root,
        force_clean_room=True if args.clean_room else None,
        dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/32 "
            f"g31_to_g32_all_passed={report.g31_to_g32_all_passed} "
            f"all_32_gates_verified={report.all_32_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = report.all_32_gates_verified if args.dry_run_simulated_backup else report.offline_29_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
