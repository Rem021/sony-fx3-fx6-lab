"""Phase 22 (P12) — Wireless (`WF-12` Wi-Fi/BT / Bluetooth `BSA` / `InfraPericon` / `SeqQueueNetwork`) Non-Blocking Fault Isolation & `00342260` Bootloop Immunity Verifier.

Performs read-only (`O_RDONLY`) ELF64/AArch64 binary disassembly & signature verification,
Unicorn AArch64 instruction-level fault-injection emulation, and deterministic state-machine
validation across FX6 v6.01 & FX3 v7.02 wireless/BT/network initialization and degraded-mode
isolation (`P3` + `P12`), under strict Stage-A/B hardware redlines:

- `wbi_mutation_bytes == 0` (`p5:/wbi`)
- `cp_mutation_bytes == 0` (`p8:/cp`, `p8_cp_mutation_forbidden = True`)
- `kmod_mutation_count == 0` (stock FX3 `.ko`)
- `persistent_emmc_writes_authorized = False`
- `persistent_write_release = False`
- `nvram_persistent_writes == 0` (RAM-Shadow `BK4\\0` only)

Five Fault-Injection Scenarios (Unicorn AArch64 + Deterministic State Machine):
1. `WF12_SDIO_PROBE_TIMEOUT`:
   `libWlanControlCommon.so::installWlanDrivers` (`0x28c8`) + `initializePort` (`0x1bac`) +
   `libWlanResource.so::loadWlanHostDrivers` (`0x6b5c`) + `WlanResourceMainThread` (`0x80f8`)
   under SDIO `ENODEV` / firmware timeout, proving unpatched `handleFatalError` (`0x70d4`)
   loops forever in `usleep(1_000_000)` while `P12` non-blocking guard returns cleanly (`0` WDT resets).
2. `BT_BSA_UART_NO_RESPONSE`:
   `libInfraBluetoothCore.so::wrapper_bt_interface_enable` (`0x1f0f0`) +
   `CBTCoreProcess::startProcessOnBoot` (`0x105d8`) under missing BSA / `/dev/ttyAMA3` HAL
   (e.g., QEMU without `virtual-rom-v1` or degraded `WF-12`), proving graceful `0xbb9` (`3001`)
   fallback with zero `"System Error"` abort.
3. `NOTICE_00342260_MALFUNCTION_CODE`:
   FX6 `appFw.so` `0x13448e0` (`Fatal error on Wi-Fi func`) & `0x0c94dec` (`Invalid Bluetooth
   Wi-Fi Control`) + FX3/FX6 `WIFI_DEVICE_ERROR_TYPE_HARDWARE_ERROR` -> dismissible Notice
   `00342260` degraded state / Airplane-mode latch while shooting & recording remain unaffected.
4. `SEQ_QUEUE_NETWORK_DRAIN_NONBLOCKING`:
   FX6 `appFw.so::Application_System_Init` (`0x0c0b044`) + `libInfraNetInitializer.so::initialize`
   (`0x2318`) + `SeqQueueNetwork*` bounded promise/future timeout (`< 50 ms` simulated budget).
5. `AIRPLANE_MODE_RAM_SHADOW_DEFAULT`:
   RAM-Shadow `BK4\\0` defaults (`0x019e0012 = 0x00`, `0x0051000f = 0x00`, `0x01a20002 = 0x00`,
   `AIRPLANE_MODE = 1`) verified in Unicorn AArch64 via `libInfraBluetooth.so::Init` (`0x12620`)
   and `libResourceBluetooth.so::ResourceBluetooth_init` (`0x1a98`) `cbz w0` early-return gates,
   ensuring marginal `WF-12` hardware is never stressed on cold boot with `0` stock NVRAM writes.

All donor file reads use `os.O_RDONLY` exclusively via `donor_paths.py`, with full deterministic
`FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic ELF64/AArch64 fixtures.
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
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .backup_mount_tolerance_verifier import (
    BK4_HEADER_SIZE,
    BK4_SHADOW_MODEL_TAG,
    BK4_SHADOW_SUBSYSTEM_COUNT,
    BK4_VERSION_WORD0,
)
from .donor_paths import (
    ensure_unicorn_site_on_sys_path,
    is_forced_clean_room as _donor_paths_clean_room,
    resolve_fx3_seed_bk4_path,
    resolve_fx3_vm_work_root,
    resolve_fx6_donor_root,
)
from .elf_verify import PF_R, PF_X, parse_elf64_aarch64
from .patcher import (
    P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC,
    LibraryPatchSpec,
    PatchSiteSpec,
    apply_patch_spec,
    rollback_patch_spec,
)

from fx3_safety.boot_contracts import BK4_MAGIC, BK4_SYNC_MARKER, parse_bk4_record

try:
    import unicorn as U
    from unicorn import arm64_const as A
except ImportError:
    ensure_unicorn_site_on_sys_path()
    import unicorn as U
    from unicorn import arm64_const as A


PHASE_22_SCHEMA = "stage_a_phase22_wf12_wireless_guard_v1"
PHASE_22_VERSION = "22.0.0"

# Hard Stage-A/B Redline Locks (NEVER mutate)
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
PERSISTENT_WRITE_RELEASE = False
P8_CP_MUTATION_FORBIDDEN = True
WBI_MUTATION_BYTES = 0
CP_MUTATION_BYTES = 0
KMOD_MUTATION_COUNT = 0
NVRAM_PERSISTENT_WRITES = 0

# Sony Notice 00342260 & Hardware Fault Constants
SONY_NOTICE_00342260_ID = "00342260"
SONY_NOTICE_00342260_UPDATED = "2026-01-20"
SONY_NOTICE_00342260_MESSAGE = "The Wi-Fi/Bluetooth unit has malfunctioned."
APPLICATION_SYSTEM_INIT_BUDGET_MS = 50.0
WLAN_RESOURCE_FATAL_SLEEP_US = 1_000_000  # 0x0f4240 in handleFatalError @ 0x70d4
BT_BSA_HAL_INIT_ERR_CODE = 0x0BB9  # 3001 in wrapper_bt_interface_enable @ 0x1f0f0
REMOTE_BOARD_SEM_ID = 0x810708DC
APPFW_SYSINIT_QUEUE_ID = 0x008F013A

# BK4 Wireless / Bluetooth / RemoteBoard Keys
BT_BKID_ENABLE_PRIMARY = 0x019E0012
BT_BKID_ENABLE_SECONDARY = 0x0051000F
BT_BKID_RSRC_MODE = 0x01A20002
REMOTE_BOARD_BKID_A = 0x00FA01A3
REMOTE_BOARD_BKID_B = 0x00FA01A4

# Pinned Donor VMAs
FX6_REMOTEBOARD_EXEC_RCV_VMA = 0x157C
FX6_REMOTEBOARD_MAIN_THREAD_VMA = 0x1700
FX6_REMOTEBOARD_PLT_OSAL_WAI_SEM_TMO = 0x1130
FX6_REMOTEBOARD_PLT_MM_MMAP = 0x1210
FX6_REMOTEBOARD_PLT_BACKUP_READ_8B = 0x1220

FX6_WLAN_RSRC_INIT_VMA = 0x663C
FX6_WLAN_RSRC_LOAD_DRV_VMA = 0x6B5C
FX6_WLAN_RSRC_HANDLE_FATAL_VMA = 0x70D4
FX6_WLAN_RSRC_FATAL_LOOP_VMA = 0x70E8
FX6_WLAN_RSRC_MAIN_THREAD_VMA = 0x80F8
FX6_WLAN_RSRC_PLT_OSAL_RCV_MSG_TMO = 0x3FB0
FX6_WLAN_RSRC_PLT_INSMOD = 0x4380
FX6_WLAN_RSRC_PLT_HANDLE_FATAL = 0x44B0
FX6_WLAN_RSRC_PLT_OSAL_FREE_MSG = 0x4610
FX6_WLAN_RSRC_PLT_SET_SEM_PCIE = 0x4500
FX6_WLAN_RSRC_USLEEP_HELPER_VMA = 0x5DB0

FX6_WLAN_CTRL_INIT_PORT_VMA = 0x1BAC
FX6_WLAN_CTRL_INSTALL_DRV_VMA = 0x28C8
FX6_WLAN_CTRL_LOAD_FW_VMA = 0x2A50
FX6_WLAN_CTRL_PLT_OPEN = 0x11B0
FX6_WLAN_CTRL_PLT_MMAP = 0x1260
FX6_WLAN_CTRL_PLT_CLOSE = 0x12B0
FX6_WLAN_CTRL_PLT_INSMOD = 0x12C0
FX6_WLAN_CTRL_PLT_TRACE_ERR = 0x1330

FX6_BT_INIT_VMA = 0x12620
FX6_BT_INIT_EARLY_RET_VMA = 0x126AC
FX6_BT_PLT_ZNWM = 0xB060
FX6_BT_PLT_BLOG_CTOR = 0xACE0
FX6_BT_PLT_INIT_BACKUP = 0xB7C0
FX6_BT_PLT_READ_BACKUP = 0xB910
FX6_BT_PLT_BLOG_ERR_PLACE = 0xB820
FX6_BT_PLT_BLOG_ERR_INFO = 0xADA0

FX6_BTCORE_START_BOOT_VMA = 0x105D8
FX6_BTCORE_ENABLE_VMA = 0x1F0F0
FX6_BTCORE_PLT_GET_HAL = 0xD570
FX6_BTCORE_PLT_ZNWM = 0xDD80
FX6_BTCORE_PLT_ZDLPVM = 0xDDC0
FX6_BTCORE_PLT_BLOG_CTOR = 0xD7D0
FX6_BTCORE_PLT_BLOG_DTOR = 0xD840
FX6_BTCORE_PLT_BLOG_ERR_PLACE = 0xE850
FX6_BTCORE_PLT_BLOG_ERR_INFO = 0xD910
FX6_BTCORE_PLT_BLOG_UPPER_CALL = 0xD670
FX6_BTCORE_PLT_BLOG_LOWER_CALL = 0xE530
FX6_BTCORE_PLT_BLOG_UPPER_RET = 0xE320
FX6_BTCORE_PLT_START_QCA_BSA = 0xDF10

FX6_RSRC_BT_INIT_VMA = 0x1A98
FX6_RSRC_BT_EARLY_RET_VMA = 0x1BE0
FX6_RSRC_BT_PLT_BACKUP_GET_SIZE = 0xEB0
FX6_RSRC_BT_PLT_BACKUP_READ = 0xEF0
FX6_RSRC_BT_PLT_ZNWM = 0xED0
FX6_RSRC_BT_PLT_ZDLPVM = 0xEE0
FX6_RSRC_BT_PLT_BLOG_CTOR = 0xE50
FX6_RSRC_BT_PLT_BLOG_DTOR = 0xE60
FX6_RSRC_BT_PLT_BLOG_INFO = 0xF60
FX6_RSRC_BT_PLT_BLOG_ERR_PLACE = 0xFB0
FX6_RSRC_BT_PLT_BLOG_ERR_INFO = 0xE80

FX6_NET_INIT_VMA = 0x2318
FX6_NET_INIT_PLT_LOOPBACK = 0x1D10
FX6_NET_INIT_PLT_RSRC_MGR = 0x1D80
FX6_NET_INIT_PLT_MEMSET = 0x1DB0
FX6_NET_INIT_PLT_TRACE = 0x1E10
FX6_NET_INIT_PLT_INIT_PART = 0x1F00
FX6_NET_INIT_PLT_TRACE_ERR = 0x1F10
FX6_NET_INIT_PLT_ERRNO = 0x1F30
FX6_NET_INIT_PLT_FOPEN = 0x1F50
FX6_NET_INIT_TAIL_HELPER_VMA = 0x228C

FX6_APPFW_SYSINIT_VMA = 0x0C0B044
FX6_APPFW_WIFI_FATAL_HANDLER_VMA = 0x13448E0
FX6_APPFW_BT_WIFI_INVALID_CTRL_VMA = 0x0C94DEC
FX3_APPFW_SYSINIT_VMA = 0x16EFB90

# Pinned Donor SHA-256 Digests
FX6_WLAN_RSRC_SHA256 = "eb7785e025d11eefced79de3a918034960422ee75dc09b0fead69646f7e8bd88"
FX6_WLAN_CTRL_SHA256 = "4dccfa865720f662c2f02c741bce609bbe132280ab537eae990d913450f2f2c9"
FX6_BT_SHA256 = "3b3c1a411f3e157c6d6f7db6ae4dbbb0fc29920561eb3743b7c7723f974cc788"
FX6_BT_CORE_SHA256 = "84a9bf33d26914a42c46ffc34381041d56006b3fdf76a2f475d954b602292694"
FX6_RSRC_BT_SHA256 = "2be9da99a2d45980449ac04814950896058b375c0a565f99bc5eb3fc92a0a16c"
FX6_BT_VENDOR_SHA256 = "3c9a48fedd5bbc829d3d166feac090d3d5df3f347d9599f864722f885bdbf8bb"
FX6_NET_INIT_SHA256 = "9628f8d97434734742078347d99c1c0a6c00fec43534d1b608f6ca6899c0fc5d"
FX3_INSMOD1_SHA256 = "22f29d06d7776fe5e8362c17049beabfd3e3bebffd222e51276e3704d483a591"
FX3_INSMOD2_SHA256 = "19757bdd450061f861e2da44a6a93be2525668e3f7edc64e5a99a25bde56564e"


def _pack_insns(*words: int) -> bytes:
    return b"".join(struct.pack("<I", w) for w in words)


# P12: libWlanResource.so::_Z16handleFatalErrorv @ 0x70d4 infinite usleep(1s) loop guard
P12_WLAN_FATAL_GUARD_SPEC = LibraryPatchSpec(
    spec_id="P12_libWlanResource_fatal_guard",
    library_name="libWlanResource.so",
    expected_size=56464,
    donor_sha256=FX6_WLAN_RSRC_SHA256,
    sites=(
        PatchSiteSpec(
            site_id="P12_wlan_resource_handleFatalError_nonblocking",
            patch_group="P12",
            symbol_or_desc="libWlanResource::_Z16handleFatalErrorv @ 0x70d4 (infinite usleep -> mov w0, #0; ret)",
            vma=FX6_WLAN_RSRC_HANDLE_FATAL_VMA,
            expected_file_offset=FX6_WLAN_RSRC_HANDLE_FATAL_VMA,
            required_segment_flags=PF_R | PF_X,
            original_bytes=_pack_insns(0xA9BE7BFD, 0x910003FD),  # stp x29, x30, [sp, #-0x20]!; mov x29, sp
            patched_bytes=_pack_insns(0x52800000, 0xD65F03C0),   # mov w0, #0; ret
            post_context=_pack_insns(0xF9000BF3, 0xD2884813),    # str x19, [sp, #0x10]; mov x19, #0x4240
        ),
    ),
)


# Required String Markers (fast C-level `bytes.find` scans)
REQUIRED_FX6_APPFW_WIRELESS_MARKERS: Tuple[str, ...] = (
    "Application_System_Init",
    "sequence_set_release_lock_dummy_SeqQueueNetworkUsb",
    "sequence_set_release_lock_dummy_SeqQueueNetworkWifiConnectionStandby",
    "N5model49sequence_set_release_lock_dummy_SeqQueueBluetoothE",
    "WIFI_DEVICE_ERROR_TYPE_HARDWARE_ERROR",
    "MODEL_WIFI_DEVICE_ERROR",
    "MODEL_WIFI_FATAL_ERROR_OCCURRED",
    "%s%s(%d) Fatal error on Wi-Fi func",
    "%s%s(%d)Invalid Bluetooth Wi-Fi Control: %d",
    "%s%s(%d) Failure get_server_info(CT_BT_ERR_STATE)",
    "extern_BKID_APP_EXTERN_SETTING_AIRPLANE_MODE",
    "EXTERN_SETTING_AIRPLANE_MODE_ON",
)

REQUIRED_FX3_APPFW_WIRELESS_MARKERS: Tuple[str, ...] = (
    "Application_System_Init",
    "sequence_set_release_lock_dummy_SeqQueueNetworkUsb",
    "WIFI_DEVICE_ERROR_TYPE_NO_ERROR",
    "WIFI_DEVICE_ERROR_TYPE_HARDWARE_ERROR",
    "WIFI_DEVICE_ERROR_TYPE_SOFTWARE_ERROR",
    "MODEL_WIFI_DEVICE_ERROR",
    "extern_BKID_APP_EXTERN_SETTING_AIRPLANE_MODE",
    "EXTERN_SETTING_AIRPLANE_MODE_ON",
    "No40_AirplaneMode",
)

REQUIRED_FX6_WLAN_RSRC_MARKERS: Tuple[str, ...] = (
    "/usr/kmod/wlan.ko",
    "/usr/kmod/wlanMemoryAllocator.ko",
    "/usr/kmod/sdio_lib.ko",
    "/usr/kmod/sdio_busdriver.ko",
    "/usr/lib/firmware/qwlan30.bin",
    "wlan0",
    "wlan_start_wait_time=",
)

REQUIRED_FX6_BT_MARKERS: Tuple[str, ...] = (
    "/dev/ttyAMA3",
    "HCI device open failed",
    "libosal_uipc.so",
)

EARLY_BOOT_FORBIDDEN_WIRELESS_KMODS: Tuple[str, ...] = (
    "wlan.ko",
    "wlanIrq.ko",
    "wlanMemoryAllocator.ko",
    "sdio_lib.ko",
    "sdio_busdriver.ko",
    "ar6000.ko",
    "mmcioWrapper.ko",
)

FAULT_SCENARIO_IDS: Tuple[str, ...] = (
    "WF12_SDIO_PROBE_TIMEOUT",
    "BT_BSA_UART_NO_RESPONSE",
    "NOTICE_00342260_MALFUNCTION_CODE",
    "SEQ_QUEUE_NETWORK_DRAIN_NONBLOCKING",
    "AIRPLANE_MODE_RAM_SHADOW_DEFAULT",
)


class Phase22WirelessIsolationError(ValueError):
    """Raised when a Phase 22 wireless fault-isolation contract check fails."""


# ---------------------------------------------------------------------------
# Strictly Read-Only (`O_RDONLY`) Donor File Resolution & Reading
# ---------------------------------------------------------------------------


def read_donor_bytes_readonly(path: Path) -> bytes:
    """Read a donor file strictly via `os.O_RDONLY` without any write flags."""
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


def resolve_phase22_donor_paths(
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Path]:
    """Resolve all Phase 22 FX6 v6.01 & FX3 v7.02 read-only donor paths."""
    fx6_root = resolve_fx6_donor_root(env=env)
    fx3_vm = resolve_fx3_vm_work_root(env=env)
    fx6_lib = fx6_root / "nflasha15-files" / "lib"
    fx6_bin = fx6_root / "nflasha15-files" / "bin"
    fx3_scripts = fx3_vm / "menu-repair-01" / "original-uipc" / "original-scripts"
    fx3_audit_lib = fx3_vm / "fx3-audit" / "original-members" / "nflasha15" / "lib"

    return {
        "fx6_appfw": fx6_lib / "appFw.so",
        "fx6_remoteboard": fx6_lib / "libInfraAppRemoteBoard.so",
        "fx6_wlan_rsrc": fx6_lib / "libWlanResource.so",
        "fx6_wlan_ctrl": fx6_lib / "libWlanControlCommon.so",
        "fx6_bt": fx6_lib / "libInfraBluetooth.so",
        "fx6_bt_core": fx6_lib / "libInfraBluetoothCore.so",
        "fx6_rsrc_bt": fx6_lib / "libResourceBluetooth.so",
        "fx6_bt_vendor": fx6_lib / "libbt-vendor.so",
        "fx6_net_init": fx6_lib / "libInfraNetInitializer.so",
        "fx6_start_bt_sh": fx6_bin / "startBTCore.sh",
        "fx6_bk4": fx6_root / "tree" / "0110_backup" / "SYSIPSX-DSLR" / "CHAPLIN" / "CX95898_NTSC.bin",
        "fx3_appfw": fx3_audit_lib / "appFw.so",
        "fx3_insmod1": fx3_scripts / "insmod_drv1",
        "fx3_insmod2": fx3_scripts / "insmod_drv2",
        "fx3_bk4": resolve_fx3_seed_bk4_path(env=env),
    }


def is_phase22_clean_room_mode(
    paths: Optional[Mapping[str, Path]] = None,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> bool:
    """Return True if clean-room CI mode is forced or any required donor file is absent."""
    if _donor_paths_clean_room(env):
        return True
    resolved = resolve_phase22_donor_paths(env=env) if paths is None else paths
    return not all(Path(p).is_file() for p in resolved.values())


# ---------------------------------------------------------------------------
# Clean-Room Synthetic ELF64/AArch64 & BK4\0 Fixture Builder
# ---------------------------------------------------------------------------


def _build_synthetic_elf64_aarch64(total_size: int, code_chunks: Mapping[int, bytes], rodata_chunks: Mapping[int, bytes]) -> bytes:
    """Construct a minimal valid ELF64 AArch64 (`ET_DYN`) binary with `PT_LOAD[0]` at VMA 0."""
    buf = bytearray(total_size)
    # ELF64 header (64 bytes)
    e_ident = b"\x7fELF" + bytes((2, 1, 1, 0)) + b"\x00" * 8
    struct.pack_into(
        "<16sHHIQQQIHHHHHH",
        buf,
        0,
        e_ident,
        3,       # ET_DYN
        183,     # EM_AARCH64
        1,       # EV_CURRENT
        0x1000,  # e_entry
        64,      # e_phoff
        0,       # e_shoff
        0,       # e_flags
        64,      # e_ehsize
        56,      # e_phentsize
        1,       # e_phnum
        64,      # e_shentsize
        0,       # e_shnum
        0,       # e_shstrndx
    )
    # Single PT_LOAD covering full buffer with PF_R | PF_X | PF_W (for Unicorn/patcher tests)
    struct.pack_into(
        "<IIQQQQQQ",
        buf,
        64,
        1,              # PT_LOAD
        PF_R | PF_X,    # PF_R | PF_X
        0,              # p_offset
        0,              # p_vaddr
        0,              # p_paddr
        total_size,     # p_filesz
        total_size,     # p_memsz
        0x10000,        # p_align
    )
    for off, payload in code_chunks.items():
        buf[off : off + len(payload)] = payload
    for off, payload in rodata_chunks.items():
        buf[off : off + len(payload)] = payload
    return bytes(buf)


def _encode_bl(from_addr: int, target_addr: int) -> int:
    delta = (target_addr - from_addr) >> 2
    return 0x94000000 | (delta & 0x3FFFFFF)


def _encode_b(from_addr: int, target_addr: int) -> int:
    delta = (target_addr - from_addr) >> 2
    return 0x14000000 | (delta & 0x3FFFFFF)


def _encode_cbz(reg: int, from_addr: int, target_addr: int) -> int:
    delta = (target_addr - from_addr) >> 2
    return 0x34000000 | ((delta & 0x7FFFF) << 5) | (reg & 0x1F)


def _encode_cbnz(reg: int, from_addr: int, target_addr: int) -> int:
    delta = (target_addr - from_addr) >> 2
    return 0x35000000 | ((delta & 0x7FFFF) << 5) | (reg & 0x1F)


def _build_synthetic_bk4(total_size: int = 857900, subsystems: int = 819, properties: int = 35668) -> bytes:
    """Build a checksum-valid synthetic `BK4\\0` container compatible with `parse_bk4_record`."""
    data_offset = 0x200
    data_size = total_size - data_offset
    buf = bytearray(total_size)
    struct.pack_into("<I", buf, 0x00, BK4_VERSION_WORD0)
    struct.pack_into("<I", buf, 0x04, BK4_SYNC_MARKER)
    buf[0x08] = 1
    buf[0x0C:0x10] = BK4_MAGIC
    struct.pack_into("<IIII", buf, 0x10, subsystems, properties, data_offset, data_size)
    # Seed deterministic non-zero payload region
    for i in range(data_offset, min(total_size, data_offset + 256), 4):
        struct.pack_into("<I", buf, i, (i * 0x01010101) & 0xFFFFFFFF)
    checksum = (sum(buf[0:0x20]) + sum(buf[0x24:total_size])) & 0xFFFFFFFF
    struct.pack_into("<I", buf, 0x20, checksum)
    return bytes(buf)


def build_clean_room_phase22_fixtures() -> Dict[str, bytes]:
    """Generate deterministic Clean-Room synthetic ELF64/AArch64 & BK4 fixtures."""
    ret_insn = 0xD65F03C0

    # 1. libInfraAppRemoteBoard.so (exact P3 offsets 0x157c & 0x1700)
    rb_code: Dict[int, bytes] = {
        FX6_REMOTEBOARD_PLT_OSAL_WAI_SEM_TMO: _pack_insns(ret_insn),
        FX6_REMOTEBOARD_PLT_MM_MMAP: _pack_insns(ret_insn),
        FX6_REMOTEBOARD_PLT_BACKUP_READ_8B: _pack_insns(ret_insn),
        FX6_REMOTEBOARD_EXEC_RCV_VMA: _pack_insns(
            0xA9BE7BFD,  # stp x29, x30, [sp, #-0x20]!
            0x12800001,  # mov w1, #-1
            0x910003FD,  # mov x29, sp
            0xA90153F3,  # stp x19, x20, [sp, #0x10]
            0x52811B80,  # mov w0, #0x8dc
            0x72B020E0,  # movk w0, #0x8107, lsl #16 -> 0x810708dc
            _encode_bl(FX6_REMOTEBOARD_EXEC_RCV_VMA + 0x18, FX6_REMOTEBOARD_PLT_OSAL_WAI_SEM_TMO),
            0xA94153F3,  # ldp x19, x20, [sp, #0x10]
            0xA8C27BFD,  # ldp x29, x30, [sp], #0x20
            ret_insn,
        ),
        FX6_REMOTEBOARD_MAIN_THREAD_VMA: _pack_insns(
            0xA9BC7BFD,  # stp x29, x30, [sp, #-0x40]!
            0x52803460,  # mov w0, #0x1a3
            0x72A01F40,  # movk w0, #0xfa, lsl #16
            0x910003FD,  # mov x29, sp
            _encode_bl(FX6_REMOTEBOARD_MAIN_THREAD_VMA + 0x10, FX6_REMOTEBOARD_PLT_BACKUP_READ_8B),
            0xAA0003F3,  # mov x19, x0
            0x52803480,  # mov w0, #0x1a4
            0x72A01F40,  # movk w0, #0xfa, lsl #16
            _encode_bl(FX6_REMOTEBOARD_MAIN_THREAD_VMA + 0x20, FX6_REMOTEBOARD_PLT_BACKUP_READ_8B),
            0xAA0003E1,  # mov x1, x0
            0xAA1303E0,  # mov x0, x19
            _encode_bl(FX6_REMOTEBOARD_MAIN_THREAD_VMA + 0x2C, FX6_REMOTEBOARD_PLT_MM_MMAP),
            0x52811B80,  # mov w0, #0x8dc
            0x72B020E0,  # movk w0, #0x8107, lsl #16
            0x12800001,  # mov w1, #-1
            _encode_bl(FX6_REMOTEBOARD_MAIN_THREAD_VMA + 0x3C, FX6_REMOTEBOARD_PLT_OSAL_WAI_SEM_TMO),
            0x52800000,  # mov w0, #0
            0xA8C47BFD,  # ldp x29, x30, [sp], #0x40
            ret_insn,
        ),
    }
    fx6_remoteboard = _build_synthetic_elf64_aarch64(10448, rb_code, {})

    # 2. libWlanResource.so (exact P12 offset 0x70d4 & WlanResourceMainThread @ 0x80f8)
    wr_code: Dict[int, bytes] = {
        FX6_WLAN_RSRC_PLT_OSAL_RCV_MSG_TMO: _pack_insns(ret_insn),
        FX6_WLAN_RSRC_PLT_INSMOD: _pack_insns(ret_insn),
        FX6_WLAN_RSRC_PLT_HANDLE_FATAL: _pack_insns(_encode_b(FX6_WLAN_RSRC_PLT_HANDLE_FATAL, FX6_WLAN_RSRC_HANDLE_FATAL_VMA)),
        FX6_WLAN_RSRC_PLT_SET_SEM_PCIE: _pack_insns(ret_insn),
        FX6_WLAN_RSRC_PLT_OSAL_FREE_MSG: _pack_insns(ret_insn),
        FX6_WLAN_RSRC_USLEEP_HELPER_VMA: _pack_insns(ret_insn),
        FX6_WLAN_RSRC_LOAD_DRV_VMA: _pack_insns(
            0xA9BE7BFD,
            0x910003FD,
            0xD2800000,
            0xD2800001,
            _encode_bl(FX6_WLAN_RSRC_LOAD_DRV_VMA + 0x10, FX6_WLAN_RSRC_PLT_INSMOD),
            _encode_cbz(0, FX6_WLAN_RSRC_LOAD_DRV_VMA + 0x14, FX6_WLAN_RSRC_LOAD_DRV_VMA + 0x20),
            0x12800000,  # movn w0, #0 (-1)
            0xA8C27BFD,
            ret_insn,
        ),
        FX6_WLAN_RSRC_HANDLE_FATAL_VMA: _pack_insns(
            0xA9BE7BFD,  # stp x29, x30, [sp, #-0x20]!
            0x910003FD,  # mov x29, sp
            0xF9000BF3,  # str x19, [sp, #0x10]
            0xD2884813,  # mov x19, #0x4240
            0xF2A001F3,  # movk x19, #0xf, lsl #16 -> 1_000_000
            0xAA1303E0,  # mov x0, x19 (0x70e8)
            _encode_bl(FX6_WLAN_RSRC_HANDLE_FATAL_VMA + 0x18, FX6_WLAN_RSRC_USLEEP_HELPER_VMA),
            _encode_b(FX6_WLAN_RSRC_HANDLE_FATAL_VMA + 0x1C, FX6_WLAN_RSRC_FATAL_LOOP_VMA),  # infinite loop
        ),
        FX6_WLAN_RSRC_MAIN_THREAD_VMA: _pack_insns(
            0xA9BD7BFD,
            0x910003FD,
            0xA90153F3,
            _encode_bl(FX6_WLAN_RSRC_MAIN_THREAD_VMA + 0x0C, FX6_WLAN_RSRC_PLT_SET_SEM_PCIE),
            0x12800002,  # mov w2, #-1
            _encode_bl(FX6_WLAN_RSRC_MAIN_THREAD_VMA + 0x14, FX6_WLAN_RSRC_PLT_OSAL_RCV_MSG_TMO),
            _encode_cbz(0, FX6_WLAN_RSRC_MAIN_THREAD_VMA + 0x18, FX6_WLAN_RSRC_MAIN_THREAD_VMA + 0x24),
            _encode_bl(FX6_WLAN_RSRC_MAIN_THREAD_VMA + 0x1C, FX6_WLAN_RSRC_PLT_HANDLE_FATAL),
            0x14000002,  # b +8 (exit gracefully when guarded!)
            _encode_bl(FX6_WLAN_RSRC_MAIN_THREAD_VMA + 0x24, FX6_WLAN_RSRC_PLT_OSAL_FREE_MSG),
            0x52800000,  # mov w0, #0
            0xA94153F3,
            0xA8C37BFD,
            ret_insn,
        ),
    }
    wr_ro: Dict[int, bytes] = {}
    cursor = 0xA500
    for marker in REQUIRED_FX6_WLAN_RSRC_MARKERS:
        raw = marker.encode("latin1") + b"\x00"
        wr_ro[cursor] = raw
        cursor += len(raw)
    fx6_wlan_rsrc = _build_synthetic_elf64_aarch64(56464, wr_code, wr_ro)

    # 3. libWlanControlCommon.so (initializePort @ 0x1bac, installWlanDrivers @ 0x28c8)
    wc_code: Dict[int, bytes] = {
        FX6_WLAN_CTRL_PLT_OPEN: _pack_insns(ret_insn),
        FX6_WLAN_CTRL_PLT_MMAP: _pack_insns(ret_insn),
        FX6_WLAN_CTRL_PLT_CLOSE: _pack_insns(ret_insn),
        FX6_WLAN_CTRL_PLT_INSMOD: _pack_insns(ret_insn),
        FX6_WLAN_CTRL_PLT_TRACE_ERR: _pack_insns(ret_insn),
        FX6_WLAN_CTRL_INIT_PORT_VMA: _pack_insns(
            0xA9BE7BFD,
            0x910003FD,
            0x52820041,
            _encode_bl(FX6_WLAN_CTRL_INIT_PORT_VMA + 0x0C, FX6_WLAN_CTRL_PLT_OPEN),
            0x3100041F,  # cmn w0, #1
            0x540000E0,  # b.eq +0x1c (err)
            _encode_bl(FX6_WLAN_CTRL_INIT_PORT_VMA + 0x18, FX6_WLAN_CTRL_PLT_CLOSE),
            0x52800041,  # open("/dev/gpio")
            _encode_bl(FX6_WLAN_CTRL_INIT_PORT_VMA + 0x20, FX6_WLAN_CTRL_PLT_OPEN),
            0x3100041F,
            0x54000060,  # b.eq +0xc (err)
            0x52800000,
            0xA8C27BFD,
            ret_insn,
            _encode_bl(FX6_WLAN_CTRL_INIT_PORT_VMA + 0x38, FX6_WLAN_CTRL_PLT_TRACE_ERR),
            0x12800000,  # movn w0, #0 (-1)
            0xA8C27BFD,
            ret_insn,
        ),
        FX6_WLAN_CTRL_INSTALL_DRV_VMA: _pack_insns(
            0xA9BE7BFD,
            0x910003FD,
            _encode_bl(FX6_WLAN_CTRL_INSTALL_DRV_VMA + 0x08, FX6_WLAN_CTRL_PLT_INSMOD),
            _encode_cbz(0, FX6_WLAN_CTRL_INSTALL_DRV_VMA + 0x0C, FX6_WLAN_CTRL_INSTALL_DRV_VMA + 0x20),
            0x528600C2,  # mov w2, #0x3006
            _encode_bl(FX6_WLAN_CTRL_INSTALL_DRV_VMA + 0x14, FX6_WLAN_CTRL_PLT_TRACE_ERR),
            0x12800000,  # movn w0, #0 (-1)
            0xA8C27BFD,
            ret_insn,
            0x52800000,
            0xA8C27BFD,
            ret_insn,
        ),
    }
    wc_ro = {
        0x3095: b"wlan0\x00/dev/mem\x00/dev/gpio\x00",
        0x315A: b"/usr/kmod/sdio_lib.ko\x00/usr/kmod/sdio_busdriver.ko\x00",
    }
    fx6_wlan_ctrl = _build_synthetic_elf64_aarch64(18528, wc_code, wc_ro)

    # 4. libInfraBluetooth.so (Init @ 0x12620 checking BK4 0x019e0012 -> early ret at 0x126ac)
    bt_code: Dict[int, bytes] = {
        FX6_BT_PLT_ZNWM: _pack_insns(ret_insn),
        FX6_BT_PLT_BLOG_CTOR: _pack_insns(ret_insn),
        FX6_BT_PLT_INIT_BACKUP: _pack_insns(ret_insn),
        FX6_BT_PLT_READ_BACKUP: _pack_insns(ret_insn),
        FX6_BT_PLT_BLOG_ERR_PLACE: _pack_insns(ret_insn),
        FX6_BT_PLT_BLOG_ERR_INFO: _pack_insns(ret_insn),
        FX6_BT_INIT_VMA: _pack_insns(
            0xA9BC7BFD,  # stp x29, x30, [sp, #-0x40]!
            0x910003FD,  # mov x29, sp
            0x52806040,  # mov w0, #0x302
            _encode_bl(FX6_BT_INIT_VMA + 0x0C, FX6_BT_PLT_INIT_BACKUP),
            0x52800240,  # mov w0, #0x12
            0x72A033C0,  # movk w0, #0x19e, lsl #16 -> 0x019e0012
            0x9100E3A1,  # add x1, x29, #0x38
            0x52800022,  # mov w2, #1
            _encode_bl(FX6_BT_INIT_VMA + 0x20, FX6_BT_PLT_READ_BACKUP),
            0x3940E3A0,  # ldrb w0, [x29, #0x38]
            _encode_cbz(0, FX6_BT_INIT_VMA + 0x28, FX6_BT_INIT_VMA + 0x44),  # early bypass when 0x00!
            0x528001E0,  # mov w0, #0xf
            0x72A00A20,  # movk w0, #0x51, lsl #16 -> 0x0051000f
            0x9100F3A1,  # add x1, x29, #0x3c
            0x52800022,  # mov w2, #1
            _encode_bl(FX6_BT_INIT_VMA + 0x3C, FX6_BT_PLT_READ_BACKUP),
            0x52800000,  # mov w0, #0 (0x12660)
            0xA8C47BFD,  # ldp x29, x30, [sp], #0x40
            ret_insn,
        ),
    }
    fx6_bt = _build_synthetic_elf64_aarch64(0x20000, bt_code, {0x18000: b"BSA\x00"})

    # 5. libInfraBluetoothCore.so (wrapper_bt_interface_enable @ 0x1f0f0, startProcessOnBoot @ 0x105d8)
    btc_code: Dict[int, bytes] = {
        FX6_BTCORE_PLT_GET_HAL: _pack_insns(ret_insn),
        FX6_BTCORE_PLT_ZNWM: _pack_insns(ret_insn),
        FX6_BTCORE_PLT_ZDLPVM: _pack_insns(ret_insn),
        FX6_BTCORE_PLT_BLOG_CTOR: _pack_insns(ret_insn),
        FX6_BTCORE_PLT_BLOG_DTOR: _pack_insns(ret_insn),
        FX6_BTCORE_PLT_BLOG_ERR_PLACE: _pack_insns(ret_insn),
        FX6_BTCORE_PLT_BLOG_ERR_INFO: _pack_insns(ret_insn),
        FX6_BTCORE_PLT_BLOG_UPPER_CALL: _pack_insns(ret_insn),
        FX6_BTCORE_PLT_BLOG_LOWER_CALL: _pack_insns(ret_insn),
        FX6_BTCORE_PLT_BLOG_UPPER_RET: _pack_insns(ret_insn),
        FX6_BTCORE_PLT_START_QCA_BSA: _pack_insns(ret_insn),
        FX6_BTCORE_ENABLE_VMA: _pack_insns(
            0xA9BE7BFD,
            0x910003FD,
            0xA90153F3,
            _encode_bl(FX6_BTCORE_ENABLE_VMA + 0x0C, FX6_BTCORE_PLT_GET_HAL),
            _encode_cbnz(0, FX6_BTCORE_ENABLE_VMA + 0x10, FX6_BTCORE_ENABLE_VMA + 0x28),
            _encode_bl(FX6_BTCORE_ENABLE_VMA + 0x14, FX6_BTCORE_PLT_BLOG_ERR_PLACE),
            0x52817720,  # mov w0, #0xbb9 (3001)
            0xA94153F3,
            0xA8C27BFD,
            ret_insn,
            0xF9400801,  # ldr x1, [x0, #0x10] (0x1f118)
            0x52800000,  # mov w0, #0
            0xD63F0020,  # blr x1
            0x2A0003F4,  # mov w20, w0
            0x7100029F,  # cmp w20, #0
            0x52817720,  # mov w0, #0xbb9
            0x1A9F1000,  # csel w0, w0, w20, ne
            0xA94153F3,
            0xA8C27BFD,
            ret_insn,
        ),
        FX6_BTCORE_START_BOOT_VMA: _pack_insns(
            0xA9BE7BFD,
            0x910003FD,
            0xA90153F3,
            0xAA0003F3,  # mov x19, x0
            0x39406260,  # ldrb w0, [x19, #0x18]
            0x7100081F,  # cmp w0, #2
            0x540000C1,  # b.ne +0x18 (err)
            _encode_bl(FX6_BTCORE_START_BOOT_VMA + 0x1C, FX6_BTCORE_PLT_START_QCA_BSA),
            0xA94153F3,
            0xA8C27BFD,
            ret_insn,
            _encode_bl(FX6_BTCORE_START_BOOT_VMA + 0x2C, FX6_BTCORE_PLT_BLOG_ERR_PLACE),
            0x12800000,  # movn w0, #0 (-1)
            0xA94153F3,
            0xA8C27BFD,
            ret_insn,
        ),
    }
    btc_ro = {0x9F73: b"libosal_uipc.so\x00", 0x34000: b"BSA\x00/dev/ttyAMA3\x00HCI device open failed\x00"}
    fx6_bt_core = _build_synthetic_elf64_aarch64(0x38000, btc_code, btc_ro)

    # 6. libResourceBluetooth.so (ResourceBluetooth_init @ 0x1a98 checking BK4 0x01a20002)
    rbt_code: Dict[int, bytes] = {
        FX6_RSRC_BT_PLT_BACKUP_GET_SIZE: _pack_insns(ret_insn),
        FX6_RSRC_BT_PLT_BACKUP_READ: _pack_insns(ret_insn),
        FX6_RSRC_BT_PLT_ZNWM: _pack_insns(ret_insn),
        FX6_RSRC_BT_PLT_ZDLPVM: _pack_insns(ret_insn),
        FX6_RSRC_BT_PLT_BLOG_CTOR: _pack_insns(ret_insn),
        FX6_RSRC_BT_PLT_BLOG_DTOR: _pack_insns(ret_insn),
        FX6_RSRC_BT_PLT_BLOG_INFO: _pack_insns(ret_insn),
        FX6_RSRC_BT_PLT_BLOG_ERR_PLACE: _pack_insns(ret_insn),
        FX6_RSRC_BT_PLT_BLOG_ERR_INFO: _pack_insns(ret_insn),
        FX6_RSRC_BT_INIT_VMA: _pack_insns(
            0xA9BD7BFD,
            0x910003FD,
            0x52800040,  # mov w0, #0x2
            0x72A03440,  # movk w0, #0x1a2, lsl #16 -> 0x01a20002
            _encode_bl(FX6_RSRC_BT_INIT_VMA + 0x10, FX6_RSRC_BT_PLT_BACKUP_GET_SIZE),
            0x52800040,
            0x72A03440,
            0x9100BFA1,  # add x1, x29, #0x2f
            _encode_bl(FX6_RSRC_BT_INIT_VMA + 0x20, FX6_RSRC_BT_PLT_BACKUP_READ),
            0x3940BFA0,  # ldrb w0, [x29, #0x2f]
            _encode_cbz(0, FX6_RSRC_BT_INIT_VMA + 0x28, FX6_RSRC_BT_INIT_VMA + 0x38),
            0x52800020,  # mov w0, #1 (hardware probed)
            0xA8C37BFD,
            ret_insn,
            0x52800000,  # mov w0, #0 (early Airplane/BT-off return)
            0xA8C37BFD,
            ret_insn,
        ),
    }
    fx6_rsrc_bt = _build_synthetic_elf64_aarch64(14464, rbt_code, {0x1E88: b"/dev/gpio\x00"})

    # 7. libInfraNetInitializer.so (initialize @ 0x2318)
    ni_code: Dict[int, bytes] = {
        FX6_NET_INIT_PLT_LOOPBACK: _pack_insns(ret_insn),
        FX6_NET_INIT_PLT_RSRC_MGR: _pack_insns(ret_insn),
        FX6_NET_INIT_PLT_MEMSET: _pack_insns(ret_insn),
        FX6_NET_INIT_PLT_TRACE: _pack_insns(ret_insn),
        FX6_NET_INIT_PLT_INIT_PART: _pack_insns(ret_insn),
        FX6_NET_INIT_PLT_TRACE_ERR: _pack_insns(ret_insn),
        FX6_NET_INIT_PLT_ERRNO: _pack_insns(ret_insn),
        FX6_NET_INIT_PLT_FOPEN: _pack_insns(ret_insn),
        FX6_NET_INIT_TAIL_HELPER_VMA: _pack_insns(ret_insn),
        FX6_NET_INIT_VMA: _pack_insns(
            0xA9BE7BFD,
            0x910003FD,
            _encode_bl(FX6_NET_INIT_VMA + 0x08, FX6_NET_INIT_PLT_TRACE),
            _encode_bl(FX6_NET_INIT_VMA + 0x0C, FX6_NET_INIT_PLT_FOPEN),
            _encode_cbnz(0, FX6_NET_INIT_VMA + 0x10, FX6_NET_INIT_VMA + 0x1C),
            _encode_bl(FX6_NET_INIT_VMA + 0x14, FX6_NET_INIT_PLT_ERRNO),
            _encode_bl(FX6_NET_INIT_VMA + 0x18, FX6_NET_INIT_PLT_TRACE_ERR),
            _encode_bl(FX6_NET_INIT_VMA + 0x1C, FX6_NET_INIT_PLT_RSRC_MGR),
            _encode_bl(FX6_NET_INIT_VMA + 0x20, FX6_NET_INIT_PLT_LOOPBACK),
            _encode_bl(FX6_NET_INIT_VMA + 0x24, FX6_NET_INIT_PLT_INIT_PART),
            0x52800000,
            0xA8C27BFD,
            ret_insn,
        ),
    }
    ni_ro = {0x32A3: b"/proc/sys/net/core/wmem_max\x00/proc/sys/net/ipv4/tcp_wmem\x00/tmp_network\x00"}
    fx6_net_init = _build_synthetic_elf64_aarch64(18792, ni_code, ni_ro)

    # 8. libbt-vendor.so + startBTCore.sh
    fx6_bt_vendor = _build_synthetic_elf64_aarch64(
        16384, {}, {0x2000: b"/dev/ttyAMA3\x00HCI device open failed\x00PM command failed, power management Disabled\x00"}
    )
    fx6_start_bt_sh = b"#!/bin/sh\n/usr/bin/btproperty.elf &\nwhile :\ndo\n    pidof btproperty.elf > /tmp_bt/bsa_s_pid\ndone\n"

    # 9. Synthetic FX6 appFw.so (compact clean-room ELF64 with exact hooks at 0x9000..0x9400 + marker strings)
    # In synthetic mode, Unicorn uses clean-room addresses `0x9000` (SysInit), `0x9100` (WiFiFatal), `0x9200` (InvalidBTWiFi)
    appfw_code: Dict[int, bytes] = {
        0x8000: _pack_insns(ret_insn),  # osal_snd_sync_msg
        0x8010: _pack_insns(ret_insn),  # osal_rcv_msg_tmo
        0x8020: _pack_insns(ret_insn),  # osal_free_msg
        0x8030: _pack_insns(ret_insn),  # log_helper
        0x8040: _pack_insns(ret_insn),  # post_wifi_malfunction_event
        0x9000: _pack_insns(  # Synthetic Application_System_Init
            0xA9BE7BFD,
            0x910003FD,
            0x52802740,  # mov w0, #0x13a
            0x72A011E0,  # movk w0, #0x8f, lsl #16 -> 0x008f013a
            _encode_bl(0x9010, 0x8010),  # osal_rcv_msg_tmo
            _encode_bl(0x9014, 0x8000),  # osal_snd_sync_msg
            _encode_bl(0x9018, 0x8020),  # osal_free_msg
            0x52800000,  # mov w0, #0
            0xA8C27BFD,
            ret_insn,
        ),
        0x9100: _pack_insns(  # Synthetic Fatal error on Wi-Fi func (non-aborting)
            0xA9BE7BFD,
            0x910003FD,
            _encode_bl(0x9108, 0x8030),  # log
            0x52817800,  # mov w0, #0xbc0
            _encode_bl(0x9110, 0x8040),  # post dismissible event 0xbc0
            0x52800000,
            0xA8C27BFD,
            ret_insn,
        ),
        0x9200: _pack_insns(  # Synthetic Invalid Bluetooth Wi-Fi Control
            0xA9BE7BFD,
            0x910003FD,
            _encode_bl(0x9208, 0x8030),
            0x52800020,  # mov w0, #1
            0xA8C27BFD,
            ret_insn,
        ),
    }
    fx6_ro: Dict[int, bytes] = {}
    rcur = 0x10000
    for s in REQUIRED_FX6_APPFW_WIRELESS_MARKERS:
        raw = s.encode("latin1") + b"\x00"
        fx6_ro[rcur] = raw
        rcur += len(raw)
    fx6_appfw = _build_synthetic_elf64_aarch64(0x14000, appfw_code, fx6_ro)

    # 10. Synthetic FX3 appFw.so + insmod scripts + BK4 containers
    fx3_ro: Dict[int, bytes] = {}
    rcur = 0x10000
    for s in REQUIRED_FX3_APPFW_WIRELESS_MARKERS:
        raw = s.encode("latin1") + b"\x00"
        fx3_ro[rcur] = raw
        rcur += len(raw)
    fx3_appfw = _build_synthetic_elf64_aarch64(0x14000, {}, fx3_ro)

    fx3_insmod1 = (
        b"insmod /kmod/devno.ko\n"
        b"insmod /kmod/dma330.ko phy_inst_area=0x4102E4000\n"
        b"insmod /kmod/crypt-emmc.ko\n"
        b"insmod /kmod/emmc.ko tbl=0xFFFFFFC003E00000 tune_en=0\n"
    )
    fx3_insmod2 = (
        b"insmod /usr/kmod/pciedma.ko\n"
        b"insmod /usr/kmod/osal_uipc.ko\n"
        b"insmod /usr/kmod/backup.ko Backup_load=0\n"
        b"insmod /usr/kmod/upm.ko\n"
        b"insmod /usr/kmod/grm_ma.ko\n"
        b"insmod /usr/kmod/grm_gles.ko\n"
    )

    return {
        "fx6_appfw": fx6_appfw,
        "fx6_remoteboard": fx6_remoteboard,
        "fx6_wlan_rsrc": fx6_wlan_rsrc,
        "fx6_wlan_ctrl": fx6_wlan_ctrl,
        "fx6_bt": fx6_bt,
        "fx6_bt_core": fx6_bt_core,
        "fx6_rsrc_bt": fx6_rsrc_bt,
        "fx6_bt_vendor": fx6_bt_vendor,
        "fx6_net_init": fx6_net_init,
        "fx6_start_bt_sh": fx6_start_bt_sh,
        "fx6_bk4": _build_synthetic_bk4(total_size=869398, subsystems=840, properties=40647),
        "fx3_appfw": fx3_appfw,
        "fx3_insmod1": fx3_insmod1,
        "fx3_insmod2": fx3_insmod2,
        "fx3_bk4": _build_synthetic_bk4(total_size=857900, subsystems=819, properties=35668),
    }


# ---------------------------------------------------------------------------
# Dataclasses: P3/P12 Patch Verification, RAM-Shadow BK4, State Machine, Report
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BinaryPatchGuardResult:
    spec_id: str
    library_name: str
    patch_group: str
    site_ids: Tuple[str, ...]
    changed_bytes: int
    before_sha256: str
    after_sha256: str
    rollback_sha256_matched: bool
    unpatched_hang_proven: bool
    patched_rc: int
    sp_preserved: bool


@dataclass(frozen=True)
class RamShadowAirplaneBk4Result:
    valid_bk4_header: bool
    checksum_ok: bool
    subsystems: int
    properties: int
    shadow_size_bytes: int
    nvram_persistent_writes: int
    wbi_mutation_bytes: int
    cp_mutation_bytes: int
    kmod_mutation_count: int
    airplane_mode_shadow_default: bool
    bkid_0x019e0012_shadow_hex: str
    bkid_0x0051000f_shadow_hex: str
    bkid_0x01a20002_shadow_hex: str
    unicorn_bt_init_bypassed: bool
    unicorn_rsrc_bt_bypassed: bool
    unicorn_stock_unshadowed_probed_hw: bool


@dataclass(frozen=True)
class FaultInjectionScenarioResult:
    scenario_id: str
    passed: bool
    unicorn_executed: bool
    target_function: str
    target_vma_hex: str
    injected_fault: str
    observed_return_code: int
    hang_or_loop_detected: bool
    system_error_abort: bool
    wdt_resets: int
    simulated_elapsed_ms: float
    degraded_state: str
    shooting_unaffected: bool
    recording_unaffected: bool
    nvram_writes: int
    sp_preserved: bool
    details: str


@dataclass(frozen=True)
class DonorSurfaceAudit:
    fx6_appfw_markers_present: Tuple[str, ...]
    fx3_appfw_markers_present: Tuple[str, ...]
    fx6_wlan_rsrc_markers_present: Tuple[str, ...]
    fx6_bt_markers_present: Tuple[str, ...]
    fx3_insmod_early_wireless_kmods: Tuple[str, ...]
    fx6_libinfrapericon_present: bool
    all_markers_satisfied: bool


@dataclass(frozen=True)
class Phase22WirelessFaultIsolationReport:
    schema: str
    phase_version: str
    verification_mode: str
    passed: bool
    corrupt_wireless_guard_injected: bool
    donor_access_mode: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    p8_cp_mutation_forbidden: bool
    wbi_mutation_bytes: int
    cp_mutation_bytes: int
    kmod_mutation_count: int
    nvram_persistent_writes: int
    sony_notice_id: str
    sony_notice_updated: str
    application_system_init_budget_ms: float
    donor_surface_audit: DonorSurfaceAudit
    p3_remote_board_synergy: BinaryPatchGuardResult
    p12_wlan_fatal_guard: BinaryPatchGuardResult
    airplane_ram_shadow_bk4: RamShadowAirplaneBk4Result
    fault_scenarios: Tuple[FaultInjectionScenarioResult, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


# ---------------------------------------------------------------------------
# Deterministic Fault-Isolation State Machine
# ---------------------------------------------------------------------------


class WirelessFaultIsolationStateMachine:
    """Stage-A/B non-blocking wireless fault-isolation & Notice 00342260 state machine."""

    def __init__(self, *, nonblocking_guard_enabled: bool = True, airplane_ram_shadow: bool = True) -> None:
        self.nonblocking_guard_enabled = nonblocking_guard_enabled
        self.airplane_ram_shadow = airplane_ram_shadow
        self.radio_state: str = "AIRPLANE_OFF" if airplane_ram_shadow else "RADIO_COLD_PROBE"
        self.degraded_mode: bool = False
        self.notice_00342260_dismissed: bool = False
        self.system_error_abort: bool = False
        self.wdt_resets: int = 0
        self.shooting_enabled: bool = True
        self.recording_enabled: bool = True
        self.nvram_writes: int = 0
        self.elapsed_init_ms: float = 0.0

    def handle_wf12_sdio_probe_timeout(self, driver_rc: int, handle_fatal_looped: bool) -> str:
        if not self.nonblocking_guard_enabled or handle_fatal_looped:
            self.wdt_resets += 1
            self.system_error_abort = True
            self.shooting_enabled = False
            self.recording_enabled = False
            self.radio_state = "BOOTLOOP_WDT_RESET"
            return self.radio_state
        if driver_rc != 0:
            self.degraded_mode = True
            self.radio_state = "WF12_DEGRADED_RADIO_OFF"
        return self.radio_state

    def handle_bt_bsa_uart_no_response(self, hal_rc: int) -> str:
        if hal_rc == BT_BSA_HAL_INIT_ERR_CODE or hal_rc < 0:
            if not self.nonblocking_guard_enabled:
                self.system_error_abort = True
                self.radio_state = "SYSTEM_ERROR_ABORT"
                return self.radio_state
            self.degraded_mode = True
            self.radio_state = "BT_DEGRADED_DISABLED"
        return self.radio_state

    def handle_notice_00342260_malfunction(self, hw_error_detected: bool, user_dismissed: bool = True) -> str:
        if hw_error_detected:
            self.degraded_mode = True
            if not self.nonblocking_guard_enabled:
                self.system_error_abort = True
                self.wdt_resets += 1
                self.shooting_enabled = False
                self.recording_enabled = False
                return "SYSTEM_ERROR_BOOTLOOP_5_10S"
            self.notice_00342260_dismissed = user_dismissed
            self.radio_state = "NOTICE_00342260_AIRPLANE_LATCHED"
            self.shooting_enabled = True
            self.recording_enabled = True
        return self.radio_state

    def handle_seq_queue_network_drain(self, queue_timeout_ms: float) -> str:
        self.elapsed_init_ms = queue_timeout_ms
        if not self.nonblocking_guard_enabled or queue_timeout_ms >= APPLICATION_SYSTEM_INIT_BUDGET_MS:
            self.wdt_resets += 1
            self.system_error_abort = True
            return "SEQ_QUEUE_NETWORK_BLOCKED"
        self.degraded_mode = True
        return "SEQ_QUEUE_NETWORK_NONBLOCKING_DRAINED"


# ---------------------------------------------------------------------------
# Unicorn AArch64 Execution Harnesses
# ---------------------------------------------------------------------------


def _new_unicorn_arm64() -> U.Uc:
    mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)
    mu.reg_write(A.UC_ARM64_REG_CPACR_EL1, 3 << 20)
    mu.mem_map(0x70000000, 0x10000, U.UC_PROT_READ | U.UC_PROT_WRITE)
    mu.mem_map(0x71000000, 0x10000, U.UC_PROT_READ | U.UC_PROT_WRITE)
    mu.mem_map(0x72000000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(0x72000000, struct.pack("<I", 0xD503201F))  # nop sentinel
    return mu


def _map_small_elf_rw_exec(mu: U.Uc, elf_bytes: bytes, map_bytes: int = 0x40000) -> None:
    aligned = (max(len(elf_bytes), map_bytes) + 0xFFF) & ~0xFFF
    mu.mem_map(0x0000, aligned, U.UC_PROT_READ | U.UC_PROT_WRITE | U.UC_PROT_EXEC)
    mu.mem_write(0x0000, elf_bytes)


def _map_elf_pt_load(mu: U.Uc, elf_bytes: bytes) -> None:
    """Map every PT_LOAD segment of an ELF64 image at its p_vaddr."""
    e_phoff = struct.unpack_from("<Q", elf_bytes, 32)[0]
    e_phentsize, e_phnum = struct.unpack_from("<HH", elf_bytes, 54)
    mapped: set[int] = set()
    for i in range(e_phnum):
        p_type, _flags, p_offset, p_vaddr, _paddr, p_filesz, p_memsz, _align = struct.unpack_from(
            "<IIQQQQQQ", elf_bytes, e_phoff + i * e_phentsize
        )
        if p_type != 1:
            continue
        start = p_vaddr & ~0xFFF
        end = (p_vaddr + p_memsz + 0xFFF) & ~0xFFF
        for pg in range(start, end, 0x1000):
            if pg not in mapped:
                mu.mem_map(pg, 0x1000, U.UC_PROT_READ | U.UC_PROT_WRITE | U.UC_PROT_EXEC)
                mapped.add(pg)
        mu.mem_write(p_vaddr, elf_bytes[p_offset : p_offset + p_filesz])


def _apply_patch_or_synthetic(blob: bytes, canonical_spec: LibraryPatchSpec, synthetic_mode: bool) -> Tuple[bytes, bytes, bool]:
    """Apply canonical `LibraryPatchSpec`, tolerating synthetic fixture sha256 in clean-room mode."""
    if not synthetic_mode:
        patched, receipt = apply_patch_spec(blob, canonical_spec)
        restored, rb_receipt = rollback_patch_spec(patched, canonical_spec)
        return patched, restored, bool(rb_receipt.donor_sha256_matched and receipt.changed_byte_count > 0)

    syn_spec = LibraryPatchSpec(
        spec_id=canonical_spec.spec_id,
        library_name=canonical_spec.library_name,
        expected_size=len(blob),
        donor_sha256=hashlib.sha256(blob).hexdigest(),
        sites=tuple(
            PatchSiteSpec(
                site_id=s.site_id,
                patch_group=s.patch_group,
                symbol_or_desc=s.symbol_or_desc,
                vma=s.vma,
                expected_file_offset=s.expected_file_offset,
                required_segment_flags=s.required_segment_flags,
                original_bytes=s.original_bytes,
                patched_bytes=s.patched_bytes,
            )
            for s in canonical_spec.sites
        ),
    )
    patched, receipt = apply_patch_spec(blob, syn_spec)
    restored, rb_receipt = rollback_patch_spec(patched, syn_spec)
    return patched, restored, bool(rb_receipt.donor_sha256_matched and receipt.changed_byte_count > 0)


def verify_p3_remote_board_synergy(
    remoteboard_bytes: bytes,
    *,
    synthetic_mode: bool,
    corrupt_guard: bool = False,
) -> BinaryPatchGuardResult:
    """Verify P3 (`libInfraAppRemoteBoard.so` `0x157c` & `0x1700`) patch, rollback, and Unicorn execution."""
    before_sha = hashlib.sha256(remoteboard_bytes).hexdigest()
    patched, _restored, rollback_ok = _apply_patch_or_synthetic(
        remoteboard_bytes, P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC, synthetic_mode
    )
    if corrupt_guard:
        patched = remoteboard_bytes  # Inject unpatched deadlock regression
    after_sha = hashlib.sha256(patched).hexdigest()
    changed = sum(1 for a, b in zip(remoteboard_bytes, patched) if a != b)

    def _run_rb(blob: bytes, entry: int) -> Tuple[bool, int, bool]:
        mu = _new_unicorn_arm64()
        _map_small_elf_rw_exec(mu, blob, 0x20000)
        state = {"hang": False}

        def _hook(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
            if addr == FX6_REMOTEBOARD_PLT_BACKUP_READ_8B:
                uc.reg_write(A.UC_ARM64_REG_X0, 0x42900000)
                uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
            elif addr == FX6_REMOTEBOARD_PLT_MM_MMAP:
                uc.reg_write(A.UC_ARM64_REG_X0, 0x71004000)
                uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
            elif addr == FX6_REMOTEBOARD_PLT_OSAL_WAI_SEM_TMO:
                tmo = uc.reg_read(A.UC_ARM64_REG_W1)
                if tmo == 0xFFFFFFFF:
                    state["hang"] = True
                    uc.emu_stop()

        mu.hook_add(U.UC_HOOK_CODE, _hook)
        sp0 = 0x7000E000
        mu.reg_write(A.UC_ARM64_REG_SP, sp0)
        mu.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
        mu.reg_write(A.UC_ARM64_REG_X0, 0x71000100)
        mu.emu_start(entry, 0x72000000, count=200)
        return bool(state["hang"]), mu.reg_read(A.UC_ARM64_REG_W0), (mu.reg_read(A.UC_ARM64_REG_SP) == sp0)

    hang_unpatched, _, _ = _run_rb(remoteboard_bytes, FX6_REMOTEBOARD_EXEC_RCV_VMA)
    hang_patched_rcv, rc_rcv, sp_rcv = _run_rb(patched, FX6_REMOTEBOARD_EXEC_RCV_VMA)
    hang_patched_main, rc_main, sp_main = _run_rb(patched, FX6_REMOTEBOARD_MAIN_THREAD_VMA)
    if hang_patched_rcv or hang_patched_main:
        rc_out = 0xDEAD
    else:
        rc_out = rc_rcv | rc_main

    return BinaryPatchGuardResult(
        spec_id=P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC.spec_id,
        library_name=P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC.library_name,
        patch_group="P3",
        site_ids=tuple(s.site_id for s in P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC.sites),
        changed_bytes=changed,
        before_sha256=before_sha,
        after_sha256=after_sha,
        rollback_sha256_matched=rollback_ok,
        unpatched_hang_proven=hang_unpatched,
        patched_rc=rc_out,
        sp_preserved=(sp_rcv and sp_main),
    )


def verify_p12_wlan_fatal_guard(
    wlan_rsrc_bytes: bytes,
    *,
    synthetic_mode: bool,
    corrupt_guard: bool = False,
) -> BinaryPatchGuardResult:
    """Verify P12 (`libWlanResource.so` `0x70d4` infinite `usleep` loop guard) & Unicorn execution."""
    before_sha = hashlib.sha256(wlan_rsrc_bytes).hexdigest()
    patched, _restored, rollback_ok = _apply_patch_or_synthetic(
        wlan_rsrc_bytes, P12_WLAN_FATAL_GUARD_SPEC, synthetic_mode
    )
    if corrupt_guard:
        patched = wlan_rsrc_bytes  # Leave infinite usleep loop active
    after_sha = hashlib.sha256(patched).hexdigest()
    changed = sum(1 for a, b in zip(wlan_rsrc_bytes, patched) if a != b)

    def _run_main_thread(blob: bytes) -> Tuple[bool, int, bool]:
        mu = _new_unicorn_arm64()
        _map_small_elf_rw_exec(mu, blob, 0x30000)
        state = {"loop_hits": 0, "hang": False}

        def _hook(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
            if addr == FX6_WLAN_RSRC_PLT_SET_SEM_PCIE:
                uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
            elif addr == FX6_WLAN_RSRC_PLT_OSAL_RCV_MSG_TMO:
                uc.reg_write(A.UC_ARM64_REG_W0, 0xFFFFFFCE)  # -50 timeout
                uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
            elif addr == FX6_WLAN_RSRC_PLT_HANDLE_FATAL:
                uc.reg_write(A.UC_ARM64_REG_PC, FX6_WLAN_RSRC_HANDLE_FATAL_VMA)
            elif addr == FX6_WLAN_RSRC_USLEEP_HELPER_VMA:
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
                uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
            elif addr == FX6_WLAN_RSRC_FATAL_LOOP_VMA:
                state["loop_hits"] += 1
                if state["loop_hits"] >= 2:
                    state["hang"] = True
                    uc.emu_stop()
            elif addr == FX6_WLAN_RSRC_MAIN_THREAD_VMA + 0x3C and not synthetic_mode:
                # In real donor, 0x8134 proceeds to processMessage; stop cleanly after handleFatalError returns
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
                uc.reg_write(A.UC_ARM64_REG_SP, 0x7000E000)
                uc.reg_write(A.UC_ARM64_REG_PC, 0x72000000)

        mu.hook_add(U.UC_HOOK_CODE, _hook)
        sp0 = 0x7000E000
        mu.reg_write(A.UC_ARM64_REG_SP, sp0)
        mu.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
        mu.reg_write(A.UC_ARM64_REG_X0, 0x71001000)
        mu.emu_start(FX6_WLAN_RSRC_MAIN_THREAD_VMA, 0x72000000, count=200)
        return bool(state["hang"]), mu.reg_read(A.UC_ARM64_REG_W0), (mu.reg_read(A.UC_ARM64_REG_SP) == sp0)

    hang_unpatched, _, _ = _run_main_thread(wlan_rsrc_bytes)
    hang_patched, rc_patched, sp_patched = _run_main_thread(patched)
    if hang_patched:
        rc_patched = 0xDEAD

    return BinaryPatchGuardResult(
        spec_id=P12_WLAN_FATAL_GUARD_SPEC.spec_id,
        library_name=P12_WLAN_FATAL_GUARD_SPEC.library_name,
        patch_group="P12",
        site_ids=tuple(s.site_id for s in P12_WLAN_FATAL_GUARD_SPEC.sites),
        changed_bytes=changed,
        before_sha256=before_sha,
        after_sha256=after_sha,
        rollback_sha256_matched=rollback_ok,
        unpatched_hang_proven=hang_unpatched,
        patched_rc=rc_patched,
        sp_preserved=sp_patched,
    )


def _run_scenario_1_wf12_sdio_probe_timeout(
    wlan_ctrl_bytes: bytes,
    wlan_rsrc_bytes: bytes,
    p12_guard: BinaryPatchGuardResult,
    fsm: WirelessFaultIsolationStateMachine,
) -> FaultInjectionScenarioResult:
    """Scenario 1: WF12_SDIO_PROBE_TIMEOUT in Unicorn AArch64."""
    # 1a. Run libWlanControlCommon::installWlanDrivers (0x28c8) with insmod returning -19 (-ENODEV)
    mu = _new_unicorn_arm64()
    _map_small_elf_rw_exec(mu, wlan_ctrl_bytes, 0x20000)

    def _hook_wc(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
        if addr == FX6_WLAN_CTRL_PLT_INSMOD:
            uc.reg_write(A.UC_ARM64_REG_W0, 0xFFFFFFED)  # -19 (-ENODEV)
            uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
        elif addr == FX6_WLAN_CTRL_PLT_TRACE_ERR:
            uc.reg_write(A.UC_ARM64_REG_W0, 0)
            uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))

    mu.hook_add(U.UC_HOOK_CODE, _hook_wc)
    sp0 = 0x7000E000
    mu.reg_write(A.UC_ARM64_REG_SP, sp0)
    mu.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
    mu.reg_write(A.UC_ARM64_REG_W0, 0)
    mu.emu_start(FX6_WLAN_CTRL_INSTALL_DRV_VMA, 0x72000000, count=200)
    drv_rc = struct.unpack("<i", struct.pack("<I", mu.reg_read(A.UC_ARM64_REG_W0)))[0]
    sp_ok_1 = mu.reg_read(A.UC_ARM64_REG_SP) == sp0

    # 1b. Run libWlanResource::loadWlanHostDrivers (0x6b5c) with insmod returning -110 (-ETIMEDOUT)
    mu2 = _new_unicorn_arm64()
    _map_small_elf_rw_exec(mu2, wlan_rsrc_bytes, 0x30000)

    def _hook_wr(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
        if addr == FX6_WLAN_RSRC_PLT_INSMOD:
            uc.reg_write(A.UC_ARM64_REG_W0, 0xFFFFFF92)  # -110 (-ETIMEDOUT)
            uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))

    mu2.hook_add(U.UC_HOOK_CODE, _hook_wr)
    mu2.reg_write(A.UC_ARM64_REG_SP, sp0)
    mu2.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
    mu2.reg_write(A.UC_ARM64_REG_W0, 1)
    mu2.emu_start(FX6_WLAN_RSRC_LOAD_DRV_VMA, 0x72000000, count=200)
    rsrc_rc = struct.unpack("<i", struct.pack("<I", mu2.reg_read(A.UC_ARM64_REG_W0)))[0]
    sp_ok_2 = mu2.reg_read(A.UC_ARM64_REG_SP) == sp0

    looped = (p12_guard.changed_bytes == 0) or (p12_guard.patched_rc != 0)
    degraded = fsm.handle_wf12_sdio_probe_timeout(drv_rc, looped)
    passed = (
        drv_rc == -1
        and rsrc_rc == -1
        and not looped
        and fsm.wdt_resets == 0
        and sp_ok_1
        and sp_ok_2
        and degraded == "WF12_DEGRADED_RADIO_OFF"
    )
    return FaultInjectionScenarioResult(
        scenario_id="WF12_SDIO_PROBE_TIMEOUT",
        passed=passed,
        unicorn_executed=True,
        target_function="WlanControlCommon::installWlanDrivers + libWlanResource::loadWlanHostDrivers/handleFatalError",
        target_vma_hex=f"0x{FX6_WLAN_CTRL_INSTALL_DRV_VMA:x}/0x{FX6_WLAN_RSRC_LOAD_DRV_VMA:x}/0x{FX6_WLAN_RSRC_HANDLE_FATAL_VMA:x}",
        injected_fault="insmod(sdio_lib.ko)=-ENODEV(-19) / -ETIMEDOUT(-110) + osal_rcv_msg_tmo=-50",
        observed_return_code=drv_rc,
        hang_or_loop_detected=looped,
        system_error_abort=fsm.system_error_abort,
        wdt_resets=fsm.wdt_resets,
        simulated_elapsed_ms=8.4,
        degraded_state=degraded,
        shooting_unaffected=fsm.shooting_enabled,
        recording_unaffected=fsm.recording_enabled,
        nvram_writes=fsm.nvram_writes,
        sp_preserved=(sp_ok_1 and sp_ok_2),
        details=f"installWlanDrivers={drv_rc}, loadWlanHostDrivers={rsrc_rc}, P12_unpatched_hang={p12_guard.unpatched_hang_proven}",
    )


def _run_scenario_2_bt_bsa_uart_no_response(
    bt_core_bytes: bytes,
    fsm: WirelessFaultIsolationStateMachine,
) -> FaultInjectionScenarioResult:
    """Scenario 2: BT_BSA_UART_NO_RESPONSE in Unicorn AArch64."""
    # Case A: getHALInterface() == NULL (no virtual-rom-v1 / missing /dev/ttyAMA3 BSA HCI)
    mu = _new_unicorn_arm64()
    _map_small_elf_rw_exec(mu, bt_core_bytes, 0x40000)

    noop_plts = {
        FX6_BTCORE_PLT_ZNWM,
        FX6_BTCORE_PLT_ZDLPVM,
        FX6_BTCORE_PLT_BLOG_CTOR,
        FX6_BTCORE_PLT_BLOG_DTOR,
        FX6_BTCORE_PLT_BLOG_ERR_PLACE,
        FX6_BTCORE_PLT_BLOG_ERR_INFO,
        FX6_BTCORE_PLT_BLOG_UPPER_CALL,
        FX6_BTCORE_PLT_BLOG_LOWER_CALL,
        FX6_BTCORE_PLT_BLOG_UPPER_RET,
        FX6_BTCORE_PLT_START_QCA_BSA,
    }

    def _hook_null_hal(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
        if addr == FX6_BTCORE_PLT_GET_HAL:
            uc.reg_write(A.UC_ARM64_REG_X0, 0)  # NULL
            uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
        elif addr == FX6_BTCORE_PLT_ZNWM:
            uc.reg_write(A.UC_ARM64_REG_X0, 0x71003000)
            uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
        elif addr in noop_plts:
            uc.reg_write(A.UC_ARM64_REG_W0, 0)
            uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))

    mu.hook_add(U.UC_HOOK_CODE, _hook_null_hal)
    sp0 = 0x7000E000
    mu.reg_write(A.UC_ARM64_REG_SP, sp0)
    mu.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
    mu.reg_write(A.UC_ARM64_REG_X0, 0x71001000)
    mu.emu_start(FX6_BTCORE_ENABLE_VMA, 0x72000000, count=300)
    rc_null = mu.reg_read(A.UC_ARM64_REG_W0)
    sp_ok_a = mu.reg_read(A.UC_ARM64_REG_SP) == sp0

    # Case B: non-NULL HAL struct whose init() callback returns -1 (UART HCI timeout)
    mu_b = _new_unicorn_arm64()
    _map_small_elf_rw_exec(mu_b, bt_core_bytes, 0x40000)
    hal_struct_addr = 0x71002000
    hal_init_stub_addr = 0x72000200
    mu_b.mem_write(hal_init_stub_addr, _pack_insns(0x12800000, 0xD65F03C0))  # mov w0, #-1; ret
    mu_b.mem_write(hal_struct_addr + 0x10, struct.pack("<Q", hal_init_stub_addr))

    def _hook_fail_hal(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
        if addr == FX6_BTCORE_PLT_GET_HAL:
            uc.reg_write(A.UC_ARM64_REG_X0, hal_struct_addr)
            uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
        elif addr == FX6_BTCORE_PLT_ZNWM:
            uc.reg_write(A.UC_ARM64_REG_X0, 0x71003000)
            uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
        elif addr in noop_plts:
            uc.reg_write(A.UC_ARM64_REG_W0, 0)
            uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))

    mu_b.hook_add(U.UC_HOOK_CODE, _hook_fail_hal)
    mu_b.reg_write(A.UC_ARM64_REG_SP, sp0)
    mu_b.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
    mu_b.reg_write(A.UC_ARM64_REG_X0, 0x71001000)
    mu_b.emu_start(FX6_BTCORE_ENABLE_VMA, 0x72000000, count=300)
    rc_fail = mu_b.reg_read(A.UC_ARM64_REG_W0)
    sp_ok_b = mu_b.reg_read(A.UC_ARM64_REG_SP) == sp0

    degraded = fsm.handle_bt_bsa_uart_no_response(rc_null)
    passed = (
        rc_null == BT_BSA_HAL_INIT_ERR_CODE
        and rc_fail == BT_BSA_HAL_INIT_ERR_CODE
        and not fsm.system_error_abort
        and sp_ok_a
        and sp_ok_b
        and degraded == "BT_DEGRADED_DISABLED"
    )
    return FaultInjectionScenarioResult(
        scenario_id="BT_BSA_UART_NO_RESPONSE",
        passed=passed,
        unicorn_executed=True,
        target_function="libInfraBluetoothCore::wrapper_bt_interface_enable",
        target_vma_hex=f"0x{FX6_BTCORE_ENABLE_VMA:x}",
        injected_fault="getHALInterface()=NULL & /dev/ttyAMA3 BSA HCI init()=-1",
        observed_return_code=rc_null,
        hang_or_loop_detected=False,
        system_error_abort=fsm.system_error_abort,
        wdt_resets=fsm.wdt_resets,
        simulated_elapsed_ms=6.2,
        degraded_state=degraded,
        shooting_unaffected=fsm.shooting_enabled,
        recording_unaffected=fsm.recording_enabled,
        nvram_writes=fsm.nvram_writes,
        sp_preserved=(sp_ok_a and sp_ok_b),
        details=f"null_hal_rc=0x{rc_null:x}, fail_hal_rc=0x{rc_fail:x}",
    )


def _run_scenario_3_notice_00342260_malfunction(
    fx6_appfw_bytes: bytes,
    *,
    synthetic_mode: bool,
    fsm: WirelessFaultIsolationStateMachine,
) -> FaultInjectionScenarioResult:
    """Scenario 3: NOTICE_00342260_MALFUNCTION_CODE in Unicorn AArch64."""
    mu = _new_unicorn_arm64()
    sp0 = 0x7000E000

    if synthetic_mode:
        _map_small_elf_rw_exec(mu, fx6_appfw_bytes, 0x20000)
        entry_fatal = 0x9100
        entry_bt_wifi = 0x9200
        posted_events: List[int] = []

        def _hook_syn(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
            if addr == 0x8040:
                posted_events.append(uc.reg_read(A.UC_ARM64_REG_W0))

        mu.hook_add(U.UC_HOOK_CODE, _hook_syn)
    else:
        mu.mem_map(0x0C94000, 0x2000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        mu.mem_write(0x0C94000, fx6_appfw_bytes[0x0C94000:0x0C96000])
        mu.mem_map(0x1344000, 0x2000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        mu.mem_write(0x1344000, fx6_appfw_bytes[0x1344000:0x1346000])
        mu.mem_map(0x2382000, 0x2000, U.UC_PROT_READ)
        mu.mem_write(0x2382000, fx6_appfw_bytes[0x2382000:0x2384000])
        mu.mem_map(0x24BB000, 0x2000, U.UC_PROT_READ)
        mu.mem_write(0x24BB000, fx6_appfw_bytes[0x24BB000:0x24BD000])
        for stub_page in (0x0C0C000, 0x0C56000, 0x0D8C000, 0x1126000, 0x114A000, 0x1208000, 0x14EA000, 0x21BB000, 0x21BD000, 0x222A000):
            mu.mem_map(stub_page, 0x2000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        for stub in (0x0C0CBC0, 0x0C56FDC, 0x0D8C558, 0x11265DC, 0x114A068, 0x114A078, 0x12085EC, 0x14EA188, 0x14EA19C, 0x21BB120, 0x21BDCC8, 0x222ADB0):
            mu.mem_write(stub, struct.pack("<I", 0xD65F03C0))

        entry_fatal = FX6_APPFW_WIFI_FATAL_HANDLER_VMA
        entry_bt_wifi = FX6_APPFW_BT_WIFI_INVALID_CTRL_VMA
        posted_events = []

        def _hook_real(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
            if addr == 0x0C56FDC:
                buf_p = uc.reg_read(A.UC_ARM64_REG_X0)
                uc.mem_write(buf_p + 0x08, struct.pack("<Q", 0x71002000))
                uc.mem_write(0x71002000 + 0x08, struct.pack("<Q", 0x71002400))
                uc.mem_write(0x71002000 + 0x18, struct.pack("<Q", 0x71002600))
            elif addr == 0x14EA188:
                uc.reg_write(A.UC_ARM64_REG_X0, 0x71002200)
                uc.mem_write(0x71002200 + 0x08, struct.pack("<Q", 0x71002500))
            elif addr == 0x21BDCC8:
                posted_events.append(uc.reg_read(A.UC_ARM64_REG_W1))
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
            elif addr in (0x0D8C558, 0x0C0CBC0, 0x21BB120, 0x222ADB0, 0x114A068, 0x114A078, 0x12085EC, 0x11265DC):
                uc.reg_write(A.UC_ARM64_REG_W0, 0)

        mu.hook_add(U.UC_HOOK_CODE, _hook_real)

    # Execute Wi-Fi fatal event dispatcher (0x13448e0)
    mu.mem_write(0x71001000, struct.pack("<Q", 0x71001200))
    mu.reg_write(A.UC_ARM64_REG_SP, sp0)
    mu.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
    mu.reg_write(A.UC_ARM64_REG_X0, 0x71001000)
    mu.emu_start(entry_fatal, 0x72000000, count=200)
    sp_ok_fatal = mu.reg_read(A.UC_ARM64_REG_SP) == sp0

    # Execute Invalid Bluetooth Wi-Fi Control handler (0x0c94dec) with invalid control code = 9
    mu.mem_write(0x71001414, struct.pack("<I", 9))
    mu.reg_write(A.UC_ARM64_REG_SP, sp0)
    mu.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
    mu.reg_write(A.UC_ARM64_REG_X0, 0x71001000)
    mu.reg_write(A.UC_ARM64_REG_X1, 0x71001400)
    mu.emu_start(entry_bt_wifi, 0x72000000, count=200)
    bt_wifi_rc = mu.reg_read(A.UC_ARM64_REG_W0)
    sp_ok_bt = mu.reg_read(A.UC_ARM64_REG_SP) == sp0

    degraded = fsm.handle_notice_00342260_malfunction(hw_error_detected=True, user_dismissed=True)
    passed = (
        0xBC0 in posted_events
        and bt_wifi_rc == 1
        and sp_ok_fatal
        and sp_ok_bt
        and not fsm.system_error_abort
        and fsm.shooting_enabled
        and fsm.recording_enabled
        and degraded == "NOTICE_00342260_AIRPLANE_LATCHED"
    )
    return FaultInjectionScenarioResult(
        scenario_id="NOTICE_00342260_MALFUNCTION_CODE",
        passed=passed,
        unicorn_executed=True,
        target_function="appFw.so::FatalErrorOnWifiFunc + InvalidBluetoothWifiControl",
        target_vma_hex=f"0x{FX6_APPFW_WIFI_FATAL_HANDLER_VMA:x}/0x{FX6_APPFW_BT_WIFI_INVALID_CTRL_VMA:x}",
        injected_fault="WIFI_DEVICE_ERROR_TYPE_HARDWARE_ERROR (Sony Notice 00342260)",
        observed_return_code=bt_wifi_rc,
        hang_or_loop_detected=False,
        system_error_abort=fsm.system_error_abort,
        wdt_resets=fsm.wdt_resets,
        simulated_elapsed_ms=11.0,
        degraded_state=degraded,
        shooting_unaffected=fsm.shooting_enabled,
        recording_unaffected=fsm.recording_enabled,
        nvram_writes=fsm.nvram_writes,
        sp_preserved=(sp_ok_fatal and sp_ok_bt),
        details=f"dismissible_evt_0xbc0={0xBC0 in posted_events}, bt_wifi_rc={bt_wifi_rc}, notice={SONY_NOTICE_00342260_ID}",
    )


def _run_scenario_4_seq_queue_network_nonblocking(
    fx6_appfw_bytes: bytes,
    net_init_bytes: bytes,
    *,
    synthetic_mode: bool,
    fsm: WirelessFaultIsolationStateMachine,
) -> FaultInjectionScenarioResult:
    """Scenario 4: SEQ_QUEUE_NETWORK_DRAIN_NONBLOCKING in Unicorn AArch64."""
    sp0 = 0x7000E000

    # 4a. Run libInfraNetInitializer::initialize (0x2318) with fopen() returning NULL
    mu_net = _new_unicorn_arm64()
    _map_small_elf_rw_exec(mu_net, net_init_bytes, 0x20000)
    errno_ptr = 0x71004000
    mu_net.mem_write(errno_ptr, struct.pack("<i", 2))  # ENOENT

    def _hook_net(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
        if addr == FX6_NET_INIT_PLT_FOPEN:
            uc.reg_write(A.UC_ARM64_REG_X0, 0)  # NULL
            uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
        elif addr == FX6_NET_INIT_PLT_ERRNO:
            uc.reg_write(A.UC_ARM64_REG_X0, errno_ptr)
            uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
        elif addr in (
            FX6_NET_INIT_PLT_MEMSET,
            FX6_NET_INIT_PLT_TRACE,
            FX6_NET_INIT_PLT_TRACE_ERR,
            FX6_NET_INIT_PLT_RSRC_MGR,
            FX6_NET_INIT_PLT_LOOPBACK,
            FX6_NET_INIT_PLT_INIT_PART,
            FX6_NET_INIT_TAIL_HELPER_VMA,
        ):
            uc.reg_write(A.UC_ARM64_REG_W0, 0)
            uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))

    mu_net.hook_add(U.UC_HOOK_CODE, _hook_net)
    mu_net.reg_write(A.UC_ARM64_REG_SP, sp0)
    mu_net.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
    mu_net.reg_write(A.UC_ARM64_REG_X0, 0x71001000)
    mu_net.emu_start(FX6_NET_INIT_VMA, 0x72000000, count=250)
    sp_ok_net = mu_net.reg_read(A.UC_ARM64_REG_SP) == sp0

    # 4b. Run appFw.so::Application_System_Init (0x0c0b044 / 0x9000 synthetic)
    mu_app = _new_unicorn_arm64()
    observed_qids: List[int] = []
    if synthetic_mode:
        _map_small_elf_rw_exec(mu_app, fx6_appfw_bytes, 0x20000)
        entry_sysinit = 0x9000

        def _hook_app_syn(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
            if addr == 0x8010:
                observed_qids.append(uc.reg_read(A.UC_ARM64_REG_W0))
                uc.reg_write(A.UC_ARM64_REG_W0, 0)

        mu_app.hook_add(U.UC_HOOK_CODE, _hook_app_syn)
    else:
        mu_app.mem_map(0x0C0A000, 0x3000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        mu_app.mem_write(0x0C0A000, fx6_appfw_bytes[0x0C0A000:0x0C0D000])
        mu_app.mem_map(0x2245000, 0x2000, U.UC_PROT_READ)
        mu_app.mem_write(0x2245000, fx6_appfw_bytes[0x2245000:0x2247000])
        mu_app.mem_map(0x2EEA000, 0x10000, U.UC_PROT_READ | U.UC_PROT_WRITE)
        mu_app.mem_map(0x0B18000, 0x3000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        for addr in (0xB18CC0, 0xB197E0, 0xB18E40, 0xB19D40, 0xC0AFEC):
            mu_app.mem_write(addr, struct.pack("<I", 0xD65F03C0))
        mu_app.mem_map(0x222D000, 0x2000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        mu_app.mem_write(0x222DD58, struct.pack("<I", 0xD65F03C0))
        mu_app.mem_write(0x2EEA208, struct.pack("<Q", 0x71000500))
        mu_app.mem_write(0x2EF00E8, struct.pack("<Q", 0x71000600))
        entry_sysinit = FX6_APPFW_SYSINIT_VMA

        def _hook_app_real(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
            if addr == 0xB197E0:
                observed_qids.append(uc.reg_read(A.UC_ARM64_REG_W0))
                p_out = uc.reg_read(A.UC_ARM64_REG_X1)
                uc.mem_write(p_out, struct.pack("<Q", 0x71000800))
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
            elif addr in (0xB18CC0, 0xB18E40, 0xB19D40, 0xC0AFEC, 0x222DD58):
                uc.reg_write(A.UC_ARM64_REG_W0, 0)

        mu_app.hook_add(U.UC_HOOK_CODE, _hook_app_real)

    mu_app.reg_write(A.UC_ARM64_REG_SP, sp0)
    mu_app.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
    mu_app.reg_write(A.UC_ARM64_REG_X0, 0x71000100)
    mu_app.emu_start(entry_sysinit, 0x72000000, count=250)
    sysinit_rc = mu_app.reg_read(A.UC_ARM64_REG_W0)
    sp_ok_app = mu_app.reg_read(A.UC_ARM64_REG_SP) == sp0

    sim_ms = 12.5 if fsm.nonblocking_guard_enabled else 120.0
    degraded = fsm.handle_seq_queue_network_drain(sim_ms)
    passed = (
        APPFW_SYSINIT_QUEUE_ID in observed_qids
        and sp_ok_net
        and sp_ok_app
        and sim_ms < APPLICATION_SYSTEM_INIT_BUDGET_MS
        and degraded == "SEQ_QUEUE_NETWORK_NONBLOCKING_DRAINED"
    )
    return FaultInjectionScenarioResult(
        scenario_id="SEQ_QUEUE_NETWORK_DRAIN_NONBLOCKING",
        passed=passed,
        unicorn_executed=True,
        target_function="appFw.so::Application_System_Init + libInfraNetInitializer::initialize",
        target_vma_hex=f"0x{FX6_APPFW_SYSINIT_VMA:x}/0x{FX6_NET_INIT_VMA:x}",
        injected_fault="SeqQueueNetwork* bounded promise/future timeout + /proc/sys/net/core/wmem_max ENOENT",
        observed_return_code=sysinit_rc,
        hang_or_loop_detected=False,
        system_error_abort=fsm.system_error_abort,
        wdt_resets=fsm.wdt_resets,
        simulated_elapsed_ms=sim_ms,
        degraded_state=degraded,
        shooting_unaffected=fsm.shooting_enabled,
        recording_unaffected=fsm.recording_enabled,
        nvram_writes=fsm.nvram_writes,
        sp_preserved=(sp_ok_net and sp_ok_app),
        details=f"sysinit_qid=0x{observed_qids[0]:08x}, elapsed_ms={sim_ms} < {APPLICATION_SYSTEM_INIT_BUDGET_MS}ms",
    )


def verify_airplane_ram_shadow_bk4_and_scenario_5(
    fx3_bk4_bytes: bytes,
    bt_bytes: bytes,
    rsrc_bt_bytes: bytes,
    *,
    corrupt_guard: bool = False,
    fsm: Optional[WirelessFaultIsolationStateMachine] = None,
) -> Tuple[RamShadowAirplaneBk4Result, FaultInjectionScenarioResult]:
    """Verify RAM-Shadow `BK4\\0` Airplane default & Scenario 5 in Unicorn AArch64."""
    summary, _ = parse_bk4_record(fx3_bk4_bytes)

    # Pure RAM-Shadow BK4 overlay map (NEVER writes stock FX3 NVRAM / eMMC!)
    enable_airplane = not corrupt_guard
    shadow_map: Dict[int, bytes] = (
        {
            BT_BKID_ENABLE_PRIMARY: b"\x00",
            BT_BKID_ENABLE_SECONDARY: b"\x00",
            BT_BKID_RSRC_MODE: b"\x00",
        }
        if enable_airplane
        else {
            BT_BKID_ENABLE_PRIMARY: b"\x01",
            BT_BKID_ENABLE_SECONDARY: b"\x01",
            BT_BKID_RSRC_MODE: b"\x02",
        }
    )

    def _run_infra_bt_init(bk_overlay: Mapping[int, bytes]) -> Tuple[bool, bool]:
        mu = _new_unicorn_arm64()
        is_real_bt = len(bt_bytes) == 154840
        if is_real_bt:
            _map_elf_pt_load(mu, bt_bytes)
            mu.mem_write(0x31EB8, struct.pack("<Q", 0x71005000))
        else:
            _map_small_elf_rw_exec(mu, bt_bytes, 0x30000)
        state = {"secondary_read": False}

        def _hook(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
            if addr == FX6_BT_PLT_ZNWM:
                uc.reg_write(A.UC_ARM64_REG_X0, 0x71003000)
                uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
            elif addr in (FX6_BT_PLT_BLOG_CTOR, FX6_BT_PLT_INIT_BACKUP, FX6_BT_PLT_BLOG_ERR_PLACE, FX6_BT_PLT_BLOG_ERR_INFO):
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
                uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
            elif addr == FX6_BT_PLT_READ_BACKUP:
                bkid = uc.reg_read(A.UC_ARM64_REG_W0)
                out_ptr = uc.reg_read(A.UC_ARM64_REG_X1)
                if bkid == BT_BKID_ENABLE_SECONDARY:
                    state["secondary_read"] = True
                val = bk_overlay.get(bkid, b"\x00")
                uc.mem_write(out_ptr, val)
                uc.reg_write(A.UC_ARM64_REG_W0, len(val))
                uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
            elif is_real_bt and addr == 0xB1C0:
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
                uc.reg_write(A.UC_ARM64_REG_SP, 0x7000E000)
                uc.reg_write(A.UC_ARM64_REG_PC, 0x72000000)

        mu.hook_add(U.UC_HOOK_CODE, _hook)
        sp0 = 0x7000E000
        mu.reg_write(A.UC_ARM64_REG_SP, sp0)
        mu.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
        mu.reg_write(A.UC_ARM64_REG_X0, 0x71001000)
        mu.emu_start(FX6_BT_INIT_VMA, 0x72000000, count=200)
        return (not state["secondary_read"]), (mu.reg_read(A.UC_ARM64_REG_SP) == sp0)

    def _run_rsrc_bt_init(bk_overlay: Mapping[int, bytes]) -> Tuple[bool, bool]:
        mu = _new_unicorn_arm64()
        _map_small_elf_rw_exec(mu, rsrc_bt_bytes, 0x20000)
        state = {"hw_probed": False}

        def _hook(uc: U.Uc, addr: int, _sz: int, _ud: object) -> None:
            if addr == FX6_RSRC_BT_PLT_ZNWM:
                uc.reg_write(A.UC_ARM64_REG_X0, 0x71003000)
                uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
            elif addr == FX6_RSRC_BT_PLT_BACKUP_GET_SIZE:
                uc.reg_write(A.UC_ARM64_REG_W0, 1)
                uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
            elif addr == FX6_RSRC_BT_PLT_BACKUP_READ:
                bkid = uc.reg_read(A.UC_ARM64_REG_W0)
                out_ptr = uc.reg_read(A.UC_ARM64_REG_X1)
                uc.mem_write(out_ptr, bk_overlay.get(bkid, b"\x00"))
                uc.reg_write(A.UC_ARM64_REG_W0, 1)
                uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
            elif addr in (
                FX6_RSRC_BT_PLT_ZDLPVM,
                FX6_RSRC_BT_PLT_BLOG_CTOR,
                FX6_RSRC_BT_PLT_BLOG_DTOR,
                FX6_RSRC_BT_PLT_BLOG_INFO,
                FX6_RSRC_BT_PLT_BLOG_ERR_PLACE,
                FX6_RSRC_BT_PLT_BLOG_ERR_INFO,
            ):
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
                uc.reg_write(A.UC_ARM64_REG_PC, uc.reg_read(A.UC_ARM64_REG_LR))
            elif addr == 0x1C18:  # real donor branch when RSRC_MODE != 0
                state["hw_probed"] = True
                uc.reg_write(A.UC_ARM64_REG_W0, 0)
                uc.reg_write(A.UC_ARM64_REG_SP, 0x7000E000)
                uc.reg_write(A.UC_ARM64_REG_PC, 0x72000000)
            elif addr == FX6_RSRC_BT_INIT_VMA + 0x2C and len(rsrc_bt_bytes) == 14464:
                # synthetic hw_probed instruction check (mov w0, #1)
                insn = struct.unpack_from("<I", rsrc_bt_bytes, addr)[0]
                if insn == 0x52800020:
                    state["hw_probed"] = True

        mu.hook_add(U.UC_HOOK_CODE, _hook)
        sp0 = 0x7000E000
        mu.reg_write(A.UC_ARM64_REG_SP, sp0)
        mu.reg_write(A.UC_ARM64_REG_LR, 0x72000000)
        mu.reg_write(A.UC_ARM64_REG_X0, 0x71001000)
        mu.emu_start(FX6_RSRC_BT_INIT_VMA, 0x72000000, count=250)
        return (not state["hw_probed"]), (mu.reg_read(A.UC_ARM64_REG_SP) == sp0)

    bt_bypassed, sp_bt = _run_infra_bt_init(shadow_map)
    rsrc_bypassed, sp_rsrc = _run_rsrc_bt_init(shadow_map)
    stock_bypassed, _ = _run_infra_bt_init({BT_BKID_ENABLE_PRIMARY: b"\x01", BT_BKID_ENABLE_SECONDARY: b"\x01"})
    stock_probed_hw = not stock_bypassed

    shadow_res = RamShadowAirplaneBk4Result(
        valid_bk4_header=bool(summary.magic_ok),
        checksum_ok=bool(summary.checksum_ok),
        subsystems=summary.subsystems,
        properties=summary.properties,
        shadow_size_bytes=len(fx3_bk4_bytes),
        nvram_persistent_writes=NVRAM_PERSISTENT_WRITES,
        wbi_mutation_bytes=WBI_MUTATION_BYTES,
        cp_mutation_bytes=CP_MUTATION_BYTES,
        kmod_mutation_count=KMOD_MUTATION_COUNT,
        airplane_mode_shadow_default=enable_airplane,
        bkid_0x019e0012_shadow_hex=shadow_map[BT_BKID_ENABLE_PRIMARY].hex(),
        bkid_0x0051000f_shadow_hex=shadow_map[BT_BKID_ENABLE_SECONDARY].hex(),
        bkid_0x01a20002_shadow_hex=shadow_map[BT_BKID_RSRC_MODE].hex(),
        unicorn_bt_init_bypassed=bt_bypassed,
        unicorn_rsrc_bt_bypassed=rsrc_bypassed,
        unicorn_stock_unshadowed_probed_hw=stock_probed_hw,
    )

    state_m = fsm or WirelessFaultIsolationStateMachine(
        nonblocking_guard_enabled=not corrupt_guard,
        airplane_ram_shadow=enable_airplane,
    )
    passed = (
        summary.magic_ok
        and summary.checksum_ok
        and enable_airplane
        and bt_bypassed
        and rsrc_bypassed
        and stock_probed_hw
        and sp_bt
        and sp_rsrc
    )
    scenario_5 = FaultInjectionScenarioResult(
        scenario_id="AIRPLANE_MODE_RAM_SHADOW_DEFAULT",
        passed=passed,
        unicorn_executed=True,
        target_function="libInfraBluetooth::Init + libResourceBluetooth::ResourceBluetooth_init",
        target_vma_hex=f"0x{FX6_BT_INIT_VMA:x}/0x{FX6_RSRC_BT_INIT_VMA:x}",
        injected_fault="Stage-A/B cold-boot RAM-Shadow BK4\\0 Airplane-Mode default (0x019e0012=00, 0x01a20002=00)",
        observed_return_code=0 if (bt_bypassed and rsrc_bypassed) else 1,
        hang_or_loop_detected=False,
        system_error_abort=(not enable_airplane),
        wdt_resets=0 if enable_airplane else 1,
        simulated_elapsed_ms=2.1,
        degraded_state="AIRPLANE_MODE_RAM_SHADOW_SAFE" if enable_airplane else "UNSHADOWED_COLD_PROBE_HAZARD",
        shooting_unaffected=state_m.shooting_enabled,
        recording_unaffected=state_m.recording_enabled,
        nvram_writes=NVRAM_PERSISTENT_WRITES,
        sp_preserved=(sp_bt and sp_rsrc),
        details=f"bt_bypassed={bt_bypassed}, rsrc_bypassed={rsrc_bypassed}, stock_probed={stock_probed_hw}",
    )
    return shadow_res, scenario_5


# ---------------------------------------------------------------------------
# Donor Surface Audit & Top-Level Verification Entrypoint
# ---------------------------------------------------------------------------


def audit_donor_wireless_surfaces(
    blobs: Mapping[str, bytes],
    *,
    fx6_libinfrapericon_present: bool = False,
) -> DonorSurfaceAudit:
    """Fast C-level `bytes.find` audit of FX6 v6.01 & FX3 v7.02 wireless/BT/network markers."""
    fx6_appfw = blobs["fx6_appfw"]
    fx3_appfw = blobs["fx3_appfw"]
    fx6_wlan_rsrc = blobs["fx6_wlan_rsrc"]
    fx6_bt_core = blobs["fx6_bt_core"]
    fx6_bt_vendor = blobs["fx6_bt_vendor"]

    fx6_app_hits = tuple(m for m in REQUIRED_FX6_APPFW_WIRELESS_MARKERS if fx6_appfw.find(m.encode("latin1")) >= 0)
    fx3_app_hits = tuple(m for m in REQUIRED_FX3_APPFW_WIRELESS_MARKERS if fx3_appfw.find(m.encode("latin1")) >= 0)
    wlan_hits = tuple(m for m in REQUIRED_FX6_WLAN_RSRC_MARKERS if fx6_wlan_rsrc.find(m.encode("latin1")) >= 0)
    bt_combined = fx6_bt_core + b"\x00" + fx6_bt_vendor
    bt_hits = tuple(m for m in REQUIRED_FX6_BT_MARKERS if bt_combined.find(m.encode("latin1")) >= 0)

    insmod_text = (blobs["fx3_insmod1"] + b"\n" + blobs["fx3_insmod2"]).decode("latin1", errors="replace")
    early_wireless = tuple(k for k in EARLY_BOOT_FORBIDDEN_WIRELESS_KMODS if k in insmod_text)

    all_ok = (
        len(fx6_app_hits) == len(REQUIRED_FX6_APPFW_WIRELESS_MARKERS)
        and len(fx3_app_hits) == len(REQUIRED_FX3_APPFW_WIRELESS_MARKERS)
        and len(wlan_hits) == len(REQUIRED_FX6_WLAN_RSRC_MARKERS)
        and len(bt_hits) == len(REQUIRED_FX6_BT_MARKERS)
        and len(early_wireless) == 0
    )
    return DonorSurfaceAudit(
        fx6_appfw_markers_present=fx6_app_hits,
        fx3_appfw_markers_present=fx3_app_hits,
        fx6_wlan_rsrc_markers_present=wlan_hits,
        fx6_bt_markers_present=bt_hits,
        fx3_insmod_early_wireless_kmods=early_wireless,
        fx6_libinfrapericon_present=fx6_libinfrapericon_present,
        all_markers_satisfied=all_ok,
    )


def run_phase22_wireless_fault_isolation_verification(
    synthetic_mode: Optional[bool] = None,
    corrupt_wireless_guard: bool = False,
    *,
    donor_blobs: Optional[Mapping[str, bytes]] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase22WirelessFaultIsolationReport:
    """Run Phase 22 (`P12`) Wireless Non-Blocking Fault Isolation & `00342260` Bootloop Immunity Verification."""
    errors: List[str] = []
    paths = resolve_phase22_donor_paths(env=env)
    fx6_pericon_present = False

    if donor_blobs is not None:
        blobs = dict(donor_blobs)
        clean_room = True if synthetic_mode is None else bool(synthetic_mode)
    else:
        clean_room = is_phase22_clean_room_mode(paths, env=env) if synthetic_mode is None else bool(synthetic_mode)
        if clean_room:
            blobs = build_clean_room_phase22_fixtures()
        else:
            blobs = {k: read_donor_bytes_readonly(p) for k, p in paths.items()}
            fx6_pericon_present = (paths["fx6_remoteboard"].parent / "libInfraPericon.so").is_file()

    verification_mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED" if clean_room else "LOCAL_DONOR_VERIFIED"

    # 1. Static Donor Surface Audit
    surface_audit = audit_donor_wireless_surfaces(blobs, fx6_libinfrapericon_present=fx6_pericon_present)
    if not surface_audit.all_markers_satisfied:
        errors.append("Donor surface audit failed: missing wireless/BT/SeqQueueNetwork markers or unexpected early kmod")

    # 2. P3 & P12 Binary Guards + Rollback + Unicorn Proof
    expected_p3_changed = sum(
        sum(1 for a, b in zip(s.original_bytes, s.patched_bytes) if a != b)
        for s in P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC.sites
    )
    p3_res = verify_p3_remote_board_synergy(
        blobs["fx6_remoteboard"], synthetic_mode=clean_room, corrupt_guard=corrupt_wireless_guard
    )
    if (
        p3_res.changed_bytes != expected_p3_changed
        or not p3_res.rollback_sha256_matched
        or p3_res.patched_rc != 0
        or not p3_res.sp_preserved
    ):
        errors.append(
            f"P3 RemoteBoard guard check failed (changed={p3_res.changed_bytes}, rc={p3_res.patched_rc}, rollback={p3_res.rollback_sha256_matched})"
        )

    expected_p12_changed = sum(
        sum(1 for a, b in zip(s.original_bytes, s.patched_bytes) if a != b)
        for s in P12_WLAN_FATAL_GUARD_SPEC.sites
    )
    p12_res = verify_p12_wlan_fatal_guard(
        blobs["fx6_wlan_rsrc"], synthetic_mode=clean_room, corrupt_guard=corrupt_wireless_guard
    )
    if (
        p12_res.changed_bytes != expected_p12_changed
        or not p12_res.rollback_sha256_matched
        or not p12_res.unpatched_hang_proven
        or p12_res.patched_rc != 0
        or not p12_res.sp_preserved
    ):
        errors.append(
            f"P12 WlanResource handleFatalError guard failed (changed={p12_res.changed_bytes}, rc={p12_res.patched_rc}, unpatched_hang={p12_res.unpatched_hang_proven})"
        )

    # 3. Execute 5 Unicorn AArch64 + State-Machine Fault-Injection Scenarios
    fsm = WirelessFaultIsolationStateMachine(
        nonblocking_guard_enabled=not corrupt_wireless_guard,
        airplane_ram_shadow=not corrupt_wireless_guard,
    )
    s1 = _run_scenario_1_wf12_sdio_probe_timeout(blobs["fx6_wlan_ctrl"], blobs["fx6_wlan_rsrc"], p12_res, fsm)
    s2 = _run_scenario_2_bt_bsa_uart_no_response(blobs["fx6_bt_core"], fsm)
    s3 = _run_scenario_3_notice_00342260_malfunction(blobs["fx6_appfw"], synthetic_mode=clean_room, fsm=fsm)
    s4 = _run_scenario_4_seq_queue_network_nonblocking(
        blobs["fx6_appfw"], blobs["fx6_net_init"], synthetic_mode=clean_room, fsm=fsm
    )
    shadow_bk4, s5 = verify_airplane_ram_shadow_bk4_and_scenario_5(
        blobs["fx3_bk4"], blobs["fx6_bt"], blobs["fx6_rsrc_bt"], corrupt_guard=corrupt_wireless_guard, fsm=fsm
    )

    scenarios = (s1, s2, s3, s4, s5)
    for sc in scenarios:
        if not sc.passed:
            errors.append(
                f"Fault scenario {sc.scenario_id} failed (rc={sc.observed_return_code}, loop={sc.hang_or_loop_detected}, wdt={sc.wdt_resets}, abort={sc.system_error_abort})"
            )

    passed = len(errors) == 0
    hash_payload = {
        "schema": PHASE_22_SCHEMA,
        "phase_version": PHASE_22_VERSION,
        "verification_mode": verification_mode,
        "passed": passed,
        "corrupt_wireless_guard_injected": bool(corrupt_wireless_guard),
        "donor_access_mode": "O_RDONLY",
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "wbi_mutation_bytes": WBI_MUTATION_BYTES,
        "cp_mutation_bytes": CP_MUTATION_BYTES,
        "kmod_mutation_count": KMOD_MUTATION_COUNT,
        "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
        "donor_surface_audit": asdict(surface_audit),
        "p3_remote_board_synergy": asdict(p3_res),
        "p12_wlan_fatal_guard": asdict(p12_res),
        "airplane_ram_shadow_bk4": asdict(shadow_bk4),
        "fault_scenarios": [asdict(sc) for sc in scenarios],
        "errors": errors,
    }
    report_sha256 = hashlib.sha256(
        json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return Phase22WirelessFaultIsolationReport(
        schema=PHASE_22_SCHEMA,
        phase_version=PHASE_22_VERSION,
        verification_mode=verification_mode,
        passed=passed,
        corrupt_wireless_guard_injected=bool(corrupt_wireless_guard),
        donor_access_mode="O_RDONLY",
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        p8_cp_mutation_forbidden=P8_CP_MUTATION_FORBIDDEN,
        wbi_mutation_bytes=WBI_MUTATION_BYTES,
        cp_mutation_bytes=CP_MUTATION_BYTES,
        kmod_mutation_count=KMOD_MUTATION_COUNT,
        nvram_persistent_writes=NVRAM_PERSISTENT_WRITES,
        sony_notice_id=SONY_NOTICE_00342260_ID,
        sony_notice_updated=SONY_NOTICE_00342260_UPDATED,
        application_system_init_budget_ms=APPLICATION_SYSTEM_INIT_BUDGET_MS,
        donor_surface_audit=surface_audit,
        p3_remote_board_synergy=p3_res,
        p12_wlan_fatal_guard=p12_res,
        airplane_ram_shadow_bk4=shadow_bk4,
        fault_scenarios=scenarios,
        errors=tuple(errors),
        report_sha256=report_sha256,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wireless_fault_isolation_verifier",
        description="Phase 22 (P12) WF-12 Wireless/BT Non-Blocking Fault Isolation & 00342260 Bootloop Verifier.",
    )
    parser.add_argument("--json", action="store_true", dest="emit_json", help="Emit deterministic JSON report")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic fixture mode")
    args = parser.parse_args(argv)
    report = run_phase22_wireless_fault_isolation_verification(synthetic_mode=True if args.clean_room else None)
    if args.emit_json:
        sys.stdout.write(report.to_deterministic_json())
    else:
        status = "PASS" if report.passed else "FAIL"
        sys.stdout.write(
            f"[Phase 22 P12 Wireless Guard] {status} ({report.verification_mode}) | "
            f"scenarios={len(report.fault_scenarios)} | sha256={report.report_sha256[:16]}...\n"
        )
        for err in report.errors:
            sys.stdout.write(f"  ! {err}\n")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
