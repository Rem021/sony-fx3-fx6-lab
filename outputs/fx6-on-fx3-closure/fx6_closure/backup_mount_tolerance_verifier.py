"""Phase 6 — Storage Mount-Failure Tolerance Audit (U4 Closure) & RAM-Shadow BK4\\0 Synthesizer.

Covers two independent verification dimensions across read-only FX6 6.01 and FX3 7.02 donors:

- **Dimension A (Storage Mount Return-Code & Degradation Contract Audit — Closing Blueprint `U4`)**:
  Pins exact ELF64 virtual addresses, instruction words, `.rodata` format strings, and PLT targets
  for `libInfraSetupFile.so` (`SetupFile::RcvThread` @ `0x19650..0x197f4` around `bl mount@plt` @
  `0x196e0`) and `libInfraKikiLogGenerator.so` (`KikiLogGenerator_res_ope` @ `0x3cb0..0x3df8` and
  `KikiLogGenerator_init_ope` @ `0x3dfc` around `bl mount@plt` @ `0x3d48`), then micro-executes
  both decision blocks inside **Unicorn AArch64** across `mount_rc = 0` (with P1 `/dev/nflasha30`
  and P2 `opelog.vfat` loopback) vs `mount_rc = -1` (`ENOENT = 2` / `EINVAL = 22` / `EROFS = 30`),
  proving quantitatively that neither library aborts or crashes on mount failure while P1 + P2
  restore 100% persistent user 3D LUT and operation-log directory initialization.

- **Dimension B (Cross-Model `BK4\\0` Backup Key Schema Audit & RAM-Only Shadow Synthesizer)**:
  Audits FX6 6.01 (`libbackup.so`, `libBackupManager.so`, `CX95898_NTSC.bin`) vs FX3 7.02
  (`libbackup.so`, `FX3-CX95900_ALLLANG-Backup.bin`) plus clean-room receipts
  (`backup-section-audit.json` and `backup-key-values.txt`), and provides a deterministic,
  zero-flash-write **RAM-Only Shadow `BK4\\0` Container Synthesizer & Validator**
  (`synthesize_ram_shadow_bk4` / `audit_ram_shadow_bk4`) fully compatible with
  `fx3_safety.boot_contracts.parse_bk4_record`, `parse_fa0080_table`, and
  `verify_boot_screen_enum_contract`.
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from fx3_safety.boot_contracts import (
    BK4_HEADER_SIZE,
    BK4_MAGIC,
    BK4_SYNC_MARKER,
    BK4RecordSummary,
    FA0080_SLOT_STRIDE,
    FA0080_TOTAL_BYTES,
    parse_bk4_record,
    parse_fa0080_table,
    verify_boot_screen_enum_contract,
)

from .patcher import (
    DEFAULT_FX6_DONOR_LIB_DIR,
    P1_LIB_INFRA_SETUP_FILE_SPEC,
    apply_patch_spec,
)


UNICORN_SITE_PACKAGES = Path(
    "/Volumes/KAFU2T/AI/Orca/Worktrees/Phayen/dugong/work/firmware-reverse-2026-10-22"
    "/tools/venv/lib/python3.14/site-packages"
)

DEFAULT_COLOR_PORT_WORK_DIR = Path("/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027")
DEFAULT_FX6_TEAM_DIR = DEFAULT_COLOR_PORT_WORK_DIR / "FX6-donor-assessment-20261103" / "team"
DEFAULT_FX6_BACKUP_MANAGER_PATH = (
    DEFAULT_FX6_TEAM_DIR / "parallel-review-20261105" / "fx6-backup-read-contract" / "work" / "libBackupManager.so"
)
DEFAULT_BACKUP_SECTION_AUDIT_PATH = (
    DEFAULT_FX6_TEAM_DIR / "parallel-review-20261105" / "fx6-66ed0f78-audit" / "receipts" / "backup-section-audit.json"
)
DEFAULT_BACKUP_KEY_VALUES_PATH = (
    DEFAULT_FX6_TEAM_DIR / "parallel-review-20261105" / "fx6-boot-screen-contract" / "receipts" / "backup-key-values.txt"
)
DEFAULT_FX6_TEMPLATE_BK4_PATH = (
    DEFAULT_FX6_TEAM_DIR / "donor" / "tree" / "0110_backup" / "SYSIPSX-DSLR" / "CHAPLIN" / "CX95898_NTSC.bin"
)
DEFAULT_FX3_LIBBACKUP_PATH = (
    DEFAULT_COLOR_PORT_WORK_DIR / "input-20261028" / "engine-rootfs" / "2.05" / "usr" / "lib" / "libbackup.so"
)
DEFAULT_FX3_SEED_BK4_PATH = Path(
    "/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds"
    "/FX3-CX95900_ALLLANG-Backup.bin"
)

# Pinned donor SHA-256 digests
PINNED_LIB_INFRA_SETUP_FILE_SHA256 = "b489c64adef153d42e465f0fb26d2d3a971cde122a6bcf7ec5e056e30400c357"
PINNED_LIB_INFRA_KIKILOG_SHA256 = "be7abc37ceb019b203a3853eba633d5d703d86d9a24ec2a6081b74873dd71917"
PINNED_FX6_LIBBACKUP_SHA256 = "e003e2d8a1f42fdf629dda012a01f225940c016b2ab4dbf482a761378e8d286f"
PINNED_FX6_LIBBACKUP_MANAGER_SHA256 = "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"
PINNED_FX3_LIBBACKUP_SHA256 = "5c1ede86e363bbc718063299833b905985f4a254f5b4d25ad81fce62e253daeb"
PINNED_FX6_TEMPLATE_BK4_SHA256 = "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e"
PINNED_FX3_SEED_BK4_SHA256 = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"

# Dimension A — Pinned VMAs & Instruction Words
SETUPFILE_RCV_THREAD_VMA = 0x19650
SETUPFILE_MOUNT_BLOCK_START_VMA = 0x196B8
SETUPFILE_MOUNT_CALL_VMA = 0x196E0
SETUPFILE_MOUNT_CBZ_VMA = 0x196E4
SETUPFILE_ERR_LOG_CALL_VMA = 0x19710
SETUPFILE_POST_MOUNT_JOIN_VMA = 0x19714
SETUPFILE_OSAL_RCV_CALL_VMA = 0x19744
SETUPFILE_OSAL_RCV_AFTER_VMA = 0x19748

SETUPFILE_PLT_OSAL_RCV_MSG_TMO = 0x14270
SETUPFILE_PLT_STRERROR = 0x14350
SETUPFILE_PLT_MOUNT = 0x144F0
SETUPFILE_PLT_LOG_TEXT_REC = 0x14730
SETUPFILE_PLT_ERRNO_LOCATION = 0x14DF0

SETUPFILE_GOT_MOUNT_PATH = 0x3FD70
SETUPFILE_GOT_DEV_NODE = 0x3FFB8
SETUPFILE_RODATA_DEV_NAME_VMA = 0x25E90
SETUPFILE_RODATA_MOUNT_PATH_VMA = 0x286C8
SETUPFILE_EXPECTED_QUEUE_ID = 0x01DE05A5
SETUPFILE_EXPECTED_MOUNT_FLAGS = 0xC0ED0480

SETUPFILE_PINNED_INSNS: Tuple[Tuple[int, int, str], ...] = (
    (0x196C8, 0xD2809003, "mov x3, #0x480"),
    (0x196DC, 0xF2B81DA3, "movk x3, #0xc0ed, lsl #16"),
    (0x196E0, 0x97FFEB84, "bl 0x144f0 <mount@plt>"),
    (0x196E4, 0x34000180, "cbz w0, 0x19714"),
    (0x196E8, 0x97FFEDC2, "bl 0x14df0 <__errno_location@plt>"),
    (0x196F0, 0x97FFEB18, "bl 0x14350 <strerror@plt>"),
    (0x19710, 0x97FFEC08, "bl 0x14730 <SetupFileLogTextRec@plt>"),
    (0x19744, 0x97FFEACB, "bl 0x14270 <osal_rcv_msg_tmo@plt>"),
)

KIKILOG_RES_OPE_VMA = 0x3CB0
KIKILOG_INIT_OPE_VMA = 0x3DFC
KIKILOG_EPILOGUE_VMA = 0x3DE0
KIKILOG_RET_VMA = 0x3DF0

KIKILOG_PLT_MEMSET = 0x1F10
KIKILOG_PLT_MOUNT = 0x2030
KIKILOG_PLT_SNPRINTF = 0x20D0
KIKILOG_PLT_ERRNO_LOCATION = 0x2100
KIKILOG_PLT_MKDIR = 0x2120
KIKILOG_PLT_BACKUP_NREAD = 0x2180
KIKILOG_EXPECTED_MOUNT_FLAGS = 0xC0ED0490

KIKILOG_PINNED_INSNS: Tuple[Tuple[int, int, str], ...] = (
    (0x3D04, 0x97FFF907, "bl 0x2120 <mkdir@plt> (/etc/opelog/)"),
    (0x3D08, 0x340000A0, "cbz w0, 0x3d1c"),
    (0x3D34, 0xD2809203, "mov x3, #0x490"),
    (0x3D3C, 0xF2B81DA3, "movk x3, #0xc0ed, lsl #16"),
    (0x3D48, 0x97FFF8BA, "bl 0x2030 <mount@plt> (/dev/nflasha21 -> /etc/opelog/)"),
    (0x3D4C, 0x910DA280, "add x0, x20, #0x368 (mount w0 unchecked)"),
    (0x3D6C, 0x97FFF8ED, "bl 0x2120 <mkdir@plt> (/etc/opelog/logs/)"),
    (0x3D70, 0x340000A0, "cbz w0, 0x3d84"),
    (0x3D7C, 0x7100441F, "cmp w0, #0x11 (EEXIST)"),
    (0x3D80, 0x54000301, "b.ne 0x3de0 (clean epilogue)"),
    (0x3DC8, 0x97FFF8D6, "bl 0x2120 <mkdir@plt> (/etc/opelog/logs/%03d/)"),
    (0x3DF0, 0xD65F03C0, "ret"),
    (0x3DFC, 0x17FFFFAD, "b 0x3cb0 <KikiLogGenerator_res_ope>"),
)

# Dimension B — Canonical Backup Key IDs & Constants
KEY_FIXED_AREA_TOP = 0x00FA0028
KEY_FIXED_AREA_SIZE = 0x00FA005D
KEY_FA0080_BOOT_DESC = 0x00FA0080
KEY_FA0084_BOOT_SELECTOR = 0x00FA0084
KEY_DUAL_SLOT_MEDIA_SHADOW = 0x807B002B
KEY_BOOT_SCREEN_MODEL_A = 0x02CF0214
KEY_BOOT_SCREEN_MODEL_B = 0x02CF0218
KEY_MEDIACONFIG_SLOT0_BASE = 0x00CF0000
KEY_MEDIACONFIG_SLOT1_BASE = 0x00CF0040
KEY_MEDIACONFIG_SLOT2_BASE = 0x00CF0080

DEFAULT_SHADOW_FIXED_AREA_TOP = 0x0000000429200000
DEFAULT_SHADOW_FIXED_AREA_SIZE = 0x0000000000100000
MIN_MONDRV_FIXED_AREA_SIZE = 0x0005B400

FX6_DUAL_SLOT_MEDIA_IDS: Tuple[int, int] = (0x1000, 0x1010)
FX6_DUAL_SLOT_DEV_IDS: Tuple[int, int] = (0xDF10, 0xDF20)

BK4_VERSION_WORD0 = 0x04000000  # bytes 00 00 00 04 in CX95898_NTSC.bin & FX3 seed
BK4_SHADOW_SUBSYSTEM_COUNT = 840
BK4_ATTR_SHADOW_CRC16 = 0x00C0
BK4_SHADOW_MODEL_TAG = b"FX6_ON_FX3_RAM\x00"


def _ensure_unicorn_imported():
    try:
        import unicorn  # type: ignore
        import unicorn.arm64_const as arm64_const  # type: ignore
        return unicorn, arm64_const
    except ImportError:
        if UNICORN_SITE_PACKAGES.exists() and str(UNICORN_SITE_PACKAGES) not in sys.path:
            sys.path.insert(0, str(UNICORN_SITE_PACKAGES))
        import unicorn  # type: ignore
        import unicorn.arm64_const as arm64_const  # type: ignore
        return unicorn, arm64_const


def _page_down(addr: int) -> int:
    return addr & ~0xFFF


def _page_up(addr: int) -> int:
    return (addr + 0xFFF) & ~0xFFF


def _read_c_string(blob: bytes, offset: int, max_len: int = 256) -> str:
    end = blob.find(b"\x00", offset, offset + max_len)
    if end < 0:
        end = min(len(blob), offset + max_len)
    return blob[offset:end].decode("ascii", errors="replace")


def _read_guest_c_string(mu, addr: int, max_len: int = 256) -> str:
    if addr == 0:
        return ""
    raw = bytes(mu.mem_read(addr, max_len))
    nul = raw.find(b"\x00")
    if nul >= 0:
        raw = raw[:nul]
    return raw.decode("ascii", errors="replace")


def _parse_elf64_pt_loads(elf_bytes: bytes) -> List[Tuple[int, int, int, int, int]]:
    """Return list of `(p_offset, p_vaddr, p_filesz, p_memsz, p_flags)` for ELF64 `PT_LOAD` segments."""
    if len(elf_bytes) < 64 or elf_bytes[:4] != b"\x7fELF" or elf_bytes[4] != 2:
        raise ValueError("Expected 64-bit ELF binary")
    e_phoff = struct.unpack_from("<Q", elf_bytes, 32)[0]
    e_phentsize, e_phnum = struct.unpack_from("<HH", elf_bytes, 54)
    loads: List[Tuple[int, int, int, int, int]] = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, p_flags, p_off, p_vaddr, _, p_filesz, p_memsz, _ = struct.unpack_from(
            "<IIQQQQQQ", elf_bytes, off
        )
        if p_type == 1:
            loads.append((p_off, p_vaddr, p_filesz, p_memsz, p_flags))
    return loads


def _vma_to_file_offset(elf_bytes: bytes, vma: int) -> int:
    for p_off, p_vaddr, p_filesz, _, _ in _parse_elf64_pt_loads(elf_bytes):
        if p_vaddr <= vma < p_vaddr + p_filesz:
            return p_off + (vma - p_vaddr)
    raise ValueError(f"VMA {hex(vma)} not backed by PT_LOAD file bytes")


def _parse_elf64_defined_dynsyms(elf_bytes: bytes) -> Dict[str, int]:
    """Return `{symbol_name: st_value}` for defined dynamic symbols (`SHN_UNDEF` excluded)."""
    e_shoff = struct.unpack_from("<Q", elf_bytes, 40)[0]
    e_shentsize, e_shnum, _ = struct.unpack_from("<HHH", elf_bytes, 58)
    dynsym_hdr = None
    shdrs = []
    for i in range(e_shnum):
        sh = struct.unpack_from("<IIQQQQIIQQ", elf_bytes, e_shoff + i * e_shentsize)
        shdrs.append(sh)
        if sh[1] == 11:  # SHT_DYNSYM
            dynsym_hdr = sh
    if dynsym_hdr is None:
        return {}
    _, _, _, _, sh_offset, sh_size, sh_link, _, _, sh_entsize = dynsym_hdr
    str_sh = shdrs[sh_link]
    strtab = elf_bytes[str_sh[4] : str_sh[4] + str_sh[5]]
    entsize = sh_entsize or 24
    out: Dict[str, int] = {}
    for pos in range(sh_offset, sh_offset + sh_size, entsize):
        st_name, st_info, _, st_shndx, st_value, _ = struct.unpack_from("<IBBHQQ", elf_bytes, pos)
        if st_shndx == 0 or st_name >= len(strtab):
            continue
        nul = strtab.find(b"\x00", st_name)
        name = strtab[st_name : (nul if nul >= 0 else len(strtab))].decode("ascii", errors="replace")
        if name and (st_info >> 4) in (1, 2):  # STB_GLOBAL / STB_WEAK
            out[name] = st_value
    return out


def compute_crc16_ccitt(data: bytes, init: int = 0xFFFF) -> int:
    """Deterministic 16-bit CRC-16/CCITT-FALSE (`poly=0x1021`, `init=0xFFFF`) for shadow properties."""
    crc = init & 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


# ---------------------------------------------------------------------------
# Dimension A: Storage Mount Return-Code & Degradation Contract Audit (U4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PinnedInstructionCheck:
    vma: int
    file_offset: int
    expected_word: int
    actual_word: int
    mnemonic: str
    matched: bool


@dataclass(frozen=True)
class SetupFileMountUnicornCase:
    case_id: str
    adapted_p1: bool
    injected_mount_rc: int
    injected_errno: int
    observed_mount_source: str
    observed_mount_target: str
    observed_fstype: str
    observed_mount_flags: int
    observed_mount_data: str
    error_branch_entered: bool
    error_log_calls: int
    logged_func_name: str
    logged_line: int
    reached_msg_loop: bool
    observed_queue_id: int
    abort_or_fault: bool


@dataclass(frozen=True)
class KikiLogMountUnicornCase:
    case_id: str
    injected_mount_rc: int
    injected_mount_errno: int
    injected_logs_mkdir_rc: int
    injected_logs_mkdir_errno: int
    observed_mount_source: str
    observed_mount_target: str
    observed_fstype: str
    observed_mount_flags: int
    observed_mount_data: str
    mount_rc_checked_by_caller: bool
    early_exit_on_logs_mkdir: bool
    mkdir_paths: Tuple[str, ...]
    subdirs_created: Tuple[str, ...]
    sp_preserved: bool
    abort_or_fault: bool


@dataclass(frozen=True)
class StorageMountToleranceAuditReport:
    all_checks_passed: bool
    u4_closed: bool
    setupfile_sha256: str
    setupfile_sha256_verified: bool
    kikilog_sha256: str
    kikilog_sha256_verified: bool
    setupfile_pinned_insns: Tuple[PinnedInstructionCheck, ...]
    kikilog_pinned_insns: Tuple[PinnedInstructionCheck, ...]
    setupfile_rodata_strings: Dict[str, str]
    kikilog_rodata_strings: Dict[str, str]
    setupfile_unicorn_cases: Tuple[SetupFileMountUnicornCase, ...]
    kikilog_unicorn_cases: Tuple[KikiLogMountUnicornCase, ...]


def _map_elf_into_unicorn(mu, elf_bytes: bytes, extra_high_addr: int = 0x90010000) -> None:
    loads = _parse_elf64_pt_loads(elf_bytes)
    mapped_pages = set()
    for p_off, p_vaddr, p_filesz, p_memsz, _ in loads:
        start_pg = _page_down(p_vaddr)
        end_pg = _page_up(p_vaddr + p_memsz)
        for pg in range(start_pg, end_pg, 0x1000):
            if pg not in mapped_pages:
                mu.mem_map(pg, 0x1000)
                mapped_pages.add(pg)
        if p_filesz > 0:
            mu.mem_write(p_vaddr, elf_bytes[p_off : p_off + p_filesz])
    # Map scratch + stack region
    mu.mem_map(0x70000000, 0x20000)  # stack + TLS/errno + guest scratch strings
    mu.mem_map(_page_down(extra_high_addr - 0x1000), 0x4000)


def run_setupfile_mount_unicorn_case(
    elf_bytes: bytes,
    *,
    case_id: str,
    adapted_p1: bool,
    mount_rc: int,
    mount_errno: int,
) -> SetupFileMountUnicornCase:
    """Micro-execute `SetupFile::RcvThread` (`0x196b8..0x19748`) in Unicorn AArch64."""
    unicorn, arm64_const = _ensure_unicorn_imported()
    mu = unicorn.Uc(unicorn.UC_ARCH_ARM64, unicorn.UC_MODE_ARM)
    _map_elf_into_unicorn(mu, elf_bytes)

    # Guest scratch layout in 0x70000000..0x70020000
    errno_addr = 0x70001100
    strerror_str_addr = 0x70001180
    stack_top = 0x7001E000
    frame_fp = 0x7001DF00

    mu.mem_write(errno_addr, struct.pack("<i", mount_errno))
    mu.mem_write(strerror_str_addr, f"errno={mount_errno}\x00".encode("ascii"))

    # Point GOT slots read by 0x196d0 (`0x3fd70`) and 0x196d8 (`0x3ffb8`) directly into mapped .rodata
    mu.mem_write(SETUPFILE_GOT_MOUNT_PATH, struct.pack("<Q", SETUPFILE_RODATA_MOUNT_PATH_VMA))
    mu.mem_write(SETUPFILE_GOT_DEV_NODE, struct.pack("<Q", SETUPFILE_RODATA_DEV_NAME_VMA))

    mu.reg_write(arm64_const.UC_ARM64_REG_SP, frame_fp)
    mu.reg_write(arm64_const.UC_ARM64_REG_X29, frame_fp)

    state: Dict[str, object] = {
        "mount_source": "",
        "mount_target": "",
        "fstype": "",
        "flags": 0,
        "data": "",
        "err_entered": False,
        "log_calls": 0,
        "func_name": "",
        "line": 0,
        "reached_loop": False,
        "queue_id": 0,
    }

    plt_addrs = {
        SETUPFILE_PLT_MOUNT,
        SETUPFILE_PLT_ERRNO_LOCATION,
        SETUPFILE_PLT_STRERROR,
        SETUPFILE_PLT_LOG_TEXT_REC,
        SETUPFILE_PLT_OSAL_RCV_MSG_TMO,
    }

    def _hook_code(uc, address: int, size: int, user_data) -> None:
        if address == 0x196E8:
            state["err_entered"] = True
        if address not in plt_addrs:
            return
        lr = uc.reg_read(arm64_const.UC_ARM64_REG_LR)
        if address == SETUPFILE_PLT_MOUNT:
            state["mount_source"] = _read_guest_c_string(uc, uc.reg_read(arm64_const.UC_ARM64_REG_X0))
            state["mount_target"] = _read_guest_c_string(uc, uc.reg_read(arm64_const.UC_ARM64_REG_X1))
            state["fstype"] = _read_guest_c_string(uc, uc.reg_read(arm64_const.UC_ARM64_REG_X2))
            state["flags"] = uc.reg_read(arm64_const.UC_ARM64_REG_X3) & 0xFFFFFFFFFFFFFFFF
            state["data"] = _read_guest_c_string(uc, uc.reg_read(arm64_const.UC_ARM64_REG_X4))
            uc.reg_write(arm64_const.UC_ARM64_REG_X0, mount_rc & 0xFFFFFFFFFFFFFFFF)
            uc.reg_write(arm64_const.UC_ARM64_REG_PC, lr)
        elif address == SETUPFILE_PLT_ERRNO_LOCATION:
            uc.reg_write(arm64_const.UC_ARM64_REG_X0, errno_addr)
            uc.reg_write(arm64_const.UC_ARM64_REG_PC, lr)
        elif address == SETUPFILE_PLT_STRERROR:
            uc.reg_write(arm64_const.UC_ARM64_REG_X0, strerror_str_addr)
            uc.reg_write(arm64_const.UC_ARM64_REG_PC, lr)
        elif address == SETUPFILE_PLT_LOG_TEXT_REC:
            state["log_calls"] = int(state["log_calls"]) + 1
            state["func_name"] = _read_guest_c_string(uc, uc.reg_read(arm64_const.UC_ARM64_REG_X2))
            state["line"] = uc.reg_read(arm64_const.UC_ARM64_REG_X3) & 0xFFFFFFFF
            uc.reg_write(arm64_const.UC_ARM64_REG_X0, 0)
            uc.reg_write(arm64_const.UC_ARM64_REG_PC, lr)
        elif address == SETUPFILE_PLT_OSAL_RCV_MSG_TMO:
            state["reached_loop"] = True
            state["queue_id"] = uc.reg_read(arm64_const.UC_ARM64_REG_X0) & 0xFFFFFFFF
            uc.reg_write(arm64_const.UC_ARM64_REG_X0, 0)
            uc.emu_stop()

    mu.hook_add(unicorn.UC_HOOK_CODE, _hook_code)
    fault = False
    try:
        mu.emu_start(SETUPFILE_MOUNT_BLOCK_START_VMA, SETUPFILE_OSAL_RCV_AFTER_VMA, count=512)
    except Exception:
        fault = True

    _ = stack_top
    return SetupFileMountUnicornCase(
        case_id=case_id,
        adapted_p1=adapted_p1,
        injected_mount_rc=mount_rc,
        injected_errno=mount_errno,
        observed_mount_source=str(state["mount_source"]),
        observed_mount_target=str(state["mount_target"]),
        observed_fstype=str(state["fstype"]),
        observed_mount_flags=int(state["flags"]),
        observed_mount_data=str(state["data"]),
        error_branch_entered=bool(state["err_entered"]),
        error_log_calls=int(state["log_calls"]),
        logged_func_name=str(state["func_name"]),
        logged_line=int(state["line"]),
        reached_msg_loop=bool(state["reached_loop"]),
        observed_queue_id=int(state["queue_id"]),
        abort_or_fault=fault,
    )


def run_kikilog_mount_unicorn_case(
    elf_bytes: bytes,
    *,
    case_id: str,
    mount_rc: int,
    mount_errno: int,
    logs_mkdir_rc: int,
    logs_mkdir_errno: int,
    subdir_count: int = 3,
) -> KikiLogMountUnicornCase:
    """Micro-execute `KikiLogGenerator_init_ope` (`0x3dfc -> 0x3cb0 -> 0x3df0`) in Unicorn AArch64."""
    unicorn, arm64_const = _ensure_unicorn_imported()
    mu = unicorn.Uc(unicorn.UC_ARCH_ARM64, unicorn.UC_MODE_ARM)
    sentinel_lr = 0x90000000
    _map_elf_into_unicorn(mu, elf_bytes, extra_high_addr=sentinel_lr)
    mu.mem_write(sentinel_lr, struct.pack("<I", 0xD503201F))  # nop

    errno_addr = 0x70001100
    initial_sp = 0x7001E000
    mu.mem_write(errno_addr, struct.pack("<i", 0))
    mu.reg_write(arm64_const.UC_ARM64_REG_SP, initial_sp)
    mu.reg_write(arm64_const.UC_ARM64_REG_LR, sentinel_lr)

    mkdir_paths: List[str] = []
    subdirs_created: List[str] = []
    state: Dict[str, object] = {
        "mount_source": "",
        "mount_target": "",
        "fstype": "",
        "flags": 0,
        "data": "",
        "early_exit": False,
    }

    plt_addrs = {
        KIKILOG_PLT_BACKUP_NREAD,
        KIKILOG_PLT_MKDIR,
        KIKILOG_PLT_ERRNO_LOCATION,
        KIKILOG_PLT_MOUNT,
        KIKILOG_PLT_MEMSET,
        KIKILOG_PLT_SNPRINTF,
    }

    def _hook_code(uc, address: int, size: int, user_data) -> None:
        if address not in plt_addrs:
            return
        lr = uc.reg_read(arm64_const.UC_ARM64_REG_LR)
        if address == KIKILOG_PLT_BACKUP_NREAD:
            key_id = uc.reg_read(arm64_const.UC_ARM64_REG_X0) & 0xFFFFFFFF
            dst = uc.reg_read(arm64_const.UC_ARM64_REG_X1)
            req_len = uc.reg_read(arm64_const.UC_ARM64_REG_X2) & 0xFFFFFFFF
            if key_id == 0x0110000A and req_len == 1:
                uc.mem_write(dst, b"\x01")
                uc.reg_write(arm64_const.UC_ARM64_REG_X0, 1)
            elif key_id == 0x0051000F and req_len == 1:
                uc.mem_write(dst, b"\x00")  # Normal Boot mode
                uc.reg_write(arm64_const.UC_ARM64_REG_X0, 1)
            elif key_id == 0x0110000C and req_len == 4:
                uc.mem_write(dst, struct.pack("<I", subdir_count))
                uc.reg_write(arm64_const.UC_ARM64_REG_X0, 4)
            elif key_id == 0x0110000B and req_len == 4:
                uc.mem_write(dst, struct.pack("<I", 1))
                uc.reg_write(arm64_const.UC_ARM64_REG_X0, 4)
            else:
                uc.reg_write(arm64_const.UC_ARM64_REG_X0, (-1) & 0xFFFFFFFFFFFFFFFF)
            uc.reg_write(arm64_const.UC_ARM64_REG_PC, lr)
        elif address == KIKILOG_PLT_MOUNT:
            state["mount_source"] = _read_guest_c_string(uc, uc.reg_read(arm64_const.UC_ARM64_REG_X0))
            state["mount_target"] = _read_guest_c_string(uc, uc.reg_read(arm64_const.UC_ARM64_REG_X1))
            state["fstype"] = _read_guest_c_string(uc, uc.reg_read(arm64_const.UC_ARM64_REG_X2))
            state["flags"] = uc.reg_read(arm64_const.UC_ARM64_REG_X3) & 0xFFFFFFFFFFFFFFFF
            state["data"] = _read_guest_c_string(uc, uc.reg_read(arm64_const.UC_ARM64_REG_X4))
            if mount_rc < 0:
                uc.mem_write(errno_addr, struct.pack("<i", mount_errno))
            uc.reg_write(arm64_const.UC_ARM64_REG_X0, mount_rc & 0xFFFFFFFFFFFFFFFF)
            uc.reg_write(arm64_const.UC_ARM64_REG_PC, lr)
        elif address == KIKILOG_PLT_MEMSET:
            dst = uc.reg_read(arm64_const.UC_ARM64_REG_X0)
            val = uc.reg_read(arm64_const.UC_ARM64_REG_X1) & 0xFF
            ln = uc.reg_read(arm64_const.UC_ARM64_REG_X2)
            uc.mem_write(dst, bytes([val]) * ln)
            uc.reg_write(arm64_const.UC_ARM64_REG_PC, lr)
        elif address == KIKILOG_PLT_SNPRINTF:
            dst = uc.reg_read(arm64_const.UC_ARM64_REG_X0)
            cap = uc.reg_read(arm64_const.UC_ARM64_REG_X1)
            fmt = _read_guest_c_string(uc, uc.reg_read(arm64_const.UC_ARM64_REG_X2))
            if fmt == "%s%03d%s":
                s_prefix = _read_guest_c_string(uc, uc.reg_read(arm64_const.UC_ARM64_REG_X3))
                idx = uc.reg_read(arm64_const.UC_ARM64_REG_X4) & 0xFFFFFFFF
                s_suffix = _read_guest_c_string(uc, uc.reg_read(arm64_const.UC_ARM64_REG_X5))
                rendered = f"{s_prefix}{idx:03d}{s_suffix}".encode("ascii")[: max(0, cap - 1)] + b"\x00"
            else:
                rendered = b"err\x00"
            uc.mem_write(dst, rendered)
            uc.reg_write(arm64_const.UC_ARM64_REG_X0, len(rendered) - 1)
            uc.reg_write(arm64_const.UC_ARM64_REG_PC, lr)
        elif address == KIKILOG_PLT_MKDIR:
            p_str = _read_guest_c_string(uc, uc.reg_read(arm64_const.UC_ARM64_REG_X0))
            mkdir_paths.append(p_str)
            if p_str == "/etc/opelog/":
                # Mountpoint directory already exists on rootfs (`EEXIST == 0x11`)
                uc.mem_write(errno_addr, struct.pack("<i", 0x11))
                uc.reg_write(arm64_const.UC_ARM64_REG_X0, (-1) & 0xFFFFFFFFFFFFFFFF)
            elif p_str == "/etc/opelog/logs/":
                if logs_mkdir_rc < 0:
                    uc.mem_write(errno_addr, struct.pack("<i", logs_mkdir_errno))
                    if logs_mkdir_errno != 0x11:
                        state["early_exit"] = True
                uc.reg_write(arm64_const.UC_ARM64_REG_X0, logs_mkdir_rc & 0xFFFFFFFFFFFFFFFF)
            else:
                subdirs_created.append(p_str)
                uc.reg_write(arm64_const.UC_ARM64_REG_X0, 0)
            uc.reg_write(arm64_const.UC_ARM64_REG_PC, lr)
        elif address == KIKILOG_PLT_ERRNO_LOCATION:
            uc.reg_write(arm64_const.UC_ARM64_REG_X0, errno_addr)
            uc.reg_write(arm64_const.UC_ARM64_REG_PC, lr)

    mu.hook_add(unicorn.UC_HOOK_CODE, _hook_code)
    fault = False
    try:
        mu.emu_start(KIKILOG_INIT_OPE_VMA, sentinel_lr, count=2048)
    except Exception:
        fault = True

    final_sp = mu.reg_read(arm64_const.UC_ARM64_REG_SP)
    final_pc = mu.reg_read(arm64_const.UC_ARM64_REG_PC)
    # Static + dynamic check: instruction right after `bl mount@plt` (`0x3d48`) is `add x0, x20, #0x368` (`0x3d4c`),
    # overwriting `x0` without reading `w0`!
    after_mount_word = struct.unpack_from("<I", elf_bytes, _vma_to_file_offset(elf_bytes, 0x3D4C))[0]
    mount_rc_checked = after_mount_word != 0x910DA280

    return KikiLogMountUnicornCase(
        case_id=case_id,
        injected_mount_rc=mount_rc,
        injected_mount_errno=mount_errno,
        injected_logs_mkdir_rc=logs_mkdir_rc,
        injected_logs_mkdir_errno=logs_mkdir_errno,
        observed_mount_source=str(state["mount_source"]),
        observed_mount_target=str(state["mount_target"]),
        observed_fstype=str(state["fstype"]),
        observed_mount_flags=int(state["flags"]),
        observed_mount_data=str(state["data"]),
        mount_rc_checked_by_caller=mount_rc_checked,
        early_exit_on_logs_mkdir=bool(state["early_exit"]),
        mkdir_paths=tuple(mkdir_paths),
        subdirs_created=tuple(subdirs_created),
        sp_preserved=(final_sp == initial_sp and final_pc == sentinel_lr),
        abort_or_fault=fault or (final_pc != sentinel_lr),
    )


def audit_storage_mount_tolerance(
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
) -> StorageMountToleranceAuditReport:
    """Execute Dimension A static instruction pinning + Unicorn micro-execution closing Blueprint `U4`."""
    sf_raw = (fx6_lib_dir / "libInfraSetupFile.so").read_bytes()
    kl_raw = (fx6_lib_dir / "libInfraKikiLogGenerator.so").read_bytes()
    sf_adapted, _ = apply_patch_spec(sf_raw, P1_LIB_INFRA_SETUP_FILE_SPEC)

    sf_sha = hashlib.sha256(sf_raw).hexdigest()
    kl_sha = hashlib.sha256(kl_raw).hexdigest()
    sf_sha_ok = sf_sha == PINNED_LIB_INFRA_SETUP_FILE_SHA256
    kl_sha_ok = kl_sha == PINNED_LIB_INFRA_KIKILOG_SHA256

    sf_checks: List[PinnedInstructionCheck] = []
    for vma, exp_word, mnem in SETUPFILE_PINNED_INSNS:
        foff = _vma_to_file_offset(sf_raw, vma)
        act_word = struct.unpack_from("<I", sf_raw, foff)[0]
        sf_checks.append(
            PinnedInstructionCheck(
                vma=vma,
                file_offset=foff,
                expected_word=exp_word,
                actual_word=act_word,
                mnemonic=mnem,
                matched=(act_word == exp_word),
            )
        )

    kl_checks: List[PinnedInstructionCheck] = []
    for vma, exp_word, mnem in KIKILOG_PINNED_INSNS:
        foff = _vma_to_file_offset(kl_raw, vma)
        act_word = struct.unpack_from("<I", kl_raw, foff)[0]
        kl_checks.append(
            PinnedInstructionCheck(
                vma=vma,
                file_offset=foff,
                expected_word=exp_word,
                actual_word=act_word,
                mnemonic=mnem,
                matched=(act_word == exp_word),
            )
        )

    sf_rodata = {
        "mount_opts_0x26652": _read_c_string(sf_raw, _vma_to_file_offset(sf_raw, 0x26652)),
        "fstype_0x2665d": _read_c_string(sf_raw, _vma_to_file_offset(sf_raw, 0x2665D)),
        "mount_err_fmt_0x26662": _read_c_string(sf_raw, _vma_to_file_offset(sf_raw, 0x26662)),
        "func_name_0x26a70": _read_c_string(sf_raw, _vma_to_file_offset(sf_raw, 0x26A70)),
        "mount_path_0x286c8": _read_c_string(sf_raw, _vma_to_file_offset(sf_raw, SETUPFILE_RODATA_MOUNT_PATH_VMA)),
        "unadapted_dev_0x25e90": _read_c_string(sf_raw, _vma_to_file_offset(sf_raw, SETUPFILE_RODATA_DEV_NAME_VMA)),
        "adapted_p1_dev_0x25e90": _read_c_string(
            sf_adapted, _vma_to_file_offset(sf_adapted, SETUPFILE_RODATA_DEV_NAME_VMA)
        ),
    }
    kl_rodata = {
        "slash_0x484a": _read_c_string(kl_raw, _vma_to_file_offset(kl_raw, 0x484A)),
        "mount_target_0x4866": _read_c_string(kl_raw, _vma_to_file_offset(kl_raw, 0x4866)),
        "logs_dir_0x4873": _read_c_string(kl_raw, _vma_to_file_offset(kl_raw, 0x4873)),
        "subdir_fmt_0x4885": _read_c_string(kl_raw, _vma_to_file_offset(kl_raw, 0x4885)),
        "mount_opts_0x488e": _read_c_string(kl_raw, _vma_to_file_offset(kl_raw, 0x488E)),
        "fstype_0x4899": _read_c_string(kl_raw, _vma_to_file_offset(kl_raw, 0x4899)),
        "dev_node_0x489e": _read_c_string(kl_raw, _vma_to_file_offset(kl_raw, 0x489E)),
    }

    # Unicorn micro-execution cases for SetupFile::RcvThread
    sf_ok = run_setupfile_mount_unicorn_case(
        sf_adapted,
        case_id="P1_ADAPTED_MOUNT_OK",
        adapted_p1=True,
        mount_rc=0,
        mount_errno=0,
    )
    sf_enoent = run_setupfile_mount_unicorn_case(
        sf_raw,
        case_id="UNADAPTED_P20_MOUNT_ENOENT",
        adapted_p1=False,
        mount_rc=-1,
        mount_errno=2,  # ENOENT
    )
    sf_einval = run_setupfile_mount_unicorn_case(
        sf_raw,
        case_id="UNADAPTED_P20_MOUNT_EINVAL",
        adapted_p1=False,
        mount_rc=-1,
        mount_errno=22,  # EINVAL
    )

    # Unicorn micro-execution cases for KikiLogGenerator_init_ope -> KikiLogGenerator_res_ope
    kl_ok = run_kikilog_mount_unicorn_case(
        kl_raw,
        case_id="P2_LOOPBACK_MOUNT_OK",
        mount_rc=0,
        mount_errno=0,
        logs_mkdir_rc=0,
        logs_mkdir_errno=0,
        subdir_count=3,
    )
    kl_enoent = run_kikilog_mount_unicorn_case(
        kl_raw,
        case_id="UNADAPTED_P21_MOUNT_ENOENT_EROFS",
        mount_rc=-1,
        mount_errno=2,   # ENOENT on missing /dev/nflasha21
        logs_mkdir_rc=-1,
        logs_mkdir_errno=30,  # EROFS on unmounted /etc/opelog/logs/
        subdir_count=3,
    )
    kl_einval = run_kikilog_mount_unicorn_case(
        kl_raw,
        case_id="UNADAPTED_P21_MOUNT_EINVAL_EROFS",
        mount_rc=-1,
        mount_errno=22,  # EINVAL
        logs_mkdir_rc=-1,
        logs_mkdir_errno=30,  # EROFS
        subdir_count=3,
    )

    rodata_ok = (
        sf_rodata["mount_opts_0x26652"] == "posix_attr"
        and sf_rodata["fstype_0x2665d"] == "vfat"
        and sf_rodata["mount_path_0x286c8"] == "/usr/data/lut/"
        and sf_rodata["unadapted_dev_0x25e90"] == "/dev/nflasha20"
        and sf_rodata["adapted_p1_dev_0x25e90"] == "/dev/nflasha30"
        and kl_rodata["mount_target_0x4866"] == "/etc/opelog/"
        and kl_rodata["logs_dir_0x4873"] == "/etc/opelog/logs/"
        and kl_rodata["dev_node_0x489e"] == "/dev/nflasha21"
        and kl_rodata["fstype_0x4899"] == "vfat"
        and kl_rodata["mount_opts_0x488e"] == "posix_attr"
    )

    sf_uni_ok = (
        not sf_ok.abort_or_fault
        and sf_ok.observed_mount_source == "/dev/nflasha30"
        and sf_ok.observed_mount_target == "/usr/data/lut/"
        and sf_ok.observed_mount_flags == SETUPFILE_EXPECTED_MOUNT_FLAGS
        and not sf_ok.error_branch_entered
        and sf_ok.error_log_calls == 0
        and sf_ok.reached_msg_loop
        and sf_ok.observed_queue_id == SETUPFILE_EXPECTED_QUEUE_ID
        and not sf_enoent.abort_or_fault
        and sf_enoent.observed_mount_source == "/dev/nflasha20"
        and sf_enoent.error_branch_entered
        and sf_enoent.error_log_calls == 1
        and sf_enoent.logged_func_name == "RcvThread"
        and sf_enoent.logged_line == 304
        and sf_enoent.reached_msg_loop
        and not sf_einval.abort_or_fault
        and sf_einval.error_branch_entered
        and sf_einval.error_log_calls == 1
        and sf_einval.reached_msg_loop
    )

    kl_uni_ok = (
        not kl_ok.abort_or_fault
        and kl_ok.sp_preserved
        and kl_ok.observed_mount_source == "/dev/nflasha21"
        and kl_ok.observed_mount_target == "/etc/opelog/"
        and kl_ok.observed_mount_flags == KIKILOG_EXPECTED_MOUNT_FLAGS
        and not kl_ok.mount_rc_checked_by_caller
        and not kl_ok.early_exit_on_logs_mkdir
        and kl_ok.subdirs_created == (
            "/etc/opelog/logs/000/",
            "/etc/opelog/logs/001/",
            "/etc/opelog/logs/002/",
        )
        and not kl_enoent.abort_or_fault
        and kl_enoent.sp_preserved
        and kl_enoent.early_exit_on_logs_mkdir
        and kl_enoent.subdirs_created == ()
        and not kl_einval.abort_or_fault
        and kl_einval.sp_preserved
        and kl_einval.early_exit_on_logs_mkdir
        and kl_einval.subdirs_created == ()
    )

    all_insns_ok = all(c.matched for c in sf_checks) and all(c.matched for c in kl_checks)
    u4_closed = sf_sha_ok and kl_sha_ok and all_insns_ok and rodata_ok and sf_uni_ok and kl_uni_ok

    return StorageMountToleranceAuditReport(
        all_checks_passed=u4_closed,
        u4_closed=u4_closed,
        setupfile_sha256=sf_sha,
        setupfile_sha256_verified=sf_sha_ok,
        kikilog_sha256=kl_sha,
        kikilog_sha256_verified=kl_sha_ok,
        setupfile_pinned_insns=tuple(sf_checks),
        kikilog_pinned_insns=tuple(kl_checks),
        setupfile_rodata_strings=sf_rodata,
        kikilog_rodata_strings=kl_rodata,
        setupfile_unicorn_cases=(sf_ok, sf_enoent, sf_einval),
        kikilog_unicorn_cases=(kl_ok, kl_enoent, kl_einval),
    )


# ---------------------------------------------------------------------------
# Dimension B: Cross-Model BK4\0 Schema Audit & RAM-Shadow Synthesizer
# ---------------------------------------------------------------------------


def read_bk4_property_bytes(buf: bytes, key_id: int, offset: int = 0) -> Optional[bytes]:
    """Read a property payload from a `BK4\\0` record using Sony's 6-byte subsystem/property tables."""
    if offset + BK4_HEADER_SIZE > len(buf):
        return None
    if buf[offset + 0x0C : offset + 0x10] != BK4_MAGIC:
        return None
    subs, props, dataoff, datasize = struct.unpack_from("<IIII", buf, offset + 0x10)
    if offset + dataoff + datasize > len(buf):
        return None
    sub_idx = (key_id >> 16) & 0x7FFF
    prop_unit = key_id & 0xFFFF
    if sub_idx >= subs:
        return None
    sub_off = offset + BK4_HEADER_SIZE + sub_idx * 6
    if sub_off + 6 > len(buf):
        return None
    prop_count, first_idx = struct.unpack_from("<HI", buf, sub_off)
    if prop_unit >= prop_count or first_idx + prop_unit >= props:
        return None
    prop_off = offset + BK4_HEADER_SIZE + subs * 6 + (first_idx + prop_unit) * 6
    if prop_off + 6 > len(buf):
        return None
    _, word2 = struct.unpack_from("<HI", buf, prop_off)
    if word2 == 0xFFFFFFFF:
        return None
    tag8 = (word2 >> 24) & 0xFF
    off24 = word2 & 0xFFFFFF
    if not (dataoff <= off24 < dataoff + datasize):
        return None
    abs_off = offset + off24
    data_end = offset + dataoff + datasize
    if tag8 == 0xFF:
        if abs_off + 2 > data_end:
            return None
        sz = struct.unpack_from("<H", buf, abs_off)[0]
        if abs_off + 2 + sz > data_end:
            return None
        return buf[abs_off + 2 : abs_off + 2 + sz]
    if tag8 == 0x00:
        if abs_off + 4 > data_end:
            return None
        sz, max_sz = struct.unpack_from("<HH", buf, abs_off)
        if sz > max_sz or abs_off + 4 + max_sz > data_end:
            return None
        return buf[abs_off + 4 : abs_off + 4 + sz]
    if abs_off + tag8 > data_end:
        return None
    return buf[abs_off : abs_off + tag8]


