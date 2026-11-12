"""Regular local files only. New private output directories, never in-place writes."""
from pathlib import Path
import atexit
import json
import os
import plistlib
import shutil
import stat
import subprocess
import time

WORKSPACE_ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
_RESOLVED = Path(__file__).resolve()
ROOT = WORKSPACE_ROOT if _RESOLVED.is_relative_to(WORKSPACE_ROOT) else _RESOLVED.parents[3]
VOLUME_UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'


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


def local_path(path):
    path = Path(os.path.abspath(path))
    require(path.is_relative_to(ROOT), 'path must be inside this Mac project workspace')
    for part in (ROOT, *reversed(path.relative_to(ROOT).parents)):
        p = part if part == ROOT else ROOT/part
        if p.exists():
            require(not p.is_symlink(), 'symlink parent rejected')
    require(not path.is_symlink(), 'symlink rejected')
    return path


def read_file(path, limit):
    p = local_path(path)
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
    if os.environ.get('FX3_FX6_FORCE_CLEAN_ROOM', '').strip().lower() in ('1', 'true', 'yes'):
        return True
    if ROOT != WORKSPACE_ROOT or not WORKSPACE_ROOT.is_dir():
        return True
    for p in required_paths:
        if not Path(p).exists():
            return True
    return False


def check_volume():
    require(ROOT == Path('/Volumes/KAFU2T/AI/Projects/Mac'), 'unexpected installed workspace root')
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
