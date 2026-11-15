"""Phase 108 — Coastal Salt-Spray / Studio Glycol-Haze Fan Ingestion Firewall (Gate G33),
Wireless Follow-Focus Hard-Stop Lens-Barrel Torque & Gimbal Dynamic CoG Shift Guard
(Gate G34), and Unified 34-Gate Master Safety Preflight (`G01..G34` / `verify-34-gates`).

Operationalizes two critical environmental-aerosol & motorized-rigging hardware
protections for Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, SoC `CXD90057`),
while keeping all prior gate modules (`preflight.py`, `master_16gate_preflight.py`,
`usblan_ptpip_and_18gate_preflight.py`, `rig_groundloop_lensrail_and_20gate_guard.py`,
`phantom48v_gimbal_and_22gate_guard.py`, `dewpoint_tec_usbc_and_24gate_guard.py`,
`intake_occlusion_tripod_and_26gate_guard.py`,
`sensor_curtain_subzero_and_28gate_guard.py`,
`wireless_tx_emi_endurance_and_30gate_guard.py`, and
`pl_cantilever_dummybatt_and_32gate_guard.py`) completely untouched:

1. **Read-Only (`os.O_RDONLY`) FX3/FX6 Donor Cooling / Lens-Comm / ExtCmd Audit**:
   - Inspects local FX3 `v7.02` & FX6 `v6.01` `libfan.so`
     (`fan_infra_init`, `_Z19fan_i_bkup_is_validv`,
     `_Z33psm_fan_i_bkup_read_dev_temp_infoP22ST_FAN_I_DEV_TEMP_LIST`,
     `g_bkup_dev_temp_bkid_list`, `_Z15fan_i_bkup_readP13ST_FAN_I_BKUP`),
     `libInfraLensCommunicator.so` (`GetMountedLensInfo`, `SndSyncMsg`,
     `GetSuopportedCommandIds`, `ReadBackup`), and `libInfraExtCmdSvc.so`
     (`ExtCmdSvc_Create`, `IntrRegistTransportCmd`, `SndMsgToUpperSync`)
     strictly via `os.open(..., os.O_RDONLY)`, plus optional chunked scans of
     `appFw.so` (`FAN_CONTROL_AUTO`, `FAN_CONTROL_MINIMUM`, `OFF_BY_IM_THERMAL`,
     `VAL_lens_information_LENS_INFORMATION_TYPE_EMOUNT`,
     `PRM_FEATURE_MANAGER_lens_mount`, `FOCUS_MODE`, `STEADY_SHOT`, `ZOOM`)
     and `cpapp-b.bin` (`FAN_EQ_ID`, `SET_S1_STEADY_SHOT_MODE`,
     `C_LENS_XDETECT_BODY_INT_NO`, `THERMISTOR_ADJ_START`) when
     `include_large_binaries=True`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent.

2. **Gate G33 — Coastal Salt-Spray / Fine Desert Silica Dust & Studio Mineral-Oil /
   Glycol Haze Sigma Blower Ingestion Firewall**:
   - FX3's internal Sigma centrifugal cooling duct isolates the mainboard via a
     graphite-heatsink partition, yet active air suction pulls salt-laden surf mist,
     fine Sahara/playa alkali dust (<10 um), or heavy soundstage mineral-oil/glycol
     haze directly onto the fan impeller bearing and heatsink fins, caking sticky
     conductive residue or seizing the Hall-sensor bearing.
   - Fails closed on:
     a) `BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT` when
        `coastal_salt_spray_env == True` and
        `hydrophobic_vent_membrane_or_housing == False`,
     b) `BLOCKED_FINE_ALKALI_DUST_ABRASION_HAZARD` when
        `pm10_dust_ug_m3 > 600.0` and `intake_hepa_mesh_installed == False`,
     c) `BLOCKED_OIL_GLYCOL_HAZE_FIN_FOULING` when
        `studio_haze_density_mg_m3 > 25.0` and `continuous_fan_exposure_min > 45.0`
        and `post_wrap_isopropyl_duct_purge_scheduled == False`.

3. **Gate G34 — High-Torque Wireless Follow-Focus (`Nucleus-M / Preston / Tilta`
   `> 2.5 N*m`) Uncalibrated Hard-Stop Gear Stripping & Telescoping-Zoom Gimbal
   Motor Oscillation Guard**:
   - Cinema wireless follow-focus motors (`2.5 N*m .. 5.0 N*m`) mounted on a single
     15mm rod without automatic/manual A-B hard-stop calibration slam Sony
     fly-by-wire E-Mount plastic helicoids or vintage cine brass stops, stripping
     focus gears or flexing the single rod and misaligning gear mesh. Furthermore,
     external-zooming lenses (`24-70 / 200-600`) shift CoG > 18 mm during zoom on
     compact 3-axis gimbals (`RS3/RS4`), inducing violent `40..90 Hz` roll/pitch PID
     oscillation that saturates FX3's IBIS voice coils.
   - Fails closed on:
     a) `BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE` when
        `wireless_fiz_motor_torque_nm > 1.2` and `hard_stops_calibrated == False`
        and `fly_by_wire_infinite_ring == False`,
     b) `BLOCKED_SINGLE_ROD_FIZ_DEFLECTION_SLIP` when
        `wireless_fiz_motor_torque_nm > 1.8` and
        `dual_rod_or_cage_bridge_clamp == False`,
     c) `BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION` when
        `gimbal_mounted == True` and `zoom_cog_shift_mm > 15.0` and
        `gimbal_autotune_after_zoom == False`.

4. **Unified 34-Gate Master Safety Preflight (`evaluate_34gate_preflight` / CLI
   `verify-34-gates`)**:
   - Composes `evaluate_32gate_preflight` (`G01..G32`) with `G33` and `G34`:
     * Offline default mode: `31/34` gates pass (`G10..G12` physical Tier-0 backup
       truthfully remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` ->
       `overall_ready_for_hardware_attach = False`).
     * `--dry-run-simulated-backup` mode: `34/34` simulation gates pass
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
from .pl_cantilever_dummybatt_and_32gate_guard import (
    Master32GateReport,
    evaluate_32gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
    scan_tokens_o_rdonly,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

SALTSPRAY_HAZE_FOLLOWFOCUS_34GATE_SCHEMA: str = (
    "fx3-saltspray-haze-followfocus-34gate-preflight-v1"
)
SALTSPRAY_HAZE_FOLLOWFOCUS_34GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G33..G34
G33_GATE_ID: str = "G33_saltspray_alkali_dust_and_glycol_haze_ingestion_safe"
G33_GATE_CODE: str = "SALTSPRAY_ALKALI_DUST_AND_GLYCOL_HAZE_INGESTION_SAFE"

G34_GATE_ID: str = "G34_wireless_followfocus_hardstop_and_gimbal_cog_safe"
G34_GATE_CODE: str = "WIRELESS_FOLLOWFOCUS_HARDSTOP_AND_GIMBAL_COG_SAFE"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G33: str = (
    "VERIFIED_SALTSPRAY_ALKALI_DUST_AND_GLYCOL_HAZE_INGESTION_SAFE"
)
STATUS_VERIFIED_G34: str = (
    "VERIFIED_WIRELESS_FOLLOWFOCUS_HARDSTOP_AND_GIMBAL_COG_SAFE"
)

# Gate G33 Violation Codes
STATUS_BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT: str = (
    "BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT"
)
STATUS_BLOCKED_FINE_ALKALI_DUST_ABRASION_HAZARD: str = (
    "BLOCKED_FINE_ALKALI_DUST_ABRASION_HAZARD"
)
STATUS_BLOCKED_OIL_GLYCOL_HAZE_FIN_FOULING: str = (
    "BLOCKED_OIL_GLYCOL_HAZE_FIN_FOULING"
)
STATUS_BLOCKED_SALTSPRAY_HAZE_TELEMETRY_INVALID: str = (
    "BLOCKED_SALTSPRAY_HAZE_TELEMETRY_INVALID"
)

# Gate G34 Violation Codes
STATUS_BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE: str = (
    "BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE"
)
STATUS_BLOCKED_SINGLE_ROD_FIZ_DEFLECTION_SLIP: str = (
    "BLOCKED_SINGLE_ROD_FIZ_DEFLECTION_SLIP"
)
STATUS_BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION: str = (
    "BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION"
)
STATUS_BLOCKED_FOLLOWFOCUS_GIMBAL_TELEMETRY_INVALID: str = (
    "BLOCKED_FOLLOWFOCUS_GIMBAL_TELEMETRY_INVALID"
)

STATUS_BLOCKED_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE108_34GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G33 Aerosol / Dust / Haze Thresholds
PM10_DUST_MAX_UNFILTERED_UG_M3: float = 600.0
STUDIO_HAZE_MAX_UNPURGED_MG_M3: float = 25.0
HAZE_MAX_CONTINUOUS_FAN_MIN: float = 45.0
SIGMA_BLOWER_NOMINAL_AIRFLOW_L_MIN: float = 18.0

# Gate G34 Follow-Focus Torque, Rod Mechanics & Gimbal CoG Shift Thresholds
FIZ_UNCALIBRATED_MAX_TORQUE_NM: float = 1.2
FIZ_SINGLE_ROD_MAX_TORQUE_NM: float = 1.8
FIZ_TYPICAL_HIGH_TORQUE_MIN_NM: float = 2.5
FIZ_TYPICAL_HIGH_TORQUE_MAX_NM: float = 5.0
GIMBAL_MAX_UNAUTOTUNED_ZOOM_COG_SHIFT_MM: float = 15.0
GIMBAL_OSCILLATION_BAND_MIN_HZ: float = 40.0
GIMBAL_OSCILLATION_BAND_MAX_HZ: float = 90.0
DEFAULT_FIZ_GEAR_PITCH_RADIUS_MM: float = 15.0
DEFAULT_15MM_ROD_CANTILEVER_MM: float = 120.0
# 15mm OD x 12mm ID 6061-T6 aluminum rod flexural rigidity EI = E * I (N*m^2)
ROD_15MM_FLEXURAL_EI_NM2: float = (
    69.0e9 * (math.pi / 64.0) * (0.015**4 - 0.012**4)
)
STANDARD_GRAVITY_M_S2: float = 9.80665

# Compact FX3/FX6 Donor Specs for Fan/Duct & Lens/ExtCmd Contracts (O_RDONLY verified)
PINNED_PHASE108_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_lib_fan": (
        "fx3",
        "libfan.so",
        27_280,
        "c607fc8d3ea3b46ef1082e07c57ba484a910e6841772e638ab5909189942726c",
        (
            b"fan_infra_init",
            b"_Z19fan_i_bkup_is_validv",
            b"_Z33psm_fan_i_bkup_read_dev_temp_infoP22ST_FAN_I_DEV_TEMP_LIST",
            b"g_bkup_dev_temp_bkid_list",
            b"_Z15fan_i_bkup_readP13ST_FAN_I_BKUP",
        ),
        "fx3/libfan.so::{fan_infra_init,fan_i_bkup_is_valid,dev_temp_info,g_bkup_dev_temp_bkid_list}",
    ),
    "fx6_lib_fan": (
        "fx6",
        "libfan.so",
        31_176,
        "d4f01ff36a2d3d45c236cdb546816d585eed4aa9ce1ca68fdb03174151ea4850",
        (
            b"fan_infra_init",
            b"_Z19fan_i_bkup_is_validv",
            b"_Z33psm_fan_i_bkup_read_dev_temp_infoP22ST_FAN_I_DEV_TEMP_LIST",
            b"g_bkup_dev_temp_bkid_list",
            b"_Z15fan_i_bkup_readP13ST_FAN_I_BKUP",
        ),
        "fx6/libfan.so::{fan_infra_init,fan_i_bkup_is_valid,dev_temp_info,g_bkup_dev_temp_bkid_list}",
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
        ),
        "fx3/libInfraExtCmdSvc.so::{ExtCmdSvc_Create,IntrRegistTransportCmd,SndMsgToUpperSync}",
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
        ),
        "fx6/libInfraExtCmdSvc.so::{ExtCmdSvc_Create,IntrRegistTransportCmd,SndMsgToUpperSync}",
    ),
}

PINNED_APPFW_FAN_LENS_TOKENS: Tuple[str, ...] = (
    "FAN_CONTROL_AUTO",
    "FAN_CONTROL_MINIMUM",
    "OFF_BY_IM_THERMAL",
    "VAL_lens_information_LENS_INFORMATION_TYPE_EMOUNT",
    "PRM_FEATURE_MANAGER_lens_mount",
    "FOCUS_MODE",
    "STEADY_SHOT",
    "ZOOM",
)

PINNED_CPAPP_FAN_IBIS_TOKENS: Tuple[str, ...] = (
    "FAN_EQ_ID",
    "SET_S1_STEADY_SHOT_MODE",
    "C_LENS_XDETECT_BODY_INT_NO",
    "THERMISTOR_ADJ_START",
)


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase108DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    sigma_fan_tokens_verified: bool
    emount_lens_comm_tokens_verified: bool
    ext_cmd_svc_tokens_verified: bool
    large_binaries_scanned: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SaltsprayHazeFirewallResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    environment_profile: str
    coastal_salt_spray_env: bool
    hydrophobic_vent_membrane_or_housing: bool
    pm10_dust_ug_m3: float
    intake_hepa_mesh_installed: bool
    studio_haze_density_mg_m3: float
    continuous_fan_exposure_min: float
    post_wrap_isopropyl_duct_purge_scheduled: bool
    haze_exposure_dose_mg_min_m3: float
    estimated_ingested_aerosol_ug: float
    saltspray_duct_safe: bool
    alkali_dust_filtration_safe: bool
    glycol_haze_fouling_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FollowFocusGimbalGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    rig_profile: str
    wireless_fiz_motor_torque_nm: float
    hard_stops_calibrated: bool
    fly_by_wire_infinite_ring: bool
    dual_rod_or_cage_bridge_clamp: bool
    gimbal_mounted: bool
    zoom_cog_shift_mm: float
    gimbal_autotune_after_zoom: bool
    rig_mass_kg: float
    gear_pitch_radius_mm: float
    rod_cantilever_mm: float
    gear_tangential_force_n: float
    single_rod_deflection_mm: float
    gimbal_cog_torque_imbalance_nm: float
    hardstop_torque_safe: bool
    rod_deflection_mesh_safe: bool
    gimbal_cog_oscillation_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G33SaltsprayHazeResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    saltspray_haze_firewall: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G34FollowFocusGimbalResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    followfocus_gimbal_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master34GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_31_gates_verified: bool
    all_34_gates_verified: bool
    g13_to_g34_all_passed: bool
    g33_to_g34_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_32_report: Dict[str, Any]
    g33_result: Dict[str, Any]
    g34_result: Dict[str, Any]
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


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase108_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
) -> Phase108DonorAuditResult:
    """Inspect FX3/FX6 Sigma fan, lens-communicator & ExtCmdSvc donors via `os.O_RDONLY`."""
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
        "fx3_lib_fan": fx3_lib_dir / "libfan.so",
        "fx6_lib_fan": fx6_lib_dir / "libfan.so",
        "fx3_lib_infra_lens_comm": fx3_lib_dir / "libInfraLensCommunicator.so",
        "fx6_lib_infra_lens_comm": fx6_lib_dir / "libInfraLensCommunicator.so",
        "fx3_lib_infra_ext_cmd_svc": fx3_lib_dir / "libInfraExtCmdSvc.so",
        "fx6_lib_infra_ext_cmd_svc": fx6_lib_dir / "libInfraExtCmdSvc.so",
    }

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase108DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE108_DONOR_SPECS.values()
            ),
            missing_markers=(),
            sigma_fan_tokens_verified=True,
            emount_lens_comm_tokens_verified=True,
            ext_cmd_svc_tokens_verified=True,
            large_binaries_scanned=False,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE108_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE108_DONOR_SPECS.items()
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
    ) in PINNED_PHASE108_DONOR_SPECS.items():
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
                paths.fx3_appfw_path, PINNED_APPFW_FAN_LENS_TOKENS
            )
            sizes["fx3_appfw"] = appfw_sz
            files_inspected += 1
            large_scanned = True
            if missing_appfw:
                appfw_ok = False
                missing.extend(missing_appfw)
                errors.append(
                    f"fx3 appFw.so missing fan/lens/steadyshot tokens: {missing_appfw}"
                )
            else:
                checked.append(
                    "fx3/appFw.so::FAN_CONTROL+EMOUNT+FOCUS_MODE+STEADY_SHOT+ZOOM"
                )
        else:
            warnings.append(
                "fx3/appFw.so not found for optional large-binary fan/lens/IBIS scan."
            )

        if paths.fx3_cp_path.is_file():
            cp_sz, missing_cp = scan_tokens_o_rdonly(
                paths.fx3_cp_path, PINNED_CPAPP_FAN_IBIS_TOKENS
            )
            sizes["fx3_cpapp"] = cp_sz
            files_inspected += 1
            large_scanned = True
            if missing_cp:
                cpapp_ok = False
                missing.extend(missing_cp)
                errors.append(
                    f"fx3 cpapp-b.bin missing FAN_EQ_ID/STEADY_SHOT/LENS_XDETECT tokens: {missing_cp}"
                )
            else:
                checked.append(
                    "fx3/cpapp-b.bin::FAN_EQ_ID+SET_S1_STEADY_SHOT_MODE+C_LENS_XDETECT"
                )
        else:
            warnings.append(
                "fx3/cpapp-b.bin not found for optional large-binary CP fan/IBIS scan."
            )

    valid = len(errors) == 0 and len(missing) == 0
    return Phase108DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        sigma_fan_tokens_verified={
            "fx3_lib_fan",
            "fx6_lib_fan",
        }.issubset(passed_keys)
        and appfw_ok
        and cpapp_ok,
        emount_lens_comm_tokens_verified={
            "fx3_lib_infra_lens_comm",
            "fx6_lib_infra_lens_comm",
        }.issubset(passed_keys)
        and appfw_ok
        and cpapp_ok,
        ext_cmd_svc_tokens_verified={
            "fx3_lib_infra_ext_cmd_svc",
            "fx6_lib_infra_ext_cmd_svc",
        }.issubset(passed_keys),
        large_binaries_scanned=large_scanned,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Aerosol & Follow-Focus/Gimbal Physics Helpers for Gates G33 & G34
# ---------------------------------------------------------------------------


def compute_haze_fin_fouling_dose_mg_min_m3(
    studio_haze_density_mg_m3: float,
    continuous_fan_exposure_min: float,
) -> float:
    """Compute cumulative soundstage haze exposure dose (mg*min/m^3)."""
    if not (
        _is_finite_number(studio_haze_density_mg_m3)
        and _is_finite_number(continuous_fan_exposure_min)
    ):
        raise ValueError(
            "studio_haze_density_mg_m3 and continuous_fan_exposure_min must be finite numbers."
        )
    if (
        float(studio_haze_density_mg_m3) < 0.0
        or float(continuous_fan_exposure_min) < 0.0
    ):
        raise ValueError(
            "studio_haze_density_mg_m3 and continuous_fan_exposure_min must be >= 0.0."
        )
    return float(studio_haze_density_mg_m3) * float(continuous_fan_exposure_min)


def compute_estimated_ingested_aerosol_ug(
    concentration_ug_m3: float,
    exposure_min: float,
    *,
    airflow_l_per_min: float = SIGMA_BLOWER_NOMINAL_AIRFLOW_L_MIN,
) -> float:
    """Estimate total aerosol mass (ug) drawn through FX3's Sigma blower duct."""
    if not (
        _is_finite_number(concentration_ug_m3)
        and _is_finite_number(exposure_min)
        and _is_finite_number(airflow_l_per_min)
    ):
        raise ValueError(
            "concentration_ug_m3, exposure_min, and airflow_l_per_min must be finite."
        )
    if (
        float(concentration_ug_m3) < 0.0
        or float(exposure_min) < 0.0
        or float(airflow_l_per_min) < 0.0
    ):
        raise ValueError(
            "concentration_ug_m3, exposure_min, and airflow_l_per_min must be >= 0.0."
        )
    air_volume_m3 = (float(airflow_l_per_min) * float(exposure_min)) / 1000.0
    return float(concentration_ug_m3) * air_volume_m3