def build_canonical_fa0080_normal_boot_table(
    donor_seed_bk4_path: Optional[Path] = DEFAULT_FX3_SEED_BK4_PATH,
) -> bytes:
    """Return the canonical 9,216-byte `0x00fa0080` Normal Boot `p3` descriptor table."""
    if donor_seed_bk4_path is not None and donor_seed_bk4_path.is_file():
        raw_seed = donor_seed_bk4_path.read_bytes()
        extracted = read_bk4_property_bytes(raw_seed, KEY_FA0080_BOOT_DESC, offset=0)
        if extracted is not None and len(extracted) == FA0080_TOTAL_BYTES:
            return extracted

    # Deterministic standalone fallback matching FX3 7.02 Normal Boot p3 descriptor table
    tbl = bytearray(FA0080_TOTAL_BYTES)
    canonical_slots = (
        (0, 0x401000000, 0x401FFFFFF, 3, 0x05000000, b"\\av-cam.bin"),
        (1, 0x400001000, 0x400001FFF, 2, 0x01000000, b"\\kemco.txt"),
        (2, 0x408000000, 0x408FFFFFF, 3, 0x01000000, b"\\initrd.img"),
        (3, 0x400080000, 0x4005FFFFF, 3, 0x81000000, b"\\vmlinux.bin"),
        (4, 0x400002000, 0x400005FFF, 2, 0x01000000, b"\\cxd90057.dtb"),
    )
    for idx, s_addr, e_addr, part, mode, path_b in canonical_slots:
        off = idx * FA0080_SLOT_STRIDE
        struct.pack_into("<QQII", tbl, off, s_addr, e_addr, part, mode)
        tbl[off + 0x18 : off + 0x18 + len(path_b)] = path_b
    return bytes(tbl)


