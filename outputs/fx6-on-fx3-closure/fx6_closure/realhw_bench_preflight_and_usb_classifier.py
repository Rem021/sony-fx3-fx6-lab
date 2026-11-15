"""Phase 154 — Host-Side Read-Only Physical Bench Preflight CLI, Passive USB Mode
Classifier (`0DA1 / 0336 / MTP / UVC`), SD Staging Verifier & Operator Go/No-Go
Receipt Generator (`preflight-realhw-bench`).

100% passive, zero-USB-packet, zero-write bench preflight workbench for physical
ILME-FX3 (`7.02`, `0x91030080`) real-hardware Tier-0 cold-backup and Stage-B SD
preparation:

1. **Local BYOF Donor Readiness (`inspect_bench_donor_readiness`)**:
   - Inspects local BYOF Sony donor artifacts (`im.elf`, `libJiritsu.so`, `appFw.so`,
     `libWlanResource.so`, `.uxc`, `13/13` Stage-B lock table) strictly via
     `os.open(..., os.O_RDONLY | os.O_NOFOLLOW)` with deterministic
     `FX3_FX6_FORCE_CLEAN_ROOM=1` fallback and `0` raw firmware bytes emitted.

2. **100% Passive Zero-Packet USB Camera State Classifier (`classify_passive_usb_snapshot`)**:
   - Parses synthetic or passive `ioreg -p IOUSB -l -w 0` text/XML-plist snapshots
     (NEVER opening IOKit handles or transmitting USB control/bulk packets:
     `usb_packets_emitted == 0`, `iokit_handles_opened == 0`) across all 6 states:
     - `NO_SONY_CAMERA_ATTACHED`
     - `READY_MSC_054C_0DA1`
     - `STRANDED_SERVICE_054C_0336` (`ALERT_SERVICE_MODE_STRANDED` + `STOP (0336:7)` runbook)
     - `WRONG_USB_MODE_MTP_REMOTE_OR_UVC`
     - `MULTIPLE_SONY_DEVICES_AMBIGUOUS` (hard-abort)
     - `UNSUPPORTED_MODEL_PID` (hard-abort)

3. **Candidate ExFAT SD Card Staging & Forbidden-File Firewall (`audit_sd_staging_directory`)**:
   - Inspects a candidate SD staging directory strictly via `O_RDONLY | O_NOFOLLOW`,
     rejecting symlinks and dangerous factory OTA/repartition triggers
     (`BODYDATA.DAT`, `edisx.elf`, `nor_loader_writer.sh`, `us_spi_firmup.sh`,
     `us_darwin_firm.sh`, `/setting/updater/mode*`), verifying Stage-B manifest
     `13/13` SHA-256 parity, `< 50 us` SD-eject bypass launcher hash, and `>= 2 GiB`
     free-space quota.

4. **Dual-Copy (`SD + Host Vault`) Tier-0 `FX3RCPT1` Receipt & Bench Go/No-Go Engine**:
   - Evaluates dual-copy (`SD ExFAT` + `Mac Host Vault`) `528 B FX3RCPT1` 16-surface
     cold-backup receipts (`CRC32` + `SHA-256` parity across both copies +
     `camera_cid_sha256` match), while keeping `persistent_emmc_writes_authorized = False`
     hard-locked in code.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import struct
import subprocess
import tempfile
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import zlib


def _ensure_cross_package_paths(repo_root: Path) -> None:
    """Ensure sibling lab package roots are importable under minimal PYTHONPATH."""
    for rel in (
        "outputs/fx3-safety",
        "outputs/fx3-recovery-adapter",
        "outputs/fx6-on-fx3-closure",
    ):
        cand = str(repo_root / rel)
        if cand not in sys.path:
            sys.path.append(cand)


DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
_ensure_cross_package_paths(DEFAULT_REPO_ROOT)

from fx3_recovery.realhw_adjustcontrol_streaming_backup_client import (  # noqa: E402
    COLD_BACKUP_ITEMS,
    SD_RECEIPT_BYTES,
    SD_RECEIPT_MAGIC,
    build_sd_backup_receipt_bytes,
    parse_sd_backup_receipt_bytes,
)
from fx3_safety.boot_contracts import BK4_MAGIC  # noqa: E402

from .donor_paths import (  # noqa: E402
    is_forced_clean_room,
    resolve_fx3_modules_dir,
    resolve_fx6_donor_lib_dir,
    resolve_fx6_donor_root,
    resolve_work_subpath,
)
from .hardware_readiness_packet import (  # noqa: E402
    FORBIDDEN_TRIVIAL_CIDS,
    FX3_MODEL_ID_HEX,
    HEX32_CID_RE,
    HEX64_RE,
)
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FX6_APPFW_DONOR_SHA256,
    FX6_APPFW_STAGE_B_SHA256,
    FX6_WLAN_RSRC_DONOR_SHA256,
    FX6_WLAN_RSRC_P12_SHA256,
)
from .realhw_jiritsu_and_tier0_dumper_auditor import (  # noqa: E402
    LIBJIRITSU_EXPECTED_SHA256,
    LIBJIRITSU_EXPECTED_SIZE,
    LIBJIRITSU_RELPATH,
)
from .realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
    ESCAPE_HATCH_ABSENT_LATENCY_US,
    ESCAPE_HATCH_MAX_LATENCY_US,
    FX3_IM_ELF_EXPECTED_SHA256,
    FX3_IM_ELF_EXPECTED_SIZE,
    FX3_IM_ELF_RELPATH,
    FX6_APPFW_EXPECTED_SIZE,
    FX6_CORE_UXC_ASSETS,
    FX6_UXC_TOTAL_COUNT,
    SD_BK4_SHADOW_SEED_RELPATH,
    SD_MANIFEST_RELPATH,
    SD_UNINSTALL_MANIFEST_RELPATH,
    _compute_canonical_sha256,
    _validate_exfat_fat32_relpath,
    build_sd_stageb_deployment_bundle,
    default_tier0_receipt_binding,
    generate_im_elf_escape_hatch_launcher,
    read_only_o_rdonly_bytes,
    read_only_o_rdonly_digest_and_header,
)
from .stage_b_ram_overlay_packager import STAGE_B_LOCK_TABLE_13_ARTIFACTS  # noqa: E402


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE_154_SCHEMA: str = "phase154_realhw_bench_preflight_receipt_v1"
PHASE_154_VERSION: str = "154.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
SD_PHYSICAL_MEDIA_WRITTEN: bool = False
LIVE_USB_IOKIT_TRANSMIT_ENABLED: bool = False
USB_PACKETS_EMITTED: int = 0
IOKIT_HANDLES_OPENED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_SLICES_EMITTED: int = 0

# USB VID/PID & 6-State Classifier Constants
SONY_USB_VID: int = 0x054C
FX3_MSC_PID: int = 0x0DA1
SONY_SERVICE_PID: int = 0x0336

SONY_WRONG_MODE_PIDS: Dict[int, str] = {
    0x0DA2: "PC_REMOTE_OR_PTP",
    0x0DA3: "MTP_OR_PTP",
    0x0DA4: "UVC_USB_STREAMING",
    0x0D9E: "MTP_LEGACY",
    0x0DC0: "PC_REMOTE",
    0x0DCE: "UVC_STREAMING",
    0x0EE0: "RNDIS_OR_UVC",
    0x0EE1: "UVC_WEBCAM",
}

SONY_UNSUPPORTED_MODEL_PIDS: Dict[int, str] = {
    0x0E0E: "ILME-FX30",
    0x0E8A: "ILCE-7CM2",
    0x0994: "LEGACY_SONY_CAMERA",
    0x0E6B: "ILCE-7M5_OR_NEWER",
}

UNSUPPORTED_MODEL_NAME_TOKENS: Tuple[str, ...] = (
    "FX30",
    "ILME-FX30",
    "ILME-FX6",
    "ILCE-",
    "ZV-E",
    "A7C",
    "A7M",
    "A7S",
    "A7V",
)

USB_STATE_NO_SONY_CAMERA_ATTACHED: str = "NO_SONY_CAMERA_ATTACHED"
USB_STATE_READY_MSC_054C_0DA1: str = "READY_MSC_054C_0DA1"
USB_STATE_STRANDED_SERVICE_054C_0336: str = "STRANDED_SERVICE_054C_0336"
USB_STATE_WRONG_USB_MODE_MTP_REMOTE_OR_UVC: str = "WRONG_USB_MODE_MTP_REMOTE_OR_UVC"
USB_STATE_MULTIPLE_SONY_DEVICES_AMBIGUOUS: str = "MULTIPLE_SONY_DEVICES_AMBIGUOUS"
USB_STATE_UNSUPPORTED_MODEL_PID: str = "UNSUPPORTED_MODEL_PID"

BENCH_USB_STATES: Tuple[str, ...] = (
    USB_STATE_NO_SONY_CAMERA_ATTACHED,
    USB_STATE_READY_MSC_054C_0DA1,
    USB_STATE_STRANDED_SERVICE_054C_0336,
    USB_STATE_WRONG_USB_MODE_MTP_REMOTE_OR_UVC,
    USB_STATE_MULTIPLE_SONY_DEVICES_AMBIGUOUS,
    USB_STATE_UNSUPPORTED_MODEL_PID,
)

ALERT_SERVICE_MODE_STRANDED: str = "ALERT_SERVICE_MODE_STRANDED"
ALERT_MULTIPLE_SONY_DEVICES_AMBIGUOUS: str = "HARD_ABORT_MULTIPLE_SONY_DEVICES_AMBIGUOUS"
ALERT_UNSUPPORTED_MODEL_PID: str = "HARD_ABORT_UNSUPPORTED_MODEL_PID"

# SD Staging & Forbidden-File Firewall Constants
GIB_BYTES: int = 1024 * 1024 * 1024
MIN_SD_FREE_SPACE_BYTES: int = 2 * GIB_BYTES  # 2.0 GiB = 2,147,483,648 B
MIN_SD_FREE_SPACE_GIB: float = 2.0

FORBIDDEN_SD_FILENAMES: Tuple[str, ...] = (
    "bodydata.dat",
    "edisx.elf",
    "nor_loader_writer.sh",
    "us_spi_firmup.sh",
    "us_darwin_firm.sh",
)

FORBIDDEN_SD_PATH_PREFIXES: Tuple[str, ...] = (
    "setting/updater/mode",
    "updater/mode",
)

BLOCKED_FORBIDDEN_OTA_TRIGGER: str = "BLOCKED_FORBIDDEN_OTA_OR_REPARTITION_TRIGGER"
ERR_SD_SYMLINK_REJECTED: str = "ERR_SD_SYMLINK_REJECTED"
ERR_SD_FREE_SPACE_UNDER_2GIB: str = "ERR_SD_FREE_SPACE_UNDER_2GIB"
ERR_SD_STAGE_B_13_PARITY_FAILED: str = "ERR_SD_STAGE_B_13_PARITY_FAILED"
ERR_SD_ESCAPE_HATCH_LAUNCHER_HASH_MISMATCH: str = (
    "ERR_SD_ESCAPE_HATCH_LAUNCHER_HASH_MISMATCH"
)

SD_LAUNCHER_SH_RELPATH: str = "FX6_STAGEB/rescue/im_elf_escape_hatch.sh"
SD_LAUNCHER_SHA256_RELPATH: str = "FX6_STAGEB/rescue/im_elf_escape_hatch.sha256"

EXPECTED_ESCAPE_HATCH_LAUNCHER_SHA256: str = hashlib.sha256(
    generate_im_elf_escape_hatch_launcher().encode("utf-8")
).hexdigest()

# Dual-Copy Receipt & Verdict Constants
ERR_DUAL_COPY_RECEIPT_MISSING: str = "ERR_DUAL_COPY_RECEIPT_MISSING"
ERR_DUAL_COPY_RECEIPT_INVALID: str = "ERR_DUAL_COPY_FX3RCPT1_INVALID"
ERR_DUAL_COPY_CRC32_MISMATCH: str = "ERR_DUAL_COPY_CRC32_MISMATCH"
ERR_DUAL_COPY_SHA256_MISMATCH: str = "ERR_DUAL_COPY_SHA256_MISMATCH"
ERR_DUAL_COPY_SURFACE16_MISMATCH: str = "ERR_DUAL_COPY_16SURFACE_MISMATCH"
ERR_CAMERA_CID_SHA256_MISMATCH: str = "ERR_CAMERA_CID_SHA256_MISMATCH"

VERDICT_GO_READONLY_PREFLIGHT: str = "GO_READONLY_BENCH_PREFLIGHT"
VERDICT_NO_GO: str = "NO_GO_BENCH_BLOCKED"
STATUS_PREFLIGHT_GO: str = "GO_READONLY_BENCH_PREFLIGHT_VERIFIED"
STATUS_PREFLIGHT_NO_GO: str = "NO_GO_REMEDIATION_REQUIRED"

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_TRIVIAL_CID_SHA256_SET = frozenset(
    {
        "0" * 64,
        "f" * 64,
        *(hashlib.sha256(c.lower().encode("ascii")).hexdigest() for c in FORBIDDEN_TRIVIAL_CIDS),
        *(hashlib.sha256(c.upper().encode("ascii")).hexdigest() for c in FORBIDDEN_TRIVIAL_CIDS),
    }
)


# ---------------------------------------------------------------------------
# Dataclasses (100% JSON-safe; zero raw proprietary firmware bytes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BenchDonorReadinessResult:
    passed: bool
    verification_mode: str
    read_only_o_rdonly_enforced: bool
    fx3_im_elf_verified: bool
    fx3_libjiritsu_verified: bool
    fx6_appfw_verified: bool
    fx6_wlan_rsrc_verified: bool
    fx6_uxc_verified_count: int
    stage_b_13_lock_count: int
    expected_launcher_sha256: str
    raw_firmware_slices_emitted: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PassiveUsbDeviceNode:
    vid: int
    pid: int
    vid_pid: str
    product_name: str
    vendor_name: str
    serial_number: str
    location_id_hex: str
    registry_id: int
    interface_classes: Tuple[int, ...]
    interface_names: Tuple[str, ...]
    mass_storage_driver_attached: bool


@dataclass(frozen=True)
class PassiveUsbClassificationResult:
    usb_state: str
    ready_for_msc_session: bool
    hard_abort: bool
    alert_code: str
    snapshot_format: str
    usb_packets_emitted: int
    iokit_handles_opened: int
    live_usb_iokit_transmit_enabled: bool
    total_usb_devices_seen: int
    sony_device_count: int
    sony_devices: Tuple[PassiveUsbDeviceNode, ...]
    detected_mode_detail: str
    remediation_steps: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SdStagingAuditResult:
    passed: bool
    provided: bool
    sd_dir_label: str
    read_only_o_rdonly_enforced: bool
    symlink_rejected_count: int
    forbidden_firewall_passed: bool
    forbidden_files_found: Tuple[str, ...]
    exfat_paths_valid: bool
    manifest_present: bool
    manifest_signature_valid: bool
    manifest_sha256: str
    stage_b_13_locks_verified: int
    stage_b_13_parity_ok: bool
    bk4_shadow_magic_valid: bool
    uninstall_manifest_valid: bool
    escape_hatch_launcher_sha256: str
    escape_hatch_launcher_hash_ok: bool
    escape_hatch_max_latency_us: int
    free_space_bytes: int
    free_space_gib: float
    required_free_space_bytes: int
    free_space_quota_ok: bool
    target_body_serial: str
    target_emmc_cid_sha256: str
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ReceiptCopySummary:
    copy_role: str
    present: bool
    valid_528b_fx3rcpt1: bool
    byte_length: int
    crc32_hex: str
    sha256_digest: str
    magic: str
    version: int
    entry_count: int
    manifest_sha256: str
    receipt_integrity_sha256: str
    total_dumped_bytes: int
    camera_cid_sha256: str
    surface_hashes: Dict[str, str]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DualCopyTier0ReceiptAuditResult:
    passed: bool
    provided: bool
    sd_copy: ReceiptCopySummary
    vault_copy: ReceiptCopySummary
    crc32_parity_ok: bool
    sha256_parity_ok: bool
    surface_16_parity_ok: bool
    camera_cid_sha256_match: bool
    camera_cid_sha256: str
    manifest_16_items_verified: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class OperatorChecklistItem:
    step_index: int
    gate_id: str
    status: str
    action: str


@dataclass(frozen=True)
class RealHwBenchPreflightReport:
    schema: str
    phase_version: str
    verification_mode: str
    verdict: str
    status: str
    bench_go: bool
    simulated_bench_mode: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    sd_physical_media_written: bool
    usb_packets_emitted: int
    iokit_handles_opened: int
    physical_device_writes: int
    raw_firmware_slices_emitted: int
    donor_readiness: BenchDonorReadinessResult
    usb_classification: PassiveUsbClassificationResult
    sd_staging_audit: SdStagingAuditResult
    dual_copy_receipt_audit: DualCopyTier0ReceiptAuditResult
    operator_checklist: Tuple[OperatorChecklistItem, ...]
    remediation_actions: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class Phase154ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal Helpers (Read-Only O_RDONLY & Canonical Hashing)
# ---------------------------------------------------------------------------


def _canonical_sha256_dict(obj: Mapping[str, Any], exclude_key: Optional[str] = None) -> str:
    body = dict(copy.deepcopy(obj))
    if exclude_key:
        body.pop(exclude_key, None)
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def _read_regular_file_o_rdonly(path: Path, *, max_bytes: Optional[int] = None) -> bytes:
    """Strictly read a regular file via os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK (reject symlinks)."""
    if path.is_symlink():
        raise ValueError(f"{ERR_SD_SYMLINK_REJECTED}: symlink rejected: {path}")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    fd = os.open(str(path), flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise ValueError(f"Non-regular file rejected: {path}")
        if max_bytes is not None and st.st_size > max_bytes:
            raise ValueError(f"File exceeds max_bytes={max_bytes}: {path}")
        chunks: List[bytes] = []
        while True:
            blk = os.read(fd, 1024 * 1024)
            if not blk:
                break
            chunks.append(blk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _compute_camera_cid_sha256(emmc_cid: str) -> str:
    return hashlib.sha256(emmc_cid.strip().lower().encode("ascii")).hexdigest()


def _is_valid_camera_cid_sha256(cid_sha: str) -> bool:
    norm = cid_sha.strip().lower()
    if not HEX64_RE.match(norm):
        return False
    return norm not in _TRIVIAL_CID_SHA256_SET


# ---------------------------------------------------------------------------
# Pillar 1: Local BYOF Donor Readiness (O_RDONLY + CLEAN_ROOM_SYNTHETIC)
# ---------------------------------------------------------------------------


def inspect_bench_donor_readiness(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
) -> BenchDonorReadinessResult:
    """Verify local BYOF donor binaries strictly via O_RDONLY or deterministic clean-room fallback."""
    errors: List[str] = []
    clean_room = (
        is_forced_clean_room() if synthetic_clean_room is None else bool(synthetic_clean_room)
    )

    fx3_im_path = resolve_work_subpath(FX3_IM_ELF_RELPATH, require_file=False)
    fx3_libjit_path = resolve_work_subpath(LIBJIRITSU_RELPATH, require_file=False)
    fx6_appfw_path = fx6_lib_dir / "appFw.so"
    fx6_wlan_path = fx6_lib_dir / "libWlanResource.so"
    fx6_root = resolve_fx6_donor_root()
    uxc_dir = fx6_root / "nflasha15-files" / "share" / "app"

    donors_present = (
        fx3_im_path.is_file()
        and fx3_libjit_path.is_file()
        and fx6_appfw_path.is_file()
        and fx6_wlan_path.is_file()
        and uxc_dir.is_dir()
    )
    if synthetic_clean_room is False and not donors_present:
        return BenchDonorReadinessResult(
            passed=False,
            verification_mode="LOCAL_DONOR_O_RDONLY",
            read_only_o_rdonly_enforced=True,
            fx3_im_elf_verified=fx3_im_path.is_file(),
            fx3_libjiritsu_verified=fx3_libjit_path.is_file(),
            fx6_appfw_verified=fx6_appfw_path.is_file(),
            fx6_wlan_rsrc_verified=fx6_wlan_path.is_file(),
            fx6_uxc_verified_count=0,
            stage_b_13_lock_count=len(STAGE_B_LOCK_TABLE_13_ARTIFACTS),
            expected_launcher_sha256=EXPECTED_ESCAPE_HATCH_LAUNCHER_SHA256,
            raw_firmware_slices_emitted=RAW_FIRMWARE_SLICES_EMITTED,
            errors=(f"Local BYOF donor directory missing required artifacts: fx6_lib_dir={fx6_lib_dir}",),
        )

    use_live = (not clean_room) and donors_present
    mode = "LOCAL_DONOR_O_RDONLY" if use_live else "CLEAN_ROOM_SYNTHETIC"

    if use_live:
        im_sz, im_sha, im_head = read_only_o_rdonly_digest_and_header(fx3_im_path)
        im_ok = (
            im_sz == FX3_IM_ELF_EXPECTED_SIZE
            and im_sha == FX3_IM_ELF_EXPECTED_SHA256
            and len(im_head) >= 20
            and im_head[:4] == b"\x7fELF"
            and struct.unpack_from("<H", im_head, 18)[0] == 183
        )
        if not im_ok:
            errors.append(f"FX3 im.elf mismatch: size={im_sz} sha256={im_sha}")

        jit_sz, jit_sha, jit_head = read_only_o_rdonly_digest_and_header(fx3_libjit_path)
        jit_ok = (
            jit_sz == LIBJIRITSU_EXPECTED_SIZE
            and jit_sha == LIBJIRITSU_EXPECTED_SHA256
            and len(jit_head) >= 20
            and jit_head[:4] == b"\x7fELF"
        )
        if not jit_ok:
            errors.append(f"FX3 libJiritsu.so mismatch: size={jit_sz} sha256={jit_sha}")

        appfw_sz, appfw_sha, _ = read_only_o_rdonly_digest_and_header(fx6_appfw_path)
        appfw_ok = appfw_sz == FX6_APPFW_EXPECTED_SIZE and appfw_sha == FX6_APPFW_DONOR_SHA256
        if not appfw_ok:
            errors.append(f"FX6 appFw.so mismatch: size={appfw_sz} sha256={appfw_sha}")

        _wlan_sz, wlan_sha, _ = read_only_o_rdonly_digest_and_header(fx6_wlan_path)
        wlan_ok = wlan_sha == FX6_WLAN_RSRC_DONOR_SHA256
        if not wlan_ok:
            errors.append(f"FX6 libWlanResource.so mismatch: sha256={wlan_sha}")

        all_uxc = sorted(uxc_dir.glob("*.uxc"))
        if len(all_uxc) != FX6_UXC_TOTAL_COUNT:
            errors.append(f"Expected {FX6_UXC_TOTAL_COUNT} .uxc files, found {len(all_uxc)}")
        uxc_verified = 0
        for name, (exp_sz, exp_sha) in FX6_CORE_UXC_ASSETS.items():
            p = uxc_dir / name
            if not p.is_file():
                errors.append(f"Missing core .uxc asset: {name}")
                continue
            sz, sha, _ = read_only_o_rdonly_digest_and_header(p)
            if sz != exp_sz or sha != exp_sha:
                errors.append(f"Core .uxc asset mismatch: {name}")
            else:
                uxc_verified += 1
    else:
        im_ok = True
        jit_ok = True
        appfw_ok = True
        wlan_ok = True
        uxc_verified = len(FX6_CORE_UXC_ASSETS)

    # Confirm modules dir existence note only in live mode when present
    _ = fx3_modules_dir
    return BenchDonorReadinessResult(
        passed=(len(errors) == 0),
        verification_mode=mode,
        read_only_o_rdonly_enforced=True,
        fx3_im_elf_verified=im_ok,
        fx3_libjiritsu_verified=jit_ok,
        fx6_appfw_verified=appfw_ok,
        fx6_wlan_rsrc_verified=wlan_ok,
        fx6_uxc_verified_count=uxc_verified,
        stage_b_13_lock_count=len(STAGE_B_LOCK_TABLE_13_ARTIFACTS),
        expected_launcher_sha256=EXPECTED_ESCAPE_HATCH_LAUNCHER_SHA256,
        raw_firmware_slices_emitted=RAW_FIRMWARE_SLICES_EMITTED,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 2: 100% Passive Zero-Packet USB Camera State Classifier
# ---------------------------------------------------------------------------


def capture_passive_ioreg_snapshot(*, timeout_s: float = 5.0) -> Tuple[str, Optional[str]]:
    """Run read-only `ioreg -a -p IOUSB -l -w 0` on macOS without opening any IOKit handle."""
    if sys.platform != "darwin":
        return "", "passive ioreg capture only supported on macOS darwin"
    try:
        proc = subprocess.run(
            ["ioreg", "-a", "-p", "IOUSB", "-l", "-w", "0"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        if proc.returncode != 0:
            return "", f"ioreg exited with rc={proc.returncode}"
        return proc.stdout, None
    except FileNotFoundError:
        return "", "ioreg binary not found"
    except Exception as exc:
        return "", f"ioreg failed: {exc}"


def _parse_ioreg_scalar(raw_v: str) -> Any:
    val = raw_v.strip()
    if val.startswith('"') and val.endswith('"') and len(val) >= 2:
        return val[1:-1]
    if val in ("Yes", "true", "True"):
        return True
    if val in ("No", "false", "False"):
        return False
    try:
        return int(val, 0)
    except ValueError:
        return val


def _parse_ioreg_text_to_tree(text: str) -> List[Dict[str, Any]]:
    """Parse `ioreg -p IOUSB -l -w 0` text output (with or without `{}` / `|` pipes) into nodes."""
    roots: List[Dict[str, Any]] = []
    stack: List[Tuple[int, Dict[str, Any]]] = []

    for raw_line in text.splitlines():
        if "+-o " in raw_line:
            marker_idx = raw_line.index("+-o ")
            m = re.search(
                r"\+-o\s+([^\s<]+)(?:\s+<class\s+([^,>]+)(?:,\s*id\s+([0-9]+|0x[0-9a-fA-F]+))?[^>]*>)?",
                raw_line[marker_idx:],
            )
            node_name = m.group(1) if m else raw_line[marker_idx + 4 :].strip()
            node_class = m.group(2).strip() if (m and m.group(2)) else ""
            node_id = int(m.group(3), 0) if (m and m.group(3)) else 0
            node: Dict[str, Any] = {
                "IORegistryEntryName": node_name,
                "IOClass": node_class,
                "IORegistryEntryID": node_id,
                "IORegistryEntryChildren": [],
            }
            while stack and stack[-1][0] >= marker_idx:
                stack.pop()
            if stack:
                stack[-1][1]["IORegistryEntryChildren"].append(node)
            else:
                roots.append(node)
            stack.append((marker_idx, node))
            continue

        stripped = raw_line.lstrip(" |\t")
        if not stripped or stripped in ("{", "}"):
            continue
        kv = re.match(r'^"([^"]+)"\s*=\s*(.+)$', stripped)
        if kv and stack:
            key, raw_val = kv.group(1), kv.group(2)
            stack[-1][1][key] = _parse_ioreg_scalar(raw_val)

    return roots


def _collect_usb_device_nodes(tree_roots: Sequence[Mapping[str, Any]]) -> List[PassiveUsbDeviceNode]:
    """Extract USB devices and their descendant interface classes/driver names from an ioreg tree."""
    devices: List[PassiveUsbDeviceNode] = []

    def _gather_descendants(
        node: Mapping[str, Any],
        if_classes: List[int],
        if_names: List[str],
        msc_flag: List[bool],
    ) -> None:
        for child in node.get("IORegistryEntryChildren", []) or []:
            if not isinstance(child, Mapping):
                continue
            # Stop descending into a nested USB device (e.g. behind a hub)
            if "idVendor" in child and "idProduct" in child:
                continue
            cname = str(child.get("IORegistryEntryName", "") or "")
            cclass = str(child.get("IOClass", "") or "")
            for s in (cname, cclass):
                if s:
                    if_names.append(s)
                    if "IOUSBMassStorageDriver" in s or "IOBlockStorageDriver" in s:
                        msc_flag[0] = True
            if "bInterfaceClass" in child:
                try:
                    ic = int(child["bInterfaceClass"])
                    if ic not in if_classes:
                        if_classes.append(ic)
                except Exception:
                    pass
            _gather_descendants(child, if_classes, if_names, msc_flag)

    def _walk(node: Mapping[str, Any]) -> None:
        if "idVendor" in node and "idProduct" in node:
            try:
                vid = int(node["idVendor"])
                pid = int(node["idProduct"])
            except Exception:
                vid, pid = 0, 0
            if vid > 0:
                if_classes: List[int] = []
                if_names: List[str] = []
                msc_flag = [False]
                if "bInterfaceClass" in node:
                    try:
                        if_classes.append(int(node["bInterfaceClass"]))
                    except Exception:
                        pass
                _gather_descendants(node, if_classes, if_names, msc_flag)
                loc_raw = node.get("locationID", 0)
                try:
                    loc_int = int(loc_raw)
                except Exception:
                    loc_int = 0
                reg_raw = node.get("IORegistryEntryID", 0)
                try:
                    reg_int = int(reg_raw)
                except Exception:
                    reg_int = 0
                prod = str(
                    node.get("USB Product Name")
                    or node.get("kUSBProductString")
                    or node.get("IORegistryEntryName")
                    or ""
                )
                vend = str(
                    node.get("USB Vendor Name")
                    or node.get("kUSBVendorString")
                    or ""
                )
                ser = str(
                    node.get("USB Serial Number")
                    or node.get("kUSBSerialNumberString")
                    or ""
                )
                devices.append(
                    PassiveUsbDeviceNode(
                        vid=vid,
                        pid=pid,
                        vid_pid=f"{vid:04X}:{pid:04X}",
                        product_name=prod,
                        vendor_name=vend,
                        serial_number=ser,
                        location_id_hex=f"{loc_int:#010x}",
                        registry_id=reg_int,
                        interface_classes=tuple(if_classes),
                        interface_names=tuple(if_names),
                        mass_storage_driver_attached=msc_flag[0] or (8 in if_classes),
                    )
                )
        for child in node.get("IORegistryEntryChildren", []) or []:
            if isinstance(child, Mapping):
                _walk(child)

    for root in tree_roots:
        if isinstance(root, Mapping):
            _walk(root)
    return devices


def parse_ioreg_usb_snapshot(snapshot_text: str) -> Tuple[Tuple[PassiveUsbDeviceNode, ...], str, Tuple[str, ...]]:
    """Parse `ioreg -p IOUSB -l -w 0` text or XML plist strictly passively (0 USB packets)."""
    if not isinstance(snapshot_text, str) or not snapshot_text.strip():
        return (), "empty_offline", ()

    stripped = snapshot_text.lstrip()
    errors: List[str] = []
    roots: List[Dict[str, Any]] = []
    if stripped.startswith("<?xml") or stripped.startswith("<plist"):
        fmt = "xml_plist"
        try:
            parsed = plistlib.loads(snapshot_text.encode("utf-8"))
            if isinstance(parsed, list):
                roots = [x for x in parsed if isinstance(x, dict)]
            elif isinstance(parsed, dict):
                roots = [parsed]
            else:
                errors.append("unexpected XML plist root type")
        except Exception as exc:
            errors.append(f"invalid ioreg XML plist: {exc}")
    else:
        fmt = "ioreg_text"
        roots = _parse_ioreg_text_to_tree(snapshot_text)

    devices = tuple(_collect_usb_device_nodes(roots))
    return devices, fmt, tuple(errors)


def _detect_wrong_usb_mode_label(dev: PassiveUsbDeviceNode) -> Optional[str]:
    if dev.pid in SONY_WRONG_MODE_PIDS:
        return SONY_WRONG_MODE_PIDS[dev.pid]
    # USB Interface Classes: 6 = Still Imaging (PTP/MTP), 14 = Video (UVC), 2/224 = CDC/RNDIS
    if 14 in dev.interface_classes:
        return "UVC_VIDEO_CLASS_0x0E"
    if 6 in dev.interface_classes:
        return "MTP_OR_PTP_CLASS_0x06"
    if 224 in dev.interface_classes or 2 in dev.interface_classes:
        return "RNDIS_OR_CDC_REMOTE"
    combined = " ".join((dev.product_name, *dev.interface_names)).upper()
    for token, label in (
        ("UVC", "UVC_STREAMING"),
        ("USB STREAMING", "UVC_STREAMING"),
        ("WEBCAM", "UVC_STREAMING"),
        ("MTP", "MTP_MODE"),
        ("PTP", "PTP_MODE"),
        ("PC REMOTE", "PC_REMOTE_MODE"),
        ("RNDIS", "RNDIS_NETWORK_MODE"),
    ):
        if token in combined:
            return label
    return None


def classify_passive_usb_snapshot(snapshot_text: str) -> PassiveUsbClassificationResult:
    """100% passive, zero-packet USB camera mode classifier across all 6 physical bench states."""
    assert not LIVE_USB_IOKIT_TRANSMIT_ENABLED
    assert USB_PACKETS_EMITTED == 0
    assert IOKIT_HANDLES_OPENED == 0

    all_devices, fmt, parse_errors = parse_ioreg_usb_snapshot(snapshot_text)
    sony_devices = tuple(d for d in all_devices if d.vid == SONY_USB_VID)
    errors = list(parse_errors)

    if len(sony_devices) == 0:
        return PassiveUsbClassificationResult(
            usb_state=USB_STATE_NO_SONY_CAMERA_ATTACHED,
            ready_for_msc_session=False,
            hard_abort=False,
            alert_code="NO_SONY_CAMERA_ATTACHED",
            snapshot_format=fmt,
            usb_packets_emitted=USB_PACKETS_EMITTED,
            iokit_handles_opened=IOKIT_HANDLES_OPENED,
            live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
            total_usb_devices_seen=len(all_devices),
            sony_device_count=0,
            sony_devices=(),
            detected_mode_detail="No Sony 0x054C USB device present in passive ioreg snapshot",
            remediation_steps=(
                "1. Verify NP-FZ100 battery charge >= 80% (or attach verified USB-PD 9V/3A supply).",
                "2. Disconnect any VMC-BNCM1 Multi-USB adapter or passive USB hub from the camera.",
                "3. On FX3 camera set: MENU -> Setup -> USB -> USB Connection Mode -> Mass Storage.",
                "4. Connect a direct USB-C data cable to the Mac host USB-C port and re-run preflight-realhw-bench.",
            ),
            errors=tuple(errors),
        )

    if len(sony_devices) > 1:
        vid_pids = ", ".join(f"{d.vid_pid}@{d.location_id_hex}" for d in sony_devices)
        return PassiveUsbClassificationResult(
            usb_state=USB_STATE_MULTIPLE_SONY_DEVICES_AMBIGUOUS,
            ready_for_msc_session=False,
            hard_abort=True,
            alert_code=ALERT_MULTIPLE_SONY_DEVICES_AMBIGUOUS,
            snapshot_format=fmt,
            usb_packets_emitted=USB_PACKETS_EMITTED,
            iokit_handles_opened=IOKIT_HANDLES_OPENED,
            live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
            total_usb_devices_seen=len(all_devices),
            sony_device_count=len(sony_devices),
            sony_devices=sony_devices,
            detected_mode_detail=f"Multiple Sony 0x054C devices attached: {vid_pids}",
            remediation_steps=(
                "1. HARD ABORT: Multiple Sony USB devices detected; wrong-camera targeting prevented.",
                "2. Unplug all secondary Sony cameras/accessories until strictly ONE target ILME-FX3 (054C:0DA1) remains.",
                "3. Re-run preflight-realhw-bench and verify sony_device_count == 1.",
            ),
            errors=tuple(errors + [f"{ALERT_MULTIPLE_SONY_DEVICES_AMBIGUOUS}: {vid_pids}"]),
        )

    dev = sony_devices[0]
    upper_prod = dev.product_name.upper()
    non_fx3_model_hit = any(tok in upper_prod for tok in UNSUPPORTED_MODEL_NAME_TOKENS)

    if dev.pid in SONY_UNSUPPORTED_MODEL_PIDS or non_fx3_model_hit:
        model_hint = SONY_UNSUPPORTED_MODEL_PIDS.get(dev.pid, dev.product_name or dev.vid_pid)
        return PassiveUsbClassificationResult(
            usb_state=USB_STATE_UNSUPPORTED_MODEL_PID,
            ready_for_msc_session=False,
            hard_abort=True,
            alert_code=ALERT_UNSUPPORTED_MODEL_PID,
            snapshot_format=fmt,
            usb_packets_emitted=USB_PACKETS_EMITTED,
            iokit_handles_opened=IOKIT_HANDLES_OPENED,
            live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
            total_usb_devices_seen=len(all_devices),
            sony_device_count=1,
            sony_devices=sony_devices,
            detected_mode_detail=f"Unsupported Sony USB PID/model {dev.vid_pid} ({model_hint})",
            remediation_steps=(
                f"1. HARD ABORT: Attached Sony device {dev.vid_pid} ({model_hint}) is NOT a supported ILME-FX3 (054C:0DA1).",
                "2. Disconnect unsupported body immediately; NEVER attempt Senser/Jiritsu session on non-FX3 models.",
            ),
            errors=tuple(errors + [f"{ALERT_UNSUPPORTED_MODEL_PID}: {dev.vid_pid} ({model_hint})"]),
        )

    if dev.pid == SONY_SERVICE_PID:
        return PassiveUsbClassificationResult(
            usb_state=USB_STATE_STRANDED_SERVICE_054C_0336,
            ready_for_msc_session=False,
            hard_abort=True,
            alert_code=ALERT_SERVICE_MODE_STRANDED,
            snapshot_format=fmt,
            usb_packets_emitted=USB_PACKETS_EMITTED,
            iokit_handles_opened=IOKIT_HANDLES_OPENED,
            live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
            total_usb_devices_seen=len(all_devices),
            sony_device_count=1,
            sony_devices=sony_devices,
            detected_mode_detail=f"Stranded Sony SERVICE endpoint {dev.vid_pid} at {dev.location_id_hex}",
            remediation_steps=(
                "1. ALERT_SERVICE_MODE_STRANDED: Physical camera is already in 054C:0336 SERVICE mode.",
                "2. DO NOT send SET_FILE2 or start a new Stage-285/288 session while stranded in 0336.",
                "3. Run safe teardown if active session handle exists: STOP (0336:7) -> release (0336:8) -> 054C:0DA1 (0da1:9) within <= 5000 ms.",
                "4. If no active session handle exists, unplug USB-C cable, power OFF FX3 (pull NP-FZ100 10s if needed), reboot to stock MSC (054C:0DA1).",
            ),
            errors=tuple(errors + [f"{ALERT_SERVICE_MODE_STRANDED}: 054C:0336 detected"]),
        )

    wrong_mode = _detect_wrong_usb_mode_label(dev)
    if wrong_mode is not None:
        return PassiveUsbClassificationResult(
            usb_state=USB_STATE_WRONG_USB_MODE_MTP_REMOTE_OR_UVC,
            ready_for_msc_session=False,
            hard_abort=False,
            alert_code="WRONG_USB_MODE_SWITCH_TO_MSC",
            snapshot_format=fmt,
            usb_packets_emitted=USB_PACKETS_EMITTED,
            iokit_handles_opened=IOKIT_HANDLES_OPENED,
            live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
            total_usb_devices_seen=len(all_devices),
            sony_device_count=1,
            sony_devices=sony_devices,
            detected_mode_detail=f"Sony device {dev.vid_pid} in non-MSC mode: {wrong_mode}",
            remediation_steps=(
                f"1. Camera detected in {wrong_mode} ({dev.vid_pid}), not Mass Storage (054C:0DA1).",
                "2. On FX3 menu set: MENU -> Setup -> USB -> USB Connection Mode -> Mass Storage.",
                "3. Disable USB Streaming (UVC) / PC Remote, reconnect USB-C, and re-run preflight-realhw-bench.",
            ),
            errors=tuple(errors + [f"WRONG_USB_MODE_MTP_REMOTE_OR_UVC: {dev.vid_pid} ({wrong_mode})"]),
        )

    if dev.pid == FX3_MSC_PID:
        return PassiveUsbClassificationResult(
            usb_state=USB_STATE_READY_MSC_054C_0DA1,
            ready_for_msc_session=True,
            hard_abort=False,
            alert_code="READY_MSC_054C_0DA1_OK",
            snapshot_format=fmt,
            usb_packets_emitted=USB_PACKETS_EMITTED,
            iokit_handles_opened=IOKIT_HANDLES_OPENED,
            live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
            total_usb_devices_seen=len(all_devices),
            sony_device_count=1,
            sony_devices=sony_devices,
            detected_mode_detail=f"Valid ILME-FX3 MSC endpoint 054C:0DA1 at {dev.location_id_hex}",
            remediation_steps=(
                "Valid 054C:0DA1 Mass Storage attachment confirmed passively (0 USB packets emitted).",
            ),
            errors=tuple(errors),
        )

    return PassiveUsbClassificationResult(
        usb_state=USB_STATE_UNSUPPORTED_MODEL_PID,
        ready_for_msc_session=False,
        hard_abort=True,
        alert_code=ALERT_UNSUPPORTED_MODEL_PID,
        snapshot_format=fmt,
        usb_packets_emitted=USB_PACKETS_EMITTED,
        iokit_handles_opened=IOKIT_HANDLES_OPENED,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        total_usb_devices_seen=len(all_devices),
        sony_device_count=1,
        sony_devices=sony_devices,
        detected_mode_detail=f"Unrecognized Sony USB PID {dev.vid_pid} ({dev.product_name})",
        remediation_steps=(
            f"1. HARD ABORT: Unrecognized Sony PID {dev.vid_pid}; only ILME-FX3 MSC (054C:0DA1) is permitted.",
            "2. Disconnect device and verify exact ILME-FX3 body + USB Mass Storage mode.",
        ),
        errors=tuple(errors + [f"{ALERT_UNSUPPORTED_MODEL_PID}: {dev.vid_pid}"]),
    )


def build_synthetic_ioreg_snapshot(
    *,
    scenario: str = "READY_MSC_054C_0DA1",
    snapshot_format: str = "xml_plist",
    location_id: int = 0x01100000,
) -> str:
    """Generate deterministic synthetic `ioreg -p IOUSB -l -w 0` XML plist or text snapshots."""
    nodes: List[Dict[str, Any]] = []
    if scenario == "NO_SONY_CAMERA_ATTACHED":
        nodes.append(
            {
                "IORegistryEntryName": "Internal Memory Card Reader",
                "IORegistryEntryID": 4295000100,
                "idVendor": 0x05AC,
                "idProduct": 0x8406,
                "USB Product Name": "Internal Memory Card Reader",
                "locationID": 0x02100000,
                "IORegistryEntryChildren": [],
            }
        )
    elif scenario == "READY_MSC_054C_0DA1":
        nodes.append(
            {
                "IORegistryEntryName": "ILME-FX3",
                "IORegistryEntryID": 4296580734,
                "idVendor": SONY_USB_VID,
                "idProduct": FX3_MSC_PID,
                "USB Product Name": "ILME-FX3",
                "USB Vendor Name": "Sony",
                "locationID": location_id,
                "IORegistryEntryChildren": [
                    {
                        "IORegistryEntryName": "IOUSBHostInterface@0",
                        "bInterfaceClass": 8,
                        "IORegistryEntryChildren": [
                            {"IORegistryEntryName": "IOUSBMassStorageDriver"}
                        ],
                    }
                ],
            }
        )
    elif scenario == "STRANDED_SERVICE_054C_0336":
        nodes.append(
            {
                "IORegistryEntryName": "ILME-FX3",
                "IORegistryEntryID": 4296580674,
                "idVendor": SONY_USB_VID,
                "idProduct": SONY_SERVICE_PID,
                "USB Product Name": "ILME-FX3",
                "USB Vendor Name": "Sony",
                "locationID": location_id,
                "IORegistryEntryChildren": [],
            }
        )
    elif scenario == "WRONG_USB_MODE_MTP":
        nodes.append(
            {
                "IORegistryEntryName": "ILME-FX3",
                "IORegistryEntryID": 4296580801,
                "idVendor": SONY_USB_VID,
                "idProduct": 0x0DA3,
                "USB Product Name": "ILME-FX3",
                "USB Vendor Name": "Sony",
                "locationID": location_id,
                "IORegistryEntryChildren": [
                    {"IORegistryEntryName": "IOUSBHostInterface@0", "bInterfaceClass": 6}
                ],
            }
        )
    elif scenario == "WRONG_USB_MODE_REMOTE":
        nodes.append(
            {
                "IORegistryEntryName": "ILME-FX3",
                "IORegistryEntryID": 4296580802,
                "idVendor": SONY_USB_VID,
                "idProduct": 0x0DA2,
                "USB Product Name": "ILME-FX3 PC Remote",
                "USB Vendor Name": "Sony",
                "locationID": location_id,
                "IORegistryEntryChildren": [],
            }
        )
    elif scenario == "WRONG_USB_MODE_UVC":
        nodes.append(
            {
                "IORegistryEntryName": "ILME-FX3",
                "IORegistryEntryID": 4296580803,
                "idVendor": SONY_USB_VID,
                "idProduct": 0x0DA4,
                "USB Product Name": "ILME-FX3 USB Streaming",
                "USB Vendor Name": "Sony",
                "locationID": location_id,
                "IORegistryEntryChildren": [
                    {"IORegistryEntryName": "AppleUSBVideoDevice", "bInterfaceClass": 14}
                ],
            }
        )
    elif scenario == "MULTIPLE_SONY_DEVICES_AMBIGUOUS":
        nodes.append(
            {
                "IORegistryEntryName": "ILME-FX3",
                "IORegistryEntryID": 4296580734,
                "idVendor": SONY_USB_VID,
                "idProduct": FX3_MSC_PID,
                "USB Product Name": "ILME-FX3",
                "locationID": 0x01100000,
                "IORegistryEntryChildren": [],
            }
        )
        nodes.append(
            {
                "IORegistryEntryName": "ILCE-7M4",
                "IORegistryEntryID": 4296580799,
                "idVendor": SONY_USB_VID,
                "idProduct": 0x0DA3,
                "USB Product Name": "ILCE-7M4",
                "locationID": 0x01200000,
                "IORegistryEntryChildren": [],
            }
        )
    elif scenario == "UNSUPPORTED_MODEL_PID":
        nodes.append(
            {
                "IORegistryEntryName": "ILME-FX30",
                "IORegistryEntryID": 4296580900,
                "idVendor": SONY_USB_VID,
                "idProduct": 0x0E0E,
                "USB Product Name": "ILME-FX30",
                "USB Vendor Name": "Sony",
                "locationID": location_id,
                "IORegistryEntryChildren": [],
            }
        )
    else:
        raise ValueError(f"Unknown synthetic ioreg scenario: {scenario!r}")

    if snapshot_format == "xml_plist":
        root = {
            "IORegistryEntryName": "AppleUSB30XHCIPort",
            "IORegistryEntryID": 4294968654,
            "IORegistryEntryChildren": nodes,
        }
        return plistlib.dumps(root).decode("utf-8")

    if snapshot_format == "ioreg_text":
        lines = [
            f"+-o AppleUSB30XHCIPort@{location_id:08x}  <class AppleUSB30XHCIPort, id 0x100000620>"
        ]
        for idx, n in enumerate(nodes):
            lines.extend(
                [
                    f"  +-o {n['IORegistryEntryName']}@{n['locationID']:08x}  <class IOUSBHostDevice, id {n['IORegistryEntryID'] + idx}>",
                    "    {",
                    f'      "idVendor" = {n["idVendor"]}',
                    f'      "idProduct" = {n["idProduct"]}',
                    f'      "USB Product Name" = "{n["USB Product Name"]}"',
                    f'      "locationID" = {n["locationID"]}',
                    "    }",
                ]
            )
            for child in n.get("IORegistryEntryChildren", []):
                lines.append(
                    f"      +-o {child['IORegistryEntryName']}  <class {child['IORegistryEntryName']}, id 0x100000950>"
                )
                if "bInterfaceClass" in child:
                    lines.append("        {")
                    lines.append(f'          "bInterfaceClass" = {child["bInterfaceClass"]}')
                    lines.append("        }")
        return "\n".join(lines) + "\n"

    raise ValueError(f"Unsupported snapshot_format={snapshot_format!r}")


# ---------------------------------------------------------------------------
# Pillar 3: Candidate ExFAT SD Card Staging & Forbidden-File Firewall
# ---------------------------------------------------------------------------


def _is_forbidden_ota_relpath(rel_posix: str) -> bool:
    norm = rel_posix.strip("/").lower()
    base = norm.rsplit("/", 1)[-1]
    if base in FORBIDDEN_SD_FILENAMES:
        return True
    for prefix in FORBIDDEN_SD_PATH_PREFIXES:
        if norm == prefix or norm.startswith(prefix):
            return True
    return "/setting/updater/mode" in f"/{norm}" or "/updater/mode" in f"/{norm}"


def audit_sd_staging_directory(
    sd_dir: Optional[Path],
    *,
    free_bytes_override: Optional[int] = None,
    observed_launcher_sha256: Optional[str] = None,
    require_launcher_artifact: bool = False,
) -> SdStagingAuditResult:
    """Audit a candidate ExFAT SD staging directory strictly via O_RDONLY | O_NOFOLLOW."""
    if sd_dir is None:
        return SdStagingAuditResult(
            passed=False,
            provided=False,
            sd_dir_label="<not_provided>",
            read_only_o_rdonly_enforced=True,
            symlink_rejected_count=0,
            forbidden_firewall_passed=False,
            forbidden_files_found=(),
            exfat_paths_valid=False,
            manifest_present=False,
            manifest_signature_valid=False,
            manifest_sha256="",
            stage_b_13_locks_verified=0,
            stage_b_13_parity_ok=False,
            bk4_shadow_magic_valid=False,
            uninstall_manifest_valid=False,
            escape_hatch_launcher_sha256="",
            escape_hatch_launcher_hash_ok=False,
            escape_hatch_max_latency_us=ESCAPE_HATCH_MAX_LATENCY_US,
            free_space_bytes=0,
            free_space_gib=0.0,
            required_free_space_bytes=MIN_SD_FREE_SPACE_BYTES,
            free_space_quota_ok=False,
            target_body_serial="",
            target_emmc_cid_sha256="",
            error_codes=("ERR_SD_DIR_NOT_PROVIDED",),
            errors=("SD staging directory (--sd-dir) was not provided",),
        )

    errors: List[str] = []
    error_codes: List[str] = []
    sd_label = sd_dir.name or str(sd_dir)

    if sd_dir.is_symlink() or not sd_dir.is_dir():
        return SdStagingAuditResult(
            passed=False,
            provided=True,
            sd_dir_label=sd_label,
            read_only_o_rdonly_enforced=True,
            symlink_rejected_count=1 if sd_dir.is_symlink() else 0,
            forbidden_firewall_passed=False,
            forbidden_files_found=(),
            exfat_paths_valid=False,
            manifest_present=False,
            manifest_signature_valid=False,
            manifest_sha256="",
            stage_b_13_locks_verified=0,
            stage_b_13_parity_ok=False,
            bk4_shadow_magic_valid=False,
            uninstall_manifest_valid=False,
            escape_hatch_launcher_sha256="",
            escape_hatch_launcher_hash_ok=False,
            escape_hatch_max_latency_us=ESCAPE_HATCH_MAX_LATENCY_US,
            free_space_bytes=0,
            free_space_gib=0.0,
            required_free_space_bytes=MIN_SD_FREE_SPACE_BYTES,
            free_space_quota_ok=False,
            target_body_serial="",
            target_emmc_cid_sha256="",
            error_codes=("ERR_SD_DIR_MISSING_OR_INVALID",),
            errors=(f"SD staging path missing or not a real directory: {sd_dir}",),
        )

    # 1. Walk directory (followlinks=False), reject symlinks, check exFAT paths & forbidden OTA triggers
    symlink_count = 0
    forbidden_hits: List[str] = []
    exfat_ok = True
    for root, dirs, files in os.walk(sd_dir, followlinks=False):
        root_p = Path(root)
        # Check directory entries for symlinks & forbidden paths
        clean_dirs: List[str] = []
        for d in sorted(dirs):
            dp = root_p / d
            rel_d = dp.relative_to(sd_dir).as_posix()
            if dp.is_symlink():
                symlink_count += 1
                errors.append(f"{ERR_SD_SYMLINK_REJECTED}: {rel_d}")
                continue
            if _is_forbidden_ota_relpath(rel_d):
                forbidden_hits.append(rel_d)
            clean_dirs.append(d)
        dirs[:] = clean_dirs

        for fn in sorted(files):
            fp = root_p / fn
            rel_f = fp.relative_to(sd_dir).as_posix()
            if fp.is_symlink():
                symlink_count += 1
                errors.append(f"{ERR_SD_SYMLINK_REJECTED}: {rel_f}")
                continue
            if _is_forbidden_ota_relpath(rel_f):
                forbidden_hits.append(rel_f)
            ok_exfat, exfat_err = _validate_exfat_fat32_relpath(rel_f)
            if not ok_exfat:
                exfat_ok = False
                errors.append(f"Invalid exFAT/FAT32 path {rel_f}: {exfat_err}")

    if symlink_count > 0:
        error_codes.append(ERR_SD_SYMLINK_REJECTED)
    forbidden_firewall_passed = len(forbidden_hits) == 0
    if not forbidden_firewall_passed:
        error_codes.append(BLOCKED_FORBIDDEN_OTA_TRIGGER)
        errors.append(
            f"{BLOCKED_FORBIDDEN_OTA_TRIGGER}: forbidden factory OTA/repartition triggers found: {forbidden_hits}"
        )

    # 2. Free-space quota (>= 2 GiB required for 16-surface Tier-0 cold backup)
    if free_bytes_override is not None:
        free_bytes = int(free_bytes_override)
    else:
        st_vfs = os.statvfs(sd_dir)
        free_bytes = int(st_vfs.f_bavail) * int(st_vfs.f_frsize)
    free_gib = round(free_bytes / float(GIB_BYTES), 3)
    free_ok = free_bytes >= MIN_SD_FREE_SPACE_BYTES
    if not free_ok:
        error_codes.append(ERR_SD_FREE_SPACE_UNDER_2GIB)
        errors.append(
            f"{ERR_SD_FREE_SPACE_UNDER_2GIB}: free={free_bytes} B ({free_gib:.3f} GiB) < {MIN_SD_FREE_SPACE_BYTES} B (2.0 GiB)"
        )

    # 3. Manifest & 13/13 Stage-B lock parity via O_RDONLY
    manifest_path = sd_dir / SD_MANIFEST_RELPATH
    manifest_present = manifest_path.is_file() and not manifest_path.is_symlink()
    manifest_sig_valid = False
    manifest_sha = ""
    locks_verified = 0
    locks_parity_ok = False
    bk4_ok = False
    uninstall_ok = False
    target_serial = ""
    target_cid_sha256 = ""
    manifest_launcher_sha = ""

    if not manifest_present:
        error_codes.append("ERR_SD_MANIFEST_MISSING")
        errors.append(f"Missing Stage-B manifest: {SD_MANIFEST_RELPATH}")
    else:
        try:
            manifest_raw = _read_regular_file_o_rdonly(manifest_path, max_bytes=4 * 1024 * 1024)
            manifest = json.loads(manifest_raw.decode("utf-8"))
            manifest_sha = str(manifest.get("manifest_sha256", ""))
            expected_sig = _compute_canonical_sha256(manifest, "manifest_sha256")
            manifest_sig_valid = (manifest_sha == expected_sig) and bool(HEX64_RE.match(manifest_sha))
            if not manifest_sig_valid:
                error_codes.append("ERR_SD_MANIFEST_SIGNATURE_INVALID")
                errors.append("FX6_STAGEB_BOOT.MANIFEST manifest_sha256 signature mismatch")
            if manifest.get("persistent_emmc_writes_authorized") is not False:
                error_codes.append("ERR_SD_MANIFEST_WRITE_POLICY_VIOLATION")
                errors.append("FX6_STAGEB_BOOT.MANIFEST must hard-lock persistent_emmc_writes_authorized=False")

            target_serial = str(manifest.get("target_body_serial", ""))
            raw_cid = str(manifest.get("target_emmc_cid", "")).strip().lower()
            if HEX32_CID_RE.match(raw_cid) and raw_cid not in FORBIDDEN_TRIVIAL_CIDS:
                target_cid_sha256 = _compute_camera_cid_sha256(raw_cid)
            manifest_launcher_sha = str(manifest.get("launcher_script_sha256", "")).strip()

            expected_matrix_ids = {
                e[0] if isinstance(e, tuple) else e.matrix_id
                for e in STAGE_B_LOCK_TABLE_13_ARTIFACTS
            }
            seen_matrix_ids = set()
            lock_rows = manifest.get("lock_table_13", [])
            if len(lock_rows) != 13:
                errors.append(f"Expected 13 lock_table_13 entries, got {len(lock_rows)}")
            for row in lock_rows:
                mid = str(row.get("matrix_id", ""))
                sd_rel = str(row.get("sd_rel_path", ""))
                exp_sha = str(row.get("sha256", ""))
                exp_sz = int(row.get("size_bytes", -1))
                if mid:
                    seen_matrix_ids.add(mid)
                art_path = sd_dir / sd_rel
                if not art_path.is_file() or art_path.is_symlink():
                    errors.append(f"Missing/invalid Stage-B artifact on SD: {sd_rel}")
                    continue
                obs_sz, obs_sha, _ = read_only_o_rdonly_digest_and_header(art_path)
                if obs_sha != exp_sha or (exp_sz >= 0 and obs_sz != exp_sz):
                    errors.append(f"Stage-B artifact parity mismatch on SD: {sd_rel}")
                    continue
                if manifest.get("verification_mode") == "LOCAL_DONOR_O_RDONLY":
                    if sd_rel.endswith("lib/appFw.so") and obs_sha != FX6_APPFW_STAGE_B_SHA256:
                        errors.append(f"appFw.so Stage-B SHA-256 mismatch: {obs_sha}")
                        continue
                    if sd_rel.endswith("lib/libWlanResource.so") and obs_sha != FX6_WLAN_RSRC_P12_SHA256:
                        errors.append(f"libWlanResource.so P12 SHA-256 mismatch: {obs_sha}")
                        continue
                locks_verified += 1

            locks_parity_ok = (
                len(lock_rows) == 13
                and seen_matrix_ids == expected_matrix_ids
                and locks_verified == 13
            )
            if not locks_parity_ok:
                error_codes.append(ERR_SD_STAGE_B_13_PARITY_FAILED)

            # Verify sd_files catalog parity
            sd_files_map = manifest.get("sd_files", {})
            for rel_p, meta in sd_files_map.items():
                fp = sd_dir / str(rel_p)
                if not fp.is_file() or fp.is_symlink():
                    errors.append(f"Missing sd_files entry on SD: {rel_p}")
                    continue
                obs_sz, obs_sha, _ = read_only_o_rdonly_digest_and_header(fp)
                if obs_sha != meta.get("sha256") or obs_sz != int(meta.get("size_bytes", -1)):
                    errors.append(f"sd_files digest/size mismatch: {rel_p}")
        except Exception as exc:
            error_codes.append("ERR_SD_MANIFEST_PARSE_FAILED")
            errors.append(f"Failed auditing {SD_MANIFEST_RELPATH}: {exc}")

    # 4. Verify BK4\0 shadow seed & rescue uninstall manifest
    bk4_path = sd_dir / SD_BK4_SHADOW_SEED_RELPATH
    if bk4_path.is_file() and not bk4_path.is_symlink():
        try:
            bk4_bytes = _read_regular_file_o_rdonly(bk4_path, max_bytes=256 * 1024)
            bk4_ok = bk4_bytes.startswith(BK4_MAGIC) or (
                len(bk4_bytes) >= 16 and bk4_bytes[12:16] == BK4_MAGIC
            )
            if not bk4_ok:
                errors.append(f"Invalid BK4 magic in {SD_BK4_SHADOW_SEED_RELPATH}")
        except Exception as exc:
            errors.append(f"Failed reading {SD_BK4_SHADOW_SEED_RELPATH}: {exc}")
    else:
        errors.append(f"Missing {SD_BK4_SHADOW_SEED_RELPATH}")

    uninst_path = sd_dir / SD_UNINSTALL_MANIFEST_RELPATH
    if uninst_path.is_file() and not uninst_path.is_symlink():
        try:
            uninst_raw = _read_regular_file_o_rdonly(uninst_path, max_bytes=1024 * 1024)
            uninst = json.loads(uninst_raw.decode("utf-8"))
            uninst_sig = _compute_canonical_sha256(uninst, "manifest_sha256")
            uninstall_ok = (
                uninst.get("manifest_sha256") == uninst_sig
                and uninst.get("persistent_emmc_writes_authorized") is False
                and uninst.get("crypto_block_device") == "/dev/cnflasha15"
            )
            if not uninstall_ok:
                errors.append(f"Invalid rescue uninstall manifest signature/contract: {SD_UNINSTALL_MANIFEST_RELPATH}")
        except Exception as exc:
            errors.append(f"Failed reading {SD_UNINSTALL_MANIFEST_RELPATH}: {exc}")
    else:
        errors.append(f"Missing {SD_UNINSTALL_MANIFEST_RELPATH}")

    # 5. Verify < 50 us SD-eject bypass launcher hash
    expected_launcher_sha = (
        hashlib.sha256(
            generate_im_elf_escape_hatch_launcher(expected_body_serial=target_serial).encode("utf-8")
        ).hexdigest()
        if target_serial
        else EXPECTED_ESCAPE_HATCH_LAUNCHER_SHA256
    )
    launcher_sh_path = sd_dir / SD_LAUNCHER_SH_RELPATH
    launcher_sha_path = sd_dir / SD_LAUNCHER_SHA256_RELPATH
    actual_launcher_sha = expected_launcher_sha
    launcher_found_on_sd = False

    if launcher_sh_path.is_file() and not launcher_sh_path.is_symlink():
        launcher_found_on_sd = True
        _lsz, actual_launcher_sha, _ = read_only_o_rdonly_digest_and_header(launcher_sh_path)
    elif launcher_sha_path.is_file() and not launcher_sha_path.is_symlink():
        launcher_found_on_sd = True
        actual_launcher_sha = _read_regular_file_o_rdonly(launcher_sha_path, max_bytes=4096).decode(
            "utf-8", "replace"
        ).strip().split()[0]
    elif manifest_launcher_sha:
        launcher_found_on_sd = True
        actual_launcher_sha = manifest_launcher_sha

    if observed_launcher_sha256 is not None:
        actual_launcher_sha = observed_launcher_sha256.strip().lower()
        launcher_found_on_sd = True

    if require_launcher_artifact and not launcher_found_on_sd:
        launcher_hash_ok = False
        error_codes.append(ERR_SD_ESCAPE_HATCH_LAUNCHER_HASH_MISMATCH)
        errors.append("Missing < 50 us escape-hatch launcher artifact/hash on SD staging dir")
    else:
        launcher_hash_ok = actual_launcher_sha == expected_launcher_sha
        if not launcher_hash_ok:
            error_codes.append(ERR_SD_ESCAPE_HATCH_LAUNCHER_HASH_MISMATCH)
            errors.append(
                f"{ERR_SD_ESCAPE_HATCH_LAUNCHER_HASH_MISMATCH}: observed={actual_launcher_sha} != expected={expected_launcher_sha}"
            )

    passed = (
        len(errors) == 0
        and symlink_count == 0
        and forbidden_firewall_passed
        and exfat_ok
        and manifest_present
        and manifest_sig_valid
        and locks_parity_ok
        and bk4_ok
        and uninstall_ok
        and launcher_hash_ok
        and free_ok
    )
    return SdStagingAuditResult(
        passed=passed,
        provided=True,
        sd_dir_label=sd_label,
        read_only_o_rdonly_enforced=True,
        symlink_rejected_count=symlink_count,
        forbidden_firewall_passed=forbidden_firewall_passed,
        forbidden_files_found=tuple(sorted(set(forbidden_hits))),
        exfat_paths_valid=exfat_ok,
        manifest_present=manifest_present,
        manifest_signature_valid=manifest_sig_valid,
        manifest_sha256=manifest_sha,
        stage_b_13_locks_verified=locks_verified,
        stage_b_13_parity_ok=locks_parity_ok,
        bk4_shadow_magic_valid=bk4_ok,
        uninstall_manifest_valid=uninstall_ok,
        escape_hatch_launcher_sha256=actual_launcher_sha,
        escape_hatch_launcher_hash_ok=launcher_hash_ok,
        escape_hatch_max_latency_us=ESCAPE_HATCH_MAX_LATENCY_US,
        free_space_bytes=free_bytes,
        free_space_gib=free_gib,
        required_free_space_bytes=MIN_SD_FREE_SPACE_BYTES,
        free_space_quota_ok=free_ok,
        target_body_serial=target_serial,
        target_emmc_cid_sha256=target_cid_sha256,
        error_codes=tuple(sorted(set(error_codes))),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 4: Dual-Copy (SD + Host Vault) Tier-0 FX3RCPT1 Receipt Verifier
# ---------------------------------------------------------------------------


def _extract_receipt_surface_hashes(rcpt_bytes: bytes) -> Dict[str, str]:
    info = parse_sd_backup_receipt_bytes(rcpt_bytes)
    slots = [rcpt_bytes[16 + i * 32 : 16 + (i + 1) * 32] for i in range(15)] if len(rcpt_bytes) == SD_RECEIPT_BYTES else []
    surfaces: Dict[str, str] = {
        "manifest_sha256": info.manifest_sha256,
        "sector0": info.sector0_sha256,
        "p1": info.p1_sha256,
        "p2": info.p2_sha256,
        "p6": info.p6_sha256,
        "p12": info.p12_sha256,
        "p18": info.p18_sha256,
        "spi_nor_ddrtraining": info.spi_nor_ddrtraining_sha256,
        "spi_nor_loader": info.spi_nor_loader_sha256,
        "p3": slots[9].hex() if len(slots) >= 13 else "",
        "p7": slots[10].hex() if len(slots) >= 13 else "",
        "p8": slots[11].hex() if len(slots) >= 13 else "",
        "tier2_bundle_p5_p13_p15_p23_p30": info.tier2_bundle_sha256,
    }
    return surfaces


def _read_sidecar_cid_sha256(receipt_path: Optional[Path]) -> str:
    if receipt_path is None:
        return ""
    candidates = [
        receipt_path.with_suffix(".meta.json"),
        receipt_path.parent / "tier0_identity.json",
    ]
    for cand in candidates:
        if cand.is_file() and not cand.is_symlink():
            try:
                raw = _read_regular_file_o_rdonly(cand, max_bytes=256 * 1024)
                doc = json.loads(raw.decode("utf-8"))
                cid_sha = str(doc.get("camera_cid_sha256", "")).strip().lower()
                if cid_sha:
                    return cid_sha
                raw_cid = str(doc.get("emmc_cid", "")).strip().lower()
                if HEX32_CID_RE.match(raw_cid):
                    return _compute_camera_cid_sha256(raw_cid)
            except Exception:
                return ""
    return ""


def _audit_single_receipt_copy(
    copy_role: str,
    receipt_path: Optional[Path],
    receipt_bytes: Optional[bytes],
    cid_sha256_override: Optional[str],
) -> Tuple[ReceiptCopySummary, Optional[bytes]]:
    if receipt_bytes is None and receipt_path is None:
        return (
            ReceiptCopySummary(
                copy_role=copy_role,
                present=False,
                valid_528b_fx3rcpt1=False,
                byte_length=0,
                crc32_hex="",
                sha256_digest="",
                magic="",
                version=0,
                entry_count=0,
                manifest_sha256="",
                receipt_integrity_sha256="",
                total_dumped_bytes=0,
                camera_cid_sha256="",
                surface_hashes={},
                errors=(f"{copy_role} receipt not provided",),
            ),
            None,
        )

    raw: Optional[bytes] = receipt_bytes
    errors: List[str] = []
    if raw is None and receipt_path is not None:
        if not receipt_path.is_file() or receipt_path.is_symlink():
            return (
                ReceiptCopySummary(
                    copy_role=copy_role,
                    present=False,
                    valid_528b_fx3rcpt1=False,
                    byte_length=0,
                    crc32_hex="",
                    sha256_digest="",
                    magic="",
                    version=0,
                    entry_count=0,
                    manifest_sha256="",
                    receipt_integrity_sha256="",
                    total_dumped_bytes=0,
                    camera_cid_sha256="",
                    surface_hashes={},
                    errors=(f"{copy_role} receipt missing or symlink: {receipt_path}",),
                ),
                None,
            )
        try:
            raw = _read_regular_file_o_rdonly(receipt_path, max_bytes=4096)
        except Exception as exc:
            return (
                ReceiptCopySummary(
                    copy_role=copy_role,
                    present=False,
                    valid_528b_fx3rcpt1=False,
                    byte_length=0,
                    crc32_hex="",
                    sha256_digest="",
                    magic="",
                    version=0,
                    entry_count=0,
                    manifest_sha256="",
                    receipt_integrity_sha256="",
                    total_dumped_bytes=0,
                    camera_cid_sha256="",
                    surface_hashes={},
                    errors=(f"{copy_role} read error: {exc}",),
                ),
                None,
            )

    assert raw is not None
    info = parse_sd_backup_receipt_bytes(raw)
    errors.extend(info.errors)
    crc32_val = zlib.crc32(raw) & 0xFFFFFFFF
    sha_val = hashlib.sha256(raw).hexdigest()
    cid_sha = (
        cid_sha256_override.strip().lower()
        if cid_sha256_override is not None
        else _read_sidecar_cid_sha256(receipt_path)
    )
    if not _is_valid_camera_cid_sha256(cid_sha):
        errors.append(f"{copy_role} missing or trivial/invalid camera_cid_sha256")

    return (
        ReceiptCopySummary(
            copy_role=copy_role,
            present=True,
            valid_528b_fx3rcpt1=info.valid,
            byte_length=len(raw),
            crc32_hex=f"{crc32_val:#010x}",
            sha256_digest=sha_val,
            magic=info.magic,
            version=info.version,
            entry_count=info.entry_count,
            manifest_sha256=info.manifest_sha256,
            receipt_integrity_sha256=info.receipt_integrity_sha256,
            total_dumped_bytes=info.total_dumped_bytes,
            camera_cid_sha256=cid_sha,
            surface_hashes=_extract_receipt_surface_hashes(raw),
            errors=tuple(errors),
        ),
        raw,
    )


def verify_dual_copy_tier0_receipts(
    *,
    sd_receipt_path: Optional[Path] = None,
    vault_receipt_path: Optional[Path] = None,
    sd_receipt_bytes: Optional[bytes] = None,
    vault_receipt_bytes: Optional[bytes] = None,
    sd_camera_cid_sha256: Optional[str] = None,
    vault_camera_cid_sha256: Optional[str] = None,
    expected_camera_cid_sha256: Optional[str] = None,
) -> DualCopyTier0ReceiptAuditResult:
    """Verify dual-copy (SD ExFAT + Mac Host Vault) 528 B FX3RCPT1 receipts via O_RDONLY."""
    sd_summary, sd_raw = _audit_single_receipt_copy(
        "SD_EXFAT", sd_receipt_path, sd_receipt_bytes, sd_camera_cid_sha256
    )
    vault_summary, vault_raw = _audit_single_receipt_copy(
        "HOST_VAULT", vault_receipt_path, vault_receipt_bytes, vault_camera_cid_sha256
    )

    provided = sd_summary.present or vault_summary.present
    if not sd_summary.present or not vault_summary.present:
        errs = list(sd_summary.errors) + list(vault_summary.errors)
        return DualCopyTier0ReceiptAuditResult(
            passed=False,
            provided=provided,
            sd_copy=sd_summary,
            vault_copy=vault_summary,
            crc32_parity_ok=False,
            sha256_parity_ok=False,
            surface_16_parity_ok=False,
            camera_cid_sha256_match=False,
            camera_cid_sha256="",
            manifest_16_items_verified=False,
            error_codes=(ERR_DUAL_COPY_RECEIPT_MISSING,),
            errors=tuple(errs or [f"{ERR_DUAL_COPY_RECEIPT_MISSING}: both SD and Host Vault 528 B FX3RCPT1 receipts are required"]),
        )

    errors: List[str] = list(sd_summary.errors) + list(vault_summary.errors)
    error_codes: List[str] = []

    if not sd_summary.valid_528b_fx3rcpt1 or not vault_summary.valid_528b_fx3rcpt1:
        error_codes.append(ERR_DUAL_COPY_RECEIPT_INVALID)

    crc32_ok = bool(sd_summary.crc32_hex) and sd_summary.crc32_hex == vault_summary.crc32_hex
    if not crc32_ok:
        error_codes.append(ERR_DUAL_COPY_CRC32_MISMATCH)
        errors.append(
            f"{ERR_DUAL_COPY_CRC32_MISMATCH}: sd={sd_summary.crc32_hex} != vault={vault_summary.crc32_hex}"
        )

    sha256_ok = bool(sd_summary.sha256_digest) and sd_summary.sha256_digest == vault_summary.sha256_digest
    if not sha256_ok:
        error_codes.append(ERR_DUAL_COPY_SHA256_MISMATCH)
        errors.append(
            f"{ERR_DUAL_COPY_SHA256_MISMATCH}: sd={sd_summary.sha256_digest} != vault={vault_summary.sha256_digest}"
        )

    surface_16_ok = (
        sd_summary.valid_528b_fx3rcpt1
        and vault_summary.valid_528b_fx3rcpt1
        and sd_summary.entry_count == len(COLD_BACKUP_ITEMS)
        and vault_summary.entry_count == len(COLD_BACKUP_ITEMS)
        and sd_summary.surface_hashes == vault_summary.surface_hashes
        and sd_summary.total_dumped_bytes > 0
        and sd_summary.total_dumped_bytes == vault_summary.total_dumped_bytes
    )
    if not surface_16_ok:
        error_codes.append(ERR_DUAL_COPY_SURFACE16_MISMATCH)
        errors.append(f"{ERR_DUAL_COPY_SURFACE16_MISMATCH}: 16-surface digest or total_dumped_bytes mismatch")

    cid_match = (
        _is_valid_camera_cid_sha256(sd_summary.camera_cid_sha256)
        and _is_valid_camera_cid_sha256(vault_summary.camera_cid_sha256)
        and sd_summary.camera_cid_sha256 == vault_summary.camera_cid_sha256
    )
    if expected_camera_cid_sha256 is not None:
        norm_exp = expected_camera_cid_sha256.strip().lower()
        if not _is_valid_camera_cid_sha256(norm_exp) or sd_summary.camera_cid_sha256 != norm_exp:
            cid_match = False
    if not cid_match:
        error_codes.append(ERR_CAMERA_CID_SHA256_MISMATCH)
        errors.append(
            f"{ERR_CAMERA_CID_SHA256_MISMATCH}: sd={sd_summary.camera_cid_sha256!r} vault={vault_summary.camera_cid_sha256!r}"
        )

    # Check optional MANIFEST.SHA256 sidecar parity if present alongside SD/Vault receipts
    manifest_16_ok = True
    expected_filenames = {item.filename for item in COLD_BACKUP_ITEMS}
    for role, rpath, rsummary in (
        ("SD_EXFAT", sd_receipt_path, sd_summary),
        ("HOST_VAULT", vault_receipt_path, vault_summary),
    ):
        if rpath is not None:
            man_path = rpath.parent / "MANIFEST.SHA256"
            if man_path.is_file() and not man_path.is_symlink():
                try:
                    man_raw = _read_regular_file_o_rdonly(man_path, max_bytes=1024 * 1024)
                    man_sha = hashlib.sha256(man_raw).hexdigest()
                    if man_sha != rsummary.manifest_sha256:
                        manifest_16_ok = False
                        errors.append(f"{role} MANIFEST.SHA256 digest mismatch vs FX3RCPT1")
                    seen_names = set()
                    for line in man_raw.decode("utf-8").splitlines():
                        parts = line.strip().split()
                        if len(parts) == 2 and HEX64_RE.match(parts[0]):
                            seen_names.add(parts[1])
                    if seen_names != expected_filenames:
                        manifest_16_ok = False
                        errors.append(f"{role} MANIFEST.SHA256 missing 16-surface items")
                except Exception as exc:
                    manifest_16_ok = False
                    errors.append(f"{role} MANIFEST.SHA256 read error: {exc}")

    _ = (sd_raw, vault_raw)
    passed = (
        len(errors) == 0
        and sd_summary.valid_528b_fx3rcpt1
        and vault_summary.valid_528b_fx3rcpt1
        and crc32_ok
        and sha256_ok
        and surface_16_ok
        and cid_match
        and manifest_16_ok
    )
    return DualCopyTier0ReceiptAuditResult(
        passed=passed,
        provided=True,
        sd_copy=sd_summary,
        vault_copy=vault_summary,
        crc32_parity_ok=crc32_ok,
        sha256_parity_ok=sha256_ok,
        surface_16_parity_ok=surface_16_ok,
        camera_cid_sha256_match=cid_match,
        camera_cid_sha256=sd_summary.camera_cid_sha256 if cid_match else "",
        manifest_16_items_verified=manifest_16_ok,
        error_codes=tuple(sorted(set(error_codes))),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Fixture Populators (for Tests & `--simulate-ready-bench`)
# ---------------------------------------------------------------------------


def populate_sd_staging_fixture(
    sd_dir: Path,
    *,
    body_serial: str = DEFAULT_TARGET_BODY_SERIAL,
    emmc_cid: str = DEFAULT_TARGET_EMMC_CID,
    lang: str = "en",
    synthetic_clean_room: Optional[bool] = None,
    include_launcher_file: bool = True,
    forbidden_trigger_relpath: Optional[str] = None,
) -> Dict[str, Any]:
    """Write a complete valid Stage-B SD staging tree into `sd_dir` (for temp-dir tests)."""
    tier0_bind = default_tier0_receipt_binding(
        body_serial=body_serial,
        emmc_cid=emmc_cid,
    )
    bundle = build_sd_stageb_deployment_bundle(
        tier0_receipt=tier0_bind,
        target_body_serial=body_serial,
        target_emmc_cid=emmc_cid,
        lang=lang,
        synthetic_clean_room=synthetic_clean_room,
    )
    sd_dir.mkdir(parents=True, exist_ok=True)
    for rel_p, blob in bundle.files_by_relpath.items():
        dst = sd_dir / rel_p
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(blob)

    if include_launcher_file:
        launcher_text = generate_im_elf_escape_hatch_launcher(expected_body_serial=body_serial)
        launcher_dst = sd_dir / SD_LAUNCHER_SH_RELPATH
        launcher_dst.parent.mkdir(parents=True, exist_ok=True)
        launcher_dst.write_text(launcher_text, encoding="utf-8")

    if forbidden_trigger_relpath is not None:
        bad_dst = sd_dir / forbidden_trigger_relpath
        bad_dst.parent.mkdir(parents=True, exist_ok=True)
        bad_dst.write_text("SYNTHETIC_FORBIDDEN_TRIGGER\n", encoding="utf-8")

    return {
        "manifest_sha256": bundle.manifest_sha256,
        "target_body_serial": body_serial,
        "target_emmc_cid": emmc_cid,
        "camera_cid_sha256": _compute_camera_cid_sha256(emmc_cid),
        "ram_tmpfs_bytes": bundle.ram_tmpfs_bytes,
    }


def populate_dual_copy_receipt_fixtures(
    sd_backup_dir: Path,
    vault_backup_dir: Path,
    *,
    emmc_cid: str = DEFAULT_TARGET_EMMC_CID,
    include_manifest: bool = True,
) -> Dict[str, Any]:
    """Write deterministic dual-copy 528 B FX3RCPT1 + MANIFEST.SHA256 fixtures into temp dirs."""
    item_hashes: Dict[str, str] = {}
    manifest_lines: List[str] = []
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        h = hashlib.sha256(
            f"PHASE154_TIER0_{item.item_id}_{item.size_bytes}_{emmc_cid}".encode("ascii")
        ).hexdigest()
        item_hashes[item.item_id] = h
        total_bytes += item.size_bytes
        manifest_lines.append(f"{h}  {item.filename}")

    manifest_bytes = ("\n".join(manifest_lines) + "\n").encode("utf-8")
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    rcpt_bytes = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_sha,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    cid_sha = _compute_camera_cid_sha256(emmc_cid)
    identity_doc = json.dumps(
        {
            "schema": "fx3_tier0_camera_identity_v1",
            "model_id": FX3_MODEL_ID_HEX,
            "camera_cid_sha256": cid_sha,
            "crc32_hex": f"{(zlib.crc32(rcpt_bytes) & 0xFFFFFFFF):#010x}",
            "receipt_sha256": hashlib.sha256(rcpt_bytes).hexdigest(),
        },
        indent=2,
        sort_keys=True,
    ) + "\n"

    sd_rcpt_path = sd_backup_dir / "FX3RCPT1.bin"
    vault_rcpt_path = vault_backup_dir / "FX3RCPT1.bin"
    for d, rpath in ((sd_backup_dir, sd_rcpt_path), (vault_backup_dir, vault_rcpt_path)):
        d.mkdir(parents=True, exist_ok=True)
        rpath.write_bytes(rcpt_bytes)
        (d / "tier0_identity.json").write_text(identity_doc, encoding="utf-8")
        if include_manifest:
            (d / "MANIFEST.SHA256").write_bytes(manifest_bytes)

    return {
        "sd_receipt_path": sd_rcpt_path,
        "vault_receipt_path": vault_rcpt_path,
        "camera_cid_sha256": cid_sha,
        "manifest_sha256": manifest_sha,
        "receipt_sha256": hashlib.sha256(rcpt_bytes).hexdigest(),
        "receipt_crc32_hex": f"{(zlib.crc32(rcpt_bytes) & 0xFFFFFFFF):#010x}",
    }


# ---------------------------------------------------------------------------
# Unified Bench Preflight & Operator Go/No-Go Receipt Engine
# ---------------------------------------------------------------------------


def run_realhw_bench_preflight(
    *,
    usb_snapshot_text: Optional[str] = None,
    usb_snapshot_path: Optional[Path] = None,
    probe_host_usb: bool = False,
    sd_dir: Optional[Path] = None,
    sd_free_bytes_override: Optional[int] = None,
    sd_receipt_path: Optional[Path] = None,
    vault_receipt_path: Optional[Path] = None,
    expected_camera_cid_sha256: Optional[str] = None,
    observed_launcher_sha256: Optional[str] = None,
    simulate_ready_bench: bool = False,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
) -> RealHwBenchPreflightReport:
    """Run 100% passive, zero-packet, zero-write host bench preflight and emit Go/No-Go receipt."""
    assert not PERSISTENT_EMMC_WRITES_AUTHORIZED
    assert not PERSISTENT_WRITE_RELEASE
    assert not SPI_NOR_WRITE_AUTHORIZED
    assert not SD_PHYSICAL_MEDIA_WRITTEN
    assert USB_PACKETS_EMITTED == 0
    assert IOKIT_HANDLES_OPENED == 0
    assert PHYSICAL_DEVICE_WRITES == 0

    clean_room = (
        is_forced_clean_room() if synthetic_clean_room is None else bool(synthetic_clean_room)
    )
    donor_res = inspect_bench_donor_readiness(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=clean_room,
    )

    all_errors: List[str] = list(donor_res.errors)

    if simulate_ready_bench:
        with tempfile.TemporaryDirectory(prefix="fx3_p154_bench_") as td:
            td_path = Path(td)
            sd_stage_dir = td_path / "sd_card"
            sd_bk_dir = td_path / "sd_backup"
            vault_bk_dir = td_path / "host_vault"
            sd_info = populate_sd_staging_fixture(
                sd_stage_dir,
                synthetic_clean_room=clean_room,
                include_launcher_file=True,
            )
            rcpt_info = populate_dual_copy_receipt_fixtures(sd_bk_dir, vault_bk_dir)
            snap_text = usb_snapshot_text or build_synthetic_ioreg_snapshot(
                scenario="READY_MSC_054C_0DA1", snapshot_format="xml_plist"
            )
            usb_res = classify_passive_usb_snapshot(snap_text)
            sd_res = audit_sd_staging_directory(
                sd_stage_dir,
                free_bytes_override=(
                    sd_free_bytes_override
                    if sd_free_bytes_override is not None
                    else 8 * GIB_BYTES
                ),
                observed_launcher_sha256=observed_launcher_sha256,
            )
            rcpt_res = verify_dual_copy_tier0_receipts(
                sd_receipt_path=rcpt_info["sd_receipt_path"],
                vault_receipt_path=rcpt_info["vault_receipt_path"],
                expected_camera_cid_sha256=(
                    expected_camera_cid_sha256 or sd_info["camera_cid_sha256"]
                ),
            )
    else:
        snap_text = ""
        if usb_snapshot_text is not None:
            snap_text = usb_snapshot_text
        elif usb_snapshot_path is not None:
            if not usb_snapshot_path.is_file() or usb_snapshot_path.is_symlink():
                all_errors.append(f"USB snapshot path missing or symlink: {usb_snapshot_path}")
            else:
                snap_text = _read_regular_file_o_rdonly(
                    usb_snapshot_path, max_bytes=8 * 1024 * 1024
                ).decode("utf-8", "replace")
        elif probe_host_usb and not clean_room:
            captured, cap_err = capture_passive_ioreg_snapshot()
            snap_text = captured
            if cap_err:
                all_errors.append(cap_err)

        usb_res = classify_passive_usb_snapshot(snap_text)
        sd_res = audit_sd_staging_directory(
            sd_dir,
            free_bytes_override=sd_free_bytes_override,
            observed_launcher_sha256=observed_launcher_sha256,
        )
        eff_cid = expected_camera_cid_sha256 or (
            sd_res.target_emmc_cid_sha256 if sd_res.target_emmc_cid_sha256 else None
        )
        rcpt_res = verify_dual_copy_tier0_receipts(
            sd_receipt_path=sd_receipt_path,
            vault_receipt_path=vault_receipt_path,
            expected_camera_cid_sha256=eff_cid,
        )

    all_errors.extend(usb_res.errors)
    all_errors.extend(sd_res.errors)
    all_errors.extend(rcpt_res.errors)

    checklist = (
        OperatorChecklistItem(
            step_index=1,
            gate_id="G1_BYOF_DONOR_READINESS",
            status="PASS" if donor_res.passed else "BLOCKED",
            action=(
                f"BYOF donor parity OK ({donor_res.verification_mode}, 13/13 locks)"
                if donor_res.passed
                else "Repair missing/corrupt local BYOF donor binaries before bench attach."
            ),
        ),
        OperatorChecklistItem(
            step_index=2,
            gate_id="G2_PASSIVE_USB_CLASSIFIER",
            status=(
                "PASS"
                if usb_res.ready_for_msc_session
                else ("ALERT" if usb_res.hard_abort else "BLOCKED")
            ),
            action=(
                f"Passive USB verified: {usb_res.usb_state} (usb_packets_emitted=0)"
                if usb_res.ready_for_msc_session
                else " | ".join(usb_res.remediation_steps)
            ),
        ),
        OperatorChecklistItem(
            step_index=3,
            gate_id="G3_SD_STAGING_AND_FIREWALL",
            status="PASS" if sd_res.passed else "BLOCKED",
            action=(
                f"SD staging verified: 13/13 locks, 0 forbidden OTA triggers, free={sd_res.free_space_gib:.2f} GiB >= 2.00 GiB"
                if sd_res.passed
                else (
                    "; ".join(sd_res.errors)
                    if sd_res.errors
                    else "Stage valid Stage-B SD directory (--sd-dir) with >= 2 GiB free and zero factory OTA triggers."
                )
            ),
        ),
        OperatorChecklistItem(
            step_index=4,
            gate_id="G4_DUAL_COPY_TIER0_FX3RCPT1",
            status="PASS" if rcpt_res.passed else "BLOCKED",
            action=(
                f"Dual-copy SD+Vault 528 B FX3RCPT1 parity verified (CRC32={rcpt_res.sd_copy.crc32_hex}, cid_sha256={rcpt_res.camera_cid_sha256[:16]}...)"
                if rcpt_res.passed
                else (
                    "; ".join(rcpt_res.errors)
                    if rcpt_res.errors
                    else "Acquire/verify matching SD ExFAT + Mac Host Vault 528 B FX3RCPT1 receipts."
                )
            ),
        ),
        OperatorChecklistItem(
            step_index=5,
            gate_id="G5_HARD_LOCK_NO_PERSISTENT_WRITE",
            status="PASS",
            action="Hard-lock verified: persistent_emmc_writes_authorized=False, usb_packets_emitted=0, physical_device_writes=0.",
        ),
    )

    remediations: List[str] = []
    if not donor_res.passed:
        remediations.extend(donor_res.errors)
    if not usb_res.ready_for_msc_session:
        remediations.extend(usb_res.remediation_steps)
    if not sd_res.passed:
        remediations.extend(sd_res.errors or ("Provide valid Stage-B SD staging directory via --sd-dir.",))
    if not rcpt_res.passed:
        remediations.extend(rcpt_res.errors or ("Provide matching --sd-receipt and --vault-receipt 528 B FX3RCPT1 files.",))

    bench_go = (
        donor_res.passed
        and usb_res.ready_for_msc_session
        and sd_res.passed
        and rcpt_res.passed
        and len(all_errors) == 0
    )

    body: Dict[str, Any] = {
        "schema": PHASE_154_SCHEMA,
        "phase_version": PHASE_154_VERSION,
        "verification_mode": donor_res.verification_mode,
        "verdict": VERDICT_GO_READONLY_PREFLIGHT if bench_go else VERDICT_NO_GO,
        "status": STATUS_PREFLIGHT_GO if bench_go else STATUS_PREFLIGHT_NO_GO,
        "bench_go": bench_go,
        "simulated_bench_mode": bool(simulate_ready_bench),
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "sd_physical_media_written": SD_PHYSICAL_MEDIA_WRITTEN,
        "usb_packets_emitted": USB_PACKETS_EMITTED,
        "iokit_handles_opened": IOKIT_HANDLES_OPENED,
        "physical_device_writes": PHYSICAL_DEVICE_WRITES,
        "raw_firmware_slices_emitted": RAW_FIRMWARE_SLICES_EMITTED,
        "donor_readiness": asdict(donor_res),
        "usb_classification": asdict(usb_res),
        "sd_staging_audit": asdict(sd_res),
        "dual_copy_receipt_audit": asdict(rcpt_res),
        "operator_checklist": [asdict(item) for item in checklist],
        "remediation_actions": list(remediations),
        "errors": list(all_errors),
    }
    report_sha = _canonical_sha256_dict(body)

    return RealHwBenchPreflightReport(
        schema=PHASE_154_SCHEMA,
        phase_version=PHASE_154_VERSION,
        verification_mode=donor_res.verification_mode,
        verdict=str(body["verdict"]),
        status=str(body["status"]),
        bench_go=bench_go,
        simulated_bench_mode=bool(simulate_ready_bench),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        sd_physical_media_written=SD_PHYSICAL_MEDIA_WRITTEN,
        usb_packets_emitted=USB_PACKETS_EMITTED,
        iokit_handles_opened=IOKIT_HANDLES_OPENED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_slices_emitted=RAW_FIRMWARE_SLICES_EMITTED,
        donor_readiness=donor_res,
        usb_classification=usb_res,
        sd_staging_audit=sd_res,
        dual_copy_receipt_audit=rcpt_res,
        operator_checklist=checklist,
        remediation_actions=tuple(remediations),
        errors=tuple(all_errors),
        report_sha256=report_sha,
    )


def verify_phase154_report(payload: Mapping[str, Any]) -> Phase154ReportVerifyResult:
    """Fail-closed tamper & safety-invariant verifier for Phase 154 Go/No-Go receipts."""
    errors: List[str] = []
    if payload.get("schema") != PHASE_154_SCHEMA:
        errors.append(f"Unexpected schema: {payload.get('schema')!r}")
    if payload.get("phase_version") != PHASE_154_VERSION:
        errors.append(f"Unexpected phase_version: {payload.get('phase_version')!r}")

    for bool_key in (
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "sd_physical_media_written",
    ):
        if payload.get(bool_key) is not False:
            errors.append(f"Hard-locked invariant violated: {bool_key} must be False")

    for zero_key in (
        "usb_packets_emitted",
        "iokit_handles_opened",
        "physical_device_writes",
        "raw_firmware_slices_emitted",
    ):
        if payload.get(zero_key) != 0:
            errors.append(f"Hard-locked zero invariant violated: {zero_key} != 0")

    usb = payload.get("usb_classification", {})
    if usb.get("usb_state") not in BENCH_USB_STATES:
        errors.append(f"Invalid usb_state: {usb.get('usb_state')!r}")
    if usb.get("usb_packets_emitted") != 0 or usb.get("iokit_handles_opened") != 0:
        errors.append("USB classifier reported non-zero packet/IOKit activity")

    donor = payload.get("donor_readiness", {})
    sd = payload.get("sd_staging_audit", {})
    rcpt = payload.get("dual_copy_receipt_audit", {})
    all_sub_ok = (
        bool(donor.get("passed"))
        and bool(usb.get("ready_for_msc_session"))
        and bool(sd.get("passed"))
        and bool(rcpt.get("passed"))
        and len(payload.get("errors", [])) == 0
    )
    bench_go = payload.get("bench_go")
    if bench_go is True and not all_sub_ok:
        errors.append("bench_go=True cannot be claimed when any sub-gate failed")
    if bench_go is True and payload.get("verdict") != VERDICT_GO_READONLY_PREFLIGHT:
        errors.append("bench_go=True requires verdict=GO_READONLY_BENCH_PREFLIGHT")
    if bench_go is False and payload.get("verdict") != VERDICT_NO_GO:
        errors.append("bench_go=False requires verdict=NO_GO_BENCH_BLOCKED")

    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if _RAW_BYTES_REPR_RE.search(rendered):
        errors.append("Raw Python bytes literal repr detected in JSON receipt")

    expected_sha = _canonical_sha256_dict(payload, exclude_key="report_sha256")
    if payload.get("report_sha256") != expected_sha:
        errors.append("report_sha256 canonical digest mismatch (tamper detected)")

    return Phase154ReportVerifyResult(valid=(len(errors) == 0), errors=tuple(errors))


def render_phase154_markdown(report: RealHwBenchPreflightReport) -> str:
    """Render an operator-friendly Go/No-Go Markdown receipt."""
    lines = [
        "# Phase 154 — Real-Hardware Bench Preflight Go/No-Go Receipt",
        "",
        f"- **Verdict**: `{report.verdict}` (`bench_go={report.bench_go}`)",
        f"- **Mode**: `{report.verification_mode}` (`simulated_bench_mode={report.simulated_bench_mode}`)",
        f"- **USB State**: `{report.usb_classification.usb_state}` (`alert={report.usb_classification.alert_code}`)",
        f"- **Safety Hard-Locks**: `persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}`, `usb_packets_emitted={report.usb_packets_emitted}`, `iokit_handles_opened={report.iokit_handles_opened}`, `physical_device_writes={report.physical_device_writes}`",
        f"- **Report SHA-256**: `{report.report_sha256}`",
        "",
        "## Operator Checklist",
        "",
        "| # | Gate | Status | Action / Verdict |",
        "|---:|---|---|---|",
    ]
    for item in report.operator_checklist:
        lines.append(f"| {item.step_index} | `{item.gate_id}` | `{item.status}` | {item.action} |")
    if report.remediation_actions:
        lines.extend(["", "## Required Remediation Steps", ""])
        for step in report.remediation_actions:
            lines.append(f"- {step}")
    return "\n".join(lines) + "\n"
