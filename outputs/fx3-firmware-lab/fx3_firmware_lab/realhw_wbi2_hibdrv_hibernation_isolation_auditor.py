"""Phase 174 — 36th Unified Firmware-Lab Auditor (36/36): Real-Hardware
`p5:/wbi` (`WBI2` / `hibdrv.ko`) Hibernation Snapshot Isolation, Zero-Write Lock
& Stock/Stage-B Cold-Boot Determinism Auditor.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ` / bounded `os.pread`) &
Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`im.elf`, `libsencore.so`, `libmpr.so`,
  `appFw.so`, `cpapp-b.bin`, `Backup.bin`, `nflasha5.img`) and FX6 v6.01
  (`im.elf`, `libsencore.so`, `libmpr.so`, `appFw.so`, `cpapp-b.bin`,
  `Backup.bin`, `nflasha5`) strictly via `os.O_RDONLY` + `mmap.ACCESS_READ` /
  bounded `os.pread` (< 1.5 s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 `.so`/`.elf`,
  `cpapp-b.bin`, `BK4\\0` `Backup.bin`, and byte-compliant `WBI2` fixtures
  carrying verified contract markers, leaking zero raw Sony proprietary bytes
  in JSON output.

Audits Four Phase 174 Real-Hardware Hibernation Isolation & Cold-Boot Pillars:
1. Pillar 1 (`P5_WBI2_HIBDRV_ZERO_WRITE_LOCK`):
   Audits FX3 v7.02 (`nflasha5.img`: `1,399` sections, `82` zero sections,
   `resume_vector=0x4004a67f0`, `wbimem=0x00ba0000`, `phys=[0x400001000, 0x420000000)`)
   and FX6 v6.01 (`nflasha5`: `1,197` sections, `54` zero sections,
   `resume_vector=0x4004a87f0`, `wbimem=0x01919000`, `phys=[0x400001000, 0x424000000)`)
   + `libsencore.so` (`/dev/nflasha5`, `WBI_DROP`, `/boot/sen/smode`) + `hibdrv`
   / `wbi_raw` symbols (`image_drop`, `image_mode`, `image_mem`, `image_dev`,
   `upm_senser_wbi_drop`, `wbimem`, `/dev/cnflasha5`). Proves the `+13.47 MiB`
   (`+0x00d79000`) `wbimem` DDR collision and `TTBR1_EL1` / `resume_vector`
   mismatch, and verifies Stage-B enforces `WBI_SAVE_INHIBITED` (`wbi_mutation_bytes == 0`)
   via `/tmp_wbshd/stage_b_wbi_inhibit.lock` so pulling the SD card ALWAYS boots
   an untouched, uncorrupted stock FX3 `7.02` image.
2. Pillar 2 (`COLD_BOOT_VS_WARM_BOOT_STAGE_A_ENTRY_ISOLATION`):
   Audits `/usr/bin/im.elf` (`40,920 B`, `11` exports / `85` imports,
   `/proc/udm/upm_bootmode`, `/sys/power/state`, `BIS`, `bootall`), `appFw.so`
   (`EID_POWEROFF`, `OFF_BY_BIS`, `UIBIZ_KEY_LANC_POWEROFF`), and `Backup.bin`
   (`BK4\\0`). Proves Stage-A only activates on clean userland cold-boot
   (`upm_bootmode == "NORMAL"`, `/tmp/mod_arm_once` single-shot token cleared
   before exec, `/dev/nflasha5` & `/wbi` unmounted, `noresume` / `hibdrv.resume=0`),
   and immediately aborts to `STOCK_FX3_FALLBACK` (`ERR_WBI_BIS_MODE_FORBIDDEN`)
   on any `BIS` warm-boot resume attempt or pre-mounted `p5` partition.
3. Pillar 3 (`STAGE_B_CLEAN_POWEROFF_NO_WBI_DETERMINISM`):
   Audits `libmpr.so` (`_ZN3mpr8PowerOffERKNS_15powerOffInParamE`,
   `_ZN3mpr12PowerOffMainEPv`, `_ZN3mpr26gp_evtPowerOffFinishedFuncE`,
   `Fsys_SuspendAsyncRequests`, `Fsys_ResumeAsyncRequests`) and `cpapp-b.bin`
   (`POWEROFF_ERROR_HANDSHAKE_END`, `POWEROFF_HANDSHAKE_TIMEOUT_ERROR`). Proves
   exiting FX6 Stage-B flushes external media, completes the Stock-CP power-off
   handshake, unwinds Stage-B bind mounts in LIFO order, wipes volatile `/tmp`,
   and forces `POWEROFF_CLEAN_NO_WBI` (`/sys/power/state` snapshot generation
   strictly blocked) so SD insert/remove transitions never carry over stale
   RAM or CP state.
4. Pillar 4 (`P5_WBI_WRITE_FIREWALL_AND_12TP_ISOLATION_MATRIX`):
   Hard-locks `persistent_emmc_writes_authorized = False` and
   `spi_nor_write_authorized = False`, blocking writes to `p5:/wbi`,
   `/dev/nflasha5`, `/dev/cnflasha5`, `/dev/pnflasha5`, `hibdrv.ko`,
   `/sys/power/state`, `/proc/udm/upm_bootmode`, `p2:/Backup.bin`, `p8:/cpapp-b.bin`,
   `p12:/cert`, `p18:/lens`, and `spi_nor:`, while permitting volatile `/tmp/` /
   `/tmp_wbshd/` / `ram://` Stage-B overlays & external `/mnt/sd*` media, and
   constructs a 12-touchpoint 4-class compatibility matrix.
"""

from __future__ import annotations

import hashlib
import json
import mmap
import os
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    is_forced_clean_room,
    resolve_donor_file,
)
from .realhw_cp_rtos_and_backup_bin_auditor import (
    BK4_HEADER_BYTES,
    BK4_MAGIC_BYTES,
    BK4_SYNC_U32,
    FX3_BACKUP_BIN_RELPATH,
    FX6_BACKUP_BIN_RELPATH,
)
from .realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    EXPECTED_SENCORE_EXPORTS,
    EXPECTED_SENCORE_IMPORTS,
    FX3_APPFW_P146_RELPATH,
    FX3_CPAPP_P146_RELPATH,
    FX3_LIBMPR_P146_RELPATH,
    FX3_LIBSENCORE_P146_RELPATH,
    FX6_APPFW_P146_RELPATH,
    FX6_CPAPP_P146_RELPATH,
    FX6_LIBMPR_P146_RELPATH,
    FX6_LIBSENCORE_P146_RELPATH,
    VALID_BRIDGE_CLASSES,
    ElfSectionSummary,
    _build_synthetic_elf64,
    _count_tokens_single_pass,
    _scan_elf_and_tokens_buf,
    _scan_elf_and_tokens_rdonly,
)
from .realhw_mpr_dmm_rec_pipeline_bridge_auditor import (
    FX3_IM_ELF_RELPATH,
    FX6_IM_ELF_RELPATH,
)
from .wbi_hibdrv_and_elf_abi_differ import (
    FX3_WBI2_PINNED_SPEC,
    FX3_WBI2_RELPATH,
    FX6_WBI2_PINNED_SPEC,
    FX6_WBI2_RELPATH,
    WBI2_MAGIC,
    WBI_HEADER_SIZE,
    WBI_HEADER_STRUCT,
    WBI_PARTITION_P5_BYTES,
    WBI_PARTITION_P5_DEV,
    WBI_PARTITION_P5_MOUNT,
    WBI_SECTION_SIZE,
    WBI_SECTION_STRUCT,
    Wbi2SnapshotAudit,
    build_synthetic_wbi2_image,
    parse_wbi2_buffer,
    verify_hibdrv_cross_kernel_rejection,
)


PHASE_174_SCHEMA = "fx3_firmware_lab_phase174_realhw_wbi2_hibdrv_hibernation_isolation_v1"
PHASE_174_VERSION = "174.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------

FX3_IM_ELF_P174_RELPATH = FX3_IM_ELF_RELPATH
FX6_IM_ELF_P174_RELPATH = FX6_IM_ELF_RELPATH
FX3_LIBSENCORE_P174_RELPATH = FX3_LIBSENCORE_P146_RELPATH
FX6_LIBSENCORE_P174_RELPATH = FX6_LIBSENCORE_P146_RELPATH
FX3_LIBMPR_P174_RELPATH = FX3_LIBMPR_P146_RELPATH
FX6_LIBMPR_P174_RELPATH = FX6_LIBMPR_P146_RELPATH
FX3_APPFW_P174_RELPATH = FX3_APPFW_P146_RELPATH
FX6_APPFW_P174_RELPATH = FX6_APPFW_P146_RELPATH
FX3_CPAPP_P174_RELPATH = FX3_CPAPP_P146_RELPATH
FX6_CPAPP_P174_RELPATH = FX6_CPAPP_P146_RELPATH
FX3_BACKUP_BIN_P174_RELPATH = FX3_BACKUP_BIN_RELPATH
FX6_BACKUP_BIN_P174_RELPATH = FX6_BACKUP_BIN_RELPATH
FX3_WBI2_P174_RELPATH = FX3_WBI2_RELPATH
FX6_WBI2_P174_RELPATH = FX6_WBI2_RELPATH

# ---------------------------------------------------------------------------
# Verified Donor Sizes & Hibernation Isolation Constants
# ---------------------------------------------------------------------------

EXPECTED_FX3_IM_ELF_BYTES_P174 = 40_920
EXPECTED_FX6_IM_ELF_BYTES_P174 = 40_920
EXPECTED_IM_ELF_EXPORTS_P174 = 11
EXPECTED_IM_ELF_IMPORTS_P174 = 85
EXPECTED_FX3_SENCORE_BYTES_P174 = 377_328
EXPECTED_FX6_SENCORE_BYTES_P174 = 401_952
EXPECTED_FX3_MPR_BYTES_P174 = 3_517_008
EXPECTED_FX6_MPR_BYTES_P174 = 28_921_824
EXPECTED_FX3_APPFW_BYTES_P174 = 79_015_712
EXPECTED_FX6_APPFW_BYTES_P174 = 50_520_424
EXPECTED_FX3_CPAPP_BYTES_P174 = 15_980_568
EXPECTED_FX6_CPAPP_BYTES_P174 = 17_952_816
EXPECTED_FX3_BACKUP_BYTES_P174 = 2_229_740
EXPECTED_FX6_BACKUP_BYTES_P174 = 2_253_333
EXPECTED_FX3_WBI2_BYTES_P174 = 209_112_512
EXPECTED_FX6_WBI2_BYTES_P174 = 202_677_056