def build_dual_slot_807b002b_payload(
    slot_a_media_id: int = 0x1000,
    slot_b_media_id: int = 0x1010,
    slot_a_dev_id: int = 0xDF10,
    slot_b_dev_id: int = 0xDF20,
) -> bytes:
    """Pack the 16-byte Dual-Slot (`0x1000`/`0x1010`) MediaConfig compatibility descriptor."""
    return struct.pack(
        "<HHHHII",
        slot_a_media_id & 0xFFFF,
        slot_b_media_id & 0xFFFF,
        slot_a_dev_id & 0xFFFF,
        slot_b_dev_id & 0xFFFF,
        2,  # active_slot_count == 2 (CFexpress Type A / SDXC Slot A & Slot B)
        0x00000003,  # dual-slot active bitmask
    )


def _build_mediaconfig_64byte_slot_record(media_id: int, dev_id: int, slot_num_1based: int) -> bytes:
    """Build 64-byte `InfraMediaConfig::CreateMediaInfoByBackup` (`0x00cf0000 + slot*0x40`) record."""
    rec = bytearray(64)
    if media_id == 0:
        return bytes(rec)
    struct.pack_into("<IH", rec, 0, media_id, dev_id)
    rec[6:16] = bytes([0x03, 0x0A, 0x00, 0x00, 0x00, 0x03, slot_num_1based & 0xFF, 0x03, 0x00, 0x41])
    return bytes(rec)


