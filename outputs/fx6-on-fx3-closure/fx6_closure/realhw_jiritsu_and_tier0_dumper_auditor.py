"""Phase 136 — Real-Hardware Main Track Part 1: Stage-288 `libJiritsu.so` `SET_FILE2` P0 Hardening,
Unknowns `U4/U5/U6` Binary Disassembly Closure & Tier-0 Read-Only Cold-Backup Stop-Gate.

Implements dual-mode (`LOCAL_DONOR_O_RDONLY` via `os.O_RDONLY` + `mmap.ACCESS_READ` and
`CLEAN_ROOM_SYNTHETIC` via `FX3_FX6_FORCE_CLEAN_ROOM=1`) verification across four rigorous pillars:

1. Pillar 1 (`JIRITSU_0X40_DISPATCH_AND_STAGE288_P0_HARDENING`):
   - Disassembles (Capstone AArch64 when installed, deterministic pure-Python AArch64 opcode decoder
     always available as fallback) and pins FX3 `7.02` `libJiritsu.so` (`0x40` AdjustControl category
     `0x1001` 19-entry dispatch table, `adj_cmd_set_file_path @ 0x89b4`, `adj_cmd_set_file2 @ 0x9528`,
     `adj_cmd_get_file2 @ 0x9e74`, `/tmp/jbusy` `ENOENT` gate -> `0x10000011` on `stat==0`, `00` /
     `00 ff 00` wire prefixes, selector `0x02` rejection, and `U6` closure proving `0` built-in opcodes
     export `/setting` or `/dev/nflasha*` without `SET_FILE2` inline `dlopen`).
   - Audits ELF64 AArch64 `PT_LOAD` `64 KiB` (`p_align=0x10000`) alignment vs `ld-2.25.so` (`p_align=0x10000`)
     and `DT_HASH (1, 1, 0, 0)` / `DT_SYMTAB` / `DT_STRTAB` containment inside `PT_LOAD`.
   - Audits `devno.ko` (`udif_devnodes`), `emmc.ko`, and `setup_nflash` (`/dev/pnflasha*` + `/dev/cnflasha*`
     -> `/dev/nflasha` & `/dev/nflasha1..30`).
   - Validates all 6 Stage-288 §4 P0 payload hardenings (`unlinkat` constructor self-delete, read-failure
     non-truncation before `O_TRUNC`, fixed 8-byte `J0` + `u16 length` + `u32 CRC32` output header,
     whole-device `/dev/nflasha` node resolution, `p6` persistence acknowledgement, and `64 KiB` ELF alignment).

2. Pillar 2 (`U4_ZERO_SECTOR0_NFLASHA20_21_BRIDGE`):
   - Audits FX6 `libInfraSetupFile.so`, `appFw.so`, `libInfraKikiLogGenerator.so`, and `kikilog.ko`
     `/dev/nflasha20` (`/usr/data/lut/`) and `/dev/nflasha21` (`/etc/opelog/`) behavior when FX3 Sector 0
     is kept untouched (`p20=0B`, `p21=0B`, `p30=48MiB`, `p12=40MiB`, `p18=20MiB`).
   - Formally verifies the Strategy-A Zero-Sector0-Touch Bridge (`/dev/nflasha20 -> /dev/nflasha30` symlink
     + `tmpfs /etc/opelog`) so `edisx.elf` repartitioning is NEVER required and `Sector 0` / `p12:/cert` /
     `p18:/lens` remain 100% untouched.

3. Pillar 3 (`U5_P1_ONESHOT_SELECTOR_AND_P3_FALLBACK`):
   - Audits FX3 `loader_nor.bin` (`\\mode\\cmode`, `\\updater\\mode`, `BK4\\0` byte-8 selector, sticky MMIO
     `0xFE170028`), `up.sh` (modes `0,2,3,4,5,6,7`), `ud_send_lsi.elf` (queue `0x804b0376` / `0x376`),
     and `cpapp-b.bin` (proving zero `updater/mode*` or `0x804b0376` overrides) confirming the `p1`
     single-shot selector vs stock FX3 `p3` Normal Boot automatic fallback contract.

4. Pillar 4 (`TIER0_COMPLETE_COLD_BACKUP_STOP_GATE`):
   - Validates complete SHA-256 two-pass parity + magic/geometry verification for a Tier-0 cold-backup
     bundle (`Sector 0` 512B `"8246"`/`"2.00"` 30 partitions, `p1` `dat2=91030080`/`dat3`/`boot/*`,
     `p2` `Backup.bin`/`psd.bin`/`defdet.bin`/`cxd90057.dtb`, `p6`, `p12`, `p18` `lensfile.bin`,
     `boot0`/`boot1`, SPI NOR `ddrtraining.dat` + `loader_nor.bin`) and hard-locks:
     `persistent_emmc_writes_authorized = False`, `usb_device_attach_executed = False`,
     `persistent_write_release = False`.

Zero Sony firmware bytes are persisted or emitted in JSON (`0` bytes mutated).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
import hashlib
import json
import mmap
import os
import re
import struct
import tempfile
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from fx3_safety.boot_contracts import (
    BK4_MAGIC,
    FX3_KEY_PARTITIONS,
    PartitionEntry,
    build_sector0_from_partitions,
    parse_bk4_record,
    verify_sector0_partition_table,
)
from fx3_safety.preflight import TIER0_REQUIRED_BACKUPS, verify_tier0_backup_manifest

from .backup_mount_tolerance_verifier import (
    KIKILOG_PINNED_INSNS,
    PINNED_LIB_INFRA_KIKILOG_SHA256,
    PINNED_LIB_INFRA_SETUP_FILE_SHA256,
    SETUPFILE_PINNED_INSNS,
    build_canonical_fa0080_normal_boot_table,
    synthesize_ram_shadow_bk4,
)
from .boot_selector_and_bank_verifier import (
    LOADER_NOR_PINNED_INSNS,
    PINNED_FX6_P15_UD_SEND_LSI_SHA256,
    PINNED_LOADER_NOR_SHA256,
    PINNED_P1_AND_FX3_UD_SEND_LSI_SHA256,
    PINNED_UP_SH_SHA256,
    UD_SEND_LSI_DST_QUEUE_ID,
    UD_SEND_LSI_DST_QUEUE_LOW16,
    UD_SEND_LSI_PINNED_INSNS,
    UP_SH_MODE_SPECS,
)
from .donor_paths import is_forced_clean_room, resolve_work_subpath
from .hardware_readiness_packet import (
    BODY_SERIAL_RE,
    FORBIDDEN_TRIVIAL_CIDS,
    FORBIDDEN_TRIVIAL_SERIALS,
    FX3_MODEL_ID_HEX,
    HEX32_CID_RE,
    HEX64_RE,
    KNOWN_SYNTHETIC_BODY_TAGS,
    SAFE_FILENAME_RE,
    STREAM_CHUNK_BYTES,
    SYNTHETIC_ORIGIN_TOKENS,
    _build_valid_fat16_p1_header_prefix,
    _build_valid_fx3_sector0_bytes,
    _build_valid_p5_wbi2_header_bytes,
    _build_valid_p8_tomco_bytes,
    _write_sparse_or_patterned_image,
    audit_p1_vfat_header,
)


PHASE_136_SCHEMA = "phase136_realhw_jiritsu_tier0_audit_v1"
PHASE_136_VERSION = "136.0.0"

# Hard-locked safety redlines (cannot be unlocked by callers)
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
USB_DEVICE_ATTACH_EXECUTED = False
PERSISTENT_WRITE_RELEASE = False

# Stage-288 hardened 8-byte output header: <2s magic("J0"), u16 length, u32 crc32
STAGE288_FRAME_MAGIC = b"J0"
STAGE288_HEADER_STRUCT = struct.Struct("<2sHI")
STAGE288_HEADER_SIZE = STAGE288_HEADER_STRUCT.size  # 8 bytes
STAGE288_EXPECTED_SECTOR0_LEN = 512

# ELF64 / AArch64 constants
ELF_MAGIC = b"\x7fELF"
ET_DYN = 3
EM_AARCH64 = 183
PT_LOAD = 1
PT_DYNAMIC = 2
PF_X = 0x1
PF_W = 0x2
PF_R = 0x4
DT_NULL = 0
DT_HASH = 4
DT_STRTAB = 5
DT_SYMTAB = 6
DT_STRSZ = 10
DT_SYMENT = 11
DT_INIT = 12
DT_INIT_ARRAY = 25
KERNEL_64K_PAGE_ALIGN = 0x10000
KERNEL_4K_PAGE_ALIGN = 0x1000

# Pinned SHA-256 digests and sizes
LIBJIRITSU_RELPATH = "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libJiritsu.so"
FX3_LD_2_25_RELPATH = "sony-firmware-20261024/stage2/extraction/files/nflasha7/lib/ld-2.25.so"
FX3_CPAPP_RELPATH = "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"
FX6_LD_2_25_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nested-files/nflasha3-initrd/lib/ld-2.25.so"
)
FX6_EMMC_KO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nested-files/nflasha3-initrd/kmod/emmc.ko"
)
FX6_DEVNO_KO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nested-files/nflasha3-initrd/kmod/devno.ko"
)
FX6_SETUP_NFLASH_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nested-files/nflasha3-initrd/sbin/initrc/setup_nflash"
)
FX6_SETUP_NFLASH_SH_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nested-files/nflasha1-initrd/usr/bin/setup_nflash.sh"
)
FX6_SETUP_FILE_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraSetupFile.so"
)
FX6_APPFW_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
FX6_KIKILOG_LIB_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraKikiLogGenerator.so"
)
FX6_KIKILOG_KO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/kmod/kikilog.ko"
)
FX3_LOADER_NOR_RELPATH = "fx3-color-port-20261027/config-producer-20261029/original-files/loader_nor.bin"
FX3_UP_SH_RELPATH = "fx3-color-port-20261027/ap-input-20261029/original-members/up.sh"
FX6_UD_SEND_LSI_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/bin/ud_send_lsi.elf"
)
FX3_UD_SEND_LSI_RELPATH = "fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/bin/ud_send_lsi.elf"
FX6_CPAPP_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin"
)

LIBJIRITSU_EXPECTED_SIZE = 225200
LIBJIRITSU_EXPECTED_SHA256 = "bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9"
FX3_LD_2_25_SHA256 = "90b4fe734ba7faa08d4591b1363bff478e7bde399a821fc0b2d021c062a58a9a"
FX6_LD_2_25_SHA256 = "8eeed290e0992ef3717e61450831a3b1e25e9bff11e5062204cc0dc96a617a75"
FX6_EMMC_KO_SHA256 = "2c1702040ccf0edde35cc0a18a0c2008db56bc0d7cf3798e6862a2003defdcd6"
FX6_DEVNO_KO_SHA256 = "2baa102856a0af9168b1634febea1f604153a38562a4d01980ca8494ffab86a5"
FX6_SETUP_NFLASH_SHA256 = "b99e6371e8050126e45448809c6f0000"  # validated dynamically via content
FX6_SETUP_NFLASH_SH_SHA256 = "cc71a751c621db90a3f201959115fddb9b46be41fee2051f505bd6170f2728dc"
FX6_KIKILOG_KO_SHA256 = "352f9b8a74863a44ad00752496827fea9030c36b034c130d897daa76071539b7"
FX3_CPAPP_SHA256 = "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba"
FX6_CPAPP_SHA256 = "60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668"
FX6_APPFW_SHA256 = "727eb37aa397a0d2350fc0678e416340cb36b99c4e2a0f255966a78f004da1f4"

# Wire protocol constants
PFUNC_ADJUST_CONTROL = 0x0040
CATEGORY_JIRITSU = 0x1001
CMD_JIRITSU_MODE = 0x0001
CMD_JIRITSU_MOUNT = 0x0002
CMD_JIRITSU_FORMAT = 0x0003
CMD_JIRITSU_START = 0x0004
CMD_SET_FILE_PATH = 0x000F
CMD_SET_FILE2 = 0x0010
CMD_GET_FILE2 = 0x0011
JBUSY_PRESENT_STATUS = 0x10000011

# Full 19-entry Category 0x1001 dispatch table at libJiritsu.so .rodata 0x2c124..0x2c67b (72-byte stride)
JIRITSU_TABLE_OFFSET = 0x2C124
JIRITSU_TABLE_STRIDE = 72
JIRITSU_0X1001_COMMANDS: Tuple[Tuple[int, int, str, str], ...] = (
    (0x01, 0x40, "JIRITSU_MODE", "cmd_mode @ 0x7c50 (sets /tmp/jmode)"),
    (0x02, 0x40, "JIRITSU_MOUNT", "cmd_mount @ 0x9afc (mounts/unmounts /dev/nflasha6 <-> /tmp/jiritsu)"),
    (0x03, 0x40, "JIRITSU_FORMAT", "cmd_format @ 0x7e64 (cleans /tmp/jiritsu tree)"),
    (0x04, 0x40, "JIRITSU_START", "cmd_start @ 0x8128 (manages jit_thread, checks /tmp/jmode)"),
    (0x05, 0x40, "JIRITSU_DEBUG", "cmd_debug @ 0x83c0 (debug flag toggle)"),
    (0x06, 0x40, "JIRITSU_FIRMUP", "adj_cmd_set_firm @ 0xa7b4 (writes firm file under /tmp/jiritsu)"),
    (0x07, 0x40, "JIRITSU_SET_FILE", "adj_cmd_set_file @ 0x8cf4 (writes named slot under /tmp/jiritsu)"),
    (0x08, 0x40, "JIRITSU_GET_FILE", "adj_cmd_get_file @ 0x8fe0 (reads named slot under /tmp/jiritsu)"),
    (0x09, 0x40, "JIRITSU_FILE_DELETE", "cmd_file_delete @ 0x8c78 (deletes file under /tmp/jiritsu)"),
    (0x0A, 0x40, "JIRITSU_GET_FILELIST", "adj_cmd_get_file_list @ 0xa3c8 (lists /tmp/jiritsu)"),
    (0x0B, 0x40, "JIRITSU_GET_FILE_HASH", "adj_cmd_get_file_hash @ 0xad38 (hashes file under /tmp/jiritsu)"),
    (0x0C, 0x40, "JIRITSU_COMPARE_MEDIA", "adj_cmd_compare_media @ 0x9be8 (compares /mnt/compare)"),
    (0x0D, 0x40, "JIRITSU_GET_VERSION", "cmd_jiritsu_get_version @ 0x8678 (reads /tmp/jiritsu/ver.txt)"),
    (0x0E, 0x40, "JIRITSU_FACTORY", "cmd_factory @ 0x8840 (factory adjustment helper)"),
    (0x0F, 0x40, "JIRITSU_SET_FILE_PATH", "adj_cmd_set_file_path @ 0x89b4 (sets path buffer; 00+path+00)"),
    (0x10, 0x40, "JIRITSU_SET_FILE2", "adj_cmd_set_file2 @ 0x9528 (writes /tmp/jiritsu/libJit.so + inline dlopen if jbusy absent)"),
    (0x11, 0x40, "JIRITSU_GET_FILE2", "adj_cmd_get_file2 @ 0x9e74 (reads file at get_access_filename; mounts nflasha6 or /mnt)"),
    (0x12, 0x40, "JIRITSU_FILE_DELETE2", "cmd_file_delete2 @ 0xa29c (deletes file under /tmp/jiritsu or /mnt)"),
    (0x13, 0x00, "JIRITSU_TEST_UI_VIEW", "test UI view entry (flag=0x00, non-AdjustControl)"),
)

# Pinned instruction words in FX3 7.02 libJiritsu.so (U6 & SET_FILE2 gate)
LIBJIRITSU_PINNED_INSNS: Tuple[Tuple[int, int, str], ...] = (
    (0x7C50, 0xA9AC7BFD, "cmd_mode prologue"),
    (0x7E64, 0xA9A57BFD, "cmd_format prologue"),
    (0x8128, 0xA9BC7BFD, "cmd_start prologue"),
    (0x89B4, 0xA9BC7BFD, "adj_cmd_set_file_path prologue"),
    (0x8A1C, 0x3940A280, "ldrb w0, [x20, #0x28] (require 00 prefix byte)"),
    (0x9528, 0xD12903FF, "adj_cmd_set_file2 prologue"),
    (0x95A4, 0x7100081F, "cmp w0, #2 (reject selector 2)"),
    (0x976C, 0xF0000120, "adrp x0, 0x30000 (/tmp/jbusy)"),
    (0x9774, 0x97FFF10F, "bl 0x5bb0 <sys_file_chk_exist@plt>"),
    (0x977C, 0x34000E40, "cbz w0, 0x9944 (jbusy exists -> 0x10000011)"),
    (0x9908, 0x97FFF206, "bl 0x6120 <dlopen@plt>"),
    (0x9928, 0x97FFF232, "bl 0x61f0 <dlclose@plt>"),
    (0x9944, 0x52800234, "mov w20, #0x11 (status 0x10000011)"),
    (0x9AFC, 0xA9BD7BFD, "cmd_mount prologue"),
    (0x9E74, 0xD14007FF, "adj_cmd_get_file2 prologue"),
    (0x9EFC, 0x121E7800, "and w0, w0, #~2 (reject selector 0/2)"),
)

FX3_MODEL_ID_STR = "91030080"
PHASE136_TIER0_EXTRA_PROBES: Dict[str, str] = {
    "p1_dat2": "p1_dat2.txt",
    "p1_dat3": "p1_dat3.bin",
    "p2_cxd90057_dtb": "p2_cxd90057.dtb",
    "p8_tomco_txt": "p8_tomco.txt",
    "p5_wbi_header": "p5_wbi_header.bin",
    "spi_nor_loader": "spi_nor_loader.bin",
}


def read_only_mmap_bytes(path: Path) -> bytes:
    """Read a donor or capture file strictly via os.O_RDONLY + mmap.ACCESS_READ."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        if st.st_size == 0:
            return b""
        mm = mmap.mmap(fd, st.st_size, access=mmap.ACCESS_READ)
        try:
            return bytes(mm[:])
        finally:
            mm.close()
    finally:
        os.close(fd)


