#!/usr/bin/env python3
"""Guard the original FX3 libObj call sites used by the v25 passive observer."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6] / "fx3-audit/original-members/nflasha15/lib"
ORIGINAL_SHA = "c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae"
WORDS = {
    0xF2220: 0xF9402400,  # object's +0x48 semaphore pointer, draw path
    0xF2224: 0x94002C48,  # call wait wrapper in original libObj
    0xF2234: 0x14002C54,  # branch to native signal helper
    0xF22C8: 0xF9402660,  # same object's +0x48 on 6005 branch
    0xF22CC: 0x94002C2E,  # call native signal helper
    0xF22F0: 0x79400022,  # receive completion kind
    0xF22F4: 0x528C0063,  # compare 6003
    0xF2300: 0x528C00A3,  # compare 6005
    0xFD354: 0x97FD60C7,  # osal_wai_sem_tmo@plt, original timeout in w1
    0xFD390: 0x97FD6A08,  # osal_sig_sem@plt
}


def elf_sections(data):
    if data[:4] != b"\x7fELF" or data[4:6] != b"\x02\x01":
        raise ValueError("not ELF64 little endian")
    shoff = struct.unpack_from("<Q", data, 0x28)[0]
    entsize, count, names_index = struct.unpack_from("<HHH", data, 0x3A)
    if entsize != 64 or shoff + count * entsize > len(data):
        raise ValueError("invalid section table")
    entries = [struct.unpack_from("<IIQQQQIIQQ", data, shoff + i * entsize) for i in range(count)]
    names = entries[names_index]
    strings = data[names[4]:names[4] + names[5]]
    for item in entries:
        name_end = strings.find(b"\0", item[0])
        name = strings[item[0]:name_end].decode()
        yield name, item


def audit(path):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != ORIGINAL_SHA:
        raise ValueError("original libObj SHA mismatch")
    text = next(item for name, item in elf_sections(data) if name == ".text")
    rows = []
    for address, expected in WORDS.items():
        if not text[3] <= address < text[3] + text[5] - 3:
            raise ValueError("instruction outside original .text")
        offset = text[4] + address - text[3]
        actual = struct.unpack_from("<I", data, offset)[0]
        if actual != expected:
            raise ValueError(f"original instruction changed at {address:#x}: {actual:#x}")
        rows.append({"vma": hex(address), "file_offset": hex(offset),
                     "original_word": f"{actual:08x}"})
    return {"path": str(path), "sha256": digest, "text_vma": hex(text[3]),
            "text_file_offset": hex(text[4]), "instruction_guards": rows,
            "menu_handler_offset": None, "menu_handler_attribution": "unproven"}


if __name__ == "__main__":
    print(json.dumps(audit(ROOT / "libObj.so"), indent=2))
