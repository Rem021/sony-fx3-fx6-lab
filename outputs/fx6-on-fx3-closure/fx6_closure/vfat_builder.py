"""Pure-Python Deterministic VFAT (FAT16 / FAT32) Image Builder & BPB Verifier for P2 (/etc/opelog).

Supports zero-repartitioning FX6 `/dev/nflasha21` -> `/dev/loop7` loopback adaptation:
- 8 MiB RAM mode (`/tmp/opelog.vfat`, FAT16)
- 16 MiB persistent mode (`/log/opelog.vfat` on FX3 499MiB p11, FAT16)
- 44.5 MiB native-geometry mode (91,136 sectors = `0x16400` sectors, FAT16 or FAT32)

Pre-populates deterministic directory tree `/OPE`, `/OPE/00`, `/OPE/01` with valid `.` and `..`
entries and dual identical FAT tables, without leaving any binary `.img`/`.vfat` in the repository.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


SECTOR_SIZE = 512
ATTR_READ_ONLY = 0x01
ATTR_HIDDEN = 0x02
ATTR_SYSTEM = 0x04
ATTR_VOLUME_ID = 0x08
ATTR_DIRECTORY = 0x10
ATTR_ARCHIVE = 0x20

DETERMINISTIC_FAT_DATE = ((2026 - 1980) << 9) | (11 << 5) | 10
DETERMINISTIC_FAT_TIME = 0x0000
DETERMINISTIC_VOL_ID = 0x46583632  # 'FX62'

PRESET_MODES: Dict[str, Tuple[int, str]] = {
    "8m_ram": (8 * 1024 * 1024, "FAT16"),
    "16m_log": (16 * 1024 * 1024, "FAT16"),
    "44.5m_log": (91136 * SECTOR_SIZE, "FAT16"),
    "44.5m_fat32": (91136 * SECTOR_SIZE, "FAT32"),
}


class VfatValidationError(ValueError):
    """Raised when a VFAT image fails BPB, FAT table, or directory hierarchy validation."""


@dataclass(frozen=True)
class VfatBuildReceipt:
    mode: str
    fat_type: str
    total_bytes: int
    total_sectors: int
    bytes_per_sector: int
    sectors_per_cluster: int
    reserved_sectors: int
    num_fats: int
    sectors_per_fat: int
    cluster_count: int
    precreated_dirs: Tuple[str, ...]
    sha256: str


@dataclass(frozen=True)
class VfatAuditResult:
    valid: bool
    fat_type: str
    total_bytes: int
    total_sectors: int
    bytes_per_sector: int
    sectors_per_cluster: int
    reserved_sectors: int
    num_fats: int
    sectors_per_fat: int
    cluster_count: int
    fats_identical: bool
    discovered_dirs: Tuple[str, ...]
    errors: Tuple[str, ...]


def _format_short_name(name: str) -> bytes:
    if name == ".":
        return b".          "
    if name == "..":
        return b"..         "
    if "." in name:
        stem, ext = name.split(".", 1)
    else:
        stem, ext = name, ""
    stem_b = stem.upper().encode("ascii")[:8].ljust(8, b" ")
    ext_b = ext.upper().encode("ascii")[:3].ljust(3, b" ")
    return stem_b + ext_b


def _pack_dir_entry(
    name: str,
    attr: int,
    cluster: int,
    file_size: int = 0,
) -> bytes:
    entry = bytearray(32)
    entry[0:11] = _format_short_name(name)
    entry[11] = attr
    entry[12] = 0x00
    entry[13] = 0x00
    struct.pack_into("<HH", entry, 14, DETERMINISTIC_FAT_TIME, DETERMINISTIC_FAT_DATE)
    struct.pack_into("<H", entry, 18, DETERMINISTIC_FAT_DATE)
    struct.pack_into("<H", entry, 20, (cluster >> 16) & 0xFFFF)
    struct.pack_into("<HH", entry, 22, DETERMINISTIC_FAT_TIME, DETERMINISTIC_FAT_DATE)
    struct.pack_into("<H", entry, 26, cluster & 0xFFFF)
    struct.pack_into("<I", entry, 28, file_size)
    return bytes(entry)


def _choose_geometry(total_sectors: int, fat_type: str) -> Tuple[int, int, int, int]:
    """Return `(sectors_per_cluster, reserved_sectors, root_entry_count, sectors_per_fat)`."""
    if fat_type == "FAT16":
        reserved = 4
        root_entries = 512
        root_dir_sectors = (root_entries * 32 + SECTOR_SIZE - 1) // SECTOR_SIZE
        for spc in (1, 2, 4, 8, 16, 32, 64):
            fat_sz = 1
            for _ in range(8):
                data_sec = total_sectors - reserved - root_dir_sectors - 2 * fat_sz
                if data_sec <= 0:
                    break
                clusters = data_sec // spc
                needed_bytes = (clusters + 2) * 2
                fat_sz = (needed_bytes + SECTOR_SIZE - 1) // SECTOR_SIZE
            data_sec = total_sectors - reserved - root_dir_sectors - 2 * fat_sz
            clusters = data_sec // spc if data_sec > 0 else 0
            if 4085 <= clusters < 65525:
                return spc, reserved, root_entries, fat_sz
        raise ValueError(f"Cannot fit valid FAT16 geometry (4085..65524 clusters) in {total_sectors} sectors")

    if fat_type == "FAT32":
        reserved = 32
        root_entries = 0
        for spc in (1, 2, 4, 8, 16, 32, 64):
            fat_sz = 1
            for _ in range(8):
                data_sec = total_sectors - reserved - 2 * fat_sz
                if data_sec <= 0:
                    break
                clusters = data_sec // spc
                needed_bytes = (clusters + 2) * 4
                fat_sz = (needed_bytes + SECTOR_SIZE - 1) // SECTOR_SIZE
            data_sec = total_sectors - reserved - 2 * fat_sz
            clusters = data_sec // spc if data_sec > 0 else 0
            if clusters >= 65525:
                return spc, reserved, root_entries, fat_sz
        raise ValueError(f"Cannot fit valid FAT32 geometry (>=65525 clusters) in {total_sectors} sectors")

    raise ValueError(f"Unsupported FAT type: {fat_type!r} (expected 'FAT16' or 'FAT32')")


def build_opelog_vfat_image(
    mode: str = "16m_log",
    custom_size_bytes: Optional[int] = None,
    custom_fat_type: Optional[str] = None,
    volume_label: str = "FX6_OPELOG",
) -> Tuple[bytes, VfatBuildReceipt]:
    """Deterministically build an in-memory VFAT image with `/OPE`, `/OPE/00`, `/OPE/01` precreated."""
    if custom_size_bytes is not None:
        total_bytes = custom_size_bytes
        fat_type = (custom_fat_type or "FAT16").upper()
        mode_name = mode
    else:
        if mode not in PRESET_MODES:
            raise ValueError(f"Unknown preset mode {mode!r}; expected one of {sorted(PRESET_MODES.keys())}")
        total_bytes, default_fat = PRESET_MODES[mode]
        fat_type = (custom_fat_type or default_fat).upper()
        mode_name = mode

    if total_bytes <= 0 or (total_bytes % SECTOR_SIZE) != 0:
        raise ValueError(f"Image size {total_bytes} B must be a positive multiple of {SECTOR_SIZE} B")

    total_sectors = total_bytes // SECTOR_SIZE
    spc, reserved_sectors, root_entries, sectors_per_fat = _choose_geometry(total_sectors, fat_type)
    num_fats = 2
    root_dir_sectors = (root_entries * 32 + SECTOR_SIZE - 1) // SECTOR_SIZE
    first_data_sector = reserved_sectors + num_fats * sectors_per_fat + root_dir_sectors
    data_sectors = total_sectors - first_data_sector
    cluster_count = data_sectors // spc

    img = bytearray(total_bytes)
    label_padded = volume_label.upper().encode("ascii")[:11].ljust(11, b" ")

    bpb = bytearray(SECTOR_SIZE)
    bpb[0:3] = b"\xeb\x58\x90" if fat_type == "FAT32" else b"\xeb\x3c\x90"
    bpb[3:11] = b"MSWIN4.1"
    struct.pack_into(
        "<HBHBHHBHHHII",
        bpb,
        11,
        SECTOR_SIZE,
        spc,
        reserved_sectors,
        num_fats,
        root_entries,
        total_sectors if total_sectors < 65536 else 0,
        0xF8,
        sectors_per_fat if fat_type == "FAT16" else 0,
        63,
        255,
        0,
        total_sectors if total_sectors >= 65536 or fat_type == "FAT32" else 0,
    )

    if fat_type == "FAT16":
        bpb[36] = 0x80
        bpb[37] = 0x00
        bpb[38] = 0x29
        struct.pack_into("<I", bpb, 39, DETERMINISTIC_VOL_ID)
        bpb[43:54] = label_padded
        bpb[54:62] = b"FAT16   "
        bpb[510:512] = b"\x55\xaa"
        img[0:SECTOR_SIZE] = bpb
    else:
        struct.pack_into(
            "<IHHIHH",
            bpb,
            36,
            sectors_per_fat,
            0,
            0,
            2,
            1,
            6,
        )
        bpb[64] = 0x80
        bpb[65] = 0x00
        bpb[66] = 0x29
        struct.pack_into("<I", bpb, 67, DETERMINISTIC_VOL_ID)
        bpb[71:82] = label_padded
        bpb[82:90] = b"FAT32   "
        bpb[510:512] = b"\x55\xaa"
        img[0:SECTOR_SIZE] = bpb
        img[6 * SECTOR_SIZE : 7 * SECTOR_SIZE] = bpb

        fsinfo = bytearray(SECTOR_SIZE)
        struct.pack_into("<I", fsinfo, 0, 0x41615252)
        struct.pack_into("<I", fsinfo, 484, 0x61417272)
        struct.pack_into("<II", fsinfo, 488, cluster_count - 4, 6)
        struct.pack_into("<I", fsinfo, 508, 0xAA550000)
        img[1 * SECTOR_SIZE : 2 * SECTOR_SIZE] = fsinfo
        img[7 * SECTOR_SIZE : 8 * SECTOR_SIZE] = fsinfo

    def _cluster_offset(clus: int) -> int:
        return (first_data_sector + (clus - 2) * spc) * SECTOR_SIZE

    fat_bytes = bytearray(sectors_per_fat * SECTOR_SIZE)
    if fat_type == "FAT16":
        struct.pack_into("<HHHHH", fat_bytes, 0, 0xFFF8, 0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF)

        root_off = (reserved_sectors + num_fats * sectors_per_fat) * SECTOR_SIZE
        img[root_off : root_off + 32] = _pack_dir_entry(volume_label, ATTR_VOLUME_ID, 0)
        img[root_off + 32 : root_off + 64] = _pack_dir_entry("OPE", ATTR_DIRECTORY, 2)

        c2 = _cluster_offset(2)
        img[c2 : c2 + 32] = _pack_dir_entry(".", ATTR_DIRECTORY, 2)
        img[c2 + 32 : c2 + 64] = _pack_dir_entry("..", ATTR_DIRECTORY, 0)
        img[c2 + 64 : c2 + 96] = _pack_dir_entry("00", ATTR_DIRECTORY, 3)
        img[c2 + 96 : c2 + 128] = _pack_dir_entry("01", ATTR_DIRECTORY, 4)

        c3 = _cluster_offset(3)
        img[c3 : c3 + 32] = _pack_dir_entry(".", ATTR_DIRECTORY, 3)
        img[c3 + 32 : c3 + 64] = _pack_dir_entry("..", ATTR_DIRECTORY, 2)

        c4 = _cluster_offset(4)
        img[c4 : c4 + 32] = _pack_dir_entry(".", ATTR_DIRECTORY, 4)
        img[c4 + 32 : c4 + 64] = _pack_dir_entry("..", ATTR_DIRECTORY, 2)
    else:
        struct.pack_into(
            "<6I",
            fat_bytes,
            0,
            0x0FFFFFF8,
            0x0FFFFFFF,
            0x0FFFFFFF,
            0x0FFFFFFF,
            0x0FFFFFFF,
            0x0FFFFFFF,
        )

        c2 = _cluster_offset(2)
        img[c2 : c2 + 32] = _pack_dir_entry(volume_label, ATTR_VOLUME_ID, 0)
        img[c2 + 32 : c2 + 64] = _pack_dir_entry("OPE", ATTR_DIRECTORY, 3)

        c3 = _cluster_offset(3)
        img[c3 : c3 + 32] = _pack_dir_entry(".", ATTR_DIRECTORY, 3)
        img[c3 + 32 : c3 + 64] = _pack_dir_entry("..", ATTR_DIRECTORY, 0)
        img[c3 + 64 : c3 + 96] = _pack_dir_entry("00", ATTR_DIRECTORY, 4)
        img[c3 + 96 : c3 + 128] = _pack_dir_entry("01", ATTR_DIRECTORY, 5)

        c4 = _cluster_offset(4)
        img[c4 : c4 + 32] = _pack_dir_entry(".", ATTR_DIRECTORY, 4)
        img[c4 + 32 : c4 + 64] = _pack_dir_entry("..", ATTR_DIRECTORY, 3)

        c5 = _cluster_offset(5)
        img[c5 : c5 + 32] = _pack_dir_entry(".", ATTR_DIRECTORY, 5)
        img[c5 + 32 : c5 + 64] = _pack_dir_entry("..", ATTR_DIRECTORY, 3)

    for fat_idx in range(num_fats):
        fat_off = (reserved_sectors + fat_idx * sectors_per_fat) * SECTOR_SIZE
        img[fat_off : fat_off + len(fat_bytes)] = fat_bytes

    out = bytes(img)
    return out, VfatBuildReceipt(
        mode=mode_name,
        fat_type=fat_type,
        total_bytes=total_bytes,
        total_sectors=total_sectors,
        bytes_per_sector=SECTOR_SIZE,
        sectors_per_cluster=spc,
        reserved_sectors=reserved_sectors,
        num_fats=num_fats,
        sectors_per_fat=sectors_per_fat,
        cluster_count=cluster_count,
        precreated_dirs=("/OPE", "/OPE/00", "/OPE/01"),
        sha256=hashlib.sha256(out).hexdigest(),
    )


def verify_vfat_image(
    raw: bytes,
    require_opelog_dirs: bool = True,
) -> VfatAuditResult:
    """Validate BPB geometry, cluster-count FAT16/FAT32 classification, FAT mirror, and `/OPE` tree."""
    errors: List[str] = []
    if len(raw) < SECTOR_SIZE or (len(raw) % SECTOR_SIZE) != 0:
        return VfatAuditResult(
            valid=False,
            fat_type="INVALID",
            total_bytes=len(raw),
            total_sectors=len(raw) // SECTOR_SIZE,
            bytes_per_sector=0,
            sectors_per_cluster=0,
            reserved_sectors=0,
            num_fats=0,
            sectors_per_fat=0,
            cluster_count=0,
            fats_identical=False,
            discovered_dirs=(),
            errors=("Image size must be >= 512 and a multiple of 512 bytes",),
        )

    if raw[510:512] != b"\x55\xaa":
        errors.append(f"Missing Sector 0 0x55AA boot signature (got {raw[510:512].hex()})")

    if raw[0] not in (0xEB, 0xE9):
        errors.append(f"Invalid x86 jump opcode 0x{raw[0]:02x} at BPB offset 0")

    (
        byts_per_sec,
        sec_per_clus,
        rsvd_sec_cnt,
        num_fats,
        root_ent_cnt,
        tot_sec16,
        media,
        fat_sz16,
        _sec_per_trk,
        _num_heads,
        _hidd_sec,
        tot_sec32,
    ) = struct.unpack_from("<HBHBHHBHHHII", raw, 11)

    if byts_per_sec != SECTOR_SIZE:
        errors.append(f"Unsupported BPB_BytsPerSec={byts_per_sec} (expected 512)")
        byts_per_sec = SECTOR_SIZE

    if sec_per_clus == 0 or (sec_per_clus & (sec_per_clus - 1)) != 0 or sec_per_clus > 128:
        errors.append(f"Invalid BPB_SecPerClus={sec_per_clus}")
        sec_per_clus = max(sec_per_clus, 1)

    if rsvd_sec_cnt == 0:
        errors.append("BPB_RsvdSecCnt must be >= 1")
    if num_fats < 2:
        errors.append(f"BPB_NumFATs={num_fats} (expected >= 2)")
    if media != 0xF8:
        errors.append(f"Unexpected BPB_Media=0x{media:02x} (expected 0xF8 fixed disk)")

    total_sectors = tot_sec16 if tot_sec16 != 0 else tot_sec32
    if total_sectors * byts_per_sec != len(raw):
        errors.append(
            f"BPB total_sectors ({total_sectors}) * {byts_per_sec} != actual image bytes ({len(raw)})"
        )

    fat_sz = fat_sz16 if fat_sz16 != 0 else struct.unpack_from("<I", raw, 36)[0]
    if fat_sz == 0:
        errors.append("Both BPB_FATSz16 and BPB_FATSz32 are 0")

    root_dir_sectors = (root_ent_cnt * 32 + byts_per_sec - 1) // byts_per_sec
    first_data_sector = rsvd_sec_cnt + num_fats * fat_sz + root_dir_sectors
    if first_data_sector >= total_sectors:
        errors.append(f"first_data_sector ({first_data_sector}) >= total_sectors ({total_sectors})")
        cluster_count = 0
    else:
        cluster_count = (total_sectors - first_data_sector) // sec_per_clus

    if cluster_count < 4085:
        fat_type = "FAT12"
        errors.append(f"Cluster count {cluster_count} < 4085 (FAT12); P2 opelog requires FAT16 or FAT32")
    elif cluster_count < 65525:
        fat_type = "FAT16"
        if fat_sz16 == 0 or root_ent_cnt == 0:
            errors.append("FAT16 cluster count requires non-zero BPB_FATSz16 and BPB_RootEntCnt")
    else:
        fat_type = "FAT32"
        if fat_sz16 != 0 or root_ent_cnt != 0:
            errors.append("FAT32 cluster count requires BPB_FATSz16 == 0 and BPB_RootEntCnt == 0")

    fats_identical = True
    fat0 = b""
    if fat_sz > 0 and rsvd_sec_cnt + num_fats * fat_sz <= len(raw) // byts_per_sec:
        fat_byte_len = fat_sz * byts_per_sec
        f0_off = rsvd_sec_cnt * byts_per_sec
        fat0 = raw[f0_off : f0_off + fat_byte_len]
        for idx in range(1, num_fats):
            fi_off = (rsvd_sec_cnt + idx * fat_sz) * byts_per_sec
            if raw[fi_off : fi_off + fat_byte_len] != fat0:
                fats_identical = False
                errors.append(f"FAT copy {idx} differs from FAT copy 0")

        if fat_type == "FAT16" and len(fat0) >= 4:
            e0, e1 = struct.unpack_from("<HH", fat0, 0)
            if e0 != 0xFFF8 or e1 != 0xFFFF:
                errors.append(f"FAT16 reserved entries [0,1]=(0x{e0:04x}, 0x{e1:04x}), expected (0xfff8, 0xffff)")
        elif fat_type == "FAT32" and len(fat0) >= 8:
            e0, e1 = struct.unpack_from("<II", fat0, 0)
            if (e0 & 0x0FFFFFFF) != 0x0FFFFFF8 or (e1 & 0x0FFFFFFF) < 0x0FFFFFF8:
                errors.append(f"FAT32 reserved entries [0,1]=(0x{e0:08x}, 0x{e1:08x}) invalid")
            fsinfo_sec = struct.unpack_from("<H", raw, 48)[0]
            if fsinfo_sec == 0 or (fsinfo_sec + 1) * byts_per_sec > len(raw):
                errors.append(f"Invalid FAT32 FSInfo sector {fsinfo_sec}")
            else:
                fsi = raw[fsinfo_sec * byts_per_sec : (fsinfo_sec + 1) * byts_per_sec]
                sig1 = struct.unpack_from("<I", fsi, 0)[0]
                sig2 = struct.unpack_from("<I", fsi, 484)[0]
                sig3 = struct.unpack_from("<I", fsi, 508)[0]
                if (sig1, sig2, sig3) != (0x41615252, 0x61417272, 0xAA550000):
                    errors.append("FAT32 FSInfo signatures corrupted")
    else:
        fats_identical = False

    discovered: List[str] = []

    def _read_cluster_chain(start_clus: int) -> bytes:
        if start_clus < 2 or start_clus >= cluster_count + 2:
            errors.append(f"Directory cluster {start_clus} out of valid range 2..{cluster_count + 1}")
            return b""
        seen = set()
        cur = start_clus
        chunks: List[bytes] = []
        while True:
            if cur in seen:
                errors.append(f"Cycle detected in FAT cluster chain at cluster {cur}")
                break
            seen.add(cur)
            off = (first_data_sector + (cur - 2) * sec_per_clus) * byts_per_sec
            chunks.append(raw[off : off + sec_per_clus * byts_per_sec])
            if fat_type == "FAT16":
                nxt = struct.unpack_from("<H", fat0, cur * 2)[0]
                if nxt >= 0xFFF8:
                    break
                if nxt < 2 or nxt >= cluster_count + 2:
                    errors.append(f"Invalid FAT16 next-cluster entry 0x{nxt:04x} at cluster {cur}")
                    break
                cur = nxt
            else:
                nxt = struct.unpack_from("<I", fat0, cur * 4)[0] & 0x0FFFFFFF
                if nxt >= 0x0FFFFFF8:
                    break
                if nxt < 2 or nxt >= cluster_count + 2:
                    errors.append(f"Invalid FAT32 next-cluster entry 0x{nxt:08x} at cluster {cur}")
                    break
                cur = nxt
        return b"".join(chunks)

    def _walk_dir(dir_bytes: bytes, prefix: str, expected_self_clus: Optional[int], expected_parent_clus: int) -> None:
        saw_dot = False
        saw_dotdot = False
        for off in range(0, len(dir_bytes), 32):
            ent = dir_bytes[off : off + 32]
            if ent[0] == 0x00:
                break
            if ent[0] == 0xE5 or ent[11] == 0x0F or (ent[11] & ATTR_VOLUME_ID):
                continue
            stem = ent[0:8].decode("ascii", errors="replace").rstrip(" ")
            ext = ent[8:11].decode("ascii", errors="replace").rstrip(" ")
            name = f"{stem}.{ext}" if ext else stem
            hi = struct.unpack_from("<H", ent, 20)[0] if fat_type == "FAT32" else 0
            lo = struct.unpack_from("<H", ent, 26)[0]
            clus = (hi << 16) | lo

            if name == ".":
                saw_dot = True
                if expected_self_clus is not None and clus != expected_self_clus:
                    errors.append(f"Directory {prefix} '.' cluster={clus}, expected {expected_self_clus}")
                continue
            if name == "..":
                saw_dotdot = True
                if clus != expected_parent_clus:
                    errors.append(f"Directory {prefix} '..' cluster={clus}, expected {expected_parent_clus}")
                continue

            if ent[11] & ATTR_DIRECTORY:
                full = f"{prefix}/{name}" if prefix != "/" else f"/{name}"
                discovered.append(full)
                sub_bytes = _read_cluster_chain(clus)
                parent_expect = 0 if expected_self_clus is None else expected_self_clus
                _walk_dir(sub_bytes, full, clus, parent_expect)

        if expected_self_clus is not None and (not saw_dot or not saw_dotdot):
            errors.append(f"Subdirectory {prefix} missing mandatory '.' or '..' entry")

    if not errors:
        if fat_type == "FAT16":
            r_off = (rsvd_sec_cnt + num_fats * fat_sz) * byts_per_sec
            r_bytes = raw[r_off : r_off + root_dir_sectors * byts_per_sec]
            _walk_dir(r_bytes, "/", None, 0)
        elif fat_type == "FAT32":
            root_clus = struct.unpack_from("<I", raw, 44)[0]
            r_bytes = _read_cluster_chain(root_clus)
            _walk_dir(r_bytes, "/", None, 0)

    if require_opelog_dirs:
        for req_dir in ("/OPE", "/OPE/00", "/OPE/01"):
            if req_dir not in discovered:
                errors.append(f"Missing required precreated opelog directory: {req_dir}")

    return VfatAuditResult(
        valid=len(errors) == 0,
        fat_type=fat_type,
        total_bytes=len(raw),
        total_sectors=total_sectors,
        bytes_per_sector=byts_per_sec,
        sectors_per_cluster=sec_per_clus,
        reserved_sectors=rsvd_sec_cnt,
        num_fats=num_fats,
        sectors_per_fat=fat_sz,
        cluster_count=cluster_count,
        fats_identical=fats_identical,
        discovered_dirs=tuple(discovered),
        errors=tuple(errors),
    )


def generate_p2_opelog_mount_snippet(
    backing_image_path: str = "/log/opelog.vfat",
    loop_dev: str = "/dev/loop7",
    mount_point: str = "/etc/opelog",
) -> str:
    """Generate an idempotent POSIX sh loopback adaptation snippet for `/dev/nflasha21` (`/etc/opelog`)."""
    return (
        "#!/bin/sh\n"
        "# FX6-on-FX3 P2 /dev/nflasha21 -> /etc/opelog VFAT Loopback Adaptation (Idempotent)\n"
        f'mkdir -p "{mount_point}"\n'
        f'if [ -f "{backing_image_path}" ]; then\n'
        f'    busybox losetup -d "{loop_dev}" >/dev/null 2>&1 || true\n'
        f'    if busybox losetup "{loop_dev}" "{backing_image_path}"; then\n'
        "        rm -f /dev/nflasha21\n"
        f'        ln -s "{loop_dev}" /dev/nflasha21\n'
        f'        busybox mount -t vfat -o shortname=mixed /dev/nflasha21 "{mount_point}" >/dev/null 2>&1 || true\n'
        "    fi\n"
        "fi\n"
        f'mkdir -p "{mount_point}/ope/00" "{mount_point}/ope/01"\n'
    )
