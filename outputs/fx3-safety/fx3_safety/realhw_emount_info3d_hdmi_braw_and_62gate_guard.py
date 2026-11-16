"""Phase 181 — Real-Hardware Main Track Part 18:
Gate G61 (`MIRA_CETUS2` E-Mount `info7/info8/info3D` + `0x02cf0232` Breathing
Guard + Monitor & Control `Ver. 2.1.0+` Focus Map RO + `p18:/lens/LENSFILE.BIN`
`BLKROSET=1`),
Gate G62 (`Type-A HDMI 4264x2408` 16-bit Linear RAW `Blackmagic Video Assist
12G HDR` `.braw` & `Atomos Ninja` `ProRes RAW` vs `12G-SDI` MMIO Mask Guard),
and 62-Gate Master Preflight (`G01..G62` / `verify-62-gates`).

Composes `realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard` (`G01..G60`, keeping
`evaluate_58gate_preflight`, `evaluate_60gate_preflight`, `verify-58-gates`,
and `verify-60-gates` 100% intact) with Wave-22 Sony `MIRA_CETUS2` Real-Hardware
Intelligence (`G61` and `G62`) while hard-locking all physical flash/write/
transmit redlines:
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`
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

from .exfat_media_integrity_guard import MediaSlotConfig
from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    GateVerdict,
    P12_WLAN_FATAL_GUARD_VMA,
)
from .realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard import (
    Master60GateReport,
    evaluate_60gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_EMOUNT_INFO3D_HDMI_BRAW_62GATE_SCHEMA: str = (
    "fx3-realhw-emount-info3d-hdmi-braw-62gate-preflight-v1"
)
REALHW_EMOUNT_INFO3D_HDMI_BRAW_62GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED: bool = False
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

# Gate IDs & Canonical Codes for G61..G62
G61_GATE_ID: str = "G61_emount_info7_8_3d_lensid_and_breathing_02cf0232_guard"
G61_GATE_CODE: str = (
    "GATE_G61_EMOUNT_INFO7_8_3D_LENSID_AND_BREATHING_02CF0232_GUARD"
)
GATE_G61_EMOUNT_INFO7_8_3D_LENSID_AND_BREATHING_02CF0232_GUARD: str = G61_GATE_CODE
G61: str = G61_GATE_CODE

G62_GATE_ID: str = "G62_hdmi_4264x2408_16bit_raw_braw_prores_vs_12gsdi_guard"
G62_GATE_CODE: str = (
    "GATE_G62_HDMI_4264X2408_16BIT_RAW_BRAW_PRORES_VS_12GSDI_GUARD"
)
GATE_G62_HDMI_4264X2408_16BIT_RAW_BRAW_PRORES_VS_12GSDI_GUARD: str = G62_GATE_CODE
G62: str = G62_GATE_CODE

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G61: str = (
    "VERIFIED_EMOUNT_INFO7_8_3D_LENSID_AND_BREATHING_02CF0232_GUARD"
)
STATUS_VERIFIED_G62: str = (
    "VERIFIED_HDMI_4264X2408_16BIT_RAW_BRAW_PRORES_VS_12GSDI_GUARD"
)

# Gate G61 Violation Codes
STATUS_BLOCKED_G61_EMOUNT_SERIAL_INFO7_8_3D_CORRUPT: str = (
    "BLOCKED_G61_EMOUNT_SERIAL_INFO7_8_3D_CORRUPT"
)
STATUS_BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED: str = (
    "BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED"
)
STATUS_BLOCKED_G61_FOCUS_MAP_TELEMETRY_WRITE_UNSAFE: str = (
    "BLOCKED_G61_FOCUS_MAP_TELEMETRY_WRITE_UNSAFE"
)
STATUS_BLOCKED_G61_P18_LENSFILE_RO_OR_CINEALTA_SLOT_WRITE: str = (
    "BLOCKED_G61_P18_LENSFILE_RO_OR_CINEALTA_SLOT_WRITE"
)
STATUS_BLOCKED_G61_TELEMETRY_INVALID: str = (
    "BLOCKED_G61_EMOUNT_BREATHING_TELEMETRY_INVALID"
)

# Gate G62 Violation Codes
STATUS_BLOCKED_G62_HDMI_4264X2408_16BIT_RAW_SPEC_INVALID: str = (
    "BLOCKED_G62_HDMI_4264X2408_16BIT_RAW_SPEC_INVALID"
)
STATUS_BLOCKED_G62_BRAW_VIDEO_ASSIST_3G_OR_FW_UNSUPPORTED: str = (
    "BLOCKED_G62_BRAW_VIDEO_ASSIST_3G_OR_FW_UNSUPPORTED"
)
STATUS_BLOCKED_G62_ATOMOS_NINJA_FW_OR_METADATA_INVALID: str = (
    "BLOCKED_G62_ATOMOS_NINJA_FW_OR_METADATA_INVALID"
)
STATUS_BLOCKED_G62_FX6_12GSDI_MMIO_PROBE_UNMASKED: str = (
    "BLOCKED_G62_FX6_12GSDI_MMIO_PROBE_UNMASKED"
)
STATUS_BLOCKED_G62_TELEMETRY_INVALID: str = (
    "BLOCKED_G62_HDMI_RAW_12GSDI_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE181_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE181_62GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G61 Constants — MIRA_CETUS2 E-Mount info7/info8/info3D & 0x02cf0232
PLATFORM_MIRA_CETUS2: str = "MIRA_CETUS2"
BKID_APP_MR_SETTING_LENS_COMP_BREATHING: int = 0x02CF0232
BKID_APP_MR_SETTING_LENS_COMP_BREATHING_HEX: str = "0x02cf0232"
EMOUNT_SERIAL_PACKET_TYPES: Tuple[str, ...] = ("info7", "info8", "info3D")
INFO7_LENS_ID_BITS: int = 16
SONY_FIRST_PARTY_LENS_PREFIX_BITS: int = 3
SONY_LENS_ID_INVALID_LOW12: int = 0x0FFF
DEFAULT_SAFE_SONY_EMOUNT_LENS_ID: int = 0xC01A
MONITOR_CONTROL_MIN_VERSION: str = "2.1.0"
FOCUS_MAP_ALLOWED_TRANSPORTS: Tuple[str, ...] = (
    "WIFI",
    "WIRED_USB",
    "USB_LAN",
    "NONE",
)
P18_DEVICE_NODE: str = "/dev/nflasha18"
P18_MOUNT_POINT: str = "/lens"
P18_LENSFILE_PATH: str = "p18:/lens/LENSFILE.BIN"
P18_LENSFILE_EXPECTED_BYTES: int = 262_592
P18_REQUIRED_MOUNT_FLAG: str = "MS_RDONLY"
DEFAULT_SYNTHETIC_LENSFILE_SHA256: str = (
    "49a08398bd47b917bc54497f247ef19fcb77df593610aea15e4ae0c466e24824"
)

# Gate G62 Constants — FX3 7.02 Type-A HDMI 4264x2408 16-bit RAW vs 12G-SDI
FX3_HDMI_CONNECTOR_TYPE: str = "TYPE_A_FULL_SIZE"
FX3_HDMI_RAW_WIDTH: int = 4264
FX3_HDMI_RAW_HEIGHT: int = 2408
FX3_HDMI_RAW_ASPECT_RATIO: str = "16:9"
FX3_HDMI_RAW_BIT_DEPTH: int = 16
FX3_HDMI_RAW_COLOR_ENCODING: str = "LINEAR_RAW"
FX3_HDMI_RAW_MAX_FPS: float = 60.0
SUPPORTED_HDMI_RAW_FPS: Tuple[float, ...] = (
    23.976,
    24.0,
    25.0,
    29.97,
    30.0,
    50.0,
    59.94,
    60.0,
)
ALLOWED_INTERNAL_SIMULTANEOUS_CODECS: Tuple[str, ...] = (
    "XAVC_S",
    "XAVC_HS",
    "XAVC_S_I",
    "XAVC_S_PROXY",
    "XAVC_HS_PROXY",
    "XAVC_S_I_PROXY",
    "NONE",
)
VALID_RECORDER_MODES: Tuple[str, ...] = (
    "BRAW_VIDEO_ASSIST_12G",
    "PRORES_RAW_ATOMOS_NINJA",
    "BOTH",
    "NONE_INTERNAL_ONLY",
)
BRAW_ALLOWED_MODELS: Tuple[str, ...] = (
    "VIDEO_ASSIST_5_12G_HDR",
    "VIDEO_ASSIST_7_12G_HDR",
    "VIDEO_ASSIST_12G_HDR",
)
BRAW_REJECTED_3G_MODELS: Tuple[str, ...] = (
    "VIDEO_ASSIST_3G",
    "VIDEO_ASSIST_5_3G",
    "VIDEO_ASSIST_7_3G",
)
BRAW_MIN_VIDEO_ASSIST_FW: str = "3.22"
BRAW_MIN_SDK_VERSION: str = "5.1"
RESOLVE_MIN_VERSION: str = "20.2"
ATOMOS_ALLOWED_MODELS: Tuple[str, ...] = (
    "NINJA_V",
    "NINJA_V_PLUS",
    "NINJA_ULTRA",
    "NINJA",
)
ATOMOS_MIN_FW_VERSION: str = "10.64"
FX3_HAS_PHYSICAL_12GSDI_BNC: bool = False
FX6_FORBIDDEN_SDI_RAW_MODES: Tuple[str, ...] = (
    "12G_SDI",
    "12G-SDI",
    "12G_SDI_RAW",
    "SDI_RAW",
    "BNC_SDI_RAW",
    "MEW_SDI_RAW",
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_TRIVIAL_HEX64: Tuple[str, ...] = ("0" * 64, "f" * 64)
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?$", re.IGNORECASE)

# Pinned FX3 v7.02 & p18 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE181_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"SET_BREATHING_CORRECTION",
            b"CacheFlashBreathingCorrectionData",
            b"FocusMap",
            b"fixed_lensfile",
            b"RAW_OUTPUT",
            b"ADF_OutSetHDMIFormat",
        ),
        "fx3/cpapp-b.bin::{15980568B,ILME-FX3,SET_BREATHING_CORRECTION,CacheFlashBreathingCorrectionData,FocusMap,fixed_lensfile,RAW_OUTPUT,ADF_OutSetHDMIFormat}",
    ),
    "fx3_appfw_so": (
        "fx3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f",
        (
            b"\x7fELF",
            b"PID_SET_BREATHING_CORRECTION",
            b"uc_BreathingCorrectionLensType",
            b"No27_FocusMap",
            b"HDMI_RAW",
            b"RAW_OUTPUT",
            b"HDMI_RESOLUTION_AUTO",
            b"MIRA",
            b"CETUS",
        ),
        "fx3/appFw.so::{79015712B,ELF,PID_SET_BREATHING_CORRECTION,uc_BreathingCorrectionLensType,No27_FocusMap,HDMI_RAW,RAW_OUTPUT,HDMI_RESOLUTION_AUTO,MIRA,CETUS}",
    ),
    "p18_lensfile": (
        "p18",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0800_appli/lens/lensfile.bin",
        262_592,
        "49a08398bd47b917bc54497f247ef19fcb77df593610aea15e4ae0c466e24824",
        (b"VX8900", b"VX8901", b"VX8902"),
        "p18/lens/LENSFILE.BIN::{262592B,VX8900,VX8901,VX8902}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase181DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    p18_lensfile_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EmountInfo3dBreathingGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    platform_name: str
    bkid_breathing_hex: str
    info7_packet_valid: bool
    info8_packet_valid: bool
    info3d_packet_valid: bool
    emount_serial_packets_valid: bool
    lens_id: int
    lens_id_hex: str
    is_sony_first_party_lens: bool
    breathing_compensation_enabled: bool
    catalyst_breathing_metadata_write: bool
    lens_id_whitelist_enforced: bool
    bkid_02cf0232_passthrough_intact: bool
    breathing_guard_valid: bool
    focus_map_enabled: bool
    monitor_control_version: str
    monitor_control_min_version: str
    focus_map_transport: str
    focus_map_readonly_telemetry: bool
    focus_map_emmc_writes: int
    focus_map_cp_mutation_bytes: int
    focus_map_guard_valid: bool
    p18_device_node: str
    p18_lensfile_path: str
    p18_blkroset: int
    p18_mount_flags: str
    p18_lensfile_sha256: str
    lens_partition_writes: int
    cinealta_manual_lensfile_slot_write_requested: bool
    cinealta_manual_lensfile_slot_write_blocked: bool
    cpapp_stock_preserved: bool
    p18_lensfile_guard_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Hdmi4264x2408RawVs12gSdiGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    hdmi_connector_type: str
    hdmi_raw_width: int
    hdmi_raw_height: int
    hdmi_raw_aspect_ratio: str
    hdmi_raw_bit_depth: int
    hdmi_raw_color_encoding: str
    hdmi_raw_fps: float
    simultaneous_internal_codec: str
    simultaneous_proxy_enabled: bool
    hdmi_raw_spec_valid: bool
    recorder_mode: str
    braw_recorder_model: str
    braw_video_assist_fw: str
    braw_sdk_version: str
    resolve_version: str
    braw_iso_capture_state_locked: bool
    braw_private_sensor_profile_expected: bool
    braw_compat_valid: bool
    atomos_recorder_model: str
    atomos_fw_version: str
    prores_raw_wb_iso_offset_metadata_verified: bool
    atomos_prores_compat_valid: bool
    fx3_has_physical_12gsdi_bnc: bool
    sdi_mmio_probes_emitted: int
    sdi_driver_probes_masked: bool
    fx6_12gsdi_raw_enabled: bool
    hdmi_raw_pipeline_routed: bool
    sdi_mask_guard_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G61EmountBreathingResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    emount_breathing_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G62HdmiRawGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    hdmi_raw_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master62GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_59_gates_verified: bool
    all_62_gates_verified: bool
    g13_to_g62_all_passed: bool
    g61_to_g62_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_60_report: Dict[str, Any]
    g61_result: Dict[str, Any]
    g62_result: Dict[str, Any]
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


def _is_valid_hex64(val: Any, *, allow_trivial: bool = False) -> bool:
    if not isinstance(val, str):
        return False
    norm = val.strip().lower()
    if not _HEX64_RE.match(norm):
        return False
    if not allow_trivial and norm in _FORBIDDEN_TRIVIAL_HEX64:
        return False
    return True


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


def _normalize_ro_flag(val: Any) -> Optional[int]:
    if isinstance(val, bool):
        return 1 if val else 0
    if isinstance(val, int) and val in (0, 1):
        return int(val)
    return None


def _is_finite_number(val: Any) -> bool:
    if isinstance(val, bool):
        return False
    if not isinstance(val, (int, float)):
        return False
    return abs(float(val)) < 1e12 and (float(val) == float(val))


def parse_semver_tuple(version_str: Any) -> Optional[Tuple[int, int, int]]:
    """Parse a version string such as `'2.1.0'`, `'3.22'`, or `'10.64'` into `(major, minor, patch)`."""
    if not isinstance(version_str, str):
        return None
    m = _VERSION_RE.match(version_str.strip())
    if not m:
        return None
    major = int(m.group(1))
    minor = int(m.group(2))
    patch = int(m.group(3)) if m.group(3) is not None else 0
    return (major, minor, patch)


def is_sony_first_party_breathing_lens(lens_id: Any) -> bool:
    """Apply Sony CPAPP 16-bit E-Mount lens ID breathing compensation filter:
    `((lens_id >> 14) == 3) && ((lens_id & 0x0FFF) != 0x0FFF)`.
    """
    norm = _normalize_int_value(lens_id)
    if norm is None or norm < 0 or norm > 0xFFFF:
        return False
    return ((norm >> 14) == SONY_FIRST_PARTY_LENS_PREFIX_BITS) and (
        (norm & 0x0FFF) != SONY_LENS_ID_INVALID_LOW12
    )


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit (FX3 7.02 + p18)
# ---------------------------------------------------------------------------


def audit_phase181_donor_contracts(
    *_,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase181DonorAuditResult:
    """Inspect FX3 `7.02` `cpapp-b.bin`, `appFw.so`, and `p18:/lens/LENSFILE.BIN`
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
        ) in PINNED_PHASE181_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase181DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE181_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=True,
            p18_lensfile_verified=True,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE181_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE181_DONOR_SPECS.items()
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
    ) in PINNED_PHASE181_DONOR_SPECS.items():
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
        k for k, spec in PINNED_PHASE181_DONOR_SPECS.items() if spec[0] == "fx3"
    }
    p18_keys = {
        k for k, spec in PINNED_PHASE181_DONOR_SPECS.items() if spec[0] == "p18"
    }
    valid = len(errors) == 0 and len(missing) == 0
    return Phase181DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE181_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_keys.issubset(passed_keys) and valid,
        p18_lensfile_verified=p18_keys.issubset(passed_keys) and valid,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Pure Helper Validators (G61 & G62)
