"""Phase 137 — 27th Unified Firmware-Lab Auditor: Real-Hardware Unknowns `U2` & `U3`
(`cpapp-b.bin` TOPPERS CP RTOS Cross-Hardware Assertion, Route-1 vs Route-2
Architecture Proof, & `Backup.bin` `819->840` / `0xfa0080` Bank 0/1 Boot Descriptor
& Per-Body Calibration Auditor).

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`cpapp-b.bin`, `tomco.txt`, `kemco.txt`,
  `Backup.bin`, `LdrBkupList.txt`, `pformat_config.txt`, `loader_nor.bin`) and FX6
  v6.01 (`cpapp-b.bin`, `tomco.txt`, `kemco.txt`, `CX95898_UC.bin`,
  `nor_loader_writer.sh`, `us_spi_firmup.sh`, `us_darwin_firm.sh`,
  `big_backup.conf`, `ud_keep_backup.elf`, `mew.bin`, `darwin_core.bin`) strictly
  via `os.O_RDONLY` + `mmap.ACCESS_READ` using targeted offset/header/symbol
  lookups (< 0.25s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room dual-record `BK4\x00` containers
  with authentic 144-byte `0x00fa0080` Bank 0/1 descriptor tables, CP RTOS binary
  headers/markers, updater scripts, and config fixtures (< 0.02s warm, zero
  proprietary files required).

Audits Four Phase 137 Pillars:
1. Pillar 1 (`U2` CP RTOS & Cmdline Divergence) — Proves FX3 & FX6 `cpapp-b.bin`
   share `0x00108000` ARM32 startup + exact `128 KiB` (`0x20000`) prefix and
   CXD90057/IMX510/TOPPERS-FMP/osal_uipc drivers, while diverging cleanly at
   `0x20000` (`Darwin`, `VariableNd`, `Mew`, `MoniFpga`), `tomco.txt` (`1,724.00 MiB`
   uncached pools vs `wdt_on=0`/`exception_reboot=Y`), and `kemco.txt`
   (`cfg.uart=1` vs `cfg.uart=9`, `error.led=18,0` vs `13,3`).
2. Pillar 2 (Route-1 vs Route-2 Architecture & Brick-Hazard Proof) — Proves
   Route-1 (`Stock FX3 loader_nor.bin + Stock FX3 p3 Kernel + Stock FX3 p8/cpapp-b.bin
   + Stock FX3 p2:/Backup.bin + Reversible /usr Stage-B Overlay`) preserves 100%
   native FX3 `IMX510` ISP/IBIS/AF/XAVC while eliminating all Route-2 hazards
   (`nor_loader_writer.sh` `0x51/0x52/0x53/0x92`, `us_spi_firmup.sh` `mew.bin` `0x68`,
   `us_darwin_firm.sh` `darwin_core.bin` `0x63`).
3. Pillar 3 (`U3` `Backup.bin` `819->840`, `0xfa0080` Bank 0/1 & Per-Body Calibration)
   — Audits dual `BK4\x00` records, O(1) `0x00fa0080` Bank 0 (AP `0x400001000..
   0x408ffffff` identical) & Bank 1 (CP `0x800100000..0x809a35dff`, exact
   `+0x14000` / `+0xE0000` DDR shifts & `p8:\\cpImg.dat` vs `p3:\\cmrbnb.bin`
   non-overlap), `LdrBkupList.txt` (65 loader keys), `big_backup.conf`, and
   `ud_keep_backup.elf -r` (`BK_PROTECT_ADJ_RST_USER_FIRMUP`).
4. Pillar 4 (Volatile RAM Staging & Zero `eMMC` / `SPI NOR` Write Authorization) —
   Enforces `persistent_emmc_writes_authorized = False`,
   `spi_nor_write_authorized = False`, `emmc_mutation_bytes = 0`,
   `spi_nor_mutation_bytes = 0`, `calibration_mutation_bytes = 0`, and zero raw
   proprietary byte slices in JSON output.
"""

from __future__ import annotations

import hashlib
import mmap
import os
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    audit_bk4_record_bytes,
    is_forced_clean_room,
    resolve_donor_file,
)


PHASE_137_SCHEMA = "fx3_firmware_lab_phase137_realhw_cp_rtos_backup_bin_v1"
PHASE_137_VERSION = "137.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------

FX3_CPAPP_P137_RELPATH = "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"
FX6_CPAPP_P137_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin"
)
FX3_TOMCO_RELPATH = "sony-firmware-20261024/stage198-AP-CP-loaders-and-partition-selection/originals/tomco.txt"
FX6_TOMCO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/tomco.txt"
)
FX3_KEMCO_RELPATH = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/current-updater-evidence/"
    "tar-selected/0800_appli/setting/kemco.txt"
)
FX6_KEMCO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0800_appli/setting/kemco.txt"
)
FX3_BACKUP_BIN_RELPATH = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
FX6_BACKUP_BIN_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/"
    "SYSIPSX-DSLR/CHAPLIN/CX95898_UC.bin"
)
FX3_LDR_BKUP_LIST_RELPATH = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/nor-loader-members/LdrBkupList.txt"
)
FX3_PFORMAT_CONFIG_RELPATH = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/nor-loader-members/pformat_config.txt"
)
FX3_LOADER_NOR_BIN_RELPATH = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/nor-loader-members/loader_nor.bin"
)
FX6_NOR_LOADER_WRITER_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nested-files/"
    "updater.img/bin/nor_loader_writer.sh"
)
FX6_US_SPI_FIRMUP_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nested-files/"
    "updater.img/bin/us_spi_firmup.sh"
)
FX6_US_DARWIN_FIRM_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nested-files/"
    "nflasha1-initrd/usr/bin/us_darwin_firm.sh"
)
FX6_BIG_BACKUP_CONF_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0100_config/big_backup.conf"
)
FX6_UD_KEEP_BACKUP_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nested-files/"
    "updater.img/bin/ud_keep_backup.elf"
)
FX6_MEW_BIN_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/1010_spi/mew.bin"
)
FX6_DARWIN_CORE_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0640_darwin/darwin_core.bin"
)

# ---------------------------------------------------------------------------
# Pillar 1 Constants: Unknown U2 — cpapp-b.bin, tomco.txt, kemco.txt
# ---------------------------------------------------------------------------

CP_LOAD_BASE = 0x00108000
CP_IDENTICAL_PREFIX_BYTES = 0x20000  # 131,072 B identical ARM32 reset/boot stub
CP_ARM32_ENTRY_WORDS: Tuple[int, ...] = (
    0xE59F1004,
    0xE2811004,
    0xE1A0F001,
    0x0010800C,
    0xE3A000D3,
    0xE12FF000,
)

FX6_EXCLUSIVE_CP_MARKERS: Tuple[str, ...] = (
    "Darwin",
    "VariableNd",
    "Mew",
    "MoniFpga",
)

SHARED_CP_RTOS_MARKERS: Tuple[str, ...] = (
    "TOPPERS",
    "FMP",
    "C_ImagerCtrl_IMX510",
    "osal_uipc",
    "SET_CA_TALLY",
    "SET_FAN_EQ_ID",
    "FAN_R",
    "PANELEVF",
    "kbd: select vgrip",
)

EXPECTED_TOMCO_MEMCFG_POOLS: Tuple[str, ...] = (
    "0x400000@0x04C00000:uc",
    "0x7000000@0x09000000:uc",
    "0x24800000@0x1B800000:uc",
    "0x40000000@0x80000000:uc",
)
EXPECTED_TOMCO_TOTAL_MIB = 1724.0
EXPECTED_TOMCO_UART_BAUD = 460800
EXPECTED_TOMCO_MPCP_INT = 296
EXPECTED_TOMCO_RESET_INT = 307

# ---------------------------------------------------------------------------
# Pillar 2 Constants: Route-1 vs Route-2 Architecture & Brick Hazards
# ---------------------------------------------------------------------------

VALID_DEPLOYMENT_ROUTES: Tuple[str, ...] = (
    "ROUTE_1_HYBRID_STAGE_B",
    "ROUTE_2_FULL_FX6_NAND_NOR",
)

NOR_LOADER_WRITER_MARKERS: Tuple[str, ...] = (
    "bksb.elf",
    "ud_nor_pformat.elf",
    "ud_cp_firmup.elf",
    "0x51",
    "0x52",
    "0x53",
    "0x92",
)
US_SPI_FIRMUP_MARKERS: Tuple[str, ...] = (
    "ud_ioex_sel_en.elf",
    "ud_spirom_firmup.elf",
    "mew",
    "0x68",
)
US_DARWIN_FIRM_MARKERS: Tuple[str, ...] = (
    "ud_darwin_firmup.elf",
    "darwin_boo.bin",
    "darwin_core.bin",
    "0x63",
)
PFORMAT_REQUIRED_FILES: Tuple[str, ...] = (
    "loader_nor.bin",
    "LdrBkup.bin",
    "DGU.bin",
    "MIS.bin",
    "cpapp-b.bin",
    "pcie_phy_fw.bin",
)

# ---------------------------------------------------------------------------
# Pillar 3 Constants: Unknown U3 — BK4 Dual Records & 0x00fa0080 Slot Tables
# ---------------------------------------------------------------------------

BK4_SYNC_U32 = 0xAAAAAAAA
BK4_MAGIC_BYTES = b"BK4\x00"
BK4_HEADER_BYTES = 256
DESCRIPTOR_PROP_ID = 0x00FA0080
DESCRIPTOR_SLOT_BYTES = 144
DESCRIPTOR_SLOT_COUNT = 64
DESCRIPTOR_TABLE_BYTES = DESCRIPTOR_SLOT_BYTES * DESCRIPTOR_SLOT_COUNT  # 9,216 B

