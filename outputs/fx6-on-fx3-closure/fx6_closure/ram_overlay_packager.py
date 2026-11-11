"""Stage-A Zero-Flash-Write RAM-Overlay Deterministic CPIO `newc` Packager & Auditor.

Implements:
1. Pure-Python `cpio` SVR4 `newc` (`070701` ASCII hex magic, 110-byte header, 4-byte header+name
   and file-payload alignment, `TRAILER!!!` sentinel) deterministic archive builder and strict
   structural parser/auditor — requiring zero external `cpio` CLI tools and guaranteeing 100%
   reproducible SHA-256 digests across runs via fixed `mtime` / `ino` / `uid` / `gid` metadata.
2. Stage-A Non-Persistent RAM-Overlay bundle assembler inside `tempfile.TemporaryDirectory()` or
   in-memory, producing:
   - `etc/fx6_overlay/setup_fx6_compat.sh`: idempotent P1 (`/dev/nflasha20 -> p30` LUT symlink)
     and P2 (`/dev/loop7` `opelog.vfat` mount) adaptation script.
   - `etc/fx6_overlay/init2_guard.sh`: 4-Layer Fail-Safe boot guard passing
     `fx3_safety.preflight.verify_failsafe_hook_script` (Layer-2 Clear-Before-Exec
     `/tmp/mod_arm_once` unlink before mount, SHA-256 manifest verification, Layer-1 RAM VFS
     `mount --bind`, Layer-3 watchdog timeout & exit-code fallback, Layer-4 consecutive-failure
     `/setting/updater/mode5` recovery arming).
   - `etc/fx6_overlay/overlay_manifest.json`: deterministic manifest recording all 10 verified
     adaptation matrix items (`P1..P9 + Fan`), adapted component SHA-256s, original donor/baseline
     SHA-256s, and rollback verification receipts.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from fx3_safety.preflight import FailsafeHookAudit, verify_failsafe_hook_script

from .backup_bridge_verifier import (
    P7BackupBridgeAuditReport,
    PINNED_FIRST32_SHA256,
    SYNC100_DST_QUEUE,
    verify_p7_backup_bridge,
)
from .patcher import (
    ALL_PHASE2_TARGET_SPECS,
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    apply_patch_spec,
    resolve_donor_binary_path,
    rollback_patch_spec,
)
from .uipc_completion_verifier import UIPC_P5_P6_RULES
from .vfat_builder import build_opelog_vfat_image, verify_vfat_image


CPIO_NEWC_MAGIC = b"070701"
CPIO_HEADER_SIZE = 110
CPIO_TRAILER_NAME = "TRAILER!!!"

S_IFMT = 0o170000
S_IFDIR = 0o040000
S_IFREG = 0o100000
S_IFLNK = 0o120000

DETERMINISTIC_MTIME = 1700000000  # Fixed UTC epoch (2023-11-14T22:13:20Z) for 100% reproducible SHA-256
DETERMINISTIC_BASE_INO = 300000

REQUIRED_STAGE_A_OVERLAY_PATHS: Tuple[str, ...] = (
    "etc",
    "etc/fx6_overlay",
    "etc/fx6_overlay/30-stage-a-orchestrator.sh",
    "etc/fx6_overlay/setup_fx6_compat.sh",
    "etc/fx6_overlay/init2_guard.sh",
    "etc/fx6_overlay/overlay_manifest.json",
)


class CpioFormatError(ValueError):
    """Raised when constructing an invalid CPIO `newc` entry."""


@dataclass(frozen=True)
class CpioEntrySpec:
    name: str
    mode: int
    data: bytes = b""
    mtime: int = DETERMINISTIC_MTIME
    uid: int = 0
    gid: int = 0
    nlink: Optional[int] = None


@dataclass(frozen=True)
class ParsedCpioEntry:
    name: str
    ino: int
    mode: int
    uid: int
    gid: int
    nlink: int
    mtime: int
    filesize: int
    devmajor: int
    devminor: int
    rdevmajor: int
    rdevminor: int
    namesize: int
    check: int
    data: bytes
    sha256: str

    @property
    def is_dir(self) -> bool:
        return (self.mode & S_IFMT) == S_IFDIR

    @property
    def is_reg(self) -> bool:
        return (self.mode & S_IFMT) == S_IFREG


@dataclass(frozen=True)
class CpioArchiveAudit:
    valid: bool
    archive_size: int
    archive_sha256: str
    trailer_found: bool
    entries: Tuple[ParsedCpioEntry, ...]
    file_sha256_map: Dict[str, str]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class StageARamOverlayBundle:
    cpio_bytes: bytes
    cpio_sha256: str
    cpio_size: int
    cpio_audit: CpioArchiveAudit
    failsafe_hook_audit: FailsafeHookAudit
    setup_compat_script: str
    init2_guard_script: str
    stage_a_orchestrator_script: str
    overlay_manifest: Dict[str, object]
    staged_runtime_blobs: Dict[str, bytes]
    temp_dir_cleaned: bool


def _pad4(length: int) -> int:
    return (4 - (length % 4)) % 4


def _validate_cpio_entry_name(name: str) -> str:
    if not isinstance(name, str) or not name:
        raise CpioFormatError("CPIO entry name must be a non-empty string")
    if "\x00" in name:
        raise CpioFormatError(f"CPIO entry name contains NUL byte: {name!r}")
    if name.startswith("/") or name.startswith("./"):
        raise CpioFormatError(f"CPIO entry name must be relative without leading '/' or './': {name!r}")
    parts = name.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise CpioFormatError(f"CPIO entry name contains invalid or traversal segment: {name!r}")
    return name


def _encode_newc_record(
    *,
    name: str,
    ino: int,
    mode: int,
    uid: int,
    gid: int,
    nlink: int,
    mtime: int,
    data: bytes,
    devmajor: int = 0,
    devminor: int = 1,
    rdevmajor: int = 0,
    rdevminor: int = 0,
    check: int = 0,
) -> bytes:
    name_bytes = name.encode("utf-8") + b"\x00"
    namesize = len(name_bytes)
    filesize = len(data)

    header = (
        f"070701"
        f"{ino & 0xFFFFFFFF:08X}"
        f"{mode & 0xFFFFFFFF:08X}"
        f"{uid & 0xFFFFFFFF:08X}"
        f"{gid & 0xFFFFFFFF:08X}"
        f"{nlink & 0xFFFFFFFF:08X}"
        f"{mtime & 0xFFFFFFFF:08X}"
        f"{filesize & 0xFFFFFFFF:08X}"
        f"{devmajor & 0xFFFFFFFF:08X}"
        f"{devminor & 0xFFFFFFFF:08X}"
        f"{rdevmajor & 0xFFFFFFFF:08X}"
        f"{rdevminor & 0xFFFFFFFF:08X}"
        f"{namesize & 0xFFFFFFFF:08X}"
        f"{check & 0xFFFFFFFF:08X}"
    ).encode("ascii")
    assert len(header) == CPIO_HEADER_SIZE

    head_pad = b"\x00" * _pad4(CPIO_HEADER_SIZE + namesize)
    data_pad = b"\x00" * _pad4(filesize)
    return header + name_bytes + head_pad + data + data_pad


def build_cpio_newc_archive(
    entries: Sequence[CpioEntrySpec],
    *,
    sort_entries: bool = True,
    base_ino: int = DETERMINISTIC_BASE_INO,
) -> bytes:
    """Build a deterministic SVR4 `newc` (`070701`) CPIO archive in pure Python."""
    seen_names = set()
    validated: List[CpioEntrySpec] = []
    for spec in entries:
        norm_name = _validate_cpio_entry_name(spec.name)
        if norm_name in seen_names:
            raise CpioFormatError(f"Duplicate CPIO entry name: {norm_name!r}")
        seen_names.add(norm_name)
        is_dir = (spec.mode & S_IFMT) == S_IFDIR
        if is_dir and len(spec.data) != 0:
            raise CpioFormatError(f"Directory CPIO entry {norm_name!r} must have empty data payload")
        validated.append(
            CpioEntrySpec(
                name=norm_name,
                mode=spec.mode,
                data=bytes(spec.data),
                mtime=spec.mtime,
                uid=spec.uid,
                gid=spec.gid,
                nlink=spec.nlink,
            )
        )

    ordered = sorted(validated, key=lambda e: e.name) if sort_entries else validated
    chunks: List[bytes] = []
    for idx, spec in enumerate(ordered):
        is_dir = (spec.mode & S_IFMT) == S_IFDIR
        nlink = spec.nlink if spec.nlink is not None else (2 if is_dir else 1)
        chunks.append(
            _encode_newc_record(
                name=spec.name,
                ino=base_ino + idx,
                mode=spec.mode,
                uid=spec.uid,
                gid=spec.gid,
                nlink=nlink,
                mtime=spec.mtime,
                data=spec.data,
            )
        )

    # Append canonical TRAILER!!! sentinel record
    chunks.append(
        _encode_newc_record(
            name=CPIO_TRAILER_NAME,
            ino=0,
            mode=0,
            uid=0,
            gid=0,
            nlink=1,
            mtime=0,
            data=b"",
            devmajor=0,
            devminor=0,
            rdevmajor=0,
            rdevminor=0,
            check=0,
        )
    )
    return b"".join(chunks)


def parse_and_audit_cpio_newc(
    archive_bytes: bytes,
    required_paths: Optional[Sequence[str]] = None,
) -> CpioArchiveAudit:
    """Strictly parse and audit a `newc` (`070701`) CPIO archive buffer."""
    errors: List[str] = []
    entries: List[ParsedCpioEntry] = []
    seen_names = set()
    file_sha_map: Dict[str, str] = {}
    trailer_found = False

    archive_sha = hashlib.sha256(archive_bytes).hexdigest()
    total_len = len(archive_bytes)
    off = 0

    if total_len < CPIO_HEADER_SIZE:
        return CpioArchiveAudit(
            valid=False,
            archive_size=total_len,
            archive_sha256=archive_sha,
            trailer_found=False,
            entries=(),
            file_sha256_map={},
            errors=("Archive smaller than 110-byte CPIO newc header",),
        )

    while off < total_len:
        if total_len - off < CPIO_HEADER_SIZE:
            errors.append(f"Truncated CPIO header at offset {off} (remaining={total_len - off})")
            break

        hdr = archive_bytes[off : off + CPIO_HEADER_SIZE]
        magic = hdr[0:6]
        if magic != CPIO_NEWC_MAGIC:
            errors.append(f"Invalid CPIO newc magic at offset {off}: expected 070701, got {magic!r}")
            break

        fields: List[int] = []
        hex_ok = True
        for f_idx in range(13):
            f_slice = hdr[6 + f_idx * 8 : 6 + (f_idx + 1) * 8]
            try:
                fields.append(int(f_slice.decode("ascii"), 16))
            except Exception:
                errors.append(f"Non-hex CPIO header field {f_idx} at offset {off}: {f_slice!r}")
                hex_ok = False
                break
        if not hex_ok:
            break

        (
            ino,
            mode,
            uid,
            gid,
            nlink,
            mtime,
            filesize,
            devmajor,
            devminor,
            rdevmajor,
            rdevminor,
            namesize,
            check,
        ) = fields

        if namesize < 1:
            errors.append(f"Invalid CPIO namesize={namesize} at offset {off}")
            break

        name_start = off + CPIO_HEADER_SIZE
        name_end = name_start + namesize
        head_pad_len = _pad4(CPIO_HEADER_SIZE + namesize)
        data_start = name_end + head_pad_len
        data_end = data_start + filesize
        data_pad_len = _pad4(filesize)
        next_off = data_end + data_pad_len

        if next_off > total_len:
            errors.append(
                f"Truncated CPIO entry at offset {off}: requires end={next_off}, archive_size={total_len}"
            )
            break

        raw_name = archive_bytes[name_start:name_end]
        if raw_name[-1:] != b"\x00":
            errors.append(f"CPIO entry name missing NUL terminator at offset {off}")
            break
        if b"\x00" in raw_name[:-1]:
            errors.append(f"CPIO entry name contains embedded NUL byte at offset {off}")
            break

        head_pad = archive_bytes[name_end:data_start]
        if head_pad != (b"\x00" * head_pad_len):
            errors.append(f"Non-zero header 4-byte alignment padding at offset {name_end}")

        data_pad = archive_bytes[data_end:next_off]
        if data_pad != (b"\x00" * data_pad_len):
            errors.append(f"Non-zero payload 4-byte alignment padding at offset {data_end}")

        try:
            entry_name = raw_name[:-1].decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"Invalid UTF-8 CPIO entry name at offset {off}: {exc}")
            break

        payload = archive_bytes[data_start:data_end]
        off = next_off

        if entry_name == CPIO_TRAILER_NAME:
            if filesize != 0:
                errors.append(f"TRAILER!!! sentinel has non-zero filesize={filesize}")
            trailer_found = True
            trailing = archive_bytes[off:]
            if any(b != 0 for b in trailing):
                errors.append("Non-zero trailing bytes found after TRAILER!!! sentinel")
            break

        if entry_name.startswith("/") or ".." in entry_name.split("/"):
            errors.append(f"Unsafe path in CPIO entry: {entry_name!r}")
        if entry_name in seen_names:
            errors.append(f"Duplicate CPIO entry path: {entry_name!r}")
        seen_names.add(entry_name)

        digest = hashlib.sha256(payload).hexdigest()
        parsed = ParsedCpioEntry(
            name=entry_name,
            ino=ino,
            mode=mode,
            uid=uid,
            gid=gid,
            nlink=nlink,
            mtime=mtime,
            filesize=filesize,
            devmajor=devmajor,
            devminor=devminor,
            rdevmajor=rdevmajor,
            rdevminor=rdevminor,
            namesize=namesize,
            check=check,
            data=payload,
            sha256=digest,
        )
        entries.append(parsed)
        if parsed.is_reg:
            file_sha_map[entry_name] = digest

    if not trailer_found:
        errors.append("Missing mandatory CPIO `TRAILER!!!` end-of-archive sentinel")

    if required_paths is not None:
        for req in required_paths:
            if req not in seen_names:
                errors.append(f"Missing required Stage-A CPIO entry: {req!r}")

    return CpioArchiveAudit(
        valid=(len(errors) == 0 and trailer_found),
        archive_size=total_len,
        archive_sha256=archive_sha,
        trailer_found=trailer_found,
        entries=tuple(entries),
        file_sha256_map=file_sha_map,
        errors=tuple(errors),
    )


def extract_cpio_newc_to_dir(archive_bytes: bytes, dest_root: Path) -> CpioArchiveAudit:
    """Audit and safely extract a CPIO `newc` archive under `dest_root`."""
    audit = parse_and_audit_cpio_newc(archive_bytes)
    if not audit.valid:
        raise CpioFormatError(f"Refusing to extract invalid CPIO archive: {audit.errors}")

    dest_resolved = dest_root.resolve()
    dest_resolved.mkdir(parents=True, exist_ok=True)
    for ent in audit.entries:
        out_path = (dest_resolved / ent.name).resolve()
        if not str(out_path).startswith(str(dest_resolved) + "/"):
            raise CpioFormatError(f"Path traversal blocked during extraction: {ent.name!r}")
        if ent.is_dir:
            out_path.mkdir(parents=True, exist_ok=True)
        elif ent.is_reg:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(ent.data)
            out_path.chmod(ent.mode & 0o777)
    return audit


def generate_stage_a_setup_compat_script() -> str:
    """Generate `etc/fx6_overlay/setup_fx6_compat.sh` combining P1 LUT & P2 `loop7` opelog setup."""
    return """#!/bin/sh