# ---------------------------------------------------------------------------


def validate_emount_info7_8_3d_packets(
    *,
    platform_name: str = PLATFORM_MIRA_CETUS2,
    info7_packet_valid: bool = True,
    info8_packet_valid: bool = True,
    info3d_packet_valid: bool = True,
    info7_lens_id: int | str = DEFAULT_SAFE_SONY_EMOUNT_LENS_ID,
    info8_drive_params_valid: bool = True,
    info3d_optical_profile_valid: bool = True,
    emount_serial_crc_ok: bool = True,
    emount_packet_channels_intact: bool = True,
) -> Tuple[bool, str, List[str]]:
    """Verify `MIRA_CETUS2` E-Mount serial packet integrity (`info7` 16-bit lens ID,
    `info8` focus/iris drive parameters, and `info3D` extended optical profile).
    """
    errors: List[str] = []
    lens_id_int = _normalize_int_value(info7_lens_id)
    lens_id_range_ok = lens_id_int is not None and 0 <= lens_id_int <= 0xFFFF
    ok = (
        platform_name.strip().upper() == PLATFORM_MIRA_CETUS2
        and info7_packet_valid
        and info8_packet_valid
        and info3d_packet_valid
        and lens_id_range_ok
        and info8_drive_params_valid
        and info3d_optical_profile_valid
        and emount_serial_crc_ok
        and emount_packet_channels_intact
    )
    if not ok:
        errors.append(
            f"MIRA_CETUS2 E-Mount serial packet integrity check failed: "
            f"platform={platform_name!r}, info7={info7_packet_valid}, "
            f"info8={info8_packet_valid}, info3D={info3d_packet_valid}, "
            f"lens_id={info7_lens_id!r}, drive_ok={info8_drive_params_valid}, "
            f"optical_ok={info3d_optical_profile_valid}, crc_ok={emount_serial_crc_ok}, "
            f"channels_intact={emount_packet_channels_intact}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G61_EMOUNT_SERIAL_INFO7_8_3D_CORRUPT),
        errors,
    )


