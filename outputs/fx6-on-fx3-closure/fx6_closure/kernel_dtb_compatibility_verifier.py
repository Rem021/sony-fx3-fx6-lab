"""Phase 8 — Flattened Device Tree (`cxd90057.dtb`) SoC Compatibility & `.ko` `vermagic` / `__versions` Verifier.

Covers two independent embedded Linux kernel compatibility verification dimensions across read-only
FX3 7.02 and FX6 6.01 donors:

- **Dimension A (Pure-Python Flattened Device Tree `0xd00dfeed` Parser & `cxd90057.dtb` SoC Audit)**:
  1. Implements a dependency-free Devicetree Specification v0.4 binary FDT (`0xd00dfeed`) parser
     validating big-endian header bounds (`totalsize`, `off_dt_struct`, `off_dt_strings`,
     `off_mem_rsvmap`, `version >= 16`, `last_comp_version <= version`), non-overlapping structural
     regions, 4-byte/8-byte alignment, `/memreserve/` sentinel termination, balanced
     `FDT_BEGIN_NODE` / `FDT_END_NODE` / `FDT_PROP` / `FDT_NOP` / `FDT_END` token streams, and
     bounds-checked string table offsets.
  2. Audits FX3 `cxd90057.dtb` (`17,131 B`) against FX6 `cxd90057.dtb` (`17,131 B`), `loadaddr.txt`
     (`48 B`), and `kemco.txt` (`934 B` vs `933 B`), proving **100% byte-for-byte DTB identity**
     across all 68 FDT nodes and 493 properties (`cxd,cxd90057`, 4x Cortex-A35, `memory@400000000`,
     static `iomap` apertures `/esram@0xfe000000` + `/iomem*`, `/pcie_ep_dummy` `phandle=0x7`,
     `arm,gic-400`, 5x `arm,pl011` UARTs, `arasan,sdhci` eMMC, and 5x `snps,dw-pcie` / `cxd900xx-pcie-ep`
     IPC endpoints), 100% `loadaddr.txt` identity, and 100% identity across all 7 `kemco.txt`
     `memrsv=` DDR carveouts (documenting the exact 2-line `ramdisk_size` / `initrd` ceiling delta).

- **Dimension B (Kernel Module `.modinfo` `vermagic` & `__versions` `modversion_info` CRC Verifier)**:
  1. Parses ELF64 `ET_REL` (`EM_AARCH64`) `.modinfo` (`vermagic`, `name`, `depends`, `author`,
     `license`), `.gnu.linkonce.this_module` (`768 B` `struct module`), `.note.gnu.build-id`,
     `__versions` (`struct modversion_info`: 64-byte `(uint64 LE crc, char name[56])` records),
     `.symtab` (`SHN_UNDEF` imports), and `__ksymtab_strings` (`EXPORT_SYMBOL` exports).
  2. Audits all 9 FX3 host `.ko` modules (`backup.ko`, `devno.ko`, `osal_uipc.ko`, `osal_ulogio.ko`,
     `osal_utm.ko`, `stream.ko`, `udate.ko`, `upm.ko`, `utimer.ko`) alongside FX6 `p15`/`p3` and
     `p1`-initrd `.ko` modules, proving that Sony builds `4.9.337-scel+` with `!CONFIG_MODVERSIONS`,
     proving that applying `P9` (`upm.ko` `.text+0x136b8`) preserves 100% of `.modinfo` (`vermagic`),
     `.gnu.linkonce.this_module`, `SHN_UNDEF` / `__ksymtab` symbols, and 100% of 64-byte `__versions`
     `modversion_info` CRCs (verified on both native and `CONFIG_MODVERSIONS`-instrumented `upm.ko`),
     and quantifying the exact cross-kernel `vermagic` (`4.9.186-scel` on `p1`) and `SHN_UNDEF`
     (`Backup_sync_subsystem_for_senser_local`, `pcie_link_width_check_dev_state_ch0`) hazards that
     mandate keeping FX3's native host `.ko` stack + P9-adapted FX3 `upm.ko`.
"""

from __future__ import annotations

import hashlib
import re
import struct
import zlib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .backup_mount_tolerance_verifier import (
    DEFAULT_COLOR_PORT_WORK_DIR,
    DEFAULT_FX6_TEAM_DIR,
)
from .patcher import (
    DEFAULT_FX3_MODULES_DIR,
    P9_UPM_KO_SPEC,
    apply_patch_spec,
    rollback_patch_spec,
)


# Clean read-only donor DTB, boot parameter & kernel module paths
DEFAULT_FX3_FAT_MEMBERS_DIR = DEFAULT_COLOR_PORT_WORK_DIR / "input-20261028" / "fat-members"
DEFAULT_FX3_DTB_PATH = (
    DEFAULT_FX3_FAT_MEMBERS_DIR
    / "87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca-cxd90057.dtb"
)
DEFAULT_FX3_LOADADDR_TXT_PATH = (
    DEFAULT_FX3_FAT_MEMBERS_DIR
    / "8c7cc8eb65c40311172f4bf1dc591fe3bcbc1efe689ededdd225142139881452-loadaddr.txt"
)
DEFAULT_FX3_KEMCO_TXT_PATH = (
    DEFAULT_FX3_FAT_MEMBERS_DIR
    / "eb184157afc8eaf2d9a3dc795e7b52057130cb25f7799bc72fd6c85cbb99c94a-kemco.txt"
)

DEFAULT_FX6_BOOT_DIR = DEFAULT_FX6_TEAM_DIR / "donor" / "fat-files" / "nflasha1" / "boot"
DEFAULT_FX6_DTB_PATH = DEFAULT_FX6_BOOT_DIR / "cxd90057.dtb"
DEFAULT_FX6_LOADADDR_TXT_PATH = DEFAULT_FX6_BOOT_DIR / "loadaddr.txt"
DEFAULT_FX6_KEMCO_TXT_PATH = DEFAULT_FX6_BOOT_DIR / "kemco.txt"

DEFAULT_FX6_P15_KMOD_DIR = DEFAULT_FX6_TEAM_DIR / "donor" / "nflasha15-files" / "kmod"
DEFAULT_FX6_P3_INITRD_KMOD_DIR = (
    DEFAULT_FX6_TEAM_DIR / "donor" / "nested-files" / "nflasha3-initrd" / "kmod"
)
DEFAULT_FX6_P1_INITRD_DIR = DEFAULT_FX6_TEAM_DIR / "donor" / "nested-files" / "nflasha1-initrd"

# Pinned SHA-256 digests
PINNED_CXD90057_DTB_SHA256 = "87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca"
PINNED_LOADADDR_TXT_SHA256 = "8c7cc8eb65c40311172f4bf1dc591fe3bcbc1efe689ededdd225142139881452"
PINNED_FX3_KEMCO_TXT_SHA256 = "eb184157afc8eaf2d9a3dc795e7b52057130cb25f7799bc72fd6c85cbb99c94a"
PINNED_FX6_P1_KEMCO_TXT_SHA256 = "e7763ad93a721f297670f13abc452cf467c0d2c344888d4e55ead2440c295950"

PINNED_FX3_HOST_KO_SHA256: Dict[str, str] = {
    "backup.ko": "8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d",
    "devno.ko": "cca1d9acd87a718c7742d168ea0de402b01a7c04cd40433ff2ca4071150dbc23",
    "osal_uipc.ko": "6aa0f5c8c72f5f6cf9aa9c905fc3f3f75b8bea0dfebaf13deb632b0de088eb38",
    "osal_ulogio.ko": "dd65dfdcd086085a3359ceaddb0049f1f6b962f6ca25a2a8bc6cdfe9a45da672",
    "osal_utm.ko": "f6679c6481adaa0cffb5e27dbf949f5d8168ca4200f4cb245e900544977b5f1c",
    "stream.ko": "38cadfaf7851fe571e715368b5e62cb99a5261b406b89bb0c200cac6ee12098b",
    "udate.ko": "a3cbb9977915259a5a9d5e16e49adbb58f26c43d2ad2c63381c60e1103d205bb",
    "upm.ko": "ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e",
    "utimer.ko": "4274003013e03caf83bd1e6108209566a97d417d09812daebc31519c01c18d5c",
}

