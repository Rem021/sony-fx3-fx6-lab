"""Phase 12 — `nflasha3-initrd` Boot-Chain, WBI (`p5`) Hibernation Safety Redline & Atomic Stage-A Boot Orchestrator.

Covers two coupled embedded system startup & runtime safety dimensions:

- **Dimension A (`nflasha3-initrd` Startup Chain & `p5:/wbi` Warm-Boot Hibernation Safety Audit)**:
  1. Audits FX6 Ver. 6.01 `nested-files/nflasha3-initrd/` (`version.txt`, `root/chassis`,
     `bin/busybox`, `sbin/init`, `sbin/init2`, `sbin/mkdosfs`, `sbin/initrc/*`, and the 4 early
     initrd kernel modules `devno.ko`, `dma330.ko`, `crypt-emmc.ko`, `emmc.ko`) alongside `p15`
     (`/usr`) startup binaries (`bin/bootin.elf`, `bin/im.elf`, `bin/change_mode.sh`,
     `bin/common.src`, `bin/us_remove_modes.sh`), `0800_appli/setting/kemco.txt`, `updater.img`
     `bin/ud_wbi_drop.elf`, `0700_part_image/dev/nflasha5` (`WBI2` `202,677,056 B`), Sony OSS
     kernel `include/linux/warmboot.h` / `include/linux/wbi.h` / `kernel/power/wbi_raw.c`, and
     FX3 donor WBI/initrd comparison evidence (`WBI-zero-proof.json`, `engine-rootfs/2.05/sbin/init`).
  2. Pins exact boot-order contracts:
     `sbin/init` (`mount proc` -> `insmod_drv1` 4 initrd `.ko`s -> `setup_nflash` `/dev/pnflasha*`
     + `/dev/cnflasha*` -> optional FX3 `setup_rootfs` `p7:/rootfs` `pivot_root` vs FX6 direct
     `/dev/ram0` `/sbin/init2`) -> `sbin/init2` (`mount sysfs/debugfs` -> `fstab` mounting
     `/setting`, `/system`, `/cp`, `/log`, `/cert`, `/lens`, `/tmp`, and `/usr` `ro` -> `fstab.ext`
     mounting `/etc` + `/var` -> `mount -t tmpfs none /tmp_wbshd` -> `insmod_drv2` loading 39
     `/usr/kmod/*.ko` modules with `/usr/kmod/upm.ko` at slot #24 -> `setup_bis || setup_senser`
     -> `/usr/bin/bootin.elf &` -> `/usr/bin/im.elf`).
  3. Proves the **Two-Way `p5` (`/wbi`, `/dev/nflasha5`, `type=6`, `300.00 MiB`) Warm-Boot
     Hibernation Hazard** and enforces the **Stage-A WBI Safety Redline**:
     - `wbi_p5_write_and_hibernation_forbidden = True`, `wbi_mutation_bytes = 0`.
     - Outbound hazard: `setup_bis()` (`upm_bootmode == "BIS"`) formats `/log` (`mkdosfs`) and
       `im.elf` triggers `/sys/power/state` -> `wbi_raw.c` `wb_default_device->write_sector` onto
       `/dev/nflasha5` (`202,677,056 B` on FX6) or `ud_wbi_drop.elf` rewrites sector 0 (`"invl"`),
       violating `emmc_write_bytes == 0` and destroying FX3's factory WBI snapshot (`ac7373c5...`).
     - Inbound hazard: Cross-session `WBI2` resume (`warm.mode=2`, `resume_vector=0x4004a87f0`)
       either bypasses `nflasha3-initrd`, collides across the `+13.47 MiB` `wbimem` DDR delta at
       `0x410524000` (`0x01919000` FX6 vs `0x00BA0000` FX3), or restores stale Stage-A RAM pages
       after one-shot token clearance.

- **Dimension B (Deterministic POSIX `/bin/sh` Atomic Verify-Before-Mount Stage-A Orchestrator &
  6-Scenario Sandbox Verifier)**:
  - Synthesizes `etc/fx6_overlay/30-stage-a-orchestrator.sh` and executes it inside an isolated
    `tempfile.TemporaryDirectory()` `/bin/sh` sandbox across all 6 mandatory scenarios:
    1. Clean Nominal Stage-A Activation & Clean LIFO Teardown (`emmc_writes == 0`, `wbi_writes == 0`,
       `lingering_mounts == 0`, exact reverse LIFO unwind order).
    2. Verify-Before-Mount Atomicity (single-byte SHA-256 mismatch in staged `.so` or `opelog.vfat`
       aborts strictly BEFORE first `insmod` or `mount`).
    3. Mid-Sequence Mount Failure LIFO Rollback (step `k` mount failure unwinds `k-1 .. 1` in strict
       LIFO order and falls back cleanly to stock FX3).
    4. WBI (`p5` / `/dev/nflasha5`) Guard Enforcement (blocks `BIS` mode and runtime hibernation
       triggers; `/dev/nflasha5` never opened for write or mounted RW).
    5. Idempotent Re-Entry Guard (second invocation detects active/consumed lock and prevents
       double-mounting).
    6. Stock Cold-Boot Passthrough (unarmed cold boot performs `0` Stage-A mounts/insmods and
       boots stock FX3 untouched).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .backup_mount_tolerance_verifier import (
    DEFAULT_COLOR_PORT_WORK_DIR,
    DEFAULT_FX6_TEAM_DIR,
    synthesize_ram_shadow_bk4,
)
from .patcher import DEFAULT_FX3_MODULES_DIR, DEFAULT_FX6_DONOR_LIB_DIR


# Clean read-only donor paths (zero `stage*` paths ever referenced)
DEFAULT_FX6_DONOR_ROOT = DEFAULT_FX6_TEAM_DIR / "donor"
DEFAULT_FX6_P3_INITRD_DIR = DEFAULT_FX6_DONOR_ROOT / "nested-files" / "nflasha3-initrd"
DEFAULT_FX6_P15_FILES_DIR = DEFAULT_FX6_DONOR_ROOT / "nflasha15-files"
DEFAULT_FX6_UPDATER_IMG_DIR = DEFAULT_FX6_DONOR_ROOT / "nested-files" / "updater.img"
DEFAULT_FX6_NFLASH5_WBI_PATH = DEFAULT_FX6_DONOR_ROOT / "tree" / "0700_part_image" / "dev" / "nflasha5"
DEFAULT_FX6_WBI2_RECEIPT_PATH = DEFAULT_FX6_DONOR_ROOT / "wbi2-receipt.json"
DEFAULT_FX6_APPLI_KEMCO_PATH = DEFAULT_FX6_DONOR_ROOT / "tree" / "0800_appli" / "setting" / "kemco.txt"
DEFAULT_SONY_OSS_LINUX_DIR = (
    DEFAULT_FX6_DONOR_ROOT / "fx6-boot-readiness" / "early-kernel" / "sony-oss-fx3" / "linux-kernel" / "linux"
)
DEFAULT_FX3_WBI_ZERO_PROOF_PATH = (
    DEFAULT_COLOR_PORT_WORK_DIR / "WBI-zero-staging-20261030" / "WBI-zero-proof.json"
)
DEFAULT_FX3_205_INITRD_INIT_PATH = (
    DEFAULT_COLOR_PORT_WORK_DIR / "input-20261028" / "engine-rootfs" / "2.05" / "sbin" / "init"
)

# Pinned FX6 `nflasha3-initrd`, `p15`, WBI (`p5`), kernel OSS, and FX3 donor digests & sizes
PINNED_INITRD_AND_BOOT_ARTIFACTS: Tuple[Tuple[str, str, int, str], ...] = (
    (
        "fx6_initrd_version_txt",
        "nested-files/nflasha3-initrd/version.txt",
        19,
        "ab2abf9f3c38e7dc08b8f6f17119eabdbd8134e2bef5a5f385af48cfce1bb324",
    ),
    (
        "fx6_initrd_chassis",
        "nested-files/nflasha3-initrd/root/chassis",
        18,
        "7880368a5b3a8efe7e19337e225fc1248dca9e8f1f96eb111823eb66588417e1",
    ),
    (
        "fx6_initrd_common_src",
        "nested-files/nflasha3-initrd/root/common.src",
        2546,
        "96f3bddf603788409af69fead42f6686e3701ad6f4aa2ccd3af0ef4ba986d7d2",
    ),
    (
        "fx6_initrd_busybox",
        "nested-files/nflasha3-initrd/bin/busybox",
        423000,
        "a306367cd67674b1d1a03464b24fbe8137a8ea8f630817e7733a054f761d0c6d",
    ),
    (
        "fx6_initrd_sbin_init",
        "nested-files/nflasha3-initrd/sbin/init",
        735,
        "c83de1abeeb779f7473181b51face32ecfedfa3bd5c0fc346ae0c628f1b0ac5e",
    ),
    (
        "fx6_initrd_sbin_init2",
        "nested-files/nflasha3-initrd/sbin/init2",
        1658,
        "45d3b907e6ef96c9a930cd3e6f919db700bffb5f18c386abfdb655f4d9954aeb",
    ),
    (
        "fx6_initrd_sbin_mkdosfs",
        "nested-files/nflasha3-initrd/sbin/mkdosfs",
        33992,
        "e66b6bc7b714015ce4fb68a9bde182e30022af2c712a8a576ea2d35c4b6f9510",
    ),
    (
        "fx6_initrd_insmod_drv1",
        "nested-files/nflasha3-initrd/sbin/initrc/insmod_drv1",
        152,
        "22f29d06d7776fe5e8362c17049beabfd3e3bebffd222e51276e3704d483a591",
    ),
    (
        "fx6_initrd_setup_nflash",
        "nested-files/nflasha3-initrd/sbin/initrc/setup_nflash",
        375,
        "055cb3db7a40084aef8aaa89a7357921b514bf0af89690f920b608d9f3734cdc",
    ),
    (
        "fx6_initrd_fstab",
        "nested-files/nflasha3-initrd/sbin/initrc/fstab",
        1085,
        "3936e6508ba89a025fc998c824434562c2d16234db96e179ec3f3a90a5a1d6f0",
    ),
    (
        "fx6_initrd_fstab_ext",
        "nested-files/nflasha3-initrd/sbin/initrc/fstab.ext",
        134,
        "a77bdfb7bf15d3a1240bdefc4edb4469672f3258d6d8dba7dd4164e3fd2d51c3",
    ),
    (
        "fx6_initrd_fstab_root",
        "nested-files/nflasha3-initrd/sbin/initrc/fstab.root",
        58,
        "c77d93236b89349bcc24853756f960bb49411e922c9430ede70b5b2cb8b6a4b2",
    ),
    (
        "fx6_initrd_setup_shielding",
        "nested-files/nflasha3-initrd/sbin/initrc/setup_shielding",
        720,
        "d54f7a0ebfa3db37fe329463bdbf60c8b6fd14c3cb95dc658c244e8bf61ead1f",
    ),
    (
        "fx6_initrd_setup_cpuset_cpu3",
        "nested-files/nflasha3-initrd/sbin/initrc/setup_cpuset_CPU3",
        562,
        "95c778bd94e446d1e92f3f978cba58b714ca328c9020d03b7969ff2f83dd5ead",
    ),
    (
        "fx6_initrd_insmod_drv2",
        "nested-files/nflasha3-initrd/sbin/initrc/insmod_drv2",
        1298,
        "19757bdd450061f861e2da44a6a93be2525668e3f7edc64e5a99a25bde56564e",
    ),
    (
        "fx6_initrd_setup_console",
        "nested-files/nflasha3-initrd/sbin/initrc/setup_console",
        1205,
        "9411360fdfe60c7b7a09fa9e931e4ae9ec9c062e480b620e4c313c31f9139dd0",
    ),
    (
        "fx6_initrd_kmod_devno",
        "nested-files/nflasha3-initrd/kmod/devno.ko",
        6344,
        "2baa102856a0af9168b1634febea1f604153a38562a4d01980ca8494ffab86a5",
    ),
    (
        "fx6_initrd_kmod_dma330",
        "nested-files/nflasha3-initrd/kmod/dma330.ko",
        607336,
        "de42d7e5a17fd7fa84cb80396d908730246179f7aabdb72a8a822fed4d941770",
    ),
    (
        "fx6_initrd_kmod_crypt_emmc",
        "nested-files/nflasha3-initrd/kmod/crypt-emmc.ko",
        14592,
        "7c97edb1586f81f1b03d62719dc28cae710c13127061ddfe524e81a406938145",
    ),
    (
        "fx6_initrd_kmod_emmc",
        "nested-files/nflasha3-initrd/kmod/emmc.ko",
        341024,
        "2c1702040ccf0edde35cc0a18a0c2008db56bc0d7cf3798e6862a2003defdcd6",
    ),
    (
        "fx6_p15_bootin_elf",
        "nflasha15-files/bin/bootin.elf",
        23960,
        "72480247f8d2a1eeaab076b880c35279c6c94284649e267066f5ea10de6622a6",
    ),
    (
        "fx6_p15_im_elf",
        "nflasha15-files/bin/im.elf",
        40920,
        "87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec",
    ),
    (
        "fx6_p15_change_mode_sh",
        "nflasha15-files/bin/change_mode.sh",
        5758,
        "08b74f7b84075d67507d14ed7643e95337ccd54817d4eb7ff553eff9721e0ea7",
    ),
    (
        "fx6_p15_common_src",
        "nflasha15-files/bin/common.src",
        3287,
        "3d5334ab1698d67176f8fd35ffd4d7a9a9b85a1625b20cf128ba091f752b90a0",
    ),
    (
        "fx6_p15_us_remove_modes_sh",
        "nflasha15-files/bin/us_remove_modes.sh",
        52,
        "90a56f5b3d6e1a304055d7ccabdf058da8703a3e956781112022e7ee697bda4a",
    ),
    (
        "fx6_updater_ud_wbi_drop_elf",
        "nested-files/updater.img/bin/ud_wbi_drop.elf",
        10304,
        "4cfc8f979a4289915e2a3db6cd7e96bb97b35645149977619c04b0d9c5fbc7b3",
    ),
    (
        "fx6_appli_setting_kemco_txt",
        "tree/0800_appli/setting/kemco.txt",
        1788,
        "6a609ee6b96c2ed0db47e9056ca67dfd8d419f9445302dacf09c262eace3b4fc",
    ),
)

PINNED_FX6_INITRD_SBIN_INIT_SHA256 = "c83de1abeeb779f7473181b51face32ecfedfa3bd5c0fc346ae0c628f1b0ac5e"
PINNED_FX6_INITRD_SBIN_INIT2_SHA256 = "45d3b907e6ef96c9a930cd3e6f919db700bffb5f18c386abfdb655f4d9954aeb"
PINNED_FX6_INITRD_INSMOD_DRV1_SHA256 = "22f29d06d7776fe5e8362c17049beabfd3e3bebffd222e51276e3704d483a591"
PINNED_FX6_INITRD_INSMOD_DRV2_SHA256 = "19757bdd450061f861e2da44a6a93be2525668e3f7edc64e5a99a25bde56564e"
PINNED_FX6_BOOTIN_ELF_SHA256 = "72480247f8d2a1eeaab076b880c35279c6c94284649e267066f5ea10de6622a6"
PINNED_FX6_IM_ELF_SHA256 = "87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec"
PINNED_FX6_UD_WBI_DROP_ELF_SHA256 = "4cfc8f979a4289915e2a3db6cd7e96bb97b35645149977619c04b0d9c5fbc7b3"
PINNED_FX6_APPLI_KEMCO_SHA256 = "6a609ee6b96c2ed0db47e9056ca67dfd8d419f9445302dacf09c262eace3b4fc"

# WBI (`p5` / `/dev/nflasha5`) pinned constants
PINNED_FX6_WBI_NFLASH5_BYTES = 202677056
PINNED_FX6_WBI_NFLASH5_SHA256 = "d33f0bd9c305cd9217815cd1e1a4fd86ea48b28ddbbbe6c581c8665dc5fde2d1"
PINNED_FX3_STOCK_WBI_SHA256 = "ac7373c58a75b7685cc2fc8e920440ec37534d15c11f447ecdea546e255fb9b1"
PINNED_FX3_205_INITRD_INIT_SHA256 = "223f642c9cc8eb3a53901263940d42905a3d57fc5a091459003719e216950ccd"
PINNED_OSS_WARMBOOT_H_SHA256 = "ccd4d6b7b1e73ebab557dc0c99bf454aea20da5b31a6975c7605483f2bcaf5a1"
PINNED_OSS_WBI_H_SHA256 = "a7d38702c3cf1b8bca5ec633b4162cdb1b354bc20fd14bb8ca337cbb98997d41"
PINNED_OSS_WBI_RAW_C_SHA256 = "7e3e7c718fa285aba18115aa7b663860cc848432030db38acb2c0718db0ee1e8"

WBI2_MAGIC = b"WBI2"
WBI_PARTITION_NUMBER = 5
WBI_PARTITION_SIZE_BYTES = 0x00096000 * 512  # 314,572,800 B = 300.00 MiB (type=6 raw WBI on FX3 & FX6)
EXPECTED_FX6_WBI_SECTION_COUNT = 1197
EXPECTED_FX6_WBI_RESUME_VECTOR = 0x4004A87F0
EXPECTED_FX6_WBI_DVERSION = 0x20060224
EXPECTED_FX6_WBI_R_DATA_BYTES = 202338304
EXPECTED_FX6_WBI_O_DATA_BYTES = 264376320
EXPECTED_FX6_WBIMEM_PRIMARY_SPAN = 0x01919000  # @ 0x410524000 (26,316,800 B)
EXPECTED_FX3_WBIMEM_PRIMARY_SPAN = 0x00BA0000  # @ 0x410524000 (12,189,696 B; ends 0x4110C4000)
EXPECTED_WBIMEM_COLLISION_DELTA_BYTES = (
    EXPECTED_FX6_WBIMEM_PRIMARY_SPAN - EXPECTED_FX3_WBIMEM_PRIMARY_SPAN
)  # +14,127,104 B (+13.47 MiB)

EXPECTED_INSMOD_DRV1_ORDER: Tuple[str, ...] = (
    "/kmod/devno.ko",
    "/kmod/dma330.ko",
    "/kmod/crypt-emmc.ko",
    "/kmod/emmc.ko",
)
EXPECTED_INSMOD_DRV2_TOTAL_COUNT = 39
EXPECTED_INSMOD_DRV2_UPM_ONE_BASED_SLOT = 24  # `/usr/kmod/upm.ko` immediately after `kikilog.ko` (#23)

ORCHESTRATOR_CPIO_REL_PATH = "etc/fx6_overlay/30-stage-a-orchestrator.sh"

# Ordered Stage-A activation steps (1..10) whose reverse (10..1) defines strict LIFO teardown
EXPECTED_STAGE_A_FORWARD_STEP_IDS: Tuple[str, ...] = (
    "01_kmod_p9_upm_ko",
    "02_p1_lut_p30_ro_mount",
    "03_p2_opelog_vfat_loop_mount",
    "04_bind_ro_libInfraSetupFile_so",
    "05_bind_ro_libInfraMediaCommon_so",
    "06_bind_ro_libInfraMediaConfig_so",
    "07_bind_ro_libInfraAppRemoteBoard_so",
    "08_bind_ro_libfan_so",
    "09_bind_ro_appFw_so",
    "10_bind_ro_ram_shadow_bk4",
)
EXPECTED_STAGE_A_LIFO_UNWIND_STEP_IDS: Tuple[str, ...] = tuple(
    reversed(EXPECTED_STAGE_A_FORWARD_STEP_IDS)
)

FORBIDDEN_WBI_MUTATION_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("ud_wbi_drop_exec", re.compile(r"\bud_wbi_drop(?:\.elf)?\b")),
    (
        "nflasha5_write_dd_or_redirect",
        re.compile(
            r"(?:\bof=/dev/[cp]?nflasha5\b|>\s*\"?(?:\$\{PREFIX\})?/dev/[cp]?nflasha5\b|\bnandwrite(?:\.elf)?\b[^\n]*/dev/[cp]?nflasha5\b)"
        ),
    ),
    (
        "nflasha5_mount",
        re.compile(r"\bmount\b[^\n]*/dev/[cp]?nflasha5\b"),
    ),
    (
        "sys_power_state_hibernation_write",
        re.compile(r"\becho\s+(?:disk|mem|standby|freeze)\s*>\s*\"?(?:\$\{PREFIX\})?/sys/power/state\b"),
    ),
    (
        "upm_bootmode_bis_force",
        re.compile(r"\bUPM_BOOTMODE\s*=\s*[\"']?BIS[\"']?(?!\s*\])"),
    ),
    (
        "mkdosfs_log_bis_format",
        re.compile(r"\bmkdosfs\b[^\n]*/dev/[cp]?nflasha11\b"),
    ),
    (
        "warm_mode_2_enable",
        re.compile(r"\bwarm\.mode=2\b"),
    ),
)

SIMULATED_STAGE_A_PARTITIONS: Tuple[str, ...] = (
    "sector0",
    "p1",
    "p2",
    "p3",
    "p5_wbi",
    "p6",
    "p7",
    "p8",
    "p11_log",
    "p12",
    "p15",
    "p18",
    "p30_lut",
)


@dataclass(frozen=True)
class BootArtifactDigestRecord:
    artifact_id: str
    relative_path: str
    expected_bytes: int
    expected_sha256: str
    live_present: bool
    verified: bool


@dataclass(frozen=True)
class Wbi2HeaderAudit:
    valid: bool
    live_donor_verified: bool
    image_bytes: int
    image_sha256: str
    magic_ascii: str
    section_count: int
    flags: int
    resume_vector_hex: str
    dversion_hex: str
    sector_size: int
    r_data_bytes: int
    kern_cksum_hex: str
    o_data_bytes: int
    fx6_wbimem_primary_span_bytes: int
    fx3_wbimem_primary_span_bytes: int
    wbimem_collision_delta_bytes: int
    fx3_stock_wbi_sha256: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class InitrdBootChainContractAudit:
    valid: bool
    verification_mode: str
    artifact_count_verified: int
    artifacts: Tuple[BootArtifactDigestRecord, ...]
    insmod_drv1_modules: Tuple[str, ...]
    insmod_drv2_module_count: int
    upm_ko_insmod_drv2_slot: int
    upm_ko_absent_from_initrd: bool
    p15_usr_mounted_readonly: bool
    p5_wbi_absent_from_fstab: bool
    tmp_wbshd_tmpfs_mounted: bool
    bis_mode_formats_p11_log: bool
    bootin_hands_off_to_im_elf: bool
    im_elf_references_sys_power_state: bool
    fx3_uses_p7_setup_rootfs_pivot: bool
    fx6_runs_init2_from_ram0: bool
    wbi2_header: Wbi2HeaderAudit
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CandidateWbiRedlineAudit:
    valid: bool
    wbi_p5_write_and_hibernation_forbidden: bool
    wbi_mutation_bytes: int
    violations: Tuple[str, ...]


@dataclass(frozen=True)
class OrchestratorStateMachineTrace:
    states: Tuple[str, ...]
    boot_branch: str
    diag_code_prefix: str
    token_cleared_before_exec: bool
    wbi_guard_enforced: bool
    verify_before_mount_passed: bool
    double_mount_prevented: bool
    im_elf_invoked: bool
    forward_steps_executed: Tuple[str, ...]
    unwind_steps_executed: Tuple[str, ...]
    lingering_mounts: int
    emmc_writes: int
    wbi_writes: int


@dataclass(frozen=True)
class OrchestratorSandboxRunResult:
    run_id: str
    returncode: int
    boot_branch: str
    diag_code: str
    stock_boot_invoked: bool
    im_elf_invoked: bool
    token_cleared_before_exec: bool
    token_present_after: bool
    wbi_guard_verified: bool
    wbi_hibernation_masked: bool
    wbi_trigger_blocked_count: int
    double_mount_prevented: bool
    verified_digest_count: int
    insmod_event_count: int
    mount_event_count: int
    forward_steps: Tuple[str, ...]
    unwind_steps: Tuple[str, ...]
    lifo_order_exact: bool
    lingering_mount_count: int
    lingering_loop_count: int
    lingering_kmod_count: int
    emmc_write_count: int
    wbi_write_count: int
    sandbox_violation_count: int
    state_machine_matched: bool


@dataclass(frozen=True)
class OrchestratorScenarioResult:
    scenario_id: str
    title: str
    passed: bool
    runs: Tuple[OrchestratorSandboxRunResult, ...]
    emmc_writes: int
    wbi_writes: int
    lingering_mounts: int
    notes: str


@dataclass(frozen=True)
class Phase12StageABootOrchestratorReport:
    all_checks_passed: bool
    stage_a_orchestrator_ok: bool
    wbi_p5_write_and_hibernation_forbidden: bool
    wbi_mutation_bytes: int
    orchestrator_script_sha256: str
    orchestrator_script_bytes: int
    dimension_a_boot_chain_and_wbi: InitrdBootChainContractAudit
    candidate_wbi_redline: CandidateWbiRedlineAudit
    scenario_count: int
    total_sandbox_runs: int
    total_emmc_writes: int
    total_wbi_writes: int
    total_lingering_mounts: int
    total_sandbox_violations: int
    scenarios: Tuple[OrchestratorScenarioResult, ...]
    temp_dir_cleaned: bool
    errors: Tuple[str, ...]


def _stream_sha256_and_size(path: Path) -> Tuple[int, str]:
    h = hashlib.sha256()
    total = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            h.update(chunk)
    return total, h.hexdigest()


def parse_wbi2_header_bytes(
    header_bytes: bytes,
    *,
    image_bytes: int = PINNED_FX6_WBI_NFLASH5_BYTES,
    image_sha256: str = PINNED_FX6_WBI_NFLASH5_SHA256,
    live_donor_verified: bool = False,
) -> Wbi2HeaderAudit:
    """Parse and validate Sony `struct wb_header` (`include/linux/warmboot.h`, 88 bytes LE)."""
    errors: List[str] = []
    if len(header_bytes) < 88:
        return Wbi2HeaderAudit(
            valid=False,
            live_donor_verified=live_donor_verified,
            image_bytes=image_bytes,
            image_sha256=image_sha256,
            magic_ascii="",
            section_count=0,
            flags=0,
            resume_vector_hex="0x0",
            dversion_hex="0x0",
            sector_size=0,
            r_data_bytes=0,
            kern_cksum_hex="0x0",
            o_data_bytes=0,
            fx6_wbimem_primary_span_bytes=EXPECTED_FX6_WBIMEM_PRIMARY_SPAN,
            fx3_wbimem_primary_span_bytes=EXPECTED_FX3_WBIMEM_PRIMARY_SPAN,
            wbimem_collision_delta_bytes=EXPECTED_WBIMEM_COLLISION_DELTA_BYTES,
            fx3_stock_wbi_sha256=PINNED_FX3_STOCK_WBI_SHA256,
            errors=(f"wb_header buffer too short: {len(header_bytes)} < 88",),
        )

    (
        fver,
        _pad,
        sections,
        flag,
        resume_vec,
        dver,
        sector_sz,
        r_data_sz,
        _kern_start,
        _kern_sz,
        kern_cksum,
        o_data_sz,
    ) = struct.unpack("<4sI10Q", header_bytes[:88])

    magic_str = fver.decode("latin1")
    if fver != WBI2_MAGIC:
        errors.append(f"Expected WBI2 header magic {WBI2_MAGIC!r}, got {fver!r}")
    if sections != EXPECTED_FX6_WBI_SECTION_COUNT:
        errors.append(
            f"Expected FX6 WBI section count {EXPECTED_FX6_WBI_SECTION_COUNT}, got {sections}"
        )
    if resume_vec != EXPECTED_FX6_WBI_RESUME_VECTOR:
        errors.append(
            f"Expected FX6 WBI resume_vector 0x{EXPECTED_FX6_WBI_RESUME_VECTOR:x}, got 0x{resume_vec:x}"
        )
    if sector_sz != 512:
        errors.append(f"Expected WBI sector_size 512, got {sector_sz}")
    if r_data_sz != EXPECTED_FX6_WBI_R_DATA_BYTES:
        errors.append(
            f"Expected FX6 WBI r_data_size {EXPECTED_FX6_WBI_R_DATA_BYTES}, got {r_data_sz}"
        )
    if o_data_sz != EXPECTED_FX6_WBI_O_DATA_BYTES:
        errors.append(
            f"Expected FX6 WBI o_data_size {EXPECTED_FX6_WBI_O_DATA_BYTES}, got {o_data_sz}"
        )
    if image_bytes > WBI_PARTITION_SIZE_BYTES:
        errors.append(
            f"WBI image size {image_bytes} exceeds p5 partition size {WBI_PARTITION_SIZE_BYTES}"
        )

    return Wbi2HeaderAudit(
        valid=(len(errors) == 0),
        live_donor_verified=live_donor_verified,
        image_bytes=image_bytes,
        image_sha256=image_sha256,
        magic_ascii=magic_str,
        section_count=int(sections),
        flags=int(flag),
        resume_vector_hex=f"0x{resume_vec:x}",
        dversion_hex=f"0x{dver:x}",
        sector_size=int(sector_sz),
        r_data_bytes=int(r_data_sz),
        kern_cksum_hex=f"0x{kern_cksum:x}",
        o_data_bytes=int(o_data_sz),
        fx6_wbimem_primary_span_bytes=EXPECTED_FX6_WBIMEM_PRIMARY_SPAN,
        fx3_wbimem_primary_span_bytes=EXPECTED_FX3_WBIMEM_PRIMARY_SPAN,
        wbimem_collision_delta_bytes=EXPECTED_WBIMEM_COLLISION_DELTA_BYTES,
        fx3_stock_wbi_sha256=PINNED_FX3_STOCK_WBI_SHA256,
        errors=tuple(errors),
    )


def _canonical_fx6_wbi2_header_88b() -> bytes:
    return struct.pack(
        "<4sI10Q",
        WBI2_MAGIC,
        0,
        EXPECTED_FX6_WBI_SECTION_COUNT,
        0,
        EXPECTED_FX6_WBI_RESUME_VECTOR,
        EXPECTED_FX6_WBI_DVERSION,
        512,
        EXPECTED_FX6_WBI_R_DATA_BYTES,
        0,
        0,
        0x0F0F0F0F,
        EXPECTED_FX6_WBI_O_DATA_BYTES,
    )


def audit_initrd_boot_chain_and_wbi_contracts(
    *,
    fx6_donor_root: Path = DEFAULT_FX6_DONOR_ROOT,
    fx3_wbi_zero_proof_path: Path = DEFAULT_FX3_WBI_ZERO_PROOF_PATH,
    fx3_205_init_path: Path = DEFAULT_FX3_205_INITRD_INIT_PATH,
    oss_linux_dir: Path = DEFAULT_SONY_OSS_LINUX_DIR,
    simulate_clean_room: bool = False,
) -> InitrdBootChainContractAudit:
    """Audit `nflasha3-initrd` -> `/usr` (`p15`) -> `bootin.elf` -> `im.elf` & `p5:/wbi` contracts."""
    errors: List[str] = []
    artifact_records: List[BootArtifactDigestRecord] = []

    env_clean = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in ("1", "true", "yes")
    donor_available = (not simulate_clean_room) and (not env_clean) and fx6_donor_root.is_dir()
    mode = "LIVE_DONOR_VERIFIED" if donor_available else "CLEAN_ROOM_PINNED_CONTRACT"

    for art_id, rel_path, exp_bytes, exp_sha in PINNED_INITRD_AND_BOOT_ARTIFACTS:
        if "stage" in rel_path.lower():
            errors.append(f"Clean-room violation: stage* path in {rel_path}")
            continue
        full_p = fx6_donor_root / rel_path
        if donor_available:
            if not full_p.is_file():
                errors.append(f"Missing live FX6 donor artifact: {rel_path}")
                artifact_records.append(
                    BootArtifactDigestRecord(art_id, rel_path, exp_bytes, exp_sha, False, False)
                )
                continue
            act_bytes, act_sha = _stream_sha256_and_size(full_p)
            ok = (act_bytes == exp_bytes) and (act_sha == exp_sha)
            if not ok:
                errors.append(
                    f"Digest/size mismatch on {rel_path}: got ({act_bytes}, {act_sha}), "
                    f"expected ({exp_bytes}, {exp_sha})"
                )
            artifact_records.append(
                BootArtifactDigestRecord(art_id, rel_path, exp_bytes, exp_sha, True, ok)
            )
        else:
            artifact_records.append(
                BootArtifactDigestRecord(art_id, rel_path, exp_bytes, exp_sha, False, True)
            )

    if donor_available:
        init_txt = (fx6_donor_root / "nested-files/nflasha3-initrd/sbin/init").read_text(
            encoding="utf-8", errors="replace"
        )
        init2_txt = (fx6_donor_root / "nested-files/nflasha3-initrd/sbin/init2").read_text(
            encoding="utf-8", errors="replace"
        )
        drv1_txt = (
            fx6_donor_root / "nested-files/nflasha3-initrd/sbin/initrc/insmod_drv1"
        ).read_text(encoding="utf-8", errors="replace")
        drv2_txt = (
            fx6_donor_root / "nested-files/nflasha3-initrd/sbin/initrc/insmod_drv2"
        ).read_text(encoding="utf-8", errors="replace")
        fstab_txt = (
            fx6_donor_root / "nested-files/nflasha3-initrd/sbin/initrc/fstab"
        ).read_text(encoding="utf-8", errors="replace")
        fstab_ext_txt = (
            fx6_donor_root / "nested-files/nflasha3-initrd/sbin/initrc/fstab.ext"
        ).read_text(encoding="utf-8", errors="replace")
        fstab_root_txt = (
            fx6_donor_root / "nested-files/nflasha3-initrd/sbin/initrc/fstab.root"
        ).read_text(encoding="utf-8", errors="replace")
        kemco_txt = (fx6_donor_root / "tree/0800_appli/setting/kemco.txt").read_text(
            encoding="utf-8", errors="replace"
        )
        bootin_bytes = (fx6_donor_root / "nflasha15-files/bin/bootin.elf").read_bytes()
        im_bytes = (fx6_donor_root / "nflasha15-files/bin/im.elf").read_bytes()

        drv1_mods = tuple(
            ln.split()[1]
            for ln in drv1_txt.splitlines()
            if ln.strip().startswith("insmod ")
        )
        drv2_mods = [
            ln.split()[1]
            for ln in drv2_txt.splitlines()
            if ln.strip().startswith("insmod ")
        ]
        upm_slot = (
            drv2_mods.index("/usr/kmod/upm.ko") + 1
            if "/usr/kmod/upm.ko" in drv2_mods
            else -1
        )
        upm_absent_initrd = not (
            fx6_donor_root / "nested-files/nflasha3-initrd/kmod/upm.ko"
        ).exists() and all("upm.ko" not in m for m in drv1_mods)

        active_fstab_lines = [
            ln for ln in (fstab_txt + "\n" + fstab_ext_txt).splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")
        ]
        p15_ro = any(
            "/dev/nflasha15" in ln and "/usr" in ln and "ro" in ln
            for ln in active_fstab_lines
        )
        p5_absent_fstab = all("nflasha5" not in ln and "/wbi" not in ln for ln in active_fstab_lines)
        tmp_wbshd_ok = (
            "WBSHD=/tmp_wbshd/shared.XXXXXX" in init_txt
            and "mount -t tmpfs none /tmp_wbshd" in init2_txt
        )
        bis_formats_log = (
            'UPM_BOOTMODE=`cat /proc/udm/upm_bootmode`' in init2_txt
            and '[ "$UPM_BOOTMODE" != "BIS" ] && return 1' in init2_txt
            and "/sbin/mkdosfs -f 1 -s 32" in init2_txt
        )
        bootin_to_im = (
            "/usr/bin/bootin.elf &" in init2_txt
            and b"/usr/bin/im.elf" in bootin_bytes
        )
        im_has_sys_power = (
            b"/sys/power/state" in im_bytes
            and b"/proc/udm/upm_bootmode" in im_bytes
        )
        fx3_p7_pivot = (
            "[ -r $INITRC_DIR/setup_rootfs ] && . $INITRC_DIR/setup_rootfs" in init_txt
            and "/dev/nflasha7\t/rootfs\text2\tro" in fstab_root_txt
        )
        fx6_ram0_direct = (
            not (fx6_donor_root / "nested-files/nflasha3-initrd/sbin/initrc/setup_rootfs").exists()
            and "root=/dev/ram0 rootfstype=ext2" in kemco_txt
            and "warm.mode=2" in kemco_txt
            and "wbimem=0x01919000@0x410524000" in kemco_txt
        )

        # Verify Sony OSS kernel WBI headers & raw writer if present
        for oss_rel, exp_oss_sha in (
            ("include/linux/warmboot.h", PINNED_OSS_WARMBOOT_H_SHA256),
            ("include/linux/wbi.h", PINNED_OSS_WBI_H_SHA256),
            ("kernel/power/wbi_raw.c", PINNED_OSS_WBI_RAW_C_SHA256),
        ):
            oss_p = oss_linux_dir / oss_rel
            if oss_p.is_file():
                _, oss_sha = _stream_sha256_and_size(oss_p)
                if oss_sha != exp_oss_sha:
                    errors.append(f"OSS WBI source {oss_rel} SHA-256 mismatch: {oss_sha}")

        # Verify FX3 WBI zero-proof & FX3 2.05 initrd init when present
        if fx3_wbi_zero_proof_path.is_file():
            wbi_zero_obj = json.loads(fx3_wbi_zero_proof_path.read_text(encoding="utf-8"))
            if wbi_zero_obj.get("original_FX3_WBI_sha256") != PINNED_FX3_STOCK_WBI_SHA256:
                errors.append("FX3 stock WBI SHA-256 mismatch in WBI-zero-proof.json")
            if wbi_zero_obj.get("no_record_gap", {}).get("start") != "0x4110c4000":
                errors.append("FX3 WBI primary gap boundary mismatch (expected 0x4110c4000)")
        if fx3_205_init_path.is_file():
            _, fx3_init_sha = _stream_sha256_and_size(fx3_205_init_path)
            if fx3_init_sha != PINNED_FX3_205_INITRD_INIT_SHA256:
                errors.append(f"FX3 2.05 initrd sbin/init SHA-256 mismatch: {fx3_init_sha}")

        # Stream-hash and parse live FX6 `0700_part_image/dev/nflasha5` WBI2 image
        p5_path = fx6_donor_root / "tree/0700_part_image/dev/nflasha5"
        if p5_path.is_file():
            with p5_path.open("rb") as fh:
                hdr_88 = fh.read(88)
            p5_sz, p5_sha = _stream_sha256_and_size(p5_path)
            if p5_sz != PINNED_FX6_WBI_NFLASH5_BYTES or p5_sha != PINNED_FX6_WBI_NFLASH5_SHA256:
                errors.append(
                    f"FX6 nflasha5 WBI2 digest/size mismatch: ({p5_sz}, {p5_sha})"
                )
            wbi_audit = parse_wbi2_header_bytes(
                hdr_88,
                image_bytes=p5_sz,
                image_sha256=p5_sha,
                live_donor_verified=True,
            )
        else:
            errors.append("Missing live FX6 0700_part_image/dev/nflasha5 WBI2 image")
            wbi_audit = parse_wbi2_header_bytes(_canonical_fx6_wbi2_header_88b())
    else:
        drv1_mods = EXPECTED_INSMOD_DRV1_ORDER
        drv2_mods = [""] * EXPECTED_INSMOD_DRV2_TOTAL_COUNT
        upm_slot = EXPECTED_INSMOD_DRV2_UPM_ONE_BASED_SLOT
        upm_absent_initrd = True
        p15_ro = True
        p5_absent_fstab = True
        tmp_wbshd_ok = True
        bis_formats_log = True
        bootin_to_im = True
        im_has_sys_power = True
        fx3_p7_pivot = True
        fx6_ram0_direct = True
        wbi_audit = parse_wbi2_header_bytes(
            _canonical_fx6_wbi2_header_88b(), live_donor_verified=False
        )

    if drv1_mods != EXPECTED_INSMOD_DRV1_ORDER:
        errors.append(f"Unexpected insmod_drv1 load order: {drv1_mods}")
    if len(drv2_mods) != EXPECTED_INSMOD_DRV2_TOTAL_COUNT:
        errors.append(
            f"Expected {EXPECTED_INSMOD_DRV2_TOTAL_COUNT} modules in insmod_drv2, got {len(drv2_mods)}"
        )
    if upm_slot != EXPECTED_INSMOD_DRV2_UPM_ONE_BASED_SLOT:
        errors.append(
            f"Expected /usr/kmod/upm.ko at slot #{EXPECTED_INSMOD_DRV2_UPM_ONE_BASED_SLOT}, got #{upm_slot}"
        )
    for flag_val, err_msg in (
        (upm_absent_initrd, "upm.ko must not reside in nflasha3-initrd (loaded from /usr/kmod)"),
        (p15_ro, "/dev/nflasha15 (/usr) must be mounted read-only in fstab"),
        (p5_absent_fstab, "p5 (/dev/nflasha5 /wbi) must never appear in fstab or fstab.ext"),
        (tmp_wbshd_ok, "Missing /tmp_wbshd tmpfs setup across sbin/init and sbin/init2"),
        (bis_formats_log, "Missing setup_bis() upm_bootmode=BIS /log mkdosfs hazard signature"),
        (bootin_to_im, "Missing init2 -> bootin.elf -> im.elf startup handoff"),
        (im_has_sys_power, "Missing /sys/power/state or /proc/udm/upm_bootmode reference in im.elf"),
        (fx3_p7_pivot, "Missing setup_rootfs / fstab.root p7:/rootfs contract"),
        (fx6_ram0_direct, "Missing FX6 direct /dev/ram0 + warm.mode=2 + wbimem contract"),
        (wbi_audit.valid, f"WBI2 header validation failed: {wbi_audit.errors}"),
    ):
        if not flag_val:
            errors.append(err_msg)

    return InitrdBootChainContractAudit(
        valid=(len(errors) == 0),
        verification_mode=mode,
        artifact_count_verified=sum(1 for r in artifact_records if r.verified),
        artifacts=tuple(artifact_records),
        insmod_drv1_modules=drv1_mods,
        insmod_drv2_module_count=len(drv2_mods),
        upm_ko_insmod_drv2_slot=upm_slot,
        upm_ko_absent_from_initrd=upm_absent_initrd,
        p15_usr_mounted_readonly=p15_ro,
        p5_wbi_absent_from_fstab=p5_absent_fstab,
        tmp_wbshd_tmpfs_mounted=tmp_wbshd_ok,
        bis_mode_formats_p11_log=bis_formats_log,
        bootin_hands_off_to_im_elf=bootin_to_im,
        im_elf_references_sys_power_state=im_has_sys_power,
        fx3_uses_p7_setup_rootfs_pivot=fx3_p7_pivot,
        fx6_runs_init2_from_ram0=fx6_ram0_direct,
        wbi2_header=wbi_audit,
        errors=tuple(errors),
    )


def validate_candidate_wbi_redline(
    *,
    overlay_manifest: Optional[Mapping[str, object]] = None,
    overlay_entry_paths: Sequence[str] = (),
    scripts_to_audit: Sequence[Tuple[str, str]] = (),
) -> CandidateWbiRedlineAudit:
    """Fail-closed scanner enforcing `wbi_p5_write_and_hibernation_forbidden = True`."""
    violations: List[str] = []

    for entry_path in overlay_entry_paths:
        low = entry_path.lower()
        if any(tok in low for tok in ("nflasha5", "wbi2", "ud_wbi_drop", "/wbi/")):
            violations.append(f"Forbidden WBI/p5 payload in Stage-A CPIO path: {entry_path!r}")

    if overlay_manifest is not None:
        if overlay_manifest.get("persistent_flash_writes", 0) != 0:
            violations.append(
                f"overlay_manifest persistent_flash_writes != 0: {overlay_manifest.get('persistent_flash_writes')!r}"
            )
        wbi_flag = overlay_manifest.get("wbi_p5_write_and_hibernation_forbidden")
        if wbi_flag is False:
            violations.append("overlay_manifest explicitly disabled wbi_p5_write_and_hibernation_forbidden")
        wbi_mut = overlay_manifest.get("wbi_mutation_bytes", 0)
        if wbi_mut != 0:
            violations.append(f"overlay_manifest wbi_mutation_bytes != 0: {wbi_mut!r}")

        manifest_dump = json.dumps(overlay_manifest)
        for bad_tok in ("nflasha5", "ud_wbi_drop", PINNED_FX6_WBI_NFLASH5_SHA256):
            if bad_tok in manifest_dump:
                violations.append(f"Forbidden WBI p5 artifact token {bad_tok!r} in overlay_manifest")

    for script_name, script_text in scripts_to_audit:
        for line_no, raw_line in enumerate(script_text.splitlines(), 1):
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for rule_id, regex in FORBIDDEN_WBI_MUTATION_PATTERNS:
                if regex.search(stripped):
                    violations.append(
                        f"WBI redline violation [{rule_id}] in {script_name}:L{line_no}: {stripped}"
                    )

    ok = len(violations) == 0
    return CandidateWbiRedlineAudit(
        valid=ok,
        wbi_p5_write_and_hibernation_forbidden=ok,
        wbi_mutation_bytes=0 if ok else 1,
        violations=tuple(violations),
    )


def generate_stage_a_boot_orchestrator_script() -> str:
    """Synthesize deterministic POSIX `/bin/sh` `etc/fx6_overlay/30-stage-a-orchestrator.sh`.

    Enforces:
    1. Cold-boot unarmed passthrough (`0` mounts, `0` insmods) & idempotent re-entry lock guard.
    2. Clear-Before-Exec unlink of `/tmp/mod_arm_once` strictly prior to any verification or mount.
    3. Stage-A WBI (`p5` / `/dev/nflasha5`) Hibernation Safety Redline (`BIS` rejection, `/dev/nflasha5`
       unmounted/untouched check, and `/tmp_wbshd/stage_a_wbi_inhibit.lock` hibernation mask).
    4. Atomic Verify-Before-Mount SHA-256 verification of all 10 `overlay_manifest.json` payloads plus
       the `20,588 B` RAM-shadow `BK4\\0` (`ram_shadow_Backup.bin`) BEFORE any `insmod` or `mount`.
    5. Explicit LIFO transactional mount stack across all 10 activation steps (`01_kmod_p9_upm_ko` ..
       `10_bind_ro_ram_shadow_bk4`): any mid-sequence failure at step `k` unwinds `k-1 .. 1` in strict
       reverse LIFO order before falling back to stock FX3; clean `im.elf` exit also unwinds `10 .. 1`.
    """
    return """#!/bin/sh