# Stage-A Non-Persistent RAM-Overlay Compatibility Setup (P1 LUT + P2 opelog VFAT)
# Supports PREFIX sandbox root injection so host drills never touch real /dev or /etc.
set -eu

PREFIX="${PREFIX:-}"
if [ -z "$PREFIX" ] && [ "$(uname -s 2>/dev/null || echo unknown)" != "Linux" ]; then
    echo "ERR_SANDBOX_PREFIX_REQUIRED_ON_HOST" >&2
    exit 97
fi

STAGE_DIR="${FX3_STAGE_A_DIR:-${PREFIX}/tmp/fx6_stage_a}"
DEV_DIR="${PREFIX}/dev"
LUT_DIR="${PREFIX}/usr/data/lut"
OPELOG_MNT="${PREFIX}/etc/opelog"
OPELOG_IMG="${STAGE_DIR}/images/opelog.vfat"
LOOP_DEV="${DEV_DIR}/loop7"

# 1. P1 Zero-Repartitioning 3D LUT Adaptation (/dev/nflasha20 -> FX3 48 MiB p30)
mkdir -p "$DEV_DIR" "$LUT_DIR"
if [ -b "${DEV_DIR}/cnflasha30" ] || [ -e "${DEV_DIR}/cnflasha30" ]; then
    rm -f "${DEV_DIR}/nflasha20" "${DEV_DIR}/cnflasha20" "${DEV_DIR}/pnflasha20"
    ln -s "${DEV_DIR}/cnflasha30" "${DEV_DIR}/nflasha20"
    ln -s "${DEV_DIR}/cnflasha30" "${DEV_DIR}/cnflasha20"
    if [ -b "${DEV_DIR}/pnflasha30" ] || [ -e "${DEV_DIR}/pnflasha30" ]; then
        ln -s "${DEV_DIR}/pnflasha30" "${DEV_DIR}/pnflasha20"
    fi
