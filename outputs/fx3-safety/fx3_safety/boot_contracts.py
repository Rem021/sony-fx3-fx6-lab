"""Byte-exact validators for Sony CXD90057 boot contracts:
1. eMMC UDA Sector 0 ('8246' '2.00' 30-entry Sony Partition Table)
2. p2:/Backup.bin ('BK4\\0' dual-record headers, 32-bit byte-sum checksums, and 0xfa0080 64-slot descriptor table)
3. Octal-SPI NOR LdrBkup.bin ('BKSB' 65-key compact store)
4. Cross-model FX3 (7.02) vs FX6 (6.01) partition & CP Bank 1 hazard detection
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple


SONY_PTBL_MAGIC = b"8246"
SONY_PTBL_VERSION = b"2.00"
SONY_PTBL_ENTRY_COUNT = 30
SONY_PTBL_SIZE = 512

BK4_SYNC_MARKER = 0xAAAAAAAA
BK4_MAGIC = b"BK4\x00"
BK4_HEADER_SIZE = 256

BKSB_MAGIC = 0x42534B42  # "BKSB"

FA0080_TOTAL_BYTES = 9216
FA0080_SLOT_STRIDE = 144
FA0080_SLOT_COUNT = 64

# Canonical FX3 7.02 vs FX6 6.01 partition expectations (in 512-byte sectors)
FX3_KEY_PARTITIONS: Dict[int, Tuple[int, int, int, int, str]] = {
    1: (0x00000080, 0x0000BF80, 4, 1, "p1:/updater (Plaintext VFAT)"),
    2: (0x0000C000, 0x0000A000, 4, 1, "p2:/setting (Backup.bin, psd.bin, defdet.bin, cxd90057.dtb)"),
    3: (0x00016000, 0x00025800, 5, 1, "p3:/system (vmlinux.bin, initrd.img, av-cam.bin, bonobo.bin)"),
    5: (0x00042000, 0x00096000, 6, 1, "p5:/wbi (Warm Boot Image WB40)"),
    6: (0x000D8000, 0x0000C800, 4, 1, "p6:/tmp/jiritsu (TIER-0 FACTORY CALIBRATION)"),
    7: (0x000E4800, 0x00019000, 5, 1, "p7:/rootfs (FX3 ext2 rootfs; size 0 on FX6)"),
    8: (0x000FD800, 0x00032000, 5, 1, "p8:/cp (cpapp-b.bin, DmmCfg.bin, cpImg.dat)"),
    12: (0x0020C000, 0x00014000, 5, 1, "p12:/cert (40 MiB on FX3 vs 20 MiB on FX6)"),
    15: (0x0022A000, 0x000FA000, 5, 1, "p15:/usr (500 MiB application stack)"),
    18: (0x0031C000, 0x0000A000, 4, 1, "p18:/lens (TIER-0 lensfile.bin; LBA 0x312000 on FX6)"),
}


@dataclass(frozen=True)
class PartitionEntry:
    index: int  # 1-based partition number (1..30)
    start_sector: int
    size_sectors: int
    part_type: int
    flag: int

    @property
    def size_bytes(self) -> int:
        return self.size_sectors * 512

    @property
    def device_node(self) -> str:
        if self.part_type == 5 and (self.flag & 1):
            return f"/dev/cnflasha{self.index}"
        return f"/dev/pnflasha{self.index}"


@dataclass(frozen=True)
class Sector0AuditResult:
    valid: bool
    magic_ok: bool
    version_ok: bool
    count: int
    layout_profile: str  # "FX3_702", "FX6_601", or "CUSTOM_OR_UNKNOWN"
    has_overlaps: bool
    calibration_partitions_intact: bool
    errors: List[str]
    warnings: List[str]
    partitions: List[Dict[str, object]]


def verify_sector0_partition_table(data: bytes) -> Sector0AuditResult:
    """Validate a 512-byte Sony eMMC UDA Sector 0 partition table ('8246' '2.00')."""
    errors: List[str] = []
    warnings: List[str] = []

    if len(data) != SONY_PTBL_SIZE:
        return Sector0AuditResult(
            valid=False,
            magic_ok=False,
            version_ok=False,
            count=0,
            layout_profile="INVALID_SIZE",
            has_overlaps=False,
            calibration_partitions_intact=False,
            errors=[f"Expected exactly {SONY_PTBL_SIZE} bytes for Sector 0, got {len(data)}"],
            warnings=[],
            partitions=[],
        )

    magic = data[0:4]
    version = data[4:8]
    count = struct.unpack_from("<I", data, 8)[0]
    padding = data[12:32]

    magic_ok = magic == SONY_PTBL_MAGIC
    version_ok = version == SONY_PTBL_VERSION
    if not magic_ok:
        errors.append(f"Invalid Sector 0 magic: {magic!r} (expected {SONY_PTBL_MAGIC!r})")
    if not version_ok:
        errors.append(f"Invalid Sector 0 version: {version!r} (expected {SONY_PTBL_VERSION!r})")
    if count != SONY_PTBL_ENTRY_COUNT:
        errors.append(f"Invalid partition count: {count} (expected {SONY_PTBL_ENTRY_COUNT})")
    if any(b != 0 for b in padding):
        warnings.append("Bytes +0x0c..0x1f are non-zero (expected 20 zero padding bytes)")

    entries: List[PartitionEntry] = []
    for idx in range(SONY_PTBL_ENTRY_COUNT):
        off = 32 + idx * 16
        start_s, size_s, ptype, flag = struct.unpack_from("<IIII", data, off)
        entries.append(
            PartitionEntry(
                index=idx + 1,
                start_sector=start_s,
                size_sectors=size_s,
                part_type=ptype,
                flag=flag,
            )
        )

    # Check for overlapping non-empty partitions and Sector 0 collision
    active_spans: List[Tuple[int, int, int]] = []
    has_overlaps = False
    for e in entries:
        if e.size_sectors == 0:
            continue
        if e.start_sector < 0x80:
            errors.append(
                f"Partition p{e.index} starts at sector {hex(e.start_sector)} (< 0x80), colliding with Sector 0 header region"
            )
            has_overlaps = True
        end_sector = e.start_sector + e.size_sectors
        for prev_start, prev_end, prev_idx in active_spans:
            if not (end_sector <= prev_start or e.start_sector >= prev_end):
                errors.append(
                    f"Partition p{e.index} [{hex(e.start_sector)}..{hex(end_sector)}) overlaps p{prev_idx} [{hex(prev_start)}..{hex(prev_end)})"
                )
                has_overlaps = True
        active_spans.append((e.start_sector, end_sector, e.index))

    # Identify FX3 vs FX6 profile and verify calibration partitions (p1, p2, p6, p18)
    by_idx = {e.index: e for e in entries}
    p1 = by_idx[1]
    p2 = by_idx[2]
    p6 = by_idx[6]
    p7 = by_idx[7]
    p12 = by_idx[12]
    p18 = by_idx[18]
    p20 = by_idx[20]
    p21 = by_idx[21]

    cal_ok = True
    for pid in (1, 2, 6):
        exp_start, exp_size, exp_type, _, label = FX3_KEY_PARTITIONS[pid]
        actual = by_idx[pid]
        if (actual.start_sector, actual.size_sectors, actual.part_type) != (exp_start, exp_size, exp_type):
            errors.append(
                f"Critical partition p{pid} ({label}) mismatch: got start={hex(actual.start_sector)} size={hex(actual.size_sectors)} type={actual.part_type}"
            )
            cal_ok = False

    layout_profile = "CUSTOM_OR_UNKNOWN"
    if (
        p7.size_sectors == 0x00019000
        and p12.size_sectors == 0x00014000
        and p18.start_sector == 0x0031C000
        and p18.size_sectors == 0x0000A000
        and p20.size_sectors == 0
        and p21.size_sectors == 0
    ):
        layout_profile = "FX3_702"
    elif (
        p7.size_sectors == 0
        and p12.size_sectors == 0x0000A000
        and p18.start_sector == 0x00312000
        and p18.size_sectors == 0x0000A000
        and p20.size_sectors == 0x00032000
        and p21.size_sectors == 0x00016400
    ):
        layout_profile = "FX6_601"
        warnings.append(
            "FX6_601 Sector 0 layout detected: p18 (/lens/lensfile.bin) is shifted -20 MiB to LBA 0x312000. "
            "Applying this table to an FX3 without migrating p18 data will orphan factory lens mount calibration!"
        )
    else:
        if p18.size_sectors != 0x0000A000 or p18.start_sector not in (0x0031C000, 0x00312000):
            errors.append(
                f"Calibration partition p18 (/lens) has unexpected geometry: start={hex(p18.start_sector)} size={hex(p18.size_sectors)}"
            )
            cal_ok = False

    valid = magic_ok and version_ok and count == SONY_PTBL_ENTRY_COUNT and not has_overlaps and cal_ok and not errors
    return Sector0AuditResult(
        valid=valid,
        magic_ok=magic_ok,
        version_ok=version_ok,
        count=count,
        layout_profile=layout_profile,
        has_overlaps=has_overlaps,
        calibration_partitions_intact=cal_ok,
        errors=errors,
        warnings=warnings,
        partitions=[
            {
                "index": e.index,
                "start_sector": hex(e.start_sector),
                "size_sectors": hex(e.size_sectors),
                "size_mib": round(e.size_bytes / (1024 * 1024), 2),
                "type": e.part_type,
                "flag": e.flag,
                "device_node": e.device_node,
            }
            for e in entries
        ],
    )


@dataclass(frozen=True)
class BK4RecordSummary:
    record_index: int
    file_offset: int
    total_bytes: int
    sync_word: int
    active_byte8: int
    magic_ok: bool
    subsystems: int
    properties: int
    data_offset: int
    data_size: int
    expected_checksum: int
    computed_checksum: int
    checksum_ok: bool
    revision_word2c: int
    strict_loader_selectable: bool


def parse_bk4_record(buf: bytes, offset: int = 0, record_index: int = 0) -> Tuple[Optional[BK4RecordSummary], List[str]]:
    """Validate a single BK4\\0 record inside Backup.bin using loader_nor.bin's exact rules (0xfe04c76c / 0xfe04d584)."""
    errors: List[str] = []
    if offset + BK4_HEADER_SIZE > len(buf):
        return None, [f"Record {record_index} at {hex(offset)} truncated before 256-byte BK4 header"]

    word4 = struct.unpack_from("<I", buf, offset + 0x04)[0]
    byte8 = buf[offset + 0x08]
    magic = buf[offset + 0x0C : offset + 0x10]
    subs, props, dataoff, datasize, expected_sum = struct.unpack_from("<IIIII", buf, offset + 0x10)
    word2c = struct.unpack_from("<i", buf, offset + 0x2C)[0]

    magic_ok = magic == BK4_MAGIC
    if word4 != BK4_SYNC_MARKER:
        errors.append(f"Record {record_index} word4 sync marker is {hex(word4)} (expected 0xaaaaaaaa)")
    if not magic_ok:
        errors.append(f"Record {record_index} magic is {magic!r} (expected b'BK4\\x00')")

    total_bytes = dataoff + datasize
    if dataoff < BK4_HEADER_SIZE or offset + total_bytes > len(buf):
        errors.append(
            f"Record {record_index} span [{hex(offset)}..{hex(offset + total_bytes)}) exceeds file size {hex(len(buf))}"
        )
        return None, errors

    # loader_nor.bin 0xfe04d514: 32-bit unsigned byte sum of record[0 : total_bytes] skipping [0x20 : 0x24]
    rec_slice = buf[offset : offset + total_bytes]
    computed_sum = (sum(rec_slice[0:0x20]) + sum(rec_slice[0x24:total_bytes])) & 0xFFFFFFFF
    checksum_ok = computed_sum == expected_sum
    if not checksum_ok:
        errors.append(
            f"Record {record_index} BK4 checksum mismatch: header={hex(expected_sum)} computed={hex(computed_sum)}"
        )

    # loader_nor.bin 0xfe04c7a8 -> 0xfe04d584 (strict mode W2=1) requires word4 == 0xaaaaaaaa and byte8 == 1
    strict_selectable = (word4 == BK4_SYNC_MARKER) and (byte8 == 1) and magic_ok and checksum_ok

    summary = BK4RecordSummary(
        record_index=record_index,
        file_offset=offset,
        total_bytes=total_bytes,
        sync_word=word4,
        active_byte8=byte8,
        magic_ok=magic_ok,
        subsystems=subs,
        properties=props,
        data_offset=dataoff,
        data_size=datasize,
        expected_checksum=expected_sum,
        computed_checksum=computed_sum,
        checksum_ok=checksum_ok,
        revision_word2c=word2c,
        strict_loader_selectable=strict_selectable,
    )
    return summary, errors


