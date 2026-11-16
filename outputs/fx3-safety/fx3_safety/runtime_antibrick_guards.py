"""2026 Global Runtime Anti-Brick Guards for Sony BIONZ XR (CXD90057/CXD90058).

Deterministic static + shell/script + storage-budget + NVRAM-diff auditors
blocking the four field-proven 2025-2026 Sony BIONZ XR brick vectors:
1. `LD_SO_PRELOAD_DYNAMIC_BUSYBOX_DEADLOCK`:
   Forbids `/etc/ld.so.preload` writes or path traversal onto persistent
   VFAT/ext partitions (`/bin/busybox` & `/bin/sh` are dynamically linked; a
   bad `.so` deadlocks `/sbin/init` before shell or Jiritsu starts). Enforces
   RAM-only `LD_LIBRARY_PATH` / `tmpfs` `mount --bind` after `/tmp/mod_arm_once`
   Clear-Before-Exec.
2. `BUSYBOX_DD_TRUNCATION_HAZARD`:
   Detects and blocks `dd of=<existing_file>` without verified `conv=notrunc`
   support or raw file-truncating overwrites on Sony BusyBox, enforcing the
   `pmca-re-reloaded` 5-step atomic write contract (Drop exit guard, tmpfs
   staging, full SHA-256 readback, 5-slot rollback history manifest).
3. `NFLASHA10_12MIB_VFAT_EXHAUSTION_0x10000009`:
   Enforces strict free-space headroom on the shared 12 MiB `/setting`
   (`nflasha10`) VFAT partition so error `0x10000009` write-lockout never occurs.
4. `CAMSET_BK4_PRODUCT_MODEL_MUTATION_BLOCK`:
   Inspects `CAMSET*.DAT` / `BK4\\0` diffs to permit safe user settings while
   hard-blocking `PRODUCT_MODEL` (`ALCIN_UUD` enum `4`) NVRAM tampering.

Safety Redline:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` (hard-locked)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import posixpath
import re
import shlex
import struct
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .boot_contracts import BK4_HEADER_SIZE, BK4_MAGIC, BK4_SYNC_MARKER, parse_bk4_record


PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False

# Violation codes
V_LD_SO_PRELOAD = "LD_SO_PRELOAD_DYNAMIC_BUSYBOX_DEADLOCK"
V_BUSYBOX_DD_TRUNC = "BUSYBOX_DD_TRUNCATION_HAZARD"
V_NFLASHA10_FULL = "NFLASHA10_12MIB_VFAT_EXHAUSTION_0x10000009"
V_CAMSET_PRODUCT_MODEL = "CAMSET_BK4_PRODUCT_MODEL_MUTATION_BLOCK"
V_PMCA_5STEP = "PMCA_5STEP_WRITE_GUARD_VIOLATION"

# Partition & error constants
NFLASHA10_PARTITION_BYTES: int = 12 * 1024 * 1024  # 12 MiB shared VFAT (/setting, /tmp, /etc, /var)
NFLASHA10_CLUSTER_BYTES: int = 4096
NFLASHA10_DEFAULT_MIN_HEADROOM_BYTES: int = 2 * 1024 * 1024  # 2 MiB reserve
NFLASHA10_HARD_FLOOR_HEADROOM_BYTES: int = 1 * 1024 * 1024  # 1 MiB absolute floor
NFLASHA10_LOCKUP_ERROR_CODE: int = 0x10000009

# Product model enums from BIONZ XR feature_manager / HAITA tables
PRODUCT_MODEL_ENUMS: Dict[str, int] = {
    "PRODUCT_MODEL_LS": 0,         # ILCE-7M4 (A7 IV)
    "PRODUCT_MODEL_LAX": 3,        # ILME-FX30
    "PRODUCT_MODEL_ALCIN_UUD": 4,  # ILME-FX3 (0x91030080, IMX510, CINEMA_LINE)
}

FX3_PRODUCT_MODEL_ENUM: int = 4
FX3_MODEL_ID_HEX: str = "0x91030080"

# Known safe user BK4 IDs & CAMSET logical keys (non-identity, non-calibration)
SAFE_USER_BK4_IDS: Dict[int, str] = {
    0x02CF0004: "NTSC/PAL Warning Popup Control",
    0x02CF1443: "Log Shooting Mode (Off / Flexible ISO / Cine EI)",
    0x02CF1453: "Select LUT (S709 / R709 / S-Log3 / User1-16)",
    0x02CF1702: "Shutter Mode (Speed / Angle)",
    0x02CF1704: "Shutter Angle Value",
    0x02CF1BF2: "Anamorphic De-Squeeze Display",
}

FORBIDDEN_NVRAM_KEY_TOKENS: Tuple[str, ...] = (
    "PRODUCT_MODEL",
    "ALCIN_UUD",
    "BKID_PRODUCT_MODEL",
    "MODEL_ID",
    "CAMERA_MODEL",
    "FEATURE_MANAGER_MODEL",
    "PSD.BIN",
    "DEFDET.BIN",
    "LENSFILE.BIN",
    "DDRTRAINING",
    "P6_JIRITSU",
    "SERIAL_NO",
    "CERT_",
)

FORBIDDEN_BK4_KEY_IDS: Tuple[int, ...] = (
    0x00000000,
    0x00010000,  # Product identity / model slot family
    0x02CF0001,  # Model / region identity guard
)

PERSISTENT_TARGET_PREFIXES: Tuple[str, ...] = (
    "/dev/nflasha",
    "/dev/cnflasha",
    "/dev/pnflasha",
    "/setting/",
    "/etc/",
    "/usr/",
    "/boot/",
    "/var/",
)


@dataclass(frozen=True)
class GuardAuditResult:
    valid: bool
    status: str  # "VERIFIED_SAFE" or "BLOCKED_<CODE>"
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    details: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.valid


# ---------------------------------------------------------------------------
# 1. LD_SO_PRELOAD_DYNAMIC_BUSYBOX_DEADLOCK Guard
# ---------------------------------------------------------------------------


def normalize_camera_path(raw_path: str, *, base_dir: str = "/tmp/jiritsu") -> str:
    """Resolve `..` path traversal relative to `base_dir` just like POSIX VFS."""
    cleaned = raw_path.strip()
    if not cleaned:
        return ""
    if cleaned.startswith("/"):
        return posixpath.normpath(cleaned)
    return posixpath.normpath(posixpath.join(base_dir, cleaned))


def audit_ld_so_preload_and_overlay(
    *,
    script_text: str = "",
    target_paths: Sequence[str] = (),
    jiritsu_set_file_paths: Sequence[str] = (),
    require_clear_before_exec_for_ram_overlay: bool = True,
) -> GuardAuditResult:
    """Block persistent `/etc/ld.so.preload` traps and enforce RAM-only Clear-Before-Exec."""
    violations: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    def add_violation(msg: str) -> None:
        if V_LD_SO_PRELOAD not in violations:
            violations.append(V_LD_SO_PRELOAD)
        errors.append(msg)

    # Check explicit target paths & Jiritsu SET_FILE_PATH (0x400f) entries for traversal/preload
    for p in target_paths:
        norm = normalize_camera_path(p)
        if "ld.so.preload" in norm or "ld.so.preload" in p:
            add_violation(
                f"Forbidden persistent preload path {p!r} (normalized {norm!r}): "
                "/bin/busybox & /bin/sh are dynamically linked on CXD90057; bad preload deadlocks /sbin/init."
            )

    for jp in jiritsu_set_file_paths:
        norm = normalize_camera_path(jp, base_dir="/tmp/jiritsu")
        if ".." in jp.split("/") and not norm.startswith("/tmp/jiritsu/"):
            add_violation(
                f"Jiritsu SET_FILE_PATH traversal blocked: {jp!r} escapes /tmp/jiritsu -> {norm!r}."
            )
        if "ld.so.preload" in norm or norm.startswith("/etc"):
            add_violation(
                f"Jiritsu SET_FILE_PATH targeting persistent /etc or ld.so.preload blocked: {jp!r} -> {norm!r}."
            )

    # Scan script lines (ignoring comment-only lines)
    non_comment_lines: List[str] = []
    for raw_line in script_text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        non_comment_lines.append(stripped)
        if "ld.so.preload" in stripped:
            add_violation(
                f"Script references ld.so.preload ({stripped!r}): forbidden on dynamically-linked BusyBox CXD90057."
            )
        # Catch path traversal in shell paths targeting /etc or /usr
        for tok in re.findall(r"(?:/[^\s;\"'|&]+|\.\./[^\s;\"'|&]+)", stripped):
            if ".." in tok:
                norm_tok = normalize_camera_path(tok, base_dir="/tmp/jiritsu")
                if "ld.so.preload" in norm_tok or norm_tok.startswith(("/etc", "/usr", "/boot")):
                    add_violation(
                        f"Path traversal {tok!r} resolves to protected system path {norm_tok!r}."
                    )

    active_body = "\n".join(non_comment_lines)
    uses_ram_overlay = ("mount --bind" in active_body) or ("LD_LIBRARY_PATH=" in active_body)
    if uses_ram_overlay and require_clear_before_exec_for_ram_overlay:
        # Must contain /tmp/mod_arm_once Clear-Before-Exec (`rm -f .../tmp/mod_arm_once` + `sync`)
        # BEFORE the first `mount --bind` or `LD_LIBRARY_PATH=` activation!
        rm_m = re.search(r"rm\s+-f\s+[\"']?/tmp/mod_arm_once[\"']?", active_body)
        sync_m = re.search(r"(?:busybox\s+)?sync\b", active_body)
        act_m = re.search(r"(?:mount\s+--bind|LD_LIBRARY_PATH=)", active_body)
        if not rm_m:
            add_violation(
                "RAM-only overlay/LD_LIBRARY_PATH requires Clear-Before-Exec `rm -f /tmp/mod_arm_once`."
            )
        elif not sync_m:
            add_violation(
                "RAM-only overlay/LD_LIBRARY_PATH requires `sync` after clearing `/tmp/mod_arm_once`."
            )
        elif act_m and (rm_m.start() > act_m.start() or sync_m.start() > act_m.start()):
            add_violation(
                "Clear-Before-Exec (`rm -f /tmp/mod_arm_once` + `sync`) must occur BEFORE `mount --bind` / `LD_LIBRARY_PATH=`."
            )

    valid = len(errors) == 0
    return GuardAuditResult(
        valid=valid,
        status="VERIFIED_SAFE" if valid else f"BLOCKED_{V_LD_SO_PRELOAD}",
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={"uses_ram_overlay": uses_ram_overlay},
    )


# ---------------------------------------------------------------------------
# 2. BUSYBOX_DD_TRUNCATION_HAZARD + pmca-re-reloaded 5-Step Contract
# ---------------------------------------------------------------------------


def audit_busybox_dd_commands(
    script_text: str,
    *,
    busybox_notrunc_verified: bool = False,
    allow_verified_tmpfs_dd: bool = True,
) -> GuardAuditResult:
    """Detect Sony BusyBox `dd` truncation hazards and unsafe persistent overwrites."""
    violations: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    inspected_dd_calls: List[Dict[str, Any]] = []

    def add_violation(msg: str) -> None:
        if V_BUSYBOX_DD_TRUNC not in violations:
            violations.append(V_BUSYBOX_DD_TRUNC)
        errors.append(msg)

    for raw_line in script_text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Split chained shell statements on ; && || |
        segments = re.split(r"(?:&&|\|\||;|\|)", stripped)
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            try:
                tokens = shlex.split(seg)
            except ValueError:
                tokens = seg.split()
            if not tokens:
                continue

            # Strip leading `busybox` wrapper if present
            cmd = tokens[1:] if tokens[0] in ("busybox", "/bin/busybox") and len(tokens) > 1 else tokens
            if cmd and cmd[0] in ("dd", "/bin/dd"):
                of_vals = [t[3:] for t in cmd[1:] if t.startswith("of=")]
                conv_vals = [t[5:] for t in cmd[1:] if t.startswith("conv=")]
                has_notrunc = any("notrunc" in cv.split(",") for cv in conv_vals)
                target = of_vals[-1] if of_vals else ""
                inspected_dd_calls.append(
                    {
                        "target": target,
                        "has_notrunc": has_notrunc,
                        "busybox_notrunc_verified": busybox_notrunc_verified,
                    }
                )
                if not target:
                    continue
                norm_target = normalize_camera_path(target, base_dir="/")
                is_tmpfs_staging = allow_verified_tmpfs_dd and norm_target.startswith(("/tmp/", "/dev/shm/"))
                is_persistent_target = norm_target.startswith(PERSISTENT_TARGET_PREFIXES)

                if is_persistent_target:
                    add_violation(
                        f"Direct `dd` write to persistent/device target {target!r} blocked "
                        "(enforce tmpfs staging + verified whole-partition/atomic path)."
                    )
                elif not is_tmpfs_staging:
                    if not has_notrunc:
                        add_violation(
                            f"`dd of={target}` omits `conv=notrunc`: risks O_TRUNC 0-byte file truncation brick."
                        )
                    elif not busybox_notrunc_verified:
                        add_violation(
                            f"`dd of={target} conv=notrunc` blocked: Sony camera BusyBox `dd` "
                            "is not verified to support `conv=notrunc` (busybox_notrunc_verified=False)."
                        )

            # Also flag shell truncation redirection (`>` not `>>`) onto persistent files
            redirs = re.findall(r"(?<![>0-9])>\s*([^\s;&|]+)", seg)
            for rt in redirs:
                norm_rt = normalize_camera_path(rt, base_dir="/")
                if norm_rt.startswith(("/etc/", "/usr/", "/boot/", "/dev/nflasha", "/dev/cnflasha")):
                    add_violation(
                        f"Shell truncation redirection `> {rt}` onto protected persistent path blocked."
                    )

    valid = len(errors) == 0
    return GuardAuditResult(
        valid=valid,
        status="VERIFIED_SAFE" if valid else f"BLOCKED_{V_BUSYBOX_DD_TRUNC}",
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={"inspected_dd_calls": inspected_dd_calls},
    )


def audit_pmca_5step_write_contract(
    *,
    drop_exit_guard_ok: bool,
    tmpfs_staging_ok: bool,
    expected_sha256: str,
    readback_sha256: str,
    rollback_history: Sequence[Mapping[str, Any]],
    max_rollback_slots: int = 5,
    script_text: str = "",
    busybox_notrunc_verified: bool = False,
) -> GuardAuditResult:
    """Enforce the `pmca-re-reloaded` 5-step atomic write & 5-slot rollback safety contract."""
    violations: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    def add_5step_err(msg: str) -> None:
        if V_PMCA_5STEP not in violations:
            violations.append(V_PMCA_5STEP)
        errors.append(msg)

    if not drop_exit_guard_ok:
        add_5step_err("Step 1 (Drop exit guard) missing: staging/mode cleanup not guaranteed on failure.")
    if not tmpfs_staging_ok:
        add_5step_err("Step 2 (Atomic tmpfs staging) missing: direct in-place overwrite is forbidden.")
    if (
        len(expected_sha256) != 64
        or len(readback_sha256) != 64
        or expected_sha256.lower() != readback_sha256.lower()
    ):
        add_5step_err(
            f"Step 3 (Full verified readback) failed: expected={expected_sha256!r}, readback={readback_sha256!r}."
        )

    # Step 4: 5-slot rollback history manifest (`rollback/-.json`)
    if not isinstance(rollback_history, (list, tuple)) or not (1 <= len(rollback_history) <= max_rollback_slots):
        add_5step_err(
            f"Step 4 (5-slot rollback manifest) requires 1..{max_rollback_slots} verified entries, "
            f"got {len(rollback_history) if isinstance(rollback_history, (list, tuple)) else 'invalid'}."
        )
    else:
        seen_slots: set[str] = set()
        for idx, slot in enumerate(rollback_history):
            sid = str(slot.get("slot_id", ""))
            sha_hex = str(slot.get("sha256", ""))
            sz = slot.get("bytes")
            if not sid or sid in seen_slots:
                add_5step_err(f"Step 4 rollback slot[{idx}] has missing or duplicate slot_id: {sid!r}.")
            seen_slots.add(sid)
            if not re.fullmatch(r"[0-9a-f]{64}", sha_hex.lower()):
                add_5step_err(f"Step 4 rollback slot[{idx}] invalid sha256: {sha_hex!r}.")
            if not isinstance(sz, int) or sz <= 0:
                add_5step_err(f"Step 4 rollback slot[{idx}] invalid byte count: {sz!r}.")

    # Step 5: Zero BusyBox `dd` truncation hazards in accompanying script
    if script_text:
        dd_res = audit_busybox_dd_commands(script_text, busybox_notrunc_verified=busybox_notrunc_verified)
        if not dd_res.valid:
            for vc in dd_res.violation_codes:
                if vc not in violations:
                    violations.append(vc)
            errors.extend(dd_res.errors)

    valid = len(errors) == 0
    return GuardAuditResult(
        valid=valid,
        status="VERIFIED_SAFE" if valid else f"BLOCKED_{violations[0]}",
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "rollback_slots": len(rollback_history) if isinstance(rollback_history, (list, tuple)) else 0,
            "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        },
    )


# ---------------------------------------------------------------------------
# 3. NFLASHA10_12MIB_VFAT_EXHAUSTION_0x10000009 Guard
# ---------------------------------------------------------------------------


def audit_nflasha10_vfat_budget(
    *,
    current_used_bytes: int,
    planned_writes: Sequence[Mapping[str, Any]] = (),
    partition_bytes: int = NFLASHA10_PARTITION_BYTES,
    min_headroom_bytes: int = NFLASHA10_DEFAULT_MIN_HEADROOM_BYTES,
    cluster_bytes: int = NFLASHA10_CLUSTER_BYTES,
) -> GuardAuditResult:
    """Enforce strict free-space headroom on shared 12 MiB `/setting` (`nflasha10`) VFAT."""
    violations: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    def add_violation(msg: str) -> None:
        if V_NFLASHA10_FULL not in violations:
            violations.append(V_NFLASHA10_FULL)
        errors.append(msg)

    if partition_bytes <= 0 or partition_bytes > NFLASHA10_PARTITION_BYTES:
        add_violation(f"Invalid nflasha10 partition size {partition_bytes} B (expected <= {NFLASHA10_PARTITION_BYTES}).")
    if cluster_bytes <= 0:
        add_violation(f"Invalid VFAT cluster size {cluster_bytes} B.")
    if min_headroom_bytes < NFLASHA10_HARD_FLOOR_HEADROOM_BYTES:
        add_violation(
            f"min_headroom_bytes={min_headroom_bytes} B violates 1 MiB hard floor "
            f"({NFLASHA10_HARD_FLOOR_HEADROOM_BYTES} B) for error 0x10000009 prevention."
        )
    if current_used_bytes < 0:
        add_violation(f"Negative current_used_bytes={current_used_bytes} is invalid.")

    planned_cluster_bytes = 0
    for idx, item in enumerate(planned_writes):
        path = str(item.get("path", f"<write#{idx}>"))
        raw_sz = item.get("bytes", 0)
        if not isinstance(raw_sz, int) or raw_sz < 0:
            add_violation(f"Planned write {path!r} has invalid byte size {raw_sz!r}.")
            continue
        if raw_sz == 0:
            aligned = 0
        else:
            aligned = ((raw_sz + cluster_bytes - 1) // cluster_bytes) * cluster_bytes
        planned_cluster_bytes += aligned

    projected_used = max(0, current_used_bytes) + planned_cluster_bytes
    projected_free = partition_bytes - projected_used

    if projected_used > partition_bytes:
        add_violation(
            f"nflasha10 12 MiB VFAT overflow ({hex(NFLASHA10_LOCKUP_ERROR_CODE)}): "
            f"projected_used={projected_used} B > partition={partition_bytes} B."
        )
    elif projected_free < min_headroom_bytes:
        add_violation(
            f"nflasha10 headroom breach ({hex(NFLASHA10_LOCKUP_ERROR_CODE)}): "
            f"projected_free={projected_free} B < required_min_headroom={min_headroom_bytes} B."
        )

    valid = len(errors) == 0
    return GuardAuditResult(
        valid=valid,
        status="VERIFIED_SAFE" if valid else f"BLOCKED_{V_NFLASHA10_FULL}",
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "partition_bytes": partition_bytes,
            "current_used_bytes": current_used_bytes,
            "planned_cluster_bytes": planned_cluster_bytes,
            "projected_used_bytes": projected_used,
            "projected_free_bytes": projected_free,
            "min_headroom_bytes": min_headroom_bytes,
            "error_code": hex(NFLASHA10_LOCKUP_ERROR_CODE),
        },
    )


# ---------------------------------------------------------------------------
# 4. CAMSET_BK4_PRODUCT_MODEL_MUTATION_BLOCK Guard
# ---------------------------------------------------------------------------


def _is_forbidden_nvram_key(key_name: str, key_id: Optional[int]) -> bool:
    upper = key_name.strip().upper()
    if any(tok in upper for tok in FORBIDDEN_NVRAM_KEY_TOKENS):
        return True
    if key_id is not None and key_id in FORBIDDEN_BK4_KEY_IDS:
        return True
    return False


def audit_camset_bk4_diff(
    *,
    diff_entries: Sequence[Mapping[str, Any]] = (),
    before_bk4: Optional[bytes] = None,
    after_bk4: Optional[bytes] = None,
    protected_byte_offsets: Sequence[int] = (),
    allowed_user_byte_offsets: Sequence[int] = (),
) -> GuardAuditResult:
    """Inspect `CAMSET*.DAT` / `BK4\\0` diffs: allow safe user settings, block PRODUCT_MODEL tampering."""
    violations: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    allowed_keys: List[str] = []
    blocked_keys: List[str] = []

    def add_violation(msg: str) -> None:
        if V_CAMSET_PRODUCT_MODEL not in violations:
            violations.append(V_CAMSET_PRODUCT_MODEL)
        errors.append(msg)

    # 1. Structured CAMSET / BK4 diff inspection
    for idx, entry in enumerate(diff_entries):
        key_name = str(entry.get("key", entry.get("name", f"entry_{idx}")))
        raw_id = entry.get("bk_id")
        key_id: Optional[int] = None
        if isinstance(raw_id, int):
            key_id = raw_id
        elif isinstance(raw_id, str) and raw_id.strip():
            try:
                key_id = int(raw_id, 0)
            except ValueError:
                add_violation(f"Malformed BK4 key ID {raw_id!r} on {key_name!r}.")
                continue

        old_val = entry.get("old_value")
        new_val = entry.get("new_value")
        if old_val == new_val:
            continue

        if _is_forbidden_nvram_key(key_name, key_id):
            blocked_keys.append(key_name)
            add_violation(
                f"Blocked NVRAM mutation on protected identity/model key {key_name!r} "
                f"(id={hex(key_id) if key_id is not None else 'N/A'}, "
                f"{old_val!r} -> {new_val!r}; ALCIN_UUD enum=4 / hardware tables cannot be tampered)."
            )
            continue

        if key_id is not None and key_id in SAFE_USER_BK4_IDS:
            allowed_keys.append(f"{key_name} ({SAFE_USER_BK4_IDS[key_id]})")
        else:
            allowed_keys.append(key_name)

    # 2. Binary BK4\0 diff inspection (when before/after buffers are provided)
    changed_offsets: List[int] = []
    if before_bk4 is not None or after_bk4 is not None:
        if before_bk4 is None or after_bk4 is None:
            add_violation("Binary BK4 diff requires both before_bk4 and after_bk4 buffers.")
        elif len(before_bk4) != len(after_bk4):
            add_violation(
                f"BK4 buffer length changed ({len(before_bk4)} -> {len(after_bk4)}): size mutation rejected."
            )
        else:
            sum_before, errs_before = parse_bk4_record(before_bk4)
            sum_after, errs_after = parse_bk4_record(after_bk4)
            if sum_before is None or not sum_before.checksum_ok:
                add_violation(f"Invalid baseline before_bk4 record: {errs_before}")
            if sum_after is None or not sum_after.checksum_ok:
                add_violation(f"Invalid modified after_bk4 record (bad BK4 checksum/magic): {errs_after}")
            if sum_before is not None and sum_after is not None:
                if sum_before.subsystems != sum_after.subsystems:
                    add_violation(
                        f"BK4 subsystems count mutated ({sum_before.subsystems} -> {sum_after.subsystems})."
                    )
                if sum_before.data_offset != sum_after.data_offset or sum_before.data_size != sum_after.data_size:
                    add_violation("BK4 data_offset/data_size header layout mutated.")
                if sum_before.revision_word2c != sum_after.revision_word2c:
                    warnings.append(
                        f"BK4 +0x2c revision changed ({sum_before.revision_word2c} -> {sum_after.revision_word2c})."
                    )

            # Check byte-level diff within payload (>= BK4_HEADER_SIZE), ignoring checksum [0x20..0x24)
            prot_set = set(protected_byte_offsets)
            allow_set = set(allowed_user_byte_offsets)
            for off in range(len(before_bk4)):
                if before_bk4[off] == after_bk4[off]:
                    continue
                if 0x20 <= off < 0x24:
                    continue  # 32-bit checksum field updated legitimately
                changed_offsets.append(off)
                if off < BK4_HEADER_SIZE and off not in (0x08, 0x14, 0x2C):
                    add_violation(f"BK4 protected header byte mutated at offset {hex(off)}.")
                elif off in prot_set:
                    add_violation(
                        f"PRODUCT_MODEL / protected NVRAM byte mutated at offset {hex(off)} "
                        f"({hex(before_bk4[off])} -> {hex(after_bk4[off])})."
                    )
                elif allow_set and off not in allow_set:
                    add_violation(
                        f"Unapproved BK4 payload byte mutation at offset {hex(off)} "
                        "(outside allowed user setting offsets)."
                    )

    valid = len(errors) == 0
    return GuardAuditResult(
        valid=valid,
        status="VERIFIED_SAFE" if valid else f"BLOCKED_{V_CAMSET_PRODUCT_MODEL}",
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "allowed_keys": allowed_keys,
            "blocked_keys": blocked_keys,
            "changed_payload_offsets": [hex(o) for o in changed_offsets],
        },
    )


# ---------------------------------------------------------------------------
# Unified Runtime Anti-Brick Guard Evaluator
# ---------------------------------------------------------------------------


def evaluate_runtime_antibrick_guards(
    *,
    script_text: str = "",
    target_paths: Sequence[str] = (),
    jiritsu_set_file_paths: Sequence[str] = (),
    busybox_notrunc_verified: bool = False,
    nflasha10_used_bytes: Optional[int] = None,
    nflasha10_planned_writes: Sequence[Mapping[str, Any]] = (),
    camset_diff_entries: Sequence[Mapping[str, Any]] = (),
    before_bk4: Optional[bytes] = None,
    after_bk4: Optional[bytes] = None,
    protected_bk4_offsets: Sequence[int] = (),
    pmca_5step_manifest: Optional[Mapping[str, Any]] = None,
) -> GuardAuditResult:
    """Run all 2026 Sony BIONZ XR anti-brick guards and return consolidated fail-closed report."""
    sub_results: List[GuardAuditResult] = [
        audit_ld_so_preload_and_overlay(
            script_text=script_text,
            target_paths=target_paths,
            jiritsu_set_file_paths=jiritsu_set_file_paths,
        ),
        audit_busybox_dd_commands(
            script_text,
            busybox_notrunc_verified=busybox_notrunc_verified,
        ),
    ]

    if nflasha10_used_bytes is not None or nflasha10_planned_writes:
        sub_results.append(
            audit_nflasha10_vfat_budget(
                current_used_bytes=nflasha10_used_bytes or 0,
                planned_writes=nflasha10_planned_writes,
            )
        )

    if camset_diff_entries or before_bk4 is not None or after_bk4 is not None:
        sub_results.append(
            audit_camset_bk4_diff(
                diff_entries=camset_diff_entries,
                before_bk4=before_bk4,
                after_bk4=after_bk4,
                protected_byte_offsets=protected_bk4_offsets,
            )
        )

    if pmca_5step_manifest is not None:
        sub_results.append(
            audit_pmca_5step_write_contract(
                drop_exit_guard_ok=bool(pmca_5step_manifest.get("drop_exit_guard_ok", False)),
                tmpfs_staging_ok=bool(pmca_5step_manifest.get("tmpfs_staging_ok", False)),
                expected_sha256=str(pmca_5step_manifest.get("expected_sha256", "")),
                readback_sha256=str(pmca_5step_manifest.get("readback_sha256", "")),
                rollback_history=pmca_5step_manifest.get("rollback_history", ()),
            )
        )

    violations: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    for res in sub_results:
        for vc in res.violation_codes:
            if vc not in violations:
                violations.append(vc)
        errors.extend(res.errors)
        warnings.extend(res.warnings)

    valid = len(errors) == 0
    return GuardAuditResult(
        valid=valid,
        status="VERIFIED_SAFE" if valid else f"BLOCKED_{violations[0]}",
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
            "checks_run": len(sub_results),
        },
    )
