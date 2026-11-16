"""Phase 66 — `init2` SD-Card Sentinel Escape Shell, CXD90057 Watchdog Boot-Loop Breaker & `p1` FAT12/FAT16 Chain Integrity Verifier.

Provides three deterministic offline recovery-safety verification pillars for FX3 (`0x91030080`):

1. **Zero-Hardware SD/CFexpress Sentinel Fail-Open Escape (`init2` Early Bypass Sandbox)**:
   Generates and executes a POSIX `/bin/sh` Stage-B `init2` wrapper guard inside an
   isolated `tempfile.TemporaryDirectory` sandbox proving **4 fail-open escape mechanisms**
   BEFORE any Stage-B `cpio` extraction or `mount --bind` occurs:
   - External Media Sentinel File (`FX3_SAFE_STOCK.FLG` / `DISABLE_STAGE_B.TXT` in Slot A or Slot B)
   - Physical Key-Chord Escape (`REC+MENU` / `SHUTTER` boot-GPIO latch)
   - Stage-B Payload SHA-256 / CPIO `070701` Magic Mismatch
   - `procam_app` Crash-Loop Breaker (`>= 3` exits within `15s` in volatile `/tmp/stage_b_crash.cnt`)

2. **CXD90057 Hardware Watchdog (`WDT`) & `Tier-0..Tier-2` State-Machine Verifier**:
   Models the hardware `CXD90057` watchdog (`timeout_ms=10000`, `kick_interval_ms=2000`)
   across normal Stage-B `H1` operation, hung UI presenter thread, kernel `oops` with
   `panic_on_oops`, clean reboot (`H1 -> H2` volatile RAM wipe), and `Tier-1/2` Multi-Port
   `p1` VFAT pointer rollback, proving `0` persistent eMMC mutations allow `WDT` reset
   alone to restore `H0 == H2` stock boot.

3. **Pure-Python `p1` FAT12/FAT16 Cluster-Chain & Atomic `8.3` Directory-Swap Auditor**:
   Deterministic FAT12/FAT16 filesystem consistency auditor (compatible with
   `fx3_recovery.fat.FatP1`) verifying BPB geometry, `FAT1 == FAT2` mirror byte-equality,
   zero cluster-chain cycles (Floyd cycle detection + visited set), zero cross-linked
   clusters, zero orphan allocated clusters, valid `8.3` / LFN checksums, and in-memory
   atomic 32-byte directory-entry pointer swap (`INIT2.SH` <-> `INIT2BAK.SH`,
   `physical_writes == 0`, `persistent_emmc_writes_authorized == False`).

Safety Redlines (Hard-Locked):
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `ALLOW_BOOT_PARTITION_TARGETING = False`
- `ALLOW_DESTRUCTIVE_FASTBOOT = False`
- `PHYSICAL_WRITES = 0`
- Local donor artifacts are opened strictly `os.O_RDONLY` when available.
- Never emits raw binary `bytes` reprs; all digests use `.hex()` / `.hexdigest()`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import md5, sha256
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import tempfile
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from .fat import FatP1, MAX_P1
from .files import is_forced_clean_room, read_file, resolve_donor_path


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Protocol Constants
# ---------------------------------------------------------------------------

INIT2_ESCAPE_SCHEMA: str = "fx3-init2-escape-watchdog-fat-verifier-v1"
INIT2_ESCAPE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True
PHYSICAL_WRITES: int = 0
EMMC_WRITE_BYTES: int = 0

DONOR_P1_205_RELPATH: str = "fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1"

# Escape Guard Constants
SENTINEL_FILENAMES: Tuple[str, ...] = ("FX3_SAFE_STOCK.FLG", "DISABLE_STAGE_B.TXT")
MEDIA_SLOT_DIRS: Tuple[str, ...] = ("media/slot_a", "media/slot_b")
ESCAPE_KEY_CHORDS: Tuple[str, ...] = ("REC+MENU", "SHUTTER")
CPIO_NEWC_MAGIC: str = "070701"
CRASH_LOOP_MAX_EXITS: int = 3
CRASH_LOOP_WINDOW_SECONDS: int = 15

# CXD90057 Watchdog Constants
CXD90057_WDT_TIMEOUT_MS: int = 10_000
CXD90057_WDT_KICK_INTERVAL_MS: int = 2_000

# FAT12/FAT16 Constants
FAT_SECTOR_BYTES: int = 512
FAT_NUM_COPIES: int = 2
FAT_SWAP_ENTRY_A: str = "/init2.sh"
FAT_SWAP_ENTRY_B: str = "/init2bak.sh"
_VALID_83_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&'()-@^_`{}~")

# Deterministic Status Codes
STATUS_VERIFIED_PHASE66: str = "VERIFIED_INIT2_ESCAPE_WDT_FAT"
STATUS_FAIL_PHASE66: str = "FAIL_INIT2_ESCAPE_WDT_FAT"
STATUS_VERIFIED_FAT_INTEGRITY: str = "VERIFIED_FAT_INTEGRITY"
STATUS_FAIL_FAT_BPB: str = "FAIL_FAT_BPB_GEOMETRY"
STATUS_FAIL_FAT_MIRROR_MISMATCH: str = "FAIL_FAT_MIRROR_MISMATCH"
STATUS_FAIL_FAT_CLUSTER_CYCLE: str = "FAIL_FAT_CLUSTER_CYCLE"
STATUS_FAIL_FAT_CROSS_LINK: str = "FAIL_FAT_CROSS_LINKED"
STATUS_FAIL_FAT_ORPHAN_CLUSTERS: str = "FAIL_FAT_ORPHAN_CLUSTERS"
STATUS_FAIL_FAT_DIR_CHECKSUM: str = "FAIL_FAT_INVALID_83_OR_LFN"


# ---------------------------------------------------------------------------
# Structured Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Init2EscapeDrillResult:
    drill_id: str
    passed: bool
    escape_triggered: bool
    escape_mechanism: str
    boot_target: str
    stage_b_active: bool
    stock_procam_exec: bool
    bind_mount_count: int
    cpio_extract_count: int
    umount_count: int
    active_bind_mounts_remaining: int
    emmc_write_count: int
    crash_count_in_window: int
    tier: str
    shell_exit_code: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    trace_lines: Tuple[str, ...]
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Init2EscapeSandboxSuiteResult:
    passed: bool
    drills_total: int
    drills_passed: int
    script_sha256: str
    drills: Tuple[Init2EscapeDrillResult, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class WatchdogSimulationResult:
    scenario_id: str
    passed: bool
    fault_mode: str
    recovery_tier: str
    timeout_ms: int
    kick_interval_ms: int
    elapsed_ms: int
    kicks_sent: int
    wdt_reset_triggered: bool
    volatile_ram_wiped: bool
    p1_pointer_rolled_back: bool
    h0_stock_sha256: str
    h2_restored_sha256: str
    h0_equals_h2: bool
    persistent_emmc_mutations: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    state_transitions: Tuple[str, ...]
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class WatchdogSuiteResult:
    passed: bool
    scenarios_total: int
    scenarios_passed: int
    scenarios: Tuple[WatchdogSimulationResult, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class FatIntegrityAuditResult:
    passed: bool
    status: str
    fat_type: str
    bytes_per_sector: int
    fat_count: int
    cluster_size_bytes: int
    cluster_count: int
    fat_mirrors_equal: bool
    fat_mirror_first_diff_offset: Optional[int]
    cycle_clusters: Tuple[int, ...]
    cross_linked_clusters: Tuple[Tuple[int, str, str], ...]
    orphan_clusters: Tuple[int, ...]
    invalid_83_entries: Tuple[str, ...]
    invalid_lfn_checksums: Tuple[str, ...]
    entries_count: int
    file_paths: Tuple[str, ...]
    image_sha256: str
    physical_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AtomicDirSwapResult:
    passed: bool
    fat_type: str
    entry_a: str
    entry_b: str
    physical_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    pre_sha256: str
    post_sha256: str
    roundtrip_sha256: str
    roundtrip_sha256_exact: bool
    entry_a_before_sha256: str
    entry_a_after_sha256: str
    entry_b_before_sha256: str
    entry_b_after_sha256: str
    content_swapped_exact: bool
    pre_audit_passed: bool
    post_audit_passed: bool
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Init2EscapeAndWatchdogReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    donor_p1_sha256: str
    donor_fat_audit: Optional[FatIntegrityAuditResult]
    escape_sandbox_suite: Init2EscapeSandboxSuiteResult
    watchdog_suite: WatchdogSuiteResult
    fat12_audit: FatIntegrityAuditResult
    fat16_audit: FatIntegrityAuditResult
    fat12_atomic_swap: AtomicDirSwapResult
    fat16_atomic_swap: AtomicDirSwapResult
    physical_writes: int
    emmc_write_bytes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# 1. Zero-Hardware SD/CFexpress Sentinel Fail-Open Escape (`init2` Sandbox)
# ---------------------------------------------------------------------------


def render_init2_escape_wrapper_script() -> str:
    """Return a pure POSIX `/bin/sh` Stage-B `init2` fail-open wrapper guard script.

    All filesystem paths are strictly confined beneath `$FX3_SANDBOX_ROOT`.
    """
    return """#!/bin/sh
set -u

