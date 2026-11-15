"""Phase 72 — Tier-0 Backup GF(256) Parity Bit-Rot Healer, Short-Read/Blank-Flash Detector & Cross-Body Anti-Transplant Lock.

Provides three offline read-only recovery-backup integrity pillars for Sony FX3 (`0x91030080`):

1. **11-Partition Tier-0 Backup Truncation, Blank-Flash & A/B Slot Symmetry Verifier**:
   Validates host-side `Tier-0` readback bundles across all 11 critical partitions:
   `nbl_a`, `nbl_b`, `uboot_a`, `uboot_b`, `boot_a`, `boot_b`, `p1_vfat`, `bk4_nvram`,
   `wbi2_hibdrv`, `cnflasha_spacc`, `c2pa_rq_lic`.
   - Rejects `dd` short reads, unaligned reads, and header-declared size overflows (`TRUNCATED_PARTITION_DUMP`)
   - Rejects disconnected/erased bus reads (`ALL_ZERO_BLANK_READ`, `ALL_FF_ERASED_FLASH_READ`, `DEGENERATE_BYTE_ENTROPY`)
   - Verifies structural partition magics (`ELF`/`FDT`/`Image`, `FAT12/16` `0x55AA`, `BK4\\0` + FX3 `0x91030080`,
     `WBI2` + XOR `0x0F0F0F0F`, high-entropy `cnflasha` XTS, and `RQLC`/`C2PA`/`jumb` license structure)
     without embedding any proprietary Sony keys
   - Enforces A/B slot symmetry across `(nbl_a, nbl_b)`, `(uboot_a, uboot_b)`, `(boot_a, boot_b)`

2. **Pure-Python `GF(2^8)` (`0x11d`) Dual-Parity (`P + Q` RAID-6) Bit-Rot Healer**:
   Precomputes exact `exp`/`log`/`inv` and `bytes.translate` multiplication tables over
   `GF(2^8)` with primitive polynomial `x^8 + x^4 + x^3 + x^2 + 1` (`0x11D`, generator `g = 0x02`).
   - Encodes `k`-data + `2`-parity (`P = XOR(D_i)`, `Q = XOR(g^i * D_i)`) stripes
   - Heals up to 2 simultaneous erasures (any 2 data shards, data+P, data+Q, or P+Q)
   - Heals 1-shard silent bit-rot via pure `GF(256)` syndrome localization (`S1 / S0 == g^x`)
     and up to 2 corrupted/erased shards via per-shard SHA-256 + `GF(256)` solver, proving
     `reconstructed_sha256 == original_sha256`
   - Fails closed on `>= 3` simultaneous shard losses (`UNRECOVERABLE_QUORUM_LOSS`)

3. **Per-Body Hardware Identity Lock (`Cross-Body Anti-Transplant Firewall`)**:
   Cryptographically binds every `tier0_backup_manifest_v1` manifest to
   `body_identity_binding_sha256` derived from
   `(camera_model, body_serial_hash, cnflasha_calibration_sha256, c2pa_rq_lic_sha256)`.
   Fails closed (`CROSS_BODY_TRANSPLANT_FORBIDDEN`) if `Body-A`'s calibration or C2PA
   license (`cnflasha` / `RQ_LIC.DAT`) is paired with `Body-B`.

Safety Redlines (Hard-Locked):
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `ALLOW_BOOT_PARTITION_TARGETING = False`
- `ALLOW_DESTRUCTIVE_FASTBOOT = False`
- `PHYSICAL_DEVICE_WRITES = 0`
- Local donor artifacts opened strictly `os.O_RDONLY` when available.
- Never prints raw binary `bytes` reprs; all digests/samples use `.hex()` / `.hexdigest()`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import struct
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .emmc_dump_forensic_verifier import (
    BK4_MAGIC,
    FX3_PRODUCT_MODEL_ID,
    WBI2_MAGIC,
    analyze_bus_and_entropy,
    build_synthetic_encrypted_cnflasha,
    build_synthetic_p1_vfat_image,
    build_synthetic_p2_bk4_image,
    build_synthetic_p5_wbi2_image,
    compute_shannon_entropy,
    verify_p1_vfat_dump,
    verify_p2_bk4_nvram_dump,
    verify_p5_wbi2_dump,
)
from .files import is_forced_clean_room, read_file, require, resolve_donor_path


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

TIER0_BACKUP_GUARD_SCHEMA: str = "fx3-tier0-backup-parity-and-manifest-guard-v1"
TIER0_BACKUP_MANIFEST_SCHEMA: str = "tier0_backup_manifest_v1"
TIER0_BACKUP_GUARD_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True
PHYSICAL_DEVICE_WRITES: int = 0

DONOR_P1_205_RELPATH: str = "fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1"
DONOR_P5_WBI2_RELPATH: str = "sony-firmware-20261024/stage2/extraction/nflasha5.img"

TIER0_PARTITION_NAMES: Tuple[str, ...] = (
    "nbl_a",
    "nbl_b",
    "uboot_a",
    "uboot_b",
    "boot_a",
    "boot_b",
    "p1_vfat",
    "bk4_nvram",
    "wbi2_hibdrv",
    "cnflasha_spacc",
    "c2pa_rq_lic",
)

TIER0_AB_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("nbl_a", "nbl_b"),
    ("uboot_a", "uboot_b"),
    ("boot_a", "boot_b"),
)

TIER0_MIN_PARTITION_BYTES: Dict[str, int] = {
    "nbl_a": 2048,
    "nbl_b": 2048,
    "uboot_a": 2048,
    "uboot_b": 2048,
    "boot_a": 2048,
    "boot_b": 2048,
    "p1_vfat": 512,
    "bk4_nvram": 512,
    "wbi2_hibdrv": 512,
    "cnflasha_spacc": 4096,
    "c2pa_rq_lic": 512,
}

# Structural Magics (zero proprietary keys)
ELF_MAGIC: bytes = b"\x7fELF"
FDT_MAGIC: bytes = b"\xd0\x0d\xfe\xed"
UIMAGE_MAGIC: bytes = b"\x27\x05\x19\x56"
ANDROID_BOOT_MAGIC: bytes = b"ANDROID!"
ARM64_IMAGE_MAGIC: bytes = b"ARM\x64"
NBL_MAGIC: bytes = b"NBL0"
RQLC_MAGIC: bytes = b"RQLC"
C2PA_MAGIC: bytes = b"C2PA"
JUMBF_BOX_TYPE: bytes = b"jumb"

# Status & Fail-Closed Error Codes
STATUS_VERIFIED_TIER0_BACKUP: str = "VERIFIED_TIER0_BACKUP"
STATUS_FAIL_TIER0_BACKUP: str = "FAIL_TIER0_BACKUP"

ERR_MISSING_PARTITION: str = "MISSING_PARTITION_DUMP"
ERR_TRUNCATED_PARTITION: str = "TRUNCATED_PARTITION_DUMP"
ERR_ALL_ZERO_BLANK_READ: str = "ALL_ZERO_BLANK_READ"
ERR_ALL_FF_ERASED_FLASH_READ: str = "ALL_FF_ERASED_FLASH_READ"
ERR_DEGENERATE_BYTE_ENTROPY: str = "DEGENERATE_BYTE_ENTROPY"
ERR_INVALID_STRUCTURAL_MAGIC: str = "INVALID_STRUCTURAL_MAGIC"
ERR_AB_SLOT_ASYMMETRY: str = "AB_SLOT_ASYMMETRY_DETECTED"
ERR_UNRECOVERABLE_QUORUM_LOSS: str = "UNRECOVERABLE_QUORUM_LOSS"
ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN: str = "CROSS_BODY_TRANSPLANT_FORBIDDEN"
ERR_SAFETY_POLICY_VIOLATION: str = "SAFETY_POLICY_VIOLATION"

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

# ---------------------------------------------------------------------------
# GF(2^8) Arithmetic over Primitive Polynomial 0x11D (x^8 + x^4 + x^3 + x^2 + 1)
# ---------------------------------------------------------------------------

GF256_PRIMITIVE_POLY: int = 0x11D
GF256_GENERATOR: int = 0x02


def _build_gf256_tables() -> Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], Tuple[bytes, ...]]:
    exp_tbl = [0] * 510
    log_tbl = [-1] * 256
    x = 1
    for i in range(255):
        exp_tbl[i] = x
        exp_tbl[i + 255] = x
        log_tbl[x] = i
        x <<= 1
        if x & 0x100:
            x ^= GF256_PRIMITIVE_POLY

    inv_tbl = [0] * 256
    for a in range(1, 256):
        inv_tbl[a] = exp_tbl[255 - log_tbl[a]]

    mul_tables: List[bytes] = []
    mul_tables.append(bytes(256))
    for c in range(1, 256):
        lc = log_tbl[c]
        row = bytearray(256)
        for v in range(1, 256):
            row[v] = exp_tbl[lc + log_tbl[v]]
        mul_tables.append(bytes(row))

    return tuple(exp_tbl), tuple(log_tbl), tuple(inv_tbl), tuple(mul_tables)


GF256_EXP, GF256_LOG, GF256_INV, GF256_MUL_TABLES = _build_gf256_tables()


def gf256_add(a: int, b: int) -> int:
    return (a ^ b) & 0xFF


def gf256_sub(a: int, b: int) -> int:
    return (a ^ b) & 0xFF


def gf256_mul(a: int, b: int) -> int:
    a &= 0xFF
    b &= 0xFF
    if a == 0 or b == 0:
        return 0
    return GF256_EXP[GF256_LOG[a] + GF256_LOG[b]]


def gf256_inv(a: int) -> int:
    a &= 0xFF
    if a == 0:
        raise ZeroDivisionError("Zero has no multiplicative inverse in GF(256)")
    return GF256_INV[a]


def gf256_div(a: int, b: int) -> int:
    a &= 0xFF
    b &= 0xFF
    if b == 0:
        raise ZeroDivisionError("Division by zero in GF(256)")
    if a == 0:
        return 0
    return GF256_EXP[(GF256_LOG[a] - GF256_LOG[b]) % 255]


def gf256_pow(a: int, exponent: int) -> int:
    a &= 0xFF
    if exponent == 0:
        return 1
    if a == 0:
        return 0
    return GF256_EXP[(GF256_LOG[a] * exponent) % 255]


def _gf256_scale_bytes(scalar: int, data: bytes) -> bytes:
    scalar &= 0xFF
    if scalar == 0:
        return b"\x00" * len(data)
    if scalar == 1:
        return data
    return data.translate(GF256_MUL_TABLES[scalar])


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    n = len(a)
    if n != len(b):
        raise ValueError(f"XOR length mismatch: {n} != {len(b)}")
    if n == 0:
        return b""
    return (int.from_bytes(a, "little") ^ int.from_bytes(b, "little")).to_bytes(n, "little")


def _xor_many(chunks: Sequence[bytes], length: int) -> bytes:
    if length == 0:
        return b""
    acc = 0
    for c in chunks:
        if len(c) != length:
            raise ValueError(f"Shard length mismatch: {len(c)} != {length}")
        acc ^= int.from_bytes(c, "little")
    return acc.to_bytes(length, "little")


# ---------------------------------------------------------------------------
# Structured Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PartitionValidationResult:
    name: str
    passed: bool
    byte_length: int
    sha256: str
    magic_detected: str
    shannon_entropy_bits: float
    all_zero_pages: int
    all_ff_pages: int
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class AbSlotSymmetryResult:
    slot_pair: str
    slot_a: str
    slot_b: str
    symmetric: bool
    size_match: bool
    magic_match: bool
    digest_match: bool
    slot_a_sha256: str
    slot_b_sha256: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Tier0BundleValidationReport:
    passed: bool
    status: str
    partition_count: int
    partitions: Tuple[PartitionValidationResult, ...]
    ab_symmetry: Tuple[AbSlotSymmetryResult, ...]
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_device_writes: int


@dataclass(frozen=True)
class Gf256ParityStripe:
    shard_names: Tuple[str, ...]
    shard_sizes: Tuple[int, ...]
    shard_sha256s: Tuple[str, ...]
    stripe_bytes: int
    p_parity: bytes
    q_parity: bytes
    p_sha256: str
    q_sha256: str


@dataclass(frozen=True)
class Gf256HealResult:
    passed: bool
    status: str
    repair_mode: str
    erased_indices: Tuple[int, ...]
    corrupted_indices: Tuple[int, ...]
    healed_indices: Tuple[int, ...]
    healed_names: Tuple[str, ...]
    reconstructed_shards: Optional[Tuple[bytes, ...]]
    reconstructed_sha256s: Tuple[str, ...]
    original_bundle_sha256: str
    reconstructed_bundle_sha256: str
    bit_exact_match: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class BodyHardwareIdentity:
    camera_model: str
    body_serial_hash: str
    cnflasha_calibration_sha256: str
    c2pa_rq_lic_sha256: str
    body_identity_binding_sha256: str


@dataclass(frozen=True)
class Tier0BackupManifest:
    schema: str
    camera_model: str
    body_serial_hash: str
    cnflasha_calibration_sha256: str
    c2pa_rq_lic_sha256: str
    body_identity_binding_sha256: str
    partition_order: Tuple[str, ...]
    partition_sizes: Dict[str, int]
    partition_sha256s: Dict[str, str]
    stripe_bytes: int
    p_parity_sha256: str
    q_parity_sha256: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_device_writes: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AntiTransplantDecision:
    allowed: bool
    status: str
    manifest_binding_sha256: str
    target_binding_sha256: str
    mismatch_reasons: Tuple[str, ...]
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_device_writes: int


@dataclass(frozen=True)
class Tier0HealBundleReport:
    passed: bool
    status: str
    repair_mode: str
    healed_partitions: Tuple[str, ...]
    original_bundle_sha256: str
    reconstructed_bundle_sha256: str
    bit_exact_match: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_device_writes: int


@dataclass(frozen=True)
class Tier0BackupSuiteReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    donor_p1_sha256: str
    donor_p5_wbi2_sha256: str
    bundle_validation: Tier0BundleValidationReport
    manifest: Tier0BackupManifest
    anti_transplant_same_body: AntiTransplantDecision
    anti_transplant_cross_body_blocked: AntiTransplantDecision
    heal_1_erasure: Tier0HealBundleReport
    heal_2_erasures: Tier0HealBundleReport
    heal_1_silent_bitrot: Tier0HealBundleReport
    reject_3_losses: Tier0HealBundleReport
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    physical_device_writes: int
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# 1. 11-Partition Tier-0 Truncation, Blank-Flash & A/B Symmetry Verifier
# ---------------------------------------------------------------------------


def _detect_nbl_magic(data: bytes) -> Tuple[bool, str, Optional[str]]:
    if len(data) < 64:
        return False, "TRUNCATED", "NBL header shorter than 64 bytes"
    if data[:4] == ELF_MAGIC:
        return True, "ELF64", None
    if data[:4] == FDT_MAGIC:
        total_sz = struct.unpack_from(">I", data, 4)[0]
        if total_sz > len(data) or total_sz < 40:
            return False, "FDT_TRUNCATED", f"FDT totalsize={total_sz} outside len={len(data)}"
        return True, "FDT", None
    if len(data) >= 0x40 and data[0x38:0x3C] == ARM64_IMAGE_MAGIC:
        return True, "ARM64_IMAGE", None
    if data[:4] == NBL_MAGIC:
        declared = struct.unpack_from("<I", data, 8)[0]
        if declared > len(data) or declared < 64:
            return False, "NBL0_TRUNCATED", f"NBL0 declared_size={declared} outside len={len(data)}"
        return True, "NBL0", None
    word0 = struct.unpack_from("<I", data, 0)[0]
    if (word0 & 0xFC000000) == 0x14000000:
        return True, "AARCH64_BRANCH", None
    return False, "UNKNOWN", f"Unrecognized NBL magic: 0x{data[:4].hex()}"


def _detect_uboot_magic(data: bytes) -> Tuple[bool, str, Optional[str]]:
    if len(data) < 64:
        return False, "TRUNCATED", "U-Boot header shorter than 64 bytes"
    if data[:4] == ELF_MAGIC:
        return True, "ELF64", None
    if data[:4] == FDT_MAGIC:
        total_sz = struct.unpack_from(">I", data, 4)[0]
        if total_sz > len(data) or total_sz < 40:
            return False, "FIT_FDT_TRUNCATED", f"FIT/FDT totalsize={total_sz} outside len={len(data)}"
        return True, "FIT_FDT", None
    if data[:4] == UIMAGE_MAGIC:
        ih_size = struct.unpack_from(">I", data, 12)[0]
        if 64 + ih_size > len(data):
            return False, "UIMAGE_TRUNCATED", f"uImage payload 64+{ih_size} exceeds len={len(data)}"
        return True, "UIMAGE", None
    if len(data) >= 0x40 and data[0x38:0x3C] == ARM64_IMAGE_MAGIC:
        return True, "ARM64_IMAGE", None
    return False, "UNKNOWN", f"Unrecognized U-Boot magic: 0x{data[:4].hex()}"


def _detect_boot_magic(data: bytes) -> Tuple[bool, str, Optional[str]]:
    if len(data) < 64:
        return False, "TRUNCATED", "Boot image header shorter than 64 bytes"
    if data[:8] == ANDROID_BOOT_MAGIC and len(data) >= 40:
        k_size, _, r_size = struct.unpack_from("<III", data, 8)
        page_sz = struct.unpack_from("<I", data, 36)[0] or 2048
        min_needed = page_sz + ((k_size + page_sz - 1) // page_sz) * page_sz + ((r_size + page_sz - 1) // page_sz) * page_sz
        if min_needed > len(data):
            return False, "ANDROID_BOOT_TRUNCATED", f"Android boot image needs {min_needed}B, got {len(data)}B"
        return True, "ANDROID_BOOT", None
    if data[:4] == FDT_MAGIC:
        total_sz = struct.unpack_from(">I", data, 4)[0]
        if total_sz > len(data) or total_sz < 40:
            return False, "FIT_FDT_TRUNCATED", f"Boot FIT/FDT totalsize={total_sz} outside len={len(data)}"
        return True, "FIT_FDT", None
    if len(data) >= 0x40 and data[0x38:0x3C] == ARM64_IMAGE_MAGIC:
        return True, "ARM64_IMAGE", None
    if data[:4] == ELF_MAGIC:
        return True, "ELF64", None
    return False, "UNKNOWN", f"Unrecognized boot image magic: 0x{data[:8].hex()}"


def _detect_c2pa_rq_lic_magic(data: bytes) -> Tuple[bool, str, Optional[str]]:
    if len(data) < 64:
        return False, "TRUNCATED", "RQ_LIC.DAT shorter than 64 bytes"
    if data[:4] in (RQLC_MAGIC, C2PA_MAGIC):
        declared = struct.unpack_from("<I", data, 8)[0]
        if declared < 32 or declared > len(data):
            return False, "C2PA_RQLIC_TRUNCATED", f"C2PA/RQLC declared_size={declared} outside len={len(data)}"
        return True, data[:4].decode("ascii"), None
    if len(data) >= 8 and data[4:8] == JUMBF_BOX_TYPE:
        box_len = struct.unpack_from(">I", data, 0)[0]
        if box_len < 16 or box_len > len(data):
            return False, "JUMBF_TRUNCATED", f"JUMBF box_len={box_len} outside len={len(data)}"
        return True, "C2PA_JUMBF", None
    if data.lstrip().startswith(b"{"):
        try:
            obj = json.loads(data.decode("utf-8"))
        except Exception as exc:
            return False, "JSON_INVALID", f"Invalid JSON RQ_LIC container: {exc}"
        if isinstance(obj, dict) and ("schema" in obj or "c2pa" in obj):
            return True, "C2PA_JSON", None
    return False, "UNKNOWN", f"Unrecognized RQ_LIC.DAT/C2PA magic: 0x{data[:8].hex()}"


def _partition_bus_and_entropy_check(name: str, data: bytes) -> Tuple[List[str], List[str], float, int, int]:
    """Run blank-read, stuck-bus, alignment, and Shannon entropy checks for a Tier-0 partition."""
    codes: List[str] = []
    errors: List[str] = []
    n = len(data)
    if n == 0:
        codes.append(ERR_TRUNCATED_PARTITION)
        errors.append(f"{ERR_TRUNCATED_PARTITION}:{name}:empty_0_bytes")
        return codes, errors, 0.0, 0, 0

    first = data[0]
    if data.count(first) == n:
        if first == 0x00:
            codes.append(ERR_ALL_ZERO_BLANK_READ)
            errors.append(f"{ERR_ALL_ZERO_BLANK_READ}:{name}:all_zero_{n}B")
        elif first == 0xFF:
            codes.append(ERR_ALL_FF_ERASED_FLASH_READ)
            errors.append(f"{ERR_ALL_FF_ERASED_FLASH_READ}:{name}:all_ff_{n}B")
        else:
            codes.append(ERR_DEGENERATE_BYTE_ENTROPY)
            errors.append(f"{ERR_DEGENERATE_BYTE_ENTROPY}:{name}:constant_fill_0x{first:02x}")
        return codes, errors, 0.0, (n // 4096 if first == 0 else 0), (n // 4096 if first == 0xFF else 0)

    if name != "wbi2_hibdrv" and (n % 512 != 0):
        codes.append(ERR_TRUNCATED_PARTITION)
        errors.append(f"{ERR_TRUNCATED_PARTITION}:{name}:unaligned_bytes={n},mod512={n % 512}")

    eff_page = 4096 if n >= 4096 else 512
    total_pages = n // eff_page
    zero_pat = b"\x00" * eff_page
    ff_pat = b"\xff" * eff_page
    all_zero_pages = 0
    all_ff_pages = 0
    cur_f = 0
    max_f = 0
    mv = memoryview(data)
    for idx in range(total_pages):
        blk = mv[idx * eff_page : (idx + 1) * eff_page]
        if blk == zero_pat:
            all_zero_pages += 1
            cur_f = 0
        elif blk == ff_pat:
            all_ff_pages += 1
            cur_f += 1
            if cur_f > max_f:
                max_f = cur_f
        else:
            cur_f = 0

    is_encrypted = name == "cnflasha_spacc"
    if is_encrypted and (all_zero_pages > 0 or all_ff_pages > 0):
        codes.append(ERR_DEGENERATE_BYTE_ENTROPY)
        errors.append(f"{name}:STUCK_BUS_IN_ENCRYPTED_IMAGE:zero={all_zero_pages},ff={all_ff_pages}")
    elif total_pages > 0:
        if (all_ff_pages / total_pages) > 0.25 or max_f >= 16:
            codes.append(ERR_DEGENERATE_BYTE_ENTROPY)
            errors.append(f"{name}:STUCK_BUS_0xFF_RUN:ff_pages={all_ff_pages},max_contig_ff={max_f}")
        if (all_zero_pages / total_pages) > 0.85:
            codes.append(ERR_DEGENERATE_BYTE_ENTROPY)
            errors.append(f"{name}:STUCK_BUS_0x00_EXCESS:zero_pages={all_zero_pages}")

    if n <= 65536:
        ent = compute_shannon_entropy(data)
    else:
        win = 16384
        sample = data[:win] + data[n // 2 : n // 2 + win] + data[n - win :]
        ent = compute_shannon_entropy(sample)

    min_ent = 7.25 if is_encrypted else 2.25
    if ent < min_ent:
        codes.append(ERR_DEGENERATE_BYTE_ENTROPY)
        errors.append(f"{name}:ENTROPY_COLLAPSE:shannon={ent:.4f},floor={min_ent:.4f}")

    return codes, errors, ent, all_zero_pages, all_ff_pages


def validate_tier0_partition(
    name: str,
    data: Optional[bytes],
    *,
    expected_size: Optional[int] = None,
) -> PartitionValidationResult:
    """Validate a single Tier-0 partition dump for truncation, blank reads, entropy, and structural magic."""
    if data is None:
        return PartitionValidationResult(
            name=name,
            passed=False,
            byte_length=0,
            sha256="",
            magic_detected="MISSING",
            shannon_entropy_bits=0.0,
            all_zero_pages=0,
            all_ff_pages=0,
            error_codes=(ERR_MISSING_PARTITION,),
            errors=(f"{ERR_MISSING_PARTITION}:{name}",),
        )

    n = len(data)
    digest = sha256(data).hexdigest()
    codes, errors, ent, zero_pages, ff_pages = _partition_bus_and_entropy_check(name, data)

    min_bytes = TIER0_MIN_PARTITION_BYTES.get(name, 512)
    if n > 0 and n < min_bytes:
        if ERR_TRUNCATED_PARTITION not in codes:
            codes.append(ERR_TRUNCATED_PARTITION)
        errors.append(f"{ERR_TRUNCATED_PARTITION}:{name}:got={n},min={min_bytes}")
    if expected_size is not None and n != expected_size:
        if ERR_TRUNCATED_PARTITION not in codes:
            codes.append(ERR_TRUNCATED_PARTITION)
        errors.append(f"{ERR_TRUNCATED_PARTITION}:{name}:got={n},expected={expected_size}")

    magic_detected = "UNKNOWN"
    magic_ok = True

    if n > 0 and not any(c in codes for c in (ERR_ALL_ZERO_BLANK_READ, ERR_ALL_FF_ERASED_FLASH_READ)):
        if name in ("nbl_a", "nbl_b"):
            magic_ok, magic_detected, err = _detect_nbl_magic(data)
            if not magic_ok:
                codes.append(ERR_TRUNCATED_PARTITION if "TRUNCATED" in magic_detected else ERR_INVALID_STRUCTURAL_MAGIC)
                errors.append(f"{name}:{err}")
        elif name in ("uboot_a", "uboot_b"):
            magic_ok, magic_detected, err = _detect_uboot_magic(data)
            if not magic_ok:
                codes.append(ERR_TRUNCATED_PARTITION if "TRUNCATED" in magic_detected else ERR_INVALID_STRUCTURAL_MAGIC)
                errors.append(f"{name}:{err}")
        elif name in ("boot_a", "boot_b"):
            magic_ok, magic_detected, err = _detect_boot_magic(data)
            if not magic_ok:
                codes.append(ERR_TRUNCATED_PARTITION if "TRUNCATED" in magic_detected else ERR_INVALID_STRUCTURAL_MAGIC)
                errors.append(f"{name}:{err}")
        elif name == "p1_vfat":
            rep = verify_p1_vfat_dump(data, check_fat_tree=True)
            magic_ok = rep.valid
            magic_detected = "FAT12_0x55AA" if rep.magic_ok else "BAD_FAT_SIG"
            if not rep.valid:
                is_trunc = any("TRUNCATED" in e or "exceeds" in e for e in rep.errors)
                codes.append(ERR_TRUNCATED_PARTITION if is_trunc else ERR_INVALID_STRUCTURAL_MAGIC)
                errors.extend(f"{name}:{e}" for e in rep.errors)
        elif name == "bk4_nvram":
            rep = verify_p2_bk4_nvram_dump(data, expected_product_model_id=FX3_PRODUCT_MODEL_ID)
            magic_ok = rep.valid
            magic_detected = "BK4_FX3" if rep.valid else ("BK4_HEADER" if rep.magic_ok else "BAD_BK4")
            if not rep.valid:
                is_trunc = any("TRUNCATED" in e or "OUT_OF_BOUNDS" in e for e in rep.errors)
                codes.append(ERR_TRUNCATED_PARTITION if is_trunc else ERR_INVALID_STRUCTURAL_MAGIC)
                errors.extend(f"{name}:{e}" for e in rep.errors)
        elif name == "wbi2_hibdrv":
            rep = verify_p5_wbi2_dump(data)
            magic_ok = rep.valid
            magic_detected = "WBI2" if rep.magic_ok else "BAD_WBI2"
            if not rep.valid:
                is_trunc = any("TRUNCATED" in e or "OUT_OF_BOUNDS" in e or "OVERRUNS" in e for e in rep.errors)
                codes.append(ERR_TRUNCATED_PARTITION if is_trunc else ERR_INVALID_STRUCTURAL_MAGIC)
                errors.extend(f"{name}:{e}" for e in rep.errors)
        elif name == "cnflasha_spacc":
            magic_detected = "AES_XTS_HIGH_ENTROPY"
            if ent < 7.25:
                magic_ok = False
                if ERR_DEGENERATE_BYTE_ENTROPY not in codes:
                    codes.append(ERR_DEGENERATE_BYTE_ENTROPY)
                errors.append(f"{name}:cnflasha_entropy_too_low:{ent:.4f}<7.2500")
        elif name == "c2pa_rq_lic":
            magic_ok, magic_detected, err = _detect_c2pa_rq_lic_magic(data)
            if not magic_ok:
                codes.append(ERR_TRUNCATED_PARTITION if "TRUNCATED" in magic_detected else ERR_INVALID_STRUCTURAL_MAGIC)
                errors.append(f"{name}:{err}")
    else:
        magic_ok = False

    dedup_codes = tuple(dict.fromkeys(codes))
    dedup_errors = tuple(dict.fromkeys(errors))
    passed = (len(dedup_codes) == 0) and (len(dedup_errors) == 0) and magic_ok
    return PartitionValidationResult(
        name=name,
        passed=passed,
        byte_length=n,
        sha256=digest,
        magic_detected=magic_detected,
        shannon_entropy_bits=ent,
        all_zero_pages=zero_pages,
        all_ff_pages=ff_pages,
        error_codes=dedup_codes,
        errors=dedup_errors,
    )


def validate_tier0_backup_bundle(
    bundle: Mapping[str, Optional[bytes]],
    *,
    expected_sizes: Optional[Mapping[str, int]] = None,
    require_ab_symmetry: bool = True,
) -> Tier0BundleValidationReport:
    """Validate all 11 Tier-0 partitions for truncation, blank-flash reads, magics, and A/B symmetry."""
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent eMMC writes must stay disabled")
    require(PERSISTENT_WRITE_RELEASE is False, "persistent write release must stay disabled")

    part_results: List[PartitionValidationResult] = []
    by_name: Dict[str, PartitionValidationResult] = {}
    all_codes: List[str] = []
    all_errors: List[str] = []

    for name in TIER0_PARTITION_NAMES:
        exp_sz = expected_sizes.get(name) if expected_sizes is not None else None
        res = validate_tier0_partition(name, bundle.get(name), expected_size=exp_sz)
        part_results.append(res)
        by_name[name] = res
        all_codes.extend(res.error_codes)
        all_errors.extend(res.errors)

    ab_results: List[AbSlotSymmetryResult] = []
    for slot_a, slot_b in TIER0_AB_PAIRS:
        ra = by_name[slot_a]
        rb = by_name[slot_b]
        size_match = ra.byte_length > 0 and ra.byte_length == rb.byte_length
        magic_match = ra.passed and rb.passed and ra.magic_detected == rb.magic_detected
        digest_match = bool(ra.sha256) and ra.sha256 == rb.sha256
        pair_errors: List[str] = []
        if not size_match:
            pair_errors.append(f"{ERR_AB_SLOT_ASYMMETRY}:{slot_a}({ra.byte_length}B)!={slot_b}({rb.byte_length}B)")
        if not magic_match:
            pair_errors.append(f"{ERR_AB_SLOT_ASYMMETRY}:magic_{slot_a}({ra.magic_detected})!={slot_b}({rb.magic_detected})")
        if require_ab_symmetry and not digest_match:
            pair_errors.append(f"{ERR_AB_SLOT_ASYMMETRY}:sha256_{slot_a}!={slot_b}")
        symmetric = size_match and magic_match and (digest_match if require_ab_symmetry else True)
        if not symmetric:
            all_codes.append(ERR_AB_SLOT_ASYMMETRY)
            all_errors.extend(pair_errors)
        ab_results.append(
            AbSlotSymmetryResult(
                slot_pair=f"{slot_a}/{slot_b}",
                slot_a=slot_a,
                slot_b=slot_b,
                symmetric=symmetric,
                size_match=size_match,
                magic_match=magic_match,
                digest_match=digest_match,
                slot_a_sha256=ra.sha256,
                slot_b_sha256=rb.sha256,
                errors=tuple(pair_errors),
            )
        )

    dedup_codes = tuple(dict.fromkeys(all_codes))
    dedup_errors = tuple(dict.fromkeys(all_errors))
    passed = (len(dedup_codes) == 0) and (len(dedup_errors) == 0) and all(r.passed for r in part_results)
    return Tier0BundleValidationReport(
        passed=passed,
        status=STATUS_VERIFIED_TIER0_BACKUP if passed else STATUS_FAIL_TIER0_BACKUP,
        partition_count=len(TIER0_PARTITION_NAMES),
        partitions=tuple(part_results),
        ab_symmetry=tuple(ab_results),
        error_codes=dedup_codes,
        errors=dedup_errors,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# 2. Pure-Python GF(2^8) Dual-Parity (P + Q RAID-6) Encoder & Healer
# ---------------------------------------------------------------------------


def _bundle_digest(ordered_shards: Sequence[bytes]) -> str:
    h = sha256()
    for s in ordered_shards:
        h.update(struct.pack("<I", len(s)))
        h.update(s)
    return h.hexdigest()


def encode_gf256_pq_parity(
    shards: Sequence[bytes],
    *,
    shard_names: Optional[Sequence[str]] = None,
) -> Gf256ParityStripe:
    """Encode k data shards (1 <= k <= 254) into RAID-6 P (XOR) + Q (g^i) GF(256) parity."""
    k = len(shards)
    require(1 <= k <= 254, f"GF(256) P+Q supports 1..254 data shards, got {k}")
    names = tuple(shard_names) if shard_names is not None else tuple(f"shard_{i}" for i in range(k))
    require(len(names) == k, "shard_names length must match shards")

    sizes = tuple(len(s) for s in shards)
    stripe_bytes = max(sizes)
    require(stripe_bytes > 0, "Cannot encode empty shards with 0 stripe_bytes")

    padded = [s if len(s) == stripe_bytes else s + b"\x00" * (stripe_bytes - len(s)) for s in shards]
    p_parity = _xor_many(padded, stripe_bytes)
    q_terms = [_gf256_scale_bytes(GF256_EXP[i], padded[i]) for i in range(k)]
    q_parity = _xor_many(q_terms, stripe_bytes)

    return Gf256ParityStripe(
        shard_names=names,
        shard_sizes=sizes,
        shard_sha256s=tuple(sha256(s).hexdigest() for s in shards),
        stripe_bytes=stripe_bytes,
        p_parity=p_parity,
        q_parity=q_parity,
        p_sha256=sha256(p_parity).hexdigest(),
        q_sha256=sha256(q_parity).hexdigest(),
    )


def heal_gf256_pq_shards(
    shards: Sequence[Optional[bytes]],
    p_parity: Optional[bytes],
    q_parity: Optional[bytes],
    *,
    shard_sizes: Sequence[int],
    stripe_bytes: int,
    expected_shard_sha256s: Optional[Sequence[str]] = None,
    expected_p_sha256: Optional[str] = None,
    expected_q_sha256: Optional[str] = None,
    shard_names: Optional[Sequence[str]] = None,
) -> Tuple[Gf256HealResult, Optional[bytes], Optional[bytes]]:
    """Verify and heal up to 2 erased or corrupted shards (data or P/Q) in GF(2^8).

    Also supports pure GF(256) syndrome localization (`S1 / S0 == g^x`) when 1 data shard
    suffers silent bit-rot without relying on `expected_shard_sha256s`.
    Fails closed (`UNRECOVERABLE_QUORUM_LOSS`) if >= 3 shards are lost/corrupted.
    """
    k = len(shards)
    require(1 <= k <= 254 and len(shard_sizes) == k, "Invalid shard_sizes count")
    names = tuple(shard_names) if shard_names is not None else tuple(f"shard_{i}" for i in range(k))
    if expected_shard_sha256s is not None:
        require(len(expected_shard_sha256s) == k, "expected_shard_sha256s length mismatch")

    def _orig_bundle_digest() -> str:
        if expected_shard_sha256s is not None:
            return sha256(("|".join(expected_shard_sha256s)).encode("ascii")).hexdigest()
        return ""

    orig_digest = _orig_bundle_digest()

    erased_data: List[int] = []
    corrupted_data: List[int] = []
    padded_data: List[Optional[bytes]] = []

    for idx, raw in enumerate(shards):
        exp_sz = shard_sizes[idx]
        if raw is None:
            erased_data.append(idx)
            padded_data.append(None)
            continue
        if len(raw) != exp_sz:
            corrupted_data.append(idx)
            padded_data.append(None)
            continue
        if expected_shard_sha256s is not None and sha256(raw).hexdigest() != expected_shard_sha256s[idx]:
            corrupted_data.append(idx)
            padded_data.append(None)
            continue
        padded_data.append(raw if len(raw) == stripe_bytes else raw + b"\x00" * (stripe_bytes - len(raw)))

    p_erased = p_parity is None
    p_corrupt = (
        (p_parity is not None)
        and (
            len(p_parity) != stripe_bytes
            or (expected_p_sha256 is not None and sha256(p_parity).hexdigest() != expected_p_sha256)
        )
    )
    q_erased = q_parity is None
    q_corrupt = (
        (q_parity is not None)
        and (
            len(q_parity) != stripe_bytes
            or (expected_q_sha256 is not None and sha256(q_parity).hexdigest() != expected_q_sha256)
        )
    )

    damaged_data = sorted(set(erased_data) | set(corrupted_data))
    total_damaged = len(damaged_data) + (1 if (p_erased or p_corrupt) else 0) + (1 if (q_erased or q_corrupt) else 0)

    if total_damaged >= 3:
        msg = (
            f"{ERR_UNRECOVERABLE_QUORUM_LOSS}:damaged_count={total_damaged}>2,"
            f"data={damaged_data},p_lost={p_erased or p_corrupt},q_lost={q_erased or q_corrupt}"
        )
        return (
            Gf256HealResult(
                passed=False,
                status=STATUS_FAIL_TIER0_BACKUP,
                repair_mode=ERR_UNRECOVERABLE_QUORUM_LOSS,
                erased_indices=tuple(erased_data),
                corrupted_indices=tuple(corrupted_data),
                healed_indices=(),
                healed_names=(),
                reconstructed_shards=None,
                reconstructed_sha256s=(),
                original_bundle_sha256=orig_digest,
                reconstructed_bundle_sha256="",
                bit_exact_match=False,
                error_codes=(ERR_UNRECOVERABLE_QUORUM_LOSS,),
                errors=(msg,),
            ),
            None,
            None,
        )

    p_valid = (not p_erased) and (not p_corrupt)
    q_valid = (not q_erased) and (not q_corrupt)

    # Pure-syndrome path: 0 declared erasures & 0 SHA-flagged corruptions (or no SHA provided)
    if total_damaged == 0:
        assert p_parity is not None and q_parity is not None
        p_calc = _xor_many([s for s in padded_data if s is not None], stripe_bytes)
        q_calc = _xor_many([_gf256_scale_bytes(GF256_EXP[i], padded_data[i]) for i in range(k)], stripe_bytes)  # type: ignore[arg-type]
        s0 = _xor_bytes(p_parity, p_calc)
        s1 = _xor_bytes(q_parity, q_calc)
        if not any(s0) and not any(s1):
            final_shards = tuple(padded_data[i][: shard_sizes[i]] for i in range(k))  # type: ignore[index]
            recon_shas = tuple(sha256(s).hexdigest() for s in final_shards)
            recon_digest = sha256(("|".join(recon_shas)).encode("ascii")).hexdigest()
            return (
                Gf256HealResult(
                    passed=True,
                    status=STATUS_VERIFIED_TIER0_BACKUP,
                    repair_mode="HEALTHY_NO_REPAIR",
                    erased_indices=(),
                    corrupted_indices=(),
                    healed_indices=(),
                    healed_names=(),
                    reconstructed_shards=final_shards,
                    reconstructed_sha256s=recon_shas,
                    original_bundle_sha256=orig_digest or recon_digest,
                    reconstructed_bundle_sha256=recon_digest,
                    bit_exact_match=True,
                    error_codes=(),
                    errors=(),
                ),
                p_parity,
                q_parity,
            )

        # Single silent bit-rot localization via GF(256) syndrome ratio S1[b] / S0[b] == g^x
        if any(s0) and any(s1):
            # Find first byte position where S0 != 0
            first_nz = next(idx for idx, val in enumerate(s0) if val != 0)
            if s1[first_nz] != 0:
                ratio = gf256_div(s1[first_nz], s0[first_nz])
                x = GF256_LOG[ratio]
                if 0 <= x < k and s1 == _gf256_scale_bytes(GF256_EXP[x], s0):
                    # Verify trailing padding bytes beyond shard_sizes[x] remain zero after healing
                    healed_padded = _xor_bytes(padded_data[x], s0)  # type: ignore[arg-type]
                    if all(b == 0 for b in healed_padded[shard_sizes[x] :]):
                        padded_data[x] = healed_padded
                        final_shards = tuple(padded_data[i][: shard_sizes[i]] for i in range(k))  # type: ignore[index]
                        recon_shas = tuple(sha256(s).hexdigest() for s in final_shards)
                        recon_digest = sha256(("|".join(recon_shas)).encode("ascii")).hexdigest()
                        if expected_shard_sha256s is not None and recon_shas[x] != expected_shard_sha256s[x]:
                            return (
                                Gf256HealResult(
                                    passed=False,
                                    status=STATUS_FAIL_TIER0_BACKUP,
                                    repair_mode=ERR_UNRECOVERABLE_QUORUM_LOSS,
                                    erased_indices=(),
                                    corrupted_indices=(x,),
                                    healed_indices=(),
                                    healed_names=(),
                                    reconstructed_shards=None,
                                    reconstructed_sha256s=(),
                                    original_bundle_sha256=orig_digest,
                                    reconstructed_bundle_sha256="",
                                    bit_exact_match=False,
                                    error_codes=(ERR_UNRECOVERABLE_QUORUM_LOSS,),
                                    errors=(f"{ERR_UNRECOVERABLE_QUORUM_LOSS}:syndrome_post_heal_sha_mismatch",),
                                ),
                                None,
                                None,
                            )
                        return (
                            Gf256HealResult(
                                passed=True,
                                status=STATUS_VERIFIED_TIER0_BACKUP,
                                repair_mode="SYNDROME_SINGLE_CORRUPT_HEAL",
                                erased_indices=(),
                                corrupted_indices=(x,),
                                healed_indices=(x,),
                                healed_names=(names[x],),
                                reconstructed_shards=final_shards,
                                reconstructed_sha256s=recon_shas,
                                original_bundle_sha256=orig_digest or recon_digest,
                                reconstructed_bundle_sha256=recon_digest,
                                bit_exact_match=True,
                                error_codes=(),
                                errors=(),
                            ),
                            p_parity,
                            q_parity,
                        )

        return (
            Gf256HealResult(
                passed=False,
                status=STATUS_FAIL_TIER0_BACKUP,
                repair_mode=ERR_UNRECOVERABLE_QUORUM_LOSS,
                erased_indices=(),
                corrupted_indices=(),
                healed_indices=(),
                healed_names=(),
                reconstructed_shards=None,
                reconstructed_sha256s=(),
                original_bundle_sha256=orig_digest,
                reconstructed_bundle_sha256="",
                bit_exact_match=False,
                error_codes=(ERR_UNRECOVERABLE_QUORUM_LOSS,),
                errors=(f"{ERR_UNRECOVERABLE_QUORUM_LOSS}:multi_shard_unlocated_syndrome_mismatch",),
            ),
            None,
            None,
        )

    # Solve 1 or 2 damaged data shards (with parity intact) or data+parity / parity+parity
    repaired_p: Optional[bytes] = p_parity if p_valid else None
    repaired_q: Optional[bytes] = q_parity if q_valid else None

    if len(damaged_data) == 0:
        # Only P and/or Q were damaged; all data shards are intact
        repaired_p = _xor_many([s for s in padded_data if s is not None], stripe_bytes)
        repaired_q = _xor_many([_gf256_scale_bytes(GF256_EXP[i], padded_data[i]) for i in range(k)], stripe_bytes)  # type: ignore[arg-type]
        repair_mode = "PARITY_REBUILD_HEAL"
    elif len(damaged_data) == 1:
        x = damaged_data[0]
        if p_valid:
            others = [padded_data[i] for i in range(k) if i != x]
            padded_data[x] = _xor_many([p_parity, *others], stripe_bytes)  # type: ignore[list-item]
        else:
            # Recover D_x from Q: D_x = g^{-x} * (Q ^ XOR_{i != x}(g^i * D_i))
            assert q_valid and q_parity is not None
            q_others = [_gf256_scale_bytes(GF256_EXP[i], padded_data[i]) for i in range(k) if i != x]  # type: ignore[arg-type]
            q_rem = _xor_many([q_parity, *q_others], stripe_bytes)
            inv_gx = gf256_inv(GF256_EXP[x])
            padded_data[x] = _gf256_scale_bytes(inv_gx, q_rem)
        repaired_p = _xor_many([s for s in padded_data if s is not None], stripe_bytes)
        repaired_q = _xor_many([_gf256_scale_bytes(GF256_EXP[i], padded_data[i]) for i in range(k)], stripe_bytes)  # type: ignore[arg-type]
        repair_mode = "ERASURE_1_SHARD_HEAL" if (len(erased_data) == 1 and not corrupted_data) else "CORRUPTION_1_SHARD_HEAL"
    else:
        # Exactly 2 damaged data shards (x < y), both P and Q valid
        assert len(damaged_data) == 2 and p_valid and q_valid and p_parity is not None and q_parity is not None
        x, y = damaged_data[0], damaged_data[1]
        p_others = [padded_data[i] for i in range(k) if i not in (x, y)]
        q_others = [_gf256_scale_bytes(GF256_EXP[i], padded_data[i]) for i in range(k) if i not in (x, y)]  # type: ignore[arg-type]
        p_xy = _xor_many([p_parity, *p_others], stripe_bytes)
        q_xy = _xor_many([q_parity, *q_others], stripe_bytes)
        gx = GF256_EXP[x]
        gy = GF256_EXP[y]
        denom_inv = gf256_inv(gx ^ gy)
        # D_y = (g^x ^ g^y)^(-1) * (g^x * P_xy ^ Q_xy)
        rhs = _xor_bytes(_gf256_scale_bytes(gx, p_xy), q_xy)
        d_y = _gf256_scale_bytes(denom_inv, rhs)
        d_x = _xor_bytes(p_xy, d_y)
        padded_data[x] = d_x
        padded_data[y] = d_y
        if len(erased_data) == 2:
            repair_mode = "ERASURE_2_SHARD_HEAL"
        elif len(corrupted_data) == 2:
            repair_mode = "CORRUPTION_2_SHARD_HEAL"
        else:
            repair_mode = "MIXED_ERASE_AND_CORRUPT_2_SHARD_HEAL"

    final_shards = tuple(padded_data[i][: shard_sizes[i]] for i in range(k))  # type: ignore[index]
    recon_shas = tuple(sha256(s).hexdigest() for s in final_shards)
    recon_digest = sha256(("|".join(recon_shas)).encode("ascii")).hexdigest()

    # Post-heal SHA-256 verification (fail closed if an undeclared 3rd shard was silently corrupted)
    post_errors: List[str] = []
    if expected_shard_sha256s is not None:
        for idx in range(k):
            if recon_shas[idx] != expected_shard_sha256s[idx]:
                post_errors.append(f"{ERR_UNRECOVERABLE_QUORUM_LOSS}:post_heal_sha_mismatch:{names[idx]}")
    if expected_p_sha256 is not None and repaired_p is not None and sha256(repaired_p).hexdigest() != expected_p_sha256:
        post_errors.append(f"{ERR_UNRECOVERABLE_QUORUM_LOSS}:post_heal_p_parity_sha_mismatch")
    if expected_q_sha256 is not None and repaired_q is not None and sha256(repaired_q).hexdigest() != expected_q_sha256:
        post_errors.append(f"{ERR_UNRECOVERABLE_QUORUM_LOSS}:post_heal_q_parity_sha_mismatch")

    if post_errors:
        return (
            Gf256HealResult(
                passed=False,
                status=STATUS_FAIL_TIER0_BACKUP,
                repair_mode=ERR_UNRECOVERABLE_QUORUM_LOSS,
                erased_indices=tuple(erased_data),
                corrupted_indices=tuple(corrupted_data),
                healed_indices=(),
                healed_names=(),
                reconstructed_shards=None,
                reconstructed_sha256s=(),
                original_bundle_sha256=orig_digest,
                reconstructed_bundle_sha256="",
                bit_exact_match=False,
                error_codes=(ERR_UNRECOVERABLE_QUORUM_LOSS,),
                errors=tuple(post_errors),
            ),
            None,
            None,
        )

    bit_exact = (recon_digest == orig_digest) if orig_digest else True
    return (
        Gf256HealResult(
            passed=True,
            status=STATUS_VERIFIED_TIER0_BACKUP,
            repair_mode=repair_mode,
            erased_indices=tuple(erased_data),
            corrupted_indices=tuple(corrupted_data),
            healed_indices=tuple(damaged_data),
            healed_names=tuple(names[i] for i in damaged_data),
            reconstructed_shards=final_shards,
            reconstructed_sha256s=recon_shas,
            original_bundle_sha256=orig_digest or recon_digest,
            reconstructed_bundle_sha256=recon_digest,
            bit_exact_match=bit_exact,
            error_codes=(),
            errors=(),
        ),
        repaired_p,
        repaired_q,
    )


# ---------------------------------------------------------------------------
# 3. Per-Body Hardware Identity Lock (`Cross-Body Anti-Transplant Firewall`)
# ---------------------------------------------------------------------------


def _require_sha256_hex(value: str, label: str) -> str:
    norm = value.strip().lower()
    if not _SHA256_HEX_RE.match(norm):
        raise ValueError(f"{label} must be a 64-char lowercase hex SHA-256 digest (never raw serial)")
    return norm


def compute_body_identity_binding_sha256(
    camera_model: str,
    body_serial_hash: str,
    cnflasha_calibration_sha256: str,
    c2pa_rq_lic_sha256: str,
) -> str:
    """Derive deterministic cryptographic binding SHA-256 for a camera body."""
    model = camera_model.strip()
    require(bool(model), "camera_model must be non-empty")
    serial_h = _require_sha256_hex(body_serial_hash, "body_serial_hash")
    cnflash_h = _require_sha256_hex(cnflasha_calibration_sha256, "cnflasha_calibration_sha256")
    c2pa_h = _require_sha256_hex(c2pa_rq_lic_sha256, "c2pa_rq_lic_sha256")
    payload = {
        "domain": "fx3-tier0-body-identity-v1",
        "camera_model": model,
        "body_serial_hash": serial_h,
        "cnflasha_calibration_sha256": cnflash_h,
        "c2pa_rq_lic_sha256": c2pa_h,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def build_body_hardware_identity(
    *,
    camera_model: str,
    body_serial_hash: str,
    cnflasha_calibration_sha256: str,
    c2pa_rq_lic_sha256: str,
) -> BodyHardwareIdentity:
    serial_h = _require_sha256_hex(body_serial_hash, "body_serial_hash")
    cnflash_h = _require_sha256_hex(cnflasha_calibration_sha256, "cnflasha_calibration_sha256")
    c2pa_h = _require_sha256_hex(c2pa_rq_lic_sha256, "c2pa_rq_lic_sha256")
    binding = compute_body_identity_binding_sha256(camera_model, serial_h, cnflash_h, c2pa_h)
    return BodyHardwareIdentity(
        camera_model=camera_model.strip(),
        body_serial_hash=serial_h,
        cnflasha_calibration_sha256=cnflash_h,
        c2pa_rq_lic_sha256=c2pa_h,
        body_identity_binding_sha256=binding,
    )


def build_tier0_backup_manifest(
    bundle: Mapping[str, bytes],
    *,
    camera_model: str,
    body_serial_hash: str,
    require_ab_symmetry: bool = True,
) -> Tuple[Tier0BackupManifest, Gf256ParityStripe]:
    """Validate an 11-partition Tier-0 bundle, encode GF(256) P+Q parity, and bind body identity."""
    validation = validate_tier0_backup_bundle(bundle, require_ab_symmetry=require_ab_symmetry)
    if not validation.passed:
        raise ValueError(f"Cannot build manifest from invalid Tier-0 bundle: {validation.errors}")

    ordered_shards = [bundle[name] for name in TIER0_PARTITION_NAMES]
    parity = encode_gf256_pq_parity(ordered_shards, shard_names=TIER0_PARTITION_NAMES)

    cnflash_sha = sha256(bundle["cnflasha_spacc"]).hexdigest()
    c2pa_sha = sha256(bundle["c2pa_rq_lic"]).hexdigest()
    identity = build_body_hardware_identity(
        camera_model=camera_model,
        body_serial_hash=body_serial_hash,
        cnflasha_calibration_sha256=cnflash_sha,
        c2pa_rq_lic_sha256=c2pa_sha,
    )

    manifest = Tier0BackupManifest(
        schema=TIER0_BACKUP_MANIFEST_SCHEMA,
        camera_model=identity.camera_model,
        body_serial_hash=identity.body_serial_hash,
        cnflasha_calibration_sha256=identity.cnflasha_calibration_sha256,
        c2pa_rq_lic_sha256=identity.c2pa_rq_lic_sha256,
        body_identity_binding_sha256=identity.body_identity_binding_sha256,
        partition_order=TIER0_PARTITION_NAMES,
        partition_sizes={name: len(bundle[name]) for name in TIER0_PARTITION_NAMES},
        partition_sha256s={name: sha256(bundle[name]).hexdigest() for name in TIER0_PARTITION_NAMES},
        stripe_bytes=parity.stripe_bytes,
        p_parity_sha256=parity.p_sha256,
        q_parity_sha256=parity.q_sha256,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )
    return manifest, parity


def verify_cross_body_anti_transplant(
    manifest: Tier0BackupManifest,
    *,
    target_body_identity: Optional[BodyHardwareIdentity] = None,
    bundle_partitions: Optional[Mapping[str, bytes]] = None,
) -> AntiTransplantDecision:
    """Enforce per-body cryptographic lock; fail closed on any cross-body transplant attempt."""
    mismatches: List[str] = []
    codes: List[str] = []

    if manifest.schema != TIER0_BACKUP_MANIFEST_SCHEMA:
        codes.append(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN)
        mismatches.append(f"unexpected_manifest_schema:{manifest.schema}")

    if (
        manifest.persistent_emmc_writes_authorized is not False
        or manifest.persistent_write_release is not False
        or manifest.physical_device_writes != 0
    ):
        codes.append(ERR_SAFETY_POLICY_VIOLATION)
        mismatches.append("manifest_safety_flags_unlocked")

    try:
        recomputed_binding = compute_body_identity_binding_sha256(
            manifest.camera_model,
            manifest.body_serial_hash,
            manifest.cnflasha_calibration_sha256,
            manifest.c2pa_rq_lic_sha256,
        )
    except Exception as exc:
        codes.append(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN)
        mismatches.append(f"invalid_manifest_identity_fields:{exc}")
        recomputed_binding = ""

    if recomputed_binding and recomputed_binding != manifest.body_identity_binding_sha256:
        codes.append(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN)
        mismatches.append("manifest_body_identity_binding_sha256_tampered")

    if bundle_partitions is not None:
        if "cnflasha_spacc" in bundle_partitions:
            actual_cn = sha256(bundle_partitions["cnflasha_spacc"]).hexdigest()
            if actual_cn != manifest.cnflasha_calibration_sha256:
                codes.append(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN)
                mismatches.append("bundle_cnflasha_calibration_sha256_mismatch")
        if "c2pa_rq_lic" in bundle_partitions:
            actual_c2pa = sha256(bundle_partitions["c2pa_rq_lic"]).hexdigest()
            if actual_c2pa != manifest.c2pa_rq_lic_sha256:
                codes.append(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN)
                mismatches.append("bundle_c2pa_rq_lic_sha256_mismatch")

    target_binding = ""
    if target_body_identity is not None:
        expected_target_binding = compute_body_identity_binding_sha256(
            target_body_identity.camera_model,
            target_body_identity.body_serial_hash,
            target_body_identity.cnflasha_calibration_sha256,
            target_body_identity.c2pa_rq_lic_sha256,
        )
        target_binding = target_body_identity.body_identity_binding_sha256
        if expected_target_binding != target_binding:
            codes.append(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN)
            mismatches.append("target_body_identity_self_binding_invalid")
        if target_body_identity.camera_model != manifest.camera_model:
            codes.append(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN)
            mismatches.append(f"camera_model_mismatch:{manifest.camera_model}!={target_body_identity.camera_model}")
        if target_body_identity.body_serial_hash != manifest.body_serial_hash:
            codes.append(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN)
            mismatches.append("body_serial_hash_mismatch")
        if target_body_identity.cnflasha_calibration_sha256 != manifest.cnflasha_calibration_sha256:
            codes.append(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN)
            mismatches.append("cnflasha_calibration_sha256_mismatch")
        if target_body_identity.c2pa_rq_lic_sha256 != manifest.c2pa_rq_lic_sha256:
            codes.append(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN)
            mismatches.append("c2pa_rq_lic_sha256_mismatch")
        if target_binding != manifest.body_identity_binding_sha256:
            codes.append(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN)
            mismatches.append("body_identity_binding_sha256_mismatch")

    dedup_codes = tuple(dict.fromkeys(codes))
    errors = tuple(f"{ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN}:{m}" for m in mismatches)
    allowed = len(dedup_codes) == 0 and len(mismatches) == 0
    return AntiTransplantDecision(
        allowed=allowed,
        status=STATUS_VERIFIED_TIER0_BACKUP if allowed else ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN,
        manifest_binding_sha256=manifest.body_identity_binding_sha256,
        target_binding_sha256=target_binding or manifest.body_identity_binding_sha256,
        mismatch_reasons=tuple(mismatches),
        error_codes=dedup_codes,
        errors=errors,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


def heal_tier0_backup_bundle(
    damaged_bundle: Mapping[str, Optional[bytes]],
    manifest: Tier0BackupManifest,
    *,
    p_parity: Optional[bytes],
    q_parity: Optional[bytes],
    target_body_identity: Optional[BodyHardwareIdentity] = None,
    require_ab_symmetry: bool = True,
) -> Tuple[Tier0HealBundleReport, Optional[Dict[str, bytes]]]:
    """Reconstruct up to 2 lost/corrupted Tier-0 shards using GF(256) P+Q and enforce body lock."""
    anti_transplant = verify_cross_body_anti_transplant(manifest, target_body_identity=target_body_identity)
    if not anti_transplant.allowed:
        return (
            Tier0HealBundleReport(
                passed=False,
                status=ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN,
                repair_mode=ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN,
                healed_partitions=(),
                original_bundle_sha256="",
                reconstructed_bundle_sha256="",
                bit_exact_match=False,
                error_codes=anti_transplant.error_codes,
                errors=anti_transplant.errors,
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                persistent_write_release=PERSISTENT_WRITE_RELEASE,
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            ),
            None,
        )

    ordered_names = manifest.partition_order
    ordered_shards = [damaged_bundle.get(name) for name in ordered_names]
    shard_sizes = [manifest.partition_sizes[name] for name in ordered_names]
    expected_shas = [manifest.partition_sha256s[name] for name in ordered_names]

    heal_res, _, _ = heal_gf256_pq_shards(
        ordered_shards,
        p_parity,
        q_parity,
        shard_sizes=shard_sizes,
        stripe_bytes=manifest.stripe_bytes,
        expected_shard_sha256s=expected_shas,
        expected_p_sha256=manifest.p_parity_sha256,
        expected_q_sha256=manifest.q_parity_sha256,
        shard_names=ordered_names,
    )

    if not heal_res.passed or heal_res.reconstructed_shards is None:
        return (
            Tier0HealBundleReport(
                passed=False,
                status=heal_res.status,
                repair_mode=heal_res.repair_mode,
                healed_partitions=(),
                original_bundle_sha256=heal_res.original_bundle_sha256,
                reconstructed_bundle_sha256="",
                bit_exact_match=False,
                error_codes=heal_res.error_codes,
                errors=heal_res.errors,
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                persistent_write_release=PERSISTENT_WRITE_RELEASE,
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            ),
            None,
        )

    reconstructed_bundle = {
        name: shard for name, shard in zip(ordered_names, heal_res.reconstructed_shards)
    }

    post_errors: List[str] = []
    post_codes: List[str] = []
    for healed_name in heal_res.healed_names:
        part_rep = validate_tier0_partition(
            healed_name,
            reconstructed_bundle[healed_name],
            expected_size=manifest.partition_sizes[healed_name],
        )
        if not part_rep.passed:
            post_codes.extend(part_rep.error_codes)
            post_errors.extend(part_rep.errors)

    if require_ab_symmetry:
        for slot_a, slot_b in TIER0_AB_PAIRS:
            if len(reconstructed_bundle[slot_a]) != len(reconstructed_bundle[slot_b]) or (
                sha256(reconstructed_bundle[slot_a]).hexdigest() != sha256(reconstructed_bundle[slot_b]).hexdigest()
            ):
                post_codes.append(ERR_AB_SLOT_ASYMMETRY)
                post_errors.append(f"{ERR_AB_SLOT_ASYMMETRY}:{slot_a}/{slot_b}")

    if post_errors:
        return (
            Tier0HealBundleReport(
                passed=False,
                status=STATUS_FAIL_TIER0_BACKUP,
                repair_mode=heal_res.repair_mode,
                healed_partitions=heal_res.healed_names,
                original_bundle_sha256=heal_res.original_bundle_sha256,
                reconstructed_bundle_sha256=heal_res.reconstructed_bundle_sha256,
                bit_exact_match=False,
                error_codes=tuple(dict.fromkeys(post_codes)),
                errors=tuple(dict.fromkeys(post_errors)),
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                persistent_write_release=PERSISTENT_WRITE_RELEASE,
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
            ),
            None,
        )

    return (
        Tier0HealBundleReport(
            passed=True,
            status=STATUS_VERIFIED_TIER0_BACKUP,
            repair_mode=heal_res.repair_mode,
            healed_partitions=heal_res.healed_names,
            original_bundle_sha256=heal_res.original_bundle_sha256,
            reconstructed_bundle_sha256=heal_res.reconstructed_bundle_sha256,
            bit_exact_match=heal_res.bit_exact_match,
            error_codes=(),
            errors=(),
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        ),
        reconstructed_bundle,
    )


# ---------------------------------------------------------------------------
# 4. Deterministic Clean-Room Fixtures & Dual-Mode Suite Entrypoint
# ---------------------------------------------------------------------------


def _pseudo_random_bytes(seed_label: bytes, size: int) -> bytes:
    out = bytearray()
    seed = seed_label
    while len(out) < size:
        seed = sha256(seed).digest()
        out.extend(seed)
    return bytes(out[:size])


def _build_synthetic_elf_or_nbl(label: bytes, size: int = 4096) -> bytes:
    buf = bytearray(_pseudo_random_bytes(label, size))
    buf[0:4] = ELF_MAGIC
    buf[4] = 2  # ELFCLASS64
    buf[5] = 1  # ELFDATA2LSB
    buf[6] = 1  # EV_CURRENT
    struct.pack_into("<HHI", buf, 16, 2, 0xB7, 1)  # ET_EXEC, EM_AARCH64
    return bytes(buf)


def _build_synthetic_uboot(label: bytes, size: int = 4096) -> bytes:
    buf = bytearray(_pseudo_random_bytes(label, size))
    buf[0:4] = FDT_MAGIC
    struct.pack_into(">II", buf, 4, size, 0x28)
    return bytes(buf)


def _build_synthetic_boot_image(label: bytes, size: int = 8192) -> bytes:
    buf = bytearray(_pseudo_random_bytes(label, size))
    buf[0:8] = ANDROID_BOOT_MAGIC
    struct.pack_into("<III", buf, 8, 2048, 0x40080000, 2048)
    struct.pack_into("<I", buf, 36, 2048)
    return bytes(buf)


def _build_synthetic_c2pa_rq_lic(label: bytes, size: int = 2048) -> bytes:
    buf = bytearray(_pseudo_random_bytes(label, size))
    buf[0:4] = RQLC_MAGIC
    struct.pack_into("<II", buf, 4, 1, size)
    return bytes(buf)


def build_synthetic_tier0_backup_bundle(
    *,
    body_tag: str = "body_a",
    compact_p1: bool = False,
) -> Dict[str, bytes]:
    """Build a deterministic clean-room 11-partition FX3 Tier-0 backup bundle (zero proprietary keys)."""
    tag = body_tag.encode("utf-8")
    nbl = _build_synthetic_elf_or_nbl(b"fx3-nbl-" + tag, 4096)
    uboot = _build_synthetic_uboot(b"fx3-uboot-" + tag, 4096)
    boot = _build_synthetic_boot_image(b"fx3-boot-" + tag, 8192)
    p1 = build_synthetic_p1_vfat_image(total_clusters=8)
    if compact_p1:
        # Still full valid FAT12 BPB+FAT+root+data via build_synthetic_p1_vfat_image
        pass
    bk4 = build_synthetic_p2_bk4_image(total_size=4096)
    wbi2 = build_synthetic_p5_wbi2_image()
    cnflasha = _pseudo_random_bytes(b"fx3-cnflasha-xts-" + tag, 8192)
    c2pa = _build_synthetic_c2pa_rq_lic(b"fx3-c2pa-rq-lic-" + tag, 2048)
    return {
        "nbl_a": nbl,
        "nbl_b": nbl,
        "uboot_a": uboot,
        "uboot_b": uboot,
        "boot_a": boot,
        "boot_b": boot,
        "p1_vfat": p1,
        "bk4_nvram": bk4,
        "wbi2_hibdrv": wbi2,
        "cnflasha_spacc": cnflasha,
        "c2pa_rq_lic": c2pa,
    }


def run_tier0_backup_parity_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> Tier0BackupSuiteReport:
    """Execute full Phase 72 suite in `LOCAL_DONOR_O_RDONLY` or `CLEAN_ROOM_SYNTHETIC` mode."""
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    donor_p1_path = resolve_donor_path(DONOR_P1_205_RELPATH) if not clean_room else None
    donor_p5_path = resolve_donor_path(DONOR_P5_WBI2_RELPATH) if not clean_room else None
    has_donors = (
        donor_p1_path is not None
        and donor_p1_path.is_file()
        and donor_p5_path is not None
        and donor_p5_path.is_file()
    )

    errors: List[str] = []
    if has_donors and donor_p1_path is not None and donor_p5_path is not None:
        verification_mode = "LOCAL_DONOR_O_RDONLY"
        donor_p1_bytes = read_file(donor_p1_path, 64 * 1024 * 1024)
        donor_p5_bytes = read_file(donor_p5_path, 256 * 1024 * 1024)
        donor_p1_sha = sha256(donor_p1_bytes).hexdigest()
        donor_p5_sha = sha256(donor_p5_bytes).hexdigest()
        p1_rep = verify_p1_vfat_dump(donor_p1_bytes, check_fat_tree=True)
        p5_rep = verify_p5_wbi2_dump(donor_p5_bytes)
        if not p1_rep.valid:
            errors.extend(p1_rep.errors)
        if not p5_rep.valid:
            errors.extend(p5_rep.errors)
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
        donor_p1_sha = sha256(b"FX3_CLEAN_ROOM_PHASE72_P1_ANCHOR").hexdigest()
        donor_p5_sha = sha256(b"FX3_CLEAN_ROOM_PHASE72_P5_ANCHOR").hexdigest()

    body_a_bundle = build_synthetic_tier0_backup_bundle(body_tag="body_a")
    body_a_serial_hash = sha256(b"FX3-SYNTHETIC-BODY-A-0x91030080").hexdigest()

    bundle_val = validate_tier0_backup_bundle(body_a_bundle)
    if not bundle_val.passed:
        errors.extend(bundle_val.errors)

    manifest_a, parity_a = build_tier0_backup_manifest(
        body_a_bundle,
        camera_model="ILME-FX3",
        body_serial_hash=body_a_serial_hash,
    )

    identity_a = build_body_hardware_identity(
        camera_model="ILME-FX3",
        body_serial_hash=body_a_serial_hash,
        cnflasha_calibration_sha256=manifest_a.cnflasha_calibration_sha256,
        c2pa_rq_lic_sha256=manifest_a.c2pa_rq_lic_sha256,
    )
    same_body = verify_cross_body_anti_transplant(
        manifest_a,
        target_body_identity=identity_a,
        bundle_partitions=body_a_bundle,
    )
    if not same_body.allowed:
        errors.extend(same_body.errors)

    body_b_bundle = build_synthetic_tier0_backup_bundle(body_tag="body_b")
    identity_b = build_body_hardware_identity(
        camera_model="ILME-FX3",
        body_serial_hash=sha256(b"FX3-SYNTHETIC-BODY-B-0x91030080").hexdigest(),
        cnflasha_calibration_sha256=sha256(body_b_bundle["cnflasha_spacc"]).hexdigest(),
        c2pa_rq_lic_sha256=sha256(body_b_bundle["c2pa_rq_lic"]).hexdigest(),
    )
    cross_body = verify_cross_body_anti_transplant(
        manifest_a,
        target_body_identity=identity_b,
    )
    if cross_body.allowed or ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN not in cross_body.error_codes:
        errors.append("Cross-body transplant firewall failed to block Body-A -> Body-B")

    # Drill 1: 1-shard erasure (cnflasha_spacc lost)
    dmg_1: Dict[str, Optional[bytes]] = dict(body_a_bundle)
    dmg_1["cnflasha_spacc"] = None
    heal_1, recon_1 = heal_tier0_backup_bundle(
        dmg_1,
        manifest_a,
        p_parity=parity_a.p_parity,
        q_parity=parity_a.q_parity,
        target_body_identity=identity_a,
    )
    if not heal_1.passed or recon_1 is None or recon_1["cnflasha_spacc"] != body_a_bundle["cnflasha_spacc"]:
        errors.append("1-shard erasure healing failed")

    # Drill 2: 2-shard erasure (nbl_a + wbi2_hibdrv lost)
    dmg_2: Dict[str, Optional[bytes]] = dict(body_a_bundle)
    dmg_2["nbl_a"] = None
    dmg_2["wbi2_hibdrv"] = None
    heal_2, recon_2 = heal_tier0_backup_bundle(
        dmg_2,
        manifest_a,
        p_parity=parity_a.p_parity,
        q_parity=parity_a.q_parity,
        target_body_identity=identity_a,
    )
    if (
        not heal_2.passed
        or recon_2 is None
        or recon_2["nbl_a"] != body_a_bundle["nbl_a"]
        or recon_2["wbi2_hibdrv"] != body_a_bundle["wbi2_hibdrv"]
    ):
        errors.append("2-shard erasure healing failed")

    # Drill 3: 1-shard silent bit-rot (p1_vfat byte flipped)
    dmg_rot: Dict[str, Optional[bytes]] = dict(body_a_bundle)
    rot_buf = bytearray(body_a_bundle["p1_vfat"])
    rot_buf[128] ^= 0xA5
    rot_buf[1024] ^= 0x5A
    dmg_rot["p1_vfat"] = bytes(rot_buf)
    heal_rot, recon_rot = heal_tier0_backup_bundle(
        dmg_rot,
        manifest_a,
        p_parity=parity_a.p_parity,
        q_parity=parity_a.q_parity,
        target_body_identity=identity_a,
    )
    if not heal_rot.passed or recon_rot is None or recon_rot["p1_vfat"] != body_a_bundle["p1_vfat"]:
        errors.append("1-shard silent bit-rot healing failed")

    # Drill 4: >= 3 simultaneous shard losses -> fail closed UNRECOVERABLE_QUORUM_LOSS
    dmg_3: Dict[str, Optional[bytes]] = dict(body_a_bundle)
    dmg_3["nbl_a"] = None
    dmg_3["boot_b"] = None
    dmg_3["bk4_nvram"] = None
    reject_3, recon_3 = heal_tier0_backup_bundle(
        dmg_3,
        manifest_a,
        p_parity=parity_a.p_parity,
        q_parity=parity_a.q_parity,
        target_body_identity=identity_a,
    )
    if reject_3.passed or recon_3 is not None or ERR_UNRECOVERABLE_QUORUM_LOSS not in reject_3.error_codes:
        errors.append("3-shard loss did not fail closed with UNRECOVERABLE_QUORUM_LOSS")

    all_passed = (
        len(errors) == 0
        and bundle_val.passed
        and same_body.allowed
        and (not cross_body.allowed)
        and heal_1.passed
        and heal_2.passed
        and heal_rot.passed
        and (not reject_3.passed)
        and (PERSISTENT_EMMC_WRITES_AUTHORIZED is False)
        and (PERSISTENT_WRITE_RELEASE is False)
        and (ALLOW_BOOT_PARTITION_TARGETING is False)
        and (ALLOW_DESTRUCTIVE_FASTBOOT is False)
        and (PHYSICAL_DEVICE_WRITES == 0)
    )
    return Tier0BackupSuiteReport(
        schema=TIER0_BACKUP_GUARD_SCHEMA,
        version=TIER0_BACKUP_GUARD_VERSION,
        verification_mode=verification_mode,
        all_passed=all_passed,
        status=STATUS_VERIFIED_TIER0_BACKUP if all_passed else STATUS_FAIL_TIER0_BACKUP,
        donor_p1_sha256=donor_p1_sha,
        donor_p5_wbi2_sha256=donor_p5_sha,
        bundle_validation=bundle_val,
        manifest=manifest_a,
        anti_transplant_same_body=same_body,
        anti_transplant_cross_body_blocked=cross_body,
        heal_1_erasure=heal_1,
        heal_2_erasures=heal_2,
        heal_1_silent_bitrot=heal_rot,
        reject_3_losses=reject_3,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        errors=tuple(errors),
    )
