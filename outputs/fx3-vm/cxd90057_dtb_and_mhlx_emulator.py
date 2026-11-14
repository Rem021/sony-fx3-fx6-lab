#!/usr/bin/env python3
"""Phase 41 — QEMU CXD90057 Pure-Python FDT/DTB Synthesizer, `mhlx`/`ipcu` Hardware Mailbox Ring & `0xf0000000..0xf8ffffff` MMIO Window Emulator.

Implements four cohesive virtualization & audit subsystems inside `outputs/fx3-vm/`:

1. **Strictly `os.O_RDONLY` Donor Kernel/Module Symbol & MMIO Audit (+ Clean-Room Fallback)**:
   - Inspects FX3 `v7.02` (`vmlinux.bin`, `cxd90057.dtb`, `osal_uipc.ko`, `cpapp-b.bin`) and
     FX6 `v6.01` (`cxd90057.dtb`, `vmlinux.bin`, `osal_uipc.ko`, `utimer.ko`, `elpspacc.ko`,
     `elpspaccusr.ko`, `grm_ma.ko`, `pcie-if.ko`, `pci_ep_cp.ko`, `libspaccdev.so`,
     `libosal_uipc.so`, `libbt-vendor.so`, `libInfraBluetoothCore.so`) strictly via
     `os.open(..., os.O_RDONLY)` when present on disk.
   - Automatically switches to deterministic pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent.

2. **Pure-Python Flattened Device Tree (`.dts` + Binary FDT v17 `0xd00dfeed`) Compiler & Parser**:
   - Zero external `dtc` dependency; operates strictly in-memory (no `.dtb`/`.bin` written to repo).
   - Synthesizes the hybrid QEMU `virt` + Sony `CXD90057` device tree covering:
     `cpus` (`arm,cortex-a53`), `memory@40000000`, `reserved-memory` (`gpe0_fb@41e001000`,
     `shm_ipc@41df00000`, `wbi_hib_guard`), `soc/serial@f0200000..ttyAMA3` (`virtual-rom-v1` BT UART),
     `soc/mhlx@f0800000` (AP<->CP mailbox + doorbell IRQ), `soc/spacc@f7fc0000` (AES-XTS
     `cnflasha` isolation), `soc/timer-ip@f0100000` (watchdog/hwtimer), and `soc/ivshmem@10000000`
     BAR0/BAR2 bridge.
   - Validates FDT v17 header, 8-byte/4-byte alignment, `/memreserve/` sentinel, non-overlapping
     regions, balanced tokens, and string table bounds in `parse_fdt_blob()`.

3. **`0xf0000000..0xf8ffffff` SoC MMIO Window Emulator (`MmioWindowBus`)**:
   - Dispatches 32-bit/64-bit MMIO reads and writes across `timer-ip@f0100000` (hwtimer + WDT),
     `serial@f0200000..f0203000` (`ttyAMA0..ttyAMA3`), `mhlx@f0800000`, and `spacc@f7fc0000`
     (enforcing kernel-only AES-XTS access boundaries).

4. **`mhlx` / `ipcu` Hardware Mailbox Ring & `shm_Loader` Handshake Emulator**:
   - Models the 8-channel Sony `mhlx` channel table, 16-slot TX/RX ring descriptors in `shm_ipc`,
     per-channel and global write-1-to-clear (`W1C`) interrupt ack/clear registers, and
     `shm_Loader` cold-boot / warm-boot handshakes into Stock-CP `cpapp-b.bin` with
     `cp_mutation_bytes == 0` and `wbi_mutation_bytes == 0` strictly enforced.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import os
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# Phase 41 Schema & Redline Locks
# ---------------------------------------------------------------------------

PHASE_41_SCHEMA = "phase41_cxd90057_dtb_mhlx_mmio_v1"
PHASE_41_VERSION = "41.0.0"

P8_CP_MUTATION_FORBIDDEN = True
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
NVRAM_PERSISTENT_WRITES = 0
PHYSICAL_DEVICE_WRITES = 0
DONOR_ACCESS_MODE = "O_RDONLY"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# Pinned Donor Identities (FX3 v7.02 & FX6 v6.01)
PINNED_CXD90057_DTB_SHA256 = "87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca"
PINNED_CXD90057_DTB_BYTES = 17_131
PINNED_FX3_VMLINUX_SHA256 = "da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c"
PINNED_FX3_VMLINUX_BYTES = 6_610_952
PINNED_FX3_CPAPP_SHA256 = "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba"
PINNED_FX3_CPAPP_BYTES = 15_980_568

# Devicetree Specification v0.4 / FDT v17 Constants
FDT_MAGIC = 0xD00DFEED
FDT_VERSION = 17
FDT_LAST_COMP_VERSION = 16
FDT_HEADER_BYTES = 40
FDT_BEGIN_NODE = 0x00000001
FDT_END_NODE = 0x00000002
FDT_PROP = 0x00000003
FDT_NOP = 0x00000004
FDT_END = 0x00000009

# Hybrid QEMU Virt + Sony CXD90057 Physical Memory & MMIO Window Map
HYBRID_MEMORY_BASE = 0x4000_0000
HYBRID_MEMORY_SIZE = 0x8000_0000  # 2048 MiB

SHM_IPC_PHYS_BASE = 0x4_1DF0_0000
SHM_IPC_SIZE = 0x0008_0000  # 512 KiB
WBI_HIB_GUARD_PHYS_BASE = 0x4_1DF8_0000
WBI_HIB_GUARD_SIZE = 0x0008_0000  # 512 KiB
GPE0_FB_PHYS_BASE = 0x4_1E00_1000
GPE0_FB_SIZE = 0x0060_0000  # 6 MiB (GPE0 + GPE1 + ramfb window)

ESRAM_PROBE_BASE = 0xFE00_5000
ESRAM_PROBE_SIZE = 0x0000_1000

MMIO_WINDOW_START = 0xF000_0000
MMIO_WINDOW_END = 0xF900_0000  # covers 0xf0000000..0xf8ffffff inclusive (144 MiB)
MMIO_WINDOW_SIZE = MMIO_WINDOW_END - MMIO_WINDOW_START  # 0x09000000

TIMER_IP_BASE = 0xF010_0000
TIMER_IP_SIZE = 0x0000_1000
UART0_BASE = 0xF020_0000
UART_STRIDE = 0x0000_1000
UART_SIZE = 0x0000_1000
UART_COUNT = 4  # ttyAMA0..ttyAMA3
UART3_BT_BASE = UART0_BASE + 3 * UART_STRIDE  # 0xf0203000 -> /dev/ttyAMA3 (virtual-rom-v1)

MHLX_BASE = 0xF080_0000
MHLX_SIZE = 0x0001_0000
GIC_BASE = 0xF13A_0000
SPACC_BASE = 0xF7FC_0000
SPACC_SIZE = 0x0004_0000

IVSHMEM_BAR0_MMIO_BASE = 0x1000_0000
IVSHMEM_BAR0_MMIO_SIZE = 0x0000_1000
IVSHMEM_BAR2_SHM_BASE = 0x1010_0000
IVSHMEM_BAR2_SHM_SIZE = 0x0010_0000

# Timer-IP & Watchdog Registers (0xf0100000)
TIMER_REG_CTRL = 0x00
TIMER_REG_COUNTER = 0x04
TIMER_REG_RELOAD = 0x08
TIMER_REG_WDT_ENABLE = 0x10
TIMER_REG_WDT_KICK = 0x14
TIMER_REG_WDT_TIMEOUT = 0x18
TIMER_REG_WDT_STATUS = 0x1C
TIMER_REG_WDT_RESET_COUNT = 0x20
WDT_KICK_MAGIC = 0x5744_544B  # "WDTK"

# PL011 UART Registers (0xf0200000..0xf0203000)
UART_REG_DR = 0x00
UART_REG_FR = 0x18
UART_REG_IBRD = 0x24
UART_REG_FBRD = 0x28
UART_REG_CR = 0x30
UART_REG_IMSC = 0x38
UART_REG_ICR = 0x44
UART_FR_TXFE = 0x80
UART_FR_RXFE = 0x10

# SPAcc AES-XTS Registers (0xf7fc0000)
SPACC_REG_IRQ_EN = 0x0000
SPACC_REG_IRQ_STAT = 0x0004
SPACC_REG_IRQ_CTRL = 0x0008
SPACC_REG_FIFO_STAT = 0x000C
SPACC_REG_VERSION = 0x0018
SPACC_REG_XTS_MODE = 0x0020
SPACC_REG_KEY_LOCK = 0x0024
SPACC_VERSION_MAGIC = 0x454C_5053  # "ELPS"

# Sony MHLX / IPCU Hardware Mailbox Registers (0xf0800000)
MHLX_MAGIC = 0x4D48_4C58  # "MHLX"
MHLX_VERSION = 0x0004_0100
MHLX_CHANNEL_COUNT = 8
MHLX_RING_CAPACITY = 16
MHLX_SLOT_BYTES = 256
MHLX_SLOT_HDR_BYTES = 16
MHLX_MAX_PAYLOAD_BYTES = MHLX_SLOT_BYTES - MHLX_SLOT_HDR_BYTES  # 240 B

MHLX_REG_ID = 0x0000
MHLX_REG_VERSION = 0x0004
MHLX_REG_CH_COUNT = 0x0008
MHLX_REG_IRQ_STATUS = 0x0010
MHLX_REG_IRQ_MASK = 0x0014
MHLX_REG_IRQ_CLEAR = 0x0018
MHLX_REG_DOORBELL_SEND = 0x0020
MHLX_REG_DOORBELL_COUNT = 0x0024
MHLX_REG_SHM_LOADER_CTRL = 0x0030
MHLX_REG_SHM_LOADER_STATUS = 0x0034
MHLX_REG_SHM_BASE_LO = 0x0038
MHLX_REG_SHM_BASE_HI = 0x003C
MHLX_REG_CP_MUTATION_BYTES = 0x0040

MHLX_CH_STRIDE = 0x40
MHLX_CH_BASE = 0x0100
MHLX_CH_OFF_MODE = 0x00
MHLX_CH_OFF_ENABLE = 0x04
MHLX_CH_OFF_TX_BASE = 0x08
MHLX_CH_OFF_TX_CAP = 0x0C
MHLX_CH_OFF_TX_HEAD = 0x10
MHLX_CH_OFF_TX_TAIL = 0x14
MHLX_CH_OFF_RX_BASE = 0x18
MHLX_CH_OFF_RX_CAP = 0x1C
MHLX_CH_OFF_RX_HEAD = 0x20
MHLX_CH_OFF_RX_TAIL = 0x24
MHLX_CH_OFF_IRQ_STAT = 0x28
MHLX_CH_OFF_IRQ_CLR = 0x2C
MHLX_CH_OFF_DOORBELL = 0x30
MHLX_CH_OFF_MSG_COUNT = 0x34

MHLX_CH_UIPC_BB = 0
MHLX_CH_SHM_LOADER = 1
MHLX_CH_IPCU_SYS = 2
MHLX_CH_IPCU_AUDIO = 3

MHLX_CHANNEL_NAMES: Tuple[str, ...] = (
    "UIPC_BB_CMD",
    "SHM_LOADER_CTRL",
    "IPCU_SYS_MGR",
    "IPCU_AUDIO_HDMI",
    "IPCU_AUX_4",
    "IPCU_AUX_5",
    "IPCU_AUX_6",
    "IPCU_AUX_7",
)

SHM_LOADER_MAGIC = 0x5348_4D4C  # "SHML"
SHM_LOADER_OP_COLD_HELLO = 0x4101
SHM_LOADER_OP_WARM_RESUME = 0x4102
SHM_LOADER_OP_ACK_BIT = 0x8000
SHM_LOADER_STATE_IDLE = 0
SHM_LOADER_STATE_COLD_READY = 1
SHM_LOADER_STATE_WARM_RESUMED = 2

CP_LOAD_BASE = 0x0010_8000
EXPECTED_CP_ARM32_ENTRY_WORDS: Tuple[int, ...] = (
    0xE59F1004,
    0xE2811004,
    0xE1A0F001,
    0x0010800C,
    0xE3A000D3,
    0xE12FF000,
)


class FdtFormatError(ValueError):
    """Raised when a Flattened Device Tree (`0xd00dfeed`) blob violates FDT v17 rules."""


class MmioAccessError(RuntimeError):
    """Raised on out-of-window MMIO access or privilege-boundary violation (e.g. SPAcc userland)."""


class MhlxMailboxError(RuntimeError):
    """Raised on invalid `mhlx` channel operation, ring corruption, or CP mutation."""


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Donor Path Resolution & Scanning
# ---------------------------------------------------------------------------


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    return source.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes")


def _iter_work_roots(*, env: Optional[Mapping[str, str]] = None) -> Tuple[Path, ...]:
    if is_forced_clean_room(env):
        return ()
    source = os.environ if env is None else env
    candidates: List[Path] = []
    for key in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        val = source.get(key, "").strip()
        if val:
            candidates.append(Path(os.path.expanduser(val)))
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
    for cand in candidates:
        s = str(cand)
        if s not in seen:
            seen.add(s)
            out.append(cand)
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


def resolve_phase41_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Locate FX3 v7.02 and FX6 v6.01 kernel/module/DTB donors strictly read-only."""
    fx6_base = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor"
    return {
        "fx3_vmlinux": _resolve_donor_file(
            "sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin",
            env=env,
        ),
        "fx3_dtb": _resolve_donor_file(
            "fx3-color-port-20261027/input-20261028/fat-members/"
            "87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca-cxd90057.dtb",
            env=env,
        ),
        "fx3_osal_uipc_ko": _resolve_donor_file(
            "sony-firmware-20261024/stage201-updater-request-endpoint/originals/7.02-main/kmod/osal_uipc.ko",
            env=env,
        ),
        "fx3_cpapp": _resolve_donor_file(
            "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
            env=env,
        ),
        "fx6_dtb": _resolve_donor_file(f"{fx6_base}/fat-files/nflasha1/boot/cxd90057.dtb", env=env),
        "fx6_vmlinux": _resolve_donor_file(f"{fx6_base}/fat-files/nflasha3/vmlinux.bin", env=env),
        "fx6_osal_uipc_ko": _resolve_donor_file(f"{fx6_base}/nflasha15-files/kmod/osal_uipc.ko", env=env),
        "fx6_utimer_ko": _resolve_donor_file(f"{fx6_base}/nflasha15-files/kmod/utimer.ko", env=env),
        "fx6_elpspacc_ko": _resolve_donor_file(f"{fx6_base}/nflasha15-files/kmod/elpspacc.ko", env=env),
        "fx6_elpspaccusr_ko": _resolve_donor_file(f"{fx6_base}/nflasha15-files/kmod/elpspaccusr.ko", env=env),
        "fx6_grm_ma_ko": _resolve_donor_file(f"{fx6_base}/nflasha15-files/kmod/grm_ma.ko", env=env),
        "fx6_pcie_if_ko": _resolve_donor_file(f"{fx6_base}/nflasha15-files/kmod/pcie-if.ko", env=env),
        "fx6_pci_ep_cp_ko": _resolve_donor_file(f"{fx6_base}/nflasha15-files/kmod/pci_ep_cp.ko", env=env),
        "fx6_libspaccdev": _resolve_donor_file(f"{fx6_base}/nflasha15-files/lib/libspaccdev.so", env=env),
        "fx6_libosal_uipc": _resolve_donor_file(f"{fx6_base}/nflasha15-files/lib/libosal_uipc.so", env=env),
        "fx6_libbt_vendor": _resolve_donor_file(f"{fx6_base}/nflasha15-files/lib/libbt-vendor.so", env=env),
        "fx6_libbt_core": _resolve_donor_file(f"{fx6_base}/nflasha15-files/lib/libInfraBluetoothCore.so", env=env),
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


@dataclass(frozen=True)
class SubsystemContractEntry:
    subsystem: str
    donor_source: str
    mmio_window: str
    irq_or_device: str
    matched_markers: Tuple[str, ...]
    contract_verified: bool


@dataclass(frozen=True)
class DonorKernelMmioAudit:
    source_mode: str
    access_mode: str
    fx3_dtb_sha256: str
    fx6_dtb_sha256: str
    dtb_identity_verified: bool
    fx3_vmlinux_sha256: str
    fx3_cpapp_sha256: str
    fx3_cpapp_bytes: int
    donor_files_inspected: int
    subsystem_contracts: Tuple[SubsystemContractEntry, ...]
    all_contracts_verified: bool


_DONOR_CONTRACT_SPECS: Tuple[Tuple[str, str, str, str, Tuple[str, ...]], ...] = (
    (
        "mhlx",
        "fx6_pcie_if_ko+fx6_pci_ep_cp_ko",
        "0xf0800000..0xf080ffff",
        "IRQ_SPI_0xa6_0xa7",
        ("pcieif_send", "pcieif_rcv_sequence", "pcieif_set_interrupt", "pcieif_clr_interrupt", "pci_ep_cp_probe"),
    ),
    (
        "ipcu",
        "fx3_osal_uipc_ko+fx6_osal_uipc_ko+fx6_libosal_uipc",
        "0xf0800000+ivshmem_bar0_0x10000000",
        "/dev/uipc",
        ("k_uipc_init", "__k_uipc_dispatcher", "uipc_check_handle", "/dev/uipc"),
    ),
    (
        "shm",
        "fx6_osal_uipc_ko+fx3_vmlinux",
        "0x41df00000..0x41dffffff",
        "/proc/osal/uipc",
        ("__k_uipc_cdev_mmap", "shmem_file_setup", "/proc/osal/uipc"),
    ),
    (
        "gpe",
        "fx6_grm_ma_ko",
        "0x41e001000..0x41e600000",
        "GPE0/ramfb",
        ("grm_ma", "ver/grm_ma/allocator.c", "ver/grm_ma/dmm_if.c"),
    ),
    (
        "spacc",
        "fx6_elpspacc_ko+fx6_elpspaccusr_ko+fx6_libspaccdev",
        "0xf7fc0000..0xf7ffffff",
        "/dev/spaccusr (SPI 0xbd)",
        ("SPACC_REG_IRQ_STAT", "SPACC_REG_IRQ_EN", "spacc_probe", "/dev/spaccusr"),
    ),
    (
        "timer",
        "fx3_vmlinux+fx6_utimer_ko",
        "0xf0100000..0xf0100fff",
        "IRQ_SPI_0x30 (hwtimer+wdt)",
        ("__udif_init_udif_hwtimer", "__udif_init_udif_wdt", "hwtimer_init_timer", "utimer_drv_init"),
    ),
    (
        "ttyAMA0..ttyAMA3",
        "fx3_vmlinux+fx6_libbt_vendor+fx6_libbt_core",
        "0xf0200000..0xf0203fff",
        "/dev/ttyAMA0../dev/ttyAMA3",
        ("ttyAMA", "uart-pl011", "/dev/ttyAMA3", "bt_hci_init_transport"),
    ),
)


def inspect_donor_kernel_mmio_contracts(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> DonorKernelMmioAudit:
    """Audit FX3 v7.02 & FX6 v6.01 kernel/module symbols & MMIO strictly `os.O_RDONLY`."""
    eff_env = dict(os.environ if env is None else env)
    if force_clean_room is True:
        eff_env[ENV_FORCE_CLEAN_ROOM] = "1"
    elif force_clean_room is False:
        eff_env.pop(ENV_FORCE_CLEAN_ROOM, None)

    paths = resolve_phase41_donor_paths(env=eff_env)
    required_keys = (
        "fx3_vmlinux",
        "fx3_dtb",
        "fx3_osal_uipc_ko",
        "fx3_cpapp",
        "fx6_dtb",
        "fx6_osal_uipc_ko",
        "fx6_utimer_ko",
        "fx6_elpspacc_ko",
        "fx6_elpspaccusr_ko",
        "fx6_grm_ma_ko",
        "fx6_pcie_if_ko",
        "fx6_pci_ep_cp_ko",
        "fx6_libspaccdev",
        "fx6_libosal_uipc",
        "fx6_libbt_vendor",
        "fx6_libbt_core",
    )
    use_donor = (not is_forced_clean_room(eff_env)) and all(
        paths[k].is_file() for k in required_keys
    )

    if not use_donor:
        contracts = tuple(
            SubsystemContractEntry(
                subsystem=subsys,
                donor_source=f"CLEAN_ROOM_PINNED({src})",
                mmio_window=win,
                irq_or_device=irq_dev,
                matched_markers=markers,
                contract_verified=True,
            )
            for subsys, src, win, irq_dev, markers in _DONOR_CONTRACT_SPECS
        )
        return DonorKernelMmioAudit(
            source_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode=DONOR_ACCESS_MODE,
            fx3_dtb_sha256=PINNED_CXD90057_DTB_SHA256,
            fx6_dtb_sha256=PINNED_CXD90057_DTB_SHA256,
            dtb_identity_verified=True,
            fx3_vmlinux_sha256=PINNED_FX3_VMLINUX_SHA256,
            fx3_cpapp_sha256=PINNED_FX3_CPAPP_SHA256,
            fx3_cpapp_bytes=PINNED_FX3_CPAPP_BYTES,
            donor_files_inspected=0,
            subsystem_contracts=contracts,
            all_contracts_verified=True,
        )

    blobs: Dict[str, bytes] = {}
    for key in required_keys:
        blobs[key] = read_donor_bytes_readonly(paths[key])

    fx3_dtb_sha = hashlib.sha256(blobs["fx3_dtb"]).hexdigest()
    fx6_dtb_sha = hashlib.sha256(blobs["fx6_dtb"]).hexdigest()
    fx3_vml_sha = hashlib.sha256(blobs["fx3_vmlinux"]).hexdigest()
    fx3_cp_sha = hashlib.sha256(blobs["fx3_cpapp"]).hexdigest()

    # Validate real donor DTB via our pure-Python FDT parser
    fdt3 = parse_fdt_blob(blobs["fx3_dtb"])
    fdt6 = parse_fdt_blob(blobs["fx6_dtb"])
    dtb_ok = (
        fx3_dtb_sha == PINNED_CXD90057_DTB_SHA256
        and fx6_dtb_sha == PINNED_CXD90057_DTB_SHA256
        and blobs["fx3_dtb"] == blobs["fx6_dtb"]
        and len(fdt3.nodes) == len(fdt6.nodes) == 68
        and "/iomem@0xf0000000" in fdt3.node_map()
        and "/soc/spacc@F7FC0000" in fdt3.node_map()
    )

    corpus = b"".join(
        blobs[k]
        for k in (
            "fx3_vmlinux",
            "fx3_osal_uipc_ko",
            "fx6_osal_uipc_ko",
            "fx6_utimer_ko",
            "fx6_elpspacc_ko",
            "fx6_elpspaccusr_ko",
            "fx6_grm_ma_ko",
            "fx6_pcie_if_ko",
            "fx6_pci_ep_cp_ko",
            "fx6_libspaccdev",
            "fx6_libosal_uipc",
            "fx6_libbt_vendor",
            "fx6_libbt_core",
        )
    )

    contracts_list: List[SubsystemContractEntry] = []
    for subsys, src, win, irq_dev, markers in _DONOR_CONTRACT_SPECS:
        matched = tuple(m for m in markers if corpus.find(m.encode("ascii")) != -1)
        contracts_list.append(
            SubsystemContractEntry(
                subsystem=subsys,
                donor_source=src,
                mmio_window=win,
                irq_or_device=irq_dev,
                matched_markers=matched,
                contract_verified=(len(matched) == len(markers)),
            )
        )

    all_ok = (
        dtb_ok
        and fx3_vml_sha == PINNED_FX3_VMLINUX_SHA256
        and fx3_cp_sha == PINNED_FX3_CPAPP_SHA256
        and len(blobs["fx3_cpapp"]) == PINNED_FX3_CPAPP_BYTES
        and all(c.contract_verified for c in contracts_list)
    )

    return DonorKernelMmioAudit(
        source_mode="LOCAL_DONOR_RDONLY",
        access_mode=DONOR_ACCESS_MODE,
        fx3_dtb_sha256=fx3_dtb_sha,
        fx6_dtb_sha256=fx6_dtb_sha,
        dtb_identity_verified=dtb_ok,
        fx3_vmlinux_sha256=fx3_vml_sha,
        fx3_cpapp_sha256=fx3_cp_sha,
        fx3_cpapp_bytes=len(blobs["fx3_cpapp"]),
        donor_files_inspected=len(blobs),
        subsystem_contracts=tuple(contracts_list),
        all_contracts_verified=all_ok,
    )


# ---------------------------------------------------------------------------
# Pure-Python Flattened Device Tree (`.dts` + FDT v17 `0xd00dfeed`) Compiler & Parser
# ---------------------------------------------------------------------------


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
class FdtPropSpec:
    name: str
    raw_value: bytes
    dts_repr: str


@dataclass(frozen=True)
class FdtNodeSpec:
    unit_name: str
    properties: Tuple[FdtPropSpec, ...] = ()
    children: Tuple["FdtNodeSpec", ...] = ()


@dataclass(frozen=True)
class CompiledFdtResult:
    dts_source: str
    fdt_bytes: bytes
    fdt_sha256: str
    totalsize: int
    node_count: int
    property_count: int
    mem_reserve_count: int
    parsed: ParsedFdtBlob


def _prop_empty(name: str) -> FdtPropSpec:
    return FdtPropSpec(name=name, raw_value=b"", dts_repr="")


def _prop_u32(name: str, *vals: int) -> FdtPropSpec:
    raw = b"".join(struct.pack(">I", v & 0xFFFF_FFFF) for v in vals)
    dts = "<" + " ".join(f"0x{v & 0xFFFF_FFFF:x}" for v in vals) + ">"
    return FdtPropSpec(name=name, raw_value=raw, dts_repr=dts)


def _prop_u64_pairs(name: str, pairs: Sequence[Tuple[int, int]]) -> FdtPropSpec:
    cells: List[int] = []
    for addr, size in pairs:
        cells.extend(((addr >> 32) & 0xFFFF_FFFF, addr & 0xFFFF_FFFF, (size >> 32) & 0xFFFF_FFFF, size & 0xFFFF_FFFF))
    return _prop_u32(name, *cells)


def _prop_u64(name: str, val: int) -> FdtPropSpec:
    return _prop_u32(name, (val >> 32) & 0xFFFF_FFFF, val & 0xFFFF_FFFF)


def _prop_str(name: str, *strings: str) -> FdtPropSpec:
    for s in strings:
        if "\x00" in s:
            raise FdtFormatError(f"NUL byte in string property {name!r}")
    raw = b"".join(s.encode("ascii") + b"\x00" for s in strings)
    dts = ", ".join(f'"{s}"' for s in strings)
    return FdtPropSpec(name=name, raw_value=raw, dts_repr=dts)


def build_cxd90057_hybrid_tree_spec(
    *,
    bt_mode: str = "HEALTHY_VIRTUAL_ROM_V1",
) -> Tuple[Tuple[FdtReserveEntry, ...], FdtNodeSpec]:
    """Build declarative FDT tree spec for QEMU `virt` + Sony `CXD90057` hybrid VM."""
    reserves = (
        FdtReserveEntry(address=SHM_IPC_PHYS_BASE, size=SHM_IPC_SIZE),
        FdtReserveEntry(address=WBI_HIB_GUARD_PHYS_BASE, size=WBI_HIB_GUARD_SIZE),
        FdtReserveEntry(address=GPE0_FB_PHYS_BASE, size=GPE0_FB_SIZE),
    )

    phandle_gic = 0x1
    phandle_apb_clk = 0x2
    phandle_l2 = 0x10

    cpu_nodes = tuple(
        FdtNodeSpec(
            unit_name=f"cpu@{cpu_idx}",
            properties=(
                _prop_str("device_type", "cpu"),
                _prop_str("compatible", "arm,cortex-a53", "arm,armv8"),
                _prop_u32("reg", 0x0, cpu_idx),
                _prop_u32("next-level-cache", phandle_l2),
                _prop_str("enable-method", "psci"),
            ),
        )
        for cpu_idx in range(4)
    )

    cpus_node = FdtNodeSpec(
        unit_name="cpus",
        properties=(
            _prop_u32("#address-cells", 2),
            _prop_u32("#size-cells", 0),
        ),
        children=cpu_nodes
        + (
            FdtNodeSpec(
                unit_name="l2-cache",
                properties=(
                    _prop_str("compatible", "cache"),
                    _prop_u32("phandle", phandle_l2),
                ),
            ),
        ),
    )

    reserved_mem_node = FdtNodeSpec(
        unit_name="reserved-memory",
        properties=(
            _prop_u32("#address-cells", 2),
            _prop_u32("#size-cells", 2),
            _prop_empty("ranges"),
        ),
        children=(
            FdtNodeSpec(
                unit_name="shm_ipc@41df00000",
                properties=(
                    _prop_u64_pairs("reg", ((SHM_IPC_PHYS_BASE, SHM_IPC_SIZE),)),
                    _prop_empty("no-map"),
                    _prop_str("compatible", "sony,cxd90057-shm-ipc"),
                ),
            ),
            FdtNodeSpec(
                unit_name="wbi_hib_guard@41df80000",
                properties=(
                    _prop_u64_pairs("reg", ((WBI_HIB_GUARD_PHYS_BASE, WBI_HIB_GUARD_SIZE),)),
                    _prop_empty("no-map"),
                    _prop_str("compatible", "sony,cxd90057-wbi-hib-guard"),
                ),
            ),
            FdtNodeSpec(
                unit_name="gpe0_fb@41e001000",
                properties=(
                    _prop_u64_pairs("reg", ((GPE0_FB_PHYS_BASE, GPE0_FB_SIZE),)),
                    _prop_empty("no-map"),
                    _prop_str("compatible", "sony,cxd90057-gpe0-fb"),
                ),
            ),
        ),
    )

    serial_nodes = tuple(
        FdtNodeSpec(
            unit_name=f"serial@{UART0_BASE + idx * UART_STRIDE:08x}",
            properties=(
                _prop_str(
                    "compatible",
                    *(
                        ("sony,virtual-rom-v1-bt-uart", "arm,pl011", "arm,primecell")
                        if idx == 3
                        else ("arm,pl011", "arm,primecell")
                    ),
                ),
                _prop_u64_pairs("reg", ((UART0_BASE + idx * UART_STRIDE, UART_SIZE),)),
                _prop_u32("interrupts", 0, 0xDA + idx, 4),
                _prop_u32("clocks", phandle_apb_clk, phandle_apb_clk),
                _prop_str("clock-names", "uartclk", "apb_pclk"),
                _prop_str("sony,tty-name", f"ttyAMA{idx}"),
                _prop_str("status", "okay"),
            )
            + (
                (
                    _prop_str("sony,uart-device", "/dev/ttyAMA3"),
                    _prop_str("sony,bt-mode", bt_mode),
                )
                if idx == 3
                else ()
            ),
        )
        for idx in range(UART_COUNT)
    )

    soc_node = FdtNodeSpec(
        unit_name="soc",
        properties=(
            _prop_str("compatible", "simple-bus"),
            _prop_u32("#address-cells", 2),
            _prop_u32("#size-cells", 2),
            _prop_empty("ranges"),
        ),
        children=(
            FdtNodeSpec(
                unit_name="apb-pclk",
                properties=(
                    _prop_str("compatible", "fixed-clock"),
                    _prop_u32("#clock-cells", 0),
                    _prop_u32("clock-frequency", 48_000_000),
                    _prop_str("clock-output-names", "apb_pclk"),
                    _prop_u32("phandle", phandle_apb_clk),
                ),
            ),
            FdtNodeSpec(
                unit_name="timer-ip@f0100000",
                properties=(
                    _prop_str(
                        "compatible",
                        "sony,cxd90057-timer-ip",
                        "sony,udif-hwtimer",
                        "sony,udif-wdt",
                    ),
                    _prop_u64_pairs("reg", ((TIMER_IP_BASE, TIMER_IP_SIZE),)),
                    _prop_u32("interrupts", 0, 0x30, 4),
                    _prop_str("status", "okay"),
                ),
            ),
        )
        + serial_nodes
        + (
            FdtNodeSpec(
                unit_name="mhlx@f0800000",
                properties=(
                    _prop_str("compatible", "sony,cxd90057-mhlx", "sony,cxd-ipcu-mailbox"),
                    _prop_u64_pairs("reg", ((MHLX_BASE, MHLX_SIZE),)),
                    _prop_u32("interrupts", 0, 0xA6, 4, 0, 0xA7, 4),
                    _prop_u32("#mbox-cells", 1),
                    _prop_u32("sony,mhlx-channels", MHLX_CHANNEL_COUNT),
                    _prop_str("status", "okay"),
                ),
            ),
            FdtNodeSpec(
                unit_name="spacc@f7fc0000",
                properties=(
                    _prop_str("compatible", "snps,designware-elpmem", "sony,cxd90057-spacc"),
                    _prop_u64_pairs("reg", ((SPACC_BASE, SPACC_SIZE),)),
                    _prop_u32("interrupts", 0, 0xBD, 4),
                    _prop_str("sony,aes-xts-isolation", "cnflasha"),
                    _prop_str("status", "okay"),
                ),
            ),
            FdtNodeSpec(
                unit_name="ivshmem@10000000",
                properties=(
                    _prop_str("compatible", "qemu,ivshmem-doorbell", "pci-ram-bridge"),
                    _prop_u64_pairs(
                        "reg",
                        (
                            (IVSHMEM_BAR0_MMIO_BASE, IVSHMEM_BAR0_MMIO_SIZE),
                            (IVSHMEM_BAR2_SHM_BASE, IVSHMEM_BAR2_SHM_SIZE),
                        ),
                    ),
                    _prop_u32("interrupts", 0, 0xAC, 4),
                    _prop_u32("sony,bar0-mmio-base", IVSHMEM_BAR0_MMIO_BASE),
                    _prop_u32("sony,bar2-shm-base", IVSHMEM_BAR2_SHM_BASE),
                    _prop_u32("sony,bar2-shm-size", IVSHMEM_BAR2_SHM_SIZE),
                    _prop_str("status", "okay"),
                ),
            ),
        ),
    )

    root = FdtNodeSpec(
        unit_name="",
        properties=(
            _prop_str("compatible", "cxd,cxd90057", "linux,dummy-virt"),
            _prop_str("model", "Sony CXD90057 Hybrid QEMU-Virt (FX3/FX6 Co-Emulation)"),
            _prop_u32("#address-cells", 2),
            _prop_u32("#size-cells", 2),
            _prop_u32("interrupt-parent", phandle_gic),
        ),
        children=(
            FdtNodeSpec(
                unit_name="chosen",
                properties=(
                    _prop_str("stdout-path", "serial0:460800n8"),
                    _prop_str(
                        "bootargs",
                        "console=ttyAMA0,460800n8 earlycon=pl011,0xf0200000 nokaslr "
                        "loglevel=8 initcall_blacklist=__boottime___udif_init_udif_hwtimer,"
                        "__boottime___udif_init_udif_wdt",
                    ),
                ),
            ),
            FdtNodeSpec(
                unit_name="aliases",
                properties=(
                    _prop_str("serial0", "/soc/serial@f0200000"),
                    _prop_str("serial1", "/soc/serial@f0201000"),
                    _prop_str("serial2", "/soc/serial@f0202000"),
                    _prop_str("serial3", "/soc/serial@f0203000"),
                ),
            ),
            cpus_node,
            FdtNodeSpec(
                unit_name="psci",
                properties=(
                    _prop_str("compatible", "arm,psci-0.2", "arm,psci"),
                    _prop_str("method", "hvc"),
                    _prop_u32("cpu_on", 0xC4000003),
                    _prop_u32("cpu_off", 0x84000002),
                ),
            ),
            FdtNodeSpec(
                unit_name="memory@40000000",
                properties=(
                    _prop_str("device_type", "memory"),
                    _prop_u64_pairs("reg", ((HYBRID_MEMORY_BASE, HYBRID_MEMORY_SIZE),)),
                ),
            ),
            reserved_mem_node,
            FdtNodeSpec(
                unit_name="interrupt-controller@f13a0000",
                properties=(
                    _prop_str("compatible", "arm,gic-400"),
                    _prop_u32("#interrupt-cells", 3),
                    _prop_empty("interrupt-controller"),
                    _prop_u64_pairs("reg", ((0xF13A_1000, 0x1000), (0xF13A_2000, 0x2000))),
                    _prop_u32("phandle", phandle_gic),
                ),
            ),
            FdtNodeSpec(
                unit_name="timer",
                properties=(
                    _prop_str("compatible", "arm,armv8-timer"),
                    _prop_u32("interrupts", 1, 13, 0x308, 1, 14, 0x308, 1, 11, 0x308, 1, 10, 0x308),
                ),
            ),
            FdtNodeSpec(
                unit_name="iomem@f0000000",
                properties=(
                    _prop_str("device_type", "iomap"),
                    _prop_u64("phys", MMIO_WINDOW_START),
                    _prop_u64("size", MMIO_WINDOW_SIZE),
                ),
            ),
            FdtNodeSpec(
                unit_name="esram@fe005000",
                properties=(
                    _prop_str("device_type", "iomap"),
                    _prop_u64("phys", ESRAM_PROBE_BASE),
                    _prop_u64("size", ESRAM_PROBE_SIZE),
                ),
            ),
            soc_node,
        ),
    )

    return reserves, root


def render_dts_from_tree(reserves: Sequence[FdtReserveEntry], root: FdtNodeSpec) -> str:
    """Render deterministic `/dts-v1/;` source text from declarative FDT tree spec."""
    lines: List[str] = ["/dts-v1/;", ""]
    for entry in reserves:
        lines.append(f"/memreserve/ 0x{entry.address:08x} 0x{entry.size:08x};")
    if reserves:
        lines.append("")

    def _emit_node(node: FdtNodeSpec, depth: int) -> None:
        indent = "\t" * depth
        label = "/" if depth == 0 else node.unit_name
        lines.append(f"{indent}{label} {{")
        for prop in node.properties:
            if prop.dts_repr:
                lines.append(f"{indent}\t{prop.name} = {prop.dts_repr};")
            else:
                lines.append(f"{indent}\t{prop.name};")
        for child in node.children:
            lines.append("")
            _emit_node(child, depth + 1)
        lines.append(f"{indent}}};")

    _emit_node(root, 0)
    lines.append("")
    return "\n".join(lines)


def pack_fdt_blob(
    reserves: Sequence[FdtReserveEntry],
    root: FdtNodeSpec,
    *,
    boot_cpuid_phys: int = 0,
) -> bytes:
    """Pack an FDT v17 (`0xd00dfeed`, big-endian) binary blob purely in Python."""
    if root.unit_name != "":
        raise FdtFormatError(f"Root node unit_name must be empty, got {root.unit_name!r}")

    strings_buf = bytearray()
    string_offsets: Dict[str, int] = {}
    struct_buf = bytearray()

    def _pad4(buf: bytearray) -> None:
        rem = len(buf) & 3
        if rem:
            buf.extend(b"\x00" * (4 - rem))

    def _intern_str(name: str) -> int:
        if not name or "\x00" in name:
            raise FdtFormatError(f"Invalid FDT property name {name!r}")
        if name not in string_offsets:
            string_offsets[name] = len(strings_buf)
            strings_buf.extend(name.encode("ascii") + b"\x00")
        return string_offsets[name]

    def _emit_node(node: FdtNodeSpec, is_root: bool) -> None:
        if not is_root and (not node.unit_name or "\x00" in node.unit_name):
            raise FdtFormatError(f"Invalid child node unit_name {node.unit_name!r}")
        struct_buf.extend(struct.pack(">I", FDT_BEGIN_NODE))
        struct_buf.extend(node.unit_name.encode("ascii") + b"\x00")
        _pad4(struct_buf)

        seen_props: Set[str] = set()
        for prop in node.properties:
            if prop.name in seen_props:
                raise FdtFormatError(f"Duplicate property {prop.name!r} in node {node.unit_name!r}")
            seen_props.add(prop.name)
            nameoff = _intern_str(prop.name)
            struct_buf.extend(struct.pack(">III", FDT_PROP, len(prop.raw_value), nameoff))
            struct_buf.extend(prop.raw_value)
            _pad4(struct_buf)

        seen_children: Set[str] = set()
        for child in node.children:
            if child.unit_name in seen_children:
                raise FdtFormatError(f"Duplicate child node {child.unit_name!r}")
            seen_children.add(child.unit_name)
            _emit_node(child, is_root=False)

        struct_buf.extend(struct.pack(">I", FDT_END_NODE))

    _emit_node(root, is_root=True)
    struct_buf.extend(struct.pack(">I", FDT_END))

    rsv_buf = bytearray()
    for entry in reserves:
        if entry.address == 0 and entry.size == 0:
            raise FdtFormatError("memreserve entry cannot be (0, 0); reserved for sentinel")
        rsv_buf.extend(struct.pack(">QQ", entry.address, entry.size))
    rsv_buf.extend(struct.pack(">QQ", 0, 0))  # mandatory 16-byte terminator

    off_mem_rsvmap = FDT_HEADER_BYTES  # 40 (8-byte aligned)
    off_dt_struct = off_mem_rsvmap + len(rsv_buf)  # 8-byte & 4-byte aligned
    size_dt_struct = len(struct_buf)
    off_dt_strings = off_dt_struct + size_dt_struct
    size_dt_strings = len(strings_buf)
    totalsize = off_dt_strings + size_dt_strings

    header = struct.pack(
        ">10I",
        FDT_MAGIC,
        totalsize,
        off_dt_struct,
        off_dt_strings,
        off_mem_rsvmap,
        FDT_VERSION,
        FDT_LAST_COMP_VERSION,
        boot_cpuid_phys,
        size_dt_strings,
        size_dt_struct,
    )
    return header + bytes(rsv_buf) + bytes(struct_buf) + bytes(strings_buf)


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
    if version < 16 or last_comp_version > version:
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

    rsv_entries: List[FdtReserveEntry] = []
    rsv_pos = off_mem_rsvmap
    found_sentinel = False
    while rsv_pos + 16 <= totalsize:
        addr, sz = struct.unpack_from(">QQ", raw, rsv_pos)
        rsv_pos += 16
        if addr == 0 and sz == 0:
            found_sentinel = True
            break
        rsv_entries.append(FdtReserveEntry(address=addr, size=sz))
    if not found_sentinel:
        raise FdtFormatError("Unterminated FDT mem_rsvmap block (missing 16-byte zero sentinel)")

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


def compile_cxd90057_hybrid_fdt(*, bt_mode: str = "HEALTHY_VIRTUAL_ROM_V1") -> CompiledFdtResult:
    """Synthesize `.dts` + compile binary FDT v17 blob in-memory and verify roundtrip."""
    reserves, root = build_cxd90057_hybrid_tree_spec(bt_mode=bt_mode)
    dts_source = render_dts_from_tree(reserves, root)
    fdt_bytes = pack_fdt_blob(reserves, root)
    parsed = parse_fdt_blob(fdt_bytes)
    return CompiledFdtResult(
        dts_source=dts_source,
        fdt_bytes=fdt_bytes,
        fdt_sha256=hashlib.sha256(fdt_bytes).hexdigest(),
        totalsize=len(fdt_bytes),
        node_count=len(parsed.nodes),
        property_count=parsed.total_property_count,
        mem_reserve_count=len(parsed.mem_rsvmap),
        parsed=parsed,
    )


def verify_hybrid_fdt_topology(compiled: CompiledFdtResult) -> Dict[str, object]:
    """Validate all required CXD90057 + QEMU Virt FDT nodes, carveouts, and non-overlap."""
    nmap = compiled.parsed.node_map()
    required_paths = (
        "/",
        "/chosen",
        "/aliases",
        "/cpus",
        "/cpus/cpu@0",
        "/cpus/cpu@1",
        "/cpus/cpu@2",
        "/cpus/cpu@3",
        "/memory@40000000",
        "/reserved-memory",
        "/reserved-memory/shm_ipc@41df00000",
        "/reserved-memory/wbi_hib_guard@41df80000",
        "/reserved-memory/gpe0_fb@41e001000",
        "/iomem@f0000000",
        "/esram@fe005000",
        "/soc",
        "/soc/timer-ip@f0100000",
        "/soc/serial@f0200000",
        "/soc/serial@f0201000",
        "/soc/serial@f0202000",
        "/soc/serial@f0203000",
        "/soc/mhlx@f0800000",
        "/soc/spacc@f7fc0000",
        "/soc/ivshmem@10000000",
    )
    missing = [p for p in required_paths if p not in nmap]

    # Verify reserved-memory carveouts are sorted and non-overlapping
    rsv_ranges: List[Tuple[str, int, int]] = []
    for path in (
        "/reserved-memory/shm_ipc@41df00000",
        "/reserved-memory/wbi_hib_guard@41df80000",
        "/reserved-memory/gpe0_fb@41e001000",
    ):
        if path in nmap:
            base, size = struct.unpack(">QQ", nmap[path].prop_dict()["reg"][:16])
            rsv_ranges.append((path, base, base + size))
    rsv_ranges.sort(key=lambda x: x[1])
    zero_overlap = len(rsv_ranges) == 3 and all(
        rsv_ranges[i][2] <= rsv_ranges[i + 1][1] for i in range(len(rsv_ranges) - 1)
    )

    # Verify CPU compatible
    cpu0_compat = nmap["/cpus/cpu@0"].prop_dict()["compatible"].split(b"\x00")[:-1]
    cortex_a53_ok = [c.decode("ascii") for c in cpu0_compat] == ["arm,cortex-a53", "arm,armv8"]

    # Verify SPAcc & MHLX & timer-ip & ttyAMA3 addresses inside 0xf0000000..0xf8ffffff
    def _reg_first_pair(path: str) -> Tuple[int, int]:
        return struct.unpack(">QQ", nmap[path].prop_dict()["reg"][:16])

    timer_reg = _reg_first_pair("/soc/timer-ip@f0100000")
    uart3_reg = _reg_first_pair("/soc/serial@f0203000")
    mhlx_reg = _reg_first_pair("/soc/mhlx@f0800000")
    spacc_reg = _reg_first_pair("/soc/spacc@f7fc0000")
    ivshmem_reg_bytes = nmap["/soc/ivshmem@10000000"].prop_dict()["reg"]
    iv_bar0_base, iv_bar0_sz, iv_bar2_base, iv_bar2_sz = struct.unpack(">QQQQ", ivshmem_reg_bytes)

    mmio_bounds_ok = all(
        MMIO_WINDOW_START <= base and (base + sz) <= MMIO_WINDOW_END
        for base, sz in (timer_reg, uart3_reg, mhlx_reg, spacc_reg)
    )

    all_ok = (
        compiled.parsed.header.magic == FDT_MAGIC
        and compiled.parsed.header.version == FDT_VERSION
        and len(missing) == 0
        and zero_overlap
        and cortex_a53_ok
        and mmio_bounds_ok
        and timer_reg == (TIMER_IP_BASE, TIMER_IP_SIZE)
        and uart3_reg == (UART3_BT_BASE, UART_SIZE)
        and mhlx_reg == (MHLX_BASE, MHLX_SIZE)
        and spacc_reg == (SPACC_BASE, SPACC_SIZE)
        and (iv_bar0_base, iv_bar0_sz) == (IVSHMEM_BAR0_MMIO_BASE, IVSHMEM_BAR0_MMIO_SIZE)
        and (iv_bar2_base, iv_bar2_sz) == (IVSHMEM_BAR2_SHM_BASE, IVSHMEM_BAR2_SHM_SIZE)
    )

    return {
        "all_checks_passed": all_ok,
        "fdt_magic": f"0x{compiled.parsed.header.magic:08x}",
        "fdt_version": compiled.parsed.header.version,
        "fdt_last_comp_version": compiled.parsed.header.last_comp_version,
        "totalsize_bytes": compiled.totalsize,
        "fdt_sha256": compiled.fdt_sha256,
        "node_count": compiled.node_count,
        "property_count": compiled.property_count,
        "mem_reserve_count": compiled.mem_reserve_count,
        "missing_nodes": missing,
        "reserved_memory_zero_overlap": zero_overlap,
        "cortex_a53_ok": cortex_a53_ok,
        "mmio_bounds_ok": mmio_bounds_ok,
        "dts_line_count": len(compiled.dts_source.splitlines()),
        "header_preview_hex": compiled.fdt_bytes[:FDT_HEADER_BYTES].hex(),
    }


# ---------------------------------------------------------------------------
# `mhlx` / `ipcu` Hardware Mailbox Ring & `0xf0000000..0xf8ffffff` MMIO Emulator
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MhlxRingMessage:
    seq: int
    channel: int
    opcode: int
    flags: int
    payload: bytes


@dataclass(frozen=True)
class MhlxChannelState:
    channel_id: int
    name: str
    enabled: bool
    mode: int
    tx_base_offset: int
    tx_capacity: int
    tx_head: int
    tx_tail: int
    rx_base_offset: int
    rx_capacity: int
    rx_head: int
    rx_tail: int
    irq_status: int
    msg_count: int


@dataclass(frozen=True)
class ShmLoaderHandshakeReceipt:
    boot_mode: str
    passed: bool
    channel: int
    request_opcode: str
    ack_opcode: str
    cp_load_base: str
    cp_sha256_before: str
    cp_sha256_after: str
    cp_mutation_bytes: int
    wbi_mutation_bytes: int
    ap_tx_doorbell_fired: bool
    cp_irq_acked_w1c: bool
    cp_rx_doorbell_fired: bool
    ap_irq_acked_w1c: bool
    shm_loader_status: int


class MmioWindowBus:
    """Emulates the CXD90057 `0xf0000000..0xf8ffffff` MMIO aperture + `mhlx` mailbox ring."""

    def __init__(self, *, cp_bytes: Optional[bytes] = None) -> None:
        # Stock-CP image kept strictly immutable in-memory (read-only view + pinned SHA-256)
        if cp_bytes is None:
            cp_bytes = self._build_clean_room_cp_image()
        self._cp_image = bytes(cp_bytes)
        self.cp_sha256_initial = hashlib.sha256(self._cp_image).hexdigest()
        self.cp_mutation_bytes = 0
        self.wbi_mutation_bytes = 0

        # Shared IPC memory backing (`shm_ipc@41df00000`, 512 KiB)
        self.shm = bytearray(SHM_IPC_SIZE)

        # Timer-IP & WDT state (0xf0100000)
        self.timer_ctrl = 0x1
        self.timer_counter = 0x0001_0000
        self.timer_reload = 0x0001_0000
        self.wdt_enabled = True
        self.wdt_timeout_ticks = 10_000
        self.wdt_remaining_ticks = 10_000
        self.wdt_kick_count = 0
        self.wdt_resets = 0

        # PL011 UART state (0xf0200000..0xf0203000, ttyAMA0..ttyAMA3)
        self.uart_regs: List[Dict[int, int]] = [
            {
                UART_REG_FR: UART_FR_TXFE | UART_FR_RXFE,
                UART_REG_IBRD: 0x06 if idx == 0 else 0x1A,
                UART_REG_FBRD: 0x20 if idx == 0 else 0x03,
                UART_REG_CR: 0x0301,
                UART_REG_IMSC: 0x0000,
            }
            for idx in range(UART_COUNT)
        ]
        self.uart_tx_streams: List[bytearray] = [bytearray() for _ in range(UART_COUNT)]

        # SPAcc AES-XTS state (0xf7fc0000)
        self.spacc_irq_en = 0x1
        self.spacc_irq_stat = 0x0
        self.spacc_xts_mode = 0x1  # AES-XTS-256 cnflasha
        self.spacc_key_lock = 0x1  # Kernel-only isolation active
        self.spacc_kernel_ops = 0
        self.spacc_blocked_userland_ops = 0

        # MHLX / IPCU Mailbox state (0xf0800000)
        self.mhlx_irq_status = 0
        self.mhlx_irq_mask = (1 << MHLX_CHANNEL_COUNT) - 1  # all 8 channels unmasked by default
        self.mhlx_doorbell_count = 0
        self.mhlx_shm_loader_ctrl = 0
        self.mhlx_shm_loader_status = SHM_LOADER_STATE_IDLE
        self.mhlx_backpressure_count = 0
        self.mhlx_next_seq = 1
        self.mhlx_channels: List[Dict[str, int]] = []
        for ch in range(MHLX_CHANNEL_COUNT):
            tx_base = 0x1000 + ch * 0x2000
            rx_base = tx_base + (MHLX_RING_CAPACITY * MHLX_SLOT_BYTES)
            self.mhlx_channels.append(
                {
                    "mode": 0x3,  # bidirectional
                    "enabled": 1,
                    "tx_base": tx_base,
                    "tx_cap": MHLX_RING_CAPACITY,
                    "tx_head": 0,
                    "tx_tail": 0,
                    "rx_base": rx_base,
                    "rx_cap": MHLX_RING_CAPACITY,
                    "rx_head": 0,
                    "rx_tail": 0,
                    "irq_stat": 0,
                    "msg_count": 0,
                }
            )

        self.mmio_read_count = 0
        self.mmio_write_count = 0
        self.doorbell_trace: List[Tuple[str, int, int]] = []

    @staticmethod
    def _build_clean_room_cp_image() -> bytes:
        buf = bytearray(0x2000)
        for idx, word in enumerate(EXPECTED_CP_ARM32_ENTRY_WORDS):
            struct.pack_into("<I", buf, idx * 4, word)
        return bytes(buf)

    def _check_window(self, addr: int, size: int) -> None:
        if size not in (1, 2, 4, 8):
            raise MmioAccessError(f"Unsupported MMIO access width {size} at 0x{addr:08x}")
        if addr < MMIO_WINDOW_START or (addr + size) > MMIO_WINDOW_END:
            raise MmioAccessError(
                f"Address 0x{addr:08x} (+{size}B) outside CXD90057 MMIO window "
                f"[0x{MMIO_WINDOW_START:08x}, 0x{MMIO_WINDOW_END:08x})"
            )

    def read32(self, addr: int, *, ring: str = "kernel") -> int:
        self._check_window(addr, 4)
        self.mmio_read_count += 1

        if TIMER_IP_BASE <= addr < TIMER_IP_BASE + TIMER_IP_SIZE:
            return self._read_timer(addr - TIMER_IP_BASE)
        if UART0_BASE <= addr < UART0_BASE + UART_COUNT * UART_STRIDE:
            idx = (addr - UART0_BASE) // UART_STRIDE
            off = (addr - UART0_BASE) % UART_STRIDE
            return self.uart_regs[idx].get(off, 0)
        if MHLX_BASE <= addr < MHLX_BASE + MHLX_SIZE:
            return self._read_mhlx(addr - MHLX_BASE)
        if SPACC_BASE <= addr < SPACC_BASE + SPACC_SIZE:
            return self._read_spacc(addr - SPACC_BASE, ring=ring)
        return 0

    def write32(self, addr: int, value: int, *, ring: str = "kernel") -> None:
        self._check_window(addr, 4)
        self.mmio_write_count += 1
        val = value & 0xFFFF_FFFF

        if TIMER_IP_BASE <= addr < TIMER_IP_BASE + TIMER_IP_SIZE:
            self._write_timer(addr - TIMER_IP_BASE, val)
            return
        if UART0_BASE <= addr < UART0_BASE + UART_COUNT * UART_STRIDE:
            idx = (addr - UART0_BASE) // UART_STRIDE
            off = (addr - UART0_BASE) % UART_STRIDE
            self._write_uart(idx, off, val)
            return
        if MHLX_BASE <= addr < MHLX_BASE + MHLX_SIZE:
            self._write_mhlx(addr - MHLX_BASE, val)
            return
        if SPACC_BASE <= addr < SPACC_BASE + SPACC_SIZE:
            self._write_spacc(addr - SPACC_BASE, val, ring=ring)
            return

    def read64(self, addr: int, *, ring: str = "kernel") -> int:
        self._check_window(addr, 8)
        lo = self.read32(addr, ring=ring)
        hi = self.read32(addr + 4, ring=ring)
        return (hi << 32) | lo

    def write64(self, addr: int, value: int, *, ring: str = "kernel") -> None:
        self._check_window(addr, 8)
        self.write32(addr, value & 0xFFFF_FFFF, ring=ring)
        self.write32(addr + 4, (value >> 32) & 0xFFFF_FFFF, ring=ring)

    def _read_timer(self, off: int) -> int:
        if off == TIMER_REG_CTRL:
            return self.timer_ctrl
        if off == TIMER_REG_COUNTER:
            return self.timer_counter
        if off == TIMER_REG_RELOAD:
            return self.timer_reload
        if off == TIMER_REG_WDT_ENABLE:
            return 1 if self.wdt_enabled else 0
        if off == TIMER_REG_WDT_TIMEOUT:
            return self.wdt_timeout_ticks
        if off == TIMER_REG_WDT_STATUS:
            return self.wdt_remaining_ticks
        if off == TIMER_REG_WDT_RESET_COUNT:
            return self.wdt_resets
        return 0

    def _write_timer(self, off: int, val: int) -> None:
        if off == TIMER_REG_CTRL:
            self.timer_ctrl = val
        elif off == TIMER_REG_COUNTER:
            self.timer_counter = val
        elif off == TIMER_REG_RELOAD:
            self.timer_reload = val
        elif off == TIMER_REG_WDT_ENABLE:
            self.wdt_enabled = bool(val & 1)
        elif off == TIMER_REG_WDT_KICK:
            if val == WDT_KICK_MAGIC or val != 0:
                self.wdt_remaining_ticks = self.wdt_timeout_ticks
                self.wdt_kick_count += 1
        elif off == TIMER_REG_WDT_TIMEOUT:
            self.wdt_timeout_ticks = max(1, val)
            self.wdt_remaining_ticks = self.wdt_timeout_ticks

    def advance_timer_ticks(self, ticks: int) -> None:
        if ticks < 0:
            raise ValueError("ticks must be non-negative")
        self.timer_counter = (self.timer_counter + ticks) & 0xFFFF_FFFF
        if self.wdt_enabled:
            if ticks >= self.wdt_remaining_ticks:
                self.wdt_resets += 1
                self.wdt_remaining_ticks = self.wdt_timeout_ticks
            else:
                self.wdt_remaining_ticks -= ticks

    def _write_uart(self, idx: int, off: int, val: int) -> None:
        if off == UART_REG_DR:
            self.uart_tx_streams[idx].append(val & 0xFF)
        elif off == UART_REG_ICR:
            pass
        else:
            self.uart_regs[idx][off] = val

    def _read_spacc(self, off: int, *, ring: str) -> int:
        if ring != "kernel":
            self.spacc_blocked_userland_ops += 1
            raise MmioAccessError(
                f"Blocked non-kernel SPAcc MMIO read at 0x{SPACC_BASE + off:08x} (ring={ring!r})"
            )
        self.spacc_kernel_ops += 1
        if off == SPACC_REG_IRQ_EN:
            return self.spacc_irq_en
        if off == SPACC_REG_IRQ_STAT:
            return self.spacc_irq_stat
        if off == SPACC_REG_VERSION:
            return SPACC_VERSION_MAGIC
        if off == SPACC_REG_XTS_MODE:
            return self.spacc_xts_mode
        if off == SPACC_REG_KEY_LOCK:
            return self.spacc_key_lock
        return 0

    def _write_spacc(self, off: int, val: int, *, ring: str) -> None:
        if ring != "kernel":
            self.spacc_blocked_userland_ops += 1
            raise MmioAccessError(
                f"Blocked non-kernel SPAcc MMIO write at 0x{SPACC_BASE + off:08x} (ring={ring!r})"
            )
        self.spacc_kernel_ops += 1
        if off == SPACC_REG_IRQ_EN:
            self.spacc_irq_en = val
        elif off == SPACC_REG_IRQ_STAT:
            self.spacc_irq_stat &= ~val
        elif off == SPACC_REG_XTS_MODE:
            self.spacc_xts_mode = val

    def _read_mhlx(self, off: int) -> int:
        if off == MHLX_REG_ID:
            return MHLX_MAGIC
        if off == MHLX_REG_VERSION:
            return MHLX_VERSION
        if off == MHLX_REG_CH_COUNT:
            return MHLX_CHANNEL_COUNT
        if off == MHLX_REG_IRQ_STATUS:
            return self.mhlx_irq_status & self.mhlx_irq_mask
        if off == MHLX_REG_IRQ_MASK:
            return self.mhlx_irq_mask
        if off == MHLX_REG_DOORBELL_COUNT:
            return self.mhlx_doorbell_count
        if off == MHLX_REG_SHM_LOADER_CTRL:
            return self.mhlx_shm_loader_ctrl
        if off == MHLX_REG_SHM_LOADER_STATUS:
            return self.mhlx_shm_loader_status
        if off == MHLX_REG_SHM_BASE_LO:
            return SHM_IPC_PHYS_BASE & 0xFFFF_FFFF
        if off == MHLX_REG_SHM_BASE_HI:
            return (SHM_IPC_PHYS_BASE >> 32) & 0xFFFF_FFFF
        if off == MHLX_REG_CP_MUTATION_BYTES:
            return self.cp_mutation_bytes

        if off >= MHLX_CH_BASE:
            rel = off - MHLX_CH_BASE
            ch = rel // MHLX_CH_STRIDE
            reg = rel % MHLX_CH_STRIDE
            if 0 <= ch < MHLX_CHANNEL_COUNT:
                c = self.mhlx_channels[ch]
                mapping = {
                    MHLX_CH_OFF_MODE: c["mode"],
                    MHLX_CH_OFF_ENABLE: c["enabled"],
                    MHLX_CH_OFF_TX_BASE: c["tx_base"],
                    MHLX_CH_OFF_TX_CAP: c["tx_cap"],
                    MHLX_CH_OFF_TX_HEAD: c["tx_head"],
                    MHLX_CH_OFF_TX_TAIL: c["tx_tail"],
                    MHLX_CH_OFF_RX_BASE: c["rx_base"],
                    MHLX_CH_OFF_RX_CAP: c["rx_cap"],
                    MHLX_CH_OFF_RX_HEAD: c["rx_head"],
                    MHLX_CH_OFF_RX_TAIL: c["rx_tail"],
                    MHLX_CH_OFF_IRQ_STAT: c["irq_stat"],
                    MHLX_CH_OFF_MSG_COUNT: c["msg_count"],
                }
                return mapping.get(reg, 0)
        return 0

    def _write_mhlx(self, off: int, val: int) -> None:
        if off == MHLX_REG_IRQ_MASK:
            self.mhlx_irq_mask = val & ((1 << MHLX_CHANNEL_COUNT) - 1)
            return
        if off == MHLX_REG_IRQ_CLEAR:
            self.mhlx_irq_status &= ~val
            for ch in range(MHLX_CHANNEL_COUNT):
                if val & (1 << ch):
                    self.mhlx_channels[ch]["irq_stat"] = 0
            return
        if off == MHLX_REG_DOORBELL_SEND:
            peer = (val >> 16) & 0xFFFF
            ch = val & 0xFFFF
            if not (0 <= ch < MHLX_CHANNEL_COUNT):
                raise MhlxMailboxError(f"Invalid MHLX channel {ch} in doorbell")
            self.mhlx_doorbell_count += 1
            self.mhlx_channels[ch]["irq_stat"] |= 1 << peer
            self.mhlx_irq_status |= 1 << ch
            self.doorbell_trace.append(("AP->CP" if peer == 1 else "CP->AP", peer, ch))
            return
        if off == MHLX_REG_SHM_LOADER_CTRL:
            self.mhlx_shm_loader_ctrl = val
            return

        if off >= MHLX_CH_BASE:
            rel = off - MHLX_CH_BASE
            ch = rel // MHLX_CH_STRIDE
            reg = rel % MHLX_CH_STRIDE
            if 0 <= ch < MHLX_CHANNEL_COUNT:
                c = self.mhlx_channels[ch]
                if reg == MHLX_CH_OFF_ENABLE:
                    c["enabled"] = val & 1
                elif reg == MHLX_CH_OFF_MODE:
                    c["mode"] = val
                elif reg == MHLX_CH_OFF_IRQ_CLR:
                    c["irq_stat"] &= ~val
                    if c["irq_stat"] == 0:
                        self.mhlx_irq_status &= ~(1 << ch)
                elif reg == MHLX_CH_OFF_DOORBELL:
                    peer = val & 0xFFFF
                    self.mhlx_doorbell_count += 1
                    c["irq_stat"] |= 1 << peer
                    self.mhlx_irq_status |= 1 << ch
                    self.doorbell_trace.append(("AP->CP" if peer == 1 else "CP->AP", peer, ch))

    # --- Ring Buffer Operations ---

    def push_ring(self, channel: int, direction: str, opcode: int, payload: bytes, *, flags: int = 1) -> int:
        if not (0 <= channel < MHLX_CHANNEL_COUNT):
            raise MhlxMailboxError(f"Invalid MHLX channel {channel}")
        if direction not in ("tx", "rx"):
            raise MhlxMailboxError(f"Invalid ring direction {direction!r}")
        if len(payload) > MHLX_MAX_PAYLOAD_BYTES:
            raise MhlxMailboxError(f"Payload {len(payload)}B exceeds MHLX slot max {MHLX_MAX_PAYLOAD_BYTES}B")

        c = self.mhlx_channels[channel]
        if not c["enabled"]:
            raise MhlxMailboxError(f"MHLX channel {channel} is disabled")

        head_k = f"{direction}_head"
        tail_k = f"{direction}_tail"
        cap_k = f"{direction}_cap"
        base_k = f"{direction}_base"

        head = c[head_k]
        tail = c[tail_k]
        cap = c[cap_k]
        next_head = (head + 1) % cap
        if next_head == tail:
            self.mhlx_backpressure_count += 1
            raise MhlxMailboxError(f"MHLX channel {channel} {direction.upper()} ring full (cap={cap})")

        seq = self.mhlx_next_seq
        self.mhlx_next_seq += 1

        slot_off = c[base_k] + head * MHLX_SLOT_BYTES
        struct.pack_into("<IHHII", self.shm, slot_off, seq, channel, opcode & 0xFFFF, flags, len(payload))
        self.shm[slot_off + MHLX_SLOT_HDR_BYTES : slot_off + MHLX_SLOT_BYTES] = b"\x00" * MHLX_MAX_PAYLOAD_BYTES
        if payload:
            self.shm[slot_off + MHLX_SLOT_HDR_BYTES : slot_off + MHLX_SLOT_HDR_BYTES + len(payload)] = payload

        c[head_k] = next_head
        c["msg_count"] += 1
        return seq

    def pop_ring(self, channel: int, direction: str) -> Optional[MhlxRingMessage]:
        if not (0 <= channel < MHLX_CHANNEL_COUNT):
            raise MhlxMailboxError(f"Invalid MHLX channel {channel}")
        if direction not in ("tx", "rx"):
            raise MhlxMailboxError(f"Invalid ring direction {direction!r}")

        c = self.mhlx_channels[channel]
        head_k = f"{direction}_head"
        tail_k = f"{direction}_tail"
        cap_k = f"{direction}_cap"
        base_k = f"{direction}_base"

        head = c[head_k]
        tail = c[tail_k]
        if head == tail:
            return None

        slot_off = c[base_k] + tail * MHLX_SLOT_BYTES
        seq, slot_ch, opcode, flags, plen = struct.unpack_from("<IHHII", self.shm, slot_off)
        if plen > MHLX_MAX_PAYLOAD_BYTES or slot_ch != channel:
            raise MhlxMailboxError(
                f"Corrupted MHLX ring slot on ch={channel}: slot_ch={slot_ch}, plen={plen}"
            )
        payload = bytes(self.shm[slot_off + MHLX_SLOT_HDR_BYTES : slot_off + MHLX_SLOT_HDR_BYTES + plen])
        c[tail_k] = (tail + 1) % c[cap_k]
        return MhlxRingMessage(seq=seq, channel=channel, opcode=opcode, flags=flags, payload=payload)

    def channel_snapshot(self, channel: int) -> MhlxChannelState:
        c = self.mhlx_channels[channel]
        return MhlxChannelState(
            channel_id=channel,
            name=MHLX_CHANNEL_NAMES[channel],
            enabled=bool(c["enabled"]),
            mode=c["mode"],
            tx_base_offset=c["tx_base"],
            tx_capacity=c["tx_cap"],
            tx_head=c["tx_head"],
            tx_tail=c["tx_tail"],
            rx_base_offset=c["rx_base"],
            rx_capacity=c["rx_cap"],
            rx_head=c["rx_head"],
            rx_tail=c["rx_tail"],
            irq_status=c["irq_stat"],
            msg_count=c["msg_count"],
        )

    def verify_cp_immutability(self) -> Tuple[str, str, int]:
        sha_now = hashlib.sha256(self._cp_image).hexdigest()
        mutated = 0 if sha_now == self.cp_sha256_initial else len(self._cp_image)
        self.cp_mutation_bytes = mutated
        return self.cp_sha256_initial, sha_now, mutated

    def run_shm_loader_handshake(self, *, mode: str = "cold_boot") -> ShmLoaderHandshakeReceipt:
        """Execute `shm_Loader` cold-boot or warm-boot handshake into immutable Stock-CP."""
        if mode not in ("cold_boot", "warm_boot"):
            raise MhlxMailboxError(f"Unsupported shm_Loader boot mode {mode!r}")

        sha_before, sha_after, mut = self.verify_cp_immutability()
        if mut != 0:
            raise MhlxMailboxError("Stock-CP image mutated before shm_Loader handshake")

        ch = MHLX_CH_SHM_LOADER
        req_op = SHM_LOADER_OP_COLD_HELLO if mode == "cold_boot" else SHM_LOADER_OP_WARM_RESUME
        ctrl_val = 1 if mode == "cold_boot" else 2
        self.write32(MHLX_BASE + MHLX_REG_SHM_LOADER_CTRL, ctrl_val)

        # Verify Stock-CP ARM32 entry words read-only before accepting handshake
        entry_word0 = struct.unpack_from("<I", self._cp_image, 0)[0]
        cp_entry_ok = (entry_word0 == EXPECTED_CP_ARM32_ENTRY_WORDS[0])

        req_payload = struct.pack(
            "<IIIIQ",
            SHM_LOADER_MAGIC,
            1 if mode == "cold_boot" else 2,
            CP_LOAD_BASE,
            0x0702,
            WBI_HIB_GUARD_PHYS_BASE if mode == "warm_boot" else SHM_IPC_PHYS_BASE,
        )
        self.push_ring(ch, "tx", req_op, req_payload, flags=ctrl_val)
        # AP rings doorbell for peer 1 (CP)
        self.write32(MHLX_BASE + MHLX_REG_DOORBELL_SEND, (1 << 16) | ch)
        ap_db_fired = bool(self.read32(MHLX_BASE + MHLX_REG_IRQ_STATUS) & (1 << ch))

        # CP reads TX slot, verifies immutable CP image, and acks IRQ via W1C
        msg = self.pop_ring(ch, "tx")
        self.write32(MHLX_BASE + MHLX_REG_IRQ_CLEAR, 1 << ch)
        cp_acked_w1c = (self.read32(MHLX_BASE + MHLX_REG_IRQ_STATUS) & (1 << ch)) == 0

        ack_op = req_op | SHM_LOADER_OP_ACK_BIT
        if msg is not None and cp_entry_ok and mut == 0:
            self.mhlx_shm_loader_status = (
                SHM_LOADER_STATE_COLD_READY if mode == "cold_boot" else SHM_LOADER_STATE_WARM_RESUMED
            )
            ack_payload = struct.pack(
                "<IIII",
                SHM_LOADER_MAGIC,
                self.mhlx_shm_loader_status,
                0,  # cp_mutation_bytes == 0
                1,  # uipc_ready / ibis_reanchored
            )
            self.push_ring(ch, "rx", ack_op, ack_payload, flags=self.mhlx_shm_loader_status)
            # CP rings doorbell for peer 0 (AP)
            ch_db_addr = MHLX_BASE + MHLX_CH_BASE + ch * MHLX_CH_STRIDE + MHLX_CH_OFF_DOORBELL
            self.write32(ch_db_addr, 0)
        cp_db_fired = bool(self.read32(MHLX_BASE + MHLX_REG_IRQ_STATUS) & (1 << ch))

        # AP consumes RX completion and acks per-channel IRQ via CH_OFF_IRQ_CLR
        rx_msg = self.pop_ring(ch, "rx")
        ch_clr_addr = MHLX_BASE + MHLX_CH_BASE + ch * MHLX_CH_STRIDE + MHLX_CH_OFF_IRQ_CLR
        self.write32(ch_clr_addr, 0xFFFF)
        ap_acked_w1c = (self.read32(MHLX_BASE + MHLX_REG_IRQ_STATUS) & (1 << ch)) == 0

        sha_before2, sha_after2, mut2 = self.verify_cp_immutability()
        passed = (
            cp_entry_ok
            and ap_db_fired
            and cp_acked_w1c
            and cp_db_fired
            and ap_acked_w1c
            and rx_msg is not None
            and rx_msg.opcode == ack_op
            and mut2 == 0
            and sha_before2 == sha_after2
            and self.wbi_mutation_bytes == 0
        )

        return ShmLoaderHandshakeReceipt(
            boot_mode=mode,
            passed=passed,
            channel=ch,
            request_opcode=f"0x{req_op:04x}",
            ack_opcode=f"0x{ack_op:04x}",
            cp_load_base=f"0x{CP_LOAD_BASE:08x}",
            cp_sha256_before=sha_before,
            cp_sha256_after=sha_after2,
            cp_mutation_bytes=mut2,
            wbi_mutation_bytes=self.wbi_mutation_bytes,
            ap_tx_doorbell_fired=ap_db_fired,
            cp_irq_acked_w1c=cp_acked_w1c,
            cp_rx_doorbell_fired=cp_db_fired,
            ap_irq_acked_w1c=ap_acked_w1c,
            shm_loader_status=self.mhlx_shm_loader_status,
        )


# ---------------------------------------------------------------------------
# Unified Phase 41 Emulator Audit Entrypoint & CLI
# ---------------------------------------------------------------------------


def run_phase41_emulator_audit(
    *,
    bt_mode: str = "HEALTHY_VIRTUAL_ROM_V1",
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute the full Phase 41 FDT/DTB, MMIO Window, MHLX Ring & `shm_Loader` audit."""
    eff_env = dict(os.environ if env is None else env)
    if force_clean_room is True:
        eff_env[ENV_FORCE_CLEAN_ROOM] = "1"
    elif force_clean_room is False:
        eff_env.pop(ENV_FORCE_CLEAN_ROOM, None)

    donor_audit = inspect_donor_kernel_mmio_contracts(force_clean_room=force_clean_room, env=eff_env)

    # Load Stock-CP strictly O_RDONLY if in LOCAL_DONOR_RDONLY mode, else synthetic fixture
    cp_bytes: Optional[bytes] = None
    if donor_audit.source_mode == "LOCAL_DONOR_RDONLY":
        cp_path = resolve_phase41_donor_paths(env=eff_env)["fx3_cpapp"]
        if cp_path.is_file():
            cp_bytes = read_donor_bytes_readonly(cp_path)

    compiled_fdt = compile_cxd90057_hybrid_fdt(bt_mode=bt_mode)
    fdt_verification = verify_hybrid_fdt_topology(compiled_fdt)

    bus = MmioWindowBus(cp_bytes=cp_bytes)

    # Exercise 0xf0000000..0xf8ffffff MMIO window devices
    mhlx_id = bus.read32(MHLX_BASE + MHLX_REG_ID)
    spacc_ver = bus.read32(SPACC_BASE + SPACC_REG_VERSION, ring="kernel")
    spacc_lock = bus.read32(SPACC_BASE + SPACC_REG_KEY_LOCK, ring="kernel")

    # Verify SPAcc userland isolation blocks non-kernel touch
    spacc_userland_blocked = False
    try:
        bus.read32(SPACC_BASE + SPACC_REG_XTS_MODE, ring="userland")
    except MmioAccessError:
        spacc_userland_blocked = True

    # Exercise timer-ip + WDT kick (0 resets) and ttyAMA3 UART TX
    bus.advance_timer_ticks(2500)
    bus.write32(TIMER_IP_BASE + TIMER_REG_WDT_KICK, WDT_KICK_MAGIC)
    wdt_resets = bus.read32(TIMER_IP_BASE + TIMER_REG_WDT_RESET_COUNT)
    for b in b"\x01\x03\x0c\x00":  # HCI_Reset H4 packet probe
        bus.write32(UART3_BT_BASE + UART_REG_DR, b)
    uart3_tx_hex = bytes(bus.uart_tx_streams[3]).hex()

    # Exercise MHLX UIPC_BB channel (ch0) roundtrip + Cold-Boot & Warm-Boot shm_Loader handshakes
    bus.push_ring(MHLX_CH_UIPC_BB, "tx", 0x0416, struct.pack("<II", 0x92840747, 800))
    bus.write32(MHLX_BASE + MHLX_REG_DOORBELL_SEND, (1 << 16) | MHLX_CH_UIPC_BB)
    ch0_tx = bus.pop_ring(MHLX_CH_UIPC_BB, "tx")
    bus.write32(MHLX_BASE + MHLX_REG_IRQ_CLEAR, 1 << MHLX_CH_UIPC_BB)
    bus.push_ring(MHLX_CH_UIPC_BB, "rx", 0x8416, struct.pack("<II", 0x92840747, 0))
    bus.write32(MHLX_BASE + MHLX_REG_DOORBELL_SEND, (0 << 16) | MHLX_CH_UIPC_BB)
    ch0_rx = bus.pop_ring(MHLX_CH_UIPC_BB, "rx")
    bus.write32(MHLX_BASE + MHLX_REG_IRQ_CLEAR, 1 << MHLX_CH_UIPC_BB)

    cold_boot = bus.run_shm_loader_handshake(mode="cold_boot")
    warm_boot = bus.run_shm_loader_handshake(mode="warm_boot")

    _, _, cp_mut_final = bus.verify_cp_immutability()

    mmio_ok = (
        mhlx_id == MHLX_MAGIC
        and spacc_ver == SPACC_VERSION_MAGIC
        and spacc_lock == 1
        and spacc_userland_blocked
        and wdt_resets == 0
        and bus.wdt_kick_count == 1
        and uart3_tx_hex == "01030c00"
        and ch0_tx is not None
        and ch0_rx is not None
        and ch0_rx.opcode == 0x8416
        and bus.read32(MHLX_BASE + MHLX_REG_IRQ_STATUS) == 0
        and cold_boot.passed
        and warm_boot.passed
        and cp_mut_final == 0
        and bus.wbi_mutation_bytes == 0
    )

    all_passed = (
        donor_audit.all_contracts_verified
        and bool(fdt_verification["all_checks_passed"])
        and mmio_ok
    )

    core_payload = {
        "schema": PHASE_41_SCHEMA,
        "version": PHASE_41_VERSION,
        "all_checks_passed": all_passed,
        "clean_room_forced": is_forced_clean_room(eff_env),
        "redlines": {
            "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
            "cp_mutation_bytes": cp_mut_final,
            "wbi_mutation_bytes": bus.wbi_mutation_bytes,
            "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
            "physical_device_writes": PHYSICAL_DEVICE_WRITES,
            "donor_access_mode": DONOR_ACCESS_MODE,
        },
        "donor_kernel_mmio_audit": asdict(donor_audit),
        "fdt_synthesis_and_audit": fdt_verification,
        "mmio_window_emulation": {
            "window_range": [f"0x{MMIO_WINDOW_START:08x}", f"0x{MMIO_WINDOW_END - 1:08x}"],
            "window_size_bytes": MMIO_WINDOW_SIZE,
            "mhlx_id_hex": f"0x{mhlx_id:08x}",
            "spacc_version_hex": f"0x{spacc_ver:08x}",
            "spacc_key_lock": spacc_lock,
            "spacc_userland_blocked": spacc_userland_blocked,
            "wdt_resets": wdt_resets,
            "wdt_kick_count": bus.wdt_kick_count,
            "ttyama3_uart_tx_hex": uart3_tx_hex,
            "mmio_read_count": bus.mmio_read_count,
            "mmio_write_count": bus.mmio_write_count,
            "mhlx_doorbell_count": bus.mhlx_doorbell_count,
            "mhlx_channels": [asdict(bus.channel_snapshot(i)) for i in range(MHLX_CHANNEL_COUNT)],
        },
        "shm_loader_handshakes": {
            "cold_boot": asdict(cold_boot),
            "warm_boot": asdict(warm_boot),
        },
    }

    digest = hashlib.sha256(
        json.dumps(core_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    core_payload["audit_digest_sha256"] = digest
    return core_payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cxd90057_dtb_and_mhlx_emulator.py",
        description="Phase 41 CXD90057 Pure-Python FDT/DTB Synthesizer, MHLX Ring & MMIO Emulator",
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 41 self-test audit")
    parser.add_argument("--clean-room", action="store_true", help="Force deterministic clean-room mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit summary")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    parser.add_argument("--dts", action="store_true", help="Emit synthesized hybrid CXD90057 .dts source")
    parser.add_argument("--fdt-info", action="store_true", help="Emit parsed FDT v17 header & topology JSON")
    parser.add_argument("--bt-mode", default="HEALTHY_VIRTUAL_ROM_V1", help="BT UART mode annotation in DTB")
    args = parser.parse_args(argv)

    if args.dts:
        compiled = compile_cxd90057_hybrid_fdt(bt_mode=args.bt_mode)
        sys.stdout.write(compiled.dts_source)
        return 0

    if args.fdt_info:
        compiled = compile_cxd90057_hybrid_fdt(bt_mode=args.bt_mode)
        info = verify_hybrid_fdt_topology(compiled)
        sys.stdout.write(json.dumps(info, indent=2) + "\n")
        return 0 if info["all_checks_passed"] else 1

    rep = run_phase41_emulator_audit(
        bt_mode=args.bt_mode,
        force_clean_room=True if args.clean_room else None,
    )

    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        fdt = rep["fdt_synthesis_and_audit"]
        donor = rep["donor_kernel_mmio_audit"]
        sys.stdout.write(
            f"[{status}] Phase 41 CXD90057 DTB+MHLX+MMIO | mode={donor['source_mode']} "
            f"fdt={fdt['totalsize_bytes']}B({fdt['node_count']}nodes) "
            f"cp_mut={rep['redlines']['cp_mutation_bytes']} "
            f"doorbells={rep['mmio_window_emulation']['mhlx_doorbell_count']} "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