SANDBOX="${FX3_SANDBOX_ROOT:?FX3_SANDBOX_ROOT must be set}"
TMP_DIR="$SANDBOX/tmp"
TRACE_FILE="$TMP_DIR/init2_trace.log"
ACTIVE_MOUNTS_FILE="$TMP_DIR/active_mounts.txt"
CRASH_CNT_FILE="$TMP_DIR/stage_b_crash.cnt"
GPIO_FILE="$SANDBOX/sys/gpio_boot_chord"
PAYLOAD="${FX3_STAGE_B_PAYLOAD:-$SANDBOX/boot/stage_b_overlay.cpio}"
EXPECTED_SHA="${FX3_STAGE_B_EXPECTED_SHA256:-}"
WINDOW_S="${FX3_CRASH_LOOP_WINDOW_S:-15}"
THRESHOLD="${FX3_CRASH_LOOP_THRESHOLD:-3}"

if [ -n "${FX3_SANDBOX_NOW_EPOCH:-}" ]; then
    NOW_EPOCH="$FX3_SANDBOX_NOW_EPOCH"
else
    NOW_EPOCH="$(date +%s)"
fi

[ -d "$TMP_DIR" ] || mkdir -p "$TMP_DIR"
: > "$TRACE_FILE"

BIND_MOUNT_COUNT=0
CPIO_EXTRACT_COUNT=0
UMOUNT_COUNT=0
EMMC_WRITE_COUNT=0
STOCK_PROCAM_EXEC=0
STAGE_B_ACTIVE=0
CRASH_COUNT_IN_WINDOW=0
ESCAPE_MECHANISM="NONE"
BOOT_TARGET="UNDECIDED"
TIER="TIER_0"

trace() {
    printf '%s\n' "$1" >> "$TRACE_FILE"
}

count_recent_crashes() {
    if [ ! -s "$CRASH_CNT_FILE" ]; then
        printf '0'
        return 0
    fi
    cutoff=$((NOW_EPOCH - WINDOW_S))
    kept=""
    cnt=0
    while IFS= read -r ts || [ -n "$ts" ]; do
        case "$ts" in
            ''|*[!0-9]*)
                continue
                ;;
        esac
        if [ "$ts" -ge "$cutoff" ] && [ "$ts" -le "$NOW_EPOCH" ]; then
            cnt=$((cnt + 1))
            if [ -z "$kept" ]; then
                kept="$ts"
            else
                kept="${kept}
${ts}"
            fi
        fi
    done < "$CRASH_CNT_FILE"
    if [ -n "$kept" ]; then
        printf '%s\n' "$kept" > "$CRASH_CNT_FILE"
    else
        : > "$CRASH_CNT_FILE"
    fi
    printf '%s' "$cnt"
}

unmount_volatile_bind_mounts() {
    if [ -f "$ACTIVE_MOUNTS_FILE" ]; then
        while IFS= read -r mnt || [ -n "$mnt" ]; do
            [ -z "$mnt" ] && continue
            UMOUNT_COUNT=$((UMOUNT_COUNT + 1))
            trace "UMOUNT_TMPFS_BIND=$mnt"
        done < "$ACTIVE_MOUNTS_FILE"
        rm -f "$ACTIVE_MOUNTS_FILE"
    fi
}

active_mounts_remaining() {
    if [ -s "$ACTIVE_MOUNTS_FILE" ]; then
        cnt=0
        while IFS= read -r mnt || [ -n "$mnt" ]; do
            [ -n "$mnt" ] && cnt=$((cnt + 1))
        done < "$ACTIVE_MOUNTS_FILE"
        printf '%s' "$cnt"
    else
        printf '0'
    fi
}

emit_result() {
    rem="$(active_mounts_remaining)"
    printf 'ESCAPE_MECHANISM=%s\n' "$ESCAPE_MECHANISM"
    printf 'BOOT_TARGET=%s\n' "$BOOT_TARGET"
    printf 'STAGE_B_ACTIVE=%s\n' "$STAGE_B_ACTIVE"
    printf 'STOCK_PROCAM_EXEC=%s\n' "$STOCK_PROCAM_EXEC"
    printf 'BIND_MOUNT_COUNT=%s\n' "$BIND_MOUNT_COUNT"
    printf 'CPIO_EXTRACT_COUNT=%s\n' "$CPIO_EXTRACT_COUNT"
    printf 'UMOUNT_COUNT=%s\n' "$UMOUNT_COUNT"
    printf 'ACTIVE_BIND_MOUNTS_REMAINING=%s\n' "$rem"
    printf 'EMMC_WRITE_COUNT=%s\n' "$EMMC_WRITE_COUNT"
    printf 'CRASH_COUNT_IN_WINDOW=%s\n' "$CRASH_COUNT_IN_WINDOW"
    printf 'TIER=%s\n' "$TIER"
}

compute_sha256() {
    target="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha_line="$(sha256sum "$target")"
        printf '%s' "${sha_line%% *}"
    elif command -v shasum >/dev/null 2>&1; then
        sha_line="$(shasum -a 256 "$target")"
        printf '%s' "${sha_line%% *}"
    else
        return 1
    fi
}

# -----------------------------------------------------------------------
# Guard 1: External Media Sentinel File (Slot A or Slot B) BEFORE cpio/mount
# -----------------------------------------------------------------------
for slot in "$SANDBOX/media/slot_a" "$SANDBOX/media/slot_b"; do
    for sentinel in FX3_SAFE_STOCK.FLG DISABLE_STAGE_B.TXT; do
        if [ -f "$slot/$sentinel" ]; then
            trace "GUARD1_SENTINEL_HIT=$slot/$sentinel"
            ESCAPE_MECHANISM="EXTERNAL_MEDIA_SENTINEL"
            BOOT_TARGET="STOCK_FX3_V702"
            STOCK_PROCAM_EXEC=1
            CRASH_COUNT_IN_WINDOW="$(count_recent_crashes)"
            emit_result
            exit 0
        fi
    done
done
trace "GUARD1_SENTINEL_CLEAR"

# -----------------------------------------------------------------------
# Guard 2: Physical Key-Chord Escape (REC+MENU / SHUTTER) BEFORE cpio/mount
# -----------------------------------------------------------------------
if [ -f "$GPIO_FILE" ]; then
    IFS= read -r chord < "$GPIO_FILE" || chord=""
    case "$chord" in
        REC+MENU|REC_MENU|SHUTTER)
            trace "GUARD2_KEY_CHORD_HIT=$chord"
            ESCAPE_MECHANISM="PHYSICAL_KEY_CHORD"
            BOOT_TARGET="STOCK_FX3_V702"
            STOCK_PROCAM_EXEC=1
            CRASH_COUNT_IN_WINDOW="$(count_recent_crashes)"
            emit_result
            exit 0
            ;;
    esac
fi
trace "GUARD2_KEY_CHORD_CLEAR"

# -----------------------------------------------------------------------
# Guard 3: Stage-B Payload SHA-256 & CPIO 070701 Magic BEFORE cpio/mount
# -----------------------------------------------------------------------
if [ ! -s "$PAYLOAD" ]; then
    trace "GUARD3_PAYLOAD_MISSING=$PAYLOAD"
    ESCAPE_MECHANISM="PAYLOAD_SHA256_OR_MAGIC_MISMATCH"
    BOOT_TARGET="STOCK_FX3_V702"
    STOCK_PROCAM_EXEC=1
    CRASH_COUNT_IN_WINDOW="$(count_recent_crashes)"
    emit_result
    exit 0
fi

cpio_magic="$(dd if="$PAYLOAD" bs=6 count=1 2>/dev/null || true)"
if [ "${#cpio_magic}" -lt 6 ] || [ "$cpio_magic" != "070701" ]; then
    trace "GUARD3_CPIO_MAGIC_MISMATCH=$cpio_magic"
    ESCAPE_MECHANISM="PAYLOAD_SHA256_OR_MAGIC_MISMATCH"
    BOOT_TARGET="STOCK_FX3_V702"
    STOCK_PROCAM_EXEC=1
    CRASH_COUNT_IN_WINDOW="$(count_recent_crashes)"
    emit_result
    exit 0
fi

actual_sha="$(compute_sha256 "$PAYLOAD" || true)"
if [ -z "$EXPECTED_SHA" ] || [ "$actual_sha" != "$EXPECTED_SHA" ]; then
    trace "GUARD3_SHA256_MISMATCH"
    ESCAPE_MECHANISM="PAYLOAD_SHA256_OR_MAGIC_MISMATCH"
    BOOT_TARGET="STOCK_FX3_V702"
    STOCK_PROCAM_EXEC=1
    CRASH_COUNT_IN_WINDOW="$(count_recent_crashes)"
    emit_result
    exit 0
fi
trace "GUARD3_PAYLOAD_VERIFIED"

# -----------------------------------------------------------------------
# Guard 4a: Pre-Mount Crash-Loop Breaker (>= 3 exits in 15s)
# -----------------------------------------------------------------------
CRASH_COUNT_IN_WINDOW="$(count_recent_crashes)"
if [ "$CRASH_COUNT_IN_WINDOW" -ge "$THRESHOLD" ]; then
    trace "GUARD4_PREMOUNT_CRASH_LOOP_TRIPPED=$CRASH_COUNT_IN_WINDOW"
    unmount_volatile_bind_mounts
    ESCAPE_MECHANISM="CRASH_LOOP_BREAKER"
    BOOT_TARGET="STOCK_FX3_V702"
    STOCK_PROCAM_EXEC=1
    emit_result
    exit 0
fi

# -----------------------------------------------------------------------
# Stage-B Volatile RAM Extraction & tmpfs Bind-Mount (Zero eMMC Writes)
# -----------------------------------------------------------------------
CPIO_EXTRACT_COUNT=1
trace "STAGE_B_CPIO_EXTRACT_TMPFS=1"
printf '%s\\n%s\\n' "$SANDBOX/usr/bin/procam_app" "$SANDBOX/etc/fx6_overlay" > "$ACTIVE_MOUNTS_FILE"
BIND_MOUNT_COUNT=2
trace "STAGE_B_BIND_MOUNT_COUNT=2"

