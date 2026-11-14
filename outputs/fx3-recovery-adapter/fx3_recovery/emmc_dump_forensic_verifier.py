"""Tier-4 Offline Read-Only eMMC Dump Forensic Verifier (`O_RDONLY`-only).

Validates Sony CXD90057 / CXD90058 (`ILME-FX3` v7.02 / `ILME-FX6` v6.01) eMMC
partition dumps, ISP captures, `EXT_CSD` registers, and recovery manifests before
any offline rehearsal or Phase H0 read-only capture is trusted:

1. Stuck-Bus / Truncation / Bad-Read Detector:
   - Detects stuck `0x00` / `0xFF` bus pages and contiguous pull-up/pull-down runs
   - Detects truncated reads and unaligned sector sizes
   - Detects Shannon byte-entropy collapses on compressed (`SquashFS`/`cramfs`) or
     AES-XTS-256 encrypted (`cnflasha*`) dumps
   - Enforces two-pass `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` SHA-256 read stability
2. Sony Partition Magic & Geometry Verifier:
   - `sector0`: `'8246'` `'2.00'` 30-entry Sony partition table + overlap/profile checks
   - `p1` (`nflasha1`): VFAT FAT12 BPB geometry (`0x55 0xAA`, mirror FATs, cluster bounds)
   - `p2` (`nflasha10` / `Backup.bin`): `'BK4\\0'` (`0xAAAAAAAA`) NVRAM header + 32-bit
     byte-sum checksum + FX3 `PRODUCT_MODEL` (`0x91030080` / `ALCIN_UUD`) immutability
   - `p5` (`nflasha5`): `'WBI2'` 88-byte hibernation header + 64-byte section descriptor
     XOR (`0x0f0f0f0f`) & physical/virtual alignment checks + invalidated-magic detection
   - `p8` (`nflasha8` / `cp`): FAT12 BPB (`reserved=32`, `/cpapp-b.bin`, `/tomco.txt`)
     and ARMv7-R Cortex-R5 `cpapp-b.bin` reset vector (`0x00108000`) + `[TOMCO]` markers
   - `ext_csd`: `EXT_CSD[179]` (`PART_CONFIG` `0xB3`) boot partition sanity,
     `BOOT_BUS_CONDITIONS` (`0xB1`), `RST_n` (`0xA2`), `BOOT_SIZE_MULT` (`0xE2`), wear EOL
3. Boot-Chain Immutability Firewall:
   - Hard-locks `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` and
     `ALLOW_BOOT_PARTITION_TARGETING = False`
   - Rejects any workflow or image manifest attempting to write/erase/patch/lock
     `BOOT0`, `BOOT1`, `RPMB`, `nflashaB0/B1`, `nflasha1..nflasha8`, `sector0`,
     `loader_nor`, `LdrBkup`, or `CMD42` (`LOCK` / `FORCE_ERASE`).

Safety & Hygiene:
- Never prints raw binary `bytes` reprs; all digests/samples use `.hex()`.
- Strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`; zero proprietary keys embedded.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import stat
import struct
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .fat import FatP1, MAX_P1
from .files import is_forced_clean_room, local_path, require

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

FORENSIC_VERIFIER_SCHEMA = "fx3-tier4-emmc-forensic-verifier-v1"
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

FX3_PRODUCT_MODEL_ID: int = 0x91030080
FX3_PRODUCT_MODEL_ENUM: int = 4  # PRODUCT_MODEL_ALCIN_UUD
FX3A_PRODUCT_MODEL_ID: int = 0x91030082
A7IV_PRODUCT_MODEL_ID: int = 0x01030081

SONY_PTBL_MAGIC: bytes = b"8246"
SONY_PTBL_VERSION: bytes = b"2.00"
SONY_PTBL_ENTRY_COUNT: int = 30
SONY_PTBL_SIZE: int = 512

BK4_SYNC_MARKER: int = 0xAAAAAAAA
BK4_MAGIC: bytes = b"BK4\x00"
BK4_HEADER_SIZE: int = 256

WBI2_MAGIC: bytes = b"WBI2"
WBI2_INVALIDATED_MAGICS: Tuple[bytes, ...] = (b"wbi2", b"WBI3", b"WBI0")
WBI2_HEADER_SIZE: int = 88
WBI2_SECTION_TABLE_OFFSET_MIN: int = 512
WBI2_XOR_MASK: int = 0x0F0F0F0F

CPAPP_ARM_RESET_WORDS: Tuple[int, ...] = (0xE59F1004, 0xE2811004, 0xE1A0F001, 0x0010800C)
CPAPP_LOAD_BASE: int = 0x00108000

DEFAULT_PAGE_SIZE: int = 4096
SECTOR_SIZE: int = 512
MAX_FORENSIC_IMAGE_BYTES: int = 512 * 1024 * 1024  # 512 MiB cap
STREAM_CHUNK_BYTES: int = 1024 * 1024

EXT_CSD_SIZE: int = 512
EXT_CSD_RST_N_ENABLE_IDX: int = 162  # 0xA2
EXT_CSD_RPMB_SIZE_MULT_IDX: int = 168  # 0xA8
EXT_CSD_BOOT_BUS_COND_IDX: int = 177  # 0xB1
EXT_CSD_PART_CONFIG_IDX: int = 179  # 0xB3
EXT_CSD_REV_IDX: int = 192  # 0xC0
EXT_CSD_SEC_COUNT_IDX: int = 212  # 0xD4 (4 bytes LE)
EXT_CSD_BOOT_SIZE_MULT_IDX: int = 226  # 0xE2
EXT_CSD_PRE_EOL_INFO_IDX: int = 267  # 0x10B
EXT_CSD_LIFE_TIME_A_IDX: int = 268  # 0x10C
EXT_CSD_LIFE_TIME_B_IDX: int = 269  # 0x10D

# Canonical FX3 7.02 key partitions in 512-byte sectors (for Sector 0 validation)
FX3_KEY_PARTITIONS: Dict[int, Tuple[int, int, int, int, str]] = {
    1: (0x00000080, 0x0000BF80, 4, 1, "p1:/updater"),
    2: (0x0000C000, 0x0000A000, 4, 1, "p2:/setting"),
    3: (0x00016000, 0x00025800, 5, 1, "p3:/system"),
    5: (0x00042000, 0x00096000, 6, 1, "p5:/wbi"),
    6: (0x000D8000, 0x0000C800, 4, 1, "p6:/tmp/jiritsu"),
    7: (0x000E4800, 0x00019000, 5, 1, "p7:/rootfs"),
    8: (0x000FD800, 0x00032000, 5, 1, "p8:/cp"),
    12: (0x0020C000, 0x00014000, 5, 1, "p12:/cert"),
    15: (0x00222000, 0x000FA000, 5, 1, "p15:/usr"),
    18: (0x0031C000, 0x0000A000, 4, 1, "p18:/lens"),
}

IMMUTABLE_BOOT_PARTITION_TOKENS: Tuple[str, ...] = (
    "boot0",
    "boot1",
    "rpmb",
    "nflashab0",
    "nflashab1",
    "mmcblk0boot0",
    "mmcblk0boot1",
    "mmcblk0rpmb",
    "sector0",
    "ptbl",
    "mbr",
    "ldr_bkup",
    "ldrbkup",
    "loader_nor",
    "ext_csd",
    "part_config",
    *(f"nflasha{i}" for i in range(1, 9)),
    *(f"cnflasha{i}" for i in range(1, 9)),
    *(f"pnflasha{i}" for i in range(1, 9)),
    *(f"p{i}" for i in range(1, 9)),
)

READONLY_ALLOWED_OPS: Tuple[str, ...] = (
    "read",
    "read_verify",
    "inspect",
    "audit",
    "verify",
    "hash",
    "dump_readonly",
)

MUTATING_FORBIDDEN_OPS: Tuple[str, ...] = (
    "write",
    "flash",
    "erase",
    "format",
    "patch",
    "modify",
    "dd",
    "poke",
    "set_part_config",
    "cmd42_lock",
    "cmd42_set_pwd",
    "cmd42_force_erase",
    "unlock_write",
    "edisx",
)

VALID_ROLES: Tuple[str, ...] = (
    "sector0",
    "p1",
    "p2",
    "p5",
    "p8",
    "ext_csd",
    "cnflasha",
    "generic",
)


class ForensicVerificationError(ValueError):
    """Fail-closed Tier-4 eMMC forensic verification or firewall rejection."""


# ---------------------------------------------------------------------------
# Structured Report Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BusAndEntropyReport:
    total_bytes: int
    page_size: int
    total_pages: int
    all_zero_pages: int
    all_ff_pages: int
    zero_page_ratio: float
    ff_page_ratio: float
    max_contiguous_zero_pages: int
    max_contiguous_ff_pages: int
    shannon_entropy_bits: float
    min_window_entropy_bits: float
    truncation_detected: bool
    stuck_bus_detected: bool
    entropy_collapse_detected: bool
    constant_fill_byte: Optional[int]
    anomalies: Tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class TwoPassStabilityReport:
    source_label: str
    byte_length: int
    pass1_sha256: str
    pass2_sha256: str
    stable: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ExtCsdAuditReport:
    valid: bool
    part_config_raw: int
    boot_ack: int
    boot_partition_enable: int
    boot_partition_name: str
    partition_access: int
    partition_access_name: str
    boot_bus_conditions: int
    rst_n_enable: int
    boot_size_bytes: int
    rpmb_size_bytes: int
    pre_eol_info: int
    life_time_a: int
    life_time_b: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]


@dataclass(frozen=True)
class PartitionMagicReport:
    role: str
    valid: bool
    magic_ok: bool
    geometry_ok: bool
    fx3_immutability_ok: bool
    details: Dict[str, object]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]


@dataclass(frozen=True)
class BootChainFirewallDecision:
    allowed: bool
    persistent_emmc_writes_authorized: bool
    allow_boot_partition_targeting: bool
    blocked_targets: Tuple[str, ...]
    blocked_operations: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class EmmcDumpForensicReport:
    schema: str
    role: str
    source_mode: str
    persistent_emmc_writes_authorized: bool
    allow_boot_partition_targeting: bool
    passed: bool
    sha256: str
    two_pass_stability: Optional[TwoPassStabilityReport]
    bus_and_entropy: BusAndEntropyReport
    partition_magic: PartitionMagicReport
    ext_csd: Optional[ExtCsdAuditReport]
    boot_chain_firewall: BootChainFirewallDecision
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Shannon Entropy & Stuck-Bus / Truncation Analyzer
# ---------------------------------------------------------------------------


def compute_shannon_entropy(data: bytes) -> float:
    """Compute exact Shannon byte entropy (bits/byte in [0.0, 8.0]) using C-speed count."""
    n = len(data)
    if n == 0:
        return 0.0
    entropy = 0.0
    for byte_val in range(256):
        cnt = data.count(byte_val)
        if cnt:
            p = cnt / n
            entropy -= p * math.log2(p)
    return round(entropy, 4)


def _sampled_entropy(data: bytes, sample_cap: int = 4 * 1024 * 1024) -> Tuple[float, float]:
    """Compute overall (sampled if > 4 MiB) and minimum 64 KiB window Shannon entropy."""
    n = len(data)
    if n == 0:
        return 0.0, 0.0

    if n <= sample_cap:
        overall = compute_shannon_entropy(data)
    else:
        win = 1024 * 1024
        offsets = (0, n // 4, n // 2, (3 * n) // 4, max(0, n - win))
        sample = b"".join(data[o : o + win] for o in offsets)
        overall = compute_shannon_entropy(sample)

    window_size = 65536
    if n < window_size:
        min_win = compute_shannon_entropy(data)
    else:
        # Sample up to 16 evenly spaced 64 KiB windows to stay deterministic & < 20ms
        max_windows = 16
        step = max(window_size, ((n - window_size) // max(1, max_windows - 1)))
        min_win = 8.0
        pos = 0
        checked = 0
        while pos + window_size <= n and checked < max_windows:
            ent = compute_shannon_entropy(data[pos : pos + window_size])
            if ent < min_win:
                min_win = ent
            pos += step
            checked += 1
        tail_ent = compute_shannon_entropy(data[n - window_size : n])
        if tail_ent < min_win:
            min_win = tail_ent

    return overall, round(min_win, 4)


def analyze_bus_and_entropy(
    data: bytes,
    *,
    expected_size: Optional[int] = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    role: str = "generic",
    expect_encrypted: bool = False,
    expect_compressed: bool = False,
    min_entropy_bits: Optional[float] = None,
    max_zero_ratio: Optional[float] = None,
    max_ff_ratio: Optional[float] = None,
    max_contig_ff_pages: int = 16,
    require_sector_aligned: bool = True,
) -> BusAndEntropyReport:
    """Detect stuck-0x00/0xFF bus pages, truncations, and Shannon byte-entropy collapses."""
    require(page_size >= 512 and page_size % 512 == 0, "page_size must be a 512B-aligned integer >= 512")
    n = len(data)
    anomalies: List[str] = []
    truncation = False
    stuck_bus = False
    entropy_collapse = False

    if n == 0:
        return BusAndEntropyReport(
            total_bytes=0,
            page_size=page_size,
            total_pages=0,
            all_zero_pages=0,
            all_ff_pages=0,
            zero_page_ratio=1.0,
            ff_page_ratio=0.0,
            max_contiguous_zero_pages=0,
            max_contiguous_ff_pages=0,
            shannon_entropy_bits=0.0,
            min_window_entropy_bits=0.0,
            truncation_detected=True,
            stuck_bus_detected=True,
            entropy_collapse_detected=True,
            constant_fill_byte=None,
            anomalies=("TRUNCATED_EMPTY_DUMP",),
            passed=False,
        )

    if expected_size is not None and n != expected_size:
        truncation = True
        anomalies.append(f"TRUNCATED_OR_SIZE_MISMATCH:got={n},expected={expected_size}")

    if require_sector_aligned and (n % SECTOR_SIZE != 0):
        truncation = True
        anomalies.append(f"UNALIGNED_SECTOR_READ:bytes={n},mod512={n % SECTOR_SIZE}")

    # Constant fill check (e.g. entire dump stuck at 0x00, 0xFF, 0xAA, 0x55)
    first_byte = data[0]
    constant_fill: Optional[int] = None
    if data.count(first_byte) == n:
        constant_fill = first_byte
        stuck_bus = True
        if first_byte == 0x00:
            anomalies.append("ALL_ZERO_DUMP")
        elif first_byte == 0xFF:
            anomalies.append("ALL_FF_DUMP")
        else:
            anomalies.append(f"CONSTANT_FILL_ANOMALY:0x{first_byte:02x}")

    eff_page = page_size if n >= page_size else SECTOR_SIZE
    total_pages = n // eff_page
    zero_pat = b"\x00" * eff_page
    ff_pat = b"\xff" * eff_page

    all_zero_pages = 0
    all_ff_pages = 0
    cur_z = 0
    max_z = 0
    cur_f = 0
    max_f = 0

    mv = memoryview(data)
    for idx in range(total_pages):
        off = idx * eff_page
        blk = mv[off : off + eff_page]
        if blk == zero_pat:
            all_zero_pages += 1
            cur_z += 1
            if cur_z > max_z:
                max_z = cur_z
            cur_f = 0
        elif blk == ff_pat:
            all_ff_pages += 1
            cur_f += 1
            if cur_f > max_f:
                max_f = cur_f
            cur_z = 0
        else:
            cur_z = 0
            cur_f = 0

    zero_ratio = round(all_zero_pages / max(1, total_pages), 4)
    ff_ratio = round(all_ff_pages / max(1, total_pages), 4)

    eff_max_zero = 0.85 if max_zero_ratio is None else max_zero_ratio
    eff_max_ff = 0.25 if max_ff_ratio is None else max_ff_ratio

    if expect_encrypted:
        # AES-XTS-256 ciphertext should never contain full 4 KiB 0x00 or 0xFF pages
        if all_zero_pages > 0 or all_ff_pages > 0:
            stuck_bus = True
            anomalies.append(
                f"STUCK_BUS_IN_ENCRYPTED_IMAGE:zero_pages={all_zero_pages},ff_pages={all_ff_pages}"
            )
    else:
        if constant_fill is None:
            if ff_ratio > eff_max_ff or max_f >= max_contig_ff_pages:
                stuck_bus = True
                anomalies.append(
                    f"STUCK_BUS_0xFF_RUN:ff_pages={all_ff_pages},max_contig_ff={max_f},ratio={ff_ratio}"
                )
            if zero_ratio > eff_max_zero:
                stuck_bus = True
                anomalies.append(
                    f"STUCK_BUS_0x00_EXCESS:zero_pages={all_zero_pages},max_contig_zero={max_z},ratio={zero_ratio}"
                )

    overall_ent, min_win_ent = _sampled_entropy(data)

    if min_entropy_bits is not None:
        ent_floor = min_entropy_bits
    elif expect_encrypted or role == "cnflasha":
        ent_floor = 7.75
    elif expect_compressed:
        ent_floor = 5.0
    elif role in ("p1", "p5"):
        ent_floor = 4.0
    elif role == "p8":
        ent_floor = 3.0
    elif role == "ext_csd":
        ent_floor = 0.05
    elif role == "sector0":
        ent_floor = 0.5
    else:
        ent_floor = 1.5

    if overall_ent < ent_floor:
        entropy_collapse = True
        anomalies.append(
            f"ENTROPY_COLLAPSE:shannon={overall_ent:.4f},floor={ent_floor:.4f},role={role}"
        )

    if (expect_encrypted or role == "cnflasha") and min_win_ent < 6.5:
        entropy_collapse = True
        anomalies.append(
            f"ENCRYPTED_WINDOW_ENTROPY_COLLAPSE:min_window={min_win_ent:.4f},floor=6.5000"
        )

    passed = (not truncation) and (not stuck_bus) and (not entropy_collapse) and (len(anomalies) == 0)
    return BusAndEntropyReport(
        total_bytes=n,
        page_size=eff_page,
        total_pages=total_pages,
        all_zero_pages=all_zero_pages,
        all_ff_pages=all_ff_pages,
        zero_page_ratio=zero_ratio,
        ff_page_ratio=ff_ratio,
        max_contiguous_zero_pages=max_z,
        max_contiguous_ff_pages=max_f,
        shannon_entropy_bits=overall_ent,
        min_window_entropy_bits=min_win_ent,
        truncation_detected=truncation,
        stuck_bus_detected=stuck_bus,
        entropy_collapse_detected=entropy_collapse,
        constant_fill_byte=constant_fill,
        anomalies=tuple(anomalies),
        passed=passed,
    )


# ---------------------------------------------------------------------------
# Two-Pass O_RDONLY SHA-256 Stability Reader
# ---------------------------------------------------------------------------


def _stat_tuple(st: os.stat_result) -> Tuple[int, ...]:
    return (
        st.st_dev,
        st.st_ino,
        st.st_size,
        st.st_mtime_ns,
        st.st_ctime_ns,
        st.st_mode,
        st.st_nlink,
    )


def _read_fd_pass(fd: int, expected_size: int) -> Tuple[str, bytes]:
    os.lseek(fd, 0, os.SEEK_SET)
    h = sha256()
    buf = bytearray()
    remaining = expected_size + 1
    while remaining > 0:
        chunk = os.read(fd, min(STREAM_CHUNK_BYTES, remaining))
        if not chunk:
            break
        h.update(chunk)
        buf.extend(chunk)
        remaining -= len(chunk)
    return h.hexdigest(), bytes(buf)


def read_two_pass_sha256_readonly(
    path: Union[Path, str],
    *,
    max_bytes: int = MAX_FORENSIC_IMAGE_BYTES,
) -> Tuple[TwoPassStabilityReport, Optional[bytes]]:
    """Open `path` strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`, hash twice, and verify stability."""
    p = local_path(path, allow_donor_roots=True)
    require(hasattr(os, "O_NOFOLLOW"), "POSIX O_NOFOLLOW is required")
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    errors: List[str] = []
    try:
        st0 = os.fstat(fd)
        require(stat.S_ISREG(st0.st_mode) and st0.st_nlink == 1, "single-link regular file required")
        require(0 <= st0.st_size <= max_bytes, f"file size {st0.st_size} exceeds limit {max_bytes}")

        sha1, data1 = _read_fd_pass(fd, st0.st_size)
        st1 = os.fstat(fd)
        sha2, data2 = _read_fd_pass(fd, st0.st_size)
        st2 = os.fstat(fd)

        if _stat_tuple(st0) != _stat_tuple(st1) or _stat_tuple(st0) != _stat_tuple(st2):
            errors.append("FILE_METADATA_DRIFT_DURING_TWO_PASS_READ")
        if len(data1) != st0.st_size or len(data2) != st0.st_size:
            errors.append(
                f"READ_SIZE_DRIFT:stat={st0.st_size},pass1={len(data1)},pass2={len(data2)}"
            )
        if sha1 != sha2 or data1 != data2:
            errors.append(f"TWO_PASS_SHA256_MISMATCH:pass1={sha1},pass2={sha2}")

        stable = len(errors) == 0
        rep = TwoPassStabilityReport(
            source_label=p.name,
            byte_length=len(data1),
            pass1_sha256=sha1,
            pass2_sha256=sha2,
            stable=stable,
            errors=tuple(errors),
        )
        return rep, (data1 if stable else None)
    finally:
        os.close(fd)


def verify_two_pass_provider_stability(
    provider: Callable[[int], bytes],
    *,
    source_label: str = "provider",
    max_bytes: int = MAX_FORENSIC_IMAGE_BYTES,
) -> Tuple[TwoPassStabilityReport, Optional[bytes]]:
    """Verify two-pass SHA-256 stability over a caller-supplied read callback (for flaky-bus testing)."""
    d1 = provider(1)
    d2 = provider(2)
    if len(d1) > max_bytes or len(d2) > max_bytes:
        raise ForensicVerificationError("provider output exceeds max_bytes")
    sha1 = sha256(d1).hexdigest()
    sha2 = sha256(d2).hexdigest()
    errors: List[str] = []
    if len(d1) != len(d2):
        errors.append(f"TWO_PASS_LENGTH_MISMATCH:pass1={len(d1)},pass2={len(d2)}")
    if sha1 != sha2:
        errors.append(f"TWO_PASS_SHA256_MISMATCH:pass1={sha1},pass2={sha2}")
    stable = len(errors) == 0
    return (
        TwoPassStabilityReport(
            source_label=source_label,
            byte_length=len(d1),
            pass1_sha256=sha1,
            pass2_sha256=sha2,
            stable=stable,
            errors=tuple(errors),
        ),
        d1 if stable else None,
    )


# ---------------------------------------------------------------------------
# Sony Partition Magic & Geometry Verifiers
# ---------------------------------------------------------------------------


def verify_sector0_dump(data: bytes) -> PartitionMagicReport:
    """Validate 512-byte Sony eMMC UDA Sector 0 ('8246' '2.00' 30-entry partition table)."""
    errors: List[str] = []
    warnings: List[str] = []

    if len(data) < SONY_PTBL_SIZE:
        return PartitionMagicReport(
            role="sector0",
            valid=False,
            magic_ok=False,
            geometry_ok=False,
            fx3_immutability_ok=False,
            details={"bytes": len(data)},
            errors=(f"SECTOR0_TRUNCATED:got={len(data)},expected>={SONY_PTBL_SIZE}",),
            warnings=(),
        )

    sec0 = data[:SONY_PTBL_SIZE]
    magic = sec0[0:4]
    version = sec0[4:8]
    count = struct.unpack_from("<I", sec0, 8)[0]
    padding = sec0[12:32]

    magic_ok = (magic == SONY_PTBL_MAGIC) and (version == SONY_PTBL_VERSION)
    if magic != SONY_PTBL_MAGIC:
        errors.append(f"SECTOR0_BAD_MAGIC:{magic.hex()}")
    if version != SONY_PTBL_VERSION:
        errors.append(f"SECTOR0_BAD_VERSION:{version.hex()}")
    if count != SONY_PTBL_ENTRY_COUNT:
        errors.append(f"SECTOR0_BAD_ENTRY_COUNT:{count}")
    if any(b != 0 for b in padding):
        warnings.append("SECTOR0_NONZERO_PADDING_0x0C_0x1F")

    entries: List[Tuple[int, int, int, int, int]] = []
    for idx in range(SONY_PTBL_ENTRY_COUNT):
        off = 32 + idx * 16
        start_s, size_s, ptype, flag = struct.unpack_from("<IIII", sec0, off)
        entries.append((idx + 1, start_s, size_s, ptype, flag))

    active_spans: List[Tuple[int, int, int]] = []
    has_overlaps = False
    for pid, start_s, size_s, _ptype, _flag in entries:
        if size_s == 0:
            continue
        if start_s < 0x80:
            errors.append(f"SECTOR0_COLLISION_BELOW_0x80:p{pid}@0x{start_s:x}")
            has_overlaps = True
        end_s = start_s + size_s
        for ps, pe, pprev in active_spans:
            if not (end_s <= ps or start_s >= pe):
                errors.append(f"SECTOR0_PARTITION_OVERLAP:p{pid}[0x{start_s:x}:0x{end_s:x}]_vs_p{pprev}[0x{ps:x}:0x{pe:x}]")
                has_overlaps = True
        active_spans.append((start_s, end_s, pid))

    by_id = {e[0]: e for e in entries}
    p1, p2, p6, p7, p12, p18, p20, p21 = (by_id[i] for i in (1, 2, 6, 7, 12, 18, 20, 21))

    is_partinf_cal = (
        (p1[1], p1[2], p1[3]) == (0x00000080, 0x0000BF80, 5)
        and (p2[1], p2[2], p2[3]) == (0x0000C000, 0x0000A000, 5)
        and (p6[1], p6[2], p6[3]) == (0x000D7800, 0x0000C800, 5)
    )

    cal_ok = True
    if not is_partinf_cal:
        for pid in (1, 2, 6):
            exp_start, exp_size, exp_type, _flag, label = FX3_KEY_PARTITIONS[pid]
            _, act_start, act_size, act_type, _ = by_id[pid]
            if (act_start, act_size, act_type) != (exp_start, exp_size, exp_type):
                cal_ok = False
                errors.append(
                    f"SECTOR0_CALIBRATION_MISMATCH:{label}:start=0x{act_start:x},size=0x{act_size:x},type={act_type}"
                )

    profile = "CUSTOM_OR_UNKNOWN"
    fx3_immutability_ok = True
    if (
        not is_partinf_cal
        and p7[2] == 0x00019000
        and p12[2] == 0x00014000
        and p18[1] == 0x0031C000
        and p18[2] == 0x0000A000
        and p20[2] == 0
        and p21[2] == 0
    ):
        profile = "FX3_702"
    elif (
        not is_partinf_cal
        and p7[2] == 0
        and p12[2] == 0x0000A000
        and p18[1] == 0x00312000
        and p18[2] == 0x0000A000
        and p20[2] == 0x00032000
        and p21[2] == 0x00016400
    ):
        profile = "FX6_601"
        fx3_immutability_ok = False
        errors.append("FX6_SECTOR0_P18_SHIFT_HAZARD:p18_at_0x312000_will_orphan_fx3_lensfile")
    elif (
        is_partinf_cal
        and p12[2] == 0x00014000
        and p18[1] == 0x0031C000
        and p18[2] == 0x0000A000
    ):
        profile = "FX3_PARTINF_205"
    elif p18[2] != 0x0000A000 or p18[1] not in (0x0031C000, 0x00312000):
        cal_ok = False
        errors.append(f"SECTOR0_P18_LENS_GEOMETRY_INVALID:start=0x{p18[1]:x},size=0x{p18[2]:x}")

    geometry_ok = (count == SONY_PTBL_ENTRY_COUNT) and (not has_overlaps) and cal_ok
    valid = magic_ok and geometry_ok and fx3_immutability_ok and (len(errors) == 0)
    return PartitionMagicReport(
        role="sector0",
        valid=valid,
        magic_ok=magic_ok,
        geometry_ok=geometry_ok,
        fx3_immutability_ok=fx3_immutability_ok,
        details={
            "magic_hex": magic.hex(),
            "version_hex": version.hex(),
            "entry_count": count,
            "layout_profile": profile,
            "active_partitions": sum(1 for e in entries if e[2] > 0),
            "p18_start_sector": hex(p18[1]),
        },
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_p1_vfat_dump(data: bytes, *, check_fat_tree: bool = True) -> PartitionMagicReport:
    """Validate `p1` (`nflasha1`) VFAT FAT12 BPB geometry and optional cluster chain integrity."""
    errors: List[str] = []
    warnings: List[str] = []
    if len(data) < 512:
        return PartitionMagicReport(
            role="p1",
            valid=False,
            magic_ok=False,
            geometry_ok=False,
            fx3_immutability_ok=True,
            details={"bytes": len(data)},
            errors=(f"P1_TRUNCATED_BEFORE_BOOT_SECTOR:bytes={len(data)}",),
            warnings=(),
        )
    if len(data) > MAX_P1:
        return PartitionMagicReport(
            role="p1",
            valid=False,
            magic_ok=False,
            geometry_ok=False,
            fx3_immutability_ok=True,
            details={"bytes": len(data), "max_p1": MAX_P1},
            errors=(f"P1_EXCEEDS_MAX_PARTITION_BYTES:{len(data)}>{MAX_P1}",),
            warnings=(),
        )

    boot_sig = data[510:512]
    magic_ok = boot_sig == b"\x55\xaa"
    if not magic_ok:
        errors.append(f"P1_BAD_BOOT_SIGNATURE:{boot_sig.hex()}")

    sector = struct.unpack_from("<H", data, 11)[0]
    cluster_sectors = data[13]
    reserved = struct.unpack_from("<H", data, 14)[0]
    copies = data[16]
    entries = struct.unpack_from("<H", data, 17)[0]
    total = struct.unpack_from("<H", data, 19)[0] or struct.unpack_from("<I", data, 32)[0]
    fat_sectors = struct.unpack_from("<H", data, 22)[0]

    geometry_ok = False
    details: Dict[str, object] = {
        "boot_sig_hex": boot_sig.hex(),
        "bytes_per_sector": sector,
        "sectors_per_cluster": cluster_sectors,
        "reserved_sectors": reserved,
        "fat_copies": copies,
        "root_entries": entries,
        "fat_sectors": fat_sectors,
        "declared_total_sectors": total,
        "declared_total_bytes": total * 512,
        "actual_bytes": len(data),
    }

    if magic_ok:
        try:
            if check_fat_tree:
                fat = FatP1(data)
                details["cluster_count"] = fat.clusters
                details["file_count"] = len(fat.files)
                geometry_ok = True
            else:
                require(
                    sector == 512
                    and cluster_sectors == 32
                    and reserved == 1
                    and copies == 2
                    and entries == 512
                    and fat_sectors == 32,
                    "unsupported FX3 P1 FAT geometry",
                )
                start_bytes = (reserved + copies * fat_sectors) * 512 + entries * 32
                require(start_bytes <= total * 512 <= len(data), "FAT declared size exceeds input")
                clusters = (total * 512 - start_bytes) // (512 * cluster_sectors)
                require(0 < clusters < 4085, "unsupported FAT12 cluster count")
                fat_size = fat_sectors * 512
                fat1 = data[reserved * 512 : reserved * 512 + fat_size]
                fat2 = data[reserved * 512 + fat_size : reserved * 512 + 2 * fat_size]
                require(fat1 == fat2, "FAT copies differ")
                details["cluster_count"] = clusters
                geometry_ok = True
        except Exception as exc:
            errors.append(f"P1_FAT_VALIDATION_FAILED:{exc}")

    valid = magic_ok and geometry_ok and (len(errors) == 0)
    return PartitionMagicReport(
        role="p1",
        valid=valid,
        magic_ok=magic_ok,
        geometry_ok=geometry_ok,
        fx3_immutability_ok=True,
        details=details,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _scan_bk4_properties_for_model_id(
    payload: bytes,
    prop_count: int,
    expected_model_id: int,
) -> Tuple[Optional[int], Optional[int], List[str]]:
    """Parse BK4 TLV properties `<IH` (prop_id, len) and enforce FX3 PRODUCT_MODEL immutability."""
    errors: List[str] = []
    observed_model_id: Optional[int] = None
    observed_enum: Optional[int] = None
    cursor = 0
    parsed = 0
    while cursor + 6 <= len(payload) and parsed < prop_count:
        prop_id, val_len = struct.unpack_from("<IH", payload, cursor)
        cursor += 6
        if cursor + val_len > len(payload):
            errors.append(f"BK4_TLV_TRUNCATED:prop_id=0x{prop_id:08x},len={val_len}")
            break
        val = payload[cursor : cursor + val_len]
        cursor += val_len
        parsed += 1
        # Check explicit PRODUCT_MODEL property tags (0x00010000 / 0x02CF0000 / 0x02CF0001)
        if prop_id in (0x00010000, 0x02CF0000, 0x02CF0001):
            if val_len == 4:
                mid = struct.unpack_from("<I", val, 0)[0]
                if mid <= 32:
                    observed_enum = mid
                    if mid != FX3_PRODUCT_MODEL_ENUM:
                        errors.append(
                            f"FX3_PRODUCT_MODEL_ENUM_IMMUTABILITY_VIOLATION:got={mid},expected={FX3_PRODUCT_MODEL_ENUM}"
                        )
                else:
                    observed_model_id = mid
                    if mid != expected_model_id:
                        errors.append(
                            f"FX3_PRODUCT_MODEL_ID_IMMUTABILITY_VIOLATION:got=0x{mid:08x},expected=0x{expected_model_id:08x}"
                        )
            elif val_len == 1:
                observed_enum = val[0]
                if val[0] != FX3_PRODUCT_MODEL_ENUM:
                    errors.append(
                        f"FX3_PRODUCT_MODEL_ENUM_IMMUTABILITY_VIOLATION:got={val[0]},expected={FX3_PRODUCT_MODEL_ENUM}"
                    )

    # Also detect rogue known non-FX3 Sony model IDs embedded in raw payload metadata
    for foreign_id, label in (
        (FX3A_PRODUCT_MODEL_ID, "FX3A_0x91030082"),
        (A7IV_PRODUCT_MODEL_ID, "A7IV_0x01030081"),
    ):
        if foreign_id != expected_model_id and struct.pack("<I", foreign_id) in payload:
            errors.append(f"FX3_FOREIGN_MODEL_ID_DETECTED:{label}")

    return observed_model_id, observed_enum, errors


def verify_p2_bk4_nvram_dump(
    data: bytes,
    *,
    expected_product_model_id: int = FX3_PRODUCT_MODEL_ID,
) -> PartitionMagicReport:
    """Validate `p2` (`nflasha10` / `Backup.bin`) `'BK4\\0'` NVRAM header, checksum & FX3 model lock."""
    errors: List[str] = []
    warnings: List[str] = []
    if len(data) < BK4_HEADER_SIZE:
        return PartitionMagicReport(
            role="p2",
            valid=False,
            magic_ok=False,
            geometry_ok=False,
            fx3_immutability_ok=False,
            details={"bytes": len(data)},
            errors=(f"P2_BK4_TRUNCATED_BEFORE_HEADER:bytes={len(data)}",),
            warnings=(),
        )

    # Locate BK4 record either at offset 0 (raw Backup.bin) or inside a VFAT p2 partition image
    bk4_offset = 0
    container_type = "RAW_BK4"
    if data[0x0C:0x10] != BK4_MAGIC:
        found = data.find(BK4_MAGIC)
        if found >= 0x0C and found + (BK4_HEADER_SIZE - 0x0C) <= len(data):
            bk4_offset = found - 0x0C
            container_type = "VFAT_P2_CONTAINING_BK4"
        else:
            return PartitionMagicReport(
                role="p2",
                valid=False,
                magic_ok=False,
                geometry_ok=False,
                fx3_immutability_ok=False,
                details={"bytes": len(data), "header_magic_hex": data[0x0C:0x10].hex()},
                errors=(f"P2_BK4_MAGIC_MISSING:at_0x0c={data[0x0C:0x10].hex()}",),
                warnings=(),
            )

    sync_word = struct.unpack_from("<I", data, bk4_offset + 0x04)[0]
    active_byte8 = data[bk4_offset + 0x08]
    magic = data[bk4_offset + 0x0C : bk4_offset + 0x10]
    subs, props, data_off, data_size, expected_sum = struct.unpack_from("<IIIII", data, bk4_offset + 0x10)

    sync_ok = sync_word == BK4_SYNC_MARKER
    magic_ok = magic == BK4_MAGIC
    if not sync_ok:
        errors.append(f"P2_BK4_BAD_SYNC_MARKER:0x{sync_word:08x}")
    if not magic_ok:
        errors.append(f"P2_BK4_BAD_MAGIC:{magic.hex()}")

    total_rec = data_off + data_size
    geometry_ok = data_off >= BK4_HEADER_SIZE and bk4_offset + total_rec <= len(data)
    if not geometry_ok:
        errors.append(
            f"P2_BK4_SPAN_OUT_OF_BOUNDS:offset=0x{bk4_offset:x},data_off={data_off},data_size={data_size},len={len(data)}"
        )
        return PartitionMagicReport(
            role="p2",
            valid=False,
            magic_ok=magic_ok and sync_ok,
            geometry_ok=False,
            fx3_immutability_ok=False,
            details={"container": container_type, "bk4_offset": bk4_offset},
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    rec = data[bk4_offset : bk4_offset + total_rec]
    computed_sum = (sum(rec[0:0x20]) + sum(rec[0x24:total_rec])) & 0xFFFFFFFF
    checksum_ok = computed_sum == expected_sum
    if not checksum_ok:
        errors.append(
            f"P2_BK4_CHECKSUM_MISMATCH:header=0x{expected_sum:08x},computed=0x{computed_sum:08x}"
        )

    payload = rec[data_off:total_rec]
    obs_model_id, obs_enum, model_errors = _scan_bk4_properties_for_model_id(
        payload, props, expected_product_model_id
    )
    errors.extend(model_errors)
    if obs_model_id is None and obs_enum is None:
        warnings.append("P2_BK4_NO_EXPLICIT_PRODUCT_MODEL_TLV_PRESENT")

    if active_byte8 != 1:
        warnings.append(f"P2_BK4_ACTIVE_BYTE8_NOT_1:{active_byte8}")

    fx3_immutability_ok = len(model_errors) == 0
    valid = magic_ok and sync_ok and geometry_ok and checksum_ok and fx3_immutability_ok and (len(errors) == 0)
    return PartitionMagicReport(
        role="p2",
        valid=valid,
        magic_ok=magic_ok and sync_ok,
        geometry_ok=geometry_ok,
        fx3_immutability_ok=fx3_immutability_ok,
        details={
            "container": container_type,
            "bk4_offset": bk4_offset,
            "active_byte8": active_byte8,
            "subsystems": subs,
            "properties": props,
            "data_offset": data_off,
            "data_size": data_size,
            "checksum_ok": checksum_ok,
            "observed_product_model_id": hex(obs_model_id) if obs_model_id is not None else None,
            "observed_product_model_enum": obs_enum,
        },
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_p5_wbi2_dump(data: bytes) -> PartitionMagicReport:
    """Validate `p5` (`nflasha5`) `'WBI2'` 88-byte hibernation header & 64-byte section descriptors."""
    errors: List[str] = []
    warnings: List[str] = []
    if len(data) < WBI2_SECTION_TABLE_OFFSET_MIN:
        return PartitionMagicReport(
            role="p5",
            valid=False,
            magic_ok=False,
            geometry_ok=False,
            fx3_immutability_ok=True,
            details={"bytes": len(data)},
            errors=(f"P5_WBI2_TRUNCATED_BEFORE_HEADER:bytes={len(data)}",),
            warnings=(),
        )

    magic, padding, sections, flag, resume_vector, d_version, sector_size, r_data_size, kern_start, kern_size, kern_cksum, o_data_size = struct.unpack_from(
        "<4sI10Q", data, 0
    )

    if magic in WBI2_INVALIDATED_MAGICS:
        errors.append(f"P5_WBI2_MAGIC_INVALIDATED_COLD_BOOT_FORCED:{magic.hex()}")
    elif magic != WBI2_MAGIC:
        errors.append(f"P5_WBI2_BAD_MAGIC:{magic.hex()}")

    magic_ok = magic == WBI2_MAGIC
    if padding != 0:
        errors.append(f"P5_WBI2_NONZERO_PADDING:{padding}")
    if flag != 0:
        warnings.append(f"P5_WBI2_NONZERO_HEADER_FLAG:{flag}")
    if sector_size != SECTOR_SIZE:
        errors.append(f"P5_WBI2_BAD_SECTOR_SIZE:{sector_size}")
    if sections == 0 or sections > 100000:
        errors.append(f"P5_WBI2_INVALID_SECTION_COUNT:{sections}")

    table_off = 512 + r_data_size
    table_end = table_off + 64 * sections
    if table_end > len(data) or r_data_size > len(data):
        errors.append(
            f"P5_WBI2_TABLE_OUT_OF_BOUNDS:table_end={table_end},len={len(data)}"
        )
        return PartitionMagicReport(
            role="p5",
            valid=False,
            magic_ok=magic_ok,
            geometry_ok=False,
            fx3_immutability_ok=True,
            details={"magic_hex": magic.hex(), "sections": sections, "r_data_size": r_data_size},
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    at = 512
    total_olen = 0
    zero_sections = 0
    resume_covered = False
    spans: List[Tuple[int, int]] = []
    for idx in range(sections):
        addr, rlen, cksum, sflag, olen, virt, meta_cksum, spadding = struct.unpack_from(
            "<8Q", data, table_off + 64 * idx
        )
        if addr % 4096 != 0 or olen == 0 or olen % 4096 != 0:
            errors.append(f"P5_WBI2_UNALIGNED_SECTION:{idx}")
            break
        if sflag not in (0, 1) or spadding != 0:
            errors.append(f"P5_WBI2_BAD_SECTION_FLAG_OR_PAD:{idx}")
            break
        if (sflag == 0 and rlen != olen) or (sflag == 1 and rlen != 0):
            errors.append(f"P5_WBI2_RLEN_OLEN_MISMATCH:{idx}")
            break
        expected_meta = WBI2_XOR_MASK ^ addr ^ rlen ^ cksum ^ sflag ^ olen ^ virt
        if meta_cksum != expected_meta:
            errors.append(
                f"P5_WBI2_SECTION_META_XOR_MISMATCH:idx={idx},got=0x{meta_cksum:x},exp=0x{expected_meta:x}"
            )
            break
        if at + rlen > table_off:
            errors.append(f"P5_WBI2_SECTION_OVERRUNS_TABLE:{idx}")
            break
        if sflag == 1:
            zero_sections += 1
        if sflag == 0 and addr <= resume_vector < addr + rlen:
            resume_covered = True
        spans.append((addr, addr + olen))
        total_olen += olen
        at += rlen

    if len(errors) == 0:
        if at != table_off:
            errors.append(f"P5_WBI2_STORED_DATA_CURSOR_MISMATCH:at={at},table={table_off}")
        if total_olen != o_data_size:
            errors.append(f"P5_WBI2_ORIGINAL_DATA_SIZE_MISMATCH:sum={total_olen},hdr={o_data_size}")
        spans.sort()
        for a, b in zip(spans, spans[1:]):
            if a[1] > b[0]:
                errors.append(f"P5_WBI2_PHYSICAL_OVERLAP:0x{a[0]:x}..0x{a[1]:x}")
                break
        if not resume_covered:
            errors.append(f"P5_WBI2_RESUME_VECTOR_UNCOVERED:0x{resume_vector:x}")

    geometry_ok = len(errors) == 0
    valid = magic_ok and geometry_ok
    return PartitionMagicReport(
        role="p5",
        valid=valid,
        magic_ok=magic_ok,
        geometry_ok=geometry_ok,
        fx3_immutability_ok=True,
        details={
            "magic_hex": magic.hex(),
            "sections": sections,
            "zero_sections": zero_sections,
            "sector_size": sector_size,
            "r_data_size": r_data_size,
            "o_data_size": o_data_size,
            "resume_vector": hex(resume_vector),
            "resume_covered": resume_covered,
            "trailer_bytes": len(data) - table_end,
        },
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _walk_fat12_minimal(data: bytes) -> Tuple[Dict[str, Tuple[int, int]], Dict[str, int]]:
    """Bounded read-only FAT12 parser supporting configurable `reserved` sectors (e.g. p8 reserved=32)."""
    require(len(data) >= 512 and data[510:512] == b"\x55\xaa", "invalid FAT boot sector")
    sector = struct.unpack_from("<H", data, 11)[0]
    cluster_sectors = data[13]
    reserved = struct.unpack_from("<H", data, 14)[0]
    copies = data[16]
    entries = struct.unpack_from("<H", data, 17)[0]
    total = struct.unpack_from("<H", data, 19)[0] or struct.unpack_from("<I", data, 32)[0]
    fat_sectors = struct.unpack_from("<H", data, 22)[0]
    require(sector == 512 and cluster_sectors >= 1 and reserved >= 1 and copies == 2 and entries >= 16 and fat_sectors >= 1,
            "unsupported FAT12 BPB geometry")
    fat_start = reserved * 512
    fat_size = fat_sectors * 512
    root_off = (reserved + copies * fat_sectors) * 512
    root_size = entries * 32
    data_off = root_off + root_size
    cluster_size = 512 * cluster_sectors
    require(data_off <= total * 512 <= len(data), "FAT declared size exceeds input")
    clusters = (total * 512 - data_off) // cluster_size
    require(0 < clusters < 4085, "unsupported FAT12 cluster count")
    fat1 = data[fat_start : fat_start + fat_size]
    fat2 = data[fat_start + fat_size : fat_start + 2 * fat_size]
    require(fat1 == fat2, "FAT copies differ")

    files: Dict[str, Tuple[int, int]] = {}
    for at in range(0, root_size, 32):
        row = data[root_off + at : root_off + at + 32]
        if row[0] == 0:
            break
        if row[0] == 0xE5 or row[11] == 0x0F or (row[11] & 0x08):
            continue
        name = row[:8].rstrip(b" ").decode("ascii", errors="replace").lower()
        ext = row[8:11].rstrip(b" ").decode("ascii", errors="replace").lower()
        full = f"/{name}.{ext}" if ext else f"/{name}"
        start_c, size = struct.unpack_from("<HI", row, 26)
        if size > 0:
            require(2 <= start_c < clusters + 2, f"invalid start cluster for {full}")
            seg = data_off + (start_c - 2) * cluster_size
            require(seg < len(data), f"cluster offset out of bounds for {full}")
        files[full] = (start_c, size)

    return files, {
        "reserved_sectors": reserved,
        "fat_sectors": fat_sectors,
        "cluster_size": cluster_size,
        "cluster_count": clusters,
        "root_offset": root_off,
        "data_offset": data_off,
    }


def verify_p8_cp_rtos_dump(data: bytes) -> PartitionMagicReport:
    """Validate `p8` (`nflasha8` / `cp`) FAT12 geometry, ARMv7-R `cpapp-b.bin` vector, and Tomco markers."""
    errors: List[str] = []
    warnings: List[str] = []
    if len(data) < 64:
        return PartitionMagicReport(
            role="p8",
            valid=False,
            magic_ok=False,
            geometry_ok=False,
            fx3_immutability_ok=True,
            details={"bytes": len(data)},
            errors=(f"P8_CP_TRUNCATED:bytes={len(data)}",),
            warnings=(),
        )

    # Mode A: FAT12 p8 partition image (0x55 0xAA boot signature)
    if len(data) >= 512 and data[510:512] == b"\x55\xaa":
        try:
            files, meta = _walk_fat12_minimal(data)
        except Exception as exc:
            return PartitionMagicReport(
                role="p8",
                valid=False,
                magic_ok=False,
                geometry_ok=False,
                fx3_immutability_ok=True,
                details={"bytes": len(data)},
                errors=(f"P8_FAT12_PARSE_FAILED:{exc}",),
                warnings=(),
            )
        has_cpapp = "/cpapp-b.bin" in files
        has_tomco = "/tomco.txt" in files
        if not has_cpapp:
            errors.append("P8_MISSING_CPAPP_B_BIN")
        if not has_tomco:
            warnings.append("P8_MISSING_TOMCO_TXT")

        vector_ok = False
        tomco_marker_ok = False
        if has_cpapp:
            c_idx, _ = files["/cpapp-b.bin"]
            off = meta["data_offset"] + (c_idx - 2) * meta["cluster_size"]
            if off + 16 <= len(data):
                words = struct.unpack_from("<4I", data, off)
                # Accept exact FX3 Cortex-R5 reset vector or valid ARM branch/ldr reset word
                vector_ok = (words == CPAPP_ARM_RESET_WORDS) or (
                    (words[0] & 0xFF000000) in (0xE5000000, 0xEA000000) and words[3] == 0x0010800C
                )
            if not vector_ok:
                errors.append("P8_CPAPP_INVALID_ARM_RESET_VECTOR")
        if has_tomco:
            t_idx, t_sz = files["/tomco.txt"]
            toff = meta["data_offset"] + (t_idx - 2) * meta["cluster_size"]
            tbytes = data[toff : min(len(data), toff + min(t_sz, 512))]
            tomco_marker_ok = b"[TOMCO]" in tbytes
            if not tomco_marker_ok:
                errors.append("P8_TOMCO_TXT_MISSING_MARKER")

        rtos_marker_ok = (b"TOPPERS>" in data) or (b"LiroSeq" in data) or tomco_marker_ok
        valid = has_cpapp and vector_ok and (len(errors) == 0)
        return PartitionMagicReport(
            role="p8",
            valid=valid,
            magic_ok=vector_ok,
            geometry_ok=True,
            fx3_immutability_ok=True,
            details={
                "container": "FAT12_P8",
                "file_count": len(files),
                "has_cpapp_b_bin": has_cpapp,
                "has_tomco_txt": has_tomco,
                "tomco_marker_ok": tomco_marker_ok,
                "rtos_marker_ok": rtos_marker_ok,
                "vector_ok": vector_ok,
                **meta,
            },
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    # Mode B: Raw `cpapp-b.bin` RTOS binary
    words = struct.unpack_from("<4I", data, 0)
    vector_ok = (words == CPAPP_ARM_RESET_WORDS) or (
        (words[0] & 0xFF000000) in (0xE5000000, 0xEA000000) and words[3] == 0x0010800C
    )
    rtos_marker_ok = (b"TOPPERS>" in data) or (b"LiroSeq" in data) or (b"[TOMCO]" in data)
    if not vector_ok:
        errors.append("P8_RAW_CPAPP_INVALID_ARM_RESET_VECTOR")
    if not rtos_marker_ok:
        errors.append("P8_RAW_CPAPP_MISSING_RTOS_OR_TOMCO_MARKERS")

    valid = vector_ok and rtos_marker_ok and (len(errors) == 0)
    return PartitionMagicReport(
        role="p8",
        valid=valid,
        magic_ok=vector_ok,
        geometry_ok=len(data) >= 64,
        fx3_immutability_ok=True,
        details={
            "container": "RAW_CPAPP_B",
            "reset_words_hex": [hex(w) for w in words],
            "rtos_marker_ok": rtos_marker_ok,
        },
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_ext_csd_dump(data: bytes) -> ExtCsdAuditReport:
    """Audit 512-byte JEDEC JESD84-B51 eMMC `EXT_CSD` register dump (`PART_CONFIG` `0xB3`)."""
    errors: List[str] = []
    warnings: List[str] = []
    if len(data) != EXT_CSD_SIZE:
        return ExtCsdAuditReport(
            valid=False,
            part_config_raw=0,
            boot_ack=0,
            boot_partition_enable=0,
            boot_partition_name="INVALID_SIZE",
            partition_access=0,
            partition_access_name="INVALID_SIZE",
            boot_bus_conditions=0,
            rst_n_enable=0,
            boot_size_bytes=0,
            rpmb_size_bytes=0,
            pre_eol_info=0,
            life_time_a=0,
            life_time_b=0,
            errors=(f"EXT_CSD_BAD_SIZE:got={len(data)},expected={EXT_CSD_SIZE}",),
            warnings=(),
        )

    part_cfg = data[EXT_CSD_PART_CONFIG_IDX]
    boot_ack = (part_cfg >> 6) & 0x1
    boot_en = (part_cfg >> 3) & 0x7
    part_acc = part_cfg & 0x7
    reserved_bit7 = (part_cfg >> 7) & 0x1

    boot_names = {
        0: "NOT_BOOT_ENABLED",
        1: "BOOT0",
        2: "BOOT1",
        7: "USER_AREA",
    }
    acc_names = {
        0: "USER_AREA",
        1: "BOOT0",
        2: "BOOT1",
        3: "RPMB",
    }
    boot_name = boot_names.get(boot_en, f"RESERVED_{boot_en}")
    acc_name = acc_names.get(part_acc, f"RESERVED_{part_acc}")

    if reserved_bit7:
        errors.append(f"EXT_CSD_PART_CONFIG_RESERVED_BIT7_SET:0x{part_cfg:02x}")
    if boot_en == 0:
        errors.append("EXT_CSD_BOOT_PARTITION_DISABLED_BRICK_RISK:PART_CONFIG_bits_5_3_zero")
    elif boot_en not in (1, 2, 7):
        errors.append(f"EXT_CSD_INVALID_BOOT_PARTITION_ENABLE:{boot_en}")
    if part_acc not in (0, 1, 2, 3):
        errors.append(f"EXT_CSD_INVALID_PARTITION_ACCESS:{part_acc}")
    elif part_acc != 0:
        warnings.append(f"EXT_CSD_PARTITION_ACCESS_NOT_RESET_TO_UDA:{acc_name}")

    boot_bus = data[EXT_CSD_BOOT_BUS_COND_IDX]
    rst_n = data[EXT_CSD_RST_N_ENABLE_IDX] & 0x3
    boot_mult = data[EXT_CSD_BOOT_SIZE_MULT_IDX]
    rpmb_mult = data[EXT_CSD_RPMB_SIZE_MULT_IDX]
    boot_bytes = boot_mult * 128 * 1024
    rpmb_bytes = rpmb_mult * 128 * 1024

    if boot_mult == 0:
        errors.append("EXT_CSD_ZERO_BOOT_SIZE_MULT")
    if rst_n == 0x2:
        warnings.append("EXT_CSD_RST_N_PERMANENTLY_DISABLED")
    elif rst_n == 0x0:
        warnings.append("EXT_CSD_RST_N_TEMPORARILY_DISABLED")

    pre_eol = data[EXT_CSD_PRE_EOL_INFO_IDX]
    life_a = data[EXT_CSD_LIFE_TIME_A_IDX]
    life_b = data[EXT_CSD_LIFE_TIME_B_IDX]
    if pre_eol == 0x03:
        warnings.append("EXT_CSD_PRE_EOL_URGENT_WEAR_RISK")
    elif pre_eol == 0x02:
        warnings.append("EXT_CSD_PRE_EOL_WARNING_80PCT")
    if life_a >= 0x0A or life_b >= 0x0A:
        warnings.append(f"EXT_CSD_HIGH_NAND_WEAR:typA=0x{life_a:02x},typB=0x{life_b:02x}")

    return ExtCsdAuditReport(
        valid=len(errors) == 0,
        part_config_raw=part_cfg,
        boot_ack=boot_ack,
        boot_partition_enable=boot_en,
        boot_partition_name=boot_name,
        partition_access=part_acc,
        partition_access_name=acc_name,
        boot_bus_conditions=boot_bus,
        rst_n_enable=rst_n,
        boot_size_bytes=boot_bytes,
        rpmb_size_bytes=rpmb_bytes,
        pre_eol_info=pre_eol,
        life_time_a=life_a,
        life_time_b=life_b,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Boot-Chain Immutability Firewall
# ---------------------------------------------------------------------------


def _extract_tokens_and_ops(
    manifest_or_targets: Union[Mapping[str, object], Sequence[str], str],
    default_op: str,
) -> Tuple[List[str], List[str]]:
    targets: List[str] = []
    ops: List[str] = [default_op.lower().strip()]

    if isinstance(manifest_or_targets, str):
        targets.append(manifest_or_targets)
    elif isinstance(manifest_or_targets, Mapping):
        for k in ("target", "partition", "device", "device_node", "path", "output_target"):
            v = manifest_or_targets.get(k)
            if isinstance(v, str) and v.strip():
                targets.append(v)
        for k in ("targets", "partitions", "write_targets", "flash_targets"):
            v = manifest_or_targets.get(k)
            if isinstance(v, (list, tuple)):
                for item in v:
                    if isinstance(item, str) and item.strip():
                        targets.append(item)
        for k in ("operation", "op", "action", "mode", "command"):
            v = manifest_or_targets.get(k)
            if isinstance(v, str) and v.strip():
                ops.append(v.lower().strip())
        for k in ("operations", "commands"):
            v = manifest_or_targets.get(k)
            if isinstance(v, (list, tuple)):
                for item in v:
                    if isinstance(item, str) and item.strip():
                        ops.append(item.lower().strip())
        if manifest_or_targets.get("persistent_emmc_writes_authorized") is True:
            ops.append("unlock_write")
        if manifest_or_targets.get("flashable") is True or manifest_or_targets.get("write_enable") is True:
            ops.append("write")
        if manifest_or_targets.get("cmd42_force_erase") is True:
            ops.append("cmd42_force_erase")
    else:
        for item in manifest_or_targets:
            if isinstance(item, str) and item.strip():
                targets.append(item)

    return targets, ops


def _is_immutable_boot_target(token: str) -> bool:
    norm = token.strip().lower().replace("\\", "/")
    base = norm.split("/")[-1]
    for pat in IMMUTABLE_BOOT_PARTITION_TOKENS:
        if base == pat or norm.endswith("/" + pat) or pat in base.split(":"):
            return True
    # Also catch explicit mmcblk0boot0 / nflasha1..8 substring references in device nodes
    for idx in range(1, 9):
        if f"nflasha{idx}" in norm and (f"nflasha{idx}0" not in norm and f"nflasha{idx}1" not in norm and f"nflasha{idx}2" not in norm and f"nflasha{idx}5" not in norm and f"nflasha{idx}8" not in norm):
            return True
    for hw in ("boot0", "boot1", "rpmb", "nflashab0", "nflashab1", "loader_nor", "ldrbkup", "sector0"):
        if hw in norm:
            return True
    return False


def audit_boot_chain_immutability(
    manifest_or_targets: Union[Mapping[str, object], Sequence[str], str],
    *,
    operation: str = "read_verify",
) -> BootChainFirewallDecision:
    """Enforce hard-locked read-only policy against BOOT0/BOOT1/RPMB/nflasha1..8 mutations."""
    targets, ops = _extract_tokens_and_ops(manifest_or_targets, operation)
    blocked_targets: List[str] = []
    blocked_ops: List[str] = []
    errors: List[str] = []

    has_mutating_op = False
    for op in ops:
        if any(m in op for m in MUTATING_FORBIDDEN_OPS) or op not in READONLY_ALLOWED_OPS:
            has_mutating_op = True
            blocked_ops.append(op)

    for t in targets:
        if _is_immutable_boot_target(t) and has_mutating_op:
            blocked_targets.append(t)

    if has_mutating_op:
        errors.append(
            f"BLOCKED_BY_BOOT_CHAIN_IMMUTABILITY_FIREWALL:ops={sorted(set(blocked_ops))}"
        )
    if blocked_targets:
        errors.append(
            f"BLOCKED_IMMUTABLE_BOOT_PARTITION_TARGET:{sorted(set(blocked_targets))}"
        )

    return BootChainFirewallDecision(
        allowed=len(errors) == 0,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        blocked_targets=tuple(sorted(set(blocked_targets))),
        blocked_operations=tuple(sorted(set(blocked_ops))),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Unified Forensic Verifier Entrypoints (Bytes & File O_RDONLY)
# ---------------------------------------------------------------------------


def verify_emmc_dump_bytes(
    data: bytes,
    *,
    role: str = "generic",
    expected_size: Optional[int] = None,
    expect_encrypted: bool = False,
    ext_csd_bytes: Optional[bytes] = None,
    manifest: Optional[Mapping[str, object]] = None,
    source_mode: str = "BYTES_BUFFER",
    two_pass_stability: Optional[TwoPassStabilityReport] = None,
) -> EmmcDumpForensicReport:
    """Run all Tier-4 forensic checks on an in-memory eMMC partition dump."""
    require(role in VALID_ROLES, f"unsupported forensic role: {role}")

    firewall = audit_boot_chain_immutability(
        manifest if manifest is not None else {"target": role, "operation": "read_verify"},
        operation="read_verify",
    )

    bus_rep = analyze_bus_and_entropy(
        data,
        expected_size=expected_size,
        role=role,
        expect_encrypted=expect_encrypted or (role == "cnflasha"),
        expect_compressed=(role == "p1"),
        require_sector_aligned=(role not in ("ext_csd", "p5")) or (role == "ext_csd" and len(data) == EXT_CSD_SIZE),
    )

    ext_rep: Optional[ExtCsdAuditReport] = None
    if ext_csd_bytes is not None:
        ext_rep = verify_ext_csd_dump(ext_csd_bytes)

    if role == "sector0":
        part_rep = verify_sector0_dump(data)
    elif role == "p1":
        part_rep = verify_p1_vfat_dump(data, check_fat_tree=True)
    elif role == "p2":
        part_rep = verify_p2_bk4_nvram_dump(data)
    elif role == "p5":
        part_rep = verify_p5_wbi2_dump(data)
    elif role == "p8":
        part_rep = verify_p8_cp_rtos_dump(data)
    elif role == "ext_csd":
        ext_rep = verify_ext_csd_dump(data)
        part_rep = PartitionMagicReport(
            role="ext_csd",
            valid=ext_rep.valid,
            magic_ok=ext_rep.valid,
            geometry_ok=len(data) == EXT_CSD_SIZE,
            fx3_immutability_ok=True,
            details={"part_config_hex": hex(ext_rep.part_config_raw), "boot_partition": ext_rep.boot_partition_name},
            errors=ext_rep.errors,
            warnings=ext_rep.warnings,
        )
    else:
        # `cnflasha` or `generic`
        part_rep = PartitionMagicReport(
            role=role,
            valid=bus_rep.passed,
            magic_ok=True,
            geometry_ok=not bus_rep.truncation_detected,
            fx3_immutability_ok=True,
            details={"encrypted_expected": expect_encrypted or (role == "cnflasha")},
            errors=(),
            warnings=(),
        )

    errors: List[str] = []
    warnings: List[str] = []
    if two_pass_stability is not None and not two_pass_stability.stable:
        errors.extend(two_pass_stability.errors)
    if not firewall.allowed:
        errors.extend(firewall.errors)
    if not bus_rep.passed:
        errors.extend(bus_rep.anomalies)
    if not part_rep.valid:
        errors.extend(part_rep.errors)
    warnings.extend(part_rep.warnings)
    if ext_rep is not None:
        if not ext_rep.valid and role != "ext_csd":
            errors.extend(ext_rep.errors)
        if role != "ext_csd":
            warnings.extend(ext_rep.warnings)

    passed = (
        len(errors) == 0
        and firewall.allowed
        and bus_rep.passed
        and part_rep.valid
        and (ext_rep.valid if ext_rep is not None else True)
        and (two_pass_stability.stable if two_pass_stability is not None else True)
    )

    digest = two_pass_stability.pass1_sha256 if (two_pass_stability and two_pass_stability.stable) else sha256(data).hexdigest()

    return EmmcDumpForensicReport(
        schema=FORENSIC_VERIFIER_SCHEMA,
        role=role,
        source_mode=source_mode,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        passed=passed,
        sha256=digest,
        two_pass_stability=two_pass_stability,
        bus_and_entropy=bus_rep,
        partition_magic=part_rep,
        ext_csd=ext_rep,
        boot_chain_firewall=firewall,
        errors=tuple(dict.fromkeys(errors)),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def verify_emmc_dump_file(
    path: Union[Path, str],
    *,
    role: str = "generic",
    expected_size: Optional[int] = None,
    expect_encrypted: bool = False,
    ext_csd_path: Optional[Union[Path, str]] = None,
    manifest: Optional[Mapping[str, object]] = None,
    source_mode: str = "PATH_READONLY",
) -> EmmcDumpForensicReport:
    """Strictly `O_RDONLY` two-pass read and Tier-4 forensic verification of a local dump file."""
    stability, data = read_two_pass_sha256_readonly(path)
    if not stability.stable or data is None:
        raise ForensicVerificationError(f"Unstable two-pass O_RDONLY dump read: {stability.errors}")

    ext_bytes: Optional[bytes] = None
    if ext_csd_path is not None:
        ext_stab, ext_bytes = read_two_pass_sha256_readonly(ext_csd_path, max_bytes=4096)
        if not ext_stab.stable or ext_bytes is None:
            raise ForensicVerificationError(f"Unstable EXT_CSD O_RDONLY read: {ext_stab.errors}")

    return verify_emmc_dump_bytes(
        data,
        role=role,
        expected_size=expected_size,
        expect_encrypted=expect_encrypted,
        ext_csd_bytes=ext_bytes,
        manifest=manifest,
        source_mode=source_mode,
        two_pass_stability=stability,
    )


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixture Builders (for FX3_FX6_FORCE_CLEAN_ROOM=1)
# ---------------------------------------------------------------------------


def build_synthetic_sector0_fx3() -> bytes:
    """Build a valid 512-byte FX3 7.02 Sector 0 ('8246' '2.00') partition table."""
    buf = bytearray(SONY_PTBL_SIZE)
    buf[0:4] = SONY_PTBL_MAGIC
    buf[4:8] = SONY_PTBL_VERSION
    struct.pack_into("<I", buf, 8, SONY_PTBL_ENTRY_COUNT)
    for pid, (start_s, size_s, ptype, flag, _label) in FX3_KEY_PARTITIONS.items():
        off = 32 + (pid - 1) * 16
        struct.pack_into("<IIII", buf, off, start_s, size_s, ptype, flag)
    return bytes(buf)


def build_synthetic_p1_vfat_image(total_clusters: int = 8) -> bytes:
    """Build a valid minimal FX3 FAT12 p1 image (BPB + mirrored FATs + /p1chksum + /initrd.img)."""
    require(8 <= total_clusters < 4085, "invalid synthetic cluster count (need >= 8)")
    total_sectors = 1 + 2 * 32 + 32 + total_clusters * 32
    img = bytearray(total_sectors * 512)
    struct.pack_into("<H", img, 11, 512)
    img[13] = 32
    struct.pack_into("<H", img, 14, 1)
    img[16] = 2
    struct.pack_into("<H", img, 17, 512)
    struct.pack_into("<H", img, 19, total_sectors)
    struct.pack_into("<H", img, 22, 32)
    img[510:512] = b"\x55\xaa"

    # Cluster 2 -> EOF (/p1chksum), Clusters 3..8 chained -> EOF (/initrd.img, 96 KiB)
    fat_start = 512
    fat_size = 32 * 512
    fat_entries = {2: 0xFFF, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 0xFFF}
    for c_idx, val in fat_entries.items():
        at = fat_start + c_idx + c_idx // 2
        cur = struct.unpack_from("<H", img, at)[0]
        if c_idx & 1:
            cur = (cur & 0x000F) | ((val & 0xFFF) << 4)
        else:
            cur = (cur & 0xF000) | (val & 0xFFF)
        struct.pack_into("<H", img, at, cur)

    root_off = (1 + 2 * 32) * 512
    entry0 = bytearray(32)
    entry0[0:11] = b"P1CHKSUM   "
    entry0[11] = 0x20
    struct.pack_into("<HI", entry0, 26, 2, 32)
    img[root_off : root_off + 32] = entry0

    initrd_size = 6 * 16384
    entry1 = bytearray(32)
    entry1[0:11] = b"INITRD  IMG"
    entry1[11] = 0x20
    struct.pack_into("<HI", entry1, 26, 3, initrd_size)
    img[root_off + 32 : root_off + 64] = entry1
    img[fat_start + fat_size : fat_start + 2 * fat_size] = img[fat_start : fat_start + fat_size]

    data_off = root_off + 512 * 32
    img[data_off : data_off + 32] = b"0" * 32
    prng = bytearray()
    seed = b"fx3-synthetic-p1-initrd"
    while len(prng) < initrd_size:
        seed = sha256(seed).digest()
        prng.extend(seed)
    img[data_off + 16384 : data_off + 16384 + initrd_size] = prng[:initrd_size]
    return bytes(img)


def build_synthetic_p2_bk4_image(
    *,
    product_model_id: int = FX3_PRODUCT_MODEL_ID,
    product_model_enum: int = FX3_PRODUCT_MODEL_ENUM,
    total_size: int = 4096,
) -> bytes:
    """Build a valid 4 KiB-aligned `p2` `BK4\\0` NVRAM record with FX3 PRODUCT_MODEL."""
    props: Tuple[Tuple[int, bytes], ...] = (
        (0x02CF0000, struct.pack("<I", product_model_id)),
        (0x02CF0001, struct.pack("<I", product_model_enum)),
        (0x02CF1702, b"\x01"),
        (0x02CF1704, b"\x10"),
        (0x02CF1443, b"\x03"),
        (0x02CF1453, b"\x02"),
    )
    payload = bytearray()
    for pid, val in props:
        payload.extend(struct.pack("<IH", pid, len(val)))
        payload.extend(val)
    total_rec = BK4_HEADER_SIZE + len(payload)
    buf = bytearray(max(total_size, ((total_rec + 511) // 512) * 512))
    struct.pack_into("<I", buf, 0x04, BK4_SYNC_MARKER)
    buf[0x08] = 1
    buf[0x0C:0x10] = BK4_MAGIC
    struct.pack_into("<IIII", buf, 0x10, 1, len(props), BK4_HEADER_SIZE, len(payload))
    struct.pack_into("<i", buf, 0x2C, 1)
    buf[BK4_HEADER_SIZE : BK4_HEADER_SIZE + len(payload)] = payload
    checksum = (sum(buf[0:0x20]) + sum(buf[0x24:total_rec])) & 0xFFFFFFFF
    struct.pack_into("<I", buf, 0x20, checksum)
    # Pad remainder with deterministic non-zero bytes so entropy stays healthy
    for i in range(total_rec, len(buf), 32):
        digest = sha256(struct.pack("<I", i)).digest()
        take = min(32, len(buf) - i)
        buf[i : i + take] = digest[:take]
    return bytes(buf)


def build_synthetic_p5_wbi2_image(*, magic: bytes = WBI2_MAGIC) -> bytes:
    """Build a valid synthetic `'WBI2'` hibernation partition dump with XOR-verified descriptors."""
    sec0_addr = 0x400080000
    sec0_len = 8192
    sec1_addr = 0x400082000
    sec1_len = 4096  # zero section (flag=1)

    r_data_size = sec0_len
    o_data_size = sec0_len + sec1_len
    resume_vector = sec0_addr + 0x100
    table_off = 512 + r_data_size
    total_len = ((table_off + 2 * 64 + 511) // 512) * 512
    buf = bytearray(total_len)

    struct.pack_into(
        "<4sI10Q",
        buf,
        0,
        magic,
        0,
        2,
        0,
        resume_vector,
        0x07020000,
        SECTOR_SIZE,
        r_data_size,
        sec0_addr,
        sec0_len,
        0,
        o_data_size,
    )

    # High-entropy synthetic kernel/RAM snapshot section
    prng = bytearray()
    seed = b"fx3-synthetic-wbi2-ram"
    while len(prng) < sec0_len:
        seed = sha256(seed).digest()
        prng.extend(seed)
    buf[512 : 512 + sec0_len] = prng[:sec0_len]

    # Section descriptors
    for idx, (addr, rlen, sflag, olen) in enumerate(
        (
            (sec0_addr, sec0_len, 0, sec0_len),
            (sec1_addr, 0, 1, sec1_len),
        )
    ):
        virt = addr - 0x400000000 + 0xFFFFFFC000000000
        cksum = WBI2_XOR_MASK
        meta_cksum = WBI2_XOR_MASK ^ addr ^ rlen ^ cksum ^ sflag ^ olen ^ virt
        struct.pack_into("<8Q", buf, table_off + idx * 64, addr, rlen, cksum, sflag, olen, virt, meta_cksum, 0)

    return bytes(buf)


def build_synthetic_p8_cp_image(*, include_tomco: bool = True, valid_vector: bool = True) -> bytes:
    """Build a valid synthetic FAT12 `p8` (`nflasha8` / `cp`) image with `/cpapp-b.bin` and `/tomco.txt`."""
    reserved = 32
    fat_sectors = 32
    copies = 2
    entries = 512
    cluster_sectors = 32
    total_clusters = 8
    total_sectors = reserved + copies * fat_sectors + (entries * 32) // 512 + total_clusters * cluster_sectors
    img = bytearray(total_sectors * 512)

    struct.pack_into("<H", img, 11, 512)
    img[13] = cluster_sectors
    struct.pack_into("<H", img, 14, reserved)
    img[16] = copies
    struct.pack_into("<H", img, 17, entries)
    struct.pack_into("<I", img, 32, total_sectors)
    struct.pack_into("<H", img, 22, fat_sectors)
    img[510:512] = b"\x55\xaa"

    fat_start = reserved * 512
    fat_size = fat_sectors * 512
    for c_idx, val in ((2, 3), (3, 4), (4, 5), (5, 0xFFF), (6, 0xFFF)):
        at = fat_start + c_idx + c_idx // 2
        cur = struct.unpack_from("<H", img, at)[0]
        if c_idx & 1:
            cur = (cur & 0x000F) | ((val & 0xFFF) << 4)
        else:
            cur = (cur & 0xF000) | (val & 0xFFF)
        struct.pack_into("<H", img, at, cur)
    img[fat_start + fat_size : fat_start + 2 * fat_size] = img[fat_start : fat_start + fat_size]

    root_off = (reserved + copies * fat_sectors) * 512
    data_off = root_off + entries * 32

    # Entry 0: /cpapp-b.bin at clusters 2..5 (64 KiB)
    cp_size = 4 * 16384
    e0 = bytearray(32)
    e0[0:11] = b"CPAPP-B BIN"
    e0[11] = 0x20
    struct.pack_into("<HI", e0, 26, 2, cp_size)
    img[root_off : root_off + 32] = e0

    cp_off = data_off
    words = CPAPP_ARM_RESET_WORDS if valid_vector else (0x00000000, 0x00000000, 0x00000000, 0x00000000)
    struct.pack_into("<4I", img, cp_off, *words)
    marker = b"TOPPERS> LiroSeq: Restore."
    img[cp_off + 64 : cp_off + 64 + len(marker)] = marker
    prng = bytearray()
    seed = b"fx3-synthetic-cpapp"
    while len(prng) < cp_size - 256:
        seed = sha256(seed).digest()
        prng.extend(seed)
    img[cp_off + 256 : cp_off + cp_size] = prng[: cp_size - 256]

    if include_tomco:
        e1 = bytearray(32)
        e1[0:11] = b"TOMCO   TXT"
        e1[11] = 0x20
        struct.pack_into("<HI", e1, 26, 6, 64)
        img[root_off + 32 : root_off + 64] = e1
        tomco_bytes = b"[TOMCO]\nusrrtn_cfggrp=2\ntmon_cpu=0x0F\n"
        img[data_off + 4 * 16384 : data_off + 4 * 16384 + len(tomco_bytes)] = tomco_bytes

    return bytes(img)


def build_synthetic_ext_csd(
    *,
    part_config: int = 0x48,  # BOOT_ACK=1, BOOT0 enabled, UDA access
    boot_size_mult: int = 32,  # 4 MiB
    rpmb_size_mult: int = 32,
    rst_n_enable: int = 1,
    pre_eol_info: int = 1,
    life_time_a: int = 1,
    life_time_b: int = 1,
) -> bytes:
    """Build a valid 512-byte JEDEC `EXT_CSD` register dump."""
    buf = bytearray(EXT_CSD_SIZE)
    buf[EXT_CSD_RST_N_ENABLE_IDX] = rst_n_enable & 0xFF
    buf[EXT_CSD_RPMB_SIZE_MULT_IDX] = rpmb_size_mult & 0xFF
    buf[EXT_CSD_BOOT_BUS_COND_IDX] = 0x02  # x8 SDR
    buf[EXT_CSD_PART_CONFIG_IDX] = part_config & 0xFF
    buf[EXT_CSD_REV_IDX] = 8  # eMMC 5.1
    struct.pack_into("<I", buf, EXT_CSD_SEC_COUNT_IDX, 0x03A3E000)
    buf[EXT_CSD_BOOT_SIZE_MULT_IDX] = boot_size_mult & 0xFF
    buf[EXT_CSD_PRE_EOL_INFO_IDX] = pre_eol_info & 0xFF
    buf[EXT_CSD_LIFE_TIME_A_IDX] = life_time_a & 0xFF
    buf[EXT_CSD_LIFE_TIME_B_IDX] = life_time_b & 0xFF
    return bytes(buf)


def build_synthetic_encrypted_cnflasha(size: int = 32768) -> bytes:
    """Build a deterministic high-entropy synthetic AES-XTS-like `cnflasha` partition fixture."""
    require(size >= 4096 and size % 512 == 0, "synthetic encrypted dump must be >= 4096 and 512B aligned")
    out = bytearray()
    seed = b"fx3-synthetic-cnflasha-xts"
    while len(out) < size:
        seed = sha256(seed).digest()
        out.extend(seed)
    return bytes(out[:size])


def run_clean_room_forensic_suite() -> Dict[str, object]:
    """Execute full clean-room Tier-4 eMMC forensic self-test suite across all partition roles."""
    ext_csd = build_synthetic_ext_csd()
    checks = {
        "sector0": verify_emmc_dump_bytes(build_synthetic_sector0_fx3(), role="sector0", source_mode="CLEAN_ROOM_SYNTHETIC"),
        "p1": verify_emmc_dump_bytes(build_synthetic_p1_vfat_image(), role="p1", source_mode="CLEAN_ROOM_SYNTHETIC"),
        "p2": verify_emmc_dump_bytes(build_synthetic_p2_bk4_image(), role="p2", source_mode="CLEAN_ROOM_SYNTHETIC"),
        "p5": verify_emmc_dump_bytes(build_synthetic_p5_wbi2_image(), role="p5", source_mode="CLEAN_ROOM_SYNTHETIC"),
        "p8": verify_emmc_dump_bytes(build_synthetic_p8_cp_image(), role="p8", source_mode="CLEAN_ROOM_SYNTHETIC"),
        "ext_csd": verify_emmc_dump_bytes(ext_csd, role="ext_csd", source_mode="CLEAN_ROOM_SYNTHETIC"),
        "cnflasha": verify_emmc_dump_bytes(
            build_synthetic_encrypted_cnflasha(),
            role="cnflasha",
            expect_encrypted=True,
            ext_csd_bytes=ext_csd,
            source_mode="CLEAN_ROOM_SYNTHETIC",
        ),
    }
    firewall_block = audit_boot_chain_immutability({"target": "BOOT0", "operation": "flash"})
    all_ok = all(r.passed for r in checks.values()) and (not firewall_block.allowed)
    return {
        "schema": FORENSIC_VERIFIER_SCHEMA,
        "status": "VERIFIED_READONLY" if all_ok else "REJECTED",
        "mode": "CLEAN_ROOM_SYNTHETIC" if is_forced_clean_room() else "CLEAN_ROOM_SYNTHETIC",
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "allow_boot_partition_targeting": ALLOW_BOOT_PARTITION_TARGETING,
        "all_passed": all_ok,
        "roles_verified": {k: {"passed": v.passed, "sha256": v.sha256[:16]} for k, v in checks.items()},
        "boot_chain_firewall_blocks_boot0_flash": not firewall_block.allowed,
    }


def report_to_dict(report: EmmcDumpForensicReport) -> Dict[str, object]:
    """Serialize an `EmmcDumpForensicReport` to a deterministic JSON-compatible dict."""
    return asdict(report)
