#!/usr/bin/env python3
"""One-shot offline CPIO derivation: r3 guest + read-only /proc diagnostic only."""
from __future__ import annotations

import difflib
import hashlib
import json
import plistlib
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
R3 = HERE.parent / 'v25-menu-osd-diagnostic-r3' / 'vmopt-20261104-v25-menu-osd-diagnostic-r3'
OUT = HERE / 'vmopt-20261104-v25-procdiag-r4e'
BASE_MANIFEST_SHA = 'a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518'
BASE_CPIO_SHA = '31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83'
BASE_INIT_SHA = '8ad0be3aec240977060e25ba1193ad80f6ef596ffe47392e3d5b5b79c0ee4a05'
VOLUME_UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
MARKER = b' echo FX3_BACKUP_CP_LIVE_OBSERVER_PID=$!\n'
INSERT = (b' echo FX3_BACKUP_CP_LIVE_OBSERVER_PID=$!\n'
          b' echo "$!" > /tmp/fx3-proc97-observer.identity\n'
          b' /simulation/fx3-procdiag-v1 &\n'
          b' echo FX3_PROCDIAG_V1_PID=$!\n')
NEW_MEMBER = 'simulation/fx3-procdiag-v1'


def sha(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def align4(n):
    return (n + 3) & ~3


def copy_bytes(src, dst, amount, digest=None):
    while amount:
        part = src.read(min(amount, 1 << 20))
        if not part:
            raise ValueError('truncated CPIO')
        if digest is not None:
            digest.update(part)
        dst.write(part)
        amount -= len(part)


def newc_member(name: str, payload: bytes, *, mode: int = 0o100755):
    name_bytes = name.encode() + b'\0'
    fields = [0x525234, mode, 0, 0, 1, 0, len(payload), 0, 0, 0, 0, len(name_bytes), 0]
    head = b'070701' + b''.join(f'{value:08x}'.encode() for value in fields)
    assert len(head) == 110
    return (head + name_bytes + b'\0' * (align4(110 + len(name_bytes)) - 110 - len(name_bytes))
            + payload + b'\0' * (align4(len(payload)) - len(payload)))


def derive(src_path: Path, dst_path: Path, init_new: bytes, helper: bytes):
    seen = set()
    with src_path.open('rb') as src, dst_path.open('xb') as dst:
        while True:
            head = src.read(110)
            if len(head) != 110 or head[:6] not in (b'070701', b'070702'):
                raise ValueError('invalid original CPIO header')
            fields = [int(head[6 + i * 8:14 + i * 8], 16) for i in range(13)]
            size, name_size = fields[6], fields[11]
            if not 1 <= name_size <= 4096:
                raise ValueError('invalid CPIO member name size')
            name_raw = src.read(name_size)
            if len(name_raw) != name_size or not name_raw.endswith(b'\0'):
                raise ValueError('invalid CPIO member name')
            name = name_raw[:-1].decode()
            pad = src.read(align4(110 + name_size) - 110 - name_size)
            if name in seen:
                raise ValueError('duplicate original CPIO member: ' + name)
            seen.add(name)
            if name == NEW_MEMBER:
                raise ValueError('diagnostic member already present')
            if name == 'init':
                old = src.read(size)
                if len(old) != size or hashlib.sha256(old).hexdigest() != BASE_INIT_SHA:
                    raise ValueError('original /init identity mismatch')
                src.read(align4(size) - size)
                changed = head[:54] + f'{len(init_new):08x}'.encode() + head[62:]
                dst.write(changed + name_raw + pad + init_new)
                dst.write(b'\0' * (align4(len(init_new)) - len(init_new)))
            elif name == 'TRAILER!!!':
                if size != 0 or 'init' not in seen:
                    raise ValueError('invalid trailer or missing /init')
                dst.write(newc_member(NEW_MEMBER, helper))
                dst.write(head + name_raw + pad)
                copy_bytes(src, dst, src_path.stat().st_size - src.tell())
                break
            else:
                dst.write(head + name_raw + pad)
                copy_bytes(src, dst, align4(size))


def extract_init(src_path: Path):
    with src_path.open('rb') as src:
        while True:
            head = src.read(110)
            if len(head) != 110 or head[:6] not in (b'070701', b'070702'):
                raise ValueError('invalid CPIO header')
            fields = [int(head[6 + i * 8:14 + i * 8], 16) for i in range(13)]
            name_size, size = fields[11], fields[6]
            name_raw = src.read(name_size)
            name = name_raw[:-1].decode()
            src.seek(align4(110 + name_size) - 110 - name_size, 1)
            if name == 'init':
                data = src.read(size)
                if hashlib.sha256(data).hexdigest() != BASE_INIT_SHA:
                    raise ValueError('original /init SHA mismatch')
                return data
            src.seek(align4(size), 1)
            if name == 'TRAILER!!!':
                raise ValueError('missing init')


def main():
    vol = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    if vol.get('VolumeUUID') != VOLUME_UUID:
        raise RuntimeError('volume UUID mismatch')
    if OUT.exists():
        raise FileExistsError(OUT)
    manifest = R3 / 'candidate.json'
    if sha(manifest) != BASE_MANIFEST_SHA:
        raise ValueError('frozen r3 candidate changed')
    base = json.loads(manifest.read_text())
    source = Path(base['initrd']['path'])
    if source != R3 / 'guest.cpio' or sha(source) != BASE_CPIO_SHA:
        raise ValueError('frozen r3 CPIO changed')
    helper_path = HERE / 'fx3-procdiag-v1-r4e'
    if not helper_path.is_file():
        raise ValueError('diagnostic binary missing')
    helper = helper_path.read_bytes()
    if not helper.startswith(b'\x7fELF'):
        raise ValueError('diagnostic binary not ELF')
    old_init = extract_init(source)
    if old_init.count(MARKER) != 1:
        raise ValueError('ambiguous proc97 launch anchor')
    new_init = old_init.replace(MARKER, INSERT)
    OUT.mkdir()
    cpio = OUT / 'guest.cpio'
    derive(source, cpio, new_init, helper)
    diff = ''.join(difflib.unified_diff(old_init.decode().splitlines(True),
                                        new_init.decode().splitlines(True),
                                        fromfile='r3:/init', tofile='r4:/init'))
    (OUT / 'init-procdiag.diff').write_text(diff)
    derived = dict(base)
    derived['initrd'] = {'path': str(cpio), 'sha256': sha(cpio)}
    derived['procdiag_review_contract'] = {
        'base_candidate': str(manifest), 'base_candidate_sha256': BASE_MANIFEST_SHA,
        'base_init_sha256': BASE_INIT_SHA, 'new_init_sha256': hashlib.sha256(new_init).hexdigest(),
        'new_member': NEW_MEMBER, 'new_member_sha256': sha(helper_path),
        'changed_members': ['init', NEW_MEMBER], 'dtb_unchanged': True,
        'kernel_unchanged': True, 'Backup_unchanged': True,
        'runtime_validated': False, 'guest_loaded': False,
        'software_only_reserved_range': 'KEY93+0x9000..0x10000; date98 +0x1000..0x7000 and date99 +0x8000..0x9000 untouched',
    }
    (OUT / 'candidate.json').write_text(json.dumps(derived, indent=2) + '\n')
    receipt = {'source_cpio_sha256': BASE_CPIO_SHA, 'derived_cpio_sha256': sha(cpio),
               'source_init_sha256': BASE_INIT_SHA,
               'derived_init_sha256': hashlib.sha256(new_init).hexdigest(),
               'binary_sha256': sha(helper_path), 'candidate_sha256': sha(OUT / 'candidate.json'),
               'init_diff_sha256': sha(OUT / 'init-procdiag.diff'),
               'dtb_sha256': base['dtb']['sha256'], 'QEMU_started': False,
               'changed_members': ['init', NEW_MEMBER]}
    (OUT / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
