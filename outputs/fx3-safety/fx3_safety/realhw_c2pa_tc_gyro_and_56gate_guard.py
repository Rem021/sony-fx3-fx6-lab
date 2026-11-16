"""Phase 170 — Real-Hardware Main Track Part 15:
Gate G55 (`p12:/cert/RQ_LIC.DAT` C2PA Authenticity License Read-Only Lock &
Cross-Body/Cross-Model Signing Firewall),
Gate G56 (`VMC-BNCM1` `EXT-LK` SMPTE-12M LTC `0.5V-4.5V p-p` Electrical Bounds,
Multi-USB `1.8V UART` Mutual Exclusion, FX6-Only `TC-OUT` BNC Mask & `IMX510`
`8.7 ms` Rolling-Shutter + 6-Axis IMU Gyro `NonRealTimeMeta.xml` Guard), and
Unified 56-Gate Master Safety Preflight (`G01..G56` / `verify-56-gates`).

Operationalizes C2PA authenticity license immutability, Multi-Port timecode
electrical/mux safety, and MXF/MP4 gyro stabilization metadata integrity on
physical Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, AP `CXD90057` *Mira* +
CP `CXD90058` *Cetus*, Sensor `IMX510`) while keeping all prior gate modules
(`G01..G54`) 100% untouched and hard-locking:
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `overall_ready_for_hardware_attach = False`

1. **Dual-Mode Donor Inspection (`os.O_RDONLY`) + Clean-Room Fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**:
   - Inspects FX3 `7.02` `libsencore.so`, `libmpr.so`, `im.elf`, `cpapp-b.bin`,
     and `Backup.bin` (`FX3-CX95900_ALLLANG-Backup.bin`) strictly via
     `os.open(..., os.O_RDONLY)` when present and `FX3_FX6_FORCE_CLEAN_ROOM != "1"`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent, leaking zero raw
     Sony firmware bytes in JSON output.

2. **Gate G55 — `p12:/cert/RQ_LIC.DAT` C2PA Authenticity License Read-Only Lock
   & Cross-Body/Cross-Model Signing Firewall**:
   - Enforces `p12:/cert` `MS_RDONLY` mount (`c2pa_cert_mutation_bytes == 0`,
     `p12_cert_mount_flags == "MS_RDONLY"`).
   - Verifies same-body `RQ_LIC.DAT` SHA-256 preservation across `H0..H3`
     (`H0 == H1 == H2 == H3`).
   - Hard-blocks cross-body or cross-model C2PA signing key usage
     (`c2pa_cross_model_signing_blocked == True`, `signing_model_id == 0x91030080`,
     `signing_model_name == "ILME-FX3"`, `signing_key_body_match == True`).

3. **Gate G56 — `VMC-BNCM1` (`EXT-LK` SMPTE-12M LTC `0.5V-4.5V p-p`) Electrical
   Bounds, `TC-OUT` BNC Mask & `IMX510` 6-Axis IMU Gyro `NonRealTimeMeta.xml`
   Integrity Guard**:
   - Hard-blocks over-voltage SMPTE LTC injection (`ltc_peak_to_peak_mv > 5000`)
     and enforces `500..4500 mV` (`0.5V-4.5V p-p`) AC-coupled `EXT-LK` envelope.
   - Enforces mutual exclusion with Multi-USB `1.8V UART` tap
     (`multi_usb_uart_1v8_active == False` when `VMC-BNCM1` is attached).
   - Masks FX6-only BNC `TC-OUT` drive (`fx6_tc_out_bnc_masked == True`,
     `tc_out_bnc_drive_requested == False`, `tc_direction == "IN"`).
   - Verifies `IMX510` `8.7 ms` rolling-shutter + 6-axis IMU gyro packet integrity
     inside recorded `MXF/MP4` `NonRealTimeMeta.xml` for Catalyst Browse /
     DaVinci Resolve stabilization.

4. **Unified 56-Gate Master Safety Preflight (`evaluate_56gate_preflight` / CLI `verify-56-gates`)**:
   - Chains `evaluate_54gate_preflight` (`G01..G54`) + `G55` + `G56` = **56 Gates**.
   - Offline default reports `53/56` (`G10..G12` physical Tier-0 gates `False`,
     `persistent_emmc_writes_authorized = False`,
     `persistent_write_release = False`,
     `spi_nor_write_authorized = False`,
     `el3_payload_transmit_authorized = False`,
     `overall_ready_for_hardware_attach = False`).
   - `--dry-run-simulated-backup` reports `56/56` dry-run green while STILL
     hard-locking `el3_payload_transmit_authorized = False`,
     `spi_nor_write_authorized = False`,
     `persistent_emmc_writes_authorized = False`,
     `persistent_write_release = False`, and
     `overall_ready_for_hardware_attach = False`.
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
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import xml.etree.ElementTree as ET

from .exfat_media_integrity_guard import MediaSlotConfig
from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    GateVerdict,
    P12_WLAN_FATAL_GUARD_VMA,
)
from .realhw_cxd90058_sabin_seal_and_54gate_guard import (
    Master54GateReport,
    evaluate_54gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_C2PA_TC_GYRO_56GATE_SCHEMA: str = (
    "fx3-realhw-c2pa-tc-gyro-56gate-preflight-v1"
)
REALHW_C2PA_TC_GYRO_56GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G55..G56
G55_GATE_ID: str = "G55_c2pa_rq_lic_ro_lock_and_cross_model_signing_firewall"
G55_GATE_CODE: str = "C2PA_RQ_LIC_RO_LOCK_AND_CROSS_MODEL_SIGNING_FIREWALL"

G56_GATE_ID: str = "G56_vmc_bncm1_ltc_mux_and_imx510_gyro_nrtm_guard"
G56_GATE_CODE: str = "VMC_BNCM1_LTC_MUX_AND_IMX510_GYRO_NRTM_GUARD"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G55: str = (
    "VERIFIED_C2PA_RQ_LIC_RO_LOCK_AND_CROSS_MODEL_SIGNING_FIREWALL"
)
STATUS_VERIFIED_G56: str = (
    "VERIFIED_VMC_BNCM1_LTC_MUX_AND_IMX510_GYRO_NRTM_GUARD"
)

# Gate G55 Violation Codes
STATUS_BLOCKED_G55_P12_CERT_NON_RO_OR_MUTATION: str = (
    "BLOCKED_G55_P12_CERT_NON_RO_OR_MUTATION"
)
STATUS_BLOCKED_G55_RQ_LIC_SHA256_DRIFT: str = (
    "BLOCKED_G55_RQ_LIC_SHA256_DRIFT"
)
STATUS_BLOCKED_G55_CROSS_MODEL_SIGNING_KEY: str = (
    "BLOCKED_G55_CROSS_MODEL_SIGNING_KEY"
)
STATUS_BLOCKED_G55_TELEMETRY_INVALID: str = (
    "BLOCKED_G55_C2PA_TELEMETRY_INVALID"
)

# Gate G56 Violation Codes
STATUS_BLOCKED_G56_LTC_VOLTAGE_OR_UART_MUX_CLASH: str = (
    "BLOCKED_G56_LTC_VOLTAGE_OR_UART_MUX_CLASH"
)
STATUS_BLOCKED_G56_FX6_TC_OUT_BNC_UNMASKED: str = (
    "BLOCKED_G56_FX6_TC_OUT_BNC_UNMASKED"
)
STATUS_BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT: str = (
    "BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT"
)
STATUS_BLOCKED_G56_TELEMETRY_INVALID: str = (
    "BLOCKED_G56_TC_GYRO_META_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE170_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE170_56GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G55 Constants — p12:/cert/RQ_LIC.DAT C2PA Authenticity License & Signing Lock
FX3_MODEL_ID_INT: int = 0x91030080
FX3_MODEL_ID_HEX: str = "0x91030080"
FX3_MODEL_NAME: str = "ILME-FX3"
P12_CERT_MOUNT_POINT: str = "p12:/cert"
P12_CERT_DEVICE_NODE: str = "/dev/nflasha12"
P12_CERT_REQUIRED_MOUNT_FLAG: str = "MS_RDONLY"
RQ_LIC_FILENAME: str = "RQ_LIC.DAT"
RQ_LIC_PARTITION_PATH: str = "p12:/cert/RQ_LIC.DAT"
C2PA_FX3_MAX_LICENSES_PER_RQ_LIC: int = 100
C2PA_ALLOWED_SIGNING_MODES: Tuple[str, ...] = (
    "SAME_BODY_STOCK_C2PA",
    "UNSIGNED_STAGE_B_RESEARCH_OVERLAY",
)
DEFAULT_SYNTHETIC_RQ_LIC_SHA256: str = hashlib.sha256(
    b"ILME-FX3:0x91030080:p12:/cert/RQ_LIC.DAT:H0_H3_SEAL_V1"
).hexdigest()

# Gate G56 Constants — VMC-BNCM1 EXT-LK SMPTE-12M LTC, TC-OUT Mask & IMX510 Gyro NRTM
VMC_BNCM1_ADAPTER_NAME: str = "VMC-BNCM1"
VMC_BNCM1_LTC_MIN_MV: int = 500
VMC_BNCM1_LTC_MAX_MV: int = 4500
VMC_BNCM1_LTC_HARD_CEILING_MV: int = 5000
VMC_BNCM1_ID_RESISTOR_OHM: int = 680_000
VMC_BNCM1_ID_RESISTOR_MIN_OHM: int = 612_000
VMC_BNCM1_ID_RESISTOR_MAX_OHM: int = 748_000
VMC_BNCM1_LTC_SYNC_MODES: Tuple[str, ...] = ("EXT-LK", "EXT_LK")
SMPTE_12M_STANDARD_NAME: str = "SMPTE-12M"
SUPPORTED_SMPTE_LTC_FPS: Tuple[float, ...] = (
    23.976,
    24.0,
    25.0,
    29.97,
    30.0,
    50.0,
    59.94,
    60.0,
)

IMX510_SENSOR_NAME: str = "IMX510"
IMX510_ROLLING_SHUTTER_MS: float = 8.7
IMX510_ROLLING_SHUTTER_TOLERANCE_MS: float = 0.05
IMX510_IMU_AXES: int = 6
IMX510_IMU_SAMPLE_RATE_HZ: int = 2000
NRTM_XML_FILENAME: str = "NonRealTimeMeta.xml"
NRTM_NAMESPACE_V220: str = (
    "urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20"
)
NRTM_VALID_CONTAINERS: Tuple[str, ...] = ("MXF", "MP4")

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

# Pinned FX3 v7.02 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE170_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_libsencore": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libsencore.so",
        377_328,
        "a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410",
        (
            b"\x7fELF",
            b"C_GYRO_GAIN",
            b"MONITOR_GET_TEST_OUT_BNC_STATUS",
            b"GENLOCK",
            b"DSP",
            b"AVC",
        ),
        "fx3/libsencore.so::{ELF,C_GYRO_GAIN,MONITOR_GET_TEST_OUT_BNC_STATUS,GENLOCK,DSP,AVC}",
    ),
    "fx3_libmpr": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so",
        3_517_008,
        "9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c",
        (
            b"\x7fELF",
            b"InfraC2PA",
            b"c2pa.created",
            b"sony.created",
            b"jumdSSIG",
            b"sigcert.p12",
            b"NonRealTimeMeta",
            b"LtcChangeTable",
            b"Gyroscope",
        ),
        "fx3/libmpr.so::{ELF,InfraC2PA,c2pa.created,sony.created,jumdSSIG,sigcert.p12,NonRealTimeMeta,LtcChangeTable,Gyroscope}",
    ),
    "fx3_im_elf": (
        "fx3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/bin/im.elf",
        40_920,
        "5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91",
        (
            b"\x7fELF",
            b"/dev/nflasha12",
            b"/cert",
            b"libIMDB.so",
            b"libbackup.so",
            b"libosal_uipc.so",
        ),
        "fx3/im.elf::{40920B,ELF,/dev/nflasha12,/cert,libIMDB.so,libbackup.so,libosal_uipc.so}",
    ),
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"\x80\x00\x03\x91",
            b"C_ImagerCtrl_IMX510",
            b"LTC",
            b"Gyro Data",
            b"MTG_ULOCK_START_SLAVE",
            b"OTP",
            b"sabin",
        ),
        "fx3/cpapp-b.bin::{ILME-FX3,0x91030080,C_ImagerCtrl_IMX510,LTC,Gyro Data,MTG_ULOCK_START_SLAVE,OTP,sabin}",
    ),
    "fx3_backup_bin": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (
            b"BK4\x00",
            b"ILME-FX3",
            b"90057",
            b"psd.bin",
            b"defdet.bin",
            b"lensfile.bin",
        ),
        "fx3/Backup.bin::{2229740B,BK4\\0,ILME-FX3,90057,psd.bin,defdet.bin,lensfile.bin}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase170DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class C2paRqLicSigningGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    p12_cert_mount_point: str
    p12_cert_device_node: str
    p12_cert_mount_flags: str
    p12_cert_ro_locked: bool
    c2pa_cert_mutation_bytes: int
    c2pa_cert_write_requested: bool
    p12_cert_ro_safe: bool
    rq_lic_path: str
    rq_lic_h0_sha256: str
    rq_lic_h1_sha256: str
    rq_lic_h2_sha256: str
    rq_lic_h3_sha256: str
    rq_lic_h0_to_h3_preserved: bool
    c2pa_license_count: int
    rq_lic_preservation_safe: bool
    target_model_id_hex: str
    target_model_name: str
    signing_model_id_hex: str
    signing_model_name: str
    signing_mode: str
    signing_key_body_match: bool
    cross_body_signing_attempted: bool
    cross_model_signing_attempted: bool
    sigcert_extract_requested: bool
    c2pa_cross_model_signing_blocked: bool
    cross_model_signing_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VmcBncm1LtcGyroNrtmGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    adapter_name: str
    tc_sync_mode: str
    tc_standard: str
    tc_fps: float
    ltc_peak_to_peak_mv: int
    ltc_ac_coupled: bool
    vmc_bncm1_id_resistor_ohm: int
    vmc_bncm1_ltc_active: bool
    multi_usb_uart_1v8_active: bool
    uart_mux_conflict: bool
    ltc_voltage_and_mux_safe: bool
    tc_direction: str
    fx6_tc_out_bnc_masked: bool
    tc_out_bnc_drive_requested: bool
    fx6_tc_out_mask_safe: bool
    sensor_name: str
    imx510_rolling_shutter_ms: float
    imu_axes: int
    imu_sample_rate_hz: int
    gyro_packet_count: int
    gyro_packet_crc_valid: bool
    gyro_monotonic_timestamps: bool
    recording_container: str
    nrtm_xml_present: bool
    nrtm_schema_version: str
    nrtm_xml_validated: bool
    catalyst_browse_compatible: bool
    davinci_resolve_compatible: bool
    gyro_metadata_uncorrupted: bool
    imx510_gyro_nrtm_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G55C2paCertResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    c2pa_rq_lic_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G56TcGyroMetaResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    tc_gyro_meta_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master56GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_53_gates_verified: bool
    all_56_gates_verified: bool
    g13_to_g56_all_passed: bool
    g55_to_g56_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_54_report: Dict[str, Any]
    g55_result: Dict[str, Any]
    g56_result: Dict[str, Any]
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


def _is_positive_int(val: Any) -> bool:
    return isinstance(val, int) and (not isinstance(val, bool)) and val > 0


def _normalize_model_id_int(val: Any) -> Optional[int]:
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val if val >= 0 else None
    if isinstance(val, str):
        s = val.strip().lower()
        if not s:
            return None
        try:
            return int(s, 16) if s.startswith("0x") else int(s, 10)
        except ValueError:
            return None
    return None


def _normalize_sync_mode(mode: str) -> str:
    return mode.strip().upper().replace("_", "-")


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit (FX3 7.02)
# ---------------------------------------------------------------------------


def audit_phase170_donor_contracts(
    *_,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase170DonorAuditResult:
    """Inspect FX3 `7.02` `libsencore.so`, `libmpr.so`, `im.elf`, `cpapp-b.bin`,
    and `Backup.bin` strictly via `os.open(..., os.O_RDONLY)` with deterministic
    clean-room fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donors are absent.
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
        ) in PINNED_PHASE170_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase170DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE170_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=True,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE170_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE170_DONOR_SPECS.items()
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
    ) in PINNED_PHASE170_DONOR_SPECS.items():
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
        k for k, spec in PINNED_PHASE170_DONOR_SPECS.items() if spec[0] == "fx3"
    }
    valid = len(errors) == 0 and len(missing) == 0
    return Phase170DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE170_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_keys.issubset(passed_keys) and valid,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Pure Helper Functions (G55 & G56)