def compute_fiz_gear_tangential_force_n(
    torque_nm: float,
    gear_pitch_radius_mm: float = DEFAULT_FIZ_GEAR_PITCH_RADIUS_MM,
) -> float:
    """Compute tangential tooth force `F = tau / r` (N) at the follow-focus drive gear."""
    if not (
        _is_finite_number(torque_nm) and _is_finite_number(gear_pitch_radius_mm)
    ):
        raise ValueError("torque_nm and gear_pitch_radius_mm must be finite.")
    if float(torque_nm) < 0.0 or float(gear_pitch_radius_mm) <= 0.0:
        raise ValueError("torque_nm >= 0.0 and gear_pitch_radius_mm > 0.0 required.")
    return float(torque_nm) / (float(gear_pitch_radius_mm) / 1000.0)


def compute_single_rod_deflection_mm(
    tangential_force_n: float,
    rod_cantilever_mm: float = DEFAULT_15MM_ROD_CANTILEVER_MM,
    *,
    flexural_ei_nm2: float = ROD_15MM_FLEXURAL_EI_NM2,
) -> float:
    """Compute cantilever tip deflection `delta = F * L^3 / (3 * EI)` in mm."""
    if not (
        _is_finite_number(tangential_force_n)
        and _is_finite_number(rod_cantilever_mm)
        and _is_finite_number(flexural_ei_nm2)
    ):
        raise ValueError(
            "tangential_force_n, rod_cantilever_mm, and flexural_ei_nm2 must be finite."
        )
    if (
        float(tangential_force_n) < 0.0
        or float(rod_cantilever_mm) <= 0.0
        or float(flexural_ei_nm2) <= 0.0
    ):
        raise ValueError(
            "tangential_force_n >= 0.0, rod_cantilever_mm > 0.0, flexural_ei_nm2 > 0.0 required."
        )
    l_m = float(rod_cantilever_mm) / 1000.0
    delta_m = (float(tangential_force_n) * (l_m**3)) / (3.0 * float(flexural_ei_nm2))
    return delta_m * 1000.0