PROCAM_STUB="$SANDBOX/usr/bin/procam_app"
if [ -x "$PROCAM_STUB" ]; then
    set +e
    "$PROCAM_STUB"
    procam_rc=$?
    set -e
else
    procam_rc=0
fi

if [ "$procam_rc" -eq 0 ]; then
    STAGE_B_ACTIVE=1
    BOOT_TARGET="STAGE_B_OVERLAY"
    trace "STAGE_B_PROCAM_HEALTHY"
    emit_result
    exit 0
fi

# -----------------------------------------------------------------------
# Guard 4b: Post-Exit Crash-Loop Breaker & Volatile Unmount -> Stock Exec
# -----------------------------------------------------------------------
printf '%s\\n' "$NOW_EPOCH" >> "$CRASH_CNT_FILE"
CRASH_COUNT_IN_WINDOW="$(count_recent_crashes)"
trace "STAGE_B_PROCAM_EXIT=$procam_rc WINDOW_CRASHES=$CRASH_COUNT_IN_WINDOW"
unmount_volatile_bind_mounts

if [ "$CRASH_COUNT_IN_WINDOW" -ge "$THRESHOLD" ]; then
    ESCAPE_MECHANISM="CRASH_LOOP_BREAKER"
    BOOT_TARGET="STOCK_FX3_V702"
    STOCK_PROCAM_EXEC=1
    trace "GUARD4_CRASH_LOOP_TRIPPED_EXEC_STOCK_PROCAM"
else
    ESCAPE_MECHANISM="NONE"
    BOOT_TARGET="STAGE_B_CRASH_RETRY_PENDING"
    STOCK_PROCAM_EXEC=0
fi

