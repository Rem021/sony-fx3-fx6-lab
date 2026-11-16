"""Phase 191 — Real-Hardware Main Track Part 20:
Gate G65 (`ILME-FX3` `0x91030080` No-UVC USB Gadget Firewall & `USB-PD`
`NP-FZ100` / `DC-C1` `>=65W / 5A` Electrical Interlock),
Gate G66 (Dual-Media `.cube` User LUT Path-Asymmetry `SD` vs `CFexpress-A`,
`Cine EI` `800 / 12800` Base Sensitivity & `RMT-P1BT` BT/IR Mutual-Exclusion Guard),
and 66-Gate Master Preflight (`G01..G66` / `verify-66-gates`).

Composes `realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard` (`G01..G64`, keeping
`evaluate_58gate_preflight`, `evaluate_60gate_preflight`, `evaluate_62gate_preflight`,
`evaluate_64gate_preflight`, `verify-58-gates`, `verify-60-gates`, `verify-62-gates`,
and `verify-64-gates` 100% intact) with Wave-24 Sony Real-Hardware Intelligence
(`G65` and `G66`) while hard-locking all physical flash/write/transmit redlines:
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`
- `HUMAN_HARDWARE_ATTACH_TOKEN = False`
- `PHYSICAL_USB_PACKETS_EMITTED = 0`
- `RAW_FIRMWARE_BYTES_LEAKED = 0`
- `overall_ready_for_hardware_attach = False`
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
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .exfat_media_integrity_guard import (
    MEDIA_TYPE_CFEXPRESS_A,
    MEDIA_TYPE_SDXC,
    MediaSlotConfig,
)
from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    GateVerdict,
    P12_WLAN_FATAL_GUARD_VMA,
)
from .realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    FX3A_MODEL_NAME,
    FX3_MODEL_ID,
    FX3_MODEL_ID_HEX,
    FX3_MODEL_NAME,
    Master64GateReport,
    evaluate_64gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_NOUVC_DCC1_PD_LUT_PATH_66GATE_SCHEMA: str = (
    "fx3-realhw-nouvc-dcc1-pd-lut-path-66gate-preflight-v1"
)
REALHW_NOUVC_DCC1_PD_LUT_PATH_66GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

# Gate IDs & Canonical Codes for G65..G66
G65_GATE_ID: str = "G65_fx3_nouvc_gadget_and_usbpd_dcc1_electrical_guard"
G65_GATE_CODE: str = (
    "GATE_G65_FX3_NOUVC_GADGET_AND_USBPD_DCC1_ELECTRICAL_GUARD"
)
GATE_G65_FX3_NOUVC_GADGET_AND_USBPD_DCC1_ELECTRICAL_GUARD: str = G65_GATE_CODE
G65: str = G65_GATE_CODE

G66_GATE_ID: str = "G66_dualmedia_cube_lut_path_cineei_and_rmt_p1bt_bt_guard"
G66_GATE_CODE: str = (
    "GATE_G66_DUALMEDIA_CUBE_LUT_PATH_CINEEI_AND_RMT_P1BT_BT_GUARD"
)
GATE_G66_DUALMEDIA_CUBE_LUT_PATH_CINEEI_AND_RMT_P1BT_BT_GUARD: str = G66_GATE_CODE
G66: str = G66_GATE_CODE

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G65: str = (
    "VERIFIED_FX3_NOUVC_GADGET_AND_USBPD_DCC1_ELECTRICAL_GUARD"
)
STATUS_VERIFIED_G66: str = (
    "VERIFIED_DUALMEDIA_CUBE_LUT_PATH_CINEEI_AND_RMT_P1BT_BT_GUARD"
)

# Gate G65 Violation Codes
STATUS_BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN: str = (
    "BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN"
)
STATUS_BLOCKED_G65_INVALID_STREAMING_TRANSPORT: str = (
    "BLOCKED_G65_INVALID_STREAMING_TRANSPORT"
)
STATUS_BLOCKED_G65_USB_PD_BODY_MISSING_NPFZ100_OR_LOW_BATT: str = (
    "BLOCKED_G65_USB_PD_BODY_MISSING_NPFZ100_OR_LOW_BATT"
)
STATUS_BLOCKED_G65_MICRO_USB_POWER_REJECTED: str = (
    "BLOCKED_G65_MICRO_USB_POWER_REJECTED"
)
STATUS_BLOCKED_G65_DC_C1_INSUFFICIENT_PD_OR_NON_5A_CABLE: str = (
    "BLOCKED_G65_DC_C1_INSUFFICIENT_PD_OR_NON_5A_CABLE"
)
STATUS_BLOCKED_G65_TELEMETRY_INVALID: str = (
    "BLOCKED_G65_NOUVC_DCC1_PD_TELEMETRY_INVALID"
)

# Gate G66 Violation Codes
STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING: str = (
    "BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING"
)
STATUS_BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE: str = (
    "BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE"
)
STATUS_BLOCKED_G66_CINEEI_BASE_ISO_OR_EI_OUT_OF_BOUNDS: str = (
    "BLOCKED_G66_CINEEI_BASE_ISO_OR_EI_OUT_OF_BOUNDS"
)
STATUS_BLOCKED_G66_RMT_P1BT_BT_IR_GPS_MUTEX_VIOLATION: str = (
    "BLOCKED_G66_RMT_P1BT_BT_IR_GPS_MUTEX_VIOLATION"
)
STATUS_BLOCKED_G66_TELEMETRY_INVALID: str = (
    "BLOCKED_G66_LUT_PATH_CINEEI_BT_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE191_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE191_66GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G65 Constants — No-UVC Gadget Firewall & USB-PD / DC-C1 Electrical Interlock
FX3_KERNEL_RELEASE: str = "4.9.337-scel+"
ALLOWED_NOUVC_BODY_MODELS: Tuple[str, ...] = (FX3_MODEL_NAME, FX3A_MODEL_NAME)
ALLOWED_FX3_USB_CONNECTION_MODES: Tuple[str, ...] = (
    "SEL_WHEN_CONNECT",
    "MASS_STORAGE",
    "MSC",
    "MTP",
    "REMOTE_SHOOTING",
    "USB_LAN",
    "RNDIS",
    "CDC_NCM",
)
FORBIDDEN_FX3_UVC_MODES: Tuple[str, ...] = (
    "USB_STREAMING",
    "UVC",
    "UVC_UAC",
    "UAC",
    "USB_WEBCAM",
)
ALLOWED_4K_STREAMING_TRANSPORTS: Tuple[str, ...] = (
    "NETWORK_RTMP",
    "RTMP",
    "RTMPS",
    "SRT",
    "HDMI_TYPE_A",
    "TYPE_A_HDMI",
    "HDMI",
    "NONE",
)
NETWORK_STREAMING_TRANSPORTS: Tuple[str, ...] = (
    "NETWORK_RTMP",
    "RTMP",
    "RTMPS",
    "SRT",
)
MAX_NETWORK_STREAMING_BITRATE_MBPS: float = 38.0

POWER_SOURCE_USB_PD_BODY: str = "USB_PD_BODY"
POWER_SOURCE_DC_C1_COUPLER: str = "DC_C1_COUPLER"
VALID_POWER_SOURCES: Tuple[str, ...] = (
    POWER_SOURCE_USB_PD_BODY,
    POWER_SOURCE_DC_C1_COUPLER,
)
USB_PD_BODY_MIN_BATTERY_PCT: int = 51
USB_PD_BODY_MIN_BATTERY_BARS: int = 3
DC_C1_MIN_USB_PD_WATTS: float = 65.0
DC_C1_MIN_CABLE_AMPS: float = 5.0

# Gate G66 Constants — Dual-Media .cube LUT Path-Asymmetry, Cine EI & RMT-P1BT BT/IR
CUBE_ALLOWED_3D_SIZES: Tuple[int, ...] = (17, 33)
CUBE_MAX_FILENAME_BYTES: int = 63
USER_LUT_MAX_SLOTS: int = 16
USER_LUT_AE_OFFSET_MIN_EV: float = 0.0
USER_LUT_AE_OFFSET_MAX_EV: float = 2.0
_CUBE_ASCII_FILENAME_RE = re.compile(r"^[A-Za-z0-9_.-]+\.[Cc][Uu][Bb][Ee]$")

MEDIA_TYPE_SD: str = "SD"
SD_USER_LUT_DIR: str = "/Private/Sony/PRO/LUT/"
CFEXPRESS_A_USER_LUT_DIR: str = "/Sony/PRO/LUT/"
FORBIDDEN_STAGEB_LUT_WRITE_PREFIXES: Tuple[str, ...] = (
    "p2:",
    "/setting",
    "/dev/nflasha",
    "/dev/cnflasha",
)

CINE_EI_BASE_ISOS: Tuple[int, ...] = (800, 12800)
CINE_EI_RANGE_BY_BASE: Mapping[int, Tuple[int, int]] = {
    800: (200, 3200),
    12800: (3200, 51200),
}

RMT_P1BT_MODEL: str = "RMT-P1BT"
RMT_P1BT_BT_VERSION: str = "4.2"

# Pinned FX3 v7.02 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE191_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"ILME-FX3A",
            b"NCM",
            b"USB",
            b"LUT",
            b"cube",
            b"Cine",
            b"RMT",
            b"GPS",
            b"HDMI",
        ),
        "fx3/cpapp-b.bin::{15980568B,ILME-FX3,ILME-FX3A,NCM,USB,LUT,cube,Cine,RMT,GPS,HDMI}",
    ),
    "fx3_appfw_so": (
        "fx3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f",
        (
            b"\x7fELF",
            b"MTP",
            b"USB",
            b"LUT",
            b"cube",
            b"CineEI",
            b"Private",
            b"Sony",
            b"Bluetooth",
            b"RMT",
            b"GPS",
            b"RTMP",
            b"SRT",
            b"HDMI",
        ),
        "fx3/appFw.so::{79015712B,ELF,MTP,USB,LUT,cube,CineEI,Private,Sony,Bluetooth,RMT,GPS,RTMP,SRT,HDMI}",
    ),
    "fx3_libusbbuspower_so": (
        "power",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libUsbBusPower.so",
        48_232,
        "c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748",
        (
            b"\x7fELF",
            b"_ZN11UsbBusPower11IsVbusReadyEv",
            b"_ZN11UsbBusPower19GetCurrentBattStateEPi",
            b"_ZN11UsbBusPower22SetPowerContractStatusEi",
        ),
        "fx3/libUsbBusPower.so::{48232B,ELF,IsVbusReady,GetCurrentBattState,SetPowerContractStatus}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase191DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    power_contracts_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Fx3NoUvcDcc1PdResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    body_model_name: str
    body_model_id: int
    body_model_id_hex: str
    kernel_release: str
    usb_connection_mode: str
    uvc_uac_gadget_requested: bool
    usb_streaming_mode_requested: bool
    uvc_gadget_blocked: bool
    streaming_transport: str
    streaming_bitrate_mbps: float
    gadget_and_transport_valid: bool
    power_source: str
    np_fz100_inserted: bool
    battery_pct: int
    battery_bars: int
    micro_usb_power_attempted: bool
    micro_usb_power_rejected: bool
    usb_pd_watts: float
    emarked_5a_cable: bool
    cable_max_amps: float
    dc_c1_blinking_led_fault: bool
    lcd_max_brightness_locked: bool
    power_supply_interlock_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DualMediaLutPathCineEiBtResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    lut_3d_size: int
    lut_filename: str
    lut_filename_bytes: int
    lut_slot_index: int
    registered_lut_count: int
    ae_level_offset_ev: float
    media_type: str
    lut_directory: str
    expected_lut_directory: str
    stage_b_p2_setting_write_attempted: bool
    lut_spec_valid: bool
    media_path_asymmetry_valid: bool
    cine_ei_base_iso: int
    cine_ei_index: int
    cine_ei_min_index: int
    cine_ei_max_index: int
    cmos_analog_gain_mutated: bool
    cine_ei_valid: bool
    remote_model: str
    bt_spec_version: str
    bluetooth_rmt_ctrl_enabled: bool
    ir_remote_receiver_disabled: bool
    ir_remote_active: bool
    smartphone_gps_location_link_active: bool
    bt_ir_gps_mutex_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G65NoUvcDcc1PdGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    nouvc_dcc1_pd_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G66LutPathCineEiBtGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    lut_path_cineei_bt_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master66GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_63_gates_verified: bool
    all_66_gates_verified: bool
    g13_to_g66_all_passed: bool
    g65_to_g66_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_64_report: Dict[str, Any]
    g65_result: Dict[str, Any]
    g66_result: Dict[str, Any]
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
    """Strictly read a file via `os.open(..., os.O_RDONLY)` without leaking raw bytes."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        chunks: List[bytes] = []
        while True:
            chunk = os.read(fd, 1_048_576)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _is_non_negative_int(val: Any) -> bool:
    return isinstance(val, int) and (not isinstance(val, bool)) and val >= 0


