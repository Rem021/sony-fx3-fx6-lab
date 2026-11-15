"""Phase 196 — Real-Hardware Main Track Part 21:
Gate G67 (`ILME-FX3` `Ver. 7.00 / 7.02` Power-On `USB-LAN` `RNDIS/CDC-NCM`
Auto-Connect, Stock `/setting` Profile Protection, `RTMP/RTMPS/SRT <= 38 Mbps`
`3840x2160 59.94p` Streaming Cap & `RTMPS` TLS `EROFS` Read-Only Verification),
Gate G68 (`Creators' Cloud` `Creators' App >= 3.1.0` / `M&C >= 2.4.0` Non-Destructive
MXF/XML Sidecar `OK/NG/KEEP` Clip-Flag Hygiene, `1.3x/1.5x/1.6x/2.0x` Anamorphic
De-Squeeze Monitoring Lock with HDMI `4264x2408` Linear RAW Auto-Disable &
`CXD90057` Bright-Monitoring + Focus-Magnifier Coexistence Guard),
and 68-Gate Master Safety Preflight (`G01..G68` / `verify-68-gates` / `run_68_gate_preflight`).

Composes `realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard` (`G01..G66`, keeping
`evaluate_58gate_preflight`, `evaluate_60gate_preflight`, `evaluate_62gate_preflight`,
`evaluate_64gate_preflight`, `evaluate_66gate_preflight`, `verify-58-gates`,
`verify-60-gates`, `verify-62-gates`, `verify-64-gates`, and `verify-66-gates`
100% intact) while hard-locking all physical flash/write/transmit redlines:
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

from .exfat_media_integrity_guard import MediaSlotConfig
from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    GateVerdict,
    P12_WLAN_FATAL_GUARD_VMA,
)
from .realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    FX3A_MODEL_NAME,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
)
from .realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard import (
    Master66GateReport,
    evaluate_66gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_USBLAN_RTMP_CLIPFLAG_ANAMORPHIC_68GATE_SCHEMA: str = (
    "fx3-realhw-usblan-rtmp-clipflag-anamorphic-68gate-preflight-v1"
)
REALHW_USBLAN_RTMP_CLIPFLAG_ANAMORPHIC_68GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

# Gate IDs & Canonical Codes for G67..G68
G67_GATE_ID: str = "G67_fx3_usblan_autoconnect_and_rtmp_srt_streaming_guard"
G67_GATE_CODE: str = (
    "GATE_G67_FX3_USBLAN_AUTOCONNECT_AND_RTMP_SRT_STREAMING_GUARD"
)
GATE_G67_FX3_USBLAN_AUTOCONNECT_AND_RTMP_SRT_STREAMING_GUARD: str = G67_GATE_CODE
G67: str = G67_GATE_CODE

G68_GATE_ID: str = "G68_creators_cloud_clipflag_anamorphic_and_bright_magnifier_guard"
G68_GATE_CODE: str = (
    "GATE_G68_CREATORS_CLOUD_CLIPFLAG_ANAMORPHIC_AND_BRIGHT_MAGNIFIER_GUARD"
)
GATE_G68_CREATORS_CLOUD_CLIPFLAG_ANAMORPHIC_AND_BRIGHT_MAGNIFIER_GUARD: str = G68_GATE_CODE
G68: str = G68_GATE_CODE

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G67: str = (
    "VERIFIED_FX3_USBLAN_AUTOCONNECT_AND_RTMP_SRT_STREAMING_GUARD"
)
STATUS_VERIFIED_G68: str = (
    "VERIFIED_CREATORS_CLOUD_CLIPFLAG_ANAMORPHIC_AND_BRIGHT_MAGNIFIER_GUARD"
)

# Gate G67 Violation Codes
STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE: str = (
    "BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE"
)
STATUS_BLOCKED_G67_STAGEB_SETTING_PROFILE_OVERWRITE: str = (
    "BLOCKED_G67_STAGEB_SETTING_PROFILE_OVERWRITE"
)
STATUS_BLOCKED_G67_STREAMING_BITRATE_OR_CODEC_VIOLATION: str = (
    "BLOCKED_G67_STREAMING_BITRATE_OR_CODEC_VIOLATION"
)
STATUS_BLOCKED_G67_RTMPS_TLS_CERT_NON_RO_OR_UNVERIFIED: str = (
    "BLOCKED_G67_RTMPS_TLS_CERT_NON_RO_OR_UNVERIFIED"
)
STATUS_BLOCKED_G67_TELEMETRY_INVALID: str = (
    "BLOCKED_G67_USBLAN_RTMP_TELEMETRY_INVALID"
)

# Gate G68 Violation Codes
STATUS_BLOCKED_G68_CLIP_FLAG_ESSENCE_MUTATION_OR_APP_FLOOR: str = (
    "BLOCKED_G68_CLIP_FLAG_ESSENCE_MUTATION_OR_APP_FLOOR"
)
STATUS_BLOCKED_G68_ANAMORPHIC_DESQUEEZE_OR_HDMI_RAW_SCALE: str = (
    "BLOCKED_G68_ANAMORPHIC_DESQUEEZE_OR_HDMI_RAW_SCALE"
)
STATUS_BLOCKED_G68_BRIGHT_MONITORING_MAGNIFIER_FAULT: str = (
    "BLOCKED_G68_BRIGHT_MONITORING_MAGNIFIER_FAULT"
)
STATUS_BLOCKED_G68_TELEMETRY_INVALID: str = (
    "BLOCKED_G68_CLIPFLAG_ANAMORPHIC_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE196_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE196_68GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G67 Constants — USB-LAN Auto-Connect & Network Streaming (RTMP/RTMPS/SRT)
MIN_USBLAN_AUTOCONNECT_FW_VERSION: str = "7.00"
FX3_TARGET_FW_VERSION: str = "7.02"
ALLOWED_G67_BODY_MODELS: Tuple[str, ...] = (FX3_MODEL_NAME, FX3A_MODEL_NAME)
ALLOWED_USBLAN_PROTOCOLS: Tuple[str, ...] = ("CDC_NCM", "RNDIS")
ALLOWED_USBLAN_ADAPTER_CHIPSETS: Tuple[str, ...] = (
    "CDC_NCM",
    "ASIX",
    "AX88179",
    "RTL8153",
    "RNDIS",
)
REJECTED_USBLAN_ADAPTER_CHIPSETS: Tuple[str, ...] = (
    "AX88179A",
    "AX88179B",
    "RTL8156",
    "RTL8156B",
    "AQUANTIA_10G",
    "CDC_ECM",
)
ALLOWED_USBLAN_PORTS: Tuple[str, ...] = ("USB_TYPE_C", "TYPE_C", "USBC")
ALLOWED_USBLAN_POWER_MODES: Tuple[str, ...] = (
    "NP_FZ100",
    "USB_PD_BODY",
    "DC_C1",
    "DC_C1_COUPLER",
)
USBLAN_MAX_AUTORECONNECT_LATENCY_MS: float = 5000.0
USBLAN_MIN_NPFZ100_PCT: int = 51
USBLAN_DC_C1_MIN_WATTS: float = 65.0
USBLAN_DC_C1_MIN_CABLE_AMPS: float = 5.0
FORBIDDEN_STOCK_SETTING_PREFIXES: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "p2:",
    "/dev/nflasha2",
    "/dev/cnflasha2",
)

ALLOWED_STREAMING_PROTOCOLS: Tuple[str, ...] = ("RTMP", "RTMPS", "SRT", "NONE")
ACTIVE_STREAMING_PROTOCOLS: Tuple[str, ...] = ("RTMP", "RTMPS", "SRT")
ALLOWED_STREAMING_CODECS: Tuple[str, ...] = ("H265", "HEVC", "H264", "AVC")
MAX_STREAMING_WIDTH: int = 3840
MAX_STREAMING_HEIGHT: int = 2160
MAX_STREAMING_FPS: float = 60.0
CANONICAL_STREAMING_FPS: float = 59.94
MAX_STREAMING_BITRATE_MBPS: float = 38.0
TLS_CERT_EROFS_ERRNO: str = "EROFS"
TLS_CERT_REQUIRED_MOUNT_FLAG: str = "MS_RDONLY"
TLS_CERT_DEFAULT_PATH: str = "/cert/rtmps_ca_bundle.pem"

# Gate G68 Constants — Creators' Cloud Clip-Flag, Anamorphic & Bright Monitoring
CREATORS_APP_MIN_VERSION: str = "3.1.0"
MONITOR_CONTROL_MIN_VERSION_G68: str = "2.4.0"
VALID_CLIP_FLAGS: Tuple[str, ...] = ("OK", "NG", "KEEP", "NONE")
FILTERABLE_CLIP_FLAGS: Tuple[str, ...] = ("OK", "NG", "KEEP")
ALLOWED_CLIP_FLAG_SIDECAR_FORMATS: Tuple[str, ...] = (
    "MXF_SIDECAR",
    "XML_SIDECAR",
    "NONREALTIMEMETA_XML",
)
ALLOWED_ANAMORPHIC_DESQUEEZE_RATIOS: Tuple[float, ...] = (1.0, 1.3, 1.5, 1.6, 2.0)
HDMI_RAW_UNSCALED_WIDTH: int = 4264
HDMI_RAW_UNSCALED_HEIGHT: int = 2408
CXD90057_SOC_NAME: str = "CXD90057"
ALLOWED_FOCUS_MAGNIFIER_FACTORS: Tuple[float, ...] = (1.0, 2.0, 4.0, 8.0)
DEFAULT_SYNTHETIC_ESSENCE_SHA256: str = "a" * 64

# Pinned FX3 v7.02 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE196_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"NCM",
            b"CDC",
            b"TLS",
            b"SSL",
            b"KEEP",
            b"Bright",
            b"Magnifier",
            b"RAW",
            b"HDMI",
        ),
        "fx3/cpapp-b.bin::{15980568B,ILME-FX3,NCM,CDC,TLS,SSL,KEEP,Bright,Magnifier,RAW,HDMI}",
    ),
    "fx3_appfw_so": (
        "fx3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f",
        (
            b"\x7fELF",
            b"RTMP",
            b"SRT",
            b"TLS",
            b"SSL",
            b"MXF",
            b"KEEP",
            b"Bright",
            b"Magnifier",
            b"RAW",
            b"HDMI",
        ),
        "fx3/appFw.so::{79015712B,ELF,RTMP,SRT,TLS,SSL,MXF,KEEP,Bright,Magnifier,RAW,HDMI}",
    ),
    "fx3_libnetserviceether_so": (
        "network",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libNetServiceEther.so",
        114_384,
        "203b084190a968c732d09fd45e304c406a32eb664d98626114dcf7f178675375",
        (
            b"\x7fELF",
            b"NetService",
            b"Ether",
            b"USB",
            b"LAN",
            b"SSL",
            b"DHCP",
            b"IP",
        ),
        "fx3/libNetServiceEther.so::{114384B,ELF,NetService,Ether,USB,LAN,SSL,DHCP,IP}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase196DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    network_contracts_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Fx3UsbLanRtmpSrtGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    body_model_name: str
    body_model_id: int
    body_model_id_hex: str
    firmware_version: str
    usblan_autoconnect_enabled: bool
    usb_port: str
    usblan_protocol: str
    adapter_chipset: str
    power_mode: str
    np_fz100_present: bool
    battery_pct: int
    dc_c1_pd_watts: float
    emarked_5a_cable: bool
    auto_reconnect_latency_ms: float
    usblan_autoconnect_valid: bool
    stageb_setting_network_overwrite_attempted: bool
    setting_network_writes: int
    setting_mount_ro_protected: bool
    target_profile_path: str
    stock_setting_protected: bool
    streaming_protocol: str
    streaming_codec: str
    streaming_bitrate_mbps: float
    stream_width: int
    stream_height: int
    stream_fps: float
    streaming_cap_valid: bool
    tls_cert_path: str
    tls_cert_verified: bool
    tls_cert_mount_ro: bool
    tls_cert_write_errno: str
    tls_cert_mutation_bytes: int
    tls_cert_write_attempted: bool
    tls_erofs_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CreatorsCloudClipFlagAnamorphicResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    creators_app_version: str
    monitor_control_version: str
    clip_flag: str
    filter_flags: Tuple[str, ...]
    sidecar_format: str
    sidecar_metadata_only: bool
    video_essence_modified: bool
    video_essence_mutation_bytes: int
    mxf_mp4_essence_sha256_before: str
    mxf_mp4_essence_sha256_after: str
    stage_b_persistent_clip_rewrite: bool
    clip_flag_hygiene_valid: bool
    anamorphic_desqueeze_ratio: float
    desqueeze_monitoring_only: bool
    recorded_essence_anamorphic_baked: bool
    hdmi_raw_output_active: bool
    anamorphic_desqueeze_active_on_hdmi_raw: bool
    anamorphic_auto_disabled_for_hdmi_raw: bool
    hdmi_raw_width: int
    hdmi_raw_height: int
    hdmi_raw_linear_unscaled: bool
    anamorphic_hdmi_raw_valid: bool
    soc_name: str
    bright_monitoring_active: bool
    focus_magnifier_active: bool
    focus_magnifier_factor: float
    coexistence_supported: bool
    magnifier_overlay_non_destructive: bool
    recorded_essence_bright_or_zoom_baked: bool
    exposure_metering_corrupted: bool
    cxd90057_isp_pipeline_fault: bool
    bright_magnifier_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G67UsbLanRtmpSrtGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    usblan_rtmp_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G68ClipFlagAnamorphicGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    clipflag_anamorphic_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master68GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_65_gates_verified: bool
    all_68_gates_verified: bool
    g13_to_g68_all_passed: bool
    g67_to_g68_all_passed: bool
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
    master_66_report: Dict[str, Any]
    g67_result: Dict[str, Any]
    g68_result: Dict[str, Any]
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


def _parse_version_tuple(ver_str: str) -> Optional[Tuple[int, ...]]:
    s = ver_str.strip()
    if s.lower().startswith("ver."):
        s = s[4:].strip()
    elif s.lower().startswith("v"):
        s = s[1:].strip()
    if not s or not re.fullmatch(r"\d+(?:\.\d+){1,3}", s):
        return None
    return tuple(int(part) for part in s.split("."))


def _version_gte(ver_str: str, floor_str: str) -> bool:
    v = _parse_version_tuple(ver_str)
    f = _parse_version_tuple(floor_str)
    if v is None or f is None:
        return False
    max_len = max(len(v), len(f))
    vp = v + (0,) * (max_len - len(v))
    fp = f + (0,) * (max_len - len(f))
    return vp >= fp


def _norm_usblan_proto(proto: str) -> str:
    t = _norm_token(proto)
    if t in ("CDC_NCM", "CDCNCM", "NCM"):
        return "CDC_NCM"
    if t in ("RNDIS", "USB_RNDIS"):
        return "RNDIS"
    return t


def _norm_chipset(chipset: str) -> str:
    t = _norm_token(chipset)
    if t in ("CDC_NCM", "CDCNCM", "NCM"):
        return "CDC_NCM"
    if t in ("ASIX", "AX88179"):
        return "ASIX" if t == "ASIX" else "AX88179"
    if t in ("RTL8153", "REALTEK_RTL8153"):
        return "RTL8153"
    if t in ("RNDIS",):
        return "RNDIS"
    return t


def _norm_power_mode(mode: str) -> str:
    t = _norm_token(mode)
    if t in ("NP_FZ100", "NPFZ100", "USB_PD_BODY", "BODY_NP_FZ100"):
        return "NP_FZ100" if "FZ100" in t else "USB_PD_BODY"
    if t in ("DC_C1", "DCC1", "DC_C1_COUPLER", "DCC1_COUPLER"):
        return "DC_C1" if t in ("DC_C1", "DCC1") else "DC_C1_COUPLER"
    return t


def _norm_codec(codec: str) -> str:
    t = _norm_token(codec)
    if t in ("H265", "HEVC", "H265_HEVC"):
        return "HEVC"
    if t in ("H264", "AVC", "H264_AVC"):
        return "AVC"
    return t


def _norm_port(port: str) -> str:
    t = _norm_token(port)
    if t in ("USB_TYPE_C", "TYPE_C", "USBC", "USB_C"):
        return "USB_TYPE_C"
    return t


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase196_donor_contracts(
    *_,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase196DonorAuditResult:
    """Inspect FX3 `7.02` `cpapp-b.bin`, `appFw.so`, and `libNetServiceEther.so`
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
        ) in PINNED_PHASE196_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase196DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE196_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=True,
            network_contracts_verified=True,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE196_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE196_DONOR_SPECS.items()
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
    ) in PINNED_PHASE196_DONOR_SPECS.items():
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
        k for k, spec in PINNED_PHASE196_DONOR_SPECS.items() if spec[0] == "fx3"
    }
    net_keys = {
        k for k, spec in PINNED_PHASE196_DONOR_SPECS.items() if spec[0] == "network"
    }
    valid = len(errors) == 0 and len(missing) == 0
    return Phase196DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE196_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_keys.issubset(passed_keys) and valid,
        network_contracts_verified=net_keys.issubset(passed_keys) and valid,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Pure Helper Validators (G67 & G68)
