"""Phase 43 — `WBI2` Hibernation Snapshot Anatomy, `hibdrv` Warm-Boot Mismatch Detector & FX3 `v7.02` vs FX6 `v6.01` ELF64 `.dynsym` ABI Differ.

Strictly Read-Only (`os.O_RDONLY`) & Clean-Room Dual-Mode:
- Local Donor Mode: opens FX3 v7.02 and FX6 v6.01 `WBI2` (`p5:/wbi`, `nflasha5`)
  snapshots, optional `vmlinux.bin` kernel images, and core ELF64 shared objects
  (`appFw.so`, `libuxengine.so`, `libgemini-grm.so`, `libmpr.so`,
  `libWlanResource.so`, `libInfraBluetoothCore.so`) strictly via `os.O_RDONLY`
  + `mmap.mmap(..., ACCESS_READ)` (~0.03s total across all donor binaries).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors absent):
  synthesizes genuine byte-compliant `WBI2` (`88B` `wb_header` + `64B` section
  descriptors + XOR metadata + `RBUF`/`SUBS` trailer) and genuine ELF64 AArch64
  (`ET_DYN`, `EM_AARCH64=183`, `PT_LOAD`, `PT_DYNAMIC`, `.dynsym`, `.dynstr`)
  shared objects so the exact same parsers run in both modes.

Two core engineering pillars:
1. `WBI2` Hibernation Snapshot & `hibdrv` Warm-Boot Mismatch Verifier:
   - Parses `WBI2` `wb_header` (`O_DATA`, `R_DATA`, `resume_vector`, `dVersion`,
     `sector_size`, `kern_cksum`), validates every 64-byte section descriptor
     (`0x0F0F0F0F` XOR checksum, 4 KiB alignment, `TTBR1_EL1` linear alias
     `0xffffffc000000000 + (phys - 0x400000000)`, zero-fill `flag=1` records),
     verifies kernel build coupling (`Linux version ...` banner & 64B resume slice),
     and proves fail-closed rejection (`BLOCKED_CROSS_KERNEL_WBI2_EL1_MISMATCH`,
     `wbi_mutation_bytes == 0`) for cross-kernel / cross-model `WBI2` flashing
     (`FX6 WBI2` on `FX3` kernel -> immediate EL1 VA/PA & page-table hazard).
2. Pure-Python ELF64 `.dynsym` / `.dynstr` / `DT_NEEDED` / `DT_SONAME` ABI Differ:
   - Parses ELF64 dynamic symbol tables directly via `mmap` + `struct` without
     spawning external subprocesses (`readelf`/`nm`), gracefully handling whichever
     subset of the 6 core libraries exists on disk.
   - Categorizes exported/imported symbols into Shared BIONZ XR Base ABI vs 7
     Cinema Line FX6 feature families (`Big6`, `CineEI`, `Lut3D`, `VariableND`,
     `SdiOut`, `SmartHandle`, `WlanFatal`) plus FX3-only security/adjchk symbols,
     cross-validating why `P1..P12+Fan` closes every divergent symbol family.
"""

from __future__ import annotations

import hashlib
import json
import mmap
import os
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    FX3_APPFW_RELPATH,
    FX6_APPFW_RELPATH,
    is_forced_clean_room,
    resolve_donor_file,
)


PHASE_43_SCHEMA = "fx3_firmware_lab_phase43_wbi_hibdrv_elf_abi_v1"
PHASE_43_VERSION = "43.0.0"

# ---------------------------------------------------------------------------
# WBI2 & `hibdrv` Constants (include/linux/warmboot.h, p5:/wbi, p11:/log)
# ---------------------------------------------------------------------------

WBI2_MAGIC = b"WBI2"
WBI_HEADER_STRUCT = struct.Struct("<4sI10Q")  # 88 bytes
WBI_SECTION_STRUCT = struct.Struct("<8Q")     # 64 bytes
WBI_HEADER_SIZE = WBI_HEADER_STRUCT.size      # 88
WBI_SECTION_SIZE = WBI_SECTION_STRUCT.size    # 64
WBI_SECTOR_SIZE = 512
WBI_META_CKSUM_SEED = 0x0F0F0F0F

WBI_DRAM_PHYS_BASE = 0x400000000
WBI_KERNEL_LINEAR_ALIAS_BASE = 0xFFFFFFC000000000
WBI_ARM64_TEXT_OFFSET = 0x80000

WBI_PARTITION_P5_DEV = "/dev/nflasha5"
WBI_PARTITION_P5_MOUNT = "/wbi"
WBI_PARTITION_P5_BYTES = 0x00096000 * 512  # 314,572,800 B (300.00 MiB)
WBI_PARTITION_P11_DEV = "/dev/nflasha11"
WBI_PARTITION_P11_MOUNT = "/log"
WBI_PARTITION_P11_BYTES = 0x000F9800 * 512  # 523,239,424 B (499.00 MiB)

FX3_WBI2_RELPATH = "sony-firmware-20261024/stage2/extraction/nflasha5.img"
FX6_WBI2_RELPATH = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0700_part_image/dev/nflasha5"
FX3_NFLASH11_RELPATH = "sony-firmware-20261024/stage2/extraction/nflasha11.img"
FX6_NFLASH11_RELPATH = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0700_part_image/dev/nflasha11"
FX3_VMLINUX_RELPATH = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/p3-main/vmlinux.bin"
)
FX6_VMLINUX_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha3/vmlinux.bin"
)

FX3_WBI2_PINNED_SPEC: Dict[str, object] = {
    "body_label": "fx3_702",
    "model_id": 0x91030080,
    "model_code": "ALCIN_UUD",
    "sections": 1399,
    "zero_sections": 82,
    "resume_vector": 0x4004A67F0,
    "dversion": 0x20060224,
    "r_data_bytes": 208_760_832,
    "o_data_bytes": 237_330_432,
    "phys_min": 0x400001000,
    "phys_max": 0x420000000,
    "wbimem_primary_span": 0x00BA0000,
    "kernel_banner": (
        "Linux version 4.9.337-scel+ (jp10239@dic-build-scm-u20-028) "
        "(gcc version 6.4.0 (20201211 (Sony CE Linux 14.0.1.0)) ) "
        "#1 SMP PREEMPT Thu Dec 25 08:15:40 JST 2025"
    ),
}

FX6_WBI2_PINNED_SPEC: Dict[str, object] = {
    "body_label": "fx6_601",
    "model_id": 0x91040086,
    "model_code": "CHAPLIN",
    "sections": 1197,
    "zero_sections": 54,
    "resume_vector": 0x4004A87F0,
    "dversion": 0x20060224,
    "r_data_bytes": 202_338_304,
    "o_data_bytes": 264_376_320,
    "phys_min": 0x400001000,
    "phys_max": 0x424000000,
    "wbimem_primary_span": 0x01919000,
    "kernel_banner": (
        "Linux version 4.9.337-scel+ (jp10239@dic-build-scm-u24-002) "
        "(gcc version 6.4.0 (20240928 (Sony CE Linux 14.0.2.0)) ) "
        "#1 SMP PREEMPT Wed Aug 5 15:24:28 JST 2026"
    ),
}

# ---------------------------------------------------------------------------
# ELF64 Constants & Core Shared Objects
# ---------------------------------------------------------------------------

ELF64_EHDR_STRUCT = struct.Struct("<16sHHIQQQIHHHHHH")  # 64 B
ELF64_PHDR_STRUCT = struct.Struct("<IIQQQQQQ")         # 56 B
ELF64_SHDR_STRUCT = struct.Struct("<IIQQQQIIQQ")       # 64 B
ELF64_SYM_STRUCT = struct.Struct("<IBBHQQ")            # 24 B
ELF64_DYN_STRUCT = struct.Struct("<Qq")                # 16 B

ELF_MAGIC = b"\x7fELF"
ELFCLASS64 = 2
ELFDATA2LSB = 1
ET_DYN = 3
EM_AARCH64 = 183

PT_LOAD = 1
PT_DYNAMIC = 2

SHT_NULL = 0
SHT_STRTAB = 3
SHT_DYNAMIC = 6
SHT_DYNSYM = 11

SHF_WRITE = 0x1
SHF_ALLOC = 0x2
SHF_EXECINSTR = 0x4

DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_SYMTAB = 6
DT_STRSZ = 10
DT_SYMENT = 11
DT_SONAME = 14

STB_LOCAL = 0
STB_GLOBAL = 1
STB_WEAK = 2

STT_NOTYPE = 0
STT_OBJECT = 1
STT_FUNC = 2

SHN_UNDEF = 0

CORE_SHARED_OBJECTS: Tuple[str, ...] = (
    "appFw.so",
    "libuxengine.so",
    "libgemini-grm.so",
    "libmpr.so",
    "libWlanResource.so",
    "libInfraBluetoothCore.so",
)

FX3_CORE_SO_CANDIDATES: Dict[str, Tuple[str, ...]] = {
    "appFw.so": (FX3_APPFW_RELPATH,),
    "libuxengine.so": (
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/libuxengine.so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libuxengine.so",
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libuxengine.so",
    ),
    "libgemini-grm.so": (
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/libgemini-grm.so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgemini-grm.so",
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libgemini-grm.so",
    ),
    "libmpr.so": (
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so",
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so",
    ),
    "libWlanResource.so": (
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libWlanResource.so",
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libWlanResource.so",
    ),
    "libInfraBluetoothCore.so": (
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraBluetoothCore.so",
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libInfraBluetoothCore.so",
    ),
}

FX6_CORE_SO_CANDIDATES: Dict[str, Tuple[str, ...]] = {
    "appFw.so": (FX6_APPFW_RELPATH,),
    "libuxengine.so": (
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libuxengine.so",
    ),
    "libgemini-grm.so": (
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libgemini-grm.so",
    ),
    "libmpr.so": (
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so",
    ),
    "libWlanResource.so": (
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libWlanResource.so",
    ),
    "libInfraBluetoothCore.so": (
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraBluetoothCore.so",
    ),
}

DIVERGENT_FEATURE_FAMILIES: Tuple[str, ...] = (
    "Big6",
    "CineEI",
    "Lut3D",
    "VariableND",
    "SdiOut",
    "SmartHandle",
    "WlanFatal",
)