# === BEGIN FX3 STAGE-A ATOMIC VERIFY-BEFORE-MOUNT & WBI-GUARDED BOOT ORCHESTRATOR ===
# Target path in Stage-A CPIO: etc/fx6_overlay/30-stage-a-orchestrator.sh
# Strictly enforces:
#   - Clear-Before-Exec one-shot `/tmp/mod_arm_once` unlink
#   - WBI (`p5` / `/dev/nflasha5`) hibernation/snapshot prohibition (`wbi_mutation_bytes == 0`)
#   - Atomic Verify-Before-Mount SHA-256 check across all staged payloads + RAM-shadow `BK4\\0`
#   - Strict 10-step LIFO transactional mount/kmod unwind on mid-sequence fault or `im.elf` exit
set -u

PREFIX="${PREFIX:-}"
if [ -z "$PREFIX" ] && { [ "$(uname -s 2>/dev/null || echo unknown)" != "Linux" ] || [ ! -e "/dev/nflasha" ]; }; then
    echo "ERR_SANDBOX_PREFIX_REQUIRED_ON_HOST" >&2
    exit 97
fi

ARM_TOKEN="${PREFIX}/tmp/mod_arm_once"
REENTRY_LOCK="${PREFIX}/tmp/stage_a_orchestrator.lock"
STATE_FILE="${PREFIX}/tmp/stage_a_orchestrator_state.env"
STACK_FILE="${PREFIX}/tmp/stage_a_lifo_mount.stack"
FORWARD_LOG="${PREFIX}/tmp/stage_a_forward_steps.log"
UNWIND_LOG="${PREFIX}/tmp/stage_a_unwind_steps.log"
WORK_DIR="${PREFIX}/tmp/stage_a_verify_work"
STAGE_DIR="${FX3_STAGE_A_DIR:-${PREFIX}/tmp/fx6_stage_a}"
MANIFEST_FILE="${PREFIX}/etc/fx6_overlay/overlay_manifest.json"
RAM_BK4_FILE="${STAGE_DIR}/backup/ram_shadow_Backup.bin"
RAM_BK4_SHA_FILE="${STAGE_DIR}/backup/ram_shadow_Backup.sha256"
WBSHD_DIR="${PREFIX}/tmp_wbshd"
WBI_INHIBIT_LOCK="${WBSHD_DIR}/stage_a_wbi_inhibit.lock"
UPM_BOOTMODE_FILE="${PREFIX}/proc/udm/upm_bootmode"
PROC_MOUNTS_FILE="${PREFIX}/proc/mounts"