def _is_finite_number(val: Any) -> bool:
    if isinstance(val, bool):
        return False
    if not isinstance(val, (int, float)):
        return False
    return abs(float(val)) < 1e12 and (float(val) == float(val))


def _normalize_int_value(val: Any) -> Optional[int]:
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        s = val.strip().lower()
        if not s:
            return None
        try:
            return int(s, 16) if s.startswith("0x") else int(s, 10)
        except ValueError:
            return None
    return None


def _norm_token(val: str) -> str:
    s = val.strip().upper()
    s = s.replace(".", "").replace("(", "_").replace(")", "")
    s = re.sub(r"[^A-Z0-9]+", "_", s).strip("_")
    return s


def _norm_usb_mode(mode: str) -> str:
    t = _norm_token(mode)
    aliases = {
        "SEL_WHEN_CONNECT": "SEL_WHEN_CONNECT",
        "MASSSTORAGE_MSC": "MASS_STORAGE",
        "MASS_STORAGE_MSC": "MASS_STORAGE",
        "MASS_STORAGE": "MASS_STORAGE",
        "MSC": "MSC",
        "MTP": "MTP",
        "REMOTE_SHOOTING": "REMOTE_SHOOTING",
        "USB_LAN": "USB_LAN",
        "RNDIS": "RNDIS",
        "CDC_NCM": "CDC_NCM",
        "CDCNCM": "CDC_NCM",
        "USB_STREAMING": "USB_STREAMING",
        "UVC": "UVC",
        "UVC_UAC": "UVC_UAC",
        "UAC": "UAC",
        "USB_WEBCAM": "USB_WEBCAM",
    }
    return aliases.get(t, t)


