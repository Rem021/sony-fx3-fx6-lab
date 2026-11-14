#!/usr/bin/env python3
"""Phase 24 — Heterogeneous Dual-ISA (`CXD90057` AArch64 AP <-> `CXD90058` ARM32 Thumb-2 Stock-CP) `IVSHMEM` Bridge.

Implements a deterministic, clean-room-compliant Dual-ISA Unicorn co-emulation engine and
QEMU `ivshmem-doorbell` / `ivshmem-flat` MMIO bridge inside `outputs/fx3-vm/`:

1. **Standard QEMU `IVSHMEM` Register File (`INTRMASK`, `INTRSTATUS`, `IVPOSITION`, `DOORBELL`)**:
   - Peer 0 (`AP Mira`, `CXD90057`, `UC_ARCH_ARM64`): `ivshmem-doorbell` PCI BAR0 MMIO @ `0x1000_0000`,
     shared-memory BAR2 @ `0x1010_0000`.
   - Peer 1 (`Stock-CP Cetus`, `CXD90058`, `UC_ARCH_ARM | UC_MODE_THUMB`): `ivshmem-flat` MMIO @ `0x6780_0000`,
     shared-memory RAM @ `0x6790_0000`, unmodified FX3 v7.02 `cpapp-b.bin` mapped read-only/exec
     (`UC_PROT_READ | UC_PROT_EXEC`) at `0x0010_8000` (`cp_mutation_bytes == 0`).
   - Zero-copy shared physical RAM via Unicorn `mem_map_ptr()` over a single `ctypes` buffer.

2. **Real Dual-ISA Machine-Code Execution (`AArch64` <-> `Doorbell` <-> `Thumb-2` <-> `Doorbell` <-> `AArch64`)**:
   - Peer 0 executes real AArch64 instructions (`ap_uipc_submit` & `ap_uipc_poll_rx`) implementing:
     - `P11` AP-side filter: intercepts `0x92d2091c` (`/dev/rtc0`) and `0x91db059b` (Smart Handle) locally
       so neither ever enters the `IVSHMEM` TX ring or leaks to Stock-CP.
     - `0x92840747` UIPC BB framing: pushes requests into `AP->CP TX Ring` (16x256B), checks backpressure,
       and writes `(1 << 16) | 0` to `DOORBELL` (`0x1000_000C`).
   - Peer 1 executes real ARM32 Thumb-2 instructions (`cp_ivshmem_irq_handler`) implementing:
     - `IVPOSITION` & `INTRSTATUS` clear-on-read IRQ acknowledgement.
     - Direct in-memory verification of mapped `cpapp-b.bin` (`0x0010_800c` load base literal,
       Thumb-2 `MOVW/MOVT` `0x92840747`, and `0x1000`/`0x8000` completion constants).
     - TX ring parsing, malformed-frame rejection, `33^3` 3D LUT DMA (`0x0165`) window check
       (`> 0xbb80` threshold), 5-axis IBIS center-lock state maintenance, `opcode | 0x8000`
       completion packet emission into `CP->AP RX Ring`, and `DOORBELL` `(0 << 16) | 0` back to Peer 0.

3. **Dual-Mode Clean-Room & Local Donor Support**:
   - Opens all donor binaries (`fx3_cpapp`, `fx6_appfw`, `fx6_libosal_uipc`) strictly `os.O_RDONLY`.
   - Uses C-level `bytes.find` scanning (< 0.3s total).
   - Automatically uses synthetic `[TOMCO]` + `AArch64` + `ARM32 Thumb-2` fixtures when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor binaries are absent.

4. **External Dual-QEMU CLI Topology Spec**:
   - `build_dual_qemu_ivshmem_topology_spec()` produces validated `ivshmem-server`,
     `qemu-system-aarch64 -device ivshmem-doorbell`, and `qemu-system-arm -cpu cortex-r5 -device ivshmem-flat`
     command/MMIO specifications for external dual-process runs.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import ctypes
import hashlib
import json
import os
import site
import struct
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


def _ensure_unicorn_available() -> None:
    try:
        import unicorn  # noqa: F401
        return
    except ImportError:
        pass
    candidates: List[Path] = []
    env_site = os.environ.get("FX3_FX6_UNICORN_SITE", "").strip() or os.environ.get("UNICORN_SITE_PACKAGES", "").strip()
    if env_site:
        candidates.append(Path(os.path.expanduser(env_site)))
    try:
        us = site.getusersitepackages()
        if us:
            candidates.append(Path(us))
    except Exception:
        pass
    try:
        for sp in site.getsitepackages():
            candidates.append(Path(sp))
    except Exception:
        pass
    for cand in candidates:
        if (cand / "unicorn" / "__init__.py").is_file() or (cand / "unicorn").is_dir():
            if str(cand) not in sys.path:
                sys.path.append(str(cand))
            return


_ensure_unicorn_available()
import unicorn as U  # noqa: E402
from unicorn import arm64_const as A64  # noqa: E402
from unicorn import arm_const as A32  # noqa: E402


# ---------------------------------------------------------------------------
# Phase 24 Schema & Stage-A Stock-CP Redline Locks
# ---------------------------------------------------------------------------

PHASE_24_SCHEMA = "phase24_dual_isa_ivshmem_bridge_v1"
PHASE_24_VERSION = "24.0.0"

P8_CP_MUTATION_FORBIDDEN = True
CP_MUTATION_BYTES = 0

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"


# ---------------------------------------------------------------------------
# QEMU `ivshmem-doorbell` / `ivshmem-flat` MMIO Register & Memory Architecture
# ---------------------------------------------------------------------------

IVSHMEM_REG_INTRMASK = 0x00
IVSHMEM_REG_INTRSTATUS = 0x04
IVSHMEM_REG_IVPOSITION = 0x08
IVSHMEM_REG_DOORBELL = 0x0C
IVSHMEM_MMIO_SPAN = 0x1000

PEER_ID_AP_MIRA = 0
PEER_ID_CP_CETUS = 1

IVSHMEM_AP_MMIO_BASE = 0x1000_0000
IVSHMEM_AP_SHM_BASE = 0x1010_0000
IVSHMEM_CP_MMIO_BASE = 0x6780_0000
IVSHMEM_CP_SHM_BASE = 0x6790_0000
IVSHMEM_SHM_SIZE = 0x0010_0000  # 1 MiB

# Guest code/stack/flash map
AP_CODE_BASE = 0x0400_0000
AP_CODE_SIZE = 0x0001_0000
AP_SUBMIT_ENTRY = AP_CODE_BASE + 0x0000
AP_POLL_RX_ENTRY = AP_CODE_BASE + 0x0400
AP_CODE_EXIT = AP_CODE_BASE + 0x0FF0
AP_STACK_BASE = 0x7000_0000
AP_STACK_SIZE = 0x0001_0000
AP_SCRATCH_BASE = 0x7100_0000
AP_SCRATCH_SIZE = 0x0001_0000

CP_ISR_BASE = 0x0008_0000
CP_ISR_SIZE = 0x0001_0000
CP_ISR_ENTRY = CP_ISR_BASE + 0x0000
CP_ISR_EXIT = CP_ISR_BASE + 0x0FF0
CP_LOAD_BASE = 0x0010_8000  # Unmodified FX3 cpapp-b.bin load base
CP_SELF_REF_LIT = 0x0010_800C
CP_STACK_BASE = 0x6800_0000
CP_STACK_SIZE = 0x0001_0000
CP_SCRATCH_BASE = 0x6810_0000
CP_SCRATCH_SIZE = 0x0001_0000

# Shared-memory IPC control & ring offsets (relative to SHM base)
SHM_MAGIC = 0x49565348  # "IVSH"
SHM_VERSION = 0x00010018

SHM_CTRL_OFFSET = 0x0000
SHM_OFF_MAGIC = 0x00
SHM_OFF_VERSION = 0x04
SHM_OFF_TX_HEAD = 0x08
SHM_OFF_TX_TAIL = 0x0C
SHM_OFF_TX_CAP = 0x10
SHM_OFF_TX_SLOT_BYTES = 0x14
SHM_OFF_RX_HEAD = 0x18
SHM_OFF_RX_TAIL = 0x1C
SHM_OFF_RX_CAP = 0x20
SHM_OFF_RX_SLOT_BYTES = 0x24
SHM_OFF_P11_RTC_CNT = 0x28
SHM_OFF_P11_HANDLE_CNT = 0x2C
SHM_OFF_CP_IRQ_CNT = 0x30
SHM_OFF_AP_IRQ_CNT = 0x34
SHM_OFF_IBIS_CENTER_LOCK = 0x38
SHM_OFF_IBIS_MODE = 0x3C
SHM_OFF_LUT_DMA_ACK_CNT = 0x40
SHM_OFF_LUT_DMA_LAST_BYTES = 0x44
SHM_OFF_LAST_ERROR = 0x48
SHM_OFF_MALFORM_DROP_CNT = 0x4C
SHM_OFF_BACKPRESSURE_CNT = 0x50
SHM_OFF_CP_VERIFIED_QUEUE = 0x54
SHM_OFF_CP_VERIFIED_COMP_IMM = 0x58
SHM_OFF_CP_VERIFIED_BASE = 0x5C
SHM_OFF_AP_RTC_VALID = 0x60

SHM_TX_RING_OFFSET = 0x1000
SHM_RX_RING_OFFSET = 0x2000
SHM_RING_CAPACITY = 16
SHM_SLOT_BYTES = 256
SHM_SLOT_HDR_BYTES = 16
SHM_MAX_PAYLOAD_BYTES = SHM_SLOT_BYTES - SHM_SLOT_HDR_BYTES  # 240 B

SHM_DMA_LUT_OFFSET = 0x10000
SHM_DMA_LUT_WINDOW_BYTES = 0x50000  # 320 KiB

# UIPC Queues, Opcodes, & Imaging Constants
UIPC_BB_TARGET_QUEUE = 0x92840747
RTC_QUEUE_ID = 0x92D2091C
HANDLE_QUEUE_ID = 0x91DB059B

UIPC_BB_MAGIC = 0x200D
UIPC_BB_FLAGS = 0x8001
UIPC_BB_COMPLETION_BIT = 0x8000
UIPC_BB_HW_COMPLETION_MASK = 0x1000
UIPC_BB_COMPLETION_BYTES = 12

OPCODE_LUT_DMA = 0x0165
OPCODE_LUT_TOGGLE = 0x0166
OPCODE_DEVELOP_A = 0x0169
OPCODE_DEVELOP_B = 0x016A
OPCODE_DESQUEEZE = 0x016B
OPCODE_VIDEO_MODE_PROCAM = 0x0416
OPCODE_VDF_PEAKING = 0x0152
OPCODE_COLOR_BARS = 0x0112
OPCODE_P5_AUDIO_HDMI = 0x032D
OPCODE_TC_MODE = 0x0400
OPCODE_TC_UB_MODE = 0x0402
OPCODE_TC_UB_VAL = 0x0404

SUPPORTED_0X92840747_OPCODES: Tuple[int, ...] = (
    OPCODE_LUT_DMA,
    OPCODE_LUT_TOGGLE,
    OPCODE_DEVELOP_A,
    OPCODE_DEVELOP_B,
    OPCODE_DESQUEEZE,
    OPCODE_VIDEO_MODE_PROCAM,
    OPCODE_VDF_PEAKING,
    OPCODE_COLOR_BARS,
    OPCODE_P5_AUDIO_HDMI,
    OPCODE_TC_MODE,
    OPCODE_TC_UB_MODE,
    OPCODE_TC_UB_VAL,
)

LUT_DMA_PACKET_BYTES = 36
LUT_TOGGLE_PACKET_BYTES = 10
LUT_DMA_SRAM_REG_THRESHOLD = 0xBB80  # 48,000 B
LUT_8BIT_RAW_BYTES = 33 * 33 * 33 * 3  # 107,811 B
LUT_8BIT_ALIGNED_BYTES = 107_812
LUT_16BIT_BYTES = 33 * 33 * 33 * 6  # 215,622 B

DUAL_NATIVE_ISO_BASES: Tuple[int, int] = (800, 12800)
VALID_STEADYSHOT_MODES: Mapping[str, int] = {
    "Off": 0,
    "Standard": 1,
    "Active": 2,
}

HANDLE_REG_CMD = 0x81000001
HANDLE_UNREG_CMD = 0x81000002
HANDLE_ACK_MASK = 0x01000000

EXPECTED_FX3_CPAPP_BYTES = 15_980_568
EXPECTED_FX3_CPAPP_SHA256 = "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba"
EXPECTED_CP_ARM32_ENTRY_WORDS: Tuple[int, ...] = (
    0xE59F1004,
    0xE2811004,
    0xE1A0F001,
    0x0010800C,
    0xE3A000D3,
    0xE12FF000,
)

REQUIRED_CP_IBIS_MARKERS: Tuple[str, ...] = (
    "LiroSeq: Restore.",
    "HallPIDOUT_0",
    "GyroPIDOUT_0",
    "PWMOUT_0",
    "TOPPERS>",
)

SYNTHETIC_TOMCO_CONFIG = (
    "[TOMCO]\n"
    "memcfg=0x00400000@0x04c00000:uc\n"
    "memcfg=0x07000000@0x09000000:uc\n"
    "memcfg=0x24800000@0x1b800000:uc\n"
    "memcfg=0x40000000@0x80000000:uc\n"
    "usrrtn_cfggrp=1\n"
    "console_enable=1\n"
    "uart_baudrate=115200\n"
    "[TOMCO]\n"
)


class IvshmemBridgeError(RuntimeError):
    """Raised on invalid IVSHMEM configuration, protocol violation, or CP mutation."""


# ---------------------------------------------------------------------------
# Strictly Read-Only (`O_RDONLY`) Donor Resolution & Fast `bytes.find` Scanning
# ---------------------------------------------------------------------------


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    return source.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes")


def _iter_work_roots(*, env: Optional[Mapping[str, str]] = None) -> Tuple[Path, ...]:
    if is_forced_clean_room(env):
        return ()
    source = os.environ if env is None else env
    candidates: List[Path] = []
    for k in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        v = source.get(k, "").strip()
        if v:
            candidates.append(Path(os.path.expanduser(v)))
    mac_root = source.get(ENV_MAC_ROOT, "").strip()
    if mac_root:
        base = Path(os.path.expanduser(mac_root))
        candidates.append(base / "outputs" / "sony-fx3-fx6-lab" / "work")
        candidates.append(base / "work")
    candidates.append(DEFAULT_REPO_ROOT / "work")
    internal = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"
    candidates.append(internal / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(internal / "work")
    candidates.append(LEGACY_MAC_ROOT / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(LEGACY_MAC_ROOT / "work")
    seen: Set[str] = set()
    out: List[Path] = []
    for c in candidates:
        s = str(c)
        if s not in seen:
            seen.add(s)
            out.append(c)
    return tuple(out)


def _resolve_donor_file(rel_subpath: str, *, env: Optional[Mapping[str, str]] = None) -> Path:
    rel_norm = rel_subpath.strip("/")
    clean_fallback = DEFAULT_REPO_ROOT / CLEAN_ROOM_SENTINEL_DIRNAME / rel_norm
    if is_forced_clean_room(env):
        return clean_fallback
    for root in _iter_work_roots(env=env):
        cand = root / rel_norm
        if cand.is_file():
            return cand
    return clean_fallback


def resolve_phase24_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Locate FX3 Stock-CP `cpapp-b.bin`, FX6 `appFw.so`, and FX6 `libosal_uipc.so` read-only."""
    return {
        "fx3_cpapp": _resolve_donor_file(
            "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
            env=env,
        ),
        "fx6_appfw": _resolve_donor_file(
            "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
            env=env,
        ),
        "fx6_libosal_uipc": _resolve_donor_file(
            "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libosal_uipc.so",
            env=env,
        ),
    }