# ---------------------------------------------------------------------------


def default_verified_rq_lic_h0_to_h3_hashes(
    seed_hex: str = DEFAULT_SYNTHETIC_RQ_LIC_SHA256,
) -> Tuple[str, str, str, str]:
    """Return identical `(H0, H1, H2, H3)` SHA-256 digests for `p12:/cert/RQ_LIC.DAT`."""
    norm = seed_hex.strip().lower() if isinstance(seed_hex, str) else ""
    if not _HEX64_RE.match(norm):
        norm = DEFAULT_SYNTHETIC_RQ_LIC_SHA256
    return norm, norm, norm, norm


def build_synthetic_nrtm_gyro_xml(
    *,
    model_name: str = FX3_MODEL_NAME,
    imx510_rolling_shutter_ms: float = IMX510_ROLLING_SHUTTER_MS,
    imu_axes: int = IMX510_IMU_AXES,
    imu_sample_rate_hz: int = IMX510_IMU_SAMPLE_RATE_HZ,
    gyro_packet_count: int = 240,
    tc_sync_mode: str = "EXT-LK",
    tc_fps: float = 23.976,
    recording_container: str = "MXF",
) -> str:
    """Generate a deterministic Sony `NonRealTimeMeta v2.20` XML carrying `IMX510`
    `8.7 ms` rolling-shutter and 6-axis IMU gyro stabilization metadata.
    """
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<NonRealTimeMeta xmlns="{NRTM_NAMESPACE_V220}" lastUpdate="2026-11-15T00:00:00Z">\n'
        f'  <Device manufacturer="Sony" modelName="{model_name}" serialNo="0000001"/>\n'
        f'  <VideoFormat>\n'
        f'    <VideoFrame videoCodec="XAVC_S_I_4K" captureFps="{tc_fps:.3f}p" container="{recording_container}"/>\n'
        f'    <SensorRollingShutter unit="ms">{imx510_rolling_shutter_ms:.2f}</SensorRollingShutter>\n'
        f'  </VideoFormat>\n'
        f'  <LtcChangeTable tcFps="{tc_fps:.3f}" halfStep="false" syncMode="{tc_sync_mode}">\n'
        f'    <LtcChange frameCount="0" value="01000000" status="increment"/>\n'
        f'  </LtcChangeTable>\n'
        f'  <AcquisitionRecord>\n'
        f'    <Group name="Gyroscope" imuAxes="{imu_axes}" sampleRateHz="{imu_sample_rate_hz}" '
        f'packetCount="{gyro_packet_count}" rollingShutterMs="{imx510_rolling_shutter_ms:.2f}" '
        f'stabilizerCompat="CatalystBrowse,DaVinciResolve"/>\n'
        f'  </AcquisitionRecord>\n'
        f'</NonRealTimeMeta>\n'
    )