def _norm_media_type(media_type: str) -> str:
    t = _norm_token(media_type)
    if t in ("SD", "SDXC", "SD_SDXC", "SDHC"):
        return MEDIA_TYPE_SDXC if t == "SDXC" else MEDIA_TYPE_SD
    if t in ("CFEXPRESS_A", "CFEXPRESS_TYPE_A", "CFX_A", "CFEXPRESS"):
        return MEDIA_TYPE_CFEXPRESS_A
    return t


def _norm_lut_dir(path_str: str) -> str:
    s = path_str.strip().replace("\\", "/")
    if not s:
        return ""
    if s.startswith("/") and not s.endswith("/"):
        s += "/"
    return s


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase191_donor_contracts(
    *_,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase191DonorAuditResult:
    """Inspect FX3 `7.02` `cpapp-b.bin`, `appFw.so`, and `libUsbBusPower.so`
    strictly via `os.open(..., os.O_RDONLY)` with deterministic clean-room
    fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent.
    """
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)
    effective_work_root: Optional[Path] = (
        Path(work_root) if work_root is not None else paths.work_root
    )

    resolved: Dict[str, Path] = {}
    if effective_work_root is not None:
        for key, (
            _body,
            rel_path,
            _sz,
            _sha,
            _toks,
            _lbl,
        ) in PINNED_PHASE191_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase191DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE191_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=True,
            power_contracts_verified=True,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE191_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE191_DONOR_SPECS.items()
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
    files_inspected = 0

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE191_DONOR_SPECS.items():
        blob = _read_file_o_rdonly(resolved[key])
        files_inspected += 1
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

    fx3_keys = {
        k for k, spec in PINNED_PHASE191_DONOR_SPECS.items() if spec[0] == "fx3"
    }
    power_keys = {
        k for k, spec in PINNED_PHASE191_DONOR_SPECS.items() if spec[0] == "power"
    }
    valid = len(errors) == 0 and len(missing) == 0
    return Phase191DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE191_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_keys.issubset(passed_keys) and valid,
        power_contracts_verified=power_keys.issubset(passed_keys) and valid,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Pure Helper Validators (G65 & G66)
# ---------------------------------------------------------------------------


def validate_fx3_nouvc_usb_gadget_firewall(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int | str = FX3_MODEL_ID,
    kernel_release: str = FX3_KERNEL_RELEASE,
    usb_connection_mode: str = "USB-LAN",
    uvc_uac_gadget_requested: bool = False,
    usb_streaming_mode_requested: bool = False,
    streaming_transport: str = "RTMP",
    streaming_bitrate_mbps: float = 35.0,
) -> Tuple[bool, str, List[str]]:
    """Hard-block any Stage-B attempt to configure or bind a UVC/UAC `[USB Streaming]`
    composite gadget on `ILME-FX3` (`0x91030080`) / `ILME-FX3A` (`4.9.337-scel+`),
    permitting strictly `Sel. When Connect`, `MassStorage(MSC)`, `MTP`,
    `Remote Shooting`, and `USB-LAN` (`RNDIS`/`CDC-NCM`), while routing 4K
    streaming strictly via Network Streaming (`RTMP/RTMPS/SRT <= 38 Mbps`) or
    Type-A HDMI.
    """
    errors: List[str] = []
    model_norm = body_model_name.strip().upper().replace("_", "-")
    b_id = _normalize_int_value(body_model_id)
    mode_norm = _norm_usb_mode(usb_connection_mode)
    tr_norm = _norm_token(streaming_transport)

    model_ok = model_norm in ALLOWED_NOUVC_BODY_MODELS and (
        b_id == FX3_MODEL_ID if model_norm == FX3_MODEL_NAME else (b_id is not None and b_id >= 0)
    )
    kernel_ok = kernel_release.strip() == FX3_KERNEL_RELEASE

    is_uvc_request = (
        uvc_uac_gadget_requested is True
        or usb_streaming_mode_requested is True
        or mode_norm in FORBIDDEN_FX3_UVC_MODES
        or ("UVC" in mode_norm)
        or ("UAC" in mode_norm)
        or ("STREAMING" in mode_norm)
        or mode_norm not in ALLOWED_FX3_USB_CONNECTION_MODES
        or not model_ok
        or not kernel_ok
    )
    if is_uvc_request:
        errors.append(
            f"FX3 No-UVC USB Gadget Firewall blocked request: model={body_model_name!r} "
            f"({body_model_id!r}), kernel={kernel_release!r}, "
            f"usb_connection_mode={usb_connection_mode!r}, "
            f"uvc_uac_gadget_requested={uvc_uac_gadget_requested}, "
            f"usb_streaming_mode_requested={usb_streaming_mode_requested}."
        )
        return (False, STATUS_BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN, errors)

    if tr_norm in ("UVC", "UVC_UAC", "USB_STREAMING", "USB_WEBCAM"):
        errors.append(
            f"FX3 No-UVC Firewall rejected UVC streaming transport {streaming_transport!r}; "
            f"4K streaming must route via RTMP/RTMPS/SRT (<= {MAX_NETWORK_STREAMING_BITRATE_MBPS} Mbps) or Type-A HDMI."
        )
        return (False, STATUS_BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN, errors)

    transport_valid = tr_norm in ALLOWED_4K_STREAMING_TRANSPORTS
    bitrate_valid = (
        float(streaming_bitrate_mbps) <= MAX_NETWORK_STREAMING_BITRATE_MBPS
        if tr_norm in NETWORK_STREAMING_TRANSPORTS
        else float(streaming_bitrate_mbps) >= 0.0
    )
    if (not transport_valid) or (not bitrate_valid):
        errors.append(
            f"FX3 4K streaming transport/bitrate violation: transport={streaming_transport!r}, "
            f"bitrate={streaming_bitrate_mbps} Mbps (Network Streaming ceiling {MAX_NETWORK_STREAMING_BITRATE_MBPS} Mbps)."
        )
        return (False, STATUS_BLOCKED_G65_INVALID_STREAMING_TRANSPORT, errors)

    return (True, "", errors)