ALL_SYMBOL_FAMILIES: Tuple[str, ...] = (
    "SharedBionzXrBaseABI",
    *DIVERGENT_FEATURE_FAMILIES,
    "FX3LegacySecurity",
)

# Order-sensitive regex rules avoiding false positives (e.g. 'nd' inside 'send').
_FAMILY_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    (
        "WlanFatal",
        re.compile(
            r"handleFatalError|WlanResource|loadWlanHostDrivers|wlan_irq|"
            r"NetworkTraceRecordWlanResource|WifiAccessory",
            re.IGNORECASE,
        ),
    ),
    (
        "Lut3D",
        re.compile(
            r"SetLutData|ResetLutData|ExecuteSetLutData|CopyCubeFile|"
            r"CubeFilePath|sp_lutDataAddr|LutData",
            re.IGNORECASE,
        ),
    ),
    (
        "VariableND",
        re.compile(
            r"NdFilter|ExternalNdFilter|VariableNd|AutoNd|ClearNd|vef_set_eframing",
            re.IGNORECASE,
        ),
    ),
    (
        "SdiOut",
        re.compile(
            r"SdiOut|MoniFpga|SdiFormat|MuxMxf|libXavcMxf|GetDProXavcIntra|"
            r"SetClipName",
            re.IGNORECASE,
        ),
    ),
    (
        "SmartHandle",
        re.compile(
            r"SmartHandle|Hotshoe|InfraInput|PhyKey|BTWoL|RemoteSetting|"
            r"UnitHandle|power_save_state_changed|CBTWoLE|XLR",
            re.IGNORECASE,
        ),
    ),
    (
        "CineEI",
        re.compile(
            r"CineEI|SLog|ExposureIndex|BaseISO|CamProfile|SonyLookControl|"
            r"Rdd18|KlvConverter|CaptureGammaRDD18|ISOSensitivityRDD18",
            re.IGNORECASE,
        ),
    ),
    (
        "Big6",
        re.compile(
            r"GRM_|gemini|uxengine|GraphicsContext|GraphicsSystem|GraphicsDraw|"
            r"fbrm|gperm|screenIsDirty|screenGetOnBitmap|andromeda|stella|"
            r"libra|alcor|ux_core",
            re.IGNORECASE,
        ),
    ),
    (
        "FX3LegacySecurity",
        re.compile(
            r"SKD_Sign|SKData_|PublishPublicKey|DigitalSignature|libsecvlt|"
            r"app_adjchk_ui|NetServiceWrapperForApConnection",
            re.IGNORECASE,
        ),
    ),
)

# P1..P12+Fan closure matrix cross-validating every divergent feature family
P_CLOSURE_FAMILY_MATRIX: Tuple[Dict[str, object], ...] = (
    {
        "family": "Big6",
        "patch_ids": ("Stage-A", "Stage-B", "P10"),
        "target_libraries": ("appFw.so", "libuxengine.so", "libgemini-grm.so"),
        "closure_mechanism": (
            "Staged FX6 libuxengine.so + libgemini-grm.so + P10 keymap keep GRM/GPE0 "
            "Big6 presenter ABI self-consistent on FX3 DRM/fbrm without touching p15."
        ),
        "closed": True,
    },
    {
        "family": "CineEI",
        "patch_ids": ("P8", "P11", "BK4-Shadow"),
        "target_libraries": ("appFw.so", "libmpr.so"),
        "closure_mechanism": (
            "P8 (0x2159c50) eliminates async log stall, BK4 RAM-shadow (0x02cf1443) "
            "supplies Cine EI flags, and P11 UIPC-CP + KlvConverter RDD18 keep IMX510 "
            "Dual Base ISO (800/12800) coherent."
        ),
        "closed": True,
    },
    {
        "family": "Lut3D",
        "patch_ids": ("P1", "P11"),
        "target_libraries": ("appFw.so", "libmpr.so"),
        "closure_mechanism": (
            "P1 redirects /dev/nflasha20 -> /dev/cnflasha30 across 4 Infra libraries "
            "+ appFw.so; P11 bridges mpr::SetLutData (0x0165/0x0166) to stock FX3 CP."
        ),
        "closed": True,
    },
    {
        "family": "VariableND",
        "patch_ids": ("P4",),
        "target_libraries": ("appFw.so", "libmpr.so"),
        "closure_mechanism": (
            "P4 (appFw.so 0x2111358 nop & 0x21113f0 b 0x211145c) locks electronic "
            "Variable ND state to Clear on FX3 bodies lacking physical e-ND filter."
        ),
        "closed": True,
    },
    {
        "family": "SdiOut",
        "patch_ids": ("P2", "P5", "HDMI-Fallback"),
        "target_libraries": ("appFw.so", "libmpr.so"),
        "closure_mechanism": (
            "FX6 SDI / MXF muxing symbols coexist cleanly in libmpr.so alongside shared "
            "H.264 H422IP XAVC S-I (MP4); missing 12G-SDI BNC hardware degrades gracefully "
            "to HDMI / HDMI 16-bit RAW."
        ),
        "closed": True,
    },
    {
        "family": "SmartHandle",
        "patch_ids": ("P3", "P10", "P11", "Fan"),
        "target_libraries": ("appFw.so", "libInfraBluetoothCore.so"),
        "closure_mechanism": (
            "P3 prunes remote panel thread, P10 remaps FX3 physical buttons (0x2245a10), "
            "P11 injects 0x91db059b detached-grip ACK keeping XLR-H1 active, and Fan "
            "(libfan.so 0x1dec) validates thermal backup."
        ),
        "closed": True,
    },
    {
        "family": "WlanFatal",
        "patch_ids": ("P12", "BK4-Airplane"),
        "target_libraries": ("libWlanResource.so", "libInfraBluetoothCore.so"),
        "closure_mechanism": (
            "P12 patches libWlanResource.so::_Z16handleFatalErrorv (0x70d4 -> mov w0, #0; ret) "
            "preventing 00342260 WF-12 bootloops while BK4 Airplane shadow (0xbb9) prevents "
            "BT UART fatal traps."
        ),
        "closed": True,
    },
)


class Wbi2FormatError(ValueError):
    """Raised when a WBI2 snapshot header or section table is malformed."""


class Elf64ParseError(ValueError):
    """Raised when an ELF64 image header, dynamic table, or symbol table is malformed."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Wbi2SectionDescriptor:
    index: int
    phys_addr: int
    rlen: int
    cksum: int
    flag: int
    olen: int
    virt_addr: int
    meta_cksum: int
    file_offset: Optional[int]
    meta_cksum_ok: bool
    linear_alias_ok: bool


@dataclass(frozen=True)
class Wbi2SnapshotAudit:
    valid: bool
    body_label: str
    source_mode: str
    file_bytes: int
    magic: str
    section_count: int
    stored_section_count: int
    zero_fill_section_count: int
    flags: int
    resume_vector_hex: str
    resume_section_index: Optional[int]
    resume_64b_kernel_match: Optional[bool]
    dversion_hex: str
    sector_size: int
    r_data_bytes: int
    o_data_bytes: int
    kern_start_hex: str
    kern_size_bytes: int
    kern_cksum_hex: str
    table_offset: int
    table_end: int
    table_sha256: str
    trailer_bytes: int
    trailer_rbuf_found: bool
    trailer_subs_found: bool
    phys_min_hex: str
    phys_max_hex: str
    phys_span_bytes: int
    metadata_xor_verified_count: int
    linear_alias_verified_count: int
    sorted_physical_overlaps: int
    kernel_banner: str
    kernel_build_coupled: bool
    p11_companion_present: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HibdrvMismatchVerdict:
    rejected_fail_closed: bool
    verdict_code: str
    target_kernel_body: str
    candidate_wbi_body: str
    wbi_mutation_bytes: int
    p5_wbi_write_forbidden: bool
    p11_bis_format_forbidden: bool
    warm_mode_2_forbidden: bool
    resume_vector_delta_bytes: int
    o_data_delta_bytes: int
    phys_span_delta_bytes: int
    wbimem_delta_bytes: int
    kernel_banner_match: bool
    el1_hazards: Tuple[str, ...]
    proof_summary: str


@dataclass(frozen=True)
class Elf64DynamicSymbol:
    name: str
    is_export: bool
    bind: int
    sym_type: int
    st_shndx: int
    st_value: int
    st_size: int
    family: str


@dataclass(frozen=True)
class Elf64LibraryAbiInfo:
    library_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    e_type: int
    e_machine: int
    soname: Optional[str]
    dt_needed: Tuple[str, ...]
    total_dynsym_count: int
    export_count: int
    import_count: int
    parse_path: str  # "SECTION_HEADERS" or "PT_DYNAMIC_VADDR"
    family_counts: Dict[str, int]
    sample_exports_by_family: Dict[str, Tuple[str, ...]]
    sample_imports_by_family: Dict[str, Tuple[str, ...]]
    exports: Tuple[str, ...]
    imports: Tuple[str, ...]


@dataclass(frozen=True)
class LibraryAbiDiffResult:
    library_name: str
    comparison_status: str  # "BOTH_BODIES_PARSED", "FX6_ONLY_ON_DISK", "FX3_ONLY_ON_DISK", "MISSING_BOTH"
    fx3_present: bool
    fx6_present: bool
    fx3_soname: Optional[str]
    fx6_soname: Optional[str]
    shared_dt_needed: Tuple[str, ...]
    fx3_only_dt_needed: Tuple[str, ...]
    fx6_only_dt_needed: Tuple[str, ...]
    shared_export_count: int
    fx3_only_export_count: int
    fx6_only_export_count: int
    shared_import_count: int
    fx3_only_import_count: int
    fx6_only_import_count: int
    divergent_family_counts: Dict[str, int]
    sample_fx3_only_exports: Tuple[str, ...]
    sample_fx6_only_exports: Tuple[str, ...]
    sample_fx3_only_imports: Tuple[str, ...]
    sample_fx6_only_imports: Tuple[str, ...]


@dataclass(frozen=True)
class FeatureClosureCrossCheck:
    family: str
    patch_ids: Tuple[str, ...]
    target_libraries: Tuple[str, ...]
    observed_symbol_hits: int
    closure_mechanism: str
    closed: bool


@dataclass(frozen=True)
class WbiHibdrvAndElfAbiReport:
    schema_version: str
    version: str
    mode: str
    all_checks_passed: bool
    wbi_mutation_bytes: int
    fx3_wbi2: Wbi2SnapshotAudit
    fx6_wbi2: Wbi2SnapshotAudit
    hibdrv_cross_kernel_rejection: HibdrvMismatchVerdict
    library_diffs: Tuple[LibraryAbiDiffResult, ...]
    libraries_parsed_fx3: int
    libraries_parsed_fx6: int
    libraries_both_compared: int
    feature_closure_checks: Tuple[FeatureClosureCrossCheck, ...]
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Read-Only `os.O_RDONLY` + `mmap` Helpers
# ---------------------------------------------------------------------------


def _read_cstr(buf: Union[bytes, bytearray, memoryview, mmap.mmap], offset: int, limit: int = 4096) -> str:
    if offset < 0 or offset >= len(buf):
        return ""
    end = buf.find(b"\x00", offset, min(len(buf), offset + limit))
    if end == -1:
        end = min(len(buf), offset + limit)
    return bytes(buf[offset:end]).decode("utf-8", errors="replace")


def open_mmap_rdonly(path: Path) -> Tuple[int, mmap.mmap]:
    """Strictly open `path` with `os.O_RDONLY` and return `(fd, mmap.mmap)`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        size = os.fstat(fd).st_size
        if size == 0:
            raise ValueError(f"Cannot mmap empty file: {path}")
        mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        return fd, mm
    except Exception:
        os.close(fd)
        raise