def validate_breathing_02cf0232_lens_filter(
    *,
    lens_id: int | str = DEFAULT_SAFE_SONY_EMOUNT_LENS_ID,
    bkid_hex: str = BKID_APP_MR_SETTING_LENS_COMP_BREATHING_HEX,
    breathing_compensation_enabled: bool = True,
    catalyst_breathing_metadata_write: bool = True,
    lens_id_whitelist_enforced: bool = True,
    bkid_02cf0232_passthrough_intact: bool = True,
) -> Tuple[bool, str, List[str]]:
    """Enforce Sony first-party lens capability filter
    `((lens_id >> 14) == 3) && ((lens_id & 0x0FFF) != 0x0FFF)` for
    `BKID_APP_MR_SETTING_LENS_COMP_BREATHING` (`0x02cf0232`) and lossless
    Stage-B shim passthrough.
    """
    errors: List[str] = []
    bkid_int = _normalize_int_value(bkid_hex)
    lens_id_int = _normalize_int_value(lens_id)
    first_party = is_sony_first_party_breathing_lens(lens_id_int)

    breathing_active = (
        breathing_compensation_enabled or catalyst_breathing_metadata_write
    )
    filter_ok = (not breathing_active) or first_party
    ok = (
        bkid_int == BKID_APP_MR_SETTING_LENS_COMP_BREATHING
        and lens_id_int is not None
        and 0 <= lens_id_int <= 0xFFFF
        and lens_id_whitelist_enforced
        and bkid_02cf0232_passthrough_intact
        and filter_ok
    )
    if not ok:
        errors.append(
            f"0x02cf0232 Focus Breathing filter rejected: lens_id={lens_id!r} "
            f"(first_party={first_party}), bkid={bkid_hex!r}, "
            f"breathing_enabled={breathing_compensation_enabled}, "
            f"catalyst_meta={catalyst_breathing_metadata_write}, "
            f"whitelist_enforced={lens_id_whitelist_enforced}, "
            f"passthrough={bkid_02cf0232_passthrough_intact}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED),
        errors,
    )


def validate_focus_map_readonly_telemetry(
    *,
    focus_map_enabled: bool = True,
    monitor_control_version: str = MONITOR_CONTROL_MIN_VERSION,
    focus_map_transport: str = "WIRED_USB",
    focus_map_readonly_telemetry: bool = True,
    focus_map_emmc_writes: int = 0,
    focus_map_cp_mutation_bytes: int = 0,
) -> Tuple[bool, str, List[str]]:
    """Enforce Monitor & Control `Ver. 2.1.0+` Focus Map read-only depth telemetry
    with zero eMMC or CP mutation.
    """
    errors: List[str] = []
    mc_ver = parse_semver_tuple(monitor_control_version)
    min_ver = parse_semver_tuple(MONITOR_CONTROL_MIN_VERSION)
    assert min_ver is not None
    ver_ok = (not focus_map_enabled) or (mc_ver is not None and mc_ver >= min_ver)
    transport_ok = (
        focus_map_transport.strip().upper() in FOCUS_MAP_ALLOWED_TRANSPORTS
    )
    ok = (
        ver_ok
        and transport_ok
        and focus_map_readonly_telemetry
        and int(focus_map_emmc_writes) == 0
        and int(focus_map_cp_mutation_bytes) == 0
    )
    if not ok:
        errors.append(
            f"Focus Map telemetry safety violation: enabled={focus_map_enabled}, "
            f"mc_ver={monitor_control_version!r} (requires >= {MONITOR_CONTROL_MIN_VERSION}), "
            f"transport={focus_map_transport!r}, readonly={focus_map_readonly_telemetry}, "
            f"emmc_writes={focus_map_emmc_writes}, cp_mut={focus_map_cp_mutation_bytes}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G61_FOCUS_MAP_TELEMETRY_WRITE_UNSAFE),
        errors,
    )