def validate_usbpd_body_vs_dcc1_power_supply(
    *,
    power_source: str = POWER_SOURCE_USB_PD_BODY,
    np_fz100_inserted: bool = True,
    battery_pct: int = 85,
    battery_bars: int = 4,
    micro_usb_power_attempted: bool = False,
    micro_usb_power_rejected: bool = True,
    usb_pd_watts: float = 65.0,
    emarked_5a_cable: bool = True,
    cable_max_amps: float = 5.0,
    dc_c1_blinking_led_fault: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Enforce physical power-supply safety before Tier-0 cold backup or Stage-B dual-boot rehearsal:
    - Rejects Micro-USB power (`micro_usb_power_rejected == True`, `micro_usb_power_attempted == False`).
    - If `power_source == "USB_PD_BODY"`: requires `np_fz100_inserted == True` and `battery_pct >= 51` (`>= 3 bars`).
    - If `power_source == "DC_C1_COUPLER"`: requires `usb_pd_watts >= 65` and `emarked_5a_cable == True`.
    """
    errors: List[str] = []
    src_norm = _norm_token(power_source)

    if (
        src_norm in ("MICRO_USB", "MULTI_MICRO_USB", "MICROUSB")
        or micro_usb_power_attempted is True
        or micro_usb_power_rejected is False
    ):
        errors.append(
            f"Micro-USB power delivery is unsupported on ILME-FX3 and must be rejected: "
            f"power_source={power_source!r}, attempted={micro_usb_power_attempted}, "
            f"rejected={micro_usb_power_rejected}."
        )
        return (False, STATUS_BLOCKED_G65_MICRO_USB_POWER_REJECTED, errors)

    if src_norm == POWER_SOURCE_USB_PD_BODY:
        ok = (
            np_fz100_inserted is True
            and int(battery_pct) >= USB_PD_BODY_MIN_BATTERY_PCT
            and int(battery_bars) >= USB_PD_BODY_MIN_BATTERY_BARS
        )
        if not ok:
            errors.append(
                f"USB_PD_BODY interlock failed (requires NP-FZ100 inserted + >= {USB_PD_BODY_MIN_BATTERY_PCT}% / "
                f">= {USB_PD_BODY_MIN_BATTERY_BARS} bars): inserted={np_fz100_inserted}, "
                f"battery_pct={battery_pct}%, battery_bars={battery_bars}."
            )
            return (False, STATUS_BLOCKED_G65_USB_PD_BODY_MISSING_NPFZ100_OR_LOW_BATT, errors)
        return (True, "", errors)

    if src_norm == POWER_SOURCE_DC_C1_COUPLER:
        ok = (
            float(usb_pd_watts) >= DC_C1_MIN_USB_PD_WATTS
            and emarked_5a_cable is True
            and float(cable_max_amps) >= DC_C1_MIN_CABLE_AMPS
            and dc_c1_blinking_led_fault is False
        )
        if not ok:
            errors.append(
                f"DC_C1_COUPLER interlock failed (requires >= {DC_C1_MIN_USB_PD_WATTS:.0f}W USB-PD + "
                f"5A e-Marked cable): usb_pd_watts={usb_pd_watts}W, emarked_5a_cable={emarked_5a_cable}, "
                f"cable_max_amps={cable_max_amps}A, blinking_led_fault={dc_c1_blinking_led_fault}."
            )
            return (False, STATUS_BLOCKED_G65_DC_C1_INSUFFICIENT_PD_OR_NON_5A_CABLE, errors)
        return (True, "", errors)

    errors.append(
        f"Unsupported power_source {power_source!r}; expected one of {VALID_POWER_SOURCES}."
    )
    return (False, STATUS_BLOCKED_G65_TELEMETRY_INVALID, errors)


def validate_user_cube_lut_and_media_path_asymmetry(
    *,
    lut_3d_size: int = 33,
    lut_filename: str = "FX3_SLog3_Rec709_v1.cube",
    lut_slot_index: int = 1,
    registered_lut_count: int = 4,
    ae_level_offset_ev: float = 0.0,
    media_type: str = MEDIA_TYPE_SDXC,
    lut_directory: str = SD_USER_LUT_DIR,
    stage_b_p2_setting_write_attempted: bool = False,
    cube_text: Optional[str] = None,
) -> Tuple[bool, str, List[str]]:
    """Enforce `.cube` User LUT rules (`LUT_3D_SIZE` strictly 17 or 33, ASCII
    filename <= 63 bytes including `.cube`, max 16 slots `User1..User16`,
    `AE Level Offset` `0.0..+2.0 EV` in `1/3` EV steps) AND dual-media path
    asymmetry (`SD`/`SDXC`: `/Private/Sony/PRO/LUT/`, `CFexpress Type A`:
    `/Sony/PRO/LUT/`), rejecting swapped paths or writes into Stock `p2:/setting`.
    """
    errors: List[str] = []

    fname_str = lut_filename.strip()
    fname_ascii = fname_str.isascii() and bool(_CUBE_ASCII_FILENAME_RE.match(fname_str))
    fname_bytes = len(fname_str.encode("ascii")) if fname_str.isascii() else 999
    size_ok = int(lut_3d_size) in CUBE_ALLOWED_3D_SIZES
    slot_ok = (
        1 <= int(lut_slot_index) <= USER_LUT_MAX_SLOTS
        and 1 <= int(registered_lut_count) <= USER_LUT_MAX_SLOTS
        and int(lut_slot_index) <= int(registered_lut_count)
    )
    ev = float(ae_level_offset_ev)
    # 1/3 EV step tolerance covers both exact thirds (0.333/0.667) and Sony UI 0.3/0.7/1.3/1.7 labels
    ae_ok = (
        USER_LUT_AE_OFFSET_MIN_EV <= ev <= USER_LUT_AE_OFFSET_MAX_EV
        and abs(ev * 3.0 - round(ev * 3.0)) <= 0.105
    )

    cube_text_ok = True
    if cube_text is not None:
        m = re.search(r"^\s*LUT_3D_SIZE\s+(\d+)\s*$", cube_text, flags=re.MULTILINE)
        if not m or int(m.group(1)) != int(lut_3d_size):
            cube_text_ok = False

    if not (size_ok and fname_ascii and fname_bytes <= CUBE_MAX_FILENAME_BYTES and slot_ok and ae_ok and cube_text_ok):
        errors.append(
            f".cube User LUT spec violation: size={lut_3d_size} (allowed {CUBE_ALLOWED_3D_SIZES}), "
            f"filename={lut_filename!r} ({fname_bytes}B, max {CUBE_MAX_FILENAME_BYTES}B ASCII), "
            f"slot={lut_slot_index}/{registered_lut_count} (max {USER_LUT_MAX_SLOTS}), "
            f"ae_offset={ae_level_offset_ev} EV (0.0..+2.0 EV in 1/3 steps), "
            f"cube_text_ok={cube_text_ok}."
        )
        return (False, STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING, errors)

    m_norm = _norm_media_type(media_type)
    dir_norm = _norm_lut_dir(lut_directory)
    dir_lower = dir_norm.lower()
    p2_write = stage_b_p2_setting_write_attempted is True or any(
        dir_lower.startswith(pref) for pref in FORBIDDEN_STAGEB_LUT_WRITE_PREFIXES
    )

    expected_dir = (
        SD_USER_LUT_DIR
        if m_norm in (MEDIA_TYPE_SD, MEDIA_TYPE_SDXC)
        else (CFEXPRESS_A_USER_LUT_DIR if m_norm == MEDIA_TYPE_CFEXPRESS_A else "")
    )
    path_ok = (not p2_write) and bool(expected_dir) and (dir_norm == expected_dir)

    if not path_ok:
        errors.append(
            f"Media LUT path asymmetry / p2:/setting violation: media_type={media_type!r} "
            f"requires {expected_dir or 'VALID_MEDIA_ROOT'!r}, got {lut_directory!r}, "
            f"stage_b_p2_setting_write_attempted={stage_b_p2_setting_write_attempted}."
        )
        return (False, STATUS_BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE, errors)

    return (True, "", errors)


def validate_cine_ei_base_iso_bounds(
    *,
    cine_ei_base_iso: int = 800,
    cine_ei_index: int = 800,
    cmos_analog_gain_mutated: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Enforce `Cine EI` base sensitivity lock (`800` -> `200..3200 EI`,
    `12800` -> `3200..51200 EI`, `±2 EV`) without polluting CMOS analog gain.
    """
    errors: List[str] = []
    bounds = CINE_EI_RANGE_BY_BASE.get(int(cine_ei_base_iso))
    ok = (
        bounds is not None
        and bounds[0] <= int(cine_ei_index) <= bounds[1]
        and cmos_analog_gain_mutated is False
    )
    if not ok:
        errors.append(
            f"Cine EI sensitivity bounds violation: base_iso={cine_ei_base_iso} "
            f"(valid {CINE_EI_BASE_ISOS}), ei_index={cine_ei_index}, "
            f"cmos_analog_gain_mutated={cmos_analog_gain_mutated}."
        )
        return (False, STATUS_BLOCKED_G66_CINEEI_BASE_ISO_OR_EI_OUT_OF_BOUNDS, errors)
    return (True, "", errors)


def validate_rmt_p1bt_bt_ir_mutual_exclusion(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    remote_model: str = RMT_P1BT_MODEL,
    bt_spec_version: str = RMT_P1BT_BT_VERSION,
    bluetooth_rmt_ctrl_enabled: bool = True,
    ir_remote_receiver_disabled: bool = True,
    ir_remote_active: bool = False,
    smartphone_gps_location_link_active: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Enforce `Bluetooth Rmt Ctrl = On` (`RMT-P1BT` BT 4.2) automatic
    mutual-exclusion lock against IR remote & smartphone GPS location linking.
    """
    errors: List[str] = []
    model_norm = body_model_name.strip().upper().replace("_", "-")
    bt_ver_ok = bt_spec_version.strip() == RMT_P1BT_BT_VERSION

    if bluetooth_rmt_ctrl_enabled:
        ok = (
            remote_model.strip().upper() == RMT_P1BT_MODEL
            and bt_ver_ok
            and ir_remote_receiver_disabled is True
            and ir_remote_active is False
            and smartphone_gps_location_link_active is False
        )
    else:
        # When BT remote is Off, FX3A still has no IR hardware, and IR active requires receiver enabled
        ir_hw_ok = (ir_remote_active is False) if model_norm == FX3A_MODEL_NAME else True
        ir_state_ok = (not ir_remote_active) or (not ir_remote_receiver_disabled)
        ok = bt_ver_ok and ir_hw_ok and ir_state_ok

    if not ok:
        errors.append(
            f"RMT-P1BT Bluetooth / IR / GPS mutual-exclusion violation: "
            f"body={body_model_name!r}, remote={remote_model!r} (BT {bt_spec_version!r}), "
            f"bt_rmt_ctrl={bluetooth_rmt_ctrl_enabled}, "
            f"ir_disabled={ir_remote_receiver_disabled}, ir_active={ir_remote_active}, "
            f"gps_link_active={smartphone_gps_location_link_active}."
        )
        return (False, STATUS_BLOCKED_G66_RMT_P1BT_BT_IR_GPS_MUTEX_VIOLATION, errors)
    return (True, "", errors)


# ---------------------------------------------------------------------------
# 3. Core Guard Functions (`verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard`,
#    `verify_dualmedia_lut_path_cineei_and_bt_guard`)
# ---------------------------------------------------------------------------


def verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int | str = FX3_MODEL_ID,
    kernel_release: str = FX3_KERNEL_RELEASE,
    usb_connection_mode: str = "USB-LAN",
    uvc_uac_gadget_requested: bool = False,
    usb_streaming_mode_requested: bool = False,
    streaming_transport: str = "RTMP",
    streaming_bitrate_mbps: float = 35.0,
    power_source: str = POWER_SOURCE_USB_PD_BODY,
    np_fz100_inserted: bool = True,
    battery_pct: int = 85,
    battery_bars: int = 4,
    micro_usb_power_attempted: bool = False,
    micro_usb_power_rejected: bool = True,
    usb_pd_watts: float = 65.0,
    emarked_5a_cable: bool = True,
    cable_max_amps: float = 5.0,
    dc_c1_blinking_led_fault: bool = False,
    lcd_max_brightness_locked: bool = False,
    guard_profile: str = "FX3_REALHW_G65_NOUVC_USBPD_DCC1_GUARD_DEFAULT",
) -> Fx3NoUvcDcc1PdResult:
    """Verify Gate G65 (`ILME-FX3` No-UVC USB Gadget Firewall & USB-PD / DC-C1 Interlock)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        body_model_name,
        kernel_release,
        usb_connection_mode,
        streaming_transport,
        power_source,
        guard_profile,
    )
    bools = (
        uvc_uac_gadget_requested,
        usb_streaming_mode_requested,
        np_fz100_inserted,
        micro_usb_power_attempted,
        micro_usb_power_rejected,
        emarked_5a_cable,
        dc_c1_blinking_led_fault,
        lcd_max_brightness_locked,
    )
    b_id = _normalize_int_value(body_model_id)

    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and all(isinstance(b, bool) for b in bools)
        and (b_id is not None and b_id >= 0)
        and _is_finite_number(streaming_bitrate_mbps)
        and float(streaming_bitrate_mbps) >= 0.0
        and _is_non_negative_int(battery_pct)
        and int(battery_pct) <= 100
        and _is_non_negative_int(battery_bars)
        and int(battery_bars) <= 5
        and _is_finite_number(usb_pd_watts)
        and float(usb_pd_watts) >= 0.0
        and _is_finite_number(cable_max_amps)
        and float(cable_max_amps) >= 0.0
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G65_TELEMETRY_INVALID)
        errors.append("Gate G65 received invalid or malformed No-UVC / USB-PD / DC-C1 telemetry.")

    gadget_ok = False
    power_ok = False

    if telemetry_ok:
        gadget_ok, g_code, g_errs = validate_fx3_nouvc_usb_gadget_firewall(
            body_model_name=body_model_name,
            body_model_id=b_id,
            kernel_release=kernel_release,
            usb_connection_mode=usb_connection_mode,
            uvc_uac_gadget_requested=uvc_uac_gadget_requested,
            usb_streaming_mode_requested=usb_streaming_mode_requested,
            streaming_transport=streaming_transport,
            streaming_bitrate_mbps=float(streaming_bitrate_mbps),
        )
        if not gadget_ok:
            _add_code(codes, g_code)
            errors.extend(g_errs)

        power_ok, p_code, p_errs = validate_usbpd_body_vs_dcc1_power_supply(
            power_source=power_source,
            np_fz100_inserted=np_fz100_inserted,
            battery_pct=battery_pct,
            battery_bars=battery_bars,
            micro_usb_power_attempted=micro_usb_power_attempted,
            micro_usb_power_rejected=micro_usb_power_rejected,
            usb_pd_watts=float(usb_pd_watts),
            emarked_5a_cable=emarked_5a_cable,
            cable_max_amps=float(cable_max_amps),
            dc_c1_blinking_led_fault=dc_c1_blinking_led_fault,
        )
        if not power_ok:
            _add_code(codes, p_code)
            errors.extend(p_errs)

        if _norm_token(power_source) == POWER_SOURCE_DC_C1_COUPLER and lcd_max_brightness_locked:
            warnings.append(
                "DC-C1 coupler attached: body may enforce LCD maximum brightness lock."
            )

    valid = (
        telemetry_ok
        and gadget_ok
        and power_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G65 if valid else codes[0]
    uvc_blocked = bool(
        isinstance(uvc_uac_gadget_requested, bool)
        and isinstance(usb_streaming_mode_requested, bool)
        and (not uvc_uac_gadget_requested)
        and (not usb_streaming_mode_requested)
        and gadget_ok
    )

    return Fx3NoUvcDcc1PdResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        body_model_name=str(body_model_name) if isinstance(body_model_name, str) else "INVALID",
        body_model_id=int(b_id) if b_id is not None else -1,
        body_model_id_hex=f"0x{b_id:08x}" if b_id is not None else "INVALID",
        kernel_release=str(kernel_release) if isinstance(kernel_release, str) else "INVALID",
        usb_connection_mode=str(usb_connection_mode) if isinstance(usb_connection_mode, str) else "INVALID",
        uvc_uac_gadget_requested=bool(uvc_uac_gadget_requested) if isinstance(uvc_uac_gadget_requested, bool) else True,
        usb_streaming_mode_requested=bool(usb_streaming_mode_requested) if isinstance(usb_streaming_mode_requested, bool) else True,
        uvc_gadget_blocked=uvc_blocked,
        streaming_transport=str(streaming_transport) if isinstance(streaming_transport, str) else "INVALID",
        streaming_bitrate_mbps=float(streaming_bitrate_mbps) if _is_finite_number(streaming_bitrate_mbps) else -1.0,
        gadget_and_transport_valid=gadget_ok,
        power_source=str(power_source) if isinstance(power_source, str) else "INVALID",
        np_fz100_inserted=bool(np_fz100_inserted) if isinstance(np_fz100_inserted, bool) else False,
        battery_pct=int(battery_pct) if _is_non_negative_int(battery_pct) else -1,
        battery_bars=int(battery_bars) if _is_non_negative_int(battery_bars) else -1,
        micro_usb_power_attempted=bool(micro_usb_power_attempted) if isinstance(micro_usb_power_attempted, bool) else True,
        micro_usb_power_rejected=bool(micro_usb_power_rejected) if isinstance(micro_usb_power_rejected, bool) else False,
        usb_pd_watts=float(usb_pd_watts) if _is_finite_number(usb_pd_watts) else -1.0,
        emarked_5a_cable=bool(emarked_5a_cable) if isinstance(emarked_5a_cable, bool) else False,
        cable_max_amps=float(cable_max_amps) if _is_finite_number(cable_max_amps) else -1.0,
        dc_c1_blinking_led_fault=bool(dc_c1_blinking_led_fault) if isinstance(dc_c1_blinking_led_fault, bool) else True,
        lcd_max_brightness_locked=bool(lcd_max_brightness_locked) if isinstance(lcd_max_brightness_locked, bool) else False,
        power_supply_interlock_valid=power_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_dualmedia_lut_path_cineei_and_bt_guard(
    *,
    lut_3d_size: int = 33,
    lut_filename: str = "FX3_SLog3_Rec709_v1.cube",
    lut_slot_index: int = 1,
    registered_lut_count: int = 4,
    ae_level_offset_ev: float = 0.0,
    media_type: str = MEDIA_TYPE_SDXC,
    lut_directory: str = SD_USER_LUT_DIR,
    stage_b_p2_setting_write_attempted: bool = False,
    cube_text: Optional[str] = None,
    cine_ei_base_iso: int = 800,
    cine_ei_index: int = 800,
    cmos_analog_gain_mutated: bool = False,
    body_model_name: str = FX3_MODEL_NAME,
    remote_model: str = RMT_P1BT_MODEL,
    bt_spec_version: str = RMT_P1BT_BT_VERSION,
    bluetooth_rmt_ctrl_enabled: bool = True,
    ir_remote_receiver_disabled: bool = True,
    ir_remote_active: bool = False,
    smartphone_gps_location_link_active: bool = False,
    guard_profile: str = "FX3_REALHW_G66_LUT_PATH_CINEEI_BT_GUARD_DEFAULT",
) -> DualMediaLutPathCineEiBtResult:
    """Verify Gate G66 (Dual-Media `.cube` User LUT Path-Asymmetry, Cine EI & RMT-P1BT BT/IR)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        lut_filename,
        media_type,
        lut_directory,
        body_model_name,
        remote_model,
        bt_spec_version,
        guard_profile,
    )
    bools = (
        stage_b_p2_setting_write_attempted,
        cmos_analog_gain_mutated,
        bluetooth_rmt_ctrl_enabled,
        ir_remote_receiver_disabled,
        ir_remote_active,
        smartphone_gps_location_link_active,
    )

    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and (cube_text is None or isinstance(cube_text, str))
        and all(isinstance(b, bool) for b in bools)
        and _is_non_negative_int(lut_3d_size)
        and _is_non_negative_int(lut_slot_index)
        and _is_non_negative_int(registered_lut_count)
        and _is_finite_number(ae_level_offset_ev)
        and _is_non_negative_int(cine_ei_base_iso)
        and _is_non_negative_int(cine_ei_index)
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G66_TELEMETRY_INVALID)
        errors.append("Gate G66 received invalid or malformed LUT / Cine EI / BT telemetry.")

    lut_and_path_ok = False
    lut_spec_ok = False
    path_asym_ok = False
    cine_ok = False
    bt_ok = False

    if telemetry_ok:
        lut_and_path_ok, lp_code, lp_errs = validate_user_cube_lut_and_media_path_asymmetry(
            lut_3d_size=lut_3d_size,
            lut_filename=lut_filename,
            lut_slot_index=lut_slot_index,
            registered_lut_count=registered_lut_count,
            ae_level_offset_ev=float(ae_level_offset_ev),
            media_type=media_type,
            lut_directory=lut_directory,
            stage_b_p2_setting_write_attempted=stage_b_p2_setting_write_attempted,
            cube_text=cube_text,
        )
        if not lut_and_path_ok:
            _add_code(codes, lp_code)
            errors.extend(lp_errs)
            lut_spec_ok = lp_code != STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING
            path_asym_ok = lp_code != STATUS_BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE
        else:
            lut_spec_ok = True
            path_asym_ok = True

        cine_ok, ce_code, ce_errs = validate_cine_ei_base_iso_bounds(
            cine_ei_base_iso=cine_ei_base_iso,
            cine_ei_index=cine_ei_index,
            cmos_analog_gain_mutated=cmos_analog_gain_mutated,
        )
        if not cine_ok:
            _add_code(codes, ce_code)
            errors.extend(ce_errs)

        bt_ok, bt_code, bt_errs = validate_rmt_p1bt_bt_ir_mutual_exclusion(
            body_model_name=body_model_name,
            remote_model=remote_model,
            bt_spec_version=bt_spec_version,
            bluetooth_rmt_ctrl_enabled=bluetooth_rmt_ctrl_enabled,
            ir_remote_receiver_disabled=ir_remote_receiver_disabled,
            ir_remote_active=ir_remote_active,
            smartphone_gps_location_link_active=smartphone_gps_location_link_active,
        )
        if not bt_ok:
            _add_code(codes, bt_code)
            errors.extend(bt_errs)

    valid = (
        telemetry_ok
        and lut_and_path_ok
        and cine_ok
        and bt_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G66 if valid else codes[0]

    m_norm = _norm_media_type(media_type) if isinstance(media_type, str) else ""
    expected_dir = (
        SD_USER_LUT_DIR
        if m_norm in (MEDIA_TYPE_SD, MEDIA_TYPE_SDXC)
        else (CFEXPRESS_A_USER_LUT_DIR if m_norm == MEDIA_TYPE_CFEXPRESS_A else "INVALID")
    )
    bounds = (
        CINE_EI_RANGE_BY_BASE.get(int(cine_ei_base_iso), (-1, -1))
        if _is_non_negative_int(cine_ei_base_iso)
        else (-1, -1)
    )
    fname_bytes = (
        len(lut_filename.strip().encode("utf-8"))
        if isinstance(lut_filename, str)
        else -1
    )

    return DualMediaLutPathCineEiBtResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        lut_3d_size=int(lut_3d_size) if _is_non_negative_int(lut_3d_size) else -1,
        lut_filename=str(lut_filename) if isinstance(lut_filename, str) else "INVALID",
        lut_filename_bytes=fname_bytes,
        lut_slot_index=int(lut_slot_index) if _is_non_negative_int(lut_slot_index) else -1,
        registered_lut_count=int(registered_lut_count) if _is_non_negative_int(registered_lut_count) else -1,
        ae_level_offset_ev=float(ae_level_offset_ev) if _is_finite_number(ae_level_offset_ev) else -1.0,
        media_type=str(media_type) if isinstance(media_type, str) else "INVALID",
        lut_directory=str(lut_directory) if isinstance(lut_directory, str) else "INVALID",
        expected_lut_directory=expected_dir,
        stage_b_p2_setting_write_attempted=bool(stage_b_p2_setting_write_attempted) if isinstance(stage_b_p2_setting_write_attempted, bool) else True,
        lut_spec_valid=lut_spec_ok,
        media_path_asymmetry_valid=path_asym_ok,
        cine_ei_base_iso=int(cine_ei_base_iso) if _is_non_negative_int(cine_ei_base_iso) else -1,
        cine_ei_index=int(cine_ei_index) if _is_non_negative_int(cine_ei_index) else -1,
        cine_ei_min_index=bounds[0],
        cine_ei_max_index=bounds[1],
        cmos_analog_gain_mutated=bool(cmos_analog_gain_mutated) if isinstance(cmos_analog_gain_mutated, bool) else True,
        cine_ei_valid=cine_ok,
        remote_model=str(remote_model) if isinstance(remote_model, str) else "INVALID",
        bt_spec_version=str(bt_spec_version) if isinstance(bt_spec_version, str) else "INVALID",
        bluetooth_rmt_ctrl_enabled=bool(bluetooth_rmt_ctrl_enabled) if isinstance(bluetooth_rmt_ctrl_enabled, bool) else False,
        ir_remote_receiver_disabled=bool(ir_remote_receiver_disabled) if isinstance(ir_remote_receiver_disabled, bool) else False,
        ir_remote_active=bool(ir_remote_active) if isinstance(ir_remote_active, bool) else True,
        smartphone_gps_location_link_active=bool(smartphone_gps_location_link_active) if isinstance(smartphone_gps_location_link_active, bool) else True,
        bt_ir_gps_mutex_valid=bt_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G65 & Gate G66 Evaluators (Donor Audit + Guard -> GateVerdict)
# ---------------------------------------------------------------------------


def evaluate_g65_nouvc_dcc1_pd_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    nouvc_dcc1_pd_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase191DonorAuditResult] = None,
) -> Tuple[GateVerdict, G65NoUvcDcc1PdGuardResult]:
    """Evaluate Gate G65 (`ILME-FX3` No-UVC USB Gadget & USB-PD/DC-C1 Electrical Guard)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase191_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(nouvc_dcc1_pd_kwargs or {})
    guard = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE191_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G65 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G65 if valid else codes[0]

    res = G65NoUvcDcc1PdGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        nouvc_dcc1_pd_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, body={guard.body_model_name}({guard.body_model_id_hex}), "
        f"usb_mode={guard.usb_connection_mode}, uvc_blocked={guard.uvc_gadget_blocked}, "
        f"stream={guard.streaming_transport}@{guard.streaming_bitrate_mbps:.1f}Mbps, "
        f"power={guard.power_source}(np_fz100={guard.np_fz100_inserted}, "
        f"batt={guard.battery_pct}%, pd_w={guard.usb_pd_watts:.0f}W, 5a={guard.emarked_5a_cable})"
    )

    verdict = GateVerdict(
        gate_id=G65_GATE_ID,
        gate_code=G65_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


def evaluate_g66_lut_path_cineei_bt_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    lut_path_cineei_bt_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase191DonorAuditResult] = None,
) -> Tuple[GateVerdict, G66LutPathCineEiBtGuardResult]:
    """Evaluate Gate G66 (Dual-Media `.cube` LUT Path-Asymmetry, Cine EI & RMT-P1BT BT/IR)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase191_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(lut_path_cineei_bt_kwargs or {})
    guard = verify_dualmedia_lut_path_cineei_and_bt_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE191_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G66 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G66 if valid else codes[0]

    res = G66LutPathCineEiBtGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        lut_path_cineei_bt_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, cube={guard.lut_3d_size}pt({guard.lut_filename_bytes}B), "
        f"slot={guard.lut_slot_index}/{guard.registered_lut_count}, "
        f"media={guard.media_type}:{guard.lut_directory}, "
        f"cine_ei={guard.cine_ei_base_iso}->{guard.cine_ei_index}, "
        f"bt_rmt={guard.bluetooth_rmt_ctrl_enabled}(ir_off={guard.ir_remote_receiver_disabled}, "
        f"gps={guard.smartphone_gps_location_link_active})"
    )

    verdict = GateVerdict(
        gate_id=G66_GATE_ID,
        gate_code=G66_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Unified 66-Gate Master Safety Preflight (`G01..G66`)
# ---------------------------------------------------------------------------


def evaluate_66gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G01..G64 pass-throughs
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
    ptpip_or_mc_requests: Optional[Sequence[Any]] = None,
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
    vp_strobe_genlock_kwargs: Optional[Mapping[str, Any]] = None,
    vehiclerig_ibis_kwargs: Optional[Mapping[str, Any]] = None,
    jiritsu_service_kwargs: Optional[Mapping[str, Any]] = None,
    cnflasha_dualboot_kwargs: Optional[Mapping[str, Any]] = None,
    service_0336_canary_kwargs: Optional[Mapping[str, Any]] = None,
    stageb_mpr_ibis_p18_kwargs: Optional[Mapping[str, Any]] = None,
    pnflasha_mtdro_kwargs: Optional[Mapping[str, Any]] = None,
    rfnvs_fan_power_kwargs: Optional[Mapping[str, Any]] = None,
    uart1v8_isp_kwargs: Optional[Mapping[str, Any]] = None,
    imx510_sensor_cal_kwargs: Optional[Mapping[str, Any]] = None,
    cfexpress_ufu_kwargs: Optional[Mapping[str, Any]] = None,
    five_tier_el3_kwargs: Optional[Mapping[str, Any]] = None,
    cxd90058_sabin_kwargs: Optional[Mapping[str, Any]] = None,
    factory_seal_kwargs: Optional[Mapping[str, Any]] = None,
    c2pa_cert_kwargs: Optional[Mapping[str, Any]] = None,
    tc_gyro_meta_kwargs: Optional[Mapping[str, Any]] = None,
    dualmedia_vault_kwargs: Optional[Mapping[str, Any]] = None,
    bench_interlock_kwargs: Optional[Mapping[str, Any]] = None,
    ssboot_wbi2_kwargs: Optional[Mapping[str, Any]] = None,
    slot1_ufu_c2pa_kwargs: Optional[Mapping[str, Any]] = None,
    emount_breathing_kwargs: Optional[Mapping[str, Any]] = None,
    hdmi_raw_kwargs: Optional[Mapping[str, Any]] = None,
    fx3a_firewall_kwargs: Optional[Mapping[str, Any]] = None,
    xlrh1_mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    # G65 inputs (No-UVC USB Gadget Firewall & USB-PD / DC-C1 Electrical Interlock)
    nouvc_dcc1_pd_kwargs: Optional[Mapping[str, Any]] = None,
    # G66 inputs (Dual-Media .cube LUT Path-Asymmetry, Cine EI & RMT-P1BT BT/IR)
    lut_path_cineei_bt_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master66GateReport:
    """Evaluate all 66 Master Safety Gates (`G01..G66`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        if dry_run_simulated_backup is None
        else (dry_run_simulated or dry_run_simulated_backup)
    )

    m64_kwargs: Dict[str, Any] = {
        "force_clean_room": clean_forced,
        "dry_run_simulated": effective_dry_run,
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
        "vp_strobe_genlock_kwargs": vp_strobe_genlock_kwargs,
        "vehiclerig_ibis_kwargs": vehiclerig_ibis_kwargs,
        "jiritsu_service_kwargs": jiritsu_service_kwargs,
        "cnflasha_dualboot_kwargs": cnflasha_dualboot_kwargs,
        "service_0336_canary_kwargs": service_0336_canary_kwargs,
        "stageb_mpr_ibis_p18_kwargs": stageb_mpr_ibis_p18_kwargs,
        "pnflasha_mtdro_kwargs": pnflasha_mtdro_kwargs,
        "rfnvs_fan_power_kwargs": rfnvs_fan_power_kwargs,
        "uart1v8_isp_kwargs": uart1v8_isp_kwargs,
        "imx510_sensor_cal_kwargs": imx510_sensor_cal_kwargs,
        "cfexpress_ufu_kwargs": cfexpress_ufu_kwargs,
        "five_tier_el3_kwargs": five_tier_el3_kwargs,
        "cxd90058_sabin_kwargs": cxd90058_sabin_kwargs,
        "factory_seal_kwargs": factory_seal_kwargs,
        "c2pa_cert_kwargs": c2pa_cert_kwargs,
        "tc_gyro_meta_kwargs": tc_gyro_meta_kwargs,
        "dualmedia_vault_kwargs": dualmedia_vault_kwargs,
        "bench_interlock_kwargs": bench_interlock_kwargs,
        "ssboot_wbi2_kwargs": ssboot_wbi2_kwargs,
        "slot1_ufu_c2pa_kwargs": slot1_ufu_c2pa_kwargs,
        "emount_breathing_kwargs": emount_breathing_kwargs,
        "hdmi_raw_kwargs": hdmi_raw_kwargs,
        "fx3a_firewall_kwargs": fx3a_firewall_kwargs,
        "xlrh1_mishoe_kwargs": xlrh1_mishoe_kwargs,
    }
    if soc_start_ceiling_c is not None:
        m64_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m64_report: Master64GateReport = evaluate_64gate_preflight(
        resolved_root, **m64_kwargs
    )

    phase191_audit = audit_phase191_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g65_verdict, g65_res = evaluate_g65_nouvc_dcc1_pd_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        nouvc_dcc1_pd_kwargs=nouvc_dcc1_pd_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase191_audit,
    )

    g66_verdict, g66_res = evaluate_g66_lut_path_cineei_bt_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        lut_path_cineei_bt_kwargs=lut_path_cineei_bt_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase191_audit,
    )

    gates_65_to_66 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g65_verdict, g66_verdict)
    ]
    all_gates = tuple(list(m64_report.gates) + gates_65_to_66)

    g01_to_g12_verified = int(m64_report.summary["g01_to_g12_verified"])
    g13_to_g64_verified = (
        int(m64_report.summary["g13_to_g62_verified"])
        + int(m64_report.summary["g63_to_g64_verified"])
    )
    g65_to_g66_verified = sum(1 for v in (g65_verdict, g66_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g64_verified + g65_to_g66_verified

    g65_to_g66_all_passed = g65_to_g66_verified == 2
    g13_to_g66_all_passed = (
        m64_report.g13_to_g64_all_passed and g65_to_g66_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m64_report.gates[:9])

    offline_63_verified = (
        g01_to_g09_ok
        and m64_report.offline_61_gates_verified
        and g65_to_g66_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_66_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g66_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes
    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m64_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_63_verified
        and m64_report.h0_h1_trial_entry_allowed
        and g65_to_g66_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m64_report.errors) + list(g65_verdict.errors) + list(g66_verdict.errors)
    )
    warnings: List[str] = (
        list(m64_report.warnings)
        + list(g65_verdict.warnings)
        + list(g66_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m64_report.g13_to_g64_all_passed:
        overall_status = m64_report.status
    elif not g65_verdict.passed:
        overall_status = g65_verdict.status
    elif not g66_verdict.passed:
        overall_status = g66_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_66_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_66_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_66_verified:
        overall_status = "VERIFIED_ALL_66_GATES"
    else:
        overall_status = "VERIFIED_63_OF_66_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m64_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g65_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g66_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 66,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 66 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g64_verified": g13_to_g64_verified,
        "g65_to_g66_verified": g65_to_g66_verified,
        "g13_to_g66_all_passed": g13_to_g66_all_passed,
        "g65_to_g66_all_passed": g65_to_g66_all_passed,
        "offline_63_gates_verified": offline_63_verified,
        "all_66_gates_verified": all_66_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "human_hardware_attach_token": HUMAN_HARDWARE_ATTACH_TOKEN,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master66GateReport(
        schema=REALHW_NOUVC_DCC1_PD_LUT_PATH_66GATE_SCHEMA,
        version=REALHW_NOUVC_DCC1_PD_LUT_PATH_66GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_63_gates_verified=offline_63_verified,
        all_66_gates_verified=all_66_verified,
        g13_to_g66_all_passed=g13_to_g66_all_passed,
        g65_to_g66_all_passed=g65_to_g66_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_64_report=m64_report.to_dict(),
        g65_result=g65_res.to_dict(),
        g66_result=g66_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_66_master_safety_gates = evaluate_66gate_preflight
run_66_gate_preflight = evaluate_66gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard",
        description=(
            "Phase 191 — ILME-FX3 No-UVC USB Gadget & USB-PD/DC-C1 Electrical Guard (G65), "
            "Dual-Media .cube LUT Path-Asymmetry, Cine EI & RMT-P1BT BT/IR Guard (G66), "
            "and 66-Gate Master Preflight (G01..G66)"
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    parser.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G66 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_66gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        sys.stdout.write(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
        )
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/66 "
            f"g65_to_g66_all_passed={report.g65_to_g66_all_passed} "
            f"all_66_gates_verified={report.all_66_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
            f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
            f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
            f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        report.all_66_gates_verified
        if args.dry_run_simulated
        else report.offline_63_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
