"""Small read-only ELF64 little-endian section/symbol reader for this preflight."""
from __future__ import annotations
import struct
from pathlib import Path


class ELF64:
    def __init__(self, path: Path):
        self.path = path
        self.data = path.read_bytes()
        d = self.data
        if len(d) < 64 or d[:6] != b"\x7fELF\x02\x01":
            raise ValueError(f"not little-endian ELF64: {path}")
        self.etype = struct.unpack_from("<H", d, 16)[0]
        self.machine = struct.unpack_from("<H", d, 18)[0]
        shoff = struct.unpack_from("<Q", d, 40)[0]
        shentsize, shnum, shstr = struct.unpack_from("<HHH", d, 58)
        if not (shentsize >= 64 and 0 < shnum < 65536 and shstr < shnum and shoff + shentsize * shnum <= len(d)):
            raise ValueError("section table bounds")
        self.sections = []
        for i in range(shnum):
            fields = struct.unpack_from("<IIQQQQIIQQ", d, shoff + i * shentsize)
            name, kind, flags, addr, offset, size, link, info, align, entsize = fields
            if kind != 8 and offset + size > len(d):
                raise ValueError("section bounds")
            self.sections.append({"index": i, "name_offset": name, "type": kind, "flags": flags, "addr": addr, "offset": offset, "size": size, "link": link, "info": info, "align": align, "entsize": entsize})
        names = self.section_bytes(shstr)
        for s in self.sections:
            s["name"] = self.cstr(names, s["name_offset"])
        self.byname = {s["name"]: s for s in self.sections}

    @staticmethod
    def cstr(data: bytes, offset: int) -> str:
        if offset >= len(data):
            raise ValueError("string offset outside table")
        end = data.find(b"\0", offset)
        if end < 0:
            raise ValueError("unterminated ELF string")
        return data[offset:end].decode("ascii", "replace")

    def section_bytes(self, section):
        s = self.sections[section] if isinstance(section, int) else self.byname[section]
        if s["type"] == 8:
            raise ValueError("NOBITS section has no file bytes")
        return self.data[s["offset"]:s["offset"] + s["size"]]

    def symbols(self):
        for sec in self.sections:
            if sec["type"] != 2:
                continue
            if sec["link"] >= len(self.sections) or sec["entsize"] < 24 or sec["size"] % sec["entsize"]:
                raise ValueError("symbol table bounds")
            strings = self.section_bytes(sec["link"])
            for off in range(sec["offset"], sec["offset"] + sec["size"], sec["entsize"]):
                name, info, other, shndx, value, size = struct.unpack_from("<IBBHQQ", self.data, off)
                yield {"name": self.cstr(strings, name), "bind": info >> 4, "type": info & 15, "shndx": shndx, "value": value, "size": size, "sym_file_offset": off}

    def exported_name(self, name: str) -> bool:
        # Linux module export strings are NUL-delimited here; a symbol-table
        # definition alone is not enough to prove module export eligibility.
        sec = self.byname.get("__ksymtab_strings")
        return bool(sec and (b"\0" + name.encode() + b"\0") in (b"\0" + self.section_bytes(sec["name"])))
