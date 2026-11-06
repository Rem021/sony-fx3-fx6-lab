#!/usr/bin/env python3
"""Read-only, pinned FX6 Base ISO static-edge audit. No device or binary execution."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

EXPECTED_SHA256 = "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067"
MODEL_ID = 0x3662
TABLE_BASE = 0x29C7668

# ARM64 little-endian instruction words, independently inspectable with llvm-objdump.
CHECKS = {
    0x1A68344: ("a9b97bfd", "producer function prologue"),
    0x1A6836C: ("97e9d74f", "enum-pointer getter call"),
    0x1A68370: ("b9400001", "enum read [x0] into w1"),
    0x1A68384: ("38614800", "jump-table byte read"),
    0x1A68390: ("d61f0000", "enum branch"),
    0x1A683A8: ("5286cc40", "model ID 0x3662"),
    0x1A683B8: ("52864001", "w1 = 12800"),
    0x1A683C8: ("97ffffc2", "model setter call 0x1a682d0"),
    0x1A683D0: ("97f9204c", "dirty notification call 0x18b0500"),
    0x1A683F0: ("d65f03c0", "producer function return"),
    0x1A68408: ("5286cc40", "model ID 0x3662"),
    0x1A68410: ("5281f401", "w1 = 4000"),
    0x1A68444: ("52806401", "w1 = 800"),
    0x1A6845C: ("d0005662", "diagnostic branch begins"),
    0x1A68470: ("941bfcc5", "diagnostic logger call"),
    0x1A682E0: ("2a0103f4", "setter saves value in w20"),
    0x1A682E4: ("b9401001", "setter reads model ID at +0x10"),
    0x1A6830C: ("b9000014", "setter writes w20 to nested value"),
    0x1A6831C: ("b9000014", "setter writes w20 to primary value"),
    0x1A68324: ("39005260", "setter sets dirty flag at +0x14"),
    0x18B0500: ("39405001", "notification checks dirty flag"),
    0x18B0528: ("b9401000", "notification loads model ID"),
    0x18B052C: ("17e21053", "tail branch to 0x1134678"),
    0x113469C: ("97ff0849", "runtime registry lookup"),
    0x11346A0: ("b40002c0", "lookup miss branch"),
    0x11346AC: ("94100a79", "ID-indexed getter dispatch"),
    0x11346CC: ("b9400660", "runtime successor ID read [x19+4]"),
    0x11346D4: ("94100a7d", "successor setter dispatch"),
    0x11346FC: ("94100a57", "lookup miss indexed predicate"),
    0x1134730: ("97ff04d6", "lookup miss dirty-bit path"),
    0x15370A4: ("f9401000", "getter slot +0x20"),
    0x15370A8: ("d61f0000", "indexed branch through getter"),
    0x15370DC: ("f9400802", "setter slot +0x10"),
    0x15370E4: ("d61f0040", "indexed branch through setter"),
    0x1451E94: ("b001d400", "resolved Base ISO getter"),
    0x1451E98: ("b942d800", "getter reads global +0x2d8"),
    0x1451E7C: ("d001cac1", "resolved Base ISO setter"),
    0x1451E88: ("b90ca820", "setter writes global +0xca8"),
    0x1451E8C: ("b90cb020", "setter writes global +0xcb0"),
}


def elf_maps(blob):
    if blob[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", blob, 18)[0] != 183:
        raise ValueError("expected ELF64 little-endian AArch64")
    phoff, shoff = struct.unpack_from("<QQ", blob, 32)
    phentsize, phnum, shentsize, shnum = struct.unpack_from("<HHHH", blob, 54)
    loads = []
    for i in range(phnum):
        entry = phoff + i * phentsize
        if struct.unpack_from("<I", blob, entry)[0] == 1:
            offset, vaddr = struct.unpack_from("<QQ", blob, entry + 8)
            filesz = struct.unpack_from("<Q", blob, entry + 32)[0]
            loads.append((offset, vaddr, filesz))
    relas = []
    for i in range(shnum):
        entry = shoff + i * shentsize
        section_type = struct.unpack_from("<I", blob, entry + 4)[0]
        if section_type == 4:  # SHT_RELA
            offset, size = struct.unpack_from("<QQ", blob, entry + 24)
            entsize = struct.unpack_from("<Q", blob, entry + 56)[0]
            if entsize < 24:
                raise ValueError("invalid RELA entry size")
            relas.append((offset, size, entsize))
    return loads, relas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("appfw", type=Path, help="local original FX6 appFw.so")
    args = parser.parse_args()
    blob = args.appfw.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"REJECT original SHA256 mismatch: {digest}")
    loads, relas = elf_maps(blob)

    def read_va(va, size):
        for offset, vaddr, filesz in loads:
            if vaddr <= va and va + size <= vaddr + filesz:
                fileoff = offset + va - vaddr
                return fileoff, blob[fileoff:fileoff + size]
        raise ValueError(f"VA 0x{va:x} not file-backed")

    instructions = []
    for va, (expected, meaning) in CHECKS.items():
        fileoff, raw = read_va(va, 4)
        if raw.hex() != bytes.fromhex(expected)[::-1].hex():
            raise ValueError(f"instruction mismatch at VA 0x{va:x}: {raw.hex()}")
        instructions.append({"va": f"0x{va:x}", "file_offset": f"0x{fileoff:x}",
                             "raw_le": raw.hex(), "word": expected, "meaning": meaning})

    _, switch = read_va(0x2535DAC, 5)
    if switch != bytes.fromhex("2500101825"):
        raise ValueError("Base ISO enum jump table changed")
    switch_map = {str(i): f"0x{0x1A68394 + struct.unpack('b', bytes([b]))[0] * 4:x}"
                  for i, b in enumerate(switch)}

    slots = []
    for slot in (0, 0x10, 0x20):
        va = TABLE_BASE + MODEL_ID * 0x30 + slot
        fileoff, raw = read_va(va, 8)
        target = int.from_bytes(raw, "little")
        slots.append({"slot": f"+0x{slot:x}", "va": f"0x{va:x}",
                      "file_offset": f"0x{fileoff:x}", "raw_le": raw.hex(),
                      "pre_relocation_target": f"0x{target:x}"})
    if [int(s["pre_relocation_target"], 16) for s in slots] != [0x1476CDC, 0x1451E7C, 0x1451E94]:
        raise ValueError("model 0x3662 dispatch slots changed")

    slot_vas = {int(s["va"], 16) for s in slots}
    found_relas = {}
    for off, size, entsize in relas:
        for pos in range(off, off + size, entsize):
            r_offset, r_info, r_addend = struct.unpack_from("<QQq", blob, pos)
            if r_offset in slot_vas:
                found_relas[r_offset] = {"type": r_info & 0xffffffff, "addend": r_addend}
    for slot in slots:
        va = int(slot["va"], 16)
        rela = found_relas.get(va)
        if rela is None or rela["type"] != 1027 or rela["addend"] != int(slot["pre_relocation_target"], 16):
            raise ValueError(f"slot relocation mismatch at 0x{va:x}")
        slot["relocation"] = "R_AARCH64_RELATIVE"

    string_va = 0x25364F8
    _, trailing = read_va(string_va, 100)
    diagnostic = trailing.split(b"\0", 1)[0].decode("ascii")
    if diagnostic != "static void model::model_extern::extern_BKID_APP_EXTERN_BASE_ISO()":
        raise ValueError("diagnostic string changed")

    receipt = {
        "source": str(args.appfw.resolve()), "sha256": digest,
        "evidence_level": "FX6 original file static only; no FX3 runtime, VM, cold boot, or camera claim",
        "model_id": f"0x{MODEL_ID:x}", "diagnostic_string_va": f"0x{string_va:x}",
        "diagnostic_string": diagnostic,
        "enum_jump_table_va": "0x2535dac", "enum_jump_table_raw": switch.hex(),
        "enum_case_target": switch_map,
        "model_table_base": f"0x{TABLE_BASE:x}", "slots": slots,
        "global_value_va": "0x4ed22d8", "global_mirror_va": "0x4ed22e0",
        "first_unresolved_runtime_edge": {
            "lookup_call_va": "0x113469c", "conditional_miss_va": "0x11346a0",
            "successor_id_read_va": "0x11346cc", "successor_dispatch_call_va": "0x11346d4",
            "reason": "successor ID is read from runtime registry entry returned by lookup; original file does not fix entry presence or ID"
        },
        "ipc_field_length_consumer": "unknown; no direct IPC boundary established from this edge",
        "instructions": instructions,
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
