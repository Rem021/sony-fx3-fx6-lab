"""Unicorn AArch64 Emulated Verifier for the Hardened Read-Only Tier-0 Backup Worker.

Compiles `native/tier0_backup_worker.c` inside `tempfile.TemporaryDirectory()` via Zig's
`aarch64-linux-musl` freestanding shared-object target (leaving zero `.so`/`.bin` files in
the workspace), maps ELF64 `PT_LOAD` segments into Unicorn AArch64 memory with exact segment
permissions, and emulates the Linux AArch64 `svc #0` syscall boundary.

Verifies:
1. Positive two-pass readback across all 11 `TIER0_REQUIRED_BACKUPS` sources (~72.8 MiB per
   pass, ~145.6 MiB total SHA-256 inside Unicorn AArch64), validating both `manifest.json`
   via `fx3_safety.preflight.verify_tier0_backup_manifest` and the kernel syscall trace via
   `fx3_safety.preflight.audit_tier0_worker_syscalls`.
2. Anomaly & fault-injection paths:
   - Single-bit flip during Pass-2 readback -> `ERR_TWOPASS_SHA256_MISMATCH` (25), no manifest.
   - Corrupted `sector0` partition header magic -> `ERR_SECTOR0_MAGIC` (18), zero output files.
   - Corrupted `Backup.bin` `BK4\\0` header magic -> `ERR_BK4_MAGIC` (19), no manifest.
   - Asymmetric `boot0 != boot1` byte size -> `ERR_BOOT_SYMMETRY` (16), no manifest.
   - Reentrant second invocation -> `ERR_REENTRANT_LOCK` (10), zero additional syscalls.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fx3_safety.preflight import (
    TIER0_CANONICAL_SOURCES,
    TIER0_REQUIRED_BACKUPS,
    BackupManifestAudit,
    WorkerSyscallAudit,
    audit_tier0_worker_syscalls,
    verify_tier0_backup_manifest,
)

from .elf_verify import PF_R, PF_W, PF_X, Elf64Info, parse_elf64_aarch64

_LOCAL_UNICORN_SITE = Path(
    "/Volumes/KAFU2T/AI/Orca/Worktrees/Phayen/dugong/work/firmware-reverse-2026-10-22/"
    "tools/venv/lib/python3.14/site-packages"
)
try:
    import unicorn as U
    from unicorn import arm64_const as A
except ImportError:
    if _LOCAL_UNICORN_SITE.is_dir() and str(_LOCAL_UNICORN_SITE) not in sys.path:
        sys.path.append(str(_LOCAL_UNICORN_SITE))
    import unicorn as U
    from unicorn import arm64_const as A


DEFAULT_ZIG_BIN = Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/"
    "runtime/toolchains/zig-aarch64-macos-0.17.0/zig"
)
DEFAULT_WORKER_C_PATH = Path(__file__).resolve().parents[1] / "native" / "tier0_backup_worker.c"

# Return codes mirrored from native/tier0_backup_worker.c
WORKER_OK = 0
ERR_REENTRANT_LOCK = 10
ERR_UNLINK_LIBJIT_FAILED = 11
ERR_MKDIR_BACKUP_FAILED = 12
ERR_SRC_OPEN_FAILED = 13
ERR_SRC_STAT_FAILED = 14
ERR_SRC_SIZE_CONTRACT = 15
ERR_BOOT_SYMMETRY = 16
ERR_PREAD_SHORT_OR_IO = 17
ERR_SECTOR0_MAGIC = 18
ERR_BK4_MAGIC = 19
ERR_DST_OPEN_EXCL_FAILED = 20
ERR_DST_WRITE_FAILED = 21
ERR_DST_FSYNC_CLOSE_FAILED = 22
ERR_PASS2_OPEN_FAILED = 23
ERR_PASS2_PREAD_FAILED = 24
ERR_TWOPASS_SHA256_MISMATCH = 25
ERR_MANIFEST_WRITE_FAILED = 26

# Linux AArch64 syscall numbers
SYS_IOCTL = 29
SYS_MKDIRAT = 34
SYS_UNLINKAT = 35
SYS_OPENAT = 56
SYS_CLOSE = 57
SYS_WRITE = 64
SYS_PREAD64 = 67
SYS_PWRITE64 = 68
SYS_FSTAT = 80
SYS_SYNC = 81
SYS_FSYNC = 82

# Linux openat / errno / ioctl constants
O_ACCMODE = 0x3
O_RDONLY = 0x0
O_WRONLY = 0x1
O_CREAT = 0x40
O_EXCL = 0x80
O_TRUNC = 0x200
BLKGETSIZE64_U32 = 0x80081272

ENOENT_NEG = -2
EBADF_NEG = -9
EACCES_NEG = -13
EEXIST_NEG = -17
EINVAL_NEG = -22
ENOSYS_NEG = -38

PAGE_SIZE = 0x1000
WORKER_LOAD_BASE = 0x00400000
WORKER_STUB_BASE = 0x00500000
WORKER_STACK_BASE = 0x70000000
WORKER_STACK_SIZE = 0x00040000
WORKER_STACK_INIT_SP = WORKER_STACK_BASE + WORKER_STACK_SIZE - 0x2000
WORKER_RETURN_SENTINEL = 0x71000000

ELF64_SHDR_STRUCT = struct.Struct("<IIQQQQIIQQ")
ELF64_SYM_STRUCT = struct.Struct("<IBBHQQ")
ELF64_RELA_STRUCT = struct.Struct("<QQq")
SHT_RELA = 4
SHT_DYNSYM = 11
R_AARCH64_ABS64 = 257
R_AARCH64_GLOB_DAT = 1025
R_AARCH64_JUMP_SLOT = 1026
R_AARCH64_RELATIVE = 1027

CHUNK_BYTES = 65536


@dataclass(frozen=True)
class CompiledWorkerArtifact:
    so_bytes: bytes
    elf_info: Elf64Info
    exported_symbols: Dict[str, int]
    undefined_imports: Tuple[str, ...]
    relocations: Tuple[Tuple[int, int, str, int], ...]


@dataclass(frozen=True)
class VirtualSourceSpec:
    item_key: str
    source_path: str
    total_bytes: int
    is_block_or_mtd_device: bool
    expected_sha256: str
    header_chunk: bytes
    body_chunk_template: bytes

    def read_range(self, offset: int, count: int) -> bytes:
        """Deterministically synthesize `[offset, offset + count)` with offset-bound chunks."""
        if offset < 0 or count < 0 or offset >= self.total_bytes:
            return b""
        end = min(offset + count, self.total_bytes)
        out = bytearray()
        cur = offset
        while cur < end:
            chunk_idx = cur // CHUNK_BYTES
            chunk_off = cur % CHUNK_BYTES
            chunk_end = min((chunk_idx + 1) * CHUNK_BYTES, self.total_bytes)
            chunk_len = chunk_end - chunk_idx * CHUNK_BYTES
            if chunk_idx == 0:
                blk = self.header_chunk[:chunk_len]
            else:
                # Stamp 8-byte byte-offset tag at start of every 64 KiB block so any offset error changes SHA-256
                tag = struct.pack("<Q", chunk_idx * CHUNK_BYTES)
                if chunk_len >= 8:
                    blk = tag + self.body_chunk_template[8:chunk_len]
                else:
                    blk = tag[:chunk_len]
            take = min(end - cur, chunk_len - chunk_off)
            out.extend(blk[chunk_off : chunk_off + take])
            cur += take
        return bytes(out)


@dataclass(frozen=True)
class WrittenOutputSummary:
    path: str
    bytes_written: int
    sha256: str
    fsync_called: bool
    closed: bool


@dataclass(frozen=True)
class Tier0UnicornRunResult:
    return_code: int
    reentrant_second_return_code: Optional[int]
    libjit_unlinked: bool
    backup_dir_created: bool
    sync_called: bool
    manifest_created: bool
    manifest_json: Optional[Dict[str, object]]
    manifest_audit: Optional[BackupManifestAudit]
    syscall_trace: Tuple[Dict[str, object], ...]
    syscall_audit: WorkerSyscallAudit
    written_outputs: Dict[str, WrittenOutputSummary]
    source_expected_sha256: Dict[str, str]


def _page_down(addr: int) -> int:
    return addr & ~(PAGE_SIZE - 1)


def _page_up(addr: int) -> int:
    return (addr + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1)


def _read_c_string(uc: U.Uc, addr: int, max_bytes: int = 256) -> str:
    buf = bytearray()
    for i in range(max_bytes):
        ch = uc.mem_read(addr + i, 1)[0]
        if ch == 0:
            break
        buf.append(ch)
    return buf.decode("utf-8", errors="replace")


def _to_signed64(val: int) -> int:
    val &= 0xFFFFFFFFFFFFFFFF
    return val - (1 << 64) if (val & (1 << 63)) else val


def _resolve_zig_binary(zig_bin: Path = DEFAULT_ZIG_BIN) -> Path:
    if zig_bin != DEFAULT_ZIG_BIN:
        return zig_bin.resolve()
    for env_key in ("ZIG_BIN", "FX6_ZIG"):
        env_val = os.environ.get(env_key, "").strip()
        if env_val:
            cand = Path(env_val).resolve()
            if cand.is_file():
                return cand
    if zig_bin.is_file():
        return zig_bin.resolve()
    which_zig = shutil.which("zig")
    if which_zig:
        return Path(which_zig).resolve()
    return zig_bin.resolve()


def compile_tier0_worker_shared_object(
    worker_c_path: Path = DEFAULT_WORKER_C_PATH,
    zig_bin: Path = DEFAULT_ZIG_BIN,
) -> CompiledWorkerArtifact:
    """Compile `tier0_backup_worker.c` into an ephemeral `.so` inside `TemporaryDirectory` and parse ELF64."""
    worker_c_path = worker_c_path.resolve()
    zig_bin = _resolve_zig_binary(zig_bin)
    if not worker_c_path.is_file():
        raise FileNotFoundError(f"Missing Tier-0 worker C source: {worker_c_path}")
    if not zig_bin.is_file():
        raise FileNotFoundError(f"Missing Zig cross-compiler binary: {zig_bin}")

    with tempfile.TemporaryDirectory(prefix="tier0_worker_build_") as temp_dir:
        out_so = Path(temp_dir) / "tier0_backup_worker.so"
        cmd = [
            str(zig_bin),
            "cc",
            "-target",
            "aarch64-linux-musl",
            "-O2",
            "-fPIC",
            "-shared",
            "-nostdlib",
            str(worker_c_path),
            "-o",
            str(out_so),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(
                f"Zig AArch64 compilation failed (rc={proc.returncode}):\n{proc.stderr}\n{proc.stdout}"
            )
        so_bytes = out_so.read_bytes()

    elf_info = parse_elf64_aarch64(so_bytes)

    # Parse .dynsym / .dynstr and any SHT_RELA tables from section headers
    e_shoff = struct.unpack_from("<Q", so_bytes, 40)[0]
    e_shentsize, e_shnum, _e_shstrndx = struct.unpack_from("<HHH", so_bytes, 58)

    shdrs = [
        ELF64_SHDR_STRUCT.unpack_from(so_bytes, e_shoff + idx * e_shentsize)
        for idx in range(e_shnum)
    ]

    exported: Dict[str, int] = {}
    undef_imports: List[str] = []
    dynsym_names: List[str] = []
    relas: List[Tuple[int, int, str, int]] = []

    for sh_hdr in shdrs:
        _name_off, sh_type, _flags, _addr, sh_off, sh_size, sh_link, _info, _align, sh_entsize = sh_hdr
        if sh_type == SHT_DYNSYM and sh_entsize >= ELF64_SYM_STRUCT.size:
            str_hdr = shdrs[sh_link]
            dynstr = so_bytes[str_hdr[4] : str_hdr[4] + str_hdr[5]]
            for pos in range(sh_off, sh_off + sh_size, sh_entsize):
                st_name, _st_info, _st_other, st_shndx, st_value, _st_size = ELF64_SYM_STRUCT.unpack_from(
                    so_bytes, pos
                )
                nul = dynstr.find(b"\x00", st_name)
                sym_name = dynstr[st_name : (nul if nul >= 0 else len(dynstr))].decode("ascii", errors="replace")
                dynsym_names.append(sym_name)
                if sym_name:
                    if st_shndx == 0:
                        undef_imports.append(sym_name)
                    else:
                        exported[sym_name] = st_value

    for sh_hdr in shdrs:
        _name_off, sh_type, _flags, _addr, sh_off, sh_size, _sh_link, _info, _align, sh_entsize = sh_hdr
        if sh_type == SHT_RELA and sh_entsize >= ELF64_RELA_STRUCT.size:
            for pos in range(sh_off, sh_off + sh_size, sh_entsize):
                r_offset, r_info, r_addend = ELF64_RELA_STRUCT.unpack_from(so_bytes, pos)
                r_type = r_info & 0xFFFFFFFF
                r_sym = r_info >> 32
                sym_name = dynsym_names[r_sym] if r_sym < len(dynsym_names) else ""
                relas.append((r_offset, r_type, sym_name, r_addend))

    if "tier0_backup_worker_run" not in exported or "tier0_backup_worker_init" not in exported:
        raise RuntimeError(f"Missing expected exported worker symbols; found {sorted(exported.keys())}")

    return CompiledWorkerArtifact(
        so_bytes=so_bytes,
        elf_info=elf_info,
        exported_symbols=exported,
        undefined_imports=tuple(undef_imports),
        relocations=tuple(relas),
    )


def build_default_tier0_virtual_sources(
    corrupt_sector0_magic: bool = False,
    corrupt_bk4_magic: bool = False,
    boot1_size_override: Optional[int] = None,
) -> Dict[str, VirtualSourceSpec]:
    """Construct deterministic virtual storage sources for all 11 `TIER0_REQUIRED_BACKUPS` items."""
    default_sizes: Dict[str, int] = {
        "sector0": 512,
        "boot0": 131072,
        "boot1": boot1_size_override if boot1_size_override is not None else 131072,
        "p1_updater": 25100288,
        "p2_backup_bin": 262144,
        "p2_psd_bin": 4096,
        "p2_defdet_bin": 4096,
        "p6_jiritsu": 26214400,
        "p12_cert": 20971520,
        "p18_lensfile": 4096,
        "spi_nor_ddrtraining": 4096,
    }

    sources: Dict[str, VirtualSourceSpec] = {}
    for key, src_meta in TIER0_CANONICAL_SOURCES.items():
        src_path = str(src_meta["source_path"])
        total_bytes = default_sizes[key]
        seed = hashlib.sha256(f"fx3-tier0-sim:{key}:{src_path}".encode("utf-8")).digest()
        body_template = seed * (CHUNK_BYTES // len(seed))

        first_len = min(total_bytes, CHUNK_BYTES)
        hdr = bytearray(body_template[:first_len])

        if key == "sector0":
            hdr[:] = b"\x00" * first_len
            hdr[0:8] = b"BAD!2.00" if corrupt_sector0_magic else b"82462.00"
            struct.pack_into("<I", hdr, 8, 30)
            # Non-overlapping partition descriptors for p1, p2, p6, p12, p18
            part_entries = {
                1: (0x00000080, 0x0000BF80, 4, 1),
                2: (0x0000C000, 0x0000A000, 4, 1),
                6: (0x000D8000, 0x0000C800, 4, 1),
                12: (0x0020C000, 0x00014000, 5, 1),
                18: (0x0031C000, 0x0000A000, 4, 1),
            }
            for pid, (start_s, size_s, ptype, pflag) in part_entries.items():
                struct.pack_into("<IIII", hdr, 32 + (pid - 1) * 16, start_s, size_s, ptype, pflag)
        elif key == "p2_backup_bin":
            struct.pack_into("<I", hdr, 4, 0xAAAAAAAA)
            hdr[12:16] = b"BAD\x00" if corrupt_bk4_magic else b"BK4\x00"

        # Precompute exact SHA-256 across all chunks on host
        spec_tmp = VirtualSourceSpec(
            item_key=key,
            source_path=src_path,
            total_bytes=total_bytes,
            is_block_or_mtd_device=src_path.startswith("/dev/"),
            expected_sha256="",
            header_chunk=bytes(hdr),
            body_chunk_template=body_template,
        )
        hasher = hashlib.sha256()
        off = 0
        while off < total_bytes:
            step = min(CHUNK_BYTES, total_bytes - off)
            hasher.update(spec_tmp.read_range(off, step))
            off += step

        sources[src_path] = VirtualSourceSpec(
            item_key=key,
            source_path=src_path,
            total_bytes=total_bytes,
            is_block_or_mtd_device=src_path.startswith("/dev/"),
            expected_sha256=hasher.hexdigest(),
            header_chunk=bytes(hdr),
            body_chunk_template=body_template,
        )

    return sources


def _map_worker_elf_into_unicorn(mu: U.Uc, artifact: CompiledWorkerArtifact, base_addr: int) -> None:
    """Map ELF64 `PT_LOAD` segments into Unicorn with page-aligned permissions and resolve relocations."""
    page_perms: Dict[int, int] = {}
    for seg in artifact.elf_info.load_segments:
        if seg.p_memsz == 0:
            continue
        start_page = _page_down(base_addr + seg.p_vaddr)
        end_page = _page_up(base_addr + seg.p_vaddr + seg.p_memsz)
        prot = 0
        if seg.p_flags & PF_R:
            prot |= U.UC_PROT_READ
        if seg.p_flags & PF_W:
            prot |= U.UC_PROT_WRITE
        if seg.p_flags & PF_X:
            prot |= U.UC_PROT_EXEC
        for pg in range(start_page, end_page, PAGE_SIZE):
            page_perms[pg] = page_perms.get(pg, 0) | prot

    # Map pages RW initially to populate file-backed contents & apply relocations, then tighten permissions
    for pg in sorted(page_perms.keys()):
        mu.mem_map(pg, PAGE_SIZE, U.UC_PROT_READ | U.UC_PROT_WRITE)

    for seg in artifact.elf_info.load_segments:
        if seg.p_filesz > 0:
            data = artifact.so_bytes[seg.p_offset : seg.p_offset + seg.p_filesz]
            mu.mem_write(base_addr + seg.p_vaddr, data)

    # Map an intrinsic stub page for optional compiler helper calls (e.g. memset) if any relocation needs it
    mu.mem_map(WORKER_STUB_BASE, PAGE_SIZE, U.UC_PROT_READ | U.UC_PROT_EXEC)
    memset_stub = struct.pack(
        "<IIIIII",
        0xAA0003E3,  # mov x3, x0
        0xB4000082,  # cbz x2, +16
        0x38001461,  # strb w1, [x3], #1
        0xF1000442,  # subs x2, x2, #1
        0x54FFFFC1,  # b.ne -8
        0xD65F03C0,  # ret
    )
    mu.mem_write(WORKER_STUB_BASE, memset_stub)

    for r_offset, r_type, sym_name, r_addend in artifact.relocations:
        target_vma = base_addr + r_offset
        if r_type == R_AARCH64_RELATIVE:
            val = base_addr + r_addend
        elif r_type in (R_AARCH64_GLOB_DAT, R_AARCH64_JUMP_SLOT, R_AARCH64_ABS64):
            if sym_name in artifact.exported_symbols:
                val = base_addr + artifact.exported_symbols[sym_name] + r_addend
            elif sym_name == "memset":
                val = WORKER_STUB_BASE
            else:
                raise RuntimeError(f"Unresolved dynamic relocation symbol: {sym_name!r}")
        else:
            raise RuntimeError(f"Unsupported AArch64 relocation type: {r_type}")
        mu.mem_write(target_vma, struct.pack("<Q", val))

    for pg, prot in sorted(page_perms.items()):
        mu.mem_protect(pg, PAGE_SIZE, prot)


def run_tier0_worker_in_unicorn(
    compiled_worker: Optional[CompiledWorkerArtifact] = None,
    entrypoint: str = "tier0_backup_worker_run",
    corrupt_sector0_magic: bool = False,
    corrupt_bk4_magic: bool = False,
    pass2_bitflip_item: Optional[str] = None,
    pass2_bitflip_offset: int = 0,
    pass2_bitflip_mask: int = 0x01,
    boot1_size_override: Optional[int] = None,
    preexisting_output_file: Optional[str] = None,
    invoke_reentrant_second_call: bool = False,
) -> Tier0UnicornRunResult:
    """Execute `tier0_backup_worker.so` in Unicorn AArch64 and audit both manifest and syscall trace."""
    artifact = compiled_worker or compile_tier0_worker_shared_object()
    if entrypoint not in artifact.exported_symbols:
        raise ValueError(f"Unknown worker entrypoint {entrypoint!r}")

    sources = build_default_tier0_virtual_sources(
        corrupt_sector0_magic=corrupt_sector0_magic,
        corrupt_bk4_magic=corrupt_bk4_magic,
        boot1_size_override=boot1_size_override,
    )

    mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
    _map_worker_elf_into_unicorn(mu, artifact, WORKER_LOAD_BASE)
    mu.mem_map(WORKER_STACK_BASE, WORKER_STACK_SIZE, U.UC_PROT_READ | U.UC_PROT_WRITE)
    mu.mem_map(WORKER_RETURN_SENTINEL, PAGE_SIZE, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(WORKER_RETURN_SENTINEL, struct.pack("<I", 0xD503201F))  # nop
    mu.reg_write(A.UC_ARM64_REG_CPACR_EL1, 3 << 20)

    # Simulated kernel VFS state
    vfs_state: Dict[str, object] = {
        "libjit_present": True,
        "backup_dir_exists": False,
        "sync_called": False,
    }
    source_open_counts: Dict[str, int] = {}
    open_fds: Dict[int, Dict[str, object]] = {}
    next_fd = [10]
    output_sinks: Dict[str, Dict[str, object]] = {}
    if preexisting_output_file is not None:
        output_sinks[preexisting_output_file] = {
            "bytes": 0,
            "hasher": hashlib.sha256(),
            "raw": bytearray(),
            "fsync": False,
            "closed": True,
        }

    syscall_trace: List[Dict[str, object]] = []

    def _intr_hook(uc: U.Uc, _intno: int, _user_data: object) -> None:
        nr = uc.reg_read(A.UC_ARM64_REG_X8)
        a0 = uc.reg_read(A.UC_ARM64_REG_X0)
        a1 = uc.reg_read(A.UC_ARM64_REG_X1)
        a2 = uc.reg_read(A.UC_ARM64_REG_X2)
        a3 = uc.reg_read(A.UC_ARM64_REG_X3)

        ret = ENOSYS_NEG
        rec: Dict[str, object] = {"nr": nr}

        if nr == SYS_UNLINKAT:
            dirfd = _to_signed64(a0)
            path = _read_c_string(uc, a1)
            flags = a2 & 0xFFFFFFFF
            if path == "/tmp/jiritsu/libJit.so":
                if vfs_state["libjit_present"]:
                    vfs_state["libjit_present"] = False
                    ret = 0
                else:
                    ret = ENOENT_NEG
            elif path in output_sinks:
                output_sinks.pop(path, None)
                ret = 0
            else:
                ret = ENOENT_NEG
            rec.update({"dirfd": dirfd, "path": path, "flags": flags, "ret": ret})

        elif nr == SYS_MKDIRAT:
            dirfd = _to_signed64(a0)
            path = _read_c_string(uc, a1)
            mode = a2 & 0xFFFFFFFF
            if path.rstrip("/") == "/mnt/fx3_tier0_backup":
                if vfs_state["backup_dir_exists"]:
                    ret = EEXIST_NEG
                else:
                    vfs_state["backup_dir_exists"] = True
                    ret = 0
            else:
                ret = EACCES_NEG
            rec.update({"dirfd": dirfd, "path": path, "flags": mode, "ret": ret})

        elif nr == SYS_OPENAT:
            dirfd = _to_signed64(a0)
            path = _read_c_string(uc, a1)
            flags = a2 & 0xFFFFFFFF
            accmode = flags & O_ACCMODE
            if path in sources:
                if accmode != O_RDONLY or (flags & (O_CREAT | O_TRUNC)) != 0:
                    ret = EACCES_NEG
                else:
                    pass_num = source_open_counts.get(path, 0) + 1
                    source_open_counts[path] = pass_num
                    fd = next_fd[0]
                    next_fd[0] += 1
                    open_fds[fd] = {"kind": "source", "path": path, "pass_num": pass_num}
                    ret = fd
            elif path.startswith("/mnt/fx3_tier0_backup/"):
                if not vfs_state["backup_dir_exists"]:
                    ret = ENOENT_NEG
                elif (flags & O_EXCL) and path in output_sinks:
                    ret = EEXIST_NEG
                elif accmode != O_WRONLY or not (flags & O_CREAT):
                    ret = EINVAL_NEG
                else:
                    fd = next_fd[0]
                    next_fd[0] += 1
                    keep_raw = path.endswith("/manifest.json")
                    output_sinks[path] = {
                        "bytes": 0,
                        "hasher": hashlib.sha256(),
                        "raw": bytearray() if keep_raw else None,
                        "fsync": False,
                        "closed": False,
                    }
                    open_fds[fd] = {"kind": "output", "path": path}
                    ret = fd
            else:
                ret = ENOENT_NEG
            rec.update({"dirfd": dirfd, "path": path, "flags": flags, "ret": ret})

        elif nr == SYS_FSTAT:
            fd = a0 & 0xFFFFFFFF
            stat_ptr = a1
            entry = open_fds.get(fd)
            if entry is None or entry["kind"] != "source":
                ret = EBADF_NEG
            else:
                src = sources[str(entry["path"])]
                kstat = bytearray(128)
                # Block / MTD device nodes report st_size == 0 so worker exercises ioctl(BLKGETSIZE64)
                st_size = 0 if src.is_block_or_mtd_device else src.total_bytes
                struct.pack_into("<q", kstat, 48, st_size)
                uc.mem_write(stat_ptr, bytes(kstat))
                ret = 0
            rec.update({"fd": fd, "ret": ret})

        elif nr == SYS_IOCTL:
            fd = a0 & 0xFFFFFFFF
            cmd_u32 = a1 & 0xFFFFFFFF
            arg_ptr = a2
            entry = open_fds.get(fd)
            if entry is None or entry["kind"] != "source":
                ret = EBADF_NEG
            elif cmd_u32 != BLKGETSIZE64_U32:
                ret = EINVAL_NEG
            else:
                src = sources[str(entry["path"])]
                uc.mem_write(arg_ptr, struct.pack("<Q", src.total_bytes))
                ret = 0
            rec.update({"fd": fd, "flags": cmd_u32, "ret": ret})

        elif nr == SYS_PREAD64:
            fd = a0 & 0xFFFFFFFF
            buf_ptr = a1
            count = a2
            offset = _to_signed64(a3)
            entry = open_fds.get(fd)
            if entry is None or entry["kind"] != "source" or offset < 0:
                ret = EBADF_NEG
            else:
                src = sources[str(entry["path"])]
                chunk = bytearray(src.read_range(offset, count))
                if (
                    pass2_bitflip_item is not None
                    and src.item_key == pass2_bitflip_item
                    and int(entry["pass_num"]) == 2
                    and offset <= pass2_bitflip_offset < offset + len(chunk)
                ):
                    chunk[pass2_bitflip_offset - offset] ^= pass2_bitflip_mask & 0xFF
                if chunk:
                    uc.mem_write(buf_ptr, bytes(chunk))
                ret = len(chunk)
            rec.update({"fd": fd, "offset": offset, "count": count, "ret": ret})

        elif nr in (SYS_WRITE, SYS_PWRITE64):
            fd = a0 & 0xFFFFFFFF
            buf_ptr = a1
            count = a2
            entry = open_fds.get(fd)
            if entry is None or entry["kind"] != "output":
                ret = EBADF_NEG
            else:
                out_path = str(entry["path"])
                sink = output_sinks[out_path]
                payload = bytes(uc.mem_read(buf_ptr, count))
                sink["bytes"] = int(sink["bytes"]) + len(payload)
                sink["hasher"].update(payload)  # type: ignore[union-attr]
                if sink["raw"] is not None:
                    sink["raw"].extend(payload)  # type: ignore[union-attr]
                ret = len(payload)
            rec.update({"fd": fd, "count": count, "ret": ret})

        elif nr == SYS_FSYNC:
            fd = a0 & 0xFFFFFFFF
            entry = open_fds.get(fd)
            if entry is None:
                ret = EBADF_NEG
            else:
                if entry["kind"] == "output":
                    output_sinks[str(entry["path"])]["fsync"] = True
                ret = 0
            rec.update({"fd": fd, "ret": ret})

        elif nr == SYS_CLOSE:
            fd = a0 & 0xFFFFFFFF
            entry = open_fds.pop(fd, None)
            if entry is None:
                ret = EBADF_NEG
            else:
                if entry["kind"] == "output" and str(entry["path"]) in output_sinks:
                    output_sinks[str(entry["path"])]["closed"] = True
                ret = 0
            rec.update({"fd": fd, "ret": ret})

        elif nr == SYS_SYNC:
            vfs_state["sync_called"] = True
            ret = 0
            rec.update({"ret": 0})

        else:
            rec.update({"ret": ret})

        syscall_trace.append(rec)
        uc.reg_write(A.UC_ARM64_REG_X0, ret & 0xFFFFFFFFFFFFFFFF)

    mu.hook_add(U.UC_HOOK_INTR, _intr_hook)

    entry_vma = WORKER_LOAD_BASE + artifact.exported_symbols[entrypoint]
    mu.reg_write(A.UC_ARM64_REG_SP, WORKER_STACK_INIT_SP)
    mu.reg_write(A.UC_ARM64_REG_LR, WORKER_RETURN_SENTINEL)
    mu.emu_start(entry_vma, WORKER_RETURN_SENTINEL)
    rc1 = mu.reg_read(A.UC_ARM64_REG_W0) if entrypoint == "tier0_backup_worker_run" else 0

    rc2: Optional[int] = None
    if invoke_reentrant_second_call:
        run_vma = WORKER_LOAD_BASE + artifact.exported_symbols["tier0_backup_worker_run"]
        mu.reg_write(A.UC_ARM64_REG_SP, WORKER_STACK_INIT_SP)
        mu.reg_write(A.UC_ARM64_REG_LR, WORKER_RETURN_SENTINEL)
        mu.emu_start(run_vma, WORKER_RETURN_SENTINEL)
        rc2 = mu.reg_read(A.UC_ARM64_REG_W0)

    written_summaries: Dict[str, WrittenOutputSummary] = {}
    for out_path, sink in output_sinks.items():
        written_summaries[out_path] = WrittenOutputSummary(
            path=out_path,
            bytes_written=int(sink["bytes"]),
            sha256=sink["hasher"].hexdigest(),  # type: ignore[union-attr]
            fsync_called=bool(sink["fsync"]),
            closed=bool(sink["closed"]),
        )

    manifest_path = "/mnt/fx3_tier0_backup/manifest.json"
    manifest_created = manifest_path in output_sinks and int(output_sinks[manifest_path]["bytes"]) > 0
    manifest_json: Optional[Dict[str, object]] = None
    manifest_audit: Optional[BackupManifestAudit] = None
    if manifest_created:
        raw_manifest = bytes(output_sinks[manifest_path]["raw"]).decode("utf-8")  # type: ignore[arg-type]
        manifest_json = json.loads(raw_manifest)
        manifest_audit = verify_tier0_backup_manifest(manifest_json)

    syscall_audit = audit_tier0_worker_syscalls(syscall_trace)
    expected_by_key = {spec.item_key: spec.expected_sha256 for spec in sources.values()}

    return Tier0UnicornRunResult(
        return_code=rc1,
        reentrant_second_return_code=rc2,
        libjit_unlinked=not bool(vfs_state["libjit_present"]),
        backup_dir_created=bool(vfs_state["backup_dir_exists"]),
        sync_called=bool(vfs_state["sync_called"]),
        manifest_created=manifest_created,
        manifest_json=manifest_json,
        manifest_audit=manifest_audit,
        syscall_trace=tuple(syscall_trace),
        syscall_audit=syscall_audit,
        written_outputs=written_summaries,
        source_expected_sha256=expected_by_key,
    )
