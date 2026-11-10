"""Phase 5 — Five Core Camera Feature Routing & Cross-Model ELF Dynamic Symbol Closure Verifier.

Implements Blueprint §3 (`reports/2026-11-07-fx6-on-fx3-spoofing-and-pruning-plan/README.md`)
across three independent verification dimensions:

- **Dimension A (Cross-Library `DT_NEEDED` & `.dynsym` Dynamic Symbol Closure Audit)**:
  Parses ELF64 `.dynamic` (`DT_NEEDED`, `DT_SONAME`, `DT_FLAGS`/`DT_BIND_NOW`) and `.dynsym`
  import/export symbol tables across all 10 core camera feature libraries
  (`appFw.so`, `libuxengine.so`, `libgrm.so`, `libInfraSetupFile.so`,
  `libInfraLensCommunicator.so`, `libInfraMediaMount.so`, `libInfraMediaCommon.so`,
  `libInfraMediaConfig.so`, `libmpr.so`, `libfan.so`), combines them with the FX6 initrd/base
  system shared libraries (`nested-files/nflasha1-initrd/lib`) and `im.elf` host binary, proves
  100% `DT_NEEDED` transitive dependency closure (43 shared objects, 0 missing), audits symbol
  import/export counts, and verifies exact VMA + file offsets of core interface symbols across
  all 5 camera features.

- **Dimension B (16x User 3D `.cube` LUT Spec Generator/Validator & FX3 `p30` 48 MiB Budget)**:
  Provides a deterministic Sony-compatible `.cube` 3D LUT generator and strict syntax/domain
  validator supporting `17^3` (4,913 RGB triples) and `33^3` (35,937 RGB triples) grids,
  `TITLE`, `LUT_3D_SIZE`, `DOMAIN_MIN`/`DOMAIN_MAX`, and floating-point RGB bounds; proves via
  exact VFAT cluster allocation math that 16 full-spec `33^3` `.cube` files plus filesystem
  directory/FAT overhead fit inside FX3 `p30` (`48 MiB` = `50,331,648` bytes) with >50% free
  headroom; and audits the `libInfraSetupFile.so` `SetupFile::RcvThread` (`0x196c8..0x196e0`)
  call chain mounting `/usr/data/lut/` as `vfat` (`posix_attr`, `0xc0ed0480`) via `mount@plt`.

- **Dimension C (Cine EI / E-Mount AF / CFexpress+SD Dual-Slot Unicorn & Disassembly Contracts)**:
  Audits `appFw.so` entrypoints and `.rodata` contracts for Cine EI base picture settings
  (`set_base_picture_setting_procam_i` @ `0x21126d8`), 3D LUT binary injection
  (`set_user_lut_binary_data_procam_i` @ `0x2112b10` -> `libmpr.so` `mpr::SetLutData`), and
  E-Mount Fast Hybrid AF (`set_af_area_i` @ `0x211066c`, `set_eye_af_mode_i` @ `0x2110e44` +
  `libInfraLensCommunicator.so`); executes `set_eye_af_mode_i` in Unicorn AArch64; and executes
  `libmpr.so` `libXavcMxfGetSlotTypeFromMediaId` (`+0x53c850`) in Unicorn AArch64 to prove
  standard dual-slot IDs (`0x1000` = Slot A -> slot index `0`, `0x1010` = Slot B -> slot index `1`)
  return cleanly with zero assertions while uninitialized `0` hits the assertion path at
  `libXavcMxf.cpp:274`.
"""

from __future__ import annotations

import math
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .patcher import (
    DEFAULT_FX6_DONOR_LIB_DIR,
    P1_LIB_INFRA_SETUP_FILE_SPEC,
    PatchVerificationError,
    apply_patch_spec,
)


UNICORN_SITE_PACKAGES = Path(
    "/Volumes/KAFU2T/AI/Orca/Worktrees/Phayen/dugong/work/firmware-reverse-2026-10-22"
    "/tools/venv/lib/python3.14/site-packages"
)

DEFAULT_FX6_DONOR_BIN_DIR = (
    DEFAULT_FX6_DONOR_LIB_DIR.parent / "bin"
)
DEFAULT_FX6_INITRD_LIB_DIR = (
    DEFAULT_FX6_DONOR_LIB_DIR.parents[1] / "nested-files" / "nflasha1-initrd" / "lib"
)

CORE_CAMERA_FEATURE_LIBRARIES: Tuple[str, ...] = (
    "appFw.so",
    "libuxengine.so",
    "libgrm.so",
    "libInfraSetupFile.so",
    "libInfraLensCommunicator.so",
    "libInfraMediaMount.so",
    "libInfraMediaCommon.so",
    "libInfraMediaConfig.so",
    "libmpr.so",
    "libfan.so",
)

# ELF64 Dynamic Tags & Flags
DT_NULL = 0
DT_NEEDED = 1
DT_SONAME = 14
DT_BIND_NOW = 24
DT_FLAGS = 30
DT_FLAGS_1 = 0x6FFFFFFB
DF_BIND_NOW = 0x8
DF_1_NOW = 0x1
STB_WEAK = 2

# FX3 p30 VFAT User LUT Partition Geometry (`nflasha30`: 0x00018000 sectors * 512 B = 48 MiB)
FX3_P30_SECTOR_COUNT = 0x00018000
FX3_P30_BYTES_PER_SECTOR = 512
FX3_P30_TOTAL_BYTES = FX3_P30_SECTOR_COUNT * FX3_P30_BYTES_PER_SECTOR  # 50,331,648 B (48 MiB)
SUPPORTED_SONY_CUBE_GRID_SIZES: Tuple[int, ...] = (17, 33)

# Dimension B: libInfraSetupFile.so SetupFile::RcvThread VFAT Mount Call Chain Constants
SETUPFILE_RCVTHREAD_SYM = "_ZN14InfraSetupFile9SetupFile9RcvThreadEPv"
SETUPFILE_RCVTHREAD_VMA = 0x19650
SETUPFILE_DEV_SOURCE_SYM = "_ZN14InfraSetupFile9SetupFile10MOUNT_PATHE"
SETUPFILE_DEV_SOURCE_VMA = 0x25E90
SETUPFILE_LUT_HOME_SYM = "_ZN14InfraSetupFile16LutFileIntMemory9HOME_PATHE"
SETUPFILE_LUT_HOME_VMA = 0x286C8
SETUPFILE_POSIX_ATTR_VMA = 0x26652
SETUPFILE_VFAT_FSTYPE_VMA = 0x2665D
SETUPFILE_MOUNT_PLT_VMA = 0x144F0
SETUPFILE_GOT_TARGET_DIR = 0x3FD70
SETUPFILE_GOT_SOURCE_DEV = 0x3FFB8
SETUPFILE_EXPECTED_MOUNT_INSNS: Tuple[Tuple[int, int, str], ...] = (
    (0x196C8, 0xD2809003, "mov x3, #0x480"),
    (0x196CC, 0x91194884, "add x4, x4, #0x652 ; 'posix_attr'"),
    (0x196D0, 0xF946BB01, "ldr x1, [x24, #0xd70] ; GOT '/usr/data/lut/'"),
    (0x196D4, 0x91197442, "add x2, x2, #0x65d ; 'vfat'"),
    (0x196D8, 0xF947DC00, "ldr x0, [x0, #0xfb8] ; GOT '/dev/nflasha20'->'/dev/nflasha30'"),
    (0x196DC, 0xF2B81DA3, "movk x3, #0xc0ed, lsl #16 ; MS_MGC_VAL|0x480"),
    (0x196E0, 0x97FFEB84, "bl 0x144f0 ; mount@plt"),
)

# Dimension C: appFw.so & libmpr.so Core Camera Feature Entrypoints
APPFW_SET_BASE_PICTURE_VMA = 0x21126D8
APPFW_SET_BASE_PICTURE_SIG_VMA = 0x261BF40
APPFW_SET_USER_LUT_BIN_VMA = 0x2112B10
APPFW_SET_USER_LUT_BIN_SIG_VMA = 0x261C0C0
APPFW_SET_AF_AREA_VMA = 0x211066C
APPFW_SET_AF_AREA_SIG_VMA = 0x261CC98
APPFW_SET_EYE_AF_MODE_VMA = 0x2110E44
APPFW_SET_EYE_AF_MODE_SIG_VMA = 0x26191E8
APPFW_ASSERT_HELPER_VMA = 0x2167784

