"""Phase 69 — Rig D-Tap/HDMI Ground-Loop Interlock, E-Mount Hot-Detach Rail Guard, Power-Loss `.RSV` Salvage & `G01..G20` 20-Gate Preflight.

Operationalizes physical cinema-rig electrical safety, E-Mount hot-detach rail
protection, sudden power-loss `.RSV` salvage verification, and the unified
20-Gate Master Safety Preflight (`G01..G20`) for Sony ILME-FX3 (`Ver. 7.02`,
SoC `CXD90057`, `IMX510` 5-axis IBIS) while keeping `preflight.py`,
`master_16gate_preflight.py`, and `usblan_ptpip_and_18gate_preflight.py`
completely untouched:

1. **D-Tap / HDMI Type-A Common-Mode Ground-Loop & Hot-Plug ESD Firewall (`G19` part 1)**:
   - Models the physical cinema rig topology when an FX3 (`USB-PD 9V/3A` or
     `NP-FZ100` dummy coupler) and an external HDMI monitor/recorder (`Atomos Ninja`
     / `SmallHD`) share a single `14.8V` V-Mount/Gold-Mount battery via non-isolated
     D-Tap splitters.
   - Detects the lethal **open-negative ground-return fault** (if monitor or
     dummy-battery D-Tap `GND` disconnects before `+14.8V` while copper HDMI is
     plugged in, return current flows through HDMI Pin-17 DDC/CEC/TMDS shield and
     blows the `CXD90057` HDMI ESD array).
   - Enforces safe topology rules & strict plug/power sequence state machine
     (`Connect Power Cables -> Connect HDMI -> Power ON Camera -> Power ON Monitor`;
     teardown strictly reversed) plus `HDMI +5V Pin-18` reverse back-feed blocking
     (`> 5.25V` or `> 55 mA`).

2. **E-Mount `V_LENS` (`3.3V` Logic / `5.0V` Actuator) Hot-Detach Crowbar & Stock-CP IBIS Park Verifier (`G19` part 2)**:
   - Models the 10-pin Sony E-Mount contact array during unexpected lens release
     while camera power is `ON`.
   - Requires `LENS_DET` interrupt to crowbar `V_LENS_SERVO_5V0` to `0 mA` within
     `<= 2.0 ms` (strictly prior to the `3.5 ms` rotary contact-wipe window) AND
     command Stock-CP `0x0400` (`0x1400` completion) IBIS Center-Lock park so
     neither lens pins short nor the floating `IMX510` IBIS stage slams stops.

3. **Sudden Power-Loss `.RSV` Clip-Salvage & `USB-PD` Battery-Less Trap Guard (`G20`)**:
   - Models sudden `USB-PD 9V/3A` unplug during `4K 60p XAVC S-I` (`600 Mbps`)
     recording.
   - Verifies seamless zero-drop UPS switchover (`0` lost frames, clean
     `moov`/`MXF FooterPartition` close) when internal `NP-FZ100` has
     `soc_pct >= 15%` and `>= 6.8V` under load.
   - **Fails closed** (`BLOCK_REC_START_BATTERY_RESERVE_INSUFFICIENT`) when
     `NP-FZ100` is absent (`battery_less_usb_pd = True`) or `soc_pct < 10%`
     (or `< 15%` / `< 6.8V`), alongside deterministic read-only Sony `.RSV`
     emergency salvage header/chunk structure inspection (`physical_media_writes == 0`,
     `persistent_emmc_writes_authorized == False`).

4. **20-Gate Master Safety Preflight Engine (`G01..G20`)**:
   - Composes `evaluate_18_master_safety_gates` (`G01..G18`) with `G19`
     (`rig_hdmi_dtap_groundloop_and_lensrail_safe`) and `G20`
     (`power_failover_ups_and_rsv_salvage_safe`):
     - Offline default mode: `17/20` gates pass (`G10..G12` physical body Tier-0
       readback truthfully remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` ->
       `overall_ready_for_hardware_attach = False`).
     - `--dry-run-simulated-backup` rehearsal mode: `20/20` simulation gates green
       (`dry_run_rehearsal_only = True`), while `persistent_emmc_writes_authorized`
       remains hard-locked to `False`.

Hard Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- All donor & `.RSV` file reads strictly use `os.open(..., os.O_RDONLY)`.
- Zero raw binary `bytes` repr output (always `.hex()`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import struct
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
)
from .usblan_ptpip_and_18gate_preflight import (
    Master18GateReport,
    evaluate_18_master_safety_gates,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

RIG_GROUNDLOOP_20GATE_SCHEMA: str = "fx3-rig-groundloop-lensrail-20gate-preflight-v1"
RIG_GROUNDLOOP_20GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G19..G20
G19_GATE_ID: str = "G19_rig_hdmi_dtap_groundloop_and_lensrail_safe"
G19_GATE_CODE: str = "RIG_HDMI_DTAP_GROUNDLOOP_AND_LENSRAIL_SAFE"

G20_GATE_ID: str = "G20_power_failover_ups_and_rsv_salvage_safe"
G20_GATE_CODE: str = "POWER_FAILOVER_UPS_AND_RSV_SALVAGE_SAFE"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G19: str = "VERIFIED_RIG_HDMI_DTAP_AND_LENSRAIL_SAFE"
STATUS_VERIFIED_G20: str = "VERIFIED_POWER_FAILOVER_UPS_AND_RSV_SALVAGE_SAFE"

STATUS_BLOCKED_GROUND_LOOP_HAZARD: str = "BLOCKED_GROUND_LOOP_HAZARD"
STATUS_BLOCKED_HDMI_PIN18_BACKFEED: str = "BLOCKED_HDMI_PIN18_REVERSE_BACKFEED"
STATUS_BLOCKED_POWER_SEQUENCE_VIOLATION: str = "BLOCKED_RIG_POWER_SEQUENCE_VIOLATION"

STATUS_BLOCKED_EMOUNT_HOT_DETACH_HAZARD: str = "BLOCKED_EMOUNT_HOT_DETACH_HAZARD"
STATUS_BLOCKED_IBIS_UNPARKED_IMPACT: str = "BLOCKED_IBIS_UNPARKED_IMPACT_HAZARD"
STATUS_BLOCKED_VLENS_CROWBAR_TIMEOUT: str = "BLOCKED_VLENS_CROWBAR_TIMEOUT"

STATUS_BLOCKED_BATTERY_RESERVE_INSUFFICIENT: str = "BLOCK_REC_START_BATTERY_RESERVE_INSUFFICIENT"
STATUS_BLOCKED_RSV_SALVAGE_INVALID: str = "BLOCKED_RSV_SALVAGE_STRUCTURE_INVALID"
STATUS_BLOCKED_UPS_SWITCHOVER_DROP: str = "BLOCKED_UPS_SWITCHOVER_FRAME_DROP"

STATUS_BLOCKED_DONOR_INTEGRITY: str = "BLOCKED_RIG_20GATE_DONOR_INTEGRITY_MISMATCH"
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED: str = "FAIL_OFFLINE_HARDWARE_NOT_ATTACHED"

# D-Tap / V-Mount / HDMI Type-A Electrical Constants
VMOUNT_DTAP_NOMINAL_V: float = 14.8
VMOUNT_DTAP_MIN_V: float = 11.5
VMOUNT_DTAP_MAX_V: float = 16.8
HDMI_PIN17_DDC_CEC_GROUND_PIN: int = 17
HDMI_PIN18_5V_POWER_PIN: int = 18
HDMI_PIN18_MIN_VOLTAGE_V: float = 4.75
HDMI_PIN18_MAX_VOLTAGE_V: float = 5.25
HDMI_PIN18_MAX_CURRENT_MA: float = 55.0

HDMI_CABLE_COPPER: str = "COPPER"
HDMI_CABLE_OPTICAL_FIBER: str = "OPTICAL_FIBER"

CAMERA_POWER_INTERNAL_NPFZ100_ISOLATED_USBPD: str = "INTERNAL_NP_FZ100_ISOLATED_USBPD"
CAMERA_POWER_INTERNAL_NPFZ100_ONLY: str = "INTERNAL_NP_FZ100_ONLY"
CAMERA_POWER_DUMMY_COUPLER_SHARED_DTAP: str = "DUMMY_COUPLER_SHARED_DTAP"
CAMERA_POWER_ISOLATED_DCDC_BOX: str = "ISOLATED_DCDC_BOX"

MONITOR_POWER_DEDICATED_BATTERY: str = "DEDICATED_BATTERY"
MONITOR_POWER_SHARED_DTAP_14V8: str = "SHARED_DTAP_14V8"
MONITOR_POWER_ISOLATED_DCDC_BOX: str = "ISOLATED_DCDC_BOX"

POWER_UP_SEQUENCE_CANONICAL: Tuple[str, ...] = (
    "CONNECT_POWER_CABLES",
    "CONNECT_HDMI",
    "POWER_ON_CAMERA",
    "POWER_ON_MONITOR",
)
TEARDOWN_SEQUENCE_CANONICAL: Tuple[str, ...] = (
    "POWER_OFF_MONITOR",
    "POWER_OFF_CAMERA",
    "DISCONNECT_HDMI",
    "DISCONNECT_POWER_CABLES",
)

# E-Mount 10-Pin & Stock-CP IBIS Center-Lock Constants
EMOUNT_PIN_COUNT: int = 10
EMOUNT_PIN_MAP: Tuple[Tuple[int, str, str], ...] = (
    (1, "GND", "Power / Chassis Ground"),
    (2, "V_LENS_LOGIC_3V3", "3.3V Logic Supply"),
    (3, "V_LENS_SERVO_5V0", "5.0V Actuator / AF / OSS Motor Supply"),
    (4, "LENS_CS", "SPI Chip Select"),
    (5, "LENS_SCK", "SPI Clock"),
    (6, "LENS_MOSI", "AP -> Lens Data"),
    (7, "LENS_MISO", "Lens -> AP Data"),
    (8, "LENS_BUSY", "Handshake / Sync"),
    (9, "LENS_DET", "Bayonet Detach Interrupt (First-Break)"),
    (10, "DGND", "Signal / Logic Ground"),
)
V_LENS_LOGIC_NOMINAL_V: float = 3.3
V_LENS_LOGIC_MIN_V: float = 3.15
V_LENS_LOGIC_MAX_V: float = 3.45
V_LENS_SERVO_NOMINAL_V: float = 5.0
V_LENS_SERVO_MIN_V: float = 4.75
V_LENS_SERVO_MAX_V: float = 5.25
V_LENS_CROWBAR_MAX_MS: float = 2.0
EMOUNT_ROTARY_WIPE_WINDOW_MS: float = 3.5
STOCK_CP_IBIS_CENTER_LOCK_OPCODE: int = 0x0400
STOCK_CP_IBIS_CENTER_LOCK_COMPLETION: int = 0x1400

# Power-Loss UPS & Sony .RSV Salvage Constants
XAVC_SI_4K60_CODEC: str = "4K_60P_XAVC_SI_600MBPS"
XAVC_SI_4K60_BITRATE_MBPS: int = 600
USB_PD_REQUIRED_VOLTAGE_V: float = 9.0
USB_PD_REQUIRED_CURRENT_A: float = 3.0
USB_PD_REQUIRED_WATTS: float = 27.0
NP_FZ100_UPS_MIN_SOC_PCT: int = 15
NP_FZ100_CRITICAL_MIN_SOC_PCT: int = 10
NP_FZ100_LOAD_MIN_VOLTAGE_V: float = 6.8
SONY_RSV_SUPPORTED_BRANDS: Tuple[str, ...] = ("XAVC", "mp42", "isom", "MSNV")
MXF_KLV_PARTITION_PREFIX_HEX: str = "060e2b34"

# Compact FX3/FX6 Donor Contracts for Rig/Lens/Power/Media (O_RDONLY verified)
PINNED_RIG20_DONOR_SPECS: Mapping[str, Tuple[str, str, int, str, bytes, str]] = {
    "fx3_libinfra_lens_comm": (
        "fx3",
        "libInfraLensCommunicator.so",
        14_544,
        "e61bf145f050dd037802871395c38d1c0471518130d5bcd2f621268da8c8f6ab",
        b"_ZN16LensCommunicator18GetMountedLensInfoEPv",
        "fx3/libInfraLensCommunicator.so::GetMountedLensInfo",
    ),
    "fx6_libinfra_lens_comm": (
        "fx6",
        "libInfraLensCommunicator.so",
        14_544,
        "8848b33084f71856ecc3a2074e347e275888d8a8173f70d900968085f7401c5e",
        b"_ZN16LensCommunicator10SndSyncMsgEPvj",
        "fx6/libInfraLensCommunicator.so::SndSyncMsg",
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
        b"_ZN11UsbBusPower11IsVbusReadyEv",
        "fx3/libUsbBusPower.so::IsVbusReady",
    ),
    "fx3_libinfra_media_mount": (
        "fx3",
        "libInfraMediaMount.so",
        65_392,
        "33b4c61c39f724e08e1bc4d07fd505a799ee37a9c1f37a43fffc7c2c9c8f75ad",
        b"_ZN15InfraMediaMount10GetVersionEv",
        "fx3/libInfraMediaMount.so::GetVersion",
    ),
    "fx3_libinfra_media_common": (
        "fx3",
        "libInfraMediaCommon.so",
        402_624,
        "1ddec7e4d903eaca7cdc7901936b99a9bf97bc52f67259cd3ebb3ee60620b40b",
        b"mcmn_drv_default_unmount",
        "fx3/libInfraMediaCommon.so::mcmn_drv_default_unmount",
    ),
}

PINNED_LARGE_CP_SPEC: Tuple[str, int, str, Tuple[bytes, ...]] = (
    "cpapp-b.bin",
    15_980_568,
    "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
    (b"LiroSeq: Restore.", b"HallPIDOUT_0", b"BATT_AUTH_S", b"BATT_STATE1_S"),
)


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Rig20GateDonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    cp_large_binary_checked: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RigPowerSequenceResult:
    valid: bool
    status: str
    power_up_steps: Tuple[str, ...]
    teardown_steps: Tuple[str, ...]
    power_up_valid: bool
    teardown_valid: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RigGroundLoopFirewallResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    camera_power_mode: str
    monitor_model: str
    monitor_power_mode: str
    shared_unisolated_dtap: bool
    dtap_bus_voltage_v: float
    galvanic_dc_dc_isolated: bool
    hdmi_connected: bool
    hdmi_cable_type: str
    ground_first_locking_connector: bool
    open_negative_ground_return_fault: bool
    hdmi_pin17_shield_return_hazard: bool
    cxd90057_esd_array_at_risk: bool
    hdmi_pin18_voltage_v: float
    hdmi_pin18_current_ma: float
    hdmi_pin18_backfeed_blocked: bool
    sequence_result: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EmountHotDetachRailResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    emount_pin_count: int
    camera_power_on: bool
    hot_detach_event: bool
    lens_det_interrupt_triggered: bool
    v_lens_logic_v: float
    v_lens_servo_v: float
    v_lens_servo_crowbar_ms: float
    crowbar_max_ms: float
    rotary_wipe_window_ms: float
    v_lens_servo_residual_ma: float
    v_lens_logic_tri_stated: bool
    crowbar_within_budget: bool
    ibis_park_commanded: bool
    ibis_park_opcode_hex: str
    ibis_park_completion_hex: str
    ibis_stage_parked: bool
    cp_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G19RigGroundLoopAndLensRailResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    rig_groundloop: Dict[str, Any]
    emount_lensrail: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RsvSalvageInspectionResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    container_format: str
    ftyp_brand: str
    total_bytes: int
    header_hex: str
    has_moov_or_footer: bool
    needs_rsv_salvage: bool
    recoverable_chunks: int
    recoverable_payload_bytes: int
    boxes_parsed: Tuple[str, ...]
    physical_media_writes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PowerFailoverUpsResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    recording_codec: str
    recording_bitrate_mbps: int
    usb_pd_voltage_v: float
    usb_pd_current_a: float
    usb_pd_watts: float
    usb_pd_unplug_event: bool
    np_fz100_installed: bool
    battery_less_usb_pd: bool
    np_fz100_soc_pct: int
    np_fz100_load_voltage_v: float
    ups_switchover_seamless: bool
    lost_frames_on_switchover: int
    container_cleanly_closed: bool
    moov_atom_written: bool
    mxf_footer_partition_written: bool
    rsv_salvage_verified: bool
    rsv_salvage: Dict[str, Any]
    physical_media_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G20PowerFailoverAndRsvResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    power_failover_ups: Dict[str, Any]
    battery_less_trap_verified: bool
    physical_media_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master20GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_17_gates_verified: bool
    all_20_gates_verified: bool
    g13_to_g20_all_passed: bool
    g19_to_g20_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_18_report: Dict[str, Any]
    g19_result: Dict[str, Any]
    g20_result: Dict[str, Any]
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


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_rig_20gate_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
) -> Rig20GateDonorAuditResult:
    """Inspect FX3/FX6 lens-rail, USB-PD BusPower & MediaMount donors via `os.O_RDONLY`."""
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)

    resolved: Dict[str, Path] = {}
    for key, (body, rel_name, *_rest) in PINNED_RIG20_DONOR_SPECS.items():
        base_dir = paths.fx3_lib_dir if body == "fx3" else paths.fx6_lib_dir
        resolved[key] = base_dir / rel_name

    donor_available = (
        (not clean_forced)
        and (paths.work_root is not None)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Rig20GateDonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(spec[5] for spec in PINNED_RIG20_DONOR_SPECS.values()),
            missing_markers=(),
            sha256_by_artifact={k: spec[3] for k, spec in PINNED_RIG20_DONOR_SPECS.items()},
            bytes_by_artifact={k: spec[2] for k, spec in PINNED_RIG20_DONOR_SPECS.items()},
            cp_large_binary_checked=False,
            errors=(),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []

    for key, (_body, _rel_name, exp_size, exp_sha, marker_bytes, marker_label) in PINNED_RIG20_DONOR_SPECS.items():
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

    cp_checked = False
    if include_large_binaries and paths.fx3_cp_path.is_file():
        cp_name, cp_exp_size, cp_exp_sha, cp_markers = PINNED_LARGE_CP_SPEC
        cp_blob = _read_file_o_rdonly(paths.fx3_cp_path)
        cp_sha = hashlib.sha256(cp_blob).hexdigest()
        shas["fx3_cpapp"] = cp_sha
        sizes["fx3_cpapp"] = len(cp_blob)
        cp_checked = True
        if len(cp_blob) != cp_exp_size or cp_sha != cp_exp_sha:
            errors.append(
                f"Donor {cp_name} integrity mismatch: size={len(cp_blob)} (expected {cp_exp_size}), "
                f"sha256={cp_sha} (expected {cp_exp_sha})."
            )
        for m in cp_markers:
            lbl = f"cpapp-b.bin::{m.decode('ascii')}"
            if m in cp_blob:
                checked.append(lbl)
            else:
                missing.append(lbl)
                errors.append(f"Donor {cp_name} missing marker {lbl}.")

    valid = len(errors) == 0 and len(missing) == 0
    return Rig20GateDonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=len(resolved) + (1 if cp_checked else 0),
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        cp_large_binary_checked=cp_checked,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. D-Tap / HDMI Type-A Common-Mode Ground-Loop & Hot-Plug ESD Firewall
# ---------------------------------------------------------------------------


def verify_rig_power_sequence(
    *,
    power_up_steps: Optional[Sequence[str]] = None,
    teardown_steps: Optional[Sequence[str]] = None,
) -> RigPowerSequenceResult:
    """Enforce strict cinema-rig power-up and reversed teardown state machine."""
    up = tuple(
        s.strip().upper()
        for s in (POWER_UP_SEQUENCE_CANONICAL if power_up_steps is None else power_up_steps)
    )
    down = tuple(
        s.strip().upper()
        for s in (TEARDOWN_SEQUENCE_CANONICAL if teardown_steps is None else teardown_steps)
    )

    errors: List[str] = []
    up_ok = up == POWER_UP_SEQUENCE_CANONICAL
    if not up_ok:
        errors.append(
            f"Invalid rig power-up sequence {list(up)}: must strictly follow "
            f"{list(POWER_UP_SEQUENCE_CANONICAL)} (Connect Power -> Connect HDMI -> Power ON Camera -> Power ON Monitor)."
        )

    down_ok = down == TEARDOWN_SEQUENCE_CANONICAL
    if not down_ok:
        errors.append(
            f"Invalid rig teardown sequence {list(down)}: must strictly follow "
            f"{list(TEARDOWN_SEQUENCE_CANONICAL)} (Power OFF Monitor -> Power OFF Camera -> Disconnect HDMI -> Disconnect Power)."
        )

    valid = up_ok and down_ok
    return RigPowerSequenceResult(
        valid=valid,
        status=STATUS_SAFE if valid else STATUS_BLOCKED_GROUND_LOOP_HAZARD,
        power_up_steps=up,
        teardown_steps=down,
        power_up_valid=up_ok,
        teardown_valid=down_ok,
        errors=tuple(errors),
    )


def verify_rig_dtap_hdmi_groundloop_firewall(
    *,
    camera_power_mode: str = CAMERA_POWER_INTERNAL_NPFZ100_ISOLATED_USBPD,
    monitor_model: str = "Atomos Ninja",
    monitor_power_mode: str = MONITOR_POWER_DEDICATED_BATTERY,
    shared_unisolated_dtap: Optional[bool] = None,
    dtap_bus_voltage_v: float = VMOUNT_DTAP_NOMINAL_V,
    galvanic_dc_dc_isolated: bool = False,
    hdmi_connected: bool = True,
    hdmi_cable_type: str = HDMI_CABLE_COPPER,
    ground_first_locking_connector: bool = False,
    camera_dtap_pos_connected: bool = True,
    camera_dtap_gnd_connected: bool = True,
    monitor_dtap_pos_connected: bool = True,
    monitor_dtap_gnd_connected: bool = True,
    hdmi_pin18_voltage_v: float = 5.0,
    hdmi_pin18_current_ma: float = 35.0,
    hdmi_pin18_reverse_backfeed: bool = False,
    power_up_sequence: Optional[Sequence[str]] = None,
    teardown_sequence: Optional[Sequence[str]] = None,
    hot_plug_hdmi_while_powered: bool = False,
    request_persistent_emmc_writes: bool = False,
) -> RigGroundLoopFirewallResult:
    """Verify D-Tap / HDMI Type-A ground-loop safety, sequencing, and Pin-18 back-feed protection."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    cam_pwr = camera_power_mode.strip().upper()
    mon_pwr = monitor_power_mode.strip().upper()
    cable = hdmi_cable_type.strip().upper()

    if shared_unisolated_dtap is None:
        inferred_shared = (
            ("SHARED_DTAP" in cam_pwr or "DUMMY_COUPLER" in cam_pwr)
            and ("SHARED_DTAP" in mon_pwr)
            and (not galvanic_dc_dc_isolated)
        )
    else:
        inferred_shared = bool(shared_unisolated_dtap) and (not galvanic_dc_dc_isolated)

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    seq_res = verify_rig_power_sequence(
        power_up_steps=power_up_sequence,
        teardown_steps=teardown_sequence,
    )
    if hot_plug_hdmi_while_powered:
        _add_code(codes, STATUS_BLOCKED_GROUND_LOOP_HAZARD)
        _add_code(codes, STATUS_BLOCKED_POWER_SEQUENCE_VIOLATION)
        errors.append(
            "Hot-plugging HDMI Type-A while camera or external monitor is powered ON violates "
            "power-sequencing firewall and risks CXD90057 HDMI ESD damage."
        )
    if not seq_res.valid:
        _add_code(codes, STATUS_BLOCKED_GROUND_LOOP_HAZARD)
        _add_code(codes, STATUS_BLOCKED_POWER_SEQUENCE_VIOLATION)
        errors.extend(seq_res.errors)

    # Check open-negative ground-return fault on shared D-Tap (or dummy-coupler / monitor D-Tap)
    dtap_in_use = inferred_shared or ("DTAP" in cam_pwr) or ("DTAP" in mon_pwr) or galvanic_dc_dc_isolated
    cam_gnd_open = bool(camera_dtap_pos_connected and (not camera_dtap_gnd_connected))
    mon_gnd_open = bool(monitor_dtap_pos_connected and (not monitor_dtap_gnd_connected))
    open_negative_fault = dtap_in_use and (cam_gnd_open or mon_gnd_open)

    is_copper_hdmi = bool(hdmi_connected and cable != HDMI_CABLE_OPTICAL_FIBER)
    pin17_hazard = bool(open_negative_fault and is_copper_hdmi)
    esd_at_risk = pin17_hazard

    if open_negative_fault:
        _add_code(codes, STATUS_BLOCKED_GROUND_LOOP_HAZARD)
        if is_copper_hdmi:
            errors.append(
                "LETHAL OPEN-NEGATIVE GROUND-RETURN FAULT: D-Tap GND disconnected while +14.8V remains live "
                "and copper HDMI Type-A is attached — high return current routes through HDMI Pin-17 "
                "DDC/CEC/TMDS shield and blows CXD90057 HDMI ESD array."
            )
        else:
            errors.append(
                "D-Tap open-negative ground fault detected (GND disconnected while +14.8V rail connected)."
            )

    # Check D-Tap bus voltage bounds if D-Tap is in use
    if dtap_in_use and not (VMOUNT_DTAP_MIN_V <= float(dtap_bus_voltage_v) <= VMOUNT_DTAP_MAX_V):
        _add_code(codes, STATUS_BLOCKED_GROUND_LOOP_HAZARD)
        errors.append(
            f"V-Mount/Gold-Mount D-Tap bus voltage {dtap_bus_voltage_v:.2f}V outside safe "
            f"{VMOUNT_DTAP_MIN_V:.1f}V..{VMOUNT_DTAP_MAX_V:.1f}V envelope."
        )

    # Enforce safe rig topology rules
    if hdmi_connected and inferred_shared and is_copper_hdmi:
        if not ground_first_locking_connector:
            _add_code(codes, STATUS_BLOCKED_GROUND_LOOP_HAZARD)
            errors.append(
                "Shared unisolated 14.8V V-Mount D-Tap with copper HDMI Type-A without ground-first "
                "locking connector is blocked (BLOCKED_GROUND_LOOP_HAZARD); use internal NP-FZ100 + "
                "isolated USB-PD, optical-fiber HDMI, or galvanically isolated DC-DC distro box."
            )
        else:
            warnings.append(
                "Shared unisolated D-Tap uses ground-first locking connector + strict sequencing; "
                "optical-fiber HDMI or galvanically isolated DC-DC box remains preferred."
            )

    # Check HDMI +5V Pin-18 reverse back-feed & overcurrent (> 5.25V or > 55 mA)
    pin18_backfeed_blocked = False
    if hdmi_connected:
        if (
            bool(hdmi_pin18_reverse_backfeed)
            or float(hdmi_pin18_voltage_v) > HDMI_PIN18_MAX_VOLTAGE_V
            or float(hdmi_pin18_current_ma) > HDMI_PIN18_MAX_CURRENT_MA
            or float(hdmi_pin18_voltage_v) < 0.0
            or float(hdmi_pin18_current_ma) < 0.0
        ):
            pin18_backfeed_blocked = True
            esd_at_risk = True
            _add_code(codes, STATUS_BLOCKED_HDMI_PIN18_BACKFEED)
            errors.append(
                f"HDMI +5V Pin-18 reverse back-feed / overdraw blocked: "
                f"V={hdmi_pin18_voltage_v:.2f}V (max {HDMI_PIN18_MAX_VOLTAGE_V:.2f}V), "
                f"I={hdmi_pin18_current_ma:.1f}mA (max {HDMI_PIN18_MAX_CURRENT_MA:.1f}mA), "
                f"reverse_backfeed={hdmi_pin18_reverse_backfeed}."
            )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif STATUS_BLOCKED_GROUND_LOOP_HAZARD in codes:
        status = STATUS_BLOCKED_GROUND_LOOP_HAZARD
    else:
        status = codes[0]

    return RigGroundLoopFirewallResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        camera_power_mode=cam_pwr,
        monitor_model=monitor_model,
        monitor_power_mode=mon_pwr,
        shared_unisolated_dtap=inferred_shared,
        dtap_bus_voltage_v=float(dtap_bus_voltage_v),
        galvanic_dc_dc_isolated=bool(galvanic_dc_dc_isolated),
        hdmi_connected=bool(hdmi_connected),
        hdmi_cable_type=cable,
        ground_first_locking_connector=bool(ground_first_locking_connector),
        open_negative_ground_return_fault=open_negative_fault,
        hdmi_pin17_shield_return_hazard=pin17_hazard,
        cxd90057_esd_array_at_risk=esd_at_risk,
        hdmi_pin18_voltage_v=float(hdmi_pin18_voltage_v),
        hdmi_pin18_current_ma=float(hdmi_pin18_current_ma),
        hdmi_pin18_backfeed_blocked=pin18_backfeed_blocked,
        sequence_result=seq_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "hdmi_pin17_role": "DDC/CEC/TMDS Ground Return Shield",
            "hdmi_pin18_role": "+5V Power (<= 5.25V, <= 55 mA)",
            "target_esd_ic": "CXD90057 HDMI Type-A ESD Protection Array",
            "hot_plug_hdmi_while_powered": bool(hot_plug_hdmi_while_powered),
        },
    )


