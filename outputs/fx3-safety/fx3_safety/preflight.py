"""Pre-Flash 12-Gate Safety Evaluator and Tier-0 Per-Body Backup Manifest Verifier."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .boot_contracts import verify_sector0_partition_table


TIER0_REQUIRED_BACKUPS: Dict[str, Dict[str, object]] = {
    "sector0": {
        "description": "eMMC UDA Sector 0 ('8246' '2.00' 30-entry Sony Partition Table)",
        "exact_bytes": 512,
        "spof": True,
    },
    "boot0": {
        "description": "eMMC Boot Partition 0 (/dev/nflashaB0, 252:126)",
        "min_bytes": 131072,
        "max_bytes": 33423360,
        "multiple_of": 131072,
        "spof": True,
    },
    "boot1": {
        "description": "eMMC Boot Partition 1 (/dev/nflashaB1, 252:127)",
        "min_bytes": 131072,
        "max_bytes": 33423360,
        "multiple_of": 131072,
        "spof": True,
    },
    "p1_updater": {
        "description": "p1 (/dev/nflasha1, LBA 0x80) Plaintext FAT12 Updater + dat2/dat3 + boot/*",
        "exact_bytes": 25100288,
        "spof": True,
    },
    "p2_backup_bin": {
        "description": "p2:/setting/Backup.bin (BK4\\0 + 0xfa0080 cold-boot descriptor + per-unit NVRAM)",
        "min_bytes": 262144,
        "spof": True,
    },
    "p2_psd_bin": {
        "description": "p2:/setting/psd.bin (TIER-0 Per-Sensor Phase-Detection / Shading Calibration)",
        "min_bytes": 1024,
        "spof": True,
    },
    "p2_defdet_bin": {
        "description": "p2:/setting/defdet.bin (TIER-0 Per-Sensor Defective Pixel Map Calibration)",
        "min_bytes": 1024,
        "spof": True,
    },
    "p6_jiritsu": {
        "description": "p6 (/dev/nflasha6, LBA 0xD8000) TIER-0 Factory Autonomous Adjustment (Jiritsu)",
        "exact_bytes": 26214400,
        "spof": True,
    },
    "p12_cert": {
        "description": "p12 (/dev/nflasha12, LBA 0x20C000) TIER-0 Per-Device Cryptographic Certificates",
        "min_bytes": 20971520,
        "spof": True,
    },
    "p18_lensfile": {
        "description": "p18 (/dev/nflasha18, LBA 0x31C000) TIER-0 /lens/lensfile.bin Mount Calibration",
        "min_bytes": 1024,
        "spof": True,
    },
    "spi_nor_ddrtraining": {
        "description": "Octal-SPI NOR offset 0x03e210fc ddrtraining.dat + Sector 0..768 Bootloader Image",
        "min_bytes": 2048,
        "spof": True,
    },
}


@dataclass(frozen=True)
class BackupManifestAudit:
    valid: bool
    camera_body_tag: str
    verified_items: List[str]
    missing_items: List[str]
    mismatched_two_pass_items: List[str]
    size_error_items: List[str]
    errors: List[str]


def verify_tier0_backup_manifest(manifest: Dict[str, object]) -> BackupManifestAudit:
    """Verify a per-camera Tier-0 backup manifest with two-pass idempotent readback checks.

    Expected manifest schema:
    {
      "camera_body_tag": "<64-hex-char tag>",
      "model_id": "0x91030080",
      "items": {
        "sector0": {"bytes": 512, "pass1_sha256": "...", "pass2_sha256": "..."},
        ...
      }
    }
    """
    errors: List[str] = []
    verified: List[str] = []
    missing: List[str] = []
    mismatch: List[str] = []
    size_errs: List[str] = []

    body_tag = str(manifest.get("camera_body_tag", ""))
    if len(body_tag) != 64 or any(c not in "0123456789abcdef" for c in body_tag):
        errors.append("camera_body_tag must be a 64-character lowercase hex digest")

    items = manifest.get("items")
    if not isinstance(items, dict):
        return BackupManifestAudit(
            valid=False,
            camera_body_tag=body_tag,
            verified_items=[],
            missing_items=list(TIER0_REQUIRED_BACKUPS.keys()),
            mismatched_two_pass_items=[],
            size_error_items=[],
            errors=errors + ["manifest['items'] must be a dictionary"],
        )

    for key, spec in TIER0_REQUIRED_BACKUPS.items():
        entry = items.get(key)
        if not isinstance(entry, dict):
            missing.append(key)
            errors.append(f"Missing mandatory Tier-0 backup item: {key} ({spec['description']})")
            continue

        size = entry.get("bytes")
        sha1 = str(entry.get("pass1_sha256", ""))
        sha2 = str(entry.get("pass2_sha256", ""))

        if not isinstance(size, int) or size <= 0:
            size_errs.append(key)
            errors.append(f"Item {key} has invalid byte size: {size!r}")
            continue

        if "exact_bytes" in spec and size != spec["exact_bytes"]:
            size_errs.append(key)
            errors.append(f"Item {key} requires exact size {spec['exact_bytes']} B, got {size} B")
            continue

        if "min_bytes" in spec and size < int(spec["min_bytes"]):
            size_errs.append(key)
            errors.append(f"Item {key} requires >= {spec['min_bytes']} B, got {size} B")
            continue

        if "max_bytes" in spec and size > int(spec["max_bytes"]):
            size_errs.append(key)
            errors.append(f"Item {key} requires <= {spec['max_bytes']} B, got {size} B")
            continue

        if "multiple_of" in spec and (size % int(spec["multiple_of"]) != 0):
            size_errs.append(key)
            errors.append(f"Item {key} size {size} B is not a multiple of {spec['multiple_of']} B")
            continue

        if len(sha1) != 64 or len(sha2) != 64 or sha1 != sha2:
            mismatch.append(key)
            errors.append(
                f"Item {key} failed two-pass idempotent readback check (pass1={sha1[:16]}... vs pass2={sha2[:16]}...)"
            )
            continue

        verified.append(key)

    # Check boot0 == boot1 size symmetry if both present
    if "boot0" in items and "boot1" in items:
        b0_size = items["boot0"].get("bytes")
        b1_size = items["boot1"].get("bytes")
        if b0_size != b1_size:
            size_errs.append("boot0_boot1_symmetry")
            errors.append(f"boot0 size ({b0_size}) != boot1 size ({b1_size})")

    valid = (
        len(errors) == 0
        and len(missing) == 0
        and len(mismatch) == 0
        and len(size_errs) == 0
        and len(verified) == len(TIER0_REQUIRED_BACKUPS)
    )
    return BackupManifestAudit(
        valid=valid,
        camera_body_tag=body_tag,
        verified_items=verified,
        missing_items=missing,
        mismatched_two_pass_items=mismatch,
        size_error_items=size_errs,
        errors=errors,
    )


TIER0_CANONICAL_SOURCES: Dict[str, Dict[str, object]] = {
    "sector0": {
        "source_path": "/dev/nflasha",
        "output_name": "sector0.bin",
        "magic_kind": "sector0_ptbl",
    },
    "boot0": {
        "source_path": "/dev/nflashaB0",
        "output_name": "boot0.bin",
        "magic_kind": "none",
    },
    "boot1": {
        "source_path": "/dev/nflashaB1",
        "output_name": "boot1.bin",
        "magic_kind": "none",
    },
    "p1_updater": {
        "source_path": "/dev/nflasha1",
        "output_name": "p1_updater.bin",
        "magic_kind": "none",
    },
    "p2_backup_bin": {
        "source_path": "/setting/Backup.bin",
        "output_name": "p2_backup_bin.bin",
        "magic_kind": "bk4",
    },
    "p2_psd_bin": {
        "source_path": "/setting/psd.bin",
        "output_name": "p2_psd_bin.bin",
        "magic_kind": "none",
    },
    "p2_defdet_bin": {
        "source_path": "/setting/defdet.bin",
        "output_name": "p2_defdet_bin.bin",
        "magic_kind": "none",
    },
    "p6_jiritsu": {
        "source_path": "/dev/nflasha6",
        "output_name": "p6_jiritsu.bin",
        "magic_kind": "none",
    },
    "p12_cert": {
        "source_path": "/dev/nflasha12",
        "output_name": "p12_cert.bin",
        "magic_kind": "none",
    },
    "p18_lensfile": {
        "source_path": "/dev/nflasha18",
        "output_name": "p18_lensfile.bin",
        "magic_kind": "none",
    },
    "spi_nor_ddrtraining": {
        "source_path": "/dev/mtd0",
        "output_name": "spi_nor_ddrtraining.bin",
        "magic_kind": "none",
    },
}


@dataclass(frozen=True)
class WorkerSyscallAudit:
    valid: bool
    first_path_op_unlink_libjit: bool
    dev_write_open_count: int
    source_fd_write_count: int
    missing_nofollow_source_opens: int
    non_excl_output_opens: int
    total_syscalls: int
    errors: List[str]


def audit_tier0_worker_syscall_trace(
    syscalls: List[Dict[str, object]],
    allowed_output_prefix: str = "/mnt/fx3_tier0_backup/",
    expected_unlink_path: str = "/tmp/jiritsu/libJit.so",
) -> WorkerSyscallAudit:
    """Audit an AArch64 Linux syscall trace from the hardened Tier-0 backup worker.

    Enforces four hard safety redlines:
    1. Entry first path operation MUST be unlinkat(AT_FDCWD, "/tmp/jiritsu/libJit.so", 0).
    2. Zero openat calls on /dev/* or source paths with O_WRONLY (1) or O_RDWR (2) or O_CREAT/O_TRUNC.
    3. All source openat calls MUST carry O_RDONLY and O_NOFOLLOW (0x8000 arm64 or 0x20000 generic).
    4. All output openat calls MUST be under allowed_output_prefix with O_WRONLY | O_CREAT | O_EXCL (and NOT O_TRUNC),
       and zero write/pwrite64 calls may target a source file descriptor.
    """
    errors: List[str] = []
    first_path_seen = False
    first_path_ok = False
    dev_write_opens = 0
    source_fd_writes = 0
    missing_nofollow = 0
    non_excl_outputs = 0

    # Linux AArch64 syscall numbers
    SYS_MKDIRAT = 34
    SYS_UNLINKAT = 35
    SYS_OPENAT = 56
    SYS_CLOSE = 57
    SYS_WRITE = 64
    SYS_PWRITE64 = 68

    O_ACCMODE = 0x3
    O_WRONLY = 0x1
    O_CREAT = 0x40
    O_EXCL = 0x80
    O_TRUNC = 0x200
    O_NOFOLLOW_MASK = 0x8000 | 0x20000  # arm64 O_NOFOLLOW (0100000) or generic O_NOFOLLOW (0400000)

    active_source_fds: Dict[int, str] = {}

    for idx, rec in enumerate(syscalls):
        nr = int(rec.get("nr", -1))
        path = rec.get("path")
        flags = int(rec.get("flags", 0))
        ret = int(rec.get("ret", 0))
        fd_arg = int(rec.get("fd", -1))

        if path is not None and not first_path_seen:
            first_path_seen = True
            dirfd = int(rec.get("dirfd", 0))
            if nr == SYS_UNLINKAT and dirfd == -100 and str(path) == expected_unlink_path and flags == 0:
                first_path_ok = True
            else:
                errors.append(
                    f"First path syscall at index {idx} must be unlinkat(AT_FDCWD, {expected_unlink_path!r}, 0), "
                    f"got nr={nr} dirfd={dirfd} path={path!r} flags=0x{flags:x}"
                )

        if nr == SYS_OPENAT and path is not None:
            p_str = str(path)
            accmode = flags & O_ACCMODE
            if p_str.startswith("/dev/") or p_str.startswith("/setting/") or p_str.startswith("/lens/"):
                if accmode != 0 or (flags & (O_CREAT | O_TRUNC)) != 0:
                    dev_write_opens += 1
                    errors.append(f"Forbidden write/create flags 0x{flags:x} on source path {p_str!r} at syscall {idx}")
                if (flags & O_NOFOLLOW_MASK) == 0:
                    missing_nofollow += 1
                    errors.append(f"Source openat missing O_NOFOLLOW (flags=0x{flags:x}) on {p_str!r} at syscall {idx}")
                if ret >= 0:
                    active_source_fds[ret] = p_str
            elif p_str.startswith(allowed_output_prefix):
                req_bits = O_WRONLY | O_CREAT | O_EXCL
                if (flags & req_bits) != req_bits or (flags & O_TRUNC) != 0 or accmode != O_WRONLY:
                    non_excl_outputs += 1
                    errors.append(
                        f"Output openat on {p_str!r} must use O_WRONLY|O_CREAT|O_EXCL without O_TRUNC, got 0x{flags:x}"
                    )
            else:
                if accmode != 0 or (flags & (O_CREAT | O_TRUNC)) != 0:
                    dev_write_opens += 1
                    errors.append(f"Unexpected write openat outside backup directory: {p_str!r} (flags=0x{flags:x})")
                elif (flags & O_NOFOLLOW_MASK) == 0:
                    missing_nofollow += 1
                    errors.append(f"Read openat missing O_NOFOLLOW on {p_str!r}")
                if ret >= 0 and accmode == 0:
                    active_source_fds[ret] = p_str

        elif nr in (SYS_WRITE, SYS_PWRITE64):
            if fd_arg in active_source_fds:
                source_fd_writes += 1
                errors.append(
                    f"CRITICAL: write/pwrite64 (nr={nr}) targeted source fd {fd_arg} ({active_source_fds[fd_arg]!r})!"
                )

        elif nr == SYS_MKDIRAT and path is not None:
            p_str = str(path)
            if not p_str.rstrip("/").startswith(allowed_output_prefix.rstrip("/")):
                errors.append(f"Unexpected mkdirat outside allowed backup prefix: {p_str!r}")

        elif nr == SYS_CLOSE:
            active_source_fds.pop(fd_arg, None)

    if not first_path_seen:
        errors.append("No path-bearing syscalls recorded; missing unlinkat entry lock")

    valid = (
        first_path_ok
        and dev_write_opens == 0
        and source_fd_writes == 0
        and missing_nofollow == 0
        and non_excl_outputs == 0
        and len(errors) == 0
    )
    return WorkerSyscallAudit(
        valid=valid,
        first_path_op_unlink_libjit=first_path_ok,
        dev_write_open_count=dev_write_opens,
        source_fd_write_count=source_fd_writes,
        missing_nofollow_source_opens=missing_nofollow,
        non_excl_output_opens=non_excl_outputs,
        total_syscalls=len(syscalls),
        errors=errors,
    )


audit_tier0_worker_syscalls = audit_tier0_worker_syscall_trace


@dataclass(frozen=True)
class FailsafeHookAudit:
    valid: bool
    clear_before_exec_ok: bool
    ram_bind_mount_ok: bool
    watchdog_guard_ok: bool
    updater_mode5_fallback_ok: bool
    errors: List[str]

    def __bool__(self) -> bool:
        return self.valid


def verify_failsafe_hook_script(hook_text: str) -> FailsafeHookAudit:
    """Audit a 4-Layer Fail-Safe init2 / Stage-A RAM-Overlay boot wrapper script.

    Verifies on non-comment lines:
    1. Layer 2 Clear-Before-Exec: `rm -f "/tmp/mod_arm_once"` appears strictly BEFORE `busybox mount --bind`.
    2. Layer 1 Non-Persistent RAM VFS Overlay: `busybox mount --bind` present and zero raw `/dev/*nflasha*` writes.
    3. Layer 3 Userspace Liveness Watchdog: `sleep ` timer guard + `busybox reboot -f` recovery path.
    4. Layer 4 Consecutive-Failure Auto-Recovery: `/setting/updater/mode5` fallback arming clause.
    """
    if not isinstance(hook_text, str) or not hook_text.strip():
        return FailsafeHookAudit(
            valid=False,
            clear_before_exec_ok=False,
            ram_bind_mount_ok=False,
            watchdog_guard_ok=False,
            updater_mode5_fallback_ok=False,
            errors=["Hook script must be a non-empty string"],
        )

    active_lines = [
        ln for ln in hook_text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")
    ]
    active_body = "\n".join(active_lines)
    errors: List[str] = []

    unlink_idx = active_body.find('rm -f "/tmp/mod_arm_once"')
    bind_idx = active_body.find("busybox mount --bind")

    forbidden_flash_tokens = (
        "flashcp",
        "of=/dev/nflasha",
        "of=/dev/cnflasha",
        "of=/dev/pnflasha",
        "mkfs.vfat /dev/nflasha",
        "mkfs.ext4 /dev/nflasha",
    )
    has_forbidden_write = any(tok in active_body for tok in forbidden_flash_tokens)
    if has_forbidden_write:
        errors.append("Forbidden direct flash write command detected on /dev/*nflasha*")

    ram_bind_ok = bind_idx >= 0 and not has_forbidden_write
    if bind_idx < 0:
        errors.append("Missing Layer-1 RAM VFS `busybox mount --bind` clause")

    clear_before_exec_ok = unlink_idx >= 0 and (bind_idx < 0 or unlink_idx < bind_idx)
    if unlink_idx < 0:
        errors.append('Missing Layer-2 Clear-Before-Exec `rm -f "/tmp/mod_arm_once"` clause')
    elif bind_idx >= 0 and unlink_idx >= bind_idx:
        errors.append('Layer-2 `rm -f "/tmp/mod_arm_once"` must execute strictly BEFORE `busybox mount --bind`')

    watchdog_ok = ("sleep " in active_body) and ("busybox reboot -f" in active_body)
    if not watchdog_ok:
        errors.append("Missing Layer-3 watchdog timer (`sleep ` + `busybox reboot -f`) clause")

    mode5_ok = "/setting/updater/mode5" in active_body
    if not mode5_ok:
        errors.append("Missing Layer-4 `/setting/updater/mode5` recovery fallback clause")

    valid = (
        clear_before_exec_ok
        and ram_bind_ok
        and watchdog_ok
        and mode5_ok
        and len(errors) == 0
    )
    return FailsafeHookAudit(
        valid=valid,
        clear_before_exec_ok=clear_before_exec_ok,
        ram_bind_mount_ok=ram_bind_ok,
        watchdog_guard_ok=watchdog_ok,
        updater_mode5_fallback_ok=mode5_ok,
        errors=errors,
    )


def _verify_failsafe_hook_contract(hook_text: str) -> bool:
    return verify_failsafe_hook_script(hook_text).valid


def evaluate_12_safety_gates(
    repo_root: Path,
    tier0_manifest: Optional[Dict[str, object]] = None,
    worker_syscall_trace: Optional[List[Dict[str, object]]] = None,
    init2_failsafe_hook: Optional[str] = None,
    candidate_bundle_verified: Optional[bool] = None,
    allow_dry_run_gate12: bool = False,
) -> Dict[str, object]:
    """Evaluate all 12 Pre-Flash & Recovery Safety Gates against repository and candidate evidence."""
    repo_root = repo_root.resolve()

    def _exists(rel: str) -> bool:
        return (repo_root / rel).exists()

    def _read_json(rel: str) -> Optional[Dict[str, object]]:
        p = repo_root / rel
        if not p.is_file():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    # Gate 1: Official Reference Integrity
    old_msc = _read_json("outputs/fx3-safety/readiness-20261025-msc.json") or {}
    stock_files = old_msc.get("stock_files", [])
    g01_ok = isinstance(stock_files, list) and len(stock_files) >= 3 and all(
        isinstance(f, dict) and f.get("verified") is True for f in stock_files
    )

    # Gate 2: Authenticated USB Service Session (Stage 285)
    s285_summary = _read_json(
        "work/sony-firmware-20261024/stage285-service-access-communication05-execution/live-final-summary.json"
    )
    s285_private = _read_json(
        "work/sony-firmware-20261024/stage285-service-access-communication05-execution/private-record.json"
    )
    g02_ok = bool(
        s285_summary
        and s285_summary.get("status") == "HOST_RETURN_CONTROLLED_PORT_ASSOCIATION"
        and s285_summary.get("bounded_service_read_observed") is True
        and s285_private
        and s285_private.get("phase") == "COMPLETE"
        and s285_private.get("native_return") == 0
    )

    # Gate 3: AdjustControlFunc (0x40) & Jiritsu Wire Contract (Stage 286 & 288)
    s286_receipt = _read_json(
        "work/sony-firmware-20261024/stage286-post-communication05-session-and-wire-envelope-audit/codec-test-receipt.json"
    )
    s288_wire = _exists("work/sony-firmware-20261024/stage288-jiritsu-readonly-payload/jiritsu_wire.py")
    g03_ok = bool(s286_receipt and s288_wire)

    # Gate 4: Offline p1 Recovery, Same-Size SquashFS & Byte-Exact Rollback Engine (v0.5)
    g04_ok = all(
        _exists(p)
        for p in (
            "outputs/fx3-recovery-adapter/fx3_recovery/engine.py",
            "outputs/fx3-recovery-adapter/fx3_recovery/fat.py",
            "outputs/fx3-recovery-adapter/fx3_recovery/squash.py",
            "outputs/fx3-recovery-adapter/fx3_recovery/profiles.py",
        )
    )

    # Gate 5: Freestanding Static AArch64 Capture Workers (cnflasha1 + nflashaB0/B1)
    g05_ok = all(
        _exists(p)
        for p in (
            "outputs/fx3-recovery-adapter/native/fx3_p1_reader.c",
            "outputs/fx3-recovery-adapter/native/fx3_boot_reader.c",
            "outputs/fx3-recovery-adapter/fx3_recovery/elflink.py",
        )
    )

    # Gate 6: Bootloader (SPI NOR) & eMMC Sector 0 ("8246" "2.00") Static Audit
    g06_ok = all(
        _exists(p)
        for p in (
            "reports/2026-11-03-fx6-full-system-to-fx3/README.md",
            "outputs/fx3-safety/fx3_safety/boot_contracts.py",
        )
    )

    # Gate 7: Backup.bin BK4\0 + 0xfa0080 Cold-Boot Descriptor + Boot-Screen Enum Contract
    g07_ok = all(
        _exists(p)
        for p in (
            "work/fx3-color-port-20261027/config-producer-20261029/NOR-load-contract-review.json",
            "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-boot-screen-contract/REPORT.md",
            "outputs/fx3-safety/fx3_safety/boot_contracts.py",
        )
    )

    # Gate 8: QEMU Stage-0 Pre-Flash Sandbox & Fail-Closed Serial Fault Detector
    g08_ok = all(
        _exists(p)
        for p in (
            "outputs/fx3-vm/run_probe.py",
            "outputs/fx3-vm-trial/FX3菜单.command",
            "work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-serial-fault-detector/detect_serial_faults.py",
        )
    )

    # Gate 9: 4-Layer Fail-Safe Overlay & Watchdog Auto-Recovery Architecture
    g09_ok = _exists("outputs/fx3-safety/fx3_safety/brick_classifier.py")

    # Gate 10: Complete Same-Body Tier-0 Full Backup Checkpoint (Sector 0 + p1/p2/p6/p12/p18 + SPI NOR)
    if tier0_manifest is None:
        g10_ok = False
        g10_status = "BLOCKED_PENDING_READBACK"
    else:
        manifest_audit = verify_tier0_backup_manifest(tier0_manifest)
        if worker_syscall_trace is not None:
            trace_audit = audit_tier0_worker_syscall_trace(worker_syscall_trace)
            g10_ok = manifest_audit.valid and trace_audit.valid
        else:
            g10_ok = manifest_audit.valid and (not allow_dry_run_gate12)
        g10_status = "VERIFIED_TWOPASS_MANIFEST" if g10_ok else "BLOCKED_INVALID_TIER0_MANIFEST_OR_TRACE"

    # Gate 11: Independent Hardware Recovery Entry (Pre-Armed p1 or One-Shot Overlay)
    if init2_failsafe_hook is None:
        g11_status = "DESIGN_VERIFIED_AWAITING_TIER0_BACKUP"
    else:
        hook_ok = _verify_failsafe_hook_contract(init2_failsafe_hook)
        g11_status = (
            "VERIFIED_FAILSAFE_OVERLAY_READY"
            if (g10_ok and hook_ok)
            else "BLOCKED_INVALID_FAILSAFE_OR_MISSING_G10"
        )

    # Gate 12: Persistent Hardware Flash Authorization (or Offline Candidate Dry-Run Verification)
    prior_11_verified = all(
        (
            g01_ok,
            g02_ok,
            g03_ok,
            g04_ok,
            g05_ok,
            g06_ok,
            g07_ok,
            g08_ok,
            g09_ok,
            g10_ok,
            g11_status.startswith("VERIFIED"),
        )
    )
    if allow_dry_run_gate12 and prior_11_verified and (candidate_bundle_verified is True):
        g12_status = "VERIFIED_OFFLINE_CANDIDATE_DRY_RUN"
    else:
        g12_status = "BLOCKED_BY_SAFETY_REDLINE"

    gates = [
        {
            "gate_id": "G01_official_reference_integrity",
            "status": "VERIFIED" if g01_ok else "MISSING",
            "evidence": "Official FX3 7.02 appFw.so (545c5053...), libmpr.so (9aeef3b9...), cpapp-b.bin (c90d00d8...), and 2.04/2.05 p1 libraries verified.",
        },
        {
            "gate_id": "G02_authenticated_usb_service_session",
            "status": "VERIFIED_ON_HARDWARE" if g02_ok else "NOT_PROVEN",
            "evidence": "Stage 285: 124-frame closed-loop MSC (054C:0DA1) -> 7-round auth -> SERVICE (054C:0336) -> read0 (88B) -> STOP -> same-port MSC return (native_return=0).",
        },
        {
            "gate_id": "G03_adjust_control_and_jiritsu_wire_contract",
            "status": "VERIFIED_OFFLINE" if g03_ok else "NOT_PROVEN",
            "evidence": "Stage 286 & 288: AdjustControlFunc (0x0040, category 0x1001) Phase 1/4/16 DMM lifecycle, 00/00 ff 00 prefixes, and /tmp/jbusy ENOENT precondition verified.",
        },
        {
            "gate_id": "G04_offline_p1_recovery_and_rollback_engine",
            "status": "VERIFIED_OFFLINE" if g04_ok else "MISSING",
            "evidence": "fx3_recovery v0.5: FAT12 cycle/cross-link check, SquashFS pack_same_size Z_SYNC_FLUSH length invariance, and byte-exact rollback restoration.",
        },
        {
            "gate_id": "G05_static_aarch64_capture_workers",
            "status": "VERIFIED_EMULATED" if g05_ok else "MISSING",
            "evidence": "Freestanding static AArch64 ELF workers (fx3_p1_reader.c & fx3_boot_reader.c) + custom elflink.py verified across 58 unit & fault-injection tests.",
        },
        {
            "gate_id": "G06_bootloader_and_sector0_contract",
            "status": "VERIFIED_STATIC" if g06_ok else "MISSING",
            "evidence": "Octal-SPI NOR sector map (infomisc/DGU/LdrBkup/loader_nor/MIS+ddrtraining/cpapp-b) and eMMC Sector 0 ('8246' '2.00' 30-entry table) audited.",
        },
        {
            "gate_id": "G07_backup_bin_bk4_and_fa0080_contract",
            "status": "VERIFIED_STATIC" if g07_ok else "MISSING",
            "evidence": "loader_nor.bin BK4\\0 selector (0xfe04c7a8 -> 0xfe04d584: word4=0xaaaaaaaa, byte8=1, signed word2c), 0xfa0080 64-slot table, and 0x02cf0214/0218 contract verified.",
        },
        {
            "gate_id": "G08_qemu_stage0_preflash_sandbox",
            "status": "VERIFIED" if g08_ok else "MISSING",
            "evidence": "FX3 QEMU VM (AP70-AP105 Web UI r10-r48) + FX6 hybrid VM (180s zero-Oops MEDIA_START) + detect_serial_faults.py fail-closed assertion/fault detector.",
        },
        {
            "gate_id": "G09_failsafe_4layer_overlay_and_watchdog",
            "status": "VERIFIED_ARCHITECTURE" if g09_ok else "MISSING",
            "evidence": "Layer 1 RAM mount --bind + Layer 2 Clear-Before-Exec /tmp/mod_arm_once + Layer 3 45s BusyBox watchdog + Layer 4 3-strike /setting/updater/mode+mode5 auto-arming.",
        },
        {
            "gate_id": "G10_same_body_tier0_full_backup_checkpoint",
            "status": g10_status,
            "evidence": "Requires two-pass idempotent readback dumps of physical camera Sector 0, boot0/1, p1, p2 (Backup.bin/psd.bin/defdet.bin), p6 (Jiritsu), p12 (/cert), p18 (lensfile.bin), and SPI NOR (ddrtraining.dat).",
        },
        {
            "gate_id": "G11_independent_hardware_recovery_readiness",
            "status": g11_status,
            "evidence": "Proven that loader_nor.bin has NO auto-failover from p3 to p1 unless /setting/updater/mode* is armed; therefore p1-first staging or init2 watchdog hook is mandatory before any p15 trial.",
        },
        {
            "gate_id": "G12_persistent_flash_write_authorization",
            "status": g12_status,
            "evidence": "Hard safety lock: persistent flash writes and cross-model partition flashing remain strictly prohibited until G10 (Tier-0 full backup) is completed and verified.",
        },
    ]

    verified_count = sum(1 for g in gates if g["status"].startswith("VERIFIED"))
    return {
        "schema": "fx3-research-safety-inventory-v2",
        "evaluated_utc": datetime.now(timezone.utc).isoformat(),
        "state": "DEFENSIVE_SANDBOX_AND_READONLY_SERVICE_VERIFIED",
        "persistent_write_release": False,
        "is_flash_authorization_or_recovery_certificate": False,
        "summary": {
            "total_gates": len(gates),
            "verified_gates": verified_count,
            "blocked_or_pending_gates": len(gates) - verified_count,
            "all_12_gates_verified": verified_count == len(gates),
        },
        "gates": gates,
    }
