"""Phase 119 — SquashFS 4.0 (`hsqs` `0x73717368`) Partition Superblock / Compression /
Table-Bounds Verifier, Sony Warp-Boot `hibdrv` (`WBI` Hibernation Snapshot) Stale-Resume
Poisoning Triage & Ephemeral `noresume` RAM-Boot Bypass Verifier, & 12-Pillar Master Suite.

Provides three deterministic, RAM-only, read-only-donor verification pillars for
Sony `ILME-FX3` (`0x91030080` / `ALCIN_UUD`, `CXD90057` Linux `4.9.337-scel+`) recovery
and Stage-B safety verification:

1. **Pillar A — SquashFS 4.0 (`hsqs` LE magic `0x73717368`) Superblock & Table-Bounds Verifier**:
   - Pure-Python parser & validator for 96-byte SquashFS 4.0 superblocks (`<5I6H8Q`):
     `s_magic == 0x73717368` (rejecting big-endian `0x68737173` `sqsh` & blank/erased flash),
     `inodes`, `mkfs_time`, `block_size` power-of-two `4 KiB..1 MiB` (`block_log == log2(block_size)`),
     `fragments`, `compression_id` in `{1:GZIP, 2:LZMA, 3:LZO, 4:XZ, 5:LZ4, 6:ZSTD}`,
     `flags`, `no_ids`, `s_major == 4`, `s_minor == 0`, `bytes_used <= partition_size`,
     and strictly monotonic table bounds (`96 <= inode_table_start < directory_table_start <= ... <= bytes_used`).
   - Detects truncated rootfs/`app` flashes before boot or deployment so `/sbin/init2` `SIGBUS`
     and `VFS: Unable to mount root fs` boot-loops are caught fail-closed offline.

2. **Pillar B — Sony `Warp-Boot` / `hibdrv` (`WBI` Hibernation Snapshot) Stale-Resume Poisoning
   Triage & Ephemeral `noresume` Bypass Verifier**:
   - On Sony Linux `4.9.337-scel+` (`CXD90057`), `hibdrv` restores a saved `WBI2` hibernation
     image (`nflasha5`) for sub-second cold boot. If `UTS_VERSION` / `Image` build fingerprint or
     `initramfs` layout differs from the saved `WBI` snapshot (or power dropped mid-snapshot),
     `hibdrv` panics during page-table restore before userland starts.
   - Implements a forensic `WBI` snapshot header & section-table inspector (clean-room synthetic
     header model + read-only FX3/FX6 donor cross-check) detecting:
     a) `WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH`,
     b) `WBI_KERNEL_ABI_FINGERPRINT_MISMATCH` (stale snapshot from prior firmware slot or cross-SKU),
     c) `WBI_EPHEMERAL_NORESUME_REQUIRED` when booting a Stage-B RAM-only test kernel/ramdisk.
   - Verifies remediation uses strictly RAM-only `bootargs` (`noresume` / `hibdrv.resume=0`)
     with **zero persistent eMMC `WBI` partition erase/writes** (`wbi_partition_writes == 0`).

3. **Pillar C — 12-Pillar Recovery Master Suite Readiness Gate (`run_squashfs_and_hibdrv_wbi_suite`)**:
   - Dual-mode execution (`LOCAL_DONOR_O_RDONLY` via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`
     and `CLEAN_ROOM_SYNTHETIC` when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor absent).
   - Hard-locks `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`,
     `ALLOW_BOOT_PARTITION_TARGETING = False`, `ALLOW_DESTRUCTIVE_FASTBOOT = False`,
     `OTP_FUSE_TOUCHES = 0`, `PASSIVE_TX_BYTES_EMITTED = 0`, `PHYSICAL_DEVICE_WRITES = 0`,
     and `WBI_PARTITION_WRITES = 0`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import shlex
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple
import zlib

from .fat import FatP1, MAX_P1
from .files import is_forced_clean_room, local_path, read_file, require, resolve_donor_path


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

SQUASHFS_WBI_HIBDRV_SCHEMA: str = "fx3-squashfs-and-hibdrv-wbi-verifier-v1"
SQUASHFS_WBI_HIBDRV_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True
OTP_FUSE_TOUCHES: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
WBI_PARTITION_WRITES: int = 0

STATUS_VERIFIED_SQUASHFS_WBI_GATE: str = "VERIFIED_SQUASHFS_AND_HIBDRV_WBI_GATE"
STATUS_FAIL_SQUASHFS_WBI_GATE: str = "FAIL_SQUASHFS_AND_HIBDRV_WBI_GATE"
STATUS_VERIFIED_SQUASHFS_SUPERBLOCK: str = "VERIFIED_SQUASHFS_4_0_SUPERBLOCK"
STATUS_REJECTED_SQUASHFS_SUPERBLOCK: str = "REJECTED_SQUASHFS_4_0_SUPERBLOCK"
STATUS_WBI_HEALTHY_RESUME_MATCH: str = "WBI_HEALTHY_RESUME_FINGERPRINT_MATCH"
STATUS_WBI_POISONING_NORESUME_BYPASS: str = "WBI_POISONED_EPHEMERAL_NORESUME_BYPASS_REQUIRED"
STATUS_WBI_COLD_BOOT_INVALIDATED: str = "WBI_EXPLICITLY_INVALIDATED_COLD_BOOT"
STATUS_WBI_PERSISTENT_WRITE_BLOCKED: str = "WBI_PERSISTENT_PARTITION_WRITE_BLOCKED"
STATUS_VERIFIED_EPHEMERAL_NORESUME_BYPASS: str = "VERIFIED_EPHEMERAL_NORESUME_BOOTARGS_BYPASS"
STATUS_REJECTED_EPHEMERAL_NORESUME_BYPASS: str = "REJECTED_EPHEMERAL_NORESUME_BOOTARGS_BYPASS"

# Local Donor Relative Paths (strictly read-only via os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
DONOR_FX3_P1_205_SQUASHFS_HOST_RELPATH: str = (
    "fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1"
)
DONOR_FX3_UDTRBODY_SQUASHFS_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/original-members/udtrbody.squashfs"
)
DONOR_FX6_UPDATER_SQUASHFS_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/updater.img"
)
DONOR_FX3_NFLASH5_WBI2_RELPATH: str = "sony-firmware-20261024/stage2/extraction/nflasha5.img"
DONOR_FX6_NFLASH5_WBI2_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0700_part_image/dev/nflasha5"
)
DONOR_FX3_VMLINUX_KERNEL_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/current-updater-evidence/p3-main/vmlinux.bin"
)
DONOR_FX6_VMLINUX_KERNEL_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha3/vmlinux.bin"
)

# Pinned Integrity Anchors (Zero Proprietary Keys)
PINNED_FX3_P1_INITRD_SQUASHFS_SHA256: str = "d5c4795c962750d2d9b6c4a387d927d05bdf59d4427054e857ba6146790ae790"
PINNED_FX3_P1_INITRD_SQUASHFS_BYTES: int = 9097216
PINNED_FX3_UDTRBODY_SQUASHFS_SHA256: str = "62e86fad175e0326969d5f1cea29d780feb496ce8034acd2c9c3954320d8ccaa"
PINNED_FX3_UDTRBODY_SQUASHFS_BYTES: int = 1253376
PINNED_FX6_UPDATER_SQUASHFS_SHA256: str = "d204fcf2b2b6ca4777b0fae5dda3af919af85e9b7651c1b6b87eac760363183a"
PINNED_FX6_UPDATER_SQUASHFS_BYTES: int = 1253376

PINNED_FX3_NFLASH5_WBI2_TOTAL_BYTES: int = 209112512
PINNED_FX3_NFLASH5_WBI2_SECTIONS: int = 1399
PINNED_FX3_NFLASH5_WBI2_HDR_SHA256: str = "11ae397741d07e5bb65b61336970310ebceae72c5ee4d5cc6db2cfa3774363b9"
PINNED_FX3_NFLASH5_WBI2_TABLE_SHA256: str = "7286ddb05a7363c6bc8c28f2749164c8e52a7b2c8ffc70ed519fe3a8ac71cbc9"

PINNED_FX6_NFLASH5_WBI2_TOTAL_BYTES: int = 202677056
PINNED_FX6_NFLASH5_WBI2_SECTIONS: int = 1197
PINNED_FX6_NFLASH5_WBI2_HDR_SHA256: str = "afa139510c2c5fb2656a062690f70b6296efeab477b64ab5701c00899e0c61ba"
PINNED_FX6_NFLASH5_WBI2_TABLE_SHA256: str = "38d12419b351a09d129e949d25cac1ebde3068a8253bcc30d896414a16d5941b"

PINNED_FX3_VMLINUX_KERNEL_SHA256: str = "da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c"
PINNED_FX6_VMLINUX_KERNEL_SHA256: str = "bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9"

# ---------------------------------------------------------------------------
# Pillar A Constants — SquashFS 4.0 Superblock & Table-Bounds
# ---------------------------------------------------------------------------

SQUASHFS_MAGIC: int = 0x73717368  # 'hsqs' little-endian
SQUASHFS_MAGIC_BE: int = 0x68737173  # 'sqsh' big-endian
SQUASHFS_SUPERBLOCK_SIZE: int = 96
SQUASHFS_MAJOR_VERSION: int = 4
SQUASHFS_MINOR_VERSION: int = 0
SQUASHFS_MIN_BLOCK_SIZE: int = 4096
SQUASHFS_MAX_BLOCK_SIZE: int = 1048576
SQUASHFS_MIN_BLOCK_LOG: int = 12
SQUASHFS_MAX_BLOCK_LOG: int = 20
SQUASHFS_MAX_INODES: int = 10_000_000
SQUASHFS_MAX_BYTES_USED: int = 1 << 34  # 16 GiB sanity ceiling
SQUASHFS_INVALID_BLK: int = 0xFFFFFFFFFFFFFFFF

SQUASHFS_COMPRESSION_NAMES: Dict[int, str] = {
    1: "GZIP",
    2: "LZMA",
    3: "LZO",
    4: "XZ",
    5: "LZ4",
    6: "ZSTD",
}

SQUASHFS_FLAG_BITS: Tuple[Tuple[int, str], ...] = (
    (0x0001, "UNCOMPRESSED_INODES"),
    (0x0002, "UNCOMPRESSED_DATA"),
    (0x0004, "CHECK"),
    (0x0008, "UNCOMPRESSED_FRAGMENTS"),
    (0x0010, "NO_FRAGMENTS"),
    (0x0020, "ALWAYS_FRAGMENTS"),
    (0x0040, "DUPLICATES"),
    (0x0080, "EXPORTABLE"),
    (0x0100, "UNCOMPRESSED_XATTRS"),
    (0x0200, "NO_XATTRS"),
    (0x0400, "COMP_OPTS"),
    (0x0800, "UNCOMPRESSED_IDS"),
)
SQUASHFS_EXPORTABLE_BIT: int = 0x0080

ERR_SQUASHFS_EMPTY_OR_TRUNCATED_HEADER: str = "SQUASHFS_EMPTY_OR_TRUNCATED_HEADER"
ERR_SQUASHFS_BLANK_OR_ERASED_FLASH: str = "SQUASHFS_BLANK_OR_ERASED_FLASH_READ"
ERR_SQUASHFS_WRONG_ENDIAN_BIG_SQSH: str = "SQUASHFS_WRONG_ENDIAN_BIG_SQSH"
ERR_SQUASHFS_BAD_MAGIC: str = "SQUASHFS_BAD_MAGIC_NOT_0X73717368"
ERR_SQUASHFS_UNSUPPORTED_VERSION: str = "SQUASHFS_UNSUPPORTED_VERSION_NOT_4_0"
ERR_SQUASHFS_INVALID_INODE_COUNT: str = "SQUASHFS_INVALID_INODE_COUNT"
ERR_SQUASHFS_INVALID_BLOCK_SIZE_OR_LOG: str = "SQUASHFS_INVALID_BLOCK_SIZE_OR_LOG"
ERR_SQUASHFS_UNSUPPORTED_COMPRESSION_ID: str = "SQUASHFS_UNSUPPORTED_COMPRESSION_ID"
ERR_SQUASHFS_INVALID_ID_COUNT: str = "SQUASHFS_INVALID_NO_IDS"
ERR_SQUASHFS_INVALID_BYTES_USED: str = "SQUASHFS_INVALID_BYTES_USED"
ERR_SQUASHFS_BYTES_USED_EXCEEDS_PARTITION: str = "SQUASHFS_BYTES_USED_EXCEEDS_PARTITION"
ERR_SQUASHFS_TRUNCATED_IMAGE_PAYLOAD: str = "SQUASHFS_TRUNCATED_IMAGE_PAYLOAD"
ERR_SQUASHFS_NON_MONOTONIC_TABLE_BOUNDS: str = "SQUASHFS_NON_MONOTONIC_TABLE_BOUNDS"
ERR_SQUASHFS_TABLE_OUT_OF_BOUNDS: str = "SQUASHFS_TABLE_OUT_OF_BOUNDS"
ERR_SQUASHFS_ROOT_INODE_OUT_OF_BOUNDS: str = "SQUASHFS_ROOT_INODE_OUT_OF_BOUNDS"

# ---------------------------------------------------------------------------
# Pillar B Constants — Sony Warp-Boot / hibdrv (WBI2) & noresume Bypass
# ---------------------------------------------------------------------------

WBI_MAGIC_VALID_ASCII: str = "WBI2"
WBI_MAGIC_VALID_BYTES: bytes = b"WBI2"
WBI_INVALIDATED_MAGICS_ASCII: Tuple[str, ...] = ("invl", "wbi2", "WBI3", "WBI0", "prof")
WBI_HEADER_SIZE: int = 88
WBI_SECTOR_SIZE: int = 512
WBI_SECTION_ENTRY_SIZE: int = 64
WBI_MAX_TABLE_READ_BYTES: int = 1024 * 1024
WBI_XOR_MASK: int = 0x0F0F0F0F
WBI_SH_ZERO: int = 0x01
WBI_PHYS_BASE: int = 0x400000000
WBI_VIRT_BASE: int = 0xFFFFFFC000000000

FX3_EXPECTED_KERNEL_UTS: str = "4.9.337-scel+ (jp10239@dic-build-scm-u20-028)"
FX6_EXPECTED_KERNEL_UTS: str = "4.9.337-scel+ (jp10239@dic-build-scm-u24-002)"
FX3_EXPECTED_INITRAMFS_HASH: str = PINNED_FX3_P1_INITRD_SQUASHFS_SHA256
FX3_SKU_NAME: str = "ILME-FX3"
FX6_SKU_NAME: str = "ILME-FX6"

ALLOWED_NORESUME_TOKENS: Tuple[str, ...] = (
    "noresume",
    "hibdrv.resume=0",
    "wbi.resume=0",
)
ALLOWED_NORESUME_INIT_PATHS: Tuple[str, ...] = (
    "/sbin/init",
    "/init",
    "/sbin/init2",
    "/sbin/init2_stage_b",
    "/tmp/stage_b/sbin/init2_stage_b",
    "/tmp/stage_b/init",
)
EMMC_BLOCK_ROOT_PREFIXES: Tuple[str, ...] = (
    "/dev/mmcblk",
    "/dev/nflasha",
    "/dev/cnflasha",
)
FORBIDDEN_REPARTITION_TOKENS: Tuple[str, ...] = ("mtdparts", "blkdevparts", "mmcparts")
FORBIDDEN_WDT_DISABLE_PARAMS: Tuple[str, ...] = (
    "nowatchdog",
    "wdt=0",
    "watchdog=0",
    "cxd90057_wdt.disable=1",
    "wdt.disable=1",
)
DEFAULT_SAFE_STAGE_B_NORESUME_BOOTARGS: str = (
    "console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait "
    "noresume hibdrv.resume=0 init=/tmp/stage_b/sbin/init2_stage_b wdt.timeout=500 mem=2G"
)

WBI_DEVICE_TARGET_TOKENS: Tuple[str, ...] = (
    "/dev/nflasha5",
    "/dev/mmcblk0p5",
    "nflasha5",
    "wbi2",
    "wbi",
    "hibdrv",
)
FORBIDDEN_WBI_WRITE_VERBS: Tuple[str, ...] = (
    "dd",
    "blkdiscard",
    "flash_erase",
    "mkfs",
    "wipefs",
    "write",
    "erase",
    "truncate",
    "invl_patch",
)

# Canonical Required Detection Codes
WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH: str = "WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH"
WBI_KERNEL_ABI_FINGERPRINT_MISMATCH: str = "WBI_KERNEL_ABI_FINGERPRINT_MISMATCH"
WBI_EPHEMERAL_NORESUME_REQUIRED: str = "WBI_EPHEMERAL_NORESUME_REQUIRED"

ERR_WBI_BAD_MAGIC: str = "WBI_BAD_OR_CORRUPT_MAGIC"
ERR_WBI_HEADER_OR_TABLE_INVALID: str = "WBI_HEADER_OR_SECTION_TABLE_INVALID"
ERR_WBI_PAGE_TABLE_RESTORE_PANIC_RISK: str = "WBI_HIBDRV_PAGE_TABLE_RESTORE_PANIC_RISK"
ERR_WBI_PERSISTENT_PARTITION_WRITE_FORBIDDEN: str = "WBI_PERSISTENT_EMMC_PARTITION_WRITE_FORBIDDEN"
ERR_NORESUME_MISSING_BYPASS_TOKEN: str = "WBI_NORESUME_BYPASS_TOKEN_MISSING"
ERR_NORESUME_RW_EMMC_OR_REPARTITION_FORBIDDEN: str = "WBI_NORESUME_BOOTARGS_UNSAFE_EMMC_WRITE"
ERR_NORESUME_WDT_DISABLED: str = "WBI_NORESUME_BOOTARGS_WDT_DISABLED"
ERR_NORESUME_UNVERIFIED_INIT: str = "WBI_NORESUME_BOOTARGS_UNVERIFIED_INIT"

WBI_SCENARIO_IDS: Tuple[str, ...] = (
    "W1_HEALTHY_STOCK_702_WBI2_MATCH",
    "W2_POWER_DROP_MID_SNAPSHOT_TRUNCATED_CRC",
    "W3_STALE_SLOT_KERNEL_UTS_OR_INITRAMFS_MISMATCH",
    "W4_STAGE_B_RAM_BOOT_NORESUME_BYPASS_ACTIVE",
    "W5_STAGE_B_RAM_BOOT_MISSING_NORESUME_REJECTED",
    "W6_PERSISTENT_WBI_ERASE_ATTEMPT_BLOCKED",
)


# ---------------------------------------------------------------------------
# Internal Helpers (Zero raw bytes fields emitted)
# ---------------------------------------------------------------------------


def _canonical_sha256(obj: Any) -> str:
    encoded = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
        "utf-8"
    )
    return sha256(encoded).hexdigest()


def _safe_ascii_magic(raw4: bytes) -> str:
    return "".join(chr(b) if 32 <= b <= 126 else "?" for b in raw4)


def _read_bounded_wbi2_readonly(path: Path) -> Tuple[int, bytes, bytes, Dict[str, Any]]:
    """Open WBI2 partition file strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` and read bounded header + section table."""
    p = local_path(path, allow_donor_roots=True)
    require(hasattr(os, "O_NOFOLLOW"), "POSIX O_NOFOLLOW is required")
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "single-link regular file required")
        require(before.st_size >= WBI_SECTOR_SIZE, f"WBI2 file truncated before 512B header: {before.st_size}")

        os.lseek(fd, 0, os.SEEK_SET)
        hdr = os.read(fd, WBI_SECTOR_SIZE)
        require(len(hdr) == WBI_SECTOR_SIZE, "short read on 512B WBI2 header")

        magic, padding, sections, flag, resume_vector, d_version, sector_size, r_data_size, kern_start, kern_size, kern_cksum, o_data_size = struct.unpack_from(
            "<4sI10Q", hdr, 0
        )
        require(magic == WBI_MAGIC_VALID_BYTES, f"expected WBI2 magic, got {hdr[:4].hex()}")
        require(padding == 0 and sector_size == WBI_SECTOR_SIZE, "unexpected WBI2 padding or sector_size")
        require(0 < sections <= 16384, f"out-of-bounds WBI2 section count: {sections}")

        table_offset = WBI_SECTOR_SIZE + r_data_size
        table_bytes_len = WBI_SECTION_ENTRY_SIZE * sections
        require(table_bytes_len <= WBI_MAX_TABLE_READ_BYTES, "WBI2 section table exceeds bounded read limit")
        require(table_offset + table_bytes_len <= before.st_size, "WBI2 section table exceeds file size")

        os.lseek(fd, table_offset, os.SEEK_SET)
        chunks: List[bytes] = []
        rem = table_bytes_len
        while rem > 0:
            chunk = os.read(fd, rem)
            if not chunk:
                break
            chunks.append(chunk)
            rem -= len(chunk)
        table_bytes = b"".join(chunks)
        require(len(table_bytes) == table_bytes_len, "short read on WBI2 section table")

        after = os.fstat(fd)
        for fld in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode", "st_nlink"):
            require(getattr(before, fld) == getattr(after, fld), "WBI2 donor file changed during read")

        meta = {
            "sections": sections,
            "flag": flag,
            "resume_vector": resume_vector,
            "d_version": d_version,
            "sector_size": sector_size,
            "r_data_size": r_data_size,
            "o_data_size": o_data_size,
            "table_offset": table_offset,
            "table_end": table_offset + table_bytes_len,
        }
        return before.st_size, hdr, table_bytes, meta
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Structured Dataclasses (Zero raw bytes fields)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SquashfsWbiDonorArtifactDigest:
    label: str
    relpath: str
    source_mode: str
    byte_length: int
    sha256: str
    details: str


@dataclass(frozen=True)
class DonorSquashfsWbiSnapshot:
    verification_mode: str
    read_only_access: bool
    fx3_p1_initrd_squashfs_sha256: str
    fx3_udtrbody_squashfs_sha256: str
    fx6_updater_squashfs_sha256: str
    fx3_wbi2_hdr_sha256: str
    fx3_wbi2_table_sha256: str
    fx3_wbi2_sections: int
    fx6_wbi2_hdr_sha256: str
    fx6_wbi2_table_sha256: str
    fx6_wbi2_sections: int
    fx3_vmlinux_sha256: str
    fx6_vmlinux_sha256: str
    fx3_uts_marker: str
    fx6_uts_marker: str
    artifacts: Tuple[SquashfsWbiDonorArtifactDigest, ...]
    snapshot_sha256: str


@dataclass(frozen=True)
class SquashfsSuperblockInfo:
    s_magic: int
    s_magic_hex: str
    s_magic_ascii: str
    inodes: int
    mkfs_time: int
    block_size: int
    fragments: int
    compression_id: int
    compression_name: str
    block_log: int
    flags: int
    flag_names: Tuple[str, ...]
    no_ids: int
    s_major: int
    s_minor: int
    root_inode: int
    root_inode_hex: str
    bytes_used: int
    id_table_start: int
    xattr_table_start: int
    inode_table_start: int
    directory_table_start: int
    fragment_table_start: int
    export_table_start: int


@dataclass(frozen=True)
class SquashfsVerificationReport:
    passed: bool
    status: str
    label: str
    actual_bytes: int
    partition_size: int
    image_sha256: str
    superblock: Optional[SquashfsSuperblockInfo]
    truncated_flash_detected: bool
    sigbus_or_vfs_mount_loop_risk: bool
    recommended_action: str
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WbiHeaderInfo:
    magic_ascii: str
    magic_hex: str
    padding: int
    sections: int
    flag: int
    resume_vector: int
    resume_vector_hex: str
    d_version: int
    sector_size: int
    r_data_size: int
    kern_start: int
    kern_size: int
    kern_cksum: int
    o_data_size: int
    table_offset: int
    table_end: int


@dataclass(frozen=True)
class WbiSnapshotEnvelope:
    header_bytes: bytes
    section_table_bytes: Optional[bytes] = None
    available_bytes: Optional[int] = None
    expected_total_bytes: Optional[int] = None
    declared_crc32: Optional[int] = None
    computed_crc32: Optional[int] = None
    kernel_uts_version: str = FX3_EXPECTED_KERNEL_UTS
    kernel_build_fingerprint: str = PINNED_FX3_VMLINUX_KERNEL_SHA256
    initramfs_layout_hash: str = FX3_EXPECTED_INITRAMFS_HASH
    firmware_slot_version: str = "7.02"
    sku_code: str = FX3_SKU_NAME


@dataclass(frozen=True)
class WbiActiveBootContext:
    kernel_uts_version: str = FX3_EXPECTED_KERNEL_UTS
    kernel_build_fingerprint: str = PINNED_FX3_VMLINUX_KERNEL_SHA256
    initramfs_layout_hash: str = FX3_EXPECTED_INITRAMFS_HASH
    firmware_slot_version: str = "7.02"
    sku_code: str = FX3_SKU_NAME
    stage_b_ram_boot: bool = False
    bootargs: str = "console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait init=/sbin/init"


@dataclass(frozen=True)
class EphemeralNoresumeAuditReport:
    passed: bool
    status: str
    bootargs_raw: str
    tokens: Tuple[str, ...]
    has_noresume: bool
    has_hibdrv_resume_zero: bool
    has_ro: bool
    has_rw_emmc: bool
    has_rootwait: bool
    init_path: Optional[str]
    init_verified: bool
    has_repartitioning: bool
    has_wdt_disable: bool
    wbi_partition_writes: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WbiWriteFirewallDecision:
    allowed: bool
    status: str
    target_partition: str
    operation: str
    wbi_partition_writes: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WbiTriageReport:
    passed: bool
    triage_classified: bool
    status: str
    scenario_id: str
    header_info: Optional[WbiHeaderInfo]
    wbi_active_magic: str
    snapshot_truncated_or_crc_mismatch: bool
    kernel_abi_fingerprint_mismatch: bool
    ephemeral_noresume_required: bool
    page_table_restore_panic_risk: bool
    noresume_bypass_active: bool
    bootargs_bypass_verified: bool
    recommended_bootargs: str
    recommended_action: str
    wbi_partition_writes: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Wbi6ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[WbiTriageReport, ...]
    write_firewall_decision: WbiWriteFirewallDecision
    errors: Tuple[str, ...]
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SquashfsAndHibdrvWbiSuiteReport:
    schema: str
    version: str
    status: str
    verification_mode: str
    all_passed: bool
    read_only_donor_access: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    otp_fuse_touches: int
    passive_tx_bytes_emitted: int
    physical_device_writes: int
    wbi_partition_writes: int
    donor_snapshot: DonorSquashfsWbiSnapshot
    squashfs_compression_reports: Tuple[SquashfsVerificationReport, ...]
    squashfs_truncated_rejected: SquashfsVerificationReport
    squashfs_non_monotonic_rejected: SquashfsVerificationReport
    squashfs_bad_blocklog_rejected: SquashfsVerificationReport
    squashfs_bad_compression_rejected: SquashfsVerificationReport
    squashfs_big_endian_rejected: SquashfsVerificationReport
    wbi_6_scenario_suite: Wbi6ScenarioSuiteResult
    ephemeral_noresume_valid_report: EphemeralNoresumeAuditReport
    ephemeral_noresume_missing_rejected: EphemeralNoresumeAuditReport
    suite_sha256: str
    elapsed_seconds: float
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Pillar A — SquashFS 4.0 Superblock Builder & Verifier
# ---------------------------------------------------------------------------


def build_synthetic_squashfs_superblock(
    *,
    s_magic: int = SQUASHFS_MAGIC,
    inodes: int = 128,
    mkfs_time: int = 1711719305,
    block_size: int = 131072,
    fragments: int = 4,
    compression_id: int = 1,
    block_log: int = 17,
    flags: int = 0x00C0,
    no_ids: int = 2,
    s_major: int = 4,
    s_minor: int = 0,
    root_inode: Optional[int] = None,
    bytes_used: int = 4096,
    id_table_start: int = 4080,
    xattr_table_start: int = SQUASHFS_INVALID_BLK,
    inode_table_start: int = 3072,
    directory_table_start: int = 3584,
    fragment_table_start: int = 3968,
    export_table_start: int = 4032,
    payload_size: Optional[int] = None,
) -> bytes:
    """Build a synthetic SquashFS 4.0 image buffer in RAM for deterministic unit testing."""
    if root_inode is None:
        root_inode = (0 << 16) | 0
    header = struct.pack(
        "<5I6H8Q",
        s_magic & 0xFFFFFFFF,
        inodes & 0xFFFFFFFF,
        mkfs_time & 0xFFFFFFFF,
        block_size & 0xFFFFFFFF,
        fragments & 0xFFFFFFFF,
        compression_id & 0xFFFF,
        block_log & 0xFFFF,
        flags & 0xFFFF,
        no_ids & 0xFFFF,
        s_major & 0xFFFF,
        s_minor & 0xFFFF,
        root_inode & 0xFFFFFFFFFFFFFFFF,
        bytes_used & 0xFFFFFFFFFFFFFFFF,
        id_table_start & 0xFFFFFFFFFFFFFFFF,
        xattr_table_start & 0xFFFFFFFFFFFFFFFF,
        inode_table_start & 0xFFFFFFFFFFFFFFFF,
        directory_table_start & 0xFFFFFFFFFFFFFFFF,
        fragment_table_start & 0xFFFFFFFFFFFFFFFF,
        export_table_start & 0xFFFFFFFFFFFFFFFF,
    )
    target_len = max(SQUASHFS_SUPERBLOCK_SIZE, bytes_used) if payload_size is None else payload_size
    if target_len <= SQUASHFS_SUPERBLOCK_SIZE:
        return header[:target_len]
    out = bytearray(target_len)
    out[:SQUASHFS_SUPERBLOCK_SIZE] = header
    return bytes(out)


def _decode_squashfs_flags(flags: int) -> Tuple[str, ...]:
    return tuple(name for bit, name in SQUASHFS_FLAG_BITS if flags & bit)


def verify_squashfs_partition_bytes(
    data: bytes,
    *,
    partition_size: Optional[int] = None,
    label: str = "squashfs_partition",
    allowed_compression_ids: Optional[Sequence[int]] = None,
) -> SquashfsVerificationReport:
    """Parse and validate a SquashFS 4.0 (`hsqs` 0x73717368) superblock & table bounds strictly in RAM."""
    actual_bytes = len(data)
    effective_partition_size = partition_size if partition_size is not None else actual_bytes
    img_sha = sha256(data).hexdigest()
    error_codes: List[str] = []
    errors: List[str] = []

    def _add_err(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    if actual_bytes == 0:
        _add_err(ERR_SQUASHFS_EMPTY_OR_TRUNCATED_HEADER, "Empty SquashFS partition buffer (0 bytes).")
        return SquashfsVerificationReport(
            passed=False,
            status=STATUS_REJECTED_SQUASHFS_SUPERBLOCK,
            label=label,
            actual_bytes=actual_bytes,
            partition_size=effective_partition_size,
            image_sha256=img_sha,
            superblock=None,
            truncated_flash_detected=True,
            sigbus_or_vfs_mount_loop_risk=True,
            recommended_action="ABORT_MOUNT_AND_TIER0_READONLY_INSPECT_OR_STAGE_B_STOCK_ESCAPE",
            error_codes=tuple(error_codes),
            errors=tuple(errors),
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
        )

    probe_len = min(actual_bytes, SQUASHFS_SUPERBLOCK_SIZE)
    probe = data[:probe_len]
    if all(b == 0x00 for b in probe) or all(b == 0xFF for b in probe):
        _add_err(
            ERR_SQUASHFS_BLANK_OR_ERASED_FLASH,
            f"All-0x{probe[0]:02x} blank/erased flash detected in first {probe_len} bytes.",
        )
        return SquashfsVerificationReport(
            passed=False,
            status=STATUS_REJECTED_SQUASHFS_SUPERBLOCK,
            label=label,
            actual_bytes=actual_bytes,
            partition_size=effective_partition_size,
            image_sha256=img_sha,
            superblock=None,
            truncated_flash_detected=True,
            sigbus_or_vfs_mount_loop_risk=True,
            recommended_action="DO_NOT_BOOT_CORRUPT_ROOTFS_CHECK_AB_FALLBACK_OR_TIER0_BACKUP",
            error_codes=tuple(error_codes),
            errors=tuple(errors),
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
        )

    if actual_bytes < SQUASHFS_SUPERBLOCK_SIZE:
        _add_err(
            ERR_SQUASHFS_EMPTY_OR_TRUNCATED_HEADER,
            f"Truncated SquashFS superblock: {actual_bytes} < {SQUASHFS_SUPERBLOCK_SIZE} bytes.",
        )
        return SquashfsVerificationReport(
            passed=False,
            status=STATUS_REJECTED_SQUASHFS_SUPERBLOCK,
            label=label,
            actual_bytes=actual_bytes,
            partition_size=effective_partition_size,
            image_sha256=img_sha,
            superblock=None,
            truncated_flash_detected=True,
            sigbus_or_vfs_mount_loop_risk=True,
            recommended_action="REJECT_TRUNCATED_SQUASHFS_HEADER_PREVENT_VFS_MOUNT_PANIC",
            error_codes=tuple(error_codes),
            errors=tuple(errors),
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
        )

    (
        s_magic,
        inodes,
        mkfs_time,
        block_size,
        fragments,
        compression_id,
        block_log,
        flags,
        no_ids,
        s_major,
        s_minor,
        root_inode,
        bytes_used,
        id_table_start,
        xattr_table_start,
        inode_table_start,
        directory_table_start,
        fragment_table_start,
        export_table_start,
    ) = struct.unpack_from("<5I6H8Q", data, 0)

    comp_name = SQUASHFS_COMPRESSION_NAMES.get(compression_id, f"UNKNOWN({compression_id})")
    sb = SquashfsSuperblockInfo(
        s_magic=s_magic,
        s_magic_hex=f"0x{s_magic:08x}",
        s_magic_ascii=_safe_ascii_magic(data[0:4]),
        inodes=inodes,
        mkfs_time=mkfs_time,
        block_size=block_size,
        fragments=fragments,
        compression_id=compression_id,
        compression_name=comp_name,
        block_log=block_log,
        flags=flags,
        flag_names=_decode_squashfs_flags(flags),
        no_ids=no_ids,
        s_major=s_major,
        s_minor=s_minor,
        root_inode=root_inode,
        root_inode_hex=f"0x{root_inode:016x}",
        bytes_used=bytes_used,
        id_table_start=id_table_start,
        xattr_table_start=xattr_table_start,
        inode_table_start=inode_table_start,
        directory_table_start=directory_table_start,
        fragment_table_start=fragment_table_start,
        export_table_start=export_table_start,
    )

    if s_magic == SQUASHFS_MAGIC_BE:
        _add_err(
            ERR_SQUASHFS_WRONG_ENDIAN_BIG_SQSH,
            f"Big-endian SquashFS magic 0x{s_magic:08x} ('sqsh') rejected; CXD90057 requires little-endian 0x73717368 ('hsqs').",
        )
    elif s_magic != SQUASHFS_MAGIC:
        _add_err(
            ERR_SQUASHFS_BAD_MAGIC,
            f"Invalid SquashFS magic 0x{s_magic:08x} (expected 0x{SQUASHFS_MAGIC:08x} 'hsqs').",
        )

    if (s_major, s_minor) != (SQUASHFS_MAJOR_VERSION, SQUASHFS_MINOR_VERSION):
        _add_err(
            ERR_SQUASHFS_UNSUPPORTED_VERSION,
            f"Unsupported SquashFS version {s_major}.{s_minor} (expected 4.0).",
        )

    if inodes == 0 or inodes > SQUASHFS_MAX_INODES:
        _add_err(
            ERR_SQUASHFS_INVALID_INODE_COUNT,
            f"Invalid SquashFS inode count {inodes} (expected 1..{SQUASHFS_MAX_INODES}).",
        )

    is_pow2 = block_size > 0 and (block_size & (block_size - 1)) == 0
    if not (
        is_pow2
        and SQUASHFS_MIN_BLOCK_SIZE <= block_size <= SQUASHFS_MAX_BLOCK_SIZE
        and SQUASHFS_MIN_BLOCK_LOG <= block_log <= SQUASHFS_MAX_BLOCK_LOG
        and block_size == (1 << block_log)
    ):
        _add_err(
            ERR_SQUASHFS_INVALID_BLOCK_SIZE_OR_LOG,
            f"Invalid block_size={block_size} / block_log={block_log} (must be power-of-two 4 KiB..1 MiB with block_size == 1<<block_log).",
        )

    allowed_ids = set(SQUASHFS_COMPRESSION_NAMES.keys()) if allowed_compression_ids is None else set(allowed_compression_ids)
    if compression_id not in SQUASHFS_COMPRESSION_NAMES or compression_id not in allowed_ids:
        _add_err(
            ERR_SQUASHFS_UNSUPPORTED_COMPRESSION_ID,
            f"Unsupported SquashFS compression_id={compression_id} ({comp_name}).",
        )

    if no_ids == 0:
        _add_err(ERR_SQUASHFS_INVALID_ID_COUNT, "SquashFS no_ids must be >= 1.")

    truncated_flash = False
    if bytes_used <= SQUASHFS_SUPERBLOCK_SIZE or bytes_used > SQUASHFS_MAX_BYTES_USED:
        _add_err(
            ERR_SQUASHFS_INVALID_BYTES_USED,
            f"Invalid SquashFS bytes_used={bytes_used} (must be > {SQUASHFS_SUPERBLOCK_SIZE}).",
        )
    else:
        if partition_size is not None and bytes_used > partition_size:
            truncated_flash = True
            _add_err(
                ERR_SQUASHFS_BYTES_USED_EXCEEDS_PARTITION,
                f"SquashFS bytes_used={bytes_used} exceeds partition_size={partition_size}.",
            )
        if actual_bytes < bytes_used:
            truncated_flash = True
            _add_err(
                ERR_SQUASHFS_TRUNCATED_IMAGE_PAYLOAD,
                f"Truncated SquashFS flash: actual_bytes={actual_bytes} < superblock bytes_used={bytes_used}.",
            )

    # Validate table offsets and strict monotonic ordering within [96, bytes_used]
    if bytes_used > SQUASHFS_SUPERBLOCK_SIZE:
        if not (SQUASHFS_SUPERBLOCK_SIZE <= inode_table_start < bytes_used):
            _add_err(
                ERR_SQUASHFS_TABLE_OUT_OF_BOUNDS,
                f"inode_table_start={inode_table_start} outside [96, {bytes_used}).",
            )
        if not (SQUASHFS_SUPERBLOCK_SIZE <= directory_table_start < bytes_used):
            _add_err(
                ERR_SQUASHFS_TABLE_OUT_OF_BOUNDS,
                f"directory_table_start={directory_table_start} outside [96, {bytes_used}).",
            )
        if inode_table_start >= directory_table_start:
            _add_err(
                ERR_SQUASHFS_NON_MONOTONIC_TABLE_BOUNDS,
                f"Non-monotonic tables: inode_table_start={inode_table_start} >= directory_table_start={directory_table_start}.",
            )

        cursor = directory_table_start

        # Fragment table
        if fragments > 0:
            if fragment_table_start == SQUASHFS_INVALID_BLK or fragment_table_start >= bytes_used:
                _add_err(
                    ERR_SQUASHFS_TABLE_OUT_OF_BOUNDS,
                    f"fragments={fragments} > 0 but fragment_table_start={fragment_table_start} out of bounds.",
                )
            elif fragment_table_start < cursor:
                _add_err(
                    ERR_SQUASHFS_NON_MONOTONIC_TABLE_BOUNDS,
                    f"Non-monotonic fragment_table_start={fragment_table_start} < directory_table_start={cursor}.",
                )
            else:
                cursor = fragment_table_start
        elif fragment_table_start != SQUASHFS_INVALID_BLK:
            if fragment_table_start > bytes_used:
                _add_err(
                    ERR_SQUASHFS_TABLE_OUT_OF_BOUNDS,
                    f"fragment_table_start={fragment_table_start} > bytes_used={bytes_used}.",
                )
            elif fragment_table_start < cursor:
                _add_err(
                    ERR_SQUASHFS_NON_MONOTONIC_TABLE_BOUNDS,
                    f"Non-monotonic fragment_table_start={fragment_table_start} < directory_table_start={cursor}.",
                )
            else:
                cursor = fragment_table_start

        # Export (lookup) table
        if flags & SQUASHFS_EXPORTABLE_BIT:
            if export_table_start == SQUASHFS_INVALID_BLK or export_table_start >= bytes_used:
                _add_err(
                    ERR_SQUASHFS_TABLE_OUT_OF_BOUNDS,
                    f"EXPORTABLE flag set but export_table_start={export_table_start} out of bounds.",
                )
            elif export_table_start < cursor:
                _add_err(
                    ERR_SQUASHFS_NON_MONOTONIC_TABLE_BOUNDS,
                    f"Non-monotonic export_table_start={export_table_start} < previous_table={cursor}.",
                )
            else:
                cursor = export_table_start
        elif export_table_start != SQUASHFS_INVALID_BLK:
            if export_table_start > bytes_used:
                _add_err(
                    ERR_SQUASHFS_TABLE_OUT_OF_BOUNDS,
                    f"export_table_start={export_table_start} > bytes_used={bytes_used}.",
                )
            elif export_table_start < cursor:
                _add_err(
                    ERR_SQUASHFS_NON_MONOTONIC_TABLE_BOUNDS,
                    f"Non-monotonic export_table_start={export_table_start} < previous_table={cursor}.",
                )
            else:
                cursor = export_table_start

        # ID table (always required since no_ids >= 1)
        if id_table_start == SQUASHFS_INVALID_BLK or id_table_start >= bytes_used:
            _add_err(
                ERR_SQUASHFS_TABLE_OUT_OF_BOUNDS,
                f"id_table_start={id_table_start} outside [96, {bytes_used}).",
            )
        elif id_table_start < cursor:
            _add_err(
                ERR_SQUASHFS_NON_MONOTONIC_TABLE_BOUNDS,
                f"Non-monotonic id_table_start={id_table_start} < previous_table={cursor}.",
            )
        else:
            cursor = id_table_start

        # Optional xattr table
        if xattr_table_start != SQUASHFS_INVALID_BLK:
            if xattr_table_start >= bytes_used:
                _add_err(
                    ERR_SQUASHFS_TABLE_OUT_OF_BOUNDS,
                    f"xattr_table_start={xattr_table_start} >= bytes_used={bytes_used}.",
                )
            elif xattr_table_start < cursor:
                _add_err(
                    ERR_SQUASHFS_NON_MONOTONIC_TABLE_BOUNDS,
                    f"Non-monotonic xattr_table_start={xattr_table_start} < id_table_start={cursor}.",
                )

        # Root inode reference block offset must fall inside inode table span
        root_block_rel = root_inode >> 16
        if (
            inode_table_start < directory_table_start < bytes_used
            and inode_table_start + root_block_rel >= directory_table_start
        ):
            _add_err(
                ERR_SQUASHFS_ROOT_INODE_OUT_OF_BOUNDS,
                f"root_inode block offset {root_block_rel} exceeds inode table span [{inode_table_start}, {directory_table_start}).",
            )

    passed = len(errors) == 0
    risk = not passed
    action = (
        "SQUASHFS_4_0_SUPERBLOCK_AND_TABLE_BOUNDS_VERIFIED_READONLY"
        if passed
        else (
            "ABORT_FLASH_OR_MOUNT_TRUNCATED_SQUASHFS_PREVENTS_INIT2_SIGBUS_OR_VFS_PANIC"
            if truncated_flash
            else "REJECT_INVALID_SQUASHFS_SUPERBLOCK_FALLBACK_TO_INTACT_SLOT_OR_STAGE_B"
        )
    )
    return SquashfsVerificationReport(
        passed=passed,
        status=STATUS_VERIFIED_SQUASHFS_SUPERBLOCK if passed else STATUS_REJECTED_SQUASHFS_SUPERBLOCK,
        label=label,
        actual_bytes=actual_bytes,
        partition_size=effective_partition_size,
        image_sha256=img_sha,
        superblock=sb,
        truncated_flash_detected=truncated_flash,
        sigbus_or_vfs_mount_loop_risk=risk,
        recommended_action=action,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
    )


# ---------------------------------------------------------------------------
# Pillar B — Sony Warp-Boot / hibdrv (WBI2) Stale-Resume Triage & noresume
# ---------------------------------------------------------------------------


def build_synthetic_wbi2_snapshot_bytes(
    *,
    magic: bytes = WBI_MAGIC_VALID_BYTES,
    padding: int = 0,
    sections: int = 4,
    flag: int = 0,
    sector_size: int = WBI_SECTOR_SIZE,
    zero_section_indices: Sequence[int] = (3,),
    corrupt_meta_xor_index: Optional[int] = None,
    truncate_after_bytes: Optional[int] = None,
    section_olen: int = 4096,
    base_phys_addr: int = WBI_PHYS_BASE,
) -> Tuple[bytes, bytes, int]:
    """Build a synthetic 512B WBI2 header + section payload + 64B section table in RAM.

    Returns `(full_or_truncated_image_bytes, section_table_bytes, crc32_of_full_image)`.
    """
    require(len(magic) == 4, "WBI magic must be 4 bytes")
    require(sections > 0, "sections must be > 0")
    require(section_olen > 0 and section_olen % 4096 == 0, "section_olen must be 4K-aligned")

    zero_set = set(zero_section_indices)
    data_chunks: List[bytes] = []
    table_chunks: List[bytes] = []
    r_data_size = 0
    o_data_size = 0
    resume_vector = base_phys_addr + 0x100

    for idx in range(sections):
        addr = base_phys_addr + idx * section_olen
        virt = addr - WBI_PHYS_BASE + WBI_VIRT_BASE
        sflag = WBI_SH_ZERO if idx in zero_set else 0
        olen = section_olen
        rlen = 0 if sflag == WBI_SH_ZERO else olen
        cksum = WBI_XOR_MASK
        meta_cksum = WBI_XOR_MASK ^ addr ^ rlen ^ cksum ^ sflag ^ olen ^ virt
        if corrupt_meta_xor_index is not None and idx == corrupt_meta_xor_index:
            meta_cksum ^= 0x12345678
        if sflag == 0:
            data_chunks.append(bytes([((idx + 17) * 31) & 0xFF]) * rlen)
            if idx == 0:
                resume_vector = addr + 0x100
        table_chunks.append(struct.pack("<8Q", addr, rlen, cksum, sflag, olen, virt, meta_cksum, 0))
        r_data_size += rlen
        o_data_size += olen

    d_version = 0x20060004
    kern_start = 0
    kern_size = 0
    kern_cksum = WBI_XOR_MASK
    hdr_88 = struct.pack(
        "<4sI10Q",
        magic,
        padding,
        sections,
        flag,
        resume_vector,
        d_version,
        sector_size,
        r_data_size,
        kern_start,
        kern_size,
        kern_cksum,
        o_data_size,
    )
    hdr_512 = hdr_88 + bytes(WBI_SECTOR_SIZE - len(hdr_88))
    table_bytes = b"".join(table_chunks)
    full_bytes = hdr_512 + b"".join(data_chunks) + table_bytes
    full_crc = zlib.crc32(full_bytes) & 0xFFFFFFFF
    if truncate_after_bytes is not None:
        full_bytes = full_bytes[:truncate_after_bytes]
    return full_bytes, table_bytes, full_crc


def parse_wbi2_header_and_table(
    header_bytes: bytes,
    *,
    section_table_bytes: Optional[bytes] = None,
    available_bytes: Optional[int] = None,
) -> Tuple[Optional[WbiHeaderInfo], List[str], List[str]]:
    """Parse an 88B/512B WBI2 header and optional 64B-entry section table strictly in RAM."""
    error_codes: List[str] = []
    errors: List[str] = []

    def _add(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    eff_avail = len(header_bytes) if available_bytes is None else available_bytes
    if len(header_bytes) < WBI_HEADER_SIZE:
        _add(
            WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH,
            f"WBI header truncated: {len(header_bytes)} < {WBI_HEADER_SIZE} bytes.",
        )
        return None, error_codes, errors

    (
        magic_raw,
        padding,
        sections,
        flag,
        resume_vector,
        d_version,
        sector_size,
        r_data_size,
        kern_start,
        kern_size,
        kern_cksum,
        o_data_size,
    ) = struct.unpack_from("<4sI10Q", header_bytes, 0)

    magic_ascii = _safe_ascii_magic(magic_raw)
    table_off = WBI_SECTOR_SIZE + r_data_size
    table_end = table_off + WBI_SECTION_ENTRY_SIZE * sections
    info = WbiHeaderInfo(
        magic_ascii=magic_ascii,
        magic_hex=magic_raw.hex(),
        padding=padding,
        sections=sections,
        flag=flag,
        resume_vector=resume_vector,
        resume_vector_hex=f"0x{resume_vector:x}",
        d_version=d_version,
        sector_size=sector_size,
        r_data_size=r_data_size,
        kern_start=kern_start,
        kern_size=kern_size,
        kern_cksum=kern_cksum,
        o_data_size=o_data_size,
        table_offset=table_off,
        table_end=table_end,
    )

    if magic_ascii in WBI_INVALIDATED_MAGICS_ASCII:
        return info, error_codes, errors

    if magic_raw != WBI_MAGIC_VALID_BYTES:
        _add(ERR_WBI_BAD_MAGIC, f"Invalid WBI magic '{magic_ascii}' (0x{magic_raw.hex()}), expected 'WBI2'.")
        return info, error_codes, errors

    if padding != 0:
        _add(ERR_WBI_HEADER_OR_TABLE_INVALID, f"Non-zero WBI2 header padding: {padding}.")
    if sector_size != WBI_SECTOR_SIZE:
        _add(ERR_WBI_HEADER_OR_TABLE_INVALID, f"Invalid WBI2 sector_size={sector_size}, expected {WBI_SECTOR_SIZE}.")
    if sections == 0 or sections > 100000:
        _add(ERR_WBI_HEADER_OR_TABLE_INVALID, f"Invalid WBI2 section count={sections}.")
        return info, error_codes, errors

    if eff_avail < table_end:
        _add(
            WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH,
            f"WBI2 snapshot truncated mid-write: available_bytes={eff_avail} < table_end={table_end}.",
        )

    tbl = section_table_bytes
    if tbl is None and len(header_bytes) >= table_end:
        tbl = header_bytes[table_off:table_end]

    if tbl is not None:
        expected_tbl_len = WBI_SECTION_ENTRY_SIZE * sections
        if len(tbl) < expected_tbl_len:
            _add(
                WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH,
                f"WBI2 section table truncated: got {len(tbl)} bytes, expected {expected_tbl_len}.",
            )
        else:
            at = WBI_SECTOR_SIZE
            total_olen = 0
            resume_covered = False
            spans: List[Tuple[int, int]] = []
            for idx in range(sections):
                addr, rlen, cksum, sflag, olen, virt, meta_cksum, spadding = struct.unpack_from(
                    "<8Q", tbl, idx * WBI_SECTION_ENTRY_SIZE
                )
                if addr % 4096 != 0 or olen == 0 or olen % 4096 != 0:
                    _add(ERR_WBI_HEADER_OR_TABLE_INVALID, f"WBI2 section {idx} unaligned (addr=0x{addr:x}, olen={olen}).")
                    break
                if sflag not in (0, 1) or spadding != 0:
                    _add(ERR_WBI_HEADER_OR_TABLE_INVALID, f"WBI2 section {idx} invalid flag/padding.")
                    break
                if (sflag == 0 and rlen != olen) or (sflag == 1 and rlen != 0):
                    _add(ERR_WBI_HEADER_OR_TABLE_INVALID, f"WBI2 section {idx} rlen/olen mismatch.")
                    break
                expected_meta = WBI_XOR_MASK ^ addr ^ rlen ^ cksum ^ sflag ^ olen ^ virt
                if meta_cksum != expected_meta:
                    _add(
                        WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH,
                        f"WBI2 section {idx} XOR metadata checksum mismatch (got 0x{meta_cksum:x}, expected 0x{expected_meta:x}).",
                    )
                    break
                if at + rlen > table_off:
                    _add(WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH, f"WBI2 section {idx} overruns stored data offset.")
                    break
                if sflag == 0 and addr <= resume_vector < addr + rlen:
                    resume_covered = True
                spans.append((addr, addr + olen))
                total_olen += olen
                at += rlen
            else:
                if at != table_off:
                    _add(
                        WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH,
                        f"WBI2 stored data cursor mismatch: at={at} != table_off={table_off}.",
                    )
                if total_olen != o_data_size:
                    _add(
                        WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH,
                        f"WBI2 total original data size mismatch: sum={total_olen} != header={o_data_size}.",
                    )
                if not resume_covered:
                    _add(
                        ERR_WBI_HEADER_OR_TABLE_INVALID,
                        f"WBI2 resume_vector 0x{resume_vector:x} not covered by non-zero section.",
                    )
                spans.sort()
                for a, b in zip(spans, spans[1:]):
                    if a[1] > b[0]:
                        _add(
                            ERR_WBI_HEADER_OR_TABLE_INVALID,
                            f"WBI2 physical section overlap detected around 0x{a[0]:x}..0x{a[1]:x}.",
                        )
                        break

    return info, error_codes, errors


def verify_ephemeral_noresume_bootargs_bypass(
    bootargs: str,
    *,
    require_noresume: bool = True,
) -> EphemeralNoresumeAuditReport:
    """Audit RAM-only kernel `bootargs` for ephemeral `noresume`/`hibdrv.resume=0` bypass & read-only eMMC safety."""
    error_codes: List[str] = []
    errors: List[str] = []

    raw = (bootargs or "").strip()
    try:
        tokens = tuple(shlex.split(raw)) if raw else ()
    except ValueError:
        tokens = tuple(raw.split())

    has_noresume = "noresume" in tokens
    has_hibdrv_resume_zero = any(tok in ("hibdrv.resume=0", "wbi.resume=0") for tok in tokens)
    has_ro = "ro" in tokens
    has_rw = "rw" in tokens
    has_rootwait = "rootwait" in tokens

    root_dev: Optional[str] = None
    init_path: Optional[str] = None
    has_repartitioning = False
    has_wdt_disable = False

    for tok in tokens:
        if tok.startswith("root="):
            root_dev = tok.split("=", 1)[1]
        elif tok.startswith("init="):
            init_path = tok.split("=", 1)[1]
        elif tok.startswith("rdinit=") and init_path is None:
            init_path = tok.split("=", 1)[1]
        key = tok.split("=", 1)[0]
        if key in FORBIDDEN_REPARTITION_TOKENS:
            has_repartitioning = True
        if tok in FORBIDDEN_WDT_DISABLE_PARAMS:
            has_wdt_disable = True

    rootfs_is_emmc = bool(root_dev and root_dev.startswith(EMMC_BLOCK_ROOT_PREFIXES))
    has_rw_emmc = bool(rootfs_is_emmc and has_rw)

    if require_noresume and not (has_noresume or has_hibdrv_resume_zero):
        error_codes.append(ERR_NORESUME_MISSING_BYPASS_TOKEN)
        errors.append("RAM-only Stage-B/recovery bootargs missing required 'noresume' or 'hibdrv.resume=0' bypass token.")

    if rootfs_is_emmc and (has_rw or not has_ro or not has_rootwait):
        error_codes.append(ERR_NORESUME_RW_EMMC_OR_REPARTITION_FORBIDDEN)
        errors.append("eMMC rootfs in bootargs must strictly specify 'ro' and 'rootwait' (never 'rw').")

    if has_repartitioning:
        if ERR_NORESUME_RW_EMMC_OR_REPARTITION_FORBIDDEN not in error_codes:
            error_codes.append(ERR_NORESUME_RW_EMMC_OR_REPARTITION_FORBIDDEN)
        errors.append("Forbidden eMMC repartitioning parameter (mtdparts/blkdevparts/mmcparts) detected.")

    if has_wdt_disable:
        error_codes.append(ERR_NORESUME_WDT_DISABLED)
        errors.append("Forbidden watchdog-disable flag detected in bootargs.")

    init_verified = init_path is None or init_path in ALLOWED_NORESUME_INIT_PATHS
    if not init_verified:
        error_codes.append(ERR_NORESUME_UNVERIFIED_INIT)
        errors.append(f"Unverified init path '{init_path}' rejected in RAM-only bootargs.")

    passed = len(errors) == 0
    return EphemeralNoresumeAuditReport(
        passed=passed,
        status=STATUS_VERIFIED_EPHEMERAL_NORESUME_BYPASS if passed else STATUS_REJECTED_EPHEMERAL_NORESUME_BYPASS,
        bootargs_raw=raw,
        tokens=tokens,
        has_noresume=has_noresume,
        has_hibdrv_resume_zero=has_hibdrv_resume_zero,
        has_ro=has_ro,
        has_rw_emmc=has_rw_emmc,
        has_rootwait=has_rootwait,
        init_path=init_path,
        init_verified=init_verified,
        has_repartitioning=has_repartitioning,
        has_wdt_disable=has_wdt_disable,
        wbi_partition_writes=WBI_PARTITION_WRITES,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
    )


def audit_wbi_partition_write_attempt(target: str, operation: str) -> WbiWriteFirewallDecision:
    """Fail-closed firewall blocking any persistent write/erase/discard against eMMC WBI partition."""
    norm_target = (target or "").strip().lower()
    norm_op = (operation or "").strip().lower()
    targets_wbi = any(tok in norm_target for tok in WBI_DEVICE_TARGET_TOKENS)
    is_write_op = any(verb in norm_op for verb in FORBIDDEN_WBI_WRITE_VERBS) or ("read" not in norm_op and "inspect" not in norm_op)

    errors: List[str] = []
    error_codes: List[str] = []
    if targets_wbi or is_write_op or not PERSISTENT_EMMC_WRITES_AUTHORIZED:
        error_codes.append(ERR_WBI_PERSISTENT_PARTITION_WRITE_FORBIDDEN)
        errors.append(
            f"Persistent eMMC WBI partition mutation blocked fail-closed (target='{target}', op='{operation}', wbi_partition_writes=0). "
            "Use ephemeral RAM-only 'noresume hibdrv.resume=0' bootargs instead."
        )

    return WbiWriteFirewallDecision(
        allowed=False,
        status=STATUS_WBI_PERSISTENT_WRITE_BLOCKED,
        target_partition=target,
        operation=operation,
        wbi_partition_writes=WBI_PARTITION_WRITES,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
    )


def triage_wbi_hibdrv_snapshot(
    envelope: WbiSnapshotEnvelope,
    active_ctx: WbiActiveBootContext,
    *,
    scenario_id: str = "CUSTOM_WBI_TRIAGE",
) -> WbiTriageReport:
    """Diagnose Sony Warp-Boot (`hibdrv` / `WBI2`) stale-resume poisoning & enforce ephemeral `noresume` bypass."""
    header_info, parse_codes, parse_errors = parse_wbi2_header_and_table(
        envelope.header_bytes,
        section_table_bytes=envelope.section_table_bytes,
        available_bytes=envelope.available_bytes,
    )

    active_magic = header_info.magic_ascii if header_info is not None else "TRUNCATED"
    explicitly_invalidated = active_magic in WBI_INVALIDATED_MAGICS_ASCII

    error_codes: List[str] = list(parse_codes)
    errors: List[str] = list(parse_errors)

    # Check 1: Truncation or CRC mismatch
    truncated_or_crc = WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH in error_codes
    if (
        envelope.expected_total_bytes is not None
        and envelope.available_bytes is not None
        and envelope.available_bytes < envelope.expected_total_bytes
    ):
        truncated_or_crc = True
        if WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH not in error_codes:
            error_codes.append(WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH)
        errors.append(
            f"WBI snapshot length truncated: available={envelope.available_bytes} < expected={envelope.expected_total_bytes}."
        )
    if (
        envelope.declared_crc32 is not None
        and envelope.computed_crc32 is not None
        and envelope.declared_crc32 != envelope.computed_crc32
    ):
        truncated_or_crc = True
        if WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH not in error_codes:
            error_codes.append(WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH)
        errors.append(
            f"WBI snapshot CRC32 mismatch: declared=0x{envelope.declared_crc32:08x}, computed=0x{envelope.computed_crc32:08x}."
        )

    # Check 2: Kernel UTS / Image build fingerprint / initramfs / SKU ABI mismatch
    abi_mismatch = False
    if not explicitly_invalidated:
        if envelope.kernel_uts_version != active_ctx.kernel_uts_version:
            abi_mismatch = True
            errors.append(
                f"WBI kernel UTS_VERSION mismatch: snapshot='{envelope.kernel_uts_version}' != active='{active_ctx.kernel_uts_version}'."
            )
        if envelope.kernel_build_fingerprint != active_ctx.kernel_build_fingerprint:
            abi_mismatch = True
            errors.append(
                f"WBI kernel build fingerprint mismatch: snapshot='{envelope.kernel_build_fingerprint[:16]}' != active='{active_ctx.kernel_build_fingerprint[:16]}'."
            )
        if envelope.initramfs_layout_hash != active_ctx.initramfs_layout_hash:
            abi_mismatch = True
            errors.append(
                f"WBI initramfs layout hash mismatch: snapshot='{envelope.initramfs_layout_hash[:16]}' != active='{active_ctx.initramfs_layout_hash[:16]}'."
            )
        if envelope.sku_code != active_ctx.sku_code:
            abi_mismatch = True
            errors.append(
                f"WBI cross-SKU mismatch: snapshot='{envelope.sku_code}' != active='{active_ctx.sku_code}'."
            )
        if abi_mismatch and WBI_KERNEL_ABI_FINGERPRINT_MISMATCH not in error_codes:
            error_codes.append(WBI_KERNEL_ABI_FINGERPRINT_MISMATCH)

    # Check 3: Ephemeral noresume requirement
    ephemeral_noresume_required = bool(
        (not explicitly_invalidated)
        and (
            active_ctx.stage_b_ram_boot
            or truncated_or_crc
            or abi_mismatch
            or (ERR_WBI_BAD_MAGIC in error_codes)
            or (ERR_WBI_HEADER_OR_TABLE_INVALID in error_codes)
        )
    )
    if ephemeral_noresume_required and WBI_EPHEMERAL_NORESUME_REQUIRED not in error_codes:
        error_codes.append(WBI_EPHEMERAL_NORESUME_REQUIRED)

    # Audit provided bootargs
    bootargs_audit = verify_ephemeral_noresume_bootargs_bypass(
        active_ctx.bootargs,
        require_noresume=ephemeral_noresume_required,
    )
    noresume_bypass_active = bootargs_audit.has_noresume or bootargs_audit.has_hibdrv_resume_zero

    # If WBI2 is poisoned/stale/Stage-B AND noresume is NOT active in bootargs -> panic risk!
    panic_risk = bool(ephemeral_noresume_required and not noresume_bypass_active)
    if panic_risk:
        if ERR_WBI_PAGE_TABLE_RESTORE_PANIC_RISK not in error_codes:
            error_codes.append(ERR_WBI_PAGE_TABLE_RESTORE_PANIC_RISK)
        error_codes.extend(c for c in bootargs_audit.error_codes if c not in error_codes)
        errors.extend(bootargs_audit.errors)
        errors.append(
            "hibdrv will attempt WBI2 page-table restore against mismatched/corrupt snapshot and panic before userland."
        )
    elif ephemeral_noresume_required and not bootargs_audit.passed:
        error_codes.extend(c for c in bootargs_audit.error_codes if c not in error_codes)
        errors.extend(bootargs_audit.errors)

    if explicitly_invalidated and not truncated_or_crc and not abi_mismatch:
        status = STATUS_WBI_COLD_BOOT_INVALIDATED
        passed = bootargs_audit.passed
        recommended_action = "COLD_BOOT_SAFE_WBI_EXPLICITLY_INVALIDATED_ZERO_EMMC_WRITES"
    elif ephemeral_noresume_required:
        status = STATUS_WBI_POISONING_NORESUME_BYPASS
        passed = bootargs_audit.passed and noresume_bypass_active and (not panic_risk)
        recommended_action = (
            "APPLY_EPHEMERAL_RAM_ONLY_NORESUME_HIBDRV_RESUME_0_ZERO_WBI_PARTITION_WRITES"
            if passed
            else "ABORT_BOOT_ADD_NORESUME_TO_RAM_BOOTARGS_NEVER_ERASE_NFLASH5"
        )
    else:
        status = STATUS_WBI_HEALTHY_RESUME_MATCH
        passed = bootargs_audit.passed and len(errors) == 0
        recommended_action = "HEALTHY_WARP_BOOT_FINGERPRINT_MATCH_ZERO_WRITES"

    digest_payload = {
        "scenario_id": scenario_id,
        "status": status,
        "passed": passed,
        "magic": active_magic,
        "truncated_or_crc": truncated_or_crc,
        "abi_mismatch": abi_mismatch,
        "noresume_required": ephemeral_noresume_required,
        "noresume_active": noresume_bypass_active,
        "panic_risk": panic_risk,
        "error_codes": error_codes,
    }
    return WbiTriageReport(
        passed=passed,
        triage_classified=True,
        status=status,
        scenario_id=scenario_id,
        header_info=header_info,
        wbi_active_magic=active_magic,
        snapshot_truncated_or_crc_mismatch=truncated_or_crc,
        kernel_abi_fingerprint_mismatch=abi_mismatch,
        ephemeral_noresume_required=ephemeral_noresume_required,
        page_table_restore_panic_risk=panic_risk,
        noresume_bypass_active=noresume_bypass_active,
        bootargs_bypass_verified=bootargs_audit.passed,
        recommended_bootargs=DEFAULT_SAFE_STAGE_B_NORESUME_BOOTARGS,
        recommended_action=recommended_action,
        wbi_partition_writes=WBI_PARTITION_WRITES,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        report_sha256=_canonical_sha256(digest_payload),
    )


def run_wbi_hibdrv_6_scenario_triage() -> Wbi6ScenarioSuiteResult:
    """Execute the 6 canonical Sony Warp-Boot (`hibdrv`/`WBI2`) poisoning & ephemeral `noresume` triage scenarios."""
    valid_bytes, valid_tbl, valid_crc = build_synthetic_wbi2_snapshot_bytes(sections=4)
    trunc_bytes, _, _ = build_synthetic_wbi2_snapshot_bytes(sections=4, truncate_after_bytes=2048)
    bad_xor_bytes, bad_xor_tbl, _ = build_synthetic_wbi2_snapshot_bytes(sections=4, corrupt_meta_xor_index=1)

    scenarios: List[Tuple[str, WbiSnapshotEnvelope, WbiActiveBootContext, bool]] = [
        (
            WBI_SCENARIO_IDS[0],  # W1_HEALTHY_STOCK_702_WBI2_MATCH
            WbiSnapshotEnvelope(
                header_bytes=valid_bytes[:WBI_SECTOR_SIZE],
                section_table_bytes=valid_tbl,
                available_bytes=len(valid_bytes),
                expected_total_bytes=len(valid_bytes),
                declared_crc32=valid_crc,
                computed_crc32=valid_crc,
            ),
            WbiActiveBootContext(
                stage_b_ram_boot=False,
                bootargs="console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait init=/sbin/init",
            ),
            True,
        ),
        (
            WBI_SCENARIO_IDS[1],  # W2_POWER_DROP_MID_SNAPSHOT_TRUNCATED_CRC
            WbiSnapshotEnvelope(
                header_bytes=trunc_bytes[:WBI_SECTOR_SIZE],
                section_table_bytes=bad_xor_tbl,
                available_bytes=len(trunc_bytes),
                expected_total_bytes=len(valid_bytes),
                declared_crc32=valid_crc,
                computed_crc32=zlib.crc32(trunc_bytes) & 0xFFFFFFFF,
            ),
            WbiActiveBootContext(
                stage_b_ram_boot=True,
                bootargs=DEFAULT_SAFE_STAGE_B_NORESUME_BOOTARGS,
            ),
            True,
        ),
        (
            WBI_SCENARIO_IDS[2],  # W3_STALE_SLOT_KERNEL_UTS_OR_INITRAMFS_MISMATCH
            WbiSnapshotEnvelope(
                header_bytes=valid_bytes[:WBI_SECTOR_SIZE],
                section_table_bytes=valid_tbl,
                available_bytes=len(valid_bytes),
                expected_total_bytes=len(valid_bytes),
                declared_crc32=valid_crc,
                computed_crc32=valid_crc,
                kernel_uts_version=FX6_EXPECTED_KERNEL_UTS,
                kernel_build_fingerprint=PINNED_FX6_VMLINUX_KERNEL_SHA256,
                initramfs_layout_hash="0" * 64,
                firmware_slot_version="6.01",
                sku_code=FX6_SKU_NAME,
            ),
            WbiActiveBootContext(
                stage_b_ram_boot=True,
                bootargs=DEFAULT_SAFE_STAGE_B_NORESUME_BOOTARGS,
            ),
            True,
        ),
        (
            WBI_SCENARIO_IDS[3],  # W4_STAGE_B_RAM_BOOT_NORESUME_BYPASS_ACTIVE
            WbiSnapshotEnvelope(
                header_bytes=valid_bytes[:WBI_SECTOR_SIZE],
                section_table_bytes=valid_tbl,
                available_bytes=len(valid_bytes),
                expected_total_bytes=len(valid_bytes),
                declared_crc32=valid_crc,
                computed_crc32=valid_crc,
            ),
            WbiActiveBootContext(
                stage_b_ram_boot=True,
                bootargs=DEFAULT_SAFE_STAGE_B_NORESUME_BOOTARGS,
            ),
            True,
        ),
        (
            WBI_SCENARIO_IDS[4],  # W5_STAGE_B_RAM_BOOT_MISSING_NORESUME_REJECTED
            WbiSnapshotEnvelope(
                header_bytes=bad_xor_bytes[:WBI_SECTOR_SIZE],
                section_table_bytes=bad_xor_tbl,
                available_bytes=len(bad_xor_bytes),
                expected_total_bytes=len(bad_xor_bytes),
                kernel_uts_version="4.9.337-scel+ (stale-2.05)",
                firmware_slot_version="2.05",
            ),
            WbiActiveBootContext(
                stage_b_ram_boot=True,
                bootargs="console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait init=/tmp/stage_b/sbin/init2_stage_b",
            ),
            False,  # Expect fail-closed rejection because noresume is missing!
        ),
        (
            WBI_SCENARIO_IDS[5],  # W6_PERSISTENT_WBI_ERASE_ATTEMPT_BLOCKED
            WbiSnapshotEnvelope(
                header_bytes=b"invl" + valid_bytes[4:WBI_SECTOR_SIZE],
                section_table_bytes=None,
                available_bytes=len(valid_bytes),
            ),
            WbiActiveBootContext(
                stage_b_ram_boot=True,
                bootargs=DEFAULT_SAFE_STAGE_B_NORESUME_BOOTARGS,
            ),
            True,
        ),
    ]

    results: List[WbiTriageReport] = []
    suite_errors: List[str] = []
    passed_count = 0

    for sid, env, ctx, expected_pass in scenarios:
        rep = triage_wbi_hibdrv_snapshot(env, ctx, scenario_id=sid)
        results.append(rep)
        if rep.wbi_partition_writes != 0 or rep.physical_device_writes != 0:
            suite_errors.append(f"{sid} emitted non-zero persistent writes")
            continue
        if expected_pass:
            if rep.passed:
                passed_count += 1
            else:
                suite_errors.append(f"{sid} unexpectedly failed: {rep.error_codes}")
        else:
            if (not rep.passed) and rep.page_table_restore_panic_risk and (ERR_NORESUME_MISSING_BYPASS_TOKEN in rep.error_codes):
                passed_count += 1
            else:
                suite_errors.append(f"{sid} was expected to fail-closed with missing noresume error")

    fw_decision = audit_wbi_partition_write_attempt("/dev/nflasha5", "dd_zero_erase_wbi2")
    if fw_decision.allowed or fw_decision.wbi_partition_writes != 0 or ERR_WBI_PERSISTENT_PARTITION_WRITE_FORBIDDEN not in fw_decision.error_codes:
        suite_errors.append("WBI partition write firewall failed to block /dev/nflasha5 erase")

    all_ok = len(suite_errors) == 0 and passed_count == len(WBI_SCENARIO_IDS)
    suite_payload = {
        "scenarios": [
            {
                "id": r.scenario_id,
                "status": r.status,
                "passed": r.passed,
                "panic_risk": r.page_table_restore_panic_risk,
                "noresume_required": r.ephemeral_noresume_required,
                "noresume_active": r.noresume_bypass_active,
                "wbi_writes": r.wbi_partition_writes,
            }
            for r in results
        ],
        "fw_blocked": not fw_decision.allowed,
    }
    return Wbi6ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_SQUASHFS_WBI_GATE if all_ok else STATUS_FAIL_SQUASHFS_WBI_GATE,
        scenarios_passed=passed_count,
        scenarios_total=len(WBI_SCENARIO_IDS),
        scenario_results=tuple(results),
        write_firewall_decision=fw_decision,
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256(suite_payload),
    )


# ---------------------------------------------------------------------------
# Donor Read-Only Inspection & Clean-Room Synthetic Fallback
# ---------------------------------------------------------------------------


def inspect_squashfs_and_wbi_donors_readonly(*, force_clean_room: Optional[bool] = None) -> DonorSquashfsWbiSnapshot:
    """Inspect local FX3/FX6 SquashFS, WBI2 (`nflasha5`), and `vmlinux.bin` artifacts strictly `O_RDONLY`,
    with deterministic `CLEAN_ROOM_SYNTHETIC` fallback when forced or donor files are absent.
    """
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if not clean_room:
        p1_path = resolve_donor_path(DONOR_FX3_P1_205_SQUASHFS_HOST_RELPATH, require_file=True)
        udtr_path = resolve_donor_path(DONOR_FX3_UDTRBODY_SQUASHFS_RELPATH, require_file=True)
        fx6_upd_path = resolve_donor_path(DONOR_FX6_UPDATER_SQUASHFS_RELPATH, require_file=True)
        fx3_wbi_path = resolve_donor_path(DONOR_FX3_NFLASH5_WBI2_RELPATH, require_file=True)
        fx6_wbi_path = resolve_donor_path(DONOR_FX6_NFLASH5_WBI2_RELPATH, require_file=True)
        fx3_kern_path = resolve_donor_path(DONOR_FX3_VMLINUX_KERNEL_RELPATH, require_file=True)
        fx6_kern_path = resolve_donor_path(DONOR_FX6_VMLINUX_KERNEL_RELPATH, require_file=True)
        all_present = all(
            p.is_file()
            for p in (p1_path, udtr_path, fx6_upd_path, fx3_wbi_path, fx6_wbi_path, fx3_kern_path, fx6_kern_path)
        )
    else:
        p1_path = udtr_path = fx6_upd_path = fx3_wbi_path = fx6_wbi_path = fx3_kern_path = fx6_kern_path = Path()
        all_present = False

    if all_present:
        mode = "LOCAL_DONOR_O_RDONLY"
        p1_bytes = read_file(p1_path, MAX_P1)
        fat = FatP1(p1_bytes)
        p1_initrd_bytes = fat.contents("/boot/initrd.img")
        udtr_bytes = read_file(udtr_path, 8 * 1024 * 1024)
        fx6_upd_bytes = read_file(fx6_upd_path, 8 * 1024 * 1024)
        fx3_kern_bytes = read_file(fx3_kern_path, 16 * 1024 * 1024)
        fx6_kern_bytes = read_file(fx6_kern_path, 16 * 1024 * 1024)

        fx3_wbi_total, fx3_wbi_hdr, fx3_wbi_tbl, fx3_wbi_meta = _read_bounded_wbi2_readonly(fx3_wbi_path)
        fx6_wbi_total, fx6_wbi_hdr, fx6_wbi_tbl, fx6_wbi_meta = _read_bounded_wbi2_readonly(fx6_wbi_path)

        # Verify SquashFS 4.0 superblocks & table bounds on all 3 donor SquashFS images
        r_p1 = verify_squashfs_partition_bytes(p1_initrd_bytes, partition_size=len(p1_initrd_bytes), label="fx3_p1_initrd")
        r_udtr = verify_squashfs_partition_bytes(udtr_bytes, partition_size=len(udtr_bytes), label="fx3_udtrbody")
        r_fx6 = verify_squashfs_partition_bytes(fx6_upd_bytes, partition_size=len(fx6_upd_bytes), label="fx6_updater")
        require(r_p1.passed, f"donor p1 initrd SquashFS invalid: {r_p1.error_codes}")
        require(r_udtr.passed, f"donor FX3 udtrbody SquashFS invalid: {r_udtr.error_codes}")
        require(r_fx6.passed, f"donor FX6 updater SquashFS invalid: {r_fx6.error_codes}")

        # Verify WBI2 headers & section tables via bounded O_RDONLY read
        _, fx3_wbi_codes, fx3_wbi_errs = parse_wbi2_header_and_table(
            fx3_wbi_hdr, section_table_bytes=fx3_wbi_tbl, available_bytes=fx3_wbi_total
        )
        _, fx6_wbi_codes, fx6_wbi_errs = parse_wbi2_header_and_table(
            fx6_wbi_hdr, section_table_bytes=fx6_wbi_tbl, available_bytes=fx6_wbi_total
        )
        require(not fx3_wbi_errs, f"donor FX3 nflasha5 WBI2 invalid: {fx3_wbi_codes}")
        require(not fx6_wbi_errs, f"donor FX6 nflasha5 WBI2 invalid: {fx6_wbi_codes}")

        # Verify Linux 4.9.337-scel+ & WBI/hibernate markers in FX3 & FX6 vmlinux.bin
        require(b"Linux version 4.9.337-scel+" in fx3_kern_bytes and b"dic-build-scm-u20-028" in fx3_kern_bytes, "FX3 vmlinux missing UTS marker")
        require(b"Linux version 4.9.337-scel+" in fx6_kern_bytes and b"dic-build-scm-u24-002" in fx6_kern_bytes, "FX6 vmlinux missing UTS marker")
        require(b"WBI:invalid param" in fx3_kern_bytes and b"hibernate" in fx3_kern_bytes, "FX3 vmlinux missing WBI/hibernate markers")

        p1_initrd_sha = r_p1.image_sha256
        udtr_sha = r_udtr.image_sha256
        fx6_upd_sha = r_fx6.image_sha256
        fx3_wbi_hdr_sha = sha256(fx3_wbi_hdr).hexdigest()
        fx3_wbi_tbl_sha = sha256(fx3_wbi_tbl).hexdigest()
        fx6_wbi_hdr_sha = sha256(fx6_wbi_hdr).hexdigest()
        fx6_wbi_tbl_sha = sha256(fx6_wbi_tbl).hexdigest()
        fx3_kern_sha = sha256(fx3_kern_bytes).hexdigest()
        fx6_kern_sha = sha256(fx6_kern_bytes).hexdigest()
        fx3_wbi_sections = int(fx3_wbi_meta["sections"])
        fx6_wbi_sections = int(fx6_wbi_meta["sections"])

        artifacts = (
            SquashfsWbiDonorArtifactDigest(
                label="fx3_p1_initrd_squashfs",
                relpath=DONOR_FX3_P1_205_SQUASHFS_HOST_RELPATH,
                source_mode=mode,
                byte_length=len(p1_initrd_bytes),
                sha256=p1_initrd_sha,
                details=f"SquashFS 4.0 GZIP inodes={r_p1.superblock.inodes} bytes_used={r_p1.superblock.bytes_used}",
            ),
            SquashfsWbiDonorArtifactDigest(
                label="fx3_udtrbody_squashfs",
                relpath=DONOR_FX3_UDTRBODY_SQUASHFS_RELPATH,
                source_mode=mode,
                byte_length=len(udtr_bytes),
                sha256=udtr_sha,
                details=f"SquashFS 4.0 GZIP inodes={r_udtr.superblock.inodes} bytes_used={r_udtr.superblock.bytes_used}",
            ),
            SquashfsWbiDonorArtifactDigest(
                label="fx6_updater_squashfs",
                relpath=DONOR_FX6_UPDATER_SQUASHFS_RELPATH,
                source_mode=mode,
                byte_length=len(fx6_upd_bytes),
                sha256=fx6_upd_sha,
                details=f"FX6 SquashFS 4.0 GZIP inodes={r_fx6.superblock.inodes} bytes_used={r_fx6.superblock.bytes_used}",
            ),
            SquashfsWbiDonorArtifactDigest(
                label="fx3_nflasha5_wbi2",
                relpath=DONOR_FX3_NFLASH5_WBI2_RELPATH,
                source_mode=mode,
                byte_length=fx3_wbi_total,
                sha256=fx3_wbi_hdr_sha,
                details=f"Bounded O_RDONLY WBI2 header+table: sections={fx3_wbi_sections} table_sha256={fx3_wbi_tbl_sha[:16]}",
            ),
            SquashfsWbiDonorArtifactDigest(
                label="fx6_nflasha5_wbi2",
                relpath=DONOR_FX6_NFLASH5_WBI2_RELPATH,
                source_mode=mode,
                byte_length=fx6_wbi_total,
                sha256=fx6_wbi_hdr_sha,
                details=f"Cross-SKU FX6 WBI2 header+table: sections={fx6_wbi_sections} table_sha256={fx6_wbi_tbl_sha[:16]}",
            ),
            SquashfsWbiDonorArtifactDigest(
                label="fx3_vmlinux_kernel",
                relpath=DONOR_FX3_VMLINUX_KERNEL_RELPATH,
                source_mode=mode,
                byte_length=len(fx3_kern_bytes),
                sha256=fx3_kern_sha,
                details=f"Kernel UTS {FX3_EXPECTED_KERNEL_UTS} with WBI/hibernate symbols",
            ),
            SquashfsWbiDonorArtifactDigest(
                label="fx6_vmlinux_kernel",
                relpath=DONOR_FX6_VMLINUX_KERNEL_RELPATH,
                source_mode=mode,
                byte_length=len(fx6_kern_bytes),
                sha256=fx6_kern_sha,
                details=f"Cross-SKU FX6 Kernel UTS {FX6_EXPECTED_KERNEL_UTS}",
            ),
        )
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        p1_initrd_sha = PINNED_FX3_P1_INITRD_SQUASHFS_SHA256
        udtr_sha = PINNED_FX3_UDTRBODY_SQUASHFS_SHA256
        fx6_upd_sha = PINNED_FX6_UPDATER_SQUASHFS_SHA256
        fx3_wbi_hdr_sha = PINNED_FX3_NFLASH5_WBI2_HDR_SHA256
        fx3_wbi_tbl_sha = PINNED_FX3_NFLASH5_WBI2_TABLE_SHA256
        fx6_wbi_hdr_sha = PINNED_FX6_NFLASH5_WBI2_HDR_SHA256
        fx6_wbi_tbl_sha = PINNED_FX6_NFLASH5_WBI2_TABLE_SHA256
        fx3_kern_sha = PINNED_FX3_VMLINUX_KERNEL_SHA256
        fx6_kern_sha = PINNED_FX6_VMLINUX_KERNEL_SHA256
        fx3_wbi_sections = PINNED_FX3_NFLASH5_WBI2_SECTIONS
        fx6_wbi_sections = PINNED_FX6_NFLASH5_WBI2_SECTIONS

        artifacts = (
            SquashfsWbiDonorArtifactDigest(
                label="fx3_p1_initrd_squashfs",
                relpath=DONOR_FX3_P1_205_SQUASHFS_HOST_RELPATH,
                source_mode=mode,
                byte_length=PINNED_FX3_P1_INITRD_SQUASHFS_BYTES,
                sha256=p1_initrd_sha,
                details="Pinned clean-room FX3 p1 /boot/initrd.img SquashFS 4.0 GZIP anchor",
            ),
            SquashfsWbiDonorArtifactDigest(
                label="fx3_udtrbody_squashfs",
                relpath=DONOR_FX3_UDTRBODY_SQUASHFS_RELPATH,
                source_mode=mode,
                byte_length=PINNED_FX3_UDTRBODY_SQUASHFS_BYTES,
                sha256=udtr_sha,
                details="Pinned clean-room FX3 udtrbody.squashfs anchor",
            ),
            SquashfsWbiDonorArtifactDigest(
                label="fx6_updater_squashfs",
                relpath=DONOR_FX6_UPDATER_SQUASHFS_RELPATH,
                source_mode=mode,
                byte_length=PINNED_FX6_UPDATER_SQUASHFS_BYTES,
                sha256=fx6_upd_sha,
                details="Pinned clean-room FX6 updater.img SquashFS 4.0 anchor",
            ),
            SquashfsWbiDonorArtifactDigest(
                label="fx3_nflasha5_wbi2",
                relpath=DONOR_FX3_NFLASH5_WBI2_RELPATH,
                source_mode=mode,
                byte_length=PINNED_FX3_NFLASH5_WBI2_TOTAL_BYTES,
                sha256=fx3_wbi_hdr_sha,
                details=f"Pinned clean-room FX3 WBI2 anchor: sections={fx3_wbi_sections}",
            ),
            SquashfsWbiDonorArtifactDigest(
                label="fx6_nflasha5_wbi2",
                relpath=DONOR_FX6_NFLASH5_WBI2_RELPATH,
                source_mode=mode,
                byte_length=PINNED_FX6_NFLASH5_WBI2_TOTAL_BYTES,
                sha256=fx6_wbi_hdr_sha,
                details=f"Pinned clean-room FX6 WBI2 anchor: sections={fx6_wbi_sections}",
            ),
            SquashfsWbiDonorArtifactDigest(
                label="fx3_vmlinux_kernel",
                relpath=DONOR_FX3_VMLINUX_KERNEL_RELPATH,
                source_mode=mode,
                byte_length=6610952,
                sha256=fx3_kern_sha,
                details=f"Pinned clean-room FX3 Kernel UTS {FX3_EXPECTED_KERNEL_UTS}",
            ),
            SquashfsWbiDonorArtifactDigest(
                label="fx6_vmlinux_kernel",
                relpath=DONOR_FX6_VMLINUX_KERNEL_RELPATH,
                source_mode=mode,
                byte_length=6610952,
                sha256=fx6_kern_sha,
                details=f"Pinned clean-room FX6 Kernel UTS {FX6_EXPECTED_KERNEL_UTS}",
            ),
        )

    snap_payload = {
        "mode": mode,
        "p1_initrd_sha": p1_initrd_sha,
        "udtr_sha": udtr_sha,
        "fx6_upd_sha": fx6_upd_sha,
        "fx3_wbi_hdr_sha": fx3_wbi_hdr_sha,
        "fx3_wbi_tbl_sha": fx3_wbi_tbl_sha,
        "fx6_wbi_hdr_sha": fx6_wbi_hdr_sha,
        "fx6_wbi_tbl_sha": fx6_wbi_tbl_sha,
        "fx3_kern_sha": fx3_kern_sha,
        "fx6_kern_sha": fx6_kern_sha,
    }
    return DonorSquashfsWbiSnapshot(
        verification_mode=mode,
        read_only_access=READ_ONLY_DONOR_ACCESS,
        fx3_p1_initrd_squashfs_sha256=p1_initrd_sha,
        fx3_udtrbody_squashfs_sha256=udtr_sha,
        fx6_updater_squashfs_sha256=fx6_upd_sha,
        fx3_wbi2_hdr_sha256=fx3_wbi_hdr_sha,
        fx3_wbi2_table_sha256=fx3_wbi_tbl_sha,
        fx3_wbi2_sections=fx3_wbi_sections,
        fx6_wbi2_hdr_sha256=fx6_wbi_hdr_sha,
        fx6_wbi2_table_sha256=fx6_wbi_tbl_sha,
        fx6_wbi2_sections=fx6_wbi_sections,
        fx3_vmlinux_sha256=fx3_kern_sha,
        fx6_vmlinux_sha256=fx6_kern_sha,
        fx3_uts_marker=FX3_EXPECTED_KERNEL_UTS,
        fx6_uts_marker=FX6_EXPECTED_KERNEL_UTS,
        artifacts=artifacts,
        snapshot_sha256=_canonical_sha256(snap_payload),
    )


# ---------------------------------------------------------------------------
# Pillar C — Master Suite Runner
# ---------------------------------------------------------------------------


def run_squashfs_and_hibdrv_wbi_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> SquashfsAndHibdrvWbiSuiteReport:
    """Execute Phase 119 SquashFS 4.0 & Sony Warp-Boot `hibdrv`/`WBI` Triage Master Suite."""
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    require(PERSISTENT_WRITE_RELEASE is False, "persistent_write_release must stay False")
    require(ALLOW_BOOT_PARTITION_TARGETING is False, "allow_boot_partition_targeting must stay False")
    require(ALLOW_DESTRUCTIVE_FASTBOOT is False, "allow_destructive_fastboot must stay False")
    require(OTP_FUSE_TOUCHES == 0, "otp_fuse_touches must stay 0")
    require(PASSIVE_TX_BYTES_EMITTED == 0, "passive_tx_bytes_emitted must stay 0")
    require(PHYSICAL_DEVICE_WRITES == 0, "physical_device_writes must stay 0")
    require(WBI_PARTITION_WRITES == 0, "wbi_partition_writes must stay 0")

    t0 = time.monotonic()
    donor_snap = inspect_squashfs_and_wbi_donors_readonly(force_clean_room=force_clean_room)

    # Pillar A checks across all 6 SquashFS 4.0 compression IDs + 5 fail-closed fault matrices
    comp_reports: List[SquashfsVerificationReport] = []
    for cid, cname in sorted(SQUASHFS_COMPRESSION_NAMES.items()):
        buf = build_synthetic_squashfs_superblock(compression_id=cid, block_size=131072, block_log=17)
        comp_reports.append(verify_squashfs_partition_bytes(buf, partition_size=4096, label=f"synthetic_{cname.lower()}"))

    trunc_buf = build_synthetic_squashfs_superblock(bytes_used=8192, payload_size=4096)
    trunc_rep = verify_squashfs_partition_bytes(trunc_buf, partition_size=8192, label="truncated_flash")

    nonmono_buf = build_synthetic_squashfs_superblock(inode_table_start=3800, directory_table_start=3500)
    nonmono_rep = verify_squashfs_partition_bytes(nonmono_buf, partition_size=4096, label="non_monotonic_tables")

    bad_blog_buf = build_synthetic_squashfs_superblock(block_size=131072, block_log=16)
    bad_blog_rep = verify_squashfs_partition_bytes(bad_blog_buf, partition_size=4096, label="bad_block_log")

    bad_comp_buf = build_synthetic_squashfs_superblock(compression_id=99)
    bad_comp_rep = verify_squashfs_partition_bytes(bad_comp_buf, partition_size=4096, label="unsupported_comp_id")

    be_buf = build_synthetic_squashfs_superblock(s_magic=SQUASHFS_MAGIC_BE)
    be_rep = verify_squashfs_partition_bytes(be_buf, partition_size=4096, label="big_endian_sqsh")

    # Pillar B checks
    wbi_6 = run_wbi_hibdrv_6_scenario_triage()
    noresume_ok = verify_ephemeral_noresume_bootargs_bypass(DEFAULT_SAFE_STAGE_B_NORESUME_BOOTARGS, require_noresume=True)
    noresume_missing = verify_ephemeral_noresume_bootargs_bypass(
        "console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait init=/tmp/stage_b/sbin/init2_stage_b",
        require_noresume=True,
    )

    errors: List[str] = []
    for rep in comp_reports:
        if not rep.passed:
            errors.append(f"Valid SquashFS compression {rep.label} unexpectedly failed: {rep.error_codes}")
    if trunc_rep.passed or ERR_SQUASHFS_TRUNCATED_IMAGE_PAYLOAD not in trunc_rep.error_codes:
        errors.append("Truncated SquashFS flash was not rejected")
    if nonmono_rep.passed or ERR_SQUASHFS_NON_MONOTONIC_TABLE_BOUNDS not in nonmono_rep.error_codes:
        errors.append("Non-monotonic SquashFS table bounds were not rejected")
    if bad_blog_rep.passed or ERR_SQUASHFS_INVALID_BLOCK_SIZE_OR_LOG not in bad_blog_rep.error_codes:
        errors.append("Mismatched SquashFS block_log was not rejected")
    if bad_comp_rep.passed or ERR_SQUASHFS_UNSUPPORTED_COMPRESSION_ID not in bad_comp_rep.error_codes:
        errors.append("Unsupported SquashFS compression ID was not rejected")
    if be_rep.passed or ERR_SQUASHFS_WRONG_ENDIAN_BIG_SQSH not in be_rep.error_codes:
        errors.append("Big-endian SquashFS sqsh magic was not rejected")
    if not wbi_6.passed:
        errors.extend(wbi_6.errors)
    if not noresume_ok.passed:
        errors.extend(noresume_ok.errors)
    if noresume_missing.passed or ERR_NORESUME_MISSING_BYPASS_TOKEN not in noresume_missing.error_codes:
        errors.append("Missing noresume bootargs was not rejected")

    all_ok = len(errors) == 0
    status = STATUS_VERIFIED_SQUASHFS_WBI_GATE if all_ok else STATUS_FAIL_SQUASHFS_WBI_GATE
    digest_payload = {
        "schema": SQUASHFS_WBI_HIBDRV_SCHEMA,
        "mode": donor_snap.verification_mode,
        "donor_sha": donor_snap.snapshot_sha256,
        "comp_shas": [r.image_sha256 for r in comp_reports],
        "wbi_6": wbi_6.suite_sha256,
        "all_passed": all_ok,
    }

    return SquashfsAndHibdrvWbiSuiteReport(
        schema=SQUASHFS_WBI_HIBDRV_SCHEMA,
        version=SQUASHFS_WBI_HIBDRV_VERSION,
        status=status,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        read_only_donor_access=READ_ONLY_DONOR_ACCESS,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        wbi_partition_writes=WBI_PARTITION_WRITES,
        donor_snapshot=donor_snap,
        squashfs_compression_reports=tuple(comp_reports),
        squashfs_truncated_rejected=trunc_rep,
        squashfs_non_monotonic_rejected=nonmono_rep,
        squashfs_bad_blocklog_rejected=bad_blog_rep,
        squashfs_bad_compression_rejected=bad_comp_rep,
        squashfs_big_endian_rejected=be_rep,
        wbi_6_scenario_suite=wbi_6,
        ephemeral_noresume_valid_report=noresume_ok,
        ephemeral_noresume_missing_rejected=noresume_missing,
        suite_sha256=_canonical_sha256(digest_payload),
        elapsed_seconds=round(time.monotonic() - t0, 6),
        errors=tuple(errors),
    )


__all__ = [
    "ALLOWED_NORESUME_INIT_PATHS",
    "ALLOWED_NORESUME_TOKENS",
    "ALLOW_BOOT_PARTITION_TARGETING",
    "ALLOW_DESTRUCTIVE_FASTBOOT",
    "DEFAULT_SAFE_STAGE_B_NORESUME_BOOTARGS",
    "DONOR_FX3_NFLASH5_WBI2_RELPATH",
    "DONOR_FX3_P1_205_SQUASHFS_HOST_RELPATH",
    "DONOR_FX3_UDTRBODY_SQUASHFS_RELPATH",
    "DONOR_FX3_VMLINUX_KERNEL_RELPATH",
    "DONOR_FX6_NFLASH5_WBI2_RELPATH",
    "DONOR_FX6_UPDATER_SQUASHFS_RELPATH",
    "DONOR_FX6_VMLINUX_KERNEL_RELPATH",
    "EMMC_BLOCK_ROOT_PREFIXES",
    "ERR_NORESUME_MISSING_BYPASS_TOKEN",
    "ERR_NORESUME_RW_EMMC_OR_REPARTITION_FORBIDDEN",
    "ERR_NORESUME_UNVERIFIED_INIT",
    "ERR_NORESUME_WDT_DISABLED",
    "ERR_SQUASHFS_BAD_MAGIC",
    "ERR_SQUASHFS_BLANK_OR_ERASED_FLASH",
    "ERR_SQUASHFS_BYTES_USED_EXCEEDS_PARTITION",
    "ERR_SQUASHFS_EMPTY_OR_TRUNCATED_HEADER",
    "ERR_SQUASHFS_INVALID_BLOCK_SIZE_OR_LOG",
    "ERR_SQUASHFS_INVALID_BYTES_USED",
    "ERR_SQUASHFS_INVALID_ID_COUNT",
    "ERR_SQUASHFS_INVALID_INODE_COUNT",
    "ERR_SQUASHFS_NON_MONOTONIC_TABLE_BOUNDS",
    "ERR_SQUASHFS_ROOT_INODE_OUT_OF_BOUNDS",
    "ERR_SQUASHFS_TABLE_OUT_OF_BOUNDS",
    "ERR_SQUASHFS_TRUNCATED_IMAGE_PAYLOAD",
    "ERR_SQUASHFS_UNSUPPORTED_COMPRESSION_ID",
    "ERR_SQUASHFS_UNSUPPORTED_VERSION",
    "ERR_SQUASHFS_WRONG_ENDIAN_BIG_SQSH",
    "ERR_WBI_BAD_MAGIC",
    "ERR_WBI_HEADER_OR_TABLE_INVALID",
    "ERR_WBI_PAGE_TABLE_RESTORE_PANIC_RISK",
    "ERR_WBI_PERSISTENT_PARTITION_WRITE_FORBIDDEN",
    "FORBIDDEN_REPARTITION_TOKENS",
    "FORBIDDEN_WBI_WRITE_VERBS",
    "FORBIDDEN_WDT_DISABLE_PARAMS",
    "FX3_EXPECTED_INITRAMFS_HASH",
    "FX3_EXPECTED_KERNEL_UTS",
    "FX3_SKU_NAME",
    "FX6_EXPECTED_KERNEL_UTS",
    "FX6_SKU_NAME",
    "OTP_FUSE_TOUCHES",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHYSICAL_DEVICE_WRITES",
    "PINNED_FX3_NFLASH5_WBI2_HDR_SHA256",
    "PINNED_FX3_NFLASH5_WBI2_SECTIONS",
    "PINNED_FX3_NFLASH5_WBI2_TABLE_SHA256",
    "PINNED_FX3_NFLASH5_WBI2_TOTAL_BYTES",
    "PINNED_FX3_P1_INITRD_SQUASHFS_BYTES",
    "PINNED_FX3_P1_INITRD_SQUASHFS_SHA256",
    "PINNED_FX3_UDTRBODY_SQUASHFS_BYTES",
    "PINNED_FX3_UDTRBODY_SQUASHFS_SHA256",
    "PINNED_FX3_VMLINUX_KERNEL_SHA256",
    "PINNED_FX6_NFLASH5_WBI2_HDR_SHA256",
    "PINNED_FX6_NFLASH5_WBI2_SECTIONS",
    "PINNED_FX6_NFLASH5_WBI2_TABLE_SHA256",
    "PINNED_FX6_NFLASH5_WBI2_TOTAL_BYTES",
    "PINNED_FX6_UPDATER_SQUASHFS_BYTES",
    "PINNED_FX6_UPDATER_SQUASHFS_SHA256",
    "PINNED_FX6_VMLINUX_KERNEL_SHA256",
    "READ_ONLY_DONOR_ACCESS",
    "SQUASHFS_COMPRESSION_NAMES",
    "SQUASHFS_EXPORTABLE_BIT",
    "SQUASHFS_FLAG_BITS",
    "SQUASHFS_INVALID_BLK",
    "SQUASHFS_MAGIC",
    "SQUASHFS_MAGIC_BE",
    "SQUASHFS_MAJOR_VERSION",
    "SQUASHFS_MAX_BLOCK_LOG",
    "SQUASHFS_MAX_BLOCK_SIZE",
    "SQUASHFS_MAX_BYTES_USED",
    "SQUASHFS_MAX_INODES",
    "SQUASHFS_MINOR_VERSION",
    "SQUASHFS_MIN_BLOCK_LOG",
    "SQUASHFS_MIN_BLOCK_SIZE",
    "SQUASHFS_SUPERBLOCK_SIZE",
    "SQUASHFS_WBI_HIBDRV_SCHEMA",
    "SQUASHFS_WBI_HIBDRV_VERSION",
    "STATUS_FAIL_SQUASHFS_WBI_GATE",
    "STATUS_REJECTED_EPHEMERAL_NORESUME_BYPASS",
    "STATUS_REJECTED_SQUASHFS_SUPERBLOCK",
    "STATUS_VERIFIED_EPHEMERAL_NORESUME_BYPASS",
    "STATUS_VERIFIED_SQUASHFS_SUPERBLOCK",
    "STATUS_VERIFIED_SQUASHFS_WBI_GATE",
    "STATUS_WBI_COLD_BOOT_INVALIDATED",
    "STATUS_WBI_HEALTHY_RESUME_MATCH",
    "STATUS_WBI_PERSISTENT_WRITE_BLOCKED",
    "STATUS_WBI_POISONING_NORESUME_BYPASS",
    "WBI_DEVICE_TARGET_TOKENS",
    "WBI_EPHEMERAL_NORESUME_REQUIRED",
    "WBI_HEADER_SIZE",
    "WBI_INVALIDATED_MAGICS_ASCII",
    "WBI_KERNEL_ABI_FINGERPRINT_MISMATCH",
    "WBI_MAGIC_VALID_ASCII",
    "WBI_MAGIC_VALID_BYTES",
    "WBI_MAX_TABLE_READ_BYTES",
    "WBI_PARTITION_WRITES",
    "WBI_PHYS_BASE",
    "WBI_SCENARIO_IDS",
    "WBI_SECTION_ENTRY_SIZE",
    "WBI_SECTOR_SIZE",
    "WBI_SH_ZERO",
    "WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH",
    "WBI_VIRT_BASE",
    "WBI_XOR_MASK",
    "DonorSquashfsWbiSnapshot",
    "EphemeralNoresumeAuditReport",
    "SquashfsAndHibdrvWbiSuiteReport",
    "SquashfsSuperblockInfo",
    "SquashfsVerificationReport",
    "SquashfsWbiDonorArtifactDigest",
    "Wbi6ScenarioSuiteResult",
    "WbiActiveBootContext",
    "WbiHeaderInfo",
    "WbiSnapshotEnvelope",
    "WbiTriageReport",
    "WbiWriteFirewallDecision",
    "audit_wbi_partition_write_attempt",
    "build_synthetic_squashfs_superblock",
    "build_synthetic_wbi2_snapshot_bytes",
    "inspect_squashfs_and_wbi_donors_readonly",
    "parse_wbi2_header_and_table",
    "run_squashfs_and_hibdrv_wbi_suite",
    "run_wbi_hibdrv_6_scenario_triage",
    "triage_wbi_hibdrv_snapshot",
    "verify_ephemeral_noresume_bootargs_bypass",
    "verify_squashfs_partition_bytes",
]
