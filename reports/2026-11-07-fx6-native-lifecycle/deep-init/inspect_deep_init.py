#!/usr/bin/env python3
"""Read-only log/member/lifecycle inspection; writes no firmware bytes.

Requires pyelftools and capstone. CPIO reader intentionally covers first newc
archive only; the coordinator's full-container checker covers appended archives.
"""
import argparse
import hashlib
import io
import json
import re
import struct
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile


def sha(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def member(path, wanted):
    with path.open("rb") as f:
        while True:
            header = f.read(110)
            if len(header) != 110 or header[:6] not in (b"070701", b"070702"):
                raise ValueError("invalid newc header")
            size, ns = int(header[54:62], 16), int(header[94:102], 16)
            if not 0 < ns < 65536:
                raise ValueError("invalid member name length")
            name = f.read(ns).rstrip(b"\0").decode()
            f.seek((-f.tell()) % 4, 1)
            if name.removeprefix("./") == wanted:
                result = f.read(size)
                if len(result) != size:
                    raise ValueError("truncated member")
                return result
            if name == "TRAILER!!!":
                raise KeyError(wanted)
            f.seek(size, 1)
            f.seek((-f.tell()) % 4, 1)


class Elf:
    def __init__(self, data):
        self.data = data
        self.e = ELFFile(io.BytesIO(data))
        self.symbols = list(self.e.get_section_by_name(".dynsym").iter_symbols())
        rel, plt = self.e.get_section_by_name(".rela.plt"), self.e.get_section_by_name(".plt")
        self.plt = {plt.header.sh_addr + 32 + i * 16: self.symbols[r.entry.r_info_sym].name
                    for i, r in enumerate(rel.iter_relocations())} if rel and plt else {}

    def read(self, address, size):
        for segment in self.e.iter_segments():
            h = segment.header
            if h.p_type == "PT_LOAD" and h.p_vaddr <= address and address + size <= h.p_vaddr + h.p_filesz:
                offset = h.p_offset + address - h.p_vaddr
                return self.data[offset:offset + size]
        raise ValueError(f"unbacked address {address:#x}+{size:#x}")

    def calls(self, address, size):
        calls = []
        for ins in Cs(CS_ARCH_ARM64, CS_MODE_ARM).disasm(self.read(address, size), address):
            if ins.mnemonic in ("bl", "b") and ins.op_str.startswith("#0x"):
                target = int(ins.op_str[1:], 16)
                calls.append({"site": hex(ins.address), "target": hex(target), "symbol": self.plt.get(target)})
        return calls


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--agnostic", type=Path, required=True)
    p.add_argument("--donor-lib", type=Path, required=True)
    args = p.parse_args()
    report = {"runs": [], "members": [], "sources": {}}
    for run in ("cp-bind-9a736b1c", "cp-bind-93fb917b", "cp-bind-8d4a255b"):
        rd = args.agnostic / "runs" / run
        command = json.loads((rd / "command.json").read_text())
        raw = (rd / "serial.log").read_bytes()
        lines = raw.decode(errors="replace").splitlines()
        keys = ("FX6_APP_CONFIG_", "FX6_GRM_FBRM_CB_FIRE", "FX6_UX_SCREEN_AREA_1024", "mpMemoryHeap", "mpTextHeap", "APPFW_SEGV", "APPFW_PC_MODULE", "APPFW_LR_MODULE")
        report["runs"].append({"run": run, "candidate": command.get("candidate"), "serial": sha(raw),
                               "evidence": [{"line": i, "text": ln.strip()} for i, ln in enumerate(lines, 1)
                                            if any(key in ln for key in keys)]})
    for name in ("guest-hybrid-fx6kernel-capid-grmreal288-fast-init.cpio", "guest-hybrid-fx6kernel-capid-grmreal289-native.cpio", "guest-hybrid-fx6kernel-capid-grmreal290-upm.cpio"):
        path = args.agnostic / name
        report["members"].append({"cpio": name, "payloads": {
            item: sha(member(path, item)) for item in
            ("usr/lib/libMWF.so", "usr/lib/libgrm-fbinit9.so", "usr/lib/appFw.so", "usr/bin/appfw-launch")}})
    mwf = Elf(member(args.agnostic / "guest-hybrid-fx6kernel-capid-grmreal290-upm.cpio", "usr/lib/libMWF.so"))
    if sha(mwf.data)["sha256"] != "3c9666c49bde90076cf69af13295dc07e585d87c51a27ecaf7f1926df87d1782":
        raise ValueError("libMWF address map mismatch")
    report["mwf"] = {"init_array": [hex(v) for v in struct.unpack("<Q", mwf.e.get_section_by_name(".init_array").data())],
                     "getflag_instruction": next(Cs(CS_ARCH_ARM64, CS_MODE_ARM).disasm(mwf.read(0x3e908, 4), 0x3e908)).op_str,
                     "initialize_calls": mwf.calls(0x27d68, 164),
                     "rsrc_mcmd_calls": mwf.calls(0x393b4, 44),
                     "rsrcdp_initialize_calls": mwf.calls(0x38cb0, 528),
                     "rsrcdp_myprintf_calls": mwf.calls(0x38ec0, 236)}
    report["mwf"]["error_pointer_got_relocation"] = [dict(r.entry) | {"symbol": mwf.symbols[r.entry.r_info_sym].name}
        for r in mwf.e.get_section_by_name(".rela.dyn").iter_relocations() if r.entry.r_offset == 0x63f08]
    imdb_data = (args.donor_lib / "libIMDB.so").read_bytes()
    imdb = Elf(imdb_data)
    report["fx6_donor_imdb"] = sha(imdb_data) | {
        "module_at_0x1f280": hex(struct.unpack("<Q", imdb.read(0x1f280, 8))[0]),
        "init_at_0x1f288": hex(struct.unpack("<Q", imdb.read(0x1f288, 8))[0]),
        "module_string": imdb.read(0xaadb, 10).rstrip(b"\0").decode(),
        "init_string": imdb.read(0xaae5, 9).rstrip(b"\0").decode()}
    for name in ("appfw-launch288.c", "libgrm-fbinit25-289.c", "observe_mwf_lifecycle.c"):
        report["sources"][name] = sha(Path(__file__).with_name(name).read_bytes())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