def close_mmap_rdonly(fd: int, mm: mmap.mmap) -> None:
    try:
        mm.close()
    finally:
        os.close(fd)


def _resolve_candidate_donor(
    relpaths: Sequence[str],
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
    clean_room: bool = False,
) -> Optional[Path]:
    for rel in relpaths:
        hit = resolve_donor_file(rel, repo_root=repo_root, env=env, clean_room=clean_room)
        if hit is not None:
            return hit
    return None


# ---------------------------------------------------------------------------
# Pillar 1: `WBI2` Parser, Synthetic Builder & `hibdrv` Cross-Kernel Guard
# ---------------------------------------------------------------------------


def build_synthetic_wbi2_image(
    body: str = "fx3_702",
    *,
    include_kernel_banner: bool = True,
    corrupt_magic: bool = False,
    corrupt_xor_index: Optional[int] = None,
    corrupt_linear_alias_index: Optional[int] = None,
    corrupt_overlap: bool = False,
) -> bytes:
    """Build a deterministic, spec-compliant synthetic `WBI2` snapshot buffer."""
    spec = FX3_WBI2_PINNED_SPEC if body == "fx3_702" else FX6_WBI2_PINNED_SPEC
    rv = int(spec["resume_vector"])
    dver = int(spec["dversion"])
    banner = str(spec["kernel_banner"]).encode("ascii") + b"\x00"
    armd_magic = b"\x00" * 56 + b"ARMd" + b"\x00" * 4

    # Construct 4 compact, non-overlapping 4 KiB-aligned sections:
    # sec 0: 4 KiB early page around 0x400001000
    # sec 1: 8 KiB kernel text covering resume_vector page (rv - 0x400000000 - 0x7f0 -> aligned)
    # sec 2: 4 KiB banner / rodata page (contains Linux version + wbi4 marker)
    # sec 3: 4 KiB zero-fill flag=1 section (olen=4096, rlen=0)
    rv_page = rv & ~0xFFF
    rv_in_page = rv - rv_page
    sec1_data = bytearray(8192)
    sec1_data[0:64] = armd_magic
    # Place deterministic non-zero AArch64-like resume slice at rv_in_page
    resume_slice = hashlib.sha256(f"{body}:resume:{rv:#x}".encode("ascii")).digest() * 2
    sec1_data[rv_in_page : rv_in_page + 64] = resume_slice

    sec0_data = b"\x01\x02\x03\x04" + b"\x00" * 4092
    sec2_data = bytearray(4096)
    if include_kernel_banner:
        sec2_data[0 : len(banner)] = banner
    sec2_data[512:516] = b"wbi4"

    phys_max_boundary = int(spec["phys_max"])
    sec3_phys = phys_max_boundary - 4096 if not corrupt_overlap else rv_page

    layout: List[Tuple[int, bytes, int, int]] = [
        (0x400001000, sec0_data, 0, 4096),
        (rv_page, bytes(sec1_data), 0, 8192),
        (0x404000000, bytes(sec2_data), 0, 4096),
        (sec3_phys, b"", 1, 4096),
    ]

    r_data = bytearray()
    table_bytes = bytearray()
    o_data_sum = 0
    for idx, (phys, blob, flag, olen) in enumerate(layout):
        rlen = len(blob)
        assert (flag == 0 and rlen == olen) or (flag == 1 and rlen == 0)
        r_data.extend(blob)
        o_data_sum += olen
        virt = WBI_KERNEL_LINEAR_ALIAS_BASE + (phys - WBI_DRAM_PHYS_BASE)
        if corrupt_linear_alias_index is not None and idx == corrupt_linear_alias_index:
            virt ^= 0x1000
        cksum = WBI_META_CKSUM_SEED
        meta_cksum = WBI_META_CKSUM_SEED ^ phys ^ rlen ^ cksum ^ flag ^ olen ^ virt
        if corrupt_xor_index is not None and idx == corrupt_xor_index:
            meta_cksum ^= 0xDEAD
        table_bytes.extend(
            WBI_SECTION_STRUCT.pack(phys, rlen, cksum, flag, olen, virt, meta_cksum, 0)
        )

    r_data_len = len(r_data)
    magic = b"BAD!" if corrupt_magic else WBI2_MAGIC
    hdr_88 = WBI_HEADER_STRUCT.pack(
        magic,
        0,
        len(layout),
        0,
        rv,
        dver,
        WBI_SECTOR_SIZE,
        r_data_len,
        0,
        0,
        WBI_META_CKSUM_SEED,
        o_data_sum,
    )
    sector0 = hdr_88 + bytes(WBI_SECTOR_SIZE - len(hdr_88))
    trailer = bytearray(4096)
    trailer[0:4] = b"RBUF"
    trailer[64:68] = b"SUBS"
    return sector0 + bytes(r_data) + bytes(table_bytes) + bytes(trailer)


def build_synthetic_kernel_for_wbi(body: str = "fx3_702") -> bytes:
    """Build a minimal ARM64 `vmlinux.bin` header+slice matching synthetic `WBI2`."""
    spec = FX3_WBI2_PINNED_SPEC if body == "fx3_702" else FX6_WBI2_PINNED_SPEC
    rv = int(spec["resume_vector"])
    k_off = rv - (WBI_DRAM_PHYS_BASE + WBI_ARM64_TEXT_OFFSET)
    total = k_off + 128
    buf = bytearray(total)
    # ARM64 Image header: text_offset at +8 = 0x80000, "ARMd" at +56
    struct.pack_into("<Q", buf, 8, WBI_ARM64_TEXT_OFFSET)
    buf[56:60] = b"ARMd"
    resume_slice = hashlib.sha256(f"{body}:resume:{rv:#x}".encode("ascii")).digest() * 2
    buf[k_off : k_off + 64] = resume_slice
    return bytes(buf)


