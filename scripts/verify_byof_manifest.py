#!/usr/bin/env python3
"""Deterministic Clean-Room & Live-Donor BYOF SHA-256 Manifest Auditor (`verify-byof`).

Parses and audits `docs/BYOF-REPRODUCTION.md` (both `# English Guide` and `# 简体中文指南`):
1. Schema & Syntax Verification:
   - Every table row in §1.1 (FX3), §1.2 (FX6), and §1.3 (Phase 2 Binary Adaptation Donors)
     carries a non-empty component path, a positive integer byte size, and a strict 64-hex
     lowercase SHA-256 digest.
2. Bilingual EN <-> ZH-CN Table Parity & Conflict Detection:
   - Zero duplicate conflicting digests within either language section.
   - Exact 1:1 `(subsection, component_path) -> (size_bytes, sha256)` parity across EN and ZH.
3. Cross-Package Code Constant Synchronization:
   - Cross-checks documented sizes and SHA-256 digests against pinned constants in
     `fx6_closure` (`patcher`, `p1_recovery_bridge_verifier`, `boot_selector_and_bank_verifier`,
     `storage_and_ram_budget_verifier`, `backup_mount_tolerance_verifier`,
     `cp_rtos_compatibility_verifier`, `kernel_dtb_compatibility_verifier`),
     `fx3_recovery.profiles`, `outputs/fx3-safety/readiness-20261025-msc.json`, and
     `outputs/fx3-vm-trial/vm-candidate-gpecap25-live700.json`.
4. Dual-Mode Donor Verification:
   - When canonical BYOF donor files are present under `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027`,
     streams and verifies live byte sizes and SHA-256 digests (`LOCAL_DONOR_VERIFIED`).
   - When run in a clean Git clone without proprietary Sony firmware (or `--simulate-clean-clone`),
     cleanly reports `CLEAN_ROOM_SCHEMA_VERIFIED` with exit code `0`.

Usage:
    PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/verify_byof_manifest.py [--json] [--simulate-clean-clone]
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOC_PATH = REPO_ROOT / "docs" / "BYOF-REPRODUCTION.md"
DEFAULT_DONOR_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027")

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

# Canonical donor file mapping relative to DEFAULT_DONOR_ROOT (zero `stage*` paths ever referenced).
# Keys are `(subsection_id, normalized_component_label)`.
CANONICAL_DONOR_RELPATHS: Dict[Tuple[str, str], str] = {
    # Section 1.1: FX3 Ver. 7.02 & 2.04/2.05 Recovery Engine
    ("1.1", "0800_appli/setting/cxd90057.dtb"): "FX6-donor-assessment-20261103/team/donor/tree/0800_appli/setting/cxd90057.dtb",
    ("1.1", "nflasha1/boot/cxd90057.dtb"): "input-20261028/fat-members/87abb2b72c3d373cf8f0779f8981a6e3f6780b54d08862d61a252248ebcf36ca-cxd90057.dtb",
    ("1.1", "0300_partconf/partinf.conf"): "input-20261028/original-update-engine/2.05/partinf.conf",
    ("1.1", "0750_nor_loader/loader_nor.bin"): "config-producer-20261029/original-files/loader_nor.bin",
    ("1.1", "pformat_config.txt"): "config-producer-20261029/original-files/pformat_config.txt",
    ("1.1", "LdrBkupList.txt"): "config-producer-20261029/original-files/LdrBkupList.txt",
    ("1.1", "nflasha8/tomco.txt"): "dmm-backup-20261029/tomco.txt",
    ("1.1", "updaterfs/cp/tomco.txt"): "package-20261028/updaterfs/cp/tomco.txt",
    ("1.1", "usr/bin/ud_send_lsi.elf (p1-initrd)"): "input-20261028/engine-rootfs/2.05/usr/bin/ud_send_lsi.elf",
    ("1.1", "original-update-engine/2.04/nflasha1"): "input-20261028/original-update-engine/2.04/nflasha1",
    ("1.1", "original-update-engine/2.05/nflasha1"): "input-20261028/original-update-engine/2.05/nflasha1",
    ("1.1", "libsdfileinputupdaterapi.so (p1)"): "input-20261028/engine-rootfs/2.05/usr/lib/libsdfileinputupdaterapi.so",
    ("1.1", "libupdatercorecommon.so (p1)"): "input-20261028/engine-rootfs/2.05/usr/lib/libupdatercorecommon.so",
    ("1.1", "usr/kmod/upm.ko"): "body-state-20261029/original-members/upm.ko",
    # Section 1.2: FX6 Ver. 6.01
    ("1.2", "nflasha3/vmlinux.bin"): "FX6-donor-assessment-20261103/team/donor/fat-files/nflasha3/vmlinux.bin",
    ("1.2", "nflasha3/initrd.img"): "FX6-donor-assessment-20261103/team/donor/fat-files/nflasha3/initrd.img",
    ("1.2", "0400_updater/dev/nflasha1"): "FX6-donor-assessment-20261103/team/donor/tree/0400_updater/dev/nflasha1",
    ("1.2", "nflasha1/boot/vmlinux.bin"): "FX6-donor-assessment-20261103/team/donor/fat-files/nflasha1/boot/vmlinux.bin",
    ("1.2", "nflasha1/boot/initrd.img"): "FX6-donor-assessment-20261103/team/donor/fat-files/nflasha1/boot/initrd.img",
    ("1.2", "nflasha1/boot/cxd90057.dtb"): "FX6-donor-assessment-20261103/team/donor/fat-files/nflasha1/boot/cxd90057.dtb",
    ("1.2", "0800_appli/setting/cxd90057.dtb"): "FX6-donor-assessment-20261103/team/donor/tree/0800_appli/setting/cxd90057.dtb",
    ("1.2", "0300_partconf/partinf.conf"): "FX6-donor-assessment-20261103/team/donor/tree/0300_partconf/partinf.conf",
    ("1.2", "0700_part_image/dev/nflasha3"): "FX6-donor-assessment-20261103/team/donor/tree/0700_part_image/dev/nflasha3",
    ("1.2", "0700_part_image/dev/nflasha5"): "FX6-donor-assessment-20261103/team/donor/tree/0700_part_image/dev/nflasha5",
    ("1.2", "0700_part_image/dev/nflasha8"): "FX6-donor-assessment-20261103/team/donor/tree/0700_part_image/dev/nflasha8",
    ("1.2", "0700_part_image/dev/nflasha15"): "FX6-donor-assessment-20261103/team/donor/tree/0700_part_image/dev/nflasha15",
    ("1.2", "0700_part_image/dev/nflasha23"): "FX6-donor-assessment-20261103/team/donor/tree/0700_part_image/dev/nflasha23",
    ("1.2", "nflasha8/tomco.txt"): "FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/tomco.txt",
    ("1.2", "nflasha8/cpapp-b.bin"): "FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin",
    ("1.2", "usr/bin/ud_send_lsi.elf (p15)"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/bin/ud_send_lsi.elf",
    ("1.2", "usr/bin/ud_send_lsi.elf (p1-initrd)"): "FX6-donor-assessment-20261103/team/donor/nested-files/nflasha1-initrd/usr/bin/ud_send_lsi.elf",
    ("1.2", "0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin"): "FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
    ("1.2", "usr/lib/libgrm.so"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libgrm.so",
    ("1.2", "nflasha3-initrd/sbin/init"): "FX6-donor-assessment-20261103/team/donor/nested-files/nflasha3-initrd/sbin/init",
    ("1.2", "nflasha3-initrd/sbin/init2"): "FX6-donor-assessment-20261103/team/donor/nested-files/nflasha3-initrd/sbin/init2",
    ("1.2", "nflasha3-initrd/sbin/initrc/insmod_drv1"): "FX6-donor-assessment-20261103/team/donor/nested-files/nflasha3-initrd/sbin/initrc/insmod_drv1",
    ("1.2", "nflasha3-initrd/sbin/initrc/insmod_drv2"): "FX6-donor-assessment-20261103/team/donor/nested-files/nflasha3-initrd/sbin/initrc/insmod_drv2",
    ("1.2", "usr/bin/bootin.elf (p15)"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/bin/bootin.elf",
    ("1.2", "usr/bin/im.elf (p15)"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/bin/im.elf",
    ("1.2", "bin/ud_wbi_drop.elf (updater)"): "FX6-donor-assessment-20261103/team/donor/nested-files/updater.img/bin/ud_wbi_drop.elf",
    ("1.2", "0800_appli/setting/kemco.txt"): "FX6-donor-assessment-20261103/team/donor/tree/0800_appli/setting/kemco.txt",
    ("1.2", "usr/kmod/emg.ko"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/kmod/emg.ko",
    ("1.2", "usr/lib/libgemini-grm.so"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libgemini-grm.so",
    ("1.2", "usr/lib/libuxengine.so"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libuxengine.so",
    ("1.2", "nflasha3-initrd/lib/libc-2.25.so"): "FX6-donor-assessment-20261103/team/donor/nested-files/nflasha3-initrd/lib/libc-2.25.so",
    ("1.2", "usr/lib/libstdc++.so.6.0.22"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libstdc++.so.6.0.22",
    ("1.2", "usr/lib/libgcc_s.so.1"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libgcc_s.so.1",
    # Section 1.3: All 7 Phase 2 Binary Adaptation Donors
    ("1.3", "usr/lib/libInfraSetupFile.so (FX6 6.01)"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraSetupFile.so",
    ("1.3", "usr/lib/libInfraMediaCommon.so (FX6 6.01)"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraMediaCommon.so",
    ("1.3", "usr/lib/libInfraMediaConfig.so (FX6 6.01)"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraMediaConfig.so",
    ("1.3", "usr/lib/libInfraAppRemoteBoard.so (FX6 6.01)"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraAppRemoteBoard.so",
    ("1.3", "usr/lib/appFw.so (FX6 6.01)"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
    ("1.3", "usr/lib/libfan.so (FX6 6.01)"): "FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libfan.so",
    ("1.3", "usr/kmod/upm.ko (FX3 7.02)"): "body-state-20261029/original-members/upm.ko",
}

REQUIRED_ENTRY_KEYS: Tuple[Tuple[str, str], ...] = (
    ("1.1", "nflasha3/vmlinux.bin"),
    ("1.1", "nflasha8/tomco.txt"),
    ("1.1", "updaterfs/cp/tomco.txt"),
    ("1.1", "nflasha8/cpapp-b.bin"),
    ("1.1", "usr/bin/ud_send_lsi.elf (p1-initrd)"),
    ("1.1", "FX3-CX95900_ALLLANG-Backup.bin"),
    ("1.1", "usr/kmod/upm.ko"),
    ("1.2", "0400_updater/dev/nflasha1"),
    ("1.2", "0700_part_image/dev/nflasha5"),
    ("1.2", "nflasha8/tomco.txt"),
    ("1.2", "nflasha8/cpapp-b.bin"),
    ("1.2", "usr/bin/ud_send_lsi.elf (p15)"),
    ("1.2", "usr/bin/ud_send_lsi.elf (p1-initrd)"),
    ("1.2", "0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin"),
    ("1.2", "nflasha3-initrd/sbin/init"),
    ("1.2", "nflasha3-initrd/sbin/init2"),
    ("1.2", "nflasha3-initrd/sbin/initrc/insmod_drv1"),
    ("1.2", "nflasha3-initrd/sbin/initrc/insmod_drv2"),
    ("1.2", "usr/bin/bootin.elf (p15)"),
    ("1.2", "usr/bin/im.elf (p15)"),
    ("1.2", "bin/ud_wbi_drop.elf (updater)"),
    ("1.2", "0800_appli/setting/kemco.txt"),
    ("1.2", "usr/kmod/emg.ko"),
    ("1.2", "usr/lib/libgemini-grm.so"),
    ("1.2", "usr/lib/libuxengine.so"),
    ("1.2", "nflasha3-initrd/lib/libc-2.25.so"),
    ("1.2", "usr/lib/libstdc++.so.6.0.22"),
    ("1.2", "usr/lib/libgcc_s.so.1"),
    ("1.3", "usr/lib/libInfraSetupFile.so (FX6 6.01)"),
    ("1.3", "usr/lib/libInfraMediaCommon.so (FX6 6.01)"),
    ("1.3", "usr/lib/libInfraMediaConfig.so (FX6 6.01)"),
    ("1.3", "usr/lib/libInfraAppRemoteBoard.so (FX6 6.01)"),
    ("1.3", "usr/lib/appFw.so (FX6 6.01)"),
    ("1.3", "usr/lib/libfan.so (FX6 6.01)"),
    ("1.3", "usr/kmod/upm.ko (FX3 7.02)"),
)


@dataclass(frozen=True)
class ByofManifestRow:
    lang: str
    subsection: str
    line_no: int
    component_path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class ByofVerificationReport:
    verification_mode: str
    all_checks_passed: bool
    doc_path: str
    en_entry_count: int
    zh_entry_count: int
    en_zh_parity_ok: bool
    code_constants_checked: int
    code_constants_ok: bool
    donor_root_present: bool
    live_donor_files_verified: int
    live_donor_unique_blobs_hashed: int
    zero_stage_reference_ok: bool
    elapsed_seconds: float
    errors: Tuple[str, ...]


def _strip_ticks(cell: str) -> str:
    cleaned = cell.strip().replace("`", "")
    return re.sub(r"\s+", " ", cleaned).strip()


def _stream_sha256_and_size(path: Path) -> Tuple[int, str]:
    h = hashlib.sha256()
    total = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(8 * 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            h.update(chunk)
    return total, h.hexdigest()


def parse_byof_markdown(
    markdown_text: str,
) -> Tuple[Tuple[ByofManifestRow, ...], Tuple[str, ...]]:
    """Parse all `(lang, subsection, component_path, size_bytes, sha256)` rows in BYOF-REPRODUCTION.md."""
    rows: List[ByofManifestRow] = []
    errors: List[str] = []

    current_lang: Optional[str] = None
    current_sub: Optional[str] = None
    in_fence = False

    for line_no, raw_line in enumerate(markdown_text.splitlines(), start=1):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if stripped == "# English Guide":
            current_lang = "en"
            current_sub = None
            continue
        if stripped == "# 简体中文指南":
            current_lang = "zh"
            current_sub = None
            continue

        if stripped.startswith("## ") and not stripped.startswith("### "):
            # Leaving section 1 resets subsection tracking
            if not stripped.startswith("## 1."):
                current_sub = None
            continue

        sub_m = re.match(r"^###\s+(1\.[123])\b", stripped)
        if sub_m:
            current_sub = sub_m.group(1)
            continue

        if current_lang is None or current_sub is None:
            continue
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 3:
            continue

        # Skip header and alignment separator rows
        if all(set(c) <= {":", "-", " "} and "-" in c for c in cells[:3]):
            continue
        first_clean = _strip_ticks(cells[0]).lower()
        if first_clean in ("component / path", "组件 / 路径"):
            continue

        comp_path = _strip_ticks(cells[0])
        size_raw = _strip_ticks(cells[1]).replace(",", "")
        sha_raw = _strip_ticks(cells[2])

        if not comp_path:
            errors.append(f"Line {line_no}: empty Component / Path cell")
            continue

        if not size_raw.isdigit() or int(size_raw) <= 0:
            errors.append(
                f"Line {line_no} ({current_lang} §{current_sub} `{comp_path}`): "
                f"invalid byte size `{cells[1]}` (expected positive integer)"
            )
            size_val = -1
        else:
            size_val = int(size_raw)

        if not HEX64_RE.fullmatch(sha_raw):
            errors.append(
                f"Line {line_no} ({current_lang} §{current_sub} `{comp_path}`): "
                f"invalid SHA-256 digest `{sha_raw}` (expected 64 lowercase hex chars)"
            )

        rows.append(
            ByofManifestRow(
                lang=current_lang,
                subsection=current_sub,
                line_no=line_no,
                component_path=comp_path,
                size_bytes=size_val,
                sha256=sha_raw,
            )
        )

    return tuple(rows), tuple(errors)


def _load_expected_code_constants(repo_root: Path) -> Tuple[Dict[Tuple[str, str], Tuple[Optional[int], str, str]], List[str]]:
    """Collect pinned `(size_bytes, sha256, provenance)` constants from `fx6_closure`, `fx3_recovery`, and tracked JSONs."""
    errors: List[str] = []
    for rel in ("outputs/fx3-safety", "outputs/fx6-on-fx3-closure", "outputs/fx3-recovery-adapter"):
        candidate = str((repo_root / rel).resolve())
        if candidate not in sys.path:
            sys.path.insert(0, candidate)

    from fx3_recovery import profiles as fx3_profiles
    from fx6_closure import (
        backup_mount_tolerance_verifier,
        boot_selector_and_bank_verifier,
        cp_rtos_compatibility_verifier,
        kernel_dtb_compatibility_verifier,
        kmod_and_userland_abi_verifier,
        p1_recovery_bridge_verifier,
        patcher,
        stage_a_boot_orchestrator,
        storage_and_ram_budget_verifier,
    )

    expected: Dict[Tuple[str, str], Tuple[Optional[int], str, str]] = {}

    # 1. All 7 Phase 2 binary adaptation targets (`patcher.ALL_PHASE2_TARGET_SPECS`)
    spec_label_by_lib = {
        "libInfraSetupFile.so": "usr/lib/libInfraSetupFile.so (FX6 6.01)",
        "libInfraMediaCommon.so": "usr/lib/libInfraMediaCommon.so (FX6 6.01)",
        "libInfraMediaConfig.so": "usr/lib/libInfraMediaConfig.so (FX6 6.01)",
        "libInfraAppRemoteBoard.so": "usr/lib/libInfraAppRemoteBoard.so (FX6 6.01)",
        "appFw.so": "usr/lib/appFw.so (FX6 6.01)",
        "libfan.so": "usr/lib/libfan.so (FX6 6.01)",
        "upm.ko": "usr/kmod/upm.ko (FX3 7.02)",
    }
    for spec in patcher.ALL_PHASE2_TARGET_SPECS:
        lbl = spec_label_by_lib.get(spec.library_name)
        if lbl is None:
            errors.append(f"Unmapped Phase 2 target library `{spec.library_name}` in patcher.ALL_PHASE2_TARGET_SPECS")
            continue
        expected[("1.3", lbl)] = (None, spec.donor_sha256, f"fx6_closure.patcher:{spec.spec_id}")

    # Also cross-check FX3 `usr/kmod/upm.ko` in §1.1
    upm_spec = next(s for s in patcher.ALL_PHASE2_TARGET_SPECS if s.library_name == "upm.ko")
    expected[("1.1", "usr/kmod/upm.ko")] = (None, upm_spec.donor_sha256, "fx6_closure.patcher:P9_upm_ko")

    # 2. `fx3_recovery.profiles` reference images & updater libraries
    ref_sha_by_label = {label: sha for sha, label in fx3_profiles.REFERENCE_IMAGES.items()}
    expected[("1.1", "original-update-engine/2.04/nflasha1")] = (
        19_377_152,
        ref_sha_by_label["FX3 official 2.04 P1 payload"],
        "fx3_recovery.profiles.REFERENCE_IMAGES[2.04]",
    )
    expected[("1.1", "original-update-engine/2.05/nflasha1")] = (
        19_377_152,
        ref_sha_by_label["FX3 official 2.05 P1 payload"],
        "fx3_recovery.profiles.REFERENCE_IMAGES[2.05]",
    )
    lib_sd = fx3_profiles.LIBRARIES["/usr/lib/libsdfileinputupdaterapi.so"]
    lib_core = fx3_profiles.LIBRARIES["/usr/lib/libupdatercorecommon.so"]
    expected[("1.1", "libsdfileinputupdaterapi.so (p1)")] = (
        int(lib_sd["bytes"]),
        str(lib_sd["sha256"]),
        "fx3_recovery.profiles.LIBRARIES[libsdfileinputupdaterapi.so]",
    )
    expected[("1.1", "libupdatercorecommon.so (p1)")] = (
        int(lib_core["bytes"]),
        str(lib_core["sha256"]),
        "fx3_recovery.profiles.LIBRARIES[libupdatercorecommon.so]",
    )

    # 3. `p1_recovery_bridge_verifier` + `boot_selector_and_bank_verifier` + `storage_and_ram_budget_verifier`
    expected[("1.2", "0400_updater/dev/nflasha1")] = (
        p1_recovery_bridge_verifier.PINNED_FX6_P1_IMAGE_BYTES,
        p1_recovery_bridge_verifier.PINNED_FX6_P1_IMAGE_SHA256,
        "fx6_closure.p1_recovery_bridge_verifier.PINNED_FX6_P1_IMAGE",
    )
    expected[("1.2", "nflasha1/boot/initrd.img")] = (
        p1_recovery_bridge_verifier.PINNED_FX6_P1_INITRD_BYTES,
        p1_recovery_bridge_verifier.PINNED_FX6_P1_INITRD_SHA256,
        "fx6_closure.p1_recovery_bridge_verifier.PINNED_FX6_P1_INITRD",
    )
    expected[("1.2", "nflasha1/boot/vmlinux.bin")] = (
        p1_recovery_bridge_verifier.PINNED_FX6_P1_VMLINUX_BYTES,
        p1_recovery_bridge_verifier.PINNED_FX6_P1_VMLINUX_SHA256,
        "fx6_closure.p1_recovery_bridge_verifier.PINNED_FX6_P1_VMLINUX",
    )
    expected[("1.1", "0750_nor_loader/loader_nor.bin")] = (
        None,
        boot_selector_and_bank_verifier.PINNED_LOADER_NOR_SHA256,
        "fx6_closure.boot_selector_and_bank_verifier.PINNED_LOADER_NOR_SHA256",
    )
    expected[("1.1", "pformat_config.txt")] = (
        None,
        boot_selector_and_bank_verifier.PINNED_PFORMAT_CONFIG_SHA256,
        "fx6_closure.boot_selector_and_bank_verifier.PINNED_PFORMAT_CONFIG_SHA256",
    )
    expected[("1.1", "LdrBkupList.txt")] = (
        None,
        boot_selector_and_bank_verifier.PINNED_LDR_BKUP_LIST_SHA256,
        "fx6_closure.boot_selector_and_bank_verifier.PINNED_LDR_BKUP_LIST_SHA256",
    )
    expected[("1.1", "usr/bin/ud_send_lsi.elf (p1-initrd)")] = (
        10_248,
        boot_selector_and_bank_verifier.PINNED_P1_AND_FX3_UD_SEND_LSI_SHA256,
        "fx6_closure.boot_selector_and_bank_verifier.PINNED_P1_AND_FX3_UD_SEND_LSI_SHA256",
    )
    expected[("1.2", "usr/bin/ud_send_lsi.elf (p1-initrd)")] = (
        10_248,
        boot_selector_and_bank_verifier.PINNED_P1_AND_FX3_UD_SEND_LSI_SHA256,
        "fx6_closure.boot_selector_and_bank_verifier.PINNED_P1_AND_FX3_UD_SEND_LSI_SHA256",
    )
    expected[("1.2", "usr/bin/ud_send_lsi.elf (p15)")] = (
        10_248,
        boot_selector_and_bank_verifier.PINNED_FX6_P15_UD_SEND_LSI_SHA256,
        "fx6_closure.boot_selector_and_bank_verifier.PINNED_FX6_P15_UD_SEND_LSI_SHA256",
    )
    expected[("1.1", "0300_partconf/partinf.conf")] = (
        None,
        storage_and_ram_budget_verifier.PINNED_FX3_PARTINF_SHA256,
        "fx6_closure.storage_and_ram_budget_verifier.PINNED_FX3_PARTINF_SHA256",
    )
    expected[("1.2", "0300_partconf/partinf.conf")] = (
        None,
        storage_and_ram_budget_verifier.PINNED_FX6_PARTINF_SHA256,
        "fx6_closure.storage_and_ram_budget_verifier.PINNED_FX6_PARTINF_SHA256",
    )
    expected[("1.1", "nflasha1/boot/cxd90057.dtb")] = (
        17_131,
        kernel_dtb_compatibility_verifier.PINNED_CXD90057_DTB_SHA256,
        "fx6_closure.kernel_dtb_compatibility_verifier.PINNED_CXD90057_DTB_SHA256",
    )
    expected[("1.2", "nflasha1/boot/cxd90057.dtb")] = (
        17_131,
        kernel_dtb_compatibility_verifier.PINNED_CXD90057_DTB_SHA256,
        "fx6_closure.kernel_dtb_compatibility_verifier.PINNED_CXD90057_DTB_SHA256",
    )
    expected[("1.1", "FX3-CX95900_ALLLANG-Backup.bin")] = (
        None,
        backup_mount_tolerance_verifier.PINNED_FX3_SEED_BK4_SHA256,
        "fx6_closure.backup_mount_tolerance_verifier.PINNED_FX3_SEED_BK4_SHA256",
    )
    expected[("1.2", "0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin")] = (
        None,
        backup_mount_tolerance_verifier.PINNED_FX6_TEMPLATE_BK4_SHA256,
        "fx6_closure.backup_mount_tolerance_verifier.PINNED_FX6_TEMPLATE_BK4_SHA256",
    )
    expected[("1.1", "nflasha8/cpapp-b.bin")] = (
        cp_rtos_compatibility_verifier.EXPECTED_FX3_CP_REF_BYTES,
        cp_rtos_compatibility_verifier.EXPECTED_FX3_CP_REF_SHA256,
        "fx6_closure.cp_rtos_compatibility_verifier.EXPECTED_FX3_CP_REF",
    )
    fx6_cpapp_sz, fx6_cpapp_sha = cp_rtos_compatibility_verifier.EXPECTED_FX6_NFLASHA8_ARTIFACTS["cpapp-b.bin"]
    fx6_tomco_sz, fx6_tomco_sha = cp_rtos_compatibility_verifier.EXPECTED_FX6_NFLASHA8_ARTIFACTS["tomco.txt"]
    expected[("1.2", "nflasha8/cpapp-b.bin")] = (
        fx6_cpapp_sz,
        fx6_cpapp_sha,
        "fx6_closure.cp_rtos_compatibility_verifier.EXPECTED_FX6_NFLASHA8_ARTIFACTS[cpapp-b.bin]",
    )
    expected[("1.2", "nflasha8/tomco.txt")] = (
        fx6_tomco_sz,
        fx6_tomco_sha,
        "fx6_closure.cp_rtos_compatibility_verifier.EXPECTED_FX6_NFLASHA8_ARTIFACTS[tomco.txt]",
    )

    # 3b. Phase 12 `stage_a_boot_orchestrator` pinned `nflasha3-initrd`, `p15`, and WBI (`p5`) digests
    expected[("1.2", "0700_part_image/dev/nflasha5")] = (
        stage_a_boot_orchestrator.PINNED_FX6_WBI_NFLASH5_BYTES,
        stage_a_boot_orchestrator.PINNED_FX6_WBI_NFLASH5_SHA256,
        "fx6_closure.stage_a_boot_orchestrator.PINNED_FX6_WBI_NFLASH5",
    )
    initrd_map = {aid: (sz, sha) for aid, _rel, sz, sha in stage_a_boot_orchestrator.PINNED_INITRD_AND_BOOT_ARTIFACTS}
    phase12_byof_map = {
        "nflasha3-initrd/sbin/init": "fx6_initrd_sbin_init",
        "nflasha3-initrd/sbin/init2": "fx6_initrd_sbin_init2",
        "nflasha3-initrd/sbin/initrc/insmod_drv1": "fx6_initrd_insmod_drv1",
        "nflasha3-initrd/sbin/initrc/insmod_drv2": "fx6_initrd_insmod_drv2",
        "usr/bin/bootin.elf (p15)": "fx6_p15_bootin_elf",
        "usr/bin/im.elf (p15)": "fx6_p15_im_elf",
        "bin/ud_wbi_drop.elf (updater)": "fx6_updater_ud_wbi_drop_elf",
        "0800_appli/setting/kemco.txt": "fx6_appli_setting_kemco_txt",
    }
    for doc_lbl, aid in phase12_byof_map.items():
        sz, sha = initrd_map[aid]
        expected[("1.2", doc_lbl)] = (
            sz,
            sha,
            f"fx6_closure.stage_a_boot_orchestrator.PINNED_INITRD_AND_BOOT_ARTIFACTS[{aid}]",
        )

    # 3c. Phase 14 `kmod_and_userland_abi_verifier` pinned `.ko` & runtime/UI `.so` digests
    phase14_constants = (
        (
            "usr/kmod/emg.ko",
            kmod_and_userland_abi_verifier.PINNED_FX6_EMG_KO_BYTES,
            kmod_and_userland_abi_verifier.PINNED_FX6_EMG_KO_SHA256,
            "fx6_closure.kmod_and_userland_abi_verifier.PINNED_FX6_EMG_KO",
        ),
        (
            "usr/lib/libgemini-grm.so",
            kmod_and_userland_abi_verifier.PINNED_FX6_LIBGEMINI_GRM_BYTES,
            kmod_and_userland_abi_verifier.PINNED_FX6_LIBGEMINI_GRM_SHA256,
            "fx6_closure.kmod_and_userland_abi_verifier.PINNED_FX6_LIBGEMINI_GRM",
        ),
        (
            "usr/lib/libuxengine.so",
            kmod_and_userland_abi_verifier.PINNED_FX6_LIBUXENGINE_BYTES,
            kmod_and_userland_abi_verifier.PINNED_FX6_LIBUXENGINE_SHA256,
            "fx6_closure.kmod_and_userland_abi_verifier.PINNED_FX6_LIBUXENGINE",
        ),
        (
            "nflasha3-initrd/lib/libc-2.25.so",
            kmod_and_userland_abi_verifier.PINNED_FX6_INITRD_LIBC_BYTES,
            kmod_and_userland_abi_verifier.PINNED_FX6_INITRD_LIBC_SHA256,
            "fx6_closure.kmod_and_userland_abi_verifier.PINNED_FX6_INITRD_LIBC",
        ),
        (
            "usr/lib/libstdc++.so.6.0.22",
            kmod_and_userland_abi_verifier.PINNED_FX6_LIBSTDCXX_BYTES,
            kmod_and_userland_abi_verifier.PINNED_FX6_LIBSTDCXX_SHA256,
            "fx6_closure.kmod_and_userland_abi_verifier.PINNED_FX6_LIBSTDCXX",
        ),
        (
            "usr/lib/libgcc_s.so.1",
            kmod_and_userland_abi_verifier.PINNED_SHARED_LIBGCC_S_BYTES,
            kmod_and_userland_abi_verifier.PINNED_SHARED_LIBGCC_S_SHA256,
            "fx6_closure.kmod_and_userland_abi_verifier.PINNED_SHARED_LIBGCC_S",
        ),
    )
    for doc_lbl, sz, sha, prov in phase14_constants:
        expected[("1.2", doc_lbl)] = (sz, sha, prov)

    # 4. Tracked JSON manifest cross-check for FX3 `nflasha3/vmlinux.bin`
    vm_manifest_path = repo_root / "outputs" / "fx3-vm-trial" / "vm-candidate-gpecap25-live700.json"
    if vm_manifest_path.is_file():
        vm_json = json.loads(vm_manifest_path.read_text(encoding="utf-8"))
        kern = vm_json.get("kernel", {})
        if isinstance(kern, dict) and "sha256" in kern and "bytes" in kern:
            expected[("1.1", "nflasha3/vmlinux.bin")] = (
                int(kern["bytes"]),
                str(kern["sha256"]),
                "outputs/fx3-vm-trial/vm-candidate-gpecap25-live700.json:kernel",
            )

    return expected, errors


def verify_byof_manifest(
    doc_path: Path = DEFAULT_DOC_PATH,
    *,
    repo_root: Path = REPO_ROOT,
    donor_root: Optional[Path] = DEFAULT_DONOR_ROOT,
    simulate_clean_clone: bool = False,
    schema_only: bool = False,
) -> ByofVerificationReport:
    """Audit `docs/BYOF-REPRODUCTION.md` schema, EN/ZH parity, code constants, and optional live donor files."""
    t0 = time.monotonic()
    errors: List[str] = []

    if not doc_path.is_file():
        return ByofVerificationReport(
            verification_mode="FAILED_MISSING_DOC",
            all_checks_passed=False,
            doc_path=str(doc_path),
            en_entry_count=0,
            zh_entry_count=0,
            en_zh_parity_ok=False,
            code_constants_checked=0,
            code_constants_ok=False,
            donor_root_present=False,
            live_donor_files_verified=0,
            live_donor_unique_blobs_hashed=0,
            zero_stage_reference_ok=False,
            elapsed_seconds=round(time.monotonic() - t0, 4),
            errors=(f"BYOF reproduction guide not found: {doc_path}",),
        )

    markdown_text = doc_path.read_text(encoding="utf-8")

    # Clean-room guard: ensure zero `stage<digits>` work-folder references in `docs/BYOF-REPRODUCTION.md`
    stage_refs = re.findall(r"\bstage\d+[A-Za-z0-9_-]*", markdown_text, flags=re.IGNORECASE)
    zero_stage_ok = len(stage_refs) == 0
    if not zero_stage_ok:
        errors.append(
            f"Forbidden `stage*` work-folder reference(s) in {doc_path.name}: {sorted(set(stage_refs))}"
        )

    for (_sub, _lbl), rel_str in CANONICAL_DONOR_RELPATHS.items():
        if re.search(r"\bstage\d*", rel_str, flags=re.IGNORECASE):
            zero_stage_ok = False
            errors.append(f"Forbidden `stage*` path in CANONICAL_DONOR_RELPATHS: {rel_str}")

    parsed_rows, parse_errs = parse_byof_markdown(markdown_text)
    errors.extend(parse_errs)

    en_map: Dict[Tuple[str, str], ByofManifestRow] = {}
    zh_map: Dict[Tuple[str, str], ByofManifestRow] = {}

    for row in parsed_rows:
        target = en_map if row.lang == "en" else zh_map
        key = (row.subsection, row.component_path)
        if key in target:
            prev = target[key]
            if prev.sha256 != row.sha256 or prev.size_bytes != row.size_bytes:
                errors.append(
                    f"Duplicate inconsistent entry in {row.lang.upper()} §{row.subsection} `{row.component_path}` "
                    f"(lines {prev.line_no} vs {row.line_no})"
                )
            else:
                errors.append(
                    f"Duplicate redundant entry in {row.lang.upper()} §{row.subsection} `{row.component_path}` "
                    f"(lines {prev.line_no} vs {row.line_no})"
                )
        else:
            target[key] = row

    if len(en_map) == 0 or len(zh_map) == 0:
        errors.append(
            f"Expected non-empty EN and ZH digest tables (got en={len(en_map)}, zh={len(zh_map)})"
        )

    # Check EN <-> ZH exact 1:1 parity
    parity_errors: List[str] = []
    only_en = sorted(set(en_map) - set(zh_map))
    only_zh = sorted(set(zh_map) - set(en_map))
    for sub, comp in only_en:
        parity_errors.append(f"Entry present in EN §{sub} `{comp}` but missing from ZH table")
    for sub, comp in only_zh:
        parity_errors.append(f"Entry present in ZH §{sub} `{comp}` but missing from EN table")

    for key in sorted(set(en_map) & set(zh_map)):
        en_r = en_map[key]
        zh_r = zh_map[key]
        if en_r.size_bytes != zh_r.size_bytes or en_r.sha256 != zh_r.sha256:
            parity_errors.append(
                f"EN/ZH mismatch on §{key[0]} `{key[1]}`: "
                f"EN=({en_r.size_bytes}, {en_r.sha256}) vs ZH=({zh_r.size_bytes}, {zh_r.sha256})"
            )

    en_zh_parity_ok = len(parity_errors) == 0 and len(en_map) > 0
    errors.extend(parity_errors)

    # Check required Phase 11/12/14 deliverables coverage
    for req_key in REQUIRED_ENTRY_KEYS:
        if req_key not in en_map:
            errors.append(f"Missing required BYOF manifest entry §{req_key[0]} `{req_key[1]}`")

    # Cross-check against pinned code constants in `fx6_closure` / `fx3_recovery`
    expected_constants, const_load_errs = _load_expected_code_constants(repo_root)
    errors.extend(const_load_errs)
    const_mismatch_count = 0
    for key, (exp_size, exp_sha, provenance) in sorted(expected_constants.items()):
        if key not in en_map:
            const_mismatch_count += 1
            errors.append(
                f"Code constant `{provenance}` expects §{key[0]} `{key[1]}`, which is absent from {doc_path.name}"
            )
            continue
        row = en_map[key]
        if row.sha256 != exp_sha:
            const_mismatch_count += 1
            errors.append(
                f"SHA-256 drift on §{key[0]} `{key[1]}` vs `{provenance}`: "
                f"doc={row.sha256} code={exp_sha}"
            )
        if exp_size is not None and row.size_bytes != exp_size:
            const_mismatch_count += 1
            errors.append(
                f"Size drift on §{key[0]} `{key[1]}` vs `{provenance}`: "
                f"doc={row.size_bytes} code={exp_size}"
            )

    code_constants_ok = len(const_load_errs) == 0 and const_mismatch_count == 0

    # Live donor file verification when canonical donor directory exists (unless clean-room mode is forced)
    env_force_clean_room = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    force_clean = simulate_clean_clone or schema_only or env_force_clean_room
    effective_donor_root = None if force_clean else donor_root
    donor_present = bool(effective_donor_root is not None and effective_donor_root.is_dir())
    live_verified = 0
    digest_cache: Dict[Path, Tuple[int, str]] = {}

    if donor_present:
        assert effective_donor_root is not None
        for key, rel_str in sorted(CANONICAL_DONOR_RELPATHS.items()):
            if key not in en_map:
                continue
            row = en_map[key]
            donor_file = effective_donor_root / rel_str
            if not donor_file.is_file() or donor_file.is_symlink():
                errors.append(
                    f"Missing or symlinked canonical donor file for §{key[0]} `{key[1]}`: {donor_file}"
                )
                continue
            resolved = donor_file.resolve()
            if resolved not in digest_cache:
                digest_cache[resolved] = _stream_sha256_and_size(resolved)
            live_size, live_sha = digest_cache[resolved]
            if live_size != row.size_bytes:
                errors.append(
                    f"Live donor size mismatch on §{key[0]} `{key[1]}` ({donor_file}): "
                    f"live={live_size} doc={row.size_bytes}"
                )
                continue
            if live_sha != row.sha256:
                errors.append(
                    f"Live donor SHA-256 mismatch on §{key[0]} `{key[1]}` ({donor_file}): "
                    f"live={live_sha} doc={row.sha256}"
                )
                continue
            live_verified += 1

        mode = "LOCAL_DONOR_VERIFIED"
    else:
        mode = "CLEAN_ROOM_SCHEMA_VERIFIED"

    all_ok = (
        len(errors) == 0
        and en_zh_parity_ok
        and code_constants_ok
        and zero_stage_ok
        and (not donor_present or live_verified == len(CANONICAL_DONOR_RELPATHS))
    )

    return ByofVerificationReport(
        verification_mode=mode if all_ok else f"FAILED_{mode}",
        all_checks_passed=all_ok,
        doc_path=str(doc_path),
        en_entry_count=len(en_map),
        zh_entry_count=len(zh_map),
        en_zh_parity_ok=en_zh_parity_ok,
        code_constants_checked=len(expected_constants),
        code_constants_ok=code_constants_ok,
        donor_root_present=donor_present,
        live_donor_files_verified=live_verified,
        live_donor_unique_blobs_hashed=len(digest_cache),
        zero_stage_reference_ok=zero_stage_ok,
        elapsed_seconds=round(time.monotonic() - t0, 4),
        errors=tuple(errors),
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify_byof_manifest.py",
        description="Verify docs/BYOF-REPRODUCTION.md SHA-256 & byte-size manifest against code constants and optional local BYOF donor files.",
    )
    parser.add_argument(
        "--doc",
        type=Path,
        default=DEFAULT_DOC_PATH,
        help="Path to BYOF-REPRODUCTION.md",
    )
    parser.add_argument(
        "--donor-root",
        type=Path,
        default=DEFAULT_DONOR_ROOT,
        help="Canonical local BYOF donor root directory",
    )
    parser.add_argument(
        "--simulate-clean-clone",
        action="store_true",
        help="Simulate clean Git clone without local Sony firmware (verifies schema, EN/ZH parity, and code constants)",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Skip live large-file hashing while still verifying EN/ZH parity and code constants",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Emit structured JSON report to stdout",
    )
    args = parser.parse_args(argv)

    rep = verify_byof_manifest(
        doc_path=args.doc,
        repo_root=REPO_ROOT,
        donor_root=args.donor_root,
        simulate_clean_clone=args.simulate_clean_clone,
        schema_only=args.schema_only,
    )

    if args.emit_json:
        sys.stdout.write(json.dumps(asdict(rep), indent=2) + "\n")
    else:
        sys.stdout.write(
            f"[verify-byof] {rep.verification_mode} | "
            f"en={rep.en_entry_count} zh={rep.zh_entry_count} "
            f"parity_ok={rep.en_zh_parity_ok} "
            f"code_constants={rep.code_constants_checked} ({'OK' if rep.code_constants_ok else 'FAIL'}) "
            f"live_donors={rep.live_donor_files_verified} ({rep.live_donor_unique_blobs_hashed} blobs) "
            f"in {rep.elapsed_seconds:.2f}s\n"
        )
        for err in rep.errors:
            sys.stdout.write(f"  ! {err}\n")

    return 0 if rep.all_checks_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
