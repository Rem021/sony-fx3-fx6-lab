"""Phase 101 — CXD90057 init2 SVR4 newc cpio RAM-Disk Overlay Path/Symlink/Device-Node Firewall,
JEDEC eMMC 5.1 EXT_CSD [267..269] Pre-EOL & Life-Time Health Auditor, & 9-Pillar Recovery Master Suite Integration.

Provides three deterministic, RAM-only, read-only-donor verification pillars for
Sony `ILME-FX3` (`0x91030080` / `ALCIN_UUD`) Stage-B recovery containment & eMMC health gating:

1. **Pillar 1 — SVR4 Portable `'070701'` `newc` `cpio` RAM-Disk Overlay Structural & Security Firewall**:
   - Implements a pure-Python `'070701'` `newc` `cpio` parser and builder with exact 4-byte
     `(110 + namesize)` header+name alignment and 4-byte payload alignment plus `TRAILER!!!` sentinel.
   - Enforces 100% fail-closed rejection of `../` path traversal, leading `/` absolute path escapes,
     symlink escapes into `/dev/mmcblk0*` / `/dev/nflasha*` / host paths outside overlay containment,
     unauthorized `S_IFBLK` / `S_IFCHR` raw flash or kernel memory device nodes, setuid/setgid root
     binaries outside an explicit allowlist, missing `TRAILER!!!`, and truncated/corrupted archives.

2. **Pillar 2 — JEDEC eMMC 5.1 `EXT_CSD` `[267..269]` Pre-EOL & Life-Time Health Auditor**:
   - Parses 512-byte `EXT_CSD` registers:
     - `PRE_EOL_INFO [267]` (`0x01` Normal, `0x02` Warning 80% reserved blocks consumed, `0x03` Urgent 90%),
     - `DEVICE_LIFE_TIME_EST_TYP_A [268]` (SLC) & `TYP_B [269]` (MLC) (`0x01..0x0A` = 0%..100% in 10% steps,
       `0x0B` = exceeded max estimated device life time),
     - `PARTITION_CONFIG [179]` (`BOOT_ACK`, `BOOT_PARTITION_ENABLE`, `PARTITION_ACCESS`) verifying the
       boot partition pointer was never flipped away from factory stock (`BOOT0`, `UDA` access).
   - Fails closed before any Stage-B rehearsal if donor body eMMC reports `PRE_EOL_INFO >= 0x02` or
     `LIFE_TIME >= 0x09` (`>80%` wear) or flipped boot partition pointer, demanding immediate
     read-only Tier-0 backup preservation.

3. **Pillar 3 — RAM-Only `tmpfs` / `overlayfs` Upperdir Isolation Proof**:
   - Parses Linux mount-table (`/proc/mounts` / `fstab`) specifications and proves via longest-prefix
     mountpoint resolution that every `overlay` / `overlayfs` `upperdir` and `workdir` resides
     strictly on `tmpfs` (RAM) and every `/dev/mmcblk0p*` (and `/dev/nflasha*`) block device is either
     unmounted or `ro,noatime` with zero `rw` block mounts.

Safety Redlines (Hard-Locked):
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `ALLOW_BOOT_PARTITION_TARGETING = False`
- `ALLOW_DESTRUCTIVE_FASTBOOT = False`
- `READ_ONLY_DONOR_ACCESS = True`
- `OTP_FUSE_TOUCHES = 0`
- `PASSIVE_TX_BYTES_EMITTED = 0`
- `PHYSICAL_DEVICE_WRITES = 0`
- Local donor files opened strictly via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`.
- Zero raw `bytes` reprs emitted; all digests and header samples use `.hex()` / `.hexdigest()`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
import posixpath
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .emmc_dump_forensic_verifier import (
    EXT_CSD_BOOT_BUS_COND_IDX,
    EXT_CSD_BOOT_SIZE_MULT_IDX,
    EXT_CSD_LIFE_TIME_A_IDX,
    EXT_CSD_LIFE_TIME_B_IDX,
    EXT_CSD_PART_CONFIG_IDX,
    EXT_CSD_PRE_EOL_INFO_IDX,
    EXT_CSD_REV_IDX,
    EXT_CSD_RPMB_SIZE_MULT_IDX,
    EXT_CSD_RST_N_ENABLE_IDX,
    EXT_CSD_SIZE,
    build_synthetic_ext_csd,
)
from .fat import FatP1, MAX_P1
from .files import is_forced_clean_room, read_file, require, resolve_donor_path


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

RAMDISK_EMMC_HEALTH_SCHEMA: str = "fx3-ramdisk-overlay-and-emmc-health-verifier-v1"
RAMDISK_EMMC_HEALTH_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True
OTP_FUSE_TOUCHES: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0

STATUS_VERIFIED_RAMDISK_EMMC_HEALTH: str = "VERIFIED_RAMDISK_OVERLAY_AND_EMMC_HEALTH"
STATUS_FAIL_RAMDISK_EMMC_HEALTH: str = "FAIL_RAMDISK_OVERLAY_AND_EMMC_HEALTH"

# Local Donor Relative Paths (opened strictly O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
DONOR_FX3_P1_205_RELPATH: str = "fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1"
DONOR_FX3_INIT2_RELPATH: str = "sony-firmware-20261024/stage2/extraction/files/nflasha7/sbin/init2"
DONOR_FX3_FSTAB_RELPATH: str = "sony-firmware-20261024/stage2/extraction/files/nflasha7/sbin/initrc/fstab"
DONOR_FX6_DTB_RELPATH: str = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0800_appli/setting/cxd90057.dtb"

# ---------------------------------------------------------------------------
# Pillar 1 Constants — SVR4 Portable '070701' newc cpio
# ---------------------------------------------------------------------------

CPIO_NEWC_MAGIC_BYTES: bytes = b"070701"
CPIO_NEWC_MAGIC_STR: str = "070701"
CPIO_HEADER_SIZE: int = 110
CPIO_TRAILER_NAME: str = "TRAILER!!!"
CPIO_MAX_ARCHIVE_BYTES: int = 64 * 1024 * 1024
CPIO_MAX_NAME_BYTES: int = 4096
CPIO_MAX_ENTRIES: int = 16384

FORBIDDEN_CPIO_DEVICE_TOKENS: Tuple[str, ...] = (
    "mmcblk",
    "nflasha",
    "cnflasha",
    "dev/mem",
    "dev/kmem",
    "dev/block",
    "dev/mtd",
)
FORBIDDEN_DEVICE_MAJORS: Tuple[int, ...] = (179, 252)  # 179=MMC block, 252=Sony nflasha
DEFAULT_ALLOWED_ABS_SYMLINK_TARGETS: Tuple[str, ...] = (
    "/bin/busybox",
    "/tmp/stage_b/bin/busybox",
)

ERR_CPIO_EMPTY_OR_TRUNCATED_HEADER: str = "CPIO_EMPTY_OR_TRUNCATED_HEADER"
ERR_CPIO_BAD_MAGIC: str = "CPIO_BAD_070701_MAGIC"
ERR_CPIO_BAD_HEX_FIELD: str = "CPIO_BAD_HEX_HEADER_FIELD"
ERR_CPIO_BAD_NAMESIZE: str = "CPIO_BAD_NAMESIZE"
ERR_CPIO_TRUNCATED_NAME: str = "CPIO_TRUNCATED_NAME_OR_PADDING"
ERR_CPIO_NAME_NOT_NUL_TERMINATED: str = "CPIO_NAME_NOT_NUL_TERMINATED"
ERR_CPIO_EMBEDDED_NUL_IN_NAME: str = "CPIO_EMBEDDED_NUL_IN_NAME"
ERR_CPIO_TRUNCATED_PAYLOAD: str = "CPIO_TRUNCATED_PAYLOAD_OR_PADDING"
ERR_CPIO_MISSING_TRAILER: str = "CPIO_MISSING_TRAILER_SENTINEL"
ERR_CPIO_NONZERO_TRAILER_SIZE: str = "CPIO_NONZERO_TRAILER_FILESIZE"
ERR_CPIO_TRAILING_GARBAGE_AFTER_TRAILER: str = "CPIO_TRAILING_NONZERO_AFTER_TRAILER"
ERR_CPIO_PATH_TRAVERSAL: str = "CPIO_PATH_TRAVERSAL_REJECTED"
ERR_CPIO_ABSOLUTE_PATH: str = "CPIO_ABSOLUTE_PATH_REJECTED"
ERR_CPIO_DUPLICATE_PATH: str = "CPIO_DUPLICATE_ENTRY_PATH"
ERR_CPIO_SYMLINK_ESCAPE: str = "CPIO_SYMLINK_ESCAPE_REJECTED"
ERR_CPIO_MMCBLK_SYMLINK_ESCAPE: str = "CPIO_MMCBLK_SYMLINK_ESCAPE_REJECTED"
ERR_CPIO_UNAUTHORIZED_BLK_NODE: str = "CPIO_UNAUTHORIZED_S_IFBLK_DEVICE_NODE"
ERR_CPIO_UNAUTHORIZED_CHR_NODE: str = "CPIO_UNAUTHORIZED_S_IFCHR_DEVICE_NODE"
ERR_CPIO_UNAUTHORIZED_SETUID: str = "CPIO_UNAUTHORIZED_SETUID_OR_SETGID"
ERR_CPIO_UNSUPPORTED_FILE_TYPE: str = "CPIO_UNSUPPORTED_SPECIAL_FILE_TYPE"
ERR_CPIO_NONZERO_NONREG_FILESIZE: str = "CPIO_NONZERO_SIZE_ON_NON_REG_OR_LNK"
ERR_CPIO_ENTRY_LIMIT_EXCEEDED: str = "CPIO_ENTRY_LIMIT_EXCEEDED"

# ---------------------------------------------------------------------------
# Pillar 2 Constants — JEDEC eMMC 5.1 EXT_CSD [267..269] & [179]
# ---------------------------------------------------------------------------

EXT_CSD_PRE_EOL_NOT_DEFINED: int = 0x00
EXT_CSD_PRE_EOL_NORMAL: int = 0x01
EXT_CSD_PRE_EOL_WARNING: int = 0x02
EXT_CSD_PRE_EOL_URGENT: int = 0x03

EXT_CSD_LIFE_TIME_NOT_DEFINED: int = 0x00
EXT_CSD_LIFE_TIME_MAX_SAFE: int = 0x08  # 0x01..0x08 => 0%..80%; >=0x09 => >80% wear!
EXT_CSD_LIFE_TIME_CRITICAL_MIN: int = 0x09
EXT_CSD_LIFE_TIME_EXCEEDED: int = 0x0B

FX3_STOCK_PART_CONFIG: int = 0x48  # BOOT_ACK=1, BOOT_PARTITION_ENABLE=1 (BOOT0), PARTITION_ACCESS=0 (UDA)
FX3_STOCK_BOOT_ACK: int = 1
FX3_STOCK_BOOT_PARTITION_ENABLE: int = 1  # BOOT0
FX3_STOCK_PARTITION_ACCESS: int = 0  # USER_AREA

PRE_EOL_STATUS_MAP: Dict[int, str] = {
    0x00: "NOT_DEFINED",
    0x01: "NORMAL_LT_80PCT_RESERVED_CONSUMED",
    0x02: "WARNING_80PCT_RESERVED_CONSUMED",
    0x03: "URGENT_90PCT_RESERVED_CONSUMED",
}

LIFE_TIME_PCT_MAP: Dict[int, Tuple[int, int]] = {
    0x01: (0, 10),
    0x02: (10, 20),
    0x03: (20, 30),
    0x04: (30, 40),
    0x05: (40, 50),
    0x06: (50, 60),
    0x07: (60, 70),
    0x08: (70, 80),
    0x09: (80, 90),
    0x0A: (90, 100),
}

ERR_EXT_CSD_BAD_LENGTH: str = "EXT_CSD_BAD_LENGTH_NOT_512B"
ERR_EMMC_PRE_EOL_UNDEFINED: str = "EMMC_PRE_EOL_INFO_UNDEFINED_0X00"
ERR_EMMC_PRE_EOL_WARNING: str = "EMMC_PRE_EOL_INFO_WARNING_80PCT_0X02"
ERR_EMMC_PRE_EOL_URGENT: str = "EMMC_PRE_EOL_INFO_URGENT_90PCT_0X03"
ERR_EMMC_PRE_EOL_RESERVED: str = "EMMC_PRE_EOL_INFO_RESERVED_INVALID"
ERR_EMMC_LIFE_TIME_UNDEFINED: str = "EMMC_LIFE_TIME_EST_UNDEFINED_0X00"
ERR_EMMC_LIFE_TIME_A_CRITICAL: str = "EMMC_LIFE_TIME_TYP_A_SLC_GT_80PCT"
ERR_EMMC_LIFE_TIME_B_CRITICAL: str = "EMMC_LIFE_TIME_TYP_B_MLC_GT_80PCT"
ERR_EMMC_LIFE_TIME_RESERVED: str = "EMMC_LIFE_TIME_EST_RESERVED_INVALID"
ERR_EXT_CSD_BOOT_POINTER_FLIPPED: str = "EXT_CSD_BOOT_PARTITION_POINTER_FLIPPED"
ERR_EXT_CSD_PARTITION_ACCESS_DIRTY: str = "EXT_CSD_PARTITION_ACCESS_NOT_UDA"

# ---------------------------------------------------------------------------
# Pillar 3 Constants — RAM-Only tmpfs / overlayfs Isolation
# ---------------------------------------------------------------------------

ERR_MOUNT_EMPTY_OR_MALFORMED: str = "MOUNT_TABLE_EMPTY_OR_MALFORMED"
ERR_MOUNT_RW_BLOCK_DEVICE: str = "MOUNT_RW_EMMC_BLOCK_DEVICE_FORBIDDEN"
ERR_MOUNT_MISSING_RO_NOATIME: str = "MOUNT_EMMC_BLOCK_MISSING_RO_NOATIME"
ERR_OVERLAY_MISSING_OR_INVALID_OPTIONS: str = "OVERLAY_MISSING_OR_INVALID_DIR_OPTIONS"
ERR_OVERLAY_UPPERDIR_NOT_TMPFS: str = "OVERLAY_UPPERDIR_NOT_ON_TMPFS"
ERR_OVERLAY_WORKDIR_NOT_TMPFS: str = "OVERLAY_WORKDIR_NOT_ON_TMPFS"
ERR_OVERLAY_UPPERDIR_ON_BLOCK_PATH: str = "OVERLAY_UPPERDIR_OR_WORKDIR_UNSAFE_PATH"
ERR_OVERLAY_NO_VOLATILE_OVERLAY_MOUNT: str = "OVERLAY_NO_STAGE_B_OVERLAY_MOUNT_PRESENT"

EMMC_BLOCK_DEVICE_PREFIXES: Tuple[str, ...] = (
    "/dev/mmcblk0",
    "/dev/nflasha",
    "/dev/cnflasha",
)


# ---------------------------------------------------------------------------
# Structured Dataclasses (Zero raw bytes fields exposed in repr/to_dict)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DonorRamdiskArtifactInfo:
    label: str
    source_mode: str
    byte_length: int
    sha256: str
    magic_ok: bool
    details: Dict[str, Any]


@dataclass(frozen=True)
class DonorRamdiskSnapshot:
    verification_mode: str
    read_only_access: bool
    artifacts: Tuple[DonorRamdiskArtifactInfo, ...]
    fx3_initrd_squashfs_ok: bool
    fx3_init2_tmpfs_observed: bool
    fx3_stock_fstab_rw_count: int
    fx6_dtb_fdt_ok: bool
    snapshot_sha256: str


@dataclass(frozen=True)
class CpioEntrySpec:
    path: str
    mode: int
    payload: bytes = b""
    uid: int = 0
    gid: int = 0
    nlink: int = 1
    mtime: int = 0
    ino: int = 1
    devmajor: int = 0
    devminor: int = 0
    rdevmajor: int = 0
    rdevminor: int = 0


@dataclass(frozen=True)
class CpioEntrySummary:
    path: str
    normalized_path: str
    ino: int
    mode: int
    file_type: str
    permissions_octal: str
    is_setuid: bool
    is_setgid: bool
    uid: int
    gid: int
    nlink: int
    mtime: int
    filesize: int
    devmajor: int
    devminor: int
    rdevmajor: int
    rdevminor: int
    header_offset: int
    data_offset: int
    payload_sha256: str
    symlink_target: Optional[str] = None


@dataclass(frozen=True)
class CpioParseResult:
    valid_structure: bool
    archive_bytes: int
    archive_sha256: str
    trailer_present: bool
    entries: Tuple[CpioEntrySummary, ...]
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CpioOverlayAuditReport:
    passed: bool
    status: str
    archive_bytes: int
    archive_sha256: str
    entry_count: int
    trailer_present: bool
    regular_file_count: int
    directory_count: int
    symlink_count: int
    block_node_count: int
    char_node_count: int
    setuid_count: int
    entries: Tuple[CpioEntrySummary, ...]
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_device_writes: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EmmcHealthAuditReport:
    passed: bool
    status: str
    stage_b_rehearsal_permitted: bool
    tier0_backup_preservation_required: bool
    ext_csd_sha256: str
    ext_csd_bytes: int
    ext_csd_rev: int
    pre_eol_info_raw: int
    pre_eol_info_hex: str
    pre_eol_status: str
    life_time_typ_a_raw: int
    life_time_typ_a_hex: str
    life_time_typ_a_label: str
    life_time_typ_a_pct_range: Tuple[int, int]
    life_time_typ_b_raw: int
    life_time_typ_b_hex: str
    life_time_typ_b_label: str
    life_time_typ_b_pct_range: Tuple[int, int]
    part_config_raw: int
    part_config_hex: str
    boot_ack: int
    boot_partition_enable: int
    boot_partition_name: str
    partition_access: int
    partition_access_name: str
    boot_pointer_stock_intact: bool
    recommended_action: str
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_device_writes: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MountTableEntry:
    device: str
    mountpoint: str
    fstype: str
    options: Tuple[str, ...]
    is_block_emmc: bool
    is_read_only: bool
    has_noatime: bool
    is_tmpfs: bool
    is_overlay: bool


@dataclass(frozen=True)
class OverlayIsolationCheck:
    mountpoint: str
    fstype: str
    lowerdir: str
    upperdir: str
    workdir: str
    upperdir_backing_fstype: Optional[str]
    workdir_backing_fstype: Optional[str]
    upperdir_on_tmpfs: bool
    workdir_on_tmpfs: bool
    safe: bool


@dataclass(frozen=True)
class MountTableIsolationReport:
    passed: bool
    status: str
    mount_count: int
    emmc_block_mounts_checked: int
    rw_block_mounts_found: Tuple[str, ...]
    non_ro_noatime_block_mounts: Tuple[str, ...]
    tmpfs_mountpoints: Tuple[str, ...]
    overlay_checks: Tuple[OverlayIsolationCheck, ...]
    all_upperdir_on_tmpfs: bool
    all_workdir_on_tmpfs: bool
    zero_rw_block_mounts: bool
    mount_table_sha256: str
    entries: Tuple[MountTableEntry, ...]
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_device_writes: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RamdiskOverlayAndEmmcHealthSuiteReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    donor_snapshot: DonorRamdiskSnapshot
    cpio_valid_report: CpioOverlayAuditReport
    cpio_reject_traversal_passed: bool
    cpio_reject_mmcblk_symlink_passed: bool
    cpio_reject_blk_node_passed: bool
    cpio_reject_setuid_passed: bool
    cpio_reject_missing_trailer_passed: bool
    cpio_reject_truncated_passed: bool
    emmc_healthy_report: EmmcHealthAuditReport
    emmc_reject_pre_eol_warning_passed: bool
    emmc_reject_pre_eol_urgent_passed: bool
    emmc_reject_lifetime_gt80_passed: bool
    emmc_reject_boot_pointer_flip_passed: bool
    mount_isolation_report: MountTableIsolationReport
    mount_reject_rw_mmcblk_passed: bool
    mount_reject_non_tmpfs_upperdir_passed: bool
    stage_b_containment_ready: bool
    suite_sha256: str
    otp_fuse_touches: int
    passive_tx_bytes_emitted: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    elapsed_seconds: float
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _canonical_sha256(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def _pad4_delta(n: int) -> int:
    return (4 - (n % 4)) % 4


def _file_type_name(mode: int) -> str:
    fmt = stat.S_IFMT(mode)
    return {
        stat.S_IFREG: "REG",
        stat.S_IFDIR: "DIR",
        stat.S_IFLNK: "LNK",
        stat.S_IFBLK: "BLK",
        stat.S_IFCHR: "CHR",
        stat.S_IFIFO: "FIFO",
        stat.S_IFSOCK: "SOCK",
    }.get(fmt, f"UNKNOWN_0x{fmt:x}")


# ---------------------------------------------------------------------------
# Donor Read-Only Inspection & Clean-Room Synthetic Fallback
# ---------------------------------------------------------------------------


def inspect_ramdisk_and_emmc_donors_readonly(
    *,
    force_clean_room: Optional[bool] = None,
) -> DonorRamdiskSnapshot:
    """Inspect local FX3/FX6 ramdisk, init2, fstab & DTB headers strictly via `os.O_RDONLY`,
    falling back deterministically to `CLEAN_ROOM_SYNTHETIC` when forced or absent.
    """
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)

    p1_path = None if clean_room else resolve_donor_path(DONOR_FX3_P1_205_RELPATH)
    init2_path = None if clean_room else resolve_donor_path(DONOR_FX3_INIT2_RELPATH)
    fstab_path = None if clean_room else resolve_donor_path(DONOR_FX3_FSTAB_RELPATH)
    dtb_path = None if clean_room else resolve_donor_path(DONOR_FX6_DTB_RELPATH)

    have_local = (
        (p1_path is not None and p1_path.is_file())
        and (init2_path is not None and init2_path.is_file())
        and (fstab_path is not None and fstab_path.is_file())
        and (dtb_path is not None and dtb_path.is_file())
    )

    artifacts: List[DonorRamdiskArtifactInfo] = []
    if have_local and p1_path and init2_path and fstab_path and dtb_path:
        verification_mode = "LOCAL_DONOR_O_RDONLY"

        # 1. FX3 2.05 p1 VFAT -> /boot/initrd.img SquashFS header
        p1_bytes = read_file(p1_path, MAX_P1)
        fat = FatP1(p1_bytes)
        initrd_bytes = fat.contents("/boot/initrd.img")
        sq_magic = initrd_bytes[0:4]
        sq_inodes, _sq_mtime, sq_bsize, _sq_frags, sq_comp, _sq_blog, _sq_flags, _sq_ids, sq_maj, sq_min = (
            struct.unpack_from("<4I6H", initrd_bytes, 4)
        )
        sq_bytes_used = struct.unpack_from("<Q", initrd_bytes, 40)[0]
        initrd_ok = (sq_magic == b"hsqs") and (sq_maj, sq_min) == (4, 0) and sq_inodes > 0
        artifacts.append(
            DonorRamdiskArtifactInfo(
                label="fx3_205_p1_initrd_squashfs",
                source_mode=verification_mode,
                byte_length=len(initrd_bytes),
                sha256=sha256(initrd_bytes).hexdigest(),
                magic_ok=initrd_ok,
                details={
                    "squashfs_magic_hex": sq_magic.hex(),
                    "version": f"{sq_maj}.{sq_min}",
                    "inodes": sq_inodes,
                    "block_size": sq_bsize,
                    "compression_id": sq_comp,
                    "bytes_used": sq_bytes_used,
                },
            )
        )

        # 2. FX3 nflasha7 /sbin/init2 script
        init2_bytes = read_file(init2_path, 1024 * 1024)
        init2_text = init2_bytes.decode("utf-8", errors="replace")
        init2_tmpfs_ok = ("tmpfs" in init2_text) and ("/sbin/initrc" in init2_text)
        artifacts.append(
            DonorRamdiskArtifactInfo(
                label="fx3_nflasha7_sbin_init2",
                source_mode=verification_mode,
                byte_length=len(init2_bytes),
                sha256=sha256(init2_bytes).hexdigest(),
                magic_ok=init2_tmpfs_ok,
                details={
                    "shebang": init2_text.splitlines()[0] if init2_text else "",
                    "has_tmpfs_mount": "tmpfs" in init2_text,
                    "has_fstab_mount": "FSTAB" in init2_text,
                },
            )
        )

        # 3. FX3 nflasha7 /sbin/initrc/fstab
        fstab_bytes = read_file(fstab_path, 1024 * 1024)
        fstab_text = fstab_bytes.decode("utf-8", errors="replace")
        rw_lines = [
            ln.strip()
            for ln in fstab_text.splitlines()
            if ln.strip() and not ln.strip().startswith("#") and "\trw," in ln
        ]
        fstab_ok = "/dev/nflasha" in fstab_text
        artifacts.append(
            DonorRamdiskArtifactInfo(
                label="fx3_nflasha7_initrc_fstab",
                source_mode=verification_mode,
                byte_length=len(fstab_bytes),
                sha256=sha256(fstab_bytes).hexdigest(),
                magic_ok=fstab_ok,
                details={
                    "stock_rw_nflasha_entries": len(rw_lines),
                },
            )
        )

        # 4. FX6 cxd90057.dtb FDT header
        dtb_bytes = read_file(dtb_path, 4 * 1024 * 1024)
        dtb_magic = struct.unpack_from(">I", dtb_bytes, 0)[0] if len(dtb_bytes) >= 8 else 0
        dtb_ok = dtb_magic == 0xD00DFEED
        artifacts.append(
            DonorRamdiskArtifactInfo(
                label="fx6_cxd90057_dtb",
                source_mode=verification_mode,
                byte_length=len(dtb_bytes),
                sha256=sha256(dtb_bytes).hexdigest(),
                magic_ok=dtb_ok,
                details={"fdt_magic_hex": f"0x{dtb_magic:08x}"},
            )
        )
        stock_rw_count = len(rw_lines)
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
        syn_initrd_hdr = struct.pack("<5I6H", 0x73717368, 45, 0, 131072, 1, 1, 17, 192, 2, 4, 0) + bytes(52)
        initrd_ok = True
        artifacts.append(
            DonorRamdiskArtifactInfo(
                label="fx3_205_p1_initrd_squashfs",
                source_mode=verification_mode,
                byte_length=len(syn_initrd_hdr),
                sha256=sha256(syn_initrd_hdr).hexdigest(),
                magic_ok=True,
                details={"squashfs_magic_hex": "68737173", "version": "4.0", "synthetic": True},
            )
        )

        syn_init2 = (
            b"#!/bin/busybox sh\nINITRC_DIR=/sbin/initrc\n"
            b"busybox mount -a -T $INITRC_DIR/fstab\nmount -t tmpfs none /tmp_wbshd\n"
        )
        init2_tmpfs_ok = True
        artifacts.append(
            DonorRamdiskArtifactInfo(
                label="fx3_nflasha7_sbin_init2",
                source_mode=verification_mode,
                byte_length=len(syn_init2),
                sha256=sha256(syn_init2).hexdigest(),
                magic_ok=True,
                details={"shebang": "#!/bin/busybox sh", "has_tmpfs_mount": True, "synthetic": True},
            )
        )

        syn_fstab = (
            b"/dev/nflasha2\t/setting\tvfat\trw,noatime,sync\t0\t0\n"
            b"/dev/nflasha15\t/usr\text2\tro,noatime,sync\t0\t0\n"
        )
        stock_rw_count = 1
        artifacts.append(
            DonorRamdiskArtifactInfo(
                label="fx3_nflasha7_initrc_fstab",
                source_mode=verification_mode,
                byte_length=len(syn_fstab),
                sha256=sha256(syn_fstab).hexdigest(),
                magic_ok=True,
                details={"stock_rw_nflasha_entries": stock_rw_count, "synthetic": True},
            )
        )

        syn_dtb = struct.pack(">II", 0xD00DFEED, 16875) + bytes(56)
        dtb_ok = True
        artifacts.append(
            DonorRamdiskArtifactInfo(
                label="fx6_cxd90057_dtb",
                source_mode=verification_mode,
                byte_length=len(syn_dtb),
                sha256=sha256(syn_dtb).hexdigest(),
                magic_ok=True,
                details={"fdt_magic_hex": "0xd00dfeed", "synthetic": True},
            )
        )

    snap_sha = _canonical_sha256(
        {
            "verification_mode": verification_mode,
            "artifacts": [asdict(a) for a in artifacts],
        }
    )
    return DonorRamdiskSnapshot(
        verification_mode=verification_mode,
        read_only_access=READ_ONLY_DONOR_ACCESS,
        artifacts=tuple(artifacts),
        fx3_initrd_squashfs_ok=initrd_ok,
        fx3_init2_tmpfs_observed=init2_tmpfs_ok,
        fx3_stock_fstab_rw_count=stock_rw_count,
        fx6_dtb_fdt_ok=dtb_ok,
        snapshot_sha256=snap_sha,
    )


# ---------------------------------------------------------------------------
# Pillar 1 — SVR4 Portable '070701' newc cpio Parser, Builder & Firewall
# ---------------------------------------------------------------------------


def _encode_cpio_entry(spec: CpioEntrySpec) -> bytes:
    name_bytes = spec.path.encode("utf-8") + b"\x00"
    payload = spec.payload
    header = (
        f"{CPIO_NEWC_MAGIC_STR}"
        f"{spec.ino & 0xFFFFFFFF:08x}"
        f"{spec.mode & 0xFFFFFFFF:08x}"
        f"{spec.uid & 0xFFFFFFFF:08x}"
        f"{spec.gid & 0xFFFFFFFF:08x}"
        f"{spec.nlink & 0xFFFFFFFF:08x}"
        f"{spec.mtime & 0xFFFFFFFF:08x}"
        f"{len(payload) & 0xFFFFFFFF:08x}"
        f"{spec.devmajor & 0xFFFFFFFF:08x}"
        f"{spec.devminor & 0xFFFFFFFF:08x}"
        f"{spec.rdevmajor & 0xFFFFFFFF:08x}"
        f"{spec.rdevminor & 0xFFFFFFFF:08x}"
        f"{len(name_bytes) & 0xFFFFFFFF:08x}"
        f"{0:08x}"
    ).encode("ascii")
    require(len(header) == CPIO_HEADER_SIZE, "internal cpio header must be 110 bytes")
    name_pad = b"\x00" * _pad4_delta(CPIO_HEADER_SIZE + len(name_bytes))
    data_pad = b"\x00" * _pad4_delta(len(payload))
    return header + name_bytes + name_pad + payload + data_pad


def build_cpio_newc(
    entries: Sequence[CpioEntrySpec],
    *,
    include_trailer: bool = True,
    trailer_block_pad: int = 0,
) -> bytes:
    """Build a pure-Python SVR4 `'070701'` `newc` `cpio` archive."""
    chunks: List[bytes] = [_encode_cpio_entry(spec) for spec in entries]
    if include_trailer:
        chunks.append(
            _encode_cpio_entry(
                CpioEntrySpec(
                    path=CPIO_TRAILER_NAME,
                    mode=0,
                    payload=b"",
                    uid=0,
                    gid=0,
                    nlink=1,
                    mtime=0,
                    ino=0,
                )
            )
        )
    out = b"".join(chunks)
    if trailer_block_pad > 0:
        rem = len(out) % trailer_block_pad
        if rem:
            out += b"\x00" * (trailer_block_pad - rem)
    return out


def build_synthetic_stage_b_cpio_overlay() -> bytes:
    """Build a valid, clean-room Stage-B FX6 RAM-disk overlay `'070701'` archive."""
    entries = [
        CpioEntrySpec(path="tmp", mode=stat.S_IFDIR | 0o755, nlink=2, ino=100),
        CpioEntrySpec(path="tmp/stage_b", mode=stat.S_IFDIR | 0o755, nlink=2, ino=101),
        CpioEntrySpec(path="tmp/stage_b/bin", mode=stat.S_IFDIR | 0o755, nlink=2, ino=102),
        CpioEntrySpec(
            path="tmp/stage_b/bin/busybox",
            mode=stat.S_IFREG | 0o755,
            payload=b"#!/bin/sh\n# clean-room synthetic busybox placeholder\nexit 0\n",
            ino=103,
        ),
        CpioEntrySpec(
            path="tmp/stage_b/bin/sh",
            mode=stat.S_IFLNK | 0o777,
            payload=b"busybox",
            ino=104,
        ),
        CpioEntrySpec(
            path="tmp/stage_b/sbin",
            mode=stat.S_IFDIR | 0o755,
            nlink=2,
            ino=105,
        ),
        CpioEntrySpec(
            path="tmp/stage_b/sbin/init2_stage_b",
            mode=stat.S_IFREG | 0o750,
            payload=b"#!/tmp/stage_b/bin/sh\nmount -t tmpfs none /tmp/stage_b/upper\n",
            ino=106,
        ),
        CpioEntrySpec(path="tmp/stage_b/lib", mode=stat.S_IFDIR | 0o755, nlink=2, ino=107),
        CpioEntrySpec(
            path="tmp/stage_b/lib/libInfraCore.so",
            mode=stat.S_IFREG | 0o644,
            payload=b"FX6_STAGE_B_OVERLAY_SYNTHETIC_LIB_MARKER_V1",
            ino=108,
        ),
    ]
    return build_cpio_newc(entries, include_trailer=True, trailer_block_pad=512)


def _normalize_cpio_path(raw_path: str) -> str:
    stripped = raw_path
    while stripped.startswith("./"):
        stripped = stripped[2:]
    if stripped == "":
        return "."
    return stripped


def parse_cpio_newc(data: bytes) -> CpioParseResult:
    """Parse an SVR4 `'070701'` `newc` `cpio` archive strictly without trusting unaligned offsets."""
    archive_len = len(data)
    archive_sha = sha256(data).hexdigest()
    entries: List[CpioEntrySummary] = []
    error_codes: List[str] = []
    errors: List[str] = []
    trailer_present = False

    def _add_err(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    if archive_len < CPIO_HEADER_SIZE:
        _add_err(
            ERR_CPIO_EMPTY_OR_TRUNCATED_HEADER,
            f"Archive length {archive_len} < {CPIO_HEADER_SIZE}-byte cpio newc header.",
        )
        return CpioParseResult(
            valid_structure=False,
            archive_bytes=archive_len,
            archive_sha256=archive_sha,
            trailer_present=False,
            entries=(),
            error_codes=tuple(error_codes),
            errors=tuple(errors),
        )

    if archive_len > CPIO_MAX_ARCHIVE_BYTES:
        _add_err(
            ERR_CPIO_TRUNCATED_PAYLOAD,
            f"Archive size {archive_len} exceeds safety limit {CPIO_MAX_ARCHIVE_BYTES}.",
        )
        return CpioParseResult(
            valid_structure=False,
            archive_bytes=archive_len,
            archive_sha256=archive_sha,
            trailer_present=False,
            entries=(),
            error_codes=tuple(error_codes),
            errors=tuple(errors),
        )

    cursor = 0
    while cursor < archive_len:
        if len(entries) >= CPIO_MAX_ENTRIES:
            _add_err(ERR_CPIO_ENTRY_LIMIT_EXCEEDED, f"CPIO entries exceeded cap {CPIO_MAX_ENTRIES}.")
            break

        if cursor + CPIO_HEADER_SIZE > archive_len:
            _add_err(
                ERR_CPIO_EMPTY_OR_TRUNCATED_HEADER,
                f"Truncated cpio header at offset {cursor} (remaining={archive_len - cursor}).",
            )
            break

        hdr_offset = cursor
        magic = data[cursor : cursor + 6]
        if magic != CPIO_NEWC_MAGIC_BYTES:
            _add_err(
                ERR_CPIO_BAD_MAGIC,
                f"Bad cpio magic at offset {cursor}: hex={magic.hex()} (expected 303730373031).",
            )
            break

        hex_blob = data[cursor + 6 : cursor + CPIO_HEADER_SIZE]
        try:
            hex_str = hex_blob.decode("ascii")
            fields = [int(hex_str[i * 8 : (i + 1) * 8], 16) for i in range(13)]
        except (UnicodeDecodeError, ValueError) as exc:
            _add_err(ERR_CPIO_BAD_HEX_FIELD, f"Malformed hex field at offset {cursor}: {exc}")
            break

        (
            ino,
            mode,
            uid,
            gid,
            nlink,
            mtime,
            filesize,
            devmajor,
            devminor,
            rdevmajor,
            rdevminor,
            namesize,
            _check,
        ) = fields

        if namesize == 0 or namesize > CPIO_MAX_NAME_BYTES:
            _add_err(
                ERR_CPIO_BAD_NAMESIZE,
                f"Invalid c_namesize={namesize} at offset {cursor} (must be 1..{CPIO_MAX_NAME_BYTES}).",
            )
            break

        name_start = cursor + CPIO_HEADER_SIZE
        name_end = name_start + namesize
        name_pad = _pad4_delta(CPIO_HEADER_SIZE + namesize)
        data_start = name_end + name_pad

        if data_start > archive_len:
            _add_err(
                ERR_CPIO_TRUNCATED_NAME,
                f"Truncated pathname/padding at offset {cursor}: need {data_start}, have {archive_len}.",
            )
            break

        raw_name_bytes = data[name_start:name_end]
        if raw_name_bytes[-1] != 0:
            _add_err(
                ERR_CPIO_NAME_NOT_NUL_TERMINATED,
                f"Entry pathname at offset {cursor} lacks NUL terminator.",
            )
            break

        if b"\x00" in raw_name_bytes[:-1]:
            _add_err(
                ERR_CPIO_EMBEDDED_NUL_IN_NAME,
                f"Entry pathname at offset {cursor} contains embedded NUL byte.",
            )
            break

        raw_name = raw_name_bytes[:-1].decode("utf-8", errors="replace")
        data_end = data_start + filesize
        data_pad = _pad4_delta(filesize)
        next_cursor = data_end + data_pad

        if data_end > archive_len or next_cursor > archive_len:
            _add_err(
                ERR_CPIO_TRUNCATED_PAYLOAD,
                f"Truncated payload/padding for '{raw_name}' at offset {cursor}: "
                f"need {next_cursor}, archive_len={archive_len}.",
            )
            break

        payload = data[data_start:data_end]
        cursor = next_cursor

        if raw_name == CPIO_TRAILER_NAME:
            trailer_present = True
            if filesize != 0:
                _add_err(
                    ERR_CPIO_NONZERO_TRAILER_SIZE,
                    f"TRAILER!!! entry has non-zero filesize={filesize}.",
                )
            tail = data[cursor:]
            if tail and any(b != 0 for b in tail):
                _add_err(
                    ERR_CPIO_TRAILING_GARBAGE_AFTER_TRAILER,
                    f"Non-zero bytes ({len(tail)}B) found after TRAILER!!! sentinel.",
                )
            break

        fmt = stat.S_IFMT(mode)
        symlink_target: Optional[str] = None
        if fmt == stat.S_IFLNK:
            symlink_target = payload.decode("utf-8", errors="replace")

        entries.append(
            CpioEntrySummary(
                path=raw_name,
                normalized_path=_normalize_cpio_path(raw_name),
                ino=ino,
                mode=mode,
                file_type=_file_type_name(mode),
                permissions_octal=f"0o{stat.S_IMODE(mode):04o}",
                is_setuid=bool(mode & stat.S_ISUID),
                is_setgid=bool(mode & stat.S_ISGID),
                uid=uid,
                gid=gid,
                nlink=nlink,
                mtime=mtime,
                filesize=filesize,
                devmajor=devmajor,
                devminor=devminor,
                rdevmajor=rdevmajor,
                rdevminor=rdevminor,
                header_offset=hdr_offset,
                data_offset=data_start,
                payload_sha256=sha256(payload).hexdigest(),
                symlink_target=symlink_target,
            )
        )

    if not trailer_present and ERR_CPIO_EMPTY_OR_TRUNCATED_HEADER not in error_codes and ERR_CPIO_TRUNCATED_PAYLOAD not in error_codes:
        _add_err(ERR_CPIO_MISSING_TRAILER, "Archive lacks mandatory 'TRAILER!!!' sentinel entry.")
    elif not trailer_present and ERR_CPIO_MISSING_TRAILER not in error_codes:
        _add_err(ERR_CPIO_MISSING_TRAILER, "Archive truncated before 'TRAILER!!!' sentinel entry.")

    return CpioParseResult(
        valid_structure=len(error_codes) == 0 and trailer_present,
        archive_bytes=archive_len,
        archive_sha256=archive_sha,
        trailer_present=trailer_present,
        entries=tuple(entries),
        error_codes=tuple(error_codes),
        errors=tuple(errors),
    )


def _is_forbidden_device_target(text: str) -> bool:
    low = text.lower()
    return any(tok in low for tok in FORBIDDEN_CPIO_DEVICE_TOKENS)


def audit_cpio_ramdisk_overlay(
    data: bytes,
    *,
    allowed_setuid_paths: Sequence[str] = (),
    allowed_char_nodes: Sequence[Tuple[str, int, int]] = (),
    allowed_absolute_symlink_targets: Sequence[str] = DEFAULT_ALLOWED_ABS_SYMLINK_TARGETS,
) -> CpioOverlayAuditReport:
    """Validate an SVR4 `'070701'` `newc` `cpio` Stage-B RAM-disk overlay archive fail-closed."""
    parsed = parse_cpio_newc(data)
    error_codes: List[str] = list(parsed.error_codes)
    errors: List[str] = list(parsed.errors)
    warnings: List[str] = []

    def _add_err(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    seen_paths: set[str] = set()
    allowed_suid_set = {_normalize_cpio_path(p) for p in allowed_setuid_paths}
    allowed_chr_set = {(_normalize_cpio_path(p), maj, mn) for p, maj, mn in allowed_char_nodes}
    allowed_abs_links = set(allowed_absolute_symlink_targets)

    reg_count = 0
    dir_count = 0
    lnk_count = 0
    blk_count = 0
    chr_count = 0
    suid_count = 0

    for entry in parsed.entries:
        raw_path = entry.path
        norm_path = entry.normalized_path

        # 1. Path traversal / absolute path / duplicate checks
        if raw_path == "" or raw_path.startswith("/"):
            _add_err(
                ERR_CPIO_ABSOLUTE_PATH,
                f"Entry '{raw_path}' uses an absolute or empty path (Stage-B overlay requires relative paths).",
            )
        if "\\" in raw_path or ".." in raw_path.split("/"):
            _add_err(
                ERR_CPIO_PATH_TRAVERSAL,
                f"Entry '{raw_path}' contains forbidden '..' or backslash path traversal.",
            )
        if _is_forbidden_device_target(raw_path):
            _add_err(
                ERR_CPIO_PATH_TRAVERSAL,
                f"Entry '{raw_path}' targets forbidden raw flash/kernel device path.",
            )
        if norm_path != "." and norm_path in seen_paths:
            _add_err(
                ERR_CPIO_DUPLICATE_PATH,
                f"Duplicate normalized entry path '{norm_path}' in cpio overlay.",
            )
        seen_paths.add(norm_path)

        # 2. File type & device node firewall
        fmt = stat.S_IFMT(entry.mode)
        if fmt == stat.S_IFREG:
            reg_count += 1
        elif fmt == stat.S_IFDIR:
            dir_count += 1
            if entry.filesize != 0:
                _add_err(
                    ERR_CPIO_NONZERO_NONREG_FILESIZE,
                    f"Directory '{raw_path}' has non-zero filesize={entry.filesize}.",
                )
        elif fmt == stat.S_IFLNK:
            lnk_count += 1
            target = entry.symlink_target or ""
            if target == "" or "\x00" in target:
                _add_err(
                    ERR_CPIO_SYMLINK_ESCAPE,
                    f"Symlink '{raw_path}' has empty or NUL-containing target.",
                )
            elif _is_forbidden_device_target(target):
                _add_err(
                    ERR_CPIO_MMCBLK_SYMLINK_ESCAPE,
                    f"Symlink '{raw_path}' -> '{target}' attempts raw eMMC/kernel device escape.",
                )
            elif target.startswith("/"):
                if target not in allowed_abs_links:
                    _add_err(
                        ERR_CPIO_SYMLINK_ESCAPE,
                        f"Symlink '{raw_path}' -> '{target}' points to non-allowlisted absolute host path.",
                    )
            else:
                parent_dir = posixpath.dirname(norm_path) if norm_path != "." else ""
                combined = posixpath.join(parent_dir, target) if parent_dir else target
                resolved = posixpath.normpath(combined)
                if resolved == ".." or resolved.startswith("../") or resolved.startswith("/"):
                    _add_err(
                        ERR_CPIO_SYMLINK_ESCAPE,
                        f"Symlink '{raw_path}' -> '{target}' escapes overlay containment root ('{resolved}').",
                    )
        elif fmt == stat.S_IFBLK:
            blk_count += 1
            _add_err(
                ERR_CPIO_UNAUTHORIZED_BLK_NODE,
                f"Forbidden S_IFBLK block device node '{raw_path}' (rdev={entry.rdevmajor}:{entry.rdevminor}).",
            )
        elif fmt == stat.S_IFCHR:
            chr_count += 1
            if (
                entry.filesize != 0
                or entry.rdevmajor in FORBIDDEN_DEVICE_MAJORS
                or (entry.rdevmajor == 1 and entry.rdevminor in (1, 2))
                or _is_forbidden_device_target(raw_path)
                or (norm_path, entry.rdevmajor, entry.rdevminor) not in allowed_chr_set
            ):
                _add_err(
                    ERR_CPIO_UNAUTHORIZED_CHR_NODE,
                    f"Unauthorized S_IFCHR char device node '{raw_path}' (rdev={entry.rdevmajor}:{entry.rdevminor}).",
                )
        else:
            _add_err(
                ERR_CPIO_UNSUPPORTED_FILE_TYPE,
                f"Unsupported special file type {entry.file_type} on '{raw_path}'.",
            )

        # 3. Setuid / Setgid root binary check
        if entry.is_setuid or (entry.is_setgid and entry.gid == 0):
            suid_count += 1
            if norm_path not in allowed_suid_set:
                _add_err(
                    ERR_CPIO_UNAUTHORIZED_SETUID,
                    f"Unauthorized setuid/setgid binary '{raw_path}' (mode={entry.permissions_octal}, uid={entry.uid}).",
                )

    passed = parsed.valid_structure and len(error_codes) == 0
    status = "VERIFIED_CPIO_RAMDISK_OVERLAY" if passed else "REJECTED_CPIO_RAMDISK_OVERLAY"
    return CpioOverlayAuditReport(
        passed=passed,
        status=status,
        archive_bytes=parsed.archive_bytes,
        archive_sha256=parsed.archive_sha256,
        entry_count=len(parsed.entries),
        trailer_present=parsed.trailer_present,
        regular_file_count=reg_count,
        directory_count=dir_count,
        symlink_count=lnk_count,
        block_node_count=blk_count,
        char_node_count=chr_count,
        setuid_count=suid_count,
        entries=parsed.entries,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Pillar 2 — JEDEC eMMC 5.1 EXT_CSD [267..269] & [179] Health Auditor
# ---------------------------------------------------------------------------


def _describe_life_time(val: int) -> Tuple[str, Tuple[int, int]]:
    if val == EXT_CSD_LIFE_TIME_NOT_DEFINED:
        return "NOT_DEFINED", (0, 0)
    if val in LIFE_TIME_PCT_MAP:
        lo, hi = LIFE_TIME_PCT_MAP[val]
        suffix = "_CRITICAL" if val >= EXT_CSD_LIFE_TIME_CRITICAL_MIN else ""
        return f"{lo}_TO_{hi}_PCT{suffix}", (lo, hi)
    if val == EXT_CSD_LIFE_TIME_EXCEEDED:
        return "EXCEEDED_MAX_ESTIMATED_LIFETIME", (100, 100)
    return f"RESERVED_0X{val:02X}", (-1, -1)


def audit_emmc_ext_csd_health(
    ext_csd_data: bytes,
    *,
    expected_boot_partition_enable: int = FX3_STOCK_BOOT_PARTITION_ENABLE,
    expected_boot_ack: Optional[int] = FX3_STOCK_BOOT_ACK,
    require_uda_access_zero: bool = True,
) -> EmmcHealthAuditReport:
    """Audit 512-byte JEDEC eMMC 5.1 `EXT_CSD` (`[267..269]` Pre-EOL/Life-Time & `[179]` `PART_CONFIG`).

    Fails closed before any Stage-B rehearsal if `PRE_EOL_INFO >= 0x02`,
    `DEVICE_LIFE_TIME_EST_TYP_A/B >= 0x09` (`>80%` wear), or `PARTITION_CONFIG [179]`
    boot partition pointer was flipped away from factory stock.
    """
    ext_sha = sha256(ext_csd_data).hexdigest()
    if len(ext_csd_data) != EXT_CSD_SIZE:
        return EmmcHealthAuditReport(
            passed=False,
            status="FAIL_CLOSED_INVALID_EXT_CSD",
            stage_b_rehearsal_permitted=False,
            tier0_backup_preservation_required=True,
            ext_csd_sha256=ext_sha,
            ext_csd_bytes=len(ext_csd_data),
            ext_csd_rev=0,
            pre_eol_info_raw=0,
            pre_eol_info_hex="0x00",
            pre_eol_status="INVALID_EXT_CSD_SIZE",
            life_time_typ_a_raw=0,
            life_time_typ_a_hex="0x00",
            life_time_typ_a_label="INVALID_EXT_CSD_SIZE",
            life_time_typ_a_pct_range=(-1, -1),
            life_time_typ_b_raw=0,
            life_time_typ_b_hex="0x00",
            life_time_typ_b_label="INVALID_EXT_CSD_SIZE",
            life_time_typ_b_pct_range=(-1, -1),
            part_config_raw=0,
            part_config_hex="0x00",
            boot_ack=0,
            boot_partition_enable=0,
            boot_partition_name="INVALID_SIZE",
            partition_access=0,
            partition_access_name="INVALID_SIZE",
            boot_pointer_stock_intact=False,
            recommended_action="ABORT_STAGE_B_INSPECT_512B_EXT_CSD_READONLY",
            error_codes=(ERR_EXT_CSD_BAD_LENGTH,),
            errors=(f"EXT_CSD length {len(ext_csd_data)} != {EXT_CSD_SIZE} bytes.",),
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    ext_rev = ext_csd_data[EXT_CSD_REV_IDX]
    part_cfg = ext_csd_data[EXT_CSD_PART_CONFIG_IDX]
    reserved_bit7 = (part_cfg >> 7) & 0x1
    boot_ack = (part_cfg >> 6) & 0x1
    boot_en = (part_cfg >> 3) & 0x7
    part_acc = part_cfg & 0x7

    boot_names = {0: "NOT_BOOT_ENABLED", 1: "BOOT0", 2: "BOOT1", 7: "USER_AREA"}
    acc_names = {0: "USER_AREA", 1: "BOOT0", 2: "BOOT1", 3: "RPMB"}
    boot_name = boot_names.get(boot_en, f"RESERVED_{boot_en}")
    acc_name = acc_names.get(part_acc, f"RESERVED_{part_acc}")

    pre_eol = ext_csd_data[EXT_CSD_PRE_EOL_INFO_IDX]
    life_a = ext_csd_data[EXT_CSD_LIFE_TIME_A_IDX]
    life_b = ext_csd_data[EXT_CSD_LIFE_TIME_B_IDX]

    pre_eol_status = PRE_EOL_STATUS_MAP.get(pre_eol, f"RESERVED_0X{pre_eol:02X}")
    life_a_label, life_a_pct = _describe_life_time(life_a)
    life_b_label, life_b_pct = _describe_life_time(life_b)

    error_codes: List[str] = []
    errors: List[str] = []

    def _add_err(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    # 1. PRE_EOL_INFO [267]
    tier0_urgent = False
    if pre_eol == EXT_CSD_PRE_EOL_NOT_DEFINED:
        _add_err(ERR_EMMC_PRE_EOL_UNDEFINED, "EXT_CSD[267] PRE_EOL_INFO is 0x00 (not defined).")
    elif pre_eol == EXT_CSD_PRE_EOL_WARNING:
        tier0_urgent = True
        _add_err(
            ERR_EMMC_PRE_EOL_WARNING,
            "EXT_CSD[267] PRE_EOL_INFO=0x02 (Warning: >=80% reserved blocks consumed) — Stage-B blocked; run read-only Tier-0 backup immediately!",
        )
    elif pre_eol == EXT_CSD_PRE_EOL_URGENT:
        tier0_urgent = True
        _add_err(
            ERR_EMMC_PRE_EOL_URGENT,
            "EXT_CSD[267] PRE_EOL_INFO=0x03 (Urgent: >=90% reserved blocks consumed) — Stage-B blocked; run read-only Tier-0 backup immediately!",
        )
    elif pre_eol > EXT_CSD_PRE_EOL_URGENT:
        tier0_urgent = True
        _add_err(
            ERR_EMMC_PRE_EOL_RESERVED,
            f"EXT_CSD[267] PRE_EOL_INFO=0x{pre_eol:02x} is reserved/invalid.",
        )

    # 2. DEVICE_LIFE_TIME_EST_TYP_A [268] (SLC) & TYP_B [269] (MLC)
    if life_a == EXT_CSD_LIFE_TIME_NOT_DEFINED:
        _add_err(ERR_EMMC_LIFE_TIME_UNDEFINED, "EXT_CSD[268] LIFE_TIME_TYP_A is 0x00 (not defined).")
    elif EXT_CSD_LIFE_TIME_CRITICAL_MIN <= life_a <= EXT_CSD_LIFE_TIME_EXCEEDED:
        tier0_urgent = True
        _add_err(
            ERR_EMMC_LIFE_TIME_A_CRITICAL,
            f"EXT_CSD[268] LIFE_TIME_TYP_A=0x{life_a:02x} ({life_a_label}, >80% SLC wear) — Stage-B blocked; immediate read-only Tier-0 backup required!",
        )
    elif life_a > EXT_CSD_LIFE_TIME_EXCEEDED:
        tier0_urgent = True
        _add_err(
            ERR_EMMC_LIFE_TIME_RESERVED,
            f"EXT_CSD[268] LIFE_TIME_TYP_A=0x{life_a:02x} is reserved/invalid.",
        )

    if life_b == EXT_CSD_LIFE_TIME_NOT_DEFINED:
        _add_err(ERR_EMMC_LIFE_TIME_UNDEFINED, "EXT_CSD[269] LIFE_TIME_TYP_B is 0x00 (not defined).")
    elif EXT_CSD_LIFE_TIME_CRITICAL_MIN <= life_b <= EXT_CSD_LIFE_TIME_EXCEEDED:
        tier0_urgent = True
        _add_err(
            ERR_EMMC_LIFE_TIME_B_CRITICAL,
            f"EXT_CSD[269] LIFE_TIME_TYP_B=0x{life_b:02x} ({life_b_label}, >80% MLC wear) — Stage-B blocked; immediate read-only Tier-0 backup required!",
        )
    elif life_b > EXT_CSD_LIFE_TIME_EXCEEDED:
        tier0_urgent = True
        _add_err(
            ERR_EMMC_LIFE_TIME_RESERVED,
            f"EXT_CSD[269] LIFE_TIME_TYP_B=0x{life_b:02x} is reserved/invalid.",
        )

    # 3. PARTITION_CONFIG [179] boot pointer sanity check
    boot_pointer_intact = True
    if reserved_bit7 != 0:
        boot_pointer_intact = False
        _add_err(
            ERR_EXT_CSD_BOOT_POINTER_FLIPPED,
            f"EXT_CSD[179] PART_CONFIG=0x{part_cfg:02x} has reserved bit7 set.",
        )
    if boot_en != expected_boot_partition_enable:
        boot_pointer_intact = False
        _add_err(
            ERR_EXT_CSD_BOOT_POINTER_FLIPPED,
            f"EXT_CSD[179] BOOT_PARTITION_ENABLE={boot_en} ({boot_name}) flipped away from factory stock {expected_boot_partition_enable}.",
        )
    if expected_boot_ack is not None and boot_ack != expected_boot_ack:
        boot_pointer_intact = False
        _add_err(
            ERR_EXT_CSD_BOOT_POINTER_FLIPPED,
            f"EXT_CSD[179] BOOT_ACK={boot_ack} differs from factory stock {expected_boot_ack}.",
        )
    if require_uda_access_zero and part_acc != FX3_STOCK_PARTITION_ACCESS:
        boot_pointer_intact = False
        _add_err(
            ERR_EXT_CSD_PARTITION_ACCESS_DIRTY,
            f"EXT_CSD[179] PARTITION_ACCESS={part_acc} ({acc_name}) was not reset to USER_AREA (0).",
        )

    passed = len(error_codes) == 0
    if passed:
        status = "HEALTHY_STAGE_B_ELIGIBLE"
        action = "PROCEED_VOLATILE_RAM_STAGE_B_WITH_READONLY_EMMC"
    elif tier0_urgent:
        status = "FAIL_CLOSED_TIER0_BACKUP_REQUIRED"
        action = "IMMEDIATE_READONLY_TIER0_BACKUP_PRESERVATION_DO_NOT_REHEARSE"
    elif not boot_pointer_intact:
        status = "FAIL_CLOSED_BOOT_POINTER_FLIPPED"
        action = "ABORT_REHEARSAL_DO_NOT_MUTATE_PART_CONFIG_AUDIT_BOOT_CHAIN"
    else:
        status = "FAIL_CLOSED_EMMC_HEALTH_INVALID"
        action = "ABORT_STAGE_B_VERIFY_EXT_CSD_REGISTERS_READONLY"

    return EmmcHealthAuditReport(
        passed=passed,
        status=status,
        stage_b_rehearsal_permitted=passed,
        tier0_backup_preservation_required=tier0_urgent or (not passed),
        ext_csd_sha256=ext_sha,
        ext_csd_bytes=len(ext_csd_data),
        ext_csd_rev=ext_rev,
        pre_eol_info_raw=pre_eol,
        pre_eol_info_hex=f"0x{pre_eol:02x}",
        pre_eol_status=pre_eol_status,
        life_time_typ_a_raw=life_a,
        life_time_typ_a_hex=f"0x{life_a:02x}",
        life_time_typ_a_label=life_a_label,
        life_time_typ_a_pct_range=life_a_pct,
        life_time_typ_b_raw=life_b,
        life_time_typ_b_hex=f"0x{life_b:02x}",
        life_time_typ_b_label=life_b_label,
        life_time_typ_b_pct_range=life_b_pct,
        part_config_raw=part_cfg,
        part_config_hex=f"0x{part_cfg:02x}",
        boot_ack=boot_ack,
        boot_partition_enable=boot_en,
        boot_partition_name=boot_name,
        partition_access=part_acc,
        partition_access_name=acc_name,
        boot_pointer_stock_intact=boot_pointer_intact,
        recommended_action=action,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Pillar 3 — RAM-Only tmpfs / overlayfs Upperdir Isolation Proof
# ---------------------------------------------------------------------------


def build_synthetic_safe_stage_b_mount_table(*, include_ro_emmc_mounts: bool = True) -> str:
    """Construct a compliant Stage-B `/proc/mounts` spec (tmpfs upperdir/workdir, zero rw eMMC)."""
    lines = [
        "rootfs / rootfs ro 0 0",
        "proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0",
        "sysfs /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0",
        "tmpfs /tmp tmpfs rw,nosuid,nodev,mode=1777 0 0",
        "tmpfs /tmp/stage_b tmpfs rw,nosuid,nodev,mode=0755 0 0",
    ]
    if include_ro_emmc_mounts:
        lines.extend(
            [
                "/dev/mmcblk0p1 /mnt/p1_ro vfat ro,noatime 0 0",
                "/dev/mmcblk0p7 /rootfs ext2 ro,noatime,sync 0 0",
                "/dev/mmcblk0p14 /usr ext2 ro,noatime,sync 0 0",
            ]
        )
    lines.append(
        "overlay /tmp/stage_b/merged overlay rw,relatime,lowerdir=/usr,upperdir=/tmp/stage_b/upper,workdir=/tmp/stage_b/work 0 0"
    )
    return "\n".join(lines) + "\n"


def _is_emmc_block_device(device: str) -> bool:
    low = device.strip().lower()
    return any(low.startswith(prefix) for prefix in EMMC_BLOCK_DEVICE_PREFIXES)


def _resolve_backing_mount(target_path: str, entries: Sequence[MountTableEntry]) -> Optional[MountTableEntry]:
    norm_target = posixpath.normpath(target_path)
    best: Optional[MountTableEntry] = None
    best_len = -1
    for entry in entries:
        if entry.is_overlay:
            continue
        mp = posixpath.normpath(entry.mountpoint)
        if mp == "/" or norm_target == mp or norm_target.startswith(mp.rstrip("/") + "/"):
            if len(mp) > best_len:
                best = entry
                best_len = len(mp)
    return best


def _extract_overlay_dir_opts(options: Sequence[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for opt in options:
        if "=" in opt:
            k, v = opt.split("=", 1)
            if k in ("lowerdir", "upperdir", "workdir"):
                out[k] = v
    return out


def audit_ramdisk_overlay_mount_table(
    mount_table_text: str,
    *,
    require_overlay_entry: bool = True,
) -> MountTableIsolationReport:
    """Verify mount-table specs guarantee `upperdir`/`workdir` reside strictly on `tmpfs` (RAM)
    and every `/dev/mmcblk0*` / `/dev/nflasha*` entry is either unmounted or `ro,noatime` with zero `rw`.
    """
    mt_sha = sha256(mount_table_text.encode("utf-8")).hexdigest()
    entries: List[MountTableEntry] = []
    error_codes: List[str] = []
    errors: List[str] = []

    def _add_err(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    raw_lines = [
        ln.strip()
        for ln in mount_table_text.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if not raw_lines:
        _add_err(ERR_MOUNT_EMPTY_OR_MALFORMED, "Mount table specification is empty.")

    for idx, line in enumerate(raw_lines, start=1):
        parts = line.split()
        if len(parts) < 4:
            _add_err(
                ERR_MOUNT_EMPTY_OR_MALFORMED,
                f"Malformed mount line {idx}: expected '>=4' whitespace fields, got {len(parts)}.",
            )
            continue
        device, mountpoint, fstype, raw_opts = parts[0], parts[1], parts[2], parts[3]
        opts = tuple(o.strip() for o in raw_opts.split(",") if o.strip())
        is_blk = _is_emmc_block_device(device)
        is_ro = ("ro" in opts) and ("rw" not in opts)
        has_noatime = "noatime" in opts
        entries.append(
            MountTableEntry(
                device=device,
                mountpoint=mountpoint,
                fstype=fstype,
                options=opts,
                is_block_emmc=is_blk,
                is_read_only=is_ro,
                has_noatime=has_noatime,
                is_tmpfs=(fstype == "tmpfs"),
                is_overlay=(fstype in ("overlay", "overlayfs")),
            )
        )

    rw_block_mounts: List[str] = []
    non_ro_noatime_mounts: List[str] = []
    emmc_checked = 0

    for e in entries:
        if e.is_block_emmc:
            emmc_checked += 1
            if "rw" in e.options or not e.is_read_only:
                rw_block_mounts.append(f"{e.device}->{e.mountpoint}")
                _add_err(
                    ERR_MOUNT_RW_BLOCK_DEVICE,
                    f"Block device '{e.device}' mounted at '{e.mountpoint}' is NOT read-only (opts={','.join(e.options)}).",
                )
            if not (e.is_read_only and e.has_noatime):
                non_ro_noatime_mounts.append(f"{e.device}->{e.mountpoint}")
                _add_err(
                    ERR_MOUNT_MISSING_RO_NOATIME,
                    f"Mounted eMMC block device '{e.device}' at '{e.mountpoint}' must enforce 'ro,noatime'.",
                )

    tmpfs_mounts = tuple(e.mountpoint for e in entries if e.is_tmpfs)
    overlay_checks: List[OverlayIsolationCheck] = []

    for e in entries:
        if not e.is_overlay:
            continue
        dir_opts = _extract_overlay_dir_opts(e.options)
        lowerdir = dir_opts.get("lowerdir", "")
        upperdir = dir_opts.get("upperdir", "")
        workdir = dir_opts.get("workdir", "")

        if not lowerdir or not upperdir or not workdir:
            _add_err(
                ERR_OVERLAY_MISSING_OR_INVALID_OPTIONS,
                f"Overlay mount at '{e.mountpoint}' missing lowerdir/upperdir/workdir options.",
            )
            overlay_checks.append(
                OverlayIsolationCheck(
                    mountpoint=e.mountpoint,
                    fstype=e.fstype,
                    lowerdir=lowerdir,
                    upperdir=upperdir,
                    workdir=workdir,
                    upperdir_backing_fstype=None,
                    workdir_backing_fstype=None,
                    upperdir_on_tmpfs=False,
                    workdir_on_tmpfs=False,
                    safe=False,
                )
            )
            continue

        upper_mount = _resolve_backing_mount(upperdir, entries)
        work_mount = _resolve_backing_mount(workdir, entries)
        upper_fs = upper_mount.fstype if upper_mount else None
        work_fs = work_mount.fstype if work_mount else None
        upper_tmpfs = upper_fs == "tmpfs"
        work_tmpfs = work_fs == "tmpfs"

        if not upper_tmpfs:
            _add_err(
                ERR_OVERLAY_UPPERDIR_NOT_TMPFS,
                f"Overlay upperdir '{upperdir}' resolves to fstype={upper_fs!r} (must be 'tmpfs').",
            )
        if not work_tmpfs:
            _add_err(
                ERR_OVERLAY_WORKDIR_NOT_TMPFS,
                f"Overlay workdir '{workdir}' resolves to fstype={work_fs!r} (must be 'tmpfs').",
            )
        if _is_emmc_block_device(upperdir) or _is_emmc_block_device(workdir) or posixpath.normpath(upperdir) == posixpath.normpath(workdir):
            _add_err(
                ERR_OVERLAY_UPPERDIR_ON_BLOCK_PATH,
                f"Overlay upperdir='{upperdir}' / workdir='{workdir}' violates volatile tmpfs isolation.",
            )
            upper_tmpfs = False
            work_tmpfs = False

        safe = upper_tmpfs and work_tmpfs and (len(rw_block_mounts) == 0)
        overlay_checks.append(
            OverlayIsolationCheck(
                mountpoint=e.mountpoint,
                fstype=e.fstype,
                lowerdir=lowerdir,
                upperdir=upperdir,
                workdir=workdir,
                upperdir_backing_fstype=upper_fs,
                workdir_backing_fstype=work_fs,
                upperdir_on_tmpfs=upper_tmpfs,
                workdir_on_tmpfs=work_tmpfs,
                safe=safe,
            )
        )

    if require_overlay_entry and len(overlay_checks) == 0:
        _add_err(
            ERR_OVERLAY_NO_VOLATILE_OVERLAY_MOUNT,
            "No Stage-B overlay/overlayfs mount entry found in mount table.",
        )

    all_upper_tmpfs = bool(overlay_checks) and all(c.upperdir_on_tmpfs for c in overlay_checks)
    all_work_tmpfs = bool(overlay_checks) and all(c.workdir_on_tmpfs for c in overlay_checks)
    zero_rw = len(rw_block_mounts) == 0
    passed = len(error_codes) == 0 and zero_rw and (not require_overlay_entry or (all_upper_tmpfs and all_work_tmpfs))

    return MountTableIsolationReport(
        passed=passed,
        status="VERIFIED_TMPFS_OVERLAY_ISOLATION" if passed else "FAIL_MOUNT_TABLE_ISOLATION",
        mount_count=len(entries),
        emmc_block_mounts_checked=emmc_checked,
        rw_block_mounts_found=tuple(rw_block_mounts),
        non_ro_noatime_block_mounts=tuple(non_ro_noatime_mounts),
        tmpfs_mountpoints=tmpfs_mounts,
        overlay_checks=tuple(overlay_checks),
        all_upperdir_on_tmpfs=all_upper_tmpfs,
        all_workdir_on_tmpfs=all_work_tmpfs,
        zero_rw_block_mounts=zero_rw,
        mount_table_sha256=mt_sha,
        entries=tuple(entries),
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Unified Phase 101 Suite Runner
# ---------------------------------------------------------------------------


def run_ramdisk_overlay_and_emmc_health_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> RamdiskOverlayAndEmmcHealthSuiteReport:
    """Run all three Phase 101 pillars + fail-closed adversarial drills in `< 0.5s`."""
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    require(PERSISTENT_WRITE_RELEASE is False, "persistent_write_release must stay False")
    require(ALLOW_BOOT_PARTITION_TARGETING is False, "allow_boot_partition_targeting must stay False")
    require(ALLOW_DESTRUCTIVE_FASTBOOT is False, "allow_destructive_fastboot must stay False")
    require(OTP_FUSE_TOUCHES == 0, "otp_fuse_touches must stay 0")
    require(PASSIVE_TX_BYTES_EMITTED == 0, "passive_tx_bytes_emitted must stay 0")
    require(PHYSICAL_DEVICE_WRITES == 0, "physical_device_writes must stay 0")

    t0 = time.monotonic()
    donor_snapshot = inspect_ramdisk_and_emmc_donors_readonly(force_clean_room=force_clean_room)

    # Pillar 1: Valid overlay + 6 adversarial fail-closed drills
    valid_cpio = build_synthetic_stage_b_cpio_overlay()
    cpio_valid_report = audit_cpio_ramdisk_overlay(valid_cpio)

    cpio_trav = audit_cpio_ramdisk_overlay(
        build_cpio_newc([CpioEntrySpec(path="../../etc/passwd", mode=stat.S_IFREG | 0o644, payload=b"x")])
    )
    cpio_reject_traversal = (not cpio_trav.passed) and (ERR_CPIO_PATH_TRAVERSAL in cpio_trav.error_codes)

    cpio_sym = audit_cpio_ramdisk_overlay(
        build_cpio_newc([CpioEntrySpec(path="tmp/stage_b/raw", mode=stat.S_IFLNK | 0o777, payload=b"/dev/mmcblk0p1")])
    )
    cpio_reject_mmcblk_symlink = (not cpio_sym.passed) and (
        ERR_CPIO_MMCBLK_SYMLINK_ESCAPE in cpio_sym.error_codes
    )

    cpio_blk = audit_cpio_ramdisk_overlay(
        build_cpio_newc([CpioEntrySpec(path="tmp/stage_b/emmc0", mode=stat.S_IFBLK | 0o600, rdevmajor=179, rdevminor=0)])
    )
    cpio_reject_blk_node = (not cpio_blk.passed) and (ERR_CPIO_UNAUTHORIZED_BLK_NODE in cpio_blk.error_codes)

    cpio_suid = audit_cpio_ramdisk_overlay(
        build_cpio_newc([CpioEntrySpec(path="tmp/stage_b/bin/su_backdoor", mode=stat.S_IFREG | stat.S_ISUID | 0o755, payload=b"x")])
    )
    cpio_reject_setuid = (not cpio_suid.passed) and (ERR_CPIO_UNAUTHORIZED_SETUID in cpio_suid.error_codes)

    cpio_no_tr = audit_cpio_ramdisk_overlay(
        build_cpio_newc([CpioEntrySpec(path="tmp/stage_b/ok", mode=stat.S_IFREG | 0o644, payload=b"ok")], include_trailer=False)
    )
    cpio_reject_missing_trailer = (not cpio_no_tr.passed) and (ERR_CPIO_MISSING_TRAILER in cpio_no_tr.error_codes)

    cpio_trunc = audit_cpio_ramdisk_overlay(valid_cpio[: len(valid_cpio) // 2])
    cpio_reject_truncated = not cpio_trunc.passed

    # Pillar 2: Healthy EXT_CSD + 4 fail-closed health/boot-pointer drills
    emmc_healthy_report = audit_emmc_ext_csd_health(build_synthetic_ext_csd())

    emmc_warn = audit_emmc_ext_csd_health(build_synthetic_ext_csd(pre_eol_info=EXT_CSD_PRE_EOL_WARNING))
    emmc_reject_pre_eol_warning = (
        (not emmc_warn.passed)
        and (not emmc_warn.stage_b_rehearsal_permitted)
        and emmc_warn.tier0_backup_preservation_required
        and (ERR_EMMC_PRE_EOL_WARNING in emmc_warn.error_codes)
    )

    emmc_urg = audit_emmc_ext_csd_health(build_synthetic_ext_csd(pre_eol_info=EXT_CSD_PRE_EOL_URGENT))
    emmc_reject_pre_eol_urgent = (
        (not emmc_urg.passed)
        and (not emmc_urg.stage_b_rehearsal_permitted)
        and emmc_urg.tier0_backup_preservation_required
        and (ERR_EMMC_PRE_EOL_URGENT in emmc_urg.error_codes)
    )

    emmc_life = audit_emmc_ext_csd_health(build_synthetic_ext_csd(life_time_a=0x09, life_time_b=0x0A))
    emmc_reject_lifetime_gt80 = (
        (not emmc_life.passed)
        and (not emmc_life.stage_b_rehearsal_permitted)
        and emmc_life.tier0_backup_preservation_required
        and (ERR_EMMC_LIFE_TIME_A_CRITICAL in emmc_life.error_codes)
        and (ERR_EMMC_LIFE_TIME_B_CRITICAL in emmc_life.error_codes)
    )

    emmc_flip = audit_emmc_ext_csd_health(build_synthetic_ext_csd(part_config=0x50))  # BOOT1 instead of BOOT0
    emmc_reject_boot_pointer_flip = (
        (not emmc_flip.passed)
        and (not emmc_flip.boot_pointer_stock_intact)
        and (ERR_EXT_CSD_BOOT_POINTER_FLIPPED in emmc_flip.error_codes)
    )

    # Pillar 3: RAM-Only tmpfs/overlayfs mount isolation + 2 fail-closed drills
    safe_mt = build_synthetic_safe_stage_b_mount_table()
    mount_isolation_report = audit_ramdisk_overlay_mount_table(safe_mt)

    rw_mt = safe_mt.replace("/dev/mmcblk0p1 /mnt/p1_ro vfat ro,noatime 0 0", "/dev/mmcblk0p1 /mnt/p1_rw vfat rw,noatime 0 0")
    rw_mt_rep = audit_ramdisk_overlay_mount_table(rw_mt)
    mount_reject_rw_mmcblk = (not rw_mt_rep.passed) and (ERR_MOUNT_RW_BLOCK_DEVICE in rw_mt_rep.error_codes)

    bad_upper_mt = "\n".join(
        [
            "tmpfs /tmp tmpfs rw,nosuid,nodev 0 0",
            "/dev/mmcblk0p14 /usr ext2 ro,noatime 0 0",
            "overlay /tmp/merged overlay rw,lowerdir=/usr,upperdir=/usr/upper,workdir=/tmp/work 0 0",
        ]
    )
    bad_upper_rep = audit_ramdisk_overlay_mount_table(bad_upper_mt)
    mount_reject_non_tmpfs_upperdir = (not bad_upper_rep.passed) and (
        ERR_OVERLAY_UPPERDIR_NOT_TMPFS in bad_upper_rep.error_codes
    )

    errors: List[str] = []
    checks = {
        "donor_fx3_initrd_squashfs_ok": donor_snapshot.fx3_initrd_squashfs_ok,
        "donor_fx3_init2_tmpfs_observed": donor_snapshot.fx3_init2_tmpfs_observed,
        "donor_fx6_dtb_fdt_ok": donor_snapshot.fx6_dtb_fdt_ok,
        "cpio_valid_passed": cpio_valid_report.passed,
        "cpio_reject_traversal": cpio_reject_traversal,
        "cpio_reject_mmcblk_symlink": cpio_reject_mmcblk_symlink,
        "cpio_reject_blk_node": cpio_reject_blk_node,
        "cpio_reject_setuid": cpio_reject_setuid,
        "cpio_reject_missing_trailer": cpio_reject_missing_trailer,
        "cpio_reject_truncated": cpio_reject_truncated,
        "emmc_healthy_passed": emmc_healthy_report.passed,
        "emmc_reject_pre_eol_warning": emmc_reject_pre_eol_warning,
        "emmc_reject_pre_eol_urgent": emmc_reject_pre_eol_urgent,
        "emmc_reject_lifetime_gt80": emmc_reject_lifetime_gt80,
        "emmc_reject_boot_pointer_flip": emmc_reject_boot_pointer_flip,
        "mount_isolation_passed": mount_isolation_report.passed,
        "mount_reject_rw_mmcblk": mount_reject_rw_mmcblk,
        "mount_reject_non_tmpfs_upperdir": mount_reject_non_tmpfs_upperdir,
    }
    for name, ok in checks.items():
        if not ok:
            errors.append(f"SUITE_CHECK_FAILED:{name}")

    all_passed = (
        len(errors) == 0
        and (PERSISTENT_EMMC_WRITES_AUTHORIZED is False)
        and (PERSISTENT_WRITE_RELEASE is False)
        and (ALLOW_BOOT_PARTITION_TARGETING is False)
        and (ALLOW_DESTRUCTIVE_FASTBOOT is False)
        and (OTP_FUSE_TOUCHES == 0)
        and (PASSIVE_TX_BYTES_EMITTED == 0)
        and (PHYSICAL_DEVICE_WRITES == 0)
    )
    stage_b_containment_ready = (
        cpio_valid_report.passed
        and emmc_healthy_report.stage_b_rehearsal_permitted
        and mount_isolation_report.passed
        and all_passed
    )

    suite_sha = _canonical_sha256(
        {
            "schema": RAMDISK_EMMC_HEALTH_SCHEMA,
            "version": RAMDISK_EMMC_HEALTH_VERSION,
            "verification_mode": donor_snapshot.verification_mode,
            "donor_snapshot_sha256": donor_snapshot.snapshot_sha256,
            "cpio_archive_sha256": cpio_valid_report.archive_sha256,
            "emmc_ext_csd_sha256": emmc_healthy_report.ext_csd_sha256,
            "mount_table_sha256": mount_isolation_report.mount_table_sha256,
            "checks": checks,
            "all_passed": all_passed,
        }
    )

    return RamdiskOverlayAndEmmcHealthSuiteReport(
        schema=RAMDISK_EMMC_HEALTH_SCHEMA,
        version=RAMDISK_EMMC_HEALTH_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_passed,
        status=STATUS_VERIFIED_RAMDISK_EMMC_HEALTH if all_passed else STATUS_FAIL_RAMDISK_EMMC_HEALTH,
        donor_snapshot=donor_snapshot,
        cpio_valid_report=cpio_valid_report,
        cpio_reject_traversal_passed=cpio_reject_traversal,
        cpio_reject_mmcblk_symlink_passed=cpio_reject_mmcblk_symlink,
        cpio_reject_blk_node_passed=cpio_reject_blk_node,
        cpio_reject_setuid_passed=cpio_reject_setuid,
        cpio_reject_missing_trailer_passed=cpio_reject_missing_trailer,
        cpio_reject_truncated_passed=cpio_reject_truncated,
        emmc_healthy_report=emmc_healthy_report,
        emmc_reject_pre_eol_warning_passed=emmc_reject_pre_eol_warning,
        emmc_reject_pre_eol_urgent_passed=emmc_reject_pre_eol_urgent,
        emmc_reject_lifetime_gt80_passed=emmc_reject_lifetime_gt80,
        emmc_reject_boot_pointer_flip_passed=emmc_reject_boot_pointer_flip,
        mount_isolation_report=mount_isolation_report,
        mount_reject_rw_mmcblk_passed=mount_reject_rw_mmcblk,
        mount_reject_non_tmpfs_upperdir_passed=mount_reject_non_tmpfs_upperdir,
        stage_b_containment_ready=stage_b_containment_ready,
        suite_sha256=suite_sha,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        elapsed_seconds=round(time.monotonic() - t0, 6),
        errors=tuple(errors),
    )


__all__ = [
    "ALLOW_BOOT_PARTITION_TARGETING",
    "ALLOW_DESTRUCTIVE_FASTBOOT",
    "CPIO_HEADER_SIZE",
    "CPIO_MAX_ARCHIVE_BYTES",
    "CPIO_MAX_ENTRIES",
    "CPIO_MAX_NAME_BYTES",
    "CPIO_NEWC_MAGIC_BYTES",
    "CPIO_NEWC_MAGIC_STR",
    "CPIO_TRAILER_NAME",
    "DEFAULT_ALLOWED_ABS_SYMLINK_TARGETS",
    "DONOR_FX3_FSTAB_RELPATH",
    "DONOR_FX3_INIT2_RELPATH",
    "DONOR_FX3_P1_205_RELPATH",
    "DONOR_FX6_DTB_RELPATH",
    "EMMC_BLOCK_DEVICE_PREFIXES",
    "ERR_CPIO_ABSOLUTE_PATH",
    "ERR_CPIO_BAD_HEX_FIELD",
    "ERR_CPIO_BAD_MAGIC",
    "ERR_CPIO_BAD_NAMESIZE",
    "ERR_CPIO_DUPLICATE_PATH",
    "ERR_CPIO_EMBEDDED_NUL_IN_NAME",
    "ERR_CPIO_EMPTY_OR_TRUNCATED_HEADER",
    "ERR_CPIO_ENTRY_LIMIT_EXCEEDED",
    "ERR_CPIO_MISSING_TRAILER",
    "ERR_CPIO_MMCBLK_SYMLINK_ESCAPE",
    "ERR_CPIO_NAME_NOT_NUL_TERMINATED",
    "ERR_CPIO_NONZERO_NONREG_FILESIZE",
    "ERR_CPIO_NONZERO_TRAILER_SIZE",
    "ERR_CPIO_PATH_TRAVERSAL",
    "ERR_CPIO_SYMLINK_ESCAPE",
    "ERR_CPIO_TRAILING_GARBAGE_AFTER_TRAILER",
    "ERR_CPIO_TRUNCATED_NAME",
    "ERR_CPIO_TRUNCATED_PAYLOAD",
    "ERR_CPIO_UNAUTHORIZED_BLK_NODE",
    "ERR_CPIO_UNAUTHORIZED_CHR_NODE",
    "ERR_CPIO_UNAUTHORIZED_SETUID",
    "ERR_CPIO_UNSUPPORTED_FILE_TYPE",
    "ERR_EMMC_LIFE_TIME_A_CRITICAL",
    "ERR_EMMC_LIFE_TIME_B_CRITICAL",
    "ERR_EMMC_LIFE_TIME_RESERVED",
    "ERR_EMMC_LIFE_TIME_UNDEFINED",
    "ERR_EMMC_PRE_EOL_RESERVED",
    "ERR_EMMC_PRE_EOL_UNDEFINED",
    "ERR_EMMC_PRE_EOL_URGENT",
    "ERR_EMMC_PRE_EOL_WARNING",
    "ERR_EXT_CSD_BAD_LENGTH",
    "ERR_EXT_CSD_BOOT_POINTER_FLIPPED",
    "ERR_EXT_CSD_PARTITION_ACCESS_DIRTY",
    "ERR_MOUNT_EMPTY_OR_MALFORMED",
    "ERR_MOUNT_MISSING_RO_NOATIME",
    "ERR_MOUNT_RW_BLOCK_DEVICE",
    "ERR_OVERLAY_MISSING_OR_INVALID_OPTIONS",
    "ERR_OVERLAY_NO_VOLATILE_OVERLAY_MOUNT",
    "ERR_OVERLAY_UPPERDIR_NOT_TMPFS",
    "ERR_OVERLAY_UPPERDIR_ON_BLOCK_PATH",
    "ERR_OVERLAY_WORKDIR_NOT_TMPFS",
    "EXT_CSD_LIFE_TIME_CRITICAL_MIN",
    "EXT_CSD_LIFE_TIME_EXCEEDED",
    "EXT_CSD_LIFE_TIME_MAX_SAFE",
    "EXT_CSD_LIFE_TIME_NOT_DEFINED",
    "EXT_CSD_PRE_EOL_NORMAL",
    "EXT_CSD_PRE_EOL_NOT_DEFINED",
    "EXT_CSD_PRE_EOL_URGENT",
    "EXT_CSD_PRE_EOL_WARNING",
    "FORBIDDEN_CPIO_DEVICE_TOKENS",
    "FORBIDDEN_DEVICE_MAJORS",
    "FX3_STOCK_BOOT_ACK",
    "FX3_STOCK_BOOT_PARTITION_ENABLE",
    "FX3_STOCK_PARTITION_ACCESS",
    "FX3_STOCK_PART_CONFIG",
    "LIFE_TIME_PCT_MAP",
    "OTP_FUSE_TOUCHES",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHYSICAL_DEVICE_WRITES",
    "PRE_EOL_STATUS_MAP",
    "RAMDISK_EMMC_HEALTH_SCHEMA",
    "RAMDISK_EMMC_HEALTH_VERSION",
    "READ_ONLY_DONOR_ACCESS",
    "STATUS_FAIL_RAMDISK_EMMC_HEALTH",
    "STATUS_VERIFIED_RAMDISK_EMMC_HEALTH",
    "CpioEntrySpec",
    "CpioEntrySummary",
    "CpioOverlayAuditReport",
    "CpioParseResult",
    "DonorRamdiskArtifactInfo",
    "DonorRamdiskSnapshot",
    "EmmcHealthAuditReport",
    "MountTableEntry",
    "MountTableIsolationReport",
    "OverlayIsolationCheck",
    "RamdiskOverlayAndEmmcHealthSuiteReport",
    "audit_cpio_ramdisk_overlay",
    "audit_emmc_ext_csd_health",
    "audit_ramdisk_overlay_mount_table",
    "build_cpio_newc",
    "build_synthetic_safe_stage_b_mount_table",
    "build_synthetic_stage_b_cpio_overlay",
    "inspect_ramdisk_and_emmc_donors_readonly",
    "parse_cpio_newc",
    "run_ramdisk_overlay_and_emmc_health_suite",
]