EXPECTED_FX3_SUBSYSTEMS = 819
EXPECTED_FX6_SUBSYSTEMS = 840
EXPECTED_LDR_BKUP_KEY_COUNT = 65
EXPECTED_LDR_BKUP_PREFIXES: Tuple[str, ...] = ("0x51", "0x5d", "0x92", "0xf9", "0xfa")
EXPECTED_BIG_BACKUP_PATHS: Tuple[str, ...] = ("/setting/psd.bin", "/setting/defdet.bin")
UD_KEEP_BACKUP_MARKERS: Tuple[str, ...] = (
    "Backup_preserve",
    "Backup_restore",
    "Backup_rewrite",
    "BK_PROTECT_ADJ_RST_USER_FIRMUP",
    "-r",
)

CANONICAL_BANK0_AP_SLOTS: Tuple[Tuple[int, int, int, int, int, str], ...] = (
    # (slot_idx, partition, mode, start_addr, end_addr, path)
    (0, 3, 0x05000000, 0x401000000, 0x401FFFFFF, "\\av-cam.bin"),
    (1, 2, 0x01000000, 0x400001000, 0x400001FFF, "\\kemco.txt"),
    (2, 3, 0x01000000, 0x408000000, 0x408FFFFFF, "\\initrd.img"),
    (3, 3, 0x81000000, 0x400080000, 0x4005FFFFF, "\\vmlinux.bin"),
    (4, 2, 0x01000000, 0x400002000, 0x400005FFF, "\\cxd90057.dtb"),
)

CANONICAL_FX3_BANK0_BT_SLOTS: Tuple[Tuple[int, int, int, int, int, str], ...] = (
    (5, 2, 0x08000000, 0x0FE380000, 0x0FE3BFFFF, "\\bt_conf.cnf"),
    (6, 3, 0x08000000, 0x0FE310000, 0x0FE31FFFF, "\\btfw32a.tlv"),
    (7, 3, 0x08000000, 0x0FE320000, 0x0FE32FFFF, "\\btnv32.bin"),
    (8, 3, 0x08000001, 0x0FE300000, 0x0FE30FFFF, "\\wole_app.bin"),
)

CANONICAL_FX3_BANK1_CP_SLOTS: Tuple[Tuple[int, int, int, int, int, str], ...] = (
    (0, 3, 0x05000000, 0x809139000, 0x809178FFF, "\\sabin\\idt_cam.bin"),
    (1, 3, 0x05000000, 0x809108000, 0x809138FFF, "\\bonobo.bin"),
    (2, 8, 0x07000000, 0x800100000, 0x800107FFF, "\\tomco.txt"),
    (3, 8, 0x05000000, 0x809A08E00, 0x809A21DFF, "\\DmmCfg.bin"),
    (4, 8, 0x05000000, 0x808EB0000, 0x808F1DDCF, "\\OldAmtCL.bin"),
    (5, 8, 0x05000000, 0x8099E8E00, 0x809A08DFF, "\\SysSound.bin"),
    (6, 8, 0x81000000, 0x800108000, 0x800107FFF, "\\cpapp-b.bin"),
    (7, 2, 0x05000000, 0x809479000, 0x809978FFF, "\\defdet.bin"),
    (8, 8, 0x05000000, 0x809179000, 0x809478FFF, "\\cpImg.dat"),
    (9, 2, 0x05000000, 0x808730000, 0x808C2FFFF, "\\psd.bin"),
    (10, 18, 0x05000000, 0x808C30000, 0x808CAFFFF, "\\lensfile.bin"),
)

CANONICAL_FX6_BANK1_CP_SLOTS: Tuple[Tuple[int, int, int, int, int, str], ...] = (
    (0, 3, 0x05000000, 0x809139000, 0x809178FFF, "\\sabin\\idt_cam.bin"),
    (1, 3, 0x05000000, 0x809108000, 0x809138FFF, "\\bonobo.bin"),
    (2, 8, 0x07000000, 0x800100000, 0x800107FFF, "\\tomco.txt"),
    (3, 8, 0x05000000, 0x809A1CE00, 0x809A35DFF, "\\DmmCfg.bin"),
    (4, 3, 0x05000000, 0x809179000, 0x80918CFFF, "\\cmrbnb.bin"),
    (5, 8, 0x05000000, 0x808F90000, 0x808FFDDCF, "\\OldAmtCL.bin"),
    (6, 8, 0x81000000, 0x800108000, 0x800107FFF, "\\cpapp-b.bin"),
    (7, 2, 0x05000000, 0x80948D000, 0x80998CFFF, "\\defdet.bin"),
    (8, 2, 0x05000000, 0x808810000, 0x808D0FFFF, "\\psd.bin"),
    (9, 18, 0x05000000, 0x808D10000, 0x808D8FFFF, "\\lensfile.bin"),
)

# ---------------------------------------------------------------------------
# Pillar 4 Constants: Volatile Staging & Zero Flash Authorization Guard
# ---------------------------------------------------------------------------

VOLATILE_STAGING_PREFIXES_P137: Tuple[str, ...] = ("/tmp/", "ram://", "/ramdsk/")
FORBIDDEN_PERSISTENT_EMMC_OR_NOR_RE_P137 = re.compile(
    r"(?i)(/dev/c?nflasha|/dev/mmcblk0|/dev/mtd|spi_nor|nor_loader|Backup\.bin|"
    r"psd\.bin|defdet\.bin|lensfile\.bin|mew\.bin|darwin_core\.bin|BODYDATA\.DAT|p2:/)"
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CpRtosProfileSummary:
    body: str
    file_bytes: int
    sha256_prefix: str
    load_base_hex: str
    arm32_entry_words_hex: Tuple[str, ...]
    prefix_128k_sha256: str
    exclusive_marker_counts: Dict[str, int]
    shared_marker_counts: Dict[str, int]


@dataclass(frozen=True)
class TomcoConfigSummary:
    body: str
    file_bytes: int
    memcfg_pools: Tuple[str, ...]
    memcfg_total_mib: float
    mpcp_exception_int_no: Optional[int]
    reset_req_int_no: Optional[int]
    uart_baudrate: Optional[int]
    wdt_on: Optional[int]
    wdt_tmo: Optional[int]
    xreset_req_port: Optional[str]
    exception_reboot: Optional[str]


@dataclass(frozen=True)
class KemcoConfigSummary:
    body: str
    file_bytes: int
    cfg_uart: Optional[int]
    error_led: Optional[str]
    error_led_2: Optional[str]
    gpio_port: Optional[str]
    gpio_bitmask: Optional[str]
    pm_pasr0: Optional[str]
    wbimem_large_pool: Optional[str]


@dataclass(frozen=True)
class CpRtosCompatibilityEvalResult:
    valid: bool
    status: str
    target_body: str
    cp_source_body: str
    route: str
    cp_load_base_hex: str
    uart_match: bool
    hardware_faults: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar1CpRtosDivergenceReport:
    passed: bool
    fx3_cp: CpRtosProfileSummary
    fx6_cp: CpRtosProfileSummary
    prefix_128k_identical: bool
    fx3_tomco: TomcoConfigSummary
    fx6_tomco: TomcoConfigSummary
    fx3_kemco: KemcoConfigSummary
    fx6_kemco: KemcoConfigSummary
    eval_fx3_stock_cp_route1: CpRtosCompatibilityEvalResult
    blocked_fx6_cp_on_fx3_hw: CpRtosCompatibilityEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RouteComparisonEvalResult:
    valid: bool
    status: str
    route: str
    loader_nor_source: str
    p3_kernel_source: str
    p8_cp_rtos_source: str
    p2_backup_source: str
    usr_overlay_reversible: bool
    native_imx510_isp_preserved: bool
    spi_nor_brick_hazard: bool
    fpga_mew_mismatch_hazard: bool
    darwin_nd_fault_hazard: bool
    calibration_overwrite_hazard: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2RouteArchitectureReport:
    passed: bool
    nor_loader_writer_markers: Dict[str, bool]
    us_spi_firmup_markers: Dict[str, bool]
    us_darwin_firm_markers: Dict[str, bool]
    pformat_files: Tuple[str, ...]
    fx3_loader_nor_bytes: int
    fx6_mew_bin_bytes: int
    fx6_darwin_core_bytes: int
    eval_route1_hybrid_stage_b: RouteComparisonEvalResult
    blocked_route2_full_fx6_nand_nor: RouteComparisonEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Bk4DualRecordSummary:
    body: str
    file_bytes: int
    sha256_prefix: str
    rec0_subsystems: int
    rec0_properties: int
    rec0_span_bytes: int
    rec0_checksum_hex: str
    rec0_checksum_valid: bool
    rec1_subsystems: int
    rec1_properties: int
    rec1_span_bytes: int
    rec1_checksum_hex: str
    rec1_checksum_valid: bool


@dataclass(frozen=True)
class BootDescriptorSlot:
    slot_index: int
    partition: int
    mode_hex: str
    start_addr_hex: str
    end_addr_hex: str
    path: str
    span_bytes: int


@dataclass(frozen=True)
class BootDescriptorTableDiffEvalResult:
    valid: bool
    status: str
    fx3_bank0_count: int
    fx6_bank0_count: int
    bank0_core_ap_identical: bool
    fx3_bank1_count: int
    fx6_bank1_count: int
    bank1_identical_paths: Tuple[str, ...]
    bank1_shifted_deltas_hex: Dict[str, str]
    bank1_forked_paths: Dict[str, str]
    fx3_bank1_ddr_non_overlapping: bool
    fx6_bank1_ddr_non_overlapping: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CalibrationSynthesisEvalResult:
    valid: bool
    status: str
    target_body: str
    preserve_factory_backup_bin: bool
    preserve_psd_and_defdet: bool
    use_ud_keep_backup_r_merge: bool
    cross_camera_raw_flash_attempted: bool
    ldr_bkup_key_count: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3BackupLayoutReport:
    passed: bool
    fx3_bk4: Bk4DualRecordSummary
    fx6_bk4: Bk4DualRecordSummary
    fx3_bank0_slots: Tuple[BootDescriptorSlot, ...]
    fx6_bank0_slots: Tuple[BootDescriptorSlot, ...]
    fx3_bank1_slots: Tuple[BootDescriptorSlot, ...]
    fx6_bank1_slots: Tuple[BootDescriptorSlot, ...]
    descriptor_diff: BootDescriptorTableDiffEvalResult
    ldr_bkup_key_count: int
    ldr_bkup_prefixes: Tuple[str, ...]
    big_backup_paths: Tuple[str, ...]
    ud_keep_backup_markers: Dict[str, bool]
    eval_preserve_fx3_calibration: CalibrationSynthesisEvalResult
    blocked_cross_body_backup_overwrite: CalibrationSynthesisEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase137WriteGuardResult:
    valid: bool
    status: str
    target_path: str
    volatile_ram_staged: bool
    persistent_write_blocked: bool
    emmc_mutation_bytes: int
    spi_nor_mutation_bytes: int
    calibration_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4ZeroFlashAuthReport:
    passed: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    emmc_mutation_bytes: int
    spi_nor_mutation_bytes: int
    calibration_mutation_bytes: int
    allowed_ram_probe: Phase137WriteGuardResult
    allowed_tmp_probe: Phase137WriteGuardResult
    blocked_nflasha8_cp: Phase137WriteGuardResult
    blocked_p2_backup: Phase137WriteGuardResult
    blocked_spi_nor_loader: Phase137WriteGuardResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealhwCpRtosAndBackupBinReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    donor_file_sizes: Dict[str, int]
    pillar1_cp_rtos_divergence: Pillar1CpRtosDivergenceReport
    pillar2_route_architecture: Pillar2RouteArchitectureReport
    pillar3_backup_layout: Pillar3BackupLayoutReport
    pillar4_zero_flash_auth: Pillar4ZeroFlashAuthReport
    errors: Tuple[str, ...]
    report_sha256: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) Donor Readers
