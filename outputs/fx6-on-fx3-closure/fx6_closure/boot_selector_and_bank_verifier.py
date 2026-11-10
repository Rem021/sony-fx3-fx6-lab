"""Phase 7 — Boot-Selector Single-Shot Fallback Contract (U5 Closure) & 0xfa0080 Bank 0/1 DDR Map Verifier (U3).

Covers two independent boot-safety verification dimensions across read-only FX3 7.02 and FX6 6.01 donors:

- **Dimension A (Closing Blueprint `U5` — `up.sh` + `ud_send_lsi.elf` + `loader_nor.bin` Boot-Selector Contract)**:
  1. Audits `up.sh`, `common.src`, all three donor `ud_send_lsi.elf` binaries (`FX6 p15:/bin/ud_send_lsi.elf`,
     `FX6 p1-initrd:/usr/bin/ud_send_lsi.elf`, and `FX3 2.05:/usr/bin/ud_send_lsi.elf`), `loader_nor.bin`
     (linked at Octal-SPI NOR SRAM `0xFE049000`), `LdrBkupList.txt` (65 keys), and `pformat_config.txt`.
  2. Pins exact ELF64 `ET_EXEC` virtual addresses, instruction words, PLT/GOT slots, and `.rodata` format
     strings in `ud_send_lsi.elf` (`main` @ `0x400990..0x400ad8`), proving 100% byte-identity across all
     loadable `PT_LOAD` segments (`0x0000..0x2070`) between FX6 and FX3/initrd builds, then micro-executes
     `ud_send_lsi.elf` in **Unicorn AArch64** across all 7 `up.sh` modes (`0, 2, 3, 4, 5, 6, 7`), both
     active Sub-LSI roles (`LSI_MAIN=1`, `LSI_SUB=2`), timeout tolerance (`-0x3fe`), cold-seed `0x004b0000=3`
     no-op gating, and `argc != 2` error handling, capturing the exact 4-byte payload sent to queue
     `0x804b0376` (reply queue `0x004b0379`).
  3. Pins `loader_nor.bin`'s dual-condition boot-mode arbitrator (`0xFE054AF8..0xFE054B34`,
     `0xFE053C78..0xFE053D1C`, `0xFE057FF8..0xFE058034`, `0xFE058E60 -> 0xFE04C7A8 -> 0xFE04D584`),
     proving why the RAM-only `p7` overlay (`0` writes to `p1`, `0` writes to `p2:/setting/updater/mode*`,
     `0` non-zero `ud_send_lsi.elf` packets, `BK4\\0` byte-8 selector `== 0x00`) has zero sticky updater
     persistence risk, and enforcing the mandatory two-step `p1` recovery exit reset
     (`rm -f /setting/updater/mode* && sync` + explicit `ud_send_lsi.elf 0`).

- **Dimension B (Advancing Blueprint `U3` — `0xfa0080` Bank 0 vs Bank 1 DDR Non-Overlap & Calibration Audit)**:
  Parses and validates every slot in the 9,216-byte (`64` slots x `144`-byte stride, matching `loader_nor.bin`
  `0xFE054638..0xFE054688`) `0xfa0080` cold-boot descriptor tables across FX3 (`bank0-fa0080.bin`,
  `bank1-fa0080.bin`, `FX3-CX95900_ALLLANG-Backup.bin`) and FX6 (`CX95898_NTSC.bin` Records 0 & 1),
  proving pairwise **0-byte DDR interval overlap** in every bank, **0-byte AP DDR shift** in Bank 0, and
  quantifying the exact **`+0xE0000`** (`\\psd.bin`, `\\lensfile.bin`, `\\OldAmtCL.bin`) and **`+0x14000`**
  (`\\defdet.bin`, `\\DmmCfg.bin`) Bank 1 calibration load-address shifts between FX3 and FX6 while
  rejecting any overlapping DDR interval, out-of-bounds partition index, inverted range, or non-zero
  Bank 0 byte-8 selector.
"""

from __future__ import annotations

import hashlib
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from fx3_safety.boot_contracts import (
    FA0080_SLOT_COUNT,
    FA0080_SLOT_STRIDE,
    FA0080_TOTAL_BYTES,
    parse_bk4_record,
)

from .backup_mount_tolerance_verifier import (
    DEFAULT_COLOR_PORT_WORK_DIR,
    DEFAULT_FX3_SEED_BK4_PATH,
    DEFAULT_FX6_TEAM_DIR,
    DEFAULT_FX6_TEMPLATE_BK4_PATH,
    PINNED_FX3_SEED_BK4_SHA256,
    PINNED_FX6_TEMPLATE_BK4_SHA256,
    PinnedInstructionCheck,
    UNICORN_SITE_PACKAGES,
    _ensure_unicorn_imported,
    _page_down,
    _page_up,
    _parse_elf64_pt_loads,
    _read_c_string,
    _vma_to_file_offset,
    read_bk4_property_bytes,
)


# Clean read-only donor artifact paths
DEFAULT_AP_MEMBERS_DIR = DEFAULT_COLOR_PORT_WORK_DIR / "ap-input-20261029" / "original-members"
DEFAULT_UP_SH_PATH = DEFAULT_AP_MEMBERS_DIR / "up.sh"
DEFAULT_COMMON_SRC_PATH = DEFAULT_AP_MEMBERS_DIR / "common.src"

DEFAULT_CONFIG_ORIG_DIR = DEFAULT_COLOR_PORT_WORK_DIR / "config-producer-20261029" / "original-files"
DEFAULT_LOADER_NOR_PATH = DEFAULT_CONFIG_ORIG_DIR / "loader_nor.bin"
DEFAULT_LDR_BKUP_LIST_PATH = DEFAULT_CONFIG_ORIG_DIR / "LdrBkupList.txt"
DEFAULT_PFORMAT_CONFIG_PATH = DEFAULT_CONFIG_ORIG_DIR / "pformat_config.txt"
DEFAULT_FX3_BANK0_FA0080_PATH = DEFAULT_CONFIG_ORIG_DIR / "bank0-fa0080.bin"
DEFAULT_FX3_BANK1_FA0080_PATH = DEFAULT_CONFIG_ORIG_DIR / "bank1-fa0080.bin"

DEFAULT_FX6_P15_UD_SEND_LSI_PATH = (
    DEFAULT_FX6_TEAM_DIR / "donor" / "nflasha15-files" / "bin" / "ud_send_lsi.elf"
)
DEFAULT_FX6_P1_UD_SEND_LSI_PATH = (
    DEFAULT_FX6_TEAM_DIR / "donor" / "nested-files" / "nflasha1-initrd" / "usr" / "bin" / "ud_send_lsi.elf"
)
DEFAULT_FX3_ROOTFS_UD_SEND_LSI_PATH = (
    DEFAULT_COLOR_PORT_WORK_DIR / "input-20261028" / "engine-rootfs" / "2.05" / "usr" / "bin" / "ud_send_lsi.elf"
)

# Pinned SHA-256 digests
PINNED_UP_SH_SHA256 = "c774320a0ab92c13b467b9219e1f60262a1effa0b551ba3b713514a36dadc402"
PINNED_COMMON_SRC_SHA256 = "3d5334ab1698d67176f8fd35ffd4d7a9a9b85a1625b20cf128ba091f752b90a0"
PINNED_FX6_P15_UD_SEND_LSI_SHA256 = "d0ece6ca2b8e18d79ed1abe1f96fe40a22628aa458f5d37a19a83a3f51e4fb44"
PINNED_P1_AND_FX3_UD_SEND_LSI_SHA256 = "9fb4bd02b3434bd9fe8fb49fcf4359f7720b292506960ae0d9894332d3453c80"
PINNED_LOADER_NOR_SHA256 = "4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942"
PINNED_LDR_BKUP_LIST_SHA256 = "ae537183ecce42fbe9589c01f7ee4a19929fa2fc1cb09e48eda9ef2ab6f5dd88"
PINNED_PFORMAT_CONFIG_SHA256 = "21cd5b29dd165c322f5b00bb057802c377ff94af15f95881e150a32130302ece"
PINNED_FX3_BANK0_FA0080_SHA256 = "7211bc043617837927604e0f1900a987d31d483920323fdc653c1348d28bac5b"
PINNED_FX3_BANK1_FA0080_SHA256 = "33e39fc7bf35447d97f4ce2bf8d8251cee79453fdd6175cce0c6136f48c93ad6"

