#!/usr/bin/env python3
"""Compile an AArch64 observer object and run isolated host forwarding checks.

Does not link a guest shared library, change any CPIO or start a VM.
Generated binaries stay in the repository's ignored work/ directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess

from elftools.elf.elffile import ELFFile


def fp(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--compiler', default='/usr/bin/clang')
    ap.add_argument('--build-dir', type=Path)
    args = ap.parse_args()
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    if volume.get('VolumeUUID') != 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':
        raise RuntimeError('wrong external volume')
    here = Path(__file__).resolve().parent
    repo = here.parents[2]
    work = (args.build_dir or repo/'work/parallel-research-20261107/queue-observer-build').resolve()
    if not work.is_relative_to(repo/'work'):
        raise ValueError('build directory must stay inside ignored repository work/')
    work.mkdir(parents=True, exist_ok=True)
    source = here/'observe_osal_queue.c'
    fixture = here/'test_observe_osal_queue.c'
    obj, host = work/'observe_osal_queue.o', work/'host-fixture'
    compile_object = [args.compiler, '-target', 'aarch64-linux-gnu', '-std=c11', '-O2',
        '-fPIC', '-ffreestanding', '-Wall', '-Wextra', '-Werror', '-c', str(source), '-o', str(obj)]
    compile_host = [args.compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
        '-DFX6_QUEUE_OBSERVER_TEST', str(source), str(fixture), '-o', str(host)]
    for command in (compile_object, compile_host):
        subprocess.run(command, check=True)
    cases = []
    for parameters, expected in [([], 0), (['missing'], 126), (['self'], 126)]:
        result = subprocess.run([str(host), *parameters], capture_output=True, text=True)
        if result.returncode != expected:
            raise RuntimeError(f'host fixture failed: {parameters}: {result.returncode}')
        cases.append({'args': parameters, 'expected_exit': expected, 'actual_exit': result.returncode,
                      'stdout': result.stdout.strip()})
    with obj.open('rb') as f:
        e = ELFFile(f)
        if e['e_machine'] != 'EM_AARCH64' or e['e_type'] != 'ET_REL':
            raise ValueError('wrong object architecture/type')
        symbols = list(e.get_section_by_name('.symtab').iter_symbols())
        undefined = sorted({s.name for s in symbols if s['st_shndx'] == 'SHN_UNDEF' and s.name})
        exported = sorted({s.name for s in symbols if s['st_shndx'] != 'SHN_UNDEF' and s['st_info']['bind'] == 'STB_GLOBAL'})
        expected = {'__errno_location', '_exit', 'clock_gettime', 'dladdr', 'dlerror', 'dlsym', 'dprintf', 'syscall'}
        if set(undefined) != expected or exported != ['osal_rcv_msg_tmo']:
            raise ValueError('unexpected imports/exports or compiler runtime dependency')
    result = {'schema': 'fx6-osal-queue-observer-offline-build-v1',
        'compiler_version': subprocess.check_output([args.compiler, '--version'], text=True).strip(),
        'sources': [fp(source), fp(fixture)], 'object': fp(obj),
        'commands': [compile_object, compile_host], 'host_fixture_cases': cases,
        'object_elf_machine': 'EM_AARCH64', 'object_elf_type': 'ET_REL',
        'undefined_symbols': undefined, 'exported_symbols': exported,
        'guest_shared_library_linked': False, 'cpio_changed': False, 'guest_executed': False,
        'limits': 'Host fakes check forwarding/errno and failure gates; they do not prove guest linker resolution, timing impact or original Sony ABI execution.'}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