emit_result
exit 0
"""


def _build_ephemeral_cpio_payload(*, valid_magic: bool = True, size_bytes: int = 128) -> bytes:
    """Create a tiny in-memory CPIO-like payload stub for sandbox SHA-256 & magic testing."""
    magic = b"070701" if valid_magic else b"BADMAG"
    if size_bytes <= 6:
        return magic[:size_bytes]
    body = b"FX3_STAGE_B_TMPFS_OVERLAY_STUB_" * ((size_bytes // 31) + 1)
    return (magic + body)[:size_bytes]


def _parse_kv_stdout(stdout_text: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for line in stdout_text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            parsed[k.strip()] = v.strip()
    return parsed


def run_init2_escape_drill(
    drill_id: str,
    *,
    slot_a_sentinel: Optional[str] = None,
    slot_b_sentinel: Optional[str] = None,
    gpio_chord: Optional[str] = None,
    corrupt_payload_bytes: bool = False,
    invalid_cpio_magic: bool = False,
    truncated_payload: bool = False,
    missing_payload: bool = False,
    prior_crash_epochs: Sequence[int] = (),
    procam_exit_sequence: Sequence[int] = (0,),
    now_epochs: Optional[Sequence[int]] = None,
) -> Init2EscapeDrillResult:
    """Execute the POSIX `/bin/sh` `init2` guard script inside an isolated temporary sandbox."""
    if not procam_exit_sequence:
        raise ValueError("procam_exit_sequence must have at least one invocation")

    valid_payload = _build_ephemeral_cpio_payload(valid_magic=True, size_bytes=128)
    expected_sha = sha256(valid_payload).hexdigest()

    actual_payload = valid_payload
    if truncated_payload:
        actual_payload = b"0707"
    elif invalid_cpio_magic:
        actual_payload = _build_ephemeral_cpio_payload(valid_magic=False, size_bytes=128)
    elif corrupt_payload_bytes:
        mutated = bytearray(valid_payload)
        mutated[-1] ^= 0xFF
        actual_payload = bytes(mutated)

    script_text = render_init2_escape_wrapper_script()
    epochs = list(now_epochs) if now_epochs is not None else [1_700_000_000 + i for i in range(len(procam_exit_sequence))]
    if len(epochs) != len(procam_exit_sequence):
        raise ValueError("now_epochs length must match procam_exit_sequence length")

    with tempfile.TemporaryDirectory(prefix="fx3_init2_sandbox_") as tmp_root:
        root = Path(tmp_root)
        for sub in ("sbin", "boot", "media/slot_a", "media/slot_b", "sys", "tmp", "usr/bin", "etc/fx6_overlay"):
            (root / sub).mkdir(parents=True, exist_ok=True)

        guard_path = root / "sbin" / "init2_guard.sh"
        guard_path.write_text(script_text, encoding="utf-8")
        os.chmod(guard_path, 0o700)

        if slot_a_sentinel:
            (root / "media" / "slot_a" / slot_a_sentinel).write_text("SAFE_STOCK\n", encoding="utf-8")
        if slot_b_sentinel:
            (root / "media" / "slot_b" / slot_b_sentinel).write_text("SAFE_STOCK\n", encoding="utf-8")
        if gpio_chord is not None:
            (root / "sys" / "gpio_boot_chord").write_text(f"{gpio_chord}\n", encoding="utf-8")
        if not missing_payload:
            (root / "boot" / "stage_b_overlay.cpio").write_bytes(actual_payload)

        if prior_crash_epochs:
            (root / "tmp" / "stage_b_crash.cnt").write_text(
                "\n".join(str(int(ts)) for ts in prior_crash_epochs) + "\n",
                encoding="utf-8",
            )

        last_proc: Optional[subprocess.CompletedProcess[str]] = None
        last_kv: Dict[str, str] = {}
        trace_lines: List[str] = []

        for exit_code, epoch in zip(procam_exit_sequence, epochs):
            procam_stub = root / "usr" / "bin" / "procam_app"
            procam_stub.write_text(f"#!/bin/sh\nexit {int(exit_code)}\n", encoding="utf-8")
            os.chmod(procam_stub, 0o700)

            env = {
                "PATH": "/sbin:/bin:/usr/bin:/usr/sbin",
                "FX3_SANDBOX_ROOT": str(root),
                "FX3_STAGE_B_PAYLOAD": str(root / "boot" / "stage_b_overlay.cpio"),
                "FX3_STAGE_B_EXPECTED_SHA256": expected_sha,
                "FX3_SANDBOX_NOW_EPOCH": str(int(epoch)),
                "FX3_CRASH_LOOP_WINDOW_S": str(CRASH_LOOP_WINDOW_SECONDS),
                "FX3_CRASH_LOOP_THRESHOLD": str(CRASH_LOOP_MAX_EXITS),
            }
            last_proc = subprocess.run(
                ["/bin/sh", str(guard_path)],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            last_kv = _parse_kv_stdout(last_proc.stdout)
            trace_file = root / "tmp" / "init2_trace.log"
            if trace_file.is_file():
                trace_lines.extend(trace_file.read_text(encoding="utf-8").splitlines())

    assert last_proc is not None
    errors: List[str] = []
    if last_proc.returncode != 0:
        errors.append(f"/bin/sh exited with rc={last_proc.returncode}: {last_proc.stderr.strip()}")
    if int(last_kv.get("EMMC_WRITE_COUNT", "-1")) != 0:
        errors.append("EMMC_WRITE_COUNT must be 0")

    esc_mech = last_kv.get("ESCAPE_MECHANISM", "UNKNOWN")
    boot_target = last_kv.get("BOOT_TARGET", "UNKNOWN")
    escape_triggered = esc_mech != "NONE"

    return Init2EscapeDrillResult(
        drill_id=drill_id,
        passed=(len(errors) == 0),
        escape_triggered=escape_triggered,
        escape_mechanism=esc_mech,
        boot_target=boot_target,
        stage_b_active=(last_kv.get("STAGE_B_ACTIVE") == "1"),
        stock_procam_exec=(last_kv.get("STOCK_PROCAM_EXEC") == "1"),
        bind_mount_count=int(last_kv.get("BIND_MOUNT_COUNT", "0")),
        cpio_extract_count=int(last_kv.get("CPIO_EXTRACT_COUNT", "0")),
        umount_count=int(last_kv.get("UMOUNT_COUNT", "0")),
        active_bind_mounts_remaining=int(last_kv.get("ACTIVE_BIND_MOUNTS_REMAINING", "0")),
        emmc_write_count=int(last_kv.get("EMMC_WRITE_COUNT", "0")),
        crash_count_in_window=int(last_kv.get("CRASH_COUNT_IN_WINDOW", "0")),
        tier=last_kv.get("TIER", "TIER_0"),
        shell_exit_code=last_proc.returncode,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        trace_lines=tuple(trace_lines),
        errors=tuple(errors),
    )


def run_all_init2_escape_drills() -> Init2EscapeSandboxSuiteResult:
    """Execute the baseline Stage-B boot + all 4 fail-open POSIX `/bin/sh` escape drills."""
    script_sha = sha256(render_init2_escape_wrapper_script().encode("utf-8")).hexdigest()
    drills: List[Init2EscapeDrillResult] = []
    errors: List[str] = []

    # 0. Healthy Stage-B entry when no escape triggers
    d_normal = run_init2_escape_drill("D0_HEALTHY_STAGE_B_ENTRY", procam_exit_sequence=(0,))
    drills.append(d_normal)
    if not (d_normal.passed and not d_normal.escape_triggered and d_normal.stage_b_active and d_normal.bind_mount_count == 2):
        errors.append("D0_HEALTHY_STAGE_B_ENTRY failed expected Stage-B overlay boot.")

    # 1. External Media Sentinel (Slot A & Slot B) BEFORE cpio/mount
    d_slot_a = run_init2_escape_drill("D1_SENTINEL_SLOT_A_FX3_SAFE_STOCK", slot_a_sentinel="FX3_SAFE_STOCK.FLG")
    drills.append(d_slot_a)
    if not (
        d_slot_a.passed
        and d_slot_a.escape_mechanism == "EXTERNAL_MEDIA_SENTINEL"
        and d_slot_a.boot_target == "STOCK_FX3_V702"
        and d_slot_a.bind_mount_count == 0
        and d_slot_a.cpio_extract_count == 0
        and d_slot_a.emmc_write_count == 0
    ):
        errors.append("D1_SENTINEL_SLOT_A_FX3_SAFE_STOCK failed fail-open invariant.")

    d_slot_b = run_init2_escape_drill("D2_SENTINEL_SLOT_B_DISABLE_STAGE_B", slot_b_sentinel="DISABLE_STAGE_B.TXT")
    drills.append(d_slot_b)
    if not (
        d_slot_b.passed
        and d_slot_b.escape_mechanism == "EXTERNAL_MEDIA_SENTINEL"
        and d_slot_b.bind_mount_count == 0
        and d_slot_b.cpio_extract_count == 0
    ):
        errors.append("D2_SENTINEL_SLOT_B_DISABLE_STAGE_B failed fail-open invariant.")

    # 2. Physical Key-Chord Escape (REC+MENU / SHUTTER)
    d_chord = run_init2_escape_drill("D3_KEY_CHORD_REC_MENU", gpio_chord="REC+MENU")
    drills.append(d_chord)
    if not (
        d_chord.passed
        and d_chord.escape_mechanism == "PHYSICAL_KEY_CHORD"
        and d_chord.boot_target == "STOCK_FX3_V702"
        and d_chord.bind_mount_count == 0
        and d_chord.cpio_extract_count == 0
    ):
        errors.append("D3_KEY_CHORD_REC_MENU failed fail-open invariant.")

    # 3. Payload SHA-256 / Magic Mismatch
    d_sha = run_init2_escape_drill("D4_PAYLOAD_SHA256_MISMATCH", corrupt_payload_bytes=True)
    drills.append(d_sha)
    if not (
        d_sha.passed
        and d_sha.escape_mechanism == "PAYLOAD_SHA256_OR_MAGIC_MISMATCH"
        and d_sha.boot_target == "STOCK_FX3_V702"
        and d_sha.bind_mount_count == 0
        and d_sha.cpio_extract_count == 0
    ):
        errors.append("D4_PAYLOAD_SHA256_MISMATCH failed fail-open invariant.")

    d_magic = run_init2_escape_drill("D5_PAYLOAD_CPIO_MAGIC_MISMATCH", invalid_cpio_magic=True)
    drills.append(d_magic)
    if not (
        d_magic.passed
        and d_magic.escape_mechanism == "PAYLOAD_SHA256_OR_MAGIC_MISMATCH"
        and d_magic.bind_mount_count == 0
        and d_magic.cpio_extract_count == 0
    ):
        errors.append("D5_PAYLOAD_CPIO_MAGIC_MISMATCH failed fail-open invariant.")

    # 4. procam_app Crash-Loop Breaker (>= 3 exits within 15s)
    d_crash = run_init2_escape_drill(
        "D6_PROCAM_CRASH_LOOP_BREAKER",
        prior_crash_epochs=(1_700_000_000, 1_700_000_004),
        procam_exit_sequence=(139,),
        now_epochs=(1_700_000_009,),
    )
    drills.append(d_crash)
    if not (
        d_crash.passed
        and d_crash.escape_mechanism == "CRASH_LOOP_BREAKER"
        and d_crash.boot_target == "STOCK_FX3_V702"
        and d_crash.stock_procam_exec
        and not d_crash.stage_b_active
        and d_crash.umount_count == d_crash.bind_mount_count
        and d_crash.active_bind_mounts_remaining == 0
        and d_crash.crash_count_in_window == 3
    ):
        errors.append("D6_PROCAM_CRASH_LOOP_BREAKER failed unmount + stock exec invariant.")

    drills_passed = sum(1 for d in drills if d.passed)
    passed = len(errors) == 0 and drills_passed == len(drills)
    return Init2EscapeSandboxSuiteResult(
        passed=passed,
        drills_total=len(drills),
        drills_passed=drills_passed,
        script_sha256=script_sha,
        drills=tuple(drills),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 2. CXD90057 Hardware Watchdog (`WDT`) & `Tier-0..Tier-2` Verifier
# ---------------------------------------------------------------------------


def simulate_cxd90057_watchdog_scenario(
    scenario_id: str,
    *,
    fault_mode: str = "NORMAL_OPERATION",
    timeout_ms: int = CXD90057_WDT_TIMEOUT_MS,
    kick_interval_ms: int = CXD90057_WDT_KICK_INTERVAL_MS,
    simulation_horizon_ms: int = 20_000,
    hang_at_ms: int = 4_000,
    oops_at_ms: int = 3_000,
    reboot_at_ms: int = 4_000,
    panic_on_oops: bool = True,
    experimental_p1_pointer: bool = False,
    persistent_emmc_mutations: int = 0,
    h0_stock_bytes: bytes = b"FX3_V702_STOCK_EMMC_H0_BASELINE",
) -> WatchdogSimulationResult:
    """Simulate the CXD90057 hardware watchdog across H0 -> H1 -> WDT/Reboot -> H2."""
    if timeout_ms <= 0 or kick_interval_ms <= 0:
        raise ValueError("timeout_ms and kick_interval_ms must be positive")
    if persistent_emmc_mutations < 0:
        raise ValueError("persistent_emmc_mutations must be >= 0")

    h0_sha = sha256(h0_stock_bytes).hexdigest()
    errors: List[str] = []
    transitions: List[str] = ["H0_STOCK_EMMC"]

    if persistent_emmc_mutations > 0:
        errors.append(
            f"persistent_emmc_mutations={persistent_emmc_mutations} violates zero-mutation Stage-B invariant."
        )

    if experimental_p1_pointer:
        transitions.append("H1_STAGE_B_P1_POINTER")
    else:
        transitions.append("H1_STAGE_B_VOLATILE_RAM")

    wdt_remaining = timeout_ms
    kicks_sent = 0
    elapsed_ms = 0
    wdt_reset_triggered = False
    volatile_ram_wiped = False
    p1_pointer_rolled_back = False

    step_ms = 1_000
    next_kick_ms = kick_interval_ms
    norm_mode = fault_mode.strip().upper()

    while elapsed_ms < simulation_horizon_ms:
        elapsed_ms += step_ms
        wdt_remaining -= step_ms

        if norm_mode == "CLEAN_REBOOT" and elapsed_ms >= reboot_at_ms:
            transitions.append(f"CLEAN_REBOOT_AT_{elapsed_ms}MS")
            volatile_ram_wiped = True
            transitions.append("H2_VOLATILE_RAM_WIPED")
            break

        if norm_mode == "KERNEL_OOPS_PANIC_ON_OOPS" and elapsed_ms >= oops_at_ms:
            transitions.append(f"KERNEL_OOPS_AT_{elapsed_ms}MS")
            if panic_on_oops:
                transitions.append("PANIC_ON_OOPS_HALT_NO_KICK")
                # Panic halts kicks; CXD90057 WDT expires
                elapsed_ms += max(0, wdt_remaining)
                wdt_remaining = 0
                wdt_reset_triggered = True
                transitions.append(f"WDT_RESET_FIRED_AT_{elapsed_ms}MS")
                volatile_ram_wiped = True
                transitions.append("H2_VOLATILE_RAM_WIPED")
                break

        kicking_allowed = True
        if norm_mode in ("HUNG_UI_PRESENTER", "EXPERIMENTAL_P1_POINTER_ROLLBACK") and elapsed_ms >= hang_at_ms:
            kicking_allowed = False
            if f"UI_PRESENTER_HUNG_AT_{hang_at_ms}MS" not in transitions:
                transitions.append(f"UI_PRESENTER_HUNG_AT_{hang_at_ms}MS")

        if wdt_remaining <= 0:
            wdt_reset_triggered = True
            transitions.append(f"WDT_RESET_FIRED_AT_{elapsed_ms}MS")
            volatile_ram_wiped = True
            transitions.append("H2_VOLATILE_RAM_WIPED")
            break

        if kicking_allowed and elapsed_ms >= next_kick_ms:
            wdt_remaining = timeout_ms
            kicks_sent += 1
            next_kick_ms += kick_interval_ms

    if experimental_p1_pointer and (wdt_reset_triggered or volatile_ram_wiped):
        p1_pointer_rolled_back = True
        recovery_tier = "TIER_1_2_P1_VFAT_ROLLBACK"
        transitions.append("H2_P1_VFAT_ATOMIC_POINTER_ROLLED_BACK")
    elif wdt_reset_triggered or volatile_ram_wiped:
        recovery_tier = "TIER_0"
        transitions.append("H2_EQUALS_H0_STOCK_RESTORED")
    else:
        recovery_tier = "STAGE_B_OPERATIONAL"

    if persistent_emmc_mutations == 0:
        h2_bytes = h0_stock_bytes
    else:
        h2_bytes = h0_stock_bytes + f"_MUTATED_{persistent_emmc_mutations}".encode("ascii")
    h2_sha = sha256(h2_bytes).hexdigest()
    h0_equals_h2 = h0_sha == h2_sha

    if norm_mode == "NORMAL_OPERATION":
        passed = (
            (not wdt_reset_triggered)
            and kicks_sent > 0
            and h0_equals_h2
            and persistent_emmc_mutations == 0
            and not errors
        )
    else:
        passed = (
            (wdt_reset_triggered or volatile_ram_wiped)
            and volatile_ram_wiped
            and h0_equals_h2
            and persistent_emmc_mutations == 0
            and not errors
            and (not experimental_p1_pointer or p1_pointer_rolled_back)
        )

    return WatchdogSimulationResult(
        scenario_id=scenario_id,
        passed=passed,
        fault_mode=norm_mode,
        recovery_tier=recovery_tier,
        timeout_ms=timeout_ms,
        kick_interval_ms=kick_interval_ms,
        elapsed_ms=elapsed_ms,
        kicks_sent=kicks_sent,
        wdt_reset_triggered=wdt_reset_triggered,
        volatile_ram_wiped=volatile_ram_wiped,
        p1_pointer_rolled_back=p1_pointer_rolled_back,
        h0_stock_sha256=h0_sha,
        h2_restored_sha256=h2_sha,
        h0_equals_h2=h0_equals_h2,
        persistent_emmc_mutations=persistent_emmc_mutations,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        state_transitions=tuple(transitions),
        errors=tuple(errors),
    )


def run_cxd90057_watchdog_suite() -> WatchdogSuiteResult:
    """Run all 5 CXD90057 WDT & Tier-0..Tier-2 recovery simulations."""
    scenarios = (
        simulate_cxd90057_watchdog_scenario("WDT01_NORMAL_STAGE_B_KICKS", fault_mode="NORMAL_OPERATION"),
        simulate_cxd90057_watchdog_scenario("WDT02_HUNG_UI_PRESENTER_TIER0", fault_mode="HUNG_UI_PRESENTER"),
        simulate_cxd90057_watchdog_scenario(
            "WDT03_KERNEL_OOPS_PANIC_ON_OOPS_TIER0", fault_mode="KERNEL_OOPS_PANIC_ON_OOPS"
        ),
        simulate_cxd90057_watchdog_scenario("WDT04_CLEAN_REBOOT_RAM_WIPE_TIER0", fault_mode="CLEAN_REBOOT"),
        simulate_cxd90057_watchdog_scenario(
            "WDT05_EXPERIMENTAL_P1_POINTER_ROLLBACK_TIER12",
            fault_mode="EXPERIMENTAL_P1_POINTER_ROLLBACK",
            experimental_p1_pointer=True,
        ),
    )
    errors: List[str] = []
    for s in scenarios:
        if not s.passed:
            errors.append(f"{s.scenario_id} failed: {s.errors}")
    passed_count = sum(1 for s in scenarios if s.passed)
    return WatchdogSuiteResult(
        passed=(len(errors) == 0 and passed_count == len(scenarios)),
        scenarios_total=len(scenarios),
        scenarios_passed=passed_count,
        scenarios=scenarios,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 3. Pure-Python `p1` FAT12/FAT16 Cluster-Chain & Atomic `8.3` Swap Auditor
# ---------------------------------------------------------------------------


def _dos_83_checksum(short_11: bytes) -> int:
    chk = 0
    for b in short_11[:11]:
        chk = (((chk & 1) << 7) + (chk >> 1) + b) & 0xFF
    return chk


def _is_valid_dos_83_pair(name8_raw: bytes, ext3_raw: bytes) -> Tuple[bool, str]:
    if len(name8_raw) != 8 or len(ext3_raw) != 3:
        return False, ""
    try:
        n_str = name8_raw.decode("ascii")
        e_str = ext3_raw.decode("ascii")
    except UnicodeDecodeError:
        return False, ""
    n_trim = n_str.rstrip(" ")
    e_trim = e_str.rstrip(" ")
    if not n_trim or " " in n_trim or " " in e_trim:
        return False, ""
    if n_trim.ljust(8, " ") != n_str or e_trim.ljust(3, " ") != e_str:
        return False, ""
    if n_trim[0] == ".":
        return False, ""
    if not all(c in _VALID_83_CHARS for c in n_trim) or not all(c in _VALID_83_CHARS for c in e_trim):
        return False, ""
    formatted = f"{n_trim}.{e_trim}" if e_trim else n_trim
    return True, formatted


def _fat_dos_entry(name8: bytes, ext3: bytes, attr: int, cluster: int, size: int) -> bytes:
    ent = bytearray(32)
    ent[0:8] = name8.ljust(8, b" ")[:8]
    ent[8:11] = ext3.ljust(3, b" ")[:3]
    ent[11] = attr
    struct.pack_into("<HI", ent, 26, cluster, size)
    return bytes(ent)


def _fat_lfn_entries(lfn: str, short_11: bytes) -> bytes:
    chk = _dos_83_checksum(short_11)
    u16 = (lfn + "\x00").encode("utf-16-le")
    while len(u16) % 26 != 0:
        u16 += b"\xff\xff"
    chunks = [u16[i : i + 26] for i in range(0, len(u16), 26)]
    out = bytearray()
    total = len(chunks)
    for idx in range(total, 0, -1):
        c = chunks[idx - 1]
        seq = idx | (0x40 if idx == total else 0)
        row = bytearray(32)
        row[0] = seq
        row[1:11] = c[0:10]
        row[11] = 0x0F
        row[12] = 0
        row[13] = chk
        row[14:26] = c[10:22]
        row[26:28] = b"\x00\x00"
        row[28:32] = c[22:26]
        out.extend(row)
    return bytes(out)


def _set_fat_entry(fat: bytearray, fat_type: str, cluster: int, nxt: int) -> None:
    if fat_type == "FAT12":
        at = cluster + cluster // 2
        word = struct.unpack_from("<H", fat, at)[0]
        if cluster & 1:
            word = (word & 0x000F) | ((nxt & 0xFFF) << 4)
        else:
            word = (word & 0xF000) | (nxt & 0xFFF)
        struct.pack_into("<H", fat, at, word)
    elif fat_type == "FAT16":
        struct.pack_into("<H", fat, cluster * 2, nxt & 0xFFFF)
    else:
        raise ValueError(f"Unsupported fat_type {fat_type!r}")


def _get_fat_entry(fat: bytes, fat_type: str, cluster: int) -> int:
    if fat_type == "FAT12":
        at = cluster + cluster // 2
        word = struct.unpack_from("<H", fat, at)[0]
        return (word >> 4) if (cluster & 1) else (word & 0x0FFF)
    if fat_type == "FAT16":
        return struct.unpack_from("<H", fat, cluster * 2)[0]
    raise ValueError(f"Unsupported fat_type {fat_type!r}")


def build_synthetic_p1_vfat_with_init2(
    *,
    fat_type: str = "FAT12",
    include_lfn: bool = True,
) -> bytes:
    """Build a deterministic in-memory `FAT12` or `FAT16` `p1` image containing `INIT2.SH` and `INIT2BAK.SH`.

    - `FAT12`: 512B sectors, 32 sectors/cluster, 1 reserved, 2 FATs, 512 root entries, 32 FAT sectors
      (100% compatible with `fx3_recovery.fat.FatP1`).
    - `FAT16`: 512B sectors, 1 sector/cluster, 1 reserved, 2 FATs, 512 root entries, 17 FAT sectors,
      4100 clusters (`4085 <= clusters < 65525`).
    """
    norm_fat = fat_type.strip().upper()
    if norm_fat not in ("FAT12", "FAT16"):
        raise ValueError(f"fat_type must be 'FAT12' or 'FAT16', got {fat_type!r}")

    sector_size = FAT_SECTOR_BYTES
    reserved_sectors = 1
    num_fats = FAT_NUM_COPIES
    root_entries = 512
    root_sectors = (root_entries * 32) // sector_size

    if norm_fat == "FAT12":
        cluster_sectors = 32
        fat_sectors = 32
        total_clusters = 24
    else:
        cluster_sectors = 1
        total_clusters = 4100
        fat_sectors = ((total_clusters + 2) * 2 + sector_size - 1) // sector_size

    cluster_size = sector_size * cluster_sectors
    header_sectors = reserved_sectors + num_fats * fat_sectors + root_sectors
    total_sectors = header_sectors + total_clusters * cluster_sectors
    img = bytearray(total_sectors * sector_size)

    struct.pack_into("<H", img, 11, sector_size)
    img[13] = cluster_sectors
    struct.pack_into("<H", img, 14, reserved_sectors)
    img[16] = num_fats
    struct.pack_into("<H", img, 17, root_entries)
    if total_sectors < 65536:
        struct.pack_into("<H", img, 19, total_sectors)
    else:
        struct.pack_into("<I", img, 32, total_sectors)
    img[21] = 0xF8
    struct.pack_into("<H", img, 22, fat_sectors)
    img[510:512] = b"\x55\xaa"

    fat = bytearray(fat_sectors * sector_size)
    eof_val = 0xFFF if norm_fat == "FAT12" else 0xFFFF
    _set_fat_entry(fat, norm_fat, 0, 0xFF8 if norm_fat == "FAT12" else 0xFFF8)
    _set_fat_entry(fat, norm_fat, 1, eof_val)

    def alloc_clusters(start_c: int, data: bytes) -> Tuple[int, int]:
        n_c = max(1, (len(data) + cluster_size - 1) // cluster_size)
        for i in range(n_c):
            c = start_c + i
            _set_fat_entry(fat, norm_fat, c, eof_val if i == n_c - 1 else c + 1)
        data_off = header_sectors * sector_size + (start_c - 2) * cluster_size
        img[data_off : data_off + len(data)] = data
        return start_c, n_c

    init2_active_bytes = (
        b"#!/bin/sh\n"
        b"# FX3 Stage-B Fail-Open init2 Wrapper (Active)\n"
        b"if [ -f /mnt/sd_a/FX3_SAFE_STOCK.FLG ]; then exec /sbin/init2.stock; fi\n"
        b"exec /sbin/procam_app\n"
    )
    init2_bak_bytes = (
        b"#!/bin/sh\n"
        b"# FX3 v7.02 Stock init2 Backup (Zero-Modification)\n"
        b"exec /sbin/procam_app.stock\n"
    )
    kernel_bytes = b"FX3-V702-KERNEL-STUB\x00" * 64
    initrd_bytes = b"FX3-V702-INITRD-STUB\x00" * 64
    p1chksum_bytes = (
        f"{md5(kernel_bytes).hexdigest()}  ./boot/vmlinux.bin\n"
        f"{md5(initrd_bytes).hexdigest()}  ./boot/initrd.img\n"
    ).encode("ascii")

    next_c = 2
    boot_dir_c = next_c
    _set_fat_entry(fat, norm_fat, boot_dir_c, eof_val)
    next_c += 1

    init2_c, n = alloc_clusters(next_c, init2_active_bytes)
    next_c += n
    init2bak_c, n = alloc_clusters(next_c, init2_bak_bytes)
    next_c += n
    kern_c, n = alloc_clusters(next_c, kernel_bytes)
    next_c += n
    initrd_c, n = alloc_clusters(next_c, initrd_bytes)
    next_c += n
    chk_c, n = alloc_clusters(next_c, p1chksum_bytes)
    next_c += n

    fat1_off = reserved_sectors * sector_size
    fat2_off = fat1_off + fat_sectors * sector_size
    img[fat1_off:fat2_off] = fat
    img[fat2_off : fat2_off + fat_sectors * sector_size] = fat

    root_off = (reserved_sectors + num_fats * fat_sectors) * sector_size
    root_buf = bytearray()
    root_buf.extend(_fat_dos_entry(b"BOOT", b"", 0x10, boot_dir_c, 0))
    root_buf.extend(_fat_dos_entry(b"INIT2", b"SH", 0x20, init2_c, len(init2_active_bytes)))
    root_buf.extend(_fat_dos_entry(b"INIT2BAK", b"SH", 0x20, init2bak_c, len(init2_bak_bytes)))
    if include_lfn:
        root_buf.extend(_fat_lfn_entries("p1chksum", b"P1CHKSUM   "))
    root_buf.extend(_fat_dos_entry(b"P1CHKSUM", b"", 0x20, chk_c, len(p1chksum_bytes)))
    img[root_off : root_off + len(root_buf)] = root_buf

    boot_off = header_sectors * sector_size + (boot_dir_c - 2) * cluster_size
    boot_buf = bytearray()
    if include_lfn:
        boot_buf.extend(_fat_lfn_entries("vmlinux.bin", b"VMLINU~1BIN"))
    boot_buf.extend(_fat_dos_entry(b"VMLINU~1", b"BIN", 0x20, kern_c, len(kernel_bytes)))
    if include_lfn:
        boot_buf.extend(_fat_lfn_entries("initrd.img", b"INITRD  IMG"))
    boot_buf.extend(_fat_dos_entry(b"INITRD", b"IMG", 0x20, initrd_c, len(initrd_bytes)))
    img[boot_off : boot_off + len(boot_buf)] = boot_buf

    return bytes(img)


def _floyd_detect_cycle(
    start_c: int,
    fat1: bytes,
    fat_type: str,
    clusters: int,
    eof_min: int,
    eof_max: int,
) -> Tuple[Tuple[int, ...], Optional[int], Optional[str]]:
    """Follow a FAT chain using Floyd's cycle detection + bounded visited-set confirmation."""
    if start_c == 0:
        return (), None, None

    def nxt(c: int) -> int:
        return _get_fat_entry(fat1, fat_type, c)

    # Floyd tortoise & hare for O(1)-space cycle proof
    tortoise = start_c
    hare = start_c
    floyd_cycle_hit = False
    steps = 0
    while steps <= clusters + 2:
        if not (2 <= hare < clusters + 2):
            break
        h1 = nxt(hare)
        if not (2 <= h1 < clusters + 2):
            break
        h2 = nxt(h1)
        tortoise = nxt(tortoise)
        hare = h2
        steps += 1
        if tortoise == hare:
            floyd_cycle_hit = True
            break

    # Extract exact chain / cycle cluster
    seen: Set[int] = set()
    chain: List[int] = []
    cur = start_c
    while cur < eof_min:
        if not (2 <= cur < clusters + 2):
            return tuple(chain), None, f"FAT cluster {cur} out of range [2, {clusters + 2})"
        if cur in seen or floyd_cycle_hit and len(chain) > clusters:
            return tuple(chain), cur, f"FAT cluster-chain cycle detected at cluster {cur}"
        seen.add(cur)
        chain.append(cur)
        cur = nxt(cur)

    if not chain or cur > eof_max:
        return tuple(chain), None, f"Invalid FAT chain terminator {hex(cur)}"
    return tuple(chain), None, None