MPR_SLOT_TYPE_FROM_MEDIA_ID_VMA = 0x53C850
MPR_SLOT_TYPE_ASSERT_PLT_VMA = 0xF14E0
MEDIA_ID_SLOT_A = 0x1000
MEDIA_ID_SLOT_B = 0x1010
MEDIA_ID_UNINITIALIZED = 0x0


def _load_unicorn():
    if UNICORN_SITE_PACKAGES.is_dir() and str(UNICORN_SITE_PACKAGES) not in sys.path:
        sys.path.insert(0, str(UNICORN_SITE_PACKAGES))
    import unicorn as uc  # type: ignore
    from unicorn import arm64_const as uc_arm64  # type: ignore

    return uc, uc_arm64


@dataclass(frozen=True)
class KeySymbolSpec:
    feature_id: str
    library_name: str
    symbol_name: str
    expected_vma: int


KEY_FEATURE_SYMBOL_SPECS: Tuple[KeySymbolSpec, ...] = (
    # Feature (a): 1280x720 Cinema UI / Big6 Status Screen
    KeySymbolSpec(
        feature_id="a_cinema_ui_big6",
        library_name="libuxengine.so",
        symbol_name="_ZN2ux6gfxeng6Screen20setAreaInFramebufferEsstt",
        expected_vma=0x7B66C,
    ),
    KeySymbolSpec(
        feature_id="a_cinema_ui_big6",
        library_name="libuxengine.so",
        symbol_name="_ZN2ux6wgtsys6Widget7setSizeEff",
        expected_vma=0xA2368,
    ),
    KeySymbolSpec(
        feature_id="a_cinema_ui_big6",
        library_name="libgrm.so",
        symbol_name="_ZN3grm11FrameBuffer7setSizeEtt",
        expected_vma=0x2303C,
    ),
    # Feature (b): IMX510 + BIONZ XR Full-Frame Cine EI / S-Cinetone / S-Log3 Color Pipeline
    KeySymbolSpec(
        feature_id="b_fullframe_cine_ei_color",
        library_name="libmpr.so",
        symbol_name="_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE",
        expected_vma=0x1505A8,
    ),
    KeySymbolSpec(
        feature_id="b_fullframe_cine_ei_color",
        library_name="libmpr.so",
        symbol_name="_ZN3mpr17ExecuteSetLutDataERKNS_17setLutDataInParamE",
        expected_vma=0x150358,
    ),
    # Feature (c): 16x User 3D .cube LUT Storage & VFAT Mount Pipeline
    KeySymbolSpec(
        feature_id="c_user_3d_cube_lut",
        library_name="libInfraSetupFile.so",
        symbol_name=SETUPFILE_RCVTHREAD_SYM,
        expected_vma=SETUPFILE_RCVTHREAD_VMA,
    ),
    KeySymbolSpec(
        feature_id="c_user_3d_cube_lut",
        library_name="libInfraSetupFile.so",
        symbol_name=SETUPFILE_DEV_SOURCE_SYM,
        expected_vma=SETUPFILE_DEV_SOURCE_VMA,
    ),
    KeySymbolSpec(
        feature_id="c_user_3d_cube_lut",
        library_name="libInfraSetupFile.so",
        symbol_name=SETUPFILE_LUT_HOME_SYM,
        expected_vma=SETUPFILE_LUT_HOME_VMA,
    ),
    # Feature (d): E-Mount Fast Hybrid AF & Lens Communication
    KeySymbolSpec(
        feature_id="d_emount_autofocus",
        library_name="libInfraLensCommunicator.so",
        symbol_name="_ZN16LensCommunicatorC1Ev",
        expected_vma=0x16E0,
    ),
    KeySymbolSpec(
        feature_id="d_emount_autofocus",
        library_name="libInfraLensCommunicator.so",
        symbol_name="_ZN16LensCommunicator11FinalizeCmdEP16__extcmd_svc_msg",
        expected_vma=0x18A4,
    ),
    KeySymbolSpec(
        feature_id="d_emount_autofocus",
        library_name="libInfraLensCommunicator.so",
        symbol_name="LensCommunicator_Exit",
        expected_vma=0x229C,
    ),
    # Feature (e): Dual-Slot CFexpress Type A + SDXC Media & Thermal Fan Control
    KeySymbolSpec(
        feature_id="e_dualslot_media_and_fan",
        library_name="libInfraMediaMount.so",
        symbol_name="_ZN19InfraMediaMountMcmd9IMM_MountEiPPc",
        expected_vma=0x819C,
    ),
    KeySymbolSpec(
        feature_id="e_dualslot_media_and_fan",
        library_name="libInfraMediaMount.so",
        symbol_name="_ZN21InfraMediaMountThread11StartThreadEv",
        expected_vma=0xAA38,
    ),
    KeySymbolSpec(
        feature_id="e_dualslot_media_and_fan",
        library_name="libInfraMediaCommon.so",
        symbol_name="mcmn_drv_nvme_ioctl_io_cmd",
        expected_vma=0x31D50,
    ),
    KeySymbolSpec(
        feature_id="e_dualslot_media_and_fan",
        library_name="libInfraMediaCommon.so",
        symbol_name="mcmn_drv_scsi_open",
        expected_vma=0x3E530,
    ),
    KeySymbolSpec(
        feature_id="e_dualslot_media_and_fan",
        library_name="libInfraMediaConfig.so",
        symbol_name="_ZN20InfraMediaConfigMcmd20IMCFG_Offset2MediaIdEiPPc",
        expected_vma=0x7210,
    ),
    KeySymbolSpec(
        feature_id="e_dualslot_media_and_fan",
        library_name="libInfraMediaConfig.so",
        symbol_name="_ZN16InfraMediaConfig11GetMediaNumEPN19DefInfraMediaConfig18GetMediaNumPayloadE",
        expected_vma=0x4610,
    ),
    KeySymbolSpec(
        feature_id="e_dualslot_media_and_fan",
        library_name="libfan.so",
        symbol_name="fan_infra_init",
        expected_vma=0x1C80,
    ),
    KeySymbolSpec(
        feature_id="e_dualslot_media_and_fan",
        library_name="libfan.so",
        symbol_name="_Z19fan_i_bkup_is_validv",
        expected_vma=0x1DEC,
    ),
)

CORE_FEATURE_REQUIRED_IMPORTS: Tuple[Tuple[str, str], ...] = (
    ("appFw.so", "_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE"),
    ("appFw.so", "_ZNK2ux6wgtsys6Widget14getFilterColorEv"),
    ("appFw.so", "GRM_fbrmUnlockSwap"),
    ("libInfraMediaMount.so", "mcmn_drv_setowner"),
)


@dataclass(frozen=True)
class ElfDynamicMetadata:
    file_name: str
    file_size: int
    soname: Optional[str]
    dt_needed: Tuple[str, ...]
    bind_now: bool
    pt_loads: Tuple[Tuple[int, int, int, int], ...]  # (vaddr, offset, filesz, memsz)
    exports: Dict[str, Tuple[int, int]]  # name -> (st_value, st_size)
    strong_imports: Tuple[str, ...]
    weak_imports: Tuple[str, ...]
    rela_dyn: Dict[int, Tuple[int, Optional[str], int]]  # r_offset -> (r_type, sym_name, addend)


def _vma_to_file_offset(pt_loads: Sequence[Tuple[int, int, int, int]], vma: int) -> Optional[int]:
    for vaddr, f_off, filesz, _memsz in pt_loads:
        if vaddr <= vma < vaddr + filesz:
            return f_off + (vma - vaddr)
    return None


def _read_c_string(buf: bytes, offset: int) -> str:
    if offset < 0 or offset >= len(buf):
        return ""
    end = buf.find(b"\x00", offset)
    if end < 0:
        end = len(buf)
    return buf[offset:end].decode("ascii", errors="replace")