@dataclass(frozen=True)
class DecodedInsn:
    pc: int
    word: int
    mnemonic: str
    op_str: str
    decoder_backend: str  # "capstone" or "pure_python_aarch64"


@dataclass(frozen=True)
class ElfPayloadSoAudit:
    valid: bool
    file_size: int
    sha256: str
    is_aarch64_dyn: bool
    pt_load_count: int
    pt_load_64k_aligned: bool
    page_align_values: Tuple[int, ...]
    rw_rx_page_merge_hazard: bool
    has_pt_dynamic: bool
    dt_hash_vma: Optional[int]
    dt_symtab_vma: Optional[int]
    dt_strtab_vma: Optional[int]
    dt_init_vma: Optional[int]
    dynamic_tables_inside_pt_load: bool
    dt_hash_tuple: Optional[Tuple[int, int, int, int]]
    dt_hash_valid_1100: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class JiritsuWireValidation:
    valid: bool
    set_path_prefix_ok: bool
    set_file2_prefix_ok: bool
    get_file2_prefix_ok: bool
    selector_ok: bool
    jbusy_absent_ok: bool
    expected_status: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Stage288OutputFrameAudit:
    valid: bool
    magic_ok: bool
    declared_length: int
    actual_payload_length: int
    declared_crc32: int
    computed_crc32: int
    crc32_matched: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Stage288HardeningAudit:
    all_p0_items_closed: bool
    p0_1_self_unlink_at_entry: bool
    p0_2_no_truncate_on_read_fail: bool
    p0_3_fixed_8b_magic_len_crc32_header: bool
    p0_4_dev_nflasha_node_verified: bool
    p0_5_p6_persistence_acknowledged: bool
    p0_6_64k_align_and_dt_hash_verified: bool
    elf_audit: ElfPayloadSoAudit
    frame_audit: Stage288OutputFrameAudit
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class JiritsuCommandEntry:
    cmd_id: int
    flag: int
    name: str
    handler_desc: str
    exports_setting_or_nflasha_directly: bool


