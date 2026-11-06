#!/usr/bin/env python3
"""Native ARM64 QEMU derived build: original model patches plus Pixman only."""
from pathlib import Path
import datetime
import json
import os
import signal
import subprocess
import time
from prepare_qemu_display import ROOT, OLD, sha, state


def main():
    source = ROOT / 'sources/qemu-11.1.2'
    assert sha(source / 'hw/arm/virt.c') == 'c87dcfffc0934812284dba05fd525ab0f400b0021b3b90896371f455f6f3289d'
    env = os.environ.copy()
    env['PATH'] = str(OLD / 'build-venv/bin') + ':' + env['PATH']
    env['PKG_CONFIG'] = str(OLD / 'deps/pkgconf/3.0.10/bin/pkgconf')
    env['PKG_CONFIG_PATH'] = str(ROOT / 'pkgconfig') + ':' + str(OLD / 'pkgconfig')
    env['CC'] = '/usr/bin/clang'
    env['CXX'] = '/usr/bin/clang++'
    args = [str(source / 'configure'), '--target-list=aarch64-softmmu',
            '--without-default-features', '--enable-tcg', '--enable-fdt', '--enable-pixman',
            '--disable-docs', '--disable-tools', '--disable-guest-agent', '--disable-werror',
            '--python=' + str(OLD / 'build-venv/bin/python')]
    record = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'configure': args, 'env': {n: env[n] for n in ['CC', 'CXX', 'PATH', 'PKG_CONFIG', 'PKG_CONFIG_PATH']},
              'features': 'Pixman only added; no timer/DMA/CP peripheral model changes'}
    (ROOT / 'configure-command.json').write_text(json.dumps(record, indent=2) + '\n')

    def terminated(signum, frame):
        raise KeyboardInterrupt('Build observer signal ' + str(signum))

    signal.signal(signal.SIGTERM, terminated)

    def execute(command, filename, phase):
        start = time.monotonic()
        p = None
        with (ROOT / 'logs' / filename).open('wb') as log:
            try:
                p = subprocess.Popen(command, cwd=ROOT / 'build', env=env, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
                state(phase, child_pid=p.pid, args=command,
                      child_lstart=subprocess.check_output(['ps', '-o', 'lstart=', '-p', str(p.pid)], text=True).strip())
                rc = p.wait()
            finally:
                if p is not None and p.poll() is None:
                    os.killpg(p.pid, signal.SIGTERM)
                    try:
                        p.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid, signal.SIGKILL); p.wait(timeout=5)
        return {'exit': rc, 'seconds': time.monotonic() - start, 'log': str(ROOT / 'logs' / filename)}

    configuration = execute(args, 'configure.log', 'CONFIGURING_PIXMAN_NATIVE')
    (ROOT / 'configure-result.json').write_text(json.dumps(configuration, indent=2) + '\n')
    if configuration['exit']:
        state('CONFIGURE_FAILED', result=configuration)
        print('CONFIGURE_FAILED', configuration, flush=True)
        return 2
    config = (ROOT / 'build/config-host.h').read_text()
    assert '#define CONFIG_PIXMAN 1' in config
    dtc = source / 'subprojects/dtc'
    dtc_head = subprocess.check_output(['git', '-C', str(dtc), 'rev-parse', 'HEAD'], text=True).strip()
    assert dtc_head == 'b6910bec11614980a21e46fbccc35934b671bd81'
    build_args = [str(OLD / 'build-venv/bin/ninja'), '-C', str(ROOT / 'build'), '-j', '4', 'qemu-system-aarch64']
    (ROOT / 'build-command.json').write_text(json.dumps({'args': build_args, 'dtc_fixed_commit': dtc_head}, indent=2) + '\n')
    build_result = execute(build_args, 'build.log', 'BUILDING_PIXMAN_NATIVE_J4')
    output = ROOT / 'build/qemu-system-aarch64'
    result = {'configure': configuration, 'build': build_result, 'pixman_enabled': True,
              'dtc_fixed_commit': dtc_head, 'model_source_sha256': sha(source / 'hw/arm/virt.c'),
              'frozen_runtime_changed': False, 'guest_or_UI_acceptance': False}
    if output.exists():
        result['binary'] = str(output); result['binary_sha256'] = sha(output)
    (ROOT / 'build-result.json').write_text(json.dumps(result, indent=2) + '\n')
    state('BUILT_NOT_RELOCATED_NOT_GUEST_TESTED' if build_result['exit'] == 0 else 'BUILD_FAILED', result=result)
    print(json.dumps(result, indent=2), flush=True)
    return build_result['exit']


if __name__ == '__main__':
    raise SystemExit(main())