@dataclass(frozen=True)
class RamShadowBk4Bundle:
    bk4_bytes: bytes
    sha256: str
    total_bytes: int
    flash_write_allowed: bool
    target_backing: str
    active_byte8_selector: int
    expected_checksum32: int
    property_crc16_map: Dict[str, int]
    synthesized_key_count: int


@dataclass(frozen=True)
class RamShadowBk4AuditResult:
    valid: bool
    flash_write_prohibited: bool
    bk4_header_valid: bool
    selector_byte8_zero_ok: bool
    strict_loader_unselectable_ok: bool
    checksum32_ok: bool
    all_property_crc16_ok: bool
    fixed_area_keys_ok: bool
    fa0080_normal_boot_p3_ok: bool
    dual_slot_media_ids_ok: bool
    boot_screen_enum_ok: bool
    observed_slot_media_ids: Tuple[int, int]
    bk4_record_summary: Optional[BK4RecordSummary]
    errors: Tuple[str, ...]


def synthesize_ram_shadow_bk4(
    *,
    flash_write_allowed: bool = False,
    active_byte8: int = 0x00,
    fixed_area_top: int = DEFAULT_SHADOW_FIXED_AREA_TOP,
    fixed_area_size: int = DEFAULT_SHADOW_FIXED_AREA_SIZE,
    fa0080_table: Optional[bytes] = None,
    slot_a_media_id: int = 0x1000,
    slot_b_media_id: int = 0x1010,
    boot_screen_214: int = 0,
    boot_screen_218: int = 1,
) -> RamShadowBk4Bundle:
    """Synthesize a deterministic RAM-only shadow `BK4\\0` container for FX6-on-FX3 cold-boot safety.

    Physical `p2:/setting/Backup.bin` is NEVER modified (`flash_write_allowed` MUST be `False`).
    """
    if flash_write_allowed:
        raise ValueError(
            "Forbidden persistent flash write request: physical p2:/setting/Backup.bin must NEVER be modified "
            "(flash_write_allowed must be False)"
        )
    if not (0 <= active_byte8 <= 0xFF):
        raise ValueError(f"Invalid active_byte8: {active_byte8}")

    fa0080_payload = (
        fa0080_table if fa0080_table is not None else build_canonical_fa0080_normal_boot_table()
    )
    if len(fa0080_payload) != FA0080_TOTAL_BYTES:
        raise ValueError(f"0x00fa0080 table must be exactly {FA0080_TOTAL_BYTES} bytes, got {len(fa0080_payload)}")

    kv_map: Dict[int, bytes] = {
        KEY_FIXED_AREA_TOP: struct.pack("<Q", fixed_area_top),
        KEY_FIXED_AREA_SIZE: struct.pack("<Q", fixed_area_size),
        KEY_FA0080_BOOT_DESC: fa0080_payload,
        KEY_FA0084_BOOT_SELECTOR: struct.pack("<Q", 0),  # Normal Boot selector == 0
        KEY_DUAL_SLOT_MEDIA_SHADOW: build_dual_slot_807b002b_payload(
            slot_a_media_id=slot_a_media_id,
            slot_b_media_id=slot_b_media_id,
        ),
        KEY_BOOT_SCREEN_MODEL_A: bytes([boot_screen_214 & 0xFF]),
        KEY_BOOT_SCREEN_MODEL_B: bytes([boot_screen_218 & 0xFF]),
    }

    # Populate 64-byte MediaConfig slot blocks (`0x00cf0000..0x00cf00bf`) pruning FX3's 3rd slot `0x1002`
    slot0_rec = _build_mediaconfig_64byte_slot_record(slot_a_media_id, FX6_DUAL_SLOT_DEV_IDS[0], 1)
    slot1_rec = _build_mediaconfig_64byte_slot_record(slot_b_media_id, FX6_DUAL_SLOT_DEV_IDS[1], 2)
    slot2_rec = _build_mediaconfig_64byte_slot_record(0, 0, 0)
    for i in range(64):
        kv_map[KEY_MEDIACONFIG_SLOT0_BASE + i] = bytes([slot0_rec[i]])
        kv_map[KEY_MEDIACONFIG_SLOT1_BASE + i] = bytes([slot1_rec[i]])
        kv_map[KEY_MEDIACONFIG_SLOT2_BASE + i] = bytes([slot2_rec[i]])

    # Group keys by 15-bit Sony subsystem index `(key >> 16) & 0x7fff`
    by_sub: Dict[int, Dict[int, bytes]] = {}
    for k, val in kv_map.items():
        s_idx = (k >> 16) & 0x7FFF
        u_idx = k & 0xFFFF
        if s_idx >= BK4_SHADOW_SUBSYSTEM_COUNT:
            raise ValueError(f"Subsystem index {hex(s_idx)} exceeds {BK4_SHADOW_SUBSYSTEM_COUNT}")
        by_sub.setdefault(s_idx, {})[u_idx] = val

    sub_entries: List[Tuple[int, int]] = []
    prop_units: List[Optional[Tuple[int, bytes]]] = []
    for s_idx in range(BK4_SHADOW_SUBSYSTEM_COUNT):
        units = by_sub.get(s_idx)
        if not units:
            sub_entries.append((0, 0))
            continue
        max_unit = max(units.keys())
        cnt = max_unit + 1
        first_prop = len(prop_units)
        sub_entries.append((cnt, first_prop))
        for u_idx in range(cnt):
            if u_idx in units:
                full_key = (0x80000000 if (s_idx == 0x007B and u_idx == 0x002B) else 0) | (s_idx << 16) | u_idx
                # Preserve exact high flags (`0x02cf0214` -> `0x02cf`, `0x807b002b` -> `0x807b`)
                for orig_k in kv_map:
                    if ((orig_k >> 16) & 0x7FFF) == s_idx and (orig_k & 0xFFFF) == u_idx:
                        full_key = orig_k
                        break
                prop_units.append((full_key, units[u_idx]))
            else:
                prop_units.append(None)

    total_props = len(prop_units)
    raw_table_end = BK4_HEADER_SIZE + BK4_SHADOW_SUBSYSTEM_COUNT * 6 + total_props * 6
    data_offset = (raw_table_end + 15) & ~15

    data_blob = bytearray()
    prop_table_bytes = bytearray()
    crc16_map: Dict[str, int] = {}

    for item in prop_units:
        if item is None:
            prop_table_bytes.extend(struct.pack("<HI", 0x0000, 0xFFFFFFFF))
            continue
        full_key, payload = item
        rel_off = data_offset + len(data_blob)
        crc16 = compute_crc16_ccitt(struct.pack("<I", full_key) + payload)
        crc16_map[f"0x{full_key:08x}"] = crc16

        if len(payload) == FA0080_TOTAL_BYTES:
            tag8 = 0xFF
            data_blob.extend(struct.pack("<H", len(payload)))
            data_blob.extend(payload)
            data_blob.extend(struct.pack("<H", crc16))
        elif 1 <= len(payload) <= 0xFE:
            tag8 = len(payload)
            data_blob.extend(payload)
            data_blob.extend(struct.pack("<H", crc16))
        else:
            tag8 = 0x00
            data_blob.extend(struct.pack("<HH", len(payload), len(payload)))
            data_blob.extend(payload)
            data_blob.extend(struct.pack("<H", crc16))

        word2 = ((tag8 & 0xFF) << 24) | (rel_off & 0xFFFFFF)
        prop_table_bytes.extend(struct.pack("<HI", BK4_ATTR_SHADOW_CRC16, word2))

    # Align data_size to 4 bytes
    while len(data_blob) % 4 != 0:
        data_blob.append(0)
    data_size = len(data_blob)
    total_bytes = data_offset + data_size

    buf = bytearray(total_bytes)
    struct.pack_into("<II", buf, 0x00, BK4_VERSION_WORD0, BK4_SYNC_MARKER)
    buf[0x08] = active_byte8 & 0xFF
    buf[0x0C:0x10] = BK4_MAGIC
    struct.pack_into(
        "<IIIIII",
        buf,
        0x10,
        BK4_SHADOW_SUBSYSTEM_COUNT,
        total_props,
        data_offset,
        data_size,
        0,     # checksum placeholder at +0x20
        0x30,  # canonical BK4 header flags
    )
    struct.pack_into("<i", buf, 0x2C, 0)
    buf[0xC0 : 0xC0 + len(BK4_SHADOW_MODEL_TAG)] = BK4_SHADOW_MODEL_TAG

    # Write 6-byte subsystem table + 6-byte property table + data blob
    for idx, (cnt, first_p) in enumerate(sub_entries):
        struct.pack_into("<HI", buf, BK4_HEADER_SIZE + idx * 6, cnt, first_p)
    prop_base = BK4_HEADER_SIZE + BK4_SHADOW_SUBSYSTEM_COUNT * 6
    buf[prop_base : prop_base + len(prop_table_bytes)] = prop_table_bytes
    buf[data_offset : data_offset + data_size] = data_blob

    # Compute Sony loader_nor.bin 0xfe04d514 32-bit unsigned byte-sum checksum (skipping 0x20..0x24)
    csum32 = (sum(buf[0:0x20]) + sum(buf[0x24:total_bytes])) & 0xFFFFFFFF
    struct.pack_into("<I", buf, 0x20, csum32)

    final_bytes = bytes(buf)
    return RamShadowBk4Bundle(
        bk4_bytes=final_bytes,
        sha256=hashlib.sha256(final_bytes).hexdigest(),
        total_bytes=total_bytes,
        flash_write_allowed=False,
        target_backing="RAM_TMPFS_SHADOW_ONLY",
        active_byte8_selector=active_byte8,
        expected_checksum32=csum32,
        property_crc16_map=crc16_map,
        synthesized_key_count=len(kv_map),
    )