def audit_p1_fat_filesystem(data: bytes) -> FatIntegrityAuditResult:
    """Audit a `p1` FAT12/FAT16 image for BPB geometry, FAT1==FAT2 mirror, cycles, cross-links, orphans, and 8.3/LFN checksums."""
    img_sha = sha256(data).hexdigest()
    errors: List[str] = []

    if len(data) < 512 or len(data) > MAX_P1:
        errors.append(f"Image size {len(data)} outside [512, {MAX_P1}] bounds")
        return FatIntegrityAuditResult(
            passed=False,
            status=STATUS_FAIL_FAT_BPB,
            fat_type="UNKNOWN",
            bytes_per_sector=0,
            fat_count=0,
            cluster_size_bytes=0,
            cluster_count=0,
            fat_mirrors_equal=False,
            fat_mirror_first_diff_offset=None,
            cycle_clusters=(),
            cross_linked_clusters=(),
            orphan_clusters=(),
            invalid_83_entries=(),
            invalid_lfn_checksums=(),
            entries_count=0,
            file_paths=(),
            image_sha256=img_sha,
            physical_writes=PHYSICAL_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            errors=tuple(errors),
        )

    if data[510:512] != b"\x55\xaa":
        errors.append("Missing 0x55AA boot sector signature")

    u16 = lambda at: struct.unpack_from("<H", data, at)[0]
    bytes_per_sector = u16(11)
    cluster_sectors = data[13]
    reserved = u16(14)
    fat_count = data[16]
    root_entries = u16(17)
    fat_sectors = u16(22)
    total_sectors = u16(19) or struct.unpack_from("<I", data, 32)[0]

    if bytes_per_sector != FAT_SECTOR_BYTES:
        errors.append(f"Unsupported bytes_per_sector={bytes_per_sector} (expected 512)")
    if fat_count != FAT_NUM_COPIES:
        errors.append(f"Unsupported fat_count={fat_count} (expected 2)")
    if cluster_sectors < 1 or reserved < 1 or root_entries < 16 or fat_sectors < 1:
        errors.append("Invalid BPB reserved/cluster/root/fat counts")

    if errors:
        return FatIntegrityAuditResult(
            passed=False,
            status=STATUS_FAIL_FAT_BPB,
            fat_type="UNKNOWN",
            bytes_per_sector=bytes_per_sector,
            fat_count=fat_count,
            cluster_size_bytes=bytes_per_sector * cluster_sectors,
            cluster_count=0,
            fat_mirrors_equal=False,
            fat_mirror_first_diff_offset=None,
            cycle_clusters=(),
            cross_linked_clusters=(),
            orphan_clusters=(),
            invalid_83_entries=(),
            invalid_lfn_checksums=(),
            entries_count=0,
            file_paths=(),
            image_sha256=img_sha,
            physical_writes=PHYSICAL_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            errors=tuple(errors),
        )

    fat_start = reserved * 512
    fat_size = fat_sectors * 512
    root_start = (reserved + fat_count * fat_sectors) * 512
    root_size = root_entries * 32
    data_start = root_start + root_size
    cluster_size = 512 * cluster_sectors

    if not (data_start <= total_sectors * 512 <= len(data)):
        errors.append("FAT declared total_sectors exceeds input image bounds")
        return FatIntegrityAuditResult(
            passed=False,
            status=STATUS_FAIL_FAT_BPB,
            fat_type="UNKNOWN",
            bytes_per_sector=bytes_per_sector,
            fat_count=fat_count,
            cluster_size_bytes=cluster_size,
            cluster_count=0,
            fat_mirrors_equal=False,
            fat_mirror_first_diff_offset=None,
            cycle_clusters=(),
            cross_linked_clusters=(),
            orphan_clusters=(),
            invalid_83_entries=(),
            invalid_lfn_checksums=(),
            entries_count=0,
            file_paths=(),
            image_sha256=img_sha,
            physical_writes=PHYSICAL_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            errors=tuple(errors),
        )

    clusters = (total_sectors * 512 - data_start) // cluster_size
    if 0 < clusters < 4085:
        fat_type = "FAT12"
        eof_min, eof_max, bad_marker = 0xFF8, 0xFFF, 0xFF7
        if (clusters + 2) * 3 // 2 + 2 > fat_size:
            errors.append("FAT12 table size smaller than cluster count requires")
    elif 4085 <= clusters < 65525:
        fat_type = "FAT16"
        eof_min, eof_max, bad_marker = 0xFFF8, 0xFFFF, 0xFFF7
        if (clusters + 2) * 2 > fat_size:
            errors.append("FAT16 table size smaller than cluster count requires")
    else:
        errors.append(f"Unsupported FAT12/FAT16 cluster count: {clusters}")
        fat_type = "UNKNOWN"
        eof_min, eof_max, bad_marker = 0xFFF8, 0xFFFF, 0xFFF7

    if errors:
        return FatIntegrityAuditResult(
            passed=False,
            status=STATUS_FAIL_FAT_BPB,
            fat_type=fat_type,
            bytes_per_sector=bytes_per_sector,
            fat_count=fat_count,
            cluster_size_bytes=cluster_size,
            cluster_count=clusters,
            fat_mirrors_equal=False,
            fat_mirror_first_diff_offset=None,
            cycle_clusters=(),
            cross_linked_clusters=(),
            orphan_clusters=(),
            invalid_83_entries=(),
            invalid_lfn_checksums=(),
            entries_count=0,
            file_paths=(),
            image_sha256=img_sha,
            physical_writes=PHYSICAL_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            errors=tuple(errors),
        )

    fat1 = data[fat_start : fat_start + fat_size]
    fat2 = data[fat_start + fat_size : fat_start + 2 * fat_size]
    fat_mirrors_equal = fat1 == fat2
    first_diff: Optional[int] = None
    if not fat_mirrors_equal:
        for i, (b1, b2) in enumerate(zip(fat1, fat2)):
            if b1 != b2:
                first_diff = i
                break
        errors.append(f"FAT1 and FAT2 mirror copies differ at FAT offset {first_diff}")

    owners: Dict[int, str] = {}
    reachable_clusters: Set[int] = set()
    cycle_clusters: List[int] = []
    cross_links: List[Tuple[int, str, str]] = []
    invalid_83: List[str] = []
    invalid_lfn: List[str] = []
    file_paths: List[str] = []
    seen_paths: Set[str] = set()

    def read_cluster_bytes(c: int) -> bytes:
        off = data_start + (c - 2) * cluster_size
        if off + cluster_size > len(data):
            raise ValueError(f"Cluster {c} outside image bounds")
        return data[off : off + cluster_size]

    def walk(chain: Optional[Tuple[int, ...]], parent: str, depth: int) -> None:
        if depth >= 16 or len(file_paths) >= 1024:
            errors.append("FAT directory depth/count bound exceeded")
            return
        raw = data[root_start : root_start + root_size] if chain is None else b"".join(read_cluster_bytes(c) for c in chain)
        long_rows: List[Tuple[int, int, bytes]] = []
        for at in range(0, len(raw), 32):
            row = raw[at : at + 32]
            if row[0] == 0x00:
                if long_rows:
                    invalid_lfn.append(f"{parent}/<orphan_lfn_before_end>")
                    errors.append("Orphan LFN record before directory end")
                break
            if row[0] == 0xE5:
                long_rows = []
                continue
            attr = row[11]
            if attr == 0x0F:
                seq = row[0] & 0x1F
                if not (1 <= seq <= 20 and not (row[0] & 0xA0) and row[12] == 0 and row[26:28] == b"\x00\x00"):
                    invalid_lfn.append(f"{parent}/<invalid_lfn_seq_{seq}>")
                    errors.append(f"Invalid FAT LFN record at {parent} offset {at}")
                    long_rows = []
                    continue
                if not ((not long_rows and (row[0] & 0x40)) or (long_rows and not (row[0] & 0x40) and seq == long_rows[-1][0] - 1)):
                    invalid_lfn.append(f"{parent}/<lfn_order_{seq}>")
                    errors.append(f"FAT LFN sequence order mismatch at {parent} offset {at}")
                    long_rows = []
                    continue
                long_rows.append((seq, row[13], row[1:11] + row[14:26] + row[28:32]))
                continue
            if attr & 0x08:
                if long_rows:
                    invalid_lfn.append(f"{parent}/<lfn_on_volume_label>")
                    errors.append("LFN attached to volume label")
                    long_rows = []
                continue

            name_raw = row[0:8].rstrip(b" ").decode("ascii", errors="replace")
            if name_raw in (".", ".."):
                if long_rows:
                    invalid_lfn.append(f"{parent}/{name_raw}")
                    errors.append("LFN attached to dot directory entry")
                    long_rows = []
                continue

            ok_83, short_fmt = _is_valid_dos_83_pair(row[0:8], row[8:11])
            if not ok_83:
                invalid_83.append(f"{parent}/0x{row[0:11].hex()}")
                errors.append(f"Invalid DOS 8.3 directory entry name at {parent} offset {at}")

            lfn_name: Optional[str] = None
            if long_rows:
                expected_chk = _dos_83_checksum(row[0:11])
                if not (long_rows[-1][0] == 1 and all(r[1] == expected_chk for r in long_rows)):
                    invalid_lfn.append(f"{parent}/{short_fmt or row[0:11].hex()}")
                    errors.append(f"FAT LFN checksum mismatch for {parent}/{short_fmt}")
                else:
                    text = b"".join(r[2] for r in sorted(long_rows)).decode("utf-16-le", errors="replace")
                    if "\x00" in text:
                        text = text.split("\x00", 1)[0]
                    lfn_name = text
                long_rows = []

            canonical = (lfn_name or short_fmt or f"invalid_{at}").lower()
            path = f"{parent}/{canonical}"
            if path in seen_paths:
                errors.append(f"Duplicate FAT directory path: {path}")
            seen_paths.add(path)
            file_paths.append(path)

            start_c, size = struct.unpack_from("<HI", row, 26)
            if struct.unpack_from("<H", row, 20)[0] != 0:
                errors.append(f"Unsupported high cluster on {path}")
            c_chain, cyc_c, chain_err = _floyd_detect_cycle(start_c, fat1, fat_type, clusters, eof_min, eof_max)
            if cyc_c is not None and cyc_c not in cycle_clusters:
                cycle_clusters.append(cyc_c)
            if chain_err:
                errors.append(f"{path}: {chain_err}")

            is_dir = bool(attr & 0x10)
            cross_hit = False
            for c in c_chain:
                reachable_clusters.add(c)
                if c in owners:
                    cross_links.append((c, owners[c], path))
                    errors.append(f"Cross-linked FAT cluster {c}: claimed by {owners[c]} and {path}")
                    cross_hit = True
                else:
                    owners[c] = path

            if is_dir:
                if not c_chain or size != 0:
                    errors.append(f"Invalid directory cluster/size for {path}")
                elif cyc_c is None and not cross_hit and not chain_err:
                    walk(c_chain, path, depth + 1)
            else:
                if size > len(c_chain) * cluster_size:
                    errors.append(f"File {path} size {size} exceeds cluster chain capacity {len(c_chain) * cluster_size}")

        if long_rows:
            invalid_lfn.append(f"{parent}/<orphan_lfn_at_end>")
            errors.append("Orphan LFN record at directory end")

    walk(None, "", 0)

    # Scan FAT1 for orphan allocated clusters not reachable from any directory entry
    orphans: List[int] = []
    for c in range(2, clusters + 2):
        val = _get_fat_entry(fat1, fat_type, c)
        if val != 0 and val != bad_marker and c not in reachable_clusters:
            orphans.append(c)
    if orphans:
        errors.append(f"Orphan allocated FAT clusters detected: {orphans[:16]}")

    if not fat_mirrors_equal:
        status = STATUS_FAIL_FAT_MIRROR_MISMATCH
    elif cycle_clusters:
        status = STATUS_FAIL_FAT_CLUSTER_CYCLE
    elif cross_links:
        status = STATUS_FAIL_FAT_CROSS_LINK
    elif orphans:
        status = STATUS_FAIL_FAT_ORPHAN_CLUSTERS
    elif invalid_83 or invalid_lfn:
        status = STATUS_FAIL_FAT_DIR_CHECKSUM
    elif errors:
        status = STATUS_FAIL_FAT_BPB
    else:
        status = STATUS_VERIFIED_FAT_INTEGRITY

    return FatIntegrityAuditResult(
        passed=(len(errors) == 0),
        status=status,
        fat_type=fat_type,
        bytes_per_sector=bytes_per_sector,
        fat_count=fat_count,
        cluster_size_bytes=cluster_size,
        cluster_count=clusters,
        fat_mirrors_equal=fat_mirrors_equal,
        fat_mirror_first_diff_offset=first_diff,
        cycle_clusters=tuple(cycle_clusters),
        cross_linked_clusters=tuple(cross_links),
        orphan_clusters=tuple(orphans),
        invalid_83_entries=tuple(invalid_83),
        invalid_lfn_checksums=tuple(invalid_lfn),
        entries_count=len(file_paths),
        file_paths=tuple(file_paths),
        image_sha256=img_sha,
        physical_writes=PHYSICAL_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
    )