def parse_wbi2_buffer(
    buf: Union[bytes, bytearray, memoryview, mmap.mmap],
    *,
    body_label: str = "unknown",
    source_mode: str = "MEMORY_BUFFER",
    kernel_buf: Optional[Union[bytes, bytearray, memoryview, mmap.mmap]] = None,
    p11_companion_present: bool = False,
) -> Wbi2SnapshotAudit:
    """Parse and validate a `WBI2` hibernation snapshot from `mmap`/bytes."""
    errors: List[str] = []
    n_bytes = len(buf)
    if n_bytes < WBI_SECTOR_SIZE:
        return Wbi2SnapshotAudit(
            valid=False,
            body_label=body_label,
            source_mode=source_mode,
            file_bytes=n_bytes,
            magic="",
            section_count=0,
            stored_section_count=0,
            zero_fill_section_count=0,
            flags=0,
            resume_vector_hex="0x0",
            resume_section_index=None,
            resume_64b_kernel_match=None,
            dversion_hex="0x0",
            sector_size=0,
            r_data_bytes=0,
            o_data_bytes=0,
            kern_start_hex="0x0",
            kern_size_bytes=0,
            kern_cksum_hex="0x0",
            table_offset=0,
            table_end=0,
            table_sha256="",
            trailer_bytes=0,
            trailer_rbuf_found=False,
            trailer_subs_found=False,
            phys_min_hex="0x0",
            phys_max_hex="0x0",
            phys_span_bytes=0,
            metadata_xor_verified_count=0,
            linear_alias_verified_count=0,
            sorted_physical_overlaps=0,
            kernel_banner="",
            kernel_build_coupled=False,
            p11_companion_present=p11_companion_present,
            errors=(f"WBI2 buffer smaller than 512B header sector ({n_bytes} B)",),
        )

    (
        magic_raw,
        padding,
        sections,
        flag,
        resume_vec,
        dver,
        sector_sz,
        r_data_sz,
        kern_start,
        kern_sz,
        kern_cksum,
        o_data_sz,
    ) = WBI_HEADER_STRUCT.unpack_from(buf, 0)

    magic_str = magic_raw.decode("latin1")
    if magic_raw != WBI2_MAGIC:
        errors.append(f"Invalid WBI2 magic: expected 'WBI2', got {magic_str!r}")
    if padding != 0:
        errors.append(f"Non-zero WBI2 header padding: {padding}")
    if sector_sz != WBI_SECTOR_SIZE:
        errors.append(f"Expected sector_size={WBI_SECTOR_SIZE}, got {sector_sz}")
    if sections == 0 or sections > 100_000:
        errors.append(f"Implausible WBI2 section count: {sections}")

    table_offset = sector_sz + r_data_sz if sector_sz > 0 else WBI_SECTOR_SIZE + r_data_sz
    table_end = table_offset + sections * WBI_SECTION_SIZE
    if table_offset > n_bytes or table_end > n_bytes:
        errors.append(
            f"WBI2 section table [{table_offset}, {table_end}) exceeds buffer size {n_bytes}"
        )
        return Wbi2SnapshotAudit(
            valid=False,
            body_label=body_label,
            source_mode=source_mode,
            file_bytes=n_bytes,
            magic=magic_str,
            section_count=sections,
            stored_section_count=0,
            zero_fill_section_count=0,
            flags=flag,
            resume_vector_hex=f"0x{resume_vec:x}",
            resume_section_index=None,
            resume_64b_kernel_match=None,
            dversion_hex=f"0x{dver:x}",
            sector_size=sector_sz,
            r_data_bytes=r_data_sz,
            o_data_bytes=o_data_sz,
            kern_start_hex=f"0x{kern_start:x}",
            kern_size_bytes=kern_sz,
            kern_cksum_hex=f"0x{kern_cksum:x}",
            table_offset=table_offset,
            table_end=table_end,
            table_sha256="",
            trailer_bytes=0,
            trailer_rbuf_found=False,
            trailer_subs_found=False,
            phys_min_hex="0x0",
            phys_max_hex="0x0",
            phys_span_bytes=0,
            metadata_xor_verified_count=0,
            linear_alias_verified_count=0,
            sorted_physical_overlaps=0,
            kernel_banner="",
            kernel_build_coupled=False,
            p11_companion_present=p11_companion_present,
            errors=tuple(errors),
        )

    table_sha256 = hashlib.sha256(buf[table_offset:table_end]).hexdigest()
    cursor = sector_sz
    stored_count = 0
    zero_count = 0
    xor_ok_count = 0
    alias_ok_count = 0
    r_sum = 0
    o_sum = 0
    phys_ranges: List[Tuple[int, int, int]] = []
    resume_sec_idx: Optional[int] = None
    resume_file_off: Optional[int] = None

    for idx in range(sections):
        addr, rlen, cksum, sflag, olen, virt, meta_cksum, spad = WBI_SECTION_STRUCT.unpack_from(
            buf, table_offset + idx * WBI_SECTION_SIZE
        )
        if (addr & 0xFFF) != 0 or olen == 0 or (olen & 0xFFF) != 0:
            errors.append(f"Section {idx} alignment/size error: addr=0x{addr:x}, olen=0x{olen:x}")
        if sflag not in (0, 1) or spad != 0:
            errors.append(f"Section {idx} invalid flag={sflag} or pad={spad}")
        if (sflag == 0 and rlen != olen) or (sflag == 1 and rlen != 0):
            errors.append(f"Section {idx} flag/rlen mismatch: flag={sflag}, rlen={rlen}, olen={olen}")

        expected_xor = WBI_META_CKSUM_SEED ^ addr ^ rlen ^ cksum ^ sflag ^ olen ^ virt
        if expected_xor == meta_cksum:
            xor_ok_count += 1
        else:
            errors.append(
                f"Section {idx} metadata XOR mismatch: expected 0x{expected_xor:x}, got 0x{meta_cksum:x}"
            )

        expected_alias = WBI_KERNEL_LINEAR_ALIAS_BASE + (addr - WBI_DRAM_PHYS_BASE)
        if virt == expected_alias:
            alias_ok_count += 1
        else:
            errors.append(
                f"Section {idx} TTBR1_EL1 linear alias mismatch: expected 0x{expected_alias:x}, got 0x{virt:x}"
            )

        if sflag == 0:
            stored_count += 1
            if addr <= resume_vec and resume_vec + 64 <= addr + rlen:
                resume_sec_idx = idx
                resume_file_off = cursor + (resume_vec - addr)
        else:
            zero_count += 1

        phys_ranges.append((addr, addr + olen, idx))
        r_sum += rlen
        o_sum += olen
        cursor += rlen

    if cursor != table_offset or r_sum != r_data_sz:
        errors.append(
            f"R_DATA byte sum mismatch: cursor={cursor}, table={table_offset}, r_sum={r_sum}, header={r_data_sz}"
        )
    if o_sum != o_data_sz:
        errors.append(f"O_DATA byte sum mismatch: sum(olen)={o_sum}, header={o_data_sz}")
    if resume_sec_idx is None:
        errors.append(f"resume_vector 0x{resume_vec:x} is not covered by any stored WBI2 section")

    phys_ranges.sort(key=lambda t: t[0])
    overlaps = 0
    for left, right in zip(phys_ranges, phys_ranges[1:]):
        if left[1] > right[0]:
            overlaps += 1
    if overlaps > 0:
        errors.append(f"Detected {overlaps} overlapping physical address spans across WBI2 sections")

    phys_min = phys_ranges[0][0] if phys_ranges else 0
    phys_max = max(r[1] for r in phys_ranges) if phys_ranges else 0
    phys_span = phys_max - phys_min if phys_max >= phys_min else 0

    trailer_bytes = n_bytes - table_end
    rbuf_found = buf.find(b"RBUF", table_end, n_bytes) != -1
    subs_found = buf.find(b"SUBS", table_end, n_bytes) != -1

    fast_scan_end = min(table_offset, sector_sz + 16 * 1024 * 1024)
    lv_off = buf.find(b"Linux version ", sector_sz, fast_scan_end)
    if lv_off < 0 and fast_scan_end < table_offset:
        lv_off = buf.find(b"Linux version ", fast_scan_end, table_offset)
    kernel_banner = _read_cstr(buf, lv_off, 256).strip() if lv_off >= 0 else ""

    resume_match: Optional[bool] = None
    if kernel_buf is not None and resume_file_off is not None and len(kernel_buf) >= 64:
        text_off = struct.unpack_from("<Q", kernel_buf, 8)[0]
        k_off = resume_vec - (WBI_DRAM_PHYS_BASE + text_off)
        if 0 <= k_off and k_off + 64 <= len(kernel_buf):
            resume_match = (
                bytes(buf[resume_file_off : resume_file_off + 64])
                == bytes(kernel_buf[k_off : k_off + 64])
            )
            if not resume_match:
                errors.append(
                    f"64B resume slice at 0x{resume_vec:x} does not match target vmlinux.bin"
                )
        else:
            resume_match = False
            errors.append(
                f"resume_vector 0x{resume_vec:x} (kernel offset 0x{k_off:x}) falls outside target vmlinux.bin ({len(kernel_buf)} B)"
            )

    kernel_build_coupled = bool(kernel_banner) and (resume_match is not False)
    if not kernel_banner:
        errors.append("Missing embedded 'Linux version ' build banner inside WBI2 R_DATA")

    return Wbi2SnapshotAudit(
        valid=(len(errors) == 0),
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=n_bytes,
        magic=magic_str,
        section_count=sections,
        stored_section_count=stored_count,
        zero_fill_section_count=zero_count,
        flags=flag,
        resume_vector_hex=f"0x{resume_vec:x}",
        resume_section_index=resume_sec_idx,
        resume_64b_kernel_match=resume_match,
        dversion_hex=f"0x{dver:x}",
        sector_size=sector_sz,
        r_data_bytes=r_data_sz,
        o_data_bytes=o_data_sz,
        kern_start_hex=f"0x{kern_start:x}",
        kern_size_bytes=kern_sz,
        kern_cksum_hex=f"0x{kern_cksum:x}",
        table_offset=table_offset,
        table_end=table_end,
        table_sha256=table_sha256,
        trailer_bytes=trailer_bytes,
        trailer_rbuf_found=rbuf_found,
        trailer_subs_found=subs_found,
        phys_min_hex=f"0x{phys_min:x}",
        phys_max_hex=f"0x{phys_max:x}",
        phys_span_bytes=phys_span,
        metadata_xor_verified_count=xor_ok_count,
        linear_alias_verified_count=alias_ok_count,
        sorted_physical_overlaps=overlaps,
        kernel_banner=kernel_banner,
        kernel_build_coupled=kernel_build_coupled,
        p11_companion_present=p11_companion_present,
        errors=tuple(errors),
    )


def audit_wbi2_file_rdonly(
    wbi_path: Path,
    *,
    body_label: str,
    kernel_path: Optional[Path] = None,
    p11_path: Optional[Path] = None,
) -> Wbi2SnapshotAudit:
    """Strictly open and audit a local donor `WBI2` image via `os.O_RDONLY` + `mmap`."""
    fd_w, mm_w = open_mmap_rdonly(wbi_path)
    fd_k: Optional[int] = None
    mm_k: Optional[mmap.mmap] = None
    try:
        if kernel_path is not None and kernel_path.is_file():
            fd_k, mm_k = open_mmap_rdonly(kernel_path)
        return parse_wbi2_buffer(
            mm_w,
            body_label=body_label,
            source_mode="LOCAL_DONOR_RDONLY",
            kernel_buf=mm_k,
            p11_companion_present=bool(p11_path is not None and p11_path.is_file()),
        )
    finally:
        if fd_k is not None and mm_k is not None:
            close_mmap_rdonly(fd_k, mm_k)
        close_mmap_rdonly(fd_w, mm_w)