# Dimension A — `ud_send_lsi.elf` (`ET_EXEC` @ 0x400000) pinned VMAs, PLTs, queues & instructions
UD_SEND_LSI_ENTRY_VMA = 0x400AE0
UD_SEND_LSI_MAIN_VMA = 0x400990
UD_SEND_LSI_RET_VMA = 0x400A34
UD_SEND_LSI_PT_LOAD_END_OFFSET = 0x2070

UD_SEND_LSI_PLT_SET_MSG_SRC = 0x4008D0
UD_SEND_LSI_PLT_SND_MSG = 0x4008E0
UD_SEND_LSI_PLT_RCV_MSG_TMO = 0x4008F0
UD_SEND_LSI_PLT_VALLOC_MSG_WAIT = 0x400900
UD_SEND_LSI_PLT_ATOI = 0x400910
UD_SEND_LSI_PLT_BACKUP_READ = 0x400930
UD_SEND_LSI_PLT_EXIT = 0x400950
UD_SEND_LSI_PLT_FREE_MSG = 0x400970
UD_SEND_LSI_PLT_PRINTF = 0x400980

UD_SEND_LSI_RODATA_BKUP_ERR_VMA = 0x400CD0
UD_SEND_LSI_RODATA_VALLOC_ERR_VMA = 0x400CF6
UD_SEND_LSI_RODATA_SND_ERR_VMA = 0x400D30
UD_SEND_LSI_RODATA_RCV_ERR_VMA = 0x400D67

UD_SEND_LSI_DST_QUEUE_ID = 0x804B0376
UD_SEND_LSI_DST_QUEUE_LOW16 = 0x0376
UD_SEND_LSI_SRC_REPLY_QUEUE_ID = 0x004B0379
UD_SEND_LSI_BACKUP_KEY_LSI_TYPE = 0x004B0000
UD_SEND_LSI_PAYLOAD_BYTES = 4
UD_SEND_LSI_RCV_TIMEOUT_MS = 3000  # 0xbb8
UD_SEND_LSI_OSAL_E_TMO = -0x3FE  # -1022

UD_SEND_LSI_PINNED_INSNS: Tuple[Tuple[int, int, str], ...] = (
    (0x400990, 0xA9BD7BFD, "stp x29, x30, [sp, #-0x30]!"),
    (0x400994, 0x7100081F, "cmp w0, #2 (argc == 2)"),
    (0x4009B4, 0x52A00960, "mov w0, #0x4b0000 (Backup key 0x004b0000)"),
    (0x4009B8, 0x97FFFFDE, "bl 0x400930 <Backup_read@plt>"),
    (0x4009E0, 0x51000400, "sub w0, w0, #1"),
    (0x4009E8, 0x7100041F, "cmp w0, #1 (lsi_type in {1, 2})"),
    (0x4009EC, 0x540001E8, "b.hi 0x400a28 (skip UIPC if lsi_type not in {1, 2})"),
    (0x4009F4, 0x52806EC0, "mov w0, #0x376"),
    (0x4009FC, 0x52800082, "mov w2, #4 (4-byte payload)"),
    (0x400A00, 0x72B00960, "movk w0, #0x804b, lsl #16 (dst_queue = 0x804b0376)"),
    (0x400A04, 0x97FFFFBF, "bl 0x400900 <osal_valloc_msg_wait@plt>"),
    (0x400A3C, 0x52806F21, "mov w1, #0x379"),
    (0x400A40, 0x72A00961, "movk w1, #0x4b, lsl #16 (src_queue = 0x004b0379)"),
    (0x400A44, 0x97FFFFA3, "bl 0x4008d0 <osal_set_msg_src@plt>"),
    (0x400A4C, 0x97FFFFB1, "bl 0x400910 <atoi@plt>"),
    (0x400A58, 0xB9000260, "str w0, [x19] (store 32-bit LE mode_num payload)"),
    (0x400A64, 0x97FFFF9F, "bl 0x4008e0 <osal_snd_msg@plt>"),
    (0x400AA4, 0x52817702, "mov w2, #0xbb8 (3000 ms timeout)"),
    (0x400AAC, 0x97FFFF91, "bl 0x4008f0 <osal_rcv_msg_tmo@plt>"),
    (0x400AB8, 0x12807FA0, "mov w0, #-0x3fe (OSAL_E_TMO = -1022 tolerated)"),
    (0x400A94, 0x97FFFFB7, "bl 0x400970 <osal_free_msg@plt>"),
    (0x400A34, 0xD65F03C0, "ret"),
)

# Canonical `up.sh` mode specifications: (cli_arg_or_toggle, mode_num, label, p2_flag_files)
UP_SH_MODE_SPECS: Tuple[Tuple[str, int, str, Tuple[str, ...]], ...] = (
    ("toggle_clear", 0, "Normal mode", ()),
    ("user", 2, "UFP mode", ("/setting/updater/mode",)),
    ("serv", 3, "Service mode", ("/setting/updater/mode", "/setting/updater/mode3")),
    ("toggle_set", 4, "Updater mode", ("/setting/updater/mode", "/setting/updater/mode1")),
    ("ms", 5, "MS Crypt mode", ("/setting/updater/mode", "/setting/updater/mode5")),
    ("ver", 6, "Version Skip mode", ("/setting/updater/mode", "/setting/updater/mode6")),
    ("file", 7, "File Crypt mode", ("/setting/updater/mode", "/setting/updater/mode7")),
)

# Dimension A — `loader_nor.bin` (`0xFE049000`) pinned VMAs, strings & instructions
LOADER_NOR_BASE_VMA = 0xFE049000
LOADER_NOR_STR_BOOTMODE_FMT_VMA = 0xFE05ED07  # "BOM:<<BootMode: %u: %s>>\n"
LOADER_NOR_STR_UPDATER_MODE_VMA = 0xFE05EDAB  # "\\updater\\mode"
LOADER_NOR_STR_BACKUP_BAK_VMA = 0xFE05F8B6  # "\\Backup.bak"
LOADER_NOR_STR_BACKUP_BIN_VMA = 0xFE05F8C2  # "\\Backup.bin"
LOADER_NOR_STR_MODE_CMODE_VMA = 0xFE0609CB  # "\\mode\\cmode"
LOADER_NOR_BOOTMODE_TABLE_VMA = 0xFE05DF3C  # 10 x 8-byte BootMode names
LOADER_NOR_LBK_LIST_STR_VMA = 0xFE0615D8  # "LBK_LIST( ... )"

LOADER_NOR_EXPECTED_BOOTMODES: Tuple[str, ...] = (
    "none",
    "cold",
    "hot",
    "updater",
    "cipa",
    "adjust",
    "usbchrg",
    "off",
    "reboot",
    "ontimer",
)