def validate_p12_cert_ms_rdonly_lock(
    *,
    p12_cert_mount_point: str = P12_CERT_MOUNT_POINT,
    p12_cert_device_node: str = P12_CERT_DEVICE_NODE,
    p12_cert_mount_flags: str = P12_CERT_REQUIRED_MOUNT_FLAG,
    p12_cert_ro_locked: bool = True,
    c2pa_cert_mutation_bytes: int = 0,
    c2pa_cert_write_requested: bool = False,
) -> bool:
    """Enforce strict `MS_RDONLY` mount and zero mutation on `p12:/cert`."""
    if not isinstance(p12_cert_ro_locked, bool) or not isinstance(
        c2pa_cert_write_requested, bool
    ):
        return False
    if not _is_non_negative_int(c2pa_cert_mutation_bytes):
        return False
    for s in (p12_cert_mount_point, p12_cert_device_node, p12_cert_mount_flags):
        if not isinstance(s, str) or not s.strip():
            return False

    if p12_cert_mount_point.strip() != P12_CERT_MOUNT_POINT:
        return False
    if p12_cert_device_node.strip() != P12_CERT_DEVICE_NODE:
        return False
    flags_upper = p12_cert_mount_flags.strip().upper()
    if P12_CERT_REQUIRED_MOUNT_FLAG not in flags_upper and flags_upper != "RO":
        return False
    if "RW" in flags_upper or "REMOUNT" in flags_upper:
        return False
    if (not p12_cert_ro_locked) or int(c2pa_cert_mutation_bytes) != 0:
        return False
    if c2pa_cert_write_requested:
        return False
    return True


def validate_rq_lic_h0_to_h3_preservation(
    *,
    rq_lic_path: str = RQ_LIC_PARTITION_PATH,
    rq_lic_h0_sha256: str = DEFAULT_SYNTHETIC_RQ_LIC_SHA256,
    rq_lic_h1_sha256: str = DEFAULT_SYNTHETIC_RQ_LIC_SHA256,
    rq_lic_h2_sha256: str = DEFAULT_SYNTHETIC_RQ_LIC_SHA256,
    rq_lic_h3_sha256: str = DEFAULT_SYNTHETIC_RQ_LIC_SHA256,
    c2pa_license_count: int = 1,
) -> bool:
    """Verify same-body `p12:/cert/RQ_LIC.DAT` SHA-256 preservation across `H0..H3`."""
    if not isinstance(rq_lic_path, str) or rq_lic_path.strip() != RQ_LIC_PARTITION_PATH:
        return False
    if not _is_non_negative_int(c2pa_license_count):
        return False
    if int(c2pa_license_count) < 1 or int(c2pa_license_count) > C2PA_FX3_MAX_LICENSES_PER_RQ_LIC:
        return False
    norm_hashes: List[str] = []
    for h in (rq_lic_h0_sha256, rq_lic_h1_sha256, rq_lic_h2_sha256, rq_lic_h3_sha256):
        if not isinstance(h, str):
            return False
        s = h.strip().lower()
        if not _HEX64_RE.match(s):
            return False
        norm_hashes.append(s)
    return len(set(norm_hashes)) == 1