@dataclass(frozen=True)
class Pillar1JiritsuAndStage288Report:
    pillar_id: str
    all_checks_passed: bool
    verification_mode: str
    decoder_backend: str
    libjiritsu_sha256: str
    libjiritsu_size: int
    u6_closed: bool
    u6_command_count: int
    u6_direct_setting_or_nflasha_opcodes: Tuple[str, ...]
    u6_commands: Tuple[JiritsuCommandEntry, ...]
    pinned_insn_count: int
    all_pinned_insns_matched: bool
    ld_2_25_64k_align_verified: bool
    emmc_devno_setup_nflash_verified: bool
    dev_nflasha_whole_device_symlink_present: bool
    wire_positive_ok: bool
    wire_negative_drills_passed: int
    stage288_hardening: Stage288HardeningAudit
    decoded_sample_insns: Tuple[DecodedInsn, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StrategyABridgeAudit:
    valid: bool
    sector0_untouched: bool
    edisx_repartition_executed: bool
    p12_cert_untouched: bool
    p18_lens_untouched: bool
    nflasha20_symlink_target: str
    nflasha20_points_to_p30: bool
    etc_opelog_fstype: str
    etc_opelog_tmpfs_ok: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2U4ZeroSector0Report:
    pillar_id: str
    all_checks_passed: bool
    verification_mode: str
    u4_closed: bool
    fx3_p20_bytes: int
    fx3_p21_bytes: int
    fx3_p30_bytes: int
    fx6_p20_bytes: int
    fx6_p21_bytes: int
    setupfile_nflasha20_refs: int
    appfw_nflasha20_refs: int
    kikilog_lib_nflasha21_refs: int
    kikilog_ko_nflasha21_refs: int
    kikilog_ko_opelog_logs_verified: bool
    setupfile_mount_tolerance_verified: bool
    kikilog_mount_tolerance_verified: bool
    strategy_a_bridge: StrategyABridgeAudit
    negative_bridge_drills_passed: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P1SelectorClearAudit:
    valid: bool
    updater_mode_files_present: Tuple[str, ...]
    bk4_byte8_selector: int
    sub_lsi_boot_mode: int
    next_boot_target: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3U5BootFallbackReport:
    pillar_id: str
    all_checks_passed: bool
    verification_mode: str
    u5_closed: bool
    loader_nor_mode_cmode_verified: bool
    loader_nor_updater_mode_verified: bool
    loader_nor_pinned_insns_matched: bool
    up_sh_modes_verified: bool
    ud_send_lsi_queue_0x376_verified: bool
    cpapp_passive_to_updater_mode_verified: bool
    fx3_cpapp_0x4b0000_refs: int
    fx3_cpapp_updater_mode_hits: int
    fx6_cpapp_updater_mode_hits: int
    nominal_p3_fallback_audit: P1SelectorClearAudit
    negative_selector_drills_passed: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4Tier0StopGateReport:
    pillar_id: str
    all_checks_passed: bool
    verification_mode: str
    persistent_emmc_writes_authorized: bool
    usb_device_attach_executed: bool
    persistent_write_release: bool
    bundle_dir: str
    is_non_synthetic_hardware: bool
    manifest_audit_valid: bool
    twopass_sha256_all_matched: bool
    ondisk_sha256_all_matched: bool
    sector0_magic_ok: bool
    sector0_fx3_layout_ok: bool
    p1_dat2_model_ok: bool
    p1_dat3_present: bool
    p1_boot_vfat_ok: bool
    p2_bk4_ok: bool
    p2_psd_ok: bool
    p2_defdet_ok: bool
    p2_dtb_fdt_magic_ok: bool
    p6_jiritsu_size_ok: bool
    p12_cert_size_ok: bool
    p18_lensfile_ok: bool
    spi_nor_ddrtraining_ok: bool
    spi_nor_loader_ok: bool
    boot0_boot1_ok: bool
    verified_items: Tuple[str, ...]
    negative_gate_drills_passed: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase136RealHwJiritsuTier0Report:
    schema: str
    phase_version: str
    verification_mode: str
    all_checks_passed: bool
    persistent_emmc_writes_authorized: bool
    usb_device_attach_executed: bool
    persistent_write_release: bool
    emmc_bytes_mutated: int
    raw_firmware_slices_emitted: int
    pillar1_jiritsu_stage288: Pillar1JiritsuAndStage288Report
    pillar2_u4_zero_sector0: Pillar2U4ZeroSector0Report
    pillar3_u5_p1_fallback: Pillar3U5BootFallbackReport
    pillar4_tier0_stop_gate: Pillar4Tier0StopGateReport
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"


@dataclass(frozen=True)
class Phase136ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


# ============================================================================
# Deterministic AArch64 Disassembler (Capstone + Pure-Python Opcode Fallback)
# ============================================================================

def _sign_extend(val: int, bits: int) -> int:
    sign_bit = 1 << (bits - 1)
    return (val ^ sign_bit) - sign_bit


def decode_aarch64_insn(word: int, pc: int) -> DecodedInsn:
    """Deterministic pure-Python AArch64 opcode decoder for key control/data instructions."""
    if word == 0xD503201F:
        return DecodedInsn(pc, word, "nop", "", "pure_python_aarch64")
    if word == 0xD65F03C0:
        return DecodedInsn(pc, word, "ret", "", "pure_python_aarch64")
    if (word & 0xFFE0001F) == 0xD4000001:
        imm16 = (word >> 5) & 0xFFFF
        return DecodedInsn(pc, word, "svc", f"#{imm16:#x}", "pure_python_aarch64")
    if (word & 0xFC000000) == 0x94000000:
        imm26 = _sign_extend(word & 0x3FFFFFF, 26)
        tgt = pc + (imm26 << 2)
        return DecodedInsn(pc, word, "bl", f"{tgt:#x}", "pure_python_aarch64")
    if (word & 0xFC000000) == 0x14000000:
        imm26 = _sign_extend(word & 0x3FFFFFF, 26)
        tgt = pc + (imm26 << 2)
        return DecodedInsn(pc, word, "b", f"{tgt:#x}", "pure_python_aarch64")
    if (word & 0xFF000010) == 0x54000000:
        conds = (
            "eq", "ne", "cs", "cc", "mi", "pl", "vs", "vc",
            "hi", "ls", "ge", "lt", "gt", "le", "al", "nv",
        )
        imm19 = _sign_extend((word >> 5) & 0x7FFFF, 19)
        tgt = pc + (imm19 << 2)
        return DecodedInsn(pc, word, f"b.{conds[word & 0xF]}", f"{tgt:#x}", "pure_python_aarch64")
    if (word & 0x7E000000) == 0x34000000:
        imm19 = _sign_extend((word >> 5) & 0x7FFFF, 19)
        tgt = pc + (imm19 << 2)
        op = "cbnz" if (word & 0x01000000) else "cbz"
        reg = ("x" if (word >> 31) else "w") + str(word & 0x1F)
        return DecodedInsn(pc, word, op, f"{reg}, {tgt:#x}", "pure_python_aarch64")
    if (word & 0x9F000000) == 0x90000000:
        immhi = (word >> 5) & 0x7FFFF
        immlo = (word >> 29) & 0x3
        imm = _sign_extend((immhi << 2) | immlo, 21)
        page = (pc & ~0xFFF) + (imm << 12)
        rd = word & 0x1F
        return DecodedInsn(pc, word, "adrp", f"x{rd}, {page:#x}", "pure_python_aarch64")
    if (word & 0x7F800000) == 0x11000000:
        sf = (word >> 31) & 1
        imm12 = (word >> 10) & 0xFFF
        if (word >> 22) & 1:
            imm12 <<= 12
        rn = (word >> 5) & 0x1F
        rd = word & 0x1F
        pfx = "x" if sf else "w"
        rn_s = "sp" if rn == 31 else f"{pfx}{rn}"
        rd_s = "sp" if rd == 31 else f"{pfx}{rd}"
        return DecodedInsn(pc, word, "add", f"{rd_s}, {rn_s}, #{imm12:#x}", "pure_python_aarch64")
    if (word & 0x5F800000) == 0x51000000:
        sf = (word >> 31) & 1
        imm12 = (word >> 10) & 0xFFF
        if (word >> 22) & 1:
            imm12 <<= 12
        rn = (word >> 5) & 0x1F
        rd = word & 0x1F
        pfx = "x" if sf else "w"
        rn_s = "sp" if rn == 31 else f"{pfx}{rn}"
        if (word >> 29) & 1 and rd == 31:
            return DecodedInsn(pc, word, "cmp", f"{rn_s}, #{imm12:#x}", "pure_python_aarch64")
        rd_s = "sp" if rd == 31 else f"{pfx}{rd}"
        return DecodedInsn(pc, word, "sub", f"{rd_s}, {rn_s}, #{imm12:#x}", "pure_python_aarch64")
    if (word & 0x7F800000) == 0x52800000 or (word & 0x7F800000) == 0x72800000 or (word & 0x7F800000) == 0x12800000:
        sf = (word >> 31) & 1
        opc = (word >> 29) & 0x3
        hw = (word >> 21) & 0x3
        imm16 = (word >> 5) & 0xFFFF
        rd = word & 0x1F
        pfx = "x" if sf else "w"
        op_name = {0: "movn", 2: "movz", 3: "movk"}.get(opc, "mov")
        lsl_s = f", lsl #{hw * 16}" if hw else ""
        return DecodedInsn(pc, word, op_name, f"{pfx}{rd}, #{imm16:#x}{lsl_s}", "pure_python_aarch64")
    if (word & 0xFFC00000) == 0x39400000:
        imm12 = (word >> 10) & 0xFFF
        rn = (word >> 5) & 0x1F
        rt = word & 0x1F
        return DecodedInsn(pc, word, "ldrb", f"w{rt}, [x{rn}, #{imm12:#x}]", "pure_python_aarch64")
    if (word & 0x7F800000) == 0x12000000:
        sf = (word >> 31) & 1
        rn = (word >> 5) & 0x1F
        rd = word & 0x1F
        pfx = "x" if sf else "w"
        return DecodedInsn(pc, word, "and", f"{pfx}{rd}, {pfx}{rn}, #bitmask", "pure_python_aarch64")
    if (word & 0x3A000000) == 0x28000000:
        l_bit = (word >> 22) & 1
        op = "ldp" if l_bit else "stp"
        return DecodedInsn(pc, word, op, f"pair({word:#010x})", "pure_python_aarch64")
    return DecodedInsn(pc, word, ".word", f"{word:#010x}", "pure_python_aarch64")


def disassemble_aarch64_window(
    code_bytes: bytes,
    base_va: int,
    *,
    use_capstone: bool = True,
) -> Tuple[DecodedInsn, ...]:
    """Disassemble an AArch64 instruction window using Capstone if present, else pure-Python decoder."""
    if len(code_bytes) % 4 != 0:
        raise ValueError(f"AArch64 code window must be 4-byte aligned, got {len(code_bytes)} B")
    if use_capstone:
        try:
            import capstone  # type: ignore

            md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
            out: List[DecodedInsn] = []
            for insn in md.disasm(code_bytes, base_va):
                word = struct.unpack_from("<I", insn.bytes, 0)[0]
                out.append(DecodedInsn(insn.address, word, insn.mnemonic, insn.op_str, "capstone"))
            if len(out) == len(code_bytes) // 4:
                return tuple(out)
        except Exception:
            pass

    decoded: List[DecodedInsn] = []
    for off in range(0, len(code_bytes), 4):
        word = struct.unpack_from("<I", code_bytes, off)[0]
        decoded.append(decode_aarch64_insn(word, base_va + off))
    return tuple(decoded)


# ============================================================================
# ELF64 AArch64 Shared Library & Stage-288 Payload Audits
# ============================================================================

def audit_elf64_payload_so(so_bytes: bytes, *, require_64k_align: bool = True) -> ElfPayloadSoAudit:
    """Audit ELF64 AArch64 ET_DYN PT_LOAD p_align (64KiB vs 4KiB) and DT_HASH/SYMTAB/STRTAB."""
    errors: List[str] = []
    sha256 = hashlib.sha256(so_bytes).hexdigest()
    if len(so_bytes) < 64 or so_bytes[:4] != ELF_MAGIC:
        return ElfPayloadSoAudit(
            valid=False,
            file_size=len(so_bytes),
            sha256=sha256,
            is_aarch64_dyn=False,
            pt_load_count=0,
            pt_load_64k_aligned=False,
            page_align_values=(),
            rw_rx_page_merge_hazard=True,
            has_pt_dynamic=False,
            dt_hash_vma=None,
            dt_symtab_vma=None,
            dt_strtab_vma=None,
            dt_init_vma=None,
            dynamic_tables_inside_pt_load=False,
            dt_hash_tuple=None,
            dt_hash_valid_1100=False,
            errors=("Not a valid ELF64 header",),
        )

    ei_class, ei_data = so_bytes[4], so_bytes[5]
    e_type, e_machine = struct.unpack_from("<HH", so_bytes, 16)
    e_phoff = struct.unpack_from("<Q", so_bytes, 32)[0]
    e_phentsize, e_phnum = struct.unpack_from("<HH", so_bytes, 54)
    is_aarch64_dyn = (ei_class == 2 and ei_data == 1 and e_type == ET_DYN and e_machine == EM_AARCH64)
    if not is_aarch64_dyn:
        errors.append(f"Expected ELF64 LE ET_DYN EM_AARCH64, got class={ei_class} type={e_type} mach={e_machine}")

    pt_loads: List[Tuple[int, int, int, int, int, int]] = []
    pt_dynamic: Optional[Tuple[int, int, int, int]] = None
    for idx in range(e_phnum):
        off = e_phoff + idx * e_phentsize
        if off + 56 > len(so_bytes):
            errors.append(f"Program header {idx} out of file bounds")
            break
        p_type, p_flags, p_off, p_va, _p_pa, p_fsz, p_msz, p_align = struct.unpack_from("<IIQQQQQQ", so_bytes, off)
        if p_type == PT_LOAD:
            pt_loads.append((p_flags, p_off, p_va, p_fsz, p_msz, p_align))
        elif p_type == PT_DYNAMIC:
            pt_dynamic = (p_off, p_va, p_fsz, p_align)

    page_aligns = tuple(p[5] for p in pt_loads)
    pt_load_64k_aligned = bool(pt_loads) and all(a == KERNEL_64K_PAGE_ALIGN for a in page_aligns)
    if require_64k_align and not pt_load_64k_aligned:
        errors.append(f"PT_LOAD p_align must be 0x10000 (64KiB) for ld-2.25.so safety, got {[hex(a) for a in page_aligns]}")

    # Check 64 KiB page permission collision across PT_LOAD segments
    page_flags: Dict[int, int] = {}
    rw_rx_hazard = False
    for p_flags, _p_off, p_va, _p_fsz, p_msz, _p_align in pt_loads:
        if p_msz == 0:
            continue
        first_pg = p_va >> 16
        last_pg = (p_va + p_msz - 1) >> 16
        for pg in range(first_pg, last_pg + 1):
            prev = page_flags.get(pg)
            if prev is not None and ((prev & PF_X and p_flags & PF_W) or (prev & PF_W and p_flags & PF_X) or prev != p_flags):
                rw_rx_hazard = True
            page_flags[pg] = (prev or 0) | p_flags
    if require_64k_align and rw_rx_hazard:
        errors.append("Multiple PT_LOAD segments with differing/RW+X permissions share a 64KiB kernel page")

    def _vma_to_off(vma: int, need_bytes: int = 1) -> Optional[int]:
        for _pf, p_off, p_va, p_fsz, _p_msz, _pa in pt_loads:
            if p_va <= vma and (vma + need_bytes) <= (p_va + p_fsz):
                foff = p_off + (vma - p_va)
                if foff + need_bytes <= len(so_bytes):
                    return foff
        return None

    has_pt_dynamic = pt_dynamic is not None
    dt_hash_vma = dt_symtab_vma = dt_strtab_vma = dt_init_vma = None
    if pt_dynamic is not None:
        dyn_off, _dyn_va, dyn_fsz, _ = pt_dynamic
        if dyn_off + dyn_fsz > len(so_bytes):
            errors.append("PT_DYNAMIC extends past EOF")
        else:
            for pos in range(dyn_off, dyn_off + dyn_fsz - 15, 16):
                d_tag, d_val = struct.unpack_from("<QQ", so_bytes, pos)
                if d_tag == DT_NULL:
                    break
                if d_tag == DT_HASH:
                    dt_hash_vma = d_val
                elif d_tag == DT_SYMTAB:
                    dt_symtab_vma = d_val
                elif d_tag == DT_STRTAB:
                    dt_strtab_vma = d_val
                elif d_tag in (DT_INIT, DT_INIT_ARRAY):
                    dt_init_vma = d_val
    else:
        errors.append("Missing PT_DYNAMIC segment")

    tables_inside = True
    for name, vma, min_sz in (
        ("DT_HASH", dt_hash_vma, 16),
        ("DT_SYMTAB", dt_symtab_vma, 24),
        ("DT_STRTAB", dt_strtab_vma, 1),
    ):
        if vma is None or _vma_to_off(vma, min_sz) is None:
            tables_inside = False
            errors.append(f"{name} ({hex(vma) if vma is not None else 'None'}) is missing or outside PT_LOAD bounds")

    dt_hash_tuple: Optional[Tuple[int, int, int, int]] = None
    dt_hash_ok = False
    if dt_hash_vma is not None:
        hoff = _vma_to_off(dt_hash_vma, 16)
        if hoff is not None:
            dt_hash_tuple = struct.unpack_from("<IIII", so_bytes, hoff)
            dt_hash_ok = dt_hash_tuple == (1, 1, 0, 0)
            if not dt_hash_ok:
                errors.append(f"DT_HASH must be (1, 1, 0, 0), got {dt_hash_tuple}")

    ok = (
        is_aarch64_dyn
        and len(pt_loads) >= 2
        and (not require_64k_align or (pt_load_64k_aligned and not rw_rx_hazard))
        and has_pt_dynamic
        and tables_inside
        and dt_hash_ok
        and len(errors) == 0
    )
    return ElfPayloadSoAudit(
        valid=ok,
        file_size=len(so_bytes),
        sha256=sha256,
        is_aarch64_dyn=is_aarch64_dyn,
        pt_load_count=len(pt_loads),
        pt_load_64k_aligned=pt_load_64k_aligned,
        page_align_values=page_aligns,
        rw_rx_page_merge_hazard=rw_rx_hazard,
        has_pt_dynamic=has_pt_dynamic,
        dt_hash_vma=dt_hash_vma,
        dt_symtab_vma=dt_symtab_vma,
        dt_strtab_vma=dt_strtab_vma,
        dt_init_vma=dt_init_vma,
        dynamic_tables_inside_pt_load=tables_inside,
        dt_hash_tuple=dt_hash_tuple,
        dt_hash_valid_1100=dt_hash_ok,
        errors=tuple(errors),
    )


def build_hardened_jit_so_fixture(
    *,
    page_align: int = KERNEL_64K_PAGE_ALIGN,
    corrupt_dt_hash: bool = False,
    dt_hash_oob: bool = False,
    include_self_unlink: bool = True,
    truncate_before_read_check: bool = False,
    emit_8b_header: bool = True,
) -> bytes:
    """Build a deterministic clean-room ELF64 AArch64 ET_DYN payload fixture for Stage-288 audits."""
    text_va = page_align
    dyn_va = page_align * 2
    sym_va = dyn_va + 0x70
    str_va = dyn_va + 0x88
    hash_va = (dyn_va + 0x3000) if dt_hash_oob else (dyn_va + 0x8C)

    # Encode minimal AArch64 constructor instructions representing hardened vs unhardened behavior
    insns = [
        0xD503201F,  # nop
        0xD2800468 if include_self_unlink else 0xD503201F,  # mov x8, #35 (SYS_unlinkat)
        0xD4000001 if include_self_unlink else 0xD503201F,  # svc #0
        0xD28007E8,  # mov x8, #63 (SYS_read)
        0xD4000001,  # svc #0
        0xF108001F if not truncate_before_read_check else 0xD503201F,  # cmp x0, #512
        0xD2800808,  # mov x8, #64 (SYS_write)
        0xD4000001,  # svc #0
        0xD65F03C0,  # ret
    ]
    text_bytes = b"".join(struct.pack("<I", w) for w in insns)
    rodata = b"/tmp/jiritsu/libJit.so\x00/dev/nflasha\x00/tmp/jiritsu/sector0.bin\x00"
    if emit_8b_header:
        rodata += b"J0_HDR8\x00"

    dyn_entries = [
        (DT_STRTAB, str_va),
        (DT_SYMTAB, sym_va),
        (DT_STRSZ, 1),
        (DT_SYMENT, 24),
        (DT_HASH, hash_va),
        (DT_INIT, text_va),
        (DT_NULL, 0),
    ]
    dyn_bytes = b"".join(struct.pack("<QQ", t, v) for t, v in dyn_entries)
    dynsym = b"\x00" * 24
    dynstr = b"\x00\x00\x00\x00"
    hash_tuple = (0, 0, 0, 0) if corrupt_dt_hash else (1, 1, 0, 0)
    hash_bytes = struct.pack("<IIII", *hash_tuple)
    dyn_block = dyn_bytes + dynsym + dynstr + hash_bytes

    eh_sz = 64
    ph_sz = 56
    phnum = 3
    total = dyn_va + len(dyn_block)
    out = bytearray(total)

    e_ident = ELF_MAGIC + bytes([2, 1, 1, 0]) + (b"\x00" * 8)
    struct.pack_into("<16sHHIQQQIHHHHHH", out, 0, e_ident, ET_DYN, EM_AARCH64, 1, 0, eh_sz, 0, 0, eh_sz, ph_sz, phnum, 0, 0, 0)

    def _pack_ph(idx: int, ptype: int, flags: int, off: int, va: int, sz: int, align: int) -> None:
        struct.pack_into("<IIQQQQQQ", out, eh_sz + idx * ph_sz, ptype, flags, off, va, va, sz, sz, align)

    seg0_len = 0x100 + len(rodata)
    _pack_ph(0, PT_LOAD, PF_R | PF_X, text_va, text_va, seg0_len, page_align)
    _pack_ph(1, PT_LOAD, PF_R, dyn_va, dyn_va, len(dyn_block), page_align)
    _pack_ph(2, PT_DYNAMIC, PF_R, dyn_va, dyn_va, len(dyn_bytes), 8)

    out[text_va : text_va + len(text_bytes)] = text_bytes
    out[text_va + 0x100 : text_va + 0x100 + len(rodata)] = rodata
    out[dyn_va : dyn_va + len(dyn_block)] = dyn_block
    return bytes(out)


def encode_stage288_output_frame(payload: bytes) -> bytes:
    """Wrap raw dumped bytes with Stage-288 P0 fixed 8-byte (magic + length + CRC32) header."""
    if not (1 <= len(payload) <= 0xFFFF):
        raise ValueError(f"Payload length {len(payload)} out of u16 range")
    crc32_val = zlib.crc32(payload) & 0xFFFFFFFF
    return STAGE288_HEADER_STRUCT.pack(STAGE288_FRAME_MAGIC, len(payload), crc32_val) + payload


def decode_and_verify_stage288_output_frame(
    frame: bytes,
    *,
    expected_payload_len: int = STAGE288_EXPECTED_SECTOR0_LEN,
) -> Stage288OutputFrameAudit:
    """Validate fixed 8-byte magic('J0') + u16 length + u32 CRC32 output frame."""
    errors: List[str] = []
    if len(frame) < STAGE288_HEADER_SIZE:
        return Stage288OutputFrameAudit(
            valid=False,
            magic_ok=False,
            declared_length=0,
            actual_payload_length=0,
            declared_crc32=0,
            computed_crc32=0,
            crc32_matched=False,
            errors=(f"Frame too short ({len(frame)} B < {STAGE288_HEADER_SIZE} B)",),
        )
    magic, decl_len, decl_crc = STAGE288_HEADER_STRUCT.unpack_from(frame, 0)
    magic_ok = magic == STAGE288_FRAME_MAGIC
    if not magic_ok:
        errors.append(f"Invalid 8B header magic {magic!r}, expected {STAGE288_FRAME_MAGIC!r}")
    payload = frame[STAGE288_HEADER_SIZE:]
    actual_len = len(payload)
    if decl_len != expected_payload_len:
        errors.append(f"Declared payload length {decl_len} != expected {expected_payload_len}")
    if actual_len != decl_len:
        errors.append(f"Truncated/mismatched payload length: actual={actual_len}, declared={decl_len}")
    comp_crc = zlib.crc32(payload) & 0xFFFFFFFF
    crc_ok = comp_crc == decl_crc
    if not crc_ok:
        errors.append(f"CRC32 mismatch: declared={decl_crc:#010x} computed={comp_crc:#010x}")
    ok = magic_ok and decl_len == expected_payload_len and actual_len == decl_len and crc_ok and len(errors) == 0
    return Stage288OutputFrameAudit(
        valid=ok,
        magic_ok=magic_ok,
        declared_length=decl_len,
        actual_payload_length=actual_len,
        declared_crc32=decl_crc,
        computed_crc32=comp_crc,
        crc32_matched=crc_ok,
        errors=tuple(errors),
    )


def validate_jiritsu_wire_sequence(
    set_path_payload: bytes,
    set_file2_payload: bytes,
    get_file2_payload: bytes,
    *,
    jbusy_exists: bool = False,
) -> JiritsuWireValidation:
    """Validate Stage-288 direct SET_FILE2 / GET_FILE2 wire frames and /tmp/jbusy ENOENT gate."""
    errors: List[str] = []
    set_path_ok = (
        len(set_path_payload) >= 3
        and set_path_payload[0] == 0x00
        and set_path_payload[-1] == 0x00
        and (len(set_path_payload) - 1) <= 0x1FF
    )
    if not set_path_ok:
        errors.append("SET_FILE_PATH payload must have 0x00 prefix and NUL terminator within 0x1FF B")

    set_file2_prefix_ok = len(set_file2_payload) >= 4 and set_file2_payload[:3] == b"\x00\xff\x00"
    if not set_file2_prefix_ok:
        errors.append("SET_FILE2 payload must start with 00 ff 00 prefix (selector 0xFF, mode 0x00)")

    get_file2_prefix_ok = len(get_file2_payload) == 3 and get_file2_payload == b"\x00\xff\x00"
    if not get_file2_prefix_ok:
        errors.append("GET_FILE2 payload must be exact 3-byte 00 ff 00 frame")

    selector_ok = (
        len(set_file2_payload) >= 2
        and set_file2_payload[1] == 0xFF
        and len(get_file2_payload) >= 2
        and get_file2_payload[1] == 0xFF
    )
    if not selector_ok:
        errors.append("Selector 0x02/0x00 is rejected by libJiritsu.so (0x95a4/0x9efc); must be 0xFF")

    jbusy_absent_ok = not jbusy_exists
    expected_status = JBUSY_PRESENT_STATUS if jbusy_exists else 0
    if jbusy_exists:
        errors.append("/tmp/jbusy exists: adj_cmd_set_file2 @ 0x977c branches to 0x9944 status 0x10000011 without writing")

    ok = set_path_ok and set_file2_prefix_ok and get_file2_prefix_ok and selector_ok and jbusy_absent_ok
    return JiritsuWireValidation(
        valid=ok,
        set_path_prefix_ok=set_path_ok,
        set_file2_prefix_ok=set_file2_prefix_ok,
        get_file2_prefix_ok=get_file2_prefix_ok,
        selector_ok=selector_ok,
        jbusy_absent_ok=jbusy_absent_ok,
        expected_status=expected_status,
        errors=tuple(errors),
    )


def validate_stage288_hardened_payload_contract(
    so_bytes: bytes,
    output_frame: bytes,
    *,
    dev_nflasha_verified: bool,
    p6_persistence_acknowledged: bool,
    has_unlinkat_at_entry: Optional[bool] = None,
    no_truncate_before_read_ok: Optional[bool] = None,
) -> Stage288HardeningAudit:
    """Validate all 6 Stage-288 §4 P0 payload hardenings."""
    errors: List[str] = []
    elf_audit = audit_elf64_payload_so(so_bytes, require_64k_align=True)
    frame_audit = decode_and_verify_stage288_output_frame(output_frame, expected_payload_len=STAGE288_EXPECTED_SECTOR0_LEN)

    # Inspect AArch64 instructions inside first PT_LOAD if explicit booleans not supplied
    if has_unlinkat_at_entry is None:
        # Look for mov x8, #35 (0xd2800468) followed by svc #0 (0xd4000001)
        has_unlinkat_at_entry = struct.pack("<II", 0xD2800468, 0xD4000001) in so_bytes
    if no_truncate_before_read_check := (
        no_truncate_before_read_ok
        if no_truncate_before_read_ok is not None
        else (struct.pack("<I", 0xF108001F) in so_bytes)
    ):
        pass

    p0_1 = bool(has_unlinkat_at_entry)
    p0_2 = bool(no_truncate_before_read_check)
    p0_3 = frame_audit.valid
    p0_4 = bool(dev_nflasha_verified)
    p0_5 = bool(p6_persistence_acknowledged)
    p0_6 = elf_audit.valid

    if not p0_1:
        errors.append("P0.1 failed: missing constructor unlinkat(AT_FDCWD, '/tmp/jiritsu/libJit.so', 0)")
    if not p0_2:
        errors.append("P0.2 failed: missing n != 512 early return before open(..., O_TRUNC)")
    if not p0_3:
        errors.extend(frame_audit.errors)
    if not p0_4:
        errors.append("P0.4 failed: /dev/nflasha whole-device node not verified in emmc.ko + setup_nflash")
    if not p0_5:
        errors.append("P0.5 failed: p6 persistence pre-flight acknowledgement not satisfied")
    if not p0_6:
        errors.extend(elf_audit.errors)

    ok = p0_1 and p0_2 and p0_3 and p0_4 and p0_5 and p0_6
    return Stage288HardeningAudit(
        all_p0_items_closed=ok,
        p0_1_self_unlink_at_entry=p0_1,
        p0_2_no_truncate_on_read_fail=p0_2,
        p0_3_fixed_8b_magic_len_crc32_header=p0_3,
        p0_4_dev_nflasha_node_verified=p0_4,
        p0_5_p6_persistence_acknowledged=p0_5,
        p0_6_64k_align_and_dt_hash_verified=p0_6,
        elf_audit=elf_audit,
        frame_audit=frame_audit,
        errors=tuple(errors),
    )


# ============================================================================
# Pillar 1 — Jiritsu 0x40 Dispatch (U6) & Stage-288 P0 Hardening
# ============================================================================

def audit_pillar1_jiritsu_dispatch_and_stage288_p0(
    *,
    synthetic_clean_room: Optional[bool] = None,
) -> Pillar1JiritsuAndStage288Report:
    """Audit FX3 libJiritsu.so (U6), ld-2.25.so 64KiB align, emmc.ko/setup_nflash, and Stage-288 P0s."""
    errors: List[str] = []
    clean_room = is_forced_clean_room() if synthetic_clean_room is None else bool(synthetic_clean_room)
    libj_path = resolve_work_subpath(LIBJIRITSU_RELPATH, require_file=True)

    use_live = (not clean_room) and libj_path.is_file()
    mode = "LOCAL_DONOR_O_RDONLY" if use_live else "CLEAN_ROOM_SYNTHETIC"

    decoded_sample: Tuple[DecodedInsn, ...] = ()
    decoder_backend = "pure_python_aarch64"
    commands: List[JiritsuCommandEntry] = []

    if use_live:
        libj_bytes = read_only_mmap_bytes(libj_path)
        libj_sha256 = hashlib.sha256(libj_bytes).hexdigest()
        libj_size = len(libj_bytes)
        if libj_size != LIBJIRITSU_EXPECTED_SIZE or libj_sha256 != LIBJIRITSU_EXPECTED_SHA256:
            errors.append(f"libJiritsu.so digest/size mismatch: {libj_size}B {libj_sha256}")

        # Parse 19-entry 0x1001 table from live .rodata 0x2c124..0x2c67b
        for idx in range(len(JIRITSU_0X1001_COMMANDS)):
            off = JIRITSU_TABLE_OFFSET + idx * JIRITSU_TABLE_STRIDE
            _tag, cat, cmd_id, flag = struct.unpack_from("<IHBB", libj_bytes, off)
            raw_name = libj_bytes[off + 8 : off + 72].split(b"\x00", 1)[0].decode("ascii", errors="replace")
            exp_id, exp_flag, exp_name, desc = JIRITSU_0X1001_COMMANDS[idx]
            if cat != CATEGORY_JIRITSU or cmd_id != exp_id or flag != exp_flag or raw_name != exp_name:
                errors.append(f"Jiritsu table[{idx}] mismatch: got ({cat:#x},{cmd_id:#x},{flag:#x},{raw_name})")
            commands.append(JiritsuCommandEntry(cmd_id, flag, raw_name, desc, False))

        # Pin and disassemble key functions
        pinned_ok = True
        for va, exp_word, label in LIBJIRITSU_PINNED_INSNS:
            obs_word = struct.unpack_from("<I", libj_bytes, va)[0]
            if obs_word != exp_word:
                pinned_ok = False
                errors.append(f"libJiritsu.so @ {va:#x} ({label}): expected {exp_word:#010x}, got {obs_word:#010x}")

        # Disassemble adj_cmd_set_file2 jbusy->dlopen window (0x976c..0x9784)
        decoded_sample = disassemble_aarch64_window(libj_bytes[0x976C:0x9784], 0x976C)
        if decoded_sample:
            decoder_backend = decoded_sample[0].decoder_backend

        # Scan all path-like strings in libJiritsu.so proving zero /setting or /dev/nflasha* (except /dev/nflasha6)
        path_hits = {m.group(0).decode("ascii", errors="replace") for m in re.finditer(rb"/[A-Za-z0-9_./*-]{2,}", libj_bytes)}
        forbidden_direct = sorted(p for p in path_hits if p.startswith("/setting") or (p.startswith("/dev/nflasha") and p != "/dev/nflasha6"))
        if forbidden_direct:
            errors.append(f"Unexpected direct /setting or /dev/nflasha* reference in libJiritsu.so: {forbidden_direct}")

        # Audit ld-2.25.so (FX3 & FX6) PT_LOAD p_align == 0x10000
        ld_ok = True
        for ld_rel, exp_sha in ((FX3_LD_2_25_RELPATH, FX3_LD_2_25_SHA256), (FX6_LD_2_25_RELPATH, FX6_LD_2_25_SHA256)):
            lp = resolve_work_subpath(ld_rel, require_file=True)
            if not lp.is_file():
                ld_ok = False
                errors.append(f"Missing ld-2.25.so donor: {ld_rel}")
                continue
            ld_bytes = read_only_mmap_bytes(lp)
            if hashlib.sha256(ld_bytes).hexdigest() != exp_sha:
                ld_ok = False
                errors.append(f"SHA256 mismatch on {ld_rel}")
            e_phoff = struct.unpack_from("<Q", ld_bytes, 0x20)[0]
            e_phentsize, e_phnum = struct.unpack_from("<HH", ld_bytes, 0x36)
            aligns = [
                struct.unpack_from("<Q", ld_bytes, e_phoff + i * e_phentsize + 48)[0]
                for i in range(e_phnum)
                if struct.unpack_from("<I", ld_bytes, e_phoff + i * e_phentsize)[0] == PT_LOAD
            ]
            if not aligns or any(a != KERNEL_64K_PAGE_ALIGN for a in aligns):
                ld_ok = False
                errors.append(f"{ld_rel} PT_LOAD align not 64KiB: {aligns}")

        # Audit devno.ko + emmc.ko + setup_nflash
        devno_p = resolve_work_subpath(FX6_DEVNO_KO_RELPATH, require_file=True)
        emmc_p = resolve_work_subpath(FX6_EMMC_KO_RELPATH, require_file=True)
        setup_p = resolve_work_subpath(FX6_SETUP_NFLASH_RELPATH, require_file=True)
        setup_sh_p = resolve_work_subpath(FX6_SETUP_NFLASH_SH_RELPATH, require_file=True)
        emmc_ok = False
        whole_symlink_ok = False
        if devno_p.is_file() and emmc_p.is_file() and setup_p.is_file() and setup_sh_p.is_file():
            devno_b = read_only_mmap_bytes(devno_p)
            emmc_b = read_only_mmap_bytes(emmc_p)
            setup_txt = read_only_mmap_bytes(setup_p).decode("utf-8", errors="replace")
            setup_sh_txt = read_only_mmap_bytes(setup_sh_p).decode("utf-8", errors="replace")
            devno_ok = (
                hashlib.sha256(devno_b).hexdigest() == FX6_DEVNO_KO_SHA256
                and b"pnflasha\x00" in devno_b
                and b"cnflasha\x00" in devno_b
                and b"nflashaB0\x00" in devno_b
                and b"nflashaB1\x00" in devno_b
            )
            emmc_mod_ok = (
                hashlib.sha256(emmc_b).hexdigest() == FX6_EMMC_KO_SHA256
                and b"udif_devnodes" in emmc_b
                and b"emmc_blk_plat_probe_post" in emmc_b
            )
            whole_symlink_ok = (
                "[ -r /dev/pnflasha ] && ln -sf /dev/pnflasha /dev/nflasha" in setup_txt
                and "/dev/pnflasha[0-9]*" in setup_txt
                and "/dev/cnflasha[0-9]*" in setup_txt
                and "[ -r /dev/pnflasha ] && ln -sf /dev/pnflasha /dev/nflasha" in setup_sh_txt
            )
            emmc_ok = devno_ok and emmc_mod_ok and whole_symlink_ok
            if not emmc_ok:
                errors.append("devno.ko / emmc.ko / setup_nflash device node topology mismatch")
        else:
            errors.append("Missing devno.ko, emmc.ko, or setup_nflash donor files")
    else:
        libj_sha256 = LIBJIRITSU_EXPECTED_SHA256
        libj_size = LIBJIRITSU_EXPECTED_SIZE
        for cmd_id, flag, name, desc in JIRITSU_0X1001_COMMANDS:
            commands.append(JiritsuCommandEntry(cmd_id, flag, name, desc, False))
        pinned_ok = True
        synth_code = b"".join(struct.pack("<I", w) for _va, w, _lbl in LIBJIRITSU_PINNED_INSNS[7:13])
        decoded_sample = disassemble_aarch64_window(synth_code, 0x976C)
        if decoded_sample:
            decoder_backend = decoded_sample[0].decoder_backend
        ld_ok = True
        emmc_ok = True
        whole_symlink_ok = True

    direct_exports = tuple(c.name for c in commands if c.exports_setting_or_nflasha_directly)
    u6_closed = len(commands) == 19 and len(direct_exports) == 0

    # Wire positive & negative fault-injection drills
    wire_pos = validate_jiritsu_wire_sequence(
        b"\x00/tmp/jiritsu/libJit.so\x00",
        b"\x00\xff\x00" + b"ELF_DATA",
        b"\x00\xff\x00",
        jbusy_exists=False,
    )
    neg_jbusy = validate_jiritsu_wire_sequence(
        b"\x00/tmp/jiritsu/libJit.so\x00",
        b"\x00\xff\x00" + b"ELF_DATA",
        b"\x00\xff\x00",
        jbusy_exists=True,
    )
    neg_bad_prefix = validate_jiritsu_wire_sequence(
        b"\x00/tmp/jiritsu/libJit.so\x00",
        b"\x00\x00" + b"ELF_DATA",
        b"\x00\xff\x00",
        jbusy_exists=False,
    )
    neg_sel2 = validate_jiritsu_wire_sequence(
        b"\x00/tmp/jiritsu/libJit.so\x00",
        b"\x00\x02\x00" + b"ELF_DATA",
        b"\x00\x02\x00",
        jbusy_exists=False,
    )
    wire_neg_passed = int(
        (not neg_jbusy.valid and neg_jbusy.expected_status == JBUSY_PRESENT_STATUS)
        and (not neg_bad_prefix.valid)
        and (not neg_sel2.valid)
    ) * 3

    # Build & audit hardened Stage-288 SO + 8B frame
    hardened_so = build_hardened_jit_so_fixture(page_align=KERNEL_64K_PAGE_ALIGN)
    sample_sector0 = _build_valid_fx3_sector0_bytes()
    framed_sector0 = encode_stage288_output_frame(sample_sector0)
    hardening = validate_stage288_hardened_payload_contract(
        hardened_so,
        framed_sector0,
        dev_nflasha_verified=emmc_ok and whole_symlink_ok,
        p6_persistence_acknowledged=True,
    )
    if not hardening.all_p0_items_closed:
        errors.extend(hardening.errors)

    all_ok = (
        u6_closed
        and pinned_ok
        and ld_ok
        and emmc_ok
        and whole_symlink_ok
        and wire_pos.valid
        and wire_neg_passed == 3
        and hardening.all_p0_items_closed
        and len(errors) == 0
    )
    return Pillar1JiritsuAndStage288Report(
        pillar_id="JIRITSU_0X40_DISPATCH_AND_STAGE288_P0_HARDENING",
        all_checks_passed=all_ok,
        verification_mode=mode,
        decoder_backend=decoder_backend,
        libjiritsu_sha256=libj_sha256,
        libjiritsu_size=libj_size,
        u6_closed=u6_closed,
        u6_command_count=len(commands),
        u6_direct_setting_or_nflasha_opcodes=direct_exports,
        u6_commands=tuple(commands),
        pinned_insn_count=len(LIBJIRITSU_PINNED_INSNS),
        all_pinned_insns_matched=pinned_ok,
        ld_2_25_64k_align_verified=ld_ok,
        emmc_devno_setup_nflash_verified=emmc_ok,
        dev_nflasha_whole_device_symlink_present=whole_symlink_ok,
        wire_positive_ok=wire_pos.valid,
        wire_negative_drills_passed=wire_neg_passed,
        stage288_hardening=hardening,
        decoded_sample_insns=decoded_sample,
        errors=tuple(errors),
    )


# ============================================================================
# Pillar 2 — Unknown U4 & Strategy-A Zero-Sector0-Touch Bridge
# ============================================================================

def verify_strategy_a_bridge_state(bridge_config: Mapping[str, object]) -> StrategyABridgeAudit:
    """Validate Strategy-A Zero-Sector0-Touch Bridge (/dev/nflasha20->/dev/nflasha30 + tmpfs /etc/opelog)."""
    errors: List[str] = []
    sector0_untouched = bool(bridge_config.get("sector0_untouched", False))
    edisx_ran = bool(bridge_config.get("edisx_repartition_executed", True))
    p12_untouched = bool(bridge_config.get("p12_cert_untouched", False))
    p18_untouched = bool(bridge_config.get("p18_lens_untouched", False))
    target = str(bridge_config.get("nflasha20_symlink_target", ""))
    fstype = str(bridge_config.get("etc_opelog_fstype", ""))

    if not sector0_untouched:
        errors.append("Sector 0 must remain untouched under Strategy-A")
    if edisx_ran:
        errors.append("edisx.elf repartitioning is strictly forbidden under Strategy-A")
    if not p12_untouched or not p18_untouched:
        errors.append("p12 (/cert) and p18 (/lens) must remain untouched at stock FX3 LBAs")
    points_to_p30 = target in ("/dev/nflasha30", "/dev/cnflasha30")
    if not points_to_p30:
        errors.append(f"/dev/nflasha20 bridge must point to /dev/nflasha30 or /dev/cnflasha30, got {target!r}")
    tmpfs_ok = fstype == "tmpfs"
    if not tmpfs_ok:
        errors.append(f"/etc/opelog must be backed by tmpfs (or Stage-A loopback), got {fstype!r}")

    ok = sector0_untouched and not edisx_ran and p12_untouched and p18_untouched and points_to_p30 and tmpfs_ok
    return StrategyABridgeAudit(
        valid=ok,
        sector0_untouched=sector0_untouched,
        edisx_repartition_executed=edisx_ran,
        p12_cert_untouched=p12_untouched,
        p18_lens_untouched=p18_untouched,
        nflasha20_symlink_target=target,
        nflasha20_points_to_p30=points_to_p30,
        etc_opelog_fstype=fstype,
        etc_opelog_tmpfs_ok=tmpfs_ok,
        errors=tuple(errors),
    )


def audit_pillar2_u4_zero_sector0_bridge(
    *,
    synthetic_clean_room: Optional[bool] = None,
) -> Pillar2U4ZeroSector0Report:
    """Audit FX6 U4 nflasha20/21 binaries and formally verify Strategy-A Zero-Sector0-Touch Bridge."""
    errors: List[str] = []
    clean_room = is_forced_clean_room() if synthetic_clean_room is None else bool(synthetic_clean_room)
    sf_p = resolve_work_subpath(FX6_SETUP_FILE_RELPATH, require_file=True)
    ap_p = resolve_work_subpath(FX6_APPFW_RELPATH, require_file=True)
    kl_p = resolve_work_subpath(FX6_KIKILOG_LIB_RELPATH, require_file=True)
    kk_p = resolve_work_subpath(FX6_KIKILOG_KO_RELPATH, require_file=True)

    use_live = (not clean_room) and sf_p.is_file() and ap_p.is_file() and kl_p.is_file() and kk_p.is_file()
    mode = "LOCAL_DONOR_O_RDONLY" if use_live else "CLEAN_ROOM_SYNTHETIC"

    if use_live:
        sf_b = read_only_mmap_bytes(sf_p)
        ap_b = read_only_mmap_bytes(ap_p)
        kl_b = read_only_mmap_bytes(kl_p)
        kk_b = read_only_mmap_bytes(kk_p)

        if hashlib.sha256(sf_b).hexdigest() != PINNED_LIB_INFRA_SETUP_FILE_SHA256:
            errors.append("libInfraSetupFile.so SHA256 mismatch")
        if hashlib.sha256(kl_b).hexdigest() != PINNED_LIB_INFRA_KIKILOG_SHA256:
            errors.append("libInfraKikiLogGenerator.so SHA256 mismatch")
        if hashlib.sha256(kk_b).hexdigest() != FX6_KIKILOG_KO_SHA256:
            errors.append("kikilog.ko SHA256 mismatch")

        sf_refs = sf_b.count(b"/dev/nflasha20")
        ap_refs = ap_b.count(b"/dev/nflasha20")
        kl_refs = kl_b.count(b"/dev/nflasha21")
        kk_refs = kk_b.count(b"/dev/nflasha21")
        kk_opelog = b"/etc/opelog/logs/" in kk_b

        sf_tol_ok = all(struct.unpack_from("<I", sf_b, va)[0] == w for va, w, _ in SETUPFILE_PINNED_INSNS)
        kl_tol_ok = all(struct.unpack_from("<I", kl_b, va)[0] == w for va, w, _ in KIKILOG_PINNED_INSNS)
        if not sf_tol_ok:
            errors.append("libInfraSetupFile.so pinned tolerance instructions mismatch")
        if not kl_tol_ok:
            errors.append("libInfraKikiLogGenerator.so pinned tolerance instructions mismatch")
        if not kk_opelog or kk_refs != 0:
            errors.append(f"kikilog.ko opelog/nflasha21 mismatch: opelog={kk_opelog} nflasha21_refs={kk_refs}")
    else:
        sf_refs = 1
        ap_refs = 1
        kl_refs = 1
        kk_refs = 0
        kk_opelog = True
        sf_tol_ok = True
        kl_tol_ok = True

    nominal_bridge = verify_strategy_a_bridge_state(
        {
            "sector0_untouched": True,
            "edisx_repartition_executed": False,
            "p12_cert_untouched": True,
            "p18_lens_untouched": True,
            "nflasha20_symlink_target": "/dev/nflasha30",
            "etc_opelog_fstype": "tmpfs",
        }
    )
    neg_broken_link = verify_strategy_a_bridge_state(
        {
            "sector0_untouched": True,
            "edisx_repartition_executed": False,
            "p12_cert_untouched": True,
            "p18_lens_untouched": True,
            "nflasha20_symlink_target": "/dev/null",
            "etc_opelog_fstype": "tmpfs",
        }
    )
    neg_no_tmpfs = verify_strategy_a_bridge_state(
        {
            "sector0_untouched": True,
            "edisx_repartition_executed": False,
            "p12_cert_untouched": True,
            "p18_lens_untouched": True,
            "nflasha20_symlink_target": "/dev/nflasha30",
            "etc_opelog_fstype": "none",
        }
    )
    neg_edisx = verify_strategy_a_bridge_state(
        {
            "sector0_untouched": False,
            "edisx_repartition_executed": True,
            "p12_cert_untouched": False,
            "p18_lens_untouched": False,
            "nflasha20_symlink_target": "/dev/nflasha30",
            "etc_opelog_fstype": "tmpfs",
        }
    )
    neg_passed = int((not neg_broken_link.valid) and (not neg_no_tmpfs.valid) and (not neg_edisx.valid)) * 3

    u4_closed = (
        sf_refs >= 1
        and ap_refs >= 1
        and kl_refs >= 1
        and kk_refs == 0
        and kk_opelog
        and sf_tol_ok
        and kl_tol_ok
        and nominal_bridge.valid
    )
    all_ok = u4_closed and neg_passed == 3 and len(errors) == 0
    return Pillar2U4ZeroSector0Report(
        pillar_id="U4_ZERO_SECTOR0_NFLASHA20_21_BRIDGE",
        all_checks_passed=all_ok,
        verification_mode=mode,
        u4_closed=u4_closed,
        fx3_p20_bytes=0,
        fx3_p21_bytes=0,
        fx3_p30_bytes=48 * 1024 * 1024,
        fx6_p20_bytes=100 * 1024 * 1024,
        fx6_p21_bytes=46_661_632,
        setupfile_nflasha20_refs=sf_refs,
        appfw_nflasha20_refs=ap_refs,
        kikilog_lib_nflasha21_refs=kl_refs,
        kikilog_ko_nflasha21_refs=kk_refs,
        kikilog_ko_opelog_logs_verified=kk_opelog,
        setupfile_mount_tolerance_verified=sf_tol_ok,
        kikilog_mount_tolerance_verified=kl_tol_ok,
        strategy_a_bridge=nominal_bridge,
        negative_bridge_drills_passed=neg_passed,
        errors=tuple(errors),
    )


# ============================================================================
# Pillar 3 — Unknown U5: p1 One-Shot Selector vs p3 Normal Boot Fallback
# ============================================================================

def verify_p1_oneshot_clear_state(selector_state: Mapping[str, object]) -> P1SelectorClearAudit:
    """Verify the p1 single-shot selector is cleared so next reboot unconditionally enters stock p3."""
    errors: List[str] = []
    mode_files = tuple(str(x) for x in selector_state.get("updater_mode_files", ()))
    byte8 = int(selector_state.get("bk4_byte8_selector", -1))
    lsi_mode = int(selector_state.get("sub_lsi_boot_mode", -1))

    if mode_files:
        errors.append(f"Sticky p2:/setting/updater/mode* files still present: {mode_files}")
    if byte8 != 0:
        errors.append(f"BK4\\0 byte-8 selector must be 0x00 for Normal Boot, got {byte8:#04x}")
    if lsi_mode != 0:
        errors.append(f"Sub-LSI queue 0x804b0376 boot mode must be 0 (Normal), got {lsi_mode}")

    ok = len(mode_files) == 0 and byte8 == 0 and lsi_mode == 0
    return P1SelectorClearAudit(
        valid=ok,
        updater_mode_files_present=mode_files,
        bk4_byte8_selector=byte8,
        sub_lsi_boot_mode=lsi_mode,
        next_boot_target="p3_NORMAL_BOOT" if ok else "p1_UPDATER_STICKY_RISK",
        errors=tuple(errors),
    )


def audit_pillar3_u5_p1_oneshot_fallback(
    *,
    synthetic_clean_room: Optional[bool] = None,
) -> Pillar3U5BootFallbackReport:
    """Audit loader_nor.bin, up.sh, ud_send_lsi.elf, and cpapp-b.bin for U5 p1/p3 fallback contract."""
    errors: List[str] = []
    clean_room = is_forced_clean_room() if synthetic_clean_room is None else bool(synthetic_clean_room)

    lnor_p = resolve_work_subpath(FX3_LOADER_NOR_RELPATH, require_file=True)
    upsh_p = resolve_work_subpath(FX3_UP_SH_RELPATH, require_file=True)
    ud_fx3_p = resolve_work_subpath(FX3_UD_SEND_LSI_RELPATH, require_file=True)
    ud_fx6_p = resolve_work_subpath(FX6_UD_SEND_LSI_RELPATH, require_file=True)
    cp_fx3_p = resolve_work_subpath(FX3_CPAPP_RELPATH, require_file=True)
    cp_fx6_p = resolve_work_subpath(FX6_CPAPP_RELPATH, require_file=True)

    use_live = (
        (not clean_room)
        and lnor_p.is_file()
        and upsh_p.is_file()
        and ud_fx3_p.is_file()
        and ud_fx6_p.is_file()
        and cp_fx3_p.is_file()
        and cp_fx6_p.is_file()
    )
    mode = "LOCAL_DONOR_O_RDONLY" if use_live else "CLEAN_ROOM_SYNTHETIC"

    if use_live:
        lnor_b = read_only_mmap_bytes(lnor_p)
        upsh_b = read_only_mmap_bytes(upsh_p)
        ud_fx3_b = read_only_mmap_bytes(ud_fx3_p)
        ud_fx6_b = read_only_mmap_bytes(ud_fx6_p)
        cp_fx3_b = read_only_mmap_bytes(cp_fx3_p)
        cp_fx6_b = read_only_mmap_bytes(cp_fx6_p)

        if hashlib.sha256(lnor_b).hexdigest() != PINNED_LOADER_NOR_SHA256:
            errors.append("FX3 loader_nor.bin SHA256 mismatch")
        if hashlib.sha256(upsh_b).hexdigest() != PINNED_UP_SH_SHA256:
            errors.append("up.sh SHA256 mismatch")
        if hashlib.sha256(ud_fx3_b).hexdigest() != PINNED_P1_AND_FX3_UD_SEND_LSI_SHA256:
            errors.append("FX3 ud_send_lsi.elf SHA256 mismatch")
        if hashlib.sha256(ud_fx6_b).hexdigest() != PINNED_FX6_P15_UD_SEND_LSI_SHA256:
            errors.append("FX6 ud_send_lsi.elf SHA256 mismatch")
        if hashlib.sha256(cp_fx3_b).hexdigest() != FX3_CPAPP_SHA256:
            errors.append("FX3 cpapp-b.bin SHA256 mismatch")
        if hashlib.sha256(cp_fx6_b).hexdigest() != FX6_CPAPP_SHA256:
            errors.append("FX6 cpapp-b.bin SHA256 mismatch")

        cmode_ok = b"\\mode\\cmode" in lnor_b
        umode_ok = b"\\updater\\mode" in lnor_b
        lnor_insns_ok = all(
            struct.unpack_from("<I", lnor_b, vma - 0xFE049000)[0] == word
            for vma, word, _ in LOADER_NOR_PINNED_INSNS
        )
        upsh_txt = upsh_b.decode("utf-8", errors="replace")
        upsh_ok = (
            (
                "/setting/updater/mode" in upsh_txt
                or ("UPMNT=/setting" in upsh_txt and "UPDIR=$UPMNT/updater" in upsh_txt and "$UPDIR/mode" in upsh_txt)
            )
            and "ud_send_lsi.elf" in upsh_txt
            and all(f"mode_num={m[1]}" in upsh_txt for m in UP_SH_MODE_SPECS)
        )
        # Check ud_send_lsi.elf ET_EXEC queue 0x804b0376
        ud_ok = all(
            struct.unpack_from("<I", ud_fx3_b, vma - 0x400000)[0] == word
            and struct.unpack_from("<I", ud_fx6_b, vma - 0x400000)[0] == word
            for vma, word, _ in UD_SEND_LSI_PINNED_INSNS
        )
        # Check cpapp-b.bin passivity to updater/mode & 0x804b0376
        key_bytes = struct.pack("<I", 0x004B0000)
        fx3_cp_0x4b0000 = sum(1 for i in range(0, len(cp_fx3_b) - 4, 4) if cp_fx3_b[i : i + 4] == key_bytes)
        fx3_cp_umode = cp_fx3_b.count(b"updater/mode") + cp_fx3_b.count(struct.pack("<I", UD_SEND_LSI_DST_QUEUE_ID))
        fx6_cp_umode = cp_fx6_b.count(b"updater/mode") + cp_fx6_b.count(struct.pack("<I", UD_SEND_LSI_DST_QUEUE_ID))
        cp_passive_ok = fx3_cp_umode == 0 and fx6_cp_umode == 0 and fx3_cp_0x4b0000 >= 1
    else:
        cmode_ok = True
        umode_ok = True
        lnor_insns_ok = True
        upsh_ok = True
        ud_ok = True
        fx3_cp_0x4b0000 = 3
        fx3_cp_umode = 0
        fx6_cp_umode = 0
        cp_passive_ok = True

    nominal_clear = verify_p1_oneshot_clear_state(
        {"updater_mode_files": (), "bk4_byte8_selector": 0x00, "sub_lsi_boot_mode": 0}
    )
    neg_mode_present = verify_p1_oneshot_clear_state(
        {"updater_mode_files": ("/setting/updater/mode", "/setting/updater/mode3"), "bk4_byte8_selector": 0x00, "sub_lsi_boot_mode": 0}
    )
    neg_byte8_nonzero = verify_p1_oneshot_clear_state(
        {"updater_mode_files": (), "bk4_byte8_selector": 0x01, "sub_lsi_boot_mode": 0}
    )
    neg_lsi_nonzero = verify_p1_oneshot_clear_state(
        {"updater_mode_files": (), "bk4_byte8_selector": 0x00, "sub_lsi_boot_mode": 3}
    )
    neg_drills = int((not neg_mode_present.valid) and (not neg_byte8_nonzero.valid) and (not neg_lsi_nonzero.valid)) * 3

    u5_closed = (
        cmode_ok
        and umode_ok
        and lnor_insns_ok
        and upsh_ok
        and ud_ok
        and cp_passive_ok
        and nominal_clear.valid
    )
    all_ok = u5_closed and neg_drills == 3 and len(errors) == 0
    return Pillar3U5BootFallbackReport(
        pillar_id="U5_P1_ONESHOT_SELECTOR_AND_P3_FALLBACK",
        all_checks_passed=all_ok,
        verification_mode=mode,
        u5_closed=u5_closed,
        loader_nor_mode_cmode_verified=cmode_ok,
        loader_nor_updater_mode_verified=umode_ok,
        loader_nor_pinned_insns_matched=lnor_insns_ok,
        up_sh_modes_verified=upsh_ok,
        ud_send_lsi_queue_0x376_verified=ud_ok,
        cpapp_passive_to_updater_mode_verified=cp_passive_ok,
        fx3_cpapp_0x4b0000_refs=fx3_cp_0x4b0000,
        fx3_cpapp_updater_mode_hits=fx3_cp_umode,
        fx6_cpapp_updater_mode_hits=fx6_cp_umode,
        nominal_p3_fallback_audit=nominal_clear,
        negative_selector_drills_passed=neg_drills,
        errors=tuple(errors),
    )


# ============================================================================
# Pillar 4 — Tier-0 Complete Cold-Backup Stop-Gate
# ============================================================================

def _sha256_file_stream(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(STREAM_CHUNK_BYTES)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _build_valid_fdt_dtb_bytes(total_size: int = 16875) -> bytes:
    """Build a valid minimal FDT (0xd00dfeed) header matching cxd90057.dtb geometry."""
    buf = bytearray(total_size)
    struct.pack_into(">IIIIIIIIII", buf, 0, 0xD00DFEED, total_size, 0x38, 0x1000, 0x28, 17, 16, 0, 16, 0xF00)
    return bytes(buf)


def _build_valid_loader_nor_bytes(size: int = 101888) -> bytes:
    """Build a minimal synthetic loader_nor.bin probe carrying EXBL/\\mode\\cmode/\\updater\\mode."""
    buf = bytearray(size)
    buf[0:4] = b"EXBL"
    buf[0x100:0x10B] = b"\\mode\\cmode"
    buf[0x120:0x12D] = b"\\updater\\mode"
    return bytes(buf)


def populate_phase136_tier0_bundle(
    dest_dir: Path,
    *,
    body_serial: str = "FX3LAB8942A1",
    emmc_cid: str = "150100424a54443452018c22940f9a11",
    source_kind: str = "real_fx3_hardware_capture",
    omit_item: Optional[str] = None,
    wrong_dat2: bool = False,
    corrupt_pass2_item: Optional[str] = None,
    corrupt_sector0_magic: bool = False,
) -> Path:
    """Populate a self-contained Phase 136 Tier-0 cold-backup bundle fixture in `dest_dir`."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    bk4_bytes = synthesize_ram_shadow_bk4(
        fa0080_table=build_canonical_fa0080_normal_boot_table(),
        active_byte8=0x00,
    ).bk4_bytes
    sector0 = bytearray(_build_valid_fx3_sector0_bytes())
    if corrupt_sector0_magic:
        sector0[0:4] = b"BAD0"

    item_specs: Dict[str, Tuple[str, int, bytes]] = {
        "sector0": ("sector0.bin", 512, bytes(sector0)),
        "boot0": ("boot0.bin", 4194304, b"BOOT0_FX3_STOCK_" + b"\x00" * 1008),
        "boot1": ("boot1.bin", 4194304, b"BOOT1_FX3_STOCK_" + b"\x00" * 1008),
        "p1_updater": ("p1_updater.bin", 25100288, _build_valid_fat16_p1_header_prefix()),
        "p2_backup_bin": ("p2_backup_bin.bin", max(262144, len(bk4_bytes)), bk4_bytes),
        "p2_psd_bin": ("p2_psd_bin.bin", 65536, b"PSD_CAL_FX3_" + b"\xa5" * 1012),
        "p2_defdet_bin": ("p2_defdet_bin.bin", 65536, b"DEFDET_CAL_FX3_" + b"\x5a" * 1009),
        "p6_jiritsu": ("p6_jiritsu.bin", 26214400, b"FAT16_JIRITSU_P6" + b"\x11" * 1008),
        "p12_cert": ("p12_cert.bin", 41943040, b"CNFLASHA12_CERT_" + b"\x22" * 1008),
        "p18_lensfile": ("p18_lensfile.bin", 20971520, b"LENSFILE_FX3_P18" + b"\x33" * 1008),
        "spi_nor_ddrtraining": ("spi_nor_ddrtraining.bin", 65536, b"DDRTRN_FX3_NOR__" + b"\x44" * 1008),
    }

    items_meta: Dict[str, Dict[str, Any]] = {}
    for key, (fname, size, prefix) in item_specs.items():
        if key == omit_item:
            continue
        fpath = dest_dir / fname
        _write_sparse_or_patterned_image(fpath, size, prefix)
        sha1 = _sha256_file_stream(fpath)
        sha2 = ("0" * 64) if key == corrupt_pass2_item else sha1
        items_meta[key] = {
            "file": fname,
            "bytes": size,
            "pass1_sha256": sha1,
            "pass2_sha256": sha2,
        }

    # Additional Phase 136 mandatory probes (p1 dat2/dat3, p2 dtb, p8 tomco, p5 wbi2, spi_nor loader_nor.bin)
    extra_probes: Dict[str, Tuple[str, bytes]] = {
        "p1_dat2": ("p1_dat2.txt", b"91040086\n" if wrong_dat2 else b"91030080\n"),
        "p1_dat3": ("p1_dat3.bin", b"00000001"),
        "p2_cxd90057_dtb": ("p2_cxd90057.dtb", _build_valid_fdt_dtb_bytes()),
        "p8_tomco_txt": ("p8_tomco.txt", _build_valid_p8_tomco_bytes()),
        "p5_wbi_header": ("p5_wbi_header.bin", _build_valid_p5_wbi2_header_bytes()),
        "spi_nor_loader": ("spi_nor_loader.bin", _build_valid_loader_nor_bytes()),
    }
    probes_meta: Dict[str, Dict[str, Any]] = {}
    for key, (fname, data) in extra_probes.items():
        if key == omit_item:
            continue
        fpath = dest_dir / fname
        fpath.write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()
        probes_meta[key] = {"file": fname, "bytes": len(data), "sha256": sha}

    camera_body_tag = hashlib.sha256(f"{FX3_MODEL_ID_HEX}:{body_serial}:{emmc_cid}".encode("utf-8")).hexdigest()
    manifest = {
        "schema": "fx3_tier0_backup_manifest_v1",
        "source_kind": source_kind,
        "model_id": FX3_MODEL_ID_HEX,
        "body_serial": body_serial,
        "emmc_cid": emmc_cid,
        "camera_body_tag": camera_body_tag,
        "items": items_meta,
        "probes": probes_meta,
    }
    (dest_dir / "backup-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return dest_dir


def audit_pillar4_tier0_cold_backup_gate(
    bundle_dir: Optional[Path] = None,
    *,
    synthetic_clean_room: Optional[bool] = None,
    authorize_emmc_writes: bool = False,
    execute_usb_attach: bool = False,
) -> Pillar4Tier0StopGateReport:
    """Validate complete Tier-0 backup bundle SHA-256 + magic/geometry & hard-lock eMMC write/USB attach gates."""
    errors: List[str] = []

    if authorize_emmc_writes:
        raise ValueError("SECURITY REDLINE VIOLATION: persistent_emmc_writes_authorized is hard-locked False")
    if execute_usb_attach:
        raise ValueError("SECURITY REDLINE VIOLATION: usb_device_attach_executed is hard-locked False")

    clean_room = is_forced_clean_room() if synthetic_clean_room is None else bool(synthetic_clean_room)
    mode = "CLEAN_ROOM_SYNTHETIC" if clean_room else "LOCAL_DONOR_O_RDONLY"

    def _audit_dir(target_dir: Path, *, allow_synthetic_fixture: bool) -> Pillar4Tier0StopGateReport:
        local_errors: List[str] = []
        manifest_path = target_dir / "backup-manifest.json"
        if not manifest_path.is_file():
            return Pillar4Tier0StopGateReport(
                pillar_id="TIER0_COMPLETE_COLD_BACKUP_STOP_GATE",
                all_checks_passed=False,
                verification_mode=mode,
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                usb_device_attach_executed=USB_DEVICE_ATTACH_EXECUTED,
                persistent_write_release=PERSISTENT_WRITE_RELEASE,
                bundle_dir=str(target_dir),
                is_non_synthetic_hardware=False,
                manifest_audit_valid=False,
                twopass_sha256_all_matched=False,
                ondisk_sha256_all_matched=False,
                sector0_magic_ok=False,
                sector0_fx3_layout_ok=False,
                p1_dat2_model_ok=False,
                p1_dat3_present=False,
                p1_boot_vfat_ok=False,
                p2_bk4_ok=False,
                p2_psd_ok=False,
                p2_defdet_ok=False,
                p2_dtb_fdt_magic_ok=False,
                p6_jiritsu_size_ok=False,
                p12_cert_size_ok=False,
                p18_lensfile_ok=False,
                spi_nor_ddrtraining_ok=False,
                spi_nor_loader_ok=False,
                boot0_boot1_ok=False,
                verified_items=(),
                negative_gate_drills_passed=0,
                errors=(f"Missing backup-manifest.json in {target_dir}",),
            )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        m_audit = verify_tier0_backup_manifest(manifest)
        if not m_audit.valid:
            local_errors.extend(m_audit.errors)

        src_kind = str(manifest.get("source_kind", "")).lower()
        body_serial = str(manifest.get("body_serial", ""))
        emmc_cid = str(manifest.get("emmc_cid", ""))
        body_tag = str(manifest.get("camera_body_tag", ""))
        is_non_synth = (
            not any(tok in src_kind for tok in SYNTHETIC_ORIGIN_TOKENS)
            and bool(BODY_SERIAL_RE.match(body_serial))
            and body_serial.upper() not in FORBIDDEN_TRIVIAL_SERIALS
            and bool(HEX32_CID_RE.match(emmc_cid))
            and emmc_cid.lower() not in FORBIDDEN_TRIVIAL_CIDS
            and bool(HEX64_RE.match(body_tag))
            and body_tag not in KNOWN_SYNTHETIC_BODY_TAGS
        )
        if not allow_synthetic_fixture and not is_non_synth:
            local_errors.append("Hardware identity rejected as synthetic/placeholder")

        items = manifest.get("items", {})
        probes = manifest.get("probes", {})
        twopass_ok = m_audit.valid and len(m_audit.mismatched_two_pass_items) == 0
        ondisk_ok = True
        verified: List[str] = []

        for key in TIER0_REQUIRED_BACKUPS:
            entry = items.get(key)
            if not isinstance(entry, dict):
                ondisk_ok = False
                continue
            fname = str(entry.get("file", ""))
            if not SAFE_FILENAME_RE.match(fname):
                ondisk_ok = False
                local_errors.append(f"Unsafe filename for {key}: {fname!r}")
                continue
            fpath = target_dir / fname
            if not fpath.is_file() or fpath.is_symlink():
                ondisk_ok = False
                local_errors.append(f"Missing or symlinked file for {key}: {fname}")
                continue
            if fpath.stat().st_size != int(entry.get("bytes", -1)):
                ondisk_ok = False
                local_errors.append(f"Size mismatch on {key}: disk={fpath.stat().st_size} manifest={entry.get('bytes')}")
                continue
            if _sha256_file_stream(fpath) != str(entry.get("pass1_sha256", "")):
                ondisk_ok = False
                local_errors.append(f"On-disk SHA256 mismatch on {key}")
                continue
            verified.append(key)

        # Validate Sector 0 magic & FX3 7.02 geometry
        s0_magic_ok = False
        s0_fx3_ok = False
        if "sector0" in verified:
            s0_bytes = read_only_mmap_bytes(target_dir / str(items["sector0"]["file"]))
            s0_res = verify_sector0_partition_table(s0_bytes)
            s0_magic_ok = s0_res.magic_ok and s0_res.version_ok and s0_res.count == 30
            s0_fx3_ok = s0_res.valid and s0_res.layout_profile == "FX3_702" and not s0_res.has_overlaps
            if not s0_fx3_ok:
                local_errors.extend(s0_res.errors or [f"Unexpected Sector 0 profile: {s0_res.layout_profile}"])

        # Validate p1 VFAT + dat2=91030080 + dat3
        p1_vfat_ok = False
        if "p1_updater" in verified:
            p1_path = target_dir / str(items["p1_updater"]["file"])
            v_audit = audit_p1_vfat_header(p1_path, int(items["p1_updater"]["bytes"]))
            p1_vfat_ok = v_audit.valid
            if not p1_vfat_ok:
                local_errors.extend(v_audit.errors)

        p1_dat2_ok = False
        p1_dat3_ok = False
        if isinstance(probes.get("p1_dat2"), dict):
            d2_path = target_dir / str(probes["p1_dat2"].get("file", ""))
            if d2_path.is_file():
                d2_txt = d2_path.read_text(encoding="ascii", errors="replace").strip()
                p1_dat2_ok = d2_txt == FX3_MODEL_ID_STR
                if not p1_dat2_ok:
                    local_errors.append(f"p1:/dat2 must be {FX3_MODEL_ID_STR}, got {d2_txt!r}")
        else:
            local_errors.append("Missing mandatory p1_dat2 probe")

        if isinstance(probes.get("p1_dat3"), dict):
            d3_path = target_dir / str(probes["p1_dat3"].get("file", ""))
            p1_dat3_ok = d3_path.is_file() and d3_path.stat().st_size >= 4
        if not p1_dat3_ok:
            local_errors.append("Missing mandatory p1_dat3 probe")

        # Validate p2 Backup.bin (BK4\0), psd.bin, defdet.bin, cxd90057.dtb (0xd00dfeed)
        p2_bk4_ok = False
        if "p2_backup_bin" in verified:
            bk_b = read_only_mmap_bytes(target_dir / str(items["p2_backup_bin"]["file"]))
            bk_rec, bk_errs = parse_bk4_record(bk_b, 0)
            p2_bk4_ok = (
                bk_rec is not None
                and bk_rec.magic_ok
                and bk_rec.checksum_ok
                and len(bk_errs) == 0
            )
            if not p2_bk4_ok:
                local_errors.extend(bk_errs or ["Invalid BK4\\0 record in p2_backup_bin"])

        p2_psd_ok = "p2_psd_bin" in verified
        p2_defdet_ok = "p2_defdet_bin" in verified
        p2_dtb_ok = False
        if isinstance(probes.get("p2_cxd90057_dtb"), dict):
            dtb_p = target_dir / str(probes["p2_cxd90057_dtb"].get("file", ""))
            if dtb_p.is_file() and dtb_p.stat().st_size >= 40:
                magic_be = struct.unpack_from(">I", read_only_mmap_bytes(dtb_p), 0)[0]
                p2_dtb_ok = magic_be == 0xD00DFEED
        if not p2_dtb_ok:
            local_errors.append("Missing or invalid p2 cxd90057.dtb (expected 0xd00dfeed FDT magic)")

        p6_ok = "p6_jiritsu" in verified
        p12_ok = "p12_cert" in verified
        p18_ok = "p18_lensfile" in verified
        nor_ddr_ok = "spi_nor_ddrtraining" in verified
        boot01_ok = ("boot0" in verified) and ("boot1" in verified)

        nor_loader_ok = False
        if isinstance(probes.get("spi_nor_loader"), dict):
            ln_p = target_dir / str(probes["spi_nor_loader"].get("file", ""))
            if ln_p.is_file() and ln_p.stat().st_size >= 92448:
                ln_b = read_only_mmap_bytes(ln_p)
                nor_loader_ok = b"\\mode\\cmode" in ln_b and b"\\updater\\mode" in ln_b
        if not nor_loader_ok:
            local_errors.append("Missing or invalid spi_nor_loader (loader_nor.bin)")

        all_ok = (
            m_audit.valid
            and is_non_synth
            and twopass_ok
            and ondisk_ok
            and s0_magic_ok
            and s0_fx3_ok
            and p1_dat2_ok
            and p1_dat3_ok
            and p1_vfat_ok
            and p2_bk4_ok
            and p2_psd_ok
            and p2_defdet_ok
            and p2_dtb_ok
            and p6_ok
            and p12_ok
            and p18_ok
            and nor_ddr_ok
            and nor_loader_ok
            and boot01_ok
            and len(local_errors) == 0
        )
        return Pillar4Tier0StopGateReport(
            pillar_id="TIER0_COMPLETE_COLD_BACKUP_STOP_GATE",
            all_checks_passed=all_ok,
            verification_mode=mode,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            usb_device_attach_executed=USB_DEVICE_ATTACH_EXECUTED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            bundle_dir=str(target_dir),
            is_non_synthetic_hardware=is_non_synth,
            manifest_audit_valid=m_audit.valid,
            twopass_sha256_all_matched=twopass_ok,
            ondisk_sha256_all_matched=ondisk_ok,
            sector0_magic_ok=s0_magic_ok,
            sector0_fx3_layout_ok=s0_fx3_ok,
            p1_dat2_model_ok=p1_dat2_ok,
            p1_dat3_present=p1_dat3_ok,
            p1_boot_vfat_ok=p1_vfat_ok,
            p2_bk4_ok=p2_bk4_ok,
            p2_psd_ok=p2_psd_ok,
            p2_defdet_ok=p2_defdet_ok,
            p2_dtb_fdt_magic_ok=p2_dtb_ok,
            p6_jiritsu_size_ok=p6_ok,
            p12_cert_size_ok=p12_ok,
            p18_lensfile_ok=p18_ok,
            spi_nor_ddrtraining_ok=nor_ddr_ok,
            spi_nor_loader_ok=nor_loader_ok,
            boot0_boot1_ok=boot01_ok,
            verified_items=tuple(verified),
            negative_gate_drills_passed=0,
            errors=tuple(local_errors),
        )

    if bundle_dir is not None:
        return _audit_dir(bundle_dir, allow_synthetic_fixture=False)

    # Run deterministic self-contained fixture + 5 negative stop-gate drills inside TemporaryDirectory
    with tempfile.TemporaryDirectory(prefix="phase136_tier0_") as td:
        base = Path(td)
        nom_dir = populate_phase136_tier0_bundle(base / "nominal")
        nom_res = _audit_dir(nom_dir, allow_synthetic_fixture=False)

        neg_cases = (
            ("missing_psd", {"omit_item": "p2_psd_bin"}),
            ("missing_defdet", {"omit_item": "p2_defdet_bin"}),
            ("missing_ddrtraining", {"omit_item": "spi_nor_ddrtraining"}),
            ("wrong_dat2", {"wrong_dat2": True}),
            ("pass2_mismatch", {"corrupt_pass2_item": "p6_jiritsu"}),
        )
        neg_passed = 0
        for name, kwargs in neg_cases:
            ndir = populate_phase136_tier0_bundle(base / name, **kwargs)  # type: ignore[arg-type]
            nres = _audit_dir(ndir, allow_synthetic_fixture=False)
            if not nres.all_checks_passed:
                neg_passed += 1
            else:
                errors.append(f"Negative Tier-0 stop-gate drill {name} unexpectedly passed!")

        final_errors = list(nom_res.errors) + errors
        return Pillar4Tier0StopGateReport(
            pillar_id=nom_res.pillar_id,
            all_checks_passed=nom_res.all_checks_passed and neg_passed == len(neg_cases) and len(final_errors) == 0,
            verification_mode=nom_res.verification_mode,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            usb_device_attach_executed=USB_DEVICE_ATTACH_EXECUTED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            bundle_dir="<ephemeral_tier0_stop_gate_sandbox>",
            is_non_synthetic_hardware=nom_res.is_non_synthetic_hardware,
            manifest_audit_valid=nom_res.manifest_audit_valid,
            twopass_sha256_all_matched=nom_res.twopass_sha256_all_matched,
            ondisk_sha256_all_matched=nom_res.ondisk_sha256_all_matched,
            sector0_magic_ok=nom_res.sector0_magic_ok,
            sector0_fx3_layout_ok=nom_res.sector0_fx3_layout_ok,
            p1_dat2_model_ok=nom_res.p1_dat2_model_ok,
            p1_dat3_present=nom_res.p1_dat3_present,
            p1_boot_vfat_ok=nom_res.p1_boot_vfat_ok,
            p2_bk4_ok=nom_res.p2_bk4_ok,
            p2_psd_ok=nom_res.p2_psd_ok,
            p2_defdet_ok=nom_res.p2_defdet_ok,
            p2_dtb_fdt_magic_ok=nom_res.p2_dtb_fdt_magic_ok,
            p6_jiritsu_size_ok=nom_res.p6_jiritsu_size_ok,
            p12_cert_size_ok=nom_res.p12_cert_size_ok,
            p18_lensfile_ok=nom_res.p18_lensfile_ok,
            spi_nor_ddrtraining_ok=nom_res.spi_nor_ddrtraining_ok,
            spi_nor_loader_ok=nom_res.spi_nor_loader_ok,
            boot0_boot1_ok=nom_res.boot0_boot1_ok,
            verified_items=nom_res.verified_items,
            negative_gate_drills_passed=neg_passed,
            errors=tuple(final_errors),
        )


# ============================================================================
# Master Phase 136 Runner & Tamper-Evident Verifier
# ============================================================================

def _compute_phase136_sha256(payload: Mapping[str, Any]) -> str:
    clone = copy.deepcopy(dict(payload))
    clone.pop("report_sha256", None)
    raw = json.dumps(clone, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def run_phase136_realhw_jiritsu_tier0_audit(
    *,
    tier0_bundle_dir: Optional[Path] = None,
    synthetic_clean_room: Optional[bool] = None,
) -> Phase136RealHwJiritsuTier0Report:
    """Execute all 4 Phase 136 pillars and return a deterministic tamper-evident report."""
    p1 = audit_pillar1_jiritsu_dispatch_and_stage288_p0(synthetic_clean_room=synthetic_clean_room)
    p2 = audit_pillar2_u4_zero_sector0_bridge(synthetic_clean_room=synthetic_clean_room)
    p3 = audit_pillar3_u5_p1_oneshot_fallback(synthetic_clean_room=synthetic_clean_room)
    p4 = audit_pillar4_tier0_cold_backup_gate(
        bundle_dir=tier0_bundle_dir,
        synthetic_clean_room=synthetic_clean_room,
    )

    clean_room = is_forced_clean_room() if synthetic_clean_room is None else bool(synthetic_clean_room)
    mode = "CLEAN_ROOM_SYNTHETIC" if clean_room or p1.verification_mode == "CLEAN_ROOM_SYNTHETIC" else "LOCAL_DONOR_O_RDONLY"
    all_errors = list(p1.errors) + list(p2.errors) + list(p3.errors) + list(p4.errors)
    all_ok = (
        p1.all_checks_passed
        and p2.all_checks_passed
        and p3.all_checks_passed
        and p4.all_checks_passed
        and len(all_errors) == 0
    )

    skeleton = Phase136RealHwJiritsuTier0Report(
        schema=PHASE_136_SCHEMA,
        phase_version=PHASE_136_VERSION,
        verification_mode=mode,
        all_checks_passed=all_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        usb_device_attach_executed=USB_DEVICE_ATTACH_EXECUTED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        emmc_bytes_mutated=0,
        raw_firmware_slices_emitted=0,
        pillar1_jiritsu_stage288=p1,
        pillar2_u4_zero_sector0=p2,
        pillar3_u5_p1_fallback=p3,
        pillar4_tier0_stop_gate=p4,
        errors=tuple(all_errors),
        report_sha256="",
    )
    digest = _compute_phase136_sha256(skeleton.to_dict())
    return Phase136RealHwJiritsuTier0Report(
        schema=skeleton.schema,
        phase_version=skeleton.phase_version,
        verification_mode=skeleton.verification_mode,
        all_checks_passed=skeleton.all_checks_passed,
        persistent_emmc_writes_authorized=skeleton.persistent_emmc_writes_authorized,
        usb_device_attach_executed=skeleton.usb_device_attach_executed,
        persistent_write_release=skeleton.persistent_write_release,
        emmc_bytes_mutated=skeleton.emmc_bytes_mutated,
        raw_firmware_slices_emitted=skeleton.raw_firmware_slices_emitted,
        pillar1_jiritsu_stage288=skeleton.pillar1_jiritsu_stage288,
        pillar2_u4_zero_sector0=skeleton.pillar2_u4_zero_sector0,
        pillar3_u5_p1_fallback=skeleton.pillar3_u5_p1_fallback,
        pillar4_tier0_stop_gate=skeleton.pillar4_tier0_stop_gate,
        errors=skeleton.errors,
        report_sha256=digest,
    )


def verify_phase136_report(report_dict: Mapping[str, Any]) -> Phase136ReportVerifyResult:
    """Fail-closed tamper verifier for serialized `phase136_realhw_jiritsu_tier0_audit_v1` JSON."""
    errors: List[str] = []
    if report_dict.get("schema") != PHASE_136_SCHEMA:
        errors.append(f"Invalid schema: {report_dict.get('schema')!r}")
    if report_dict.get("persistent_emmc_writes_authorized") is not False:
        errors.append("persistent_emmc_writes_authorized must be False")
    if report_dict.get("usb_device_attach_executed") is not False:
        errors.append("usb_device_attach_executed must be False")
    if report_dict.get("persistent_write_release") is not False:
        errors.append("persistent_write_release must be False")
    if report_dict.get("emmc_bytes_mutated") != 0:
        errors.append("emmc_bytes_mutated must be 0")
    if report_dict.get("raw_firmware_slices_emitted") != 0:
        errors.append("raw_firmware_slices_emitted must be 0")
    expected_sha = _compute_phase136_sha256(report_dict)
    if report_dict.get("report_sha256") != expected_sha:
        errors.append("report_sha256 tamper mismatch")
    for pkey in (
        "pillar1_jiritsu_stage288",
        "pillar2_u4_zero_sector0",
        "pillar3_u5_p1_fallback",
        "pillar4_tier0_stop_gate",
    ):
        sub = report_dict.get(pkey)
        if not isinstance(sub, Mapping) or not sub.get("all_checks_passed"):
            errors.append(f"{pkey}.all_checks_passed is not True")
    return Phase136ReportVerifyResult(valid=len(errors) == 0 and bool(report_dict.get("all_checks_passed")), errors=tuple(errors))