def _verify_shadow_property_crc16(buf: bytes, key_id: int) -> Tuple[bool, Optional[bytes], str]:
    """Verify both presence and trailing 16-bit `CRC-16/CCITT-FALSE` checksum of a shadow property."""
    subs, props, dataoff, datasize = struct.unpack_from("<IIII", buf, 0x10)
    sub_idx = (key_id >> 16) & 0x7FFF
    unit_idx = key_id & 0xFFFF
    if sub_idx >= subs:
        return False, None, f"Key {hex(key_id)} subsystem {hex(sub_idx)} >= {subs}"
    cnt, first_idx = struct.unpack_from("<HI", buf, BK4_HEADER_SIZE + sub_idx * 6)
    if unit_idx >= cnt or first_idx + unit_idx >= props:
        return False, None, f"Key {hex(key_id)} unit {hex(unit_idx)} absent"
    prop_off = BK4_HEADER_SIZE + subs * 6 + (first_idx + unit_idx) * 6
    attr, word2 = struct.unpack_from("<HI", buf, prop_off)
    if word2 == 0xFFFFFFFF:
        return False, None, f"Key {hex(key_id)} sentinel 0xffffffff"
    tag8 = (word2 >> 24) & 0xFF
    off24 = word2 & 0xFFFFFF
    data_end = dataoff + datasize
    if tag8 == 0xFF:
        if off24 + 2 > data_end:
            return False, None, f"Key {hex(key_id)} prefix truncated"
        sz = struct.unpack_from("<H", buf, off24)[0]
        payload_start = off24 + 2
    elif tag8 == 0x00:
        if off24 + 4 > data_end:
            return False, None, f"Key {hex(key_id)} var prefix truncated"
        sz, _ = struct.unpack_from("<HH", buf, off24)
        payload_start = off24 + 4
    else:
        sz = tag8
        payload_start = off24

    if payload_start + sz + 2 > data_end or payload_start + sz + 2 > len(buf):
        return False, None, f"Key {hex(key_id)} payload/CRC16 overflows record bounds"
    payload = buf[payload_start : payload_start + sz]
    if (attr & BK4_ATTR_SHADOW_CRC16) != BK4_ATTR_SHADOW_CRC16:
        return False, payload, f"Key {hex(key_id)} missing shadow CRC16 attribute 0x00c0 (got {hex(attr)})"
    stored_crc16 = struct.unpack_from("<H", buf, payload_start + sz)[0]
    expected_crc16 = compute_crc16_ccitt(struct.pack("<I", key_id) + payload)
    if stored_crc16 != expected_crc16:
        return (
            False,
            payload,
            f"Key {hex(key_id)} 16-bit CRC mismatch: stored={hex(stored_crc16)} computed={hex(expected_crc16)}",
        )
    return True, payload, ""