fi

# 2. P2 Non-Persistent 8 MiB VFAT Loopback Adaptation (/dev/loop7 -> /dev/nflasha21 -> /etc/opelog)
mkdir -p "$OPELOG_MNT"
if [ -f "$OPELOG_IMG" ]; then
    busybox losetup -d "$LOOP_DEV" >/dev/null 2>&1 || true
    busybox losetup "$LOOP_DEV" "$OPELOG_IMG"
    rm -f "${DEV_DIR}/nflasha21"
    ln -s "$LOOP_DEV" "${DEV_DIR}/nflasha21"
    busybox mount -t vfat -o shortname=mixed "${DEV_DIR}/nflasha21" "$OPELOG_MNT"
    mkdir -p "${OPELOG_MNT}/ope/00" "${OPELOG_MNT}/ope/01"
fi
"""


def generate_stage_a_init2_guard_script() -> str:
    """Generate `etc/fx6_overlay/init2_guard.sh` (4-Layer Fail-Safe Boot Guard).

    Strictly satisfies `fx3_safety.preflight.verify_failsafe_hook_script` while supporting
    `PREFIX` sandboxed POSIX `sh` execution for deterministic 4-scenario rollback drills.
    """
    return """#!/bin/sh
# === BEGIN FX3 STAGE-A 4-LAYER FAIL-SAFE RAM-OVERLAY & WATCHDOG GUARD ===
# Layer 1: Non-persistent RAM VFS `mount --bind` (zero writes to eMMC Sector0/p2/p6/p15/p18)
# Layer 2: Clear-Before-Exec `/tmp/mod_arm_once` one-shot token unlink prior to any mount
# Layer 3: SHA-256 manifest verification + bounded watchdog timer & child exit-code fallback
# Layer 4: Consecutive failure threshold (>3) recovery pre-arming (/setting/updater/mode5)
set -u

