"""Phase 184 — Pillar 25 (Real-Hardware Air-Gapped Bench Guard):
SD/CFexpress BYOF Bundle Cryptographic Manifest Verifier (`FX3BNDL1`),
Dual-Copy `FX3RCPT1` Cross-Binding, AppleDouble (`._*`) Hygiene Scrubber,
ELF64 AArch64 Shim Validator & `BODYDATA.DAT` Mutual-Exclusion Firewall.

Before an operator ever inserts a staging CFexpress Type A / SDXC V90 card
into a physical Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`), this
offline air-gapped bench verifier proves:

1. **Bounded `O_RDONLY` Donor Inspection (`< 0.15s`) + Clean-Room Fallback**:
   - Inspects pinned local FX3 `Ver. 7.02` & Stage-B donor artifacts strictly via
     `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` with `fstat`
     stability checks and bounded (`<= 4096 B`) header reads for multi-hundred-MB
     images (`nflasha5.img`, `nflasha15.img`, `fx3-7.02-BODYDATA.DAT`), leaking
     zero raw proprietary firmware bytes (`raw_firmware_bytes_leaked == 0`).
   - Automatically falls back to deterministic `CLEAN_ROOM_SYNTHETIC` metadata
     when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor roots are absent.

2. **Pillar 25A — Per-Camera `FX3RCPT1` Hardware-Bound BYOF SD Manifest (`FX3BNDL1`) (8 Scenarios)**:
   - Binds the staging SD bundle manifest (`FX3BNDL1`, HMAC-SHA256 + IEEE CRC32)
     to the exact target camera's dual-copy `FX3RCPT1` (`528 B`) Tier-0 receipt
     fingerprint (`serial_hash`, `model_id == 0x91030080`, `body_fw == "7.02"`,
     `p2_setting_h0_sha256`, `p5_wbi2_h0_sha256`, `p12_cert_h0_sha256`,
     `p15_usr_h0_sha256`, `p18_lens_h0_sha256`, `st_dev_primary != st_dev_secondary`).
   - Fail-closed rejects cross-camera SD transplant (`CAMERA_SERIAL_RECEIPT_MISMATCH`),
     non-FX3 model IDs (`0x91030084` FX30 / `0x91020080` FX6), `< 7.02` body
     firmware, single-media unverified cold backup (`st_dev_primary == st_dev_secondary`
     or divergent copy B), Tier-0 partition `h0` mismatch, and `FX3BNDL1` CRC32/HMAC
     tampering.

3. **Pillar 25B — macOS/Linux ExFAT Staging Hygiene, AppleDouble (`._*`) Scrubber & `BODYDATA.DAT` Firewall (8 Scenarios)**:
   - Detects and rejects (and safely scrubs in isolated `TemporaryDirectory` dry-run)
     macOS `.DS_Store`, `.Spotlight-V100`, `.fseventsd`, `.Trashes`,
     `.TemporaryItems`, and `._*` AppleDouble resource-fork files inside
     `FX6_STAGEB/` that would break `dlopen` / `scandir` on SCEL Linux `4.9.337-scel+`.
   - Verifies ELF64 `EM_AARCH64` (`e_machine == 183`, little-endian) headers,
     non-zero size, `libJit.so <= 64 KiB` (`65,536 B`) ceiling, and exact SHA-256
     digests of every staged userland shim (`fx6-stage-a-verify`, `libJit.so`,
     `libgrm-fbinit9.so`).
   - Enforces Slot-1 `BODYDATA.DAT` (`\\x89UFU`) mutual exclusion (never co-arm
     dual-boot install / `p1` service trigger while `BODYDATA.DAT` or
     `BODYDATA (1).DAT` sits on the card root) and zero network socket usage
     (`airgap_sockets_opened == 0`).

4. **Hard-Locked Safety Policy Invariants**:
   - `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
   - `SPI_NOR_WRITE_AUTHORIZED = False`
   - `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
   - `ISP_WRITE_AUTHORIZED = False`
   - `OTP_FUSE_TOUCHES = 0`
   - `RPMB_COUNTER_INCREMENTS = 0`
   - `PHYSICAL_USB_PACKETS_EMITTED = 0`
   - `PHYSICAL_DEVICE_WRITES = 0`
   - `RAW_FIRMWARE_BYTES_LEAKED = 0`
   - `AIRGAP_SOCKETS_OPENED = 0`
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import tempfile
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import zlib

from .files import is_forced_clean_room, local_path, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import (
    build_fx3rcpt1_receipt,
    parse_fx3rcpt1_receipt,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE184_SCHEMA: str = "fx3-realhw-airgap-sd-bundle-manifest-verifier-v1"
PHASE184_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
ISP_WRITE_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
ALLOW_PERSISTENT_JIRITSU_WRITES: bool = False
ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS: bool = False
LIVE_USB_IOKIT_TRANSMIT_ENABLED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
AIRGAP_SOCKETS_OPENED: int = 0

# Hardware, FX3BNDL1 & ExFAT Hygiene Constants
P184_BOUNDED_HEADER_BYTES: int = 4096
P184_FX3_MODEL_ID: int = 0x91030080
P184_FX30_MODEL_ID: int = 0x91030084
P184_FX6_MODEL_ID: int = 0x91020080
P184_FX3_MODEL_NAME: str = "ILME-FX3"
P184_REQUIRED_BODY_FW: str = "7.02"
P184_KERNEL_RELEASE: str = "4.9.337-scel+"

P184_MANIFEST_MAGIC: str = "FX3BNDL1"
P184_MANIFEST_VERSION: int = 1
P184_MANIFEST_FILENAME: str = "FX3BNDL1.json"
P184_FX3RCPT1_MAGIC: bytes = b"FX3RCPT1"
P184_FX3RCPT1_BYTES: int = 528

P184_STAGEB_DIR_NAME: str = "FX6_STAGEB"
P184_REQUIRED_SHIMS: Tuple[str, ...] = (
    "fx6-stage-a-verify",
    "libJit.so",
    "libgrm-fbinit9.so",
)
P184_LIBJIT_MAX_BYTES: int = 65_536  # 64 KiB
P184_ELF_MAGIC: bytes = b"\x7fELF"
P184_ELF_CLASS_64: int = 2
P184_ELF_DATA_LSB: int = 1
P184_ELF_TYPE_EXEC: int = 2
P184_ELF_TYPE_DYN: int = 3
P184_ELF_MACHINE_AARCH64: int = 183

P184_FORBIDDEN_MACOS_NAMES: Tuple[str, ...] = (
    ".DS_Store",
    ".Spotlight-V100",
    ".fseventsd",
    ".Trashes",
    ".TemporaryItems",
)
P184_APPLEDOUBLE_PREFIX: str = "._"
P184_FORBIDDEN_BODYDATA_NAMES: Tuple[str, ...] = (
    "BODYDATA.DAT",
    "BODYDATA (1).DAT",
    "BODYDATA_OLD.DAT",
)
P184_UFU_MAGIC: bytes = b"\x89UFU\r\n\x1a\n"
P184_DEFAULT_AIRGAP_BENCH_SECRET: bytes = b"FX3-AIRGAP-BENCH-HMAC-V1"

P184_DONOR_INSPECT_BUDGET_SECONDS: float = 0.15
P184_CONCURRENT_CEILING_SECONDS: float = 6.0

# Pinned Local Donor Relpaths & Digests (strictly O_RDONLY, zero raw bytes emitted)
P184_DONOR_LIBGRM_FBINIT9_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/"
    "fx6-boot-readiness/early-kernel/cp-helper-agnostic/grm-fbinit/libgrm-fbinit9.so"
)
P184_DONOR_LIBJIT_TEST_RELPATH: str = (
    "sony-firmware-20261024/stage288-jiritsu-readonly-payload/payload/libJit_test.so"
)
P184_DONOR_LIBJIRITSU_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libJiritsu.so"
)
P184_DONOR_PARTINF_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0300_partconf/partinf.conf"
)
P184_DONOR_WBI2_RELPATH: str = "sony-firmware-20261024/stage2/extraction/nflasha5.img"
P184_DONOR_NFLASHA15_RELPATH: str = "sony-firmware-20261024/stage2/extraction/nflasha15.img"
P184_DONOR_BODYDATA_RELPATH: str = "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"

P184_PINNED_LIBGRM_FBINIT9_BYTES: int = 7_664
P184_PINNED_LIBGRM_FBINIT9_SHA256: str = "e273a4fe254bc212db2c1b0914bb5788da67262acd10104724f7e974bac78991"
P184_PINNED_LIBJIT_TEST_BYTES: int = 8_345
P184_PINNED_LIBJIT_TEST_SHA256: str = "05000a0ecceaa5004385b71fbeb2b15859bda7418e227a3d90238da31bc4cd7a"
P184_PINNED_LIBJIRITSU_BYTES: int = 225_200
P184_PINNED_LIBJIRITSU_SHA256: str = "bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9"
P184_PINNED_PARTINF_BYTES: int = 3_999
P184_PINNED_PARTINF_SHA256: str = "3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189"
P184_PINNED_WBI2_BYTES: int = 209_112_512
P184_PINNED_WBI2_HDR4K_SHA256: str = "e6e241c79507d275caaa79e673893ed690a7431edb4cae253920b9be43129f6a"
P184_PINNED_NFLASHA15_BYTES: int = 479_846_400
P184_PINNED_NFLASHA15_HDR4K_SHA256: str = "6d05ebbd28c554d1d9dcc54503face9af111170befaf2ca2a19c52d7bd8910d6"
P184_PINNED_BODYDATA_BYTES: int = 811_876_768
P184_PINNED_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"

# Pillar 25A & 25B Scenario IDs (8 + 8 = 16 Scenarios)
P184_PILLAR_25A_SCENARIO_IDS: Tuple[str, ...] = (
    "P25A1_HAPPY_FX3_702_DUAL_COPY_FX3RCPT1_BOUND_FX3BNDL1",
    "P25A2_BLOCKED_CROSS_CAMERA_SERIAL_RECEIPT_MISMATCH",
    "P25A3_BLOCKED_NON_FX3_MODEL_FX30_0X91030084",
    "P25A4_BLOCKED_NON_FX3_MODEL_FX6_0X91020080",
    "P25A5_BLOCKED_BODY_FW_BELOW_702",
    "P25A6_BLOCKED_SINGLE_MEDIA_UNVERIFIED_COLD_BACKUP",
    "P25A7_BLOCKED_TIER0_PARTITION_H0_HASH_MISMATCH",
    "P25A8_BLOCKED_FX3BNDL1_HMAC_OR_CRC32_TAMPER",
)

P184_PILLAR_25B_SCENARIO_IDS: Tuple[str, ...] = (
    "P25B1_HAPPY_CLEAN_EXFAT_STAGEB_SHIMS_AND_ZERO_SOCKET",
    "P25B2_BLOCKED_MACOS_DS_STORE_AND_APPLEDOUBLE_POLLUTION",
    "P25B3_SCRUBBED_TEMPDIR_APPLEDOUBLE_SPOTLIGHT_FSEVENTSD",
    "P25B4_BLOCKED_TRUNCATED_SHIM_OR_SHA256_BITROT",
    "P25B5_BLOCKED_WRONG_ARCH_NON_AARCH64_SHIM",
    "P25B6_BLOCKED_LIBJIT_EXCEEDS_64KIB_CEILING",
    "P25B7_BLOCKED_BODYDATA_DAT_CO_STAGING_WITH_P1_TRIGGER",
    "P25B8_BLOCKED_AIRGAP_NETWORK_SOCKET_OR_UNSAFE_WRITE_ATTEMPT",
)

# Status & Fail-Closed Error Codes
P184_STATUS_VERIFIED_SUITE: str = "VERIFIED_PILLAR25_AIRGAP_SD_BUNDLE_MANIFEST"
P184_STATUS_FAIL_SUITE: str = "FAIL_PILLAR25_AIRGAP_SD_BUNDLE_MANIFEST"
P184_STATUS_VERIFIED_25A: str = "VERIFIED_FX3RCPT1_BOUND_FX3BNDL1_MANIFEST"
P184_STATUS_REJECTED_25A: str = "REJECTED_FX3RCPT1_BOUND_FX3BNDL1_MANIFEST"
P184_STATUS_VERIFIED_25B: str = "VERIFIED_EXFAT_HYGIENE_SHIMS_AND_BODYDATA_FIREWALL"
P184_STATUS_REJECTED_25B: str = "REJECTED_EXFAT_HYGIENE_SHIMS_OR_BODYDATA_FIREWALL"

CAMERA_SERIAL_RECEIPT_MISMATCH: str = "CAMERA_SERIAL_RECEIPT_MISMATCH"
NON_FX3_MODEL_ID_FORBIDDEN: str = "NON_FX3_MODEL_ID_FORBIDDEN"
BODY_FIRMWARE_VERSION_NOT_702: str = "BODY_FIRMWARE_VERSION_NOT_702"
SINGLE_MEDIA_COLD_BACKUP_UNVERIFIED: str = "SINGLE_MEDIA_COLD_BACKUP_UNVERIFIED"
TIER0_PARTITION_H0_MISMATCH: str = "TIER0_PARTITION_H0_MISMATCH"
FX3BNDL1_CRC32_OR_HMAC_INVALID: str = "FX3BNDL1_CRC32_OR_HMAC_INVALID"
MACOS_EXFAT_JUNK_DETECTED: str = "MACOS_EXFAT_JUNK_DETECTED"
SHIM_NOT_ELF64_AARCH64: str = "SHIM_NOT_ELF64_AARCH64"
SHIM_ELF_TRUNCATED_OR_SHA256_MISMATCH: str = "SHIM_ELF_TRUNCATED_OR_SHA256_MISMATCH"
LIBJIT_EXCEEDS_64KIB_LIMIT: str = "LIBJIT_EXCEEDS_64KIB_LIMIT"
BODYDATA_DAT_MUTUAL_EXCLUSION_VIOLATION: str = "BODYDATA_DAT_MUTUAL_EXCLUSION_VIOLATION"
AIRGAP_NETWORK_VIOLATION: str = "AIRGAP_NETWORK_VIOLATION"
P184_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_PILLAR25_SAFETY_POLICY_VIOLATION"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _canonical_sha256(obj: Any) -> str:
    return sha256(_canonical_json_bytes(obj)).hexdigest()


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _open_rdonly_regular(path: Path, *, allow_donor_roots: bool = True) -> Tuple[int, os.stat_result]:
    if allow_donor_roots:
        checked = local_path(path, allow_donor_roots=True)
    else:
        checked = Path(os.path.abspath(path))
        _need(not checked.is_symlink(), "symlink rejected")
    _need(hasattr(os, "O_NOFOLLOW"), "POSIX O_NOFOLLOW is required")
    fd = os.open(checked, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        _need(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, "single-link regular file required")
        return fd, st
    except Exception:
        os.close(fd)
        raise


def _verify_fstat_unchanged(fd: int, st_before: os.stat_result) -> None:
    st_after = os.fstat(fd)
    for fld in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode", "st_nlink"):
        _need(getattr(st_before, fld) == getattr(st_after, fld), f"file changed during read ({fld})")


def _read_bounded_donor_rdonly(
    relpath: str,
    *,
    max_bytes: Optional[int] = None,
    max_full_limit: int = 2 * 1024 * 1024,
) -> Tuple[bytes, int, str, str]:
    p = resolve_donor_path(relpath, require_file=True)
    _need(p is not None and p.is_file(), f"missing donor file: {relpath}")
    fd, st_before = _open_rdonly_regular(p, allow_donor_roots=True)
    try:
        total_sz = int(st_before.st_size)
        if max_bytes is not None:
            head_len = min(total_sz, max_bytes)
            buf = os.pread(fd, head_len, 0)
            _need(len(buf) == head_len, "short bounded read on donor")
            _verify_fstat_unchanged(fd, st_before)
            h4k = sha256(buf).hexdigest()
            return buf, total_sz, h4k, h4k
        _need(total_sz <= max_full_limit, f"donor exceeds bounded full-read ceiling: {total_sz}")
        with os.fdopen(os.dup(fd), "rb") as f:
            buf = f.read(total_sz + 1)
        _need(len(buf) == total_sz, "donor read size mismatch")
        _verify_fstat_unchanged(fd, st_before)
        full_sha = sha256(buf).hexdigest()
        hdr_sha = sha256(buf[:P184_BOUNDED_HEADER_BYTES]).hexdigest()
        return buf, total_sz, full_sha, hdr_sha
    finally:
        os.close(fd)


def _derive_fx3bndl1_hmac_key(
    *,
    receipt_bytes: bytes,
    serial_hash: str,
    p2_setting_h0_sha256: str,
    p5_wbi2_h0_sha256: str,
    p12_cert_h0_sha256: str,
    p15_usr_h0_sha256: str,
    p18_lens_h0_sha256: str,
    bench_secret: bytes = P184_DEFAULT_AIRGAP_BENCH_SECRET,
) -> bytes:
    h = sha256()
    h.update(b"FX3BNDL1-AIRGAP-BIND-V1|")
    h.update(bench_secret)
    h.update(b"|")
    h.update(receipt_bytes)
    h.update(b"|")
    h.update(serial_hash.encode("ascii"))
    h.update(b"|")
    for digest in (
        p2_setting_h0_sha256,
        p5_wbi2_h0_sha256,
        p12_cert_h0_sha256,
        p15_usr_h0_sha256,
        p18_lens_h0_sha256,
    ):
        h.update(digest.encode("ascii"))
    return h.digest()


# ---------------------------------------------------------------------------
# Dataclasses (100% JSON-Safe, Zero Raw Proprietary Firmware Bytes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase184DonorArtifactDigest:
    artifact_id: str
    relpath: str
    source_mode: str
    access_mode: str
    byte_length: int
    sha256_digest: str
    header_sha256: str
    verified_markers: Tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class Phase184DonorSnapshot:
    verification_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    libgrm_fbinit9_elf64_aarch64_ok: bool
    libjit_test_under_64k_ok: bool
    libjiritsu_elf64_aarch64_ok: bool
    partinf_30_partitions_ok: bool
    wbi2_header_ok: bool
    nflasha15_ext2_magic_ok: bool
    bodydata_ufu_magic_ok: bool
    elapsed_seconds: float
    artifacts: Tuple[Phase184DonorArtifactDigest, ...]
    snapshot_sha256: str
    all_passed: bool
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CameraTier0IdentityProfile:
    serial_hash: str
    model_id: int
    body_fw: str
    p2_setting_h0_sha256: str
    p5_wbi2_h0_sha256: str
    p12_cert_h0_sha256: str
    p15_usr_h0_sha256: str
    p18_lens_h0_sha256: str
    emmc_cid_sha256: str
    manifest_sha256: str
    st_dev_primary: int
    st_dev_secondary: int
    receipt_copy_a_hex: str
    receipt_copy_b_hex: str


@dataclass(frozen=True)
class BundleFileEntry:
    relpath: str
    byte_size: int
    sha256_digest: str
    crc32_u32: int


@dataclass(frozen=True)
class Fx3Bndl1Manifest:
    magic: str
    version: int
    target_model_id: int
    target_body_fw: str
    target_serial_hash: str
    receipt_sha256: str
    st_dev_primary: int
    st_dev_secondary: int
    p2_setting_h0_sha256: str
    p5_wbi2_h0_sha256: str
    p12_cert_h0_sha256: str
    p15_usr_h0_sha256: str
    p18_lens_h0_sha256: str
    bundle_entries: Tuple[BundleFileEntry, ...]
    payload_crc32: int
    hmac_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Fx3Bndl1VerificationReport:
    passed: bool
    bundle_authorized: bool
    manifest_magic_ok: bool
    model_id_fx3_ok: bool
    body_fw_702_ok: bool
    dual_copy_receipt_ok: bool
    distinct_st_dev_ok: bool
    serial_binding_ok: bool
    tier0_5surface_h0_ok: bool
    crc32_ok: bool
    hmac_sha256_ok: bool
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    isp_write_authorized: bool = ISP_WRITE_AUTHORIZED
    otp_fuse_touches: int = OTP_FUSE_TOUCHES
    rpmb_counter_increments: int = RPMB_COUNTER_INCREMENTS
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES
    airgap_sockets_opened: int = AIRGAP_SOCKETS_OPENED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar25AScenarioOutcome:
    scenario_id: str
    passed: bool
    bundle_authorized: bool
    blocked_codes: Tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Pillar25ABindingSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar25AScenarioOutcome, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Elf64ShimHeaderInfo:
    valid: bool
    byte_size: int
    ei_class: int
    ei_data: int
    e_type: int
    e_machine: int
    is_aarch64: bool
    within_size_ceiling: bool
    sha256_digest: str
    sha256_matched: bool
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ExfatScrubDryRunReport:
    performed_in_tempdir: bool
    removed_count: int
    removed_relpaths: Tuple[str, ...]
    preserved_files_count: int
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExfatStagingHygieneReport:
    passed: bool
    staging_ready: bool
    exfat_junk_free: bool
    appledouble_count: int
    macos_metadata_hits: Tuple[str, ...]
    shims_all_elf64_aarch64_ok: bool
    libjit_under_64kib_ok: bool
    shim_digests: Dict[str, str]
    bodydata_mutual_exclusion_ok: bool
    bodydata_conflicts: Tuple[str, ...]
    airgap_zero_sockets_ok: bool
    airgap_sockets_opened: int
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    isp_write_authorized: bool = ISP_WRITE_AUTHORIZED
    otp_fuse_touches: int = OTP_FUSE_TOUCHES
    rpmb_counter_increments: int = RPMB_COUNTER_INCREMENTS
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar25BScenarioOutcome:
    scenario_id: str
    passed: bool
    staging_ready: bool
    blocked_codes: Tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Pillar25BHygieneSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar25BScenarioOutcome, ...]
    airgap_sockets_opened: int = AIRGAP_SOCKETS_OPENED
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar25AirgapSdBundleReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    under_6s_budget: bool
    donor_snapshot: Phase184DonorSnapshot
    pillar_25a_fx3bndl1_binding: Pillar25ABindingSuiteResult
    pillar_25b_exfat_hygiene: Pillar25BHygieneSuiteResult
    suite_sha256: str
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    isp_write_authorized: bool = ISP_WRITE_AUTHORIZED
    persistent_write_release: bool = PERSISTENT_WRITE_RELEASE
    allow_boot_partition_targeting: bool = ALLOW_BOOT_PARTITION_TARGETING
    allow_destructive_fastboot: bool = ALLOW_DESTRUCTIVE_FASTBOOT
    allow_persistent_jiritsu_writes: bool = ALLOW_PERSISTENT_JIRITSU_WRITES
    allow_destructive_jiritsu_commands: bool = ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS
    live_usb_iokit_transmit_enabled: bool = LIVE_USB_IOKIT_TRANSMIT_ENABLED
    read_only_donor_access: bool = READ_ONLY_DONOR_ACCESS
    otp_fuse_touches: int = OTP_FUSE_TOUCHES
    otp_fuse_writes: int = OTP_FUSE_WRITES
    rpmb_counter_increments: int = RPMB_COUNTER_INCREMENTS
    passive_tx_bytes_emitted: int = PASSIVE_TX_BYTES_EMITTED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES
    raw_firmware_bytes_leaked: int = RAW_FIRMWARE_BYTES_LEAKED
    airgap_sockets_opened: int = AIRGAP_SOCKETS_OPENED
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# 1. Bounded `O_RDONLY` Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------


def inspect_phase184_donors_readonly(*, force_clean_room: Optional[bool] = None) -> Phase184DonorSnapshot:
    """Inspect FX3 `Ver. 7.02` & Stage-B shim donors via bounded `os.O_RDONLY` or clean-room fallback."""
    t0 = time.monotonic()
    forced = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if forced:
        artifacts = (
            Phase184DonorArtifactDigest(
                "libgrm_fbinit9_so",
                P184_DONOR_LIBGRM_FBINIT9_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P184_PINNED_LIBGRM_FBINIT9_BYTES,
                P184_PINNED_LIBGRM_FBINIT9_SHA256,
                P184_PINNED_LIBGRM_FBINIT9_SHA256,
                ("ELF64_LSB_ET_DYN", "EM_AARCH64_183", "SHIM_UNDER_64KIB"),
                True,
            ),
            Phase184DonorArtifactDigest(
                "libjit_test_so",
                P184_DONOR_LIBJIT_TEST_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P184_PINNED_LIBJIT_TEST_BYTES,
                P184_PINNED_LIBJIT_TEST_SHA256,
                P184_PINNED_LIBJIT_TEST_SHA256,
                ("ELF64_LSB_ET_DYN", "EM_AARCH64_183", "UNDER_64KIB_CEILING"),
                True,
            ),
            Phase184DonorArtifactDigest(
                "fx3_libjiritsu_so",
                P184_DONOR_LIBJIRITSU_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P184_PINNED_LIBJIRITSU_BYTES,
                P184_PINNED_LIBJIRITSU_SHA256,
                P184_PINNED_LIBJIRITSU_SHA256,
                ("ELF64_LSB_ET_DYN", "EM_AARCH64_183", "HOST_LIBJIRITSU"),
                True,
            ),
            Phase184DonorArtifactDigest(
                "fx3_partinf_conf",
                P184_DONOR_PARTINF_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P184_PINNED_PARTINF_BYTES,
                P184_PINNED_PARTINF_SHA256,
                P184_PINNED_PARTINF_SHA256,
                ("30_PARTITIONS", "P2_SETTING", "P12_CERT", "P15_USR", "P18_LENS"),
                True,
            ),
            Phase184DonorArtifactDigest(
                "fx3_nflasha5_wbi2",
                P184_DONOR_WBI2_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P184_PINNED_WBI2_BYTES,
                P184_PINNED_WBI2_HDR4K_SHA256,
                P184_PINNED_WBI2_HDR4K_SHA256,
                ("BOUNDED_4K_HEADER", "WBI2_1399_SECTIONS"),
                True,
            ),
            Phase184DonorArtifactDigest(
                "fx3_nflasha15_ext2",
                P184_DONOR_NFLASHA15_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P184_PINNED_NFLASHA15_BYTES,
                P184_PINNED_NFLASHA15_HDR4K_SHA256,
                P184_PINNED_NFLASHA15_HDR4K_SHA256,
                ("BOUNDED_4K_SUPERBLOCK", "EXT2_0xEF53"),
                True,
            ),
            Phase184DonorArtifactDigest(
                "fx3_702_bodydata_dat",
                P184_DONOR_BODYDATA_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P184_PINNED_BODYDATA_BYTES,
                P184_PINNED_BODYDATA_HDR4K_SHA256,
                P184_PINNED_BODYDATA_HDR4K_SHA256,
                ("BOUNDED_4K_HEADER", "UFU_MAGIC_89UFU"),
                True,
            ),
        )
        elapsed = round(time.monotonic() - t0, 6)
        snap_sha = _canonical_sha256({"mode": "CLEAN_ROOM_SYNTHETIC", "artifacts": [asdict(a) for a in artifacts]})
        return Phase184DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_METADATA_ONLY",
            donor_files_inspected=0,
            raw_firmware_bytes_leaked=0,
            libgrm_fbinit9_elf64_aarch64_ok=True,
            libjit_test_under_64k_ok=True,
            libjiritsu_elf64_aarch64_ok=True,
            partinf_30_partitions_ok=True,
            wbi2_header_ok=True,
            nflasha15_ext2_magic_ok=True,
            bodydata_ufu_magic_ok=True,
            elapsed_seconds=elapsed,
            artifacts=artifacts,
            snapshot_sha256=snap_sha,
            all_passed=True,
            errors=(),
        )

    specs = (
        ("libgrm_fbinit9_so", P184_DONOR_LIBGRM_FBINIT9_RELPATH, P184_PINNED_LIBGRM_FBINIT9_BYTES, P184_PINNED_LIBGRM_FBINIT9_SHA256, None),
        ("libjit_test_so", P184_DONOR_LIBJIT_TEST_RELPATH, P184_PINNED_LIBJIT_TEST_BYTES, P184_PINNED_LIBJIT_TEST_SHA256, None),
        ("fx3_libjiritsu_so", P184_DONOR_LIBJIRITSU_RELPATH, P184_PINNED_LIBJIRITSU_BYTES, P184_PINNED_LIBJIRITSU_SHA256, None),
        ("fx3_partinf_conf", P184_DONOR_PARTINF_RELPATH, P184_PINNED_PARTINF_BYTES, P184_PINNED_PARTINF_SHA256, None),
        ("fx3_nflasha5_wbi2", P184_DONOR_WBI2_RELPATH, P184_PINNED_WBI2_BYTES, P184_PINNED_WBI2_HDR4K_SHA256, P184_BOUNDED_HEADER_BYTES),
        ("fx3_nflasha15_ext2", P184_DONOR_NFLASHA15_RELPATH, P184_PINNED_NFLASHA15_BYTES, P184_PINNED_NFLASHA15_HDR4K_SHA256, P184_BOUNDED_HEADER_BYTES),
        ("fx3_702_bodydata_dat", P184_DONOR_BODYDATA_RELPATH, P184_PINNED_BODYDATA_BYTES, P184_PINNED_BODYDATA_HDR4K_SHA256, P184_BOUNDED_HEADER_BYTES),
    )

    for _, rel, _, _, _ in specs:
        p = resolve_donor_path(rel, require_file=True)
        if p is None or not p.is_file():
            return inspect_phase184_donors_readonly(force_clean_room=True)

    artifacts_out: List[Phase184DonorArtifactDigest] = []
    errors: List[str] = []
    fbinit9_ok = False
    libjit_ok = False
    libjiritsu_ok = False
    partinf_ok = False
    wbi2_ok = False
    ext2_ok = False
    ufu_ok = False

    for art_id, relpath, exp_bytes, exp_sha, bounded_lim in specs:
        buf, total_sz, full_sha, hdr_sha = _read_bounded_donor_rdonly(relpath, max_bytes=bounded_lim)
        item_ok = total_sz == exp_bytes
        if not item_ok:
            errors.append(f"{art_id}: size {total_sz} != {exp_bytes}")
        digest = hdr_sha if bounded_lim is not None else full_sha
        if digest != exp_sha:
            item_ok = False
            errors.append(f"{art_id}: sha256 mismatch")

        markers: List[str] = []
        if art_id == "libgrm_fbinit9_so":
            elf_info = parse_elf64_aarch64_shim_bytes(buf, expected_sha256=exp_sha, max_bytes=P184_LIBJIT_MAX_BYTES)
            fbinit9_ok = elf_info.valid and elf_info.is_aarch64 and elf_info.within_size_ceiling
            if fbinit9_ok:
                markers.extend(["ELF64_LSB_ET_DYN", "EM_AARCH64_183", "SHIM_UNDER_64KIB"])
            else:
                item_ok = False
                errors.extend(elf_info.errors)
        elif art_id == "libjit_test_so":
            elf_info = parse_elf64_aarch64_shim_bytes(buf, expected_sha256=exp_sha, max_bytes=P184_LIBJIT_MAX_BYTES)
            libjit_ok = elf_info.valid and elf_info.is_aarch64 and elf_info.within_size_ceiling
            if libjit_ok:
                markers.extend(["ELF64_LSB_ET_DYN", "EM_AARCH64_183", "UNDER_64KIB_CEILING"])
            else:
                item_ok = False
                errors.extend(elf_info.errors)
        elif art_id == "fx3_libjiritsu_so":
            elf_info = parse_elf64_aarch64_shim_bytes(buf, expected_sha256=exp_sha)
            libjiritsu_ok = elf_info.valid and elf_info.is_aarch64
            if libjiritsu_ok:
                markers.extend(["ELF64_LSB_ET_DYN", "EM_AARCH64_183", "HOST_LIBJIRITSU"])
            else:
                item_ok = False
                errors.extend(elf_info.errors)
        elif art_id == "fx3_partinf_conf":
            txt = buf.decode("utf-8", errors="replace")
            rows = re.findall(r"^0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+,0x[0-9A-Fa-f]+", txt, flags=re.M)
            partinf_ok = len(rows) == 30 and "0x0031c000" in txt.lower()
            if partinf_ok:
                markers.extend(["30_PARTITIONS", "P2_SETTING", "P12_CERT", "P15_USR", "P18_LENS"])
            else:
                item_ok = False
                errors.append(f"fx3_partinf_conf: unexpected rows={len(rows)}")
        elif art_id == "fx3_nflasha5_wbi2":
            wbi2_ok = len(buf) >= 16 and buf[:8] == b"WBI2\x00\x00\x00\x00"
            if wbi2_ok:
                markers.extend(["BOUNDED_4K_HEADER", "WBI2_1399_SECTIONS"])
            else:
                item_ok = False
                errors.append("fx3_nflasha5_wbi2: missing WBI2 header magic")
        elif art_id == "fx3_nflasha15_ext2":
            ext2_magic = struct.unpack_from("<H", buf, 1024 + 56)[0] if len(buf) >= 1082 else 0
            ext2_ok = ext2_magic == 0xEF53
            if ext2_ok:
                markers.extend(["BOUNDED_4K_SUPERBLOCK", "EXT2_0xEF53"])
            else:
                item_ok = False
                errors.append(f"fx3_nflasha15_ext2: bad ext2 magic {ext2_magic:#x}")
        elif art_id == "fx3_702_bodydata_dat":
            ufu_ok = len(buf) >= 8 and buf[:8] == P184_UFU_MAGIC
            if ufu_ok:
                markers.extend(["BOUNDED_4K_HEADER", "UFU_MAGIC_89UFU"])
            else:
                item_ok = False
                errors.append("fx3_702_bodydata_dat: missing \\x89UFU magic")

        artifacts_out.append(
            Phase184DonorArtifactDigest(
                artifact_id=art_id,
                relpath=relpath,
                source_mode="LOCAL_DONOR_O_RDONLY",
                access_mode="O_RDONLY|O_NOFOLLOW|O_NONBLOCK",
                byte_length=total_sz,
                sha256_digest=digest,
                header_sha256=hdr_sha,
                verified_markers=tuple(markers),
                passed=item_ok,
            )
        )

    elapsed = round(time.monotonic() - t0, 6)
    all_ok = (
        len(errors) == 0
        and fbinit9_ok
        and libjit_ok
        and libjiritsu_ok
        and partinf_ok
        and wbi2_ok
        and ext2_ok
        and ufu_ok
        and all(a.passed for a in artifacts_out)
    )
    snap_sha = _canonical_sha256({"mode": "LOCAL_DONOR_O_RDONLY", "artifacts": [asdict(a) for a in artifacts_out]})
    return Phase184DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY|O_NOFOLLOW|O_NONBLOCK",
        donor_files_inspected=len(artifacts_out),
        raw_firmware_bytes_leaked=0,
        libgrm_fbinit9_elf64_aarch64_ok=fbinit9_ok,
        libjit_test_under_64k_ok=libjit_ok,
        libjiritsu_elf64_aarch64_ok=libjiritsu_ok,
        partinf_30_partitions_ok=partinf_ok,
        wbi2_header_ok=wbi2_ok,
        nflasha15_ext2_magic_ok=ext2_ok,
        bodydata_ufu_magic_ok=ufu_ok,
        elapsed_seconds=elapsed,
        artifacts=tuple(artifacts_out),
        snapshot_sha256=snap_sha,
        all_passed=all_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 2. Pillar 25A — Per-Camera `FX3RCPT1` Hardware-Bound `FX3BNDL1` Manifest
# ---------------------------------------------------------------------------


def build_synthetic_camera_tier0_profile(
    *,
    camera_label: str = "fx3-bench-unit-a",
    model_id: int = P184_FX3_MODEL_ID,
    body_fw: str = P184_REQUIRED_BODY_FW,
    st_dev_primary: int = 16777220,
    st_dev_secondary: int = 16777231,
    single_copy_only: bool = False,
    corrupt_copy_b: bool = False,
) -> CameraTier0IdentityProfile:
    """Construct a deterministic per-camera Tier-0 `FX3RCPT1` dual-copy identity profile."""
    tag = camera_label.encode("utf-8")
    serial_hash = sha256(b"SERIAL|" + tag).hexdigest()
    emmc_cid_sha = sha256(b"CID|" + tag).hexdigest()
    p2_sha = sha256(b"P2_SETTING|" + tag).hexdigest()
    p5_sha = sha256(b"P5_WBI2|" + tag).hexdigest()
    p12_sha = sha256(b"P12_CERT|" + tag).hexdigest()
    p15_sha = sha256(b"P15_USR|" + tag).hexdigest()
    p18_sha = sha256(b"P18_LENS|" + tag).hexdigest()
    manifest_sha = sha256(
        b"|".join(
            [
                serial_hash.encode("ascii"),
                emmc_cid_sha.encode("ascii"),
                p2_sha.encode("ascii"),
                p5_sha.encode("ascii"),
                p12_sha.encode("ascii"),
                p15_sha.encode("ascii"),
                p18_sha.encode("ascii"),
            ]
        )
    ).hexdigest()

    rcpt_a = build_fx3rcpt1_receipt(
        body_serial_sha256=serial_hash,
        emmc_cid_sha256=emmc_cid_sha,
        manifest_sha256=manifest_sha,
        p2_cal_bundle_sha256=p2_sha,
        p18_lensfile_sha256=p18_sha,
        model_id=model_id,
    )
    if single_copy_only:
        rcpt_b = b""
    elif corrupt_copy_b:
        mut = bytearray(rcpt_a)
        mut[100] ^= 0x01
        rcpt_b = bytes(mut)
    else:
        rcpt_b = rcpt_a

    return CameraTier0IdentityProfile(
        serial_hash=serial_hash,
        model_id=model_id,
        body_fw=body_fw,
        p2_setting_h0_sha256=p2_sha,
        p5_wbi2_h0_sha256=p5_sha,
        p12_cert_h0_sha256=p12_sha,
        p15_usr_h0_sha256=p15_sha,
        p18_lens_h0_sha256=p18_sha,
        emmc_cid_sha256=emmc_cid_sha,
        manifest_sha256=manifest_sha,
        st_dev_primary=st_dev_primary,
        st_dev_secondary=st_dev_secondary,
        receipt_copy_a_hex=rcpt_a.hex(),
        receipt_copy_b_hex=rcpt_b.hex(),
    )


def build_fx3bndl1_manifest(
    profile: CameraTier0IdentityProfile,
    entries: Sequence[BundleFileEntry],
    *,
    bench_secret: bytes = P184_DEFAULT_AIRGAP_BENCH_SECRET,
) -> Fx3Bndl1Manifest:
    """Bind a staging bundle manifest (`FX3BNDL1`, CRC32 + HMAC-SHA256) to one physical camera's `FX3RCPT1`."""
    rcpt_a = bytes.fromhex(profile.receipt_copy_a_hex)
    receipt_sha = sha256(rcpt_a).hexdigest()
    sorted_entries = tuple(sorted(entries, key=lambda e: e.relpath))

    core_payload = {
        "magic": P184_MANIFEST_MAGIC,
        "version": P184_MANIFEST_VERSION,
        "target_model_id": profile.model_id,
        "target_body_fw": profile.body_fw,
        "target_serial_hash": profile.serial_hash,
        "receipt_sha256": receipt_sha,
        "st_dev_primary": profile.st_dev_primary,
        "st_dev_secondary": profile.st_dev_secondary,
        "p2_setting_h0_sha256": profile.p2_setting_h0_sha256,
        "p5_wbi2_h0_sha256": profile.p5_wbi2_h0_sha256,
        "p12_cert_h0_sha256": profile.p12_cert_h0_sha256,
        "p15_usr_h0_sha256": profile.p15_usr_h0_sha256,
        "p18_lens_h0_sha256": profile.p18_lens_h0_sha256,
        "bundle_entries": [asdict(e) for e in sorted_entries],
    }
    core_bytes = _canonical_json_bytes(core_payload)
    payload_crc32 = zlib.crc32(core_bytes) & 0xFFFFFFFF

    hmac_key = _derive_fx3bndl1_hmac_key(
        receipt_bytes=rcpt_a,
        serial_hash=profile.serial_hash,
        p2_setting_h0_sha256=profile.p2_setting_h0_sha256,
        p5_wbi2_h0_sha256=profile.p5_wbi2_h0_sha256,
        p12_cert_h0_sha256=profile.p12_cert_h0_sha256,
        p15_usr_h0_sha256=profile.p15_usr_h0_sha256,
        p18_lens_h0_sha256=profile.p18_lens_h0_sha256,
        bench_secret=bench_secret,
    )
    mac_hex = hmac.new(hmac_key, core_bytes + struct.pack("<I", payload_crc32), sha256).hexdigest()

    return Fx3Bndl1Manifest(
        magic=P184_MANIFEST_MAGIC,
        version=P184_MANIFEST_VERSION,
        target_model_id=profile.model_id,
        target_body_fw=profile.body_fw,
        target_serial_hash=profile.serial_hash,
        receipt_sha256=receipt_sha,
        st_dev_primary=profile.st_dev_primary,
        st_dev_secondary=profile.st_dev_secondary,
        p2_setting_h0_sha256=profile.p2_setting_h0_sha256,
        p5_wbi2_h0_sha256=profile.p5_wbi2_h0_sha256,
        p12_cert_h0_sha256=profile.p12_cert_h0_sha256,
        p15_usr_h0_sha256=profile.p15_usr_h0_sha256,
        p18_lens_h0_sha256=profile.p18_lens_h0_sha256,
        bundle_entries=sorted_entries,
        payload_crc32=payload_crc32,
        hmac_sha256=mac_hex,
    )