LOADER_NOR_PINNED_INSNS: Tuple[Tuple[int, int, str], ...] = (
    (0xFE04C7A8, 0x320003E2, "mov w2, #1 (strict byte8 == 1 mode)"),
    (0xFE04C7AC, 0x14000376, "b 0xfe04d584 <select_active_bk4_record>"),
    (0xFE04D590, 0x39402008, "ldrb w8, [x0, #8] (BK4 byte-8 selector)"),
    (0xFE04D5E0, 0x7100051F, "cmp w8, #1 (require byte8 == 1 in strict selector)"),
    (0xFE053CA0, 0x52800514, "mov w20, #0x28"),
    (0xFE053CA4, 0x72BFC2F4, "movk w20, #0xfe17, lsl #16 (sticky MMIO 0xfe170028)"),
    (0xFE053CC0, 0x321F03E0, "mov w0, #2 (FAT partition p2:/setting)"),
    (0xFE053CC4, 0x94001092, "bl 0xfe057f0c <fat_mount>"),
    (0xFE053CF4, 0x9136AC00, "add x0, x0, #0xdab (\"\\\\updater\\\\mode\")"),
    (0xFE053CF8, 0x940010AA, "bl 0xfe057fa0 <fat_stat_open_updater_mode>"),
    (0xFE053D08, 0xB9000280, "str w0, [x20] (latch 1 into sticky MMIO 0xfe170028)"),
    (0xFE054614, 0x52801000, "mov w0, #0x80"),
    (0xFE054620, 0x72A01F40, "movk w0, #0xfa, lsl #16 (key 0x00fa0080)"),
    (0xFE054638, 0x52848028, "mov w8, #0x2401 (max 0xfa0080 table size = 0x2400 = 9,216 B)"),
    (0xFE054AF8, 0x34000088, "cbz w8, 0xfe054b08 (ANK Sub-LSI updater latch test)"),
    (0xFE054B00, 0x320007F6, "mov w22, #3 (BootMode[3] = 'updater')"),
    (0xFE054B20, 0x97FFFC56, "bl 0xfe053c78 <check_p2_updater_mode>"),
    (0xFE057FFC, 0x9136AC21, "add x1, x1, #0xdab (\"\\\\updater\\\\mode\", len 14)"),
    (0xFE058014, 0x91272C21, "add x1, x1, #0x9cb (\"\\\\mode\\\\cmode\", len 12)"),
    (0xFE058E60, 0x97FFCE52, "bl 0xfe04c7a8 <select_backup_bin_or_bak>"),
)

# Dimension B — Bank 1 `cpapp-b.bin` dynamic-size sentinel (`size = 0` in `pformat_config.txt`)
CPAPP_SENTINEL_MODE = 0x81000000
CPAPP_SENTINEL_PATH = "\\cpapp-b.bin"
DEFAULT_CPAPP_DDR_RESERVE_BYTES = 0x02000000  # 32 MiB conservative envelope (FX3 cpapp-b.bin is 15.24 MiB)

EXPECTED_BANK1_CALIBRATION_SHIFTS: Dict[str, int] = {
    "\\tomco.txt": 0x0,
    "\\cpapp-b.bin": 0x0,
    "\\psd.bin": 0xE0000,
    "\\lensfile.bin": 0xE0000,
    "\\OldAmtCL.bin": 0xE0000,
    "\\bonobo.bin": 0x0,
    "\\sabin\\idt_cam.bin": 0x0,
    "\\defdet.bin": 0x14000,
    "\\DmmCfg.bin": 0x14000,
}


@dataclass(frozen=True)
class UdSendLsiUnicornCase:
    case_id: str
    cli_args: Tuple[str, ...]
    injected_lsi_type: int
    injected_bkup_rc: int
    injected_rcv_rc: int
    exited_early: bool
    exit_status: int
    return_value: int
    uipc_allocated: bool
    uipc_sent: bool
    uipc_freed: bool
    observed_dst_queue: int
    observed_src_queue: int
    observed_timeout_ms: int
    emitted_payload_hex: str
    emitted_mode_u32: Optional[int]
    sp_preserved: bool
    abort_or_fault: bool


@dataclass(frozen=True)
class BootSelectorSafetyCheck:
    valid: bool
    scenario: str
    sticky_updater_risk: bool
    p1_touched: bool
    p2_updater_flags_cleared: bool
    lsi_normal_packet_emitted: bool
    iamupdater_bypass_handled: bool
    bk4_byte8_normal_ok: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DimensionABootSelectorReport:
    all_checks_passed: bool
    u5_closed: bool
    up_sh_sha256_verified: bool
    common_src_sha256_verified: bool
    ud_send_lsi_sha256_verified: bool
    ud_send_lsi_pt_load_identical_across_models: bool
    ud_send_lsi_comment_diff_bytes: int
    loader_nor_sha256_verified: bool
    ldr_bkup_list_65_keys_verified: bool
    pformat_config_sha256_verified: bool
    up_sh_modes_verified: bool
    up_sh_iamupdater_early_exit_verified: bool
    ud_send_lsi_insns: Tuple[PinnedInstructionCheck, ...]
    loader_nor_insns: Tuple[PinnedInstructionCheck, ...]
    loader_nor_bootmodes: Tuple[str, ...]
    unicorn_cases: Tuple[UdSendLsiUnicornCase, ...]
    stage_a_overlay_safety: BootSelectorSafetyCheck
    p1_recovery_two_step_reset_ok: BootSelectorSafetyCheck


@dataclass(frozen=True)
class Fa0080BankInterval:
    slot_index: int
    path: str
    partition: int
    mode: int
    raw_start_addr: int
    raw_end_addr: int
    effective_end_excl: int
    effective_span_bytes: int
    is_dynamic_size_sentinel: bool


@dataclass(frozen=True)
class Fa0080BankAuditResult:
    valid: bool
    label: str
    bank_index: int
    active_byte8: int
    total_slots: int
    active_slot_count: int
    zero_overlap_verified: bool
    selector_byte8_ok: bool
    partitions_in_bounds: bool
    intervals: Tuple[Fa0080BankInterval, ...]
    overlap_pairs: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class BankAddressShiftEntry:
    path: str
    fx3_partition: int
    fx6_partition: int
    fx3_start_addr: int
    fx6_start_addr: int
    delta_bytes: int
    delta_hex: str


@dataclass(frozen=True)
class DimensionBBankMapReport:
    all_checks_passed: bool
    u3_advanced: bool
    fx3_bank0_matches_seed_record0: bool
    fx3_bank1_matches_seed_record1: bool
    fx3_bank0_audit: Fa0080BankAuditResult
    fx3_bank1_audit: Fa0080BankAuditResult
    fx6_bank0_audit: Fa0080BankAuditResult
    fx6_bank1_audit: Fa0080BankAuditResult
    bank0_shared_zero_shift_verified: bool
    bank0_shifts: Tuple[BankAddressShiftEntry, ...]
    bank1_calibration_shifts_verified: bool
    bank1_shifts: Tuple[BankAddressShiftEntry, ...]
    fx3_only_bank1_paths: Tuple[str, ...]
    fx6_only_bank1_paths: Tuple[str, ...]


@dataclass(frozen=True)
class Phase7BootSelectorAndBankReport:
    all_checks_passed: bool
    dimension_a_boot_selector: DimensionABootSelectorReport
    dimension_b_bank_maps: DimensionBBankMapReport


def _read_u32_at_vma_exec(elf_bytes: bytes, vma: int) -> int:
    off = _vma_to_file_offset(elf_bytes, vma)
    return struct.unpack_from("<I", elf_bytes, off)[0]


def _read_u32_at_loader_vma(ldr_bytes: bytes, vma: int) -> int:
    off = vma - LOADER_NOR_BASE_VMA
    if off < 0 or off + 4 > len(ldr_bytes):
        raise ValueError(f"loader_nor.bin VMA 0x{vma:08x} out of bounds")
    return struct.unpack_from("<I", ldr_bytes, off)[0]


