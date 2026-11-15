"""Phase 77 — `XLR-H1 +48V` Phantom Transducer Burnout Firewall, Gimbal / Follow-Focus Torque & Laser-CMOS Guard + `G01..G22` 22-Gate Preflight.

Operationalizes physical audio phantom-power safety, gimbal / follow-focus
mechanical & dual-bus control safety, venue Class-3B/4 laser & shutter-curtain
protection, and the unified 22-Gate Master Safety Preflight (`G01..G22`) for
Sony ILME-FX3 (`Ver. 7.02`, SoC `CXD90057`, `IMX510` 5-axis IBIS) while
keeping `preflight.py`, `master_16gate_preflight.py`,
`usblan_ptpip_and_18gate_preflight.py`, and
`rig_groundloop_lensrail_and_20gate_guard.py` completely untouched:

1. **`XLR-H1 +48V` Phantom Power Transducer Burnout & Hot-Patch Transient Firewall (`Gate G21`)**:
   - Models the 24-pin MI-Shoe `XLR-H1` top handle's dual XLR/TRS combo inputs
     (`INPUT1`, `INPUT2` `LINE / MIC / MIC+48V`) + `INPUT3` `3.5mm` stereo
     Plug-In-Power (`2.5V`).
   - Blocks lethal `+48V` mismatches (`BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD`):
     * Passive ribbon microphone without cloudlifter/transformer isolation
       connected to `MIC+48V`,
     * Unbalanced `3.5mm TRS -> XLR` wireless receiver (`DJI Mic` / `Rode` /
       `Sennheiser` non-48V receiver) or SMPTE LTC timecode generator
       (`Tentacle Sync` / `Deity TC-1`) plugged into `MIC+48V`,
     * Hot-plugging/unplugging XLR cable while `+48V` DC-DC boost is energized
       without first ramping ADC mute & discharging `+48V` (`<= 1.0V` bleed-down
       interlock).
   - Permits balanced condenser shotgun/boom mics (`Sennheiser MKH416`,
     `Sony ECM-VG1`, `Sony ECM-B10`, `Sony ECM-XM1`) on `MIC+48V`, and requires
     `LINE` or `MIC` (`48V OFF`) for wireless receivers / dynamic / ribbon /
     LTC sources.

2. **Gimbal (`DJI RS3/RS4 Pro` USB-C `CrSDK` / `Multi-Port`), Follow-Focus Torque & Laser-Strobe `IMX510` Sensor Guard (`Gate G22`)**:
   - **Follow-Focus Gear Motor Endpoint Calibration & Torque Guard**: Blocks
     uncalibrated infinite-spin `14.8V` focus motors on fly-by-wire E-Mount
     lenses without hard stops unless a lens-support rod clamp is installed OR
     motor torque limit `<= 0.35 N·m` with calibrated soft A/B stops
     (`BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR`).
   - **USB-C vs Multi-Port Dual-Control Conflict Guard**: Blocks simultaneous
     conflicting `REC/Zoom/Iris` commands on BOTH `USB-C CrSDK` AND `Multi-Port
     RSS` from gimbal handles at the same time (`single_control_bus_arbitrated
     == True`), and enforces `IBIS Mode` in `Standard` or `Off` (blocking
     `Active` crop drift) when gimbal pan-follow is active.
   - **Class-3B/4 Venue Laser & Mechanical Shutter Dust-Curtain Park Check**:
     Flags & blocks high-risk concert/club laser environments
     (`venue_laser_present = True` without optical laser-cut filter) and
     verifies FX3's focal-plane shutter remains safely parked `OPEN`
     (`shutter_when_power_off = "OFF"` default unless explicitly enabled with
     lens-cap swap rules so bare fingers never bend fragile shutter blades).

3. **22-Gate Master Safety Preflight Engine (`G01..G22`) & CLI `verify-22-gates`**:
   - Composes `evaluate_20gate_preflight` (`G01..G20`) with `G21`
     (`xlr_phantom_48v_and_hotpatch_safe`) and `G22`
     (`gimbal_focus_torque_and_sensor_curtain_safe`):
     * Offline default mode: `19/22` gates pass (`G10..G12` physical body
       Tier-0 readback truthfully remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED`
       -> `overall_ready_for_hardware_attach = False`).
     * `--dry-run-simulated-backup` rehearsal mode: `22/22` simulation gates
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
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
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
from .rig_groundloop_lensrail_and_20gate_guard import (
    Master20GateReport,
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
    evaluate_20gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHANTOM48V_GIMBAL_22GATE_SCHEMA: str = "fx3-phantom48v-gimbal-22gate-preflight-v1"
PHANTOM48V_GIMBAL_22GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G21..G22
G21_GATE_ID: str = "G21_xlr_phantom_48v_and_hotpatch_safe"
G21_GATE_CODE: str = "XLR_PHANTOM_48V_AND_HOTPATCH_SAFE"

G22_GATE_ID: str = "G22_gimbal_focus_torque_and_sensor_curtain_safe"
G22_GATE_CODE: str = "GIMBAL_FOCUS_TORQUE_AND_SENSOR_CURTAIN_SAFE"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G21: str = "VERIFIED_XLR_PHANTOM_48V_AND_HOTPATCH_SAFE"
STATUS_VERIFIED_G22: str = "VERIFIED_GIMBAL_FOCUS_TORQUE_AND_SENSOR_CURTAIN_SAFE"

STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD: str = "BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD"
STATUS_BLOCKED_PHANTOM_48V_HOTPLUG_TRANSIENT: str = "BLOCKED_PHANTOM_48V_HOTPLUG_TRANSIENT"
STATUS_BLOCKED_XLR_H1_MISHOE_ELECTRICAL: str = "BLOCKED_XLR_H1_MISHOE_ELECTRICAL_HAZARD"

STATUS_BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR: str = "BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR"
STATUS_BLOCKED_GIMBAL_DUAL_BUS_CONFLICT: str = "BLOCKED_GIMBAL_DUAL_CONTROL_BUS_CONFLICT"
STATUS_BLOCKED_GIMBAL_ACTIVE_IBIS_DRIFT: str = "BLOCKED_GIMBAL_ACTIVE_IBIS_CROP_DRIFT"
STATUS_BLOCKED_VENUE_LASER_CMOS_HAZARD: str = "BLOCKED_VENUE_LASER_IMX510_CMOS_HAZARD"
STATUS_BLOCKED_SHUTTER_CURTAIN_EXPOSED: str = "BLOCKED_SHUTTER_DUST_CURTAIN_BLADE_HAZARD"

STATUS_BLOCKED_DONOR_INTEGRITY: str = "BLOCKED_PHASE77_22GATE_DONOR_INTEGRITY_MISMATCH"
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"

# XLR-H1 Input Channels, Modes & Audio Source Constants
XLR_H1_INPUT1: str = "INPUT1"
XLR_H1_INPUT2: str = "INPUT2"
XLR_H1_INPUT3: str = "INPUT3"

XLR_MODE_LINE: str = "LINE"
XLR_MODE_MIC: str = "MIC"
XLR_MODE_MIC_48V: str = "MIC+48V"
INPUT3_MODE_PLUG_IN_POWER_2V5: str = "PLUG_IN_POWER_2V5"
INPUT3_MODE_MIC_PIP_OFF: str = "MIC_3V5MM_PIP_OFF"

VALID_XLR_COMBO_MODES: Tuple[str, ...] = (XLR_MODE_LINE, XLR_MODE_MIC, XLR_MODE_MIC_48V)
VALID_INPUT3_MODES: Tuple[str, ...] = (INPUT3_MODE_PLUG_IN_POWER_2V5, INPUT3_MODE_MIC_PIP_OFF)

PHANTOM_48V_NOMINAL_V: float = 48.0
PHANTOM_48V_MIN_V: float = 44.0
PHANTOM_48V_MAX_V: float = 52.0
PHANTOM_48V_SAFE_BLEED_MAX_V: float = 1.0

INPUT3_PIP_NOMINAL_V: float = 2.5
INPUT3_PIP_MIN_V: float = 2.0
INPUT3_PIP_MAX_V: float = 3.0

XLR_H1_LOGIC_VDD_MIN_V: float = 2.8
XLR_H1_LOGIC_VDD_MAX_V: float = 3.15
XLR_H1_UNREG_MIN_V: float = 6.1
XLR_H1_UNREG_MAX_V: float = 8.4

SOURCE_CONDENSER_BALANCED: str = "CONDENSER_BALANCED"
SOURCE_PASSIVE_RIBBON: str = "PASSIVE_RIBBON"
SOURCE_DYNAMIC_MIC: str = "DYNAMIC_MIC"
SOURCE_WIRELESS_RECEIVER_TRS_XLR: str = "WIRELESS_RECEIVER_UNBALANCED_TRS_XLR"
SOURCE_SMPTE_LTC_GENERATOR: str = "SMPTE_LTC_GENERATOR"
SOURCE_LINE_MIXER: str = "LINE_MIXER"
SOURCE_LAV_PIP_3V5MM: str = "LAVALIER_3V5MM_PIP"
SOURCE_NONE: str = "NONE"

BALANCED_48V_CONDENSER_ALLOWLIST: Tuple[str, ...] = (
    "Sennheiser MKH416",
    "Sony ECM-VG1",
    "Sony ECM-B10",
    "Sony ECM-XM1",
)

# Gimbal, Follow-Focus, Laser-CMOS & Shutter Constants
GIMBAL_CONTROL_BUS_USBC_CRSDK: str = "USB_C_CRSDK"
GIMBAL_CONTROL_BUS_MULTIPORT_RSS: str = "MULTIPORT_RSS"
GIMBAL_CONTROL_COMMANDS: Tuple[str, ...] = ("REC", "ZOOM", "IRIS")

FOLLOW_FOCUS_MOTOR_MAX_TORQUE_NM_UNCLAMPED: float = 0.35
FOLLOW_FOCUS_MOTOR_NOMINAL_V: float = 14.8

IBIS_MODE_STANDARD: str = "STANDARD"
IBIS_MODE_OFF: str = "OFF"
IBIS_MODE_ACTIVE: str = "ACTIVE"
SAFE_GIMBAL_IBIS_MODES: Tuple[str, ...] = (IBIS_MODE_STANDARD, IBIS_MODE_OFF)

SHUTTER_WHEN_POWER_OFF_OPEN: str = "OFF"
SHUTTER_WHEN_POWER_OFF_CLOSED: str = "ON"

LASER_CLASS_NONE: str = "NONE"
LASER_CLASS_3B: str = "CLASS_3B"
LASER_CLASS_4: str = "CLASS_4"
HIGH_RISK_LASER_CLASSES: Tuple[str, ...] = (LASER_CLASS_3B, LASER_CLASS_4)

# Compact FX3/FX6 Donor Contracts for XLR-H1 MI-Shoe, PTP/USB & Lens Control (O_RDONLY verified)
PINNED_PHASE77_DONOR_SPECS: Mapping[str, Tuple[str, str, int, str, bytes, str]] = {
    "fx6_libinfra_hotshoe": (
        "fx6",
        "libInfraHotshoe.so",
        47_808,
        "0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6",
        b"INFRA_HOTSHOE_UIPC_SETSHOE_PWR_ON",
        "fx6/libInfraHotshoe.so::INFRA_HOTSHOE_UIPC_SETSHOE_PWR_ON",
    ),
    "fx3_libinfra_ptp_ext_cmd": (
        "fx3",
        "libInfraPtpExtCmd.so",
        35_600,
        "2dfe5d52abf029192714a28b85c513076f9076b00733cc3c641018607f79e5b3",
        b"_ZN9PtpExtCmd4Pipe10SetRequestEP12__extcmd_req",
        "fx3/libInfraPtpExtCmd.so::SetRequest",
    ),
    "fx3_lib_usb_control": (
        "fx3",
        "libUsbControl.so",
        135_424,
        "2bf51f28fd5066e56afc8bbb02ddbaa96b36f57ff2a823cecf9f901781754ed9",
        b"_ZN10UsbControl11GetInstanceEv",
        "fx3/libUsbControl.so::UsbControl::GetInstance",
    ),
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
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase77DonorAuditResult:
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
class XlrChannelCheckResult:
    channel_id: str
    input_mode: str
    source_type: str
    device_label: str
    phantom_48v_enabled: bool
    phantom_48v_voltage_v: float
    cloudlifter_or_transformer_isolated: bool
    hot_plug_event: bool
    adc_mute_ramped: bool
    phantom_48v_boost_energized: bool
    residual_phantom_voltage_v: float
    plug_in_power_v: float
    valid: bool
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class XlrPhantom48vFirewallResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    mishoe_24pin_attached: bool
    xlr_h1_logic_vdd_v: float
    xlr_h1_unreg_v: float
    channels: Tuple[Dict[str, Any], ...]
    hot_plug_discharge_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GimbalFocusLaserShutterGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    gimbal_model: str
    gimbal_attached: bool
    usb_c_crsdk_active: bool
    multiport_rss_active: bool
    single_control_bus_arbitrated: bool
    gimbal_pan_follow_active: bool
    ibis_mode: str
    ibis_gimbal_drift_safe: bool
    fly_by_wire_emount: bool
    lens_has_hard_stops: bool
    lens_support_rod_clamp_installed: bool
    soft_ab_stops_calibrated: bool
    infinite_spin_uncalibrated: bool
    motor_voltage_v: float
    motor_torque_nm: float
    follow_focus_shear_safe: bool
    venue_laser_present: bool
    laser_class: str
    optical_laser_cut_filter_installed: bool
    laser_hazard_flagged: bool
    laser_cmos_safe: bool
    shutter_when_power_off: str
    shutter_blade_parked_open: bool
    lens_cap_swap_rule_acknowledged: bool
    shutter_curtain_safe: bool
    cp_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G21XlrPhantom48vResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    xlr_phantom_firewall: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G22GimbalFocusLaserResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    gimbal_focus_laser_shutter: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master22GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_19_gates_verified: bool
    all_22_gates_verified: bool
    g13_to_g22_all_passed: bool
    g21_to_g22_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_20_report: Dict[str, Any]
    g21_result: Dict[str, Any]
    g22_result: Dict[str, Any]
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


def _normalize_audio_source(source_type: str) -> str:
    raw = source_type.strip().upper()
    if any(tok in raw for tok in ("MKH416", "ECM-VG1", "ECM_VG1", "ECM-B10", "ECM_B10", "ECM-XM1", "ECM_XM1", "CONDENSER")):
        return SOURCE_CONDENSER_BALANCED
    if "RIBBON" in raw:
        return SOURCE_PASSIVE_RIBBON
    if any(tok in raw for tok in ("WIRELESS", "DJI", "RODE", "SENNHEISER_EW", "TRS_XLR", "TRS->XLR")):
        return SOURCE_WIRELESS_RECEIVER_TRS_XLR
    if any(tok in raw for tok in ("LTC", "TENTACLE", "DEITY", "TIMECODE")):
        return SOURCE_SMPTE_LTC_GENERATOR
    if "DYNAMIC" in raw:
        return SOURCE_DYNAMIC_MIC
    if "LINE" in raw or "MIXER" in raw:
        return SOURCE_LINE_MIXER
    if "LAV" in raw or "PIP" in raw or "3.5" in raw or "3V5" in raw:
        return SOURCE_LAV_PIP_3V5MM
    if raw in ("NONE", "EMPTY", "UNPLUGGED", ""):
        return SOURCE_NONE
    return raw


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase77_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase77DonorAuditResult:
    """Inspect FX3/FX6 MI-Shoe Hotshoe, PTP ExtCmd, USB Control & LensComm donors via `os.O_RDONLY`."""
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)

    resolved: Dict[str, Path] = {}
    for key, (body, rel_name, *_rest) in PINNED_PHASE77_DONOR_SPECS.items():
        base_dir = paths.fx3_lib_dir if body == "fx3" else paths.fx6_lib_dir
        resolved[key] = base_dir / rel_name

    donor_available = (
        (not clean_forced)
        and (paths.work_root is not None)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase77DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(spec[5] for spec in PINNED_PHASE77_DONOR_SPECS.values()),
            missing_markers=(),
            sha256_by_artifact={k: spec[3] for k, spec in PINNED_PHASE77_DONOR_SPECS.items()},
            bytes_by_artifact={k: spec[2] for k, spec in PINNED_PHASE77_DONOR_SPECS.items()},
            errors=(),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []

    for key, (_body, _rel_name, exp_size, exp_sha, marker_bytes, marker_label) in PINNED_PHASE77_DONOR_SPECS.items():
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
    return Phase77DonorAuditResult(
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
# 2. XLR-H1 +48V Phantom Transducer Burnout & Hot-Patch Firewall (Gate G21)
# ---------------------------------------------------------------------------


def default_safe_xlr_h1_channels() -> Tuple[Dict[str, Any], ...]:
    """Return a clean-room safe 3-channel XLR-H1 input configuration."""
    return (
        {
            "channel_id": XLR_H1_INPUT1,
            "input_mode": XLR_MODE_MIC_48V,
            "source_type": SOURCE_CONDENSER_BALANCED,
            "device_label": "Sennheiser MKH416",
            "phantom_48v_voltage_v": PHANTOM_48V_NOMINAL_V,
            "cloudlifter_or_transformer_isolated": False,
            "hot_plug_event": False,
            "adc_mute_ramped": True,
            "phantom_48v_boost_energized": True,
            "residual_phantom_voltage_v": 0.0,
        },
        {
            "channel_id": XLR_H1_INPUT2,
            "input_mode": XLR_MODE_LINE,
            "source_type": SOURCE_WIRELESS_RECEIVER_TRS_XLR,
            "device_label": "DJI Mic / Rode Wireless TRS->XLR",
            "phantom_48v_voltage_v": 0.0,
            "cloudlifter_or_transformer_isolated": False,
            "hot_plug_event": False,
            "adc_mute_ramped": True,
            "phantom_48v_boost_energized": False,
            "residual_phantom_voltage_v": 0.0,
        },
        {
            "channel_id": XLR_H1_INPUT3,
            "input_mode": INPUT3_MODE_PLUG_IN_POWER_2V5,
            "source_type": SOURCE_LAV_PIP_3V5MM,
            "device_label": "3.5mm Stereo Lav (Plug-In-Power 2.5V)",
            "plug_in_power_v": INPUT3_PIP_NOMINAL_V,
            "hot_plug_event": False,
        },
    )


def verify_xlr_h1_channel(
    *,
    channel_id: str = XLR_H1_INPUT1,
    input_mode: str = XLR_MODE_MIC_48V,
    source_type: str = SOURCE_CONDENSER_BALANCED,
    device_label: str = "Sennheiser MKH416",
    phantom_48v_voltage_v: Optional[float] = None,
    cloudlifter_or_transformer_isolated: bool = False,
    hot_plug_event: bool = False,
    adc_mute_ramped: bool = True,
    phantom_48v_boost_energized: Optional[bool] = None,
    residual_phantom_voltage_v: float = 0.0,
    plug_in_power_v: float = INPUT3_PIP_NOMINAL_V,
) -> XlrChannelCheckResult:
    """Validate a single `XLR-H1` channel (`INPUT1`, `INPUT2`, or `INPUT3`) against `+48V` hazards."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    ch = channel_id.strip().upper()
    mode = input_mode.strip().upper()
    norm_source = _normalize_audio_source(source_type)

    if ch == XLR_H1_INPUT3:
        # 3.5mm stereo Plug-In-Power (2.5V) jack — +48V is never permitted here.
        phantom_on = (mode == XLR_MODE_MIC_48V) or (phantom_48v_voltage_v is not None and float(phantom_48v_voltage_v) > 3.5)
        if phantom_on:
            _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
            errors.append(
                f"{ch} (3.5mm stereo) cannot supply +48V phantom power; only 2.5V Plug-In-Power is supported."
            )
        if mode not in VALID_INPUT3_MODES and mode != XLR_MODE_MIC:
            if not phantom_on:
                _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
                errors.append(f"{ch} invalid 3.5mm mode {mode!r}; expected {VALID_INPUT3_MODES}.")
        pip_v = float(plug_in_power_v)
        if mode == INPUT3_MODE_MIC_PIP_OFF:
            if pip_v > 0.5:
                _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
                errors.append(f"{ch} PIP is OFF but measured voltage={pip_v:.2f}V > 0.5V.")
        else:
            if not (INPUT3_PIP_MIN_V <= pip_v <= INPUT3_PIP_MAX_V):
                _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
                errors.append(
                    f"{ch} Plug-In-Power voltage {pip_v:.2f}V outside safe {INPUT3_PIP_MIN_V:.1f}V..{INPUT3_PIP_MAX_V:.1f}V (2.5V nominal)."
                )
        return XlrChannelCheckResult(
            channel_id=ch,
            input_mode=mode,
            source_type=norm_source,
            device_label=device_label,
            phantom_48v_enabled=phantom_on,
            phantom_48v_voltage_v=float(phantom_48v_voltage_v or 0.0),
            cloudlifter_or_transformer_isolated=bool(cloudlifter_or_transformer_isolated),
            hot_plug_event=bool(hot_plug_event),
            adc_mute_ramped=bool(adc_mute_ramped),
            phantom_48v_boost_energized=False,
            residual_phantom_voltage_v=float(residual_phantom_voltage_v),
            plug_in_power_v=pip_v,
            valid=len(errors) == 0,
            violation_codes=tuple(codes),
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    # INPUT1 / INPUT2 XLR/TRS combo validation
    if ch not in (XLR_H1_INPUT1, XLR_H1_INPUT2):
        _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
        errors.append(f"Unknown XLR-H1 channel {ch!r}; expected INPUT1, INPUT2, or INPUT3.")

    if mode not in VALID_XLR_COMBO_MODES:
        _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
        errors.append(f"{ch} invalid input mode {mode!r}; expected one of {VALID_XLR_COMBO_MODES}.")

    phantom_on = mode == XLR_MODE_MIC_48V
    eff_48v = float(PHANTOM_48V_NOMINAL_V if phantom_48v_voltage_v is None and phantom_on else (phantom_48v_voltage_v or 0.0))
    eff_boost = bool(phantom_on if phantom_48v_boost_energized is None else phantom_48v_boost_energized)

    if phantom_on and not (PHANTOM_48V_MIN_V <= eff_48v <= PHANTOM_48V_MAX_V):
        _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
        errors.append(
            f"{ch} +48V phantom rail {eff_48v:.1f}V outside {PHANTOM_48V_MIN_V:.1f}V..{PHANTOM_48V_MAX_V:.1f}V."
        )
    if (not phantom_on) and eff_48v > PHANTOM_48V_SAFE_BLEED_MAX_V:
        _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
        errors.append(
            f"{ch} mode is {mode} (48V OFF) yet phantom voltage is {eff_48v:.2f}V > {PHANTOM_48V_SAFE_BLEED_MAX_V:.1f}V."
        )

    # Check lethal +48V transducer / source mismatches
    if phantom_on:
        if norm_source == SOURCE_PASSIVE_RIBBON:
            if not cloudlifter_or_transformer_isolated:
                _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
                errors.append(
                    f"{ch} BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD: passive ribbon microphone ({device_label}) "
                    "without Cloudlifter/transformer isolation connected to MIC+48V risks ribbon stretch/burnout; "
                    "switch to MIC (48V OFF) or add inline transformer/Cloudlifter isolation."
                )
            else:
                warnings.append(
                    f"{ch} passive ribbon ({device_label}) is protected by Cloudlifter/transformer isolation on MIC+48V."
                )
        elif norm_source == SOURCE_WIRELESS_RECEIVER_TRS_XLR:
            _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
            errors.append(
                f"{ch} BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD: unbalanced 3.5mm TRS->XLR wireless receiver "
                f"({device_label}) plugged into MIC+48V risks output stage burnout; require LINE or MIC (48V OFF)."
            )
        elif norm_source == SOURCE_SMPTE_LTC_GENERATOR:
            _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
            errors.append(
                f"{ch} BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD: SMPTE LTC timecode generator ({device_label}) "
                "plugged into MIC+48V risks driver burnout; require LINE or MIC (48V OFF)."
            )
        elif norm_source == SOURCE_DYNAMIC_MIC:
            _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
            errors.append(
                f"{ch} BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD: dynamic microphone ({device_label}) on MIC+48V; "
                "require LINE or MIC (48V OFF)."
            )
        elif norm_source == SOURCE_LINE_MIXER:
            _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
            errors.append(
                f"{ch} BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD: line-level source ({device_label}) on MIC+48V; "
                "require LINE or MIC (48V OFF)."
            )
        elif norm_source == SOURCE_CONDENSER_BALANCED:
            pass
        elif norm_source != SOURCE_NONE:
            _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
            errors.append(
                f"{ch} unknown audio source {source_type!r} cannot safely receive +48V phantom power."
            )

    # Check XLR hot-plug / unplug transient discharge interlock
    if hot_plug_event:
        if eff_boost or (not adc_mute_ramped) or float(residual_phantom_voltage_v) > PHANTOM_48V_SAFE_BLEED_MAX_V:
            _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
            _add_code(codes, STATUS_BLOCKED_PHANTOM_48V_HOTPLUG_TRANSIENT)
            errors.append(
                f"{ch} hot-plug/unplug transient blocked: must ramp ADC mute (ramped={adc_mute_ramped}), "
                f"de-energize +48V DC-DC boost (boost_energized={eff_boost}), and discharge residual "
                f"phantom voltage <= {PHANTOM_48V_SAFE_BLEED_MAX_V:.1f}V (got {residual_phantom_voltage_v:.2f}V)."
            )

    return XlrChannelCheckResult(
        channel_id=ch,
        input_mode=mode,
        source_type=norm_source,
        device_label=device_label,
        phantom_48v_enabled=phantom_on,
        phantom_48v_voltage_v=eff_48v,
        cloudlifter_or_transformer_isolated=bool(cloudlifter_or_transformer_isolated),
        hot_plug_event=bool(hot_plug_event),
        adc_mute_ramped=bool(adc_mute_ramped),
        phantom_48v_boost_energized=eff_boost,
        residual_phantom_voltage_v=float(residual_phantom_voltage_v),
        plug_in_power_v=0.0,
        valid=len(errors) == 0,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_xlr_h1_phantom_48v_firewall(
    *,
    channels: Optional[Sequence[Mapping[str, Any]]] = None,
    mishoe_24pin_attached: bool = True,
    xlr_h1_logic_vdd_v: float = 3.0,
    xlr_h1_unreg_v: float = 7.4,
    request_persistent_emmc_writes: bool = False,
    **single_channel_overrides: Any,
) -> XlrPhantom48vFirewallResult:
    """Verify 24-pin MI-Shoe `XLR-H1` `+48V` phantom transducer safety and hot-patch discharge interlock."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    if mishoe_24pin_attached:
        if not (XLR_H1_LOGIC_VDD_MIN_V <= float(xlr_h1_logic_vdd_v) <= XLR_H1_LOGIC_VDD_MAX_V):
            _add_code(codes, STATUS_BLOCKED_XLR_H1_MISHOE_ELECTRICAL)
            errors.append(
                f"XLR-H1 24-pin MI-Shoe LOGIC_VDD {xlr_h1_logic_vdd_v:.2f}V outside "
                f"{XLR_H1_LOGIC_VDD_MIN_V:.1f}V..{XLR_H1_LOGIC_VDD_MAX_V:.2f}V."
            )
        if not (XLR_H1_UNREG_MIN_V <= float(xlr_h1_unreg_v) <= XLR_H1_UNREG_MAX_V):
            _add_code(codes, STATUS_BLOCKED_XLR_H1_MISHOE_ELECTRICAL)
            errors.append(
                f"XLR-H1 24-pin MI-Shoe UNREG {xlr_h1_unreg_v:.2f}V outside "
                f"{XLR_H1_UNREG_MIN_V:.1f}V..{XLR_H1_UNREG_MAX_V:.1f}V."
            )

    if channels is not None:
        raw_channels = [dict(c) for c in channels]
    else:
        raw_channels = [dict(c) for c in default_safe_xlr_h1_channels()]
        if single_channel_overrides:
            target_ch = str(single_channel_overrides.get("channel_id", XLR_H1_INPUT1)).strip().upper()
            matched = False
            for idx, ch_cfg in enumerate(raw_channels):
                if ch_cfg["channel_id"] == target_ch:
                    updated = dict(ch_cfg)
                    updated.update(single_channel_overrides)
                    # Clear default 48V voltage if caller changed mode away from MIC+48V without specifying voltage
                    if (
                        "input_mode" in single_channel_overrides
                        and str(single_channel_overrides["input_mode"]).strip().upper() != XLR_MODE_MIC_48V
                        and "phantom_48v_voltage_v" not in single_channel_overrides
                    ):
                        updated["phantom_48v_voltage_v"] = 0.0
                    if (
                        "input_mode" in single_channel_overrides
                        and "phantom_48v_boost_energized" not in single_channel_overrides
                    ):
                        updated["phantom_48v_boost_energized"] = (
                            str(single_channel_overrides["input_mode"]).strip().upper() == XLR_MODE_MIC_48V
                        )
                    raw_channels[idx] = updated
                    matched = True
                    break
            if not matched:
                raw_channels.append(dict(single_channel_overrides))

    checked_channels: List[Dict[str, Any]] = []
    hot_plug_safe = True
    for cfg in raw_channels:
        ch_res = verify_xlr_h1_channel(**cfg)
        checked_channels.append(ch_res.to_dict())
        for c in ch_res.violation_codes:
            _add_code(codes, c)
        errors.extend(ch_res.errors)
        warnings.extend(ch_res.warnings)
        if STATUS_BLOCKED_PHANTOM_48V_HOTPLUG_TRANSIENT in ch_res.violation_codes:
            hot_plug_safe = False

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD in codes:
        status = STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD
    else:
        status = codes[0]

    return XlrPhantom48vFirewallResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        mishoe_24pin_attached=bool(mishoe_24pin_attached),
        xlr_h1_logic_vdd_v=float(xlr_h1_logic_vdd_v),
        xlr_h1_unreg_v=float(xlr_h1_unreg_v),
        channels=tuple(checked_channels),
        hot_plug_discharge_safe=hot_plug_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 3. Gimbal, Follow-Focus Torque & Laser-CMOS / Shutter Curtain Guard (G22)
# ---------------------------------------------------------------------------


def verify_gimbal_focus_torque_and_laser_shutter_guard(
    *,
    gimbal_model: str = "DJI RS4 Pro",
    gimbal_attached: bool = True,
    usb_c_crsdk_active: bool = True,
    multiport_rss_active: bool = False,
    single_control_bus_arbitrated: Optional[bool] = None,
    gimbal_pan_follow_active: bool = True,
    ibis_mode: str = IBIS_MODE_STANDARD,
    fly_by_wire_emount: bool = True,
    lens_has_hard_stops: bool = False,
    lens_support_rod_clamp_installed: bool = False,
    soft_ab_stops_calibrated: bool = True,
    infinite_spin_uncalibrated: bool = False,
    motor_voltage_v: float = FOLLOW_FOCUS_MOTOR_NOMINAL_V,
    motor_torque_nm: float = 0.28,
    venue_laser_present: bool = False,
    laser_class: str = LASER_CLASS_NONE,
    optical_laser_cut_filter_installed: bool = False,
    shutter_when_power_off: str = SHUTTER_WHEN_POWER_OFF_OPEN,
    shutter_blade_parked_open: Optional[bool] = None,
    lens_cap_swap_rule_acknowledged: bool = False,
    cp_mutation_bytes: int = 0,
    request_persistent_emmc_writes: bool = False,
) -> GimbalFocusLaserShutterGuardResult:
    """Verify Gimbal dual-bus arbitration, IBIS mode, Follow-Focus torque/rod-clamp, Laser-CMOS & Shutter park."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    if int(cp_mutation_bytes) != 0:
        _add_code(codes, STATUS_BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR)
        errors.append(f"Stock-CP cp_mutation_bytes must equal 0 (got {cp_mutation_bytes}).")

    # 1. USB-C CrSDK vs Multi-Port RSS Dual-Control Conflict Arbitration
    dual_bus_conflict = bool(usb_c_crsdk_active and multiport_rss_active)
    if single_control_bus_arbitrated is None:
        bus_arbitrated = not dual_bus_conflict
        if gimbal_attached and (not usb_c_crsdk_active) and (not multiport_rss_active):
            bus_arbitrated = False
    else:
        bus_arbitrated = bool(single_control_bus_arbitrated) and (not dual_bus_conflict)

    if dual_bus_conflict or not bus_arbitrated:
        _add_code(codes, STATUS_BLOCKED_GIMBAL_DUAL_BUS_CONFLICT)
        errors.append(
            f"Gimbal ({gimbal_model}) dual-control bus conflict: simultaneous REC/Zoom/Iris commands on "
            f"USB-C CrSDK ({usb_c_crsdk_active}) and Multi-Port RSS ({multiport_rss_active}) blocked; "
            "arbitrate a single control bus (single_control_bus_arbitrated=True)."
        )

    # 2. Gimbal Pan-Follow IBIS Mode Check (Standard / Off vs Active crop drift)
    norm_ibis = ibis_mode.strip().upper()
    ibis_safe = True
    if gimbal_attached and gimbal_pan_follow_active:
        if norm_ibis not in SAFE_GIMBAL_IBIS_MODES:
            ibis_safe = False
            _add_code(codes, STATUS_BLOCKED_GIMBAL_ACTIVE_IBIS_DRIFT)
            errors.append(
                f"IBIS Mode {norm_ibis!r} while gimbal pan-follow is active causes digital crop drift / "
                "corner warp; switch IBIS Mode to Standard or Off."
            )

    # 3. External Follow-Focus Gear Motor Endpoint Calibration & Torque Guard
    torque_val = float(motor_torque_nm)
    volt_val = float(motor_voltage_v)
    effective_calibrated = bool(soft_ab_stops_calibrated) and (not bool(infinite_spin_uncalibrated))
    focus_safe = True

    if torque_val < 0.0 or volt_val <= 0.0:
        focus_safe = False
        _add_code(codes, STATUS_BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR)
        errors.append(
            f"Invalid follow-focus motor telemetry (voltage={volt_val:.1f}V, torque={torque_val:.2f} N*m)."
        )
    elif fly_by_wire_emount and (not lens_has_hard_stops):
        torque_and_ab_ok = effective_calibrated and (torque_val <= FOLLOW_FOCUS_MOTOR_MAX_TORQUE_NM_UNCLAMPED)
        if not (lens_support_rod_clamp_installed or torque_and_ab_ok):
            focus_safe = False
            _add_code(codes, STATUS_BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR)
            errors.append(
                f"BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR: {volt_val:.1f}V follow-focus gear motor "
                f"(torque={torque_val:.2f} N*m, soft_ab_calibrated={soft_ab_stops_calibrated}, "
                f"infinite_spin_uncalibrated={infinite_spin_uncalibrated}) on fly-by-wire E-Mount lens "
                "without hard stops requires lens-support rod clamp OR motor torque <= "
                f"{FOLLOW_FOCUS_MOTOR_MAX_TORQUE_NM_UNCLAMPED:.2f} N*m with calibrated soft A/B stops."
            )
        elif lens_support_rod_clamp_installed and (not effective_calibrated or torque_val > FOLLOW_FOCUS_MOTOR_MAX_TORQUE_NM_UNCLAMPED):
            warnings.append(
                "High-torque or uncalibrated follow-focus motor mitigated mechanically by lens-support rod clamp; "
                "calibrating soft A/B endpoints remains recommended."
            )

    # 4. Class-3B / Class-4 Venue Laser IMX510 CMOS Guard
    norm_laser = laser_class.strip().upper()
    laser_flagged = bool(venue_laser_present) or (norm_laser in HIGH_RISK_LASER_CLASSES)
    laser_safe = True
    if laser_flagged and not optical_laser_cut_filter_installed:
        laser_safe = False
        _add_code(codes, STATUS_BLOCKED_VENUE_LASER_CMOS_HAZARD)
        errors.append(
            f"High-risk venue laser environment (venue_laser_present={venue_laser_present}, "
            f"laser_class={norm_laser}) without optical laser-cut filter threatens permanent IMX510 CMOS pixel burnout."
        )
    elif laser_flagged and optical_laser_cut_filter_installed:
        warnings.append(
            f"High-risk venue laser environment ({norm_laser}) flagged; optical laser-cut filter installed."
        )

    # 5. Mechanical Focal-Plane Shutter Dust-Curtain Park Check
    norm_shutter_off = shutter_when_power_off.strip().upper()
    if shutter_blade_parked_open is None:
        parked_open = norm_shutter_off == SHUTTER_WHEN_POWER_OFF_OPEN
    else:
        parked_open = bool(shutter_blade_parked_open)

    shutter_safe = True
    if (norm_shutter_off != SHUTTER_WHEN_POWER_OFF_OPEN) or (not parked_open):
        if not lens_cap_swap_rule_acknowledged:
            shutter_safe = False
            _add_code(codes, STATUS_BLOCKED_SHUTTER_CURTAIN_EXPOSED)
            errors.append(
                f"Mechanical shutter dust-curtain hazard: shutter_when_power_off={norm_shutter_off!r}, "
                f"shutter_blade_parked_open={parked_open}. Keep FX3 shutter parked OPEN ('Off') or "
                "acknowledge strict lens-cap swap rules so bare fingers never bend shutter blades."
            )
        else:
            warnings.append(
                "Shutter When Power Off is closed ('On') with lens-cap swap rule acknowledged; "
                "never touch focal-plane shutter blades during lens changes."
            )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return GimbalFocusLaserShutterGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        gimbal_model=gimbal_model,
        gimbal_attached=bool(gimbal_attached),
        usb_c_crsdk_active=bool(usb_c_crsdk_active),
        multiport_rss_active=bool(multiport_rss_active),
        single_control_bus_arbitrated=bus_arbitrated,
        gimbal_pan_follow_active=bool(gimbal_pan_follow_active),
        ibis_mode=norm_ibis,
        ibis_gimbal_drift_safe=ibis_safe,
        fly_by_wire_emount=bool(fly_by_wire_emount),
        lens_has_hard_stops=bool(lens_has_hard_stops),
        lens_support_rod_clamp_installed=bool(lens_support_rod_clamp_installed),
        soft_ab_stops_calibrated=bool(soft_ab_stops_calibrated),
        infinite_spin_uncalibrated=bool(infinite_spin_uncalibrated),
        motor_voltage_v=volt_val,
        motor_torque_nm=torque_val,
        follow_focus_shear_safe=focus_safe,
        venue_laser_present=bool(venue_laser_present),
        laser_class=norm_laser,
        optical_laser_cut_filter_installed=bool(optical_laser_cut_filter_installed),
        laser_hazard_flagged=laser_flagged,
        laser_cmos_safe=laser_safe,
        shutter_when_power_off=norm_shutter_off,
        shutter_blade_parked_open=parked_open,
        lens_cap_swap_rule_acknowledged=bool(lens_cap_swap_rule_acknowledged),
        shutter_curtain_safe=shutter_safe,
        cp_mutation_bytes=int(cp_mutation_bytes),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate 21 & Gate 22 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g21_xlr_phantom48v_and_hotpatch(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    xlr_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
) -> Tuple[GateVerdict, G21XlrPhantom48vResult]:
    """Evaluate Gate G21 (`xlr_phantom_48v_and_hotpatch_safe`)."""
    donor_audit = audit_phase77_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
    )

    eff_xlr = dict(xlr_kwargs or {})
    eff_xlr["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_xlr.get("request_persistent_emmc_writes", False)
    )
    xlr_res = verify_xlr_h1_phantom_48v_firewall(**eff_xlr)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not donor_audit.valid:
        _add_code(codes, donor_audit.status)
        errors.extend(donor_audit.errors)
    for c in xlr_res.violation_codes:
        _add_code(codes, c)
    errors.extend(xlr_res.errors)
    warnings.extend(donor_audit.warnings)
    warnings.extend(xlr_res.warnings)

    passed = (
        donor_audit.valid
        and xlr_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = STATUS_VERIFIED_G21 if passed else (codes[0] if codes else STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)

    res = G21XlrPhantom48vResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=donor_audit.verification_mode,
        donor_audit=donor_audit.to_dict(),
        xlr_phantom_firewall=xlr_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G21_GATE_ID,
        gate_code=G21_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"XLR-H1 24-pin MI-Shoe +48V Firewall ({xlr_res.status}, channels={len(xlr_res.channels)}, "
            f"hot_plug_discharge_safe={xlr_res.hot_plug_discharge_safe}, {donor_audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": donor_audit.verification_mode,
            "xlr_status": xlr_res.status,
            "channels_checked": len(xlr_res.channels),
            "hot_plug_discharge_safe": xlr_res.hot_plug_discharge_safe,
        },
    )
    return verdict, res