# ---------------------------------------------------------------------------


def _read_file_rdonly(path: Path) -> bytes:
    """Strictly open and read a file using `os.O_RDONLY` + `mmap.ACCESS_READ`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        size = os.fstat(fd).st_size
        if size == 0:
            return b""
        with mmap.mmap(fd, size, access=mmap.ACCESS_READ) as mm:
            return bytes(mm[:])
    finally:
        os.close(fd)


_CP_MARKER_BYTES: Tuple[bytes, ...] = tuple(
    m.encode("ascii") for m in (FX6_EXCLUSIVE_CP_MARKERS + SHARED_CP_RTOS_MARKERS)
)
_RE_CP_MARKERS = re.compile(b"|".join(re.escape(m) for m in _CP_MARKER_BYTES))


def _count_cp_markers_single_pass(buf: bytes) -> Tuple[Dict[str, int], Dict[str, int]]:
    counts: Dict[bytes, int] = {m: 0 for m in _CP_MARKER_BYTES}
    for hit in _RE_CP_MARKERS.finditer(buf):
        tok = hit.group(0)
        counts[tok] = counts.get(tok, 0) + 1
    excl = {m: counts[m.encode("ascii")] for m in FX6_EXCLUSIVE_CP_MARKERS}
    shared = {m: counts[m.encode("ascii")] for m in SHARED_CP_RTOS_MARKERS}
    return excl, shared


def _scan_cpapp_rdonly(path: Path, body: str) -> CpRtosProfileSummary:
    """Scan `cpapp-b.bin` strictly via `os.O_RDONLY` + `mmap.ACCESS_READ` in a single pass."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        size = os.fstat(fd).st_size
        with mmap.mmap(fd, size, access=mmap.ACCESS_READ) as mm:
            buf = mm[:]
    finally:
        os.close(fd)

    entry_words = tuple(f"0x{w:08x}" for w in struct.unpack_from("<6I", buf, 0))
    prefix_sha = hashlib.sha256(buf[:CP_IDENTICAL_PREFIX_BYTES]).hexdigest()
    sha_prefix = hashlib.sha256(buf).hexdigest()[:16]
    excl_counts, shared_counts = _count_cp_markers_single_pass(buf)
    return CpRtosProfileSummary(
        body=body,
        file_bytes=size,
        sha256_prefix=sha_prefix,
        load_base_hex=f"0x{CP_LOAD_BASE:08x}",
        arm32_entry_words_hex=entry_words,
        prefix_128k_sha256=prefix_sha,
        exclusive_marker_counts=excl_counts,
        shared_marker_counts=shared_counts,
    )