def parse_elf64_dynamic_metadata(blob: bytes, file_name: str = "<memory>") -> ElfDynamicMetadata:
    """Parse ELF64 `PT_LOAD`, `.dynamic`, `.dynsym`, and `.rela.dyn` tables in pure Python."""
    if len(blob) < 64 or blob[:4] != b"\x7fELF" or blob[4] != 2 or blob[5] != 1:
        raise ValueError(f"{file_name}: invalid ELF64 little-endian header")

    e_machine = struct.unpack_from("<H", blob, 0x12)[0]
    if e_machine != 0xB7:
        raise ValueError(f"{file_name}: expected EM_AARCH64 (0xb7), got 0x{e_machine:x}")

    e_phoff = struct.unpack_from("<Q", blob, 0x20)[0]
    e_shoff = struct.unpack_from("<Q", blob, 0x28)[0]
    e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(
        "<HHHHH", blob, 0x36
    )

    pt_loads: List[Tuple[int, int, int, int]] = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, _p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, _p_align = (
            struct.unpack_from("<IIQQQQQQ", blob, off)
        )
        if p_type == 1:  # PT_LOAD
            pt_loads.append((p_vaddr, p_offset, p_filesz, p_memsz))

    shstr_hdr_off = e_shoff + e_shstrndx * e_shentsize
    _, _, _, _, shstr_off, shstr_sz, _, _, _, _ = struct.unpack_from(
        "<IIQQQQIIQQ", blob, shstr_hdr_off
    )
    shstr = blob[shstr_off : shstr_off + shstr_sz]

    sections: Dict[str, Tuple[int, int, int]] = {}
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        (
            sh_name,
            _sh_type,
            _sh_flags,
            _sh_addr,
            sh_offset,
            sh_size,
            _sh_link,
            _sh_info,
            _sh_addralign,
            sh_entsize,
        ) = struct.unpack_from("<IIQQQQIIQQ", blob, off)
        sec_name = _read_c_string(shstr, sh_name)
        sections[sec_name] = (sh_offset, sh_size, sh_entsize)

    dynstr = b""
    if ".dynstr" in sections:
        doff, dsz, _ = sections[".dynstr"]
        dynstr = blob[doff : doff + dsz]

    soname: Optional[str] = None
    needed: List[str] = []
    bind_now = False
    if ".dynamic" in sections:
        off, sz, entsz = sections[".dynamic"]
        step = entsz or 16
        for pos in range(off, off + sz, step):
            d_tag, d_val = struct.unpack_from("<qQ", blob, pos)
            if d_tag == DT_NULL:
                break
            if d_tag == DT_NEEDED:
                needed.append(_read_c_string(dynstr, d_val))
            elif d_tag == DT_SONAME:
                soname = _read_c_string(dynstr, d_val)
            elif d_tag == DT_BIND_NOW:
                bind_now = True
            elif d_tag == DT_FLAGS and (d_val & DF_BIND_NOW):
                bind_now = True
            elif d_tag == DT_FLAGS_1 and (d_val & DF_1_NOW):
                bind_now = True

    exports: Dict[str, Tuple[int, int]] = {}
    strong_imports: List[str] = []
    weak_imports: List[str] = []
    dynsym_names_by_idx: List[Optional[str]] = []
    if ".dynsym" in sections:
        off, sz, entsz = sections[".dynsym"]
        step = entsz or 24
        for pos in range(off, off + sz, step):
            st_name, st_info, _st_other, st_shndx, st_value, st_size = struct.unpack_from(
                "<IBBHQQ", blob, pos
            )
            if st_name == 0:
                dynsym_names_by_idx.append(None)
                continue
            sym_name = _read_c_string(dynstr, st_name)
            dynsym_names_by_idx.append(sym_name)
            bind = st_info >> 4
            if st_shndx == 0:
                if bind == STB_WEAK:
                    weak_imports.append(sym_name)
                else:
                    strong_imports.append(sym_name)
            else:
                exports[sym_name] = (st_value, st_size)

    rela_dyn: Dict[int, Tuple[int, Optional[str], int]] = {}
    if ".rela.dyn" in sections:
        off, sz, entsz = sections[".rela.dyn"]
        step = entsz or 24
        for pos in range(off, off + sz, step):
            r_off, r_info, r_addend = struct.unpack_from("<QQq", blob, pos)
            r_type = r_info & 0xFFFFFFFF
            sym_idx = r_info >> 32
            sym_nm = (
                dynsym_names_by_idx[sym_idx]
                if 0 <= sym_idx < len(dynsym_names_by_idx)
                else None
            )
            rela_dyn[r_off] = (r_type, sym_nm, r_addend)

    return ElfDynamicMetadata(
        file_name=file_name,
        file_size=len(blob),
        soname=soname,
        dt_needed=tuple(needed),
        bind_now=bind_now,
        pt_loads=tuple(pt_loads),
        exports=exports,
        strong_imports=tuple(strong_imports),
        weak_imports=tuple(weak_imports),
        rela_dyn=rela_dyn,
    )


# ---------------------------------------------------------------------------
# Dimension A: Cross-Library DT_NEEDED & .dynsym Closure Audit
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoreLibrarySymbolAudit:
    library_name: str
    soname: Optional[str]
    file_size: int
    dt_needed: Tuple[str, ...]
    missing_dt_needed: Tuple[str, ...]
    bind_now: bool
    export_count: int
    strong_import_count: int
    weak_import_count: int
    resolved_strong_import_count: int
    unresolved_lazy_dead_count: int


@dataclass(frozen=True)
class KeySymbolVerification:
    feature_id: str
    library_name: str
    symbol_name: str
    expected_vma: int
    actual_vma: Optional[int]
    symbol_size: int
    file_offset: Optional[int]
    verified: bool


@dataclass(frozen=True)
class ElfSymbolClosureAuditReport:
    all_checks_passed: bool
    core_library_count: int
    transitive_closure_count: int
    missing_transitive_needed: Tuple[str, ...]
    total_core_exports: int
    total_core_strong_imports: int
    total_core_resolved_strong_imports: int
    strict_zero_unresolved_lib_count: int
    libraries: Tuple[CoreLibrarySymbolAudit, ...]
    key_symbols: Tuple[KeySymbolVerification, ...]
    required_imports_verified: bool