def run_ud_send_lsi_unicorn_case(
    elf_bytes: bytes,
    case_id: str,
    cli_args: Sequence[str],
    injected_lsi_type: int = 1,
    injected_bkup_rc: int = 1,
    injected_rcv_rc: int = 0,
) -> UdSendLsiUnicornCase:
    """Micro-execute `ud_send_lsi.elf` `main(argc, argv)` (`0x400990..0x400ad8`) inside Unicorn AArch64."""
    _ensure_unicorn_imported()
    import unicorn as uc  # type: ignore
    import unicorn.arm64_const as uca64  # type: ignore

    pt_loads = _parse_elf64_pt_loads(elf_bytes)
    mu = uc.Uc(uc.UC_ARCH_ARM64, uc.UC_MODE_ARM)

    # Map PT_LOAD segments of ET_EXEC binary (base 0x400000)
    mapped_pages = set()
    for p_offset, p_vaddr, p_filesz, p_memsz, _ in pt_loads:
        start_pg = _page_down(p_vaddr)
        end_pg = _page_up(max(p_vaddr + p_memsz, p_vaddr + 0x1000))
        for pg in range(start_pg, end_pg, 0x1000):
            if pg not in mapped_pages:
                mu.mem_map(pg, 0x1000, uc.UC_PROT_ALL)
                mapped_pages.add(pg)
        if p_filesz > 0:
            mu.mem_write(p_vaddr, elf_bytes[p_offset : p_offset + p_filesz])

    stack_base = 0x70000000
    stack_size = 0x20000
    scratch_base = 0x71000000
    scratch_size = 0x10000
    mu.mem_map(stack_base, stack_size, uc.UC_PROT_READ | uc.UC_PROT_WRITE)
    mu.mem_map(scratch_base, scratch_size, uc.UC_PROT_READ | uc.UC_PROT_WRITE)

    # Layout argv[] and C-strings in scratch memory
    argv_table_addr = scratch_base + 0x100
    str_cursor = scratch_base + 0x400
    for idx, arg in enumerate(cli_args):
        raw_arg = arg.encode("ascii") + b"\x00"
        mu.mem_write(str_cursor, raw_arg)
        mu.mem_write(argv_table_addr + idx * 8, struct.pack("<Q", str_cursor))
        str_cursor += (len(raw_arg) + 0xF) & ~0xF
    mu.mem_write(argv_table_addr + len(cli_args) * 8, struct.pack("<Q", 0))

    msg_buf_addr = scratch_base + 0x2000
    mu.mem_write(msg_buf_addr, b"\xAA\xAA\xAA\xAA")

    sentinel_lr = 0x72000000
    mu.mem_map(sentinel_lr, 0x1000, uc.UC_PROT_READ | uc.UC_PROT_EXEC)
    mu.mem_write(sentinel_lr, struct.pack("<I", 0xD503201F))

    initial_sp = stack_base + stack_size - 0x1000
    mu.reg_write(uca64.UC_ARM64_REG_SP, initial_sp)
    mu.reg_write(uca64.UC_ARM64_REG_LR, sentinel_lr)
    mu.reg_write(uca64.UC_ARM64_REG_X0, len(cli_args))
    mu.reg_write(uca64.UC_ARM64_REG_X1, argv_table_addr)

    state: Dict[str, object] = {
        "exited_early": False,
        "exit_status": 0,
        "uipc_allocated": False,
        "uipc_sent": False,
        "uipc_freed": False,
        "dst_queue": 0,
        "src_queue": 0,
        "timeout_ms": 0,
        "payload": b"",
    }

    plt_targets = {
        UD_SEND_LSI_PLT_SET_MSG_SRC,
        UD_SEND_LSI_PLT_SND_MSG,
        UD_SEND_LSI_PLT_RCV_MSG_TMO,
        UD_SEND_LSI_PLT_VALLOC_MSG_WAIT,
        UD_SEND_LSI_PLT_ATOI,
        UD_SEND_LSI_PLT_BACKUP_READ,
        UD_SEND_LSI_PLT_EXIT,
        UD_SEND_LSI_PLT_FREE_MSG,
        UD_SEND_LSI_PLT_PRINTF,
    }

    def _read_guest_str(ptr: int) -> str:
        raw = bytes(mu.mem_read(ptr, 64))
        nul = raw.find(b"\x00")
        return raw[: nul if nul != -1 else len(raw)].decode("ascii", errors="replace")

    def _hook_code(uc_engine: object, address: int, size: int, user_data: object) -> None:
        if address not in plt_targets:
            return
        lr = uc_engine.reg_read(uca64.UC_ARM64_REG_LR)
        x0 = uc_engine.reg_read(uca64.UC_ARM64_REG_X0)
        x1 = uc_engine.reg_read(uca64.UC_ARM64_REG_X1)
        x2 = uc_engine.reg_read(uca64.UC_ARM64_REG_X2)

        if address == UD_SEND_LSI_PLT_EXIT:
            state["exited_early"] = True
            state["exit_status"] = int(x0 & 0xFFFFFFFF)
            uc_engine.emu_stop()
            return
        if address == UD_SEND_LSI_PLT_BACKUP_READ:
            key_id = int(x0 & 0xFFFFFFFF)
            if key_id != UD_SEND_LSI_BACKUP_KEY_LSI_TYPE:
                raise RuntimeError(f"Unexpected Backup_read key: 0x{key_id:08x}")
            if injected_bkup_rc > 0:
                uc_engine.mem_write(x1, bytes([injected_lsi_type & 0xFF]))
            uc_engine.reg_write(uca64.UC_ARM64_REG_X0, injected_bkup_rc & 0xFFFFFFFFFFFFFFFF)
        elif address == UD_SEND_LSI_PLT_VALLOC_MSG_WAIT:
            state["uipc_allocated"] = True
            state["dst_queue"] = int(x0 & 0xFFFFFFFF)
            if int(x2 & 0xFFFFFFFF) != UD_SEND_LSI_PAYLOAD_BYTES:
                raise RuntimeError(f"Unexpected payload size {x2}")
            uc_engine.mem_write(x1, struct.pack("<Q", msg_buf_addr))
            uc_engine.reg_write(uca64.UC_ARM64_REG_X0, 0)
        elif address == UD_SEND_LSI_PLT_SET_MSG_SRC:
            state["src_queue"] = int(x1 & 0xFFFFFFFF)
            uc_engine.reg_write(uca64.UC_ARM64_REG_X0, 0)
        elif address == UD_SEND_LSI_PLT_ATOI:
            s_val = _read_guest_str(x0).strip()
            m = re.match(r"^[+-]?\d+", s_val)
            parsed = int(m.group(0)) if m else 0
            uc_engine.reg_write(uca64.UC_ARM64_REG_X0, parsed & 0xFFFFFFFF)
        elif address == UD_SEND_LSI_PLT_SND_MSG:
            state["uipc_sent"] = True
            state["dst_queue"] = int(x0 & 0xFFFFFFFF)
            state["payload"] = bytes(uc_engine.mem_read(x1, UD_SEND_LSI_PAYLOAD_BYTES))
            uc_engine.reg_write(uca64.UC_ARM64_REG_X0, 0)
        elif address == UD_SEND_LSI_PLT_RCV_MSG_TMO:
            state["timeout_ms"] = int(x2 & 0xFFFFFFFF)
            uc_engine.mem_write(x1, struct.pack("<Q", msg_buf_addr))
            uc_engine.reg_write(uca64.UC_ARM64_REG_X0, injected_rcv_rc & 0xFFFFFFFFFFFFFFFF)
        elif address == UD_SEND_LSI_PLT_FREE_MSG:
            state["uipc_freed"] = True
            uc_engine.reg_write(uca64.UC_ARM64_REG_X0, 0)
        elif address == UD_SEND_LSI_PLT_PRINTF:
            uc_engine.reg_write(uca64.UC_ARM64_REG_X0, 0)

        uc_engine.reg_write(uca64.UC_ARM64_REG_PC, lr)

    mu.hook_add(uc.UC_HOOK_CODE, _hook_code)

    abort_or_fault = False
    try:
        mu.emu_start(UD_SEND_LSI_MAIN_VMA, sentinel_lr, count=2000)
    except Exception:
        abort_or_fault = True

    exited_early = bool(state["exited_early"])
    final_sp = mu.reg_read(uca64.UC_ARM64_REG_SP)
    raw_ret = mu.reg_read(uca64.UC_ARM64_REG_X0) & 0xFFFFFFFF
    signed_ret = raw_ret - 0x100000000 if (raw_ret & 0x80000000) else raw_ret
    payload_bytes = bytes(state["payload"])  # type: ignore[arg-type]
    emitted_u32 = struct.unpack("<I", payload_bytes)[0] if len(payload_bytes) == 4 else None

    return UdSendLsiUnicornCase(
        case_id=case_id,
        cli_args=tuple(cli_args),
        injected_lsi_type=injected_lsi_type,
        injected_bkup_rc=injected_bkup_rc,
        injected_rcv_rc=injected_rcv_rc,
        exited_early=exited_early,
        exit_status=int(state["exit_status"]),
        return_value=int(state["exit_status"]) if exited_early else int(signed_ret),
        uipc_allocated=bool(state["uipc_allocated"]),
        uipc_sent=bool(state["uipc_sent"]),
        uipc_freed=bool(state["uipc_freed"]),
        observed_dst_queue=int(state["dst_queue"]),
        observed_src_queue=int(state["src_queue"]),
        observed_timeout_ms=int(state["timeout_ms"]),
        emitted_payload_hex=payload_bytes.hex(),
        emitted_mode_u32=emitted_u32,
        sp_preserved=(not exited_early) and (final_sp == initial_sp),
        abort_or_fault=abort_or_fault,
    )


