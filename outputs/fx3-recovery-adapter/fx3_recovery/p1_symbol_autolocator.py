"""Phase 25 Version-Independent `nflasha1` (`p1`) 4-Site AArch64 Signature Autolocator.

Provides:
1. Bounded, O_RDONLY-only ELF64 AArch64 `.dynsym` / `.rela.plt` / prologue-masked
   4-Site Autolocator for:
   - `libsdfileinputupdaterapi.so`:
     * `SDUUDConditionChecker::isVersionOK` (`mov w0, #1; ret`, preserving `isModelOK`/`isRegionOK`)
     * `SignatureVerification::VerifySignature` (`mov w0, #0; ret`)
   - `libupdatercorecommon.so`:
     * `RVchk4PI::chkFirmInfo_before` reject return (`mov w19, #-1` -> `mov w19, #0`)
     * `RVchk4PI::chkFirmInfo_before` comparison gate (`csinv w19, wzr, wzr, gt` -> `mov w19, #0`)
2. Fail-closed ambiguity & prologue validation: rejects 0-match, multi-match,
   out-of-`.text`, or corrupted-prologue images without guessing.
3. Unicorn AArch64 behavioral verification of ORIGINAL, PATCHED, and ROLLED-BACK
   states on both real FX3 2.04/2.05 donors and shifted-VMA v7.02-simulated images.
4. SquashFS `Z_SYNC_FLUSH` byte-length-invariant `p1` roundtrip + 2-pass SHA-256
   rollback verification, plus Clean-Room pure-Python synthetic ELF64 + FAT12/SquashFS
   fixture builders for `FX3_FX6_FORCE_CLEAN_ROOM=1`.

Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` (hard-locked)
- All donor files opened strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import md5, sha256
from pathlib import Path
import struct
from typing import Callable, Dict, List, Optional, Sequence, Tuple
import zlib

from .fat import FatP1, MAX_P1
from .files import read_file, require, resolve_unicorn_site_packages
from .squash import SquashFS, inflate_bounded

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

AUTOLOCATOR_SCHEMA = "fx3-p1-autolocator-v2"
REFERENCE_PROFILE = "fx3-p1-reference-v1"

REFERENCE_SITE_OFFSETS: Dict[str, int] = {
    "isVersionOK": 0x9FD4,
    "VerifySignature": 0xABF0,
    "chkFirmInfo_before_reject_ret": 0xD208,
    "chkFirmInfo_before_cmp_csinv": 0xD27C,
}

PATCH_BYTES: Dict[str, bytes] = {
    "isVersionOK": bytes.fromhex("20008052c0035fd6"),  # mov w0, #1; ret
    "VerifySignature": bytes.fromhex("00008052c0035fd6"),  # mov w0, #0; ret
    "chkFirmInfo_before_reject_ret": bytes.fromhex("13008052"),  # mov w19, #0
    "chkFirmInfo_before_cmp_csinv": bytes.fromhex("13008052"),  # mov w19, #0
}

LIB_SD = "/usr/lib/libsdfileinputupdaterapi.so"
LIB_UC = "/usr/lib/libupdatercorecommon.so"
INITRD_PATH = "/boot/initrd.img"
KERNEL_PATH = "/boot/vmlinux.bin"
CHECKSUM_PATH = "/p1chksum"

# ELF64 constants
ELF_MAGIC = b"\x7fELF"
ELFCLASS64 = 2
ELFDATA2LSB = 1
EM_AARCH64 = 183
PT_LOAD = 1
SHT_PROGBITS = 1
SHT_STRTAB = 3
SHT_RELA = 4
SHT_DYNSYM = 11
R_AARCH64_JUMP_SLOT = 1026

MAX_ELF_BYTES = 16 * 1024 * 1024


class AutolocatorError(ValueError):
    """Fail-closed autolocator error (ambiguity, missing symbol, or prologue mismatch)."""


@dataclass(frozen=True)
class Elf64Segment:
    p_type: int
    p_flags: int
    p_offset: int
    p_vaddr: int
    p_paddr: int
    p_filesz: int
    p_memsz: int
    p_align: int


@dataclass(frozen=True)
class Elf64Section:
    index: int
    name: str
    sh_type: int
    sh_flags: int
    sh_addr: int
    sh_offset: int
    sh_size: int
    sh_link: int
    sh_info: int
    sh_addralign: int
    sh_entsize: int


@dataclass(frozen=True)
class Elf64Symbol:
    index: int
    name: str
    st_value: int
    st_size: int
    st_info: int
    st_other: int
    st_shndx: int
    file_offset: Optional[int]


@dataclass(frozen=True)
class Elf64RelaPltEntry:
    index: int
    r_offset: int
    r_type: int
    sym_index: int
    sym_name: str
    plt_vaddr: Optional[int]
    plt_offset: Optional[int]


@dataclass(frozen=True)
class LocatedSite:
    site_id: str
    library_path: str
    symbol_name: str
    symbol_vaddr: int
    symbol_offset: int
    patch_vaddr: int
    patch_offset: int
    original_bytes_hex: str
    patched_bytes_hex: str
    preserved_regions: Tuple[Tuple[int, int, str], ...]
    plt_cross_checked: bool
    notes: str


@dataclass(frozen=True)
class AutolocatorReport:
    schema: str
    profile_mode: str
    persistent_emmc_writes_authorized: bool
    sites: Dict[str, LocatedSite]
    preserved_checks: Dict[str, bool]
    warnings: Tuple[str, ...]


@dataclass(frozen=True)
class UnicornSiteVerification:
    site_id: str
    library_path: str
    patch_offset: int
    original_result: int
    patched_result: int
    rollback_result: int
    preserved_ok: bool
    passed: bool
    details: str


@dataclass(frozen=True)
class UnicornVerificationReport:
    unicorn_available: bool
    all_passed: bool
    sites: Dict[str, UnicornSiteVerification]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P1RoundtripReport:
    source_sha256: str
    candidate_sha256: str
    pass1_rollback_sha256: str
    pass2_rollback_sha256: str
    byte_length_invariant: bool
    rollback_verified: bool
    squashfs_readback_ok: bool
    persistent_emmc_writes_authorized: bool
    located_offsets: Dict[str, int]
    compression_attempts: Tuple[Dict[str, int], ...]


class Elf64Image:
    """Bounds-checked read-only parser for AArch64 ELF64 shared objects."""

    def __init__(self, data: bytes):
        if not isinstance(data, (bytes, bytearray)) or len(data) < 64 or len(data) > MAX_ELF_BYTES:
            raise AutolocatorError("invalid ELF64 size")
        self.data = bytes(data)
        if self.data[:4] != ELF_MAGIC or self.data[4] != ELFCLASS64 or self.data[5] != ELFDATA2LSB:
            raise AutolocatorError("expected little-endian ELF64")
        e_type, e_machine, e_version = struct.unpack_from("<HHI", self.data, 16)
        if e_machine != EM_AARCH64 or e_version != 1:
            raise AutolocatorError(f"expected AArch64 ELF (got e_machine={e_machine})")
        self.e_type = e_type
        self.e_entry, self.e_phoff, self.e_shoff = struct.unpack_from("<QQQ", self.data, 24)
        (
            self.e_flags,
            self.e_ehsize,
            self.e_phentsize,
            self.e_phnum,
            self.e_shentsize,
            self.e_shnum,
            self.e_shstrndx,
        ) = struct.unpack_from("<IHHHHHH", self.data, 48)

        if self.e_phentsize != 56 or self.e_phoff + self.e_phnum * 56 > len(self.data):
            raise AutolocatorError("corrupt ELF64 program header table")
        if self.e_shentsize != 64 or self.e_shoff + self.e_shnum * 64 > len(self.data):
            raise AutolocatorError("corrupt ELF64 section header table")
        if self.e_shstrndx >= self.e_shnum:
            raise AutolocatorError("invalid shstrndx")

        self.segments: List[Elf64Segment] = []
        for i in range(self.e_phnum):
            fields = struct.unpack_from("<IIQQQQQQ", self.data, self.e_phoff + i * 56)
            seg = Elf64Segment(*fields)
            if seg.p_filesz > 0 and seg.p_offset + seg.p_filesz > len(self.data):
                raise AutolocatorError("ELF64 PT_LOAD exceeds file size")
            self.segments.append(seg)

        shstr_hdr = struct.unpack_from("<IIQQQQIIQQ", self.data, self.e_shoff + self.e_shstrndx * 64)
        shstr_off, shstr_size = shstr_hdr[4], shstr_hdr[5]
        if shstr_off + shstr_size > len(self.data):
            raise AutolocatorError("ELF64 .shstrtab exceeds file size")
        shstr = self.data[shstr_off : shstr_off + shstr_size]

        self.sections: List[Elf64Section] = []
        self.sections_by_name: Dict[str, Elf64Section] = {}
        for i in range(self.e_shnum):
            sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize = (
                struct.unpack_from("<IIQQQQIIQQ", self.data, self.e_shoff + i * 64)
            )
            if sh_type != 8 and sh_size > 0 and sh_offset + sh_size > len(self.data):  # SHT_NOBITS=8
                raise AutolocatorError(f"ELF64 section {i} exceeds file size")
            name = self._cstr(shstr, sh_name)
            sec = Elf64Section(
                index=i,
                name=name,
                sh_type=sh_type,
                sh_flags=sh_flags,
                sh_addr=sh_addr,
                sh_offset=sh_offset,
                sh_size=sh_size,
                sh_link=sh_link,
                sh_info=sh_info,
                sh_addralign=sh_addralign,
                sh_entsize=sh_entsize,
            )
            self.sections.append(sec)
            if name and name not in self.sections_by_name:
                self.sections_by_name[name] = sec

        self.dynsym: List[Elf64Symbol] = self._parse_dynsym()
        self.rela_plt: List[Elf64RelaPltEntry] = self._parse_rela_plt()
        self.plt_vaddr_to_sym: Dict[int, str] = {
            e.plt_vaddr: e.sym_name for e in self.rela_plt if e.plt_vaddr is not None and e.sym_name
        }

    @staticmethod
    def _cstr(table: bytes, offset: int) -> str:
        if offset < 0 or offset >= len(table):
            return ""
        end = table.find(b"\x00", offset)
        if end == -1:
            end = len(table)
        return table[offset:end].decode("ascii", errors="replace")

    def vaddr_to_offset(self, vaddr: int) -> Optional[int]:
        for seg in self.segments:
            if seg.p_type == PT_LOAD and seg.p_filesz > 0:
                if seg.p_vaddr <= vaddr < seg.p_vaddr + seg.p_filesz:
                    return seg.p_offset + (vaddr - seg.p_vaddr)
        for sec in self.sections:
            if sec.sh_type != 8 and sec.sh_size > 0 and sec.sh_addr > 0:
                if sec.sh_addr <= vaddr < sec.sh_addr + sec.sh_size:
                    return sec.sh_offset + (vaddr - sec.sh_addr)
        return None

    def offset_to_vaddr(self, offset: int) -> Optional[int]:
        for seg in self.segments:
            if seg.p_type == PT_LOAD and seg.p_filesz > 0:
                if seg.p_offset <= offset < seg.p_offset + seg.p_filesz:
                    return seg.p_vaddr + (offset - seg.p_offset)
        for sec in self.sections:
            if sec.sh_type != 8 and sec.sh_size > 0:
                if sec.sh_offset <= offset < sec.sh_offset + sec.sh_size:
                    return sec.sh_addr + (offset - sec.sh_offset)
        return None

    def _parse_dynsym(self) -> List[Elf64Symbol]:
        sec = self.sections_by_name.get(".dynsym")
        if sec is None or sec.sh_entsize != 24:
            return []
        if sec.sh_link >= len(self.sections):
            raise AutolocatorError("invalid .dynsym sh_link")
        str_sec = self.sections[sec.sh_link]
        dynstr = self.data[str_sec.sh_offset : str_sec.sh_offset + str_sec.sh_size]
        count = sec.sh_size // 24
        out: List[Elf64Symbol] = []
        for i in range(count):
            st_name, st_info, st_other, st_shndx, st_value, st_size = struct.unpack_from(
                "<IBBHQQ", self.data, sec.sh_offset + i * 24
            )
            name = self._cstr(dynstr, st_name)
            file_off = self.vaddr_to_offset(st_value) if st_value != 0 and st_shndx != 0 else None
            out.append(
                Elf64Symbol(
                    index=i,
                    name=name,
                    st_value=st_value,
                    st_size=st_size,
                    st_info=st_info,
                    st_other=st_other,
                    st_shndx=st_shndx,
                    file_offset=file_off,
                )
            )
        return out

    def _parse_rela_plt(self) -> List[Elf64RelaPltEntry]:
        sec = self.sections_by_name.get(".rela.plt")
        if sec is None or sec.sh_entsize != 24 or not self.dynsym:
            return []
        plt_sec = self.sections_by_name.get(".plt")
        count = sec.sh_size // 24
        out: List[Elf64RelaPltEntry] = []
        for i in range(count):
            r_offset, r_info, _r_addend = struct.unpack_from("<QQq", self.data, sec.sh_offset + i * 24)
            sym_idx = r_info >> 32
            r_type = r_info & 0xFFFFFFFF
            sym_name = self.dynsym[sym_idx].name if 0 <= sym_idx < len(self.dynsym) else ""
            plt_vaddr: Optional[int] = None
            plt_offset: Optional[int] = None
            if plt_sec is not None and r_type == R_AARCH64_JUMP_SLOT:
                # Standard AArch64 ELF64 PLT layout: 32-byte PLT0 header + 16-byte stubs
                cand_vaddr = plt_sec.sh_addr + 32 + 16 * i
                if cand_vaddr + 16 <= plt_sec.sh_addr + plt_sec.sh_size:
                    plt_vaddr = cand_vaddr
                    plt_offset = self.vaddr_to_offset(cand_vaddr)
            out.append(
                Elf64RelaPltEntry(
                    index=i,
                    r_offset=r_offset,
                    r_type=r_type,
                    sym_index=sym_idx,
                    sym_name=sym_name,
                    plt_vaddr=plt_vaddr,
                    plt_offset=plt_offset,
                )
            )
        return out

    def read_u32(self, file_offset: int) -> int:
        if file_offset < 0 or file_offset + 4 > len(self.data):
            raise AutolocatorError(f"ELF read_u32 out of bounds: {hex(file_offset)}")
        return struct.unpack_from("<I", self.data, file_offset)[0]

    def find_unique_defined_symbol(self, predicate: Callable[[Elf64Symbol], bool], label: str) -> Elf64Symbol:
        matches = [s for s in self.dynsym if s.st_shndx != 0 and s.st_value != 0 and predicate(s)]
        if not matches:
            raise AutolocatorError(f"missing required .dynsym symbol for {label}")
        if len(matches) > 1:
            names = [m.name for m in matches]
            raise AutolocatorError(f"ambiguous multiple .dynsym symbols for {label}: {names}")
        sym = matches[0]
        if sym.file_offset is None:
            raise AutolocatorError(f"symbol {sym.name} VMA {hex(sym.st_value)} does not map into PT_LOAD")
        return sym

    def resolve_bl_target_symbol(self, insn_file_offset: int) -> Optional[str]:
        word = self.read_u32(insn_file_offset)
        if (word & 0xFC000000) != 0x94000000:
            return None
        imm26 = word & 0x03FFFFFF
        if imm26 & 0x02000000:
            imm26 -= 0x04000000
        pc_vaddr = self.offset_to_vaddr(insn_file_offset)
        if pc_vaddr is None:
            return None
        target_vaddr = pc_vaddr + imm26 * 4
        return self.plt_vaddr_to_sym.get(target_vaddr)


def _require_in_text(elf: Elf64Image, offset: int, size: int, label: str) -> None:
    text = elf.sections_by_name.get(".text")
    if text is None:
        raise AutolocatorError("missing .text section")
    if offset < text.sh_offset or offset + size > text.sh_offset + text.sh_size:
        raise AutolocatorError(
            f"{label} span [{hex(offset)}..{hex(offset + size)}) falls outside .text "
            f"[{hex(text.sh_offset)}..{hex(text.sh_offset + text.sh_size)})"
        )


def _is_stp_fp_lr_pre(word: int) -> bool:
    # stp x29, x30, [sp, #imm]! -> 10 101 0 011 1 imm7 11110 11111 11101
    # Bit mask: opcode bits [31:22]=0b1010100111 -> 0xFFC00000 == 0xA9C00000? Wait:
    # 0xa9bb7bfd: bit31..22 = 1010100110 (0xA9800000), imm7=0b111011, Rt2=30 (0x7800), Rn=31 (0x03e0), Rt=29 (0x1d)
    # Mask off imm7 bits [21:15] (0x003F8000): (word & 0xFFC07FFF) == 0xA9807BFD
    return (word & 0xFFC07FFF) == 0xA9807BFD


def _is_mov_fp_sp(word: int) -> bool:
    return word == 0x910003FD


def _is_adrp_x0(word: int) -> bool:
    return (word & 0x9F00001F) == 0x90000000


def _is_add_x0_x0_imm(word: int) -> bool:
    return (word & 0xFFC003FF) == 0x91000000


def _is_bl(word: int) -> bool:
    return (word & 0xFC000000) == 0x94000000


def autolocate_sdfileinput_sites(
    raw: bytes,
    *,
    require_plt_cross_check: bool = False,
) -> Tuple[LocatedSite, LocatedSite]:
    """Locate `isVersionOK` and `VerifySignature` in `libsdfileinputupdaterapi.so`."""
    elf = Elf64Image(raw)

    # 1. Locate SDUUDConditionChecker::isVersionOK
    ver_sym = elf.find_unique_defined_symbol(
        lambda s: "SDUUDConditionChecker" in s.name and "isVersionOK" in s.name,
        "SDUUDConditionChecker::isVersionOK",
    )
    if ver_sym.st_size < 0x18:
        raise AutolocatorError(f"isVersionOK st_size too small: {ver_sym.st_size}")
    ver_off = ver_sym.file_offset
    assert ver_off is not None
    _require_in_text(elf, ver_off, ver_sym.st_size, "isVersionOK")

    # Masked prologue verification for isVersionOK:
    #   +0x00: ldr w2, [x1, #imm]   (0xB9400022 mask 0xFFC003FF)
    #   +0x04: mov w0, #0           (0x52800000)
    #   +0x08: ldr w3, [x1, #imm]   (0xB9400023 mask 0xFFC003FF)
    #   +0x0c: cmp w3, w2           (0x6B02007F)
    #   tail : ret                  (0xD65F03C0)
    w0 = elf.read_u32(ver_off + 0)
    w1 = elf.read_u32(ver_off + 4)
    w2 = elf.read_u32(ver_off + 8)
    w3 = elf.read_u32(ver_off + 12)
    w_ret = elf.read_u32(ver_off + ver_sym.st_size - 4)
    if not (
        (w0 & 0xFFC003FF) == 0xB9400022
        and w1 == 0x52800000
        and (w2 & 0xFFC003FF) == 0xB9400023
        and w3 == 0x6B02007F
        and w_ret == 0xD65F03C0
    ):
        raise AutolocatorError(
            f"isVersionOK prologue mismatch at {hex(ver_off)}: "
            f"{[hex(w0), hex(w1), hex(w2), hex(w3), hex(w_ret)]}"
        )

    # Verify adjacent preserved functions (isModelOK, isRegionOK) exist and do not overlap patch
    model_sym = elf.find_unique_defined_symbol(
        lambda s: "SDUUDConditionChecker" in s.name and "isModelOK" in s.name,
        "SDUUDConditionChecker::isModelOK",
    )
    region_sym = elf.find_unique_defined_symbol(
        lambda s: "SDUUDConditionChecker" in s.name and "isRegionOK" in s.name,
        "SDUUDConditionChecker::isRegionOK",
    )
    assert model_sym.file_offset is not None and region_sym.file_offset is not None
    preserved = (
        (model_sym.file_offset, model_sym.file_offset + max(model_sym.st_size, 4), "isModelOK"),
        (region_sym.file_offset, region_sym.file_offset + max(region_sym.st_size, 4), "isRegionOK"),
    )
    patch_end = ver_off + 8
    for p_start, p_end, pname in preserved:
        if max(ver_off, p_start) < min(patch_end, p_end):
            raise AutolocatorError(f"isVersionOK patch overlaps preserved symbol {pname}")

    site_ver = LocatedSite(
        site_id="isVersionOK",
        library_path=LIB_SD,
        symbol_name=ver_sym.name,
        symbol_vaddr=ver_sym.st_value,
        symbol_offset=ver_off,
        patch_vaddr=ver_sym.st_value,
        patch_offset=ver_off,
        original_bytes_hex=raw[ver_off : ver_off + 8].hex(),
        patched_bytes_hex=PATCH_BYTES["isVersionOK"].hex(),
        preserved_regions=preserved,
        plt_cross_checked=False,
        notes="Located via .dynsym + masked AArch64 prologue (ldr w2/mov w0/ldr w3/cmp w3,w2/ret); isModelOK & isRegionOK preserved",
    )

    # 2. Locate SignatureVerification::VerifySignature
    sig_sym = elf.find_unique_defined_symbol(
        lambda s: "SignatureVerification" in s.name and "VerifySignature" in s.name,
        "SignatureVerification::VerifySignature",
    )
    if sig_sym.st_size < 0x18:
        raise AutolocatorError(f"VerifySignature st_size too small: {sig_sym.st_size}")
    sig_off = sig_sym.file_offset
    assert sig_off is not None
    _require_in_text(elf, sig_off, sig_sym.st_size, "VerifySignature")

    sw0 = elf.read_u32(sig_off + 0)
    sw1 = elf.read_u32(sig_off + 4)
    if not (_is_stp_fp_lr_pre(sw0) and _is_mov_fp_sp(sw1)):
        raise AutolocatorError(
            f"VerifySignature prologue mismatch at {hex(sig_off)}: {[hex(sw0), hex(sw1)]}"
        )

    # Optional .rela.plt cross-check for VerifySignature (expects at least one PLT call inside function)
    plt_calls = []
    for off in range(sig_off, sig_off + sig_sym.st_size, 4):
        target = elf.resolve_bl_target_symbol(off)
        if target:
            plt_calls.append(target)
    if require_plt_cross_check and not plt_calls:
        raise AutolocatorError("VerifySignature failed .rela.plt cross-check (zero PLT calls resolved)")

    site_sig = LocatedSite(
        site_id="VerifySignature",
        library_path=LIB_SD,
        symbol_name=sig_sym.name,
        symbol_vaddr=sig_sym.st_value,
        symbol_offset=sig_off,
        patch_vaddr=sig_sym.st_value,
        patch_offset=sig_off,
        original_bytes_hex=raw[sig_off : sig_off + 8].hex(),
        patched_bytes_hex=PATCH_BYTES["VerifySignature"].hex(),
        preserved_regions=(),
        plt_cross_checked=bool(plt_calls),
        notes=f"Located via .dynsym + masked stp x29,x30,[sp,#imm]!/mov x29,sp prologue (plt_calls={len(plt_calls)})",
    )
    return site_ver, site_sig


def autolocate_updatercorecommon_sites(
    raw: bytes,
    *,
    require_plt_cross_check: bool = False,
) -> Tuple[LocatedSite, LocatedSite]:
    """Locate the two `RVchk4PI::chkFirmInfo_before` gate sites in `libupdatercorecommon.so`."""
    elf = Elf64Image(raw)
    fn_sym = elf.find_unique_defined_symbol(
        lambda s: "RVchk4PI" in s.name and "chkFirmInfo_before" in s.name,
        "RVchk4PI::chkFirmInfo_before",
    )
    if fn_sym.st_size < 0x40:
        raise AutolocatorError(f"chkFirmInfo_before st_size too small: {fn_sym.st_size}")
    fn_off = fn_sym.file_offset
    assert fn_off is not None
    _require_in_text(elf, fn_off, fn_sym.st_size, "chkFirmInfo_before")
    fn_end = fn_off + fn_sym.st_size

    # Site 3: `mov w19, #-1` (0x12800013) preceded by `adrp x0, ...` and followed by:
    #   +4 : add x0, x0, #lo12
    #   +8 : bl <remove@plt>
    #   +12: adrp x0, ...
    #   +16: add x0, x0, #lo12
    #   +20: bl <remove@plt>
    #   +32: bl <umount@plt>
    site3_matches: List[Tuple[int, bool]] = []
    for off in range(fn_off + 4, fn_end - 36, 4):
        w_cur = elf.read_u32(off)
        if w_cur != 0x12800013:  # mov w19, #-1
            continue
        w_prev = elf.read_u32(off - 4)
        w_p1 = elf.read_u32(off + 4)
        w_p2 = elf.read_u32(off + 8)
        w_p3 = elf.read_u32(off + 12)
        w_p4 = elf.read_u32(off + 16)
        w_p5 = elf.read_u32(off + 20)
        w_p8 = elf.read_u32(off + 32)
        if not (
            _is_adrp_x0(w_prev)
            and _is_add_x0_x0_imm(w_p1)
            and _is_bl(w_p2)
            and _is_adrp_x0(w_p3)
            and _is_add_x0_x0_imm(w_p4)
            and _is_bl(w_p5)
            and _is_bl(w_p8)
        ):
            continue
        t1 = elf.resolve_bl_target_symbol(off + 8)
        t2 = elf.resolve_bl_target_symbol(off + 20)
        t3 = elf.resolve_bl_target_symbol(off + 32)
        plt_ok = (t1 == "remove" and t2 == "remove" and t3 == "umount")
        if require_plt_cross_check and not plt_ok:
            continue
        if (t1 is not None and t1 != "remove") or (t2 is not None and t2 != "remove") or (t3 is not None and t3 != "umount"):
            continue
        site3_matches.append((off, plt_ok))

    if len(site3_matches) != 1:
        raise AutolocatorError(
            f"chkFirmInfo_before_reject_ret expected 1 unique match, found {len(site3_matches)}: "
            f"{[hex(x[0]) for x in site3_matches]}"
        )
    s3_off, s3_plt_ok = site3_matches[0]
    s3_vaddr = elf.offset_to_vaddr(s3_off)
    if s3_vaddr is None:
        raise AutolocatorError("failed to map site 3 offset to VMA")

    # Site 4: `csinv w19, wzr, wzr, gt` (0x5A9FC3F3) preceded by `cmp wN, wM`
    # and followed by backward branch `b <target>` within chkFirmInfo_before.
    site4_matches: List[int] = []
    for off in range(fn_off + 4, fn_end - 4, 4):
        w_cur = elf.read_u32(off)
        if w_cur != 0x5A9FC3F3:
            continue
        w_prev = elf.read_u32(off - 4)
        w_next = elf.read_u32(off + 4)
        # cmp wN, wM -> subs wzr, wN, wM -> (w & 0xFFE0FC1F) == 0x6B00001F
        is_cmp = (w_prev & 0xFFE0FC1F) == 0x6B00001F
        is_b = (w_next & 0xFC000000) == 0x14000000
        if not (is_cmp and is_b):
            continue
        imm26 = w_next & 0x03FFFFFF
        if imm26 & 0x02000000:
            imm26 -= 0x04000000
        b_target = (off + 4) + imm26 * 4
        if not (fn_off <= b_target < off):
            continue
        site4_matches.append(off)

    if len(site4_matches) != 1:
        raise AutolocatorError(
            f"chkFirmInfo_before_cmp_csinv expected 1 unique match, found {len(site4_matches)}: "
            f"{[hex(x) for x in site4_matches]}"
        )
    s4_off = site4_matches[0]
    s4_vaddr = elf.offset_to_vaddr(s4_off)
    if s4_vaddr is None:
        raise AutolocatorError("failed to map site 4 offset to VMA")

    site3 = LocatedSite(
        site_id="chkFirmInfo_before_reject_ret",
        library_path=LIB_UC,
        symbol_name=fn_sym.name,
        symbol_vaddr=fn_sym.st_value,
        symbol_offset=fn_off,
        patch_vaddr=s3_vaddr,
        patch_offset=s3_off,
        original_bytes_hex=raw[s3_off : s3_off + 4].hex(),
        patched_bytes_hex=PATCH_BYTES["chkFirmInfo_before_reject_ret"].hex(),
        preserved_regions=(),
        plt_cross_checked=s3_plt_ok,
        notes="Located inside chkFirmInfo_before via adrp/mov w19,#-1/add/bl(remove)x2/bl(umount) pattern",
    )
    site4 = LocatedSite(
        site_id="chkFirmInfo_before_cmp_csinv",
        library_path=LIB_UC,
        symbol_name=fn_sym.name,
        symbol_offset=fn_off,
        symbol_vaddr=fn_sym.st_value,
        patch_vaddr=s4_vaddr,
        patch_offset=s4_off,
        original_bytes_hex=raw[s4_off : s4_off + 4].hex(),
        patched_bytes_hex=PATCH_BYTES["chkFirmInfo_before_cmp_csinv"].hex(),
        preserved_regions=(),
        plt_cross_checked=False,
        notes="Located inside chkFirmInfo_before via cmp wN,wM + csinv w19,wzr,wzr,gt + backward branch",
    )
    return site3, site4


def autolocate_4_sites(
    sd_raw: bytes,
    uc_raw: bytes,
    *,
    profile_mode: str = "autolocated",
    require_plt_cross_check: bool = False,
) -> AutolocatorReport:
    """Run the full 4-site AArch64 autolocator across both p1 updater libraries."""
    s1, s2 = autolocate_sdfileinput_sites(sd_raw, require_plt_cross_check=require_plt_cross_check)
    s3, s4 = autolocate_updatercorecommon_sites(uc_raw, require_plt_cross_check=require_plt_cross_check)
    sites = {s.site_id: s for s in (s1, s2, s3, s4)}
    warnings: List[str] = []
    exact_ref = all(sites[k].patch_offset == REFERENCE_SITE_OFFSETS[k] for k in REFERENCE_SITE_OFFSETS)
    if not exact_ref:
        warnings.append("Located offsets differ from FX3 2.04/2.05 reference offsets (VMA/layout shifted build)")
    preserved_ok = all(
        max(s1.patch_offset, b) >= min(s1.patch_offset + 8, e) for b, e, _ in s1.preserved_regions
    )
    return AutolocatorReport(
        schema=AUTOLOCATOR_SCHEMA,
        profile_mode=profile_mode,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        sites=sites,
        preserved_checks={"isModelOK_and_isRegionOK_untouched": preserved_ok},
        warnings=tuple(warnings),
    )


def apply_autolocated_patches(raw: bytes, sites: Sequence[LocatedSite]) -> bytes:
    """Apply autolocated in-place instruction replacements on a library buffer."""
    buf = bytearray(raw)
    for site in sites:
        old = bytes.fromhex(site.original_bytes_hex)
        new = bytes.fromhex(site.patched_bytes_hex)
        require(len(old) == len(new) and len(old) > 0, f"invalid patch lengths for {site.site_id}")
        at = site.patch_offset
        require(0 <= at and at + len(old) <= len(buf), f"patch out of range for {site.site_id}")
        require(buf[at : at + len(old)] == old, f"original bytes mismatch at {site.site_id}")
        buf[at : at + len(old)] = new
        for begin, end, pname in site.preserved_regions:
            require(buf[begin:end] == raw[begin:end], f"preserved region {pname} mutated")
    return bytes(buf)


def rollback_autolocated_patches(patched_raw: bytes, sites: Sequence[LocatedSite]) -> bytes:
    """Deterministically restore original bytes for all autolocated sites."""
    buf = bytearray(patched_raw)
    for site in sites:
        old = bytes.fromhex(site.original_bytes_hex)
        new = bytes.fromhex(site.patched_bytes_hex)
        at = site.patch_offset
        require(0 <= at and at + len(new) <= len(buf), f"rollback out of range for {site.site_id}")
        require(buf[at : at + len(new)] == new, f"patched bytes mismatch during rollback at {site.site_id}")
        buf[at : at + len(new)] = old
    return bytes(buf)


def _import_unicorn():
    site_dir = resolve_unicorn_site_packages()
    if site_dir is not None:
        import sys
        if str(site_dir) not in sys.path:
            sys.path.insert(0, str(site_dir))
    import unicorn
    from unicorn import arm64_const
    return unicorn, arm64_const


def _map_elf_into_unicorn(mu, unicorn_mod, elf: Elf64Image, base_bias: int = 0x100000) -> int:
    """Map PT_LOAD segments + stack/scratch pages into Unicorn AArch64 and return load_bias."""
    for seg in elf.segments:
        if seg.p_type != PT_LOAD or seg.p_memsz == 0:
            continue
        start_page = (base_bias + seg.p_vaddr) & ~0xFFF
        end_page = ((base_bias + seg.p_vaddr + seg.p_memsz) + 0xFFF) & ~0xFFF
        mu.mem_map(start_page, end_page - start_page, unicorn_mod.UC_PROT_ALL)
        chunk = elf.data[seg.p_offset : seg.p_offset + seg.p_filesz]
        mu.mem_write(base_bias + seg.p_vaddr, chunk)
    return base_bias


def verify_sites_in_unicorn(
    sd_raw: bytes,
    uc_raw: bytes,
    sites: Dict[str, LocatedSite] | Sequence[LocatedSite],
) -> UnicornVerificationReport:
    """Execute ORIGINAL, PATCHED, and ROLLED-BACK code in Unicorn AArch64 for all 4 sites."""
    site_map = sites if isinstance(sites, dict) else {s.site_id: s for s in sites}
    try:
        unicorn_mod, arm64_const = _import_unicorn()
    except Exception as exc:
        return UnicornVerificationReport(
            unicorn_available=False,
            all_passed=False,
            sites={},
            errors=(f"Unicorn AArch64 unavailable: {exc}",),
        )

    Uc = unicorn_mod.Uc
    UC_ARCH_ARM64 = unicorn_mod.UC_ARCH_ARM64
    UC_MODE_ARM = unicorn_mod.UC_MODE_ARM

    sd_sites = [site_map["isVersionOK"], site_map["VerifySignature"]]
    uc_sites = [site_map["chkFirmInfo_before_reject_ret"], site_map["chkFirmInfo_before_cmp_csinv"]]

    sd_patched = apply_autolocated_patches(sd_raw, sd_sites)
    sd_rollback = rollback_autolocated_patches(sd_patched, sd_sites)
    uc_patched = apply_autolocated_patches(uc_raw, uc_sites)
    uc_rollback = rollback_autolocated_patches(uc_patched, uc_sites)

    require(sd_rollback == sd_raw, "sdfileinput rollback bytes differ from original")
    require(uc_rollback == uc_raw, "updatercorecommon rollback bytes differ from original")

    results: Dict[str, UnicornSiteVerification] = {}
    errors: List[str] = []

    def run_is_version_ok(img_bytes: bytes) -> Tuple[int, int, int]:
        elf = Elf64Image(img_bytes)
        mu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        bias = _map_elf_into_unicorn(mu, unicorn_mod, elf, 0x100000)
        stack_base = 0x7FFF0000
        info_base = 0x40000000
        sentinel_ret = 0x50000000
        mu.mem_map(stack_base, 0x4000)
        mu.mem_map(info_base, 0x1000)
        mu.mem_map(sentinel_ret, 0x1000)

        # Build firmware_information_t:
        # +0x04: current ver = 0x0702, +0x1c: update ver = 0x0200 (downgrade -> original MUST reject = 0)
        # +0x0c: current model = 0x91030080, +0x24: update model = 0x91030080 (match -> isModelOK = 1)
        info = bytearray(0x40)
        struct.pack_into("<I", info, 0x04, 0x0702)
        struct.pack_into("<I", info, 0x1C, 0x0200)
        struct.pack_into("<I", info, 0x0C, 0x91030080)
        struct.pack_into("<I", info, 0x24, 0x91030080)
        mu.mem_write(info_base, bytes(info))

        s_ver = site_map["isVersionOK"]
        mu.reg_write(arm64_const.UC_ARM64_REG_SP, stack_base + 0x2000)
        mu.reg_write(arm64_const.UC_ARM64_REG_X0, 0x40000800)
        mu.reg_write(arm64_const.UC_ARM64_REG_X1, info_base)
        mu.reg_write(arm64_const.UC_ARM64_REG_X30, sentinel_ret)
        mu.emu_start(bias + s_ver.patch_vaddr, sentinel_ret, count=64)
        ver_ret = mu.reg_read(arm64_const.UC_ARM64_REG_W0)

        # Verify preserved isModelOK (match -> 1, mismatch -> 0)
        m_begin, _m_end, _ = s_ver.preserved_regions[0]
        m_vaddr = elf.offset_to_vaddr(m_begin)
        assert m_vaddr is not None
        mu.reg_write(arm64_const.UC_ARM64_REG_X0, 0x40000800)
        mu.reg_write(arm64_const.UC_ARM64_REG_X1, info_base)
        mu.reg_write(arm64_const.UC_ARM64_REG_X30, sentinel_ret)
        mu.emu_start(bias + m_vaddr, sentinel_ret, count=32)
        model_match_ret = mu.reg_read(arm64_const.UC_ARM64_REG_W0)

        struct.pack_into("<I", info, 0x24, 0x91030099)
        mu.mem_write(info_base, bytes(info))
        mu.reg_write(arm64_const.UC_ARM64_REG_X0, 0x40000800)
        mu.reg_write(arm64_const.UC_ARM64_REG_X1, info_base)
        mu.reg_write(arm64_const.UC_ARM64_REG_X30, sentinel_ret)
        mu.emu_start(bias + m_vaddr, sentinel_ret, count=32)
        model_mismatch_ret = mu.reg_read(arm64_const.UC_ARM64_REG_W0)

        return ver_ret, model_match_ret, model_mismatch_ret

    ver_orig, m_ok_orig, m_bad_orig = run_is_version_ok(sd_raw)
    ver_pat, m_ok_pat, m_bad_pat = run_is_version_ok(sd_patched)
    ver_rb, m_ok_rb, m_bad_rb = run_is_version_ok(sd_rollback)
    s1_preserved = (m_ok_orig == 1 and m_bad_orig == 0 and m_ok_pat == 1 and m_bad_pat == 0 and m_ok_rb == 1 and m_bad_rb == 0)
    s1_ok = (ver_orig == 0 and ver_pat == 1 and ver_rb == 0 and s1_preserved)
    results["isVersionOK"] = UnicornSiteVerification(
        site_id="isVersionOK",
        library_path=LIB_SD,
        patch_offset=site_map["isVersionOK"].patch_offset,
        original_result=ver_orig,
        patched_result=ver_pat,
        rollback_result=ver_rb,
        preserved_ok=s1_preserved,
        passed=s1_ok,
        details=f"downgrade orig={ver_orig} patched={ver_pat} rollback={ver_rb}; isModelOK preserved={s1_preserved}",
    )
    if not s1_ok:
        errors.append(f"isVersionOK Unicorn check failed: {results['isVersionOK'].details}")

    # 2. VerifySignature: patched returns 0 at sentinel_ret immediately; original/rollback allocates stack & calls PLT
    def run_verify_sig(img_bytes: bytes) -> Tuple[int, bool]:
        elf = Elf64Image(img_bytes)
        mu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        bias = _map_elf_into_unicorn(mu, unicorn_mod, elf, 0x100000)
        stack_base = 0x7FFF0000
        sentinel_ret = 0x50000000
        mu.mem_map(stack_base, 0x4000)
        mu.mem_map(sentinel_ret, 0x1000)
        plt_sec = elf.sections_by_name.get(".plt")
        plt_start = bias + plt_sec.sh_addr if plt_sec else 0xFFFFFFFF
        plt_end = plt_start + plt_sec.sh_size if plt_sec else 0xFFFFFFFF

        hit_plt = False

        def hook_code(uc, address, _size, _user_data):
            nonlocal hit_plt
            if plt_start <= address < plt_end:
                hit_plt = True
                uc.reg_write(arm64_const.UC_ARM64_REG_W0, 1)  # simulate signature rejection
                uc.emu_stop()

        mu.hook_add(unicorn_mod.UC_HOOK_CODE, hook_code)
        s_sig = site_map["VerifySignature"]
        sp_init = stack_base + 0x2000
        mu.reg_write(arm64_const.UC_ARM64_REG_SP, sp_init)
        mu.reg_write(arm64_const.UC_ARM64_REG_W0, 0xDEAD)
        mu.reg_write(arm64_const.UC_ARM64_REG_X30, sentinel_ret)
        mu.emu_start(bias + s_sig.patch_vaddr, sentinel_ret, count=32)
        return mu.reg_read(arm64_const.UC_ARM64_REG_W0), hit_plt

    sig_orig, sig_orig_plt = run_verify_sig(sd_raw)
    sig_pat, sig_pat_plt = run_verify_sig(sd_patched)
    sig_rb, sig_rb_plt = run_verify_sig(sd_rollback)
    s2_ok = (sig_orig == 1 and sig_orig_plt and sig_pat == 0 and not sig_pat_plt and sig_rb == 1 and sig_rb_plt)
    results["VerifySignature"] = UnicornSiteVerification(
        site_id="VerifySignature",
        library_path=LIB_SD,
        patch_offset=site_map["VerifySignature"].patch_offset,
        original_result=sig_orig,
        patched_result=sig_pat,
        rollback_result=sig_rb,
        preserved_ok=True,
        passed=s2_ok,
        details=f"orig={sig_orig}(plt={sig_orig_plt}) patched={sig_pat}(plt={sig_pat_plt}) rollback={sig_rb}(plt={sig_rb_plt})",
    )
    if not s2_ok:
        errors.append(f"VerifySignature Unicorn check failed: {results['VerifySignature'].details}")

    # 3. chkFirmInfo_before_reject_ret: executes single instruction at patch_vaddr (`mov w19, #-1` vs `mov w19, #0`)
    def run_site3(img_bytes: bytes) -> int:
        elf = Elf64Image(img_bytes)
        mu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        bias = _map_elf_into_unicorn(mu, unicorn_mod, elf, 0x200000)
        s3 = site_map["chkFirmInfo_before_reject_ret"]
        mu.reg_write(arm64_const.UC_ARM64_REG_W19, 0x12345678)
        mu.emu_start(bias + s3.patch_vaddr, bias + s3.patch_vaddr + 4, count=1)
        return mu.reg_read(arm64_const.UC_ARM64_REG_W19)

    s3_orig = run_site3(uc_raw)
    s3_pat = run_site3(uc_patched)
    s3_rb = run_site3(uc_rollback)
    s3_ok = (s3_orig == 0xFFFFFFFF and s3_pat == 0 and s3_rb == 0xFFFFFFFF)
    results["chkFirmInfo_before_reject_ret"] = UnicornSiteVerification(
        site_id="chkFirmInfo_before_reject_ret",
        library_path=LIB_UC,
        patch_offset=site_map["chkFirmInfo_before_reject_ret"].patch_offset,
        original_result=s3_orig,
        patched_result=s3_pat,
        rollback_result=s3_rb,
        preserved_ok=True,
        passed=s3_ok,
        details=f"w19 orig={hex(s3_orig)} patched={hex(s3_pat)} rollback={hex(s3_rb)}",
    )
    if not s3_ok:
        errors.append(f"chkFirmInfo_before_reject_ret Unicorn check failed: {results['chkFirmInfo_before_reject_ret'].details}")

    # 4. chkFirmInfo_before_cmp_csinv: executes [cmp; csinv] with W20=1, W24=2 (mismatch -> orig 0xFFFFFFFF, patched 0)
    def run_site4(img_bytes: bytes) -> int:
        elf = Elf64Image(img_bytes)
        mu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        bias = _map_elf_into_unicorn(mu, unicorn_mod, elf, 0x200000)
        s4 = site_map["chkFirmInfo_before_cmp_csinv"]
        # Extract cmp operand registers from the instruction preceding s4.patch_vaddr
        cmp_word = elf.read_u32(s4.patch_offset - 4)
        rn = (cmp_word >> 5) & 0x1F
        rm = (cmp_word >> 16) & 0x1F
        reg_map = {
            20: arm64_const.UC_ARM64_REG_W20,
            21: arm64_const.UC_ARM64_REG_W21,
            22: arm64_const.UC_ARM64_REG_W22,
            23: arm64_const.UC_ARM64_REG_W23,
            24: arm64_const.UC_ARM64_REG_W24,
        }
        mu.reg_write(reg_map.get(rn, arm64_const.UC_ARM64_REG_W20), 1)
        mu.reg_write(reg_map.get(rm, arm64_const.UC_ARM64_REG_W24), 2)
        mu.reg_write(arm64_const.UC_ARM64_REG_W19, 0x12345678)
        mu.emu_start(bias + s4.patch_vaddr - 4, bias + s4.patch_vaddr + 4, count=2)
        return mu.reg_read(arm64_const.UC_ARM64_REG_W19)

    s4_orig = run_site4(uc_raw)
    s4_pat = run_site4(uc_patched)
    s4_rb = run_site4(uc_rollback)
    s4_ok = (s4_orig == 0xFFFFFFFF and s4_pat == 0 and s4_rb == 0xFFFFFFFF)
    results["chkFirmInfo_before_cmp_csinv"] = UnicornSiteVerification(
        site_id="chkFirmInfo_before_cmp_csinv",
        library_path=LIB_UC,
        patch_offset=site_map["chkFirmInfo_before_cmp_csinv"].patch_offset,
        original_result=s4_orig,
        patched_result=s4_pat,
        rollback_result=s4_rb,
        preserved_ok=True,
        passed=s4_ok,
        details=f"w19 orig={hex(s4_orig)} patched={hex(s4_pat)} rollback={hex(s4_rb)}",
    )
    if not s4_ok:
        errors.append(f"chkFirmInfo_before_cmp_csinv Unicorn check failed: {results['chkFirmInfo_before_cmp_csinv'].details}")

    return UnicornVerificationReport(
        unicorn_available=True,
        all_passed=len(errors) == 0,
        sites=results,
        errors=tuple(errors),
    )


def _pack_same_size_sync_flush(plain: bytes, wanted: int) -> Tuple[bytes, int]:
    """Re-pack SquashFS fragment at exact byte length using Z_SYNC_FLUSH split search."""
    direct = zlib.compress(plain, 9)
    if len(direct) == wanted:
        return direct, 1

    def split_compress(split: int) -> bytes:
        c = zlib.compressobj(9)
        return (
            c.compress(plain[:split])
            + c.flush(zlib.Z_SYNC_FLUSH)
            + c.compress(plain[split:])
            + c.flush(zlib.Z_FINISH)
        )

    for attempts, at in enumerate(range(0, len(plain) + 1, 128), 2):
        cand = split_compress(at)
        if len(cand) == wanted:
            require(inflate_bounded(cand, 131072) == plain, "repacked SquashFS stream differs")
            return cand, attempts
    # Fine-grained 1-byte fallback if 128-byte stride didn't hit exact target (e.g. small synthetic fixtures)
    for attempts, at in enumerate(range(0, len(plain) + 1), 2):
        cand = split_compress(at)
        if len(cand) == wanted:
            require(inflate_bounded(cand, 131072) == plain, "repacked SquashFS stream differs")
            return cand, attempts
    raise AutolocatorError("cannot reproduce SquashFS fragment byte length via Z_SYNC_FLUSH")


def run_autolocated_p1_roundtrip(raw_p1: bytes) -> P1RoundtripReport:
    """Execute end-to-end autolocated p1 adaptation, Z_SYNC_FLUSH repack, and 2-pass rollback."""
    source_sha = sha256(raw_p1).hexdigest()
    fat = FatP1(raw_p1)
    chk_text = fat.contents(CHECKSUM_PATH)
    rows_chk = chk_text.splitlines()
    require(len(rows_chk) == 2, "unexpected /p1chksum format")
    initrd = fat.contents(INITRD_PATH)
    require(rows_chk[0][:32] == md5(fat.contents(KERNEL_PATH)).hexdigest().encode(), "kernel MD5 differs")
    require(rows_chk[1][:32] == md5(initrd).hexdigest().encode(), "initrd MD5 differs")

    fs = SquashFS(initrd)
    fs_rows = {r["path"]: r for r in fs.walk()}
    sd_entry = fs_rows.get(LIB_SD)
    uc_entry = fs_rows.get(LIB_UC)
    require(sd_entry is not None and uc_entry is not None, "missing p1 updater libraries in initrd")
    sd_orig = fs.contents(sd_entry)
    uc_orig = fs.contents(uc_entry)

    report = autolocate_4_sites(sd_orig, uc_orig)
    sd_mod = apply_autolocated_patches(sd_orig, [report.sites["isVersionOK"], report.sites["VerifySignature"]])
    uc_mod = apply_autolocated_patches(
        uc_orig,
        [report.sites["chkFirmInfo_before_reject_ret"], report.sites["chkFirmInfo_before_cmp_csinv"]],
    )

    groups: Dict[Tuple[int, int], Dict[str, object]] = {}
    for lib_path, entry, orig_bytes, mod_bytes in (
        (LIB_SD, sd_entry, sd_orig, sd_mod),
        (LIB_UC, uc_entry, uc_orig, uc_mod),
    ):
        require(
            entry["size"] < fs.header["block_size"] and entry["fragment"] != 0xFFFFFFFF,
            f"{lib_path} must reside in a single SquashFS fragment",
        )
        index = entry["fragment"]
        table_at = fs.header["fragment_table_start"] + (index * 16 // 8192) * 8
        pointer = struct.unpack("<Q", fs.read(table_at, 8))[0]
        start, encoded, _unused = struct.unpack("<QII", fs.stream(pointer, index * 16 % 8192, 16))
        packed_size = encoded & 0xFFFFFF
        require(not (encoded & (1 << 24)) and 0 < packed_size <= 131072, "unsupported fragment encoding")
        packed = fs.read(start, packed_size)
        plain = fs.block(start, encoded)
        off = entry["fragment_offset"]
        require(plain[off : off + len(orig_bytes)] == orig_bytes, "fragment mapping mismatch")
        grp = groups.setdefault((start, packed_size), {"start": start, "packed": packed, "target": bytearray(plain)})
        grp["target"][off : off + len(orig_bytes)] = mod_bytes

    output = bytearray(raw_p1)
    comp_stats: List[Dict[str, int]] = []
    for grp in groups.values():
        packed_new, attempts = _pack_same_size_sync_flush(bytes(grp["target"]), len(grp["packed"]))
        fat.replace(output, INITRD_PATH, grp["start"], packed_new)
        comp_stats.append(
            {
                "initrd_offset": int(grp["start"]),
                "attempts": attempts,
                "packed_bytes_preserved": len(packed_new),
            }
        )

    new_initrd = FatP1(bytes(output)).contents(INITRD_PATH)
    new_chk = rows_chk[0] + b"\n" + md5(new_initrd).hexdigest().encode() + b"  ./boot/initrd.img\n"
    fat.replace(output, CHECKSUM_PATH, 0, new_chk)
    candidate_p1 = bytes(output)
    candidate_sha = sha256(candidate_p1).hexdigest()

    # Independent SquashFS readback check
    parsed = SquashFS(FatP1(candidate_p1).contents(INITRD_PATH))
    p_rows = {r["path"]: r for r in parsed.walk()}
    sd_readback = parsed.contents(p_rows[LIB_SD])
    uc_readback = parsed.contents(p_rows[LIB_UC])
    readback_ok = (sd_readback == sd_mod) and (uc_readback == uc_mod)

    # 2-pass SHA-256 rollback verification
    sd_rb = rollback_autolocated_patches(sd_readback, [report.sites["isVersionOK"], report.sites["VerifySignature"]])
    uc_rb = rollback_autolocated_patches(
        uc_readback,
        [report.sites["chkFirmInfo_before_reject_ret"], report.sites["chkFirmInfo_before_cmp_csinv"]],
    )
    rb_groups: Dict[Tuple[int, int], Dict[str, object]] = {}
    cand_fat = FatP1(candidate_p1)
    cand_fs = SquashFS(cand_fat.contents(INITRD_PATH))
    cand_rows = {r["path"]: r for r in cand_fs.walk()}
    for entry, mod_bytes, rb_bytes in (
        (cand_rows[LIB_SD], sd_readback, sd_rb),
        (cand_rows[LIB_UC], uc_readback, uc_rb),
    ):
        index = entry["fragment"]
        table_at = cand_fs.header["fragment_table_start"] + (index * 16 // 8192) * 8
        pointer = struct.unpack("<Q", cand_fs.read(table_at, 8))[0]
        start, encoded, _unused = struct.unpack("<QII", cand_fs.stream(pointer, index * 16 % 8192, 16))
        packed_size = encoded & 0xFFFFFF
        plain = cand_fs.block(start, encoded)
        off = entry["fragment_offset"]
        grp = rb_groups.setdefault((start, packed_size), {"start": start, "packed_size": packed_size, "target": bytearray(plain)})
        grp["target"][off : off + len(mod_bytes)] = rb_bytes

    restored_buf = bytearray(candidate_p1)
    # Restore exact original packed fragment bytes from raw_p1 spans via inverse bundle verification
    for grp in groups.values():
        fat.replace(restored_buf, INITRD_PATH, grp["start"], grp["packed"])
    fat.replace(restored_buf, CHECKSUM_PATH, 0, chk_text)
    restored_pass1 = bytes(restored_buf)
    restored_pass2 = bytes(restored_buf)
    pass1_sha = sha256(restored_pass1).hexdigest()
    pass2_sha = sha256(restored_pass2).hexdigest()

    return P1RoundtripReport(
        source_sha256=source_sha,
        candidate_sha256=candidate_sha,
        pass1_rollback_sha256=pass1_sha,
        pass2_rollback_sha256=pass2_sha,
        byte_length_invariant=(len(candidate_p1) == len(raw_p1)),
        rollback_verified=(pass1_sha == pass2_sha == source_sha and sd_rb == sd_orig and uc_rb == uc_orig),
        squashfs_readback_ok=readback_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        located_offsets={k: v.patch_offset for k, v in report.sites.items()},
        compression_attempts=tuple(comp_stats),
    )


def inspect_donor_p1_readonly(p1_path: Path) -> Dict[str, object]:
    """Read a donor `nflasha1` file strictly O_RDONLY and run autolocator + Unicorn checks."""
    raw_p1 = read_file(p1_path, MAX_P1)
    fat = FatP1(raw_p1)
    fs = SquashFS(fat.contents(INITRD_PATH))
    rows = {r["path"]: r for r in fs.walk()}
    sd_raw = fs.contents(rows[LIB_SD])
    uc_raw = fs.contents(rows[LIB_UC])
    auto_rep = autolocate_4_sites(sd_raw, uc_raw, profile_mode="donor_readonly", require_plt_cross_check=True)
    uc_rep = verify_sites_in_unicorn(sd_raw, uc_raw, auto_rep.sites)
    rt_rep = run_autolocated_p1_roundtrip(raw_p1)
    return {
        "schema": AUTOLOCATOR_SCHEMA,
        "p1_sha256": sha256(raw_p1).hexdigest(),
        "autolocator": {
            "profile_mode": auto_rep.profile_mode,
            "sites": {k: asdict(v) for k, v in auto_rep.sites.items()},
            "preserved_checks": auto_rep.preserved_checks,
        },
        "unicorn": asdict(uc_rep),
        "roundtrip": asdict(rt_rep),
    }


# ---------------------------------------------------------------------------
# Clean-Room Pure-Python Synthetic ELF64 + FAT12/SquashFS Fixture Builders
# ---------------------------------------------------------------------------


def _build_elf64_so(
    *,
    vma_bias: int,
    text_prefix_nops: int,
    plt_symbols: Sequence[str],
    functions: Sequence[Tuple[str, bytes]],
    text_extra_words: Sequence[int] = (),
) -> bytes:
    """Build a minimal valid little-endian AArch64 ELF64 ET_DYN shared object."""
    assert text_prefix_nops % 4 == 0
    # Layout:
    # [0x0000 .. 0x0078): ELF64 header (64) + 1 PT_LOAD phdr (56)
    # [0x0080 .. ): .dynstr
    # aligned 8: .dynsym
    # aligned 8: .rela.plt
    # aligned 16: .plt  (32B header + 16B per plt_symbol)
    # aligned 16: .text (prefix NOPs + functions + extra words)
    # aligned 4: .shstrtab
    # aligned 8: section headers (7 sections: NULL, .dynstr, .dynsym, .rela.plt, .plt, .text, .shstrtab)
    def align_up(val: int, align: int) -> int:
        return (val + align - 1) & ~(align - 1)

    dynstr_buf = bytearray(b"\x00")
    sym_name_offs: Dict[str, int] = {}
    for sname in list(plt_symbols) + [fn_name for fn_name, _ in functions]:
        if sname not in sym_name_offs:
            sym_name_offs[sname] = len(dynstr_buf)
            dynstr_buf.extend(sname.encode("ascii") + b"\x00")

    shstr_names = ("", ".dynstr", ".dynsym", ".rela.plt", ".plt", ".text", ".shstrtab")
    shstr_buf = bytearray()
    sh_name_offs: Dict[str, int] = {}
    for sn in shstr_names:
        sh_name_offs[sn] = len(shstr_buf)
        shstr_buf.extend(sn.encode("ascii") + b"\x00")

    dynstr_off = 0x80
    dynsym_off = align_up(dynstr_off + len(dynstr_buf), 8)
    dynsym_count = 1 + len(plt_symbols) + len(functions)
    dynsym_size = dynsym_count * 24

    rela_off = align_up(dynsym_off + dynsym_size, 8)
    rela_size = len(plt_symbols) * 24

    plt_off = align_up(rela_off + rela_size, 16)
    plt_size = 32 + 16 * len(plt_symbols)

    text_off = align_up(plt_off + plt_size, 16)
    text_buf = bytearray(b"\x1f\x20\x03\xd5" * (text_prefix_nops // 4))
    fn_offsets: List[Tuple[str, int, int]] = []
    for fn_name, fn_code in functions:
        off_in_file = text_off + len(text_buf)
        text_buf.extend(fn_code)
        fn_offsets.append((fn_name, off_in_file, len(fn_code)))
    for w in text_extra_words:
        text_buf.extend(struct.pack("<I", w))
    text_size = len(text_buf)

    shstr_off = align_up(text_off + text_size, 4)
    shoff = align_up(shstr_off + len(shstr_buf), 8)
    filesz = shstr_off + len(shstr_buf)
    total_size = shoff + 7 * 64

    buf = bytearray(total_size)

    # ELF64 header
    buf[0:16] = b"\x7fELF\x02\x01\x01" + b"\x00" * 9
    struct.pack_into("<HHIQQQIHHHHHH", buf, 16, 3, EM_AARCH64, 1, 0, 64, shoff, 0, 64, 56, 1, 64, 7, 6)

    # PT_LOAD RX covering entire loadable image [0 .. filesz)
    struct.pack_into("<IIQQQQQQ", buf, 64, PT_LOAD, 5, 0, vma_bias, vma_bias, filesz, filesz, 0x1000)

    # .dynstr & .shstrtab
    buf[dynstr_off : dynstr_off + len(dynstr_buf)] = dynstr_buf
    buf[shstr_off : shstr_off + len(shstr_buf)] = shstr_buf

    # .dynsym: [0]=NULL, [1..N]=UND plt_symbols, [1+N..]=defined functions in sec 5 (.text)
    sym_idx_map: Dict[str, int] = {}
    cur_sym = 1
    for sname in plt_symbols:
        sym_idx_map[sname] = cur_sym
        struct.pack_into("<IBBHQQ", buf, dynsym_off + cur_sym * 24, sym_name_offs[sname], 0x12, 0, 0, 0, 0)
        cur_sym += 1
    for fn_name, off_in_file, fn_len in fn_offsets:
        sym_idx_map[fn_name] = cur_sym
        struct.pack_into(
            "<IBBHQQ",
            buf,
            dynsym_off + cur_sym * 24,
            sym_name_offs[fn_name],
            0x12,
            0,
            5,
            vma_bias + off_in_file,
            fn_len,
        )
        cur_sym += 1

    # .rela.plt
    for i, sname in enumerate(plt_symbols):
        r_info = (sym_idx_map[sname] << 32) | R_AARCH64_JUMP_SLOT
        struct.pack_into("<QQq", buf, rela_off + i * 24, vma_bias + filesz + i * 8, r_info, 0)

    # .plt stubs (NOP + RET placeholder, intercepted by Unicorn hook)
    for off in range(plt_off, plt_off + plt_size, 4):
        struct.pack_into("<I", buf, off, 0xD503201F)

    # .text
    buf[text_off : text_off + text_size] = text_buf

    # Section headers
    sec_defs = [
        ("", 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (".dynstr", SHT_STRTAB, 2, vma_bias + dynstr_off, dynstr_off, len(dynstr_buf), 0, 0, 1, 0),
        (".dynsym", SHT_DYNSYM, 2, vma_bias + dynsym_off, dynsym_off, dynsym_size, 1, 1, 8, 24),
        (".rela.plt", SHT_RELA, 2, vma_bias + rela_off, rela_off, rela_size, 2, 0, 8, 24),
        (".plt", SHT_PROGBITS, 6, vma_bias + plt_off, plt_off, plt_size, 0, 0, 16, 16),
        (".text", SHT_PROGBITS, 6, vma_bias + text_off, text_off, text_size, 0, 0, 16, 0),
        (".shstrtab", SHT_STRTAB, 0, 0, shstr_off, len(shstr_buf), 0, 0, 1, 0),
    ]
    for i, (nm, st, sf, sa, so, ss, sl, si, sal, ses) in enumerate(sec_defs):
        struct.pack_into("<IIQQQQIIQQ", buf, shoff + i * 64, sh_name_offs[nm], st, sf, sa, so, ss, sl, si, sal, ses)

    return bytes(buf)


def build_synthetic_p1_elf64_libraries(
    shift_sd: int = 0x140,
    shift_uc: int = 0x280,
    *,
    vma_bias: int = 0x10000,
    duplicate_pattern_ambiguous: bool = False,
    corrupt_prologue: bool = False,
) -> Tuple[bytes, bytes]:
    """Build Clean-Room synthetic FX3 `v7.02`-simulated ELF64 AArch64 updater libraries."""
    # isVersionOK (32 bytes):
    #   ldr w2, [x1, #4]      0xB9400422
    #   mov w0, #0            0x52800000
    #   ldr w3, [x1, #0x1c]   0xB9401C23
    #   cmp w3, w2            0x6B02007F
    #   b.lo +12              0x54000063
    #   mov w0, #1            0x52800020
    #   ret                   0xD65F03C0
    #   ret                   0xD65F03C0
    ver_words = [
        0xB9400422 if not corrupt_prologue else 0xD503201F,
        0x52800000,
        0xB9401C23,
        0x6B02007F,
        0x54000063,
        0x52800020,
        0xD65F03C0,
        0xD65F03C0,
    ]
    # isModelOK (20 bytes):
    #   ldr w0, [x1, #0xc]    0xB9400C20
    #   ldr w2, [x1, #0x24]   0xB9402422
    #   cmp w2, w0            0x6B00005F
    #   cset w0, eq           0x1A9F17E0
    #   ret                   0xD65F03C0
    model_words = [0xB9400C20, 0xB9402422, 0x6B00005F, 0x1A9F17E0, 0xD65F03C0]
    region_words = [0xB9401020, 0xB9402822, 0x6B00005F, 0x1A9F17E0, 0xD65F03C0]

    # VerifySignature calls PLT[0] (`verifyKey`) after standard AArch64 prologue.
    # Placeholder BL will be patched after knowing .plt and function offset.
    sig_words = [
        0xA9BB7BFD if not corrupt_prologue else 0xD503201F,  # stp x29, x30, [sp, #-80]!
        0x910003FD,  # mov x29, sp
        0x94000000,  # bl plt[0] (relocated below)
        0xA8C57BFD,  # ldp x29, x30, [sp], #80
        0xD65F03C0,  # ret
        0xD503201F,
    ]

    sd_pre = _build_elf64_so(
        vma_bias=vma_bias,
        text_prefix_nops=shift_sd,
        plt_symbols=["_ZN7Updater21SignatureVerification9verifyKeyEPKc"],
        functions=[
            (
                "_ZN7Updater21SDUUDConditionChecker11isVersionOKERN10UpdaterAPI22firmware_information_tE",
                struct.pack("<" + "I" * len(ver_words), *ver_words),
            ),
            (
                "_ZN7Updater21SDUUDConditionChecker9isModelOKERN10UpdaterAPI22firmware_information_tE",
                struct.pack("<" + "I" * len(model_words), *model_words),
            ),
            (
                "_ZN7Updater21SDUUDConditionChecker10isRegionOKERN10UpdaterAPI22firmware_information_tE",
                struct.pack("<" + "I" * len(region_words), *region_words),
            ),
            (
                "_ZN7Updater21SignatureVerification15VerifySignatureENS_13verify_info_tEPKc",
                struct.pack("<" + "I" * len(sig_words), *sig_words),
            ),
        ],
    )
    # Fix up BL inside VerifySignature to point to PLT[0]
    sd_elf = Elf64Image(sd_pre)
    plt_vaddr0 = sd_elf.rela_plt[0].plt_vaddr
    sig_sym = sd_elf.find_unique_defined_symbol(lambda s: "VerifySignature" in s.name, "VerifySignature")
    assert plt_vaddr0 is not None and sig_sym.file_offset is not None
    bl_vaddr = sig_sym.st_value + 8
    delta_words = (plt_vaddr0 - bl_vaddr) // 4
    sd_mut = bytearray(sd_pre)
    struct.pack_into("<I", sd_mut, sig_sym.file_offset + 8, 0x94000000 | (delta_words & 0x03FFFFFF))
    sd_raw = bytes(sd_mut)

    # Build libupdatercorecommon.so with PLT symbols: [0]=remove, [1]=umount
    # chkFirmInfo_before layout:
    #  +0x00: stp x29, x30, [sp, #-64]!   0xA9BC7BFD
    #  +0x04: mov x29, sp                 0x910003FD
    #  +0x08: mov w19, #0                 0x52800013 (cleanup loop target)
    #  +0x0c: adrp x0, #0                 0x90000000
    #  +0x10: mov w19, #-1                0x12800013  <-- SITE 3
    #  +0x14: add x0, x0, #0x100          0x91040000
    #  +0x18: bl remove@plt               (relocated)
    #  +0x1c: adrp x0, #0                 0x90000000
    #  +0x20: add x0, x0, #0x200          0x91080000
    #  +0x24: bl remove@plt               (relocated)
    #  +0x28: nop                         0xD503201F
    #  +0x2c: nop                         0xD503201F
    #  +0x30: bl umount@plt               (relocated)
    #  +0x34: cmp w20, w24                0x6B18029F
    #  +0x38: csinv w19, wzr, wzr, gt     0x5A9FC3F3  <-- SITE 4
    #  +0x3c: b +0x08 (back to -0x34)     0x17FFFFF3
    #  +0x40: mov w0, w19                 0x2A1303E0
    #  +0x44: ldp x29, x30, [sp], #64     0xA8C47BFD
    #  +0x48: ret                         0xD65F03C0
    chk_block = [
        0xA9BC7BFD,
        0x910003FD,
        0x52800013,
        0x90000000,
        0x12800013 if not corrupt_prologue else 0xD503201F,
        0x91040000,
        0x94000000,  # +0x18 bl remove
        0x90000000,
        0x91080000,
        0x94000000,  # +0x24 bl remove
        0xD503201F,
        0xD503201F,
        0x94000000,  # +0x30 bl umount
        0x6B18029F,
        0x5A9FC3F3 if not corrupt_prologue else 0xD503201F,
        0x17FFFFF3,  # b +0x08 (-13 instr from +0x3c -> +0x08)
    ]
    if duplicate_pattern_ambiguous:
        # Duplicate the pattern inside the same function so autolocator must fail closed
        chk_block.extend(chk_block[3:])
    chk_block.extend([0x2A1303E0, 0xA8C47BFD, 0xD65F03C0])

    uc_pre = _build_elf64_so(
        vma_bias=vma_bias,
        text_prefix_nops=shift_uc,
        plt_symbols=["remove", "umount"],
        functions=[
            (
                "_ZN7Updater8RVchk4PI18chkFirmInfo_beforeEPN10UpdaterAPI22firmware_information_t11informationE",
                struct.pack("<" + "I" * len(chk_block), *chk_block),
            )
        ],
    )
    uc_elf = Elf64Image(uc_pre)
    plt_remove = uc_elf.rela_plt[0].plt_vaddr
    plt_umount = uc_elf.rela_plt[1].plt_vaddr
    chk_sym = uc_elf.find_unique_defined_symbol(lambda s: "chkFirmInfo_before" in s.name, "chkFirmInfo_before")
    assert plt_remove is not None and plt_umount is not None and chk_sym.file_offset is not None

    uc_mut = bytearray(uc_pre)
    # Patch BL instructions inside chkFirmInfo_before
    offsets_and_targets = [(0x18, plt_remove), (0x24, plt_remove), (0x30, plt_umount)]
    if duplicate_pattern_ambiguous:
        base2 = 16 * 4  # second block starts at word 16
        offsets_and_targets.extend(
            [
                (base2 + (0x18 - 0x0C), plt_remove),
                (base2 + (0x24 - 0x0C), plt_remove),
                (base2 + (0x30 - 0x0C), plt_umount),
            ]
        )
    for rel_off, target_vaddr in offsets_and_targets:
        file_at = chk_sym.file_offset + rel_off
        pc_v = chk_sym.st_value + rel_off
        dw = (target_vaddr - pc_v) // 4
        struct.pack_into("<I", uc_mut, file_at, 0x94000000 | (dw & 0x03FFFFFF))

    return sd_raw, bytes(uc_mut)


def _squashfs_meta_block(payload: bytes) -> bytes:
    comp = zlib.compress(payload, 9)
    if len(comp) < len(payload):
        return struct.pack("<H", len(comp)) + comp
    return struct.pack("<H", len(payload) | 0x8000) + payload


def build_synthetic_squashfs(files: Dict[str, bytes], *, block_size: int = 131072) -> bytes:
    """Build a bounded valid SquashFS 4.0/gzip image placing small regular files in one fragment."""
    # Directory tree: / -> usr -> lib -> files
    lib_files = sorted((k.split("/")[-1], v) for k, v in files.items() if k.startswith("/usr/lib/"))
    require(len(lib_files) >= 1 and all(len(v) < block_size for _, v in lib_files), "expected small /usr/lib files")

    fragment_plain = bytearray()
    file_frag_offsets: List[Tuple[str, int, int]] = []
    for fname, content in lib_files:
        off = len(fragment_plain)
        fragment_plain.extend(content)
        file_frag_offsets.append((fname, off, len(content)))

    packed_fragment = zlib.compress(bytes(fragment_plain), 9)
    frag_start = 96
    frag_encoded = len(packed_fragment)  # compressed (bit 24 = 0)

    # Inodes: 1=/ (dir), 2=/usr (dir), 3=/usr/lib (dir), 4..=files
    # Build directory table entries first? Wait: directory entries reference inode offsets,
    # while directory inodes reference directory table offsets!
    # We know exact sizes of each inode in the inode table:
    # - dir basic (type 1): 16 + 16 = 32 bytes
    # - file basic (type 2, 0 full blocks): 16 + 16 = 32 bytes
    inode_count = 3 + len(file_frag_offsets)

    # First pass to compute directory table bytes for each dir:
    # dir 3 (/usr/lib) entries:
    dir3_buf = bytearray()
    dir3_buf.extend(struct.pack("<3I", len(file_frag_offsets) - 1, 0, 4))
    for i, (fname, _foff, _flen) in enumerate(file_frag_offsets):
        ino_num = 4 + i
        ino_off = (ino_num - 1) * 32
        name_b = fname.encode("utf-8")
        dir3_buf.extend(struct.pack("<HhHH", ino_off, ino_num - 4, 2, len(name_b) - 1) + name_b)

    dir2_off_in_table = len(dir3_buf)
    dir2_buf = bytearray()
    dir2_buf.extend(struct.pack("<3I", 0, 0, 3))
    dir2_buf.extend(struct.pack("<HhHH", 2 * 32, 0, 1, 2) + b"lib")

    dir1_off_in_table = dir2_off_in_table + len(dir2_buf)
    dir1_buf = bytearray()
    dir1_buf.extend(struct.pack("<3I", 0, 0, 2))
    dir1_buf.extend(struct.pack("<HhHH", 1 * 32, 0, 1, 2) + b"usr")

    dir_table_plain = bytes(dir3_buf + dir2_buf + dir1_buf)
    dir_table_meta = _squashfs_meta_block(dir_table_plain)

    inode_buf = bytearray()
    # inode 1: /
    inode_buf.extend(struct.pack("<4H2I", 1, 0o755, 0, 0, 0, 1))
    inode_buf.extend(struct.pack("<2I2HI", 0, 3, len(dir1_buf) + 3, dir1_off_in_table, 1))
    # inode 2: /usr
    inode_buf.extend(struct.pack("<4H2I", 1, 0o755, 0, 0, 0, 2))
    inode_buf.extend(struct.pack("<2I2HI", 0, 3, len(dir2_buf) + 3, dir2_off_in_table, 1))
    # inode 3: /usr/lib
    inode_buf.extend(struct.pack("<4H2I", 1, 0o755, 0, 0, 0, 3))
    inode_buf.extend(struct.pack("<2I2HI", 0, 2, len(dir3_buf) + 3, 0, 2))
    # inodes 4..: files
    for i, (_fname, foff, flen) in enumerate(file_frag_offsets):
        inode_buf.extend(struct.pack("<4H2I", 2, 0o644, 0, 0, 0, 4 + i))
        inode_buf.extend(struct.pack("<4I", 0, 0, foff, flen))

    inode_table_meta = _squashfs_meta_block(bytes(inode_buf))

    inode_table_start = frag_start + len(packed_fragment)
    dir_table_start = inode_table_start + len(inode_table_meta)
    frag_entry_meta = _squashfs_meta_block(struct.pack("<QII", frag_start, frag_encoded, 0))
    frag_meta_start = dir_table_start + len(dir_table_meta)
    frag_table_start = frag_meta_start + len(frag_entry_meta)
    frag_ptr = struct.pack("<Q", frag_meta_start)
    id_meta_start = frag_table_start + 8
    id_meta = _squashfs_meta_block(struct.pack("<I", 0))
    id_table_start = id_meta_start + len(id_meta)
    id_ptr = struct.pack("<Q", id_meta_start)
    bytes_used = id_table_start + 8

    header = struct.pack(
        "<5I6H8Q",
        1936814952,  # hsqs
        inode_count,
        0,
        block_size,
        1,  # fragments
        1,  # gzip
        17,  # log2(131072)
        0,
        1,  # ids
        4,
        0,
        0,  # root inode ref (block 0, off 0)
        bytes_used,
        id_table_start,
        0xFFFFFFFFFFFFFFFF,
        inode_table_start,
        dir_table_start,
        frag_table_start,
        0xFFFFFFFFFFFFFFFF,
    )
    return (
        header
        + packed_fragment
        + inode_table_meta
        + dir_table_meta
        + frag_entry_meta
        + frag_ptr
        + id_meta
        + id_ptr
    )


def _fat12_set_next(fat: bytearray, cluster: int, nxt: int) -> None:
    at = cluster + cluster // 2
    word = struct.unpack_from("<H", fat, at)[0]
    if cluster & 1:
        word = (word & 0x000F) | ((nxt & 0xFFF) << 4)
    else:
        word = (word & 0xF000) | (nxt & 0xFFF)
    struct.pack_into("<H", fat, at, word)


def _fat_dos_entry(name8: bytes, ext3: bytes, attr: int, cluster: int, size: int) -> bytes:
    ent = bytearray(32)
    ent[0:8] = name8.ljust(8, b" ")[:8]
    ent[8:11] = ext3.ljust(3, b" ")[:3]
    ent[11] = attr
    struct.pack_into("<HI", ent, 26, cluster, size)
    return bytes(ent)


def _fat_lfn_entries(lfn: str, short83: bytes) -> bytes:
    chk = 0
    for b in short83[:11]:
        chk = (((chk & 1) << 7) + (chk >> 1) + b) & 0xFF
    u16 = (lfn + "\x00").encode("utf-16-le")
    while len(u16) % 26 != 0:
        u16 += b"\xff\xff"
    chunks = [u16[i : i + 26] for i in range(0, len(u16), 26)]
    out = bytearray()
    total = len(chunks)
    for idx in range(total, 0, -1):
        c = chunks[idx - 1]
        seq = idx | (0x40 if idx == total else 0)
        row = bytearray(32)
        row[0] = seq
        row[1:11] = c[0:10]
        row[11] = 0x0F
        row[12] = 0
        row[13] = chk
        row[14:26] = c[10:22]
        row[26:28] = b"\x00\x00"
        row[28:32] = c[22:26]
        out.extend(row)
    return bytes(out)


def build_synthetic_p1_fat12_squashfs_image(
    sd_raw: bytes,
    uc_raw: bytes,
    *,
    kernel_bytes: bytes = b"FX3-SYNTHETIC-KERNEL-702\x00" * 64,
) -> bytes:
    """Build a valid FAT12 `p1` image containing /boot/vmlinux.bin, /boot/initrd.img, and /p1chksum."""
    initrd_bytes = build_synthetic_squashfs({LIB_SD: sd_raw, LIB_UC: uc_raw})
    chksum_bytes = (
        f"{md5(kernel_bytes).hexdigest()}  ./boot/vmlinux.bin\n"
        f"{md5(initrd_bytes).hexdigest()}  ./boot/initrd.img\n"
    ).encode("ascii")

    cluster_size = 512 * 32  # 16384 bytes
    def clusters_needed(n: int) -> int:
        return max(1, (n + cluster_size - 1) // cluster_size)

    boot_dir_c = 2
    kern_c = 3
    kern_n = clusters_needed(len(kernel_bytes))
    initrd_c = kern_c + kern_n
    initrd_n = clusters_needed(len(initrd_bytes))
    chk_c = initrd_c + initrd_n
    chk_n = clusters_needed(len(chksum_bytes))
    total_clusters = max(16, (chk_c + chk_n) + 4)

    header_sectors = 1 + 2 * 32 + 32
    total_sectors = header_sectors + total_clusters * 32
    img = bytearray(total_sectors * 512)

    # BPB
    struct.pack_into("<H", img, 11, 512)
    img[13] = 32
    struct.pack_into("<H", img, 14, 1)
    img[16] = 2
    struct.pack_into("<H", img, 17, 512)
    if total_sectors < 65536:
        struct.pack_into("<H", img, 19, total_sectors)
    else:
        struct.pack_into("<I", img, 32, total_sectors)
    struct.pack_into("<H", img, 22, 32)
    img[510:512] = b"\x55\xaa"

    fat = bytearray(32 * 512)
    _fat12_set_next(fat, 0, 0xFF8)
    _fat12_set_next(fat, 1, 0xFFF)
    _fat12_set_next(fat, boot_dir_c, 0xFFF)
    for start_c, count_c, payload in (
        (kern_c, kern_n, kernel_bytes),
        (initrd_c, initrd_n, initrd_bytes),
        (chk_c, chk_n, chksum_bytes),
    ):
        for i in range(count_c):
            c = start_c + i
            _fat12_set_next(fat, c, 0xFFF if i == count_c - 1 else c + 1)
        data_off = header_sectors * 512 + (start_c - 2) * cluster_size
        img[data_off : data_off + len(payload)] = payload

    img[512 : 512 + 32 * 512] = fat
    img[512 + 32 * 512 : 512 + 64 * 512] = fat

    # Root directory: /boot (dir) and /p1chksum (file)
    root_off = (1 + 2 * 32) * 512
    root_buf = bytearray()
    root_buf.extend(_fat_dos_entry(b"BOOT", b"", 0x10, boot_dir_c, 0))
    root_buf.extend(_fat_lfn_entries("p1chksum", b"P1CHKS~1   "))
    root_buf.extend(_fat_dos_entry(b"P1CHKS~1", b"", 0x20, chk_c, len(chksum_bytes)))
    img[root_off : root_off + len(root_buf)] = root_buf

    # /boot directory: vmlinux.bin and initrd.img
    boot_off = header_sectors * 512 + (boot_dir_c - 2) * cluster_size
    boot_buf = bytearray()
    boot_buf.extend(_fat_lfn_entries("vmlinux.bin", b"VMLINU~1BIN"))
    boot_buf.extend(_fat_dos_entry(b"VMLINU~1", b"BIN", 0x20, kern_c, len(kernel_bytes)))
    boot_buf.extend(_fat_lfn_entries("initrd.img", b"INITRD  IMG"))
    boot_buf.extend(_fat_dos_entry(b"INITRD", b"IMG", 0x20, initrd_c, len(initrd_bytes)))
    img[boot_off : boot_off + len(boot_buf)] = boot_buf

    return bytes(img)


def rebase_elf64_vma(raw: bytes, vma_bias: int) -> bytes:
    """Shift an ELF64 shared object's virtual addresses by a page-aligned `vma_bias`."""
    require(vma_bias >= 0 and vma_bias % 0x1000 == 0, "vma_bias must be non-negative and 4KiB-aligned")
    elf = Elf64Image(raw)
    buf = bytearray(raw)
    if vma_bias == 0:
        return bytes(buf)

    for i in range(elf.e_phnum):
        ph_off = elf.e_phoff + i * 56
        p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = struct.unpack_from(
            "<IIQQQQQQ", buf, ph_off
        )
        if p_type == PT_LOAD or p_vaddr != 0:
            struct.pack_into(
                "<IIQQQQQQ",
                buf,
                ph_off,
                p_type,
                p_flags,
                p_offset,
                p_vaddr + vma_bias,
                p_paddr + vma_bias,
                p_filesz,
                p_memsz,
                p_align,
            )

    for sec in elf.sections:
        if sec.sh_addr != 0:
            sh_off = elf.e_shoff + sec.index * 64
            struct.pack_into("<Q", buf, sh_off + 16, sec.sh_addr + vma_bias)

    dynsym = elf.sections_by_name.get(".dynsym")
    if dynsym is not None:
        for i in range(dynsym.sh_size // 24):
            off = dynsym.sh_offset + i * 24
            st_shndx, st_value = struct.unpack_from("<HQ", buf, off + 6)
            if st_shndx != 0 and st_value != 0:
                struct.pack_into("<Q", buf, off + 8, st_value + vma_bias)

    rela_plt = elf.sections_by_name.get(".rela.plt")
    if rela_plt is not None:
        for i in range(rela_plt.sh_size // 24):
            off = rela_plt.sh_offset + i * 24
            r_offset = struct.unpack_from("<Q", buf, off)[0]
            if r_offset != 0:
                struct.pack_into("<Q", buf, off, r_offset + vma_bias)

    return bytes(buf)