def validate_p18_lensfile_ro_and_cinealta_block(
    *,
    p18_device_node: str = P18_DEVICE_NODE,
    p18_lensfile_path: str = P18_LENSFILE_PATH,
    p18_blkroset: int | bool = 1,
    p18_mount_flags: str = P18_REQUIRED_MOUNT_FLAG,
    p18_lensfile_sha256: str = DEFAULT_SYNTHETIC_LENSFILE_SHA256,
    lens_partition_writes: int = 0,
    cinealta_manual_lensfile_slot_write_requested: bool = False,
    cinealta_manual_lensfile_slot_write_blocked: bool = True,
    cpapp_stock_preserved: bool = True,
) -> Tuple[bool, str, List[str]]:
    """Enforce `BLKROSET=1` + `MS_RDONLY` on `p18:/lens/LENSFILE.BIN`
    (`lens_partition_writes == 0`) and block legacy CineAlta manual `LENSFILE` slot writes.
    """
    errors: List[str] = []
    ro_flag = _normalize_ro_flag(p18_blkroset)
    flags_upper = [
        f.strip().upper() for f in p18_mount_flags.split(",") if f.strip()
    ]
    norm_path = p18_lensfile_path.strip().lower()
    path_ok = norm_path in (
        "p18:/lens/lensfile.bin",
        "/lens/lensfile.bin",
    )
    ok = (
        p18_device_node.strip() == P18_DEVICE_NODE
        and path_ok
        and ro_flag == 1
        and (P18_REQUIRED_MOUNT_FLAG in flags_upper or "RO" in flags_upper)
        and _is_valid_hex64(p18_lensfile_sha256)
        and int(lens_partition_writes) == 0
        and (not cinealta_manual_lensfile_slot_write_requested)
        and cinealta_manual_lensfile_slot_write_blocked
        and cpapp_stock_preserved
    )
    if not ok:
        errors.append(
            f"p18:/lens/LENSFILE.BIN protection violated: dev={p18_device_node!r}, "
            f"path={p18_lensfile_path!r}, blkroset={ro_flag}, flags={p18_mount_flags!r}, "
            f"lens_writes={lens_partition_writes}, "
            f"cinealta_slot_req={cinealta_manual_lensfile_slot_write_requested}, "
            f"cinealta_slot_blocked={cinealta_manual_lensfile_slot_write_blocked}, "
            f"cpapp_stock={cpapp_stock_preserved}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G61_P18_LENSFILE_RO_OR_CINEALTA_SLOT_WRITE),
        errors,
    )


def validate_hdmi_4264x2408_16bit_raw_spec(
    *,
    hdmi_connector_type: str = FX3_HDMI_CONNECTOR_TYPE,
    hdmi_raw_width: int = FX3_HDMI_RAW_WIDTH,
    hdmi_raw_height: int = FX3_HDMI_RAW_HEIGHT,
    hdmi_raw_aspect_ratio: str = FX3_HDMI_RAW_ASPECT_RATIO,
    hdmi_raw_bit_depth: int = FX3_HDMI_RAW_BIT_DEPTH,
    hdmi_raw_color_encoding: str = FX3_HDMI_RAW_COLOR_ENCODING,
    hdmi_raw_fps: float = 59.94,
    simultaneous_internal_codec: str = "XAVC_S_I",
    simultaneous_proxy_enabled: bool = True,
) -> Tuple[bool, str, List[str]]:
    """Verify FX3 `7.02` Type-A full-size HDMI `4264x2408` (`16:9` up to `60p`)
    16-bit linear RAW specification alongside simultaneous internal `XAVC S/HS/S-I + Proxy`.
    """
    errors: List[str] = []
    fps_val = float(hdmi_raw_fps)
    fps_matched = any(abs(fps_val - ref) < 0.02 for ref in SUPPORTED_HDMI_RAW_FPS)
    codec_norm = (
        simultaneous_internal_codec.strip()
        .upper()
        .replace("-", "_")
        .replace(" ", "_")
    )
    ok = (
        hdmi_connector_type.strip().upper() == FX3_HDMI_CONNECTOR_TYPE
        and int(hdmi_raw_width) == FX3_HDMI_RAW_WIDTH
        and int(hdmi_raw_height) == FX3_HDMI_RAW_HEIGHT
        and hdmi_raw_aspect_ratio.strip() == FX3_HDMI_RAW_ASPECT_RATIO
        and int(hdmi_raw_bit_depth) == FX3_HDMI_RAW_BIT_DEPTH
        and hdmi_raw_color_encoding.strip().upper() == FX3_HDMI_RAW_COLOR_ENCODING
        and 0.0 < fps_val <= FX3_HDMI_RAW_MAX_FPS
        and fps_matched
        and codec_norm in ALLOWED_INTERNAL_SIMULTANEOUS_CODECS
        and isinstance(simultaneous_proxy_enabled, bool)
    )
    if not ok:
        errors.append(
            f"FX3 Type-A HDMI 4264x2408 16-bit RAW spec rejected: "
            f"connector={hdmi_connector_type!r}, res={hdmi_raw_width}x{hdmi_raw_height} "
            f"({hdmi_raw_aspect_ratio!r}), bits={hdmi_raw_bit_depth}, "
            f"enc={hdmi_raw_color_encoding!r}, fps={hdmi_raw_fps}, "
            f"internal_codec={simultaneous_internal_codec!r}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G62_HDMI_4264X2408_16BIT_RAW_SPEC_INVALID),
        errors,
    )