def audit_ram_shadow_bk4(
    bk4_bytes: bytes,
    *,
    flash_write_allowed: bool = False,
) -> RamShadowBk4AuditResult:
    """Validate a synthesized RAM-shadow `BK4\\0` payload against all FX6-on-FX3 cold-boot invariants."""
    errors: List[str] = []
    flash_prohibited = not flash_write_allowed
    if flash_write_allowed:
        errors.append("Physical p2:/setting/Backup.bin writes are strictly prohibited (flash_write_allowed=True)")

    summary, bk4_errs = parse_bk4_record(bk4_bytes, offset=0, record_index=0)
    errors.extend(bk4_errs)
    if summary is None:
        return RamShadowBk4AuditResult(
            valid=False,
            flash_write_prohibited=flash_prohibited,
            bk4_header_valid=False,
            selector_byte8_zero_ok=False,
            strict_loader_unselectable_ok=False,
            checksum32_ok=False,
            all_property_crc16_ok=False,
            fixed_area_keys_ok=False,
            fa0080_normal_boot_p3_ok=False,
            dual_slot_media_ids_ok=False,
            boot_screen_enum_ok=False,
            observed_slot_media_ids=(0, 0),
            bk4_record_summary=None,
            errors=tuple(errors),
        )

    header_ok = summary.magic_ok and summary.sync_word == BK4_SYNC_MARKER
    byte8_zero_ok = summary.active_byte8 == 0x00
    if not byte8_zero_ok:
        errors.append(
            f"Shadow BK4 header byte 8 boot/record selector must be 0x00, got {hex(summary.active_byte8)}"
        )
    unselectable_ok = summary.strict_loader_selectable is False
    if not unselectable_ok:
        errors.append("Shadow BK4 record must remain strict_loader_selectable == False")

    # Check mandatory keys + 16-bit per-property CRC16s
    mandatory_keys = (
        KEY_FIXED_AREA_TOP,
        KEY_FIXED_AREA_SIZE,
        KEY_FA0080_BOOT_DESC,
        KEY_FA0084_BOOT_SELECTOR,
        KEY_DUAL_SLOT_MEDIA_SHADOW,
        KEY_BOOT_SCREEN_MODEL_A,
        KEY_BOOT_SCREEN_MODEL_B,
    )
    crc16_ok = True
    extracted: Dict[int, bytes] = {}
    for key_id in mandatory_keys:
        ok_k, val_k, err_k = _verify_shadow_property_crc16(bk4_bytes, key_id)
        if not ok_k or val_k is None:
            crc16_ok = False
            errors.append(err_k)
        else:
            extracted[key_id] = val_k

    # Verify FixedArea keys (`0x00fa0028` & `0x00fa005d`)
    fixed_ok = False
    if KEY_FIXED_AREA_TOP in extracted and KEY_FIXED_AREA_SIZE in extracted:
        raw_top = extracted[KEY_FIXED_AREA_TOP]
        raw_sz = extracted[KEY_FIXED_AREA_SIZE]
        if len(raw_top) == 8 and len(raw_sz) == 8:
            top_u64 = struct.unpack("<Q", raw_top)[0]
            sz_u64 = struct.unpack("<Q", raw_sz)[0]
            fixed_ok = (top_u64 >= 0x400000000) and ((top_u64 & 0xFFF) == 0) and (sz_u64 >= MIN_MONDRV_FIXED_AREA_SIZE)
            if not fixed_ok:
                errors.append(
                    f"Invalid FixedArea contract: top={hex(top_u64)} size={hex(sz_u64)} (need >= 0x5b400)"
                )
        else:
            errors.append("FixedArea keys 0x00fa0028/0x00fa005d must be 8 bytes each")

    # Verify `0x00fa0080` Normal Boot `p3` invariant + `0x00fa0084` == 0
    fa0080_ok = False
    if KEY_FA0080_BOOT_DESC in extracted and KEY_FA0084_BOOT_SELECTOR in extracted:
        slots, fa_errs = parse_fa0080_table(extracted[KEY_FA0080_BOOT_DESC])
        errors.extend(fa_errs)
        by_path = {s.path: s for s in slots}
        sel_u64 = struct.unpack("<Q", extracted[KEY_FA0084_BOOT_SELECTOR])[0]
        p3_paths_ok = all(
            p in by_path and by_path[p].partition == 3
            for p in ("\\av-cam.bin", "\\initrd.img", "\\vmlinux.bin")
        )
        slot0_mode_low_zero = ("\\av-cam.bin" in by_path) and ((by_path["\\av-cam.bin"].mode & 0xFF) == 0x00)
        if not p3_paths_ok:
            errors.append("0x00fa0080 Normal Boot p3 invariant violated: \\av-cam.bin/\\initrd.img/\\vmlinux.bin must target partition 3")
        if not slot0_mode_low_zero or sel_u64 != 0:
            errors.append(f"0x00fa0080/0x00fa0084 Normal Boot selector invariant violated (sel={hex(sel_u64)})")
        fa0080_ok = (len(fa_errs) == 0) and p3_paths_ok and slot0_mode_low_zero and (sel_u64 == 0)

    # Verify `0x807b002b` Dual-Slot `0x1000`/`0x1010` MediaConfig descriptor AND `0x00cf0000..0x00cf00bf`
    media_ok = False
    observed_slots = (0, 0)
    if KEY_DUAL_SLOT_MEDIA_SHADOW in extracted:
        m_raw = extracted[KEY_DUAL_SLOT_MEDIA_SHADOW]
        if len(m_raw) == 16:
            sa, sb, da, db, cnt, mask = struct.unpack("<HHHHII", m_raw)
            observed_slots = (sa, sb)
            # Also check 0x00cf0000..0x00cf0003 (Slot 0), 0x00cf0040..0x00cf0043 (Slot 1), and 0x00cf0080..0x00cf0083 (Slot 2 == 0)
            cf_ok = True
            cf_bytes: List[bytes] = []
            for base_k in (KEY_MEDIACONFIG_SLOT0_BASE, KEY_MEDIACONFIG_SLOT1_BASE, KEY_MEDIACONFIG_SLOT2_BASE):
                word_b = bytearray()
                for j in range(4):
                    ok_b, val_b, err_b = _verify_shadow_property_crc16(bk4_bytes, base_k + j)
                    if not ok_b or val_b is None or len(val_b) != 1:
                        cf_ok = False
                        crc16_ok = False
                        errors.append(err_b or f"Invalid 1B MediaConfig byte at {hex(base_k + j)}")
                        break
                    word_b.append(val_b[0])
                cf_bytes.append(bytes(word_b))
            cf_ids = (
                tuple(struct.unpack("<I", b)[0] for b in cf_bytes)
                if cf_ok and all(len(b) == 4 for b in cf_bytes)
                else (-1, -1, -1)
            )
            media_ok = (
                (sa, sb) == FX6_DUAL_SLOT_MEDIA_IDS
                and (da, db) == FX6_DUAL_SLOT_DEV_IDS
                and cnt == 2
                and mask == 0x3
                and cf_ok
                and cf_ids == (0x1000, 0x1010, 0x0000)
            )
            if not media_ok:
                errors.append(
                    f"Invalid Dual-Slot MediaConfig IDs: 0x807b002b={(hex(sa), hex(sb))} cf_slots={tuple(hex(x) for x in cf_ids)} "
                    "(expected (0x1000, 0x1010) and pruned slot2=0x0)"
                )
        else:
            errors.append(f"0x807b002b payload must be 16 bytes, got {len(m_raw)}")

    # Verify `0x02cf0214` / `0x02cf0218` boot-screen enum safety `{0, 1}`
    enum_ok = False
    if KEY_BOOT_SCREEN_MODEL_A in extracted and KEY_BOOT_SCREEN_MODEL_B in extracted:
        enum_res = verify_boot_screen_enum_contract(
            extracted[KEY_BOOT_SCREEN_MODEL_A],
            extracted[KEY_BOOT_SCREEN_MODEL_B],
            target_appfw="FX6_601",
        )
        enum_ok = bool(enum_res["valid"])
        for e in enum_res["errors"]:  # type: ignore[union-attr]
            errors.append(str(e))

    valid = (
        flash_prohibited
        and header_ok
        and byte8_zero_ok
        and unselectable_ok
        and summary.checksum_ok
        and crc16_ok
        and fixed_ok
        and fa0080_ok
        and media_ok
        and enum_ok
        and len(errors) == 0
    )
    return RamShadowBk4AuditResult(
        valid=valid,
        flash_write_prohibited=flash_prohibited,
        bk4_header_valid=header_ok,
        selector_byte8_zero_ok=byte8_zero_ok,
        strict_loader_unselectable_ok=unselectable_ok,
        checksum32_ok=summary.checksum_ok,
        all_property_crc16_ok=crc16_ok,
        fixed_area_keys_ok=fixed_ok,
        fa0080_normal_boot_p3_ok=fa0080_ok,
        dual_slot_media_ids_ok=media_ok,
        boot_screen_enum_ok=enum_ok,
        observed_slot_media_ids=observed_slots,
        bk4_record_summary=summary,
        errors=tuple(errors),
    )


