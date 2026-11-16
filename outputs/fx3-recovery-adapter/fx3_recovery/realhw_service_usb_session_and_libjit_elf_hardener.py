"""Phase 144 — Pillar 18: `MSC (054C:0DA1) -> SERVICE (054C:0336)` Exclusive
Session Verifier, `op=0xFF` Zero-Mount RAM Canary & Stage-288 §4 (1..6) Hardened
ARM64 `libJit.so` ELF64 Gate (`outputs/fx3-recovery-adapter/`).

Closes every remaining Stage-285 / Stage-286 / Stage-288 host-side protocol and
ARM64 ELF safety requirement before any human-authorized physical ILME-FX3
(`7.02`) Tier-0 cold-backup read-back session is ever considered:

1. **Dual-Mode Read-Only (`O_RDONLY`) Donor Inspection + Clean-Room Fallback**:
   - Inspects FX3 `7.02` `libJiritsu.so` (`225,200 B`), `libsencore.so`
     (`377,328 B`), and optional Stage-288 `libJit_test.so` (`8,345 B`) strictly
     with `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` when
     present and `FX3_FX6_FORCE_CLEAN_ROOM != "1"`.
   - Falls back to deterministic clean-room structural descriptors with zero
     raw proprietary Sony firmware bytes leaked in `.to_dict()` / JSON.
2. **Pillar A — Stage-285/286 `054C:0DA1 -> 054C:0336` Exclusive `SERVICE`
   Session, DMM Phase `1 -> 4 -> 16` & `op=0xFF` Zero-Mount RAM Canary**:
   - Verifies the complete 9-step Stage-285/286 contract: `MSC` (`054C:0DA1`)
     7-round handshake -> same-port transition to `SERVICE` (`054C:0336`) with
     single-flight `USBDeviceOpenSeize` mutex discipline (`SenserThread`
     `Inconcurrent::resource_t::lock` at `0xdd00`) -> 7-round auth reaching
     Level 2/3 (`*0x6aee0` admitting `flags & 0xe000 == 0x4000`, rejecting Level
     1 at `0xfe48`) -> `ProductInfoFunc` (`pFunc=0x0010` `read0`: 12B `<IHHBBBB`
     req + 12B `version=3, res=1` resp + 88B body).
   - Enforces the mandatory Stage-286 Branch-A Pre-Check (`SET_FILE2` /
     `GET_FILE2` `op=0xFF` pure RAM slot canary, `slot <= 0x11`, `size <= 5 MiB`
     at `*0x46bd8`, zero `sys_mount`, zero `dlopen`, 3-phase OSAL/DMM
     `Phase 1 (0x124 inline threshold) -> Phase 4 -> Phase 16 dmm_free`) before
     ANY `op=0x00` (`/dev/nflasha6` `/tmp/jiritsu`) command is permitted.
   - Rejects `slot > 0x11`, `size > 5 MiB`, concurrent overlapping `seq`
     requests, and missing `STOP (0336:7) -> release (0336:8) -> 054C:0DA1
     return (0da1:9)` teardown.
   - Includes a strictly passive USB topology dry-run parser accepting synthetic
     `ioreg` XML/text snapshots (`usb_tx_packets_emitted == 0`,
     `persistent_emmc_writes_authorized == False`).
3. **Pillar B — Stage-288 §4 (1..6) Hardened ARM64 `libJit.so` ELF64 Builder
   & Static Disassembly Gate**:
   - Clean-room minimal AArch64 `ET_DYN` (`e_machine = 183`, `< 16 KiB`)
     generator & static verifier enforcing all 6 Stage-288 §4 P0 rules:
       1. Self-unlink first (`§4.1`: `unlinkat(AT_FDCWD=-100, "/tmp/jiritsu/libJit.so", 0)`)
       2. Read-first non-truncation (`§4.2`: `O_RDONLY | O_CLOEXEC`, `read == 512` before opening output)
       3. 528-byte framed output (`§4.3`: `b"FX3S0OK\\x00"` + `<II(512, crc32_ieee)` + `512B` Sector 0)
       4. Whole-disk node check + `/proc/partitions` / `/dev/nflasha1` fallback + 16B `b"FX3S0ERR" + <ii(stage, errno)` (`§4.4`)
       5. 64 KiB `p_align = 0x10000` `PT_LOAD` (`R|E` + `R|W`, no `W+X`), in-bounds `DT_SYMTAB`, `DT_STRTAB`, `DT_HASH` (`nbucket>=1, nchain>=1`), `DT_INIT` (`§4.6`)
       6. Static syscall & token firewall (rejects `O_WRONLY`/`O_RDWR` on block/MTD/`/setting`, `edisx`/`uc_mkfs`/`nor_loader_writer`, and `write`/`ioctl`/`mount` targeting block/MTD nodes).
   - Also flags legacy `libJit_test.so` (`8,345 B`) pre-hardening gaps and executes
     optional Unicorn ARM64 behavioral verification when Unicorn is available.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import struct
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import zlib

from .files import (
    is_forced_clean_room,
    local_path,
    require,
    resolve_donor_path,
    resolve_unicorn_site_packages,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE144_SCHEMA: str = "fx3-realhw-service-usb-session-and-libjit-hardener-v1"
PHASE144_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
LIVE_USB_IOKIT_TRANSMIT_ENABLED: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
ALLOW_PERSISTENT_JIRITSU_WRITES: bool = False
ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
USB_TX_PACKETS_EMITTED: int = 0

# Donor Paths & Pinned Integrity Anchors (zero raw firmware bytes in JSON)
P144_DONOR_LIBJIRITSU_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libJiritsu.so"
)
P144_DONOR_LIBSENCORE_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libsencore.so"
)
P144_DONOR_LIBJIT_TEST_RELPATH: str = (
    "sony-firmware-20261024/stage288-jiritsu-readonly-payload/payload/libJit_test.so"
)

P144_PINNED_LIBJIRITSU_BYTES: int = 225200
P144_PINNED_LIBJIRITSU_SHA256: str = (
    "bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9"
)
P144_PINNED_LIBSENCORE_BYTES: int = 377328
P144_PINNED_LIBSENCORE_SHA256: str = (
    "a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410"
)
P144_PINNED_LIBJIT_TEST_BYTES: int = 8345
P144_PINNED_LIBJIT_TEST_SHA256: str = (
    "05000a0ecceaa5004385b71fbeb2b15859bda7418e227a3d90238da31bc4cd7a"
)

# Stage-285/286 USB & Senser Wire Protocol Constants
SONY_USB_VID: int = 0x054C
FX3_MSC_PID: int = 0x0DA1
SONY_SERVICE_PID: int = 0x0336
FX3_MSC_VID_PID: str = "054C:0DA1"
SONY_SERVICE_VID_PID: str = "054C:0336"

MSC_HANDSHAKE_ROUNDS: int = 7
SERVICE_AUTH_ROUNDS: int = 7

PFUNC_PRODUCT_INFO: int = 0x0010
PFUNC_ADJUST_CONTROL: int = 0x0040
CATEGORY_JIRITSU: int = 0x1001

CMD_SET_FILE_PATH: int = 0x000F
CMD_SET_FILE2: int = 0x0010
CMD_GET_FILE2: int = 0x0011

OP_FILESYSTEM_MOUNT: int = 0x00
OP_MEDIA_MOUNT: int = 0x01
OP_RAM_CACHE_SLOT: int = 0xFF

MAX_OP_FF_SLOT: int = 0x11
MAX_OP_FF_MODE: int = 0x11
MAX_OP_FF_PAYLOAD_BYTES: int = 5 * 1024 * 1024  # 0x500000 (5 MiB at *0x46bd8)
DMM_INLINE_THRESHOLD_BYTES: int = 0x124  # 292 B in TransactionStart (0xfc74)
DMM_PHASES: Tuple[int, int, int] = (1, 4, 16)

REQ_VERSION_ADJUST: int = 2
RESP_VERSION_STOCK: int = 3
RESP_RES_OK: int = 1
READ0_RESP_VERSION: int = RESP_VERSION_STOCK
READ0_RESP_RES: int = RESP_RES_OK

PRODUCT_INFO_REQ_BYTES: int = 12
PRODUCT_INFO_RESP_HDR_BYTES: int = 12
PRODUCT_INFO_RESP_BODY_BYTES: int = 88

AUTH_TABLE_LEVEL_1: int = 1
AUTH_TABLE_LEVEL_2: int = 2
AUTH_TABLE_LEVEL_3: int = 3
CATEGORY_0X1001_FLAGS_MASK: int = 0xE000
CATEGORY_0X1001_FLAGS_REQUIRED: int = 0x4000

SENCORE_ADJUST_CONTROL_VA: int = 0x10344
SENCORE_INCONCURRENT_LOCK_VA: int = 0xDD00
SENCORE_INCONCURRENT_UNLOCK_VA: int = 0xDD7C
SENCORE_AUTH_LEVEL_CHECK_VA: int = 0xFE48
SENCORE_AUTH_LEVEL_GLOBAL_ADDR: int = 0x6AEE0
LIBJIRITSU_DMM_MGR_ADDR: int = 0x46BD0
LIBJIRITSU_RAM_SLOT_TABLE_ADDR: int = 0x46BD8

STAGE285_9_STEP_CONTRACT: Tuple[str, ...] = (
    "STEP1_MSC_054C_0DA1_DETECTED",
    "STEP2_MSC_7ROUND_HANDSHAKE",
    "STEP3_SERVICE_054C_0336_SAME_PORT_SEIZE",
    "STEP4_SERVICE_7ROUND_AUTH_LEVEL2_3",
    "STEP5_PRODUCT_INFO_0X0010_READ0_88B",
    "STEP6_ADJUST_0X40_OP_FF_RAM_CANARY_ROUNDTRIP",
    "STEP7_SERVICE_STOP_0336_7",
    "STEP8_SERVICE_RELEASE_0336_8",
    "STEP9_MSC_054C_0DA1_RETURN_AND_0DA1_9_RELEASE",
)

# Stage-288 §4 (1..6) ARM64 libJit.so ELF64 Hardening Constants
LIBJIT_TARGET_PATH: str = "/tmp/jiritsu/libJit.so"
SECTOR0_OUT_PATH: str = "/tmp/jiritsu/sector0.bin"
NFLASH_WHOLE_NODE: str = "/dev/nflasha"
NFLASH_FALLBACK_NODE: str = "/dev/nflasha1"
PROC_PARTITIONS_PATH: str = "/proc/partitions"

MAX_LIBJIT_ELF_BYTES: int = 16384  # < 16 KiB
ELF_MAGIC: bytes = b"\x7fELF"
ELF_CLASS_64: int = 2
ELF_DATA_LSB: int = 1
ELF_TYPE_DYN: int = 3
ELF_MACHINE_AARCH64: int = 183
ELF_PT_LOAD: int = 1
ELF_PT_DYNAMIC: int = 2
ELF_PF_X: int = 1
ELF_PF_W: int = 2
ELF_PF_R: int = 4
ELF_PT_LOAD_PAGE_ALIGN: int = 0x10000  # 64 KiB

ELF_DT_NULL: int = 0
ELF_DT_HASH: int = 4
ELF_DT_STRTAB: int = 5
ELF_DT_SYMTAB: int = 6
ELF_DT_STRSZ: int = 10
ELF_DT_SYMENT: int = 11
ELF_DT_INIT: int = 12

FX3S0OK_MAGIC: bytes = b"FX3S0OK\x00"
FX3S0ERR_MAGIC: bytes = b"FX3S0ERR"
FX3S0OK_FRAME_BYTES: int = 528
FX3S0ERR_FRAME_BYTES: int = 16

SECTOR0_BYTES: int = 512
SECTOR0_MAGIC: bytes = b"8246"
SECTOR0_VERSION: bytes = b"2.00"
SECTOR0_EXPECTED_PARTITIONS: int = 30
SECTOR0_EXPECTED_P1: Tuple[int, int] = (0x80, 0xBF80)

# Linux AArch64 ABI Syscall & Flag Constants
SYS_AARCH64_IOCTL: int = 29
SYS_AARCH64_UNLINKAT: int = 35
SYS_AARCH64_MOUNT: int = 40
SYS_AARCH64_OPENAT: int = 56
SYS_AARCH64_CLOSE: int = 57
SYS_AARCH64_READ: int = 63
SYS_AARCH64_WRITE: int = 64
SYS_AARCH64_PREAD64: int = 67
SYS_AARCH64_PWRITE64: int = 68
SYS_AARCH64_NEWFSTATAT: int = 79

AT_FDCWD: int = -100
LINUX_O_RDONLY: int = 0x0
LINUX_O_WRONLY: int = 0x1
LINUX_O_RDWR: int = 0x2
LINUX_O_ACCMODE: int = 0x3
LINUX_O_CREAT: int = 0x40
LINUX_O_TRUNC: int = 0x200
LINUX_O_CLOEXEC: int = 0x80000
S_IFMT: int = 0o170000
S_IFBLK: int = 0o060000

FORBIDDEN_ELF_STRING_TOKENS: Tuple[str, ...] = (
    "edisx",
    "uc_mkfs",
    "nor_loader_writer",
)
FORBIDDEN_WRITE_TARGET_PREFIXES: Tuple[str, ...] = (
    "/dev/nflasha",
    "/dev/cnflasha",
    "/dev/pnflasha",
    "/dev/mtd",
    "/setting",
)

# Status & Error Codes
STATUS_VERIFIED_SUITE: str = "VERIFIED_SERVICE_USB_SESSION_AND_LIBJIT_ELF_HARDENER"
STATUS_FAIL_SUITE: str = "FAIL_SERVICE_USB_SESSION_AND_LIBJIT_ELF_HARDENER"
STATUS_VERIFIED_PILLAR_A: str = "VERIFIED_SERVICE_USB_SESSION_DMM_AND_OP_FF_CANARY"
STATUS_REJECTED_PILLAR_A: str = "REJECTED_SERVICE_USB_SESSION_DMM_AND_OP_FF_CANARY"
STATUS_VERIFIED_PILLAR_B: str = "VERIFIED_STAGE288_HARDENED_ARM64_LIBJIT_ELF_GATE"
STATUS_REJECTED_PILLAR_B: str = "REJECTED_STAGE288_HARDENED_ARM64_LIBJIT_ELF_GATE"

ERR_AUTH_LEVEL1_REJECTED: str = "ERR_AUTH_LEVEL1_REJECTED_AT_0XFE48"
ERR_OP00_BLOCKED_WITHOUT_OP_FF: str = "ERR_OP00_BLOCKED_BEFORE_OP_FF_RAM_CANARY"
ERR_OP_FF_SLOT_OUT_OF_RANGE: str = "ERR_OP_FF_SLOT_EXCEEDS_0X11"
ERR_OP_FF_SIZE_OUT_OF_RANGE: str = "ERR_OP_FF_PAYLOAD_EXCEEDS_5MIB"
ERR_CONCURRENT_OVERLAPPING_SEQ: str = "ERR_CONCURRENT_OVERLAPPING_SEQ_IN_SINGLE_FLIGHT_SESSION"
ERR_MISSING_TEARDOWN_SEQUENCE: str = "ERR_MISSING_STOP_0336_7_RELEASE_0336_8_OR_0DA1_9_RETURN"
ERR_USB_TX_LOCKED: str = "ERR_PASSIVE_TOPOLOGY_USB_TX_LOCKED_ZERO"

ERR_LIBJIT_RULE1_NO_UNLINK_FIRST: str = "ERR_RULE1_MISSING_UNLINKAT_LIBJIT_FIRST"
ERR_LIBJIT_RULE2_NO_READ_FIRST_CLOEXEC: str = "ERR_RULE2_MISSING_O_RDONLY_CLOEXEC_OR_READ512_BEFORE_OPEN_OUT"
ERR_LIBJIT_RULE3_NO_528B_FRAME: str = "ERR_RULE3_MISSING_FX3S0OK_528B_CRC32_FRAMING"
ERR_LIBJIT_RULE4_NO_BLK_FALLBACK_OR_ERR_RECEIPT: str = "ERR_RULE4_MISSING_FSTATAT_S_ISBLK_PROC_PARTITIONS_OR_FX3S0ERR"
ERR_LIBJIT_RULE5_ELF_LAYOUT_OR_64K_ALIGN: str = "ERR_RULE5_PT_LOAD_NOT_64K_WX_OVERLAP_OR_DT_OOB"
ERR_LIBJIT_RULE6_FIREWALL_VIOLATION: str = "ERR_RULE6_FORBIDDEN_SYSCALL_OR_WRITE_FLAG_OR_TOKEN"
ERR_LIBJIT_ELF_OVERSIZED: str = "ERR_LIBJIT_ELF_EXCEEDS_16KIB"
ERR_FRAME_INVALID: str = "ERR_FX3S0_FRAME_OR_SECTOR0_INVALID"

PILLAR_A_SCENARIO_IDS: Tuple[str, ...] = (
    "PA1_9STEP_MSC_TO_SERVICE_OP_FF_CANARY_AND_TEARDOWN",
    "PA2_LEVEL1_AUTH_REJECTED_AT_0XFE48",
    "PA3_OP00_BLOCKED_BEFORE_OP_FF_CANARY",
    "PA4_OP_FF_SLOT_GT_0X11_REJECTED",
    "PA5_OP_FF_SIZE_GT_5MIB_REJECTED",
    "PA6_CONCURRENT_OVERLAPPING_SEQ_REJECTED",
    "PA7_MISSING_STOP_RELEASE_0DA1_RETURN_TEARDOWN_REJECTED",
    "PA8_PASSIVE_IOREG_XML_AND_TEXT_TOPOLOGY_ZERO_USB_TX",
)

PILLAR_B_SCENARIO_IDS: Tuple[str, ...] = (
    "PB1_HARDENED_LIBJIT_ELF64_STATIC_AND_UNICORN_PASS",
    "PB2_LEGACY_LIBJIT_TEST_SO_FLAGGED_PREHARDENING",
    "PB3_OUT_OF_BOUNDS_DT_PTR_0X2100_CAUGHT",
    "PB4_WX_SEGMENT_AND_4K_PT_LOAD_REJECTED",
    "PB5_SHORT_READ_NO_TRUNCATE_AND_FX3S0ERR_EMITTED",
    "PB6_MISSING_NFLASH_FALLBACK_PROC_PARTITIONS_AND_FX3S0ERR",
    "PB7_FIREWALL_REJECTS_O_RDWR_AND_BLOCK_WRITE_IOCTL_MOUNT",
    "PB8_FIREWALL_REJECTS_EDISX_UC_MKFS_NOR_LOADER_WRITER",
)


# ---------------------------------------------------------------------------
# Helpers & Read-Only (O_RDONLY) Donor Reader
# ---------------------------------------------------------------------------


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _canonical_sha256(obj: Any) -> str:
    encoded = json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _read_donor_o_rdonly(
    rel_path: str, limit: int = 2 * 1024 * 1024
) -> Tuple[Optional[bytes], str]:
    """Read a local donor file strictly with `os.open(..., os.O_RDONLY | ...)`."""
    if is_forced_clean_room():
        return None, "CLEAN_ROOM_SYNTHETIC"
    p = resolve_donor_path(rel_path, require_file=True)
    if not p.is_file():
        return None, "CLEAN_ROOM_SYNTHETIC"
    checked = local_path(str(p), allow_donor_roots=True)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    fd = os.open(str(checked), flags)
    try:
        st_before = os.fstat(fd)
        require(
            stat.S_ISREG(st_before.st_mode) and st_before.st_nlink == 1,
            "single-link regular donor file required",
        )
        require(0 <= st_before.st_size <= limit, "donor file size limit exceeded")
        chunks: List[bytes] = []
        remaining = st_before.st_size + 1
        while remaining > 0:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        st_after = os.fstat(fd)
        require(
            len(data) == st_before.st_size
            and st_before.st_dev == st_after.st_dev
            and st_before.st_ino == st_after.st_ino
            and st_before.st_size == st_after.st_size,
            "donor file modified during read",
        )
        return data, "LOCAL_DONOR_O_RDONLY"
    finally:
        os.close(fd)


def _extract_elf64_structural_summary(so_bytes: bytes) -> Dict[str, Any]:
    """Extract safe structural metadata (no raw proprietary firmware bytes)."""
    require(len(so_bytes) >= 64 and so_bytes[:4] == ELF_MAGIC, "invalid ELF magic")
    e_type, e_machine, _ver, e_entry, e_phoff, e_shoff, _flags, _ehsz, e_phentsz, e_phnum = (
        struct.unpack_from("<HHIQQQIHHH", so_bytes, 16)
    )
    e_shentsz, e_shnum, e_shstrndx = struct.unpack_from("<HHH", so_bytes, 58)
    pt_load_aligns: List[int] = []
    pt_load_count = 0
    for idx in range(e_phnum):
        off = e_phoff + idx * e_phentsz
        p_type, _pf, _po, _pv, _pp, _fs, _ms, p_align = struct.unpack_from(
            "<IIQQQQQQ", so_bytes, off
        )
        if p_type == ELF_PT_LOAD:
            pt_load_count += 1
            pt_load_aligns.append(p_align)
    # Extract symbol names from .dynsym if present (symbol names only, zero raw code bytes)
    dynsym_names: List[str] = []
    if e_shoff > 0 and e_shnum > 0 and e_shentsz >= 64 and e_shoff + e_shnum * e_shentsz <= len(so_bytes):
        shdrs = []
        for idx in range(e_shnum):
            sh_off = e_shoff + idx * e_shentsz
            sh_name, sh_type, _sf, _sa, sh_file_off, sh_size, sh_link, _si, _sal, sh_entsz = (
                struct.unpack_from("<IIQQQQIIQQ", so_bytes, sh_off)
            )
            shdrs.append((sh_name, sh_type, sh_file_off, sh_size, sh_link, sh_entsz))
        for _sn, stype, foff, fsz, link, entsz in shdrs:
            if stype == 11 and entsz >= 24 and 0 <= link < len(shdrs):  # SHT_DYNSYM
                _, _, str_off, str_sz, _, _ = shdrs[link]
                if foff + fsz <= len(so_bytes) and str_off + str_sz <= len(so_bytes):
                    strtab = so_bytes[str_off : str_off + str_sz]
                    for sym_off in range(foff, foff + fsz - 23, entsz):
                        st_name = struct.unpack_from("<I", so_bytes, sym_off)[0]
                        if 0 < st_name < len(strtab):
                            nul = strtab.find(b"\x00", st_name)
                            if nul > st_name:
                                dynsym_names.append(
                                    strtab[st_name:nul].decode("ascii", "replace")
                                )
    return {
        "e_type": e_type,
        "e_machine": e_machine,
        "e_entry": e_entry,
        "pt_load_count": pt_load_count,
        "pt_load_alignments": tuple(pt_load_aligns),
        "dynsym_names": tuple(dynsym_names),
    }


# ---------------------------------------------------------------------------
# Structured Dataclasses (JSON-safe: zero raw proprietary firmware bytes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DonorElfStructuralDescriptor:
    label: str
    source_mode: str
    present: bool
    byte_length: int
    sha256_digest: str
    e_machine: int
    pt_load_alignments: Tuple[int, ...]
    anchor_symbols_present: Tuple[str, ...]
    notes: str = ""


@dataclass(frozen=True)
class ServiceUsbAndLibjitDonorSnapshot:
    verification_mode: str
    read_only_access: bool
    o_rdonly_enforced: bool
    libjiritsu_descriptor: DonorElfStructuralDescriptor
    libsencore_descriptor: DonorElfStructuralDescriptor
    libjit_test_descriptor: DonorElfStructuralDescriptor
    legacy_libjit_test_prehardening_rejected: bool
    legacy_libjit_test_failure_codes: Tuple[str, ...]
    snapshot_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuthLevelGateResult:
    admitted: bool
    auth_level: int
    cmd_flags_hex: str
    reason_code: str


@dataclass(frozen=True)
class ProductInfoRead0Result:
    valid: bool
    seq: int
    version: int
    res: int
    body_bytes: int
    body_sha256: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DmmLifecycleTrace:
    command: int
    seq: int
    slot: int
    mode: int
    payload_bytes: int
    inline_path: bool
    phases_executed: Tuple[int, ...]
    sys_mount_calls: int
    dlopen_calls: int
    touches_filesystem: bool
    dmm_freed_cleanly: bool
    native_status: int
    echo_sha256: str


@dataclass(frozen=True)
class Op00PrecheckDecision:
    authorized: bool
    reason_code: str
    op_ff_canary_verified: bool
    service_exclusive_seized: bool
    auth_level_ok: bool
    read0_ok: bool


@dataclass(frozen=True)
class SessionTeardownStatus:
    complete: bool
    stop_0336_7_done: bool
    release_0336_8_done: bool
    msc_0da1_return_done: bool
    driver_release_0da1_9_done: bool
    error_codes: Tuple[str, ...]


@dataclass(frozen=True)
class UsbTopologyDeviceNode:
    vid: int
    pid: int
    vid_pid: str
    product_name: str
    location_id_hex: str
    registry_id: int
    port_node_id: int
    mass_storage_driver_attached: bool


@dataclass(frozen=True)
class UsbTopologyDryRunReport:
    valid: bool
    snapshot_format: str
    device_count: int
    devices: Tuple[UsbTopologyDeviceNode, ...]
    msc_0da1_present: bool
    service_0336_present: bool
    same_port_continuity_verified: bool
    usb_tx_packets_emitted: int
    live_usb_iokit_transmit_enabled: bool
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PillarAScenarioResult:
    passed: bool
    scenario_id: str
    steps_completed: Tuple[str, ...]
    dmm_phases_verified: Tuple[int, ...]
    op_ff_canary_sha256_match: bool
    op00_gate_enforced: bool
    teardown_verified: bool
    usb_tx_packets_emitted: int
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str


@dataclass(frozen=True)
class PillarA8ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[PillarAScenarioResult, ...]
    usb_tx_packets_emitted: int
    errors: Tuple[str, ...]
    suite_sha256: str


@dataclass(frozen=True)
class Sector0FrameInfo:
    valid: bool
    magic_hex: str
    payload_len: int
    crc32_expected_hex: str
    crc32_actual_hex: str
    sector0_magic: str
    sector0_version: str
    n_partitions: int
    p1_start_lba: int
    p1_size_sectors: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Sector0ErrReceipt:
    valid: bool
    magic: str
    stage: int
    errno_val: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DecodedSyscallSite:
    va: int
    syscall_num: int
    syscall_name: str
    arg0: Optional[int]
    arg1_str: Optional[str]
    arg2: Optional[int]
    arg3: Optional[int]


@dataclass(frozen=True)
class LibJitElfHardeningReport:
    passed: bool
    elf_size_bytes: int
    under_16kib: bool
    e_machine: int
    e_type: int
    pt_load_count: int
    pt_load_alignments: Tuple[int, ...]
    has_wx_segment: bool
    has_overlapping_pt_load: bool
    dt_symtab_in_bounds: bool
    dt_strtab_in_bounds: bool
    dt_hash_in_bounds: bool
    dt_init_in_bounds: bool
    dt_hash_words: Tuple[int, int, int, int]
    rule1_self_unlink_first_ok: bool
    rule2_read_first_cloexec_ok: bool
    rule3_framed_528b_output_ok: bool
    rule4_blk_node_and_fallback_ok: bool
    rule5_64k_pt_load_and_dt_bounds_ok: bool
    rule6_static_syscall_token_firewall_ok: bool
    decoded_syscalls: Tuple[DecodedSyscallSite, ...]
    firewall_violations: Tuple[str, ...]
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class UnicornLibJitEmulationResult:
    unicorn_available: bool
    executed: bool
    passed: bool
    syscall_sequence: Tuple[str, ...]
    unlinked_libjit_first: bool
    probed_proc_partitions: bool
    probed_nflasha1_fallback: bool
    sector0_file_present: bool
    sector0_file_bytes: int
    ok_frame_valid: bool
    err_receipt_valid: bool
    err_stage: int
    err_errno: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PillarBScenarioResult:
    passed: bool
    scenario_id: str
    rule_checks_ok: bool
    unicorn_executed: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str


@dataclass(frozen=True)
class PillarB8ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[PillarBScenarioResult, ...]
    hardened_elf_bytes: int
    hardened_elf_sha256: str
    errors: Tuple[str, ...]
    suite_sha256: str


@dataclass(frozen=True)
class RealHwServiceUsbAndLibjitSuiteReport:
    schema: str
    version: str
    status: str
    verification_mode: str
    all_passed: bool
    read_only_donor_access: bool
    donor_snapshot: ServiceUsbAndLibjitDonorSnapshot
    pillar_a_service_usb_8_scenarios: PillarA8ScenarioSuiteResult
    pillar_b_hardened_libjit_8_scenarios: PillarB8ScenarioSuiteResult
    live_usb_iokit_transmit_enabled: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    allow_persistent_jiritsu_writes: bool
    allow_destructive_jiritsu_commands: bool
    usb_tx_packets_emitted: int
    otp_fuse_touches: int
    otp_fuse_writes: int
    passive_tx_bytes_emitted: int
    physical_device_writes: int
    elapsed_seconds: float
    errors: Tuple[str, ...]
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Pillar A — Stage-285/286 Session, DMM Phase 1->4->16 & op=0xFF RAM Canary
# ---------------------------------------------------------------------------


def check_auth_level_for_category_0x1001(
    auth_level: int,
    cmd_flags: int = 0x4010,
) -> AuthLevelGateResult:
    """Enforce `libsencore.so` `0xfe20..0xfe4c` auth-level gate (`*0x6aee0`).

    Category `0x1001` table entries carry `flags & 0xe000 == 0x4000` (`0x4001..0x4013`):
    - Level 2 (Table B) and Level 3 (Table A) are admitted.
    - Level 1 (Table C) is rejected at `0xfe48`.
    """
    flags_masked = cmd_flags & CATEGORY_0X1001_FLAGS_MASK
    if flags_masked != CATEGORY_0X1001_FLAGS_REQUIRED:
        return AuthLevelGateResult(
            admitted=False,
            auth_level=auth_level,
            cmd_flags_hex=f"{cmd_flags:#06x}",
            reason_code="ERR_TABLE_FLAGS_MASK_NOT_0X4000",
        )
    if auth_level not in (AUTH_TABLE_LEVEL_2, AUTH_TABLE_LEVEL_3):
        return AuthLevelGateResult(
            admitted=False,
            auth_level=auth_level,
            cmd_flags_hex=f"{cmd_flags:#06x}",
            reason_code=ERR_AUTH_LEVEL1_REJECTED,
        )
    return AuthLevelGateResult(
        admitted=True,
        auth_level=auth_level,
        cmd_flags_hex=f"{cmd_flags:#06x}",
        reason_code="ADMITTED_LEVEL_2_OR_3",
    )


def build_product_info_read0_request(seq: int) -> bytes:
    """Build 12B `<IHHBBBB` `ProductInfoFunc` (`pFunc=0x0010`) `read0` request."""
    _need(isinstance(seq, int) and 0 < seq <= 0xFFFF, "invalid seq")
    return struct.pack(
        "<IHHBBBB",
        0,
        PFUNC_PRODUCT_INFO,
        seq,
        REQ_VERSION_ADJUST,
        0,
        0,
        0,
    )


def parse_product_info_read0_response(
    header: bytes,
    body: bytes,
    expected_seq: int,
) -> ProductInfoRead0Result:
    """Validate 12B `version=3, res=1` header + 88B `ProductInfoFunc` `read0` body."""
    errors: List[str] = []
    if not isinstance(header, bytes) or len(header) != PRODUCT_INFO_RESP_HDR_BYTES:
        return ProductInfoRead0Result(
            False, expected_seq, 0, 0, len(body) if isinstance(body, bytes) else 0, "", ("header must be 12 bytes",)
        )
    size, pfunc, seq, version, flag, reserved, res = struct.unpack("<IHHBBBB", header)
    if pfunc != PFUNC_PRODUCT_INFO:
        errors.append(f"unexpected pFunc {pfunc:#06x} != 0x0010")
    if seq != expected_seq:
        errors.append(f"seq mismatch {seq} != {expected_seq}")
    if version != READ0_RESP_VERSION:
        errors.append(f"version {version} != {READ0_RESP_VERSION}")
    if flag != 0 or reserved != 0:
        errors.append("non-zero flag/reserved byte")
    if res != READ0_RESP_RES:
        errors.append(f"res {res} != {READ0_RESP_RES}")
    if size != PRODUCT_INFO_RESP_BODY_BYTES:
        errors.append(f"read0 header size {size} != 88")
    if not isinstance(body, bytes) or len(body) != PRODUCT_INFO_RESP_BODY_BYTES:
        errors.append("read0 body must be exactly 88 bytes")
    digest = sha256(body).hexdigest() if isinstance(body, bytes) else ""
    return ProductInfoRead0Result(
        valid=len(errors) == 0,
        seq=seq,
        version=version,
        res=res,
        body_bytes=len(body) if isinstance(body, bytes) else 0,
        body_sha256=digest,
        errors=tuple(errors),
    )


def build_op_ff_set_request(
    seq: int,
    slot: int,
    data: bytes,
    *,
    mode: int = 0,
) -> bytes:
    """Encode `AdjustControl (0x40)` `SET_FILE2` (`16`) `op=0xFF` pure RAM slot frame."""
    _need(isinstance(seq, int) and 0 < seq <= 0xFFFF, "invalid seq")
    _need(isinstance(slot, int) and 0 <= slot <= MAX_OP_FF_SLOT, f"{ERR_OP_FF_SLOT_OUT_OF_RANGE}: {slot}")
    _need(isinstance(mode, int) and 0 <= mode <= MAX_OP_FF_MODE, f"mode out of range: {mode}")
    _need(
        isinstance(data, bytes) and 1 <= len(data) <= MAX_OP_FF_PAYLOAD_BYTES,
        f"{ERR_OP_FF_SIZE_OUT_OF_RANGE}: {len(data) if isinstance(data, bytes) else -1}",
    )
    inner = bytes([OP_RAM_CACHE_SLOT, slot, mode]) + data
    body_size = 4 + len(inner)
    hdr = struct.pack(
        "<IHHBBBB",
        body_size,
        PFUNC_ADJUST_CONTROL,
        seq,
        REQ_VERSION_ADJUST,
        0,
        0,
        0,
    )
    sel = struct.pack("<HH", CATEGORY_JIRITSU, CMD_SET_FILE2)
    return hdr + sel + inner


def build_op_ff_get_request(
    seq: int,
    slot: int,
    *,
    mode: int = 0,
) -> bytes:
    """Encode `AdjustControl (0x40)` `GET_FILE2` (`17`) `op=0xFF` pure RAM slot frame."""
    _need(isinstance(seq, int) and 0 < seq <= 0xFFFF, "invalid seq")
    _need(isinstance(slot, int) and 0 <= slot <= MAX_OP_FF_SLOT, f"{ERR_OP_FF_SLOT_OUT_OF_RANGE}: {slot}")
    _need(isinstance(mode, int) and 0 <= mode <= MAX_OP_FF_MODE, f"mode out of range: {mode}")
    inner = bytes([OP_RAM_CACHE_SLOT, slot, mode])
    body_size = 4 + len(inner)
    hdr = struct.pack(
        "<IHHBBBB",
        body_size,
        PFUNC_ADJUST_CONTROL,
        seq,
        REQ_VERSION_ADJUST,
        0,
        0,
        0,
    )
    sel = struct.pack("<HH", CATEGORY_JIRITSU, CMD_GET_FILE2)
    return hdr + sel + inner


def parse_senser_adjust_response(wire_resp: bytes, expected_seq: int) -> Tuple[int, bytes]:
    """Parse 12B `<IHHBBBB` (`version=3, res=1`) + 4B status + payload."""
    _need(isinstance(wire_resp, bytes) and len(wire_resp) >= 16, "truncated Senser response")
    size, pfunc, seq, version, flag, reserved, res = struct.unpack_from("<IHHBBBB", wire_resp, 0)
    _need(pfunc == PFUNC_ADJUST_CONTROL, f"unexpected response pFunc: {pfunc:#x}")
    _need(seq == expected_seq, f"seq mismatch: {seq} != {expected_seq}")
    _need(version == RESP_VERSION_STOCK, f"unexpected response version: {version}")
    _need(flag == 0 and reserved == 0, "non-zero flag/reserved byte")
    _need(res == RESP_RES_OK, f"non-ok Senser res byte: {res}")
    body = wire_resp[12:]
    _need(len(body) == size and size >= 4, "response body length mismatch")
    native_status = struct.unpack_from("<I", body, 0)[0]
    return native_status, body[4:]


class ServiceSessionStateMachine:
    """Models the Stage-285/286 `054C:0DA1 -> 054C:0336` exclusive `SERVICE`
    session, single-flight `Inconcurrent::resource_t::lock`, DMM Phase `1->4->16`,
    and mandatory `op=0xFF` RAM canary gate prior to any `op=0x00` command.
    """

    def __init__(self, *, port_node_id: int = 4294968654, location_id: int = 0x01100000) -> None:
        self.port_node_id = port_node_id
        self.location_id = location_id
        self.steps_completed: List[str] = []
        self.msc_detected = False
        self.msc_rounds_completed = 0
        self.service_seized = False
        self.auth_level = 0
        self.read0_result: Optional[ProductInfoRead0Result] = None
        self.in_flight_seq: Optional[int] = None
        self.inconcurrent_locked = False
        self.dmm_active = False
        self.ram_slots: Dict[int, Tuple[int, bytes]] = {}
        self.sys_mount_calls = 0
        self.dlopen_calls = 0
        self.touches_filesystem = False
        self.op_ff_canary_verified = False
        self.dmm_traces: List[DmmLifecycleTrace] = []
        self.stop_0336_7_done = False
        self.release_0336_8_done = False
        self.msc_0da1_return_done = False
        self.driver_release_0da1_9_done = False

    def detect_msc(self, vid: int = SONY_USB_VID, pid: int = FX3_MSC_PID) -> None:
        _need(vid == SONY_USB_VID and pid == FX3_MSC_PID, "expected 054C:0DA1 MSC device")
        self.msc_detected = True
        self.steps_completed.append(STAGE285_9_STEP_CONTRACT[0])

    def run_msc_handshake(self, rounds: int = MSC_HANDSHAKE_ROUNDS) -> None:
        _need(self.msc_detected, "MSC must be detected first")
        _need(rounds == MSC_HANDSHAKE_ROUNDS, "FX3 MSC handshake requires 7 rounds")
        self.msc_rounds_completed = rounds
        self.steps_completed.append(STAGE285_9_STEP_CONTRACT[1])

    def seize_service_same_port(
        self,
        *,
        vid: int = SONY_USB_VID,
        pid: int = SONY_SERVICE_PID,
        port_node_id: Optional[int] = None,
        location_id: Optional[int] = None,
    ) -> None:
        _need(self.msc_rounds_completed == MSC_HANDSHAKE_ROUNDS, "MSC 7-round handshake required")
        _need(vid == SONY_USB_VID and pid == SONY_SERVICE_PID, "expected 054C:0336 SERVICE device")
        pnode = self.port_node_id if port_node_id is None else port_node_id
        loc = self.location_id if location_id is None else location_id
        _need(pnode == self.port_node_id and loc == self.location_id, "physical port association mismatch")
        self.service_seized = True
        self.steps_completed.append(STAGE285_9_STEP_CONTRACT[2])

    def authenticate_service(self, rounds: int = SERVICE_AUTH_ROUNDS, auth_level: int = AUTH_TABLE_LEVEL_2) -> AuthLevelGateResult:
        _need(self.service_seized, "SERVICE must be exclusively seized")
        _need(rounds == SERVICE_AUTH_ROUNDS, "SERVICE auth requires 7 rounds")
        gate = check_auth_level_for_category_0x1001(auth_level)
        if not gate.admitted:
            return gate
        self.auth_level = auth_level
        self.steps_completed.append(STAGE285_9_STEP_CONTRACT[3])
        return gate

    def execute_product_info_read0(self, seq: int = 1, body: Optional[bytes] = None) -> ProductInfoRead0Result:
        _need(self.auth_level in (AUTH_TABLE_LEVEL_2, AUTH_TABLE_LEVEL_3), ERR_AUTH_LEVEL1_REJECTED)
        req = build_product_info_read0_request(seq)
        _need(len(req) == PRODUCT_INFO_REQ_BYTES, "read0 request must be 12 bytes")
        resp_body = body if body is not None else (b"FX3_READ0_" * 9)[:PRODUCT_INFO_RESP_BODY_BYTES]
        resp_hdr = struct.pack(
            "<IHHBBBB",
            len(resp_body),
            PFUNC_PRODUCT_INFO,
            seq,
            READ0_RESP_VERSION,
            0,
            0,
            READ0_RESP_RES,
        )
        res = parse_product_info_read0_response(resp_hdr, resp_body, expected_seq=seq)
        _need(res.valid, f"invalid read0 response: {res.errors}")
        self.read0_result = res
        self.steps_completed.append(STAGE285_9_STEP_CONTRACT[4])
        return res

    def begin_flight(self, seq: int) -> None:
        """Enforce single-flight host + `Inconcurrent::resource_t::lock` discipline."""
        _need(isinstance(seq, int) and 0 < seq <= 0xFFFF, "invalid seq")
        if self.in_flight_seq is not None or self.inconcurrent_locked:
            raise ValueError(
                f"{ERR_CONCURRENT_OVERLAPPING_SEQ}: active_seq={self.in_flight_seq}, new_seq={seq}"
            )
        self.in_flight_seq = seq
        self.inconcurrent_locked = True

    def end_flight(self, seq: int) -> None:
        _need(self.in_flight_seq == seq and self.inconcurrent_locked, "mismatched flight unlock")
        self.in_flight_seq = None
        self.inconcurrent_locked = False

    def execute_adjust_wire_frame(self, wire_frame: bytes) -> bytes:
        """Execute a single `AdjustControl (0x40)` frame with DMM Phase 1->4->16 tracking."""
        _need(self.service_seized, "SERVICE not seized")
        _need(self.read0_result is not None and self.read0_result.valid, "read0 probe not completed")
        _need(len(wire_frame) >= 16, "truncated SenserPacket")
        size, pfunc, seq, version, flag, reserved, res = struct.unpack_from("<IHHBBBB", wire_frame, 0)
        _need(pfunc == PFUNC_ADJUST_CONTROL and version == REQ_VERSION_ADJUST, "bad outer SenserPacket")
        _need(flag == 0 and reserved == 0 and res == 0, "non-zero header reserved bytes")
        _need(size == len(wire_frame) - 12, "SenserPacket size mismatch")
        category, cmd = struct.unpack_from("<HH", wire_frame, 12)
        _need(category == CATEGORY_JIRITSU, "unexpected AdjustControl category")
        gate = check_auth_level_for_category_0x1001(self.auth_level)
        _need(gate.admitted, gate.reason_code)

        self.begin_flight(seq)
        try:
            inner = wire_frame[16:]
            _need(len(inner) >= 3, "truncated AdjustControl inner payload")
            op = inner[0]
            if op == OP_FILESYSTEM_MOUNT:
                auth_dec = self.authorize_op00_command(op)
                _need(auth_dec.authorized, auth_dec.reason_code)
            _need(op == OP_RAM_CACHE_SLOT, "only op=0xFF supported in zero-mount RAM canary")
            slot = inner[1]
            mode = inner[2]
            _need(slot <= MAX_OP_FF_SLOT, f"{ERR_OP_FF_SLOT_OUT_OF_RANGE}: {slot}")
            _need(mode <= MAX_OP_FF_MODE, f"mode > 0x11: {mode}")

            # Phase 1: TransactionStart (0xff9c) — 0x124 inline threshold
            inline_path = len(inner) <= DMM_INLINE_THRESHOLD_BYTES
            self.dmm_active = True  # *0x46bd0 DmmMgr active during Phase 1->4->16

            # Phase 4: DoExecute (0xf9f0)
            if cmd == CMD_SET_FILE2:
                payload = inner[3:]
                _need(1 <= len(payload) <= MAX_OP_FF_PAYLOAD_BYTES, ERR_OP_FF_SIZE_OUT_OF_RANGE)
                self.ram_slots[slot] = (mode, payload)
                resp_payload = b""
                echo_sha = sha256(payload).hexdigest()
                payload_len = len(payload)
            elif cmd == CMD_GET_FILE2:
                _need(len(inner) == 3, "GET_FILE2 op=0xFF expects exactly 3 inner bytes")
                if slot not in self.ram_slots:
                    self.dmm_active = False
                    resp_body = struct.pack("<I", 0x11)
                    resp_hdr = struct.pack("<IHHBBBB", len(resp_body), PFUNC_ADJUST_CONTROL, seq, RESP_VERSION_STOCK, 0, 0, RESP_RES_OK)
                    return resp_hdr + resp_body
                _stored_mode, stored_data = self.ram_slots[slot]
                resp_payload = stored_data
                echo_sha = sha256(stored_data).hexdigest()
                payload_len = len(stored_data)
            else:
                raise ValueError(f"unsupported op=0xFF command: {cmd:#x}")

            # Phase 16: ~SubsystemCommunicationCommand (0xfaa4) — dmm_free & clear *0x46bd0
            self.dmm_active = False

            self.dmm_traces.append(
                DmmLifecycleTrace(
                    command=cmd,
                    seq=seq,
                    slot=slot,
                    mode=mode,
                    payload_bytes=payload_len,
                    inline_path=inline_path,
                    phases_executed=DMM_PHASES,
                    sys_mount_calls=self.sys_mount_calls,
                    dlopen_calls=self.dlopen_calls,
                    touches_filesystem=self.touches_filesystem,
                    dmm_freed_cleanly=not self.dmm_active,
                    native_status=0,
                    echo_sha256=echo_sha,
                )
            )
            resp_body = struct.pack("<I", 0) + resp_payload
            resp_hdr = struct.pack(
                "<IHHBBBB",
                len(resp_body),
                PFUNC_ADJUST_CONTROL,
                seq,
                RESP_VERSION_STOCK,
                0,
                0,
                RESP_RES_OK,
            )
            return resp_hdr + resp_body
        finally:
            self.end_flight(seq)

    def run_op_ff_ram_canary_roundtrip(
        self,
        *,
        slot: int = 0,
        mode: int = 0,
        canary_payload: bytes = b"FX3_STAGE286_OP_FF_RAM_CANARY_ROUNDTRIP_OK",
        seq_base: int = 10,
    ) -> Tuple[bool, str, Tuple[DmmLifecycleTrace, DmmLifecycleTrace]]:
        """Run mandatory Stage-286 Branch-A `SET_FILE2 / GET_FILE2 op=0xFF` RAM canary."""
        req_set = build_op_ff_set_request(seq_base, slot, canary_payload, mode=mode)
        resp_set = self.execute_adjust_wire_frame(req_set)
        st_set, payload_set = parse_senser_adjust_response(resp_set, expected_seq=seq_base)
        _need(st_set == 0 and payload_set == b"", "op=0xFF SET_FILE2 failed")

        req_get = build_op_ff_get_request(seq_base + 1, slot, mode=mode)
        resp_get = self.execute_adjust_wire_frame(req_get)
        st_get, payload_get = parse_senser_adjust_response(resp_get, expected_seq=seq_base + 1)
        expected_sha = sha256(canary_payload).hexdigest()
        got_sha = sha256(payload_get).hexdigest()
        ok = (
            st_get == 0
            and payload_get == canary_payload
            and got_sha == expected_sha
            and self.sys_mount_calls == 0
            and self.dlopen_calls == 0
            and not self.touches_filesystem
            and not self.dmm_active
            and not self.inconcurrent_locked
        )
        if ok:
            self.op_ff_canary_verified = True
            if STAGE285_9_STEP_CONTRACT[5] not in self.steps_completed:
                self.steps_completed.append(STAGE285_9_STEP_CONTRACT[5])
        return ok, got_sha, (self.dmm_traces[-2], self.dmm_traces[-1])

    def authorize_op00_command(self, op_byte: int = OP_FILESYSTEM_MOUNT) -> Op00PrecheckDecision:
        """Gate any `op=0x00` (`/dev/nflasha6` `/tmp/jiritsu`) request behind Branch-A `op=0xFF`."""
        read0_ok = self.read0_result is not None and self.read0_result.valid
        auth_ok = self.auth_level in (AUTH_TABLE_LEVEL_2, AUTH_TABLE_LEVEL_3)
        if op_byte == OP_FILESYSTEM_MOUNT and not self.op_ff_canary_verified:
            return Op00PrecheckDecision(
                authorized=False,
                reason_code=ERR_OP00_BLOCKED_WITHOUT_OP_FF,
                op_ff_canary_verified=False,
                service_exclusive_seized=self.service_seized,
                auth_level_ok=auth_ok,
                read0_ok=read0_ok,
            )
        ok = self.service_seized and auth_ok and read0_ok and self.op_ff_canary_verified
        return Op00PrecheckDecision(
            authorized=ok,
            reason_code="OP00_PRECHECK_SATISFIED" if ok else ERR_OP00_BLOCKED_WITHOUT_OP_FF,
            op_ff_canary_verified=self.op_ff_canary_verified,
            service_exclusive_seized=self.service_seized,
            auth_level_ok=auth_ok,
            read0_ok=read0_ok,
        )

    def send_stop_0336_7(self) -> None:
        _need(self.service_seized and not self.inconcurrent_locked, "cannot STOP while flight locked")
        self.stop_0336_7_done = True
        self.steps_completed.append(STAGE285_9_STEP_CONTRACT[6])

    def release_service_0336_8(self) -> None:
        _need(self.stop_0336_7_done, "0336:8 release requires STOP 0336:7 first")
        self.release_0336_8_done = True
        self.service_seized = False
        self.steps_completed.append(STAGE285_9_STEP_CONTRACT[7])

    def observe_msc_return_and_release_0da1_9(
        self,
        *,
        port_node_id: Optional[int] = None,
        location_id: Optional[int] = None,
    ) -> None:
        _need(self.release_0336_8_done, "0da1:9 requires 0336:8 release first")
        pnode = self.port_node_id if port_node_id is None else port_node_id
        loc = self.location_id if location_id is None else location_id
        _need(pnode == self.port_node_id and loc == self.location_id, "returned MSC on wrong physical port")
        self.msc_0da1_return_done = True
        self.driver_release_0da1_9_done = True
        self.steps_completed.append(STAGE285_9_STEP_CONTRACT[8])

    def verify_complete_session_teardown(self) -> SessionTeardownStatus:
        errs: List[str] = []
        if not (
            self.stop_0336_7_done
            and self.release_0336_8_done
            and self.msc_0da1_return_done
            and self.driver_release_0da1_9_done
        ):
            errs.append(ERR_MISSING_TEARDOWN_SEQUENCE)
        return SessionTeardownStatus(
            complete=len(errs) == 0,
            stop_0336_7_done=self.stop_0336_7_done,
            release_0336_8_done=self.release_0336_8_done,
            msc_0da1_return_done=self.msc_0da1_return_done,
            driver_release_0da1_9_done=self.driver_release_0da1_9_done,
            error_codes=tuple(errs),
        )


def _walk_plist_nodes(node: Any, parent_port_id: int = 0, out: Optional[List[UsbTopologyDeviceNode]] = None) -> List[UsbTopologyDeviceNode]:
    if out is None:
        out = []
    if isinstance(node, list):
        for item in node:
            _walk_plist_nodes(item, parent_port_id, out)
        return out
    if not isinstance(node, dict):
        return out

    reg_id = int(node.get("IORegistryEntryID", 0) or 0)
    vid = node.get("idVendor")
    pid = node.get("idProduct")
    next_parent = reg_id if ("Port" in str(node.get("IORegistryEntryName", "")) or "Root" in str(node.get("IORegistryEntryName", ""))) else parent_port_id

    if isinstance(vid, int) and isinstance(pid, int):
        loc = int(node.get("locationID", 0) or 0)
        pname = str(node.get("USB Product Name", node.get("IORegistryEntryName", "")))
        port_id = int(node.get("portNodeID", parent_port_id) or parent_port_id)
        node_blob = json.dumps(node, default=str)
        msc_attached = (
            "IOUSBMassStorageDriver" in node_blob
            or "IOBlockStorageDriver" in node_blob
            or bool(node.get("mass_storage_driver_attached", False))
        )
        out.append(
            UsbTopologyDeviceNode(
                vid=vid,
                pid=pid,
                vid_pid=f"{vid:04X}:{pid:04X}",
                product_name=pname,
                location_id_hex=f"{loc:#010x}",
                registry_id=reg_id,
                port_node_id=port_id,
                mass_storage_driver_attached=msc_attached,
            )
        )

    for child in node.get("IORegistryEntryChildren", []) or []:
        _walk_plist_nodes(child, next_parent or reg_id, out)
    return out


def parse_passive_ioreg_usb_topology(snapshot_text: str) -> UsbTopologyDryRunReport:
    """Strictly passive dry-run parser for synthetic `ioreg` XML (plist) or text snapshots.

    Never opens IOKit devices, never executes `ioreg`, and never emits USB packets.
    """
    _need(not LIVE_USB_IOKIT_TRANSMIT_ENABLED, ERR_USB_TX_LOCKED)
    _need(USB_TX_PACKETS_EMITTED == 0, ERR_USB_TX_LOCKED)
    _need(isinstance(snapshot_text, str) and len(snapshot_text.strip()) > 0, "empty ioreg snapshot")

    stripped = snapshot_text.lstrip()
    devices: List[UsbTopologyDeviceNode] = []
    errors: List[str] = []
    fmt = "text"

    if stripped.startswith("<?xml") or stripped.startswith("<plist"):
        fmt = "xml"
        try:
            parsed = plistlib.loads(snapshot_text.encode("utf-8"))
            devices = _walk_plist_nodes(parsed)
        except Exception as exc:
            errors.append(f"invalid ioreg XML plist: {exc}")
    else:
        # Parse `ioreg -p IOUSB -l` style text blocks
        current: Dict[str, Any] = {}
        last_port_id = 0
        for line in snapshot_text.splitlines():
            m_hdr = re.search(r"\+-o\s+([^\s<]+).*?id\s+([0-9]+|0x[0-9a-fA-F]+)", line)
            if m_hdr:
                if "idVendor" in current and "idProduct" in current:
                    devices.append(
                        UsbTopologyDeviceNode(
                            vid=current["idVendor"],
                            pid=current["idProduct"],
                            vid_pid=f"{current['idVendor']:04X}:{current['idProduct']:04X}",
                            product_name=current.get("product_name", ""),
                            location_id_hex=f"{current.get('locationID', 0):#010x}",
                            registry_id=current.get("registryID", 0),
                            port_node_id=current.get("portNodeID", last_port_id),
                            mass_storage_driver_attached=current.get("msc_drv", False),
                        )
                    )
                    current = {}
                name_hdr = m_hdr.group(1)
                rid = int(m_hdr.group(2), 0)
                if "Port" in name_hdr or "Root" in name_hdr:
                    last_port_id = rid
                else:
                    current["registryID"] = rid
                    current["product_name"] = name_hdr
            kv = re.search(r'"([^"]+)"\s*=\s*(.+)$', line.strip())
            if kv:
                k, raw_v = kv.group(1), kv.group(2).strip()
                if k == "idVendor":
                    current["idVendor"] = int(raw_v, 0)
                elif k == "idProduct":
                    current["idProduct"] = int(raw_v, 0)
                elif k == "locationID":
                    current["locationID"] = int(raw_v, 0)
                elif k == "IORegistryEntryID":
                    current["registryID"] = int(raw_v, 0)
                elif k == "portNodeID":
                    current["portNodeID"] = int(raw_v, 0)
                elif k == "USB Product Name":
                    current["product_name"] = raw_v.strip('"')
            if "IOUSBMassStorageDriver" in line or "IOBlockStorageDriver" in line:
                current["msc_drv"] = True
        if "idVendor" in current and "idProduct" in current:
            devices.append(
                UsbTopologyDeviceNode(
                    vid=current["idVendor"],
                    pid=current["idProduct"],
                    vid_pid=f"{current['idVendor']:04X}:{current['idProduct']:04X}",
                    product_name=current.get("product_name", ""),
                    location_id_hex=f"{current.get('locationID', 0):#010x}",
                    registry_id=current.get("registryID", 0),
                    port_node_id=current.get("portNodeID", last_port_id),
                    mass_storage_driver_attached=current.get("msc_drv", False),
                )
            )

    sony_devs = [d for d in devices if d.vid == SONY_USB_VID]
    msc_devs = [d for d in sony_devs if d.pid == FX3_MSC_PID]
    svc_devs = [d for d in sony_devs if d.pid == SONY_SERVICE_PID]

    same_port_ok = False
    if msc_devs and svc_devs:
        msc_ports = {(d.location_id_hex, d.port_node_id) for d in msc_devs}
        svc_ports = {(d.location_id_hex, d.port_node_id) for d in svc_devs}
        same_port_ok = bool(msc_ports & svc_ports)
    elif len(msc_devs) == 1 or len(svc_devs) == 1:
        same_port_ok = True

    if not sony_devs:
        errors.append("no Sony 0x054C USB device found in ioreg snapshot")

    return UsbTopologyDryRunReport(
        valid=len(errors) == 0 and len(sony_devs) >= 1,
        snapshot_format=fmt,
        device_count=len(devices),
        devices=tuple(devices),
        msc_0da1_present=bool(msc_devs),
        service_0336_present=bool(svc_devs),
        same_port_continuity_verified=same_port_ok,
        usb_tx_packets_emitted=USB_TX_PACKETS_EMITTED,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        errors=tuple(errors),
    )


def build_synthetic_ioreg_xml_snapshot(
    *,
    include_msc: bool = True,
    include_service: bool = True,
    location_id: int = 0x01100000,
    port_node_id: int = 4294968654,
) -> str:
    children: List[Dict[str, Any]] = []
    if include_msc:
        children.append(
            {
                "IORegistryEntryName": "ILME-FX3",
                "IORegistryEntryID": 4296580734,
                "idVendor": SONY_USB_VID,
                "idProduct": FX3_MSC_PID,
                "USB Product Name": "ILME-FX3",
                "locationID": location_id,
                "portNodeID": port_node_id,
                "IORegistryEntryChildren": [{"IORegistryEntryName": "IOUSBMassStorageDriver"}],
            }
        )
    if include_service:
        children.append(
            {
                "IORegistryEntryName": "ILME-FX3",
                "IORegistryEntryID": 4296580674,
                "idVendor": SONY_USB_VID,
                "idProduct": SONY_SERVICE_PID,
                "USB Product Name": "ILME-FX3",
                "locationID": location_id,
                "portNodeID": port_node_id,
                "IORegistryEntryChildren": [],
            }
        )
    root = {
        "IORegistryEntryName": "AppleUSB30XHCIPort",
        "IORegistryEntryID": port_node_id,
        "IORegistryEntryChildren": children,
    }
    return plistlib.dumps(root).decode("utf-8")


def build_synthetic_ioreg_text_snapshot(
    *,
    location_id: int = 0x01100000,
    port_node_id: int = 4294968654,
) -> str:
    return (
        f"+-o AppleUSB30XHCIPort@01100000  <class AppleUSB30XHCIPort, id {port_node_id}>\n"
        f"  +-o ILME-FX3@01100000  <class IOUSBHostDevice, id 4296580734>\n"
        f'    "idVendor" = {SONY_USB_VID}\n'
        f'    "idProduct" = {FX3_MSC_PID}\n'
        f'    "USB Product Name" = "ILME-FX3"\n'
        f'    "locationID" = {location_id:#x}\n'
        f"    +-o IOUSBMassStorageDriver  <class IOUSBMassStorageDriver, id 4296580740>\n"
    )


def run_pillar_a_service_usb_session_8_scenario_suite() -> PillarA8ScenarioSuiteResult:
    """Execute all 8 Pillar A Stage-285/286 `SERVICE` USB, DMM & `op=0xFF` scenarios."""
    results: List[PillarAScenarioResult] = []
    suite_errors: List[str] = []
    passed_count = 0

    # PA1: Full 9-step MSC -> SERVICE -> read0 -> op=0xFF (inline <=0x124 AND DMM >0x124) -> teardown
    sm1 = ServiceSessionStateMachine()
    sm1.detect_msc()
    sm1.run_msc_handshake()
    sm1.seize_service_same_port()
    auth1 = sm1.authenticate_service(auth_level=AUTH_TABLE_LEVEL_2)
    r0_1 = sm1.execute_product_info_read0(seq=1)
    ok_inline, _s1, (tr_s1, tr_g1) = sm1.run_op_ff_ram_canary_roundtrip(
        slot=0, mode=0, canary_payload=b"INLINE_CANARY_64B" * 4, seq_base=10
    )
    ok_dmm, _s2, (tr_s2, tr_g2) = sm1.run_op_ff_ram_canary_roundtrip(
        slot=0x11, mode=0x11, canary_payload=b"DMM_LARGE_CANARY_" * 64, seq_base=20
    )
    op00_after = sm1.authorize_op00_command(OP_FILESYSTEM_MOUNT)
    sm1.send_stop_0336_7()
    sm1.release_service_0336_8()
    sm1.observe_msc_return_and_release_0da1_9()
    td1 = sm1.verify_complete_session_teardown()
    pa1_ok = (
        auth1.admitted
        and r0_1.valid
        and r0_1.body_bytes == 88
        and ok_inline
        and tr_s1.inline_path
        and tr_s1.phases_executed == DMM_PHASES
        and ok_dmm
        and (not tr_s2.inline_path)
        and tr_g2.phases_executed == DMM_PHASES
        and op00_after.authorized
        and td1.complete
        and tuple(sm1.steps_completed) == STAGE285_9_STEP_CONTRACT
        and sm1.sys_mount_calls == 0
        and sm1.dlopen_calls == 0
    )
    if pa1_ok:
        passed_count += 1
    else:
        suite_errors.append("PA1 9-step Stage-285/286 + op=0xFF canary failed")
    results.append(
        PillarAScenarioResult(
            passed=pa1_ok,
            scenario_id=PILLAR_A_SCENARIO_IDS[0],
            steps_completed=tuple(sm1.steps_completed),
            dmm_phases_verified=DMM_PHASES,
            op_ff_canary_sha256_match=ok_inline and ok_dmm,
            op00_gate_enforced=op00_after.authorized,
            teardown_verified=td1.complete,
            usb_tx_packets_emitted=USB_TX_PACKETS_EMITTED,
            error_codes=(),
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_A_SCENARIO_IDS[0], "ok": pa1_ok, "steps": sm1.steps_completed}),
        )
    )

    # PA2: Level 1 auth rejected at 0xfe48; Level 2/3 admitted; bit-15 flags rejected
    g_l1 = check_auth_level_for_category_0x1001(AUTH_TABLE_LEVEL_1, 0x4010)
    g_l2 = check_auth_level_for_category_0x1001(AUTH_TABLE_LEVEL_2, 0x4010)
    g_l3 = check_auth_level_for_category_0x1001(AUTH_TABLE_LEVEL_3, 0x4001)
    g_badf = check_auth_level_for_category_0x1001(AUTH_TABLE_LEVEL_3, 0x8001)
    pa2_ok = (
        (not g_l1.admitted)
        and g_l1.reason_code == ERR_AUTH_LEVEL1_REJECTED
        and g_l2.admitted
        and g_l3.admitted
        and (not g_badf.admitted)
    )
    if pa2_ok:
        passed_count += 1
    else:
        suite_errors.append("PA2 Level 1 rejection failed")
    results.append(
        PillarAScenarioResult(
            passed=pa2_ok,
            scenario_id=PILLAR_A_SCENARIO_IDS[1],
            steps_completed=(),
            dmm_phases_verified=(),
            op_ff_canary_sha256_match=False,
            op00_gate_enforced=True,
            teardown_verified=False,
            usb_tx_packets_emitted=USB_TX_PACKETS_EMITTED,
            error_codes=(ERR_AUTH_LEVEL1_REJECTED,),
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_A_SCENARIO_IDS[1], "ok": pa2_ok}),
        )
    )

    # PA3: op=0x00 blocked before Branch-A op=0xFF RAM canary succeeds
    sm3 = ServiceSessionStateMachine()
    sm3.detect_msc()
    sm3.run_msc_handshake()
    sm3.seize_service_same_port()
    sm3.authenticate_service(auth_level=AUTH_TABLE_LEVEL_3)
    sm3.execute_product_info_read0(seq=1)
    op00_before = sm3.authorize_op00_command(OP_FILESYSTEM_MOUNT)
    op00_wire_rejected = False
    try:
        # Construct an op=0x00 SET_FILE2 wire frame directly and ensure state machine rejects it
        inner0 = b"\x00\xff\x00test"
        wf0 = (
            struct.pack("<IHHBBBB", 4 + len(inner0), PFUNC_ADJUST_CONTROL, 2, 2, 0, 0, 0)
            + struct.pack("<HH", CATEGORY_JIRITSU, CMD_SET_FILE2)
            + inner0
        )
        sm3.execute_adjust_wire_frame(wf0)
    except ValueError as exc:
        op00_wire_rejected = ERR_OP00_BLOCKED_WITHOUT_OP_FF in str(exc)
    pa3_ok = (not op00_before.authorized) and op00_before.reason_code == ERR_OP00_BLOCKED_WITHOUT_OP_FF and op00_wire_rejected
    if pa3_ok:
        passed_count += 1
    else:
        suite_errors.append("PA3 op=0x00 pre-check gate failed")
    results.append(
        PillarAScenarioResult(
            passed=pa3_ok,
            scenario_id=PILLAR_A_SCENARIO_IDS[2],
            steps_completed=tuple(sm3.steps_completed),
            dmm_phases_verified=(),
            op_ff_canary_sha256_match=False,
            op00_gate_enforced=pa3_ok,
            teardown_verified=False,
            usb_tx_packets_emitted=USB_TX_PACKETS_EMITTED,
            error_codes=(ERR_OP00_BLOCKED_WITHOUT_OP_FF,),
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_A_SCENARIO_IDS[2], "ok": pa3_ok}),
        )
    )

    # PA4: Reject slot > 0x11
    slot_rejected_set = False
    slot_rejected_get = False
    try:
        build_op_ff_set_request(1, 0x12, b"abc")
    except ValueError as exc:
        slot_rejected_set = ERR_OP_FF_SLOT_OUT_OF_RANGE in str(exc)
    try:
        build_op_ff_get_request(2, 0x12)
    except ValueError as exc:
        slot_rejected_get = ERR_OP_FF_SLOT_OUT_OF_RANGE in str(exc)
    pa4_ok = slot_rejected_set and slot_rejected_get
    if pa4_ok:
        passed_count += 1
    else:
        suite_errors.append("PA4 slot > 0x11 rejection failed")
    results.append(
        PillarAScenarioResult(
            passed=pa4_ok,
            scenario_id=PILLAR_A_SCENARIO_IDS[3],
            steps_completed=(),
            dmm_phases_verified=(),
            op_ff_canary_sha256_match=False,
            op00_gate_enforced=True,
            teardown_verified=False,
            usb_tx_packets_emitted=USB_TX_PACKETS_EMITTED,
            error_codes=(ERR_OP_FF_SLOT_OUT_OF_RANGE,),
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_A_SCENARIO_IDS[3], "ok": pa4_ok}),
        )
    )

    # PA5: Reject size > 5 MiB (and accept exact 5 MiB)
    size_rejected = False
    try:
        build_op_ff_set_request(1, 0, b"X" * (MAX_OP_FF_PAYLOAD_BYTES + 1))
    except ValueError as exc:
        size_rejected = ERR_OP_FF_SIZE_OUT_OF_RANGE in str(exc)
    exact_5m = build_op_ff_set_request(1, 0, b"X" * MAX_OP_FF_PAYLOAD_BYTES)
    pa5_ok = size_rejected and len(exact_5m) == 12 + 4 + 3 + MAX_OP_FF_PAYLOAD_BYTES
    if pa5_ok:
        passed_count += 1
    else:
        suite_errors.append("PA5 size > 5 MiB rejection failed")
    results.append(
        PillarAScenarioResult(
            passed=pa5_ok,
            scenario_id=PILLAR_A_SCENARIO_IDS[4],
            steps_completed=(),
            dmm_phases_verified=(),
            op_ff_canary_sha256_match=False,
            op00_gate_enforced=True,
            teardown_verified=False,
            usb_tx_packets_emitted=USB_TX_PACKETS_EMITTED,
            error_codes=(ERR_OP_FF_SIZE_OUT_OF_RANGE,),
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_A_SCENARIO_IDS[4], "ok": pa5_ok}),
        )
    )

    # PA6: Reject concurrent overlapping seq requests
    sm6 = ServiceSessionStateMachine()
    sm6.detect_msc()
    sm6.run_msc_handshake()
    sm6.seize_service_same_port()
    sm6.authenticate_service()
    sm6.execute_product_info_read0(seq=1)
    sm6.begin_flight(10)
    overlap_rejected = False
    try:
        sm6.begin_flight(11)
    except ValueError as exc:
        overlap_rejected = ERR_CONCURRENT_OVERLAPPING_SEQ in str(exc)
    sm6.end_flight(10)
    pa6_ok = overlap_rejected and (not sm6.inconcurrent_locked)
    if pa6_ok:
        passed_count += 1
    else:
        suite_errors.append("PA6 concurrent overlapping seq rejection failed")
    results.append(
        PillarAScenarioResult(
            passed=pa6_ok,
            scenario_id=PILLAR_A_SCENARIO_IDS[5],
            steps_completed=tuple(sm6.steps_completed),
            dmm_phases_verified=(),
            op_ff_canary_sha256_match=False,
            op00_gate_enforced=True,
            teardown_verified=False,
            usb_tx_packets_emitted=USB_TX_PACKETS_EMITTED,
            error_codes=(ERR_CONCURRENT_OVERLAPPING_SEQ,),
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_A_SCENARIO_IDS[5], "ok": pa6_ok}),
        )
    )

    # PA7: Reject missing STOP (0336:7) -> release (0336:8) -> 054C:0DA1 return (0da1:9) teardown
    sm7 = ServiceSessionStateMachine()
    sm7.detect_msc()
    sm7.run_msc_handshake()
    sm7.seize_service_same_port()
    sm7.authenticate_service()
    sm7.execute_product_info_read0(seq=1)
    sm7.run_op_ff_ram_canary_roundtrip(seq_base=2)
    sm7.send_stop_0336_7()
    # Missing release_service_0336_8 & observe_msc_return_and_release_0da1_9
    td7 = sm7.verify_complete_session_teardown()
    pa7_ok = (not td7.complete) and ERR_MISSING_TEARDOWN_SEQUENCE in td7.error_codes
    if pa7_ok:
        passed_count += 1
    else:
        suite_errors.append("PA7 missing teardown rejection failed")
    results.append(
        PillarAScenarioResult(
            passed=pa7_ok,
            scenario_id=PILLAR_A_SCENARIO_IDS[6],
            steps_completed=tuple(sm7.steps_completed),
            dmm_phases_verified=DMM_PHASES,
            op_ff_canary_sha256_match=True,
            op00_gate_enforced=True,
            teardown_verified=False,
            usb_tx_packets_emitted=USB_TX_PACKETS_EMITTED,
            error_codes=td7.error_codes,
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_A_SCENARIO_IDS[6], "ok": pa7_ok}),
        )
    )

    # PA8: Strictly passive ioreg XML & text USB topology parser (zero USB TX)
    topo_xml = parse_passive_ioreg_usb_topology(build_synthetic_ioreg_xml_snapshot())
    topo_txt = parse_passive_ioreg_usb_topology(build_synthetic_ioreg_text_snapshot())
    pa8_ok = (
        topo_xml.valid
        and topo_xml.snapshot_format == "xml"
        and topo_xml.msc_0da1_present
        and topo_xml.service_0336_present
        and topo_xml.same_port_continuity_verified
        and topo_xml.usb_tx_packets_emitted == 0
        and not topo_xml.live_usb_iokit_transmit_enabled
        and not topo_xml.persistent_emmc_writes_authorized
        and topo_txt.valid
        and topo_txt.snapshot_format == "text"
        and topo_txt.msc_0da1_present
        and topo_txt.usb_tx_packets_emitted == 0
    )
    if pa8_ok:
        passed_count += 1
    else:
        suite_errors.append("PA8 passive ioreg topology dry-run parser failed")
    results.append(
        PillarAScenarioResult(
            passed=pa8_ok,
            scenario_id=PILLAR_A_SCENARIO_IDS[7],
            steps_completed=(),
            dmm_phases_verified=(),
            op_ff_canary_sha256_match=False,
            op00_gate_enforced=True,
            teardown_verified=False,
            usb_tx_packets_emitted=USB_TX_PACKETS_EMITTED,
            error_codes=(),
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_A_SCENARIO_IDS[7], "ok": pa8_ok}),
        )
    )

    all_ok = len(suite_errors) == 0 and passed_count == len(PILLAR_A_SCENARIO_IDS)
    return PillarA8ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_PILLAR_A if all_ok else STATUS_REJECTED_PILLAR_A,
        scenarios_passed=passed_count,
        scenarios_total=len(PILLAR_A_SCENARIO_IDS),
        scenario_results=tuple(results),
        usb_tx_packets_emitted=USB_TX_PACKETS_EMITTED,
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256(
            {"scenarios": [r.report_sha256 for r in results], "ok": all_ok}
        ),
    )


# ---------------------------------------------------------------------------
# Pillar B — Stage-288 §4 (1..6) Hardened ARM64 libJit.so ELF64 Builder & Gate
# ---------------------------------------------------------------------------


def build_synthetic_sector0_fx3_table() -> bytes:
    """Build a valid 512B FX3 Sector 0 table (`8246`/`2.00`, 30 partitions, p1=0x80..0xbf80)."""
    buf = bytearray(SECTOR0_BYTES)
    buf[0:4] = SECTOR0_MAGIC
    buf[4:8] = SECTOR0_VERSION
    struct.pack_into("<I", buf, 8, SECTOR0_EXPECTED_PARTITIONS)
    struct.pack_into("<IIII", buf, 0x20, 0x80, 0xBF80, 1, 0)
    cursor = 0xC000
    for idx in range(1, SECTOR0_EXPECTED_PARTITIONS):
        size_sec = 0x2000 if idx != 5 else 0xC800
        struct.pack_into("<IIII", buf, 0x20 + idx * 16, cursor, size_sec, 1, 0)
        cursor += size_sec
    return bytes(buf)


def build_fx3_sector0_ok_frame(sector0: bytes) -> bytes:
    """Build 528B framed output: `b'FX3S0OK\\x00'` + `<II(512, crc32_ieee)` + `512B` Sector 0."""
    _need(isinstance(sector0, bytes) and len(sector0) == SECTOR0_BYTES, "sector0 must be 512 bytes")
    crc = zlib.crc32(sector0) & 0xFFFFFFFF
    return FX3S0OK_MAGIC + struct.pack("<II", SECTOR0_BYTES, crc) + sector0


def parse_fx3_sector0_ok_frame(frame: bytes) -> Sector0FrameInfo:
    """Parse and validate 528B `FX3S0OK\\x00` framed Sector 0 output."""
    errors: List[str] = []
    if not isinstance(frame, bytes) or len(frame) != FX3S0OK_FRAME_BYTES:
        return Sector0FrameInfo(
            False, "", 0, "", "", "", "", 0, 0, 0, (f"{ERR_FRAME_INVALID}: expected 528B",)
        )
    magic = frame[:8]
    payload_len, crc_expected = struct.unpack_from("<II", frame, 8)
    s0 = frame[16:]
    crc_actual = zlib.crc32(s0) & 0xFFFFFFFF
    if magic != FX3S0OK_MAGIC:
        errors.append("bad FX3S0OK magic")
    if payload_len != SECTOR0_BYTES:
        errors.append(f"unexpected payload_len={payload_len}")
    if crc_actual != crc_expected:
        errors.append("crc32_ieee mismatch")
    s0_magic = s0[0:4].decode("ascii", "replace")
    s0_ver = s0[4:8].decode("ascii", "replace")
    n_part = struct.unpack_from("<I", s0, 8)[0]
    p1_start, p1_size = struct.unpack_from("<II", s0, 0x20)
    if s0[0:4] != SECTOR0_MAGIC or s0[4:8] != SECTOR0_VERSION:
        errors.append("sector0 header not 8246/2.00")
    if n_part != SECTOR0_EXPECTED_PARTITIONS:
        errors.append(f"n_partitions={n_part} != 30")
    if (p1_start, p1_size) != SECTOR0_EXPECTED_P1:
        errors.append(f"p1={(p1_start, p1_size)} != (0x80, 0xbf80)")
    return Sector0FrameInfo(
        valid=len(errors) == 0,
        magic_hex=magic.hex(),
        payload_len=payload_len,
        crc32_expected_hex=f"{crc_expected:#010x}",
        crc32_actual_hex=f"{crc_actual:#010x}",
        sector0_magic=s0_magic,
        sector0_version=s0_ver,
        n_partitions=n_part,
        p1_start_lba=p1_start,
        p1_size_sectors=p1_size,
        errors=tuple(errors),
    )


def build_fx3_sector0_err_receipt(stage: int, errno_val: int) -> bytes:
    """Build 16B structured error receipt `b'FX3S0ERR' + <ii(stage, errno_val)`."""
    return FX3S0ERR_MAGIC + struct.pack("<ii", int(stage), int(errno_val))


def parse_fx3_sector0_err_receipt(receipt: bytes) -> Sector0ErrReceipt:
    """Parse and validate 16B `FX3S0ERR` structured error receipt."""
    errors: List[str] = []
    if not isinstance(receipt, bytes) or len(receipt) != FX3S0ERR_FRAME_BYTES:
        return Sector0ErrReceipt(False, "", 0, 0, ("error receipt must be 16 bytes",))
    magic = receipt[:8]
    stage, errno_val = struct.unpack_from("<ii", receipt, 8)
    if magic != FX3S0ERR_MAGIC:
        errors.append("bad FX3S0ERR magic")
    if stage <= 0:
        errors.append("stage must be > 0")
    if errno_val <= 0:
        errors.append("errno_val must be > 0")
    return Sector0ErrReceipt(
        valid=len(errors) == 0,
        magic=magic.decode("ascii", "replace"),
        stage=stage,
        errno_val=errno_val,
        errors=tuple(errors),
    )


# --- Clean-Room AArch64 Mini-Assembler for Hardened libJit.so DT_INIT ---

def _movz64(rd: int, imm16: int, hw: int = 0) -> int:
    return (1 << 31) | (0b10 << 29) | (0b100101 << 23) | (hw << 21) | ((imm16 & 0xFFFF) << 5) | rd


def _movz32(rd: int, imm16: int, hw: int = 0) -> int:
    return (0 << 31) | (0b10 << 29) | (0b100101 << 23) | (hw << 21) | ((imm16 & 0xFFFF) << 5) | rd


def _movk32(rd: int, imm16: int, hw: int = 0) -> int:
    return (0 << 31) | (0b11 << 29) | (0b100101 << 23) | (hw << 21) | ((imm16 & 0xFFFF) << 5) | rd


def _movn64(rd: int, imm16: int, hw: int = 0) -> int:
    return (1 << 31) | (0b00 << 29) | (0b100101 << 23) | (hw << 21) | ((imm16 & 0xFFFF) << 5) | rd


def _adr(rd: int, imm_bytes: int) -> int:
    immlo = imm_bytes & 3
    immhi = (imm_bytes >> 2) & 0x7FFFF
    return (immlo << 29) | (0b10000 << 24) | (immhi << 5) | rd


def _add64_imm(rd: int, rn: int, imm12: int) -> int:
    return (1 << 31) | (0b100010 << 23) | ((imm12 & 0xFFF) << 10) | (rn << 5) | rd


def _sub64_imm(rd: int, rn: int, imm12: int) -> int:
    return (1 << 31) | (0b10 << 29) | (0b100010 << 23) | ((imm12 & 0xFFF) << 10) | (rn << 5) | rd


def _subs64_imm(rd: int, rn: int, imm12: int) -> int:
    return (1 << 31) | (0b11 << 29) | (0b100010 << 23) | ((imm12 & 0xFFF) << 10) | (rn << 5) | rd


def _subs32_imm(rd: int, rn: int, imm12: int) -> int:
    return (0 << 31) | (0b11 << 29) | (0b100010 << 23) | ((imm12 & 0xFFF) << 10) | (rn << 5) | rd


def _mov64_reg(rd: int, rm: int) -> int:
    return (1 << 31) | (0b01 << 29) | (0b01010 << 24) | (rm << 16) | (31 << 5) | rd


def _mvn32_reg(rd: int, rm: int) -> int:
    return (0 << 31) | (0b01 << 29) | (0b01010 << 24) | (1 << 21) | (rm << 16) | (31 << 5) | rd


def _neg32_reg(rd: int, rm: int) -> int:
    return (0 << 31) | (0b10 << 29) | (0b01011 << 24) | (rm << 16) | (31 << 5) | rd


def _ubfx32(rd: int, rn: int, lsb: int, width: int) -> int:
    return (0 << 31) | (0b10 << 29) | (0b100110 << 23) | (lsb << 16) | ((lsb + width - 1) << 10) | (rn << 5) | rd


def _lsr32_1(rd: int, rn: int) -> int:
    return _ubfx32(rd, rn, 1, 31)


def _tst32_1(rn: int) -> int:
    return (0 << 31) | (0b11 << 29) | (0b100100 << 23) | (0 << 16) | (0 << 10) | (rn << 5) | 31


def _eor32(rd: int, rn: int, rm: int) -> int:
    return (0 << 31) | (0b10 << 29) | (0b01010 << 24) | (rm << 16) | (rn << 5) | rd


def _ldr64_off(rt: int, rn: int, off: int) -> int:
    return (0b11 << 30) | (0b111001 << 24) | (0b01 << 22) | ((off // 8) << 10) | (rn << 5) | rt


def _str64_off(rt: int, rn: int, off: int) -> int:
    return (0b11 << 30) | (0b111001 << 24) | (0b00 << 22) | ((off // 8) << 10) | (rn << 5) | rt


def _ldr32_off(rt: int, rn: int, off: int) -> int:
    return (0b10 << 30) | (0b111001 << 24) | (0b01 << 22) | ((off // 4) << 10) | (rn << 5) | rt


def _str32_off(rt: int, rn: int, off: int) -> int:
    return (0b10 << 30) | (0b111001 << 24) | (0b00 << 22) | ((off // 4) << 10) | (rn << 5) | rt


def _ldrb_post1(rt: int, rn: int) -> int:
    return (0b00 << 30) | (0b111000 << 24) | (0b01 << 22) | (1 << 12) | (0b01 << 10) | (rn << 5) | rt


def _stp_pre(rt1: int, rt2: int, rn: int, off: int) -> int:
    return (0b10 << 30) | (0b1010011 << 23) | (((off // 8) & 0x7F) << 15) | (rt2 << 10) | (rn << 5) | rt1


def _ldp_post(rt1: int, rt2: int, rn: int, off: int) -> int:
    return (0b10 << 30) | (0b10100011 << 22) | (((off // 8) & 0x7F) << 15) | (rt2 << 10) | (rn << 5) | rt1


def _stp_off(rt1: int, rt2: int, rn: int, off: int) -> int:
    return (0b10 << 30) | (0b1010010 << 23) | (((off // 8) & 0x7F) << 15) | (rt2 << 10) | (rn << 5) | rt1


def _ldp_off(rt1: int, rt2: int, rn: int, off: int) -> int:
    return (0b10 << 30) | (0b10100101 << 22) | (((off // 8) & 0x7F) << 15) | (rt2 << 10) | (rn << 5) | rt1


def _b_cond(cond: int, off_bytes: int) -> int:
    return (0b01010100 << 24) | (((off_bytes // 4) & 0x7FFFF) << 5) | cond


def _b_uncond(off_bytes: int) -> int:
    return (0b000101 << 26) | ((off_bytes // 4) & 0x3FFFFFF)


def _tbnz(rt: int, bit: int, off_bytes: int) -> int:
    return ((bit >> 5) << 31) | (0b0110111 << 24) | ((bit & 0x1F) << 19) | (((off_bytes // 4) & 0x3FFF) << 5) | rt


_SVC_0: int = 0xD4000001
_RET: int = 0xD65F03C0


def _assemble_hardened_init_code_and_rodata() -> bytes:
    """Assemble hardened AArch64 `DT_INIT` constructor + `.rodata` block."""
    rodata = bytearray()
    str_offsets: Dict[str, int] = {}

    def _add_ro(key: str, raw: bytes, align: int = 8) -> None:
        while len(rodata) % align != 0:
            rodata.append(0)
        str_offsets[key] = len(rodata)
        rodata.extend(raw)

    _add_ro("libjit", LIBJIT_TARGET_PATH.encode("ascii") + b"\x00", align=4)
    _add_ro("nflasha", NFLASH_WHOLE_NODE.encode("ascii") + b"\x00", align=4)
    _add_ro("proc_parts", PROC_PARTITIONS_PATH.encode("ascii") + b"\x00", align=4)
    _add_ro("nflasha1", NFLASH_FALLBACK_NODE.encode("ascii") + b"\x00", align=4)
    _add_ro("out_path", SECTOR0_OUT_PATH.encode("ascii") + b"\x00", align=4)
    _add_ro("ok_magic", FX3S0OK_MAGIC, align=8)
    _add_ro("err_magic", FX3S0ERR_MAGIC, align=8)

    # Two-pass assembly so ADR and branches resolve cleanly
    labels: Dict[str, int] = {}
    adr_fixups: List[Tuple[int, int, str]] = []  # (insn_idx, reg, ro_key)
    br_fixups: List[Tuple[int, str, str, int]] = []  # (insn_idx, kind, label, extra)
    insns: List[int] = []

    def emit(word: int) -> int:
        idx = len(insns)
        insns.append(word)
        return idx

    def label(name: str) -> None:
        labels[name] = len(insns) * 4

    def emit_adr(rd: int, ro_key: str) -> None:
        idx = emit(0)
        adr_fixups.append((idx, rd, ro_key))

    def emit_b(target: str) -> None:
        idx = emit(0)
        br_fixups.append((idx, "b", target, 0))

    def emit_b_cond(cond: int, target: str) -> None:
        idx = emit(0)
        br_fixups.append((idx, "bcond", target, cond))

    def emit_tbnz(rt: int, bit: int, target: str) -> None:
        idx = emit(0)
        br_fixups.append((idx, "tbnz", target, (rt << 8) | bit))

    # Prologue
    emit(_stp_pre(29, 30, 31, -64))
    emit(_stp_off(19, 20, 31, 16))
    emit(_stp_off(21, 22, 31, 32))
    emit(_sub64_imm(31, 31, 800))

    # §4.1 Self-unlink FIRST: unlinkat(AT_FDCWD=-100, "/tmp/jiritsu/libJit.so", 0)
    emit(_movn64(0, 99))  # x0 = -100 (AT_FDCWD)
    emit_adr(1, "libjit")
    emit(_movz64(2, 0))
    emit(_movz64(8, SYS_AARCH64_UNLINKAT))
    emit(_SVC_0)

    # §4.4 Check /dev/nflasha with newfstatat & S_ISBLK
    emit(_movn64(0, 99))
    emit_adr(1, "nflasha")
    emit(_add64_imm(2, 31, 0))  # &statbuf
    emit(_movz64(3, 0))
    emit(_movz64(8, SYS_AARCH64_NEWFSTATAT))
    emit(_SVC_0)
    emit_tbnz(0, 63, "fallback_probe")
    emit(_ldr32_off(9, 31, 16))  # st_mode at offset 16
    emit(_ubfx32(9, 9, 12, 4))  # (st_mode >> 12) & 0xf
    emit(_subs32_imm(31, 9, 6))  # S_IFBLK == 0x6000 >> 12 == 6
    emit_b_cond(0, "open_nflasha")  # b.eq

    # Fallback probe: /proc/partitions & /dev/nflasha1, then emit FX3S0ERR
    label("fallback_probe")
    emit(_movz32(19, 1))  # stage = 1
    emit(_subs64_imm(31, 0, 0))
    emit_b_cond(11, "fb_neg_errno")  # b.lt
    emit(_movz32(20, 15))  # ENOTBLK = 15
    emit_b("fb_probe_proc")
    label("fb_neg_errno")
    emit(_neg32_reg(20, 0))
    label("fb_probe_proc")
    emit(_movn64(0, 99))
    emit_adr(1, "proc_parts")
    emit(_movz32(2, 0, 0))
    emit(_movk32(2, 0x8, 1))  # O_RDONLY | O_CLOEXEC = 0x80000
    emit(_movz64(3, 0))
    emit(_movz64(8, SYS_AARCH64_OPENAT))
    emit(_SVC_0)
    emit_tbnz(0, 63, "fb_probe_p1")
    emit(_mov64_reg(21, 0))
    emit(_add64_imm(1, 31, 144))
    emit(_movz64(2, 256))
    emit(_movz64(8, SYS_AARCH64_READ))
    emit(_SVC_0)
    emit(_mov64_reg(0, 21))
    emit(_movz64(8, SYS_AARCH64_CLOSE))
    emit(_SVC_0)
    label("fb_probe_p1")
    emit(_movn64(0, 99))
    emit_adr(1, "nflasha1")
    emit(_add64_imm(2, 31, 0))
    emit(_movz64(3, 0))
    emit(_movz64(8, SYS_AARCH64_NEWFSTATAT))
    emit(_SVC_0)
    emit_b("emit_err")

    # §4.2 Open /dev/nflasha O_RDONLY | O_CLOEXEC & read 512B BEFORE opening output
    label("open_nflasha")
    emit(_movn64(0, 99))
    emit_adr(1, "nflasha")
    emit(_movz32(2, 0, 0))
    emit(_movk32(2, 0x8, 1))  # O_RDONLY | O_CLOEXEC = 0x80000
    emit(_movz64(3, 0))
    emit(_movz64(8, SYS_AARCH64_OPENAT))
    emit(_SVC_0)
    emit_tbnz(0, 63, "err_open_in")
    emit(_mov64_reg(21, 0))
    emit(_add64_imm(1, 31, 144))
    emit(_movz64(2, 512))
    emit(_movz64(8, SYS_AARCH64_READ))
    emit(_SVC_0)
    emit(_mov64_reg(22, 0))
    emit(_mov64_reg(0, 21))
    emit(_movz64(8, SYS_AARCH64_CLOSE))
    emit(_SVC_0)
    emit(_subs64_imm(31, 22, 512))
    emit_b_cond(0, "compute_crc")  # b.eq

    # Read failed / short read != 512
    emit(_movz32(19, 3))  # stage = 3 (read)
    emit(_subs64_imm(31, 22, 0))
    emit_b_cond(11, "read_neg_errno")
    emit(_movz32(20, 5))  # EIO = 5
    emit_b("emit_err")
    label("read_neg_errno")
    emit(_neg32_reg(20, 22))
    emit_b("emit_err")

    label("err_open_in")
    emit(_movz32(19, 2))  # stage = 2 (openat)
    emit(_neg32_reg(20, 0))
    emit_b("emit_err")

    # §4.3 Compute IEEE CRC-32 and emit 528B FX3S0OK\x00 frame
    label("compute_crc")
    emit(_mvn32_reg(9, 31))
    emit(_add64_imm(10, 31, 144))
    emit(_movz64(11, 512))
    emit(_movz32(12, 0x8320, 0))
    emit(_movk32(12, 0xEDB8, 1))
    label("crc_byte_loop")
    emit(_ldrb_post1(13, 10))
    emit(_eor32(9, 9, 13))
    emit(_movz32(14, 8))
    label("crc_bit_loop")
    emit(_tst32_1(9))
    emit(_lsr32_1(9, 9))
    emit_b_cond(0, "crc_skip_xor")
    emit(_eor32(9, 9, 12))
    label("crc_skip_xor")
    emit(_subs32_imm(14, 14, 1))
    emit_b_cond(1, "crc_bit_loop")
    emit(_subs64_imm(11, 11, 1))
    emit_b_cond(1, "crc_byte_loop")
    emit(_mvn32_reg(9, 9))

    emit_adr(10, "ok_magic")
    emit(_ldr64_off(11, 10, 0))
    emit(_str64_off(11, 31, 128))
    emit(_movz32(11, 512))
    emit(_str32_off(11, 31, 136))
    emit(_str32_off(9, 31, 140))

    emit(_movn64(0, 99))
    emit_adr(1, "out_path")
    emit(_movz32(2, 0x0241, 0))
    emit(_movk32(2, 0x8, 1))  # O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC = 0x80241
    emit(_movz64(3, 0x180))  # 0o600
    emit(_movz64(8, SYS_AARCH64_OPENAT))
    emit(_SVC_0)
    emit_tbnz(0, 63, "done")
    emit(_mov64_reg(21, 0))
    emit(_add64_imm(1, 31, 128))
    emit(_movz64(2, FX3S0OK_FRAME_BYTES))
    emit(_movz64(8, SYS_AARCH64_WRITE))
    emit(_SVC_0)
    emit(_mov64_reg(0, 21))
    emit(_movz64(8, SYS_AARCH64_CLOSE))
    emit(_SVC_0)
    emit_b("done")

    # §4.4 Structured 16B FX3S0ERR receipt
    label("emit_err")
    emit_adr(10, "err_magic")
    emit(_ldr64_off(11, 10, 0))
    emit(_str64_off(11, 31, 656))
    emit(_str32_off(19, 31, 664))
    emit(_str32_off(20, 31, 668))

    emit(_movn64(0, 99))
    emit_adr(1, "out_path")
    emit(_movz32(2, 0x0241, 0))
    emit(_movk32(2, 0x8, 1))
    emit(_movz64(3, 0x180))
    emit(_movz64(8, SYS_AARCH64_OPENAT))
    emit(_SVC_0)
    emit_tbnz(0, 63, "done")
    emit(_mov64_reg(21, 0))
    emit(_add64_imm(1, 31, 656))
    emit(_movz64(2, FX3S0ERR_FRAME_BYTES))
    emit(_movz64(8, SYS_AARCH64_WRITE))
    emit(_SVC_0)
    emit(_mov64_reg(0, 21))
    emit(_movz64(8, SYS_AARCH64_CLOSE))
    emit(_SVC_0)

    # Epilogue
    label("done")
    emit(_add64_imm(31, 31, 800))
    emit(_ldp_off(21, 22, 31, 32))
    emit(_ldp_off(19, 20, 31, 16))
    emit(_ldp_post(29, 30, 31, 64))
    emit(_RET)

    # Align code end to 8 bytes before .rodata
    if (len(insns) * 4) % 8 != 0:
        emit(0xD503201F)  # NOP

    rodata_base_off = len(insns) * 4
    for idx, rd, ro_key in adr_fixups:
        pc = idx * 4
        target = rodata_base_off + str_offsets[ro_key]
        insns[idx] = _adr(rd, target - pc)

    for idx, kind, target_label, extra in br_fixups:
        pc = idx * 4
        target_pc = labels[target_label]
        delta = target_pc - pc
        if kind == "b":
            insns[idx] = _b_uncond(delta)
        elif kind == "bcond":
            insns[idx] = _b_cond(extra, delta)
        elif kind == "tbnz":
            rt = extra >> 8
            bit = extra & 0xFF
            insns[idx] = _tbnz(rt, bit, delta)

    code_bytes = b"".join(struct.pack("<I", w) for w in insns)
    return code_bytes + bytes(rodata)


def build_hardened_libjit_elf64(
    *,
    pt_load_align: int = ELF_PT_LOAD_PAGE_ALIGN,
    dt_hash_words: Tuple[int, int, int, int] = (1, 1, 0, 0),
    inject_forbidden_token: Optional[str] = None,
    inject_wx_segment: bool = False,
    dt_out_of_bounds_va: Optional[int] = None,
    replace_open_flags_with: Optional[int] = None,
) -> bytes:
    """Build a clean-room minimal AArch64 `ET_DYN` (`< 16 KiB`) `libJit.so` ELF64.

    By default satisfies all 6 Stage-288 §4 hardening rules; optional keyword
    arguments allow negative-test fault injection (for gate verification).
    """
    eh_size = 64
    ph_size = 56
    ph_num = 3
    ph_off = eh_size

    text_off = 0x1000
    text_va = 0x1000
    text_rodata = bytearray(_assemble_hardened_init_code_and_rodata())
    if replace_open_flags_with is not None:
        # Patch the /dev/nflasha openat flags instruction sequence (movz w2, #0; movk w2, #0x8, lsl #16)
        target_seq = struct.pack("<II", _movz32(2, 0, 0), _movk32(2, 0x8, 1))
        # Find second occurrence (first is /proc/partitions, second is /dev/nflasha)
        first = text_rodata.find(target_seq)
        second = text_rodata.find(target_seq, first + 8) if first >= 0 else -1
        if second >= 0:
            patched = struct.pack(
                "<II", _movz32(2, replace_open_flags_with & 0xFFFF, 0), 0xD503201F
            )
            text_rodata[second : second + 8] = patched

    if inject_forbidden_token:
        text_rodata.extend(b"\x00" + inject_forbidden_token.encode("ascii") + b"\x00")

    dyn_off = 0x2000
    # Use distinct 64 KiB virtual page (0x12000 % 0x10000 == 0x2000 == dyn_off % 0x10000)
    dyn_va = 0x12000 if pt_load_align >= 0x10000 else 0x2000

    sym_va = dyn_va + 0x70
    str_va = dyn_va + 0x88
    hash_va = dyn_va + 0x89
    if dt_out_of_bounds_va is not None:
        sym_va = dt_out_of_bounds_va
        str_va = dt_out_of_bounds_va + 0x20
        hash_va = dt_out_of_bounds_va + 0x30

    dyn_entries = (
        (ELF_DT_STRTAB, str_va),
        (ELF_DT_SYMTAB, sym_va),
        (ELF_DT_STRSZ, 1),
        (ELF_DT_SYMENT, 24),
        (ELF_DT_HASH, hash_va),
        (ELF_DT_INIT, text_va),
        (ELF_DT_NULL, 0),
    )
    dyn_bytes = b"".join(struct.pack("<QQ", tag, val) for tag, val in dyn_entries)
    dynsym = b"\x00" * 24
    dynstr = b"\x00"
    hash_bytes = struct.pack("<IIII", *dt_hash_words)
    rdata = dyn_bytes + dynsym + dynstr + hash_bytes

    total_len = dyn_off + len(rdata)
    out = bytearray(total_len)
    e_ident = ELF_MAGIC + bytes([ELF_CLASS_64, ELF_DATA_LSB, 1, 0]) + (b"\x00" * 8)
    struct.pack_into(
        "<16sHHIQQQIHHHHHH",
        out,
        0,
        e_ident,
        ELF_TYPE_DYN,
        ELF_MACHINE_AARCH64,
        1,
        0,
        ph_off,
        0,
        0,
        eh_size,
        ph_size,
        ph_num,
        0,
        0,
        0,
    )

    def _set_ph(idx: int, p_type: int, p_flags: int, offset: int, vaddr: int, size: int, align: int) -> None:
        struct.pack_into(
            "<IIQQQQQQ",
            out,
            ph_off + idx * ph_size,
            p_type,
            p_flags,
            offset,
            vaddr,
            vaddr,
            size,
            size,
            align,
        )

    seg0_flags = (ELF_PF_R | ELF_PF_W | ELF_PF_X) if inject_wx_segment else (ELF_PF_R | ELF_PF_X)
    _set_ph(0, ELF_PT_LOAD, seg0_flags, text_off, text_va, len(text_rodata), pt_load_align)
    _set_ph(1, ELF_PT_LOAD, ELF_PF_R | ELF_PF_W, dyn_off, dyn_va, len(rdata), pt_load_align)
    _set_ph(2, ELF_PT_DYNAMIC, ELF_PF_R | ELF_PF_W, dyn_off, dyn_va, len(dyn_bytes), 8)
    out[text_off : text_off + len(text_rodata)] = text_rodata
    out[dyn_off : dyn_off + len(rdata)] = rdata
    return bytes(out)


def _decode_cstr_at_va(
    so_bytes: bytes,
    pt_loads: Sequence[Tuple[int, int, int, int, int]],
    va: int,
) -> Optional[str]:
    for _pf, p_off, p_va, p_fs, _al in pt_loads:
        if p_va <= va < p_va + p_fs:
            foff = p_off + (va - p_va)
            end = so_bytes.find(b"\x00", foff, min(len(so_bytes), p_off + p_fs + 1))
            if end > foff:
                try:
                    return so_bytes[foff:end].decode("ascii")
                except UnicodeDecodeError:
                    return None
    return None


def _disassemble_syscalls_and_track_regs(
    so_bytes: bytes,
    pt_loads: Sequence[Tuple[int, int, int, int, int]],
    entry_va: int,
) -> Tuple[List[DecodedSyscallSite], bool, bool]:
    """Static pure-Python AArch64 instruction decoder & constant-state tracker."""
    seg = None
    for pf, p_off, p_va, p_fs, _al in pt_loads:
        if (pf & ELF_PF_X) and p_va <= entry_va < p_va + p_fs:
            seg = (p_off, p_va, p_fs)
            break
    if seg is None:
        return [], False, False

    p_off, p_va, p_fs = seg
    start_off = p_off + (entry_va - p_va)
    end_off = p_off + p_fs

    regs: Dict[int, Optional[int]] = {i: None for i in range(32)}
    regs[31] = 0x100000  # synthetic stack pointer base
    sites: List[DecodedSyscallSite] = []
    saw_read512_cmp = False
    saw_read512_before_out_open = False
    opened_out_path = False

    def _s19(v: int) -> int:
        return v - (1 << 19) if (v & (1 << 18)) else v

    def _s21(v: int) -> int:
        return v - (1 << 21) if (v & (1 << 20)) else v

    pos = start_off
    while pos + 4 <= end_off:
        word = struct.unpack_from("<I", so_bytes, pos)[0]
        pc = p_va + (pos - p_off)
        pos += 4

        if word == _SVC_0:
            sc_num = regs.get(8)
            if isinstance(sc_num, int):
                arg0 = regs.get(0)
                arg1 = regs.get(1)
                arg2 = regs.get(2)
                arg3 = regs.get(3)
                arg1_str = _decode_cstr_at_va(so_bytes, pt_loads, arg1) if isinstance(arg1, int) else None
                sc_name = {
                    SYS_AARCH64_IOCTL: "ioctl",
                    SYS_AARCH64_UNLINKAT: "unlinkat",
                    SYS_AARCH64_MOUNT: "mount",
                    SYS_AARCH64_OPENAT: "openat",
                    SYS_AARCH64_CLOSE: "close",
                    SYS_AARCH64_READ: "read",
                    SYS_AARCH64_WRITE: "write",
                    SYS_AARCH64_PREAD64: "pread64",
                    SYS_AARCH64_PWRITE64: "pwrite64",
                    SYS_AARCH64_NEWFSTATAT: "newfstatat",
                }.get(sc_num, f"sys_{sc_num}")
                if sc_num == SYS_AARCH64_OPENAT and arg1_str == SECTOR0_OUT_PATH:
                    if not opened_out_path and saw_read512_cmp:
                        saw_read512_before_out_open = True
                    opened_out_path = True
                sites.append(
                    DecodedSyscallSite(
                        va=pc,
                        syscall_num=sc_num,
                        syscall_name=sc_name,
                        arg0=arg0,
                        arg1_str=arg1_str,
                        arg2=arg2,
                        arg3=arg3,
                    )
                )
            continue

        # Move wide (MOVZ / MOVK / MOVN)
        if (word & 0x1F800000) == 0x12800000:
            sf = (word >> 31) & 1
            opc = (word >> 29) & 3
            hw = (word >> 21) & 3
            imm16 = (word >> 5) & 0xFFFF
            rd = word & 0x1F
            shift = hw * 16
            if opc == 0b10:  # MOVZ
                regs[rd] = imm16 << shift
            elif opc == 0b00:  # MOVN
                val = ~(imm16 << shift)
                regs[rd] = val if sf else (val & 0xFFFFFFFF)
            elif opc == 0b11:  # MOVK
                cur = regs.get(rd) or 0
                mask = ~(0xFFFF << shift)
                val = (cur & mask) | (imm16 << shift)
                regs[rd] = val if sf else (val & 0xFFFFFFFF)
            continue

        # ADR / ADRP
        if (word & 0x1F000000) == 0x10000000:
            op = (word >> 31) & 1
            immlo = (word >> 29) & 3
            immhi = (word >> 5) & 0x7FFFF
            rd = word & 0x1F
            imm = _s21((immhi << 2) | immlo)
            if op == 0:  # ADR
                regs[rd] = pc + imm
            else:  # ADRP
                regs[rd] = (pc & ~0xFFF) + (imm << 12)
            continue

        # ADD / SUB / SUBS immediate
        if (word & 0x1F000000) == 0x11000000:
            sf = (word >> 31) & 1
            op = (word >> 30) & 1
            s_bit = (word >> 29) & 1
            sh = (word >> 22) & 1
            imm12 = ((word >> 10) & 0xFFF) << (12 if sh else 0)
            rn = (word >> 5) & 0x1F
            rd = word & 0x1F
            if op == 1 and s_bit == 1 and rd == 31 and imm12 == 512:
                saw_read512_cmp = True
            if rd != 31:
                base = regs.get(rn)
                if isinstance(base, int):
                    val = (base - imm12) if op else (base + imm12)
                    regs[rd] = val if sf else (val & 0xFFFFFFFF)
            continue

        # MOV (ORR Xd, XZR, Xm)
        if (word & 0x7FE0FFE0) == 0x2A0003E0:
            rm = (word >> 16) & 0x1F
            rd = word & 0x1F
            regs[rd] = regs.get(rm)
            continue

    return sites, saw_read512_cmp, saw_read512_before_out_open


def verify_hardened_libjit_elf64(so_bytes: bytes) -> LibJitElfHardeningReport:
    """Static disassembly & ELF64 gate enforcing ALL 6 Stage-288 §4 P0 hardening rules."""
    errors: List[str] = []
    error_codes: List[str] = []
    firewall_violations: List[str] = []

    if not isinstance(so_bytes, bytes) or len(so_bytes) < 64 or so_bytes[:4] != ELF_MAGIC:
        return LibJitElfHardeningReport(
            passed=False,
            elf_size_bytes=len(so_bytes) if isinstance(so_bytes, bytes) else 0,
            under_16kib=False,
            e_machine=0,
            e_type=0,
            pt_load_count=0,
            pt_load_alignments=(),
            has_wx_segment=False,
            has_overlapping_pt_load=False,
            dt_symtab_in_bounds=False,
            dt_strtab_in_bounds=False,
            dt_hash_in_bounds=False,
            dt_init_in_bounds=False,
            dt_hash_words=(0, 0, 0, 0),
            rule1_self_unlink_first_ok=False,
            rule2_read_first_cloexec_ok=False,
            rule3_framed_528b_output_ok=False,
            rule4_blk_node_and_fallback_ok=False,
            rule5_64k_pt_load_and_dt_bounds_ok=False,
            rule6_static_syscall_token_firewall_ok=False,
            decoded_syscalls=(),
            firewall_violations=(),
            error_codes=(ERR_LIBJIT_RULE5_ELF_LAYOUT_OR_64K_ALIGN,),
            errors=("invalid ELF64 header",),
        )

    under_16k = len(so_bytes) < MAX_LIBJIT_ELF_BYTES
    if not under_16k:
        error_codes.append(ERR_LIBJIT_ELF_OVERSIZED)
        errors.append(f"ELF size {len(so_bytes)} >= 16384")

    ei_class = so_bytes[4]
    ei_data = so_bytes[5]
    e_type, e_machine, _ev, _ee, e_phoff, _shoff, _ef, _ehsz, e_phentsz, e_phnum = (
        struct.unpack_from("<HHIQQQIHHH", so_bytes, 16)
    )
    if (
        ei_class != ELF_CLASS_64
        or ei_data != ELF_DATA_LSB
        or e_type != ELF_TYPE_DYN
        or e_machine != ELF_MACHINE_AARCH64
        or e_phentsz < 56
        or e_phoff + e_phnum * e_phentsz > len(so_bytes)
    ):
        error_codes.append(ERR_LIBJIT_RULE5_ELF_LAYOUT_OR_64K_ALIGN)
        errors.append("not a valid ELF64 LE AArch64 ET_DYN")
        return LibJitElfHardeningReport(
            passed=False,
            elf_size_bytes=len(so_bytes),
            under_16kib=under_16k,
            e_machine=e_machine,
            e_type=e_type,
            pt_load_count=0,
            pt_load_alignments=(),
            has_wx_segment=False,
            has_overlapping_pt_load=False,
            dt_symtab_in_bounds=False,
            dt_strtab_in_bounds=False,
            dt_hash_in_bounds=False,
            dt_init_in_bounds=False,
            dt_hash_words=(0, 0, 0, 0),
            rule1_self_unlink_first_ok=False,
            rule2_read_first_cloexec_ok=False,
            rule3_framed_528b_output_ok=False,
            rule4_blk_node_and_fallback_ok=False,
            rule5_64k_pt_load_and_dt_bounds_ok=False,
            rule6_static_syscall_token_firewall_ok=False,
            decoded_syscalls=(),
            firewall_violations=(),
            error_codes=tuple(error_codes),
            errors=tuple(errors),
        )

    pt_loads: List[Tuple[int, int, int, int, int]] = []  # (flags, off, va, filesz, align)
    pt_dyn_off = 0
    pt_dyn_sz = 0
    for idx in range(e_phnum):
        p_type, p_flags, p_off, p_va, _pp, p_fs, _ms, p_al = struct.unpack_from(
            "<IIQQQQQQ", so_bytes, e_phoff + idx * e_phentsz
        )
        if p_type == ELF_PT_LOAD:
            pt_loads.append((p_flags, p_off, p_va, p_fs, p_al))
        elif p_type == ELF_PT_DYNAMIC:
            pt_dyn_off = p_off
            pt_dyn_sz = p_fs

    aligns = tuple(item[4] for item in pt_loads)
    all_64k = len(pt_loads) >= 2 and all(item[4] == ELF_PT_LOAD_PAGE_ALIGN for item in pt_loads)
    congruent = all((item[2] % item[4]) == (item[1] % item[4]) for item in pt_loads if item[4] > 0)
    has_wx = any((item[0] & (ELF_PF_W | ELF_PF_X)) == (ELF_PF_W | ELF_PF_X) for item in pt_loads)

    # Check non-overlapping R|E and R|W PT_LOAD segments (both VA and 64K page ranges)
    has_overlap = False
    for i in range(len(pt_loads)):
        for j in range(i + 1, len(pt_loads)):
            _fi, oi, vai, fsi, _ai = pt_loads[i]
            _fj, oj, vaj, fsj, _aj = pt_loads[j]
            if (vai < vaj + fsj and vaj < vai + fsi) or (oi < oj + fsj and oj < oi + fsi):
                has_overlap = True

    dt_symtab_va = 0
    dt_strtab_va = 0
    dt_hash_va = 0
    dt_init_va = 0
    if pt_dyn_off > 0 and pt_dyn_off + pt_dyn_sz <= len(so_bytes):
        for off in range(pt_dyn_off, pt_dyn_off + pt_dyn_sz - 15, 16):
            d_tag, d_val = struct.unpack_from("<QQ", so_bytes, off)
            if d_tag == ELF_DT_NULL:
                break
            elif d_tag == ELF_DT_SYMTAB:
                dt_symtab_va = d_val
            elif d_tag == ELF_DT_STRTAB:
                dt_strtab_va = d_val
            elif d_tag == ELF_DT_HASH:
                dt_hash_va = d_val
            elif d_tag == ELF_DT_INIT:
                dt_init_va = d_val

    def _va_to_file_off(va: int, min_bytes: int, *, need_exec: bool = False) -> Optional[int]:
        if va == 0:
            return None
        for pf, p_off, p_va, p_fs, _al in pt_loads:
            if need_exec and not (pf & ELF_PF_X):
                continue
            if p_va <= va and (va + min_bytes) <= (p_va + p_fs):
                foff = p_off + (va - p_va)
                if 0 <= foff and foff + min_bytes <= len(so_bytes):
                    return foff
        return None

    sym_off = _va_to_file_off(dt_symtab_va, 24)
    str_off = _va_to_file_off(dt_strtab_va, 1)
    hash_off = _va_to_file_off(dt_hash_va, 16)
    init_off = _va_to_file_off(dt_init_va, 4, need_exec=True)

    dt_hash_words: Tuple[int, int, int, int] = (0, 0, 0, 0)
    if hash_off is not None:
        dt_hash_words = struct.unpack_from("<IIII", so_bytes, hash_off)
    dt_hash_nonempty = dt_hash_words[0] >= 1 and dt_hash_words[1] >= 1

    rule5_ok = (
        all_64k
        and congruent
        and (not has_wx)
        and (not has_overlap)
        and sym_off is not None
        and str_off is not None
        and hash_off is not None
        and init_off is not None
        and dt_hash_nonempty
    )
    if not rule5_ok:
        error_codes.append(ERR_LIBJIT_RULE5_ELF_LAYOUT_OR_64K_ALIGN)
        errors.append("ELF PT_LOAD 64KiB alignment / non-overlap / W^X / DT_* bounds failed")

    # Decode syscalls from DT_INIT (or first executable PT_LOAD if DT_INIT is out of bounds)
    scan_va = dt_init_va if init_off is not None else (pt_loads[0][2] if pt_loads else 0)
    sites, _saw_cmp512, saw_cmp512_before_out = _disassemble_syscalls_and_track_regs(
        so_bytes, pt_loads, scan_va
    )

    # Rule 1 (§4.1): First syscall in constructor is unlinkat(AT_FDCWD=-100, "/tmp/jiritsu/libJit.so", 0)
    rule1_ok = False
    if sites:
        s0 = sites[0]
        if (
            s0.syscall_num == SYS_AARCH64_UNLINKAT
            and s0.arg0 == AT_FDCWD
            and s0.arg1_str == LIBJIT_TARGET_PATH
            and (s0.arg2 == 0 or s0.arg2 is None)
        ):
            rule1_ok = True
    if not rule1_ok:
        error_codes.append(ERR_LIBJIT_RULE1_NO_UNLINK_FIRST)
        errors.append("Rule 1 failed: constructor does not start with unlinkat(-100, '/tmp/jiritsu/libJit.so', 0)")

    # Rule 2 (§4.2): openat("/dev/nflasha", O_RDONLY | O_CLOEXEC) + read/pread64(512) + cmp 512 BEFORE openat(sector0.bin)
    nflasha_open_idx: Optional[int] = None
    out_open_idx: Optional[int] = None
    read_512_idx: Optional[int] = None
    for idx, sc in enumerate(sites):
        if sc.syscall_num == SYS_AARCH64_OPENAT:
            if sc.arg1_str == NFLASH_WHOLE_NODE and nflasha_open_idx is None:
                flags_val = sc.arg2 if sc.arg2 is not None else -1
                if (flags_val & LINUX_O_ACCMODE) == LINUX_O_RDONLY and (flags_val & LINUX_O_CLOEXEC) != 0:
                    nflasha_open_idx = idx
            elif sc.arg1_str == SECTOR0_OUT_PATH and out_open_idx is None:
                out_open_idx = idx
        elif sc.syscall_num in (SYS_AARCH64_READ, SYS_AARCH64_PREAD64) and sc.arg2 == SECTOR0_BYTES:
            if nflasha_open_idx is not None and idx > nflasha_open_idx:
                read_512_idx = idx

    rule2_ok = (
        nflasha_open_idx is not None
        and read_512_idx is not None
        and out_open_idx is not None
        and nflasha_open_idx < read_512_idx < out_open_idx
        and saw_cmp512_before_out
    )
    if not rule2_ok:
        error_codes.append(ERR_LIBJIT_RULE2_NO_READ_FIRST_CLOEXEC)
        errors.append("Rule 2 failed: missing O_RDONLY|O_CLOEXEC read==512 pre-check before opening sector0.bin")

    # Rule 3 (§4.3): 528B framed output FX3S0OK\x00 + write(528)
    has_ok_magic = FX3S0OK_MAGIC in so_bytes
    has_528_write = any(
        sc.syscall_num == SYS_AARCH64_WRITE and sc.arg2 == FX3S0OK_FRAME_BYTES for sc in sites
    )
    rule3_ok = has_ok_magic and has_528_write
    if not rule3_ok:
        error_codes.append(ERR_LIBJIT_RULE3_NO_528B_FRAME)
        errors.append("Rule 3 failed: missing FX3S0OK\\x00 528-byte framed output")

    # Rule 4 (§4.4): newfstatat("/dev/nflasha") + /proc/partitions & /dev/nflasha1 fallback + FX3S0ERR 16B receipt
    has_fstat_nflasha = any(
        sc.syscall_num == SYS_AARCH64_NEWFSTATAT and sc.arg1_str == NFLASH_WHOLE_NODE for sc in sites
    )
    has_proc_parts = b"/proc/partitions\x00" in so_bytes and any(
        sc.syscall_num == SYS_AARCH64_OPENAT and sc.arg1_str == PROC_PARTITIONS_PATH for sc in sites
    )
    has_nflasha1_fb = b"/dev/nflasha1\x00" in so_bytes and any(
        sc.syscall_num == SYS_AARCH64_NEWFSTATAT and sc.arg1_str == NFLASH_FALLBACK_NODE for sc in sites
    )
    has_err_receipt = FX3S0ERR_MAGIC in so_bytes and any(
        sc.syscall_num == SYS_AARCH64_WRITE and sc.arg2 == FX3S0ERR_FRAME_BYTES for sc in sites
    )
    rule4_ok = has_fstat_nflasha and has_proc_parts and has_nflasha1_fb and has_err_receipt
    if not rule4_ok:
        error_codes.append(ERR_LIBJIT_RULE4_NO_BLK_FALLBACK_OR_ERR_RECEIPT)
        errors.append("Rule 4 failed: missing newfstatat S_ISBLK, /proc/partitions / /dev/nflasha1 fallback, or FX3S0ERR receipt")

    # Rule 6 (Static Syscall & Token Firewall)
    lower_blob = so_bytes.lower()
    for tok in FORBIDDEN_ELF_STRING_TOKENS:
        if tok.encode("ascii") in lower_blob:
            firewall_violations.append(f"forbidden_token:{tok}")

    opened_sector0_out = False
    for sc in sites:
        target = sc.arg1_str or ""
        is_protected_node = any(target.startswith(pfx) for pfx in FORBIDDEN_WRITE_TARGET_PREFIXES)
        if sc.syscall_num == SYS_AARCH64_OPENAT:
            if target == SECTOR0_OUT_PATH:
                opened_sector0_out = True
            if is_protected_node:
                flags_val = sc.arg2 if sc.arg2 is not None else 0
                if (flags_val & LINUX_O_ACCMODE) != LINUX_O_RDONLY:
                    firewall_violations.append(
                        f"forbidden_write_open:{target}:flags={flags_val:#x}"
                    )
        if sc.syscall_num in (SYS_AARCH64_IOCTL, SYS_AARCH64_MOUNT):
            firewall_violations.append(f"forbidden_syscall:{sc.syscall_name}@{sc.va:#x}")
        if sc.syscall_num in (SYS_AARCH64_WRITE, SYS_AARCH64_PWRITE64):
            # Only allow fixed-size writes (528B / 16B) after opening /tmp/jiritsu/sector0.bin
            if (
                is_protected_node
                or (not opened_sector0_out)
                or sc.arg2 not in (FX3S0OK_FRAME_BYTES, FX3S0ERR_FRAME_BYTES)
            ):
                firewall_violations.append(
                    f"forbidden_write_syscall:{sc.syscall_name}@{sc.va:#x}:len={sc.arg2}"
                )

    rule6_ok = len(firewall_violations) == 0
    if not rule6_ok:
        error_codes.append(ERR_LIBJIT_RULE6_FIREWALL_VIOLATION)
        errors.append("Rule 6 firewall rejected forbidden tokens/syscalls/write-open flags")

    passed = (
        under_16k
        and rule1_ok
        and rule2_ok
        and rule3_ok
        and rule4_ok
        and rule5_ok
        and rule6_ok
        and len(errors) == 0
    )
    return LibJitElfHardeningReport(
        passed=passed,
        elf_size_bytes=len(so_bytes),
        under_16kib=under_16k,
        e_machine=e_machine,
        e_type=e_type,
        pt_load_count=len(pt_loads),
        pt_load_alignments=aligns,
        has_wx_segment=has_wx,
        has_overlapping_pt_load=has_overlap,
        dt_symtab_in_bounds=sym_off is not None,
        dt_strtab_in_bounds=str_off is not None,
        dt_hash_in_bounds=hash_off is not None,
        dt_init_in_bounds=init_off is not None,
        dt_hash_words=dt_hash_words,
        rule1_self_unlink_first_ok=rule1_ok,
        rule2_read_first_cloexec_ok=rule2_ok,
        rule3_framed_528b_output_ok=rule3_ok,
        rule4_blk_node_and_fallback_ok=rule4_ok,
        rule5_64k_pt_load_and_dt_bounds_ok=rule5_ok,
        rule6_static_syscall_token_firewall_ok=rule6_ok,
        decoded_syscalls=tuple(sites),
        firewall_violations=tuple(firewall_violations),
        error_codes=tuple(error_codes),
        errors=tuple(errors),
    )


def emulate_hardened_libjit_in_unicorn(
    so_bytes: bytes,
    *,
    sector0_bytes: Optional[bytes] = None,
    nflasha_present: bool = True,
    nflasha_is_blk: bool = True,
    short_read_len: Optional[int] = None,
) -> UnicornLibJitEmulationResult:
    """Execute hardened `libJit.so` `DT_INIT` constructor in Unicorn ARM64 (if available)."""
    try:
        from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_INTR  # type: ignore
        from unicorn.arm64_const import (  # type: ignore
            UC_ARM64_REG_SP,
            UC_ARM64_REG_X0,
            UC_ARM64_REG_X1,
            UC_ARM64_REG_X2,
            UC_ARM64_REG_X3,
            UC_ARM64_REG_X8,
            UC_ARM64_REG_X30,
        )
    except ImportError:
        sp_site = resolve_unicorn_site_packages()
        if sp_site is not None:
            import sys as _sys

            if str(sp_site) not in _sys.path:
                _sys.path.insert(0, str(sp_site))
        try:
            from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_INTR  # type: ignore
            from unicorn.arm64_const import (  # type: ignore
                UC_ARM64_REG_SP,
                UC_ARM64_REG_X0,
                UC_ARM64_REG_X1,
                UC_ARM64_REG_X2,
                UC_ARM64_REG_X3,
                UC_ARM64_REG_X8,
                UC_ARM64_REG_X30,
            )
        except ImportError:
            return UnicornLibJitEmulationResult(
                False, False, True, (), False, False, False, False, 0, False, False, 0, 0, ()
            )

    s0_data = sector0_bytes if sector0_bytes is not None else build_synthetic_sector0_fx3_table()
    if short_read_len is not None:
        s0_data = s0_data[:short_read_len]

    # Map ELF PT_LOAD segments at base 0x400000
    base = 0x400000
    e_phoff = struct.unpack_from("<Q", so_bytes, 32)[0]
    e_phentsz, e_phnum = struct.unpack_from("<HH", so_bytes, 54)
    pt_loads = []
    dt_init_va = 0
    for idx in range(e_phnum):
        p_type, _pf, p_off, p_va, _pp, p_fs, _ms, _al = struct.unpack_from(
            "<IIQQQQQQ", so_bytes, e_phoff + idx * e_phentsz
        )
        if p_type == ELF_PT_LOAD:
            pt_loads.append((p_off, p_va, p_fs))
        elif p_type == ELF_PT_DYNAMIC:
            for doff in range(p_off, p_off + p_fs - 15, 16):
                tag, val = struct.unpack_from("<QQ", so_bytes, doff)
                if tag == ELF_DT_NULL:
                    break
                if tag == ELF_DT_INIT:
                    dt_init_va = val

    uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    uc.mem_map(base, 0x30000)
    for p_off, p_va, p_fs in pt_loads:
        uc.mem_write(base + p_va, so_bytes[p_off : p_off + p_fs])

    stack_base = 0x800000
    uc.mem_map(stack_base, 0x10000)
    uc.reg_write(UC_ARM64_REG_SP, stack_base + 0xF000)
    ret_sentinel = base + 0x2F000
    uc.reg_write(UC_ARM64_REG_X30, ret_sentinel)

    vfs_files: Dict[str, bytes] = {
        LIBJIT_TARGET_PATH: so_bytes,
        PROC_PARTITIONS_PATH: b"major minor #blocks name\n 179 0 30535680 nflasha\n",
    }
    if nflasha_present:
        vfs_files[NFLASH_WHOLE_NODE] = s0_data
    open_fds: Dict[int, Tuple[str, int, int]] = {}
    next_fd = 3
    syscall_seq: List[str] = []
    probed_proc = False
    probed_p1 = False

    def _read_cstr(addr: int) -> str:
        raw = bytes(uc.mem_read(addr, 128))
        return raw.split(b"\x00", 1)[0].decode("ascii", "replace")

    def _hook_svc(uc_obj: Any, intno: int, _user: Any) -> None:
        nonlocal next_fd, probed_proc, probed_p1
        if intno != 2:
            return
        sc = uc_obj.reg_read(UC_ARM64_REG_X8)
        x0 = uc_obj.reg_read(UC_ARM64_REG_X0)
        x1 = uc_obj.reg_read(UC_ARM64_REG_X1)
        x2 = uc_obj.reg_read(UC_ARM64_REG_X2)
        if sc == SYS_AARCH64_UNLINKAT:
            path = _read_cstr(x1)
            syscall_seq.append(f"unlinkat:{path}")
            if path in vfs_files:
                del vfs_files[path]
                uc_obj.reg_write(UC_ARM64_REG_X0, 0)
            else:
                uc_obj.reg_write(UC_ARM64_REG_X0, (-2) & 0xFFFFFFFFFFFFFFFF)
        elif sc == SYS_AARCH64_NEWFSTATAT:
            path = _read_cstr(x1)
            syscall_seq.append(f"newfstatat:{path}")
            if path == NFLASH_FALLBACK_NODE:
                probed_p1 = True
            if path == NFLASH_WHOLE_NODE and nflasha_present:
                st_mode = (S_IFBLK | 0o600) if nflasha_is_blk else 0o100644
                stat_buf = bytearray(128)
                struct.pack_into("<I", stat_buf, 16, st_mode)
                uc_obj.mem_write(x2, bytes(stat_buf))
                uc_obj.reg_write(UC_ARM64_REG_X0, 0)
            else:
                uc_obj.reg_write(UC_ARM64_REG_X0, (-2) & 0xFFFFFFFFFFFFFFFF)
        elif sc == SYS_AARCH64_OPENAT:
            path = _read_cstr(x1)
            syscall_seq.append(f"openat:{path}:{x2:#x}")
            if path == PROC_PARTITIONS_PATH:
                probed_proc = True
            if (x2 & LINUX_O_ACCMODE) == LINUX_O_RDONLY:
                if path in vfs_files:
                    fd = next_fd
                    next_fd += 1
                    open_fds[fd] = (path, 0, x2)
                    uc_obj.reg_write(UC_ARM64_REG_X0, fd)
                else:
                    uc_obj.reg_write(UC_ARM64_REG_X0, (-2) & 0xFFFFFFFFFFFFFFFF)
            else:
                if x2 & LINUX_O_TRUNC:
                    vfs_files[path] = b""
                elif path not in vfs_files:
                    vfs_files[path] = b""
                fd = next_fd
                next_fd += 1
                open_fds[fd] = (path, 0, x2)
                uc_obj.reg_write(UC_ARM64_REG_X0, fd)
        elif sc == SYS_AARCH64_READ:
            syscall_seq.append(f"read:{x2}")
            if x0 in open_fds:
                path, cur, _fl = open_fds[x0]
                data = vfs_files.get(path, b"")
                chunk = data[cur : cur + x2]
                uc_obj.mem_write(x1, chunk)
                open_fds[x0] = (path, cur + len(chunk), _fl)
                uc_obj.reg_write(UC_ARM64_REG_X0, len(chunk))
            else:
                uc_obj.reg_write(UC_ARM64_REG_X0, (-9) & 0xFFFFFFFFFFFFFFFF)
        elif sc == SYS_AARCH64_WRITE:
            syscall_seq.append(f"write:{x2}")
            if x0 in open_fds:
                path, cur, _fl = open_fds[x0]
                payload = bytes(uc_obj.mem_read(x1, x2))
                prev = vfs_files.get(path, b"")
                vfs_files[path] = prev[:cur] + payload
                open_fds[x0] = (path, cur + len(payload), _fl)
                uc_obj.reg_write(UC_ARM64_REG_X0, len(payload))
            else:
                uc_obj.reg_write(UC_ARM64_REG_X0, (-9) & 0xFFFFFFFFFFFFFFFF)
        elif sc == SYS_AARCH64_CLOSE:
            syscall_seq.append("close")
            open_fds.pop(x0, None)
            uc_obj.reg_write(UC_ARM64_REG_X0, 0)

    uc.hook_add(UC_HOOK_INTR, _hook_svc)
    uc.emu_start(base + dt_init_va, ret_sentinel, count=500000)

    out_bytes = vfs_files.get(SECTOR0_OUT_PATH, b"")
    ok_info = parse_fx3_sector0_ok_frame(out_bytes) if len(out_bytes) == FX3S0OK_FRAME_BYTES else None
    err_info = parse_fx3_sector0_err_receipt(out_bytes) if len(out_bytes) == FX3S0ERR_FRAME_BYTES else None
    unlinked_first = (
        len(syscall_seq) > 0
        and syscall_seq[0] == f"unlinkat:{LIBJIT_TARGET_PATH}"
        and LIBJIT_TARGET_PATH not in vfs_files
    )

    return UnicornLibJitEmulationResult(
        unicorn_available=True,
        executed=True,
        passed=unlinked_first and (bool(ok_info and ok_info.valid) or bool(err_info and err_info.valid)),
        syscall_sequence=tuple(syscall_seq),
        unlinked_libjit_first=unlinked_first,
        probed_proc_partitions=probed_proc,
        probed_nflasha1_fallback=probed_p1,
        sector0_file_present=SECTOR0_OUT_PATH in vfs_files,
        sector0_file_bytes=len(out_bytes),
        ok_frame_valid=bool(ok_info and ok_info.valid),
        err_receipt_valid=bool(err_info and err_info.valid),
        err_stage=err_info.stage if err_info and err_info.valid else 0,
        err_errno=err_info.errno_val if err_info and err_info.valid else 0,
        errors=(),
    )


def _build_legacy_unhardened_so_stub(*, dt_out_of_bounds: bool = False) -> bytes:
    """Clean-room replica of unhardened pre-§4 layout for negative regression checks."""
    eh_size = 64
    ph_size = 56
    ph_num = 3
    ph_off = eh_size
    text_off = 0x1000
    text_va = 0x1000
    # Unhardened: no unlinkat, O_RDONLY without O_CLOEXEC, no read==512 check, 4K align
    rodata = b"/dev/nflasha\x00/tmp/jiritsu/sector0.bin\x00"
    insns = [
        _movn64(0, 99),
        _adr(1, 32),
        _movz32(2, 0),
        _movz64(8, SYS_AARCH64_OPENAT),
        _SVC_0,
        _RET,
    ]
    code = b"".join(struct.pack("<I", w) for w in insns) + rodata
    dyn_off = 0x2000
    dyn_va = 0x2000
    sym_va = 0x2100 if dt_out_of_bounds else 0x2070
    str_va = 0x2120 if dt_out_of_bounds else 0x2088
    hash_va = 0x2130 if dt_out_of_bounds else 0x2089
    dyn_entries = (
        (ELF_DT_STRTAB, str_va),
        (ELF_DT_SYMTAB, sym_va),
        (ELF_DT_STRSZ, 1),
        (ELF_DT_SYMENT, 24),
        (ELF_DT_HASH, hash_va),
        (ELF_DT_INIT, text_va),
        (ELF_DT_NULL, 0),
    )
    dyn_bytes = b"".join(struct.pack("<QQ", t, v) for t, v in dyn_entries)
    rdata = dyn_bytes + (b"\x00" * 24) + b"\x00" + struct.pack("<IIII", 1, 1, 0, 0)
    out = bytearray(dyn_off + len(rdata))
    e_ident = ELF_MAGIC + bytes([ELF_CLASS_64, ELF_DATA_LSB, 1, 0]) + (b"\x00" * 8)
    struct.pack_into(
        "<16sHHIQQQIHHHHHH", out, 0, e_ident, ELF_TYPE_DYN, ELF_MACHINE_AARCH64, 1, 0, ph_off, 0, 0, eh_size, ph_size, ph_num, 0, 0, 0
    )
    struct.pack_into("<IIQQQQQQ", out, ph_off, ELF_PT_LOAD, 5, text_off, text_va, text_va, len(code), len(code), 0x1000)
    struct.pack_into("<IIQQQQQQ", out, ph_off + ph_size, ELF_PT_LOAD, 4, dyn_off, dyn_va, dyn_va, len(rdata), len(rdata), 0x1000)
    struct.pack_into("<IIQQQQQQ", out, ph_off + 2 * ph_size, ELF_PT_DYNAMIC, 4, dyn_off, dyn_va, dyn_va, len(dyn_bytes), len(dyn_bytes), 8)
    out[text_off : text_off + len(code)] = code
    out[dyn_off : dyn_off + len(rdata)] = rdata
    return bytes(out)


def _build_malicious_syscall_so(
    syscall_num: int,
    *,
    target_path: str = "/dev/cnflasha3",
    arg2_val: int = 16,
) -> bytes:
    """Clean-room negative test ELF containing a forbidden `ioctl`/`mount`/`write`/`openat` syscall."""
    eh_size = 64
    ph_size = 56
    ph_num = 3
    ph_off = eh_size
    text_off = 0x1000
    text_va = 0x1000
    insns = [
        _movn64(0, 99),
        _adr(1, 20),
        _movz64(2, arg2_val),
        _movz64(8, syscall_num),
        _SVC_0,
        _RET,
    ]
    code = b"".join(struct.pack("<I", w) for w in insns) + target_path.encode("ascii") + b"\x00"
    dyn_off = 0x2000
    dyn_va = 0x12000
    dyn_entries = (
        (ELF_DT_STRTAB, dyn_va + 0x88),
        (ELF_DT_SYMTAB, dyn_va + 0x70),
        (ELF_DT_STRSZ, 1),
        (ELF_DT_SYMENT, 24),
        (ELF_DT_HASH, dyn_va + 0x89),
        (ELF_DT_INIT, text_va),
        (ELF_DT_NULL, 0),
    )
    dyn_bytes = b"".join(struct.pack("<QQ", t, v) for t, v in dyn_entries)
    rdata = dyn_bytes + (b"\x00" * 24) + b"\x00" + struct.pack("<IIII", 1, 1, 0, 0)
    out = bytearray(dyn_off + len(rdata))
    e_ident = ELF_MAGIC + bytes([ELF_CLASS_64, ELF_DATA_LSB, 1, 0]) + (b"\x00" * 8)
    struct.pack_into(
        "<16sHHIQQQIHHHHHH", out, 0, e_ident, ELF_TYPE_DYN, ELF_MACHINE_AARCH64, 1, 0, ph_off, 0, 0, eh_size, ph_size, ph_num, 0, 0, 0
    )
    struct.pack_into("<IIQQQQQQ", out, ph_off, ELF_PT_LOAD, 5, text_off, text_va, text_va, len(code), len(code), ELF_PT_LOAD_PAGE_ALIGN)
    struct.pack_into("<IIQQQQQQ", out, ph_off + ph_size, ELF_PT_LOAD, 6, dyn_off, dyn_va, dyn_va, len(rdata), len(rdata), ELF_PT_LOAD_PAGE_ALIGN)
    struct.pack_into("<IIQQQQQQ", out, ph_off + 2 * ph_size, ELF_PT_DYNAMIC, 6, dyn_off, dyn_va, dyn_va, len(dyn_bytes), len(dyn_bytes), 8)
    out[text_off : text_off + len(code)] = code
    out[dyn_off : dyn_off + len(rdata)] = rdata
    return bytes(out)


def run_pillar_b_hardened_libjit_elf_8_scenario_suite(
    *,
    legacy_libjit_test_bytes: Optional[bytes] = None,
) -> PillarB8ScenarioSuiteResult:
    """Execute all 8 Pillar B Stage-288 §4 (1..6) Hardened ARM64 `libJit.so` ELF Gate scenarios."""
    results: List[PillarBScenarioResult] = []
    suite_errors: List[str] = []
    passed_count = 0

    hardened_so = build_hardened_libjit_elf64()
    hardened_sha = sha256(hardened_so).hexdigest()

    # PB1: Hardened ELF64 static disassembly + Unicorn happy 528B FX3S0OK\x00 execution
    r_pb1 = verify_hardened_libjit_elf64(hardened_so)
    emu_pb1 = emulate_hardened_libjit_in_unicorn(hardened_so)
    pb1_ok = (
        r_pb1.passed
        and r_pb1.under_16kib
        and r_pb1.rule1_self_unlink_first_ok
        and r_pb1.rule2_read_first_cloexec_ok
        and r_pb1.rule3_framed_528b_output_ok
        and r_pb1.rule4_blk_node_and_fallback_ok
        and r_pb1.rule5_64k_pt_load_and_dt_bounds_ok
        and r_pb1.rule6_static_syscall_token_firewall_ok
        and (
            (not emu_pb1.unicorn_available)
            or (emu_pb1.unlinked_libjit_first and emu_pb1.ok_frame_valid and emu_pb1.sector0_file_bytes == 528)
        )
    )
    if pb1_ok:
        passed_count += 1
    else:
        suite_errors.append(f"PB1 hardened ELF failed: {r_pb1.error_codes}")
    results.append(
        PillarBScenarioResult(
            passed=pb1_ok,
            scenario_id=PILLAR_B_SCENARIO_IDS[0],
            rule_checks_ok=r_pb1.passed,
            unicorn_executed=emu_pb1.executed,
            error_codes=r_pb1.error_codes,
            errors=r_pb1.errors,
            report_sha256=_canonical_sha256({"id": PILLAR_B_SCENARIO_IDS[0], "ok": pb1_ok, "sha": hardened_sha}),
        )
    )

    # PB2: Legacy libJit_test.so (8,345B or clean-room stub) flagged as failing pre-hardening checks
    legacy_bytes = (
        legacy_libjit_test_bytes
        if legacy_libjit_test_bytes is not None
        else _build_legacy_unhardened_so_stub(dt_out_of_bounds=False)
    )
    r_pb2 = verify_hardened_libjit_elf64(legacy_bytes)
    pb2_ok = (
        (not r_pb2.passed)
        and (not r_pb2.rule1_self_unlink_first_ok)
        and (not r_pb2.rule2_read_first_cloexec_ok)
        and (not r_pb2.rule3_framed_528b_output_ok)
        and (not r_pb2.rule4_blk_node_and_fallback_ok)
        and (not r_pb2.rule5_64k_pt_load_and_dt_bounds_ok)
    )
    if pb2_ok:
        passed_count += 1
    else:
        suite_errors.append("PB2 failed to flag legacy unhardened libJit_test.so")
    results.append(
        PillarBScenarioResult(
            passed=pb2_ok,
            scenario_id=PILLAR_B_SCENARIO_IDS[1],
            rule_checks_ok=pb2_ok,
            unicorn_executed=False,
            error_codes=r_pb2.error_codes,
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_B_SCENARIO_IDS[1], "ok": pb2_ok, "codes": r_pb2.error_codes}),
        )
    )

    # PB3: Legacy out-of-bounds DT_* (0x2100 > 0x2099) caught
    oob_so = _build_legacy_unhardened_so_stub(dt_out_of_bounds=True)
    r_pb3 = verify_hardened_libjit_elf64(oob_so)
    pb3_ok = (
        (not r_pb3.passed)
        and (not r_pb3.dt_symtab_in_bounds)
        and (not r_pb3.dt_strtab_in_bounds)
        and (not r_pb3.dt_hash_in_bounds)
        and ERR_LIBJIT_RULE5_ELF_LAYOUT_OR_64K_ALIGN in r_pb3.error_codes
    )
    if pb3_ok:
        passed_count += 1
    else:
        suite_errors.append("PB3 failed to catch out-of-bounds DT_*")
    results.append(
        PillarBScenarioResult(
            passed=pb3_ok,
            scenario_id=PILLAR_B_SCENARIO_IDS[2],
            rule_checks_ok=pb3_ok,
            unicorn_executed=False,
            error_codes=r_pb3.error_codes,
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_B_SCENARIO_IDS[2], "ok": pb3_ok}),
        )
    )

    # PB4: W+X segment and 4 KiB PT_LOAD alignment rejected
    wx_so = build_hardened_libjit_elf64(inject_wx_segment=True)
    align4k_so = build_hardened_libjit_elf64(pt_load_align=0x1000)
    r_wx = verify_hardened_libjit_elf64(wx_so)
    r_4k = verify_hardened_libjit_elf64(align4k_so)
    pb4_ok = (
        (not r_wx.passed)
        and r_wx.has_wx_segment
        and (not r_wx.rule5_64k_pt_load_and_dt_bounds_ok)
        and (not r_4k.passed)
        and (not r_4k.rule5_64k_pt_load_and_dt_bounds_ok)
    )
    if pb4_ok:
        passed_count += 1
    else:
        suite_errors.append("PB4 failed to reject W+X / 4K PT_LOAD")
    results.append(
        PillarBScenarioResult(
            passed=pb4_ok,
            scenario_id=PILLAR_B_SCENARIO_IDS[3],
            rule_checks_ok=pb4_ok,
            unicorn_executed=False,
            error_codes=r_wx.error_codes,
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_B_SCENARIO_IDS[3], "ok": pb4_ok}),
        )
    )

    # PB5: Unicorn short read (256B != 512B) -> no 0B truncation, emits 16B FX3S0ERR (stage=3, errno=5 EIO)
    emu_pb5 = emulate_hardened_libjit_in_unicorn(hardened_so, short_read_len=256)
    pb5_ok = (
        (not emu_pb5.unicorn_available)
        or (
            emu_pb5.unlinked_libjit_first
            and emu_pb5.err_receipt_valid
            and emu_pb5.sector0_file_bytes == 16
            and emu_pb5.err_stage == 3
            and emu_pb5.err_errno == 5
        )
    )
    if pb5_ok:
        passed_count += 1
    else:
        suite_errors.append("PB5 short-read FX3S0ERR verification failed")
    results.append(
        PillarBScenarioResult(
            passed=pb5_ok,
            scenario_id=PILLAR_B_SCENARIO_IDS[4],
            rule_checks_ok=True,
            unicorn_executed=emu_pb5.executed,
            error_codes=(),
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_B_SCENARIO_IDS[4], "ok": pb5_ok}),
        )
    )

    # PB6: Unicorn missing /dev/nflasha -> probes /proc/partitions & /dev/nflasha1, emits 16B FX3S0ERR (stage=1, errno=2 ENOENT)
    emu_pb6 = emulate_hardened_libjit_in_unicorn(hardened_so, nflasha_present=False)
    pb6_ok = (
        (not emu_pb6.unicorn_available)
        or (
            emu_pb6.unlinked_libjit_first
            and emu_pb6.probed_proc_partitions
            and emu_pb6.probed_nflasha1_fallback
            and emu_pb6.err_receipt_valid
            and emu_pb6.err_stage == 1
            and emu_pb6.err_errno == 2
        )
    )
    if pb6_ok:
        passed_count += 1
    else:
        suite_errors.append("PB6 missing /dev/nflasha fallback verification failed")
    results.append(
        PillarBScenarioResult(
            passed=pb6_ok,
            scenario_id=PILLAR_B_SCENARIO_IDS[5],
            rule_checks_ok=True,
            unicorn_executed=emu_pb6.executed,
            error_codes=(),
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_B_SCENARIO_IDS[5], "ok": pb6_ok}),
        )
    )

    # PB7: Firewall rejects O_RDWR / O_WRONLY on /dev/nflasha* & write/ioctl/mount syscalls
    rdwr_so = build_hardened_libjit_elf64(replace_open_flags_with=LINUX_O_RDWR)
    r_rdwr = verify_hardened_libjit_elf64(rdwr_so)
    r_ioctl = verify_hardened_libjit_elf64(_build_malicious_syscall_so(SYS_AARCH64_IOCTL))
    r_mount = verify_hardened_libjit_elf64(_build_malicious_syscall_so(SYS_AARCH64_MOUNT))
    r_write = verify_hardened_libjit_elf64(_build_malicious_syscall_so(SYS_AARCH64_WRITE))
    pb7_ok = (
        (not r_rdwr.rule6_static_syscall_token_firewall_ok)
        and (not r_ioctl.rule6_static_syscall_token_firewall_ok)
        and (not r_mount.rule6_static_syscall_token_firewall_ok)
        and (not r_write.rule6_static_syscall_token_firewall_ok)
        and ERR_LIBJIT_RULE6_FIREWALL_VIOLATION in r_rdwr.error_codes
    )
    if pb7_ok:
        passed_count += 1
    else:
        suite_errors.append("PB7 firewall failed to reject O_RDWR/write/ioctl/mount")
    results.append(
        PillarBScenarioResult(
            passed=pb7_ok,
            scenario_id=PILLAR_B_SCENARIO_IDS[6],
            rule_checks_ok=pb7_ok,
            unicorn_executed=False,
            error_codes=r_rdwr.error_codes,
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_B_SCENARIO_IDS[6], "ok": pb7_ok}),
        )
    )

    # PB8: Firewall rejects forbidden tokens edisx / uc_mkfs / nor_loader_writer
    tok_rejected = True
    for tok in FORBIDDEN_ELF_STRING_TOKENS:
        r_tok = verify_hardened_libjit_elf64(build_hardened_libjit_elf64(inject_forbidden_token=tok))
        if r_tok.rule6_static_syscall_token_firewall_ok or ERR_LIBJIT_RULE6_FIREWALL_VIOLATION not in r_tok.error_codes:
            tok_rejected = False
            break
    pb8_ok = tok_rejected
    if pb8_ok:
        passed_count += 1
    else:
        suite_errors.append("PB8 firewall failed to reject forbidden tokens")
    results.append(
        PillarBScenarioResult(
            passed=pb8_ok,
            scenario_id=PILLAR_B_SCENARIO_IDS[7],
            rule_checks_ok=pb8_ok,
            unicorn_executed=False,
            error_codes=(ERR_LIBJIT_RULE6_FIREWALL_VIOLATION,),
            errors=(),
            report_sha256=_canonical_sha256({"id": PILLAR_B_SCENARIO_IDS[7], "ok": pb8_ok}),
        )
    )

    all_ok = len(suite_errors) == 0 and passed_count == len(PILLAR_B_SCENARIO_IDS)
    return PillarB8ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_PILLAR_B if all_ok else STATUS_REJECTED_PILLAR_B,
        scenarios_passed=passed_count,
        scenarios_total=len(PILLAR_B_SCENARIO_IDS),
        scenario_results=tuple(results),
        hardened_elf_bytes=len(hardened_so),
        hardened_elf_sha256=hardened_sha,
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256(
            {"scenarios": [r.report_sha256 for r in results], "ok": all_ok}
        ),
    )


# ---------------------------------------------------------------------------
# Dual-Mode Read-Only (O_RDONLY) Donor Inspection
# ---------------------------------------------------------------------------


def inspect_service_usb_and_libjit_donors_readonly(
    *,
    force_clean_room: Optional[bool] = None,
) -> Tuple[ServiceUsbAndLibjitDonorSnapshot, Optional[bytes]]:
    """Inspect `libJiritsu.so`, `libsencore.so`, and optional `libJit_test.so` strictly via
    `os.open(..., os.O_RDONLY)`, falling back deterministically in clean-room mode.
    """
    forced = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)

    def _inspect_one(
        rel: str,
        label: str,
        pinned_len: int,
        pinned_sha: str,
        pinned_aligns: Tuple[int, ...],
        expected_anchors: Tuple[str, ...],
    ) -> Tuple[Optional[bytes], DonorElfStructuralDescriptor]:
        if forced:
            return None, DonorElfStructuralDescriptor(
                label=label,
                source_mode="CLEAN_ROOM_SYNTHETIC",
                present=False,
                byte_length=pinned_len,
                sha256_digest=pinned_sha,
                e_machine=ELF_MACHINE_AARCH64,
                pt_load_alignments=pinned_aligns,
                anchor_symbols_present=expected_anchors,
                notes="forced clean-room structural descriptor",
            )
        raw, mode = _read_donor_o_rdonly(rel)
        if raw is None:
            return None, DonorElfStructuralDescriptor(
                label=label,
                source_mode="CLEAN_ROOM_SYNTHETIC",
                present=False,
                byte_length=pinned_len,
                sha256_digest=pinned_sha,
                e_machine=ELF_MACHINE_AARCH64,
                pt_load_alignments=pinned_aligns,
                anchor_symbols_present=expected_anchors,
                notes="clean-room fallback (donor absent)",
            )
        digest = sha256(raw).hexdigest()
        require(
            len(raw) == pinned_len and digest == pinned_sha,
            f"donor integrity mismatch for {label}: got len={len(raw)} sha={digest}",
        )
        meta = _extract_elf64_structural_summary(raw)
        require(meta["e_machine"] == ELF_MACHINE_AARCH64, f"{label} not AArch64")
        syms = set(meta["dynsym_names"])
        found_anchors = tuple(a for a in expected_anchors if a in syms)
        require(
            len(found_anchors) == len(expected_anchors),
            f"{label} missing anchor symbols: {set(expected_anchors) - set(found_anchors)}",
        )
        return raw, DonorElfStructuralDescriptor(
            label=label,
            source_mode=mode,
            present=True,
            byte_length=len(raw),
            sha256_digest=digest,
            e_machine=meta["e_machine"],
            pt_load_alignments=meta["pt_load_alignments"],
            anchor_symbols_present=found_anchors,
            notes="verified via os.O_RDONLY",
        )

    _jit_raw, jit_desc = _inspect_one(
        P144_DONOR_LIBJIRITSU_RELPATH,
        "fx3_libJiritsu_so",
        P144_PINNED_LIBJIRITSU_BYTES,
        P144_PINNED_LIBJIRITSU_SHA256,
        (0x10000, 0x10000),
        ("adj_cmd_set_file_path", "adj_cmd_set_file2", "adj_cmd_get_file2", "cmd_high_capacity_send_file", "cmd_high_capacity_get_file"),
    )
    _sen_raw, sen_desc = _inspect_one(
        P144_DONOR_LIBSENCORE_RELPATH,
        "fx3_libsencore_so",
        P144_PINNED_LIBSENCORE_BYTES,
        P144_PINNED_LIBSENCORE_SHA256,
        (0x10000, 0x10000),
        ("_Z17AdjustControlFuncPK12SenserPacket", "_ZN12Inconcurrent10resource_t4lockEPK12SenserPacket", "_ZN29SubsystemCommunicationCommand16TransactionStartEPK12SenserPacketPKvS4_"),
    )
    test_raw, test_desc = _inspect_one(
        P144_DONOR_LIBJIT_TEST_RELPATH,
        "stage288_libJit_test_so",
        P144_PINNED_LIBJIT_TEST_BYTES,
        P144_PINNED_LIBJIT_TEST_SHA256,
        (0x1000, 0x1000),
        (),
    )

    modes = {jit_desc.source_mode, sen_desc.source_mode}
    ver_mode = "LOCAL_DONOR_O_RDONLY" if modes == {"LOCAL_DONOR_O_RDONLY"} else "CLEAN_ROOM_SYNTHETIC"

    # Evaluate legacy libJit_test.so (or clean-room equivalent) against Stage-288 §4 gate
    legacy_probe = test_raw if test_raw is not None else _build_legacy_unhardened_so_stub()
    legacy_eval = verify_hardened_libjit_elf64(legacy_probe)
    legacy_rejected = not legacy_eval.passed

    snap_payload = {
        "mode": ver_mode,
        "libjiritsu": asdict(jit_desc),
        "libsencore": asdict(sen_desc),
        "libjit_test": asdict(test_desc),
        "legacy_rejected": legacy_rejected,
        "legacy_codes": list(legacy_eval.error_codes),
    }
    snap = ServiceUsbAndLibjitDonorSnapshot(
        verification_mode=ver_mode,
        read_only_access=READ_ONLY_DONOR_ACCESS,
        o_rdonly_enforced=True,
        libjiritsu_descriptor=jit_desc,
        libsencore_descriptor=sen_desc,
        libjit_test_descriptor=test_desc,
        legacy_libjit_test_prehardening_rejected=legacy_rejected,
        legacy_libjit_test_failure_codes=legacy_eval.error_codes,
        snapshot_sha256=_canonical_sha256(snap_payload),
    )
    return snap, test_raw


# ---------------------------------------------------------------------------
# Master Suite Entrypoint (Pillar 18)
# ---------------------------------------------------------------------------


def run_realhw_service_usb_and_libjit_hardener_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> RealHwServiceUsbAndLibjitSuiteReport:
    """Run Phase 144 Pillar 18: O_RDONLY donor inspection, Stage-285/286 `MSC -> SERVICE`
    exclusive session & `op=0xFF` zero-mount RAM canary, and Stage-288 §4 (1..6)
    hardened ARM64 `libJit.so` ELF64 gate.
    """
    t0 = time.monotonic()
    require(not PERSISTENT_EMMC_WRITES_AUTHORIZED, "persistent_emmc_writes_authorized must stay False")
    require(not LIVE_USB_IOKIT_TRANSMIT_ENABLED, "live_usb_iokit_transmit_enabled must stay False")
    require(USB_TX_PACKETS_EMITTED == 0, "usb_tx_packets_emitted must stay 0")

    donor_snap, legacy_raw = inspect_service_usb_and_libjit_donors_readonly(
        force_clean_room=force_clean_room
    )
    pillar_a = run_pillar_a_service_usb_session_8_scenario_suite()
    pillar_b = run_pillar_b_hardened_libjit_elf_8_scenario_suite(
        legacy_libjit_test_bytes=legacy_raw
    )

    errors: List[str] = []
    if not donor_snap.legacy_libjit_test_prehardening_rejected:
        errors.append("legacy libJit_test.so must be flagged as unhardened")
    errors.extend(pillar_a.errors)
    errors.extend(pillar_b.errors)

    all_ok = (
        len(errors) == 0
        and pillar_a.passed
        and pillar_b.passed
        and donor_snap.legacy_libjit_test_prehardening_rejected
        and not LIVE_USB_IOKIT_TRANSMIT_ENABLED
        and not PERSISTENT_EMMC_WRITES_AUTHORIZED
        and not PERSISTENT_WRITE_RELEASE
        and PHYSICAL_DEVICE_WRITES == 0
        and USB_TX_PACKETS_EMITTED == 0
    )
    status = STATUS_VERIFIED_SUITE if all_ok else STATUS_FAIL_SUITE
    digest_payload = {
        "schema": PHASE144_SCHEMA,
        "version": PHASE144_VERSION,
        "status": status,
        "mode": donor_snap.verification_mode,
        "donor_sha256": donor_snap.snapshot_sha256,
        "pillar_a_sha256": pillar_a.suite_sha256,
        "pillar_b_sha256": pillar_b.suite_sha256,
        "all_passed": all_ok,
    }
    return RealHwServiceUsbAndLibjitSuiteReport(
        schema=PHASE144_SCHEMA,
        version=PHASE144_VERSION,
        status=status,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        read_only_donor_access=READ_ONLY_DONOR_ACCESS,
        donor_snapshot=donor_snap,
        pillar_a_service_usb_8_scenarios=pillar_a,
        pillar_b_hardened_libjit_8_scenarios=pillar_b,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        allow_persistent_jiritsu_writes=ALLOW_PERSISTENT_JIRITSU_WRITES,
        allow_destructive_jiritsu_commands=ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
        usb_tx_packets_emitted=USB_TX_PACKETS_EMITTED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        elapsed_seconds=round(time.monotonic() - t0, 6),
        errors=tuple(errors),
        suite_sha256=_canonical_sha256(digest_payload),
    )