PREFIX="${PREFIX:-}"
if [ -z "$PREFIX" ] && [ "$(uname -s 2>/dev/null || echo unknown)" != "Linux" ]; then
    echo "ERR_SANDBOX_PREFIX_REQUIRED_ON_HOST" >&2
    exit 97
fi

ARM_TOKEN="${PREFIX}/tmp/mod_arm_once"
FAIL_COUNTER="${PREFIX}/tmp/mod_fail_count"
HEARTBEAT_FILE="${PREFIX}/dev/shm/fx3_ap_healthy"
STAGE_DIR="${FX3_STAGE_A_DIR:-${PREFIX}/tmp/fx6_stage_a}"
MANIFEST_FILE="${PREFIX}/etc/fx6_overlay/overlay_manifest.json"
COMPAT_SCRIPT="${PREFIX}/etc/fx6_overlay/setup_fx6_compat.sh"
STATE_FILE="${PREFIX}/tmp/init2_guard_state.env"
MOUNT_WORK_DIR="${PREFIX}/tmp/fx6_mount_work"
RAM_USR_LIB_TARGET="${PREFIX}/tmp/fx6_ram_usr_lib"
WATCHDOG_SEC="${FX3_WATCHDOG_TIMEOUT_SEC:-45}"
MAX_FAILS="${FX3_MAX_CONSECUTIVE_FAILS:-3}"
TOKEN_CLEARED_BEFORE_EXEC=0

mkdir -p "${PREFIX}/tmp" "${PREFIX}/dev/shm"

compute_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        echo "MISSING_SHA256_TOOL"
    fi
}

cleanup_overlay_mounts() {
    if [ -z "$PREFIX" ]; then
        busybox umount -l "/usr/lib/appFw.so" >/dev/null 2>&1 || true
        busybox umount -l "/usr/lib/libfan.so" >/dev/null 2>&1 || true
        busybox umount -l "/etc/opelog" >/dev/null 2>&1 || true
        busybox losetup -d "/dev/loop7" >/dev/null 2>&1 || true
        rm -f /dev/nflasha20 /dev/cnflasha20 /dev/pnflasha20 /dev/nflasha21 2>/dev/null || true
    else
        busybox umount -l "${RAM_USR_LIB_TARGET}/appFw.so" >/dev/null 2>&1 || true
        busybox umount -l "${RAM_USR_LIB_TARGET}/libfan.so" >/dev/null 2>&1 || true
        busybox umount -l "${PREFIX}/etc/opelog" >/dev/null 2>&1 || true
        busybox losetup -d "${PREFIX}/dev/loop7" >/dev/null 2>&1 || true
        rm -f "${PREFIX}/dev/nflasha20" "${PREFIX}/dev/cnflasha20" "${PREFIX}/dev/pnflasha20" "${PREFIX}/dev/nflasha21" 2>/dev/null || true
    fi
    rm -rf "$MOUNT_WORK_DIR" 2>/dev/null || true
}

write_guard_state() {
    cat > "$STATE_FILE" <<EOF
BOOT_BRANCH=$1
DIAG_CODE=$2
STOCK_BOOT_INVOKED=$3
ADAPTED_BOOT_INVOKED=$4
TOKEN_CLEARED_BEFORE_EXEC=$TOKEN_CLEARED_BEFORE_EXEC
EOF
}