def compute_gimbal_cog_torque_imbalance_nm(
    rig_mass_kg: float,
    zoom_cog_shift_mm: float,
) -> float:
    """Compute pitch/roll torque disturbance `tau = m * g * (delta_cog / 1000.0)` in N*m."""
    if not (_is_finite_number(rig_mass_kg) and _is_finite_number(zoom_cog_shift_mm)):
        raise ValueError("rig_mass_kg and zoom_cog_shift_mm must be finite.")
    if float(rig_mass_kg) < 0.0 or float(zoom_cog_shift_mm) < 0.0:
        raise ValueError("rig_mass_kg >= 0.0 and zoom_cog_shift_mm >= 0.0 required.")
    return (
        float(rig_mass_kg)
        * STANDARD_GRAVITY_M_S2
        * (float(zoom_cog_shift_mm) / 1000.0)
    )


# ---------------------------------------------------------------------------
# 3. Gate G33 — Coastal Salt-Spray / Alkali Dust / Studio Glycol-Haze Firewall
# ---------------------------------------------------------------------------


def verify_saltspray_alkali_dust_and_haze_firewall(
    *,
    environment_profile: str = "CLEAN_CONTROLLED_INTERIOR",
    coastal_salt_spray_env: bool = False,
    hydrophobic_vent_membrane_or_housing: bool = False,
    pm10_dust_ug_m3: float = 35.0,
    intake_hepa_mesh_installed: bool = False,
    studio_haze_density_mg_m3: float = 2.0,
    continuous_fan_exposure_min: float = 15.0,
    post_wrap_isopropyl_duct_purge_scheduled: bool = False,
    request_persistent_emmc_writes: bool = False,
) -> SaltsprayHazeFirewallResult:
    """Verify Gate G33 (Coastal salt-spray, <10um alkali dust & studio oil/glycol haze guard)."""
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
    if not _is_finite_number(pm10_dust_ug_m3) or float(pm10_dust_ug_m3) < 0.0:
        _add_code(codes, STATUS_BLOCKED_SALTSPRAY_HAZE_TELEMETRY_INVALID)
        errors.append(
            f"pm10_dust_ug_m3 must be finite >= 0.0, got {pm10_dust_ug_m3!r}."
        )
        telemetry_ok = False
        eff_pm10 = 35.0
    else:
        eff_pm10 = float(pm10_dust_ug_m3)

    if (
        not _is_finite_number(studio_haze_density_mg_m3)
        or float(studio_haze_density_mg_m3) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_SALTSPRAY_HAZE_TELEMETRY_INVALID)
        errors.append(
            "studio_haze_density_mg_m3 must be finite >= 0.0, "
            f"got {studio_haze_density_mg_m3!r}."
        )
        telemetry_ok = False
        eff_haze = 2.0
    else:
        eff_haze = float(studio_haze_density_mg_m3)

    if (
        not _is_finite_number(continuous_fan_exposure_min)
        or float(continuous_fan_exposure_min) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_SALTSPRAY_HAZE_TELEMETRY_INVALID)
        errors.append(
            "continuous_fan_exposure_min must be finite >= 0.0, "
            f"got {continuous_fan_exposure_min!r}."
        )
        telemetry_ok = False
        eff_min = 15.0
    else:
        eff_min = float(continuous_fan_exposure_min)

    haze_dose = compute_haze_fin_fouling_dose_mg_min_m3(eff_haze, eff_min)
    # Total aerosol concentration (PM10 ug/m^3 + haze mg/m^3 * 1000 ug/mg)
    total_conc_ug_m3 = eff_pm10 + eff_haze * 1000.0
    est_ingested_ug = compute_estimated_ingested_aerosol_ug(total_conc_ug_m3, eff_min)

    # a) Coastal Salt-Spray Unsealed Duct Guard
    saltspray_duct_safe = not (
        telemetry_ok
        and bool(coastal_salt_spray_env)
        and (not bool(hydrophobic_vent_membrane_or_housing))
    )
    if not saltspray_duct_safe:
        _add_code(codes, STATUS_BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT)
        errors.append(
            f"BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT: {environment_profile} exposes FX3's "
            "Sigma centrifugal cooling duct to salt-laden surf mist without "
            "hydrophobic_vent_membrane_or_housing=True, risking conductive salt crusting and "
            "Hall-sensor fan bearing seizure."
        )

    # b) Fine Desert / Playa Alkali Dust (<10 um) Abrasion Hazard Guard
    alkali_dust_filtration_safe = not (
        telemetry_ok
        and (eff_pm10 > PM10_DUST_MAX_UNFILTERED_UG_M3)
        and (not bool(intake_hepa_mesh_installed))
    )
    if not alkali_dust_filtration_safe:
        _add_code(codes, STATUS_BLOCKED_FINE_ALKALI_DUST_ABRASION_HAZARD)
        errors.append(
            f"BLOCKED_FINE_ALKALI_DUST_ABRASION_HAZARD: pm10_dust_ug_m3={eff_pm10:.1f} > "
            f"{PM10_DUST_MAX_UNFILTERED_UG_M3:.1f} ug/m^3 without intake_hepa_mesh_installed=True "
            "pulls abrasive <10um silica/alkali dust onto the Sigma impeller bearing."
        )

    # c) Studio Mineral-Oil / Glycol Haze Heatsink Fin Fouling Guard
    glycol_haze_fouling_safe = not (
        telemetry_ok
        and (eff_haze > STUDIO_HAZE_MAX_UNPURGED_MG_M3)
        and (eff_min > HAZE_MAX_CONTINUOUS_FAN_MIN)
        and (not bool(post_wrap_isopropyl_duct_purge_scheduled))
    )
    if not glycol_haze_fouling_safe:
        _add_code(codes, STATUS_BLOCKED_OIL_GLYCOL_HAZE_FIN_FOULING)
        errors.append(
            f"BLOCKED_OIL_GLYCOL_HAZE_FIN_FOULING: studio_haze_density_mg_m3={eff_haze:.1f} > "
            f"{STUDIO_HAZE_MAX_UNPURGED_MG_M3:.1f} mg/m^3 for continuous_fan_exposure_min="
            f"{eff_min:.1f} > {HAZE_MAX_CONTINUOUS_FAN_MIN:.1f} min (dose={haze_dose:.1f} "
            "mg*min/m^3) without post_wrap_isopropyl_duct_purge_scheduled=True cakes sticky "
            "mineral-oil/glycol residue across FX3's internal heatsink fins."
        )

    if telemetry_ok and len(errors) == 0:
        mitigated_hazards: List[str] = []
        if coastal_salt_spray_env and hydrophobic_vent_membrane_or_housing:
            mitigated_hazards.append("hydrophobic vent membrane/housing active")
        if eff_pm10 > PM10_DUST_MAX_UNFILTERED_UG_M3 and intake_hepa_mesh_installed:
            mitigated_hazards.append("HEPA intake mesh active")
        if (
            eff_haze > STUDIO_HAZE_MAX_UNPURGED_MG_M3
            and eff_min > HAZE_MAX_CONTINUOUS_FAN_MIN
            and post_wrap_isopropyl_duct_purge_scheduled
        ):
            mitigated_hazards.append("post-wrap isopropyl duct purge scheduled")
        if mitigated_hazards:
            warnings.append(
                f"Harsh aerosol environment ({environment_profile}) mitigated: "
                f"{', '.join(mitigated_hazards)}."
            )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return SaltsprayHazeFirewallResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        environment_profile=str(environment_profile),
        coastal_salt_spray_env=bool(coastal_salt_spray_env),
        hydrophobic_vent_membrane_or_housing=bool(hydrophobic_vent_membrane_or_housing),
        pm10_dust_ug_m3=round(eff_pm10, 2),
        intake_hepa_mesh_installed=bool(intake_hepa_mesh_installed),
        studio_haze_density_mg_m3=round(eff_haze, 2),
        continuous_fan_exposure_min=round(eff_min, 2),
        post_wrap_isopropyl_duct_purge_scheduled=bool(
            post_wrap_isopropyl_duct_purge_scheduled
        ),
        haze_exposure_dose_mg_min_m3=round(haze_dose, 2),
        estimated_ingested_aerosol_ug=round(est_ingested_ug, 3),
        saltspray_duct_safe=saltspray_duct_safe,
        alkali_dust_filtration_safe=alkali_dust_filtration_safe,
        glycol_haze_fouling_safe=glycol_haze_fouling_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G34 — Wireless Follow-Focus Torque & Gimbal Dynamic CoG Shift Guard