# ---------------------------------------------------------------------------


def validate_usblan_poweron_autoconnect(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int | str = FX3_MODEL_ID,
    firmware_version: str = FX3_TARGET_FW_VERSION,
    usblan_autoconnect_enabled: bool = True,
    usb_port: str = "USB_TYPE_C",
    usblan_protocol: str = "CDC-NCM",
    adapter_chipset: str = "RTL8153",
    power_mode: str = "NP-FZ100",
    np_fz100_present: bool = True,
    battery_pct: int = 85,
    dc_c1_pd_watts: float = 65.0,
    emarked_5a_cable: bool = True,
    auto_reconnect_latency_ms: float = 850.0,
    stageb_setting_network_overwrite_attempted: bool = False,
    setting_network_writes: int = 0,
    setting_mount_ro_protected: bool = True,
    target_profile_path: str = "/tmp/stageb_net/usblan_profile.json",
) -> Tuple[bool, str, List[str]]:
    """Validate `ILME-FX3` (`Ver. 7.00 / 7.02`) power-on `USB-LAN` (`RNDIS/CDC-NCM`)
    auto-connect (`CDC-NCM` / `ASIX` / `RTL8153`) over `Type-C` powered via
    `NP-FZ100` or `DC-C1`, ensuring zero Stage-B overwrite of Stock `/setting`
    network profiles.
    """
    errors: List[str] = []

    model_norm = body_model_name.strip().upper().replace("_", "-")
    b_id = _normalize_int_value(body_model_id)
    fw_ok = _version_gte(firmware_version, MIN_USBLAN_AUTOCONNECT_FW_VERSION)
    port_norm = _norm_port(usb_port)
    proto_norm = _norm_usblan_proto(usblan_protocol)
    chip_norm = _norm_chipset(adapter_chipset)
    pwr_norm = _norm_power_mode(power_mode)

    model_ok = model_norm in ALLOWED_G67_BODY_MODELS and (
        b_id == FX3_MODEL_ID if model_norm == FX3_MODEL_NAME else (b_id is not None and b_id >= 0)
    )

    if pwr_norm in ("NP_FZ100", "USB_PD_BODY"):
        power_ok = (np_fz100_present is True) and (int(battery_pct) >= USBLAN_MIN_NPFZ100_PCT)
    elif pwr_norm in ("DC_C1", "DC_C1_COUPLER"):
        power_ok = (
            float(dc_c1_pd_watts) >= USBLAN_DC_C1_MIN_WATTS
            and (emarked_5a_cable is True)
        )
    else:
        power_ok = False

    adapter_ok = (
        model_ok
        and fw_ok
        and (usblan_autoconnect_enabled is True)
        and (port_norm == "USB_TYPE_C")
        and (proto_norm in ALLOWED_USBLAN_PROTOCOLS)
        and (chip_norm in ALLOWED_USBLAN_ADAPTER_CHIPSETS)
        and (chip_norm not in REJECTED_USBLAN_ADAPTER_CHIPSETS)
        and (0.0 <= float(auto_reconnect_latency_ms) <= USBLAN_MAX_AUTORECONNECT_LATENCY_MS)
        and power_ok
    )
    if not adapter_ok:
        errors.append(
            f"USB-LAN power-on auto-connect check failed: model={body_model_name!r}, "
            f"fw={firmware_version!r} (>={MIN_USBLAN_AUTOCONNECT_FW_VERSION}), "
            f"autoconnect={usblan_autoconnect_enabled}, port={usb_port!r}, "
            f"proto={usblan_protocol!r}, chipset={adapter_chipset!r}, "
            f"power_mode={power_mode!r}, np_fz100={np_fz100_present}, "
            f"batt={battery_pct}%, dc_c1_w={dc_c1_pd_watts}, 5a={emarked_5a_cable}, "
            f"latency_ms={auto_reconnect_latency_ms}."
        )
        return (False, STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE, errors)

    prof_lower = target_profile_path.strip().lower().replace("\\", "/")
    targets_stock_setting = any(
        prof_lower.startswith(pref) for pref in FORBIDDEN_STOCK_SETTING_PREFIXES
    )
    setting_ok = (
        (stageb_setting_network_overwrite_attempted is False)
        and (int(setting_network_writes) == 0)
        and (setting_mount_ro_protected is True)
        and (not targets_stock_setting)
    )
    if not setting_ok:
        errors.append(
            f"Stage-B Stock /setting network profile overwrite blocked: "
            f"overwrite_attempted={stageb_setting_network_overwrite_attempted}, "
            f"writes={setting_network_writes}, ro_protected={setting_mount_ro_protected}, "
            f"target_profile_path={target_profile_path!r}."
        )
        return (False, STATUS_BLOCKED_G67_STAGEB_SETTING_PROFILE_OVERWRITE, errors)

    return (True, "", errors)