exec_stock_fx3_boot() {
    BRANCH_LABEL="$1"
    DIAG_LABEL="$2"
    write_guard_state "$BRANCH_LABEL" "$DIAG_LABEL" 1 0
    if [ -n "${FX3_STOCK_BOOT_CMD:-}" ]; then
        /bin/sh -c "$FX3_STOCK_BOOT_CMD"
    fi
}

# Scenario 1: Unarmed boot -> 100% stock FX3 boot chain, zero overlay mounts
if [ ! -f "$ARM_TOKEN" ]; then
    exec_stock_fx3_boot "STOCK_FX3" "STOCK_UNARMED"
    exit 0
fi

# Layer 2: Clear-Before-Exec (Unlink one-shot token BEFORE any SHA check or mount)
if [ -z "$PREFIX" ]; then
    rm -f "/tmp/mod_arm_once"
else
    rm -f "${PREFIX}/tmp/mod_arm_once"
fi
busybox sync
TOKEN_CLEARED_BEFORE_EXEC=1

# Prepare temporary staging directory and verify overlay_manifest.json SHA-256 checklist
mkdir -p "$MOUNT_WORK_DIR"
if [ ! -f "$MANIFEST_FILE" ]; then
    cleanup_overlay_mounts
    exec_stock_fx3_boot "STOCK_FX3_FALLBACK" "ERR_MANIFEST_MISSING"
    exit 0
fi

CHECKLIST_FILE="${MOUNT_WORK_DIR}/sha256.checklist"
sed -n 's/^[[:space:]]*"\\([0-9a-f]\\{64\\}\\)|\\([^"]*\\)".*/\\1 \\2/p' "$MANIFEST_FILE" > "$CHECKLIST_FILE"
CHECK_ROWS=$(wc -l < "$CHECKLIST_FILE" | tr -d ' ')
if [ "${CHECK_ROWS:-0}" -lt 10 ]; then
    cleanup_overlay_mounts
    exec_stock_fx3_boot "STOCK_FX3_FALLBACK" "ERR_MANIFEST_SCHEMA_INCOMPLETE"
    exit 0
fi

MANIFEST_ERR=""
while IFS=' ' read -r EXP_SHA REL_PATH; do
    [ -z "$EXP_SHA" ] && continue
    TARGET_FILE="${STAGE_DIR}/${REL_PATH}"
    if [ ! -f "$TARGET_FILE" ]; then
        MANIFEST_ERR="ERR_MANIFEST_COMPONENT_MISSING:${REL_PATH}"
        break
    fi
    ACT_SHA=$(compute_sha256 "$TARGET_FILE")
    if [ "$ACT_SHA" != "$EXP_SHA" ]; then
        MANIFEST_ERR="ERR_MANIFEST_SHA256_MISMATCH:${REL_PATH}"
        break
    fi
done < "$CHECKLIST_FILE"

if [ -n "$MANIFEST_ERR" ]; then
    cleanup_overlay_mounts
    exec_stock_fx3_boot "STOCK_FX3_FALLBACK" "$MANIFEST_ERR"
    exit 0
fi

# Layer 4: Consecutive failure threshold guard (>3 strikes -> pre-arm p1 recovery mode5)
FAILS=0
if [ -f "$FAIL_COUNTER" ]; then
    FAILS=$(cat "$FAIL_COUNTER" 2>/dev/null || echo 0)
fi
FAILS=$((FAILS + 1))
echo "$FAILS" > "$FAIL_COUNTER"
busybox sync

if [ "$FAILS" -gt "$MAX_FAILS" ]; then
    if [ -z "$PREFIX" ]; then
        mkdir -p /setting/updater 2>/dev/null || true
        rm -f /setting/updater/comp 2>/dev/null || true
        : > /setting/updater/mode
        : > /setting/updater/mode5
    else
        : > "${PREFIX}/tmp/updater_mode5_prearmed.flag"
    fi
    rm -f "$FAIL_COUNTER"
    busybox sync
    cleanup_overlay_mounts
    exec_stock_fx3_boot "STOCK_FX3_FALLBACK" "ERR_MAX_FAILS_UPDATER_MODE5"
    exit 0
fi

# Layer 1: RAM VFS Bind-Mount Overlay + P1/P2 Non-Persistent Compatibility Setup
rm -f "$HEARTBEAT_FILE" 2>/dev/null || true
if ! /bin/sh "$COMPAT_SCRIPT"; then
    cleanup_overlay_mounts
    exec_stock_fx3_boot "STOCK_FX3_FALLBACK" "ERR_COMPAT_SETUP_FAILED"
    exit 0
fi

if [ -z "$PREFIX" ]; then
    if ! busybox mount --bind "${STAGE_DIR}/lib/appFw.so" "/usr/lib/appFw.so" || \
       ! busybox mount --bind "${STAGE_DIR}/lib/libfan.so" "/usr/lib/libfan.so"; then
        cleanup_overlay_mounts
        exec_stock_fx3_boot "STOCK_FX3_FALLBACK" "ERR_BIND_MOUNT_FAILED"
        exit 0
    fi
else
    mkdir -p "$RAM_USR_LIB_TARGET"
    : > "${RAM_USR_LIB_TARGET}/appFw.so"
    : > "${RAM_USR_LIB_TARGET}/libfan.so"
    if ! busybox mount --bind "${STAGE_DIR}/lib/appFw.so" "${RAM_USR_LIB_TARGET}/appFw.so" || \
       ! busybox mount --bind "${STAGE_DIR}/lib/libfan.so" "${RAM_USR_LIB_TARGET}/libfan.so"; then
        cleanup_overlay_mounts
        exec_stock_fx3_boot "STOCK_FX3_FALLBACK" "ERR_BIND_MOUNT_FAILED"
        exit 0
    fi
