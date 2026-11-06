#!/usr/bin/env python3
"""Pinned, task-local QEMU+Pixman preparation. No guest or source camera access."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import plistlib
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent / 'qemu-display-build'
OLD = Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host')


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def state(phase, **kwargs):
    p = ROOT / 'DISPLAY_BUILD_STATE.json'
    value = {'updated_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'phase': phase, 'owner': '/root/fx3_vm_host', 'preparation_pid': os.getpid(),
             'frozen_runtime_untouched': True, 'guest_started': False, **kwargs}
    tmp = p.with_suffix('.json.tmp'); tmp.write_text(json.dumps(value, indent=2) + '\n'); tmp.replace(p)


def main():
    assert plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    state('PREPARING_PINNED_SOURCES')
    archive = ROOT / 'downloads/qemu-11.1.2.tar.xz'
    assert archive.stat().st_size == 141815216
    assert sha(archive) == '731b5681e4bb18be313231579b8efd0296c5b015fa36dc533874b639ba838016'
    formula_path = ROOT / 'downloads/pixman-formula.json'
    formula = json.loads(formula_path.read_text())
    bottle = formula['bottle']['stable']['files']['arm64_golden_gate']
    assert formula['versions']['stable'] == '0.46.4' and formula['dependencies'] == []
    expected = '918ff532bf70bc121376f4b51420f44fc1abd0b9c519d7f8040f6ad9d304bc02'
    assert bottle['sha256'] == expected
    pixman_archive = ROOT / ('downloads/pixman-' + expected + '.tar.gz')
    if not pixman_archive.exists():
        token_url = 'https://ghcr.io/token?service=ghcr.io&scope=repository%3Ahomebrew%2Fcore%2Fpixman%3Apull'
        token = json.loads(subprocess.check_output(['curl', '--silent', '--show-error', '--fail', '--location', token_url]))['token']
        args = ['curl', '--silent', '--show-error', '--fail', '--location', '--max-time', '180',
                '--header', 'Authorization: Bearer ' + token,
                '--output', str(pixman_archive), bottle['url']]
        proc = subprocess.run(args, capture_output=True)
        if proc.returncode:
            raise RuntimeError('Public bottle fetch failed (header not logged), rc=' + str(proc.returncode))
        del token, args
    assert sha(pixman_archive) == expected
    pixman_prefix = ROOT / 'deps/pixman/0.46.4'
    if not pixman_prefix.exists():
        with tarfile.open(pixman_archive) as tf:
            tf.extractall(ROOT / 'deps', filter='data')
    changes = []
    for lib in sorted((pixman_prefix / 'lib').glob('*.dylib')):
        if lib.is_symlink():
            continue
        before = sha(lib)
        listing = subprocess.check_output(['otool', '-L', str(lib)], text=True)
        local_changes = []
        for line in listing.splitlines()[1:]:
            dependency = line.strip().split(' (')[0]
            if dependency.startswith(('/usr/lib/', '/System/Library/')):
                continue
            if Path(dependency).name == lib.name:
                subprocess.run(['install_name_tool', '-id', str(lib), str(lib)], check=True, capture_output=True)
                local_changes.append({'old': dependency, 'new': str(lib)})
            else:
                raise RuntimeError('Unexpected Pixman dylib dependency: ' + dependency)
        if local_changes:
            subprocess.run(['codesign', '--force', '--sign', '-', str(lib)], check=True, capture_output=True)
        changes.append({'path': str(lib), 'before': before, 'after': sha(lib), 'changes': local_changes})
    for pc in pixman_prefix.rglob('*.pc'):
        text = pc.read_text()
        for old in ['/opt/homebrew/opt/pixman', '/opt/homebrew/Cellar/pixman/0.46.4',
                    '@@HOMEBREW_PREFIX@@/opt/pixman', '@@HOMEBREW_CELLAR@@/pixman/0.46.4']:
            text = text.replace(old, str(pixman_prefix))
        assert '/opt/homebrew/' not in text and '@@HOMEBREW' not in text
        (ROOT / 'pkgconfig' / pc.name).write_text(text)
    source = ROOT / 'sources/qemu-11.1.2'
    if not source.exists():
        def safe_member(member, target):
            if member.issym() and member.linkname == '/opt/X11/include':
                return None
            return tarfile.data_filter(member, target)
        with tarfile.open(archive, 'r:xz') as tf:
            tf.extractall(ROOT / 'sources', filter=safe_member)
    patch = OLD / 'source-cleanup-support/qemu-original-to-fx3-complete.patch'
    assert sha(patch) == '23052b0e06f3adc6a3500d22aad8ea51688a49fa6d09f0693fb435954d1fbba7'
    if sha(source / 'hw/arm/virt.c') != 'c87dcfffc0934812284dba05fd525ab0f400b0021b3b90896371f455f6f3289d':
        subprocess.run(['patch', '-p1', '-i', str(patch)], cwd=source, check=True, capture_output=True)
    assert sha(source / 'hw/arm/virt.c') == 'c87dcfffc0934812284dba05fd525ab0f400b0021b3b90896371f455f6f3289d'
    record = {'qemu': {'url': 'https://download.qemu.org/qemu-11.1.2.tar.xz', 'sha256': sha(archive),
                       'bytes': archive.stat().st_size, 'version': '11.1.2'},
              'pixman': {'formula_url': 'https://formulae.brew.sh/api/formula/pixman.json',
                         'formula_sha256': sha(formula_path), 'version': '0.46.4', 'tag': 'arm64_golden_gate',
                         'bottle': bottle, 'archive_bytes': pixman_archive.stat().st_size,
                         'local_dylib_relocation': changes},
              'own_patch': {'path': str(patch), 'sha256': sha(patch)},
              'model_scope': 'Exactly original 4KiB SRAM mailbox and highDDR base with2GiB backing. No timer/CP models.',
              'source': str(source), 'global_install_or_settings': False}
    (ROOT / 'source-provenance.json').write_text(json.dumps(record, indent=2) + '\n')
    state('SOURCES_READY_CONFIGURE_NOT_STARTED', source=str(source), pixman_prefix=str(pixman_prefix))
    print('SOURCES_READY', source, 'PIXMAN', pixman_prefix, flush=True)


if __name__ == '__main__':
    main()
