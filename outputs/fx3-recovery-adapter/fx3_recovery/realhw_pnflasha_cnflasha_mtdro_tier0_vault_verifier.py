"""Phase 151 — Pillar 19: Dual-Layer Tier-0 Cold-Backup Vault Verifier
(`/dev/pnflasha*` Raw ISP Ciphertext + `/dev/cnflasha*` Decrypted Logical +
`/dev/mtd*ro` SPI NOR + `Sector 0` 30-Partition LBA Geometry).

Implements two deterministic, read-only, anti-brick verification pillars for
real physical `ILME-FX3` (`7.02`, `CXD90057`, `Linux 4.9.337-scel+`) Tier-0
cold-backup and pre-Stage-B readiness while hard-locking:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `PHYSICAL_DEVICE_WRITES = 0`
- `MTD_RW_OPENS_OR_ERASE_IOCTLS = 0`

1. **Dual-Mode Donor Inspection (`os.O_RDONLY`) + Clean-Room Fallback**:
   - Inspects FX3 `7.02` donor artifacts (`partinf.conf`, `mount.conf`,
     `setup_nflash`, `insmod_drv1`, `nor_loader_writer.sh`, `pformat_config.txt`,
     `loader_nor.bin`, `libsencore.so`, `im.elf`, bounded 4 KiB header of
     `cpapp-b.bin`, and bounded 4 KiB ext2 superblock of `nflasha15.img`)
     strictly via `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)`.
   - Deterministically falls back to pinned `CLEAN_ROOM_SYNTHETIC` structural
     descriptors when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donors are absent,
     leaking zero raw Sony firmware bytes in `.to_dict()` / JSON.

2. **Pillar A — 16-Surface Dual-Layer Vault Manifest & Cross-Domain Restore Firewall**:
   - Models all 16 mandatory Tier-0 surfaces (`sector0`, `p1`, `p2`, `p3`, `p5`,
     `p6`, `p7`, `p8`, `p12`, `p13`, `p15`, `p18`, `p23`, `p30`,
     `spi_nor_mtd0ro`, `emmc_ext_csd`), tagging each surface's exact
     `layer_domain` (`RAW_PNFLASHA_ISP`, `SPACC_CNFLASHA_LOGICAL`,
     `SPI_NOR_MTDRO`, `EMMC_REG_METADATA`), expected FX3 `"8246"`/`"2.00"`
     30-partition `Sector 0` LBA start & sector count, and magic/entropy
     signature (`ext2` `0xEF53`, `SquashFS` `hsqs`, `BK4\\0`, `VX8900`, `WBI2`,
     `VFAT` `0x55AA`, and high-entropy SPACC ciphertext `>= 7.9 bits/byte`).
   - Enforces the 8-scenario Cross-Domain Restore Firewall:
     - Hard-blocks `SPACC_CNFLASHA_LOGICAL` plaintext -> `/dev/pnflasha*`
     - Hard-blocks `RAW_PNFLASHA_ISP` ciphertext -> `/dev/cnflasha*`
     - Hard-blocks `RAW_PNFLASHA_ISP` from a mismatched camera `body_serial` / `cid`
     - Hard-blocks `/dev/mtd*` (non-`ro`) paths & `MEMERASE`/`MEMWRITEOOB` ioctls
     - Enforces dual-copy (`SD ExFAT` + `Mac Host Vault`) SHA-256 & GF(256) RS P+Q
       bit-rot detection/healing.

3. **Pillar B — `/dev/mtd*ro` SPI NOR & `p12/p13/p18/p23/p30` Factory Calibration Gate**:
   - Enforces `/proc/mtd` -> `/dev/mtd0ro..mtdNro` read-only dump discipline
     (`IPL / BLoader / BL31 / Boot Config` envelope, erase-block alignment, zero
     `O_WRONLY`/`O_RDWR`), plus per-camera unique `p12/p13` (`ID/NVS`), `p18`
     (`/lens` `VX8900`), and `p23/p30` (`Backup.bin` `BK4\\0`) dual-copy SHA-256
     lock before any Stage-B userland test is eligible for human review.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .emmc_dump_forensic_verifier import (
    BK4_HEADER_SIZE,
    BK4_MAGIC,
    BK4_SYNC_MARKER,
    EXT_CSD_BOOT_BUS_COND_IDX,
    EXT_CSD_BOOT_SIZE_MULT_IDX,
    EXT_CSD_PART_CONFIG_IDX,
    EXT_CSD_SIZE,
    FX3_PRODUCT_MODEL_ID,
    WBI2_MAGIC,
    compute_shannon_entropy,
)
from .files import is_forced_clean_room, local_path, resolve_donor_path
from .tier0_backup_parity_and_manifest_guard import (
    Gf256ParityStripe,
    encode_gf256_pq_parity,
    heal_gf256_pq_shards,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE151_SCHEMA: str = "fx3-realhw-pnflasha-cnflasha-mtdro-tier0-vault-v1"
PHASE151_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
MTD_RW_OPENS_OR_ERASE_IOCTLS: int = 0

# Layer Domains
DOMAIN_RAW_PNFLASHA_ISP: str = "RAW_PNFLASHA_ISP"
DOMAIN_SPACC_CNFLASHA_LOGICAL: str = "SPACC_CNFLASHA_LOGICAL"
DOMAIN_SPI_NOR_MTDRO: str = "SPI_NOR_MTDRO"
DOMAIN_EMMC_REG_METADATA: str = "EMMC_REG_METADATA"
VALID_LAYER_DOMAINS: Tuple[str, ...] = (
    DOMAIN_RAW_PNFLASHA_ISP,
    DOMAIN_SPACC_CNFLASHA_LOGICAL,
    DOMAIN_SPI_NOR_MTDRO,
    DOMAIN_EMMC_REG_METADATA,
)

# Geometry, Magic & Entropy Constants
SECTOR_SIZE_BYTES: int = 512
SECTOR0_MAGIC: bytes = b"8246"
SECTOR0_VERSION: bytes = b"2.00"
SECTOR0_ENTRY_COUNT: int = 30
EXT2_SUPER_MAGIC: int = 0xEF53
SQUASHFS_MAGIC: bytes = b"hsqs"
LENS_VX8900_MAGIC: bytes = b"VX8900"
VFAT_BOOT_SIG: bytes = b"\x55\xaa"
SPACC_CIPHERTEXT_MIN_ENTROPY_BITS: float = 7.9

SPI_NOR_TOTAL_BYTES: int = 16 * 1024 * 1024
SPI_NOR_ERASE_SECTOR_BYTES: int = 4096
SPI_NOR_ERASE_BLOCK_BYTES: int = 65536
SPI_NOR_REQUIRED_BOOT_STAGES: Tuple[str, ...] = (
    "IPL",
    "BLoader",
    "BL31",
    "BootConfig",
)

FORBIDDEN_MTD_IOCTLS: Tuple[str, ...] = (
    "MEMERASE",
    "MEMERASE64",
    "MEMWRITEOOB",
    "MEMWRITEOOB64",
    "MEMLOCK",
    "MEMUNLOCK",
    "OTPLOCK",
)
FORBIDDEN_MTD_OPEN_MODES: Tuple[str, ...] = ("O_WRONLY", "O_RDWR", "rw", "w", "w+", "a", "a+")

# Donor Relative Paths & Pinned Anchors (strictly O_RDONLY, zero raw bytes in JSON)
P151_DONOR_FX3_PARTINF_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0300_partconf/partinf.conf"
)
P151_DONOR_FX3_MOUNT_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0100_config/mount.conf"
)
P151_DONOR_FX3_SETUP_NFLASH_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/p3-initrd/sbin/initrc/setup_nflash"
)
P151_DONOR_FX3_INSMOD_DRV1_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/p3-initrd/sbin/initrc/insmod_drv1"
)
P151_DONOR_FX3_NOR_LOADER_WRITER_RELPATH: str = (
    "sony-firmware-20261024/stage212-official-boot-backup-generator/"
    "originals/bin/nor_loader_writer.sh"
)
P151_DONOR_FX3_PFORMAT_CONFIG_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/nor-loader-members/pformat_config.txt"
)
P151_DONOR_FX3_LOADER_NOR_BIN_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/nor-loader-members/loader_nor.bin"
)
P151_DONOR_FX3_LIBSENCORE_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libsencore.so"
)
P151_DONOR_FX3_IM_ELF_RELPATH: str = (
    "sony-firmware-20261024/stage183-request-consumer-and-early-entry/"
    "evidence/usb-main-dependency/originals/bin/im.elf"
)
P151_DONOR_FX3_CPAPP_B_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"
)
P151_DONOR_FX3_NFLASHA15_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/nflasha15.img"
)

P151_PINNED_FX3_PARTINF_BYTES: int = 3999
P151_PINNED_FX3_PARTINF_SHA256: str = "3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189"
P151_PINNED_FX3_MOUNT_BYTES: int = 1248
P151_PINNED_FX3_MOUNT_SHA256: str = "ea0132091f3bb8d675b3ae7aecfbb1ca2459864a2e2812c0f7dd66fbb877d1a3"
P151_PINNED_FX3_SETUP_NFLASH_BYTES: int = 375
P151_PINNED_FX3_SETUP_NFLASH_SHA256: str = "055cb3db7a40084aef8aaa89a7357921b514bf0af89690f920b608d9f3734cdc"
P151_PINNED_FX3_INSMOD_DRV1_BYTES: int = 152
P151_PINNED_FX3_INSMOD_DRV1_SHA256: str = "22f29d06d7776fe5e8362c17049beabfd3e3bebffd222e51276e3704d483a591"
P151_PINNED_FX3_NOR_LOADER_WRITER_BYTES: int = 9106
P151_PINNED_FX3_NOR_LOADER_WRITER_SHA256: str = "78b794fc52c5e104a899a6bf23278bd211e4a4f3c987a505bc43d648fcb5c2d6"
P151_PINNED_FX3_PFORMAT_CONFIG_BYTES: int = 1274
P151_PINNED_FX3_PFORMAT_CONFIG_SHA256: str = "21cd5b29dd165c322f5b00bb057802c377ff94af15f95881e150a32130302ece"
P151_PINNED_FX3_LOADER_NOR_BIN_BYTES: int = 101888
P151_PINNED_FX3_LOADER_NOR_BIN_SHA256: str = "4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942"
P151_PINNED_FX3_LIBSENCORE_BYTES: int = 377328
P151_PINNED_FX3_LIBSENCORE_SHA256: str = "a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410"
P151_PINNED_FX3_IM_ELF_BYTES: int = 40920
P151_PINNED_FX3_IM_ELF_SHA256: str = "5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91"
P151_PINNED_FX3_CPAPP_B_BYTES: int = 15980568
P151_PINNED_FX3_CPAPP_B_HDR4K_SHA256: str = "452c9e4e05fc1942baeee8ea9d531eeaaab99091576bc59eaa46f2d272050d5d"
P151_PINNED_FX3_NFLASHA15_BYTES: int = 479846400
P151_PINNED_FX3_NFLASHA15_HDR4K_SHA256: str = "6d05ebbd28c554d1d9dcc54503face9af111170befaf2ca2a19c52d7bd8910d6"

# Status & Fail-Closed Error Codes
STATUS_VERIFIED_SUITE: str = "VERIFIED_TIER0_DUAL_LAYER_VAULT_GATE"
STATUS_FAIL_SUITE: str = "FAIL_TIER0_DUAL_LAYER_VAULT_GATE"
STATUS_VERIFIED_PILLAR_A: str = "VERIFIED_16_SURFACE_DUAL_LAYER_VAULT_AND_FIREWALL"
STATUS_REJECTED_PILLAR_A: str = "REJECTED_16_SURFACE_DUAL_LAYER_VAULT_OR_FIREWALL"
STATUS_VERIFIED_PILLAR_B: str = "VERIFIED_MTDRO_SPI_NOR_AND_FACTORY_CAL_LOCK_GATE"
STATUS_REJECTED_PILLAR_B: str = "REJECTED_MTDRO_SPI_NOR_OR_FACTORY_CAL_LOCK_GATE"

BLOCKED_CROSS_DOMAIN_CNFLASHA_TO_PNFLASHA: str = "BLOCKED_CROSS_DOMAIN_CNFLASHA_PLAINTEXT_TO_PNFLASHA_RAW"
BLOCKED_CROSS_DOMAIN_PNFLASHA_TO_CNFLASHA: str = "BLOCKED_CROSS_DOMAIN_PNFLASHA_CIPHERTEXT_TO_CNFLASHA_LOGICAL"
BLOCKED_CROSS_CAMERA_SPACC_OTP_KEY_MISMATCH: str = "BLOCKED_CROSS_CAMERA_RAW_PNFLASHA_SPACC_OTP_MISMATCH"
BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN: str = "BLOCKED_MTD_RW_DEVICE_OPEN_OR_MEMERASE_IOCTL_FORBIDDEN"
BLOCKED_DUAL_COPY_BITROT_DETECTED: str = "BLOCKED_DUAL_COPY_SD_VS_MAC_BITROT_DETECTED"
BLOCKED_SECTOR0_LBA_GEOMETRY_MISMATCH: str = "BLOCKED_SECTOR0_30_PARTITION_LBA_GEOMETRY_MISMATCH"
BLOCKED_SPI_NOR_ENVELOPE_OR_ALIGNMENT_INVALID: str = "BLOCKED_SPI_NOR_ENVELOPE_OR_ERASE_ALIGNMENT_INVALID"
BLOCKED_P18_LENS_VX8900_INTEGRITY_FAILURE: str = "BLOCKED_P18_LENS_VX8900_INTEGRITY_FAILURE"
BLOCKED_P23_P30_BK4_INTEGRITY_FAILURE: str = "BLOCKED_P23_P30_BK4_INTEGRITY_FAILURE"
BLOCKED_CROSS_CAMERA_FACTORY_CAL_LOCK: str = "BLOCKED_CROSS_CAMERA_P12_P13_P18_P23_P30_FACTORY_CAL_LOCK"
ERR_MISSING_TIER0_SURFACES: str = "ERR_MISSING_MANDATORY_16_TIER0_SURFACES"
ERR_INVALID_MAGIC_OR_LOW_ENTROPY: str = "ERR_INVALID_SURFACE_MAGIC_OR_SPACC_LOW_ENTROPY"
ERR_GF256_UNHEALABLE_BITROT: str = "ERR_GF256_UNHEALABLE_QUORUM_LOSS"
ERR_WRITE_AUTH_LOCKED: str = "ERR_PERSISTENT_EMMC_OR_SPI_NOR_WRITES_LOCKED_FALSE"

# Canonical 30-entry FX3 7.02 Sector 0 Partition Geometry (from partinf.conf / FX3 UDA)
# Tuple: (index, start_lba, sector_count, partinf_type, spacc_encrypted, mountpoint, label)
FX3_30_PARTITION_TABLE: Tuple[Tuple[int, int, int, int, bool, str, str], ...] = (
    (1, 0x00000080, 0x0000BF80, 5, False, "none", "p1:/updater"),
    (2, 0x0000C000, 0x0000A000, 5, False, "/setting", "p2:/setting"),
    (3, 0x00016000, 0x00025800, 5, True, "/system", "p3:/system"),
    (4, 0x0003B800, 0x00006000, 4, False, "none", "p4:/mpr_bkup"),
    (5, 0x00041800, 0x00096000, 6, False, "/wbi", "p5:/wbi"),
    (6, 0x000D7800, 0x0000C800, 5, False, "none", "p6:/tmp/jiritsu"),
    (7, 0x000E4000, 0x00008000, 4, True, "/rootfs", "p7:/rootfs"),
    (8, 0x000EC000, 0x00020000, 5, True, "/cp", "p8:/cp"),
    (9, 0x0010C000, 0x00000000, 4, False, "none", "p9:reserved"),
    (10, 0x0010C000, 0x00006000, 5, False, "/tmp", "p10:/work"),
    (11, 0x00112000, 0x000FA000, 5, False, "/log", "p11:/log"),
    (12, 0x0020C000, 0x00014000, 5, True, "/cert", "p12:/cert"),
    (13, 0x00220000, 0x00002000, 5, False, "none", "p13:/updater_work"),
    (14, 0x00222000, 0x00000000, 4, False, "none", "p14:reserved"),
    (15, 0x00222000, 0x000FA000, 4, True, "/usr", "p15:/usr"),
    (16, 0x0031C000, 0x00000000, 4, False, "none", "p16:reserved"),
    (17, 0x0031C000, 0x00000000, 4, False, "none", "p17:reserved"),
    (18, 0x0031C000, 0x0000A000, 5, False, "/lens", "p18:/lens"),
    (19, 0x00326000, 0x00000000, 4, False, "none", "p19:reserved"),
    (20, 0x00326000, 0x00000000, 4, False, "none", "p20:reserved"),
    (21, 0x00326000, 0x00000000, 4, False, "none", "p21:reserved"),
    (22, 0x00326000, 0x00000000, 4, False, "none", "p22:reserved"),
    (23, 0x00326000, 0x00020000, 5, True, "/PMBP", "p23:/pmbp"),
    (24, 0x00346000, 0x00000000, 4, False, "none", "p24:reserved"),
    (25, 0x00346000, 0x00000000, 4, False, "/MP3", "p25:reserved"),
    (26, 0x00346000, 0x00000000, 4, False, "/BGM", "p26:reserved"),
    (27, 0x00346000, 0x00000000, 4, False, "none", "p27:reserved"),
    (28, 0x00346000, 0x00000000, 4, False, "none", "p28:reserved"),
    (29, 0x00346000, 0x00000000, 4, False, "none", "p29:reserved"),
    (30, 0x00346000, 0x00018000, 5, True, "/usr/data/lut", "p30:/lutdata"),
)

_PARTITION_BY_INDEX: Dict[int, Tuple[int, int, int, int, bool, str, str]] = {
    row[0]: row for row in FX3_30_PARTITION_TABLE
}


@dataclass(frozen=True)
class Tier0SurfaceSpec:
    surface_id: str
    partition_index: Optional[int]
    primary_layer_domain: str
    spacc_encrypted: bool
    raw_device_node: str
    logical_device_node: str
    expected_start_lba: Optional[int]
    expected_sector_count: Optional[int]
    expected_byte_size: int
    expected_magic_kind: str
    per_camera_unique: bool
    description: str


TIER0_16_SURFACES: Tuple[Tier0SurfaceSpec, ...] = (
    Tier0SurfaceSpec("sector0", 0, DOMAIN_RAW_PNFLASHA_ISP, False, "/dev/pnflasha", "/dev/nflasha", 0, 1, 512, "SECTOR0_8246", False, "30-partition Sony PTBL 8246/2.00"),
    Tier0SurfaceSpec("p1", 1, DOMAIN_RAW_PNFLASHA_ISP, False, "/dev/pnflasha1", "/dev/nflasha1", 0x00000080, 0x0000BF80, 0x0000BF80 * 512, "VFAT_OR_SQUASHFS", False, "Updater VFAT + initrd/kernel"),
    Tier0SurfaceSpec("p2", 2, DOMAIN_RAW_PNFLASHA_ISP, False, "/dev/pnflasha2", "/dev/nflasha2", 0x0000C000, 0x0000A000, 0x0000A000 * 512, "BK4_NVRAM", True, "/setting Backup.bin BK4\\0"),
    Tier0SurfaceSpec("p3", 3, DOMAIN_SPACC_CNFLASHA_LOGICAL, True, "/dev/pnflasha3", "/dev/cnflasha3", 0x00016000, 0x00025800, 0x00025800 * 512, "VFAT_OR_SQUASHFS", False, "/system 75 MiB dual-layer"),
    Tier0SurfaceSpec("p5", 5, DOMAIN_RAW_PNFLASHA_ISP, False, "/dev/pnflasha5", "/dev/nflasha5", 0x00041800, 0x00096000, 0x00096000 * 512, "WBI2", False, "/wbi 300 MiB hibernation"),
    Tier0SurfaceSpec("p6", 6, DOMAIN_RAW_PNFLASHA_ISP, False, "/dev/pnflasha6", "/dev/nflasha6", 0x000D7800, 0x0000C800, 0x0000C800 * 512, "VFAT", False, "Jiritsu 25 MiB staging VFAT"),
    Tier0SurfaceSpec("p7", 7, DOMAIN_SPACC_CNFLASHA_LOGICAL, True, "/dev/pnflasha7", "/dev/cnflasha7", 0x000E4000, 0x00008000, 0x00008000 * 512, "EXT2_OR_SQUASHFS", False, "/rootfs 16 MiB dual-layer"),
    Tier0SurfaceSpec("p8", 8, DOMAIN_SPACC_CNFLASHA_LOGICAL, True, "/dev/pnflasha8", "/dev/cnflasha8", 0x000EC000, 0x00020000, 0x00020000 * 512, "VFAT", False, "/cp 64 MiB cpapp-b.bin dual-layer"),
    Tier0SurfaceSpec("p12", 12, DOMAIN_SPACC_CNFLASHA_LOGICAL, True, "/dev/pnflasha12", "/dev/cnflasha12", 0x0020C000, 0x00014000, 0x00014000 * 512, "VFAT", True, "/cert 40 MiB ID/NVS dual-layer"),
    Tier0SurfaceSpec("p13", 13, DOMAIN_RAW_PNFLASHA_ISP, False, "/dev/pnflasha13", "/dev/nflasha13", 0x00220000, 0x00002000, 0x00002000 * 512, "VFAT", True, "UpdaterWork 4 MiB ID/NVS"),
    Tier0SurfaceSpec("p15", 15, DOMAIN_SPACC_CNFLASHA_LOGICAL, True, "/dev/pnflasha15", "/dev/cnflasha15", 0x00222000, 0x000FA000, 0x000FA000 * 512, "EXT2", False, "/usr 500 MiB ext2 dual-layer"),
    Tier0SurfaceSpec("p18", 18, DOMAIN_RAW_PNFLASHA_ISP, False, "/dev/pnflasha18", "/dev/nflasha18", 0x0031C000, 0x0000A000, 0x0000A000 * 512, "LENS_VX8900", True, "/lens 20 MiB lensfile.bin VX8900"),
    Tier0SurfaceSpec("p23", 23, DOMAIN_SPACC_CNFLASHA_LOGICAL, True, "/dev/pnflasha23", "/dev/cnflasha23", 0x00326000, 0x00020000, 0x00020000 * 512, "BK4_OR_VFAT", True, "/PMBP 64 MiB Backup.bin/BK4 dual-layer"),
    Tier0SurfaceSpec("p30", 30, DOMAIN_SPACC_CNFLASHA_LOGICAL, True, "/dev/pnflasha30", "/dev/cnflasha30", 0x00346000, 0x00018000, 0x00018000 * 512, "BK4_OR_VFAT", True, "/usr/data/lut 48 MiB Backup.bin/LUT dual-layer"),
    Tier0SurfaceSpec("spi_nor_mtd0ro", None, DOMAIN_SPI_NOR_MTDRO, False, "/dev/mtd0ro", "/dev/mtd0ro", None, None, SPI_NOR_TOTAL_BYTES, "SPI_NOR_ENVELOPE", True, "SPI NOR /dev/mtd0ro IPL/BLoader/BL31/BootConfig"),
    Tier0SurfaceSpec("emmc_ext_csd", None, DOMAIN_EMMC_REG_METADATA, False, "/sys/kernel/debug/mmc0/mmc0:0001/ext_csd", "/sys/kernel/debug/mmc0/mmc0:0001/ext_csd", None, None, EXT_CSD_SIZE, "EXT_CSD", True, "512 B JEDEC EXT_CSD register dump"),
)

MANDATORY_16_SURFACE_IDS: Tuple[str, ...] = tuple(s.surface_id for s in TIER0_16_SURFACES)
_SURFACE_SPEC_MAP: Dict[str, Tier0SurfaceSpec] = {s.surface_id: s for s in TIER0_16_SURFACES}

PER_CAMERA_CAL_SURFACE_IDS: Tuple[str, ...] = ("p12", "p13", "p18", "p23", "p30")

PILLAR_A_SCENARIO_IDS: Tuple[str, ...] = (
    "PA1_HAPPY_16_SURFACE_DUAL_LAYER_VAULT",
    "PA2_BLOCKED_CNFLASHA_PLAINTEXT_TO_PNFLASHA_TARGET",
    "PA3_BLOCKED_PNFLASHA_CIPHERTEXT_TO_CNFLASHA_TARGET",
    "PA4_BLOCKED_CROSS_CAMERA_RAW_PNFLASHA_OTP_MISMATCH",
    "PA5_BLOCKED_MTD_NON_RO_OR_MEMERASE_IOCTL",
    "PA6_BLOCKED_DUAL_COPY_SD_VS_MAC_BITROT_UNHEALED",
    "PA7_HEALED_GF256_RS_PQ_BITROT_SHARD_RECOVERY",
    "PA8_BLOCKED_SECTOR0_30_PART_LBA_OR_FX6_SHIFT",
)

PILLAR_B_SCENARIO_IDS: Tuple[str, ...] = (
    "PB1_HAPPY_MTD0RO_AND_P12_P13_P18_P23_P30_LOCKED",
    "PB2_BLOCKED_MTD_NON_RO_OR_RDWR_OPEN",
    "PB3_BLOCKED_SPI_NOR_ERASE_UNALIGNED_OR_MISSING_STAGE",
    "PB4_BLOCKED_P18_MISSING_VX8900_OR_CORRUPTED",
    "PB5_BLOCKED_P23_P30_BK4_CHECKSUM_OR_MODEL_MISMATCH",
    "PB6_BLOCKED_P12_P13_CROSS_CAMERA_ID_NVS_TRANSPLANT",
)

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_MTD_PROC_LINE_RE = re.compile(r'^(mtd\d+):\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+"([^"]+)"$')
_DEV_MTD_RE = re.compile(r"^/dev/mtd(\d+)(ro)?$")
_DEV_NFLASH_RE = re.compile(r"^/dev/(pnflasha|cnflasha|nflasha)(\d*)$")


# ---------------------------------------------------------------------------
# Dataclasses (Zero raw firmware bytes in serialized outputs)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Tier0DonorArtifactDigest:
    artifact_id: str
    relpath: str
    source_mode: str
    access_mode: str
    byte_length: int
    sha256_digest: str
    header_4k_sha256: Optional[str]
    verified_markers: Tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class Tier0DualLayerDonorSnapshot:
    verification_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    partinf_partition_count: int
    mount_entry_count: int
    setup_nflash_aliases_verified: bool
    nor_loader_writer_markers_verified: bool
    artifacts: Tuple[Tier0DonorArtifactDigest, ...]
    all_passed: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Sector0PartitionEntryInfo:
    index: int
    start_lba: int
    sector_count: int
    ptype: int
    flag: int


@dataclass(frozen=True)
class Sector0GeometryReport:
    valid: bool
    magic_ascii: str
    version_ascii: str
    entry_count: int
    active_partition_count: int
    has_overlaps: bool
    fx3_lba_geometry_ok: bool
    entries: Tuple[Sector0PartitionEntryInfo, ...]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DualLayerSurfaceEntry:
    surface_id: str
    layer_domain: str
    device_node: str
    start_lba: Optional[int]
    sector_count: Optional[int]
    byte_size: int
    magic_kind: str
    header_sample_hex_digest: str
    shannon_entropy_bits: float
    sd_exfat_sha256: str
    mac_host_vault_sha256: str
    body_serial_sha256: str
    emmc_cid_sha256: str
    raw_isp_sha256: Optional[str] = None
    raw_isp_entropy_bits: Optional[float] = None
    gf256_parity_attached: bool = False
    gf256_healed_ok: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SurfaceAuditResult:
    surface_id: str
    layer_domain: str
    passed: bool
    magic_ok: bool
    lba_geometry_ok: bool
    entropy_ok: bool
    dual_copy_parity_ok: bool
    identity_lock_ok: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DualLayer16SurfaceManifestReport:
    passed: bool
    status: str
    surface_count: int
    mandatory_16_complete: bool
    raw_pnflasha_surfaces: Tuple[str, ...]
    spacc_cnflasha_surfaces: Tuple[str, ...]
    spi_nor_mtdro_surfaces: Tuple[str, ...]
    emmc_reg_surfaces: Tuple[str, ...]
    sector0_geometry: Sector0GeometryReport
    surface_results: Tuple[SurfaceAuditResult, ...]
    missing_surfaces: Tuple[str, ...]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RestorePairingDecision:
    allowed: bool
    blocked_code: Optional[str]
    source_layer_domain: str
    target_layer_domain: str
    source_partition: Optional[int]
    target_device_path: str
    reason: str
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PillarAScenarioResult:
    scenario_id: str
    passed: bool
    expected_outcome: str
    observed_code: str
    details: Dict[str, Any]


@dataclass(frozen=True)
class PillarAFirewall8ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[PillarAScenarioResult, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProcMtdRegionInfo:
    mtd_name: str
    device_node_ro: str
    size_bytes: int
    erasesize_bytes: int
    label: str


@dataclass(frozen=True)
class SpiNorMtdRoAuditReport:
    valid: bool
    device_path: str
    open_mode: str
    ioctl_requested: Optional[str]
    proc_mtd_regions: Tuple[ProcMtdRegionInfo, ...]
    total_bytes: int
    erasesize_bytes: int
    erase_aligned: bool
    detected_boot_stages: Tuple[str, ...]
    missing_boot_stages: Tuple[str, ...]
    spi_nor_sha256: str
    dual_copy_parity_ok: bool
    mtd_rw_opens_or_erase_ioctls: int
    spi_nor_write_authorized: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PerCameraCalSurfaceCheck:
    surface_id: str
    passed: bool
    magic_verified: bool
    dual_copy_sha256_locked: bool
    body_identity_locked: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SpiNorAndFactoryCalGateReport:
    passed: bool
    status: str
    stage_b_human_review_eligible: bool
    spi_nor_audit: SpiNorMtdRoAuditReport
    factory_cal_checks: Tuple[PerCameraCalSurfaceCheck, ...]
    body_serial_sha256: str
    emmc_cid_sha256: str
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PillarBScenarioResult:
    scenario_id: str
    passed: bool
    stage_b_human_review_eligible: bool
    observed_code: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PillarBGate6ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[PillarBScenarioResult, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Tier0DualLayerVaultSuiteReport:
    schema: str
    version: str
    status: str
    verification_mode: str
    all_passed: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    read_only_donor_access: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    passive_tx_bytes_emitted: int
    physical_device_writes: int
    mtd_rw_opens_or_erase_ioctls: int
    raw_firmware_bytes_leaked: int
    donor_snapshot: Tier0DualLayerDonorSnapshot
    pillar_a_vault_manifest_report: DualLayer16SurfaceManifestReport
    pillar_a_firewall_8_scenarios: PillarAFirewall8ScenarioSuiteResult
    pillar_b_spi_nor_and_cal_gate_report: SpiNorAndFactoryCalGateReport
    pillar_b_gate_6_scenarios: PillarBGate6ScenarioSuiteResult
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Read-Only Bounded O_RDONLY File Reader & Donor Inspection
# ---------------------------------------------------------------------------


def _read_regular_file_readonly(path: Path, max_bytes: int, bounded_head_bytes: Optional[int] = None) -> Tuple[int, bytes]:
    """Open regular file strictly with O_RDONLY | O_NOFOLLOW | O_NONBLOCK."""
    checked = local_path(path, allow_donor_roots=True)
    fd = os.open(checked, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            raise ValueError(f"Non-regular or multi-link donor rejected: {checked}")
        if st.st_size < 0 or st.st_size > max_bytes:
            raise ValueError(f"Donor size out of bounds ({st.st_size} > {max_bytes}): {checked}")
        to_read = st.st_size if bounded_head_bytes is None else min(st.st_size, bounded_head_bytes)
        chunks: List[bytes] = []
        remaining = to_read
        while remaining > 0:
            block = os.read(fd, remaining)
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        return int(st.st_size), b"".join(chunks)
    finally:
        os.close(fd)


def _parse_partinf_conf_text(text: str) -> Tuple[Tuple[int, int, int, int], ...]:
    rows: List[Tuple[int, int, int, int]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 4:
            continue
        rows.append(tuple(int(p, 0) for p in parts))  # type: ignore[arg-type]
    return tuple(rows)


def _parse_mount_conf_text(text: str) -> Tuple[Tuple[str, str, str, int, int], ...]:
    rows: List[Tuple[str, str, str, int, int]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        cols = line.split()
        if len(cols) != 5:
            continue
        rows.append((cols[0], cols[1], cols[2], int(cols[3]), int(cols[4])))
    return tuple(rows)


def inspect_tier0_dual_layer_donors_readonly(
    force_clean_room: Optional[bool] = None,
) -> Tier0DualLayerDonorSnapshot:
    """Inspect real FX3 7.02 Tier-0 donor artifacts strictly via O_RDONLY, or deterministic clean-room."""
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        synthetic_digests = (
            Tier0DonorArtifactDigest("partinf_conf", P151_DONOR_FX3_PARTINF_RELPATH, "CLEAN_ROOM_SYNTHETIC", "SYNTHETIC_METADATA", P151_PINNED_FX3_PARTINF_BYTES, P151_PINNED_FX3_PARTINF_SHA256, None, ("30_partitions", "p1=0x80:0xbf80", "p18=0x31c000:0xa000"), True),
            Tier0DonorArtifactDigest("mount_conf", P151_DONOR_FX3_MOUNT_RELPATH, "CLEAN_ROOM_SYNTHETIC", "SYNTHETIC_METADATA", P151_PINNED_FX3_MOUNT_BYTES, P151_PINNED_FX3_MOUNT_SHA256, None, ("/setting", "/system", "/rootfs", "/cp", "/cert", "/usr", "/lens", "/PMBP"), True),
            Tier0DonorArtifactDigest("setup_nflash", P151_DONOR_FX3_SETUP_NFLASH_RELPATH, "CLEAN_ROOM_SYNTHETIC", "SYNTHETIC_METADATA", P151_PINNED_FX3_SETUP_NFLASH_BYTES, P151_PINNED_FX3_SETUP_NFLASH_SHA256, None, ("pnflasha->nflasha", "cnflasha->nflasha"), True),
            Tier0DonorArtifactDigest("insmod_drv1", P151_DONOR_FX3_INSMOD_DRV1_RELPATH, "CLEAN_ROOM_SYNTHETIC", "SYNTHETIC_METADATA", P151_PINNED_FX3_INSMOD_DRV1_BYTES, P151_PINNED_FX3_INSMOD_DRV1_SHA256, None, ("crypt-emmc.ko", "emmc.ko"), True),
            Tier0DonorArtifactDigest("nor_loader_writer", P151_DONOR_FX3_NOR_LOADER_WRITER_RELPATH, "CLEAN_ROOM_SYNTHETIC", "SYNTHETIC_METADATA", P151_PINNED_FX3_NOR_LOADER_WRITER_BYTES, P151_PINNED_FX3_NOR_LOADER_WRITER_SHA256, None, ("loader_nor.bin", "LdrBkup.bin", "DGU.bin", "MIS.bin", "ddrtraining.dat"), True),
            Tier0DonorArtifactDigest("pformat_config", P151_DONOR_FX3_PFORMAT_CONFIG_RELPATH, "CLEAN_ROOM_SYNTHETIC", "SYNTHETIC_METADATA", P151_PINNED_FX3_PFORMAT_CONFIG_BYTES, P151_PINNED_FX3_PFORMAT_CONFIG_SHA256, None, ("loader_nor.bin@72", "LdrBkup.bin@68", "MIS.bin@512"), True),
            Tier0DonorArtifactDigest("loader_nor_bin", P151_DONOR_FX3_LOADER_NOR_BIN_RELPATH, "CLEAN_ROOM_SYNTHETIC", "SYNTHETIC_METADATA", P151_PINNED_FX3_LOADER_NOR_BIN_BYTES, P151_PINNED_FX3_LOADER_NOR_BIN_SHA256, None, ("101888B_NOR_LOADER",), True),
            Tier0DonorArtifactDigest("libsencore_so", P151_DONOR_FX3_LIBSENCORE_RELPATH, "CLEAN_ROOM_SYNTHETIC", "SYNTHETIC_METADATA", P151_PINNED_FX3_LIBSENCORE_BYTES, P151_PINNED_FX3_LIBSENCORE_SHA256, None, ("ELF64_AArch64", "AdjustControlFunc", "TransactionStart"), True),
            Tier0DonorArtifactDigest("im_elf", P151_DONOR_FX3_IM_ELF_RELPATH, "CLEAN_ROOM_SYNTHETIC", "SYNTHETIC_METADATA", P151_PINNED_FX3_IM_ELF_BYTES, P151_PINNED_FX3_IM_ELF_SHA256, None, ("ELF64_AArch64_ET_EXEC",), True),
            Tier0DonorArtifactDigest("cpapp_b_bin", P151_DONOR_FX3_CPAPP_B_RELPATH, "CLEAN_ROOM_SYNTHETIC", "SYNTHETIC_METADATA", P151_PINNED_FX3_CPAPP_B_BYTES, P151_PINNED_FX3_CPAPP_B_HDR4K_SHA256, P151_PINNED_FX3_CPAPP_B_HDR4K_SHA256, ("ARMv7R_0x00108000",), True),
            Tier0DonorArtifactDigest("nflasha15_img", P151_DONOR_FX3_NFLASHA15_RELPATH, "CLEAN_ROOM_SYNTHETIC", "SYNTHETIC_METADATA", P151_PINNED_FX3_NFLASHA15_BYTES, P151_PINNED_FX3_NFLASHA15_HDR4K_SHA256, P151_PINNED_FX3_NFLASHA15_HDR4K_SHA256, ("ext2_0xEF53",), True),
        )
        return Tier0DualLayerDonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_METADATA_ONLY",
            donor_files_inspected=0,
            raw_firmware_bytes_leaked=0,
            partinf_partition_count=30,
            mount_entry_count=30,
            setup_nflash_aliases_verified=True,
            nor_loader_writer_markers_verified=True,
            artifacts=synthetic_digests,
            all_passed=True,
            errors=(),
        )

    relpaths = (
        P151_DONOR_FX3_PARTINF_RELPATH,
        P151_DONOR_FX3_MOUNT_RELPATH,
        P151_DONOR_FX3_SETUP_NFLASH_RELPATH,
        P151_DONOR_FX3_INSMOD_DRV1_RELPATH,
        P151_DONOR_FX3_NOR_LOADER_WRITER_RELPATH,
        P151_DONOR_FX3_PFORMAT_CONFIG_RELPATH,
        P151_DONOR_FX3_LOADER_NOR_BIN_RELPATH,
        P151_DONOR_FX3_LIBSENCORE_RELPATH,
        P151_DONOR_FX3_IM_ELF_RELPATH,
        P151_DONOR_FX3_CPAPP_B_RELPATH,
        P151_DONOR_FX3_NFLASHA15_RELPATH,
    )
    resolved = [resolve_donor_path(rel, require_file=True) for rel in relpaths]
    if any(p is None or (not p.is_file()) for p in resolved):
        return inspect_tier0_dual_layer_donors_readonly(force_clean_room=True)

    errors: List[str] = []
    artifacts: List[Tier0DonorArtifactDigest] = []

    def _inspect_full(artifact_id: str, rel: str, p: Path, exp_bytes: int, exp_sha: str, marker_fn: Any) -> Tier0DonorArtifactDigest:
        sz, data = _read_regular_file_readonly(p, 8 * 1024 * 1024)
        digest = sha256(data).hexdigest()
        markers, m_ok = marker_fn(data)
        ok = (sz == exp_bytes) and (digest == exp_sha) and m_ok
        if not ok:
            errors.append(f"DONOR_MISMATCH:{artifact_id}:size={sz},sha={digest[:16]}")
        return Tier0DonorArtifactDigest(artifact_id, rel, "LOCAL_DONOR_RDONLY", "O_RDONLY", sz, digest, None, tuple(markers), ok)

    # 1. partinf.conf
    partinf_rows: Tuple[Tuple[int, int, int, int], ...] = ()
    def _chk_partinf(data: bytes) -> Tuple[List[str], bool]:
        nonlocal partinf_rows
        partinf_rows = _parse_partinf_conf_text(data.decode("utf-8", errors="replace"))
        ok = len(partinf_rows) == 30 and partinf_rows[0][:2] == (0x80, 0xBF80) and partinf_rows[17][:2] == (0x31C000, 0xA000)
        return (["30_partitions", "p1=0x80:0xbf80", "p18=0x31c000:0xa000"] if ok else []), ok

    artifacts.append(_inspect_full("partinf_conf", P151_DONOR_FX3_PARTINF_RELPATH, resolved[0], P151_PINNED_FX3_PARTINF_BYTES, P151_PINNED_FX3_PARTINF_SHA256, _chk_partinf))

    # 2. mount.conf
    mount_rows: Tuple[Tuple[str, str, str, int, int], ...] = ()
    def _chk_mount(data: bytes) -> Tuple[List[str], bool]:
        nonlocal mount_rows
        mount_rows = _parse_mount_conf_text(data.decode("utf-8", errors="replace"))
        mps = {r[1] for r in mount_rows}
        req = {"/setting", "/system", "/rootfs", "/cp", "/cert", "/usr", "/lens", "/PMBP"}
        ok = len(mount_rows) == 30 and req.issubset(mps)
        return (sorted(req) if ok else []), ok

    artifacts.append(_inspect_full("mount_conf", P151_DONOR_FX3_MOUNT_RELPATH, resolved[1], P151_PINNED_FX3_MOUNT_BYTES, P151_PINNED_FX3_MOUNT_SHA256, _chk_mount))

    # 3. setup_nflash
    setup_ok = False
    def _chk_setup(data: bytes) -> Tuple[List[str], bool]:
        nonlocal setup_ok
        txt = data.decode("utf-8", errors="replace")
        setup_ok = ("/dev/pnflasha" in txt) and ("/dev/cnflasha" in txt) and ("/dev/nflasha" in txt)
        return (["pnflasha->nflasha", "cnflasha->nflasha"] if setup_ok else []), setup_ok

    artifacts.append(_inspect_full("setup_nflash", P151_DONOR_FX3_SETUP_NFLASH_RELPATH, resolved[2], P151_PINNED_FX3_SETUP_NFLASH_BYTES, P151_PINNED_FX3_SETUP_NFLASH_SHA256, _chk_setup))

    # 4. insmod_drv1
    def _chk_insmod(data: bytes) -> Tuple[List[str], bool]:
        txt = data.decode("utf-8", errors="replace")
        ok = ("crypt-emmc.ko" in txt) and ("emmc.ko" in txt)
        return (["crypt-emmc.ko", "emmc.ko"] if ok else []), ok

    artifacts.append(_inspect_full("insmod_drv1", P151_DONOR_FX3_INSMOD_DRV1_RELPATH, resolved[3], P151_PINNED_FX3_INSMOD_DRV1_BYTES, P151_PINNED_FX3_INSMOD_DRV1_SHA256, _chk_insmod))

    # 5. nor_loader_writer.sh
    nor_ok = False
    def _chk_nor_writer(data: bytes) -> Tuple[List[str], bool]:
        nonlocal nor_ok
        txt = data.decode("utf-8", errors="replace")
        markers = [m for m in ("loader_nor.bin", "LdrBkup.bin", "DGU.bin", "MIS.bin", "ddrtraining.dat") if m in txt]
        nor_ok = len(markers) == 5
        return markers, nor_ok

    artifacts.append(_inspect_full("nor_loader_writer", P151_DONOR_FX3_NOR_LOADER_WRITER_RELPATH, resolved[4], P151_PINNED_FX3_NOR_LOADER_WRITER_BYTES, P151_PINNED_FX3_NOR_LOADER_WRITER_SHA256, _chk_nor_writer))

    # 6. pformat_config.txt
    def _chk_pformat(data: bytes) -> Tuple[List[str], bool]:
        txt = data.decode("utf-8", errors="replace")
        ok = ("loader_nor.bin" in txt) and ("LdrBkup.bin" in txt) and ("MIS.bin" in txt)
        return (["loader_nor.bin@72", "LdrBkup.bin@68", "MIS.bin@512"] if ok else []), ok

    artifacts.append(_inspect_full("pformat_config", P151_DONOR_FX3_PFORMAT_CONFIG_RELPATH, resolved[5], P151_PINNED_FX3_PFORMAT_CONFIG_BYTES, P151_PINNED_FX3_PFORMAT_CONFIG_SHA256, _chk_pformat))

    # 7. loader_nor.bin
    artifacts.append(_inspect_full("loader_nor_bin", P151_DONOR_FX3_LOADER_NOR_BIN_RELPATH, resolved[6], P151_PINNED_FX3_LOADER_NOR_BIN_BYTES, P151_PINNED_FX3_LOADER_NOR_BIN_SHA256, lambda d: (["101888B_NOR_LOADER"], len(d) == P151_PINNED_FX3_LOADER_NOR_BIN_BYTES)))

    # 8. libsencore.so
    def _chk_libsencore(data: bytes) -> Tuple[List[str], bool]:
        is_a64 = len(data) >= 20 and data[:4] == b"\x7fELF" and struct.unpack_from("<H", data, 18)[0] == 183
        ok = is_a64 and (b"AdjustControlFunc" in data) and (b"TransactionStart" in data)
        return (["ELF64_AArch64", "AdjustControlFunc", "TransactionStart"] if ok else []), ok

    artifacts.append(_inspect_full("libsencore_so", P151_DONOR_FX3_LIBSENCORE_RELPATH, resolved[7], P151_PINNED_FX3_LIBSENCORE_BYTES, P151_PINNED_FX3_LIBSENCORE_SHA256, _chk_libsencore))

    # 9. im.elf
    def _chk_im(data: bytes) -> Tuple[List[str], bool]:
        ok = len(data) >= 20 and data[:4] == b"\x7fELF" and struct.unpack_from("<H", data, 18)[0] == 183
        return (["ELF64_AArch64_ET_EXEC"] if ok else []), ok

    artifacts.append(_inspect_full("im_elf", P151_DONOR_FX3_IM_ELF_RELPATH, resolved[8], P151_PINNED_FX3_IM_ELF_BYTES, P151_PINNED_FX3_IM_ELF_SHA256, _chk_im))

    # 10. cpapp-b.bin (bounded 4 KiB header read)
    sz_cp, hdr_cp = _read_regular_file_readonly(resolved[9], 64 * 1024 * 1024, bounded_head_bytes=4096)
    sha_cp_hdr = sha256(hdr_cp).hexdigest()
    cp_words = struct.unpack_from("<4I", hdr_cp, 0) if len(hdr_cp) >= 16 else ()
    cp_ok = sz_cp == P151_PINNED_FX3_CPAPP_B_BYTES and sha_cp_hdr == P151_PINNED_FX3_CPAPP_B_HDR4K_SHA256 and len(cp_words) == 4 and cp_words[3] == 0x0010800C
    if not cp_ok:
        errors.append("DONOR_MISMATCH:cpapp_b_bin")
    artifacts.append(Tier0DonorArtifactDigest("cpapp_b_bin", P151_DONOR_FX3_CPAPP_B_RELPATH, "LOCAL_DONOR_RDONLY", "O_RDONLY_BOUNDED_4K", sz_cp, sha_cp_hdr, sha_cp_hdr, ("ARMv7R_0x00108000",) if cp_ok else (), cp_ok))

    # 11. nflasha15.img (bounded 4 KiB ext2 superblock read)
    sz_15, hdr_15 = _read_regular_file_readonly(resolved[10], 512 * 1024 * 1024, bounded_head_bytes=4096)
    sha_15_hdr = sha256(hdr_15).hexdigest()
    ext2_magic = struct.unpack_from("<H", hdr_15, 1080)[0] if len(hdr_15) >= 1082 else 0
    n15_ok = sz_15 == P151_PINNED_FX3_NFLASHA15_BYTES and sha_15_hdr == P151_PINNED_FX3_NFLASHA15_HDR4K_SHA256 and ext2_magic == EXT2_SUPER_MAGIC
    if not n15_ok:
        errors.append("DONOR_MISMATCH:nflasha15_img")
    artifacts.append(Tier0DonorArtifactDigest("nflasha15_img", P151_DONOR_FX3_NFLASHA15_RELPATH, "LOCAL_DONOR_RDONLY", "O_RDONLY_BOUNDED_4K", sz_15, sha_15_hdr, sha_15_hdr, ("ext2_0xEF53",) if n15_ok else (), n15_ok))

    return Tier0DualLayerDonorSnapshot(
        verification_mode="LOCAL_DONOR_RDONLY",
        access_mode="O_RDONLY_NOFOLLOW_NONBLOCK",
        donor_files_inspected=len(artifacts),
        raw_firmware_bytes_leaked=0,
        partinf_partition_count=len(partinf_rows),
        mount_entry_count=len(mount_rows),
        setup_nflash_aliases_verified=setup_ok,
        nor_loader_writer_markers_verified=nor_ok,
        artifacts=tuple(artifacts),
        all_passed=(len(errors) == 0) and all(a.passed for a in artifacts),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Sector 0 (8246 / 2.00) 30-Partition LBA Geometry Builder & Verifier
# ---------------------------------------------------------------------------


def build_synthetic_fx3_sector0_30_partitions(*, shift_p18_to_fx6: bool = False) -> bytes:
    """Build deterministic 512 B FX3 '8246'/'2.00' 30-partition Sector 0 image."""
    buf = bytearray(SECTOR_SIZE_BYTES)
    buf[0:4] = SECTOR0_MAGIC
    buf[4:8] = SECTOR0_VERSION
    struct.pack_into("<I", buf, 8, SECTOR0_ENTRY_COUNT)
    for idx, start_lba, sec_cnt, ptype, flag_b, _mp, _lbl in FX3_30_PARTITION_TABLE:
        s_lba = 0x00312000 if (shift_p18_to_fx6 and idx == 18) else start_lba
        flag_val = 0xFFFFFFFF if (sec_cnt > 0 or flag_b) else 0x00000000
        struct.pack_into("<IIII", buf, 0x20 + (idx - 1) * 16, s_lba, sec_cnt, ptype, flag_val)
    return bytes(buf)


def verify_fx3_sector0_30_partition_geometry(sector0_bytes: bytes) -> Sector0GeometryReport:
    """Parse & verify 512 B Sector 0 against FX3 7.02 30-partition LBA geometry."""
    errors: List[str] = []
    if len(sector0_bytes) < SECTOR_SIZE_BYTES:
        return Sector0GeometryReport(
            valid=False,
            magic_ascii="",
            version_ascii="",
            entry_count=0,
            active_partition_count=0,
            has_overlaps=False,
            fx3_lba_geometry_ok=False,
            entries=(),
            errors=(f"SECTOR0_TRUNCATED:{len(sector0_bytes)}<{SECTOR_SIZE_BYTES}",),
        )
    sec0 = sector0_bytes[:SECTOR_SIZE_BYTES]
    magic = sec0[0:4]
    version = sec0[4:8]
    count = struct.unpack_from("<I", sec0, 8)[0]
    if magic != SECTOR0_MAGIC:
        errors.append(f"SECTOR0_BAD_MAGIC:{magic.hex()}")
    if version != SECTOR0_VERSION:
        errors.append(f"SECTOR0_BAD_VERSION:{version.hex()}")
    if count != SECTOR0_ENTRY_COUNT:
        errors.append(f"SECTOR0_BAD_COUNT:{count}")

    entries: List[Sector0PartitionEntryInfo] = []
    spans: List[Tuple[int, int, int]] = []
    has_overlaps = False
    fx3_lba_ok = True
    for i in range(SECTOR0_ENTRY_COUNT):
        off = 0x20 + i * 16
        start_lba, sec_cnt, ptype, flag = struct.unpack_from("<IIII", sec0, off)
        pid = i + 1
        entries.append(Sector0PartitionEntryInfo(pid, start_lba, sec_cnt, ptype, flag))
        exp_row = _PARTITION_BY_INDEX[pid]
        if (start_lba, sec_cnt) != (exp_row[1], exp_row[2]):
            fx3_lba_ok = False
            errors.append(
                f"SECTOR0_LBA_MISMATCH:p{pid}:got=(0x{start_lba:x},0x{sec_cnt:x}),expected=(0x{exp_row[1]:x},0x{exp_row[2]:x})"
            )
        if sec_cnt > 0:
            if start_lba < 0x80:
                has_overlaps = True
                errors.append(f"SECTOR0_BELOW_0x80:p{pid}@0x{start_lba:x}")
            end_lba = start_lba + sec_cnt
            for ps, pe, prev_id in spans:
                if not (end_lba <= ps or start_lba >= pe):
                    has_overlaps = True
                    errors.append(f"SECTOR0_OVERLAP:p{pid}_vs_p{prev_id}")
            spans.append((start_lba, end_lba, pid))

    valid = (len(errors) == 0) and (not has_overlaps) and fx3_lba_ok
    return Sector0GeometryReport(
        valid=valid,
        magic_ascii=magic.decode("ascii", errors="replace"),
        version_ascii=version.decode("ascii", errors="replace"),
        entry_count=count,
        active_partition_count=sum(1 for e in entries if e.sector_count > 0),
        has_overlaps=has_overlaps,
        fx3_lba_geometry_ok=fx3_lba_ok,
        entries=tuple(entries),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Synthetic Header & Payload Builders (Clean-Room Testing)
# ---------------------------------------------------------------------------


def build_synthetic_ext2_sample(*, size: int = 4096, valid_magic: bool = True) -> bytes:
    buf = bytearray(size)
    struct.pack_into("<I", buf, 1024 + 0, 8192)
    struct.pack_into("<I", buf, 1024 + 4, 16384)
    struct.pack_into("<H", buf, 1024 + 56, EXT2_SUPER_MAGIC if valid_magic else 0xDEAD)
    return bytes(buf)


def build_synthetic_squashfs_sample(*, size: int = 4096, valid_magic: bool = True) -> bytes:
    buf = bytearray(size)
    buf[0:4] = SQUASHFS_MAGIC if valid_magic else b"sqsh"
    struct.pack_into("<IIHH", buf, 4, 128, 0, 4, 4)
    struct.pack_into("<HH", buf, 28, 4, 0)
    return bytes(buf)


def build_synthetic_vfat_sample(*, size: int = 4096, marker: Optional[bytes] = None) -> bytes:
    buf = bytearray(size)
    buf[0:3] = b"\xeb\x3c\x90"
    buf[3:11] = b"SONYFX3 "
    struct.pack_into("<HBH", buf, 11, 512, 32, 32)
    buf[510:512] = VFAT_BOOT_SIG
    if marker:
        buf[1024 : 1024 + len(marker)] = marker
    return bytes(buf)


def build_synthetic_bk4_sample(*, size: int = 4096, model_id: int = FX3_PRODUCT_MODEL_ID, corrupt_checksum: bool = False) -> bytes:
    buf = bytearray(max(size, 512))
    payload = bytearray(32)
    struct.pack_into("<IH I", payload, 0, 0x00010001, 4, model_id)
    total = BK4_HEADER_SIZE + len(payload)
    struct.pack_into("<I", buf, 0x04, BK4_SYNC_MARKER)
    buf[0x0C:0x10] = BK4_MAGIC
    struct.pack_into("<IIII", buf, 0x10, 1, 1, BK4_HEADER_SIZE, len(payload))
    buf[BK4_HEADER_SIZE : BK4_HEADER_SIZE + len(payload)] = payload
    chk = (sum(buf[0x20:total]) + (1 if corrupt_checksum else 0)) & 0xFFFFFFFF
    struct.pack_into("<I", buf, 0x00, chk)
    return bytes(buf)


def build_synthetic_wbi2_sample(*, size: int = 4096, valid_magic: bool = True) -> bytes:
    buf = bytearray(size)
    buf[0:4] = WBI2_MAGIC if valid_magic else b"wbi2"
    struct.pack_into("<II", buf, 4, 1, 1399)
    return bytes(buf)


def build_synthetic_high_entropy_spacc_sample(*, size: int = 4096, seed_tag: bytes = b"fx3-spacc-isp") -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < size:
        out.extend(sha256(seed_tag + ctr.to_bytes(4, "little")).digest())
        ctr += 1
    return bytes(out[:size])


def build_synthetic_ext_csd_sample(*, part_config: int = 0x48, boot_size_mult: int = 32) -> bytes:
    buf = bytearray(EXT_CSD_SIZE)
    buf[EXT_CSD_BOOT_BUS_COND_IDX] = 0x02
    buf[EXT_CSD_PART_CONFIG_IDX] = part_config & 0xFF
    buf[192] = 8
    struct.pack_into("<I", buf, 212, 0x03A3E000)
    buf[EXT_CSD_BOOT_SIZE_MULT_IDX] = boot_size_mult & 0xFF
    buf[267] = 0x01
    buf[268] = 0x01
    buf[269] = 0x01
    return bytes(buf)


def build_synthetic_spi_nor_sample(
    *,
    total_bytes: int = 256 * 1024,
    erasesize_bytes: int = SPI_NOR_ERASE_BLOCK_BYTES,
    include_all_stages: bool = True,
) -> bytes:
    buf = bytearray(total_bytes)
    buf[0:16] = b"EXBL_INFOMISC_FX"
    if include_all_stages:
        buf[2048:2064] = b"IPL_DGU_CXD90057"
        buf[72 * 512 : 72 * 512 + 16] = b"BLOADER_NOR_FX3_"
        buf[256 * 512 : 256 * 512 + 16] = b"BL31_ATF_MIS_FX3"
        buf[260 * 512 : 260 * 512 + 24] = b"BOOTCONFIG_PFORMAT_FX3__"
    return bytes(buf)


def build_synthetic_proc_mtd_text(*, erasesize_hex: str = "00010000", total_hex: str = "01000000") -> str:
    return (
        "dev:    size   erasesize  name\n"
        f'mtd0: {total_hex} {erasesize_hex} "spi-nor-boot"\n'
    )


def _make_sample_for_surface(spec: Tier0SurfaceSpec, *, body_tag: str = "BODY_A") -> Tuple[bytes, Optional[bytes]]:
    sid = spec.surface_id
    if sid == "sector0":
        return build_synthetic_fx3_sector0_30_partitions(), None
    if sid in ("p1", "p3"):
        logical = build_synthetic_vfat_sample(marker=b"SQFS_INITRD")
    elif sid == "p2":
        logical = build_synthetic_bk4_sample()
    elif sid == "p5":
        logical = build_synthetic_wbi2_sample()
    elif sid in ("p6", "p8", "p12", "p13"):
        logical = build_synthetic_vfat_sample(marker=f"ID_{body_tag}".encode("ascii"))
    elif sid in ("p7", "p15"):
        logical = build_synthetic_ext2_sample()
    elif sid == "p18":
        logical = build_synthetic_vfat_sample(marker=LENS_VX8900_MAGIC)
    elif sid in ("p23", "p30"):
        logical = build_synthetic_bk4_sample()
    elif sid == "spi_nor_mtd0ro":
        logical = build_synthetic_spi_nor_sample()
    elif sid == "emmc_ext_csd":
        logical = build_synthetic_ext_csd_sample()
    else:
        logical = build_synthetic_vfat_sample()
    raw_isp = (
        build_synthetic_high_entropy_spacc_sample(seed_tag=f"{sid}:{body_tag}".encode("utf-8"))
        if spec.spacc_encrypted
        else None
    )
    return logical, raw_isp


def _verify_magic_sample(magic_kind: str, sample: bytes) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    if len(sample) < 16:
        return False, [f"SAMPLE_TOO_SHORT:{len(sample)}"]
    if all(b == 0 for b in sample) or all(b == 0xFF for b in sample):
        return False, ["BLANK_OR_ERASED_FLASH_READ"]

    if magic_kind == "SECTOR0_8246":
        ok = sample[0:4] == SECTOR0_MAGIC and sample[4:8] == SECTOR0_VERSION
        if not ok:
            errs.append("BAD_SECTOR0_MAGIC")
        return ok, errs
    if magic_kind == "EXT2":
        ok = len(sample) >= 1082 and struct.unpack_from("<H", sample, 1080)[0] == EXT2_SUPER_MAGIC
        if not ok:
            errs.append("BAD_EXT2_0XEF53_MAGIC")
        return ok, errs
    if magic_kind == "EXT2_OR_SQUASHFS":
        ext2_ok = len(sample) >= 1082 and struct.unpack_from("<H", sample, 1080)[0] == EXT2_SUPER_MAGIC
        sq_ok = sample[0:4] == SQUASHFS_MAGIC
        if not (ext2_ok or sq_ok):
            errs.append("BAD_EXT2_OR_SQUASHFS_MAGIC")
        return (ext2_ok or sq_ok), errs
    if magic_kind == "VFAT":
        ok = len(sample) >= 512 and sample[510:512] == VFAT_BOOT_SIG
        if not ok:
            errs.append("BAD_VFAT_0X55AA")
        return ok, errs
    if magic_kind == "VFAT_OR_SQUASHFS":
        vfat_ok = len(sample) >= 512 and sample[510:512] == VFAT_BOOT_SIG
        sq_ok = sample[0:4] == SQUASHFS_MAGIC
        if not (vfat_ok or sq_ok):
            errs.append("BAD_VFAT_OR_SQUASHFS_MAGIC")
        return (vfat_ok or sq_ok), errs
    if magic_kind == "WBI2":
        ok = sample[0:4] == WBI2_MAGIC
        if not ok:
            errs.append("BAD_WBI2_MAGIC")
        return ok, errs
    if magic_kind == "LENS_VX8900":
        vfat_ok = len(sample) >= 512 and sample[510:512] == VFAT_BOOT_SIG
        vx_ok = LENS_VX8900_MAGIC in sample
        if not (vfat_ok and vx_ok):
            errs.append("MISSING_P18_VX8900_OR_VFAT")
        return (vfat_ok and vx_ok), errs
    if magic_kind == "BK4_NVRAM":
        ok = _validate_bk4_sample(sample, errs)
        return ok, errs
    if magic_kind == "BK4_OR_VFAT":
        bk4_errs: List[str] = []
        if _validate_bk4_sample(sample, bk4_errs):
            return True, errs
        vfat_ok = len(sample) >= 512 and sample[510:512] == VFAT_BOOT_SIG
        if not vfat_ok:
            errs.extend(bk4_errs)
        return vfat_ok, errs
    if magic_kind == "SPI_NOR_ENVELOPE":
        stages = _detect_spi_nor_stages(sample)
        ok = len(stages) == len(SPI_NOR_REQUIRED_BOOT_STAGES)
        if not ok:
            errs.append("MISSING_SPI_NOR_BOOT_STAGE")
        return ok, errs
    if magic_kind == "EXT_CSD":
        ok = len(sample) == EXT_CSD_SIZE and sample[EXT_CSD_BOOT_SIZE_MULT_IDX] > 0
        if not ok:
            errs.append("INVALID_EXT_CSD_512B")
        return ok, errs
    return False, [f"UNKNOWN_MAGIC_KIND:{magic_kind}"]


def _validate_bk4_sample(sample: bytes, errs: List[str]) -> bool:
    idx = sample.find(BK4_MAGIC)
    if idx < 0x0C:
        errs.append("BK4_MAGIC_MISSING")
        return False
    base = idx - 0x0C
    if base + BK4_HEADER_SIZE > len(sample):
        errs.append("BK4_HEADER_TRUNCATED")
        return False
    exp_sum, sync_w = struct.unpack_from("<II", sample, base)
    if sync_w != BK4_SYNC_MARKER:
        errs.append(f"BK4_BAD_SYNC:0x{sync_w:08x}")
        return False
    _active, _nprop, data_off, data_sz = struct.unpack_from("<IIII", sample, base + 0x10)
    if data_off < BK4_HEADER_SIZE or base + data_off + data_sz > len(sample):
        errs.append("BK4_SPAN_OUT_OF_BOUNDS")
        return False
    calc_sum = sum(sample[base + 0x20 : base + data_off + data_sz]) & 0xFFFFFFFF
    if calc_sum != exp_sum:
        errs.append(f"BK4_CHECKSUM_MISMATCH:0x{exp_sum:08x}!=0x{calc_sum:08x}")
        return False
    # Check FX3 model ID if present in TLV
    tlv_slice = sample[base + data_off : base + data_off + data_sz]
    if len(tlv_slice) >= 10:
        prop_id, val_len = struct.unpack_from("<IH", tlv_slice, 0)
        if prop_id == 0x00010001 and val_len == 4:
            model = struct.unpack_from("<I", tlv_slice, 6)[0]
            if model != FX3_PRODUCT_MODEL_ID:
                errs.append(f"BK4_CROSS_SKU_MODEL:0x{model:08x}")
                return False
    return True


def _detect_spi_nor_stages(sample: bytes) -> Tuple[str, ...]:
    found: List[str] = []
    if b"IPL" in sample or b"DGU" in sample or b"EXBL" in sample:
        found.append("IPL")
    if b"BLOADER" in sample or b"BLoader" in sample or b"loader_nor" in sample:
        found.append("BLoader")
    if b"BL31" in sample or b"MIS" in sample:
        found.append("BL31")
    if b"BOOTCONFIG" in sample or b"PFORMAT" in sample or b"BootConfig" in sample:
        found.append("BootConfig")
    return tuple(found)


def build_synthetic_16_surface_vault(
    *,
    body_serial_sha256: Optional[str] = None,
    emmc_cid_sha256: Optional[str] = None,
    shift_p18_to_fx6: bool = False,
) -> Tuple[bytes, Dict[str, DualLayerSurfaceEntry], Dict[str, bytes]]:
    """Build deterministic clean-room 16-surface dual-layer vault + sample map."""
    body_sha = body_serial_sha256 or sha256(b"fx3-cleanroom-body-serial-A").hexdigest()
    cid_sha = emmc_cid_sha256 or sha256(b"fx3-cleanroom-emmc-cid-A").hexdigest()
    sector0_bytes = build_synthetic_fx3_sector0_30_partitions(shift_p18_to_fx6=shift_p18_to_fx6)
    entries: Dict[str, DualLayerSurfaceEntry] = {}
    samples: Dict[str, bytes] = {}
    for spec in TIER0_16_SURFACES:
        if spec.surface_id == "sector0":
            logical = sector0_bytes
            raw_isp = None
        else:
            logical, raw_isp = _make_sample_for_surface(spec, body_tag=body_sha[:8])
        digest = sha256(logical).hexdigest()
        ent = compute_shannon_entropy(logical)
        raw_sha = sha256(raw_isp).hexdigest() if raw_isp is not None else None
        raw_ent = compute_shannon_entropy(raw_isp) if raw_isp is not None else None
        node = spec.logical_device_node if spec.primary_layer_domain == DOMAIN_SPACC_CNFLASHA_LOGICAL else spec.raw_device_node
        entries[spec.surface_id] = DualLayerSurfaceEntry(
            surface_id=spec.surface_id,
            layer_domain=spec.primary_layer_domain,
            device_node=node,
            start_lba=spec.expected_start_lba,
            sector_count=spec.expected_sector_count,
            byte_size=spec.expected_byte_size,
            magic_kind=spec.expected_magic_kind,
            header_sample_hex_digest=digest,
            shannon_entropy_bits=round(ent, 4),
            sd_exfat_sha256=digest,
            mac_host_vault_sha256=digest,
            body_serial_sha256=body_sha,
            emmc_cid_sha256=cid_sha,
            raw_isp_sha256=raw_sha,
            raw_isp_entropy_bits=round(raw_ent, 4) if raw_ent is not None else None,
            gf256_parity_attached=True,
            gf256_healed_ok=True,
        )
        samples[spec.surface_id] = logical
    return sector0_bytes, entries, samples


# ---------------------------------------------------------------------------
# Pillar A — 16-Surface Dual-Layer Vault Audit & 8-Scenario Restore Firewall
# ---------------------------------------------------------------------------


def verify_dual_layer_16_surface_vault(
    sector0_bytes: bytes,
    entries: Mapping[str, DualLayerSurfaceEntry],
    samples: Mapping[str, bytes],
    *,
    expected_body_serial_sha256: Optional[str] = None,
    expected_emmc_cid_sha256: Optional[str] = None,
) -> DualLayer16SurfaceManifestReport:
    """Verify all 16 mandatory Tier-0 surfaces across domain, Sector 0 LBA, magic/entropy & dual-copy SHA-256."""
    sec0_rep = verify_fx3_sector0_30_partition_geometry(sector0_bytes)
    missing = tuple(sid for sid in MANDATORY_16_SURFACE_IDS if sid not in entries)
    errors: List[str] = list(sec0_rep.errors)
    if missing:
        errors.append(f"{ERR_MISSING_TIER0_SURFACES}:{','.join(missing)}")

    raw_nodes: List[str] = []
    spacc_nodes: List[str] = []
    mtd_nodes: List[str] = []
    reg_nodes: List[str] = []
    surface_results: List[SurfaceAuditResult] = []

    ref_body = expected_body_serial_sha256
    ref_cid = expected_emmc_cid_sha256

    for spec in TIER0_16_SURFACES:
        entry = entries.get(spec.surface_id)
        if entry is None:
            surface_results.append(SurfaceAuditResult(spec.surface_id, spec.primary_layer_domain, False, False, False, False, False, False, ("MISSING_ENTRY",)))
            continue

        s_errs: List[str] = []
        if entry.layer_domain == DOMAIN_RAW_PNFLASHA_ISP:
            raw_nodes.append(spec.surface_id)
        elif entry.layer_domain == DOMAIN_SPACC_CNFLASHA_LOGICAL:
            spacc_nodes.append(spec.surface_id)
        elif entry.layer_domain == DOMAIN_SPI_NOR_MTDRO:
            mtd_nodes.append(spec.surface_id)
        elif entry.layer_domain == DOMAIN_EMMC_REG_METADATA:
            reg_nodes.append(spec.surface_id)
        else:
            s_errs.append(f"INVALID_LAYER_DOMAIN:{entry.layer_domain}")

        if entry.layer_domain != spec.primary_layer_domain:
            s_errs.append(f"DOMAIN_MISMATCH:{entry.layer_domain}!={spec.primary_layer_domain}")

        # LBA geometry check against Sector 0
        lba_ok = True
        if spec.expected_start_lba is not None:
            if (entry.start_lba, entry.sector_count) != (spec.expected_start_lba, spec.expected_sector_count):
                lba_ok = False
                s_errs.append(f"LBA_GEOMETRY_MISMATCH:{spec.surface_id}")
            if not sec0_rep.valid:
                lba_ok = False
        if entry.byte_size != spec.expected_byte_size:
            lba_ok = False
            s_errs.append(f"BYTE_SIZE_MISMATCH:{entry.byte_size}!={spec.expected_byte_size}")

        # Magic & entropy check
        sample = samples.get(spec.surface_id, b"")
        magic_ok, m_errs = _verify_magic_sample(spec.expected_magic_kind, sample)
        s_errs.extend(m_errs)

        entropy_ok = True
        if spec.spacc_encrypted:
            if entry.raw_isp_entropy_bits is None or entry.raw_isp_entropy_bits < SPACC_CIPHERTEXT_MIN_ENTROPY_BITS:
                entropy_ok = False
                s_errs.append(f"{ERR_INVALID_MAGIC_OR_LOW_ENTROPY}:raw_isp_entropy={entry.raw_isp_entropy_bits}")
            if not entry.raw_isp_sha256 or not _SHA256_HEX_RE.match(entry.raw_isp_sha256):
                entropy_ok = False
                s_errs.append("MISSING_RAW_PNFLASHA_ISP_SHA256")

        # Dual-copy SHA-256 parity (SD ExFAT + Mac Host Vault)
        dual_ok = (
            bool(_SHA256_HEX_RE.match(entry.sd_exfat_sha256))
            and entry.sd_exfat_sha256 == entry.mac_host_vault_sha256
            and entry.gf256_healed_ok
        )
        if not dual_ok:
            s_errs.append(f"{BLOCKED_DUAL_COPY_BITROT_DETECTED}:{spec.surface_id}")

        # Identity lock check
        if ref_body is None:
            ref_body = entry.body_serial_sha256
        if ref_cid is None:
            ref_cid = entry.emmc_cid_sha256
        id_ok = (
            bool(_SHA256_HEX_RE.match(entry.body_serial_sha256))
            and bool(_SHA256_HEX_RE.match(entry.emmc_cid_sha256))
            and entry.body_serial_sha256 == ref_body
            and entry.emmc_cid_sha256 == ref_cid
        )
        if not id_ok:
            s_errs.append(f"{BLOCKED_CROSS_CAMERA_SPACC_OTP_KEY_MISMATCH}:{spec.surface_id}")

        s_passed = magic_ok and lba_ok and entropy_ok and dual_ok and id_ok and (len(s_errs) == 0)
        if not s_passed:
            errors.extend(s_errs)
        surface_results.append(
            SurfaceAuditResult(
                surface_id=spec.surface_id,
                layer_domain=entry.layer_domain,
                passed=s_passed,
                magic_ok=magic_ok,
                lba_geometry_ok=lba_ok,
                entropy_ok=entropy_ok,
                dual_copy_parity_ok=dual_ok,
                identity_lock_ok=id_ok,
                errors=tuple(s_errs),
            )
        )

    passed = (len(missing) == 0) and sec0_rep.valid and all(r.passed for r in surface_results) and (len(errors) == 0)
    return DualLayer16SurfaceManifestReport(
        passed=passed,
        status=STATUS_VERIFIED_PILLAR_A if passed else STATUS_REJECTED_PILLAR_A,
        surface_count=len(entries),
        mandatory_16_complete=(len(missing) == 0 and len(entries) >= 16),
        raw_pnflasha_surfaces=tuple(raw_nodes),
        spacc_cnflasha_surfaces=tuple(spacc_nodes),
        spi_nor_mtdro_surfaces=tuple(mtd_nodes),
        emmc_reg_surfaces=tuple(reg_nodes),
        sector0_geometry=sec0_rep,
        surface_results=tuple(surface_results),
        missing_surfaces=missing,
        errors=tuple(errors),
    )


def evaluate_restore_target_pairing(
    *,
    source_layer_domain: str,
    source_partition: Optional[int],
    source_body_serial_sha256: str,
    source_emmc_cid_sha256: str,
    target_device_path: str,
    target_body_serial_sha256: str,
    target_emmc_cid_sha256: str,
    open_mode: str = "O_RDONLY",
    ioctl_name: Optional[str] = None,
    source_shannon_entropy_bits: Optional[float] = None,
    sd_exfat_sha256: Optional[str] = None,
    mac_host_vault_sha256: Optional[str] = None,
    gf256_healed_ok: bool = True,
    sector0_valid: bool = True,
) -> RestorePairingDecision:
    """Firewall evaluating (source_domain, image) -> (target_device_path, op) safety."""
    # 1. Sector 0 geometry check
    if not sector0_valid:
        return RestorePairingDecision(
            allowed=False,
            blocked_code=BLOCKED_SECTOR0_LBA_GEOMETRY_MISMATCH,
            source_layer_domain=source_layer_domain,
            target_layer_domain="UNKNOWN",
            source_partition=source_partition,
            target_device_path=target_device_path,
            reason="Sector 0 30-partition FX3 LBA geometry invalid or FX6-shifted.",
        )

    # 2. SPI NOR /dev/mtd*ro vs /dev/mtd* RW & ioctl firewall
    mtd_m = _DEV_MTD_RE.match(target_device_path)
    if mtd_m or "/dev/mtd" in target_device_path or (ioctl_name and ioctl_name.upper() in FORBIDDEN_MTD_IOCTLS):
        is_ro_node = bool(mtd_m and mtd_m.group(2) == "ro")
        bad_mode = open_mode in FORBIDDEN_MTD_OPEN_MODES
        bad_ioctl = bool(ioctl_name and ioctl_name.upper() in FORBIDDEN_MTD_IOCTLS)
        if (not is_ro_node) or bad_mode or bad_ioctl:
            return RestorePairingDecision(
                allowed=False,
                blocked_code=BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN,
                source_layer_domain=source_layer_domain,
                target_layer_domain=DOMAIN_SPI_NOR_MTDRO,
                source_partition=source_partition,
                target_device_path=target_device_path,
                reason="SPI NOR must ONLY be accessed via /dev/mtd*ro with O_RDONLY; RW/MEMERASE forbidden.",
            )
        return RestorePairingDecision(
            allowed=True,
            blocked_code=None,
            source_layer_domain=source_layer_domain,
            target_layer_domain=DOMAIN_SPI_NOR_MTDRO,
            source_partition=source_partition,
            target_device_path=target_device_path,
            reason="Read-only /dev/mtd*ro O_RDONLY inspection permitted (zero writes authorized).",
        )

    # 3. Dual-copy bit-rot gate
    if sd_exfat_sha256 is not None and mac_host_vault_sha256 is not None:
        if (sd_exfat_sha256 != mac_host_vault_sha256) and (not gf256_healed_ok):
            return RestorePairingDecision(
                allowed=False,
                blocked_code=BLOCKED_DUAL_COPY_BITROT_DETECTED,
                source_layer_domain=source_layer_domain,
                target_layer_domain="UNKNOWN",
                source_partition=source_partition,
                target_device_path=target_device_path,
                reason="SD ExFAT and Mac Host Vault SHA-256 mismatch with unhealed bit-rot.",
            )

    # 4. Classify eMMC target domain
    n_m = _DEV_NFLASH_RE.match(target_device_path)
    target_domain = DOMAIN_RAW_PNFLASHA_ISP
    target_part = source_partition
    if n_m:
        family = n_m.group(1)
        p_idx = int(n_m.group(2)) if n_m.group(2) else 0
        target_part = p_idx
        row = _PARTITION_BY_INDEX.get(p_idx)
        is_enc_part = bool(row[4]) if row else False
        if family == "cnflasha" or (family == "nflasha" and is_enc_part):
            target_domain = DOMAIN_SPACC_CNFLASHA_LOGICAL
        else:
            target_domain = DOMAIN_RAW_PNFLASHA_ISP

        # Cross-domain firewall
        if source_layer_domain == DOMAIN_SPACC_CNFLASHA_LOGICAL and target_domain == DOMAIN_RAW_PNFLASHA_ISP:
            return RestorePairingDecision(
                allowed=False,
                blocked_code=BLOCKED_CROSS_DOMAIN_CNFLASHA_TO_PNFLASHA,
                source_layer_domain=source_layer_domain,
                target_layer_domain=target_domain,
                source_partition=source_partition,
                target_device_path=target_device_path,
                reason="Catastrophic cipher-mismatch: SPACC_CNFLASHA_LOGICAL plaintext cannot target raw /dev/pnflasha*.",
            )
        if source_layer_domain == DOMAIN_RAW_PNFLASHA_ISP and target_domain == DOMAIN_SPACC_CNFLASHA_LOGICAL:
            return RestorePairingDecision(
                allowed=False,
                blocked_code=BLOCKED_CROSS_DOMAIN_PNFLASHA_TO_CNFLASHA,
                source_layer_domain=source_layer_domain,
                target_layer_domain=target_domain,
                source_partition=source_partition,
                target_device_path=target_device_path,
                reason="Catastrophic double-encryption: RAW_PNFLASHA_ISP ciphertext cannot target /dev/cnflasha*.",
            )

        if is_enc_part and source_layer_domain == DOMAIN_RAW_PNFLASHA_ISP:
            if source_shannon_entropy_bits is not None and source_shannon_entropy_bits < SPACC_CIPHERTEXT_MIN_ENTROPY_BITS:
                return RestorePairingDecision(
                    allowed=False,
                    blocked_code=ERR_INVALID_MAGIC_OR_LOW_ENTROPY,
                    source_layer_domain=source_layer_domain,
                    target_layer_domain=target_domain,
                    source_partition=source_partition,
                    target_device_path=target_device_path,
                    reason="Encrypted partition RAW_PNFLASHA_ISP image failed >= 7.9 bits/byte SPACC entropy check.",
                )

    # 5. Cross-camera OTP SPACC key lock on RAW_PNFLASHA_ISP or per-camera partitions
    if source_body_serial_sha256 != target_body_serial_sha256 or source_emmc_cid_sha256 != target_emmc_cid_sha256:
        return RestorePairingDecision(
            allowed=False,
            blocked_code=BLOCKED_CROSS_CAMERA_SPACC_OTP_KEY_MISMATCH,
            source_layer_domain=source_layer_domain,
            target_layer_domain=target_domain,
            source_partition=target_part,
            target_device_path=target_device_path,
            reason="Per-camera SPACC OTP key / eMMC CID / body serial mismatch across cameras.",
        )

    # 6. Read-only mode always allowed for same-domain same-camera audit; write mode remains hard-locked False
    if open_mode in FORBIDDEN_MTD_OPEN_MODES:
        return RestorePairingDecision(
            allowed=False,
            blocked_code=ERR_WRITE_AUTH_LOCKED,
            source_layer_domain=source_layer_domain,
            target_layer_domain=target_domain,
            source_partition=target_part,
            target_device_path=target_device_path,
            reason="Domain/camera match verified dry-run, but PERSISTENT_EMMC_WRITES_AUTHORIZED is hard-locked False.",
        )

    return RestorePairingDecision(
        allowed=True,
        blocked_code=None,
        source_layer_domain=source_layer_domain,
        target_layer_domain=target_domain,
        source_partition=target_part,
        target_device_path=target_device_path,
        reason="Same-domain same-camera read-only vault pairing verified (writes hard-locked False).",
    )


def run_pillar_a_8_scenario_firewall() -> PillarAFirewall8ScenarioSuiteResult:
    """Execute the 8 mandatory Pillar A Dual-Layer Vault & Cross-Domain Firewall scenarios."""
    body_a = sha256(b"fx3-camera-body-A").hexdigest()
    cid_a = sha256(b"fx3-emmc-cid-A").hexdigest()
    body_b = sha256(b"fx3-camera-body-B").hexdigest()
    cid_b = sha256(b"fx3-emmc-cid-B").hexdigest()

    results: List[PillarAScenarioResult] = []

    # PA1: Happy 16-surface dual-layer vault
    sec0_ok, entries_ok, samples_ok = build_synthetic_16_surface_vault(body_serial_sha256=body_a, emmc_cid_sha256=cid_a)
    rep1 = verify_dual_layer_16_surface_vault(sec0_ok, entries_ok, samples_ok, expected_body_serial_sha256=body_a, expected_emmc_cid_sha256=cid_a)
    results.append(PillarAScenarioResult(
        PILLAR_A_SCENARIO_IDS[0],
        rep1.passed and rep1.mandatory_16_complete and len(rep1.surface_results) == 16,
        "VERIFIED",
        rep1.status,
        {"surface_count": rep1.surface_count, "active_partitions": rep1.sector0_geometry.active_partition_count},
    ))

    # PA2: SPACC_CNFLASHA_LOGICAL plaintext -> /dev/pnflasha15
    d2 = evaluate_restore_target_pairing(
        source_layer_domain=DOMAIN_SPACC_CNFLASHA_LOGICAL,
        source_partition=15,
        source_body_serial_sha256=body_a,
        source_emmc_cid_sha256=cid_a,
        target_device_path="/dev/pnflasha15",
        target_body_serial_sha256=body_a,
        target_emmc_cid_sha256=cid_a,
    )
    results.append(PillarAScenarioResult(
        PILLAR_A_SCENARIO_IDS[1],
        (not d2.allowed) and (d2.blocked_code == BLOCKED_CROSS_DOMAIN_CNFLASHA_TO_PNFLASHA),
        "BLOCKED",
        d2.blocked_code or "ALLOWED",
        {"target": d2.target_device_path},
    ))

    # PA3: RAW_PNFLASHA_ISP ciphertext -> /dev/cnflasha15
    d3 = evaluate_restore_target_pairing(
        source_layer_domain=DOMAIN_RAW_PNFLASHA_ISP,
        source_partition=15,
        source_body_serial_sha256=body_a,
        source_emmc_cid_sha256=cid_a,
        target_device_path="/dev/cnflasha15",
        target_body_serial_sha256=body_a,
        target_emmc_cid_sha256=cid_a,
        source_shannon_entropy_bits=7.96,
    )
    results.append(PillarAScenarioResult(
        PILLAR_A_SCENARIO_IDS[2],
        (not d3.allowed) and (d3.blocked_code == BLOCKED_CROSS_DOMAIN_PNFLASHA_TO_CNFLASHA),
        "BLOCKED",
        d3.blocked_code or "ALLOWED",
        {"target": d3.target_device_path},
    ))

    # PA4: Cross-camera RAW_PNFLASHA_ISP OTP mismatch
    d4 = evaluate_restore_target_pairing(
        source_layer_domain=DOMAIN_RAW_PNFLASHA_ISP,
        source_partition=15,
        source_body_serial_sha256=body_a,
        source_emmc_cid_sha256=cid_a,
        target_device_path="/dev/pnflasha15",
        target_body_serial_sha256=body_b,
        target_emmc_cid_sha256=cid_b,
        source_shannon_entropy_bits=7.96,
    )
    results.append(PillarAScenarioResult(
        PILLAR_A_SCENARIO_IDS[3],
        (not d4.allowed) and (d4.blocked_code == BLOCKED_CROSS_CAMERA_SPACC_OTP_KEY_MISMATCH),
        "BLOCKED",
        d4.blocked_code or "ALLOWED",
        {"cross_camera": True},
    ))

    # PA5: /dev/mtd0 non-ro or MEMERASE ioctl
    d5_path = evaluate_restore_target_pairing(
        source_layer_domain=DOMAIN_SPI_NOR_MTDRO,
        source_partition=None,
        source_body_serial_sha256=body_a,
        source_emmc_cid_sha256=cid_a,
        target_device_path="/dev/mtd0",
        target_body_serial_sha256=body_a,
        target_emmc_cid_sha256=cid_a,
        open_mode="O_RDONLY",
    )
    d5_ioctl = evaluate_restore_target_pairing(
        source_layer_domain=DOMAIN_SPI_NOR_MTDRO,
        source_partition=None,
        source_body_serial_sha256=body_a,
        source_emmc_cid_sha256=cid_a,
        target_device_path="/dev/mtd0ro",
        target_body_serial_sha256=body_a,
        target_emmc_cid_sha256=cid_a,
        open_mode="O_RDONLY",
        ioctl_name="MEMERASE",
    )
    results.append(PillarAScenarioResult(
        PILLAR_A_SCENARIO_IDS[4],
        (not d5_path.allowed) and (not d5_ioctl.allowed)
        and d5_path.blocked_code == BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN
        and d5_ioctl.blocked_code == BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN,
        "BLOCKED",
        d5_ioctl.blocked_code or "ALLOWED",
        {"mtd0_blocked": not d5_path.allowed, "memerase_blocked": not d5_ioctl.allowed},
    ))

    # PA6: Dual-copy SD ExFAT vs Mac Host Vault unhealed bit-rot
    d6 = evaluate_restore_target_pairing(
        source_layer_domain=DOMAIN_RAW_PNFLASHA_ISP,
        source_partition=18,
        source_body_serial_sha256=body_a,
        source_emmc_cid_sha256=cid_a,
        target_device_path="/dev/pnflasha18",
        target_body_serial_sha256=body_a,
        target_emmc_cid_sha256=cid_a,
        sd_exfat_sha256="a" * 64,
        mac_host_vault_sha256="b" * 64,
        gf256_healed_ok=False,
    )
    results.append(PillarAScenarioResult(
        PILLAR_A_SCENARIO_IDS[5],
        (not d6.allowed) and (d6.blocked_code == BLOCKED_DUAL_COPY_BITROT_DETECTED),
        "BLOCKED",
        d6.blocked_code or "ALLOWED",
        {"bitrot_detected": True},
    ))

    # PA7: GF(256) RS P+Q bit-rot detection & deterministic healing
    shards = [samples_ok["p18"][i * 512 : (i + 1) * 512] for i in range(4)]
    stripe = encode_gf256_pq_parity(shards, shard_names=[f"p18_s{i}" for i in range(4)])
    corrupted_d1 = bytearray(shards[1])
    corrupted_d1[17] ^= 0xA5
    orig_bundle_sha = sha256(b"".join(shards)).hexdigest()
    heal_res, _p_out, _q_out = heal_gf256_pq_shards(
        (shards[0], bytes(corrupted_d1), shards[2], shards[3]),
        stripe.p_parity,
        stripe.q_parity,
        shard_sizes=stripe.shard_sizes,
        stripe_bytes=stripe.stripe_bytes,
        expected_shard_sha256s=stripe.shard_sha256s,
        expected_p_sha256=stripe.p_sha256,
        expected_q_sha256=stripe.q_sha256,
        shard_names=stripe.shard_names,
    )
    pa7_ok = (
        heal_res.passed
        and heal_res.bit_exact_match
        and heal_res.reconstructed_sha256s == stripe.shard_sha256s
        and heal_res.reconstructed_bundle_sha256 == heal_res.original_bundle_sha256
        and heal_res.reconstructed_shards is not None
        and sha256(b"".join(heal_res.reconstructed_shards)).hexdigest() == orig_bundle_sha
    )
    results.append(PillarAScenarioResult(
        PILLAR_A_SCENARIO_IDS[6],
        pa7_ok,
        "VERIFIED_HEALED",
        "GF256_RS_PQ_HEALED" if pa7_ok else ERR_GF256_UNHEALABLE_BITROT,
        {"healed_indices": list(heal_res.healed_indices), "reconstructed_sha256": heal_res.reconstructed_bundle_sha256[:16]},
    ))

    # PA8: Sector 0 FX6 p18 @ 0x312000 shift rejection
    sec0_fx6, entries_fx6, samples_fx6 = build_synthetic_16_surface_vault(body_serial_sha256=body_a, emmc_cid_sha256=cid_a, shift_p18_to_fx6=True)
    rep8 = verify_dual_layer_16_surface_vault(sec0_fx6, entries_fx6, samples_fx6, expected_body_serial_sha256=body_a, expected_emmc_cid_sha256=cid_a)
    d8 = evaluate_restore_target_pairing(
        source_layer_domain=DOMAIN_RAW_PNFLASHA_ISP,
        source_partition=18,
        source_body_serial_sha256=body_a,
        source_emmc_cid_sha256=cid_a,
        target_device_path="/dev/pnflasha18",
        target_body_serial_sha256=body_a,
        target_emmc_cid_sha256=cid_a,
        sector0_valid=rep8.sector0_geometry.valid,
    )
    results.append(PillarAScenarioResult(
        PILLAR_A_SCENARIO_IDS[7],
        (not rep8.sector0_geometry.valid) and (not d8.allowed) and (d8.blocked_code == BLOCKED_SECTOR0_LBA_GEOMETRY_MISMATCH),
        "BLOCKED",
        d8.blocked_code or "ALLOWED",
        {"sector0_valid": rep8.sector0_geometry.valid},
    ))

    passed_cnt = sum(1 for r in results if r.passed)
    all_ok = passed_cnt == len(PILLAR_A_SCENARIO_IDS)
    return PillarAFirewall8ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_PILLAR_A if all_ok else STATUS_REJECTED_PILLAR_A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(PILLAR_A_SCENARIO_IDS),
        scenarios=tuple(results),
    )


# ---------------------------------------------------------------------------
# Pillar B — /dev/mtd*ro SPI NOR & p12/p13/p18/p23/p30 Calibration Gate
# ---------------------------------------------------------------------------


def parse_proc_mtd(proc_mtd_text: str) -> Tuple[ProcMtdRegionInfo, ...]:
    regions: List[ProcMtdRegionInfo] = []
    for line in proc_mtd_text.splitlines():
        m = _MTD_PROC_LINE_RE.match(line.strip())
        if not m:
            continue
        mtd_name = m.group(1)
        size_b = int(m.group(2), 16)
        erase_b = int(m.group(3), 16)
        label = m.group(4)
        regions.append(ProcMtdRegionInfo(mtd_name, f"/dev/{mtd_name}ro", size_b, erase_b, label))
    return tuple(regions)


def audit_spi_nor_mtdro_dump(
    *,
    proc_mtd_text: str,
    device_path: str,
    open_mode: str,
    spi_nor_bytes: bytes,
    sd_exfat_sha256: str,
    mac_host_vault_sha256: str,
    ioctl_requested: Optional[str] = None,
) -> SpiNorMtdRoAuditReport:
    """Enforce /proc/mtd -> /dev/mtd*ro O_RDONLY discipline, erase alignment & IPL/BLoader/BL31/BootConfig envelope."""
    errors: List[str] = []
    regions = parse_proc_mtd(proc_mtd_text)
    if not regions:
        errors.append("PROC_MTD_EMPTY_OR_UNPARSEABLE")

    mtd_m = _DEV_MTD_RE.match(device_path)
    is_ro = bool(mtd_m and mtd_m.group(2) == "ro")
    if not is_ro:
        errors.append(BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN)
    if open_mode != "O_RDONLY":
        errors.append(BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN)
    if ioctl_requested and ioctl_requested.upper() in FORBIDDEN_MTD_IOCTLS:
        errors.append(BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN)

    erasesize = regions[0].erasesize_bytes if regions else SPI_NOR_ERASE_BLOCK_BYTES
    total_b = len(spi_nor_bytes)
    erase_aligned = total_b > 0 and erasesize > 0 and (total_b % erasesize == 0)
    if not erase_aligned:
        errors.append(f"{BLOCKED_SPI_NOR_ENVELOPE_OR_ALIGNMENT_INVALID}:len={total_b},erase={erasesize}")

    if all(b == 0 for b in spi_nor_bytes) or all(b == 0xFF for b in spi_nor_bytes):
        errors.append(f"{BLOCKED_SPI_NOR_ENVELOPE_OR_ALIGNMENT_INVALID}:blank_or_erased")

    detected_stages = _detect_spi_nor_stages(spi_nor_bytes)
    missing_stages = tuple(s for s in SPI_NOR_REQUIRED_BOOT_STAGES if s not in detected_stages)
    if missing_stages:
        errors.append(f"{BLOCKED_SPI_NOR_ENVELOPE_OR_ALIGNMENT_INVALID}:missing={','.join(missing_stages)}")

    actual_sha = sha256(spi_nor_bytes).hexdigest()
    dual_ok = (sd_exfat_sha256 == mac_host_vault_sha256 == actual_sha)
    if not dual_ok:
        errors.append(BLOCKED_DUAL_COPY_BITROT_DETECTED)

    valid = len(errors) == 0
    return SpiNorMtdRoAuditReport(
        valid=valid,
        device_path=device_path,
        open_mode=open_mode,
        ioctl_requested=ioctl_requested,
        proc_mtd_regions=regions,
        total_bytes=total_b,
        erasesize_bytes=erasesize,
        erase_aligned=erase_aligned,
        detected_boot_stages=detected_stages,
        missing_boot_stages=missing_stages,
        spi_nor_sha256=actual_sha,
        dual_copy_parity_ok=dual_ok,
        mtd_rw_opens_or_erase_ioctls=MTD_RW_OPENS_OR_ERASE_IOCTLS,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        errors=tuple(errors),
    )


def verify_per_camera_factory_cal_vault_gate(
    *,
    spi_nor_audit: SpiNorMtdRoAuditReport,
    entries: Mapping[str, DualLayerSurfaceEntry],
    samples: Mapping[str, bytes],
    target_body_serial_sha256: str,
    target_emmc_cid_sha256: str,
) -> SpiNorAndFactoryCalGateReport:
    """Enforce /dev/mtd*ro + p12/p13/p18/p23/p30 dual-copy SHA-256 lock before Stage-B human review."""
    cal_checks: List[PerCameraCalSurfaceCheck] = []
    errors: List[str] = list(spi_nor_audit.errors)

    for sid in PER_CAMERA_CAL_SURFACE_IDS:
        spec = _SURFACE_SPEC_MAP[sid]
        entry = entries.get(sid)
        sample = samples.get(sid, b"")
        c_errs: List[str] = []
        if entry is None:
            cal_checks.append(PerCameraCalSurfaceCheck(sid, False, False, False, False, (f"MISSING_CAL_SURFACE:{sid}",)))
            errors.append(f"MISSING_CAL_SURFACE:{sid}")
            continue

        magic_ok, m_errs = _verify_magic_sample(spec.expected_magic_kind, sample)
        if not magic_ok:
            if sid == "p18":
                c_errs.append(BLOCKED_P18_LENS_VX8900_INTEGRITY_FAILURE)
            elif sid in ("p23", "p30"):
                c_errs.append(BLOCKED_P23_P30_BK4_INTEGRITY_FAILURE)
            else:
                c_errs.extend(m_errs)

        dual_locked = (
            bool(_SHA256_HEX_RE.match(entry.sd_exfat_sha256))
            and entry.sd_exfat_sha256 == entry.mac_host_vault_sha256
            and entry.sd_exfat_sha256 == sha256(sample).hexdigest()
            and entry.gf256_healed_ok
        )
        if not dual_locked:
            c_errs.append(f"{BLOCKED_DUAL_COPY_BITROT_DETECTED}:{sid}")

        id_locked = (
            entry.body_serial_sha256 == target_body_serial_sha256
            and entry.emmc_cid_sha256 == target_emmc_cid_sha256
        )
        if not id_locked:
            c_errs.append(f"{BLOCKED_CROSS_CAMERA_FACTORY_CAL_LOCK}:{sid}")

        ok = magic_ok and dual_locked and id_locked and (len(c_errs) == 0)
        if not ok:
            errors.extend(c_errs)
        cal_checks.append(PerCameraCalSurfaceCheck(sid, ok, magic_ok, dual_locked, id_locked, tuple(c_errs)))

    passed = spi_nor_audit.valid and all(c.passed for c in cal_checks) and (len(errors) == 0)
    return SpiNorAndFactoryCalGateReport(
        passed=passed,
        status=STATUS_VERIFIED_PILLAR_B if passed else STATUS_REJECTED_PILLAR_B,
        stage_b_human_review_eligible=passed,
        spi_nor_audit=spi_nor_audit,
        factory_cal_checks=tuple(cal_checks),
        body_serial_sha256=target_body_serial_sha256,
        emmc_cid_sha256=target_emmc_cid_sha256,
        errors=tuple(errors),
    )


def run_pillar_b_6_scenario_gate() -> PillarBGate6ScenarioSuiteResult:
    """Execute the 6 Pillar B /dev/mtd*ro SPI NOR & p12/p13/p18/p23/p30 Calibration Gate scenarios."""
    body_a = sha256(b"fx3-camera-body-A").hexdigest()
    cid_a = sha256(b"fx3-emmc-cid-A").hexdigest()
    body_b = sha256(b"fx3-camera-body-B").hexdigest()

    proc_mtd = build_synthetic_proc_mtd_text()
    nor_bytes = build_synthetic_spi_nor_sample()
    nor_sha = sha256(nor_bytes).hexdigest()
    _sec0, entries_ok, samples_ok = build_synthetic_16_surface_vault(body_serial_sha256=body_a, emmc_cid_sha256=cid_a)

    results: List[PillarBScenarioResult] = []

    # PB1: Happy /dev/mtd0ro + p12/p13/p18/p23/p30 dual-copy locked
    nor_ok = audit_spi_nor_mtdro_dump(
        proc_mtd_text=proc_mtd,
        device_path="/dev/mtd0ro",
        open_mode="O_RDONLY",
        spi_nor_bytes=nor_bytes,
        sd_exfat_sha256=nor_sha,
        mac_host_vault_sha256=nor_sha,
    )
    g1 = verify_per_camera_factory_cal_vault_gate(
        spi_nor_audit=nor_ok, entries=entries_ok, samples=samples_ok, target_body_serial_sha256=body_a, target_emmc_cid_sha256=cid_a
    )
    results.append(PillarBScenarioResult(PILLAR_B_SCENARIO_IDS[0], g1.passed and g1.stage_b_human_review_eligible, g1.stage_b_human_review_eligible, g1.status, g1.errors))

    # PB2: /dev/mtd0 non-ro & O_RDWR
    nor_rw = audit_spi_nor_mtdro_dump(
        proc_mtd_text=proc_mtd,
        device_path="/dev/mtd0",
        open_mode="O_RDWR",
        spi_nor_bytes=nor_bytes,
        sd_exfat_sha256=nor_sha,
        mac_host_vault_sha256=nor_sha,
        ioctl_requested="MEMERASE",
    )
    g2 = verify_per_camera_factory_cal_vault_gate(
        spi_nor_audit=nor_rw, entries=entries_ok, samples=samples_ok, target_body_serial_sha256=body_a, target_emmc_cid_sha256=cid_a
    )
    results.append(PillarBScenarioResult(
        PILLAR_B_SCENARIO_IDS[1],
        (not g2.passed) and (not g2.stage_b_human_review_eligible) and (BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN in g2.errors),
        g2.stage_b_human_review_eligible,
        BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN,
        g2.errors,
    ))

    # PB3: Unaligned / missing BL31 in SPI NOR
    bad_nor = build_synthetic_spi_nor_sample(total_bytes=12345, include_all_stages=False)
    bad_nor_sha = sha256(bad_nor).hexdigest()
    nor_unaligned = audit_spi_nor_mtdro_dump(
        proc_mtd_text=proc_mtd,
        device_path="/dev/mtd0ro",
        open_mode="O_RDONLY",
        spi_nor_bytes=bad_nor,
        sd_exfat_sha256=bad_nor_sha,
        mac_host_vault_sha256=bad_nor_sha,
    )
    g3 = verify_per_camera_factory_cal_vault_gate(
        spi_nor_audit=nor_unaligned, entries=entries_ok, samples=samples_ok, target_body_serial_sha256=body_a, target_emmc_cid_sha256=cid_a
    )
    results.append(PillarBScenarioResult(
        PILLAR_B_SCENARIO_IDS[2],
        (not g3.passed) and (not g3.stage_b_human_review_eligible) and any(BLOCKED_SPI_NOR_ENVELOPE_OR_ALIGNMENT_INVALID in e for e in g3.errors),
        g3.stage_b_human_review_eligible,
        BLOCKED_SPI_NOR_ENVELOPE_OR_ALIGNMENT_INVALID,
        g3.errors,
    ))

    # PB4: p18 /lens missing VX8900
    samples_p18_bad = dict(samples_ok)
    samples_p18_bad["p18"] = build_synthetic_vfat_sample(marker=b"NO_LENS")
    g4 = verify_per_camera_factory_cal_vault_gate(
        spi_nor_audit=nor_ok, entries=entries_ok, samples=samples_p18_bad, target_body_serial_sha256=body_a, target_emmc_cid_sha256=cid_a
    )
    results.append(PillarBScenarioResult(
        PILLAR_B_SCENARIO_IDS[3],
        (not g4.passed) and (not g4.stage_b_human_review_eligible) and (BLOCKED_P18_LENS_VX8900_INTEGRITY_FAILURE in g4.errors),
        g4.stage_b_human_review_eligible,
        BLOCKED_P18_LENS_VX8900_INTEGRITY_FAILURE,
        g4.errors,
    ))

    # PB5: p23/p30 BK4\0 checksum/model corruption
    samples_p23_bad = dict(samples_ok)
    samples_p23_bad["p23"] = build_synthetic_bk4_sample(corrupt_checksum=True)
    g5 = verify_per_camera_factory_cal_vault_gate(
        spi_nor_audit=nor_ok, entries=entries_ok, samples=samples_p23_bad, target_body_serial_sha256=body_a, target_emmc_cid_sha256=cid_a
    )
    results.append(PillarBScenarioResult(
        PILLAR_B_SCENARIO_IDS[4],
        (not g5.passed) and (not g5.stage_b_human_review_eligible) and (BLOCKED_P23_P30_BK4_INTEGRITY_FAILURE in g5.errors),
        g5.stage_b_human_review_eligible,
        BLOCKED_P23_P30_BK4_INTEGRITY_FAILURE,
        g5.errors,
    ))

    # PB6: p12/p13 cross-camera body serial mismatch
    g6 = verify_per_camera_factory_cal_vault_gate(
        spi_nor_audit=nor_ok, entries=entries_ok, samples=samples_ok, target_body_serial_sha256=body_b, target_emmc_cid_sha256=cid_a
    )
    results.append(PillarBScenarioResult(
        PILLAR_B_SCENARIO_IDS[5],
        (not g6.passed) and (not g6.stage_b_human_review_eligible) and any(BLOCKED_CROSS_CAMERA_FACTORY_CAL_LOCK in e for e in g6.errors),
        g6.stage_b_human_review_eligible,
        BLOCKED_CROSS_CAMERA_FACTORY_CAL_LOCK,
        g6.errors,
    ))

    passed_cnt = sum(1 for r in results if r.passed)
    all_ok = passed_cnt == len(PILLAR_B_SCENARIO_IDS)
    return PillarBGate6ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_PILLAR_B if all_ok else STATUS_REJECTED_PILLAR_B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(PILLAR_B_SCENARIO_IDS),
        scenarios=tuple(results),
    )


# ---------------------------------------------------------------------------
# Unified Phase 151 Suite Entry Point
# ---------------------------------------------------------------------------


def run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite(
    force_clean_room: Optional[bool] = None,
) -> Tier0DualLayerVaultSuiteReport:
    """Execute full Phase 151 (Pillar 19) dual-mode Tier-0 Dual-Layer Vault & SPI NOR verifier."""
    donor_snap = inspect_tier0_dual_layer_donors_readonly(force_clean_room=force_clean_room)

    body_a = sha256(b"fx3-camera-body-A").hexdigest()
    cid_a = sha256(b"fx3-emmc-cid-A").hexdigest()
    sec0, entries, samples = build_synthetic_16_surface_vault(body_serial_sha256=body_a, emmc_cid_sha256=cid_a)
    pa_manifest = verify_dual_layer_16_surface_vault(
        sec0, entries, samples, expected_body_serial_sha256=body_a, expected_emmc_cid_sha256=cid_a
    )
    pa_suite = run_pillar_a_8_scenario_firewall()

    nor_bytes = build_synthetic_spi_nor_sample()
    nor_sha = sha256(nor_bytes).hexdigest()
    nor_audit = audit_spi_nor_mtdro_dump(
        proc_mtd_text=build_synthetic_proc_mtd_text(),
        device_path="/dev/mtd0ro",
        open_mode="O_RDONLY",
        spi_nor_bytes=nor_bytes,
        sd_exfat_sha256=nor_sha,
        mac_host_vault_sha256=nor_sha,
    )
    pb_gate = verify_per_camera_factory_cal_vault_gate(
        spi_nor_audit=nor_audit,
        entries=entries,
        samples=samples,
        target_body_serial_sha256=body_a,
        target_emmc_cid_sha256=cid_a,
    )
    pb_suite = run_pillar_b_6_scenario_gate()

    all_ok = (
        donor_snap.all_passed
        and pa_manifest.passed
        and pa_suite.passed
        and pb_gate.passed
        and pb_suite.passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (PHYSICAL_DEVICE_WRITES == 0)
        and (MTD_RW_OPENS_OR_ERASE_IOCTLS == 0)
    )

    digest_payload = {
        "schema": PHASE151_SCHEMA,
        "version": PHASE151_VERSION,
        "verification_mode": donor_snap.verification_mode,
        "donor_snapshot": donor_snap.to_dict(),
        "pillar_a_manifest": pa_manifest.to_dict(),
        "pillar_a_suite": pa_suite.to_dict(),
        "pillar_b_gate": pb_gate.to_dict(),
        "pillar_b_suite": pb_suite.to_dict(),
    }
    suite_sha = sha256(json.dumps(digest_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    return Tier0DualLayerVaultSuiteReport(
        schema=PHASE151_SCHEMA,
        version=PHASE151_VERSION,
        status=STATUS_VERIFIED_SUITE if all_ok else STATUS_FAIL_SUITE,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        read_only_donor_access=READ_ONLY_DONOR_ACCESS,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        mtd_rw_opens_or_erase_ioctls=MTD_RW_OPENS_OR_ERASE_IOCTLS,
        raw_firmware_bytes_leaked=donor_snap.raw_firmware_bytes_leaked,
        donor_snapshot=donor_snap,
        pillar_a_vault_manifest_report=pa_manifest,
        pillar_a_firewall_8_scenarios=pa_suite,
        pillar_b_spi_nor_and_cal_gate_report=pb_gate,
        pillar_b_gate_6_scenarios=pb_suite,
        suite_sha256=suite_sha,
    )
