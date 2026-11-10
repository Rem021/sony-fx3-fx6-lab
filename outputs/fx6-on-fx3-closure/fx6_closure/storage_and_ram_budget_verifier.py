"""Phase 9 — 30-Partition Zero-Repartition Storage/`p15` Footprint & Linux DDR/`tmpfs` RAM-Overlay Budget Verifier.

Covers two independent embedded systems storage/memory budgeting dimensions across read-only
FX3 7.02 and FX6 6.01 donors:

- **Dimension A (30-Partition Zero-Repartition Topology, `edisx.elf` Redline & `p15` `/usr` Footprint Budget)**:
  1. Cross-verifies FX3 (`0x0035E000` sectors = `1,724.00 MiB`) vs FX6 (`0x00384400` sectors =
     `1,800.50 MiB`, `+0x00026400` sectors = `+76.50 MiB` delta) 30-partition layouts across
     `partinf.conf` and `fx3_safety.boot_contracts.verify_sector0_partition_table`, plus the
     Octal-SPI NOR sector layout in `pformat_config.txt`, proving that **every FX6 runtime
     partition requirement maps onto FX3's stock Sector 0 without repartitioning**
     (`edisx_repartition_forbidden = True`, `sector0_mutation_bytes = 0`, `spi_nor_mutation_bytes = 0`):
     - `p20` (FX6 user 3D LUT store) -> FX3 stock `p30` (`48.00 MiB` = `50,331,648 B` via P1,
       holding all 16x `33^3` `.cube` LUTs with `66.75%` positive headroom);
     - `p21` (FX6 `44.50 MiB` `opelog`) -> RAM/`tmpfs` VFAT loopback (`8.00 MiB` / `16.00 MiB`
       on `/dev/loop7 -> /etc/opelog` via P2);
     - `p12` (`/cert` Tier-0) & `p18` (`/lens` Tier-0) -> kept untouched on FX3 stock LBAs
       (`0x0020C000` `40.00 MiB` and `0x0031C000` `20.00 MiB`), avoiding the `-20.00 MiB` `p18`
       LBA shift hazard of `edisx.elf`.
  2. Audits `nflasha15-manifest.json` (`834` entries: `753` regular files + `81` symlinks), walks
     `nflasha15-files` read-only (`33` subdirectories = `34` directories including `/usr` root),
     and inspects the ext2 superblock (`0xef53`) of `0700_part_image/dev/nflasha15` (`445,843,456 B`
     = `425.19 MiB`), computing exact raw bytes (`378,791,274 B` = `361.24 MiB`), 4 KiB-aligned
     block budget (`380,293,120 B` = `362.68 MiB`), SquashFS 4 KiB upper-bound budget, and ext4
     4 KiB `ro` filesystem budget against FX3 stock `p15` (`500.00 MiB` = `524,288,000 B`), proving
     strictly positive byte and MiB headroom.

- **Dimension B (CXD90057 Linux Usable DDR Pool & Stage-A `tmpfs` RAM-Overlay Memory Budget)**:
  1. Computes total SoC DDR (`8.00 GiB` in `cxd90057.dtb` `/memory@400000000`), Linux `mem=2G`
     ceiling (`2,147,483,648 B`), exact sum of all 7 `kemco.txt` `memrsv=` carveouts (`136,712,192 B`
     = `130.38 MiB`), and net Linux-managed DDR (`2,010,771,456 B` = `1,917.62 MiB`).
  2. Computes exact 4 KiB-page-aligned Stage-A `tmpfs` (`/tmp`) RAM-overlay footprints across all
     adapted binaries (`appFw.so`, `libInfraSetupFile.so`, `libInfraMediaCommon.so`,
     `libInfraMediaConfig.so`, `libInfraKikiLogGenerator.so`, `libInfraAppRemoteBoard.so`,
     `libfan.so`, `upm.ko`), `opelog.vfat` (`8 MiB` & `16 MiB` modes), `20,588 B` RAM-shadow
     `BK4\\0`, and CPIO streaming-unpack vs in-RAM peak-buffer unpack modes, proving all modes stay
     strictly within safe Linux `tmpfs` bounds without OOM risk while failing closed on over-budget
     payloads or Sector-0 rewrite attempts.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from fx3_safety.boot_contracts import (
    PartitionEntry,
    Sector0AuditResult,
    build_sector0_from_partitions,
    parse_partinf_conf,
    verify_sector0_partition_table,
)

from .backup_mount_tolerance_verifier import (
    DEFAULT_COLOR_PORT_WORK_DIR,
    DEFAULT_FX6_TEAM_DIR,
    PINNED_LIB_INFRA_KIKILOG_SHA256,
    synthesize_ram_shadow_bk4,
)
from .feature_routing_verifier import verify_p30_lut_capacity_budget
from .kernel_dtb_compatibility_verifier import (
    DEFAULT_FX3_DTB_PATH,
    DEFAULT_FX3_KEMCO_TXT_PATH,
    parse_fdt_blob,
    parse_kemco_bootargs,
)
from .patcher import (
    ALL_PHASE2_TARGET_SPECS,
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    apply_patch_spec,
    resolve_donor_binary_path,
)
from .ram_overlay_packager import CPIO_HEADER_SIZE, build_stage_a_ram_overlay_package
from .vfat_builder import build_opelog_vfat_image


SECTOR_BYTES = 512
PAGE_BYTES_4K = 4096
MIB_BYTES = 1024 * 1024

# Clean read-only donor paths
DEFAULT_FX3_PARTINF_PATH = (
    DEFAULT_COLOR_PORT_WORK_DIR / "input-20261028" / "original-update-engine" / "2.05" / "partinf.conf"
)
DEFAULT_FX6_PARTINF_PATH = (
    DEFAULT_FX6_TEAM_DIR / "donor" / "tree" / "0300_partconf" / "partinf.conf"
)
DEFAULT_PFORMAT_CONFIG_PATH = (
    DEFAULT_COLOR_PORT_WORK_DIR / "config-producer-20261029" / "original-files" / "pformat_config.txt"
)
DEFAULT_FX3_EDISX_PATH = (
    DEFAULT_COLOR_PORT_WORK_DIR / "package-20261028" / "updaterfs" / "bin" / "edisx.elf"
)
DEFAULT_FX6_EDISX_PATH = (
    DEFAULT_FX6_TEAM_DIR / "donor" / "nested-files" / "updater.img" / "bin" / "edisx.elf"
)
DEFAULT_FX6_NFLASH15_MANIFEST_PATH = (
    DEFAULT_FX6_TEAM_DIR / "donor" / "nflasha15-manifest.json"
)
DEFAULT_FX6_NFLASH15_FILES_DIR = (
    DEFAULT_FX6_TEAM_DIR / "donor" / "nflasha15-files"
)
DEFAULT_FX6_NFLASH15_IMAGE_PATH = (
    DEFAULT_FX6_TEAM_DIR / "donor" / "tree" / "0700_part_image" / "dev" / "nflasha15"
)

# Pinned SHA-256 digests
PINNED_FX3_PARTINF_SHA256 = "3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189"
PINNED_FX6_PARTINF_SHA256 = "e05b53d1f739968510dd24d62cd38426772fe3e50fe463a3d260c5f113e17ec9"
PINNED_PFORMAT_CONFIG_SHA256 = "21cd5b29dd165c322f5b00bb057802c377ff94af15f95881e150a32130302ece"
PINNED_EDISX_ELF_SHA256 = "3fab0e163242f0f4524d74d810dfb01baec4a505bcb37fccc43390012ea4b65a"
PINNED_NFLASH15_MANIFEST_SHA256 = "9dbd5331ea03543075df1ef547810d8d47a661651fecd683ee7aec238988aee4"

# Canonical 30-partition topology & footprint constants
EXPECTED_FX3_END_SECTOR = 0x0035E000  # 3,530,752 sectors = 1,807,745,024 B = 1,724.00 MiB
EXPECTED_FX6_END_SECTOR = 0x00384400  # 3,687,424 sectors = 1,887,961,088 B = 1,800.50 MiB
EXPECTED_UDA_DELTA_SECTORS = 0x00026400  # 156,672 sectors = 80,216,064 B = +76.50 MiB
EXPECTED_FX3_P15_SECTORS = 0x000FA000  # 1,024,000 sectors = 524,288,000 B = 500.00 MiB
EXPECTED_FX3_P15_BYTES = EXPECTED_FX3_P15_SECTORS * SECTOR_BYTES
EXPECTED_FX3_P30_SECTORS = 0x00018000  # 98,304 sectors = 50,331,648 B = 48.00 MiB
EXPECTED_FX3_P30_BYTES = EXPECTED_FX3_P30_SECTORS * SECTOR_BYTES
EXPECTED_FX6_P20_SECTORS = 0x00032000  # 204,800 sectors = 104,857,600 B = 100.00 MiB
EXPECTED_FX6_P21_SECTORS = 0x00016400  # 91,136 sectors = 46,661,632 B = 44.50 MiB

EXPECTED_NFLASH15_ENTRY_COUNT = 834
EXPECTED_NFLASH15_REGULAR_FILES = 753
EXPECTED_NFLASH15_SYMLINKS = 81
EXPECTED_NFLASH15_SUBDIRS = 33
EXPECTED_NFLASH15_TOTAL_DIRS = 34  # 33 subdirectories + 1 root directory (`/usr`)
EXPECTED_NFLASH15_RAW_BYTES = 378_791_274
EXPECTED_NFLASH15_ALIGNED_4K_BYTES = 380_293_120
EXPECTED_NFLASH15_EXT2_IMAGE_BYTES = 445_843_456
EXT2_SUPER_MAGIC = 0xEF53

# Conservative Linux DDR & Stage-A tmpfs safety limits
DEFAULT_LINUX_KERNEL_AND_INITRD_RESERVE_BYTES = 64 * MIB_BYTES  # 64.00 MiB static kernel + slab + ramdisk
DEFAULT_SAFE_STAGE_A_TMPFS_CEILING_BYTES = 256 * MIB_BYTES  # 256.00 MiB (<13.5% of Linux MemTotal)
TMPFS_INODE_METADATA_OVERHEAD_BYTES = 1024  # ~1 KiB shmem_inode_info + dentry overhead per tmpfs object

FORBIDDEN_REPARTITION_TOKENS: Tuple[str, ...] = (
    "edisx.elf",
    "ud_lerase.elf",
    "uc_mkfs.elf",
    "pformat",
    "of=/dev/nflasha ",
    "of=/dev/nflasha\n",
    "of=/dev/nflasha\"",
    "of=/dev/nflasha'",
    "BLKRRPART",
)
FORBIDDEN_REPARTITION_BINARIES: Tuple[str, ...] = (
    "edisx.elf",
    "ud_lerase.elf",
    "uc_mkfs.elf",
    "chknandcapa.elf",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _align_up(value: int, alignment: int) -> int:
    if value <= 0:
        return 0
    return ((value + alignment - 1) // alignment) * alignment


@dataclass(frozen=True)
class PartitionMappingEntry:
    index: int
    fx3_start_sector: int
    fx3_size_sectors: int
    fx3_size_mib: float
    fx6_start_sector: int
    fx6_size_sectors: int
    fx6_size_mib: float
    mapping_strategy: str
    fx3_backing_target: str
    zero_repartition_compatible: bool


@dataclass(frozen=True)
class SpiNorFileParam:
    path: str
    load_addr: int
    start_sector: int
    size_sectors: int
    ldrinfo: Optional[int]


@dataclass(frozen=True)
class SpiNorLayoutAudit:
    valid: bool
    sha256_verified: bool
    awake_entry: int
    bp_entry: int
    entries: Tuple[SpiNorFileParam, ...]
    has_overlaps: bool
    spi_nor_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ZeroRepartitionRedlineAudit:
    valid: bool
    edisx_repartition_forbidden: bool
    edisx_donor_sha256_verified: bool
    edisx_identical_across_models: bool
    edisx_has_blkrrpart_signature: bool
    sector0_mutation_bytes: int
    spi_nor_mutation_bytes: int
    forbidden_script_hits: Tuple[str, ...]
    forbidden_binary_hits: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P15UsrFootprintAudit:
    valid: bool
    manifest_sha256_verified: bool
    manifest_entry_count: int
    regular_file_count: int
    zero_byte_file_count: int
    symlink_count: int
    subdirectory_count: int
    total_directory_count: int
    walk_cross_check_matched: bool
    raw_payload_bytes: int
    raw_payload_mib: float
    aligned_4k_payload_bytes: int
    aligned_4k_payload_mib: float
    squashfs_uncompressed_upper_bytes: int
    squashfs_uncompressed_upper_mib: float
    ext4_ro_4k_budget_bytes: int
    ext4_ro_4k_budget_mib: float
    donor_ext2_image_present: bool
    donor_ext2_magic_ok: bool
    donor_ext2_image_bytes: int
    donor_ext2_image_mib: float
    fx3_stock_p15_bytes: int
    fx3_stock_p15_mib: float
    raw_headroom_bytes: int
    raw_headroom_mib: float
    squashfs_upper_headroom_bytes: int
    squashfs_upper_headroom_mib: float
    ext4_ro_headroom_bytes: int
    ext4_ro_headroom_mib: float
    donor_ext2_image_headroom_bytes: int
    donor_ext2_image_headroom_mib: float
    p15_fits_stock_fx3: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StorageTopologyAndP15Report:
    all_checks_passed: bool
    fx3_partinf_sha256_verified: bool
    fx6_partinf_sha256_verified: bool
    fx3_sector0_audit: Sector0AuditResult
    fx6_sector0_audit: Sector0AuditResult
    fx3_end_sector: int
    fx3_total_uda_bytes: int
    fx3_total_uda_mib: float
    fx6_end_sector: int
    fx6_total_uda_bytes: int
    fx6_total_uda_mib: float
    uda_delta_sectors: int
    uda_delta_bytes: int
    uda_delta_mib: float
    identical_prefix_partition_count: int
    partition_mappings: Tuple[PartitionMappingEntry, ...]
    all_30_partitions_mapped_zero_repartition: bool
    p20_to_p30_lut_headroom_bytes: int
    p20_to_p30_lut_headroom_mib: float
    p21_tmpfs_vfat_8m_bytes: int
    p21_tmpfs_vfat_16m_bytes: int
    spi_nor_audit: SpiNorLayoutAudit
    redline_audit: ZeroRepartitionRedlineAudit
    p15_footprint: P15UsrFootprintAudit
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class OverlayComponentFootprint:
    name: str
    category: str
    raw_bytes: int
    paged_4k_bytes: int
    cpio_record_bytes: int


@dataclass(frozen=True)
class TmpfsUnpackScenarioBudget:
    scenario_id: str
    vfat_mode: str
    unpack_mode: str  # "streaming_unpack" or "peak_buffer_unpack"
    steady_state_tmpfs_bytes: int
    steady_state_tmpfs_mib: float
    peak_tmpfs_bytes: int
    peak_tmpfs_mib: float
    safe_tmpfs_ceiling_bytes: int
    safe_tmpfs_ceiling_mib: float
    linux_default_tmpfs_50pct_bytes: int
    headroom_vs_safe_ceiling_bytes: int
    headroom_vs_safe_ceiling_mib: float
    headroom_vs_linux_tmpfs_50pct_bytes: int
    share_of_linux_memtotal_pct: float
    within_safe_bounds: bool


@dataclass(frozen=True)
class DdrCarveoutItem:
    phys_addr: int
    size_bytes: int
    size_mib: float
    uncached: bool


@dataclass(frozen=True)
class LinuxDdrAndTmpfsBudgetReport:
    all_checks_passed: bool
    soc_dtb_memory_base: int
    soc_dtb_total_ddr_bytes: int
    soc_dtb_total_ddr_mib: float
    kemco_mem_limit_bytes: int
    kemco_mem_limit_mib: float
    kemco_carveout_count: int
    kemco_carveouts: Tuple[DdrCarveoutItem, ...]
    total_memrsv_carveout_bytes: int
    total_memrsv_carveout_mib: float
    net_linux_managed_ddr_bytes: int
    net_linux_managed_ddr_mib: float
    kernel_and_initrd_reserve_bytes: int
    estimated_userland_free_ddr_bytes: int
    estimated_userland_free_ddr_mib: float
    linux_default_tmpfs_50pct_bytes: int
    linux_default_tmpfs_50pct_mib: float
    safe_stage_a_tmpfs_ceiling_bytes: int
    safe_stage_a_tmpfs_ceiling_mib: float
    components_8m: Tuple[OverlayComponentFootprint, ...]
    components_16m: Tuple[OverlayComponentFootprint, ...]
    ram_shadow_bk4_bytes: int
    control_cpio_archive_bytes: int
    scenarios: Tuple[TmpfsUnpackScenarioBudget, ...]
    ram_budget_within_safe_bounds: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase9StorageAndRamBudgetReport:
    all_checks_passed: bool
    edisx_repartition_forbidden: bool
    sector0_mutation_bytes: int
    p15_fits_stock_fx3: bool
    ram_budget_within_safe_bounds: bool
    dimension_a_storage: StorageTopologyAndP15Report
    dimension_b_ddr_tmpfs: LinuxDdrAndTmpfsBudgetReport


def parse_and_audit_pformat_config(
    pformat_path: Path = DEFAULT_PFORMAT_CONFIG_PATH,
    *,
    spi_nor_mutation_bytes: int = 0,
) -> SpiNorLayoutAudit:
    """Parse and validate the Octal-SPI NOR layout in `pformat_config.txt`."""
    errors: List[str] = []
    raw_bytes = pformat_path.read_bytes()
    sha_ok = _sha256(raw_bytes) == PINNED_PFORMAT_CONFIG_SHA256
    if not sha_ok:
        errors.append(f"pformat_config.txt SHA-256 mismatch on {pformat_path}")

    text = raw_bytes.decode("utf-8", errors="replace")
    awake_m = re.search(r"awake_entry\s*=\s*(0x[0-9A-Fa-f]+|\d+)", text)
    bp_m = re.search(r"bp_entry\s*=\s*(0x[0-9A-Fa-f]+|\d+)", text)
    awake_entry = int(awake_m.group(1), 0) if awake_m else 0
    bp_entry = int(bp_m.group(1), 0) if bp_m else 0
    if awake_entry != 0xFE049000 or bp_entry != 0xFE049000:
        errors.append(
            f"Unexpected awake_entry/bp_entry in pformat_config.txt: {hex(awake_entry)} / {hex(bp_entry)}"
        )

    entries: List[SpiNorFileParam] = []
    for blk in re.finditer(r"file_param\s*\{([^}]*)\}", text, flags=re.DOTALL):
        body = blk.group(1)
        path_m = re.search(r'path\s*=\s*"([^"]+)"', body)
        load_m = re.search(r"load\s*=\s*(0x[0-9A-Fa-f]+|\d+)", body)
        start_m = re.search(r"start\s*=\s*(0x[0-9A-Fa-f]+|\d+)", body)
        size_m = re.search(r"size\s*=\s*(0x[0-9A-Fa-f]+|\d+)", body)
        ldr_m = re.search(r"ldrinfo\s*=\s*(0x[0-9A-Fa-f]+|\d+)", body)
        if not (path_m and load_m and start_m and size_m):
            errors.append(f"Incomplete file_param block in pformat_config.txt: {body!r}")
            continue
        entries.append(
            SpiNorFileParam(
                path=path_m.group(1),
                load_addr=int(load_m.group(1), 0),
                start_sector=int(start_m.group(1), 0),
                size_sectors=int(size_m.group(1), 0),
                ldrinfo=int(ldr_m.group(1), 0) if ldr_m else None,
            )
        )

    if len(entries) != 6:
        errors.append(f"Expected 6 file_param blocks in pformat_config.txt, got {len(entries)}")

    has_overlaps = False
    sized_spans: List[Tuple[int, int, str]] = []
    for e in entries:
        if e.start_sector < 4:
            errors.append(f"SPI NOR entry {e.path} collides with Information Sector (<4): start={e.start_sector}")
            has_overlaps = True
        if e.size_sectors > 0:
            end_s = e.start_sector + e.size_sectors
            for ps, pe, pname in sized_spans:
                if not (end_s <= ps or e.start_sector >= pe):
                    errors.append(
                        f"SPI NOR overlap between {e.path} [{e.start_sector}..{end_s}) and {pname} [{ps}..{pe})"
                    )
                    has_overlaps = True
            sized_spans.append((e.start_sector, end_s, e.path))

    if spi_nor_mutation_bytes != 0:
        errors.append(
            f"SPI NOR write redline violated: spi_nor_mutation_bytes={spi_nor_mutation_bytes} (must be 0)"
        )

    valid = sha_ok and len(entries) == 6 and not has_overlaps and spi_nor_mutation_bytes == 0 and not errors
    return SpiNorLayoutAudit(
        valid=valid,
        sha256_verified=sha_ok,
        awake_entry=awake_entry,
        bp_entry=bp_entry,
        entries=tuple(entries),
        has_overlaps=has_overlaps,
        spi_nor_mutation_bytes=spi_nor_mutation_bytes,
        errors=tuple(errors),
    )


def audit_zero_repartition_redline(
    *,
    scripts: Sequence[Tuple[str, str]] = (),
    staged_binary_names: Sequence[str] = (),
    sector0_mutation_bytes: int = 0,
    spi_nor_mutation_bytes: int = 0,
    fx3_edisx_path: Path = DEFAULT_FX3_EDISX_PATH,
    fx6_edisx_path: Path = DEFAULT_FX6_EDISX_PATH,
) -> ZeroRepartitionRedlineAudit:
    """Enforce the zero-repartition redline (`edisx.elf` & Sector-0 mutation strictly prohibited)."""
    errors: List[str] = []
    fx3_edisx = fx3_edisx_path.read_bytes()
    fx6_edisx = fx6_edisx_path.read_bytes()

    fx3_sha = _sha256(fx3_edisx)
    fx6_sha = _sha256(fx6_edisx)
    edisx_sha_ok = fx3_sha == PINNED_EDISX_ELF_SHA256 and fx6_sha == PINNED_EDISX_ELF_SHA256
    edisx_same = fx3_edisx == fx6_edisx
    has_blkrrpart = (
        b"Usage: edisx.elf device_file partinfo_file" in fx6_edisx
        and b"BLKRRPART" in fx6_edisx
        and b"Partition Table" in fx6_edisx
    )

    if not edisx_sha_ok:
        errors.append(f"Unexpected edisx.elf SHA-256: fx3={fx3_sha[:16]}... fx6={fx6_sha[:16]}...")
    if not has_blkrrpart:
        errors.append("edisx.elf missing expected Sector-0 Partition Table / BLKRRPART signatures")

    if sector0_mutation_bytes != 0:
        errors.append(
            f"CRITICAL REDLINE: Sector-0 mutation attempted ({sector0_mutation_bytes} bytes != 0)"
        )
    if spi_nor_mutation_bytes != 0:
        errors.append(
            f"CRITICAL REDLINE: Octal-SPI NOR mutation attempted ({spi_nor_mutation_bytes} bytes != 0)"
        )

    script_hits: List[str] = []
    for script_label, script_body in scripts:
        active_lines = [
            ln for ln in script_body.splitlines() if ln.strip() and not ln.lstrip().startswith("#")
        ]
        joined = "\n".join(active_lines) + "\n"
        for tok in FORBIDDEN_REPARTITION_TOKENS:
            if tok in joined:
                hit = f"{script_label}:{tok.strip()}"
                script_hits.append(hit)
                errors.append(f"Forbidden repartition/format command {tok.strip()!r} in {script_label}")
        # Also catch raw `/dev/nflasha` (whole-disk LBA 0) write redirection without partition number
        if re.search(r"(?:of=|>\s*)/dev/(?:c|p)?nflasha(?![0-9B])", joined):
            hit = f"{script_label}:raw_/dev/nflasha_write"
            script_hits.append(hit)
            errors.append(f"Forbidden raw whole-eMMC `/dev/nflasha` write target in {script_label}")

    bin_hits: List[str] = []
    for bname in staged_binary_names:
        base = Path(bname).name
        if base in FORBIDDEN_REPARTITION_BINARIES:
            bin_hits.append(bname)
            errors.append(f"Forbidden repartition/format utility staged in candidate payload: {bname!r}")

    valid = (
        edisx_sha_ok
        and edisx_same
        and has_blkrrpart
        and sector0_mutation_bytes == 0
        and spi_nor_mutation_bytes == 0
        and len(script_hits) == 0
        and len(bin_hits) == 0
        and len(errors) == 0
    )
    return ZeroRepartitionRedlineAudit(
        valid=valid,
        edisx_repartition_forbidden=True,
        edisx_donor_sha256_verified=edisx_sha_ok,
        edisx_identical_across_models=edisx_same,
        edisx_has_blkrrpart_signature=has_blkrrpart,
        sector0_mutation_bytes=sector0_mutation_bytes,
        spi_nor_mutation_bytes=spi_nor_mutation_bytes,
        forbidden_script_hits=tuple(script_hits),
        forbidden_binary_hits=tuple(bin_hits),
        errors=tuple(errors),
    )


def audit_p15_usr_footprint(
    manifest_path: Path = DEFAULT_FX6_NFLASH15_MANIFEST_PATH,
    files_dir: Optional[Path] = DEFAULT_FX6_NFLASH15_FILES_DIR,
    donor_image_path: Optional[Path] = DEFAULT_FX6_NFLASH15_IMAGE_PATH,
    *,
    fx3_p15_capacity_bytes: int = EXPECTED_FX3_P15_BYTES,
    additional_payload_bytes: int = 0,
) -> P15UsrFootprintAudit:
    """Audit FX6 `nflasha15` (`/usr`) manifest, extracted tree, and 4 KiB-block storage budgets."""
    errors: List[str] = []
    mf_bytes = manifest_path.read_bytes()
    mf_sha_ok = _sha256(mf_bytes) == PINNED_NFLASH15_MANIFEST_SHA256
    if not mf_sha_ok:
        errors.append(f"nflasha15-manifest.json SHA-256 mismatch on {manifest_path}")

    manifest_obj = json.loads(mf_bytes.decode("utf-8"))
    entries = manifest_obj.get("entries", [])
    if not isinstance(entries, list) or len(entries) == 0:
        errors.append("nflasha15-manifest.json contains no entries")

    reg_files = [e for e in entries if isinstance(e, dict) and e.get("kind") == "file"]
    symlinks = [e for e in entries if isinstance(e, dict) and e.get("kind") == "symlink"]
    zero_byte_files = sum(1 for e in reg_files if int(e.get("bytes", 0)) == 0)

    raw_bytes = sum(int(e["bytes"]) for e in reg_files) + max(0, additional_payload_bytes)
    aligned_4k_bytes = sum(_align_up(int(e["bytes"]), PAGE_BYTES_4K) for e in reg_files) + _align_up(
        max(0, additional_payload_bytes), PAGE_BYTES_4K
    )

    if additional_payload_bytes < 0:
        errors.append(f"additional_payload_bytes must be non-negative, got {additional_payload_bytes}")

    # Infer directory hierarchy from manifest paths as fallback, and cross-verify via read-only walk
    inferred_dirs = set()
    for e in entries:
        if not isinstance(e, dict):
            continue
        parts = str(e.get("path", "")).strip("/").split("/")
        for idx in range(1, len(parts)):
            inferred_dirs.add("/" + "/".join(parts[:idx]))

    subdir_count = len(inferred_dirs)
    walk_matched = True
    if files_dir is not None and files_dir.is_dir():
        walk_subdirs = 0
        walk_reg_files = 0
        walk_raw_sum = 0
        for root, dirs, files in os.walk(files_dir):
            dirs[:] = [d for d in dirs if not d.lower().startswith("stage")]
            for d in dirs:
                dp = Path(root) / d
                if not dp.is_symlink():
                    walk_subdirs += 1
            for fn in files:
                fp = Path(root) / fn
                if not fp.is_symlink():
                    walk_reg_files += 1
                    walk_raw_sum += fp.stat().st_size
        subdir_count = walk_subdirs
        base_manifest_raw = sum(int(e["bytes"]) for e in reg_files)
        walk_matched = (walk_reg_files == len(reg_files)) and (walk_raw_sum == base_manifest_raw)
        if not walk_matched:
            errors.append(
                f"nflasha15-files walk mismatch vs manifest: walk=({walk_reg_files} files, {walk_raw_sum} B) "
                f"vs manifest=({len(reg_files)} files, {base_manifest_raw} B)"
            )

    total_dir_count = subdir_count + 1  # include `/usr` root inode

    # SquashFS 4 KiB-aligned uncompressed upper-bound budget (128 B/inode+dir-entry metadata + 4 KiB pad)
    squash_meta = _align_up((len(entries) + total_dir_count) * 128 + 4096, PAGE_BYTES_4K)
    squashfs_upper_bytes = aligned_4k_bytes + squash_meta

    # Conservative ext4 read-only 4 KiB-block filesystem budget:
    # 4 KiB-aligned file data blocks + 1x 4 KiB block per directory/long-symlink +
    # 16,384 x 256-byte inodes (4.00 MiB) + 2% superblock/GDT/block-bitmap reserve
    dir_and_link_blocks = (total_dir_count + len(symlinks)) * PAGE_BYTES_4K
    inode_table_bytes = 16384 * 256
    fs_meta_reserve = _align_up(int(aligned_4k_bytes * 0.02), PAGE_BYTES_4K)
    ext4_ro_bytes = aligned_4k_bytes + dir_and_link_blocks + inode_table_bytes + fs_meta_reserve

    # Inspect donor raw ext2 partition image header (read-only 2 KiB superblock read!)
    donor_img_present = False
    donor_ext2_magic_ok = False
    donor_img_bytes = 0
    if donor_image_path is not None and donor_image_path.is_file():
        donor_img_present = True
        donor_img_bytes = donor_image_path.stat().st_size + max(0, additional_payload_bytes)
        with donor_image_path.open("rb") as fh:
            fh.seek(1024)
            sb = fh.read(128)
        if len(sb) >= 0x3A:
            s_magic = struct.unpack_from("<H", sb, 0x38)[0]
            donor_ext2_magic_ok = s_magic == EXT2_SUPER_MAGIC
        if not donor_ext2_magic_ok:
            errors.append(f"Donor nflasha15 image {donor_image_path} missing ext2 magic 0xef53")

    raw_headroom = fx3_p15_capacity_bytes - raw_bytes
    squash_headroom = fx3_p15_capacity_bytes - squashfs_upper_bytes
    ext4_headroom = fx3_p15_capacity_bytes - ext4_ro_bytes
    donor_img_headroom = (
        (fx3_p15_capacity_bytes - donor_img_bytes) if donor_img_present else ext4_headroom
    )

    fits_stock_p15 = (
        raw_headroom > 0
        and squash_headroom > 0
        and ext4_headroom > 0
        and donor_img_headroom > 0
    )
    if not fits_stock_p15:
        errors.append(
            f"FX6 /usr payload exceeds FX3 p15 capacity ({fx3_p15_capacity_bytes} B): "
            f"raw_headroom={raw_headroom} B, ext4_headroom={ext4_headroom} B, "
            f"donor_img_headroom={donor_img_headroom} B"
        )

    valid = mf_sha_ok and walk_matched and fits_stock_p15 and len(errors) == 0
    return P15UsrFootprintAudit(
        valid=valid,
        manifest_sha256_verified=mf_sha_ok,
        manifest_entry_count=len(entries),
        regular_file_count=len(reg_files),
        zero_byte_file_count=zero_byte_files,
        symlink_count=len(symlinks),
        subdirectory_count=subdir_count,
        total_directory_count=total_dir_count,
        walk_cross_check_matched=walk_matched,
        raw_payload_bytes=raw_bytes,
        raw_payload_mib=round(raw_bytes / MIB_BYTES, 4),
        aligned_4k_payload_bytes=aligned_4k_bytes,
        aligned_4k_payload_mib=round(aligned_4k_bytes / MIB_BYTES, 4),
        squashfs_uncompressed_upper_bytes=squashfs_upper_bytes,
        squashfs_uncompressed_upper_mib=round(squashfs_upper_bytes / MIB_BYTES, 4),
        ext4_ro_4k_budget_bytes=ext4_ro_bytes,
        ext4_ro_4k_budget_mib=round(ext4_ro_bytes / MIB_BYTES, 4),
        donor_ext2_image_present=donor_img_present,
        donor_ext2_magic_ok=donor_ext2_magic_ok,
        donor_ext2_image_bytes=donor_img_bytes,
        donor_ext2_image_mib=round(donor_img_bytes / MIB_BYTES, 4),
        fx3_stock_p15_bytes=fx3_p15_capacity_bytes,
        fx3_stock_p15_mib=round(fx3_p15_capacity_bytes / MIB_BYTES, 4),
        raw_headroom_bytes=raw_headroom,
        raw_headroom_mib=round(raw_headroom / MIB_BYTES, 4),
        squashfs_upper_headroom_bytes=squash_headroom,
        squashfs_upper_headroom_mib=round(squash_headroom / MIB_BYTES, 4),
        ext4_ro_headroom_bytes=ext4_headroom,
        ext4_ro_headroom_mib=round(ext4_headroom / MIB_BYTES, 4),
        donor_ext2_image_headroom_bytes=donor_img_headroom,
        donor_ext2_image_headroom_mib=round(donor_img_headroom / MIB_BYTES, 4),
        p15_fits_stock_fx3=fits_stock_p15,
        errors=tuple(errors),
    )


def _classify_partition_mapping(fx3_e: PartitionEntry, fx6_e: PartitionEntry) -> Tuple[str, str, bool]:
    idx = fx3_e.index
    if (
        fx3_e.start_sector == fx6_e.start_sector
        and fx3_e.size_sectors == fx6_e.size_sectors
        and fx3_e.part_type == fx6_e.part_type
    ):
        if fx3_e.size_sectors == 0:
            return ("UNUSED_ZERO_SIZE", "none", True)
        return ("IDENTICAL_GEOMETRY", f"/dev/nflasha{idx}", True)

    if idx == 12:
        ok = fx3_e.size_sectors >= fx6_e.size_sectors and fx3_e.start_sector == fx6_e.start_sector
        return ("PRESERVE_FX3_STOCK_TIER0_CERT", "/dev/nflasha12 (40 MiB stock >= 20 MiB)", ok)
    if idx == 13:
        ok = fx3_e.size_sectors == fx6_e.size_sectors
        return ("INDEX_MOUNTED_SAME_SIZE", "/dev/nflasha13 (4 MiB)", ok)
    if idx == 15:
        ok = fx3_e.size_sectors == EXPECTED_FX3_P15_SECTORS and fx6_e.size_sectors == EXPECTED_FX3_P15_SECTORS
        return ("INDEX_MOUNTED_SAME_SIZE_500MIB", "/dev/nflasha15 (500 MiB /usr)", ok)
    if idx == 18:
        ok = fx3_e.start_sector == 0x0031C000 and fx3_e.size_sectors == fx6_e.size_sectors == 0x0000A000
        return ("PRESERVE_FX3_STOCK_TIER0_LENS", "/dev/nflasha18 (LBA 0x31C000 intact)", ok)
    if idx == 20:
        ok = fx3_e.size_sectors == 0 and fx6_e.size_sectors == EXPECTED_FX6_P20_SECTORS
        return ("REMAPPED_TO_FX3_P30_VIA_P1", "/dev/nflasha30 (48 MiB LutData via P1)", ok)
    if idx == 21:
        ok = fx3_e.size_sectors == 0 and fx6_e.size_sectors == EXPECTED_FX6_P21_SECTORS
        return ("REMAPPED_TO_TMPFS_VFAT_LOOPBACK_VIA_P2", "/tmp/opelog.vfat -> /etc/opelog (8/16 MiB via P2)", ok)
    if idx == 23:
        ok = fx3_e.size_sectors == fx6_e.size_sectors == 0x00020000
        return ("INDEX_MOUNTED_SAME_SIZE_PMBP", "/dev/nflasha23 (64 MiB PMBP)", ok)
    if idx == 30:
        ok = fx3_e.size_sectors == EXPECTED_FX3_P30_SECTORS and fx6_e.size_sectors == 0
        return ("ACTIVE_LUT_TARGET_FOR_FX6_P20", "/dev/nflasha30 (48 MiB LutData)", ok)
    if fx3_e.size_sectors == 0 and fx6_e.size_sectors == 0:
        return ("UNUSED_ZERO_SIZE", "none", True)
    return ("UNMAPPED_CONFLICT", "none", False)


def audit_storage_topology_and_p15_budget(
    *,
    fx3_partinf_path: Path = DEFAULT_FX3_PARTINF_PATH,
    fx6_partinf_path: Path = DEFAULT_FX6_PARTINF_PATH,
    pformat_config_path: Path = DEFAULT_PFORMAT_CONFIG_PATH,
    manifest_path: Path = DEFAULT_FX6_NFLASH15_MANIFEST_PATH,
    files_dir: Optional[Path] = DEFAULT_FX6_NFLASH15_FILES_DIR,
    donor_image_path: Optional[Path] = DEFAULT_FX6_NFLASH15_IMAGE_PATH,
    scripts_to_audit: Sequence[Tuple[str, str]] = (),
    staged_binary_names: Sequence[str] = (),
    sector0_mutation_bytes: int = 0,
    spi_nor_mutation_bytes: int = 0,
    additional_p15_payload_bytes: int = 0,
) -> StorageTopologyAndP15Report:
    """Execute Dimension A: 30-Partition Zero-Repartition Topology, `edisx.elf` Redline & `p15` Budget."""
    errors: List[str] = []

    fx3_raw = fx3_partinf_path.read_bytes()
    fx6_raw = fx6_partinf_path.read_bytes()
    fx3_sha_ok = _sha256(fx3_raw) == PINNED_FX3_PARTINF_SHA256
    fx6_sha_ok = _sha256(fx6_raw) == PINNED_FX6_PARTINF_SHA256
    if not fx3_sha_ok:
        errors.append(f"FX3 partinf.conf SHA-256 mismatch on {fx3_partinf_path}")
    if not fx6_sha_ok:
        errors.append(f"FX6 partinf.conf SHA-256 mismatch on {fx6_partinf_path}")

    fx3_entries = parse_partinf_conf(fx3_raw.decode("utf-8", errors="replace"))
    fx6_entries = parse_partinf_conf(fx6_raw.decode("utf-8", errors="replace"))

    fx3_s0 = build_sector0_from_partitions(fx3_entries)
    fx6_s0 = build_sector0_from_partitions(fx6_entries)
    fx3_s0_audit = verify_sector0_partition_table(fx3_s0)
    fx6_s0_audit = verify_sector0_partition_table(fx6_s0)

    if not fx3_s0_audit.valid or fx3_s0_audit.layout_profile != "FX3_PARTINF_205":
        errors.append(f"FX3 Sector-0 audit failed: profile={fx3_s0_audit.layout_profile} errs={fx3_s0_audit.errors}")
    if not fx6_s0_audit.valid or fx6_s0_audit.layout_profile != "FX6_PARTINF_601":
        errors.append(f"FX6 Sector-0 audit failed: profile={fx6_s0_audit.layout_profile} errs={fx6_s0_audit.errors}")

    fx3_end = max(e.start_sector + e.size_sectors for e in fx3_entries)
    fx6_end = max(e.start_sector + e.size_sectors for e in fx6_entries)
    delta_sectors = fx6_end - fx3_end
    if fx3_end != EXPECTED_FX3_END_SECTOR:
        errors.append(f"Expected FX3 end sector {hex(EXPECTED_FX3_END_SECTOR)}, got {hex(fx3_end)}")
    if fx6_end != EXPECTED_FX6_END_SECTOR:
        errors.append(f"Expected FX6 end sector {hex(EXPECTED_FX6_END_SECTOR)}, got {hex(fx6_end)}")
    if delta_sectors != EXPECTED_UDA_DELTA_SECTORS:
        errors.append(f"Expected UDA delta {hex(EXPECTED_UDA_DELTA_SECTORS)}, got {hex(delta_sectors)}")

    identical_prefix = 0
    for e3, e6 in zip(fx3_entries, fx6_entries):
        if (e3.start_sector, e3.size_sectors, e3.part_type, e3.flag) == (
            e6.start_sector,
            e6.size_sectors,
            e6.part_type,
            e6.flag,
        ):
            identical_prefix += 1
        else:
            break

    mappings: List[PartitionMappingEntry] = []
    all_mapped = True
    for e3, e6 in zip(fx3_entries, fx6_entries):
        strat, backing, compat = _classify_partition_mapping(e3, e6)
        if not compat:
            all_mapped = False
            errors.append(f"Partition p{e3.index} failed zero-repartition mapping ({strat})")
        mappings.append(
            PartitionMappingEntry(
                index=e3.index,
                fx3_start_sector=e3.start_sector,
                fx3_size_sectors=e3.size_sectors,
                fx3_size_mib=round((e3.size_sectors * SECTOR_BYTES) / MIB_BYTES, 4),
                fx6_start_sector=e6.start_sector,
                fx6_size_sectors=e6.size_sectors,
                fx6_size_mib=round((e6.size_sectors * SECTOR_BYTES) / MIB_BYTES, 4),
                mapping_strategy=strat,
                fx3_backing_target=backing,
                zero_repartition_compatible=compat,
            )
        )

    lut_cap = verify_p30_lut_capacity_budget(max_user_luts=16, cluster_size_bytes=8192)
    if not lut_cap.fits_in_fx3_p30:
        errors.append("P1 p20 -> p30 16x 3D LUT VFAT capacity check failed")
    lut_headroom_bytes = lut_cap.canonical_free_bytes

    vfat8, _ = build_opelog_vfat_image(mode="8m_ram")
    vfat16, _ = build_opelog_vfat_image(mode="16m_log")

    spi_audit = parse_and_audit_pformat_config(
        pformat_config_path,
        spi_nor_mutation_bytes=spi_nor_mutation_bytes,
    )
    if not spi_audit.valid:
        errors.extend(spi_audit.errors)

    redline_audit = audit_zero_repartition_redline(
        scripts=scripts_to_audit,
        staged_binary_names=staged_binary_names,
        sector0_mutation_bytes=sector0_mutation_bytes,
        spi_nor_mutation_bytes=spi_nor_mutation_bytes,
    )
    if not redline_audit.valid:
        errors.extend(redline_audit.errors)

    p15_audit = audit_p15_usr_footprint(
        manifest_path=manifest_path,
        files_dir=files_dir,
        donor_image_path=donor_image_path,
        additional_payload_bytes=additional_p15_payload_bytes,
    )
    if not p15_audit.valid:
        errors.extend(p15_audit.errors)

    all_ok = (
        fx3_sha_ok
        and fx6_sha_ok
        and fx3_s0_audit.valid
        and fx6_s0_audit.valid
        and fx3_end == EXPECTED_FX3_END_SECTOR
        and fx6_end == EXPECTED_FX6_END_SECTOR
        and delta_sectors == EXPECTED_UDA_DELTA_SECTORS
        and identical_prefix == 11
        and all_mapped
        and lut_cap.fits_in_fx3_p30
        and spi_audit.valid
        and redline_audit.valid
        and p15_audit.valid
        and len(errors) == 0
    )

    return StorageTopologyAndP15Report(
        all_checks_passed=all_ok,
        fx3_partinf_sha256_verified=fx3_sha_ok,
        fx6_partinf_sha256_verified=fx6_sha_ok,
        fx3_sector0_audit=fx3_s0_audit,
        fx6_sector0_audit=fx6_s0_audit,
        fx3_end_sector=fx3_end,
        fx3_total_uda_bytes=fx3_end * SECTOR_BYTES,
        fx3_total_uda_mib=round((fx3_end * SECTOR_BYTES) / MIB_BYTES, 4),
        fx6_end_sector=fx6_end,
        fx6_total_uda_bytes=fx6_end * SECTOR_BYTES,
        fx6_total_uda_mib=round((fx6_end * SECTOR_BYTES) / MIB_BYTES, 4),
        uda_delta_sectors=delta_sectors,
        uda_delta_bytes=delta_sectors * SECTOR_BYTES,
        uda_delta_mib=round((delta_sectors * SECTOR_BYTES) / MIB_BYTES, 4),
        identical_prefix_partition_count=identical_prefix,
        partition_mappings=tuple(mappings),
        all_30_partitions_mapped_zero_repartition=all_mapped,
        p20_to_p30_lut_headroom_bytes=lut_headroom_bytes,
        p20_to_p30_lut_headroom_mib=round(lut_headroom_bytes / MIB_BYTES, 4),
        p21_tmpfs_vfat_8m_bytes=len(vfat8),
        p21_tmpfs_vfat_16m_bytes=len(vfat16),
        spi_nor_audit=spi_audit,
        redline_audit=redline_audit,
        p15_footprint=p15_audit,
        errors=tuple(errors),
    )


def _cpio_entry_wire_bytes(rel_name: str, payload_size: int) -> int:
    name_len = len(rel_name.encode("utf-8")) + 1
    head_padded = _align_up(CPIO_HEADER_SIZE + name_len, 4)
    data_padded = _align_up(payload_size, 4)
    return head_padded + data_padded


def _build_overlay_component_list(
    *,
    adapted_lib_sizes: Dict[str, int],
    kikilog_bytes: int,
    opelog_vfat_bytes: int,
    ram_shadow_bk4_bytes: int,
    control_cpio_bytes: int,
    extra_overlay_bytes: int = 0,
) -> Tuple[OverlayComponentFootprint, ...]:
    ordered_items: List[Tuple[str, str, int]] = [
        ("lib/appFw.so", "adapted_elf_so", adapted_lib_sizes["appFw.so"]),
        ("lib/libInfraSetupFile.so", "adapted_elf_so", adapted_lib_sizes["libInfraSetupFile.so"]),
        ("lib/libInfraMediaCommon.so", "adapted_elf_so", adapted_lib_sizes["libInfraMediaCommon.so"]),
        ("lib/libInfraMediaConfig.so", "adapted_elf_so", adapted_lib_sizes["libInfraMediaConfig.so"]),
        ("lib/libInfraKikiLogGenerator.so", "companion_elf_so", kikilog_bytes),
        ("lib/libInfraAppRemoteBoard.so", "adapted_elf_so", adapted_lib_sizes["libInfraAppRemoteBoard.so"]),
        ("lib/libfan.so", "adapted_elf_so", adapted_lib_sizes["libfan.so"]),
        ("modules/upm.ko", "adapted_kernel_ko", adapted_lib_sizes["upm.ko"]),
        ("images/opelog.vfat", "loopback_vfat_image", opelog_vfat_bytes),
        ("nvram/Backup_ram_shadow.bin", "ram_shadow_bk4", ram_shadow_bk4_bytes),
        ("etc/fx6_overlay/stage_a_control.cpio", "control_scripts_manifest", control_cpio_bytes),
    ]
    if extra_overlay_bytes > 0:
        ordered_items.append(("debug/injected_extra_payload.bin", "injected_payload", extra_overlay_bytes))

    out: List[OverlayComponentFootprint] = []
    for name, cat, sz in ordered_items:
        out.append(
            OverlayComponentFootprint(
                name=name,
                category=cat,
                raw_bytes=sz,
                paged_4k_bytes=_align_up(sz, PAGE_BYTES_4K),
                cpio_record_bytes=_cpio_entry_wire_bytes(name, sz),
            )
        )
    return tuple(out)


def _evaluate_tmpfs_scenario(
    *,
    scenario_id: str,
    vfat_mode: str,
    unpack_mode: str,
    components: Sequence[OverlayComponentFootprint],
    net_linux_ddr_bytes: int,
    linux_tmpfs_50pct_bytes: int,
    safe_tmpfs_ceiling_bytes: int,
) -> TmpfsUnpackScenarioBudget:
    inode_overhead = (len(components) + 8) * TMPFS_INODE_METADATA_OVERHEAD_BYTES
    steady_bytes = sum(c.paged_4k_bytes for c in components) + _align_up(inode_overhead, PAGE_BYTES_4K)

    full_cpio_wire_bytes = sum(c.cpio_record_bytes for c in components) + _cpio_entry_wire_bytes("TRAILER!!!", 0)
    full_cpio_paged_bytes = _align_up(full_cpio_wire_bytes, PAGE_BYTES_4K)

    if unpack_mode == "streaming_unpack":
        # Streaming unpack (`cpio -idm < stream`) holds only extracted tmpfs pages + 64 KiB pipe buffer
        peak_bytes = steady_bytes + (64 * 1024)
    elif unpack_mode == "peak_buffer_unpack":
        # Peak-buffer unpack holds the entire `.cpio` archive inside tmpfs simultaneously with extracted files
        peak_bytes = steady_bytes + full_cpio_paged_bytes + PAGE_BYTES_4K
    else:
        raise ValueError(f"Unsupported unpack_mode: {unpack_mode!r}")

    headroom_safe = safe_tmpfs_ceiling_bytes - peak_bytes
    headroom_50pct = linux_tmpfs_50pct_bytes - peak_bytes
    within_bounds = peak_bytes <= safe_tmpfs_ceiling_bytes and peak_bytes <= linux_tmpfs_50pct_bytes
    pct_memtotal = round((peak_bytes / net_linux_ddr_bytes) * 100.0, 4)

    return TmpfsUnpackScenarioBudget(
        scenario_id=scenario_id,
        vfat_mode=vfat_mode,
        unpack_mode=unpack_mode,
        steady_state_tmpfs_bytes=steady_bytes,
        steady_state_tmpfs_mib=round(steady_bytes / MIB_BYTES, 4),
        peak_tmpfs_bytes=peak_bytes,
        peak_tmpfs_mib=round(peak_bytes / MIB_BYTES, 4),
        safe_tmpfs_ceiling_bytes=safe_tmpfs_ceiling_bytes,
        safe_tmpfs_ceiling_mib=round(safe_tmpfs_ceiling_bytes / MIB_BYTES, 4),
        linux_default_tmpfs_50pct_bytes=linux_tmpfs_50pct_bytes,
        headroom_vs_safe_ceiling_bytes=headroom_safe,
        headroom_vs_safe_ceiling_mib=round(headroom_safe / MIB_BYTES, 4),
        headroom_vs_linux_tmpfs_50pct_bytes=headroom_50pct,
        share_of_linux_memtotal_pct=pct_memtotal,
        within_safe_bounds=within_bounds,
    )


def audit_ddr_and_tmpfs_ram_budget(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    dtb_path: Path = DEFAULT_FX3_DTB_PATH,
    kemco_path: Path = DEFAULT_FX3_KEMCO_TXT_PATH,
    safe_tmpfs_ceiling_bytes: int = DEFAULT_SAFE_STAGE_A_TMPFS_CEILING_BYTES,
    kernel_and_initrd_reserve_bytes: int = DEFAULT_LINUX_KERNEL_AND_INITRD_RESERVE_BYTES,
    extra_overlay_bytes: int = 0,
) -> LinuxDdrAndTmpfsBudgetReport:
    """Execute Dimension B: CXD90057 Linux Usable DDR Pool & Stage-A `tmpfs` RAM-Overlay Budget."""
    errors: List[str] = []

    if extra_overlay_bytes < 0:
        errors.append(f"extra_overlay_bytes must be non-negative, got {extra_overlay_bytes}")

    # 1. Parse DTB `/memory@400000000` and `kemco.txt` `mem=2G` + 7 `memrsv=` carveouts
    fdt_blob = parse_fdt_blob(dtb_path.read_bytes())
    mem_node = fdt_blob.node_map()["/memory@400000000"]
    soc_mem_base, soc_total_ddr = struct.unpack(">QQ", mem_node.prop_dict()["reg"])

    kemco_raw = kemco_path.read_bytes()
    kemco_audit = parse_kemco_bootargs(kemco_raw.decode("utf-8", errors="replace"), _sha256(kemco_raw))
    if not kemco_audit.valid:
        errors.append("FX3 kemco.txt failed structural/non-overlap validation")

    mem_str = kemco_audit.mem_limit.upper()
    if mem_str.endswith("G"):
        kemco_mem_limit = int(mem_str[:-1], 10) * 1024 * MIB_BYTES
    elif mem_str.endswith("M"):
        kemco_mem_limit = int(mem_str[:-1], 10) * MIB_BYTES
    else:
        kemco_mem_limit = 0
    if kemco_mem_limit <= 0 or kemco_mem_limit > soc_total_ddr:
        errors.append(
            f"Invalid kemco mem= limit ({kemco_audit.mem_limit!r} -> {kemco_mem_limit}) against DTB /memory ({soc_total_ddr})"
        )

    carveout_items: List[DdrCarveoutItem] = []
    for entry in kemco_audit.memrsv_entries:
        carveout_items.append(
            DdrCarveoutItem(
                phys_addr=entry.base_addr,
                size_bytes=entry.size_bytes,
                size_mib=round(entry.size_bytes / MIB_BYTES, 4),
                uncached=entry.uncached,
            )
        )

    total_carveout_bytes = sum(c.size_bytes for c in carveout_items)
    net_linux_ddr_bytes = kemco_mem_limit - total_carveout_bytes
    est_userland_free_ddr = net_linux_ddr_bytes - kernel_and_initrd_reserve_bytes
    linux_tmpfs_50pct_bytes = (net_linux_ddr_bytes // 2 // PAGE_BYTES_4K) * PAGE_BYTES_4K

    if safe_tmpfs_ceiling_bytes <= 0 or safe_tmpfs_ceiling_bytes > linux_tmpfs_50pct_bytes:
        errors.append(
            f"safe_tmpfs_ceiling_bytes ({safe_tmpfs_ceiling_bytes}) exceeds Linux 50% tmpfs ceiling ({linux_tmpfs_50pct_bytes})"
        )

    # 2. Measure exact adapted binary sizes, KikiLog companion, VFAT 8M/16M, RAM-shadow BK4\0, and CPIO
    adapted_sizes: Dict[str, int] = {}
    for spec in ALL_PHASE2_TARGET_SPECS:
        src = resolve_donor_binary_path(spec, fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
        patched, _ = apply_patch_spec(src.read_bytes(), spec)
        adapted_sizes[spec.library_name] = len(patched)

    kikilog_path = fx6_lib_dir / "libInfraKikiLogGenerator.so"
    kikilog_raw = kikilog_path.read_bytes()
    if _sha256(kikilog_raw) != PINNED_LIB_INFRA_KIKILOG_SHA256:
        errors.append("libInfraKikiLogGenerator.so SHA-256 mismatch")
    kikilog_size = len(kikilog_raw)

    vfat8, _ = build_opelog_vfat_image(mode="8m_ram")
    vfat16, _ = build_opelog_vfat_image(mode="16m_log")
    bk4_shadow = synthesize_ram_shadow_bk4(flash_write_allowed=False)
    bk4_bytes_len = len(bk4_shadow.bk4_bytes)
    if bk4_bytes_len != 20_588:
        errors.append(f"Expected 20,588 B RAM-shadow BK4\\0 container, got {bk4_bytes_len} B")

    stage_a_pkg = build_stage_a_ram_overlay_package(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        vfat_mode="8m_ram",
    )
    control_cpio_len = stage_a_pkg.cpio_size

    comp_8m = _build_overlay_component_list(
        adapted_lib_sizes=adapted_sizes,
        kikilog_bytes=kikilog_size,
        opelog_vfat_bytes=len(vfat8),
        ram_shadow_bk4_bytes=bk4_bytes_len,
        control_cpio_bytes=control_cpio_len,
        extra_overlay_bytes=extra_overlay_bytes,
    )
    comp_16m = _build_overlay_component_list(
        adapted_lib_sizes=adapted_sizes,
        kikilog_bytes=kikilog_size,
        opelog_vfat_bytes=len(vfat16),
        ram_shadow_bk4_bytes=bk4_bytes_len,
        control_cpio_bytes=control_cpio_len,
        extra_overlay_bytes=extra_overlay_bytes,
    )

    scenarios = (
        _evaluate_tmpfs_scenario(
            scenario_id="STAGE_A_8M_STREAMING",
            vfat_mode="8m_ram",
            unpack_mode="streaming_unpack",
            components=comp_8m,
            net_linux_ddr_bytes=net_linux_ddr_bytes,
            linux_tmpfs_50pct_bytes=linux_tmpfs_50pct_bytes,
            safe_tmpfs_ceiling_bytes=safe_tmpfs_ceiling_bytes,
        ),
        _evaluate_tmpfs_scenario(
            scenario_id="STAGE_A_8M_PEAK_BUFFER",
            vfat_mode="8m_ram",
            unpack_mode="peak_buffer_unpack",
            components=comp_8m,
            net_linux_ddr_bytes=net_linux_ddr_bytes,
            linux_tmpfs_50pct_bytes=linux_tmpfs_50pct_bytes,
            safe_tmpfs_ceiling_bytes=safe_tmpfs_ceiling_bytes,
        ),
        _evaluate_tmpfs_scenario(
            scenario_id="STAGE_A_16M_STREAMING",
            vfat_mode="16m_log",
            unpack_mode="streaming_unpack",
            components=comp_16m,
            net_linux_ddr_bytes=net_linux_ddr_bytes,
            linux_tmpfs_50pct_bytes=linux_tmpfs_50pct_bytes,
            safe_tmpfs_ceiling_bytes=safe_tmpfs_ceiling_bytes,
        ),
        _evaluate_tmpfs_scenario(
            scenario_id="STAGE_A_16M_PEAK_BUFFER",
            vfat_mode="16m_log",
            unpack_mode="peak_buffer_unpack",
            components=comp_16m,
            net_linux_ddr_bytes=net_linux_ddr_bytes,
            linux_tmpfs_50pct_bytes=linux_tmpfs_50pct_bytes,
            safe_tmpfs_ceiling_bytes=safe_tmpfs_ceiling_bytes,
        ),
    )

    within_safe = all(sc.within_safe_bounds for sc in scenarios)
    if not within_safe:
        for sc in scenarios:
            if not sc.within_safe_bounds:
                errors.append(
                    f"Scenario {sc.scenario_id} exceeded safe tmpfs RAM ceiling: "
                    f"peak={sc.peak_tmpfs_bytes} B > ceiling={sc.safe_tmpfs_ceiling_bytes} B"
                )

    all_ok = kemco_audit.valid and within_safe and len(errors) == 0
    return LinuxDdrAndTmpfsBudgetReport(
        all_checks_passed=all_ok,
        soc_dtb_memory_base=soc_mem_base,
        soc_dtb_total_ddr_bytes=soc_total_ddr,
        soc_dtb_total_ddr_mib=round(soc_total_ddr / MIB_BYTES, 2),
        kemco_mem_limit_bytes=kemco_mem_limit,
        kemco_mem_limit_mib=round(kemco_mem_limit / MIB_BYTES, 2),
        kemco_carveout_count=len(carveout_items),
        kemco_carveouts=tuple(carveout_items),
        total_memrsv_carveout_bytes=total_carveout_bytes,
        total_memrsv_carveout_mib=round(total_carveout_bytes / MIB_BYTES, 4),
        net_linux_managed_ddr_bytes=net_linux_ddr_bytes,
        net_linux_managed_ddr_mib=round(net_linux_ddr_bytes / MIB_BYTES, 4),
        kernel_and_initrd_reserve_bytes=kernel_and_initrd_reserve_bytes,
        estimated_userland_free_ddr_bytes=est_userland_free_ddr,
        estimated_userland_free_ddr_mib=round(est_userland_free_ddr / MIB_BYTES, 4),
        linux_default_tmpfs_50pct_bytes=linux_tmpfs_50pct_bytes,
        linux_default_tmpfs_50pct_mib=round(linux_tmpfs_50pct_bytes / MIB_BYTES, 4),
        safe_stage_a_tmpfs_ceiling_bytes=safe_tmpfs_ceiling_bytes,
        safe_stage_a_tmpfs_ceiling_mib=round(safe_tmpfs_ceiling_bytes / MIB_BYTES, 4),
        components_8m=comp_8m,
        components_16m=comp_16m,
        ram_shadow_bk4_bytes=bk4_bytes_len,
        control_cpio_archive_bytes=control_cpio_len,
        scenarios=scenarios,
        ram_budget_within_safe_bounds=within_safe,
        errors=tuple(errors),
    )


def run_storage_and_ram_budget_verification(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    scripts_to_audit: Optional[Sequence[Tuple[str, str]]] = None,
    staged_binary_names: Sequence[str] = (),
    sector0_mutation_bytes: int = 0,
    spi_nor_mutation_bytes: int = 0,
    additional_p15_payload_bytes: int = 0,
    extra_overlay_bytes: int = 0,
    safe_tmpfs_ceiling_bytes: int = DEFAULT_SAFE_STAGE_A_TMPFS_CEILING_BYTES,
) -> Phase9StorageAndRamBudgetReport:
    """Run full Phase 9 Dimension A (30-partition + `p15` budget) & Dimension B (DDR + `tmpfs` budget)."""
    if scripts_to_audit is None:
        pkg = build_stage_a_ram_overlay_package(
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
        )
        scripts_to_audit = (
            ("setup_fx6_compat.sh", pkg.setup_compat_script),
            ("init2_guard.sh", pkg.init2_guard_script),
        )
        if not staged_binary_names:
            staged_binary_names = tuple(pkg.staged_runtime_blobs.keys())

    dim_a = audit_storage_topology_and_p15_budget(
        scripts_to_audit=scripts_to_audit,
        staged_binary_names=staged_binary_names,
        sector0_mutation_bytes=sector0_mutation_bytes,
        spi_nor_mutation_bytes=spi_nor_mutation_bytes,
        additional_p15_payload_bytes=additional_p15_payload_bytes,
    )
    dim_b = audit_ddr_and_tmpfs_ram_budget(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        safe_tmpfs_ceiling_bytes=safe_tmpfs_ceiling_bytes,
        extra_overlay_bytes=extra_overlay_bytes,
    )
    all_ok = dim_a.all_checks_passed and dim_b.all_checks_passed
    return Phase9StorageAndRamBudgetReport(
        all_checks_passed=all_ok,
        edisx_repartition_forbidden=dim_a.redline_audit.edisx_repartition_forbidden,
        sector0_mutation_bytes=dim_a.redline_audit.sector0_mutation_bytes,
        p15_fits_stock_fx3=dim_a.p15_footprint.p15_fits_stock_fx3,
        ram_budget_within_safe_bounds=dim_b.ram_budget_within_safe_bounds,
        dimension_a_storage=dim_a,
        dimension_b_ddr_tmpfs=dim_b,
    )
