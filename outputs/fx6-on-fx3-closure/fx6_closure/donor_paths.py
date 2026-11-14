"""Dynamic BYOF donor, main-lab work, and host toolchain path resolution.

Resolution precedence (unless `FX3_FX6_FORCE_CLEAN_ROOM` is enabled):
1. Explicit environment variable overrides:
   - `FX3_FX6_MAC_WORK_ROOT` (donor `work/` root)
   - `FX3_FX6_MAIN_LAB_WORK_ROOT` (main-lab `work/` root)
   - `FX3_FX6_MAC_ROOT` (derives `<MAC_ROOT>/outputs/sony-fx3-fx6-lab/work` and `<MAC_ROOT>/work`)
2. Current worktree's own `work/` directory (`<repo_root>/work`) when the probed target exists.
3. Internal SSD workspace derived from `Path.home() / "AI-Workspace/AI/Projects/Mac"`
   (`outputs/sony-fx3-fx6-lab/work` and `work`), avoiding hardcoded usernames.
4. Legacy external disk fallback (`/Volumes/KAFU2T/AI/Projects/Mac/...`).

When `FX3_FX6_FORCE_CLEAN_ROOM` is truthy (`1`, `true`, `yes`), clean-room isolation is strictly
enforced and external local Sony donor trees are never admitted.
"""

from __future__ import annotations

import os
import site
import sys
from pathlib import Path
from typing import List, Mapping, Optional, Tuple


ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"
ENV_UNICORN_SITE = "FX3_FX6_UNICORN_SITE"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