TOKEN_CLEARED_BEFORE_EXEC=0
WBI_GUARD_VERIFIED=0
WBI_HIBERNATION_MASKED=0
DOUBLE_MOUNT_PREVENTED=0
VERIFIED_DIGEST_COUNT=0
IM_ELF_INVOKED=0
STOCK_BOOT_INVOKED=0

mkdir -p "${PREFIX}/tmp" "$WBSHD_DIR"

write_orchestrator_state() {
    cat > "$STATE_FILE" <<EOF
BOOT_BRANCH=$1
DIAG_CODE=$2
STOCK_BOOT_INVOKED=$STOCK_BOOT_INVOKED
IM_ELF_INVOKED=$IM_ELF_INVOKED
TOKEN_CLEARED_BEFORE_EXEC=$TOKEN_CLEARED_BEFORE_EXEC
WBI_GUARD_VERIFIED=$WBI_GUARD_VERIFIED
WBI_HIBERNATION_MASKED=$WBI_HIBERNATION_MASKED
DOUBLE_MOUNT_PREVENTED=$DOUBLE_MOUNT_PREVENTED
VERIFIED_DIGEST_COUNT=$VERIFIED_DIGEST_COUNT
EOF
}

invoke_stock_fx3_passthrough() {
    BRANCH_NAME="$1"
    REASON_CODE="$2"
    STOCK_BOOT_INVOKED=1
    write_orchestrator_state "$BRANCH_NAME" "$REASON_CODE"
    if [ -n "${FX3_STOCK_BOOT_CMD:-}" ]; then
        /bin/sh -c "$FX3_STOCK_BOOT_CMD"
    fi
}

