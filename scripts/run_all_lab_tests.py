#!/usr/bin/env python3
"""Unified Cross-Suite Lab Verification Runner & Clean-Room Binary/Bytecode Hygiene Auditor.

Orchestrates and times all four repository verification suites plus BYOF manifest and
tracked-tree clean-room hygiene checks with `PYTHONDONTWRITEBYTECODE=1` (`-B`):
1. `outputs/fx3-recovery-adapter/tests` (58 tests)
2. `outputs/fx3-safety/tests` (17 tests)
3. `outputs/fx6-on-fx3-closure/tests` (56 tests)
4. `outputs/fx3-vm-trial/tests` (16 tests — Track 1A `fx3-vm-trial` & Track 2 `fx3-vm` offline verification)
5. Bilingual `docs/BYOF-REPRODUCTION.md` SHA-256 manifest audit (`scripts/verify_byof_manifest.py`)
6. Tracked-tree clean-room binary/bytecode hygiene check (`git status --porcelain -uall`
   verifying zero untracked `.so` / `.elf` / `.ko` / `.cpio` / `.bin` / `.vfat` / `.pyc`
   artifacts, plus direct filesystem sweep of `outputs/fx3-safety` and `outputs/fx6-on-fx3-closure`).

Usage:
    /usr/bin/python3 -B scripts/run_all_lab_tests.py [--json] [--clean-only]
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import json
import os
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_BIN = "/usr/bin/python3"

FORBIDDEN_UNTRACKED_EXTENSIONS: Tuple[str, ...] = (
    ".so",
    ".elf",
    ".ko",
    ".cpio",
    ".bin",
    ".vfat",
    ".pyc",
)

STRICT_ZERO_ARTIFACT_DIRS: Tuple[str, ...] = (
    "outputs/fx3-safety",
    "outputs/fx6-on-fx3-closure",
)


@dataclass(frozen=True)
class LabSuiteSpec:
    suite_id: str
    display_name: str
    test_dir_rel: str
    pythonpath_Entries: Tuple[str, ...]


LAB_SUITES: Tuple[LabSuiteSpec, ...] = (
    LabSuiteSpec(
        suite_id="fx3_recovery_adapter",
        display_name="outputs/fx3-recovery-adapter/tests",
        test_dir_rel="outputs/fx3-recovery-adapter/tests",
        pythonpath_Entries=("outputs/fx3-recovery-adapter",),
    ),
    LabSuiteSpec(
        suite_id="fx3_safety",
        display_name="outputs/fx3-safety/tests",
        test_dir_rel="outputs/fx3-safety/tests",
        pythonpath_Entries=("outputs/fx3-safety",),
    ),
    LabSuiteSpec(
        suite_id="fx6_on_fx3_closure",
        display_name="outputs/fx6-on-fx3-closure/tests",
        test_dir_rel="outputs/fx6-on-fx3-closure/tests",
        pythonpath_Entries=("outputs/fx3-safety", "outputs/fx6-on-fx3-closure"),
    ),
    LabSuiteSpec(
        suite_id="fx3_vm_trial",
        display_name="outputs/fx3-vm-trial/tests",
        test_dir_rel="outputs/fx3-vm-trial/tests",
        pythonpath_Entries=("outputs/fx3-vm-trial",),
    ),
)


@dataclass(frozen=True)
class SuiteExecutionResult:
    suite_id: str
    display_name: str
    passed: bool
    return_code: int
    tests_ran: int
    elapsed_seconds: float
    summary_line: str


@dataclass(frozen=True)
class CleanRoomHygieneResult:
    clean: bool
    git_porcelain_checked: bool
    untracked_forbidden_files: Tuple[str, ...]
    direct_sweep_forbidden_files: Tuple[str, ...]
    elapsed_seconds: float
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ByofManifestAuditSummary:
    checked: bool
    passed: bool
    verification_mode: str
    en_entry_count: int
    zh_entry_count: int
    code_constants_checked: int
    live_donor_files_verified: int
    elapsed_seconds: float
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class UnifiedLabRunReport:
    all_passed: bool
    total_tests_ran: int
    suite_count: int
    total_elapsed_seconds: float
    suites: Tuple[SuiteExecutionResult, ...]
    byof_manifest: ByofManifestAuditSummary
    clean_room_hygiene: CleanRoomHygieneResult


def parse_git_porcelain_for_forbidden_artifacts(
    porcelain_output: str,
    forbidden_extensions: Sequence[str] = FORBIDDEN_UNTRACKED_EXTENSIONS,
) -> Tuple[str, ...]:
    """Extract untracked or newly staged files carrying forbidden binary/bytecode extensions."""
    lower_exts = tuple(ext.lower() for ext in forbidden_extensions)
    offenders: List[str] = []
    for raw_line in porcelain_output.splitlines():
        if len(raw_line) < 4:
            continue
        status_xy = raw_line[:2]
        path_part = raw_line[3:].strip()
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1].strip()
        path_part = path_part.strip('"')
        # Flag untracked (`??`) or newly added (`A`) binary/pyc files
        if status_xy == "??" or "A" in status_xy:
            if path_part.lower().endswith(lower_exts):
                offenders.append(path_part)
    return tuple(sorted(set(offenders)))


def audit_clean_room_hygiene(
    repo_root: Path = REPO_ROOT,
    *,
    strict_dirs: Sequence[str] = STRICT_ZERO_ARTIFACT_DIRS,
    forbidden_extensions: Sequence[str] = FORBIDDEN_UNTRACKED_EXTENSIONS,
) -> CleanRoomHygieneResult:
    """Verify zero untracked `.so`/`.elf`/`.ko`/`.cpio`/`.bin`/`.vfat`/`.pyc` files in repo."""
    t0 = time.monotonic()
    errors: List[str] = []
    lower_exts = tuple(ext.lower() for ext in forbidden_extensions)

    proc = subprocess.run(
        ["git", "status", "--porcelain", "-uall"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    porcelain_ok = proc.returncode == 0
    if not porcelain_ok:
        errors.append(f"git status --porcelain failed with rc={proc.returncode}: {proc.stderr.strip()}")
        untracked_hits: Tuple[str, ...] = ()
    else:
        untracked_hits = parse_git_porcelain_for_forbidden_artifacts(
            proc.stdout,
            forbidden_extensions=forbidden_extensions,
        )
        for hit in untracked_hits:
            errors.append(f"Untracked/added binary or bytecode residue in git status: {hit}")

    direct_hits: List[str] = []
    for rel_dir in strict_dirs:
        base = repo_root / rel_dir
        if not base.is_dir():
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.lower().startswith("stage")]
            for fn in files:
                if fn.lower().endswith(lower_exts):
                    rel_path = str((Path(root) / fn).relative_to(repo_root))
                    direct_hits.append(rel_path)
                    errors.append(f"Forbidden binary/bytecode residue in {rel_dir}: {rel_path}")

    elapsed = round(time.monotonic() - t0, 4)
    clean = porcelain_ok and len(untracked_hits) == 0 and len(direct_hits) == 0 and len(errors) == 0
    return CleanRoomHygieneResult(
        clean=clean,
        git_porcelain_checked=porcelain_ok,
        untracked_forbidden_files=untracked_hits,
        direct_sweep_forbidden_files=tuple(sorted(set(direct_hits))),
        elapsed_seconds=elapsed,
        errors=tuple(errors),
    )


def _parse_unittest_count_and_summary(stderr_text: str) -> Tuple[int, str]:
    ran_m = re.search(r"Ran\s+(\d+)\s+tests?\s+in\s+[0-9.]+s", stderr_text)
    count = int(ran_m.group(1)) if ran_m else 0
    non_empty = [ln.strip() for ln in stderr_text.splitlines() if ln.strip()]
    summary = non_empty[-1] if non_empty else ""
    return count, summary


def run_single_suite(spec: LabSuiteSpec, repo_root: Path = REPO_ROOT) -> SuiteExecutionResult:
    """Execute a single `unittest discover` suite with `-B` and `PYTHONDONTWRITEBYTECODE=1`."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    py_paths = [str((repo_root / rel).resolve()) for rel in spec.pythonpath_Entries]
    env["PYTHONPATH"] = os.pathsep.join(py_paths)

    python_exe = PYTHON_BIN if Path(PYTHON_BIN).is_file() else sys.executable
    cmd = [
        python_exe,
        "-B",
        "-m",
        "unittest",
        "discover",
        "-s",
        str(repo_root / spec.test_dir_rel),
        "-p",
        "test_*.py",
    ]
    t0 = time.monotonic()
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = round(time.monotonic() - t0, 4)
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    tests_ran, summary_line = _parse_unittest_count_and_summary(combined)
    passed = proc.returncode == 0 and tests_ran > 0
    return SuiteExecutionResult(
        suite_id=spec.suite_id,
        display_name=spec.display_name,
        passed=passed,
        return_code=proc.returncode,
        tests_ran=tests_ran,
        elapsed_seconds=elapsed,
        summary_line=summary_line,
    )