def read_donor_bytes_readonly(path: Path) -> bytes:
    """Read a donor file strictly via `os.open(..., os.O_RDONLY)` and deterministic close."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        chunks: List[bytes] = []
        remaining = st.st_size
        while remaining > 0:
            chunk = os.read(fd, min(remaining, 4 * 1024 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Fast `bytes.find` Instruction Encoders & Binary Scanners
# ---------------------------------------------------------------------------


def _encode_thumb2_movw(rd: int, imm16: int) -> bytes:
    i = (imm16 >> 11) & 1
    imm4 = (imm16 >> 12) & 0xF
    imm3 = (imm16 >> 8) & 0x7
    imm8 = imm16 & 0xFF
    return struct.pack(
        "<HH",
        0xF240 | (i << 10) | imm4,
        (imm3 << 12) | ((rd & 0xF) << 8) | imm8,
    )


def _encode_thumb2_movt(rd: int, imm16: int) -> bytes:
    i = (imm16 >> 11) & 1
    imm4 = (imm16 >> 12) & 0xF
    imm3 = (imm16 >> 8) & 0x7
    imm8 = imm16 & 0xFF
    return struct.pack(
        "<HH",
        0xF2C0 | (i << 10) | imm4,
        (imm3 << 12) | ((rd & 0xF) << 8) | imm8,
    )


def _encode_thumb2_movwt(rd: int, val: int) -> bytes:
    return _encode_thumb2_movw(rd, val & 0xFFFF) + _encode_thumb2_movt(rd, (val >> 16) & 0xFFFF)


def _encode_aarch64_movzk(rd: int, val: int) -> bytes:
    lo = val & 0xFFFF
    hi = (val >> 16) & 0xFFFF
    return struct.pack(
        "<II",
        0x52800000 | (lo << 5) | (rd & 0x1F),
        0x72A00000 | (hi << 5) | (rd & 0x1F),
    )


def _scan_cp_movwt_0x9xxx_with_offsets(cp_bytes: bytes) -> Dict[int, List[int]]:
    """Scan Thumb-2 `MOVW/MOVT` pairs yielding `0x9000_0000..0x9FFF_FFFF` via C-level `bytes.find`."""
    n = len(cp_bytes)
    mv = memoryview(cp_bytes)
    found: Dict[int, List[int]] = {}
    for pat in (b"\xc9\xf2", b"\xc9\xf6"):
        pos = cp_bytes.find(pat, 0)
        while pos != -1:
            if (pos & 1) == 0 and pos + 4 <= n:
                hw2 = struct.unpack_from("<H", mv, pos + 2)[0]
                if (hw2 & 0x8000) == 0:
                    hw1 = struct.unpack_from("<H", mv, pos)[0]
                    rd = (hw2 >> 8) & 0xF
                    low_bound = max(0, pos - 24)
                    for prev_i in range(pos - 2, low_bound - 1, -2):
                        phw1 = struct.unpack_from("<H", mv, prev_i)[0]
                        if (phw1 & 0xFBF0) == 0xF240:
                            phw2 = struct.unpack_from("<H", mv, prev_i + 2)[0]
                            if (phw2 & 0x8000) == 0 and ((phw2 >> 8) & 0xF) == rd:
                                imm16_lo = (
                                    ((phw1 & 0xF) << 12)
                                    | (((phw1 >> 10) & 1) << 11)
                                    | (((phw2 >> 12) & 7) << 8)
                                    | (phw2 & 0xFF)
                                )
                                imm16_hi = (
                                    ((hw1 & 0xF) << 12)
                                    | (((hw1 >> 10) & 1) << 11)
                                    | (((hw2 >> 12) & 7) << 8)
                                    | (hw2 & 0xFF)
                                )
                                val = (imm16_hi << 16) | imm16_lo
                                if 0x90000000 <= val <= 0x9FFFFFFF:
                                    found.setdefault(val, []).append(prev_i)
                                break
            pos = cp_bytes.find(pat, pos + 1)
    return found


def _scan_cp_movw_immediates(cp_bytes: bytes, targets: Iterable[int]) -> Dict[int, List[int]]:
    target_set = set(targets)
    found: Dict[int, List[int]] = {}
    n = len(cp_bytes)
    mv = memoryview(cp_bytes)
    hw1_patterns = {
        struct.pack("<H", 0xF240 | (((imm >> 11) & 1) << 10) | ((imm >> 12) & 0xF))
        for imm in target_set
    }
    for pat in hw1_patterns:
        pos = cp_bytes.find(pat, 0)
        while pos != -1:
            if (pos & 1) == 0 and pos + 4 <= n:
                hw2 = struct.unpack_from("<H", mv, pos + 2)[0]
                if (hw2 & 0x8000) == 0:
                    hw1 = struct.unpack_from("<H", mv, pos)[0]
                    imm16 = (
                        ((hw1 & 0xF) << 12)
                        | (((hw1 >> 10) & 1) << 11)
                        | (((hw2 >> 12) & 7) << 8)
                        | (hw2 & 0xFF)
                    )
                    if imm16 in target_set:
                        found.setdefault(imm16, []).append(pos)
            pos = cp_bytes.find(pat, pos + 1)
    return found


def _scan_aarch64_movzk_0x9xxx(elf_bytes: bytes) -> Set[int]:
    n = len(elf_bytes)
    insns = memoryview(elf_bytes)
    found: Set[int] = set()
    for pat in (b"\xb2\x72", b"\xb3\x72", b"\xb2\xf2", b"\xb3\xf2"):
        pos = elf_bytes.find(pat, 2)
        while pos != -1:
            off = pos - 2
            if (off & 3) == 0 and off + 4 <= n:
                w = struct.unpack_from("<I", insns, off)[0]
                if (w & 0x7FE00000) == 0x72A00000:
                    rd = w & 0x1F
                    low_bound = max(0, off - 24)
                    for prev_off in range(off - 4, low_bound - 1, -4):
                        pw = struct.unpack_from("<I", insns, prev_off)[0]
                        if (pw & 0x7FE00000) == 0x52800000 and (pw & 0x1F) == rd:
                            val = (((w >> 5) & 0xFFFF) << 16) | ((pw >> 5) & 0xFFFF)
                            if 0x90000000 <= val <= 0x9FFFFFFF:
                                found.add(val)
                            break
            pos = elf_bytes.find(pat, pos + 1)
    return found


@dataclass(frozen=True)
class CpBinaryInspection:
    source_mode: str
    byte_length: int
    sha256: str
    load_base: int
    self_ref_literal: int
    startup_header_valid: bool
    has_0x92840747: bool
    queue_0x92840747_hit_count: int
    first_0x92840747_offset: int
    p11_rtc_present_in_cp: bool
    p11_handle_present_in_cp: bool
    completion_0x1000_opcodes: Tuple[str, ...]
    completion_0x8000_opcodes: Tuple[str, ...]
    first_comp_movw_offset: int
    first_comp_movw_imm16: int
    uipc_flags_0x8001_count: int
    orr_0x8000_count: int
    ibis_markers_verified: Tuple[str, ...]
    tomco_present: bool


@dataclass(frozen=True)
class ApBinaryInspection:
    source_mode: str
    appfw_bytes: int
    appfw_sha256: str
    libosal_uipc_bytes: int
    libosal_uipc_sha256: str
    appfw_has_0x92840747: bool
    appfw_has_p11_rtc: bool
    appfw_has_p11_handle: bool
    uipc_has_dev_uipc: bool
    uipc_has_osal_snd_msg: bool
    uipc_has_osal_rcv_msg: bool


def inspect_cp_binary(cp_bytes: bytes, *, source_mode: str) -> CpBinaryInspection:
    """Fast `bytes.find` inspection of FX3 `cpapp-b.bin` or clean-room synthetic CP binary."""
    sha = hashlib.sha256(cp_bytes).hexdigest()
    startup_ok = False
    self_ref = 0
    if len(cp_bytes) >= 24:
        entry_words = struct.unpack_from("<6I", cp_bytes, 0)
        self_ref = entry_words[3]
        startup_ok = entry_words == EXPECTED_CP_ARM32_ENTRY_WORDS and (self_ref - 0x0C) == CP_LOAD_BASE

    q_map = _scan_cp_movwt_0x9xxx_with_offsets(cp_bytes)
    q_hits = q_map.get(UIPC_BB_TARGET_QUEUE, [])

    comp_1000_targets = {op | UIPC_BB_HW_COMPLETION_MASK: op for op in SUPPORTED_0X92840747_OPCODES}
    comp_8000_targets = {op | UIPC_BB_COMPLETION_BIT: op for op in SUPPORTED_0X92840747_OPCODES}
    all_movw_hits = _scan_cp_movw_immediates(
        cp_bytes,
        list(comp_1000_targets.keys()) + list(comp_8000_targets.keys()) + [UIPC_BB_FLAGS],
    )

    found_1000 = sorted(
        op for imm, op in comp_1000_targets.items() if imm in all_movw_hits
    )
    found_8000 = sorted(
        op for imm, op in comp_8000_targets.items() if imm in all_movw_hits
    )

    # Prefer `0x1165` (real `cpapp-b.bin` `0x0165 | 0x1000` at `0x4c1d58`) or `0x8165`
    first_comp_off = -1
    first_comp_imm = 0
    for cand_imm in (OPCODE_LUT_DMA | UIPC_BB_HW_COMPLETION_MASK, OPCODE_LUT_DMA | UIPC_BB_COMPLETION_BIT):
        offs = all_movw_hits.get(cand_imm)
        if offs:
            first_comp_off = offs[0]
            first_comp_imm = cand_imm
            break

    ibis_hits = tuple(
        m for m in REQUIRED_CP_IBIS_MARKERS if cp_bytes.find(m.encode("ascii")) != -1
    )

    return CpBinaryInspection(
        source_mode=source_mode,
        byte_length=len(cp_bytes),
        sha256=sha,
        load_base=CP_LOAD_BASE,
        self_ref_literal=self_ref,
        startup_header_valid=startup_ok,
        has_0x92840747=len(q_hits) > 0,
        queue_0x92840747_hit_count=len(q_hits),
        first_0x92840747_offset=q_hits[0] if q_hits else -1,
        p11_rtc_present_in_cp=RTC_QUEUE_ID in q_map,
        p11_handle_present_in_cp=HANDLE_QUEUE_ID in q_map,
        completion_0x1000_opcodes=tuple(f"0x{op:04x}" for op in found_1000),
        completion_0x8000_opcodes=tuple(f"0x{op:04x}" for op in found_8000),
        first_comp_movw_offset=first_comp_off,
        first_comp_movw_imm16=first_comp_imm,
        uipc_flags_0x8001_count=len(all_movw_hits.get(UIPC_BB_FLAGS, [])),
        orr_0x8000_count=cp_bytes.count(b"\x4f\xf4\x00\x40"),
        ibis_markers_verified=ibis_hits,
        tomco_present=cp_bytes.find(b"[TOMCO]") != -1,
    )


def inspect_ap_binaries(
    appfw_bytes: bytes,
    libosal_uipc_bytes: bytes,
    *,
    source_mode: str,
) -> ApBinaryInspection:
    q_set = _scan_aarch64_movzk_0x9xxx(appfw_bytes)
    return ApBinaryInspection(
        source_mode=source_mode,
        appfw_bytes=len(appfw_bytes),
        appfw_sha256=hashlib.sha256(appfw_bytes).hexdigest(),
        libosal_uipc_bytes=len(libosal_uipc_bytes),
        libosal_uipc_sha256=hashlib.sha256(libosal_uipc_bytes).hexdigest(),
        appfw_has_0x92840747=UIPC_BB_TARGET_QUEUE in q_set,
        appfw_has_p11_rtc=RTC_QUEUE_ID in q_set,
        appfw_has_p11_handle=HANDLE_QUEUE_ID in q_set,
        uipc_has_dev_uipc=libosal_uipc_bytes.find(b"/dev/uipc") != -1,
        uipc_has_osal_snd_msg=libosal_uipc_bytes.find(b"osal_snd_msg") != -1,
        uipc_has_osal_rcv_msg=libosal_uipc_bytes.find(b"osal_rcv_msg") != -1,
    )


# ---------------------------------------------------------------------------
# Clean-Room Synthetic AArch64 + ARM32 Thumb-2 (`TOMCO` + `0x92840747` + `0x8000`)
# ---------------------------------------------------------------------------


def _build_minimal_elf64(code_bytes: bytes, rodata_bytes: bytes) -> bytes:
    total_size = 0x10000
    buf = bytearray(total_size)
    e_ident = b"\x7fELF\x02\x01\x01" + b"\x00" * 9
    struct.pack_into("<16sHHIQQQIHHHHHH", buf, 0, e_ident, 3, 183, 1, 0x4000, 64, 0xE000, 0, 64, 56, 2, 64, 5, 4)
    buf[0x4000 : 0x4000 + len(code_bytes)] = code_bytes
    buf[0x8000 : 0x8000 + len(rodata_bytes)] = rodata_bytes
    return bytes(buf)


def build_clean_room_synthetic_binaries() -> Dict[str, bytes]:
    """Build deterministic clean-room AArch64 + ARM32 Thumb-2 (`TOMCO` + `0x92840747` + `|0x8000`)."""
    # 1. Clean-room ARM32 Thumb-2 Stock-CP binary mapped at 0x0010_8000
    cp = bytearray()
    for w in EXPECTED_CP_ARM32_ENTRY_WORDS:
        cp.extend(struct.pack("<I", w))
    while len(cp) < 0x40:
        cp.extend(b"\x00")
    cp.extend(SYNTHETIC_TOMCO_CONFIG.encode("ascii"))
    while len(cp) & 3:
        cp.append(0)
    # Thumb-2 MOVW/MOVT 0x92840747 + ORR.W #0x8000 + MOVW completion constants
    cp.extend(_encode_thumb2_movwt(0, UIPC_BB_TARGET_QUEUE))
    cp.extend(struct.pack("<HH", 0xF440, 0x4000))  # ORR.W r0, r0, #0x8000
    cp.extend(_encode_thumb2_movw(1, UIPC_BB_FLAGS))
    for op in SUPPORTED_0X92840747_OPCODES:
        cp.extend(_encode_thumb2_movw(1, op | UIPC_BB_HW_COMPLETION_MASK))
        cp.extend(_encode_thumb2_movw(2, op | UIPC_BB_COMPLETION_BIT))
    cp.extend(b"\x00".join(m.encode("ascii") for m in REQUIRED_CP_IBIS_MARKERS) + b"\x00")
    while len(cp) < 0x2000:
        cp.append(0)

    # 2. Clean-room AArch64 `appFw.so` & `libosal_uipc.so`
    ap_code = (
        _encode_aarch64_movzk(0, UIPC_BB_TARGET_QUEUE)
        + _encode_aarch64_movzk(0, RTC_QUEUE_ID)
        + _encode_aarch64_movzk(0, HANDLE_QUEUE_ID)
        + struct.pack("<I", 0xD65F03C0)
    )
    appfw_elf = _build_minimal_elf64(
        ap_code,
        b"infra_wrapper_rtc_procam_chaplin_base.cpp\x00infra_wrapper_handle_procam_chaplin_base.cpp\x00",
    )
    uipc_elf = _build_minimal_elf64(
        struct.pack("<I", 0xD65F03C0),
        b"osal_snd_msg\x00osal_rcv_msg\x00/dev/uipc\x00",
    )
    return {
        "fx3_cpapp": bytes(cp),
        "fx6_appfw": appfw_elf,
        "fx6_libosal_uipc": uipc_elf,
    }


# ---------------------------------------------------------------------------
# QEMU `ivshmem-doorbell` / `ivshmem-flat` MMIO Register Model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DoorbellEvent:
    seq: int
    src_peer: int
    dst_peer: int
    vector: int
    raw_value: int
    delivered_irq: bool
    reason: str


class IvshmemPeerRegisters:
    """QEMU `ivshmem-doorbell` / `ivshmem-flat` 4-register BAR0/MMIO block."""

    def __init__(self, peer_id: int, *, intrmask: int = 0xFFFFFFFF) -> None:
        self.peer_id = peer_id
        self.intrmask = intrmask & 0xFFFFFFFF
        self.intrstatus = 0
        self.irq_received_count = 0

    def read32(self, offset: int) -> int:
        if offset == IVSHMEM_REG_INTRMASK:
            return self.intrmask
        if offset == IVSHMEM_REG_INTRSTATUS:
            # Standard QEMU ivshmem INTRSTATUS is clear-on-read
            val = self.intrstatus
            self.intrstatus = 0
            return val
        if offset == IVSHMEM_REG_IVPOSITION:
            return self.peer_id
        return 0

    def write32(self, offset: int, value: int, bus: "IvshmemBus") -> None:
        value &= 0xFFFFFFFF
        if offset == IVSHMEM_REG_INTRMASK:
            self.intrmask = value
        elif offset == IVSHMEM_REG_DOORBELL:
            bus.ring_doorbell(src_peer=self.peer_id, raw_value=value)
        # IVPOSITION & INTRSTATUS writes are ignored per QEMU hardware spec


class IvshmemBus:
    """Connects Peer 0 (`ivshmem-doorbell`) and Peer 1 (`ivshmem-flat`) via DOORBELL."""

    def __init__(self) -> None:
        self.peers: Dict[int, IvshmemPeerRegisters] = {
            PEER_ID_AP_MIRA: IvshmemPeerRegisters(PEER_ID_AP_MIRA),
            PEER_ID_CP_CETUS: IvshmemPeerRegisters(PEER_ID_CP_CETUS),
        }
        self.doorbell_trace: List[DoorbellEvent] = []
        self.invalid_doorbell_count: int = 0
        self.masked_doorbell_count: int = 0
        self.pending_irq_peers: Set[int] = set()

    def ring_doorbell(self, *, src_peer: int, raw_value: int) -> DoorbellEvent:
        dst_peer = (raw_value >> 16) & 0xFFFF
        vector = raw_value & 0xFFFF
        target = self.peers.get(dst_peer)
        seq = len(self.doorbell_trace) + 1
        if target is None:
            self.invalid_doorbell_count += 1
            ev = DoorbellEvent(
                seq=seq,
                src_peer=src_peer,
                dst_peer=dst_peer,
                vector=vector,
                raw_value=raw_value,
                delivered_irq=False,
                reason=f"unknown_target_peer_{dst_peer}",
            )
            self.doorbell_trace.append(ev)
            return ev

        bit = 1 << (vector & 31)
        target.intrstatus |= bit
        irq_allowed = (target.intrmask & bit) != 0
        if irq_allowed:
            target.irq_received_count += 1
            self.pending_irq_peers.add(dst_peer)
            reason = "irq_delivered"
        else:
            self.masked_doorbell_count += 1
            reason = "masked_by_intrmask"

        ev = DoorbellEvent(
            seq=seq,
            src_peer=src_peer,
            dst_peer=dst_peer,
            vector=vector,
            raw_value=raw_value,
            delivered_irq=irq_allowed,
            reason=reason,
        )
        self.doorbell_trace.append(ev)
        return ev


# ---------------------------------------------------------------------------
# AArch64 (Peer 0) & ARM32 Thumb-2 (Peer 1) Firmware Routine Builders
# ---------------------------------------------------------------------------


class _AArch64Assembler:
    """Minimal deterministic AArch64 assembler with label patching."""

    def __init__(self, base_vma: int) -> None:
        self.base_vma = base_vma
        self.words: List[int] = []
        self.labels: Dict[str, int] = {}
        self.fixups: List[Tuple[int, str, str, int]] = []  # (idx, kind, label, reg)

    def label(self, name: str) -> None:
        self.labels[name] = len(self.words)

    def emit(self, word: int) -> None:
        self.words.append(word & 0xFFFFFFFF)

    def mov32(self, rd: int, val: int) -> None:
        lo = val & 0xFFFF
        hi = (val >> 16) & 0xFFFF
        self.emit(0x52800000 | (lo << 5) | (rd & 0x1F))
        if hi:
            self.emit(0x72A00000 | (hi << 5) | (rd & 0x1F))

    def mov64(self, rd: int, val: int) -> None:
        self.emit(0xD2800000 | ((val & 0xFFFF) << 5) | (rd & 0x1F))
        for shift, hw in ((16, (val >> 16) & 0xFFFF), (32, (val >> 32) & 0xFFFF), (48, (val >> 48) & 0xFFFF)):
            if hw:
                self.emit(0xF2800000 | ((shift // 16) << 21) | (hw << 5) | (rd & 0x1F))

    def b(self, label: str) -> None:
        self.fixups.append((len(self.words), "b", label, 0))
        self.emit(0x14000000)

    def b_cond(self, cond: int, label: str) -> None:
        self.fixups.append((len(self.words), "bcond", label, cond))
        self.emit(0x54000000 | (cond & 0xF))

    def cbz(self, rt: int, label: str) -> None:
        self.fixups.append((len(self.words), "cbz", label, rt))
        self.emit(0x34000000 | (rt & 0x1F))

    def cbnz(self, rt: int, label: str) -> None:
        self.fixups.append((len(self.words), "cbnz", label, rt))
        self.emit(0x35000000 | (rt & 0x1F))

    def link(self) -> bytes:
        out = list(self.words)
        for idx, kind, label, extra in self.fixups:
            delta = self.labels[label] - idx
            if kind == "b":
                out[idx] = 0x14000000 | (delta & 0x03FFFFFF)
            elif kind == "bcond":
                out[idx] = 0x54000000 | ((delta & 0x7FFFF) << 5) | (extra & 0xF)
            elif kind == "cbz":
                out[idx] = 0x34000000 | ((delta & 0x7FFFF) << 5) | (extra & 0x1F)
            elif kind == "cbnz":
                out[idx] = 0x35000000 | ((delta & 0x7FFFF) << 5) | (extra & 0x1F)
        return b"".join(struct.pack("<I", w) for w in out)


def _build_ap_aarch64_firmware() -> Tuple[bytes, bytes]:
    """Assemble real AArch64 `ap_uipc_submit` and `ap_uipc_poll_rx` routines for Peer 0."""
    # Routine 1: uint32_t ap_uipc_submit(w0=queue_id, x1=req_ptr, w2=req_len, w3=seq_id, x4=local_reply_buf)
    a = _AArch64Assembler(AP_SUBMIT_ENTRY)
    a.mov32(8, IVSHMEM_AP_MMIO_BASE)   # x8 = MMIO BAR0
    a.mov32(9, IVSHMEM_AP_SHM_BASE)    # x9 = SHM BAR2

    # P11 Filter #1: queue_id == 0x92d2091c (RTC)
    a.mov32(10, RTC_QUEUE_ID)
    a.emit(0x6B0A001F)  # cmp w0, w10
    a.b_cond(0, "p11_rtc")  # b.eq

    # P11 Filter #2: queue_id == 0x91db059b (Smart Handle)
    a.mov32(10, HANDLE_QUEUE_ID)
    a.emit(0x6B0A001F)  # cmp w0, w10
    a.b_cond(0, "p11_handle")  # b.eq

    # Check queue_id == 0x92840747
    a.mov32(10, UIPC_BB_TARGET_QUEUE)
    a.emit(0x6B0A001F)  # cmp w0, w10
    a.b_cond(1, "invalid_arg")  # b.ne

    # Validate 1 <= req_len <= 240
    a.cbz(2, "invalid_arg")
    a.emit(0x7103C05F)  # cmp w2, #240 (0xF0)
    a.b_cond(8, "invalid_arg")  # b.hi

    # Check TX ring space: tx_head - tx_tail < tx_cap
    a.emit(0xB940092A)  # ldr w10, [x9, #0x08] (tx_head)
    a.emit(0xB9400D2B)  # ldr w11, [x9, #0x0C] (tx_tail)
    a.emit(0xB940112C)  # ldr w12, [x9, #0x10] (tx_cap)
    a.emit(0x4B0B014D)  # sub w13, w10, w11
    a.emit(0x6B0C01BF)  # cmp w13, w12
    a.b_cond(3, "tx_has_space")  # b.lo

    # Backpressure: increment [x9 + 0x50] and return -1
    a.emit(0xB940512D)  # ldr w13, [x9, #0x50]
    a.emit(0x110005AD)  # add w13, w13, #1
    a.emit(0xB900512D)  # str w13, [x9, #0x50]
    a.emit(0x12800000)  # mov w0, #-1
    a.emit(0xD65F03C0)  # ret

    a.label("tx_has_space")
    # slot_addr x14 = x9 + 0x1000 + ((w10 & 15) << 8)
    a.emit(0x12000D4D)  # and w13, w10, #0xf
    a.emit(0x53185DAD)  # lsl w13, w13, #8
    a.emit(0x9140052E)  # add x14, x9, #0x1000
    a.emit(0x8B0D01CE)  # add x14, x14, x13

    # Write slot header: queue_id, seq_id, req_len, flags=1
    a.emit(0xB90001C0)  # str w0, [x14, #0x00]
    a.emit(0xB90005C3)  # str w3, [x14, #0x04]
    a.emit(0xB90009C2)  # str w2, [x14, #0x08]
    a.emit(0x5280002F)  # mov w15, #1
    a.emit(0xB9000DCF)  # str w15, [x14, #0x0C]

    # Copy req_len bytes from x1 -> x14 + 0x10
    a.emit(0x910041CE)  # add x14, x14, #0x10
    a.emit(0xD280000F)  # mov x15, #0
    a.label("copy_loop")
    a.emit(0x6B0201FF)  # cmp w15, w2
    a.b_cond(2, "copy_done")  # b.hs
    a.emit(0x386F6830)  # ldrb w16, [x1, x15]
    a.emit(0x382F69D0)  # strb w16, [x14, x15]
    a.emit(0x910005EF)  # add x15, x15, #1
    a.b("copy_loop")

    a.label("copy_done")
    a.emit(0x1100054A)  # add w10, w10, #1
    a.emit(0xB900092A)  # str w10, [x9, #0x08] (tx_head)
    a.emit(0xD5033FBF)  # dmb sy
    # Ring DOORBELL targeting Peer 1 vector 0: (1 << 16) | 0 = 0x00010000
    a.mov32(13, (PEER_ID_CP_CETUS << 16) | 0)
    a.emit(0xB9000D0D)  # str w13, [x8, #0x0C]
    a.emit(0x52800000)  # mov w0, #0
    a.emit(0xD65F03C0)  # ret

    # Local P11 RTC (0x92d2091c): expects len==2 and req[0]==0x03
    a.label("p11_rtc")
    a.emit(0x7100085F)  # cmp w2, #2
    a.b_cond(1, "invalid_arg")
    a.emit(0x3940002B)  # ldrb w11, [x1, #0]
    a.emit(0x71000D7F)  # cmp w11, #3
    a.b_cond(1, "invalid_arg")
    a.emit(0x3900008B)  # strb w11, [x4, #0] (0x03)
    a.emit(0xB940612C)  # ldr w12, [x9, #0x60] (ap_rtc_valid)
    a.emit(0x7100019F)  # cmp w12, #0
    a.emit(0x1A9F17EC)  # cset w12, eq -> 0 if valid else 1
    a.emit(0x3900048C)  # strb w12, [x4, #1]
    a.emit(0xB940292D)  # ldr w13, [x9, #0x28] (p11_rtc_cnt)
    a.emit(0x110005AD)  # add w13, w13, #1
    a.emit(0xB900292D)  # str w13, [x9, #0x28]
    a.emit(0x52800020)  # mov w0, #1
    a.emit(0xD65F03C0)  # ret

    # Local P11 Smart Handle (0x91db059b): expects len==12
    a.label("p11_handle")
    a.emit(0x7100305F)  # cmp w2, #12
    a.b_cond(1, "invalid_arg")
    a.emit(0xB940002B)  # ldr w11, [x1, #0] (cmd)
    a.emit(0xB940082C)  # ldr w12, [x1, #8] (cb_qid)
    a.mov32(13, HANDLE_ACK_MASK)
    a.emit(0x2A0D016B)  # orr w11, w11, w13
    a.emit(0xB900008B)  # str w11, [x4, #0]
    a.emit(0xB900049F)  # str wzr, [x4, #4]
    a.emit(0xB900088C)  # str w12, [x4, #8]
    a.emit(0xB9402D2D)  # ldr w13, [x9, #0x2C] (p11_handle_cnt)
    a.emit(0x110005AD)  # add w13, w13, #1
    a.emit(0xB9002D2D)  # str w13, [x9, #0x2C]
    a.emit(0x52800020)  # mov w0, #1
    a.emit(0xD65F03C0)  # ret

    a.label("invalid_arg")
    a.emit(0x12800020)  # mov w0, #-2
    a.emit(0xD65F03C0)  # ret

    # Routine 2: uint32_t ap_uipc_poll_rx(x0=out_slot_buf)
    p = _AArch64Assembler(AP_POLL_RX_ENTRY)
    p.mov32(8, IVSHMEM_AP_MMIO_BASE)
    p.mov32(9, IVSHMEM_AP_SHM_BASE)
    p.emit(0xB940050A)  # ldr w10, [x8, #0x04] (INTRSTATUS clear-on-read)
    p.cbz(10, "check_rx")
    p.emit(0xB940352B)  # ldr w11, [x9, #0x34] (ap_irq_cnt)
    p.emit(0x1100056B)  # add w11, w11, #1
    p.emit(0xB900352B)  # str w11, [x9, #0x34]

    p.label("check_rx")
    p.emit(0xB940192A)  # ldr w10, [x9, #0x18] (rx_head)
    p.emit(0xB9401D2B)  # ldr w11, [x9, #0x1C] (rx_tail)
    p.emit(0x6B0B015F)  # cmp w10, w11
    p.b_cond(1, "rx_non_empty")  # b.ne
    p.emit(0x12800000)  # mov w0, #-1
    p.emit(0xD65F03C0)  # ret

    p.label("rx_non_empty")
    p.emit(0x12000D6C)  # and w12, w11, #0xf
    p.emit(0x53185D8C)  # lsl w12, w12, #8
    p.emit(0x9140092D)  # add x13, x9, #0x2000
    p.emit(0x8B0C01AD)  # add x13, x13, x12

    # Copy 48 bytes (0x30) from RX slot x13 -> x0
    p.emit(0xD280000E)  # mov x14, #0
    p.label("rx_copy")
    p.emit(0xF100C1DF)  # cmp x14, #48
    p.b_cond(2, "rx_copy_done")  # b.hs
    p.emit(0x386E69AF)  # ldrb w15, [x13, x14]
    p.emit(0x382E680F)  # strb w15, [x0, x14]
    p.emit(0x910005CE)  # add x14, x14, #1
    p.b("rx_copy")

    p.label("rx_copy_done")
    p.emit(0x1100056B)  # add w11, w11, #1
    p.emit(0xB9001D2B)  # str w11, [x9, #0x1C] (rx_tail)
    p.emit(0x52800000)  # mov w0, #0
    p.emit(0xD65F03C0)  # ret

    return a.link(), p.link()


class _Thumb2Assembler:
    """Minimal deterministic ARM32 Thumb-2 assembler with label patching."""

    def __init__(self) -> None:
        self.buf = bytearray()
        self.labels: Dict[str, int] = {}
        self.fixups: List[Tuple[int, str, str, int]] = []

    def label(self, name: str) -> None:
        self.labels[name] = len(self.buf)

    def h16(self, val: int) -> None:
        self.buf.extend(struct.pack("<H", val & 0xFFFF))

    def w32(self, hw1: int, hw2: int) -> None:
        self.buf.extend(struct.pack("<HH", hw1 & 0xFFFF, hw2 & 0xFFFF))

    def movw(self, rd: int, imm16: int) -> None:
        self.buf.extend(_encode_thumb2_movw(rd, imm16))

    def movt(self, rd: int, imm16: int) -> None:
        self.buf.extend(_encode_thumb2_movt(rd, imm16))

    def mov32(self, rd: int, val: int) -> None:
        self.movw(rd, val & 0xFFFF)
        hi = (val >> 16) & 0xFFFF
        if hi:
            self.movt(rd, hi)

    def ldr_w(self, rt: int, rn: int, imm12: int) -> None:
        self.w32(0xF8D0 | (rn & 0xF), ((rt & 0xF) << 12) | (imm12 & 0xFFF))

    def str_w(self, rt: int, rn: int, imm12: int) -> None:
        self.w32(0xF8C0 | (rn & 0xF), ((rt & 0xF) << 12) | (imm12 & 0xFFF))

    def ldrh_w(self, rt: int, rn: int, imm12: int) -> None:
        self.w32(0xF8B0 | (rn & 0xF), ((rt & 0xF) << 12) | (imm12 & 0xFFF))

    def strh_w(self, rt: int, rn: int, imm12: int) -> None:
        self.w32(0xF8A0 | (rn & 0xF), ((rt & 0xF) << 12) | (imm12 & 0xFFF))

    def add_lsl(self, rd: int, rn: int, rm: int, shift: int) -> None:
        imm3 = (shift >> 2) & 7
        imm2 = shift & 3
        self.w32(0xEB00 | (rn & 0xF), (imm3 << 12) | ((rd & 0xF) << 8) | (imm2 << 6) | (rm & 0xF))

    def add_imm(self, rd: int, rn: int, imm12: int) -> None:
        # ADDW rd, rn, #imm12
        i = (imm12 >> 11) & 1
        imm3 = (imm12 >> 8) & 7
        imm8 = imm12 & 0xFF
        self.w32(0xF200 | (i << 10) | (rn & 0xF), (imm3 << 12) | ((rd & 0xF) << 8) | imm8)

    def ubfx(self, rd: int, rn: int, lsb: int, width: int) -> None:
        imm3 = (lsb >> 2) & 7
        imm2 = lsb & 3
        self.w32(0xF3C0 | (rn & 0xF), (imm3 << 12) | ((rd & 0xF) << 8) | (imm2 << 6) | (width - 1))

    def bfi(self, rd: int, rn: int, lsb: int, width: int) -> None:
        imm3 = (lsb >> 2) & 7
        imm2 = lsb & 3
        msb = lsb + width - 1
        self.w32(0xF360 | (rn & 0xF), (imm3 << 12) | ((rd & 0xF) << 8) | (imm2 << 6) | msb)

    def orr_w_8000(self, rd: int, rn: int) -> None:
        self.w32(0xF440 | (rn & 0xF), 0x4000 | ((rd & 0xF) << 8))

    def orr_w_1000(self, rd: int, rn: int) -> None:
        # ThumbExpandImm(0x1000): i=0, imm3=2 (010), a=1 -> 0x4000? Let's encode MOVW+ORRS or verify:
        # 0x1000 = 0x80 << 5 -> rot = 27 = 0b11011 -> i=1, imm3=5, a=1 -> 0xF440, imm8=0x00, i=1 -> 0xF440|rn|0x0400, 0x5000|(rd<<8)
        # Simpler: MOVW r_tmp, #0x1000 + ORR.W rd, rn, r_tmp (0xEA40 | rn, (rd << 8) | r_tmp)
        self.w32(0xEA40 | (rn & 0xF), ((rd & 0xF) << 8) | 12)

    def cmp_rr(self, rn: int, rm: int) -> None:
        # 32-bit CMP.W rn, rm (supports r0..r12)
        self.w32(0xEBB0 | (rn & 0xF), 0x0F00 | (rm & 0xF))

    def b(self, label: str) -> None:
        # 32-bit Thumb-2 B.W T4 (handles any offset cleanly!)
        self.fixups.append((len(self.buf), "bw", label, 0))
        self.w32(0xF000, 0x9000)

    def b_cond(self, cond: int, label: str) -> None:
        # 32-bit Thumb-2 B<cond>.W T3 (handles +/-1 MiB!)
        self.fixups.append((len(self.buf), "bcondw", label, cond))
        self.w32(0xF000, 0x8000)

    def link(self) -> bytes:
        out = bytearray(self.buf)
        for off, kind, label, cond in self.fixups:
            target = self.labels[label]
            rel = target - (off + 4)
            if kind == "bw":
                s = 1 if rel < 0 else 0
                imm24 = rel >> 1
                j1 = 1 ^ ((imm24 >> 22) & 1) ^ s
                j2 = 1 ^ ((imm24 >> 21) & 1) ^ s
                imm10 = (imm24 >> 11) & 0x3FF
                imm11 = imm24 & 0x7FF
                hw1 = 0xF000 | (s << 10) | imm10
                hw2 = 0x9000 | (j1 << 13) | (j2 << 11) | imm11
                struct.pack_into("<HH", out, off, hw1, hw2)
            elif kind == "bcondw":
                s = 1 if rel < 0 else 0
                imm20 = rel >> 1
                j2 = (imm20 >> 19) & 1
                j1 = (imm20 >> 18) & 1
                imm6 = (imm20 >> 11) & 0x3F
                imm11 = imm20 & 0x7FF
                hw1 = 0xF000 | (s << 10) | ((cond & 0xF) << 6) | imm6
                hw2 = 0x8000 | (j1 << 13) | (j2 << 11) | imm11
                struct.pack_into("<HH", out, off, hw1, hw2)
        return bytes(out)


def _build_cp_thumb2_firmware() -> bytes:
    """Assemble real ARM32 Thumb-2 `cp_ivshmem_irq_handler` for Peer 1 (Cortex-R5 Stock-CP).

    Signature: `uint32_t cp_ivshmem_irq_handler(uint32_t movwt_vma, uint32_t comp_movw_vma)`
      - `r0` = VMA inside mapped `cpapp-b.bin` of Thumb-2 `MOVW/MOVT` loading `0x92840747`
      - `r1` = VMA inside mapped `cpapp-b.bin` of Thumb-2 `MOVW` loading `0x1165` (or `0x8165`)
    Returns count of packets processed in `r0`.
    """
    t = _Thumb2Assembler()
    # PUSH {r4-r11, lr}
    t.w32(0xE92D, 0x4FF0)

    # r4 = IVSHMEM_CP_MMIO_BASE (0x6780_0000), r5 = IVSHMEM_CP_SHM_BASE (0x6790_0000)
    t.mov32(4, IVSHMEM_CP_MMIO_BASE)
    t.mov32(5, IVSHMEM_CP_SHM_BASE)

    # 1. Verify IVPOSITION == 1
    t.ldr_w(2, 4, IVSHMEM_REG_IVPOSITION)
    t.mov32(3, PEER_ID_CP_CETUS)
    t.cmp_rr(2, 3)
    t.b_cond(1, "done_zero")  # b.ne

    # 2. Read INTRSTATUS (clear-on-read) and increment cp_irq_cnt if non-zero
    t.ldr_w(2, 4, IVSHMEM_REG_INTRSTATUS)
    t.mov32(3, 0)
    t.cmp_rr(2, 3)
    t.b_cond(0, "skip_irq_cnt")
    t.ldr_w(3, 5, SHM_OFF_CP_IRQ_CNT)
    t.add_imm(3, 3, 1)
    t.str_w(3, 5, SHM_OFF_CP_IRQ_CNT)
    t.label("skip_irq_cnt")

    # 3. Verify cpapp-b.bin startup self-referential literal at 0x0010_800C == 0x0010800C
    t.mov32(6, CP_SELF_REF_LIT)
    t.ldr_w(7, 6, 0)
    t.cmp_rr(7, 6)
    t.b_cond(1, "skip_base_ok")
    t.mov32(7, 1)
    t.str_w(7, 5, SHM_OFF_CP_VERIFIED_BASE)
    t.label("skip_base_ok")

    # 4. Inspect mapped cpapp-b.bin Thumb-2 MOVW/MOVT @ r0 and reconstruct 32-bit 0x92840747!
    #    MOVW at [r0]: hw1=[r0], hw2=[r0+2]; MOVT at [r0+4..24] (we pass exact MOVW + next MOVT or scan)
    #    Actually pass r0 = MOVW VMA, and scan up to 6 halfwords forward for MOVT (0xF2C0 mask 0xFBF0)
    t.mov32(6, 0)  # r6 = offset cursor 0..24
    t.label("scan_movt_loop")
    t.mov32(7, 24)
    t.cmp_rr(6, 7)
    t.b_cond(12, "skip_q_verify")  # b.gt
    t.add_lsl(8, 0, 6, 0)         # r8 = r0 + r6
    t.add_imm(8, 8, 4)
    t.ldrh_w(9, 8, 0)             # hw1 of candidate MOVT
    t.mov32(10, 0xFBF0)
    t.w32(0xEA09, 0x0A0A)         # and.w r10, r9, r10
    t.mov32(11, 0xF2C0)
    t.cmp_rr(10, 11)
    t.b_cond(0, "found_movt")
    t.add_imm(6, 6, 2)
    t.b("scan_movt_loop")

    t.label("found_movt")
    # Decode MOVW [r0] into r6 (low16), and MOVT [r8] into r7 (high16), combine into r6
    # imm16 = (hw2 & 0xff) | ((hw2 & 0x7000) >> 4) | ((hw1 & 0x0400) << 1) | ((hw1 & 0xf) << 12)
    t.ldrh_w(9, 0, 0)
    t.ldrh_w(10, 0, 2)
    t.ubfx(6, 10, 0, 8)
    t.ubfx(11, 10, 12, 3)
    t.bfi(6, 11, 8, 3)
    t.ubfx(11, 9, 10, 1)
    t.bfi(6, 11, 11, 1)
    t.ubfx(11, 9, 0, 4)
    t.bfi(6, 11, 12, 4)

    t.ldrh_w(9, 8, 0)
    t.ldrh_w(10, 8, 2)
    t.ubfx(7, 10, 0, 8)
    t.ubfx(11, 10, 12, 3)
    t.bfi(7, 11, 8, 3)
    t.ubfx(11, 9, 10, 1)
    t.bfi(7, 11, 11, 1)
    t.ubfx(11, 9, 0, 4)
    t.bfi(7, 11, 12, 4)

    t.bfi(6, 7, 16, 16)
    t.mov32(7, UIPC_BB_TARGET_QUEUE)
    t.cmp_rr(6, 7)
    t.b_cond(1, "skip_q_verify")
    t.mov32(7, 1)
    t.str_w(7, 5, SHM_OFF_CP_VERIFIED_QUEUE)
    t.label("skip_q_verify")

    # 5. Inspect mapped cpapp-b.bin completion MOVW @ r1 (e.g., 0x1165 or 0x8165)
    t.ldrh_w(9, 1, 0)
    t.ldrh_w(10, 1, 2)
    t.ubfx(6, 10, 0, 8)
    t.ubfx(11, 10, 12, 3)
    t.bfi(6, 11, 8, 3)
    t.ubfx(11, 9, 10, 1)
    t.bfi(6, 11, 11, 1)
    t.ubfx(11, 9, 0, 4)
    t.bfi(6, 11, 12, 4)
    t.str_w(6, 5, SHM_OFF_CP_VERIFIED_COMP_IMM)

    # 6. Process TX ring slots: r11 = processed_count = 0
    t.mov32(11, 0)
    t.label("tx_loop")
    t.ldr_w(6, 5, SHM_OFF_TX_HEAD)
    t.ldr_w(7, 5, SHM_OFF_TX_TAIL)
    t.cmp_rr(7, 6)
    t.b_cond(0, "tx_loop_end")  # tx_tail == tx_head

    # tx_slot r8 = r5 + 0x1000 + ((r7 & 15) << 8)
    t.mov32(9, 0xF)
    t.w32(0xEA07, 0x0909)  # and.w r9, r7, r9
    t.mov32(12, SHM_TX_RING_OFFSET)
    t.add_lsl(8, 5, 12, 0)
    t.add_lsl(8, 8, 9, 8)

    # Validate slot queue_id == 0x92840747 & 8 <= payload_len <= 240
    t.ldr_w(9, 8, 0x00)
    t.mov32(10, UIPC_BB_TARGET_QUEUE)
    t.cmp_rr(9, 10)
    t.b_cond(1, "malformed_frame")
    t.ldr_w(9, 8, 0x08)  # payload_len
    t.mov32(10, 8)
    t.cmp_rr(9, 10)
    t.b_cond(3, "malformed_frame")  # b.lo
    t.mov32(10, SHM_MAX_PAYLOAD_BYTES)
    t.cmp_rr(9, 10)
    t.b_cond(8, "malformed_frame")  # b.hi

    # Validate UIPC BB header: magic==0x200d, decl_len==payload_len, flags==0x8001
    t.ldrh_w(10, 8, 0x10)  # magic
    t.mov32(12, UIPC_BB_MAGIC)
    t.cmp_rr(10, 12)
    t.b_cond(1, "malformed_frame")
    t.ldrh_w(10, 8, 0x14)  # decl_len
    t.cmp_rr(10, 9)
    t.b_cond(1, "malformed_frame")
    t.ldrh_w(10, 8, 0x16)  # flags
    t.mov32(12, UIPC_BB_FLAGS)
    t.cmp_rr(10, 12)
    t.b_cond(1, "malformed_frame")

    # Extract opcode into r2; handle opcode-specific checks
    t.ldrh_w(2, 8, 0x12)
    t.mov32(3, 0)  # r3 = lut_dma_acked_bytes for this slot

    # Check 0x0165 (36B 3D LUT DMA)
    t.mov32(12, OPCODE_LUT_DMA)
    t.cmp_rr(2, 12)
    t.b_cond(1, "check_0166")
    t.mov32(12, LUT_DMA_PACKET_BYTES)
    t.cmp_rr(9, 12)
    t.b_cond(1, "malformed_frame")
    # Read sram_sz at [tx_slot + 0x10 + 0x18 = 0x28]; if > 0xbb80, touch DMA LUT window & record
    t.ldr_w(3, 8, 0x28)
    t.mov32(12, LUT_DMA_SRAM_REG_THRESHOLD)
    t.cmp_rr(3, 12)
    t.b_cond(9, "after_opcode_check")  # b.ls
    t.mov32(12, IVSHMEM_CP_SHM_BASE + SHM_DMA_LUT_OFFSET)
    t.ldr_w(10, 12, 0)  # read first LUT word from shared DMA window
    t.ldr_w(12, 5, SHM_OFF_LUT_DMA_ACK_CNT)
    t.add_imm(12, 12, 1)
    t.str_w(12, 5, SHM_OFF_LUT_DMA_ACK_CNT)
    t.str_w(3, 5, SHM_OFF_LUT_DMA_LAST_BYTES)
    t.b("after_opcode_check")

    t.label("check_0166")
    t.mov32(12, OPCODE_LUT_TOGGLE)
    t.cmp_rr(2, 12)
    t.b_cond(1, "check_0400")
    t.mov32(12, LUT_TOGGLE_PACKET_BYTES)
    t.cmp_rr(9, 12)
    t.b_cond(1, "malformed_frame")
    t.b("after_opcode_check")

    t.label("check_0400")
    t.mov32(12, OPCODE_TC_MODE)
    t.cmp_rr(2, 12)
    t.b_cond(1, "after_opcode_check")
    t.mov32(12, 9)
    t.cmp_rr(9, 12)
    t.b_cond(3, "after_opcode_check")  # b.lo (< 9 bytes)
    t.w32(0xF898, 0xC018)  # ldrb.w r12, [r8, #0x18] (payload[0] = steadyshot mode)
    t.str_w(12, 5, SHM_OFF_IBIS_MODE)

    t.label("after_opcode_check")
    # Maintain IBIS energized voice-coil center-lock = 1
    t.mov32(12, 1)
    t.str_w(12, 5, SHM_OFF_IBIS_CENTER_LOCK)

    # Check RX ring space: rx_head - rx_tail < 16
    t.ldr_w(6, 5, SHM_OFF_RX_HEAD)
    t.ldr_w(9, 5, SHM_OFF_RX_TAIL)
    t.w32(0xEBA6, 0x0A09)  # sub.w r10, r6, r9
    t.mov32(12, SHM_RING_CAPACITY)
    t.cmp_rr(10, 12)
    t.b_cond(3, "rx_has_space")  # b.lo
    t.mov32(12, 0xE003)
    t.str_w(12, 5, SHM_OFF_LAST_ERROR)
    t.b("tx_loop_end")

    t.label("rx_has_space")
    # rx_slot r9 = r5 + 0x2000 + ((r6 & 15) << 8)
    t.mov32(10, 0xF)
    t.w32(0xEA06, 0x0A0A)  # and.w r10, r6, r10
    t.mov32(12, SHM_RX_RING_OFFSET)
    t.add_lsl(9, 5, 12, 0)
    t.add_lsl(9, 9, 10, 8)

    # Write RX slot header + 12B completion packet (opcode | 0x8000) + hw_alias (opcode | 0x1000)
    t.mov32(10, UIPC_BB_TARGET_QUEUE)
    t.str_w(10, 9, 0x00)       # queue_id
    t.ldr_w(10, 8, 0x04)       # seq_id
    t.str_w(10, 9, 0x04)
    t.mov32(10, UIPC_BB_COMPLETION_BYTES)
    t.str_w(10, 9, 0x08)       # payload_len = 12
    t.mov32(10, 0)
    t.str_w(10, 9, 0x0C)       # raw_status = 0

    t.mov32(10, UIPC_BB_MAGIC)
    t.strh_w(10, 9, 0x10)      # magic = 0x200d
    t.orr_w_8000(10, 2)        # r10 = opcode | 0x8000
    t.strh_w(10, 9, 0x12)      # completion opcode
    t.mov32(10, UIPC_BB_COMPLETION_BYTES)
    t.strh_w(10, 9, 0x14)      # length = 12
    t.mov32(10, UIPC_BB_FLAGS)
    t.strh_w(10, 9, 0x16)      # flags = 0x8001
    t.mov32(10, 0)
    t.str_w(10, 9, 0x18)       # raw_status = 0

    t.mov32(12, UIPC_BB_HW_COMPLETION_MASK)
    t.orr_w_1000(10, 2)        # r10 = opcode | 0x1000
    t.str_w(10, 9, 0x1C)       # hw alias opcode
    t.mov32(10, 1)
    t.str_w(10, 9, 0x20)       # ibis_center_lock_energized = 1
    t.str_w(3, 9, 0x24)        # lut_dma_acked_bytes

    # Commit rx_head & tx_tail
    t.add_imm(6, 6, 1)
    t.str_w(6, 5, SHM_OFF_RX_HEAD)
    t.add_imm(7, 7, 1)
    t.str_w(7, 5, SHM_OFF_TX_TAIL)
    t.w32(0xF3BF, 0x8F5F)      # DMB SY

    # Ring DOORBELL back to Peer 0 vector 0: (0 << 16) | 0 = 0
    t.mov32(10, (PEER_ID_AP_MIRA << 16) | 0)
    t.str_w(10, 4, IVSHMEM_REG_DOORBELL)

    t.add_imm(11, 11, 1)
    t.b("tx_loop")

    t.label("malformed_frame")
    t.ldr_w(12, 5, SHM_OFF_MALFORM_DROP_CNT)
    t.add_imm(12, 12, 1)
    t.str_w(12, 5, SHM_OFF_MALFORM_DROP_CNT)
    t.mov32(12, 0xE001)
    t.str_w(12, 5, SHM_OFF_LAST_ERROR)
    t.add_imm(7, 7, 1)
    t.str_w(7, 5, SHM_OFF_TX_TAIL)
    t.b("tx_loop")

    t.label("done_zero")
    t.mov32(11, 0)

    t.label("tx_loop_end")
    t.w32(0x4658, 0x0000)  # wait: 16-bit MOV r0, r11 is 0x4658; emit h16!
    # Undo that w32 and emit clean MOV r0, r11 + POP {r4-r11, pc}
    t.buf = t.buf[:-4]
    t.h16(0x4658)  # mov r0, r11
    t.w32(0xE8BD, 0x8FF0)  # pop {r4-r11, pc}
    return t.link()


# ---------------------------------------------------------------------------
# Dual-ISA Unicorn Co-Emulation Session & Receipts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoEmulationRoundTripReceipt:
    queue_id: str
    seq_id: int
    opcode: Optional[str]
    request_bytes: int
    intercepted_by_p11: bool
    tx_enqueued: bool
    ap_doorbell_to_cp: bool
    cp_executed: bool
    cp_doorbell_to_ap: bool
    rx_completion_bytes: int
    rx_completion_hex: str
    rx_completion_opcode: Optional[str]
    rx_hw_1000_alias_opcode: Optional[str]
    ibis_center_lock_energized: bool
    lut_dma_acked_bytes: int
    backpressure_rejected: bool
    malformed_dropped: bool
    cp_mutation_bytes: int


@dataclass(frozen=True)
class CpImmutabilityAudit:
    cp_load_base: str
    cp_byte_length: int
    sha256_before: str
    sha256_after: str
    cp_mutation_bytes: int
    immutable: bool


class DualApCpIvshmemSession:
    """Live Dual-ISA Unicorn co-emulation session (`AArch64` AP <-> `IVSHMEM` <-> `Thumb-2` Stock-CP)."""

    def __init__(
        self,
        *,
        cp_bytes: bytes,
        cp_inspection: CpBinaryInspection,
        ap_inspection: ApBinaryInspection,
        source_mode: str,
        rtc_valid: bool = True,
    ) -> None:
        self.source_mode = source_mode
        self.cp_bytes = cp_bytes
        self.cp_inspection = cp_inspection
        self.ap_inspection = ap_inspection
        self.cp_sha256_before = hashlib.sha256(cp_bytes).hexdigest()

        # Shared physical RAM (ctypes buffer mapped zero-copy into BOTH Unicorn instances)
        self.shm_buf = (ctypes.c_uint8 * IVSHMEM_SHM_SIZE)()
        self.shm_ptr = ctypes.addressof(self.shm_buf)
        self.bus = IvshmemBus()
        self._seq_counter = 0

        self._init_shm_ctrl(rtc_valid=rtc_valid)

        # Peer 0: CXD90057 AP ("Mira") — UC_ARCH_ARM64
        self.ap_uc = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
        self.ap_uc.reg_write(A64.UC_ARM64_REG_CPACR_EL1, 3 << 20)
        self.ap_uc.mem_map(AP_CODE_BASE, AP_CODE_SIZE, U.UC_PROT_READ | U.UC_PROT_EXEC)
        ap_submit_code, ap_poll_code = _build_ap_aarch64_firmware()
        self.ap_uc.mem_write(AP_SUBMIT_ENTRY, ap_submit_code)
        self.ap_uc.mem_write(AP_POLL_RX_ENTRY, ap_poll_code)
        self.ap_uc.mem_write(AP_CODE_EXIT, struct.pack("<I", 0xD503201F))  # NOP sentinel
        self.ap_uc.mem_map(AP_STACK_BASE, AP_STACK_SIZE, U.UC_PROT_READ | U.UC_PROT_WRITE)
        self.ap_uc.mem_map(AP_SCRATCH_BASE, AP_SCRATCH_SIZE, U.UC_PROT_READ | U.UC_PROT_WRITE)
        self.ap_uc.mem_map(IVSHMEM_AP_MMIO_BASE, IVSHMEM_MMIO_SPAN, U.UC_PROT_READ | U.UC_PROT_WRITE)
        self.ap_uc.mem_map_ptr(IVSHMEM_AP_SHM_BASE, IVSHMEM_SHM_SIZE, U.UC_PROT_ALL, self.shm_ptr)

        # Peer 1: CXD90058 Stock-CP ("Cetus") — UC_ARCH_ARM | UC_MODE_THUMB
        self.cp_uc = U.Uc(U.UC_ARCH_ARM, U.UC_MODE_THUMB)
        self.cp_uc.mem_map(CP_ISR_BASE, CP_ISR_SIZE, U.UC_PROT_READ | U.UC_PROT_EXEC)
        cp_isr_code = _build_cp_thumb2_firmware()
        self.cp_uc.mem_write(CP_ISR_ENTRY, cp_isr_code)
        self.cp_uc.mem_write(CP_ISR_EXIT, struct.pack("<H", 0xBF00))  # Thumb NOP sentinel
        cp_map_size = (len(cp_bytes) + 0xFFF) & ~0xFFF
        # Strictly READ + EXEC (`cp_mutation_bytes == 0` enforced by Unicorn MMU!)
        self.cp_uc.mem_map(CP_LOAD_BASE, cp_map_size, U.UC_PROT_READ | U.UC_PROT_EXEC)
        self.cp_uc.mem_write(CP_LOAD_BASE, cp_bytes)
        self.cp_uc.mem_map(CP_STACK_BASE, CP_STACK_SIZE, U.UC_PROT_READ | U.UC_PROT_WRITE)
        self.cp_uc.mem_map(CP_SCRATCH_BASE, CP_SCRATCH_SIZE, U.UC_PROT_READ | U.UC_PROT_WRITE)
        self.cp_uc.mem_map(IVSHMEM_CP_MMIO_BASE, IVSHMEM_MMIO_SPAN, U.UC_PROT_READ | U.UC_PROT_WRITE)
        self.cp_uc.mem_map_ptr(IVSHMEM_CP_SHM_BASE, IVSHMEM_SHM_SIZE, U.UC_PROT_ALL, self.shm_ptr)

        # Install IVSHMEM MMIO hooks on BOTH Unicorn instances
        self._install_mmio_hooks(self.ap_uc, PEER_ID_AP_MIRA, IVSHMEM_AP_MMIO_BASE)
        self._install_mmio_hooks(self.cp_uc, PEER_ID_CP_CETUS, IVSHMEM_CP_MMIO_BASE)

    def _init_shm_ctrl(self, *, rtc_valid: bool) -> None:
        self._write_shm_u32(SHM_OFF_MAGIC, SHM_MAGIC)
        self._write_shm_u32(SHM_OFF_VERSION, SHM_VERSION)
        self._write_shm_u32(SHM_OFF_TX_CAP, SHM_RING_CAPACITY)
        self._write_shm_u32(SHM_OFF_TX_SLOT_BYTES, SHM_SLOT_BYTES)
        self._write_shm_u32(SHM_OFF_RX_CAP, SHM_RING_CAPACITY)
        self._write_shm_u32(SHM_OFF_RX_SLOT_BYTES, SHM_SLOT_BYTES)
        self._write_shm_u32(SHM_OFF_AP_RTC_VALID, 1 if rtc_valid else 0)

    def _read_shm_u32(self, offset: int) -> int:
        return struct.unpack_from("<I", bytes(self.shm_buf[offset : offset + 4]), 0)[0]

    def _write_shm_u32(self, offset: int, val: int) -> None:
        raw = struct.pack("<I", val & 0xFFFFFFFF)
        for i in range(4):
            self.shm_buf[offset + i] = raw[i]

    def set_ap_rtc_valid(self, valid: bool) -> None:
        self._write_shm_u32(SHM_OFF_AP_RTC_VALID, 1 if valid else 0)

    def _install_mmio_hooks(self, uc: U.Uc, peer_id: int, mmio_base: int) -> None:
        peer_regs = self.bus.peers[peer_id]

        def _on_read(uc_inst: U.Uc, access: int, addr: int, size: int, value: int, user_data: object) -> None:
            reg_off = addr - mmio_base
            if 0 <= reg_off < 0x10 and size == 4:
                val = peer_regs.read32(reg_off)
                uc_inst.mem_write(addr, struct.pack("<I", val))

        def _on_write(uc_inst: U.Uc, access: int, addr: int, size: int, value: int, user_data: object) -> None:
            reg_off = addr - mmio_base
            if 0 <= reg_off < 0x10 and size == 4:
                peer_regs.write32(reg_off, value, self.bus)

        uc.hook_add(U.UC_HOOK_MEM_READ, _on_read, begin=mmio_base, end=mmio_base + 0x10)
        uc.hook_add(U.UC_HOOK_MEM_WRITE, _on_write, begin=mmio_base, end=mmio_base + 0x10)

    def _run_ap_submit(self, queue_id: int, req_bytes: bytes, seq_id: int) -> Tuple[int, bytes]:
        req_addr = AP_SCRATCH_BASE + 0x0100
        reply_addr = AP_SCRATCH_BASE + 0x0400
        self.ap_uc.mem_write(req_addr, req_bytes)
        self.ap_uc.mem_write(reply_addr, b"\x00" * 32)
        self.ap_uc.reg_write(A64.UC_ARM64_REG_SP, AP_STACK_BASE + AP_STACK_SIZE - 0x100)
        self.ap_uc.reg_write(A64.UC_ARM64_REG_LR, AP_CODE_EXIT)
        self.ap_uc.reg_write(A64.UC_ARM64_REG_X0, queue_id & 0xFFFFFFFF)
        self.ap_uc.reg_write(A64.UC_ARM64_REG_X1, req_addr)
        self.ap_uc.reg_write(A64.UC_ARM64_REG_X2, len(req_bytes))
        self.ap_uc.reg_write(A64.UC_ARM64_REG_X3, seq_id & 0xFFFFFFFF)
        self.ap_uc.reg_write(A64.UC_ARM64_REG_X4, reply_addr)
        self.ap_uc.emu_start(AP_SUBMIT_ENTRY, AP_CODE_EXIT, count=5000)
        rc = self.ap_uc.reg_read(A64.UC_ARM64_REG_W0)
        local_reply = bytes(self.ap_uc.mem_read(reply_addr, 16))
        return rc, local_reply

    def _run_ap_poll_rx(self) -> Tuple[int, bytes]:
        out_addr = AP_SCRATCH_BASE + 0x0800
        self.ap_uc.mem_write(out_addr, b"\x00" * 48)
        self.ap_uc.reg_write(A64.UC_ARM64_REG_SP, AP_STACK_BASE + AP_STACK_SIZE - 0x100)
        self.ap_uc.reg_write(A64.UC_ARM64_REG_LR, AP_CODE_EXIT)
        self.ap_uc.reg_write(A64.UC_ARM64_REG_X0, out_addr)
        self.ap_uc.emu_start(AP_POLL_RX_ENTRY, AP_CODE_EXIT, count=5000)
        rc = self.ap_uc.reg_read(A64.UC_ARM64_REG_W0)
        slot_bytes = bytes(self.ap_uc.mem_read(out_addr, 48))
        return rc, slot_bytes

    def run_cp_isr(self) -> int:
        """Execute Peer 1 ARM32 Thumb-2 `cp_ivshmem_irq_handler` inside Unicorn."""
        movwt_vma = CP_LOAD_BASE + max(0, self.cp_inspection.first_0x92840747_offset)
        comp_vma = CP_LOAD_BASE + max(0, self.cp_inspection.first_comp_movw_offset)
        self.cp_uc.reg_write(A32.UC_ARM_REG_SP, CP_STACK_BASE + CP_STACK_SIZE - 0x100)
        self.cp_uc.reg_write(A32.UC_ARM_REG_LR, CP_ISR_EXIT | 1)
        self.cp_uc.reg_write(A32.UC_ARM_REG_R0, movwt_vma)
        self.cp_uc.reg_write(A32.UC_ARM_REG_R1, comp_vma)
        self.cp_uc.emu_start(CP_ISR_ENTRY | 1, CP_ISR_EXIT, count=20000)
        return self.cp_uc.reg_read(A32.UC_ARM_REG_R0)

    def stage_lut_dma_window(self, lut_bytes: bytes) -> None:
        if len(lut_bytes) > SHM_DMA_LUT_WINDOW_BYTES:
            raise IvshmemBridgeError(
                f"3D LUT payload {len(lut_bytes)}B exceeds DMA window {SHM_DMA_LUT_WINDOW_BYTES}B"
            )
        self.ap_uc.mem_write(IVSHMEM_AP_SHM_BASE + SHM_DMA_LUT_OFFSET, lut_bytes)

    def send_uipc_from_ap(
        self,
        queue_id: int,
        payload_bytes: bytes,
        *,
        stage_lut_bytes: Optional[bytes] = None,
    ) -> CoEmulationRoundTripReceipt:
        """Execute full Dual-ISA `AArch64 -> Doorbell -> Thumb-2 -> Doorbell -> AArch64` cycle."""
        self._seq_counter += 1
        seq_id = self._seq_counter
        if stage_lut_bytes is not None:
            self.stage_lut_dma_window(stage_lut_bytes)

        req_opcode: Optional[int] = None
        if queue_id == UIPC_BB_TARGET_QUEUE and len(payload_bytes) >= 8:
            _m, op_raw, _dl, _fl = struct.unpack_from("<HHHH", payload_bytes, 0)
            req_opcode = op_raw

        trace_before = len(self.bus.doorbell_trace)
        malform_before = self._read_shm_u32(SHM_OFF_MALFORM_DROP_CNT)
        bp_before = self._read_shm_u32(SHM_OFF_BACKPRESSURE_CNT)

        rc, local_reply = self._run_ap_submit(queue_id, payload_bytes, seq_id)

        # Case A: P11 AP-side local filter (0x92d2091c or 0x91db059b)
        if rc == 1:
            reply_len = 2 if queue_id == RTC_QUEUE_ID else 12
            reply_slice = local_reply[:reply_len]
            return CoEmulationRoundTripReceipt(
                queue_id=f"0x{queue_id:08x}",
                seq_id=seq_id,
                opcode=None,
                request_bytes=len(payload_bytes),
                intercepted_by_p11=True,
                tx_enqueued=False,
                ap_doorbell_to_cp=False,
                cp_executed=False,
                cp_doorbell_to_ap=False,
                rx_completion_bytes=reply_len,
                rx_completion_hex=reply_slice.hex(),
                rx_completion_opcode=None,
                rx_hw_1000_alias_opcode=None,
                ibis_center_lock_energized=bool(self._read_shm_u32(SHM_OFF_IBIS_CENTER_LOCK)),
                lut_dma_acked_bytes=self._read_shm_u32(SHM_OFF_LUT_DMA_LAST_BYTES),
                backpressure_rejected=False,
                malformed_dropped=False,
                cp_mutation_bytes=self.verify_cp_immutability().cp_mutation_bytes,
            )

        # Case B: Backpressure (TX ring full) or invalid length on AP
        if rc != 0:
            bp_after = self._read_shm_u32(SHM_OFF_BACKPRESSURE_CNT)
            return CoEmulationRoundTripReceipt(
                queue_id=f"0x{queue_id:08x}",
                seq_id=seq_id,
                opcode=f"0x{req_opcode:04x}" if req_opcode is not None else None,
                request_bytes=len(payload_bytes),
                intercepted_by_p11=False,
                tx_enqueued=False,
                ap_doorbell_to_cp=False,
                cp_executed=False,
                cp_doorbell_to_ap=False,
                rx_completion_bytes=0,
                rx_completion_hex="",
                rx_completion_opcode=None,
                rx_hw_1000_alias_opcode=None,
                ibis_center_lock_energized=bool(self._read_shm_u32(SHM_OFF_IBIS_CENTER_LOCK)),
                lut_dma_acked_bytes=self._read_shm_u32(SHM_OFF_LUT_DMA_LAST_BYTES),
                backpressure_rejected=bp_after > bp_before,
                malformed_dropped=False,
                cp_mutation_bytes=self.verify_cp_immutability().cp_mutation_bytes,
            )

        # Case C: Forwarded to IVSHMEM TX Ring; check Doorbell -> Peer 1 Thumb-2 execution
        new_events = self.bus.doorbell_trace[trace_before:]
        ap_to_cp = any(
            ev.src_peer == PEER_ID_AP_MIRA and ev.dst_peer == PEER_ID_CP_CETUS and ev.delivered_irq
            for ev in new_events
        )
        cp_executed = False
        if PEER_ID_CP_CETUS in self.bus.pending_irq_peers:
            self.bus.pending_irq_peers.discard(PEER_ID_CP_CETUS)
            self.run_cp_isr()
            cp_executed = True

        after_cp_events = self.bus.doorbell_trace[trace_before:]
        cp_to_ap = any(
            ev.src_peer == PEER_ID_CP_CETUS and ev.dst_peer == PEER_ID_AP_MIRA and ev.delivered_irq
            for ev in after_cp_events
        )

        malform_after = self._read_shm_u32(SHM_OFF_MALFORM_DROP_CNT)
        malformed_dropped = malform_after > malform_before

        rx_hex = ""
        rx_len = 0
        rx_comp_op: Optional[str] = None
        rx_hw_op: Optional[str] = None
        lut_acked = 0
        if PEER_ID_AP_MIRA in self.bus.pending_irq_peers or (
            self._read_shm_u32(SHM_OFF_RX_HEAD) != self._read_shm_u32(SHM_OFF_RX_TAIL)
        ):
            self.bus.pending_irq_peers.discard(PEER_ID_AP_MIRA)
            poll_rc, slot_bytes = self._run_ap_poll_rx()
            if poll_rc == 0:
                rx_len = struct.unpack_from("<I", slot_bytes, 0x08)[0]
                comp_pkt = slot_bytes[0x10 : 0x10 + rx_len]
                rx_hex = comp_pkt.hex()
                _rm, rx_op_val, _rl, _rf, _rs = struct.unpack_from("<HHHHI", comp_pkt, 0)
                rx_comp_op = f"0x{rx_op_val:04x}"
                hw_alias = struct.unpack_from("<I", slot_bytes, 0x1C)[0]
                rx_hw_op = f"0x{hw_alias:04x}"
                lut_acked = struct.unpack_from("<I", slot_bytes, 0x24)[0]

        return CoEmulationRoundTripReceipt(
            queue_id=f"0x{queue_id:08x}",
            seq_id=seq_id,
            opcode=f"0x{req_opcode:04x}" if req_opcode is not None else None,
            request_bytes=len(payload_bytes),
            intercepted_by_p11=False,
            tx_enqueued=True,
            ap_doorbell_to_cp=ap_to_cp,
            cp_executed=cp_executed,
            cp_doorbell_to_ap=cp_to_ap,
            rx_completion_bytes=rx_len,
            rx_completion_hex=rx_hex,
            rx_completion_opcode=rx_comp_op,
            rx_hw_1000_alias_opcode=rx_hw_op,
            ibis_center_lock_energized=bool(self._read_shm_u32(SHM_OFF_IBIS_CENTER_LOCK)),
            lut_dma_acked_bytes=lut_acked,
            backpressure_rejected=False,
            malformed_dropped=malformed_dropped,
            cp_mutation_bytes=self.verify_cp_immutability().cp_mutation_bytes,
        )

    def enqueue_tx_without_cp_drain(self, payload_bytes: bytes) -> CoEmulationRoundTripReceipt:
        """Push directly onto IVSHMEM TX ring from Peer 0 AArch64 without running Peer 1 ISR (for backpressure tests)."""
        self._seq_counter += 1
        seq_id = self._seq_counter
        bp_before = self._read_shm_u32(SHM_OFF_BACKPRESSURE_CNT)
        rc, _ = self._run_ap_submit(UIPC_BB_TARGET_QUEUE, payload_bytes, seq_id)
        bp_after = self._read_shm_u32(SHM_OFF_BACKPRESSURE_CNT)
        return CoEmulationRoundTripReceipt(
            queue_id=f"0x{UIPC_BB_TARGET_QUEUE:08x}",
            seq_id=seq_id,
            opcode=None,
            request_bytes=len(payload_bytes),
            intercepted_by_p11=False,
            tx_enqueued=(rc == 0),
            ap_doorbell_to_cp=(rc == 0),
            cp_executed=False,
            cp_doorbell_to_ap=False,
            rx_completion_bytes=0,
            rx_completion_hex="",
            rx_completion_opcode=None,
            rx_hw_1000_alias_opcode=None,
            ibis_center_lock_energized=bool(self._read_shm_u32(SHM_OFF_IBIS_CENTER_LOCK)),
            lut_dma_acked_bytes=0,
            backpressure_rejected=(rc != 0 and bp_after > bp_before),
            malformed_dropped=False,
            cp_mutation_bytes=self.verify_cp_immutability().cp_mutation_bytes,
        )

    def verify_cp_immutability(self) -> CpImmutabilityAudit:
        mapped_cp = bytes(self.cp_uc.mem_read(CP_LOAD_BASE, len(self.cp_bytes)))
        sha_after = hashlib.sha256(mapped_cp).hexdigest()
        diff_bytes = 0
        if sha_after != self.cp_sha256_before:
            diff_bytes = sum(1 for a, b in zip(self.cp_bytes, mapped_cp) if a != b) + abs(
                len(self.cp_bytes) - len(mapped_cp)
            )
        return CpImmutabilityAudit(
            cp_load_base=f"0x{CP_LOAD_BASE:08x}",
            cp_byte_length=len(self.cp_bytes),
            sha256_before=self.cp_sha256_before,
            sha256_after=sha_after,
            cp_mutation_bytes=diff_bytes,
            immutable=(diff_bytes == 0 and sha_after == self.cp_sha256_before),
        )

    def telemetry_snapshot(self) -> Dict[str, int]:
        return {
            "tx_head": self._read_shm_u32(SHM_OFF_TX_HEAD),
            "tx_tail": self._read_shm_u32(SHM_OFF_TX_TAIL),
            "rx_head": self._read_shm_u32(SHM_OFF_RX_HEAD),
            "rx_tail": self._read_shm_u32(SHM_OFF_RX_TAIL),
            "p11_local_rtc_count": self._read_shm_u32(SHM_OFF_P11_RTC_CNT),
            "p11_local_handle_count": self._read_shm_u32(SHM_OFF_P11_HANDLE_CNT),
            "cp_doorbell_irq_count": self._read_shm_u32(SHM_OFF_CP_IRQ_CNT),
            "ap_doorbell_irq_count": self._read_shm_u32(SHM_OFF_AP_IRQ_CNT),
            "ibis_center_lock_state": self._read_shm_u32(SHM_OFF_IBIS_CENTER_LOCK),
            "ibis_steadyshot_mode": self._read_shm_u32(SHM_OFF_IBIS_MODE),
            "lut_dma_ack_count": self._read_shm_u32(SHM_OFF_LUT_DMA_ACK_CNT),
            "lut_dma_last_bytes": self._read_shm_u32(SHM_OFF_LUT_DMA_LAST_BYTES),
            "last_error_code": self._read_shm_u32(SHM_OFF_LAST_ERROR),
            "malform_drop_count": self._read_shm_u32(SHM_OFF_MALFORM_DROP_CNT),
            "backpressure_count": self._read_shm_u32(SHM_OFF_BACKPRESSURE_CNT),
            "cp_verified_0x92840747": self._read_shm_u32(SHM_OFF_CP_VERIFIED_QUEUE),
            "cp_verified_completion_imm": self._read_shm_u32(SHM_OFF_CP_VERIFIED_COMP_IMM),
            "cp_verified_load_base": self._read_shm_u32(SHM_OFF_CP_VERIFIED_BASE),
        }


# ---------------------------------------------------------------------------
# UIPC Packet Builders & Session Factory
# ---------------------------------------------------------------------------


def build_0x92840747_packet(opcode: int, payload: bytes = b"") -> bytes:
    total_len = 8 + len(payload)
    if total_len < 8 or total_len > SHM_MAX_PAYLOAD_BYTES:
        raise IvshmemBridgeError(f"Invalid UIPC BB packet length {total_len}")
    return struct.pack("<HHHH", UIPC_BB_MAGIC, opcode & 0xFFFF, total_len, UIPC_BB_FLAGS) + payload


def build_0x0165_lut_dma_packet(
    *,
    lut_bytes: int = LUT_8BIT_ALIGNED_BYTES,
    sram_offset: int = 0x1000,
    reg_offset: int = 0x20000,
    reg_size: int = 0x400,
) -> bytes:
    inline_sz = lut_bytes if lut_bytes <= LUT_DMA_SRAM_REG_THRESHOLD else 0
    sram_sz = lut_bytes if lut_bytes > LUT_DMA_SRAM_REG_THRESHOLD else 0
    sram_off = sram_offset if lut_bytes > LUT_DMA_SRAM_REG_THRESHOLD else 0
    reg_off = reg_offset if lut_bytes > LUT_DMA_SRAM_REG_THRESHOLD else 0
    reg_s = reg_size if lut_bytes > LUT_DMA_SRAM_REG_THRESHOLD else 0
    return struct.pack(
        "<HHHHBBHIIIIII",
        UIPC_BB_MAGIC,
        OPCODE_LUT_DMA,
        LUT_DMA_PACKET_BYTES,
        UIPC_BB_FLAGS,
        3,
        0,
        0,
        1,
        inline_sz,
        sram_off,
        sram_sz,
        reg_off,
        reg_s,
    )


def build_0x0166_lut_toggle_packet(*, enable: bool) -> bytes:
    return struct.pack(
        "<HHHHH",
        UIPC_BB_MAGIC,
        OPCODE_LUT_TOGGLE,
        LUT_TOGGLE_PACKET_BYTES,
        UIPC_BB_FLAGS,
        1 if enable else 0,
    )


_BUNDLE_CACHE: Dict[
    Tuple[str, str, str, str],
    Tuple[bytes, CpBinaryInspection, ApBinaryInspection],
] = {}


def create_dual_ap_cp_session(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
    rtc_valid: bool = True,
) -> DualApCpIvshmemSession:
    """Create a Dual-ISA Unicorn session using real local donors (`O_RDONLY`) or clean-room fixtures."""
    donor_paths = resolve_phase24_donor_paths(env=env)
    use_clean_room = (
        bool(force_clean_room)
        if force_clean_room is not None
        else (is_forced_clean_room(env) or not all(p.is_file() for p in donor_paths.values()))
    )
    if use_clean_room:
        source_mode = "CLEAN_ROOM_SYNTHETIC"
        cache_key = (source_mode, "", "", "")
        if cache_key not in _BUNDLE_CACHE:
            blobs = build_clean_room_synthetic_binaries()
            cp_insp = inspect_cp_binary(blobs["fx3_cpapp"], source_mode=source_mode)
            ap_insp = inspect_ap_binaries(
                blobs["fx6_appfw"],
                blobs["fx6_libosal_uipc"],
                source_mode=source_mode,
            )
            _BUNDLE_CACHE[cache_key] = (blobs["fx3_cpapp"], cp_insp, ap_insp)
    else:
        source_mode = "LOCAL_DONOR_READONLY"
        cache_key = (
            source_mode,
            str(donor_paths["fx3_cpapp"]),
            str(donor_paths["fx6_appfw"]),
            str(donor_paths["fx6_libosal_uipc"]),
        )
        if cache_key not in _BUNDLE_CACHE:
            blobs = {
                "fx3_cpapp": read_donor_bytes_readonly(donor_paths["fx3_cpapp"]),
                "fx6_appfw": read_donor_bytes_readonly(donor_paths["fx6_appfw"]),
                "fx6_libosal_uipc": read_donor_bytes_readonly(donor_paths["fx6_libosal_uipc"]),
            }
            cp_insp = inspect_cp_binary(blobs["fx3_cpapp"], source_mode=source_mode)
            ap_insp = inspect_ap_binaries(
                blobs["fx6_appfw"],
                blobs["fx6_libosal_uipc"],
                source_mode=source_mode,
            )
            _BUNDLE_CACHE[cache_key] = (blobs["fx3_cpapp"], cp_insp, ap_insp)

    cp_bytes, cp_insp, ap_insp = _BUNDLE_CACHE[cache_key]
    return DualApCpIvshmemSession(
        cp_bytes=cp_bytes,
        cp_inspection=cp_insp,
        ap_inspection=ap_insp,
        source_mode=source_mode,
        rtc_valid=rtc_valid,
    )


# ---------------------------------------------------------------------------
# External Dual-QEMU `ivshmem-doorbell` + `ivshmem-flat` Topology Generator
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DualQemuIvshmemTopologySpec:
    schema: str
    socket_path: str
    shm_size_mib: int
    vectors: int
    ivshmem_server_cmd: Tuple[str, ...]
    peer0_ap_mira: Dict[str, object]
    peer1_cp_cetus: Dict[str, object]
    mmio_register_map: Dict[str, str]
    redlines: Dict[str, object]


def build_dual_qemu_ivshmem_topology_spec(
    *,
    socket_path: str = "/tmp/fx3-dual-ivshmem.sock",
    shm_size_mib: int = 4,
    vectors: int = 2,
    kernel_path: str = "vmlinux.bin",
    initrd_path: str = "initrd.cpio",
    dtb_path: str = "virt-fx3.dtb",
    cpapp_path: str = "cpapp-b.bin",
) -> DualQemuIvshmemTopologySpec:
    """Generate validated `ivshmem-server` + `ivshmem-doorbell` (AP) + `ivshmem-flat` (CP) QEMU CLI topology."""
    if shm_size_mib < 1 or (shm_size_mib & (shm_size_mib - 1)) != 0:
        raise IvshmemBridgeError(f"IVSHMEM shared memory size must be a power-of-two MiB >= 1, got {shm_size_mib}")
    if vectors < 1 or vectors > 32:
        raise IvshmemBridgeError(f"IVSHMEM vectors must be in 1..32, got {vectors}")
    if not socket_path or len(socket_path.encode("utf-8")) >= 100:
        raise IvshmemBridgeError(f"Unix socket path must be 1..99 bytes: {socket_path!r}")

    server_cmd = (
        "ivshmem-server",
        "-F",
        "-S",
        socket_path,
        "-l",
        f"{shm_size_mib}M",
        "-n",
        str(vectors),
    )

    ap_cmd = (
        "qemu-system-aarch64",
        "-machine",
        "virt,gic-version=2,secure=off",
        "-accel",
        "tcg",
        "-cpu",
        "cortex-a35",
        "-smp",
        "1",
        "-m",
        "2048",
        "-display",
        "none",
        "-nodefaults",
        "-nic",
        "none",
        "-no-reboot",
        "-kernel",
        kernel_path,
        "-initrd",
        initrd_path,
        "-device",
        f"loader,file={dtb_path},addr=0x400002000,force-raw=on",
        "-chardev",
        f"socket,path={socket_path},id=fx3_ivshmem_chr",
        "-device",
        f"ivshmem-doorbell,chardev=fx3_ivshmem_chr,vectors={vectors}",
    )

    cp_cmd = (
        "qemu-system-arm",
        "-machine",
        "virt",
        "-accel",
        "tcg",
        "-cpu",
        "cortex-r5",
        "-smp",
        "1",
        "-m",
        "64",
        "-display",
        "none",
        "-nodefaults",
        "-nic",
        "none",
        "-no-reboot",
        "-device",
        f"loader,file={cpapp_path},addr=0x{CP_LOAD_BASE:08x},force-raw=on",
        "-chardev",
        f"socket,path={socket_path},id=cp_ivshmem_chr",
        "-device",
        (
            f"ivshmem-flat,chardev=cp_ivshmem_chr,"
            f"x-irq-qompath=/machine/gic/unnamed-gpio-in[16],"
            f"x-bus-qompath=/machine/sysbus"
        ),
    )

    return DualQemuIvshmemTopologySpec(
        schema=PHASE_24_SCHEMA,
        socket_path=socket_path,
        shm_size_mib=shm_size_mib,
        vectors=vectors,
        ivshmem_server_cmd=server_cmd,
        peer0_ap_mira={
            "peer_id": PEER_ID_AP_MIRA,
            "soc": "CXD90057",
            "arch": "aarch64",
            "device": "ivshmem-doorbell",
            "mmio_bar0_base": f"0x{IVSHMEM_AP_MMIO_BASE:08x}",
            "shm_bar2_base": f"0x{IVSHMEM_AP_SHM_BASE:08x}",
            "model_env": {"FX3_VM_ESRAM_RAM": "1", "FX3_VM_HIGH_DDR": "1"},
            "argv": list(ap_cmd),
        },
        peer1_cp_cetus={
            "peer_id": PEER_ID_CP_CETUS,
            "soc": "CXD90058",
            "arch": "arm32-thumb2-cortex-r5",
            "device": "ivshmem-flat",
            "mmio_base": f"0x{IVSHMEM_CP_MMIO_BASE:08x}",
            "shm_base": f"0x{IVSHMEM_CP_SHM_BASE:08x}",
            "cp_load_base": f"0x{CP_LOAD_BASE:08x}",
            "cp_read_only": True,
            "cp_mutation_bytes": CP_MUTATION_BYTES,
            "argv": list(cp_cmd),
        },
        mmio_register_map={
            "0x00": "INTRMASK (RW)",
            "0x04": "INTRSTATUS (RO clear-on-read)",
            "0x08": "IVPOSITION (RO peer_id)",
            "0x0C": "DOORBELL (WO (peer_id << 16) | vector)",
        },
        redlines={
            "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
            "cp_mutation_bytes": CP_MUTATION_BYTES,
            "p11_queues_isolated_on_ap": [f"0x{RTC_QUEUE_ID:08x}", f"0x{HANDLE_QUEUE_ID:08x}"],
            "shared_uipc_queue": f"0x{UIPC_BB_TARGET_QUEUE:08x}",
        },
    )


# ---------------------------------------------------------------------------
# End-to-End Phase 24 Audit Runner
# ---------------------------------------------------------------------------


def run_phase24_co_emulation_audit(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run full Phase 24 Dual-ISA Unicorn co-emulation & donor/clean-room audit."""
    t0 = time.monotonic()
    session = create_dual_ap_cp_session(force_clean_room=force_clean_room, env=env)

    # 1. P11 isolation tests (must NEVER enter IVSHMEM TX ring or wake Peer 1)
    rtc_receipt = session.send_uipc_from_ap(RTC_QUEUE_ID, bytes((0x03, 0x00)))
    handle_receipt = session.send_uipc_from_ap(
        HANDLE_QUEUE_ID,
        struct.pack("<III", HANDLE_REG_CMD, 0, 0x81CC0501),
    )

    # 2. Developing FHD + Cine EI Dual Base ISO 800 / 12800 round-trips
    r_0416 = session.send_uipc_from_ap(UIPC_BB_TARGET_QUEUE, build_0x92840747_packet(OPCODE_VIDEO_MODE_PROCAM))
    r_0169 = session.send_uipc_from_ap(
        UIPC_BB_TARGET_QUEUE,
        build_0x92840747_packet(OPCODE_DEVELOP_A, struct.pack("<BBH", 1, 0, 800)),
    )
    r_016a = session.send_uipc_from_ap(
        UIPC_BB_TARGET_QUEUE,
        build_0x92840747_packet(OPCODE_DEVELOP_B, struct.pack("<HH", 12800, 1)),
    )

    # 3. 33^3 3D LUT DMA (0x0165 36B > 0xbb80 + 107,812B DMA window + 0x0166 10B toggle)
    lut_payload = (b"FX3LUT33" * ((LUT_8BIT_ALIGNED_BYTES // 8) + 1))[:LUT_8BIT_ALIGNED_BYTES]
    r_0165 = session.send_uipc_from_ap(
        UIPC_BB_TARGET_QUEUE,
        build_0x0165_lut_dma_packet(lut_bytes=LUT_8BIT_ALIGNED_BYTES),
        stage_lut_bytes=lut_payload,
    )
    r_0166 = session.send_uipc_from_ap(
        UIPC_BB_TARGET_QUEUE,
        build_0x0166_lut_toggle_packet(enable=True),
    )

    # 4. 5-axis IBIS center-lock / SteadyShot
    r_0400 = session.send_uipc_from_ap(
        UIPC_BB_TARGET_QUEUE,
        build_0x92840747_packet(OPCODE_TC_MODE, struct.pack("<BBH", 1, 1, 0)),
    )

    immut = session.verify_cp_immutability()
    telemetry = session.telemetry_snapshot()
    topo = build_dual_qemu_ivshmem_topology_spec()

    receipts = (rtc_receipt, handle_receipt, r_0416, r_0169, r_016a, r_0165, r_0166, r_0400)
    all_passed = (
        immut.immutable
        and immut.cp_mutation_bytes == 0
        and rtc_receipt.intercepted_by_p11
        and not rtc_receipt.cp_executed
        and handle_receipt.intercepted_by_p11
        and not handle_receipt.cp_executed
        and all(
            r.tx_enqueued
            and r.ap_doorbell_to_cp
            and r.cp_executed
            and r.cp_doorbell_to_ap
            and r.ibis_center_lock_energized
            for r in (r_0416, r_0169, r_016a, r_0165, r_0166, r_0400)
        )
        and r_0165.rx_completion_opcode == f"0x{OPCODE_LUT_DMA | UIPC_BB_COMPLETION_BIT:04x}"
        and r_0165.lut_dma_acked_bytes == LUT_8BIT_ALIGNED_BYTES
        and telemetry["cp_verified_0x92840747"] == 1
        and telemetry["cp_verified_load_base"] == 1
        and telemetry["cp_doorbell_irq_count"] == 6
        and telemetry["ap_doorbell_irq_count"] == 6
    )

    return {
        "schema": PHASE_24_SCHEMA,
        "version": PHASE_24_VERSION,
        "source_mode": session.source_mode,
        "all_checks_passed": all_passed,
        "elapsed_seconds": round(time.monotonic() - t0, 4),
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "cp_mutation_bytes": immut.cp_mutation_bytes,
        "cp_immutability": asdict(immut),
        "cp_inspection": asdict(session.cp_inspection),
        "ap_inspection": asdict(session.ap_inspection),
        "telemetry": telemetry,
        "doorbell_event_count": len(session.bus.doorbell_trace),
        "receipts": [asdict(r) for r in receipts],
        "qemu_topology": asdict(topo),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dual_ap_cp_ivshmem_bridge.py",
        description="Phase 24 Dual-ISA (CXD90057 AArch64 <-> CXD90058 ARM32 Thumb-2) IVSHMEM Co-Emulation Bridge",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--topology", action="store_true", help="Print Dual-QEMU ivshmem topology JSON only")
    args = parser.parse_args(argv)

    if args.topology:
        sys.stdout.write(json.dumps(asdict(build_dual_qemu_ivshmem_topology_spec()), indent=2) + "\n")
        return 0

    rep = run_phase24_co_emulation_audit(force_clean_room=True if args.clean_room else None)
    if args.json:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    else:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        tel = rep["telemetry"]
        sys.stdout.write(
            f"[{status}] Phase 24 Dual-ISA IVSHMEM Bridge ({rep['source_mode']}) in {rep['elapsed_seconds']}s | "
            f"cp_mutation_bytes={rep['cp_mutation_bytes']} | "
            f"cp_irqs={tel['cp_doorbell_irq_count']} ap_irqs={tel['ap_doorbell_irq_count']} "
            f"p11_rtc={tel['p11_local_rtc_count']} p11_handle={tel['p11_local_handle_count']} "
            f"lut_acks={tel['lut_dma_ack_count']}\n"
        )
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