def audit_core_elf_symbol_closure(
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx6_initrd_lib_dir: Path = DEFAULT_FX6_INITRD_LIB_DIR,
    fx6_bin_dir: Path = DEFAULT_FX6_DONOR_BIN_DIR,
    required_core_libs: Sequence[str] = CORE_CAMERA_FEATURE_LIBRARIES,
) -> ElfSymbolClosureAuditReport:
    """Audit ELF64 `DT_NEEDED` transitive closure and `.dynsym` symbol integrity across core libs."""
    provider_index: Dict[str, Path] = {}
    parsed_cache: Dict[Path, ElfDynamicMetadata] = {}
    universe_exports: Set[str] = set()

    def _get_meta(path: Path) -> ElfDynamicMetadata:
        resolved = path.resolve()
        if resolved not in parsed_cache:
            parsed_cache[resolved] = parse_elf64_dynamic_metadata(
                resolved.read_bytes(), file_name=path.name
            )
        return parsed_cache[resolved]

    for search_dir in (fx6_lib_dir, fx6_initrd_lib_dir):
        if not search_dir.is_dir():
            continue
        for entry in sorted(search_dir.iterdir()):
            if not entry.is_file():
                continue
            with entry.open("rb") as fh:
                raw_head = fh.read(6)
            if raw_head[:4] != b"\x7fELF" or raw_head[4] != 2 or raw_head[5] != 1:
                continue
            meta = _get_meta(entry)
            provider_index.setdefault(entry.name, entry)
            if meta.soname:
                provider_index.setdefault(meta.soname, entry)
            universe_exports.update(meta.exports.keys())

    im_elf = fx6_bin_dir / "im.elf"
    if im_elf.is_file():
        im_meta = _get_meta(im_elf)
        universe_exports.update(im_meta.exports.keys())

    # 1. Transitive DT_NEEDED closure walk starting from all 10 core libraries
    visited: Set[str] = set()
    queue: List[str] = list(required_core_libs)
    missing_transitive: List[str] = []
    while queue:
        cur = queue.pop(0)
        if cur in visited:
            continue
        visited.add(cur)
        if cur not in provider_index:
            missing_transitive.append(cur)
            continue
        cur_meta = _get_meta(provider_index[cur])
        for dep in cur_meta.dt_needed:
            if dep not in visited:
                queue.append(dep)

    # 2. Per-library .dynamic & .dynsym audit
    lib_audits: List[CoreLibrarySymbolAudit] = []
    core_meta_by_name: Dict[str, ElfDynamicMetadata] = {}
    total_exports = 0
    total_strong_imports = 0
    total_resolved_strong = 0
    strict_zero_unres_cnt = 0
    all_libs_present = True

    for lib_name in required_core_libs:
        lib_path = fx6_lib_dir / lib_name
        if not lib_path.is_file():
            all_libs_present = False
            continue
        meta = _get_meta(lib_path)
        core_meta_by_name[lib_name] = meta
        missing_direct = tuple(dep for dep in meta.dt_needed if dep not in provider_index)
        resolved_cnt = sum(1 for sym in meta.strong_imports if sym in universe_exports)
        unres_cnt = len(meta.strong_imports) - resolved_cnt
        if unres_cnt == 0:
            strict_zero_unres_cnt += 1

        total_exports += len(meta.exports)
        total_strong_imports += len(meta.strong_imports)
        total_resolved_strong += resolved_cnt

        lib_audits.append(
            CoreLibrarySymbolAudit(
                library_name=lib_name,
                soname=meta.soname,
                file_size=meta.file_size,
                dt_needed=meta.dt_needed,
                missing_dt_needed=missing_direct,
                bind_now=meta.bind_now,
                export_count=len(meta.exports),
                strong_import_count=len(meta.strong_imports),
                weak_import_count=len(meta.weak_imports),
                resolved_strong_import_count=resolved_cnt,
                unresolved_lazy_dead_count=unres_cnt,
            )
        )

    # 3. Verify exact VMA & file offsets of all key camera feature interface symbols
    key_verifications: List[KeySymbolVerification] = []
    for spec in KEY_FEATURE_SYMBOL_SPECS:
        meta = core_meta_by_name.get(spec.library_name)
        if meta is None or spec.symbol_name not in meta.exports:
            key_verifications.append(
                KeySymbolVerification(
                    feature_id=spec.feature_id,
                    library_name=spec.library_name,
                    symbol_name=spec.symbol_name,
                    expected_vma=spec.expected_vma,
                    actual_vma=None,
                    symbol_size=0,
                    file_offset=None,
                    verified=False,
                )
            )
            continue
        actual_vma, sym_sz = meta.exports[spec.symbol_name]
        f_off = _vma_to_file_offset(meta.pt_loads, actual_vma)
        ok = actual_vma == spec.expected_vma and f_off is not None and f_off > 0
        key_verifications.append(
            KeySymbolVerification(
                feature_id=spec.feature_id,
                library_name=spec.library_name,
                symbol_name=spec.symbol_name,
                expected_vma=spec.expected_vma,
                actual_vma=actual_vma,
                symbol_size=sym_sz,
                file_offset=f_off,
                verified=ok,
            )
        )

    # 4. Verify critical cross-library imports exist in consumer .dynsym AND provider .dynsym
    req_imports_ok = True
    for consumer_lib, sym_name in CORE_FEATURE_REQUIRED_IMPORTS:
        c_meta = core_meta_by_name.get(consumer_lib)
        if c_meta is None or sym_name not in c_meta.strong_imports or sym_name not in universe_exports:
            req_imports_ok = False

    # Any library with uncalled SDK dead-code PLT imports must use lazy binding (bind_now == False)
    lazy_plt_safe = all(
        (aud.unresolved_lazy_dead_count == 0) or (not aud.bind_now)
        for aud in lib_audits
    )

    all_ok = (
        all_libs_present
        and len(lib_audits) == len(required_core_libs)
        and len(missing_transitive) == 0
        and all(len(a.missing_dt_needed) == 0 for a in lib_audits)
        and strict_zero_unres_cnt >= 8
        and lazy_plt_safe
        and all(kv.verified for kv in key_verifications)
        and req_imports_ok
    )

    return ElfSymbolClosureAuditReport(
        all_checks_passed=all_ok,
        core_library_count=len(lib_audits),
        transitive_closure_count=len(visited),
        missing_transitive_needed=tuple(missing_transitive),
        total_core_exports=total_exports,
        total_core_strong_imports=total_strong_imports,
        total_core_resolved_strong_imports=total_resolved_strong,
        strict_zero_unresolved_lib_count=strict_zero_unres_cnt,
        libraries=tuple(lib_audits),
        key_symbols=tuple(key_verifications),
        required_imports_verified=req_imports_ok,
    )


# ---------------------------------------------------------------------------
# Dimension B: 16x User 3D .cube LUT Generator/Validator, FX3 p30 48 MiB Budget
#              & libInfraSetupFile.so RcvThread Mount Chain Audit
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CubeLutValidationResult:
    valid: bool
    title: Optional[str]
    grid_size: Optional[int]
    expected_triple_count: int
    actual_triple_count: int
    domain_min: Tuple[float, float, float]
    domain_max: Tuple[float, float, float]
    byte_length: int
    errors: Tuple[str, ...]


def generate_sony_cube_3d_lut(
    grid_size: int = 33,
    title: str = "SONY_SLog3_SGamut3Cine_To_Rec709",
    domain_min: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    domain_max: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    gamma: float = 1.0,
    line_ending: str = "\n",
) -> str:
    """Deterministically generate a Sony Cinema Line compatible `.cube` 3D LUT (`17^3` or `33^3`)."""
    if grid_size not in SUPPORTED_SONY_CUBE_GRID_SIZES:
        raise ValueError(
            f"Unsupported Sony .cube grid_size={grid_size}; expected one of {SUPPORTED_SONY_CUBE_GRID_SIZES}"
        )
    if not title or '"' in title or "\n" in title or "\r" in title:
        raise ValueError("Invalid TITLE string for .cube header")
    if gamma <= 0.0 or not math.isfinite(gamma):
        raise ValueError("gamma must be a positive finite float")
    for ch in range(3):
        if not (math.isfinite(domain_min[ch]) and math.isfinite(domain_max[ch])):
            raise ValueError("DOMAIN_MIN/DOMAIN_MAX must be finite floats")
        if domain_min[ch] >= domain_max[ch]:
            raise ValueError("DOMAIN_MIN must be strictly less than DOMAIN_MAX on all channels")

    lines: List[str] = [
        "# Sony Cinema Line Compatible 3D LUT (.cube)",
        f'TITLE "{title}"',
        f"LUT_3D_SIZE {grid_size}",
        f"DOMAIN_MIN {domain_min[0]:.6f} {domain_min[1]:.6f} {domain_min[2]:.6f}",
        f"DOMAIN_MAX {domain_max[0]:.6f} {domain_max[1]:.6f} {domain_max[2]:.6f}",
    ]
    denom = float(grid_size - 1)
    # Standard IRIDAS / Adobe / Sony .cube ordering: R changes fastest, G middle, B slowest
    for b_idx in range(grid_size):
        b_norm = b_idx / denom
        b_val = domain_min[2] + (domain_max[2] - domain_min[2]) * (b_norm ** gamma)
        for g_idx in range(grid_size):
            g_norm = g_idx / denom
            g_val = domain_min[1] + (domain_max[1] - domain_min[1]) * (g_norm ** gamma)
            for r_idx in range(grid_size):
                r_norm = r_idx / denom
                r_val = domain_min[0] + (domain_max[0] - domain_min[0]) * (r_norm ** gamma)
                lines.append(f"{r_val:.6f} {g_val:.6f} {b_val:.6f}")

    return line_ending.join(lines) + line_ending


