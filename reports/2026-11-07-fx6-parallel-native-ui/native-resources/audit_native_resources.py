#!/usr/bin/env python3
"""Read-only BYOF audit of FX6 UI identities and descriptor-table bindings.

Only structural metadata is printed; no firmware or resource payload is emitted.
Uses Python's standard library. Unknown firmware hashes fail closed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

FX6_SHA = "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067"
REFERENCE_SHA = "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f"
OLD_TABLES = [0x451AB28, 0x44AF468, 0x452AC48, 0x44C0978, 0x44C20D8]
SCREENS = [
    ("procam_big6_menu_home_presenter", 0xDE10F4, 0xDE1228, 0x2EE57B8, 0x2E9E210, 98, 0xDE11DC),
    ("procam_shooting_presenter", 0xDD3DF8, 0xDD3F88, 0x2EEE798, 0x2E94910, 356, 0xDD3F3C),
    ("procam_menu_layer_1st_presenter", 0xDD7470, 0xDD7588, 0x2EEC5A0, 0x2EA02F8, 35, 0xDD7548),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ELF:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        if self.data[:6] != b"\x7fELF\x02\x01":
            raise ValueError("Expected little-endian ELF64")
        h = struct.unpack_from("<HHIQQQIHHHHHH", self.data, 16)
        if h[1] != 183:
            raise ValueError("Expected AArch64 ELF")
        self.loads = []
        for i in range(h[9]):
            p = struct.unpack_from("<IIQQQQQQ", self.data, h[4] + i*h[8])
            if p[0] == 1:
                self.loads.append(dict(offset=p[2], vaddr=p[3], filesz=p[5], memsz=p[6]))
        self.sections = []
        for i in range(h[11]):
            s = struct.unpack_from("<IIQQQQIIQQ", self.data, h[5]+i*h[10])
            self.sections.append(s)
        self.relocations = {}
        for s in self.sections:
            if s[1] == 4:  # SHT_RELA
                for off in range(s[4], s[4]+s[5], s[9]):
                    target, info, addend = struct.unpack_from("<QQq", self.data, off)
                    if info & 0xffffffff == 1027:  # R_AARCH64_RELATIVE
                        self.relocations[target] = addend

    def storage(self, addr):
        for p in self.loads:
            if p["vaddr"] <= addr < p["vaddr"]+p["filesz"]:
                return "file-backed"
            if p["vaddr"]+p["filesz"] <= addr < p["vaddr"]+p["memsz"]:
                return "zero-fill/BSS"
        return "unmapped"

    def offset(self, addr):
        for p in self.loads:
            if p["vaddr"] <= addr < p["vaddr"]+p["filesz"]:
                return p["offset"] + addr-p["vaddr"]
        raise ValueError(f"VMA {addr:#x} has no file bytes")

    def u64(self, addr):
        return struct.unpack_from("<Q", self.data, self.offset(addr))[0]

    def u32(self, addr):
        return struct.unpack_from("<I", self.data, self.offset(addr))[0]

    def string(self, addr):
        off = self.offset(addr)
        end = self.data.index(b"\0", off, off+256)
        return self.data[off:end].decode("ascii")

    def identity(self):
        return {"path": str(self.path), "bytes": len(self.data), "sha256": sha(self.data)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fx6", required=True, type=Path, help="Untouched FX6 appFw.so")
    ap.add_argument("--reference", type=Path, help="Optional FX3 79 MB appFw.so")
    ap.add_argument("--app-dir", required=True, type=Path, help="FX6 usr/share/app directory")
    args = ap.parse_args()
    fx6 = ELF(args.fx6)
    if sha(fx6.data) != FX6_SHA:
        raise ValueError("FX6 SHA mismatch; VMA assertions apply only to the pinned donor")
    result = {"fx6": fx6.identity(), "old_documented_tables": [
        {"vma": hex(a), "fx6_storage": fx6.storage(a)} for a in OLD_TABLES
    ], "screens": []}
    for name, ctor, xref, got, table, count, count_pc in SCREENS:
        if fx6.u32(ctor) != 0xA9BC7BFD:  # stp x29,x30,[sp,#-0x40]!
            raise ValueError(f"{name}: constructor prologue mismatch")
        adrp, add = fx6.u32(xref), fx6.u32(xref+8)
        if adrp & 0x9F00001F != 0x90000002 or add & 0xFFC003FF != 0x91000042:
            raise ValueError(f"{name}: constructor-name ADRP/ADD mismatch")
        imm = ((adrp >> 29) & 3) | (((adrp >> 5) & 0x7ffff) << 2)
        if imm & (1 << 20):
            imm -= 1 << 21
        name_vma = (xref & ~4095)+(imm << 12)+((add >> 10) & 0xfff)
        if not fx6.string(name_vma).startswith(f"{name}::{name}("):
            raise ValueError(f"{name}: constructor name mismatch")
        if fx6.u32(count_pc) != 0xD2800003 | (count << 5):
            raise ValueError(f"{name}: mov x3,#descriptor_count mismatch")
        if fx6.relocations.get(got) != table:
            raise ValueError(f"{name}: table relocation mismatch")
        names = [fx6.string(fx6.u64(table+i*0x48+8)) for i in range(count)]
        if not all(n.startswith("No") for n in names):
            raise ValueError(f"{name}: invalid descriptor names")
        result["screens"].append({"name": name, "constructor_vma": hex(ctor),
            "constructor_assert_name_adrp_vma": hex(xref), "constructor_name_vma": hex(name_vma),
            "count_instruction_vma": hex(count_pc), "table_got_vma": hex(got),
            "table_vma": hex(table), "count": count, "stride": "0x48",
            "validated_name_records": len(names), "first_names": names[:3],
            "last_names": names[-3:], "name_sequence_sha256": sha("\n".join(names).encode())})
    result["legacy_name_presence_in_fx6"] = {
        n: fx6.data.find(n.encode()) >= 0 for n in
        ["scr7286_0001", "No113_SelectButton", "rep_menu", "rep_shooting_presenter"]}
    if args.reference:
        ref = ELF(args.reference)
        if sha(ref.data) != REFERENCE_SHA:
            raise ValueError("Reference SHA mismatch")
        result["reference"] = ref.identity()
        result["reference_legacy_name_presence"] = {
            n: ref.data.find(n.encode()) >= 0 for n in result["legacy_name_presence_in_fx6"]}
    resource_names = set()
    for src in ["global.xdb", "fontlist.dat"]:
        data = (args.app_dir/src).read_bytes()
        for raw in re.findall(rb"[ -~]{5,}", data):
            value = raw.decode()
            if re.search(r"\.(?:uxc|uxb|ltt|ttf)$", value):
                resource_names.add(Path(value).name)
    resources = []
    for name in sorted(resource_names | {"global.xdb", "fontlist.dat", "lang.uxb"}):
        p = args.app_dir/name
        resources.append({"name": name, "exists": p.is_file(),
            **({"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} if p.is_file() else {})})
    result["resources"] = resources
    result["resource_closure_missing"] = [r["name"] for r in resources if not r["exists"]]
    result["boundary"] = "Static donor identity/descriptor/resource audit only; no guest execution or screen opening proved."
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
