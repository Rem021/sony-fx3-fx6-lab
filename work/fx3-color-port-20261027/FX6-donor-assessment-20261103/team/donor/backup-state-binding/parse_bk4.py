#!/usr/bin/env python3
"""Bounded, read-only BK4 parser for pinned public default Backup files."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
DONOR = Path(__file__).resolve().parents[1]
TARGET = 0x02AE0000
SOURCES = {
    "fx6_chaplin_ntsc": (DONOR / "tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin", "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e"),
    "fx6_chaplin_j": (DONOR / "tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_J.bin", "eb7933185eda7019e20cf8bb33c27c6cffee683767fd6d6bcdd472592ae01333"),
    "fx6_chaplin_uc": (DONOR / "tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_UC.bin", "ec67687d1e2dc39775614cb7ac61a809fb2d8e6f06ebbdd20cf708b33803653c"),
    "fx6_chaplin_cee": (DONOR / "tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95899_CEE.bin", "031ba95604e891c79406acebd86e4fc8835ccd7200942c14c79a0309b27d1173"),
    "fx6_chaplin_cn1": (DONOR / "tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95899_CN1.bin", "0c98d1ad9035f0f56a60462efe0d0440c6b29d5584fd3f1e8ffd6a59366f0a28"),
    "fx3_official_seed": (ROOT / "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin", "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"),
}


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def read_record(data: bytes, base: int, target: int = TARGET, require_checksum: bool = True) -> tuple[dict, int]:
    if base < 0 or base + 256 > len(data):
        raise ValueError("record header outside file")
    magic, cookie, write, rev, ns, np, start, size, checksum = struct.unpack_from("<III4s5I", data, base)
    end = base + start + size
    if rev != b"BK4\0" or not (0 < ns < 65536 and 0 < np < 1 << 24):
        raise ValueError("invalid BK4 header")
    if 256 + 6 * (ns + np) > start or end > len(data):
        raise ValueError("invalid BK4 table/data bounds")
    check = sum(data[base:base + 32]) + sum(data[base + 36:end])
    if check != checksum and require_checksum:
        raise ValueError("BK4 checksum mismatch")
    subs = []
    for i in range(ns):
        count, index = struct.unpack_from("<HI", data, base + 256 + 6 * i)
        if index + count > np:
            raise ValueError("subsystem index overflow")
        subs.append((count, index))
    props = []
    for i in range(np):
        table = base + 256 + 6 * ns + 6 * i
        attr, ptr = struct.unpack_from("<HI", data, table)
        if ptr == 0xFFFFFFFF:
            props.append(None)
            continue
        length, offset = ptr >> 24, ptr & 0xFFFFFF
        if not (start <= offset < start + size):
            raise ValueError("property offset outside data")
        prefix = 0
        if length == 255:
            if offset + 2 > start + size:
                raise ValueError("large property length prefix overflow")
            length = maximum = u16(data, base + offset)
            prefix = 2
        elif length == 0:
            if offset + 4 > start + size:
                raise ValueError("variable property length prefix overflow")
            length, maximum = struct.unpack_from("<HH", data, base + offset)
            prefix = 4
        else:
            maximum = length
        if length > maximum or offset + prefix + maximum > start + size:
            raise ValueError("property data overflow")
        props.append({"attribute": attr, "encoded_pointer": ptr, "length": length, "max_length": maximum, "table_file_offset": table, "prefix_file_offset": base + offset, "data_file_offset": base + offset + prefix, "prefix_bytes": prefix})
    subsystem, unit = target >> 16, target & 0xFFFF
    if subsystem >= ns:
        selected = {"present": False, "reason": "subsystem out of bounds"}
    elif unit >= subs[subsystem][0]:
        selected = {"present": False, "reason": "unit out of bounds", "subsystem_count": subs[subsystem][0]}
    else:
        ix = subs[subsystem][1] + unit
        p = props[ix]
        if p is None:
            selected = {"present": False, "reason": "invalid pointer sentinel", "property_index": ix}
        else:
            raw = data[p["data_file_offset"]:p["data_file_offset"] + p["length"]]
            selected = {"present": True, "property_index": ix, **p, "raw_hex": raw.hex(), "raw_sha256": hashlib.sha256(raw).hexdigest()}
            if len(raw) == 4:
                selected["u32_le"] = struct.unpack("<I", raw)[0]
    return {"record_file_offset": base, "record_bytes": start + size, "subsystem_count": ns, "property_count": np, "data_relative_offset": start, "data_bytes": size, "checksum_stored": checksum, "checksum_computed": check, "checksum_matches":check==checksum, "all_entry_bounds_checked": True, "id": f"0x{target:08x}", "selected": selected}, end


def parse_file(path: Path, expected_sha: str, target: int = TARGET) -> dict:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha:
        raise ValueError(f"SHA mismatch for {path}: {digest}")
    records = []
    pos = 0
    while pos < len(data):
        record, end = read_record(data, pos, target)
        records.append(record)
        pos = (end + 4095) & ~4095
        if pos >= len(data):
            if end != len(data) and any(data[end:]):
                raise ValueError("nonzero tail padding")
            break
        if any(data[end:pos]):
            raise ValueError("nonzero inter-record padding")
    return {"path": str(path), "sha256": digest, "size": len(data), "records": records}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=lambda s: int(s, 0), default=TARGET)
    args = ap.parse_args()
    dest = DONOR / "tree/0110_backup/MainDest.txt"
    dest_blob = dest.read_bytes()
    dest_sha = hashlib.sha256(dest_blob).hexdigest()
    if dest_sha != "51bc347fed1435a0afb93b4e694722aceea809751bd7748482432650bebd98f2":
        raise ValueError("MainDest SHA mismatch")
    result = {"scope": "pinned public default templates and offline FX3 seed only; no runtime current body", "target": f"0x{args.target:08x}", "fx6_main_dest": {"path":str(dest),"sha256":dest_sha,"text":dest_blob.decode()}, "sources": {name: parse_file(path, digest, args.target) for name, (path, digest) in SOURCES.items()}}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