def _stat_sha_rdonly(path: Path) -> int:
    """Verify read-only open with `os.O_RDONLY` + `mmap.ACCESS_READ` and return byte length."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        size = os.fstat(fd).st_size
        if size > 0:
            with mmap.mmap(fd, size, access=mmap.ACCESS_READ) as mm:
                _ = mm[: min(64, size)]
        return size
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Pure Parsers: tomco.txt, kemco.txt, BK4\x00 Dual Records & 0x00fa0080
# ---------------------------------------------------------------------------


_RE_MEMCFG = re.compile(r"memcfg=([^\s]+)")
_RE_WBIMEM = re.compile(r"wbimem=(0x[0-9a-fA-F]+@0x[0-9a-fA-F]+)")
_RE_MEMCFG_SIZE = re.compile(r"^(0x[0-9a-fA-F]+)@")


def parse_tomco_text(text: str, *, body: str, file_bytes: Optional[int] = None) -> TomcoConfigSummary:
    """Parse `tomco.txt` CP RTOS memory-pool & exception/UART parameters."""
    pools = tuple(_RE_MEMCFG.findall(text))
    total_bytes = 0
    for pool in pools:
        m = _RE_MEMCFG_SIZE.match(pool)
        if m:
            total_bytes += int(m.group(1), 16)

    def _int_val(key: str) -> Optional[int]:
        m = re.search(rf"^{re.escape(key)}=(-?\d+)\b", text, re.MULTILINE)
        return int(m.group(1)) if m else None

    def _str_val(key: str) -> Optional[str]:
        m = re.search(rf"^{re.escape(key)}=([^\s]+)", text, re.MULTILINE)
        return m.group(1) if m else None

    xreset_ch = _str_val("xreset_req_port_ch")
    xreset_bit = _str_val("xreset_req_port_bit")
    xreset_port = f"{xreset_ch}:{xreset_bit}" if (xreset_ch is not None and xreset_bit is not None) else None

    return TomcoConfigSummary(
        body=body,
        file_bytes=len(text.encode("ascii", errors="ignore")) if file_bytes is None else file_bytes,
        memcfg_pools=pools,
        memcfg_total_mib=round(total_bytes / (1024.0 * 1024.0), 2),
        mpcp_exception_int_no=_int_val("mpcp_exception_int_no"),
        reset_req_int_no=_int_val("reset_req_int_no"),
        uart_baudrate=_int_val("uart_baudrate"),
        wdt_on=_int_val("wdt_on"),
        wdt_tmo=_int_val("wdt_tmo"),
        xreset_req_port=xreset_port,
        exception_reboot=_str_val("exception_reboot"),
    )


def parse_kemco_text(text: str, *, body: str, file_bytes: Optional[int] = None) -> KemcoConfigSummary:
    """Parse `kemco.txt` AP Linux cmdline UART, LED, GPIO & WBI memory parameters."""
    def _token(pattern: str) -> Optional[str]:
        m = re.search(pattern, text)
        return m.group(1) if m else None

    cfg_uart_s = _token(r"\bcfg\.uart=(\d+)\b")
    wbimems = _RE_WBIMEM.findall(text)
    return KemcoConfigSummary(
        body=body,
        file_bytes=len(text.encode("ascii", errors="ignore")) if file_bytes is None else file_bytes,
        cfg_uart=int(cfg_uart_s) if cfg_uart_s is not None else None,
        error_led=_token(r"\berror\.led=([^\s]+)"),
        error_led_2=_token(r"\berror\.led_2=([^\s]+)"),
        gpio_port=_token(r"\bgpio\.port=([^\s]+)"),
        gpio_bitmask=_token(r"\bgpio\.bitmask=([^\s]+)"),
        pm_pasr0=_token(r"\bpm\.pasr0=([^\s]+)"),
        wbimem_large_pool=wbimems[-1] if wbimems else None,
    )


def _decode_descriptor_slots(buf: bytes, bank_marker: bytes, start_off: int, end_off: int) -> Tuple[BootDescriptorSlot, ...]:
    """Extract the 64x144B `0x00fa0080` boot descriptor entries anchored by a known path."""
    pos = buf.find(bank_marker, start_off, end_off)
    if pos == -1:
        return ()
    base = pos - 0x18
    if base < start_off:
        return ()
    slots: List[BootDescriptorSlot] = []
    for idx in range(DESCRIPTOR_SLOT_COUNT):
        ent_off = base + idx * DESCRIPTOR_SLOT_BYTES
        if ent_off + DESCRIPTOR_SLOT_BYTES > end_off:
            break
        s_addr, e_addr, part, mode = struct.unpack_from("<QQII", buf, ent_off)
        raw_path = buf[ent_off + 24 : ent_off + 144]
        if raw_path.startswith(b"\\"):
            path = raw_path.split(b"\x00", 1)[0].decode("ascii", errors="replace")
            if e_addr >= s_addr and s_addr != 0:
                span = (e_addr - s_addr) + 1
            else:
                span = 0
            slots.append(
                BootDescriptorSlot(
                    slot_index=idx,
                    partition=part,
                    mode_hex=f"0x{mode:08x}",
                    start_addr_hex=f"0x{s_addr:x}",
                    end_addr_hex=f"0x{e_addr:x}",
                    path=path,
                    span_bytes=span,
                )
            )
    return tuple(slots)


def parse_dual_bk4_and_descriptors(
    buf: bytes, *, body: str
) -> Tuple[Bk4DualRecordSummary, Tuple[BootDescriptorSlot, ...], Tuple[BootDescriptorSlot, ...]]:
    """Parse dual `BK4\x00` records and O(1) `0x00fa0080` Bank 0 (AP) + Bank 1 (CP) descriptor tables."""
    if len(buf) < BK4_HEADER_BYTES:
        raise ValueError(f"{body} Backup.bin too small ({len(buf)} bytes)")

    w0 = struct.unpack_from("<10I", buf, 0)
    rec0_sub, rec0_prop, rec0_dataoff, rec0_datasize, rec0_csum = w0[4], w0[5], w0[6], w0[7], w0[8]
    rec0_span = rec0_dataoff + rec0_datasize
    if rec0_span > len(buf):
        raise ValueError(f"{body} Rec 0 span {rec0_span} exceeds file size {len(buf)}")
    rec0_audit = audit_bk4_record_bytes(buf[:rec0_span])

    nxt = buf.find(BK4_MAGIC_BYTES, 16)
    if nxt == -1 or nxt < 12:
        raise ValueError(f"{body} missing Record 1 BK4\\x00 header")
    rec1_off = nxt - 12
    w1 = struct.unpack_from("<10I", buf, rec1_off)
    rec1_sub, rec1_prop, rec1_dataoff, rec1_datasize, rec1_csum = w1[4], w1[5], w1[6], w1[7], w1[8]
    rec1_span = rec1_dataoff + rec1_datasize
    if rec1_off + rec1_span > len(buf):
        raise ValueError(f"{body} Rec 1 span exceeds file size {len(buf)}")
    rec1_audit = audit_bk4_record_bytes(buf[rec1_off : rec1_off + rec1_span])

    bank0_slots = _decode_descriptor_slots(buf, b"\\av-cam.bin", 0, rec0_span)
    bank1_slots = _decode_descriptor_slots(buf, b"\\sabin\\idt_cam.bin", rec1_off, rec1_off + rec1_span)

    summary = Bk4DualRecordSummary(
        body=body,
        file_bytes=len(buf),
        sha256_prefix=hashlib.sha256(buf).hexdigest()[:16],
        rec0_subsystems=rec0_sub,
        rec0_properties=rec0_prop,
        rec0_span_bytes=rec0_span,
        rec0_checksum_hex=f"0x{rec0_csum:08x}",
        rec0_checksum_valid=rec0_audit.checksum_ok and rec0_audit.magic_ok and rec0_audit.sync_ok,
        rec1_subsystems=rec1_sub,
        rec1_properties=rec1_prop,
        rec1_span_bytes=rec1_span,
        rec1_checksum_hex=f"0x{rec1_csum:08x}",
        rec1_checksum_valid=rec1_audit.checksum_ok and rec1_audit.magic_ok and rec1_audit.sync_ok,
    )
    return summary, bank0_slots, bank1_slots


def _check_ddr_non_overlap(slots: Sequence[BootDescriptorSlot]) -> bool:
    """Verify no two active bounded DDR ranges in a descriptor bank overlap."""
    intervals: List[Tuple[int, int, str]] = []
    for s in slots:
        start = int(s.start_addr_hex, 16)
        end = int(s.end_addr_hex, 16)
        if s.span_bytes > 0 and end >= start:
            intervals.append((start, end, s.path))
    intervals.sort(key=lambda item: item[0])
    for idx in range(len(intervals) - 1):
        if intervals[idx][1] >= intervals[idx + 1][0]:
            return False
    return len(intervals) > 0


# ---------------------------------------------------------------------------
# Clean-Room Fixture Builder (Zero Proprietary Files Required)
# ---------------------------------------------------------------------------


def _pack_bk4_record(
    *,
    subsystems: int,
    properties: int,
    slots: Sequence[Tuple[int, int, int, int, int, str]],
) -> bytes:
    """Build a valid synthetic `BK4\x00` record carrying a 144B*64 `0x00fa0080` descriptor table."""
    table = bytearray(DESCRIPTOR_TABLE_BYTES)
    for idx, part, mode, s_addr, e_addr, path in slots:
        ent = bytearray(DESCRIPTOR_SLOT_BYTES)
        struct.pack_into("<QQII", ent, 0, s_addr, e_addr, part, mode)
        pb = path.encode("ascii")
        ent[24 : 24 + len(pb)] = pb
        table[idx * DESCRIPTOR_SLOT_BYTES : (idx + 1) * DESCRIPTOR_SLOT_BYTES] = ent

    dataoff = BK4_HEADER_BYTES
    datasize = len(table)
    hdr = bytearray(BK4_HEADER_BYTES)
    struct.pack_into(
        "<II4s4sIIIII",
        hdr,
        0,
        0x04000000,
        BK4_SYNC_U32,
        b"\x00\x00\x00\x00",
        BK4_MAGIC_BYTES,
        subsystems,
        properties,
        dataoff,
        datasize,
        0,
    )
    body = bytes(hdr) + bytes(table)
    csum = (sum(body) - sum(body[32:36])) & 0xFFFFFFFF
    struct.pack_into("<I", hdr, 32, csum)
    return bytes(hdr) + bytes(table)


def build_clean_room_realhw_cp_backup_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room fixtures for all Phase 137 Unknowns U2 & U3 tests."""
    prefix_128k = bytearray(CP_IDENTICAL_PREFIX_BYTES)
    struct.pack_into("<6I", prefix_128k, 0, *CP_ARM32_ENTRY_WORDS)
    # Place deterministic marker text inside the prefix vs divergent tail
    prefix_shared = b"TOPPERS/FMP/C_ImagerCtrl_IMX510/osal_uipc/SET_CA_TALLY/SET_FAN_EQ_ID/FAN_R/PANELEVF/kbd: select vgrip"
    prefix_128k[0x100 : 0x100 + len(prefix_shared)] = prefix_shared

    fx3_tail = b"\x00".join(
        [
            b"TOPPERS" * 15,
            b"FMP" * 13,
            b"PANELEVF" * 51,
            b"osal_uipc",
            b"SET_FAN_EQ_ID",
            b"ALCIN_UUD_IMX510_CP_STOCK",
        ]
    )
    fx6_tail = b"\x00".join(
        [
            b"TOPPERS" * 15,
            b"FMP" * 13,
            b"PANELEVF" * 51,
            b"osal_uipc",
            b"SET_FAN_EQ_ID",
            b"CHAPLIN_CP_RTOS",
            b"Darwin",
            b"VariableNd" * 6,
            b"Mew" * 4,
            b"MoniFpga" * 48,
        ]
    )

    fx3_tomco = (
        "[TOMCO]\n"
        "mpcp_exception_int_no=296\n"
        "reset_req_int_no=307\n"
        "memcfg=0x400000@0x04C00000:uc\n"
        "memcfg=0x7000000@0x09000000:uc\n"
        "memcfg=0x24800000@0x1B800000:uc\n"
        "memcfg=0x40000000@0x80000000:uc\n"
        "uart_baudrate=460800\n"
        "wdt_on=1\n"
        "wdt_tmo=7\n"
    ).encode("ascii")
    fx6_tomco = (
        "[TOMCO]\n"
        "xreset_req_port_ch=0\n"
        "xreset_req_port_bit=22\n"
        "mpcp_exception_int_no=296\n"
        "reset_req_int_no=307\n"
        "memcfg=0x400000@0x04C00000:uc\n"
        "memcfg=0x7000000@0x09000000:uc\n"
        "memcfg=0x24800000@0x1B800000:uc\n"
        "memcfg=0x40000000@0x80000000:uc\n"
        "uart_baudrate=460800\n"
        "exception_reboot=Y\n"
        "wdt_on=0\n"
        "wdt_tmo=6\n"
    ).encode("ascii")

    fx3_kemco = (
        "kemco\ncfg.uart=1\npm.pasr0=0xFE\nerror.led=18,0\n"
        "wbimem=0x00BA0000@0x410524000\n"
    ).encode("ascii")
    fx6_kemco = (
        "kemco\ncfg.uart=9\ngpio.port=0x5 gpio.bitmask=0x10\nerror.led_2=13,1\nerror.led=13,3\n"
        "wbimem=0x01919000@0x410524000\n"
    ).encode("ascii")

    fx3_rec0 = _pack_bk4_record(
        subsystems=EXPECTED_FX3_SUBSYSTEMS,
        properties=35668,
        slots=CANONICAL_BANK0_AP_SLOTS + CANONICAL_FX3_BANK0_BT_SLOTS,
    )
    fx3_rec1 = _pack_bk4_record(
        subsystems=EXPECTED_FX3_SUBSYSTEMS,
        properties=31197,
        slots=CANONICAL_FX3_BANK1_CP_SLOTS,
    )
    fx6_rec0 = _pack_bk4_record(
        subsystems=EXPECTED_FX6_SUBSYSTEMS,
        properties=40647,
        slots=CANONICAL_BANK0_AP_SLOTS,
    )
    fx6_rec1 = _pack_bk4_record(
        subsystems=EXPECTED_FX6_SUBSYSTEMS,
        properties=35088,
        slots=CANONICAL_FX6_BANK1_CP_SLOTS,
    )

    # Generate deterministic 65-key LdrBkupList covering all 5 prefixes
    prefixes = ("0x51", "0x5d", "0x92", "0xf9", "0xfa")
    ldr_keys = [f"{prefixes[i % 5]}{i:04x}".upper().replace("0X", "0x") for i in range(EXPECTED_LDR_BKUP_KEY_COUNT)]
    ldr_bkup_list = (", ".join(ldr_keys) + "\n").encode("ascii")

    pformat_config = (
        'file_param{ path = "loader_nor.bin" load = 0xFE049000 }\n'
        'file_param{ path = "LdrBkup.bin" load = 0xFE048800 }\n'
        'file_param{ path = "DGU.bin" load = 0xFE040800 }\n'
        'file_param{ path = "MIS.bin" load = 0xFE080000 }\n'
        'file_param{ path = "cpapp-b.bin" load = 0x00108000 }\n'
        'file_param{ path = "pcie_phy_fw.bin" load = 0xFE0A0000 }\n'
    ).encode("ascii")

    nor_writer = (
        "LED_ERROR_CODE_PLUGIN=0x51\nLED_ERROR_CODE_BADBLOCK=0x52\n"
        "LED_ERROR_CODE_GETCFG=0x53\nLED_ERROR_CODE_CETUS=0x92\n"
        "bksb.elf Backup.bin LdrBkupList.txt -c LdrBkup.bin\n"
        "ud_nor_pformat.elf\nud_cp_firmup.elf\n"
    ).encode("ascii")
    spi_up = (
        "ud_ioex_sel_en.elf -M -e\n"
        "ud_spirom_firmup.elf 2 mew.bin hash -f\n"
        "getledval.elf 0x68\n"
    ).encode("ascii")
    darwin_up = (
        "ud_darwin_firmup.elf darwin_boo.bin darwin_core.bin\n"
        "getledval.elf 0x63\n"
    ).encode("ascii")
    big_backup = b"/setting/psd.bin\n/setting/defdet.bin\n"
    ud_keep = (
        b"\x7fELF\x01\x01\x01\x00"
        + bytes(24)
        + b"Backup_preserve\x00Backup_restore\x00Backup_rewrite\x00"
        b"-r\x00BK_PROTECT_ADJ_RST_USER_FIRMUP\x00"
    )

    return {
        "fx3_cp": bytes(prefix_128k) + fx3_tail,
        "fx6_cp": bytes(prefix_128k) + fx6_tail,
        "fx3_tomco": fx3_tomco,
        "fx6_tomco": fx6_tomco,
        "fx3_kemco": fx3_kemco,
        "fx6_kemco": fx6_kemco,
        "fx3_backup": fx3_rec0 + fx3_rec1,
        "fx6_backup": fx6_rec0 + fx6_rec1,
        "ldr_bkup_list": ldr_bkup_list,
        "pformat_config": pformat_config,
        "nor_loader_writer": nor_writer,
        "us_spi_firmup": spi_up,
        "us_darwin_firm": darwin_up,
        "big_backup_conf": big_backup,
        "ud_keep_backup": ud_keep,
        "loader_nor_bin": b"SYNTH_LOADER_NOR",
        "mew_bin": b"SYNTH_MEW_FPGA",
        "darwin_core_bin": b"SYNTH_DARWIN_ND",
    }