def verify_boot_selector_safety_contract(
    scenario: str,
    *,
    in_p1_updater_env: bool,
    p1_partition_written: bool,
    p2_updater_mode_files: Sequence[str],
    up_sh_invoked_without_direct_lsi: bool,
    direct_ud_send_lsi_payload: Optional[bytes],
    bk4_selector_byte8: int,
) -> BootSelectorSafetyCheck:
    """Verify boot-selector single-shot / non-sticky invariants across Stage-A overlay and p1 exit."""
    errors: List[str] = []
    sticky_risk = False

    if bk4_selector_byte8 != 0x00:
        sticky_risk = True
        errors.append(
            f"BK4 selector byte 8 is 0x{bk4_selector_byte8:02x} (must be 0x00 to prevent strict loader update latch)"
        )

    flags_cleared = len(p2_updater_mode_files) == 0
    if not flags_cleared:
        sticky_risk = True
        errors.append(
            f"Persistent p2:/setting/updater flag files remain present ({list(p2_updater_mode_files)}), "
            "causing loader_nor.bin (0xFE053CF8) to latch [0xFE170028]=1 into sticky updater mode"
        )

    if not in_p1_updater_env:
        # Normal p7 / Stage-A RAM-overlay execution path
        if p1_partition_written:
            sticky_risk = True
            errors.append("Stage-A RAM-overlay path must never write to p1:/updater")
        if direct_ud_send_lsi_payload is not None and direct_ud_send_lsi_payload != b"\x00\x00\x00\x00":
            sticky_risk = True
            errors.append(
                f"Non-zero ud_send_lsi.elf packet ({direct_ud_send_lsi_payload.hex()}) arms Sub-LSI ANK updater latch"
            )
        lsi_normal_ok = direct_ud_send_lsi_payload in (None, b"\x00\x00\x00\x00")
        iamupdater_ok = True
    else:
        # Exiting p1 recovery environment: BOTH p2 mode* deletion AND explicit `ud_send_lsi.elf 0` are mandatory!
        iamupdater_ok = not up_sh_invoked_without_direct_lsi
        if up_sh_invoked_without_direct_lsi:
            sticky_risk = True
            errors.append(
                "Inside /root/IAMUPDATER, up.sh exits at `test -e /root/IAMUPDATER && exit 0` BEFORE invoking "
                "`ud_send_lsi.elf 0`; explicit `ud_send_lsi.elf 0` is mandatory"
            )
        lsi_normal_ok = direct_ud_send_lsi_payload == b"\x00\x00\x00\x00"
        if not lsi_normal_ok:
            sticky_risk = True
            errors.append(
                "Exiting p1 recovery requires explicit `ud_send_lsi.elf 0` (4-byte payload 00000000 to 0x804b0376) "
                "to clear the Sub-LSI ANK updater latch checked at loader_nor.bin 0xFE054AF8"
            )

    return BootSelectorSafetyCheck(
        valid=(len(errors) == 0) and (not sticky_risk),
        scenario=scenario,
        sticky_updater_risk=sticky_risk,
        p1_touched=p1_partition_written,
        p2_updater_flags_cleared=flags_cleared,
        lsi_normal_packet_emitted=lsi_normal_ok,
        iamupdater_bypass_handled=iamupdater_ok,
        bk4_byte8_normal_ok=(bk4_selector_byte8 == 0x00),
        errors=tuple(errors),
    )


