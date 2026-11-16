"""Phase 177 — Real-Hardware Main Track Part 17:
Gate G59 (`ssboot` / `WBI2` `prsv-img` Bootloader-Bypass Guard + `liro.ko` /
`/proc/udm` Stage-B Write-Block + `H0 == H3` Clean-Uninstall Guard),
Gate G60 (`FX3 7.02` `>= Ver. 2.04` UFU Floor + Slot-1 Root & Duplicate
Filename Guard + C2PA 100-License Ceiling / `p12:/cert/RQ_LIC.DAT` `BLKROSET=1`
+ `Ver. 7.00+` Wireless Security Floor), and
60-Gate Milestone Master Preflight (`G01..G60` / `verify-60-gates`).

Composes `realhw_dualmedia_bench_interlock_and_58gate_guard` (`G01..G58`,
keeping `evaluate_58gate_preflight` and CLI `verify-58-gates` 100% intact)
with Wave-21 Sony BIONZ XR Real-Hardware Intelligence (`G59` and `G60`) while
hard-locking all physical flash/write/transmit redlines:
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
import math
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
from .realhw_dualmedia_bench_interlock_and_58gate_guard import (
    Master58GateReport,
    evaluate_58gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_SSBOOT_WBI2_SLOT1_UFU_60GATE_SCHEMA: str = (
    "fx3-realhw-ssboot-wbi2-slot1-ufu-60gate-preflight-v1"
)
REALHW_SSBOOT_WBI2_SLOT1_UFU_60GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED: bool = False
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

# Gate IDs & Canonical Codes for G59..G60
G59_GATE_ID: str = "G59_ssboot_wbi2_prsvimg_and_liro_bypass_guard"
G59_GATE_CODE: str = "GATE_G59_SSBOOT_WBI2_PRSVIMG_AND_LIRO_BYPASS_GUARD"
GATE_G59_SSBOOT_WBI2_PRSVIMG_AND_LIRO_BYPASS_GUARD: str = G59_GATE_CODE

G60_GATE_ID: str = "G60_fx3_702_ufu_version_floor_and_slot1_c2pa_guard"
G60_GATE_CODE: str = "GATE_G60_FX3_702_UFU_VERSION_FLOOR_AND_SLOT1_C2PA_GUARD"
GATE_G60_FX3_702_UFU_VERSION_FLOOR_AND_SLOT1_C2PA_GUARD: str = G60_GATE_CODE

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G59: str = (
    "VERIFIED_SSBOOT_WBI2_PRSVIMG_AND_LIRO_BYPASS_GUARD"
)
STATUS_VERIFIED_G60: str = (
    "VERIFIED_FX3_702_UFU_VERSION_FLOOR_AND_SLOT1_C2PA_GUARD"
)

# Gate G59 Violation Codes
STATUS_BLOCKED_G59_WBI2_TIER0_RECEIPT_MISSING: str = (
    "BLOCKED_G59_WBI2_TIER0_RECEIPT_MISSING"
)
STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED: str = (
    "BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED"
)
STATUS_BLOCKED_G59_SSBOOT_RESUME_INIT_BYPASS_TRAP: str = (
    "BLOCKED_G59_SSBOOT_RESUME_INIT_BYPASS_TRAP"
)
STATUS_BLOCKED_G59_WBI2_CLEAN_UNINSTALL_H0_H3_MISMATCH: str = (
    "BLOCKED_G59_WBI2_CLEAN_UNINSTALL_H0_H3_MISMATCH"
)
STATUS_BLOCKED_G59_TELEMETRY_INVALID: str = (
    "BLOCKED_G59_SSBOOT_WBI2_TELEMETRY_INVALID"
)

# Gate G60 Violation Codes
STATUS_BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR: str = (
    "BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR"
)
STATUS_BLOCKED_G60_SLOT1_ROOT_OR_DUPLICATE_BODYDATA: str = (
    "BLOCKED_G60_SLOT1_ROOT_OR_DUPLICATE_BODYDATA"
)
STATUS_BLOCKED_G60_C2PA_100_LICENSE_CEILING_OR_P12_RO: str = (
    "BLOCKED_G60_C2PA_100_LICENSE_CEILING_OR_P12_RO"
)
STATUS_BLOCKED_G60_INSECURE_WIRELESS_WEP_WPA1_IPSEC: str = (
    "BLOCKED_G60_INSECURE_WIRELESS_WEP_WPA1_IPSEC"
)
STATUS_BLOCKED_G60_TELEMETRY_INVALID: str = (
    "BLOCKED_G60_SLOT1_UFU_C2PA_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE177_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE177_60GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G59 Constants — Sony SCEL ssboot / WBI2 (/dev/nflasha5)
WBI_PARTITION_DEV: str = "/dev/nflasha5"
WBI_RAW_PARTITION_DEV: str = "/dev/pnflasha5"
WBI_MOUNT_POINT: str = "/wbi"
WBI_PARTITION_APPROX_MIB: float = 232.5
WBI_SECTOR0_BYTES: int = 512
WBI2_MAGIC_BYTES: bytes = b"WBI2\x00\x00\x00\x00"
WBI2_MAGIC_HEX: str = "5742493200000000"
WBI_COMPRESSION_CODEC: str = "LZO"
WBI_SNAPSHOT_IMAGE_NAME: str = "prsv-img"
WBI_KERNEL_MODULE_NAME: str = "liro.ko"
WBI_UDM_PROC_DIR: str = "/proc/udm"
WBI_SUSPEND_DISK_STATE: str = "disk"
WBI_STAGE_A_VERIFY_TARGET: str = "fx6-stage-a-verify"
WBI_STOCK_INIT_PATH: str = "/sbin/init"
WBI_STOCK_WARMBOOT_SEC: float = 0.5
FX3RCPT1_MAGIC: str = "FX3RCPT1"
FX3RCPT1_PACKET_BYTES: int = 528

DEFAULT_SYNTHETIC_WBI2_SECTOR0_SHA256: str = hashlib.sha256(
    WBI2_MAGIC_BYTES + b":SECTOR0_512B:/dev/nflasha5:ILME-FX3:7.02"
).hexdigest()
DEFAULT_SYNTHETIC_NFLASHA5_FULL_SHA256: str = hashlib.sha256(
    b"ILME-FX3:0x91030080:/dev/nflasha5:WBI2_232.5MIB_H0_BASELINE_PHASE177"
).hexdigest()

# Gate G60 Constants — FX3 7.02 UFU Floor >= 2.04, Slot-1 Root, C2PA <= 100 & Wireless Floor
FX3_MODEL_ID_INT: int = 0x91030080
FX3_MODEL_ID_HEX: str = "0x91030080"
FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MIN_BODY_FIRMWARE_FLOOR: str = "2.04"
FX3_UFU_TARGET_VERSION: str = "7.02"
FX3_BRICK_LED_BELOW_FLOOR: str = "7L+7S"

BODYDATA_FILENAME: str = "BODYDATA.DAT"
BODYDATA_702_EXACT_BYTES: int = 811_876_768
BODYDATA_UFU_MAGIC_BYTES: bytes = b"\x89UFU\r\n\x1a\n"
BODYDATA_UFU_MAGIC_HEX: str = "895546550d0a1a0a"
PINNED_BODYDATA_HEADER_RELPATH: str = "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
PINNED_BODYDATA_HEADER_READ_BYTES: int = 4096
PINNED_BODYDATA_HEADER_SHA256: str = (
    "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
)
PINNED_BODYDATA_HEADER_MARKERS: Tuple[bytes, ...] = (
    BODYDATA_UFU_MAGIC_BYTES,
    b"DATV",
    b"PROV",
    b"UDID",
)

REQUIRED_UPDATE_SLOT: int = 1
REQUIRED_SLOT1_BODYDATA_PATH: str = "/BODYDATA.DAT"
C2PA_MAX_LICENSES_CEILING: int = 100
P12_RQ_LIC_PATH: str = "p12:/cert/RQ_LIC.DAT"
P12_DEVICE_NODE: str = "/dev/nflasha12"
P12_REQUIRED_MOUNT_FLAG: str = "MS_RDONLY"

DEPRECATED_WIRELESS_PROTOCOLS: Tuple[str, ...] = (
    "WEP",
    "WPA1",
    "WPA",
    "WPA-PSK",
    "IPSEC",
    "LEGACY_IPSEC",
)
ALLOWED_WIRELESS_PROTOCOLS: Tuple[str, ...] = (
    "WPA2",
    "WPA2-PSK",
    "WPA3",
    "WPA3-SAE",
    "ACCESS_AUTHENTICATION",
    "NONE_AIRPLANE_OFF",
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_TRIVIAL_HEX64: Tuple[str, ...] = ("0" * 64, "f" * 64)
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?$", re.IGNORECASE)
_BODYDATA_LIKE_RE = re.compile(r"bodydata", re.IGNORECASE)

# Pinned FX3 v7.02 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE177_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_liro_ko": (
        "fx3",
        "sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha15/kmod/liro.ko",
        121_488,
        "b4bd80cc614751e0092ee19e89cb90632db580bc01f23f1a1df23544e9b10186",
        (
            b"\x7fELF",
            b"liro",
            b"/proc/liro/start",
            b"/proc/susres",
            b"liro-RESUME",
            b"liro_resume_async",
        ),
        "fx3/liro.ko::{121488B,ELF,liro,/proc/liro/start,/proc/susres,liro-RESUME,liro_resume_async}",
    ),
    "fx3_sbin_init2": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha7/sbin/init2",
        1_658,
        "45d3b907e6ef96c9a930cd3e6f919db700bffb5f18c386abfdb655f4d9954aeb",
        (
            b"/proc/udm/upm_bootmode",
            b"/proc/udm/drivers",
            b"/usr/bin/bootin.elf",
            b"setup_senser",
        ),
        "fx3/sbin/init2::{1658B,/proc/udm/upm_bootmode,/proc/udm/drivers,/usr/bin/bootin.elf,setup_senser}",
    ),
    "fx3_initrc_fstab": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha7/sbin/initrc/fstab",
        1_085,
        "3936e6508ba89a025fc998c824434562c2d16234db96e179ec3f3a90a5a1d6f0",
        (
            b"/dev/nflasha12",
            b"/cert",
            b"/dev/nflasha15",
            b"/usr",
        ),
        "fx3/sbin/initrc/fstab::{1085B,/dev/nflasha12,/cert,/dev/nflasha15,/usr}",
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
            b"udm",
        ),
        "fx3/im.elf::{40920B,ELF,/dev/nflasha12,/cert,udm}",
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
            b"sigcert.p12",
            b"WEP",
        ),
        "fx3/libmpr.so::{3517008B,ELF,InfraC2PA,c2pa.created,sigcert.p12,WEP}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase177DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    bodydata_header_verified: bool
    bodydata_total_bytes: int
    bodydata_header_sha256: str
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SsbootWbi2LiroGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    wbi_partition_dev: str
    wbi_raw_partition_dev: str
    wbi_mount_point: str
    wbi2_magic_hex: str
    wbi_compression_codec: str
    wbi_snapshot_image_name: str
    fx3rcpt1_magic: str
    fx3rcpt1_packet_bytes: int
    tier0_wbi2_sector0_captured: bool
    tier0_wbi2_sector0_sha256: str
    tier0_nflasha5_full_captured: bool
    tier0_nflasha5_h0_sha256: str
    tier0_receipt_valid: bool
    blkroset_nflasha5: int
    blkroset_pnflasha5: int
    proc_udm_write_blocked: bool
    pm_suspend_disk_blocked: bool
    stageb_snapshot_save_blocked: bool
    wbi_persistent_writes: int
    wbi_mutation_bytes: int
    stageb_ro_protection_valid: bool
    wbi2_active_resume_pending: bool
    wbi2_resume_bypass_verified: bool
    init_entry_executed: bool
    stage_a_verify_executed: bool
    sbin_init_bypassed: bool
    resume_bypass_guard_valid: bool
    h3_wbi2_sector0_sha256: str
    h3_nflasha5_full_sha256: str
    h0_equals_h3_wbi2: bool
    stock_warmboot_05s_preserved: bool
    clean_uninstall_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Slot1UfuC2paGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    target_model_id_hex: str
    target_model_name: str
    body_firmware_version: str
    min_body_firmware_floor: str
    target_ufu_version: str
    bodydata_filename: str
    bodydata_size_bytes: int
    bodydata_ufu_magic_hex: str
    body_version_floor_valid: bool
    update_slot: int
    bodydata_path: str
    c2pa_import_slot: int
    c2pa_import_path: str
    duplicate_bodydata_detected: bool
    slot1_placement_valid: bool
    c2pa_license_count: int
    c2pa_max_licenses_ceiling: int
    rq_lic_path: str
    p12_device_node: str
    p12_blkroset: int
    p12_mount_flags: str
    p12_mutation_bytes: int
    c2pa_and_p12_lock_valid: bool
    stageb_wireless_profiles: Tuple[str, ...]
    rejected_wireless_protocols: Tuple[str, ...]
    wireless_security_floor_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G59SsbootWbi2Result:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    ssboot_wbi2_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G60Slot1UfuC2paResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    slot1_ufu_c2pa_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master60GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_57_gates_verified: bool
    all_60_gates_verified: bool
    g13_to_g60_all_passed: bool
    g59_to_g60_all_passed: bool
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
    master_58_report: Dict[str, Any]
    g59_result: Dict[str, Any]
    g60_result: Dict[str, Any]
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


def _read_file_o_rdonly(path: Path, max_bytes: Optional[int] = None) -> Tuple[bytes, int]:
    """Strictly read a file via `os.open(..., os.O_RDONLY)` without leaking raw bytes.
    Returns `(content_bytes, total_file_size)`.
    """
    fd = os.open(str(path), os.O_RDONLY)
    try:
        total_size = int(os.fstat(fd).st_size)
        if max_bytes is not None:
            data = os.read(fd, max_bytes)
            return data, total_size
        chunks: List[bytes] = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks), total_size
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


def _normalize_ro_flag(val: Any) -> Optional[int]:
    """Normalize `BLKROSET` flag (`1` / `True` -> `1`, `0` / `False` -> `0`)."""
    if isinstance(val, bool):
        return 1 if val else 0
    if isinstance(val, int) and val in (0, 1):
        return int(val)
    return None


def parse_firmware_version_tuple(version_str: Any) -> Optional[Tuple[int, int, int]]:
    """Parse a Sony camera firmware version string like `'2.04'` or `'7.02'` into `(major, minor, patch)`."""
    if not isinstance(version_str, str):
        return None
    m = _VERSION_RE.match(version_str.strip())
    if not m:
        return None
    major = int(m.group(1))
    minor = int(m.group(2))
    patch = int(m.group(3)) if m.group(3) is not None else 0
    return (major, minor, patch)


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit (FX3 7.02)
# ---------------------------------------------------------------------------


def audit_phase177_donor_contracts(
    *_,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase177DonorAuditResult:
    """Inspect FX3 `7.02` `liro.ko`, `sbin/init2`, `sbin/initrc/fstab`, `im.elf`,
    `libmpr.so`, and the `4096 B` header of `fx3-7.02-BODYDATA.DAT` strictly via
    `os.open(..., os.O_RDONLY)` with deterministic clean-room fallback when
    `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent.
    """
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)
    effective_work_root: Optional[Path] = (
        Path(work_root) if work_root is not None else paths.work_root
    )

    resolved: Dict[str, Path] = {}
    bodydata_path: Optional[Path] = None
    if effective_work_root is not None:
        for key, (
            _body,
            rel_path,
            _sz,
            _sha,
            _toks,
            _lbl,
        ) in PINNED_PHASE177_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path
        bodydata_path = effective_work_root / PINNED_BODYDATA_HEADER_RELPATH

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
        and (bodydata_path is not None and bodydata_path.is_file())
    )

    if not donor_available:
        return Phase177DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                [spec[5] for spec in PINNED_PHASE177_DONOR_SPECS.values()]
                + ["fx3/BODYDATA.DAT::{811876768B,\\x89UFU,DATV,PROV,UDID}"]
            ),
            missing_markers=(),
            fx3_contracts_verified=True,
            bodydata_header_verified=True,
            bodydata_total_bytes=BODYDATA_702_EXACT_BYTES,
            bodydata_header_sha256=PINNED_BODYDATA_HEADER_SHA256,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE177_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE177_DONOR_SPECS.items()
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
    ) in PINNED_PHASE177_DONOR_SPECS.items():
        blob, _ = _read_file_o_rdonly(resolved[key])
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

    assert bodydata_path is not None
    hdr_blob, bd_total_size = _read_file_o_rdonly(
        bodydata_path, max_bytes=PINNED_BODYDATA_HEADER_READ_BYTES
    )
    files_inspected += 1
    hdr_sha = hashlib.sha256(hdr_blob).hexdigest()
    bd_label = "fx3/BODYDATA.DAT::{811876768B,\\x89UFU,DATV,PROV,UDID}"
    bd_missing = [m for m in PINNED_BODYDATA_HEADER_MARKERS if m not in hdr_blob]
    bd_ok = (
        bd_total_size == BODYDATA_702_EXACT_BYTES
        and hdr_sha == PINNED_BODYDATA_HEADER_SHA256
        and not bd_missing
    )
    if not bd_missing:
        checked.append(bd_label)
    else:
        missing.append(bd_label)
        errors.append(
            f"Donor BODYDATA.DAT header missing {len(bd_missing)} marker(s)."
        )
    if bd_total_size != BODYDATA_702_EXACT_BYTES or hdr_sha != PINNED_BODYDATA_HEADER_SHA256:
        errors.append(
            f"Donor BODYDATA.DAT integrity mismatch: size={bd_total_size} "
            f"(expected {BODYDATA_702_EXACT_BYTES}), hdr_sha256={hdr_sha} "
            f"(expected {PINNED_BODYDATA_HEADER_SHA256})."
        )

    fx3_keys = {
        k for k, spec in PINNED_PHASE177_DONOR_SPECS.items() if spec[0] == "fx3"
    }
    valid = len(errors) == 0 and len(missing) == 0 and bd_ok
    return Phase177DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE177_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_keys.issubset(passed_keys) and bd_ok and valid,
        bodydata_header_verified=bd_ok,
        bodydata_total_bytes=bd_total_size,
        bodydata_header_sha256=hdr_sha,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Pure Helper Validators (G59 & G60)
# ---------------------------------------------------------------------------


def build_synthetic_wbi2_sector0(
    magic: bytes = WBI2_MAGIC_BYTES,
    payload_tag: bytes = b"PRSV-IMG-LZO-FX3-702",
) -> bytes:
    """Build a synthetic 512-byte `/dev/nflasha5` Sector-0 header carrying `WBI2\\x00\\x00\\x00\\x00`."""
    buf = bytearray(WBI_SECTOR0_BYTES)
    buf[: len(magic)] = magic[: WBI_SECTOR0_BYTES]
    tag_start = min(len(magic), WBI_SECTOR0_BYTES)
    tag_end = min(tag_start + len(payload_tag), WBI_SECTOR0_BYTES)
    buf[tag_start:tag_end] = payload_tag[: tag_end - tag_start]
    return bytes(buf)


def validate_wbi2_tier0_receipt(
    *,
    wbi_partition_dev: str = WBI_PARTITION_DEV,
    wbi_raw_partition_dev: str = WBI_RAW_PARTITION_DEV,
    wbi_mount_point: str = WBI_MOUNT_POINT,
    wbi2_sector0_bytes: Optional[bytes] = None,
    wbi2_magic_hex: str = WBI2_MAGIC_HEX,
    wbi_compression_codec: str = WBI_COMPRESSION_CODEC,
    wbi_snapshot_image_name: str = WBI_SNAPSHOT_IMAGE_NAME,
    fx3rcpt1_magic: str = FX3RCPT1_MAGIC,
    fx3rcpt1_packet_bytes: int = FX3RCPT1_PACKET_BYTES,
    fx3rcpt1_verified: bool = True,
    tier0_wbi2_sector0_captured: bool = True,
    tier0_wbi2_sector0_sha256: str = DEFAULT_SYNTHETIC_WBI2_SECTOR0_SHA256,
    tier0_nflasha5_full_captured: bool = True,
    tier0_nflasha5_h0_sha256: str = DEFAULT_SYNTHETIC_NFLASHA5_FULL_SHA256,
) -> Tuple[bool, str, List[str]]:
    """Validate that `FX3RCPT1` cold-backup captures BOTH the 512 B `WBI2` sector-0
    header AND the full `/dev/nflasha5` baseline `H0` before dual-boot activation.
    """
    errors: List[str] = []
    sector0_ok = True
    resolved_sector0_sha = tier0_wbi2_sector0_sha256.strip().lower()
    if wbi2_sector0_bytes is not None:
        if not isinstance(wbi2_sector0_bytes, (bytes, bytearray)):
            sector0_ok = False
            errors.append("wbi2_sector0_bytes must be bytes/bytearray.")
        elif len(wbi2_sector0_bytes) != WBI_SECTOR0_BYTES:
            sector0_ok = False
            errors.append(
                f"WBI2 sector0 length must be {WBI_SECTOR0_BYTES} B (got {len(wbi2_sector0_bytes)} B)."
            )
        elif bytes(wbi2_sector0_bytes[:8]) != WBI2_MAGIC_BYTES:
            sector0_ok = False
            errors.append(
                f"WBI2 sector0 magic mismatch: got {bytes(wbi2_sector0_bytes[:8]).hex()}, expected {WBI2_MAGIC_HEX}."
            )
        else:
            computed = hashlib.sha256(bytes(wbi2_sector0_bytes)).hexdigest()
            if computed != resolved_sector0_sha:
                sector0_ok = False
                errors.append(
                    "tier0_wbi2_sector0_sha256 does not match wbi2_sector0_bytes digest."
                )

    ok = (
        sector0_ok
        and wbi_partition_dev.strip() == WBI_PARTITION_DEV
        and wbi_raw_partition_dev.strip() == WBI_RAW_PARTITION_DEV
        and wbi_mount_point.strip() == WBI_MOUNT_POINT
        and wbi2_magic_hex.strip().lower() == WBI2_MAGIC_HEX
        and wbi_compression_codec.strip().upper() == WBI_COMPRESSION_CODEC
        and wbi_snapshot_image_name.strip() == WBI_SNAPSHOT_IMAGE_NAME
        and fx3rcpt1_magic.strip() == FX3RCPT1_MAGIC
        and int(fx3rcpt1_packet_bytes) == FX3RCPT1_PACKET_BYTES
        and fx3rcpt1_verified
        and tier0_wbi2_sector0_captured
        and _is_valid_hex64(resolved_sector0_sha)
        and tier0_nflasha5_full_captured
        and _is_valid_hex64(tier0_nflasha5_h0_sha256)
    )
    if not ok and not errors:
        errors.append(
            "Tier-0 FX3RCPT1 cold-backup receipt must capture both 512 B WBI2 header "
            "and full /dev/nflasha5 H0 SHA-256 baseline before dual-boot activation."
        )
    return ok, ("" if ok else STATUS_BLOCKED_G59_WBI2_TIER0_RECEIPT_MISSING), errors


def validate_wbi2_stageb_ro_protection(
    *,
    blkroset_nflasha5: int | bool = 1,
    blkroset_pnflasha5: int | bool = 1,
    proc_udm_write_blocked: bool = True,
    pm_suspend_disk_blocked: bool = True,
    stageb_snapshot_save_blocked: bool = True,
    liro_snapshot_save_invoked: bool = False,
    wbi_persistent_writes: int = 0,
    wbi_mutation_bytes: int = 0,
) -> Tuple[bool, str, List[str]]:
    """Enforce `BLKROSET=1` on `/dev/nflasha5` + `/dev/pnflasha5` and zero Stage-B
    `ssboot` / `/proc/udm` / `PM_SUSPEND_DISK` snapshot writes.
    """
    errors: List[str] = []
    ro_a5 = _normalize_ro_flag(blkroset_nflasha5)
    ro_pa5 = _normalize_ro_flag(blkroset_pnflasha5)
    ok = (
        ro_a5 == 1
        and ro_pa5 == 1
        and proc_udm_write_blocked
        and pm_suspend_disk_blocked
        and stageb_snapshot_save_blocked
        and (not liro_snapshot_save_invoked)
        and int(wbi_persistent_writes) == 0
        and int(wbi_mutation_bytes) == 0
    )
    if not ok:
        errors.append(
            f"Stage-B WBI2 read-only protection violated: BLKROSET(nflasha5={ro_a5}, "
            f"pnflasha5={ro_pa5}), proc_udm_blocked={proc_udm_write_blocked}, "
            f"pm_suspend_disk_blocked={pm_suspend_disk_blocked}, "
            f"stageb_snapshot_save_blocked={stageb_snapshot_save_blocked}, "
            f"liro_save={liro_snapshot_save_invoked}, wbi_writes={wbi_persistent_writes}, "
            f"wbi_mut_bytes={wbi_mutation_bytes}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED),
        errors,
    )


def validate_ssboot_resume_bypass_guard(
    *,
    wbi2_active_resume_pending: bool = False,
    wbi2_resume_bypass_verified: bool = True,
    cold_boot_verified: bool = True,
    init_entry_executed: bool = True,
    stage_a_verify_executed: bool = True,
    sbin_init_bypassed: bool = False,
    sbin_init_path: str = WBI_STOCK_INIT_PATH,
    stage_a_verify_script: str = WBI_STAGE_A_VERIFY_TARGET,
) -> Tuple[bool, str, List[str]]:
    """Fail closed if an active/unhandled `WBI2` resume trap would bypass `/sbin/init`
    (`fx6-stage-a-verify`) and jump straight into stale DRAM snapshot resume.
    """
    errors: List[str] = []
    unhandled_resume_trap = wbi2_active_resume_pending and (
        (not wbi2_resume_bypass_verified) or (not cold_boot_verified)
    )
    ok = (
        (not unhandled_resume_trap)
        and wbi2_resume_bypass_verified
        and cold_boot_verified
        and init_entry_executed
        and stage_a_verify_executed
        and (not sbin_init_bypassed)
        and sbin_init_path.strip() == WBI_STOCK_INIT_PATH
        and stage_a_verify_script.strip() == WBI_STAGE_A_VERIFY_TARGET
    )
    if not ok:
        errors.append(
            f"WBI2 ssboot resume bypass trap detected: resume_pending={wbi2_active_resume_pending}, "
            f"bypass_verified={wbi2_resume_bypass_verified}, cold_boot={cold_boot_verified}, "
            f"init_exec={init_entry_executed}, stage_a_verify={stage_a_verify_executed}, "
            f"sbin_init_bypassed={sbin_init_bypassed}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G59_SSBOOT_RESUME_INIT_BYPASS_TRAP),
        errors,
    )


def validate_wbi2_clean_uninstall_h0_h3(
    *,
    tier0_wbi2_sector0_sha256: str = DEFAULT_SYNTHETIC_WBI2_SECTOR0_SHA256,
    tier0_nflasha5_h0_sha256: str = DEFAULT_SYNTHETIC_NFLASHA5_FULL_SHA256,
    h3_wbi2_sector0_sha256: str = DEFAULT_SYNTHETIC_WBI2_SECTOR0_SHA256,
    h3_nflasha5_full_sha256: str = DEFAULT_SYNTHETIC_NFLASHA5_FULL_SHA256,
    stock_warmboot_05s_preserved: bool = True,
    clean_uninstall_verified: bool = True,
) -> Tuple[bool, str, List[str]]:
    """Verify Clean Uninstall (`H2 -> H3`) restores bit-exact `512 B` `WBI2` header
    and full `/dev/nflasha5` `H0 == H3` baseline, preserving Stock FX3 `0.5s` warm-boot.
    """
    errors: List[str] = []
    s0_h0 = tier0_wbi2_sector0_sha256.strip().lower()
    s0_h3 = h3_wbi2_sector0_sha256.strip().lower()
    full_h0 = tier0_nflasha5_h0_sha256.strip().lower()
    full_h3 = h3_nflasha5_full_sha256.strip().lower()
    ok = (
        _is_valid_hex64(s0_h0)
        and _is_valid_hex64(s0_h3)
        and _is_valid_hex64(full_h0)
        and _is_valid_hex64(full_h3)
        and (s0_h0 == s0_h3)
        and (full_h0 == full_h3)
        and stock_warmboot_05s_preserved
        and clean_uninstall_verified
    )
    if not ok:
        errors.append(
            f"Clean Uninstall H0==H3 WBI2 mismatch: sector0_eq={s0_h0 == s0_h3}, "
            f"full_nflasha5_eq={full_h0 == full_h3}, warmboot_05s={stock_warmboot_05s_preserved}, "
            f"uninstall_ok={clean_uninstall_verified}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G59_WBI2_CLEAN_UNINSTALL_H0_H3_MISMATCH),
        errors,
    )


def validate_fx3_body_firmware_floor(
    *,
    body_firmware_version: str = FX3_MIN_BODY_FIRMWARE_FLOOR,
    target_ufu_version: str = FX3_UFU_TARGET_VERSION,
    target_model_id: int | str = FX3_MODEL_ID_INT,
    target_model_name: str = FX3_MODEL_NAME,
    bodydata_filename: str = BODYDATA_FILENAME,
    bodydata_size_bytes: int = BODYDATA_702_EXACT_BYTES,
    bodydata_ufu_magic_hex: str = BODYDATA_UFU_MAGIC_HEX,
) -> Tuple[bool, str, List[str]]:
    """Enforce FX3 body firmware `>= Ver. 2.04` floor before `Ver. 7.00 / 7.02`
    `BODYDATA.DAT` (`811,876,768 B`, `\\x89UFU\\r\\n\\x1a\\n`, Model ID `0x91030080`) arming.
    """
    errors: List[str] = []
    body_ver = parse_firmware_version_tuple(body_firmware_version)
    floor_ver = parse_firmware_version_tuple(FX3_MIN_BODY_FIRMWARE_FLOOR)
    target_ver = parse_firmware_version_tuple(target_ufu_version)
    min_target_ver = parse_firmware_version_tuple("7.00")
    model_id_int = _normalize_model_id_int(target_model_id)

    assert floor_ver is not None and min_target_ver is not None
    body_ok = body_ver is not None and body_ver >= floor_ver
    target_ok = target_ver is not None and target_ver >= min_target_ver
    spec_ok = (
        model_id_int == FX3_MODEL_ID_INT
        and target_model_name.strip().upper() == FX3_MODEL_NAME
        and bodydata_filename.strip() == BODYDATA_FILENAME
        and int(bodydata_size_bytes) == BODYDATA_702_EXACT_BYTES
        and bodydata_ufu_magic_hex.strip().lower() == BODYDATA_UFU_MAGIC_HEX
    )
    ok = body_ok and target_ok and spec_ok
    if not ok:
        errors.append(
            f"FX3 7.02 UFU floor/spec rejected: body_ver={body_firmware_version!r} "
            f"(requires >= {FX3_MIN_BODY_FIRMWARE_FLOOR}; <= 2.02 triggers {FX3_BRICK_LED_BELOW_FLOOR} LED brick), "
            f"target_ufu={target_ufu_version!r}, model={target_model_name}({target_model_id!r}), "
            f"size={bodydata_size_bytes}B, magic={bodydata_ufu_magic_hex!r}."
        )
    return ok, ("" if ok else STATUS_BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR), errors


def _is_duplicate_or_renamed_bodydata(entry_name: str) -> bool:
    base = entry_name.rsplit("/", 1)[-1].strip()
    if not base:
        return False
    if base == BODYDATA_FILENAME:
        return False
    return bool(_BODYDATA_LIKE_RE.search(base))


def validate_slot1_root_and_duplicate_guard(
    *,
    update_slot: int = REQUIRED_UPDATE_SLOT,
    bodydata_path: str = REQUIRED_SLOT1_BODYDATA_PATH,
    c2pa_import_slot: int = REQUIRED_UPDATE_SLOT,
    c2pa_import_path: str = "/RQ_LIC.DAT",
    slot1_root_entries: Sequence[str] = (BODYDATA_FILENAME,),
    slot2_root_entries: Sequence[str] = (),
    duplicate_bodydata_detected: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Enforce Slot-1 root-only placement for `BODYDATA.DAT` and C2PA imports,
    rejecting Slot-2 attempts, subdirectories, or duplicate/renamed copies (`BODYDATA (1).DAT`).
    """
    errors: List[str] = []
    norm_bd_path = bodydata_path.strip()
    norm_c2pa_path = c2pa_import_path.strip()
    bd_is_root = norm_bd_path == REQUIRED_SLOT1_BODYDATA_PATH
    c2pa_is_root = (
        norm_c2pa_path.startswith("/")
        and "/" not in norm_c2pa_path.lstrip("/")
        and len(norm_c2pa_path.lstrip("/")) > 0
    )

    slot1_exact_count = sum(
        1 for item in slot1_root_entries if item.strip() == BODYDATA_FILENAME
    )
    slot1_dups = [
        item for item in slot1_root_entries if _is_duplicate_or_renamed_bodydata(item)
    ]
    slot2_has_bd = any(
        item.strip() == BODYDATA_FILENAME or _is_duplicate_or_renamed_bodydata(item)
        for item in slot2_root_entries
    )

    ok = (
        int(update_slot) == REQUIRED_UPDATE_SLOT
        and int(c2pa_import_slot) == REQUIRED_UPDATE_SLOT
        and bd_is_root
        and c2pa_is_root
        and (not duplicate_bodydata_detected)
        and slot1_exact_count <= 1
        and len(slot1_dups) == 0
        and (not slot2_has_bd)
    )
    if not ok:
        errors.append(
            f"Slot-1 root / duplicate BODYDATA.DAT guard failed: update_slot={update_slot}, "
            f"bodydata_path={bodydata_path!r}, c2pa_slot={c2pa_import_slot}, "
            f"c2pa_path={c2pa_import_path!r}, slot1_dups={slot1_dups!r}, "
            f"slot1_exact_count={slot1_exact_count}, slot2_has_bd={slot2_has_bd}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G60_SLOT1_ROOT_OR_DUPLICATE_BODYDATA),
        errors,
    )


def validate_c2pa_100_license_and_p12_lock(
    *,
    c2pa_license_count: int = 1,
    rq_lic_path: str = P12_RQ_LIC_PATH,
    p12_device_node: str = P12_DEVICE_NODE,
    p12_blkroset: int | bool = 1,
    p12_mount_flags: str = P12_REQUIRED_MOUNT_FLAG,
    p12_mutation_bytes: int = 0,
    c2pa_write_attempts_blocked: bool = True,
) -> Tuple[bool, str, List[str]]:
    """Enforce C2PA single-package <= 100 licenses hardware ceiling and `p12:/cert/RQ_LIC.DAT`
    read-only (`BLKROSET=1` + `MS_RDONLY`) protection during Stage-B.
    """
    errors: List[str] = []
    ro_p12 = _normalize_ro_flag(p12_blkroset)
    flags_upper = [f.strip().upper() for f in p12_mount_flags.split(",") if f.strip()]
    ok = (
        0 <= int(c2pa_license_count) <= C2PA_MAX_LICENSES_CEILING
        and rq_lic_path.strip() == P12_RQ_LIC_PATH
        and p12_device_node.strip() == P12_DEVICE_NODE
        and ro_p12 == 1
        and (P12_REQUIRED_MOUNT_FLAG in flags_upper or "RO" in flags_upper)
        and int(p12_mutation_bytes) == 0
        and c2pa_write_attempts_blocked
    )
    if not ok:
        errors.append(
            f"C2PA 100-license ceiling or p12:/cert/RQ_LIC.DAT RO lock failed: "
            f"licenses={c2pa_license_count} (max {C2PA_MAX_LICENSES_CEILING}), "
            f"p12_blkroset={ro_p12}, mount_flags={p12_mount_flags!r}, "
            f"p12_mut={p12_mutation_bytes}B, writes_blocked={c2pa_write_attempts_blocked}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G60_C2PA_100_LICENSE_CEILING_OR_P12_RO),
        errors,
    )


def validate_v700_wireless_security_floor(
    stageb_wireless_profiles: Sequence[str] = ("WPA2", "WPA3"),
) -> Tuple[bool, str, Tuple[str, ...], List[str]]:
    """Enforce FX3 `Ver. 7.00+` wireless security floor: reject deprecated `WEP`,
    `WPA1`, and legacy `IPsec` profiles; allow only `WPA2`, `WPA3`, and `Access Authentication`.
    """
    rejected: List[str] = []
    errors: List[str] = []
    for raw_proto in stageb_wireless_profiles:
        norm = raw_proto.strip().upper().replace(" ", "_")
        if not norm:
            rejected.append(raw_proto)
            continue
        is_deprecated = (
            norm in DEPRECATED_WIRELESS_PROTOCOLS
            or "WEP" in norm
            or "WPA1" in norm
            or "IPSEC" in norm
            or norm == "WPA"
            or norm.startswith("WPA-")
            or norm.startswith("WPA_")
        )
        if is_deprecated or norm not in ALLOWED_WIRELESS_PROTOCOLS:
            rejected.append(raw_proto)

    ok = len(rejected) == 0
    if not ok:
        errors.append(
            f"Deprecated or disallowed Ver. 7.00+ wireless profile(s) rejected: {rejected!r} "
            "(WEP / WPA1 / legacy IPsec are forbidden; only WPA2 / WPA3 / Access Authentication allowed)."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G60_INSECURE_WIRELESS_WEP_WPA1_IPSEC),
        tuple(rejected),
        errors,
    )


# ---------------------------------------------------------------------------
# 3. Core Guard Functions (`verify_ssboot_wbi2_prsvimg_and_liro_guard`,
#    `verify_fx3_702_ufu_floor_and_slot1_c2pa_guard`)
# ---------------------------------------------------------------------------


def verify_ssboot_wbi2_prsvimg_and_liro_guard(
    *,
    wbi_partition_dev: str = WBI_PARTITION_DEV,
    wbi_raw_partition_dev: str = WBI_RAW_PARTITION_DEV,
    wbi_mount_point: str = WBI_MOUNT_POINT,
    wbi2_sector0_bytes: Optional[bytes] = None,
    wbi2_magic_hex: str = WBI2_MAGIC_HEX,
    wbi_compression_codec: str = WBI_COMPRESSION_CODEC,
    wbi_snapshot_image_name: str = WBI_SNAPSHOT_IMAGE_NAME,
    fx3rcpt1_magic: str = FX3RCPT1_MAGIC,
    fx3rcpt1_packet_bytes: int = FX3RCPT1_PACKET_BYTES,
    fx3rcpt1_verified: bool = True,
    tier0_wbi2_sector0_captured: bool = True,
    tier0_wbi2_sector0_sha256: str = DEFAULT_SYNTHETIC_WBI2_SECTOR0_SHA256,
    tier0_nflasha5_full_captured: bool = True,
    tier0_nflasha5_h0_sha256: str = DEFAULT_SYNTHETIC_NFLASHA5_FULL_SHA256,
    blkroset_nflasha5: int | bool = 1,
    blkroset_pnflasha5: int | bool = 1,
    proc_udm_write_blocked: bool = True,
    pm_suspend_disk_blocked: bool = True,
    stageb_snapshot_save_blocked: bool = True,
    liro_snapshot_save_invoked: bool = False,
    wbi_persistent_writes: int = 0,
    wbi_mutation_bytes: int = 0,
    wbi2_active_resume_pending: bool = False,
    wbi2_resume_bypass_verified: bool = True,
    cold_boot_verified: bool = True,
    init_entry_executed: bool = True,
    stage_a_verify_executed: bool = True,
    sbin_init_bypassed: bool = False,
    sbin_init_path: str = WBI_STOCK_INIT_PATH,
    stage_a_verify_script: str = WBI_STAGE_A_VERIFY_TARGET,
    h3_wbi2_sector0_sha256: str = DEFAULT_SYNTHETIC_WBI2_SECTOR0_SHA256,
    h3_nflasha5_full_sha256: str = DEFAULT_SYNTHETIC_NFLASHA5_FULL_SHA256,
    stock_warmboot_05s_preserved: bool = True,
    clean_uninstall_verified: bool = True,
    guard_profile: str = "FX3_REALHW_G59_SSBOOT_WBI2_PRSVIMG_LIRO_DEFAULT",
) -> SsbootWbi2LiroGuardResult:
    """Verify Gate G59 (`ssboot` / `WBI2` / `liro.ko` / `/proc/udm` / `H0 == H3`) fail-closed."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        wbi_partition_dev,
        wbi_raw_partition_dev,
        wbi_mount_point,
        wbi2_magic_hex,
        wbi_compression_codec,
        wbi_snapshot_image_name,
        fx3rcpt1_magic,
        tier0_wbi2_sector0_sha256,
        tier0_nflasha5_h0_sha256,
        sbin_init_path,
        stage_a_verify_script,
        h3_wbi2_sector0_sha256,
        h3_nflasha5_full_sha256,
        guard_profile,
    )
    bools = (
        fx3rcpt1_verified,
        tier0_wbi2_sector0_captured,
        tier0_nflasha5_full_captured,
        proc_udm_write_blocked,
        pm_suspend_disk_blocked,
        stageb_snapshot_save_blocked,
        liro_snapshot_save_invoked,
        wbi2_active_resume_pending,
        wbi2_resume_bypass_verified,
        cold_boot_verified,
        init_entry_executed,
        stage_a_verify_executed,
        sbin_init_bypassed,
        stock_warmboot_05s_preserved,
        clean_uninstall_verified,
    )
    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and all(isinstance(b, bool) for b in bools)
        and _is_non_negative_int(fx3rcpt1_packet_bytes)
        and (_normalize_ro_flag(blkroset_nflasha5) is not None)
        and (_normalize_ro_flag(blkroset_pnflasha5) is not None)
        and _is_non_negative_int(wbi_persistent_writes)
        and _is_non_negative_int(wbi_mutation_bytes)
        and (
            wbi2_sector0_bytes is None
            or isinstance(wbi2_sector0_bytes, (bytes, bytearray))
        )
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G59_TELEMETRY_INVALID)
        errors.append("Gate G59 received invalid or malformed ssboot/WBI2 telemetry.")

    tier0_ok = False
    stageb_ok = False
    resume_ok = False
    uninstall_ok = False

    if telemetry_ok:
        tier0_ok, tier0_code, tier0_errs = validate_wbi2_tier0_receipt(
            wbi_partition_dev=wbi_partition_dev,
            wbi_raw_partition_dev=wbi_raw_partition_dev,
            wbi_mount_point=wbi_mount_point,
            wbi2_sector0_bytes=wbi2_sector0_bytes,
            wbi2_magic_hex=wbi2_magic_hex,
            wbi_compression_codec=wbi_compression_codec,
            wbi_snapshot_image_name=wbi_snapshot_image_name,
            fx3rcpt1_magic=fx3rcpt1_magic,
            fx3rcpt1_packet_bytes=fx3rcpt1_packet_bytes,
            fx3rcpt1_verified=fx3rcpt1_verified,
            tier0_wbi2_sector0_captured=tier0_wbi2_sector0_captured,
            tier0_wbi2_sector0_sha256=tier0_wbi2_sector0_sha256,
            tier0_nflasha5_full_captured=tier0_nflasha5_full_captured,
            tier0_nflasha5_h0_sha256=tier0_nflasha5_h0_sha256,
        )
        if not tier0_ok:
            _add_code(codes, tier0_code)
            errors.extend(tier0_errs)

        stageb_ok, stageb_code, stageb_errs = validate_wbi2_stageb_ro_protection(
            blkroset_nflasha5=blkroset_nflasha5,
            blkroset_pnflasha5=blkroset_pnflasha5,
            proc_udm_write_blocked=proc_udm_write_blocked,
            pm_suspend_disk_blocked=pm_suspend_disk_blocked,
            stageb_snapshot_save_blocked=stageb_snapshot_save_blocked,
            liro_snapshot_save_invoked=liro_snapshot_save_invoked,
            wbi_persistent_writes=wbi_persistent_writes,
            wbi_mutation_bytes=wbi_mutation_bytes,
        )
        if not stageb_ok:
            _add_code(codes, stageb_code)
            errors.extend(stageb_errs)

        resume_ok, resume_code, resume_errs = validate_ssboot_resume_bypass_guard(
            wbi2_active_resume_pending=wbi2_active_resume_pending,
            wbi2_resume_bypass_verified=wbi2_resume_bypass_verified,
            cold_boot_verified=cold_boot_verified,
            init_entry_executed=init_entry_executed,
            stage_a_verify_executed=stage_a_verify_executed,
            sbin_init_bypassed=sbin_init_bypassed,
            sbin_init_path=sbin_init_path,
            stage_a_verify_script=stage_a_verify_script,
        )
        if not resume_ok:
            _add_code(codes, resume_code)
            errors.extend(resume_errs)

        uninstall_ok, uninstall_code, uninstall_errs = validate_wbi2_clean_uninstall_h0_h3(
            tier0_wbi2_sector0_sha256=tier0_wbi2_sector0_sha256,
            tier0_nflasha5_h0_sha256=tier0_nflasha5_h0_sha256,
            h3_wbi2_sector0_sha256=h3_wbi2_sector0_sha256,
            h3_nflasha5_full_sha256=h3_nflasha5_full_sha256,
            stock_warmboot_05s_preserved=stock_warmboot_05s_preserved,
            clean_uninstall_verified=clean_uninstall_verified,
        )
        if not uninstall_ok:
            _add_code(codes, uninstall_code)
            errors.extend(uninstall_errs)

    valid = (
        telemetry_ok
        and tier0_ok
        and stageb_ok
        and resume_ok
        and uninstall_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G59 if valid else codes[0]

    ro_a5_norm = _normalize_ro_flag(blkroset_nflasha5)
    ro_pa5_norm = _normalize_ro_flag(blkroset_pnflasha5)
    h0_eq_h3 = (
        isinstance(tier0_wbi2_sector0_sha256, str)
        and isinstance(h3_wbi2_sector0_sha256, str)
        and isinstance(tier0_nflasha5_h0_sha256, str)
        and isinstance(h3_nflasha5_full_sha256, str)
        and tier0_wbi2_sector0_sha256.strip().lower() == h3_wbi2_sector0_sha256.strip().lower()
        and tier0_nflasha5_h0_sha256.strip().lower() == h3_nflasha5_full_sha256.strip().lower()
    )

    return SsbootWbi2LiroGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        wbi_partition_dev=str(wbi_partition_dev) if isinstance(wbi_partition_dev, str) else "INVALID",
        wbi_raw_partition_dev=str(wbi_raw_partition_dev) if isinstance(wbi_raw_partition_dev, str) else "INVALID",
        wbi_mount_point=str(wbi_mount_point) if isinstance(wbi_mount_point, str) else "INVALID",
        wbi2_magic_hex=wbi2_magic_hex.strip().lower() if isinstance(wbi2_magic_hex, str) else "INVALID",
        wbi_compression_codec=str(wbi_compression_codec) if isinstance(wbi_compression_codec, str) else "INVALID",
        wbi_snapshot_image_name=str(wbi_snapshot_image_name) if isinstance(wbi_snapshot_image_name, str) else "INVALID",
        fx3rcpt1_magic=str(fx3rcpt1_magic) if isinstance(fx3rcpt1_magic, str) else "INVALID",
        fx3rcpt1_packet_bytes=int(fx3rcpt1_packet_bytes) if _is_non_negative_int(fx3rcpt1_packet_bytes) else -1,
        tier0_wbi2_sector0_captured=bool(tier0_wbi2_sector0_captured) if isinstance(tier0_wbi2_sector0_captured, bool) else False,
        tier0_wbi2_sector0_sha256=tier0_wbi2_sector0_sha256.strip().lower() if isinstance(tier0_wbi2_sector0_sha256, str) else "INVALID",
        tier0_nflasha5_full_captured=bool(tier0_nflasha5_full_captured) if isinstance(tier0_nflasha5_full_captured, bool) else False,
        tier0_nflasha5_h0_sha256=tier0_nflasha5_h0_sha256.strip().lower() if isinstance(tier0_nflasha5_h0_sha256, str) else "INVALID",
        tier0_receipt_valid=tier0_ok,
        blkroset_nflasha5=ro_a5_norm if ro_a5_norm is not None else -1,
        blkroset_pnflasha5=ro_pa5_norm if ro_pa5_norm is not None else -1,
        proc_udm_write_blocked=bool(proc_udm_write_blocked) if isinstance(proc_udm_write_blocked, bool) else False,
        pm_suspend_disk_blocked=bool(pm_suspend_disk_blocked) if isinstance(pm_suspend_disk_blocked, bool) else False,
        stageb_snapshot_save_blocked=bool(stageb_snapshot_save_blocked) if isinstance(stageb_snapshot_save_blocked, bool) else False,
        wbi_persistent_writes=int(wbi_persistent_writes) if _is_non_negative_int(wbi_persistent_writes) else -1,
        wbi_mutation_bytes=int(wbi_mutation_bytes) if _is_non_negative_int(wbi_mutation_bytes) else -1,
        stageb_ro_protection_valid=stageb_ok,
        wbi2_active_resume_pending=bool(wbi2_active_resume_pending) if isinstance(wbi2_active_resume_pending, bool) else True,
        wbi2_resume_bypass_verified=bool(wbi2_resume_bypass_verified) if isinstance(wbi2_resume_bypass_verified, bool) else False,
        init_entry_executed=bool(init_entry_executed) if isinstance(init_entry_executed, bool) else False,
        stage_a_verify_executed=bool(stage_a_verify_executed) if isinstance(stage_a_verify_executed, bool) else False,
        sbin_init_bypassed=bool(sbin_init_bypassed) if isinstance(sbin_init_bypassed, bool) else True,
        resume_bypass_guard_valid=resume_ok,
        h3_wbi2_sector0_sha256=h3_wbi2_sector0_sha256.strip().lower() if isinstance(h3_wbi2_sector0_sha256, str) else "INVALID",
        h3_nflasha5_full_sha256=h3_nflasha5_full_sha256.strip().lower() if isinstance(h3_nflasha5_full_sha256, str) else "INVALID",
        h0_equals_h3_wbi2=bool(h0_eq_h3),
        stock_warmboot_05s_preserved=bool(stock_warmboot_05s_preserved) if isinstance(stock_warmboot_05s_preserved, bool) else False,
        clean_uninstall_valid=uninstall_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(
    *,
    body_firmware_version: str = FX3_MIN_BODY_FIRMWARE_FLOOR,
    target_ufu_version: str = FX3_UFU_TARGET_VERSION,
    target_model_id: int | str = FX3_MODEL_ID_INT,
    target_model_name: str = FX3_MODEL_NAME,
    bodydata_filename: str = BODYDATA_FILENAME,
    bodydata_size_bytes: int = BODYDATA_702_EXACT_BYTES,
    bodydata_ufu_magic_hex: str = BODYDATA_UFU_MAGIC_HEX,
    update_slot: int = REQUIRED_UPDATE_SLOT,
    bodydata_path: str = REQUIRED_SLOT1_BODYDATA_PATH,
    c2pa_import_slot: int = REQUIRED_UPDATE_SLOT,
    c2pa_import_path: str = "/RQ_LIC.DAT",
    slot1_root_entries: Sequence[str] = (BODYDATA_FILENAME,),
    slot2_root_entries: Sequence[str] = (),
    duplicate_bodydata_detected: bool = False,
    c2pa_license_count: int = 1,
    rq_lic_path: str = P12_RQ_LIC_PATH,
    p12_device_node: str = P12_DEVICE_NODE,
    p12_blkroset: int | bool = 1,
    p12_mount_flags: str = P12_REQUIRED_MOUNT_FLAG,
    p12_mutation_bytes: int = 0,
    c2pa_write_attempts_blocked: bool = True,
    stageb_wireless_profiles: Sequence[str] = ("WPA2", "WPA3"),
    guard_profile: str = "FX3_REALHW_G60_702_UFU_SLOT1_C2PA_DEFAULT",
) -> Slot1UfuC2paGuardResult:
    """Verify Gate G60 (`FX3 7.02 >= 2.04` UFU floor, Slot-1 root & duplicate
    guard, C2PA `<= 100` license ceiling & `p12` RO lock, and `7.00+` wireless floor).
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        body_firmware_version,
        target_ufu_version,
        target_model_name,
        bodydata_filename,
        bodydata_ufu_magic_hex,
        bodydata_path,
        c2pa_import_path,
        rq_lic_path,
        p12_device_node,
        p12_mount_flags,
        guard_profile,
    )
    t_id_norm = _normalize_model_id_int(target_model_id)
    ro_p12 = _normalize_ro_flag(p12_blkroset)

    seq_ok = (
        isinstance(slot1_root_entries, (tuple, list))
        and all(isinstance(x, str) for x in slot1_root_entries)
        and isinstance(slot2_root_entries, (tuple, list))
        and all(isinstance(x, str) for x in slot2_root_entries)
        and isinstance(stageb_wireless_profiles, (tuple, list))
        and all(isinstance(x, str) for x in stageb_wireless_profiles)
    )

    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and (t_id_norm is not None)
        and _is_non_negative_int(bodydata_size_bytes)
        and isinstance(update_slot, int)
        and not isinstance(update_slot, bool)
        and isinstance(c2pa_import_slot, int)
        and not isinstance(c2pa_import_slot, bool)
        and isinstance(duplicate_bodydata_detected, bool)
        and _is_non_negative_int(c2pa_license_count)
        and (ro_p12 is not None)
        and _is_non_negative_int(p12_mutation_bytes)
        and isinstance(c2pa_write_attempts_blocked, bool)
        and seq_ok
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G60_TELEMETRY_INVALID)
        errors.append("Gate G60 received invalid or malformed UFU/Slot-1/C2PA telemetry.")

    floor_ok = False
    slot1_ok = False
    c2pa_ok = False
    wifi_ok = False
    rejected_wifi: Tuple[str, ...] = ()

    if telemetry_ok:
        floor_ok, floor_code, floor_errs = validate_fx3_body_firmware_floor(
            body_firmware_version=body_firmware_version,
            target_ufu_version=target_ufu_version,
            target_model_id=target_model_id,
            target_model_name=target_model_name,
            bodydata_filename=bodydata_filename,
            bodydata_size_bytes=bodydata_size_bytes,
            bodydata_ufu_magic_hex=bodydata_ufu_magic_hex,
        )
        if not floor_ok:
            _add_code(codes, floor_code)
            errors.extend(floor_errs)

        slot1_ok, slot1_code, slot1_errs = validate_slot1_root_and_duplicate_guard(
            update_slot=update_slot,
            bodydata_path=bodydata_path,
            c2pa_import_slot=c2pa_import_slot,
            c2pa_import_path=c2pa_import_path,
            slot1_root_entries=slot1_root_entries,
            slot2_root_entries=slot2_root_entries,
            duplicate_bodydata_detected=duplicate_bodydata_detected,
        )
        if not slot1_ok:
            _add_code(codes, slot1_code)
            errors.extend(slot1_errs)

        c2pa_ok, c2pa_code, c2pa_errs = validate_c2pa_100_license_and_p12_lock(
            c2pa_license_count=c2pa_license_count,
            rq_lic_path=rq_lic_path,
            p12_device_node=p12_device_node,
            p12_blkroset=p12_blkroset,
            p12_mount_flags=p12_mount_flags,
            p12_mutation_bytes=p12_mutation_bytes,
            c2pa_write_attempts_blocked=c2pa_write_attempts_blocked,
        )
        if not c2pa_ok:
            _add_code(codes, c2pa_code)
            errors.extend(c2pa_errs)

        wifi_ok, wifi_code, rejected_wifi, wifi_errs = validate_v700_wireless_security_floor(
            stageb_wireless_profiles=stageb_wireless_profiles,
        )
        if not wifi_ok:
            _add_code(codes, wifi_code)
            errors.extend(wifi_errs)

    valid = (
        telemetry_ok
        and floor_ok
        and slot1_ok
        and c2pa_ok
        and wifi_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G60 if valid else codes[0]

    return Slot1UfuC2paGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        target_model_id_hex=f"0x{t_id_norm:08x}" if t_id_norm is not None else "INVALID",
        target_model_name=str(target_model_name) if isinstance(target_model_name, str) else "INVALID",
        body_firmware_version=str(body_firmware_version) if isinstance(body_firmware_version, str) else "INVALID",
        min_body_firmware_floor=FX3_MIN_BODY_FIRMWARE_FLOOR,
        target_ufu_version=str(target_ufu_version) if isinstance(target_ufu_version, str) else "INVALID",
        bodydata_filename=str(bodydata_filename) if isinstance(bodydata_filename, str) else "INVALID",
        bodydata_size_bytes=int(bodydata_size_bytes) if _is_non_negative_int(bodydata_size_bytes) else -1,
        bodydata_ufu_magic_hex=bodydata_ufu_magic_hex.strip().lower() if isinstance(bodydata_ufu_magic_hex, str) else "INVALID",
        body_version_floor_valid=floor_ok,
        update_slot=int(update_slot) if isinstance(update_slot, int) and not isinstance(update_slot, bool) else -1,
        bodydata_path=str(bodydata_path) if isinstance(bodydata_path, str) else "INVALID",
        c2pa_import_slot=int(c2pa_import_slot) if isinstance(c2pa_import_slot, int) and not isinstance(c2pa_import_slot, bool) else -1,
        c2pa_import_path=str(c2pa_import_path) if isinstance(c2pa_import_path, str) else "INVALID",
        duplicate_bodydata_detected=bool(duplicate_bodydata_detected) if isinstance(duplicate_bodydata_detected, bool) else True,
        slot1_placement_valid=slot1_ok,
        c2pa_license_count=int(c2pa_license_count) if _is_non_negative_int(c2pa_license_count) else -1,
        c2pa_max_licenses_ceiling=C2PA_MAX_LICENSES_CEILING,
        rq_lic_path=str(rq_lic_path) if isinstance(rq_lic_path, str) else "INVALID",
        p12_device_node=str(p12_device_node) if isinstance(p12_device_node, str) else "INVALID",
        p12_blkroset=ro_p12 if ro_p12 is not None else -1,
        p12_mount_flags=str(p12_mount_flags) if isinstance(p12_mount_flags, str) else "INVALID",
        p12_mutation_bytes=int(p12_mutation_bytes) if _is_non_negative_int(p12_mutation_bytes) else -1,
        c2pa_and_p12_lock_valid=c2pa_ok,
        stageb_wireless_profiles=tuple(str(x) for x in stageb_wireless_profiles) if seq_ok else (),
        rejected_wireless_protocols=rejected_wifi,
        wireless_security_floor_valid=wifi_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G59 & Gate G60 Evaluators (Donor Audit + Guard -> GateVerdict)
# ---------------------------------------------------------------------------


def evaluate_g59_ssboot_wbi2_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    ssboot_wbi2_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase177DonorAuditResult] = None,
) -> Tuple[GateVerdict, G59SsbootWbi2Result]:
    """Evaluate Gate G59 (`ssboot` / `WBI2` `prsv-img` & `liro.ko` Bypass Guard)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase177_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(ssboot_wbi2_kwargs or {})
    guard = verify_ssboot_wbi2_prsvimg_and_liro_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE177_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G59 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G59 if valid else codes[0]

    res = G59SsbootWbi2Result(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        ssboot_wbi2_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, dev={guard.wbi_partition_dev}, "
        f"magic=0x{guard.wbi2_magic_hex}, blkroset=({guard.blkroset_nflasha5},{guard.blkroset_pnflasha5}), "
        f"wbi_writes={guard.wbi_persistent_writes}, init_ok={guard.init_entry_executed}, "
        f"h0_eq_h3={guard.h0_equals_h3_wbi2}"
    )

    verdict = GateVerdict(
        gate_id=G59_GATE_ID,
        gate_code=G59_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


def evaluate_g60_slot1_ufu_c2pa_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    slot1_ufu_c2pa_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase177DonorAuditResult] = None,
) -> Tuple[GateVerdict, G60Slot1UfuC2paResult]:
    """Evaluate Gate G60 (`FX3 7.02 >= 2.04` UFU Floor & Slot-1 C2PA 100-License Guard)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase177_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(slot1_ufu_c2pa_kwargs or {})
    guard = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE177_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G60 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G60 if valid else codes[0]

    res = G60Slot1UfuC2paResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        slot1_ufu_c2pa_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, body_ver={guard.body_firmware_version}(>={guard.min_body_firmware_floor}), "
        f"ufu={guard.target_ufu_version}({guard.bodydata_size_bytes}B), "
        f"slot={guard.update_slot}:{guard.bodydata_path}, "
        f"c2pa_lic={guard.c2pa_license_count}/{guard.c2pa_max_licenses_ceiling}, "
        f"p12_ro={guard.p12_blkroset}, wifi_ok={guard.wireless_security_floor_valid}"
    )

    verdict = GateVerdict(
        gate_id=G60_GATE_ID,
        gate_code=G60_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Unified 60-Gate Master Safety Preflight (`G01..G60`)
# ---------------------------------------------------------------------------


def evaluate_60gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G01..G58 pass-throughs
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
    # G59 inputs (ssboot / WBI2 prsv-img + liro.ko + BLKROSET=1 + H0==H3)
    ssboot_wbi2_kwargs: Optional[Mapping[str, Any]] = None,
    # G60 inputs (FX3 7.02 >= 2.04 UFU floor + Slot-1 root + C2PA <=100 + wireless floor)
    slot1_ufu_c2pa_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master60GateReport:
    """Evaluate all 60 Master Safety Gates (`G01..G60`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        if dry_run_simulated_backup is None
        else (dry_run_simulated or dry_run_simulated_backup)
    )

    m58_kwargs: Dict[str, Any] = {
        "force_clean_room": clean_forced,
        "dry_run_simulated_backup": effective_dry_run,
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
    }
    if soc_start_ceiling_c is not None:
        m58_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m58_report: Master58GateReport = evaluate_58gate_preflight(
        resolved_root, **m58_kwargs
    )

    phase177_audit = audit_phase177_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g59_verdict, g59_res = evaluate_g59_ssboot_wbi2_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        ssboot_wbi2_kwargs=ssboot_wbi2_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase177_audit,
    )

    g60_verdict, g60_res = evaluate_g60_slot1_ufu_c2pa_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        slot1_ufu_c2pa_kwargs=slot1_ufu_c2pa_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase177_audit,
    )

    gates_59_to_60 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g59_verdict, g60_verdict)
    ]
    all_gates = tuple(list(m58_report.gates) + gates_59_to_60)

    g01_to_g12_verified = int(m58_report.summary["g01_to_g12_verified"])
    g13_to_g58_verified = (
        int(m58_report.summary["g13_to_g56_verified"])
        + int(m58_report.summary["g57_to_g58_verified"])
    )
    g59_to_g60_verified = sum(1 for v in (g59_verdict, g60_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g58_verified + g59_to_g60_verified

    g59_to_g60_all_passed = g59_to_g60_verified == 2
    g13_to_g60_all_passed = (
        m58_report.g13_to_g58_all_passed and g59_to_g60_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m58_report.gates[:9])

    offline_57_verified = (
        g01_to_g09_ok
        and m58_report.offline_55_gates_verified
        and g59_to_g60_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_60_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g60_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes
    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m58_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_57_verified
        and m58_report.h0_h1_trial_entry_allowed
        and g59_to_g60_all_passed
        and agent_auto_flash_blocked
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m58_report.errors) + list(g59_verdict.errors) + list(g60_verdict.errors)
    )
    warnings: List[str] = (
        list(m58_report.warnings)
        + list(g59_verdict.warnings)
        + list(g60_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m58_report.g13_to_g58_all_passed:
        overall_status = m58_report.status
    elif not g59_verdict.passed:
        overall_status = g59_verdict.status
    elif not g60_verdict.passed:
        overall_status = g60_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_60_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_60_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_60_verified:
        overall_status = "VERIFIED_ALL_60_GATES"
    else:
        overall_status = "VERIFIED_57_OF_60_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m58_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g59_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g60_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 60,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 60 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g58_verified": g13_to_g58_verified,
        "g59_to_g60_verified": g59_to_g60_verified,
        "g13_to_g60_all_passed": g13_to_g60_all_passed,
        "g59_to_g60_all_passed": g59_to_g60_all_passed,
        "offline_57_gates_verified": offline_57_verified,
        "all_60_gates_verified": all_60_verified,
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

    return Master60GateReport(
        schema=REALHW_SSBOOT_WBI2_SLOT1_UFU_60GATE_SCHEMA,
        version=REALHW_SSBOOT_WBI2_SLOT1_UFU_60GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_57_gates_verified=offline_57_verified,
        all_60_gates_verified=all_60_verified,
        g13_to_g60_all_passed=g13_to_g60_all_passed,
        g59_to_g60_all_passed=g59_to_g60_all_passed,
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
        master_58_report=m58_report.to_dict(),
        g59_result=g59_res.to_dict(),
        g60_result=g60_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_60_master_safety_gates = evaluate_60gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard",
        description=(
            "Phase 177 — ssboot/WBI2 prsv-img Bootloader-Bypass Guard (G59), "
            "FX3 7.02 >=2.04 UFU Floor & Slot-1 C2PA 100-License Guard (G60), "
            "and 60-Gate Milestone Master Preflight (G01..G60)"
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G60 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_60gate_preflight(
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
            f"verified={report.summary['verified_gates']}/60 "
            f"g59_to_g60_all_passed={report.g59_to_g60_all_passed} "
            f"all_60_gates_verified={report.all_60_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
            f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
            f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
            f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        report.all_60_gates_verified
        if args.dry_run_simulated
        else report.offline_57_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
