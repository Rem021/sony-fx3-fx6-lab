"""Phase 138 — Reversible A7C-II-Style `/dev/nflasha15` (`ext2` `/usr`) File-Level
Atomic Stage-B Installer Dry-Run, Hash-Rollback Engine & `p1` Single-Shot
Emergency Rescue Verifier (Pillar 16).

Provides three deterministic, RAM-only, read-only-donor verification pillars for
real physical `ILME-FX3` (`7.02`, `0x91030080` / `ALCIN_UUD`) Stage-B execution
readiness while strictly locking `persistent_emmc_writes_authorized = False`,
`physical_device_writes = 0`, and zero cross-model raw partition overwrite:

1. **Read-Only (`O_RDONLY`) FX3 `7.02` & FX6 `6.01` Donor Inspection**:
   - Opens local FX3 `7.02` (`partinf.conf`, `mount.conf`, `p2/setting/kemco.txt`,
     `nflasha15.img` bounded 4 KiB ext2 superblock, `im.elf`) and FX6 `6.01`
     (`partinf.conf`, `mount.conf`, `p2/setting/kemco.txt`, `nflasha1/boot/kemco.txt`,
     `nflasha1/boot/loadaddr.txt`, `nflasha15` bounded 4 KiB ext2 superblock,
     `im.elf`) strictly via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`.
   - Deterministically falls back to pinned `CLEAN_ROOM_SYNTHETIC` metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent.
   - Emits zero raw proprietary firmware bytes or keys in JSON reports.

2. **Pillar A — `EXT2_NFLASHA15_ATOMIC_INSTALLER_AND_ROLLBACK`**:
   - Validates `/dev/nflasha15` (`ext2` superblock `s_magic == 0xEF53`, `500 MiB`
     slot `524,288,000 B`, `479,846,400 B` FX3 image, free inode & block
     headroom `>= 32 MiB`).
   - Enforces `/dev/nflashaN` / `/dev/cnflashaN` (`crypt-emmc.ko` SPACC transparent
     encryption) for `type=5, flag=1` partitions (`p3`, `p8`, `p15`, `p23`),
     **HARD-BLOCKING** any raw plaintext write to `/dev/pnflasha3/8/15/23`.
   - Enforces the SD-card escape-hatch wrapper:
     `if [ ! -f /mnt/sd/FX6_STAGEB_BOOT.MANIFEST ]; then exec /usr/bin/im.elf.orig "$@"; fi`
   - Simulates full in-memory A7C-II (`installer.c`) atomic install (`ro` check ->
     verify stock SHA-256 -> `remount rw` -> save `.orig` backup -> write wrapper/hook
     -> full read-back SHA-256 verify -> automatic rollback on bit-flip / short-write
     -> `remount ro`), proving `100%` byte-identical restoration to stock SHA-256
     and `ro` remount.

3. **Pillar B — `P1_P3_MUTUAL_EXCLUSION_AND_ONESHOT_RESCUE_INITRD`**:
   - Enforces the **Golden Mutual-Exclusion Law**: `p1` (`23.94 MiB` VFAT
     `/dev/nflasha1`) and `p3` (`75 MiB` VFAT `/dev/nflasha3`) MUST NEVER be
     modified in the same transaction; at least one untouched bootable partition
     always remains intact.
   - Verifies `p1` single-shot diagnostic config: `p1:/dat2 == "91030080"`
     preserved, `p1:/dat3` preserved, `p1:/boot/loadaddr.txt` valid,
     `p1:/boot/kemco.txt` enforcing `cfg.uart=1` & `console=ttyAMA0,460800n8`,
     and `/sbin/init` line-1 `rm -f /setting/updater/mode* && sync` before any
     other action, hard-blocking FX6 `cfg.uart=9` blind UART blackout or missing
     `mode*` clear.

4. **Pillar C — `TIER0_PRECONDITION_AND_HARDWARE_WRITE_LOCK`**:
   - Requires verified Tier-0 backup receipt (`sector0`, `p1`, `p2`, `p6`, `p12`,
     `p18`, SPI NOR `ddrtraining.dat`) with `readback_verified == True` before even
     dry-run readiness passes, while keeping `persistent_emmc_writes_authorized = False`
     and `physical_device_writes = 0` hard-locked.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
import re
import stat
import struct
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .files import is_forced_clean_room, local_path, read_file, require, resolve_donor_path


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_EXT2_P1_RESCUE_SCHEMA: str = "fx3-realhw-ext2-installer-and-p1-rescue-verifier-v1"
REALHW_EXT2_P1_RESCUE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True
OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0

FX3_MODEL_ID_STR: str = "91030080"
FX6_MODEL_ID_STR: str = "91040086"
FX3_EXPECTED_REGION_TAG: str = "US_JP_EU_CN_NTSC"

# Partition & Geometry Constants (512 B sectors)
SECTOR_SIZE_BYTES: int = 512
P1_VFAT_CAPACITY_BYTES: int = 25100288  # 0x0000BF80 * 512 (~23.94 MiB)
P3_VFAT_CAPACITY_BYTES: int = 78643200  # 0x00026000 * 512 (75 MiB)
P15_EXT2_SLOT_BYTES: int = 524288000    # 0x000FA000 * 512 (500 MiB)
FX3_P15_IMAGE_BYTES: int = 479846400
FX6_P15_IMAGE_BYTES: int = 445843456
EXT2_SUPER_MAGIC: int = 0xEF53
EXT2_SUPERBLOCK_OFFSET: int = 1024
EXT2_SUPERBLOCK_SIZE: int = 1024
EXT2_MIN_HEADROOM_BYTES: int = 32 * 1024 * 1024  # 33,554,432 B (32 MiB)
EXT2_MIN_FREE_INODES: int = 256

# Encrypted partitions in partinf.conf (type=5, flag=1) -> must use /dev/nflashaN or /dev/cnflashaN
ENCRYPTED_TYPE5_PARTITIONS: Tuple[int, ...] = (3, 4, 5, 7, 8, 12, 15, 20, 21, 23)
CRITICAL_CRYPTO_BOOT_AND_USR_PARTITIONS: Tuple[int, ...] = (3, 8, 15, 23)
PLAINTEXT_VFAT_PARTITIONS: Tuple[int, ...] = (1, 2, 6, 10, 11, 13, 18)

# Required SD Escape-Hatch Snippet for /usr/bin/im.elf wrapper
SD_ESCAPE_HATCH_MANIFEST_PATH: str = "/mnt/sd/FX6_STAGEB_BOOT.MANIFEST"
SD_ESCAPE_HATCH_EXEC_LINE: str = (
    'if [ ! -f /mnt/sd/FX6_STAGEB_BOOT.MANIFEST ]; then exec /usr/bin/im.elf.orig "$@"; fi'
)
DEFAULT_P1_LOADADDR_TEXT: str = "0x400080000,0x408000000,0x400001000,0x400002000"

# Status & Error Codes
STATUS_VERIFIED_REALHW_EXT2_P1_GATE: str = "VERIFIED_REALHW_EXT2_INSTALLER_AND_P1_RESCUE_GATE"
STATUS_FAIL_REALHW_EXT2_P1_GATE: str = "FAIL_REALHW_EXT2_INSTALLER_AND_P1_RESCUE_GATE"

STATUS_VERIFIED_EXT2_INSTALLER_PILLAR: str = "VERIFIED_EXT2_NFLASHA15_ATOMIC_INSTALLER"
STATUS_REJECTED_EXT2_INSTALLER_PILLAR: str = "REJECTED_EXT2_NFLASHA15_ATOMIC_INSTALLER"
STATUS_ROLLED_BACK_TO_STOCK_EXACT: str = "ROLLED_BACK_TO_STOCK_SHA256_EXACT"

STATUS_VERIFIED_P1_RESCUE_PILLAR: str = "VERIFIED_P1_P3_MUTUAL_EXCLUSION_AND_ONESHOT_RESCUE"
STATUS_REJECTED_P1_RESCUE_PILLAR: str = "REJECTED_P1_P3_MUTUAL_EXCLUSION_AND_ONESHOT_RESCUE"

STATUS_VERIFIED_TIER0_LOCK_PILLAR: str = "VERIFIED_TIER0_PRECONDITION_AND_HARDWARE_WRITE_LOCK"
STATUS_REJECTED_TIER0_LOCK_PILLAR: str = "REJECTED_TIER0_PRECONDITION_AND_HARDWARE_WRITE_LOCK"

# Required Firewall Error Codes
BLOCKED_RAW_PNFLASHA_PLAINTEXT_HAZARD: str = "BLOCKED_RAW_PNFLASHA_PLAINTEXT_CIPHERTEXT_CORRUPTION"
BLOCKED_MISSING_SD_ESCAPE_HATCH_WRAPPER: str = "BLOCKED_MISSING_SD_ESCAPE_HATCH_WRAPPER"
BLOCKED_STOCK_SHA256_MISMATCH: str = "BLOCKED_STOCK_TARGET_SHA256_MISMATCH"
BLOCKED_READBACK_SHA256_MISMATCH_ROLLED_BACK: str = "BLOCKED_READBACK_SHA256_MISMATCH_ROLLED_BACK"
BLOCKED_SHORT_WRITE_ROLLED_BACK: str = "BLOCKED_SHORT_WRITE_ROLLED_BACK"
ERR_EXT2_BAD_MAGIC: str = "ERR_EXT2_INVALID_SUPERBLOCK_MAGIC"
ERR_EXT2_SLOT_OVERFLOW: str = "ERR_EXT2_IMAGE_EXCEEDS_500MIB_SLOT"
ERR_EXT2_INSUFFICIENT_HEADROOM: str = "ERR_EXT2_INSUFFICIENT_HEADROOM_LT_32MIB"
ERR_EXT2_INSUFFICIENT_INODES: str = "ERR_EXT2_INSUFFICIENT_FREE_INODES"

BLOCKED_DUAL_BOOT_PARTITION_SIMULTANEOUS_WRITE: str = (
    "BLOCKED_P1_P3_MUTUAL_EXCLUSION_VIOLATION_NO_DUAL_WRITE"
)
BLOCKED_FX6_UART9_BLIND_BLACKOUT: str = "BLOCKED_FX6_CFG_UART9_BLIND_SERIAL_BLACKOUT"
BLOCKED_P1_MISSING_SERIAL_CONSOLE: str = "BLOCKED_P1_MISSING_TTYAMA0_460800_CONSOLE"
BLOCKED_MISSING_FIRST_LINE_MODE_CLEAR_SYNC: str = (
    "BLOCKED_INITRD_MISSING_FIRST_LINE_MODE_CLEAR_AND_SYNC"
)
BLOCKED_P1_DAT2_MODEL_ID_CORRUPTED: str = "BLOCKED_P1_DAT2_MODEL_ID_NOT_91030080"
BLOCKED_P1_DAT3_REGION_CORRUPTED: str = "BLOCKED_P1_DAT3_REGION_MISSING_OR_TAMPERED"
BLOCKED_P1_LOADADDR_INVALID: str = "BLOCKED_P1_LOADADDR_OR_CAPACITY_INVALID"

BLOCKED_MISSING_TIER0_BACKUP_PRECONDITION: str = "BLOCKED_MISSING_TIER0_BACKUP_PRECONDITION"
BLOCKED_TIER0_READBACK_UNVERIFIED: str = "BLOCKED_TIER0_READBACK_SHA256_UNVERIFIED"
BLOCKED_HARDWARE_EMMC_WRITE_LOCKED: str = "BLOCKED_PERSISTENT_EMMC_WRITES_HARD_LOCKED_FALSE"

# Required Tier-0 Artifacts
REQUIRED_TIER0_ARTIFACT_NAMES: Tuple[str, ...] = (
    "sector0",
    "p1",
    "p2",
    "p6",
    "p12",
    "p18",
    "spi_nor_ddrtraining",
)

TIER0_ARTIFACT_EXPECTED_SIZES: Dict[str, Tuple[int, int]] = {
    "sector0": (512, 512),
    "p1": (25100288, 25100288),
    "p2": (20971520, 20971520),
    "p6": (26214400, 26214400),
    "p12": (41943040, 41943040),
    "p18": (20971520, 20971520),
    "spi_nor_ddrtraining": (1024, 131072),
}

# Local Donor Relative Paths (strictly read-only via os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
P138_DONOR_FX3_PARTINF_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0300_partconf/partinf.conf"
)
P138_DONOR_FX6_PARTINF_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0300_partconf/partinf.conf"
)
P138_DONOR_FX3_MOUNT_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0100_config/mount.conf"
)
P138_DONOR_FX6_MOUNT_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0100_config/mount.conf"
)
P138_DONOR_FX3_P2_KEMCO_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0800_appli/setting/kemco.txt"
)
P138_DONOR_FX6_P2_KEMCO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0800_appli/setting/kemco.txt"
)
P138_DONOR_FX6_P1_KEMCO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha1/boot/kemco.txt"
)
P138_DONOR_FX6_P1_LOADADDR_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha1/boot/loadaddr.txt"
)
P138_DONOR_FX3_NFLASHA15_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/nflasha15.img"
)
P138_DONOR_FX6_NFLASHA15_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0700_part_image/dev/nflasha15"
)
P138_DONOR_FX3_IM_ELF_RELPATH: str = (
    "sony-firmware-20261024/stage183-request-consumer-and-early-entry/"
    "evidence/usb-main-dependency/originals/bin/im.elf"
)
P138_DONOR_FX6_IM_ELF_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/bin/im.elf"
)

# Pinned Donor Integrity Anchors (Zero Proprietary Keys / Zero Raw Firmware Bytes)
P138_PINNED_FX3_PARTINF_BYTES: int = 3999
P138_PINNED_FX3_PARTINF_SHA256: str = "3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189"
P138_PINNED_FX6_PARTINF_BYTES: int = 3990
P138_PINNED_FX6_PARTINF_SHA256: str = "e05b53d1f739968510dd24d62cd38426772fe3e50fe463a3d260c5f113e17ec9"
P138_PINNED_FX3_MOUNT_BYTES: int = 1248
P138_PINNED_FX3_MOUNT_SHA256: str = "ea0132091f3bb8d675b3ae7aecfbb1ca2459864a2e2812c0f7dd66fbb877d1a3"
P138_PINNED_FX6_MOUNT_BYTES: int = 1267
P138_PINNED_FX6_MOUNT_SHA256: str = "221d6a59ddc87623342ac413072405a95151980e692b79116e5924d03e9a049b"
P138_PINNED_FX3_P2_KEMCO_BYTES: int = 1736
P138_PINNED_FX3_P2_KEMCO_SHA256: str = "555454e8b7db1461d6494e9ca9eb21f00918475af02557bc6ca3cedd309bcaf2"
P138_PINNED_FX6_P2_KEMCO_BYTES: int = 1788
P138_PINNED_FX6_P2_KEMCO_SHA256: str = "6a609ee6b96c2ed0db47e9056ca67dfd8d419f9445302dacf09c262eace3b4fc"
P138_PINNED_FX6_P1_KEMCO_BYTES: int = 933
P138_PINNED_FX6_P1_KEMCO_SHA256: str = "e7763ad93a721f297670f13abc452cf467c0d2c344888d4e55ead2440c295950"
P138_PINNED_FX6_P1_LOADADDR_BYTES: int = 48
P138_PINNED_FX6_P1_LOADADDR_SHA256: str = "8c7cc8eb65c40311172f4bf1dc591fe3bcbc1efe689ededdd225142139881452"
P138_PINNED_FX3_NFLASHA15_BYTES: int = 479846400
P138_PINNED_FX3_NFLASHA15_HDR4K_SHA256: str = "6d05ebbd28c554d1d9dcc54503face9af111170befaf2ca2a19c52d7bd8910d6"
P138_PINNED_FX6_NFLASHA15_BYTES: int = 445843456
P138_PINNED_FX6_NFLASHA15_HDR4K_SHA256: str = "3ba0016fbb2debca3b6eab5aef579f2af705fe7476846397f4edaac518cc2876"
P138_PINNED_FX3_IM_ELF_BYTES: int = 40920
P138_PINNED_FX3_IM_ELF_SHA256: str = "5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91"
P138_PINNED_FX6_IM_ELF_BYTES: int = 40920
P138_PINNED_FX6_IM_ELF_SHA256: str = "87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec"

# Scenario IDs
EXT2_INSTALLER_SCENARIO_IDS: Tuple[str, ...] = (
    "EI1_HEALTHY_ATOMIC_INSTALL_AND_CLEAN_ROLLBACK",
    "EI2_INJECTED_BITFLIP_TRIGGERS_EXACT_ROLLBACK",
    "EI3_INJECTED_SHORT_WRITE_TRIGGERS_EXACT_ROLLBACK",
    "EI4_RAW_PNFLASHA15_PLAINTEXT_WRITE_BLOCKED",
    "EI5_STOCK_HASH_MISMATCH_OR_LOW_HEADROOM_ABORTED",
    "EI6_MISSING_SD_ESCAPE_HATCH_WRAPPER_BLOCKED",
)

P1_RESCUE_SCENARIO_IDS: Tuple[str, ...] = (
    "PR1_HEALTHY_P1_ONESHOT_DIAGNOSTIC_WITH_P3_INTACT",
    "PR2_SIMULTANEOUS_P1_AND_P3_WRITE_BLOCKED",
    "PR3_FX6_CFG_UART9_BLACKOUT_BLOCKED",
    "PR4_MISSING_FIRST_LINE_MODE_CLEAR_SYNC_BLOCKED",
    "PR5_CORRUPTED_OR_OVERWRITTEN_DAT2_DAT3_BLOCKED",
    "PR6_RAW_PNFLASHA3_WRITE_ON_P3_BANK_BLOCKED",
)

TIER0_LOCK_SCENARIO_IDS: Tuple[str, ...] = (
    "T0L1_COMPLETE_TIER0_RECEIPT_AND_WRITE_LOCK_PASSES",
    "T0L2_MISSING_TIER0_BACKUP_ARTIFACT_BLOCKED",
    "T0L3_UNVERIFIED_TIER0_READBACK_SHA256_BLOCKED",
    "T0L4_PERSISTENT_EMMC_WRITE_UNLOCK_ATTEMPT_BLOCKED",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_sha256(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(payload).hexdigest()


def _is_hex64(val: str) -> bool:
    return isinstance(val, str) and len(val) == 64 and all(c in "0123456789abcdefABCDEF" for c in val)


def _read_bounded_prefix_readonly(path_str: str, max_bytes: int) -> Tuple[bytes, int]:
    """Read up to `max_bytes` from a regular single-link file strictly via os.O_RDONLY."""
    p = local_path(path_str, allow_donor_roots=True)
    require(hasattr(os, "O_NOFOLLOW"), "POSIX O_NOFOLLOW required")
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, "regular single-link file required")
        with os.fdopen(os.dup(fd), "rb") as f:
            prefix = f.read(max_bytes)
        after = os.fstat(fd)
        require(st.st_size == after.st_size and st.st_ino == after.st_ino, "donor changed during read")
        return prefix, st.st_size
    finally:
        os.close(fd)


def _extract_cfg_uart(kemco_text: str) -> Optional[int]:
    m = re.search(r"\bcfg\.uart=(\d+)\b", kemco_text)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Structured Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RealHwDonorArtifactDigest:
    label: str
    sku: str
    source_mode: str
    byte_length: int
    sha256_digest: str
    bounded_prefix_only: bool
    ext2_magic_hex: str = ""
    cfg_uart_value: Optional[int] = None


@dataclass(frozen=True)
class Ext2SuperblockMetadata:
    s_magic: int
    s_magic_hex: str
    s_inodes_count: int
    s_blocks_count: int
    s_r_blocks_count: int
    s_free_blocks_count: int
    s_free_inodes_count: int
    s_first_data_block: int
    block_size_bytes: int
    image_bytes: int
    partition_slot_bytes: int
    ext2_internal_free_bytes: int
    partition_tail_headroom_bytes: int
    effective_headroom_bytes: int


@dataclass(frozen=True)
class RealHwDonorSnapshot:
    verification_mode: str
    read_only_access: bool
    cross_sku_distinct: bool
    fx3_p15_bytes: int
    fx6_p15_bytes: int
    fx3_p15_ext2_magic_hex: str
    fx6_p15_ext2_magic_hex: str
    fx3_p15_free_inodes: int
    fx3_p15_effective_headroom_bytes: int
    fx6_p15_free_inodes: int
    fx6_p15_effective_headroom_bytes: int
    fx3_p2_cfg_uart: int
    fx6_p2_cfg_uart: int
    fx6_p1_cfg_uart: int
    fx6_p1_loadaddr_sha256: str
    fx3_im_elf_sha256: str
    fx6_im_elf_sha256: str
    artifacts: Tuple[RealHwDonorArtifactDigest, ...]
    snapshot_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CryptoBlockDeviceDecision:
    allowed: bool
    device_path: str
    partition_number: int
    is_encrypted_type5: bool
    uses_transparent_crypto_layer: bool
    error_code: str
    reason: str


@dataclass(frozen=True)
class SdEscapeHatchAuditResult:
    passed: bool
    has_shebang: bool
    checks_manifest_path: bool
    execs_orig_binary: bool
    error_code: str
    reason: str


@dataclass(frozen=True)
class AtomicExt2InstallTransactionReport:
    passed: bool
    status: str
    scenario_id: str
    device_path: str
    target_path: str
    backup_path: str
    fault_injected: str
    stock_sha256_before: str
    final_target_sha256: str
    final_backup_sha256: str
    stock_restored_exact: bool
    final_mount_state: str
    ro_remount_verified: bool
    phases_executed: Tuple[str, ...]
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Ext2Installer6ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[AtomicExt2InstallTransactionReport, ...]
    physical_device_writes: int
    errors: Tuple[str, ...]
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MutualExclusionDecision:
    allowed: bool
    touches_p1: bool
    touches_p3: bool
    p1_intact: bool
    p3_intact: bool
    untouched_bootable_banks: Tuple[str, ...]
    error_codes: Tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class P1OneshotRescueProposal:
    scenario_id: str
    touches_p1: bool
    touches_p3: bool
    p1_device_path: str
    p3_device_path: str
    p1_dat2_value: str
    p1_dat3_value: str
    p1_dat3_expected: str
    p1_kemco_text: str
    p1_loadaddr_text: str
    p1_payload_bytes: int
    initrd_sbin_init_text: str


@dataclass(frozen=True)
class P1OneshotRescueReport:
    passed: bool
    status: str
    scenario_id: str
    mutual_exclusion_ok: bool
    untouched_bootable_banks: Tuple[str, ...]
    dat2_preserved: bool
    dat3_preserved: bool
    cfg_uart: Optional[int]
    console_uart_ok: bool
    first_line_mode_clear_sync_ok: bool
    loadaddr_ok: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P1Rescue6ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[P1OneshotRescueReport, ...]
    physical_device_writes: int
    errors: Tuple[str, ...]
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Tier0BackupArtifactEntry:
    name: str
    byte_length: int
    sha256_digest: str
    readback_verified: bool
    source_mode: str = "O_RDONLY"


@dataclass(frozen=True)
class Tier0BackupReceipt:
    body_id_tag: str
    model_id: str
    artifacts: Tuple[Tier0BackupArtifactEntry, ...]
    persistent_emmc_writes_requested: bool = False


@dataclass(frozen=True)
class Tier0PreconditionAndLockReport:
    passed: bool
    status: str
    scenario_id: str
    present_artifacts: Tuple[str, ...]
    missing_artifacts: Tuple[str, ...]
    unverified_artifacts: Tuple[str, ...]
    tier0_complete: bool
    dry_run_readiness_permitted: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_device_writes: int
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Tier0Lock4ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[Tier0PreconditionAndLockReport, ...]
    physical_device_writes: int
    errors: Tuple[str, ...]
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealHwExt2InstallerAndP1RescueSuiteReport:
    schema: str
    version: str
    status: str
    verification_mode: str
    all_passed: bool
    read_only_donor_access: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    passive_tx_bytes_emitted: int
    physical_device_writes: int
    donor_snapshot: RealHwDonorSnapshot
    pillar_a_ext2_installer_6_scenarios: Ext2Installer6ScenarioSuiteResult
    pillar_b_p1_rescue_6_scenarios: P1Rescue6ScenarioSuiteResult
    pillar_c_tier0_lock_4_scenarios: Tier0Lock4ScenarioSuiteResult
    suite_sha256: str
    elapsed_seconds: float
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Donor Inspection (O_RDONLY) + Deterministic Clean-Room Fallback
# ---------------------------------------------------------------------------


def parse_ext2_superblock_bytes(
    header_bytes: bytes,
    *,
    partition_slot_bytes: int = P15_EXT2_SLOT_BYTES,
) -> Ext2SuperblockMetadata:
    """Parse an ext2 superblock at offset 1024 and verify slot/headroom fields."""
    if len(header_bytes) < EXT2_SUPERBLOCK_OFFSET + EXT2_SUPERBLOCK_SIZE:
        raise ValueError(f"{ERR_EXT2_BAD_MAGIC}: header truncated ({len(header_bytes)} B)")
    sb = header_bytes[EXT2_SUPERBLOCK_OFFSET : EXT2_SUPERBLOCK_OFFSET + EXT2_SUPERBLOCK_SIZE]
    (
        s_inodes_count,
        s_blocks_count,
        s_r_blocks_count,
        s_free_blocks_count,
        s_free_inodes_count,
        s_first_data_block,
        s_log_block_size,
    ) = struct.unpack_from("<7I", sb, 0)
    (s_magic,) = struct.unpack_from("<H", sb, 56)
    if s_magic != EXT2_SUPER_MAGIC:
        raise ValueError(f"{ERR_EXT2_BAD_MAGIC}: got 0x{s_magic:04x}, expected 0x{EXT2_SUPER_MAGIC:04x}")
    if s_log_block_size > 6:
        raise ValueError(f"{ERR_EXT2_BAD_MAGIC}: invalid s_log_block_size={s_log_block_size}")
    block_size = 1024 << s_log_block_size
    image_bytes = s_blocks_count * block_size
    if image_bytes > partition_slot_bytes:
        raise ValueError(
            f"{ERR_EXT2_SLOT_OVERFLOW}: image_bytes={image_bytes} > slot={partition_slot_bytes}"
        )
    internal_free = s_free_blocks_count * block_size
    tail_headroom = partition_slot_bytes - image_bytes
    effective_headroom = internal_free + tail_headroom
    return Ext2SuperblockMetadata(
        s_magic=s_magic,
        s_magic_hex=f"0x{s_magic:04x}",
        s_inodes_count=s_inodes_count,
        s_blocks_count=s_blocks_count,
        s_r_blocks_count=s_r_blocks_count,
        s_free_blocks_count=s_free_blocks_count,
        s_free_inodes_count=s_free_inodes_count,
        s_first_data_block=s_first_data_block,
        block_size_bytes=block_size,
        image_bytes=image_bytes,
        partition_slot_bytes=partition_slot_bytes,
        ext2_internal_free_bytes=internal_free,
        partition_tail_headroom_bytes=tail_headroom,
        effective_headroom_bytes=effective_headroom,
    )


def build_synthetic_ext2_superblock_header(
    *,
    s_magic: int = EXT2_SUPER_MAGIC,
    s_inodes_count: int = 117392,
    s_free_inodes_count: int = 116467,
    s_blocks_count: int = 468600,
    s_free_blocks_count: int = 23430,
    s_r_blocks_count: int = 0,
    s_first_data_block: int = 1,
    s_log_block_size: int = 0,
) -> bytes:
    """Build a deterministic 4 KiB synthetic ext2 boot/superblock header in RAM."""
    buf = bytearray(4096)
    struct.pack_into(
        "<7I",
        buf,
        EXT2_SUPERBLOCK_OFFSET,
        s_inodes_count,
        s_blocks_count,
        s_r_blocks_count,
        s_free_blocks_count,
        s_free_inodes_count,
        s_first_data_block,
        s_log_block_size,
    )
    struct.pack_into("<H", buf, EXT2_SUPERBLOCK_OFFSET + 56, s_magic)
    return bytes(buf)


def inspect_realhw_ext2_and_p1_donors_readonly(
    *,
    force_clean_room: Optional[bool] = None,
) -> RealHwDonorSnapshot:
    """Inspect FX3 7.02 and FX6 6.01 donors strictly via os.O_RDONLY or return pinned clean-room metadata."""
    clean_forced = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)

    rel_map = {
        "fx3_partinf": P138_DONOR_FX3_PARTINF_RELPATH,
        "fx6_partinf": P138_DONOR_FX6_PARTINF_RELPATH,
        "fx3_mount": P138_DONOR_FX3_MOUNT_RELPATH,
        "fx6_mount": P138_DONOR_FX6_MOUNT_RELPATH,
        "fx3_p2_kemco": P138_DONOR_FX3_P2_KEMCO_RELPATH,
        "fx6_p2_kemco": P138_DONOR_FX6_P2_KEMCO_RELPATH,
        "fx6_p1_kemco": P138_DONOR_FX6_P1_KEMCO_RELPATH,
        "fx6_p1_loadaddr": P138_DONOR_FX6_P1_LOADADDR_RELPATH,
        "fx3_nflasha15": P138_DONOR_FX3_NFLASHA15_RELPATH,
        "fx6_nflasha15": P138_DONOR_FX6_NFLASHA15_RELPATH,
        "fx3_im_elf": P138_DONOR_FX3_IM_ELF_RELPATH,
        "fx6_im_elf": P138_DONOR_FX6_IM_ELF_RELPATH,
    }
    resolved = {} if clean_forced else {k: resolve_donor_path(v, require_file=True) for k, v in rel_map.items()}
    all_present = (not clean_forced) and all(p.is_file() for p in resolved.values())

    if not all_present:
        fx3_sb = parse_ext2_superblock_bytes(build_synthetic_ext2_superblock_header())
        fx6_sb = parse_ext2_superblock_bytes(
            build_synthetic_ext2_superblock_header(
                s_inodes_count=108864,
                s_free_inodes_count=107981,
                s_blocks_count=435392,
                s_free_blocks_count=33473,
            )
        )
        artifacts = (
            RealHwDonorArtifactDigest("fx3_v702_partinf_conf", "ILME-FX3", "CLEAN_ROOM_SYNTHETIC", P138_PINNED_FX3_PARTINF_BYTES, P138_PINNED_FX3_PARTINF_SHA256, False),
            RealHwDonorArtifactDigest("fx6_v601_partinf_conf", "ILME-FX6", "CLEAN_ROOM_SYNTHETIC", P138_PINNED_FX6_PARTINF_BYTES, P138_PINNED_FX6_PARTINF_SHA256, False),
            RealHwDonorArtifactDigest("fx3_v702_mount_conf", "ILME-FX3", "CLEAN_ROOM_SYNTHETIC", P138_PINNED_FX3_MOUNT_BYTES, P138_PINNED_FX3_MOUNT_SHA256, False),
            RealHwDonorArtifactDigest("fx6_v601_mount_conf", "ILME-FX6", "CLEAN_ROOM_SYNTHETIC", P138_PINNED_FX6_MOUNT_BYTES, P138_PINNED_FX6_MOUNT_SHA256, False),
            RealHwDonorArtifactDigest("fx3_v702_p2_kemco_txt", "ILME-FX3", "CLEAN_ROOM_SYNTHETIC", P138_PINNED_FX3_P2_KEMCO_BYTES, P138_PINNED_FX3_P2_KEMCO_SHA256, False, cfg_uart_value=1),
            RealHwDonorArtifactDigest("fx6_v601_p2_kemco_txt", "ILME-FX6", "CLEAN_ROOM_SYNTHETIC", P138_PINNED_FX6_P2_KEMCO_BYTES, P138_PINNED_FX6_P2_KEMCO_SHA256, False, cfg_uart_value=9),
            RealHwDonorArtifactDigest("fx6_v601_p1_kemco_txt", "ILME-FX6", "CLEAN_ROOM_SYNTHETIC", P138_PINNED_FX6_P1_KEMCO_BYTES, P138_PINNED_FX6_P1_KEMCO_SHA256, False, cfg_uart_value=9),
            RealHwDonorArtifactDigest("fx6_v601_p1_loadaddr_txt", "ILME-FX6", "CLEAN_ROOM_SYNTHETIC", P138_PINNED_FX6_P1_LOADADDR_BYTES, P138_PINNED_FX6_P1_LOADADDR_SHA256, False),
            RealHwDonorArtifactDigest("fx3_v702_nflasha15_ext2_hdr4k", "ILME-FX3", "CLEAN_ROOM_SYNTHETIC", P138_PINNED_FX3_NFLASHA15_BYTES, P138_PINNED_FX3_NFLASHA15_HDR4K_SHA256, True, ext2_magic_hex=fx3_sb.s_magic_hex),
            RealHwDonorArtifactDigest("fx6_v601_nflasha15_ext2_hdr4k", "ILME-FX6", "CLEAN_ROOM_SYNTHETIC", P138_PINNED_FX6_NFLASHA15_BYTES, P138_PINNED_FX6_NFLASHA15_HDR4K_SHA256, True, ext2_magic_hex=fx6_sb.s_magic_hex),
            RealHwDonorArtifactDigest("fx3_v702_im_elf", "ILME-FX3", "CLEAN_ROOM_SYNTHETIC", P138_PINNED_FX3_IM_ELF_BYTES, P138_PINNED_FX3_IM_ELF_SHA256, False),
            RealHwDonorArtifactDigest("fx6_v601_im_elf", "ILME-FX6", "CLEAN_ROOM_SYNTHETIC", P138_PINNED_FX6_IM_ELF_BYTES, P138_PINNED_FX6_IM_ELF_SHA256, False),
        )
        cross_ok = True
        snap_payload = {
            "mode": "CLEAN_ROOM_SYNTHETIC",
            "artifacts": [(a.label, a.byte_length, a.sha256_digest) for a in artifacts],
        }
        return RealHwDonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            read_only_access=READ_ONLY_DONOR_ACCESS,
            cross_sku_distinct=cross_ok,
            fx3_p15_bytes=P138_PINNED_FX3_NFLASHA15_BYTES,
            fx6_p15_bytes=P138_PINNED_FX6_NFLASHA15_BYTES,
            fx3_p15_ext2_magic_hex=fx3_sb.s_magic_hex,
            fx6_p15_ext2_magic_hex=fx6_sb.s_magic_hex,
            fx3_p15_free_inodes=fx3_sb.s_free_inodes_count,
            fx3_p15_effective_headroom_bytes=fx3_sb.effective_headroom_bytes,
            fx6_p15_free_inodes=fx6_sb.s_free_inodes_count,
            fx6_p15_effective_headroom_bytes=fx6_sb.effective_headroom_bytes,
            fx3_p2_cfg_uart=1,
            fx6_p2_cfg_uart=9,
            fx6_p1_cfg_uart=9,
            fx6_p1_loadaddr_sha256=P138_PINNED_FX6_P1_LOADADDR_SHA256,
            fx3_im_elf_sha256=P138_PINNED_FX3_IM_ELF_SHA256,
            fx6_im_elf_sha256=P138_PINNED_FX6_IM_ELF_SHA256,
            artifacts=artifacts,
            snapshot_sha256=_canonical_sha256(snap_payload),
        )

    # Strictly O_RDONLY reads on local donor artifacts
    fx3_partinf = read_file(str(resolved["fx3_partinf"]), 64 * 1024)
    fx6_partinf = read_file(str(resolved["fx6_partinf"]), 64 * 1024)
    fx3_mount = read_file(str(resolved["fx3_mount"]), 64 * 1024)
    fx6_mount = read_file(str(resolved["fx6_mount"]), 64 * 1024)
    fx3_p2_kemco = read_file(str(resolved["fx3_p2_kemco"]), 64 * 1024)
    fx6_p2_kemco = read_file(str(resolved["fx6_p2_kemco"]), 64 * 1024)
    fx6_p1_kemco = read_file(str(resolved["fx6_p1_kemco"]), 64 * 1024)
    fx6_p1_loadaddr = read_file(str(resolved["fx6_p1_loadaddr"]), 4096)
    fx3_im_elf = read_file(str(resolved["fx3_im_elf"]), 1024 * 1024)
    fx6_im_elf = read_file(str(resolved["fx6_im_elf"]), 1024 * 1024)
    fx3_p15_hdr4k, fx3_p15_size = _read_bounded_prefix_readonly(str(resolved["fx3_nflasha15"]), 4096)
    fx6_p15_hdr4k, fx6_p15_size = _read_bounded_prefix_readonly(str(resolved["fx6_nflasha15"]), 4096)

    fx3_sb = parse_ext2_superblock_bytes(fx3_p15_hdr4k)
    fx6_sb = parse_ext2_superblock_bytes(fx6_p15_hdr4k)
    fx3_p2_uart = _extract_cfg_uart(fx3_p2_kemco.decode("utf-8", errors="replace")) or -1
    fx6_p2_uart = _extract_cfg_uart(fx6_p2_kemco.decode("utf-8", errors="replace")) or -1
    fx6_p1_uart = _extract_cfg_uart(fx6_p1_kemco.decode("utf-8", errors="replace")) or -1

    fx3_partinf_sha = sha256(fx3_partinf).hexdigest()
    fx6_partinf_sha = sha256(fx6_partinf).hexdigest()
    fx3_mount_sha = sha256(fx3_mount).hexdigest()
    fx6_mount_sha = sha256(fx6_mount).hexdigest()
    fx3_p2_kemco_sha = sha256(fx3_p2_kemco).hexdigest()
    fx6_p2_kemco_sha = sha256(fx6_p2_kemco).hexdigest()
    fx6_p1_kemco_sha = sha256(fx6_p1_kemco).hexdigest()
    fx6_p1_loadaddr_sha = sha256(fx6_p1_loadaddr).hexdigest()
    fx3_p15_hdr_sha = sha256(fx3_p15_hdr4k).hexdigest()
    fx6_p15_hdr_sha = sha256(fx6_p15_hdr4k).hexdigest()
    fx3_im_sha = sha256(fx3_im_elf).hexdigest()
    fx6_im_sha = sha256(fx6_im_elf).hexdigest()

    artifacts = (
        RealHwDonorArtifactDigest("fx3_v702_partinf_conf", "ILME-FX3", "LOCAL_DONOR_O_RDONLY", len(fx3_partinf), fx3_partinf_sha, False),
        RealHwDonorArtifactDigest("fx6_v601_partinf_conf", "ILME-FX6", "LOCAL_DONOR_O_RDONLY", len(fx6_partinf), fx6_partinf_sha, False),
        RealHwDonorArtifactDigest("fx3_v702_mount_conf", "ILME-FX3", "LOCAL_DONOR_O_RDONLY", len(fx3_mount), fx3_mount_sha, False),
        RealHwDonorArtifactDigest("fx6_v601_mount_conf", "ILME-FX6", "LOCAL_DONOR_O_RDONLY", len(fx6_mount), fx6_mount_sha, False),
        RealHwDonorArtifactDigest("fx3_v702_p2_kemco_txt", "ILME-FX3", "LOCAL_DONOR_O_RDONLY", len(fx3_p2_kemco), fx3_p2_kemco_sha, False, cfg_uart_value=fx3_p2_uart),
        RealHwDonorArtifactDigest("fx6_v601_p2_kemco_txt", "ILME-FX6", "LOCAL_DONOR_O_RDONLY", len(fx6_p2_kemco), fx6_p2_kemco_sha, False, cfg_uart_value=fx6_p2_uart),
        RealHwDonorArtifactDigest("fx6_v601_p1_kemco_txt", "ILME-FX6", "LOCAL_DONOR_O_RDONLY", len(fx6_p1_kemco), fx6_p1_kemco_sha, False, cfg_uart_value=fx6_p1_uart),
        RealHwDonorArtifactDigest("fx6_v601_p1_loadaddr_txt", "ILME-FX6", "LOCAL_DONOR_O_RDONLY", len(fx6_p1_loadaddr), fx6_p1_loadaddr_sha, False),
        RealHwDonorArtifactDigest("fx3_v702_nflasha15_ext2_hdr4k", "ILME-FX3", "LOCAL_DONOR_O_RDONLY", fx3_p15_size, fx3_p15_hdr_sha, True, ext2_magic_hex=fx3_sb.s_magic_hex),
        RealHwDonorArtifactDigest("fx6_v601_nflasha15_ext2_hdr4k", "ILME-FX6", "LOCAL_DONOR_O_RDONLY", fx6_p15_size, fx6_p15_hdr_sha, True, ext2_magic_hex=fx6_sb.s_magic_hex),
        RealHwDonorArtifactDigest("fx3_v702_im_elf", "ILME-FX3", "LOCAL_DONOR_O_RDONLY", len(fx3_im_elf), fx3_im_sha, False),
        RealHwDonorArtifactDigest("fx6_v601_im_elf", "ILME-FX6", "LOCAL_DONOR_O_RDONLY", len(fx6_im_elf), fx6_im_sha, False),
    )

    cross_ok = (
        fx3_partinf_sha != fx6_partinf_sha
        and fx3_mount_sha != fx6_mount_sha
        and fx3_im_sha != fx6_im_sha
        and fx3_p2_uart == 1
        and fx6_p2_uart == 9
        and fx6_p1_uart == 9
        and fx3_p15_size == P138_PINNED_FX3_NFLASHA15_BYTES
        and fx6_p15_size == P138_PINNED_FX6_NFLASHA15_BYTES
        and fx3_sb.s_magic == EXT2_SUPER_MAGIC
        and fx6_sb.s_magic == EXT2_SUPER_MAGIC
    )
    snap_payload = {
        "mode": "LOCAL_DONOR_O_RDONLY",
        "artifacts": [(a.label, a.byte_length, a.sha256_digest) for a in artifacts],
    }
    return RealHwDonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        read_only_access=READ_ONLY_DONOR_ACCESS,
        cross_sku_distinct=cross_ok,
        fx3_p15_bytes=fx3_p15_size,
        fx6_p15_bytes=fx6_p15_size,
        fx3_p15_ext2_magic_hex=fx3_sb.s_magic_hex,
        fx6_p15_ext2_magic_hex=fx6_sb.s_magic_hex,
        fx3_p15_free_inodes=fx3_sb.s_free_inodes_count,
        fx3_p15_effective_headroom_bytes=fx3_sb.effective_headroom_bytes,
        fx6_p15_free_inodes=fx6_sb.s_free_inodes_count,
        fx6_p15_effective_headroom_bytes=fx6_sb.effective_headroom_bytes,
        fx3_p2_cfg_uart=fx3_p2_uart,
        fx6_p2_cfg_uart=fx6_p2_uart,
        fx6_p1_cfg_uart=fx6_p1_uart,
        fx6_p1_loadaddr_sha256=fx6_p1_loadaddr_sha,
        fx3_im_elf_sha256=fx3_im_sha,
        fx6_im_elf_sha256=fx6_im_sha,
        artifacts=artifacts,
        snapshot_sha256=_canonical_sha256(snap_payload),
    )


# ---------------------------------------------------------------------------
# Pillar A — EXT2_NFLASHA15_ATOMIC_INSTALLER_AND_ROLLBACK
# ---------------------------------------------------------------------------


def audit_crypto_block_device_path(device_path: str) -> CryptoBlockDeviceDecision:
    """Enforce /dev/nflashaN or /dev/cnflashaN for type=5, flag=1 encrypted partitions.

    Hard-blocks /dev/pnflasha3/8/15/23 (raw plaintext bypass that corrupts SPACC
    ciphertext on disk!).
    """
    norm = device_path.strip()
    m_raw = re.fullmatch(r"/dev/pnflasha(\d+)", norm)
    if m_raw:
        pnum = int(m_raw.group(1))
        if pnum in ENCRYPTED_TYPE5_PARTITIONS:
            return CryptoBlockDeviceDecision(
                allowed=False,
                device_path=norm,
                partition_number=pnum,
                is_encrypted_type5=True,
                uses_transparent_crypto_layer=False,
                error_code=BLOCKED_RAW_PNFLASHA_PLAINTEXT_HAZARD,
                reason=(
                    f"Raw plaintext device {norm} bypasses crypt-emmc.ko SPACC transparent "
                    f"encryption on type=5,flag=1 partition p{pnum}; must route via "
                    f"/dev/nflasha{pnum} or /dev/cnflasha{pnum}."
                ),
            )
        return CryptoBlockDeviceDecision(
            allowed=True,
            device_path=norm,
            partition_number=pnum,
            is_encrypted_type5=False,
            uses_transparent_crypto_layer=False,
            error_code="",
            reason=f"Plaintext VFAT partition p{pnum} does not use SPACC type=5 encryption.",
        )

    m_crypt = re.fullmatch(r"/dev/(?:cnflasha|nflasha)(\d+)", norm)
    if m_crypt:
        pnum = int(m_crypt.group(1))
        is_enc = pnum in ENCRYPTED_TYPE5_PARTITIONS
        return CryptoBlockDeviceDecision(
            allowed=True,
            device_path=norm,
            partition_number=pnum,
            is_encrypted_type5=is_enc,
            uses_transparent_crypto_layer=is_enc,
            error_code="",
            reason=f"Validated safe block-device route {norm} for partition p{pnum}.",
        )

    return CryptoBlockDeviceDecision(
        allowed=False,
        device_path=norm,
        partition_number=-1,
        is_encrypted_type5=False,
        uses_transparent_crypto_layer=False,
        error_code=BLOCKED_RAW_PNFLASHA_PLAINTEXT_HAZARD,
        reason=f"Unrecognized or unsafe block device path: {norm!r}.",
    )


def build_default_sd_escape_wrapper_script(*, stage_b_exec_target: str = "/tmp/stageb/im_hook.elf") -> str:
    """Build the canonical SD-card escape-hatch wrapper for /usr/bin/im.elf."""
    return (
        "#!/bin/sh\n"
        "# FX3 Stage-B reversible SD escape-hatch wrapper\n"
        f"{SD_ESCAPE_HATCH_EXEC_LINE}\n"
        f'exec {stage_b_exec_target} "$@"\n'
    )


def validate_sd_escape_hatch_wrapper(wrapper_text: str) -> SdEscapeHatchAuditResult:
    """Verify wrapper contains the mandatory SD-card escape-hatch fallback to .orig."""
    lines = [ln.strip() for ln in wrapper_text.splitlines() if ln.strip()]
    has_shebang = len(lines) > 0 and lines[0].startswith("#!/bin/sh")
    checks_manifest = SD_ESCAPE_HATCH_MANIFEST_PATH in wrapper_text
    execs_orig = bool(
        re.search(
            r'if\s+\[\s+!\s+-f\s+/mnt/sd/FX6_STAGEB_BOOT\.MANIFEST\s+\]\s*;\s*then\s+exec\s+/usr/bin/im\.elf\.orig\s+"\$@"\s*;\s*fi',
            wrapper_text,
        )
    )
    passed = has_shebang and checks_manifest and execs_orig
    if passed:
        return SdEscapeHatchAuditResult(
            passed=True,
            has_shebang=has_shebang,
            checks_manifest_path=checks_manifest,
            execs_orig_binary=execs_orig,
            error_code="",
            reason="SD escape-hatch wrapper verified.",
        )
    return SdEscapeHatchAuditResult(
        passed=False,
        has_shebang=has_shebang,
        checks_manifest_path=checks_manifest,
        execs_orig_binary=execs_orig,
        error_code=BLOCKED_MISSING_SD_ESCAPE_HATCH_WRAPPER,
        reason=(
            "Wrapper must start with #!/bin/sh and enforce "
            f"{SD_ESCAPE_HATCH_EXEC_LINE!r}."
        ),
    )


class InMemoryExt2Filesystem:
    """Strictly in-memory simulation of `/dev/nflasha15` (`ext2` `/usr`) for dry-run transactions."""

    def __init__(
        self,
        *,
        device_path: str = "/dev/cnflasha15",
        mount_mode: str = "ro",
        superblock: Optional[Ext2SuperblockMetadata] = None,
        files: Optional[Dict[str, bytes]] = None,
    ) -> None:
        self.device_path = device_path
        self.mount_mode = mount_mode
        self.superblock = superblock or parse_ext2_superblock_bytes(build_synthetic_ext2_superblock_header())
        self.files: Dict[str, bytes] = dict(files or {})

    def remount(self, mode: str) -> None:
        if mode not in ("ro", "rw"):
            raise ValueError(f"Invalid mount mode: {mode}")
        self.mount_mode = mode

    def read_bytes(self, path: str) -> bytes:
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path]

    def write_bytes(self, path: str, data: bytes) -> None:
        if self.mount_mode != "rw":
            raise PermissionError(f"Filesystem {self.device_path} is mounted {self.mount_mode}, write denied")
        self.files[path] = bytes(data)

    def remove(self, path: str) -> None:
        if self.mount_mode != "rw":
            raise PermissionError(f"Filesystem {self.device_path} is mounted {self.mount_mode}, unlink denied")
        self.files.pop(path, None)


def simulate_atomic_ext2_install_and_rollback(
    *,
    fs: InMemoryExt2Filesystem,
    expected_stock_sha256: str,
    staged_wrapper_text: str,
    target_path: str = "/usr/bin/im.elf",
    backup_path: str = "/usr/bin/im.elf.orig",
    fault_injection: str = "none",
    perform_clean_uninstall_rollback: bool = False,
    scenario_id: str = "AD_HOC",
) -> AtomicExt2InstallTransactionReport:
    """Simulate an A7C-II (`installer.c`) reversible file-level ext2 install & hash-verified rollback.

    Fault injection modes:
      - "none": complete install + read-back verify + remount ro (plus optional clean uninstall)
      - "bit_flip": inject 1-bit flip during disk write so read-back SHA-256 fails -> triggers rollback
      - "short_write": inject truncated write -> read-back SHA-256 fails -> triggers rollback
    """
    error_codes: List[str] = []
    errors: List[str] = []
    phases: List[str] = ["PRECHECK"]

    stock_bytes = fs.read_bytes(target_path)
    stock_sha_before = sha256(stock_bytes).hexdigest()

    # 1. Device path transparent-crypto firewall (/dev/pnflasha15 blocked)
    dev_decision = audit_crypto_block_device_path(fs.device_path)
    if not dev_decision.allowed:
        error_codes.append(dev_decision.error_code)
        errors.append(dev_decision.reason)

    # 2. SD escape-hatch wrapper firewall
    wrapper_audit = validate_sd_escape_hatch_wrapper(staged_wrapper_text)
    if not wrapper_audit.passed:
        error_codes.append(wrapper_audit.error_code)
        errors.append(wrapper_audit.reason)

    # 3. Ext2 superblock, headroom >= 32 MiB & inode check
    sb = fs.superblock
    if sb.s_magic != EXT2_SUPER_MAGIC:
        error_codes.append(ERR_EXT2_BAD_MAGIC)
        errors.append(f"Invalid ext2 s_magic={sb.s_magic_hex}")
    if sb.image_bytes > sb.partition_slot_bytes:
        error_codes.append(ERR_EXT2_SLOT_OVERFLOW)
        errors.append(f"Image {sb.image_bytes} exceeds 500 MiB slot {sb.partition_slot_bytes}")
    staged_bytes = staged_wrapper_text.encode("utf-8")
    min_internal_needed = len(stock_bytes) + len(staged_bytes) + 65536
    if sb.effective_headroom_bytes < EXT2_MIN_HEADROOM_BYTES or sb.ext2_internal_free_bytes < min_internal_needed:
        error_codes.append(ERR_EXT2_INSUFFICIENT_HEADROOM)
        errors.append(
            f"Ext2 headroom insufficient: effective={sb.effective_headroom_bytes} B (<32 MiB) "
            f"or internal_free={sb.ext2_internal_free_bytes} B (<{min_internal_needed} B)"
        )
    if sb.s_free_inodes_count < EXT2_MIN_FREE_INODES:
        error_codes.append(ERR_EXT2_INSUFFICIENT_INODES)
        errors.append(f"Ext2 free inodes {sb.s_free_inodes_count} < {EXT2_MIN_FREE_INODES}")

    # 4. Stock SHA-256 verification BEFORE remounting rw
    if stock_sha_before != expected_stock_sha256:
        error_codes.append(BLOCKED_STOCK_SHA256_MISMATCH)
        errors.append(
            f"Stock {target_path} SHA-256 {stock_sha_before} != expected {expected_stock_sha256}; aborting before rw remount."
        )

    if error_codes:
        final_sha = sha256(fs.read_bytes(target_path)).hexdigest()
        ro_ok = fs.mount_mode == "ro"
        payload = {
            "scenario_id": scenario_id,
            "status": STATUS_REJECTED_EXT2_INSTALLER_PILLAR,
            "error_codes": error_codes,
            "final_sha": final_sha,
        }
        return AtomicExt2InstallTransactionReport(
            passed=False,
            status=STATUS_REJECTED_EXT2_INSTALLER_PILLAR,
            scenario_id=scenario_id,
            device_path=fs.device_path,
            target_path=target_path,
            backup_path=backup_path,
            fault_injected=fault_injection,
            stock_sha256_before=stock_sha_before,
            final_target_sha256=final_sha,
            final_backup_sha256="",
            stock_restored_exact=(final_sha == expected_stock_sha256),
            final_mount_state=fs.mount_mode,
            ro_remount_verified=ro_ok,
            phases_executed=tuple(phases),
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            error_codes=tuple(error_codes),
            errors=tuple(errors),
            report_sha256=_canonical_sha256(payload),
        )

    # 5. Atomic rw transaction with guaranteed rollback & ro remount
    expected_staged_sha = sha256(staged_bytes).hexdigest()
    tmp_path = f"{target_path}.new"
    rolled_back = False

    try:
        fs.remount("rw")
        phases.append("REMOUNT_RW")

        # Save .orig backup & read-back verify .orig
        fs.write_bytes(backup_path, stock_bytes)
        phases.append("BACKUP_ORIG")
        if sha256(fs.read_bytes(backup_path)).hexdigest() != stock_sha_before:
            raise RuntimeError("Backup .orig read-back SHA-256 mismatch")

        # Write staged file (applying fault injection if requested)
        written_bytes = staged_bytes
        if fault_injection == "bit_flip":
            mutated = bytearray(staged_bytes)
            mutated[-1] ^= 0x01
            written_bytes = bytes(mutated)
        elif fault_injection == "short_write":
            written_bytes = staged_bytes[: max(1, len(staged_bytes) // 2)]
        elif fault_injection != "none":
            raise ValueError(f"Unsupported fault_injection mode: {fault_injection}")

        fs.write_bytes(tmp_path, written_bytes)
        fs.write_bytes(target_path, fs.read_bytes(tmp_path))
        fs.remove(tmp_path)
        phases.append("WRITE_STAGED")

        # Full read-back SHA-256 verify
        readback = fs.read_bytes(target_path)
        readback_sha = sha256(readback).hexdigest()
        phases.append("READBACK_VERIFY")

        if readback_sha != expected_staged_sha or len(readback) != len(staged_bytes):
            if fault_injection == "short_write" or len(readback) != len(staged_bytes):
                error_codes.append(BLOCKED_SHORT_WRITE_ROLLED_BACK)
                errors.append(
                    f"Short-write detected ({len(readback)} B != {len(staged_bytes)} B); rolling back from {backup_path}."
                )
            else:
                error_codes.append(BLOCKED_READBACK_SHA256_MISMATCH_ROLLED_BACK)
                errors.append(
                    f"Read-back SHA-256 mismatch ({readback_sha} != {expected_staged_sha}); rolling back from {backup_path}."
                )
            # Atomic Rollback from .orig
            fs.write_bytes(target_path, fs.read_bytes(backup_path))
            fs.remove(backup_path)
            rolled_back = True
            phases.append("ROLLBACK_FROM_ORIG")
            restored_sha = sha256(fs.read_bytes(target_path)).hexdigest()
            if restored_sha != stock_sha_before:
                raise RuntimeError("Rollback verification failed to restore exact stock SHA-256")
            phases.append("VERIFY_ROLLBACK_SHA256")
        elif perform_clean_uninstall_rollback:
            # Remount ro after install, then verify clean uninstall/rollback cycle restores exact stock
            fs.remount("ro")
            phases.append("REMOUNT_RO_AFTER_INSTALL")
            fs.remount("rw")
            phases.append("UNINSTALL_REMOUNT_RW")
            fs.write_bytes(target_path, fs.read_bytes(backup_path))
            fs.remove(backup_path)
            rolled_back = True
            phases.append("CLEAN_UNINSTALL_FROM_ORIG")
            if sha256(fs.read_bytes(target_path)).hexdigest() != stock_sha_before:
                raise RuntimeError("Clean uninstall failed to restore exact stock SHA-256")
            phases.append("VERIFY_ROLLBACK_SHA256")
    finally:
        if fs.mount_mode != "ro":
            fs.remount("ro")
            phases.append("REMOUNT_RO")

    final_target_sha = sha256(fs.read_bytes(target_path)).hexdigest()
    final_backup_sha = sha256(fs.read_bytes(backup_path)).hexdigest() if backup_path in fs.files else ""
    stock_restored_exact = final_target_sha == stock_sha_before
    ro_ok = fs.mount_mode == "ro"

    if rolled_back and error_codes:
        status = STATUS_ROLLED_BACK_TO_STOCK_EXACT if (stock_restored_exact and ro_ok) else STATUS_REJECTED_EXT2_INSTALLER_PILLAR
        passed = False
    elif rolled_back and not error_codes:
        status = STATUS_VERIFIED_EXT2_INSTALLER_PILLAR if (stock_restored_exact and ro_ok) else STATUS_REJECTED_EXT2_INSTALLER_PILLAR
        passed = stock_restored_exact and ro_ok
    else:
        status = STATUS_VERIFIED_EXT2_INSTALLER_PILLAR if (final_target_sha == expected_staged_sha and final_backup_sha == stock_sha_before and ro_ok) else STATUS_REJECTED_EXT2_INSTALLER_PILLAR
        passed = status == STATUS_VERIFIED_EXT2_INSTALLER_PILLAR

    payload = {
        "scenario_id": scenario_id,
        "status": status,
        "final_target_sha": final_target_sha,
        "final_backup_sha": final_backup_sha,
        "phases": phases,
        "error_codes": error_codes,
    }
    return AtomicExt2InstallTransactionReport(
        passed=passed,
        status=status,
        scenario_id=scenario_id,
        device_path=fs.device_path,
        target_path=target_path,
        backup_path=backup_path,
        fault_injected=fault_injection,
        stock_sha256_before=stock_sha_before,
        final_target_sha256=final_target_sha,
        final_backup_sha256=final_backup_sha,
        stock_restored_exact=stock_restored_exact,
        final_mount_state=fs.mount_mode,
        ro_remount_verified=ro_ok,
        phases_executed=tuple(phases),
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        report_sha256=_canonical_sha256(payload),
    )


def run_ext2_atomic_installer_6_scenario_suite(
    *,
    stock_im_elf_bytes: Optional[bytes] = None,
) -> Ext2Installer6ScenarioSuiteResult:
    """Execute the 6 canonical Pillar A ext2 `/dev/nflasha15` atomic installer & rollback scenarios."""
    stock_data = stock_im_elf_bytes if stock_im_elf_bytes is not None else (b"\x7fELF" + b"FX3_STOCK_IM_ELF_40920B" * 1779)[:P138_PINNED_FX3_IM_ELF_BYTES]
    stock_sha = sha256(stock_data).hexdigest()
    good_wrapper = build_default_sd_escape_wrapper_script()
    healthy_sb = parse_ext2_superblock_bytes(build_synthetic_ext2_superblock_header())

    # EI1: Healthy atomic install + clean uninstall rollback -> 100% stock SHA-256 & ro remount
    r1 = simulate_atomic_ext2_install_and_rollback(
        fs=InMemoryExt2Filesystem(device_path="/dev/cnflasha15", superblock=healthy_sb, files={"/usr/bin/im.elf": stock_data}),
        expected_stock_sha256=stock_sha,
        staged_wrapper_text=good_wrapper,
        fault_injection="none",
        perform_clean_uninstall_rollback=True,
        scenario_id=EXT2_INSTALLER_SCENARIO_IDS[0],
    )

    # EI2: Injected bit-flip during write -> read-back mismatch -> automatic exact rollback & ro remount
    r2 = simulate_atomic_ext2_install_and_rollback(
        fs=InMemoryExt2Filesystem(device_path="/dev/nflasha15", superblock=healthy_sb, files={"/usr/bin/im.elf": stock_data}),
        expected_stock_sha256=stock_sha,
        staged_wrapper_text=good_wrapper,
        fault_injection="bit_flip",
        scenario_id=EXT2_INSTALLER_SCENARIO_IDS[1],
    )

    # EI3: Injected short-write -> automatic exact rollback & ro remount
    r3 = simulate_atomic_ext2_install_and_rollback(
        fs=InMemoryExt2Filesystem(device_path="/dev/cnflasha15", superblock=healthy_sb, files={"/usr/bin/im.elf": stock_data}),
        expected_stock_sha256=stock_sha,
        staged_wrapper_text=good_wrapper,
        fault_injection="short_write",
        scenario_id=EXT2_INSTALLER_SCENARIO_IDS[2],
    )

    # EI4: Raw plaintext /dev/pnflasha15 bypass -> hard-blocked before remount
    r4 = simulate_atomic_ext2_install_and_rollback(
        fs=InMemoryExt2Filesystem(device_path="/dev/pnflasha15", superblock=healthy_sb, files={"/usr/bin/im.elf": stock_data}),
        expected_stock_sha256=stock_sha,
        staged_wrapper_text=good_wrapper,
        fault_injection="none",
        scenario_id=EXT2_INSTALLER_SCENARIO_IDS[3],
    )

    # EI5: Stock SHA-256 mismatch + low headroom (<32 MiB) -> aborted before rw remount
    cramped_sb = parse_ext2_superblock_bytes(
        build_synthetic_ext2_superblock_header(
            s_blocks_count=500000,
            s_free_blocks_count=4096,  # 4 MiB internal + 12.288 MiB tail = 16 MiB < 32 MiB
            s_free_inodes_count=64,
        )
    )
    r5 = simulate_atomic_ext2_install_and_rollback(
        fs=InMemoryExt2Filesystem(device_path="/dev/cnflasha15", superblock=cramped_sb, files={"/usr/bin/im.elf": stock_data + b"TAMPERED"}),
        expected_stock_sha256=stock_sha,
        staged_wrapper_text=good_wrapper,
        fault_injection="none",
        scenario_id=EXT2_INSTALLER_SCENARIO_IDS[4],
    )

    # EI6: Missing SD escape-hatch wrapper -> hard-blocked
    bad_wrapper = "#!/bin/sh\nexec /tmp/stageb/im_hook.elf \"$@\"\n"
    r6 = simulate_atomic_ext2_install_and_rollback(
        fs=InMemoryExt2Filesystem(device_path="/dev/cnflasha15", superblock=healthy_sb, files={"/usr/bin/im.elf": stock_data}),
        expected_stock_sha256=stock_sha,
        staged_wrapper_text=bad_wrapper,
        fault_injection="none",
        scenario_id=EXT2_INSTALLER_SCENARIO_IDS[5],
    )

    results = (r1, r2, r3, r4, r5, r6)
    suite_errors: List[str] = []
    passed_count = 0

    if r1.passed and r1.stock_restored_exact and r1.ro_remount_verified:
        passed_count += 1
    else:
        suite_errors.append(f"EI1 failed: {r1.error_codes}")

    if (not r2.passed) and r2.status == STATUS_ROLLED_BACK_TO_STOCK_EXACT and r2.stock_restored_exact and r2.ro_remount_verified and BLOCKED_READBACK_SHA256_MISMATCH_ROLLED_BACK in r2.error_codes:
        passed_count += 1
    else:
        suite_errors.append(f"EI2 failed rollback verify: {r2.status} {r2.error_codes}")

    if (not r3.passed) and r3.status == STATUS_ROLLED_BACK_TO_STOCK_EXACT and r3.stock_restored_exact and r3.ro_remount_verified and BLOCKED_SHORT_WRITE_ROLLED_BACK in r3.error_codes:
        passed_count += 1
    else:
        suite_errors.append(f"EI3 failed short-write rollback verify: {r3.status} {r3.error_codes}")

    if (not r4.passed) and BLOCKED_RAW_PNFLASHA_PLAINTEXT_HAZARD in r4.error_codes and r4.ro_remount_verified:
        passed_count += 1
    else:
        suite_errors.append(f"EI4 failed to block /dev/pnflasha15: {r4.error_codes}")

    if (not r5.passed) and BLOCKED_STOCK_SHA256_MISMATCH in r5.error_codes and ERR_EXT2_INSUFFICIENT_HEADROOM in r5.error_codes and ERR_EXT2_INSUFFICIENT_INODES in r5.error_codes and r5.ro_remount_verified:
        passed_count += 1
    else:
        suite_errors.append(f"EI5 failed stock-hash/headroom abort: {r5.error_codes}")

    if (not r6.passed) and BLOCKED_MISSING_SD_ESCAPE_HATCH_WRAPPER in r6.error_codes and r6.ro_remount_verified:
        passed_count += 1
    else:
        suite_errors.append(f"EI6 failed to block missing SD escape hatch: {r6.error_codes}")

    all_ok = len(suite_errors) == 0 and passed_count == len(EXT2_INSTALLER_SCENARIO_IDS)
    suite_payload = {
        "scenarios": [
            {"id": r.scenario_id, "status": r.status, "passed": r.passed, "error_codes": list(r.error_codes)}
            for r in results
        ]
    }
    return Ext2Installer6ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_EXT2_INSTALLER_PILLAR if all_ok else STATUS_REJECTED_EXT2_INSTALLER_PILLAR,
        scenarios_passed=passed_count,
        scenarios_total=len(EXT2_INSTALLER_SCENARIO_IDS),
        scenario_results=results,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256(suite_payload),
    )


# ---------------------------------------------------------------------------
# Pillar B — P1_P3_MUTUAL_EXCLUSION_AND_ONESHOT_RESCUE_INITRD
# ---------------------------------------------------------------------------


def audit_p1_p3_mutual_exclusion(*, touches_p1: bool, touches_p3: bool) -> MutualExclusionDecision:
    """Enforce Golden Mutual-Exclusion Law: never modify p1 and p3 in the same transaction."""
    p1_intact = not touches_p1
    p3_intact = not touches_p3
    untouched: List[str] = []
    if p1_intact:
        untouched.append("p1")
    if p3_intact:
        untouched.append("p3")

    if touches_p1 and touches_p3:
        return MutualExclusionDecision(
            allowed=False,
            touches_p1=True,
            touches_p3=True,
            p1_intact=False,
            p3_intact=False,
            untouched_bootable_banks=(),
            error_codes=(BLOCKED_DUAL_BOOT_PARTITION_SIMULTANEOUS_WRITE,),
            reason=(
                "Golden Mutual-Exclusion Law violated: p1 (23.94 MiB) and p3 (75 MiB) "
                "MUST NEVER be modified in the same transaction."
            ),
        )
    return MutualExclusionDecision(
        allowed=True,
        touches_p1=touches_p1,
        touches_p3=touches_p3,
        p1_intact=p1_intact,
        p3_intact=p3_intact,
        untouched_bootable_banks=tuple(untouched),
        error_codes=(),
        reason=f"Mutual-exclusion invariant satisfied; untouched bootable bank(s): {tuple(untouched)}.",
    )


def build_default_safe_p1_kemco_text() -> str:
    """Build safe FX3 p1:/boot/kemco.txt with cfg.uart=1 and ttyAMA0,460800n8 console."""
    return (
        "kemco\n"
        "init=/sbin/init\n"
        "ramdisk_size=8192\n"
        "rw noatime\n"
        "cfg.uart=1\n"
        "ip=off root=/dev/ram0 rootfstype=squashfs\n"
        "console=ttyAMA0,460800n8 amba2.console=1\n"
        "exception.reboot=1 wdt.mode=1\n"
        "*\n"
    )


def build_default_oneshot_p1_sbin_init() -> str:
    """Build single-shot diagnostic /sbin/init with mode* clear + sync as very first executable line."""
    return (
        "#!/bin/sh\n"
        "# Single-shot p1 diagnostic init: clear mode* BEFORE anything else\n"
        "rm -f /setting/updater/mode* && sync\n"
        "mount -t proc proc /proc\n"
        "mount -t sysfs sysfs /sys\n"
        "dmesg > /tmp/p1_diag_dmesg.txt 2>&1\n"
        "sync\n"
        "reboot -f\n"
    )


def _first_executable_line(script_text: str) -> str:
    for raw in script_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        return line
    return ""


def audit_p1_oneshot_rescue_proposal(proposal: P1OneshotRescueProposal) -> P1OneshotRescueReport:
    """Verify P1/P3 mutual exclusion, p1 dat2/dat3 preservation, cfg.uart=1, and line-1 mode* clear."""
    error_codes: List[str] = []
    errors: List[str] = []

    # 1. Mutual exclusion between p1 and p3
    me = audit_p1_p3_mutual_exclusion(touches_p1=proposal.touches_p1, touches_p3=proposal.touches_p3)
    if not me.allowed:
        error_codes.extend(me.error_codes)
        errors.append(me.reason)

    # 2. Block-device path check if touching p1 or p3
    if proposal.touches_p1:
        d1 = audit_crypto_block_device_path(proposal.p1_device_path)
        if not d1.allowed or d1.partition_number != 1:
            error_codes.append(BLOCKED_RAW_PNFLASHA_PLAINTEXT_HAZARD)
            errors.append(f"Invalid p1 device path: {proposal.p1_device_path}")
    if proposal.touches_p3:
        d3 = audit_crypto_block_device_path(proposal.p3_device_path)
        if not d3.allowed or d3.partition_number != 3:
            error_codes.append(d3.error_code or BLOCKED_RAW_PNFLASHA_PLAINTEXT_HAZARD)
            errors.append(d3.reason)

    # 3. Stock p1:/dat2 == "91030080" and p1:/dat3 preserved
    dat2_ok = proposal.p1_dat2_value.strip() == FX3_MODEL_ID_STR
    if not dat2_ok:
        error_codes.append(BLOCKED_P1_DAT2_MODEL_ID_CORRUPTED)
        errors.append(
            f"p1:/dat2={proposal.p1_dat2_value!r} != required FX3 {FX3_MODEL_ID_STR!r}"
        )

    dat3_ok = bool(proposal.p1_dat3_value.strip()) and (
        proposal.p1_dat3_value.strip() == proposal.p1_dat3_expected.strip()
    )
    if not dat3_ok:
        error_codes.append(BLOCKED_P1_DAT3_REGION_CORRUPTED)
        errors.append("p1:/dat3 region marker missing or altered.")

    # 4. p1:/boot/loadaddr.txt and capacity <= 25,100,288 B
    loadaddr_ok = (
        proposal.p1_loadaddr_text.strip() == DEFAULT_P1_LOADADDR_TEXT
        and 0 < proposal.p1_payload_bytes <= P1_VFAT_CAPACITY_BYTES
    )
    if not loadaddr_ok:
        error_codes.append(BLOCKED_P1_LOADADDR_INVALID)
        errors.append("p1:/boot/loadaddr.txt mismatch or payload exceeds 23.94 MiB VFAT slot.")

    # 5. p1:/boot/kemco.txt must enforce cfg.uart=1 (NOT FX6 cfg.uart=9!) & console=ttyAMA0,460800n8
    cfg_uart = _extract_cfg_uart(proposal.p1_kemco_text)
    if cfg_uart == 9:
        error_codes.append(BLOCKED_FX6_UART9_BLIND_BLACKOUT)
        errors.append("FX6 cfg.uart=9 causes blind UART blackout on FX3; cfg.uart=1 is mandatory.")
    elif cfg_uart != 1:
        error_codes.append(BLOCKED_FX6_UART9_BLIND_BLACKOUT)
        errors.append(f"p1:/boot/kemco.txt has cfg.uart={cfg_uart}; expected cfg.uart=1.")

    console_ok = (
        "console=ttyAMA0,460800n8" in proposal.p1_kemco_text
        and "console=ttynull" not in proposal.p1_kemco_text
    )
    if not console_ok:
        error_codes.append(BLOCKED_P1_MISSING_SERIAL_CONSOLE)
        errors.append("p1:/boot/kemco.txt must include console=ttyAMA0,460800n8 (and not console=ttynull).")

    # 6. /sbin/init line 1 MUST delete /setting/updater/mode* + sync
    first_line = _first_executable_line(proposal.initrd_sbin_init_text)
    first_line_ok = bool(
        re.match(r"^rm\s+-(?:rf|fr|f)\s+/setting/updater/mode\*\s*(?:&&|;)\s*sync\b", first_line)
    )
    if not first_line_ok:
        error_codes.append(BLOCKED_MISSING_FIRST_LINE_MODE_CLEAR_SYNC)
        errors.append(
            f"/sbin/init first executable line must be `rm -f /setting/updater/mode* && sync`, got: {first_line!r}"
        )

    passed = len(error_codes) == 0
    status = STATUS_VERIFIED_P1_RESCUE_PILLAR if passed else STATUS_REJECTED_P1_RESCUE_PILLAR
    payload = {
        "scenario_id": proposal.scenario_id,
        "status": status,
        "untouched_banks": list(me.untouched_bootable_banks),
        "cfg_uart": cfg_uart,
        "error_codes": error_codes,
    }
    return P1OneshotRescueReport(
        passed=passed,
        status=status,
        scenario_id=proposal.scenario_id,
        mutual_exclusion_ok=me.allowed,
        untouched_bootable_banks=me.untouched_bootable_banks,
        dat2_preserved=dat2_ok,
        dat3_preserved=dat3_ok,
        cfg_uart=cfg_uart,
        console_uart_ok=console_ok,
        first_line_mode_clear_sync_ok=first_line_ok,
        loadaddr_ok=loadaddr_ok,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        report_sha256=_canonical_sha256(payload),
    )


def run_p1_rescue_and_mutual_exclusion_6_scenario_suite() -> P1Rescue6ScenarioSuiteResult:
    """Execute the 6 canonical Pillar B p1/p3 mutual-exclusion & single-shot rescue initrd scenarios."""
    safe_kemco = build_default_safe_p1_kemco_text()
    safe_init = build_default_oneshot_p1_sbin_init()

    def _base(sid: str, **overrides: Any) -> P1OneshotRescueProposal:
        defaults: Dict[str, Any] = {
            "scenario_id": sid,
            "touches_p1": True,
            "touches_p3": False,
            "p1_device_path": "/dev/nflasha1",
            "p3_device_path": "/dev/cnflasha3",
            "p1_dat2_value": FX3_MODEL_ID_STR,
            "p1_dat3_value": FX3_EXPECTED_REGION_TAG,
            "p1_dat3_expected": FX3_EXPECTED_REGION_TAG,
            "p1_kemco_text": safe_kemco,
            "p1_loadaddr_text": DEFAULT_P1_LOADADDR_TEXT,
            "p1_payload_bytes": 16684032,
            "initrd_sbin_init_text": safe_init,
        }
        defaults.update(overrides)
        return P1OneshotRescueProposal(**defaults)

    # PR1: Healthy p1 single-shot diagnostic with p3 untouched
    r1 = audit_p1_oneshot_rescue_proposal(_base(P1_RESCUE_SCENARIO_IDS[0]))

    # PR2: Simultaneous p1 + p3 modification -> blocked
    r2 = audit_p1_oneshot_rescue_proposal(_base(P1_RESCUE_SCENARIO_IDS[1], touches_p1=True, touches_p3=True))

    # PR3: FX6 cfg.uart=9 + console=ttynull -> blocked
    fx6_blind_kemco = safe_kemco.replace("cfg.uart=1", "cfg.uart=9").replace(
        "console=ttyAMA0,460800n8", "console=ttynull"
    )
    r3 = audit_p1_oneshot_rescue_proposal(_base(P1_RESCUE_SCENARIO_IDS[2], p1_kemco_text=fx6_blind_kemco))

    # PR4: /sbin/init missing line-1 mode* clear + sync (placed too late) -> blocked
    late_clear_init = (
        "#!/bin/sh\n"
        "mount -t proc proc /proc\n"
        "rm -f /setting/updater/mode* && sync\n"
        "reboot -f\n"
    )
    r4 = audit_p1_oneshot_rescue_proposal(_base(P1_RESCUE_SCENARIO_IDS[3], initrd_sbin_init_text=late_clear_init))

    # PR5: Corrupted p1:/dat2 ("91040086") and missing p1:/dat3 -> blocked
    r5 = audit_p1_oneshot_rescue_proposal(
        _base(P1_RESCUE_SCENARIO_IDS[4], p1_dat2_value=FX6_MODEL_ID_STR, p1_dat3_value="")
    )

    # PR6: p3-only bank transaction targeting raw plaintext /dev/pnflasha3 -> blocked
    r6 = audit_p1_oneshot_rescue_proposal(
        _base(P1_RESCUE_SCENARIO_IDS[5], touches_p1=False, touches_p3=True, p3_device_path="/dev/pnflasha3")
    )

    results = (r1, r2, r3, r4, r5, r6)
    suite_errors: List[str] = []
    passed_count = 0

    if r1.passed and "p3" in r1.untouched_bootable_banks and r1.cfg_uart == 1 and r1.first_line_mode_clear_sync_ok:
        passed_count += 1
    else:
        suite_errors.append(f"PR1 failed: {r1.error_codes}")

    if (not r2.passed) and BLOCKED_DUAL_BOOT_PARTITION_SIMULTANEOUS_WRITE in r2.error_codes:
        passed_count += 1
    else:
        suite_errors.append(f"PR2 failed to block dual p1+p3 write: {r2.error_codes}")

    if (not r3.passed) and BLOCKED_FX6_UART9_BLIND_BLACKOUT in r3.error_codes and BLOCKED_P1_MISSING_SERIAL_CONSOLE in r3.error_codes:
        passed_count += 1
    else:
        suite_errors.append(f"PR3 failed to block FX6 cfg.uart=9 blackout: {r3.error_codes}")

    if (not r4.passed) and BLOCKED_MISSING_FIRST_LINE_MODE_CLEAR_SYNC in r4.error_codes:
        passed_count += 1
    else:
        suite_errors.append(f"PR4 failed to block missing line-1 mode* clear: {r4.error_codes}")

    if (not r5.passed) and BLOCKED_P1_DAT2_MODEL_ID_CORRUPTED in r5.error_codes and BLOCKED_P1_DAT3_REGION_CORRUPTED in r5.error_codes:
        passed_count += 1
    else:
        suite_errors.append(f"PR5 failed to block dat2/dat3 corruption: {r5.error_codes}")

    if (not r6.passed) and BLOCKED_RAW_PNFLASHA_PLAINTEXT_HAZARD in r6.error_codes:
        passed_count += 1
    else:
        suite_errors.append(f"PR6 failed to block /dev/pnflasha3 plaintext write: {r6.error_codes}")

    all_ok = len(suite_errors) == 0 and passed_count == len(P1_RESCUE_SCENARIO_IDS)
    suite_payload = {
        "scenarios": [
            {"id": r.scenario_id, "status": r.status, "passed": r.passed, "error_codes": list(r.error_codes)}
            for r in results
        ]
    }
    return P1Rescue6ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_P1_RESCUE_PILLAR if all_ok else STATUS_REJECTED_P1_RESCUE_PILLAR,
        scenarios_passed=passed_count,
        scenarios_total=len(P1_RESCUE_SCENARIO_IDS),
        scenario_results=results,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256(suite_payload),
    )


# ---------------------------------------------------------------------------
# Pillar C — TIER0_PRECONDITION_AND_HARDWARE_WRITE_LOCK
# ---------------------------------------------------------------------------


def build_synthetic_tier0_receipt(
    *,
    omit: Sequence[str] = (),
    unverified: Sequence[str] = (),
    persistent_emmc_writes_requested: bool = False,
) -> Tier0BackupReceipt:
    """Build a deterministic Tier-0 backup receipt for Pillar C testing."""
    omit_set = set(omit)
    unver_set = set(unverified)
    entries: List[Tier0BackupArtifactEntry] = []
    for name in REQUIRED_TIER0_ARTIFACT_NAMES:
        if name in omit_set:
            continue
        min_sz, max_sz = TIER0_ARTIFACT_EXPECTED_SIZES[name]
        sz = min_sz if name != "spi_nor_ddrtraining" else 4096
        digest = sha256(f"synthetic-tier0-{name}-{sz}".encode("utf-8")).hexdigest()
        if name in unver_set:
            digest = "0" * 64
        entries.append(
            Tier0BackupArtifactEntry(
                name=name,
                byte_length=sz,
                sha256_digest=digest,
                readback_verified=(name not in unver_set),
                source_mode="O_RDONLY",
            )
        )
    return Tier0BackupReceipt(
        body_id_tag=sha256(b"fx3-body-tag-synthetic-01").hexdigest(),
        model_id=FX3_MODEL_ID_STR,
        artifacts=tuple(entries),
        persistent_emmc_writes_requested=persistent_emmc_writes_requested,
    )


def verify_tier0_backup_precondition(
    receipt: Tier0BackupReceipt,
    *,
    scenario_id: str = "AD_HOC",
) -> Tier0PreconditionAndLockReport:
    """Verify full Tier-0 backup receipt (Sector 0, p1, p2, p6, p12, p18, SPI NOR ddrtraining.dat)
    while keeping `persistent_emmc_writes_authorized = False` hard-locked.
    """
    error_codes: List[str] = []
    errors: List[str] = []

    if PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE or PHYSICAL_DEVICE_WRITES != 0:
        error_codes.append(BLOCKED_HARDWARE_EMMC_WRITE_LOCKED)
        errors.append("Hard-locked zero-write invariant violated in module constants.")

    if receipt.persistent_emmc_writes_requested:
        error_codes.append(BLOCKED_HARDWARE_EMMC_WRITE_LOCKED)
        errors.append("Persistent physical eMMC writes are hard-locked False (unauthorized).")

    if not _is_hex64(receipt.body_id_tag) or receipt.model_id != FX3_MODEL_ID_STR:
        error_codes.append(BLOCKED_MISSING_TIER0_BACKUP_PRECONDITION)
        errors.append(f"Invalid Tier-0 receipt identity (model_id={receipt.model_id!r}).")

    by_name: Dict[str, Tier0BackupArtifactEntry] = {a.name: a for a in receipt.artifacts}
    present = tuple(n for n in REQUIRED_TIER0_ARTIFACT_NAMES if n in by_name)
    missing = tuple(n for n in REQUIRED_TIER0_ARTIFACT_NAMES if n not in by_name)
    unverified_list: List[str] = []

    if missing:
        error_codes.append(BLOCKED_MISSING_TIER0_BACKUP_PRECONDITION)
        errors.append(f"Missing required Tier-0 backup artifact(s): {missing}")

    for name in present:
        art = by_name[name]
        min_sz, max_sz = TIER0_ARTIFACT_EXPECTED_SIZES[name]
        zero_sha = art.sha256_digest == ("0" * 64)
        valid_sha = _is_hex64(art.sha256_digest) and (not zero_sha)
        size_ok = min_sz <= art.byte_length <= max_sz
        if (not art.readback_verified) or (not valid_sha) or (not size_ok) or (art.source_mode != "O_RDONLY"):
            unverified_list.append(name)

    if unverified_list:
        error_codes.append(BLOCKED_TIER0_READBACK_UNVERIFIED)
        errors.append(f"Tier-0 readback SHA-256 or size verification failed for: {tuple(unverified_list)}")

    tier0_complete = len(missing) == 0 and len(unverified_list) == 0 and _is_hex64(receipt.body_id_tag) and receipt.model_id == FX3_MODEL_ID_STR
    passed = len(error_codes) == 0 and tier0_complete
    status = STATUS_VERIFIED_TIER0_LOCK_PILLAR if passed else STATUS_REJECTED_TIER0_LOCK_PILLAR
    payload = {
        "scenario_id": scenario_id,
        "status": status,
        "present": list(present),
        "missing": list(missing),
        "unverified": unverified_list,
        "error_codes": error_codes,
    }
    return Tier0PreconditionAndLockReport(
        passed=passed,
        status=status,
        scenario_id=scenario_id,
        present_artifacts=present,
        missing_artifacts=missing,
        unverified_artifacts=tuple(unverified_list),
        tier0_complete=tier0_complete,
        dry_run_readiness_permitted=passed,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        report_sha256=_canonical_sha256(payload),
    )


def run_tier0_precondition_and_lock_4_scenario_suite() -> Tier0Lock4ScenarioSuiteResult:
    """Execute the 4 canonical Pillar C Tier-0 backup precondition & hardware write-lock scenarios."""
    r1 = verify_tier0_backup_precondition(
        build_synthetic_tier0_receipt(),
        scenario_id=TIER0_LOCK_SCENARIO_IDS[0],
    )
    r2 = verify_tier0_backup_precondition(
        build_synthetic_tier0_receipt(omit=("spi_nor_ddrtraining", "p6")),
        scenario_id=TIER0_LOCK_SCENARIO_IDS[1],
    )
    r3 = verify_tier0_backup_precondition(
        build_synthetic_tier0_receipt(unverified=("p18",)),
        scenario_id=TIER0_LOCK_SCENARIO_IDS[2],
    )
    r4 = verify_tier0_backup_precondition(
        build_synthetic_tier0_receipt(persistent_emmc_writes_requested=True),
        scenario_id=TIER0_LOCK_SCENARIO_IDS[3],
    )

    results = (r1, r2, r3, r4)
    suite_errors: List[str] = []
    passed_count = 0

    if r1.passed and r1.tier0_complete and r1.dry_run_readiness_permitted and (not r1.persistent_emmc_writes_authorized):
        passed_count += 1
    else:
        suite_errors.append(f"T0L1 failed: {r1.error_codes}")

    if (not r2.passed) and (not r2.dry_run_readiness_permitted) and BLOCKED_MISSING_TIER0_BACKUP_PRECONDITION in r2.error_codes:
        passed_count += 1
    else:
        suite_errors.append(f"T0L2 failed to block missing Tier-0 artifact: {r2.error_codes}")

    if (not r3.passed) and (not r3.dry_run_readiness_permitted) and BLOCKED_TIER0_READBACK_UNVERIFIED in r3.error_codes:
        passed_count += 1
    else:
        suite_errors.append(f"T0L3 failed to block unverified Tier-0 readback: {r3.error_codes}")

    if (not r4.passed) and (not r4.persistent_emmc_writes_authorized) and BLOCKED_HARDWARE_EMMC_WRITE_LOCKED in r4.error_codes:
        passed_count += 1
    else:
        suite_errors.append(f"T0L4 failed to lock persistent eMMC writes: {r4.error_codes}")

    all_ok = len(suite_errors) == 0 and passed_count == len(TIER0_LOCK_SCENARIO_IDS)
    suite_payload = {
        "scenarios": [
            {"id": r.scenario_id, "status": r.status, "passed": r.passed, "error_codes": list(r.error_codes)}
            for r in results
        ]
    }
    return Tier0Lock4ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_TIER0_LOCK_PILLAR if all_ok else STATUS_REJECTED_TIER0_LOCK_PILLAR,
        scenarios_passed=passed_count,
        scenarios_total=len(TIER0_LOCK_SCENARIO_IDS),
        scenario_results=results,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256(suite_payload),
    )


# ---------------------------------------------------------------------------
# Master Suite Entrypoint (Pillar 16)
# ---------------------------------------------------------------------------


def run_realhw_ext2_installer_and_p1_rescue_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> RealHwExt2InstallerAndP1RescueSuiteReport:
    """Run Phase 138 Pillar 16: O_RDONLY donor inspection, reversible A7C-II-style
    `/dev/nflasha15` (`ext2` `/usr`) atomic Stage-B installer & rollback engine,
    `p1`/`p3` mutual-exclusion & single-shot rescue initrd verifier, and Tier-0
    backup precondition + hard-locked write gate.
    """
    t0 = time.monotonic()
    donor_snap = inspect_realhw_ext2_and_p1_donors_readonly(force_clean_room=force_clean_room)

    # If live donor im.elf is available in LOCAL_DONOR_O_RDONLY mode, exercise its exact bytes in-memory!
    stock_im_bytes: Optional[bytes] = None
    if donor_snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
        im_path = resolve_donor_path(P138_DONOR_FX3_IM_ELF_RELPATH, require_file=True)
        if im_path.is_file():
            stock_im_bytes = read_file(str(im_path), 1024 * 1024)

    pillar_a = run_ext2_atomic_installer_6_scenario_suite(stock_im_elf_bytes=stock_im_bytes)
    pillar_b = run_p1_rescue_and_mutual_exclusion_6_scenario_suite()
    pillar_c = run_tier0_precondition_and_lock_4_scenario_suite()

    errors: List[str] = []
    if not donor_snap.cross_sku_distinct:
        errors.append("Cross-SKU FX3 7.02 / FX6 6.01 donor distinction verification failed.")
    errors.extend(pillar_a.errors)
    errors.extend(pillar_b.errors)
    errors.extend(pillar_c.errors)

    all_passed = (
        donor_snap.cross_sku_distinct
        and pillar_a.passed
        and pillar_b.passed
        and pillar_c.passed
        and (PHYSICAL_DEVICE_WRITES == 0)
        and (OTP_FUSE_TOUCHES == 0)
        and (OTP_FUSE_WRITES == 0)
        and (PASSIVE_TX_BYTES_EMITTED == 0)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
    )
    suite_payload = {
        "schema": REALHW_EXT2_P1_RESCUE_SCHEMA,
        "version": REALHW_EXT2_P1_RESCUE_VERSION,
        "mode": donor_snap.verification_mode,
        "donor_sha256": donor_snap.snapshot_sha256,
        "pillar_a_sha256": pillar_a.suite_sha256,
        "pillar_b_sha256": pillar_b.suite_sha256,
        "pillar_c_sha256": pillar_c.suite_sha256,
        "all_passed": all_passed,
    }
    elapsed = round(time.monotonic() - t0, 4)
    return RealHwExt2InstallerAndP1RescueSuiteReport(
        schema=REALHW_EXT2_P1_RESCUE_SCHEMA,
        version=REALHW_EXT2_P1_RESCUE_VERSION,
        status=STATUS_VERIFIED_REALHW_EXT2_P1_GATE if all_passed else STATUS_FAIL_REALHW_EXT2_P1_GATE,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_passed,
        read_only_donor_access=READ_ONLY_DONOR_ACCESS,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        donor_snapshot=donor_snap,
        pillar_a_ext2_installer_6_scenarios=pillar_a,
        pillar_b_p1_rescue_6_scenarios=pillar_b,
        pillar_c_tier0_lock_4_scenarios=pillar_c,
        suite_sha256=_canonical_sha256(suite_payload),
        elapsed_seconds=elapsed,
        errors=tuple(errors),
    )