def run_byof_manifest_audit(repo_root: Path = REPO_ROOT) -> ByofManifestAuditSummary:
    """Execute `scripts/verify_byof_manifest.py --json` with `-B` and `PYTHONDONTWRITEBYTECODE=1`."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    python_exe = PYTHON_BIN if Path(PYTHON_BIN).is_file() else sys.executable
    script_path = repo_root / "scripts" / "verify_byof_manifest.py"
    t0 = time.monotonic()
    proc = subprocess.run(
        [python_exe, "-B", str(script_path), "--json"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = round(time.monotonic() - t0, 4)
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}

    passed = proc.returncode == 0 and bool(payload.get("all_checks_passed", False))
    errs = list(payload.get("errors", []))
    if proc.returncode != 0 and not errs:
        errs.append((proc.stderr or proc.stdout or f"rc={proc.returncode}").strip())
    return ByofManifestAuditSummary(
        checked=True,
        passed=passed,
        verification_mode=str(payload.get("verification_mode", "UNKNOWN")),
        en_entry_count=int(payload.get("en_entry_count", 0)),
        zh_entry_count=int(payload.get("zh_entry_count", 0)),
        code_constants_checked=int(payload.get("code_constants_checked", 0)),
        live_donor_files_verified=int(payload.get("live_donor_files_verified", 0)),
        elapsed_seconds=elapsed,
        errors=tuple(str(e) for e in errs),
    )


def run_all_lab_verifications(
    repo_root: Path = REPO_ROOT,
    *,
    clean_only: bool = False,
    stream_progress: bool = False,
) -> UnifiedLabRunReport:
    """Run all four lab unittest suites, BYOF manifest check, and clean-room binary/pyc hygiene audit."""
    overall_t0 = time.monotonic()
    suite_results: List[SuiteExecutionResult] = []

    if not clean_only:
        for idx, spec in enumerate(LAB_SUITES, start=1):
            if stream_progress:
                sys.stdout.write(f"[{idx}/{len(LAB_SUITES)}] Running {spec.display_name} ...\n")
                sys.stdout.flush()
            res = run_single_suite(spec, repo_root=repo_root)
            suite_results.append(res)
            if stream_progress:
                status_str = "PASS" if res.passed else "FAIL"
                sys.stdout.write(
                    f"    -> {status_str}: {res.tests_ran} tests in {res.elapsed_seconds:.2f}s ({res.summary_line})\n"
                )
                sys.stdout.flush()

        byof_summary = run_byof_manifest_audit(repo_root=repo_root)
        if stream_progress:
            b_str = "PASS" if byof_summary.passed else "FAIL"
            sys.stdout.write(
                f"[byof] docs/BYOF-REPRODUCTION.md manifest audit: {b_str} "
                f"({byof_summary.verification_mode}, en={byof_summary.en_entry_count}, "
                f"zh={byof_summary.zh_entry_count}, constants={byof_summary.code_constants_checked}, "
                f"live={byof_summary.live_donor_files_verified}) in {byof_summary.elapsed_seconds:.2f}s\n"
            )
            for err in byof_summary.errors:
                sys.stdout.write(f"    ! {err}\n")
            sys.stdout.flush()
    else:
        byof_summary = ByofManifestAuditSummary(
            checked=False,
            passed=True,
            verification_mode="SKIPPED_CLEAN_ONLY",
            en_entry_count=0,
            zh_entry_count=0,
            code_constants_checked=0,
            live_donor_files_verified=0,
            elapsed_seconds=0.0,
            errors=(),
        )

    hygiene = audit_clean_room_hygiene(repo_root=repo_root)
    if stream_progress:
        h_str = "CLEAN" if hygiene.clean else "DIRTY"
        sys.stdout.write(
            f"[hygiene] git status --porcelain binary/pyc audit: {h_str} ({hygiene.elapsed_seconds:.2f}s)\n"
        )
        for err in hygiene.errors:
            sys.stdout.write(f"    ! {err}\n")
        sys.stdout.flush()

    total_elapsed = round(time.monotonic() - overall_t0, 4)
    total_tests = sum(r.tests_ran for r in suite_results)
    suites_ok = all(r.passed for r in suite_results)
    all_passed = suites_ok and byof_summary.passed and hygiene.clean

    return UnifiedLabRunReport(
        all_passed=all_passed,
        total_tests_ran=total_tests,
        suite_count=len(suite_results),
        total_elapsed_seconds=total_elapsed,
        suites=tuple(suite_results),
        byof_manifest=byof_summary,
        clean_room_hygiene=hygiene,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_all_lab_tests.py",
        description="Run all Sony FX3/FX6 Lab unittest suites, BYOF manifest audit, and clean-room binary/pyc hygiene.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Emit structured JSON summary to stdout",
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Run only the tracked-tree clean-room binary/pyc hygiene audit",
    )
    args = parser.parse_args(argv)

    rep = run_all_lab_verifications(
        repo_root=REPO_ROOT,
        clean_only=args.clean_only,
        stream_progress=not args.emit_json,
    )

    if args.emit_json:
        sys.stdout.write(json.dumps(asdict(rep), indent=2) + "\n")
    else:
        overall = "ALL GREEN" if rep.all_passed else "FAILED"
        if args.clean_only:
            sys.stdout.write(
                f"\n=== Clean-Room Audit: {overall} in {rep.total_elapsed_seconds:.2f}s ===\n"
            )
        else:
            sys.stdout.write(
                f"\n=== Unified Lab Verification: {overall} — "
                f"{rep.total_tests_ran} tests across {rep.suite_count} suites + BYOF manifest + clean-room audit "
                f"in {rep.total_elapsed_seconds:.2f}s ===\n"
            )

    return 0 if rep.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