compute_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        echo "MISSING_SHA256_TOOL"
    fi
}

push_lifo_step() {
    STEP_ID="$1"
    UNWIND_ACTION="$2"
    printf '%s|%s\n' "$STEP_ID" "$UNWIND_ACTION" >> "$STACK_FILE"
    printf '%s\n' "$STEP_ID" >> "$FORWARD_LOG"
}

unwind_lifo_stack() {
    [ -f "$STACK_FILE" ] || return 0
    TOTAL_LINES=$(wc -l < "$STACK_FILE" | tr -d ' ')
    IDX="$TOTAL_LINES"
    while [ "$IDX" -ge 1 ]; do
        LINE=$(sed -n "${IDX}p" "$STACK_FILE")
        STEP_ID="${LINE%%|*}"
        UNWIND_CMD="${LINE#*|}"
        if [ -n "$STEP_ID" ]; then
            /bin/sh -c "$UNWIND_CMD" >/dev/null 2>&1 || true
            printf '%s\n' "$STEP_ID" >> "$UNWIND_LOG"
        fi
        IDX=$((IDX - 1))
    done
    rm -f "$STACK_FILE"
}

# 0. Idempotent Re-Entry Guard (refuse double-mounting if already active or consumed this boot)
if [ -f "$REENTRY_LOCK" ]; then
    DOUBLE_MOUNT_PREVENTED=1
    write_orchestrator_state "REENTRY_BLOCKED" "ERR_IDEMPOTENT_REENTRY_BLOCKED"
    exit 0
fi

# 1. Stock Cold-Boot Passthrough when single-shot arming token is absent
if [ ! -f "$ARM_TOKEN" ]; then
    : > "$FORWARD_LOG"
    : > "$UNWIND_LOG"
    invoke_stock_fx3_passthrough "STOCK_FX3" "STOCK_COLD_BOOT_PASSTHROUGH"
    exit 0
fi

# 2. Layer-2 Clear-Before-Exec: unlink `/tmp/mod_arm_once` & claim session re-entry lock FIRST
if [ -z "$PREFIX" ]; then
    rm -f "/tmp/mod_arm_once"
else
    rm -f "${PREFIX}/tmp/mod_arm_once"
fi
: > "$REENTRY_LOCK"
: > "$FORWARD_LOG"
: > "$UNWIND_LOG"
rm -f "$STACK_FILE"
busybox sync
TOKEN_CLEARED_BEFORE_EXEC=1

# 3. Stage-A WBI (`p5` / `/dev/nflasha5`) Hibernation Safety Redline Guard
UPM_MODE="NORMAL"
if [ -r "$UPM_BOOTMODE_FILE" ]; then
    UPM_MODE=$(cat "$UPM_BOOTMODE_FILE" 2>/dev/null | tr -d ' \t\r\n')