def verify_fx3bndl1_manifest(
    manifest: Fx3Bndl1Manifest,
    camera_profile: CameraTier0IdentityProfile,
    *,
    bench_secret: bytes = P184_DEFAULT_AIRGAP_BENCH_SECRET,
    request_persistent_write_unlock: bool = False,
) -> Fx3Bndl1VerificationReport:
    """Verify `FX3BNDL1` cryptographic cross-binding against a camera's dual-copy `FX3RCPT1` receipt."""
    blocked: List[str] = []
    errors: List[str] = []

    if request_persistent_write_unlock:
        blocked.append(P184_BLOCKED_SAFETY_POLICY_VIOLATION)
        errors.append("persistent write unlock is permanently locked False")

    magic_ok = manifest.magic == P184_MANIFEST_MAGIC and manifest.version == P184_MANIFEST_VERSION
    if not magic_ok:
        blocked.append(FX3BNDL1_CRC32_OR_HMAC_INVALID)
        errors.append(f"invalid FX3BNDL1 header magic={manifest.magic!r} version={manifest.version}")

    # 1. Model ID gate (strictly ILME-FX3 0x91030080)
    model_ok = (
        manifest.target_model_id == P184_FX3_MODEL_ID
        and camera_profile.model_id == P184_FX3_MODEL_ID
    )
    if not model_ok:
        blocked.append(NON_FX3_MODEL_ID_FORBIDDEN)
        errors.append(
            f"non-FX3 model id forbidden: manifest={manifest.target_model_id:#x}, "
            f"camera={camera_profile.model_id:#x}"
        )

    # 2. Body firmware version gate (must be Ver. 7.02)
    fw_ok = (
        manifest.target_body_fw.strip() == P184_REQUIRED_BODY_FW
        and camera_profile.body_fw.strip() == P184_REQUIRED_BODY_FW
    )
    if not fw_ok:
        blocked.append(BODY_FIRMWARE_VERSION_NOT_702)
        errors.append(
            f"body_fw must be {P184_REQUIRED_BODY_FW!r}: manifest={manifest.target_body_fw!r}, "
            f"camera={camera_profile.body_fw!r}"
        )

    # 3. Dual-copy FX3RCPT1 & distinct physical media (st_dev_primary != st_dev_secondary)
    try:
        rcpt_a = bytes.fromhex(camera_profile.receipt_copy_a_hex)
        rcpt_b = bytes.fromhex(camera_profile.receipt_copy_b_hex) if camera_profile.receipt_copy_b_hex else b""
    except ValueError:
        rcpt_a = b""
        rcpt_b = b""

    rcpt_info_a = parse_fx3rcpt1_receipt(rcpt_a)
    distinct_st_dev_ok = (
        camera_profile.st_dev_primary != camera_profile.st_dev_secondary
        and manifest.st_dev_primary != manifest.st_dev_secondary
        and camera_profile.st_dev_primary > 0
        and camera_profile.st_dev_secondary > 0
    )
    dual_copy_ok = (
        len(rcpt_a) == P184_FX3RCPT1_BYTES
        and len(rcpt_b) == P184_FX3RCPT1_BYTES
        and rcpt_a == rcpt_b
        and rcpt_info_a.crc32_valid
        and rcpt_info_a.magic_hex == P184_FX3RCPT1_MAGIC.hex()
        and rcpt_info_a.surface_count == 16
    )
    if not distinct_st_dev_ok or not dual_copy_ok:
        blocked.append(SINGLE_MEDIA_COLD_BACKUP_UNVERIFIED)
        if not distinct_st_dev_ok:
            errors.append(
                f"st_dev_primary ({camera_profile.st_dev_primary}) must differ from "
                f"st_dev_secondary ({camera_profile.st_dev_secondary})"
            )
        if not dual_copy_ok:
            errors.append("dual-copy 528B FX3RCPT1 receipt missing, mismatched, or CRC32 invalid")

    # 4. Per-camera serial & receipt fingerprint binding
    rcpt_a_sha = sha256(rcpt_a).hexdigest() if rcpt_a else ""
    serial_ok = (
        bool(_SHA256_RE.match(manifest.target_serial_hash))
        and manifest.target_serial_hash == camera_profile.serial_hash
        and rcpt_info_a.body_serial_sha256 == camera_profile.serial_hash
        and manifest.receipt_sha256 == rcpt_a_sha
        and manifest.st_dev_primary == camera_profile.st_dev_primary
        and manifest.st_dev_secondary == camera_profile.st_dev_secondary
    )
    if not serial_ok:
        blocked.append(CAMERA_SERIAL_RECEIPT_MISMATCH)
        errors.append("camera serial_hash or FX3RCPT1 receipt fingerprint mismatch")

    # 5. 5 mandatory Tier-0 partition H0 digests
    tier0_5_ok = (
        manifest.p2_setting_h0_sha256 == camera_profile.p2_setting_h0_sha256
        and manifest.p5_wbi2_h0_sha256 == camera_profile.p5_wbi2_h0_sha256
        and manifest.p12_cert_h0_sha256 == camera_profile.p12_cert_h0_sha256
        and manifest.p15_usr_h0_sha256 == camera_profile.p15_usr_h0_sha256
        and manifest.p18_lens_h0_sha256 == camera_profile.p18_lens_h0_sha256
        and rcpt_info_a.p2_cal_bundle_sha256 == camera_profile.p2_setting_h0_sha256
        and rcpt_info_a.p18_lensfile_sha256 == camera_profile.p18_lens_h0_sha256
        and all(
            bool(_SHA256_RE.match(d))
            for d in (
                manifest.p2_setting_h0_sha256,
                manifest.p5_wbi2_h0_sha256,
                manifest.p12_cert_h0_sha256,
                manifest.p15_usr_h0_sha256,
                manifest.p18_lens_h0_sha256,
            )
        )
    )
    if not tier0_5_ok:
        blocked.append(TIER0_PARTITION_H0_MISMATCH)
        errors.append("one or more Tier-0 baseline digests (p2/p5/p12/p15/p18) mismatched")

    # 6. FX3BNDL1 IEEE CRC32 + HMAC-SHA256 verification
    core_payload = {
        "magic": manifest.magic,
        "version": manifest.version,
        "target_model_id": manifest.target_model_id,
        "target_body_fw": manifest.target_body_fw,
        "target_serial_hash": manifest.target_serial_hash,
        "receipt_sha256": manifest.receipt_sha256,
        "st_dev_primary": manifest.st_dev_primary,
        "st_dev_secondary": manifest.st_dev_secondary,
        "p2_setting_h0_sha256": manifest.p2_setting_h0_sha256,
        "p5_wbi2_h0_sha256": manifest.p5_wbi2_h0_sha256,
        "p12_cert_h0_sha256": manifest.p12_cert_h0_sha256,
        "p15_usr_h0_sha256": manifest.p15_usr_h0_sha256,
        "p18_lens_h0_sha256": manifest.p18_lens_h0_sha256,
        "bundle_entries": [asdict(e) for e in manifest.bundle_entries],
    }
    core_bytes = _canonical_json_bytes(core_payload)
    calc_crc32 = zlib.crc32(core_bytes) & 0xFFFFFFFF
    crc32_ok = calc_crc32 == manifest.payload_crc32

    hmac_key = _derive_fx3bndl1_hmac_key(
        receipt_bytes=rcpt_a,
        serial_hash=camera_profile.serial_hash,
        p2_setting_h0_sha256=camera_profile.p2_setting_h0_sha256,
        p5_wbi2_h0_sha256=camera_profile.p5_wbi2_h0_sha256,
        p12_cert_h0_sha256=camera_profile.p12_cert_h0_sha256,
        p15_usr_h0_sha256=camera_profile.p15_usr_h0_sha256,
        p18_lens_h0_sha256=camera_profile.p18_lens_h0_sha256,
        bench_secret=bench_secret,
    )
    expected_mac = hmac.new(hmac_key, core_bytes + struct.pack("<I", manifest.payload_crc32), sha256).hexdigest()
    hmac_ok = hmac.compare_digest(expected_mac, manifest.hmac_sha256)
    if not crc32_ok or not hmac_ok:
        blocked.append(FX3BNDL1_CRC32_OR_HMAC_INVALID)
        if not crc32_ok:
            errors.append(f"FX3BNDL1 payload CRC32 mismatch: got={manifest.payload_crc32:#x} expected={calc_crc32:#x}")
        if not hmac_ok:
            errors.append("FX3BNDL1 HMAC-SHA256 verification failed")

    dedup_blocked = tuple(dict.fromkeys(blocked))
    passed = (
        len(dedup_blocked) == 0
        and magic_ok
        and model_ok
        and fw_ok
        and dual_copy_ok
        and distinct_st_dev_ok
        and serial_ok
        and tier0_5_ok
        and crc32_ok
        and hmac_ok
    )
    return Fx3Bndl1VerificationReport(
        passed=passed,
        bundle_authorized=passed,
        manifest_magic_ok=magic_ok,
        model_id_fx3_ok=model_ok,
        body_fw_702_ok=fw_ok,
        dual_copy_receipt_ok=dual_copy_ok,
        distinct_st_dev_ok=distinct_st_dev_ok,
        serial_binding_ok=serial_ok,
        tier0_5surface_h0_ok=tier0_5_ok,
        crc32_ok=crc32_ok,
        hmac_sha256_ok=hmac_ok,
        blocked_codes=dedup_blocked,
        errors=tuple(errors),
    )


