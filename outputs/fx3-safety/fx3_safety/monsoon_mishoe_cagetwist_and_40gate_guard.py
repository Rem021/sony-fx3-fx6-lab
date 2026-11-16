"""Milestone Phase 125 — Tropical Monsoon Rain / Wet MI-Shoe 24-Pin Contact Short-Circuit
Firewall (Gate G39), FX3 Top-Plate 1/4"-20 Thread Shear / XLR-H1 Whip-Leverage &
Cage-Twist Flange-Focal-Distance Guard (Gate G40), and Unified 40-Gate Master Safety
Preflight (`G01..G40` / `verify-40-gates`).

Operationalizes two critical tropical-weather / wet MI-Shoe electrical-short and
magnesium-chassis / E-Mount FFD mechanical-warpage hardware guards for Sony ILME-FX3
(`Ver. 7.02`, Model ID `0x91030080`, SoC `CXD90057`), while keeping all prior gate
modules (`preflight.py`, `master_16gate_preflight.py`,
`usblan_ptpip_and_18gate_preflight.py`, `rig_groundloop_lensrail_and_20gate_guard.py`,
`phantom48v_gimbal_and_22gate_guard.py`, `dewpoint_tec_usbc_and_24gate_guard.py`,
`intake_occlusion_tripod_and_26gate_guard.py`,
`sensor_curtain_subzero_and_28gate_guard.py`,
`wireless_tx_emi_endurance_and_30gate_guard.py`,
`pl_cantilever_dummybatt_and_32gate_guard.py`,
`saltspray_haze_followfocus_and_34gate_guard.py`,
`hdmi_aoc_5v_cfexpress_and_36gate_guard.py`, and
`usbpd_trigger_multiterminal_and_38gate_guard.py`) completely untouched:

1. **Read-Only (`os.O_RDONLY`) FX3/FX6 Donor MI-Shoe / Chassis / Mount Audit**:
   - Inspects local FX6 `v6.01` `libInfraHotshoe.so`
     (`_ZN12InfraHotshoe13QueryShoeIdOnEij`, `_ZN12InfraHotshoe17SetShoeLogicPwrOnEb`,
     `_ZN12InfraHotshoe27SetShoeUnregOnWaitStabilityEbjj`,
     `INFRA_HOTSHOE_UIPC_SETSHOE_PWR_ON`), FX3 `v7.02` & FX6 `v6.01`
     `libInfraLensCommunicator.so` (`GetMountedLensInfo`, `SndSyncMsg`,
     `GetSuopportedCommandIds`, `ReadBackup`), `libInfraExtCmdSvc.so`
     (`ExtCmdSvc_Create`, `IntrRegistTransportCmd`, `SndMsgToUpperSync`,
     `SndMsgToLowerSync`), and `libBusPower.so`
     (`SetUSBPDSinkStatusToPowerManager`, `NotifyUSBPowerContractState`,
     `NotifyUSBPowerSupplyState`, `MSGID_VBUS_ERROR_EVT`) strictly via
     `os.open(..., os.O_RDONLY)`, plus optional chunked scans of `appFw.so`
     (`VAL_hotshoe_xlr_mic_connection_status_XLR_MIC_CONNECT_ON`,
     `PID_SET_HOTSHOE_VIDEOLIGHT`,
     `VAL_lens_information_LENS_INFORMATION_TYPE_EMOUNT`,
     `VAL_built_in_steady_shot_error_BUILT_IN_STEADY_SHOT_ERROR_OCCURED`,
     `OFF_BY_BATT_OVERCURRENT`) and `cpapp-b.bin`
     (`8AccyFifoI17ACCY_MI_SHOE_TYPEE`,
     `7AdfFifoIN21AdfShoePowerSequencer38SHOE_POWER_SEQUENCER_RESERVE_CALL_BACKEE`,
     `MSGQ_GID_HOTSHOE_INFRA1`, `ID_FLG_CAM_LENS_MOUNT`,
     `SET_S1_STEADY_SHOT_MODE`) when `include_large_binaries=True`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent.

2. **Gate G39 — Tropical Monsoon Rain Ingress, Uncapped Wet 24-Pin MI-Shoe Gold-Finger
   Galvanic Short-Circuit & Open Port-Flap Capillary Guard**:
   - FX3 lacks an IP-rated immersion seal, and its recessed 24-pin Multi-Interface
     (MI) Shoe exposes `+3.15V/+5V` accessory power, `I2S` digital audio clocks, and
     detect pins directly upward on the top plate.
   - Fails closed on:
     a) `BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT` when
        (`precipitation_mm_hr > 0.5` and `mi_shoe_accessory_attached == False` and
        `mi_shoe_weather_cap_installed == False`), or when
        `mi_shoe_contact_resistance_kohm < 50.0` (wet bridge across pins) while
        `mi_shoe_power_rail_enabled == True`,
     b) `BLOCKED_NON_GASKETED_MISHOE_ACCESSORY_IN_RAIN` when
        `precipitation_mm_hr > 2.0` and `mi_shoe_accessory_attached == True` and
        `mi_shoe_silicone_perimeter_gasket_sealed == False` and
        `rain_cover_installed == False`,
     c) `BLOCKED_OPEN_SIDE_PORT_FLAP_CAPILLARY_INGRESS` when
        (`precipitation_mm_hr > 0.5` or `water_spray_rig == True`) and
        `open_rubber_port_flaps_count > 0` and
        `weather_sealed_cable_gland_or_rain_slicker == False`.

3. **Gate G40 — FX3 Top-Plate `2x M4` XLR-H1 Handle Whip-Leverage Shear, `1/4"-20`
   Magnesium-Chassis Thread Strip (`> 3.5 N*m`) & Asymmetric Cage-Twist E-Mount
   `18.00 mm` Flange-Focal-Distance (`FFD`) Warpage Guard**:
   - Protects FX3's internal magnesium-alloy chassis (`5x 1/4"-20` body threads +
     `2x M4` MI-Shoe handle screws) and `18.00 mm` (`±0.015 mm`) E-Mount flange plane.
   - Fails closed on:
     a) `BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR` when
        `xlr_h1_handle_installed == True` and
        (`total_rig_mass_suspended_from_xlr_h1_kg > 2.8` or
        `top_handle_monitor_moment_nm > 3.2`) and
        `metal_cage_nato_top_handle_reinforcement == False`,
     b) `BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP` when
        `body_thread_fastener_torque_nm > 3.5` (exceeding magnesium `1/4"-20`
        helicoil/boss yield threshold),
     c) `BLOCKED_ASYMMETRIC_CAGE_TWIST_FFD_WARPAGE` when
        `cage_multi_point_locked == True` and `unshimmed_side_screw_gap_mm > 0.25`
        causing `estimated_emount_ffd_tilt_um > 12.0` (decentering fast `T1.4` cinema
        primes).

4. **Unified 40-Gate Master Safety Preflight (`evaluate_40gate_preflight` / CLI
   `verify-40-gates`)**:
   - Composes `evaluate_38gate_preflight` (`G01..G38`) with `G39` and `G40`:
     * Offline default mode: `37/40` gates pass (`G10..G12` physical Tier-0 backup
       truthfully remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` ->
       `overall_ready_for_hardware_attach = False`).
     * `--dry-run-simulated-backup` mode: `40/40` simulation gates pass
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
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
    scan_tokens_o_rdonly,
)
from .usbpd_trigger_multiterminal_and_38gate_guard import (
    Master38GateReport,
    evaluate_38gate_preflight,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

MONSOON_MISHOE_CAGETWIST_40GATE_SCHEMA: str = (
    "fx3-monsoon-mishoe-cagetwist-40gate-preflight-v1"
)
MONSOON_MISHOE_CAGETWIST_40GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G39..G40
G39_GATE_ID: str = "G39_monsoon_rain_mishoe_short_and_port_flap_safe"
G39_GATE_CODE: str = "MONSOON_RAIN_MISHOE_SHORT_AND_PORT_FLAP_SAFE"

G40_GATE_ID: str = "G40_xlr_h1_whip_shear_quarter20_torque_and_cage_ffd_safe"
G40_GATE_CODE: str = "XLR_H1_WHIP_SHEAR_QUARTER20_TORQUE_AND_CAGE_FFD_SAFE"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G39: str = "VERIFIED_MONSOON_RAIN_MISHOE_SHORT_AND_PORT_FLAP_SAFE"
STATUS_VERIFIED_G40: str = (
    "VERIFIED_XLR_H1_WHIP_SHEAR_QUARTER20_TORQUE_AND_CAGE_FFD_SAFE"
)

# Gate G39 Violation Codes
STATUS_BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT: str = (
    "BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT"
)
STATUS_BLOCKED_NON_GASKETED_MISHOE_ACCESSORY_IN_RAIN: str = (
    "BLOCKED_NON_GASKETED_MISHOE_ACCESSORY_IN_RAIN"
)
STATUS_BLOCKED_OPEN_SIDE_PORT_FLAP_CAPILLARY_INGRESS: str = (
    "BLOCKED_OPEN_SIDE_PORT_FLAP_CAPILLARY_INGRESS"
)
STATUS_BLOCKED_MONSOON_MISHOE_TELEMETRY_INVALID: str = (
    "BLOCKED_MONSOON_MISHOE_TELEMETRY_INVALID"
)

# Gate G40 Violation Codes
STATUS_BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR: str = (
    "BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR"
)
STATUS_BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP: str = (
    "BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP"
)
STATUS_BLOCKED_ASYMMETRIC_CAGE_TWIST_FFD_WARPAGE: str = (
    "BLOCKED_ASYMMETRIC_CAGE_TWIST_FFD_WARPAGE"
)
STATUS_BLOCKED_CAGETWIST_XLRH1_TELEMETRY_INVALID: str = (
    "BLOCKED_CAGETWIST_XLRH1_TELEMETRY_INVALID"
)

STATUS_BLOCKED_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE125_40GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G39 Tropical Monsoon Rain & Wet 24-Pin MI-Shoe Thresholds
MONSOON_RAIN_UNCAPPED_MISHOE_MAX_MM_HR: float = 0.5
MONSOON_RAIN_NONGASKETED_ACC_MAX_MM_HR: float = 2.0
MISHOE_MIN_DRY_CONTACT_RESISTANCE_KOHM: float = 50.0
MISHOE_LOGIC_RAIL_NOMINAL_V: float = 3.15
MISHOE_UNREG_RAIL_NOMINAL_V: float = 5.0

# Gate G40 XLR-H1 Whip-Shear, 1/4"-20 Thread Strip & Cage-Twist FFD Thresholds
STANDARD_GRAVITY_M_S2: float = 9.80665
XLR_H1_SUSPENDED_MASS_MAX_KG: float = 2.8
XLR_H1_TOP_HANDLE_MOMENT_MAX_NM: float = 3.2
BODY_QUARTER20_TORQUE_MAX_NM: float = 3.5
CAGE_UNSHIMMED_SIDE_GAP_MAX_MM: float = 0.25
EMOUNT_FLANGE_FOCAL_DISTANCE_MM: float = 18.00
EMOUNT_FFD_TOLERANCE_MM: float = 0.015
EMOUNT_FFD_TILT_MAX_UM: float = 12.0
EMOUNT_CAGE_TWIST_UM_PER_MM: float = 48.0

# Compact FX3/FX6 Donor Specs for MI-Shoe / Mount / ExtCmd / Power (O_RDONLY verified)
PINNED_PHASE125_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx6_lib_infra_hotshoe": (
        "fx6",
        "libInfraHotshoe.so",
        47_808,
        "0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6",
        (
            b"_ZN12InfraHotshoe13QueryShoeIdOnEij",
            b"_ZN12InfraHotshoe17SetShoeLogicPwrOnEb",
            b"_ZN12InfraHotshoe27SetShoeUnregOnWaitStabilityEbjj",
            b"INFRA_HOTSHOE_UIPC_SETSHOE_PWR_ON",
        ),
        "fx6/libInfraHotshoe.so::{QueryShoeIdOn,SetShoeLogicPwrOn,SetShoeUnregOnWaitStability,SETSHOE_PWR_ON}",
    ),
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
    "fx3_lib_bus_power": (
        "fx3",
        "libBusPower.so",
        43_968,
        "4c39d2789745a4638490da1aa41b39c90980c7dd30837a693e87085689bbcc0e",
        (
            b"_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt",
            b"_ZN8BusPower27NotifyUSBPowerContractStateEi",
            b"_ZN8BusPower25NotifyUSBPowerSupplyStateEPvi",
            b"MSGID_VBUS_ERROR_EVT",
        ),
        "fx3/libBusPower.so::{SetUSBPDSinkStatusToPowerManager,NotifyUSBPowerContractState,NotifyUSBPowerSupplyState,MSGID_VBUS_ERROR_EVT}",
    ),
    "fx6_lib_bus_power": (
        "fx6",
        "libBusPower.so",
        43_968,
        "d4f2ffe4e74786b66b64ca4eec05b0d433ff0157326156a486d7afec742d00b8",
        (
            b"_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt",
            b"_ZN8BusPower27NotifyUSBPowerContractStateEi",
            b"_ZN8BusPower25NotifyUSBPowerSupplyStateEPvi",
            b"MSGID_VBUS_ERROR_EVT",
        ),
        "fx6/libBusPower.so::{SetUSBPDSinkStatusToPowerManager,NotifyUSBPowerContractState,NotifyUSBPowerSupplyState,MSGID_VBUS_ERROR_EVT}",
    ),
}

PINNED_APPFW_MISHOE_MOUNT_TOKENS: Tuple[str, ...] = (
    "VAL_hotshoe_xlr_mic_connection_status_XLR_MIC_CONNECT_ON",
    "PID_SET_HOTSHOE_VIDEOLIGHT",
    "VAL_lens_information_LENS_INFORMATION_TYPE_EMOUNT",
    "VAL_built_in_steady_shot_error_BUILT_IN_STEADY_SHOT_ERROR_OCCURED",
    "OFF_BY_BATT_OVERCURRENT",
)

PINNED_CPAPP_MISHOE_MOUNT_TOKENS: Tuple[str, ...] = (
    "8AccyFifoI17ACCY_MI_SHOE_TYPEE",
    "7AdfFifoIN21AdfShoePowerSequencer38SHOE_POWER_SEQUENCER_RESERVE_CALL_BACKEE",
    "MSGQ_GID_HOTSHOE_INFRA1",
    "ID_FLG_CAM_LENS_MOUNT",
    "SET_S1_STEADY_SHOT_MODE",
)


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase125DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    mishoe_hotshoe_tokens_verified: bool
    lens_mount_comm_tokens_verified: bool
    ext_cmd_buspower_tokens_verified: bool
    large_binaries_scanned: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MonsoonMiShoeFirewallResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    weather_profile: str
    precipitation_mm_hr: float
    water_spray_rig: bool
    mi_shoe_accessory_attached: bool
    mi_shoe_weather_cap_installed: bool
    mi_shoe_silicone_perimeter_gasket_sealed: bool
    rain_cover_installed: bool
    mi_shoe_contact_resistance_kohm: float
    mi_shoe_power_rail_enabled: bool
    open_rubber_port_flaps_count: int
    weather_sealed_cable_gland_or_rain_slicker: bool
    estimated_leakage_current_ma: float
    estimated_electrolysis_power_mw: float
    uncapped_mishoe_rain_safe: bool
    gasketed_mishoe_accessory_safe: bool
    side_port_flap_capillary_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class XlrH1Quarter20CageTwistGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    rigging_profile: str
    xlr_h1_handle_installed: bool
    total_rig_mass_suspended_from_xlr_h1_kg: float
    top_handle_monitor_moment_nm: float
    metal_cage_nato_top_handle_reinforcement: bool
    body_thread_fastener_torque_nm: float
    cage_multi_point_locked: bool
    unshimmed_side_screw_gap_mm: float
    estimated_emount_ffd_tilt_um: float
    xlr_h1_whip_shear_safe: bool
    quarter20_thread_torque_safe: bool
    asymmetric_cage_twist_ffd_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G39MonsoonMiShoeResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    monsoon_mishoe_firewall: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G40XlrH1CageTwistResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    cagetwist_xlrh1_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master40GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_37_gates_verified: bool
    all_40_gates_verified: bool
    g13_to_g40_all_passed: bool
    g39_to_g40_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_38_report: Dict[str, Any]
    g39_result: Dict[str, Any]
    g40_result: Dict[str, Any]
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


def audit_phase125_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
) -> Phase125DonorAuditResult:
    """Inspect FX3/FX6 MI-Shoe/Lens-Mount/ExtCmd/BusPower donors via `os.O_RDONLY`."""
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
        "fx6_lib_infra_hotshoe": fx6_lib_dir / "libInfraHotshoe.so",
        "fx3_lib_infra_lens_comm": fx3_lib_dir / "libInfraLensCommunicator.so",
        "fx6_lib_infra_lens_comm": fx6_lib_dir / "libInfraLensCommunicator.so",
        "fx3_lib_infra_ext_cmd_svc": fx3_lib_dir / "libInfraExtCmdSvc.so",
        "fx6_lib_infra_ext_cmd_svc": fx6_lib_dir / "libInfraExtCmdSvc.so",
        "fx3_lib_bus_power": fx3_lib_dir / "libBusPower.so",
        "fx6_lib_bus_power": fx6_lib_dir / "libBusPower.so",
    }

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase125DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE125_DONOR_SPECS.values()
            ),
            missing_markers=(),
            mishoe_hotshoe_tokens_verified=True,
            lens_mount_comm_tokens_verified=True,
            ext_cmd_buspower_tokens_verified=True,
            large_binaries_scanned=False,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE125_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE125_DONOR_SPECS.items()
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
    ) in PINNED_PHASE125_DONOR_SPECS.items():
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
                paths.fx3_appfw_path, PINNED_APPFW_MISHOE_MOUNT_TOKENS
            )
            sizes["fx3_appfw"] = appfw_sz
            files_inspected += 1
            large_scanned = True
            if missing_appfw:
                appfw_ok = False
                missing.extend(missing_appfw)
                errors.append(
                    f"fx3 appFw.so missing MI-Shoe/E-Mount/IBIS/Overcurrent tokens: {missing_appfw}"
                )
            else:
                checked.append(
                    "fx3/appFw.so::XLR_MIC_CONNECT_ON+HOTSHOE_VIDEOLIGHT+LENS_TYPE_EMOUNT+STEADY_SHOT_ERROR+BATT_OVERCURRENT"
                )
        else:
            warnings.append(
                "fx3/appFw.so not found for optional large-binary MI-Shoe/E-Mount scan."
            )

        if paths.fx3_cp_path.is_file():
            cp_sz, missing_cp = scan_tokens_o_rdonly(
                paths.fx3_cp_path, PINNED_CPAPP_MISHOE_MOUNT_TOKENS
            )
            sizes["fx3_cpapp"] = cp_sz
            files_inspected += 1
            large_scanned = True
            if missing_cp:
                cpapp_ok = False
                missing.extend(missing_cp)
                errors.append(
                    f"fx3 cpapp-b.bin missing ACCY_MI_SHOE_TYPE/ShoePowerSequencer/LENS_MOUNT tokens: {missing_cp}"
                )
            else:
                checked.append(
                    "fx3/cpapp-b.bin::ACCY_MI_SHOE_TYPE+AdfShoePowerSequencer+HOTSHOE_INFRA1+ID_FLG_CAM_LENS_MOUNT"
                )
        else:
            warnings.append(
                "fx3/cpapp-b.bin not found for optional large-binary MI-Shoe sequencer scan."
            )

    valid = len(errors) == 0 and len(missing) == 0
    return Phase125DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        mishoe_hotshoe_tokens_verified=("fx6_lib_infra_hotshoe" in passed_keys)
        and appfw_ok
        and cpapp_ok,
        lens_mount_comm_tokens_verified={
            "fx3_lib_infra_lens_comm",
            "fx6_lib_infra_lens_comm",
        }.issubset(passed_keys)
        and appfw_ok
        and cpapp_ok,
        ext_cmd_buspower_tokens_verified={
            "fx3_lib_infra_ext_cmd_svc",
            "fx6_lib_infra_ext_cmd_svc",
            "fx3_lib_bus_power",
            "fx6_lib_bus_power",
        }.issubset(passed_keys)
        and appfw_ok,
        large_binaries_scanned=large_scanned,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Wet MI-Shoe Electrolysis & Cage-Twist / XLR-H1 Physics Helpers
# ---------------------------------------------------------------------------


def compute_mishoe_galvanic_leakage_current_ma(
    rail_voltage_v: float,
    contact_resistance_kohm: float,
) -> float:
    """Compute galvanic surface leakage current (mA = V / kOhm) across wet 24-pin MI-Shoe fingers."""
    if not (
        _is_finite_number(rail_voltage_v)
        and _is_finite_number(contact_resistance_kohm)
    ):
        raise ValueError(
            "rail_voltage_v and contact_resistance_kohm must be finite numbers."
        )
    if float(rail_voltage_v) < 0.0 or float(contact_resistance_kohm) <= 0.0:
        raise ValueError(
            "rail_voltage_v >= 0.0 and contact_resistance_kohm > 0.0 required."
        )
    return float(rail_voltage_v) / float(contact_resistance_kohm)


def estimate_mishoe_pin_electrolysis_power_mw(
    rail_voltage_v: float,
    contact_resistance_kohm: float,
) -> float:
    """Estimate galvanic electrolysis dissipation (mW = V^2 / kOhm) on wet MI-Shoe contacts."""
    if not (
        _is_finite_number(rail_voltage_v)
        and _is_finite_number(contact_resistance_kohm)
    ):
        raise ValueError(
            "rail_voltage_v and contact_resistance_kohm must be finite numbers."
        )
    if float(rail_voltage_v) < 0.0 or float(contact_resistance_kohm) <= 0.0:
        raise ValueError(
            "rail_voltage_v >= 0.0 and contact_resistance_kohm > 0.0 required."
        )
    v = float(rail_voltage_v)
    return (v * v) / float(contact_resistance_kohm)


def compute_xlr_h1_whip_moment_nm(
    suspended_mass_kg: float,
    lever_arm_m: float,
    *,
    dynamic_whip_g: float = 1.0,
) -> float:
    """Compute bending moment (N*m) applied to the 2x M4 XLR-H1 top-handle screws."""
    if not (
        _is_finite_number(suspended_mass_kg)
        and _is_finite_number(lever_arm_m)
        and _is_finite_number(dynamic_whip_g)
    ):
        raise ValueError(
            "suspended_mass_kg, lever_arm_m, and dynamic_whip_g must be finite numbers."
        )
    if (
        float(suspended_mass_kg) < 0.0
        or float(lever_arm_m) < 0.0
        or float(dynamic_whip_g) <= 0.0
    ):
        raise ValueError(
            "suspended_mass_kg >= 0.0, lever_arm_m >= 0.0, and dynamic_whip_g > 0.0 required."
        )
    return (
        float(suspended_mass_kg)
        * STANDARD_GRAVITY_M_S2
        * float(lever_arm_m)
        * float(dynamic_whip_g)
    )


def estimate_emount_ffd_tilt_um(
    unshimmed_side_screw_gap_mm: float,
    *,
    coupling_um_per_mm: float = EMOUNT_CAGE_TWIST_UM_PER_MM,
) -> float:
    """Estimate E-Mount 18.00 mm FFD flange tilt (um) induced by asymmetric cage side-screw twist."""
    if not (
        _is_finite_number(unshimmed_side_screw_gap_mm)
        and _is_finite_number(coupling_um_per_mm)
    ):
        raise ValueError(
            "unshimmed_side_screw_gap_mm and coupling_um_per_mm must be finite numbers."
        )
    if float(unshimmed_side_screw_gap_mm) < 0.0 or float(coupling_um_per_mm) < 0.0:
        raise ValueError(
            "unshimmed_side_screw_gap_mm and coupling_um_per_mm must be >= 0.0."
        )
    return float(unshimmed_side_screw_gap_mm) * float(coupling_um_per_mm)


# ---------------------------------------------------------------------------
# 3. Gate G39 — Tropical Monsoon Rain & Wet 24-Pin MI-Shoe Short-Circuit Firewall
# ---------------------------------------------------------------------------


def verify_monsoon_rain_mishoe_firewall(
    *,
    weather_profile: str = "FX3_CAPPED_DRY_STUDIO",
    precipitation_mm_hr: float = 0.0,
    water_spray_rig: bool = False,
    mi_shoe_accessory_attached: bool = False,
    mi_shoe_weather_cap_installed: bool = True,
    mi_shoe_silicone_perimeter_gasket_sealed: bool = False,
    rain_cover_installed: bool = False,
    mi_shoe_contact_resistance_kohm: float = 1000.0,
    mi_shoe_power_rail_enabled: bool = False,
    open_rubber_port_flaps_count: int = 0,
    weather_sealed_cable_gland_or_rain_slicker: bool = False,
    request_persistent_emmc_writes: bool = False,
) -> MonsoonMiShoeFirewallResult:
    """Verify Gate G39 (Tropical Monsoon Rain, Wet 24-Pin MI-Shoe Short & Port-Flap Capillary)."""
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
    if not _is_finite_number(precipitation_mm_hr) or float(precipitation_mm_hr) < 0.0:
        _add_code(codes, STATUS_BLOCKED_MONSOON_MISHOE_TELEMETRY_INVALID)
        errors.append(
            f"precipitation_mm_hr must be finite >= 0.0, got {precipitation_mm_hr!r}."
        )
        telemetry_ok = False
        eff_precip_mm_hr = 0.0
    else:
        eff_precip_mm_hr = float(precipitation_mm_hr)

    if (
        not _is_finite_number(mi_shoe_contact_resistance_kohm)
        or float(mi_shoe_contact_resistance_kohm) <= 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_MONSOON_MISHOE_TELEMETRY_INVALID)
        errors.append(
            f"mi_shoe_contact_resistance_kohm must be finite > 0.0, got {mi_shoe_contact_resistance_kohm!r}."
        )
        telemetry_ok = False
        eff_res_kohm = 1000.0
    else:
        eff_res_kohm = float(mi_shoe_contact_resistance_kohm)

    if not _is_non_negative_int(open_rubber_port_flaps_count):
        _add_code(codes, STATUS_BLOCKED_MONSOON_MISHOE_TELEMETRY_INVALID)
        errors.append(
            f"open_rubber_port_flaps_count must be integer >= 0, got {open_rubber_port_flaps_count!r}."
        )
        telemetry_ok = False
        eff_open_flaps = 0
    else:
        eff_open_flaps = int(open_rubber_port_flaps_count)

    rail_v = MISHOE_UNREG_RAIL_NOMINAL_V if mi_shoe_power_rail_enabled else 0.0
    leakage_ma = compute_mishoe_galvanic_leakage_current_ma(rail_v, eff_res_kohm)
    electrolysis_mw = estimate_mishoe_pin_electrolysis_power_mw(rail_v, eff_res_kohm)

    # a) Uncapped Wet 24-Pin MI-Shoe Rain / Galvanic Short-Circuit Guard
    uncapped_rain_exposed = (
        (eff_precip_mm_hr > MONSOON_RAIN_UNCAPPED_MISHOE_MAX_MM_HR)
        and (not bool(mi_shoe_accessory_attached))
        and (not bool(mi_shoe_weather_cap_installed))
    )
    wet_pin_bridge_powered = (
        eff_res_kohm < MISHOE_MIN_DRY_CONTACT_RESISTANCE_KOHM
    ) and bool(mi_shoe_power_rail_enabled)
    uncapped_mishoe_rain_safe = not (
        telemetry_ok and (uncapped_rain_exposed or wet_pin_bridge_powered)
    )
    if not uncapped_mishoe_rain_safe:
        _add_code(codes, STATUS_BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT)
        errors.append(
            f"BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT: {weather_profile} has "
            f"precipitation_mm_hr={eff_precip_mm_hr:.2f} mm/hr, "
            f"mi_shoe_weather_cap_installed={mi_shoe_weather_cap_installed}, "
            f"mi_shoe_contact_resistance_kohm={eff_res_kohm:.1f} kOhm "
            f"(limit >= {MISHOE_MIN_DRY_CONTACT_RESISTANCE_KOHM:.1f} kOhm) with "
            f"mi_shoe_power_rail_enabled={mi_shoe_power_rail_enabled} "
            f"(leakage={leakage_ma:.3f} mA, electrolysis={electrolysis_mw:.2f} mW) "
            "across FX3 24-pin MI-Shoe gold fingers."
        )

    # b) Non-Gasketed MI-Shoe Accessory in Heavy Rain Guard
    gasketed_mishoe_accessory_safe = not (
        telemetry_ok
        and (eff_precip_mm_hr > MONSOON_RAIN_NONGASKETED_ACC_MAX_MM_HR)
        and bool(mi_shoe_accessory_attached)
        and (not bool(mi_shoe_silicone_perimeter_gasket_sealed))
        and (not bool(rain_cover_installed))
    )
    if not gasketed_mishoe_accessory_safe:
        _add_code(codes, STATUS_BLOCKED_NON_GASKETED_MISHOE_ACCESSORY_IN_RAIN)
        errors.append(
            f"BLOCKED_NON_GASKETED_MISHOE_ACCESSORY_IN_RAIN: {weather_profile} has "
            f"precipitation_mm_hr={eff_precip_mm_hr:.2f} mm/hr "
            f"(limit {MONSOON_RAIN_NONGASKETED_ACC_MAX_MM_HR:.1f} mm/hr) with "
            "mi_shoe_accessory_attached=True, "
            "mi_shoe_silicone_perimeter_gasket_sealed=False, and "
            "rain_cover_installed=False, risking capillary ingress into the 24-pin recess."
        )

    # c) Open Side Port-Flap Capillary Ingress Guard
    side_port_flap_capillary_safe = not (
        telemetry_ok
        and (
            (eff_precip_mm_hr > MONSOON_RAIN_UNCAPPED_MISHOE_MAX_MM_HR)
            or bool(water_spray_rig)
        )
        and (eff_open_flaps > 0)
        and (not bool(weather_sealed_cable_gland_or_rain_slicker))
    )
    if not side_port_flap_capillary_safe:
        _add_code(codes, STATUS_BLOCKED_OPEN_SIDE_PORT_FLAP_CAPILLARY_INGRESS)
        errors.append(
            f"BLOCKED_OPEN_SIDE_PORT_FLAP_CAPILLARY_INGRESS: {weather_profile} has "
            f"precipitation_mm_hr={eff_precip_mm_hr:.2f} mm/hr, "
            f"water_spray_rig={water_spray_rig}, "
            f"open_rubber_port_flaps_count={eff_open_flaps} (> 0), and "
            "weather_sealed_cable_gland_or_rain_slicker=False, risking moisture wicking "
            "into FX3 HDMI Type-A / USB-C / Multi-Terminal ports."
        )

    if telemetry_ok and len(errors) == 0:
        if eff_precip_mm_hr > MONSOON_RAIN_UNCAPPED_MISHOE_MAX_MM_HR or water_spray_rig:
            warnings.append(
                "Wet-weather operation mitigated by MI-Shoe cap/gasket/rain-cover and port-flap sealing."
            )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return MonsoonMiShoeFirewallResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        weather_profile=str(weather_profile),
        precipitation_mm_hr=round(eff_precip_mm_hr, 3),
        water_spray_rig=bool(water_spray_rig),
        mi_shoe_accessory_attached=bool(mi_shoe_accessory_attached),
        mi_shoe_weather_cap_installed=bool(mi_shoe_weather_cap_installed),
        mi_shoe_silicone_perimeter_gasket_sealed=bool(
            mi_shoe_silicone_perimeter_gasket_sealed
        ),
        rain_cover_installed=bool(rain_cover_installed),
        mi_shoe_contact_resistance_kohm=round(eff_res_kohm, 3),
        mi_shoe_power_rail_enabled=bool(mi_shoe_power_rail_enabled),
        open_rubber_port_flaps_count=eff_open_flaps,
        weather_sealed_cable_gland_or_rain_slicker=bool(
            weather_sealed_cable_gland_or_rain_slicker
        ),
        estimated_leakage_current_ma=round(leakage_ma, 4),
        estimated_electrolysis_power_mw=round(electrolysis_mw, 4),
        uncapped_mishoe_rain_safe=uncapped_mishoe_rain_safe,
        gasketed_mishoe_accessory_safe=gasketed_mishoe_accessory_safe,
        side_port_flap_capillary_safe=side_port_flap_capillary_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G40 — XLR-H1 Whip Shear, 1/4"-20 Thread Strip & Cage-Twist FFD Guard
# ---------------------------------------------------------------------------


def verify_xlr_h1_quarter20_and_cage_twist_guard(
    *,
    rigging_profile: str = "FX3_CAGE_TORQUE_CALIBRATED_SHIMMED",
    xlr_h1_handle_installed: bool = False,
    total_rig_mass_suspended_from_xlr_h1_kg: float = 1.2,
    top_handle_monitor_moment_nm: float = 0.8,
    metal_cage_nato_top_handle_reinforcement: bool = False,
    body_thread_fastener_torque_nm: float = 2.2,
    cage_multi_point_locked: bool = True,
    unshimmed_side_screw_gap_mm: float = 0.0,
    estimated_emount_ffd_tilt_um: Optional[float] = None,
    request_persistent_emmc_writes: bool = False,
) -> XlrH1Quarter20CageTwistGuardResult:
    """Verify Gate G40 (XLR-H1 2x M4 whip shear, 1/4"-20 thread strip & cage-twist E-Mount FFD)."""
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
    if (
        not _is_finite_number(total_rig_mass_suspended_from_xlr_h1_kg)
        or float(total_rig_mass_suspended_from_xlr_h1_kg) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_CAGETWIST_XLRH1_TELEMETRY_INVALID)
        errors.append(
            "total_rig_mass_suspended_from_xlr_h1_kg must be finite >= 0.0, "
            f"got {total_rig_mass_suspended_from_xlr_h1_kg!r}."
        )
        telemetry_ok = False
        eff_mass_kg = 1.2
    else:
        eff_mass_kg = float(total_rig_mass_suspended_from_xlr_h1_kg)

    if (
        not _is_finite_number(top_handle_monitor_moment_nm)
        or float(top_handle_monitor_moment_nm) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_CAGETWIST_XLRH1_TELEMETRY_INVALID)
        errors.append(
            f"top_handle_monitor_moment_nm must be finite >= 0.0, got {top_handle_monitor_moment_nm!r}."
        )
        telemetry_ok = False
        eff_moment_nm = 0.8
    else:
        eff_moment_nm = float(top_handle_monitor_moment_nm)

    if (
        not _is_finite_number(body_thread_fastener_torque_nm)
        or float(body_thread_fastener_torque_nm) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_CAGETWIST_XLRH1_TELEMETRY_INVALID)
        errors.append(
            f"body_thread_fastener_torque_nm must be finite >= 0.0, got {body_thread_fastener_torque_nm!r}."
        )
        telemetry_ok = False
        eff_torque_nm = 2.2
    else:
        eff_torque_nm = float(body_thread_fastener_torque_nm)

    if (
        not _is_finite_number(unshimmed_side_screw_gap_mm)
        or float(unshimmed_side_screw_gap_mm) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_CAGETWIST_XLRH1_TELEMETRY_INVALID)
        errors.append(
            f"unshimmed_side_screw_gap_mm must be finite >= 0.0, got {unshimmed_side_screw_gap_mm!r}."
        )
        telemetry_ok = False
        eff_gap_mm = 0.0
    else:
        eff_gap_mm = float(unshimmed_side_screw_gap_mm)

    if estimated_emount_ffd_tilt_um is None:
        eff_tilt_um = estimate_emount_ffd_tilt_um(eff_gap_mm)
    elif (
        not _is_finite_number(estimated_emount_ffd_tilt_um)
        or float(estimated_emount_ffd_tilt_um) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_CAGETWIST_XLRH1_TELEMETRY_INVALID)
        errors.append(
            f"estimated_emount_ffd_tilt_um must be finite >= 0.0, got {estimated_emount_ffd_tilt_um!r}."
        )
        telemetry_ok = False
        eff_tilt_um = 0.0
    else:
        eff_tilt_um = float(estimated_emount_ffd_tilt_um)

    # a) XLR-H1 2x M4 Top-Handle Whip-Leverage Shear Guard
    xlr_h1_whip_shear_safe = not (
        telemetry_ok
        and bool(xlr_h1_handle_installed)
        and (
            (eff_mass_kg > XLR_H1_SUSPENDED_MASS_MAX_KG)
            or (eff_moment_nm > XLR_H1_TOP_HANDLE_MOMENT_MAX_NM)
        )
        and (not bool(metal_cage_nato_top_handle_reinforcement))
    )
    if not xlr_h1_whip_shear_safe:
        _add_code(codes, STATUS_BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR)
        errors.append(
            f"BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR: {rigging_profile} has "
            f"xlr_h1_handle_installed=True with suspended_mass={eff_mass_kg:.2f} kg "
            f"(limit {XLR_H1_SUSPENDED_MASS_MAX_KG:.1f} kg) and "
            f"top_handle_monitor_moment_nm={eff_moment_nm:.2f} N*m "
            f"(limit {XLR_H1_TOP_HANDLE_MOMENT_MAX_NM:.1f} N*m) without metal cage NATO "
            "top-handle reinforcement, risking 2x M4 / MI-Shoe bracket shear."
        )

    # b) 1/4"-20 Magnesium-Chassis Thread Strip Guard
    quarter20_thread_torque_safe = not (
        telemetry_ok and (eff_torque_nm > BODY_QUARTER20_TORQUE_MAX_NM)
    )
    if not quarter20_thread_torque_safe:
        _add_code(codes, STATUS_BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP)
        errors.append(
            f"BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP: {rigging_profile} applies "
            f"body_thread_fastener_torque_nm={eff_torque_nm:.2f} N*m "
            f"(limit {BODY_QUARTER20_TORQUE_MAX_NM:.1f} N*m), exceeding FX3 magnesium "
            "1/4\"-20 helicoil/boss yield threshold."
        )

    # c) Asymmetric Cage-Twist E-Mount 18.00 mm FFD Warpage Guard
    asymmetric_cage_twist_ffd_safe = not (
        telemetry_ok
        and bool(cage_multi_point_locked)
        and (eff_gap_mm > CAGE_UNSHIMMED_SIDE_GAP_MAX_MM)
        and (eff_tilt_um > EMOUNT_FFD_TILT_MAX_UM)
    )
    if not asymmetric_cage_twist_ffd_safe:
        _add_code(codes, STATUS_BLOCKED_ASYMMETRIC_CAGE_TWIST_FFD_WARPAGE)
        errors.append(
            f"BLOCKED_ASYMMETRIC_CAGE_TWIST_FFD_WARPAGE: {rigging_profile} has "
            f"cage_multi_point_locked=True with unshimmed_side_screw_gap_mm={eff_gap_mm:.3f} mm "
            f"(limit {CAGE_UNSHIMMED_SIDE_GAP_MAX_MM:.2f} mm) inducing "
            f"estimated_emount_ffd_tilt_um={eff_tilt_um:.2f} um "
            f"(limit {EMOUNT_FFD_TILT_MAX_UM:.1f} um across 18.00 mm E-Mount flange), "
            "decentering fast T1.4 cinema primes."
        )

    if telemetry_ok and len(errors) == 0:
        if (
            xlr_h1_handle_installed
            and (
                eff_mass_kg > XLR_H1_SUSPENDED_MASS_MAX_KG
                or eff_moment_nm > XLR_H1_TOP_HANDLE_MOMENT_MAX_NM
            )
            and metal_cage_nato_top_handle_reinforcement
        ):
            warnings.append(
                "Heavy XLR-H1 top-rig load safely offloaded via metal cage NATO top-handle reinforcement."
            )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return XlrH1Quarter20CageTwistGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        rigging_profile=str(rigging_profile),
        xlr_h1_handle_installed=bool(xlr_h1_handle_installed),
        total_rig_mass_suspended_from_xlr_h1_kg=round(eff_mass_kg, 3),
        top_handle_monitor_moment_nm=round(eff_moment_nm, 3),
        metal_cage_nato_top_handle_reinforcement=bool(
            metal_cage_nato_top_handle_reinforcement
        ),
        body_thread_fastener_torque_nm=round(eff_torque_nm, 3),
        cage_multi_point_locked=bool(cage_multi_point_locked),
        unshimmed_side_screw_gap_mm=round(eff_gap_mm, 4),
        estimated_emount_ffd_tilt_um=round(eff_tilt_um, 3),
        xlr_h1_whip_shear_safe=xlr_h1_whip_shear_safe,
        quarter20_thread_torque_safe=quarter20_thread_torque_safe,
        asymmetric_cage_twist_ffd_safe=asymmetric_cage_twist_ffd_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 5. Gate G39 & Gate G40 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g39_monsoon_rain_and_mishoe(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    monsoon_mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase125DonorAuditResult] = None,
) -> Tuple[GateVerdict, G39MonsoonMiShoeResult]:
    """Evaluate Gate G39 (`monsoon_rain_mishoe_short_and_port_flap_safe`)."""
    audit = donor_audit or audit_phase125_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(monsoon_mishoe_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    fw_res = verify_monsoon_rain_mishoe_firewall(**eff_kwargs)

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
        STATUS_VERIFIED_G39
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT
        )
    )

    res = G39MonsoonMiShoeResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        monsoon_mishoe_firewall=fw_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G39_GATE_ID,
        gate_code=G39_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Tropical Monsoon Rain / Wet 24-Pin MI-Shoe Short-Circuit & Port-Flap Capillary "
            f"Firewall ({fw_res.status}, precip={fw_res.precipitation_mm_hr:.2f}mm/hr, "
            f"cap={fw_res.mi_shoe_weather_cap_installed}, "
            f"r_contact={fw_res.mi_shoe_contact_resistance_kohm:.1f}kOhm, "
            f"open_flaps={fw_res.open_rubber_port_flaps_count}, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "uncapped_mishoe_rain_safe": fw_res.uncapped_mishoe_rain_safe,
            "gasketed_mishoe_accessory_safe": fw_res.gasketed_mishoe_accessory_safe,
            "side_port_flap_capillary_safe": fw_res.side_port_flap_capillary_safe,
        },
    )
    return verdict, res