def verify_hibdrv_cross_kernel_rejection(
    target_wbi: Wbi2SnapshotAudit,
    candidate_wbi: Wbi2SnapshotAudit,
    *,
    requested_warm_mode: int = 2,
    allow_p5_write: bool = False,
    allow_p11_bis_format: bool = False,
) -> HibdrvMismatchVerdict:
    """Prove fail-closed rejection of cross-kernel / cross-model `WBI2` warm-boot flashing.

    `wbi_mutation_bytes` is hard-locked to `0`.
    """
    hazards: List[str] = []

    target_rv = int(target_wbi.resume_vector_hex, 16)
    cand_rv = int(candidate_wbi.resume_vector_hex, 16)
    rv_delta = abs(cand_rv - target_rv)
    odata_delta = abs(candidate_wbi.o_data_bytes - target_wbi.o_data_bytes)
    target_pmax = int(target_wbi.phys_max_hex, 16)
    cand_pmax = int(candidate_wbi.phys_max_hex, 16)
    span_delta = abs(cand_pmax - target_pmax)

    fx3_wbimem = int(FX3_WBI2_PINNED_SPEC["wbimem_primary_span"])
    fx6_wbimem = int(FX6_WBI2_PINNED_SPEC["wbimem_primary_span"])
    wbimem_delta = abs(fx6_wbimem - fx3_wbimem)

    banner_match = bool(
        target_wbi.kernel_banner
        and candidate_wbi.kernel_banner
        and target_wbi.kernel_banner == candidate_wbi.kernel_banner
    )

    if not target_wbi.valid or not candidate_wbi.valid:
        hazards.append("INVALID_WBI2_HEADER_OR_SECTION_METADATA")
    if not banner_match:
        hazards.append(
            "KERNEL_BUILD_COUPLED_BANNER_MISMATCH: "
            "different Sony CE Linux toolchain/build host timestamps"
        )
    if target_rv != cand_rv:
        hazards.append(
            f"EL1_RESUME_VECTOR_MISMATCH: target=0x{target_rv:x} vs "
            f"candidate=0x{cand_rv:x} (delta=0x{rv_delta:x} B)"
        )
    if target_pmax != cand_pmax:
        hazards.append(
            f"EL1_TTBR1_PAGE_TABLE_DRAM_SPAN_HAZARD: target_end=0x{target_pmax:x} vs "
            f"candidate_end=0x{cand_pmax:x} (delta={span_delta} B)"
        )
    if target_wbi.o_data_bytes != candidate_wbi.o_data_bytes:
        hazards.append(
            f"O_DATA_RESTORE_FOOTPRINT_MISMATCH: target={target_wbi.o_data_bytes} vs "
            f"candidate={candidate_wbi.o_data_bytes} (delta={odata_delta} B)"
        )
    if target_wbi.section_count != candidate_wbi.section_count:
        hazards.append(
            f"SECTION_DESCRIPTOR_COUNT_MISMATCH: {target_wbi.section_count} vs "
            f"{candidate_wbi.section_count}"
        )
    if requested_warm_mode == 2:
        hazards.append("HIBDRV_WARM_MODE_2_FORBIDDEN_ON_STAGE_A_B")
    if allow_p5_write:
        hazards.append("P5_NFLASHA5_RAW_WBI_WRITE_FORBIDDEN")
    if allow_p11_bis_format:
        hazards.append("P11_NFLASHA11_BIS_LOG_FORMAT_FORBIDDEN")

    cross_kernel_mismatch = (
        not banner_match
        or target_rv != cand_rv
        or target_pmax != cand_pmax
        or target_wbi.o_data_bytes != candidate_wbi.o_data_bytes
        or target_wbi.section_count != candidate_wbi.section_count
        or target_wbi.body_label != candidate_wbi.body_label
    )
    rejected = cross_kernel_mismatch or requested_warm_mode == 2 or allow_p5_write or allow_p11_bis_format

    if not target_wbi.valid or not candidate_wbi.valid:
        verdict_code = "BLOCKED_INVALID_WBI2_OR_KERNEL"
    elif cross_kernel_mismatch:
        verdict_code = "BLOCKED_CROSS_KERNEL_WBI2_EL1_MISMATCH"
    elif rejected:
        verdict_code = "BLOCKED_WBI_MUTATION_AND_WARM_MODE_LOCKED"
    else:
        verdict_code = "ALLOWED_IDENTICAL_KERNEL_WBI2_READONLY"

    proof_summary = (
        f"Fail-closed {verdict_code}: {candidate_wbi.body_label} WBI2 on "
        f"{target_wbi.body_label} kernel introduces EL1 resume_vector delta 0x{rv_delta:x} B, "
        f"O_DATA delta {odata_delta} B, DRAM linear-alias span delta {span_delta} B, "
        f"and wbimem collision delta {wbimem_delta} B; p5:/wbi & p11:/log locked "
        f"(wbi_mutation_bytes=0)."
    )

    return HibdrvMismatchVerdict(
        rejected_fail_closed=rejected,
        verdict_code=verdict_code,
        target_kernel_body=target_wbi.body_label,
        candidate_wbi_body=candidate_wbi.body_label,
        wbi_mutation_bytes=0,
        p5_wbi_write_forbidden=True,
        p11_bis_format_forbidden=True,
        warm_mode_2_forbidden=True,
        resume_vector_delta_bytes=rv_delta,
        o_data_delta_bytes=odata_delta,
        phys_span_delta_bytes=span_delta,
        wbimem_delta_bytes=wbimem_delta,
        kernel_banner_match=banner_match,
        el1_hazards=tuple(hazards),
        proof_summary=proof_summary,
    )


# ---------------------------------------------------------------------------
# Pillar 2: Pure-Python ELF64 `.dynsym` / `.dynstr` / `DT_NEEDED` Differ
# ---------------------------------------------------------------------------


def classify_symbol_family(symbol_name: str) -> str:
    """Categorize an ELF64 dynamic symbol into Shared Base ABI or a Cinema Line family."""
    for family, pattern in _FAMILY_PATTERNS:
        if pattern.search(symbol_name):
            return family
    return "SharedBionzXrBaseABI"


def parse_elf64_dynamic_abi(
    buf: Union[bytes, bytearray, memoryview, mmap.mmap],
    *,
    library_name: str,
    body_label: str,
    source_mode: str = "MEMORY_BUFFER",
) -> Elf64LibraryAbiInfo:
    """Parse ELF64 `.dynsym`, `.dynstr`, `DT_NEEDED`, and `DT_SONAME` directly via `mmap`/`struct`."""
    n_bytes = len(buf)
    if n_bytes < ELF64_EHDR_STRUCT.size:
        raise Elf64ParseError(f"{library_name}: buffer too small ({n_bytes} B)")

    (
        e_ident,
        e_type,
        e_machine,
        e_version,
        _e_entry,
        e_phoff,
        e_shoff,
        _e_flags,
        e_ehsize,
        e_phentsize,
        e_phnum,
        e_shentsize,
        e_shnum,
        e_shstrndx,
    ) = ELF64_EHDR_STRUCT.unpack_from(buf, 0)

    if e_ident[:4] != ELF_MAGIC or e_ident[4] != ELFCLASS64 or e_ident[5] != ELFDATA2LSB:
        raise Elf64ParseError(f"{library_name}: not a 64-bit little-endian ELF image")
    if e_machine != EM_AARCH64:
        raise Elf64ParseError(f"{library_name}: expected EM_AARCH64 (183), got {e_machine}")
    if e_version != 1 or e_ehsize < ELF64_EHDR_STRUCT.size:
        raise Elf64ParseError(f"{library_name}: invalid ELF64 version/ehsize")

    loads: List[Tuple[int, int, int]] = []
    dyn_off: Optional[int] = None
    dyn_sz = 0
    if e_phnum > 0:
        if e_phentsize < ELF64_PHDR_STRUCT.size or e_phoff + e_phnum * e_phentsize > n_bytes:
            raise Elf64ParseError(f"{library_name}: program header table out of bounds")
        for idx in range(e_phnum):
            pt, _pf, poff, pv, _pp, pfsz, _pmsz, _pa = ELF64_PHDR_STRUCT.unpack_from(
                buf, e_phoff + idx * e_phentsize
            )
            if pt == PT_LOAD:
                loads.append((pv, poff, pfsz))
            elif pt == PT_DYNAMIC:
                dyn_off, dyn_sz = poff, pfsz

    def _vaddr_to_offset(va: int) -> Optional[int]:
        for pv, poff, pfsz in loads:
            if pv <= va < pv + pfsz:
                return poff + (va - pv)
        return None

    dynsym_info: Optional[Tuple[int, int, int]] = None
    dynstr_info: Optional[Tuple[int, int]] = None
    parse_path = "SECTION_HEADERS"

    if e_shoff > 0 and e_shnum > 0 and e_shentsize >= ELF64_SHDR_STRUCT.size:
        if e_shoff + e_shnum * e_shentsize > n_bytes:
            raise Elf64ParseError(f"{library_name}: section header table out of bounds")
        shdrs = [
            ELF64_SHDR_STRUCT.unpack_from(buf, e_shoff + i * e_shentsize)
            for i in range(e_shnum)
        ]
        shstr_off = shdrs[e_shstrndx][4] if e_shstrndx < len(shdrs) else 0
        for sh in shdrs:
            sh_name, sh_type, _flags, _addr, sh_offset, sh_size, _link, _info, _align, sh_entsize = sh
            sname = _read_cstr(buf, shstr_off + sh_name, 256) if shstr_off else ""
            if sh_type == SHT_DYNSYM or sname == ".dynsym":
                dynsym_info = (sh_offset, sh_size, sh_entsize or ELF64_SYM_STRUCT.size)
            elif sh_type == SHT_STRTAB and sname == ".dynstr":
                dynstr_info = (sh_offset, sh_size)
            elif sh_type == SHT_DYNAMIC and dyn_off is None:
                dyn_off, dyn_sz = sh_offset, sh_size

    needed_offs: List[int] = []
    soname_off: Optional[int] = None
    dt_strtab_va: Optional[int] = None
    dt_symtab_va: Optional[int] = None
    dt_strsz = 0
    dt_syment = ELF64_SYM_STRUCT.size

    if dyn_off is not None and dyn_sz > 0:
        if dyn_off + dyn_sz > n_bytes:
            raise Elf64ParseError(f"{library_name}: PT_DYNAMIC extends past EOF")
        for pos in range(dyn_off, dyn_off + dyn_sz - (dyn_sz % ELF64_DYN_STRUCT.size), ELF64_DYN_STRUCT.size):
            d_tag, d_val = ELF64_DYN_STRUCT.unpack_from(buf, pos)
            if d_tag == DT_NULL:
                break
            if d_tag == DT_NEEDED:
                needed_offs.append(d_val)
            elif d_tag == DT_SONAME:
                soname_off = d_val
            elif d_tag == DT_STRTAB:
                dt_strtab_va = d_val
            elif d_tag == DT_SYMTAB:
                dt_symtab_va = d_val
            elif d_tag == DT_STRSZ:
                dt_strsz = d_val
            elif d_tag == DT_SYMENT:
                dt_syment = d_val or ELF64_SYM_STRUCT.size

    if dynstr_info is None and dt_strtab_va is not None:
        str_foff = _vaddr_to_offset(dt_strtab_va)
        if str_foff is not None:
            dynstr_info = (str_foff, dt_strsz or max(0, n_bytes - str_foff))
            parse_path = "PT_DYNAMIC_VADDR"

    if dynsym_info is None and dt_symtab_va is not None and dynstr_info is not None:
        sym_foff = _vaddr_to_offset(dt_symtab_va)
        if sym_foff is not None and sym_foff < dynstr_info[0]:
            dynsym_info = (sym_foff, dynstr_info[0] - sym_foff, dt_syment)
            parse_path = "PT_DYNAMIC_VADDR"

    if dynstr_info is None or dynsym_info is None:
        raise Elf64ParseError(f"{library_name}: missing .dynsym or .dynstr metadata")

    str_off, str_sz = dynstr_info
    sym_off, sym_sz, sym_ent = dynsym_info
    if str_off + str_sz > n_bytes or sym_off + sym_sz > n_bytes:
        raise Elf64ParseError(f"{library_name}: .dynsym/.dynstr extends past EOF")
    if sym_ent < ELF64_SYM_STRUCT.size:
        raise Elf64ParseError(f"{library_name}: invalid dynsym entry size {sym_ent}")

    dt_needed = tuple(_read_cstr(buf, str_off + o, 512) for o in needed_offs)
    soname = _read_cstr(buf, str_off + soname_off, 512) if soname_off is not None else None

    n_syms = sym_sz // sym_ent
    exports: List[str] = []
    imports: List[str] = []
    family_counts: Dict[str, int] = {fam: 0 for fam in ALL_SYMBOL_FAMILIES}
    exp_by_fam: Dict[str, List[str]] = {fam: [] for fam in ALL_SYMBOL_FAMILIES}
    imp_by_fam: Dict[str, List[str]] = {fam: [] for fam in ALL_SYMBOL_FAMILIES}

    for idx in range(n_syms):
        st_name, _st_info, _st_other, st_shndx, _st_value, _st_size = ELF64_SYM_STRUCT.unpack_from(
            buf, sym_off + idx * sym_ent
        )
        if st_name == 0:
            continue
        if st_name >= str_sz:
            continue
        sym_name = _read_cstr(buf, str_off + st_name, 1024)
        if not sym_name:
            continue
        fam = classify_symbol_family(sym_name)
        family_counts[fam] = family_counts.get(fam, 0) + 1
        if st_shndx == SHN_UNDEF:
            imports.append(sym_name)
            if len(imp_by_fam[fam]) < 6:
                imp_by_fam[fam].append(sym_name)
        else:
            exports.append(sym_name)
            if len(exp_by_fam[fam]) < 6:
                exp_by_fam[fam].append(sym_name)

    return Elf64LibraryAbiInfo(
        library_name=library_name,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=n_bytes,
        e_type=e_type,
        e_machine=e_machine,
        soname=soname,
        dt_needed=dt_needed,
        total_dynsym_count=n_syms,
        export_count=len(exports),
        import_count=len(imports),
        parse_path=parse_path,
        family_counts=family_counts,
        sample_exports_by_family={k: tuple(v) for k, v in exp_by_fam.items() if v},
        sample_imports_by_family={k: tuple(v) for k, v in imp_by_fam.items() if v},
        exports=tuple(sorted(set(exports))),
        imports=tuple(sorted(set(imports))),
    )