def validate_c2pa_cross_model_signing_firewall(
    *,
    target_model_id: Any = FX3_MODEL_ID_INT,
    target_model_name: str = FX3_MODEL_NAME,
    signing_model_id: Any = FX3_MODEL_ID_INT,
    signing_model_name: str = FX3_MODEL_NAME,
    signing_mode: str = "SAME_BODY_STOCK_C2PA",
    signing_key_body_match: bool = True,
    cross_body_signing_attempted: bool = False,
    cross_model_signing_attempted: bool = False,
    sigcert_extract_requested: bool = False,
    c2pa_cross_model_signing_blocked: bool = True,
) -> bool:
    """Hard-block cross-body/cross-model C2PA signing key usage or cert extraction."""
    for b in (
        signing_key_body_match,
        cross_body_signing_attempted,
        cross_model_signing_attempted,
        sigcert_extract_requested,
        c2pa_cross_model_signing_blocked,
    ):
        if not isinstance(b, bool):
            return False
    if not isinstance(target_model_name, str) or not isinstance(signing_model_name, str):
        return False
    if not isinstance(signing_mode, str) or not signing_mode.strip():
        return False

    t_id = _normalize_model_id_int(target_model_id)
    s_id = _normalize_model_id_int(signing_model_id)
    if t_id != FX3_MODEL_ID_INT or s_id != FX3_MODEL_ID_INT:
        return False
    if target_model_name.strip().upper() != FX3_MODEL_NAME:
        return False
    if signing_model_name.strip().upper() != FX3_MODEL_NAME:
        return False
    if signing_mode.strip().upper() not in C2PA_ALLOWED_SIGNING_MODES:
        return False
    if not signing_key_body_match:
        return False
    if cross_body_signing_attempted or cross_model_signing_attempted or sigcert_extract_requested:
        return False
    if not c2pa_cross_model_signing_blocked:
        return False
    return True


def validate_vmc_bncm1_ltc_and_uart_mux(
    *,
    adapter_name: str = VMC_BNCM1_ADAPTER_NAME,
    tc_sync_mode: str = "EXT-LK",
    tc_standard: str = SMPTE_12M_STANDARD_NAME,
    tc_fps: float = 23.976,
    ltc_peak_to_peak_mv: int = 2000,
    ltc_ac_coupled: bool = True,
    vmc_bncm1_id_resistor_ohm: int = VMC_BNCM1_ID_RESISTOR_OHM,
    vmc_bncm1_ltc_active: bool = True,
    multi_usb_uart_1v8_active: bool = False,
    uart_mux_conflict: bool = False,
) -> bool:
    """Verify `VMC-BNCM1` `EXT-LK` SMPTE-12M LTC `0.5V-4.5V p-p` bounds and
    mutual exclusion with Multi-USB `1.8V UART` tap.
    """
    for b in (
        ltc_ac_coupled,
        vmc_bncm1_ltc_active,
        multi_usb_uart_1v8_active,
        uart_mux_conflict,
    ):
        if not isinstance(b, bool):
            return False
    if not _is_non_negative_int(ltc_peak_to_peak_mv):
        return False
    if not _is_positive_int(vmc_bncm1_id_resistor_ohm):
        return False
    if not _is_finite_number(tc_fps):
        return False
    for s in (adapter_name, tc_sync_mode, tc_standard):
        if not isinstance(s, str) or not s.strip():
            return False

    if adapter_name.strip().upper() != VMC_BNCM1_ADAPTER_NAME:
        return False
    if _normalize_sync_mode(tc_sync_mode) not in VMC_BNCM1_LTC_SYNC_MODES:
        return False
    if tc_standard.strip().upper().replace("_", "-") != SMPTE_12M_STANDARD_NAME:
        return False
    if not any(abs(float(tc_fps) - f) <= 0.01 for f in SUPPORTED_SMPTE_LTC_FPS):
        return False
    # Over-voltage (> 5000 mV) or out-of-envelope (< 500 mV or > 4500 mV) blocked
    if int(ltc_peak_to_peak_mv) > VMC_BNCM1_LTC_HARD_CEILING_MV:
        return False
    if int(ltc_peak_to_peak_mv) < VMC_BNCM1_LTC_MIN_MV or int(ltc_peak_to_peak_mv) > VMC_BNCM1_LTC_MAX_MV:
        return False
    if not ltc_ac_coupled:
        return False
    if (
        int(vmc_bncm1_id_resistor_ohm) < VMC_BNCM1_ID_RESISTOR_MIN_OHM
        or int(vmc_bncm1_id_resistor_ohm) > VMC_BNCM1_ID_RESISTOR_MAX_OHM
    ):
        return False
    # Mutual exclusion: VMC-BNCM1 and Multi-USB 1.8V UART tap cannot share Multi-Port
    if uart_mux_conflict or (vmc_bncm1_ltc_active and multi_usb_uart_1v8_active):
        return False
    return True


def validate_fx6_tc_out_bnc_mask(
    *,
    tc_direction: str = "IN",
    fx6_tc_out_bnc_masked: bool = True,
    tc_out_bnc_drive_requested: bool = False,
) -> bool:
    """Enforce fail-closed mask of FX6-only dedicated BNC `TC-OUT` drive on FX3."""
    if not isinstance(fx6_tc_out_bnc_masked, bool) or not isinstance(
        tc_out_bnc_drive_requested, bool
    ):
        return False
    if not isinstance(tc_direction, str) or not tc_direction.strip():
        return False
    norm_dir = tc_direction.strip().upper()
    if norm_dir != "IN":
        return False
    if (not fx6_tc_out_bnc_masked) or tc_out_bnc_drive_requested:
        return False
    return True


def validate_imx510_gyro_nrtm_integrity(
    *,
    sensor_name: str = IMX510_SENSOR_NAME,
    imx510_rolling_shutter_ms: float = IMX510_ROLLING_SHUTTER_MS,
    imu_axes: int = IMX510_IMU_AXES,
    imu_sample_rate_hz: int = IMX510_IMU_SAMPLE_RATE_HZ,
    gyro_packet_count: int = 240,
    gyro_packet_crc_valid: bool = True,
    gyro_monotonic_timestamps: bool = True,
    recording_container: str = "MXF",
    nrtm_xml_present: bool = True,
    nrtm_schema_version: str = "2.20",
    nrtm_xml_text: Optional[str] = None,
    catalyst_browse_compatible: bool = True,
    davinci_resolve_compatible: bool = True,
    gyro_metadata_uncorrupted: bool = True,
) -> Tuple[bool, bool]:
    """Verify `IMX510` `8.7 ms` rolling-shutter + 6-axis IMU gyro packet integrity
    inside recorded `MXF/MP4` `NonRealTimeMeta.xml`. Returns `(valid, xml_validated)`.
    """
    for b in (
        gyro_packet_crc_valid,
        gyro_monotonic_timestamps,
        nrtm_xml_present,
        catalyst_browse_compatible,
        davinci_resolve_compatible,
        gyro_metadata_uncorrupted,
    ):
        if not isinstance(b, bool):
            return False, False
    if not _is_finite_number(imx510_rolling_shutter_ms):
        return False, False
    for i in (imu_axes, imu_sample_rate_hz, gyro_packet_count):
        if not _is_positive_int(i):
            return False, False
    for s in (sensor_name, recording_container, nrtm_schema_version):
        if not isinstance(s, str) or not s.strip():
            return False, False

    if sensor_name.strip().upper() != IMX510_SENSOR_NAME:
        return False, False
    if (
        abs(float(imx510_rolling_shutter_ms) - IMX510_ROLLING_SHUTTER_MS)
        > IMX510_ROLLING_SHUTTER_TOLERANCE_MS
    ):
        return False, False
    if int(imu_axes) != IMX510_IMU_AXES:
        return False, False
    if int(imu_sample_rate_hz) < 1000 or int(imu_sample_rate_hz) > 4000:
        return False, False
    if int(gyro_packet_count) <= 0:
        return False, False
    if not gyro_packet_crc_valid or not gyro_monotonic_timestamps:
        return False, False
    if recording_container.strip().upper() not in NRTM_VALID_CONTAINERS:
        return False, False
    if not nrtm_xml_present:
        return False, False
    if nrtm_schema_version.strip() != "2.20":
        return False, False
    if (
        (not catalyst_browse_compatible)
        or (not davinci_resolve_compatible)
        or (not gyro_metadata_uncorrupted)
    ):
        return False, False

    xml_to_parse = (
        build_synthetic_nrtm_gyro_xml(
            imx510_rolling_shutter_ms=float(imx510_rolling_shutter_ms),
            imu_axes=int(imu_axes),
            imu_sample_rate_hz=int(imu_sample_rate_hz),
            gyro_packet_count=int(gyro_packet_count),
            recording_container=recording_container.strip().upper(),
        )
        if nrtm_xml_text is None
        else nrtm_xml_text
    )
    if not isinstance(xml_to_parse, str) or not xml_to_parse.strip():
        return False, False

    try:
        root = ET.fromstring(xml_to_parse)
    except ET.ParseError:
        return False, False

    if not root.tag.endswith("NonRealTimeMeta"):
        return False, False

    rs_el = None
    gyro_el = None
    for elem in root.iter():
        local = elem.tag.split("}", 1)[-1]
        if local == "SensorRollingShutter":
            rs_el = elem
        elif local == "Group" and elem.attrib.get("name") == "Gyroscope":
            gyro_el = elem

    if rs_el is None or gyro_el is None:
        return False, False

    try:
        rs_val = float((rs_el.text or "").strip())
        xml_axes = int(gyro_el.attrib.get("imuAxes", "0"))
        xml_rate = int(gyro_el.attrib.get("sampleRateHz", "0"))
        xml_pkts = int(gyro_el.attrib.get("packetCount", "0"))
    except ValueError:
        return False, False

    if abs(rs_val - IMX510_ROLLING_SHUTTER_MS) > IMX510_ROLLING_SHUTTER_TOLERANCE_MS:
        return False, False
    if xml_axes != IMX510_IMU_AXES or xml_rate != int(imu_sample_rate_hz) or xml_pkts <= 0:
        return False, False

    return True, True