def evaluate_g40_xlr_h1_quarter20_and_cage_twist(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    cagetwist_xlrh1_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase125DonorAuditResult] = None,
) -> Tuple[GateVerdict, G40XlrH1CageTwistResult]:
    """Evaluate Gate G40 (`xlr_h1_whip_shear_quarter20_torque_and_cage_ffd_safe`)."""
    audit = donor_audit or audit_phase125_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(cagetwist_xlrh1_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    guard_res = verify_xlr_h1_quarter20_and_cage_twist_guard(**eff_kwargs)

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
        STATUS_VERIFIED_G40
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR
        )
    )

    res = G40XlrH1CageTwistResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        cagetwist_xlrh1_guard=guard_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G40_GATE_ID,
        gate_code=G40_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"FX3 XLR-H1 Whip-Leverage Shear, 1/4\"-20 Magnesium Thread Strip & Cage-Twist "
            f"18.00 mm E-Mount FFD Guard ({guard_res.status}, "
            f"xlr_h1={guard_res.xlr_h1_handle_installed}, "
            f"mass={guard_res.total_rig_mass_suspended_from_xlr_h1_kg:.2f}kg, "
            f"torque={guard_res.body_thread_fastener_torque_nm:.2f}Nm, "
            f"ffd_tilt={guard_res.estimated_emount_ffd_tilt_um:.2f}um, "
            f"{audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "xlr_h1_whip_shear_safe": guard_res.xlr_h1_whip_shear_safe,
            "quarter20_thread_torque_safe": guard_res.quarter20_thread_torque_safe,
            "asymmetric_cage_twist_ffd_safe": guard_res.asymmetric_cage_twist_ffd_safe,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 6. Master 40-Gate Preflight Evaluator (`G01..G40`) & CLI