def audit_boot_selector_contract(
    up_sh_path: Path = DEFAULT_UP_SH_PATH,
    common_src_path: Path = DEFAULT_COMMON_SRC_PATH,
    fx6_p15_ud_send_lsi_path: Path = DEFAULT_FX6_P15_UD_SEND_LSI_PATH,
    fx6_p1_ud_send_lsi_path: Path = DEFAULT_FX6_P1_UD_SEND_LSI_PATH,
    fx3_rootfs_ud_send_lsi_path: Path = DEFAULT_FX3_ROOTFS_UD_SEND_LSI_PATH,
    loader_nor_path: Path = DEFAULT_LOADER_NOR_PATH,
    ldr_bkup_list_path: Path = DEFAULT_LDR_BKUP_LIST_PATH,
    pformat_config_path: Path = DEFAULT_PFORMAT_CONFIG_PATH,
) -> DimensionABootSelectorReport:
    """Audit `up.sh`, `ud_send_lsi.elf` (static + Unicorn), and `loader_nor.bin` boot-selector contracts (closing U5)."""
    up_sh_bytes = up_sh_path.read_bytes()
    common_src_bytes = common_src_path.read_bytes()
    ud_fx6_p15 = fx6_p15_ud_send_lsi_path.read_bytes()
    ud_fx6_p1 = fx6_p1_ud_send_lsi_path.read_bytes()
    ud_fx3 = fx3_rootfs_ud_send_lsi_path.read_bytes()
    ldr_bytes = loader_nor_path.read_bytes()
    ldr_list_bytes = ldr_bkup_list_path.read_bytes()
    pformat_bytes = pformat_config_path.read_bytes()

    up_sh_ok = hashlib.sha256(up_sh_bytes).hexdigest() == PINNED_UP_SH_SHA256
    common_ok = hashlib.sha256(common_src_bytes).hexdigest() == PINNED_COMMON_SRC_SHA256
    ud_sha_ok = (
        hashlib.sha256(ud_fx6_p15).hexdigest() == PINNED_FX6_P15_UD_SEND_LSI_SHA256
        and hashlib.sha256(ud_fx6_p1).hexdigest() == PINNED_P1_AND_FX3_UD_SEND_LSI_SHA256
        and hashlib.sha256(ud_fx3).hexdigest() == PINNED_P1_AND_FX3_UD_SEND_LSI_SHA256
    )
    ldr_sha_ok = hashlib.sha256(ldr_bytes).hexdigest() == PINNED_LOADER_NOR_SHA256
    ldr_list_sha_ok = hashlib.sha256(ldr_list_bytes).hexdigest() == PINNED_LDR_BKUP_LIST_SHA256
    pformat_sha_ok = hashlib.sha256(pformat_bytes).hexdigest() == PINNED_PFORMAT_CONFIG_SHA256

    # Prove 100% byte-identity across all loadable PT_LOAD segments (0x0000..0x2070)
    pt_load_identical = (
        ud_fx6_p15[:UD_SEND_LSI_PT_LOAD_END_OFFSET] == ud_fx6_p1[:UD_SEND_LSI_PT_LOAD_END_OFFSET]
        and ud_fx6_p1 == ud_fx3
    )
    comment_diff_bytes = sum(1 for a, b in zip(ud_fx6_p15, ud_fx6_p1) if a != b)

    # Verify `up.sh` mode table and `/root/IAMUPDATER` guard
    up_text = up_sh_bytes.decode("utf-8", errors="replace")
    required_up_tokens = (
        "UPMNT=/setting",
        "UPDIR=$UPMNT/updater",
        "UPMODE=$UPDIR/mode",
        "UPMODE1=$UPDIR/mode1",
        "LSI_MAIN=1",
        "LSI_SUB=2",
        "mode_num=4",
        "mode_num=0",
        "mode_num=2",
        "mode_num=3",
        "mode_num=5",
        "mode_num=6",
        "mode_num=7",
        "test -e /root/IAMUPDATER",
        "ud_send_lsi.elf $mode_num",
    )
    up_modes_ok = all(tok in up_text for tok in required_up_tokens)
    iam_idx = up_text.rfind("test -e /root/IAMUPDATER")
    lsi_call_idx = up_text.rfind("ud_send_lsi.elf $mode_num")
    iam_guard_ok = 0 <= iam_idx < lsi_call_idx

    # Static instruction & .rodata pinning on `ud_send_lsi.elf`
    e_entry = struct.unpack_from("<Q", ud_fx6_p15, 24)[0]
    ud_checks: List[PinnedInstructionCheck] = []
    for vma, exp_word, meaning in UD_SEND_LSI_PINNED_INSNS:
        f_off = _vma_to_file_offset(ud_fx6_p15, vma)
        act_word = struct.unpack_from("<I", ud_fx6_p15, f_off)[0]
        ud_checks.append(
            PinnedInstructionCheck(
                vma=vma,
                file_offset=f_off,
                expected_word=exp_word,
                actual_word=act_word,
                mnemonic=meaning,
                matched=(act_word == exp_word),
            )
        )
    ro_bkup = _read_c_string(ud_fx6_p15, _vma_to_file_offset(ud_fx6_p15, UD_SEND_LSI_RODATA_BKUP_ERR_VMA))
    ro_valloc = _read_c_string(ud_fx6_p15, _vma_to_file_offset(ud_fx6_p15, UD_SEND_LSI_RODATA_VALLOC_ERR_VMA))
    ro_snd = _read_c_string(ud_fx6_p15, _vma_to_file_offset(ud_fx6_p15, UD_SEND_LSI_RODATA_SND_ERR_VMA))
    ro_rcv = _read_c_string(ud_fx6_p15, _vma_to_file_offset(ud_fx6_p15, UD_SEND_LSI_RODATA_RCV_ERR_VMA))
    ud_rodata_ok = (
        e_entry == UD_SEND_LSI_ENTRY_VMA
        and ro_bkup == "[UD_SEND_LSI] Backup_read() error %d\n"
        and ro_valloc == "[UD_SEND_LSI] error : osal_valloc_msg, id = %d, err = %d\n"
        and ro_snd == "[UD_SEND_LSI] error : osal_snd_msg, id = %d, err = %d\n"
        and ro_rcv == "[UD_SEND_LSI] error : osal_rcv_msg_tmo, err = %d\n"
    )

    # Static instruction & string pinning on `loader_nor.bin` + 65-key `LdrBkupList.txt`
    ldr_checks: List[PinnedInstructionCheck] = []
    for vma, exp_word, meaning in LOADER_NOR_PINNED_INSNS:
        f_off = vma - LOADER_NOR_BASE_VMA
        act_word = _read_u32_at_loader_vma(ldr_bytes, vma)
        ldr_checks.append(
            PinnedInstructionCheck(
                vma=vma,
                file_offset=f_off,
                expected_word=exp_word,
                actual_word=act_word,
                mnemonic=meaning,
                matched=(act_word == exp_word),
            )
        )
    bootmodes: List[str] = []
    bm_base = LOADER_NOR_BOOTMODE_TABLE_VMA - LOADER_NOR_BASE_VMA
    for i in range(10):
        raw_bm = ldr_bytes[bm_base + i * 8 : bm_base + (i + 1) * 8].split(b"\x00")[0]
        bootmodes.append(raw_bm.decode("ascii", errors="replace"))

    s_bom = _read_c_string(ldr_bytes, LOADER_NOR_STR_BOOTMODE_FMT_VMA - LOADER_NOR_BASE_VMA)
    s_upmode = _read_c_string(ldr_bytes, LOADER_NOR_STR_UPDATER_MODE_VMA - LOADER_NOR_BASE_VMA)
    s_cmode = _read_c_string(ldr_bytes, LOADER_NOR_STR_MODE_CMODE_VMA - LOADER_NOR_BASE_VMA)
    s_bkbin = _read_c_string(ldr_bytes, LOADER_NOR_STR_BACKUP_BIN_VMA - LOADER_NOR_BASE_VMA)
    s_bkbak = _read_c_string(ldr_bytes, LOADER_NOR_STR_BACKUP_BAK_VMA - LOADER_NOR_BASE_VMA)
    lbk_off = LOADER_NOR_LBK_LIST_STR_VMA - LOADER_NOR_BASE_VMA
    lbk_end = ldr_bytes.find(b"\x00", lbk_off)
    s_lbk_list = ldr_bytes[lbk_off : (lbk_end if lbk_end != -1 else lbk_off + 1024)].decode("ascii", errors="replace")

    txt_keys = [int(x.strip(), 16) for x in ldr_list_bytes.decode("ascii").strip().split(",") if x.strip()]
    bin_keys_match = re.search(r"LBK_LIST\(\s*([^)]+?)\s*\)", s_lbk_list)
    bin_keys = (
        [int(x.strip(), 16) for x in bin_keys_match.group(1).split(",") if x.strip()]
        if bin_keys_match
        else []
    )
    ldr_list_65_ok = ldr_list_sha_ok and len(txt_keys) == 65 and txt_keys == bin_keys
    ldr_strings_ok = (
        tuple(bootmodes) == LOADER_NOR_EXPECTED_BOOTMODES
        and s_bom == "BOM:<<BootMode: %u: %s>>\n"
        and s_upmode == "\\updater\\mode"
        and s_cmode == "\\mode\\cmode"
        and s_bkbin == "\\Backup.bin"
        and s_bkbak == "\\Backup.bak"
    )

    # Unicorn AArch64 micro-execution across all 7 `up.sh` modes + LSI_SUB + OSAL_E_TMO + cold-seed 3 + argc!=2
    uni_cases: List[UdSendLsiUnicornCase] = []
    for _, mode_num, label, _ in UP_SH_MODE_SPECS:
        uni_cases.append(
            run_ud_send_lsi_unicorn_case(
                ud_fx6_p15,
                case_id=f"LSI_MAIN_MODE_{mode_num}_{label.upper().replace(' ', '_')}",
                cli_args=("ud_send_lsi.elf", str(mode_num)),
                injected_lsi_type=1,
                injected_bkup_rc=1,
                injected_rcv_rc=0,
            )
        )
    uni_cases.append(
        run_ud_send_lsi_unicorn_case(
            ud_fx6_p1,
            case_id="P1_BINARY_LSI_SUB_NORMAL_TMO_TOLERATED",
            cli_args=("ud_send_lsi.elf", "0"),
            injected_lsi_type=2,
            injected_bkup_rc=1,
            injected_rcv_rc=UD_SEND_LSI_OSAL_E_TMO,
        )
    )
    uni_cases.append(
        run_ud_send_lsi_unicorn_case(
            ud_fx6_p15,
            case_id="COLD_SEED_LSI_TYPE_3_NOOP_GATE",
            cli_args=("ud_send_lsi.elf", "4"),
            injected_lsi_type=3,
            injected_bkup_rc=1,
            injected_rcv_rc=0,
        )
    )
    uni_cases.append(
        run_ud_send_lsi_unicorn_case(
            ud_fx6_p15,
            case_id="INVALID_ARGC_EXIT_1",
            cli_args=("ud_send_lsi.elf",),
            injected_lsi_type=1,
            injected_bkup_rc=1,
            injected_rcv_rc=0,
        )
    )

    mode_cases_ok = all(
        (not c.abort_or_fault)
        and (not c.exited_early)
        and c.return_value == 0
        and c.uipc_allocated
        and c.uipc_sent
        and c.uipc_freed
        and c.observed_dst_queue == UD_SEND_LSI_DST_QUEUE_ID
        and (c.observed_dst_queue & 0xFFFF) == UD_SEND_LSI_DST_QUEUE_LOW16
        and c.observed_src_queue == UD_SEND_LSI_SRC_REPLY_QUEUE_ID
        and c.observed_timeout_ms == UD_SEND_LSI_RCV_TIMEOUT_MS
        and c.emitted_mode_u32 == spec[1]
        and c.emitted_payload_hex == struct.pack("<I", spec[1]).hex()
        and c.sp_preserved
        for c, spec in zip(uni_cases[:7], UP_SH_MODE_SPECS)
    )
    sub_tmo_case = uni_cases[7]
    sub_tmo_ok = (
        not sub_tmo_case.abort_or_fault
        and sub_tmo_case.return_value == 0
        and sub_tmo_case.uipc_sent
        and sub_tmo_case.uipc_freed
        and sub_tmo_case.emitted_payload_hex == "00000000"
        and sub_tmo_case.sp_preserved
    )
    noop_case = uni_cases[8]
    noop_ok = (
        not noop_case.abort_or_fault
        and not noop_case.exited_early
        and noop_case.return_value == 0
        and not noop_case.uipc_allocated
        and not noop_case.uipc_sent
        and noop_case.sp_preserved
    )
    argc_case = uni_cases[9]
    argc_ok = (
        not argc_case.abort_or_fault
        and argc_case.exited_early
        and argc_case.exit_status == 1
        and not argc_case.uipc_sent
    )

    stage_a_safety = verify_boot_selector_safety_contract(
        "STAGE_A_P7_RAM_OVERLAY",
        in_p1_updater_env=False,
        p1_partition_written=False,
        p2_updater_mode_files=(),
        up_sh_invoked_without_direct_lsi=False,
        direct_ud_send_lsi_payload=None,
        bk4_selector_byte8=0x00,
    )
    p1_reset_safety = verify_boot_selector_safety_contract(
        "P1_RECOVERY_ATOMIC_TWO_STEP_EXIT",
        in_p1_updater_env=True,
        p1_partition_written=False,
        p2_updater_mode_files=(),
        up_sh_invoked_without_direct_lsi=False,
        direct_ud_send_lsi_payload=bytes.fromhex(uni_cases[0].emitted_payload_hex),
        bk4_selector_byte8=0x00,
    )

    u5_closed = (
        up_sh_ok
        and common_ok
        and ud_sha_ok
        and pt_load_identical
        and comment_diff_bytes == 7
        and ldr_sha_ok
        and ldr_list_65_ok
        and pformat_sha_ok
        and up_modes_ok
        and iam_guard_ok
        and ud_rodata_ok
        and ldr_strings_ok
        and all(c.matched for c in ud_checks)
        and all(c.matched for c in ldr_checks)
        and mode_cases_ok
        and sub_tmo_ok
        and noop_ok
        and argc_ok
        and stage_a_safety.valid
        and p1_reset_safety.valid
    )

    return DimensionABootSelectorReport(
        all_checks_passed=u5_closed,
        u5_closed=u5_closed,
        up_sh_sha256_verified=up_sh_ok,
        common_src_sha256_verified=common_ok,
        ud_send_lsi_sha256_verified=ud_sha_ok,
        ud_send_lsi_pt_load_identical_across_models=pt_load_identical,
        ud_send_lsi_comment_diff_bytes=comment_diff_bytes,
        loader_nor_sha256_verified=ldr_sha_ok,
        ldr_bkup_list_65_keys_verified=ldr_list_65_ok,
        pformat_config_sha256_verified=pformat_sha_ok,
        up_sh_modes_verified=up_modes_ok,
        up_sh_iamupdater_early_exit_verified=iam_guard_ok,
        ud_send_lsi_insns=tuple(ud_checks),
        loader_nor_insns=tuple(ldr_checks),
        loader_nor_bootmodes=tuple(bootmodes),
        unicorn_cases=tuple(uni_cases),
        stage_a_overlay_safety=stage_a_safety,
        p1_recovery_two_step_reset_ok=p1_reset_safety,
    )