EXPECTED_HOST_VERMAGIC = "4.9.337-scel+ SMP preempt mod_unload aarch64"
EXPECTED_P1_UPDATER_VERMAGIC = "4.9.186-scel SMP preempt mod_unload aarch64"

# Devicetree Specification v0.4 constants
FDT_MAGIC = 0xD00DFEED
FDT_HEADER_BYTES = 40
FDT_MIN_VERSION = 16
FDT_BEGIN_NODE = 0x00000001
FDT_END_NODE = 0x00000002
FDT_PROP = 0x00000003
FDT_NOP = 0x00000004
FDT_END = 0x00000009

EXPECTED_KEMCO_MEMRSV_CARVEOUTS: Tuple[Tuple[int, int, bool], ...] = (
    (0x400000000, 0x00001000, False),
    (0x400020000, 0x00060000, False),
    (0x403E00000, 0x00200000, True),
    (0x404000000, 0x02000000, False),
    (0x410000000, 0x00200000, False),
    (0x410200000, 0x01E00000, True),
    (0x47C000000, 0x04000000, True),
)

# ELF64 / Linux `struct modversion_info` constants
ELF_MAGIC = b"\x7fELF"
ELFCLASS64 = 2
ELFDATA2LSB = 1
ET_REL = 1
EM_AARCH64 = 183
SHT_PROGBITS = 1
SHT_SYMTAB = 2
SHT_STRTAB = 3
SHF_ALLOC = 0x2
MODVERSION_ENTRY_BYTES = 64
MODVERSION_NAME_MAX_BYTES = 56
THIS_MODULE_MIN_BYTES = 80
THIS_MODULE_NAME_OFFSET = 24
THIS_MODULE_NAME_MAX_BYTES = 56
SYNTHETIC_MODULE_LAYOUT_CRC = 0x67A19E4B


class FdtFormatError(ValueError):
    """Raised when a Flattened Device Tree (`0xd00dfeed`) binary violates the FDT specification."""


class KoModuleFormatError(ValueError):
    """Raised when an ELF64 `.ko` module fails `.modinfo`, `vermagic`, or `__versions` integrity."""


@dataclass(frozen=True)
class FdtHeader:
    magic: int
    totalsize: int
    off_dt_struct: int
    off_dt_strings: int
    off_mem_rsvmap: int
    version: int
    last_comp_version: int
    boot_cpuid_phys: int
    size_dt_strings: int
    size_dt_struct: int


@dataclass(frozen=True)
class FdtReserveEntry:
    address: int
    size: int


@dataclass(frozen=True)
class FdtNode:
    path: str
    unit_name: str
    properties: Tuple[Tuple[str, bytes], ...]

    def prop_dict(self) -> Dict[str, bytes]:
        return dict(self.properties)


@dataclass(frozen=True)
class ParsedFdtBlob:
    header: FdtHeader
    mem_rsvmap: Tuple[FdtReserveEntry, ...]
    nodes: Tuple[FdtNode, ...]
    total_property_count: int

    def node_map(self) -> Dict[str, FdtNode]:
        return {n.path: n for n in self.nodes}


@dataclass(frozen=True)
class KemcoMemrsvEntry:
    base_addr: int
    size_bytes: int
    uncached: bool


@dataclass(frozen=True)
class KemcoBootargsAudit:
    valid: bool
    sha256: str
    total_lines: int
    ramdisk_size_kib: int
    initrd_base_addr: int
    initrd_size_bytes: int
    mem_limit: str
    boottime_spec: str
    klog_addr: int
    klog_size: int
    memrsv_entries: Tuple[KemcoMemrsvEntry, ...]
    memrsv_zero_overlap: bool


@dataclass(frozen=True)
class SocHardwareSummary:
    root_compatible: Tuple[str, ...]
    root_model: str
    chosen_stdout_path: str
    chosen_has_inline_bootargs: bool
    memory_base_addr: int
    memory_size_bytes: int
    has_reserved_memory_node: bool
    static_iomap_regions: Tuple[Tuple[str, int, int], ...]
    pcie_ep_dummy_carveout: Tuple[int, int, int]
    cpu_count: int
    cpu_compatible: Tuple[str, ...]
    gic_compatible: Tuple[str, ...]
    gic_mmio_windows: Tuple[Tuple[int, int], ...]
    uart_nodes: Tuple[Tuple[str, int, int, int], ...]
    emmc_compatible: Tuple[str, ...]
    pcie_rc_nodes: Tuple[str, ...]
    pcie_ep_ipc_nodes: Tuple[str, ...]


@dataclass(frozen=True)
class DimensionADtbCompatibilityReport:
    all_checks_passed: bool
    fx3_dtb_sha256_verified: bool
    fx6_dtb_sha256_verified: bool
    dtb_byte_identical: bool
    fdt_node_count: int
    fdt_property_count: int
    node_or_property_diff_count: int
    loadaddr_txt_identical: bool
    loadaddr_quad: Tuple[int, int, int, int]
    soc_summary: SocHardwareSummary
    fx3_kemco_audit: KemcoBootargsAudit
    fx6_p1_kemco_audit: KemcoBootargsAudit
    kemco_memrsv_identical: bool
    kemco_diff_keys: Tuple[str, ...]


@dataclass(frozen=True)
class ModversionEntry:
    symbol: str
    crc: int


@dataclass(frozen=True)
class KoModuleAudit:
    module_filename: str
    sha256: str
    size_bytes: int
    build_id_hex: str
    this_module_name: str
    this_module_sha256: str
    modinfo_sha256: str
    vermagic: str
    depends: Tuple[str, ...]
    license_str: str
    author_str: str
    has_modversions_flag: bool
    has_versions_section: bool
    module_layout_crc: Optional[int]
    modversions: Tuple[ModversionEntry, ...]
    undef_symbols: Tuple[str, ...]
    exported_ksymtab_symbols: Tuple[str, ...]


@dataclass(frozen=True)
class P9KoIntegrityCheck:
    valid: bool
    donor_sha256: str
    patched_sha256: str
    rollback_sha256_matched: bool
    vermagic_preserved: bool
    modinfo_sha256_preserved: bool
    this_module_sha256_preserved: bool
    undef_symbols_preserved: bool
    exported_symbols_preserved: bool
    native_modversions_preserved: bool
    synthetic_modversions_count: int
    synthetic_modversions_100pct_preserved: bool


@dataclass(frozen=True)
class CrossKernelModuleComparison:
    module_filename: str
    fx3_vermagic: str
    fx6_runtime_vermagic: str
    fx6_p1_vermagic: Optional[str]
    vermagic_runtime_equal: bool
    vermagic_p1_mismatch_detected: bool
    fx3_undef_count: int
    fx6_undef_count: int
    only_fx3_undef: Tuple[str, ...]
    only_fx6_undef: Tuple[str, ...]
    only_fx3_exports: Tuple[str, ...]
    only_fx6_exports: Tuple[str, ...]
    symbol_abi_identical: bool


@dataclass(frozen=True)
class DimensionBKoIntegrityReport:
    all_checks_passed: bool
    fx3_host_module_count: int
    fx3_all_sha256_verified: bool
    fx3_uniform_vermagic_verified: bool
    fx3_depends_dag_closed: bool
    sony_config_modversions_enabled: bool
    p9_upm_integrity: P9KoIntegrityCheck
    cross_kernel_comparisons: Tuple[CrossKernelModuleComparison, ...]
    identical_abi_module_count: int
    divergent_abi_modules: Tuple[str, ...]
    p1_vermagic_mismatch_count: int