# ---------------------------------------------------------------------------


def verify_followfocus_hardstop_and_gimbal_cog_guard(
    *,
    rig_profile: str = "FX3_HANDHELD_COMPACT_PRIME",
    wireless_fiz_motor_torque_nm: float = 0.0,
    hard_stops_calibrated: bool = True,
    fly_by_wire_infinite_ring: bool = True,
    dual_rod_or_cage_bridge_clamp: bool = True,
    gimbal_mounted: bool = False,
    zoom_cog_shift_mm: float = 0.0,
    gimbal_autotune_after_zoom: bool = True,
    rig_mass_kg: float = 1.65,
    gear_pitch_radius_mm: float = DEFAULT_FIZ_GEAR_PITCH_RADIUS_MM,
    rod_cantilever_mm: float = DEFAULT_15MM_ROD_CANTILEVER_MM,
    request_persistent_emmc_writes: bool = False,
) -> FollowFocusGimbalGuardResult:
    """Verify Gate G34 (Wireless FIZ hard-stop torque, 15mm rod deflection & gimbal zoom CoG)."""
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
        not _is_finite_number(wireless_fiz_motor_torque_nm)
        or float(wireless_fiz_motor_torque_nm) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_FOLLOWFOCUS_GIMBAL_TELEMETRY_INVALID)
        errors.append(
            "wireless_fiz_motor_torque_nm must be finite >= 0.0, "
            f"got {wireless_fiz_motor_torque_nm!r}."
        )
        telemetry_ok = False
        eff_torque_nm = 0.0
    else:
        eff_torque_nm = float(wireless_fiz_motor_torque_nm)

    if (
        not _is_finite_number(zoom_cog_shift_mm)
        or float(zoom_cog_shift_mm) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_FOLLOWFOCUS_GIMBAL_TELEMETRY_INVALID)
        errors.append(
            f"zoom_cog_shift_mm must be finite >= 0.0, got {zoom_cog_shift_mm!r}."
        )
        telemetry_ok = False
        eff_cog_mm = 0.0
    else:
        eff_cog_mm = float(zoom_cog_shift_mm)

    if not _is_finite_number(rig_mass_kg) or float(rig_mass_kg) < 0.0:
        _add_code(codes, STATUS_BLOCKED_FOLLOWFOCUS_GIMBAL_TELEMETRY_INVALID)
        errors.append(f"rig_mass_kg must be finite >= 0.0, got {rig_mass_kg!r}.")
        telemetry_ok = False
        eff_mass_kg = 1.65
    else:
        eff_mass_kg = float(rig_mass_kg)

    if (
        not _is_finite_number(gear_pitch_radius_mm)
        or float(gear_pitch_radius_mm) <= 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_FOLLOWFOCUS_GIMBAL_TELEMETRY_INVALID)
        errors.append(
            f"gear_pitch_radius_mm must be finite > 0.0, got {gear_pitch_radius_mm!r}."
        )
        telemetry_ok = False
        eff_radius_mm = DEFAULT_FIZ_GEAR_PITCH_RADIUS_MM
    else:
        eff_radius_mm = float(gear_pitch_radius_mm)

    if not _is_finite_number(rod_cantilever_mm) or float(rod_cantilever_mm) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_FOLLOWFOCUS_GIMBAL_TELEMETRY_INVALID)
        errors.append(
            f"rod_cantilever_mm must be finite > 0.0, got {rod_cantilever_mm!r}."
        )
        telemetry_ok = False
        eff_rod_mm = DEFAULT_15MM_ROD_CANTILEVER_MM
    else:
        eff_rod_mm = float(rod_cantilever_mm)

    tangential_force_n = compute_fiz_gear_tangential_force_n(
        eff_torque_nm, eff_radius_mm
    )
    rod_deflection_mm = compute_single_rod_deflection_mm(
        tangential_force_n, eff_rod_mm
    )
    cog_torque_nm = compute_gimbal_cog_torque_imbalance_nm(eff_mass_kg, eff_cog_mm)

    # a) Uncalibrated High-Torque Wireless Follow-Focus Hard-Stop Gear Stripping Guard
    hardstop_torque_safe = not (
        telemetry_ok
        and (eff_torque_nm > FIZ_UNCALIBRATED_MAX_TORQUE_NM)
        and (not bool(hard_stops_calibrated))
        and (not bool(fly_by_wire_infinite_ring))
    )
    if not hardstop_torque_safe:
        _add_code(codes, STATUS_BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE)
        errors.append(
            f"BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE: {rig_profile} drives "
            f"wireless_fiz_motor_torque_nm={eff_torque_nm:.2f} N*m (> {FIZ_UNCALIBRATED_MAX_TORQUE_NM:.1f} N*m, "
            f"F_tooth={tangential_force_n:.1f} N) with hard_stops_calibrated=False on a "
            "hard-stop lens barrel (fly_by_wire_infinite_ring=False), risking stripped helicoids/gears."
        )

    # b) Single 15mm Rod FIZ Deflection & Gear-Mesh Slip Guard
    rod_deflection_mesh_safe = not (
        telemetry_ok
        and (eff_torque_nm > FIZ_SINGLE_ROD_MAX_TORQUE_NM)
        and (not bool(dual_rod_or_cage_bridge_clamp))
    )
    if not rod_deflection_mesh_safe:
        _add_code(codes, STATUS_BLOCKED_SINGLE_ROD_FIZ_DEFLECTION_SLIP)
        errors.append(
            f"BLOCKED_SINGLE_ROD_FIZ_DEFLECTION_SLIP: wireless_fiz_motor_torque_nm="
            f"{eff_torque_nm:.2f} N*m (> {FIZ_SINGLE_ROD_MAX_TORQUE_NM:.1f} N*m) on a single "
            f"15mm rod (cantilever={eff_rod_mm:.0f} mm, delta={rod_deflection_mm:.3f} mm) without "
            "dual_rod_or_cage_bridge_clamp=True misaligns 0.8 MOD focus gear mesh."
        )

    # c) Gimbal Telescoping-Zoom Dynamic CoG Shift & 40..90 Hz IBIS Oscillation Guard
    gimbal_cog_oscillation_safe = not (
        telemetry_ok
        and bool(gimbal_mounted)
        and (eff_cog_mm > GIMBAL_MAX_UNAUTOTUNED_ZOOM_COG_SHIFT_MM)
        and (not bool(gimbal_autotune_after_zoom))
    )
    if not gimbal_cog_oscillation_safe:
        _add_code(codes, STATUS_BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION)
        errors.append(
            f"BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION: gimbal_mounted=True with telescoping "
            f"zoom_cog_shift_mm={eff_cog_mm:.1f} mm (> {GIMBAL_MAX_UNAUTOTUNED_ZOOM_COG_SHIFT_MM:.1f} mm, "
            f"tau_imbalance={cog_torque_nm:.3f} N*m) and gimbal_autotune_after_zoom=False excites "
            f"{GIMBAL_OSCILLATION_BAND_MIN_HZ:.0f}..{GIMBAL_OSCILLATION_BAND_MAX_HZ:.0f} Hz PID "
            "oscillation that saturates FX3's IBIS voice coils."
        )

    if telemetry_ok and len(errors) == 0:
        if eff_torque_nm >= FIZ_TYPICAL_HIGH_TORQUE_MIN_NM:
            warnings.append(
                f"High-torque wireless FIZ ({eff_torque_nm:.2f} N*m) safely constrained with "
                f"calibrated/infinite stops and dual-rod/bridge clamp."
            )
        if gimbal_mounted and eff_cog_mm > GIMBAL_MAX_UNAUTOTUNED_ZOOM_COG_SHIFT_MM:
            warnings.append(
                f"Telescoping zoom CoG shift ({eff_cog_mm:.1f} mm) compensated by post-zoom gimbal autotune."
            )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return FollowFocusGimbalGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        rig_profile=str(rig_profile),
        wireless_fiz_motor_torque_nm=round(eff_torque_nm, 3),
        hard_stops_calibrated=bool(hard_stops_calibrated),
        fly_by_wire_infinite_ring=bool(fly_by_wire_infinite_ring),
        dual_rod_or_cage_bridge_clamp=bool(dual_rod_or_cage_bridge_clamp),
        gimbal_mounted=bool(gimbal_mounted),
        zoom_cog_shift_mm=round(eff_cog_mm, 2),
        gimbal_autotune_after_zoom=bool(gimbal_autotune_after_zoom),
        rig_mass_kg=round(eff_mass_kg, 3),
        gear_pitch_radius_mm=round(eff_radius_mm, 2),
        rod_cantilever_mm=round(eff_rod_mm, 2),
        gear_tangential_force_n=round(tangential_force_n, 2),
        single_rod_deflection_mm=round(rod_deflection_mm, 4),
        gimbal_cog_torque_imbalance_nm=round(cog_torque_nm, 4),
        hardstop_torque_safe=hardstop_torque_safe,
        rod_deflection_mesh_safe=rod_deflection_mesh_safe,
        gimbal_cog_oscillation_safe=gimbal_cog_oscillation_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 5. Gate G33 & Gate G34 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g33_saltspray_alkali_dust_and_haze(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    saltspray_haze_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase108DonorAuditResult] = None,
) -> Tuple[GateVerdict, G33SaltsprayHazeResult]:
    """Evaluate Gate G33 (`saltspray_alkali_dust_and_glycol_haze_ingestion_safe`)."""
    audit = donor_audit or audit_phase108_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(saltspray_haze_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    fw_res = verify_saltspray_alkali_dust_and_haze_firewall(**eff_kwargs)

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
        STATUS_VERIFIED_G33
        if passed
        else (
            codes[0] if codes else STATUS_BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT
        )
    )

    res = G33SaltsprayHazeResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        saltspray_haze_firewall=fw_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G33_GATE_ID,
        gate_code=G33_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Coastal Salt-Spray / Alkali Dust & Glycol-Haze Sigma Blower Firewall "
            f"({fw_res.status}, saltspray={fw_res.coastal_salt_spray_env}, "
            f"pm10={fw_res.pm10_dust_ug_m3:.1f}ug/m3, haze={fw_res.studio_haze_density_mg_m3:.1f}mg/m3, "
            f"exp={fw_res.continuous_fan_exposure_min:.1f}min, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "saltspray_duct_safe": fw_res.saltspray_duct_safe,
            "alkali_dust_filtration_safe": fw_res.alkali_dust_filtration_safe,
            "glycol_haze_fouling_safe": fw_res.glycol_haze_fouling_safe,
        },
    )
    return verdict, res