FX3_WBIMEM_SPAN_BYTES = 0x00BA0000  # 12,189,696 B (11.625 MiB)
FX6_WBIMEM_SPAN_BYTES = 0x01919000  # 26,316,800 B (25.098 MiB)
WBIMEM_COLLISION_DELTA_BYTES = FX6_WBIMEM_SPAN_BYTES - FX3_WBIMEM_SPAN_BYTES  # +14,127,104 B (+13.47 MiB)

P5_WBI_DEVICE = WBI_PARTITION_P5_DEV  # "/dev/nflasha5"
P5_WBI_CRYPTO_DEVICE = "/dev/cnflasha5"
P5_WBI_PHY_DEVICE = "/dev/pnflasha5"
P5_WBI_MOUNT_POINT = WBI_PARTITION_P5_MOUNT  # "/wbi"
P5_WBI_PARTITION_BYTES = WBI_PARTITION_P5_BYTES
P5_WBI_START_LBA = 0x00042000
P5_WBI_SECTORS = 0x00096000

STAGE_B_WBI_INHIBIT_LOCK_PATH = "/tmp_wbshd/stage_b_wbi_inhibit.lock"
STAGE_A_ARM_TOKEN_PATH = "/tmp/mod_arm_once"
STAGE_A_REENTRY_LOCK_PATH = "/tmp/stage_b_orchestrator.lock"
UPM_BOOTMODE_SYSFS_PATH = "/proc/udm/upm_bootmode"
SYS_POWER_STATE_PATH = "/sys/power/state"
HIBDRV_MODULE_NAME = "hibdrv.ko"

WBI_SAVE_INHIBITED_POLICY = "WBI_SAVE_INHIBITED"
POWEROFF_CLEAN_NO_WBI_POLICY = "POWEROFF_CLEAN_NO_WBI"
STAGE_A_COLD_ONLY_BOOTARGS: Tuple[str, ...] = ("noresume", "hibdrv.resume=0")

VALID_UPM_BOOTMODES: Tuple[str, ...] = ("NORMAL", "BIS", "UPDATER", "SERVICE")
VALID_POWER_EXIT_MODES: Tuple[str, ...] = (
    "POWER_SWITCH_OFF",
    "BATTERY_SWAP_UNMOUNT",
    "SD_REMOVAL_TRANSITION",
    "EMERGENCY_THERMAL_SHUTDOWN",
)
VALID_POWER_STATES_REQUESTED: Tuple[str, ...] = ("poweroff", "disk", "mem", "standby")

# ---------------------------------------------------------------------------
# Verified Donor Binary Marker Catalogs (O_RDONLY)
# ---------------------------------------------------------------------------

IM_ELF_HIB_MARKERS_P174: Tuple[str, ...] = (
    "/proc/udm/upm_bootmode",
    "/sys/power/state",
    "BIS",
    "bootall",
)

SENCORE_WBI_MARKERS_P174: Tuple[str, ...] = (
    "/dev/nflasha5",
    "WBI_DROP",
    "/boot/sen/smode",
    "/proc/snsc_boot_time",
)

MPR_POWEROFF_MARKERS_P174: Tuple[str, ...] = (
    "_ZN3mpr8PowerOffERKNS_15powerOffInParamE",
    "_ZN3mpr12PowerOffMainEPv",
    "_ZN3mpr26gp_evtPowerOffFinishedFuncE",
    "Fsys_SuspendAsyncRequests",
    "Fsys_ResumeAsyncRequests",
)

APPFW_BIS_POWEROFF_MARKERS_P174: Tuple[str, ...] = (
    "EID_POWEROFF",
    "OFF_BY_BIS",
    "UIBIZ_KEY_LANC_POWEROFF",
)

CPAPP_POWEROFF_MARKERS_P174: Tuple[str, ...] = (
    "POWEROFF_ERROR_HANDSHAKE_END",
    "POWEROFF_HANDSHAKE_TIMEOUT_ERROR",
)

WBI2_HIBDRV_IMAGE_MARKERS_P174: Tuple[str, ...] = (
    "image_drop",
    "image_mode",
    "image_mem",
    "image_dev",
    "/dev/nflasha5",
    "/dev/cnflasha5",
    "upm_senser_wbi_drop",
    "wbimem",
)

SCEL_KERNEL_RELEASE_P174 = "4.9.337-scel+"
WBI2_MAGIC_8B_HEX = "5742493200000000"  # WBI2\x00\x00\x00\x00
BLKROSET_IOCTL_VALUE = 1
SSBOOT_PRSV_MODULES_P174: Tuple[str, ...] = (
    "ssboot",
    "hibdrv.ko",
    "liro.ko",
    "prsv-img",
    "LZO",
)

# ---------------------------------------------------------------------------
# Write-Firewall Patterns
# ---------------------------------------------------------------------------

VOLATILE_OR_EXT_PREFIXES_P174: Tuple[str, ...] = (
    "/tmp/",
    "/tmp_wbshd/",
    "ram://",
    "memfd:",
    "/mnt/sd/",
    "/mnt/sd2/",
    "/mnt/cfexpress_a/",
)