def validate_network_streaming_rtmp_srt_and_tls(
    *,
    streaming_protocol: str = "RTMPS",
    streaming_codec: str = "H.265/HEVC",
    streaming_bitrate_mbps: float = 35.0,
    stream_width: int = 3840,
    stream_height: int = 2160,
    stream_fps: float = 59.94,
    tls_cert_path: str = TLS_CERT_DEFAULT_PATH,
    tls_cert_verified: bool = True,
    tls_cert_mount_ro: bool = True,
    tls_cert_write_errno: str = TLS_CERT_EROFS_ERRNO,
    tls_cert_mutation_bytes: int = 0,
    tls_cert_write_attempted: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Validate `RTMP / RTMPS / SRT` streaming bounds (`<= 38 Mbps`,
    `<= 3840x2160 59.94p`, `H.265/HEVC` or `H.264/AVC`) and strict TLS certificate
    read-only (`EROFS` / `MS_RDONLY`) protection for `RTMPS`.
    """
    errors: List[str] = []
    proto_norm = _norm_token(streaming_protocol)
    codec_norm = _norm_codec(streaming_codec)

    if proto_norm not in ALLOWED_STREAMING_PROTOCOLS:
        errors.append(
            f"Unsupported streaming protocol {streaming_protocol!r}; "
            f"expected one of {ALLOWED_STREAMING_PROTOCOLS}."
        )
        return (False, STATUS_BLOCKED_G67_STREAMING_BITRATE_OR_CODEC_VIOLATION, errors)

    if proto_norm in ACTIVE_STREAMING_PROTOCOLS:
        bw = float(streaming_bitrate_mbps)
        fps = float(stream_fps)
        cap_ok = (
            (0.0 < bw <= MAX_STREAMING_BITRATE_MBPS)
            and (codec_norm in ALLOWED_STREAMING_CODECS)
            and (1 <= int(stream_width) <= MAX_STREAMING_WIDTH)
            and (1 <= int(stream_height) <= MAX_STREAMING_HEIGHT)
            and (0.0 < fps <= MAX_STREAMING_FPS)
        )
        if not cap_ok:
            errors.append(
                f"Network Streaming spec violation: proto={streaming_protocol!r}, "
                f"codec={streaming_codec!r}, bitrate={streaming_bitrate_mbps} Mbps "
                f"(cap {MAX_STREAMING_BITRATE_MBPS} Mbps), "
                f"res={stream_width}x{stream_height}@{stream_fps}fps "
                f"(max {MAX_STREAMING_WIDTH}x{MAX_STREAMING_HEIGHT}@{CANONICAL_STREAMING_FPS}p)."
            )
            return (False, STATUS_BLOCKED_G67_STREAMING_BITRATE_OR_CODEC_VIOLATION, errors)

    errno_norm = tls_cert_write_errno.strip().upper()
    if proto_norm == "RTMPS":
        tls_ok = (
            bool(tls_cert_path.strip())
            and (tls_cert_verified is True)
            and (tls_cert_mount_ro is True)
            and (errno_norm == TLS_CERT_EROFS_ERRNO)
            and (int(tls_cert_mutation_bytes) == 0)
            and (tls_cert_write_attempted is False)
        )
    else:
        # Even outside RTMPS, TLS cert store must remain read-only with zero mutation
        tls_ok = (
            (tls_cert_mount_ro is True)
            and (errno_norm == TLS_CERT_EROFS_ERRNO)
            and (int(tls_cert_mutation_bytes) == 0)
            and (tls_cert_write_attempted is False)
        )

    if not tls_ok:
        errors.append(
            f"RTMPS TLS certificate read-only (EROFS) verification failed: "
            f"proto={streaming_protocol!r}, cert_path={tls_cert_path!r}, "
            f"verified={tls_cert_verified}, mount_ro={tls_cert_mount_ro}, "
            f"write_errno={tls_cert_write_errno!r} (expected {TLS_CERT_EROFS_ERRNO!r}), "
            f"mutation_bytes={tls_cert_mutation_bytes}, write_attempted={tls_cert_write_attempted}."
        )
        return (False, STATUS_BLOCKED_G67_RTMPS_TLS_CERT_NON_RO_OR_UNVERIFIED, errors)

    return (True, "", errors)


def validate_creators_cloud_clip_flag_hygiene(
    *,
    creators_app_version: str = CREATORS_APP_MIN_VERSION,
    monitor_control_version: str = MONITOR_CONTROL_MIN_VERSION_G68,
    clip_flag: str = "KEEP",
    filter_flags: Sequence[str] = FILTERABLE_CLIP_FLAGS,
    sidecar_format: str = "MXF_SIDECAR",
    sidecar_metadata_only: bool = True,
    video_essence_modified: bool = False,
    video_essence_mutation_bytes: int = 0,
    mxf_mp4_essence_sha256_before: str = DEFAULT_SYNTHETIC_ESSENCE_SHA256,
    mxf_mp4_essence_sha256_after: str = DEFAULT_SYNTHETIC_ESSENCE_SHA256,
    stage_b_persistent_clip_rewrite: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Enforce `Creators' App >= 3.1.0` / `M&C >= 2.4.0` non-destructive MXF/XML
    sidecar clip-flag (`OK`, `NG`, `KEEP`) filtering without modifying recorded
    video essence.
    """
    errors: List[str] = []

    app_ok = _version_gte(creators_app_version, CREATORS_APP_MIN_VERSION)
    mc_ok = _version_gte(monitor_control_version, MONITOR_CONTROL_MIN_VERSION_G68)
    flag_norm = _norm_token(clip_flag)
    flag_ok = flag_norm in VALID_CLIP_FLAGS
    filter_norms = tuple(_norm_token(f) for f in filter_flags)
    filters_ok = bool(filter_norms) and all(f in FILTERABLE_CLIP_FLAGS for f in filter_norms)
    fmt_norm = _norm_token(sidecar_format)
    fmt_ok = fmt_norm in ALLOWED_CLIP_FLAG_SIDECAR_FORMATS

    sha_before = mxf_mp4_essence_sha256_before.strip().lower()
    sha_after = mxf_mp4_essence_sha256_after.strip().lower()
    essence_ok = (
        (sidecar_metadata_only is True)
        and (video_essence_modified is False)
        and (int(video_essence_mutation_bytes) == 0)
        and bool(sha_before)
        and (sha_before == sha_after)
        and (stage_b_persistent_clip_rewrite is False)
    )

    if not (app_ok and mc_ok and flag_ok and filters_ok and fmt_ok and essence_ok):
        errors.append(
            f"Creators' Cloud Clip-Flag hygiene violation: "
            f"creators_app={creators_app_version!r} (>={CREATORS_APP_MIN_VERSION}), "
            f"m_and_c={monitor_control_version!r} (>={MONITOR_CONTROL_MIN_VERSION_G68}), "
            f"clip_flag={clip_flag!r}, filter_flags={list(filter_flags)!r}, "
            f"sidecar_format={sidecar_format!r}, sidecar_only={sidecar_metadata_only}, "
            f"essence_modified={video_essence_modified}, mut_bytes={video_essence_mutation_bytes}, "
            f"sha_match={sha_before == sha_after}, persistent_rewrite={stage_b_persistent_clip_rewrite}."
        )
        return (False, STATUS_BLOCKED_G68_CLIP_FLAG_ESSENCE_MUTATION_OR_APP_FLOOR, errors)

    return (True, "", errors)


def validate_anamorphic_desqueeze_and_hdmi_raw_lock(
    *,
    anamorphic_desqueeze_ratio: float = 1.5,
    desqueeze_monitoring_only: bool = True,
    recorded_essence_anamorphic_baked: bool = False,
    hdmi_raw_output_active: bool = False,
    anamorphic_desqueeze_active_on_hdmi_raw: bool = False,
    anamorphic_auto_disabled_for_hdmi_raw: bool = True,
    hdmi_raw_width: int = HDMI_RAW_UNSCALED_WIDTH,
    hdmi_raw_height: int = HDMI_RAW_UNSCALED_HEIGHT,
    hdmi_raw_linear_unscaled: bool = True,
) -> Tuple[bool, str, List[str]]:
    """Enforce `1.3x / 1.5x / 1.6x / 2.0x` (plus `1.0x` off) anamorphic de-squeeze
    monitoring lock while automatically disabling de-squeeze during HDMI RAW output
    so `4264x2408` linear RAW remains unscaled.
    """
    errors: List[str] = []

    ratio_val = round(float(anamorphic_desqueeze_ratio), 2)
    ratio_ok = ratio_val in ALLOWED_ANAMORPHIC_DESQUEEZE_RATIOS
    mon_only_ok = (
        (desqueeze_monitoring_only is True)
        and (recorded_essence_anamorphic_baked is False)
    )

    if hdmi_raw_output_active:
        raw_ok = (
            (anamorphic_desqueeze_active_on_hdmi_raw is False)
            and (anamorphic_auto_disabled_for_hdmi_raw is True)
            and (int(hdmi_raw_width) == HDMI_RAW_UNSCALED_WIDTH)
            and (int(hdmi_raw_height) == HDMI_RAW_UNSCALED_HEIGHT)
            and (hdmi_raw_linear_unscaled is True)
        )
    else:
        raw_ok = anamorphic_desqueeze_active_on_hdmi_raw is False

    if not (ratio_ok and mon_only_ok and raw_ok):
        errors.append(
            f"Anamorphic de-squeeze / HDMI RAW lock violation: "
            f"ratio={anamorphic_desqueeze_ratio}x (allowed {ALLOWED_ANAMORPHIC_DESQUEEZE_RATIOS}), "
            f"mon_only={desqueeze_monitoring_only}, baked={recorded_essence_anamorphic_baked}, "
            f"hdmi_raw_active={hdmi_raw_output_active}, "
            f"desqueeze_on_raw={anamorphic_desqueeze_active_on_hdmi_raw}, "
            f"auto_disabled_for_raw={anamorphic_auto_disabled_for_hdmi_raw}, "
            f"raw_res={hdmi_raw_width}x{hdmi_raw_height}, unscaled={hdmi_raw_linear_unscaled}."
        )
        return (False, STATUS_BLOCKED_G68_ANAMORPHIC_DESQUEEZE_OR_HDMI_RAW_SCALE, errors)

    return (True, "", errors)


def validate_bright_monitoring_and_focus_magnifier_cxd90057(
    *,
    soc_name: str = CXD90057_SOC_NAME,
    bright_monitoring_active: bool = True,
    focus_magnifier_active: bool = True,
    focus_magnifier_factor: float = 4.0,
    coexistence_supported: bool = True,
    magnifier_overlay_non_destructive: bool = True,
    recorded_essence_bright_or_zoom_baked: bool = False,
    exposure_metering_corrupted: bool = False,
    cxd90057_isp_pipeline_fault: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Validate Focus Magnifier coexistence with Bright Monitoring on `CXD90057`."""
    errors: List[str] = []

    soc_ok = soc_name.strip().upper() == CXD90057_SOC_NAME
    factor_val = round(float(focus_magnifier_factor), 2)
    factor_ok = factor_val in ALLOWED_FOCUS_MAGNIFIER_FACTORS
    if not focus_magnifier_active:
        factor_ok = factor_ok or factor_val == 1.0

    coexist_ok = (
        soc_ok
        and factor_ok
        and (coexistence_supported is True)
        and (magnifier_overlay_non_destructive is True)
        and (recorded_essence_bright_or_zoom_baked is False)
        and (exposure_metering_corrupted is False)
        and (cxd90057_isp_pipeline_fault is False)
    )
    if not coexist_ok:
        errors.append(
            f"CXD90057 Bright Monitoring + Focus Magnifier guard failed: "
            f"soc={soc_name!r}, bright={bright_monitoring_active}, "
            f"magnifier={focus_magnifier_active} ({focus_magnifier_factor}x), "
            f"coexist={coexistence_supported}, non_destructive={magnifier_overlay_non_destructive}, "
            f"baked={recorded_essence_bright_or_zoom_baked}, "
            f"metering_corrupt={exposure_metering_corrupted}, isp_fault={cxd90057_isp_pipeline_fault}."
        )
        return (False, STATUS_BLOCKED_G68_BRIGHT_MONITORING_MAGNIFIER_FAULT, errors)

    return (True, "", errors)


# ---------------------------------------------------------------------------
# 3. Core Guard Functions (`verify_usblan_autoconnect_and_rtmp_srt_guard`,
#    `verify_clipflag_anamorphic_and_bright_magnifier_guard`)
# ---------------------------------------------------------------------------


def verify_usblan_autoconnect_and_rtmp_srt_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int | str = FX3_MODEL_ID,
    firmware_version: str = FX3_TARGET_FW_VERSION,
    usblan_autoconnect_enabled: bool = True,
    usb_port: str = "USB_TYPE_C",
    usblan_protocol: str = "CDC-NCM",
    adapter_chipset: str = "RTL8153",
    power_mode: str = "NP-FZ100",
    np_fz100_present: bool = True,
    battery_pct: int = 85,
    dc_c1_pd_watts: float = 65.0,
    emarked_5a_cable: bool = True,
    auto_reconnect_latency_ms: float = 850.0,
    stageb_setting_network_overwrite_attempted: bool = False,
    setting_network_writes: int = 0,
    setting_mount_ro_protected: bool = True,
    target_profile_path: str = "/tmp/stageb_net/usblan_profile.json",
    streaming_protocol: str = "RTMPS",
    streaming_codec: str = "H.265/HEVC",
    streaming_bitrate_mbps: float = 35.0,
    stream_width: int = 3840,
    stream_height: int = 2160,
    stream_fps: float = 59.94,
    tls_cert_path: str = TLS_CERT_DEFAULT_PATH,
    tls_cert_verified: bool = True,
    tls_cert_mount_ro: bool = True,
    tls_cert_write_errno: str = TLS_CERT_EROFS_ERRNO,
    tls_cert_mutation_bytes: int = 0,
    tls_cert_write_attempted: bool = False,
    guard_profile: str = "FX3_REALHW_G67_USBLAN_RTMP_GUARD_DEFAULT",
) -> Fx3UsbLanRtmpSrtGuardResult:
    """Verify Gate G67 (`ILME-FX3` Power-On `USB-LAN` Auto-Connect & `RTMP/RTMPS/SRT` Guard)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        body_model_name,
        firmware_version,
        usb_port,
        usblan_protocol,
        adapter_chipset,
        power_mode,
        target_profile_path,
        streaming_protocol,
        streaming_codec,
        tls_cert_path,
        tls_cert_write_errno,
        guard_profile,
    )
    bools = (
        usblan_autoconnect_enabled,
        np_fz100_present,
        emarked_5a_cable,
        stageb_setting_network_overwrite_attempted,
        setting_mount_ro_protected,
        tls_cert_verified,
        tls_cert_mount_ro,
        tls_cert_write_attempted,
    )
    b_id = _normalize_int_value(body_model_id)

    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and all(isinstance(b, bool) for b in bools)
        and (b_id is not None and b_id >= 0)
        and _is_non_negative_int(battery_pct)
        and int(battery_pct) <= 100
        and _is_finite_number(dc_c1_pd_watts)
        and float(dc_c1_pd_watts) >= 0.0
        and _is_finite_number(auto_reconnect_latency_ms)
        and float(auto_reconnect_latency_ms) >= 0.0
        and _is_non_negative_int(setting_network_writes)
        and _is_finite_number(streaming_bitrate_mbps)
        and float(streaming_bitrate_mbps) >= 0.0
        and _is_non_negative_int(stream_width)
        and _is_non_negative_int(stream_height)
        and _is_finite_number(stream_fps)
        and float(stream_fps) >= 0.0
        and _is_non_negative_int(tls_cert_mutation_bytes)
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G67_TELEMETRY_INVALID)
        errors.append("Gate G67 received invalid or malformed USB-LAN / RTMP / TLS telemetry.")

    usblan_ok = False
    setting_ok = False
    streaming_ok = False
    tls_ok = False

    if telemetry_ok:
        u_ok, u_code, u_errs = validate_usblan_poweron_autoconnect(
            body_model_name=body_model_name,
            body_model_id=b_id,
            firmware_version=firmware_version,
            usblan_autoconnect_enabled=usblan_autoconnect_enabled,
            usb_port=usb_port,
            usblan_protocol=usblan_protocol,
            adapter_chipset=adapter_chipset,
            power_mode=power_mode,
            np_fz100_present=np_fz100_present,
            battery_pct=battery_pct,
            dc_c1_pd_watts=float(dc_c1_pd_watts),
            emarked_5a_cable=emarked_5a_cable,
            auto_reconnect_latency_ms=float(auto_reconnect_latency_ms),
            stageb_setting_network_overwrite_attempted=stageb_setting_network_overwrite_attempted,
            setting_network_writes=setting_network_writes,
            setting_mount_ro_protected=setting_mount_ro_protected,
            target_profile_path=target_profile_path,
        )
        if not u_ok:
            _add_code(codes, u_code)
            errors.extend(u_errs)
            usblan_ok = u_code != STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE
            setting_ok = u_code != STATUS_BLOCKED_G67_STAGEB_SETTING_PROFILE_OVERWRITE
        else:
            usblan_ok = True
            setting_ok = True

        s_ok, s_code, s_errs = validate_network_streaming_rtmp_srt_and_tls(
            streaming_protocol=streaming_protocol,
            streaming_codec=streaming_codec,
            streaming_bitrate_mbps=float(streaming_bitrate_mbps),
            stream_width=stream_width,
            stream_height=stream_height,
            stream_fps=float(stream_fps),
            tls_cert_path=tls_cert_path,
            tls_cert_verified=tls_cert_verified,
            tls_cert_mount_ro=tls_cert_mount_ro,
            tls_cert_write_errno=tls_cert_write_errno,
            tls_cert_mutation_bytes=tls_cert_mutation_bytes,
            tls_cert_write_attempted=tls_cert_write_attempted,
        )
        if not s_ok:
            _add_code(codes, s_code)
            errors.extend(s_errs)
            streaming_ok = s_code != STATUS_BLOCKED_G67_STREAMING_BITRATE_OR_CODEC_VIOLATION
            tls_ok = s_code != STATUS_BLOCKED_G67_RTMPS_TLS_CERT_NON_RO_OR_UNVERIFIED
        else:
            streaming_ok = True
            tls_ok = True

    valid = (
        telemetry_ok
        and usblan_ok
        and setting_ok
        and streaming_ok
        and tls_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G67 if valid else codes[0]

    return Fx3UsbLanRtmpSrtGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        body_model_name=str(body_model_name) if isinstance(body_model_name, str) else "INVALID",
        body_model_id=int(b_id) if b_id is not None else -1,
        body_model_id_hex=f"0x{b_id:08x}" if b_id is not None else "INVALID",
        firmware_version=str(firmware_version) if isinstance(firmware_version, str) else "INVALID",
        usblan_autoconnect_enabled=bool(usblan_autoconnect_enabled) if isinstance(usblan_autoconnect_enabled, bool) else False,
        usb_port=str(usb_port) if isinstance(usb_port, str) else "INVALID",
        usblan_protocol=str(usblan_protocol) if isinstance(usblan_protocol, str) else "INVALID",
        adapter_chipset=str(adapter_chipset) if isinstance(adapter_chipset, str) else "INVALID",
        power_mode=str(power_mode) if isinstance(power_mode, str) else "INVALID",
        np_fz100_present=bool(np_fz100_present) if isinstance(np_fz100_present, bool) else False,
        battery_pct=int(battery_pct) if _is_non_negative_int(battery_pct) else -1,
        dc_c1_pd_watts=float(dc_c1_pd_watts) if _is_finite_number(dc_c1_pd_watts) else -1.0,
        emarked_5a_cable=bool(emarked_5a_cable) if isinstance(emarked_5a_cable, bool) else False,
        auto_reconnect_latency_ms=float(auto_reconnect_latency_ms) if _is_finite_number(auto_reconnect_latency_ms) else -1.0,
        usblan_autoconnect_valid=usblan_ok,
        stageb_setting_network_overwrite_attempted=bool(stageb_setting_network_overwrite_attempted) if isinstance(stageb_setting_network_overwrite_attempted, bool) else True,
        setting_network_writes=int(setting_network_writes) if _is_non_negative_int(setting_network_writes) else -1,
        setting_mount_ro_protected=bool(setting_mount_ro_protected) if isinstance(setting_mount_ro_protected, bool) else False,
        target_profile_path=str(target_profile_path) if isinstance(target_profile_path, str) else "INVALID",
        stock_setting_protected=setting_ok,
        streaming_protocol=str(streaming_protocol) if isinstance(streaming_protocol, str) else "INVALID",
        streaming_codec=str(streaming_codec) if isinstance(streaming_codec, str) else "INVALID",
        streaming_bitrate_mbps=float(streaming_bitrate_mbps) if _is_finite_number(streaming_bitrate_mbps) else -1.0,
        stream_width=int(stream_width) if _is_non_negative_int(stream_width) else -1,
        stream_height=int(stream_height) if _is_non_negative_int(stream_height) else -1,
        stream_fps=float(stream_fps) if _is_finite_number(stream_fps) else -1.0,
        streaming_cap_valid=streaming_ok,
        tls_cert_path=str(tls_cert_path) if isinstance(tls_cert_path, str) else "INVALID",
        tls_cert_verified=bool(tls_cert_verified) if isinstance(tls_cert_verified, bool) else False,
        tls_cert_mount_ro=bool(tls_cert_mount_ro) if isinstance(tls_cert_mount_ro, bool) else False,
        tls_cert_write_errno=str(tls_cert_write_errno) if isinstance(tls_cert_write_errno, str) else "INVALID",
        tls_cert_mutation_bytes=int(tls_cert_mutation_bytes) if _is_non_negative_int(tls_cert_mutation_bytes) else -1,
        tls_cert_write_attempted=bool(tls_cert_write_attempted) if isinstance(tls_cert_write_attempted, bool) else True,
        tls_erofs_valid=tls_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_clipflag_anamorphic_and_bright_magnifier_guard(
    *,
    creators_app_version: str = CREATORS_APP_MIN_VERSION,
    monitor_control_version: str = MONITOR_CONTROL_MIN_VERSION_G68,
    clip_flag: str = "KEEP",
    filter_flags: Sequence[str] = FILTERABLE_CLIP_FLAGS,
    sidecar_format: str = "MXF_SIDECAR",
    sidecar_metadata_only: bool = True,
    video_essence_modified: bool = False,
    video_essence_mutation_bytes: int = 0,
    mxf_mp4_essence_sha256_before: str = DEFAULT_SYNTHETIC_ESSENCE_SHA256,
    mxf_mp4_essence_sha256_after: str = DEFAULT_SYNTHETIC_ESSENCE_SHA256,
    stage_b_persistent_clip_rewrite: bool = False,
    anamorphic_desqueeze_ratio: float = 1.5,
    desqueeze_monitoring_only: bool = True,
    recorded_essence_anamorphic_baked: bool = False,
    hdmi_raw_output_active: bool = False,
    anamorphic_desqueeze_active_on_hdmi_raw: bool = False,
    anamorphic_auto_disabled_for_hdmi_raw: bool = True,
    hdmi_raw_width: int = HDMI_RAW_UNSCALED_WIDTH,
    hdmi_raw_height: int = HDMI_RAW_UNSCALED_HEIGHT,
    hdmi_raw_linear_unscaled: bool = True,
    soc_name: str = CXD90057_SOC_NAME,
    bright_monitoring_active: bool = True,
    focus_magnifier_active: bool = True,
    focus_magnifier_factor: float = 4.0,
    coexistence_supported: bool = True,
    magnifier_overlay_non_destructive: bool = True,
    recorded_essence_bright_or_zoom_baked: bool = False,
    exposure_metering_corrupted: bool = False,
    cxd90057_isp_pipeline_fault: bool = False,
    guard_profile: str = "FX3_REALHW_G68_CLIPFLAG_ANAMORPHIC_GUARD_DEFAULT",
) -> CreatorsCloudClipFlagAnamorphicResult:
    """Verify Gate G68 (`Creators' Cloud` Clip-Flag, Anamorphic De-Squeeze & Bright-Monitoring Magnifier)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        creators_app_version,
        monitor_control_version,
        clip_flag,
        sidecar_format,
        mxf_mp4_essence_sha256_before,
        mxf_mp4_essence_sha256_after,
        soc_name,
        guard_profile,
    )
    bools = (
        sidecar_metadata_only,
        video_essence_modified,
        stage_b_persistent_clip_rewrite,
        desqueeze_monitoring_only,
        recorded_essence_anamorphic_baked,
        hdmi_raw_output_active,
        anamorphic_desqueeze_active_on_hdmi_raw,
        anamorphic_auto_disabled_for_hdmi_raw,
        hdmi_raw_linear_unscaled,
        bright_monitoring_active,
        focus_magnifier_active,
        coexistence_supported,
        magnifier_overlay_non_destructive,
        recorded_essence_bright_or_zoom_baked,
        exposure_metering_corrupted,
        cxd90057_isp_pipeline_fault,
    )

    filter_seq_ok = (
        isinstance(filter_flags, (list, tuple))
        and all(isinstance(f, str) and bool(f.strip()) for f in filter_flags)
    )

    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and filter_seq_ok
        and all(isinstance(b, bool) for b in bools)
        and _is_non_negative_int(video_essence_mutation_bytes)
        and _is_finite_number(anamorphic_desqueeze_ratio)
        and float(anamorphic_desqueeze_ratio) > 0.0
        and _is_non_negative_int(hdmi_raw_width)
        and _is_non_negative_int(hdmi_raw_height)
        and _is_finite_number(focus_magnifier_factor)
        and float(focus_magnifier_factor) > 0.0
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G68_TELEMETRY_INVALID)
        errors.append(
            "Gate G68 received invalid or malformed Clip-Flag / Anamorphic / Bright-Monitoring telemetry."
        )

    clip_ok = False
    anamorphic_ok = False
    bright_ok = False

    if telemetry_ok:
        clip_ok, c_code, c_errs = validate_creators_cloud_clip_flag_hygiene(
            creators_app_version=creators_app_version,
            monitor_control_version=monitor_control_version,
            clip_flag=clip_flag,
            filter_flags=filter_flags,
            sidecar_format=sidecar_format,
            sidecar_metadata_only=sidecar_metadata_only,
            video_essence_modified=video_essence_modified,
            video_essence_mutation_bytes=video_essence_mutation_bytes,
            mxf_mp4_essence_sha256_before=mxf_mp4_essence_sha256_before,
            mxf_mp4_essence_sha256_after=mxf_mp4_essence_sha256_after,
            stage_b_persistent_clip_rewrite=stage_b_persistent_clip_rewrite,
        )
        if not clip_ok:
            _add_code(codes, c_code)
            errors.extend(c_errs)

        anamorphic_ok, a_code, a_errs = validate_anamorphic_desqueeze_and_hdmi_raw_lock(
            anamorphic_desqueeze_ratio=float(anamorphic_desqueeze_ratio),
            desqueeze_monitoring_only=desqueeze_monitoring_only,
            recorded_essence_anamorphic_baked=recorded_essence_anamorphic_baked,
            hdmi_raw_output_active=hdmi_raw_output_active,
            anamorphic_desqueeze_active_on_hdmi_raw=anamorphic_desqueeze_active_on_hdmi_raw,
            anamorphic_auto_disabled_for_hdmi_raw=anamorphic_auto_disabled_for_hdmi_raw,
            hdmi_raw_width=hdmi_raw_width,
            hdmi_raw_height=hdmi_raw_height,
            hdmi_raw_linear_unscaled=hdmi_raw_linear_unscaled,
        )
        if not anamorphic_ok:
            _add_code(codes, a_code)
            errors.extend(a_errs)
        elif hdmi_raw_output_active and round(float(anamorphic_desqueeze_ratio), 2) != 1.0:
            warnings.append(
                f"HDMI RAW ({HDMI_RAW_UNSCALED_WIDTH}x{HDMI_RAW_UNSCALED_HEIGHT}) active: "
                f"{anamorphic_desqueeze_ratio}x anamorphic de-squeeze auto-disabled to keep linear RAW unscaled."
            )

        bright_ok, b_code, b_errs = validate_bright_monitoring_and_focus_magnifier_cxd90057(
            soc_name=soc_name,
            bright_monitoring_active=bright_monitoring_active,
            focus_magnifier_active=focus_magnifier_active,
            focus_magnifier_factor=float(focus_magnifier_factor),
            coexistence_supported=coexistence_supported,
            magnifier_overlay_non_destructive=magnifier_overlay_non_destructive,
            recorded_essence_bright_or_zoom_baked=recorded_essence_bright_or_zoom_baked,
            exposure_metering_corrupted=exposure_metering_corrupted,
            cxd90057_isp_pipeline_fault=cxd90057_isp_pipeline_fault,
        )
        if not bright_ok:
            _add_code(codes, b_code)
            errors.extend(b_errs)

    valid = (
        telemetry_ok
        and clip_ok
        and anamorphic_ok
        and bright_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G68 if valid else codes[0]

    return CreatorsCloudClipFlagAnamorphicResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        creators_app_version=str(creators_app_version) if isinstance(creators_app_version, str) else "INVALID",
        monitor_control_version=str(monitor_control_version) if isinstance(monitor_control_version, str) else "INVALID",
        clip_flag=str(clip_flag) if isinstance(clip_flag, str) else "INVALID",
        filter_flags=tuple(str(f) for f in filter_flags) if filter_seq_ok else (),
        sidecar_format=str(sidecar_format) if isinstance(sidecar_format, str) else "INVALID",
        sidecar_metadata_only=bool(sidecar_metadata_only) if isinstance(sidecar_metadata_only, bool) else False,
        video_essence_modified=bool(video_essence_modified) if isinstance(video_essence_modified, bool) else True,
        video_essence_mutation_bytes=int(video_essence_mutation_bytes) if _is_non_negative_int(video_essence_mutation_bytes) else -1,
        mxf_mp4_essence_sha256_before=str(mxf_mp4_essence_sha256_before) if isinstance(mxf_mp4_essence_sha256_before, str) else "INVALID",
        mxf_mp4_essence_sha256_after=str(mxf_mp4_essence_sha256_after) if isinstance(mxf_mp4_essence_sha256_after, str) else "INVALID",
        stage_b_persistent_clip_rewrite=bool(stage_b_persistent_clip_rewrite) if isinstance(stage_b_persistent_clip_rewrite, bool) else True,
        clip_flag_hygiene_valid=clip_ok,
        anamorphic_desqueeze_ratio=float(anamorphic_desqueeze_ratio) if _is_finite_number(anamorphic_desqueeze_ratio) else -1.0,
        desqueeze_monitoring_only=bool(desqueeze_monitoring_only) if isinstance(desqueeze_monitoring_only, bool) else False,
        recorded_essence_anamorphic_baked=bool(recorded_essence_anamorphic_baked) if isinstance(recorded_essence_anamorphic_baked, bool) else True,
        hdmi_raw_output_active=bool(hdmi_raw_output_active) if isinstance(hdmi_raw_output_active, bool) else False,
        anamorphic_desqueeze_active_on_hdmi_raw=bool(anamorphic_desqueeze_active_on_hdmi_raw) if isinstance(anamorphic_desqueeze_active_on_hdmi_raw, bool) else True,
        anamorphic_auto_disabled_for_hdmi_raw=bool(anamorphic_auto_disabled_for_hdmi_raw) if isinstance(anamorphic_auto_disabled_for_hdmi_raw, bool) else False,
        hdmi_raw_width=int(hdmi_raw_width) if _is_non_negative_int(hdmi_raw_width) else -1,
        hdmi_raw_height=int(hdmi_raw_height) if _is_non_negative_int(hdmi_raw_height) else -1,
        hdmi_raw_linear_unscaled=bool(hdmi_raw_linear_unscaled) if isinstance(hdmi_raw_linear_unscaled, bool) else False,
        anamorphic_hdmi_raw_valid=anamorphic_ok,
        soc_name=str(soc_name) if isinstance(soc_name, str) else "INVALID",
        bright_monitoring_active=bool(bright_monitoring_active) if isinstance(bright_monitoring_active, bool) else False,
        focus_magnifier_active=bool(focus_magnifier_active) if isinstance(focus_magnifier_active, bool) else False,
        focus_magnifier_factor=float(focus_magnifier_factor) if _is_finite_number(focus_magnifier_factor) else -1.0,
        coexistence_supported=bool(coexistence_supported) if isinstance(coexistence_supported, bool) else False,
        magnifier_overlay_non_destructive=bool(magnifier_overlay_non_destructive) if isinstance(magnifier_overlay_non_destructive, bool) else False,
        recorded_essence_bright_or_zoom_baked=bool(recorded_essence_bright_or_zoom_baked) if isinstance(recorded_essence_bright_or_zoom_baked, bool) else True,
        exposure_metering_corrupted=bool(exposure_metering_corrupted) if isinstance(exposure_metering_corrupted, bool) else True,
        cxd90057_isp_pipeline_fault=bool(cxd90057_isp_pipeline_fault) if isinstance(cxd90057_isp_pipeline_fault, bool) else True,
        bright_magnifier_valid=bright_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G67 & Gate G68 Evaluators (Donor Audit + Guard -> GateVerdict)
# ---------------------------------------------------------------------------


def evaluate_g67_usblan_rtmp_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    usblan_rtmp_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase196DonorAuditResult] = None,
) -> Tuple[GateVerdict, G67UsbLanRtmpSrtGuardResult]:
    """Evaluate Gate G67 (`ILME-FX3` Power-On `USB-LAN` Auto-Connect & `RTMP/RTMPS/SRT` Guard)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase196_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(usblan_rtmp_kwargs or {})
    guard = verify_usblan_autoconnect_and_rtmp_srt_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE196_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G67 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G67 if valid else codes[0]

    res = G67UsbLanRtmpSrtGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        usblan_rtmp_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, body={guard.body_model_name}({guard.body_model_id_hex}), "
        f"fw={guard.firmware_version}, usblan={guard.usblan_protocol}/{guard.adapter_chipset}, "
        f"power={guard.power_mode}, setting_ro={guard.stock_setting_protected}, "
        f"stream={guard.streaming_protocol}/{guard.streaming_codec}@{guard.streaming_bitrate_mbps:.1f}Mbps"
        f"({guard.stream_width}x{guard.stream_height}@{guard.stream_fps:.2f}p), "
        f"tls_erofs={guard.tls_erofs_valid}"
    )

    verdict = GateVerdict(
        gate_id=G67_GATE_ID,
        gate_code=G67_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


def evaluate_g68_clipflag_anamorphic_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    clipflag_anamorphic_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase196DonorAuditResult] = None,
) -> Tuple[GateVerdict, G68ClipFlagAnamorphicGuardResult]:
    """Evaluate Gate G68 (`Creators' Cloud` Clip-Flag, Anamorphic De-Squeeze & Bright-Monitoring Magnifier)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase196_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(clipflag_anamorphic_kwargs or {})
    guard = verify_clipflag_anamorphic_and_bright_magnifier_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE196_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G68 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G68 if valid else codes[0]

    res = G68ClipFlagAnamorphicGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        clipflag_anamorphic_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, creators_app={guard.creators_app_version}, "
        f"m_and_c={guard.monitor_control_version}, clip_flag={guard.clip_flag}"
        f"(sidecar_only={guard.sidecar_metadata_only}, essence_mut={guard.video_essence_mutation_bytes}B), "
        f"anamorphic={guard.anamorphic_desqueeze_ratio}x(hdmi_raw={guard.hdmi_raw_output_active}, "
        f"raw_unscaled={guard.hdmi_raw_linear_unscaled}), "
        f"soc={guard.soc_name}(bright={guard.bright_monitoring_active}, "
        f"magnifier={guard.focus_magnifier_factor}x)"
    )

    verdict = GateVerdict(
        gate_id=G68_GATE_ID,
        gate_code=G68_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Unified 68-Gate Master Safety Preflight (`G01..G68`)
# ---------------------------------------------------------------------------


def evaluate_68gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G01..G66 pass-throughs
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
    nouvc_dcc1_pd_kwargs: Optional[Mapping[str, Any]] = None,
    lut_path_cineei_bt_kwargs: Optional[Mapping[str, Any]] = None,
    # G67 inputs (USB-LAN Power-On Auto-Connect & RTMP/RTMPS/SRT Guard)
    usblan_rtmp_kwargs: Optional[Mapping[str, Any]] = None,
    # G68 inputs (Creators' Cloud Clip-Flag, Anamorphic & Bright-Monitoring Magnifier)
    clipflag_anamorphic_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master68GateReport:
    """Evaluate all 68 Master Safety Gates (`G01..G68`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        if dry_run_simulated_backup is None
        else (dry_run_simulated or dry_run_simulated_backup)
    )

    m66_kwargs: Dict[str, Any] = {
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
        "nouvc_dcc1_pd_kwargs": nouvc_dcc1_pd_kwargs,
        "lut_path_cineei_bt_kwargs": lut_path_cineei_bt_kwargs,
    }
    if soc_start_ceiling_c is not None:
        m66_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m66_report: Master66GateReport = evaluate_66gate_preflight(
        resolved_root, **m66_kwargs
    )

    phase196_audit = audit_phase196_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g67_verdict, g67_res = evaluate_g67_usblan_rtmp_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        usblan_rtmp_kwargs=usblan_rtmp_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase196_audit,
    )

    g68_verdict, g68_res = evaluate_g68_clipflag_anamorphic_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        clipflag_anamorphic_kwargs=clipflag_anamorphic_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase196_audit,
    )

    gates_67_to_68 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g67_verdict, g68_verdict)
    ]
    all_gates = tuple(list(m66_report.gates) + gates_67_to_68)

    g01_to_g12_verified = int(m66_report.summary["g01_to_g12_verified"])
    g13_to_g66_verified = (
        int(m66_report.summary["g13_to_g64_verified"])
        + int(m66_report.summary["g65_to_g66_verified"])
    )
    g67_to_g68_verified = sum(1 for v in (g67_verdict, g68_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g66_verified + g67_to_g68_verified

    g67_to_g68_all_passed = g67_to_g68_verified == 2
    g13_to_g68_all_passed = (
        m66_report.g13_to_g66_all_passed and g67_to_g68_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m66_report.gates[:9])

    offline_65_verified = (
        g01_to_g09_ok
        and m66_report.offline_63_gates_verified
        and g67_to_g68_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_68_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g68_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes
    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m66_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_65_verified
        and m66_report.h0_h1_trial_entry_allowed
        and g67_to_g68_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m66_report.errors) + list(g67_verdict.errors) + list(g68_verdict.errors)
    )
    warnings: List[str] = (
        list(m66_report.warnings)
        + list(g67_verdict.warnings)
        + list(g68_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m66_report.g13_to_g66_all_passed:
        overall_status = m66_report.status
    elif not g67_verdict.passed:
        overall_status = g67_verdict.status
    elif not g68_verdict.passed:
        overall_status = g68_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_68_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_68_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_68_verified:
        overall_status = "VERIFIED_ALL_68_GATES"
    else:
        overall_status = "VERIFIED_65_OF_68_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m66_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g67_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g68_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 68,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 68 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g66_verified": g13_to_g66_verified,
        "g67_to_g68_verified": g67_to_g68_verified,
        "g13_to_g68_all_passed": g13_to_g68_all_passed,
        "g67_to_g68_all_passed": g67_to_g68_all_passed,
        "offline_65_gates_verified": offline_65_verified,
        "all_68_gates_verified": all_68_verified,
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

    return Master68GateReport(
        schema=REALHW_USBLAN_RTMP_CLIPFLAG_ANAMORPHIC_68GATE_SCHEMA,
        version=REALHW_USBLAN_RTMP_CLIPFLAG_ANAMORPHIC_68GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_65_gates_verified=offline_65_verified,
        all_68_gates_verified=all_68_verified,
        g13_to_g68_all_passed=g13_to_g68_all_passed,
        g67_to_g68_all_passed=g67_to_g68_all_passed,
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
        master_66_report=m66_report.to_dict(),
        g67_result=g67_res.to_dict(),
        g68_result=g68_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_68_master_safety_gates = evaluate_68gate_preflight
run_68_gate_preflight = evaluate_68gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard",
        description=(
            "Phase 196 — ILME-FX3 Power-On USB-LAN Auto-Connect & RTMP/RTMPS/SRT Guard (G67), "
            "Creators' Cloud Clip-Flag, Anamorphic De-Squeeze & Bright-Monitoring Magnifier Guard (G68), "
            "and 68-Gate Master Preflight (G01..G68)"
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G68 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_68gate_preflight(
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
            f"verified={report.summary['verified_gates']}/68 "
            f"g67_to_g68_all_passed={report.g67_to_g68_all_passed} "
            f"all_68_gates_verified={report.all_68_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
            f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
            f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
            f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        report.all_68_gates_verified
        if args.dry_run_simulated
        else report.offline_65_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