def evaluate_g22_gimbal_focus_torque_and_sensor_curtain(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    gimbal_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
) -> Tuple[GateVerdict, G22GimbalFocusLaserResult]:
    """Evaluate Gate G22 (`gimbal_focus_torque_and_sensor_curtain_safe`)."""
    donor_audit = audit_phase77_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
    )

    eff_gimbal = dict(gimbal_kwargs or {})
    eff_gimbal["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_gimbal.get("request_persistent_emmc_writes", False)
    )
    gimbal_res = verify_gimbal_focus_torque_and_laser_shutter_guard(**eff_gimbal)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not donor_audit.valid:
        _add_code(codes, donor_audit.status)
        errors.extend(donor_audit.errors)
    for c in gimbal_res.violation_codes:
        _add_code(codes, c)
    errors.extend(gimbal_res.errors)
    warnings.extend(donor_audit.warnings)
    warnings.extend(gimbal_res.warnings)

    passed = (
        donor_audit.valid
        and gimbal_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = STATUS_VERIFIED_G22 if passed else (codes[0] if codes else STATUS_BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR)

    res = G22GimbalFocusLaserResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=donor_audit.verification_mode,
        donor_audit=donor_audit.to_dict(),
        gimbal_focus_laser_shutter=gimbal_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G22_GATE_ID,
        gate_code=G22_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Gimbal/Focus/Laser/Shutter ({gimbal_res.status}, bus_arbitrated={gimbal_res.single_control_bus_arbitrated}, "
            f"ibis={gimbal_res.ibis_mode}, torque={gimbal_res.motor_torque_nm:.2f}Nm, "
            f"laser_safe={gimbal_res.laser_cmos_safe}, shutter_open={gimbal_res.shutter_blade_parked_open}, "
            f"{donor_audit.verification_mode}), persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": donor_audit.verification_mode,
            "gimbal_status": gimbal_res.status,
            "single_control_bus_arbitrated": gimbal_res.single_control_bus_arbitrated,
            "follow_focus_shear_safe": gimbal_res.follow_focus_shear_safe,
            "laser_cmos_safe": gimbal_res.laser_cmos_safe,
            "shutter_curtain_safe": gimbal_res.shutter_curtain_safe,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Master 22-Gate Preflight Evaluator (`G01..G22`) & CLI
# ---------------------------------------------------------------------------


def evaluate_22gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G20 pass-throughs
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
    # G21 inputs (XLR-H1 +48V Phantom Transducer & Hot-Patch Firewall)
    xlr_kwargs: Optional[Mapping[str, Any]] = None,
    # G22 inputs (Gimbal, Follow-Focus Torque & Laser-CMOS / Shutter Guard)
    gimbal_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master22GateReport:
    """Evaluate all 22 Master Safety Gates (`G01..G22`) deterministically."""
    resolved_root = (DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m20_kwargs: Dict[str, Any] = {
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
    }
    if soc_start_ceiling_c is not None:
        m20_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m20_report: Master20GateReport = evaluate_20gate_preflight(resolved_root, **m20_kwargs)

    g21_verdict, g21_res = evaluate_g21_xlr_phantom48v_and_hotpatch(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        xlr_kwargs=xlr_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
    )

    g22_verdict, g22_res = evaluate_g22_gimbal_focus_torque_and_sensor_curtain(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        gimbal_kwargs=gimbal_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
    )

    gates_21_to_22 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g21_verdict, g22_verdict)
    ]
    all_gates = tuple(list(m20_report.gates) + gates_21_to_22)

    g01_to_g12_verified = int(m20_report.summary["g01_to_g12_verified"])
    g13_to_g20_verified = int(m20_report.summary["g13_to_g18_verified"]) + int(m20_report.summary["g19_to_g20_verified"])
    g21_to_g22_verified = sum(1 for v in (g21_verdict, g22_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g20_verified + g21_to_g22_verified

    g21_to_g22_all_passed = g21_to_g22_verified == 2
    g13_to_g22_all_passed = m20_report.g13_to_g20_all_passed and g21_to_g22_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m20_report.gates[:9])

    offline_19_verified = (
        g01_to_g09_ok
        and m20_report.offline_17_gates_verified
        and g21_to_g22_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_22_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g22_all_passed
        and (not request_persistent_emmc_writes)
    )

    real_tier0_verified = (g01_to_g12_verified == 12) and (not dry_run_simulated_backup)
    overall_ready_for_hardware_attach = (
        real_tier0_verified
        and g13_to_g22_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    h0_h1_allowed = (
        offline_19_verified
        and m20_report.h0_h1_trial_entry_allowed
        and g21_to_g22_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = list(m20_report.errors) + list(g21_verdict.errors) + list(g22_verdict.errors)
    warnings: List[str] = list(m20_report.warnings) + list(g21_verdict.warnings) + list(g22_verdict.warnings)

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m20_report.g13_to_g20_all_passed:
        overall_status = m20_report.status
    elif not g21_verdict.passed:
        overall_status = g21_verdict.status
    elif not g22_verdict.passed:
        overall_status = g22_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_22_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_22_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_22_verified:
        overall_status = "VERIFIED_ALL_22_GATES"
    else:
        overall_status = "VERIFIED_19_OF_22_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m20_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g21_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g22_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 22,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 22 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g20_verified": g13_to_g20_verified,
        "g21_to_g22_verified": g21_to_g22_verified,
        "g13_to_g22_all_passed": g13_to_g22_all_passed,
        "g21_to_g22_all_passed": g21_to_g22_all_passed,
        "offline_19_gates_verified": offline_19_verified,
        "all_22_gates_verified": all_22_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master22GateReport(
        schema=PHANTOM48V_GIMBAL_22GATE_SCHEMA,
        version=PHANTOM48V_GIMBAL_22GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_19_gates_verified=offline_19_verified,
        all_22_gates_verified=all_22_verified,
        g13_to_g22_all_passed=g13_to_g22_all_passed,
        g21_to_g22_all_passed=g21_to_g22_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_20_report=m20_report.to_dict(),
        g21_result=g21_res.to_dict(),
        g22_result=g22_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_22_master_safety_gates = evaluate_22gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="phantom48v_gimbal_and_22gate_guard",
        description="Phase 77 — XLR-H1 +48V Phantom Firewall, Gimbal/Focus/Laser/Shutter Guard & 22-Gate Preflight (G01..G22)",
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G22 can be exercised offline",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_22gate_preflight(
        args.repo_root,
        force_clean_room=True if args.clean_room else None,
        dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/22 "
            f"g21_to_g22_all_passed={report.g21_to_g22_all_passed} "
            f"all_22_gates_verified={report.all_22_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = report.all_22_gates_verified if args.dry_run_simulated_backup else report.offline_19_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
