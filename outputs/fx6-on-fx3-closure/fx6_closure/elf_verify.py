"""ELF64 AArch64 PT_LOAD, PT_DYNAMIC & ET_REL Section Mapper for File-Offset Translation."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


ELF64_HEADER_STRUCT = struct.Struct("<16sHHIQQQIHHHHHH")
ELF64_PHDR_STRUCT = struct.Struct("<IIQQQQQQ")
ELF64_SHDR_STRUCT = struct.Struct("<IIQQQQIIQQ")
ELF64_DYN_STRUCT = struct.Struct("<Qq")

ET_REL = 1
ET_EXEC = 2
ET_DYN = 3

PT_LOAD = 1
PT_DYNAMIC = 2

PF_X = 0x1
PF_W = 0x2
PF_R = 0x4

SHT_PROGBITS = 1
SHT_NOBITS = 8

SHF_WRITE = 0x1
SHF_ALLOC = 0x2
SHF_EXECINSTR = 0x4

EM_AARCH64 = 183


class ElfMappingError(ValueError):
    """Raised when an ELF64 header, PT_LOAD segment, ET_REL section, or offset check fails."""


@dataclass(frozen=True)
class Elf64LoadSegment:
    index: int
    p_vaddr: int
    p_paddr: int
    p_offset: int
    p_filesz: int
    p_memsz: int
    p_flags: int
    p_align: int

    @property
    def vma_file_delta(self) -> int:
        return self.p_vaddr - self.p_offset

    @property
    def flags_str(self) -> str:
        r = "R" if (self.p_flags & PF_R) else "-"
        w = "W" if (self.p_flags & PF_W) else "-"
        x = "X" if (self.p_flags & PF_X) else "-"
        return f"{r}{w}{x}"


@dataclass(frozen=True)
class Elf64Info:
    e_type: int
    e_machine: int
    e_entry: int
    file_size: int
    load_segments: Tuple[Elf64LoadSegment, ...]
    dynamic_tags: Dict[int, int]


@dataclass(frozen=True)
class Elf64SectionInfo:
    index: int
    name: str
    sh_type: int
    sh_flags: int
    sh_addr: int
    sh_offset: int
    sh_size: int
    sh_addralign: int

    @property
    def flags_str(self) -> str:
        a = "A" if (self.sh_flags & SHF_ALLOC) else "-"
        w = "W" if (self.sh_flags & SHF_WRITE) else "-"
        x = "X" if (self.sh_flags & SHF_EXECINSTR) else "-"
        return f"{a}{w}{x}"


@dataclass(frozen=True)
class Elf64RelocatableInfo:
    e_type: int
    e_machine: int
    file_size: int
    sections: Tuple[Elf64SectionInfo, ...]


def parse_elf64_aarch64(raw: bytes) -> Elf64Info:
    """Parse an AArch64 little-endian ELF64 shared/exec image and extract PT_LOAD & PT_DYNAMIC metadata."""
    if len(raw) < ELF64_HEADER_STRUCT.size:
        raise ElfMappingError(f"Buffer too small for ELF64 header ({len(raw)} B)")

    (
        e_ident,
        e_type,
        e_machine,
        e_version,
        e_entry,
        e_phoff,
        _e_shoff,
        _e_flags,
        e_ehsize,
        e_phentsize,
        e_phnum,
        _e_shentsize,
        _e_shnum,
        _e_shstrndx,
    ) = ELF64_HEADER_STRUCT.unpack_from(raw, 0)

    if e_ident[:4] != b"\x7fELF" or e_ident[4] != 2 or e_ident[5] != 1:
        raise ElfMappingError("Not a 64-bit little-endian ELF image")
    if e_machine != EM_AARCH64:
        raise ElfMappingError(f"Expected EM_AARCH64 (183), got e_machine={e_machine}")
    if e_version != 1 or e_ehsize < ELF64_HEADER_STRUCT.size:
        raise ElfMappingError("Invalid ELF64 version or header size")
    if e_phnum == 0 or e_phentsize < ELF64_PHDR_STRUCT.size:
        raise ElfMappingError("ELF64 image has no valid program headers")
    if e_phoff + e_phnum * e_phentsize > len(raw):
        raise ElfMappingError("Program header table extends past end of file")

    loads: List[Elf64LoadSegment] = []
    dyn_range: Optional[Tuple[int, int]] = None

    for idx in range(e_phnum):
        off = e_phoff + idx * e_phentsize
        p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = ELF64_PHDR_STRUCT.unpack_from(
            raw, off
        )
        if p_type == PT_LOAD:
            if p_offset + p_filesz > len(raw):
                raise ElfMappingError(
                    f"PT_LOAD[{idx}] file range [0x{p_offset:x}, +0x{p_filesz:x}) exceeds file size 0x{len(raw):x}"
                )
            if p_memsz < p_filesz:
                raise ElfMappingError(f"PT_LOAD[{idx}] p_memsz (0x{p_memsz:x}) < p_filesz (0x{p_filesz:x})")
            loads.append(
                Elf64LoadSegment(
                    index=idx,
                    p_vaddr=p_vaddr,
                    p_paddr=p_paddr,
                    p_offset=p_offset,
                    p_filesz=p_filesz,
                    p_memsz=p_memsz,
                    p_flags=p_flags,
                    p_align=p_align,
                )
            )
        elif p_type == PT_DYNAMIC:
            if p_offset + p_filesz > len(raw):
                raise ElfMappingError("PT_DYNAMIC extends past end of file")
            dyn_range = (p_offset, p_filesz)

    if not loads:
        raise ElfMappingError("ELF64 image contains zero PT_LOAD segments")

    dyn_tags: Dict[int, int] = {}
    if dyn_range is not None:
        d_off, d_sz = dyn_range
        for pos in range(d_off, d_off + d_sz - (d_sz % ELF64_DYN_STRUCT.size), ELF64_DYN_STRUCT.size):
            d_tag, d_val = ELF64_DYN_STRUCT.unpack_from(raw, pos)
            if d_tag == 0:
                dyn_tags[0] = 0
                break
            if d_tag not in dyn_tags:
                dyn_tags[d_tag] = d_val

    return Elf64Info(
        e_type=e_type,
        e_machine=e_machine,
        e_entry=e_entry,
        file_size=len(raw),
        load_segments=tuple(loads),
        dynamic_tags=dyn_tags,
    )


def vma_to_file_offset(
    elf: Elf64Info,
    vma: int,
    size: int = 1,
    required_flags: Optional[int] = None,
) -> Tuple[int, Elf64LoadSegment]:
    """Translate an ELF virtual memory address (VMA) to an exact file-backed offset via PT_LOAD."""
    if size <= 0:
        raise ElfMappingError(f"Invalid mapping size: {size}")

    matches: List[Tuple[int, Elf64LoadSegment]] = []
    for seg in elf.load_segments:
        if seg.p_vaddr <= vma and (vma - seg.p_vaddr) + size <= seg.p_filesz:
            foff = seg.p_offset + (vma - seg.p_vaddr)
            matches.append((foff, seg))

    if not matches:
        for seg in elf.load_segments:
            if seg.p_vaddr <= vma < seg.p_vaddr + seg.p_memsz:
                raise ElfMappingError(
                    f"VMA 0x{vma:x} (+{size} B) falls into unbacked NOBITS/.bss region of PT_LOAD[{seg.index}]"
                )
        raise ElfMappingError(f"VMA 0x{vma:x} (+{size} B) is not covered by any PT_LOAD segment")

    if len(matches) > 1:
        raise ElfMappingError(f"Ambiguous VMA 0x{vma:x}: matched {len(matches)} overlapping PT_LOAD segments")

    foff, seg = matches[0]
    if required_flags is not None and (seg.p_flags & required_flags) != required_flags:
        raise ElfMappingError(
            f"VMA 0x{vma:x} in PT_LOAD[{seg.index}] has flags 0x{seg.p_flags:x} ({seg.flags_str}), "
            f"missing required flags 0x{required_flags:x}"
        )
    return foff, seg


def parse_elf64_relocatable_aarch64(raw: bytes) -> Elf64RelocatableInfo:
    """Parse an AArch64 little-endian ELF64 relocatable object (`ET_REL`, e.g. `.ko` kernel module)."""
    if len(raw) < ELF64_HEADER_STRUCT.size:
        raise ElfMappingError(f"Buffer too small for ELF64 header ({len(raw)} B)")

    (
        e_ident,
        e_type,
        e_machine,
        e_version,
        _e_entry,
        _e_phoff,
        e_shoff,
        _e_flags,
        e_ehsize,
        _e_phentsize,
        _e_phnum,
        e_shentsize,
        e_shnum,
        e_shstrndx,
    ) = ELF64_HEADER_STRUCT.unpack_from(raw, 0)

    if e_ident[:4] != b"\x7fELF" or e_ident[4] != 2 or e_ident[5] != 1:
        raise ElfMappingError("Not a 64-bit little-endian ELF image")
    if e_machine != EM_AARCH64:
        raise ElfMappingError(f"Expected EM_AARCH64 (183), got e_machine={e_machine}")
    if e_type != ET_REL:
        raise ElfMappingError(f"Expected ET_REL (1) relocatable object, got e_type={e_type}")
    if e_version != 1 or e_ehsize < ELF64_HEADER_STRUCT.size:
        raise ElfMappingError("Invalid ELF64 version or header size")
    if e_shnum == 0 or e_shentsize < ELF64_SHDR_STRUCT.size or e_shstrndx >= e_shnum:
        raise ElfMappingError("Invalid ELF64 section header table metadata")
    if e_shoff + e_shnum * e_shentsize > len(raw):
        raise ElfMappingError("Section header table extends past end of file")

    raw_shdrs = [
        ELF64_SHDR_STRUCT.unpack_from(raw, e_shoff + idx * e_shentsize)
        for idx in range(e_shnum)
    ]
    shstr_hdr = raw_shdrs[e_shstrndx]
    shstr_off, shstr_sz = shstr_hdr[4], shstr_hdr[5]
    if shstr_off + shstr_sz > len(raw):
        raise ElfMappingError("Section header string table extends past end of file")
    shstrtab = raw[shstr_off : shstr_off + shstr_sz]

    sections: List[Elf64SectionInfo] = []
    for idx, hdr in enumerate(raw_shdrs):
        sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, _link, _info, sh_addralign, _entsz = hdr
        if sh_name >= len(shstrtab):
            raise ElfMappingError(f"Section {idx} name index {sh_name} out of range")
        nul = shstrtab.find(b"\x00", sh_name)
        sec_name = shstrtab[sh_name : (nul if nul >= 0 else len(shstrtab))].decode("ascii", errors="replace")
        if sh_type != SHT_NOBITS and sh_size > 0 and sh_offset + sh_size > len(raw):
            raise ElfMappingError(
                f"Section {sec_name!r} [{idx}] file range [0x{sh_offset:x}, +0x{sh_size:x}) exceeds file size"
            )
        sections.append(
            Elf64SectionInfo(
                index=idx,
                name=sec_name,
                sh_type=sh_type,
                sh_flags=sh_flags,
                sh_addr=sh_addr,
                sh_offset=sh_offset,
                sh_size=sh_size,
                sh_addralign=sh_addralign,
            )
        )

    return Elf64RelocatableInfo(
        e_type=e_type,
        e_machine=e_machine,
        file_size=len(raw),
        sections=tuple(sections),
    )


def section_offset_to_file_offset(
    elf_rel: Elf64RelocatableInfo,
    section_name: str,
    section_offset: int,
    size: int = 1,
    required_sh_flags: Optional[int] = None,
) -> Tuple[int, Elf64SectionInfo]:
    """Translate a section-relative offset (`section_name + section_offset`) in an `ET_REL` object to file offset."""
    if size <= 0 or section_offset < 0:
        raise ElfMappingError(f"Invalid section offset 0x{section_offset:x} or size {size}")

    matches = [s for s in elf_rel.sections if s.name == section_name]
    if not matches:
        raise ElfMappingError(f"Section {section_name!r} not found in ET_REL object")
    if len(matches) > 1:
        raise ElfMappingError(f"Ambiguous section {section_name!r}: matched {len(matches)} sections")

    sec = matches[0]
    if sec.sh_type == SHT_NOBITS:
        raise ElfMappingError(f"Section {section_name!r} is SHT_NOBITS (unbacked in file)")
    if section_offset + size > sec.sh_size:
        raise ElfMappingError(
            f"{section_name}+0x{section_offset:x} (+{size} B) exceeds section size 0x{sec.sh_size:x}"
        )
    if required_sh_flags is not None and (sec.sh_flags & required_sh_flags) != required_sh_flags:
        raise ElfMappingError(
            f"Section {section_name!r} has flags 0x{sec.sh_flags:x} ({sec.flags_str}), "
            f"missing required flags 0x{required_sh_flags:x}"
        )

    return sec.sh_offset + section_offset, sec
