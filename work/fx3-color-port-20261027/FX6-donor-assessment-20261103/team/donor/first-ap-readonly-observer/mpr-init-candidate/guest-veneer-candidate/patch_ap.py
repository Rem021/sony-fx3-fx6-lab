"""Make a separate FX6 AP copy with two unique bridge imports and one DT_NEEDED.

This is an in-place ELF metadata patch of the *copy*: no segment, section size,
load address, executable instruction, old dependency, or relocation is changed.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
DONOR = HERE.parents[2]
SOURCE = DONOR / "nflasha15-files/lib/appFw.so"
OUTPUT = HERE / "appFw-bridge.so"
SOURCE_SHA = "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067"
INIT_OLD = b"_ZN3mpr4InitERKNS_11initInParamE"
ENTER_OLD = b"_ZN3mpr8EnterRecERKNS_15enterRecInParamE"
INIT_NEW = b"fx6diag_mpr_init"
ENTER_NEW = b"fx6diag_mpr_enterrec"
NEEDED = b"libfx6diag.so"
GOT = {INIT_OLD: 0x2ef1368, ENTER_OLD: 0x2ef2670}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def u(data: bytes, fmt: str, off: int):
    return struct.unpack_from("<" + fmt, data, off)


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(f"preserve existing patched AP: {OUTPUT}")
    original = SOURCE.read_bytes()
    if sha(original) != SOURCE_SHA or len(original) != 50520424:
        raise ValueError("FX6 original AP identity drift")
    patched = bytearray(original)
    if original[:6] != b"\x7fELF\x02\x01" or u(original, "H", 18)[0] != 183:
        raise ValueError("not AArch64 ELF64 LE")
    phoff = u(original, "Q", 32)[0]
    phentsize, phnum = u(original, "HH", 54)
    loads = []
    dynamic = None
    for i in range(phnum):
        p = phoff + i * phentsize
        typ = u(original, "I", p)[0]
        off, va, _, filesz, _, _ = u(original, "QQQQQQ", p+8)
        if typ == 1: loads.append((va, va+filesz, off))
        if typ == 2: dynamic = (off, filesz)
    if dynamic is None: raise ValueError("no PT_DYNAMIC")
    def fileoff(va: int) -> int:
        for start, end, off in loads:
            if start <= va < end: return off + va - start
        raise ValueError(f"VA outside PT_LOAD: {va:x}")
    doff, dsize = dynamic
    entries = [u(original, "qQ", doff+i*16) for i in range(dsize//16)]
    first_null = next(i for i, (tag, _) in enumerate(entries) if tag == 0)
    if first_null != 38 or entries[first_null+1] != (0,0):
        raise ValueError("expected two spare DT_NULL entries")
    dt = dict(entries[:first_null])
    if u(original, "4I", fileoff(dt[0x6ffffef5]))[1] != 912:
        raise ValueError("GNU hash symbol offset drift")
    str_off = fileoff(dt[5]); str_len = dt[10]
    sym_off = fileoff(dt[6]); sym_ent = dt[11]
    if sym_ent != 24: raise ValueError("dynsym stride drift")
    strings = original[str_off:str_off+str_len]
    name_offsets = {name: strings.find(name + b"\0") for name in GOT}
    if any(v < 0 or strings.count(name+b"\0") != 1 for name,v in name_offsets.items()):
        raise ValueError("old undefined names not unique")
    # The two undefined entries predate GNU hash symoffset and have no aliasing st_name.
    expected_indices = {INIT_OLD: 124, ENTER_OLD: 795}
    for name, idx in expected_indices.items():
        if u(original, "I", sym_off+idx*sym_ent)[0] != name_offsets[name]:
            raise ValueError("old dynsym name mismatch")
        if u(original, "H", sym_off+idx*sym_ent+6)[0] != 0:
            raise ValueError("expected undefined symbol")
        start, end = name_offsets[name], name_offsets[name]+len(name)+1
        for other in range(912):
            if other != idx and start <= u(original, "I", sym_off+other*sym_ent)[0] < end:
                raise ValueError("another dynsym references old string span")
    init_off = name_offsets[INIT_OLD]
    bridge_name_off = init_off + len(INIT_NEW) + 1
    init_replacement = INIT_NEW + b"\0" + NEEDED + b"\0"
    if len(init_replacement) > len(INIT_OLD)+1:
        raise ValueError("bridge name does not fit old Init string slot")
    for old, new in ((INIT_OLD, init_replacement), (ENTER_OLD, ENTER_NEW+b"\0")):
        pos = str_off+name_offsets[old]
        size = len(old)+1
        patched[pos:pos+size] = new.ljust(size, b"\0")
    if any(tag == 1 and name_offsets[INIT_OLD] <= value < name_offsets[INIT_OLD]+len(INIT_OLD)+1
           for tag, value in entries[:first_null]):
        raise ValueError("old dependency aliases Init string span")
    struct.pack_into("<qQ", patched, doff+first_null*16, 1, bridge_name_off)
    # Check the original JUMP_SLOT targets and symbol indices; only names change.
    jmp_off = fileoff(dt[23]); jmp_bytes = dt[2]
    if jmp_bytes % 24: raise ValueError("RELA PLT stride")
    for name, got in GOT.items():
        found = [(off, info) for i in range(jmp_bytes//24)
                 for off, info, _ in [u(original,"QQq",jmp_off+i*24)] if off == got]
        if len(found) != 1 or found[0][1] & 0xffffffff != 1026 or found[0][1] >> 32 != expected_indices[name]:
            raise ValueError(f"JUMP_SLOT drift {name!r}")
    diffs = []
    for i, (a,b) in enumerate(zip(original,patched)):
        if a != b: diffs.append(i)
    allowed = (set(range(str_off+init_off, str_off+init_off+len(INIT_OLD)+1)) |
               set(range(str_off+name_offsets[ENTER_OLD], str_off+name_offsets[ENTER_OLD]+len(ENTER_OLD)+1)) |
               set(range(doff+first_null*16, doff+(first_null+1)*16)))
    if not diffs or any(i not in allowed for i in diffs):
        raise ValueError("unexpected ELF byte change")
    OUTPUT.write_bytes(patched)
    report = {"source": str(SOURCE), "source_sha256": SOURCE_SHA,
              "patched_sha256": sha(patched), "size": len(patched),
              "patched_ranges": [{"offset": str_off+init_off, "length": len(INIT_OLD)+1, "meaning": "Init unique symbol + bridge DT_NEEDED name"},
                                 {"offset": str_off+name_offsets[ENTER_OLD], "length": len(ENTER_OLD)+1, "meaning": "EnterRec unique symbol"},
                                 {"offset": doff+first_null*16, "length": 16, "meaning": "spare DT_NULL to DT_NEEDED"}],
              "bytes_changed": len(diffs), "gnu_hash_symoffset": 912,
              "dynsym_indices": {"Init": 124, "EnterRec": 795},
              "unchanged_jump_slots": {k.decode(): hex(v) for k,v in GOT.items()},
              "new_needed": NEEDED.decode(), "new_symbols": [INIT_NEW.decode(),ENTER_NEW.decode()]}
    (HERE / "ap-patch.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k:report[k] for k in ("patched_sha256","bytes_changed","new_needed")},indent=2))


if __name__ == "__main__": main()
