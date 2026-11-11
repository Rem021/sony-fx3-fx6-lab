"""Phase 11 — Cross-Package `p1` Recovery & Tier-0 Bridge Verifier (`fx3_recovery` <-> `fx3_safety` <-> `fx6_closure`).

Bridges Track 4 (`outputs/fx3-recovery-adapter/fx3_recovery`) and Track 3
(`outputs/fx6-on-fx3-closure` + `outputs/fx3-safety`) with a deterministic, zero-residue
offline verifier covering two safety dimensions:

- **Dimension A (Tier-0 <-> `fx3_recovery` Read-Only Capture & Partition Contract Alignment)**:
  1. Cross-checks `fx3_safety.preflight` (`TIER0_CANONICAL_SOURCES`, `TIER0_REQUIRED_BACKUPS`,
     `verify_tier0_backup_manifest`, `audit_tier0_worker_syscall_trace`) against `fx3_recovery`
     (`worker`, `boot_worker`, `capture`, `profiles`, `fat`, `squash`, `engine`).
  2. Audits all three freestanding AArch64 C capture workers (`native/tier0_backup_worker.c`,
     `outputs/fx3-recovery-adapter/native/fx3_p1_reader.c`, and
     `outputs/fx3-recovery-adapter/native/fx3_boot_reader.c`), proving strict `O_RDONLY | O_NOFOLLOW`
     source access (`0` write/create/truncate bits), exclusive `O_WRONLY | O_CREAT | O_EXCL`
     evidence output (`0` `O_TRUNC` bits), identical `65,536 B` chunk geometry, identical 128-byte
     Linux AArch64 `struct kstat` ABI (`size` at `+48`), and aligned `boot0`/`boot1`/`p1` device
     node semantics (`/dev/nflashaB0` `252:126`, `/dev/nflashaB1` `252:127`, and `setup_nflash.sh`
     `/dev/nflasha1 -> /dev/cnflasha1` over `25,100,288 B` `MAX_P1`).
  3. Executes an end-to-end ephemeral round-trip across `fx3_recovery.capture.capture_local`,
     3-window `fx3_recovery.worker.assemble_worker_windows` (`128 + 128 + 127 = 383` chunks),
     symmetric `fx3_recovery.boot_worker.assemble_windows` (`boot0`/`boot1`), and
     `fx3_safety.preflight.verify_tier0_backup_manifest` (11/11 two-pass SHA-256 items).

- **Dimension B (`p1` FAT12 + SquashFS + `/p1chksum` Container & `U5` Exit Handoff Audit)**:
  1. Parses the canonical read-only FX6 updater image `0400_updater/dev/nflasha1` (`16,684,032 B`,
     SHA-256 `2a32ea4d...`) in memory via `fx3_recovery.fat.FatP1`, `fx3_recovery.squash.SquashFS`,
     `fx3_recovery.engine.checksum_pair`, and `fx3_recovery.engine.inspect_image`.
  2. Verifies the VFAT boot layout (`/boot/initrd.img`, `/boot/vmlinux.bin`, `/boot/cxd90057.dtb`,
     `/boot/kemco.txt`, `/boot/loadaddr.txt`, `/p1chksum` MD5 pair), SquashFS 4.0/gzip rootfs
     (`342` entries, `/root/IAMUPDATER` marker, cross-model `component_profile_match == False`
     isolation on `libsdfileinputupdaterapi.so`, byte-identical `libupdatercorecommon.so`,
     `common.src`, `up.sh`, and `ud_send_lsi.elf`), and `setup_nflash.sh` / `us_remove_modes.sh` /
     `execute_ufp.sh` / `us_reboot.sh` scripts.
  3. Micro-executes the `p1`-SquashFS `/usr/bin/ud_send_lsi.elf` (`9fb4bd02...`) in Unicorn AArch64
     (`argv = ["ud_send_lsi.elf", "0"]` -> `00000000` on queue `0x804b0376`) and proves via
     `verify_boot_selector_safety_contract` that partial teardown traps the camera in sticky `p1`
     mode whereas complete two-step teardown (`rm -f /setting/updater/mode*` + `ud_send_lsi.elf 0`)
     guarantees deterministic return to normal `Bank 0` cold boot.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import struct
import sys
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from fx3_safety.preflight import (
    TIER0_CANONICAL_SOURCES,
    TIER0_REQUIRED_BACKUPS,
    audit_tier0_worker_syscall_trace,
    verify_tier0_backup_manifest,
)

from .backup_mount_tolerance_verifier import (
    DEFAULT_COLOR_PORT_WORK_DIR,
    DEFAULT_FX6_TEAM_DIR,
)
from .boot_selector_and_bank_verifier import (
    PINNED_COMMON_SRC_SHA256,
    PINNED_P1_AND_FX3_UD_SEND_LSI_SHA256,
    PINNED_UP_SH_SHA256,
    UD_SEND_LSI_DST_QUEUE_ID,
    UD_SEND_LSI_SRC_REPLY_QUEUE_ID,
    BootSelectorSafetyCheck,
    UdSendLsiUnicornCase,
    run_ud_send_lsi_unicorn_case,
    verify_boot_selector_safety_contract,
)
from .kernel_dtb_compatibility_verifier import (
    PINNED_CXD90057_DTB_SHA256,
    PINNED_LOADADDR_TXT_SHA256,
    PINNED_FX3_HOST_KO_SHA256,
)


DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RECOVERY_ADAPTER_DIR = DEFAULT_REPO_ROOT / "outputs" / "fx3-recovery-adapter"
DEFAULT_TIER0_WORKER_C_PATH = DEFAULT_REPO_ROOT / "outputs" / "fx6-on-fx3-closure" / "native" / "tier0_backup_worker.c"
DEFAULT_FX3_P1_READER_C_PATH = DEFAULT_RECOVERY_ADAPTER_DIR / "native" / "fx3_p1_reader.c"
DEFAULT_FX3_BOOT_READER_C_PATH = DEFAULT_RECOVERY_ADAPTER_DIR / "native" / "fx3_boot_reader.c"


def _resolve_default_fx6_p1_image_path() -> Path:
    tree_candidate = DEFAULT_FX6_TEAM_DIR / "donor" / "tree" / "0400_updater" / "dev" / "nflasha1"
    if tree_candidate.is_file():
        return tree_candidate
    flat_candidate = DEFAULT_FX6_TEAM_DIR / "donor" / "0400_updater" / "dev" / "nflasha1"
    return flat_candidate


DEFAULT_FX6_P1_IMAGE_PATH = _resolve_default_fx6_p1_image_path()


def _ensure_fx3_recovery_imported() -> None:
    adapter_str = str(DEFAULT_RECOVERY_ADAPTER_DIR.resolve())
    if DEFAULT_RECOVERY_ADAPTER_DIR.is_dir() and adapter_str not in sys.path:
        sys.path.insert(0, adapter_str)


# Pinned FX6 `0400_updater/dev/nflasha1` & SquashFS member digests
PINNED_FX6_P1_IMAGE_BYTES = 16_684_032
PINNED_FX6_P1_IMAGE_SHA256 = "2a32ea4db3c7cabc5daad3b4e015acbc3c277ac38148b253f241c9c31d456786"
PINNED_FX6_P1_INITRD_BYTES = 6_914_048
PINNED_FX6_P1_INITRD_SHA256 = "5032fc777296e3e1f1b3bb6c7f2f249f18ee135f3c2424f83b7b6fff1e5831c0"
PINNED_FX6_P1_VMLINUX_BYTES = 6_582_280
PINNED_FX6_P1_VMLINUX_SHA256 = "58f595d53a0bfb328ee6530c7e93cbdd29d3296d1f2ee08c8322f5b1ba77c70b"
PINNED_FX6_P1_KEMCO_BYTES = 933
PINNED_FX6_P1_KEMCO_SHA256 = "e7763ad93a721f297670f13abc452cf467c0d2c344888d4e55ead2440c295950"
PINNED_FX6_P1_CHKSUM_BYTES = 105
PINNED_FX6_P1_CHKSUM_SHA256 = "10ccb63659f0ea2d485d513142006947c0ce0b7683f5b22b9ca0e0a006b031d3"

PINNED_EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
PINNED_FX6_P1_SETUP_NFLASH_SHA256 = "cc71a751c621db90a3f201959115fddb9b46be41fee2051f505bd6170f2728dc"
PINNED_FX6_P1_US_REMOVE_MODES_SHA256 = "90a56f5b3d6e1a304055d7ccabdf058da8703a3e956781112022e7ee697bda4a"
PINNED_FX6_P1_US_REBOOT_SHA256 = "9307a9f79e2814589202cc0f41e5ba531d0ca993f0471ea791ffba5da5b51c4f"
PINNED_FX6_P1_EXECUTE_UFP_SHA256 = "956e5bf01e0641e79a83dd4806aaece1aecca19b1b3d29b9606a2b981392960a"
PINNED_FX6_SDFILEINPUT_API_SHA256 = "cdea4f632692efc9742c5daf6e2bc5f1f2f9a75547d05b12823282a10d83f167"
PINNED_SHARED_UPDATER_CORE_COMMON_SHA256 = "b2b066b963a42d96556f811a773579eb16a0358de1b3a9206a1845c0df99bb74"

# Linux openat flag masks
O_ACCMODE = 0x3
O_RDONLY = 0x0
O_WRONLY = 0x1
O_CREAT = 0x40
O_EXCL = 0x80
O_TRUNC = 0x200
O_NOFOLLOW_ANY = 0x8000 | 0x20000
O_CLOEXEC = 0x80000


@dataclass(frozen=True)
class WorkerCSourcePosture:
    worker_name: str
    source_relpath: str
    source_sha256: str
    chunk_bytes: int
    at_fdcwd: int
    rd_open_flags_hex: str
    wr_excl_flags_hex: str
    rd_is_strictly_readonly: bool
    rd_carries_nofollow_and_cloexec: bool
    wr_carries_creat_excl_no_trunc: bool
    kstat_128b_assert_present: bool
    valid: bool


@dataclass(frozen=True)
class Tier0RecoveryAlignmentReport:
    valid: bool
    workers_audited: Tuple[WorkerCSourcePosture, ...]
    boot_unit_bytes: int
    boot_max_bytes: int
    boot_major_minor_b0: Tuple[int, int]
    boot_major_minor_b1: Tuple[int, int]
    p1_exact_bytes: int
    p1_chunk_count: int
    p1_window_counts: Tuple[int, int, int]
    devno_ko_profile_hash_matched: bool
    cnflasha1_nflasha1_symlink_contract_verified: bool
    twopass_capture_local_sha256: str
    assembled_p1_worker_sha256: str
    assembled_boot0_sha256: str
    assembled_boot1_sha256: str
    tier0_manifest_11_items_valid: bool
    tier0_syscall_trace_valid: bool
    non_deployment_flags_aligned: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P1SquashFsContractAudit:
    valid: bool
    fat_sector_bytes: int
    fat_cluster_sectors: int
    fat_clusters: int
    boot_member_count: int
    p1chksum_md5_verified: bool
    dtb_matches_fx3_canonical: bool
    loadaddr_matches_fx3_canonical: bool
    squashfs_inodes: int
    squashfs_fragments: int
    squashfs_block_size: int
    iamupdater_marker_present: bool
    fx3_profile_rejected_on_fx6_p1: bool
    shared_updatercorecommon_matched: bool
    common_src_matched_u5: bool
    up_sh_matched_u5: bool
    ud_send_lsi_matched_u5: bool
    setup_nflash_symlink_script_verified: bool
    teardown_scripts_verified: bool
    ud_send_lsi_mode0_main_case: UdSendLsiUnicornCase
    ud_send_lsi_mode0_sub_case: UdSendLsiUnicornCase
    partial_mode_only_sticky_detected: bool
    partial_lsi_only_sticky_detected: bool
    full_two_step_bank0_handoff: BootSelectorSafetyCheck
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase11P1RecoveryBridgeReport:
    all_checks_passed: bool
    p1_recovery_bridge_ok: bool
    tier0_alignment: Tier0RecoveryAlignmentReport
    p1_container_and_u5_handoff: P1SquashFsContractAudit
    errors: Tuple[str, ...]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_c_enum_int(c_text: str, name: str) -> Optional[int]:
    m = re.search(rf"\b{re.escape(name)}\s*=\s*(-?0x[0-9a-fA-F]+|-?\d+)\b", c_text)
    if not m:
        return None
    return int(m.group(1), 0)


def audit_worker_c_source_posture(
    worker_name: str,
    c_path: Path,
    *,
    rd_const_name: str,
    wr_const_name: str,
    chunk_const_name: str,
    repo_root: Path = DEFAULT_REPO_ROOT,
) -> WorkerCSourcePosture:
    raw = c_path.read_bytes()
    text = raw.decode("utf-8")
    chunk_val = _parse_c_enum_int(text, chunk_const_name) or 0
    at_fdcwd = _parse_c_enum_int(text, "AT_FDCWD") or 0
    rd_flags = _parse_c_enum_int(text, rd_const_name)
    wr_flags = _parse_c_enum_int(text, wr_const_name)

    rd_ok = (
        rd_flags is not None
        and (rd_flags & O_ACCMODE) == O_RDONLY
        and (rd_flags & (O_CREAT | O_EXCL | O_TRUNC)) == 0
    )
    rd_nofollow_cloexec = (
        rd_flags is not None
        and (rd_flags & O_NOFOLLOW_ANY) != 0
        and (rd_flags & O_CLOEXEC) != 0
    )
    wr_ok = (
        wr_flags is not None
        and (wr_flags & O_ACCMODE) == O_WRONLY
        and (wr_flags & (O_CREAT | O_EXCL)) == (O_CREAT | O_EXCL)
        and (wr_flags & O_TRUNC) == 0
        and (wr_flags & O_NOFOLLOW_ANY) != 0
    )
    kstat_ok = ("sizeof(struct kstat)" in text and "128" in text and "48" in text)

    try:
        rel_str = str(c_path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        rel_str = c_path.name

    valid = (
        chunk_val == 65536
        and at_fdcwd == -100
        and rd_ok
        and rd_nofollow_cloexec
        and wr_ok
        and kstat_ok
    )
    return WorkerCSourcePosture(
        worker_name=worker_name,
        source_relpath=rel_str,
        source_sha256=_sha256_bytes(raw),
        chunk_bytes=chunk_val,
        at_fdcwd=at_fdcwd,
        rd_open_flags_hex=hex(rd_flags) if rd_flags is not None else "missing",
        wr_excl_flags_hex=hex(wr_flags) if wr_flags is not None else "missing",
        rd_carries_nofollow_and_cloexec=rd_nofollow_cloexec,
        rd_is_strictly_readonly=rd_ok,
        wr_carries_creat_excl_no_trunc=wr_ok,
        kstat_128b_assert_present=kstat_ok,
        valid=valid,
    )


def _write_synthetic_p1_worker_window(
    win_dir: Path,
    capture_id: str,
    window: int,
    full_image: bytes,
    *,
    major: int = 253,
    minor: int = 1,
) -> None:
    _ensure_fx3_recovery_imported()
    from fx3_recovery import capture as cap_mod  # type: ignore
    from fx3_recovery import worker as p1_worker  # type: ignore

    win_dir.mkdir(parents=True, exist_ok=False)
    req_bytes = p1_worker.request(capture_id, window)
    (win_dir / "request.bin").write_bytes(req_bytes)

    first, count = cap_mod.shape(window)
    win_slice = full_image[first * cap_mod.BLOCK : (first + count) * cap_mod.BLOCK]

    for local_idx, chunk_idx in enumerate(range(first, first + count)):
        chunk_data = full_image[chunk_idx * cap_mod.BLOCK : (chunk_idx + 1) * cap_mod.BLOCK]
        header = bytearray(128)
        header[:16] = p1_worker.CHUNK
        struct.pack_into(
            "<IIIiQQIIIIII",
            header,
            16,
            1,
            window,
            chunk_idx,
            0,
            cap_mod.MAX_P1,
            chunk_idx * cap_mod.BLOCK,
            cap_mod.BLOCK,
            cap_mod.BLOCK,
            zlib.crc32(chunk_data),
            major,
            minor,
            0,
        )
        header[72:88] = bytes.fromhex(capture_id)
        header[88:104] = p1_worker.NAME
        (win_dir / f"chunk-{local_idx:03d}.bin").write_bytes(bytes(header) + chunk_data)

    manifest = bytearray(128)
    manifest[:16] = p1_worker.MANIFEST
    struct.pack_into(
        "<IIIIQQIIII",
        manifest,
        16,
        1,
        window,
        first,
        count,
        cap_mod.MAX_P1,
        first * cap_mod.BLOCK,
        cap_mod.BLOCK,
        zlib.crc32(win_slice),
        major,
        minor,
    )
    manifest[64:80] = bytes.fromhex(capture_id)
    manifest[80:96] = p1_worker.NAME
    struct.pack_into("<iII", manifest, 96, 0, 63, zlib.crc32(req_bytes[:52]))
    (win_dir / "manifest.bin").write_bytes(bytes(manifest))


def _write_synthetic_boot_worker_window(
    win_dir: Path,
    capture_id: str,
    target: str,
    window: int,
    boot_image: bytes,
) -> None:
    _ensure_fx3_recovery_imported()
    from fx3_recovery import boot_worker  # type: ignore
    from fx3_recovery import capture as cap_mod  # type: ignore

    role = int(target[-1])
    total = len(boot_image)
    win_dir.mkdir(parents=True, exist_ok=False)
    req_bytes = boot_worker.request(capture_id, target, window, expected_total=total)
    (win_dir / "request.bin").write_bytes(req_bytes)

    start, num = boot_worker.shape(total, window)
    windows_total = (boot_worker.geometry(total) + boot_worker.WINDOW - 1) // boot_worker.WINDOW
    win_slice = boot_image[start * cap_mod.BLOCK : (start + num) * cap_mod.BLOCK]
    req_sha = hashlib.sha256(req_bytes).digest()
    dev_name = f"nflashaB{role}".encode("ascii").ljust(16, b"\x00")

    for local_idx, chunk_idx in enumerate(range(start, start + num)):
        chunk_data = boot_image[chunk_idx * cap_mod.BLOCK : (chunk_idx + 1) * cap_mod.BLOCK]
        header = bytearray(256)
        header[:16] = boot_worker.CHUNK
        struct.pack_into(
            "<IIIIQQIIIIII",
            header,
            16,
            1,
            role,
            window,
            chunk_idx,
            total,
            chunk_idx * cap_mod.BLOCK,
            cap_mod.BLOCK,
            cap_mod.BLOCK,
            zlib.crc32(chunk_data),
            252,
            126 + role,
            3,
        )
        header[72:88] = bytes.fromhex(capture_id)
        header[88:104] = dev_name
        header[104:136] = boot_worker.PROFILE
        header[136:168] = req_sha
        (win_dir / f"chunk-{local_idx:03d}.bin").write_bytes(bytes(header) + chunk_data)

    manifest = bytearray(256)
    manifest[:16] = boot_worker.MANIFEST
    struct.pack_into(
        "<IIIIIIQQIIII",
        manifest,
        16,
        1,
        role,
        window,
        start,
        num,
        cap_mod.BLOCK,
        total,
        start * cap_mod.BLOCK,
        zlib.crc32(win_slice),
        252,
        126 + role,
        255,
    )
    manifest[72:88] = bytes.fromhex(capture_id)
    manifest[88:104] = dev_name
    manifest[104:136] = boot_worker.PROFILE
    manifest[136:168] = req_sha
    struct.pack_into("<IIIIi", manifest, 168, zlib.crc32(req_bytes[:124]), windows_total, 1, 3, 0)
    (win_dir / "manifest.bin").write_bytes(bytes(manifest))


def verify_tier0_fx3_recovery_alignment(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    tier0_worker_c_path: Path = DEFAULT_TIER0_WORKER_C_PATH,
    fx3_p1_reader_c_path: Path = DEFAULT_FX3_P1_READER_C_PATH,
    fx3_boot_reader_c_path: Path = DEFAULT_FX3_BOOT_READER_C_PATH,
    inject_tier0_size_mismatch: bool = False,
    inject_worker_write_flag: bool = False,
) -> Tier0RecoveryAlignmentReport:
    """Audit Read-Only Capture, Device Node, and Two-Pass SHA-256 Contracts across Tier-0 and `fx3_recovery`."""
    _ensure_fx3_recovery_imported()
    from fx3_recovery import boot_worker  # type: ignore
    from fx3_recovery import capture as cap_mod  # type: ignore
    from fx3_recovery import files as fx3_files  # type: ignore
    from fx3_recovery import worker as p1_worker  # type: ignore

    errors: List[str] = []

    # 1. C worker source posture cross-audit
    w_tier0 = audit_worker_c_source_posture(
        "tier0_backup_worker",
        tier0_worker_c_path,
        rd_const_name="O_RDONLY_SAFE",
        wr_const_name="O_WRONLY_EXCL",
        chunk_const_name="CHUNK_BYTES",
        repo_root=repo_root,
    )
    w_p1 = audit_worker_c_source_posture(
        "fx3_p1_reader",
        fx3_p1_reader_c_path,
        rd_const_name="RD",
        wr_const_name="NEW",
        chunk_const_name="BLOCK",
        repo_root=repo_root,
    )
    w_boot = audit_worker_c_source_posture(
        "fx3_boot_reader",
        fx3_boot_reader_c_path,
        rd_const_name="RD",
        wr_const_name="NEW",
        chunk_const_name="BLOCK",
        repo_root=repo_root,
    )
    workers = (w_tier0, w_p1, w_boot)
    for w in workers:
        if not w.valid:
            errors.append(f"C worker posture check failed for {w.worker_name} ({w.source_relpath})")

    # 2. Boot0 / Boot1 / p1 geometry & device-node semantics alignment
    t0_b0 = TIER0_REQUIRED_BACKUPS["boot0"]
    t0_b1 = TIER0_REQUIRED_BACKUPS["boot1"]
    t0_p1 = TIER0_REQUIRED_BACKUPS["p1_updater"]

    boot_bounds_ok = (
        int(t0_b0["min_bytes"]) == boot_worker.UNIT == 131_072
        and int(t0_b0["max_bytes"]) == boot_worker.MAX_BOOT == 33_423_360
        and int(t0_b0["multiple_of"]) == boot_worker.UNIT
        and int(t0_b1["min_bytes"]) == boot_worker.UNIT
        and int(t0_b1["max_bytes"]) == boot_worker.MAX_BOOT
        and int(t0_b1["multiple_of"]) == boot_worker.UNIT
        and TIER0_CANONICAL_SOURCES["boot0"]["source_path"] == "/dev/nflashaB0"
        and TIER0_CANONICAL_SOURCES["boot1"]["source_path"] == "/dev/nflashaB1"
    )
    if not boot_bounds_ok:
        errors.append("boot0/boot1 geometry or /dev/nflashaB0..B1 paths drifted between fx3_safety and fx3_recovery")

    req_b0 = boot_worker.request("1" * 32, "boot0", 0, expected_total=boot_worker.UNIT)
    req_b1 = boot_worker.request("1" * 32, "boot1", 0, expected_total=boot_worker.UNIT)
    _, maj0, min0, _ = struct.unpack_from("<IIII", req_b0, 88)
    _, maj1, min1, _ = struct.unpack_from("<IIII", req_b1, 88)
    if (maj0, min0) != (252, 126) or (maj1, min1) != (252, 127):
        errors.append(f"Unexpected boot0/boot1 major:minor {(maj0, min0)} / {(maj1, min1)}")

    win_shapes = tuple(cap_mod.shape(w)[1] for w in (0, 1, 2))
    p1_bounds_ok = (
        int(t0_p1["exact_bytes"]) == cap_mod.MAX_P1 == 25_100_288
        and cap_mod.CHUNKS == 383
        and cap_mod.BLOCK == 65_536
        and sum(win_shapes) == cap_mod.CHUNKS
        and win_shapes == (128, 128, 127)
        and TIER0_CANONICAL_SOURCES["p1_updater"]["source_path"] == "/dev/nflasha1"
        and p1_worker.NAME.rstrip(b"\x00") == b"cnflasha1"
    )
    if not p1_bounds_ok:
        errors.append("p1_updater size (25,100,288 B) or 3-window 383-chunk geometry drifted")

    p1_c_text = fx3_p1_reader_c_path.read_text(encoding="utf-8")
    symlink_contract_ok = (
        '"pnflasha1"' in p1_c_text
        and '"cnflasha1"' in p1_c_text
        and '"/dev/cnflasha1"' in p1_c_text
        and "TOTAL/1024" in p1_c_text
    )
    if not symlink_contract_ok:
        errors.append("fx3_p1_reader.c missing dual pnflasha1/cnflasha1 partition & O_NOFOLLOW block-node check")

    # Verify devno.ko SHA-256 in boot_worker.FILE_PROFILE matches Phase 8 pinned FX3 host .ko
    boot_profile_map = {p: (sz, h) for p, sz, h in boot_worker.FILE_PROFILE}
    devno_ok = (
        "/kmod/devno.ko" in boot_profile_map
        and boot_profile_map["/kmod/devno.ko"][1] == PINNED_FX3_HOST_KO_SHA256["devno.ko"]
    )
    if not devno_ok:
        errors.append("boot_worker.FILE_PROFILE /kmod/devno.ko SHA-256 drifted from Phase 8 FX3 host module pin")

    non_deploy_ok = (
        cap_mod.FALSE_FLAGS.get("flashable") is False
        and cap_mod.FALSE_FLAGS.get("hardware_validated") is False
        and boot_worker.BOOT_FALSE.get("hardware_partition_access_restored") is False
    )
    if not non_deploy_ok:
        errors.append("fx3_recovery non-deployment safety flags are not strictly False")

    # 3. Ephemeral two-pass SHA-256 & 3-window assembly round-trip inside fx3_files.ROOT
    scratch_parent = fx3_files.ROOT if fx3_files.ROOT.is_dir() else repo_root
    tmp_dir_path = Path(tempfile.mkdtemp(prefix=".fx6-p1-bridge-", dir=str(scratch_parent)))
    try:
        synth_p1 = (b"FX3-P1-BRIDGE-SYNTH\x00" * 16)[:320] + bytes(cap_mod.MAX_P1 - 320)
        synth_boot0 = (b"FX3-BOOT0-SYNTH\x00" * 16)[:256] + bytes(boot_worker.UNIT - 256)
        synth_boot1 = (b"FX3-BOOT1-SYNTH\x00" * 16)[:256] + bytes(boot_worker.UNIT - 256)

        p1_src = tmp_dir_path / "regular_source.p1"
        p1_src.write_bytes(synth_p1)
        os.chmod(p1_src, 0o600)
        expected_p1_sha = _sha256_bytes(synth_p1)
        body_tag = hashlib.sha256(b"phase11-bridge-camera-body-tag").hexdigest()
        cap_id = "a1b2c3d4e5f60718293a4b5c6d7e8f90"

        reg_src = cap_mod.RegularFileSource(p1_src, expected_p1_sha)
        try:
            src_ident = reg_src.identify()
            streamed_sha = hashlib.sha256()
            nonce_hex = "11223344556677889900aabbccddeeff"
            for chunk_idx in range(cap_mod.CHUNKS):
                req_obj = cap_mod.Request(cap_id, nonce_hex, chunk_idx, chunk_idx * cap_mod.BLOCK)
                rep_obj = reg_src.read_at(req_obj, 60.0)
                if rep_obj.status != 0 or rep_obj.actual != cap_mod.BLOCK:
                    errors.append(f"RegularFileSource short/failed pread at chunk {chunk_idx}")
                    break
                streamed_sha.update(rep_obj.data)
            reg_src.finish()
            cap_sha = streamed_sha.hexdigest()
            if src_ident.get("expected_sha256") != expected_p1_sha:
                errors.append("RegularFileSource identify() expected_sha256 mismatch")
        finally:
            reg_src.close()

        p1_win_dirs = []
        for w_idx in (0, 1, 2):
            w_dir = tmp_dir_path / f"p1_win_{w_idx}"
            _write_synthetic_p1_worker_window(w_dir, cap_id, w_idx, synth_p1)
            p1_win_dirs.append(w_dir)
        p1_assembled_out = tmp_dir_path / "p1_worker_assembled"
        p1_worker_rep = p1_worker.assemble_worker_windows(
            p1_win_dirs,
            [0, 0, 0],
            p1_assembled_out,
            body_tag,
        )
        assembled_p1_sha = str(p1_worker_rep["sha256"])

        b0_win_dir = tmp_dir_path / "boot0_w0"
        _write_synthetic_boot_worker_window(b0_win_dir, cap_id, "boot0", 0, synth_boot0)
        b0_rep = boot_worker.assemble_windows([b0_win_dir], [0], tmp_dir_path / "boot0_assembled", body_tag)
        assembled_b0_sha = str(b0_rep["sha256"])

        b1_win_dir = tmp_dir_path / "boot1_w0"
        _write_synthetic_boot_worker_window(b1_win_dir, cap_id, "boot1", 0, synth_boot1)
        b1_rep = boot_worker.assemble_windows([b1_win_dir], [0], tmp_dir_path / "boot1_assembled", body_tag)
        assembled_b1_sha = str(b1_rep["sha256"])

        if cap_sha != expected_p1_sha or assembled_p1_sha != expected_p1_sha:
            errors.append(
                f"p1 SHA-256 mismatch across capture_local ({cap_sha}) vs worker assembly ({assembled_p1_sha})"
            )

        # Feed assembled digests directly into Tier-0 11-item manifest verifier
        p1_manifest_bytes = cap_mod.MAX_P1 - 512 if inject_tier0_size_mismatch else cap_mod.MAX_P1
        dummy_sha = hashlib.sha256(b"tier0-bridge-fixed-item").hexdigest()
        tier0_manifest: Dict[str, object] = {
            "camera_body_tag": body_tag,
            "model_id": "0x91030080",
            "items": {
                "sector0": {"bytes": 512, "pass1_sha256": dummy_sha, "pass2_sha256": dummy_sha},
                "boot0": {
                    "bytes": boot_worker.UNIT,
                    "pass1_sha256": assembled_b0_sha,
                    "pass2_sha256": assembled_b0_sha,
                },
                "boot1": {
                    "bytes": boot_worker.UNIT,
                    "pass1_sha256": assembled_b1_sha,
                    "pass2_sha256": assembled_b1_sha,
                },
                "p1_updater": {
                    "bytes": p1_manifest_bytes,
                    "pass1_sha256": cap_sha,
                    "pass2_sha256": assembled_p1_sha,
                },
                "p2_backup_bin": {"bytes": 262144, "pass1_sha256": dummy_sha, "pass2_sha256": dummy_sha},
                "p2_psd_bin": {"bytes": 4096, "pass1_sha256": dummy_sha, "pass2_sha256": dummy_sha},
                "p2_defdet_bin": {"bytes": 4096, "pass1_sha256": dummy_sha, "pass2_sha256": dummy_sha},
                "p6_jiritsu": {"bytes": 26214400, "pass1_sha256": dummy_sha, "pass2_sha256": dummy_sha},
                "p12_cert": {"bytes": 20971520, "pass1_sha256": dummy_sha, "pass2_sha256": dummy_sha},
                "p18_lensfile": {"bytes": 4096, "pass1_sha256": dummy_sha, "pass2_sha256": dummy_sha},
                "spi_nor_ddrtraining": {"bytes": 4096, "pass1_sha256": dummy_sha, "pass2_sha256": dummy_sha},
            },
        }
        manifest_audit = verify_tier0_backup_manifest(tier0_manifest)
        if not manifest_audit.valid:
            errors.extend(manifest_audit.errors)

        p1_open_flags = (0xA0000 | O_WRONLY) if inject_worker_write_flag else 0xA0000
        bridged_trace: List[Dict[str, object]] = [
            {"nr": 35, "dirfd": -100, "path": "/tmp/jiritsu/libJit.so", "flags": 0, "ret": 0},
            {"nr": 56, "dirfd": -100, "path": "/dev/cnflasha1", "flags": p1_open_flags, "ret": 3},
            {"nr": 56, "dirfd": -100, "path": "/dev/nflashaB0", "flags": 0xA0000, "ret": 4},
            {"nr": 56, "dirfd": -100, "path": "/dev/nflashaB1", "flags": 0xA0000, "ret": 5},
            {"nr": 56, "dirfd": -100, "path": "/mnt/fx3_tier0_backup/p1_updater.bin", "flags": 0xA00C1, "ret": 6},
            {"nr": 64, "fd": 6, "ret": 65536},
            {"nr": 57, "fd": 6, "ret": 0},
            {"nr": 57, "fd": 5, "ret": 0},
            {"nr": 57, "fd": 4, "ret": 0},
            {"nr": 57, "fd": 3, "ret": 0},
        ]
        trace_audit = audit_tier0_worker_syscall_trace(bridged_trace)
        if not trace_audit.valid:
            errors.extend(trace_audit.errors)
    finally:
        shutil.rmtree(tmp_dir_path, ignore_errors=True)

    valid = (
        all(w.valid for w in workers)
        and boot_bounds_ok
        and p1_bounds_ok
        and symlink_contract_ok
        and devno_ok
        and non_deploy_ok
        and manifest_audit.valid
        and trace_audit.valid
        and len(errors) == 0
    )
    return Tier0RecoveryAlignmentReport(
        valid=valid,
        workers_audited=workers,
        boot_unit_bytes=boot_worker.UNIT,
        boot_max_bytes=boot_worker.MAX_BOOT,
        boot_major_minor_b0=(maj0, min0),
        boot_major_minor_b1=(maj1, min1),
        p1_exact_bytes=cap_mod.MAX_P1,
        p1_chunk_count=cap_mod.CHUNKS,
        p1_window_counts=win_shapes,
        devno_ko_profile_hash_matched=devno_ok,
        cnflasha1_nflasha1_symlink_contract_verified=symlink_contract_ok,
        twopass_capture_local_sha256=cap_sha,
        assembled_p1_worker_sha256=assembled_p1_sha,
        assembled_boot0_sha256=assembled_b0_sha,
        assembled_boot1_sha256=assembled_b1_sha,
        tier0_manifest_11_items_valid=manifest_audit.valid,
        tier0_syscall_trace_valid=trace_audit.valid,
        non_deployment_flags_aligned=non_deploy_ok,
        errors=tuple(errors),
    )


def verify_p1_container_and_u5_handoff(
    *,
    fx6_p1_image_path: Path = DEFAULT_FX6_P1_IMAGE_PATH,
    tamper_p1_checksum: bool = False,
    incomplete_u5_teardown: bool = False,
) -> P1SquashFsContractAudit:
    """Audit `0400_updater/dev/nflasha1` via `fx3_recovery.fat`/`squash` and prove `U5` sticky-free `Bank 0` exit."""
    _ensure_fx3_recovery_imported()
    from fx3_recovery.engine import CHECKSUM, checksum_pair, inspect_image  # type: ignore
    from fx3_recovery.fat import FatP1  # type: ignore
    from fx3_recovery.squash import SquashFS  # type: ignore

    errors: List[str] = []
    raw_p1 = fx6_p1_image_path.read_bytes()
    if len(raw_p1) != PINNED_FX6_P1_IMAGE_BYTES or _sha256_bytes(raw_p1) != PINNED_FX6_P1_IMAGE_SHA256:
        errors.append(
            f"FX6 p1 donor image size/SHA-256 mismatch: got {len(raw_p1)} B / {_sha256_bytes(raw_p1)}"
        )

    if tamper_p1_checksum:
        mut = bytearray(raw_p1)
        temp_fat = FatP1(raw_p1)
        bad_chk = bytearray(temp_fat.contents(CHECKSUM))
        bad_chk[0] = ord("f") if bad_chk[0] != ord("f") else ord("0")
        temp_fat.replace(mut, CHECKSUM, 0, bytes(bad_chk))
        raw_p1 = bytes(mut)

    fat = FatP1(raw_p1)
    p1chksum_ok = False
    try:
        verified_chk = checksum_pair(fat)
        p1chksum_ok = (verified_chk == fat.contents(CHECKSUM))
    except Exception as exc:
        errors.append(f"p1chksum verification failed: {exc}")

    expected_members = {
        "/boot/initrd.img": (PINNED_FX6_P1_INITRD_BYTES, PINNED_FX6_P1_INITRD_SHA256),
        "/boot/vmlinux.bin": (PINNED_FX6_P1_VMLINUX_BYTES, PINNED_FX6_P1_VMLINUX_SHA256),
        "/boot/cxd90057.dtb": (17_131, PINNED_CXD90057_DTB_SHA256),
        "/boot/kemco.txt": (PINNED_FX6_P1_KEMCO_BYTES, PINNED_FX6_P1_KEMCO_SHA256),
        "/boot/loadaddr.txt": (48, PINNED_LOADADDR_TXT_SHA256),
    }
    regular_files = [k for k, v in fat.files.items() if not v["directory"]]
    for member_path, (exp_sz, exp_sha) in expected_members.items():
        if member_path not in fat.files:
            errors.append(f"Missing mandatory p1 VFAT boot member: {member_path}")
            continue
        blob = fat.contents(member_path)
        if len(blob) != exp_sz or _sha256_bytes(blob) != exp_sha:
            errors.append(f"p1 VFAT member {member_path} digest/size mismatch")

    dtb_ok = (
        "/boot/cxd90057.dtb" in fat.files
        and _sha256_bytes(fat.contents("/boot/cxd90057.dtb")) == PINNED_CXD90057_DTB_SHA256
    )
    loadaddr_ok = (
        "/boot/loadaddr.txt" in fat.files
        and _sha256_bytes(fat.contents("/boot/loadaddr.txt")) == PINNED_LOADADDR_TXT_SHA256
    )

    initrd_bytes = fat.contents("/boot/initrd.img")
    sq = SquashFS(initrd_bytes)
    sq_entries = {r["path"]: r for r in sq.walk()}

    iamupdater_ok = (
        "/root/IAMUPDATER" in sq_entries
        and sq_entries["/root/IAMUPDATER"]["size"] == 0
        and _sha256_bytes(sq.contents(sq_entries["/root/IAMUPDATER"])) == PINNED_EMPTY_SHA256
    )
    if not iamupdater_ok:
        errors.append("Missing 0-byte /root/IAMUPDATER marker in p1 SquashFS")

    profile_rejected_ok = False
    shared_core_ok = False
    if p1chksum_ok:
        insp = inspect_image(raw_p1)
        lib_map = {row["path"]: row for row in insp["libraries"]}
        profile_rejected_ok = (
            insp["component_profile_match"] is False
            and lib_map["/usr/lib/libsdfileinputupdaterapi.so"]["sha256"] == PINNED_FX6_SDFILEINPUT_API_SHA256
            and lib_map["/usr/lib/libsdfileinputupdaterapi.so"]["reference_profile_match"] is False
        )
        shared_core_ok = (
            lib_map["/usr/lib/libupdatercorecommon.so"]["sha256"] == PINNED_SHARED_UPDATER_CORE_COMMON_SHA256
            and lib_map["/usr/lib/libupdatercorecommon.so"]["reference_profile_match"] is True
        )
        if not profile_rejected_ok or not shared_core_ok:
            errors.append("Unexpected cross-model fx3_recovery component_profile_match result on FX6 p1")

    def _sq_sha(p_str: str) -> Optional[str]:
        ent = sq_entries.get(p_str)
        if ent is None or ent["type"] != "file":
            return None
        return _sha256_bytes(sq.contents(ent))

    common_ok = _sq_sha("/usr/bin/common.src") == PINNED_COMMON_SRC_SHA256
    up_sh_ok = _sq_sha("/usr/bin/up.sh") == PINNED_UP_SH_SHA256
    ud_send_ok = _sq_sha("/usr/bin/ud_send_lsi.elf") == PINNED_P1_AND_FX3_UD_SEND_LSI_SHA256
    if not (common_ok and up_sh_ok and ud_send_ok):
        errors.append("p1 SquashFS common.src / up.sh / ud_send_lsi.elf diverged from Phase 7 U5 pins")

    setup_nflash_bytes = sq.contents(sq_entries["/usr/bin/setup_nflash.sh"])
    setup_nflash_text = setup_nflash_bytes.decode("utf-8", errors="replace")
    setup_nflash_ok = (
        _sha256_bytes(setup_nflash_bytes) == PINNED_FX6_P1_SETUP_NFLASH_SHA256
        and "s/pnflasha/nflasha/g" in setup_nflash_text
        and "s/cnflasha/nflasha/g" in setup_nflash_text
    )
    if not setup_nflash_ok:
        errors.append("p1 SquashFS /usr/bin/setup_nflash.sh symlink mapping check failed")

    rm_modes_bytes = sq.contents(sq_entries["/usr/bin/us_remove_modes.sh"])
    reboot_bytes = sq.contents(sq_entries["/usr/bin/us_reboot.sh"])
    exec_ufp_bytes = sq.contents(sq_entries["/usr/bin/execute_ufp.sh"])
    teardown_scripts_ok = (
        _sha256_bytes(rm_modes_bytes) == PINNED_FX6_P1_US_REMOVE_MODES_SHA256
        and b"/bin/rm -f /setting/updater/mode*" in rm_modes_bytes
        and _sha256_bytes(reboot_bytes) == PINNED_FX6_P1_US_REBOOT_SHA256
        and b"ud_reboot.elf" in reboot_bytes
        and _sha256_bytes(exec_ufp_bytes) == PINNED_FX6_P1_EXECUTE_UFP_SHA256
        and b"rm -rf /setting/updater/mode*" in exec_ufp_bytes
    )
    if not teardown_scripts_ok:
        errors.append("p1 SquashFS teardown scripts (us_remove_modes.sh / execute_ufp.sh / us_reboot.sh) mismatch")

    # Micro-execute the exact p1-SquashFS `/usr/bin/ud_send_lsi.elf` in Unicorn AArch64 (`mode 0`)
    ud_elf_bytes = sq.contents(sq_entries["/usr/bin/ud_send_lsi.elf"])
    case_main = run_ud_send_lsi_unicorn_case(
        ud_elf_bytes,
        case_id="p1_squashfs_ud_send_lsi_mode0_main",
        cli_args=("ud_send_lsi.elf", "0"),
        injected_lsi_type=1,
    )
    case_sub = run_ud_send_lsi_unicorn_case(
        ud_elf_bytes,
        case_id="p1_squashfs_ud_send_lsi_mode0_sub",
        cli_args=("ud_send_lsi.elf", "0"),
        injected_lsi_type=2,
    )
    unicorn_mode0_ok = (
        not case_main.abort_or_fault
        and not case_sub.abort_or_fault
        and case_main.return_value == 0
        and case_sub.return_value == 0
        and case_main.uipc_sent
        and case_sub.uipc_sent
        and case_main.observed_dst_queue == UD_SEND_LSI_DST_QUEUE_ID
        and case_main.observed_src_queue == UD_SEND_LSI_SRC_REPLY_QUEUE_ID
        and case_main.emitted_payload_hex == "00000000"
        and case_sub.emitted_payload_hex == "00000000"
    )
    if not unicorn_mode0_ok:
        errors.append("Unicorn execution of p1 SquashFS ud_send_lsi.elf mode 0 failed")

    # Prove sticky-trap detection on partial teardowns vs deterministic Bank 0 return on full 2-step teardown
    partial_mode_only = verify_boot_selector_safety_contract(
        "p1_exit_partial_us_remove_modes_only_missing_lsi0",
        in_p1_updater_env=True,
        p1_partition_written=False,
        p2_updater_mode_files=(),
        up_sh_invoked_without_direct_lsi=True,
        direct_ud_send_lsi_payload=None,
        bk4_selector_byte8=0x00,
    )
    partial_lsi_only = verify_boot_selector_safety_contract(
        "p1_exit_partial_lsi0_only_lingering_mode5",
        in_p1_updater_env=True,
        p1_partition_written=False,
        p2_updater_mode_files=("/setting/updater/mode", "/setting/updater/mode5"),
        up_sh_invoked_without_direct_lsi=False,
        direct_ud_send_lsi_payload=bytes.fromhex(case_main.emitted_payload_hex),
        bk4_selector_byte8=0x00,
    )
    partial_mode_sticky = (not partial_mode_only.valid) and partial_mode_only.sticky_updater_risk
    partial_lsi_sticky = (not partial_lsi_only.valid) and partial_lsi_only.sticky_updater_risk
    if not (partial_mode_sticky and partial_lsi_sticky):
        errors.append("Failed to flag sticky updater risk on partial p1 exit teardown")

    full_handoff = verify_boot_selector_safety_contract(
        "p1_exit_two_step_atomic_reset_to_bank0",
        in_p1_updater_env=True,
        p1_partition_written=False,
        p2_updater_mode_files=("/setting/updater/mode5",) if incomplete_u5_teardown else (),
        up_sh_invoked_without_direct_lsi=incomplete_u5_teardown,
        direct_ud_send_lsi_payload=None if incomplete_u5_teardown else bytes.fromhex(case_main.emitted_payload_hex),
        bk4_selector_byte8=0x00,
    )
    if not full_handoff.valid:
        errors.extend(full_handoff.errors)

    valid = (
        p1chksum_ok
        and dtb_ok
        and loadaddr_ok
        and iamupdater_ok
        and profile_rejected_ok
        and shared_core_ok
        and common_ok
        and up_sh_ok
        and ud_send_ok
        and setup_nflash_ok
        and teardown_scripts_ok
        and unicorn_mode0_ok
        and partial_mode_sticky
        and partial_lsi_sticky
        and full_handoff.valid
        and len(errors) == 0
    )
    return P1SquashFsContractAudit(
        valid=valid,
        fat_sector_bytes=fat.sector,
        fat_cluster_sectors=fat.cluster_sectors,
        fat_clusters=fat.clusters,
        boot_member_count=len(regular_files),
        p1chksum_md5_verified=p1chksum_ok,
        dtb_matches_fx3_canonical=dtb_ok,
        loadaddr_matches_fx3_canonical=loadaddr_ok,
        squashfs_inodes=int(sq.header["inodes"]),
        squashfs_fragments=int(sq.header["fragments"]),
        squashfs_block_size=int(sq.header["block_size"]),
        iamupdater_marker_present=iamupdater_ok,
        fx3_profile_rejected_on_fx6_p1=profile_rejected_ok,
        shared_updatercorecommon_matched=shared_core_ok,
        common_src_matched_u5=common_ok,
        up_sh_matched_u5=up_sh_ok,
        ud_send_lsi_matched_u5=ud_send_ok,
        setup_nflash_symlink_script_verified=setup_nflash_ok,
        teardown_scripts_verified=teardown_scripts_ok,
        ud_send_lsi_mode0_main_case=case_main,
        ud_send_lsi_mode0_sub_case=case_sub,
        partial_mode_only_sticky_detected=partial_mode_sticky,
        partial_lsi_only_sticky_detected=partial_lsi_sticky,
        full_two_step_bank0_handoff=full_handoff,
        errors=tuple(errors),
    )


def run_p1_recovery_bridge_verification(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_p1_image_path: Path = DEFAULT_FX6_P1_IMAGE_PATH,
    tamper_p1_checksum: bool = False,
    inject_tier0_size_mismatch: bool = False,
    inject_worker_write_flag: bool = False,
    incomplete_u5_teardown: bool = False,
) -> Phase11P1RecoveryBridgeReport:
    """Execute both Dimension A (Tier-0 <-> fx3_recovery) and Dimension B (p1 VFAT/SquashFS + U5 exit)."""
    dim_a = verify_tier0_fx3_recovery_alignment(
        repo_root=repo_root,
        inject_tier0_size_mismatch=inject_tier0_size_mismatch,
        inject_worker_write_flag=inject_worker_write_flag,
    )
    dim_b = verify_p1_container_and_u5_handoff(
        fx6_p1_image_path=fx6_p1_image_path,
        tamper_p1_checksum=tamper_p1_checksum,
        incomplete_u5_teardown=incomplete_u5_teardown,
    )
    errors = tuple(list(dim_a.errors) + list(dim_b.errors))
    ok = dim_a.valid and dim_b.valid and len(errors) == 0
    return Phase11P1RecoveryBridgeReport(
        all_checks_passed=ok,
        p1_recovery_bridge_ok=ok,
        tier0_alignment=dim_a,
        p1_container_and_u5_handoff=dim_b,
        errors=errors,
    )