def validate_sony_cube_3d_lut(cube_text: str) -> CubeLutValidationResult:
    """Strictly validate a Sony Cinema Line 3D `.cube` file (`17^3` or `33^3`)."""
    errors: List[str] = []
    title: Optional[str] = None
    grid_size: Optional[int] = None
    domain_min: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    domain_max: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    seen_size = False
    seen_domain_min = False
    seen_domain_max = False
    seen_title = False
    data_started = False
    actual_triples = 0
    eps = 1e-6

    raw_bytes = cube_text.encode("utf-8", errors="strict")
    for line_no, raw_line in enumerate(cube_text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        upper = stripped.upper()
        if upper.startswith("TITLE"):
            if data_started:
                errors.append(f"line {line_no}: TITLE keyword appeared after LUT data started")
                continue
            if seen_title:
                errors.append(f"line {line_no}: duplicate TITLE keyword")
                continue
            seen_title = True
            rest = stripped[5:].strip()
            if len(rest) < 2 or not (rest.startswith('"') and rest.endswith('"')):
                errors.append(f"line {line_no}: TITLE must be enclosed in double quotes")
            else:
                title = rest[1:-1]
                if not title or len(title.encode("utf-8")) > 240:
                    errors.append(f"line {line_no}: TITLE must be 1..240 bytes")
            continue

        if upper.startswith("LUT_1D_SIZE"):
            errors.append(f"line {line_no}: 1D LUTs (LUT_1D_SIZE) are not supported by Sony 3D User LUT slots")
            continue

        if upper.startswith("LUT_3D_INPUT_RANGE"):
            errors.append(f"line {line_no}: non-standard LUT_3D_INPUT_RANGE; use DOMAIN_MIN/DOMAIN_MAX")
            continue

        if upper.startswith("LUT_3D_SIZE"):
            if data_started:
                errors.append(f"line {line_no}: LUT_3D_SIZE appeared after LUT data started")
                continue
            if seen_size:
                errors.append(f"line {line_no}: duplicate LUT_3D_SIZE keyword")
                continue
            seen_size = True
            parts = stripped.split()
            if len(parts) != 2:
                errors.append(f"line {line_no}: malformed LUT_3D_SIZE directive")
                continue
            try:
                parsed_sz = int(parts[1])
            except ValueError:
                errors.append(f"line {line_no}: non-integer LUT_3D_SIZE '{parts[1]}'")
                continue
            grid_size = parsed_sz
            if parsed_sz not in SUPPORTED_SONY_CUBE_GRID_SIZES:
                errors.append(
                    f"line {line_no}: unsupported LUT_3D_SIZE {parsed_sz}; Sony supports {SUPPORTED_SONY_CUBE_GRID_SIZES}"
                )
            continue

        if upper.startswith("DOMAIN_MIN") or upper.startswith("DOMAIN_MAX"):
            is_min = upper.startswith("DOMAIN_MIN")
            if data_started:
                errors.append(f"line {line_no}: {parts[0] if (parts := stripped.split()) else 'DOMAIN'} after data")
                continue
            if (is_min and seen_domain_min) or ((not is_min) and seen_domain_max):
                errors.append(f"line {line_no}: duplicate {'DOMAIN_MIN' if is_min else 'DOMAIN_MAX'}")
                continue
            parts = stripped.split()
            if len(parts) != 4:
                errors.append(f"line {line_no}: expected 3 floats for {parts[0]}")
                continue
            try:
                vals = (float(parts[1]), float(parts[2]), float(parts[3]))
            except ValueError:
                errors.append(f"line {line_no}: non-numeric domain bound")
                continue
            if not all(math.isfinite(v) for v in vals):
                errors.append(f"line {line_no}: non-finite domain bound")
                continue
            if is_min:
                seen_domain_min = True
                domain_min = vals
            else:
                seen_domain_max = True
                domain_max = vals
            continue

        # Must be an RGB floating-point triple line
        if not data_started:
            data_started = True
            for ch in range(3):
                if domain_min[ch] >= domain_max[ch]:
                    errors.append(
                        f"header: DOMAIN_MIN[{ch}]={domain_min[ch]} >= DOMAIN_MAX[{ch}]={domain_max[ch]}"
                    )
        parts = stripped.split()
        if len(parts) != 3:
            if len(errors) < 8:
                errors.append(f"line {line_no}: expected 3 RGB floats, got {len(parts)} tokens")
            continue
        try:
            r_v, g_v, b_v = float(parts[0]), float(parts[1]), float(parts[2])
        except ValueError:
            if len(errors) < 8:
                errors.append(f"line {line_no}: non-float token in RGB triple")
            continue
        if not (math.isfinite(r_v) and math.isfinite(g_v) and math.isfinite(b_v)):
            if len(errors) < 8:
                errors.append(f"line {line_no}: NaN/Inf in RGB triple")
            continue
        for ch_idx, ch_val in enumerate((r_v, g_v, b_v)):
            if ch_val < domain_min[ch_idx] - eps or ch_val > domain_max[ch_idx] + eps:
                if len(errors) < 8:
                    errors.append(
                        f"line {line_no}: channel {ch_idx} value {ch_val} outside domain "
                        f"[{domain_min[ch_idx]}, {domain_max[ch_idx]}]"
                    )
        actual_triples += 1

    if not seen_size or grid_size is None:
        errors.append("missing required LUT_3D_SIZE directive")
        expected_triples = 0
    else:
        expected_triples = grid_size ** 3
        if actual_triples != expected_triples:
            errors.append(
                f"RGB triple count mismatch: expected {expected_triples} ({grid_size}^3), got {actual_triples}"
            )

    return CubeLutValidationResult(
        valid=len(errors) == 0,
        title=title,
        grid_size=grid_size,
        expected_triple_count=expected_triples,
        actual_triple_count=actual_triples,
        domain_min=domain_min,
        domain_max=domain_max,
        byte_length=len(raw_bytes),
        errors=tuple(errors),
    )


@dataclass(frozen=True)
class P30LutCapacityReport:
    fits_in_fx3_p30: bool
    partition_sectors: int
    partition_bytes: int
    cluster_size_bytes: int
    total_clusters: int
    vfat_system_overhead_bytes: int
    usable_data_bytes: int
    max_user_luts: int
    single_17_cube_bytes: int
    single_33_cube_bytes: int
    single_33_worst_case_bytes: int
    sixteen_33_canonical_cluster_bytes: int
    sixteen_33_worst_case_cluster_bytes: int
    canonical_free_bytes: int
    canonical_free_ratio: float
    worst_case_free_bytes: int
    worst_case_free_ratio: float


def verify_p30_lut_capacity_budget(
    max_user_luts: int = 16,
    cluster_size_bytes: int = 8192,
) -> P30LutCapacityReport:
    """Prove 16 full-spec `33^3` `.cube` files + VFAT overhead fit inside FX3 `p30` (`48 MiB`)."""
    if cluster_size_bytes <= 0 or (cluster_size_bytes & (cluster_size_bytes - 1)) != 0:
        raise ValueError("cluster_size_bytes must be a positive power of two")

    cube_17 = generate_sony_cube_3d_lut(grid_size=17, title="SONY_USER_LUT_17", line_ending="\r\n")
    cube_33 = generate_sony_cube_3d_lut(grid_size=33, title="SONY_USER_LUT_33_MAX", line_ending="\r\n")
    val_17 = validate_sony_cube_3d_lut(cube_17)
    val_33 = validate_sony_cube_3d_lut(cube_33)
    if not (val_17.valid and val_33.valid):
        raise RuntimeError("Generated canonical .cube LUT failed self-validation")

    total_clusters = FX3_P30_TOTAL_BYTES // cluster_size_bytes
    # Conservative VFAT (FAT32) system layout overhead:
    # - 32 reserved 512B sectors
    # - 2 copies of FAT (4 bytes per cluster entry, rounded up to 512B sector boundary)
    # - 1 root directory cluster + 2 clusters for `/usr/data/lut/` LFN directory entries
    # - 64 clusters reserved for Sony SetupFile metadata / index files
    reserved_bytes = 32 * FX3_P30_BYTES_PER_SECTOR
    fat_bytes_single = math.ceil((total_clusters + 2) * 4 / FX3_P30_BYTES_PER_SECTOR) * FX3_P30_BYTES_PER_SECTOR
    dir_and_meta_clusters = 1 + 2 + 64
    vfat_overhead_bytes = reserved_bytes + (2 * fat_bytes_single) + (dir_and_meta_clusters * cluster_size_bytes)
    usable_data_bytes = FX3_P30_TOTAL_BYTES - vfat_overhead_bytes

    def _cluster_align(sz: int) -> int:
        return math.ceil(sz / cluster_size_bytes) * cluster_size_bytes

    # Worst-case verbose 33^3 .cube: 4 KiB header comments + 35,937 lines * 40 bytes/line
    single_33_worst = 4096 + (33 ** 3) * 40
    sixteen_canonical = max_user_luts * _cluster_align(val_33.byte_length)
    sixteen_worst = max_user_luts * _cluster_align(single_33_worst)

    canonical_free = usable_data_bytes - sixteen_canonical
    worst_free = usable_data_bytes - sixteen_worst
    fits = (
        canonical_free > 0
        and worst_free > 0
        and (canonical_free / FX3_P30_TOTAL_BYTES) >= 0.50
        and (worst_free / FX3_P30_TOTAL_BYTES) >= 0.40
    )

    return P30LutCapacityReport(
        fits_in_fx3_p30=fits,
        partition_sectors=FX3_P30_SECTOR_COUNT,
        partition_bytes=FX3_P30_TOTAL_BYTES,
        cluster_size_bytes=cluster_size_bytes,
        total_clusters=total_clusters,
        vfat_system_overhead_bytes=vfat_overhead_bytes,
        usable_data_bytes=usable_data_bytes,
        max_user_luts=max_user_luts,
        single_17_cube_bytes=val_17.byte_length,
        single_33_cube_bytes=val_33.byte_length,
        single_33_worst_case_bytes=single_33_worst,
        sixteen_33_canonical_cluster_bytes=sixteen_canonical,
        sixteen_33_worst_case_cluster_bytes=sixteen_worst,
        canonical_free_bytes=canonical_free,
        canonical_free_ratio=round(canonical_free / FX3_P30_TOTAL_BYTES, 6),
        worst_case_free_bytes=worst_free,
        worst_case_free_ratio=round(worst_free / FX3_P30_TOTAL_BYTES, 6),
    )


@dataclass(frozen=True)
class SetupFileMountChainAudit:
    verified: bool
    rcv_thread_vma: int
    mount_plt_vma: int
    mount_flags_hex: str
    fstype_literal: str
    mount_opts_literal: str
    target_dir_literal: str
    donor_device_literal: str
    adapted_device_literal: str
    got_relocations_verified: bool
    instruction_sequence_verified: bool


def verify_setupfile_lut_mount_chain(
    setup_file_donor_bytes: bytes,
) -> SetupFileMountChainAudit:
    """Verify `libInfraSetupFile.so` `SetupFile::RcvThread` (`0x196c8..0x196e0`) VFAT `/usr/data/lut/` mount chain."""
    meta = parse_elf64_dynamic_metadata(setup_file_donor_bytes, file_name="libInfraSetupFile.so")
    try:
        adapted_bytes, _ = apply_patch_spec(setup_file_donor_bytes, P1_LIB_INFRA_SETUP_FILE_SPEC)
    except PatchVerificationError:
        adapted_bytes = b""

    rcv_vma = meta.exports.get(SETUPFILE_RCVTHREAD_SYM, (0, 0))[0]
    insns_ok = rcv_vma == SETUPFILE_RCVTHREAD_VMA
    for insn_vma, expected_word, _desc in SETUPFILE_EXPECTED_MOUNT_INSNS:
        f_off = _vma_to_file_offset(meta.pt_loads, insn_vma)
        if f_off is None:
            insns_ok = False
            break
        actual_word = struct.unpack_from("<I", setup_file_donor_bytes, f_off)[0]
        if actual_word != expected_word:
            insns_ok = False
            break

    def _read_vma_str(buf: bytes, vma: int) -> str:
        off = _vma_to_file_offset(meta.pt_loads, vma)
        return _read_c_string(buf, off) if (off is not None and off < len(buf)) else ""

    fstype = _read_vma_str(setup_file_donor_bytes, SETUPFILE_VFAT_FSTYPE_VMA)
    mount_opts = _read_vma_str(setup_file_donor_bytes, SETUPFILE_POSIX_ATTR_VMA)
    target_dir = _read_vma_str(setup_file_donor_bytes, SETUPFILE_LUT_HOME_VMA)
    donor_dev = _read_vma_str(setup_file_donor_bytes, SETUPFILE_DEV_SOURCE_VMA)
    adapted_dev = _read_vma_str(adapted_bytes, SETUPFILE_DEV_SOURCE_VMA)

    got_target = meta.rela_dyn.get(SETUPFILE_GOT_TARGET_DIR)
    got_source = meta.rela_dyn.get(SETUPFILE_GOT_SOURCE_DEV)
    got_ok = (
        got_target is not None
        and got_target[1] == SETUPFILE_LUT_HOME_SYM
        and got_source is not None
        and got_source[1] == SETUPFILE_DEV_SOURCE_SYM
    )

    verified = (
        insns_ok
        and got_ok
        and fstype == "vfat"
        and mount_opts == "posix_attr"
        and target_dir == "/usr/data/lut/"
        and donor_dev == "/dev/nflasha20"
        and adapted_dev == "/dev/nflasha30"
    )

    return SetupFileMountChainAudit(
        verified=verified,
        rcv_thread_vma=rcv_vma,
        mount_plt_vma=SETUPFILE_MOUNT_PLT_VMA,
        mount_flags_hex="0xc0ed0480",
        fstype_literal=fstype,
        mount_opts_literal=mount_opts,
        target_dir_literal=target_dir,
        donor_device_literal=donor_dev,
        adapted_device_literal=adapted_dev,
        got_relocations_verified=got_ok,
        instruction_sequence_verified=insns_ok,
    )


# ---------------------------------------------------------------------------
# Dimension C: Cine EI / E-Mount AF / CFexpress+SD Dual-Slot Unicorn & Disassembly Contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AppFwContractEntryAudit:
    name: str
    entry_vma: int
    prologue_word_hex: str
    guard_word_hex: str
    signature_vma: int
    signature_text: str
    verified: bool


@dataclass(frozen=True)
class EyeAfUnicornCase:
    mode_input: int
    out_byte_at_offset_8: Optional[int]
    assert_hit: bool
    assert_func: Optional[str]
    sp_preserved: bool


@dataclass(frozen=True)
class DualSlotMediaUnicornCase:
    media_id: int
    media_id_hex: str
    raw_slot_type_enum: Optional[int]
    slot_index: Optional[int]
    assert_hit: bool
    assert_expr: Optional[str]
    assert_file: Optional[str]
    assert_line: Optional[int]
    assert_func: Optional[str]
    sp_preserved: bool


@dataclass(frozen=True)
class CineEiAfDualSlotAuditReport:
    all_checks_passed: bool
    appfw_contracts: Tuple[AppFwContractEntryAudit, ...]
    appfw_imports_mpr_set_lut_data: bool
    lens_communicator_verified: bool
    eye_af_unicorn_cases: Tuple[EyeAfUnicornCase, ...]
    dual_slot_unicorn_cases: Tuple[DualSlotMediaUnicornCase, ...]


def _run_appfw_eye_af_unicorn_cases(
    appfw_bytes: bytes,
    pt_loads: Sequence[Tuple[int, int, int, int]],
) -> Tuple[EyeAfUnicornCase, ...]:
    uc, uc_arm64 = _load_unicorn()
    base = 0x10000000
    code_page = APPFW_SET_EYE_AF_MODE_VMA & ~0xFFF
    sig_page = APPFW_SET_EYE_AF_MODE_SIG_VMA & ~0xFFF
    assert_page = APPFW_ASSERT_HELPER_VMA & ~0xFFF

    results: List[EyeAfUnicornCase] = []
    for mode_in in (0, 1, 2):
        mu = uc.Uc(uc.UC_ARCH_ARM64, uc.UC_MODE_ARM)
        for pg in {code_page, code_page + 0x1000, sig_page - 0x1000, sig_page, sig_page + 0x1000, assert_page}:
            mu.mem_map(base + pg, 0x1000, uc.UC_PROT_ALL)
            f_off = _vma_to_file_offset(pt_loads, pg)
            if f_off is not None:
                mu.mem_write(base + pg, appfw_bytes[f_off : f_off + 0x1000])

        stack_addr = 0x70000000
        out_struct_addr = 0x71000000
        ret_sentinel = 0x7FFF0000
        mu.mem_map(stack_addr, 0x10000, uc.UC_PROT_ALL)
        mu.mem_map(out_struct_addr, 0x1000, uc.UC_PROT_ALL)
        mu.mem_map(ret_sentinel, 0x1000, uc.UC_PROT_ALL)
        mu.mem_write(out_struct_addr, b"\xAA" * 32)

        initial_sp = stack_addr + 0x8000
        assert_state: Dict[str, object] = {"hit": False, "func": None}

        def _hook_code(emu, address, _size, _user_data):
            if address == base + APPFW_ASSERT_HELPER_VMA:
                x2 = emu.reg_read(uc_arm64.UC_ARM64_REG_X2)
                raw = bytes(emu.mem_read(x2, 160))
                assert_state["hit"] = True
                assert_state["func"] = raw.split(b"\x00", 1)[0].decode("ascii", errors="replace")
                emu.emu_stop()

        mu.hook_add(uc.UC_HOOK_CODE, _hook_code)
        mu.reg_write(uc_arm64.UC_ARM64_REG_SP, initial_sp)
        mu.reg_write(uc_arm64.UC_ARM64_REG_LR, ret_sentinel)
        mu.reg_write(uc_arm64.UC_ARM64_REG_X0, mode_in)
        mu.reg_write(uc_arm64.UC_ARM64_REG_X1, out_struct_addr)

        mu.emu_start(base + APPFW_SET_EYE_AF_MODE_VMA, ret_sentinel, count=100)
        final_sp = mu.reg_read(uc_arm64.UC_ARM64_REG_SP)
        hit = bool(assert_state["hit"])
        out_byte = None if hit else int(mu.mem_read(out_struct_addr + 8, 1)[0])
        results.append(
            EyeAfUnicornCase(
                mode_input=mode_in,
                out_byte_at_offset_8=out_byte,
                assert_hit=hit,
                assert_func=str(assert_state["func"]) if assert_state["func"] else None,
                sp_preserved=(final_sp == initial_sp),
            )
        )
    return tuple(results)


def run_libmpr_dual_slot_unicorn_check(
    libmpr_bytes: bytes,
    media_ids: Sequence[int] = (MEDIA_ID_SLOT_A, MEDIA_ID_SLOT_B, MEDIA_ID_UNINITIALIZED, 0x2000),
) -> Tuple[DualSlotMediaUnicornCase, ...]:
    """Execute `libmpr.so` `libXavcMxfGetSlotTypeFromMediaId` (`+0x53c850`) in Unicorn AArch64."""
    uc, uc_arm64 = _load_unicorn()
    meta = parse_elf64_dynamic_metadata(libmpr_bytes, file_name="libmpr.so")

    base = 0x10000000
    code_page = MPR_SLOT_TYPE_FROM_MEDIA_ID_VMA & ~0xFFF
    plt_page = MPR_SLOT_TYPE_ASSERT_PLT_VMA & ~0xFFF
    rodata_pages = (0xD4C000, 0xD4D000)

    cases: List[DualSlotMediaUnicornCase] = []
    for media_id in media_ids:
        mu = uc.Uc(uc.UC_ARCH_ARM64, uc.UC_MODE_ARM)
        for pg in {code_page, plt_page, *rodata_pages}:
            mu.mem_map(base + pg, 0x1000, uc.UC_PROT_ALL)
            f_off = _vma_to_file_offset(meta.pt_loads, pg)
            if f_off is not None:
                mu.mem_write(base + pg, libmpr_bytes[f_off : f_off + 0x1000])

        stack_addr = 0x70000000
        ret_sentinel = 0x7FFF0000
        mu.mem_map(stack_addr, 0x10000, uc.UC_PROT_ALL)
        mu.mem_map(ret_sentinel, 0x1000, uc.UC_PROT_ALL)
        initial_sp = stack_addr + 0x8000

        assert_record: Dict[str, object] = {"hit": False}

        def _read_guest_cstr(emu, addr: int) -> str:
            raw = bytes(emu.mem_read(addr, 160))
            return raw.split(b"\x00", 1)[0].decode("ascii", errors="replace")

        def _hook_code(emu, address, _size, _user_data):
            if address == base + MPR_SLOT_TYPE_ASSERT_PLT_VMA:
                x0 = emu.reg_read(uc_arm64.UC_ARM64_REG_X0)
                x1 = emu.reg_read(uc_arm64.UC_ARM64_REG_X1)
                x2 = emu.reg_read(uc_arm64.UC_ARM64_REG_X2) & 0xFFFFFFFF
                x3 = emu.reg_read(uc_arm64.UC_ARM64_REG_X3)
                assert_record["hit"] = True
                assert_record["expr"] = _read_guest_cstr(emu, x0)
                assert_record["file"] = _read_guest_cstr(emu, x1)
                assert_record["line"] = int(x2)
                assert_record["func"] = _read_guest_cstr(emu, x3)
                emu.emu_stop()

        mu.hook_add(uc.UC_HOOK_CODE, _hook_code)
        mu.reg_write(uc_arm64.UC_ARM64_REG_SP, initial_sp)
        mu.reg_write(uc_arm64.UC_ARM64_REG_LR, ret_sentinel)
        mu.reg_write(uc_arm64.UC_ARM64_REG_X0, media_id & 0xFFFFFFFF)

        mu.emu_start(base + MPR_SLOT_TYPE_FROM_MEDIA_ID_VMA, ret_sentinel, count=200)
        final_sp = mu.reg_read(uc_arm64.UC_ARM64_REG_SP)
        hit = bool(assert_record["hit"])

        if hit:
            cases.append(
                DualSlotMediaUnicornCase(
                    media_id=media_id,
                    media_id_hex=f"0x{media_id:04x}",
                    raw_slot_type_enum=None,
                    slot_index=None,
                    assert_hit=True,
                    assert_expr=str(assert_record.get("expr", "")),
                    assert_file=str(assert_record.get("file", "")),
                    assert_line=int(assert_record.get("line", 0)),
                    assert_func=str(assert_record.get("func", "")),
                    sp_preserved=False,
                )
            )
        else:
            raw_enum = int(mu.reg_read(uc_arm64.UC_ARM64_REG_X0) & 0xFFFFFFFF)
            # MEDIASLOTTYPE in libXavcMxf.cpp is 1-based (1 = Slot A, 2 = Slot B -> 0-based index 0, 1)
            slot_idx = raw_enum - 1 if raw_enum in (1, 2) else None
            cases.append(
                DualSlotMediaUnicornCase(
                    media_id=media_id,
                    media_id_hex=f"0x{media_id:04x}",
                    raw_slot_type_enum=raw_enum,
                    slot_index=slot_idx,
                    assert_hit=False,
                    assert_expr=None,
                    assert_file=None,
                    assert_line=None,
                    assert_func=None,
                    sp_preserved=(final_sp == initial_sp),
                )
            )

    return tuple(cases)


def verify_cine_ei_af_and_dual_slot_contracts(
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
) -> CineEiAfDualSlotAuditReport:
    """Verify Dimension C contracts across `appFw.so`, `libInfraLensCommunicator.so`, and `libmpr.so`."""
    appfw_bytes = (fx6_lib_dir / "appFw.so").read_bytes()
    lens_bytes = (fx6_lib_dir / "libInfraLensCommunicator.so").read_bytes()
    mpr_bytes = (fx6_lib_dir / "libmpr.so").read_bytes()

    appfw_meta = parse_elf64_dynamic_metadata(appfw_bytes, file_name="appFw.so")
    lens_meta = parse_elf64_dynamic_metadata(lens_bytes, file_name="libInfraLensCommunicator.so")

    def _audit_appfw_entry(
        label: str,
        entry_vma: int,
        expected_prologue: int,
        guard_offset: int,
        expected_guard: int,
        sig_vma: int,
        expected_substr: str,
    ) -> AppFwContractEntryAudit:
        e_off = _vma_to_file_offset(appfw_meta.pt_loads, entry_vma)
        s_off = _vma_to_file_offset(appfw_meta.pt_loads, sig_vma)
        if e_off is None or s_off is None:
            return AppFwContractEntryAudit(label, entry_vma, "0x0", "0x0", sig_vma, "", False)
        p_word = struct.unpack_from("<I", appfw_bytes, e_off)[0]
        g_word = struct.unpack_from("<I", appfw_bytes, e_off + guard_offset)[0]
        sig_str = _read_c_string(appfw_bytes, s_off)
        ok = (
            p_word == expected_prologue
            and g_word == expected_guard
            and expected_substr in sig_str
        )
        return AppFwContractEntryAudit(
            name=label,
            entry_vma=entry_vma,
            prologue_word_hex=f"0x{p_word:08x}",
            guard_word_hex=f"0x{g_word:08x}",
            signature_vma=sig_vma,
            signature_text=sig_str,
            verified=ok,
        )

    contracts = (
        _audit_appfw_entry(
            label="set_base_picture_setting_procam_i",
            entry_vma=APPFW_SET_BASE_PICTURE_VMA,
            expected_prologue=0xA9BA7BFD,  # stp x29, x30, [sp, #-0x60]!
            guard_offset=0x04,
            expected_guard=0x71000C1F,  # cmp w0, #3 (Cine EI / Cine EI Quick / Custom)
            sig_vma=APPFW_SET_BASE_PICTURE_SIG_VMA,
            expected_substr="set_base_picture_setting_procam_i",
        ),
        _audit_appfw_entry(
            label="set_user_lut_binary_data_procam_i",
            entry_vma=APPFW_SET_USER_LUT_BIN_VMA,
            expected_prologue=0xA9BE7BFD,  # stp x29, x30, [sp, #-0x20]!
            guard_offset=0x0C,
            expected_guard=0x910003FD,  # mov x29, sp
            sig_vma=APPFW_SET_USER_LUT_BIN_SIG_VMA,
            expected_substr="set_user_lut_binary_data_procam_i",
        ),
        _audit_appfw_entry(
            label="set_af_area_i",
            entry_vma=APPFW_SET_AF_AREA_VMA,
            expected_prologue=0xA9BB7BFD,  # stp x29, x30, [sp, #-0x50]!
            guard_offset=0x04,
            expected_guard=0x7100181F,  # cmp w0, #6 (E-Mount AF area enum 0..6)
            sig_vma=APPFW_SET_AF_AREA_SIG_VMA,
            expected_substr="set_af_area_i",
        ),
        _audit_appfw_entry(
            label="set_eye_af_mode_i",
            entry_vma=APPFW_SET_EYE_AF_MODE_VMA,
            expected_prologue=0x34000120,  # cbz w0, +0x24
            guard_offset=0x04,
            expected_guard=0x7100041F,  # cmp w0, #1
            sig_vma=APPFW_SET_EYE_AF_MODE_SIG_VMA,
            expected_substr="set_eye_af_mode_i",
        ),
    )

    imports_lut = "_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE" in appfw_meta.strong_imports
    lens_ok = (
        lens_meta.exports.get("_ZN16LensCommunicatorC1Ev", (0, 0))[0] == 0x16E0
        and lens_meta.exports.get("_ZN16LensCommunicator11FinalizeCmdEP16__extcmd_svc_msg", (0, 0))[0]
        == 0x18A4
        and lens_meta.exports.get("LensCommunicator_Exit", (0, 0))[0] == 0x229C
    )

    eye_cases = _run_appfw_eye_af_unicorn_cases(appfw_bytes, appfw_meta.pt_loads)
    eye_ok = (
        len(eye_cases) == 3
        and not eye_cases[0].assert_hit
        and eye_cases[0].out_byte_at_offset_8 == 1
        and eye_cases[0].sp_preserved
        and not eye_cases[1].assert_hit
        and eye_cases[1].out_byte_at_offset_8 == 0
        and eye_cases[1].sp_preserved
        and eye_cases[2].assert_hit
        and eye_cases[2].assert_func is not None
        and "set_eye_af_mode_i" in eye_cases[2].assert_func
    )

    slot_cases = run_libmpr_dual_slot_unicorn_check(mpr_bytes)
    slot_by_id = {c.media_id: c for c in slot_cases}
    slot_a = slot_by_id[MEDIA_ID_SLOT_A]
    slot_b = slot_by_id[MEDIA_ID_SLOT_B]
    slot_zero = slot_by_id[MEDIA_ID_UNINITIALIZED]
    slot_bad = slot_by_id[0x2000]

    dual_slot_ok = (
        not slot_a.assert_hit
        and slot_a.raw_slot_type_enum == 1
        and slot_a.slot_index == 0
        and slot_a.sp_preserved
        and not slot_b.assert_hit
        and slot_b.raw_slot_type_enum == 2
        and slot_b.slot_index == 1
        and slot_b.sp_preserved
        and slot_zero.assert_hit
        and slot_zero.assert_file == "libXavcMxf.cpp"
        and slot_zero.assert_line == 274
        and slot_zero.assert_func is not None
        and "libXavcMxfGetSlotTypeFromMediaId" in slot_zero.assert_func
        and slot_bad.assert_hit
    )

    all_ok = (
        all(c.verified for c in contracts)
        and imports_lut
        and lens_ok
        and eye_ok
        and dual_slot_ok
    )

    return CineEiAfDualSlotAuditReport(
        all_checks_passed=all_ok,
        appfw_contracts=contracts,
        appfw_imports_mpr_set_lut_data=imports_lut,
        lens_communicator_verified=lens_ok,
        eye_af_unicorn_cases=eye_cases,
        dual_slot_unicorn_cases=slot_cases,
    )


# ---------------------------------------------------------------------------
# Combined Phase 5 Orchestrator
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeatureRoutingAuditReport:
    all_checks_passed: bool
    dimension_a_symbol_closure: ElfSymbolClosureAuditReport
    dimension_b_lut_capacity: P30LutCapacityReport
    dimension_b_setupfile_mount: SetupFileMountChainAudit
    dimension_c_contracts_unicorn: CineEiAfDualSlotAuditReport


def run_feature_routing_verification(
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx6_initrd_lib_dir: Path = DEFAULT_FX6_INITRD_LIB_DIR,
    fx6_bin_dir: Path = DEFAULT_FX6_DONOR_BIN_DIR,
) -> FeatureRoutingAuditReport:
    """Execute all three Phase 5 verification dimensions (A, B, and C) end-to-end."""
    dim_a = audit_core_elf_symbol_closure(
        fx6_lib_dir=fx6_lib_dir,
        fx6_initrd_lib_dir=fx6_initrd_lib_dir,
        fx6_bin_dir=fx6_bin_dir,
    )
    dim_b_cap = verify_p30_lut_capacity_budget()
    setup_bytes = (fx6_lib_dir / "libInfraSetupFile.so").read_bytes()
    dim_b_mount = verify_setupfile_lut_mount_chain(setup_bytes)
    dim_c = verify_cine_ei_af_and_dual_slot_contracts(fx6_lib_dir=fx6_lib_dir)

    all_ok = (
        dim_a.all_checks_passed
        and dim_b_cap.fits_in_fx3_p30
        and dim_b_mount.verified
        and dim_c.all_checks_passed
    )
    return FeatureRoutingAuditReport(
        all_checks_passed=all_ok,
        dimension_a_symbol_closure=dim_a,
        dimension_b_lut_capacity=dim_b_cap,
        dimension_b_setupfile_mount=dim_b_mount,
        dimension_c_contracts_unicorn=dim_c,
    )
