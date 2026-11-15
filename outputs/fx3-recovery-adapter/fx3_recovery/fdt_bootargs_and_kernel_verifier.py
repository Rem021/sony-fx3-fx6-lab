"""Phase 106 — CXD90057 Flattened Device-Tree (FDT 0xd00dfeed) /chosen/bootargs Read-Only Rootfs
& Init-Path Firewall, Kernel Image ARM64 Magic/Header Verifier, & 10-Pillar Recovery Master Suite.

Provides three deterministic, RAM-only, read-only-donor verification pillars for
Sony `ILME-FX3` (`0x91030080` / `ALCIN_UUD`) Stage-B recovery gating:

1. **Pillar 1 — Pure-Python Flattened Device Tree (`FDT 0xd00dfeed` v17) Binary Parser & `/chosen/bootargs` Firewall**:
   - Implements a dependency-free IEEE 1275 / Devicetree v17 binary blob parser & in-memory
     synthesizer (40-byte big-endian `fdt_header`, `FDT_BEGIN_NODE=1`, `FDT_END_NODE=2`,
     `FDT_PROP=3`, `FDT_NOP=4`, `FDT_END=9`, 8-byte aligned `mem_rsvmap` `(0, 0)`-terminated,
     strict `off_dt_struct` / `off_dt_strings` / padding bounds checks).
   - Audits `/chosen/bootargs` and `/chosen/linux,initrd-start..end`:
     - Fails closed if `rw` is passed for `/dev/mmcblk0p*` / `/dev/nflasha*` eMMC rootfs
       (requires `ro` and `rootwait`),
     - Fails closed if `init=` (or `rdinit=`) points outside verified `/sbin/init`, `/init`,
       or the Stage-B volatile RAM wrapper,
     - Fails closed if `mtdparts=` / `blkdevparts=` attempts to repartition internal eMMC or
       if `nowatchdog` (or WDT disable flags) disables the `CXD90057` hardware watchdog.

2. **Pillar 2 — ARM64 Linux Kernel `Image` Header (`0x644d5241` `'ARM\\x64'` @ `0x38`) & Cross-SKU Kernel Firewall**:
   - Parses the 64-byte ARM64 Linux `Image` header (`code0`, `code1`, `text_offset`,
     `image_size`, `flags` LE/4K-pages, `magic == 0x644d5241`).
   - Proves Stage-B boots strictly FX3's authentic `4.9.337-scel+` kernel for `CXD90057`
     and rejects cross-SKU FX6 kernel transplants, mismatched kernel releases, bad flags,
     or truncated images fail-closed.

3. **Pillar 3 — 10-Pillar Recovery Master Suite Readiness Gate (`run_fdt_bootargs_and_kernel_suite`)**:
   - Supports dual-mode execution (`LOCAL_DONOR_O_RDONLY` via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`
     and `CLEAN_ROOM_SYNTHETIC` when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor absent).
   - Hard-locks `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`, `PERSISTENT_WRITE_RELEASE = False`,
     `OTP_FUSE_TOUCHES = 0`, `PASSIVE_TX_BYTES_EMITTED = 0`, `PHYSICAL_DEVICE_WRITES = 0`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shlex
import stat
import struct
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .files import is_forced_clean_room, read_file, require, resolve_donor_path


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

FDT_BOOTARGS_KERNEL_SCHEMA: str = "fx3-fdt-bootargs-and-kernel-verifier-v1"
FDT_BOOTARGS_KERNEL_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True
OTP_FUSE_TOUCHES: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0

STATUS_VERIFIED_FDT_KERNEL_GATE: str = "VERIFIED_FDT_BOOTARGS_AND_KERNEL_GATE"
STATUS_FAIL_FDT_KERNEL_GATE: str = "FAIL_FDT_BOOTARGS_AND_KERNEL_GATE"
STATUS_VERIFIED_FDT_BLOB: str = "VERIFIED_FDT_BLOB"
STATUS_REJECTED_FDT_BLOB: str = "REJECTED_FDT_BLOB"
STATUS_VERIFIED_BOOTARGS_FIREWALL: str = "VERIFIED_BOOTARGS_FIREWALL"
STATUS_REJECTED_BOOTARGS_FIREWALL: str = "REJECTED_BOOTARGS_FIREWALL"
STATUS_VERIFIED_ARM64_KERNEL: str = "VERIFIED_ARM64_KERNEL"
STATUS_REJECTED_ARM64_KERNEL: str = "REJECTED_ARM64_KERNEL"

# Local Donor Relative Paths (strictly read-only via os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
DONOR_FX3_SETTING_DTB_RELPATH: str = (
    "sony-firmware-20261024/stage205-FX3-hardware-profile-differences/originals/7.02-setting-cxd90057.dtb"
)
DONOR_FX3_BOOT_DTB_RELPATH: str = (
    "fx3-color-port-20261027/input-20261028/fat-members/"
    "87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca-cxd90057.dtb"
)
DONOR_FX6_SETTING_DTB_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0800_appli/setting/cxd90057.dtb"
)
DONOR_FX3_VMLINUX_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/current-updater-evidence/p3-main/vmlinux.bin"
)
DONOR_FX6_VMLINUX_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha3/vmlinux.bin"
)
DONOR_FX3_KEMCO_RELPATH: str = (
    "fx3-color-port-20261027/input-20261028/fat-members/"
    "eb184157afc8eaf2d9a3dc795e7b52057130cb25f7799bc72fd6c85cbb99c94a-kemco.txt"
)
DONOR_FX6_KEMCO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha1/boot/kemco.txt"
)

# Pinned Hardware / Donor Anchors (Zero Proprietary Keys)
CXD90057_SOC_MODEL: str = "CXD90057"
CXD90057_COMPATIBLE: str = "cxd,cxd90057"
CXD90057_DRAM_BASE: int = 0x400000000
CXD90057_DRAM_SIZE: int = 0x200000000
CXD90057_INITRD_BASE: int = 0x408000000
FX3_KEMCO_INITRD_SIZE: int = 0x2000000  # 32 MiB
FX6_KEMCO_INITRD_SIZE: int = 0x1000000  # 16 MiB
PINNED_FX3_VMLINUX_SHA256: str = "da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c"
PINNED_FX6_VMLINUX_SHA256: str = "bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9"
PINNED_CXD90057_SETTING_DTB_SHA256: str = "c5735ad9c6da8c48fb24eeee0bb743d07c486a47d5db19bef13b5eaea24ad280"
PINNED_CXD90057_BOOT_DTB_SHA256: str = "87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca"

# ---------------------------------------------------------------------------
# Pillar 1 Constants — IEEE 1275 / Devicetree v17 FDT & /chosen/bootargs
# ---------------------------------------------------------------------------

FDT_MAGIC: int = 0xD00DFEED
FDT_MAGIC_U32: int = FDT_MAGIC
FDT_HEADER_SIZE: int = 40
FDT_VERSION_17: int = 17
FDT_MIN_COMP_VERSION: int = 16
FDT_MAX_BLOB_BYTES: int = 8 * 1024 * 1024

FDT_BEGIN_NODE: int = 0x00000001
FDT_END_NODE: int = 0x00000002
FDT_PROP: int = 0x00000003
FDT_NOP: int = 0x00000004
FDT_END: int = 0x00000009

ALLOWED_VERIFIED_INIT_PATHS: Tuple[str, ...] = (
    "/sbin/init",
    "/init",
    "/sbin/init2",
    "/sbin/init2_stage_b",
    "/tmp/stage_b/sbin/init2_stage_b",
    "/tmp/stage_b/init",
)
EMMC_ROOT_DEVICE_PREFIXES: Tuple[str, ...] = (
    "/dev/mmcblk",
    "/dev/nflasha",
    "/dev/cnflasha",
)
FORBIDDEN_REPARTITION_KEYS: Tuple[str, ...] = (
    "mtdparts",
    "blkdevparts",
    "mmcparts",
)
FORBIDDEN_WDT_DISABLE_TOKENS: Tuple[str, ...] = (
    "nowatchdog",
    "wdt=0",
    "watchdog=0",
    "cxd90057_wdt.disable=1",
    "wdt.disable=1",
    "softlockup_panic=0",
)
MAX_INITRD_WINDOW_BYTES: int = 128 * 1024 * 1024  # 128 MiB sanity ceiling

DEFAULT_SAFE_STAGE_B_BOOTARGS: str = (
    "console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait "
    "init=/tmp/stage_b/sbin/init2_stage_b wdt.timeout=500 mem=2G"
)

# FDT Parser Error Codes
ERR_FDT_EMPTY_OR_TRUNCATED_HEADER: str = "FDT_EMPTY_OR_TRUNCATED_HEADER"
ERR_FDT_BAD_MAGIC: str = "FDT_BAD_0XD00DFEED_MAGIC"
ERR_FDT_BAD_TOTALSIZE: str = "FDT_BAD_TOTALSIZE_OR_TRUNCATED"
ERR_FDT_UNSUPPORTED_VERSION: str = "FDT_UNSUPPORTED_VERSION_LT_17"
ERR_FDT_BAD_BOUNDS: str = "FDT_REGION_BOUNDS_OR_ALIGNMENT_INVALID"
ERR_FDT_OVERLAPPING_REGIONS: str = "FDT_OVERLAPPING_STRUCT_OR_STRINGS"
ERR_FDT_BAD_MEM_RSVMAP: str = "FDT_BAD_MEM_RSVMAP_TERMINATION"
ERR_FDT_MALFORMED_TOKENS: str = "FDT_MALFORMED_TOKEN_STREAM"
ERR_FDT_BAD_STRING_OFFSET: str = "FDT_OUT_OF_BOUNDS_STRING_OFFSET"
ERR_FDT_MISSING_END_TOKEN: str = "FDT_MISSING_END_TOKEN"
ERR_FDT_UNCLOSED_NODE: str = "FDT_UNCLOSED_NODE_BEFORE_END"
ERR_FDT_UNKNOWN_TOKEN: str = "FDT_UNKNOWN_OR_UNALIGNED_TOKEN"
ERR_FDT_NONZERO_PADDING: str = "FDT_NONZERO_ALIGNMENT_PADDING"
ERR_FDT_SOC_MISMATCH: str = "FDT_CXD90057_SOC_MISMATCH"
ERR_FDT_MISSING_CHOSEN: str = "FDT_MISSING_CHOSEN_NODE"

# /chosen/bootargs & initrd Firewall Error Codes
ERR_BOOTARGS_MISSING_OR_EMPTY: str = "BOOTARGS_MISSING_OR_EMPTY"
ERR_BOOTARGS_MALFORMED: str = "BOOTARGS_MALFORMED_OR_NON_NUL"
ERR_BOOTARGS_RW_EMMC_ROOTFS: str = "BOOTARGS_RW_EMMC_ROOTFS_FORBIDDEN"
ERR_BOOTARGS_MISSING_RO: str = "BOOTARGS_EMMC_ROOTFS_MISSING_RO"
ERR_BOOTARGS_MISSING_ROOTWAIT: str = "BOOTARGS_EMMC_ROOTFS_MISSING_ROOTWAIT"
ERR_BOOTARGS_UNVERIFIED_INIT_PATH: str = "BOOTARGS_UNVERIFIED_INIT_PATH_REJECTED"
ERR_BOOTARGS_FORBIDDEN_REPARTITIONING: str = "BOOTARGS_FORBIDDEN_EMMC_REPARTITIONING"
ERR_BOOTARGS_WDT_DISABLED: str = "BOOTARGS_WDT_DISABLED_NOWATCHDOG_FORBIDDEN"
ERR_INITRD_MISSING: str = "CHOSEN_INITRD_BOUNDS_MISSING"
ERR_INITRD_ASYMMETRIC_BOUNDS: str = "CHOSEN_INITRD_ASYMMETRIC_START_END"
ERR_INITRD_INVALID_CELL_SIZE: str = "CHOSEN_INITRD_INVALID_CELL_SIZE"
ERR_INITRD_INVALID_RANGE: str = "CHOSEN_INITRD_INVALID_RANGE"
ERR_INITRD_SIZE_OUT_OF_BOUNDS: str = "CHOSEN_INITRD_SIZE_OUT_OF_BOUNDS"

# ---------------------------------------------------------------------------
# Pillar 2 Constants — ARM64 Linux Kernel Image Header & Cross-SKU Firewall
# ---------------------------------------------------------------------------

ARM64_IMAGE_HEADER_SIZE: int = 64
ARM64_IMAGE_MAGIC: int = 0x644D5241  # 'ARM\x64' little-endian at offset 0x38
ARM64_IMAGE_MAGIC_U32: int = ARM64_IMAGE_MAGIC
ARM64_FLAG_ENDIAN_MASK: int = 0x1
ARM64_FLAG_PAGE_SIZE_SHIFT: int = 1
ARM64_FLAG_PAGE_SIZE_MASK: int = 0x3
ARM64_FLAG_PHYS_PLACEMENT_BIT: int = 0x8
ARM64_PAGE_SIZE_MAP: Dict[int, str] = {
    0: "UNSPECIFIED",
    1: "4K",
    2: "16K",
    3: "64K",
}
EXPECTED_ARM64_TEXT_OFFSET: int = 0x80000
EXPECTED_ARM64_IMAGE_SIZE: int = 0x6AF000
EXPECTED_FX3_KERNEL_RELEASE: str = "4.9.337-scel+"
FX3_KERNEL_MIN_FILE_BYTES: int = 4 * 1024 * 1024  # Real FX3 Image is 6,610,952 bytes

FX3_KERNEL_BUILD_HOST: str = "dic-build-scm-u20-028"
FX3_KERNEL_TOOLCHAIN_MARKER: str = "Sony CE Linux 14.0.1.0"
FX6_KERNEL_BUILD_HOST: str = "dic-build-scm-u24-002"
FX6_KERNEL_TOOLCHAIN_MARKER: str = "Sony CE Linux 14.0.2.0"

ERR_KERNEL_TRUNCATED_HEADER: str = "KERNEL_TRUNCATED_ARM64_IMAGE_HEADER"
ERR_KERNEL_BAD_ARM64_MAGIC: str = "KERNEL_BAD_ARM64_MAGIC_NOT_0X644D5241"
ERR_KERNEL_INVALID_CODE0: str = "KERNEL_INVALID_ZERO_OR_NONBRANCH_CODE0"
ERR_KERNEL_BIG_ENDIAN_FORBIDDEN: str = "KERNEL_BIG_ENDIAN_FLAG_FORBIDDEN"
ERR_KERNEL_UNSUPPORTED_PAGE_SIZE: str = "KERNEL_UNSUPPORTED_PAGE_SIZE_NOT_4K"
ERR_KERNEL_NONZERO_RESERVED_FLAGS: str = "KERNEL_NONZERO_RESERVED_FLAGS"
ERR_KERNEL_INVALID_TEXT_OFFSET: str = "KERNEL_INVALID_TEXT_OFFSET_NOT_0X80000"
ERR_KERNEL_ZERO_IMAGE_SIZE: str = "KERNEL_ZERO_IMAGE_SIZE"
ERR_KERNEL_TRUNCATED_IMAGE: str = "KERNEL_TRUNCATED_IMAGE_PAYLOAD"
ERR_KERNEL_RELEASE_MISMATCH: str = "KERNEL_RELEASE_NOT_4_9_337_SCEL_PLUS"
ERR_KERNEL_SOC_MISMATCH: str = "KERNEL_CXD90057_SOC_MARKER_MISSING"
ERR_KERNEL_CROSS_SKU_FX6_TRANSPLANT: str = "KERNEL_CROSS_SKU_FX6_TRANSPLANT_REJECTED"
ERR_KERNEL_SHA256_MISMATCH: str = "KERNEL_FX3_PINNED_SHA256_MISMATCH"


# ---------------------------------------------------------------------------
# Structured Dataclasses (Zero raw bytes fields emitted in repr/to_dict)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FdtHeaderInfo:
    magic: int
    magic_hex: str
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
class FdtReserveEntryInfo:
    address: int
    address_hex: str
    size: int
    size_hex: str


@dataclass(frozen=True)
class FdtPropertyInfo:
    name: str
    value_len: int
    value_sha256: str
    value_hex_prefix: str
    text_preview: Optional[str] = None
    u32_be: Optional[int] = None
    u64_be: Optional[int] = None


@dataclass(frozen=True)
class FdtNodeInfo:
    path: str
    unit_name: str
    properties: Tuple[FdtPropertyInfo, ...]


@dataclass(frozen=True)
class FdtParseReport:
    valid: bool
    status: str
    blob_bytes: int
    blob_sha256: str
    header: Optional[FdtHeaderInfo]
    mem_rsvmap: Tuple[FdtReserveEntryInfo, ...]
    node_count: int
    property_count: int
    root_model: str
    root_compatible: Tuple[str, ...]
    has_chosen: bool
    chosen_stdout_path: Optional[str]
    chosen_bootargs: Optional[str]
    chosen_initrd_start: Optional[int]
    chosen_initrd_end: Optional[int]
    nodes: Tuple[FdtNodeInfo, ...]
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FdtBootargsAuditReport:
    passed: bool
    status: str
    fdt_valid: bool
    fdt_sha256: str
    root_model: str
    root_compatible: Tuple[str, ...]
    bootargs_raw: str
    bootargs_tokens: Tuple[str, ...]
    root_device: Optional[str]
    rootfs_is_emmc_block: bool
    has_ro: bool
    has_rw: bool
    has_rootwait: bool
    init_path: Optional[str]
    rdinit_path: Optional[str]
    init_path_verified: bool
    has_forbidden_repartitioning: bool
    repartitioning_tokens: Tuple[str, ...]
    watchdog_enabled: bool
    wdt_disable_tokens: Tuple[str, ...]
    initrd_present: bool
    initrd_start: Optional[int]
    initrd_end: Optional[int]
    initrd_size_bytes: Optional[int]
    initrd_valid: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_device_writes: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Arm64KernelImageReport:
    passed: bool
    status: str
    label: str
    file_bytes: int
    image_sha256: str
    magic: int
    magic_hex: str
    code0: int
    code0_hex: str
    code1: int
    text_offset: int
    text_offset_hex: str
    image_size: int
    image_size_hex: str
    flags: int
    flags_hex: str
    is_little_endian: bool
    page_size_code: int
    page_size_label: str
    phys_placement_2mb_aligned: bool
    reserved_flags_zero: bool
    kernel_release: str
    kernel_banner: str
    build_host: str
    toolchain_marker: str
    cxd90057_marker_present: bool
    detected_sku: str
    cross_sku_transplant_detected: bool
    truncated_image: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_device_writes: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DonorFdtKernelArtifactInfo:
    label: str
    source_mode: str
    byte_length: int
    sha256: str
    valid: bool
    details: Dict[str, Any]


@dataclass(frozen=True)
class DonorFdtKernelSnapshot:
    verification_mode: str
    read_only_access: bool
    artifacts: Tuple[DonorFdtKernelArtifactInfo, ...]
    fx3_setting_dtb_ok: bool
    fx3_boot_dtb_ok: bool
    fx6_setting_dtb_ok: bool
    fx3_kernel_ok: bool
    fx6_kernel_detected_as_fx6: bool
    fx3_kemco_ok: bool
    fx6_kemco_ok: bool
    snapshot_sha256: str


@dataclass(frozen=True)
class FdtBootargsAndKernelSuiteReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    donor_snapshot: DonorFdtKernelSnapshot
    stage_b_fdt_parse_report: FdtParseReport
    stage_b_bootargs_valid_report: FdtBootargsAuditReport
    bootargs_reject_rw_emmc_passed: bool
    bootargs_reject_bad_init_passed: bool
    bootargs_reject_mtdparts_passed: bool
    bootargs_reject_blkdevparts_passed: bool
    bootargs_reject_nowatchdog_passed: bool
    fdt_reject_bad_magic_passed: bool
    fdt_reject_truncated_passed: bool
    fx3_kernel_valid_report: Arm64KernelImageReport
    kernel_reject_fx6_transplant_passed: bool
    kernel_reject_bad_magic_passed: bool
    kernel_reject_truncated_passed: bool
    kernel_reject_wrong_release_passed: bool
    stage_b_boot_gate_ready: bool
    suite_sha256: str
    otp_fuse_touches: int
    passive_tx_bytes_emitted: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    elapsed_seconds: float
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _canonical_sha256(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def _align4(n: int) -> int:
    return (n + 3) & ~3


def _align8(n: int) -> int:
    return (n + 7) & ~7


def _decode_strlist(raw: bytes) -> Tuple[str, ...]:
    if not raw:
        return ()
    parts = raw.split(b"\x00")
    if parts and parts[-1] == b"":
        parts = parts[:-1]
    return tuple(p.decode("utf-8", errors="replace") for p in parts if p)


# ---------------------------------------------------------------------------
# Pillar 1A — Pure-Python FDT (0xd00dfeed v17) Synthesizer & Binary Parser
# ---------------------------------------------------------------------------


def build_synthetic_fdt_blob(
    *,
    model: str = CXD90057_SOC_MODEL,
    compatible: Sequence[str] = (CXD90057_COMPATIBLE,),
    bootargs: Optional[str] = DEFAULT_SAFE_STAGE_B_BOOTARGS,
    stdout_path: Optional[str] = "serial0:460800n8",
    initrd_start: Optional[int] = CXD90057_INITRD_BASE,
    initrd_end: Optional[int] = CXD90057_INITRD_BASE + FX3_KEMCO_INITRD_SIZE,
    initrd_cell_bytes: int = 8,
    include_chosen: bool = True,
    mem_rsvmap: Sequence[Tuple[int, int]] = (),
    boot_cpuid_phys: int = 0,
    version: int = FDT_VERSION_17,
    last_comp_version: int = FDT_MIN_COMP_VERSION,
    include_memory_node: bool = True,
    include_nop_token: bool = False,
) -> bytes:
    """Synthesize a valid IEEE 1275 / Devicetree v17 binary FDT blob strictly in memory."""
    if initrd_cell_bytes not in (4, 8):
        raise ValueError("initrd_cell_bytes must be 4 or 8")

    string_offsets: Dict[str, int] = {}
    strings_buf = bytearray()

    def _intern_prop_name(name: str) -> int:
        if name in string_offsets:
            return string_offsets[name]
        off = len(strings_buf)
        strings_buf.extend(name.encode("ascii") + b"\x00")
        string_offsets[name] = off
        return off

    struct_buf = bytearray()

    def _emit_u32(val: int) -> None:
        struct_buf.extend(struct.pack(">I", val & 0xFFFFFFFF))

    def _begin_node(name: str) -> None:
        _emit_u32(FDT_BEGIN_NODE)
        raw_name = name.encode("ascii") + b"\x00"
        struct_buf.extend(raw_name)
        pad = _align4(len(raw_name)) - len(raw_name)
        if pad:
            struct_buf.extend(b"\x00" * pad)

    def _end_node() -> None:
        _emit_u32(FDT_END_NODE)

    def _emit_prop(name: str, value: bytes) -> None:
        nameoff = _intern_prop_name(name)
        _emit_u32(FDT_PROP)
        _emit_u32(len(value))
        _emit_u32(nameoff)
        struct_buf.extend(value)
        pad = _align4(len(value)) - len(value)
        if pad:
            struct_buf.extend(b"\x00" * pad)

    def _pack_strlist(items: Sequence[str]) -> bytes:
        return b"".join(s.encode("utf-8") + b"\x00" for s in items)

    _begin_node("")
    _emit_prop("compatible", _pack_strlist(compatible))
    _emit_prop("#address-cells", struct.pack(">I", 2))
    _emit_prop("#size-cells", struct.pack(">I", 2))
    _emit_prop("model", model.encode("utf-8") + b"\x00")

    if include_nop_token:
        _emit_u32(FDT_NOP)

    if include_memory_node:
        _begin_node("memory@400000000")
        _emit_prop("device_type", b"memory\x00")
        _emit_prop("reg", struct.pack(">QQ", CXD90057_DRAM_BASE, CXD90057_DRAM_SIZE))
        _end_node()

    if include_chosen:
        _begin_node("chosen")
        if stdout_path is not None:
            _emit_prop("stdout-path", stdout_path.encode("utf-8") + b"\x00")
        if bootargs is not None:
            _emit_prop("bootargs", bootargs.encode("utf-8") + b"\x00")
        fmt = ">I" if initrd_cell_bytes == 4 else ">Q"
        if initrd_start is not None:
            _emit_prop("linux,initrd-start", struct.pack(fmt, initrd_start))
        if initrd_end is not None:
            _emit_prop("linux,initrd-end", struct.pack(fmt, initrd_end))
        _end_node()

    _end_node()
    _emit_u32(FDT_END)

    rsv_buf = bytearray()
    for addr, sz in mem_rsvmap:
        rsv_buf.extend(struct.pack(">QQ", addr, sz))
    rsv_buf.extend(struct.pack(">QQ", 0, 0))

    off_mem_rsvmap = _align8(FDT_HEADER_SIZE)
    off_dt_struct = _align4(off_mem_rsvmap + len(rsv_buf))
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
        version,
        last_comp_version,
        boot_cpuid_phys,
        size_dt_strings,
        size_dt_struct,
    )

    out = bytearray(totalsize)
    out[0:FDT_HEADER_SIZE] = header
    out[off_mem_rsvmap : off_mem_rsvmap + len(rsv_buf)] = rsv_buf
    out[off_dt_struct : off_dt_struct + size_dt_struct] = struct_buf
    out[off_dt_strings : off_dt_strings + size_dt_strings] = strings_buf
    return bytes(out)


def parse_fdt_blob(data: bytes) -> FdtParseReport:
    """Parse and validate a Devicetree v17 (`0xd00dfeed`) binary blob without side effects."""
    blob_len = len(data)
    blob_sha = sha256(data).hexdigest()
    error_codes: List[str] = []
    errors: List[str] = []

    def _add_err(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    def _fail_early() -> FdtParseReport:
        return FdtParseReport(
            valid=False,
            status=STATUS_REJECTED_FDT_BLOB,
            blob_bytes=blob_len,
            blob_sha256=blob_sha,
            header=None,
            mem_rsvmap=(),
            node_count=0,
            property_count=0,
            root_model="",
            root_compatible=(),
            has_chosen=False,
            chosen_stdout_path=None,
            chosen_bootargs=None,
            chosen_initrd_start=None,
            chosen_initrd_end=None,
            nodes=(),
            error_codes=tuple(error_codes),
            errors=tuple(errors),
        )

    if blob_len < FDT_HEADER_SIZE or blob_len > FDT_MAX_BLOB_BYTES:
        _add_err(
            ERR_FDT_EMPTY_OR_TRUNCATED_HEADER,
            f"FDT blob length {blob_len} outside valid range [{FDT_HEADER_SIZE}, {FDT_MAX_BLOB_BYTES}].",
        )
        return _fail_early()

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
    ) = struct.unpack_from(">10I", data, 0)

    hdr = FdtHeaderInfo(
        magic=magic,
        magic_hex=f"0x{magic:08x}",
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

    if magic != FDT_MAGIC:
        _add_err(
            ERR_FDT_BAD_MAGIC,
            f"Bad FDT magic 0x{magic:08x} (expected 0x{FDT_MAGIC:08x}).",
        )
    if totalsize < FDT_HEADER_SIZE or totalsize > blob_len:
        _add_err(
            ERR_FDT_BAD_TOTALSIZE,
            f"Invalid FDT totalsize={totalsize} for blob_len={blob_len}.",
        )
    if version < FDT_VERSION_17 or last_comp_version > version or last_comp_version < FDT_MIN_COMP_VERSION:
        _add_err(
            ERR_FDT_UNSUPPORTED_VERSION,
            f"Unsupported FDT version={version} last_comp_version={last_comp_version} (require v17).",
        )

    effective_total = min(totalsize, blob_len)
    if off_mem_rsvmap < FDT_HEADER_SIZE or off_mem_rsvmap % 8 != 0 or off_mem_rsvmap + 16 > effective_total:
        _add_err(
            ERR_FDT_BAD_BOUNDS,
            f"Invalid off_mem_rsvmap=0x{off_mem_rsvmap:x} within totalsize={totalsize}.",
        )
    if (
        off_dt_struct < FDT_HEADER_SIZE
        or off_dt_struct % 4 != 0
        or size_dt_struct < 4
        or size_dt_struct % 4 != 0
        or off_dt_struct + size_dt_struct > effective_total
    ):
        _add_err(
            ERR_FDT_BAD_BOUNDS,
            f"Invalid dt_struct bounds [0x{off_dt_struct:x}, +0x{size_dt_struct:x}) vs totalsize={totalsize}.",
        )
    if off_dt_strings < FDT_HEADER_SIZE or off_dt_strings + size_dt_strings > effective_total:
        _add_err(
            ERR_FDT_BAD_BOUNDS,
            f"Invalid dt_strings bounds [0x{off_dt_strings:x}, +0x{size_dt_strings:x}) vs totalsize={totalsize}.",
        )

    struct_end = off_dt_struct + size_dt_struct
    strings_end = off_dt_strings + size_dt_strings
    if (
        not (struct_end <= off_dt_strings or strings_end <= off_dt_struct)
        and ERR_FDT_BAD_BOUNDS not in error_codes
    ):
        _add_err(
            ERR_FDT_OVERLAPPING_REGIONS,
            f"dt_struct [0x{off_dt_struct:x}, 0x{struct_end:x}) overlaps dt_strings [0x{off_dt_strings:x}, 0x{strings_end:x}).",
        )

    if error_codes:
        return FdtParseReport(
            valid=False,
            status=STATUS_REJECTED_FDT_BLOB,
            blob_bytes=blob_len,
            blob_sha256=blob_sha,
            header=hdr,
            mem_rsvmap=(),
            node_count=0,
            property_count=0,
            root_model="",
            root_compatible=(),
            has_chosen=False,
            chosen_stdout_path=None,
            chosen_bootargs=None,
            chosen_initrd_start=None,
            chosen_initrd_end=None,
            nodes=(),
            error_codes=tuple(error_codes),
            errors=tuple(errors),
        )

    # Parse /memreserve/ table
    rsv_entries: List[FdtReserveEntryInfo] = []
    rsv_pos = off_mem_rsvmap
    rsv_terminated = False
    while rsv_pos + 16 <= effective_total:
        addr, sz = struct.unpack_from(">QQ", data, rsv_pos)
        rsv_pos += 16
        if addr == 0 and sz == 0:
            rsv_terminated = True
            break
        rsv_entries.append(
            FdtReserveEntryInfo(
                address=addr,
                address_hex=f"0x{addr:x}",
                size=sz,
                size_hex=f"0x{sz:x}",
            )
        )
        if len(rsv_entries) > 256:
            break
    if not rsv_terminated:
        _add_err(ERR_FDT_BAD_MEM_RSVMAP, "FDT mem_rsvmap lacks terminating (0, 0) entry.")

    # Parse dt_struct token stream
    stack: List[str] = []
    node_order: List[str] = []
    node_units: Dict[str, str] = {}
    node_props: Dict[str, List[FdtPropertyInfo]] = {}
    raw_prop_bytes: Dict[Tuple[str, str], bytes] = {}
    total_props = 0
    saw_root = False
    saw_end = False

    pos = off_dt_struct
    while pos < struct_end:
        if pos + 4 > struct_end:
            _add_err(ERR_FDT_MALFORMED_TOKENS, f"Truncated FDT token at offset 0x{pos:x}.")
            break
        tok = struct.unpack_from(">I", data, pos)[0]
        pos += 4

        if tok == FDT_NOP:
            continue

        if tok == FDT_BEGIN_NODE:
            nul = data.find(b"\x00", pos, struct_end)
            if nul == -1:
                _add_err(ERR_FDT_MALFORMED_TOKENS, f"Unterminated node name at offset 0x{pos:x}.")
                break
            raw_unit = data[pos:nul]
            aligned_pos = _align4(nul + 1)
            if aligned_pos > struct_end:
                _add_err(ERR_FDT_MALFORMED_TOKENS, f"Node name padding exceeds dt_struct at offset 0x{pos:x}.")
                break
            if any(b != 0 for b in data[nul + 1 : aligned_pos]):
                _add_err(ERR_FDT_NONZERO_PADDING, f"Non-zero padding after node name at offset 0x{pos:x}.")
                break
            pos = aligned_pos
            try:
                unit_name = raw_unit.decode("ascii")
            except UnicodeDecodeError:
                _add_err(ERR_FDT_MALFORMED_TOKENS, f"Non-ASCII FDT node name at offset 0x{pos:x}.")
                break

            if not stack:
                if saw_root or unit_name != "":
                    _add_err(
                        ERR_FDT_MALFORMED_TOKENS,
                        f"Root node must have empty name and appear once (got {unit_name!r}).",
                    )
                    break
                saw_root = True
                full_path = "/"
            else:
                if not unit_name:
                    _add_err(ERR_FDT_MALFORMED_TOKENS, "Nested FDT node cannot have empty unit name.")
                    break
                parent = stack[-1]
                full_path = f"/{unit_name}" if parent == "/" else f"{parent}/{unit_name}"

            if full_path in node_props:
                _add_err(ERR_FDT_MALFORMED_TOKENS, f"Duplicate FDT node path {full_path!r}.")
                break
            stack.append(full_path)
            node_order.append(full_path)
            node_units[full_path] = unit_name
            node_props[full_path] = []

        elif tok == FDT_END_NODE:
            if not stack:
                _add_err(ERR_FDT_MALFORMED_TOKENS, f"FDT_END_NODE underflow at offset 0x{pos - 4:x}.")
                break
            stack.pop()

        elif tok == FDT_PROP:
            if not stack:
                _add_err(ERR_FDT_MALFORMED_TOKENS, f"FDT_PROP outside open node at offset 0x{pos - 4:x}.")
                break
            if pos + 8 > struct_end:
                _add_err(ERR_FDT_MALFORMED_TOKENS, f"Truncated FDT_PROP header at offset 0x{pos - 4:x}.")
                break
            plen, nameoff = struct.unpack_from(">II", data, pos)
            pos += 8
            val_end = pos + plen
            aligned_end = _align4(val_end)
            if aligned_end > struct_end:
                _add_err(ERR_FDT_MALFORMED_TOKENS, f"FDT_PROP payload exceeds dt_struct at offset 0x{pos:x}.")
                break
            if any(b != 0 for b in data[val_end:aligned_end]):
                _add_err(ERR_FDT_NONZERO_PADDING, f"Non-zero FDT_PROP padding at offset 0x{val_end:x}.")
                break
            val_bytes = data[pos:val_end]
            pos = aligned_end

            if nameoff >= size_dt_strings:
                _add_err(
                    ERR_FDT_BAD_STRING_OFFSET,
                    f"FDT_PROP nameoff=0x{nameoff:x} >= size_dt_strings=0x{size_dt_strings:x}.",
                )
                break
            s_nul = data.find(b"\x00", off_dt_strings + nameoff, strings_end)
            if s_nul == -1:
                _add_err(
                    ERR_FDT_BAD_STRING_OFFSET,
                    f"Unterminated property name in dt_strings at offset 0x{nameoff:x}.",
                )
                break
            prop_name = data[off_dt_strings + nameoff : s_nul].decode("ascii", errors="replace")
            if not prop_name:
                _add_err(ERR_FDT_MALFORMED_TOKENS, "Empty property name in FDT_PROP.")
                break

            preview: Optional[str] = None
            if val_bytes and val_bytes.endswith(b"\x00"):
                cand = val_bytes[:-1]
                if all(32 <= b < 127 or b in (0, 9, 10) for b in cand):
                    preview = cand.replace(b"\x00", b", ").decode("ascii", errors="replace")[:160]
            u32_val = struct.unpack(">I", val_bytes)[0] if len(val_bytes) == 4 else None
            u64_val = struct.unpack(">Q", val_bytes)[0] if len(val_bytes) == 8 else None

            cur_path = stack[-1]
            node_props[cur_path].append(
                FdtPropertyInfo(
                    name=prop_name,
                    value_len=len(val_bytes),
                    value_sha256=sha256(val_bytes).hexdigest(),
                    value_hex_prefix=val_bytes[:16].hex(),
                    text_preview=preview,
                    u32_be=u32_val,
                    u64_be=u64_val,
                )
            )
            raw_prop_bytes[(cur_path, prop_name)] = val_bytes
            total_props += 1

        elif tok == FDT_END:
            if stack:
                _add_err(
                    ERR_FDT_UNCLOSED_NODE,
                    f"FDT_END encountered while {len(stack)} node(s) remain unclosed.",
                )
                break
            if not saw_root:
                _add_err(ERR_FDT_MALFORMED_TOKENS, "FDT_END encountered without root node.")
                break
            saw_end = True
            while pos < struct_end:
                trailing = struct.unpack_from(">I", data, pos)[0]
                if trailing != FDT_NOP:
                    _add_err(
                        ERR_FDT_MALFORMED_TOKENS,
                        f"Unexpected token 0x{trailing:08x} after FDT_END.",
                    )
                    break
                pos += 4
            break

        else:
            _add_err(
                ERR_FDT_UNKNOWN_TOKEN,
                f"Unknown FDT token 0x{tok:08x} at dt_struct offset 0x{pos - 4:x}.",
            )
            break

    if not saw_end and ERR_FDT_MISSING_END_TOKEN not in error_codes and not error_codes:
        _add_err(ERR_FDT_MISSING_END_TOKEN, "Missing terminating FDT_END (0x00000009) token.")
    elif not saw_end and ERR_FDT_UNCLOSED_NODE not in error_codes and ERR_FDT_MISSING_END_TOKEN not in error_codes:
        _add_err(ERR_FDT_MISSING_END_TOKEN, "FDT token stream ended without valid FDT_END.")

    nodes = tuple(
        FdtNodeInfo(path=p, unit_name=node_units[p], properties=tuple(node_props[p]))
        for p in node_order
    )

    root_model_raw = raw_prop_bytes.get(("/", "model"), b"")
    root_model = root_model_raw.rstrip(b"\x00").decode("utf-8", errors="replace") if root_model_raw else ""
    root_compat = _decode_strlist(raw_prop_bytes.get(("/", "compatible"), b""))
    has_chosen = "/chosen" in node_props

    stdout_raw = raw_prop_bytes.get(("/chosen", "stdout-path"))
    chosen_stdout = stdout_raw.rstrip(b"\x00").decode("utf-8", errors="replace") if stdout_raw else None

    bootargs_raw = raw_prop_bytes.get(("/chosen", "bootargs"))
    chosen_bootargs = bootargs_raw.rstrip(b"\x00").decode("utf-8", errors="replace") if bootargs_raw else None

    def _decode_addr_prop(raw_val: Optional[bytes]) -> Optional[int]:
        if raw_val is None:
            return None
        if len(raw_val) == 4:
            return struct.unpack(">I", raw_val)[0]
        if len(raw_val) == 8:
            return struct.unpack(">Q", raw_val)[0]
        return None

    initrd_start = _decode_addr_prop(raw_prop_bytes.get(("/chosen", "linux,initrd-start")))
    initrd_end = _decode_addr_prop(raw_prop_bytes.get(("/chosen", "linux,initrd-end")))

    valid = len(error_codes) == 0 and saw_root and saw_end
    return FdtParseReport(
        valid=valid,
        status=STATUS_VERIFIED_FDT_BLOB if valid else STATUS_REJECTED_FDT_BLOB,
        blob_bytes=blob_len,
        blob_sha256=blob_sha,
        header=hdr,
        mem_rsvmap=tuple(rsv_entries),
        node_count=len(nodes),
        property_count=total_props,
        root_model=root_model,
        root_compatible=root_compat,
        has_chosen=has_chosen,
        chosen_stdout_path=chosen_stdout,
        chosen_bootargs=chosen_bootargs,
        chosen_initrd_start=initrd_start,
        chosen_initrd_end=initrd_end,
        nodes=nodes,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 1B — /chosen/bootargs & /chosen/linux,initrd-start..end Firewall
# ---------------------------------------------------------------------------


def _is_emmc_root_device(root_dev: Optional[str]) -> bool:
    if not root_dev:
        return False
    low = root_dev.strip().lower()
    return any(low.startswith(pref) for pref in EMMC_ROOT_DEVICE_PREFIXES)


def audit_fdt_chosen_bootargs(
    fdt_blob: bytes,
    *,
    require_cxd90057: bool = True,
    require_initrd: bool = True,
    allowed_init_paths: Sequence[str] = ALLOWED_VERIFIED_INIT_PATHS,
) -> FdtBootargsAuditReport:
    """Audit an FDT blob's `/chosen/bootargs` and `/chosen/linux,initrd-start..end` fail-closed."""
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    require(PERSISTENT_WRITE_RELEASE is False, "persistent_write_release must stay False")

    parsed = parse_fdt_blob(fdt_blob)
    error_codes: List[str] = list(parsed.error_codes)
    errors: List[str] = list(parsed.errors)

    def _add_err(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    if require_cxd90057 and parsed.valid:
        if parsed.root_model != CXD90057_SOC_MODEL or CXD90057_COMPATIBLE not in parsed.root_compatible:
            _add_err(
                ERR_FDT_SOC_MISMATCH,
                f"FDT SoC mismatch: model={parsed.root_model!r}, compatible={parsed.root_compatible!r} "
                f"(expected {CXD90057_SOC_MODEL!r} / {CXD90057_COMPATIBLE!r}).",
            )

    if parsed.valid and not parsed.has_chosen:
        _add_err(ERR_FDT_MISSING_CHOSEN, "FDT blob lacks /chosen node.")

    bootargs_str = (parsed.chosen_bootargs or "").strip() if parsed.chosen_bootargs is not None else ""
    if not bootargs_str:
        _add_err(ERR_BOOTARGS_MISSING_OR_EMPTY, "/chosen/bootargs property is missing or empty.")

    tokens: Tuple[str, ...] = ()
    if bootargs_str:
        try:
            tokens = tuple(shlex.split(bootargs_str))
        except ValueError as exc:
            _add_err(ERR_BOOTARGS_MALFORMED, f"Malformed /chosen/bootargs quoting: {exc}")

    root_device: Optional[str] = None
    init_path: Optional[str] = None
    rdinit_path: Optional[str] = None
    has_ro = False
    has_rw = False
    has_rootwait = False
    repart_tokens: List[str] = []
    wdt_disable_tokens: List[str] = []

    for tok in tokens:
        low = tok.lower()
        if tok == "ro":
            has_ro = True
        elif tok == "rw":
            has_rw = True
        elif tok == "rootwait":
            has_rootwait = True
        elif tok.startswith("root="):
            root_device = tok.split("=", 1)[1]
        elif tok.startswith("init="):
            init_path = tok.split("=", 1)[1]
        elif tok.startswith("rdinit="):
            rdinit_path = tok.split("=", 1)[1]

        key = low.split("=", 1)[0]
        if key in FORBIDDEN_REPARTITION_KEYS:
            repart_tokens.append(tok)
        if low in FORBIDDEN_WDT_DISABLE_TOKENS or "nowatchdog" in low:
            wdt_disable_tokens.append(tok)

    rootfs_is_emmc = _is_emmc_root_device(root_device)
    if rootfs_is_emmc:
        if has_rw:
            _add_err(
                ERR_BOOTARGS_RW_EMMC_ROOTFS,
                f"Forbidden 'rw' mount flag passed for eMMC rootfs '{root_device}' (require 'ro rootwait').",
            )
        if not has_ro:
            _add_err(
                ERR_BOOTARGS_MISSING_RO,
                f"eMMC rootfs '{root_device}' requires explicit 'ro' flag in /chosen/bootargs.",
            )
        if not has_rootwait:
            _add_err(
                ERR_BOOTARGS_MISSING_ROOTWAIT,
                f"eMMC rootfs '{root_device}' requires 'rootwait' in /chosen/bootargs.",
            )
    elif has_rw and (root_device is None or root_device not in ("/dev/ram0", "tmpfs")):
        _add_err(
            ERR_BOOTARGS_RW_EMMC_ROOTFS,
            f"Forbidden 'rw' flag in Stage-B /chosen/bootargs (root={root_device!r}).",
        )

    allowed_inits = set(allowed_init_paths)
    init_ok = True
    if init_path is not None and init_path not in allowed_inits:
        init_ok = False
        _add_err(
            ERR_BOOTARGS_UNVERIFIED_INIT_PATH,
            f"Unverified init={init_path!r} outside allowed Stage-B/stock init paths.",
        )
    if rdinit_path is not None and rdinit_path not in allowed_inits:
        init_ok = False
        _add_err(
            ERR_BOOTARGS_UNVERIFIED_INIT_PATH,
            f"Unverified rdinit={rdinit_path!r} outside allowed Stage-B/stock init paths.",
        )

    if repart_tokens:
        _add_err(
            ERR_BOOTARGS_FORBIDDEN_REPARTITIONING,
            f"Forbidden eMMC repartitioning bootarg(s) detected: {', '.join(repart_tokens)}.",
        )

    if wdt_disable_tokens:
        _add_err(
            ERR_BOOTARGS_WDT_DISABLED,
            f"Watchdog-disabling bootarg(s) forbidden in Stage-B rehearsals: {', '.join(wdt_disable_tokens)}.",
        )

    # Audit /chosen/linux,initrd-start..end
    chosen_node = next((n for n in parsed.nodes if n.path == "/chosen"), None)
    initrd_start_prop = next((p for p in chosen_node.properties if p.name == "linux,initrd-start"), None) if chosen_node else None
    initrd_end_prop = next((p for p in chosen_node.properties if p.name == "linux,initrd-end"), None) if chosen_node else None

    has_start_prop = initrd_start_prop is not None
    has_end_prop = initrd_end_prop is not None
    initrd_present = has_start_prop and has_end_prop
    initrd_size: Optional[int] = None
    initrd_ok = True

    if has_start_prop != has_end_prop:
        initrd_ok = False
        _add_err(
            ERR_INITRD_ASYMMETRIC_BOUNDS,
            "Asymmetric /chosen/linux,initrd-start and linux,initrd-end properties.",
        )
    elif not initrd_present:
        if require_initrd:
            initrd_ok = False
            _add_err(
                ERR_INITRD_MISSING,
                "Missing mandatory /chosen/linux,initrd-start and linux,initrd-end properties.",
            )
    else:
        assert initrd_start_prop is not None and initrd_end_prop is not None
        if initrd_start_prop.value_len not in (4, 8) or initrd_end_prop.value_len not in (4, 8):
            initrd_ok = False
            _add_err(
                ERR_INITRD_INVALID_CELL_SIZE,
                f"Invalid initrd cell sizes: start={initrd_start_prop.value_len}B, end={initrd_end_prop.value_len}B (expected 4 or 8).",
            )
        else:
            s_val = parsed.chosen_initrd_start
            e_val = parsed.chosen_initrd_end
            if s_val is None or e_val is None or s_val == 0 or e_val <= s_val:
                initrd_ok = False
                _add_err(
                    ERR_INITRD_INVALID_RANGE,
                    f"Invalid initrd address window: start={s_val}, end={e_val}.",
                )
            else:
                initrd_size = e_val - s_val
                if initrd_size > MAX_INITRD_WINDOW_BYTES:
                    initrd_ok = False
                    _add_err(
                        ERR_INITRD_SIZE_OUT_OF_BOUNDS,
                        f"Initrd window size {initrd_size} exceeds safety ceiling {MAX_INITRD_WINDOW_BYTES}.",
                    )

    passed = parsed.valid and len(error_codes) == 0
    return FdtBootargsAuditReport(
        passed=passed,
        status=STATUS_VERIFIED_BOOTARGS_FIREWALL if passed else STATUS_REJECTED_BOOTARGS_FIREWALL,
        fdt_valid=parsed.valid,
        fdt_sha256=parsed.blob_sha256,
        root_model=parsed.root_model,
        root_compatible=parsed.root_compatible,
        bootargs_raw=bootargs_str,
        bootargs_tokens=tokens,
        root_device=root_device,
        rootfs_is_emmc_block=rootfs_is_emmc,
        has_ro=has_ro,
        has_rw=has_rw,
        has_rootwait=has_rootwait,
        init_path=init_path,
        rdinit_path=rdinit_path,
        init_path_verified=init_ok,
        has_forbidden_repartitioning=bool(repart_tokens),
        repartitioning_tokens=tuple(repart_tokens),
        watchdog_enabled=len(wdt_disable_tokens) == 0,
        wdt_disable_tokens=tuple(wdt_disable_tokens),
        initrd_present=initrd_present,
        initrd_start=parsed.chosen_initrd_start,
        initrd_end=parsed.chosen_initrd_end,
        initrd_size_bytes=initrd_size,
        initrd_valid=initrd_ok,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Pillar 2 — ARM64 Linux Kernel Image Header & Cross-SKU Firewall
# ---------------------------------------------------------------------------


def build_synthetic_arm64_kernel_image(
    *,
    sku: str = "ILME-FX3",
    kernel_release: str = EXPECTED_FX3_KERNEL_RELEASE,
    code0: int = 0x1416C000,
    code1: int = 0,
    text_offset: int = EXPECTED_ARM64_TEXT_OFFSET,
    image_size: int = EXPECTED_ARM64_IMAGE_SIZE,
    flags: int = 0xA,
    magic: int = ARM64_IMAGE_MAGIC,
    include_cxd90057_marker: bool = True,
    total_size_bytes: int = 4096,
) -> bytes:
    """Synthesize an ARM64 Linux `Image` binary strictly in memory for clean-room tests."""
    if total_size_bytes < ARM64_IMAGE_HEADER_SIZE:
        hdr = struct.pack(
            "<IIQQQQQQII",
            code0,
            code1,
            text_offset,
            image_size,
            flags,
            0,
            0,
            0,
            magic,
            0,
        )
        return hdr[:total_size_bytes]

    buf = bytearray(total_size_bytes)
    struct.pack_into(
        "<IIQQQQQQII",
        buf,
        0,
        code0,
        code1,
        text_offset,
        image_size,
        flags,
        0,
        0,
        0,
        magic,
        0,
    )
    if sku.upper() in ("FX6", "ILME-FX6", "CHAPLIN"):
        banner = (
            f"Linux version {kernel_release} (jp10239@{FX6_KERNEL_BUILD_HOST}) "
            f"(gcc version 6.4.0 (20240928 ({FX6_KERNEL_TOOLCHAIN_MARKER})) ) "
            "#1 SMP PREEMPT Wed Aug 5 15:24:28 JST 2026\n\x00"
        ).encode("ascii")
    else:
        banner = (
            f"Linux version {kernel_release} (jp10239@{FX3_KERNEL_BUILD_HOST}) "
            f"(gcc version 6.4.0 (20201211 ({FX3_KERNEL_TOOLCHAIN_MARKER})) ) "
            "#1 SMP PREEMPT Thu Dec 25 08:15:40 JST 2025\n\x00"
        ).encode("ascii")

    cursor = 0x100
    if cursor + len(banner) <= total_size_bytes:
        buf[cursor : cursor + len(banner)] = banner
        cursor += len(banner) + 16
    if include_cxd90057_marker:
        soc_marker = b"sony,cxd90057\x00CXD90057\x00"
        if cursor + len(soc_marker) <= total_size_bytes:
            buf[cursor : cursor + len(soc_marker)] = soc_marker
    return bytes(buf)


def audit_arm64_kernel_image(
    data: bytes,
    *,
    label: str = "vmlinux.bin",
    expected_sku: str = "ILME-FX3",
    candidate_sku: Optional[str] = None,
    expected_fx3_sha256: Optional[str] = None,
    min_file_bytes: int = 1024,
    require_cxd90057_marker: bool = True,
) -> Arm64KernelImageReport:
    """Parse 64-byte ARM64 Linux `Image` header & enforce authentic FX3 CXD90057 kernel firewall."""
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    require(PERSISTENT_WRITE_RELEASE is False, "persistent_write_release must stay False")

    file_bytes = len(data)
    img_sha = sha256(data).hexdigest()
    error_codes: List[str] = []
    errors: List[str] = []

    def _add_err(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    if file_bytes < ARM64_IMAGE_HEADER_SIZE:
        _add_err(
            ERR_KERNEL_TRUNCATED_HEADER,
            f"Kernel image '{label}' length {file_bytes} < {ARM64_IMAGE_HEADER_SIZE}-byte ARM64 header.",
        )
        return Arm64KernelImageReport(
            passed=False,
            status=STATUS_REJECTED_ARM64_KERNEL,
            label=label,
            file_bytes=file_bytes,
            image_sha256=img_sha,
            magic=0,
            magic_hex="0x00000000",
            code0=0,
            code0_hex="0x00000000",
            code1=0,
            text_offset=0,
            text_offset_hex="0x0",
            image_size=0,
            image_size_hex="0x0",
            flags=0,
            flags_hex="0x0",
            is_little_endian=False,
            page_size_code=0,
            page_size_label="UNKNOWN",
            phys_placement_2mb_aligned=False,
            reserved_flags_zero=False,
            kernel_release="",
            kernel_banner="",
            build_host="",
            toolchain_marker="",
            cxd90057_marker_present=False,
            detected_sku="UNKNOWN",
            cross_sku_transplant_detected=False,
            truncated_image=True,
            error_codes=tuple(error_codes),
            errors=tuple(errors),
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    code0, code1, text_offset, image_size, flags, _r2, _r3, _r4, magic, _r5 = struct.unpack_from(
        "<IIQQQQQQII", data, 0
    )
    is_le = (flags & ARM64_FLAG_ENDIAN_MASK) == 0
    page_code = (flags >> ARM64_FLAG_PAGE_SIZE_SHIFT) & ARM64_FLAG_PAGE_SIZE_MASK
    page_label = ARM64_PAGE_SIZE_MAP.get(page_code, f"UNKNOWN_{page_code}")
    phys_2mb = bool(flags & ARM64_FLAG_PHYS_PLACEMENT_BIT)
    reserved_zero = (flags & ~0xF) == 0

    if magic != ARM64_IMAGE_MAGIC:
        _add_err(
            ERR_KERNEL_BAD_ARM64_MAGIC,
            f"Bad ARM64 Image magic 0x{magic:08x} at offset 0x38 (expected 0x{ARM64_IMAGE_MAGIC:08x}).",
        )
    if code0 == 0:
        _add_err(ERR_KERNEL_INVALID_CODE0, "ARM64 Image header code0 is 0x00000000 (missing branch).")
    if not is_le:
        _add_err(ERR_KERNEL_BIG_ENDIAN_FORBIDDEN, "ARM64 Image flags bit 0 indicates big-endian kernel (forbidden).")
    if page_code != 1:
        _add_err(
            ERR_KERNEL_UNSUPPORTED_PAGE_SIZE,
            f"ARM64 Image page size is {page_label} (code={page_code}), expected 4K (code=1).",
        )
    if not reserved_zero:
        _add_err(
            ERR_KERNEL_NONZERO_RESERVED_FLAGS,
            f"ARM64 Image flags 0x{flags:x} has non-zero reserved bits.",
        )
    if text_offset != EXPECTED_ARM64_TEXT_OFFSET:
        _add_err(
            ERR_KERNEL_INVALID_TEXT_OFFSET,
            f"ARM64 Image text_offset=0x{text_offset:x} != expected 0x{EXPECTED_ARM64_TEXT_OFFSET:x}.",
        )
    if image_size == 0:
        _add_err(ERR_KERNEL_ZERO_IMAGE_SIZE, "ARM64 Image header image_size is 0.")

    truncated = False
    if file_bytes < min_file_bytes:
        truncated = True
        _add_err(
            ERR_KERNEL_TRUNCATED_IMAGE,
            f"Kernel image '{label}' truncated: {file_bytes}B < minimum {min_file_bytes}B.",
        )

    banner_m = re.search(rb"Linux version ([^\n\x00]+)", data)
    kernel_banner = banner_m.group(0).decode("ascii", errors="replace") if banner_m else ""
    rel_m = re.search(rb"Linux version ([^\s\x00]+)", data)
    kernel_release = rel_m.group(1).decode("ascii", errors="replace") if rel_m else ""

    if not kernel_release.startswith(EXPECTED_FX3_KERNEL_RELEASE):
        _add_err(
            ERR_KERNEL_RELEASE_MISMATCH,
            f"Kernel release {kernel_release or 'NONE'!r} != expected '{EXPECTED_FX3_KERNEL_RELEASE}'.",
        )

    cxd_present = (b"cxd90057" in data.lower()) or (b"sony,cxd90057" in data)
    if require_cxd90057_marker and not cxd_present:
        _add_err(ERR_KERNEL_SOC_MISMATCH, "Kernel image lacks CXD90057 SoC compatibility marker.")

    build_host = ""
    if FX3_KERNEL_BUILD_HOST in kernel_banner:
        build_host = FX3_KERNEL_BUILD_HOST
    elif FX6_KERNEL_BUILD_HOST in kernel_banner:
        build_host = FX6_KERNEL_BUILD_HOST

    toolchain_marker = ""
    if FX3_KERNEL_TOOLCHAIN_MARKER in kernel_banner:
        toolchain_marker = FX3_KERNEL_TOOLCHAIN_MARKER
    elif FX6_KERNEL_TOOLCHAIN_MARKER in kernel_banner:
        toolchain_marker = FX6_KERNEL_TOOLCHAIN_MARKER

    detected_sku = "UNKNOWN"
    if (
        img_sha == PINNED_FX6_VMLINUX_SHA256
        or build_host == FX6_KERNEL_BUILD_HOST
        or toolchain_marker == FX6_KERNEL_TOOLCHAIN_MARKER
        or b"ILME-FX6" in data
        or b"CHAPLIN" in data
        or (candidate_sku and candidate_sku.upper() in ("FX6", "ILME-FX6", "CHAPLIN"))
    ):
        detected_sku = "ILME-FX6"
    elif (
        img_sha == PINNED_FX3_VMLINUX_SHA256
        or build_host == FX3_KERNEL_BUILD_HOST
        or toolchain_marker == FX3_KERNEL_TOOLCHAIN_MARKER
        or b"ILME-FX3" in data
        or b"ALCIN_UUD" in data
        or (candidate_sku and candidate_sku.upper() in ("FX3", "ILME-FX3", "ALCIN_UUD"))
    ):
        detected_sku = "ILME-FX3"

    cross_sku = False
    if expected_sku.upper() in ("FX3", "ILME-FX3", "ALCIN_UUD") and detected_sku == "ILME-FX6":
        cross_sku = True
        _add_err(
            ERR_KERNEL_CROSS_SKU_FX6_TRANSPLANT,
            f"Cross-SKU FX6 kernel transplant rejected ({build_host or img_sha[:16]}): "
            "Stage-B must boot FX3's authentic 4.9.337-scel+ kernel.",
        )

    if expected_fx3_sha256 is not None and img_sha != expected_fx3_sha256 and not cross_sku:
        _add_err(
            ERR_KERNEL_SHA256_MISMATCH,
            f"Kernel SHA-256 {img_sha[:16]} != expected FX3 digest {expected_fx3_sha256[:16]}.",
        )

    passed = len(error_codes) == 0
    return Arm64KernelImageReport(
        passed=passed,
        status=STATUS_VERIFIED_ARM64_KERNEL if passed else STATUS_REJECTED_ARM64_KERNEL,
        label=label,
        file_bytes=file_bytes,
        image_sha256=img_sha,
        magic=magic,
        magic_hex=f"0x{magic:08x}",
        code0=code0,
        code0_hex=f"0x{code0:08x}",
        code1=code1,
        text_offset=text_offset,
        text_offset_hex=f"0x{text_offset:x}",
        image_size=image_size,
        image_size_hex=f"0x{image_size:x}",
        flags=flags,
        flags_hex=f"0x{flags:x}",
        is_little_endian=is_le,
        page_size_code=page_code,
        page_size_label=page_label,
        phys_placement_2mb_aligned=phys_2mb,
        reserved_flags_zero=reserved_zero,
        kernel_release=kernel_release,
        kernel_banner=kernel_banner,
        build_host=build_host,
        toolchain_marker=toolchain_marker,
        cxd90057_marker_present=cxd_present,
        detected_sku=detected_sku,
        cross_sku_transplant_detected=cross_sku,
        truncated_image=truncated,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Donor Read-Only Inspection & Clean-Room Synthetic Fallback
# ---------------------------------------------------------------------------


def inspect_fdt_and_kernel_donors_readonly(
    *,
    force_clean_room: Optional[bool] = None,
) -> DonorFdtKernelSnapshot:
    """Inspect local FX3/FX6 DTB, kernel `Image`, and `kemco.txt` strictly via `os.O_RDONLY`,
    falling back deterministically to `CLEAN_ROOM_SYNTHETIC` when forced or absent.
    """
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)

    fx3_s_dtb_p = None if clean_room else resolve_donor_path(DONOR_FX3_SETTING_DTB_RELPATH)
    fx3_b_dtb_p = None if clean_room else resolve_donor_path(DONOR_FX3_BOOT_DTB_RELPATH)
    fx6_s_dtb_p = None if clean_room else resolve_donor_path(DONOR_FX6_SETTING_DTB_RELPATH)
    fx3_kern_p = None if clean_room else resolve_donor_path(DONOR_FX3_VMLINUX_RELPATH)
    fx6_kern_p = None if clean_room else resolve_donor_path(DONOR_FX6_VMLINUX_RELPATH)
    fx3_kemco_p = None if clean_room else resolve_donor_path(DONOR_FX3_KEMCO_RELPATH)
    fx6_kemco_p = None if clean_room else resolve_donor_path(DONOR_FX6_KEMCO_RELPATH)

    have_local = all(
        p is not None and p.is_file()
        for p in (fx3_s_dtb_p, fx3_b_dtb_p, fx6_s_dtb_p, fx3_kern_p, fx6_kern_p, fx3_kemco_p, fx6_kemco_p)
    )

    artifacts: List[DonorFdtKernelArtifactInfo] = []
    if have_local and fx3_s_dtb_p and fx3_b_dtb_p and fx6_s_dtb_p and fx3_kern_p and fx6_kern_p and fx3_kemco_p and fx6_kemco_p:
        verification_mode = "LOCAL_DONOR_O_RDONLY"

        fx3_s_dtb = read_file(fx3_s_dtb_p, FDT_MAX_BLOB_BYTES)
        fx3_s_rep = parse_fdt_blob(fx3_s_dtb)
        fx3_s_ok = fx3_s_rep.valid and fx3_s_rep.root_model == CXD90057_SOC_MODEL
        artifacts.append(
            DonorFdtKernelArtifactInfo(
                label="fx3_setting_cxd90057_dtb",
                source_mode=verification_mode,
                byte_length=len(fx3_s_dtb),
                sha256=fx3_s_rep.blob_sha256,
                valid=fx3_s_ok,
                details={
                    "root_model": fx3_s_rep.root_model,
                    "node_count": fx3_s_rep.node_count,
                    "property_count": fx3_s_rep.property_count,
                    "stdout_path": fx3_s_rep.chosen_stdout_path,
                },
            )
        )

        fx3_b_dtb = read_file(fx3_b_dtb_p, FDT_MAX_BLOB_BYTES)
        fx3_b_rep = parse_fdt_blob(fx3_b_dtb)
        fx3_b_ok = fx3_b_rep.valid and fx3_b_rep.root_model == CXD90057_SOC_MODEL
        artifacts.append(
            DonorFdtKernelArtifactInfo(
                label="fx3_boot_cxd90057_dtb",
                source_mode=verification_mode,
                byte_length=len(fx3_b_dtb),
                sha256=fx3_b_rep.blob_sha256,
                valid=fx3_b_ok,
                details={
                    "root_model": fx3_b_rep.root_model,
                    "node_count": fx3_b_rep.node_count,
                    "property_count": fx3_b_rep.property_count,
                },
            )
        )

        fx6_s_dtb = read_file(fx6_s_dtb_p, FDT_MAX_BLOB_BYTES)
        fx6_s_rep = parse_fdt_blob(fx6_s_dtb)
        fx6_s_ok = fx6_s_rep.valid and fx6_s_rep.root_model == CXD90057_SOC_MODEL
        artifacts.append(
            DonorFdtKernelArtifactInfo(
                label="fx6_setting_cxd90057_dtb",
                source_mode=verification_mode,
                byte_length=len(fx6_s_dtb),
                sha256=fx6_s_rep.blob_sha256,
                valid=fx6_s_ok,
                details={
                    "root_model": fx6_s_rep.root_model,
                    "matches_fx3_setting_dtb": fx6_s_rep.blob_sha256 == fx3_s_rep.blob_sha256,
                },
            )
        )

        fx3_kern = read_file(fx3_kern_p, 32 * 1024 * 1024)
        fx3_k_rep = audit_arm64_kernel_image(
            fx3_kern,
            label="fx3_vmlinux.bin",
            expected_fx3_sha256=PINNED_FX3_VMLINUX_SHA256,
            min_file_bytes=FX3_KERNEL_MIN_FILE_BYTES,
        )
        fx3_k_ok = fx3_k_rep.passed
        artifacts.append(
            DonorFdtKernelArtifactInfo(
                label="fx3_vmlinux_arm64_image",
                source_mode=verification_mode,
                byte_length=len(fx3_kern),
                sha256=fx3_k_rep.image_sha256,
                valid=fx3_k_ok,
                details={
                    "magic_hex": fx3_k_rep.magic_hex,
                    "text_offset_hex": fx3_k_rep.text_offset_hex,
                    "image_size_hex": fx3_k_rep.image_size_hex,
                    "kernel_release": fx3_k_rep.kernel_release,
                    "build_host": fx3_k_rep.build_host,
                    "detected_sku": fx3_k_rep.detected_sku,
                },
            )
        )

        fx6_kern = read_file(fx6_kern_p, 32 * 1024 * 1024)
        fx6_k_rep = audit_arm64_kernel_image(
            fx6_kern,
            label="fx6_vmlinux.bin",
            expected_sku="ILME-FX3",
            min_file_bytes=FX3_KERNEL_MIN_FILE_BYTES,
        )
        fx6_rejected_ok = (
            (not fx6_k_rep.passed)
            and fx6_k_rep.cross_sku_transplant_detected
            and (ERR_KERNEL_CROSS_SKU_FX6_TRANSPLANT in fx6_k_rep.error_codes)
        )
        artifacts.append(
            DonorFdtKernelArtifactInfo(
                label="fx6_vmlinux_arm64_image",
                source_mode=verification_mode,
                byte_length=len(fx6_kern),
                sha256=fx6_k_rep.image_sha256,
                valid=fx6_rejected_ok,
                details={
                    "detected_sku": fx6_k_rep.detected_sku,
                    "build_host": fx6_k_rep.build_host,
                    "cross_sku_transplant_rejected": fx6_rejected_ok,
                },
            )
        )

        fx3_kemco = read_file(fx3_kemco_p, 256 * 1024)
        fx3_kemco_txt = fx3_kemco.decode("utf-8", errors="replace")
        fx3_kemco_ok = ("init=/sbin/init" in fx3_kemco_txt) and ("wdt.timeout=500" in fx3_kemco_txt)
        artifacts.append(
            DonorFdtKernelArtifactInfo(
                label="fx3_kemco_txt",
                source_mode=verification_mode,
                byte_length=len(fx3_kemco),
                sha256=sha256(fx3_kemco).hexdigest(),
                valid=fx3_kemco_ok,
                details={"has_wdt_timeout": "wdt.timeout=500" in fx3_kemco_txt, "has_ramdisk_16384": "ramdisk_size=16384" in fx3_kemco_txt},
            )
        )

        fx6_kemco = read_file(fx6_kemco_p, 256 * 1024)
        fx6_kemco_txt = fx6_kemco.decode("utf-8", errors="replace")
        fx6_kemco_ok = ("init=/sbin/init" in fx6_kemco_txt) and ("ramdisk_size=8192" in fx6_kemco_txt)
        artifacts.append(
            DonorFdtKernelArtifactInfo(
                label="fx6_kemco_txt",
                source_mode=verification_mode,
                byte_length=len(fx6_kemco),
                sha256=sha256(fx6_kemco).hexdigest(),
                valid=fx6_kemco_ok,
                details={"has_wdt_timeout": "wdt.timeout=500" in fx6_kemco_txt, "has_ramdisk_8192": "ramdisk_size=8192" in fx6_kemco_txt},
            )
        )
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
        syn_dtb = build_synthetic_fdt_blob(bootargs=None, initrd_start=None, initrd_end=None)
        syn_dtb_rep = parse_fdt_blob(syn_dtb)
        fx3_s_ok = syn_dtb_rep.valid
        fx3_b_ok = syn_dtb_rep.valid
        fx6_s_ok = syn_dtb_rep.valid
        for lbl in ("fx3_setting_cxd90057_dtb", "fx3_boot_cxd90057_dtb", "fx6_setting_cxd90057_dtb"):
            artifacts.append(
                DonorFdtKernelArtifactInfo(
                    label=lbl,
                    source_mode=verification_mode,
                    byte_length=len(syn_dtb),
                    sha256=syn_dtb_rep.blob_sha256,
                    valid=True,
                    details={"root_model": syn_dtb_rep.root_model, "synthetic": True},
                )
            )

        syn_fx3_kern = build_synthetic_arm64_kernel_image(sku="ILME-FX3")
        syn_fx3_rep = audit_arm64_kernel_image(syn_fx3_kern, label="synthetic_fx3_vmlinux.bin")
        fx3_k_ok = syn_fx3_rep.passed
        artifacts.append(
            DonorFdtKernelArtifactInfo(
                label="fx3_vmlinux_arm64_image",
                source_mode=verification_mode,
                byte_length=len(syn_fx3_kern),
                sha256=syn_fx3_rep.image_sha256,
                valid=fx3_k_ok,
                details={"kernel_release": syn_fx3_rep.kernel_release, "detected_sku": syn_fx3_rep.detected_sku, "synthetic": True},
            )
        )

        syn_fx6_kern = build_synthetic_arm64_kernel_image(sku="ILME-FX6")
        syn_fx6_rep = audit_arm64_kernel_image(syn_fx6_kern, label="synthetic_fx6_vmlinux.bin")
        fx6_rejected_ok = (not syn_fx6_rep.passed) and syn_fx6_rep.cross_sku_transplant_detected
        artifacts.append(
            DonorFdtKernelArtifactInfo(
                label="fx6_vmlinux_arm64_image",
                source_mode=verification_mode,
                byte_length=len(syn_fx6_kern),
                sha256=syn_fx6_rep.image_sha256,
                valid=fx6_rejected_ok,
                details={"detected_sku": syn_fx6_rep.detected_sku, "cross_sku_transplant_rejected": fx6_rejected_ok, "synthetic": True},
            )
        )

        fx3_kemco_ok = True
        fx6_kemco_ok = True
        for lbl, rsz in (("fx3_kemco_txt", 16384), ("fx6_kemco_txt", 8192)):
            syn_k = f"kemco\ninit=/sbin/init\nramdisk_size={rsz}\nwdt.timeout=500\n*\n".encode("utf-8")
            artifacts.append(
                DonorFdtKernelArtifactInfo(
                    label=lbl,
                    source_mode=verification_mode,
                    byte_length=len(syn_k),
                    sha256=sha256(syn_k).hexdigest(),
                    valid=True,
                    details={"ramdisk_size": rsz, "synthetic": True},
                )
            )

    snap_sha = _canonical_sha256(
        {
            "verification_mode": verification_mode,
            "artifacts": [(a.label, a.byte_length, a.sha256, a.valid) for a in artifacts],
        }
    )
    return DonorFdtKernelSnapshot(
        verification_mode=verification_mode,
        read_only_access=READ_ONLY_DONOR_ACCESS,
        artifacts=tuple(artifacts),
        fx3_setting_dtb_ok=fx3_s_ok,
        fx3_boot_dtb_ok=fx3_b_ok,
        fx6_setting_dtb_ok=fx6_s_ok,
        fx3_kernel_ok=fx3_k_ok,
        fx6_kernel_detected_as_fx6=fx6_rejected_ok,
        fx3_kemco_ok=fx3_kemco_ok,
        fx6_kemco_ok=fx6_kemco_ok,
        snapshot_sha256=snap_sha,
    )


# ---------------------------------------------------------------------------
# Unified Phase 106 Suite Runner
# ---------------------------------------------------------------------------


def run_fdt_bootargs_and_kernel_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> FdtBootargsAndKernelSuiteReport:
    """Run all Phase 106 FDT/bootargs & ARM64 kernel verification drills in `< 0.5s`."""
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    require(PERSISTENT_WRITE_RELEASE is False, "persistent_write_release must stay False")
    require(ALLOW_BOOT_PARTITION_TARGETING is False, "allow_boot_partition_targeting must stay False")
    require(ALLOW_DESTRUCTIVE_FASTBOOT is False, "allow_destructive_fastboot must stay False")
    require(OTP_FUSE_TOUCHES == 0, "otp_fuse_touches must stay 0")
    require(PASSIVE_TX_BYTES_EMITTED == 0, "passive_tx_bytes_emitted must stay 0")
    require(PHYSICAL_DEVICE_WRITES == 0, "physical_device_writes must stay 0")

    t0 = time.monotonic()
    donor_snapshot = inspect_fdt_and_kernel_donors_readonly(force_clean_room=force_clean_room)

    # Pillar 1: Compliant Stage-B FDT + adversarial fail-closed bootargs/FDT drills
    valid_fdt = build_synthetic_fdt_blob(include_nop_token=True)
    stage_b_fdt_parse_report = parse_fdt_blob(valid_fdt)
    stage_b_bootargs_valid_report = audit_fdt_chosen_bootargs(valid_fdt)

    rw_fdt = build_synthetic_fdt_blob(
        bootargs="console=ttyAMA0,115200 root=/dev/mmcblk0p7 rw rootwait init=/sbin/init wdt.timeout=500"
    )
    rw_rep = audit_fdt_chosen_bootargs(rw_fdt)
    bootargs_reject_rw_emmc = (not rw_rep.passed) and (ERR_BOOTARGS_RW_EMMC_ROOTFS in rw_rep.error_codes)

    bad_init_fdt = build_synthetic_fdt_blob(
        bootargs="console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait init=/bin/sh wdt.timeout=500"
    )
    bad_init_rep = audit_fdt_chosen_bootargs(bad_init_fdt)
    bootargs_reject_bad_init = (not bad_init_rep.passed) and (
        ERR_BOOTARGS_UNVERIFIED_INIT_PATH in bad_init_rep.error_codes
    )

    mtd_fdt = build_synthetic_fdt_blob(
        bootargs=(
            "console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait init=/sbin/init "
            "mtdparts=emmc0:1m(boot)ro,-(rw)"
        )
    )
    mtd_rep = audit_fdt_chosen_bootargs(mtd_fdt)
    bootargs_reject_mtdparts = (not mtd_rep.passed) and (
        ERR_BOOTARGS_FORBIDDEN_REPARTITIONING in mtd_rep.error_codes
    )

    blk_fdt = build_synthetic_fdt_blob(
        bootargs=(
            "console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait init=/sbin/init "
            "blkdevparts=mmcblk0:16M(p1),32M(p2)"
        )
    )
    blk_rep = audit_fdt_chosen_bootargs(blk_fdt)
    bootargs_reject_blkdevparts = (not blk_rep.passed) and (
        ERR_BOOTARGS_FORBIDDEN_REPARTITIONING in blk_rep.error_codes
    )

    nowdt_fdt = build_synthetic_fdt_blob(
        bootargs="console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait init=/sbin/init nowatchdog"
    )
    nowdt_rep = audit_fdt_chosen_bootargs(nowdt_fdt)
    bootargs_reject_nowatchdog = (not nowdt_rep.passed) and (ERR_BOOTARGS_WDT_DISABLED in nowdt_rep.error_codes)

    bad_magic_fdt = b"\xde\xad\xbe\xef" + valid_fdt[4:]
    bad_magic_rep = parse_fdt_blob(bad_magic_fdt)
    fdt_reject_bad_magic = (not bad_magic_rep.valid) and (ERR_FDT_BAD_MAGIC in bad_magic_rep.error_codes)

    trunc_fdt_rep = parse_fdt_blob(valid_fdt[: len(valid_fdt) // 2])
    fdt_reject_truncated = (not trunc_fdt_rep.valid) and (ERR_FDT_BAD_TOTALSIZE in trunc_fdt_rep.error_codes)

    # Pillar 2: FX3 ARM64 Image + cross-SKU FX6 & malformed kernel drills
    fx3_kern_bytes = build_synthetic_arm64_kernel_image(sku="ILME-FX3")
    fx3_kernel_valid_report = audit_arm64_kernel_image(fx3_kern_bytes, label="stage_b_fx3_vmlinux.bin")

    fx6_kern_bytes = build_synthetic_arm64_kernel_image(sku="ILME-FX6")
    fx6_rep = audit_arm64_kernel_image(fx6_kern_bytes, label="cross_sku_fx6_vmlinux.bin")
    kernel_reject_fx6_transplant = (not fx6_rep.passed) and (
        ERR_KERNEL_CROSS_SKU_FX6_TRANSPLANT in fx6_rep.error_codes
    )

    bad_k_magic = build_synthetic_arm64_kernel_image(magic=0xDEADBEEF)
    bad_km_rep = audit_arm64_kernel_image(bad_k_magic, label="bad_magic_vmlinux.bin")
    kernel_reject_bad_magic = (not bad_km_rep.passed) and (ERR_KERNEL_BAD_ARM64_MAGIC in bad_km_rep.error_codes)

    trunc_k_rep = audit_arm64_kernel_image(fx3_kern_bytes[:48], label="truncated_vmlinux.bin")
    kernel_reject_truncated = (not trunc_k_rep.passed) and (ERR_KERNEL_TRUNCATED_HEADER in trunc_k_rep.error_codes)

    wrong_rel_k = build_synthetic_arm64_kernel_image(kernel_release="4.9.186-scel")
    wrong_rel_rep = audit_arm64_kernel_image(wrong_rel_k, label="wrong_release_vmlinux.bin")
    kernel_reject_wrong_release = (not wrong_rel_rep.passed) and (
        ERR_KERNEL_RELEASE_MISMATCH in wrong_rel_rep.error_codes
    )

    errors: List[str] = []
    checks = {
        "donor_fx3_setting_dtb_ok": donor_snapshot.fx3_setting_dtb_ok,
        "donor_fx3_boot_dtb_ok": donor_snapshot.fx3_boot_dtb_ok,
        "donor_fx6_setting_dtb_ok": donor_snapshot.fx6_setting_dtb_ok,
        "donor_fx3_kernel_ok": donor_snapshot.fx3_kernel_ok,
        "donor_fx6_kernel_detected_as_fx6": donor_snapshot.fx6_kernel_detected_as_fx6,
        "donor_fx3_kemco_ok": donor_snapshot.fx3_kemco_ok,
        "donor_fx6_kemco_ok": donor_snapshot.fx6_kemco_ok,
        "stage_b_fdt_parse_valid": stage_b_fdt_parse_report.valid,
        "stage_b_bootargs_valid": stage_b_bootargs_valid_report.passed,
        "bootargs_reject_rw_emmc": bootargs_reject_rw_emmc,
        "bootargs_reject_bad_init": bootargs_reject_bad_init,
        "bootargs_reject_mtdparts": bootargs_reject_mtdparts,
        "bootargs_reject_blkdevparts": bootargs_reject_blkdevparts,
        "bootargs_reject_nowatchdog": bootargs_reject_nowatchdog,
        "fdt_reject_bad_magic": fdt_reject_bad_magic,
        "fdt_reject_truncated": fdt_reject_truncated,
        "fx3_kernel_valid": fx3_kernel_valid_report.passed,
        "kernel_reject_fx6_transplant": kernel_reject_fx6_transplant,
        "kernel_reject_bad_magic": kernel_reject_bad_magic,
        "kernel_reject_truncated": kernel_reject_truncated,
        "kernel_reject_wrong_release": kernel_reject_wrong_release,
    }
    for name, ok in checks.items():
        if not ok:
            errors.append(f"SUITE_CHECK_FAILED:{name}")

    all_passed = (
        len(errors) == 0
        and (PERSISTENT_EMMC_WRITES_AUTHORIZED is False)
        and (PERSISTENT_WRITE_RELEASE is False)
        and (ALLOW_BOOT_PARTITION_TARGETING is False)
        and (ALLOW_DESTRUCTIVE_FASTBOOT is False)
        and (OTP_FUSE_TOUCHES == 0)
        and (PASSIVE_TX_BYTES_EMITTED == 0)
        and (PHYSICAL_DEVICE_WRITES == 0)
    )
    stage_b_boot_gate_ready = (
        stage_b_fdt_parse_report.valid
        and stage_b_bootargs_valid_report.passed
        and fx3_kernel_valid_report.passed
        and all_passed
    )

    suite_sha = _canonical_sha256(
        {
            "schema": FDT_BOOTARGS_KERNEL_SCHEMA,
            "version": FDT_BOOTARGS_KERNEL_VERSION,
            "verification_mode": donor_snapshot.verification_mode,
            "donor_snapshot_sha256": donor_snapshot.snapshot_sha256,
            "stage_b_fdt_sha256": stage_b_fdt_parse_report.blob_sha256,
            "fx3_kernel_sha256": fx3_kernel_valid_report.image_sha256,
            "checks": checks,
            "all_passed": all_passed,
        }
    )

    return FdtBootargsAndKernelSuiteReport(
        schema=FDT_BOOTARGS_KERNEL_SCHEMA,
        version=FDT_BOOTARGS_KERNEL_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_passed,
        status=STATUS_VERIFIED_FDT_KERNEL_GATE if all_passed else STATUS_FAIL_FDT_KERNEL_GATE,
        donor_snapshot=donor_snapshot,
        stage_b_fdt_parse_report=stage_b_fdt_parse_report,
        stage_b_bootargs_valid_report=stage_b_bootargs_valid_report,
        bootargs_reject_rw_emmc_passed=bootargs_reject_rw_emmc,
        bootargs_reject_bad_init_passed=bootargs_reject_bad_init,
        bootargs_reject_mtdparts_passed=bootargs_reject_mtdparts,
        bootargs_reject_blkdevparts_passed=bootargs_reject_blkdevparts,
        bootargs_reject_nowatchdog_passed=bootargs_reject_nowatchdog,
        fdt_reject_bad_magic_passed=fdt_reject_bad_magic,
        fdt_reject_truncated_passed=fdt_reject_truncated,
        fx3_kernel_valid_report=fx3_kernel_valid_report,
        kernel_reject_fx6_transplant_passed=kernel_reject_fx6_transplant,
        kernel_reject_bad_magic_passed=kernel_reject_bad_magic,
        kernel_reject_truncated_passed=kernel_reject_truncated,
        kernel_reject_wrong_release_passed=kernel_reject_wrong_release,
        stage_b_boot_gate_ready=stage_b_boot_gate_ready,
        suite_sha256=suite_sha,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        elapsed_seconds=round(time.monotonic() - t0, 6),
        errors=tuple(errors),
    )


__all__ = [
    "ALLOW_BOOT_PARTITION_TARGETING",
    "ALLOW_DESTRUCTIVE_FASTBOOT",
    "ALLOWED_VERIFIED_INIT_PATHS",
    "ARM64_FLAG_ENDIAN_MASK",
    "ARM64_FLAG_PAGE_SIZE_MASK",
    "ARM64_FLAG_PAGE_SIZE_SHIFT",
    "ARM64_FLAG_PHYS_PLACEMENT_BIT",
    "ARM64_IMAGE_HEADER_SIZE",
    "ARM64_IMAGE_MAGIC",
    "ARM64_IMAGE_MAGIC_U32",
    "ARM64_PAGE_SIZE_MAP",
    "CXD90057_COMPATIBLE",
    "CXD90057_DRAM_BASE",
    "CXD90057_DRAM_SIZE",
    "CXD90057_INITRD_BASE",
    "CXD90057_SOC_MODEL",
    "DEFAULT_SAFE_STAGE_B_BOOTARGS",
    "DONOR_FX3_BOOT_DTB_RELPATH",
    "DONOR_FX3_KEMCO_RELPATH",
    "DONOR_FX3_SETTING_DTB_RELPATH",
    "DONOR_FX3_VMLINUX_RELPATH",
    "DONOR_FX6_KEMCO_RELPATH",
    "DONOR_FX6_SETTING_DTB_RELPATH",
    "DONOR_FX6_VMLINUX_RELPATH",
    "EMMC_ROOT_DEVICE_PREFIXES",
    "ERR_BOOTARGS_FORBIDDEN_REPARTITIONING",
    "ERR_BOOTARGS_MALFORMED",
    "ERR_BOOTARGS_MISSING_OR_EMPTY",
    "ERR_BOOTARGS_MISSING_RO",
    "ERR_BOOTARGS_MISSING_ROOTWAIT",
    "ERR_BOOTARGS_RW_EMMC_ROOTFS",
    "ERR_BOOTARGS_UNVERIFIED_INIT_PATH",
    "ERR_BOOTARGS_WDT_DISABLED",
    "ERR_FDT_BAD_BOUNDS",
    "ERR_FDT_BAD_MAGIC",
    "ERR_FDT_BAD_MEM_RSVMAP",
    "ERR_FDT_BAD_STRING_OFFSET",
    "ERR_FDT_BAD_TOTALSIZE",
    "ERR_FDT_EMPTY_OR_TRUNCATED_HEADER",
    "ERR_FDT_MALFORMED_TOKENS",
    "ERR_FDT_MISSING_CHOSEN",
    "ERR_FDT_MISSING_END_TOKEN",
    "ERR_FDT_NONZERO_PADDING",
    "ERR_FDT_OVERLAPPING_REGIONS",
    "ERR_FDT_SOC_MISMATCH",
    "ERR_FDT_UNCLOSED_NODE",
    "ERR_FDT_UNKNOWN_TOKEN",
    "ERR_FDT_UNSUPPORTED_VERSION",
    "ERR_INITRD_ASYMMETRIC_BOUNDS",
    "ERR_INITRD_INVALID_CELL_SIZE",
    "ERR_INITRD_INVALID_RANGE",
    "ERR_INITRD_MISSING",
    "ERR_INITRD_SIZE_OUT_OF_BOUNDS",
    "ERR_KERNEL_BAD_ARM64_MAGIC",
    "ERR_KERNEL_BIG_ENDIAN_FORBIDDEN",
    "ERR_KERNEL_CROSS_SKU_FX6_TRANSPLANT",
    "ERR_KERNEL_INVALID_CODE0",
    "ERR_KERNEL_INVALID_TEXT_OFFSET",
    "ERR_KERNEL_NONZERO_RESERVED_FLAGS",
    "ERR_KERNEL_RELEASE_MISMATCH",
    "ERR_KERNEL_SHA256_MISMATCH",
    "ERR_KERNEL_SOC_MISMATCH",
    "ERR_KERNEL_TRUNCATED_HEADER",
    "ERR_KERNEL_TRUNCATED_IMAGE",
    "ERR_KERNEL_UNSUPPORTED_PAGE_SIZE",
    "ERR_KERNEL_ZERO_IMAGE_SIZE",
    "EXPECTED_ARM64_IMAGE_SIZE",
    "EXPECTED_ARM64_TEXT_OFFSET",
    "EXPECTED_FX3_KERNEL_RELEASE",
    "FDT_BEGIN_NODE",
    "FDT_BOOTARGS_KERNEL_SCHEMA",
    "FDT_BOOTARGS_KERNEL_VERSION",
    "FDT_END",
    "FDT_END_NODE",
    "FDT_HEADER_SIZE",
    "FDT_MAGIC",
    "FDT_MAGIC_U32",
    "FDT_MAX_BLOB_BYTES",
    "FDT_MIN_COMP_VERSION",
    "FDT_NOP",
    "FDT_PROP",
    "FDT_VERSION_17",
    "FORBIDDEN_REPARTITION_KEYS",
    "FORBIDDEN_WDT_DISABLE_TOKENS",
    "FX3_KEMCO_INITRD_SIZE",
    "FX3_KERNEL_BUILD_HOST",
    "FX3_KERNEL_MIN_FILE_BYTES",
    "FX3_KERNEL_TOOLCHAIN_MARKER",
    "FX6_KEMCO_INITRD_SIZE",
    "FX6_KERNEL_BUILD_HOST",
    "FX6_KERNEL_TOOLCHAIN_MARKER",
    "MAX_INITRD_WINDOW_BYTES",
    "OTP_FUSE_TOUCHES",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHYSICAL_DEVICE_WRITES",
    "PINNED_CXD90057_BOOT_DTB_SHA256",
    "PINNED_CXD90057_SETTING_DTB_SHA256",
    "PINNED_FX3_VMLINUX_SHA256",
    "PINNED_FX6_VMLINUX_SHA256",
    "READ_ONLY_DONOR_ACCESS",
    "STATUS_FAIL_FDT_KERNEL_GATE",
    "STATUS_REJECTED_ARM64_KERNEL",
    "STATUS_REJECTED_BOOTARGS_FIREWALL",
    "STATUS_REJECTED_FDT_BLOB",
    "STATUS_VERIFIED_ARM64_KERNEL",
    "STATUS_VERIFIED_BOOTARGS_FIREWALL",
    "STATUS_VERIFIED_FDT_BLOB",
    "STATUS_VERIFIED_FDT_KERNEL_GATE",
    "Arm64KernelImageReport",
    "DonorFdtKernelArtifactInfo",
    "DonorFdtKernelSnapshot",
    "FdtBootargsAndKernelSuiteReport",
    "FdtBootargsAuditReport",
    "FdtHeaderInfo",
    "FdtNodeInfo",
    "FdtParseReport",
    "FdtPropertyInfo",
    "FdtReserveEntryInfo",
    "audit_arm64_kernel_image",
    "audit_fdt_chosen_bootargs",
    "build_synthetic_arm64_kernel_image",
    "build_synthetic_fdt_blob",
    "inspect_fdt_and_kernel_donors_readonly",
    "parse_fdt_blob",
    "run_fdt_bootargs_and_kernel_suite",
]