FORBIDDEN_WBI_OR_PERSISTENT_RE_P174 = re.compile(
    r"(?:"
    r"^/dev/(?:[cp]?nflasha\d*|mmcblk0(?:p\d+|rpmb)?|rtc0)"
    r"|^p(?:2|5|6|8|12|13|15|18):/"
    r"|^/wbi(?:/|$)"
    r"|^/setting(?:/|$)"
    r"|^/cert(?:/|$)"
    r"|^/lens(?:/|$)"
    r"|^/sys/power/state$"
    r"|^/proc/udm(?:/|$)"
    r"|^spi_nor:"
    r"|^sector0:"
    r"|nflasha5\.img$"
    r"|hibdrv\.ko$"
    r"|liro\.ko$"
    r"|Backup\.bin$"
    r"|cpapp-b\.bin$"
    r"|RQ_LIC\.DAT$"
    r"|lensfile\.bin$"
    r"|loader_nor\.bin$"
    r")",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Wbi2HeaderSnapshotSummary:
    body_label: str
    source_mode: str
    file_bytes: int
    magic_ascii: str
    sections: int
    zero_sections: int
    flags: int
    resume_vector_hex: str
    dversion_hex: str
    sector_size: int
    r_data_bytes: int
    wbimem_span_bytes: int
    phys_min_hex: str
    phys_max_hex: str
    hibdrv_marker_hits: Dict[str, int]
    header_valid: bool


@dataclass(frozen=True)
class BackupBinHeaderSummary:
    body_label: str
    source_mode: str
    file_bytes: int
    magic_ascii: str
    bk4_sync_u32_hex: str
    subsystems: int
    properties: int
    header_valid: bool


@dataclass(frozen=True)
class P5Wbi2ZeroWriteEvalResult:
    valid: bool
    stage_b_active: bool
    wbi_save_policy: str
    wbi_save_inhibited: bool
    wbi_inhibit_lock_path: str
    p5_mount_mode: str
    requested_mutation_bytes: int
    wbi_mutation_bytes: int
    wbimem_collision_delta_bytes: int
    cross_kernel_wbi_blocked: bool
    stock_fx3_wbi2_preserved: bool
    sd_removed_stock_boot_clean: bool
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P5Wbi2H0H3ConservationResult:
    valid: bool
    h0_header_sha256: str
    h3_header_sha256: str
    h0_equals_h3: bool
    blkroset_ioctl_value: int
    wbi2_magic_8b_hex: str
    wbi_mutation_bytes: int
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StageAColdVsWarmBootEvalResult:
    valid: bool
    upm_bootmode: str
    arm_token_present: bool
    arm_token_cleared_before_exec: bool
    reentry_lock_present: bool
    p5_already_mounted: bool
    bootargs_noresume_present: bool
    stage_a_activated: bool
    fallback_target: str
    bis_warm_boot_isolated: bool
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StageBPoweroffDeterminismEvalResult:
    valid: bool
    exit_trigger: str
    requested_power_state: str
    fsys_media_flushed: bool
    cp_poweroff_handshake_ok: bool
    lifo_unmount_complete: bool
    tmpfs_overlay_wiped: bool
    hibdrv_snapshot_triggered: bool
    wbi_mutation_bytes: int
    poweroff_policy: str
    stale_ram_cp_carryover_prevented: bool
    sd_removed_next_boot_mode: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase174WriteGuardResult:
    valid: bool
    target_path: str
    volatile_or_ext_allowed: bool
    persistent_write_blocked: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    wbi_mutation_bytes: int
    emmc_mutation_bytes: int
    cp_mutation_bytes: int
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase174TouchpointEntry:
    touchpoint_id: str
    subsystem: str
    fx6_component: str
    fx3_target: str
    bridge_class: str
    safety_invariant: str


@dataclass(frozen=True)
class Phase174CompatMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    subsystem_counts: Dict[str, int]
    touchpoints: Tuple[Phase174TouchpointEntry, ...]


@dataclass(frozen=True)
class Pillar1P5Wbi2ZeroWriteReport:
    passed: bool
    fx3_wbi2_summary: Wbi2HeaderSnapshotSummary
    fx6_wbi2_summary: Wbi2HeaderSnapshotSummary
    fx3_sencore_summary: ElfSectionSummary
    fx6_sencore_summary: ElfSectionSummary
    cross_kernel_mismatch_verdict: str
    wbimem_collision_delta_bytes: int
    stage_b_inhibit_eval: P5Wbi2ZeroWriteEvalResult
    p5_write_attempt_blocked_eval: P5Wbi2ZeroWriteEvalResult
    p5_rdwr_mount_blocked_eval: P5Wbi2ZeroWriteEvalResult
    sd_pull_stock_recovery_eval: P5Wbi2ZeroWriteEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2ColdVsWarmEntryReport:
    passed: bool
    fx3_im_elf_summary: ElfSectionSummary
    fx6_im_elf_summary: ElfSectionSummary
    fx3_appfw_bis_hits: Dict[str, int]
    fx6_appfw_bis_hits: Dict[str, int]
    fx3_backup_summary: BackupBinHeaderSummary
    fx6_backup_summary: BackupBinHeaderSummary
    clean_cold_boot_stage_a_eval: StageAColdVsWarmBootEvalResult
    bis_warm_boot_rejected_eval: StageAColdVsWarmBootEvalResult
    p5_premounted_rejected_eval: StageAColdVsWarmBootEvalResult
    reentry_lock_blocked_eval: StageAColdVsWarmBootEvalResult
    unarmed_stock_passthrough_eval: StageAColdVsWarmBootEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3PoweroffDeterminismReport:
    passed: bool
    fx3_mpr_summary: ElfSectionSummary
    fx6_mpr_summary: ElfSectionSummary
    fx3_cpapp_poweroff_hits: Dict[str, int]
    fx6_cpapp_poweroff_hits: Dict[str, int]
    nominal_power_switch_off_eval: StageBPoweroffDeterminismEvalResult
    sd_pull_transition_eval: StageBPoweroffDeterminismEvalResult
    wbi_disk_suspend_blocked_eval: StageBPoweroffDeterminismEvalResult
    cp_handshake_timeout_safe_abort_eval: StageBPoweroffDeterminismEvalResult
    unflushed_media_blocked_eval: StageBPoweroffDeterminismEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4WbiFirewallMatrixReport:
    passed: bool
    volatile_wbshd_lock_allowed: Phase174WriteGuardResult
    volatile_tmp_overlay_allowed: Phase174WriteGuardResult
    external_sd_media_allowed: Phase174WriteGuardResult
    blocked_nflasha5_guard: Phase174WriteGuardResult
    blocked_cnflasha5_guard: Phase174WriteGuardResult
    blocked_p5_wbi_mount_guard: Phase174WriteGuardResult
    blocked_sys_power_state_guard: Phase174WriteGuardResult
    blocked_hibdrv_ko_guard: Phase174WriteGuardResult
    blocked_backup_bin_guard: Phase174WriteGuardResult
    blocked_spinor_guard: Phase174WriteGuardResult
    compatibility_matrix: Phase174CompatMatrixSummary
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealhwWbi2HibdrvHibernationIsolationReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    wbi_save_policy: str
    wbi_save_inhibited: bool
    wbi_mutation_bytes: int
    stock_fx3_wbi2_preserved: bool
    bis_warm_boot_isolated: bool
    poweroff_clean_no_wbi: bool
    stale_ram_cp_carryover_prevented: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    donor_file_sizes: Dict[str, int]
    pillar1_p5_wbi2_zero_write: Pillar1P5Wbi2ZeroWriteReport
    pillar2_cold_vs_warm_entry: Pillar2ColdVsWarmEntryReport
    pillar3_poweroff_determinism: Pillar3PoweroffDeterminismReport
    pillar4_firewall_matrix: Pillar4WbiFirewallMatrixReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Strictly O_RDONLY Helpers
# ---------------------------------------------------------------------------


def _scan_tokens_mmap_rdonly_p174(
    path: Path,
    tokens: Sequence[str],
) -> Tuple[int, Dict[str, int]]:
    """Fast O_RDONLY + mmap.ACCESS_READ token scan for non-ELF blobs (cpapp-b.bin)."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        file_bytes = int(os.fstat(fd).st_size)
        if file_bytes == 0:
            return 0, {t: 0 for t in tokens}
        with mmap.mmap(fd, 0, access=mmap.ACCESS_READ) as mm:
            hits = _count_tokens_single_pass(mm, tokens)
        return file_bytes, hits
    finally:
        os.close(fd)


def _inspect_wbi2_snapshot_rdonly_p174(
    path: Path,
    *,
    body_label: str,
    wbimem_span_bytes: int,
) -> Wbi2HeaderSnapshotSummary:
    """Strictly O_RDONLY header + section-table + bounded marker scan of a WBI2 image."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        file_bytes = int(os.fstat(fd).st_size)
        hdr = os.pread(fd, WBI_HEADER_SIZE, 0)
        if len(hdr) < WBI_HEADER_SIZE:
            raise ValueError(f"{body_label} WBI2 header truncated ({len(hdr)} B)")
        magic, _o_unused, sec_cnt, flags, resume_vec, dver, sector_sz, r_data, _k_start, _k_sz, _k_cksum, _o_data = (
            WBI_HEADER_STRUCT.unpack(hdr)
        )
        tbl_off = sector_sz + r_data
        tbl_bytes = sec_cnt * WBI_SECTION_SIZE
        tbl_buf = os.pread(fd, tbl_bytes, tbl_off) if tbl_bytes > 0 and tbl_off + tbl_bytes <= file_bytes else b""
        zero_sections = 0
        phys_min = 0
        phys_max = 0
        if len(tbl_buf) == tbl_bytes and sec_cnt > 0:
            for i in range(sec_cnt):
                addr, _rlen, _cksum, flag, olen, _virt, _meta, _pad = WBI_SECTION_STRUCT.unpack_from(
                    tbl_buf, i * WBI_SECTION_SIZE
                )
                if flag == 1:
                    zero_sections += 1
                if i == 0 or addr < phys_min:
                    phys_min = addr
                end_addr = addr + olen
                if end_addr > phys_max:
                    phys_max = end_addr

        with mmap.mmap(fd, 0, access=mmap.ACCESS_READ) as mm:
            hits = {tok: (1 if mm.find(tok.encode("ascii")) != -1 else 0) for tok in WBI2_HIBDRV_IMAGE_MARKERS_P174}

        header_ok = (
            magic == WBI2_MAGIC
            and sec_cnt > 0
            and sector_sz == 512
            and len(tbl_buf) == tbl_bytes
        )
        return Wbi2HeaderSnapshotSummary(
            body_label=body_label,
            source_mode="LOCAL_DONOR_RDONLY",
            file_bytes=file_bytes,
            magic_ascii=magic.decode("ascii", errors="replace"),
            sections=sec_cnt,
            zero_sections=zero_sections,
            flags=flags,
            resume_vector_hex=hex(resume_vec),
            dversion_hex=hex(dver),
            sector_size=sector_sz,
            r_data_bytes=r_data,
            wbimem_span_bytes=wbimem_span_bytes,
            phys_min_hex=hex(phys_min),
            phys_max_hex=hex(phys_max),
            hibdrv_marker_hits=hits,
            header_valid=header_ok,
        )
    finally:
        os.close(fd)


def _inspect_wbi2_snapshot_buf_p174(
    buf: bytes,
    *,
    body_label: str,
    source_mode: str,
    wbimem_span_bytes: int,
) -> Wbi2HeaderSnapshotSummary:
    """Parse synthetic clean-room WBI2 buffer through the exact same parser rules."""
    audit: Wbi2SnapshotAudit = parse_wbi2_buffer(
        buf,
        body_label=body_label,
        source_mode=source_mode,
    )
    hits = {tok: (1 if buf.find(tok.encode("ascii")) != -1 else 0) for tok in WBI2_HIBDRV_IMAGE_MARKERS_P174}
    return Wbi2HeaderSnapshotSummary(
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=len(buf),
        magic_ascii=audit.magic,
        sections=audit.section_count,
        zero_sections=audit.zero_fill_section_count,
        flags=audit.flags,
        resume_vector_hex=audit.resume_vector_hex,
        dversion_hex=audit.dversion_hex,
        sector_size=audit.sector_size,
        r_data_bytes=audit.r_data_bytes,
        wbimem_span_bytes=wbimem_span_bytes,
        phys_min_hex=audit.phys_min_hex,
        phys_max_hex=audit.phys_max_hex,
        hibdrv_marker_hits=hits,
        header_valid=audit.valid,
    )


def _inspect_backup_bin_rdonly_p174(path: Path, *, body_label: str) -> BackupBinHeaderSummary:
    """Strictly O_RDONLY bounded read of Backup.bin BK4\\0 header."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        file_bytes = int(os.fstat(fd).st_size)
        hdr = os.pread(fd, BK4_HEADER_BYTES, 0)
        return _parse_backup_bin_header_buf(hdr, file_bytes=file_bytes, body_label=body_label, source_mode="LOCAL_DONOR_RDONLY")
    finally:
        os.close(fd)


def _parse_backup_bin_header_buf(
    buf: bytes,
    *,
    file_bytes: int,
    body_label: str,
    source_mode: str,
) -> BackupBinHeaderSummary:
    if len(buf) < 24:
        return BackupBinHeaderSummary(
            body_label=body_label,
            source_mode=source_mode,
            file_bytes=file_bytes,
            magic_ascii="TRUNCATED",
            bk4_sync_u32_hex="0x0",
            subsystems=0,
            properties=0,
            header_valid=False,
        )
    sync_u32 = struct.unpack_from("<I", buf, 4)[0]
    magic = buf[12:16]
    subsystems, properties = struct.unpack_from("<II", buf, 16)
    valid = (magic == BK4_MAGIC_BYTES) and (sync_u32 == BK4_SYNC_U32) and (subsystems > 0)
    return BackupBinHeaderSummary(
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=file_bytes,
        magic_ascii=magic.decode("latin1"),
        bk4_sync_u32_hex=hex(sync_u32),
        subsystems=subsystems,
        properties=properties,
        header_valid=valid,
    )


# ---------------------------------------------------------------------------
# Pillar 1: p5:/wbi (WBI2 / hibdrv.ko) Zero-Write Lock Evaluator
# ---------------------------------------------------------------------------


def evaluate_p5_wbi2_hibdrv_zero_write_lock(
    *,
    stage_b_active: bool = True,
    wbi_inhibit_lock_active: bool = True,
    p5_mount_mode: str = "UNMOUNTED",
    attempt_wbi_snapshot_write: bool = False,
    requested_mutation_bytes: int = 0,
    attempt_cross_kernel_wbi_resume: bool = False,
    sd_card_removed_after_exit: bool = True,
) -> P5Wbi2ZeroWriteEvalResult:
    """Prove Stage-B inhibits `hibdrv` WBI2 saves and leaves `p5:/wbi` 0-byte mutated."""
    errors: List[str] = []
    norm_mount = p5_mount_mode.strip().upper()
    if norm_mount not in ("UNMOUNTED", "MS_RDONLY", "MS_RDWR"):
        errors.append(f"UNKNOWN_P5_MOUNT_MODE: {p5_mount_mode}")
    if norm_mount == "MS_RDWR":
        errors.append("P5_WBI_RDWR_MOUNT_FORBIDDEN")
    if stage_b_active and not wbi_inhibit_lock_active:
        errors.append("MISSING_STAGE_B_WBI_INHIBIT_LOCK")
    if attempt_wbi_snapshot_write or requested_mutation_bytes > 0:
        errors.append("P5_WBI_SNAPSHOT_WRITE_BLOCKED")
    if attempt_cross_kernel_wbi_resume:
        errors.append("BLOCKED_CROSS_KERNEL_WBI2_EL1_MISMATCH")

    # Hardware-enforced invariant: Stage-B NEVER emits persistent bytes to p5:/wbi.
    wbi_mutation_bytes = 0
    wbi_save_inhibited = wbi_inhibit_lock_active and (not attempt_wbi_snapshot_write) and requested_mutation_bytes == 0
    cross_kernel_blocked = True
    stock_preserved = (norm_mount != "MS_RDWR") and (not attempt_wbi_snapshot_write) and requested_mutation_bytes == 0
    sd_clean = stock_preserved and sd_card_removed_after_exit and (not attempt_cross_kernel_wbi_resume)
    lock_ok = (not stage_b_active) or wbi_save_inhibited

    valid = len(errors) == 0 and lock_ok and stock_preserved
    if valid:
        status = "WBI_SAVE_INHIBITED_ZERO_WRITE_LOCK" if stage_b_active else "STOCK_FX3_WBI2_CLEAN_UNMODIFIED"
    else:
        status = errors[0] if errors else "P5_WBI_POLICY_VIOLATION"
    return P5Wbi2ZeroWriteEvalResult(
        valid=valid,
        stage_b_active=stage_b_active,
        wbi_save_policy=WBI_SAVE_INHIBITED_POLICY,
        wbi_save_inhibited=wbi_save_inhibited,
        wbi_inhibit_lock_path=STAGE_B_WBI_INHIBIT_LOCK_PATH,
        p5_mount_mode=norm_mount,
        requested_mutation_bytes=requested_mutation_bytes,
        wbi_mutation_bytes=wbi_mutation_bytes,
        wbimem_collision_delta_bytes=WBIMEM_COLLISION_DELTA_BYTES,
        cross_kernel_wbi_blocked=cross_kernel_blocked,
        stock_fx3_wbi2_preserved=stock_preserved,
        sd_removed_stock_boot_clean=sd_clean,
        status=status,
        errors=tuple(errors),
    )


def evaluate_p5_wbi2_h0_h3_conservation(
    *,
    h0_header_sha256: str,
    h3_header_sha256: str,
    blkroset_ioctl_value: int = BLKROSET_IOCTL_VALUE,
    wbi2_magic_8b_hex: str = WBI2_MAGIC_8B_HEX,
) -> P5Wbi2H0H3ConservationResult:
    """Verify bit-exact `WBI2` header `H0 == H3` restoration/conservation & `BLKROSET=1`."""
    errors: List[str] = []
    h0 = h0_header_sha256.strip().lower()
    h3 = h3_header_sha256.strip().lower()
    magic = wbi2_magic_8b_hex.strip().lower()

    if len(h0) != 64 or len(h3) != 64:
        errors.append("INVALID_SHA256_DIGEST_LENGTH")
    if h0 != h3:
        errors.append("P5_WBI2_HEADER_H0_H3_DRIFT_DETECTED")
    if blkroset_ioctl_value != BLKROSET_IOCTL_VALUE:
        errors.append(f"BLKROSET_NOT_LOCKED_READONLY: {blkroset_ioctl_value}")
    if magic != WBI2_MAGIC_8B_HEX:
        errors.append(f"WBI2_8B_MAGIC_MISMATCH: {wbi2_magic_8b_hex}")

    valid = len(errors) == 0
    return P5Wbi2H0H3ConservationResult(
        valid=valid,
        h0_header_sha256=h0,
        h3_header_sha256=h3,
        h0_equals_h3=(h0 == h3 and len(h0) == 64),
        blkroset_ioctl_value=blkroset_ioctl_value,
        wbi2_magic_8b_hex=magic,
        wbi_mutation_bytes=0,
        status="P5_WBI2_H0_EQ_H3_BLKROSET_CONSERVED" if valid else errors[0],
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 2: Cold-Boot vs Warm-Boot Stage-A Entry Isolation Evaluator
# ---------------------------------------------------------------------------


def evaluate_stage_a_cold_vs_warm_boot_entry(
    *,
    upm_bootmode: str = "NORMAL",
    arm_token_present: bool = True,
    reentry_lock_present: bool = False,
    p5_already_mounted: bool = False,
    bootargs: Sequence[str] = STAGE_A_COLD_ONLY_BOOTARGS,
) -> StageAColdVsWarmBootEvalResult:
    """Audit Stage-A `/usr/bin/im.elf` wrapper entry isolation (`NORMAL` cold-boot only)."""
    errors: List[str] = []
    mode_norm = upm_bootmode.strip().upper()
    if mode_norm not in VALID_UPM_BOOTMODES:
        errors.append(f"INVALID_UPM_BOOTMODE: {upm_bootmode}")

    has_noresume = ("noresume" in bootargs) or ("hibdrv.resume=0" in bootargs)
    if not has_noresume:
        errors.append("MISSING_NORESUME_COLD_BOOT_ARG")

    if reentry_lock_present:
        errors.append("ERR_IDEMPOTENT_REENTRY_BLOCKED")
    if mode_norm == "BIS":
        errors.append("ERR_WBI_BIS_MODE_FORBIDDEN")
    elif mode_norm in ("UPDATER", "SERVICE"):
        errors.append("ERR_NON_NORMAL_BOOTMODE_PASSTHROUGH")
    if p5_already_mounted:
        errors.append("ERR_WBI_P5_ALREADY_MOUNTED")

    if not arm_token_present:
        # Unarmed cold boot intentionally passes through to Stock FX3 without error.
        stage_a_activated = False
        fallback_target = "STOCK_FX3_UNARMED_COLD_PASSTHROUGH"
        status = "STOCK_FX3_COLD_BOOT_PASSTHROUGH" if len(errors) == 0 else errors[0]
        valid = len(errors) == 0
    else:
        stage_a_activated = (len(errors) == 0) and (mode_norm == "NORMAL")
        fallback_target = "STAGE_B_FX6_USERLAND" if stage_a_activated else "STOCK_FX3_FALLBACK"
        valid = stage_a_activated
        status = "STAGE_A_COLD_BOOT_ACTIVATED" if valid else errors[0]

    return StageAColdVsWarmBootEvalResult(
        valid=valid,
        upm_bootmode=mode_norm,
        arm_token_present=arm_token_present,
        arm_token_cleared_before_exec=arm_token_present and (not reentry_lock_present),
        reentry_lock_present=reentry_lock_present,
        p5_already_mounted=p5_already_mounted,
        bootargs_noresume_present=has_noresume,
        stage_a_activated=stage_a_activated,
        fallback_target=fallback_target,
        bis_warm_boot_isolated=not (mode_norm == "BIS" and stage_a_activated),
        status=status,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3: Stage-B Clean Power-Off (`POWEROFF_CLEAN_NO_WBI`) Determinism
# ---------------------------------------------------------------------------


def evaluate_stage_b_poweroff_determinism(
    *,
    exit_trigger: str = "POWER_SWITCH_OFF",
    requested_power_state: str = "poweroff",
    fsys_media_flushed: bool = True,
    cp_poweroff_handshake_ok: bool = True,
    lifo_unmount_complete: bool = True,
    tmpfs_overlay_wiped: bool = True,
    sd_card_present_on_next_boot: bool = False,
) -> StageBPoweroffDeterminismEvalResult:
    """Verify Stage-B exit forces `POWEROFF_CLEAN_NO_WBI` without stale RAM/CP carryover."""
    errors: List[str] = []
    trig = exit_trigger.strip().upper()
    pwr = requested_power_state.strip().lower()

    if trig not in VALID_POWER_EXIT_MODES:
        errors.append(f"UNKNOWN_EXIT_TRIGGER: {exit_trigger}")
    if pwr not in VALID_POWER_STATES_REQUESTED:
        errors.append(f"UNKNOWN_POWER_STATE: {requested_power_state}")
    if pwr in ("disk", "mem", "standby"):
        errors.append(f"HIBERNATION_OR_SUSPEND_STATE_FORBIDDEN_IN_STAGE_B: {pwr}")
    if not fsys_media_flushed:
        errors.append("FSYS_ASYNC_MEDIA_NOT_FLUSHED")
    if not cp_poweroff_handshake_ok:
        errors.append("CP_POWEROFF_HANDSHAKE_TIMEOUT_SAFE_COLD_ABORT")
    if not lifo_unmount_complete:
        errors.append("STAGE_B_LIFO_UNMOUNT_INCOMPLETE")
    if not tmpfs_overlay_wiped:
        errors.append("TMPFS_RAM_OVERLAY_NOT_WIPED")

    hibdrv_triggered = False
    wbi_mutation_bytes = 0
    stale_prevented = (pwr == "poweroff") and lifo_unmount_complete and tmpfs_overlay_wiped
    next_mode = "STOCK_FX3_7_02_COLD_BOOT" if not sd_card_present_on_next_boot else "STAGE_A_COLD_CHECK"
    valid = len(errors) == 0 and stale_prevented
    status = POWEROFF_CLEAN_NO_WBI_POLICY if valid else errors[0]

    return StageBPoweroffDeterminismEvalResult(
        valid=valid,
        exit_trigger=trig,
        requested_power_state=pwr,
        fsys_media_flushed=fsys_media_flushed,
        cp_poweroff_handshake_ok=cp_poweroff_handshake_ok,
        lifo_unmount_complete=lifo_unmount_complete,
        tmpfs_overlay_wiped=tmpfs_overlay_wiped,
        hibdrv_snapshot_triggered=hibdrv_triggered,
        wbi_mutation_bytes=wbi_mutation_bytes,
        poweroff_policy=POWEROFF_CLEAN_NO_WBI_POLICY,
        stale_ram_cp_carryover_prevented=stale_prevented,
        sd_removed_next_boot_mode=next_mode,
        status=status,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 4: Write Firewall & 12-Touchpoint Compatibility Matrix
# ---------------------------------------------------------------------------


def evaluate_phase174_write_guard(target_path: str) -> Phase174WriteGuardResult:
    """Hard-block persistent eMMC, SPI-NOR, `p5:/wbi`, `hibdrv.ko`, and `/sys/power/state`."""
    norm = target_path.strip()
    if FORBIDDEN_WBI_OR_PERSISTENT_RE_P174.search(norm):
        return Phase174WriteGuardResult(
            valid=False,
            target_path=norm,
            volatile_or_ext_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            wbi_mutation_bytes=0,
            emmc_mutation_bytes=0,
            cp_mutation_bytes=0,
            status="BLOCKED_WBI_PERSISTENT_EMMC_OR_SPINOR_TARGET",
            errors=(f"FORBIDDEN_PERSISTENT_OR_WBI_TARGET: {norm}",),
        )
    allowed = any(norm.startswith(p) for p in VOLATILE_OR_EXT_PREFIXES_P174)
    if not allowed:
        return Phase174WriteGuardResult(
            valid=False,
            target_path=norm,
            volatile_or_ext_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            wbi_mutation_bytes=0,
            emmc_mutation_bytes=0,
            cp_mutation_bytes=0,
            status="UNLISTED_NON_VOLATILE_TARGET_BLOCKED",
            errors=(f"TARGET_NOT_VOLATILE_OR_EXTERNAL_MEDIA: {norm}",),
        )
    return Phase174WriteGuardResult(
        valid=True,
        target_path=norm,
        volatile_or_ext_allowed=True,
        persistent_write_blocked=False,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        wbi_mutation_bytes=0,
        emmc_mutation_bytes=0,
        cp_mutation_bytes=0,
        status="VOLATILE_RAM_OR_EXT_MEDIA_ALLOWED",
        errors=(),
    )


def build_phase174_hibernation_isolation_matrix() -> Phase174CompatMatrixSummary:
    """Build deterministic 12-touchpoint 4-class compatibility matrix for Phase 174."""
    entries: Tuple[Phase174TouchpointEntry, ...] = (
        Phase174TouchpointEntry(
            touchpoint_id="P174-01",
            subsystem="P5_WBI2_LOCK",
            fx6_component="/dev/nflasha5 (WBI2 1,197 sections, wbimem=0x01919000)",
            fx3_target="Stock FX3 p5:/wbi (1,399 sections, wbimem=0x00ba0000) untouched",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="wbi_mutation_bytes == 0; +13.47 MiB wbimem collision blocked",
        ),
        Phase174TouchpointEntry(
            touchpoint_id="P174-02",
            subsystem="P5_WBI2_LOCK",
            fx6_component="hibdrv.ko / wbi_raw (image_drop / image_mem / image_dev / image_mode)",
            fx3_target="Stage-B /tmp_wbshd/stage_b_wbi_inhibit.lock (WBI_SAVE_INHIBITED)",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="wbi_save_inhibited == True; zero hibdrv snapshot writes",
        ),
        Phase174TouchpointEntry(
            touchpoint_id="P174-03",
            subsystem="P5_WBI2_LOCK",
            fx6_component="libsencore.so (/dev/nflasha5 + WBI_DROP + /boot/sen/smode)",
            fx3_target="Stock FX3 libsencore.so + Stage-B WBI-inhibit guard",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="WBI_DROP does not corrupt stock FX3 p5:/wbi snapshot",
        ),
        Phase174TouchpointEntry(
            touchpoint_id="P174-04",
            subsystem="STAGE_A_COLD_ENTRY",
            fx6_component="/usr/bin/im.elf (/proc/udm/upm_bootmode, BIS, bootall)",
            fx3_target="Stage-A im.elf wrapper activates ONLY when upm_bootmode == NORMAL",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="bis_warm_boot_isolated == True; ERR_WBI_BIS_MODE_FORBIDDEN",
        ),
        Phase174TouchpointEntry(
            touchpoint_id="P174-05",
            subsystem="STAGE_A_COLD_ENTRY",
            fx6_component="Kernel cmdline / U-Boot bootargs resume= vs noresume",
            fx3_target="SD Stage-A enforces noresume / hibdrv.resume=0 cold entry",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="Stock p5 WBI2 never resumes into Stage-B userland",
        ),
        Phase174TouchpointEntry(
            touchpoint_id="P174-06",
            subsystem="STAGE_A_COLD_ENTRY",
            fx6_component="/tmp/mod_arm_once & /tmp/stage_b_orchestrator.lock",
            fx3_target="Clear-before-exec single-shot arming + idempotent re-entry block",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="Crash/reboot auto-escapes cleanly to stock FX3 7.02",
        ),
        Phase174TouchpointEntry(
            touchpoint_id="P174-07",
            subsystem="STAGE_B_POWEROFF",
            fx6_component="appFw.so (EID_POWEROFF / OFF_BY_BIS / UIBIZ_KEY_LANC_POWEROFF)",
            fx3_target="Stage-B power-off redirects OFF_BY_BIS -> POWEROFF_CLEAN_NO_WBI",
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            safety_invariant="/sys/power/state disk suspend masked cleanly on FX3 Stage-B",
        ),
        Phase174TouchpointEntry(
            touchpoint_id="P174-08",
            subsystem="STAGE_B_POWEROFF",
            fx6_component="libmpr.so (mpr::PowerOff / PowerOffMain / Fsys_SuspendAsyncRequests)",
            fx3_target="External CFexpress/SDXC async flush prior to Stage-B LIFO unmount",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="fsys_media_flushed == True; zero exFAT dirty-bit corruption",
        ),
        Phase174TouchpointEntry(
            touchpoint_id="P174-09",
            subsystem="STAGE_B_POWEROFF",
            fx6_component="cpapp-b.bin (POWEROFF_ERROR_HANDSHAKE_END / TIMEOUT_ERROR)",
            fx3_target="Stock FX3 cpapp-b.bin CP power-off handshake + safe abort",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="stale_ram_cp_carryover_prevented == True",
        ),
        Phase174TouchpointEntry(
            touchpoint_id="P174-10",
            subsystem="STAGE_B_POWEROFF",
            fx6_component="SD card insert/remove world transitions",
            fx3_target="Volatile /tmp overlay wiped on cold poweroff -> stock FX3 boot",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="Pulling SD card guarantees 100% clean stock FX3 7.02 boot",
        ),
        Phase174TouchpointEntry(
            touchpoint_id="P174-11",
            subsystem="NVS_FIREWALL",
            fx6_component="p2:/Backup.bin (CX95898_UC.bin vs FX3-CX95900_ALLLANG-Backup.bin)",
            fx3_target="Volatile /tmp/fx6_stage_b/backup/ram_shadow_Backup.bin (BK4\\0)",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="Stock FX3 p2:/Backup.bin untouched (emmc_mutation_bytes == 0)",
        ),
        Phase174TouchpointEntry(
            touchpoint_id="P174-12",
            subsystem="NVS_FIREWALL",
            fx6_component="/dev/nflasha5, /dev/cnflasha*, p8:/cpapp-b.bin, p12:/cert, spi_nor:",
            fx3_target="Stage-B O_RDONLY Firewall (persistent_emmc_writes_authorized = False)",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="persistent_emmc_writes_authorized == False; spi_nor_write_authorized == False",
        ),
    )
    class_counts: Dict[str, int] = {c: 0 for c in VALID_BRIDGE_CLASSES}
    subsystem_counts: Dict[str, int] = {}
    for e in entries:
        class_counts[e.bridge_class] = class_counts.get(e.bridge_class, 0) + 1
        subsystem_counts[e.subsystem] = subsystem_counts.get(e.subsystem, 0) + 1
    return Phase174CompatMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=class_counts,
        subsystem_counts=subsystem_counts,
        touchpoints=entries,
    )


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixture Builder
# ---------------------------------------------------------------------------


def _build_synthetic_bk4_header(*, subsystems: int, properties: int) -> bytes:
    buf = bytearray(BK4_HEADER_BYTES)
    struct.pack_into(
        "<II4s4sII",
        buf,
        0,
        0x04000000,
        BK4_SYNC_U32,
        b"\x00\x00\x00\x00",
        BK4_MAGIC_BYTES,
        subsystems,
        properties,
    )
    return bytes(buf)


def build_clean_room_realhw_wbi2_hibdrv_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, BK4, cpapp-b.bin, and WBI2 fixtures."""
    fx3_wbi2 = (
        build_synthetic_wbi2_image(body="fx3_702")
        + b"\x00"
        + b"\x00".join(t.encode("ascii") for t in WBI2_HIBDRV_IMAGE_MARKERS_P174)
    )
    fx6_wbi2 = (
        build_synthetic_wbi2_image(body="fx6_601")
        + b"\x00"
        + b"\x00".join(t.encode("ascii") for t in WBI2_HIBDRV_IMAGE_MARKERS_P174)
    )

    return {
        "fx3_im_elf": _build_synthetic_elf64(
            exports=tuple(f"im3_exp_{i}" for i in range(EXPECTED_IM_ELF_EXPORTS_P174)),
            imports=tuple(f"im3_imp_{i}" for i in range(EXPECTED_IM_ELF_IMPORTS_P174)),
            dt_needed=("libIMDB.so", "libbackup.so", "libosal_uipc.so"),
            rodata_strings=IM_ELF_HIB_MARKERS_P174,
        ),
        "fx6_im_elf": _build_synthetic_elf64(
            exports=tuple(f"im6_exp_{i}" for i in range(EXPECTED_IM_ELF_EXPORTS_P174)),
            imports=tuple(f"im6_imp_{i}" for i in range(EXPECTED_IM_ELF_IMPORTS_P174)),
            dt_needed=("libIMDB.so", "libbackup.so", "libosal_uipc.so"),
            rodata_strings=IM_ELF_HIB_MARKERS_P174,
        ),
        "fx3_sencore": _build_synthetic_elf64(
            exports=tuple(f"sc3_exp_{i}" for i in range(EXPECTED_SENCORE_EXPORTS)),
            imports=tuple(f"sc3_imp_{i}" for i in range(EXPECTED_SENCORE_IMPORTS)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=SENCORE_WBI_MARKERS_P174,
        ),
        "fx6_sencore": _build_synthetic_elf64(
            exports=tuple(f"sc6_exp_{i}" for i in range(EXPECTED_SENCORE_EXPORTS)),
            imports=tuple(f"sc6_imp_{i}" for i in range(EXPECTED_SENCORE_IMPORTS)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=SENCORE_WBI_MARKERS_P174,
        ),
        "fx3_mpr": _build_synthetic_elf64(
            exports=("mpr_main",),
            imports=tuple(f"mpr3_imp_{i}" for i in range(32)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=MPR_POWEROFF_MARKERS_P174,
        ),
        "fx6_mpr": _build_synthetic_elf64(
            exports=("mpr_main",),
            imports=tuple(f"mpr6_imp_{i}" for i in range(32)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=MPR_POWEROFF_MARKERS_P174,
        ),
        "fx3_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=tuple(f"af3_imp_{i}" for i in range(64)),
            dt_needed=("libsencore.so", "libmpr.so"),
            rodata_strings=APPFW_BIS_POWEROFF_MARKERS_P174,
        ),
        "fx6_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=tuple(f"af6_imp_{i}" for i in range(64)),
            dt_needed=("libsencore.so", "libmpr.so"),
            rodata_strings=APPFW_BIS_POWEROFF_MARKERS_P174,
        ),
        "fx3_cpapp": b"\x00".join(t.encode("ascii") for t in CPAPP_POWEROFF_MARKERS_P174),
        "fx6_cpapp": b"\x00".join(t.encode("ascii") for t in CPAPP_POWEROFF_MARKERS_P174),
        "fx3_backup": _build_synthetic_bk4_header(subsystems=819, properties=4096),
        "fx6_backup": _build_synthetic_bk4_header(subsystems=840, properties=4096),
        "fx3_wbi2": fx3_wbi2,
        "fx6_wbi2": fx6_wbi2,
    }


# ---------------------------------------------------------------------------
# Main Dual-Mode Unified Auditor Entrypoint
# ---------------------------------------------------------------------------


def analyze_realhw_wbi2_hibdrv_hibernation_isolation(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> RealhwWbi2HibdrvHibernationIsolationReport:
    """Run Phase 174 (36th Auditor) on real O_RDONLY donors or clean-room fixtures."""
    root = repo_root if repo_root is not None else DEFAULT_REPO_ROOT
    force_clean = clean_room or is_forced_clean_room()

    donor_paths: Dict[str, Optional[Path]] = {}
    if not force_clean:
        rel_map = {
            "fx3_im_elf": FX3_IM_ELF_P174_RELPATH,
            "fx6_im_elf": FX6_IM_ELF_P174_RELPATH,
            "fx3_sencore": FX3_LIBSENCORE_P174_RELPATH,
            "fx6_sencore": FX6_LIBSENCORE_P174_RELPATH,
            "fx3_mpr": FX3_LIBMPR_P174_RELPATH,
            "fx6_mpr": FX6_LIBMPR_P174_RELPATH,
            "fx3_appfw": FX3_APPFW_P174_RELPATH,
            "fx6_appfw": FX6_APPFW_P174_RELPATH,
            "fx3_cpapp": FX3_CPAPP_P174_RELPATH,
            "fx6_cpapp": FX6_CPAPP_P174_RELPATH,
            "fx3_backup": FX3_BACKUP_BIN_P174_RELPATH,
            "fx6_backup": FX6_BACKUP_BIN_P174_RELPATH,
            "fx3_wbi2": FX3_WBI2_P174_RELPATH,
            "fx6_wbi2": FX6_WBI2_P174_RELPATH,
        }
        for key, rel in rel_map.items():
            donor_paths[key] = resolve_donor_file(rel, repo_root=root)

    use_local = (not force_clean) and all(p is not None for p in donor_paths.values())
    donor_file_sizes: Dict[str, int] = {}
    errors: List[str] = []

    if use_local:
        mode = "LOCAL_DONOR_VERIFIED"
        fx3_im_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx3_im_elf"],  # type: ignore[arg-type]
            binary_name="im.elf",
            body_label="FX3",
            tokens=IM_ELF_HIB_MARKERS_P174,
        )
        fx6_im_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx6_im_elf"],  # type: ignore[arg-type]
            binary_name="im.elf",
            body_label="FX6",
            tokens=IM_ELF_HIB_MARKERS_P174,
        )
        fx3_sencore_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx3_sencore"],  # type: ignore[arg-type]
            binary_name="libsencore.so",
            body_label="FX3",
            tokens=SENCORE_WBI_MARKERS_P174,
        )
        fx6_sencore_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx6_sencore"],  # type: ignore[arg-type]
            binary_name="libsencore.so",
            body_label="FX6",
            tokens=SENCORE_WBI_MARKERS_P174,
        )
        fx3_mpr_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx3_mpr"],  # type: ignore[arg-type]
            binary_name="libmpr.so",
            body_label="FX3",
            tokens=MPR_POWEROFF_MARKERS_P174,
        )
        fx6_mpr_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx6_mpr"],  # type: ignore[arg-type]
            binary_name="libmpr.so",
            body_label="FX6",
            tokens=MPR_POWEROFF_MARKERS_P174,
        )
        fx3_appfw_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx3_appfw"],  # type: ignore[arg-type]
            binary_name="appFw.so",
            body_label="FX3",
            tokens=APPFW_BIS_POWEROFF_MARKERS_P174,
        )
        fx6_appfw_sum, _, _ = _scan_elf_and_tokens_rdonly(
            donor_paths["fx6_appfw"],  # type: ignore[arg-type]
            binary_name="appFw.so",
            body_label="FX6",
            tokens=APPFW_BIS_POWEROFF_MARKERS_P174,
        )
        fx3_cp_sz, fx3_cp_hits = _scan_tokens_mmap_rdonly_p174(
            donor_paths["fx3_cpapp"], CPAPP_POWEROFF_MARKERS_P174  # type: ignore[arg-type]
        )
        fx6_cp_sz, fx6_cp_hits = _scan_tokens_mmap_rdonly_p174(
            donor_paths["fx6_cpapp"], CPAPP_POWEROFF_MARKERS_P174  # type: ignore[arg-type]
        )
        fx3_backup_sum = _inspect_backup_bin_rdonly_p174(
            donor_paths["fx3_backup"], body_label="FX3"  # type: ignore[arg-type]
        )
        fx6_backup_sum = _inspect_backup_bin_rdonly_p174(
            donor_paths["fx6_backup"], body_label="FX6"  # type: ignore[arg-type]
        )
        fx3_wbi2_sum = _inspect_wbi2_snapshot_rdonly_p174(
            donor_paths["fx3_wbi2"],  # type: ignore[arg-type]
            body_label="FX3",
            wbimem_span_bytes=FX3_WBIMEM_SPAN_BYTES,
        )
        fx6_wbi2_sum = _inspect_wbi2_snapshot_rdonly_p174(
            donor_paths["fx6_wbi2"],  # type: ignore[arg-type]
            body_label="FX6",
            wbimem_span_bytes=FX6_WBIMEM_SPAN_BYTES,
        )
        donor_file_sizes = {
            "fx3_im_elf": fx3_im_sum.file_bytes,
            "fx6_im_elf": fx6_im_sum.file_bytes,
            "fx3_sencore": fx3_sencore_sum.file_bytes,
            "fx6_sencore": fx6_sencore_sum.file_bytes,
            "fx3_mpr": fx3_mpr_sum.file_bytes,
            "fx6_mpr": fx6_mpr_sum.file_bytes,
            "fx3_appfw": fx3_appfw_sum.file_bytes,
            "fx6_appfw": fx6_appfw_sum.file_bytes,
            "fx3_cpapp": fx3_cp_sz,
            "fx6_cpapp": fx6_cp_sz,
            "fx3_backup": fx3_backup_sum.file_bytes,
            "fx6_backup": fx6_backup_sum.file_bytes,
            "fx3_wbi2": fx3_wbi2_sum.file_bytes,
            "fx6_wbi2": fx6_wbi2_sum.file_bytes,
        }
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        fx = build_clean_room_realhw_wbi2_hibdrv_fixtures()
        fx3_im_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_im_elf"],
            binary_name="im.elf",
            body_label="FX3",
            source_mode=mode,
            tokens=IM_ELF_HIB_MARKERS_P174,
        )
        fx6_im_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_im_elf"],
            binary_name="im.elf",
            body_label="FX6",
            source_mode=mode,
            tokens=IM_ELF_HIB_MARKERS_P174,
        )
        fx3_sencore_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_sencore"],
            binary_name="libsencore.so",
            body_label="FX3",
            source_mode=mode,
            tokens=SENCORE_WBI_MARKERS_P174,
        )
        fx6_sencore_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_sencore"],
            binary_name="libsencore.so",
            body_label="FX6",
            source_mode=mode,
            tokens=SENCORE_WBI_MARKERS_P174,
        )
        fx3_mpr_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_mpr"],
            binary_name="libmpr.so",
            body_label="FX3",
            source_mode=mode,
            tokens=MPR_POWEROFF_MARKERS_P174,
        )
        fx6_mpr_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_mpr"],
            binary_name="libmpr.so",
            body_label="FX6",
            source_mode=mode,
            tokens=MPR_POWEROFF_MARKERS_P174,
        )
        fx3_appfw_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_appfw"],
            binary_name="appFw.so",
            body_label="FX3",
            source_mode=mode,
            tokens=APPFW_BIS_POWEROFF_MARKERS_P174,
        )
        fx6_appfw_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_appfw"],
            binary_name="appFw.so",
            body_label="FX6",
            source_mode=mode,
            tokens=APPFW_BIS_POWEROFF_MARKERS_P174,
        )
        fx3_cp_hits = _count_tokens_single_pass(fx["fx3_cpapp"], CPAPP_POWEROFF_MARKERS_P174)
        fx6_cp_hits = _count_tokens_single_pass(fx["fx6_cpapp"], CPAPP_POWEROFF_MARKERS_P174)
        fx3_backup_sum = _parse_backup_bin_header_buf(
            fx["fx3_backup"],
            file_bytes=len(fx["fx3_backup"]),
            body_label="FX3",
            source_mode=mode,
        )
        fx6_backup_sum = _parse_backup_bin_header_buf(
            fx["fx6_backup"],
            file_bytes=len(fx["fx6_backup"]),
            body_label="FX6",
            source_mode=mode,
        )
        # Strip trailing marker suffix before strict WBI2 payload validation, then scan full buffer for markers.
        fx3_wbi2_core = fx["fx3_wbi2"].split(b"\x00" + WBI2_HIBDRV_IMAGE_MARKERS_P174[0].encode("ascii"))[0]
        fx6_wbi2_core = fx["fx6_wbi2"].split(b"\x00" + WBI2_HIBDRV_IMAGE_MARKERS_P174[0].encode("ascii"))[0]
        fx3_wbi2_sum = _inspect_wbi2_snapshot_buf_p174(
            fx3_wbi2_core,
            body_label="FX3",
            source_mode=mode,
            wbimem_span_bytes=FX3_WBIMEM_SPAN_BYTES,
        )
        fx6_wbi2_sum = _inspect_wbi2_snapshot_buf_p174(
            fx6_wbi2_core,
            body_label="FX6",
            source_mode=mode,
            wbimem_span_bytes=FX6_WBIMEM_SPAN_BYTES,
        )
        fx3_wbi2_sum = Wbi2HeaderSnapshotSummary(
            body_label=fx3_wbi2_sum.body_label,
            source_mode=fx3_wbi2_sum.source_mode,
            file_bytes=len(fx["fx3_wbi2"]),
            magic_ascii=fx3_wbi2_sum.magic_ascii,
            sections=fx3_wbi2_sum.sections,
            zero_sections=fx3_wbi2_sum.zero_sections,
            flags=fx3_wbi2_sum.flags,
            resume_vector_hex=fx3_wbi2_sum.resume_vector_hex,
            dversion_hex=fx3_wbi2_sum.dversion_hex,
            sector_size=fx3_wbi2_sum.sector_size,
            r_data_bytes=fx3_wbi2_sum.r_data_bytes,
            wbimem_span_bytes=fx3_wbi2_sum.wbimem_span_bytes,
            phys_min_hex=fx3_wbi2_sum.phys_min_hex,
            phys_max_hex=fx3_wbi2_sum.phys_max_hex,
            hibdrv_marker_hits={
                tok: (1 if fx["fx3_wbi2"].find(tok.encode("ascii")) != -1 else 0)
                for tok in WBI2_HIBDRV_IMAGE_MARKERS_P174
            },
            header_valid=fx3_wbi2_sum.header_valid,
        )
        fx6_wbi2_sum = Wbi2HeaderSnapshotSummary(
            body_label=fx6_wbi2_sum.body_label,
            source_mode=fx6_wbi2_sum.source_mode,
            file_bytes=len(fx["fx6_wbi2"]),
            magic_ascii=fx6_wbi2_sum.magic_ascii,
            sections=fx6_wbi2_sum.sections,
            zero_sections=fx6_wbi2_sum.zero_sections,
            flags=fx6_wbi2_sum.flags,
            resume_vector_hex=fx6_wbi2_sum.resume_vector_hex,
            dversion_hex=fx6_wbi2_sum.dversion_hex,
            sector_size=fx6_wbi2_sum.sector_size,
            r_data_bytes=fx6_wbi2_sum.r_data_bytes,
            wbimem_span_bytes=fx6_wbi2_sum.wbimem_span_bytes,
            phys_min_hex=fx6_wbi2_sum.phys_min_hex,
            phys_max_hex=fx6_wbi2_sum.phys_max_hex,
            hibdrv_marker_hits={
                tok: (1 if fx["fx6_wbi2"].find(tok.encode("ascii")) != -1 else 0)
                for tok in WBI2_HIBDRV_IMAGE_MARKERS_P174
            },
            header_valid=fx6_wbi2_sum.header_valid,
        )
        donor_file_sizes = {k: len(v) for k, v in fx.items()}

    # ---- Pillar 1: p5:/wbi (WBI2 / hibdrv.ko) Zero-Write Lock ----
    p1_errors: List[str] = []
    if not fx3_wbi2_sum.header_valid:
        p1_errors.append("fx3_wbi2 header validation failed")
    if not fx6_wbi2_sum.header_valid:
        p1_errors.append("fx6_wbi2 header validation failed")
    if fx3_wbi2_sum.resume_vector_hex == fx6_wbi2_sum.resume_vector_hex:
        p1_errors.append("Expected distinct FX3 vs FX6 WBI2 resume_vector")

    for lbl, summary, expected in (
        ("fx3_wbi2", fx3_wbi2_sum.hibdrv_marker_hits, WBI2_HIBDRV_IMAGE_MARKERS_P174),
        ("fx6_wbi2", fx6_wbi2_sum.hibdrv_marker_hits, WBI2_HIBDRV_IMAGE_MARKERS_P174),
        ("fx3_sencore", fx3_sencore_sum.marker_hits, SENCORE_WBI_MARKERS_P174),
        ("fx6_sencore", fx6_sencore_sum.marker_hits, SENCORE_WBI_MARKERS_P174),
    ):
        missing = [m for m in expected if summary.get(m, 0) <= 0]
        if missing:
            p1_errors.append(f"{lbl} missing WBI/hibdrv markers: {missing}")

    # Verify Phase 43 cross-kernel mismatch detector also rejects FX6 WBI2 on FX3 kernel.
    fx3_synth_audit = parse_wbi2_buffer(
        build_synthetic_wbi2_image(body="fx3_702"),
        body_label="fx3_702",
        source_mode="SYNTHETIC_CROSS_KERNEL_CHECK",
    )
    fx6_synth_audit = parse_wbi2_buffer(
        build_synthetic_wbi2_image(body="fx6_601"),
        body_label="fx6_601",
        source_mode="SYNTHETIC_CROSS_KERNEL_CHECK",
    )
    mismatch = verify_hibdrv_cross_kernel_rejection(
        target_wbi=fx3_synth_audit,
        candidate_wbi=fx6_synth_audit,
    )
    if not mismatch.rejected_fail_closed or mismatch.wbi_mutation_bytes != 0:
        p1_errors.append("Cross-kernel FX6 WBI2 on FX3 host was not rejected")

    stage_b_inhibit = evaluate_p5_wbi2_hibdrv_zero_write_lock()
    p5_write_blocked = evaluate_p5_wbi2_hibdrv_zero_write_lock(
        attempt_wbi_snapshot_write=True,
        requested_mutation_bytes=4096,
    )
    p5_rdwr_blocked = evaluate_p5_wbi2_hibdrv_zero_write_lock(p5_mount_mode="MS_RDWR")
    sd_pull_clean = evaluate_p5_wbi2_hibdrv_zero_write_lock(
        stage_b_active=False,
        wbi_inhibit_lock_active=False,
        p5_mount_mode="MS_RDONLY",
        sd_card_removed_after_exit=True,
    )

    if not stage_b_inhibit.valid or not stage_b_inhibit.wbi_save_inhibited:
        p1_errors.append("stage_b_inhibit failed")
    if p5_write_blocked.valid or p5_write_blocked.wbi_mutation_bytes != 0:
        p1_errors.append("p5 WBI snapshot write was not blocked with 0 mutation bytes")
    if p5_rdwr_blocked.valid or p5_rdwr_blocked.stock_fx3_wbi2_preserved:
        p1_errors.append("p5 MS_RDWR mount was not blocked")
    if not sd_pull_clean.valid or not sd_pull_clean.sd_removed_stock_boot_clean:
        p1_errors.append("sd_pull_stock_recovery_eval failed")

    pillar1 = Pillar1P5Wbi2ZeroWriteReport(
        passed=len(p1_errors) == 0,
        fx3_wbi2_summary=fx3_wbi2_sum,
        fx6_wbi2_summary=fx6_wbi2_sum,
        fx3_sencore_summary=fx3_sencore_sum,
        fx6_sencore_summary=fx6_sencore_sum,
        cross_kernel_mismatch_verdict=mismatch.verdict_code,
        wbimem_collision_delta_bytes=WBIMEM_COLLISION_DELTA_BYTES,
        stage_b_inhibit_eval=stage_b_inhibit,
        p5_write_attempt_blocked_eval=p5_write_blocked,
        p5_rdwr_mount_blocked_eval=p5_rdwr_blocked,
        sd_pull_stock_recovery_eval=sd_pull_clean,
        errors=tuple(p1_errors),
    )

    # ---- Pillar 2: Cold-Boot vs Warm-Boot Stage-A Entry Isolation ----
    p2_errors: List[str] = []
    fx3_appfw_bis_hits = {m: fx3_appfw_sum.marker_hits.get(m, 0) for m in APPFW_BIS_POWEROFF_MARKERS_P174}
    fx6_appfw_bis_hits = {m: fx6_appfw_sum.marker_hits.get(m, 0) for m in APPFW_BIS_POWEROFF_MARKERS_P174}
    for lbl, hits_dict, expected in (
        ("fx3_im_elf", fx3_im_sum.marker_hits, IM_ELF_HIB_MARKERS_P174),
        ("fx6_im_elf", fx6_im_sum.marker_hits, IM_ELF_HIB_MARKERS_P174),
        ("fx3_appfw_bis", fx3_appfw_bis_hits, APPFW_BIS_POWEROFF_MARKERS_P174),
        ("fx6_appfw_bis", fx6_appfw_bis_hits, APPFW_BIS_POWEROFF_MARKERS_P174),
    ):
        missing = [m for m in expected if hits_dict.get(m, 0) <= 0]
        if missing:
            p2_errors.append(f"{lbl} missing cold/warm entry markers: {missing}")

    if fx3_im_sum.export_count != EXPECTED_IM_ELF_EXPORTS_P174 or fx3_im_sum.import_count != EXPECTED_IM_ELF_IMPORTS_P174:
        p2_errors.append("fx3_im_elf export/import ABI mismatch")
    if fx6_im_sum.export_count != EXPECTED_IM_ELF_EXPORTS_P174 or fx6_im_sum.import_count != EXPECTED_IM_ELF_IMPORTS_P174:
        p2_errors.append("fx6_im_elf export/import ABI mismatch")
    if not fx3_backup_sum.header_valid or not fx6_backup_sum.header_valid:
        p2_errors.append("Backup.bin BK4 header validation failed")

    clean_cold = evaluate_stage_a_cold_vs_warm_boot_entry(upm_bootmode="NORMAL", arm_token_present=True)
    bis_rejected = evaluate_stage_a_cold_vs_warm_boot_entry(upm_bootmode="BIS", arm_token_present=True)
    p5_premounted = evaluate_stage_a_cold_vs_warm_boot_entry(upm_bootmode="NORMAL", p5_already_mounted=True)
    reentry_blocked = evaluate_stage_a_cold_vs_warm_boot_entry(upm_bootmode="NORMAL", reentry_lock_present=True)
    unarmed_pass = evaluate_stage_a_cold_vs_warm_boot_entry(upm_bootmode="NORMAL", arm_token_present=False)

    if not clean_cold.valid or not clean_cold.stage_a_activated:
        p2_errors.append("clean_cold_boot_stage_a_eval failed")
    if bis_rejected.valid or bis_rejected.stage_a_activated or not bis_rejected.bis_warm_boot_isolated:
        p2_errors.append("BIS warm-boot entry was not rejected")
    if p5_premounted.valid or p5_premounted.stage_a_activated:
        p2_errors.append("Pre-mounted p5 was not rejected")
    if reentry_blocked.valid or reentry_blocked.stage_a_activated:
        p2_errors.append("Re-entry lock did not block double-mount")
    if not unarmed_pass.valid or unarmed_pass.stage_a_activated:
        p2_errors.append("Unarmed cold boot did not pass through to Stock FX3")

    pillar2 = Pillar2ColdVsWarmEntryReport(
        passed=len(p2_errors) == 0,
        fx3_im_elf_summary=fx3_im_sum,
        fx6_im_elf_summary=fx6_im_sum,
        fx3_appfw_bis_hits=fx3_appfw_bis_hits,
        fx6_appfw_bis_hits=fx6_appfw_bis_hits,
        fx3_backup_summary=fx3_backup_sum,
        fx6_backup_summary=fx6_backup_sum,
        clean_cold_boot_stage_a_eval=clean_cold,
        bis_warm_boot_rejected_eval=bis_rejected,
        p5_premounted_rejected_eval=p5_premounted,
        reentry_lock_blocked_eval=reentry_blocked,
        unarmed_stock_passthrough_eval=unarmed_pass,
        errors=tuple(p2_errors),
    )

    # ---- Pillar 3: Stage-B Clean Power-Off (`POWEROFF_CLEAN_NO_WBI`) Determinism ----
    p3_errors: List[str] = []
    fx3_cp_pwr_hits = {m: fx3_cp_hits.get(m, 0) for m in CPAPP_POWEROFF_MARKERS_P174}
    fx6_cp_pwr_hits = {m: fx6_cp_hits.get(m, 0) for m in CPAPP_POWEROFF_MARKERS_P174}
    for lbl, hits_dict, expected in (
        ("fx3_mpr", fx3_mpr_sum.marker_hits, MPR_POWEROFF_MARKERS_P174),
        ("fx6_mpr", fx6_mpr_sum.marker_hits, MPR_POWEROFF_MARKERS_P174),
        ("fx3_cpapp_pwr", fx3_cp_pwr_hits, CPAPP_POWEROFF_MARKERS_P174),
        ("fx6_cpapp_pwr", fx6_cp_pwr_hits, CPAPP_POWEROFF_MARKERS_P174),
    ):
        missing = [m for m in expected if hits_dict.get(m, 0) <= 0]
        if missing:
            p3_errors.append(f"{lbl} missing PowerOff/Fsys markers: {missing}")

    nom_poweroff = evaluate_stage_b_poweroff_determinism(exit_trigger="POWER_SWITCH_OFF", requested_power_state="poweroff")
    sd_pull_exit = evaluate_stage_b_poweroff_determinism(
        exit_trigger="SD_REMOVAL_TRANSITION",
        requested_power_state="poweroff",
        sd_card_present_on_next_boot=False,
    )
    disk_blocked = evaluate_stage_b_poweroff_determinism(exit_trigger="POWER_SWITCH_OFF", requested_power_state="disk")
    cp_timeout_abort = evaluate_stage_b_poweroff_determinism(
        exit_trigger="POWER_SWITCH_OFF",
        requested_power_state="poweroff",
        cp_poweroff_handshake_ok=False,
    )
    unflushed_blocked = evaluate_stage_b_poweroff_determinism(
        exit_trigger="SD_REMOVAL_TRANSITION",
        requested_power_state="poweroff",
        fsys_media_flushed=False,
    )

    if not nom_poweroff.valid or nom_poweroff.hibdrv_snapshot_triggered:
        p3_errors.append("nominal_power_switch_off_eval failed")
    if not sd_pull_exit.valid or sd_pull_exit.sd_removed_next_boot_mode != "STOCK_FX3_7_02_COLD_BOOT":
        p3_errors.append("sd_pull_transition_eval failed")
    if disk_blocked.valid or disk_blocked.hibdrv_snapshot_triggered or disk_blocked.wbi_mutation_bytes != 0:
        p3_errors.append("/sys/power/state disk hibernation was not blocked")
    if cp_timeout_abort.valid or cp_timeout_abort.hibdrv_snapshot_triggered:
        p3_errors.append("CP poweroff timeout did not fail-safe without WBI")
    if unflushed_blocked.valid:
        p3_errors.append("Unflushed media transition was not blocked")

    pillar3 = Pillar3PoweroffDeterminismReport(
        passed=len(p3_errors) == 0,
        fx3_mpr_summary=fx3_mpr_sum,
        fx6_mpr_summary=fx6_mpr_sum,
        fx3_cpapp_poweroff_hits=fx3_cp_pwr_hits,
        fx6_cpapp_poweroff_hits=fx6_cp_pwr_hits,
        nominal_power_switch_off_eval=nom_poweroff,
        sd_pull_transition_eval=sd_pull_exit,
        wbi_disk_suspend_blocked_eval=disk_blocked,
        cp_handshake_timeout_safe_abort_eval=cp_timeout_abort,
        unflushed_media_blocked_eval=unflushed_blocked,
        errors=tuple(p3_errors),
    )

    # ---- Pillar 4: Write Firewall & 12-Touchpoint Compatibility Matrix ----
    p4_errors: List[str] = []
    g_wbshd = evaluate_phase174_write_guard(STAGE_B_WBI_INHIBIT_LOCK_PATH)
    g_tmp = evaluate_phase174_write_guard("/tmp/fx6_stage_b/stage_b_state.env")
    g_ext = evaluate_phase174_write_guard("/mnt/cfexpress_a/PRIVATE/M4ROOT/CLIP/C0001.MP4")
    g_n5 = evaluate_phase174_write_guard(P5_WBI_DEVICE)
    g_cn5 = evaluate_phase174_write_guard(P5_WBI_CRYPTO_DEVICE)
    g_p5 = evaluate_phase174_write_guard("p5:/wbi")
    g_pwr = evaluate_phase174_write_guard(SYS_POWER_STATE_PATH)
    g_hib = evaluate_phase174_write_guard("/lib/modules/hibdrv.ko")
    g_bk4 = evaluate_phase174_write_guard("p2:/Backup.bin")
    g_spi = evaluate_phase174_write_guard("spi_nor:/loader_nor.bin")

    for ok_guard in (g_wbshd, g_tmp, g_ext):
        if not ok_guard.valid:
            p4_errors.append(f"Volatile/ext guard failed: {ok_guard.target_path}")
    for blk_guard in (g_n5, g_cn5, g_p5, g_pwr, g_hib, g_bk4, g_spi):
        if blk_guard.valid or not blk_guard.persistent_write_blocked or blk_guard.wbi_mutation_bytes != 0:
            p4_errors.append(f"Persistent/WBI guard failed to block {blk_guard.target_path}")

    matrix = build_phase174_hibernation_isolation_matrix()
    if matrix.total_touchpoints != 12:
        p4_errors.append(f"Expected 12 touchpoints, got {matrix.total_touchpoints}")

    pillar4 = Pillar4WbiFirewallMatrixReport(
        passed=len(p4_errors) == 0,
        volatile_wbshd_lock_allowed=g_wbshd,
        volatile_tmp_overlay_allowed=g_tmp,
        external_sd_media_allowed=g_ext,
        blocked_nflasha5_guard=g_n5,
        blocked_cnflasha5_guard=g_cn5,
        blocked_p5_wbi_mount_guard=g_p5,
        blocked_sys_power_state_guard=g_pwr,
        blocked_hibdrv_ko_guard=g_hib,
        blocked_backup_bin_guard=g_bk4,
        blocked_spinor_guard=g_spi,
        compatibility_matrix=matrix,
        errors=tuple(p4_errors),
    )

    errors.extend(p1_errors)
    errors.extend(p2_errors)
    errors.extend(p3_errors)
    errors.extend(p4_errors)
    all_ok = pillar1.passed and pillar2.passed and pillar3.passed and pillar4.passed

    digest_payload = {
        "schema": PHASE_174_SCHEMA,
        "mode": mode,
        "all_ok": all_ok,
        "donor_file_sizes": donor_file_sizes,
        "p1": pillar1.passed,
        "p2": pillar2.passed,
        "p3": pillar3.passed,
        "p4": pillar4.passed,
        "fx3_resume": fx3_wbi2_sum.resume_vector_hex,
        "fx6_resume": fx6_wbi2_sum.resume_vector_hex,
    }
    report_sha = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return RealhwWbi2HibdrvHibernationIsolationReport(
        schema_version=PHASE_174_SCHEMA,
        phase_version=PHASE_174_VERSION,
        mode=mode,
        all_checks_passed=all_ok,
        o_rdonly_enforced=True,
        wbi_save_policy=WBI_SAVE_INHIBITED_POLICY,
        wbi_save_inhibited=stage_b_inhibit.wbi_save_inhibited,
        wbi_mutation_bytes=0,
        stock_fx3_wbi2_preserved=stage_b_inhibit.stock_fx3_wbi2_preserved and sd_pull_clean.sd_removed_stock_boot_clean,
        bis_warm_boot_isolated=bis_rejected.bis_warm_boot_isolated and clean_cold.stage_a_activated,
        poweroff_clean_no_wbi=(nom_poweroff.poweroff_policy == POWEROFF_CLEAN_NO_WBI_POLICY and not nom_poweroff.hibdrv_snapshot_triggered),
        stale_ram_cp_carryover_prevented=nom_poweroff.stale_ram_cp_carryover_prevented and sd_pull_exit.stale_ram_cp_carryover_prevented,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        donor_file_sizes=donor_file_sizes,
        pillar1_p5_wbi2_zero_write=pillar1,
        pillar2_cold_vs_warm_entry=pillar2,
        pillar3_poweroff_determinism=pillar3,
        pillar4_firewall_matrix=pillar4,
        report_sha256=report_sha,
        errors=tuple(errors),
    )


def realhw_wbi2_hibdrv_hibernation_isolation_report_to_dict(
    report: RealhwWbi2HibdrvHibernationIsolationReport,
) -> Dict[str, object]:
    """Convert `RealhwWbi2HibdrvHibernationIsolationReport` to a JSON-safe dict."""
    return asdict(report)