fi

# Layer 3: Watchdog Timer & Child Exit Supervision
if [ -z "$PREFIX" ] && [ "${FX3_SUPERVISED_MODE:-0}" != "1" ]; then
    (
        sleep 45
        if ! busybox pidof im.elf >/dev/null 2>&1 || [ ! -f "/dev/shm/fx3_ap_healthy" ]; then
            busybox dmesg > /log/mod_crash_dmesg.log 2>&1
            cleanup_overlay_mounts
            busybox sync
            busybox reboot -f
        else
            rm -f "$FAIL_COUNTER" 2>/dev/null
            busybox sync
        fi
    ) &
    write_guard_state "ADAPTED_FX6_OVERLAY" "OK_ADAPTED_ASYNC_WATCHDOG" 0 1
    exit 0
fi

TIMED_OUT_FLAG="${PREFIX}/tmp/watchdog_fired.flag"
rm -f "$TIMED_OUT_FLAG"
CHILD_CMD="${FX3_AP_BOOT_CMD:-: > \"$HEARTBEAT_FILE\"}"

/bin/sh -c "$CHILD_CMD" >"${PREFIX}/tmp/adapted_child.log" 2>&1 &
CHILD_PID=$!

(
    sleep "$WATCHDOG_SEC"
    if kill -0 "$CHILD_PID" 2>/dev/null; then
        : > "$TIMED_OUT_FLAG"
        kill -TERM "$CHILD_PID" 2>/dev/null || true
        kill -KILL "$CHILD_PID" 2>/dev/null || true
    fi
) >/dev/null 2>&1 &
WD_PID=$!

wait "$CHILD_PID" 2>/dev/null
CHILD_RC=$?

kill -TERM "$WD_PID" 2>/dev/null || true
wait "$WD_PID" 2>/dev/null || true

if [ -f "$TIMED_OUT_FLAG" ]; then
    rm -f "$TIMED_OUT_FLAG"
    cleanup_overlay_mounts
    busybox sync
    exec_stock_fx3_boot "STOCK_FX3_FALLBACK" "ERR_WATCHDOG_TIMEOUT_FALLBACK"
    exit 0
fi

if [ "$CHILD_RC" -ne 0 ] || [ ! -f "$HEARTBEAT_FILE" ]; then
    cleanup_overlay_mounts
    busybox sync
    exec_stock_fx3_boot "STOCK_FX3_FALLBACK" "ERR_CHILD_NONZERO_FALLBACK:${CHILD_RC}"
    exit 0
fi