@dataclass(frozen=True)
class Phase8KernelDtbReport:
    all_checks_passed: bool
    dimension_a_dtb: DimensionADtbCompatibilityReport
    dimension_b_ko: DimensionBKoIntegrityReport


def _decode_fdt_strlist(raw: bytes) -> Tuple[str, ...]:
    if not raw or not raw.endswith(b"\x00"):
        raise FdtFormatError(f"Invalid FDT stringlist property: {raw!r}")
    return tuple(part.decode("ascii") for part in raw[:-1].split(b"\x00"))


def parse_fdt_blob(raw: bytes) -> ParsedFdtBlob:
    """Parse and strictly validate a big-endian Flattened Device Tree (`0xd00dfeed`) binary."""
    if len(raw) < FDT_HEADER_BYTES:
        raise FdtFormatError(f"FDT buffer too short ({len(raw)} B < {FDT_HEADER_BYTES} B)")

    (
        magic,
        totalsize,
        off_dt_struct,
        off_dt_strings,
        off_mem_rsvmap,
        version,
        last_comp_version,
        boot_cpuid_phys,
        size_dt_strings,
        size_dt_struct,
    ) = struct.unpack_from(">10I", raw, 0)

    if magic != FDT_MAGIC:
        raise FdtFormatError(f"Invalid FDT magic 0x{magic:08x} (expected 0x{FDT_MAGIC:08x})")
    if totalsize < FDT_HEADER_BYTES or totalsize > len(raw):
        raise FdtFormatError(f"Truncated or invalid FDT totalsize {totalsize} (buffer has {len(raw)} B)")
    if version < FDT_MIN_VERSION or last_comp_version > version:
        raise FdtFormatError(f"Unsupported FDT version ({version}, last_comp={last_comp_version})")
    if off_mem_rsvmap < FDT_HEADER_BYTES or (off_mem_rsvmap % 8) != 0 or off_mem_rsvmap + 16 > totalsize:
        raise FdtFormatError(f"Invalid off_mem_rsvmap 0x{off_mem_rsvmap:x}")
    if off_dt_struct < FDT_HEADER_BYTES or (off_dt_struct % 4) != 0 or (size_dt_struct % 4) != 0 or size_dt_struct < 4:
        raise FdtFormatError(
            f"Unaligned or invalid dt_struct region (off=0x{off_dt_struct:x}, size=0x{size_dt_struct:x})"
        )
    if off_dt_struct + size_dt_struct > totalsize:
        raise FdtFormatError("dt_struct region exceeds totalsize")
    if off_dt_strings < FDT_HEADER_BYTES or off_dt_strings + size_dt_strings > totalsize:
        raise FdtFormatError("dt_strings region exceeds totalsize")

    # Parse /memreserve/ block until (0, 0) sentinel
    rsv_entries: List[FdtReserveEntry] = []
    rsv_pos = off_mem_rsvmap
    found_rsv_sentinel = False
    while rsv_pos + 16 <= totalsize:
        addr, sz = struct.unpack_from(">QQ", raw, rsv_pos)
        rsv_pos += 16
        if addr == 0 and sz == 0:
            found_rsv_sentinel = True
            break
        rsv_entries.append(FdtReserveEntry(address=addr, size=sz))
    if not found_rsv_sentinel:
        raise FdtFormatError("Unterminated FDT mem_rsvmap block (missing 16-byte zero sentinel)")

    # Verify non-overlap across mem_rsvmap, dt_struct, and dt_strings
    regions = sorted(
        (
            (off_mem_rsvmap, rsv_pos, "mem_rsvmap"),
            (off_dt_struct, off_dt_struct + size_dt_struct, "dt_struct"),
            (off_dt_strings, off_dt_strings + size_dt_strings, "dt_strings"),
        ),
        key=lambda item: item[0],
    )
    for idx in range(len(regions) - 1):
        a_start, a_end, a_name = regions[idx]
        b_start, b_end, b_name = regions[idx + 1]
        if a_end > b_start:
            raise FdtFormatError(
                f"Overlapping FDT blocks {a_name} [0x{a_start:x}, 0x{a_end:x}) and "
                f"{b_name} [0x{b_start:x}, 0x{b_end:x})"
            )

    # Parse dt_struct token stream
    struct_end = off_dt_struct + size_dt_struct
    strings_base = off_dt_strings
    strings_end = off_dt_strings + size_dt_strings

    pos = off_dt_struct
    stack: List[str] = []
    node_order: List[str] = []
    node_units: Dict[str, str] = {}
    node_props: Dict[str, List[Tuple[str, bytes]]] = {}
    saw_root = False
    saw_end_token = False
    total_props = 0

    while pos < struct_end:
        if pos + 4 > struct_end:
            raise FdtFormatError("Truncated FDT token word")
        tok = struct.unpack_from(">I", raw, pos)[0]
        pos += 4

        if tok == FDT_NOP:
            continue

        if tok == FDT_BEGIN_NODE:
            if saw_end_token:
                raise FdtFormatError("FDT_BEGIN_NODE encountered after FDT_END")
            nul_pos = raw.find(b"\x00", pos, struct_end)
            if nul_pos == -1:
                raise FdtFormatError("Unterminated node unit name in FDT_BEGIN_NODE")
            unit_name = raw[pos:nul_pos].decode("ascii")
            next_pos = (nul_pos + 1 + 3) & ~3
            if next_pos > struct_end:
                raise FdtFormatError("FDT_BEGIN_NODE alignment exceeds dt_struct")
            if any(b != 0 for b in raw[nul_pos + 1 : next_pos]):
                raise FdtFormatError("Non-zero padding bytes in FDT_BEGIN_NODE")
            pos = next_pos

            if not stack:
                if saw_root or unit_name != "":
                    raise FdtFormatError(f"Root FDT node must have empty unit name, got {unit_name!r}")
                saw_root = True
                full_path = "/"
            else:
                if not unit_name:
                    raise FdtFormatError("Nested FDT node cannot have empty unit name")
                parent = stack[-1]
                full_path = f"/{unit_name}" if parent == "/" else f"{parent}/{unit_name}"

            if full_path in node_props:
                raise FdtFormatError(f"Duplicate FDT node path {full_path!r}")
            stack.append(full_path)
            node_order.append(full_path)
            node_units[full_path] = unit_name
            node_props[full_path] = []

        elif tok == FDT_END_NODE:
            if not stack:
                raise FdtFormatError("FDT_END_NODE stack underflow")
            stack.pop()

        elif tok == FDT_PROP:
            if not stack:
                raise FdtFormatError("FDT_PROP encountered outside any open FDT node")
            if pos + 8 > struct_end:
                raise FdtFormatError("Truncated FDT_PROP header")
            plen, nameoff = struct.unpack_from(">II", raw, pos)
            pos += 8
            val_end = pos + plen
            aligned_end = (val_end + 3) & ~3
            if aligned_end > struct_end:
                raise FdtFormatError("FDT_PROP value exceeds dt_struct bounds")
            if any(b != 0 for b in raw[val_end:aligned_end]):
                raise FdtFormatError("Non-zero padding bytes in FDT_PROP value")
            val_bytes = raw[pos:val_end]
            pos = aligned_end

            if nameoff >= size_dt_strings:
                raise FdtFormatError(
                    f"Out-of-bounds FDT_PROP nameoff 0x{nameoff:x} (size_dt_strings=0x{size_dt_strings:x})"
                )
            s_nul = raw.find(b"\x00", strings_base + nameoff, strings_end)
            if s_nul == -1:
                raise FdtFormatError(f"Unterminated property name at nameoff 0x{nameoff:x}")
            prop_name = raw[strings_base + nameoff : s_nul].decode("ascii")
            if not prop_name:
                raise FdtFormatError("Empty property name in FDT_PROP")

            node_props[stack[-1]].append((prop_name, val_bytes))
            total_props += 1

        elif tok == FDT_END:
            if stack:
                raise FdtFormatError(f"FDT_END encountered while {len(stack)} node(s) remain open")
            if not saw_root:
                raise FdtFormatError("FDT_END encountered without root node")
            saw_end_token = True
            # Any trailing words inside size_dt_struct must be FDT_NOP only
            while pos < struct_end:
                trailing = struct.unpack_from(">I", raw, pos)[0]
                if trailing != FDT_NOP:
                    raise FdtFormatError(f"Unexpected trailing token 0x{trailing:08x} after FDT_END")
                pos += 4
            break

        else:
            raise FdtFormatError(f"Unknown or unaligned FDT token 0x{tok:08x} at offset 0x{pos - 4:x}")

    if not saw_end_token:
        raise FdtFormatError("Missing terminating FDT_END (0x00000009) token in dt_struct")

    hdr = FdtHeader(
        magic=magic,
        totalsize=totalsize,
        off_dt_struct=off_dt_struct,
        off_dt_strings=off_dt_strings,
        off_mem_rsvmap=off_mem_rsvmap,
        version=version,
        last_comp_version=last_comp_version,
        boot_cpuid_phys=boot_cpuid_phys,
        size_dt_strings=size_dt_strings,
        size_dt_struct=size_dt_struct,
    )
    nodes = tuple(
        FdtNode(path=p, unit_name=node_units[p], properties=tuple(node_props[p])) for p in node_order
    )
    return ParsedFdtBlob(
        header=hdr,
        mem_rsvmap=tuple(rsv_entries),
        nodes=nodes,
        total_property_count=total_props,
    )