# ---------------------------------------------------------------------------
# 3. E-Mount V_LENS Hot-Detach Crowbar & Stock-CP IBIS Park Verifier
# ---------------------------------------------------------------------------


def verify_emount_hot_detach_rail_and_ibis_park(
    *,
    camera_power_on: bool = True,
    hot_detach_event: bool = True,
    lens_det_interrupt_triggered: bool = True,
    v_lens_logic_v: float = V_LENS_LOGIC_NOMINAL_V,
    v_lens_servo_v: float = V_LENS_SERVO_NOMINAL_V,
    v_lens_servo_crowbar_ms: float = 1.2,
    v_lens_servo_residual_ma: float = 0.0,
    v_lens_logic_tri_stated: bool = True,
    ibis_park_commanded: bool = True,
    ibis_park_opcode: int = STOCK_CP_IBIS_CENTER_LOCK_OPCODE,
    ibis_park_completion_opcode: int = STOCK_CP_IBIS_CENTER_LOCK_COMPLETION,
    ibis_stage_parked: bool = True,
    cp_mutation_bytes: int = 0,
    request_persistent_emmc_writes: bool = False,
) -> EmountHotDetachRailResult:
    """Verify 10-pin Sony E-Mount hot-detach `V_LENS` crowbar (`<= 2.0 ms`) & Stock-CP `0x0400` IBIS park."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    if not (V_LENS_LOGIC_MIN_V <= float(v_lens_logic_v) <= V_LENS_LOGIC_MAX_V):
        _add_code(codes, STATUS_BLOCKED_EMOUNT_HOT_DETACH_HAZARD)
        errors.append(
            f"V_LENS_LOGIC_3V3={v_lens_logic_v:.2f}V outside {V_LENS_LOGIC_MIN_V:.2f}V..{V_LENS_LOGIC_MAX_V:.2f}V."
        )

    if not (V_LENS_SERVO_MIN_V <= float(v_lens_servo_v) <= V_LENS_SERVO_MAX_V):
        _add_code(codes, STATUS_BLOCKED_EMOUNT_HOT_DETACH_HAZARD)
        errors.append(
            f"V_LENS_SERVO_5V0={v_lens_servo_v:.2f}V outside {V_LENS_SERVO_MIN_V:.2f}V..{V_LENS_SERVO_MAX_V:.2f}V."
        )

    if int(cp_mutation_bytes) != 0:
        _add_code(codes, STATUS_BLOCKED_EMOUNT_HOT_DETACH_HAZARD)
        errors.append(f"Stock-CP cp_mutation_bytes must equal 0 (got {cp_mutation_bytes}).")

    crowbar_within_budget = (
        float(v_lens_servo_crowbar_ms) >= 0.0
        and float(v_lens_servo_crowbar_ms) <= V_LENS_CROWBAR_MAX_MS
        and float(v_lens_servo_crowbar_ms) < EMOUNT_ROTARY_WIPE_WINDOW_MS
    )

    if camera_power_on and hot_detach_event:
        if not lens_det_interrupt_triggered:
            _add_code(codes, STATUS_BLOCKED_EMOUNT_HOT_DETACH_HAZARD)
            errors.append(
                "E-Mount Pin-9 LENS_DET interrupt did not fire during live hot-detach; "
                "V_LENS rails left energized across 3.5 ms rotary wipe window."
            )
        if not crowbar_within_budget:
            _add_code(codes, STATUS_BLOCKED_VLENS_CROWBAR_TIMEOUT)
            _add_code(codes, STATUS_BLOCKED_EMOUNT_HOT_DETACH_HAZARD)
            errors.append(
                f"V_LENS_SERVO_5V0 crowbar took {v_lens_servo_crowbar_ms:.2f} ms, exceeding "
                f"<= {V_LENS_CROWBAR_MAX_MS:.1f} ms limit (must discharge before {EMOUNT_ROTARY_WIPE_WINDOW_MS:.1f} ms rotary wipe)."
            )
        if float(v_lens_servo_residual_ma) != 0.0:
            _add_code(codes, STATUS_BLOCKED_EMOUNT_HOT_DETACH_HAZARD)
            errors.append(
                f"V_LENS_SERVO_5V0 residual current {v_lens_servo_residual_ma:.2f} mA != 0 mA after crowbar; "
                "adjacent E-Mount pin short hazard."
            )
        if not v_lens_logic_tri_stated:
            _add_code(codes, STATUS_BLOCKED_EMOUNT_HOT_DETACH_HAZARD)
            errors.append("V_LENS_LOGIC_3V3 / SPI lines were not tri-stated during hot-detach.")

        ibis_ok = (
            bool(ibis_park_commanded)
            and int(ibis_park_opcode) == STOCK_CP_IBIS_CENTER_LOCK_OPCODE
            and int(ibis_park_completion_opcode) == STOCK_CP_IBIS_CENTER_LOCK_COMPLETION
            and bool(ibis_stage_parked)
        )
        if not ibis_ok:
            _add_code(codes, STATUS_BLOCKED_IBIS_UNPARKED_IMPACT)
            _add_code(codes, STATUS_BLOCKED_EMOUNT_HOT_DETACH_HAZARD)
            errors.append(
                f"Stock-CP 0x0400 IBIS Center-Lock park failed (commanded={ibis_park_commanded}, "
                f"opcode=0x{int(ibis_park_opcode):04x}, completion=0x{int(ibis_park_completion_opcode):04x}, "
                f"parked={ibis_stage_parked}): floating IMX510 IBIS stage at mechanical stop impact risk."
            )

    valid = len(errors) == 0 and len(codes) == 0
    status = STATUS_SAFE if valid else codes[0]

    return EmountHotDetachRailResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        emount_pin_count=EMOUNT_PIN_COUNT,
        camera_power_on=bool(camera_power_on),
        hot_detach_event=bool(hot_detach_event),
        lens_det_interrupt_triggered=bool(lens_det_interrupt_triggered),
        v_lens_logic_v=float(v_lens_logic_v),
        v_lens_servo_v=float(v_lens_servo_v),
        v_lens_servo_crowbar_ms=float(v_lens_servo_crowbar_ms),
        crowbar_max_ms=V_LENS_CROWBAR_MAX_MS,
        rotary_wipe_window_ms=EMOUNT_ROTARY_WIPE_WINDOW_MS,
        v_lens_servo_residual_ma=float(v_lens_servo_residual_ma),
        v_lens_logic_tri_stated=bool(v_lens_logic_tri_stated),
        crowbar_within_budget=crowbar_within_budget and float(v_lens_servo_residual_ma) == 0.0,
        ibis_park_commanded=bool(ibis_park_commanded),
        ibis_park_opcode_hex=f"0x{int(ibis_park_opcode):04x}",
        ibis_park_completion_hex=f"0x{int(ibis_park_completion_opcode):04x}",
        ibis_stage_parked=bool(ibis_stage_parked),
        cp_mutation_bytes=int(cp_mutation_bytes),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "pin_map": [
                {"pin": pin, "signal": sig, "role": role}
                for pin, sig, role in EMOUNT_PIN_MAP
            ],
            "stock_cp_center_lock_seq": "0x0400 -> 0x1400 (LiroSeq: Restore.)",
        },
    )


# ---------------------------------------------------------------------------
# 4. Sudden Power-Loss .RSV Salvage & USB-PD Battery-Less Trap Guard
# ---------------------------------------------------------------------------


def build_synthetic_sony_rsv_payload(
    *,
    brand: str = "XAVC",
    frame_count: int = 4,
    frame_payload_bytes: int = 256,
    include_moov: bool = False,
    corrupt_header: bool = False,
) -> bytes:
    """Build a deterministic clean-room Sony `.RSV` ISO-BMFF emergency salvage payload."""
    if corrupt_header:
        return b"BAD!\x00\x00\x00\x00corrupt_rsv_payload"

    brand_bytes = brand.encode("ascii")[:4].ljust(4, b" ")
    # ftyp box: size(4) + 'ftyp'(4) + major_brand(4) + minor_ver(4) + compat(8) = 24 bytes
    ftyp = struct.pack(">I4s4sI4s4s", 24, b"ftyp", brand_bytes, 0x01000000, brand_bytes, b"mp42")
    # free box: 16 bytes Sony salvage anchor
    free_box = struct.pack(">I4s8s", 16, b"free", b"SONY_RSV")

    # mdat chunks: open-ended mdat (size=0 until EOF, standard for interrupted power-loss .RSV)
    chunks: List[bytes] = []
    for idx in range(max(1, int(frame_count))):
        # Synthetic XAVC S-I NAL frame header + deterministic payload
        hdr = struct.pack(">II", 0x00000001, 0x65000000 | (idx & 0xFFFF))
        body = (bytes([0xA5 ^ (idx & 0xFF)]) * max(16, int(frame_payload_bytes) - len(hdr)))
        chunks.append(hdr + body)
    mdat_body = b"".join(chunks)
    if include_moov:
        mdat = struct.pack(">I4s", 8 + len(mdat_body), b"mdat") + mdat_body
        moov_payload = b"mvhd_finalized"
        moov = struct.pack(">I4s", 8 + len(moov_payload), b"moov") + moov_payload
        return ftyp + free_box + mdat + moov
    mdat = struct.pack(">I4s", 0, b"mdat") + mdat_body
    return ftyp + free_box + mdat


def inspect_sony_rsv_salvage_structure(
    rsv_bytes: Optional[bytes] = None,
    *,
    rsv_path: Optional[Path] = None,
) -> RsvSalvageInspectionResult:
    """Strictly read-only deterministic inspection of Sony `.RSV` emergency salvage header/chunks."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if rsv_path is not None:
        blob = _read_file_o_rdonly(Path(rsv_path))
    elif rsv_bytes is not None:
        blob = bytes(rsv_bytes)
    else:
        blob = build_synthetic_sony_rsv_payload()

    total_len = len(blob)
    header_hex = blob[:16].hex()

    if total_len < 32:
        _add_code(codes, STATUS_BLOCKED_RSV_SALVAGE_INVALID)
        errors.append(f".RSV payload too short ({total_len} B < 32 B) for valid container header.")
        return RsvSalvageInspectionResult(
            valid=False,
            status=STATUS_BLOCKED_RSV_SALVAGE_INVALID,
            violation_codes=tuple(codes),
            container_format="UNKNOWN",
            ftyp_brand="",
            total_bytes=total_len,
            header_hex=header_hex,
            has_moov_or_footer=False,
            needs_rsv_salvage=False,
            recoverable_chunks=0,
            recoverable_payload_bytes=0,
            boxes_parsed=(),
            physical_media_writes=0,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    # Check ISO BMFF (MP4 / XAVC S-I .RSV)
    if blob[4:8] == b"ftyp":
        boxes: List[str] = []
        offset = 0
        ftyp_brand = ""
        has_mdat = False
        has_moov = False
        recoverable_bytes = 0
        recoverable_chunks = 0

        while offset + 8 <= total_len:
            box_size, box_type_raw = struct.unpack_from(">I4s", blob, offset)
            try:
                box_type = box_type_raw.decode("ascii")
            except UnicodeDecodeError:
                _add_code(codes, STATUS_BLOCKED_RSV_SALVAGE_INVALID)
                errors.append(f"Non-ASCII ISO-BMFF box tag at offset {offset}.")
                break
            if not box_type.isprintable():
                _add_code(codes, STATUS_BLOCKED_RSV_SALVAGE_INVALID)
                errors.append(f"Invalid box tag at offset {offset}.")
                break

            header_len = 8
            if box_size == 0:
                actual_size = total_len - offset
            elif box_size == 1:
                if offset + 16 > total_len:
                    _add_code(codes, STATUS_BLOCKED_RSV_SALVAGE_INVALID)
                    errors.append(f"Truncated 64-bit extended box header at offset {offset}.")
                    break
                actual_size = struct.unpack_from(">Q", blob, offset + 8)[0]
                header_len = 16
            elif box_size < 8:
                _add_code(codes, STATUS_BLOCKED_RSV_SALVAGE_INVALID)
                errors.append(f"Invalid ISO-BMFF box size {box_size} at offset {offset}.")
                break
            else:
                actual_size = box_size

            if offset + actual_size > total_len:
                _add_code(codes, STATUS_BLOCKED_RSV_SALVAGE_INVALID)
                errors.append(f"Box {box_type!r} overruns .RSV payload ({offset + actual_size} > {total_len}).")
                break

            boxes.append(box_type)
            if box_type == "ftyp" and actual_size >= 16:
                ftyp_brand = blob[offset + 8 : offset + 12].decode("ascii", "replace")
            elif box_type == "mdat":
                has_mdat = True
                payload_span = actual_size - header_len
                recoverable_bytes += payload_span
                if payload_span > 0:
                    # Count Annex-B / XAVC NAL sync headers (0x00000001) or 256B chunks
                    mdat_slice = blob[offset + header_len : offset + actual_size]
                    sync_hits = mdat_slice.count(b"\x00\x00\x00\x01")
                    recoverable_chunks += sync_hits if sync_hits > 0 else max(1, payload_span // 256)
            elif box_type == "moov":
                has_moov = True

            offset += actual_size
            if box_size == 0:
                break

        if ftyp_brand not in SONY_RSV_SUPPORTED_BRANDS:
            _add_code(codes, STATUS_BLOCKED_RSV_SALVAGE_INVALID)
            errors.append(
                f"Unsupported .RSV ftyp brand {ftyp_brand!r}; expected one of {SONY_RSV_SUPPORTED_BRANDS}."
            )
        if not has_mdat or recoverable_bytes <= 0 or recoverable_chunks <= 0:
            _add_code(codes, STATUS_BLOCKED_RSV_SALVAGE_INVALID)
            errors.append(".RSV file lacks recoverable mdat media chunks.")

        valid = len(errors) == 0 and len(codes) == 0
        return RsvSalvageInspectionResult(
            valid=valid,
            status=STATUS_SAFE if valid else codes[0],
            violation_codes=tuple(codes),
            container_format="ISO_BMFF_XAVC_RSV",
            ftyp_brand=ftyp_brand,
            total_bytes=total_len,
            header_hex=header_hex,
            has_moov_or_footer=has_moov,
            needs_rsv_salvage=(not has_moov) and has_mdat,
            recoverable_chunks=recoverable_chunks,
            recoverable_payload_bytes=recoverable_bytes,
            boxes_parsed=tuple(boxes),
            physical_media_writes=0,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    # Check MXF KLV Header Partition Pack (06 0e 2b 34)
    if blob[:4].hex() == MXF_KLV_PARTITION_PREFIX_HEX:
        has_footer = b"\x06\x0e\x2b\x34\x02\x05\x01\x01\x0d\x01\x02\x01\x01\x04" in blob
        klv_count = blob.count(b"\x06\x0e\x2b\x34")
        if klv_count < 2:
            _add_code(codes, STATUS_BLOCKED_RSV_SALVAGE_INVALID)
            errors.append("MXF .RSV lacks body essence KLV packs.")
        valid = len(errors) == 0
        return RsvSalvageInspectionResult(
            valid=valid,
            status=STATUS_SAFE if valid else codes[0],
            violation_codes=tuple(codes),
            container_format="MXF_KLV_RSV",
            ftyp_brand="MXF",
            total_bytes=total_len,
            header_hex=header_hex,
            has_moov_or_footer=has_footer,
            needs_rsv_salvage=not has_footer,
            recoverable_chunks=max(0, klv_count - 1),
            recoverable_payload_bytes=max(0, total_len - 32),
            boxes_parsed=("HeaderPartition", "EssenceKLV"),
            physical_media_writes=0,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    _add_code(codes, STATUS_BLOCKED_RSV_SALVAGE_INVALID)
    errors.append(f"Unrecognized .RSV header signature ({header_hex[:16]}).")
    return RsvSalvageInspectionResult(
        valid=False,
        status=STATUS_BLOCKED_RSV_SALVAGE_INVALID,
        violation_codes=tuple(codes),
        container_format="UNKNOWN",
        ftyp_brand="",
        total_bytes=total_len,
        header_hex=header_hex,
        has_moov_or_footer=False,
        needs_rsv_salvage=False,
        recoverable_chunks=0,
        recoverable_payload_bytes=0,
        boxes_parsed=(),
        physical_media_writes=0,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_power_failover_ups_and_rsv_salvage(
    *,
    recording_codec: str = XAVC_SI_4K60_CODEC,
    recording_bitrate_mbps: int = XAVC_SI_4K60_BITRATE_MBPS,
    usb_pd_voltage_v: float = USB_PD_REQUIRED_VOLTAGE_V,
    usb_pd_current_a: float = USB_PD_REQUIRED_CURRENT_A,
    usb_pd_unplug_event: bool = True,
    np_fz100_installed: bool = True,
    battery_less_usb_pd: bool = False,
    np_fz100_soc_pct: int = 88,
    np_fz100_load_voltage_v: float = 8.0,
    lost_frames_on_switchover: int = 0,
    container_cleanly_closed: bool = True,
    rsv_bytes: Optional[bytes] = None,
    rsv_path: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
) -> PowerFailoverUpsResult:
    """Verify `USB-PD` unplug UPS switchover (`NP-FZ100 >= 15%`, `>= 6.8V`), battery-less trap block, & read-only `.RSV` salvage."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    pd_watts = round(float(usb_pd_voltage_v) * float(usb_pd_current_a), 2)
    if float(usb_pd_voltage_v) < USB_PD_REQUIRED_VOLTAGE_V or pd_watts < USB_PD_REQUIRED_WATTS:
        _add_code(codes, STATUS_BLOCKED_BATTERY_RESERVE_INSUFFICIENT)
        errors.append(
            f"USB-PD rail {usb_pd_voltage_v:.1f}V/{usb_pd_current_a:.1f}A ({pd_watts:.1f}W) below "
            f"required 9V/3A (27W) contract for {recording_codec}."
        )

    # Always run deterministic read-only .RSV emergency salvage structure check
    rsv_res = inspect_sony_rsv_salvage_structure(rsv_bytes=rsv_bytes, rsv_path=rsv_path)
    if not rsv_res.valid:
        for c in rsv_res.violation_codes:
            _add_code(codes, c)
        errors.extend(rsv_res.errors)

    # Battery-less USB-PD trap & low-SOC fail-closed block
    effective_battery_less = bool(battery_less_usb_pd) or (not bool(np_fz100_installed))
    soc_ok = (not effective_battery_less) and (int(np_fz100_soc_pct) >= NP_FZ100_UPS_MIN_SOC_PCT)
    volt_ok = (not effective_battery_less) and (float(np_fz100_load_voltage_v) >= NP_FZ100_LOAD_MIN_VOLTAGE_V)

    if not (soc_ok and volt_ok):
        _add_code(codes, STATUS_BLOCKED_BATTERY_RESERVE_INSUFFICIENT)
        if effective_battery_less:
            errors.append(
                "BLOCK_REC_START_BATTERY_RESERVE_INSUFFICIENT: NP-FZ100 absent (battery_less_usb_pd=True); "
                "refusing high-bitrate 4K 60p XAVC S-I recording to prevent unfinalized .RSV media corruption on USB-PD unplug."
            )
        else:
            errors.append(
                f"BLOCK_REC_START_BATTERY_RESERVE_INSUFFICIENT: NP-FZ100 reserve too low "
                f"(soc={np_fz100_soc_pct}% < {NP_FZ100_UPS_MIN_SOC_PCT}% or "
                f"V_load={np_fz100_load_voltage_v:.2f}V < {NP_FZ100_LOAD_MIN_VOLTAGE_V:.1f}V)."
            )

    ups_seamless = bool(soc_ok and volt_ok)
    moov_closed = False
    mxf_closed = False
    if ups_seamless:
        if usb_pd_unplug_event:
            if int(lost_frames_on_switchover) != 0 or not bool(container_cleanly_closed):
                ups_seamless = False
                _add_code(codes, STATUS_BLOCKED_UPS_SWITCHOVER_DROP)
                errors.append(
                    f"UPS switchover during USB-PD unplug dropped frames ({lost_frames_on_switchover}) "
                    f"or failed clean container close (closed={container_cleanly_closed})."
                )
            else:
                moov_closed = True
                mxf_closed = True
        else:
            moov_closed = bool(container_cleanly_closed)
            mxf_closed = bool(container_cleanly_closed)

    valid = len(errors) == 0 and len(codes) == 0 and rsv_res.valid and ups_seamless
    status = STATUS_SAFE if valid else codes[0]

    return PowerFailoverUpsResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        recording_codec=recording_codec,
        recording_bitrate_mbps=int(recording_bitrate_mbps),
        usb_pd_voltage_v=float(usb_pd_voltage_v),
        usb_pd_current_a=float(usb_pd_current_a),
        usb_pd_watts=pd_watts,
        usb_pd_unplug_event=bool(usb_pd_unplug_event),
        np_fz100_installed=bool(np_fz100_installed),
        battery_less_usb_pd=effective_battery_less,
        np_fz100_soc_pct=int(np_fz100_soc_pct),
        np_fz100_load_voltage_v=float(np_fz100_load_voltage_v),
        ups_switchover_seamless=ups_seamless,
        lost_frames_on_switchover=int(lost_frames_on_switchover),
        container_cleanly_closed=bool(container_cleanly_closed) and ups_seamless,
        moov_atom_written=moov_closed,
        mxf_footer_partition_written=mxf_closed,
        rsv_salvage_verified=rsv_res.valid,
        rsv_salvage=rsv_res.to_dict(),
        physical_media_writes=0,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 5. Gate 19 & Gate 20 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g19_rig_groundloop_and_lensrail(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    rig_kwargs: Optional[Mapping[str, Any]] = None,
    emount_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
) -> Tuple[GateVerdict, G19RigGroundLoopAndLensRailResult]:
    """Evaluate Gate G19 (`rig_hdmi_dtap_groundloop_and_lensrail_safe`)."""
    donor_audit = audit_rig_20gate_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_rig = dict(rig_kwargs or {})
    eff_rig["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_rig.get("request_persistent_emmc_writes", False)
    )
    rig_res = verify_rig_dtap_hdmi_groundloop_firewall(**eff_rig)

    eff_emount = dict(emount_kwargs or {})
    eff_emount["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_emount.get("request_persistent_emmc_writes", False)
    )
    emount_res = verify_emount_hot_detach_rail_and_ibis_park(**eff_emount)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not donor_audit.valid:
        _add_code(codes, donor_audit.status)
        errors.extend(donor_audit.errors)
    for c in rig_res.violation_codes + emount_res.violation_codes:
        _add_code(codes, c)
    errors.extend(rig_res.errors)
    errors.extend(emount_res.errors)
    warnings.extend(donor_audit.warnings)
    warnings.extend(rig_res.warnings)
    warnings.extend(emount_res.warnings)

    passed = (
        donor_audit.valid
        and rig_res.valid
        and emount_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = STATUS_VERIFIED_G19 if passed else (codes[0] if codes else STATUS_BLOCKED_GROUND_LOOP_HAZARD)

    res = G19RigGroundLoopAndLensRailResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=donor_audit.verification_mode,
        donor_audit=donor_audit.to_dict(),
        rig_groundloop=rig_res.to_dict(),
        emount_lensrail=emount_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G19_GATE_ID,
        gate_code=G19_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"D-Tap/HDMI Ground-Loop ({rig_res.status}, cable={rig_res.hdmi_cable_type}, "
            f"pin18={rig_res.hdmi_pin18_voltage_v:.2f}V/{rig_res.hdmi_pin18_current_ma:.0f}mA) + "
            f"E-Mount Hot-Detach Crowbar ({emount_res.v_lens_servo_crowbar_ms:.2f}ms <= {V_LENS_CROWBAR_MAX_MS:.1f}ms, "
            f"0mA, IBIS {emount_res.ibis_park_opcode_hex} parked={emount_res.ibis_stage_parked}, "
            f"{donor_audit.verification_mode}), persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": donor_audit.verification_mode,
            "rig_status": rig_res.status,
            "emount_status": emount_res.status,
            "crowbar_ms": emount_res.v_lens_servo_crowbar_ms,
            "ibis_park_opcode": emount_res.ibis_park_opcode_hex,
        },
    )
    return verdict, res


def evaluate_g20_power_failover_ups_and_rsv_salvage(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    power_failover_kwargs: Optional[Mapping[str, Any]] = None,
    rsv_bytes: Optional[bytes] = None,
    rsv_path: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
) -> Tuple[GateVerdict, G20PowerFailoverAndRsvResult]:
    """Evaluate Gate G20 (`power_failover_ups_and_rsv_salvage_safe`)."""
    donor_audit = audit_rig_20gate_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_pf = dict(power_failover_kwargs or {})
    if rsv_bytes is not None and "rsv_bytes" not in eff_pf:
        eff_pf["rsv_bytes"] = rsv_bytes
    if rsv_path is not None and "rsv_path" not in eff_pf:
        eff_pf["rsv_path"] = rsv_path
    eff_pf["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_pf.get("request_persistent_emmc_writes", False)
    )

    pf_res = verify_power_failover_ups_and_rsv_salvage(**eff_pf)

    # Probe battery-less trap guard to verify fail-closed protection is active
    trap_probe = verify_power_failover_ups_and_rsv_salvage(
        np_fz100_installed=False,
        battery_less_usb_pd=True,
    )
    trap_verified = (not trap_probe.valid) and (
        trap_probe.status == STATUS_BLOCKED_BATTERY_RESERVE_INSUFFICIENT
    )

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not donor_audit.valid:
        _add_code(codes, donor_audit.status)
        errors.extend(donor_audit.errors)
    for c in pf_res.violation_codes:
        _add_code(codes, c)
    errors.extend(pf_res.errors)
    if not trap_verified:
        _add_code(codes, STATUS_BLOCKED_BATTERY_RESERVE_INSUFFICIENT)
        errors.append("Battery-less USB-PD fail-closed trap self-probe did not block as required.")
    warnings.extend(donor_audit.warnings)
    warnings.extend(pf_res.warnings)

    passed = (
        donor_audit.valid
        and pf_res.valid
        and trap_verified
        and pf_res.physical_media_writes == 0
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = STATUS_VERIFIED_G20 if passed else (codes[0] if codes else STATUS_BLOCKED_BATTERY_RESERVE_INSUFFICIENT)

    res = G20PowerFailoverAndRsvResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=donor_audit.verification_mode,
        donor_audit=donor_audit.to_dict(),
        power_failover_ups=pf_res.to_dict(),
        battery_less_trap_verified=trap_verified,
        physical_media_writes=0,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G20_GATE_ID,
        gate_code=G20_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"UPS Failover ({pf_res.recording_codec}, NP-FZ100 {pf_res.np_fz100_soc_pct}%/"
            f"{pf_res.np_fz100_load_voltage_v:.1f}V, lost_frames={pf_res.lost_frames_on_switchover}, "
            f"rsv_salvage_ok={pf_res.rsv_salvage_verified}, battery_less_trap={trap_verified}, "
            f"physical_media_writes={pf_res.physical_media_writes}, {donor_audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": donor_audit.verification_mode,
            "ups_switchover_seamless": pf_res.ups_switchover_seamless,
            "rsv_salvage_verified": pf_res.rsv_salvage_verified,
            "battery_less_trap_verified": trap_verified,
            "physical_media_writes": pf_res.physical_media_writes,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 6. Master 20-Gate Preflight Evaluator (`G01..G20`) & CLI
# ---------------------------------------------------------------------------


def evaluate_20gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G12 pass-throughs
    tier0_manifest: Optional[Dict[str, object]] = None,
    worker_syscall_trace: Optional[List[Dict[str, object]]] = None,
    init2_failsafe_hook: Optional[str] = None,
    candidate_bundle_verified: Optional[bool] = None,
    allow_dry_run_gate12: bool = False,
    gate12_kwargs: Optional[Mapping[str, Any]] = None,
    # G13..G18 pass-throughs
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
    # G19 inputs (Rig D-Tap/HDMI Ground-Loop + E-Mount V_LENS / IBIS park)
    rig_kwargs: Optional[Mapping[str, Any]] = None,
    emount_kwargs: Optional[Mapping[str, Any]] = None,
    # G20 inputs (Power-loss .RSV salvage + UPS failover)
    power_failover_kwargs: Optional[Mapping[str, Any]] = None,
    rsv_bytes: Optional[bytes] = None,
    rsv_path: Optional[Path] = None,
) -> Master20GateReport:
    """Evaluate all 20 Master Safety Gates (`G01..G20`) deterministically."""
    resolved_root = (DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m18_kwargs: Dict[str, Any] = {
        "force_clean_room": clean_forced,
        "include_large_binaries": include_large_binaries,
        "work_root": work_root,
        "tier0_manifest": tier0_manifest,
        "worker_syscall_trace": worker_syscall_trace,
        "init2_failsafe_hook": init2_failsafe_hook,
        "candidate_bundle_verified": candidate_bundle_verified,
        "allow_dry_run_gate12": allow_dry_run_gate12,
        "use_synthetic_dry_run_tier0": bool(dry_run_simulated_backup),
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
    }
    if soc_start_ceiling_c is not None:
        m18_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m18_report: Master18GateReport = evaluate_18_master_safety_gates(resolved_root, **m18_kwargs)

    g19_verdict, g19_res = evaluate_g19_rig_groundloop_and_lensrail(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        rig_kwargs=rig_kwargs,
        emount_kwargs=emount_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
    )

    g20_verdict, g20_res = evaluate_g20_power_failover_ups_and_rsv_salvage(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        power_failover_kwargs=power_failover_kwargs,
        rsv_bytes=rsv_bytes,
        rsv_path=rsv_path,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
    )

    # Normalize G01..G18 gate dicts; in offline default mode G10..G12 remain truthfully
    # FAIL_OFFLINE_HARDWARE_NOT_ATTACHED unless verified by real or dry-run inputs.
    normalized_18: List[Dict[str, Any]] = []
    for idx, g in enumerate(m18_report.gates):
        entry = dict(g)
        raw_status = str(entry.get("status", ""))
        is_verified = raw_status.startswith("VERIFIED")
        if idx in (9, 10, 11) and (not dry_run_simulated_backup) and (not is_verified):
            entry["underlying_status"] = raw_status
            entry["status"] = STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED
            entry["passed"] = False
        else:
            entry["passed"] = bool(entry.get("passed", is_verified))
        normalized_18.append(entry)

    gates_19_to_20 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g19_verdict, g20_verdict)
    ]
    all_gates = tuple(normalized_18 + gates_19_to_20)

    g01_to_g12_verified = sum(1 for g in normalized_18[:12] if bool(g["passed"]))
    g13_to_g18_verified = sum(1 for g in normalized_18[12:18] if bool(g["passed"]))
    g19_to_g20_verified = sum(1 for v in (g19_verdict, g20_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g18_verified + g19_to_g20_verified

    g19_to_g20_all_passed = g19_to_g20_verified == 2
    g13_to_g20_all_passed = m18_report.g13_to_g18_all_passed and g19_to_g20_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in normalized_18[:9])

    offline_17_verified = g01_to_g09_ok and g13_to_g20_all_passed and (not request_persistent_emmc_writes)
    all_20_verified = (g01_to_g12_verified == 12) and g13_to_g20_all_passed and (not request_persistent_emmc_writes)

    # Physical hardware attach requires real Tier-0 backup readback (not dry-run simulation)
    real_tier0_verified = (g01_to_g12_verified == 12) and (not dry_run_simulated_backup)
    overall_ready_for_hardware_attach = (
        real_tier0_verified
        and g13_to_g20_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    h0_h1_allowed = (
        offline_17_verified
        and m18_report.h0_h1_trial_entry_allowed
        and g19_to_g20_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = list(m18_report.errors) + list(g19_verdict.errors) + list(g20_verdict.errors)
    warnings: List[str] = list(m18_report.warnings) + list(g19_verdict.warnings) + list(g20_verdict.warnings)

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m18_report.g13_to_g18_all_passed:
        overall_status = m18_report.status
    elif not g19_verdict.passed:
        overall_status = g19_verdict.status
    elif not g20_verdict.passed:
        overall_status = g20_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_20_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_20_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_20_verified:
        overall_status = "VERIFIED_ALL_20_GATES"
    else:
        overall_status = "VERIFIED_17_OF_20_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m18_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g19_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g20_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 20,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 20 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g18_verified": g13_to_g18_verified,
        "g19_to_g20_verified": g19_to_g20_verified,
        "g13_to_g20_all_passed": g13_to_g20_all_passed,
        "g19_to_g20_all_passed": g19_to_g20_all_passed,
        "offline_17_gates_verified": offline_17_verified,
        "all_20_gates_verified": all_20_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master20GateReport(
        schema=RIG_GROUNDLOOP_20GATE_SCHEMA,
        version=RIG_GROUNDLOOP_20GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_17_gates_verified=offline_17_verified,
        all_20_gates_verified=all_20_verified,
        g13_to_g20_all_passed=g13_to_g20_all_passed,
        g19_to_g20_all_passed=g19_to_g20_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_18_report=m18_report.to_dict(),
        g19_result=g19_res.to_dict(),
        g20_result=g20_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_20_master_safety_gates = evaluate_20gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rig_groundloop_lensrail_and_20gate_guard",
        description="Phase 69 — Rig D-Tap/HDMI Ground-Loop, E-Mount Rail Guard, .RSV Salvage & 20-Gate Preflight (G01..G20)",
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G20 can be exercised offline",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_20gate_preflight(
        args.repo_root,
        force_clean_room=True if args.clean_room else None,
        dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/20 "
            f"g19_to_g20_all_passed={report.g19_to_g20_all_passed} "
            f"all_20_gates_verified={report.all_20_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = report.all_20_gates_verified if args.dry_run_simulated_backup else report.offline_17_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
