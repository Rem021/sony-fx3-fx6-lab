"""4-Layer Fail-Safe Automatic Rollback State-Machine & Sandboxed POSIX `sh` Drill Runner.

Executes deterministic state-machine verification AND real POSIX `/bin/sh` subprocess drills
against the Stage-A RAM-Overlay boot guard (`etc/fx6_overlay/init2_guard.sh`) strictly inside
an ephemeral `tempfile.TemporaryDirectory()` via `PREFIX` injection (never touching host `/dev`
or `/tmp` root paths):

- **Scenario 1 (No one-shot arm token)**: `arm_once` absent -> 100% stock FX3 boot branch and
  zero overlay mounts.
- **Scenario 2 (Normal single-boot + reboot auto-revert)**: `arm_once` present -> unlinks token
  *before* execution, passes 10-component SHA-256 manifest verification, mounts RAM overlay on
  Boot #1; simulated power-loss / Boot #2 automatically reverts 100% to stock FX3 branch because
  the one-shot token was already cleared (zero boot-loop).
- **Scenario 3 (Component SHA-256 mismatch or missing)**: guard immediately aborts overlay mount,
  cleans temporary mount staging, and safely falls back to stock FX3 branch.
- **Scenario 4 (Watchdog timeout / non-zero exit fallback)**: child process exits non-zero or
  exceeds watchdog timeout -> guard automatically unmounts/cleans overlay, falls back to stock
  FX3 branch with explicit diagnostic code, and verifies **0 writes** across all simulated eMMC
  partitions (`sector0`, `p2`, `p6`, `p15`, `p18`).
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .patcher import DEFAULT_FX3_MODULES_DIR, DEFAULT_FX6_DONOR_LIB_DIR
from .ram_overlay_packager import (
    StageARamOverlayBundle,
    build_stage_a_ram_overlay_package,
    extract_cpio_newc_to_dir,
)


SIMULATED_EMMC_PARTITIONS: Tuple[str, ...] = ("sector0", "p2", "p6", "p15", "p18")


@dataclass(frozen=True)
class StateMachineTrace:
    states: Tuple[str, ...]
    boot_branch: str
    diag_code_prefix: str
    token_present_after: bool
    active_overlay_mounts: int
    emmc_writes: int


@dataclass(frozen=True)
class EmmcPartitionSnapshot:
    partition_id: str
    size_bytes: int
    sha256: str
    mtime_ns: int


@dataclass(frozen=True)
class SubprocessBootRunResult:
    step_id: str
    returncode: int
    boot_branch: str
    diag_code: str
    stock_boot_invoked: bool
    adapted_boot_invoked: bool
    token_cleared_before_exec: bool
    token_present_after: bool
    child_observed_token_absent: Optional[bool]
    active_overlay_mount_count: int
    active_loop_count: int
    mount_work_dir_cleaned: bool
    sandbox_violation_count: int
    emmc_write_count: int
    state_machine_matched: bool


@dataclass(frozen=True)
class ScenarioDrillResult:
    scenario_id: str
    title: str
    passed: bool
    runs: Tuple[SubprocessBootRunResult, ...]
    emmc_writes_detected: int
    notes: str


@dataclass(frozen=True)
class RollbackDrillReport:
    all_scenarios_passed: bool
    scenario_count: int
    total_subprocess_runs: int
    total_emmc_writes: int
    total_sandbox_violations: int
    emmc_partitions_verified: Tuple[str, ...]
    overlay_cpio_sha256: str
    overlay_cpio_size: int
    failsafe_hook_verified: bool
    scenarios: Tuple[ScenarioDrillResult, ...]
    temp_dir_cleaned: bool


def simulate_failsafe_state_machine(
    *,
    arm_once_present: bool,
    manifest_component_present: bool = True,
    manifest_sha256_valid: bool = True,
    child_exit_code: int = 0,
    child_timed_out: bool = False,
    heartbeat_written: bool = True,
) -> StateMachineTrace:
    """Deterministic formal state-machine reference for the 4-Layer Fail-Safe Boot Guard."""
    states: List[str] = ["INIT_CHECK_TOKEN"]
    if not arm_once_present:
        states.append("STOCK_FX3_BOOTED")
        return StateMachineTrace(
            states=tuple(states),
            boot_branch="STOCK_FX3",
            diag_code_prefix="STOCK_UNARMED",
            token_present_after=False,
            active_overlay_mounts=0,
            emmc_writes=0,
        )

    states.append("CLEAR_TOKEN_BEFORE_EXEC")
    states.append("VERIFY_MANIFEST_SHA256")

    if not manifest_component_present:
        states.extend(["CLEANUP_AND_FALLBACK_STOCK", "STOCK_FX3_BOOTED"])
        return StateMachineTrace(
            states=tuple(states),
            boot_branch="STOCK_FX3_FALLBACK",
            diag_code_prefix="ERR_MANIFEST_COMPONENT_MISSING",
            token_present_after=False,
            active_overlay_mounts=0,
            emmc_writes=0,
        )

    if not manifest_sha256_valid:
        states.extend(["CLEANUP_AND_FALLBACK_STOCK", "STOCK_FX3_BOOTED"])
        return StateMachineTrace(
            states=tuple(states),
            boot_branch="STOCK_FX3_FALLBACK",
            diag_code_prefix="ERR_MANIFEST_SHA256_MISMATCH",
            token_present_after=False,
            active_overlay_mounts=0,
            emmc_writes=0,
        )

    states.extend(["MOUNT_RAM_OVERLAY", "SUPERVISE_ADAPTED_BOOT"])

    if child_timed_out:
        states.extend(["CLEANUP_AND_FALLBACK_STOCK", "STOCK_FX3_BOOTED"])
        return StateMachineTrace(
            states=tuple(states),
            boot_branch="STOCK_FX3_FALLBACK",
            diag_code_prefix="ERR_WATCHDOG_TIMEOUT_FALLBACK",
            token_present_after=False,
            active_overlay_mounts=0,
            emmc_writes=0,
        )

    if child_exit_code != 0 or not heartbeat_written:
        states.extend(["CLEANUP_AND_FALLBACK_STOCK", "STOCK_FX3_BOOTED"])
        return StateMachineTrace(
            states=tuple(states),
            boot_branch="STOCK_FX3_FALLBACK",
            diag_code_prefix=f"ERR_CHILD_NONZERO_FALLBACK:{child_exit_code}",
            token_present_after=False,
            active_overlay_mounts=0,
            emmc_writes=0,
        )

    states.append("ADAPTED_FX6_BOOTED")
    return StateMachineTrace(
        states=tuple(states),
        boot_branch="ADAPTED_FX6_OVERLAY",
        diag_code_prefix="OK_ADAPTED_SINGLE_BOOT",
        token_present_after=False,
        active_overlay_mounts=3,
        emmc_writes=0,
    )


def _generate_sandbox_busybox_shim() -> str:
    """Generate a sandbox-enforcing POSIX `/bin/sh` mock `busybox` inside `$PREFIX/mock_bin`."""
    return """#!/bin/sh