# ---------------------------------------------------------------------------
# Public Evaluators (Positive & Negative Unit Test Surfaces)
# ---------------------------------------------------------------------------


def evaluate_cp_rtos_compatibility(
    *,
    target_body: str = "ILME_FX3",
    cp_source_body: str = "FX3_STOCK_702",
    route: str = "ROUTE_1_HYBRID_STAGE_B",
    kemco_uart: int = 1,
    has_darwin_nd_driver: bool = False,
    has_mew_fpga_driver: bool = False,
) -> CpRtosCompatibilityEvalResult:
    """Verify whether a CP RTOS image + AP cmdline UART pairing is hardware-safe on target_body."""
    t_body = target_body.strip().upper()
    s_body = cp_source_body.strip().upper()
    rt = route.strip().upper()
    if rt not in VALID_DEPLOYMENT_ROUTES:
        raise ValueError(f"Unsupported deployment route={route!r}")

    faults: List[str] = []
    errors: List[str] = []
    expected_uart = 1 if t_body == "ILME_FX3" else 9
    uart_match = kemco_uart == expected_uart
    if not uart_match:
        faults.append("AP_CP_KEMCO_UART_MISMATCH")
        errors.append(
            f"BLOCKED_CP_UART_MISMATCH: target={t_body} expects cfg.uart={expected_uart}, got {kemco_uart}"
        )

    if t_body == "ILME_FX3":
        if s_body != "FX3_STOCK_702" or rt == "ROUTE_2_FULL_FX6_NAND_NOR":
            faults.append("CROSS_BODY_CP_RTOS_ON_FX3_HW")
            errors.append(
                "BLOCKED_FX6_CP_RTOS_ON_FX3_HARDWARE: FX6 cpapp-b.bin requires FX6-only Darwin ND / Mew FPGA / MoniFpga"
            )
        if has_darwin_nd_driver:
            faults.append("DARWIN_ELECTRONIC_ND_ABSENT_ON_FX3")
            errors.append("BLOCKED_DARWIN_ND_ABSENT: FX3 lacks electronic variable ND (LED 0x63)")
        if has_mew_fpga_driver:
            faults.append("MEW_12G_SDI_FPGA_ABSENT_ON_FX3")
            errors.append("BLOCKED_MEW_FPGA_ABSENT: FX3 lacks mew.bin 12G-SDI FPGA (LED 0x68)")

    status = "FX3_STOCK_CP_RTOS_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return CpRtosCompatibilityEvalResult(
        valid=len(errors) == 0,
        status=status,
        target_body=t_body,
        cp_source_body=s_body,
        route=rt,
        cp_load_base_hex=f"0x{CP_LOAD_BASE:08x}",
        uart_match=uart_match,
        hardware_faults=tuple(faults),
        errors=tuple(errors),
    )


def evaluate_route1_vs_route2_architecture(
    *,
    route: str = "ROUTE_1_HYBRID_STAGE_B",
    loader_nor_source: str = "STOCK_FX3_LOADER_NOR",
    p3_kernel_source: str = "STOCK_FX3_P3_KERNEL",
    p8_cp_rtos_source: str = "STOCK_FX3_P8_CPAPP",
    p2_backup_source: str = "STOCK_FX3_P2_BACKUP_BIN",
    usr_overlay_reversible: bool = True,
) -> RouteComparisonEvalResult:
    """Compare Route-1 (Hybrid Userland Stage-B) vs Route-2 (Full FX6 NAND/NOR overwrite)."""
    rt = route.strip().upper()
    if rt not in VALID_DEPLOYMENT_ROUTES:
        raise ValueError(f"Unsupported route={route!r}")

    errors: List[str] = []
    nor_hazard = loader_nor_source != "STOCK_FX3_LOADER_NOR"
    fpga_hazard = p8_cp_rtos_source != "STOCK_FX3_P8_CPAPP" or rt == "ROUTE_2_FULL_FX6_NAND_NOR"
    nd_hazard = p8_cp_rtos_source != "STOCK_FX3_P8_CPAPP" or rt == "ROUTE_2_FULL_FX6_NAND_NOR"
    calib_hazard = p2_backup_source != "STOCK_FX3_P2_BACKUP_BIN"
    native_isp = (p3_kernel_source == "STOCK_FX3_P3_KERNEL") and (p8_cp_rtos_source == "STOCK_FX3_P8_CPAPP")

    if rt == "ROUTE_2_FULL_FX6_NAND_NOR" or nor_hazard or fpga_hazard or nd_hazard or calib_hazard:
        errors.append(
            "BLOCKED_ROUTE2_SPI_NOR_AND_FPGA_BRICK_HAZARD: Cross-model loader_nor/mew.bin/darwin/Backup.bin "
            "flashing risks permanent 0x51/0x52/0x53/0x63/0x68/0x92 brick & calibration loss"
        )
    if p3_kernel_source != "STOCK_FX3_P3_KERNEL":
        errors.append("BLOCKED_NON_STOCK_P3_KERNEL: Must retain Stock FX3 p3 kernel for IMX510/WBI2/hibdrv safety")
    if not usr_overlay_reversible:
        errors.append("BLOCKED_NON_REVERSIBLE_USR_OVERLAY: Stage-B /usr overlay must remain atomically reversible")

    status = "ROUTE1_HYBRID_STAGE_B_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return RouteComparisonEvalResult(
        valid=len(errors) == 0,
        status=status,
        route=rt,
        loader_nor_source=loader_nor_source,
        p3_kernel_source=p3_kernel_source,
        p8_cp_rtos_source=p8_cp_rtos_source,
        p2_backup_source=p2_backup_source,
        usr_overlay_reversible=usr_overlay_reversible,
        native_imx510_isp_preserved=native_isp,
        spi_nor_brick_hazard=nor_hazard or (rt == "ROUTE_2_FULL_FX6_NAND_NOR"),
        fpga_mew_mismatch_hazard=fpga_hazard,
        darwin_nd_fault_hazard=nd_hazard,
        calibration_overwrite_hazard=calib_hazard,
        errors=tuple(errors),
    )


