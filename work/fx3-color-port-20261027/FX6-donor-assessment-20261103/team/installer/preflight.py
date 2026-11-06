#!/usr/bin/env python3
"""FX3 7.02 local-original audit. Reads regular local files only; emits JSON to stdout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
EXPECTED = {
    'ap': '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
    'cp': 'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
    'fstab': '3936e6508ba89a025fc998c824434562c2d16234db96e179ec3f3a90a5a1d6f0',
    'bootin': 'dab3ce4b6c28a6c9ffd9f0b893dce1d08f3ee7302a09df87e518409e728be2f2',
    'im': '5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91',
}
UNKNOWN = [
    'FX3 live AP/CP regular-file bytes, inode and mount identity were not read',
    'FX3-specific patch windows and final hashes do not exist',
    'FX3 writable remount, fsync and read-only restoration are untested',
    'Power-loss behavior, rollback after partial writes, and independent recovery are untested',
    'Cold boot loaded AP/CP identity and modified-code execution are untested',
    'FX3 WBI image_mode/image_dev and drop sequence are unverified',
    'FX3 Jiritsu temporary native loader and file transport are not runtime-proven',
]

def read_local(path, need_data=False):
    supplied = Path(path).absolute()
    real_root = ROOT.resolve(strict=True)
    # Resolve before containment: Path.absolute()/is_relative_to() alone are lexical.
    p = supplied.resolve(strict=False)
    if not p.is_relative_to(real_root):
        raise ValueError('path outside project')
    if '..' in supplied.parts:
        raise ValueError('parent traversal is not accepted')
    # Refuse symlinks at every input component, including the final component.
    try:
        relative = supplied.relative_to(ROOT)
    except ValueError as e:
        raise ValueError('path outside project') from e
    walk = ROOT
    for part in relative.parts:
        walk /= part
        if walk.is_symlink():
            raise ValueError('symlink path is not accepted')
    fd = os.open(p, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    try:
        s = os.fstat(fd)
        if not stat.S_ISREG(s.st_mode):
            raise ValueError('not a regular file')
        h = hashlib.sha256()
        data = bytearray() if need_data else None
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk: break
            h.update(chunk)
            if need_data: data.extend(chunk)
        return {'path': str(p), 'bytes': s.st_size, 'sha256': h.hexdigest()}, bytes(data) if need_data else None
    finally:
        os.close(fd)

def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--model', required=True, help='claimed source model; not live-device proof')
    for name in EXPECTED: a.add_argument('--' + name, required=True)
    v = vars(a.parse_args())
    checks = []
    def check(name, ok, detail): checks.append({'check': name, 'ok': bool(ok), 'detail': detail})
    check('claimed_model', v['model'] == 'ILME-FX3', v['model'])
    seen = {}
    for name, digest in EXPECTED.items():
        try:
            info, data = read_local(v[name], name == 'fstab')
            seen[name] = info
            check(name + '_sha256', info['sha256'] == digest, info)
            if name == 'fstab':
                rows = [line.split() for line in data.decode('ascii').splitlines() if line and not line.startswith('#')]
                rows = [r for r in rows if len(r) >= 4]
                check('fx3_mount_rows',
                      ['/dev/nflasha15', '/usr', 'ext2', 'ro'] in [[*r[:3], r[3].split(',')[0]] for r in rows]
                      and ['/dev/nflasha8', '/cp', 'vfat', 'rw'] in [[*r[:3], r[3].split(',')[0]] for r in rows],
                      {'usr': next((r for r in rows if r[1] == '/usr'), None),
                       'cp': next((r for r in rows if r[1] == '/cp'), None)})
        except (OSError, ValueError, UnicodeError) as e:
            check(name + '_local_read', False, type(e).__name__ + ': ' + str(e))
    result = {'schema': 'fx3-installer-local-audit-v1', 'method': 'local regular files, read-only',
              'status': 'fail' if any(not c['ok'] for c in checks) else 'local_original_preflight_only',
              'checks': checks, 'unknown': UNKNOWN, 'installation_ready': False,
              'patch_windows': [], 'source_original_sha256': EXPECTED}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result['status'] == 'fail' else 0

if __name__ == '__main__': sys.exit(main())