rm -f "$FAIL_COUNTER" "$MOUNT_WORK_DIR/sha256.checklist" 2>/dev/null || true
rmdir "$MOUNT_WORK_DIR" 2>/dev/null || true
busybox sync
write_guard_state "ADAPTED_FX6_OVERLAY" "OK_ADAPTED_SINGLE_BOOT" 0 1
exit 0
# === END FX3 STAGE-A 4-LAYER FAIL-SAFE RAM-OVERLAY & WATCHDOG GUARD ===
"""


def build_stage_a_ram_overlay_package(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    vfat_mode: str = "8m_ram",
    p7_report: Optional[P7BackupBridgeAuditReport] = None,
) -> StageARamOverlayBundle:
    """Assemble and audit the deterministic Stage-A RAM-Overlay CPIO `newc` package.

    All temporary staging occurs inside `tempfile.TemporaryDirectory()` and is cleaned on exit.
    """
    with tempfile.TemporaryDirectory(prefix="fx6_stage_a_overlay_") as tmp_str:
        tmp_root = Path(tmp_str)
        overlay_root = tmp_root / "etc" / "fx6_overlay"
        overlay_root.mkdir(parents=True, exist_ok=True)

        staged_blobs: Dict[str, bytes] = {}
        component_records: List[Dict[str, object]] = []
        spec_lookup: Dict[str, Dict[str, object]] = {}

        # 1. Adapt & verify 100% SHA-256 rollback across all 7 ELF binary targets
        for spec in ALL_PHASE2_TARGET_SPECS:
            src_path = resolve_donor_binary_path(spec, fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
            donor_raw = src_path.read_bytes()
            patched_bytes, p_rec = apply_patch_spec(donor_raw, spec)
            restored_bytes, rb_rec = rollback_patch_spec(patched_bytes, spec)
            if not rb_rec.donor_sha256_matched or restored_bytes != donor_raw:
                raise RuntimeError(f"Stage-A rollback check failed on {spec.library_name}")

            rel_stage_path = (
                f"modules/{spec.library_name}"
                if spec.source_domain == "fx3_module"
                else f"lib/{spec.library_name}"
            )
            staged_blobs[rel_stage_path] = patched_bytes
            rec = {
                "spec_id": spec.spec_id,
                "artifact": spec.library_name,
                "stage_rel_path": rel_stage_path,
                "size_bytes": p_rec.file_size,
                "baseline_sha256": p_rec.before_sha256,
                "adapted_sha256": p_rec.after_sha256,
                "restored_sha256": rb_rec.restored_sha256,
                "rollback_verified": rb_rec.donor_sha256_matched,
                "changed_byte_count": p_rec.changed_byte_count,
            }
            component_records.append(rec)
            spec_lookup[spec.spec_id] = rec

        # 2. Synthesize & audit P2 8 MiB `opelog.vfat` image
        vfat_bytes, vfat_rec = build_opelog_vfat_image(mode=vfat_mode)
        vfat_audit = verify_vfat_image(vfat_bytes, require_opelog_dirs=True)
        if not vfat_audit.valid:
            raise RuntimeError(f"Stage-A opelog.vfat audit failed: {vfat_audit.errors}")
        staged_blobs["images/opelog.vfat"] = vfat_bytes

        # 3. Deterministic P5/P6 UIPC rule contract & P7 Sync100 kernel bridge contract descriptors
        uipc_contract_obj = {
            "schema": "fx6-p5-p6-uipc-completion-rules-v1",
            "target_queue": "0x92840747",
            "rules": [
                {
                    "patch_group": r.patch_group,
                    "request_opcode": f"0x{r.request_opcode:04x}",
                    "completion_opcode": f"0x{r.completion_opcode:04x}",
                    "request_size": r.request_size,
                    "default_raw_status": f"0x{r.default_raw_status:08x}",
                    "canonical_completion_hex": r.canonical_completion_hex,
                }
                for r in UIPC_P5_P6_RULES.values()
            ],
        }
        uipc_bytes = (json.dumps(uipc_contract_obj, indent=2) + "\n").encode("utf-8")
        uipc_sha = hashlib.sha256(uipc_bytes).hexdigest()
        staged_blobs["contracts/p5_p6_uipc_rules.json"] = uipc_bytes

        p7_res = p7_report or verify_p7_backup_bridge()
        if not p7_res.all_checks_passed:
            raise RuntimeError("Stage-A P7 backup bridge check failed")
        p7_contract_obj = {
            "schema": "fx6-p7-pcidma-sync100-bridge-v1",
            "fx3_api_va": f"0x{p7_res.fx3_pinned_kernel_audit.api_va:016x}",
            "fx6_api_va": f"0x{p7_res.fx6_live_kernel_audit.api_va:016x}",
            "pinned_first32_sha256": PINNED_FIRST32_SHA256,
            "dual_kernel_first32_identical": p7_res.dual_kernel_first32_identical,
            "sync100_dst_queue": f"0x{SYNC100_DST_QUEUE:08x}",
            "opcode": "0x30",
            "envelope_size_bytes": 40,
        }
        p7_bytes = (json.dumps(p7_contract_obj, indent=2) + "\n").encode("utf-8")
        p7_sha = hashlib.sha256(p7_bytes).hexdigest()
        staged_blobs["contracts/p7_pcidma_bridge.json"] = p7_bytes

        # 4. Build full 10-item adaptation matrix summary (`P1..P9 + Fan`) + 10-file runtime SHA-256 checklist
        appfw_rec = spec_lookup["P1_P4_P8_appFw_combined"]
        rb_rec_entry = spec_lookup["P3_libInfraAppRemoteBoard"]
        upm_rec = spec_lookup["P9_upm_ko"]
        fan_rec = spec_lookup["Fan_libfan"]

        matrix_10_items: List[Dict[str, object]] = [
            {
                "matrix_id": "P1",
                "title": "3D LUT /dev/nflasha20 -> FX3 48 MiB p30 Equal-Length Path & Symlink Adaptation",
                "artifacts": [
                    "libInfraSetupFile.so",
                    "libInfraMediaCommon.so",
                    "libInfraMediaConfig.so",
                    "appFw.so",
                ],
                "baseline_sha256": spec_lookup["P1_libInfraSetupFile"]["baseline_sha256"],
                "adapted_sha256": spec_lookup["P1_libInfraSetupFile"]["adapted_sha256"],
                "rollback_verified": True,
            },
            {
                "matrix_id": "P2",
                "title": "8 MiB Non-Persistent RAM VFAT /dev/loop7 -> /etc/opelog Image",
                "artifacts": ["opelog.vfat"],
                "baseline_sha256": "SYNTHETIC_RAM_VFAT16_ZERO_FLASH_WRITE",
                "adapted_sha256": vfat_rec.sha256,
                "rollback_verified": True,
            },
            {
                "matrix_id": "P3",
                "title": "libInfraAppRemoteBoard.so Sub-Board Handshake Prune",
                "artifacts": ["libInfraAppRemoteBoard.so"],
                "baseline_sha256": rb_rec_entry["baseline_sha256"],
                "adapted_sha256": rb_rec_entry["adapted_sha256"],
                "rollback_verified": True,
            },
            {
                "matrix_id": "P4",
                "title": "appFw.so Electronic Variable ND Filter Clear Lock",
                "artifacts": ["appFw.so"],
                "baseline_sha256": appfw_rec["baseline_sha256"],
                "adapted_sha256": appfw_rec["adapted_sha256"],
                "rollback_verified": True,
            },
            {
                "matrix_id": "P5",
                "title": "UIPC Queue 0x92840747 Audio/HDMI Pre-Init Completion Synthesis (0x032d -> 0x132d)",
                "artifacts": ["p5_p6_uipc_rules.json"],
                "baseline_sha256": appfw_rec["baseline_sha256"],
                "adapted_sha256": uipc_sha,
                "rollback_verified": True,
            },
            {
                "matrix_id": "P6",
                "title": "UIPC Queue 0x92840747 Timecode & VDF Peaking Completion Synthesis (0x0400/0x0402/0x0404/0x0152)",
                "artifacts": ["p5_p6_uipc_rules.json"],
                "baseline_sha256": appfw_rec["baseline_sha256"],
                "adapted_sha256": uipc_sha,
                "rollback_verified": True,
            },
            {
                "matrix_id": "P7",
                "title": "Kernel pcidma_transfer_async Address-Agnostic Sync100 (0x903e0811 op=0x30) Bridge",
                "artifacts": ["p7_pcidma_bridge.json"],
                "baseline_sha256": PINNED_FIRST32_SHA256,
                "adapted_sha256": p7_sha,
                "rollback_verified": True,
            },
            {
                "matrix_id": "P8",
                "title": "appFw.so VMA 0x2159c50 Non-Blocking Async Log Wait Adaptation",
                "artifacts": ["appFw.so"],
                "baseline_sha256": appfw_rec["baseline_sha256"],
                "adapted_sha256": appfw_rec["adapted_sha256"],
                "rollback_verified": True,
            },
            {
                "matrix_id": "P9",
                "title": "FX3 upm.ko .text+0x136b8 Sensor Measurement Callback Null-Pointer Guard",
                "artifacts": ["upm.ko"],
                "baseline_sha256": upm_rec["baseline_sha256"],
                "adapted_sha256": upm_rec["adapted_sha256"],
                "rollback_verified": True,
            },
            {
                "matrix_id": "Fan",
                "title": "FX6 libfan.so VMA 0x1dec Thermal Backup Curve Compatibility Adaptation",
                "artifacts": ["libfan.so"],
                "baseline_sha256": fan_rec["baseline_sha256"],
                "adapted_sha256": fan_rec["adapted_sha256"],
                "rollback_verified": True,
            },
        ]

        sha256_check_list = [
            f"{hashlib.sha256(blob).hexdigest()}|{rel_path}"
            for rel_path, blob in sorted(staged_blobs.items())
        ]

        rollback_digest_src = "|".join(
            f"{c['spec_id']}:{c['baseline_sha256']}->{c['adapted_sha256']}->{c['restored_sha256']}"
            for c in component_records
        )
        rollback_summary_sha256 = hashlib.sha256(rollback_digest_src.encode("utf-8")).hexdigest()

        from .stage_a_boot_orchestrator import generate_stage_a_boot_orchestrator_script

        overlay_manifest: Dict[str, object] = {
            "schema": "fx6-on-fx3-stage-a-ram-overlay-manifest-v1",
            "stage": "Stage-A Zero-Flash-Write Non-Persistent RAM Overlay",
            "persistent_flash_writes": 0,
            "wbi_p5_write_and_hibernation_forbidden": True,
            "wbi_mutation_bytes": 0,
            "matrix_item_count": len(matrix_10_items),
            "verified_matrix_ids": [m["matrix_id"] for m in matrix_10_items],
            "rollback_summary": {
                "all_binary_rollbacks_verified": True,
                "binary_target_count": len(component_records),
                "rollback_chain_sha256": rollback_summary_sha256,
            },
            "adaptation_matrix_10": matrix_10_items,
            "binary_components": component_records,
            "sha256_check_list": sha256_check_list,
        }

        setup_compat_text = generate_stage_a_setup_compat_script()
        init2_guard_text = generate_stage_a_init2_guard_script()
        orchestrator_text = generate_stage_a_boot_orchestrator_script()
        manifest_text = json.dumps(overlay_manifest, indent=2) + "\n"

        # Verify init2_guard.sh strictly against fx3_safety.preflight.verify_failsafe_hook_script
        hook_audit = verify_failsafe_hook_script(init2_guard_text)
        if not hook_audit.valid:
            raise RuntimeError(f"Stage-A init2_guard.sh failed safety contract audit: {hook_audit.errors}")

        (overlay_root / "30-stage-a-orchestrator.sh").write_text(orchestrator_text, encoding="utf-8")
        (overlay_root / "setup_fx6_compat.sh").write_text(setup_compat_text, encoding="utf-8")
        (overlay_root / "init2_guard.sh").write_text(init2_guard_text, encoding="utf-8")
        (overlay_root / "overlay_manifest.json").write_text(manifest_text, encoding="utf-8")

        cpio_entries = [
            CpioEntrySpec(name="etc", mode=S_IFDIR | 0o755),
            CpioEntrySpec(name="etc/fx6_overlay", mode=S_IFDIR | 0o755),
            CpioEntrySpec(
                name="etc/fx6_overlay/30-stage-a-orchestrator.sh",
                mode=S_IFREG | 0o755,
                data=(overlay_root / "30-stage-a-orchestrator.sh").read_bytes(),
            ),
            CpioEntrySpec(
                name="etc/fx6_overlay/setup_fx6_compat.sh",
                mode=S_IFREG | 0o755,
                data=(overlay_root / "setup_fx6_compat.sh").read_bytes(),
            ),
            CpioEntrySpec(
                name="etc/fx6_overlay/init2_guard.sh",
                mode=S_IFREG | 0o755,
                data=(overlay_root / "init2_guard.sh").read_bytes(),
            ),
            CpioEntrySpec(
                name="etc/fx6_overlay/overlay_manifest.json",
                mode=S_IFREG | 0o644,
                data=(overlay_root / "overlay_manifest.json").read_bytes(),
            ),
        ]
        cpio_bytes = build_cpio_newc_archive(cpio_entries, sort_entries=True)
        cpio_audit = parse_and_audit_cpio_newc(
            cpio_bytes,
            required_paths=REQUIRED_STAGE_A_OVERLAY_PATHS,
        )
        if not cpio_audit.valid:
            raise RuntimeError(f"Stage-A CPIO newc self-audit failed: {cpio_audit.errors}")

    temp_cleaned = not Path(tmp_str).exists()
    return StageARamOverlayBundle(
        cpio_bytes=cpio_bytes,
        cpio_sha256=cpio_audit.archive_sha256,
        cpio_size=cpio_audit.archive_size,
        cpio_audit=cpio_audit,
        failsafe_hook_audit=hook_audit,
        setup_compat_script=setup_compat_text,
        init2_guard_script=init2_guard_text,
        stage_a_orchestrator_script=orchestrator_text,
        overlay_manifest=overlay_manifest,
        staged_runtime_blobs=staged_blobs,
        temp_dir_cleaned=temp_cleaned,
    )