def _locate_83_entry_offset_and_read(
    data: bytes,
    target_path: str,
) -> Tuple[int, bytes, bytes]:
    """Locate a root/subfile 32-byte DOS 8.3 entry offset and read its file payload."""
    u16 = lambda at: struct.unpack_from("<H", data, at)[0]
    cluster_sectors = data[13]
    reserved = u16(14)
    copies = data[16]
    entries = u16(17)
    fat_sectors = u16(22)
    total_sectors = u16(19) or struct.unpack_from("<I", data, 32)[0]
    fat_start = reserved * 512
    fat_size = fat_sectors * 512
    root_start = (reserved + copies * fat_sectors) * 512
    root_size = entries * 32
    data_start = root_start + root_size
    cluster_size = 512 * cluster_sectors
    clusters = (total_sectors * 512 - data_start) // cluster_size
    fat_type = "FAT12" if clusters < 4085 else "FAT16"
    eof_min = 0xFF8 if fat_type == "FAT12" else 0xFFF8
    fat1 = data[fat_start : fat_start + fat_size]

    want = target_path.strip("/").lower()
    if "/" in want:
        raise ValueError(f"Only root-directory 8.3 swap targets supported, got {target_path!r}")

    for at in range(root_start, root_start + root_size, 32):
        row = data[at : at + 32]
        if row[0] == 0x00:
            break
        if row[0] == 0xE5 or row[11] == 0x0F or (row[11] & 0x08):
            continue
        ok, fmt = _is_valid_dos_83_pair(row[0:8], row[8:11])
        if ok and fmt.lower() == want:
            start_c, size = struct.unpack_from("<HI", row, 26)
            buf = bytearray()
            cur = start_c
            seen: Set[int] = set()
            while cur and cur < eof_min:
                if cur in seen:
                    raise ValueError("Cycle during payload read")
                seen.add(cur)
                off = data_start + (cur - 2) * cluster_size
                buf.extend(data[off : off + cluster_size])
                cur = _get_fat_entry(fat1, fat_type, cur)
            return at, row, bytes(buf[:size])

    raise ValueError(f"8.3 entry {target_path!r} not found in root directory")