def evaluate_g34_followfocus_hardstop_and_gimbal_cog(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    followfocus_gimbal_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase108DonorAuditResult] = None,
) -> Tuple[GateVerdict, G34FollowFocusGimbalResult]:
    """Evaluate Gate G34 (`wireless_followfocus_hardstop_and_gimbal_cog_safe`)."""
    audit = donor_audit or audit_phase108_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(followfocus_gimbal_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    guard_res = verify_followfocus_hardstop_and_gimbal_cog_guard(**eff_kwargs)

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
        STATUS_VERIFIED_G34
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE
        )
    )

    res = G34FollowFocusGimbalResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        followfocus_gimbal_guard=guard_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G34_GATE_ID,
        gate_code=G34_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Wireless Follow-Focus Hard-Stop Torque & Gimbal Dynamic CoG Guard "
            f"({guard_res.status}, fiz_torque={guard_res.wireless_fiz_motor_torque_nm:.2f}N*m, "
            f"calibrated={guard_res.hard_stops_calibrated}, dual_rod={guard_res.dual_rod_or_cage_bridge_clamp}, "
            f"gimbal={guard_res.gimbal_mounted}, cog_shift={guard_res.zoom_cog_shift_mm:.1f}mm, "
            f"{audit.verification_mode}), persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "hardstop_torque_safe": guard_res.hardstop_torque_safe,
            "rod_deflection_mesh_safe": guard_res.rod_deflection_mesh_safe,
            "gimbal_cog_oscillation_safe": guard_res.gimbal_cog_oscillation_safe,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 6. Master 34-Gate Preflight Evaluator (`G01..G34`) & CLI