_COLOR_PORT_SENTINEL = (
    "FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
_FX3_VM_SENTINEL = "menu-repair-01/original-uipc/original-modules/upm.ko"
_ZIG_TOOLCHAIN_REL = (
    "fx3-vm-20261101/menu-repair-01/runtime/toolchains/"
    "zig-aarch64-macos-0.17.0/zig"
)


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    """Return True when `FX3_FX6_FORCE_CLEAN_ROOM` requests strict donorless CI mode."""
    source = os.environ if env is None else env
    return source.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def default_internal_mac_root(home: Optional[Path] = None) -> Path:
    """Return the internal SSD Mac workspace root derived from `Path.home()`."""
    base_home = Path.home() if home is None else Path(home)
    return base_home / "AI-Workspace" / "AI" / "Projects" / "Mac"


def _expand_path(raw: str) -> Path:
    return Path(os.path.expanduser(raw.strip()))


def _dedupe_paths(candidates: List[Path]) -> Tuple[Path, ...]:
    seen = set()
    ordered: List[Path] = []
    for cand in candidates:
        key = str(cand)
        if key not in seen:
            seen.add(key)
            ordered.append(cand)
    return tuple(ordered)


def iter_work_roots(
    *,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
    include_legacy: bool = True,
    prefer_main_lab: bool = False,
    bypass_clean_room: bool = False,
) -> Tuple[Path, ...]:
    """Return ordered candidate `work/` roots according to dynamic SSD/env precedence."""
    if not bypass_clean_room and is_forced_clean_room(env):
        return ()

    source = os.environ if env is None else env
    repo = DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    internal_mac = default_internal_mac_root(home=home)

    candidates: List[Path] = []

    # 1. Explicit environment variable overrides
    env_mac_work = source.get(ENV_MAC_WORK_ROOT, "").strip()
    env_main_lab_work = source.get(ENV_MAIN_LAB_WORK_ROOT, "").strip()
    env_mac_root = source.get(ENV_MAC_ROOT, "").strip()

    if prefer_main_lab:
        if env_main_lab_work:
            candidates.append(_expand_path(env_main_lab_work))
        if env_mac_work:
            candidates.append(_expand_path(env_mac_work))
        if env_mac_root:
            mac_base = _expand_path(env_mac_root)
            candidates.append(mac_base / "outputs" / "sony-fx3-fx6-lab" / "work")
            candidates.append(mac_base / "work")
    else:
        if env_mac_work:
            candidates.append(_expand_path(env_mac_work))
        if env_main_lab_work:
            candidates.append(_expand_path(env_main_lab_work))
        if env_mac_root:
            mac_base = _expand_path(env_mac_root)
            candidates.append(mac_base / "work")
            candidates.append(mac_base / "outputs" / "sony-fx3-fx6-lab" / "work")

    # 2. Current worktree's own `work/`
    candidates.append(repo / "work")

    # 3. Internal SSD main lab & Mac work roots (via Path.home())
    candidates.append(internal_mac / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(internal_mac / "work")

    # 4. Legacy external volume fallback
    if include_legacy:
        candidates.append(LEGACY_MAC_ROOT / "outputs" / "sony-fx3-fx6-lab" / "work")
        candidates.append(LEGACY_MAC_ROOT / "work")

    return _dedupe_paths(candidates)


def resolve_work_subpath(
    rel_subpath: str,
    *,
    sentinel_relpath: Optional[str] = None,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
    require_file: bool = False,
    prefer_main_lab: bool = False,
    include_legacy: bool = True,
) -> Path:
    """Resolve a relative path under `work/` by probing for `sentinel_relpath` (or the target itself).

    In clean-room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`) or when no candidate contains the probed
    target, returns a deterministic non-existent sentinel path so callers never mistake an
    incomplete git-tracked `work/` directory for a live donor tree.
    """
    repo = DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    rel_norm = rel_subpath.strip("/")
    clean_fallback = repo / CLEAN_ROOM_SENTINEL_DIRNAME / rel_norm

    if is_forced_clean_room(env):
        return clean_fallback

    probe_rel = (
        f"{rel_norm}/{sentinel_relpath.strip('/')}" if sentinel_relpath else rel_norm
    )

    roots = iter_work_roots(
        repo_root=repo,
        env=env,
        home=home,
        include_legacy=include_legacy,
        prefer_main_lab=prefer_main_lab,
        bypass_clean_room=False,
    )
    for root in roots:
        probe = root / probe_rel
        hit = probe.is_file() if require_file else probe.exists()
        if hit:
            return root / rel_norm

    return clean_fallback


def resolve_toolchain_subpath(
    rel_subpath: str,
    *,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
    require_file: bool = True,
    include_legacy: bool = True,
) -> Path:
    """Resolve a host build toolchain path (not a Sony donor; available in clean-room mode)."""
    repo = DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    rel_norm = rel_subpath.strip("/")
    roots = iter_work_roots(
        repo_root=repo,
        env=env,
        home=home,
        include_legacy=include_legacy,
        prefer_main_lab=False,
        bypass_clean_room=True,
    )
    for root in roots:
        probe = root / rel_norm
        if probe.is_file() if require_file else probe.exists():
            return probe
    return default_internal_mac_root(home=home) / "work" / rel_norm


def resolve_color_port_work_dir(
    *,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
) -> Path:
    return resolve_work_subpath(
        "fx3-color-port-20261027",
        sentinel_relpath=_COLOR_PORT_SENTINEL,
        repo_root=repo_root,
        env=env,
        home=home,
        require_file=True,
    )


def resolve_fx6_team_dir(
    *,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
) -> Path:
    return (
        resolve_color_port_work_dir(repo_root=repo_root, env=env, home=home)
        / "FX6-donor-assessment-20261103"
        / "team"
    )


def resolve_fx6_donor_root(
    *,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
) -> Path:
    return resolve_fx6_team_dir(repo_root=repo_root, env=env, home=home) / "donor"


def resolve_fx6_donor_lib_dir(
    *,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
) -> Path:
    return resolve_work_subpath(
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib",
        sentinel_relpath="appFw.so",
        repo_root=repo_root,
        env=env,
        home=home,
        require_file=True,
    )


def resolve_fx3_vm_work_root(
    *,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
) -> Path:
    return resolve_work_subpath(
        "fx3-vm-20261101",
        sentinel_relpath=_FX3_VM_SENTINEL,
        repo_root=repo_root,
        env=env,
        home=home,
        require_file=True,
    )


def resolve_fx3_modules_dir(
    *,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
) -> Path:
    return resolve_work_subpath(
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-modules",
        sentinel_relpath="upm.ko",
        repo_root=repo_root,
        env=env,
        home=home,
        require_file=True,
    )


def resolve_fx3_seed_bk4_path(
    *,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
) -> Path:
    return resolve_work_subpath(
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        repo_root=repo_root,
        env=env,
        home=home,
        require_file=True,
    )


def resolve_lab_work_file(
    rel_subpath: str,
    *,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
) -> Path:
    return resolve_work_subpath(
        rel_subpath,
        repo_root=repo_root,
        env=env,
        home=home,
        require_file=True,
        prefer_main_lab=True,
    )


def rebase_legacy_work_path(
    raw_path: str,
    *,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
) -> Path:
    """Rebase a recorded `/Volumes/KAFU2T/.../work/...` path inside historical JSONs to a live file."""
    repo = DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    candidate = Path(raw_path)
    if is_forced_clean_room(env):
        return repo / CLEAN_ROOM_SENTINEL_DIRNAME / candidate.name
    if candidate.is_file():
        return candidate
    marker = "/work/"
    if marker in raw_path:
        rel_after_work = raw_path.split(marker, 1)[1].lstrip("/")
        if rel_after_work:
            return resolve_work_subpath(
                rel_after_work,
                repo_root=repo,
                env=env,
                home=home,
                require_file=True,
            )
    return candidate


def resolve_zig_binary_default(
    *,
    repo_root: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
) -> Path:
    return resolve_toolchain_subpath(
        _ZIG_TOOLCHAIN_REL,
        repo_root=repo_root,
        env=env,
        home=home,
        require_file=True,
    )


def resolve_unicorn_site_packages(
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Path]:
    """Locate an optional site-packages directory containing `unicorn` without dead external paths."""
    source = os.environ if env is None else env
    candidates: List[Path] = []

    for env_key in (ENV_UNICORN_SITE, "UNICORN_SITE_PACKAGES"):
        raw = source.get(env_key, "").strip()
        if raw:
            candidates.append(_expand_path(raw))

    try:
        user_site = site.getusersitepackages()
        if user_site:
            candidates.append(Path(user_site))
    except Exception:
        pass

    try:
        for sp in site.getsitepackages():
            candidates.append(Path(sp))
    except Exception:
        pass

    py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidates.append(Path(sys.prefix) / "lib" / py_ver / "site-packages")

    for cand in _dedupe_paths(candidates):
        if cand.is_dir() and (
            (cand / "unicorn" / "__init__.py").is_file() or (cand / "unicorn").is_dir()
        ):
            return cand
    return None


def ensure_unicorn_site_on_sys_path(
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Path]:
    """Append a discovered Unicorn site-packages directory to `sys.path` if needed."""
    found = resolve_unicorn_site_packages(env=env)
    if found is not None:
        found_str = str(found)
        if found_str not in sys.path:
            sys.path.append(found_str)
    return found
