#!/usr/bin/env python3
"""Read-only FX6 native UI init inspection. No firmware content is written.

Requires pyelftools and capstone. Inputs must be supplied by the operator (BYOF).
"""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile


def digest(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def member(path, wanted):
    # One newc archive only. Deliberately does not cross TRAILER!!! into an
    # appended archive; the coordinator separately checks complete containers.
    with path.open("rb") as f:
        while True:
            header = f.read(110)
            if len(header) != 110 or header[:6] not in (b"070701", b"070702"):
                raise ValueError("invalid newc header")
            size, namesize = int(header[54:62], 16), int(header[94:102], 16)
            if not 0 < namesize < 65536:
                raise ValueError("invalid member name")
            name = f.read(namesize).rstrip(b"\0").decode()
            f.seek((-f.tell()) % 4, 1)
            if name.removeprefix("./") == wanted:
                data = f.read(size)
                if len(data) != size:
                    raise ValueError("truncated member")
                return data
            if name == "TRAILER!!!":
                raise KeyError(wanted)
            f.seek(size, 1)
            f.seek((-f.tell()) % 4, 1)


class Elf:
    def __init__(self, data):
        self.data = data
        self.elf = ELFFile(io.BytesIO(data))
        self.symbols = list(self.elf.get_section_by_name(".dynsym").iter_symbols())
        rel = self.elf.get_section_by_name(".rela.plt")
        plt = self.elf.get_section_by_name(".plt")
        self.plt = {}
        if rel is not None and plt is not None:
            self.plt = {
                plt.header.sh_addr + 32 + i * 16: self.symbols[r.entry.r_info_sym].name
                for i, r in enumerate(rel.iter_relocations())
            }

    def read(self, address, size):
        for seg in self.elf.iter_segments():
            h = seg.header
            if h.p_type == "PT_LOAD" and h.p_vaddr <= address and address + size <= h.p_vaddr + h.p_filesz:
                offset = h.p_offset + address - h.p_vaddr
                return self.data[offset:offset + size]
        raise ValueError(f"unbacked VMA {address:#x}+{size:#x}")

    def string(self, address):
        return self.read(address, 128).split(b"\0", 1)[0].decode(errors="replace")

    def calls(self, address, size):
        result = []
        for instruction in Cs(CS_ARCH_ARM64, CS_MODE_ARM).disasm(self.read(address, size), address):
            if instruction.mnemonic in ("bl", "b") and instruction.op_str.startswith("#0x"):
                target = int(instruction.op_str[1:], 16)
                result.append({"site": hex(instruction.address), "target": hex(target),
                               "symbol": self.plt.get(target)})
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--appfw", type=Path, required=True)
    parser.add_argument("--cpio", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--serial", type=Path)
    args = parser.parse_args()
    donor = args.appfw.read_bytes()
    packed = member(args.cpio, "usr/lib/appFw.so")
    if digest(donor)["sha256"] != "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067":
        raise ValueError("this address map only applies to the verified 50.5 MB FX6 donor")
    elf = Elf(donor)
    shim = member(args.cpio, "usr/lib/libgrm-fbinit9.so")
    utm = member(args.cpio, "usr/lib/libosal_utm.so")
    result = {"donor": digest(donor), "packed_appfw": digest(packed),
              "packed_matches_donor": packed == donor,
              "packed_fbinit9": digest(shim), "packed_osal_utm": digest(utm),
              "application_init_calls": elf.calls(0xc0b044, 0xe8),
              "ui_worker_calls": elf.calls(0xc0b470, 0xd8),
              "thread_creation_calls": elf.calls(0x222dc1c, 0x13c),
              "thread_trampoline_calls": elf.calls(0x222dbc0, 0x5c),
              "ui_worker_pointer_at_0x2ef00e8": hex(struct.unpack("<Q", elf.read(0x2ef00e8, 8))[0])}
    name, priority, cpu, flags = struct.unpack("<QiiB", elf.read(0x2d196f0, 17))
    result["thread_type_zero_template"] = {"name": elf.string(name), "priority": priority,
                                            "cpu": cpu, "flags": flags}
    base, count, descriptors = struct.unpack("<Qi4xQ", elf.read(0x2ef2b88, 24))
    arenas = []
    for i in range(count):
        name, size, minblock, maxblock, flags = struct.unpack("<QQIIB", elf.read(descriptors + 32 * i, 25))
        arenas.append({"name": elf.string(name), "bytes": size,
                       "field_0x10": minblock, "field_0x14": maxblock, "field_0x18": flags})
    result["arenas"] = arenas
    result["total_arena_bytes"] = sum(a["bytes"] for a in arenas)
    result["source"] = digest(args.source.read_bytes()) if args.source else None
    if args.serial:
        serial = args.serial.read_bytes()
        result["serial"] = digest(serial)
        text = serial.decode(errors="replace")
        result["init_markers"] = [line.strip() for line in text.splitlines()
                                  if "FX6_APP_CONFIG_" in line or "FX6_OSAL_" in line]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