def validate_braw_video_assist_12g_compat(
    *,
    recorder_mode: str = "BOTH",
    braw_recorder_model: str = "VIDEO_ASSIST_7_12G_HDR",
    braw_video_assist_fw: str = BRAW_MIN_VIDEO_ASSIST_FW,
    braw_sdk_version: str = BRAW_MIN_SDK_VERSION,
    resolve_version: str = RESOLVE_MIN_VERSION,
    braw_iso_capture_state_locked: bool = True,
    braw_private_sensor_profile_expected: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Enforce `Blackmagic Video Assist 12G HDR` (`3.22+`) `.braw` compatibility:
    reject `3G` models, enforce `3.22+` / `BRAW 5.1+` / `Resolve 20.2+`, and verify
    `.braw` ISO capture-state lock (no private Blackmagic sensor profile sent over Sony HDMI RAW).
    """
    errors: List[str] = []
    mode_norm = recorder_mode.strip().upper()
    if mode_norm not in ("BRAW_VIDEO_ASSIST_12G", "BOTH"):
        return True, "", errors

    model_norm = braw_recorder_model.strip().upper().replace(" ", "_")
    is_3g = ("3G" in model_norm) or (model_norm in BRAW_REJECTED_3G_MODELS)
    model_ok = (not is_3g) and (model_norm in BRAW_ALLOWED_MODELS)

    fw_ver = parse_semver_tuple(braw_video_assist_fw)
    min_fw = parse_semver_tuple(BRAW_MIN_VIDEO_ASSIST_FW)
    sdk_ver = parse_semver_tuple(braw_sdk_version)
    min_sdk = parse_semver_tuple(BRAW_MIN_SDK_VERSION)
    res_ver = parse_semver_tuple(resolve_version)
    min_res = parse_semver_tuple(RESOLVE_MIN_VERSION)
    assert min_fw is not None and min_sdk is not None and min_res is not None

    ok = (
        model_ok
        and (fw_ver is not None and fw_ver >= min_fw)
        and (sdk_ver is not None and sdk_ver >= min_sdk)
        and (res_ver is not None and res_ver >= min_res)
        and braw_iso_capture_state_locked
        and (not braw_private_sensor_profile_expected)
    )
    if not ok:
        errors.append(
            f"Blackmagic .braw Video Assist compatibility rejected: "
            f"model={braw_recorder_model!r} (3G rejected), fw={braw_video_assist_fw!r} "
            f"(>= {BRAW_MIN_VIDEO_ASSIST_FW}), sdk={braw_sdk_version!r} "
            f"(>= {BRAW_MIN_SDK_VERSION}), resolve={resolve_version!r} "
            f"(>= {RESOLVE_MIN_VERSION}), iso_locked={braw_iso_capture_state_locked}, "
            f"private_profile_expected={braw_private_sensor_profile_expected}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G62_BRAW_VIDEO_ASSIST_3G_OR_FW_UNSUPPORTED),
        errors,
    )


def validate_atomos_ninja_prores_raw_compat(
    *,
    recorder_mode: str = "BOTH",
    atomos_recorder_model: str = "NINJA_V_PLUS",
    atomos_fw_version: str = ATOMOS_MIN_FW_VERSION,
    resolve_version: str = RESOLVE_MIN_VERSION,
    prores_raw_wb_iso_offset_metadata_verified: bool = True,
) -> Tuple[bool, str, List[str]]:
    """Enforce `Atomos Ninja` (`AtomOS 10.64+`) `ProRes RAW` compatibility and
    WB/ISO offset metadata verification.
    """
    errors: List[str] = []
    mode_norm = recorder_mode.strip().upper()
    if mode_norm not in ("PRORES_RAW_ATOMOS_NINJA", "BOTH"):
        return True, "", errors

    model_norm = (
        atomos_recorder_model.strip()
        .upper()
        .replace("+", "_PLUS")
        .replace(" ", "_")
    )
    model_ok = model_norm in ATOMOS_ALLOWED_MODELS
    fw_ver = parse_semver_tuple(atomos_fw_version)
    min_fw = parse_semver_tuple(ATOMOS_MIN_FW_VERSION)
    res_ver = parse_semver_tuple(resolve_version)
    min_res = parse_semver_tuple(RESOLVE_MIN_VERSION)
    assert min_fw is not None and min_res is not None

    ok = (
        model_ok
        and (fw_ver is not None and fw_ver >= min_fw)
        and (res_ver is not None and res_ver >= min_res)
        and prores_raw_wb_iso_offset_metadata_verified
    )
    if not ok:
        errors.append(
            f"Atomos Ninja ProRes RAW compatibility rejected: "
            f"model={atomos_recorder_model!r}, atomos_fw={atomos_fw_version!r} "
            f"(>= {ATOMOS_MIN_FW_VERSION}), resolve={resolve_version!r} "
            f"(>= {RESOLVE_MIN_VERSION}), wb_iso_meta={prores_raw_wb_iso_offset_metadata_verified}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G62_ATOMOS_NINJA_FW_OR_METADATA_INVALID),
        errors,
    )


def validate_fx6_12gsdi_mmio_mask(
    *,
    fx3_has_physical_12gsdi_bnc: bool = FX3_HAS_PHYSICAL_12GSDI_BNC,
    sdi_mmio_probes_emitted: int = 0,
    sdi_driver_probes_masked: bool = True,
    fx6_12gsdi_raw_enabled: bool = False,
    hdmi_raw_pipeline_routed: bool = True,
    requested_sdi_mode: str = "MASKED_OFF",
) -> Tuple[bool, str, List[str]]:
    """Hard-mask FX6's non-existent `12G-SDI` BNC hardware MMIO/driver probes
    (`sdi_mmio_probes_emitted == 0`) and route RAW/Clean HDMI/TC to FX3 `7.02`
    native Type-A HDMI pipeline.
    """
    errors: List[str] = []
    sdi_mode_norm = requested_sdi_mode.strip().upper()
    forbidden_mode = sdi_mode_norm in FX6_FORBIDDEN_SDI_RAW_MODES
    ok = (
        (not fx3_has_physical_12gsdi_bnc)
        and int(sdi_mmio_probes_emitted) == 0
        and sdi_driver_probes_masked
        and (not fx6_12gsdi_raw_enabled)
        and hdmi_raw_pipeline_routed
        and (not forbidden_mode)
    )
    if not ok:
        errors.append(
            f"FX6 12G-SDI BNC MMIO probe mask violation: "
            f"has_bnc={fx3_has_physical_12gsdi_bnc}, sdi_mmio_probes={sdi_mmio_probes_emitted}, "
            f"probes_masked={sdi_driver_probes_masked}, sdi_raw_enabled={fx6_12gsdi_raw_enabled}, "
            f"hdmi_routed={hdmi_raw_pipeline_routed}, requested_sdi_mode={requested_sdi_mode!r}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G62_FX6_12GSDI_MMIO_PROBE_UNMASKED),
        errors,
    )


# ---------------------------------------------------------------------------
# 3. Core Guard Functions (`verify_emount_info3d_and_breathing_02cf0232_guard`,
#    `verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard`)
# ---------------------------------------------------------------------------


def verify_emount_info3d_and_breathing_02cf0232_guard(
    *,
    platform_name: str = PLATFORM_MIRA_CETUS2,
    info7_packet_valid: bool = True,
    info8_packet_valid: bool = True,
    info3d_packet_valid: bool = True,
    info8_drive_params_valid: bool = True,
    info3d_optical_profile_valid: bool = True,
    emount_serial_crc_ok: bool = True,
    emount_packet_channels_intact: bool = True,
    lens_id: int | str = DEFAULT_SAFE_SONY_EMOUNT_LENS_ID,
    bkid_hex: str = BKID_APP_MR_SETTING_LENS_COMP_BREATHING_HEX,
    breathing_compensation_enabled: bool = True,
    catalyst_breathing_metadata_write: bool = True,
    lens_id_whitelist_enforced: bool = True,
    bkid_02cf0232_passthrough_intact: bool = True,
    focus_map_enabled: bool = True,
    monitor_control_version: str = MONITOR_CONTROL_MIN_VERSION,
    focus_map_transport: str = "WIRED_USB",
    focus_map_readonly_telemetry: bool = True,
    focus_map_emmc_writes: int = 0,
    focus_map_cp_mutation_bytes: int = 0,
    p18_device_node: str = P18_DEVICE_NODE,
    p18_lensfile_path: str = P18_LENSFILE_PATH,
    p18_blkroset: int | bool = 1,
    p18_mount_flags: str = P18_REQUIRED_MOUNT_FLAG,
    p18_lensfile_sha256: str = DEFAULT_SYNTHETIC_LENSFILE_SHA256,
    lens_partition_writes: int = 0,
    cinealta_manual_lensfile_slot_write_requested: bool = False,
    cinealta_manual_lensfile_slot_write_blocked: bool = True,
    cpapp_stock_preserved: bool = True,
    guard_profile: str = "FX3_REALHW_G61_MIRA_CETUS2_EMOUNT_BREATHING_DEFAULT",
) -> EmountInfo3dBreathingGuardResult:
    """Verify Gate G61 (`MIRA_CETUS2` E-Mount `info7/info8/info3D` + `0x02cf0232`
    Breathing Guard + Focus Map RO + `p18:/lens/LENSFILE.BIN` `BLKROSET=1`) fail-closed.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        platform_name,
        bkid_hex,
        monitor_control_version,
        focus_map_transport,
        p18_device_node,
        p18_lensfile_path,
        p18_mount_flags,
        p18_lensfile_sha256,
        guard_profile,
    )
    bools = (
        info7_packet_valid,
        info8_packet_valid,
        info3d_packet_valid,
        info8_drive_params_valid,
        info3d_optical_profile_valid,
        emount_serial_crc_ok,
        emount_packet_channels_intact,
        breathing_compensation_enabled,
        catalyst_breathing_metadata_write,
        lens_id_whitelist_enforced,
        bkid_02cf0232_passthrough_intact,
        focus_map_enabled,
        focus_map_readonly_telemetry,
        cinealta_manual_lensfile_slot_write_requested,
        cinealta_manual_lensfile_slot_write_blocked,
        cpapp_stock_preserved,
    )
    lens_id_norm = _normalize_int_value(lens_id)
    bkid_norm = _normalize_int_value(bkid_hex)
    ro_p18 = _normalize_ro_flag(p18_blkroset)

    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and all(isinstance(b, bool) for b in bools)
        and (lens_id_norm is not None and 0 <= lens_id_norm <= 0xFFFF)
        and (bkid_norm is not None and bkid_norm >= 0)
        and _is_non_negative_int(focus_map_emmc_writes)
        and _is_non_negative_int(focus_map_cp_mutation_bytes)
        and (ro_p18 is not None)
        and _is_non_negative_int(lens_partition_writes)
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G61_TELEMETRY_INVALID)
        errors.append("Gate G61 received invalid or malformed E-Mount/Breathing telemetry.")

    packets_ok = False
    breathing_ok = False
    focus_map_ok = False
    p18_ok = False

    if telemetry_ok:
        packets_ok, pkt_code, pkt_errs = validate_emount_info7_8_3d_packets(
            platform_name=platform_name,
            info7_packet_valid=info7_packet_valid,
            info8_packet_valid=info8_packet_valid,
            info3d_packet_valid=info3d_packet_valid,
            info7_lens_id=lens_id_norm,
            info8_drive_params_valid=info8_drive_params_valid,
            info3d_optical_profile_valid=info3d_optical_profile_valid,
            emount_serial_crc_ok=emount_serial_crc_ok,
            emount_packet_channels_intact=emount_packet_channels_intact,
        )
        if not packets_ok:
            _add_code(codes, pkt_code)
            errors.extend(pkt_errs)

        breathing_ok, br_code, br_errs = validate_breathing_02cf0232_lens_filter(
            lens_id=lens_id_norm,
            bkid_hex=bkid_hex,
            breathing_compensation_enabled=breathing_compensation_enabled,
            catalyst_breathing_metadata_write=catalyst_breathing_metadata_write,
            lens_id_whitelist_enforced=lens_id_whitelist_enforced,
            bkid_02cf0232_passthrough_intact=bkid_02cf0232_passthrough_intact,
        )
        if not breathing_ok:
            _add_code(codes, br_code)
            errors.extend(br_errs)

        focus_map_ok, fm_code, fm_errs = validate_focus_map_readonly_telemetry(
            focus_map_enabled=focus_map_enabled,
            monitor_control_version=monitor_control_version,
            focus_map_transport=focus_map_transport,
            focus_map_readonly_telemetry=focus_map_readonly_telemetry,
            focus_map_emmc_writes=focus_map_emmc_writes,
            focus_map_cp_mutation_bytes=focus_map_cp_mutation_bytes,
        )
        if not focus_map_ok:
            _add_code(codes, fm_code)
            errors.extend(fm_errs)

        p18_ok, p18_code, p18_errs = validate_p18_lensfile_ro_and_cinealta_block(
            p18_device_node=p18_device_node,
            p18_lensfile_path=p18_lensfile_path,
            p18_blkroset=p18_blkroset,
            p18_mount_flags=p18_mount_flags,
            p18_lensfile_sha256=p18_lensfile_sha256,
            lens_partition_writes=lens_partition_writes,
            cinealta_manual_lensfile_slot_write_requested=cinealta_manual_lensfile_slot_write_requested,
            cinealta_manual_lensfile_slot_write_blocked=cinealta_manual_lensfile_slot_write_blocked,
            cpapp_stock_preserved=cpapp_stock_preserved,
        )
        if not p18_ok:
            _add_code(codes, p18_code)
            errors.extend(p18_errs)

    valid = (
        telemetry_ok
        and packets_ok
        and breathing_ok
        and focus_map_ok
        and p18_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G61 if valid else codes[0]
    first_party = (
        is_sony_first_party_breathing_lens(lens_id_norm)
        if lens_id_norm is not None
        else False
    )

    return EmountInfo3dBreathingGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        platform_name=str(platform_name) if isinstance(platform_name, str) else "INVALID",
        bkid_breathing_hex=f"0x{bkid_norm:08x}" if bkid_norm is not None else "INVALID",
        info7_packet_valid=bool(info7_packet_valid) if isinstance(info7_packet_valid, bool) else False,
        info8_packet_valid=bool(info8_packet_valid) if isinstance(info8_packet_valid, bool) else False,
        info3d_packet_valid=bool(info3d_packet_valid) if isinstance(info3d_packet_valid, bool) else False,
        emount_serial_packets_valid=packets_ok,
        lens_id=int(lens_id_norm) if lens_id_norm is not None else -1,
        lens_id_hex=f"0x{lens_id_norm:04x}" if lens_id_norm is not None and 0 <= lens_id_norm <= 0xFFFF else "INVALID",
        is_sony_first_party_lens=first_party,
        breathing_compensation_enabled=bool(breathing_compensation_enabled) if isinstance(breathing_compensation_enabled, bool) else False,
        catalyst_breathing_metadata_write=bool(catalyst_breathing_metadata_write) if isinstance(catalyst_breathing_metadata_write, bool) else False,
        lens_id_whitelist_enforced=bool(lens_id_whitelist_enforced) if isinstance(lens_id_whitelist_enforced, bool) else False,
        bkid_02cf0232_passthrough_intact=bool(bkid_02cf0232_passthrough_intact) if isinstance(bkid_02cf0232_passthrough_intact, bool) else False,
        breathing_guard_valid=breathing_ok,
        focus_map_enabled=bool(focus_map_enabled) if isinstance(focus_map_enabled, bool) else False,
        monitor_control_version=str(monitor_control_version) if isinstance(monitor_control_version, str) else "INVALID",
        monitor_control_min_version=MONITOR_CONTROL_MIN_VERSION,
        focus_map_transport=str(focus_map_transport) if isinstance(focus_map_transport, str) else "INVALID",
        focus_map_readonly_telemetry=bool(focus_map_readonly_telemetry) if isinstance(focus_map_readonly_telemetry, bool) else False,
        focus_map_emmc_writes=int(focus_map_emmc_writes) if _is_non_negative_int(focus_map_emmc_writes) else -1,
        focus_map_cp_mutation_bytes=int(focus_map_cp_mutation_bytes) if _is_non_negative_int(focus_map_cp_mutation_bytes) else -1,
        focus_map_guard_valid=focus_map_ok,
        p18_device_node=str(p18_device_node) if isinstance(p18_device_node, str) else "INVALID",
        p18_lensfile_path=str(p18_lensfile_path) if isinstance(p18_lensfile_path, str) else "INVALID",
        p18_blkroset=ro_p18 if ro_p18 is not None else -1,
        p18_mount_flags=str(p18_mount_flags) if isinstance(p18_mount_flags, str) else "INVALID",
        p18_lensfile_sha256=p18_lensfile_sha256.strip().lower() if isinstance(p18_lensfile_sha256, str) else "INVALID",
        lens_partition_writes=int(lens_partition_writes) if _is_non_negative_int(lens_partition_writes) else -1,
        cinealta_manual_lensfile_slot_write_requested=bool(cinealta_manual_lensfile_slot_write_requested) if isinstance(cinealta_manual_lensfile_slot_write_requested, bool) else True,
        cinealta_manual_lensfile_slot_write_blocked=bool(cinealta_manual_lensfile_slot_write_blocked) if isinstance(cinealta_manual_lensfile_slot_write_blocked, bool) else False,
        cpapp_stock_preserved=bool(cpapp_stock_preserved) if isinstance(cpapp_stock_preserved, bool) else False,
        p18_lensfile_guard_valid=p18_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(
    *,
    hdmi_connector_type: str = FX3_HDMI_CONNECTOR_TYPE,
    hdmi_raw_width: int = FX3_HDMI_RAW_WIDTH,
    hdmi_raw_height: int = FX3_HDMI_RAW_HEIGHT,
    hdmi_raw_aspect_ratio: str = FX3_HDMI_RAW_ASPECT_RATIO,
    hdmi_raw_bit_depth: int = FX3_HDMI_RAW_BIT_DEPTH,
    hdmi_raw_color_encoding: str = FX3_HDMI_RAW_COLOR_ENCODING,
    hdmi_raw_fps: float = 59.94,
    simultaneous_internal_codec: str = "XAVC_S_I",
    simultaneous_proxy_enabled: bool = True,
    recorder_mode: str = "BOTH",
    braw_recorder_model: str = "VIDEO_ASSIST_7_12G_HDR",
    braw_video_assist_fw: str = BRAW_MIN_VIDEO_ASSIST_FW,
    braw_sdk_version: str = BRAW_MIN_SDK_VERSION,
    resolve_version: str = RESOLVE_MIN_VERSION,
    braw_iso_capture_state_locked: bool = True,
    braw_private_sensor_profile_expected: bool = False,
    atomos_recorder_model: str = "NINJA_V_PLUS",
    atomos_fw_version: str = ATOMOS_MIN_FW_VERSION,
    prores_raw_wb_iso_offset_metadata_verified: bool = True,
    fx3_has_physical_12gsdi_bnc: bool = FX3_HAS_PHYSICAL_12GSDI_BNC,
    sdi_mmio_probes_emitted: int = 0,
    sdi_driver_probes_masked: bool = True,
    fx6_12gsdi_raw_enabled: bool = False,
    hdmi_raw_pipeline_routed: bool = True,
    requested_sdi_mode: str = "MASKED_OFF",
    guard_profile: str = "FX3_REALHW_G62_HDMI_4264X2408_RAW_VS_12GSDI_DEFAULT",
) -> Hdmi4264x2408RawVs12gSdiGuardResult:
    """Verify Gate G62 (`Type-A HDMI 4264x2408` 16-bit RAW `.braw` / `ProRes RAW`
    vs FX6 `12G-SDI` MMIO Mask Guard) fail-closed.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        hdmi_connector_type,
        hdmi_raw_aspect_ratio,
        hdmi_raw_color_encoding,
        simultaneous_internal_codec,
        recorder_mode,
        braw_recorder_model,
        braw_video_assist_fw,
        braw_sdk_version,
        resolve_version,
        atomos_recorder_model,
        atomos_fw_version,
        requested_sdi_mode,
        guard_profile,
    )
    bools = (
        simultaneous_proxy_enabled,
        braw_iso_capture_state_locked,
        braw_private_sensor_profile_expected,
        prores_raw_wb_iso_offset_metadata_verified,
        fx3_has_physical_12gsdi_bnc,
        sdi_driver_probes_masked,
        fx6_12gsdi_raw_enabled,
        hdmi_raw_pipeline_routed,
    )
    mode_ok = isinstance(recorder_mode, str) and (
        recorder_mode.strip().upper() in VALID_RECORDER_MODES
    )
    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and all(isinstance(b, bool) for b in bools)
        and mode_ok
        and _is_non_negative_int(hdmi_raw_width)
        and _is_non_negative_int(hdmi_raw_height)
        and _is_non_negative_int(hdmi_raw_bit_depth)
        and _is_finite_number(hdmi_raw_fps)
        and _is_non_negative_int(sdi_mmio_probes_emitted)
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G62_TELEMETRY_INVALID)
        errors.append("Gate G62 received invalid or malformed HDMI RAW / 12G-SDI telemetry.")

    raw_spec_ok = False
    braw_ok = False
    atomos_ok = False
    sdi_mask_ok = False

    if telemetry_ok:
        raw_spec_ok, raw_code, raw_errs = validate_hdmi_4264x2408_16bit_raw_spec(
            hdmi_connector_type=hdmi_connector_type,
            hdmi_raw_width=hdmi_raw_width,
            hdmi_raw_height=hdmi_raw_height,
            hdmi_raw_aspect_ratio=hdmi_raw_aspect_ratio,
            hdmi_raw_bit_depth=hdmi_raw_bit_depth,
            hdmi_raw_color_encoding=hdmi_raw_color_encoding,
            hdmi_raw_fps=float(hdmi_raw_fps),
            simultaneous_internal_codec=simultaneous_internal_codec,
            simultaneous_proxy_enabled=simultaneous_proxy_enabled,
        )
        if not raw_spec_ok:
            _add_code(codes, raw_code)
            errors.extend(raw_errs)

        braw_ok, braw_code, braw_errs = validate_braw_video_assist_12g_compat(
            recorder_mode=recorder_mode,
            braw_recorder_model=braw_recorder_model,
            braw_video_assist_fw=braw_video_assist_fw,
            braw_sdk_version=braw_sdk_version,
            resolve_version=resolve_version,
            braw_iso_capture_state_locked=braw_iso_capture_state_locked,
            braw_private_sensor_profile_expected=braw_private_sensor_profile_expected,
        )
        if not braw_ok:
            _add_code(codes, braw_code)
            errors.extend(braw_errs)

        atomos_ok, atomos_code, atomos_errs = validate_atomos_ninja_prores_raw_compat(
            recorder_mode=recorder_mode,
            atomos_recorder_model=atomos_recorder_model,
            atomos_fw_version=atomos_fw_version,
            resolve_version=resolve_version,
            prores_raw_wb_iso_offset_metadata_verified=prores_raw_wb_iso_offset_metadata_verified,
        )
        if not atomos_ok:
            _add_code(codes, atomos_code)
            errors.extend(atomos_errs)

        sdi_mask_ok, sdi_code, sdi_errs = validate_fx6_12gsdi_mmio_mask(
            fx3_has_physical_12gsdi_bnc=fx3_has_physical_12gsdi_bnc,
            sdi_mmio_probes_emitted=sdi_mmio_probes_emitted,
            sdi_driver_probes_masked=sdi_driver_probes_masked,
            fx6_12gsdi_raw_enabled=fx6_12gsdi_raw_enabled,
            hdmi_raw_pipeline_routed=hdmi_raw_pipeline_routed,
            requested_sdi_mode=requested_sdi_mode,
        )
        if not sdi_mask_ok:
            _add_code(codes, sdi_code)
            errors.extend(sdi_errs)

    valid = (
        telemetry_ok
        and raw_spec_ok
        and braw_ok
        and atomos_ok
        and sdi_mask_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G62 if valid else codes[0]

    return Hdmi4264x2408RawVs12gSdiGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        hdmi_connector_type=str(hdmi_connector_type) if isinstance(hdmi_connector_type, str) else "INVALID",
        hdmi_raw_width=int(hdmi_raw_width) if _is_non_negative_int(hdmi_raw_width) else -1,
        hdmi_raw_height=int(hdmi_raw_height) if _is_non_negative_int(hdmi_raw_height) else -1,
        hdmi_raw_aspect_ratio=str(hdmi_raw_aspect_ratio) if isinstance(hdmi_raw_aspect_ratio, str) else "INVALID",
        hdmi_raw_bit_depth=int(hdmi_raw_bit_depth) if _is_non_negative_int(hdmi_raw_bit_depth) else -1,
        hdmi_raw_color_encoding=str(hdmi_raw_color_encoding) if isinstance(hdmi_raw_color_encoding, str) else "INVALID",
        hdmi_raw_fps=float(hdmi_raw_fps) if _is_finite_number(hdmi_raw_fps) else -1.0,
        simultaneous_internal_codec=str(simultaneous_internal_codec) if isinstance(simultaneous_internal_codec, str) else "INVALID",
        simultaneous_proxy_enabled=bool(simultaneous_proxy_enabled) if isinstance(simultaneous_proxy_enabled, bool) else False,
        hdmi_raw_spec_valid=raw_spec_ok,
        recorder_mode=str(recorder_mode) if isinstance(recorder_mode, str) else "INVALID",
        braw_recorder_model=str(braw_recorder_model) if isinstance(braw_recorder_model, str) else "INVALID",
        braw_video_assist_fw=str(braw_video_assist_fw) if isinstance(braw_video_assist_fw, str) else "INVALID",
        braw_sdk_version=str(braw_sdk_version) if isinstance(braw_sdk_version, str) else "INVALID",
        resolve_version=str(resolve_version) if isinstance(resolve_version, str) else "INVALID",
        braw_iso_capture_state_locked=bool(braw_iso_capture_state_locked) if isinstance(braw_iso_capture_state_locked, bool) else False,
        braw_private_sensor_profile_expected=bool(braw_private_sensor_profile_expected) if isinstance(braw_private_sensor_profile_expected, bool) else True,
        braw_compat_valid=braw_ok,
        atomos_recorder_model=str(atomos_recorder_model) if isinstance(atomos_recorder_model, str) else "INVALID",
        atomos_fw_version=str(atomos_fw_version) if isinstance(atomos_fw_version, str) else "INVALID",
        prores_raw_wb_iso_offset_metadata_verified=bool(prores_raw_wb_iso_offset_metadata_verified) if isinstance(prores_raw_wb_iso_offset_metadata_verified, bool) else False,
        atomos_prores_compat_valid=atomos_ok,
        fx3_has_physical_12gsdi_bnc=bool(fx3_has_physical_12gsdi_bnc) if isinstance(fx3_has_physical_12gsdi_bnc, bool) else True,
        sdi_mmio_probes_emitted=int(sdi_mmio_probes_emitted) if _is_non_negative_int(sdi_mmio_probes_emitted) else -1,
        sdi_driver_probes_masked=bool(sdi_driver_probes_masked) if isinstance(sdi_driver_probes_masked, bool) else False,
        fx6_12gsdi_raw_enabled=bool(fx6_12gsdi_raw_enabled) if isinstance(fx6_12gsdi_raw_enabled, bool) else True,
        hdmi_raw_pipeline_routed=bool(hdmi_raw_pipeline_routed) if isinstance(hdmi_raw_pipeline_routed, bool) else False,
        sdi_mask_guard_valid=sdi_mask_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G61 & Gate G62 Evaluators (Donor Audit + Guard -> GateVerdict)
# ---------------------------------------------------------------------------


def evaluate_g61_emount_breathing_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    emount_breathing_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase181DonorAuditResult] = None,
) -> Tuple[GateVerdict, G61EmountBreathingResult]:
    """Evaluate Gate G61 (`MIRA_CETUS2` E-Mount `info7/info8/info3D` + `0x02cf0232`
    Breathing + Focus Map RO + `p18:/lens/LENSFILE.BIN` `BLKROSET=1` Guard).
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase181_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(emount_breathing_kwargs or {})
    if "p18_lensfile_sha256" not in guard_kwargs and "p18_lensfile" in audit.sha256_by_artifact:
        guard_kwargs["p18_lensfile_sha256"] = audit.sha256_by_artifact["p18_lensfile"]
    guard = verify_emount_info3d_and_breathing_02cf0232_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE181_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G61 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G61 if valid else codes[0]

    res = G61EmountBreathingResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        emount_breathing_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, platform={guard.platform_name}, "
        f"lens_id={guard.lens_id_hex}(first_party={guard.is_sony_first_party_lens}), "
        f"bkid={guard.bkid_breathing_hex}, mc_ver={guard.monitor_control_version}, "
        f"p18_blkroset={guard.p18_blkroset}, lens_writes={guard.lens_partition_writes}"
    )

    verdict = GateVerdict(
        gate_id=G61_GATE_ID,
        gate_code=G61_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


def evaluate_g62_hdmi_raw_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    hdmi_raw_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase181DonorAuditResult] = None,
) -> Tuple[GateVerdict, G62HdmiRawGuardResult]:
    """Evaluate Gate G62 (`Type-A HDMI 4264x2408` 16-bit RAW `.braw` / `ProRes RAW`
    vs FX6 `12G-SDI` Guard).
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase181_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(hdmi_raw_kwargs or {})
    guard = verify_hdmi_4264x2408_16bit_raw_vs_12gsdi_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE181_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G62 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G62 if valid else codes[0]

    res = G62HdmiRawGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        hdmi_raw_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, hdmi={guard.hdmi_raw_width}x{guard.hdmi_raw_height}"
        f"@{guard.hdmi_raw_fps}fps/{guard.hdmi_raw_bit_depth}b, "
        f"internal={guard.simultaneous_internal_codec}, "
        f"braw_fw={guard.braw_video_assist_fw}, atomos_fw={guard.atomos_fw_version}, "
        f"sdi_mmio_probes={guard.sdi_mmio_probes_emitted}"
    )

    verdict = GateVerdict(
        gate_id=G62_GATE_ID,
        gate_code=G62_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Unified 62-Gate Master Safety Preflight (`G01..G62`)
# ---------------------------------------------------------------------------


def evaluate_62gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G01..G60 pass-throughs
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
    # G61 inputs (MIRA_CETUS2 E-Mount info7/info8/info3D + 0x02cf0232 + Focus Map RO + p18 RO)
    emount_breathing_kwargs: Optional[Mapping[str, Any]] = None,
    # G62 inputs (Type-A HDMI 4264x2408 16-bit RAW .braw / ProRes RAW vs 12G-SDI mask)
    hdmi_raw_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master62GateReport:
    """Evaluate all 62 Master Safety Gates (`G01..G62`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        if dry_run_simulated_backup is None
        else (dry_run_simulated or dry_run_simulated_backup)
    )

    m60_kwargs: Dict[str, Any] = {
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
    }
    if soc_start_ceiling_c is not None:
        m60_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m60_report: Master60GateReport = evaluate_60gate_preflight(
        resolved_root, **m60_kwargs
    )

    phase181_audit = audit_phase181_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g61_verdict, g61_res = evaluate_g61_emount_breathing_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        emount_breathing_kwargs=emount_breathing_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase181_audit,
    )

    g62_verdict, g62_res = evaluate_g62_hdmi_raw_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        hdmi_raw_kwargs=hdmi_raw_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase181_audit,
    )

    gates_61_to_62 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g61_verdict, g62_verdict)
    ]
    all_gates = tuple(list(m60_report.gates) + gates_61_to_62)

    g01_to_g12_verified = int(m60_report.summary["g01_to_g12_verified"])
    g13_to_g60_verified = (
        int(m60_report.summary["g13_to_g58_verified"])
        + int(m60_report.summary["g59_to_g60_verified"])
    )
    g61_to_g62_verified = sum(1 for v in (g61_verdict, g62_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g60_verified + g61_to_g62_verified

    g61_to_g62_all_passed = g61_to_g62_verified == 2
    g13_to_g62_all_passed = (
        m60_report.g13_to_g60_all_passed and g61_to_g62_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m60_report.gates[:9])

    offline_59_verified = (
        g01_to_g09_ok
        and m60_report.offline_57_gates_verified
        and g61_to_g62_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_62_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g62_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes
    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m60_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_59_verified
        and m60_report.h0_h1_trial_entry_allowed
        and g61_to_g62_all_passed
        and agent_auto_flash_blocked
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m60_report.errors) + list(g61_verdict.errors) + list(g62_verdict.errors)
    )
    warnings: List[str] = (
        list(m60_report.warnings)
        + list(g61_verdict.warnings)
        + list(g62_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m60_report.g13_to_g60_all_passed:
        overall_status = m60_report.status
    elif not g61_verdict.passed:
        overall_status = g61_verdict.status
    elif not g62_verdict.passed:
        overall_status = g62_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_62_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_62_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_62_verified:
        overall_status = "VERIFIED_ALL_62_GATES"
    else:
        overall_status = "VERIFIED_59_OF_62_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m60_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g61_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g62_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 62,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 62 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g60_verified": g13_to_g60_verified,
        "g61_to_g62_verified": g61_to_g62_verified,
        "g13_to_g62_all_passed": g13_to_g62_all_passed,
        "g61_to_g62_all_passed": g61_to_g62_all_passed,
        "offline_59_gates_verified": offline_59_verified,
        "all_62_gates_verified": all_62_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master62GateReport(
        schema=REALHW_EMOUNT_INFO3D_HDMI_BRAW_62GATE_SCHEMA,
        version=REALHW_EMOUNT_INFO3D_HDMI_BRAW_62GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_59_gates_verified=offline_59_verified,
        all_62_gates_verified=all_62_verified,
        g13_to_g62_all_passed=g13_to_g62_all_passed,
        g61_to_g62_all_passed=g61_to_g62_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        summary=summary,
        gates=all_gates,
        master_60_report=m60_report.to_dict(),
        g61_result=g61_res.to_dict(),
        g62_result=g62_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_62_master_safety_gates = evaluate_62gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_emount_info3d_hdmi_braw_and_62gate_guard",
        description=(
            "Phase 181 — MIRA_CETUS2 E-Mount info7/info8/info3D & 0x02cf0232 Breathing "
            "Guard (G61), Type-A HDMI 4264x2408 16-bit RAW vs 12G-SDI Guard (G62), "
            "and 62-Gate Master Preflight (G01..G62)"
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G62 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_62gate_preflight(
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
            f"verified={report.summary['verified_gates']}/62 "
            f"g61_to_g62_all_passed={report.g61_to_g62_all_passed} "
            f"all_62_gates_verified={report.all_62_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
            f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
            f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
            f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        report.all_62_gates_verified
        if args.dry_run_simulated
        else report.offline_59_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