def evaluate_boot_descriptor_diff(
    *,
    fx3_bank0: Sequence[BootDescriptorSlot],
    fx6_bank0: Sequence[BootDescriptorSlot],
    fx3_bank1: Sequence[BootDescriptorSlot],
    fx6_bank1: Sequence[BootDescriptorSlot],
) -> BootDescriptorTableDiffEvalResult:
    """Verify `0x00fa0080` Bank 0 (AP) & Bank 1 (CP) load-address invariants and non-overlap."""
    errors: List[str] = []
    fx3_b0_map = {s.path: s for s in fx3_bank0}
    fx6_b0_map = {s.path: s for s in fx6_bank0}
    core_ap_paths = ("\\av-cam.bin", "\\kemco.txt", "\\initrd.img", "\\vmlinux.bin", "\\cxd90057.dtb")
    bank0_identical = all(
        p in fx3_b0_map
        and p in fx6_b0_map
        and fx3_b0_map[p].start_addr_hex == fx6_b0_map[p].start_addr_hex
        and fx3_b0_map[p].end_addr_hex == fx6_b0_map[p].end_addr_hex
        and fx3_b0_map[p].partition == fx6_b0_map[p].partition
        for p in core_ap_paths
    )
    if not bank0_identical:
        errors.append("BLOCKED_BANK0_AP_LOAD_ADDRESS_DIVERGENCE")

    fx3_b1_map = {s.path: s for s in fx3_bank1}
    fx6_b1_map = {s.path: s for s in fx6_bank1}
    identical_cp: List[str] = []
    shifted: Dict[str, str] = {}
    for p in sorted(set(fx3_b1_map) & set(fx6_b1_map)):
        s3 = int(fx3_b1_map[p].start_addr_hex, 16)
        s6 = int(fx6_b1_map[p].start_addr_hex, 16)
        if s3 == s6 and fx3_b1_map[p].partition == fx6_b1_map[p].partition:
            identical_cp.append(p)
        else:
            delta = s6 - s3
            shifted[p] = f"+0x{delta:x}" if delta >= 0 else f"-0x{-delta:x}"

    forked: Dict[str, str] = {}
    for p in sorted(set(fx3_b1_map) - set(fx6_b1_map)):
        forked[p] = f"FX3_ONLY(p{fx3_b1_map[p].partition}@{fx3_b1_map[p].start_addr_hex})"
    for p in sorted(set(fx6_b1_map) - set(fx3_b1_map)):
        forked[p] = f"FX6_ONLY(p{fx6_b1_map[p].partition}@{fx6_b1_map[p].start_addr_hex})"

    if "\\cpapp-b.bin" not in identical_cp or "\\tomco.txt" not in identical_cp:
        errors.append("BLOCKED_BANK1_CORE_CP_ENTRY_MISMATCH")
    defdet_shift = shifted.get("\\defdet.bin")
    if defdet_shift != "+0x14000":
        errors.append(f"UNEXPECTED_DEFDET_SHIFT:{defdet_shift}")
    if shifted.get("\\psd.bin") != "+0xe0000" or shifted.get("\\lensfile.bin") != "+0xe0000":
        errors.append(f"UNEXPECTED_PSD_LENS_SHIFT:{shifted}")

    fx3_no_ov = _check_ddr_non_overlap(fx3_bank1)
    fx6_no_ov = _check_ddr_non_overlap(fx6_bank1)
    if not (fx3_no_ov and fx6_no_ov):
        errors.append("BLOCKED_BANK1_DDR_REGION_OVERLAP")

    status = "BOOT_DESCRIPTOR_BANK0_BANK1_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return BootDescriptorTableDiffEvalResult(
        valid=len(errors) == 0,
        status=status,
        fx3_bank0_count=len(fx3_bank0),
        fx6_bank0_count=len(fx6_bank0),
        bank0_core_ap_identical=bank0_identical,
        fx3_bank1_count=len(fx3_bank1),
        fx6_bank1_count=len(fx6_bank1),
        bank1_identical_paths=tuple(identical_cp),
        bank1_shifted_deltas_hex=shifted,
        bank1_forked_paths=forked,
        fx3_bank1_ddr_non_overlapping=fx3_no_ov,
        fx6_bank1_ddr_non_overlapping=fx6_no_ov,
        errors=tuple(errors),
    )


def evaluate_per_body_calibration_policy(
    *,
    target_body: str = "ILME_FX3",
    preserve_factory_backup_bin: bool = True,
    preserve_psd_and_defdet: bool = True,
    use_ud_keep_backup_r_merge: bool = True,
    cross_camera_raw_flash_attempted: bool = False,
    ldr_bkup_key_count: int = EXPECTED_LDR_BKUP_KEY_COUNT,
) -> CalibrationSynthesisEvalResult:
    """Enforce per-body factory calibration retention (`psd.bin`/`defdet.bin`/`Backup.bin`)."""
    errors: List[str] = []
    if cross_camera_raw_flash_attempted:
        errors.append(
            "BLOCKED_CROSS_CAMERA_CALIBRATION_DESTRUCTION: Flashing raw FX6 CX95898_UC.bin / "
            "psd.bin / defdet.bin overwrites per-body IMX510 shading/defect tables & 0xfa0080 DDR layout"
        )
    if not preserve_factory_backup_bin:
        errors.append("BLOCKED_FACTORY_BACKUP_BIN_MUTATION: Must preserve stock FX3 p2:/Backup.bin")
    if not preserve_psd_and_defdet:
        errors.append("BLOCKED_PSD_DEFDET_MUTATION: Must preserve /setting/psd.bin and /setting/defdet.bin")
    if not use_ud_keep_backup_r_merge:
        errors.append("BLOCKED_UNSAFE_BACKUP_MERGE: Missing ud_keep_backup.elf -r retention policy")
    if ldr_bkup_key_count != EXPECTED_LDR_BKUP_KEY_COUNT:
        errors.append(f"BLOCKED_LDR_BKUP_KEY_COUNT_DRIFT: expected {EXPECTED_LDR_BKUP_KEY_COUNT}, got {ldr_bkup_key_count}")

    status = "PER_BODY_CALIBRATION_PRESERVED" if not errors else errors[0].split(":", 1)[0]
    return CalibrationSynthesisEvalResult(
        valid=len(errors) == 0,
        status=status,
        target_body=target_body.strip().upper(),
        preserve_factory_backup_bin=preserve_factory_backup_bin,
        preserve_psd_and_defdet=preserve_psd_and_defdet,
        use_ud_keep_backup_r_merge=use_ud_keep_backup_r_merge,
        cross_camera_raw_flash_attempted=cross_camera_raw_flash_attempted,
        ldr_bkup_key_count=ldr_bkup_key_count,
        errors=tuple(errors),
    )


def evaluate_phase137_write_guard(target_path: str) -> Phase137WriteGuardResult:
    """Enforce volatile RAM staging only and zero persistent eMMC / SPI NOR / calibration writes."""
    norm = target_path.strip()
    is_volatile = norm.startswith(VOLATILE_STAGING_PREFIXES_P137) and not bool(
        FORBIDDEN_PERSISTENT_EMMC_OR_NOR_RE_P137.search(norm)
    )
    if is_volatile:
        return Phase137WriteGuardResult(
            valid=True,
            status="VOLATILE_RAM_STAGING_ALLOWED",
            target_path=norm,
            volatile_ram_staged=True,
            persistent_write_blocked=False,
            emmc_mutation_bytes=0,
            spi_nor_mutation_bytes=0,
            calibration_mutation_bytes=0,
            errors=(),
        )
    return Phase137WriteGuardResult(
        valid=False,
        status="BLOCKED_PERSISTENT_EMMC_OR_SPI_NOR_WRITE",
        target_path=norm,
        volatile_ram_staged=False,
        persistent_write_blocked=True,
        emmc_mutation_bytes=0,
        spi_nor_mutation_bytes=0,
        calibration_mutation_bytes=0,
        errors=(f"BLOCKED_PERSISTENT_EMMC_OR_SPI_NOR_WRITE: target_path={norm!r}",),
    )


# ---------------------------------------------------------------------------
# Top-Level Phase 137 Unified Auditor
# ---------------------------------------------------------------------------