def parse_kemco_bootargs(text: str, raw_sha256: str) -> KemcoBootargsAudit:
    """Parse Sony `kemco.txt` kernel bootargs and verify pairwise 0-byte `memrsv=` carveout overlap."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    ramdisk_kib = 0
    initrd_base = 0
    initrd_size = 0
    mem_limit = ""
    boottime_spec = ""
    klog_addr = 0
    klog_size = 0
    memrsv: List[KemcoMemrsvEntry] = []

    for ln in lines:
        for tok in ln.split():
            if tok.startswith("ramdisk_size="):
                ramdisk_kib = int(tok.split("=", 1)[1], 10)
            elif tok.startswith("initrd="):
                b_s, sz_s = tok.split("=", 1)[1].split(",", 1)
                initrd_base = int(b_s, 16)
                initrd_size = int(sz_s, 16)
            elif tok.startswith("mem="):
                mem_limit = tok.split("=", 1)[1]
            elif tok.startswith("boottime="):
                boottime_spec = tok.split("=", 1)[1]
            elif tok.startswith("klog.addr="):
                klog_addr = int(tok.split("=", 1)[1], 16)
            elif tok.startswith("klog.size="):
                klog_size = int(tok.split("=", 1)[1], 16)
            elif tok.startswith("memrsv="):
                spec = tok.split("=", 1)[1]
                uc_flag = spec.endswith(":uc")
                if uc_flag:
                    spec = spec[:-3]
                sz_hex, addr_hex = spec.split("@", 1)
                memrsv.append(
                    KemcoMemrsvEntry(
                        base_addr=int(addr_hex, 16),
                        size_bytes=int(sz_hex, 16),
                        uncached=uc_flag,
                    )
                )

    sorted_rsv = sorted(memrsv, key=lambda r: r.base_addr)
    zero_overlap = len(sorted_rsv) > 0
    for i in range(len(sorted_rsv) - 1):
        if sorted_rsv[i].base_addr + sorted_rsv[i].size_bytes > sorted_rsv[i + 1].base_addr:
            zero_overlap = False

    valid = (
        lines[0] == "kemco"
        and lines[-1] == "*"
        and ramdisk_kib > 0
        and initrd_base == 0x408000000
        and initrd_size > 0
        and mem_limit == "2G"
        and zero_overlap
    )
    return KemcoBootargsAudit(
        valid=valid,
        sha256=raw_sha256,
        total_lines=len(lines),
        ramdisk_size_kib=ramdisk_kib,
        initrd_base_addr=initrd_base,
        initrd_size_bytes=initrd_size,
        mem_limit=mem_limit,
        boottime_spec=boottime_spec,
        klog_addr=klog_addr,
        klog_size=klog_size,
        memrsv_entries=tuple(memrsv),
        memrsv_zero_overlap=zero_overlap,
    )


def _extract_soc_summary(fdt: ParsedFdtBlob) -> SocHardwareSummary:
    nmap = fdt.node_map()
    root_p = nmap["/"].prop_dict()
    chosen_p = nmap["/chosen"].prop_dict()
    mem_p = nmap["/memory@400000000"].prop_dict()
    mem_base, mem_size = struct.unpack(">QQ", mem_p["reg"])

    iomaps: List[Tuple[str, int, int]] = []
    for path in ("/esram@0xfe000000", "/iomem@0xf0000000", "/iomem2@0xf0000000"):
        ip = nmap[path].prop_dict()
        phys = struct.unpack(">Q", ip["phys"])[0]
        sz = struct.unpack(">Q", ip["size"])[0]
        iomaps.append((path, phys, sz))

    ep_dummy_p = nmap["/pcie_ep_dummy"].prop_dict()
    ep_base, ep_sz = struct.unpack(">QQ", ep_dummy_p["reg"])
    ep_phandle = struct.unpack(">I", ep_dummy_p["phandle"])[0]

    cpu_nodes = [n for n in fdt.nodes if re.fullmatch(r"/cpus/cpu@\d+", n.path)]
    cpu_compat = _decode_fdt_strlist(cpu_nodes[0].prop_dict()["compatible"])

    gic_p = nmap["/interrupt-controller@f13A0000"].prop_dict()
    gic_compat = _decode_fdt_strlist(gic_p["compatible"])
    gic_reg = gic_p["reg"]
    gic_wins = tuple(
        struct.unpack_from(">QQ", gic_reg, off) for off in range(0, len(gic_reg), 16)
    )

    uarts: List[Tuple[str, int, int, int]] = []
    for n in fdt.nodes:
        if n.path.startswith("/soc/serial@"):
            up = n.prop_dict()
            u_base, u_sz = struct.unpack(">QQ", up["reg"])
            _, irq_spi, _ = struct.unpack(">III", up["interrupts"])
            uarts.append((n.path, u_base, u_sz, irq_spi))

    emmc_compat = _decode_fdt_strlist(nmap["/soc/emmc0"].prop_dict()["compatible"])
    pcie_rc = tuple(
        n.path
        for n in fdt.nodes
        if n.path.startswith("/soc/pcie_")
        and "/" not in n.path[len("/soc/") :]
        and not n.path.endswith("_ep")
    )
    pcie_ep = tuple(
        n.path
        for n in fdt.nodes
        if n.path.startswith("/soc/pcie_") and n.path.endswith("_ep")
    )

    return SocHardwareSummary(
        root_compatible=_decode_fdt_strlist(root_p["compatible"]),
        root_model=_decode_fdt_strlist(root_p["model"])[0],
        chosen_stdout_path=_decode_fdt_strlist(chosen_p["stdout-path"])[0],
        chosen_has_inline_bootargs=("bootargs" in chosen_p),
        memory_base_addr=mem_base,
        memory_size_bytes=mem_size,
        has_reserved_memory_node=("/reserved-memory" in nmap),
        static_iomap_regions=tuple(iomaps),
        pcie_ep_dummy_carveout=(ep_phandle, ep_base, ep_sz),
        cpu_count=len(cpu_nodes),
        cpu_compatible=cpu_compat,
        gic_compatible=gic_compat,
        gic_mmio_windows=gic_wins,
        uart_nodes=tuple(uarts),
        emmc_compatible=emmc_compat,
        pcie_rc_nodes=pcie_rc,
        pcie_ep_ipc_nodes=pcie_ep,
    )


def audit_dtb_soc_compatibility(
    fx3_dtb_path: Path = DEFAULT_FX3_DTB_PATH,
    fx6_dtb_path: Path = DEFAULT_FX6_DTB_PATH,
    fx3_loadaddr_path: Path = DEFAULT_FX3_LOADADDR_TXT_PATH,
    fx6_loadaddr_path: Path = DEFAULT_FX6_LOADADDR_TXT_PATH,
    fx3_kemco_path: Path = DEFAULT_FX3_KEMCO_TXT_PATH,
    fx6_kemco_path: Path = DEFAULT_FX6_KEMCO_TXT_PATH,
) -> DimensionADtbCompatibilityReport:
    """Audit FX3 vs FX6 `cxd90057.dtb`, `loadaddr.txt`, and `kemco.txt` SoC & carveout compatibility."""
    fx3_dtb_raw = fx3_dtb_path.read_bytes()
    fx6_dtb_raw = fx6_dtb_path.read_bytes()
    fx3_la_raw = fx3_loadaddr_path.read_bytes()
    fx6_la_raw = fx6_loadaddr_path.read_bytes()
    fx3_km_raw = fx3_kemco_path.read_bytes()
    fx6_km_raw = fx6_kemco_path.read_bytes()

    fx3_dtb_sha_ok = hashlib.sha256(fx3_dtb_raw).hexdigest() == PINNED_CXD90057_DTB_SHA256
    fx6_dtb_sha_ok = hashlib.sha256(fx6_dtb_raw).hexdigest() == PINNED_CXD90057_DTB_SHA256
    dtb_identical = fx3_dtb_raw == fx6_dtb_raw

    fdt3 = parse_fdt_blob(fx3_dtb_raw)
    fdt6 = parse_fdt_blob(fx6_dtb_raw)

    map3 = fdt3.node_map()
    map6 = fdt6.node_map()
    diff_cnt = 0
    for path in sorted(set(map3) | set(map6)):
        if path not in map3 or path not in map6:
            diff_cnt += 1
            continue
        p3 = map3[path].prop_dict()
        p6 = map6[path].prop_dict()
        for k in set(p3) | set(p6):
            if p3.get(k) != p6.get(k):
                diff_cnt += 1

    la_ok = (
        hashlib.sha256(fx3_la_raw).hexdigest() == PINNED_LOADADDR_TXT_SHA256
        and fx3_la_raw == fx6_la_raw
    )
    la_parts = tuple(int(x.strip(), 16) for x in fx3_la_raw.decode("ascii").strip().split(","))
    assert len(la_parts) == 4
    la_quad: Tuple[int, int, int, int] = (la_parts[0], la_parts[1], la_parts[2], la_parts[3])

    soc = _extract_soc_summary(fdt3)
    soc_ok = (
        soc.root_compatible == ("cxd,cxd90057",)
        and soc.root_model == "CXD90057"
        and soc.chosen_stdout_path == "serial0:460800n8"
        and not soc.chosen_has_inline_bootargs
        and soc.memory_base_addr == 0x400000000
        and soc.memory_size_bytes == 0x200000000
        and soc.pcie_ep_dummy_carveout == (0x7, 0x400000000, 0x1000)
        and soc.cpu_count == 4
        and soc.cpu_compatible == ("arm,cortex-a35", "arm,armv8")
        and soc.gic_compatible == ("arm,gic-400",)
        and len(soc.gic_mmio_windows) == 4
        and len(soc.uart_nodes) == 5
        and soc.emmc_compatible == ("arasan,sdhci",)
        and len(soc.pcie_rc_nodes) == 5
        and len(soc.pcie_ep_ipc_nodes) == 5
    )

    km3_sha = hashlib.sha256(fx3_km_raw).hexdigest()
    km6_sha = hashlib.sha256(fx6_km_raw).hexdigest()
    km3_audit = parse_kemco_bootargs(fx3_km_raw.decode("utf-8"), km3_sha)
    km6_audit = parse_kemco_bootargs(fx6_km_raw.decode("utf-8"), km6_sha)

    expected_rsv_objs = tuple(
        KemcoMemrsvEntry(base_addr=a, size_bytes=s, uncached=u)
        for a, s, u in EXPECTED_KEMCO_MEMRSV_CARVEOUTS
    )
    memrsv_eq = (
        km3_audit.memrsv_entries == km6_audit.memrsv_entries
        and km3_audit.memrsv_entries == expected_rsv_objs
    )

    km3_lines = [ln.strip() for ln in fx3_km_raw.decode("utf-8").splitlines() if ln.strip()]
    km6_lines = [ln.strip() for ln in fx6_km_raw.decode("utf-8").splitlines() if ln.strip()]
    diff_keys: List[str] = []
    for l3, l6 in zip(km3_lines, km6_lines):
        if l3 != l6:
            diff_keys.append(l3.split("=", 1)[0])

    all_ok = (
        fx3_dtb_sha_ok
        and fx6_dtb_sha_ok
        and dtb_identical
        and fdt3.header.totalsize == 17131
        and len(fdt3.nodes) == 68
        and diff_cnt == 0
        and la_ok
        and la_quad == (0x400080000, 0x408000000, 0x400001000, 0x400002000)
        and soc_ok
        and km3_sha == PINNED_FX3_KEMCO_TXT_SHA256
        and km6_sha == PINNED_FX6_P1_KEMCO_TXT_SHA256
        and km3_audit.valid
        and km6_audit.valid
        and memrsv_eq
        and tuple(diff_keys) == ("ramdisk_size", "initrd")
    )

    return DimensionADtbCompatibilityReport(
        all_checks_passed=all_ok,
        fx3_dtb_sha256_verified=fx3_dtb_sha_ok,
        fx6_dtb_sha256_verified=fx6_dtb_sha_ok,
        dtb_byte_identical=dtb_identical,
        fdt_node_count=len(fdt3.nodes),
        fdt_property_count=fdt3.total_property_count,
        node_or_property_diff_count=diff_cnt,
        loadaddr_txt_identical=la_ok,
        loadaddr_quad=la_quad,
        soc_summary=soc,
        fx3_kemco_audit=km3_audit,
        fx6_p1_kemco_audit=km6_audit,
        kemco_memrsv_identical=memrsv_eq,
        kemco_diff_keys=tuple(diff_keys),
    )


def parse_and_audit_ko_module(
    raw: bytes,
    module_filename: str = "<memory.ko>",
    *,
    expected_vermagic: Optional[str] = None,
    expected_module_layout_crc: Optional[int] = None,
) -> KoModuleAudit:
    """Parse ELF64 `ET_REL` `.ko` `.modinfo` (`vermagic`), `this_module`, `__versions` CRCs, and symbols."""
    if len(raw) < 64 or raw[:4] != ELF_MAGIC or raw[4] != ELFCLASS64 or raw[5] != ELFDATA2LSB:
        raise KoModuleFormatError(f"{module_filename}: Not a valid 64-bit little-endian ELF image")

    e_type, e_machine = struct.unpack_from("<HH", raw, 16)
    if e_type != ET_REL or e_machine != EM_AARCH64:
        raise KoModuleFormatError(
            f"{module_filename}: Expected ET_REL/EM_AARCH64 (1/183), got ({e_type}/{e_machine})"
        )

    e_shoff = struct.unpack_from("<Q", raw, 40)[0]
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", raw, 58)
    if e_shentsize < 64 or e_shnum == 0 or e_shstrndx >= e_shnum:
        raise KoModuleFormatError(f"{module_filename}: Invalid ELF64 section header table metadata")
    if e_shoff + e_shnum * e_shentsize > len(raw):
        raise KoModuleFormatError(f"{module_filename}: Truncated ELF64 section header table")

    shdrs = [struct.unpack_from("<IIQQQQIIQQ", raw, e_shoff + i * e_shentsize) for i in range(e_shnum)]
    shstr_off, shstr_sz = shdrs[e_shstrndx][4], shdrs[e_shstrndx][5]
    if shstr_off + shstr_sz > len(raw):
        raise KoModuleFormatError(f"{module_filename}: Out-of-bounds .shstrtab section")
    shstr = raw[shstr_off : shstr_off + shstr_sz]

    sec_map: Dict[str, Tuple[int, int, Tuple[int, ...]]] = {}
    for sh in shdrs:
        noff = sh[0]
        if noff >= len(shstr):
            raise KoModuleFormatError(f"{module_filename}: Section name offset out of bounds")
        end = shstr.find(b"\x00", noff)
        if end == -1:
            raise KoModuleFormatError(f"{module_filename}: Unterminated section name in .shstrtab")
        sname = shstr[noff:end].decode("ascii")
        s_off, s_sz, s_type = sh[4], sh[5], sh[1]
        if s_type != 8 and s_off + s_sz > len(raw):  # 8 == SHT_NOBITS
            raise KoModuleFormatError(f"{module_filename}: Section {sname!r} exceeds file bounds")
        sec_map[sname] = (s_off, s_sz, sh)

    # 1. Parse `.modinfo`
    if ".modinfo" not in sec_map:
        raise KoModuleFormatError(f"{module_filename}: Missing required .modinfo section")
    mi_off, mi_sz, _ = sec_map[".modinfo"]
    mi_bytes = raw[mi_off : mi_off + mi_sz]
    if not mi_bytes or not mi_bytes.endswith(b"\x00"):
        raise KoModuleFormatError(f"{module_filename}: Malformed or non-NUL-terminated .modinfo section")
    mi_sha = hashlib.sha256(mi_bytes).hexdigest()

    modinfo_kv: Dict[str, List[str]] = {}
    for token in mi_bytes[:-1].split(b"\x00"):
        if not token:
            continue
        try:
            text_tok = token.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise KoModuleFormatError(f"{module_filename}: Invalid UTF-8 in .modinfo") from exc
        if "=" not in text_tok:
            raise KoModuleFormatError(f"{module_filename}: Malformed .modinfo entry {text_tok!r} (missing '=')")
        k, v = text_tok.split("=", 1)
        if not k:
            raise KoModuleFormatError(f"{module_filename}: Empty key in .modinfo entry {text_tok!r}")
        modinfo_kv.setdefault(k, []).append(v)

    vermagic_list = modinfo_kv.get("vermagic", [])
    if len(vermagic_list) != 1 or not vermagic_list[0].strip():
        raise KoModuleFormatError(f"{module_filename}: Missing or duplicate vermagic in .modinfo")
    vermagic = vermagic_list[0]
    if expected_vermagic is not None and vermagic != expected_vermagic:
        raise KoModuleFormatError(
            f"{module_filename}: vermagic mismatch ({vermagic!r} != expected {expected_vermagic!r})"
        )

    depends_raw = modinfo_kv.get("depends", [""])[0]
    depends = tuple(d for d in depends_raw.split(",") if d)
    license_str = modinfo_kv.get("license", [""])[0]
    author_str = modinfo_kv.get("author", [""])[0]
    has_modversions_flag = "modversions" in vermagic.split()

    # 2. Parse `.gnu.linkonce.this_module` (`struct module`)
    if ".gnu.linkonce.this_module" not in sec_map:
        raise KoModuleFormatError(f"{module_filename}: Missing .gnu.linkonce.this_module section")
    tm_off, tm_sz, _ = sec_map[".gnu.linkonce.this_module"]
    if tm_sz < THIS_MODULE_MIN_BYTES:
        raise KoModuleFormatError(f"{module_filename}: Truncated .gnu.linkonce.this_module ({tm_sz} B)")
    tm_bytes = raw[tm_off : tm_off + tm_sz]
    tm_name_field = tm_bytes[THIS_MODULE_NAME_OFFSET : THIS_MODULE_NAME_OFFSET + THIS_MODULE_NAME_MAX_BYTES]
    tm_nul = tm_name_field.find(b"\x00")
    if tm_nul <= 0:
        raise KoModuleFormatError(f"{module_filename}: Empty or unterminated name in .gnu.linkonce.this_module")
    this_mod_name = tm_name_field[:tm_nul].decode("ascii")
    tm_sha = hashlib.sha256(tm_bytes).hexdigest()

    # 3. Parse `.note.gnu.build-id` (optional 20B SHA-1)
    build_id_hex = ""
    if ".note.gnu.build-id" in sec_map:
        b_off, b_sz, _ = sec_map[".note.gnu.build-id"]
        if b_sz >= 16:
            namesz, descsz, _ = struct.unpack_from("<III", raw, b_off)
            desc_off = b_off + 12 + ((namesz + 3) & ~3)
            if desc_off + descsz <= b_off + b_sz:
                build_id_hex = raw[desc_off : desc_off + descsz].hex()

    # 4. Parse `__versions` (`struct modversion_info`: 8B LE crc + 56B NUL-padded name = 64B)
    has_versions_sec = "__versions" in sec_map
    modversions: List[ModversionEntry] = []
    module_layout_crc: Optional[int] = None

    if has_versions_sec:
        v_off, v_sz, _ = sec_map["__versions"]
        if (v_sz % MODVERSION_ENTRY_BYTES) != 0 or v_sz == 0:
            raise KoModuleFormatError(
                f"{module_filename}: Unaligned or empty __versions section size {v_sz} B "
                f"(must be a positive multiple of {MODVERSION_ENTRY_BYTES} B)"
            )
        for off in range(v_off, v_off + v_sz, MODVERSION_ENTRY_BYTES):
            crc = struct.unpack_from("<Q", raw, off)[0]
            name_buf = raw[off + 8 : off + MODVERSION_ENTRY_BYTES]
            s_nul = name_buf.find(b"\x00")
            if s_nul <= 0:
                raise KoModuleFormatError(
                    f"{module_filename}: Malformed or unterminated symbol name in __versions at 0x{off:x}"
                )
            sym_name = name_buf[:s_nul].decode("ascii")
            modversions.append(ModversionEntry(symbol=sym_name, crc=crc))
            if sym_name == "module_layout":
                module_layout_crc = crc

        if module_layout_crc is None:
            raise KoModuleFormatError(f"{module_filename}: __versions section missing mandatory module_layout entry")

    if has_modversions_flag and not has_versions_sec:
        raise KoModuleFormatError(
            f"{module_filename}: vermagic advertises 'modversions' but __versions section is missing"
        )
    if expected_module_layout_crc is not None:
        if module_layout_crc != expected_module_layout_crc:
            raise KoModuleFormatError(
                f"{module_filename}: module_layout CRC mismatch "
                f"({hex(module_layout_crc) if module_layout_crc is not None else None} != "
                f"0x{expected_module_layout_crc:x})"
            )

    # 5. Parse `.symtab` (`SHN_UNDEF` imports) & `__ksymtab_strings` (exported kernel symbols)
    undef_syms: List[str] = []
    if ".symtab" in sec_map and ".strtab" in sec_map:
        sym_off, sym_sz, _ = sec_map[".symtab"]
        str_off, str_sz, _ = sec_map[".strtab"]
        strtab = raw[str_off : str_off + str_sz]
        for off in range(sym_off, sym_off + sym_sz, 24):
            st_name, _, _, st_shndx, _, _ = struct.unpack_from("<IBBHQQ", raw, off)
            if st_shndx == 0 and st_name != 0:
                end = strtab.find(b"\x00", st_name)
                if end != -1:
                    undef_syms.append(strtab[st_name:end].decode("ascii"))

    ksym_exports: List[str] = []
    if "__ksymtab_strings" in sec_map:
        k_off, k_sz, _ = sec_map["__ksymtab_strings"]
        for tok in raw[k_off : k_off + k_sz].split(b"\x00"):
            if tok:
                ksym_exports.append(tok.decode("ascii"))

    return KoModuleAudit(
        module_filename=module_filename,
        sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw),
        build_id_hex=build_id_hex,
        this_module_name=this_mod_name,
        this_module_sha256=tm_sha,
        modinfo_sha256=mi_sha,
        vermagic=vermagic,
        depends=tuple(sorted(depends)),
        license_str=license_str,
        author_str=author_str,
        has_modversions_flag=has_modversions_flag,
        has_versions_section=has_versions_sec,
        module_layout_crc=module_layout_crc,
        modversions=tuple(modversions),
        undef_symbols=tuple(sorted(set(undef_syms))),
        exported_ksymtab_symbols=tuple(sorted(set(ksym_exports))),
    )


def inject_synthetic_modversions_section(
    ko_raw: bytes,
    crc_entries: Sequence[Tuple[str, int]],
    *,
    append_modversions_flag: bool = True,
    raw_versions_override: Optional[bytes] = None,
) -> bytes:
    """Build an in-memory ELF64 `ET_REL` `.ko` image with a 64B-stride `__versions` section for testing."""
    e_shoff = struct.unpack_from("<Q", ko_raw, 40)[0]
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", ko_raw, 58)
    assert e_shentsize == 64

    shdrs = [list(struct.unpack_from("<IIQQQQIIQQ", ko_raw, e_shoff + i * e_shentsize)) for i in range(e_shnum)]
    shstr_off, shstr_sz = shdrs[e_shstrndx][4], shdrs[e_shstrndx][5]
    old_shstr = ko_raw[shstr_off : shstr_off + shstr_sz]

    if raw_versions_override is not None:
        ver_blob = raw_versions_override
    else:
        chunks: List[bytes] = []
        for sym, crc in crc_entries:
            sym_b = sym.encode("ascii")
            if len(sym_b) >= MODVERSION_NAME_MAX_BYTES:
                raise ValueError(f"Symbol {sym!r} exceeds 55-byte modversion_info limit")
            padded = sym_b + b"\x00" * (MODVERSION_NAME_MAX_BYTES - len(sym_b))
            chunks.append(struct.pack("<Q", crc & 0xFFFFFFFFFFFFFFFF) + padded)
        ver_blob = b"".join(chunks)

    # Optionally update `.modinfo` vermagic to include `modversions`
    body = bytearray(ko_raw)
    if append_modversions_flag:
        for idx, sh in enumerate(shdrs):
            end = old_shstr.find(b"\x00", sh[0])
            sname = old_shstr[sh[0]:end].decode("ascii")
            if sname == ".modinfo":
                mi_bytes = body[sh[4] : sh[4] + sh[5]]
                tokens = [t for t in mi_bytes.split(b"\x00") if t]
                new_tokens: List[bytes] = []
                for t in tokens:
                    if t.startswith(b"vermagic=") and b" modversions " not in t:
                        # Insert 'modversions ' before architecture token
                        parts = t.decode("utf-8").split()
                        parts.insert(-1, "modversions")
                        new_tokens.append(" ".join(parts).encode("utf-8"))
                    else:
                        new_tokens.append(t)
                new_mi = b"\x00".join(new_tokens) + b"\x00"
                new_mi_off = (len(body) + 7) & ~7
                body.extend(b"\x00" * (new_mi_off - len(body)))
                body.extend(new_mi)
                shdrs[idx][4] = new_mi_off
                shdrs[idx][5] = len(new_mi)
                break

    # Append new `.shstrtab` with `"__versions\0"`
    ver_name_off = len(old_shstr)
    new_shstr = old_shstr + b"__versions\x00"
    new_shstr_off = (len(body) + 7) & ~7
    body.extend(b"\x00" * (new_shstr_off - len(body)))
    body.extend(new_shstr)
    shdrs[e_shstrndx][4] = new_shstr_off
    shdrs[e_shstrndx][5] = len(new_shstr)

    # Append `__versions` section payload (8-byte aligned)
    ver_sec_off = (len(body) + 7) & ~7
    body.extend(b"\x00" * (ver_sec_off - len(body)))
    body.extend(ver_blob)

    shdrs.append(
        [
            ver_name_off,
            SHT_PROGBITS,
            SHF_ALLOC,
            0,
            ver_sec_off,
            len(ver_blob),
            0,
            0,
            8,
            0,
        ]
    )

    new_shoff = (len(body) + 7) & ~7
    body.extend(b"\x00" * (new_shoff - len(body)))
    for sh in shdrs:
        body.extend(struct.pack("<IIQQQQIIQQ", *sh))

    struct.pack_into("<Q", body, 40, new_shoff)
    struct.pack_into("<H", body, 60, len(shdrs))
    return bytes(body)


def audit_kernel_module_compatibility(
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    fx6_p15_kmod_dir: Path = DEFAULT_FX6_P15_KMOD_DIR,
    fx6_p3_initrd_kmod_dir: Path = DEFAULT_FX6_P3_INITRD_KMOD_DIR,
    fx6_p1_initrd_dir: Path = DEFAULT_FX6_P1_INITRD_DIR,
) -> DimensionBKoIntegrityReport:
    """Audit `.modinfo` (`vermagic`), `__versions`, P9 `upm.ko` preservation, and cross-kernel `.ko` ABI."""
    fx3_audits: Dict[str, KoModuleAudit] = {}
    sha_all_ok = True

    for ko_name, expected_sha in sorted(PINNED_FX3_HOST_KO_SHA256.items()):
        raw = (fx3_modules_dir / ko_name).read_bytes()
        audit = parse_and_audit_ko_module(raw, ko_name, expected_vermagic=EXPECTED_HOST_VERMAGIC)
        fx3_audits[ko_name] = audit
        if audit.sha256 != expected_sha:
            sha_all_ok = False

    uniform_vermagic_ok = (
        len(fx3_audits) == 9
        and all(a.vermagic == EXPECTED_HOST_VERMAGIC for a in fx3_audits.values())
    )
    sony_modversions_enabled = any(
        a.has_versions_section or a.has_modversions_flag for a in fx3_audits.values()
    )

    # Verify `depends=` DAG closure within FX3 host module set (`this_module_name`)
    provided_mod_names = {a.this_module_name for a in fx3_audits.values()}
    depends_closed = all(
        all(dep in provided_mod_names for dep in a.depends) for a in fx3_audits.values()
    )

    # 1. Quantitative P9 (`upm.ko` `.text+0x136b8`) module-loader integrity verification
    orig_upm_raw = (fx3_modules_dir / "upm.ko").read_bytes()
    orig_upm_audit = fx3_audits["upm.ko"]
    patched_upm_raw, _ = apply_patch_spec(orig_upm_raw, P9_UPM_KO_SPEC)
    restored_upm_raw, rb_rec = rollback_patch_spec(patched_upm_raw, P9_UPM_KO_SPEC)
    patched_upm_audit = parse_and_audit_ko_module(
        patched_upm_raw, "upm.ko (P9 adapted)", expected_vermagic=EXPECTED_HOST_VERMAGIC
    )

    # Also prove 100% 64-byte `struct modversion_info` CRC preservation on a CONFIG_MODVERSIONS-enabled `upm.ko`!
    synth_crc_table: List[Tuple[str, int]] = [("module_layout", SYNTHETIC_MODULE_LAYOUT_CRC)]
    for sym in orig_upm_audit.undef_symbols:
        synth_crc_table.append((sym, zlib.crc32(sym.encode("ascii")) & 0xFFFFFFFF))
    modver_upm_donor = inject_synthetic_modversions_section(orig_upm_raw, synth_crc_table)
    modver_spec = replace(
        P9_UPM_KO_SPEC,
        expected_size=len(modver_upm_donor),
        donor_sha256=hashlib.sha256(modver_upm_donor).hexdigest(),
    )
    modver_upm_patched, _ = apply_patch_spec(modver_upm_donor, modver_spec)
    modver_upm_restored, modver_rb_rec = rollback_patch_spec(modver_upm_patched, modver_spec)
    expected_modver_vm = "4.9.337-scel+ SMP preempt mod_unload modversions aarch64"
    modver_donor_audit = parse_and_audit_ko_module(
        modver_upm_donor,
        "upm.ko (CONFIG_MODVERSIONS donor)",
        expected_vermagic=expected_modver_vm,
        expected_module_layout_crc=SYNTHETIC_MODULE_LAYOUT_CRC,
    )
    modver_patched_audit = parse_and_audit_ko_module(
        modver_upm_patched,
        "upm.ko (CONFIG_MODVERSIONS P9 adapted)",
        expected_vermagic=expected_modver_vm,
        expected_module_layout_crc=SYNTHETIC_MODULE_LAYOUT_CRC,
    )

    synth_modver_ok = (
        len(modver_donor_audit.modversions) == 1 + len(orig_upm_audit.undef_symbols)
        and modver_donor_audit.modversions == modver_patched_audit.modversions
        and modver_donor_audit.this_module_sha256 == modver_patched_audit.this_module_sha256
        and modver_donor_audit.modinfo_sha256 == modver_patched_audit.modinfo_sha256
        and modver_rb_rec.donor_sha256_matched
        and modver_upm_restored == modver_upm_donor
    )

    p9_check = P9KoIntegrityCheck(
        valid=(
            rb_rec.donor_sha256_matched
            and restored_upm_raw == orig_upm_raw
            and orig_upm_audit.vermagic == patched_upm_audit.vermagic
            and orig_upm_audit.modinfo_sha256 == patched_upm_audit.modinfo_sha256
            and orig_upm_audit.this_module_sha256 == patched_upm_audit.this_module_sha256
            and orig_upm_audit.undef_symbols == patched_upm_audit.undef_symbols
            and orig_upm_audit.exported_ksymtab_symbols == patched_upm_audit.exported_ksymtab_symbols
            and orig_upm_audit.modversions == patched_upm_audit.modversions
            and synth_modver_ok
        ),
        donor_sha256=orig_upm_audit.sha256,
        patched_sha256=patched_upm_audit.sha256,
        rollback_sha256_matched=rb_rec.donor_sha256_matched,
        vermagic_preserved=(orig_upm_audit.vermagic == patched_upm_audit.vermagic),
        modinfo_sha256_preserved=(orig_upm_audit.modinfo_sha256 == patched_upm_audit.modinfo_sha256),
        this_module_sha256_preserved=(
            orig_upm_audit.this_module_sha256 == patched_upm_audit.this_module_sha256
        ),
        undef_symbols_preserved=(orig_upm_audit.undef_symbols == patched_upm_audit.undef_symbols),
        exported_symbols_preserved=(
            orig_upm_audit.exported_ksymtab_symbols == patched_upm_audit.exported_ksymtab_symbols
        ),
        native_modversions_preserved=(orig_upm_audit.modversions == patched_upm_audit.modversions),
        synthetic_modversions_count=len(modver_patched_audit.modversions),
        synthetic_modversions_100pct_preserved=synth_modver_ok,
    )

    # 2. Cross-kernel comparison against FX6 runtime (`p15`/`p3`) and `p1` initrd `.ko` modules
    comparisons: List[CrossKernelModuleComparison] = []
    p1_mismatch_cnt = 0
    identical_abi_cnt = 0
    divergent_mods: List[str] = []

    for ko_name, a3 in sorted(fx3_audits.items()):
        p6_rt = fx6_p15_kmod_dir / ko_name
        if not p6_rt.exists():
            p6_rt = fx6_p3_initrd_kmod_dir / ko_name
        a6_rt = parse_and_audit_ko_module(p6_rt.read_bytes(), f"FX6:{ko_name}")

        p6_p1_candidates = [
            fx6_p1_initrd_dir / "usr" / "kmod" / ko_name,
            fx6_p1_initrd_dir / "kmod" / ko_name,
        ]
        p6_p1 = next((c for c in p6_p1_candidates if c.exists()), None)
        p1_vm: Optional[str] = None
        p1_mismatch = False
        if p6_p1 is not None:
            a6_p1 = parse_and_audit_ko_module(p6_p1.read_bytes(), f"FX6_p1:{ko_name}")
            p1_vm = a6_p1.vermagic
            if p1_vm != EXPECTED_HOST_VERMAGIC and p1_vm == EXPECTED_P1_UPDATER_VERMAGIC:
                p1_mismatch = True
                p1_mismatch_cnt += 1

        u3 = set(a3.undef_symbols)
        u6 = set(a6_rt.undef_symbols)
        e3 = set(a3.exported_ksymtab_symbols)
        e6 = set(a6_rt.exported_ksymtab_symbols)
        abi_eq = (u3 == u6) and (e3 == e6)
        if abi_eq:
            identical_abi_cnt += 1
        else:
            divergent_mods.append(ko_name)

        comparisons.append(
            CrossKernelModuleComparison(
                module_filename=ko_name,
                fx3_vermagic=a3.vermagic,
                fx6_runtime_vermagic=a6_rt.vermagic,
                fx6_p1_vermagic=p1_vm,
                vermagic_runtime_equal=(a3.vermagic == a6_rt.vermagic),
                vermagic_p1_mismatch_detected=p1_mismatch,
                fx3_undef_count=len(u3),
                fx6_undef_count=len(u6),
                only_fx3_undef=tuple(sorted(u3 - u6)),
                only_fx6_undef=tuple(sorted(u6 - u3)),
                only_fx3_exports=tuple(sorted(e3 - e6)),
                only_fx6_exports=tuple(sorted(e6 - e3)),
                symbol_abi_identical=abi_eq,
            )
        )

    all_ok = (
        sha_all_ok
        and uniform_vermagic_ok
        and depends_closed
        and not sony_modversions_enabled
        and p9_check.valid
        and identical_abi_cnt == 7
        and tuple(divergent_mods) == ("backup.ko", "upm.ko")
        and p1_mismatch_cnt == 8
    )

    return DimensionBKoIntegrityReport(
        all_checks_passed=all_ok,
        fx3_host_module_count=len(fx3_audits),
        fx3_all_sha256_verified=sha_all_ok,
        fx3_uniform_vermagic_verified=uniform_vermagic_ok,
        fx3_depends_dag_closed=depends_closed,
        sony_config_modversions_enabled=sony_modversions_enabled,
        p9_upm_integrity=p9_check,
        cross_kernel_comparisons=tuple(comparisons),
        identical_abi_module_count=identical_abi_cnt,
        divergent_abi_modules=tuple(divergent_mods),
        p1_vermagic_mismatch_count=p1_mismatch_cnt,
    )


def run_kernel_dtb_verification(
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
) -> Phase8KernelDtbReport:
    """Execute full Phase 8 Dimension A (`cxd90057.dtb` FDT) & Dimension B (`.ko` integrity) audit."""
    rep_a = audit_dtb_soc_compatibility()
    rep_b = audit_kernel_module_compatibility(fx3_modules_dir=fx3_modules_dir)
    return Phase8KernelDtbReport(
        all_checks_passed=(rep_a.all_checks_passed and rep_b.all_checks_passed),
        dimension_a_dtb=rep_a,
        dimension_b_ko=rep_b,
    )