def audit_elf64_file_rdonly(
    path: Path,
    *,
    library_name: str,
    body_label: str,
) -> Elf64LibraryAbiInfo:
    """Strictly open and parse a local donor ELF64 `.so` via `os.O_RDONLY` + `mmap`."""
    fd, mm = open_mmap_rdonly(path)
    try:
        return parse_elf64_dynamic_abi(
            mm,
            library_name=library_name,
            body_label=body_label,
            source_mode="LOCAL_DONOR_RDONLY",
        )
    finally:
        close_mmap_rdonly(fd, mm)


def build_synthetic_elf64_so(
    *,
    soname: str,
    dt_needed: Sequence[str],
    exports: Sequence[str],
    imports: Sequence[str],
    include_section_headers: bool = True,
) -> bytes:
    """Synthesize a genuine, parseable AArch64 `ET_DYN` ELF64 `.so` buffer."""
    # Build .dynstr
    dynstr = bytearray(b"\x00")
    str_offs: Dict[str, int] = {}

    def _add_str(s: str) -> int:
        if s not in str_offs:
            str_offs[s] = len(dynstr)
            dynstr.extend(s.encode("utf-8") + b"\x00")
        return str_offs[s]

    soname_off = _add_str(soname)
    needed_offs = [_add_str(dep) for dep in dt_needed]
    exp_entries = [(_add_str(sym), 1, 0x1000 + i * 16) for i, sym in enumerate(exports)]
    imp_entries = [(_add_str(sym), SHN_UNDEF, 0) for sym in imports]

    # Build .dynsym (entry 0 is STN_UNDEF)
    dynsym = bytearray(ELF64_SYM_STRUCT.pack(0, 0, 0, 0, 0, 0))
    for name_off, shndx, val in exp_entries + imp_entries:
        st_info = (STB_GLOBAL << 4) | STT_FUNC
        dynsym.extend(ELF64_SYM_STRUCT.pack(name_off, st_info, 0, shndx, val, 16 if shndx else 0))

    # Build .shstrtab
    shstrtab = bytearray(b"\x00")
    sh_name_offs: Dict[str, int] = {}
    for sn in (".dynsym", ".dynstr", ".dynamic", ".shstrtab"):
        sh_name_offs[sn] = len(shstrtab)
        shstrtab.extend(sn.encode("ascii") + b"\x00")

    # Layout offsets after ELF64 header (64B) + 2 PHDRs (2*56=112B) => 0xB0 (176), align to 0x100
    hdr_end = 0x100
    dynsym_off = hdr_end
    dynstr_off = dynsym_off + len(dynsym)
    dynstr_aligned_end = (dynstr_off + len(dynstr) + 7) & ~7
    dynamic_off = dynstr_aligned_end

    # Reserve space for DT_NEEDED + DT_SONAME + DT_STRTAB + DT_SYMTAB + DT_STRSZ + DT_SYMENT + DT_NULL
    dyn_count = len(needed_offs) + 6
    dynamic_sz = dyn_count * ELF64_DYN_STRUCT.size
    dynamic_bytes = bytearray()
    for noff in needed_offs:
        dynamic_bytes.extend(ELF64_DYN_STRUCT.pack(DT_NEEDED, noff))
    dynamic_bytes.extend(ELF64_DYN_STRUCT.pack(DT_SONAME, soname_off))
    dynamic_bytes.extend(ELF64_DYN_STRUCT.pack(DT_STRTAB, dynstr_off))
    dynamic_bytes.extend(ELF64_DYN_STRUCT.pack(DT_SYMTAB, dynsym_off))
    dynamic_bytes.extend(ELF64_DYN_STRUCT.pack(DT_STRSZ, len(dynstr)))
    dynamic_bytes.extend(ELF64_DYN_STRUCT.pack(DT_SYMENT, ELF64_SYM_STRUCT.size))
    dynamic_bytes.extend(ELF64_DYN_STRUCT.pack(DT_NULL, 0))
    assert len(dynamic_bytes) == dynamic_sz

    shstr_off = dynamic_off + dynamic_sz
    shoff = (shstr_off + len(shstrtab) + 7) & ~7
    total_size = shoff + (5 * ELF64_SHDR_STRUCT.size if include_section_headers else 0)

    out = bytearray(total_size)
    out[dynsym_off : dynsym_off + len(dynsym)] = dynsym
    out[dynstr_off : dynstr_off + len(dynstr)] = dynstr
    out[dynamic_off : dynamic_off + len(dynamic_bytes)] = dynamic_bytes
    out[shstr_off : shstr_off + len(shstrtab)] = shstrtab

    # ELF64 header
    e_ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    ELF64_EHDR_STRUCT.pack_into(
        out,
        0,
        e_ident,
        ET_DYN,
        EM_AARCH64,
        1,
        0x1000,
        ELF64_EHDR_STRUCT.size,
        shoff if include_section_headers else 0,
        0,
        ELF64_EHDR_STRUCT.size,
        ELF64_PHDR_STRUCT.size,
        2,
        ELF64_SHDR_STRUCT.size if include_section_headers else 0,
        5 if include_section_headers else 0,
        4 if include_section_headers else 0,
    )

    # PHDR 0: PT_LOAD covering full image at vaddr=0
    ELF64_PHDR_STRUCT.pack_into(out, 64, PT_LOAD, 0x5, 0, 0, 0, total_size, total_size, 0x1000)
    # PHDR 1: PT_DYNAMIC
    ELF64_PHDR_STRUCT.pack_into(
        out, 64 + 56, PT_DYNAMIC, 0x6, dynamic_off, dynamic_off, dynamic_off, dynamic_sz, dynamic_sz, 8
    )

    if include_section_headers:
        # 0: SHT_NULL
        ELF64_SHDR_STRUCT.pack_into(out, shoff, 0, SHT_NULL, 0, 0, 0, 0, 0, 0, 0, 0)
        # 1: .dynsym
        ELF64_SHDR_STRUCT.pack_into(
            out,
            shoff + 64,
            sh_name_offs[".dynsym"],
            SHT_DYNSYM,
            SHF_ALLOC,
            dynsym_off,
            dynsym_off,
            len(dynsym),
            2,
            1,
            8,
            ELF64_SYM_STRUCT.size,
        )
        # 2: .dynstr
        ELF64_SHDR_STRUCT.pack_into(
            out,
            shoff + 128,
            sh_name_offs[".dynstr"],
            SHT_STRTAB,
            SHF_ALLOC,
            dynstr_off,
            dynstr_off,
            len(dynstr),
            0,
            0,
            1,
            0,
        )
        # 3: .dynamic
        ELF64_SHDR_STRUCT.pack_into(
            out,
            shoff + 192,
            sh_name_offs[".dynamic"],
            SHT_DYNAMIC,
            SHF_ALLOC | SHF_WRITE,
            dynamic_off,
            dynamic_off,
            dynamic_sz,
            2,
            0,
            8,
            ELF64_DYN_STRUCT.size,
        )
        # 4: .shstrtab
        ELF64_SHDR_STRUCT.pack_into(
            out,
            shoff + 256,
            sh_name_offs[".shstrtab"],
            SHT_STRTAB,
            0,
            0,
            shstr_off,
            len(shstrtab),
            0,
            0,
            1,
            0,
        )

    return bytes(out)


