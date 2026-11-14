"""Regular local files only. New private output directories, never in-place writes."""
from pathlib import Path
import atexit
import json
import os
import plistlib
import shutil
import site
import stat
import subprocess
import sys
import time

ENV_FORCE_CLEAN_ROOM = 'FX3_FX6_FORCE_CLEAN_ROOM'
ENV_MAC_ROOT = 'FX3_FX6_MAC_ROOT'
ENV_MAC_WORK_ROOT = 'FX3_FX6_MAC_WORK_ROOT'
ENV_MAIN_LAB_WORK_ROOT = 'FX3_FX6_MAIN_LAB_WORK_ROOT'
ENV_UNICORN_SITE = 'FX3_FX6_UNICORN_SITE'

_INTERNAL_WORKSPACE = Path.home() / 'AI-Workspace/AI/Projects/Mac'
_LEGACY_WORKSPACE = Path('/Volumes/KAFU2T/AI/Projects/Mac')
WORKSPACE_ROOT = _INTERNAL_WORKSPACE if _INTERNAL_WORKSPACE.is_dir() else _LEGACY_WORKSPACE
_RESOLVED = Path(__file__).resolve()
ROOT = _RESOLVED.parents[3]
CLEAN_ROOM_SENTINEL_DIRNAME = '__fx3_fx6_clean_room_donor_disabled__'
VOLUME_UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'


def is_forced_clean_room(env=None):
    source = os.environ if env is None else env
    return source.get(ENV_FORCE_CLEAN_ROOM, '').strip().lower() in ('1', 'true', 'yes')


def iter_donor_work_roots(env=None):
    if is_forced_clean_room(env):
        return ()
    source = os.environ if env is None else env
    candidates = []
    for key in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        raw = source.get(key, '').strip()
        if raw:
            candidates.append(Path(os.path.expanduser(raw)))
    raw_mac = source.get(ENV_MAC_ROOT, '').strip()
    if raw_mac:
        mac_base = Path(os.path.expanduser(raw_mac))
        candidates.append(mac_base / 'work')
        candidates.append(mac_base / 'outputs' / 'sony-fx3-fx6-lab' / 'work')
    candidates.append(ROOT / 'work')
    candidates.append(_INTERNAL_WORKSPACE / 'outputs' / 'sony-fx3-fx6-lab' / 'work')
    candidates.append(_INTERNAL_WORKSPACE / 'work')
    candidates.append(_LEGACY_WORKSPACE / 'outputs' / 'sony-fx3-fx6-lab' / 'work')
    candidates.append(_LEGACY_WORKSPACE / 'work')
    seen = set()
    ordered = []
    for cand in candidates:
        key = str(cand)
        if key not in seen:
            seen.add(key)
            ordered.append(cand)
    return tuple(ordered)


def resolve_donor_path(rel_subpath, *, sentinel_relpath=None, require_file=False, env=None):
    rel_norm = rel_subpath.strip('/')
    if rel_norm.startswith('work/'):
        rel_norm = rel_norm[len('work/'):]
    fallback = ROOT / CLEAN_ROOM_SENTINEL_DIRNAME / rel_norm
    if is_forced_clean_room(env):
        return fallback
    probe_rel = f"{rel_norm}/{sentinel_relpath.strip('/')}" if sentinel_relpath else rel_norm
    for work_root in iter_donor_work_roots(env=env):
        probe = work_root / probe_rel
        if probe.is_file() if require_file else probe.exists():
            return work_root / rel_norm
    return fallback


def resolve_unicorn_site_packages(env=None):
    source = os.environ if env is None else env
    candidates = []
    for key in (ENV_UNICORN_SITE, 'UNICORN_SITE_PACKAGES'):
        raw = source.get(key, '').strip()
        if raw:
            candidates.append(Path(os.path.expanduser(raw)))
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
    py_ver = f'python{sys.version_info.major}.{sys.version_info.minor}'
    candidates.append(Path(sys.prefix) / 'lib' / py_ver / 'site-packages')
    for cand in candidates:
        if cand.is_dir() and ((cand / 'unicorn' / '__init__.py').is_file() or (cand / 'unicorn').is_dir()):
            return cand
    return None


def allocate_test_run_dir(stage_runs_relpath, prefix, module_name, argv):
    """Return explicit CLI run path for __main__, or an isolated auto-cleaned run path under ROOT."""
    if module_name == '__main__' and len(argv) > 1:
        run_dir = Path(argv[1])
        argv[:] = argv[:1]
        return run_dir
    parent = ROOT / stage_runs_relpath
    run_dir = parent / f'{prefix}-{os.getpid()}-{time.time_ns()}'
    atexit.register(lambda p=run_dir: shutil.rmtree(p, ignore_errors=True))
    return run_dir


def require(ok, message):
    if not ok:
        raise ValueError(message)


def local_path(path, allow_donor_roots=False):
    path = Path(os.path.abspath(path))
    allowed_roots = [ROOT]
    if allow_donor_roots and not is_forced_clean_room():
        allowed_roots.extend(r for r in iter_donor_work_roots() if r.is_dir())
    base = next((r for r in allowed_roots if path.is_relative_to(r)), None)
    require(base is not None, 'path must be inside this Mac project workspace')
    for part in (base, *reversed(path.relative_to(base).parents)):
        p = part if part == base else base/part
        if p.exists():
            require(not p.is_symlink(), 'symlink parent rejected')
    require(not path.is_symlink(), 'symlink rejected')
    return path


def read_file(path, limit):
    p = local_path(path, allow_donor_roots=True)
    require(hasattr(os, 'O_NOFOLLOW'), 'this build requires POSIX O_NOFOLLOW')
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'single-link regular file required; no device/FIFO input')
        require(0 <= before.st_size <= limit, 'input size limit exceeded')
        with os.fdopen(os.dup(fd), 'rb') as f:
            data = f.read(before.st_size+1)
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode', 'st_nlink')
        require(len(data) == before.st_size and all(getattr(before, n) == getattr(after, n) for n in fields), 'input changed during read')
        return data
    finally:
        os.close(fd)


def is_clean_room_or_donor_unavailable(required_paths=()):
    if is_forced_clean_room():
        return True
    if not ROOT.is_dir():
        return True
    for p in required_paths:
        if not Path(p).exists():
            return True
    return False


def check_volume():
    require(ROOT.is_dir(), 'unexpected installed workspace root')
    if str(ROOT).startswith('/Volumes/KAFU2T'):
        data = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
        require(data.get('VolumeUUID') == VOLUME_UUID, 'target external volume missing or identity differs')


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()


def new_directory(path, contents):
    """Write into an exclusive directory. A failed write leaves evidence, never deletes it."""
    check_volume()
    p = local_path(path)
    require(p.parent.is_dir(), 'output parent must already exist')
    require(all('/' not in n and n not in ('', '.', '..') for n in contents), 'flat output names required')
    parent = os.open(p.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.mkdir(p.name, 0o700, dir_fd=parent)
        directory = os.open(p.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            for name, data in contents.items():
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
                with os.fdopen(fd, 'wb') as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
            os.fsync(directory)
        finally:
            os.close(directory)
        os.fsync(parent)
    finally:
        os.close(parent)