def parse_and_audit_fa0080_bank(
    table_bytes: bytes,
    *,
    label: str,
    bank_index: int,
    active_byte8: int = 0,
    cpapp_reserve_bytes: int = DEFAULT_CPAPP_DDR_RESERVE_BYTES,
) -> Fa0080BankAuditResult:
    """Parse all 64 descriptor slots (`64 x 144 = 9,216 B`) in a `0xfa0080` bank and prove 0-byte DDR overlap."""
    errors: List[str] = []
    overlap_pairs: List[str] = []

    if bank_index not in (0, 1):
        errors.append(f"Invalid bank_index {bank_index} (expected 0 or 1)")

    selector_ok = True
    if bank_index == 0 and active_byte8 != 0x00:
        selector_ok = False
        errors.append(
            f"Bank 0 BK4 active_byte8 is 0x{active_byte8:02x} (must be 0x00 to preserve Normal Boot cold-start safety)"
        )

    if len(table_bytes) != FA0080_TOTAL_BYTES:
        errors.append(
            f"Invalid 0xfa0080 table length {len(table_bytes)} B (expected {FA0080_TOTAL_BYTES} B = "
            f"{FA0080_SLOT_COUNT} slots x {FA0080_SLOT_STRIDE} B)"
        )
        return Fa0080BankAuditResult(
            valid=False,
            label=label,
            bank_index=bank_index,
            active_byte8=active_byte8,
            total_slots=FA0080_SLOT_COUNT,
            active_slot_count=0,
            zero_overlap_verified=False,
            selector_byte8_ok=selector_ok,
            partitions_in_bounds=False,
            intervals=(),
            overlap_pairs=(),
            errors=tuple(errors),
        )

    intervals: List[Fa0080BankInterval] = []
    parts_ok = True

    for slot_idx in range(FA0080_SLOT_COUNT):
        off = slot_idx * FA0080_SLOT_STRIDE
        start_addr, end_addr, part, mode = struct.unpack_from("<QQII", table_bytes, off)
        raw_path = table_bytes[off + 0x18 : off + FA0080_SLOT_STRIDE]
        nul = raw_path.find(b"\x00")
        path_str = (raw_path[:nul] if nul != -1 else raw_path).decode("ascii", errors="replace")

        if start_addr == 0 and end_addr == 0 and part == 0 and mode == 0 and not path_str:
            continue

        if not path_str:
            errors.append(f"Slot [{slot_idx}] has non-zero fields but empty path")
        if not (1 <= part <= 30):
            parts_ok = False
            errors.append(f"Slot [{slot_idx}] ({path_str!r}) references out-of-bounds partition p{part}")

        is_dyn_sentinel = (
            bank_index == 1
            and path_str == CPAPP_SENTINEL_PATH
            and mode == CPAPP_SENTINEL_MODE
            and start_addr > 0
            and end_addr == start_addr - 1
        )
        if is_dyn_sentinel:
            end_excl = start_addr + cpapp_reserve_bytes
        elif end_addr >= start_addr and start_addr > 0:
            end_excl = end_addr + 1
        else:
            errors.append(
                f"Slot [{slot_idx}] ({path_str!r}) has invalid DDR range [0x{start_addr:x}..0x{end_addr:x}]"
            )
            continue

        intervals.append(
            Fa0080BankInterval(
                slot_index=slot_idx,
                path=path_str,
                partition=part,
                mode=mode,
                raw_start_addr=start_addr,
                raw_end_addr=end_addr,
                effective_end_excl=end_excl,
                effective_span_bytes=end_excl - start_addr,
                is_dynamic_size_sentinel=is_dyn_sentinel,
            )
        )

    # Pairwise interval non-overlap verification across all active slots in this bank
    sorted_iv = sorted(intervals, key=lambda iv: (iv.raw_start_addr, iv.slot_index))
    for i in range(len(sorted_iv)):
        for j in range(i + 1, len(sorted_iv)):
            a = sorted_iv[i]
            b = sorted_iv[j]
            ov_start = max(a.raw_start_addr, b.raw_start_addr)
            ov_end = min(a.effective_end_excl, b.effective_end_excl)
            if ov_start < ov_end:
                msg = (
                    f"Slots [{a.slot_index}] {a.path!r} [0x{a.raw_start_addr:x}, 0x{a.effective_end_excl:x}) "
                    f"and [{b.slot_index}] {b.path!r} [0x{b.raw_start_addr:x}, 0x{b.effective_end_excl:x}) "
                    f"overlap by 0x{ov_end - ov_start:x} bytes"
                )
                overlap_pairs.append(msg)
                errors.append(msg)

    zero_overlap = len(overlap_pairs) == 0 and len(intervals) > 0
    valid = selector_ok and parts_ok and zero_overlap and len(errors) == 0
    return Fa0080BankAuditResult(
        valid=valid,
        label=label,
        bank_index=bank_index,
        active_byte8=active_byte8,
        total_slots=FA0080_SLOT_COUNT,
        active_slot_count=len(intervals),
        zero_overlap_verified=zero_overlap,
        selector_byte8_ok=selector_ok,
        partitions_in_bounds=parts_ok,
        intervals=tuple(sorted_iv),
        overlap_pairs=tuple(overlap_pairs),
        errors=tuple(errors),
    )