@dataclass(frozen=True)
class Fa0080Slot:
    slot_index: int
    start_addr: int
    end_addr: int
    partition: int
    mode: int
    path: str

    @property
    def capacity_bytes(self) -> int:
        if self.end_addr >= self.start_addr and self.start_addr > 0:
            return self.end_addr - self.start_addr + 1
        return 0


def parse_fa0080_table(table_bytes: bytes) -> Tuple[List[Fa0080Slot], List[str]]:
    """Parse a 9,216-byte (64 x 144 B) 0xfa0080 cold-boot descriptor table."""
    errors: List[str] = []
    if len(table_bytes) != FA0080_TOTAL_BYTES:
        return [], [f"Invalid 0xfa0080 descriptor table size: {len(table_bytes)} (expected {FA0080_TOTAL_BYTES})"]

    slots: List[Fa0080Slot] = []
    for i in range(FA0080_SLOT_COUNT):
        off = i * FA0080_SLOT_STRIDE
        start_addr, end_addr, part, mode = struct.unpack_from("<QQII", table_bytes, off)
        raw_path = table_bytes[off + 0x18 : off + 0x90]
        nul = raw_path.find(b"\x00")
        path_bytes = raw_path[:nul] if nul != -1 else raw_path
        path_str = path_bytes.decode("ascii", errors="replace")
        if start_addr == 0 and end_addr == 0 and part == 0 and not path_str:
            continue
        if end_addr < start_addr:
            errors.append(
                f"Slot [{i}] ({path_str!r}) has end_addr {hex(end_addr)} < start_addr {hex(start_addr)}"
            )
        if not (1 <= part <= 30):
            errors.append(f"Slot [{i}] ({path_str!r}) references invalid eMMC partition {part}")
        slots.append(
            Fa0080Slot(
                slot_index=i,
                start_addr=start_addr,
                end_addr=end_addr,
                partition=part,
                mode=mode,
                path=path_str,
            )
        )
    return slots, errors


