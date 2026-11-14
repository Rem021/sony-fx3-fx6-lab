#!/usr/bin/env python3
"""
Real-time GitHub Sync Daemon for `sony-fx3-fx6-lab` (`FX3｜FX5 & FX6 系统研究`).
1. Exports and categorizes all FX3 / FX5 / FX6 conversations from Orca (`export_orca_conversations.mjs`).
2. Syncs any new or updated FX3 / FX5 / FX6 / VENICE reports from `/Volumes/KAFU2T/AI/Projects/Mac/reports/`.
3. Enforces clean-room rules (excludes proprietary firmware binaries and files > 25 MB).
4. Commits and pushes any changes in `/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab` to `origin/main`.
"""
import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAC_REPORTS = REPO_ROOT.parents[1] / "reports"
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_orca_conversations.mjs"

REPORT_PAT = re.compile(r"(fx3|fx5|fx6|venice|sony-fx|索尼\s*FX)", re.IGNORECASE)
FORBIDDEN_EXTS = {
    ".dat",
    ".bin",
    ".img",
    ".cpio",
    ".squashfs",
    ".iso",
    ".dmg",
    ".pkg",
    ".so",
    ".elf",
    ".ko",
    ".dylib",
    ".a",
    ".o",
}
MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB safety limit


def sync_reports():
    if not MAC_REPORTS.exists():
        return
    dst_reports = REPO_ROOT / "reports"
    dst_reports.mkdir(parents=True, exist_ok=True)
    for item in MAC_REPORTS.iterdir():
        if not REPORT_PAT.search(item.name):
            continue
        target = dst_reports / item.name
        if item.is_file():
            if item.suffix.lower() in FORBIDDEN_EXTS or item.stat().st_size > MAX_FILE_BYTES:
                continue
            if not target.exists() or item.stat().st_mtime > target.stat().st_mtime:
                shutil.copy2(item, target)
        elif item.is_dir():
            subprocess.run(
                [
                    "rsync",
                    "-a",
                    "--exclude=*.bin",
                    "--exclude=*.dat",
                    "--exclude=*.img",
                    "--exclude=*.cpio",
                    "--exclude=*.squashfs",
                    "--exclude=*.so",
                    "--exclude=*.so.*",
                    "--exclude=*.elf",
                    "--exclude=*.ko",
                    "--max-size=25m",
                    f"{item}/",
                    f"{target}/",
                ],
                check=False,
            )


def run_git(args):
    return subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-conversations", action="store_true")
    args = parser.parse_args()

    if not args.skip_conversations and EXPORT_SCRIPT.exists():
        subprocess.run(["node", str(EXPORT_SCRIPT)], cwd=str(REPO_ROOT), check=False)

    sync_reports()

    status = run_git(["status", "--porcelain"])
    if not status.stdout.strip():
        print("No changes to sync.")
        return 0

    run_git(["add", "-A"])

    # Unstage any accidentally staged file > 25MB or proprietary binary extension
    staged = run_git(["diff", "--cached", "--name-only"]).stdout.splitlines()
    for rel in staged:
        p = REPO_ROOT / rel
        if p.exists() and p.is_file():
            if p.suffix.lower() in FORBIDDEN_EXTS or p.stat().st_size > MAX_FILE_BYTES:
                run_git(["reset", "HEAD", "--", rel])

    staged_after = run_git(["diff", "--cached", "--name-only"]).stdout.splitlines()
    if not staged_after:
        print("No eligible clean-room files to commit.")
        return 0

    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    msg = f"sync(realtime): auto-sync FX3/FX5/FX6 research & Orca conversations ({len(staged_after)} files @ {now_utc})"
    commit_res = run_git(["commit", "-m", msg])
    print(commit_res.stdout.strip())

    push_res = run_git(["push", "origin", "main"])
    if push_res.returncode != 0:
        print(push_res.stderr.strip(), file=sys.stderr)
        return push_res.returncode

    print(f"Successfully pushed {len(staged_after)} files to origin/main.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