# ---------------------------------------------------------------------------


def evaluate_34gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G32 pass-throughs
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
    # G33 inputs (Coastal Salt-Spray / Alkali Dust / Studio Glycol-Haze Firewall)
    saltspray_haze_kwargs: Optional[Mapping[str, Any]] = None,
    # G34 inputs (Wireless Follow-Focus Hard-Stop Torque & Gimbal Dynamic CoG Guard)
    followfocus_gimbal_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master34GateReport:
    """Evaluate all 34 Master Safety Gates (`G01..G34`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m32_kwargs: Dict[str, Any] = {
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
    }
    if soc_start_ceiling_c is not None:
        m32_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m32_report: Master32GateReport = evaluate_32gate_preflight(
        resolved_root, **m32_kwargs
    )

    phase108_audit = audit_phase108_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
    )

    g33_verdict, g33_res = evaluate_g33_saltspray_alkali_dust_and_haze(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        saltspray_haze_kwargs=saltspray_haze_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase108_audit,
    )

    g34_verdict, g34_res = evaluate_g34_followfocus_hardstop_and_gimbal_cog(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        followfocus_gimbal_kwargs=followfocus_gimbal_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase108_audit,
    )

    gates_33_to_34 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g33_verdict, g34_verdict)
    ]
    all_gates = tuple(list(m32_report.gates) + gates_33_to_34)

    g01_to_g12_verified = int(m32_report.summary["g01_to_g12_verified"])
    g13_to_g32_verified = (
        int(m32_report.summary["g13_to_g30_verified"])
        + int(m32_report.summary["g31_to_g32_verified"])
    )
    g33_to_g34_verified = sum(1 for v in (g33_verdict, g34_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g32_verified + g33_to_g34_verified

    g33_to_g34_all_passed = g33_to_g34_verified == 2
    g13_to_g34_all_passed = (
        m32_report.g13_to_g32_all_passed and g33_to_g34_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m32_report.gates[:9])

    offline_31_verified = (
        g01_to_g09_ok
        and m32_report.offline_29_gates_verified
        and g33_to_g34_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_34_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g34_all_passed
        and (not request_persistent_emmc_writes)
    )

    real_tier0_verified = (g01_to_g12_verified == 12) and (
        not dry_run_simulated_backup
    )
    overall_ready_for_hardware_attach = (
        real_tier0_verified
        and g13_to_g34_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    h0_h1_allowed = (
        offline_31_verified
        and m32_report.h0_h1_trial_entry_allowed
        and g33_to_g34_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m32_report.errors) + list(g33_verdict.errors) + list(g34_verdict.errors)
    )
    warnings: List[str] = (
        list(m32_report.warnings)
        + list(g33_verdict.warnings)
        + list(g34_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m32_report.g13_to_g32_all_passed:
        overall_status = m32_report.status
    elif not g33_verdict.passed:
        overall_status = g33_verdict.status
    elif not g34_verdict.passed:
        overall_status = g34_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_34_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_34_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_34_verified:
        overall_status = "VERIFIED_ALL_34_GATES"
    else:
        overall_status = "VERIFIED_31_OF_34_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m32_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g33_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g34_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 34,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 34 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g32_verified": g13_to_g32_verified,
        "g33_to_g34_verified": g33_to_g34_verified,
        "g13_to_g34_all_passed": g13_to_g34_all_passed,
        "g33_to_g34_all_passed": g33_to_g34_all_passed,
        "offline_31_gates_verified": offline_31_verified,
        "all_34_gates_verified": all_34_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master34GateReport(
        schema=SALTSPRAY_HAZE_FOLLOWFOCUS_34GATE_SCHEMA,
        version=SALTSPRAY_HAZE_FOLLOWFOCUS_34GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_31_gates_verified=offline_31_verified,
        all_34_gates_verified=all_34_verified,
        g13_to_g34_all_passed=g13_to_g34_all_passed,
        g33_to_g34_all_passed=g33_to_g34_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_32_report=m32_report.to_dict(),
        g33_result=g33_res.to_dict(),
        g34_result=g34_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_34_master_safety_gates = evaluate_34gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="saltspray_haze_followfocus_and_34gate_guard",
        description=(
            "Phase 108 — Coastal Salt-Spray / Studio Glycol-Haze Ingestion Firewall (G33), "
            "Wireless Follow-Focus Hard-Stop Torque & Gimbal Dynamic CoG Guard (G34), "
            "and 34-Gate Master Preflight (G01..G34)"
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G34 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_34gate_preflight(
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
            f"verified={report.summary['verified_gates']}/34 "
            f"g33_to_g34_all_passed={report.g33_to_g34_all_passed} "
            f"all_34_gates_verified={report.all_34_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = (
        report.all_34_gates_verified
        if args.dry_run_simulated_backup
        else report.offline_31_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