def verify_bksb_ldr_bkup(data: bytes) -> Dict[str, object]:
    """Validate Octal-SPI NOR LdrBkup.bin ('BKSB' @ 0xFE048800, 65 loader keys)."""
    errors: List[str] = []
    if len(data) < 8:
        return {"valid": False, "errors": ["LdrBkup.bin smaller than 8-byte BKSB header"]}
    magic, count = struct.unpack_from("<II", data, 0)
    if magic != BKSB_MAGIC:
        errors.append(f"Invalid LdrBkup.bin magic {hex(magic)} (expected 0x42534b42 'BKSB')")
    if 8 + count * 12 > len(data):
        errors.append(f"BKSB key count {count} exceeds buffer length {len(data)}")
        return {"valid": False, "magic_ok": magic == BKSB_MAGIC, "key_count": count, "errors": errors}

    keys: List[Dict[str, int]] = []
    for i in range(count):
        k, val_off, val_size = struct.unpack_from("<III", data, 8 + i * 12)
        if val_off + val_size > len(data):
            errors.append(f"Key {hex(k)} value span [{val_off}..{val_off + val_size}) exceeds buffer size {len(data)}")
        keys.append({"key": hex(k), "offset": val_off, "size": val_size})

    return {
        "valid": len(errors) == 0,
        "magic_ok": magic == BKSB_MAGIC,
        "key_count": count,
        "keys": keys,
        "errors": errors,
    }