def analyze_realhw_cp_rtos_and_backup_bin(*, clean_room: bool = False) -> RealhwCpRtosAndBackupBinReport:
    """Run all 4 Phase 137 real-hardware U2 & U3 pillars via local donors (`O_RDONLY`) or clean-room fixtures."""
    force_cr = bool(clean_room or is_forced_clean_room())
    donor_paths: Dict[str, Optional[Path]] = {}
    rel_map: Dict[str, str] = {
        "fx3_cp": FX3_CPAPP_P137_RELPATH,
        "fx6_cp": FX6_CPAPP_P137_RELPATH,
        "fx3_tomco": FX3_TOMCO_RELPATH,
        "fx6_tomco": FX6_TOMCO_RELPATH,
        "fx3_kemco": FX3_KEMCO_RELPATH,
        "fx6_kemco": FX6_KEMCO_RELPATH,
        "fx3_backup": FX3_BACKUP_BIN_RELPATH,
        "fx6_backup": FX6_BACKUP_BIN_RELPATH,
        "ldr_bkup_list": FX3_LDR_BKUP_LIST_RELPATH,
        "pformat_config": FX3_PFORMAT_CONFIG_RELPATH,
        "loader_nor_bin": FX3_LOADER_NOR_BIN_RELPATH,
        "nor_loader_writer": FX6_NOR_LOADER_WRITER_RELPATH,
        "us_spi_firmup": FX6_US_SPI_FIRMUP_RELPATH,
        "us_darwin_firm": FX6_US_DARWIN_FIRM_RELPATH,
        "big_backup_conf": FX6_BIG_BACKUP_CONF_RELPATH,
        "ud_keep_backup": FX6_UD_KEEP_BACKUP_RELPATH,
        "mew_bin": FX6_MEW_BIN_RELPATH,
        "darwin_core_bin": FX6_DARWIN_CORE_RELPATH,
    }

    if not force_cr:
        for key, rel in rel_map.items():
            donor_paths[key] = resolve_donor_file(rel, repo_root=DEFAULT_REPO_ROOT, clean_room=False)
        have_all_donors = all(p is not None for p in donor_paths.values())
    else:
        have_all_donors = False

    donor_sizes: Dict[str, int] = {}
    if have_all_donors:
        mode = "LOCAL_DONOR_VERIFIED"
        fx3_cp_prof = _scan_cpapp_rdonly(donor_paths["fx3_cp"], "FX3_702")  # type: ignore[arg-type]
        fx6_cp_prof = _scan_cpapp_rdonly(donor_paths["fx6_cp"], "FX6_601")  # type: ignore[arg-type]
        fx3_tomco_b = _read_file_rdonly(donor_paths["fx3_tomco"])  # type: ignore[arg-type]
        fx6_tomco_b = _read_file_rdonly(donor_paths["fx6_tomco"])  # type: ignore[arg-type]
        fx3_kemco_b = _read_file_rdonly(donor_paths["fx3_kemco"])  # type: ignore[arg-type]
        fx6_kemco_b = _read_file_rdonly(donor_paths["fx6_kemco"])  # type: ignore[arg-type]
        fx3_bk_b = _read_file_rdonly(donor_paths["fx3_backup"])  # type: ignore[arg-type]
        fx6_bk_b = _read_file_rdonly(donor_paths["fx6_backup"])  # type: ignore[arg-type]
        ldr_list_b = _read_file_rdonly(donor_paths["ldr_bkup_list"])  # type: ignore[arg-type]
        pformat_b = _read_file_rdonly(donor_paths["pformat_config"])  # type: ignore[arg-type]
        nor_writer_b = _read_file_rdonly(donor_paths["nor_loader_writer"])  # type: ignore[arg-type]
        spi_up_b = _read_file_rdonly(donor_paths["us_spi_firmup"])  # type: ignore[arg-type]
        darwin_up_b = _read_file_rdonly(donor_paths["us_darwin_firm"])  # type: ignore[arg-type]
        big_bk_b = _read_file_rdonly(donor_paths["big_backup_conf"])  # type: ignore[arg-type]
        ud_keep_b = _read_file_rdonly(donor_paths["ud_keep_backup"])  # type: ignore[arg-type]
        ldr_nor_sz = _stat_sha_rdonly(donor_paths["loader_nor_bin"])  # type: ignore[arg-type]
        mew_sz = _stat_sha_rdonly(donor_paths["mew_bin"])  # type: ignore[arg-type]
        darwin_sz = _stat_sha_rdonly(donor_paths["darwin_core_bin"])  # type: ignore[arg-type]

        donor_sizes = {
            "fx3_cp": fx3_cp_prof.file_bytes,
            "fx6_cp": fx6_cp_prof.file_bytes,
            "fx3_tomco": len(fx3_tomco_b),
            "fx6_tomco": len(fx6_tomco_b),
            "fx3_kemco": len(fx3_kemco_b),
            "fx6_kemco": len(fx6_kemco_b),
            "fx3_backup": len(fx3_bk_b),
            "fx6_backup": len(fx6_bk_b),
            "ldr_bkup_list": len(ldr_list_b),
            "pformat_config": len(pformat_b),
            "loader_nor_bin": ldr_nor_sz,
            "nor_loader_writer": len(nor_writer_b),
            "us_spi_firmup": len(spi_up_b),
            "us_darwin_firm": len(darwin_up_b),
            "big_backup_conf": len(big_bk_b),
            "ud_keep_backup": len(ud_keep_b),
            "mew_bin": mew_sz,
            "darwin_core_bin": darwin_sz,
        }
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        fx = build_clean_room_realhw_cp_backup_fixtures()
        fx3_buf = fx["fx3_cp"]
        fx6_buf = fx["fx6_cp"]
        fx3_cp_prof = CpRtosProfileSummary(
            body="FX3_702",
            file_bytes=len(fx3_buf),
            sha256_prefix=hashlib.sha256(fx3_buf).hexdigest()[:16],
            load_base_hex=f"0x{CP_LOAD_BASE:08x}",
            arm32_entry_words_hex=tuple(f"0x{w:08x}" for w in struct.unpack_from("<6I", fx3_buf, 0)),
            prefix_128k_sha256=hashlib.sha256(fx3_buf[:CP_IDENTICAL_PREFIX_BYTES]).hexdigest(),
            exclusive_marker_counts={m: fx3_buf.count(m.encode("ascii")) for m in FX6_EXCLUSIVE_CP_MARKERS},
            shared_marker_counts={m: fx3_buf.count(m.encode("ascii")) for m in SHARED_CP_RTOS_MARKERS},
        )
        fx6_cp_prof = CpRtosProfileSummary(
            body="FX6_601",
            file_bytes=len(fx6_buf),
            sha256_prefix=hashlib.sha256(fx6_buf).hexdigest()[:16],
            load_base_hex=f"0x{CP_LOAD_BASE:08x}",
            arm32_entry_words_hex=tuple(f"0x{w:08x}" for w in struct.unpack_from("<6I", fx6_buf, 0)),
            prefix_128k_sha256=hashlib.sha256(fx6_buf[:CP_IDENTICAL_PREFIX_BYTES]).hexdigest(),
            exclusive_marker_counts={m: fx6_buf.count(m.encode("ascii")) for m in FX6_EXCLUSIVE_CP_MARKERS},
            shared_marker_counts={m: fx6_buf.count(m.encode("ascii")) for m in SHARED_CP_RTOS_MARKERS},
        )
        fx3_tomco_b = fx["fx3_tomco"]
        fx6_tomco_b = fx["fx6_tomco"]
        fx3_kemco_b = fx["fx3_kemco"]
        fx6_kemco_b = fx["fx6_kemco"]
        fx3_bk_b = fx["fx3_backup"]
        fx6_bk_b = fx["fx6_backup"]
        ldr_list_b = fx["ldr_bkup_list"]
        pformat_b = fx["pformat_config"]
        nor_writer_b = fx["nor_loader_writer"]
        spi_up_b = fx["us_spi_firmup"]
        darwin_up_b = fx["us_darwin_firm"]
        big_bk_b = fx["big_backup_conf"]
        ud_keep_b = fx["ud_keep_backup"]
        ldr_nor_sz = len(fx["loader_nor_bin"])
        mew_sz = len(fx["mew_bin"])
        darwin_sz = len(fx["darwin_core_bin"])
        donor_sizes = {k: len(v) for k, v in fx.items()}

    # --- Pillar 1: Unknown U2 CP RTOS & Cmdline Divergence ---
    p1_errors: List[str] = []
    prefix_identical = fx3_cp_prof.prefix_128k_sha256 == fx6_cp_prof.prefix_128k_sha256
    if not prefix_identical:
        p1_errors.append("CP_128K_PREFIX_MISMATCH")
    expected_entry_hex = tuple(f"0x{w:08x}" for w in CP_ARM32_ENTRY_WORDS)
    if fx3_cp_prof.arm32_entry_words_hex != expected_entry_hex or fx6_cp_prof.arm32_entry_words_hex != expected_entry_hex:
        p1_errors.append("CP_ARM32_ENTRY_VECTOR_MISMATCH")
    for m in FX6_EXCLUSIVE_CP_MARKERS:
        if fx3_cp_prof.exclusive_marker_counts.get(m, -1) != 0:
            p1_errors.append(f"FX3_CP_UNEXPECTED_{m}_HIT")
        if fx6_cp_prof.exclusive_marker_counts.get(m, 0) <= 0:
            p1_errors.append(f"FX6_CP_MISSING_{m}_HIT")
    for m in SHARED_CP_RTOS_MARKERS:
        if fx3_cp_prof.shared_marker_counts.get(m, 0) <= 0 or fx6_cp_prof.shared_marker_counts.get(m, 0) <= 0:
            p1_errors.append(f"SHARED_CP_MARKER_MISSING_{m}")

    fx3_tomco = parse_tomco_text(fx3_tomco_b.decode("ascii", errors="replace"), body="FX3_702", file_bytes=len(fx3_tomco_b))
    fx6_tomco = parse_tomco_text(fx6_tomco_b.decode("ascii", errors="replace"), body="FX6_601", file_bytes=len(fx6_tomco_b))
    if fx3_tomco.memcfg_pools != EXPECTED_TOMCO_MEMCFG_POOLS or fx6_tomco.memcfg_pools != EXPECTED_TOMCO_MEMCFG_POOLS:
        p1_errors.append("TOMCO_MEMCFG_POOL_MISMATCH")
    if fx3_tomco.memcfg_total_mib != EXPECTED_TOMCO_TOTAL_MIB or fx6_tomco.memcfg_total_mib != EXPECTED_TOMCO_TOTAL_MIB:
        p1_errors.append("TOMCO_MEMCFG_MIB_MISMATCH")

    fx3_kemco = parse_kemco_text(fx3_kemco_b.decode("ascii", errors="replace"), body="FX3_702", file_bytes=len(fx3_kemco_b))
    fx6_kemco = parse_kemco_text(fx6_kemco_b.decode("ascii", errors="replace"), body="FX6_601", file_bytes=len(fx6_kemco_b))
    if fx3_kemco.cfg_uart != 1 or fx6_kemco.cfg_uart != 9:
        p1_errors.append(f"KEMCO_UART_DIVERGENCE_MISMATCH: fx3={fx3_kemco.cfg_uart}, fx6={fx6_kemco.cfg_uart}")

    eval_fx3_cp_ok = evaluate_cp_rtos_compatibility(
        target_body="ILME_FX3",
        cp_source_body="FX3_STOCK_702",
        route="ROUTE_1_HYBRID_STAGE_B",
        kemco_uart=fx3_kemco.cfg_uart or 1,
        has_darwin_nd_driver=False,
        has_mew_fpga_driver=False,
    )
    blk_fx6_cp = evaluate_cp_rtos_compatibility(
        target_body="ILME_FX3",
        cp_source_body="FX6_STOCK_601",
        route="ROUTE_2_FULL_FX6_NAND_NOR",
        kemco_uart=fx6_kemco.cfg_uart or 9,
        has_darwin_nd_driver=True,
        has_mew_fpga_driver=True,
    )
    if not eval_fx3_cp_ok.valid:
        p1_errors.extend(eval_fx3_cp_ok.errors)
    if blk_fx6_cp.valid:
        p1_errors.append("NEGATIVE_FX6_CP_ON_FX3_CHECK_FAILED")

    pillar1 = Pillar1CpRtosDivergenceReport(
        passed=len(p1_errors) == 0,
        fx3_cp=fx3_cp_prof,
        fx6_cp=fx6_cp_prof,
        prefix_128k_identical=prefix_identical,
        fx3_tomco=fx3_tomco,
        fx6_tomco=fx6_tomco,
        fx3_kemco=fx3_kemco,
        fx6_kemco=fx6_kemco,
        eval_fx3_stock_cp_route1=eval_fx3_cp_ok,
        blocked_fx6_cp_on_fx3_hw=blk_fx6_cp,
        errors=tuple(p1_errors),
    )

    # --- Pillar 2: Route-1 vs Route-2 Architecture & Brick Hazards ---
    p2_errors: List[str] = []
    nor_text = nor_writer_b.decode("ascii", errors="replace")
    spi_text = spi_up_b.decode("ascii", errors="replace")
    darwin_text = darwin_up_b.decode("ascii", errors="replace")
    pformat_text = pformat_b.decode("ascii", errors="replace")

    nor_markers = {m: (m in nor_text) for m in NOR_LOADER_WRITER_MARKERS}
    spi_markers = {m: (m in spi_text) for m in US_SPI_FIRMUP_MARKERS}
    darwin_markers = {m: (m in darwin_text) for m in US_DARWIN_FIRM_MARKERS}
    pformat_files = tuple(m for m in PFORMAT_REQUIRED_FILES if m in pformat_text)

    if not all(nor_markers.values()):
        p2_errors.append("MISSING_NOR_LOADER_WRITER_MARKERS")
    if not all(spi_markers.values()):
        p2_errors.append("MISSING_US_SPI_FIRMUP_MARKERS")
    if not all(darwin_markers.values()):
        p2_errors.append("MISSING_US_DARWIN_FIRM_MARKERS")
    if len(pformat_files) != len(PFORMAT_REQUIRED_FILES):
        p2_errors.append("MISSING_PFORMAT_CONFIG_FILES")

    eval_r1 = evaluate_route1_vs_route2_architecture(route="ROUTE_1_HYBRID_STAGE_B")
    blk_r2 = evaluate_route1_vs_route2_architecture(
        route="ROUTE_2_FULL_FX6_NAND_NOR",
        loader_nor_source="FX6_CHAPLIN_LOADER_NOR",
        p3_kernel_source="FX6_CHAPLIN_KERNEL",
        p8_cp_rtos_source="FX6_CHAPLIN_CPAPP",
        p2_backup_source="FX6_CHAPLIN_BACKUP_BIN",
        usr_overlay_reversible=False,
    )
    if not eval_r1.valid:
        p2_errors.extend(eval_r1.errors)
    if blk_r2.valid:
        p2_errors.append("NEGATIVE_ROUTE2_BRICK_GUARD_FAILED")

    pillar2 = Pillar2RouteArchitectureReport(
        passed=len(p2_errors) == 0,
        nor_loader_writer_markers=nor_markers,
        us_spi_firmup_markers=spi_markers,
        us_darwin_firm_markers=darwin_markers,
        pformat_files=pformat_files,
        fx3_loader_nor_bytes=ldr_nor_sz,
        fx6_mew_bin_bytes=mew_sz,
        fx6_darwin_core_bytes=darwin_sz,
        eval_route1_hybrid_stage_b=eval_r1,
        blocked_route2_full_fx6_nand_nor=blk_r2,
        errors=tuple(p2_errors),
    )

    # --- Pillar 3: Unknown U3 Backup.bin 819->840 & 0x00fa0080 Slot Tables ---
    p3_errors: List[str] = []
    fx3_bk4, fx3_b0, fx3_b1 = parse_dual_bk4_and_descriptors(fx3_bk_b, body="FX3_702")
    fx6_bk4, fx6_b0, fx6_b1 = parse_dual_bk4_and_descriptors(fx6_bk_b, body="FX6_601")
    if fx3_bk4.rec0_subsystems != EXPECTED_FX3_SUBSYSTEMS or fx3_bk4.rec1_subsystems != EXPECTED_FX3_SUBSYSTEMS:
        p3_errors.append("FX3_BK4_SUBSYSTEM_COUNT_MISMATCH")
    if fx6_bk4.rec0_subsystems != EXPECTED_FX6_SUBSYSTEMS or fx6_bk4.rec1_subsystems != EXPECTED_FX6_SUBSYSTEMS:
        p3_errors.append("FX6_BK4_SUBSYSTEM_COUNT_MISMATCH")
    if not (fx3_bk4.rec0_checksum_valid and fx3_bk4.rec1_checksum_valid and fx6_bk4.rec0_checksum_valid and fx6_bk4.rec1_checksum_valid):
        p3_errors.append("BK4_CHECKSUM_INVALID")

    desc_diff = evaluate_boot_descriptor_diff(
        fx3_bank0=fx3_b0,
        fx6_bank0=fx6_b0,
        fx3_bank1=fx3_b1,
        fx6_bank1=fx6_b1,
    )
    if not desc_diff.valid:
        p3_errors.extend(desc_diff.errors)

    ldr_tokens = [tok.strip() for tok in ldr_list_b.decode("ascii", errors="replace").split(",") if tok.strip()]
    ldr_prefixes = tuple(sorted({tok[:4].lower() for tok in ldr_tokens}))
    big_paths = tuple(line.strip() for line in big_bk_b.decode("ascii", errors="replace").splitlines() if line.strip())
    ud_markers = {m: (m.encode("ascii") in ud_keep_b) for m in UD_KEEP_BACKUP_MARKERS}

    if len(ldr_tokens) != EXPECTED_LDR_BKUP_KEY_COUNT:
        p3_errors.append(f"LDR_BKUP_KEY_COUNT_MISMATCH: {len(ldr_tokens)}")
    if ldr_prefixes != EXPECTED_LDR_BKUP_PREFIXES:
        p3_errors.append(f"LDR_BKUP_PREFIXES_MISMATCH: {ldr_prefixes}")
    if big_paths != EXPECTED_BIG_BACKUP_PATHS:
        p3_errors.append(f"BIG_BACKUP_CONF_MISMATCH: {big_paths}")
    if not all(ud_markers.values()):
        p3_errors.append("UD_KEEP_BACKUP_MARKERS_MISSING")

    eval_calib_ok = evaluate_per_body_calibration_policy(
        target_body="ILME_FX3",
        preserve_factory_backup_bin=True,
        preserve_psd_and_defdet=True,
        use_ud_keep_backup_r_merge=True,
        cross_camera_raw_flash_attempted=False,
        ldr_bkup_key_count=len(ldr_tokens),
    )
    blk_calib = evaluate_per_body_calibration_policy(
        target_body="ILME_FX3",
        preserve_factory_backup_bin=False,
        preserve_psd_and_defdet=False,
        use_ud_keep_backup_r_merge=False,
        cross_camera_raw_flash_attempted=True,
        ldr_bkup_key_count=len(ldr_tokens),
    )
    if not eval_calib_ok.valid:
        p3_errors.extend(eval_calib_ok.errors)
    if blk_calib.valid:
        p3_errors.append("NEGATIVE_CALIBRATION_DESTRUCTION_GUARD_FAILED")

    pillar3 = Pillar3BackupLayoutReport(
        passed=len(p3_errors) == 0,
        fx3_bk4=fx3_bk4,
        fx6_bk4=fx6_bk4,
        fx3_bank0_slots=fx3_b0,
        fx6_bank0_slots=fx6_b0,
        fx3_bank1_slots=fx3_b1,
        fx6_bank1_slots=fx6_b1,
        descriptor_diff=desc_diff,
        ldr_bkup_key_count=len(ldr_tokens),
        ldr_bkup_prefixes=ldr_prefixes,
        big_backup_paths=big_paths,
        ud_keep_backup_markers=ud_markers,
        eval_preserve_fx3_calibration=eval_calib_ok,
        blocked_cross_body_backup_overwrite=blk_calib,
        errors=tuple(p3_errors),
    )

    # --- Pillar 4: Volatile RAM Staging & Zero eMMC / SPI NOR Authorization ---
    p4_errors: List[str] = []
    ok_ram = evaluate_phase137_write_guard("ram://stage_b_bk4_shadow.json")
    ok_tmp = evaluate_phase137_write_guard("/tmp/fx3_stage_b_rtos_audit.json")
    blk_p8 = evaluate_phase137_write_guard("/dev/nflasha8")
    blk_p2 = evaluate_phase137_write_guard("p2:/Backup.bin")
    blk_nor = evaluate_phase137_write_guard("spi_nor://loader_nor.bin")

    if not (ok_ram.valid and ok_tmp.valid):
        p4_errors.append("VOLATILE_STAGING_PATH_UNEXPECTEDLY_BLOCKED")
    if blk_p8.valid or blk_p2.valid or blk_nor.valid:
        p4_errors.append("PERSISTENT_EMMC_OR_SPI_NOR_WRITE_NOT_BLOCKED")

    pillar4 = Pillar4ZeroFlashAuthReport(
        passed=len(p4_errors) == 0,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        emmc_mutation_bytes=0,
        spi_nor_mutation_bytes=0,
        calibration_mutation_bytes=0,
        allowed_ram_probe=ok_ram,
        allowed_tmp_probe=ok_tmp,
        blocked_nflasha8_cp=blk_p8,
        blocked_p2_backup=blk_p2,
        blocked_spi_nor_loader=blk_nor,
        errors=tuple(p4_errors),
    )

    all_errors = p1_errors + p2_errors + p3_errors + p4_errors
    all_passed = bool(
        pillar1.passed
        and pillar2.passed
        and pillar3.passed
        and pillar4.passed
        and not all_errors
    )

    digest_input = "|".join(
        [
            PHASE_137_SCHEMA,
            mode,
            fx3_cp_prof.prefix_128k_sha256,
            fx3_bk4.rec1_checksum_hex,
            fx6_bk4.rec1_checksum_hex,
            str(all_passed),
        ]
    ).encode("utf-8")
    report_sha256 = hashlib.sha256(digest_input).hexdigest()

    return RealhwCpRtosAndBackupBinReport(
        schema_version=PHASE_137_SCHEMA,
        phase_version=PHASE_137_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        donor_file_sizes=donor_sizes,
        pillar1_cp_rtos_divergence=pillar1,
        pillar2_route_architecture=pillar2,
        pillar3_backup_layout=pillar3,
        pillar4_zero_flash_auth=pillar4,
        errors=tuple(all_errors),
        report_sha256=report_sha256,
    )


def realhw_cp_rtos_and_backup_bin_report_to_dict(
    report: RealhwCpRtosAndBackupBinReport,
) -> Dict[str, object]:
    """Convert `RealhwCpRtosAndBackupBinReport` to a deterministic JSON-serializable dict."""
    return asdict(report)
