"""Phase 57 — Non-Journaled exFAT (`BootChecksum` / `VolumeDirty` / `.RSV`) & Dual CFexpress Media Firewall.

Operationalizes Wave-4 Phase 50 media-safety research (`exfat_media_hygiene_ok`,
Microsoft/SDA exFAT specification) into a deterministic, fail-closed media
integrity & production-footage isolation firewall for `outputs/fx3-safety/`:

1. **Pure-Python `exFAT` VBR (`EXFAT   `) & 12-Sector `BootChecksum` Verifier**:
   - Parses Main (`Sectors 0..11`) and Backup (`Sectors 12..23`) Boot Regions.
   - Verifies exact Microsoft/SDA 32-bit rolling `BootChecksum` across the first
     11 sectors (`0..10` and `12..22`), explicitly skipping `VolumeFlags`
     (byte offsets `106..107`, `0x6A..0x6B`) and `PercentInUse` (byte offset
     `112`, `0x70`) per the exFAT specification, and checking every 32-bit slot
     in Sector `11` and Sector `23`.
   - Enforces `FileSystemName == b"EXFAT   "`, `MustBeZero` (`53` zero bytes),
     power-of-two `BytesPerSectorShift` (`9..12` -> `512..4096 B`) and
     `SectorsPerClusterShift` (`0..25 - BytesPerSectorShift`), `BootSignature == 0xAA55`,
     geometry invariants, `VolumeDirty` (`VolumeFlags & 0x0002`), and
     `MediaFailure` (`VolumeFlags & 0x0004`).

2. **Sony Camera Media Tree (`XDROOT` FX6 MXF vs `PRIVATE/M4ROOT` FX3 MP4 + `.RSV`) Firewall**:
   - Inspects both `Slot A` and `Slot B` CFexpress Type A / SDXC cards (either
     via read-only directory scan or deterministic virtual/manifest file lists).
   - Detects live client production footage (`XDROOT/Clip/*.MXF`, `XDROOT/Sub/*`,
     `PRIVATE/M4ROOT/CLIP/*.MP4`, `M4ROOT/CLIP/*.MP4`, `DCIM/*`) and unfinalized
     Sony `.RSV` power-loss recovery clips (plus `FOUND.000/*.CHK` `chkdsk /f`
     remnants), **blocking `H0`/`H1` trial entry fail-closed** unless dedicated
     blank / dedicated lab rehearsal media is verified.

3. **Strict `p1` `FAT12`/`FAT16` vs External `exFAT` Filesystem Separation**:
   - Audits internal/capsule `p1` failsafe VBR (`FAT12` / `FAT16`, rejecting
     `EXFAT   ` or `FAT32`) using `os.O_RDONLY` on local FX3 `v7.02` donor
     `nflasha1` with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback.
   - Enforces strict device/mount separation between internal `p1` (`nflasha1`)
     and external `Slot A` / `Slot B` `exFAT` media, with
     `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` hard-locked.

Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- All file reads strictly use `os.open(..., os.O_RDONLY)`.
- Never prints raw binary `bytes` reprs (always `.hex()`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path, PurePosixPath
import re
import struct
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

EXFAT_MEDIA_INTEGRITY_GUARD_SCHEMA: str = "fx3-exfat-media-integrity-guard-v1"
EXFAT_MEDIA_INTEGRITY_GUARD_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[3]

# Microsoft / SDA exFAT Boot Region Specification Constants
EXFAT_FS_NAME: bytes = b"EXFAT   "
EXFAT_FS_NAME_HEX: str = EXFAT_FS_NAME.hex()
EXFAT_MUST_BE_ZERO_OFFSET: int = 11
EXFAT_MUST_BE_ZERO_LEN: int = 53
EXFAT_VOLUME_FLAGS_OFFSET: int = 106  # 0x6A
EXFAT_PERCENT_IN_USE_OFFSET: int = 112  # 0x70
EXFAT_BOOT_CHECKSUM_SKIP_OFFSETS: Tuple[int, ...] = (106, 107, 112)
EXFAT_BOOT_SIGNATURE: int = 0xAA55
EXFAT_EXTENDED_BOOT_SIGNATURE: int = 0xAA550000

EXFAT_FLAG_ACTIVE_FAT: int = 0x0001
EXFAT_FLAG_VOLUME_DIRTY: int = 0x0002
EXFAT_FLAG_MEDIA_FAILURE: int = 0x0004
EXFAT_FLAG_CLEAR_TO_ZERO: int = 0x0008

EXFAT_MIN_SECTOR_SHIFT: int = 9   # 512 bytes
EXFAT_MAX_SECTOR_SHIFT: int = 12  # 4096 bytes
EXFAT_MAX_CLUSTER_SIZE_SHIFT: int = 25  # 32 MiB
EXFAT_BOOT_REGION_SECTORS: int = 12
EXFAT_CHECKSUM_INPUT_SECTORS: int = 11
EXFAT_FULL_BOOT_AREA_SECTORS: int = 24

# Slot & Media Constants
SLOT_A: str = "SLOT_A"
SLOT_B: str = "SLOT_B"
MEDIA_TYPE_CFEXPRESS_A: str = "CFEXPRESS_TYPE_A"
MEDIA_TYPE_SDXC: str = "SDXC"

# Internal p1 failsafe donor expectations (FX3 v7.02 update-engine 2.05 nflasha1)
PINNED_P1_DONOR_SIZE: int = 19377152
PINNED_P1_FAT_TYPE: str = "FAT12"
VALID_P1_FAT_TYPES: Tuple[str, ...] = ("FAT12", "FAT16")

# Canonical Status & Violation Codes
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_BLOCKED_EXFAT_VBR_INVALID: str = "BLOCKED_EXFAT_VBR_INVALID"
STATUS_BLOCKED_EXFAT_BOOT_CHECKSUM: str = "BLOCKED_EXFAT_BOOT_CHECKSUM_MISMATCH"
STATUS_BLOCKED_EXFAT_BACKUP_MISMATCH: str = "BLOCKED_EXFAT_BACKUP_REGION_MISMATCH"
STATUS_BLOCKED_EXFAT_VOLUME_DIRTY: str = "BLOCKED_EXFAT_VOLUME_DIRTY"
STATUS_BLOCKED_EXFAT_MEDIA_FAILURE: str = "BLOCKED_EXFAT_MEDIA_FAILURE"
STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT: str = "BLOCKED_PRODUCTION_FOOTAGE_PRESENT"
STATUS_BLOCKED_UNFINALIZED_RSV_PRESENT: str = "BLOCKED_UNFINALIZED_RSV_CLIP_PRESENT"
STATUS_BLOCKED_CHKDSK_FOUND_CHK_PRESENT: str = "BLOCKED_CHKDSK_FOUND_CHK_PRESENT"
STATUS_BLOCKED_NO_LAB_MEDIA_CARD: str = "BLOCKED_NO_DEDICATED_LAB_MEDIA_CARD"
STATUS_BLOCKED_FILESYSTEM_SEPARATION: str = "BLOCKED_FILESYSTEM_SEPARATION_VIOLATION"
STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID: str = "BLOCKED_P1_FAILSAFE_VBR_INVALID"
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = "BLOCKED_PERSISTENT_EMMC_WRITE_FORBIDDEN"

INTERNAL_EMMC_OR_P1_TOKENS: Tuple[str, ...] = (
    "/dev/nflasha",
    "/dev/cnflasha",
    "/dev/pnflasha",
    "/dev/mmcblk0",
    "/dev/mtd",
    "/dev/boot0",
    "/dev/boot1",
    "p1:/",
    "/updater",
    "/setting",
    "/boot",
)

PRODUCTION_CLIP_EXTENSIONS: Tuple[str, ...] = (".mxf", ".mp4")
PRODUCTION_STILL_EXTENSIONS: Tuple[str, ...] = (".arw", ".jpg", ".jpeg", ".hif", ".cr3")


# ---------------------------------------------------------------------------
# Data Models (Raw bytes never stored/printed; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExfatVbrParseResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    file_system_name_hex: str
    file_system_name_ok: bool
    must_be_zero_ok: bool
    bytes_per_sector_shift: int
    sectors_per_cluster_shift: int
    bytes_per_sector: int
    sectors_per_cluster: int
    bytes_per_cluster: int
    sector_shift_power_of_two_ok: bool
    cluster_shift_power_of_two_ok: bool
    partition_offset: int
    volume_length: int
    fat_offset: int
    fat_length: int
    cluster_heap_offset: int
    cluster_count: int
    first_cluster_of_root_directory: int
    volume_serial_hex: str
    file_system_revision_hex: str
    volume_flags: int
    active_fat: int
    volume_dirty: bool
    media_failure: bool
    clear_to_zero: bool
    number_of_fats: int
    drive_select: int
    percent_in_use: int
    boot_signature_hex: str
    boot_signature_ok: bool
    geometry_ok: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExfatBootRegionAuditResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    bytes_per_sector: int
    bytes_per_cluster: int
    main_vbr: Dict[str, Any]
    backup_vbr: Optional[Dict[str, Any]]
    computed_main_checksum_hex: str
    expected_main_checksum_hex: str
    main_checksum_ok: bool
    main_checksum_sector_uniform: bool
    main_extended_signatures_ok: bool
    backup_region_present: bool
    computed_backup_checksum_hex: Optional[str]
    expected_backup_checksum_hex: Optional[str]
    backup_checksum_ok: Optional[bool]
    backup_checksum_sector_uniform: Optional[bool]
    backup_extended_signatures_ok: Optional[bool]
    main_vs_backup_consistent: Optional[bool]
    volume_dirty: bool
    media_failure: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SonyMediaTreeInspection:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    detected_trees: Tuple[str, ...]
    total_files_scanned: int
    fx6_xdroot_mxf_clips: Tuple[str, ...]
    fx3_m4root_mp4_clips: Tuple[str, ...]
    other_production_media: Tuple[str, ...]
    unfinalized_rsv_files: Tuple[str, ...]
    chkdsk_chk_files: Tuple[str, ...]
    zero_byte_clip_stubs: Tuple[str, ...]
    c2pa_card_credentials: Tuple[str, ...]
    sony_metadata_files: Tuple[str, ...]
    total_production_bytes: int
    is_clean_lab_media: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MediaSlotConfig:
    slot_id: str = SLOT_A
    inserted: bool = True
    media_type: str = MEDIA_TYPE_CFEXPRESS_A
    device_node: str = "/dev/mmcblk1p1"
    mount_point: str = "/mnt/slot_a"
    exfat_boot_bytes: Optional[bytes] = None
    exfat_image_path: Optional[Path] = None
    card_root: Optional[Path] = None
    card_entries: Optional[Sequence[Union[str, Tuple[str, int], Mapping[str, Any]]]] = None
    dedicated_lab_card: bool = True
    require_backup_region: bool = True


@dataclass(frozen=True)
class MediaSlotAuditResult:
    slot_id: str
    inserted: bool
    media_type: str
    device_node: str
    mount_point: str
    dedicated_lab_card: bool
    passed: bool
    status: str
    violation_codes: Tuple[str, ...]
    exfat_audit: Optional[Dict[str, Any]]
    media_tree_audit: Optional[Dict[str, Any]]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DualSlotMediaFirewallResult:
    valid: bool
    status: str
    h0_h1_trial_entry_allowed: bool
    violation_codes: Tuple[str, ...]
    inserted_lab_slots: Tuple[str, ...]
    slot_a_result: Dict[str, Any]
    slot_b_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P1VfatAuditResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    fat_type: str
    oem_name_hex: str
    oem_name_ascii: str
    filsys_type_hex: str
    filsys_type_ascii: str
    bytes_per_sector: int
    sectors_per_cluster: int
    reserved_sectors: int
    num_fats: int
    root_entry_count: int
    total_sectors: int
    fat_sectors: int
    data_clusters: int
    media_descriptor_hex: str
    boot_signature_hex: str
    is_exfat_spoofed: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FilesystemSeparationResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    p1_device_node: str
    p1_filesystem: str
    p1_vbr_audit: Dict[str, Any]
    slot_a_device_node: str
    slot_b_device_node: str
    strict_separation_enforced: bool
    blocked_cross_domain_targets: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExfatMediaIntegrityReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    violation_codes: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    dual_slot_firewall: Dict[str, Any]
    filesystem_separation: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers (Strict O_RDONLY, zero raw bytes printing)
# ---------------------------------------------------------------------------


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _is_power_of_two(val: int) -> bool:
    return val > 0 and (val & (val - 1)) == 0


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes", "on")


def read_slice_o_rdonly(path: Union[str, Path], offset: int, length: int) -> bytes:
    """Read a bounded slice strictly via `os.open(..., os.O_RDONLY)`."""
    if offset < 0 or length < 0:
        raise ValueError("offset and length must be non-negative")
    fd = os.open(str(path), os.O_RDONLY)
    try:
        if offset > 0:
            os.lseek(fd, offset, os.SEEK_SET)
        out = bytearray()
        while len(out) < length:
            chunk = os.read(fd, length - len(out))
            if not chunk:
                break
            out.extend(chunk)
        return bytes(out)
    finally:
        os.close(fd)


def _resolve_donor_p1_path(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> Optional[Path]:
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)
    if paths.work_root is None:
        return None
    cand = (
        paths.work_root
        / "fx3-color-port-20261027"
        / "input-20261028"
        / "original-update-engine"
        / "2.05"
        / "nflasha1"
    )
    if cand.is_file():
        return cand
    return None


# ---------------------------------------------------------------------------
# 1. Pure-Python exFAT VBR (`EXFAT   `) & 12-Sector `BootChecksum` Verifier
# ---------------------------------------------------------------------------


def compute_exfat_boot_checksum(
    sectors_0_to_10: bytes,
    bytes_per_sector: int = 512,
) -> int:
    """Compute the exact Microsoft/SDA exFAT 32-bit rolling BootChecksum.

    Sums over the first 11 sectors (`11 * bytes_per_sector` bytes), explicitly
    skipping `VolumeFlags` (byte offsets `106..107`) and `PercentInUse` (byte
    offset `112`) per the Microsoft exFAT specification.
    """
    if bytes_per_sector not in (512, 1024, 2048, 4096):
        raise ValueError(f"Unsupported exFAT bytes_per_sector={bytes_per_sector}")
    expected_len = EXFAT_CHECKSUM_INPUT_SECTORS * bytes_per_sector
    if len(sectors_0_to_10) != expected_len:
        raise ValueError(
            f"Expected {expected_len} bytes (11 sectors x {bytes_per_sector}B), got {len(sectors_0_to_10)}"
        )

    checksum = 0
    for idx, byte_val in enumerate(sectors_0_to_10):
        if idx in EXFAT_BOOT_CHECKSUM_SKIP_OFFSETS:
            continue
        checksum = (((0x80000000 if (checksum & 1) else 0) + (checksum >> 1) + byte_val) & 0xFFFFFFFF)
    return checksum


def build_synthetic_exfat_boot_region(
    *,
    bytes_per_sector_shift: int = 9,
    sectors_per_cluster_shift: int = 6,
    partition_offset: int = 2048,
    volume_length: int = 131072,
    fat_offset: int = 24,
    fat_length: int = 16,
    cluster_heap_offset: int = 40,
    cluster_count: int = 2040,
    first_cluster_of_root_directory: int = 2,
    volume_serial: int = 0x46583336,
    file_system_revision: int = 0x0100,
    volume_flags: int = 0x0000,
    number_of_fats: int = 1,
    drive_select: int = 0x80,
    percent_in_use: int = 0,
    include_backup_region: bool = True,
    extended_boot_signatures: bool = True,
    backup_volume_flags: Optional[int] = None,
) -> bytes:
    """Build a spec-compliant 12-sector or 24-sector exFAT Boot Region for tests/clean-room."""
    if not (EXFAT_MIN_SECTOR_SHIFT <= bytes_per_sector_shift <= EXFAT_MAX_SECTOR_SHIFT):
        raise ValueError(f"Invalid bytes_per_sector_shift={bytes_per_sector_shift}")
    if not (0 <= sectors_per_cluster_shift <= EXFAT_MAX_CLUSTER_SIZE_SHIFT - bytes_per_sector_shift):
        raise ValueError(f"Invalid sectors_per_cluster_shift={sectors_per_cluster_shift}")
    if number_of_fats not in (1, 2):
        raise ValueError(f"Invalid number_of_fats={number_of_fats}")

    bps = 1 << bytes_per_sector_shift

    def _build_12_sectors(vflags: int) -> bytes:
        region = bytearray(EXFAT_BOOT_REGION_SECTORS * bps)
        # Sector 0: Main/Backup VBR
        region[0:3] = b"\xeb\x76\x90"
        region[3:11] = EXFAT_FS_NAME
        # MustBeZero [11:64] already zero
        struct.pack_into("<QQ", region, 64, partition_offset, volume_length)
        struct.pack_into("<IIII", region, 80, fat_offset, fat_length, cluster_heap_offset, cluster_count)
        struct.pack_into("<II", region, 96, first_cluster_of_root_directory, volume_serial)
        struct.pack_into("<HH", region, 104, file_system_revision, vflags)
        region[108] = bytes_per_sector_shift
        region[109] = sectors_per_cluster_shift
        region[110] = number_of_fats
        region[111] = drive_select
        region[112] = percent_in_use
        struct.pack_into("<H", region, 510, EXFAT_BOOT_SIGNATURE)

        # Sectors 1..8: Extended Boot Sectors
        if extended_boot_signatures:
            for sec_idx in range(1, 9):
                struct.pack_into("<I", region, (sec_idx + 1) * bps - 4, EXFAT_EXTENDED_BOOT_SIGNATURE)

        # Sectors 9..10: OEM Parameters + Reserved (zeroed)
        # Sector 11: Boot Checksum repeated bps // 4 times
        chk = compute_exfat_boot_checksum(bytes(region[: 11 * bps]), bytes_per_sector=bps)
        chk_word = struct.pack("<I", chk)
        sector11_off = 11 * bps
        region[sector11_off : sector11_off + bps] = chk_word * (bps // 4)
        return bytes(region)

    main_12 = _build_12_sectors(volume_flags)
    if not include_backup_region:
        return main_12
    b_flags = volume_flags if backup_volume_flags is None else backup_volume_flags
    backup_12 = _build_12_sectors(b_flags)
    return main_12 + backup_12


def parse_exfat_vbr(vbr_bytes: bytes) -> ExfatVbrParseResult:
    """Parse and validate a single exFAT Boot Sector (Main VBR Sector 0 or Backup VBR Sector 12)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if len(vbr_bytes) < 512:
        _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
        errors.append(f"exFAT VBR requires at least 512 bytes, got {len(vbr_bytes)}")
        return ExfatVbrParseResult(
            valid=False,
            status=STATUS_BLOCKED_EXFAT_VBR_INVALID,
            violation_codes=tuple(codes),
            file_system_name_hex=vbr_bytes[3:11].hex() if len(vbr_bytes) >= 11 else "",
            file_system_name_ok=False,
            must_be_zero_ok=False,
            bytes_per_sector_shift=0,
            sectors_per_cluster_shift=0,
            bytes_per_sector=0,
            sectors_per_cluster=0,
            bytes_per_cluster=0,
            sector_shift_power_of_two_ok=False,
            cluster_shift_power_of_two_ok=False,
            partition_offset=0,
            volume_length=0,
            fat_offset=0,
            fat_length=0,
            cluster_heap_offset=0,
            cluster_count=0,
            first_cluster_of_root_directory=0,
            volume_serial_hex="00000000",
            file_system_revision_hex="0000",
            volume_flags=0,
            active_fat=0,
            volume_dirty=False,
            media_failure=False,
            clear_to_zero=False,
            number_of_fats=0,
            drive_select=0,
            percent_in_use=0,
            boot_signature_hex="0000",
            boot_signature_ok=False,
            geometry_ok=False,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    fs_name_raw = vbr_bytes[3:11]
    fs_name_hex = fs_name_raw.hex()
    fs_name_ok = fs_name_raw == EXFAT_FS_NAME
    if not fs_name_ok:
        _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
        errors.append(
            f"Invalid exFAT FileSystemName at offset 3..11: hex={fs_name_hex} (expected {EXFAT_FS_NAME_HEX} 'EXFAT   ')"
        )

    must_be_zero_raw = vbr_bytes[EXFAT_MUST_BE_ZERO_OFFSET : EXFAT_MUST_BE_ZERO_OFFSET + EXFAT_MUST_BE_ZERO_LEN]
    must_be_zero_ok = all(b == 0 for b in must_be_zero_raw)
    if not must_be_zero_ok:
        _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
        errors.append("exFAT MustBeZero region (bytes 11..63) contains non-zero bytes")

    partition_offset, volume_length = struct.unpack_from("<QQ", vbr_bytes, 64)
    fat_offset, fat_length, cluster_heap_offset, cluster_count = struct.unpack_from("<IIII", vbr_bytes, 80)
    first_cluster_root, volume_serial = struct.unpack_from("<II", vbr_bytes, 96)
    fs_revision, volume_flags = struct.unpack_from("<HH", vbr_bytes, 104)
    bps_shift = vbr_bytes[108]
    spc_shift = vbr_bytes[109]
    num_fats = vbr_bytes[110]
    drive_select = vbr_bytes[111]
    percent_in_use = vbr_bytes[112]
    boot_sig = struct.unpack_from("<H", vbr_bytes, 510)[0]

    boot_sig_ok = boot_sig == EXFAT_BOOT_SIGNATURE
    if not boot_sig_ok:
        _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
        errors.append(f"Invalid exFAT BootSignature at 0x1FE: {hex(boot_sig)} (expected 0xaa55)")

    sector_shift_ok = EXFAT_MIN_SECTOR_SHIFT <= bps_shift <= EXFAT_MAX_SECTOR_SHIFT
    if sector_shift_ok:
        bps = 1 << bps_shift
        sector_pow2_ok = _is_power_of_two(bps)
    else:
        bps = 0
        sector_pow2_ok = False
        _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
        errors.append(
            f"Invalid BytesPerSectorShift={bps_shift} (must be in {EXFAT_MIN_SECTOR_SHIFT}..{EXFAT_MAX_SECTOR_SHIFT})"
        )

    if sector_shift_ok and (0 <= spc_shift <= (EXFAT_MAX_CLUSTER_SIZE_SHIFT - bps_shift)):
        spc = 1 << spc_shift
        bpc = bps * spc
        cluster_pow2_ok = _is_power_of_two(spc) and _is_power_of_two(bpc)
    else:
        spc = 0
        bpc = 0
        cluster_pow2_ok = False
        _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
        errors.append(
            f"Invalid SectorsPerClusterShift={spc_shift} for BytesPerSectorShift={bps_shift} "
            f"(cluster size must not exceed 32 MiB)"
        )

    if sector_pow2_ok and len(vbr_bytes) > 512:
        if len(vbr_bytes) < bps:
            _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
            errors.append(f"VBR length {len(vbr_bytes)} < BytesPerSector {bps}")
        elif bps > 512 and any(b != 0 for b in vbr_bytes[512:bps]):
            _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
            errors.append("exFAT VBR ExcessSpace (bytes 512..BytesPerSector-1) must be zero")

    # Revision & FAT count
    rev_major = (fs_revision >> 8) & 0xFF
    if rev_major != 1:
        _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
        errors.append(f"Unsupported exFAT FileSystemRevision={hex(fs_revision)} (expected major=1)")

    if num_fats not in (1, 2):
        _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
        errors.append(f"Invalid exFAT NumberOfFats={num_fats} (must be 1 or 2)")

    active_fat = volume_flags & EXFAT_FLAG_ACTIVE_FAT
    volume_dirty = bool(volume_flags & EXFAT_FLAG_VOLUME_DIRTY)
    media_failure = bool(volume_flags & EXFAT_FLAG_MEDIA_FAILURE)
    clear_to_zero = bool(volume_flags & EXFAT_FLAG_CLEAR_TO_ZERO)

    if active_fat == 1 and num_fats < 2:
        _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
        errors.append("VolumeFlags.ActiveFat=1 requires NumberOfFats=2")

    if percent_in_use > 100 and percent_in_use != 0xFF:
        warnings.append(f"Reserved PercentInUse value {percent_in_use} (spec expects 0..100 or 0xFF)")

    # Geometry checks
    geometry_ok = True
    if fat_offset < EXFAT_FULL_BOOT_AREA_SECTORS:
        geometry_ok = False
        errors.append(f"FatOffset={fat_offset} overlaps Boot Area (< 24 sectors)")
    if fat_length < 1:
        geometry_ok = False
        errors.append(f"FatLength={fat_length} must be >= 1")
    if num_fats in (1, 2) and cluster_heap_offset < (fat_offset + fat_length * num_fats):
        geometry_ok = False
        errors.append(
            f"ClusterHeapOffset={cluster_heap_offset} overlaps FAT region "
            f"(fat_offset + fat_length*num_fats = {fat_offset + fat_length * num_fats})"
        )
    if cluster_count < 1:
        geometry_ok = False
        errors.append(f"ClusterCount={cluster_count} must be >= 1")
    if spc > 0 and volume_length < (cluster_heap_offset + cluster_count * spc):
        geometry_ok = False
        errors.append(
            f"VolumeLength={volume_length} < required {cluster_heap_offset + cluster_count * spc} sectors"
        )
    if not (2 <= first_cluster_root < cluster_count + 2):
        geometry_ok = False
        errors.append(
            f"FirstClusterOfRootDirectory={first_cluster_root} outside valid range [2, {cluster_count + 2})"
        )
    if not geometry_ok:
        _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)

    if volume_dirty:
        _add_code(codes, STATUS_BLOCKED_EXFAT_VOLUME_DIRTY)
        errors.append("exFAT VolumeDirty flag (VolumeFlags & 0x0002 at offset 0x6A) is set")
    if media_failure:
        _add_code(codes, STATUS_BLOCKED_EXFAT_MEDIA_FAILURE)
        errors.append("exFAT MediaFailure flag (VolumeFlags & 0x0004 at offset 0x6A) is set")

    valid = len(errors) == 0
    status = STATUS_VERIFIED_SAFE if valid else codes[0]

    return ExfatVbrParseResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        file_system_name_hex=fs_name_hex,
        file_system_name_ok=fs_name_ok,
        must_be_zero_ok=must_be_zero_ok,
        bytes_per_sector_shift=bps_shift,
        sectors_per_cluster_shift=spc_shift,
        bytes_per_sector=bps,
        sectors_per_cluster=spc,
        bytes_per_cluster=bpc,
        sector_shift_power_of_two_ok=sector_pow2_ok,
        cluster_shift_power_of_two_ok=cluster_pow2_ok,
        partition_offset=partition_offset,
        volume_length=volume_length,
        fat_offset=fat_offset,
        fat_length=fat_length,
        cluster_heap_offset=cluster_heap_offset,
        cluster_count=cluster_count,
        first_cluster_of_root_directory=first_cluster_root,
        volume_serial_hex=f"{volume_serial:08x}",
        file_system_revision_hex=f"{fs_revision:04x}",
        volume_flags=volume_flags,
        active_fat=active_fat,
        volume_dirty=volume_dirty,
        media_failure=media_failure,
        clear_to_zero=clear_to_zero,
        number_of_fats=num_fats,
        drive_select=drive_select,
        percent_in_use=percent_in_use,
        boot_signature_hex=f"{boot_sig:04x}",
        boot_signature_ok=boot_sig_ok,
        geometry_ok=geometry_ok,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _verify_12_sector_region_checksum(
    region_bytes: bytes,
    bps: int,
    label: str,
) -> Tuple[int, int, bool, bool, bool, List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    computed = compute_exfat_boot_checksum(
        region_bytes[: EXFAT_CHECKSUM_INPUT_SECTORS * bps],
        bytes_per_sector=bps,
    )
    chk_sec_off = EXFAT_CHECKSUM_INPUT_SECTORS * bps
    chk_sec = region_bytes[chk_sec_off : chk_sec_off + bps]
    words = struct.unpack(f"<{bps // 4}I", chk_sec)
    expected = words[0]
    uniform = all(w == expected for w in words)
    checksum_ok = uniform and (computed == expected)

    if not uniform:
        errors.append(
            f"{label} BootChecksum sector (sector 11) is not uniform across all {bps // 4} 32-bit slots"
        )
    if computed != expected:
        errors.append(
            f"{label} BootChecksum mismatch: computed={computed:08x} stored={expected:08x}"
        )

    ext_sigs_ok = True
    for sec_idx in range(1, 9):
        sig = struct.unpack_from("<I", region_bytes, (sec_idx + 1) * bps - 4)[0]
        if sig != EXFAT_EXTENDED_BOOT_SIGNATURE:
            ext_sigs_ok = False
            break
    if not ext_sigs_ok:
        warnings.append(
            f"{label} Extended Boot Sectors 1..8 lack 0xAA550000 signature in one or more sectors"
        )

    return computed, expected, checksum_ok, uniform, ext_sigs_ok, errors, warnings


def verify_exfat_boot_region(
    boot_bytes: bytes,
    *,
    require_backup_region: bool = True,
    require_extended_boot_signatures: bool = False,
    allow_volume_dirty: bool = False,
) -> ExfatBootRegionAuditResult:
    """Verify exFAT Main (Sectors 0..11) and Backup (Sectors 12..23) Boot Regions & 12-sector BootChecksums."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    main_vbr = parse_exfat_vbr(boot_bytes[:512] if len(boot_bytes) >= 512 else boot_bytes)
    bps = main_vbr.bytes_per_sector

    if bps not in (512, 1024, 2048, 4096):
        _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
        errors.extend(main_vbr.errors)
        return ExfatBootRegionAuditResult(
            valid=False,
            status=codes[0],
            violation_codes=tuple(codes),
            bytes_per_sector=0,
            bytes_per_cluster=0,
            main_vbr=main_vbr.to_dict(),
            backup_vbr=None,
            computed_main_checksum_hex="",
            expected_main_checksum_hex="",
            main_checksum_ok=False,
            main_checksum_sector_uniform=False,
            main_extended_signatures_ok=False,
            backup_region_present=False,
            computed_backup_checksum_hex=None,
            expected_backup_checksum_hex=None,
            backup_checksum_ok=None,
            backup_checksum_sector_uniform=None,
            backup_extended_signatures_ok=None,
            main_vs_backup_consistent=None,
            volume_dirty=main_vbr.volume_dirty,
            media_failure=main_vbr.media_failure,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    # Re-parse full sector 0 if bps > 512 so ExcessSpace is checked too
    if bps > 512 and len(boot_bytes) >= bps:
        main_vbr = parse_exfat_vbr(boot_bytes[:bps])

    for err in main_vbr.errors:
        # Filter dirty/failure if caller explicitly checks structure only, else propagate
        if allow_volume_dirty and "VolumeDirty" in err:
            continue
        errors.append(err)
    for code in main_vbr.violation_codes:
        if allow_volume_dirty and code == STATUS_BLOCKED_EXFAT_VOLUME_DIRTY:
            continue
        _add_code(codes, code)
    warnings.extend(main_vbr.warnings)

    main_region_bytes = EXFAT_BOOT_REGION_SECTORS * bps
    if len(boot_bytes) < main_region_bytes:
        _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
        errors.append(
            f"exFAT Main Boot Region requires {main_region_bytes} bytes (12 sectors x {bps}B), got {len(boot_bytes)}"
        )
        return ExfatBootRegionAuditResult(
            valid=False,
            status=codes[0],
            violation_codes=tuple(codes),
            bytes_per_sector=bps,
            bytes_per_cluster=main_vbr.bytes_per_cluster,
            main_vbr=main_vbr.to_dict(),
            backup_vbr=None,
            computed_main_checksum_hex="",
            expected_main_checksum_hex="",
            main_checksum_ok=False,
            main_checksum_sector_uniform=False,
            main_extended_signatures_ok=False,
            backup_region_present=False,
            computed_backup_checksum_hex=None,
            expected_backup_checksum_hex=None,
            backup_checksum_ok=None,
            backup_checksum_sector_uniform=None,
            backup_extended_signatures_ok=None,
            main_vs_backup_consistent=None,
            volume_dirty=main_vbr.volume_dirty,
            media_failure=main_vbr.media_failure,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    main_slice = boot_bytes[:main_region_bytes]
    (
        comp_main,
        exp_main,
        main_chk_ok,
        main_uni,
        main_ext_ok,
        main_chk_errs,
        main_chk_warns,
    ) = _verify_12_sector_region_checksum(main_slice, bps, "Main Boot Region")
    if not main_chk_ok:
        _add_code(codes, STATUS_BLOCKED_EXFAT_BOOT_CHECKSUM)
        errors.extend(main_chk_errs)
    warnings.extend(main_chk_warns)
    if require_extended_boot_signatures and not main_ext_ok:
        _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
        errors.append("Main Extended Boot Sectors missing 0xAA550000 signatures")

    # Backup Boot Region (Sectors 12..23)
    full_24_bytes = EXFAT_FULL_BOOT_AREA_SECTORS * bps
    backup_present = len(boot_bytes) >= full_24_bytes
    backup_vbr_dict: Optional[Dict[str, Any]] = None
    comp_bkp_hex: Optional[str] = None
    exp_bkp_hex: Optional[str] = None
    bkp_chk_ok: Optional[bool] = None
    bkp_uni: Optional[bool] = None
    bkp_ext_ok: Optional[bool] = None
    main_vs_backup_ok: Optional[bool] = None

    any_dirty = main_vbr.volume_dirty
    any_media_failure = main_vbr.media_failure

    if backup_present:
        backup_slice = boot_bytes[main_region_bytes:full_24_bytes]
        backup_vbr = parse_exfat_vbr(backup_slice[:bps])
        backup_vbr_dict = backup_vbr.to_dict()
        if backup_vbr.volume_dirty:
            any_dirty = True
        if backup_vbr.media_failure:
            any_media_failure = True

        for err in backup_vbr.errors:
            if allow_volume_dirty and "VolumeDirty" in err:
                continue
            errors.append(f"Backup VBR: {err}")
        for code in backup_vbr.violation_codes:
            if allow_volume_dirty and code == STATUS_BLOCKED_EXFAT_VOLUME_DIRTY:
                continue
            _add_code(codes, code)

        (
            comp_bkp,
            exp_bkp,
            bkp_chk_ok_val,
            bkp_uni_val,
            bkp_ext_ok_val,
            bkp_chk_errs,
            bkp_chk_warns,
        ) = _verify_12_sector_region_checksum(backup_slice, bps, "Backup Boot Region")
        comp_bkp_hex = f"{comp_bkp:08x}"
        exp_bkp_hex = f"{exp_bkp:08x}"
        bkp_chk_ok = bkp_chk_ok_val
        bkp_uni = bkp_uni_val
        bkp_ext_ok = bkp_ext_ok_val
        if not bkp_chk_ok_val:
            _add_code(codes, STATUS_BLOCKED_EXFAT_BOOT_CHECKSUM)
            errors.extend(bkp_chk_errs)
        warnings.extend(bkp_chk_warns)
        if require_extended_boot_signatures and not bkp_ext_ok_val:
            _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
            errors.append("Backup Extended Boot Sectors missing 0xAA550000 signatures")

        # Compare Sectors 0..10 vs Sectors 12..22 excluding volatile VolumeFlags (106..107) and PercentInUse (112)
        m_cmp = bytearray(main_slice[: EXFAT_CHECKSUM_INPUT_SECTORS * bps])
        b_cmp = bytearray(backup_slice[: EXFAT_CHECKSUM_INPUT_SECTORS * bps])
        for skip_off in EXFAT_BOOT_CHECKSUM_SKIP_OFFSETS:
            m_cmp[skip_off] = 0
            b_cmp[skip_off] = 0
        main_vs_backup_ok = m_cmp == b_cmp
        if not main_vs_backup_ok:
            _add_code(codes, STATUS_BLOCKED_EXFAT_BACKUP_MISMATCH)
            errors.append(
                "exFAT Main Boot Region (Sectors 0..10) diverges from Backup Boot Region (Sectors 12..22) "
                "outside volatile VolumeFlags/PercentInUse offsets"
            )
    elif require_backup_region:
        _add_code(codes, STATUS_BLOCKED_EXFAT_BACKUP_MISMATCH)
        errors.append(
            f"exFAT Backup Boot Region (Sectors 12..23, {full_24_bytes} B total) is missing (got {len(boot_bytes)} B)"
        )

    valid = len(errors) == 0
    status = STATUS_VERIFIED_SAFE if valid else codes[0]

    return ExfatBootRegionAuditResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        bytes_per_sector=bps,
        bytes_per_cluster=main_vbr.bytes_per_cluster,
        main_vbr=main_vbr.to_dict(),
        backup_vbr=backup_vbr_dict,
        computed_main_checksum_hex=f"{comp_main:08x}",
        expected_main_checksum_hex=f"{exp_main:08x}",
        main_checksum_ok=main_chk_ok,
        main_checksum_sector_uniform=main_uni,
        main_extended_signatures_ok=main_ext_ok,
        backup_region_present=backup_present,
        computed_backup_checksum_hex=comp_bkp_hex,
        expected_backup_checksum_hex=exp_bkp_hex,
        backup_checksum_ok=bkp_chk_ok,
        backup_checksum_sector_uniform=bkp_uni,
        backup_extended_signatures_ok=bkp_ext_ok,
        main_vs_backup_consistent=main_vs_backup_ok,
        volume_dirty=any_dirty,
        media_failure=any_media_failure,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_exfat_image_file(
    image_path: Path,
    *,
    require_backup_region: bool = True,
    require_extended_boot_signatures: bool = False,
    allow_volume_dirty: bool = False,
) -> ExfatBootRegionAuditResult:
    """Read up to 24 sectors strictly via `os.O_RDONLY` and verify exFAT Boot Regions."""
    header_probe = read_slice_o_rdonly(image_path, 0, 512)
    vbr = parse_exfat_vbr(header_probe)
    bps = vbr.bytes_per_sector if vbr.bytes_per_sector in (512, 1024, 2048, 4096) else 512
    need = EXFAT_FULL_BOOT_AREA_SECTORS * bps
    boot_bytes = read_slice_o_rdonly(image_path, 0, need)
    return verify_exfat_boot_region(
        boot_bytes,
        require_backup_region=require_backup_region,
        require_extended_boot_signatures=require_extended_boot_signatures,
        allow_volume_dirty=allow_volume_dirty,
    )


# ---------------------------------------------------------------------------
# 2. Sony Camera Media Tree (`XDROOT` vs `M4ROOT` + `.RSV`) & Dual-Slot Firewall
# ---------------------------------------------------------------------------


def _normalize_card_entries(
    *,
    card_root: Optional[Path] = None,
    entries: Optional[Sequence[Union[str, Tuple[str, int], Mapping[str, Any]]]] = None,
) -> List[Tuple[str, int]]:
    normalized: List[Tuple[str, int]] = []
    if card_root is not None:
        root_path = Path(card_root)
        if not root_path.is_dir():
            raise FileNotFoundError(f"Card root directory does not exist: {root_path}")
        stack: List[Path] = [root_path]
        while stack:
            cur = stack.pop()
            with os.scandir(cur) as it:
                for de in sorted(it, key=lambda d: d.name):
                    if de.is_dir(follow_symlinks=False):
                        stack.append(Path(de.path))
                    elif de.is_file(follow_symlinks=False):
                        rel = Path(de.path).relative_to(root_path).as_posix()
                        st = de.stat(follow_symlinks=False)
                        normalized.append((rel, int(st.st_size)))

    if entries is not None:
        for item in entries:
            if isinstance(item, str):
                rel = PurePosixPath(item.replace("\\", "/").lstrip("/")).as_posix()
                normalized.append((rel, 1))
            elif isinstance(item, tuple) and len(item) == 2:
                rel = PurePosixPath(str(item[0]).replace("\\", "/").lstrip("/")).as_posix()
                normalized.append((rel, int(item[1])))
            elif isinstance(item, Mapping):
                raw_p = str(item.get("path", "")).replace("\\", "/").lstrip("/")
                rel = PurePosixPath(raw_p).as_posix()
                size_v = int(item.get("size", item.get("bytes", 0)))
                normalized.append((rel, size_v))
            else:
                raise TypeError(f"Unsupported card entry format: {type(item).__name__}")

    return sorted(normalized, key=lambda x: x[0])


def inspect_sony_media_tree(
    *,
    card_root: Optional[Path] = None,
    entries: Optional[Sequence[Union[str, Tuple[str, int], Mapping[str, Any]]]] = None,
) -> SonyMediaTreeInspection:
    """Scan a Sony CFexpress Type A / SDXC media tree for FX6 XDROOT, FX3 M4ROOT, and .RSV salvage clips."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    try:
        items = _normalize_card_entries(card_root=card_root, entries=entries)
    except FileNotFoundError as exc:
        _add_code(codes, STATUS_BLOCKED_NO_LAB_MEDIA_CARD)
        errors.append(str(exc))
        return SonyMediaTreeInspection(
            valid=False,
            status=STATUS_BLOCKED_NO_LAB_MEDIA_CARD,
            violation_codes=tuple(codes),
            detected_trees=(),
            total_files_scanned=0,
            fx6_xdroot_mxf_clips=(),
            fx3_m4root_mp4_clips=(),
            other_production_media=(),
            unfinalized_rsv_files=(),
            chkdsk_chk_files=(),
            zero_byte_clip_stubs=(),
            c2pa_card_credentials=(),
            sony_metadata_files=(),
            total_production_bytes=0,
            is_clean_lab_media=False,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    detected_trees: List[str] = []
    fx6_clips: List[str] = []
    fx3_clips: List[str] = []
    other_media: List[str] = []
    rsv_files: List[str] = []
    chk_files: List[str] = []
    zero_stubs: List[str] = []
    c2pa_creds: List[str] = []
    metadata_files: List[str] = []
    total_prod_bytes = 0

    def _add_tree(tag: str) -> None:
        if tag not in detected_trees:
            detected_trees.append(tag)

    for rel_path, size_bytes in items:
        if not rel_path or rel_path == ".":
            continue
        low = rel_path.lower()
        parts = [p for p in low.split("/") if p]
        fname = parts[-1] if parts else ""
        ext = PurePosixPath(fname).suffix.lower()

        if parts and parts[0] == "xdroot":
            _add_tree("FX6_XDROOT")
        if (len(parts) >= 2 and parts[0] == "private" and parts[1] == "m4root"):
            _add_tree("FX3_PRIVATE_M4ROOT")
        elif parts and parts[0] == "m4root":
            _add_tree("FX3_M4ROOT")
        if parts and parts[0] == "dcim":
            _add_tree("SONY_DCIM")

        # 1. Unfinalized .RSV power-loss recovery clips (ANY size >= 0 blocks!)
        if ext == ".rsv":
            rsv_files.append(rel_path)
            if size_bytes > 0:
                total_prod_bytes += size_bytes
            continue

        # 2. Destructive chkdsk /f remnants (FOUND.000/*.CHK)
        if parts and re.match(r"^found\.\d+$", parts[0]) and ext == ".chk":
            chk_files.append(rel_path)
            if size_bytes > 0:
                total_prod_bytes += size_bytes
            continue

        # 3. FX6 XDROOT clips (XDROOT/Clip/*.MXF, XDROOT/Sub/*.MXF, XDROOT/Clip/*.MP4)
        is_xdroot_clip_dir = (
            len(parts) >= 3 and parts[0] == "xdroot" and parts[1] in ("clip", "sub")
        )
        if is_xdroot_clip_dir and ext in PRODUCTION_CLIP_EXTENSIONS:
            if size_bytes > 0:
                fx6_clips.append(rel_path)
                total_prod_bytes += size_bytes
            else:
                zero_stubs.append(rel_path)
            continue

        # 4. FX3 PRIVATE/M4ROOT/CLIP/*.MP4 or M4ROOT/CLIP/*.MP4 (and SUB)
        is_private_m4root_clip = (
            len(parts) >= 4
            and parts[0] == "private"
            and parts[1] == "m4root"
            and parts[2] in ("clip", "sub")
        )
        is_cfex_m4root_clip = (
            len(parts) >= 3
            and parts[0] == "m4root"
            and parts[1] in ("clip", "sub")
        )
        if (is_private_m4root_clip or is_cfex_m4root_clip) and ext in PRODUCTION_CLIP_EXTENSIONS:
            if size_bytes > 0:
                fx3_clips.append(rel_path)
                total_prod_bytes += size_bytes
            else:
                zero_stubs.append(rel_path)
            continue

        # 5. Any other non-empty video/RAW/still production media under DCIM/XDROOT/M4ROOT
        if (
            (parts and parts[0] in ("dcim", "xdroot", "m4root"))
            or (len(parts) >= 2 and parts[0] == "private" and parts[1] == "m4root")
        ):
            if ext in PRODUCTION_CLIP_EXTENSIONS + PRODUCTION_STILL_EXTENSIONS:
                if size_bytes > 0:
                    other_media.append(rel_path)
                    total_prod_bytes += size_bytes
                else:
                    zero_stubs.append(rel_path)
                continue
            if ext in (".xml", ".bim", ".smi", ".ppn", ".cube"):
                metadata_files.append(rel_path)

        # 6. Sony C2PA card root credentials (warning)
        if fname in ("rq_lic.dat", "sigcert.p12", "sigcert.pfx"):
            c2pa_creds.append(rel_path)

    if zero_stubs:
        warnings.append(
            f"Detected {len(zero_stubs)} zero-byte clip stub(s) ({', '.join(zero_stubs[:3])}); check card for aborted writes."
        )
    if c2pa_creds:
        warnings.append(
            f"Detected Sony C2PA provisioning file(s) on card ({', '.join(c2pa_creds)}); archive before lab use."
        )

    if rsv_files:
        _add_code(codes, STATUS_BLOCKED_UNFINALIZED_RSV_PRESENT)
        errors.append(
            f"Unfinalized Sony .RSV power-loss recovery clip(s) detected ({', '.join(rsv_files[:4])}); "
            "capture read-only clone before any Stage-A/B or H0/H1 session."
        )
    if fx6_clips or fx3_clips or other_media:
        _add_code(codes, STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT)
        sample = (fx6_clips + fx3_clips + other_media)[:4]
        errors.append(
            f"Live client production footage detected on media card ({', '.join(sample)}, "
            f"{total_prod_bytes} bytes); dedicated blank/lab rehearsal media required."
        )
    if chk_files:
        _add_code(codes, STATUS_BLOCKED_CHKDSK_FOUND_CHK_PRESENT)
        errors.append(
            f"Destructive chkdsk /f remnants detected ({', '.join(chk_files[:4])}); card is corrupted/unclean."
        )

    is_clean = len(errors) == 0
    status = STATUS_VERIFIED_SAFE if is_clean else codes[0]

    return SonyMediaTreeInspection(
        valid=is_clean,
        status=status,
        violation_codes=tuple(codes),
        detected_trees=tuple(detected_trees),
        total_files_scanned=len(items),
        fx6_xdroot_mxf_clips=tuple(fx6_clips),
        fx3_m4root_mp4_clips=tuple(fx3_clips),
        other_production_media=tuple(other_media),
        unfinalized_rsv_files=tuple(rsv_files),
        chkdsk_chk_files=tuple(chk_files),
        zero_byte_clip_stubs=tuple(zero_stubs),
        c2pa_card_credentials=tuple(c2pa_creds),
        sony_metadata_files=tuple(metadata_files),
        total_production_bytes=total_prod_bytes,
        is_clean_lab_media=is_clean,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _audit_single_slot(slot: MediaSlotConfig) -> MediaSlotAuditResult:
    slot_id = slot.slot_id.strip().upper()
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not slot.inserted:
        return MediaSlotAuditResult(
            slot_id=slot_id,
            inserted=False,
            media_type=slot.media_type,
            device_node=slot.device_node,
            mount_point=slot.mount_point,
            dedicated_lab_card=False,
            passed=True,
            status=STATUS_VERIFIED_SAFE,
            violation_codes=(),
            exfat_audit=None,
            media_tree_audit=None,
            errors=(),
            warnings=(),
        )

    if not slot.dedicated_lab_card:
        _add_code(codes, STATUS_BLOCKED_NO_LAB_MEDIA_CARD)
        errors.append(
            f"{slot_id}: Inserted card is not confirmed as a dedicated blank/lab rehearsal card."
        )

    exfat_dict: Optional[Dict[str, Any]] = None
    if slot.exfat_boot_bytes is not None:
        exfat_res = verify_exfat_boot_region(
            slot.exfat_boot_bytes,
            require_backup_region=slot.require_backup_region,
        )
        exfat_dict = exfat_res.to_dict()
        if not exfat_res.valid:
            for c in exfat_res.violation_codes:
                _add_code(codes, c)
            errors.extend(f"{slot_id}: {e}" for e in exfat_res.errors)
        warnings.extend(f"{slot_id}: {w}" for w in exfat_res.warnings)
    elif slot.exfat_image_path is not None:
        exfat_res = verify_exfat_image_file(
            slot.exfat_image_path,
            require_backup_region=slot.require_backup_region,
        )
        exfat_dict = exfat_res.to_dict()
        if not exfat_res.valid:
            for c in exfat_res.violation_codes:
                _add_code(codes, c)
            errors.extend(f"{slot_id}: {e}" for e in exfat_res.errors)
        warnings.extend(f"{slot_id}: {w}" for w in exfat_res.warnings)
    else:
        _add_code(codes, STATUS_BLOCKED_EXFAT_VBR_INVALID)
        errors.append(
            f"{slot_id}: Inserted card missing exFAT VBR / 12-sector BootChecksum evidence."
        )

    tree_res = inspect_sony_media_tree(
        card_root=slot.card_root,
        entries=slot.card_entries if slot.card_entries is not None else (),
    )
    tree_dict = tree_res.to_dict()
    if not tree_res.valid:
        for c in tree_res.violation_codes:
            _add_code(codes, c)
        errors.extend(f"{slot_id}: {e}" for e in tree_res.errors)
    warnings.extend(f"{slot_id}: {w}" for w in tree_res.warnings)

    passed = len(errors) == 0
    status = STATUS_VERIFIED_SAFE if passed else codes[0]
    return MediaSlotAuditResult(
        slot_id=slot_id,
        inserted=True,
        media_type=slot.media_type,
        device_node=slot.device_node,
        mount_point=slot.mount_point,
        dedicated_lab_card=slot.dedicated_lab_card,
        passed=passed,
        status=status,
        violation_codes=tuple(codes),
        exfat_audit=exfat_dict,
        media_tree_audit=tree_dict,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_dual_slot_media_firewall(
    *,
    slot_a: Optional[MediaSlotConfig] = None,
    slot_b: Optional[MediaSlotConfig] = None,
    require_at_least_one_lab_card: bool = True,
) -> DualSlotMediaFirewallResult:
    """Verify both Slot A and Slot B CFexpress/SDXC cards; block H0/H1 if production media or dirty exFAT."""
    eff_a = slot_a if slot_a is not None else MediaSlotConfig(
        slot_id=SLOT_A,
        inserted=True,
        media_type=MEDIA_TYPE_CFEXPRESS_A,
        device_node="/dev/mmcblk1p1",
        mount_point="/mnt/slot_a",
        exfat_boot_bytes=build_synthetic_exfat_boot_region(),
        card_entries=(),
        dedicated_lab_card=True,
    )
    eff_b = slot_b if slot_b is not None else MediaSlotConfig(
        slot_id=SLOT_B,
        inserted=False,
        media_type=MEDIA_TYPE_SDXC,
        device_node="/dev/mmcblk2p1",
        mount_point="/mnt/slot_b",
        dedicated_lab_card=False,
    )

    res_a = _audit_single_slot(eff_a)
    res_b = _audit_single_slot(eff_b)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    for r in (res_a, res_b):
        for c in r.violation_codes:
            _add_code(codes, c)
        errors.extend(r.errors)
        warnings.extend(r.warnings)

    inserted_lab_slots: List[str] = []
    for r in (res_a, res_b):
        if r.inserted and r.passed and r.dedicated_lab_card:
            inserted_lab_slots.append(r.slot_id)

    if require_at_least_one_lab_card and not inserted_lab_slots:
        _add_code(codes, STATUS_BLOCKED_NO_LAB_MEDIA_CARD)
        if not errors:
            errors.append(
                "H0/H1 trial entry requires at least one verified blank/dedicated lab exFAT card in Slot A or Slot B."
            )

    valid = res_a.passed and res_b.passed and len(errors) == 0
    status = STATUS_VERIFIED_SAFE if valid else codes[0]
    return DualSlotMediaFirewallResult(
        valid=valid,
        status=status,
        h0_h1_trial_entry_allowed=valid,
        violation_codes=tuple(codes),
        inserted_lab_slots=tuple(inserted_lab_slots),
        slot_a_result=res_a.to_dict(),
        slot_b_result=res_b.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 3. Internal `p1` (`FAT12`/`FAT16`) vs External `exFAT` Filesystem Separation
# ---------------------------------------------------------------------------


def build_synthetic_p1_fat12_vbr(*, fat_type: str = "FAT12") -> bytes:
    """Build a valid 512-byte synthetic `p1` FAT12/FAT16 failsafe VBR for clean-room audits."""
    norm = fat_type.strip().upper()
    if norm not in VALID_P1_FAT_TYPES:
        raise ValueError(f"p1 fat_type must be 'FAT12' or 'FAT16', got {fat_type!r}")
    vbr = bytearray(512)
    vbr[0:3] = b"\xeb\x3c\x90"
    vbr[3:11] = b"mkfs.fat"
    bps = 512
    spc = 32 if norm == "FAT12" else 1
    rsvd = 1
    num_fats = 2
    root_ent = 512
    fat_sectors = 32 if norm == "FAT12" else 17
    tot_sectors = 37846 if norm == "FAT12" else (1 + 2 * 17 + 32 + 4100)
    struct.pack_into("<H", vbr, 11, bps)
    vbr[13] = spc
    struct.pack_into("<H", vbr, 14, rsvd)
    vbr[16] = num_fats
    struct.pack_into("<H", vbr, 17, root_ent)
    struct.pack_into("<H", vbr, 19, tot_sectors)
    vbr[21] = 0xF8
    struct.pack_into("<H", vbr, 22, fat_sectors)
    vbr[54:62] = b"FAT12   " if norm == "FAT12" else b"FAT16   "
    vbr[510:512] = b"\x55\xaa"
    return bytes(vbr)


def parse_p1_fat12_fat16_vbr(vbr_bytes: bytes) -> P1VfatAuditResult:
    """Verify a 512-byte internal/capsule `p1` failsafe VBR is FAT12 or FAT16 (never exFAT)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if len(vbr_bytes) < 512:
        _add_code(codes, STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID)
        errors.append(f"p1 VBR requires at least 512 bytes, got {len(vbr_bytes)}")
        return P1VfatAuditResult(
            valid=False,
            status=STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID,
            violation_codes=tuple(codes),
            fat_type="INVALID",
            oem_name_hex=vbr_bytes[3:11].hex() if len(vbr_bytes) >= 11 else "",
            oem_name_ascii="",
            filsys_type_hex="",
            filsys_type_ascii="",
            bytes_per_sector=0,
            sectors_per_cluster=0,
            reserved_sectors=0,
            num_fats=0,
            root_entry_count=0,
            total_sectors=0,
            fat_sectors=0,
            data_clusters=0,
            media_descriptor_hex="00",
            boot_signature_hex="0000",
            is_exfat_spoofed=False,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    oem_raw = vbr_bytes[3:11]
    oem_hex = oem_raw.hex()
    oem_ascii = oem_raw.decode("ascii", errors="replace")
    is_exfat = oem_raw == EXFAT_FS_NAME
    if is_exfat:
        _add_code(codes, STATUS_BLOCKED_FILESYSTEM_SEPARATION)
        errors.append(
            "Internal p1 failsafe partition carries 'EXFAT   ' OEM signature; p1 MUST remain FAT12/FAT16."
        )

    bps = struct.unpack_from("<H", vbr_bytes, 11)[0]
    spc = vbr_bytes[13]
    rsvd = struct.unpack_from("<H", vbr_bytes, 14)[0]
    num_fats = vbr_bytes[16]
    root_ent = struct.unpack_from("<H", vbr_bytes, 17)[0]
    tot16 = struct.unpack_from("<H", vbr_bytes, 19)[0]
    media = vbr_bytes[21]
    fat_sz16 = struct.unpack_from("<H", vbr_bytes, 22)[0]
    tot32 = struct.unpack_from("<I", vbr_bytes, 32)[0]
    tot_sectors = tot16 if tot16 != 0 else tot32
    filsys_raw = vbr_bytes[54:62]
    filsys_hex = filsys_raw.hex()
    filsys_ascii = filsys_raw.decode("ascii", errors="replace")
    boot_sig = struct.unpack_from("<H", vbr_bytes, 510)[0]

    if boot_sig != 0xAA55:
        _add_code(codes, STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID)
        errors.append(f"p1 VBR invalid BootSignature {hex(boot_sig)} (expected 0xaa55)")
    if bps not in (512, 1024, 2048, 4096):
        _add_code(codes, STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID)
        errors.append(f"p1 VBR invalid BytesPerSector={bps}")
    if not _is_power_of_two(spc) or spc > 128:
        _add_code(codes, STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID)
        errors.append(f"p1 VBR invalid SectorsPerCluster={spc}")
    if rsvd < 1:
        _add_code(codes, STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID)
        errors.append(f"p1 VBR ReservedSectors={rsvd} must be >= 1")
    if num_fats not in (1, 2):
        _add_code(codes, STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID)
        errors.append(f"p1 VBR NumFATs={num_fats} must be 1 or 2")
    if root_ent == 0 or (bps > 0 and (root_ent * 32) % bps != 0):
        _add_code(codes, STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID)
        errors.append(f"p1 VBR invalid RootEntryCount={root_ent} for FAT12/FAT16")
    if fat_sz16 == 0:
        _add_code(codes, STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID)
        errors.append("p1 VBR FATSize16 must be > 0 for FAT12/FAT16")
    if media not in (0xF0, 0xF8):
        _add_code(codes, STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID)
        errors.append(f"p1 VBR unexpected MediaDescriptor={hex(media)}")

    data_clusters = 0
    fat_type = "INVALID"
    if bps in (512, 1024, 2048, 4096) and spc > 0 and fat_sz16 > 0 and tot_sectors > 0:
        root_dir_sectors = ((root_ent * 32) + (bps - 1)) // bps
        non_data_sectors = rsvd + num_fats * fat_sz16 + root_dir_sectors
        if tot_sectors <= non_data_sectors:
            _add_code(codes, STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID)
            errors.append(
                f"p1 VBR TotalSectors={tot_sectors} <= non-data sectors {non_data_sectors}"
            )
        else:
            data_sectors = tot_sectors - non_data_sectors
            data_clusters = data_sectors // spc
            if data_clusters < 4085:
                fat_type = "FAT12"
            elif data_clusters < 65525:
                fat_type = "FAT16"
            else:
                fat_type = "FAT32"
                _add_code(codes, STATUS_BLOCKED_FILESYSTEM_SEPARATION)
                errors.append(
                    f"p1 cluster count {data_clusters} classifies as FAT32; p1 requires FAT12 or FAT16"
                )

    stripped_fs = filsys_ascii.strip().upper()
    if stripped_fs and stripped_fs not in ("FAT12", "FAT16", "FAT"):
        _add_code(codes, STATUS_BLOCKED_FILESYSTEM_SEPARATION)
        errors.append(f"p1 BS_FilSysType={filsys_ascii!r} is not FAT12/FAT16")
    elif stripped_fs in ("FAT12", "FAT16") and fat_type in VALID_P1_FAT_TYPES and stripped_fs != fat_type:
        _add_code(codes, STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID)
        errors.append(f"p1 BS_FilSysType={stripped_fs} disagrees with cluster geometry ({fat_type})")

    valid = len(errors) == 0 and fat_type in VALID_P1_FAT_TYPES and not is_exfat
    status = STATUS_VERIFIED_SAFE if valid else codes[0]
    return P1VfatAuditResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        fat_type=fat_type,
        oem_name_hex=oem_hex,
        oem_name_ascii=oem_ascii,
        filsys_type_hex=filsys_hex,
        filsys_type_ascii=filsys_ascii,
        bytes_per_sector=bps,
        sectors_per_cluster=spc,
        reserved_sectors=rsvd,
        num_fats=num_fats,
        root_entry_count=root_ent,
        total_sectors=tot_sectors,
        fat_sectors=fat_sz16,
        data_clusters=data_clusters,
        media_descriptor_hex=f"{media:02x}",
        boot_signature_hex=f"{boot_sig:04x}",
        is_exfat_spoofed=is_exfat,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_p1_vs_exfat_filesystem_separation(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    p1_vbr_bytes: Optional[bytes] = None,
    p1_image_path: Optional[Path] = None,
    p1_device_node: str = "/dev/nflasha1",
    slot_a: Optional[MediaSlotConfig] = None,
    slot_b: Optional[MediaSlotConfig] = None,
    planned_mounts: Sequence[str] = (),
    planned_writes: Sequence[str] = (),
    request_persistent_emmc_writes: bool = False,
) -> FilesystemSeparationResult:
    """Verify strict separation between internal FAT12/FAT16 `p1` and external exFAT Slot A/B media."""
    clean_forced = _is_forced_clean_room(force_clean_room)
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    blocked_targets: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False)."
        )

    if p1_vbr_bytes is not None:
        vbr_raw = p1_vbr_bytes[:512]
        mode = "EXPLICIT_P1_VBR"
    elif p1_image_path is not None:
        vbr_raw = read_slice_o_rdonly(p1_image_path, 0, 512)
        mode = "EXPLICIT_P1_IMAGE_O_RDONLY"
    else:
        donor_p1 = None if clean_forced else _resolve_donor_p1_path(work_root=work_root, repo_root=repo_root)
        if donor_p1 is not None:
            vbr_raw = read_slice_o_rdonly(donor_p1, 0, 512)
            mode = "LOCAL_DONOR_O_RDONLY"
        else:
            vbr_raw = build_synthetic_p1_fat12_vbr(fat_type=PINNED_P1_FAT_TYPE)
            mode = "CLEAN_ROOM_SYNTHETIC"

    p1_audit = parse_p1_fat12_fat16_vbr(vbr_raw)
    if not p1_audit.valid:
        for c in p1_audit.violation_codes:
            _add_code(codes, c)
        errors.extend(p1_audit.errors)

    # Verify p1_device_node is internal p1 (not external card slot)
    p1_dev_low = p1_device_node.strip().lower()
    if p1_dev_low not in ("/dev/nflasha1", "/dev/pnflasha1", "/dev/cnflasha1", "p1:/updater"):
        _add_code(codes, STATUS_BLOCKED_FILESYSTEM_SEPARATION)
        blocked_targets.append(f"p1_device:{p1_device_node}")
        errors.append(
            f"p1_device_node={p1_device_node!r} must refer to internal p1 failsafe partition."
        )

    eff_a = slot_a if slot_a is not None else MediaSlotConfig(slot_id=SLOT_A, inserted=True)
    eff_b = slot_b if slot_b is not None else MediaSlotConfig(
        slot_id=SLOT_B, inserted=False, device_node="/dev/mmcblk2p1", mount_point="/mnt/slot_b"
    )

    # External slots must NEVER point at internal eMMC / p1 / SPI NOR devices or mount paths
    for s in (eff_a, eff_b):
        for field_label, val in (("device_node", s.device_node), ("mount_point", s.mount_point)):
            low_val = val.strip().lower()
            for tok in INTERNAL_EMMC_OR_P1_TOKENS:
                if tok in low_val:
                    _add_code(codes, STATUS_BLOCKED_FILESYSTEM_SEPARATION)
                    blocked_targets.append(f"{s.slot_id}:{field_label}:{val}")
                    errors.append(
                        f"External {s.slot_id} {field_label}={val!r} overlaps protected internal partition/eMMC token {tok!r}."
                    )
                    break

    if eff_a.inserted and eff_b.inserted:
        if eff_a.device_node.strip() == eff_b.device_node.strip():
            _add_code(codes, STATUS_BLOCKED_FILESYSTEM_SEPARATION)
            blocked_targets.append(f"slot_overlap_dev:{eff_a.device_node}")
            errors.append(f"Slot A and Slot B share identical device_node={eff_a.device_node!r}.")
        if eff_a.mount_point.strip() == eff_b.mount_point.strip():
            _add_code(codes, STATUS_BLOCKED_FILESYSTEM_SEPARATION)
            blocked_targets.append(f"slot_overlap_mnt:{eff_a.mount_point}")
            errors.append(f"Slot A and Slot B share identical mount_point={eff_a.mount_point!r}.")

    # Audit planned mounts & writes for cross-domain exFAT <-> p1/eMMC violations
    for label, entries in (("mount", planned_mounts), ("write", planned_writes)):
        for raw_entry in entries:
            low = str(raw_entry).strip().lower()
            hits_internal = any(tok in low for tok in INTERNAL_EMMC_OR_P1_TOKENS)
            mentions_exfat_or_slot = (
                "exfat" in low
                or "slot_a" in low
                or "slot_b" in low
                or "xdroot" in low
                or "m4root" in low
                or "cfexpress" in low
            )
            if hits_internal and (label == "write" or mentions_exfat_or_slot):
                _add_code(codes, STATUS_BLOCKED_FILESYSTEM_SEPARATION)
                blocked_targets.append(f"{label}:{raw_entry}")
                errors.append(
                    f"Cross-domain {label} violating p1/eMMC vs external exFAT separation blocked: {raw_entry!r}"
                )

    valid = len(errors) == 0
    status = STATUS_VERIFIED_SAFE if valid else codes[0]
    return FilesystemSeparationResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=mode,
        p1_device_node=p1_device_node,
        p1_filesystem=p1_audit.fat_type,
        p1_vbr_audit=p1_audit.to_dict(),
        slot_a_device_node=eff_a.device_node,
        slot_b_device_node=eff_b.device_node,
        strict_separation_enforced=valid,
        blocked_cross_domain_targets=tuple(blocked_targets),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Unified Phase 57 Evaluator & CLI
# ---------------------------------------------------------------------------


def evaluate_exfat_media_integrity_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    slot_a: Optional[MediaSlotConfig] = None,
    slot_b: Optional[MediaSlotConfig] = None,
    p1_vbr_bytes: Optional[bytes] = None,
    p1_image_path: Optional[Path] = None,
    p1_device_node: str = "/dev/nflasha1",
    planned_mounts: Sequence[str] = (),
    planned_writes: Sequence[str] = (),
    require_at_least_one_lab_card: bool = True,
    request_persistent_emmc_writes: bool = False,
) -> ExfatMediaIntegrityReport:
    """Run all Phase 57 exFAT VBR/BootChecksum, dual-slot Sony media firewall & p1 separation checks."""
    clean_forced = _is_forced_clean_room(force_clean_room)

    eff_a = slot_a if slot_a is not None else MediaSlotConfig(
        slot_id=SLOT_A,
        inserted=True,
        media_type=MEDIA_TYPE_CFEXPRESS_A,
        device_node="/dev/mmcblk1p1",
        mount_point="/mnt/slot_a",
        exfat_boot_bytes=build_synthetic_exfat_boot_region(),
        card_entries=(),
        dedicated_lab_card=True,
    )
    eff_b = slot_b if slot_b is not None else MediaSlotConfig(
        slot_id=SLOT_B,
        inserted=False,
        media_type=MEDIA_TYPE_SDXC,
        device_node="/dev/mmcblk2p1",
        mount_point="/mnt/slot_b",
        dedicated_lab_card=False,
    )

    firewall = verify_dual_slot_media_firewall(
        slot_a=eff_a,
        slot_b=eff_b,
        require_at_least_one_lab_card=require_at_least_one_lab_card,
    )
    separation = verify_p1_vs_exfat_filesystem_separation(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=clean_forced,
        p1_vbr_bytes=p1_vbr_bytes,
        p1_image_path=p1_image_path,
        p1_device_node=p1_device_node,
        slot_a=eff_a,
        slot_b=eff_b,
        planned_mounts=planned_mounts,
        planned_writes=planned_writes,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
    )

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    for c in firewall.violation_codes + separation.violation_codes:
        _add_code(codes, c)
    errors.extend(firewall.errors)
    errors.extend(separation.errors)
    warnings.extend(firewall.warnings)
    warnings.extend(separation.warnings)

    all_passed = firewall.valid and separation.valid and (not errors)
    h0_h1_allowed = all_passed and firewall.h0_h1_trial_entry_allowed and separation.strict_separation_enforced
    status = STATUS_VERIFIED_SAFE if all_passed else codes[0]

    return ExfatMediaIntegrityReport(
        schema=EXFAT_MEDIA_INTEGRITY_GUARD_SCHEMA,
        version=EXFAT_MEDIA_INTEGRITY_GUARD_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=separation.verification_mode,
        clean_room_forced=clean_forced,
        all_passed=all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=status,
        violation_codes=tuple(codes),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        dual_slot_firewall=firewall.to_dict(),
        filesystem_separation=separation.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def main(argv: Optional[List[str]] = None) -> int:
    import json

    parser = argparse.ArgumentParser(
        prog="fx3_safety.exfat_media_integrity_guard",
        description="Phase 57 Non-Journaled exFAT BootChecksum, Sony Media Tree & Dual CFexpress Firewall",
    )
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    parser.add_argument("--slot-a-root", type=Path, help="Optional Slot A mounted directory to scan read-only")
    parser.add_argument("--slot-b-root", type=Path, help="Optional Slot B mounted directory to scan read-only")
    parser.add_argument("--slot-a-image", type=Path, help="Optional Slot A exFAT image/VBR file (O_RDONLY)")
    parser.add_argument("--slot-b-image", type=Path, help="Optional Slot B exFAT image/VBR file (O_RDONLY)")
    parser.add_argument("--p1-image", type=Path, help="Optional p1 FAT12/FAT16 image/VBR file (O_RDONLY)")
    args = parser.parse_args(argv)

    slot_a: Optional[MediaSlotConfig] = None
    if args.slot_a_root is not None or args.slot_a_image is not None:
        slot_a = MediaSlotConfig(
            slot_id=SLOT_A,
            inserted=True,
            exfat_boot_bytes=None if args.slot_a_image is not None else build_synthetic_exfat_boot_region(),
            exfat_image_path=args.slot_a_image,
            card_root=args.slot_a_root,
            card_entries=None if args.slot_a_root is not None else (),
            dedicated_lab_card=True,
        )

    slot_b: Optional[MediaSlotConfig] = None
    if args.slot_b_root is not None or args.slot_b_image is not None:
        slot_b = MediaSlotConfig(
            slot_id=SLOT_B,
            inserted=True,
            media_type=MEDIA_TYPE_SDXC,
            device_node="/dev/mmcblk2p1",
            mount_point="/mnt/slot_b",
            exfat_boot_bytes=None if args.slot_b_image is not None else build_synthetic_exfat_boot_region(),
            exfat_image_path=args.slot_b_image,
            card_root=args.slot_b_root,
            card_entries=None if args.slot_b_root is not None else (),
            dedicated_lab_card=True,
        )

    report = evaluate_exfat_media_integrity_guard(
        force_clean_room=True if args.clean_room else None,
        slot_a=slot_a,
        slot_b=slot_b,
        p1_image_path=args.p1_image,
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} all_passed={report.all_passed} "
            f"h0_h1_trial_entry_allowed={report.h0_h1_trial_entry_allowed} "
            f"p1_fs={report.filesystem_separation['p1_filesystem']} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
