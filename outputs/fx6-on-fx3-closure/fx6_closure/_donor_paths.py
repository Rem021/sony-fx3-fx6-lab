"""Dynamic BYOF donor & workspace path resolution across internal SSD, worktrees, and legacy KAFU2T."""

from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LEGACY_MAC_PROJECT_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")


def resolve_mac_project_root(repo_root: Path = REPO_ROOT) -> Path:
    env_override = os.environ.get("FX3_FX6_MAC_PROJECT_ROOT", "").strip()
    if env_override:
        return Path(env_override)
    for cand in (
        repo_root.parents[1],
        Path.home() / "AI-Workspace/AI/Projects/Mac",
        LEGACY_MAC_PROJECT_ROOT,
    ):
        if (cand / "work").is_dir():
            return cand
    return LEGACY_MAC_PROJECT_ROOT


def resolve_mac_work_dir(repo_root: Path = REPO_ROOT) -> Path:
    env_work = os.environ.get("FX3_FX6_MAC_WORK_DIR", "").strip()
    if env_work:
        return Path(env_work)
    return resolve_mac_project_root(repo_root) / "work"


def ensure_unicorn_importable() -> None:
    try:
        import unicorn  # noqa: F401
        return
    except ImportError:
        pass
    candidates = [
        *sorted(glob.glob(str(Path.home() / "Library/Python/*/lib/python/site-packages"))),
        *sorted(glob.glob(str(Path.home() / ".local/share/uv/**/site-packages"), recursive=True)),
        *sorted(glob.glob("/opt/homebrew/lib/python*/site-packages")),
        *sorted(glob.glob("/Library/Frameworks/Python.framework/Versions/*/lib/python*/site-packages")),
        "/Volumes/KAFU2T/AI/Orca/Worktrees/Phayen/dugong/work/firmware-reverse-2026-10-22/tools/venv/lib/python3.14/site-packages",
    ]
    for sp in candidates:
        p = Path(sp)
        if (p / "unicorn").is_dir() and sp not in sys.path:
            sys.path.append(sp)
            try:
                import unicorn  # noqa: F401
                return
            except ImportError:
                sys.path.remove(sp)