def _default_synthetic_bundle_entries() -> Tuple[BundleFileEntry, ...]:
    items = (
        ("FX6_STAGEB/fx6-stage-a-verify", build_synthetic_aarch64_elf64_shim(e_type=P184_ELF_TYPE_EXEC, marker=b"FX6_STAGE_A_VERIFY", target_size=8192)),
        ("FX6_STAGEB/libJit.so", build_synthetic_aarch64_elf64_shim(e_type=P184_ELF_TYPE_DYN, marker=b"LIBJIT_STAGEB_SHIM", target_size=12288)),
        ("FX6_STAGEB/libgrm-fbinit9.so", build_synthetic_aarch64_elf64_shim(e_type=P184_ELF_TYPE_DYN, marker=b"LIBGRM_FBINIT9", target_size=7664)),
    )
    return tuple(
        BundleFileEntry(
            relpath=rel,
            byte_size=len(blob),
            sha256_digest=sha256(blob).hexdigest(),
            crc32_u32=zlib.crc32(blob) & 0xFFFFFFFF,
        )
        for rel, blob in items
    )


def run_pillar25a_fx3bndl1_binding_8_scenario_suite() -> Pillar25ABindingSuiteResult:
    """Run all 8 deterministic scenarios for Pillar 25A (`FX3RCPT1` <-> `FX3BNDL1` binding)."""
    entries = _default_synthetic_bundle_entries()
    cam_a = build_synthetic_camera_tier0_profile(camera_label="fx3-unit-alpha")
    manifest_a = build_fx3bndl1_manifest(cam_a, entries)

    outcomes: List[Pillar25AScenarioOutcome] = []

    # 1. Happy path
    r1 = verify_fx3bndl1_manifest(manifest_a, cam_a)
    outcomes.append(
        Pillar25AScenarioOutcome(
            P184_PILLAR_25A_SCENARIO_IDS[0],
            r1.passed and r1.bundle_authorized,
            r1.bundle_authorized,
            r1.blocked_codes,
            "FX3 7.02 (0x91030080) dual-copy FX3RCPT1 + FX3BNDL1 HMAC/CRC32 verified",
        )
    )

    # 2. Cross-camera transplant (Camera A's card inserted into Camera B)
    cam_b = build_synthetic_camera_tier0_profile(camera_label="fx3-unit-beta")
    r2 = verify_fx3bndl1_manifest(manifest_a, cam_b)
    outcomes.append(
        Pillar25AScenarioOutcome(
            P184_PILLAR_25A_SCENARIO_IDS[1],
            (not r2.passed) and (not r2.bundle_authorized) and (CAMERA_SERIAL_RECEIPT_MISMATCH in r2.blocked_codes),
            r2.bundle_authorized,
            r2.blocked_codes,
            "Cross-camera SD transplant rejected (CAMERA_SERIAL_RECEIPT_MISMATCH)",
        )
    )

    # 3. Non-FX3 FX30 (0x91030084)
    cam_fx30 = build_synthetic_camera_tier0_profile(camera_label="fx30-unit", model_id=P184_FX30_MODEL_ID)
    man_fx30 = build_fx3bndl1_manifest(cam_fx30, entries)
    r3 = verify_fx3bndl1_manifest(man_fx30, cam_fx30)
    outcomes.append(
        Pillar25AScenarioOutcome(
            P184_PILLAR_25A_SCENARIO_IDS[2],
            (not r3.passed) and (not r3.bundle_authorized) and (NON_FX3_MODEL_ID_FORBIDDEN in r3.blocked_codes),
            r3.bundle_authorized,
            r3.blocked_codes,
            "Non-FX3 model 0x91030084 (FX30) rejected",
        )
    )

    # 4. Non-FX3 FX6 (0x91020080)
    cam_fx6 = build_synthetic_camera_tier0_profile(camera_label="fx6-unit", model_id=P184_FX6_MODEL_ID)
    man_fx6 = build_fx3bndl1_manifest(cam_fx6, entries)
    r4 = verify_fx3bndl1_manifest(man_fx6, cam_fx6)
    outcomes.append(
        Pillar25AScenarioOutcome(
            P184_PILLAR_25A_SCENARIO_IDS[3],
            (not r4.passed) and (not r4.bundle_authorized) and (NON_FX3_MODEL_ID_FORBIDDEN in r4.blocked_codes),
            r4.bundle_authorized,
            r4.blocked_codes,
            "Non-FX3 model 0x91020080 (FX6) rejected",
        )
    )

    # 5. Body firmware < 7.02 (e.g. 2.05)
    cam_old = build_synthetic_camera_tier0_profile(camera_label="fx3-unit-205", body_fw="2.05")
    man_old = build_fx3bndl1_manifest(cam_old, entries)
    r5 = verify_fx3bndl1_manifest(man_old, cam_old)
    outcomes.append(
        Pillar25AScenarioOutcome(
            P184_PILLAR_25A_SCENARIO_IDS[4],
            (not r5.passed) and (not r5.bundle_authorized) and (BODY_FIRMWARE_VERSION_NOT_702 in r5.blocked_codes),
            r5.bundle_authorized,
            r5.blocked_codes,
            "FX3 body firmware < 7.02 (2.05) rejected",
        )
    )

    # 6. Single-media unverified cold backup (st_dev_primary == st_dev_secondary)
    cam_single = build_synthetic_camera_tier0_profile(
        camera_label="fx3-single-media",
        st_dev_primary=16777220,
        st_dev_secondary=16777220,
        single_copy_only=True,
    )
    man_single = build_fx3bndl1_manifest(cam_single, entries)
    r6 = verify_fx3bndl1_manifest(man_single, cam_single)
    outcomes.append(
        Pillar25AScenarioOutcome(
            P184_PILLAR_25A_SCENARIO_IDS[5],
            (not r6.passed) and (not r6.bundle_authorized) and (SINGLE_MEDIA_COLD_BACKUP_UNVERIFIED in r6.blocked_codes),
            r6.bundle_authorized,
            r6.blocked_codes,
            "Single-media unverified Tier-0 backup (st_dev_a == st_dev_b) rejected",
        )
    )

    # 7. Tier-0 partition H0 hash mismatch (p5_wbi2_h0_sha256 drifted)
    man_h0_drift = Fx3Bndl1Manifest(**{**asdict(manifest_a), "p5_wbi2_h0_sha256": "f" * 64, "bundle_entries": manifest_a.bundle_entries})
    r7 = verify_fx3bndl1_manifest(man_h0_drift, cam_a)
    outcomes.append(
        Pillar25AScenarioOutcome(
            P184_PILLAR_25A_SCENARIO_IDS[6],
            (not r7.passed) and (not r7.bundle_authorized) and (TIER0_PARTITION_H0_MISMATCH in r7.blocked_codes),
            r7.bundle_authorized,
            r7.blocked_codes,
            "Tier-0 p5_wbi2_h0_sha256 mismatch rejected",
        )
    )

    # 8. FX3BNDL1 HMAC/CRC32 tamper
    tampered_mac = ("0" if manifest_a.hmac_sha256[0] != "0" else "1") + manifest_a.hmac_sha256[1:]
    man_tamper = Fx3Bndl1Manifest(**{**asdict(manifest_a), "hmac_sha256": tampered_mac, "payload_crc32": manifest_a.payload_crc32 ^ 0x1, "bundle_entries": manifest_a.bundle_entries})
    r8 = verify_fx3bndl1_manifest(man_tamper, cam_a)
    outcomes.append(
        Pillar25AScenarioOutcome(
            P184_PILLAR_25A_SCENARIO_IDS[7],
            (not r8.passed) and (not r8.bundle_authorized) and (FX3BNDL1_CRC32_OR_HMAC_INVALID in r8.blocked_codes),
            r8.bundle_authorized,
            r8.blocked_codes,
            "FX3BNDL1 CRC32 / HMAC-SHA256 1-bit tamper rejected",
        )
    )

    passed_count = sum(1 for o in outcomes if o.passed)
    all_ok = passed_count == len(P184_PILLAR_25A_SCENARIO_IDS)
    return Pillar25ABindingSuiteResult(
        passed=all_ok,
        status=P184_STATUS_VERIFIED_25A if all_ok else P184_STATUS_REJECTED_25A,
        scenarios_passed=passed_count,
        scenarios_total=len(P184_PILLAR_25A_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# 3. Pillar 25B — ExFAT Hygiene, AppleDouble Scrubber, ELF64 & BODYDATA Guard
# ---------------------------------------------------------------------------


def build_synthetic_aarch64_elf64_shim(
    *,
    e_type: int = P184_ELF_TYPE_DYN,
    e_machine: int = P184_ELF_MACHINE_AARCH64,
    ei_class: int = P184_ELF_CLASS_64,
    ei_data: int = P184_ELF_DATA_LSB,
    marker: bytes = b"FX3_STAGEB_SHIM",
    target_size: int = 4096,
) -> bytes:
    """Build a minimal deterministic ELF64 AArch64 header + marker blob for clean-room staging tests."""
    _need(target_size >= 64, "ELF64 header requires >= 64 bytes")
    ehdr = bytearray(64)
    ehdr[0:4] = P184_ELF_MAGIC
    ehdr[4] = ei_class
    ehdr[5] = ei_data
    ehdr[6] = 1  # EV_CURRENT
    struct.pack_into("<HHIQQQIHHHHHH", ehdr, 16, e_type, e_machine, 1, 0x1000, 64, 0, 0, 64, 56, 1, 64, 0, 0)
    body = bytes(ehdr) + marker
    if len(body) < target_size:
        body += b"\x00" * (target_size - len(body))
    else:
        body = body[:target_size]
    return body


def parse_elf64_aarch64_shim_bytes(
    data: bytes,
    *,
    expected_sha256: Optional[str] = None,
    max_bytes: Optional[int] = None,
) -> Elf64ShimHeaderInfo:
    """Validate ELF64 little-endian `EM_AARCH64` (`e_machine == 183`) userland shim header & SHA-256."""
    errs: List[str] = []
    sz = len(data)
    digest = sha256(data).hexdigest() if sz > 0 else sha256(b"").hexdigest()
    sha_ok = True if expected_sha256 is None else (digest == expected_sha256)
    if not sha_ok:
        errs.append(f"sha256 mismatch: got={digest} expected={expected_sha256}")

    within_limit = True if max_bytes is None else (0 < sz <= max_bytes)
    if sz == 0:
        errs.append("zero-byte shim file")
    elif max_bytes is not None and sz > max_bytes:
        errs.append(f"shim size {sz} exceeds max_bytes={max_bytes}")

    if sz < 64:
        errs.append(f"truncated ELF64 header ({sz} < 64 bytes)")
        return Elf64ShimHeaderInfo(
            valid=False,
            byte_size=sz,
            ei_class=0,
            ei_data=0,
            e_type=0,
            e_machine=0,
            is_aarch64=False,
            within_size_ceiling=within_limit,
            sha256_digest=digest,
            sha256_matched=sha_ok,
            errors=tuple(errs),
        )

    magic = data[0:4]
    ei_class = data[4]
    ei_data = data[5]
    e_type, e_machine = struct.unpack_from("<HH", data, 16)

    if magic != P184_ELF_MAGIC:
        errs.append(f"bad ELF magic: {magic!r}")
    if ei_class != P184_ELF_CLASS_64:
        errs.append(f"not ELF64 (ei_class={ei_class})")
    if ei_data != P184_ELF_DATA_LSB:
        errs.append(f"not little-endian ELF (ei_data={ei_data})")
    if e_type not in (P184_ELF_TYPE_EXEC, P184_ELF_TYPE_DYN):
        errs.append(f"unexpected ELF e_type={e_type}")
    is_aarch64 = e_machine == P184_ELF_MACHINE_AARCH64
    if not is_aarch64:
        errs.append(f"wrong ELF e_machine={e_machine} (expected EM_AARCH64=183)")

    valid = len(errs) == 0 and magic == P184_ELF_MAGIC and ei_class == P184_ELF_CLASS_64 and ei_data == P184_ELF_DATA_LSB and is_aarch64 and within_limit and sha_ok
    return Elf64ShimHeaderInfo(
        valid=valid,
        byte_size=sz,
        ei_class=ei_class,
        ei_data=ei_data,
        e_type=e_type,
        e_machine=e_machine,
        is_aarch64=is_aarch64,
        within_size_ceiling=within_limit,
        sha256_digest=digest,
        sha256_matched=sha_ok,
        errors=tuple(errs),
    )


def _is_macos_exfat_junk_name(name: str) -> bool:
    return name.startswith(P184_APPLEDOUBLE_PREFIX) or (name in P184_FORBIDDEN_MACOS_NAMES)


def _is_bodydata_conflict_name(name: str) -> bool:
    upper = name.upper()
    return upper == "BODYDATA.DAT" or upper.startswith("BODYDATA") and upper.endswith(".DAT")


def scrub_exfat_staging_tree_tempdir_dry_run(staging_root: Path) -> ExfatScrubDryRunReport:
    """Safely scrub macOS `.DS_Store`/`.Spotlight-V100`/`.fseventsd`/`._*` inside an isolated temp directory."""
    resolved = Path(os.path.abspath(staging_root))
    temp_base = Path(os.path.abspath(tempfile.gettempdir()))
    if not resolved.is_relative_to(temp_base):
        return ExfatScrubDryRunReport(
            performed_in_tempdir=False,
            removed_count=0,
            removed_relpaths=(),
            preserved_files_count=0,
            errors=(f"refusing to scrub outside system tempdir: {resolved}",),
        )
    if not resolved.is_dir() or resolved.is_symlink():
        return ExfatScrubDryRunReport(
            performed_in_tempdir=True,
            removed_count=0,
            removed_relpaths=(),
            preserved_files_count=0,
            errors=("staging_root must be a real non-symlink directory",),
        )

    removed: List[str] = []
    preserved = 0
    for root, dirs, files in os.walk(resolved, topdown=True, followlinks=False):
        root_p = Path(root)
        for dn in list(dirs):
            dp = root_p / dn
            rel = str(dp.relative_to(resolved))
            if _is_macos_exfat_junk_name(dn):
                shutil.rmtree(dp)
                removed.append(rel + "/")
                dirs.remove(dn)
        for fn in files:
            fp = root_p / fn
            rel = str(fp.relative_to(resolved))
            if _is_macos_exfat_junk_name(fn):
                os.unlink(fp)
                removed.append(rel)
            else:
                preserved += 1

    return ExfatScrubDryRunReport(
        performed_in_tempdir=True,
        removed_count=len(removed),
        removed_relpaths=tuple(sorted(removed)),
        preserved_files_count=preserved,
        errors=(),
    )


def audit_exfat_staging_directory(
    staging_root: Path,
    *,
    expected_shim_sha256s: Mapping[str, str],
    p1_service_trigger_active: bool = True,
    airgap_sockets_opened: int = AIRGAP_SOCKETS_OPENED,
    request_persistent_write_unlock: bool = False,
) -> ExfatStagingHygieneReport:
    """Audit an offline SD/CFexpress staging tree for ExFAT/macOS hygiene, ELF64 shims, BODYDATA.DAT & airgap."""
    blocked: List[str] = []
    errors: List[str] = []

    if request_persistent_write_unlock:
        blocked.append(P184_BLOCKED_SAFETY_POLICY_VIOLATION)
        errors.append("persistent write unlock is permanently locked False")

    zero_sockets_ok = airgap_sockets_opened == 0
    if not zero_sockets_ok:
        blocked.append(AIRGAP_NETWORK_VIOLATION)
        errors.append(f"airgap network socket violation: airgap_sockets_opened={airgap_sockets_opened}")

    root_p = Path(os.path.abspath(staging_root))
    _need(root_p.is_dir() and not root_p.is_symlink(), "staging_root must be a real directory")

    macos_hits: List[str] = []
    appledouble_count = 0
    bodydata_conflicts: List[str] = []

    for cur_root, dirs, files in os.walk(root_p, followlinks=False):
        cur_p = Path(cur_root)
        for dn in list(dirs):
            dp = cur_p / dn
            rel = str(dp.relative_to(root_p))
            if dp.is_symlink():
                macos_hits.append(rel + " (symlink)")
                dirs.remove(dn)
                continue
            if _is_macos_exfat_junk_name(dn):
                macos_hits.append(rel + "/")
                if dn.startswith(P184_APPLEDOUBLE_PREFIX):
                    appledouble_count += 1
        for fn in files:
            fp = cur_p / fn
            rel = str(fp.relative_to(root_p))
            if fp.is_symlink():
                macos_hits.append(rel + " (symlink)")
                continue
            if _is_macos_exfat_junk_name(fn):
                macos_hits.append(rel)
                if fn.startswith(P184_APPLEDOUBLE_PREFIX):
                    appledouble_count += 1
            if _is_bodydata_conflict_name(fn):
                bodydata_conflicts.append(rel)

    exfat_junk_free = len(macos_hits) == 0
    if not exfat_junk_free:
        blocked.append(MACOS_EXFAT_JUNK_DETECTED)
        errors.append(f"macOS/ExFAT junk detected in staging tree: {', '.join(sorted(macos_hits))}")

    bodydata_ok = len(bodydata_conflicts) == 0
    if not bodydata_ok and p1_service_trigger_active:
        blocked.append(BODYDATA_DAT_MUTUAL_EXCLUSION_VIOLATION)
        errors.append(
            f"BODYDATA.DAT mutual-exclusion violation while p1 trigger active: {', '.join(sorted(bodydata_conflicts))}"
        )
    elif not bodydata_ok:
        blocked.append(BODYDATA_DAT_MUTUAL_EXCLUSION_VIOLATION)
        errors.append(f"BODYDATA.DAT co-located on staging card root: {', '.join(sorted(bodydata_conflicts))}")

    # Verify required shims inside FX6_STAGEB/
    stageb_dir = root_p / P184_STAGEB_DIR_NAME
    shims_all_ok = True
    libjit_under_64k_ok = True
    shim_digests: Dict[str, str] = {}

    for shim_name in P184_REQUIRED_SHIMS:
        shim_path = stageb_dir / shim_name
        if not shim_path.is_file() or shim_path.is_symlink():
            shims_all_ok = False
            blocked.append(SHIM_ELF_TRUNCATED_OR_SHA256_MISMATCH)
            errors.append(f"missing staged shim: {P184_STAGEB_DIR_NAME}/{shim_name}")
            continue

        fd, st_before = _open_rdonly_regular(shim_path, allow_donor_roots=False)
        try:
            max_read = 256 * 1024
            _need(st_before.st_size <= max_read, f"shim exceeds read ceiling: {shim_name}")
            with os.fdopen(os.dup(fd), "rb") as f:
                blob = f.read(st_before.st_size + 1)
            _verify_fstat_unchanged(fd, st_before)
        finally:
            os.close(fd)

        exp_sha = expected_shim_sha256s.get(shim_name)
        max_b = P184_LIBJIT_MAX_BYTES if shim_name == "libJit.so" else None
        elf_info = parse_elf64_aarch64_shim_bytes(blob, expected_sha256=exp_sha, max_bytes=max_b)
        shim_digests[shim_name] = elf_info.sha256_digest

        if shim_name == "libJit.so" and not elf_info.within_size_ceiling:
            libjit_under_64k_ok = False
            shims_all_ok = False
            blocked.append(LIBJIT_EXCEEDS_64KIB_LIMIT)
            errors.append(f"libJit.so exceeds 64 KiB ceiling ({elf_info.byte_size} > {P184_LIBJIT_MAX_BYTES})")
        if not elf_info.is_aarch64 or elf_info.ei_class != P184_ELF_CLASS_64 or elf_info.ei_data != P184_ELF_DATA_LSB:
            shims_all_ok = False
            blocked.append(SHIM_NOT_ELF64_AARCH64)
            errors.append(f"{shim_name}: not ELF64 AArch64 ({', '.join(elf_info.errors)})")
        if not elf_info.sha256_matched or elf_info.byte_size < 64:
            shims_all_ok = False
            blocked.append(SHIM_ELF_TRUNCATED_OR_SHA256_MISMATCH)
            errors.append(f"{shim_name}: truncated or SHA-256 mismatch")

    dedup_blocked = tuple(dict.fromkeys(blocked))
    passed = (
        len(dedup_blocked) == 0
        and exfat_junk_free
        and shims_all_ok
        and libjit_under_64k_ok
        and bodydata_ok
        and zero_sockets_ok
    )
    return ExfatStagingHygieneReport(
        passed=passed,
        staging_ready=passed,
        exfat_junk_free=exfat_junk_free,
        appledouble_count=appledouble_count,
        macos_metadata_hits=tuple(sorted(macos_hits)),
        shims_all_elf64_aarch64_ok=shims_all_ok,
        libjit_under_64kib_ok=libjit_under_64k_ok,
        shim_digests=shim_digests,
        bodydata_mutual_exclusion_ok=bodydata_ok,
        bodydata_conflicts=tuple(sorted(bodydata_conflicts)),
        airgap_zero_sockets_ok=zero_sockets_ok,
        airgap_sockets_opened=airgap_sockets_opened,
        blocked_codes=dedup_blocked,
        errors=tuple(errors),
    )


def _populate_temp_stageb_tree(root: Path) -> Dict[str, str]:
    stageb = root / P184_STAGEB_DIR_NAME
    stageb.mkdir(parents=True, exist_ok=True)
    blobs = {
        "fx6-stage-a-verify": build_synthetic_aarch64_elf64_shim(
            e_type=P184_ELF_TYPE_EXEC,
            marker=b"FX6_STAGE_A_VERIFY",
            target_size=8192,
        ),
        "libJit.so": build_synthetic_aarch64_elf64_shim(
            e_type=P184_ELF_TYPE_DYN,
            marker=b"LIBJIT_STAGEB_SHIM",
            target_size=12288,
        ),
        "libgrm-fbinit9.so": build_synthetic_aarch64_elf64_shim(
            e_type=P184_ELF_TYPE_DYN,
            marker=b"LIBGRM_FBINIT9",
            target_size=7664,
        ),
    }
    digests: Dict[str, str] = {}
    for name, data in blobs.items():
        (stageb / name).write_bytes(data)
        digests[name] = sha256(data).hexdigest()
    return digests


def run_pillar25b_exfat_hygiene_8_scenario_suite() -> Pillar25BHygieneSuiteResult:
    """Run all 8 deterministic scenarios for Pillar 25B (ExFAT hygiene, AppleDouble scrubber, ELF64 & BODYDATA)."""
    outcomes: List[Pillar25BScenarioOutcome] = []

    with tempfile.TemporaryDirectory(prefix="fx3_p25b_") as td:
        base = Path(td)

        # 1. Clean ExFAT FX6_STAGEB/ tree + zero network sockets
        s1_dir = base / "s1_clean"
        exp1 = _populate_temp_stageb_tree(s1_dir)
        r1 = audit_exfat_staging_directory(s1_dir, expected_shim_sha256s=exp1, p1_service_trigger_active=True)
        outcomes.append(
            Pillar25BScenarioOutcome(
                P184_PILLAR_25B_SCENARIO_IDS[0],
                r1.passed and r1.staging_ready and r1.airgap_zero_sockets_ok,
                r1.staging_ready,
                r1.blocked_codes,
                "Clean ExFAT FX6_STAGEB/ shims (ELF64 AArch64, libJit<=64KiB) + zero sockets verified",
            )
        )

        # 2. macOS .DS_Store + ._libJit.so AppleDouble pollution rejected
        s2_dir = base / "s2_junk"
        exp2 = _populate_temp_stageb_tree(s2_dir)
        (s2_dir / P184_STAGEB_DIR_NAME / ".DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1")
        (s2_dir / P184_STAGEB_DIR_NAME / "._libJit.so").write_bytes(b"\x00\x05\x16\x07AppleDouble")
        r2 = audit_exfat_staging_directory(s2_dir, expected_shim_sha256s=exp2)
        outcomes.append(
            Pillar25BScenarioOutcome(
                P184_PILLAR_25B_SCENARIO_IDS[1],
                (not r2.passed) and (not r2.staging_ready) and (MACOS_EXFAT_JUNK_DETECTED in r2.blocked_codes) and r2.appledouble_count == 1,
                r2.staging_ready,
                r2.blocked_codes,
                "macOS .DS_Store and ._libJit.so AppleDouble files rejected",
            )
        )

        # 3. Temp-dir dry-run AppleDouble/.Spotlight-V100/.fseventsd scrubber -> clean re-audit
        s3_dir = base / "s3_scrub"
        exp3 = _populate_temp_stageb_tree(s3_dir)
        (s3_dir / ".DS_Store").write_bytes(b"DS")
        (s3_dir / ".Spotlight-V100").mkdir()
        (s3_dir / ".Spotlight-V100" / "VolumeConfiguration.plist").write_bytes(b"plist")
        (s3_dir / ".fseventsd").mkdir()
        (s3_dir / ".fseventsd" / "fseventsd-uuid").write_bytes(b"uuid")
        (s3_dir / P184_STAGEB_DIR_NAME / "._fx6-stage-a-verify").write_bytes(b"AD")
        (s3_dir / P184_STAGEB_DIR_NAME / "._libgrm-fbinit9.so").write_bytes(b"AD")
        pre3 = audit_exfat_staging_directory(s3_dir, expected_shim_sha256s=exp3)
        scrub3 = scrub_exfat_staging_tree_tempdir_dry_run(s3_dir)
        post3 = audit_exfat_staging_directory(s3_dir, expected_shim_sha256s=exp3)
        outcomes.append(
            Pillar25BScenarioOutcome(
                P184_PILLAR_25B_SCENARIO_IDS[2],
                (not pre3.passed) and scrub3.performed_in_tempdir and scrub3.removed_count >= 5 and post3.passed and post3.staging_ready,
                post3.staging_ready,
                post3.blocked_codes,
                "Temp-dir scrubber removed .DS_Store/.Spotlight-V100/.fseventsd/._* and verified SHA-256 intact",
            )
        )

        # 4. Truncated shim / 1-byte bit-rot SHA-256 mismatch
        s4_dir = base / "s4_bitrot"
        exp4 = _populate_temp_stageb_tree(s4_dir)
        jit_p = s4_dir / P184_STAGEB_DIR_NAME / "libJit.so"
        mut = bytearray(jit_p.read_bytes())
        mut[-1] ^= 0xFF
        jit_p.write_bytes(bytes(mut))
        r4 = audit_exfat_staging_directory(s4_dir, expected_shim_sha256s=exp4)
        outcomes.append(
            Pillar25BScenarioOutcome(
                P184_PILLAR_25B_SCENARIO_IDS[3],
                (not r4.passed) and (SHIM_ELF_TRUNCATED_OR_SHA256_MISMATCH in r4.blocked_codes),
                r4.staging_ready,
                r4.blocked_codes,
                "1-byte ExFAT bit-rot in libJit.so caught via SHA-256 verification",
            )
        )

        # 5. Wrong ELF architecture (x86_64 e_machine=62 instead of EM_AARCH64=183)
        s5_dir = base / "s5_wrong_arch"
        exp5 = _populate_temp_stageb_tree(s5_dir)
        bad_elf = build_synthetic_aarch64_elf64_shim(e_type=P184_ELF_TYPE_DYN, e_machine=62, target_size=7664)
        (s5_dir / P184_STAGEB_DIR_NAME / "libgrm-fbinit9.so").write_bytes(bad_elf)
        exp5["libgrm-fbinit9.so"] = sha256(bad_elf).hexdigest()
        r5 = audit_exfat_staging_directory(s5_dir, expected_shim_sha256s=exp5)
        outcomes.append(
            Pillar25BScenarioOutcome(
                P184_PILLAR_25B_SCENARIO_IDS[4],
                (not r5.passed) and (SHIM_NOT_ELF64_AARCH64 in r5.blocked_codes),
                r5.staging_ready,
                r5.blocked_codes,
                "Non-AArch64 ELF64 shim (e_machine=62) rejected",
            )
        )

        # 6. libJit.so exceeds 64 KiB ceiling (65,537 B > 65,536 B)
        s6_dir = base / "s6_oversize_jit"
        exp6 = _populate_temp_stageb_tree(s6_dir)
        big_jit = build_synthetic_aarch64_elf64_shim(e_type=P184_ELF_TYPE_DYN, target_size=P184_LIBJIT_MAX_BYTES + 1)
        (s6_dir / P184_STAGEB_DIR_NAME / "libJit.so").write_bytes(big_jit)
        exp6["libJit.so"] = sha256(big_jit).hexdigest()
        r6 = audit_exfat_staging_directory(s6_dir, expected_shim_sha256s=exp6)
        outcomes.append(
            Pillar25BScenarioOutcome(
                P184_PILLAR_25B_SCENARIO_IDS[5],
                (not r6.passed) and (not r6.libjit_under_64kib_ok) and (LIBJIT_EXCEEDS_64KIB_LIMIT in r6.blocked_codes),
                r6.staging_ready,
                r6.blocked_codes,
                "Oversized libJit.so (> 64 KiB) rejected",
            )
        )

        # 7. BODYDATA.DAT co-located on card root with active p1 service trigger
        s7_dir = base / "s7_bodydata"
        exp7 = _populate_temp_stageb_tree(s7_dir)
        (s7_dir / "BODYDATA.DAT").write_bytes(P184_UFU_MAGIC + b"\x00" * 64)
        r7 = audit_exfat_staging_directory(s7_dir, expected_shim_sha256s=exp7, p1_service_trigger_active=True)
        outcomes.append(
            Pillar25BScenarioOutcome(
                P184_PILLAR_25B_SCENARIO_IDS[6],
                (not r7.passed) and (not r7.bodydata_mutual_exclusion_ok) and (BODYDATA_DAT_MUTUAL_EXCLUSION_VIOLATION in r7.blocked_codes),
                r7.staging_ready,
                r7.blocked_codes,
                "Slot-1 BODYDATA.DAT co-staging with active p1 trigger rejected",
            )
        )

        # 8. Air-gap network socket attempt or persistent write unlock attempt
        s8_dir = base / "s8_airgap"
        exp8 = _populate_temp_stageb_tree(s8_dir)
        r8 = audit_exfat_staging_directory(
            s8_dir,
            expected_shim_sha256s=exp8,
            airgap_sockets_opened=1,
            request_persistent_write_unlock=True,
        )
        outcomes.append(
            Pillar25BScenarioOutcome(
                P184_PILLAR_25B_SCENARIO_IDS[7],
                (not r8.passed)
                and (AIRGAP_NETWORK_VIOLATION in r8.blocked_codes)
                and (P184_BLOCKED_SAFETY_POLICY_VIOLATION in r8.blocked_codes),
                r8.staging_ready,
                r8.blocked_codes,
                "Air-gap network socket attempt & persistent write unlock rejected fail-closed",
            )
        )

    passed_count = sum(1 for o in outcomes if o.passed)
    all_ok = passed_count == len(P184_PILLAR_25B_SCENARIO_IDS)
    return Pillar25BHygieneSuiteResult(
        passed=all_ok,
        status=P184_STATUS_VERIFIED_25B if all_ok else P184_STATUS_REJECTED_25B,
        scenarios_passed=passed_count,
        scenarios_total=len(P184_PILLAR_25B_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# 4. Unified Pillar 25 Suite Runner
# ---------------------------------------------------------------------------


def run_airgap_sd_bundle_manifest_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> Pillar25AirgapSdBundleReport:
    """Execute Pillar 25 (25A + 25B + O_RDONLY donor/clean-room inspection) under strict air-gap safety locks."""
    t0 = time.monotonic()
    donor_snapshot = inspect_phase184_donors_readonly(force_clean_room=force_clean_room)
    p25a = run_pillar25a_fx3bndl1_binding_8_scenario_suite()
    p25b = run_pillar25b_exfat_hygiene_8_scenario_suite()

    elapsed = round(time.monotonic() - t0, 6)
    under_6s = elapsed < P184_CONCURRENT_CEILING_SECONDS

    errors: List[str] = []
    if not donor_snapshot.all_passed:
        errors.extend(donor_snapshot.errors)
    if not p25a.passed:
        errors.append("Pillar 25A FX3BNDL1 cross-binding suite failed")
    if not p25b.passed:
        errors.append("Pillar 25B ExFAT/AppleDouble/ELF64/BODYDATA suite failed")
    if not under_6s:
        errors.append(f"wall-clock budget exceeded: {elapsed:.3f}s >= {P184_CONCURRENT_CEILING_SECONDS}s")

    all_ok = donor_snapshot.all_passed and p25a.passed and p25b.passed and under_6s and (len(errors) == 0)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE184_SCHEMA,
            "version": PHASE184_VERSION,
            "verification_mode": donor_snapshot.verification_mode,
            "donor_snapshot_sha256": donor_snapshot.snapshot_sha256,
            "pillar_25a": p25a.to_dict(),
            "pillar_25b": p25b.to_dict(),
            "all_passed": all_ok,
        }
    )

    return Pillar25AirgapSdBundleReport(
        schema=PHASE184_SCHEMA,
        version=PHASE184_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P184_STATUS_VERIFIED_SUITE if all_ok else P184_STATUS_FAIL_SUITE,
        elapsed_seconds=elapsed,
        under_6s_budget=under_6s,
        donor_snapshot=donor_snapshot,
        pillar_25a_fx3bndl1_binding=p25a,
        pillar_25b_exfat_hygiene=p25b,
        suite_sha256=suite_sha,
        errors=tuple(errors),
    )