@dataclass(frozen=True)
class CrossModelBackupContractReport:
    all_checks_passed: bool
    fx6_libbackup_sha256_verified: bool
    fx6_libbackup_manager_sha256_verified: bool
    fx3_libbackup_sha256_verified: bool
    fx6_backup_export_count: int
    fx3_backup_export_count: int
    fx3_exports_superset_of_fx6: bool
    backup_section_receipt_verified: bool
    backup_key_values_receipt_verified: bool
    fx6_template_subsystems: int
    fx6_template_properties: int
    fx3_seed_subsystems: int
    fx3_seed_properties: int
    fx3_extra_slot2_media_id: int
    ram_shadow_bundle_sha256: str
    ram_shadow_bundle_bytes: int
    ram_shadow_audit: RamShadowBk4AuditResult


def audit_cross_model_backup_contracts(
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx6_backup_manager_path: Path = DEFAULT_FX6_BACKUP_MANAGER_PATH,
    fx3_libbackup_path: Path = DEFAULT_FX3_LIBBACKUP_PATH,
    backup_section_audit_path: Path = DEFAULT_BACKUP_SECTION_AUDIT_PATH,
    backup_key_values_path: Path = DEFAULT_BACKUP_KEY_VALUES_PATH,
    fx6_template_bk4_path: Path = DEFAULT_FX6_TEMPLATE_BK4_PATH,
    fx3_seed_bk4_path: Path = DEFAULT_FX3_SEED_BK4_PATH,
) -> CrossModelBackupContractReport:
    """Execute Dimension B cross-model Backup ABI/schema audit and RAM-shadow `BK4\\0` verification."""
    fx6_lb = (fx6_lib_dir / "libbackup.so").read_bytes()
    fx6_lbm = fx6_backup_manager_path.read_bytes()
    fx3_lb = fx3_libbackup_path.read_bytes()

    fx6_lb_ok = hashlib.sha256(fx6_lb).hexdigest() == PINNED_FX6_LIBBACKUP_SHA256
    fx6_lbm_ok = hashlib.sha256(fx6_lbm).hexdigest() == PINNED_FX6_LIBBACKUP_MANAGER_SHA256
    fx3_lb_ok = hashlib.sha256(fx3_lb).hexdigest() == PINNED_FX3_LIBBACKUP_SHA256

    fx6_syms = {
        k for k in _parse_elf64_defined_dynsyms(fx6_lb) if k.startswith(("Backup_", "backup_"))
    }
    fx3_syms = {
        k for k in _parse_elf64_defined_dynsyms(fx3_lb) if k.startswith(("Backup_", "backup_"))
    }
    lbm_syms = _parse_elf64_defined_dynsyms(fx6_lbm)
    superset_ok = fx6_syms.issubset(fx3_syms) and len(fx6_syms) >= 50 and "_Z11BkDmn_writejPKvi" in lbm_syms

    sec_receipt = json.loads(backup_section_audit_path.read_text(encoding="utf-8"))
    sec_ok = (
        sec_receipt.get("schema") == "fx6-r50-backup-section-audit-v1"
        and sec_receipt.get("claim_section_offset") == "0x75c"
        and sec_receipt.get("file_offset_for_claim") == "0x7c4"
        and sec_receipt.get("claim_supported") is True
    )

    kv_text = backup_key_values_path.read_text(encoding="utf-8")
    kv_ok = (
        "0x2cf0214 len 4 raw 16161616" in kv_text
        and "0x2cf0218 len 4 raw 19191919" in kv_text
        and "0x2cf0214 len 1 raw 00" in kv_text
        and "0x2cf0218 len 1 raw 01" in kv_text
    )

    fx6_tmpl = fx6_template_bk4_path.read_bytes()
    fx3_seed = fx3_seed_bk4_path.read_bytes()
    fx6_tmpl_sha_ok = hashlib.sha256(fx6_tmpl).hexdigest() == PINNED_FX6_TEMPLATE_BK4_SHA256
    fx3_seed_sha_ok = hashlib.sha256(fx3_seed).hexdigest() == PINNED_FX3_SEED_BK4_SHA256

    fx6_rec, fx6_errs = parse_bk4_record(fx6_tmpl, offset=0, record_index=0)
    fx3_rec, fx3_errs = parse_bk4_record(fx3_seed, offset=0, record_index=0)
    assert fx6_rec is not None and fx3_rec is not None

    # Observe FX3 extra slot 2 (`0x00cf0080..0x00cf0083` == `0x1002`) vs FX6 (`0x0000`)
    fx3_s2_bytes = bytes(
        (read_bk4_property_bytes(fx3_seed, KEY_MEDIACONFIG_SLOT2_BASE + i) or b"\x00")[0]
        for i in range(4)
    )
    fx3_slot2_id = struct.unpack("<I", fx3_s2_bytes)[0]

    fa0080_from_fx3 = read_bk4_property_bytes(fx3_seed, KEY_FA0080_BOOT_DESC)
    shadow_bundle = synthesize_ram_shadow_bk4(
        flash_write_allowed=False,
        fa0080_table=fa0080_from_fx3,
    )
    shadow_audit = audit_ram_shadow_bk4(shadow_bundle.bk4_bytes, flash_write_allowed=False)

    all_ok = (
        fx6_lb_ok
        and fx6_lbm_ok
        and fx3_lb_ok
        and superset_ok
        and sec_ok
        and kv_ok
        and fx6_tmpl_sha_ok
        and fx3_seed_sha_ok
        and len(fx6_errs) == 0
        and len(fx3_errs) == 0
        and fx6_rec.subsystems == 840
        and fx3_rec.subsystems == 819
        and fx3_slot2_id == 0x1002
        and shadow_audit.valid
    )

    return CrossModelBackupContractReport(
        all_checks_passed=all_ok,
        fx6_libbackup_sha256_verified=fx6_lb_ok,
        fx6_libbackup_manager_sha256_verified=fx6_lbm_ok,
        fx3_libbackup_sha256_verified=fx3_lb_ok,
        fx6_backup_export_count=len(fx6_syms),
        fx3_backup_export_count=len(fx3_syms),
        fx3_exports_superset_of_fx6=superset_ok,
        backup_section_receipt_verified=sec_ok,
        backup_key_values_receipt_verified=kv_ok,
        fx6_template_subsystems=fx6_rec.subsystems,
        fx6_template_properties=fx6_rec.properties,
        fx3_seed_subsystems=fx3_rec.subsystems,
        fx3_seed_properties=fx3_rec.properties,
        fx3_extra_slot2_media_id=fx3_slot2_id,
        ram_shadow_bundle_sha256=shadow_bundle.sha256,
        ram_shadow_bundle_bytes=shadow_bundle.total_bytes,
        ram_shadow_audit=shadow_audit,
    )


@dataclass(frozen=True)
class Phase6BackupMountToleranceReport:
    all_checks_passed: bool
    dimension_a_mount_tolerance: StorageMountToleranceAuditReport
    dimension_b_backup_contracts: CrossModelBackupContractReport


def run_backup_mount_tolerance_verification(
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
) -> Phase6BackupMountToleranceReport:
    """Execute complete Phase 6 `U4` Storage Mount-Tolerance & RAM-Shadow `BK4\\0` verification."""
    dim_a = audit_storage_mount_tolerance(fx6_lib_dir=fx6_lib_dir)
    dim_b = audit_cross_model_backup_contracts(fx6_lib_dir=fx6_lib_dir)
    return Phase6BackupMountToleranceReport(
        all_checks_passed=(dim_a.all_checks_passed and dim_b.all_checks_passed),
        dimension_a_mount_tolerance=dim_a,
        dimension_b_backup_contracts=dim_b,
    )