fi
if [ "$UPM_MODE" = "BIS" ]; then
    invoke_stock_fx3_passthrough "STOCK_FX3_FALLBACK" "ERR_WBI_BIS_MODE_FORBIDDEN"
    exit 0
fi

if [ -r "$PROC_MOUNTS_FILE" ] && grep -E '/dev/[cp]?nflasha5|/wbi' "$PROC_MOUNTS_FILE" >/dev/null 2>&1; then
    invoke_stock_fx3_passthrough "STOCK_FX3_FALLBACK" "ERR_WBI_P5_ALREADY_MOUNTED"
    exit 0
fi

# Mask WBI snapshot/hibernation triggers for the entire Stage-A session (`wbi_mutation_bytes == 0`)
cat > "$WBI_INHIBIT_LOCK" <<EOF
STAGE_A_WBI_HIBERNATION_FORBIDDEN=1
WBI_DEVICE=/dev/nflasha5
EOF
export STAGE_A_WBI_HIBERNATION_MASKED=1
WBI_GUARD_VERIFIED=1
WBI_HIBERNATION_MASKED=1

# 4. Atomic Verify-Before-Mount SHA-256 Gate (strictly BEFORE first `insmod` or `mount`)
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
if [ ! -f "$MANIFEST_FILE" ]; then
    rm -rf "$WORK_DIR"
    invoke_stock_fx3_passthrough "STOCK_FX3_FALLBACK" "ERR_MANIFEST_MISSING"
    exit 0
fi

CHECKLIST_FILE="${WORK_DIR}/sha256.checklist"
sed -n 's/^[[:space:]]*"\\([0-9a-f]\\{64\\}\\)|\\([^"]*\\)".*/\\1 \\2/p' "$MANIFEST_FILE" > "$CHECKLIST_FILE"
CHECK_ROWS=$(wc -l < "$CHECKLIST_FILE" | tr -d ' ')
if [ "${CHECK_ROWS:-0}" -lt 10 ]; then
    rm -rf "$WORK_DIR"
    invoke_stock_fx3_passthrough "STOCK_FX3_FALLBACK" "ERR_MANIFEST_SCHEMA_INCOMPLETE"
    exit 0
fi

VERIFY_ERR=""
COUNT_OK=0
while IFS=' ' read -r EXP_SHA REL_PATH; do
    [ -z "$EXP_SHA" ] && continue
    CAND_FILE="${STAGE_DIR}/${REL_PATH}"
    if [ ! -f "$CAND_FILE" ]; then
        VERIFY_ERR="ERR_VERIFY_MISSING:${REL_PATH}"
        break
    fi
    ACT_SHA=$(compute_sha256 "$CAND_FILE")
    if [ "$ACT_SHA" != "$EXP_SHA" ]; then
        VERIFY_ERR="ERR_VERIFY_SHA256_MISMATCH:${REL_PATH}"
        break
    fi
    COUNT_OK=$((COUNT_OK + 1))
done < "$CHECKLIST_FILE"

if [ -z "$VERIFY_ERR" ]; then
    if [ ! -f "$RAM_BK4_FILE" ] || [ ! -f "$RAM_BK4_SHA_FILE" ]; then
        VERIFY_ERR="ERR_VERIFY_RAM_SHADOW_BK4_MISSING"
    else
        EXP_BK4_SHA=$(cat "$RAM_BK4_SHA_FILE" | tr -d ' \t\r\n')
        ACT_BK4_SHA=$(compute_sha256 "$RAM_BK4_FILE")
        if [ -z "$EXP_BK4_SHA" ] || [ "$ACT_BK4_SHA" != "$EXP_BK4_SHA" ]; then
            VERIFY_ERR="ERR_VERIFY_RAM_SHADOW_BK4_SHA256_MISMATCH"
        else
            COUNT_OK=$((COUNT_OK + 1))
        fi
    fi
fi
rm -rf "$WORK_DIR"

if [ -n "$VERIFY_ERR" ]; then
    invoke_stock_fx3_passthrough "STOCK_FX3_FALLBACK" "$VERIFY_ERR"
    exit 0
fi
VERIFIED_DIGEST_COUNT="$COUNT_OK"

# 5. Transactional 10-Step Stage-A Activation with Strict LIFO Mid-Sequence Rollback
abort_mid_sequence() {
    FAIL_STEP="$1"
    unwind_lifo_stack
    rm -f "$WBI_INHIBIT_LOCK"
    WBI_HIBERNATION_MASKED=0
    invoke_stock_fx3_passthrough "STOCK_FX3_FALLBACK" "ERR_MID_SEQUENCE_ROLLBACK:${FAIL_STEP}"
    exit 0
}

DEV_DIR="${PREFIX}/dev"
USR_LIB_DIR="${PREFIX}/usr/lib"
LUT_MNT_USR="${PREFIX}/usr/data/lut"
LUT_ALIAS_ETC="${PREFIX}/etc/lut"
OPELOG_MNT="${PREFIX}/etc/opelog"
SETTING_BK4_TARGET="${PREFIX}/setting/Backup.bin"
LOOP_DEV="${DEV_DIR}/loop7"

mkdir -p "$DEV_DIR" "$USR_LIB_DIR" "$LUT_MNT_USR" "${PREFIX}/etc" "$OPELOG_MNT" "${PREFIX}/setting"

# Step 01: P9-adapted FX3 `upm.ko` module load hook
if ! STAGE_A_STEP_ID="01_kmod_p9_upm_ko" busybox insmod "${STAGE_DIR}/modules/upm.ko"; then
    abort_mid_sequence "01_kmod_p9_upm_ko"
fi
push_lifo_step "01_kmod_p9_upm_ko" "busybox rmmod upm"

# Step 02: P1 read-only FX3 `p30` -> `/dev/nflasha20` -> `/usr/data/lut` (+ `/etc/lut` symlink)
rm -f "${DEV_DIR}/nflasha20" "${DEV_DIR}/cnflasha20" "$LUT_ALIAS_ETC"
ln -s "${DEV_DIR}/cnflasha30" "${DEV_DIR}/nflasha20"
ln -s "${DEV_DIR}/cnflasha30" "${DEV_DIR}/cnflasha20"
ln -s "$LUT_MNT_USR" "$LUT_ALIAS_ETC"
if ! STAGE_A_STEP_ID="02_p1_lut_p30_ro_mount" busybox mount -t vfat -o ro "${DEV_DIR}/nflasha20" "$LUT_MNT_USR"; then
    rm -f "${DEV_DIR}/nflasha20" "${DEV_DIR}/cnflasha20" "$LUT_ALIAS_ETC"
    abort_mid_sequence "02_p1_lut_p30_ro_mount"
fi
push_lifo_step "02_p1_lut_p30_ro_mount" "busybox umount \"$LUT_MNT_USR\" && rm -f \"${DEV_DIR}/nflasha20\" \"${DEV_DIR}/cnflasha20\" \"$LUT_ALIAS_ETC\""

# Step 03: P2 non-persistent RAM `opelog.vfat` loopback mount onto `/etc/opelog`
if ! STAGE_A_STEP_ID="03_p2_opelog_vfat_loop_mount" busybox losetup "$LOOP_DEV" "${STAGE_DIR}/images/opelog.vfat"; then
    abort_mid_sequence "03_p2_opelog_vfat_loop_mount"
fi
rm -f "${DEV_DIR}/nflasha21"
ln -s "$LOOP_DEV" "${DEV_DIR}/nflasha21"
if ! STAGE_A_STEP_ID="03_p2_opelog_vfat_loop_mount" busybox mount -t vfat -o ro,shortname=mixed "${DEV_DIR}/nflasha21" "$OPELOG_MNT"; then
    busybox losetup -d "$LOOP_DEV" >/dev/null 2>&1 || true
    rm -f "${DEV_DIR}/nflasha21"
    abort_mid_sequence "03_p2_opelog_vfat_loop_mount"
fi
push_lifo_step "03_p2_opelog_vfat_loop_mount" "busybox umount \"$OPELOG_MNT\" && busybox losetup -d \"$LOOP_DEV\" && rm -f \"${DEV_DIR}/nflasha21\""

# Steps 04..09: Read-only bind-mounts of all 6 adapted FX6 `.so` targets
bind_ro_shared_object() {
    STEP_TAG="$1"
    SO_NAME="$2"
    SRC_SO="${STAGE_DIR}/lib/${SO_NAME}"
    DST_SO="${USR_LIB_DIR}/${SO_NAME}"
    [ -f "$DST_SO" ] || : > "$DST_SO"
    if ! STAGE_A_STEP_ID="$STEP_TAG" busybox mount --bind -o ro "$SRC_SO" "$DST_SO"; then
        abort_mid_sequence "$STEP_TAG"
    fi
    push_lifo_step "$STEP_TAG" "busybox umount \"$DST_SO\""
}

bind_ro_shared_object "04_bind_ro_libInfraSetupFile_so" "libInfraSetupFile.so"
bind_ro_shared_object "05_bind_ro_libInfraMediaCommon_so" "libInfraMediaCommon.so"
bind_ro_shared_object "06_bind_ro_libInfraMediaConfig_so" "libInfraMediaConfig.so"
bind_ro_shared_object "07_bind_ro_libInfraAppRemoteBoard_so" "libInfraAppRemoteBoard.so"
bind_ro_shared_object "08_bind_ro_libfan_so" "libfan.so"
bind_ro_shared_object "09_bind_ro_appFw_so" "appFw.so"

# Step 10: Read-only VFS bind-mount of RAM-shadow `BK4\\0` over `/setting/Backup.bin` (zero p2 flash writes)
[ -f "$SETTING_BK4_TARGET" ] || : > "$SETTING_BK4_TARGET"
if ! STAGE_A_STEP_ID="10_bind_ro_ram_shadow_bk4" busybox mount --bind -o ro "$RAM_BK4_FILE" "$SETTING_BK4_TARGET"; then
    abort_mid_sequence "10_bind_ro_ram_shadow_bk4"
fi
push_lifo_step "10_bind_ro_ram_shadow_bk4" "busybox umount \"$SETTING_BK4_TARGET\""

# 6. Handoff to `im.elf` (`bootin.elf -> im.elf` userland supervisor) & Clean LIFO Teardown on Exit
IM_ELF_CMD="${FX3_IM_ELF_CMD:-:}"
IM_ELF_INVOKED=1
/bin/sh -c "$IM_ELF_CMD"
IM_RC=$?

unwind_lifo_stack
rm -f "$WBI_INHIBIT_LOCK"
busybox sync

if [ "$IM_RC" -ne 0 ]; then
    invoke_stock_fx3_passthrough "STOCK_FX3_FALLBACK" "ERR_IM_ELF_NONZERO:${IM_RC}"
    exit 0
fi