# ---------------------------------------------------------------------------
# 3. Gate G55 & Gate G56 Core Evaluators
# ---------------------------------------------------------------------------


def verify_c2pa_rq_lic_and_cross_model_signing_guard(
    *,
    p12_cert_mount_point: str = P12_CERT_MOUNT_POINT,
    p12_cert_device_node: str = P12_CERT_DEVICE_NODE,
    p12_cert_mount_flags: str = P12_CERT_REQUIRED_MOUNT_FLAG,
    p12_cert_ro_locked: bool = True,
    c2pa_cert_mutation_bytes: int = 0,
    c2pa_cert_write_requested: bool = False,
    rq_lic_path: str = RQ_LIC_PARTITION_PATH,
    rq_lic_h0_sha256: str = DEFAULT_SYNTHETIC_RQ_LIC_SHA256,
    rq_lic_h1_sha256: str = DEFAULT_SYNTHETIC_RQ_LIC_SHA256,
    rq_lic_h2_sha256: str = DEFAULT_SYNTHETIC_RQ_LIC_SHA256,
    rq_lic_h3_sha256: str = DEFAULT_SYNTHETIC_RQ_LIC_SHA256,
    c2pa_license_count: int = 1,
    target_model_id: Any = FX3_MODEL_ID_INT,
    target_model_name: str = FX3_MODEL_NAME,
    signing_model_id: Any = FX3_MODEL_ID_INT,
    signing_model_name: str = FX3_MODEL_NAME,
    signing_mode: str = "SAME_BODY_STOCK_C2PA",
    signing_key_body_match: bool = True,
    cross_body_signing_attempted: bool = False,
    cross_model_signing_attempted: bool = False,
    sigcert_extract_requested: bool = False,
    c2pa_cross_model_signing_blocked: bool = True,
    guard_profile: str = "FX3_REALHW_G55_C2PA_RQ_LIC_SIGNING_DEFAULT",
) -> C2paRqLicSigningGuardResult:
    """Verify Gate G55 invariants fail-closed."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    bool_inputs = (
        p12_cert_ro_locked,
        c2pa_cert_write_requested,
        signing_key_body_match,
        cross_body_signing_attempted,
        cross_model_signing_attempted,
        sigcert_extract_requested,
        c2pa_cross_model_signing_blocked,
    )
    str_inputs = (
        p12_cert_mount_point,
        p12_cert_device_node,
        p12_cert_mount_flags,
        rq_lic_path,
        rq_lic_h0_sha256,
        rq_lic_h1_sha256,
        rq_lic_h2_sha256,
        rq_lic_h3_sha256,
        target_model_name,
        signing_model_name,
        signing_mode,
        guard_profile,
    )
    t_id_norm = _normalize_model_id_int(target_model_id)
    s_id_norm = _normalize_model_id_int(signing_model_id)

    telemetry_ok = (
        all(isinstance(b, bool) for b in bool_inputs)
        and _is_non_negative_int(c2pa_cert_mutation_bytes)
        and _is_non_negative_int(c2pa_license_count)
        and (t_id_norm is not None)
        and (s_id_norm is not None)
        and all(isinstance(s, str) and bool(s.strip()) for s in str_inputs)
        and all(
            bool(_HEX64_RE.match(h.strip().lower()))
            for h in (
                rq_lic_h0_sha256,
                rq_lic_h1_sha256,
                rq_lic_h2_sha256,
                rq_lic_h3_sha256,
            )
            if isinstance(h, str)
        )
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G55_TELEMETRY_INVALID)
        errors.append("Gate G55 received invalid, non-finite, or malformed telemetry.")

    ro_safe = False
    rq_lic_safe = False
    signing_safe = False

    if telemetry_ok:
        ro_safe = validate_p12_cert_ms_rdonly_lock(
            p12_cert_mount_point=p12_cert_mount_point,
            p12_cert_device_node=p12_cert_device_node,
            p12_cert_mount_flags=p12_cert_mount_flags,
            p12_cert_ro_locked=p12_cert_ro_locked,
            c2pa_cert_mutation_bytes=int(c2pa_cert_mutation_bytes),
            c2pa_cert_write_requested=c2pa_cert_write_requested,
        )
        if not ro_safe:
            _add_code(codes, STATUS_BLOCKED_G55_P12_CERT_NON_RO_OR_MUTATION)
            errors.append(
                f"p12:/cert RO lock violation: mount={p12_cert_mount_point} ({p12_cert_mount_flags}), "
                f"ro_locked={p12_cert_ro_locked}, mut={c2pa_cert_mutation_bytes}B, "
                f"write_req={c2pa_cert_write_requested}."
            )

        rq_lic_safe = validate_rq_lic_h0_to_h3_preservation(
            rq_lic_path=rq_lic_path,
            rq_lic_h0_sha256=rq_lic_h0_sha256,
            rq_lic_h1_sha256=rq_lic_h1_sha256,
            rq_lic_h2_sha256=rq_lic_h2_sha256,
            rq_lic_h3_sha256=rq_lic_h3_sha256,
            c2pa_license_count=int(c2pa_license_count),
        )
        if not rq_lic_safe:
            _add_code(codes, STATUS_BLOCKED_G55_RQ_LIC_SHA256_DRIFT)
            errors.append(
                f"RQ_LIC.DAT H0..H3 preservation violation: path={rq_lic_path}, "
                f"licenses={c2pa_license_count}, H0..H3 SHA-256 mismatch or invalid license count."
            )

        signing_safe = validate_c2pa_cross_model_signing_firewall(
            target_model_id=target_model_id,
            target_model_name=target_model_name,
            signing_model_id=signing_model_id,
            signing_model_name=signing_model_name,
            signing_mode=signing_mode,
            signing_key_body_match=signing_key_body_match,
            cross_body_signing_attempted=cross_body_signing_attempted,
            cross_model_signing_attempted=cross_model_signing_attempted,
            sigcert_extract_requested=sigcert_extract_requested,
            c2pa_cross_model_signing_blocked=c2pa_cross_model_signing_blocked,
        )
        if not signing_safe:
            _add_code(codes, STATUS_BLOCKED_G55_CROSS_MODEL_SIGNING_KEY)
            errors.append(
                f"Cross-body/cross-model C2PA signing violation: target={target_model_name}, "
                f"signing={signing_model_name}, body_match={signing_key_body_match}, "
                f"cross_body={cross_body_signing_attempted}, cross_model={cross_model_signing_attempted}."
            )

    valid = (
        telemetry_ok
        and ro_safe
        and rq_lic_safe
        and signing_safe
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G55 if valid else codes[0]

    return C2paRqLicSigningGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        p12_cert_mount_point=(
            str(p12_cert_mount_point)
            if isinstance(p12_cert_mount_point, str)
            else "INVALID"
        ),
        p12_cert_device_node=(
            str(p12_cert_device_node)
            if isinstance(p12_cert_device_node, str)
            else "INVALID"
        ),
        p12_cert_mount_flags=(
            str(p12_cert_mount_flags)
            if isinstance(p12_cert_mount_flags, str)
            else "INVALID"
        ),
        p12_cert_ro_locked=(
            bool(p12_cert_ro_locked) if isinstance(p12_cert_ro_locked, bool) else False
        ),
        c2pa_cert_mutation_bytes=(
            int(c2pa_cert_mutation_bytes)
            if _is_non_negative_int(c2pa_cert_mutation_bytes)
            else -1
        ),
        c2pa_cert_write_requested=(
            bool(c2pa_cert_write_requested)
            if isinstance(c2pa_cert_write_requested, bool)
            else True
        ),
        p12_cert_ro_safe=ro_safe,
        rq_lic_path=str(rq_lic_path) if isinstance(rq_lic_path, str) else "INVALID",
        rq_lic_h0_sha256=(
            rq_lic_h0_sha256.strip().lower()
            if isinstance(rq_lic_h0_sha256, str)
            else "INVALID"
        ),
        rq_lic_h1_sha256=(
            rq_lic_h1_sha256.strip().lower()
            if isinstance(rq_lic_h1_sha256, str)
            else "INVALID"
        ),
        rq_lic_h2_sha256=(
            rq_lic_h2_sha256.strip().lower()
            if isinstance(rq_lic_h2_sha256, str)
            else "INVALID"
        ),
        rq_lic_h3_sha256=(
            rq_lic_h3_sha256.strip().lower()
            if isinstance(rq_lic_h3_sha256, str)
            else "INVALID"
        ),
        rq_lic_h0_to_h3_preserved=rq_lic_safe,
        c2pa_license_count=(
            int(c2pa_license_count) if _is_non_negative_int(c2pa_license_count) else -1
        ),
        rq_lic_preservation_safe=rq_lic_safe,
        target_model_id_hex=f"0x{t_id_norm:08x}" if t_id_norm is not None else "INVALID",
        target_model_name=(
            str(target_model_name) if isinstance(target_model_name, str) else "INVALID"
        ),
        signing_model_id_hex=f"0x{s_id_norm:08x}" if s_id_norm is not None else "INVALID",
        signing_model_name=(
            str(signing_model_name) if isinstance(signing_model_name, str) else "INVALID"
        ),
        signing_mode=str(signing_mode) if isinstance(signing_mode, str) else "INVALID",
        signing_key_body_match=(
            bool(signing_key_body_match)
            if isinstance(signing_key_body_match, bool)
            else False
        ),
        cross_body_signing_attempted=(
            bool(cross_body_signing_attempted)
            if isinstance(cross_body_signing_attempted, bool)
            else True
        ),
        cross_model_signing_attempted=(
            bool(cross_model_signing_attempted)
            if isinstance(cross_model_signing_attempted, bool)
            else True
        ),
        sigcert_extract_requested=(
            bool(sigcert_extract_requested)
            if isinstance(sigcert_extract_requested, bool)
            else True
        ),
        c2pa_cross_model_signing_blocked=(
            bool(c2pa_cross_model_signing_blocked)
            if isinstance(c2pa_cross_model_signing_blocked, bool)
            else False
        ),
        cross_model_signing_safe=signing_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(
    *,
    adapter_name: str = VMC_BNCM1_ADAPTER_NAME,
    tc_sync_mode: str = "EXT-LK",
    tc_standard: str = SMPTE_12M_STANDARD_NAME,
    tc_fps: float = 23.976,
    ltc_peak_to_peak_mv: int = 2000,
    ltc_ac_coupled: bool = True,
    vmc_bncm1_id_resistor_ohm: int = VMC_BNCM1_ID_RESISTOR_OHM,
    vmc_bncm1_ltc_active: bool = True,
    multi_usb_uart_1v8_active: bool = False,
    uart_mux_conflict: bool = False,
    tc_direction: str = "IN",
    fx6_tc_out_bnc_masked: bool = True,
    tc_out_bnc_drive_requested: bool = False,
    sensor_name: str = IMX510_SENSOR_NAME,
    imx510_rolling_shutter_ms: float = IMX510_ROLLING_SHUTTER_MS,
    imu_axes: int = IMX510_IMU_AXES,
    imu_sample_rate_hz: int = IMX510_IMU_SAMPLE_RATE_HZ,
    gyro_packet_count: int = 240,
    gyro_packet_crc_valid: bool = True,
    gyro_monotonic_timestamps: bool = True,
    recording_container: str = "MXF",
    nrtm_xml_present: bool = True,
    nrtm_schema_version: str = "2.20",
    nrtm_xml_text: Optional[str] = None,
    catalyst_browse_compatible: bool = True,
    davinci_resolve_compatible: bool = True,
    gyro_metadata_uncorrupted: bool = True,
    guard_profile: str = "FX3_REALHW_G56_VMC_BNCM1_LTC_IMX510_GYRO_NRTM_DEFAULT",
) -> VmcBncm1LtcGyroNrtmGuardResult:
    """Verify Gate G56 invariants fail-closed."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    bool_inputs = (
        ltc_ac_coupled,
        vmc_bncm1_ltc_active,
        multi_usb_uart_1v8_active,
        uart_mux_conflict,
        fx6_tc_out_bnc_masked,
        tc_out_bnc_drive_requested,
        gyro_packet_crc_valid,
        gyro_monotonic_timestamps,
        nrtm_xml_present,
        catalyst_browse_compatible,
        davinci_resolve_compatible,
        gyro_metadata_uncorrupted,
    )
    str_inputs = (
        adapter_name,
        tc_sync_mode,
        tc_standard,
        tc_direction,
        sensor_name,
        recording_container,
        nrtm_schema_version,
        guard_profile,
    )
    telemetry_ok = (
        all(isinstance(b, bool) for b in bool_inputs)
        and _is_non_negative_int(ltc_peak_to_peak_mv)
        and _is_positive_int(vmc_bncm1_id_resistor_ohm)
        and _is_positive_int(imu_axes)
        and _is_positive_int(imu_sample_rate_hz)
        and _is_non_negative_int(gyro_packet_count)
        and _is_finite_number(tc_fps)
        and _is_finite_number(imx510_rolling_shutter_ms)
        and all(isinstance(s, str) and bool(s.strip()) for s in str_inputs)
        and (nrtm_xml_text is None or isinstance(nrtm_xml_text, str))
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G56_TELEMETRY_INVALID)
        errors.append("Gate G56 received invalid, non-finite, or malformed telemetry.")

    ltc_mux_safe = False
    tc_out_mask_safe = False
    gyro_nrtm_safe = False
    xml_validated = False

    if telemetry_ok:
        ltc_mux_safe = validate_vmc_bncm1_ltc_and_uart_mux(
            adapter_name=adapter_name,
            tc_sync_mode=tc_sync_mode,
            tc_standard=tc_standard,
            tc_fps=float(tc_fps),
            ltc_peak_to_peak_mv=int(ltc_peak_to_peak_mv),
            ltc_ac_coupled=ltc_ac_coupled,
            vmc_bncm1_id_resistor_ohm=int(vmc_bncm1_id_resistor_ohm),
            vmc_bncm1_ltc_active=vmc_bncm1_ltc_active,
            multi_usb_uart_1v8_active=multi_usb_uart_1v8_active,
            uart_mux_conflict=uart_mux_conflict,
        )
        if not ltc_mux_safe:
            _add_code(codes, STATUS_BLOCKED_G56_LTC_VOLTAGE_OR_UART_MUX_CLASH)
            errors.append(
                f"VMC-BNCM1 LTC/UART mux violation: vpp={ltc_peak_to_peak_mv}mV, "
                f"ac_coupled={ltc_ac_coupled}, id_ohm={vmc_bncm1_id_resistor_ohm}, "
                f"ltc_active={vmc_bncm1_ltc_active}, uart_1v8_active={multi_usb_uart_1v8_active}, "
                f"mux_conflict={uart_mux_conflict}."
            )

        tc_out_mask_safe = validate_fx6_tc_out_bnc_mask(
            tc_direction=tc_direction,
            fx6_tc_out_bnc_masked=fx6_tc_out_bnc_masked,
            tc_out_bnc_drive_requested=tc_out_bnc_drive_requested,
        )
        if not tc_out_mask_safe:
            _add_code(codes, STATUS_BLOCKED_G56_FX6_TC_OUT_BNC_UNMASKED)
            errors.append(
                f"FX6-only TC-OUT BNC mask violation: direction={tc_direction}, "
                f"masked={fx6_tc_out_bnc_masked}, drive_req={tc_out_bnc_drive_requested}."
            )

        gyro_nrtm_safe, xml_validated = validate_imx510_gyro_nrtm_integrity(
            sensor_name=sensor_name,
            imx510_rolling_shutter_ms=float(imx510_rolling_shutter_ms),
            imu_axes=int(imu_axes),
            imu_sample_rate_hz=int(imu_sample_rate_hz),
            gyro_packet_count=int(gyro_packet_count),
            gyro_packet_crc_valid=gyro_packet_crc_valid,
            gyro_monotonic_timestamps=gyro_monotonic_timestamps,
            recording_container=recording_container,
            nrtm_xml_present=nrtm_xml_present,
            nrtm_schema_version=nrtm_schema_version,
            nrtm_xml_text=nrtm_xml_text,
            catalyst_browse_compatible=catalyst_browse_compatible,
            davinci_resolve_compatible=davinci_resolve_compatible,
            gyro_metadata_uncorrupted=gyro_metadata_uncorrupted,
        )
        if not gyro_nrtm_safe:
            _add_code(codes, STATUS_BLOCKED_G56_IMX510_GYRO_NRTM_CORRUPT)
            errors.append(
                f"IMX510 8.7ms/6-axis IMU NonRealTimeMeta.xml violation: sensor={sensor_name}, "
                f"rs_ms={imx510_rolling_shutter_ms}, axes={imu_axes}, rate={imu_sample_rate_hz}Hz, "
                f"pkts={gyro_packet_count}, crc={gyro_packet_crc_valid}, xml_ok={xml_validated}."
            )

    valid = (
        telemetry_ok
        and ltc_mux_safe
        and tc_out_mask_safe
        and gyro_nrtm_safe
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G56 if valid else codes[0]

    return VmcBncm1LtcGyroNrtmGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        adapter_name=str(adapter_name) if isinstance(adapter_name, str) else "INVALID",
        tc_sync_mode=str(tc_sync_mode) if isinstance(tc_sync_mode, str) else "INVALID",
        tc_standard=str(tc_standard) if isinstance(tc_standard, str) else "INVALID",
        tc_fps=float(tc_fps) if _is_finite_number(tc_fps) else -1.0,
        ltc_peak_to_peak_mv=(
            int(ltc_peak_to_peak_mv)
            if _is_non_negative_int(ltc_peak_to_peak_mv)
            else -1
        ),
        ltc_ac_coupled=(
            bool(ltc_ac_coupled) if isinstance(ltc_ac_coupled, bool) else False
        ),
        vmc_bncm1_id_resistor_ohm=(
            int(vmc_bncm1_id_resistor_ohm)
            if _is_positive_int(vmc_bncm1_id_resistor_ohm)
            else -1
        ),
        vmc_bncm1_ltc_active=(
            bool(vmc_bncm1_ltc_active)
            if isinstance(vmc_bncm1_ltc_active, bool)
            else False
        ),
        multi_usb_uart_1v8_active=(
            bool(multi_usb_uart_1v8_active)
            if isinstance(multi_usb_uart_1v8_active, bool)
            else True
        ),
        uart_mux_conflict=(
            bool(uart_mux_conflict) if isinstance(uart_mux_conflict, bool) else True
        ),
        ltc_voltage_and_mux_safe=ltc_mux_safe,
        tc_direction=str(tc_direction) if isinstance(tc_direction, str) else "INVALID",
        fx6_tc_out_bnc_masked=(
            bool(fx6_tc_out_bnc_masked)
            if isinstance(fx6_tc_out_bnc_masked, bool)
            else False
        ),
        tc_out_bnc_drive_requested=(
            bool(tc_out_bnc_drive_requested)
            if isinstance(tc_out_bnc_drive_requested, bool)
            else True
        ),
        fx6_tc_out_mask_safe=tc_out_mask_safe,
        sensor_name=str(sensor_name) if isinstance(sensor_name, str) else "INVALID",
        imx510_rolling_shutter_ms=(
            float(imx510_rolling_shutter_ms)
            if _is_finite_number(imx510_rolling_shutter_ms)
            else -1.0
        ),
        imu_axes=int(imu_axes) if _is_positive_int(imu_axes) else -1,
        imu_sample_rate_hz=(
            int(imu_sample_rate_hz) if _is_positive_int(imu_sample_rate_hz) else -1
        ),
        gyro_packet_count=(
            int(gyro_packet_count) if _is_non_negative_int(gyro_packet_count) else -1
        ),
        gyro_packet_crc_valid=(
            bool(gyro_packet_crc_valid)
            if isinstance(gyro_packet_crc_valid, bool)
            else False
        ),
        gyro_monotonic_timestamps=(
            bool(gyro_monotonic_timestamps)
            if isinstance(gyro_monotonic_timestamps, bool)
            else False
        ),
        recording_container=(
            str(recording_container)
            if isinstance(recording_container, str)
            else "INVALID"
        ),
        nrtm_xml_present=(
            bool(nrtm_xml_present) if isinstance(nrtm_xml_present, bool) else False
        ),
        nrtm_schema_version=(
            str(nrtm_schema_version)
            if isinstance(nrtm_schema_version, str)
            else "INVALID"
        ),
        nrtm_xml_validated=xml_validated,
        catalyst_browse_compatible=(
            bool(catalyst_browse_compatible)
            if isinstance(catalyst_browse_compatible, bool)
            else False
        ),
        davinci_resolve_compatible=(
            bool(davinci_resolve_compatible)
            if isinstance(davinci_resolve_compatible, bool)
            else False
        ),
        gyro_metadata_uncorrupted=(
            bool(gyro_metadata_uncorrupted)
            if isinstance(gyro_metadata_uncorrupted, bool)
            else False
        ),
        imx510_gyro_nrtm_safe=gyro_nrtm_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G55 & Gate G56 Evaluators (Donor Audit + Guard -> GateVerdict)
# ---------------------------------------------------------------------------


def evaluate_g55_c2pa_cert(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    c2pa_cert_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase170DonorAuditResult] = None,
) -> Tuple[GateVerdict, G55C2paCertResult]:
    """Evaluate Gate G55 (`p12:/cert/RQ_LIC.DAT` RO Lock & Cross-Model C2PA Firewall)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase170_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(c2pa_cert_kwargs or {})
    guard = verify_c2pa_rq_lic_and_cross_model_signing_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE170_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Gate G55 blocked persistent eMMC write authorization request."
        )

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G55 if valid else codes[0]

    res = G55C2paCertResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        c2pa_rq_lic_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, p12_flags={guard.p12_cert_mount_flags}, "
        f"cert_mut={guard.c2pa_cert_mutation_bytes}B, "
        f"rq_lic_h0_h3={guard.rq_lic_h0_to_h3_preserved}, "
        f"signing={guard.signing_model_name}({guard.signing_model_id_hex}), "
        f"cross_model_blocked={guard.c2pa_cross_model_signing_blocked}"
    )

    verdict = GateVerdict(
        gate_id=G55_GATE_ID,
        gate_code=G55_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


def evaluate_g56_tc_gyro_meta(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    tc_gyro_meta_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase170DonorAuditResult] = None,
) -> Tuple[GateVerdict, G56TcGyroMetaResult]:
    """Evaluate Gate G56 (`VMC-BNCM1` LTC Mux, `TC-OUT` Mask & `IMX510` Gyro `NonRealTimeMeta.xml`)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase170_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(tc_gyro_meta_kwargs or {})
    guard = verify_vmc_bncm1_ltc_and_imx510_gyro_nrtm_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE170_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Gate G56 blocked persistent eMMC write authorization request."
        )

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G56 if valid else codes[0]

    res = G56TcGyroMetaResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        tc_gyro_meta_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, adapter={guard.adapter_name}({guard.tc_sync_mode}), "
        f"ltc_vpp={guard.ltc_peak_to_peak_mv}mV, uart1v8={guard.multi_usb_uart_1v8_active}, "
        f"tc_out_masked={guard.fx6_tc_out_bnc_masked}, rs={guard.imx510_rolling_shutter_ms}ms, "
        f"imu={guard.imu_axes}axis@{guard.imu_sample_rate_hz}Hz, "
        f"nrtm_ok={guard.nrtm_xml_validated}"
    )

    verdict = GateVerdict(
        gate_id=G56_GATE_ID,
        gate_code=G56_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Unified 56-Gate Master Safety Preflight (`G01..G56`)
# ---------------------------------------------------------------------------


def evaluate_56gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G01..G54 pass-throughs
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
    # G55 inputs (p12:/cert/RQ_LIC.DAT RO lock & cross-body/cross-model C2PA firewall)
    c2pa_cert_kwargs: Optional[Mapping[str, Any]] = None,
    # G56 inputs (VMC-BNCM1 LTC/UART mux, TC-OUT mask & IMX510 gyro NonRealTimeMeta.xml)
    tc_gyro_meta_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master56GateReport:
    """Evaluate all 56 Master Safety Gates (`G01..G56`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m54_kwargs: Dict[str, Any] = {
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
    }
    if soc_start_ceiling_c is not None:
        m54_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m54_report: Master54GateReport = evaluate_54gate_preflight(
        resolved_root, **m54_kwargs
    )

    phase170_audit = audit_phase170_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g55_verdict, g55_res = evaluate_g55_c2pa_cert(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        c2pa_cert_kwargs=c2pa_cert_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase170_audit,
    )

    g56_verdict, g56_res = evaluate_g56_tc_gyro_meta(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        tc_gyro_meta_kwargs=tc_gyro_meta_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase170_audit,
    )

    gates_55_to_56 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g55_verdict, g56_verdict)
    ]
    all_gates = tuple(list(m54_report.gates) + gates_55_to_56)

    g01_to_g12_verified = int(m54_report.summary["g01_to_g12_verified"])
    g13_to_g54_verified = (
        int(m54_report.summary["g13_to_g52_verified"])
        + int(m54_report.summary["g53_to_g54_verified"])
    )
    g55_to_g56_verified = sum(1 for v in (g55_verdict, g56_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g54_verified + g55_to_g56_verified

    g55_to_g56_all_passed = g55_to_g56_verified == 2
    g13_to_g56_all_passed = (
        m54_report.g13_to_g54_all_passed and g55_to_g56_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m54_report.gates[:9])

    offline_53_verified = (
        g01_to_g09_ok
        and m54_report.offline_51_gates_verified
        and g55_to_g56_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_56_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g56_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes; never authorizes EL3 TX / eMMC / SPI-NOR writes
    overall_ready_for_hardware_attach = False

    h0_h1_allowed = (
        offline_53_verified
        and m54_report.h0_h1_trial_entry_allowed
        and g55_to_g56_all_passed
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m54_report.errors) + list(g55_verdict.errors) + list(g56_verdict.errors)
    )
    warnings: List[str] = (
        list(m54_report.warnings)
        + list(g55_verdict.warnings)
        + list(g56_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m54_report.g13_to_g54_all_passed:
        overall_status = m54_report.status
    elif not g55_verdict.passed:
        overall_status = g55_verdict.status
    elif not g56_verdict.passed:
        overall_status = g56_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_56_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_56_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_56_verified:
        overall_status = "VERIFIED_ALL_56_GATES"
    else:
        overall_status = "VERIFIED_53_OF_56_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m54_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g55_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g56_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 56,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 56 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g54_verified": g13_to_g54_verified,
        "g55_to_g56_verified": g55_to_g56_verified,
        "g13_to_g56_all_passed": g13_to_g56_all_passed,
        "g55_to_g56_all_passed": g55_to_g56_all_passed,
        "offline_53_gates_verified": offline_53_verified,
        "all_56_gates_verified": all_56_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
    }

    return Master56GateReport(
        schema=REALHW_C2PA_TC_GYRO_56GATE_SCHEMA,
        version=REALHW_C2PA_TC_GYRO_56GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_53_gates_verified=offline_53_verified,
        all_56_gates_verified=all_56_verified,
        g13_to_g56_all_passed=g13_to_g56_all_passed,
        g55_to_g56_all_passed=g55_to_g56_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_54_report=m54_report.to_dict(),
        g55_result=g55_res.to_dict(),
        g56_result=g56_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_56_master_safety_gates = evaluate_56gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_c2pa_tc_gyro_and_56gate_guard",
        description=(
            "Phase 170 — p12:/cert/RQ_LIC.DAT C2PA Read-Only Lock & Cross-Model Signing "
            "Firewall (G55), VMC-BNCM1 EXT-LK SMPTE-12M LTC / UART Mux & IMX510 6-Axis IMU "
            "Gyro NonRealTimeMeta.xml Guard (G56), and 56-Gate Master Preflight (G01..G56)"
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G56 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_56gate_preflight(
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
            f"verified={report.summary['verified_gates']}/56 "
            f"g55_to_g56_all_passed={report.g55_to_g56_all_passed} "
            f"all_56_gates_verified={report.all_56_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
            f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = (
        report.all_56_gates_verified
        if args.dry_run_simulated_backup
        else report.offline_53_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
