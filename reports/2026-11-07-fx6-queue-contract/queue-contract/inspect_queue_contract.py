#!/usr/bin/env python3
"""Read-only, BYOF FX6 BB queue-contract inspection (pyelftools/capstone)."""
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


def cpio_member(path, wanted):
    """First newc archive only; full-container validation is a separate check."""
    with path.open("rb") as f:
        while True:
            h = f.read(110)
            if len(h) != 110 or h[:6] not in (b"070701", b"070702"):
                raise ValueError("bad newc header")
            size, ns = int(h[54:62], 16), int(h[94:102], 16)
            if not 0 < ns < 65536:
                raise ValueError("bad name size")
            name = f.read(ns).rstrip(b"\0").decode()
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
        self.e = ELFFile(io.BytesIO(data))
        self.syms = list(self.e.get_section_by_name(".dynsym").iter_symbols())
        rel, plt = self.e.get_section_by_name(".rela.plt"), self.e.get_section_by_name(".plt")
        self.plt = {plt.header.sh_addr + 32 + i * 16: self.syms[r.entry.r_info_sym].name
                    for i, r in enumerate(rel.iter_relocations())} if rel and plt else {}

    def read(self, addr, size):
        for seg in self.e.iter_segments():
            h = seg.header
            if h.p_type == "PT_LOAD" and h.p_vaddr <= addr and addr + size <= h.p_vaddr + h.p_filesz:
                off = h.p_offset + addr - h.p_vaddr
                return self.data[off:off + size]
        raise ValueError(f"unbacked VMA {addr:#x}+{size:#x}")

    def instructions(self, addr, size):
        return list(Cs(CS_ARCH_ARM64, CS_MODE_ARM).disasm(self.read(addr, size), addr))

    def calls(self, addr, size):
        result = []
        for x in self.instructions(addr, size):
            if x.mnemonic in ("bl", "b") and x.op_str.startswith("#0x"):
                t = int(x.op_str[1:], 16)
                result.append({"site": hex(x.address), "target": hex(t), "symbol": self.plt.get(t)})
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--appfw", type=Path, required=True)
    p.add_argument("--osal", type=Path, required=True)
    p.add_argument("--cpio", type=Path)
    p.add_argument("--serial", type=Path)
    args = p.parse_args()
    app, osal = Elf(args.appfw.read_bytes()), Elf(args.osal.read_bytes())
    expected = {"appfw": "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067",
                "osal": "fe248d226863722b2ab911ca70195c616566b8cb96a2ab13b920ee25202a7b9a"}
    for key, value in (("appfw", app), ("osal", osal)):
        if digest(value.data)["sha256"] != expected[key]:
            raise ValueError(f"{key} address-map SHA mismatch")
    report = {"inputs": {"appfw": digest(app.data), "osal": digest(osal.data)},
              "identity_string": app.read(0x26022d8, 64).split(b"\0", 1)[0].decode(),
              "bb_queue_storage": "appFw+0x5c38594",
              "receive_abi": {"return": "int (w0)", "qid": "uint32_t (w0)",
                              "output": "void ** (x1)", "timeout": "int (w2)"}}
    ranges = {"bb_initialize": (0x20ef9d0, 0x138), "bb_finalize": (0x20efb08, 0x138),
              "bb_receiver_shutdown_branch": (0x20f80b8, 0xe8),
              "temporary_queue_guard_ctor": (0x20ef48c, 0x178),
              "synchronous_request_helper": (0x20ef604, 0x1ec)}
    report["calls"] = {name: app.calls(addr, size) for name, (addr, size) in ranges.items()}
    sites = {"bb_finalize": 0x20efbb8, "bb_receiver": 0x20f80f4,
             "synchronous_request": 0x20ef7c8, "temporary_queue_drain": 0x20ef550}
    report["receive_sites"] = {}
    for name, addr in sites.items():
        report["receive_sites"][name] = {"call": hex(addr), "lr": hex(addr + 4),
            "following": [{"address": hex(x.address), "instruction": x.mnemonic + " " + x.op_str}
                          for x in app.instructions(addr + 4, 28)]}
    report["osal_symbols"] = {s.name: {"offset": hex(s.entry.st_value), "bytes": s.entry.st_size}
        for s in osal.syms if s.name in ("osal_rcv_msg_tmo", "u_osal_rcv_msg_tmo", "osal_get_msg_src", "osal_free_msg", "osal_dynamic_id")}
    report["kernel_receive_proxy_calls"] = osal.calls(0x3c60, 120)
    report["kernel_receive_ioctl"] = "0x80000007"
    report["qid_0x910040"] = {"bit15": bool(0x910040 & 0x8000), "branch": "u_osal_rcv_msg_tmo kernel proxy",
                              "runtime_owner_and_caller": "unbound by the supplied 293 wchan log"}
    if args.cpio:
        report["packed_inputs"] = {name: digest(cpio_member(args.cpio, name))
                                   for name in ("usr/lib/appFw.so", "usr/lib/libosal_uipc.so")}
    if args.serial:
        raw = args.serial.read_bytes()
        lines = raw.decode(errors="replace").splitlines()
        report["serial_snapshot"] = digest(raw)
        report["runtime_exact_site_or_qid_lines"] = [{"line": i, "text": line.strip()}
            for i, line in enumerate(lines, 1) if "20efbb8" in line.lower() or "910040" in line.lower()]
        report["receive_wchan_count"] = sum(line.strip() == "osal_rcv_msg_tmo" for line in lines)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