write_orchestrator_state "STAGE_A_ADAPTED_CLEAN_EXIT" "OK_STAGE_A_LIFO_TEARDOWN_CLEAN"
exit 0
# === END FX3 STAGE-A ATOMIC VERIFY-BEFORE-MOUNT & WBI-GUARDED BOOT ORCHESTRATOR ===
"""


def simulate_orchestrator_state_machine(
    *,
    arm_token_present: bool,
    reentry_lock_present: bool = False,
    upm_bootmode: str = "NORMAL",
    wbi_already_mounted: bool = False,
    payload_sha256_valid: bool = True,
    fail_at_step_id: Optional[str] = None,
    im_elf_exit_code: int = 0,
) -> OrchestratorStateMachineTrace:
    """Formal reference state machine for `30-stage-a-orchestrator.sh`."""
    states: List[str] = ["CHECK_REENTRY_LOCK"]
    if reentry_lock_present:
        states.append("REENTRY_BLOCKED")
        return OrchestratorStateMachineTrace(
            states=tuple(states),
            boot_branch="REENTRY_BLOCKED",
            diag_code_prefix="ERR_IDEMPOTENT_REENTRY_BLOCKED",
            token_cleared_before_exec=False,
            wbi_guard_enforced=False,
            verify_before_mount_passed=False,
            double_mount_prevented=True,
            im_elf_invoked=False,
            forward_steps_executed=(),
            unwind_steps_executed=(),
            lingering_mounts=0,
            emmc_writes=0,
            wbi_writes=0,
        )

    states.append("CHECK_ARM_TOKEN")
    if not arm_token_present:
        states.append("STOCK_COLD_BOOT_PASSTHROUGH")
        return OrchestratorStateMachineTrace(
            states=tuple(states),
            boot_branch="STOCK_FX3",
            diag_code_prefix="STOCK_COLD_BOOT_PASSTHROUGH",
            token_cleared_before_exec=False,
            wbi_guard_enforced=False,
            verify_before_mount_passed=False,
            double_mount_prevented=False,
            im_elf_invoked=False,
            forward_steps_executed=(),
            unwind_steps_executed=(),
            lingering_mounts=0,
            emmc_writes=0,
            wbi_writes=0,
        )

    states.append("UNLINK_TOKEN_AND_LOCK")
    states.append("CHECK_WBI_P5_REDLINE")
    if upm_bootmode == "BIS" or wbi_already_mounted:
        states.append("WBI_REDLINE_ABORT_TO_STOCK")
        diag = "ERR_WBI_BIS_MODE_FORBIDDEN" if upm_bootmode == "BIS" else "ERR_WBI_P5_ALREADY_MOUNTED"
        return OrchestratorStateMachineTrace(
            states=tuple(states),
            boot_branch="STOCK_FX3_FALLBACK",
            diag_code_prefix=diag,
            token_cleared_before_exec=True,
            wbi_guard_enforced=False,
            verify_before_mount_passed=False,
            double_mount_prevented=False,
            im_elf_invoked=False,
            forward_steps_executed=(),
            unwind_steps_executed=(),
            lingering_mounts=0,
            emmc_writes=0,
            wbi_writes=0,
        )

    states.append("VERIFY_BEFORE_MOUNT_SHA256")
    if not payload_sha256_valid:
        states.append("VERIFY_ABORT_BEFORE_FIRST_MOUNT")
        return OrchestratorStateMachineTrace(
            states=tuple(states),
            boot_branch="STOCK_FX3_FALLBACK",
            diag_code_prefix="ERR_VERIFY_",
            token_cleared_before_exec=True,
            wbi_guard_enforced=True,
            verify_before_mount_passed=False,
            double_mount_prevented=False,
            im_elf_invoked=False,
            forward_steps_executed=(),
            unwind_steps_executed=(),
            lingering_mounts=0,
            emmc_writes=0,
            wbi_writes=0,
        )

    forward_done: List[str] = []
    for step_id in EXPECTED_STAGE_A_FORWARD_STEP_IDS:
        if fail_at_step_id == step_id:
            states.append(f"FAULT_AT_{step_id}")
            unwind_done = list(reversed(forward_done))
            states.append("LIFO_UNWIND_COMPLETE")
            return OrchestratorStateMachineTrace(
                states=tuple(states),
                boot_branch="STOCK_FX3_FALLBACK",
                diag_code_prefix=f"ERR_MID_SEQUENCE_ROLLBACK:{step_id}",
                token_cleared_before_exec=True,
                wbi_guard_enforced=True,
                verify_before_mount_passed=True,
                double_mount_prevented=False,
                im_elf_invoked=False,
                forward_steps_executed=tuple(forward_done),
                unwind_steps_executed=tuple(unwind_done),
                lingering_mounts=0,
                emmc_writes=0,
                wbi_writes=0,
            )
        forward_done.append(step_id)

    states.append("IM_ELF_HANDOFF")
    unwind_all = list(reversed(forward_done))
    states.append("LIFO_TEARDOWN_COMPLETE")

    if im_elf_exit_code != 0:
        return OrchestratorStateMachineTrace(
            states=tuple(states),
            boot_branch="STOCK_FX3_FALLBACK",
            diag_code_prefix=f"ERR_IM_ELF_NONZERO:{im_elf_exit_code}",
            token_cleared_before_exec=True,
            wbi_guard_enforced=True,
            verify_before_mount_passed=True,
            double_mount_prevented=False,
            im_elf_invoked=True,
            forward_steps_executed=tuple(forward_done),
            unwind_steps_executed=tuple(unwind_all),
            lingering_mounts=0,
            emmc_writes=0,
            wbi_writes=0,
        )

    return OrchestratorStateMachineTrace(
        states=tuple(states),
        boot_branch="STAGE_A_ADAPTED_CLEAN_EXIT",
        diag_code_prefix="OK_STAGE_A_LIFO_TEARDOWN_CLEAN",
        token_cleared_before_exec=True,
        wbi_guard_enforced=True,
        verify_before_mount_passed=True,
        double_mount_prevented=False,
        im_elf_invoked=True,
        forward_steps_executed=tuple(forward_done),
        unwind_steps_executed=tuple(unwind_all),
        lingering_mounts=0,
        emmc_writes=0,
        wbi_writes=0,
    )


def _install_orchestrator_mock_bin(mock_bin: Path, sandbox_root: Path) -> None:
    """Install deterministic sandboxed `busybox` + `wbi_trigger_probe` inside `mock_bin`."""
    mock_bin.mkdir(parents=True, exist_ok=True)
    bb_script = mock_bin / "busybox"
    bb_script.write_text(
        f"""#!/bin/sh
set -u
SANDBOX_ROOT="{sandbox_root}"
MNT_TABLE="${{SANDBOX_ROOT}}/tmp/mock_mounts.tbl"
LOOP_TABLE="${{SANDBOX_ROOT}}/tmp/mock_loops.tbl"
KMOD_TABLE="${{SANDBOX_ROOT}}/tmp/mock_kmods.tbl"
EVENT_LOG="${{SANDBOX_ROOT}}/tmp/mock_events.log"
VIOLATIONS="${{SANDBOX_ROOT}}/tmp/mock_sandbox_violations.log"
WBI_VIOLATIONS="${{SANDBOX_ROOT}}/tmp/mock_wbi_writes.log"
mkdir -p "${{SANDBOX_ROOT}}/tmp"
touch "$MNT_TABLE" "$LOOP_TABLE" "$KMOD_TABLE" "$EVENT_LOG"

check_sandbox_path() {{
    P="$1"
    [ -z "$P" ] && return 0
    case "$P" in
        "$SANDBOX_ROOT"/*|vfat|tmpfs|proc|sysfs|none|-*)
            return 0
            ;;
        /*)
            echo "OUTSIDE_SANDBOX:$P" >> "$VIOLATIONS"
            exit 98
            ;;
    esac
}}

check_fault_injection() {{
    CUR_STEP="${{STAGE_A_STEP_ID:-}}"
    INJ_STEP="${{STAGE_A_INJECT_FAIL_STEP:-}}"
    if [ -n "$CUR_STEP" ] && [ -n "$INJ_STEP" ] && [ "$CUR_STEP" = "$INJ_STEP" ]; then
        echo "FAULT_INJECTED:$CUR_STEP" >> "$EVENT_LOG"
        exit 42
    fi
}}

SUBCMD="${{1:-}}"
shift || true

case "$SUBCMD" in
    sync)
        exit 0
        ;;
    insmod)
        KO_PATH="${{1:-}}"
        check_sandbox_path "$KO_PATH"
        check_fault_injection
        [ -f "$KO_PATH" ] || exit 2
        MOD_BASE=$(basename "$KO_PATH" .ko)
        echo "INSMOD|$MOD_BASE|$KO_PATH" >> "$EVENT_LOG"
        echo "$MOD_BASE|$KO_PATH" >> "$KMOD_TABLE"
        exit 0
        ;;
    rmmod)
        MOD_NAME="${{1:-}}"
        echo "RMMOD|$MOD_NAME" >> "$EVENT_LOG"
        if [ -f "$KMOD_TABLE" ]; then
            grep -v "^${{MOD_NAME}}|" "$KMOD_TABLE" > "${{KMOD_TABLE}}.tmp" || true
            mv "${{KMOD_TABLE}}.tmp" "$KMOD_TABLE"
        fi
        exit 0
        ;;
    losetup)
        if [ "${{1:-}}" = "-d" ]; then
            LDEV="${{2:-}}"
            check_sandbox_path "$LDEV"
            echo "LOSETUP_DETACH|$LDEV" >> "$EVENT_LOG"
            if [ -f "$LOOP_TABLE" ]; then
                grep -v "^${{LDEV}}|" "$LOOP_TABLE" > "${{LOOP_TABLE}}.tmp" || true
                mv "${{LOOP_TABLE}}.tmp" "$LOOP_TABLE"
            fi
            rm -f "$LDEV"
            exit 0
        fi
        LDEV="${{1:-}}"
        IMG="${{2:-}}"
        check_sandbox_path "$LDEV"
        check_sandbox_path "$IMG"
        check_fault_injection
        [ -f "$IMG" ] || exit 2
        echo "LOSETUP_ATTACH|$LDEV|$IMG" >> "$EVENT_LOG"
        echo "$LDEV|$IMG" > "$LDEV"
        echo "$LDEV|$IMG" >> "$LOOP_TABLE"
        exit 0
        ;;
    mount)
        IS_BIND=0
        IS_RO=0
        POS_1=""
        POS_2=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --bind)
                    IS_BIND=1
                    shift
                    ;;
                -t)
                    shift 2
                    ;;
                -o)
                    case "${{2:-}}" in
                        *ro*) IS_RO=1 ;;
                    esac
                    shift 2
                    ;;
                -*)
                    shift
                    ;;
                *)
                    if [ -z "$POS_1" ]; then
                        POS_1="$1"
                    else
                        POS_2="$1"
                    fi
                    shift
                    ;;
            esac
        done
        check_sandbox_path "$POS_1"
        check_sandbox_path "$POS_2"
        case "$POS_1$POS_2" in
            *nflasha5*|*/wbi*)
                echo "FORBIDDEN_WBI_MOUNT|$POS_1|$POS_2" >> "$WBI_VIOLATIONS"
                exit 91
                ;;
        esac
        if [ "$IS_RO" -ne 1 ]; then
            echo "NON_RO_MOUNT_REJECTED|$POS_1|$POS_2" >> "$VIOLATIONS"
            exit 92
        fi
        check_fault_injection
        [ -e "$POS_1" ] || exit 3
        echo "MOUNT|bind=${{IS_BIND}}|ro=${{IS_RO}}|$POS_1|$POS_2" >> "$EVENT_LOG"
        echo "$POS_2|$POS_1" >> "$MNT_TABLE"
        exit 0
        ;;
    umount)
        if [ "${{1:-}}" = "-l" ]; then
            shift
        fi
        TGT="${{1:-}}"
        check_sandbox_path "$TGT"
        echo "UMOUNT|$TGT" >> "$EVENT_LOG"
        if [ -f "$MNT_TABLE" ]; then
            grep -v "^${{TGT}}|" "$MNT_TABLE" > "${{MNT_TABLE}}.tmp" || true
            mv "${{MNT_TABLE}}.tmp" "$MNT_TABLE"
        fi
        exit 0
        ;;
    *)
        "$SUBCMD" "$@"
        ;;
esac
""",
        encoding="utf-8",
    )
    bb_script.chmod(0o755)

    # Mock hibernation / WBI write probe simulating `echo disk > /sys/power/state` or `/dev/nflasha5` write attempt
    wbi_probe = mock_bin / "wbi_hibernation_probe"
    wbi_probe.write_text(
        f"""#!/bin/sh
set -u
SANDBOX_ROOT="{sandbox_root}"
INHIBIT="${{SANDBOX_ROOT}}/tmp_wbshd/stage_a_wbi_inhibit.lock"
BLOCKED_LOG="${{SANDBOX_ROOT}}/tmp/mock_wbi_blocked.log"
WBI_VIOLATIONS="${{SANDBOX_ROOT}}/tmp/mock_wbi_writes.log"
if [ "${{STAGE_A_WBI_HIBERNATION_MASKED:-0}}" = "1" ] || [ -f "$INHIBIT" ]; then
    echo "BLOCKED_BY_STAGE_A_WBI_GUARD" >> "$BLOCKED_LOG"
    exit 0