def verify_boot_screen_enum_contract(
    key_02cf0214: bytes,
    key_02cf0218: bytes,
    target_appfw: str = "FX6_601",
) -> Dict[str, object]:
    """Verify Backup keys 0x02cf0214 and 0x02cf0218 against FX6 set_model_for_boot_screen() contract."""
    errors: List[str] = []
    warnings: List[str] = []

    def _decode_val(raw: bytes) -> int:
        if len(raw) == 1:
            return raw[0]
        if len(raw) == 4:
            return struct.unpack("<I", raw)[0]
        return int.from_bytes(raw, "little")

    v214 = _decode_val(key_02cf0214) if key_02cf0214 else -1
    v218 = _decode_val(key_02cf0218) if key_02cf0218 else -1

    if target_appfw == "FX6_601":
        if v214 not in (0, 1):
            errors.append(
                f"Backup key 0x02cf0214 value {hex(v214)} ({key_02cf0214.hex()}) violates FX6 set_model_for_boot_screen() "
                "contract {0, 1} -> will trigger C++ assert at model_api.cpp:3147"
            )
        if v218 not in (0, 1):
            errors.append(
                f"Backup key 0x02cf0218 value {hex(v218)} ({key_02cf0218.hex()}) violates FX6 set_model_for_boot_screen() "
                "contract {0, 1} -> will trigger C++ assert at model_api.cpp:3176"
            )
    else:
        if key_02cf0214 == b"\x16\x16\x16\x16" or key_02cf0218 == b"\x19\x19\x19\x19":
            warnings.append(
                "FX3 4-byte pattern (16161616 / 19191919) present on 0x02cf0214/0x02cf0218: valid on native FX3, "
                "but must be normalized to {0, 1} before booting FX6 appFw.so"
            )

    return {
        "valid": len(errors) == 0,
        "target_appfw": target_appfw,
        "key_02cf0214_hex": key_02cf0214.hex(),
        "key_02cf0218_hex": key_02cf0218.hex(),
        "errors": errors,
        "warnings": warnings,
    }