def _extract_two_bk4_records(raw: bytes) -> Tuple[Tuple[int, bytes], Tuple[int, bytes]]:
    pos = 0
    found: List[Tuple[int, bytes]] = []
    while len(found) < 2:
        hit = raw.find(b"BK4\x00", pos)
        if hit < 0x0C:
            if hit == -1:
                break
            pos = hit + 4
            continue
        rec_off = hit - 0x0C
        summary, errs = parse_bk4_record(raw, rec_off, len(found))
        if summary is not None and not errs:
            found.append((summary.active_byte8, raw[rec_off : rec_off + summary.total_bytes]))
            pos = rec_off + summary.total_bytes
        else:
            pos = hit + 4
    if len(found) != 2:
        raise RuntimeError(f"Expected 2 valid BK4 records in Backup seed, found {len(found)}")
    return found[0], found[1]


def audit_fa0080_bank_maps(
    fx3_bank0_path: Path = DEFAULT_FX3_BANK0_FA0080_PATH,
    fx3_bank1_path: Path = DEFAULT_FX3_BANK1_FA0080_PATH,
    fx3_seed_bk4_path: Path = DEFAULT_FX3_SEED_BK4_PATH,
    fx6_template_bk4_path: Path = DEFAULT_FX6_TEMPLATE_BK4_PATH,
) -> DimensionBBankMapReport:
    """Audit FX3 & FX6 Bank 0 / Bank 1 `0xfa0080` DDR maps and quantify calibration shifts (advancing U3)."""
    fx3_b0_raw = fx3_bank0_path.read_bytes()
    fx3_b1_raw = fx3_bank1_path.read_bytes()
    fx3_seed_raw = fx3_seed_bk4_path.read_bytes()
    fx6_seed_raw = fx6_template_bk4_path.read_bytes()

    sha_ok = (
        hashlib.sha256(fx3_b0_raw).hexdigest() == PINNED_FX3_BANK0_FA0080_SHA256
        and hashlib.sha256(fx3_b1_raw).hexdigest() == PINNED_FX3_BANK1_FA0080_SHA256
        and hashlib.sha256(fx3_seed_raw).hexdigest() == PINNED_FX3_SEED_BK4_SHA256
        and hashlib.sha256(fx6_seed_raw).hexdigest() == PINNED_FX6_TEMPLATE_BK4_SHA256
    )

    (fx3_r0_b8, fx3_r0_bytes), (fx3_r1_b8, fx3_r1_bytes) = _extract_two_bk4_records(fx3_seed_raw)
    (fx6_r0_b8, fx6_r0_bytes), (fx6_r1_b8, fx6_r1_bytes) = _extract_two_bk4_records(fx6_seed_raw)

    fx3_seed_b0 = read_bk4_property_bytes(fx3_r0_bytes, 0x00FA0080)
    fx3_seed_b1 = read_bk4_property_bytes(fx3_r1_bytes, 0x00FA0080)
    fx6_seed_b0 = read_bk4_property_bytes(fx6_r0_bytes, 0x00FA0080)
    fx6_seed_b1 = read_bk4_property_bytes(fx6_r1_bytes, 0x00FA0080)
    if fx6_seed_b0 is None or fx6_seed_b1 is None:
        raise RuntimeError("Missing 0x00fa0080 table in FX6 CX95898_NTSC.bin")

    b0_matches_seed = fx3_seed_b0 == fx3_b0_raw
    b1_matches_seed = fx3_seed_b1 == fx3_b1_raw

    fx3_b0_audit = parse_and_audit_fa0080_bank(
        fx3_b0_raw, label="FX3_702_BANK0", bank_index=0, active_byte8=fx3_r0_b8
    )
    fx3_b1_audit = parse_and_audit_fa0080_bank(
        fx3_b1_raw, label="FX3_702_BANK1", bank_index=1, active_byte8=fx3_r1_b8
    )
    fx6_b0_audit = parse_and_audit_fa0080_bank(
        fx6_seed_b0, label="FX6_601_BANK0", bank_index=0, active_byte8=fx6_r0_b8
    )
    fx6_b1_audit = parse_and_audit_fa0080_bank(
        fx6_seed_b1, label="FX6_601_BANK1", bank_index=1, active_byte8=fx6_r1_b8
    )

    def _compute_shifts(
        fx3_iv: Sequence[Fa0080BankInterval],
        fx6_iv: Sequence[Fa0080BankInterval],
    ) -> Tuple[List[BankAddressShiftEntry], Tuple[str, ...], Tuple[str, ...]]:
        m3 = {iv.path: iv for iv in fx3_iv}
        m6 = {iv.path: iv for iv in fx6_iv}
        shared = [p for p in m3 if p in m6]
        shifts: List[BankAddressShiftEntry] = []
        for p in shared:
            delta = m6[p].raw_start_addr - m3[p].raw_start_addr
            sign = "+" if delta >= 0 else "-"
            shifts.append(
                BankAddressShiftEntry(
                    path=p,
                    fx3_partition=m3[p].partition,
                    fx6_partition=m6[p].partition,
                    fx3_start_addr=m3[p].raw_start_addr,
                    fx6_start_addr=m6[p].raw_start_addr,
                    delta_bytes=delta,
                    delta_hex=f"{sign}0x{abs(delta):x}" if delta != 0 else "0x0",
                )
            )
        only3 = tuple(sorted(set(m3) - set(m6)))
        only6 = tuple(sorted(set(m6) - set(m3)))
        return shifts, only3, only6

    b0_shifts, _, _ = _compute_shifts(fx3_b0_audit.intervals, fx6_b0_audit.intervals)
    b1_shifts, b1_only3, b1_only6 = _compute_shifts(fx3_b1_audit.intervals, fx6_b1_audit.intervals)

    b0_zero_shift_ok = len(b0_shifts) == 5 and all(s.delta_bytes == 0 for s in b0_shifts)
    observed_b1_map = {s.path: s.delta_bytes for s in b1_shifts}
    b1_shifts_ok = (
        observed_b1_map == EXPECTED_BANK1_CALIBRATION_SHIFTS
        and b1_only3 == ("\\SysSound.bin", "\\cpImg.dat")
        and b1_only6 == ("\\cmrbnb.bin",)
    )

    u3_ok = (
        sha_ok
        and b0_matches_seed
        and b1_matches_seed
        and fx3_b0_audit.valid
        and fx3_b1_audit.valid
        and fx6_b0_audit.valid
        and fx6_b1_audit.valid
        and fx3_b0_audit.active_slot_count == 9
        and fx3_b1_audit.active_slot_count == 11
        and fx6_b0_audit.active_slot_count == 5
        and fx6_b1_audit.active_slot_count == 10
        and b0_zero_shift_ok
        and b1_shifts_ok
    )

    return DimensionBBankMapReport(
        all_checks_passed=u3_ok,
        u3_advanced=u3_ok,
        fx3_bank0_matches_seed_record0=b0_matches_seed,
        fx3_bank1_matches_seed_record1=b1_matches_seed,
        fx3_bank0_audit=fx3_b0_audit,
        fx3_bank1_audit=fx3_b1_audit,
        fx6_bank0_audit=fx6_b0_audit,
        fx6_bank1_audit=fx6_b1_audit,
        bank0_shared_zero_shift_verified=b0_zero_shift_ok,
        bank0_shifts=tuple(b0_shifts),
        bank1_calibration_shifts_verified=b1_shifts_ok,
        bank1_shifts=tuple(b1_shifts),
        fx3_only_bank1_paths=b1_only3,
        fx6_only_bank1_paths=b1_only6,
    )


def run_boot_selector_and_bank_verification() -> Phase7BootSelectorAndBankReport:
    """Execute complete Phase 7 Dimension A (`U5` closure) and Dimension B (`U3` bank non-overlap) audits."""
    dim_a = audit_boot_selector_contract()
    dim_b = audit_fa0080_bank_maps()
    return Phase7BootSelectorAndBankReport(
        all_checks_passed=(dim_a.all_checks_passed and dim_b.all_checks_passed),
        dimension_a_boot_selector=dim_a,
        dimension_b_bank_maps=dim_b,
    )