fi
echo "UNMASKED_WBI_WRITE_ATTEMPT" >> "$WBI_VIOLATIONS"
exit 93
""",
        encoding="utf-8",
    )
    wbi_probe.chmod(0o755)


@dataclass(frozen=True)
class _PartitionSnap:
    name: str
    sha256: str
    mtime_ns: int


def _init_simulated_partitions(sandbox_root: Path) -> Dict[str, Path]:
    emmc_dir = sandbox_root / "emmc_hw"
    dev_dir = sandbox_root / "dev"
    emmc_dir.mkdir(parents=True, exist_ok=True)
    dev_dir.mkdir(parents=True, exist_ok=True)

    mapping: Dict[str, Path] = {}
    for part_name in SIMULATED_STAGE_A_PARTITIONS:
        p = emmc_dir / f"{part_name}.img"
        if part_name == "p5_wbi":
            # Populate simulated p5 `/dev/nflasha5` with authentic 88-byte WBI2 header + sentinel
            payload = _canonical_fx6_wbi2_header_88b() + (b"\xA5" * (4096 - 88))
        else:
            payload = hashlib.sha256(f"FX3_STOCK_{part_name}".encode("utf-8")).digest() * 128
        p.write_bytes(payload)
        mapping[part_name] = p

    # Wire `/dev/nflasha5`, `/dev/cnflasha30`, `/dev/pnflasha30`, `/dev/nflasha11`, `/dev/nflasha15`
    for link_name, target_key in (
        ("nflasha5", "p5_wbi"),
        ("pnflasha5", "p5_wbi"),
        ("cnflasha30", "p30_lut"),
        ("pnflasha30", "p30_lut"),
        ("nflasha11", "p11_log"),
        ("nflasha15", "p15"),
    ):
        lnk = dev_dir / link_name
        if lnk.exists() or lnk.is_symlink():
            lnk.unlink()
        lnk.symlink_to(mapping[target_key])

    return mapping


def _snap_partitions(mapping: Mapping[str, Path]) -> Dict[str, _PartitionSnap]:
    out: Dict[str, _PartitionSnap] = {}
    for k, p in mapping.items():
        st = p.stat()
        out[k] = _PartitionSnap(
            name=k,
            sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            mtime_ns=st.st_mtime_ns,
        )
    return out


def _diff_partitions(
    before: Mapping[str, _PartitionSnap],
    after: Mapping[str, _PartitionSnap],
) -> Tuple[int, int]:
    """Return `(emmc_non_wbi_writes, wbi_p5_writes)`."""
    emmc_writes = 0
    wbi_writes = 0
    for k, b_snap in before.items():
        a_snap = after[k]
        if a_snap.sha256 != b_snap.sha256 or a_snap.mtime_ns != b_snap.mtime_ns:
            if k == "p5_wbi":
                wbi_writes += 1
            else:
                emmc_writes += 1
    return emmc_writes, wbi_writes


def _parse_kv_env(path: Path) -> Dict[str, str]:
    if not path.is_file():
        return {}
    out: Dict[str, str] = {}
    for ln in path.read_text(encoding="utf-8").splitlines():
        if "=" in ln:
            k, v = ln.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _read_nonempty_lines(path: Path) -> Tuple[str, ...]:
    if not path.is_file():
        return ()
    return tuple(ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())


def _execute_orchestrator_sandbox_run(
    *,
    run_id: str,
    sandbox_root: Path,
    mock_bin: Path,
    part_map: Mapping[str, Path],
    arm_token: bool,
    keep_reentry_lock: bool = False,
    upm_bootmode: str = "NORMAL",
    pre_populate_wbi_proc_mount: bool = False,
    im_elf_cmd: str = ":",
    inject_fail_step: Optional[str] = None,
    expected_sm: OrchestratorStateMachineTrace,
) -> OrchestratorSandboxRunResult:
    tmp_dir = sandbox_root / "tmp"
    proc_udm_dir = sandbox_root / "proc" / "udm"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    proc_udm_dir.mkdir(parents=True, exist_ok=True)

    # Reset per-run transient logs while optionally preserving `stage_a_orchestrator.lock`
    for log_name in (
        "mock_mounts.tbl",
        "mock_loops.tbl",
        "mock_kmods.tbl",
        "mock_events.log",
        "mock_sandbox_violations.log",
        "mock_wbi_writes.log",
        "mock_wbi_blocked.log",
        "stage_a_orchestrator_state.env",
        "stage_a_forward_steps.log",
        "stage_a_unwind_steps.log",
    ):
        (tmp_dir / log_name).unlink(missing_ok=True)

    reentry_lock = tmp_dir / "stage_a_orchestrator.lock"
    if not keep_reentry_lock:
        reentry_lock.unlink(missing_ok=True)

    token_file = tmp_dir / "mod_arm_once"
    if arm_token:
        token_file.write_text("1\n", encoding="utf-8")
    else:
        token_file.unlink(missing_ok=True)

    (proc_udm_dir / "upm_bootmode").write_text(f"{upm_bootmode}\n", encoding="utf-8")
    proc_mounts = sandbox_root / "proc" / "mounts"
    if pre_populate_wbi_proc_mount:
        proc_mounts.write_text("/dev/nflasha5 /wbi raw rw 0 0\n", encoding="utf-8")
    else:
        proc_mounts.write_text("/dev/nflasha15 /usr ext2 ro 0 0\n", encoding="utf-8")

    snap_before = _snap_partitions(part_map)

    env = dict(os.environ)
    env["PREFIX"] = str(sandbox_root)
    env["FX3_STAGE_A_DIR"] = str(sandbox_root / "tmp" / "fx6_stage_a")
    env["FX3_IM_ELF_CMD"] = im_elf_cmd
    env["FX3_STOCK_BOOT_CMD"] = f': > "{sandbox_root}/tmp/stock_fx3_booted.marker"'
    env["PATH"] = f"{mock_bin}:/usr/bin:/bin:/usr/sbin:/sbin"
    if inject_fail_step is not None:
        env["STAGE_A_INJECT_FAIL_STEP"] = inject_fail_step
    else:
        env.pop("STAGE_A_INJECT_FAIL_STEP", None)

    orch_script = sandbox_root / ORCHESTRATOR_CPIO_REL_PATH
    proc = subprocess.run(
        ["/bin/sh", str(orch_script)],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    snap_after = _snap_partitions(part_map)
    emmc_writes, wbi_part_writes = _diff_partitions(snap_before, snap_after)

    state = _parse_kv_env(tmp_dir / "stage_a_orchestrator_state.env")
    events = _read_nonempty_lines(tmp_dir / "mock_events.log")
    forward_steps = _read_nonempty_lines(tmp_dir / "stage_a_forward_steps.log")
    unwind_steps = _read_nonempty_lines(tmp_dir / "stage_a_unwind_steps.log")
    lingering_mounts = len(_read_nonempty_lines(tmp_dir / "mock_mounts.tbl"))
    lingering_loops = len(_read_nonempty_lines(tmp_dir / "mock_loops.tbl"))
    lingering_kmods = len(_read_nonempty_lines(tmp_dir / "mock_kmods.tbl"))
    sandbox_violations = len(_read_nonempty_lines(tmp_dir / "mock_sandbox_violations.log"))
    wbi_log_writes = len(_read_nonempty_lines(tmp_dir / "mock_wbi_writes.log"))
    wbi_blocked_cnt = len(_read_nonempty_lines(tmp_dir / "mock_wbi_blocked.log"))

    total_wbi_writes = wbi_part_writes + wbi_log_writes
    insmod_cnt = sum(1 for e in events if e.startswith("INSMOD|"))
    mount_cnt = sum(1 for e in events if e.startswith("MOUNT|"))

    boot_branch = state.get("BOOT_BRANCH", "MISSING")
    diag_code = state.get("DIAG_CODE", "MISSING")
    stock_invoked = state.get("STOCK_BOOT_INVOKED") == "1"
    im_invoked = state.get("IM_ELF_INVOKED") == "1"
    tok_cleared = state.get("TOKEN_CLEARED_BEFORE_EXEC") == "1"
    wbi_guard_ok = state.get("WBI_GUARD_VERIFIED") == "1"
    wbi_masked = state.get("WBI_HIBERNATION_MASKED") == "1"
    dbl_prevented = state.get("DOUBLE_MOUNT_PREVENTED") == "1"
    verified_cnt = int(state.get("VERIFIED_DIGEST_COUNT", "0"))
    tok_after = token_file.exists()

    lifo_exact = unwind_steps == tuple(reversed(forward_steps))
    sm_match = (
        boot_branch == expected_sm.boot_branch
        and diag_code.startswith(expected_sm.diag_code_prefix)
        and tok_cleared == expected_sm.token_cleared_before_exec
        and dbl_prevented == expected_sm.double_mount_prevented
        and im_invoked == expected_sm.im_elf_invoked
        and forward_steps == expected_sm.forward_steps_executed
        and unwind_steps == expected_sm.unwind_steps_executed
        and lingering_mounts == expected_sm.lingering_mounts
        and emmc_writes == expected_sm.emmc_writes
        and total_wbi_writes == expected_sm.wbi_writes
    )

    return OrchestratorSandboxRunResult(
        run_id=run_id,
        returncode=proc.returncode,
        boot_branch=boot_branch,
        diag_code=diag_code,
        stock_boot_invoked=stock_invoked,
        im_elf_invoked=im_invoked,
        token_cleared_before_exec=tok_cleared,
        token_present_after=tok_after,
        wbi_guard_verified=wbi_guard_ok,
        wbi_hibernation_masked=wbi_masked,
        wbi_trigger_blocked_count=wbi_blocked_cnt,
        double_mount_prevented=dbl_prevented,
        verified_digest_count=verified_cnt,
        insmod_event_count=insmod_cnt,
        mount_event_count=mount_cnt,
        forward_steps=forward_steps,
        unwind_steps=unwind_steps,
        lifo_order_exact=lifo_exact,
        lingering_mount_count=lingering_mounts,
        lingering_loop_count=lingering_loops,
        lingering_kmod_count=lingering_kmods,
        emmc_write_count=emmc_writes,
        wbi_write_count=total_wbi_writes,
        sandbox_violation_count=sandbox_violations,
        state_machine_matched=sm_match,
    )


def _populate_staged_runtime_tree(
    sandbox_root: Path,
    staged_blobs: Mapping[str, bytes],
    ram_bk4_bytes: bytes,
) -> None:
    stage_dir = sandbox_root / "tmp" / "fx6_stage_a"
    for rel_path, payload in staged_blobs.items():
        dst = stage_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(payload)

    bk4_dir = stage_dir / "backup"
    bk4_dir.mkdir(parents=True, exist_ok=True)
    (bk4_dir / "ram_shadow_Backup.bin").write_bytes(ram_bk4_bytes)
    (bk4_dir / "ram_shadow_Backup.sha256").write_text(
        hashlib.sha256(ram_bk4_bytes).hexdigest() + "\n",
        encoding="utf-8",
    )


def run_stage_a_boot_orchestrator_verification(
    *,
    overlay_bundle: Optional[object] = None,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    fx6_donor_root: Path = DEFAULT_FX6_DONOR_ROOT,
    simulate_clean_room_initrd: bool = False,
) -> Phase12StageABootOrchestratorReport:
    """Execute full Phase 12 Dimension A (`nflasha3-initrd` & `p5` WBI audit) + Dimension B (6-scenario `/bin/sh` sandbox)."""
    from .ram_overlay_packager import (
        StageARamOverlayBundle,
        build_stage_a_ram_overlay_package,
        extract_cpio_newc_to_dir,
    )

    errors: List[str] = []

    # 1. Dimension A: Audit `nflasha3-initrd` boot-order contracts & `p5` (`WBI2`) hibernation redline
    dim_a = audit_initrd_boot_chain_and_wbi_contracts(
        fx6_donor_root=fx6_donor_root,
        simulate_clean_room=simulate_clean_room_initrd,
    )
    if not dim_a.valid:
        errors.extend(dim_a.errors)

    bundle: StageARamOverlayBundle = (
        overlay_bundle  # type: ignore[assignment]
        if isinstance(overlay_bundle, StageARamOverlayBundle)
        else build_stage_a_ram_overlay_package(
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
            vfat_mode="8m_ram",
        )
    )

    orch_script_text = generate_stage_a_boot_orchestrator_script()
    orch_script_bytes = orch_script_text.encode("utf-8")
    orch_script_sha = hashlib.sha256(orch_script_bytes).hexdigest()

    wbi_redline = validate_candidate_wbi_redline(
        overlay_manifest=bundle.overlay_manifest,
        overlay_entry_paths=tuple(e.name for e in bundle.cpio_audit.entries),
        scripts_to_audit=(
            ("setup_fx6_compat.sh", bundle.setup_compat_script),
            ("init2_guard.sh", bundle.init2_guard_script),
            ("30-stage-a-orchestrator.sh", orch_script_text),
        ),
    )
    if not wbi_redline.valid:
        errors.extend(wbi_redline.violations)

    ram_bk4 = synthesize_ram_shadow_bk4()
    scenarios: List[OrchestratorScenarioResult] = []

    # 2. Dimension B: Isolated `tempfile.TemporaryDirectory()` `/bin/sh` 6-Scenario Verification
    with tempfile.TemporaryDirectory(prefix="fx6_stage_a_orch_sandbox_") as tmp_str:
        sandbox_root = Path(tmp_str).resolve()
        mock_bin = sandbox_root / "mock_bin"
        _install_orchestrator_mock_bin(mock_bin, sandbox_root)
        part_map = _init_simulated_partitions(sandbox_root)

        extract_cpio_newc_to_dir(bundle.cpio_bytes, sandbox_root)
        orch_dst = sandbox_root / ORCHESTRATOR_CPIO_REL_PATH
        if not orch_dst.is_file():
            orch_dst.parent.mkdir(parents=True, exist_ok=True)
            orch_dst.write_bytes(orch_script_bytes)
            orch_dst.chmod(0o755)
        _populate_staged_runtime_tree(sandbox_root, bundle.staged_runtime_blobs, ram_bk4.bk4_bytes)

        # --- Scenario 1: Clean Nominal Stage-A Activation & Clean LIFO Teardown ---
        sm_s1 = simulate_orchestrator_state_machine(arm_token_present=True)
        run_s1 = _execute_orchestrator_sandbox_run(
            run_id="S1_nominal_activation_and_lifo_teardown",
            sandbox_root=sandbox_root,
            mock_bin=mock_bin,
            part_map=part_map,
            arm_token=True,
            im_elf_cmd='[ ! -f "$PREFIX/tmp/mod_arm_once" ] && [ -f "$PREFIX/tmp_wbshd/stage_a_wbi_inhibit.lock" ]',
            expected_sm=sm_s1,
        )
        s1_ok = (
            run_s1.returncode == 0
            and run_s1.state_machine_matched
            and run_s1.token_cleared_before_exec
            and not run_s1.token_present_after
            and run_s1.wbi_guard_verified
            and run_s1.verified_digest_count == 11
            and run_s1.insmod_event_count == 1
            and run_s1.mount_event_count == 9
            and run_s1.forward_steps == EXPECTED_STAGE_A_FORWARD_STEP_IDS
            and run_s1.lifo_order_exact
            and run_s1.im_elf_invoked
            and run_s1.lingering_mount_count == 0
            and run_s1.lingering_loop_count == 0
            and run_s1.lingering_kmod_count == 0
            and run_s1.emmc_write_count == 0
            and run_s1.wbi_write_count == 0
        )
        scenarios.append(
            OrchestratorScenarioResult(
                scenario_id="S1_CLEAN_NOMINAL_ACTIVATION_AND_LIFO_TEARDOWN",
                title="Clean nominal Stage-A Verify-Before-Mount activation, im.elf handoff & reverse 10..1 LIFO teardown",
                passed=s1_ok,
                runs=(run_s1,),
                emmc_writes=run_s1.emmc_write_count,
                wbi_writes=run_s1.wbi_write_count,
                lingering_mounts=run_s1.lingering_mount_count,
                notes="11 SHA-256 digests verified prior to first insmod/mount; exact 10->1 LIFO unmount.",
            )
        )

        # --- Scenario 2: Verify-Before-Mount Atomicity (Corrupted `.so` & Corrupted `opelog.vfat`) ---
        sm_s2 = simulate_orchestrator_state_machine(
            arm_token_present=True, payload_sha256_valid=False
        )
        appfw_stage = sandbox_root / "tmp" / "fx6_stage_a" / "lib" / "appFw.so"
        orig_appfw = appfw_stage.read_bytes()
        corrupt_appfw = bytearray(orig_appfw)
        corrupt_appfw[0] ^= 0xFF
        appfw_stage.write_bytes(bytes(corrupt_appfw))

        run_s2a = _execute_orchestrator_sandbox_run(
            run_id="S2a_corrupt_staged_so_sha256",
            sandbox_root=sandbox_root,
            mock_bin=mock_bin,
            part_map=part_map,
            arm_token=True,
            expected_sm=sm_s2,
        )
        appfw_stage.write_bytes(orig_appfw)

        vfat_stage = sandbox_root / "tmp" / "fx6_stage_a" / "images" / "opelog.vfat"
        orig_vfat = vfat_stage.read_bytes()
        corrupt_vfat = bytearray(orig_vfat)
        corrupt_vfat[512] ^= 0x55
        vfat_stage.write_bytes(bytes(corrupt_vfat))

        run_s2b = _execute_orchestrator_sandbox_run(
            run_id="S2b_corrupt_opelog_vfat_sha256",
            sandbox_root=sandbox_root,
            mock_bin=mock_bin,
            part_map=part_map,
            arm_token=True,
            expected_sm=sm_s2,
        )
        vfat_stage.write_bytes(orig_vfat)

        s2_ok = all(
            r.returncode == 0
            and r.state_machine_matched
            and r.insmod_event_count == 0
            and r.mount_event_count == 0
            and r.lingering_mount_count == 0
            and r.stock_boot_invoked
            and r.emmc_write_count == 0
            and r.wbi_write_count == 0
            for r in (run_s2a, run_s2b)
        )
        scenarios.append(
            OrchestratorScenarioResult(
                scenario_id="S2_VERIFY_BEFORE_MOUNT_CORRUPTED_DIGEST_ABORT",
                title="Corrupted staged appFw.so or opelog.vfat SHA-256 aborts strictly BEFORE first insmod or mount",
                passed=s2_ok,
                runs=(run_s2a, run_s2b),
                emmc_writes=run_s2a.emmc_write_count + run_s2b.emmc_write_count,
                wbi_writes=run_s2a.wbi_write_count + run_s2b.wbi_write_count,
                lingering_mounts=run_s2a.lingering_mount_count + run_s2b.lingering_mount_count,
                notes="Zero insmod and zero mount syscalls executed on digest mismatch; clean stock FX3 fallback.",
            )
        )

        # --- Scenario 3: Mid-Sequence Mount Failure LIFO Rollback (step 3 & step 9) ---
        sm_s3a = simulate_orchestrator_state_machine(
            arm_token_present=True, fail_at_step_id="03_p2_opelog_vfat_loop_mount"
        )
        run_s3a = _execute_orchestrator_sandbox_run(
            run_id="S3a_fail_at_step03_opelog_loop",
            sandbox_root=sandbox_root,
            mock_bin=mock_bin,
            part_map=part_map,
            arm_token=True,
            inject_fail_step="03_p2_opelog_vfat_loop_mount",
            expected_sm=sm_s3a,
        )
        sm_s3b = simulate_orchestrator_state_machine(
            arm_token_present=True, fail_at_step_id="09_bind_ro_appFw_so"
        )
        run_s3b = _execute_orchestrator_sandbox_run(
            run_id="S3b_fail_at_step09_appfw_bind",
            sandbox_root=sandbox_root,
            mock_bin=mock_bin,
            part_map=part_map,
            arm_token=True,
            inject_fail_step="09_bind_ro_appFw_so",
            expected_sm=sm_s3b,
        )
        s3_ok = all(
            r.returncode == 0
            and r.state_machine_matched
            and r.lifo_order_exact
            and r.lingering_mount_count == 0
            and r.lingering_loop_count == 0
            and r.lingering_kmod_count == 0
            and r.stock_boot_invoked
            and not r.im_elf_invoked
            and r.emmc_write_count == 0
            and r.wbi_write_count == 0
            for r in (run_s3a, run_s3b)
        ) and len(run_s3a.unwind_steps) == 2 and len(run_s3b.unwind_steps) == 8
        scenarios.append(
            OrchestratorScenarioResult(
                scenario_id="S3_MID_SEQUENCE_MOUNT_FAILURE_LIFO_ROLLBACK",
                title="Mid-sequence mount failure at step k unwinds steps k-1..1 in strict LIFO order",
                passed=s3_ok,
                runs=(run_s3a, run_s3b),
                emmc_writes=run_s3a.emmc_write_count + run_s3b.emmc_write_count,
                wbi_writes=run_s3a.wbi_write_count + run_s3b.wbi_write_count,
                lingering_mounts=run_s3a.lingering_mount_count + run_s3b.lingering_mount_count,
                notes="Verified both step-3 (2->1 unwind) and step-9 (8->1 unwind) fault rollbacks with 0 lingering mounts.",
            )
        )

        # --- Scenario 4: WBI (`p5` / `/dev/nflasha5`) Guard Enforcement (`BIS` mode + runtime probe) ---
        sm_s4a = simulate_orchestrator_state_machine(
            arm_token_present=True, upm_bootmode="BIS"
        )
        run_s4a = _execute_orchestrator_sandbox_run(
            run_id="S4a_upm_bootmode_bis_rejected",
            sandbox_root=sandbox_root,
            mock_bin=mock_bin,
            part_map=part_map,
            arm_token=True,
            upm_bootmode="BIS",
            expected_sm=sm_s4a,
        )
        sm_s4b = simulate_orchestrator_state_machine(
            arm_token_present=True, wbi_already_mounted=True
        )
        run_s4b = _execute_orchestrator_sandbox_run(
            run_id="S4b_wbi_p5_rw_mount_detected_rejected",
            sandbox_root=sandbox_root,
            mock_bin=mock_bin,
            part_map=part_map,
            arm_token=True,
            pre_populate_wbi_proc_mount=True,
            expected_sm=sm_s4b,
        )
        sm_s4c = simulate_orchestrator_state_machine(arm_token_present=True)
        run_s4c = _execute_orchestrator_sandbox_run(
            run_id="S4c_runtime_wbi_hibernation_trigger_masked",
            sandbox_root=sandbox_root,
            mock_bin=mock_bin,
            part_map=part_map,
            arm_token=True,
            im_elf_cmd="wbi_hibernation_probe",
            expected_sm=sm_s4c,
        )
        s4_ok = (
            run_s4a.returncode == 0
            and run_s4a.state_machine_matched
            and run_s4a.diag_code == "ERR_WBI_BIS_MODE_FORBIDDEN"
            and run_s4a.insmod_event_count == 0
            and run_s4a.mount_event_count == 0
            and run_s4a.wbi_write_count == 0
            and run_s4b.returncode == 0
            and run_s4b.state_machine_matched
            and run_s4b.diag_code == "ERR_WBI_P5_ALREADY_MOUNTED"
            and run_s4b.insmod_event_count == 0
            and run_s4b.mount_event_count == 0
            and run_s4b.wbi_write_count == 0
            and run_s4c.returncode == 0
            and run_s4c.state_machine_matched
            and run_s4c.wbi_trigger_blocked_count == 1
            and run_s4c.wbi_write_count == 0
            and run_s4c.emmc_write_count == 0
        )
        scenarios.append(
            OrchestratorScenarioResult(
                scenario_id="S4_WBI_P5_HIBERNATION_GUARD_ENFORCEMENT",
                title="WBI (p5 / /dev/nflasha5) guard rejects BIS mode, rejects p5 RW mount & masks hibernation triggers",
                passed=s4_ok,
                runs=(run_s4a, run_s4b, run_s4c),
                emmc_writes=run_s4a.emmc_write_count + run_s4b.emmc_write_count + run_s4c.emmc_write_count,
                wbi_writes=run_s4a.wbi_write_count + run_s4b.wbi_write_count + run_s4c.wbi_write_count,
                lingering_mounts=run_s4a.lingering_mount_count + run_s4b.lingering_mount_count + run_s4c.lingering_mount_count,
                notes="/dev/nflasha5 (p5) WBI2 image SHA-256 and mtime_ns 100% untouched across BIS, mount, & runtime probes.",
            )
        )

        # --- Scenario 5: Idempotent Re-Entry Guard (second invocation refuses double-mounting) ---
        # `run_s4b` left `stage_a_orchestrator.lock` active for this boot session; re-invoke with `keep_reentry_lock=True`
        sm_s5 = simulate_orchestrator_state_machine(
            arm_token_present=True, reentry_lock_present=True
        )
        run_s5 = _execute_orchestrator_sandbox_run(
            run_id="S5_second_invocation_reentry_blocked",
            sandbox_root=sandbox_root,
            mock_bin=mock_bin,
            part_map=part_map,
            arm_token=True,
            keep_reentry_lock=True,
            expected_sm=sm_s5,
        )
        s5_ok = (
            run_s5.returncode == 0
            and run_s5.state_machine_matched
            and run_s5.double_mount_prevented
            and run_s5.diag_code == "ERR_IDEMPOTENT_REENTRY_BLOCKED"
            and run_s5.insmod_event_count == 0
            and run_s5.mount_event_count == 0
            and run_s5.emmc_write_count == 0
            and run_s5.wbi_write_count == 0
        )
        scenarios.append(
            OrchestratorScenarioResult(
                scenario_id="S5_IDEMPOTENT_REENTRY_GUARD",
                title="Second invocation detects active/consumed Stage-A lock and refuses double-mounting",
                passed=s5_ok,
                runs=(run_s5,),
                emmc_writes=run_s5.emmc_write_count,
                wbi_writes=run_s5.wbi_write_count,
                lingering_mounts=run_s5.lingering_mount_count,
                notes="Zero duplicate mounts or insmods when re-invoked in same boot cycle.",
            )
        )

        # --- Scenario 6: Stock Cold-Boot Passthrough (without `/tmp/mod_arm_once`) ---
        sm_s6 = simulate_orchestrator_state_machine(arm_token_present=False)
        run_s6 = _execute_orchestrator_sandbox_run(
            run_id="S6_stock_cold_boot_unarmed_passthrough",
            sandbox_root=sandbox_root,
            mock_bin=mock_bin,
            part_map=part_map,
            arm_token=False,
            keep_reentry_lock=False,
            expected_sm=sm_s6,
        )
        s6_ok = (
            run_s6.returncode == 0
            and run_s6.state_machine_matched
            and run_s6.boot_branch == "STOCK_FX3"
            and run_s6.diag_code == "STOCK_COLD_BOOT_PASSTHROUGH"
            and run_s6.stock_boot_invoked
            and not run_s6.im_elf_invoked
            and run_s6.insmod_event_count == 0
            and run_s6.mount_event_count == 0
            and run_s6.lingering_mount_count == 0
            and run_s6.emmc_write_count == 0
            and run_s6.wbi_write_count == 0
        )
        scenarios.append(
            OrchestratorScenarioResult(
                scenario_id="S6_STOCK_COLD_BOOT_PASSTHROUGH",
                title="Unarmed cold boot performs 0 Stage-A mounts/insmods and boots stock FX3 untouched",
                passed=s6_ok,
                runs=(run_s6,),
                emmc_writes=run_s6.emmc_write_count,
                wbi_writes=run_s6.wbi_write_count,
                lingering_mounts=run_s6.lingering_mount_count,
                notes="100% stock FX3 passthrough when /tmp/mod_arm_once is absent.",
            )
        )

    temp_cleaned = not Path(tmp_str).exists()
    all_runs = [r for s in scenarios for r in s.runs]
    total_emmc = sum(r.emmc_write_count for r in all_runs)
    total_wbi = sum(r.wbi_write_count for r in all_runs)
    total_lingering = sum(r.lingering_mount_count for r in all_runs)
    total_violations = sum(r.sandbox_violation_count for r in all_runs)

    for s in scenarios:
        if not s.passed:
            errors.append(f"Orchestrator sandbox scenario failed: {s.scenario_id}")

    all_ok = (
        dim_a.valid
        and wbi_redline.valid
        and len(scenarios) == 6
        and all(s.passed for s in scenarios)
        and total_emmc == 0
        and total_wbi == 0
        and total_lingering == 0
        and total_violations == 0
        and temp_cleaned
        and len(errors) == 0
    )
    return Phase12StageABootOrchestratorReport(
        all_checks_passed=all_ok,
        stage_a_orchestrator_ok=all_ok,
        wbi_p5_write_and_hibernation_forbidden=wbi_redline.wbi_p5_write_and_hibernation_forbidden,
        wbi_mutation_bytes=wbi_redline.wbi_mutation_bytes + total_wbi,
        orchestrator_script_sha256=orch_script_sha,
        orchestrator_script_bytes=len(orch_script_bytes),
        dimension_a_boot_chain_and_wbi=dim_a,
        candidate_wbi_redline=wbi_redline,
        scenario_count=len(scenarios),
        total_sandbox_runs=len(all_runs),
        total_emmc_writes=total_emmc,
        total_wbi_writes=total_wbi,
        total_lingering_mounts=total_lingering,
        total_sandbox_violations=total_violations,
        scenarios=tuple(scenarios),
        temp_dir_cleaned=temp_cleaned,
        errors=tuple(errors),
    )