# Sandbox mock busybox for deterministic Stage-A rollback drills.
# Strictly enforces that every absolute path stays under $PREFIX (except /dev/null).
set -eu

if [ -z "${PREFIX:-}" ]; then
    echo "ERR_BUSYBOX_SHIM_MISSING_PREFIX" >&2
    exit 99
fi

RUN_DIR="${PREFIX}/run"
EMMC_DIR="${PREFIX}/emmc_partitions"
MOUNTS_DB="${RUN_DIR}/active_mounts.db"
LOOPS_DB="${RUN_DIR}/active_loops.db"
VIOLATIONS_LOG="${RUN_DIR}/sandbox_violations.log"
EMMC_WRITES_LOG="${RUN_DIR}/emmc_write_attempts.log"

mkdir -p "$RUN_DIR"
touch "$MOUNTS_DB" "$LOOPS_DB"

for ARG in "$@"; do
    case "$ARG" in
        /dev/null) ;;
        /*)
            case "$ARG" in
                "${PREFIX}"/*|"${PREFIX}") ;;
                *)
                    echo "SANDBOX_ESCAPE:$ARG" >> "$VIOLATIONS_LOG"
                    exit 99
                    ;;
            esac
            case "$ARG" in
                "${EMMC_DIR}"/*|"${EMMC_DIR}")
                    echo "EMMC_ACCESS:$ARG" >> "$EMMC_WRITES_LOG"
                    exit 98
                    ;;
            esac
            ;;
    esac
done

SUBCMD="${1:-}"
shift || true

case "$SUBCMD" in
    sync)
        echo "sync" >> "${RUN_DIR}/sync.log"
        exit 0
        ;;
    losetup)
        if [ "${1:-}" = "-d" ]; then
            LOOP_DEV="${2:-}"
            TMP_DB="${LOOPS_DB}.tmp"
            grep -v "^${LOOP_DEV}|" "$LOOPS_DB" > "$TMP_DB" 2>/dev/null || true
            mv "$TMP_DB" "$LOOPS_DB"
            rm -f "$LOOP_DEV" 2>/dev/null || true
            exit 0
        else
            LOOP_DEV="${1:-}"
            IMG_PATH="${2:-}"
            if [ ! -f "$IMG_PATH" ]; then
                exit 1
            fi
            mkdir -p "$(dirname "$LOOP_DEV")"
            : > "$LOOP_DEV"
            TMP_DB="${LOOPS_DB}.tmp"
            grep -v "^${LOOP_DEV}|" "$LOOPS_DB" > "$TMP_DB" 2>/dev/null || true
            echo "${LOOP_DEV}|${IMG_PATH}" >> "$TMP_DB"
            mv "$TMP_DB" "$LOOPS_DB"
            exit 0
        fi
        ;;
    mount)
        if [ "${1:-}" = "--bind" ]; then
            SRC="${2:-}"
            DST="${3:-}"
            if [ ! -e "$SRC" ] || [ ! -e "$DST" ]; then
                exit 1
            fi
            TMP_DB="${MOUNTS_DB}.tmp"
            grep -v "|${DST}$" "$MOUNTS_DB" > "$TMP_DB" 2>/dev/null || true
            echo "bind|${SRC}|${DST}" >> "$TMP_DB"
            mv "$TMP_DB" "$MOUNTS_DB"
            exit 0
        elif [ "${1:-}" = "-t" ]; then
            # mount -t vfat -o shortname=mixed <src> <dst>
            SRC="${5:-}"
            DST="${6:-}"
            if [ ! -e "$SRC" ] || [ ! -d "$DST" ]; then
                exit 1
            fi
            TMP_DB="${MOUNTS_DB}.tmp"
            grep -v "|${DST}$" "$MOUNTS_DB" > "$TMP_DB" 2>/dev/null || true
            echo "vfat|${SRC}|${DST}" >> "$TMP_DB"
            mv "$TMP_DB" "$MOUNTS_DB"
            exit 0
        fi
        exit 1
        ;;
    umount)
        if [ "${1:-}" = "-l" ]; then
            DST="${2:-}"
        else
            DST="${1:-}"
        fi
        TMP_DB="${MOUNTS_DB}.tmp"
        grep -v "|${DST}$" "$MOUNTS_DB" > "$TMP_DB" 2>/dev/null || true
        mv "$TMP_DB" "$MOUNTS_DB"
        exit 0
        ;;
    pidof)
        exit 0
        ;;
    dmesg)
        echo "sandbox_dmesg"
        exit 0
        ;;
    reboot)
        echo "reboot $*" >> "${RUN_DIR}/reboot.log"
        exit 0
        ;;
    *)
        exit 1
        ;;
esac
"""


def _snapshot_emmc_partitions(emmc_dir: Path) -> Dict[str, EmmcPartitionSnapshot]:
    snaps: Dict[str, EmmcPartitionSnapshot] = {}
    for part_id in SIMULATED_EMMC_PARTITIONS:
        p = emmc_dir / f"{part_id}.bin"
        st = p.stat()
        raw = p.read_bytes()
        snaps[part_id] = EmmcPartitionSnapshot(
            partition_id=part_id,
            size_bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            mtime_ns=st.st_mtime_ns,
        )
    return snaps


def _count_emmc_mutations(
    before: Dict[str, EmmcPartitionSnapshot],
    after: Dict[str, EmmcPartitionSnapshot],
    emmc_writes_log: Path,
) -> int:
    mutations = 0
    for part_id in SIMULATED_EMMC_PARTITIONS:
        b = before[part_id]
        a = after[part_id]
        if (b.sha256 != a.sha256) or (b.size_bytes != a.size_bytes) or (b.mtime_ns != a.mtime_ns):
            mutations += 1
    if emmc_writes_log.is_file():
        lines = [ln for ln in emmc_writes_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
        mutations += len(lines)
    return mutations


def _parse_kv_env_file(path: Path) -> Dict[str, str]:
    if not path.is_file():
        return {}
    out: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _count_nonempty_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())


def _reset_volatile_ram_mounts_on_reboot(prefix: Path) -> None:
    """Simulate volatile RAM tmpfs reset across camera power-cycle / reboot."""
    for db_name in ("active_mounts.db", "active_loops.db"):
        db_path = prefix / "run" / db_name
        if db_path.exists():
            db_path.write_text("", encoding="utf-8")
    shm_dir = prefix / "dev" / "shm"
    if shm_dir.is_dir():
        for child in shm_dir.iterdir():
            if child.is_file():
                child.unlink()
    for transient in ("nflasha20", "cnflasha20", "pnflasha20", "nflasha21", "loop7"):
        p = prefix / "dev" / transient
        if p.exists() or p.is_symlink():
            p.unlink()


def run_four_layer_rollback_drill(
    *,
    overlay_bundle: Optional[StageARamOverlayBundle] = None,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
) -> RollbackDrillReport:
    """Run all 4 mandatory fail-safe rollback scenarios in a `PREFIX`-isolated POSIX `sh` sandbox."""
    bundle = overlay_bundle or build_stage_a_ram_overlay_package(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )

    with tempfile.TemporaryDirectory(prefix="fx6_rollback_drill_") as tmp_str:
        prefix = Path(tmp_str).resolve()

        # 1. Extract Stage-A CPIO archive (`etc/fx6_overlay/*`) under $PREFIX
        extract_cpio_newc_to_dir(bundle.cpio_bytes, prefix)
        guard_script_path = prefix / "etc" / "fx6_overlay" / "init2_guard.sh"

        # 2. Stage all 10 runtime overlay components under $PREFIX/tmp/fx6_stage_a
        stage_dir = prefix / "tmp" / "fx6_stage_a"
        for rel_path, blob in bundle.staged_runtime_blobs.items():
            target = stage_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)

        # 3. Create simulated FX3 p30 LUT device nodes inside $PREFIX/dev (never touching host /dev)
        dev_dir = prefix / "dev"
        dev_dir.mkdir(parents=True, exist_ok=True)
        (dev_dir / "cnflasha30").write_bytes(b"FX3_P30_DECRYPTED_STUB")
        (dev_dir / "pnflasha30").write_bytes(b"FX3_P30_PHYSICAL_STUB")

        # 4. Create simulated read-only eMMC partitions (sector0, p2, p6, p15, p18)
        emmc_dir = prefix / "emmc_partitions"
        emmc_dir.mkdir(parents=True, exist_ok=True)
        for part_id in SIMULATED_EMMC_PARTITIONS:
            part_file = emmc_dir / f"{part_id}.bin"
            part_file.write_bytes(f"IMMUTABLE_FX3_EMMC_{part_id.upper()}_IMAGE\n".encode("ascii") * 16)
            part_file.chmod(0o444)

        baseline_emmc = _snapshot_emmc_partitions(emmc_dir)

        # 5. Install sandbox-enforcing mock `busybox` in $PREFIX/mock_bin
        mock_bin = prefix / "mock_bin"
        mock_bin.mkdir(parents=True, exist_ok=True)
        busybox_path = mock_bin / "busybox"
        busybox_path.write_text(_generate_sandbox_busybox_shim(), encoding="utf-8")
        busybox_path.chmod(0o755)

        host_tmp = prefix / "sandbox_tmpdir"
        host_tmp.mkdir(parents=True, exist_ok=True)

        arm_token_path = prefix / "tmp" / "mod_arm_once"
        state_env_path = prefix / "tmp" / "init2_guard_state.env"
        child_probe_path = prefix / "tmp" / "child_probe.env"
        stock_boot_marker = prefix / "tmp" / "stock_boot_marker.log"

        def _invoke_guard(
            step_id: str,
            expected_sm: StateMachineTrace,
            *,
            ap_boot_cmd: str = "",
            watchdog_sec: int = 5,
        ) -> SubprocessBootRunResult:
            if state_env_path.exists():
                state_env_path.unlink()
            if child_probe_path.exists():
                child_probe_path.unlink()
            if stock_boot_marker.exists():
                stock_boot_marker.unlink()

            env = {
                "PATH": f"{mock_bin}:/usr/bin:/bin",
                "PREFIX": str(prefix),
                "FX3_STAGE_A_DIR": str(stage_dir),
                "FX3_WATCHDOG_TIMEOUT_SEC": str(watchdog_sec),
                "FX3_STOCK_BOOT_CMD": f'echo "{step_id}" > "{stock_boot_marker}"',
                "TMPDIR": str(host_tmp),
                "LC_ALL": "C",
            }
            if ap_boot_cmd:
                env["FX3_AP_BOOT_CMD"] = ap_boot_cmd

            proc = subprocess.run(
                ["/bin/sh", str(guard_script_path)],
                cwd=str(prefix),
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )

            kv = _parse_kv_env_file(state_env_path)
            probe_kv = _parse_kv_env_file(child_probe_path)
            after_emmc = _snapshot_emmc_partitions(emmc_dir)
            emmc_writes = _count_emmc_mutations(
                baseline_emmc,
                after_emmc,
                prefix / "run" / "emmc_write_attempts.log",
            )
            violations = _count_nonempty_lines(prefix / "run" / "sandbox_violations.log")
            active_mounts = _count_nonempty_lines(prefix / "run" / "active_mounts.db")
            active_loops = _count_nonempty_lines(prefix / "run" / "active_loops.db")

            boot_branch = kv.get("BOOT_BRANCH", "UNKNOWN")
            diag_code = kv.get("DIAG_CODE", "UNKNOWN")
            stock_invoked = (kv.get("STOCK_BOOT_INVOKED") == "1") and stock_boot_marker.is_file()
            adapted_invoked = kv.get("ADAPTED_BOOT_INVOKED") == "1"
            token_cleared = kv.get("TOKEN_CLEARED_BEFORE_EXEC") == "1"
            token_after = arm_token_path.exists()
            child_saw_absent: Optional[bool] = None
            if "CHILD_OBSERVED_TOKEN_ABSENT" in probe_kv:
                child_saw_absent = probe_kv["CHILD_OBSERVED_TOKEN_ABSENT"] == "1"

            mount_work_cleaned = not (prefix / "tmp" / "fx6_mount_work").exists()

            sm_ok = (
                proc.returncode == 0
                and boot_branch == expected_sm.boot_branch
                and diag_code.startswith(expected_sm.diag_code_prefix)
                and token_after == expected_sm.token_present_after
                and active_mounts == expected_sm.active_overlay_mounts
                and emmc_writes == expected_sm.emmc_writes
                and violations == 0
            )

            return SubprocessBootRunResult(
                step_id=step_id,
                returncode=proc.returncode,
                boot_branch=boot_branch,
                diag_code=diag_code,
                stock_boot_invoked=stock_invoked,
                adapted_boot_invoked=adapted_invoked,
                token_cleared_before_exec=token_cleared,
                token_present_after=token_after,
                child_observed_token_absent=child_saw_absent,
                active_overlay_mount_count=active_mounts,
                active_loop_count=active_loops,
                mount_work_dir_cleaned=mount_work_cleaned,
                sandbox_violation_count=violations,
                emmc_write_count=emmc_writes,
                state_machine_matched=sm_ok,
            )

        try:
            scenarios: List[ScenarioDrillResult] = []

            # =====================================================================
            # Scenario 1: Unarmed boot (no arm_once token -> 100% stock FX3 branch)
            # =====================================================================
            if arm_token_path.exists():
                arm_token_path.unlink()
            sm_s1 = simulate_failsafe_state_machine(arm_once_present=False)
            r_s1 = _invoke_guard("S1_unarmed_boot", sm_s1)
            s1_ok = (
                r_s1.state_machine_matched
                and r_s1.stock_boot_invoked
                and not r_s1.adapted_boot_invoked
                and r_s1.active_overlay_mount_count == 0
                and r_s1.active_loop_count == 0
                and r_s1.emmc_write_count == 0
            )
            scenarios.append(
                ScenarioDrillResult(
                    scenario_id="S1_unarmed_stock_boot",
                    title="Unarmed Boot: No arm_once Token -> 100% Stock FX3 Branch & Zero Overlay Mounts",
                    passed=s1_ok,
                    runs=(r_s1,),
                    emmc_writes_detected=r_s1.emmc_write_count,
                    notes="Verified zero mounts, zero loop devices, and direct stock FX3 execution.",
                )
            )

            # =====================================================================
            # Scenario 2: Armed single-boot + simulated power-loss/reboot revert
            # =====================================================================
            arm_token_path.write_text("ARM_ONCE_TOKEN\n", encoding="utf-8")
            healthy_child_cmd = (
                f'if [ ! -f "{arm_token_path}" ]; then '
                f'echo "CHILD_OBSERVED_TOKEN_ABSENT=1" > "{child_probe_path}"; '
                f'else echo "CHILD_OBSERVED_TOKEN_ABSENT=0" > "{child_probe_path}"; fi; '
                f': > "{prefix}/dev/shm/fx3_ap_healthy"; exit 0'
            )
            sm_s2_boot1 = simulate_failsafe_state_machine(arm_once_present=True)
            r_s2_boot1 = _invoke_guard("S2_boot1_armed", sm_s2_boot1, ap_boot_cmd=healthy_child_cmd)
            p1_lut_symlinks_ok = (
                (prefix / "dev" / "nflasha20").is_symlink()
                and (prefix / "dev" / "cnflasha20").is_symlink()
                and (prefix / "dev" / "pnflasha20").is_symlink()
                and (prefix / "etc" / "opelog" / "ope" / "00").is_dir()
                and (prefix / "etc" / "opelog" / "ope" / "01").is_dir()
            )

            # Simulate sudden power-loss / second reboot (volatile RAM mounts cleared, no new token)
            _reset_volatile_ram_mounts_on_reboot(prefix)
            sm_s2_boot2 = simulate_failsafe_state_machine(arm_once_present=False)
            r_s2_boot2 = _invoke_guard("S2_boot2_reboot_revert", sm_s2_boot2)

            s2_ok = (
                r_s2_boot1.state_machine_matched
                and r_s2_boot1.token_cleared_before_exec
                and (r_s2_boot1.child_observed_token_absent is True)
                and not r_s2_boot1.token_present_after
                and r_s2_boot1.adapted_boot_invoked
                and not r_s2_boot1.stock_boot_invoked
                and r_s2_boot1.active_overlay_mount_count == 3
                and r_s2_boot1.active_loop_count == 1
                and p1_lut_symlinks_ok
                and r_s2_boot2.state_machine_matched
                and r_s2_boot2.stock_boot_invoked
                and not r_s2_boot2.adapted_boot_invoked
                and r_s2_boot2.active_overlay_mount_count == 0
                and r_s2_boot2.active_loop_count == 0
            )
            scenarios.append(
                ScenarioDrillResult(
                    scenario_id="S2_armed_single_boot_and_reboot_revert",
                    title="Armed Single-Boot (Clear-Before-Exec + SHA-256 Pass) & Second Reboot Auto-Revert to Stock",
                    passed=s2_ok,
                    runs=(r_s2_boot1, r_s2_boot2),
                    emmc_writes_detected=r_s2_boot1.emmc_write_count + r_s2_boot2.emmc_write_count,
                    notes="Boot #1 unlinked arm_once prior to child exec & mounted P1/P2/RAM overlay; Boot #2 reverted 100% to stock FX3.",
                )
            )

            # =====================================================================
            # Scenario 3: Component SHA-256 mismatch (3a) or missing file (3b)
            # =====================================================================
            appfw_stage_file = stage_dir / "lib" / "appFw.so"
            orig_appfw = appfw_stage_file.read_bytes()
            tampered_appfw = bytearray(orig_appfw)
            tampered_appfw[0] ^= 0xFF
            appfw_stage_file.write_bytes(bytes(tampered_appfw))

            arm_token_path.write_text("ARM_ONCE_TOKEN\n", encoding="utf-8")
            sm_s3_mismatch = simulate_failsafe_state_machine(
                arm_once_present=True,
                manifest_sha256_valid=False,
            )
            r_s3_mismatch = _invoke_guard("S3a_sha256_mismatch", sm_s3_mismatch)
            appfw_stage_file.write_bytes(orig_appfw)

            fan_stage_file = stage_dir / "lib" / "libfan.so"
            orig_fan = fan_stage_file.read_bytes()
            fan_stage_file.unlink()
            arm_token_path.write_text("ARM_ONCE_TOKEN\n", encoding="utf-8")
            sm_s3_missing = simulate_failsafe_state_machine(
                arm_once_present=True,
                manifest_component_present=False,
            )
            r_s3_missing = _invoke_guard("S3b_component_missing", sm_s3_missing)
            fan_stage_file.write_bytes(orig_fan)

            s3_ok = (
                r_s3_mismatch.state_machine_matched
                and r_s3_mismatch.stock_boot_invoked
                and not r_s3_mismatch.adapted_boot_invoked
                and r_s3_mismatch.mount_work_dir_cleaned
                and r_s3_mismatch.active_overlay_mount_count == 0
                and r_s3_mismatch.active_loop_count == 0
                and r_s3_missing.state_machine_matched
                and r_s3_missing.stock_boot_invoked
                and not r_s3_missing.adapted_boot_invoked
                and r_s3_missing.mount_work_dir_cleaned
                and r_s3_missing.active_overlay_mount_count == 0
                and r_s3_missing.active_loop_count == 0
            )
            scenarios.append(
                ScenarioDrillResult(
                    scenario_id="S3_sha256_mismatch_or_missing_fallback",
                    title="Manifest Component SHA-256 Mismatch or Missing -> Immediate Abort, Cleanup & Stock Fallback",
                    passed=s3_ok,
                    runs=(r_s3_mismatch, r_s3_missing),
                    emmc_writes_detected=r_s3_mismatch.emmc_write_count + r_s3_missing.emmc_write_count,
                    notes="Both corrupted appFw.so SHA-256 and missing libfan.so aborted before mount and reverted cleanly to stock FX3.",
                )
            )

            # =====================================================================
            # Scenario 4: Subprocess non-zero exit (4a) & watchdog timeout (4b)
            # =====================================================================
            arm_token_path.write_text("ARM_ONCE_TOKEN\n", encoding="utf-8")
            sm_s4_nonzero = simulate_failsafe_state_machine(
                arm_once_present=True,
                child_exit_code=139,
                heartbeat_written=False,
            )
            r_s4_nonzero = _invoke_guard(
                "S4a_child_nonzero_139",
                sm_s4_nonzero,
                ap_boot_cmd="exit 139",
                watchdog_sec=5,
            )

            arm_token_path.write_text("ARM_ONCE_TOKEN\n", encoding="utf-8")
            sm_s4_timeout = simulate_failsafe_state_machine(
                arm_once_present=True,
                child_timed_out=True,
                heartbeat_written=False,
            )
            r_s4_timeout = _invoke_guard(
                "S4b_watchdog_timeout",
                sm_s4_timeout,
                ap_boot_cmd="exec sleep 5",
                watchdog_sec=1,
            )

            s4_ok = (
                r_s4_nonzero.state_machine_matched
                and r_s4_nonzero.diag_code == "ERR_CHILD_NONZERO_FALLBACK:139"
                and r_s4_nonzero.stock_boot_invoked
                and not r_s4_nonzero.adapted_boot_invoked
                and r_s4_nonzero.active_overlay_mount_count == 0
                and r_s4_nonzero.active_loop_count == 0
                and r_s4_timeout.state_machine_matched
                and r_s4_timeout.diag_code == "ERR_WATCHDOG_TIMEOUT_FALLBACK"
                and r_s4_timeout.stock_boot_invoked
                and not r_s4_timeout.adapted_boot_invoked
                and r_s4_timeout.active_overlay_mount_count == 0
                and r_s4_timeout.active_loop_count == 0
                and r_s4_nonzero.emmc_write_count == 0
                and r_s4_timeout.emmc_write_count == 0
            )
            scenarios.append(
                ScenarioDrillResult(
                    scenario_id="S4_timeout_and_nonzero_exit_fallback",
                    title="Watchdog Timeout & Non-Zero Exit -> Automatic Overlay Unmount, Fallback & Zero eMMC Writes",
                    passed=s4_ok,
                    runs=(r_s4_nonzero, r_s4_timeout),
                    emmc_writes_detected=r_s4_nonzero.emmc_write_count + r_s4_timeout.emmc_write_count,
                    notes="Verified exit=139 and 1s watchdog timeout both unmounted all overlays/loop7, recorded explicit diagnostic codes, and wrote 0 bytes to eMMC.",
                )
            )
        finally:
            # Restore write bit on simulated eMMC files so TemporaryDirectory exits cleanly
            for part_id in SIMULATED_EMMC_PARTITIONS:
                part_file = emmc_dir / f"{part_id}.bin"
                if part_file.exists():
                    part_file.chmod(0o644)

    temp_cleaned = not Path(tmp_str).exists()
    all_runs = [r for sc in scenarios for r in sc.runs]
    total_writes = sum(r.emmc_write_count for r in all_runs)
    total_violations = sum(r.sandbox_violation_count for r in all_runs)
    all_ok = (
        len(scenarios) == 4
        and all(sc.passed for sc in scenarios)
        and total_writes == 0
        and total_violations == 0
        and bundle.failsafe_hook_audit.valid
        and temp_cleaned
    )

    return RollbackDrillReport(
        all_scenarios_passed=all_ok,
        scenario_count=len(scenarios),
        total_subprocess_runs=len(all_runs),
        total_emmc_writes=total_writes,
        total_sandbox_violations=total_violations,
        emmc_partitions_verified=SIMULATED_EMMC_PARTITIONS,
        overlay_cpio_sha256=bundle.cpio_sha256,
        overlay_cpio_size=bundle.cpio_size,
        failsafe_hook_verified=bundle.failsafe_hook_audit.valid,
        scenarios=tuple(scenarios),
        temp_dir_cleaned=temp_cleaned,
    )