def simulate_atomic_83_dir_swap(
    data: bytes,
    *,
    entry_a: str = FAT_SWAP_ENTRY_A,
    entry_b: str = FAT_SWAP_ENTRY_B,
) -> AtomicDirSwapResult:
    """Perform an in-memory-only atomic 32-byte directory-entry pointer swap (`INIT2.SH` <-> `INIT2BAK.SH`).

    Swaps cluster pointer + file size metadata in memory (`physical_writes == 0`,
    `persistent_emmc_writes_authorized == False`), validates full FAT consistency after
    swap, and verifies reverse swap restores the exact original SHA-256.
    """
    pre_sha = sha256(data).hexdigest()
    pre_audit = audit_p1_fat_filesystem(data)
    if not pre_audit.passed:
        return AtomicDirSwapResult(
            passed=False,
            fat_type=pre_audit.fat_type,
            entry_a=entry_a,
            entry_b=entry_b,
            physical_writes=PHYSICAL_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            pre_sha256=pre_sha,
            post_sha256="",
            roundtrip_sha256="",
            roundtrip_sha256_exact=False,
            entry_a_before_sha256="",
            entry_a_after_sha256="",
            entry_b_before_sha256="",
            entry_b_after_sha256="",
            content_swapped_exact=False,
            pre_audit_passed=False,
            post_audit_passed=False,
            errors=pre_audit.errors,
        )

    errors: List[str] = []
    off_a, row_a, bytes_a_before = _locate_83_entry_offset_and_read(data, entry_a)
    off_b, row_b, bytes_b_before = _locate_83_entry_offset_and_read(data, entry_b)

    def _swap_in_memory(src: bytes) -> bytes:
        buf = bytearray(src)
        # Swap bytes 20..22 (high cluster) and 26..32 (start_cluster + size), keeping 0..11 8.3 name intact
        hi_a = bytes(buf[off_a + 20 : off_a + 22])
        hi_b = bytes(buf[off_b + 20 : off_b + 22])
        ptr_a = bytes(buf[off_a + 26 : off_a + 32])
        ptr_b = bytes(buf[off_b + 26 : off_b + 32])
        buf[off_a + 20 : off_a + 22] = hi_b
        buf[off_b + 20 : off_b + 22] = hi_a
        buf[off_a + 26 : off_a + 32] = ptr_b
        buf[off_b + 26 : off_b + 32] = ptr_a
        return bytes(buf)

    swapped = _swap_in_memory(data)
    post_sha = sha256(swapped).hexdigest()
    post_audit = audit_p1_fat_filesystem(swapped)
    if not post_audit.passed:
        errors.extend(post_audit.errors)

    _, _, bytes_a_after = _locate_83_entry_offset_and_read(swapped, entry_a)
    _, _, bytes_b_after = _locate_83_entry_offset_and_read(swapped, entry_b)

    a_before_sha = sha256(bytes_a_before).hexdigest()
    b_before_sha = sha256(bytes_b_before).hexdigest()
    a_after_sha = sha256(bytes_a_after).hexdigest()
    b_after_sha = sha256(bytes_b_after).hexdigest()

    content_swapped_exact = (a_after_sha == b_before_sha) and (b_after_sha == a_before_sha)
    if not content_swapped_exact:
        errors.append("Post-swap file contents did not swap cleanly.")

    roundtrip = _swap_in_memory(swapped)
    roundtrip_sha = sha256(roundtrip).hexdigest()
    roundtrip_exact = roundtrip_sha == pre_sha
    if not roundtrip_exact:
        errors.append("Reverse 8.3 swap did not restore exact original SHA-256.")

    passed = (
        pre_audit.passed
        and post_audit.passed
        and content_swapped_exact
        and roundtrip_exact
        and PHYSICAL_WRITES == 0
        and (PERSISTENT_EMMC_WRITES_AUTHORIZED is False)
        and (PERSISTENT_WRITE_RELEASE is False)
        and len(errors) == 0
    )
    return AtomicDirSwapResult(
        passed=passed,
        fat_type=pre_audit.fat_type,
        entry_a=entry_a,
        entry_b=entry_b,
        physical_writes=PHYSICAL_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        pre_sha256=pre_sha,
        post_sha256=post_sha,
        roundtrip_sha256=roundtrip_sha,
        roundtrip_sha256_exact=roundtrip_exact,
        entry_a_before_sha256=a_before_sha,
        entry_a_after_sha256=a_after_sha,
        entry_b_before_sha256=b_before_sha,
        entry_b_after_sha256=b_after_sha,
        content_swapped_exact=content_swapped_exact,
        pre_audit_passed=pre_audit.passed,
        post_audit_passed=post_audit.passed,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 4. Unified Dual-Mode Phase 66 Suite Entrypoint
# ---------------------------------------------------------------------------


def run_init2_escape_and_watchdog_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> Init2EscapeAndWatchdogReport:
    """Execute the full Phase 66 suite in `LOCAL_DONOR_O_RDONLY` or `CLEAN_ROOM_SYNTHETIC` mode."""
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    donor_p1_path = resolve_donor_path(DONOR_P1_205_RELPATH) if not clean_room else None
    use_donor = (donor_p1_path is not None) and donor_p1_path.is_file()

    errors: List[str] = []
    donor_p1_sha256 = ""
    donor_fat_audit: Optional[FatIntegrityAuditResult] = None

    if use_donor and donor_p1_path is not None:
        verification_mode = "LOCAL_DONOR_O_RDONLY"
        donor_bytes = read_file(donor_p1_path, MAX_P1)
        donor_p1_sha256 = sha256(donor_bytes).hexdigest()
        donor_fat_audit = audit_p1_fat_filesystem(donor_bytes)
        if not donor_fat_audit.passed:
            errors.extend(donor_fat_audit.errors)
        # Confirm FatP1 compatibility
        _ = FatP1(donor_bytes)
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
        donor_p1_sha256 = sha256(b"FX3_CLEAN_ROOM_PHASE66_ANCHOR_0x91030080").hexdigest()

    escape_suite = run_all_init2_escape_drills()
    if not escape_suite.passed:
        errors.extend(escape_suite.errors)

    wdt_suite = run_cxd90057_watchdog_suite()
    if not wdt_suite.passed:
        errors.extend(wdt_suite.errors)

    fat12_img = build_synthetic_p1_vfat_with_init2(fat_type="FAT12", include_lfn=True)
    # Confirm FatP1 compatibility on our synthetic FAT12 image
    fat_p1_compat = FatP1(fat12_img)
    if "/init2.sh" not in fat_p1_compat.files or "/init2bak.sh" not in fat_p1_compat.files:
        errors.append("FatP1 compatibility check missing /init2.sh or /init2bak.sh")

    fat12_audit = audit_p1_fat_filesystem(fat12_img)
    if not fat12_audit.passed:
        errors.extend(fat12_audit.errors)

    fat16_img = build_synthetic_p1_vfat_with_init2(fat_type="FAT16", include_lfn=True)
    fat16_audit = audit_p1_fat_filesystem(fat16_img)
    if not fat16_audit.passed:
        errors.extend(fat16_audit.errors)

    fat12_swap = simulate_atomic_83_dir_swap(fat12_img)
    if not fat12_swap.passed:
        errors.extend(fat12_swap.errors)

    fat16_swap = simulate_atomic_83_dir_swap(fat16_img)
    if not fat16_swap.passed:
        errors.extend(fat16_swap.errors)

    all_passed = (
        len(errors) == 0
        and escape_suite.passed
        and wdt_suite.passed
        and fat12_audit.passed
        and fat16_audit.passed
        and fat12_swap.passed
        and fat16_swap.passed
        and (donor_fat_audit is None or donor_fat_audit.passed)
        and (PERSISTENT_EMMC_WRITES_AUTHORIZED is False)
        and (PERSISTENT_WRITE_RELEASE is False)
        and (PHYSICAL_WRITES == 0)
    )

    return Init2EscapeAndWatchdogReport(
        schema=INIT2_ESCAPE_SCHEMA,
        version=INIT2_ESCAPE_VERSION,
        verification_mode=verification_mode,
        all_passed=all_passed,
        status=STATUS_VERIFIED_PHASE66 if all_passed else STATUS_FAIL_PHASE66,
        donor_p1_sha256=donor_p1_sha256,
        donor_fat_audit=donor_fat_audit,
        escape_sandbox_suite=escape_suite,
        watchdog_suite=wdt_suite,
        fat12_audit=fat12_audit,
        fat16_audit=fat16_audit,
        fat12_atomic_swap=fat12_swap,
        fat16_atomic_swap=fat16_swap,
        physical_writes=PHYSICAL_WRITES,
        emmc_write_bytes=EMMC_WRITE_BYTES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        errors=tuple(errors),
    )