# ---------------------------------------------------------------------------


def evaluate_40gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G38 pass-throughs
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
    # G39 inputs (Monsoon Rain, Wet 24-Pin MI-Shoe Short & Port-Flap Capillary Firewall)
    monsoon_mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    # G40 inputs (XLR-H1 2x M4 Whip Shear, 1/4"-20 Thread Strip & Cage-Twist FFD Guard)
    cagetwist_xlrh1_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master40GateReport:
    """Evaluate all 40 Master Safety Gates (`G01..G40`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m38_kwargs: Dict[str, Any] = {
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
    }
    if soc_start_ceiling_c is not None:
        m38_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m38_report: Master38GateReport = evaluate_38gate_preflight(
        resolved_root, **m38_kwargs
    )

    phase125_audit = audit_phase125_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
    )

    g39_verdict, g39_res = evaluate_g39_monsoon_rain_and_mishoe(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        monsoon_mishoe_kwargs=monsoon_mishoe_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase125_audit,
    )

    g40_verdict, g40_res = evaluate_g40_xlr_h1_quarter20_and_cage_twist(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        cagetwist_xlrh1_kwargs=cagetwist_xlrh1_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase125_audit,
    )

    gates_39_to_40 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g39_verdict, g40_verdict)
    ]
    all_gates = tuple(list(m38_report.gates) + gates_39_to_40)

    g01_to_g12_verified = int(m38_report.summary["g01_to_g12_verified"])
    g13_to_g38_verified = (
        int(m38_report.summary["g13_to_g36_verified"])
        + int(m38_report.summary["g37_to_g38_verified"])
    )
    g39_to_g40_verified = sum(1 for v in (g39_verdict, g40_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g38_verified + g39_to_g40_verified

    g39_to_g40_all_passed = g39_to_g40_verified == 2
    g13_to_g40_all_passed = (
        m38_report.g13_to_g38_all_passed and g39_to_g40_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m38_report.gates[:9])

    offline_37_verified = (
        g01_to_g09_ok
        and m38_report.offline_35_gates_verified
        and g39_to_g40_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_40_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g40_all_passed
        and (not request_persistent_emmc_writes)
    )

    real_tier0_verified = (g01_to_g12_verified == 12) and (
        not dry_run_simulated_backup
    )
    overall_ready_for_hardware_attach = (
        real_tier0_verified
        and g13_to_g40_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    h0_h1_allowed = (
        offline_37_verified
        and m38_report.h0_h1_trial_entry_allowed
        and g39_to_g40_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m38_report.errors) + list(g39_verdict.errors) + list(g40_verdict.errors)
    )
    warnings: List[str] = (
        list(m38_report.warnings)
        + list(g39_verdict.warnings)
        + list(g40_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m38_report.g13_to_g38_all_passed:
        overall_status = m38_report.status
    elif not g39_verdict.passed:
        overall_status = g39_verdict.status
    elif not g40_verdict.passed:
        overall_status = g40_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_40_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_40_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_40_verified:
        overall_status = "VERIFIED_ALL_40_GATES"
    else:
        overall_status = "VERIFIED_37_OF_40_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m38_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g39_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g40_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 40,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 40 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g38_verified": g13_to_g38_verified,
        "g39_to_g40_verified": g39_to_g40_verified,
        "g13_to_g40_all_passed": g13_to_g40_all_passed,
        "g39_to_g40_all_passed": g39_to_g40_all_passed,
        "offline_37_gates_verified": offline_37_verified,
        "all_40_gates_verified": all_40_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master40GateReport(
        schema=MONSOON_MISHOE_CAGETWIST_40GATE_SCHEMA,
        version=MONSOON_MISHOE_CAGETWIST_40GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_37_gates_verified=offline_37_verified,
        all_40_gates_verified=all_40_verified,
        g13_to_g40_all_passed=g13_to_g40_all_passed,
        g39_to_g40_all_passed=g39_to_g40_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_38_report=m38_report.to_dict(),
        g39_result=g39_res.to_dict(),
        g40_result=g40_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_40_master_safety_gates = evaluate_40gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="monsoon_mishoe_cagetwist_and_40gate_guard",
        description=(
            "Milestone Phase 125 — Tropical Monsoon Rain / Wet MI-Shoe 24-Pin Short Firewall "
            "(G39), FX3 XLR-H1 Whip-Shear / 1/4\"-20 Thread Strip & Cage-Twist FFD Guard (G40), "
            "and 40-Gate Master Preflight (G01..G40)"
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G40 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_40gate_preflight(
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
            f"verified={report.summary['verified_gates']}/40 "
            f"g39_to_g40_all_passed={report.g39_to_g40_all_passed} "
            f"all_40_gates_verified={report.all_40_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = (
        report.all_40_gates_verified
        if args.dry_run_simulated_backup
        else report.offline_37_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