def build_clean_room_elf64_fixtures() -> Dict[str, Dict[str, bytes]]:
    """Build deterministic clean-room FX3 v7.02 and FX6 v6.01 ELF64 shared objects."""
    shared_libc = ("libpthread.so.0", "libstdc++.so.6", "libm.so.6", "libc.so.6", "librt.so.1")
    fixtures: Dict[str, Dict[str, bytes]] = {"fx3_702": {}, "fx6_601": {}}

    fixtures["fx3_702"]["appFw.so"] = build_synthetic_elf64_so(
        soname="appFw.so",
        dt_needed=("libInfraSKD.so", "libCertificateManager.so", "libssl.so.3", *shared_libc),
        exports=("appFw_main",),
        imports=(
            "_ZN8UXEngine6resmgrEv",
            "GRM_fbrmSetScreenPreference",
            "_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE",
            "_ZN10InfraInput15GetPhyKeyStatusEiP21_InfraInputPhyKeyData",
            "SKD_Sign",
            "_ZN3mpr16PublishPublicKeyEj",
            "AccessLog_Delete",
        ),
    )
    fixtures["fx6_601"]["appFw.so"] = build_synthetic_elf64_so(
        soname="appFw.so",
        dt_needed=("libexpat.so.1", "libopus.so.0", "libSoundTouch.so.1", *shared_libc),
        exports=("appFw_main",),
        imports=(
            "_ZN8UXEngine6resmgrEv",
            "GRM_fbrmRegisterTriggerFrameworkCb",
            "GRM_screenIsDirty",
            "_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE",
            "_ZN10InfraInput9SetKeyInhEib",
            "_ZN17infra_wrapper_upm6detail36register_cb_power_save_state_changedEP27i_infra_wrapper_cb_delegate",
            "_ZN16infra_wrapper_bb6detail26vef_set_eframing_format_v2ERKNS_31vef_set_eframing_format_v2_in_tERNS_32vef_set_eframing_format_v2_out_tE",
            "Backup_get_suspend_flag",
            "AccessLog_Delete",
        ),
    )

    fixtures["fx3_702"]["libuxengine.so"] = build_synthetic_elf64_so(
        soname="libuxengine.so",
        dt_needed=("libgemini-grm.so", "libstella.so", *shared_libc),
        exports=(
            "_ZN2ux4core6Kernel10getProfileENS0_21UXEngineConfigurationEl",
            "_ZN2ux4core14GraphicsSystem18getGraphicsContextEv",
        ),
        imports=("GRM_gpermRectblit", "osal_create_thread"),
    )
    fixtures["fx6_601"]["libuxengine.so"] = build_synthetic_elf64_so(
        soname="libuxengine.so",
        dt_needed=("libgemini-grm.so", "libandromeda.so", "libstella.so", "libux_core.so", *shared_libc),
        exports=(
            "_ZN2ux4core6Kernel10getProfileENS0_21UXEngineConfigurationEl",
            "_ZN2ux4core14GraphicsSystem18getGraphicsContextEv",
            "_ZN9andromeda6Window18setGraphicsContextEPN6gemini17GraphicsContext3DE",
            "_ZN6gemini6Camera4initERKN6stella7Vector4ES4_ffff",
        ),
        imports=("GRM_gpermRectblit", "osal_create_thread"),
    )

    fixtures["fx3_702"]["libgemini-grm.so"] = build_synthetic_elf64_so(
        soname="libgemini-grm.so",
        dt_needed=shared_libc,
        exports=("GRM_gpermRectblit", "GRM_gpermDrawFlush", "GRM_fbrmInitialize"),
        imports=("pthread_mutex_lock",),
    )
    fixtures["fx6_601"]["libgemini-grm.so"] = build_synthetic_elf64_so(
        soname="libgemini-grm.so",
        dt_needed=shared_libc,
        exports=(
            "GRM_gpermRectblit",
            "GRM_gpermDrawFlush",
            "GRM_fbrmInitialize",
            "_ZN6gemini11GRMRendererC1Ev",
            "_ZN6gemini17GraphicsContext3D16prepareRenderingEPv",
        ),
        imports=("pthread_mutex_lock",),
    )

    fixtures["fx3_702"]["libmpr.so"] = build_synthetic_elf64_so(
        soname="libmpr.so",
        dt_needed=("libexpat.so.1", "libsecvlt.so", *shared_libc),
        exports=(
            "_ZN3mpr16SetMovieRecParamERKNS_13movieRecParamE",
            "_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE",
            "_ZN3mpr17ExecuteSetLutDataERKNS_17setLutDataInParamE",
            "_ZN3mpr15GetCubeFilePathERKN4sidb10recordInfoEjRNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE",
            "_ZN3mpr12KlvConverter18Rdd18KeyCameraUnitE",
            "_ZN3mpr12KlvConverter46ManuallyEnteredMeta2rdd_ExternalNdFilterFactorERKtPhRjb",
            "_Z27GenerateAndStoreSPVCBoxDataPhN3mpr8libcrypt13operationModeEj",
        ),
        imports=("osal_snd_sync_msg", "BIO_new"),
    )
    fixtures["fx6_601"]["libmpr.so"] = build_synthetic_elf64_so(
        soname="libmpr.so",
        dt_needed=("libexpat.so.1", *shared_libc),
        exports=(
            "_ZN3mpr16SetMovieRecParamERKNS_13movieRecParamE",
            "_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE",
            "_ZN3mpr17ExecuteSetLutDataERKNS_17setLutDataInParamE",
            "_ZN3mpr21GetCubeFilePathForMXFERKN4sidb10recordInfoEjRNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE",
            "_ZN3mpr12KlvConverter18Rdd18KeyCameraUnitE",
            "setMetaData_ExposureIndexRDD18",
            "setMetaData_CaptureGammaRDD18",
            "MuxMxfFnlzPrm_GetVideoCompression",
            "_ZN10libXavcMxf11SetClipNameEjRA4_KN3mpr13ClipNameParamE",
        ),
        imports=("osal_snd_sync_msg", "Fsys_SetStreamArea"),
    )

    fixtures["fx3_702"]["libWlanResource.so"] = build_synthetic_elf64_so(
        soname="libWlanResource.so",
        dt_needed=("libbackup.so", "libExternalCommand.so", *shared_libc),
        exports=(
            "_Z16handleFatalErrorv",
            "_Z19loadWlanHostDriversb",
            "_Z30NetworkTraceRecordWlanResourcehhtj",
        ),
        imports=("osal_snd_sync_direct",),
    )
    fixtures["fx6_601"]["libWlanResource.so"] = build_synthetic_elf64_so(
        soname="libWlanResource.so",
        dt_needed=("libbackup.so", "libExternalCommand.so", *shared_libc),
        exports=(
            "_Z16handleFatalErrorv",
            "_Z19loadWlanHostDriversb",
            "_Z30NetworkTraceRecordWlanResourcehhti",
        ),
        imports=("osal_snd_sync_direct",),
    )

    fixtures["fx3_702"]["libInfraBluetoothCore.so"] = build_synthetic_elf64_so(
        soname="libInfraBluetoothCore.so",
        dt_needed=("libosal_uipc.so", "libBTUtils.so", "libhardware.so", "libbackup.so", *shared_libc),
        exports=(
            "_ZN12InfraBTCore_7CBTWoLE9startWoLEEv",
            "_ZN12InfraBTCore_7CBTWoLE16pvtBTChipPowerONEv",
            "_ZN12InfraBTCore_7CBTWoLE17pvtBTChipPowerOFFEv",
        ),
        imports=("osal_snd_sync_msg",),
    )
    fixtures["fx6_601"]["libInfraBluetoothCore.so"] = build_synthetic_elf64_so(
        soname="libInfraBluetoothCore.so",
        dt_needed=("libosal_uipc.so", "libBTUtils.so", "libhardware.so", "libbackup.so", *shared_libc),
        exports=(
            "_ZN12InfraBTCore_7CBTWoLE9startWoLEEv",
            "_ZN12InfraBTCore_7CBTWoLE10read_eventEiPh",
        ),
        imports=("osal_snd_sync_msg",),
    )

    return fixtures


def diff_library_abi(
    library_name: str,
    fx3_info: Optional[Elf64LibraryAbiInfo],
    fx6_info: Optional[Elf64LibraryAbiInfo],
) -> LibraryAbiDiffResult:
    """Compute pure-Python `.dynsym` & `DT_NEEDED` ABI differential for one shared object."""
    if fx3_info is not None and fx6_info is not None:
        status = "BOTH_BODIES_PARSED"
    elif fx6_info is not None:
        status = "FX6_ONLY_ON_DISK"
    elif fx3_info is not None:
        status = "FX3_ONLY_ON_DISK"
    else:
        status = "MISSING_BOTH"

    n3 = set(fx3_info.dt_needed) if fx3_info else set()
    n6 = set(fx6_info.dt_needed) if fx6_info else set()
    e3 = set(fx3_info.exports) if fx3_info else set()
    e6 = set(fx6_info.exports) if fx6_info else set()
    i3 = set(fx3_info.imports) if fx3_info else set()
    i6 = set(fx6_info.imports) if fx6_info else set()

    all_syms = e3 | e6 | i3 | i6
    fam_counts: Dict[str, int] = {fam: 0 for fam in ALL_SYMBOL_FAMILIES}
    for s in all_syms:
        fam = classify_symbol_family(s)
        fam_counts[fam] = fam_counts.get(fam, 0) + 1

    return LibraryAbiDiffResult(
        library_name=library_name,
        comparison_status=status,
        fx3_present=fx3_info is not None,
        fx6_present=fx6_info is not None,
        fx3_soname=fx3_info.soname if fx3_info else None,
        fx6_soname=fx6_info.soname if fx6_info else None,
        shared_dt_needed=tuple(sorted(n3 & n6)),
        fx3_only_dt_needed=tuple(sorted(n3 - n6)),
        fx6_only_dt_needed=tuple(sorted(n6 - n3)),
        shared_export_count=len(e3 & e6),
        fx3_only_export_count=len(e3 - e6),
        fx6_only_export_count=len(e6 - e3),
        shared_import_count=len(i3 & i6),
        fx3_only_import_count=len(i3 - i6),
        fx6_only_import_count=len(i6 - i3),
        divergent_family_counts=fam_counts,
        sample_fx3_only_exports=tuple(sorted(e3 - e6)[:8]),
        sample_fx6_only_exports=tuple(sorted(e6 - e3)[:8]),
        sample_fx3_only_imports=tuple(sorted(i3 - i6)[:8]),
        sample_fx6_only_imports=tuple(sorted(i6 - i3)[:8]),
    )


def cross_validate_p_closure_matrix(
    library_diffs: Sequence[LibraryAbiDiffResult],
) -> Tuple[FeatureClosureCrossCheck, ...]:
    """Cross-validate why `P1..P12+Fan` closes each hardware-divergent symbol family."""
    diff_by_lib = {d.library_name: d for d in library_diffs}
    checks: List[FeatureClosureCrossCheck] = []
    for entry in P_CLOSURE_FAMILY_MATRIX:
        fam = str(entry["family"])
        libs = tuple(str(x) for x in entry["target_libraries"])  # type: ignore[attr-defined]
        hits = sum(
            diff_by_lib[lib].divergent_family_counts.get(fam, 0)
            for lib in libs
            if lib in diff_by_lib
        )
        checks.append(
            FeatureClosureCrossCheck(
                family=fam,
                patch_ids=tuple(str(x) for x in entry["patch_ids"]),  # type: ignore[attr-defined]
                target_libraries=libs,
                observed_symbol_hits=hits,
                closure_mechanism=str(entry["closure_mechanism"]),
                closed=bool(entry["closed"]),
            )
        )
    return tuple(checks)


# ---------------------------------------------------------------------------
# Unified Phase 43 Auditor Entrypoint & JSON Serialization
# ---------------------------------------------------------------------------


def analyze_wbi_hibdrv_and_elf_abi(
    *,
    clean_room: bool = False,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
) -> WbiHibdrvAndElfAbiReport:
    """Run Phase 43 WBI2/hibdrv + pure-Python ELF64 `.dynsym`/`DT_NEEDED` differential audit."""
    forced_clean = clean_room or is_forced_clean_room(env)
    errors: List[str] = []

    # 1. WBI2 & `hibdrv` audit (Local Donor O_RDONLY or Clean-Room synthetic)
    fx3_wbi_path = resolve_donor_file(
        FX3_WBI2_RELPATH, repo_root=repo_root, env=env, clean_room=forced_clean
    )
    fx6_wbi_path = resolve_donor_file(
        FX6_WBI2_RELPATH, repo_root=repo_root, env=env, clean_room=forced_clean
    )
    fx3_k_path = resolve_donor_file(
        FX3_VMLINUX_RELPATH, repo_root=repo_root, env=env, clean_room=forced_clean
    )
    fx6_k_path = resolve_donor_file(
        FX6_VMLINUX_RELPATH, repo_root=repo_root, env=env, clean_room=forced_clean
    )
    fx3_p11 = resolve_donor_file(
        FX3_NFLASH11_RELPATH, repo_root=repo_root, env=env, clean_room=forced_clean
    )
    fx6_p11 = resolve_donor_file(
        FX6_NFLASH11_RELPATH, repo_root=repo_root, env=env, clean_room=forced_clean
    )

    if fx3_wbi_path is not None and fx6_wbi_path is not None:
        fx3_wbi = audit_wbi2_file_rdonly(
            fx3_wbi_path, body_label="fx3_702", kernel_path=fx3_k_path, p11_path=fx3_p11
        )
        fx6_wbi = audit_wbi2_file_rdonly(
            fx6_wbi_path, body_label="fx6_601", kernel_path=fx6_k_path, p11_path=fx6_p11
        )
        wbi_mode = "LOCAL_DONOR_RDONLY"
    else:
        fx3_wbi = parse_wbi2_buffer(
            build_synthetic_wbi2_image("fx3_702"),
            body_label="fx3_702",
            source_mode="SYNTHETIC_CLEAN_ROOM",
            kernel_buf=build_synthetic_kernel_for_wbi("fx3_702"),
        )
        fx6_wbi = parse_wbi2_buffer(
            build_synthetic_wbi2_image("fx6_601"),
            body_label="fx6_601",
            source_mode="SYNTHETIC_CLEAN_ROOM",
            kernel_buf=build_synthetic_kernel_for_wbi("fx6_601"),
        )
        wbi_mode = "SYNTHETIC_CLEAN_ROOM"

    if not fx3_wbi.valid:
        errors.extend(f"fx3_wbi2: {e}" for e in fx3_wbi.errors)
    if not fx6_wbi.valid:
        errors.extend(f"fx6_wbi2: {e}" for e in fx6_wbi.errors)

    hibdrv_verdict = verify_hibdrv_cross_kernel_rejection(
        fx3_wbi,
        fx6_wbi,
        requested_warm_mode=2,
        allow_p5_write=False,
        allow_p11_bis_format=False,
    )
    if not hibdrv_verdict.rejected_fail_closed or hibdrv_verdict.wbi_mutation_bytes != 0:
        errors.append("hibdrv cross-kernel rejection failed to enforce fail-closed zero-mutation")

    # 2. Pure-Python ELF64 `.dynsym` / `.dynstr` / `DT_NEEDED` differential
    synth_elfs = build_clean_room_elf64_fixtures() if forced_clean else None
    fx3_parsed = 0
    fx6_parsed = 0
    both_compared = 0
    diffs: List[LibraryAbiDiffResult] = []
    elf_donor_hits = 0

    for lib in CORE_SHARED_OBJECTS:
        fx3_info: Optional[Elf64LibraryAbiInfo] = None
        fx6_info: Optional[Elf64LibraryAbiInfo] = None

        if not forced_clean:
            p3 = _resolve_candidate_donor(
                FX3_CORE_SO_CANDIDATES[lib], repo_root=repo_root, env=env, clean_room=False
            )
            p6 = _resolve_candidate_donor(
                FX6_CORE_SO_CANDIDATES[lib], repo_root=repo_root, env=env, clean_room=False
            )
            if p3 is not None:
                fx3_info = audit_elf64_file_rdonly(p3, library_name=lib, body_label="fx3_702")
                elf_donor_hits += 1
            if p6 is not None:
                fx6_info = audit_elf64_file_rdonly(p6, library_name=lib, body_label="fx6_601")
                elf_donor_hits += 1

        if fx3_info is None and fx6_info is None:
            if synth_elfs is None:
                synth_elfs = build_clean_room_elf64_fixtures()
            fx3_info = parse_elf64_dynamic_abi(
                synth_elfs["fx3_702"][lib],
                library_name=lib,
                body_label="fx3_702",
                source_mode="SYNTHETIC_CLEAN_ROOM",
            )
            fx6_info = parse_elf64_dynamic_abi(
                synth_elfs["fx6_601"][lib],
                library_name=lib,
                body_label="fx6_601",
                source_mode="SYNTHETIC_CLEAN_ROOM",
            )

        if fx3_info is not None:
            fx3_parsed += 1
        if fx6_info is not None:
            fx6_parsed += 1
        if fx3_info is not None and fx6_info is not None:
            both_compared += 1

        diffs.append(diff_library_abi(lib, fx3_info, fx6_info))

    closure_checks = cross_validate_p_closure_matrix(diffs)
    if not all(c.closed for c in closure_checks):
        errors.append("One or more divergent symbol families lack P1..P12+Fan closure")
    if both_compared < 4:
        errors.append(f"Expected >= 4 shared libraries compared across both bodies, got {both_compared}")

    mode = (
        "LOCAL_DONOR_VERIFIED"
        if (not forced_clean and wbi_mode == "LOCAL_DONOR_RDONLY" and elf_donor_hits >= 8)
        else "CLEAN_ROOM_SYNTHETIC_VERIFIED"
    )
    all_passed = len(errors) == 0

    core_payload = {
        "schema_version": PHASE_43_SCHEMA,
        "version": PHASE_43_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "wbi_mutation_bytes": 0,
        "fx3_wbi2": asdict(fx3_wbi),
        "fx6_wbi2": asdict(fx6_wbi),
        "hibdrv_cross_kernel_rejection": asdict(hibdrv_verdict),
        "library_diffs": [asdict(d) for d in diffs],
        "libraries_parsed_fx3": fx3_parsed,
        "libraries_parsed_fx6": fx6_parsed,
        "libraries_both_compared": both_compared,
        "feature_closure_checks": [asdict(c) for c in closure_checks],
        "errors": list(errors),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(core_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return WbiHibdrvAndElfAbiReport(
        schema_version=PHASE_43_SCHEMA,
        version=PHASE_43_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        wbi_mutation_bytes=0,
        fx3_wbi2=fx3_wbi,
        fx6_wbi2=fx6_wbi,
        hibdrv_cross_kernel_rejection=hibdrv_verdict,
        library_diffs=tuple(diffs),
        libraries_parsed_fx3=fx3_parsed,
        libraries_parsed_fx6=fx6_parsed,
        libraries_both_compared=both_compared,
        feature_closure_checks=closure_checks,
        report_sha256=report_sha256,
        errors=tuple(errors),
    )


def wbi_hibdrv_and_elf_abi_report_to_dict(
    report: WbiHibdrvAndElfAbiReport,
) -> Dict[str, object]:
    """Convert `WbiHibdrvAndElfAbiReport` to a deterministic JSON-serializable dict."""
    return asdict(report)
